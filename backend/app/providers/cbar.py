from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
import httpx
from defusedxml import ElementTree
from app.services.audit import now
class CBAR:
    async def fetch(self):
        date=now().astimezone(ZoneInfo("Asia/Baku")).date()
        async with httpx.AsyncClient(timeout=10,follow_redirects=False) as client:
            for offset in range(10):
                target=date-timedelta(days=offset)
                url=f"https://cbar.az/currencies/{target:%d.%m.%Y}.xml"
                response=await client.get(url)
                if response.status_code!=200:continue
                if len(response.content)>1000000:continue
                root=ElementTree.fromstring(response.content)
                for entry in root.iter("Valute"):
                    if entry.attrib.get("Code")=="USD":
                        rate=Decimal(entry.findtext("Value").replace(",","."))/Decimal(entry.findtext("Nominal"))
                        if rate<=0:continue
                        return target,rate,url
        return None
