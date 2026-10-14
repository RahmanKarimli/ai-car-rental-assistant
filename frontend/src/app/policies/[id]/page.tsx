'use client';
import {useParams} from 'next/navigation';
import {useEffect,useState} from 'react';
import {api} from '@/lib/api';
export default function Policy(){const {id}=useParams<{id:string}>();const [policy,setPolicy]=useState<any>(null),[error,setError]=useState('');useEffect(()=>{api('/policies/'+id).then(setPolicy).catch(e=>setError(e.message))},[id]);return <main className="booking-page"><a className="brand" href="/">yol.</a>{policy&&<><h1>{policy.title}</h1><p className="muted-small">{policy.language.toUpperCase()} · v{policy.version} · {policy.section}</p><article className="admin-page" style={{whiteSpace:'pre-wrap',lineHeight:1.9,marginTop:20}}>{policy.content}</article></>}{error&&<p className="form-error">{error}</p>}</main>}
