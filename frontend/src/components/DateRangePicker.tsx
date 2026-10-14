'use client';

import {CalendarBlank,CaretLeft,CaretRight,Check} from '@phosphor-icons/react';
import {useEffect,useId,useLayoutEffect,useRef,useState} from 'react';
import {Select} from '@/components/Select';
import type {Language,SearchValues} from '@/types/chat';

type DateField='pickup'|'returnAt';

function dateKey(date:Date){
  return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
}
function dateFromKey(value:string){
  const [year,month,day]=value.slice(0,10).split('-').map(Number);
  return new Date(year,month-1,day,12);
}
function bakuToday(){
  const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Baku',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
  const part=(name:string)=>parts.find(item=>item.type===name)?.value||'';
  return `${part('year')}-${part('month')}-${part('day')}`;
}

export function DateRangePicker({values,language,onChange}:{values:SearchValues;language:Language;onChange:(values:SearchValues)=>void}){
  const id=useId(),root=useRef<HTMLDivElement>(null),az=language==='az';
  const calendar=useRef<HTMLElement>(null);
  const [open,setOpen]=useState(false),[active,setActive]=useState<DateField>('pickup'),[pickupChosen,setPickupChosen]=useState(false),[month,setMonth]=useState(()=>dateFromKey(values.pickup)),[calendarPosition,setCalendarPosition]=useState({top:12,left:12});
  const pickup=values.pickup.slice(0,10),returnAt=values.returnAt.slice(0,10),today=bakuToday();
  const locale=az?'az-AZ':'en-GB';
  const times=Array.from({length:48},(_,index)=>`${String(Math.floor(index/2)).padStart(2,'0')}:${index%2?'30':'00'}`);
  const pretty=(key:string)=>key?new Intl.DateTimeFormat(locale,{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(key+'T12:00:00Z')):'';
  const monthTitle=new Intl.DateTimeFormat(locale,{month:'long',year:'numeric'}).format(month);
  const weekdays=Array.from({length:7},(_,index)=>new Intl.DateTimeFormat(locale,{weekday:'short'}).format(new Date(Date.UTC(2024,0,1+index))));
  const first=new Date(month.getFullYear(),month.getMonth(),1,12),offset=(first.getDay()+6)%7;
  const start=new Date(first);start.setDate(first.getDate()-offset);
  const days=Array.from({length:42},(_,index)=>{const day=new Date(start);day.setDate(start.getDate()+index);return day;});
  const earliestMonth=dateFromKey(active==='pickup'?today:pickup);
  const previousMonthDisabled=month.getFullYear()<earliestMonth.getFullYear()||(month.getFullYear()===earliestMonth.getFullYear()&&month.getMonth()<=earliestMonth.getMonth());
  const close=()=>setOpen(false);

  useEffect(()=>{
    if(!open)return;
    const outside=(event:PointerEvent)=>{if(!root.current?.contains(event.target as Node))close();};
    const escape=(event:KeyboardEvent)=>{if(event.key==='Escape')close();};
    document.addEventListener('pointerdown',outside);document.addEventListener('keydown',escape);
    return()=>{document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',escape);};
  },[open]);

  useLayoutEffect(()=>{
    if(!open||!root.current||!calendar.current)return;
    const reposition=()=>{
      if(!root.current||!calendar.current)return;
      const anchor=root.current.getBoundingClientRect(),panel=calendar.current.getBoundingClientRect();
      const top=anchor.bottom+10+panel.height<=window.innerHeight?anchor.bottom+10:Math.max(12,anchor.top-panel.height-10);
      const left=Math.max(12,Math.min(anchor.left,window.innerWidth-panel.width-12));
      setCalendarPosition({top,left});
    };
    reposition();window.addEventListener('resize',reposition);window.addEventListener('scroll',reposition,true);
    return()=>{window.removeEventListener('resize',reposition);window.removeEventListener('scroll',reposition,true);};
  },[open,month,active]);

  const showCalendar=(field:DateField)=>{
    if(field==='returnAt'&&!pickupChosen)return;
    setActive(field);setMonth(dateFromKey(field==='pickup'?pickup:returnAt));setOpen(true);
  };
  const choose=(day:Date)=>{
    const key=dateKey(day);
    if(active==='pickup'){
      if(key<today)return;
      const nextReturn=returnAt<=key?dateKey(new Date(day.getFullYear(),day.getMonth(),day.getDate()+1,12)):returnAt;
      onChange({...values,pickup:key+'T'+(values.pickup.slice(11)||'12:00'),returnAt:nextReturn+'T'+(values.pickup.slice(11)||'12:00')});
      setPickupChosen(true);setActive('returnAt');setMonth(day);
      return;
    }
    if(key<=pickup)return;
    onChange({...values,returnAt:key+'T'+(values.pickup.slice(11)||'12:00')});close();
  };

  return <div className="date-range-picker" ref={root}>
    {(['pickup','returnAt'] as const).map(field=>{
      const chosen=field==='pickup'?pickup:returnAt,disabled=field==='returnAt'&&!pickupChosen;
      const label=field==='pickup'?(az?'Götürmə':'Pickup'):(az?'Qaytarma':'Return');
      return <div className={'search-field date-search-field '+(field==='pickup'?'pickup-date-field':'return-date-field')} key={field}>
        <CalendarBlank size={22} aria-hidden="true"/>
        <div><label id={`${id}-${field}-label`}>{label}</label>
          <div className="date-value-row">
            <button type="button" className="date-trigger" aria-labelledby={`${id}-${field}-label ${id}-${field}-value`} aria-haspopup="dialog" aria-expanded={open&&(active===field||field==='pickup'&&active==='returnAt')} aria-controls={`${id}-calendar`} disabled={disabled} onClick={()=>showCalendar(field)}>
              <span id={`${id}-${field}-value`}>{pretty(chosen)}</span>
            </button>
            {field==='pickup'?<Select className="date-time-select" aria-label={az?'Götürmə vaxtı':'Pickup time'} value={values.pickup.slice(11)||'12:00'} onChange={event=>onChange({...values,pickup:pickup+'T'+event.target.value,returnAt:returnAt+'T'+event.target.value})}>{[...new Set([...times,values.pickup.slice(11)])].filter(Boolean).sort().map(time=><option key={time}>{time}</option>)}</Select>:<span className="date-time-value return-time" aria-label={az?'Qaytarma vaxtı, götürmə vaxtı ilə eyni':'Return time, same as pickup'}>{values.pickup.slice(11)||'12:00'}</span>}
          </div>
        </div>
      </div>;
    })}
    {open&&<section ref={calendar} className="date-calendar" id={`${id}-calendar`} style={{top:calendarPosition.top,left:calendarPosition.left}} role="dialog" aria-modal="false" aria-labelledby={`${id}-calendar-title`}>
      <div className="date-calendar-heading">
        <div><p className="date-calendar-step">{az?(active==='pickup'?'1 · Götürmə':'2 · Qaytarma'):(active==='pickup'?'1 · Pickup':'2 · Return')}</p><h3 id={`${id}-calendar-title`}>{az?(active==='pickup'?'Götürmə tarixini seçin':'Qaytarma tarixini seçin'):(active==='pickup'?'Choose pickup date':'Choose return date')}</h3></div>
        <div className="date-calendar-nav"><button type="button" aria-label={az?'Əvvəlki ay':'Previous month'} disabled={previousMonthDisabled} onClick={()=>setMonth(new Date(month.getFullYear(),month.getMonth()-1,1,12))}><CaretLeft size={18}/></button><b>{monthTitle}</b><button type="button" aria-label={az?'Növbəti ay':'Next month'} onClick={()=>setMonth(new Date(month.getFullYear(),month.getMonth()+1,1,12))}><CaretRight size={18}/></button></div>
      </div>
      <div className="date-calendar-grid" role="grid" aria-label={monthTitle}>
        {weekdays.map((day,index)=><span className="date-weekday" role="columnheader" key={index}>{day}</span>)}
        {days.map(day=>{
          const key=dateKey(day),outside=day.getMonth()!==month.getMonth(),isPickup=key===pickup,isReturn=key===returnAt;
          const inRange=key>pickup&&key<returnAt;
          const disabled=active==='pickup'?key<today:key<=pickup;
          return <button type="button" role="gridcell" key={key} className={'date-day'+(outside?' is-outside':'')+(inRange?' is-in-range':'')+((isPickup||isReturn)?' is-selected':'')} aria-label={new Intl.DateTimeFormat(locale,{weekday:'long',day:'numeric',month:'long',year:'numeric',timeZone:'UTC'}).format(new Date(key+'T12:00:00Z'))} aria-selected={isPickup||isReturn} disabled={disabled} onClick={()=>choose(day)}>{day.getDate()}{(isPickup||isReturn)&&<Check className="date-day-check" size={11} weight="bold"/>}</button>;
        })}
      </div>
      <div className="date-calendar-footer"><span>{active==='returnAt'&&pickupChosen?(az?`Götürmə: ${pretty(pickup)}`:`Pickup: ${pretty(pickup)}`):(az?'Tarixlər Bakı vaxtı ilə göstərilir':'Dates shown in Baku time')}</span><button type="button" onClick={close}>{az?'Bağla':'Done'}</button></div>
    </section>}
  </div>;
}
