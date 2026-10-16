/** 🚗 Vehicles on the island town (owner 16/10 "xe, máy bay … chạy thực tế ở map cũ và map mới"): the new interface's
 * share of public/js/v4/ride.js. A runtime module (the Phaser bundle imports /js/* as is, scripts/build_isometric.mjs).
 *   townVehicles(state,content)  what this player shows: `ride` the two-wheeler or car ridden in the streets (ride.js
 *                                choice: the same toggle as the old interface), `fleet` the yachts moored at the harbour
 *                                and the planes parked at the airfield (owned, not broken), `fly` the plane taken out
 *                                today ("Bay ngắm phố": it flies over the town once), `wire` the live presence's `r`
 *   peerVehicle(r,content)       someone else's `r` (live/town.py): a road vehicle under them, or their yacht/plane
 *   rideStamp / boatStamp / planeStamp  one cached canvas each (immutable: the scene uploads it once)
 * Auction plates (gold, game/garage.py `uq`) are drawn on the vehicle: a road plate at the back, a plane's registration
 * on its tail, a yacht's name on its hull. Phones: a stamp is drawn once per look, vehicle, side and wheel frame; parked
 * yachts and planes are static images, capped (MAX_PARKED) and culled with the rest of the town. */
import {choice,wire,fromWire,drawRide,plateAt,FAST,TWO} from '../v4/ride.js';
import {figureOf} from '../v4/look.js';

/** World px per character unit (the island's characters are about 110 px tall, ride.js draws them 140 units). */
export const RIDE_SCALE=.78;
/** Texture pixels per world px (sharp at the town's closest zoom without large bitmaps). */
export const RES=1.5;
/** Riding is faster than walking, never more than 1.8× (live/town.py SPEED leaves room for it). */
export const MAX_SPEED=1.8;
export const MAX_PARKED={boat:4,plane:3};
const BOX={x:116,up:228,down:24};
const HEX=/^#[0-9a-f]{6}$/i,TEXT_MAX=24;
const text=t=>typeof t==='string'&&t.length<=TEXT_MAX&&!/[\u0000-\u001f\u007f]/.test(t)?t.trim():'';

function cat(content){const g=content?.journey?.garage;return g&&Array.isArray(g.vehicles)?g:null;}
function paintHex(g,id,fallback){const p=(g.paints||[]).find(x=>x.id===id)||(g.paints||[]).find(x=>x.id===fallback);return HEX.test(p?.hex||'')?p.hex:'#d9534f';}

/** This player's vehicles on the island (see the header). Never throws: nothing to show is {ride:null,fleet:[],…}. */
export function townVehicles(state,content){
  const none={ride:null,fleet:[],fly:'',wire:null};
  try{
    const J=state?.journey,g=J?.story?J.garage:null,c=cat(content);
    if(!g||!c||!Array.isArray(g.cars))return none;
    const ride=choice(state,content)||null,fleet=[],count={boat:0,plane:0};
    for(const car of g.cars){
      const it=c.vehicles.find(v=>v.id===car?.id);
      if(!it||!(it.group in count)||car.broken!=null||count[it.group]>=MAX_PARKED[it.group])continue;
      count[it.group]++;
      const uq=text(car.uq?.t);
      fleet.push({id:it.id,group:it.group,name:String(it.name||''),emoji:String(it.emoji||''),hex:paintHex(c,car.color,it.paint),
        plate:uq||text(car.plate),uq:Boolean(uq),mine:true,...(it.limited?{limited:true}:{})});
    }
    const shown=fleet.find(f=>f.id===g.ride);   // the yacht/plane "đang đi": the live presence carries it
    const fly=typeof g.trip_id==='string'&&g.tripped&&fleet.some(f=>f.id===g.trip_id&&f.group==='plane')?g.trip_id:'';
    const r=ride?wire(ride):shown?{v:shown.id,c:(g.cars.find(x=>x.id===shown.id)?.color)||'',...(shown.uq?{p:shown.plate}:{})}:null;
    return {ride:ride?{...ride,group:TWO.has(ride.kind)?'bike':'car'}:null,fleet,fly,wire:r};
  }catch(e){console.warn('iso vehicles',e);return none;}
}

/** Someone else's vehicle from the live town (`r` {v, c, p?}): a road view, a yacht or a plane, or null. */
export function peerVehicle(r,content){
  if(!r||typeof r!=='object'||typeof r.v!=='string')return null;
  const c=cat(content),it=c?.vehicles.find(v=>v.id===r.v);if(!it)return null;
  if(it.group==='boat'||it.group==='plane'){const p=text(r.p);
    return {id:it.id,group:it.group,name:String(it.name||''),emoji:String(it.emoji||''),hex:paintHex(c,typeof r.c==='string'?r.c:'',it.paint),plate:p,uq:Boolean(p)};}
  const v=fromWire(r,content);return v?{...v,group:TWO.has(v.kind)?'bike':'car'}:null;
}

export const rideSpeed=v=>v?Math.min(MAX_SPEED,FAST[v.kind]||1.5):1;
/** ride.js art faces left: the island's sw/nw facings go left on screen, se/ne go right. */
export const faceOf=direction=>direction==='se'||direction==='ne'?1:-1;
/** Where the stamp's ground point is (Phaser origin). */
export const RIDE_ORIGIN={x:.5,y:BOX.up/(BOX.up+BOX.down)};

/** The rider on their vehicle, facing `face` (-1 left, 1 right), wheels at frame 0..2. A new canvas: the caller caches it. */
export function rideStamp({look,gender,v,face,frame=0}){
  const s=RIDE_SCALE*RES,cv=document.createElement('canvas');
  cv.width=Math.ceil(BOX.x*2*s);cv.height=Math.ceil((BOX.up+BOX.down)*s);
  const c=cv.getContext('2d');
  try{
    const F=look?figureOf(look,gender):null;
    drawRide(c,{x:BOX.x*s,y:BOX.up*s,s,px:1,F,fkey:JSON.stringify([look,gender]),v,r:{face,from:face,turn:1,ang:frame*Math.PI/3}});
  }catch(e){console.warn('iso ride art',e);}
  return cv;
}

/* ---- yachts and planes: side views facing left, flipped for the other side; their plate in gold when won ---- */
const shade=(hex,k)=>{const n=parseInt(hex.slice(1),16),f=v=>Math.max(0,Math.min(255,Math.round(k<0?v*(1+k):v+(255-v)*k)));return `rgb(${f(n>>16&255)},${f(n>>8&255)},${f(n&255)})`;};
function sign(c,x,y,w,h,words,gold){
  // the plate itself: ride.js plateAt (gold for an auction plate), wider for a long name
  plateAt(c,x,y,w,h,words,1,RES,gold);
}
/** A moored yacht (about 210 × 110 world px), its name on the hull. */
export function boatStamp(v,face=-1){
  const W=230,H=130,cv=document.createElement('canvas');cv.width=Math.ceil(W*RES);cv.height=Math.ceil(H*RES);
  const c=cv.getContext('2d');c.scale(RES,RES);c.translate(W/2,H-22);if(face>0)c.scale(-1,1);
  const hex=HEX.test(v?.hex||'')?v.hex:'#1b2a52';
  c.fillStyle='rgba(30,70,80,.22)';c.beginPath();c.ellipse(0,14,104,12,0,0,Math.PI*2);c.fill();
  // hull
  c.beginPath();c.moveTo(-104,-30);c.lineTo(96,-30);c.quadraticCurveTo(100,0,74,6);c.lineTo(-70,6);c.quadraticCurveTo(-96,-8,-104,-30);c.closePath();
  c.fillStyle=hex;c.fill();c.lineWidth=2;c.strokeStyle=shade(hex,-.35);c.stroke();
  c.fillStyle='#f6f2ea';c.fillRect(-100,-36,192,7);
  c.strokeStyle='rgba(255,255,255,.55)';c.lineWidth=2;c.beginPath();c.moveTo(-86,-14);c.lineTo(84,-14);c.stroke();
  // decks and cabin
  c.fillStyle='#fbf8f2';c.beginPath();c.moveTo(-62,-36);c.lineTo(-44,-62);c.lineTo(52,-62);c.lineTo(70,-36);c.closePath();c.fill();c.strokeStyle='#b9b2a6';c.lineWidth=1.5;c.stroke();
  c.beginPath();c.moveTo(-30,-62);c.lineTo(-18,-80);c.lineTo(34,-80);c.lineTo(44,-62);c.closePath();c.fill();c.stroke();
  c.fillStyle='#2f4a5c';for(let i=0;i<5;i++)c.fillRect(-46+i*21,-56,15,9);c.fillRect(-12,-76,40,8);
  c.strokeStyle='#d8d2c6';c.lineWidth=2.5;c.beginPath();c.moveTo(8,-80);c.lineTo(8,-100);c.stroke();
  c.fillStyle='#e2533c';c.beginPath();c.moveTo(8,-100);c.lineTo(24,-95);c.lineTo(8,-90);c.closePath();c.fill();
  const words=text(v?.plate);
  if(words){c.save();if(face>0)c.scale(-1,1);const w=Math.max(46,Math.min(120,words.length*7.4));sign(c,-w/2,-24,w,14,words,Boolean(v.uq));c.restore();}
  return cv;
}
/** A private plane (about 230 × 90 world px), its registration on the tail; `flying`: no ground shadow, gear up. */
export function planeStamp(v,face=-1,flying=false){
  const W=250,H=110,cv=document.createElement('canvas');cv.width=Math.ceil(W*RES);cv.height=Math.ceil(H*RES);
  const c=cv.getContext('2d');c.scale(RES,RES);c.translate(W/2,H-16);if(face>0)c.scale(-1,1);
  const hex=HEX.test(v?.hex||'')?v.hex:'#8d76bb';
  if(!flying){c.fillStyle='rgba(40,50,40,.2)';c.beginPath();c.ellipse(0,8,108,10,0,0,Math.PI*2);c.fill();
    c.strokeStyle='#5b5552';c.lineWidth=3;for(const x of [-70,26,40]){c.beginPath();c.moveTo(x,-14);c.lineTo(x,2);c.stroke();c.fillStyle='#3f3a38';c.beginPath();c.arc(x,3,4.5,0,Math.PI*2);c.fill();}}
  // fuselage
  c.beginPath();c.moveTo(-112,-24);c.quadraticCurveTo(-112,-44,-80,-46);c.lineTo(78,-46);c.lineTo(112,-74);c.lineTo(122,-74);c.lineTo(112,-30);c.quadraticCurveTo(60,-14,-80,-14);c.quadraticCurveTo(-110,-14,-112,-24);c.closePath();
  c.fillStyle='#f7f5f0';c.fill();c.strokeStyle='#a9a39a';c.lineWidth=1.5;c.stroke();
  c.fillStyle=hex;c.beginPath();c.moveTo(-104,-24);c.lineTo(100,-36);c.lineTo(104,-30);c.lineTo(-100,-19);c.closePath();c.fill();
  c.beginPath();c.moveTo(82,-46);c.lineTo(112,-74);c.lineTo(122,-74);c.lineTo(114,-46);c.closePath();c.fill();
  // cockpit, windows, wing, engine
  c.fillStyle='#2f4a5c';c.beginPath();c.moveTo(-104,-32);c.quadraticCurveTo(-98,-44,-82,-44);c.lineTo(-84,-34);c.closePath();c.fill();
  for(let i=0;i<6;i++){c.beginPath();c.ellipse(-60+i*18,-36,4.5,5,0,0,Math.PI*2);c.fill();}
  c.fillStyle=shade(hex,-.25);c.beginPath();c.moveTo(-18,-22);c.lineTo(34,-22);c.lineTo(58,-6);c.lineTo(44,-6);c.closePath();c.fill();
  c.fillStyle='#d8d4cc';c.beginPath();c.ellipse(70,-50,18,7,0,0,Math.PI*2);c.fill();c.strokeStyle='#9a948b';c.stroke();
  const words=text(v?.plate);
  if(words){c.save();c.translate(76,-34);if(face>0)c.scale(-1,1);const w=Math.max(42,Math.min(96,words.length*7));sign(c,-w/2,-6,w,12,words,Boolean(v.uq));c.restore();}
  return cv;
}
/** The stamp's size in world px (its texture is RES times larger). */
export const stampSize=cv=>({width:cv.width/RES,height:cv.height/RES});
/** Yacht berths in the harbour basin and plane stands on the airfield (town ground units: client/isometric/town-scenery.ts). */
export const BERTHS=[{x:83.6,y:32.2},{x:83.6,y:35.6},{x:83.6,y:39},{x:83.6,y:42.2},{x:85.8,y:33.9},{x:85.8,y:37.3}];
export const STANDS=[{x:61.5,y:21.2},{x:67.5,y:21.2},{x:73.5,y:21.2},{x:64.5,y:23.2},{x:70.5,y:23.2}];
/** Peers' yachts/planes after this player's own, each kind capped (phones: a few static images). */
export function parkedFleet(mine,peers,content){
  const out=[],count={boat:0,plane:0},cap={boat:BERTHS.length,plane:STANDS.length};
  const add=f=>{if(f&&f.group in count&&count[f.group]<cap[f.group]){out.push({...f,slot:count[f.group]++});}};
  for(const f of mine||[])add(f);
  for(const p of peers||[]){const v=peerVehicle(p?.r,content);if(v&&(v.group==='boat'||v.group==='plane'))add({...v,owner:String(p.name||'').slice(0,24)});}
  return out;
}
export const slotOf=f=>f.group==='boat'?BERTHS[f.slot%BERTHS.length]:STANDS[f.slot%STANDS.length];
export const stampKey=f=>`iso-veh-${f.group}-${f.id}-${f.hex}-${f.uq?1:0}-${encodeURIComponent(f.plate||'')}`;
export const stampOf=f=>f.group==='boat'?boatStamp(f,-1):planeStamp(f,-1);
/** The stamp's waterline / wheels (Phaser origin): boatStamp draws it 22 px over the bottom, planeStamp 10. */
export const stampOrigin=f=>f.group==='boat'?{x:.5,y:(130-20)/130}:{x:.5,y:(110-10)/110};
