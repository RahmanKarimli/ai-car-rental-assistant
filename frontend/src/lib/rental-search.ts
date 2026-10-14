import {fromBakuInput,toBakuInput} from './dates';
import type {InventoryFilters,Language,SearchValues,Vehicle} from '@/types/chat';

export function defaultSearch():SearchValues {
  const tomorrow=toBakuInput(new Date(Date.now()+86400000).toISOString()).slice(0,10);
  const later=toBakuInput(new Date(Date.now()+3*86400000).toISOString()).slice(0,10);
  return {branch:'',pickup:tomorrow+'T12:00',returnAt:later+'T12:00',category:'',seats:'',fuel:'',transmission:'',budget:'',currency:'AZN',budgetBasis:'DAY'};
}

// Rentals use whole days: the return clock always follows the pickup clock.
export function sameTimeReturn(values:SearchValues):SearchValues {
  return {...values,returnAt:returnAtPickupTime(values.pickup,values.returnAt)};
}

export function returnAtPickupTime(pickup:string,returnAt:string) {
  return returnAt.slice(0,10)+'T'+(pickup.slice(11)||'12:00');
}

export function inventoryFilters(values:SearchValues):InventoryFilters {
  const trip=sameTimeReturn(values);
  const pickup=fromBakuInput(trip.pickup),returnAt=fromBakuInput(trip.returnAt);
  if(!values.branch)throw new Error('branch');
  if(new Date(returnAt)<=new Date(pickup))throw new Error('dates');
  if(new Date(pickup)<=new Date())throw new Error('past');
  if(values.budget!==''&&(!Number.isFinite(Number(values.budget))||Number(values.budget)<0))throw new Error('budget');
  const filters:InventoryFilters={pickup_branch_id:values.branch,pickup_at:pickup,return_at:returnAt};
  if(values.category==='PREMIUM'||values.category==='ECONOMY')filters.class_code=values.category;
  else if(values.category==='ELECTRIC')filters.fuel_type='ELECTRIC';
  else if(values.category)filters.vehicle_type=values.category;
  if(values.fuel)filters.fuel_type=values.fuel;
  if(values.transmission)filters.transmission=values.transmission;
  if(values.seats)filters.minimum_seats=Number(values.seats);
  if(values.budget!==''){filters.budget_amount=values.budget;filters.budget_currency=values.currency;filters.budget_basis=values.budgetBasis;}
  return filters;
}

export function inventoryQuery(filters:InventoryFilters,language:Language) {
  const params=new URLSearchParams({language});
  Object.entries(filters).forEach(([key,value])=>{if(value!==undefined&&value!=='')params.set(key,String(value));});
  return '/inventory?'+params.toString();
}

export function inventoryPageQuery(filters:InventoryFilters,language:Language,page:number,sort:string,ids?:string[]) {
  const params=new URLSearchParams(inventoryQuery(filters,language).split('?')[1]);
  params.set('page',String(page));params.set('page_size','12');params.set('sort',sort);
  ids?.forEach(id=>params.append('vehicle_ids',id));
  return '/inventory/page?'+params.toString();
}

const labels:Record<string,[string,string]>={SUV:['SUV','SUV'],SEDAN:['Sedan','Sedan'],HATCHBACK:['Hatchback','Hetçbek'],VAN:['Van','Furqon'],MINIVAN:['Minivan','Minivan'],CONVERTIBLE:['Convertible','Kabriolet'],COUPE:['Coupe','Kupe'],WAGON:['Estate','Universal'],PICKUP:['Pickup','Pikap'],ECONOMY:['Economy','Ekonom'],STANDARD:['Standard','Standart'],FAMILY:['Family','Ailə'],PREMIUM:['Luxury','Lüks'],ELECTRIC:['Electric','Elektrik'],HYBRID:['Hybrid','Hibrid'],PETROL:['Petrol','Benzin'],DIESEL:['Diesel','Dizel'],LPG:['LPG','LPG'],AUTOMATIC:['Automatic','Avtomatik'],MANUAL:['Manual','Mexaniki']};
export function rentalLabel(value:string,language:Language){return labels[value]?.[language==='az'?1:0]||value;}
export function categoryImage(car:Pick<Vehicle,'fuel_type'|'class_code'|'vehicle_type'>){
  const category=car.fuel_type==='ELECTRIC'?'electric':car.class_code==='PREMIUM'?'luxury':car.vehicle_type==='SUV'?'suv':car.class_code==='ECONOMY'?'economy':null;
  return category?'/assets/category-'+category+'.webp':null;
}
