from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from app.api.dependencies import administrator, database
from app.core.errors import DomainError
from app.services.admin_metadata import TABLES, metadata
from app.services.admin_data import model_for, record_data, create_record, update_record, delete_record
from app.services.audit import audit

router = APIRouter(prefix='/admin/data')


@router.get('/tables')
async def tables(session=Depends(administrator)):
    return [metadata(name) for name in TABLES]


@router.get('/{table}')
async def records(table: str, offset: int = Query(default=0, ge=0), limit: int = Query(default=25, ge=1, le=100),
                  session=Depends(administrator), db=Depends(database)):
    model = model_for(table)
    total = await db.scalar(select(func.count()).select_from(model))
    rows = (await db.scalars(select(model).order_by(model.created_at.desc(), model.id).offset(offset).limit(limit))).all()
    result = [record_data(row) for row in rows]
    # Reading unredacted operational data is itself recorded, with no transcript copies in the audit.
    audit(db, session, 'ADMIN_TABLE_READ', model(id=uuid4()), uuid4(), after={'table': table, 'offset': offset, 'count': len(result)})
    await db.commit()
    return {'items': result, 'total': total, 'offset': offset, 'limit': limit}


@router.get('/{table}/{id}')
async def record(table: str, id: UUID, session=Depends(administrator), db=Depends(database)):
    row = await db.get(model_for(table), id)
    if not row: raise DomainError('NOT_FOUND', 'Record not found', 404)
    result = record_data(row)
    audit(db, session, 'ADMIN_RECORD_READ', row, uuid4())
    await db.commit()
    return result


@router.post('/{table}')
async def create(table: str, body: dict, session=Depends(administrator), db=Depends(database)):
    return await create_record(db, session, table, body)


@router.patch('/{table}/{id}')
async def change(table: str, id: UUID, body: dict, session=Depends(administrator), db=Depends(database)):
    return await update_record(db, session, table, id, body)


@router.delete('/{table}/{id}')
async def remove(table: str, id: UUID, session=Depends(administrator), db=Depends(database)):
    return await delete_record(db, session, table, id)
