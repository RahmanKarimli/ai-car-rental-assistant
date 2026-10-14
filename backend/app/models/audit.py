import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Text, Integer, BigInteger, Boolean, DateTime, Date, Numeric, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSTZRANGE, TSVECTOR, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.db.base import Base, Record

class AuditEvent(Record, Base):
    __tablename__ = "audit_events"
    actor_type: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[uuid.UUID | None] = mapped_column()
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[uuid.UUID] = mapped_column()
    request_id: Mapped[str] = mapped_column(Text)
    before_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    after_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
class ConversionEvent(Record, Base):
    __tablename__ = "conversion_events"
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("conversations.id"))
    event_name: Mapped[str] = mapped_column(String(60))
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
