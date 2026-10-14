import {NextRequest} from 'next/server';
export const dynamic='force-dynamic';
async function proxy(request:NextRequest,{params}:{params:Promise<{path:string[]}>}){
 const {path}=await params;
 if(path.some(p=>p==='..'||p.includes('/')))return Response.json({detail:'Invalid path'}, {status:400});
 const base=process.env.INTERNAL_API_URL||'http://localhost:8000';
 const headers=new Headers();
 for(const key of ['content-type','cookie','origin','x-csrf-token','idempotency-key']){const value=request.headers.get(key);if(value)headers.set(key,value)}
 try{
 const response=await fetch(`${base}/api/${path.map(encodeURIComponent).join('/')}${request.nextUrl.search}`,{method:request.method,headers,body:['GET','HEAD'].includes(request.method)?undefined:await request.arrayBuffer(),cache:'no-store',signal:AbortSignal.timeout(120000)});
 const out=new Headers();for(const key of ['content-type','set-cookie','x-content-type-options']){const value=response.headers.get(key);if(value)out.set(key,value)}
 out.set('Cache-Control','no-store');return new Response(response.body,{status:response.status,headers:out});
 }catch{return Response.json({code:'API_UNAVAILABLE',detail:'The local rental service is unavailable. Please retry shortly.'},{status:503})}
}
export {proxy as GET,proxy as POST,proxy as PATCH,proxy as DELETE};
