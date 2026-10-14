from datetime import datetime
from typing import Literal
from pydantic import Field
from app.schemas.bookings import StrictModel
class Login(StrictModel):
    email: str
    password: str
class PolicyUpload(StrictModel):
    document_key: str = Field(pattern=r"^[a-z0-9_-]+$", max_length=80)
    topic: str
    language: Literal["az", "en"]
    version: int = Field(ge=1)
    content: str = Field(min_length=10, max_length=200000)
    effective_from: datetime
class OperationalRules(StrictModel):
    minimum_driver_age: int = Field(ge=16, le=100)
    maximum_rental_days: int = Field(ge=1, le=365)
    modification_fee_qepik: int = Field(ge=0)
    cancellation_fee_qepik: int = Field(ge=0)
    cancellation_free_hours: int = Field(ge=0)
class PublishRules(StrictModel):
    bundle_key: str
    version: int = Field(ge=1)
    rules: OperationalRules
class ResolveCase(StrictModel):
    decision: Literal["RESUME", "DECLINE", "APPROVE_DISCOUNT"]
    reason: str = Field(min_length=3, max_length=2000)
    discount_qepik: int | None = Field(default=None, gt=0)
class AdminMessage(StrictModel):
    text: str = Field(min_length=1, max_length=20000)
class PrivacyAction(StrictModel):
    action: Literal["PURGE", "EXTEND"]
    reason: str = Field(min_length=3, max_length=2000)
    months: int = Field(default=3, ge=1, le=12)
