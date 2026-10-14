from pydantic import BaseModel, ConfigDict
from typing import Literal
SearchSort = Literal["RECOMMENDED", "PRICE_ASC", "SPACE_DESC"]
class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vehicle_type: Literal["SEDAN", "SUV", "HATCHBACK", "VAN", "MINIVAN", "CONVERTIBLE", "COUPE", "WAGON", "PICKUP"] | None
    class_code: Literal["ECONOMY", "STANDARD", "FAMILY", "PREMIUM", "VAN", "ELECTRIC"] | None = None
    minimum_seats: int | None
    fuel_type: Literal["PETROL", "DIESEL", "HYBRID", "ELECTRIC", "LPG"] | None
    transmission: Literal["AUTOMATIC", "MANUAL"] | None
    pickup_at: str | None
    return_at: str | None
    pickup_date: str | None = None
    return_date: str | None = None
    rental_days: int | None = None
    budget_amount: str | None
    budget_currency: Literal["AZN", "USD"] | None
    budget_basis: Literal["DAY", "TOTAL"] | None
    destination: str | None
    passenger_count: int | None
    child_passengers: int | None
    has_children: bool | None = None
    child_ages: list[int] | None = None
    needs_navigation: bool | None
    sort_by: SearchSort | None = None
class IntentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Literal["az", "en"]
    intent: Literal["SEARCH", "POLICY_QA", "CREATE_DRAFT", "MODIFY", "CANCEL", "ESCALATE", "GUIDANCE", "GREETING", "CAPABILITIES", "OUT_OF_SCOPE"]
    search_mode: Literal["NEW", "REFINE"] | None = None
    show_different: bool = False
    clear_preferences: list[Literal["vehicle_type", "class_code", "minimum_seats", "fuel_type", "transmission", "budget_amount", "budget_currency", "budget_basis", "pickup_at", "return_at", "pickup_date", "return_date", "rental_days", "sort_by"]] = []
    preferences: Preferences
    policy_query: str | None
    risk_reason: Literal["MANUAL_DISCOUNT", "OUT_OF_STATE_DROPOFF", "PAYMENT_EXCEPTION"] | None
class PolicyAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str
    source_ids: list[str]
    supported: bool

class GuidanceAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
