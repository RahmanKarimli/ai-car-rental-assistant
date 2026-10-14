import asyncio,getpass,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.db.session import Session
from app.models import AdminUser
from app.core.security import passwords
async def main():
    email=input("Administrator email: ").strip().lower();password=getpass.getpass("Administrator password (12+ characters): ")
    if len(password)<12:raise SystemExit("Use at least 12 characters")
    async with Session() as db,db.begin():
        if await db.scalar(select(AdminUser.id).where(AdminUser.email==email)):raise SystemExit("Administrator already exists")
        db.add(AdminUser(email=email,password_hash=passwords.hash(password),role="ADMIN"))
    print("Administrator created.")
asyncio.run(main())
