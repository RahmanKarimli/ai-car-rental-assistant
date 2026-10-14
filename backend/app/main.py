import asyncio
import contextlib
from contextlib import asynccontextmanager
from uuid import uuid4
from pathlib import PurePosixPath
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse,FileResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError,SQLAlchemyError
from app.api.routes import auth,conversations,bookings,admin,admin_data
from app.db.session import engine
from app.db.checkpoints import pool,get_saver
from app.agents import graph as graph_module
from app.core.rate_limits import redis_client
from app.core.errors import DomainError
from app.core.config import settings
from app.services.fx import refresh_loop
from app.providers.filesystem import assets

@asynccontextmanager
async def lifespan(app):
    await pool.open();graph_module.graph=graph_module.build_graph(get_saver());task=asyncio.create_task(refresh_loop())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):await task
    from app.providers.openai_chat import chat
    await chat.client.close();await pool.close();await redis_client.aclose();await engine.dispose()
app=FastAPI(title="Rental Assistant",version="0.1.0",lifespan=lifespan)
@app.middleware("http")
async def boundary(request:Request,call_next):
    origin=request.headers.get("origin")
    if request.method not in {"GET","HEAD","OPTIONS"} and origin and origin.rstrip('/')!=settings().app_origin.rstrip('/'):
        return JSONResponse({"code":"ORIGIN_REJECTED","detail":"Origin is not allowed"},status_code=403)
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff";response.headers["Cache-Control"]="no-store";return response
@app.exception_handler(DomainError)
async def domain(request,error):return JSONResponse({"code":error.code,"detail":error.detail},status_code=error.status)
@app.exception_handler(IntegrityError)
async def conflict(request,error):return JSONResponse({"code":"DATA_CONFLICT","detail":"Inventory or record changed. Refresh and retry."},status_code=409)
@app.exception_handler(SQLAlchemyError)
async def database_error(request,error):return JSONResponse({"code":"DATABASE_UNAVAILABLE","detail":"This action could not be accepted. Retry shortly."},status_code=503)
for router in [auth.router,conversations.router,bookings.router,admin.router,admin_data.router]:app.include_router(router,prefix="/api/v1")
@app.get("/api/v1/assets/{key:path}")
async def asset(key:str):
    if not key.startswith("vehicles/") or ".." in PurePosixPath(key).parts:raise DomainError("NOT_FOUND","Asset not found",404)
    return FileResponse(assets.open(key))
@app.get("/health/live")
async def live():return {"status":"ok"}
@app.get("/health/ready")
async def ready():
    async with engine.connect() as db:await db.execute(text("SELECT 1"))
    return {"status":"ready","ai_configured":bool(settings().api_key)}
