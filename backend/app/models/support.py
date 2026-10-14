import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Text, Integer, BigInteger, Boolean, DateTime, Date, Numeric, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSTZRANGE, TSVECTOR, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.db.base import Base, Record

class EscalationCase(Record, Base):
    __tablename__ = "escalation_cases"
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"))
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reservations.id"))
    reason_code: Mapped[str] = mapped_column(String(60))
    summary: Mapped[str] = mapped_column(Text)
    source_log_ids: Mapped[list] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    assigned_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    resolution: Mapped[dict | None] = mapped_column(JSONB)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
