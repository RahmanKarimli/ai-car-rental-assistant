from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator
from app.schemas.bookings import StrictModel
class InventoryFilters(StrictModel):
    vehicle_type: str | None = None
    class_code: str | None = None
    minimum_seats: int | None = Field(default=None, ge=1, le=60)
    fuel_type: str | None = None
    transmission: str | None = None
    pickup_branch_id: UUID | None = None
    pickup_at: datetime | None = None
    return_at: datetime | None = None
    budget_amount: Decimal | None = Field(default=None, ge=0)
    budget_currency: Literal["AZN", "USD"] | None = None
    budget_basis: Literal["DAY", "TOTAL"] | None = None
    @model_validator(mode="after")
    def validate_window(self):
        if bool(self.pickup_at) != bool(self.return_at):raise ValueError("Both dates are required")
        if self.pickup_at and (self.pickup_at.tzinfo is None or self.return_at.tzinfo is None or self.return_at <= self.pickup_at):raise ValueError("Invalid timezone-aware dates")
        if self.budget_amount is not None and (not self.budget_currency or not self.budget_basis):raise ValueError("Budget currency and basis required")
        return self

class InventoryPage(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int
    pages: int

class UsdDisplayRate(BaseModel):
    available: bool
    azn_per_unit: str | None
    effective_date: str | None
    source: str

class DisplayCurrencies(BaseModel):
    base_currency: Literal["AZN"]
    usd: UsdDisplayRate
