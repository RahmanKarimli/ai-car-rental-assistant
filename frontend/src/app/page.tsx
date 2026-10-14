'use client';
import {Select} from '@/components/Select';
import {useEffect,useRef,useState,type CSSProperties} from 'react';
import {ArrowLeft,ArrowRight,ArrowUpRight,Car,CaretDown,Check,ClockCounterClockwise,Heart,MapPin,ShieldCheck,SlidersHorizontal,Sparkle,UserCircle,X} from '@phosphor-icons/react';
import {useQuery} from '@tanstack/react-query';
import {api} from '@/lib/api';
import {defaultSearch,inventoryFilters,inventoryPageQuery,rentalLabel,sameTimeReturn} from '@/lib/rental-search';
import {formatRentalDate,toBakuInput} from '@/lib/dates';
import {useConversation} from '@/hooks/useConversation';
import {VehicleCard} from '@/components/VehicleCard';
import {SearchForm} from '@/components/SearchForm';
import {ConciergePanel} from '@/components/ConciergePanel';
import {DisplayControls} from '@/components/DisplayControls';
import {Pagination} from '@/components/Pagination';
import {useDisplayPreferences} from '@/lib/display-preferences';
import {BookingDrawer} from '@/components/BookingDrawer';
import {clampConciergeWidth} from '@/lib/concierge-sizing';
import type {Branch,Extra,InventoryFilters,InventoryPage,SearchValues,Vehicle} from '@/types/chat';

type RecentSearch={values:SearchValues;createdAt:string};
const categoryOptions=[{value:'ECONOMY',image:'economy'},{value:'SUV',image:'suv'},{value:'ELECTRIC',image:'electric'},{value:'PREMIUM',image:'luxury'}];
export default function Home(){
  const chat=useConversation(),az=chat.language==='az';
  const display=useDisplayPreferences();
  const [page,setPage]=useState(1);
  const [conciergeWidth,setConciergeWidth]=useState(360),[conciergeWidthReady,setConciergeWidthReady]=useState(false);
  const [values,setValues]=useState<SearchValues>(defaultSearch),[query,setQueryState]=useState<InventoryFilters|null>(null);
  const [assistant,setAssistant]=useState<'closed'|'side'>('closed'),[filtersOpen,setFiltersOpen]=useState(false),[sort,setSortState]=useState('recommended');
  const setQuery=(value:InventoryFilters|null)=>{setPage(1);setQueryState(value);};
  const setSort=(value:string)=>{setPage(1);setSortState(value);};
  const [saved,setSaved]=useState<string[]>([]),[savedOnly,setSavedOnly]=useState(false),[recent,setRecent]=useState<RecentSearch[]>([]);
  const [selected,setSelected]=useState<Vehicle|null>(null),[selectedValues,setSelectedValues]=useState<SearchValues>(defaultSearch),[extraSelections,setExtraSelections]=useState<string[]>([]),[formError,setFormError]=useState('');
  const previousConversation=useRef(''),resultsHeading=useRef<HTMLHeadingElement>(null);
  const previousPreferences=useRef<{conversation:string;value:string}|null>(null);
  const initializedBranch=useRef(false);
  const branches=useQuery({queryKey:['branches'],queryFn:()=>api<Branch[]>('/branches')});
  const extras=useQuery({queryKey:['extras'],queryFn:()=>api<Extra[]>('/extras')});
  const browseFilters:InventoryFilters=query||{};
  const emptySaved=savedOnly&&saved.length===0;
  const inventory=useQuery({queryKey:['rental-inventory-page',chat.language,browseFilters,page,sort,savedOnly?saved:null],queryFn:({signal})=>api<InventoryPage>(inventoryPageQuery(browseFilters,chat.language,page,sort,savedOnly?saved:undefined),{signal}),enabled:!emptySaved,staleTime:15000});
  useEffect(()=>{if(inventory.data&&inventory.data.page!==page)setPage(inventory.data.page);},[inventory.data,page]);
  const hasResults=!!query||savedOnly;
  const branch=branches.data?.find(b=>b.id===query?.pickup_branch_id);
  const filterCount=[values.category,values.seats,values.fuel,values.transmission,values.budget].filter(value=>value!=='').length;

  useEffect(()=>{
    try{const ids=JSON.parse(localStorage.getItem('yol-saved-cars')||'[]');if(Array.isArray(ids))setSaved(ids.filter(id=>typeof id==='string'));const entries=JSON.parse(localStorage.getItem('yol-recent-searches')||'[]');if(Array.isArray(entries))setRecent(entries.filter(entry=>entry?.values?.branch&&entry?.values?.pickup&&entry?.values?.returnAt).slice(0,3));}catch{}
  },[]);

  useEffect(()=>{try{const stored=Number(localStorage.getItem('yol-concierge-width'));if(Number.isFinite(stored)&&stored>0)setConciergeWidth(clampConciergeWidth(stored,window.innerWidth));}catch{}setConciergeWidthReady(true);},[]);
  useEffect(()=>{if(conciergeWidthReady)try{localStorage.setItem('yol-concierge-width',String(conciergeWidth));}catch{}},[conciergeWidth,conciergeWidthReady]);
  useEffect(()=>{const resize=()=>setConciergeWidth(width=>clampConciergeWidth(width,window.innerWidth));window.addEventListener('resize',resize);return()=>window.removeEventListener('resize',resize);},[]);

  useEffect(()=>{if(branches.data?.length&&!initializedBranch.current){initializedBranch.current=true;setValues(previous=>previous.branch?previous:{...previous,branch:branches.data![0].id});}},[branches.data]);
  useEffect(()=>{
    if(previousConversation.current&&previousConversation.current!==chat.id){setSelected(null);setQuery(null);setExtraSelections([]);setSavedOnly(false);setFormError('');setValues({...defaultSearch(),branch:branches.data?.[0]?.id||''});}
    if(chat.id)previousConversation.current=chat.id;
  },[chat.id]);
  useEffect(()=>{
    if(!chat.id)return;
    const p=chat.preferences,snapshot=JSON.stringify(p);
    const restored=previousPreferences.current?.conversation!==chat.id;
    if(!restored&&previousPreferences.current?.value===snapshot)return;
    previousPreferences.current={conversation:chat.id,value:snapshot};
    // Form searches already apply their filters. Their eventual chat response must
    // not reinstate an old search after the customer chooses All cars.
    if(!restored&&chat.preferencesEvent!=='TEXT_MESSAGE'&&chat.preferencesEvent!=='RESTORE')return;
    if(!Object.keys(p).length)return;
    const electricCategory=p.fuel_type==='ELECTRIC'&&!p.vehicle_type&&!p.class_code;
    const next:SearchValues=sameTimeReturn({...values,branch:p.pickup_branch_id||values.branch,pickup:p.pickup_at?toBakuInput(p.pickup_at):values.pickup,returnAt:p.return_at?toBakuInput(p.return_at):values.returnAt,category:p.class_code==='PREMIUM'?'PREMIUM':p.class_code==='ECONOMY'?'ECONOMY':electricCategory?'ELECTRIC':p.vehicle_type||'',seats:p.minimum_seats?String(p.minimum_seats):'',fuel:electricCategory?'':p.fuel_type||'',transmission:p.transmission||'',budget:p.budget_amount===undefined||p.budget_amount===null?'':String(p.budget_amount),currency:p.budget_currency||'AZN',budgetBasis:p.budget_basis||'DAY'});
    setValues(next);if(!restored&&p.pickup_at&&p.return_at&&p.pickup_branch_id){try{setQuery(inventoryFilters(next));}catch{}}
  },[chat.preferences,chat.id,chat.preferencesEvent]);
  const lastMessage=chat.messages.at(-1);
  useEffect(()=>{if(lastMessage?.cards.some(card=>card.type==='booking'))void inventory.refetch();},[lastMessage?.id]);

  const cars=emptySaved?[]:inventory.data?.items||[];
  const total=emptySaved?0:inventory.data?.total||0;
  const changePage=(next:number)=>{setPage(next);resultsHeading.current?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});};
  const saveCar=(id:string)=>setSaved(previous=>{const next=previous.includes(id)?previous.filter(value=>value!==id):[...previous,id];try{localStorage.setItem('yol-saved-cars',JSON.stringify(next));}catch{}return next;});
  const remember=(search:SearchValues)=>setRecent(previous=>{const next=[{values:search,createdAt:new Date().toISOString()},...previous.filter(row=>JSON.stringify(row.values)!==JSON.stringify(search))].slice(0,3);try{localStorage.setItem('yol-recent-searches',JSON.stringify(next));}catch{}return next;});
  const runSearch=(input=values)=>{
    const search=sameTimeReturn(input);
    setFormError('');let filters:InventoryFilters;
    try{filters=inventoryFilters(search);}catch(e){const code=(e as Error).message;setFormError(code==='branch'?(az?'Götürmə məntəqəsini seçin.':'Choose a pickup location.'):code==='past'?(az?'Gələcək götürmə tarixi seçin.':'Choose a future pickup date.'):code==='budget'?(az?'Düzgün büdcə daxil edin.':'Enter a valid budget.'):(az?'Qaytarma vaxtı götürmə vaxtından sonra olmalıdır.':'Return must be after pickup. Check both dates.'));return;}
    setValues(search);setQuery(filters);setSavedOnly(false);setFiltersOpen(false);remember(search);
    window.scrollTo({top:0,behavior:'instant'});
    if(chat.id&&!chat.busy)void chat.send('SEARCH',{filters});
  };
  const chooseCategory=(category:string)=>runSearch({...values,category,fuel:category==='ELECTRIC'||values.category==='ELECTRIC'?'':values.fuel});
  const chooseCar=(car:Vehicle)=>{
    const trip=sameTimeReturn({...values,branch:car.branch_id,pickup:query?.pickup_at?toBakuInput(query.pickup_at):values.pickup,returnAt:query?.return_at?toBakuInput(query.return_at):values.returnAt});
    try{inventoryFilters(trip);}catch{setFormError(az?'Əvvəl düzgün tarix və məntəqə seçin.':'Choose valid dates and a pickup location first.');return;}
    setSelectedValues(trip);setSelected(car);
  };
  const openAI=()=>setAssistant(previous=>previous==='closed'?'side':'closed');
  const browseAll=()=>{setQuery(null);setSavedOnly(false);setFiltersOpen(false);setSort('recommended');setValues(previous=>({...previous,category:'',seats:'',fuel:'',transmission:'',budget:''}));requestAnimationFrame(()=>resultsHeading.current?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'}));};
  const clearFilters=()=>runSearch({...values,category:'',seats:'',fuel:'',transmission:'',budget:''});

  return <>
    <a className="skip-link" href="#main-content">{az?'Əsas məzmuna keç':'Skip to main content'}</a>
    <header className="site-header"><div className="container header-inner"><a className="brand" href="/" aria-label="Yol home">yol<span>.</span></a><nav className="primary-nav" aria-label={az?'Əsas naviqasiya':'Main navigation'}><a className="nav-active" href="/" aria-current="page"><Car size={20}/>{az?'Avtomobillər':'Cars'}</a><a href="/reservations">{az?'Rezervasiyalarım':'My reservations'}</a></nav><button type="button" className={'ask-ai-button '+(assistant!=='closed'?'is-active':'')} onClick={openAI} aria-expanded={assistant!=='closed'}><Sparkle size={18} weight="fill"/>{az?'AI köməkçi':'Ask AI'}</button><div className="header-actions"><DisplayControls language={chat.language}/><Select className="language-button" value={chat.language} disabled={chat.busy||!chat.id} onChange={e=>{if(e.target.value!==chat.language)void chat.send('LANGUAGE_CHANGE',{language:e.target.value});}} aria-label={az?'Dil seçin':'Choose language'}><option value="en">EN</option><option value="az">AZ</option></Select><button type="button" className={'icon-button '+(savedOnly?'is-saved':'')} aria-label={az?'Yadda saxlanılan avtomobillər':'Saved cars'} aria-pressed={savedOnly} onClick={()=>{setPage(1);setSavedOnly(previous=>!previous);setAssistant('closed');}}><Heart size={23} weight={savedOnly?'fill':'regular'}/>{saved.length>0&&<span className="saved-count">{saved.length}</span>}</button><a href="/reservations" className="icon-button account-link" aria-label={az?'Rezervasiyalarım':'My reservations'}><UserCircle size={25}/></a></div></div></header>

    <main id="main-content" className={assistant==='side'?'customer-page--with-ai':''} style={{'--concierge-width':`${conciergeWidth}px`} as CSSProperties}>
      {assistant==='side'&&<ConciergePanel chat={chat} width={conciergeWidth} onResize={clientX=>setConciergeWidth(clampConciergeWidth(clientX-8,window.innerWidth))} onClose={()=>setAssistant('closed')} onSelect={chooseCar} onExtra={id=>setExtraSelections(previous=>Array.from(new Set([...previous,id])))}/>}
      {!hasResults?<section className="search-hero"><div className="container"><div className="hero-content"><div className="hero-copy"><p className="eyebrow">{az?'AVTOMOBİL İCARƏSİ. SİZİN QAYDALARINIZLA.':'CAR RENTAL. YOUR WAY.'}</p><h1>{az?'Növbəti səfərinizə uyğun avtomobili tapın.':'Find the right car for your next journey.'}</h1><p>{az?'Avtomobilləri müqayisə edin, tarixlərinizi seçin və bütün məlumatlara baxıb rezervasiya edin.':'Compare cars, choose your dates, and book with all the details in view.'}</p><div className="hero-tabs"><span><Car size={20} weight="fill"/>{az?'Avtomobil icarəsi':'Car rental'}</span><button type="button" onClick={openAI}><Sparkle size={18}/>{az?'AI ilə planlaşdır':'Plan with AI'}<ArrowUpRight size={16}/></button></div></div><div className="hero-visual" aria-hidden="true"><img src="/assets/category-suv.webp" alt="" width={480} height={480}/><div><MapPin size={18}/><span>Azerbaijan</span><span className="hero-visual-line"/><Car size={19}/></div></div></div><SearchForm values={values} branches={branches.data||[]} language={chat.language} onChange={setValues} onSubmit={runSearch} busy={chat.busy}/><p className="search-context"><Check size={15}/>{az?'Eyni götürmə və qaytarma məntəqəsi':'Same pickup and drop-off location'}<span>·</span>{az?'Bakı vaxtı':'Baku time'}</p>{formError&&<p role="alert" className="form-error">{formError}</p>}{branches.error&&<p className="form-error" role="alert">{branches.error.message}</p>}</div></section>:<section className="search-band"><div className="container"><SearchForm values={values} branches={branches.data||[]} language={chat.language} onChange={setValues} onSubmit={runSearch} busy={chat.busy} compact/>{formError&&<p role="alert" className="form-error">{formError}</p>}</div></section>}

      <div className="container main-body">
        {!hasResults&&recent.length>0&&<section className="recent-section"><div className="section-heading"><h2>{az?'Son axtarışlarınız':'Your recent searches'}</h2><span>{az?'Qaldığınız yerdən davam edin':'Pick up where you left off'}</span></div><div className="recent-grid">{recent.map((search,index)=>{const location=branches.data?.find(b=>b.id===search.values.branch);return <button className="recent-search" type="button" key={index} disabled={chat.busy||!location} onClick={()=>runSearch(search.values)}><ClockCounterClockwise size={23}/><div><b>{location?(az?location.name_az:location.name_en):(az?'Əvvəlki məntəqə':'Previous location')}</b><span>{search.values.pickup.slice(0,10)} → {search.values.returnAt.slice(0,10)}</span></div><ArrowUpRight size={20}/></button>;})}</div></section>}

        {!hasResults&&<section className="category-section"><div className="section-heading"><h2>{az?'Özünüzə uyğun avtomobil seçin':'Find your kind of car'}</h2><p>{az?'Şəhər üçün kiçik. Səfər üçün geniş. Seçim sizindir.':'Compact for the city. Roomy for the road. Your choice.'}</p></div><div className="category-strip">{categoryOptions.map(category=><button type="button" className="category-button" disabled={chat.busy||!values.branch} key={category.value} onClick={()=>chooseCategory(category.value)}><img src={'/assets/category-'+category.image+'.webp'} alt="" width={140} height={100}/><span>{rentalLabel(category.value,chat.language)}</span><ArrowUpRight size={19}/></button>)}</div></section>}

        <div className="results-layout">
          <section className="results-region" aria-label={az?'Avtomobil nəticələri':'Car results'}>
            {hasResults?<><div className="filters-toolbar"><button type="button" className="filter-chip" onClick={browseAll}><ArrowLeft size={18}/>{az?'Bütün avtomobillər':'All cars'}</button><button type="button" className={'filter-chip '+(filtersOpen?'is-active':'')} aria-expanded={filtersOpen} aria-controls="rental-filters" onClick={()=>setFiltersOpen(previous=>!previous)}><SlidersHorizontal size={19}/>{az?'Bütün filtrlər':'All filters'}{filterCount>0&&<span className="filter-count">{filterCount}</span>}<CaretDown size={14}/></button>{categoryOptions.map(category=><button type="button" className={'filter-chip '+(values.category===category.value?'is-active':'')} key={category.value} disabled={chat.busy} onClick={()=>chooseCategory(values.category===category.value?'':category.value)}>{rentalLabel(category.value,chat.language)}</button>)}{savedOnly&&<button type="button" className="filter-chip is-active" onClick={()=>setSavedOnly(false)}><Heart size={17} weight="fill"/>{az?'Yadda saxlanılanlar':'Saved'}<X size={14}/></button>}</div>
              {filtersOpen&&<form id="rental-filters" className="filters-panel" onSubmit={e=>{e.preventDefault();runSearch();}}><div className="filters-panel-heading"><h3>{az?'Axtarışı dəqiqləşdirin':'Make the search yours'}</h3><button type="button" className="icon-button" aria-label={az?'Filtrləri bağla':'Close filters'} onClick={()=>setFiltersOpen(false)}><X size={20}/></button></div><div className="filter-fields"><div><label htmlFor="filter-category">{az?'Avtomobil növü':'Car type'}</label><Select id="filter-category" value={values.category} onChange={e=>setValues({...values,category:e.target.value,fuel:e.target.value==='ELECTRIC'||values.category==='ELECTRIC'?'':values.fuel})}><option value="">{az?'İstənilən':'Any'}</option>{['ECONOMY','PREMIUM','ELECTRIC','SUV','SEDAN','HATCHBACK','VAN','MINIVAN','CONVERTIBLE','COUPE','WAGON','PICKUP'].map(value=><option key={value} value={value}>{rentalLabel(value,chat.language)}</option>)}</Select></div><div><label htmlFor="filter-seats">{az?'Ən az yer sayı':'Minimum seats'}</label><Select id="filter-seats" value={values.seats} onChange={e=>setValues({...values,seats:e.target.value})}><option value="">{az?'İstənilən':'Any'}</option>{[2,4,5,6,7,8,9].map(seats=><option key={seats} value={seats}>{seats} {az?'yer':'seats'}</option>)}</Select></div><div><label htmlFor="filter-gear">{az?'Sürətlər qutusu':'Transmission'}</label><Select id="filter-gear" value={values.transmission} onChange={e=>setValues({...values,transmission:e.target.value})}><option value="">{az?'İstənilən':'Any'}</option>{['AUTOMATIC','MANUAL'].map(value=><option key={value} value={value}>{rentalLabel(value,chat.language)}</option>)}</Select></div><div><label htmlFor="filter-fuel">{az?'Yanacaq':'Fuel type'}</label><Select id="filter-fuel" value={values.fuel} onChange={e=>setValues({...values,fuel:e.target.value,category:values.category==='ELECTRIC'?'':values.category})}><option value="">{az?'İstənilən':'Any'}</option>{['PETROL','DIESEL','HYBRID','ELECTRIC','LPG'].map(value=><option key={value} value={value}>{rentalLabel(value,chat.language)}</option>)}</Select></div><div><label htmlFor="filter-budget">{az?'Maksimum büdcə':'Maximum budget'}</label><div className="budget-field"><input id="filter-budget" type="number" min="0" value={values.budget} onChange={e=>setValues({...values,budget:e.target.value})} placeholder={az?'İstəyə görə':'Optional'}/><Select aria-label={az?'Büdcə valyutası':'Budget currency'} value={values.currency} onChange={e=>setValues({...values,currency:e.target.value as 'AZN'|'USD'})}><option>AZN</option><option>USD</option></Select></div></div><div><label htmlFor="filter-basis">{az?'Büdcə əsası':'Budget basis'}</label><Select id="filter-basis" value={values.budgetBasis} onChange={e=>setValues({...values,budgetBasis:e.target.value as 'DAY'|'TOTAL'})}><option value="DAY">{az?'Günlük':'Per day'}</option><option value="TOTAL">{az?'İcarə cəmi':'Rental total'}</option></Select></div></div><div className="filter-panel-actions"><button type="button" className="text-button" disabled={chat.busy} onClick={clearFilters}>{az?'Filtrləri sıfırla':'Clear filters'}</button><button className="primary" type="submit" disabled={chat.busy}>{az?'Filtrləri tətbiq et':'Apply filters'}<ArrowRight size={17}/></button></div></form>}
            </>:null}
            <div className="results-heading"><div><p className="eyebrow">{savedOnly?(az?'YADDA SAXLANILANLAR':'YOUR SAVED CARS'):hasResults?(az?'SƏFƏRİNİZ ÜÇÜN':'FOR YOUR JOURNEY'):(az?'PARKIMIZI KƏŞF EDİN':'EXPLORE OUR FLEET')}</p><h2 ref={resultsHeading}>{savedOnly?(az?'Yadda saxlanılan avtomobillər':'Your saved cars'):hasResults?(az?'Sizə uyğun avtomobillər':'Cars for your trip'):(az?'Bütün avtomobillərimizə baxın':'Explore all our cars')}</h2><p>{branch?(az?branch.name_az:branch.name_en):(az?'Bütün məntəqələr':'All pickup locations')}{inventory.data&&` · ${total} ${az?'avtomobil':'cars'}`}</p></div>{hasResults?<label className="sort-label">{az?'Sıralama':'Sort by'}<Select aria-label={az?'Sıralama':'Sort by'} value={sort} onChange={e=>setSort(e.target.value)}><option value="recommended">{az?'Tövsiyə olunur':'Recommended'}</option><option value="price-low">{az?'Qiymət: aşağıdan yuxarı':'Price: low to high'}</option><option value="price-high">{az?'Qiymət: yuxarıdan aşağı':'Price: high to low'}</option><option value="seats">{az?'Yerlərin sayı':'Most seats'}</option></Select></label>:<button className="text-button" type="button" disabled={chat.busy||!values.branch} onClick={browseAll}>{az?'Bütün avtomobillərə bax':'Browse all cars'}<ArrowRight size={19}/></button>}</div>
            {hasResults&&query?.pickup_at&&query?.return_at&&<div className="trip-summary"><MapPin size={19}/><span>{branch?.address||branch?.city||'Azerbaijan'}</span><span className="trip-summary-dates">{formatRentalDate(query.pickup_at,chat.language)} → {formatRentalDate(query.return_at,chat.language)}</span></div>}
            {hasResults&&<div className="results-note"><ShieldCheck size={21}/><p><b>{az?'Qiymətə baxın. Sonra qərar verin.':'See the details. Then decide.'}</b> {az?'Təklifinizdə səfərin qiyməti, depozit və bütün əlavələr ayrı göstərilir.':'Your quote includes the trip price and a clear breakdown of your deposit and extras.'}</p></div>}
            {inventory.error||branches.error?<div className="empty-state" role="alert"><Car size={36}/><h3>{az?'Avtomobillər yüklənmədi':'We couldn’t load the cars'}</h3><p>{(inventory.error||branches.error)?.message}</p><button type="button" className="secondary" onClick={()=>{inventory.refetch();branches.refetch();}}>{az?'Yenidən cəhd et':'Try again'}<ArrowRight size={18}/></button></div>:inventory.isPending&&!emptySaved?<div className={'vehicle-skeletons '+(hasResults?'':'vehicle-skeletons--grid')} aria-label={az?'Avtomobillər yüklənir':'Loading cars'}>{[1,2,3].map(n=><div className="vehicle-skeleton" key={n}><span/><div><span/><span/><span/></div></div>)}</div>:cars.length===0?<div className="empty-state"><Car size={38}/><h3>{savedOnly?(az?'Bu məntəqədə yadda saxlanılan avtomobil yoxdur':'No saved cars match this search'):(az?'Uyğun avtomobil tapılmadı':'No cars match these details')}</h3><p>{savedOnly?(az?'Avtomobilin yanındakı ürəyi seçib yadda saxlayın və ya götürmə məntəqəsini dəyişin.':'Use the heart on a car to save it, or choose another pickup location.'):(az?'Başqa tarix və ya məntəqə seçin, yaxud filtrləri dəyişin.':'Try different dates, another pickup location, or fewer filters.')}</p><button type="button" className="secondary" onClick={()=>{if(savedOnly)setSavedOnly(false);else clearFilters();}}>{savedOnly?(az?'Avtomobillərə bax':'Explore cars'):(az?'Filtrləri sıfırla':'Clear filters')}<ArrowRight size={18}/></button></div>:<div className={hasResults?'vehicle-list':'fleet-grid'}>{cars.map(car=><VehicleCard key={car.vehicle_id} car={car} language={chat.language} branch={branches.data?.find(b=>b.id===car.branch_id)} variant={hasResults?'list':'grid'} onSelect={chooseCar} onSave={saveCar} saved={saved.includes(car.vehicle_id)} disabled={chat.busy||!chat.id}/>)}</div>}
            {display.currency==='USD'&&<p className="currency-note" role="status">{display.usdAvailable?(az?'USD qiymətləri məlumat üçündür. Ödəniş və təsdiqlənmiş təklif AZN ilədir.':'USD prices are estimates. Payment and confirmed quotes are in AZN.'):(az?'USD məzənnəsi hazırda yoxdur. AZN qiymətləri göstərilir.':'USD rate is currently unavailable. Showing AZN prices.')}{display.usdAvailable&&` · CBAR ${display.rates?.usd.effective_date}`}</p>}
            {!inventory.error&&!emptySaved&&inventory.data&&<Pagination page={inventory.data.page} pages={inventory.data.pages} total={total} pageSize={inventory.data.page_size} count={cars.length} onChange={changePage} busy={inventory.isFetching} language={chat.language}/>}
            {hasResults&&assistant==='closed'&&<button className="concierge-inline" type="button" onClick={()=>setAssistant('side')}><Sparkle size={24} weight="fill"/><div><b>{az?'Seçim etməkdə kömək lazımdır?':'A little help choosing?'}</b><span>{az?'Yol köməkçisinə səfərinizdən danışın.':'Tell the Yol concierge about your trip.'}</span></div><ArrowUpRight size={23}/></button>}
          </section>
        </div>
        {chat.error&&assistant==='closed'&&<div className="error-banner" role="alert">{chat.error}<button type="button" onClick={()=>{if(chat.id){setAssistant('side');chat.retry();}else window.location.reload();}}>{az?'Yenidən cəhd et':'Retry'}</button></div>}
      </div>
    </main>
    <footer className="container site-footer"><a className="brand" href="/">yol<span>.</span></a><span>© {new Date().getFullYear()} Yol · Azerbaijan</span><a href="/admin">{az?'İdarəetmə':'Operator console'}<ArrowUpRight size={16}/></a></footer>
    <BookingDrawer car={selected} branch={branches.data?.find(b=>b.id===selected?.branch_id)} values={selectedValues} language={chat.language} catalog={extras.data||[]} busy={chat.busy} conversationId={chat.id} onClose={()=>setSelected(null)} onSend={chat.send} onRetry={chat.retry} canRetry={chat.hasPending} initialExtras={extraSelections}/>
  </>;
}
