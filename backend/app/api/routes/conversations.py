from uuid import UUID
from fastapi import APIRouter,Depends,Query
from sqlalchemy import select
from dateutil.relativedelta import relativedelta
from app.api.dependencies import database,actor,own_conversation
from app.models import Conversation,ChatLog,AgentRun
from app.schemas.chat import ChatEvent
from app.services.conversations import process
from app.services.audit import now,serialize
from app.core.config import settings
from app.core.errors import DomainError
router=APIRouter()
@router.get("/conversations")
async def list_conversations(session=Depends(actor),db=Depends(database)):
    first_message=(select(ChatLog.raw_content).where(ChatLog.conversation_id==Conversation.id,ChatLog.role=="USER",ChatLog.raw_content!="").order_by(ChatLog.sequence).limit(1).correlate(Conversation).scalar_subquery())
    rows=(await db.execute(select(Conversation.id,Conversation.language,Conversation.status,Conversation.last_activity_at,first_message.label("preview")).where(Conversation.session_id==session.id,Conversation.status!="CLOSED").order_by(Conversation.last_activity_at.desc()).limit(50))).all()
    return [{"id":str(row.id),"language":row.language,"status":row.status,"last_activity_at":row.last_activity_at,"preview":row.preview} for row in rows]
@router.post("/conversations")
async def create(session=Depends(actor),db=Depends(database)):
    c=Conversation(session_id=session.id,language=settings().default_language,last_activity_at=now(),retention_due_at=now()+relativedelta(months=settings().chat_retention_months))
    db.add(c);await db.commit();return {"id":str(c.id),"language":c.language}
@router.get("/conversations/{id}")
async def history(id:UUID,after:int=0,limit:int=Query(100,ge=1,le=200),session=Depends(actor),db=Depends(database)):
    c=await own_conversation(db,session,id)
    rows=(await db.scalars(select(ChatLog).where(ChatLog.conversation_id==id,ChatLog.sequence>after).order_by(ChatLog.sequence).limit(limit))).all()
    return {"id":str(c.id),"language":c.language,"state":c.session_state,"status":c.status,"messages":[serialize(r) for r in rows]}
@router.post("/conversations/{id}/events")
async def events(id:UUID,event:ChatEvent,session=Depends(actor)):
    return await process(session,id,event)
@router.get("/conversations/{id}/runs/{run_id}")
async def run(id:UUID,run_id:UUID,session=Depends(actor),db=Depends(database)):
    await own_conversation(db,session,id);r=await db.get(AgentRun,run_id)
    if not r or r.conversation_id!=id:raise DomainError("NOT_FOUND","Run not found",404)
    return {"status":r.status,"response":(await db.get(ChatLog,r.response_log_id)).payload if r.response_log_id else None}
