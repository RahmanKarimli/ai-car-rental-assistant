from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4
from sqlalchemy import select
from app.models import RatePlan, RentalPolicy, PricingRule, Extra, FxRate, Quote, QuoteItem, Vehicle, Branch, ApprovedAdjustment
from app.core.config import settings
from app.core.errors import DomainError
from app.core.security import sign
from app.schemas.bookings import Trip
from app.schemas.money import money, usd
from app.services.audit import now

def rounded(value):return int(Decimal(value).quantize(Decimal(1),rounding=ROUND_HALF_UP))
def signature_payload(q, items):
    return {"id":str(q.id),"inputs":q.inputs_snapshot,"policy":q.policy_snapshot,"total":q.total_qepik,"deposit":q.deposit_qepik,
        "delta":q.delta_qepik,"valid_until":q.valid_until.isoformat(),"items":[{"code":i.code,"quantity":i.quantity,"unit":i.unit_amount_qepik,"total":i.line_total_qepik,"rule":i.rule_reference} for i in items]}

async def calculate(db, trip: Trip, original=None, action="CREATE", adjustment=None):
    vehicle=await db.get(Vehicle,trip.vehicle_id)
    if not vehicle or vehicle.status!="ACTIVE":raise DomainError("VEHICLE_UNAVAILABLE","Vehicle is unavailable",409)
    plan=await db.get(RatePlan,vehicle.rate_plan_id)
    policy=await db.get(RentalPolicy,plan.rental_policy_id)
    if not policy.published_at:raise DomainError("POLICY_NOT_PUBLISHED","The operator must publish reviewed rental terms",409)
    rules=policy.rules
    if trip.driver_age<rules["minimum_driver_age"]:raise DomainError("DRIVER_INELIGIBLE","Driver does not meet the published age requirement",409)
    if trip.pickup_branch_id!=vehicle.branch_id:raise DomainError("BRANCH_MISMATCH","Vehicle is located at a different branch",409)
    branch=await db.get(Branch,trip.pickup_branch_id)
    if not branch or not branch.active:raise DomainError("BRANCH_UNAVAILABLE","Pickup branch is unavailable",409)
    if trip.return_branch_id!=trip.pickup_branch_id:raise DomainError("OUT_OF_STATE_DROPOFF","A different drop-off location needs administrator handling",409)
    if trip.pickup_at<=now():raise DomainError("INVALID_DATES","Pickup must be in the future")
    seconds=int((trip.return_at-trip.pickup_at).total_seconds())
    days=max(1,(seconds+86399)//86400)
    if days>rules["maximum_rental_days"]:raise DomainError("RENTAL_TOO_LONG","The requested trip exceeds the published rental limit")
    items=[]
    def add(code,az,en,quantity,unit,ref=None):
        items.append(dict(code=code,label_az=az,label_en=en,quantity=quantity,unit_amount_qepik=unit,line_total_qepik=quantity*unit,rule_reference=ref or {}))
    seasonal=(await db.scalars(select(PricingRule).where(PricingRule.rate_plan_id==plan.id))).all()
    for day in range(days):
        date=(trip.pickup_at+timedelta(days=day)).astimezone(__import__('zoneinfo').ZoneInfo(settings().app_timezone)).date()
        overrides=[r for r in seasonal if r.kind=="SEASONAL_DAILY" and r.effective_dates and date in r.effective_dates]
        if len(overrides)>1:raise DomainError("AMBIGUOUS_PRICING","Pricing configuration needs administrator attention",409)
        value=overrides[0].amount_qepik if overrides else (vehicle.daily_rate_qepik if vehicle.daily_rate_qepik is not None else plan.daily_rate_qepik)
        add(f"RENTAL_{day+1}",f"İcarə — gün {day+1}",f"Rental — day {day+1}",1,value,{"rate_plan_id":str(plan.id),"vehicle_price_override":vehicle.daily_rate_qepik is not None,"seasonal_rule_id":str(overrides[0].id) if overrides else None})
    for rule in seasonal:
        if rule.kind=="FIXED_FEE":add("FEE","İcarə haqqı","Rental fee",1,rule.amount_qepik,{"rule_id":str(rule.id)})
    extra_snapshots=[]
    for selection in trip.extras:
        extra=await db.get(Extra,selection.extra_id)
        if not extra or not extra.active:raise DomainError("EXTRA_UNAVAILABLE","Selected extra is unavailable",409)
        allowed=extra.eligibility_rules.get("vehicle_classes")
        if allowed and vehicle.class_code not in allowed:raise DomainError("EXTRA_INELIGIBLE","Extra is incompatible with the vehicle")
        units=selection.quantity*(days if extra.billing_unit=="PER_DAY" else 1)
        add(extra.code,extra.name_az,extra.name_en,units,extra.price_qepik,{"extra_id":str(extra.id)})
        extra_snapshots.append({"extra_id":str(extra.id),"quantity":selection.quantity})
    if action=="MODIFY":add("MODIFICATION","Dəyişiklik haqqı","Modification fee",1,rules["modification_fee_qepik"])
    if adjustment:
        add("ADMIN_ADJUSTMENT","Təsdiqlənmiş düzəliş","Approved adjustment",1,adjustment.amount_qepik,{"adjustment_id":str(adjustment.id)})
    subtotal=sum(i["line_total_qepik"] for i in items)
    if subtotal<0:raise DomainError("INVALID_ADJUSTMENT","Adjustment exceeds the rental charges")
    if plan.tax_mode=="EXCLUSIVE" and plan.tax_basis_points:
        tax=rounded(Decimal(subtotal)*plan.tax_basis_points/10000)
        add("TAX","Vergi","Tax",1,tax,{"basis_points":plan.tax_basis_points})
    return plan,policy,items,sum(i["line_total_qepik"] for i in items),plan.deposit_qepik

async def create_quote(db, conversation, trip, key, original=None, action="CREATE", adjustment=None):
    existing=await db.scalar(select(Quote).where(Quote.operation_key==key))
    if existing:return existing
    if action=="CANCEL":
        version=await db.scalar(select(__import__('app.models',fromlist=['ReservationVersion']).ReservationVersion).where(__import__('app.models',fromlist=['ReservationVersion']).ReservationVersion.reservation_id==original.id).order_by(__import__('app.models',fromlist=['ReservationVersion']).ReservationVersion.version.desc()).limit(1))
        old_quote=await db.get(Quote,version.quote_id)
        plan=await db.get(RatePlan,old_quote.rate_plan_id)
        policy_snapshot=old_quote.policy_snapshot
        hours=(original.pickup_at-now()).total_seconds()/3600
        fee=0 if hours>=policy_snapshot["rules"]["cancellation_free_hours"] else policy_snapshot["rules"]["cancellation_fee_qepik"]
        items=[dict(code="CANCELLATION",label_az="Ləğv haqqı",label_en="Cancellation fee",quantity=1,unit_amount_qepik=fee,line_total_qepik=fee,rule_reference={})]
        total,deposit=fee,0
        inputs={"reservation_id":str(original.id),"base_version":original.current_version}
    else:
        # Match the booking allocation lock order: vehicles, then all affected extras.
        # Search estimates remain read-only; durable quotes retain product references.
        vehicle_ids=sorted({trip.vehicle_id,original.vehicle_id} if original else {trip.vehicle_id})
        await db.execute(select(Vehicle).where(Vehicle.id.in_(vehicle_ids)).order_by(Vehicle.id).with_for_update().execution_options(populate_existing=True))
        old_extra_ids=[]
        if original:
            from app.models import ExtraAllocation
            old_extra_ids=(await db.scalars(select(ExtraAllocation.extra_id).where(ExtraAllocation.reservation_id==original.id,ExtraAllocation.status=="ACTIVE"))).all()
        extra_ids=sorted({selection.extra_id for selection in trip.extras}|set(old_extra_ids))
        if extra_ids:await db.execute(select(Extra).where(Extra.id.in_(extra_ids)).order_by(Extra.id).with_for_update().execution_options(populate_existing=True))
        plan,policy,items,total,deposit=await calculate(db,trip,original,action,adjustment)
        policy_snapshot={"id":str(policy.id),"version":policy.version,"rules":policy.rules,"bundle":policy.policy_bundle_key}
        inputs=trip.model_dump(mode="json")
        if adjustment:inputs["approved_adjustment_id"]=str(adjustment.id)
    fx=await db.scalar(select(FxRate).where(FxRate.currency_code=="USD").order_by(FxRate.effective_date.desc()).limit(1))
    quote=Quote(id=uuid4(),conversation_id=conversation.id,action_kind=action,reservation_id=original.id if original else None,
        inputs_snapshot=inputs,policy_snapshot=policy_snapshot,rate_plan_id=plan.id,fx_rate_id=fx.id if fx else None,
        total_qepik=total,deposit_qepik=deposit,delta_qepik=total-original.total_qepik if original else None,
        signature="",valid_until=now()+timedelta(seconds=min(settings().quote_ttl_seconds,settings().hold_ttl_seconds)),operation_key=key)
    rows=[QuoteItem(id=uuid4(),quote_id=quote.id,sort_order=n,**item) for n,item in enumerate(items)]
    signing_key=settings().secret(settings().quote_signing_key_file)
    if len(signing_key)<32:raise DomainError("SIGNING_KEY_MISSING","Configure the quote signing secret",503)
    quote.signature=sign(signature_payload(quote,rows),signing_key)
    db.add(quote);await db.flush();db.add_all(rows);await db.flush()
    return quote

async def quote_card(db, quote, language, draft=None):
    items=(await db.scalars(select(QuoteItem).where(QuoteItem.quote_id==quote.id).order_by(QuoteItem.sort_order))).all()
    fx=await db.get(FxRate,quote.fx_rate_id) if quote.fx_rate_id else None
    trip_summary=None
    from app.models import Branch,Reservation
    inputs=quote.inputs_snapshot
    if inputs.get("vehicle_id"):
        v=await db.get(Vehicle,UUID(inputs["vehicle_id"]))
        branch=await db.get(Branch,UUID(inputs["pickup_branch_id"]))
        trip_summary={"vehicle":f"{v.make} {v.model}","pickup_at":inputs["pickup_at"],"return_at":inputs["return_at"],"location":branch.name_az if language=="az" else branch.name_en}
    elif quote.reservation_id:
        r=await db.get(Reservation,quote.reservation_id);v=await db.get(Vehicle,r.vehicle_id);branch=await db.get(Branch,r.pickup_branch_id)
        trip_summary={"vehicle":f"{v.make} {v.model}","pickup_at":r.pickup_at.isoformat(),"return_at":r.return_at.isoformat(),"location":branch.name_az if language=="az" else branch.name_en}
    return {"type":"quote","trip":trip_summary,"quote_id":str(quote.id),"draft_id":str(draft.id) if draft else None,"action_kind":quote.action_kind,
        "items":[{"label":i.label_az if language=="az" else i.label_en,"quantity":i.quantity,"amount":money(i.line_total_qepik,language)} for i in items],
        "total":money(quote.total_qepik,language),"deposit":money(quote.deposit_qepik,language),"delta":money(quote.delta_qepik,language) if quote.delta_qepik is not None else None,
        "usd_display":usd(quote.total_qepik,fx.azn_per_unit) if fx else None,"fx_date":str(fx.effective_date) if fx else None,
        "valid_until":quote.valid_until.isoformat(),"expected_reservation_version":draft.base_reservation_version if draft else None,
        "status":draft.status if draft else "ESTIMATE","payment_method":"PAY_AT_PICKUP"}
