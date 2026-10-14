'use client';
import {ArrowUpRight,Check,Clock,Compass,MapPin,ShieldCheck} from '@phosphor-icons/react';
import {useEffect,useState} from 'react';
import {formatRentalDate} from '@/lib/dates';
import {VehicleCard} from './VehicleCard';
import type {Card,Language,Vehicle} from '@/types/chat';

type Props={card:Card;language:Language;disabled?:boolean;onSelect?:(c:Card)=>void;onConfirm?:(c:Card)=>void;onExtra?:(id:string)=>void;onDecline?:(id:string)=>void};
function QuoteCard({card:c,language,onConfirm,disabled}:Props){
  const az=language==='az', [now,setNow]=useState(Date.now());
  useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),10000);return()=>clearInterval(timer);},[]);
  const expired=new Date(c.valid_until).getTime()<=now;
  return <article className="quote-card">
    <div className="card-heading"><ShieldCheck size={22}/><h3>{c.action_kind==='CANCEL'?(az?'Ləğv təklifi':'Cancellation summary'):c.action_kind==='MODIFY'?(az?'Dəyişiklik təklifi':'Your updated quote'):(az?'İcarə təklifiniz':'Your rental quote')}</h3></div>
    {c.trip&&<div className="quote-trip"><b>{c.trip.vehicle}</b><span>{c.trip.location}</span><span>{formatRentalDate(c.trip.pickup_at,language)} → {formatRentalDate(c.trip.return_at,language)}</span></div>}
    {c.items.map((item:any,index:number)=><div className="line-item" key={index}><span>{item.label}{item.quantity>1?` × ${item.quantity}`:''}</span><span>{item.amount.formatted}</span></div>)}
    <div className="quote-total"><span>{az?'Cəmi':'Total'}</span><b>{c.total.formatted}</b></div>
    {c.usd_display&&<p className="muted-small">{c.usd_display} · CBAR {c.fx_date} · {az?'məlumat üçün':'informational'}</p>}
    <div className="line-item"><span>{az?'Depozit':'Security deposit'}</span><span>{c.deposit.formatted}</span></div>
    {c.delta&&<div className="line-item"><span>{az?'Qiymət fərqi':'Price difference'}</span><span>{c.delta.formatted}</span></div>}
    <p className="quote-note"><Clock size={17}/>{az?'Götürmə zamanı ödəniş. Təklifin son vaxtı: ':'Pay at pickup. Quote expires: '}{formatRentalDate(c.valid_until,language)}</p>
    {expired&&c.status==='READY'&&<p className="form-error" role="status">{az?'Təklifin vaxtı bitib. Yeni təklif hazırlayın.':'This quote has expired. Prepare a new quote to continue.'}</p>}
    {c.draft_id&&c.status==='READY'&&<button type="button" className="primary full" disabled={disabled||!onConfirm||expired} onClick={()=>onConfirm?.(c)}>{az?'Təsdiqlə':'Confirm '+(c.action_kind==='CREATE'?'booking':c.action_kind==='MODIFY'?'changes':'cancellation')}<ArrowUpRight size={18}/></button>}
  </article>;
}
export function CardRenderer(props:Props){
  const {card:c,language,onSelect,onExtra,onDecline,disabled}=props,az=language==='az';
  if(c.type==='vehicle')return <VehicleCard car={c as Vehicle} language={language} variant="compact" onSelect={onSelect} disabled={disabled}/>;
  if(c.type==='quote')return <QuoteCard {...props}/>;
  if(c.type==='booking')return <article className="booking-card"><div className="card-heading"><Check size={22}/><h3>{c.status==='CANCELLED'?(az?'Rezervasiya ləğv edildi':'Reservation cancelled'):(az?'Rezervasiya təsdiqləndi':'Reservation confirmed')}</h3></div><p className="booking-ref">{c.reference}</p><h3>{c.title}</h3><div className="booking-dates"><span><MapPin size={17}/>{c.location}</span><span>{formatRentalDate(c.pickup_at,language)}</span><span>{formatRentalDate(c.return_at,language)}</span></div><div className="line-item"><span>{az?'Cəmi':'Total'}</span><b>{c.total.formatted}</b></div><div className="line-item"><span>{az?'Depozit':'Security deposit'}</span><b>{c.deposit.formatted}</b></div><p className="muted-small">{az?'Götürmə zamanı ödəniş':'Payment at pickup'}</p><a className="text-link" href={`/reservations/${c.reservation_id}`}>{az?'Rezervasiyanı idarə et':'Manage reservation'}<ArrowUpRight size={17}/></a></article>;
  if(c.type==='upsell')return <article className="upsell-card"><Compass size={24}/><div><h4>{c.title}</h4><p>{c.description}</p><div className="inline-actions"><button type="button" disabled={disabled||!onExtra} onClick={()=>onExtra?.(c.extra_id)}>{az?'Əlavə et':'Add to quote'}</button><button type="button" disabled={disabled||!onDecline} className="quiet" onClick={()=>onDecline?.(c.extra_id)}>{az?'Xeyr, təşəkkür':'No thanks'}</button></div></div></article>;
  if(c.type==='policy')return <div className="policy-sources">{c.sources.map((source:any)=><a className="text-link" href={`/policies/${source.source_id}`} target="_blank" rel="noopener noreferrer" key={source.source_id}>{source.document} · v{source.version} · {source.section}<ArrowUpRight size={16}/></a>)}</div>;
  if(c.type==='escalation')return <div className="handoff-card"><ShieldCheck size={24}/><div><b>{az?'Mütəxəssisə yönləndirildi':'A specialist will help'}</b><p>{az?'Mesajlarınız dəstək panelində saxlanılır.':'Your messages are saved in the support inbox.'}</p></div></div>;
  return null;
}
