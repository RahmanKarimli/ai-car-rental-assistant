"""Translate incomplete conversational preferences into safe inventory queries.

Conversation state may be partial. Inventory queries and booking drafts remain strict.
"""
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from app.schemas.inventory import InventoryFilters

DATE_FIELDS = {"pickup_at", "return_at", "pickup_date", "return_date"}
TEMPORAL_REFERENCE = re.compile(
    r"\b(today|tomorrow|yesterday|tonight|noon|midnight|next|weekend|monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"january|february|march|april|june|july|august|september|october|november|december|"
    r"bugün|sabah|birigün|gələn|bazar|bazar ertəsi|çərşənbə|cümə|şənbə|"
    r"yanvar|fevral|mart|aprel|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)\b|"
    r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?\b|"
    r"\b\d{1,2}:\d{2}\b|\b\d{1,2}\s*(?:am|pm)\b|\b(?:at|saat)\s+\d{1,2}\b|"
    r"\b(?:for|üçün)\s+(?:\d+|one|two|three|four|five|six|seven|bir|iki|üç|dörd|beş)\s+(?:days?|weeks?|gün|həftə)\b|"
    r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|bir|iki|üç|dörd|beş|altı|yeddi)\s+(?:days?|weeks?|gün|həftə)\b|\bmay\s+\d{1,2}\b|\b\d{1,2}\s+may\b",
    re.IGNORECASE,
)
EXACT_TIME = re.compile(r"\b\d{1,2}:\d{2}\b|\b\d{1,2}\s*(?:am|pm)\b|\b(?:at|saat)\s+\d{1,2}\b|\b(noon|midnight|gecə yarısı)\b", re.IGNORECASE)


def datetime_value(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result if result.tzinfo is not None else None
    except (ValueError, TypeError):
        return None


def sanitize_patch(patch, text, saved):
    patch = dict(patch)
    if not TEMPORAL_REFERENCE.search(text):
        for field in DATE_FIELDS | {"rental_days"}:
            patch.pop(field, None)
    elif not EXACT_TIME.search(text):
        for field, date_field in [("pickup_at", "pickup_date"), ("return_at", "return_date")]:
            value = patch.pop(field, None)
            # A date-only message must never introduce a fabricated clock time.
            if value and value != saved.get(field):
                parsed = datetime_value(value)
                if parsed:
                    patch[date_field] = parsed.astimezone(ZoneInfo("Asia/Baku")).date().isoformat()
    if patch.get("child_passengers", 0) > 0 or patch.get("child_ages"):
        patch["has_children"] = True
    if patch.get("child_ages") and not patch.get("child_passengers"):
        patch["child_passengers"] = len(patch["child_ages"])
    if patch.get("has_children") is False or patch.get("child_passengers") == 0:
        patch.update(has_children=False, child_passengers=0, child_ages=[])
    return patch


def inventory_preferences(preferences, current_time):
    p = {key: value for key, value in preferences.items() if value is not None}
    values = {key: value for key, value in p.items() if key in InventoryFilters.model_fields}
    notes = []
    missing = []
    zone = ZoneInfo("Asia/Baku")
    today = current_time.astimezone(zone).date()
    for field in ["pickup_date", "return_date"]:
        if p.get(field):
            try:
                date.fromisoformat(p[field])
            except (ValueError, TypeError):
                p.pop(field, None)
                notes.append("INVALID_DATES")
    for field in ["pickup_at", "return_at"]:
        if p.get(field):
            parsed = datetime_value(p[field])
            if parsed is None:
                p.pop(field, None)
                values.pop(field, None)
                notes.append("INVALID_DATES")
            else:
                p[field] = parsed.isoformat()
                p[field.replace("_at", "_date")] = parsed.astimezone(zone).date().isoformat()
    days = p.get("rental_days")
    if isinstance(days, int) and 1 <= days <= 365:
        if p.get("pickup_at") and not p.get("return_at"):
            p["return_at"] = (datetime_value(p["pickup_at"]) + timedelta(days=days)).isoformat()
        elif p.get("pickup_date") and not p.get("return_date"):
            p["return_date"] = (date.fromisoformat(p["pickup_date"]) + timedelta(days=days)).isoformat()
    elif days is not None:
        p.pop("rental_days", None)
        notes.append("INVALID_DURATION")
    start, end = datetime_value(p.get("pickup_at")), datetime_value(p.get("return_at"))
    if start and start <= current_time:
        p.pop("pickup_at", None)
        p.pop("pickup_date", None)
        start = None
        notes.append("PAST_PICKUP")
    elif p.get("pickup_date") and date.fromisoformat(p["pickup_date"]) < today:
        p.pop("pickup_date", None)
        notes.append("PAST_PICKUP")
    if start and end and end <= start:
        p.pop("return_at", None)
        p.pop("return_date", None)
        end = None
        notes.append("RETURN_BEFORE_PICKUP")
    elif p.get("pickup_date") and p.get("return_date") and p["return_date"] < p["pickup_date"]:
        p.pop("return_at", None)
        p.pop("return_date", None)
        end = None
        notes.append("RETURN_BEFORE_PICKUP")
    # Keep genuine partial dates in state, but query the catalog without a window.
    values.pop("pickup_at", None)
    values.pop("return_at", None)
    if start and end:
        values.update(pickup_at=start, return_at=end)
    else:
        if not start:
            missing.append("pickup_at")
        if not end:
            missing.append("return_at")

    for field in ["passenger_count", "minimum_seats"]:
        if field in p and (not isinstance(p[field], int) or p[field] < 1):
            p.pop(field, None)
            values.pop(field, None)
            missing.append("passenger_count")
    passengers = p.get("passenger_count")
    seats = p.get("minimum_seats")
    required = max(passengers or 0, seats or 0)
    capacity_exceeded = required > 60
    if required > 0 and not capacity_exceeded:
        p["minimum_seats"] = values["minimum_seats"] = required
    else:
        values.pop("minimum_seats", None)
    if capacity_exceeded:
        notes.append("GROUP_TOO_LARGE")

    if p.get("budget_amount") is not None:
        try:
            amount = Decimal(str(p["budget_amount"]))
            if not amount.is_finite() or amount < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            p.pop("budget_amount", None)
            notes.append("INVALID_BUDGET")
            amount = None
        for field, allowed in [("budget_currency", {"AZN", "USD"}), ("budget_basis", {"DAY", "TOTAL"})]:
            if p.get(field) not in allowed:
                p.pop(field, None)
            if amount is not None and not p.get(field):
                missing.append(field)
        if amount is None or not p.get("budget_currency") or not p.get("budget_basis") or (p.get("budget_basis") == "TOTAL" and not (start and end)):
            # A total-trip budget cannot be compared without a known rental length.
            for field in ["budget_amount", "budget_currency", "budget_basis"]:
                values.pop(field, None)
        else:
            values["budget_amount"] = amount
    if p.get("has_children") or p.get("child_passengers", 0) > 0:
        if not p.get("child_passengers") or not p.get("child_ages"):
            missing.append("children_details")
    return p, InventoryFilters.model_validate(values), list(dict.fromkeys(notes)), list(dict.fromkeys(missing)), capacity_exceeded


def follow_up(preferences, missing, language):
    az = language == "az"
    questions = []
    if "pickup_at" in missing or "return_at" in missing:
        start = preferences.get("pickup_date")
        end = preferences.get("return_date")
        if "pickup_at" not in missing:
            questions.append("Avtomobili nə vaxt qaytaracaqsınız? Tarix və Bakı vaxtını yazın." if az else "When will you return the car? Please include the date and Baku time.")
        elif "return_at" not in missing:
            questions.append("Avtomobili nə vaxt götürəcəksiniz? Tarix və Bakı vaxtını yazın." if az else "When would you like to pick up the car? Please include the date and Baku time.")
        elif start and end:
            questions.append(f"{start} götürmə və {end} qaytarma üçün saatları Bakı vaxtı ilə yaza bilərsiniz?" if az else f"What pickup time on {start} and return time on {end} should I use (Baku time)?")
        elif start:
            questions.append(f"{start} üçün götürmə saatı və qaytarma tarixi/saatı nə olsun (Bakı vaxtı)?" if az else f"What pickup time on {start} and return date/time would you like (Baku time)?")
        else:
            questions.append("Götürmə və qaytarma tarixlərini və saatlarını Bakı vaxtı ilə yaza bilərsiniz?" if az else "What pickup and return dates and times would you like (Baku time)?")
    if "budget_currency" in missing or "budget_basis" in missing:
        parts = []
        if "budget_currency" in missing:
            parts.append("AZN, yoxsa USD" if az else "AZN or USD")
        if "budget_basis" in missing:
            parts.append("günlük, yoxsa bütün səfər üçün" if az else "per day or for the whole trip")
        questions.append(("Büdcəniz " + ", ".join(parts) + " nəzərdə tutulub?") if az else "Is your budget " + " and ".join(parts) + "?")
    if "children_details" in missing:
        questions.append(("Uşaqların yaşları neçədir?" if az else "How old are the children?") if preferences.get("child_passengers") else ("Neçə uşaq var və yaşları neçədir?" if az else "How many children are travelling, and what are their ages?"))
    if "passenger_count" in missing:
        questions.append("Cəmi neçə nəfər səyahət edəcək?" if az else "How many people will be travelling in total?")
    return " ".join(questions[:2])
