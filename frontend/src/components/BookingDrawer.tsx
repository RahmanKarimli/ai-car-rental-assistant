'use client';
import {ArrowLeft,ArrowRight,Check,MapPin,ShieldCheck,X} from '@phosphor-icons/react';
import {useEffect,useRef,useState} from 'react';
import {CardRenderer} from './CardRenderer';
import {VehicleCard} from './VehicleCard';
import {formatRentalDate,fromBakuInput} from '@/lib/dates';
import {sameTimeReturn} from '@/lib/rental-search';
import type {Branch,Card,ChatResponse,Extra,Language,SearchValues,Vehicle} from '@/types/chat';

export function BookingDrawer({car,branch,values,language,catalog,busy,conversationId,onClose,onSend,onRetry,canRetry,initialExtras}:{car:Vehicle|null;branch?:Branch;values:SearchValues;language:Language;catalog:Extra[];busy:boolean;conversationId:string;onClose:()=>void;onSend:(kind:string,payload:any)=>Promise<ChatResponse|undefined>;onRetry:()=>Promise<ChatResponse|undefined>;canRetry:boolean;initialExtras:string[]}){
  const dialog=useRef<HTMLDialogElement>(null),az=language==='az';
  const [closing,setClosing]=useState(false),closeTimer=useRef<ReturnType<typeof setTimeout>|null>(null);
  const requestClose=()=>{
    if(closeTimer.current)return;
    setClosing(true);
    closeTimer.current=setTimeout(()=>{closeTimer.current=null;onClose();},window.matchMedia('(prefers-reduced-motion: reduce)').matches?0:180);
  };
  useEffect(()=>()=>{if(closeTimer.current)clearTimeout(closeTimer.current);},[]);
  const [contact,setContact]=useState({name:'',phone:'',email:''}),[age,setAge]=useState('');
  const [extras,setExtras]=useState<Record<string,number>>({}),[quote,setQuote]=useState<Card|null>(null),[booking,setBooking]=useState<Card|null>(null),[error,setError]=useState('');
  useEffect(()=>{setClosing(false);if(car){setQuote(null);setBooking(null);setError('');setExtras(Object.fromEntries(initialExtras.map(id=>[id,1])));if(!dialog.current?.open)dialog.current?.showModal();}else dialog.current?.close();},[car]);
  const prepare=async()=>{
    if(!car||busy)return;setError('');
    let pickup:string,returnAt:string;
    try{const trip=sameTimeReturn(values);pickup=fromBakuInput(trip.pickup);returnAt=fromBakuInput(trip.returnAt);if(new Date(returnAt)<=new Date(pickup))throw new Error();}
    catch{setError(az?'Düzgün götürmə və qaytarma tarixləri seçin.':'Choose valid pickup and return dates.');return;}
    try{
      const result=await onSend('PREPARE_DRAFT',{draft:{conversation_id:conversationId,action_kind:'CREATE',trip:{vehicle_id:car.vehicle_id,pickup_branch_id:car.branch_id,return_branch_id:car.branch_id,pickup_at:pickup,return_at:returnAt,driver_age:Number(age),extras:Object.entries(extras).map(([extra_id,quantity])=>({extra_id,quantity}))},contact:{name:contact.name.trim(),phone:contact.phone.trim(),email:contact.email.trim()||null}}});
      if(!result){setError(az?'Təklif cavabı alınmadı. Eyni sorğunu aşağıda yenidən göndərin.':'The quote could not be delivered. Retry the same request below.');return;}
      if(result.error_code){setError(result.text);return;}
      const next=result.cards.find(card=>card.type==='quote');if(next)setQuote(next);else setError(result.text);
    }catch(e){setError((e as Error).message);}
  };
  const confirm=async(card:Card)=>{
    if(busy)return;setError('');
    const result=await onSend('CONFIRM_DRAFT',{draft_id:card.draft_id,quote_id:card.quote_id,expected_reservation_version:card.expected_reservation_version});
    if(!result){setError(az?'Təsdiq cavabı alınmadı. Eyni sorğunu aşağıda yenidən göndərin.':'Confirmation could not be delivered. Retry the same request below.');return;}
    if(result.error_code){setError(result.text);return;}
    const confirmed=result.cards.find(c=>c.type==='booking');if(confirmed){setBooking(confirmed);setQuote(null);}else setError(result.text);
  };
  return <dialog ref={dialog} className={'booking-dialog '+(closing?'is-closing':'')} onCancel={e=>{e.preventDefault();requestClose();}} onClick={e=>{if(e.target===e.currentTarget){const box=e.currentTarget.getBoundingClientRect();if(e.clientX<box.left||e.clientX>box.right||e.clientY<box.top||e.clientY>box.bottom)requestClose();}}} aria-labelledby="booking-dialog-title">
    <div className="drawer-heading"><div><p className="eyebrow">{az?'SİZİN SEÇİMİNİZ':'YOUR SELECTION'}</p><h2 id="booking-dialog-title">{booking?(az?'Rezervasiya tamamlandı':'You’re ready to go'):quote?(az?'Təklifinizi yoxlayın':'Review your quote'):(az?'İcarə məlumatları':'Rental details')}</h2></div><button type="button" className="icon-button" aria-label={az?'Bağla':'Close rental details'} onClick={requestClose}><X size={22}/></button></div>
    {car&&<div className="drawer-body">
      {booking?<><CardRenderer card={booking} language={language}/><button className="secondary full" onClick={requestClose}>{az?'Avtomobillərə qayıt':'Back to cars'}<Check size={18}/></button></>:quote?<><CardRenderer card={quote} language={language} disabled={busy} onConfirm={confirm}/><button className="text-button" type="button" disabled={busy} onClick={()=>setQuote(null)}><ArrowLeft size={17}/>{az?'Məlumatları dəyiş':'Edit rental details'}</button></>:<>
        <VehicleCard car={{...car,rental_price:null,availability_checked:false}} language={language} variant="compact"/>
        <div className="drawer-trip"><MapPin size={20}/><div><b>{branch?(az?branch.name_az:branch.name_en):''}</b><p>{formatRentalDate(fromBakuInput(values.pickup),language)}<br/>{formatRentalDate(fromBakuInput(sameTimeReturn(values).returnAt),language)}</p></div></div>
        <form onSubmit={e=>{e.preventDefault();prepare();}} className="booking-form">
          <div className="two-fields"><div><label htmlFor="driver-age">{az?'Sürücünün yaşı':'Driver age'}</label><input id="driver-age" type="number" min={16} max={100} required value={age} onChange={e=>setAge(e.target.value)}/></div><div><label htmlFor="renter-name">{az?'Ad və soyad':'Full name'}</label><input id="renter-name" autoComplete="name" required value={contact.name} onChange={e=>setContact({...contact,name:e.target.value})}/></div></div>
          <label htmlFor="renter-phone">{az?'Telefon nömrəsi':'Phone number'}</label><input id="renter-phone" type="tel" autoComplete="tel" required value={contact.phone} onChange={e=>setContact({...contact,phone:e.target.value})}/>
          <label htmlFor="renter-email">{az?'E-poçt (istəyə görə)':'Email (optional)'}</label><input id="renter-email" type="email" autoComplete="email" value={contact.email} onChange={e=>setContact({...contact,email:e.target.value})}/>
          {catalog.length>0&&<fieldset className="extras-fieldset"><legend>{az?'İstəyə görə əlavələr':'Optional extras'}</legend>{catalog.map(extra=><div className="extra-row" key={extra.id}><label className="check-label"><input type="checkbox" checked={!!extras[extra.id]} onChange={e=>setExtras(previous=>{const next={...previous};if(e.target.checked)next[extra.id]=1;else delete next[extra.id];return next;})}/><span>{az?extra.name_az:extra.name_en}</span></label>{extras[extra.id]&&<input className="quantity-input" type="number" min={1} max={10} value={extras[extra.id]} aria-label={(az?'Miqdar: ':'Quantity: ')+(az?extra.name_az:extra.name_en)} onChange={e=>setExtras({...extras,[extra.id]:Number(e.target.value)})}/>}</div>)}</fieldset>}
          <p className="booking-assurance"><ShieldCheck size={20}/>{az?'Rezervasiyadan əvvəl qiymət, depozit və bütün əlavələri yoxlayacaqsınız.':'You’ll review the price, deposit, and every extra before confirming.'}</p>
          <button className="primary full" disabled={busy||!conversationId} type="submit">{busy?(az?'Hazırlanır…':'Preparing…'):(az?'Detallı təklifə bax':'Review itemized quote')}<ArrowRight size={18}/></button>
        </form>
      </>}
      {error&&<div className="form-error" role="alert"><p>{error}</p>{canRetry&&<button className="text-button" type="button" disabled={busy} onClick={async()=>{const result=await onRetry();if(!result)return;setError(result.error_code?result.text:'');if(result.error_code)return;const confirmed=result.cards.find(c=>c.type==='booking'),nextQuote=result.cards.find(c=>c.type==='quote');if(confirmed){setBooking(confirmed);setQuote(null);}else if(nextQuote)setQuote(nextQuote);}}>{az?'Eyni sorğunu yenidən göndər':'Retry the same request'}<ArrowRight size={17}/></button>}</div>}
    </div>}
  </dialog>;
}
