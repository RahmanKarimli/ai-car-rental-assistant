from sqlalchemy import select
from app.models import EscalationCase
from app.services.audit import now
async def escalate(db,conversation,reason,log_id):
    case=await db.scalar(select(EscalationCase).where(EscalationCase.conversation_id==conversation.id,EscalationCase.status.in_(["OPEN","ASSIGNED"])).limit(1))
    if not case:
        case=EscalationCase(conversation_id=conversation.id,reason_code=reason,summary=reason,source_log_ids=[str(log_id)],opened_at=now());db.add(case);await db.flush()
    conversation.status="HUMAN"
    return {"type":"escalation","case_id":str(case.id),"status":case.status}
