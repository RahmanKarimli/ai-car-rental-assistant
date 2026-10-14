from uuid import UUID,uuid4
from sqlalchemy import select,func
from dateutil.relativedelta import relativedelta
from app.models import Conversation,ChatLog,AgentRun,ConversionEvent
from app.db.session import Session
from app.db.locks import conversation_lock
from app.api.dependencies import own_conversation
from app.core.config import settings
from app.core.errors import DomainError
from app.services.audit import now
from app.agents import graph as graph_module
async def process(actor,id,event):
    async with conversation_lock(id):
        async with Session() as db,db.begin():
            c=await own_conversation(db,actor,id)
            existing=await db.scalar(select(AgentRun).where(AgentRun.conversation_id==id,AgentRun.client_event_id==event.client_event_id))

            if existing:
                raw=await db.get(ChatLog,existing.input_log_id)
                if raw.payload!=event.model_dump(mode="json"):raise DomainError("IDEMPOTENCY_CONFLICT","Event ID was reused with different content",409)
                if existing.response_log_id:return (await db.get(ChatLog,existing.response_log_id)).payload
                run=existing
            else:
                seq=await db.scalar(select(func.coalesce(func.max(ChatLog.sequence),0)).where(ChatLog.conversation_id==id))
                row=ChatLog(id=uuid4(),conversation_id=id,sequence=seq+1,client_event_id=event.client_event_id,role="USER",raw_content=getattr(event,"text",""),payload=event.model_dump(mode="json"))
                db.add(row);await db.flush()
                run=AgentRun(id=uuid4(),conversation_id=id,client_event_id=event.client_event_id,input_log_id=row.id,event_kind=event.kind,started_at=now())
                db.add(run);await db.flush();row.agent_run_id=run.id
            if event.kind=="LANGUAGE_CHANGE":c.language=event.language
            if event.kind=="DECLINE_UPSELL":c.session_state={**c.session_state,"declined_extras":list(set(c.session_state.get("declined_extras",[])+[str(event.extra_id)]))}
            c.last_activity_at=now();c.retention_due_at=now()+relativedelta(months=settings().chat_retention_months)
        state={"conversation_id":str(id),"session_id":str(actor.id),"run_id":str(run.id),"event":event.model_dump(mode="json")}
        result=await graph_module.graph.ainvoke(state,{"configurable":{"thread_id":str(id)},"recursion_limit":32},durability="sync")
        return result["response"]
