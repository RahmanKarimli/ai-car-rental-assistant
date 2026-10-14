import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Text, Integer, BigInteger, Boolean, DateTime, Date, Numeric, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSTZRANGE, TSVECTOR, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.db.base import Base, Record

class Branch(Record, Base):
    __tablename__ = "branches"
    name_az: Mapped[str] = mapped_column(Text)
    name_en: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(Text)
    address: Mapped[str] = mapped_column(Text)
    country_code: Mapped[str] = mapped_column(String(2), default="AZ")
    opening_hours: Mapped[dict] = mapped_column(JSONB, default=dict)
    active: Mapped[bool] = mapped_column(default=True)
class Vehicle(Record, Base):
    __tablename__ = "vehicles"
    registration_number: Mapped[str] = mapped_column(Text, unique=True)
    make: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    model_year: Mapped[int] = mapped_column()
    vehicle_type: Mapped[str] = mapped_column(String(30))
    class_code: Mapped[str] = mapped_column(String(40))
    seats: Mapped[int] = mapped_column()
    fuel_type: Mapped[str] = mapped_column(String(30))
    transmission: Mapped[str] = mapped_column(String(30))
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"))
    rate_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rate_plans.id"))
    # Optional per-vehicle override. When set, this physical car's price is
    # used instead of the shared rate-plan base daily rate.
    daily_rate_qepik: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    features: Mapped[list] = mapped_column(JSONB, default=list)
    __table_args__ = (CheckConstraint("seats > 0"), CheckConstraint("daily_rate_qepik IS NULL OR daily_rate_qepik >= 0"))
class VehiclePhoto(Record, Base):
    __tablename__ = "vehicle_photos"
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id"))
    asset_key: Mapped[str] = mapped_column(Text)
    alt_az: Mapped[str] = mapped_column(Text)
    alt_en: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(default=0)
class Extra(Record, Base):
    __tablename__ = "extras"
    code: Mapped[str] = mapped_column(String(40), unique=True)
    kind: Mapped[str] = mapped_column(String(30))
    name_az: Mapped[str] = mapped_column(Text)
    name_en: Mapped[str] = mapped_column(Text)
    description_az: Mapped[str] = mapped_column(Text)
    description_en: Mapped[str] = mapped_column(Text)
    price_qepik: Mapped[int] = mapped_column(BigInteger)
    billing_unit: Mapped[str] = mapped_column(String(20))
    stock_total: Mapped[int | None] = mapped_column()
    eligibility_rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    active: Mapped[bool] = mapped_column(default=True)
    __table_args__ = (CheckConstraint("price_qepik >= 0"), CheckConstraint("stock_total IS NULL OR stock_total >= 0"))
class VehicleAllocation(Record, Base):
    __tablename__ = "vehicle_allocations"
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id"))
    period = mapped_column(TSTZRANGE, nullable=False)
    purpose: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    draft_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("booking_drafts.id"))
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reservations.id"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (ExcludeConstraint(("vehicle_id", "="), ("period", "&&"), where=text("status = 'ACTIVE'"), using="gist", name="no_vehicle_overlap"), CheckConstraint("NOT isempty(period)"))
class ExtraAllocation(Record, Base):
    __tablename__ = "extra_allocations"
    extra_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("extras.id"))
    period = mapped_column(TSTZRANGE, nullable=False)
    quantity: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    draft_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("booking_drafts.id"))
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reservations.id"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("quantity > 0"), Index("extra_window", "extra_id", "period", postgresql_using="gist"))
