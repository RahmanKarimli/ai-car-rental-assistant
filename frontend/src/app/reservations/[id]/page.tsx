'use client';
import {Select} from '@/components/Select';
import {useParams} from 'next/navigation';
import {useEffect,useState} from 'react';
import {api,initializeSession,mutation} from '@/lib/api';
import {toBakuInput,fromBakuInput} from '@/lib/dates';
import {returnAtPickupTime} from '@/lib/rental-search';
import {CardRenderer} from '@/components/CardRenderer';
import type {Language} from '@/types/chat';

export default function Manage(){
 const {id}=useParams<{id:string}>();
 const [language,setLanguage]=useState<Language>('en');
 const [data,setData]=useState<any>(null),[quote,setQuote]=useState<any>(null);
 const [error,setError]=useState(''),[busy,setBusy]=useState(false);
 const [pickup,setPickup]=useState(''),[returnAt,setReturn]=useState('');
 const [vehicles,setVehicles]=useState<any[]>([]),[vehicleId,setVehicleId]=useState('');
 const [catalog,setCatalog]=useState<any[]>([]),[extras,setExtras]=useState<any[]>([]);
 const az=language==='az',effectiveReturn=returnAtPickupTime(pickup,returnAt);
 const pickupDay=new Date(pickup.slice(0,10)+'T00:00:00Z');
 const earliestReturn=Number.isFinite(pickupDay.getTime())?new Date(pickupDay.getTime()+86400000).toISOString().slice(0,10):undefined;
 const load=async()=>{
  const selectedLanguage=localStorage.getItem('yol-language')==='az'?'az':'en';
  setLanguage(selectedLanguage);
  const result=await api<any>(`/reservations/${id}?language=${selectedLanguage}`);
  setData(result);setVehicleId(result.snapshot.trip?.vehicle_id||'');
  setExtras(result.snapshot.trip?.extras||[]);
  setPickup(toBakuInput(result.card.pickup_at));setReturn(toBakuInput(result.card.return_at));
 };
 useEffect(()=>{
  initializeSession().then(async()=>{await load();setCatalog(await api<any[]>('/extras'))}).catch(e=>setError(e.message));
 },[id]);
 useEffect(()=>{
  if(!data||!pickup||!returnAt)return;
  let active=true;
  try{
   const params=new URLSearchParams({pickup_branch_id:data.snapshot.pickup_branch_id,pickup_at:fromBakuInput(pickup),return_at:fromBakuInput(effectiveReturn),language});
   api<any[]>('/inventory?'+params).then(results=>{if(active)setVehicles(results)}).catch(()=>{if(active)setVehicles([])});
  }catch{setVehicles([])}
  return()=>{active=false};
 },[data,pickup,effectiveReturn,language]);
 const draft=async(kind:'MODIFY'|'CANCEL')=>{
  setBusy(true);setError('');
  try{
   let conversation_id=localStorage.getItem('yol-conversation');
   // Signing into the operator console changes the browser session. A saved
   // customer conversation may no longer belong to the current actor.
   if(conversation_id){
    try{const existing=await api<any>('/conversations/'+conversation_id);if(existing.status!=='ACTIVE')conversation_id=null}
    catch{conversation_id=null}
   }
   if(!conversation_id){
    const conversation=await api<any>('/conversations',{method:'POST'});
    conversation_id=conversation.id;localStorage.setItem('yol-conversation',conversation_id!);
   }
   const result=await api<any>(`/reservations/${id}/${kind==='MODIFY'?'modification':'cancellation'}-drafts`,mutation({
    conversation_id,action_kind:kind,reservation_id:id,expected_reservation_version:data.card.version,
    trip:kind==='MODIFY'?{...data.snapshot.trip,vehicle_id:vehicleId,extras,pickup_at:fromBakuInput(pickup),return_at:fromBakuInput(effectiveReturn)}:null,contact:null
   }));
   setQuote(result.cards.find((card:any)=>card.type==='quote')||null);
  }catch(e){setError((e as Error).message)}finally{setBusy(false)}
 };
 const confirm=async(card:any)=>{
  if(busy)return;setBusy(true);setError('');
  try{
   await api(`/drafts/${card.draft_id}/confirm`,mutation({quote_id:card.quote_id,expected_reservation_version:card.expected_reservation_version}));
   setQuote(null);await load();
  }catch(e){setError((e as Error).message)}finally{setBusy(false)}
 };
 return <main className="booking-page">
  <a className="brand" href="/">yol.</a>
  <h1>{az?'Rezervasiyanı idarə et':'Manage reservation'}</h1>
  {error&&<p className="form-error">{error}</p>}
  {data&&<>
   <CardRenderer card={data.card} language={language}/>
   {data.card.status==='CONFIRMED'&&<div className="admin-page" style={{marginTop:20}}>
    <h3>{az?'Avtomobili, tarixləri və ya əlavələri dəyişin':'Update your vehicle, dates or extras'}</h3>
    <label>{az?'Avtomobil':'Vehicle'}</label>
    <Select value={vehicleId} onChange={e=>setVehicleId(e.target.value)}>
     <option value={data.snapshot.trip?.vehicle_id}>{data.card.title} · {az?'hazırkı avtomobil':'current vehicle'}</option>
     {vehicles.filter(vehicle=>vehicle.vehicle_id!==data.snapshot.trip?.vehicle_id).map(vehicle=><option key={vehicle.vehicle_id} value={vehicle.vehicle_id}>{vehicle.title} · {vehicle.daily_price.formatted} / {az?'gün':'day'}</option>)}
    </Select>
    <div className="two-fields">
     <div><label htmlFor="modify-pickup">{az?'Götürmə (Bakı vaxtı)':'Pickup (Baku time)'}</label><input id="modify-pickup" type="datetime-local" value={pickup} onChange={e=>setPickup(e.target.value)}/></div>
     <div><label htmlFor="modify-return">{az?'Qaytarma (Bakı vaxtı)':'Return (Baku time)'}</label><input id="modify-return" type="date" min={earliestReturn} value={returnAt.slice(0,10)} onChange={e=>setReturn(e.target.value)}/><p className="muted-small">{pickup.slice(11)} · {az?'Götürmə vaxtı ilə eyni':'Same time as pickup'}</p></div>
    </div>
    <label>{az?'İstəyə görə əlavələr':'Optional extras'}</label>
    {catalog.map(extra=><label key={extra.id} className="extra-check">
     <input type="checkbox" checked={extras.some(selected=>selected.extra_id===extra.id)} onChange={event=>setExtras(previous=>event.target.checked?[...previous,{extra_id:extra.id,quantity:1}]:previous.filter(selected=>selected.extra_id!==extra.id))}/>
     <span>{az?extra.name_az:extra.name_en}</span>
     {extras.some(selected=>selected.extra_id===extra.id)&&<input style={{width:55}} aria-label={az?'Miqdar':'Quantity'} type="number" min="1" max="10" value={extras.find(selected=>selected.extra_id===extra.id)?.quantity||1} onChange={event=>setExtras(previous=>previous.map(selected=>selected.extra_id===extra.id?{...selected,quantity:Number(event.target.value)}:selected))}/>}</label>)}
    <div className="inline-actions" style={{marginTop:20}}>
     <button disabled={busy} onClick={()=>draft('MODIFY')}>{az?'Dəyişiklik təklifinə bax':'Review modification quote'}</button>
     <button disabled={busy} onClick={()=>draft('CANCEL')}>{az?'Ləğv təklifinə bax':'Review cancellation'}</button>
    </div>
    <p className="muted-small" style={{marginTop:15}}>{az?'Detallı dəyişikliyi təsdiqləyənədək hazırkı rezervasiya qüvvədə qalır.':'Your existing booking stays in place until you confirm the itemized change.'}</p>
   </div>}
   {quote&&<div style={{marginTop:20}}><CardRenderer card={quote} language={language} onConfirm={busy?undefined:confirm}/></div>}
  </>}
 </main>;
}
