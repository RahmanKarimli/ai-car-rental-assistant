from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
class ExtraSelection(StrictModel):
    extra_id: UUID
    quantity: int = Field(default=1, ge=1, le=10)
class Trip(StrictModel):
    vehicle_id: UUID
    pickup_branch_id: UUID
    return_branch_id: UUID
    pickup_at: datetime
    return_at: datetime
    extras: list[ExtraSelection] = Field(default_factory=list, max_length=20)
    driver_age: int = Field(ge=16, le=100)
    @model_validator(mode="after")
    def valid_dates(self):
        if self.pickup_at.tzinfo is None or self.return_at.tzinfo is None:
            raise ValueError("Dates require a timezone")
        if self.return_at <= self.pickup_at:
            raise ValueError("Return must follow pickup")
        if len({e.extra_id for e in self.extras}) != len(self.extras):
            raise ValueError("Duplicate extras")
        return self
class Contact(StrictModel):
    name: str = Field(min_length=2, max_length=200)
    phone: str = Field(min_length=5, max_length=40)
    email: str | None = Field(default=None, max_length=255)
class DraftRequest(StrictModel):
    conversation_id: UUID
    action_kind: Literal["CREATE", "MODIFY", "CANCEL"] = "CREATE"
    reservation_id: UUID | None = None
    expected_reservation_version: int | None = Field(default=None, ge=1)
    trip: Trip | None = None
    contact: Contact | None = None
class ConfirmRequest(StrictModel):
    quote_id: UUID
    expected_reservation_version: int | None = None
