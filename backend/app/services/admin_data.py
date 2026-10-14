"""Admin CRUD with explicit input schemas, relationship guards and auditing."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4
from pydantic import ValidationError
from sqlalchemy import select, func, update, or_
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.exc import IntegrityError
from app.models import (
    Base, AdminUser, WebSession, Vehicle, VehicleAllocation, ExtraAllocation,
    RatePlan, RentalPolicy, PricingRule, PolicyDocument, Quote, QuoteItem,
)
from app.core.errors import DomainError
from app.core.security import passwords, digest
from app.providers.filesystem import assets
from app.services.audit import audit, now
from app.services.admin_metadata import TABLES, INPUTS, EDITABLE, DELETABLE, HIDDEN


def model_for(table):
    if table not in TABLES:
        raise DomainError('NOT_FOUND', 'Table not found', 404)
    return TABLES[table][0]


def record_data(row):
    result = {}
    for column in row.__table__.columns:
        if column.name in HIDDEN:
            continue
        value = getattr(row, column.name)
        if isinstance(value, Range):
            value = {'start': str(value.lower), 'end': str(value.upper), 'bounds': value.bounds}
            if column.name == 'effective_dates': value = [value['start'], value['end']]
        elif isinstance(value, (UUID, datetime, date, Decimal)):
            value = str(value)
        elif column.name.endswith('qepik') and value is not None:
            value = str(value)
        result[column.name] = value
    return result


def validated(table, body, row=None):
    if table not in INPUTS:
        raise DomainError('WORKFLOW_REQUIRED', 'Use the booking, publication or retention workflow for this table', 409)
    schema = INPUTS[table]
    allowed = set(schema.model_fields)
    if set(body) - allowed:
        raise DomainError('INVALID_FIELDS', 'These fields cannot be written: ' + ', '.join(sorted(set(body) - allowed)), 422)
    current = {key: value for key, value in record_data(row).items() if key in allowed} if row else {}
    try:
        result = schema.model_validate({**current, **body}).model_dump()
    except ValidationError as error:
        detail = '; '.join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors(include_input=False, include_url=False))
        raise DomainError('INVALID_FIELDS', detail, 422)
    if row: result = {key: value for key, value in result.items() if key in body}
    if table == 'extras' and 'eligibility_rules' in result:
        result['eligibility_rules'] = {k: v for k, v in result['eligibility_rules'].items() if v is not None}
    if table == 'pricing_rules' and result.get('effective_dates'):
        start, end = result['effective_dates']
        result['effective_dates'] = Range(date.fromisoformat(start), date.fromisoformat(end), bounds='[)')
    return result


async def references(db, table, id):
    """Count incoming foreign keys, including historical references; never cascade."""
    result = []
    for source in Base.metadata.tables.values():
        for column in source.columns:
            if any(fk.column.table.name == table for fk in column.foreign_keys):
                count = await db.scalar(select(func.count()).select_from(source).where(column == id))
                if count: result.append(f'{source.name}.{column.name} ({count})')
    if table == 'extras':
        count = await db.scalar(select(func.count()).select_from(QuoteItem).where(QuoteItem.rule_reference['extra_id'].astext == str(id)))
        if count: result.append(f'quote_items.rule_reference.extra_id ({count})')
    return result


async def check_references(db, table, values):
    model = model_for(table)
    for name, value in values.items():
        if name not in model.__table__.columns or value is None: continue
        for fk in model.__table__.columns[name].foreign_keys:
            target = model_for(fk.column.table.name)
            if not await db.get(target, value):
                raise DomainError('INVALID_REFERENCE', f'{name}: linked record does not exist', 422)


async def guard(db, table, values, row=None, deleting=False):
    if table == 'policy_documents' and row and row.status != 'DRAFT':
        raise DomainError('PUBLISHED_POLICY', 'Published and retired policy sources are retained. Create a new version.', 409)
    if table == 'vehicles' and row and set(values) - {'status', 'features'}:
        allocated = await db.scalar(select(VehicleAllocation.id).where(
            VehicleAllocation.vehicle_id == row.id, VehicleAllocation.status == 'ACTIVE',
            func.upper(VehicleAllocation.period) > now(),
            or_(VehicleAllocation.expires_at.is_(None), VehicleAllocation.expires_at > now()),
        ).limit(1))
        if allocated:
            raise DomainError('VEHICLE_ALLOCATED', 'This car has a hold or future booking. Resolve it before changing vehicle details or pricing.', 409)
    if table == 'extras' and row and 'stock_total' in values:
        total = values['stock_total']
        if total is not None and (row.stock_total is None or total < row.stock_total):
            allocated = await db.scalar(select(ExtraAllocation.id).where(
                ExtraAllocation.extra_id == row.id, ExtraAllocation.status == 'ACTIVE',
                func.upper(ExtraAllocation.period) > now(),
                or_(ExtraAllocation.expires_at.is_(None), ExtraAllocation.expires_at > now()),
            ).limit(1))
            if allocated:
                raise DomainError('STOCK_ALLOCATED', 'Resolve active allocations before reducing total equipment stock.', 409)
    if (table == 'vehicles' and 'rate_plan_id' in values) or table == 'rate_plans':
        plan = await db.get(RatePlan, values['rate_plan_id'], with_for_update=True) if table == 'vehicles' else None
        policy_id = plan.rental_policy_id if plan else values.get('rental_policy_id')
        policy = await db.get(RentalPolicy, policy_id) if policy_id else None
        if not policy or not policy.published_at:
            raise DomainError('POLICY_NOT_PUBLISHED', 'Select a rate plan with published operational rules.', 409)
    if table == 'pricing_rules':
        plan = await db.get(RatePlan, values['rate_plan_id'], with_for_update=True)
        if not plan: raise DomainError('INVALID_REFERENCE', 'Select an existing rate plan.', 422)
        used = await db.scalar(select(Vehicle.id).where(Vehicle.rate_plan_id == plan.id).limit(1))
        quoted = await db.scalar(select(Quote.id).where(Quote.rate_plan_id == plan.id).limit(1))
        if used or quoted:
            raise DomainError('PLAN_IN_USE', 'This plan is already in use. Create a new rate-plan version, add its rules, then assign vehicles.', 409)
        if values['kind'] == 'SEASONAL_DAILY':
            overlap = await db.scalar(select(PricingRule.id).where(
                PricingRule.rate_plan_id == plan.id, PricingRule.kind == 'SEASONAL_DAILY',
                PricingRule.effective_dates.op('&&')(values['effective_dates']),
            ).limit(1))
            if overlap: raise DomainError('AMBIGUOUS_PRICING', 'Seasonal date ranges overlap for this rate plan.', 409)
    if deleting:
        usage = await references(db, table, row.id)
        if usage:
            raise DomainError('RECORD_IN_USE', 'Cannot delete a referenced record: ' + ', '.join(usage) + '. Deactivate it where available.', 409)


async def account_guard(db, actor, row, values, deleting=False):
    # Lock all administrators in stable order to prevent concurrent last-admin removal.
    await db.execute(select(AdminUser.id).where(AdminUser.role == 'ADMIN').order_by(AdminUser.id).with_for_update())
    if row and row.id == actor.admin_user_id and (deleting or values.get('active') is False or values.get('role', row.role) != 'ADMIN'):
        raise DomainError('OWN_ACCOUNT', 'Your current administrator account cannot be disabled, demoted or deleted.', 409)
    if row and row.role == 'ADMIN' and row.active and (deleting or values.get('active') is False or values.get('role', row.role) != 'ADMIN'):
        others = await db.scalar(select(func.count()).select_from(AdminUser).where(AdminUser.role == 'ADMIN', AdminUser.active.is_(True), AdminUser.id != row.id))
        if not others: raise DomainError('LAST_ADMIN', 'Keep at least one active administrator.', 409)


def document_source(row):
    row.content_hash = digest(row.full_text)
    row.source_asset_key = f'policies/{row.language}/{row.document_key}-v{row.version}-{row.content_hash[:16]}.md'
    assets.put(row.source_asset_key, row.full_text.encode('utf-8'))


async def finish(db):
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise DomainError('DATA_CONFLICT', 'A unique value already exists, or another action linked this record. Refresh and review its fields.', 409)


async def create_record(db, actor, table, body):
    if table == 'vehicle_photos':
        raise DomainError('UPLOAD_REQUIRED', 'Use the image upload control to create a photo.', 422)
    model = model_for(table)
    values = validated(table, body)
    await check_references(db, table, values)
    await guard(db, table, values)
    if table == 'rate_plans': values['created_by'] = actor.admin_user_id
    if table == 'admin_users':
        password = values.pop('password')
        if not password: raise DomainError('PASSWORD_REQUIRED', 'A new account requires a password of at least 12 characters.', 422)
        values['password_hash'] = passwords.hash(password)
    row = model(id=uuid4(), **values)
    if table == 'policy_documents': document_source(row)
    db.add(row)
    try: await db.flush()
    except IntegrityError:
        await db.rollback()
        raise DomainError('DATA_CONFLICT', 'A record with these unique fields already exists.', 409)
    result = record_data(row)
    audit(db, actor, 'ADMIN_RECORD_CREATED', row, uuid4(), after=result)
    await finish(db)
    return result


async def update_record(db, actor, table, id, body):
    model = model_for(table)
    if table not in EDITABLE:
        raise DomainError('WORKFLOW_REQUIRED', 'This record is maintained through its application workflow or a new published version.', 409)
    if table == 'admin_users': await account_guard(db, actor, None, {})
    row = await db.get(model, id, with_for_update=True)
    if not row: raise DomainError('NOT_FOUND', 'Record not found', 404)
    if not body: raise DomainError('INVALID_FIELDS', 'Change at least one editable field.', 422)
    values = validated(table, body, row)
    await check_references(db, table, values)
    await guard(db, table, values, row)
    before = record_data(row)
    if table == 'admin_users':
        await account_guard(db, actor, row, values)
        password = values.pop('password', None)
        if password: values['password_hash'] = passwords.hash(password)
        if password or 'role' in values or values.get('active') is False:
            # A changed credential or role invalidates other sessions immediately.
            await db.execute(update(WebSession).where(WebSession.admin_user_id == row.id, WebSession.id != actor.id, WebSession.revoked_at.is_(None)).values(revoked_at=now()))
    for key, value in values.items(): setattr(row, key, value)
    if table == 'policy_documents': document_source(row)
    result = record_data(row)
    audit(db, actor, 'ADMIN_RECORD_UPDATED', row, uuid4(), before=before, after=result,
          reason='Password changed' if 'password_hash' in values else None)
    await finish(db)
    return result


async def delete_record(db, actor, table, id):
    model = model_for(table)
    if table not in DELETABLE:
        raise DomainError('WORKFLOW_REQUIRED', 'This record must be retained. Use its booking or retention workflow.', 409)
    if table == 'admin_users': await account_guard(db, actor, None, {})
    row = await db.get(model, id, with_for_update=True)
    if not row: raise DomainError('NOT_FOUND', 'Record not found', 404)
    if table == 'admin_users': await account_guard(db, actor, row, {}, deleting=True)
    await guard(db, table, {}, row, deleting=True)
    before = record_data(row)
    audit(db, actor, 'ADMIN_RECORD_DELETED', row, uuid4(), before=before)
    await db.delete(row)
    await finish(db)
    return {'deleted': True, 'id': str(id)}
