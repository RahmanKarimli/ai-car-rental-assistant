"""Validated admin input. System-generated columns never enter these schemas."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BeforeValidator, Field, field_validator, model_validator
from app.schemas.bookings import StrictModel


def integer(value):
    if isinstance(value, bool) or not (isinstance(value, int) or isinstance(value, str) and value.lstrip('-').isdigit()):
        raise ValueError('Enter a whole integer; monetary amounts use AZN qəpiks')
    return int(value)


Whole = Annotated[int, BeforeValidator(integer)]
Money = Annotated[Whole, Field(ge=0, le=9223372036854775807)]
Name = Annotated[str, Field(min_length=1, max_length=255)]


class BranchInput(StrictModel):
    name_az: Name
    name_en: Name
    city: Name
    address: Annotated[str, Field(min_length=1, max_length=2000)]
    country_code: Literal['AZ'] = 'AZ'
    opening_hours: dict = Field(default_factory=dict)
    active: bool = True


class VehicleInput(StrictModel):
    registration_number: Name
    make: Name
    model: Name
    model_year: Annotated[Whole, Field(ge=1950, le=2100)]
    vehicle_type: Literal['SEDAN', 'SUV', 'HATCHBACK', 'VAN', 'MINIVAN', 'CONVERTIBLE', 'COUPE', 'WAGON', 'PICKUP']
    class_code: Name
    seats: Annotated[Whole, Field(ge=1, le=60)]
    fuel_type: Literal['PETROL', 'DIESEL', 'HYBRID', 'ELECTRIC', 'LPG']
    transmission: Literal['AUTOMATIC', 'MANUAL']
    branch_id: UUID
    rate_plan_id: UUID
    daily_rate_qepik: Money | None = None
    status: Literal['ACTIVE', 'INACTIVE', 'MAINTENANCE'] = 'ACTIVE'
    features: list[str] = Field(default_factory=list, max_length=100)


class Eligibility(StrictModel):
    minimum_trip_days: Annotated[Whole, Field(ge=1, le=365)] | None = None
    months: list[Annotated[Whole, Field(ge=1, le=12)]] | None = None
    destinations: list[str] | None = None
    vehicle_classes: list[str] | None = None


class ExtraInput(StrictModel):
    code: Annotated[str, Field(min_length=1, max_length=40)]
    kind: Literal['GPS', 'CHILD_SEAT', 'INSURANCE', 'OTHER']
    name_az: Name
    name_en: Name
    description_az: Annotated[str, Field(min_length=1, max_length=4000)]
    description_en: Annotated[str, Field(min_length=1, max_length=4000)]
    price_qepik: Money
    billing_unit: Literal['PER_DAY', 'PER_RENTAL']
    stock_total: Annotated[Whole, Field(ge=0, le=2147483647)] | None = None
    eligibility_rules: Eligibility = Field(default_factory=Eligibility)
    active: bool = True


class RateInput(StrictModel):
    code: Name
    version: Annotated[Whole, Field(ge=1, le=2147483647)]
    daily_rate_qepik: Money
    deposit_qepik: Money
    tax_basis_points: Annotated[Whole, Field(ge=0, le=10000)] = 0
    tax_mode: Literal['INCLUSIVE', 'EXCLUSIVE'] = 'EXCLUSIVE'
    rental_policy_id: UUID


class RuleInput(StrictModel):
    rate_plan_id: UUID
    kind: Literal['SEASONAL_DAILY', 'FIXED_FEE']
    amount_qepik: Money
    effective_dates: tuple[str, str] | None = None
    conditions: dict = Field(default_factory=dict)

    @model_validator(mode='after')
    def valid_dates(self):
        from datetime import date
        if self.kind == 'SEASONAL_DAILY' and not self.effective_dates:
            raise ValueError('Seasonal pricing requires a start date and an exclusive end date')
        if self.kind == 'FIXED_FEE' and self.effective_dates:
            raise ValueError('Fixed fees apply to every rental; leave dates empty')
        if self.effective_dates:
            start, end = [date.fromisoformat(x) for x in self.effective_dates]
            if end <= start:
                raise ValueError('End date must follow start date')
        if self.conditions:
            raise ValueError('Conditions are reserved for future use; use an empty object')
        return self


class PhotoInput(StrictModel):
    vehicle_id: UUID
    alt_az: Annotated[str, Field(min_length=1, max_length=1000)]
    alt_en: Annotated[str, Field(min_length=1, max_length=1000)]
    sort_order: Annotated[Whole, Field(ge=0, le=10000)] = 0


class AdminInput(StrictModel):
    email: Annotated[str, Field(min_length=3, max_length=255, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')]
    password: Annotated[str, Field(min_length=12, max_length=128)] | None = None
    role: Literal['ADMIN', 'SUPPORT'] = 'ADMIN'
    active: bool = True

    @field_validator('email')
    @classmethod
    def normalized_email(cls, value):
        return value.strip().lower()


class DocumentInput(StrictModel):
    document_key: Annotated[str, Field(pattern=r'^[a-z0-9_-]+$', max_length=80)]
    topic: Name
    language: Literal['az', 'en']
    version: Annotated[Whole, Field(ge=1, le=2147483647)]
    branch_id: UUID | None = None
    full_text: Annotated[str, Field(min_length=10, max_length=200000)]
    effective_from: datetime
    effective_until: datetime | None = None

    @model_validator(mode='after')
    def valid_dates(self):
        if self.effective_from.tzinfo is None or self.effective_until and self.effective_until.tzinfo is None:
            raise ValueError('Include a timezone in policy dates')
        if self.effective_until and self.effective_until <= self.effective_from:
            raise ValueError('Policy end date must follow its start date')
        return self
