from datetime import timedelta
from fastapi import APIRouter,Depends,Response,Request
from sqlalchemy import select
from app.api.dependencies import database,actor
from app.models import WebSession,AdminUser
from app.schemas.admin import Login
from app.core.security import token,digest,verify_password
from app.core.config import settings
from app.core.errors import DomainError
from app.core.rate_limits import redis_client
from app.services.audit import now
router=APIRouter()
async def issue(db,response,admin=None):
    raw=token();session=WebSession(token_hash=digest(raw),actor_type="ADMIN" if admin else "CUSTOMER",admin_user_id=admin.id if admin else None,expires_at=now()+timedelta(days=1 if admin else 30))
    db.add(session);await db.commit()
    response.set_cookie("rental_session",raw,httponly=True,secure=settings().cookie_secure,samesite="strict",max_age=86400 if admin else 2592000,path="/")
    return {"session_id":str(session.id),"csrf_token":raw,"role":admin.role if admin else "CUSTOMER"}
@router.post("/sessions")
async def create_session(response:Response,db=Depends(database)):
    return await issue(db,response)
@router.get("/sessions/current")
async def current(request:Request,session=Depends(actor),db=Depends(database)):
    admin=await db.get(AdminUser,session.admin_user_id) if session.admin_user_id else None
    return {"session_id":str(session.id),"csrf_token":request.cookies["rental_session"],"role":admin.role if admin else "CUSTOMER"}
@router.post("/auth/login")
async def login(body:Login,response:Response,db=Depends(database)):
    try:
        key="login:"+digest(body.email.lower());count=await redis_client.incr(key)
        if count==1:await redis_client.expire(key,300)
        if count>10:raise DomainError("LOGIN_THROTTLED","Too many login attempts",429)
    except DomainError:raise
    except Exception:raise DomainError("AUTH_UNAVAILABLE","Login is temporarily unavailable",503)
    user=await db.scalar(select(AdminUser).where(AdminUser.email==body.email.lower(),AdminUser.active.is_(True)))
    if not user or not verify_password(body.password,user.password_hash):raise DomainError("INVALID_LOGIN","Invalid credentials",401)
    return await issue(db,response,user)
@router.post("/auth/logout")
async def logout(response:Response,session=Depends(actor),db=Depends(database)):
    session.revoked_at=now();await db.commit();response.delete_cookie("rental_session",path="/");return {"ok":True}
