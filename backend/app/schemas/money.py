from decimal import Decimal, ROUND_HALF_UP

def money(qepik: int, language: str = "en") -> dict:
    whole, minor = divmod(abs(qepik), 100)
    label = f"{'-' if qepik < 0 else ''}{whole:,}.{minor:02d} AZN"
    return {"currency":"AZN", "amount_qepik":str(qepik), "formatted":label}
def usd(qepik: int, rate: Decimal) -> str:
    value = (Decimal(qepik) / 100 / rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"≈ {value:,.2f} USD"
