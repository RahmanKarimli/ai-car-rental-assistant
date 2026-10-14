'use client';
import {Children,isValidElement,useEffect,useId,useLayoutEffect,useMemo,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {CaretDown,Check} from '@phosphor-icons/react';
import type {ReactNode} from 'react';

type Props={children:ReactNode;value?:string|number;onChange:(event:{target:{value:string}})=>void;id?:string;name?:string;disabled?:boolean;required?:boolean;className?:string;'aria-label'?:string;'aria-describedby'?:string;icon?:ReactNode;menuWidth?:number};
export function Select({children,value='',onChange,id,name,disabled,required,className='',icon,menuWidth=200,...aria}:Props){
  const uid=useId(),listId=uid+'-list',trigger=useRef<HTMLButtonElement>(null),menu=useRef<HTMLDivElement>(null),search=useRef(''),searchTimer=useRef<ReturnType<typeof setTimeout>|null>(null);
  const [open,setOpen]=useState(false),[active,setActive]=useState(0),[invalid,setInvalid]=useState(false),[position,setPosition]=useState({top:0,left:0,width:200,maxHeight:280});
  const options=useMemo(()=>Children.toArray(children).filter(isValidElement).map(child=>{const p=child.props as {value?:string|number;children:ReactNode;disabled?:boolean};return {value:String(p.value??p.children??''),label:p.children,disabled:!!p.disabled};}),[children]);
  const selected=options.findIndex(option=>option.value===String(value));
  const choose=(index:number)=>{const option=options[index];if(!option||option.disabled)return;search.current='';if(searchTimer.current)clearTimeout(searchTimer.current);onChange({target:{value:option.value}});setInvalid(false);setOpen(false);trigger.current?.focus({preventScroll:true});};
  const show=()=>{if(disabled)return;setActive(Math.max(0,selected));setOpen(true);};
  useLayoutEffect(()=>{
    if(!open)return;
    const place=()=>{const r=trigger.current!.getBoundingClientRect(),width=Math.min(Math.max(r.width,menuWidth),window.innerWidth-16),spaceBelow=window.innerHeight-r.bottom-16,spaceAbove=r.top-16,above=spaceBelow<Math.min(280,options.length*44+16)&&spaceAbove>spaceBelow,maxHeight=Math.max(44,Math.min(280,above?spaceAbove:spaceBelow));setPosition({width,left:Math.max(8,Math.min(r.left,window.innerWidth-width-8)),top:above?r.top-Math.min(maxHeight,options.length*44+16)-8:r.bottom+8,maxHeight});};
    place();const outside=(event:PointerEvent)=>{if(!trigger.current?.contains(event.target as Node)&&!menu.current?.contains(event.target as Node))setOpen(false);};
    window.addEventListener('resize',place);window.addEventListener('scroll',place,true);document.addEventListener('pointerdown',outside);
    return()=>{window.removeEventListener('resize',place);window.removeEventListener('scroll',place,true);document.removeEventListener('pointerdown',outside);};
  },[open,menuWidth,options.length]);
  useEffect(()=>{if(open)menu.current?.querySelector('[data-active="true"]')?.scrollIntoView({block:'nearest'});},[active,open]);
  useEffect(()=>{if(disabled)setOpen(false);},[disabled]);
  useEffect(()=>()=>{if(searchTimer.current)clearTimeout(searchTimer.current);},[]);
  const move=(direction:number)=>{let index=active;for(let i=0;i<options.length;i++){index=(index+direction+options.length)%options.length;if(!options[index].disabled){setActive(index);return;}}};
  return <div className={'custom-select '+className}>
    <button ref={trigger} type="button" id={id} className="select-trigger" role="combobox" aria-haspopup="listbox" aria-expanded={open} aria-controls={open?listId:undefined} aria-activedescendant={open?listId+'-'+active:undefined} aria-required={required||undefined} aria-invalid={invalid||undefined} {...aria} disabled={disabled} onClick={()=>open?setOpen(false):show()} onKeyDown={e=>{
      if(e.key==='Escape'){if(open){e.preventDefault();e.stopPropagation();setOpen(false);}return;}
      if(e.key==='Tab'){setOpen(false);return;}
      if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();if(!open)show();else move(e.key==='ArrowDown'?1:-1);return;}
      if(e.key==='Home'||e.key==='End'){e.preventDefault();if(!open)show();setActive(e.key==='Home'?0:options.length-1);return;}
      if(e.key==='Enter'||e.key===' '){e.preventDefault();if(open)choose(active);else show();return;}
      if(e.key.length===1&&!e.metaKey&&!e.ctrlKey&&!e.altKey){e.preventDefault();search.current+=e.key.toLocaleLowerCase();if(searchTimer.current)clearTimeout(searchTimer.current);searchTimer.current=setTimeout(()=>{search.current='';},600);const index=options.findIndex(option=>!option.disabled&&String(option.label).toLocaleLowerCase().startsWith(search.current));if(index>=0){setActive(index);setOpen(true);}}
    }}>{icon}<span className="select-value">{options[selected]?.label??options[0]?.label??''}</span><CaretDown size={14} className="select-caret"/></button>
    {(required||name)&&<select hidden className="select-validation" aria-hidden="true" tabIndex={-1} name={name} required={required} value={value} onChange={e=>onChange({target:{value:e.target.value}})} onInvalid={e=>{e.preventDefault();setInvalid(true);show();trigger.current?.focus();}}>{children}</select>}
    {open&&createPortal(<div ref={menu} id={listId} role="listbox" aria-label={aria['aria-label']} className="select-menu" style={position}>{options.map((option,index)=><div role="option" aria-selected={index===selected} aria-disabled={option.disabled||undefined} id={listId+'-'+index} key={option.value+'-'+index} data-active={active===index} className={'select-option '+(index===selected?'is-selected':'')} onPointerMove={()=>{if(!option.disabled)setActive(index);}} onPointerDown={e=>e.preventDefault()} onClick={()=>choose(index)}><span>{option.label}</span>{index===selected&&<Check size={17} weight="bold"/>}</div>)}</div>,document.body)}
  </div>;
}
