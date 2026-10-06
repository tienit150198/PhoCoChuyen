/** Geometry stays in ground coordinates; the camera never changes navigation. */
import {TOWN_ZOOM} from './island';
import townLayout from '../../game/town_layout.json';
import {BUILDING_ART} from './building-art';
export interface Point { x: number; y: number }
export interface Rect { x0: number; y0: number; x1: number; y1: number }
export interface Career { id: string; short?: string; name?: string; place?: string; station?: string; category?: string; color?: string; [key: string]: unknown }
export interface Navigation { bounds: Rect; roads: Rect[]; obstacles: Rect[]; step: number; clearance: number }
export interface Building { id: string; meta: Career; at: Point; door: Point; footprint: Rect; variant: 'grocery' | 'home' | 'cafe'; district: number; slot:number }
export interface CameraView {width:number;height:number;scrollX:number;scrollY:number;zoom:number}
export type Facing='se'|'sw'|'ne'|'nw';
export interface RemotePlayer extends Point {pid:string;name:string;look:Record<string,any>;gender:'male'|'female'|'none';direction:Facing}
export interface TownLandmark {id:'outing:fishing'|'outing:boat'|'outing:pool';label:string;kind:'pond'|'boat'|'pool';at:Point;approach:Point;footprint:Rect}
export const CAMERA_ZOOM={min:.24,max:1.6};
export {ISLAND_PLAN,ISLAND_REFERENCE,activeIslandRegions,islandCoastline,insideIsland,islandWorldBounds,islandOverviewCamera} from './island';
export const project = (p: Point, hw=64, hh=32, origin: Point={x:0,y:0}): Point => ({x:origin.x+(p.x-p.y)*hw,y:origin.y+(p.x+p.y)*hh});
export const unproject = (p: Point, hw=64, hh=32, origin: Point={x:0,y:0}): Point => {
  const a=(p.x-origin.x)/hw,b=(p.y-origin.y)/hh;return {x:(a+b)/2,y:(b-a)/2};
};
/** Cache the viewport with a pan margin; distant zoom never allocates a whole-town bitmap. */
export function groundCacheRegion(view:Rect,zoom=1){
  const margin=220,region={x0:Math.floor(view.x0-margin),y0:Math.floor(view.y0-margin),x1:Math.ceil(view.x1+margin),y1:Math.ceil(view.y1+margin)},w=region.x1-region.x0,h=region.y1-region.y0;
  const scale=Math.min(1.25,Math.max(.4,zoom),Math.sqrt(2396000/(w*h))),width=Math.ceil(w*scale),height=Math.ceil(h*scale);
  return {region,width,height,scale,scroll:{x:region.x0+width/(2*scale)-width/2,y:region.y0+height/(2*scale)-height/2}};
}
/** Art aliases never change stable catalogue IDs or the public town geometry. */
export function townBuildingArt(meta:Career,fallback:Building['variant']){return BUILDING_ART[meta.id]||fallback;}
/** Aerial leisure artwork lies flat on its reserved footprint rather than standing upright. */
export function landmarkPlaneGeometry(r:Rect){const w=r.x1-r.x0,d=r.y1-r.y0;return {x:(r.x0-r.y1)*64,y:(r.x0+r.y0)*32,width:(w+d)*64,height:(w+d)*32,a:w*64,b:w*32,c:-d*64,d:d*32,e:d*64,depth:(r.x1+r.y1)*32};}
/** Our camera never rotates; this transform stays current even while Phaser is asleep. */
export const cameraWorldPoint = (p:Point,camera:{width:number;height:number;scrollX:number;scrollY:number;zoom:number}): Point => ({x:camera.scrollX+camera.width/2+(p.x-camera.width/2)/camera.zoom,y:camera.scrollY+camera.height/2+(p.y-camera.height/2)/camera.zoom});
export function defaultCamera(mode:'town'|'work',width:number,height:number):CameraView{
  const work=mode==='work',zoom=width<=620?(work?Math.min(.64,Math.max(.5,width/700)):.64):Math.max(work?CAMERA_ZOOM.min:.38,Math.min(work?1.1:.92,width/(work?1340:1220),height/(work?1040:900))),center=work?{x:0,y:225}:project({x:6.7,y:6.7},64,32,{x:0,y:-260});
  return {width,height,zoom,scrollX:center.x-width/2,scrollY:center.y-height/2};
}
/** Keep intentional pan at one viewport size; a phone transition starts with a fitted room. */
export function resizedCamera(mode:'town'|'work',old:CameraView,width:number,height:number):CameraView{
  if(old.width===width&&old.height===height)return {...old};
  if((old.width<=620)!==(width<=620))return defaultCamera(mode,width,height);
  const zoom=Math.max(mode==='town'?TOWN_ZOOM.min:CAMERA_ZOOM.min,Math.min(CAMERA_ZOOM.max,old.zoom*defaultCamera(mode,width,height).zoom/defaultCamera(mode,old.width,old.height).zoom));
  return {width,height,zoom,scrollX:old.scrollX+(old.width-width)/2,scrollY:old.scrollY+(old.height-height)/2};
}
export function normalizeMovementInput(x:number,y:number):Point{
  x=Number.isFinite(x)?Math.max(-1,Math.min(1,x)):0;y=Number.isFinite(y)?Math.max(-1,Math.min(1,y)):0;
  const length=Math.max(1,Math.hypot(x,y));return {x:x/length,y:y/length};
}
/** Analog and keyboard movement share continuous collision checks and wall sliding. */
export function moveOnGround(nav:Navigation,from:Point,input:Point,dt:number):Point{
  const axis=normalizeMovementInput(input.x,input.y),seconds=Number.isFinite(dt)?Math.max(0,Math.min(.06,dt)):0,delta=unproject({x:axis.x*170*seconds,y:axis.y*170*seconds}),next={x:from.x+delta.x,y:from.y+delta.y};
  if(lineClear(nav,from,next))return next;
  const slides=[{x:next.x,y:from.y},{x:from.x,y:next.y}].sort((a,b)=>Math.hypot(b.x-from.x,b.y-from.y)-Math.hypot(a.x-from.x,a.y-from.y));
  return slides.find(p=>lineClear(nav,from,p))||{x:from.x,y:from.y};
}
export function advanceRoute(from:Point,path:Point[],stride:number,metric:'ground'|'screen'='ground',nav?:Navigation):{point:Point;path:Point[];arrived:boolean}{
  if(!path.length)return {point:{x:from.x,y:from.y},path:[],arrived:false};
  let point={...from},step=Number.isFinite(stride)?Math.max(0,stride):0,index=0;
  while(index<path.length){const goal=path[index],dx=goal.x-point.x,dy=goal.y-point.y,delta=metric==='screen'?project({x:dx,y:dy}):{x:dx,y:dy},distance=Math.hypot(delta.x,delta.y);
    const next=distance>step+1e-9?{x:point.x+dx/distance*step,y:point.y+dy/distance*step}:goal;
    // A frame spanning a sharp corner must not visually cut through a trunk/wall.
    // Finish at the corner only when that direct chord is blocked; open turns keep their stride.
    if(nav&&index>0&&!lineClear(nav,from,next))return {point,path:path.slice(index),arrived:false};
    if(distance>step+1e-9)return {point:next,path:path.slice(index),arrived:false};
    point={...goal};step=Math.max(0,step-distance);index++;
  }
  return {point,path:[],arrived:true};
}
/** Apply only while walking, so an idle user's deliberate camera pan stays untouched. */
export function followCamera(camera:CameraView,point:Point,dt:number):CameraView{
  const x=camera.width/2+(point.x-camera.scrollX-camera.width/2)*camera.zoom,y=camera.height/2+(point.y-camera.scrollY-camera.height/2)*camera.zoom;
  const marginX=Math.min(160,camera.width*.23),top=Math.min(180,camera.height*.22),bottom=camera.height*.72;
  const dx=x-Math.max(marginX,Math.min(camera.width-marginX,x)),dy=y-Math.max(top,Math.min(bottom,y)),smooth=1-Math.exp(-8*Math.max(0,Math.min(.06,dt)));
  return {...camera,scrollX:camera.scrollX+dx/camera.zoom*smooth,scrollY:camera.scrollY+dy/camera.zoom*smooth};
}
export function presenceDirection(from:Point,to:Point,previous:Facing='se'):Facing{
  const dx=to.x-from.x,dy=to.y-from.y;if(Math.hypot(dx,dy)<1e-8)return previous;
  // Four illustrated facings meet at screen-horizontal/vertical boundaries.
  // Retain the current valid facing around that boundary to avoid rapid flipping.
  const xFacing:Facing=dx>=0?'se':'nw',yFacing:Facing=dy>=0?'sw':'ne';
  if(Math.abs(Math.abs(dx)-Math.abs(dy))<Math.max(Math.abs(dx),Math.abs(dy))*.12&&(previous===xFacing||previous===yFacing))return previous;
  return Math.abs(dx)>=Math.abs(dy)?dx>=0?'se':'nw':dy>=0?'sw':'ne';
}
/** Gait follows distance, so slow joystick walking and frame drops never shuffle in place. */
export function walkingPose(distance:number,moving:boolean,reduced=false){
  if(!moving||reduced)return {frame:0,lean:0,squash:1};
  const phase=Math.max(0,distance)/104*Math.PI*2;
  return {frame:[0,1,0,2][Math.floor(Math.max(0,distance)/26)%4],lean:Math.sin(phase)*.018,squash:1-Math.abs(Math.sin(phase))*.012};
}
/** Copy only the public presence contract; private game data never enters the renderer. */
export function publicTownPlayers(peers:unknown,nav?:Navigation):RemotePlayer[]{
  if(!Array.isArray(peers))return [];const seen=new Set<string>(),result:RemotePlayer[]=[];
  for(const peer of peers){
    if(!peer||typeof peer.pid!=='string'||!peer.pid.trim()||seen.has(peer.pid)||!Number.isFinite(peer.x)||!Number.isFinite(peer.y))continue;
    const at=nav?nearestWalkable(nav,{x:peer.x,y:peer.y}):{x:peer.x,y:peer.y};if(!at)continue;
    const look:Record<string,any>={},source=peer.look&&typeof peer.look==='object'&&!Array.isArray(peer.look)?peer.look:{};
    for(const slot of ['hair','shade','skin','top','bottom','shoes','acc'])if(typeof source[slot]==='string')look[slot]=source[slot].slice(0,48);
    if(typeof source.uniform==='boolean')look.uniform=source.uniform;
    if(source.tint&&typeof source.tint==='object'&&!Array.isArray(source.tint)){look.tint=Object.create(null);for(const [item,color] of Object.entries(source.tint))if(typeof color==='string'&&item.length<=48)look.tint[item]=color.slice(0,48);}
    seen.add(peer.pid);result.push({pid:peer.pid,name:typeof peer.name==='string'?peer.name.slice(0,64):'Người chơi',look,gender:peer.gender==='male'||peer.gender==='female'?peer.gender:'none',...at,direction:['se','sw','ne','nw'].includes(peer.direction)?peer.direction:'se'});
  }
  return result;
}
export function interpolateRoute(from:Point,path:Point[],progress:number):Point{
  if(!path.length)return {x:from.x,y:from.y};const amount=Math.max(0,Math.min(1,Number.isFinite(progress)?progress:0));if(amount===1)return {...path[path.length-1]};
  let total=0,previous=from;for(const point of path){total+=Math.hypot(point.x-previous.x,point.y-previous.y);previous=point;}
  let remaining=total*amount;previous=from;
  for(const point of path){const dx=point.x-previous.x,dy=point.y-previous.y,length=Math.hypot(dx,dy);if(length>0&&remaining<=length)return {x:previous.x+dx*remaining/length,y:previous.y+dy*remaining/length};remaining-=length;previous=point;}
  return {x:previous.x,y:previous.y};
}
export const gestureIsDrag = (start: Point, end: Point, threshold=8): boolean => Math.hypot(end.x-start.x,end.y-start.y)>threshold;
export const activeTasks = (room: {tasks?: any[]} | null | undefined): any[] => (room?.tasks||[]).filter(t=>!['completed','referred','cancelled'].includes(t.status));
export const WORK_WINDOW={x:5.5,y:0,z:130};
export const WORK_FOOD_SHELF:Rect={x0:6.8,y0:.3,x1:7.25,y1:1.4};
export const workWindowAnchors=()=>{const glass=project(WORK_WINDOW,64,32,{x:0,y:-WORK_WINDOW.z});return {glass,window:{x:glass.x,y:glass.y+43}};};
export const canvasDescription=(mode:'town'|'work',career:string)=>mode==='town'?'Khu phố isometric. Chạm cửa tiệm, kéo để xem phố, dùng phím mũi tên để đi và E để tương tác.':`${career}. Chạm một vị trí làm việc, dùng phím mũi tên để đi và E để tương tác.`;
export function effectFrameState(ev:{t0:number;end?:number|null}|null|undefined,time:number,reduced:boolean){
  if(!ev)return {animate:false,needsFrames:false,clear:false};
  const finished=ev.end!=null,clear=finished&&time-ev.end!>=2.5,animate=!reduced&&!clear&&(finished||time-ev.t0<6);
  return {animate,needsFrames:!clear&&(finished||animate),clear};
}
export function nearestReachableHotspot<T extends {id:string;approach:Point}>(nav:Navigation,from:Point,hotspots:T[],range=2.4):T|null{
  const nearby=hotspots.map(h=>({h,d:Math.hypot(h.approach.x-from.x,h.approach.y-from.y)})).filter(h=>h.d<=range).sort((a,b)=>a.d-b.d);
  for(const {h} of nearby)if(findRoute(nav,from,h.approach).length)return h;return null;
}
export interface SavedDecor {id:'plant'|'lamp'|'seat'|'rug'|'poster';spot:string;at:Point;z:number;footprint:Rect|null}
export interface RoomAppearance {theme:'boba'|'warm'|'sage'|'lavender';wall:string;wallSide:string;tier:'cozy'|'sunny'|'garden';security:string[];decor:SavedDecor[];tools:string[];gearTier:number;needsRepair:boolean}
/** Workplace saves store semantic spots, never screen pixels. Keep those entries unchanged.
 * Named old Boba plan positions map to floor/sill/wall anchors on the new 10×9 floor.
 * journey.decor is the separate home editor's free-unit layout and is not workplace decor.
 */
export function roomAppearance(room:any,career=''):RoomAppearance{
  const theme:RoomAppearance['theme']=['warm','sage','lavender'].includes(room?.theme)?room.theme:'boba';
  const walls={boba:['#f1dfbd','#e2cba8'],warm:['#fff0da','#ecd8b9'],sage:['#edf5e8','#c8d8c0'],lavender:['#f3e9fb','#d9cce6']};
  const owned=new Set<string>(room?.upgrades||[]),decor:SavedDecor[]=[];
  const floor:Record<string,Point>={corner:{x:2.55,y:5.3},front:{x:7.1,y:7.95},center:{x:4.9,y:6.7}};
  for(const id of ['plant','lamp','seat','rug','poster'] as const){const entry=room?.decor?.[id];if(!entry||!owned.has(id)||!['window','corner','front','center','wall'].includes(entry.spot))continue;
    let at:Point,z=0,footprint:Rect|null=null;
    if(id==='poster'){at={x:2.2,y:.04};z=140;}
    else if(entry.spot==='window'&&id!=='rug'){at={x:WORK_WINDOW.x+({plant:-.4,lamp:.1,seat:.65}[id]||0),y:.05};z=WORK_WINDOW.z-25;}
    else{at={...(floor[entry.spot]||{x:5.5,y:7.6})};const offset={plant:-.34,lamp:.32,seat:0,rug:0}[id];at.x+=offset;if(id!=='rug'){const rx=id==='seat'?.55:.26,ry=id==='seat'?.34:.24;footprint={x0:at.x-rx,y0:at.y-ry,x1:at.x+rx,y1:at.y+ry};}}
    decor.push({id,spot:entry.spot,at,z,footprint});
  }
  const tier:RoomAppearance['tier']=['sunny','garden'].includes(room?.ops?.property?.tier)?room.ops.property.tier:'cozy';
  const security=[...new Set<string>((room?.ops?.security?.items||[]).filter((i:string)=>['bell','camera','lock','light'].includes(i)))].sort();
  let gearTier=0;for(const id of owned){const match=id.match(/^workgear_(.+)_([123])$/);if(match&&(!career||match[1]===career))gearTier=Math.max(gearTier,Number(match[2]));}
  return {theme,wall:walls[theme][0],wallSide:walls[theme][1],tier,security,decor,tools:['shelf','workbench','board'].filter(id=>owned.has(id)),gearTier,needsRepair:typeof room?.ops?.equipment?.condition==='number'&&room.ops.equipment.condition<100};
}
export const makeNavigation = (options: Omit<Navigation,'clearance'> & {clearance?:number}): Navigation => ({...options,clearance:options.clearance??.14});
export const inside = (p: Point,r: Rect): boolean => p.x>=r.x0&&p.x<=r.x1&&p.y>=r.y0&&p.y<=r.y1;
export const isWalkable = (nav: Navigation,p: Point): boolean => inside(p,nav.bounds)&&nav.roads.some(r=>inside(p,r))&&!nav.obstacles.some(r=>inside(p,{x0:r.x0-nav.clearance,y0:r.y0-nav.clearance,x1:r.x1+nav.clearance,y1:r.y1+nav.clearance}));

/** Continuous segment/rectangle intervals prevent smoothing through small gaps. */
function interval(a:Point,b:Point,r:Rect): [number,number] | null {
  let lo=0,hi=1;
  for(const [v,d,min,max] of [[a.x,b.x-a.x,r.x0,r.x1],[a.y,b.y-a.y,r.y0,r.y1]]){
    if(Math.abs(d)<1e-9){if(v<min||v>max)return null;continue;}
    const t0=(min-v)/d,t1=(max-v)/d;lo=Math.max(lo,Math.min(t0,t1));hi=Math.min(hi,Math.max(t0,t1));if(lo>hi)return null;
  }
  return [lo,hi];
}
export function lineClear(nav:Navigation,a:Point,b:Point): boolean {
  if(!isWalkable(nav,a)||!isWalkable(nav,b))return false;
  for(const o of nav.obstacles){const span=interval(a,b,{x0:o.x0-nav.clearance,y0:o.y0-nav.clearance,x1:o.x1+nav.clearance,y1:o.y1+nav.clearance});
    // Touching one padded corner has no interior overlap. Ignore sub-nanoframe
    // intervals from floating-point rounding, consistently for long and short segments.
    if(span&&span[1]-span[0]>1e-9)return false;
  }
  const spans=nav.roads.map(r=>interval(a,b,r)).filter((r):r is [number,number]=>!!r).sort((a,b)=>a[0]-b[0]);
  let covered=0;for(const [lo,hi] of spans){if(lo>covered+1e-8)return false;covered=Math.max(covered,hi);if(covered>=1-1e-8)return true;}return false;
}
export function nearestWalkable(nav:Navigation,p:Point): Point | null {
  if(isWalkable(nav,p))return p;
  let result:Point|null=null,distance=Infinity;
  // A single clamp remains inside furniture on a room-wide road. Search the free
  // rectangle boundaries too, including intersecting furniture's corner gaps.
  const epsilon=.01,pad=nav.clearance+epsilon;
  const consider=(q:Point)=>{const d=Math.hypot(q.x-p.x,q.y-p.y);if(d<distance&&isWalkable(nav,q)){result=q;distance=d;}};
  for(const road of nav.roads){
    const r={x0:Math.max(road.x0,nav.bounds.x0),y0:Math.max(road.y0,nav.bounds.y0),x1:Math.min(road.x1,nav.bounds.x1),y1:Math.min(road.y1,nav.bounds.y1)};
    if(r.x1<=r.x0||r.y1<=r.y0)continue;
    const x=Math.max(r.x0,Math.min(r.x1,p.x)),y=Math.max(r.y0,Math.min(r.y1,p.y));consider({x,y});
    const obstacles=nav.obstacles.filter(o=>o.x1+pad>=r.x0&&o.x0-pad<=r.x1&&o.y1+pad>=r.y0&&o.y0-pad<=r.y1);
    const xs=[x,r.x0,r.x1,...obstacles.flatMap(o=>[o.x0-pad,o.x1+pad])].filter(v=>v>=r.x0&&v<=r.x1);
    const ys=[y,r.y0,r.y1,...obstacles.flatMap(o=>[o.y0-pad,o.y1+pad])].filter(v=>v>=r.y0&&v<=r.y1);
    for(const x of xs)for(const y of ys)consider({x,y});
  }
  return result;
}
/** Eight-neighbour A* with exact segment checks, then safe path simplification. */
export function findRoute(nav:Navigation,start:Point,end:Point): Point[] {
  if(!isWalkable(nav,start)||!isWalkable(nav,end))return [];
  if(lineClear(nav,start,end))return [end];
  const step=nav.step,cols=Math.ceil((nav.bounds.x1-nav.bounds.x0)/step)+1,rows=Math.ceil((nav.bounds.y1-nav.bounds.y0)/step)+1;
  const point=(key:number):Point=>({x:nav.bounds.x0+(key%cols)*step,y:nav.bounds.y0+Math.floor(key/cols)*step});
  const nearby=(p:Point):number[]=>{
    const cx=Math.round((p.x-nav.bounds.x0)/step),cy=Math.round((p.y-nav.bounds.y0)/step),out:number[]=[];
    for(let y=cy-2;y<=cy+2;y++)for(let x=cx-2;x<=cx+2;x++){if(x<0||y<0||x>=cols||y>=rows)continue;const key=y*cols+x;if(lineClear(nav,p,point(key)))out.push(key);}return out;
  };
  const targets=new Set(nearby(end)),begins=nearby(start);if(!targets.size||!begins.length)return [];
  const costs=new Map<number,number>(),parents=new Map<number,number>(),closed=new Set<number>(),heap:{key:number,rank:number}[]=[];
  const put=(key:number,rank:number)=>{heap.push({key,rank});let i=heap.length-1;while(i>0){const p=(i-1)>>1;if(heap[p].rank<=rank)break;[heap[p],heap[i]]=[heap[i],heap[p]];i=p;}};
  const take=()=>{const first=heap[0],last=heap.pop()!;if(heap.length){heap[0]=last;let i=0;for(;;){let j=i*2+1;if(j>=heap.length)break;if(j+1<heap.length&&heap[j+1].rank<heap[j].rank)j++;if(heap[i].rank<=heap[j].rank)break;[heap[i],heap[j]]=[heap[j],heap[i]];i=j;}}return first.key;};
  for(const key of begins){const p=point(key),g=Math.hypot(p.x-start.x,p.y-start.y);costs.set(key,g);parents.set(key,-1);put(key,g+Math.hypot(p.x-end.x,p.y-end.y));}
  let goal:number|undefined;
  while(heap.length){const key=take();if(closed.has(key))continue;if(targets.has(key)){goal=key;break;}closed.add(key);const p=point(key),cx=key%cols,cy=Math.floor(key/cols);
    for(const [dx,dy] of [[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[1,-1],[-1,1],[1,1]]){const x=cx+dx,y=cy+dy;if(x<0||y<0||x>=cols||y>=rows)continue;const n=y*cols+x;if(closed.has(n))continue;const q=point(n);if(!lineClear(nav,p,q))continue;const g=costs.get(key)!+Math.hypot(dx,dy)*step;if(g>=(costs.get(n)??Infinity))continue;costs.set(n,g);parents.set(n,key);put(n,g+Math.hypot(q.x-end.x,q.y-end.y));}
  }
  if(goal===undefined)return [];
  const raw:Point[]=[end];for(let key=goal;key!==-1;key=parents.get(key)??-1)raw.push(point(key));raw.reverse();
  const smooth:Point[]=[];let from=start,i=0;while(i<raw.length){let j=raw.length-1;while(j>i&&!lineClear(nav,from,raw[j]))j--;smooth.push(raw[j]);from=raw[j];i=j+1;}return smooth;
}
/** 1.8.1's careers where they belong: police and rescue next to nurse (the service street), lifeguard on the block
 * beside the pool (slot 8), lighthouse last (the southern edge, by the sea). Only the order changes: live/town.py's
 * geometry depends on the count alone. */
export function townOrder<T extends {id:string}>(list:T[]):T[]{
  const q=[...list],take=(id:string)=>{const i=q.findIndex(c=>c.id===id);return i<0?null:q.splice(i,1)[0];};
  const lighthouse=take('lighthouse'),lifeguard=take('lifeguard'),near=[take('police'),take('rescue')].filter((c):c is T=>Boolean(c)),nurse=q.findIndex(c=>c.id==='nurse');
  if(near.length)q.splice(nurse<0?q.length:nurse+1,0,...near);
  if(lifeguard)q.splice(Math.min(7,q.length),0,lifeguard);
  if(lighthouse)q.push(lighthouse);
  return q;
}
export function townBuildings(catalogue:Career[]): Building[] {
  // Three familiar doors form the first block; remaining careers retain catalogue order.
  const first=['grocery','homemaker','cafe_bakery'];const ordered=townOrder(catalogue.filter(c=>c.playable!==false).sort((a,b)=>{const ai=first.indexOf(a.id),bi=first.indexOf(b.id);return (ai<0?99:ai)-(bi<0?99:bi);}));
  const slots=[0,1,6,2,3,4,5,...Array.from({length:Math.max(0,ordered.length-7)},(_,i)=>i+8)];
  return ordered.map((meta,i)=>{const j=slots[i],col=j%6,row=Math.floor(j/6),[dx,dy]=townLayout.setbacks[(j+row)%townLayout.setbacks.length],x=col*7+1+dx,y=row*7+1+dy;return {id:meta.id,meta,at:{x:x+1.8,y:y+3.2},door:{x:x+2.2,y:row*7+6.1+dy},footprint:{x0:x,y0:y,x1:x+4.2,y1:y+4.2},variant:(meta.id==='grocery'||meta.category==='shop'?'grocery':['cafe_bakery','milk_tea','restaurant','pho','com','tra_da','ice_cream'].includes(meta.id)?'cafe':'home') as Building['variant'],district:row,slot:j};});
}
export interface GardenProp {at:Point;kind:string;size:number;footprint:Rect}
export function townGarden(buildings:Building[]):GardenProp[]{
  return buildings.flatMap(b=>townLayout.gardens[(b.slot+b.district)%townLayout.gardens.length].map(p=>{
    const at={x:b.slot%6*7+p.x,y:Math.floor(b.slot/6)*7+p.y},r=['flowers','shrubs','rocks'].includes(p.kind)?.22:.15;
    return {at,kind:p.kind,size:p.size,footprint:{x0:at.x-r,y0:at.y-r,x1:at.x+r,y1:at.y+r}};
  }));
}
export function townRoads(buildings:Building[]):Rect[]{
  const rows=Math.max(2,Math.ceil((buildings.length+(buildings.length>7?1:0))/6)),bounds={x0:0,y0:0,x1:43,y1:rows*7+1},roads:Rect[]=[];
  for(let x=0;x<=6;x++)roads.push({x0:x*7+5.5,y0:0,x1:Math.min(43,x*7+7),y1:bounds.y1});
  for(let y=0;y<=rows;y++)roads.push({x0:0,y0:y*7+5.5,x1:43,y1:Math.min(bounds.y1,y*7+7)});
  return roads.filter(r=>r.x1>r.x0&&r.y1>r.y0);
}
export function townNavigation(buildings:Building[]): Navigation {
  const rows=Math.max(2,Math.ceil((buildings.length+(buildings.length>7?1:0))/6)),bounds={x0:0,y0:0,x1:43,y1:rows*7+1};
  return makeNavigation({bounds,roads:[bounds],obstacles:[...buildings.map(b=>b.footprint),...townLandmarks().map(p=>p.footprint),...townGarden(buildings).map(p=>p.footprint)],step:.5});
}
/** Shared data is consumed by Python too, so lawns, entrances and water agree online. */
export function townLandmarks():TownLandmark[]{return townLayout.commons.map(p=>({...p,at:{...p.at},approach:{...p.approach},footprint:{...p.footprint}})) as TownLandmark[];}
