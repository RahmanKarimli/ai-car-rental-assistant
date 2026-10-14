from typing import Literal, Annotated
from uuid import UUID
from pydantic import Field
from app.schemas.bookings import StrictModel, DraftRequest
class TextEvent(StrictModel):
    kind: Literal["TEXT_MESSAGE"]
    client_event_id: UUID
    text: str = Field(min_length=1, max_length=20000)
class SearchEvent(StrictModel):
    kind: Literal["SEARCH"]
    client_event_id: UUID
    filters: dict
class DraftEvent(StrictModel):
    kind: Literal["PREPARE_DRAFT"]
    client_event_id: UUID
    draft: DraftRequest
class ConfirmEvent(StrictModel):
    kind: Literal["CONFIRM_DRAFT"]
    client_event_id: UUID
    draft_id: UUID
    quote_id: UUID
    expected_reservation_version: int | None = None
class LanguageEvent(StrictModel):
    kind: Literal["LANGUAGE_CHANGE"]
    client_event_id: UUID
    language: Literal["az", "en"]
class DeclineEvent(StrictModel):
    kind: Literal["DECLINE_UPSELL"]
    client_event_id: UUID
    extra_id: UUID
class HandoffEvent(StrictModel):
    kind: Literal["HANDOFF"]
    client_event_id: UUID
ChatEvent = Annotated[TextEvent | SearchEvent | DraftEvent | ConfirmEvent | LanguageEvent | DeclineEvent | HandoffEvent, Field(discriminator="kind")]
