import asyncio
import logging
from sqlalchemy import select,text
from app.db.session import Session,engine
from app.models import FxRate
from app.providers.cbar import CBAR
from app.services.audit import now
from app.core.config import settings
async def refresh_loop():
    while True:
        try:
            async with engine.connect() as lock:
                elected=await lock.scalar(text("SELECT pg_try_advisory_lock(7410001)"));await lock.commit()
                if elected:
                    try:
                        value=await CBAR().fetch()
                        if value:
                            date,rate,url=value
                            async with Session() as db,db.begin():
                                found=await db.scalar(select(FxRate).where(FxRate.currency_code=="USD",FxRate.effective_date==date))
                                if not found:db.add(FxRate(currency_code="USD",effective_date=date,azn_per_unit=rate,source_url=url,fetched_at=now()))
                    finally:await lock.execute(text("SELECT pg_advisory_unlock(7410001)"));await lock.commit()
        except asyncio.CancelledError:raise
        except Exception:logging.getLogger("rental").info("fx_refresh_unavailable")
        await asyncio.sleep(settings().fx_refresh_seconds)
