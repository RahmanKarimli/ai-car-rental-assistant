import hmac
from uuid import UUID, uuid4
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import Range
from app.models import *
from app.core.errors import DomainError
from app.core.security import sign, digest, canonical, token
from app.core.config import settings
from app.services.audit import now, audit, serialize
from app.services.pricing import signature_payload
from app.services.drafts import release_draft, hold_resources
from app.schemas.bookings import Trip
from app.api.dependencies import reservation_access

async def booking_card(db,reservation,language):
    vehicle=await db.get(Vehicle,reservation.vehicle_id)
    branch=await db.get(Branch,reservation.pickup_branch_id)
    return {"type":"booking","reservation_id":str(reservation.id),"reference":reservation.public_reference,"status":reservation.status,
        "title":f"{vehicle.make} {vehicle.model}","pickup_at":reservation.pickup_at.isoformat(),"return_at":reservation.return_at.isoformat(),
        "location":branch.name_az if language=="az" else branch.name_en,
        "version":reservation.current_version,"total":__import__('app.schemas.money',fromlist=['money']).money(reservation.total_qepik,language),
        "deposit":__import__('app.schemas.money',fromlist=['money']).money(reservation.deposit_qepik,language),"payment_method":reservation.payment_method}

async def confirm(db,actor,conversation,draft_id,quote_id,expected_version,key):
    draft=await db.get(BookingDraft,draft_id,with_for_update=True)
    if not draft or draft.conversation_id!=conversation.id:raise DomainError("NOT_FOUND","Draft not found",404)
    if draft.quote_id!=quote_id:raise DomainError("QUOTE_MISMATCH","Confirm the exact displayed quote",409)
    if draft.status=="COMMITTED":
        version=await db.get(ReservationVersion,draft.committed_version_id)
        return await db.get(Reservation,version.reservation_id)
    if draft.status!="READY" or draft.expires_at<=now():raise DomainError("DRAFT_EXPIRED","Prepare a new quote and confirm again",409)
    if conversation.status!="ACTIVE":raise DomainError("HUMAN_HANDOFF","Administrator handling is active",409)
    quote=await db.get(Quote,draft.quote_id)
    items=(await db.scalars(select(QuoteItem).where(QuoteItem.quote_id==quote.id).order_by(QuoteItem.sort_order))).all()
    if not hmac.compare_digest(quote.signature,sign(signature_payload(quote,items),settings().secret(settings().quote_signing_key_file))):raise DomainError("QUOTE_INTEGRITY","Quote integrity could not be established",409)
    original=None
    if draft.reservation_id:
        await reservation_access(db,actor,draft.reservation_id,draft.action_kind)
        original=await db.get(Reservation,draft.reservation_id,with_for_update=True)
        if original.status!="CONFIRMED" or original.pickup_at<=now():raise DomainError("INVALID_RESERVATION","Administrator handling is required",409)
        if expected_version!=original.current_version or original.current_version!=draft.base_reservation_version:raise DomainError("VERSION_CONFLICT","Reservation changed; prepare a new draft",409)
    before=serialize(original) if original else None
    trip=Trip.model_validate(draft.proposal["trip"]) if draft.action_kind!="CANCEL" else None
    if trip:
        vehicle=await db.get(Vehicle,trip.vehicle_id)
        if vehicle.status!="ACTIVE" or trip.pickup_at<=now():raise DomainError("VEHICLE_UNAVAILABLE","Prepare a fresh draft",409)
        branch=await db.get(Branch,trip.pickup_branch_id)
        if not branch or not branch.active:raise DomainError("BRANCH_UNAVAILABLE","Pickup branch is unavailable",409)
        latest_plan=await db.get(RatePlan,vehicle.rate_plan_id)
        latest_policy=await db.get(RentalPolicy,latest_plan.rental_policy_id)
        if not latest_policy.published_at or trip.driver_age<latest_policy.rules["minimum_driver_age"]:raise DomainError("POLICY_CHANGED","Eligibility changed; prepare a new draft",409)
        # Refresh only resource checks. Prices remain frozen in the signed quote.
        await db.execute(update(VehicleAllocation).where(VehicleAllocation.draft_id==draft.id,VehicleAllocation.status=="ACTIVE").values(status="RELEASED"))
        await db.execute(update(ExtraAllocation).where(ExtraAllocation.draft_id==draft.id,ExtraAllocation.status=="ACTIVE").values(status="RELEASED"))
        await hold_resources(db,draft,trip,original)
    if original:
        await db.execute(update(VehicleAllocation).where(VehicleAllocation.reservation_id==original.id,VehicleAllocation.status=="ACTIVE").values(status="RELEASED"))
        await db.execute(update(ExtraAllocation).where(ExtraAllocation.reservation_id==original.id,ExtraAllocation.status=="ACTIVE").values(status="RELEASED"))
        reservation=original;reservation.current_version+=1
    else:
        reservation=Reservation(id=uuid4(),public_reference="AZ-"+token()[:10].upper(),conversation_id=conversation.id,
            vehicle_id=trip.vehicle_id,pickup_branch_id=trip.pickup_branch_id,return_branch_id=trip.return_branch_id,
            pickup_at=trip.pickup_at,return_at=trip.return_at,total_qepik=quote.total_qepik,deposit_qepik=quote.deposit_qepik,
            renter_contact=draft.proposal["contact"],current_version=1,updated_at=now())
        db.add(reservation);await db.flush()
        db.add(BookingAccessGrant(session_id=actor.id,reservation_id=reservation.id))
    if draft.action_kind=="CANCEL":reservation.status="CANCELLED"
    else:
        reservation.vehicle_id=trip.vehicle_id;reservation.pickup_branch_id=trip.pickup_branch_id;reservation.return_branch_id=trip.return_branch_id
        reservation.pickup_at=trip.pickup_at;reservation.return_at=trip.return_at;reservation.renter_contact=draft.proposal["contact"]
        await db.execute(update(VehicleAllocation).where(VehicleAllocation.draft_id==draft.id,VehicleAllocation.status=="ACTIVE").values(status="RELEASED"))
        await db.execute(update(ExtraAllocation).where(ExtraAllocation.draft_id==draft.id,ExtraAllocation.status=="ACTIVE").values(status="RELEASED"))
        db.add(VehicleAllocation(vehicle_id=trip.vehicle_id,period=Range(trip.pickup_at,trip.return_at,bounds="[)"),purpose="RESERVATION",reservation_id=reservation.id))
        for extra in trip.extras:
            db.add(ExtraAllocation(extra_id=extra.extra_id,period=Range(trip.pickup_at,trip.return_at,bounds="[)"),quantity=extra.quantity,reservation_id=reservation.id))
    reservation.total_qepik=quote.total_qepik;reservation.deposit_qepik=quote.deposit_qepik;reservation.updated_at=now()
    await db.flush()
    snapshot={**serialize(reservation),"trip":draft.proposal.get("trip"),"policy":quote.policy_snapshot,"items":[serialize(i) for i in items]}
    version=ReservationVersion(id=uuid4(),reservation_id=reservation.id,version=reservation.current_version,action_kind=draft.action_kind,quote_id=quote.id,snapshot=snapshot,actor_type=actor.actor_type,actor_id=actor.admin_user_id or actor.id)
    db.add(version);await db.flush()
    adjustment_id=quote.inputs_snapshot.get("approved_adjustment_id")
    if adjustment_id:
        adjustment=await db.get(ApprovedAdjustment,UUID(adjustment_id),with_for_update=True)
        if adjustment.consumed_by_version_id or adjustment.expires_at<=now():raise DomainError("ADJUSTMENT_EXPIRED","Administrator adjustment requires renewed approval",409)
        adjustment.consumed_by_version_id=version.id
    draft.status="COMMITTED";draft.committed_version_id=version.id;conversation.active_draft_id=None
    conversation.session_state={**conversation.session_state,"phase":"BOOKED","reservation_id":str(reservation.id)}
    audit(db,actor,"RESERVATION_"+draft.action_kind,reservation,key,before=before,after=snapshot)
    db.add(ConversionEvent(conversation_id=conversation.id,event_name="BOOKING_"+draft.action_kind,attributes={"reservation_id":str(reservation.id)}))
    db.add(IdempotencyRecord(session_id=actor.id,key=key,operation="CONFIRM",request_hash=digest(canonical({"draft_id":str(draft_id),"quote_id":str(quote_id),"version":expected_version})),result_reference={"reservation_id":str(reservation.id)}))
    return reservation
