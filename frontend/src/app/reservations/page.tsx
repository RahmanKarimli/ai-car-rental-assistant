'use client';
import {useEffect,useState} from 'react';
import {api,initializeSession} from '@/lib/api';
import {CardRenderer} from '@/components/CardRenderer';
import type {Language} from '@/types/chat';
export default function Reservations(){
 const [rows,setRows]=useState<any[]>([]),[error,setError]=useState(''),[loading,setLoading]=useState(true),[language,setLanguage]=useState<Language>('en');
 const az=language==='az';
 useEffect(()=>{
  const selectedLanguage=localStorage.getItem('yol-language')==='az'?'az':'en';setLanguage(selectedLanguage);
  initializeSession().then(()=>api<any[]>('/reservations?language='+selectedLanguage)).then(setRows).catch(e=>setError(e.message)).finally(()=>setLoading(false));
 },[]);
 return <main className="booking-page"><a className="brand" href="/">yol.</a><h1>{az?'Rezervasiyalarım':'My reservations'}</h1>{error&&<p className="form-error">{error}</p>}<div className="cards">{rows.map(row=><CardRenderer key={row.reservation_id} card={row} language={language}/>)}</div>{loading?<p>{az?'Yüklənir…':'Loading…'}</p>:!rows.length&&!error&&<div className="notice">{az?'Təsdiqlənmiş rezervasiyalarınız burada görünəcək.':'Your confirmed reservations will appear here.'} <a className="text-link" href="/">{az?'Uyğun avtomobil tapın →':'Find your next car →'}</a></div>}</main>;
}
