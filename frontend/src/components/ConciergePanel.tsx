'use client';
import {Select} from '@/components/Select';
import {conciergeWidthBounds} from '@/lib/concierge-sizing';
import {ArrowUpRight,DotsSixVertical,Headset,PaperPlaneRight,Plus,Sparkle,X} from '@phosphor-icons/react';
import {useEffect,useRef,useState} from 'react';
import {CardRenderer} from './CardRenderer';
import type {Card,Vehicle} from '@/types/chat';
import type {useConversation} from '@/hooks/useConversation';
type Chat=ReturnType<typeof useConversation>;
export function ConciergePanel({chat,width,onResize,onClose,onSelect,onExtra}:{chat:Chat;width:number;onResize:(clientX:number)=>void;onClose:()=>void;onSelect:(c:Vehicle)=>void;onExtra:(id:string)=>void}){
  const [text,setText]=useState(''),[resizing,setResizing]=useState(false),end=useRef<HTMLDivElement>(null),input=useRef<HTMLTextAreaElement>(null),az=chat.language==='az';
  const {min,max}=conciergeWidthBounds(typeof window==='undefined'?1600:window.innerWidth);
  useEffect(()=>{const previous=document.activeElement as HTMLElement|null;input.current?.focus({preventScroll:true});return()=>previous?.focus({preventScroll:true});},[]);
  useEffect(()=>{end.current?.scrollIntoView({behavior:'instant',block:'nearest'});},[chat.messages,chat.busy]);
  const send=async(value=text)=>{if(!value.trim()||chat.busy||!chat.id)return;setText('');await chat.send('TEXT_MESSAGE',{text:value});};
  const confirm=(card:Card)=>chat.send('CONFIRM_DRAFT',{draft_id:card.draft_id,quote_id:card.quote_id,expected_reservation_version:card.expected_reservation_version});
  const resizeHandle=(
    <div className={'concierge-resize-handle'+(resizing?' is-resizing':'')} role="separator" aria-orientation="vertical" aria-label={az?'AI köməkçi panelinin enini dəyiş':'Resize AI concierge panel'} aria-controls="ai-concierge" aria-valuenow={width} aria-valuemin={min} aria-valuemax={max} tabIndex={0} title={az?'Panelin enini dəyişmək üçün sürüşdürün':'Drag to resize the panel'}
      onPointerDown={event=>{event.preventDefault();event.currentTarget.setPointerCapture(event.pointerId);setResizing(true);}}
      onPointerMove={event=>{if(resizing)onResize(event.clientX);}}
      onPointerUp={event=>{if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId);setResizing(false);}}
      onPointerCancel={()=>setResizing(false)}
      onKeyDown={event=>{if(event.key==='ArrowLeft'){event.preventDefault();onResize(8+width-24);}else if(event.key==='ArrowRight'){event.preventDefault();onResize(8+width+24);}else if(event.key==='Home'){event.preventDefault();onResize(0);}else if(event.key==='End'){event.preventDefault();onResize(Number.MAX_SAFE_INTEGER);}}}
    ><DotsSixVertical size={19} weight="bold"/></div>
  );
  return <aside id="ai-concierge" className={'concierge-panel'+(resizing?' is-resizing':'')} style={{width}} aria-label={az?'AI köməkçi':'AI concierge'} onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();onClose();}}}>
    {resizeHandle}
    <div className="concierge-heading"><span className="assistant-mark"><Sparkle size={23} weight="fill"/></span><div><h2>{az?'Yol köməkçisi':'Yol concierge'}</h2><p>{chat.human?(az?'Mütəxəssis dəstəyi':'Specialist support'):(az?'Sizin şəxsi icarə köməkçiniz':'Your personal rental assistant')}</p></div><div className="concierge-controls"><button className="icon-button" type="button" aria-label={az?'Köməkçini bağla':'Close concierge'} onClick={onClose}><X size={19}/></button></div></div>
    <div className="chat-tools"><Select aria-label={az?'Söhbəti seçin':'Choose a chat'} value={chat.id} disabled={chat.busy||!chat.id} onChange={e=>chat.openChat(e.target.value)}>{chat.conversations.map((c,i)=><option key={c.id} value={c.id}>{c.preview?.trim().slice(0,32)||`${az?'Yeni söhbət':'New chat'} ${i+1}`}</option>)}</Select><button type="button" className="icon-button" aria-label={az?'Yeni söhbət':'New chat'} disabled={chat.busy||!chat.id} onClick={chat.newChat}><Plus size={20}/></button></div>
    <div className="messages" aria-live="polite" aria-busy={chat.busy}>
      {!chat.messages.length&&<div className="chat-welcome"><Sparkle size={30} weight="fill"/><h3>{az?'Səfərinizi birlikdə planlaşdıraq.':'Let’s find your kind of car.'}</h3><p>{az?'Hara getdiyinizi və nə istədiyinizi yazın. Uyğun avtomobilləri tapa və icarə qaydalarını izah edə bilərəm.':'Tell me where you’re going and what you need. I can find cars and explain the rental details.'}</p><div className="chat-suggestions">{(az?['Ailə səfəri üçün SUV tap','İcarə qaydalarını izah et','Rezervasiyamı dəyişmək istəyirəm']:['Find an SUV for a family trip','Explain the rental policies','Help me change my reservation']).map(value=><button type="button" disabled={chat.busy||!chat.id} key={value} onClick={()=>send(value)}>{value}<ArrowUpRight size={17}/></button>)}</div></div>}
      {chat.messages.map(message=><div key={message.id} className={'message '+(message.role==='USER'?'from-user':'from-assistant')}>
        {message.role!=='USER'&&<div className="message-byline">{message.role==='ADMIN'?<Headset size={17}/>:<Sparkle size={17} weight="fill"/>}{message.role==='ADMIN'?(az?'Mütəxəssis':'Rental specialist'):(az?'Yol köməkçisi':'Yol concierge')}</div>}
        {message.text&&<div className="bubble">{message.text}</div>}
        {!!message.cards.length&&<div className="cards">{message.cards.map((card,index)=><CardRenderer key={index} card={card} language={chat.language} disabled={chat.busy} onSelect={c=>onSelect(c as Vehicle)} onConfirm={confirm} onExtra={onExtra} onDecline={id=>chat.send('DECLINE_UPSELL',{extra_id:id})}/>)}</div>}
      </div>)}
      {chat.busy&&<p className="thinking" role="status"><span className="thinking-dots"><span/><span/><span/></span>{az?'Seçimləri yoxlayıram…':'Checking the details…'}</p>}<div ref={end}/>
    </div>
    {chat.error&&<div className="error-banner" role="alert">{chat.error}<button type="button" disabled={chat.busy} onClick={chat.retry}>{az?'Yenidən cəhd et':'Retry'}</button></div>}
    <form className="composer" onSubmit={e=>{e.preventDefault();send();}}><label className="sr-only" htmlFor="concierge-message">{az?'Mesaj':'Message'}</label><textarea ref={input} id="concierge-message" rows={2} value={text} onChange={e=>setText(e.target.value)} maxLength={20000} placeholder={az?'Səfəriniz və ya sualınız…':'Ask about cars, dates, or rental details…'} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();send();}}}/><button type="submit" disabled={chat.busy||!chat.id||!text.trim()} aria-label={az?'Mesajı göndər':'Send message'}><PaperPlaneRight size={22} weight="fill"/></button></form>
    <p className="conversation-footer">{az?'AI cavabları səhv ola bilər. Söhbət yerli saxlanılır; müvafiq mətn OpenAI-yə göndərilir.':'AI can make mistakes. Chat is stored locally; relevant context is sent to OpenAI.'}</p>
    <button className="specialist-link" type="button" disabled={chat.busy||!chat.id||chat.human} onClick={()=>chat.send('HANDOFF')}><Headset size={18}/>{chat.human?(az?'Mütəxəssis dəstəyi aktivdir':'Specialist support is active'):(az?'Mütəxəssislə danış':'Talk to a rental specialist')}</button>
  </aside>;
}
