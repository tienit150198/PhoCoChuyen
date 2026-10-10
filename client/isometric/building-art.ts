import {CAREER_ART} from './career-art';

/** Shared paintings remain available while a finished exterior is loading and
 * for older/non-catalogue callers. They are never the final career selection. */
export const LEGACY_BUILDING_ART:Record<string,string>={
  grocery:'grocery',mother_baby:'mother-baby',pharmacy:'pharmacy',
  accounting:'office',customer_care:'office',corp_accounting:'office',tax_payroll:'office',
  group_accounting:'office',hr_admin:'office',secretary:'office',it_helpdesk:'office',tour_guide:'office',
  restaurant:'pho',pho:'pho',com:'pho',naucom:'home',cafe_bakery:'cafe',milk_tea:'cafe',ice_cream:'cafe',
  farm:'market',fruit:'market',tra_da:'market',clothing:'grocery',
  florist:'florist',salon:'salon',nail:'salon',pet_care:'pet',pet_shop:'pet',teacher:'school',pagoda:'pagoda',
  delivery:'garage',garbage:'garage',drain:'garage',repair:'garage',garage:'garage',
  homestay:'home',homemaker:'home',giupviec:'home',babysitter:'home',photobooth:'office',pilot:'airport',flight_attendant:'airport',
  library:'school',nurse:'pharmacy',oil:'garage',railway:'airport',
  lighthouse:'lighthouse',rescue:'office',lifeguard:'market',police:'office',
  zpop:'grocery',
};
/** Exactly one complete exterior painting per real catalogue profession. */
export const BUILDING_ART:Record<string,string>={...LEGACY_BUILDING_ART,...Object.fromEntries(Object.values(CAREER_ART).map(a=>[a.career,a.key]))};
export const NEW_BUILDING_ART=['florist','salon','office','pet','school','pagoda','airport','market','lighthouse'];
/** Keep a shop name to at most two lines; automatic word wrap made long signs tiny. */
export function facadeTextLines(text:string){
  const clean=text.trim().replace(/\s+/g,' ');if(clean.length<=18)return clean;
  const words=clean.replace(/cà phê|nhà thuốc|kế toán|nhân sự|giao hàng/gi,part=>part.replace(' ','\u00a0')).split(' ');
  if(words.length<2)return clean;
  let best=1,score=Infinity;
  for(let i=1;i<words.length;i++){const left=words.slice(0,i).join(' ').length,right=words.slice(i).join(' ').length,delta=Math.abs(left-right);if(delta<score){score=delta;best=i;}}
  return [words.slice(0,best).join(' '),words.slice(best).join(' ')].join('\n').replace(/\u00a0/g,' ');
}
/** Sign centres are measured on each trimmed sprite's painted upper facade.
 * Width and height are fractions of sprite width/height, never ground coordinates. */
export const FACADE_SIGNS:Record<string,{x:number;y:number;width:number;height:number;angle:number;panel?:boolean}>={
  grocery:{x:.34,y:.326,width:.42,height:.086,angle:.33},
  cafe:{x:.37,y:.285,width:.31,height:.09,angle:.27},
  home:{x:.34,y:.50,width:.42,height:.08,angle:.30,panel:true},
  pharmacy:{x:.408,y:.329,width:.43,height:.068,angle:.33},
  'mother-baby':{x:.42,y:.447,width:.34,height:.077,angle:.31},
  garage:{x:.397,y:.336,width:.25,height:.09,angle:.35},
  pho:{x:.36,y:.25,width:.28,height:.09,angle:.30},
  florist:{x:.356,y:.358,width:.43,height:.084,angle:.30},
  salon:{x:.347,y:.343,width:.43,height:.084,angle:.30},
  office:{x:.295,y:.55,width:.43,height:.084,angle:.30},
  pet:{x:.355,y:.374,width:.43,height:.084,angle:.30},
  school:{x:.397,y:.38,width:.39,height:.084,angle:.30},
  pagoda:{x:.432,y:.45,width:.37,height:.084,angle:.25},
  airport:{x:.459,y:.467,width:.4,height:.084,angle:.23},
  lighthouse:{x:.4,y:.56,width:.35,height:.063,angle:.29,panel:true},
  market:{x:.371,y:.378,width:.41,height:.084,angle:.30},
  ...Object.fromEntries(Object.values(CAREER_ART).map(a=>[a.key,a.sign])),
};
