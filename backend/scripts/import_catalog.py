import asyncio,getpass,json,sys
from pathlib import Path
import httpx
async def main():
    if len(sys.argv)<2:raise SystemExit("Usage: python scripts/import_catalog.py catalog.json [http://web:3000]")
    records=json.loads(Path(sys.argv[1]).read_text());base=sys.argv[2] if len(sys.argv)>2 else "http://web:3000"
    email=input("Administrator email: ");password=getpass.getpass("Password: ")
    async with httpx.AsyncClient(base_url=base,timeout=120) as client:
        response=await client.post("/api/v1/auth/login",json={"email":email,"password":password});response.raise_for_status()
        client.headers["X-CSRF-Token"]=response.json()["csrf_token"]
        for kind in ["branches","rates","rules","extras","vehicles"]:
            for record in records.get(kind,[]):
                response=await client.post("/api/v1/admin/catalog/"+kind,json=record);response.raise_for_status()
                print(kind,response.json()["id"])
asyncio.run(main())
