from uuid import UUID,uuid4
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter,Depends,UploadFile,File,Form
from sqlalchemy import select,func,text,update
from app.api.dependencies import administrator,staff,database
from app.models import *
from app.schemas.admin import *
from app.services.audit import now,audit,serialize
from app.services.policies import ingest
from app.providers.filesystem import assets
from app.core.errors import DomainError
from app.core.config import settings
from app.db.locks import conversation_lock
from app.db.session import Session
from app.services.admin_data import create_record,update_record,delete_record,record_data
from app.schemas.catalog import PhotoInput
router=APIRouter(prefix="/admin")
CATALOG={"branches":Branch,"vehicles":Vehicle,"extras":Extra,"rates":RatePlan,"rules":PricingRule,"rental-policies":RentalPolicy,"photos":VehiclePhoto}
@router.get("/catalog/{kind}")
async def catalog(kind:str,session=Depends(administrator),db=Depends(database)):
    model=CATALOG.get(kind)
    if not model:raise DomainError("NOT_FOUND","Catalog not found",404)
    rows=(await db.scalars(select(model).order_by(model.created_at.desc()).limit(200))).all()
    result=[]
    for row in rows:
        item=serialize(row)
        if kind=="rules":item["effective_dates"]=str(row.effective_dates) if row.effective_dates else None
        result.append(item)
    return result
CATALOG_TABLES={key:model.__tablename__ for key,model in CATALOG.items()}
@router.get("/catalog/{kind}/{id}")
async def catalog_record(kind:str,id:UUID,session=Depends(administrator),db=Depends(database)):
    model=CATALOG.get(kind)
    row=await db.get(model,id) if model else None
    if not row:raise DomainError("NOT_FOUND","Catalog record not found",404)
    return record_data(row)
@router.post("/catalog/{kind}")
async def add_catalog(kind:str,body:dict,session=Depends(administrator),db=Depends(database)):
    table=CATALOG_TABLES.get(kind)
    if not table:raise DomainError("NOT_FOUND","Catalog not found",404)
    return await create_record(db,session,table,body)
@router.patch("/catalog/{kind}/{id}")
async def edit_catalog(kind:str,id:UUID,body:dict,session=Depends(administrator),db=Depends(database)):
    table=CATALOG_TABLES.get(kind)
    if not table:raise DomainError("NOT_FOUND","Catalog not found",404)
    return await update_record(db,session,table,id,body)
@router.delete("/catalog/{kind}/{id}")
async def remove_catalog(kind:str,id:UUID,session=Depends(administrator),db=Depends(database)):
    table=CATALOG_TABLES.get(kind)
    if not table:raise DomainError("NOT_FOUND","Catalog not found",404)
    return await delete_record(db,session,table,id)
@router.post("/vehicles/{id}/photos")
async def photo(id:UUID,file:UploadFile=File(),alt_az:str|None=Form(default=None),alt_en:str|None=Form(default=None),sort_order:int=Form(default=0,ge=0,le=10000),session=Depends(administrator),db=Depends(database)):
    vehicle=await db.get(Vehicle,id)
    if not vehicle:raise DomainError("NOT_FOUND","Vehicle not found",404)
    content=await file.read(5000001)
    if len(content)>5000000:raise DomainError("ASSET_TOO_LARGE","Maximum image size is 5 MB")
    extension="png" if content.startswith(b'\x89PNG\r\n\x1a\n') else "jpg" if content.startswith(b'\xff\xd8\xff') else "webp" if content.startswith(b'RIFF') and content[8:12]==b'WEBP' else None
    if not extension:raise DomainError("INVALID_IMAGE","Use PNG, JPEG or WebP")
    from pydantic import ValidationError
    try:values=PhotoInput(vehicle_id=id,alt_az=alt_az or f"{vehicle.make} {vehicle.model}",alt_en=alt_en or f"{vehicle.make} {vehicle.model}",sort_order=sort_order).model_dump()
    except ValidationError:raise DomainError("INVALID_FIELDS","Photo captions must be 1–1000 characters and display order must be nonnegative",422)
    key=f"vehicles/{id}/{uuid4()}.{extension}";assets.put(key,content)
    row=VehiclePhoto(asset_key=key,**values);db.add(row);await db.flush()
    audit(db,session,"ADMIN_RECORD_CREATED",row,uuid4(),after=record_data(row));await db.commit();return record_data(row)
@router.get("/policies")
async def policies(session=Depends(administrator),db=Depends(database)):
    return [serialize(x) for x in (await db.scalars(select(PolicyDocument).order_by(PolicyDocument.created_at.desc()))).all()]
@router.post("/policies")
async def upload(body:PolicyUpload,session=Depends(administrator),db=Depends(database)):
    return await create_record(db,session,"policy_documents",{
        "document_key":body.document_key,"topic":body.topic,"language":body.language,
        "version":body.version,"full_text":body.content,"effective_from":body.effective_from,
    })
@router.post("/policies/{id}/publish")
async def publish(id:UUID,session=Depends(administrator),db=Depends(database)):
    source=await db.get(PolicyDocument,id)
    if not source:raise DomainError("NOT_FOUND","Policy not found",404)
    documents=(await db.scalars(select(PolicyDocument).where(PolicyDocument.document_key==source.document_key,PolicyDocument.version==source.version).order_by(PolicyDocument.id).with_for_update().execution_options(populate_existing=True))).all()
    document=next((d for d in documents if d.id==id),None)
    pair=next((d for d in documents if d.id!=id),None)
    if not document:raise DomainError("NOT_FOUND","Policy draft changed or was deleted. Refresh and retry.",409)
    if not pair or {d.language for d in documents}!={"az","en"}:raise DomainError("TRANSLATION_REQUIRED","Upload both Azerbaijani and English versions",409)
    if any(d.status!="DRAFT" for d in documents):raise DomainError("PUBLISHED_POLICY","This pair is already published or retired. Create a new version.",409)
    if document.branch_id!=pair.branch_id:
        raise DomainError("POLICY_SCOPE_MISMATCH","Both language documents must apply to the same branch.",409)
    await ingest(db,document);await ingest(db,pair)
    for d in [document,pair]:
        await db.execute(update(PolicyDocument).where(PolicyDocument.document_key==d.document_key,PolicyDocument.language==d.language,PolicyDocument.status=="PUBLISHED",PolicyDocument.id!=d.id).values(status="RETIRED"))
        d.status="PUBLISHED";d.reviewed_by=session.admin_user_id;d.reviewed_at=now();audit(db,session,"POLICY_PUBLISHED",d,uuid4(),after={"version":d.version,"language":d.language})
    await db.commit();return {"published":True}
@router.post("/rental-policies")
async def publish_rules(body:PublishRules,session=Depends(administrator),db=Depends(database)):
    docs=(await db.scalars(select(PolicyDocument).where(PolicyDocument.document_key==body.bundle_key,PolicyDocument.version==body.version,PolicyDocument.status=="PUBLISHED"))).all()
    if {d.language for d in docs}!={"az","en"}:raise DomainError("POLICY_NOT_PUBLISHED","Publish the matching bilingual document bundle first",409)
    row=RentalPolicy(version=body.version,rules=body.rules.model_dump(),policy_bundle_key=body.bundle_key,published_by=session.admin_user_id,published_at=now());db.add(row);await db.flush()
    audit(db,session,"RENTAL_RULES_PUBLISHED",row,uuid4(),after=serialize(row));await db.commit();return serialize(row)
async def assigned_access(db,session,conversation_id):
    user=await db.get(AdminUser,session.admin_user_id)
    if user.role=="ADMIN":return
    case=await db.scalar(select(EscalationCase.id).where(EscalationCase.conversation_id==conversation_id,EscalationCase.assigned_admin_id==user.id,EscalationCase.status=="ASSIGNED"))
    if not case:raise DomainError("FORBIDDEN","This conversation is not assigned to you",403)
@router.get("/conversations")
async def conversations(session=Depends(administrator),db=Depends(database)):
    return [serialize(x) for x in (await db.scalars(select(Conversation).order_by(Conversation.last_activity_at.desc()).limit(200))).all()]
@router.get("/conversations/{id}")
async def transcript(id:UUID,after:int=0,session=Depends(staff),db=Depends(database)):
    await assigned_access(db,session,id);c=await db.get(Conversation,id)
    if not c:raise DomainError("NOT_FOUND","Conversation not found",404)
    audit(db,session,"TRANSCRIPT_READ",c,uuid4());await db.commit()
    logs=(await db.scalars(select(ChatLog).where(ChatLog.conversation_id==id,ChatLog.sequence>after).order_by(ChatLog.sequence).limit(200))).all()
    return {"conversation":serialize(c),"messages":[serialize(x) for x in logs]}
@router.get("/escalations")
async def cases(session=Depends(staff),db=Depends(database)):
    user=await db.get(AdminUser,session.admin_user_id);q=select(EscalationCase).order_by(EscalationCase.opened_at.desc())
    if user.role!="ADMIN":q=q.where(EscalationCase.assigned_admin_id==user.id)
    return [serialize(x) for x in (await db.scalars(q.limit(200))).all()]
@router.post("/escalations/{id}/claim")
async def claim(id:UUID,session=Depends(administrator),db=Depends(database)):
    case=await db.get(EscalationCase,id,with_for_update=True)
    if not case:raise DomainError("NOT_FOUND","Case not found",404)
    case.assigned_admin_id=session.admin_user_id;case.status="ASSIGNED";audit(db,session,"CASE_CLAIMED",case,uuid4());await db.commit();return serialize(case)
@router.post("/escalations/{id}/resolve")
async def resolve(id:UUID,body:ResolveCase,session=Depends(administrator),db=Depends(database)):
    case=await db.get(EscalationCase,id)
    if not case:raise DomainError("NOT_FOUND","Case not found",404)
    async with conversation_lock(case.conversation_id):
        c=await db.get(Conversation,case.conversation_id)
        if body.decision=="APPROVE_DISCOUNT":
            if not body.discount_qepik or case.reason_code!="MANUAL_DISCOUNT":raise DomainError("INVALID_APPROVAL","Discount approval requires a discount case and amount")
            db.add(ApprovedAdjustment(escalation_case_id=id,conversation_id=c.id,reservation_id=case.reservation_id,amount_qepik=-body.discount_qepik,reason=body.reason,approved_by=session.admin_user_id,expires_at=now()+timedelta(hours=1)))
        case.status="RESOLVED";case.resolution=body.model_dump();case.resolved_at=now();c.status="ACTIVE"
        audit(db,session,"CASE_RESOLVED",case,uuid4(),after=body.model_dump());await db.commit();return serialize(case)
@router.post("/conversations/{id}/messages")
async def admin_message(id:UUID,body:AdminMessage,session=Depends(staff),db=Depends(database)):
    async with conversation_lock(id):
        await assigned_access(db,session,id);c=await db.get(Conversation,id)
        if not c or c.status!="HUMAN":raise DomainError("TAKEOVER_REQUIRED","Conversation must be in human handoff",409)
        seq=await db.scalar(select(func.coalesce(func.max(ChatLog.sequence),0)).where(ChatLog.conversation_id==id))
        row=ChatLog(conversation_id=id,sequence=seq+1,role="ADMIN",raw_content=body.text,payload={"text":body.text,"cards":[]});db.add(row)
        c.last_activity_at=now();c.retention_due_at=now()+relativedelta(months=settings().chat_retention_months)
        audit(db,session,"ADMIN_MESSAGE",c,uuid4());await db.commit();return {"ok":True}
@router.get("/privacy/due")
async def due(session=Depends(administrator),db=Depends(database)):
    return [serialize(x) for x in (await db.scalars(select(Conversation).where(Conversation.retention_due_at<=now()).order_by(Conversation.retention_due_at).limit(200))).all()]
@router.post("/privacy/{id}/review")
async def privacy(id:UUID,body:PrivacyAction,session=Depends(administrator)):
    from dateutil.relativedelta import relativedelta
    from app.services.drafts import release_draft
    async with conversation_lock(id),Session() as db,db.begin():
        c=await db.get(Conversation,id,with_for_update=True)
        if not c or c.retention_due_at>now():raise DomainError("NOT_ELIGIBLE","Conversation is not due for retention review",409)
        if body.action=="EXTEND":c.retention_due_at=now()+relativedelta(months=body.months)
        else:
            count=await db.scalar(select(func.count(ChatLog.id)).where(ChatLog.conversation_id==id))
            c.status="CLOSED"
            if c.active_draft_id:await release_draft(db,c.active_draft_id,"EXPIRED")
            await db.flush()
            await db.execute(text("SELECT purge_chat_history(:id)"),{"id":id})
            drafts=(await db.scalars(select(BookingDraft).where(BookingDraft.conversation_id==id))).all()
            for d in drafts:d.proposal={k:v for k,v in d.proposal.items() if k!="contact"}
        audit(db,session,"RETENTION_"+body.action,c,uuid4(),after={"deleted_log_count":count if body.action=="PURGE" else 0},reason=body.reason)
    return {"ok":True}
@router.get("/reservations")
async def reservations(session=Depends(administrator),db=Depends(database)):
    return [serialize(x) for x in (await db.scalars(select(Reservation).order_by(Reservation.created_at.desc()).limit(200))).all()]
@router.get("/analytics")
async def analytics(session=Depends(administrator),db=Depends(database)):
    return {"conversations":await db.scalar(select(func.count(Conversation.id))),"bookings":await db.scalar(select(func.count(Reservation.id))),"cancelled":await db.scalar(select(func.count(Reservation.id)).where(Reservation.status=="CANCELLED")),"open_cases":await db.scalar(select(func.count(EscalationCase.id)).where(EscalationCase.status.in_(["OPEN","ASSIGNED"]))),"funnel":dict((await db.execute(select(ConversionEvent.event_name,func.count()).group_by(ConversionEvent.event_name))).all())}
