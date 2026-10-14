from typing import TypedDict, Any
class RentalAgentState(TypedDict,total=False):
    conversation_id: str
    session_id: str
    run_id: str
    event: dict
    language: str
    preferences: dict
    phase: str
    intent: str
    risk_reason: str | None
    active_draft_id: str | None
    retrieved_chunks: list
    policy_query: str | None
    cards: list
    text: str
    context: list
    missing_fields: list
    error_code: str | None
    response: dict
    usage: dict

    interpretation: dict | None
    recent_vehicle_ids: list[str]
    search_signature: str | None
    search_seen_vehicle_ids: list[str]
    show_different: bool
    search_mode: str | None
    search_notes: list[str]
    alternative_class: str | None
    alternative_budget: bool
    error_node: str | None
