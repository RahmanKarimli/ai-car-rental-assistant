from uuid import UUID
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import re
from sqlalchemy import select,func
from pydantic import ValidationError
from app.db.session import Session
from app.models import *
from app.services.audit import now
from app.services.inventory import search
from app.services.pricing import quote_card
from app.services.drafts import prepare
from app.services.reservations import confirm,booking_card
from app.services.policies import retrieve
from app.services.upsells import recommend
from app.services.escalations import escalate as create_escalation
from app.services.search_preferences import sanitize_patch, inventory_preferences, follow_up
from app.services.search_ranking import search_controls, ordered_vehicles, protect_ranking_refinement
from app.core.security import canonical, digest
from app.providers.openai_chat import chat
from app.schemas.bookings import DraftRequest
from app.schemas.inventory import InventoryFilters
from app.core.config import settings
from app.core.errors import DomainError
import tiktoken

def copy(language,en,az):return az if language=="az" else en

def customer_language(text):
    words=set(re.findall(r"[^\W\d_]+",text.casefold()))
    english=len(words & {"hi","hello","i","we","need","want","car","cars","find","for","with","and","tomorrow","pickup","return","people","budget","please","what","how"})
    azerbaijani=len(words & {"salam","mən","men","biz","maşın","masin","avtomobil","avtomobili","sabah","istəyirəm","isteyirem","gedəcəyik","nəfərik","neferik","nəfər","nefer","uşaq","uşaqlar","uşaqlarımız","usaq","üçün","ucun","gün","sigorta","sığorta","ailə","lüks"})
    if english>=2 and english>azerbaijani:return "en"
    if azerbaijani:return "az"
    if english:return "en"
    return None

FILTER_VALUES = {
    "vehicle_type": {
        "SEDAN": "SEDAN", "SALOON": "SEDAN", "SUV": "SUV", "CROSSOVER": "SUV",
        "HATCHBACK": "HATCHBACK", "MINIVAN": "MINIVAN", "MPV": "MINIVAN",
        "VAN": "VAN", "CONVERTIBLE": "CONVERTIBLE", "COUPE": "COUPE",
        "WAGON": "WAGON", "PICKUP": "PICKUP",
    },
    "fuel_type": {"PETROL": "PETROL", "GASOLINE": "PETROL", "GAS": "PETROL",
        "DIESEL": "DIESEL", "HYBRID": "HYBRID", "ELECTRIC": "ELECTRIC", "LPG": "LPG"},
    "transmission": {"AUTOMATIC": "AUTOMATIC", "AUTO": "AUTOMATIC", "MANUAL": "MANUAL"},
    "class_code": {"ECONOMY": "ECONOMY", "STANDARD": "STANDARD", "FAMILY": "FAMILY",
        "PREMIUM": "PREMIUM", "LUXURY": "PREMIUM", "VAN": "VAN", "ELECTRIC": "ELECTRIC"},
}

SEARCH_FIELDS = set(InventoryFilters.model_fields)
VEHICLE_PREFERENCES = {"vehicle_type", "class_code", "fuel_type", "transmission", "sort_by"}
GENERIC_FLEET_REQUESTS = {"what cars are available", "what vehicles are available", "show me available cars",
    "show me cars", "what cars do you have", "hansı avtomobillər var", "nə maşınlar var"}


def normalize_catalog_filter(name, value):
    if value is None:
        return None
    return FILTER_VALUES[name].get(str(value).strip().upper())

class Nodes:
    async def load_context(self,s):
        async with Session() as db:
            c=await db.get(Conversation,UUID(s["conversation_id"]))
            logs=(await db.scalars(select(ChatLog).where(ChatLog.conversation_id==c.id,ChatLog.role.in_(["USER","ASSISTANT"])).order_by(ChatLog.sequence.desc()).limit(settings().chat_context_max_turns))).all()
            enc=tiktoken.get_encoding("cl100k_base");messages=[];remaining=settings().chat_context_max_tokens
            for row in logs:
                tokens=enc.encode(row.raw_content)
                if len(tokens)>remaining:break
                messages.append({"role":"user" if row.role=="USER" else "assistant","content":row.raw_content});remaining-=len(tokens)
            return {"language":c.language,"preferences":c.session_state.get("preferences",{}),"phase":c.session_state.get("phase","DISCOVERY"),
                "recent_vehicle_ids":c.session_state.get("recent_vehicle_ids",[]),
                "search_signature":c.session_state.get("search_signature"),"search_seen_vehicle_ids":c.session_state.get("search_seen_vehicle_ids",[]),"show_different":False,
                "context":list(reversed(messages)),"active_draft_id":str(c.active_draft_id) if c.active_draft_id else None,
                "intent":"HANDOFF" if c.status=="HUMAN" else "GUIDANCE","risk_reason":None,"cards":[],"text":copy(c.language,"Your message is saved for the rental specialist.","Mesajınız icarə mütəxəssisi üçün saxlanıldı.") if c.status=="HUMAN" else "","error_code":None,"error_node":None,"usage":{},"interpretation":None,
                "missing_fields":[],"search_notes":[],"alternative_class":None,"alternative_budget":False,"retrieved_chunks":[],"policy_query":None,"search_mode":None}
    async def detect_language(self,s):
        if s["event"]["kind"]!="TEXT_MESSAGE" or s["intent"]=="HANDOFF":return {}
        async with Session() as db:
            count=await db.scalar(select(func.count(AgentRun.id)).where(AgentRun.conversation_id==UUID(s["conversation_id"]),AgentRun.event_kind=="TEXT_MESSAGE"))
        if count!=1:return {}
        language=customer_language(s["event"]["text"])
        result,usage=await chat.interpret(s["context"],{"language":language or "auto","preferences":s["preferences"],"current_time_baku":now().astimezone(ZoneInfo(settings().app_timezone)).isoformat()},s["event"]["text"])
        return {"language":language or result.language,"interpretation":result.model_dump(),"usage":usage}
    async def interpret_request(self,s):
        event=s["event"];kind=event["kind"]
        if s["intent"]=="HANDOFF":return {}
        if kind!="TEXT_MESSAGE":return {"intent":kind}
        text=event["text"].lower()
        risk=None
        # Guard direct exception requests, not ordinary policy questions mentioning
        # words such as "discount" or "deposit".
        for reason,pattern in {
            "MANUAL_DISCOUNT":r"\b(?:apply|give|make|approve)\b.{0,35}\bdiscount\b|\bmanual (?:price|discount)\b|qiyməti azalt|endirim et",
            "OUT_OF_STATE_DROPOFF":r"\b(?:drop.?off|return)\b.{0,40}\b(?:georgia|out.of.state|outside azerbaijan)\b",
            "PAYMENT_EXCEPTION":r"\b(?:skip|waive|bypass)\b.{0,15}\bdeposit\b|\b(?:let me|can i|i want to) pay later\b|depositsiz (?:icarə|götür)|depoziti (?:ləğv|ödəmədən)",
        }.items():
            if re.search(pattern,text):risk=reason
        if risk:return {"intent":"ESCALATE","risk_reason":risk}
        if s.get("interpretation"):
            from app.schemas.intent import IntentResult
            result=IntentResult.model_validate(s["interpretation"]);usage=s["usage"]
        else:
            result,usage=await chat.interpret(s["context"],{"language":s["language"],"preferences":s["preferences"],"current_time_baku":now().astimezone(ZoneInfo(settings().app_timezone)).isoformat()},event["text"])
        language=s["language"]
        clean=text.strip(" \t\r\n!?.,")
        intent=result.intent
        if clean in {"hi","hello","hey","salam","salamlar","good morning","good evening","thanks","thank you","təşəkkürlər","sağ olun"}:
            intent="GREETING"
        elif clean in {"what can you do","how can you help me","what do you do","nə edə bilərsən","nə edə bilərsiniz"}:
            intent="CAPABILITIES"
        elif "which ai model" in clean or "what ai model" in clean or "size of the universe" in clean:
            intent="OUT_OF_SCOPE"
        elif clean in GENERIC_FLEET_REQUESTS:
            intent="SEARCH"
        patch=sanitize_patch(result.preferences.model_dump(exclude_none=True),event["text"],s["preferences"])
        sort_by,show_different=search_controls(event["text"],patch.get("sort_by"),result.show_different)
        if sort_by:patch["sort_by"]=sort_by
        if intent=="GUIDANCE" and (patch or result.clear_preferences or show_different):intent="SEARCH"
        if intent in {"GREETING", "CAPABILITIES", "OUT_OF_SCOPE", "GUIDANCE", "POLICY_QA", "MODIFY", "CANCEL", "ESCALATE"}:
            return {"language":language,"intent":intent,"risk_reason":result.risk_reason if intent=="ESCALATE" else None,
                "policy_query":result.policy_query,"usage":usage}
        clear_fields=result.clear_preferences
        if sort_by or show_different:patch,clear_fields=protect_ranking_refinement(patch,clear_fields,event["text"])
        for field in ["vehicle_type","class_code","fuel_type","transmission"]:
            if patch.get(field):patch[field]=patch[field].upper()
        mode=result.search_mode or ("REFINE" if s["preferences"] else "NEW")
        if sort_by or show_different:mode="REFINE"
        if clean in GENERIC_FLEET_REQUESTS:
            mode="NEW"
            patch={}
        preferences=dict(s["preferences"])
        if intent=="SEARCH" and mode=="NEW":
            for field in VEHICLE_PREFERENCES:preferences.pop(field,None)
        for field in clear_fields:preferences.pop(field,None)
        for clock,day in [("pickup_at","pickup_date"),("return_at","return_date")]:
            if clock in clear_fields or day in clear_fields:
                preferences.pop(clock,None);preferences.pop(day,None);preferences.pop("rental_days",None)
        if "minimum_seats" in clear_fields:preferences.pop("passenger_count",None)
        if "budget_amount" in clear_fields:
            for field in ["budget_currency","budget_basis"]:preferences.pop(field,None)
        # Date edits replace the corresponding old timestamp. Duration edits must
        # recalculate the return from the requested pickup, not reuse an old end.
        if patch.get("pickup_date") and not patch.get("pickup_at"):preferences.pop("pickup_at",None)
        if patch.get("return_date") and not patch.get("return_at"):preferences.pop("return_at",None)
        if patch.get("rental_days") and not patch.get("return_at") and not patch.get("return_date"):
            preferences.pop("return_at",None);preferences.pop("return_date",None)
        if re.search(r"\b(?:luxury|luxurious|premium|high.end|lüks)\b",text) and "class_code" not in clear_fields and not re.search(r"\b(?:not|no|don't|do not|forget|ignore|without|instead of)\b.{0,25}\b(?:luxury|premium|lüks)\b|lüks.{0,20}lazım deyil",text):patch["class_code"]="PREMIUM"
        if patch.get("passenger_count") and not patch.get("minimum_seats"):patch["minimum_seats"]=patch["passenger_count"]
        preferences.update(patch)
        return {"language":language,"intent":intent,"search_mode":mode,"preferences":preferences,"show_different":show_different,
            "risk_reason":None,"policy_query":result.policy_query,"usage":usage}
    async def risk_gate(self,s):
        if s["event"]["kind"]=="HANDOFF":return {"risk_reason":"CUSTOMER_REQUEST","intent":"ESCALATE"}
        if s["risk_reason"]:return {"intent":"ESCALATE"}
        return {}
    async def route_intent(self,s):return {}
    async def clarify(self,s):
        if s["event"]["kind"]=="LANGUAGE_CHANGE":return {"text":copy(s["language"],"I’ll continue in English. How can I help with your rental?","Azərbaycan dilində davam edəcəyəm. İcarə ilə bağlı necə kömək edə bilərəm?")}
        if s["event"]["kind"]=="DECLINE_UPSELL":return {"text":copy(s["language"],"Of course — I’ll leave that extra out. You can continue with your car selection.","Əlbəttə, bu əlavəni seçməyəcəyik. Avtomobil seçiminə davam edə bilərsiniz.")}
        if s["intent"]=="GREETING":
            return {"text":copy(s["language"],"Hi! I can help you find and book a rental car in Azerbaijan. Where will you pick it up, and when do you need it?",
                "Salam! Azərbaycanda icarə avtomobili tapmağa və rezervasiya etməyə kömək edə bilərəm. Avtomobili haradan və nə vaxt götürmək istəyirsiniz?")}
        if s["intent"]=="CAPABILITIES":
            return {"text":copy(s["language"],"I can find available cars, compare options, explain rental policies, prepare an itemized quote, and help manage a booking. Tell me your dates and what kind of car you need.",
                "Mövcud avtomobilləri tapa, seçimləri müqayisə edə, icarə qaydalarını izah edə, detallı qiymət təklifi hazırlaya və rezervasiyanı idarə etməyə kömək edə bilərəm. Tarixlərinizi və istədiyiniz avtomobili yazın.")}
        if s["intent"]=="OUT_OF_SCOPE":
            return {"text":copy(s["language"],"I’m a car rental assistant, so I don’t have reliable information about that. I can help you find a car, check rental policies, or manage a booking in Azerbaijan.",
                "Mən avtomobil icarəsi köməkçisiyəm, ona görə bu mövzuda etibarlı məlumatım yoxdur. Azərbaycanda avtomobil tapmağa, icarə qaydalarını yoxlamağa və rezervasiyanı idarə etməyə kömək edə bilərəm.")}
        if s["intent"] in {"MODIFY","CANCEL"}:
            async with Session() as db:
                reservations=(await db.scalars(select(Reservation).join(BookingAccessGrant,BookingAccessGrant.reservation_id==Reservation.id).where(
                    BookingAccessGrant.session_id==UUID(s["session_id"]),BookingAccessGrant.revoked_at.is_(None),
                    Reservation.status=="CONFIRMED",Reservation.pickup_at>now()).order_by(Reservation.pickup_at).limit(5))).all()
                cards=[await booking_card(db,reservation,s["language"]) for reservation in reservations]
            return {"cards":cards,"text":copy(s["language"],
                "Choose the reservation below and open Manage reservation. You’ll review an itemized change or cancellation draft before confirming." if cards else "I can’t find a future booking in this browser session. A rental specialist can help recover access to an existing reservation.",
                "Aşağıdakı rezervasiyanı seçib Rezervasiyanı idarə et səhifəsini açın. Təsdiqdən əvvəl detallı dəyişiklik və ya ləğv təklifinə baxacaqsınız." if cards else "Bu brauzer sessiyasında gələcək rezervasiya tapılmadı. İcarə mütəxəssisi mövcud rezervasiyaya girişinizi bərpa etməyə kömək edə bilər.")}
        preferences,_,notes,missing,_=inventory_preferences(s["preferences"],now())
        question=follow_up(preferences,missing,s["language"])
        return {"preferences":preferences,"text":question or copy(s["language"],"Select a car from the cards, then complete the driver and contact details to review your itemized quote.","Kartlardan avtomobil seçin, sonra detallı təklif üçün sürücü və əlaqə məlumatlarını daxil edin.")}
    async def search_inventory(self,s):
        form_search=s["event"]["kind"]=="SEARCH"
        values=s["event"].get("filters") if form_search else {k:v for k,v in s["preferences"].items() if k in SEARCH_FIELDS}
        values=dict(values or {})
        preferences={k:v for k,v in s["preferences"].items() if k not in SEARCH_FIELDS|{"passenger_count"}} if form_search else dict(s["preferences"])
        if values.get("vehicle_type")=="LUXURY":
            values.pop("vehicle_type")
            values["class_code"]="PREMIUM"
        elif values.get("vehicle_type")=="COMPACT":
            values["vehicle_type"]="HATCHBACK"
        # Model output is descriptive, not a trusted database enum. Ignore unsupported
        # labels such as "comfortable" instead of turning them into zero-result filters.
        for field in FILTER_VALUES:
            raw=values.get(field)
            if raw is not None:
                normalized=normalize_catalog_filter(field,raw)
                if normalized is None:
                    values.pop(field,None)
                    preferences.pop(field,None)
                else:
                    values[field]=normalized
                    preferences[field]=normalized
        preferences.update(values)
        preferences,filters,notes,missing,capacity_exceeded=inventory_preferences(preferences,now())
        alternative_class=None
        budget_unresolved=preferences.get("budget_amount") is not None and filters.budget_amount is None
        async with Session() as db,db.begin():
            cards=[] if capacity_exceeded or budget_unresolved else await search(db,filters,s["language"])
            if not cards and filters.class_code and not capacity_exceeded and not budget_unresolved:
                # Offer clearly labelled category alternatives while preserving
                # seats, dates, location, vehicle type and any complete budget.
                cards=await search(db,filters.model_copy(update={"class_code":None}),s["language"])
                if cards:
                    alternative_class=filters.class_code
                    for card in cards:card["alternative_to_class"]=alternative_class
            db.add(ConversionEvent(conversation_id=UUID(s["conversation_id"]),event_name="SEARCH",attributes={"results":len(cards)}))
        signature_filters=filters.model_dump(mode="json")
        if filters.budget_amount is not None:signature_filters["budget_amount"]=str(filters.budget_amount.normalize())
        for field in ["pickup_at","return_at"]:
            if getattr(filters,field):signature_filters[field]=getattr(filters,field).astimezone(timezone.utc).isoformat()
        signature=digest(canonical({"filters":signature_filters,"alternative_class":alternative_class}))
        seen=s.get("search_seen_vehicle_ids",[]) if s.get("search_signature")==signature else s.get("recent_vehicle_ids",[]) if not s.get("search_signature") else []
        text=copy(s["language"],"These cars fit the confirmed search details." if cards else "I couldn’t find a car matching all those preferences. I can check different dates, another pickup branch, or a different vehicle category while keeping enough seats and your stated budget.","Bu avtomobillər dəqiqləşdirilmiş seçimlərə uyğundur." if cards else "Bütün seçimlərə uyğun avtomobil tapmadım. Yer sayını və bildirdiyiniz büdcəni saxlayaraq başqa tarixləri, götürmə məntəqəsini və ya kateqoriyanı yoxlaya bilərəm.")
        if budget_unresolved:text=copy(s["language"],"I’ll check matching cars once your budget details are clear.","Büdcə məlumatları dəqiqləşəndən sonra uyğun avtomobilləri yoxlayacağam.")
        return {"cards":cards,"phase":"CHOOSING" if cards else "DISCOVERY","preferences":preferences,"search_notes":notes,"missing_fields":missing,"alternative_class":alternative_class,"alternative_budget":False,
            "search_signature":signature,"search_seen_vehicle_ids":list(seen),"text":text}
    async def rank_options(self,s):
        ordered=ordered_vehicles(s["cards"],s["preferences"])
        seen=s.get("search_seen_vehicle_ids",[])
        if s.get("show_different"):
            shown=set(seen)
            unseen=[card for card in ordered if card["vehicle_id"] not in shown]
            if ordered and not unseen:
                return {"cards":[],"phase":"DISCOVERY","text":copy(s["language"],"There are no additional matching cars left in this search. I can show the original matching options again, or you can change a preference.","Bu axtarışda göstərilməmiş başqa uyğun avtomobil qalmayıb. Əvvəlki uyğun seçimləri yenidən göstərə və ya seçiminizi dəyişə bilərəm.")}
            ordered=unseen
        vehicles=ordered[:3]
        for index,card in enumerate(vehicles):card["best_fit"]=index==0
        return {"cards":vehicles,"search_seen_vehicle_ids":list(dict.fromkeys([*seen,*[card["vehicle_id"] for card in vehicles]]))}
    async def retrieve_policy(self,s):
        query=s.get("policy_query")
        if not query:return {"error_code":"POLICY_UNSUPPORTED"}
        async with Session() as db:chunks=await retrieve(db,query,s["language"],UUID(s["preferences"]["pickup_branch_id"]) if s["preferences"].get("pickup_branch_id") else None)
        return {"retrieved_chunks":chunks}
    async def answer_policy(self,s):
        if not s.get("retrieved_chunks"):return {"error_code":"POLICY_UNSUPPORTED"}
        answer,usage=await chat.answer_policy(s["policy_query"],s["retrieved_chunks"],s["language"])
        allowed={c["source_id"] for c in s["retrieved_chunks"]}
        if not answer.supported or not answer.source_ids or not set(answer.source_ids)<=allowed:return {"error_code":"POLICY_UNSUPPORTED"}
        sources=[{k:c[k] for k in ["source_id","document","version","section"]} for c in s["retrieved_chunks"] if c["source_id"] in answer.source_ids]
        return {"text":answer.answer,"cards":[{"type":"policy","sources":sources}],"usage":{k:s.get("usage",{}).get(k,0)+usage.get(k,0) for k in ["input_tokens","output_tokens"]}}
    async def recommend_extras(self,s):
        if not any(card.get("type")=="vehicle" for card in s["cards"]):return {}
        async with Session() as db:
            c=await db.get(Conversation,UUID(s["conversation_id"]))
            offers=await recommend(db,s["preferences"],c.session_state.get("declined_extras",[]),s["language"])
        cards=s["cards"]+offers
        # Offer an available, roomier option only when it still satisfies hard filters.
        if len(s["cards"]) and int(s["preferences"].get("passenger_count") or 0)>=3:
            best=s["cards"][0]
            for candidate in s["cards"][1:]:
                if candidate["seats"]>best["seats"] and int(candidate["daily_price"]["amount_qepik"])>int(best["daily_price"]["amount_qepik"]):
                    candidate["upgrade_recommendation"]=True
                    break
        return {"cards":cards}
    async def prepare_draft(self,s):
        if s["event"]["kind"]!="PREPARE_DRAFT":return await self.clarify(s)
        request=DraftRequest.model_validate(s["event"]["draft"])
        if str(request.conversation_id)!=s["conversation_id"]:raise DomainError("NOT_FOUND","Conversation not found",404)
        async with Session() as db,db.begin():
            actor=await db.get(WebSession,UUID(s["session_id"]));c=await db.get(Conversation,UUID(s["conversation_id"]))
            draft=await prepare(db,actor,c,request,s["run_id"]+":draft")
            card=await quote_card(db,await db.get(Quote,draft.quote_id),s["language"],draft)
        return {"active_draft_id":str(draft.id),"phase":"AWAITING_CONFIRMATION","cards":[card],"text":copy(s["language"],"Review each item below. Your booking changes only when you press Confirm.","Aşağıdakı bütün maddələri nəzərdən keçirin. Rezervasiya yalnız Təsdiqlə düyməsinə basdıqda dəyişir.")}
    async def validate_confirmation(self,s):
        if s["event"]["kind"]!="CONFIRM_DRAFT":raise DomainError("CONFIRMATION_REQUIRED","Use the quote confirmation button",409)
        return {}
    async def commit_action(self,s):
        event=s["event"]
        async with Session() as db,db.begin():
            actor=await db.get(WebSession,UUID(s["session_id"]));c=await db.get(Conversation,UUID(s["conversation_id"]))
            reservation=await confirm(db,actor,c,UUID(event["draft_id"]),UUID(event["quote_id"]),event.get("expected_reservation_version"),s["run_id"]+":confirm")
            card=await booking_card(db,reservation,s["language"])
        return {"cards":[card],"active_draft_id":None,"phase":"BOOKED","text":copy(s["language"],"Your reservation action is confirmed. The committed details are below.","Rezervasiya əməliyyatınız təsdiqləndi. Təsdiqlənmiş məlumatlar aşağıdadır.")}
    async def escalate(self,s):
        async with Session() as db,db.begin():
            c=await db.get(Conversation,UUID(s["conversation_id"]));run=await db.get(AgentRun,UUID(s["run_id"]))
            card=await create_escalation(db,c,s.get("risk_reason") or s.get("error_code") or "CUSTOMER_REQUEST",run.input_log_id)
        return {"cards":[card],"phase":"HUMAN_HANDOFF","error_code":None,"text":copy(s["language"],"I’ve queued this for a rental specialist. Your messages will appear in their support inbox.","Sorğunuzu icarə mütəxəssisinə yönləndirdim. Mesajlarınız onun dəstək panelində görünəcək.")}
    async def compose_response(self,s):
        if s["intent"]=="SEARCH" and not s.get("error_code"):
            facts=[{k:c.get(k) for k in ["title","vehicle_type","class_code","seats","features","fuel_type","transmission","availability_checked","best_fit","alternative_to_class"]} for c in s["cards"] if c["type"]=="vehicle"]
            notes=s.get("search_notes",[]);parts=[];usage=s.get("usage",{})
            explanations={
                "INVALID_DATES":("I need valid dates and exact times before checking live availability.","Canlı mövcudluğu yoxlamaq üçün düzgün tarixlər və dəqiq saatlar lazımdır."),
                "PAST_PICKUP":("The pickup must be in the future; let’s choose a new pickup date and time.","Götürmə vaxtı gələcəkdə olmalıdır; yeni tarix və saat seçək."),
                "RETURN_BEFORE_PICKUP":("The return must be after the pickup. Let’s correct the return date and time.","Qaytarma götürmədən sonra olmalıdır. Qaytarma tarixini və saatını dəqiqləşdirək."),
                "INVALID_BUDGET":("Please give a valid nonnegative budget; I haven’t applied that limit yet.","Düzgün, mənfi olmayan büdcə yazın; bu limiti hələ tətbiq etməmişəm."),
                "INVALID_DURATION":("Please clarify the rental length in days.","İcarə müddətini günlə dəqiqləşdirin."),
            }
            for note in notes:
                if note in explanations:parts.append(copy(s["language"],*explanations[note]))
            if "GROUP_TOO_LARGE" in notes:
                return {"text":copy(s["language"],"That group is too large for one vehicle. Would you consider multiple cars? A rental specialist can coordinate the group booking.","Bu sərnişin qrupu bir avtomobil üçün çox böyükdür. Bir neçə avtomobil düşünərsiniz? İcarə mütəxəssisi qrup rezervasiyasını əlaqələndirə bilər.")}
            if s.get("alternative_class") and facts:
                category=s["alternative_class"].title()
                seats=s["preferences"].get("minimum_seats")
                requirement=copy(s["language"],f" with at least {seats} seats" if seats else "",f" ən azı {seats} yerlik" if seats else "")
                parts.append(copy(s["language"],f"I couldn’t find a {category} car{requirement} matching all your preferences. These are alternatives in other categories; your requested category remains saved.",f"Bütün seçimlərinizə uyğun{requirement} {category} avtomobil tapmadım. Bunlar digər kateqoriyalardan alternativlərdir; istədiyiniz kateqoriya yadda saxlanılır."))
            if s.get("alternative_budget"):
                parts.append(copy(s["language"],"I couldn’t find a car within your budget matching the other preferences. These options are above your budget; the prices are shown on the cards and your requested limit remains saved.","Digər seçimlərə uyğun, büdcə daxilində avtomobil tapmadım. Bu seçimlər büdcənizdən yuxarıdır; qiymətlər kartlarda göstərilir və istədiyiniz limit yadda saxlanılır."))
            body=s["text"]
            if facts:
                first=facts[0]
                if s["preferences"].get("sort_by")=="PRICE_ASC":
                    parts.append(copy(s["language"],"Ordered by the pricing engine’s total for your selected dates, including mandatory charges." if first["availability_checked"] else "Ordered by base daily rate for now; trip-price order needs your rental dates.","Seçilmiş tarixlər üçün məcburi ödənişlər daxil olmaqla qiymət mühərrikinin hesabladığı cəmi məbləğə görə sıralanıb." if first["availability_checked"] else "Hələlik əsas günlük tarifə görə sıralanıb; səfərin cəmi qiymətinə görə sıralamaq üçün tarixlər lazımdır."))
                elif s["preferences"].get("sort_by")=="SPACE_DESC":
                    parts.append(copy(s["language"],"Ordered by seat capacity, then recorded large-boot or luggage-space features. Vehicle dimensions aren’t recorded.","Yer sayına, sonra kataloqda qeyd olunan geniş baqaj xüsusiyyətlərinə görə sıralanıb. Avtomobil ölçüləri qeyd olunmayıb."))
                body=copy(s["language"],f"The {first['title']} has {first['seats']} seats and is a {first['class_code'].title()} {first['vehicle_type'].lower()}.",f"{first['title']} {first['seats']} yerlik {first['class_code']} kateqoriyalı {first['vehicle_type']} avtomobildir.")
                if s["event"]["kind"]=="TEXT_MESSAGE":
                    try:
                        answer,extra_usage=await chat.guide(s["event"]["text"],facts,s["language"],s["preferences"],bool(s.get("alternative_class")))
                        # Monetary claims are rejected; cards remain the price surface.
                        invalid_money=re.search(r"AZN|USD|\$|₼|qəpik|qepik|manat|dollar|discount|endirim|\bprice\b|qiymət",answer.text,re.I)
                        wrong_language=s["language"]=="az" and re.search(r"\b(?:ve|için|kişilik|diğer|öneriyorum|seçenek|koltuk|sahiptir|bulunmaktadır)\b",answer.text,re.I)
                        if not invalid_money and not wrong_language:body=answer.text
                        usage={k:usage.get(k,0)+extra_usage.get(k,0) for k in ["input_tokens","output_tokens"]}
                    except (DomainError,ValueError):
                        pass
                if not first["availability_checked"]:
                    parts.append(copy(s["language"],"These are catalog options; live availability needs both dates and exact times.","Bunlar kataloq seçimləridir; canlı mövcudluq üçün hər iki tarix və dəqiq saatlar lazımdır."))
            parts.append(body)
            if any(field in s.get("missing_fields",[]) for field in ["budget_currency","budget_basis"]) or (s["preferences"].get("budget_basis")=="TOTAL" and any(field in s.get("missing_fields",[]) for field in ["pickup_at","return_at"])):
                parts.append(copy(s["language"],"I haven’t applied your budget filter yet; I need its currency, whether it covers a day or the whole trip, and the rental length for a total budget.","Büdcə filtrini hələ tətbiq etməmişəm; valyuta, günlük və ya bütün səfər üçün olması, ümumi büdcə üçün isə icarə müddəti lazımdır."))
            question=follow_up(s["preferences"],s.get("missing_fields",[]),s["language"])
            if question:parts.append(question)
            elif facts:parts.append(copy(s["language"],"Select a car below to prepare your itemized quote.","Detallı təklif üçün aşağıdan avtomobil seçin."))
            return {"text":" ".join(parts),"usage":usage}
        if s["text"]:return {}
        return {"text":copy(s["language"],"Tell me your dates, passenger count and budget, or use the trip form to get started.","Tarixləri, sərnişin sayını və büdcəni yazın və ya başlamaq üçün səfər formasından istifadə edin.")}
    async def persist_response(self,s):
        from dateutil.relativedelta import relativedelta
        async with Session() as db,db.begin():
            c=await db.get(Conversation,UUID(s["conversation_id"]));run=await db.get(AgentRun,UUID(s["run_id"]))
            if run.response_log_id:
                row=await db.get(ChatLog,run.response_log_id);return {"response":row.payload}
            seq=await db.scalar(select(func.coalesce(func.max(ChatLog.sequence),0)).where(ChatLog.conversation_id==c.id))
            row=ChatLog(conversation_id=c.id,sequence=seq+1,role="ASSISTANT",raw_content=s["text"],payload={},agent_run_id=run.id)
            db.add(row);await db.flush()
            response={"run_id":str(run.id),"message_id":str(row.id),"language":s["language"],"text":s["text"],"cards":s["cards"],"conversation_phase":s["phase"],"error_code":s.get("error_code"),"preferences":s["preferences"]}
            row.payload=response;c.language=s["language"];c.last_activity_at=now();c.retention_due_at=now()+relativedelta(months=settings().chat_retention_months)
            recent=s.get("recent_vehicle_ids",[])
            if s["intent"]=="SEARCH":
                shown=[card["vehicle_id"] for card in s["cards"] if card.get("type")=="vehicle"]
                recent=(recent+shown)[-18:]
            c.session_state={**c.session_state,"preferences":s["preferences"],"phase":s["phase"],"recent_vehicle_ids":recent,
                "search_signature":s.get("search_signature"),"search_seen_vehicle_ids":s.get("search_seen_vehicle_ids",[])};c.state_version+=1
            run.status="COMPLETE";run.response_log_id=row.id;run.finished_at=now();run.error_code=s.get("error_code")
            run.input_tokens=s.get("usage",{}).get("input_tokens",0);run.output_tokens=s.get("usage",{}).get("output_tokens",0)
            return {"response":response}
    async def await_confirmation(self,s):return {}
    async def recover(self,s):
        code=s.get("error_code")
        messages={"POLICY_UNSUPPORTED":("I couldn’t find a reviewed policy answer. A rental specialist can clarify this.","Təsdiqlənmiş siyasətdə cavab tapa bilmədim. İcarə mütəxəssisi bunu dəqiqləşdirə bilər."),"DRAFT_EXPIRED":("This draft expired. Prepare a fresh quote before confirming.","Bu təklifin müddəti bitib. Təsdiqdən əvvəl yeni təklif hazırlayın."),"VERSION_CONFLICT":("This reservation changed. Refresh its details before modifying it.","Rezervasiya dəyişib. Dəyişiklikdən əvvəl məlumatları yeniləyin."),
            "AI_QUOTA":("The assistant is busy right now. Retry shortly, or use the trip form to search directly.","Köməkçi hazırda məşğuldur. Bir az sonra yenidən cəhd edin və ya səfər formasından birbaşa axtarış edin."),
            "AI_UNAVAILABLE":("The AI connection is temporarily unavailable. Your message is saved; retry or search using the trip form.","AI bağlantısı müvəqqəti əlçatan deyil. Mesajınız saxlanılıb; yenidən cəhd edin və ya səfər formasından axtarış edin."),
            "INVALID_INPUT":("I need a little more detail to process that request. Please clarify the dates, passenger count or budget you want to change.","Sorğunu emal etmək üçün bir az dəqiqləşdirmə lazımdır. Dəyişmək istədiyiniz tarixləri, sərnişin sayını və ya büdcəni yazın.")}
        en,az=messages.get(code,("I couldn’t complete this step. Use the trip controls or contact a rental specialist. Your existing booking remains unchanged.","Bu addımı tamamlamaq mümkün olmadı. Səfər idarəetmə panelindən istifadə edin və ya mütəxəssislə əlaqə saxlayın. Mövcud rezervasiya dəyişməyib."))
        return {"text":copy(s["language"],en,az),"cards":[]}
