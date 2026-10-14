'use client';
import {Select} from '@/components/Select';
import {DateRangePicker} from '@/components/DateRangePicker';
import {MapPin,MagnifyingGlass} from '@phosphor-icons/react';
import {useId} from 'react';
import {sameTimeReturn} from '@/lib/rental-search';
import type {Branch,Language,SearchValues} from '@/types/chat';
export function SearchForm({values,branches,language,onChange,onSubmit,busy,compact=false}:{values:SearchValues;branches:Branch[];language:Language;onChange:(values:SearchValues)=>void;onSubmit:()=>void;busy:boolean;compact?:boolean}){
  const id=useId(),az=language==='az';
  const change=(next:SearchValues)=>onChange(sameTimeReturn(next));
  return <form className={'rental-search '+(compact?'rental-search--compact':'')} onSubmit={e=>{e.preventDefault();onSubmit();}}>
    <div className="search-field location-field"><MapPin size={22}/><div><label htmlFor={id+'-location'}>{az?'Götürmə məntəqəsi':'Pickup location'}</label><Select id={id+'-location'} value={values.branch} onChange={e=>onChange({...values,branch:e.target.value})} required><option value="">{az?'Məntəqə seçin':'Choose a branch'}</option>{branches.map(b=><option key={b.id} value={b.id}>{az?b.name_az:b.name_en}</option>)}</Select></div></div>
    <DateRangePicker values={values} language={language} onChange={change}/>
    <button type="submit" className="primary search-submit" disabled={busy||!branches.length}><MagnifyingGlass size={20}/>{az?'Axtar':'Search'}</button>
  </form>;
}
