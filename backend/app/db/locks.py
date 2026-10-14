from contextlib import asynccontextmanager
from sqlalchemy import text
from app.db.session import engine
from app.core.errors import DomainError
@asynccontextmanager
async def conversation_lock(id):
    async with engine.connect() as connection:
        key = int.from_bytes(id.bytes[:8], "big", signed=True)
        acquired = await connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key":key})
        await connection.commit()
        if not acquired:raise DomainError("TURN_IN_PROGRESS", "Another action is processing. Retry shortly.", 409)
        try:yield
        finally:
            await connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key":key})
            await connection.commit()
