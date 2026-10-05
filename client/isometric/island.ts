import {project} from './model';
import type {CameraView,Point,Rect} from './model';

export interface IslandRegion {
  id:string;
  name:string;
  status:'active'|'reserved';
  navigationBounds:Rect|null;
  anchor:Point;
  coastline:readonly Point[];
}

/** Simplified natural shoreline observed in the 2014-02-01 reference, excluding piers.
 * East is +x, south is +y before the isometric projection. One uniform scale preserves
 * the ~1.8:1 outline; town streets are fictional and never geographic coordinates.
 */
export const ISLAND_REFERENCE=Object.freeze({
  name:'Đảo Hoàng Sa',internationalName:'Pattle Island',archipelago:'Quần đảo Hoàng Sa',
  source:'https://amti.csis.org/dao-hoang-sa/?lang=vi',imageDate:'2014-02-01',
  descriptionSource:'https://danang.gov.vn/vi/web/dng/w/ubnd-huyen-hoang-sa-i',
  outline:'simplified-natural-shoreline',groundAspect:1.8
});
const naturalShore=[
  [0,.38],[.05,.32],[.13,.28],[.23,.18],[.37,.09],[.49,.04],[.59,0],
  [.67,.04],[.80,.10],[.94,.15],[.98,.22],[.98,.42],[1,.53],[.98,.60],
  [.96,.74],[.945,.89],[.89,.93],[.76,.975],[.66,1],[.53,.99],[.40,.97],
  [.33,.93],[.22,.92],[.10,.91],[.04,.87],[.02,.80],[.015,.59],[0,.48]
].map(([x,y])=>({x:-49.6+x*142.2,y:-14.5+y*79}));
/** Future districts lie inside the same fixed island. They add no roads or jobs yet. */
export const ISLAND_PLAN=Object.freeze<{version:number;regions:readonly IslandRegion[]}>({version:2,regions:[
  {id:'core',name:ISLAND_REFERENCE.name,status:'active',navigationBounds:{x0:0,y0:0,x1:43,y1:50},anchor:{x:21.5,y:25},coastline:naturalShore},
  {id:'east-harbour',name:'Khu phía đông · mở sau',status:'reserved',navigationBounds:null,anchor:{x:64,y:25},coastline:[]},
  {id:'west-garden',name:'Vườn phía tây · mở sau',status:'reserved',navigationBounds:null,anchor:{x:-22,y:30},coastline:[]}
]});
export const TOWN_ZOOM={min:.03,max:1.6};
export const SEA_COLOR='#75bec1';

export function activeIslandRegions(){return ISLAND_PLAN.regions.filter(region=>region.status==='active');}
/** Closed Catmull-Rom curve keeps the shore organic while its control points stay editable. */
export function islandCoastline(outward=0,region:IslandRegion=activeIslandRegions()[0]):Point[]{
  const controls=region.coastline.map(p=>{const dx=p.x-region.anchor.x,dy=p.y-region.anchor.y,length=Math.hypot(dx,dy);return {x:p.x+dx/length*outward,y:p.y+dy/length*outward};}),points:Point[]=[];
  const interpolate=(a:number,b:number,c:number,d:number,t:number)=>.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t);
  for(let i=0;i<controls.length;i++)for(let s=0;s<8;s++){const a=controls[(i+controls.length-1)%controls.length],b=controls[i],c=controls[(i+1)%controls.length],d=controls[(i+2)%controls.length],t=s/8;points.push({x:interpolate(a.x,b.x,c.x,d.x,t),y:interpolate(a.y,b.y,c.y,d.y,t)});}
  return points;
}
export function insideIsland(p:Point){
  const points=islandCoastline(-1.15);let inside=false;
  for(let i=0,j=points.length-1;i<points.length;j=i++){const a=points[i],b=points[j];if((a.y>p.y)!==(b.y>p.y)&&p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x)inside=!inside;}
  return inside;
}
/** Includes water rim, roof height and coastal props, rather than fitting only road data. */
export function islandWorldBounds():Rect{
  const points=islandCoastline(6).map(p=>project(p));
  return {x0:Math.min(...points.map(p=>p.x))-130,y0:Math.min(...points.map(p=>p.y))-330,x1:Math.max(...points.map(p=>p.x))+130,y1:Math.max(...points.map(p=>p.y))+120};
}
export function islandOverviewCamera(width:number,height:number):CameraView{
  const bounds=islandWorldBounds(),zoom=Math.min((width-36)/(bounds.x1-bounds.x0),(height-174)/(bounds.y1-bounds.y0)),center={x:(bounds.x0+bounds.x1)/2,y:(bounds.y0+bounds.y1)/2};
  return {width,height,zoom,scrollX:center.x-width/2,scrollY:center.y-height/2};
}
