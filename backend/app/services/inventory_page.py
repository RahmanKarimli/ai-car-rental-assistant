"""Paged public fleet browsing. Quotes and contract amounts remain in AZN."""
from decimal import Decimal
from sqlalchemy import select, func
from app.models import Vehicle, VehiclePhoto, RatePlan, RentalPolicy, FxRate
from app.schemas.bookings import Trip
from app.schemas.money import money
from app.services.inventory import inventory_statement
from app.services.pricing import calculate
from app.core.errors import DomainError


async def display_currencies(db):
    fx = await db.scalar(select(FxRate).where(FxRate.currency_code == "USD", FxRate.azn_per_unit > 0).order_by(FxRate.effective_date.desc()).limit(1))
    return {"base_currency": "AZN", "usd": {"available": fx is not None, "azn_per_unit": str(fx.azn_per_unit) if fx else None, "effective_date": str(fx.effective_date) if fx else None, "source": "CBAR"}}


async def rental_amount(db, vehicle, policy, filters, daily):
    if not filters.pickup_at:
        return daily
    _, _, _, amount, _ = await calculate(db, Trip(vehicle_id=vehicle.id, pickup_branch_id=vehicle.branch_id, return_branch_id=vehicle.branch_id, pickup_at=filters.pickup_at, return_at=filters.return_at, driver_age=policy.rules["minimum_driver_age"]))
    return amount


async def search_page(db, filters, language, page, page_size, sort, vehicle_ids):
    query = inventory_statement(filters).add_columns(RentalPolicy).join(RentalPolicy, RentalPolicy.id == RatePlan.rental_policy_id)
    if filters.pickup_at:
        query = query.where(RentalPolicy.published_at.is_not(None))
    if vehicle_ids is not None:
        query = query.where(Vehicle.id.in_(vehicle_ids))
    daily = func.coalesce(Vehicle.daily_rate_qepik, RatePlan.daily_rate_qepik)
    budget_limit = None
    if filters.budget_amount is not None:
        rate = Decimal(1)
        if filters.budget_currency == "USD":
            fx = await display_currencies(db)
            if not fx["usd"]["available"]:
                raise DomainError("FX_UNAVAILABLE", "Use an AZN budget while exchange rates are unavailable", 409)
            rate = Decimal(fx["usd"]["azn_per_unit"])
        budget_limit = filters.budget_amount * rate * 100
        if not filters.pickup_at:
            query = query.where(daily <= budget_limit)

    # Dated budgets and dated price ordering must use the pricing engine's exact
    # seasonal/tax result across matches, before selecting a page. Photos and
    # full response cards are fetched only for that page.
    priced = bool(filters.pickup_at and (budget_limit is not None or sort in {"price-low", "price-high"}))
    if priced:
        eligible = []
        blocks = max(1, -(-int((filters.return_at - filters.pickup_at).total_seconds()) // 86400))
        for vehicle, plan, policy in (await db.execute(query.order_by(daily, Vehicle.id))).all():
            base = vehicle.daily_rate_qepik if vehicle.daily_rate_qepik is not None else plan.daily_rate_qepik
            amount = await rental_amount(db, vehicle, policy, filters, base)
            required = amount if filters.budget_basis == "TOTAL" else Decimal(amount) / blocks
            if budget_limit is not None and required > budget_limit:
                continue
            eligible.append((vehicle, plan, policy, base, amount))
        if sort in {"price-low", "price-high"}:
            eligible.sort(key=lambda row: ((-row[4] if sort == "price-high" else row[4]), str(row[0].id)))
        elif sort == "seats":
            eligible.sort(key=lambda row: (-row[0].seats, row[3], str(row[0].id)))
        total = len(eligible)
        pages = max(1, (total + page_size - 1) // page_size)
        page = min(page, pages)
        rows = eligible[(page - 1) * page_size:page * page_size]
    else:
        total = await db.scalar(select(func.count()).select_from(query.subquery()))
        pages = max(1, (total + page_size - 1) // page_size)
        page = min(page, pages)
        order = [Vehicle.seats.desc(), daily, Vehicle.id] if sort == "seats" else [daily.desc(), Vehicle.id] if sort == "price-high" else [daily, Vehicle.id]
        selected = (await db.execute(query.order_by(*order).offset((page - 1) * page_size).limit(page_size))).all()
        rows = []
        for vehicle, plan, policy in selected:
            base = vehicle.daily_rate_qepik if vehicle.daily_rate_qepik is not None else plan.daily_rate_qepik
            rows.append((vehicle, plan, policy, base, await rental_amount(db, vehicle, policy, filters, base)))

    photos = {}
    if rows:
        for photo in (await db.scalars(select(VehiclePhoto).where(VehiclePhoto.vehicle_id.in_([row[0].id for row in rows])).order_by(VehiclePhoto.sort_order, VehiclePhoto.id))).all():
            photos.setdefault(photo.vehicle_id, photo)
    cards = []
    for index, (vehicle, plan, policy, base, amount) in enumerate(rows):
        photo = photos.get(vehicle.id)
        cards.append({"type": "vehicle", "vehicle_id": str(vehicle.id), "title": f"{vehicle.make} {vehicle.model}", "year": vehicle.model_year,
                      "vehicle_type": vehicle.vehicle_type, "class_code": vehicle.class_code, "seats": vehicle.seats, "fuel_type": vehicle.fuel_type, "transmission": vehicle.transmission,
                      "branch_id": str(vehicle.branch_id), "features": vehicle.features, "photo_url": f"/api/v1/assets/{photo.asset_key}" if photo else None,
                      "daily_price": money(base, language), "rental_price": money(amount, language) if filters.pickup_at else None,
                      "availability_checked": bool(filters.pickup_at), "best_fit": sort == "recommended" and page == 1 and index == 0})
    return {"items": cards, "total": total, "page": page, "page_size": page_size, "pages": pages}
