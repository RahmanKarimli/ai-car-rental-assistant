import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Text, Integer, BigInteger, Boolean, DateTime, Date, Numeric, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSTZRANGE, TSVECTOR, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.db.base import Base, Record

class RentalPolicy(Record, Base):
    __tablename__ = "rental_policies"
    version: Mapped[int] = mapped_column()
    rules: Mapped[dict] = mapped_column(JSONB)
    policy_bundle_key: Mapped[str] = mapped_column(Text)
    published_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
class RatePlan(Record, Base):
    __tablename__ = "rate_plans"
    code: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column()
    daily_rate_qepik: Mapped[int] = mapped_column(BigInteger)
    deposit_qepik: Mapped[int] = mapped_column(BigInteger)
    tax_basis_points: Mapped[int] = mapped_column(default=0)
    tax_mode: Mapped[str] = mapped_column(String(20), default="EXCLUSIVE")
    rental_policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rental_policies.id"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    __table_args__ = (UniqueConstraint("code", "version"), CheckConstraint("daily_rate_qepik >= 0 AND deposit_qepik >= 0"), CheckConstraint("tax_basis_points BETWEEN 0 AND 10000"))
class PricingRule(Record, Base):
    __tablename__ = "pricing_rules"
    rate_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rate_plans.id"))
    kind: Mapped[str] = mapped_column(String(30))
    amount_qepik: Mapped[int] = mapped_column(BigInteger)
    effective_dates = mapped_column(__import__('sqlalchemy.dialects.postgresql', fromlist=['DATERANGE']).DATERANGE, nullable=True)
    conditions: Mapped[dict] = mapped_column(JSONB, default=dict)
class FxRate(Record, Base):
    __tablename__ = "fx_rates"
    currency_code: Mapped[str] = mapped_column(String(3))
    effective_date: Mapped[date] = mapped_column(Date)
    azn_per_unit: Mapped[Decimal] = mapped_column(Numeric(18,8))
    source_url: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("currency_code", "effective_date"), CheckConstraint("azn_per_unit > 0"))
class ApprovedAdjustment(Record, Base):
    __tablename__ = "approved_adjustments"
    escalation_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("escalation_cases.id"))
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"))
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reservations.id"))
    amount_qepik: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str] = mapped_column(Text)
    approved_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("admin_users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_by_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reservation_versions.id"))
