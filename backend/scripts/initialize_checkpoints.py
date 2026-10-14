import asyncio
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.db.checkpoints import pool,get_saver
async def main():
    await pool.open();await get_saver().setup();await pool.close()
asyncio.run(main())
