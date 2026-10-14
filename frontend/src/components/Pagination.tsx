'use client';
import {CaretLeft,CaretRight} from '@phosphor-icons/react';
import type {Language} from '@/types/chat';
export function Pagination({page,pages,total,pageSize,count,onChange,busy,language}:{page:number;pages:number;total:number;pageSize:number;count:number;onChange:(page:number)=>void;busy:boolean;language:Language}){
  const az=language==='az',start=Math.max(1,Math.min(page-2,pages-4));
  const numbers=Array.from({length:Math.min(5,pages)},(_,i)=>start+i);
  if(!total)return null;
  return <div className="fleet-pagination"><p role="status">{az?'Göstərilir':'Showing'} {(page-1)*pageSize+1}–{(page-1)*pageSize+count} / {total} {az?'avtomobil':'cars'}</p><nav aria-label={az?'Avtomobil səhifələri':'Car pages'}><button type="button" className="page-button" disabled={page===1||busy} aria-label={az?'Əvvəlki səhifə':'Previous page'} onClick={()=>onChange(page-1)}><CaretLeft size={18}/></button>{start>1&&<><button className="page-button" type="button" disabled={busy} aria-label={az?'Səhifə 1':'Page 1'} onClick={()=>onChange(1)}>1</button>{start>2&&<span className="page-ellipsis">…</span>}</>}{numbers.map(n=><button className={'page-button '+(n===page?'is-current':'')} type="button" key={n} disabled={busy} aria-current={n===page?'page':undefined} aria-label={(az?'Səhifə ':'Page ')+n} onClick={()=>onChange(n)}>{n}</button>)}{numbers.at(-1)!<pages&&<>{numbers.at(-1)!<pages-1&&<span className="page-ellipsis">…</span>}<button className="page-button" type="button" disabled={busy} aria-label={(az?'Səhifə ':'Page ')+pages} onClick={()=>onChange(pages)}>{pages}</button></>}<button type="button" className="page-button" disabled={page===pages||busy} aria-label={az?'Növbəti səhifə':'Next page'} onClick={()=>onChange(page+1)}><CaretRight size={18}/></button></nav></div>;
}
