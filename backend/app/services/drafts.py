from uuid import UUID, uuid4
from sqlalchemy import select, update, or_
from sqlalchemy.dialects.postgresql import Range
from app.models import *
from app.schemas.bookings import DraftRequest, Trip
from app.services.audit import now, audit
from app.services.pricing import create_quote
from app.services.inventory import release_expired
from app.api.dependencies import reservation_access
from app.core.errors import DomainError

async def get_original(db, actor, request):
    if request.action_kind=="CREATE":return None
    if not request.reservation_id:raise DomainError("RESERVATION_REQUIRED","Select a reservation")
    await reservation_access(db,actor,request.reservation_id,request.action_kind)
    original=await db.get(Reservation,request.reservation_id,with_for_update=True)
    if not original or original.status!="CONFIRMED":raise DomainError("INVALID_RESERVATION","Only confirmed future reservations can be changed",409)
    if original.pickup_at<=now():raise DomainError("PICKUP_STARTED","An administrator must handle changes after pickup",409)
    if request.expected_reservation_version!=original.current_version:raise DomainError("VERSION_CONFLICT","The reservation changed. Refresh before proposing changes.",409)
    return original

async def release_draft(db, id, status="SUPERSEDED"):
    await db.execute(update(VehicleAllocation).where(VehicleAllocation.draft_id==id,VehicleAllocation.status=="ACTIVE").values(status="RELEASED"))
    await db.execute(update(ExtraAllocation).where(ExtraAllocation.draft_id==id,ExtraAllocation.status=="ACTIVE").values(status="RELEASED"))
    await db.execute(update(BookingDraft).where(BookingDraft.id==id,BookingDraft.status=="READY").values(status=status))

def difference(start,end,old_start,old_end):
    if old_end<=start or old_start>=end:return [(start,end)]
    result=[]
    if start<old_start:result.append((start,old_start))
    if end>old_end:result.append((old_end,end))
    return result

async def hold_resources(db, draft, trip, original):
    ids=sorted({trip.vehicle_id, original.vehicle_id} if original else {trip.vehicle_id})
    await db.execute(select(Vehicle).where(Vehicle.id.in_(ids)).order_by(Vehicle.id).with_for_update())
    await release_expired(db,ids)
    period=Range(trip.pickup_at,trip.return_at,bounds="[)")
    conflict=select(VehicleAllocation.id).where(VehicleAllocation.vehicle_id==trip.vehicle_id,VehicleAllocation.status=="ACTIVE",VehicleAllocation.period.op("&&")(period))
    if original:conflict=conflict.where(or_(VehicleAllocation.reservation_id.is_(None),VehicleAllocation.reservation_id!=original.id))
    if await db.scalar(conflict.limit(1)):raise DomainError("VEHICLE_UNAVAILABLE","Vehicle has just become unavailable",409)
    windows=difference(trip.pickup_at,trip.return_at,original.pickup_at,original.return_at) if original and original.vehicle_id==trip.vehicle_id else [(trip.pickup_at,trip.return_at)]
    for start,end in windows:
        db.add(VehicleAllocation(vehicle_id=trip.vehicle_id,period=Range(start,end,bounds="[)"),purpose="HOLD",draft_id=draft.id,expires_at=draft.expires_at))
    old=[]
    if original:
        old=(await db.scalars(select(ExtraAllocation).where(ExtraAllocation.reservation_id==original.id,ExtraAllocation.status=="ACTIVE"))).all()
    old_by={x.extra_id:x for x in old}
    all_extra_ids=sorted({x.extra_id for x in trip.extras}|set(old_by))
    if all_extra_ids:await db.execute(select(Extra).where(Extra.id.in_(all_extra_ids)).order_by(Extra.id).with_for_update())
    await db.execute(update(ExtraAllocation).where(ExtraAllocation.extra_id.in_(all_extra_ids),ExtraAllocation.status=="ACTIVE",ExtraAllocation.expires_at<=now()).values(status="RELEASED"))
    for selected in trip.extras:
        extra=await db.get(Extra,selected.extra_id)
        if extra.stock_total is None:continue
        allocations=(await db.scalars(select(ExtraAllocation).where(ExtraAllocation.extra_id==extra.id,ExtraAllocation.status=="ACTIVE",ExtraAllocation.period.op("&&")(period)))).all()
        # Check peak concurrent usage, excluding the customer's existing booking.
        points=[(trip.pickup_at,selected.quantity),(trip.return_at,-selected.quantity)]
        for allocation in allocations:
            if original and allocation.reservation_id==original.id:continue
            points += [(max(trip.pickup_at,allocation.period.lower),allocation.quantity),(min(trip.return_at,allocation.period.upper),-allocation.quantity)]
        count=0
        for moment,change in sorted(points,key=lambda x:(x[0],x[1])):
            count+=change
            if count>extra.stock_total:raise DomainError("EXTRA_UNAVAILABLE","Selected extra has insufficient stock",409)
        previous=old_by.get(extra.id)
        if previous:
            for a,b in difference(trip.pickup_at,trip.return_at,previous.period.lower,previous.period.upper):
                db.add(ExtraAllocation(extra_id=extra.id,period=Range(a,b,bounds="[)"),quantity=selected.quantity,draft_id=draft.id,expires_at=draft.expires_at))
            a,b=max(trip.pickup_at,previous.period.lower),min(trip.return_at,previous.period.upper)
            if a<b and selected.quantity>previous.quantity:
                db.add(ExtraAllocation(extra_id=extra.id,period=Range(a,b,bounds="[)"),quantity=selected.quantity-previous.quantity,draft_id=draft.id,expires_at=draft.expires_at))
        else:db.add(ExtraAllocation(extra_id=extra.id,period=period,quantity=selected.quantity,draft_id=draft.id,expires_at=draft.expires_at))
    await db.flush()

async def prepare(db, actor, conversation, request: DraftRequest, key):
    previous=await db.scalar(select(BookingDraft).where(BookingDraft.operation_key==key))
    if previous:return previous
    if conversation.status!="ACTIVE":raise DomainError("HUMAN_HANDOFF","An administrator is handling this request",409)
    original=await get_original(db,actor,request)
    if request.action_kind!="CANCEL" and not request.trip:raise DomainError("TRIP_REQUIRED","Complete trip details")
    if request.action_kind=="CREATE" and not request.contact:raise DomainError("CONTACT_REQUIRED","Provide name and phone")
    if conversation.active_draft_id:await release_draft(db,conversation.active_draft_id)
    adjustment=None
    if request.action_kind!="CANCEL":
        adjustment=await db.scalar(select(ApprovedAdjustment).where(ApprovedAdjustment.conversation_id==conversation.id,ApprovedAdjustment.consumed_by_version_id.is_(None),ApprovedAdjustment.expires_at>now(),ApprovedAdjustment.reservation_id== (original.id if original else None)).order_by(ApprovedAdjustment.created_at.desc()).limit(1))
    quote=await create_quote(db,conversation,request.trip,key+":quote",original,request.action_kind,adjustment)
    proposal=request.model_dump(mode="json")
    if original and not proposal["contact"]:proposal["contact"]=original.renter_contact
    draft=BookingDraft(id=uuid4(),conversation_id=conversation.id,quote_id=quote.id,action_kind=request.action_kind,
        reservation_id=original.id if original else None,base_reservation_version=original.current_version if original else None,
        proposal=proposal,expires_at=quote.valid_until,operation_key=key)
    db.add(draft);await db.flush()
    if request.trip and request.action_kind!="CANCEL":await hold_resources(db,draft,request.trip,original)
    conversation.active_draft_id=draft.id
    conversation.session_state={**conversation.session_state,"phase":"AWAITING_CONFIRMATION"}
    if request.contact:
        conversation.contact_name=request.contact.name;conversation.contact_phone=request.contact.phone;conversation.contact_email=request.contact.email
    db.add(ConversionEvent(conversation_id=conversation.id,event_name="DRAFT_CREATED",attributes={"action":draft.action_kind}))
    audit(db,actor,"DRAFT_CREATED",draft,key,after={"quote_id":str(quote.id),"action":draft.action_kind})
    return draft
