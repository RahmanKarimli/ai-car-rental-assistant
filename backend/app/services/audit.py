from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from sqlalchemy import inspect
from app.models import AuditEvent

def serialize(row):
    out = {}
    for c in inspect(row).mapper.columns:
        value = getattr(row, c.key)
        if isinstance(value, (UUID, datetime, Decimal)):value = str(value)
        if c.key.endswith("qepik") and value is not None:value = str(value)
        out[c.key] = value
    return out

def audit(db, actor, action, entity, request_id, before=None, after=None, reason=None):
    db.add(AuditEvent(actor_type=actor.actor_type, actor_id=actor.admin_user_id or actor.id,
        action=action, entity_type=entity.__tablename__, entity_id=entity.id,
        request_id=str(request_id), before_snapshot=before, after_snapshot=after, reason=reason))
def now():return datetime.now(timezone.utc)
