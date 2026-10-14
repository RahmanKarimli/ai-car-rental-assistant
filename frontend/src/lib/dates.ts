/** Rental dates are entered and displayed in the pickup market's timezone. */
export function toBakuInput(value:string):string {
  const date=new Date(value);
  if(Number.isNaN(date.getTime()))return '';
  const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Baku',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(date);
  const part=(key:string)=>parts.find(p=>p.type===key)?.value||'';
  return `${part('year')}-${part('month')}-${part('day')}T${part('hour')}:${part('minute')}`;
}

export function fromBakuInput(value:string):string {
  // Azerbaijan has a fixed UTC+04:00 offset, with no daylight-saving transition.
  return new Date(value+'+04:00').toISOString();
}

export function formatRentalDate(value:string,language:'az'|'en'):string {
  return new Date(value).toLocaleString(language==='az'?'az-AZ':'en-GB',{timeZone:'Asia/Baku',dateStyle:'medium',timeStyle:'short'})+' (Baku)';
}
