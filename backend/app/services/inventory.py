from datetime import timedelta
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select, or_, exists, func
from sqlalchemy.dialects.postgresql import Range
from app.models import Vehicle, VehiclePhoto, VehicleAllocation, RatePlan, FxRate, Branch
from app.schemas.inventory import InventoryFilters
from app.schemas.money import money
from app.services.audit import now, serialize
from app.core.errors import DomainError

async def release_expired(db, vehicle_ids):
    from sqlalchemy import update
    await db.execute(update(VehicleAllocation).where(VehicleAllocation.vehicle_id.in_(vehicle_ids),VehicleAllocation.status=="ACTIVE",VehicleAllocation.purpose=="HOLD",VehicleAllocation.expires_at<=now()).values(status="RELEASED"))

def inventory_statement(filters: InventoryFilters):
    query=select(Vehicle,RatePlan).join(RatePlan, Vehicle.rate_plan_id==RatePlan.id).join(Branch,Vehicle.branch_id==Branch.id).where(Vehicle.status=="ACTIVE",Branch.active.is_(True))
    for name, field in [("vehicle_type",Vehicle.vehicle_type),("class_code",Vehicle.class_code),("fuel_type",Vehicle.fuel_type),("transmission",Vehicle.transmission),("pickup_branch_id",Vehicle.branch_id)]:
        value=getattr(filters,name)
        if value is not None:query=query.where(field==value)
    if filters.minimum_seats:query=query.where(Vehicle.seats>=filters.minimum_seats)
    if filters.pickup_at:
        period=Range(filters.pickup_at,filters.return_at,bounds="[)")
        blocked=exists(select(VehicleAllocation.id).where(VehicleAllocation.vehicle_id==Vehicle.id,VehicleAllocation.status=="ACTIVE",VehicleAllocation.period.op("&&")(period),or_(VehicleAllocation.purpose!="HOLD",VehicleAllocation.expires_at>now())))
        query=query.where(~blocked)
    return query

async def search(db, filters: InventoryFilters, language="en"):
    query=inventory_statement(filters)
    # Rank after the pricing engine has evaluated every eligible vehicle. A
    # base-rate limit here could omit the actual cheapest car for these dates.
    candidates=(await db.execute(query.order_by(func.coalesce(Vehicle.daily_rate_qepik,RatePlan.daily_rate_qepik),Vehicle.id))).all()
    photos={}
    if candidates:
        rows=(await db.scalars(select(VehiclePhoto).where(VehiclePhoto.vehicle_id.in_([vehicle.id for vehicle,_ in candidates])).order_by(VehiclePhoto.sort_order,VehiclePhoto.id))).all()
        for photo in rows:photos.setdefault(photo.vehicle_id,photo)
    rate=Decimal(1)
    if filters.budget_amount is not None and filters.budget_currency=="USD":
        fx=await db.scalar(select(FxRate).where(FxRate.currency_code=="USD",FxRate.azn_per_unit>0).order_by(FxRate.effective_date.desc()).limit(1))
        if not fx:raise DomainError("FX_UNAVAILABLE","Use an AZN budget while exchange rates are unavailable",409)
        rate=fx.azn_per_unit
    cards=[]
    for vehicle,plan in candidates:
        photo=photos.get(vehicle.id)
        amount=vehicle.daily_rate_qepik if vehicle.daily_rate_qepik is not None else plan.daily_rate_qepik
        rental_amount=amount
        if filters.pickup_at:
            from app.services.pricing import calculate
            from app.schemas.bookings import Trip
            from app.models import RentalPolicy
            policy=await db.get(RentalPolicy,plan.rental_policy_id)
            if policy.published_at:
                _,_,_,rental_amount,_=await calculate(db,Trip(vehicle_id=vehicle.id,pickup_branch_id=vehicle.branch_id,return_branch_id=vehicle.branch_id,pickup_at=filters.pickup_at,return_at=filters.return_at,driver_age=policy.rules["minimum_driver_age"]))
            else:
                continue
        if filters.budget_amount is not None:
            # Dated budget matching uses the engine total, including seasonal
            # rates, mandatory fees and taxes; optional extras are quoted later.
            blocks=max(1, -(-int((filters.return_at-filters.pickup_at).total_seconds())//86400)) if filters.pickup_at else 1
            required=rental_amount if filters.budget_basis=="TOTAL" else Decimal(rental_amount)/blocks
            if required>filters.budget_amount*rate*100:continue
        cards.append({"type":"vehicle", "vehicle_id":str(vehicle.id),"title":f"{vehicle.make} {vehicle.model}","year":vehicle.model_year,
            "vehicle_type":vehicle.vehicle_type,"class_code":vehicle.class_code,"seats":vehicle.seats,"fuel_type":vehicle.fuel_type,"transmission":vehicle.transmission,
            "branch_id":str(vehicle.branch_id),"features":vehicle.features,"photo_url":f"/api/v1/assets/{photo.asset_key}" if photo else None,
            "daily_price":money(amount,language),"rental_price":money(rental_amount,language) if filters.pickup_at else None,"availability_checked":bool(filters.pickup_at),"best_fit":len(cards)==0})
    from app.services.search_ranking import actual_search_amount
    cards.sort(key=lambda card:(actual_search_amount(card),card["vehicle_id"]))
    for index,card in enumerate(cards):card["best_fit"]=index==0
    return cards
