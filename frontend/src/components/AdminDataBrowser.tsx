'use client';
import {Select} from '@/components/Select';

import {useEffect, useState} from 'react';
import {CaretLeft as ChevronLeft,CaretRight as ChevronRight,Database,Eye,Pencil,Plus,ArrowsClockwise as RefreshCw,Trash as Trash2,X} from '@phosphor-icons/react';
import {api, mutation} from '@/lib/api';
import {fromBakuInput, toBakuInput, formatRentalDate} from '@/lib/dates';

type Row = Record<string, any>;
type Field = {
 name:string;label:string;description:string;type:string;nullable:boolean;editable:boolean;create:boolean;
 required:boolean;hidden:boolean;reference?:string;enum?:string[];default?:any;
 minimum?:number;maximum?:number;minLength?:number;maxLength?:number;
};
type Table = {name:string;title:string;description:string;fields:Field[];can_create:boolean;can_edit:boolean;can_delete:boolean;create_mode:string;note:string};
type Page = {items:Row[];total:number;offset:number;limit:number};
type Props = {tables?:string[];initialTable?:string;refreshKey?:number};

const label = (row:Row) => row.name_en || row.public_reference || row.email || row.document_key && `${row.document_key} · ${row.language} · v${row.version}` || row.make && `${row.make} ${row.model} · ${row.registration_number}` || row.code && `${row.code}${row.version ? ` · v${row.version}` : ''}` || row.contact_name || row.event_name || row.action || row.reason_code || row.id;
const textValue = (value:any) => value===null||value===undefined?'Empty':typeof value==='object'?JSON.stringify(value,null,2):String(value);
function initialValues(table:Table,row?:Row):Row {
 return Object.fromEntries(table.fields.filter(field=>field.create||field.editable).map(field=>{
  let value=row?.[field.name]??field.default??(field.nullable?'':field.type==='boolean'?true:field.type==='json'?(field.name==='features'?[]:{}):field.type==='datetime'?new Date().toISOString():'');
  if(field.name==='password')value='';
  if(field.type==='money'&&value!=='')value=(Number(value)/100).toFixed(2);
  if(field.type==='json')value=JSON.stringify(value,null,2);
  if(field.type==='datetime'&&value)value=toBakuInput(value);
  return [field.name,value];
 }));
}
function payload(table:Table,values:Row,mode:'create'|'edit',original?:Row):Row {
 const result:Row={};
 for(const field of table.fields.filter(field=>mode==='create'?field.create:field.editable)){
  let value=values[field.name];
  if(field.type==='money'&&value!==''&&value!==null){
   const amount=Number(value);
   if(!Number.isFinite(amount)||amount<0)throw new Error(`${field.label}: enter a non-negative AZN amount.`);
   value=Math.round(amount*100);
  }
  if(mode==='edit'&&field.type==='datetime'&&original?.[field.name]&&value===toBakuInput(original[field.name]))continue;
  if(field.name==='password'&&!value&&mode==='edit')continue;
  if(value===''&&field.nullable)value=null;
  if(field.type==='json'&&value!==null){try{value=JSON.parse(value)}catch{throw new Error(`${field.label}: enter valid JSON.`)}}
  if(field.type==='datetime'&&value)value=fromBakuInput(value);
  if(field.type==='date_range'&&Array.isArray(value)&&value.every(item=>!item))value=null;
  if(mode==='edit'){
   const prior=original?.[field.name];
   // Compare timestamps by instant, since input displays Asia/Baku wall time.
   if(field.type==='datetime'&&value&&prior&&new Date(value).getTime()===new Date(prior).getTime())continue;
   if(JSON.stringify(value)===JSON.stringify(prior))continue;
   if(field.type==='integer'&&String(value)===String(prior))continue;
  }
  result[field.name]=value;
 }
 return result;
}

export function AdminDataBrowser({tables:allowed,initialTable='branches',refreshKey=0}:Props){
 const [catalog,setCatalog]=useState<Table[]>([]),[tableName,setTableName]=useState(initialTable);
 const [page,setPage]=useState<Page>({items:[],total:0,offset:0,limit:25}),[offset,setOffset]=useState(0);
 const [selected,setSelected]=useState<Row|null>(null),[mode,setMode]=useState<'view'|'create'|'edit'|null>(null);
 const [values,setValues]=useState<Row>({}),[references,setReferences]=useState<Record<string,Row[]>>({});
 const [file,setFile]=useState<File|null>(null),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [busy,setBusy]=useState(false),[loading,setLoading]=useState(true),[deleting,setDeleting]=useState(false);
 const [deleteText,setDeleteText]=useState(''),[generation,setGeneration]=useState(0),[referenceError,setReferenceError]=useState('');
 const table=catalog.find(item=>item.name===tableName);
 const visibleTables=catalog.filter(item=>!allowed||allowed.includes(item.name));
 const writable=table?.can_edit&&(table.name!=='policy_documents'||selected?.status==='DRAFT');
 const removable=table?.can_delete&&(table.name!=='policy_documents'||selected?.status==='DRAFT');

 useEffect(()=>{
  let active=true;
  api<Table[]>('/admin/data/tables').then(result=>{if(active){setCatalog(result);if(!allowed){const target=new URLSearchParams(window.location.search).get('table');if(target&&result.some(item=>item.name===target))setTableName(target)}}}).catch(e=>{if(active){setError(e.message);setLoading(false)}});
  return()=>{active=false};
 },[]);
 useEffect(()=>{setTableName(initialTable);setOffset(0);setMode(null);setSelected(null)},[initialTable]);
 useEffect(()=>{
  if(!table)return;
  let active=true;setLoading(true);setError('');
  api<Page>(`/admin/data/${table.name}?offset=${offset}`).then(result=>{if(active)setPage(result)}).catch(e=>{if(active)setError(e.message)}).finally(()=>{if(active)setLoading(false)});
  return()=>{active=false};
 },[table?.name,offset,generation,refreshKey]);
 useEffect(()=>{
  if(!catalog.length||allowed)return;
  const params=new URLSearchParams(window.location.search),target=params.get('table'),id=params.get('record');
  if(target&&id&&catalog.some(item=>item.name===target)){
   setTableName(target);api<Row>(`/admin/data/${target}/${id}`).then(row=>{setSelected(row);setMode('view')}).catch(e=>setError(e.message));
  }
 },[catalog]);
 useEffect(()=>{
  if(!table||!['create','edit'].includes(mode||''))return;
  let active=true;setReferenceError('');
  const targets=[...new Set(table.fields.filter(field=>field.reference&&(mode==='create'?field.create:field.editable)).map(field=>field.reference!))];
  Promise.all(targets.map(async target=>[target,(await api<Page>(`/admin/data/${target}?limit=100`)).items] as const)).then(result=>{if(active)setReferences(Object.fromEntries(result))}).catch(e=>{if(active)setReferenceError(`Could not load linked records: ${e.message}. You can enter a known record ID.`)});
  return()=>{active=false};
 },[table?.name,mode,generation]);

 const choose=(name:string)=>{setTableName(name);setOffset(0);setMode(null);setSelected(null);setNotice('');setError('');setDeleting(false);setDeleteText('')};
 const open=async(row:Row)=>{if(!table)return;setError('');try{setSelected(await api<Row>(`/admin/data/${table.name}/${row.id}`));setMode('view');setDeleting(false);setDeleteText('')}catch(e){setError((e as Error).message)}};
 const openEdit=async(row:Row)=>{if(!table)return;setError('');try{const full=await api<Row>(`/admin/data/${table.name}/${row.id}`);setSelected(full);setValues(initialValues(table,full));setMode('edit');setDeleting(false);setNotice('')}catch(e){setError((e as Error).message)}};
 const edit=()=>{if(!table||!selected)return;setValues(initialValues(table,selected));setMode('edit');setDeleting(false);setNotice('');setError('')};
 const openDelete=async(row:Row)=>{if(!table)return;setError('');try{const full=await api<Row>(`/admin/data/${table.name}/${row.id}`);setSelected(full);setMode('view');setDeleting(true);setDeleteText('');setError('')}catch(e){setError((e as Error).message)}};
 const create=(copy?:Row,translation=false)=>{
  if(!table)return;
  const next=initialValues(table,copy);
  if(copy&&['rate_plans','policy_documents'].includes(table.name)&&!translation)next.version=String(Number(copy.version)+1);
  if(translation){next.language=copy?.language==='en'?'az':'en';next.full_text=''}
  setValues(next);setMode('create');setSelected(null);setFile(null);setDeleting(false);setNotice('');setError('');
 };
 const save=async(event:React.FormEvent)=>{
  event.preventDefault();if(!table||busy||!['create','edit'].includes(mode||''))return;
  setBusy(true);setError('');setNotice('');
  try{
   const data=payload(table,values,mode as 'create'|'edit',selected||undefined);
   let row:Row;
   if(mode==='create'&&table.create_mode==='upload'){
    if(!file)throw new Error('Choose a car photo to upload.');
    if(file.size>5000000)throw new Error('Maximum image size is 5 MB.');
    const form=new FormData();form.append('file',file);
    form.append('alt_az',String(data.alt_az));form.append('alt_en',String(data.alt_en));form.append('sort_order',String(data.sort_order||0));
    row=await api<Row>(`/admin/vehicles/${data.vehicle_id}/photos`,{method:'POST',body:form});
   }else if(mode==='create')row=await api<Row>(`/admin/data/${table.name}`,mutation(data));
   else{
    if(!Object.keys(data).length)throw new Error('Change at least one field before saving.');
    row=await api<Row>(`/admin/data/${table.name}/${selected!.id}`,{method:'PATCH',body:JSON.stringify(data)});
   }
   setSelected(row);setMode('view');setGeneration(previous=>previous+1);setNotice(mode==='create'?'Record created.':'Changes saved.');
  }catch(e){setError((e as Error).message)}finally{setBusy(false)}
 };
 const remove=async()=>{
  if(!table||!selected||busy||deleteText!=='DELETE')return;
  setBusy(true);setError('');
  try{
   await api(`/admin/data/${table.name}/${selected.id}`,{method:'DELETE'});
   setMode(null);setSelected(null);setDeleting(false);setDeleteText('');setNotice('Record deleted.');
   if(page.items.length===1&&offset>0)setOffset(previous=>Math.max(0,previous-25));
   else setGeneration(previous=>previous+1);
  }catch(e){setError((e as Error).message)}finally{setBusy(false)}
 };
 const publish=async()=>{
  if(!selected||busy)return;setBusy(true);setError('');setNotice('');
  try{await api(`/admin/policies/${selected.id}/publish`,{method:'POST'});setSelected(await api<Row>(`/admin/data/policy_documents/${selected.id}`));setGeneration(previous=>previous+1);setNotice('Reviewed bilingual policy pair published.')}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 };
 const change=(name:string,value:any)=>setValues(previous=>({...previous,[name]:value}));
 const displayFields=table?.name==='vehicles'
  ? ['registration_number','make','model','model_year','daily_rate_qepik','status'].map(name=>table.fields.find(field=>field.name===name)!).filter(Boolean)
  : table?.fields.filter(field=>!field.hidden&&!['id','created_at'].includes(field.name)&&!['json','multiline','range','date_range','password'].includes(field.type)).slice(0,5)||[];
 const displayValue=(field:Field,value:any)=>field.name==='daily_rate_qepik'&&value!==null&&value!==undefined
  ? `${(Number(value)/100).toFixed(2)} AZN` : textValue(value);

 return <div className="data-browser">
  <div className="data-toolbar"><div><label htmlFor="admin-table-choice">Database table</label><Select id="admin-table-choice" value={tableName} onChange={event=>choose(event.target.value)} disabled={busy}>{visibleTables.map(item=><option key={item.name} value={item.name}>{item.title} · {item.name}</option>)}</Select></div><button className="secondary" disabled={busy||loading} onClick={()=>setGeneration(previous=>previous+1)}><RefreshCw size={15}/>Refresh records</button></div>
  {error&&<div className="error-banner" role="alert">{error}</div>}{notice&&<div className="notice" role="status">{notice}</div>}
  {!table&&!error&&<p className="muted-small">Loading table descriptions…</p>}
  {table&&<>
   <div className="data-heading"><div><span className="section-eyebrow"><Database size={13}/>{table.name}</span><h2>{table.title}</h2><p>{table.description}</p></div>{table.can_create&&<button className="primary" disabled={busy} onClick={()=>create()}><Plus size={15}/>{table.name==='rate_plans'?'Create rate plan version':table.name==='pricing_rules'?'Add pricing rule':'Create record'}</button>}</div>
   <p className="data-note">{table.note}</p>
   <details className="field-guide" open><summary>Table fields and descriptions · {table.fields.length} fields</summary><dl>{table.fields.map(field=><div key={field.name}><dt><code>{field.name}</code><span>{field.editable?'Editable':field.create?'Set on creation':'System managed'}</span></dt><dd>{field.description}</dd></div>)}</dl></details>
   {mode&&<section className="data-detail" aria-label={mode==='view'?'Record details':'Record editor'}>
    <div className="data-heading"><h3>{mode==='create'?'Create '+table.title:mode==='edit'?'Edit record':'Record details'}</h3><button className="round-action" disabled={busy} aria-label="Close record" onClick={()=>{setMode(null);setDeleting(false)}}><X size={17}/></button></div>
    {selected&&<p className="muted-small">{label(selected)} · {selected.id}</p>}
    {mode==='view'&&selected&&<>
     <div className="data-actions">
      {writable&&<button className="secondary" disabled={busy} onClick={edit}><Pencil size={14}/>Edit fields</button>}
      {table.can_create&&table.name!=='admin_users'&&<button className="secondary" disabled={busy} onClick={()=>create(selected)}><Plus size={14}/>{['rate_plans','policy_documents'].includes(table.name)?'Copy to new version':'Copy to new record'}</button>}
      {removable&&<button className="danger-button" disabled={busy} onClick={()=>{setDeleting(true);setDeleteText('')}}><Trash2 size={14}/>Delete record</button>}
      {table.name==='reservations'&&<a className="secondary" href={'/reservations/'+selected.id}>Manage booking</a>}
      {table.name==='conversations'&&<a className="secondary" href={'/admin/conversations/'+selected.id}>Open conversation</a>}
      {['rental_policies','policy_chunks'].includes(table.name)&&<a className="secondary" href="/admin/policies">Manage policy versions</a>}
      {table.name==='policy_documents'&&selected.status==='DRAFT'&&<button className="primary" disabled={busy} onClick={publish}>Approve and publish bilingual pair</button>}
      {table.name==='policy_documents'&&selected.status==='DRAFT'&&<button className="secondary" disabled={busy} onClick={()=>create(selected,true)}>Create {selected.language==='en'?'Azerbaijani':'English'} translation</button>}
     </div>
     {deleting&&<div className="delete-confirm"><h4>Delete {label(selected)}?</h4><p>This permanently removes this record. Records linked to bookings or other tables cannot be deleted.</p><label htmlFor="delete-word">Type DELETE to confirm</label><input id="delete-word" value={deleteText} onChange={event=>setDeleteText(event.target.value)} autoComplete="off"/><div className="data-actions"><button className="danger-button" disabled={busy||deleteText!=='DELETE'} onClick={remove}>{busy?'Deleting…':'Permanently delete'}</button><button className="secondary" disabled={busy} onClick={()=>setDeleting(false)}>Keep record</button></div></div>}
     {table.name==='vehicle_photos'&&<img className="admin-photo" src={'/api/v1/assets/'+selected.asset_key} alt={selected.alt_en}/>}
     <dl className="record-fields">{table.fields.filter(field=>field.type!=='password').map(field=><div key={field.name}><dt>{field.label}<code>{field.name}</code></dt><dd><p className="field-help">{field.description}</p>{field.hidden?<span className="muted-small">Internal value is not exposed.</span>:field.reference&&selected[field.name]?<a className="reference-link" href={`/admin/data?table=${field.reference}&record=${selected[field.name]}`}>{selected[field.name]} ↗</a>:<pre>{field.type==='datetime'&&selected[field.name]?formatRentalDate(selected[field.name],'en'):displayValue(field,selected[field.name])}</pre>}</dd></div>)}</dl>
    </>}
    {(mode==='create'||mode==='edit')&&<form onSubmit={save} className="data-form">
     {referenceError&&<p className="form-error">{referenceError}</p>}
     <div className="data-form-grid">{table.fields.filter(field=>mode==='create'?field.create:field.editable).map(field=>{
      const inputId=`field-${table.name}-${field.name}`,helpId=inputId+'-help',value=values[field.name]??'';
      const required=field.required&&!(field.name==='password'&&mode==='edit');
      return <div key={field.name} className={['json','multiline','date_range'].includes(field.type)?'wide-field':''}>
       <label htmlFor={inputId}>{field.label}{required?' *':field.nullable?' · optional':''}</label>
       {field.type==='boolean'?<label className="boolean-field"><input id={inputId} type="checkbox" checked={Boolean(value)} disabled={busy} aria-describedby={helpId} onChange={event=>change(field.name,event.target.checked)}/>{value?'Enabled':'Disabled'}</label>
        :field.enum?<Select id={inputId} value={value} required={required} disabled={busy} aria-describedby={helpId} onChange={event=>change(field.name,event.target.value)}><option value="">Select {field.label.toLowerCase()}</option>{field.enum.map(option=><option key={option}>{option}</option>)}</Select>
        :['json','multiline'].includes(field.type)?<textarea id={inputId} value={value} required={required} maxLength={field.maxLength} disabled={busy} aria-describedby={helpId} rows={field.type==='multiline'?12:4} onChange={event=>change(field.name,event.target.value)}/>
        :field.type==='date_range'?<div className="two-fields"><input id={inputId} type="date" aria-label="Start date (included)" aria-describedby={helpId} value={Array.isArray(value)?value[0]:''} disabled={busy} onChange={event=>change(field.name,[event.target.value,Array.isArray(value)?value[1]:''])}/><input type="date" aria-label="End date (excluded)" aria-describedby={helpId} value={Array.isArray(value)?value[1]:''} disabled={busy} onChange={event=>change(field.name,[Array.isArray(value)?value[0]:'',event.target.value])}/></div>
        :<input id={inputId} value={value} type={field.type==='password'?'password':field.type==='datetime'?'datetime-local':field.type==='date'?'date':field.type==='money'?'number':'text'} step={field.type==='money'?'0.01':undefined} min={field.type==='money'?'0':undefined} inputMode={field.type==='integer'?'numeric':undefined} list={field.reference?inputId+'-options':undefined} required={required} minLength={field.minLength} maxLength={field.maxLength} disabled={busy} aria-describedby={helpId} autoComplete={field.type==='password'?'new-password':'off'} onChange={event=>change(field.name,event.target.value)}/>}
       {field.reference&&<datalist id={inputId+'-options'}>{(references[field.reference]||[]).map(row=><option key={row.id} value={row.id}>{label(row)}</option>)}</datalist>}
       <p id={helpId} className="field-help">{field.description}{field.type==='datetime'?' Dates shown in Baku time (UTC+04:00).':''}{field.reference?' Choose a linked record or enter its full ID.':''}</p>
      </div>;
     })}</div>
     {mode==='create'&&table.create_mode==='upload'&&<><label htmlFor="admin-photo-upload">Image file *</label><input id="admin-photo-upload" type="file" accept="image/png,image/jpeg,image/webp" required disabled={busy} onChange={event=>setFile(event.target.files?.[0]||null)}/><p className="field-help">JPEG, PNG or WebP, up to 5 MB. The system stores the file locally and generates its asset path.</p></>}
     <div className="data-actions"><button className="primary" disabled={busy} type="submit">{busy?'Saving…':mode==='create'?'Create record':'Save changes'}</button><button className="secondary" disabled={busy} type="button" onClick={()=>setMode(selected?'view':null)}>Cancel</button></div>
    </form>}
   </section>}
   <div className="data-table-wrap"><table className="admin-table"><thead><tr>{displayFields.map(field=><th key={field.name} title={field.description}>{field.label}</th>)}<th>Actions</th></tr></thead><tbody>{page.items.map(row=><tr key={row.id}>{displayFields.map(field=><td key={field.name}>{field.type==='boolean'?(row[field.name]?'Yes':'No'):field.reference&&row[field.name]?<a className="reference-link" href={`/admin/data?table=${field.reference}&record=${row[field.name]}`}>{String(row[field.name]).slice(0,8)}</a>:displayValue(field,row[field.name])}</td>)}<td><div className="row-actions"><button disabled={busy} onClick={()=>open(row)}><Eye size={13}/>Read</button>{table.can_edit&&!(table.name==='policy_documents'&&row.status!=='DRAFT')&&<button disabled={busy} onClick={()=>openEdit(row)}><Pencil size={13}/>Edit</button>}{table.can_delete&&!(table.name==='policy_documents'&&row.status!=='DRAFT')&&<button className="row-delete" disabled={busy} onClick={()=>openDelete(row)}><Trash2 size={13}/>Delete</button>}</div></td></tr>)}</tbody></table></div>
   {loading?<p className="field-help" role="status">Loading records…</p>:!page.items.length&&<p className="field-help">No records in this table yet.</p>}
   <div className="data-pagination"><span>{page.total?`${offset+1}–${Math.min(offset+page.items.length,page.total)} of ${page.total} records`:'0 records'}</span><div><button className="secondary" aria-label="Previous page" disabled={busy||loading||offset===0} onClick={()=>{setOffset(previous=>Math.max(0,previous-25));setMode(null)}}><ChevronLeft size={16}/></button><button className="secondary" aria-label="Next page" disabled={busy||loading||offset+25>=page.total} onClick={()=>{setOffset(previous=>previous+25);setMode(null)}}><ChevronRight size={16}/></button></div></div>
  </>}
 </div>;
}
