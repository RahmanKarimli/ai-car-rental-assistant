from sqlalchemy import select
from app.models import Extra
async def recommend(db,preferences,declined,language):
    result=[]
    from datetime import datetime
    start,end=preferences.get("pickup_at"),preferences.get("return_at")
    length=None;month=None
    if start and end:
        try:
            a,b=datetime.fromisoformat(start.replace("Z","+00:00")),datetime.fromisoformat(end.replace("Z","+00:00"))
            length=max(1,int((b-a).total_seconds()+86399)//86400);month=a.month
        except ValueError:pass
    for extra in (await db.scalars(select(Extra).where(Extra.active.is_(True)).order_by(Extra.id))).all():
        if str(extra.id) in declined:continue
        rules=extra.eligibility_rules
        if rules.get("minimum_trip_days") and (length is None or length<rules["minimum_trip_days"]):continue
        if rules.get("months") and month not in rules["months"]:continue
        if rules.get("destinations") and preferences.get("destination") not in rules["destinations"]:continue
        if extra.kind=="CHILD_SEAT" and not (preferences.get("has_children") or preferences.get("child_passengers")):continue
        if extra.kind=="GPS" and not preferences.get("needs_navigation"):continue
        if extra.kind not in {"CHILD_SEAT","GPS","INSURANCE"}:continue
        if extra.stock_total==0:continue
        result.append({"type":"upsell","extra_id":str(extra.id),"kind":extra.kind,"title":extra.name_az if language=="az" else extra.name_en,"description":extra.description_az if language=="az" else extra.description_en})
    return sorted(result,key=lambda x:{"CHILD_SEAT":0,"GPS":1,"INSURANCE":2}[x["kind"]])[:2]
