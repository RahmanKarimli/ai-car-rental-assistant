'use client';
import {createContext,useContext,useEffect,useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {api} from './api';
import type {Money} from '@/types/chat';
export type Theme='light'|'dark'|'system';
export type Currency='AZN'|'USD';
type Rates={base_currency:'AZN';usd:{available:boolean;azn_per_unit:string|null;effective_date:string|null;source:string}};
type Preferences={theme:Theme;setTheme:(v:Theme)=>void;currency:Currency;setCurrency:(v:Currency)=>void;rates?:Rates;rateError:boolean;formatMoney:(v:Money)=>string;usdAvailable:boolean};
const Context=createContext<Preferences|null>(null);

// Exact minor-unit arithmetic for informational USD display. Never used in a
// draft or confirmation; all signed amounts remain the server's AZN amounts.
export function informationalUsd(amount:string,rate:string):string {
  const zero=BigInt(0),two=BigInt(2),hundred=BigInt(100);
  const [whole,fraction='']=rate.split('.'),denominator=BigInt(whole+fraction),scale=BigInt(10)**BigInt(fraction.length);
  if(denominator<=zero)throw new Error('Invalid display rate');
  const raw=BigInt(amount),negative=raw<zero,numerator=(negative?-raw:raw)*scale;
  const cents=(numerator*two+denominator)/(denominator*two);
  const integer=(cents/hundred).toString().replace(/\B(?=(\d{3})+(?!\d))/g,',');
  return `≈ ${negative?'-':''}${integer}.${(cents%hundred).toString().padStart(2,'0')} USD`;
}
export function DisplayPreferencesProvider({children}:{children:React.ReactNode}){
  const [theme,setThemeState]=useState<Theme>('system'),[currency,setCurrencyState]=useState<Currency>('AZN'),[ready,setReady]=useState(false);
  const fx=useQuery({queryKey:['display-currencies'],queryFn:()=>api<Rates>('/display-currencies'),staleTime:300000});
  useEffect(()=>{try{const t=localStorage.getItem('yol-theme'),c=localStorage.getItem('yol-currency');if(t==='light'||t==='dark'||t==='system')setThemeState(t);if(c==='USD')setCurrencyState(c);}catch{}setReady(true);},[]);
  useEffect(()=>{if(!ready)return;const media=window.matchMedia('(prefers-color-scheme: dark)'),apply=()=>{document.documentElement.dataset.theme=theme==='system'?(media.matches?'dark':'light'):theme;};apply();media.addEventListener('change',apply);return()=>media.removeEventListener('change',apply);},[theme,ready]);
  const setTheme=(value:Theme)=>{setThemeState(value);try{localStorage.setItem('yol-theme',value);}catch{}};
  const setCurrency=(value:Currency)=>{setCurrencyState(value);try{localStorage.setItem('yol-currency',value);}catch{}};
  const usdAvailable=!!fx.data?.usd.available;
  const formatMoney=(money:Money)=>currency==='USD'&&usdAvailable&&fx.data?.usd.azn_per_unit?informationalUsd(money.amount_qepik,fx.data.usd.azn_per_unit):money.formatted;
  return <Context.Provider value={{theme,setTheme,currency,setCurrency,rates:fx.data,rateError:!!fx.error,usdAvailable,formatMoney}}>{children}</Context.Provider>;
}
export function useDisplayPreferences(){const value=useContext(Context);if(!value)throw new Error('Display preferences provider missing');return value;}
