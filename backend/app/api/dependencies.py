from uuid import UUID
from fastapi import Depends, Request
from sqlalchemy import select
from app.db.session import Session
from app.models import WebSession, AdminUser, Conversation, BookingAccessGrant
from app.core.security import digest
from app.core.errors import DomainError
from app.services.audit import now
async def database():
    async with Session() as db:yield db
async def actor(request: Request, db=Depends(database)):
    cookie = request.cookies.get("rental_session", "")
    session = await db.scalar(select(WebSession).where(WebSession.token_hash==digest(cookie), WebSession.expires_at>now(), WebSession.revoked_at.is_(None)))
    if not session:raise DomainError("UNAUTHENTICATED", "A valid session is required", 401)
    if session.admin_user_id:
        user=await db.get(AdminUser,session.admin_user_id)
        if not user or not user.active:raise DomainError("UNAUTHENTICATED", "Staff account is inactive",401)
    if request.method not in {"GET","HEAD","OPTIONS"} and request.headers.get("X-CSRF-Token") != cookie:
        raise DomainError("CSRF_REJECTED", "Missing session-bound CSRF header", 403)
    return session
async def staff(session=Depends(actor), db=Depends(database)):
    user = await db.get(AdminUser, session.admin_user_id) if session.admin_user_id else None
    if not user or not user.active:raise DomainError("FORBIDDEN", "Staff access required", 403)
    return session
async def administrator(session=Depends(staff), db=Depends(database)):
    user=await db.get(AdminUser, session.admin_user_id)
    if user.role!="ADMIN":raise DomainError("FORBIDDEN", "Administrator access required", 403)
    return session
async def own_conversation(db, session, id: UUID):
    item=await db.get(Conversation,id)
    if not item or item.session_id!=session.id:raise DomainError("NOT_FOUND", "Conversation not found",404)
    if item.status=="CLOSED":raise DomainError("CONVERSATION_CLOSED", "Start a new conversation",409)
    return item
async def reservation_access(db, session, id: UUID, permission="READ"):
    if session.actor_type=="ADMIN":
        user=await db.get(AdminUser,session.admin_user_id)
        if user and user.active and user.role=="ADMIN":return
    grant=await db.scalar(select(BookingAccessGrant).where(BookingAccessGrant.session_id==session.id,BookingAccessGrant.reservation_id==id,BookingAccessGrant.revoked_at.is_(None)))
    if not grant or permission not in grant.permissions:raise DomainError("NOT_FOUND", "Reservation not found",404)
