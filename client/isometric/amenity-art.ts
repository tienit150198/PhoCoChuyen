import type {Point} from './model';

/** Static, alpha-preserving illustrations. No per-sprite animation loop. */
export const CIVIC_ASSETS=Object.fromEntries([...['park','date','market','wedding','karaoke','pets'].map(id=>['civic-'+id,`/icons/cozy-v4/civic-${id}.webp`]),...['fairgrounds','dograce','district-rent','district-apartment','district-townhouse','district-villa'].map(id=>[id,`/icons/cozy-v5/${id}.webp`])]);
export interface AmenityArt {id:string;label:string;at:Point;art?:string;artAt?:Point;artWidth?:number}
export function amenityPlacement(p:AmenityArt){
  if(!p.art||!p.artAt||!Number.isFinite(p.artWidth)||!p.artWidth||p.artWidth<=0)return null;
  return {kind:p.art,at:p.artAt,width:p.artWidth,originY:.82};
}
/** Only sprites with a painted facade receive a mounted title. Open gardens use a stand. */
export const CIVIC_FACADES:Record<string,{x:number;y:number;width:number;height:number;angle:number;panel?:boolean}>={
  'civic-market':{x:.516,y:.177,width:.22,height:.08,angle:-.15},
  'civic-karaoke':{x:.573,y:.356,width:.29,height:.08,angle:-.16},
  'civic-wedding':{x:.64,y:.675,width:.26,height:.055,angle:.29,panel:true},
};
