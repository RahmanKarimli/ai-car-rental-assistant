from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
engine = create_async_engine(settings().db_url(), pool_size=5, max_overflow=5, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False)
