from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.core.config import settings
pool=AsyncConnectionPool(settings().db_url(graph=True),open=False,min_size=1,max_size=5,kwargs={"autocommit":True,"row_factory":dict_row,"options":"-c search_path=agent_state"})
def get_saver():
    return AsyncPostgresSaver(pool)
