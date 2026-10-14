let csrf='';
export async function api<T=unknown>(path:string,options:RequestInit={}):Promise<T>{
 const headers=new Headers(options.headers);if(!(options.body instanceof FormData))headers.set('Content-Type','application/json');if(csrf)headers.set('X-CSRF-Token',csrf);
 const response=await fetch('/api/v1'+path,{...options,headers,credentials:'same-origin'});
 const data=await response.json();if(!response.ok)throw new Error(Array.isArray(data.detail)?data.detail.map((e:any)=>`${e.loc?.join('.')}: ${e.msg}`).join('; '):data.detail||data.code||'Request failed');return data as T;
}
export function setSession(token:string){csrf=token}
export async function initializeSession(){
 let session:{csrf_token:string;role:string};
 try{session=await api('/sessions/current')}catch{session=await api('/sessions',{method:'POST'})}
 setSession(session.csrf_token);return session;
}
export function mutation(body:unknown,key=crypto.randomUUID()):RequestInit{return {method:'POST',headers:{'Idempotency-Key':key},body:JSON.stringify(body)}}
