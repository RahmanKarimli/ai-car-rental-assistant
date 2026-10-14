'use client';
import {Desktop,Moon,Sun} from '@phosphor-icons/react';
import {Select} from './Select';
import {useDisplayPreferences} from '@/lib/display-preferences';
import type {Currency,Theme} from '@/lib/display-preferences';
import type {Language} from '@/types/chat';
export function DisplayControls({language}:{language:Language}){
  const {theme,setTheme,currency,setCurrency,usdAvailable}=useDisplayPreferences(),az=language==='az';
  return <>
    <Select className="currency-control" aria-label={az?'Göstərilən valyuta':'Display currency'} value={currency} onChange={e=>setCurrency(e.target.value as Currency)} menuWidth={160}><option value="AZN">AZN</option><option value="USD" disabled={!usdAvailable}>USD</option></Select>
    <Select className="theme-control" aria-label={az?'Görünüş':'Appearance'} value={theme} onChange={e=>setTheme(e.target.value as Theme)} icon={theme==='dark'?<Moon size={20}/>:theme==='light'?<Sun size={20}/>:<Desktop size={20}/>} menuWidth={190}><option value="system">{az?'Sistem':'System'}</option><option value="light">{az?'İşıqlı':'Light'}</option><option value="dark">{az?'Qaranlıq':'Dark'}</option></Select>
  </>;
}
