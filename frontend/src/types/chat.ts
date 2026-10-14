export type Language='en'|'az';
export type Money={amount_qepik:string;formatted:string;currency:'AZN'};
export type Card={type:string;[key:string]:any};
export type ChatResponse={run_id:string;message_id:string;language:Language;text:string;cards:Card[];conversation_phase:string;error_code?:string};
export type Message={id:string;role:string;text:string;cards:Card[]};
export type Branch={id:string;name_en:string;name_az:string;city:string;address?:string};
export type Extra={id:string;name_en:string;name_az:string;description_en:string;description_az:string;price_qepik:string;billing_unit:string};
export type Vehicle=Card & {type:'vehicle';vehicle_id:string;title:string;year:number;vehicle_type:string;class_code:string;seats:number;fuel_type:string;transmission:string;branch_id:string;features:string[];photo_url:string|null;daily_price:Money;rental_price:Money|null;availability_checked:boolean;best_fit:boolean};
export type SearchValues={branch:string;pickup:string;returnAt:string;category:string;seats:string;fuel:string;transmission:string;budget:string;currency:'AZN'|'USD';budgetBasis:'DAY'|'TOTAL'};
export type InventoryFilters={pickup_branch_id?:string;pickup_at?:string;return_at?:string;vehicle_type?:string;class_code?:string;minimum_seats?:number;fuel_type?:string;transmission?:string;budget_amount?:string;budget_currency?:'AZN'|'USD';budget_basis?:'DAY'|'TOTAL'};

export type InventoryPage={items:Vehicle[];total:number;page:number;page_size:number;pages:number};
