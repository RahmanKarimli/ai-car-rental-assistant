import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Text, Integer, BigInteger, Boolean, DateTime, Date, Numeric, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSTZRANGE, TSVECTOR, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.db.base import Base, Record

class Quote(Record, Base):
    __tablename__ = "quotes"
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"))
    action_kind: Mapped[str] = mapped_column(String(20))
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reservations.id", use_alter=True, name="fk_quote_reservation"))
    inputs_snapshot: Mapped[dict] = mapped_column(JSONB)
    policy_snapshot: Mapped[dict] = mapped_column(JSONB)
    rate_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rate_plans.id"))
    fx_rate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fx_rates.id"))
    total_qepik: Mapped[int] = mapped_column(BigInteger)
    deposit_qepik: Mapped[int] = mapped_column(BigInteger)
    delta_qepik: Mapped[int | None] = mapped_column(BigInteger)
    signature: Mapped[str] = mapped_column(String(64))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    operation_key: Mapped[str] = mapped_column(Text, unique=True)
    __table_args__ = (CheckConstraint("total_qepik >= 0 AND deposit_qepik >= 0"),)
class QuoteItem(Record, Base):
    __tablename__ = "quote_items"
    quote_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quotes.id"))
    code: Mapped[str] = mapped_column(String(60))
    label_az: Mapped[str] = mapped_column(Text)
    label_en: Mapped[str] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column()
    unit_amount_qepik: Mapped[int] = mapped_column(BigInteger)
    line_total_qepik: Mapped[int] = mapped_column(BigInteger)
    rule_reference: Mapped[dict] = mapped_column(JSONB, default=dict)
    sort_order: Mapped[int] = mapped_column(default=0)
class BookingDraft(Record, Base):
    __tablename__ = "booking_drafts"
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"))
    quote_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quotes.id"))
    action_kind: Mapped[str] = mapped_column(String(20))
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reservations.id"))
    base_reservation_version: Mapped[int | None] = mapped_column()
    proposal: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="READY")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    committed_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reservation_versions.id", use_alter=True, name="fk_draft_committed_version"))
    operation_key: Mapped[str] = mapped_column(Text, unique=True)
class Reservation(Record, Base):
    __tablename__ = "reservations"
    public_reference: Mapped[str] = mapped_column(String(40), unique=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("conversations.id"))
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id"))
    pickup_branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"))
    return_branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"))
    pickup_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    return_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="CONFIRMED")
    current_version: Mapped[int] = mapped_column(default=1)
    total_qepik: Mapped[int] = mapped_column(BigInteger)
    deposit_qepik: Mapped[int] = mapped_column(BigInteger)
    renter_contact: Mapped[dict] = mapped_column(JSONB)
    payment_method: Mapped[str] = mapped_column(String(30), default="PAY_AT_PICKUP")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("return_at > pickup_at"), CheckConstraint("total_qepik >= 0 AND deposit_qepik >= 0"))
class ReservationVersion(Record, Base):
    __tablename__ = "reservation_versions"
    reservation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reservations.id"))
    version: Mapped[int] = mapped_column()
    action_kind: Mapped[str] = mapped_column(String(20))
    quote_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quotes.id"))
    snapshot: Mapped[dict] = mapped_column(JSONB)
    actor_type: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[uuid.UUID | None] = mapped_column()
    reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("reservation_id", "version"),)
class BookingAccessGrant(Record, Base):
    __tablename__ = "booking_access_grants"
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"))
    reservation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reservations.id"))
    permissions: Mapped[list] = mapped_column(JSONB, default=lambda:["READ","MODIFY","CANCEL"])
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("session_id", "reservation_id"),)
