'use client';
import {useEffect,useState} from 'react';
import {usePathname} from 'next/navigation';
import {Car as CarFront,ArrowUpRight,ArrowsClockwise as RefreshCw} from '@phosphor-icons/react';
import {api,initializeSession,mutation,setSession} from '@/lib/api';
import {AdminDataBrowser} from '@/components/AdminDataBrowser';
import {formatRentalDate} from '@/lib/dates';
const menus=['overview','fleet','pricing','policies','data','conversations','escalations','reservations','privacy'];
const descriptions:Record<string,string>={
 overview:'Booking activity and operational setup at a glance.',
 fleet:'Manage pickup offices, physical vehicles, optional extras and car photos.',
 pricing:'Create versioned pricing plans and seasonal or fixed-fee rules. Amounts are stored in AZN qəpiks.',
 policies:'Manage bilingual policy documents and publish the operational rules enforced during booking.',
 data:'Browse all 28 application tables, read record details and manage editable data. Each table and field includes an explanation.',
 conversations:'Read the complete, unredacted customer history and contact details. Send messages during a human handoff.',
 escalations:'Review requests requiring a human decision, assign ownership and record the resolution.',
 reservations:'Read current bookings and manage modifications or cancellation through an itemized draft and confirmation.',
 privacy:'Manually review conversations due for retention review. Contractual booking records and audit history are retained.',
};
const ruleFields=[
 {name:'minimum_driver_age',label:'Minimum driver age',help:'Youngest eligible driver, in years. Must match the reviewed policy documents.',min:16,max:100,value:21},
 {name:'maximum_rental_days',label:'Maximum rental days',help:'Longest allowed rental, in whole days.',min:1,max:365,value:30},
 {name:'modification_fee_qepik',label:'Modification fee',help:'Fee for a confirmed booking change, in AZN qəpiks. 100 qəpiks = 1 AZN.',min:0,value:0},
 {name:'cancellation_fee_qepik',label:'Cancellation fee',help:'Late cancellation fee, in AZN qəpiks.',min:0,value:0},
 {name:'cancellation_free_hours',label:'Free cancellation window',help:'Minimum hours before pickup for cancellation without a fee.',min:0,value:24},
];
export function AdminConsole(){
 const path=usePathname(),parts=path.split('/').filter(Boolean),section=parts[1]||'overview',conversationId=parts[2];
 const [role,setRole]=useState(''),[email,setEmail]=useState(''),[password,setPassword]=useState('');
 const [error,setError]=useState(''),[notice,setNotice]=useState(''),[rows,setRows]=useState<any[]>([]),[stats,setStats]=useState<any>({});
 const [documentKey,setDocumentKey]=useState(''),[version,setVersion]=useState('1');
 const [rules,setRules]=useState<Record<string,string>>(Object.fromEntries(ruleFields.map(field=>[field.name,String(field.value)])));
 const [adminText,setAdminText]=useState(''),[selected,setSelected]=useState<any>(null),[busy,setBusy]=useState(false),[refreshKey,setRefreshKey]=useState(0);
 const load=async()=>{
  try{
   setError('');
   if(['fleet','pricing','policies','data'].includes(section)){setRefreshKey(previous=>previous+1);return}
   if(section==='overview')setStats(await api('/admin/analytics'));
   else if(section==='conversations'&&conversationId){const result=await api<any>('/admin/conversations/'+conversationId);setRows(result.messages);setSelected(result.conversation)}
   else if(section==='conversations')setRows(await api<any[]>('/admin/conversations'));
   else if(section==='privacy')setRows(await api<any[]>('/admin/privacy/due'));
   else setRows(await api<any[]>('/admin/'+section));
  }catch(e){setError((e as Error).message)}
 };
 useEffect(()=>{initializeSession().then(session=>setRole(session.role)).catch(e=>setError(e.message))},[]);
 useEffect(()=>{if(role==='ADMIN'||role==='SUPPORT')load()},[role,section,conversationId]);
 const action=async(fn:()=>Promise<unknown>)=>{setBusy(true);setNotice('');setError('');try{await fn();setNotice('Saved.');await load()}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const login=async()=>{try{const result=await api<any>('/auth/login',mutation({email,password}));setSession(result.csrf_token);setRole(result.role);setPassword('')}catch(e){setError((e as Error).message)}};
 if(role!=='ADMIN'&&role!=='SUPPORT')return <div className="admin-shell"><a className="brand" href="/"><span className="brand-icon"><CarFront size={20}/></span>yol.</a><div className="admin-page login"><h1>Operator sign in</h1><p className="muted-small">Review conversations and manage your rental fleet.</p><label htmlFor="operator-email">Email</label><input id="operator-email" type="email" value={email} onChange={event=>setEmail(event.target.value)}/><label htmlFor="operator-password">Password</label><input id="operator-password" type="password" value={password} onChange={event=>setPassword(event.target.value)} onKeyDown={event=>event.key==='Enter'&&login()}/><button className="primary full" style={{marginTop:22}} onClick={login}>Sign in<ArrowUpRight size={15}/></button>{error&&<p className="form-error">{error}</p>}<p className="muted-small" style={{marginTop:20}}>Create the first operator with the administrator bootstrap command in the README.</p></div></div>;
 return <main className="admin-shell">
  <header style={{display:'flex',alignItems:'center',justifyContent:'space-between'}}><a className="brand" href="/"><span className="brand-icon"><CarFront size={20}/></span>yol.</a><span className="muted-small">Operator console · {role}</span></header>
  <nav className="admin-nav">{menus.filter(item=>role==='ADMIN'||['escalations','conversations'].includes(item)).map(item=><a className={item===section?'active':''} key={item} href={'/admin/'+(item==='overview'?'':item)}>{item==='data'?'Database tables':item.charAt(0).toUpperCase()+item.slice(1)}</a>)}</nav>
  <section className="admin-page"><div className="data-heading"><div><h1>{section==='data'?'Database tables':section.charAt(0).toUpperCase()+section.slice(1)}</h1><p className="admin-description">{descriptions[section]}</p></div><button className="round-action" onClick={load} aria-label="Refresh"><RefreshCw size={17}/></button></div>
   {error&&<div className="error-banner" role="alert">{error}</div>}{notice&&<div className="notice" role="status">{notice}</div>}
   {section==='overview'&&<><div className="stat-grid">{[['conversations','Conversations'],['bookings','Completed booking actions'],['cancelled','Cancelled reservations'],['open_cases','Open support cases']].map(([key,label])=><div className="stat" key={key}><b>{stats[key]||0}</b><span>{label}</span></div>)}</div><div className="notice">Setup order: create and publish bilingual policy documents → publish matching operational rules → create rate plans and their pricing rules → add branches and vehicles.</div><a className="secondary" href="/admin/data">Browse tables and manage records</a></>}
   {role==='ADMIN'&&section==='fleet'&&<AdminDataBrowser tables={['branches','vehicles','extras','vehicle_photos']} initialTable="branches" refreshKey={refreshKey}/>}
   {role==='ADMIN'&&section==='pricing'&&<AdminDataBrowser tables={['rate_plans','pricing_rules','rental_policies']} initialTable="rate_plans" refreshKey={refreshKey}/>}
   {role==='ADMIN'&&section==='data'&&<AdminDataBrowser refreshKey={refreshKey}/>}
   {role==='ADMIN'&&section==='policies'&&<>
    <AdminDataBrowser tables={['policy_documents','rental_policies','policy_chunks']} initialTable="policy_documents" refreshKey={refreshKey}/>
    <form className="data-detail data-form" onSubmit={event=>{event.preventDefault();action(()=>api('/admin/rental-policies',mutation({bundle_key:documentKey,version:Number(version),rules:Object.fromEntries(Object.entries(rules).map(([key,value])=>[key,Number(value)]))})))}}>
     <h3>Publish operational rules</h3><p className="field-help">These rules are enforced by the booking engine. Review both language documents first and use the same bundle key and version. Values below are editable examples until you publish.</p>
     <div className="data-form-grid"><div><label htmlFor="rule-bundle">Policy bundle key *</label><input id="rule-bundle" required pattern="[a-z0-9_-]+" value={documentKey} onChange={event=>setDocumentKey(event.target.value)}/><p className="field-help">Shared document key of the already published English and Azerbaijani pair.</p></div><div><label htmlFor="rule-version">Policy version *</label><input id="rule-version" type="number" min="1" step="1" required value={version} onChange={event=>setVersion(event.target.value)}/><p className="field-help">Version of that published bilingual pair. Existing operational versions remain unchanged.</p></div>{ruleFields.map(field=><div key={field.name}><label htmlFor={'rule-'+field.name}>{field.label} *</label><input id={'rule-'+field.name} required type="number" step="1" min={field.min} max={field.max} value={rules[field.name]} onChange={event=>setRules(previous=>({...previous,[field.name]:event.target.value}))}/><p className="field-help">{field.help}</p></div>)}</div>
     <button disabled={busy} className="primary" style={{marginTop:20}} type="submit">Publish operational policy version</button>
    </form>
   </>}
   {section==='conversations'&&!conversationId&&<div className="data-table-wrap"><table className="admin-table"><thead><tr><th title="Unredacted customer name and phone number">Customer</th><th title="az: Azerbaijani; en: English">Language</th><th title="ACTIVE: automated; HUMAN: operator handoff; CLOSED: ended">Status</th><th title="Most recent conversation activity, shown in Baku time">Last activity</th><th>Actions</th></tr></thead><tbody>{rows.map(row=><tr key={row.id}><td>{row.contact_name||'Guest'}<br/>{row.contact_phone}</td><td>{row.language}</td><td>{row.status}</td><td>{formatRentalDate(row.last_activity_at,'en')}</td><td><a className="text-link" href={'/admin/conversations/'+row.id}>Open full history</a>{role==='ADMIN'&&<a className="text-link" href={`/admin/data?table=conversations&record=${row.id}`}>Fields and descriptions</a>}</td></tr>)}</tbody></table></div>}
   {section==='conversations'&&conversationId&&<><div className="notice">{selected?.contact_name} · {selected?.contact_phone} · {selected?.contact_email} · {selected?.status}</div>{role==='ADMIN'&&<a className="text-link" href={`/admin/data?table=conversations&record=${conversationId}`}>Read conversation fields and descriptions</a>}{rows.map(row=><div className="record" key={row.id}><b>{row.role} · {formatRentalDate(row.created_at,'en')}</b><p className="field-help">Original message text</p><pre>{row.raw_content}</pre>{row.payload&&<><p className="field-help">Structured message details and visual cards</p><pre>{JSON.stringify(row.payload,null,2)}</pre></>}</div>)}<button className="secondary" onClick={async()=>{try{const data=await api<any>(`/admin/conversations/${conversationId}?after=${rows.at(-1)?.sequence||0}`);setRows(previous=>[...previous,...data.messages])}catch(e){setError((e as Error).message)}}}>Load more history</button><label htmlFor="operator-message">Message customer during human takeover</label><textarea id="operator-message" value={adminText} onChange={event=>setAdminText(event.target.value)}/><p className="field-help">Sent to the customer and stored in the original conversation history with your operator role.</p><button disabled={busy||!adminText.trim()} className="primary" onClick={()=>action(()=>api('/admin/conversations/'+conversationId+'/messages',mutation({text:adminText})))}>Send message</button></>}
   {section==='escalations'&&rows.map(row=><div className="record" key={row.id}><b>{row.reason_code}</b><p className="field-help">Reason category for administrator review</p><p>{row.summary}</p><p className="muted-small">{row.status} · Conversation: {row.conversation_id}</p><div className="inline-actions"><a className="text-link" href={'/admin/conversations/'+row.conversation_id}>View conversation</a>{role==='ADMIN'&&<><a className="text-link" href={`/admin/data?table=escalation_cases&record=${row.id}`}>All fields</a><button disabled={busy} onClick={()=>action(()=>api('/admin/escalations/'+row.id+'/claim',{method:'POST'}))}>Take ownership</button><button disabled={busy} onClick={()=>{const reason=prompt('Resolution reason');if(reason)action(()=>api('/admin/escalations/'+row.id+'/resolve',mutation({decision:'RESUME',reason})))}}>Resolve and resume</button>{row.reason_code==='MANUAL_DISCOUNT'&&<button disabled={busy} onClick={()=>{const amount=prompt('Approved discount in AZN qəpiks');const reason=prompt('Approval reason');if(amount&&reason)action(()=>api('/admin/escalations/'+row.id+'/resolve',mutation({decision:'APPROVE_DISCOUNT',discount_qepik:Number(amount),reason})))}}>Approve discount</button>}</>}</div></div>)}
   {section==='reservations'&&<div className="data-table-wrap"><table className="admin-table"><thead><tr><th title="Customer-facing booking identifier">Reference</th><th title="Contractual renter name and phone">Customer</th><th title="Scheduled pickup in Baku time">Pickup</th><th title="Current booking state">Status</th><th title="Calculated rental charge; 100 qəpiks = 1 AZN">Total qəpiks</th><th>Actions</th></tr></thead><tbody>{rows.map(row=><tr key={row.id}><td>{row.public_reference}</td><td>{row.renter_contact?.name}<br/>{row.renter_contact?.phone}</td><td>{formatRentalDate(row.pickup_at,'en')}</td><td>{row.status}</td><td>{row.total_qepik}</td><td><a className="text-link" href={'/reservations/'+row.id}>Manage booking</a><a className="text-link" href={`/admin/data?table=reservations&record=${row.id}`}>Read all fields</a></td></tr>)}</tbody></table></div>}
   {section==='privacy'&&<><div className="notice">Purging deletes eligible chat history, contact/session context and graph checkpoints. Contractual reservation records and booking audits are preserved.</div>{rows.map(row=><div className="record" key={row.id}><b>{row.contact_name||row.id}</b><p className="field-help">Retention review due: {formatRentalDate(row.retention_due_at,'en')}</p><div className="inline-actions"><a className="text-link" href={`/admin/data?table=conversations&record=${row.id}`}>Review fields</a><button disabled={busy} onClick={()=>{const reason=prompt('Reason for retention extension');if(reason)action(()=>api('/admin/privacy/'+row.id+'/review',mutation({action:'EXTEND',reason,months:3})))}}>Extend 3 months</button><button disabled={busy} onClick={()=>{const reason=prompt('Deletion reason; this removes the complete chat history');if(reason&&confirm('Permanently delete this eligible chat history?'))action(()=>api('/admin/privacy/'+row.id+'/review',mutation({action:'PURGE',reason})))}}>Delete eligible history</button></div></div>)}</>}
   {rows.length===0&&['conversations','escalations','reservations','privacy'].includes(section)&&<p className="muted-small" style={{marginTop:20}}>No records yet.</p>}
  </section>
 </main>;
}
