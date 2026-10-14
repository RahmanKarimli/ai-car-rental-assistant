'use client';
import {useState,useEffect,useCallback,useRef} from 'react';
import {api,initializeSession} from '@/lib/api';
import type {Message,ChatResponse,Language} from '@/types/chat';
type ConversationSummary={id:string;language:Language;status:string;last_activity_at:string;preview:string|null};
export function useConversation(){
 const [id,setId]=useState(''),[messages,setMessages]=useState<Message[]>([]),[language,setLanguage]=useState<Language>('en'),[busy,setBusy]=useState(false),[error,setError]=useState(''),[human,setHuman]=useState(false),[preferences,setPreferences]=useState<any>({}),[conversations,setConversations]=useState<ConversationSummary[]>([]);
 const pending=useRef<any>(null),generation=useRef(0);
 const [preferencesEvent,setPreferencesEvent]=useState('RESTORE');
 useEffect(()=>{document.documentElement.lang=language},[language]);
 const refreshConversations=useCallback(async()=>setConversations(await api<ConversationSummary[]>('/conversations')),[]);
 const load=useCallback(async(conversationId:string,version:number,source='RESTORE')=>{let after=0;const logs:any[]=[];let data:any;do{data=await api<any>(`/conversations/${conversationId}?after=${after}&limit=200`);logs.push(...data.messages);after=data.messages.at(-1)?.sequence||after}while(data.messages.length===200);if(version!==generation.current)return;setLanguage(data.language);localStorage.setItem('yol-language',data.language);setHuman(data.status==='HUMAN');setPreferencesEvent(source);setPreferences(data.state?.preferences||{});setMessages(logs.map((m:any)=>({id:m.id,role:m.role,text:m.raw_content,cards:m.payload?.cards||[]})))},[]);
 useEffect(()=>{let active=true;(async()=>{try{await initializeSession();let stored=localStorage.getItem('yol-conversation');if(stored){try{await load(stored,generation.current)}catch{stored=null}}if(!stored){const c=await api<{id:string}>('/conversations',{method:'POST'});stored=c.id;localStorage.setItem('yol-conversation',stored)}if(active){setId(stored);await refreshConversations()}}catch(e){if(active)setError((e as Error).message)}})();return()=>{active=false;generation.current++}},[load,refreshConversations]);
 useEffect(()=>{if(!human||!id)return;const timer=setInterval(()=>{load(id,generation.current).catch(()=>{})},5000);return()=>clearInterval(timer)},[human,id,load]);
 const newChat=async()=>{if(busy||!id)return;setBusy(true);setError('');try{const c=await api<{id:string}>('/conversations',{method:'POST'});generation.current++;localStorage.setItem('yol-conversation',c.id);setId(c.id);setMessages([]);setHuman(false);setPreferences({});pending.current=null;setLanguage(localStorage.getItem('yol-language')==='az'?'az':'en');refreshConversations().catch(()=>{});return c.id}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const openChat=async(conversationId:string)=>{if(busy||!id||conversationId===id)return;setBusy(true);setError('');try{const version=++generation.current;await load(conversationId,version);localStorage.setItem('yol-conversation',conversationId);setId(conversationId);pending.current=null}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const send=async(kind:string,payload:any={})=>{
 if(!id||busy)return;setBusy(true);setError('');const event={kind,client_event_id:crypto.randomUUID(),...payload};pending.current=event;
 try{const result=await api<ChatResponse>(`/conversations/${id}/events`,{method:'POST',body:JSON.stringify(event)});setLanguage(result.language);setHuman(result.conversation_phase==='HUMAN_HANDOFF');await load(id,generation.current,kind);pending.current=null;refreshConversations().catch(()=>{});return result}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 };
 const retry=async()=>{if(!pending.current||busy)return;setBusy(true);try{const result=await api<ChatResponse>(`/conversations/${id}/events`,{method:'POST',body:JSON.stringify(pending.current)});await load(id,generation.current,pending.current.kind);pending.current=null;setError('');refreshConversations().catch(()=>{});return result}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 return {id,messages,language,setLanguage,busy,error,human,preferences,preferencesEvent,conversations,newChat,openChat,send,retry,hasPending:pending.current!==null};
}
