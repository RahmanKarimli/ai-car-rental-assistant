import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Text, Integer, BigInteger, Boolean, DateTime, Date, Numeric, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSTZRANGE, TSVECTOR, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.db.base import Base, Record

class AdminUser(Record, Base):
    __tablename__ = "admin_users"
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="ADMIN")
    active: Mapped[bool] = mapped_column(default=True)
class WebSession(Record, Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    actor_type: Mapped[str] = mapped_column(String(20), default="CUSTOMER")
    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
class IdempotencyRecord(Record, Base):
    __tablename__ = "idempotency_records"
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"))
    key: Mapped[str] = mapped_column(String(200))
    operation: Mapped[str] = mapped_column(String(80))
    request_hash: Mapped[str] = mapped_column(String(64))
    result_reference: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (UniqueConstraint("session_id", "key"),)
