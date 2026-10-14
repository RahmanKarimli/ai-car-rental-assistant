from uuid import UUID,uuid5,NAMESPACE_URL
from typing import Literal
from fastapi import APIRouter,Depends,Header,Query
from sqlalchemy import select
from app.api.dependencies import actor,database,own_conversation,reservation_access
from app.core.errors import DomainError
from app.models import *
from app.schemas.bookings import DraftRequest,ConfirmRequest
from app.schemas.chat import DraftEvent,ConfirmEvent
from app.schemas.inventory import InventoryFilters,InventoryPage,DisplayCurrencies
from app.services.inventory import search
from app.services.inventory_page import search_page,display_currencies
from app.services.conversations import process
from app.services.reservations import booking_card
from app.services.pricing import create_quote,quote_card
from app.services.audit import serialize
from app.db.locks import conversation_lock
router=APIRouter()
@router.get("/branches")
async def branches(db=Depends(database)):
    return [serialize(x) for x in (await db.scalars(select(Branch).where(Branch.active.is_(True)))).all()]
@router.get("/extras")
async def extras(db=Depends(database)):
    return [serialize(x) for x in (await db.scalars(select(Extra).where(Extra.active.is_(True)))).all()]
@router.get("/inventory")
async def inventory(filters:InventoryFilters=Depends(),language:str="en",db=Depends(database)):
    return await search(db,filters,language if language in {"az","en"} else "en")
@router.get("/inventory/page",response_model=InventoryPage)
async def inventory_page(filters:InventoryFilters=Depends(),language:Literal["en","az"]="en",page:int=Query(default=1,ge=1),page_size:int=Query(default=12,ge=1,le=24),sort:Literal["recommended","price-low","price-high","seats"]="recommended",vehicle_ids:list[UUID]|None=Query(default=None,max_length=200),db=Depends(database)):
    return await search_page(db,filters,language,page,page_size,sort,vehicle_ids)
@router.get("/display-currencies",response_model=DisplayCurrencies)
async def currencies(db=Depends(database)):
    return await display_currencies(db)
@router.post("/quotes")
async def quote(body:DraftRequest,key:str=Header(alias="Idempotency-Key",min_length=1,max_length=200),session=Depends(actor)):
    if body.action_kind!="CREATE" or not body.trip:raise DomainError("INVALID_QUOTE","Use modification/cancellation drafts for existing reservations")
    async with conversation_lock(body.conversation_id):
        from app.db.session import Session
        async with Session() as db,db.begin():
            c=await own_conversation(db,session,body.conversation_id)
            quote=await create_quote(db,c,body.trip,f"estimate:{session.id}:{key}")
            if quote.inputs_snapshot!=body.trip.model_dump(mode="json"):raise DomainError("IDEMPOTENCY_CONFLICT","Key reused with different trip",409)
            return await quote_card(db,quote,c.language)
async def draft_response(body,key,session):
    response=await process(session,body.conversation_id,DraftEvent(kind="PREPARE_DRAFT",client_event_id=uuid5(NAMESPACE_URL,f"draft:{session.id}:{key}"),draft=body))
    if response.get("error_code"):raise DomainError(response["error_code"],response["text"],409)
    return response
@router.post("/drafts")
async def draft(body:DraftRequest,key:str=Header(alias="Idempotency-Key",min_length=1,max_length=200),session=Depends(actor)):
    return await draft_response(body,key,session)
@router.get("/drafts/{id}")
async def get_draft(id:UUID,session=Depends(actor),db=Depends(database)):
    draft=await db.get(BookingDraft,id)
    if not draft:raise DomainError("NOT_FOUND","Draft not found",404)
    c=await own_conversation(db,session,draft.conversation_id)
    return await quote_card(db,await db.get(Quote,draft.quote_id),c.language,draft)
@router.post("/drafts/{id}/confirm")
async def confirmation(id:UUID,body:ConfirmRequest,key:str=Header(alias="Idempotency-Key",min_length=1,max_length=200),session=Depends(actor),db=Depends(database)):
    draft=await db.get(BookingDraft,id)
    if not draft:raise DomainError("NOT_FOUND","Draft not found",404)
    response=await process(session,draft.conversation_id,ConfirmEvent(kind="CONFIRM_DRAFT",client_event_id=uuid5(NAMESPACE_URL,f"confirm:{session.id}:{key}"),draft_id=id,quote_id=body.quote_id,expected_reservation_version=body.expected_reservation_version))
    if response.get("error_code"):raise DomainError(response["error_code"],response["text"],409)
    return response
@router.get("/reservations")
async def list_bookings(language:str="en",session=Depends(actor),db=Depends(database)):
    result=(await db.scalars(select(Reservation).join(BookingAccessGrant,BookingAccessGrant.reservation_id==Reservation.id).where(BookingAccessGrant.session_id==session.id,BookingAccessGrant.revoked_at.is_(None)).order_by(Reservation.created_at.desc()))).all()
    return [await booking_card(db,r,language if language in {"en","az"} else "en") for r in result]
@router.get("/reservations/{id}")
async def booking(id:UUID,language:str="en",session=Depends(actor),db=Depends(database)):
    await reservation_access(db,session,id);r=await db.get(Reservation,id)
    if not r:raise DomainError("NOT_FOUND","Reservation not found",404)
    version=await db.scalar(select(ReservationVersion).where(ReservationVersion.reservation_id==id,ReservationVersion.version==r.current_version))
    return {"card":await booking_card(db,r,language if language in {"en","az"} else "en"),"snapshot":version.snapshot}
@router.post("/reservations/{id}/{kind}-drafts")
async def change(id:UUID,kind:str,body:DraftRequest,key:str=Header(alias="Idempotency-Key",min_length=1,max_length=200),session=Depends(actor)):
    action={"modification":"MODIFY","cancellation":"CANCEL"}.get(kind)
    if not action or body.action_kind!=action or body.reservation_id!=id:raise DomainError("INVALID_ACTION","Action does not match reservation")
    return await draft_response(body,key,session)

@router.get("/policies/{chunk_id}")
async def policy_source(chunk_id:UUID,db=Depends(database)):
    from app.services.audit import now
    chunk=await db.get(PolicyChunk,chunk_id)
    doc=await db.get(PolicyDocument,chunk.document_id) if chunk else None
    if not doc or doc.status!="PUBLISHED" or doc.effective_from>now() or (doc.effective_until and doc.effective_until<=now()):
        raise DomainError("NOT_FOUND","Reviewed source is not currently published",404)
    return {"title":doc.document_key,"language":doc.language,"version":doc.version,"section":chunk.section_reference,"content":doc.full_text}
