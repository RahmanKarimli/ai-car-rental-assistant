"""Deterministic search ordering; vehicle eligibility and pricing stay in services."""
import re
PRICE_REQUEST = re.compile(
    r"\b(?:cheapest|cheaper|cheap|least expensive|less expensive|lowest (?:trip |rental |total |daily )?(?:price|cost|rate)|"
    r"most affordable|lowest.priced|price.low|price ascending|ən ucuz|en ucuz|daha ucuz|ucuz|"
    r"ən sərfəli|en serfeli)\b", re.IGNORECASE,
)
SPACE_REQUEST = re.compile(
    r"\b(?:biggest|largest|most spacious|roomiest|more spacious|(?:most|more) (?:room|space|seats)|"
    r"maximum (?:space|capacity)|ən böyük|en boyuk|ən geniş|en genis|daha geniş|daha genis)\b",
    re.IGNORECASE,
)
DIFFERENT_REQUEST = re.compile(
    r"\b(?:other|different|alternative|additional)\s+(?:\w+\s+){0,2}(?:cars?|vehicles?|options?|choices?|ones?)\b|"
    r"\b(?:show|give|see|offer)\s+(?:me\s+)?(?:some\s+)?(?:others|alternatives)\b|"
    r"\b(?:show|give|see|offer)\s+(?:me\s+)?(?:some\s+)?more\s*[.!?]*$|"
    r"\bmore\s+(?:\w+\s+){0,2}(?:cars?|vehicles?|options?|choices?)\b|"
    r"\b(?:başqa|basqa|digər|diger)\s+(?:\w+\s+){0,2}(?:avtomobil\w*|maşın\w*|masin\w*|seçim\w*|secim\w*|variant\w*)\b|"
    r"\b(?:başqalarını|basqalarini|daha çox seçim|daha cox secim)\b",
    re.IGNORECASE,
)
LUGGAGE_SPACE = re.compile(
    r"\b(?:large (?:boot|luggage area|cargo area)|extra luggage space|spacious cabin|extra legroom|"
    r"geniş (?:baqaj|salon|yük sahəsi))\b", re.IGNORECASE,
)


def search_controls(text, model_sort=None, model_different=False):
    """Known ordering phrases have stable semantics even if model classification varies."""
    price, space = PRICE_REQUEST.search(text), SPACE_REQUEST.search(text)
    sort = model_sort
    if price or space:
        sort = "PRICE_ASC" if price and (not space or price.start() < space.start()) else "SPACE_DESC"
    if sort not in {"RECOMMENDED", "PRICE_ASC", "SPACE_DESC"}:
        sort = None
    different = bool(DIFFERENT_REQUEST.search(text)) or bool(re.search(r"\b(?:something else|anything else|what else|not these|not those|not the same|another (?:car|option)|başqa nə|digərlərini)\b",text,re.IGNORECASE))
    # A model flag alone must not make an ordinary repeat rotate its results.
    if model_different and re.search(r"\b(?:others|alternatives|remaining (?:cars|options)|next (?:cars|options)|new (?:cars|options|recommendations)|digərləri)\b",text,re.IGNORECASE):
        different = True
    if re.search(r"\b(?:don't|do not|no)\s+(?:show\s+)?(?:me\s+)?(?:different|other|more|alternatives)\b", text, re.IGNORECASE):
        different = False
    return sort, different


def protect_ranking_refinement(patch, clear_fields, text):
    """An ordering-only message cannot manufacture or erase eligibility filters."""
    patch = dict(patch)
    capacity = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|bir|iki|üç|dörd|beş|altı|yeddi|səkkiz|doqquz|on)"
    sources = {
        "minimum_seats": rf"\b{capacity}[\s-]*(?:seats?|seaters?|places?|people|passengers?|persons?|nəfər\w*|yer\w*|oturacaq\w*)\b|\b(?:seats?|places?|people|passengers?)\s*(?:for|:)?\s*{capacity}\b|\b(?:we are|we're|for)\s+{capacity}\b",
        "budget_amount": r"\bbudget\b|\blimit\b|AZN|USD|[$₼]|manat|dollar|büdcə|\b(?:under|below|up to|at most|maximum|max)\s+\d",
        "vehicle_type": r"\b(?:sedan|saloon|suv|crossover|hatchback|compact|van|minivan|mpv|convertible|coupe|wagon|pickup)\b",
        "class_code": r"\b(?:economy|standard|family|premium|luxury|luxurious|high.end|van|electric|ailə|lüks|ekonom)\b",
        "fuel_type": r"\b(?:petrol|gasoline|diesel|hybrid|electric|lpg|benzin|dizel|hibrid|elektrik)\b",
        "transmission": r"\b(?:automatic|auto|manual|avtomat|mexaniki)\b",
    }
    clear = set(clear_fields)
    for field, pattern in sources.items():
        if not re.search(pattern, text, re.IGNORECASE):
            patch.pop(field, None)
            if field in {"vehicle_type", "class_code", "fuel_type", "transmission"}:
                clear.discard(field)
            if field == "minimum_seats":
                patch.pop("passenger_count", None)
            if field == "budget_amount":
                patch.pop("budget_currency", None)
                patch.pop("budget_basis", None)
    if not re.search(r"\b(?:no|without|ignore|forget|remove|drop|unlimited)\b.{0,25}\b(?:budget|limit)\b|\bbudget\b.{0,25}(?:no limit|doesn't matter|unlimited)|büdcə.{0,25}(?:yox|ləğv)|büdcəni.{0,25}(?:unut|sil)", text, re.IGNORECASE):
        clear -= {"budget_amount", "budget_currency", "budget_basis"}
    if not re.search(r"\b(?:any|ignore|forget|remove|no)\b.{0,25}\b(?:seats?|seat count|seat limit)\b|yer.{0,25}(?:fərq etmir|məhdudiyyət yoxdur)",text,re.IGNORECASE):
        clear.discard("minimum_seats")
    if not re.search(r"\b(?:ignore|forget|remove|clear|reset|no)\b.{0,25}\b(?:dates?|times?|pickup|return)\b|tarix.{0,25}(?:unut|sil|ləğv)",text,re.IGNORECASE):
        clear -= {"pickup_at", "return_at", "pickup_date", "return_date", "rental_days"}
    return patch, [field for field in clear_fields if field in clear]


def actual_search_amount(card):
    # The pricing engine supplies the trip total. With incomplete dates, only
    # the base daily rate is known; response copy explicitly states that limit.
    return int((card.get("rental_price") or card["daily_price"])["amount_qepik"])


def recorded_luggage_space(card):
    return any(LUGGAGE_SPACE.search(feature) for feature in card.get("features", []) if isinstance(feature, str))


def ordered_vehicles(cards, preferences):
    sort = preferences.get("sort_by", "RECOMMENDED")
    seats = preferences.get("minimum_seats") or preferences.get("passenger_count") or 1

    def key(card):
        price, identifier = actual_search_amount(card), card["vehicle_id"]
        if sort == "PRICE_ASC":
            return price, identifier
        if sort == "SPACE_DESC":
            return -card["seats"], -int(recorded_luggage_space(card)), price, identifier
        return max(0, card["seats"] - seats), price, identifier

    return sorted((card for card in cards if card.get("type") == "vehicle"), key=key)
