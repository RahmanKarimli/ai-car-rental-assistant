'use client';
import {ArrowRight,CarProfile,Check,GasPump,Gear,Heart,MapPin,Users} from '@phosphor-icons/react';
import {useDisplayPreferences} from '@/lib/display-preferences';
import {useState} from 'react';
import {categoryImage,rentalLabel} from '@/lib/rental-search';
import type {Branch,Language,Vehicle} from '@/types/chat';

export function VehicleCard({car,language,branch,variant='list',onSelect,onSave,saved=false,disabled=false}:{car:Vehicle;language:Language;branch?:Branch;variant?:'list'|'grid'|'compact';onSelect?:(car:Vehicle)=>void;onSave?:(id:string)=>void;saved?:boolean;disabled?:boolean}){
  const az=language==='az';
  const {formatMoney,currency,usdAvailable}=useDisplayPreferences();
  const [failedPhoto,setFailedPhoto]=useState(false);
  const illustration=!car.photo_url||failedPhoto;
  const src=illustration?categoryImage(car):car.photo_url!;
  const price=car.rental_price||car.daily_price;
  const match=car.budget_alternative?(az?'Büdcədən yuxarı alternativ':'Above-budget alternative'):car.alternative_to_class?(az?'Digər kateqoriya':'Category alternative'):car.upgrade_recommendation?(az?'Daha geniş seçim':'Roomier option'):car.best_fit?(az?'Tövsiyə olunur':'Recommended'):'';
  return <article className={'vehicle-card vehicle-card--'+variant}>
    <div className="vehicle-visual">
      {onSave&&<button className={'icon-button save-car '+(saved?'is-saved':'')} type="button" onClick={()=>onSave(car.vehicle_id)} aria-pressed={saved} aria-label={saved?(az?'Avtomobili yaddaşdan sil':'Remove saved car'):(az?'Avtomobili yadda saxla':'Save car')}><Heart size={21} weight={saved?'fill':'regular'}/></button>}
      {src?<img src={src} alt={illustration?(az?'Kateqoriya illüstrasiyası; avtomobilin fotosu əlavə edilməyib':'Category illustration; vehicle photo not supplied'):car.title} loading="lazy" width={360} height={220} onError={()=>{if(!illustration)setFailedPhoto(true);}}/>:<div className="vehicle-placeholder"><CarProfile size={88} weight="light"/><span>{az?'Foto əlavə edilməyib':'Photo not supplied'}</span></div>}
      {src&&illustration&&<span className="illustration-label">{az?'Kateqoriya illüstrasiyası':'Category illustration'}</span>}
    </div>
    <div className="vehicle-detail">
      <div className="vehicle-kicker">{rentalLabel(car.class_code,language)} · {car.year}</div>
      <h3>{car.title}</h3>
      <p className="vehicle-type">{rentalLabel(car.vehicle_type,language)}</p>
      <div className="specs">
        <span><Users size={17}/>{car.seats} {az?'yer':'seats'}</span>
        <span><Gear size={17}/>{rentalLabel(car.transmission,language)}</span>
        <span><GasPump size={17}/>{rentalLabel(car.fuel_type,language)}</span>
      </div>
      {branch&&<p className="vehicle-location"><MapPin size={17}/>{az?branch.name_az:branch.name_en}</p>}
      <div className="vehicle-tags">{match&&<span className="match"><Check size={14}/>{match}</span>}{car.availability_checked&&<span className="availability"><Check size={14}/>{az?'Tarixləriniz üçün mövcuddur':'Available for your dates'}</span>}</div>
    </div>
    <div className="vehicle-price">
      <div><b>{formatMoney(price)}</b><span>{car.rental_price?(az?'icarə cəmi':'rental total'):(az?'əsas günlük tarif':'base rate / day')}</span></div>
      {car.rental_price&&<small>{formatMoney(car.daily_price)} / {az?'gün':'day'}</small>}
      {currency==='USD'&&usdAvailable&&<small>{price.formatted} · {az?'AZN ilə ödəniş':'Pay in AZN'}</small>}
      {onSelect&&<button type="button" className="offer-button" disabled={disabled} onClick={()=>onSelect(car)}>{az?'Təklifə bax':'View offer'}<ArrowRight size={17}/></button>}
      <p>{az?'Əlavələr və depozit təklifdə göstərilir.':'Extras and deposit shown in your quote.'}</p>
    </div>
  </article>;
}
