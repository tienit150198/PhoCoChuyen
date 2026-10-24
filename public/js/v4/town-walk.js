/** 🗺️ Bản đồ phố: the home screen as a small town to stroll (owner 03/10: "như hàng rong hồi xưa, đi dạo rồi vào
 * các nơi công việc để làm"). The player's own character (outfit and all, v4/look.js) walks the streets of
 * scenes/town-place.js: tap the street to walk, tap a shop to walk to its door; at the door a small card says what it
 * is and holds one button, the same one the Hành trình list has ("Vào làm" = data-action choose: the same server
 * action, the same confirms, the same first-day start). Landmarks open what already exists (Ngân hàng, Nhà mình,
 * Gara, Cổng hội chợ, Quầy của bạn, Đi dạo, Nhóm phố, Quảng trường). "📋 Danh sách" on top opens the list
 * (v4/journey.js homeMain), unchanged; it is also the keyboard's and a screen reader's way in.
 * journey.js owns the sheet: it calls townHTML() for the page and townMount() after each render, which puts the one
 * persistent stage (canvas + card) back into the page's slot (data-morph-keep: a render never rebuilds it).
 * Light on phones, like the fair's walk (v4/fair-walk.js): the town is painted once per size and state into a cached
 * bitmap; a frame is a slice of it, the glow and the player (one cached sprite). Frames run only while the player
 * walks or the view moves (and ~12 a second for a new player's lit shops; none with reduced motion).
 * 🛵 A player who owns a vehicle (game/garage.py) rides it here (./ride.js): faster, wheels turning; at a door it is
 * parked beside the door and the player walks the last steps; the next walk starts by hopping back on. The small
 * "🛵 Đi xe / 🚶 Đi bộ" button on the stage changes it (each vehicle owned in turn, then walking; remembered here).
 * 🪽 Bay (owner 24/10 "bay được k nhỉ, sẽ có tăng tốc độ như xe ấy, nếu sử dụng cánh thì k lái xe được"): wearing wings,
 * "🪽 Bay / 🪽 Hạ cánh" under it: the player hovers over the street (a bob with the wings' beat, their shadow on the
 * ground), the wings drawn apart at their full stroke, faster by the tier (./ride.js flySpeedNow); never on the vehicle
 * (its toggle lands first, taking off sends it home). No parking at a door: they fly to it.
 * 🪽 In the air nothing is in the way (owner 24/10 "bay bị mắc nhà ... bay cứ vướng vướng"): a straight line over the shops
 * and roofs to the tap, the door or the keys' step, kept inside the town (town-place.js airRoute); Hạ cánh over a shop
 * walks them down to the nearest street point, and the rest of the way goes on over the streets (groundRoute). */
import {plan,nearest,walkable,airRoute,groundRoute,itemAt,districtAt,back,marks,LANDMARKS,SIGNS} from '../scenes/town-place.js';
import {figure,paintPlayer,CANVAS,lookOf,myPairs,wingOfState} from './look.js';
import {drawWings,drawMotes,wingBitmap,flapStep,wingScale,flyMotion,flyShadow,FLY_WING,FLY_LEAN,CLASSIC_WING,WING_BOX} from './wings-art.js';   // 🪽 Bay
import {refURL,refBox} from './pet-art.js';   // 🐾 the pet walking with you (game/pets.py walk_ref)
import {t as tr,language} from './i18n.js';
import {lightAt} from './dayclock.js';
import {escapeHTML as esc,icon} from '../icons.js';
import {choice,next as nextRide,canRide,label as rideLabel,speedOf,drawRide,rider,steer,halfOf,loadSpouse,canFly,flying,toggleFly,flyLabel,flySpeedNow,FLY_TOAST} from './ride.js';
// 👶 "Bế bé đi chơi": the baby in your arms (v4/baby.js), a toggle under the ride's
import * as BB from './baby.js';
import {townBirds} from './town-birds.js';   // 🐦 a flock now and then (no frame loop)
import {loadTown,onTown,peekTown,stagesOf} from './town-projects-data.js';   // 🏗️ each project lot's stage

const RM=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)');
const still=()=>Boolean(RM?.matches)||document.documentElement.classList.contains('reduce-motion')||document.body.classList.contains('reduce-motion');
const ME=.5;                  // the character (about 140 units tall) in town pixels
const SPEED=270,MAX_WALK=2.4; // town pixels a second; no walk takes longer than MAX_WALK seconds
const IDLE_MS=84,MAX_PX=7e6;  // the glow's frame gap; the cached town bitmap's pixel budget
const LM_COLOR={bank:'#8d7b4c',garage:'#5a6f88',gadgets:'#6f8fb8',pets:'#d98a6a',quan:'#9a6a43',spa:'#b07aa8',rap:'#6c4f8f',congduc:'#b8862f',style:'#c0607a',fair:'#c8423a',board:'#a8743f',walk:'#5f8f3e',house:'#d9573b',quay:'#e0892b',square:'#418d94',karaoke:'#9b4f96',ghepba:'#3f8f7a',travel:'#4f8fd1',duhoc:'#3f7fb0',hanghieu:'#b8862f',mtq:'#c8423a',dinhthu:'#3f9a78',daugia:'#8a5a2b',danhthang:'#4f8a5b',
  tp_cong_vien:'#5f8f3e',tp_rap_phim:'#6c4f8f',tp_thu_vien:'#a4543d',tp_san_van_dong:'#3f8f5a',tp_cau_ra_dao:'#418d94',tp_benh_vien:'#c0392b'};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');

const W={env:null,h:null,el:null,cv:null,c:null,where:null,whereText:'',card:null,pl:null,bg:null,bgKey:'',bs:1,k:1,cw:0,ch:0,dpr:1,
  cam:{x:0,y:0},free:false,me:null,raf:0,last:0,time:0,drawn:0,down:null,at:'',lastCur:undefined,look:null,st:null,stKey:'',
  sprite:null,spriteKey:'',ok:null,hooked:false,frames:[],zoom:1,destination:'',destinationKey:'',
  ride:null,rideKey:'',rv:rider(),park:null,legs:[],leg:null,btn:null,fly:false,fb:null};

/* ------------------------------------------------------------ what the town shows */
const S=()=>W.env.api.state;
const meta=id=>W.env.api.content.catalogue.find(m=>m.id===id)||{id,short:id,place:id};
/** 📱 Perk 'recent' of the phone in use (game/gadgets.py): the last 3 places picked in Chỉ đường, on top. This device only. */
const RECENT_KEY='mnl.townRecent';
const recentOn=()=>Boolean(S()?.journey?.gadgets?.perks?.includes?.('recent'));
function recent(){try{const r=JSON.parse(localStorage.getItem(RECENT_KEY)||'[]');return Array.isArray(r)?r.filter(x=>typeof x==='string').slice(0,3):[];}catch{return [];}}
function remember(key){if(!recentOn())return;try{localStorage.setItem(RECENT_KEY,JSON.stringify([key,...recent().filter(x=>x!==key)].slice(0,3)));}catch{/* storage blocked */}W.destinationKey=null;}
/** Only destinations this save can visit are offered by the route chooser. */
export function destinations(items,state){
  return items.flatMap(it=>{const s=state(it);return s.off||s.lock?[]:[{key:it.key,label:`${s.emoji||'📍'} ${s.name}`}];});
}
/** Join the current leg and queued road legs; no straight line through buildings. */
export function remainingPath(me,legs){
  if(!me?.path?.length)return [];
  return [[me.x,me.y],...me.path,...legs.flatMap(g=>(g.preview||[]).slice(1))];
}
/** Every career this save has, in catalogue order. */
const careerIds=()=>W.env.api.content.catalogue.map(m=>m.id).filter(id=>S().careers[id]);
const CH1=()=>(W.env.api.content.journey?.chapters?.[0]?.unlocks||[]);
function landmarkOn(lm){
  const s=S(),J=s.journey||{},api=W.env.api;
  switch(lm){
    case'garage':return !!(J.story&&J.garage);
    case'gadgets':return !!(J.story&&J.gadgets);   // 📱 v4/gadgets.js
    case'pets':return !!(J.story&&J.pets);   // 🐾 v4/pets.js
    case'quan':case'spa':case'rap':case'congduc':case'style':return !!(J.story&&J.spend);   // ☕ v4/spend.js
    case'travel':return !!(J.story&&(J.travel||J.lux));   // ✈️ v4/travel.js (#464)
    case'hanghieu':case'mtq':case'dinhthu':return !!(J.story&&J.lux);   // 🛍️ v4/lux.js
    case'duhoc':return !!(J.story&&J.abroad);   // ✈️🌏 v4/abroad.js
    case'daugia':case'danhthang':return !!(J.story&&api.content.journey?.auction);   // 🔨 v4/auction.js
    case'fair':return !!s.fair?.show;
    case'walk':{const lv=W.env.live?.();return !!(lv?.flags?.street&&lv.welcomed);}
    case'karaoke':{const lv=W.env.live?.();return !!(lv?.flags?.kara&&lv.welcomed);}   // 🎤 v4/karaoke.js
    case'ghepba':return !!(J.story&&J.tile);   // 🧩 v4/tile-match.js
    case'house':return !!J.story;
    case'quay':return !!(J.story&&api.content.journey?.quay);
    case'square':return !!(s.current&&api.content.experiences?.town);
    case'tp_cong_vien':case'tp_rap_phim':case'tp_thu_vien':case'tp_san_van_dong':case'tp_cau_ra_dao':case'tp_benh_vien':return !!J.story;   // 🏗️ v4/town-projects.js
    default:return true;   // bank, board: always in the menu too
  }
}
/** Who is new (nothing started yet): the lit shops, the arrow, the one hint line. */
function guide(){
  const s=S(),J=s.journey||{},open=new Set(J.story?J.unlocked||[]:Object.keys(s.careers));
  const fresh=!!J.story&&!Object.values(s.careers).some(c=>c?.started);
  const lit=fresh?CH1().filter(id=>open.has(id)&&s.careers[id]):J.suggested&&J.suggested!==s.current&&open.has(J.suggested)?[J.suggested]:[];
  const arrow=fresh?(lit.includes(W.h.FIRST_JOB)?W.h.FIRST_JOB:lit[0]||null):null;
  return {fresh,lit,arrow,open};
}
/** Each building's look: colour, sign, and its state (locked, current, ×3, lit, closed for now). */
function stateFn(){
  const s=S(),J=s.journey||{},g=guide(),x3=new Set(s.x3?.today||[]),lit=new Set(g.lit);
  const lots=Object.fromEntries(stagesOf(peekTown()).map(x=>['tp_'+x.id,x]));
  return it=>{
    if(it.lm){const L=LANDMARKS[it.lm],lot=lots[it.lm];return {color:LM_COLOR[it.lm],emoji:L.emoji,name:L.name,off:!landmarkOn(it.lm),...(lot?{stage:lot.stage,pct:lot.pct,left:lot.left}:{})};}
    const m=meta(it.id),sg=SIGNS[it.id]||[W.h.emojiOf(m),m.short||m.place||it.id];
    return {color:/^#[0-9a-f]{6}/i.test(m.color||'')?m.color:'#c4a27a',emoji:sg[0],name:sg[1],lock:!g.open.has(it.id),cur:it.id===s.current,
      x3:x3.has(it.id),glow:lit.has(it.id),paused:!!J.places?.[it.id]?.paused};
  };
}
/** The time of day of the place the player works at (its own clock), else none: the town stays bright. */
function tint(){
  const s=S(),dc=s.current&&s.careers[s.current]?.day_clock;
  if(!dc||!Number.isFinite(dc.minute))return null;
  const m=Math.round(dc.minute/20)*20;return {...lightAt(m),m};
}

/* ------------------------------------------------------------ the page */
/** The page: a slim top bar (where, ×3, Danh sách, close), a new player's one hint line, the stage's slot. */
export function townHTML(env,h){
  W.env=env;W.h=h;
  const s=env.api.state,J=s.journey||{},g=guide();
  const x3=s.x3?.today?.length?`<button type="button" class="tw-chip tw-x3" data-action="x3Week" aria-label="${esc(`Hôm nay lời x${s.x3.x}`)}">🔥 x${esc(s.x3.x)}</button>`:'';
  const close=s.current?`<button type="button" class="icon-btn tw-close" data-action="close" aria-label="Đóng">${icon('x',20)}</button>`:'';
  const day=!J.story?'':typeof document!=='undefined'&&document.documentElement?.hasAttribute?.('data-clean')?`<small aria-label="Ngày sống ${fmt(J.life_day)}">📅 ${fmt(J.life_day)}</small>`:`<small>Ngày sống ${fmt(J.life_day)}</small>`;
  // Clean layout (docs/UI_KIT.md, wave 5): the same pointer in five words, under the goal card that already names the job.
  const slim=typeof document!=='undefined'&&!!document.documentElement?.hasAttribute?.('data-clean');
  const hint=g.fresh?`<p class="tw-hint" role="status"><span aria-hidden="true">👉</span> ${slim?'Vào tiệm sáng đèn':'Đi tới một tiệm đang sáng để làm'}</p>`:'';
  const goals=J.story&&h.chapterCard?`<div class="tw-goals">${h.chapterCard(env,{compact:true})}</div>`:'';
  // 🎓 F#267 (owner 08/10: "phần thi chứng chỉ đưa ra ngoài cho rõ"): one tap from the town to the certificate centre,
  // with a dot while an exam is open or a workplace you work at has a certificate you lack.
  const dot=J.story&&h.certBadge?.(env.api);
  const cert=J.story&&env.api.content?.journey?.certs?`<button type="button" class="tw-chip tw-cert${dot?' due':''}" data-action="jrCerts" aria-label="${esc(dot?'Thi chứng chỉ · có việc cần làm':'Thi chứng chỉ')}">🎓<span class="tw-word"> Chứng chỉ</span>${dot?'<i class="dot" aria-hidden="true"></i>':''}</button>`:'';
  // 🏮 The fair (owner 08/10: "để luôn ở ngoài"): one tap from the town while it is on (a dot until played today) or
  // about to open ("sắp mở"); the 🏮 gate on Phố hàng rong stays too.
  const fr=s.fair,fairOn=J.story&&fr?.show&&!fr.over;
  const fair=fairOn?`<button type="button" class="tw-chip tw-fair${fr.open&&!fr.played?' due':''}" data-action="fair" aria-label="${esc(fr.soon?'Chợ đen sắp mở':'Vào chợ đen')}">🕶️<span class="tw-word"> Chợ đen${fr.soon?' <small>sắp mở</small>':''}</span>${fr.open&&!fr.played?'<i class="dot" aria-hidden="true"></i>':''}</button>`:'';
  // owner 19/10 "bấm đổi nghề nó có bên trên xấu quá, xóa rồi gọn lại": one row on a phone (🏝️ Ra đảo stays in the menu
  // and the rail; Chợ đen and Chứng chỉ show their emoji only on a narrow screen), the ✕ at the right end
  return `<div class="tw-home"><header class="tw-top home-top"><div class="tw-title"><h2>Khu phố</h2>${day}</div>${x3}${fair}${cert}
    <button type="button" class="tw-chip tw-find" data-action="jrPickFind" aria-label="Tìm nghề">🔎<span class="tw-word"> Tìm nghề</span></button><button type="button" class="tw-chip tw-list" data-action="jrList">📋 Danh sách</button>${close}</header>${goals}${hint}
    <div class="tw-slot" data-tw-slot><i class="tw-end" hidden></i></div></div>`;
}
/** Can this browser draw it? (else the list shows, as before) */
export function townOK(){
  if(W.ok===null){try{W.ok=!!document.createElement('canvas').getContext('2d')&&typeof ResizeObserver==='function';}catch{W.ok=false;}}
  return W.ok;
}

/* ------------------------------------------------------------ the stage */
function build(){
  const el=document.createElement('div');el.className='tw-stage';el.setAttribute('data-morph-keep','');
  el.innerHTML=`<canvas class="tw-canvas" tabindex="0" role="img"></canvas>
    <form class="tw-route-picker"><select aria-label="${esc(tr('Chọn điểm đến'))}"></select><button type="submit">${esc(tr('Chỉ đường'))}</button></form>
    <div class="tw-where" aria-live="polite"></div><button type="button" class="rd-toggle" hidden></button><button type="button" class="fl-toggle" hidden></button><button type="button" class="bb-toggle" hidden></button>
    <div class="tw-map-tools" role="group" aria-label="${esc(tr('Độ phóng bản đồ'))}"><button type="button" data-tw-zoom="out" aria-label="${esc(tr('Thu nhỏ bản đồ'))}">−</button><output>100%</output><button type="button" data-tw-zoom="in" aria-label="${esc(tr('Phóng to bản đồ'))}">+</button><button type="button" data-tw-zoom="me" aria-label="${esc(tr('Về vị trí của bạn'))}">◎</button></div>
    <div class="tw-card" hidden></div>`;
  W.el=el;W.cv=el.querySelector('canvas');W.c=W.cv.getContext('2d');W.where=el.querySelector('.tw-where');W.card=el.querySelector('.tw-card');
  W.btn=el.querySelector('.rd-toggle');W.btn.addEventListener('click',()=>{const was=flying(S());nextRide(S(),W.env.api.content);setRide();setFly();setBaby();if(was&&W.ride)W.env?.toast?.(tr(FLY_TOAST.land));});
  W.fb=el.querySelector('.fl-toggle');W.fb.addEventListener('click',()=>{const say=toggleFly(S(),W.env.api.content);setRide();setFly();setBaby();if(say)W.env?.toast?.(tr(say));});   // 🪽
  W.bb=el.querySelector('.bb-toggle');W.bb.addEventListener('click',()=>{BB.nextCarry(S());setRide();setFly();setBaby();});   // 👶
  el.querySelector('.tw-route-picker').addEventListener('submit',e=>{
    e.preventDefault();const key=el.querySelector('.tw-route-picker select').value,it=W.pl.items.find(it=>it.key===key);remember(key);
    if(it&&!W.st(it).off&&!W.st(it).lock)goItem(it,true);
  });
  for(const button of el.querySelectorAll('[data-tw-zoom]'))button.addEventListener('click',()=>{
    const action=button.dataset.twZoom;
    if(action!=='me')W.zoom=Math.max(.65,Math.min(2,W.zoom*(action==='in'?1.25:1/1.25)));
    W.free=false;size();
  });
  W.cv.setAttribute('aria-label',tr('Khu phố: chạm vào một nơi để đi tới. Mũi tên để đi, Enter để vào.'));
  W.cv.addEventListener('pointerdown',down);W.cv.addEventListener('pointermove',move);W.cv.addEventListener('pointerup',up);W.cv.addEventListener('pointercancel',()=>{W.down=null;});
  W.cv.addEventListener('wheel',wheel,{passive:false});
  W.cv.addEventListener('keydown',onKey);
  townBirds(el,visible);
  W.card.addEventListener('click',e=>{if(e.target.closest('[data-tw-x]'))hide();});
  el.addEventListener('keydown',e=>{if(e.key==='Escape'&&!W.card.hidden){e.preventDefault();e.stopPropagation();hide();W.cv.focus({preventScroll:true});}});
  let sizing=0;new ResizeObserver(()=>{cancelAnimationFrame(sizing);sizing=requestAnimationFrame(size);}).observe(el);
}
/** After each render of the home sheet: the stage into its slot, the town brought up to date. */
export function townMount(env,h){
  W.env=env;W.h=h;
  // The sheet renders before it opens (app.js openSheet): mount into the slot either way, and size/animate once the
  // dialog is up (the next frame).
  const slot=document.querySelector('#sheet [data-tw-slot]');
  if(!slot)return;
  if(!W.el)build();
  if(!W.hooked){W.hooked=true;env.api.addEventListener('state',()=>{if(visible())refresh();});onTown(()=>{if(visible())refresh();});BB.onChange(()=>{if(visible()){setRide();setFly();setBaby();}});}
  if(W.el.parentNode!==slot){slot.prepend(W.el);W.cw=0;}
  refresh();
  if(!W.cw)size();
  if(!visible())requestAnimationFrame(()=>{if(visible()){size();kick();}});
}
const visible=()=>!!W.el?.isConnected&&!!W.el.closest('dialog[open]');
/** The save changed (or the stage came back): a new plan when the careers changed, the player at the door of the
 * place they work at when that changed (back from work: at its door), the town repainted when anything shows
 * differently. */
function refresh(){
  const ids=careerIds(),cats=Object.fromEntries(ids.map(id=>[id,meta(id).category||'']));
  W.pl=plan(ids,cats,landmarkOn('karaoke')?[]:['lm:karaoke']);   // 🎤 not built while the live service has it off
  const st=stateFn();W.st=st;
  const choices=destinations(W.pl.items,st),rec=recentOn()?recent().map(k=>choices.find(c=>c.key===k)).filter(Boolean):[],key=JSON.stringify([choices,rec]),select=W.el.querySelector('.tw-route-picker select');
  if(key!==W.destinationKey){
    const selected=select.value;W.destinationKey=key;
    const opts=list=>list.map(it=>`<option value="${esc(it.key)}">${esc(tr(it.label))}</option>`).join('');
    select.innerHTML=rec.length?`<optgroup label="📱 Vừa đi">${opts(rec)}</optgroup><optgroup label="${esc(tr('Tất cả'))}">${opts(choices)}</optgroup>`:opts(choices);
    if(choices.some(it=>it.key===selected))select.value=selected;
    select.disabled=!choices.length;W.el.querySelector('.tw-route-picker button').disabled=!choices.length;
  }
  const t=tint();W.tintNow=t;
  W.stKey=JSON.stringify([W.pl.items.map(it=>{const s=st(it);return [s.lock,s.cur,s.x3,s.glow,s.paused,s.off,s.name,s.stage,s.pct,s.left];}),t?.m??-1,language()]);
  if(S().journey?.story)loadTown(W.env.api);   // 🏗️ at most a request a minute; a new page repaints the lots (townMount)
  const cur=S().current||null;
  setRide(false);loadSpouse(W.env.api).then(()=>setRide(false));   // 💑 the spouse's vehicles too (cached a minute)
  setFly();
  setBaby();BB.loadFamily(W.env.api).then(()=>{if(visible())BB.greet(W.env);});   // 👶 the shared child too (cached a minute)
  if(!W.me||cur!==W.lastCur){W.lastCur=cur;place(spawn());W.free=false;snap();hide();parkAtDoor();}
  else if(W.at){const it=W.pl.items.find(x=>x.key===W.at);if(it&&!W.card.hidden)showCard(it,false);}
  W.drawn=0;kick();
}
function doorOf(key){return W.pl.items.find(it=>it.key===key);}
/** Where the player comes in: the door of the place they work at, a new player just left of the first lit shop, else
 * the suggested place's door, else home. */
function spawn(){
  const s=S(),g=guide(),cur=s.current&&doorOf(s.current);
  if(cur)return cur.stand;
  if(g.arrow){const it=doorOf(g.arrow);if(it)return [it.stand[0]-150,it.stand[1]];}
  const sug=s.journey?.suggested&&doorOf(s.journey.suggested);if(sug)return sug.stand;
  return (doorOf('lm:house')||W.pl.items[0]).stand;
}
function place(p){const q=nearest(W.pl,p);W.me={x:q[0],y:q[1],path:null,step:0,len:0};W.legs=[];W.leg=null;W.park=null;W.destination='';}

/* ---- 🛵 riding (./ride.js) ---- */
/** The vehicle ridden now (the toggle, the save), the button brought up to date. `fresh`: a tap on the toggle (or a
 * change in the garage) while on the map: hop on where the player stands, or off (the vehicle goes home). */
function setRide(fresh=true){
  const v=choice(S(),W.env.api.content),key=v?`${v.key}|${v.hex}|${v.plate}`:'';
  if(W.btn){const own=canRide(S(),W.env.api.content);W.btn.hidden=!own;
    if(own){const t=tr(rideLabel(v));if(W.btn.textContent!==t)W.btn.textContent=t;W.btn.setAttribute('aria-pressed',String(!!v));W.btn.title=tr(v?v.name:'Đi bộ');}}
  if(key===W.rideKey)return;
  const had=W.ride;W.ride=v;W.rideKey=key;
  if(!v||!had||fresh)W.park=null;
  W.drawn=0;kick();
}
const riding=()=>!!W.ride&&!W.park;
/** 🪽 The fly toggle (only wearing wings) and the flight itself (never on the vehicle: ./ride.js). */
function setFly(){
  const can=canFly(S()),on=can&&flying(S())&&!W.ride;
  if(W.fb){W.fb.hidden=!can;if(can){const t=tr(flyLabel(on));if(W.fb.textContent!==t)W.fb.textContent=t;W.fb.setAttribute('aria-pressed',String(on));W.fb.title=tr(on?'Đang bay: chạm để hạ cánh':'Bay nhanh như đi xe');}}
  if(on===W.fly)return;
  W.fly=on;if(on)W.park=null;else landNow();W.drawn=0;kick();
}
/** 🪽 Hạ cánh: the rest of the way on foot from where they are (over a shop: down to the street first), or, standing
 * over a roof, the few steps down to the nearest street point. */
function landNow(){
  const m=W.me;if(!m||!W.pl)return;
  if(m.path?.length&&W.leg){W.legs.unshift({...W.leg,fly:false});W.leg=null;m.path=null;nextLeg();return;}
  if(!walkable(W.pl,[m.x,m.y])){W.legs=[{to:nearest(W.pl,[m.x,m.y])}];W.leg=null;nextLeg();}
}
/** One leg's path: straight in the air, else over the floor (from over a roof: down to the street first). */
const legPath=(g,from)=>g.fly&&W.fly?airRoute(W.pl,from,g.to):groundRoute(W.pl,from,g.to);
/** 👶 The baby toggle (only with a baby at home) and the sprite with the baby in your arms. */
function setBaby(){
  if(!W.bb)return;
  const any=BB.hasBaby(S()),b=BB.carried(S());W.bb.hidden=!any;
  if(any){BB.css();const t=tr(BB.label(b));if(W.bb.textContent!==t)W.bb.textContent=t;W.bb.setAttribute('aria-pressed',String(!!b));}
  W.drawn=0;kick();
}
/** Where the vehicle waits by a door: beside the stand point, on the side the player came from. */
function parkSpot(it,fromX){
  const side=fromX<=it.stand[0]?-1:1,off=halfOf(W.ride)*ME+16;
  return nearest(W.pl,[it.stand[0]+side*off,it.stand[1]+8]);
}
/** Just placed at a door (back from work, a new visit): the vehicle parked beside it, the player on foot. */
function parkAtDoor(){
  if(!W.ride||!W.me)return;
  const it=W.pl.items.find(x=>Math.hypot(x.stand[0]-W.me.x,x.stand[1]-W.me.y)<2);
  if(!it)return;
  const [x,y]=parkSpot(it,it.stand[0]-1);W.park={x,y,key:it.key,face:1};W.rv=rider(1);
}

/* ---- size and camera ---- */
function size(){
  if(!W.el?.isConnected)return;
  const r=W.el.getBoundingClientRect(),cw=Math.max(1,r.width),ch=Math.max(1,r.height);
  W.dpr=Math.min(2,globalThis.devicePixelRatio||1);W.cw=cw;W.ch=ch;
  const w=Math.round(cw*W.dpr),h=Math.round(ch*W.dpr);if(W.cv.width!==w)W.cv.width=w;if(W.cv.height!==h)W.cv.height=h;
  W.k=Math.max(.6,Math.min(1,cw/560,ch/600))*W.zoom;
  W.el.querySelector('.tw-map-tools output').textContent=Math.round(W.zoom*100)+'%';
  W.el.querySelector('[data-tw-zoom="out"]').disabled=W.zoom<=.65;
  W.el.querySelector('[data-tw-zoom="in"]').disabled=W.zoom>=2;
  if(W.me)snap();
  W.drawn=0;draw();
}
const view=()=>[W.cw/W.k,W.ch/W.k];
/** Where the camera wants to be: the player a little below the middle, inside the town (centred when it is smaller). */
function camGoal(){
  const [vw,vh]=view(),{W:TW,H:TH}=W.pl,fit=(v,len,full)=>full<=len?(full-len)/2:Math.max(0,Math.min(full-len,v));
  return [fit(W.me.x-vw/2,vw,TW),fit(W.me.y-vh*.58,vh,TH)];
}
function clampCam(){const [vw,vh]=view(),{W:TW,H:TH}=W.pl,f=(v,len,full)=>full<=len?(full-len)/2:Math.max(0,Math.min(full-len,v));W.cam.x=f(W.cam.x,vw,TW);W.cam.y=f(W.cam.y,vh,TH);}
function snap(){if(!W.me||!W.pl)return;const [x,y]=camGoal();W.cam.x=x;W.cam.y=y;}
const toWorld=(cx,cy)=>{const r=W.cv.getBoundingClientRect();return [W.cam.x+(cx-r.left)/W.k,W.cam.y+(cy-r.top)/W.k];};

/* ---- input: tap to walk, drag to look around, wheel on a desktop, arrows / WASD ---- */
function down(e){W.down={x:e.clientX,y:e.clientY,t:performance.now(),cx:W.cam.x,cy:W.cam.y,pan:false,id:e.pointerId};}
function move(e){
  const d=W.down;if(!d||d.id!==e.pointerId)return;
  const dx=e.clientX-d.x,dy=e.clientY-d.y;
  if(!d.pan&&Math.hypot(dx,dy)>12){d.pan=true;try{W.cv.setPointerCapture(e.pointerId);}catch{/* gone */}}
  if(d.pan){W.free=true;W.cam.x=d.cx-dx/W.k;W.cam.y=d.cy-dy/W.k;clampCam();W.drawn=0;kick();}
}
function up(e){
  const d=W.down;W.down=null;if(!d||d.pan||performance.now()-d.t>900)return;
  tapAt(e.clientX,e.clientY);
}
function wheel(e){if(e.ctrlKey)return;e.preventDefault();W.free=true;W.cam.x+=(e.shiftKey?e.deltaY:e.deltaX)/W.k;if(!e.shiftKey)W.cam.y+=e.deltaY/W.k;clampCam();W.drawn=0;kick();}
function tapAt(cx,cy){
  const p=toWorld(cx,cy),it=itemAt(W.pl,p);
  if(it&&!W.st(it).off)goItem(it);else{hide();walkTo(p);}
}
function goItem(it,focus=false){hide();walkTo(it.stand,()=>showCard(it,focus),it);}
function onKey(e){
  const step={ArrowLeft:[-70,0],ArrowRight:[70,0],ArrowUp:[0,-60],ArrowDown:[0,60],a:[-70,0],d:[70,0],w:[0,-60],s:[0,60]}[e.key.length===1?e.key.toLowerCase():e.key];
  if(step){e.preventDefault();hide();walkTo([W.me.x+step[0],W.me.y+step[1]]);return;}
  if(e.key==='Enter'||e.key===' '){
    let best=null,bd=110;for(const it of W.pl.items){if(W.st(it).off)continue;const d=Math.hypot(it.stand[0]-W.me.x,it.stand[1]-W.me.y);if(d<bd){bd=d;best=it;}}
    if(best){e.preventDefault();goItem(best,true);}
  }
}

/* ---- walking (riding: back to the vehicle on foot, ride, park by the door, the last steps on foot) ---- */
function walkTo(p,then=null,door=null){
  W.free=false;W.arrive=then;W.destination=door?.key||'';
  if(door&&!W.st(door).off&&!W.st(door).lock)W.el.querySelector('.tw-route-picker select').value=door.key;
  const legs=[];
  if(!W.ride)legs.push({to:p,fly:W.fly});   // 🪽 a flyer goes straight to the door
  else if(door&&W.park?.key===door.key)legs.push({to:door.stand});   // parked at this very door
  else{
    if(W.park)legs.push({to:[W.park.x,W.park.y],mount:true});
    if(door){const from=W.park?W.park.x:W.me.x;legs.push({to:parkSpot(door,from),ride:true,park:door.key},{to:door.stand});}
    else legs.push({to:p,ride:true});
  }
  let from=[W.me.x,W.me.y];
  for(const g of legs){g.preview=legPath(g,from);if(g.preview?.length)from=g.preview.at(-1);}
  W.legs=legs;W.leg=null;
  if(still()){while(W.legs.length){const g=W.legs.shift(),path=legPath(g,[W.me.x,W.me.y]),end=path?path[path.length-1]:[W.me.x,W.me.y];W.me.x=end[0];W.me.y=end[1];legEnd(g);}
    W.me.path=null;snap();W.drawn=0;kick();arrived();return;}
  nextLeg();
}
/** The next leg of the walk (none left: arrived). */
function nextLeg(){
  for(;;){
    const g=W.legs.shift();W.leg=g||null;
    if(!g){arrived();return;}
    const path=legPath(g,[W.me.x,W.me.y]);
    let len=0;if(path)for(let i=1;i<path.length;i++)len+=Math.hypot(path[i][0]-path[i-1][0],path[i][1]-path[i-1][1]);
    if(!path||len<.5){legEnd(g);continue;}
    const fast=g.ride?speedOf(W.ride):g.fly&&W.fly?flySpeedNow(S()):1;   // 🪽 the wings' speed
    W.me.path=path.slice(1);W.me.len=Math.max(SPEED*fast,len/(fast>1?MAX_WALK/1.5:MAX_WALK));
    kick();return;
  }
}
/** What happens at the end of a leg: hop on the parked vehicle, or park it here and get off. */
function legEnd(g){
  if(g.mount&&W.park){W.rv=rider(W.park.face??W.rv.face);W.park=null;}
  if(g.park&&W.ride)W.park={x:W.me.x,y:W.me.y,key:g.park,face:W.rv.face};
}
function arrived(){const f=W.arrive;W.arrive=null;W.legs=[];W.leg=null;if(W.me)W.me.path=null;if(f)f();}

/* ---- the card at a door ---- */
const tag=(t,kind='')=>`<span class="tw-tag ${kind}">${t}</span>`;
const act=(label,action,data={},style='primary')=>`<button type="button" class="btn ${style} tw-go" data-action="${action}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}>${label}</button>`;
function cardHTML(it){
  const s=S(),J=s.journey||{},st=W.st(it),x=`<button type="button" class="tw-card-x" data-tw-x aria-label="Đóng">×</button>`;
  if(it.lm){const L=LANDMARKS[it.lm],soft=it.lm==='garage'&&!canRide(s,W.env.api.content)?'<small>Mua xe để chạy quanh phố</small>':projectNote(st);
    return `<span class="tw-card-ico" aria-hidden="true">${L.emoji}</span><div class="tw-card-text"><b>${esc(L.name)}</b>${soft}</div>${act(`${st.stage==='funding'?'Góp xây':'Vào'} ${icon('arrow',14)}`,L.action,L.data||{})}${x}`;}
  const m=meta(it.id),c=s.careers[it.id]||{},h=W.h;
  if(st.lock){const n=(W.env.api.content.journey?.unlock_chapter||{})[it.id],L=h.lockOf?.(W.env.api,it.id);
    // How it opens (feedback #140 "sao không mở tiệm được"; owner 23/10): the same reason as 🔎 Đổi nghề (career-pick.js lockOf).
    const how=L?.how||(n?(n===J.chapter+1?`Mở ở chương ${n}: làm xong việc cần làm của chương này trong 📋 Danh sách.`:`Mở ở chương ${n}. Đang ở chương ${J.chapter||1}.`):'');
    return `<span class="tw-card-ico locked" aria-hidden="true">${esc(st.emoji)}</span><div class="tw-card-text"><b>🔒 ${esc(m.place||m.short||st.name)}</b><small>${esc(how||(n===J.chapter+1?'Sắp mở':'Còn ở phía trước'))}</small></div>${L?.act==='accountingSchool'?act(`Đi học ${icon('arrow',14)}`,'accountingSchool',{},'cream'):n?act('📋 Việc cần làm','jrList',{},'cream'):''}${x}`;}
  const job=c.job||{},aj=h.acctPlace(W.env.api,it.id),tags=[],cur=it.id===s.current,ab=s.abandon?.preview;
  if(cur&&ab&&!ab.soft&&ab.career===it.id)tags.push(tag('⏳ Đang làm dở','amber'));
  if(st.x3)tags.push(tag(`🔥 Lời x${s.x3.x} hôm nay`,'hot'));
  if(cur&&c.promo?.rank>0&&c.promo.title)tags.push(tag(`🎖️ ${esc(c.promo.title)}`,'blue'));
  if(st.paused)tags.push(tag('⏸ Đang tạm đóng','amber'));
  if(job.status==='offer')tags.push(tag('💌 Có thư mời','blue'));
  else if(job.required&&job.status!=='hired')tags.push(tag('Cần xin việc','amber'));
  if(!c.started&&J.story&&(W.env.api.content.journey?.unlock_chapter||{})[it.id]===J.chapter&&J.chapter>1)tags.push(tag('Mới mở','green'));
  if(guide().arrow===it.id)tags.push(tag('Hợp người mới','green'));
  // ⏸ A place the player closed (Tạm đóng) still has its sign: say why "Vào làm" is not there (reopening is free since #oldcost).
  const soft=h.lockOf?.(W.env.api,it.id);   // 🔒 khai trừ, phỏng vấn lại, đang ở nước ngoài: you may go in, the work waits
  const why=aj&&!aj.ok?`<small class="tw-why">🔒 ${esc(aj.why)}</small>`:soft?.soft?`<small class="tw-why">${esc(soft.how||soft.t)}</small>`:st.paused?'<small class="tw-why">Bạn đã tạm đóng nơi này. Mở lại miễn phí rồi vào làm ngay.</small>':'';
  const button=aj&&!aj.ok?act(`Đi học ${icon('arrow',14)}`,'accountingSchool',{},'cream'):st.paused?act('Mở lại','jrReopen',{career:it.id,go:1},'primary'):
    act(`${cur&&c.started?'Vào tiếp':'Vào làm'} ${icon('arrow',14)}`,'choose',{career:it.id});
  return `<span class="tw-card-ico" aria-hidden="true">${esc(st.emoji)}</span><div class="tw-card-text"><b>${esc(m.place||m.short)}</b><small>${esc(m.short||'')}</small>${why}${tags.length?`<div class="tw-tags">${tags.join('')}</div>`:''}</div>${button}${x}`;
}
/** 🏗️ A project lot's stage, under its name on the card. */
function projectNote(st){
  if(!st.stage)return '';
  const text=st.stage==='funding'?`💰 Đang góp tiền xây · ${st.pct}%`:st.stage==='building'?`🚧 Đang xây · còn ${st.left} giờ`:st.stage==='done'?'🎉 Đã khánh thành':'🪧 Sắp xây';
  return `<small>${esc(text)}</small>`;
}
function showCard(it,focus=false){
  if(!W.card)return;
  W.at=it.key;W.card.innerHTML=cardHTML(it);W.card.style.setProperty('--tw-c',W.st(it).color||'#c4a27a');W.card.hidden=false;
  if(focus)W.card.querySelector('.tw-go,[data-tw-x]')?.focus({preventScroll:true});
  W.drawn=0;kick();
}
function hide(){if(W.card&&!W.card.hidden){W.card.hidden=true;W.card.innerHTML='';}W.at='';}

/* ---- frames ---- */
function kick(){if(!W.raf&&visible()){W.last=performance.now();W.raf=requestAnimationFrame(loop);}}
/* ---- 🐾 the pet that walks with you: trails a step behind, sits when you stop (an image of v4/pet-art.js, cached);
 * on the vehicle it rides along (góp ý #413: in the basket / on the back seat, ./ride.js) and hops off with you ---- */
const PET={img:new Map(),x:0,y:0,on:false,face:1,moving:false};
function petImg(pose){
  const ref=S()?.journey?.pets?.ref,cat=W.env?.api?.content?.journey?.pets;if(!ref||!cat)return null;
  const key=JSON.stringify([ref,pose]);let im=PET.img.get(key);
  if(!im){if(PET.img.size>6)PET.img.clear();const url=refURL(cat,ref,pose);if(!url)return null;im=new Image();im.onload=()=>{W.drawn=0;kick();};im.src=url;PET.img.set(key,im);}
  return im.complete&&im.naturalWidth?im:null;
}
function petStep(m,dt){
  if(!S()?.journey?.pets?.ref){PET.on=false;return false;}
  if(riding()){PET.x=m.x;PET.y=m.y;PET.on=true;PET.moving=false;return false;}   // riding along: off where you get off
  const tx=m.x-26*PET.face,ty=m.y+5;
  if(!PET.on){PET.x=tx;PET.y=ty;PET.on=true;}
  let ex=tx-PET.x,ey=ty-PET.y,d=Math.hypot(ex,ey);
  if(d>40){PET.x=tx-ex/d*40;PET.y=ty-ey/d*40;ex=tx-PET.x;ey=ty-PET.y;d=40;}   // never left far behind (a fast vehicle)
  if(d>.6){const k=1-Math.exp(-dt*(still()?30:7));PET.x+=ex*k;PET.y+=ey*k;PET.moving=d>3;return true;}
  PET.moving=false;return false;
}
function drawPet(c,world){
  if(!PET.on||riding())return;const pose=PET.moving?'walk':'sit',im=petImg(pose);if(!im)return;
  const ref=S()?.journey?.pets?.ref,B=refBox(W.env?.api?.content?.journey?.pets,ref,pose);   // 🐶 bigger dogs, 🏅 the aura's room
  world();const w=(pose==='walk'?46:40)*B.w/B.base*B.k,h=w*B.h/B.w,foot=B.foot;
  c.save();c.translate(PET.x,PET.y);if(PET.face<0)c.scale(-1,1);c.drawImage(im,-w/2,-h*foot,w,h);c.restore();
}
function animating(){return !still()&&!document.hidden&&(W.marks?.glow?.length||W.marks?.arrow||W.fly);}   // 🪽 hovering: the bob and the wings
function loop(now){
  W.raf=0;if(!visible()||!W.me)return;
  const dt=Math.min(.05,(now-W.last)/1000);W.last=now;W.time+=dt;
  const m=W.me;let busy=false;
  if(m.path?.length){
    const sp=Math.max(SPEED,m.len||0)*dt,[tx,ty]=m.path[0],dx=tx-m.x,dy=ty-m.y,d=Math.hypot(dx,dy),x0=m.x;busy=true;
    if(Math.abs(dx)>1)PET.face=dx>0?1:-1;
    if(d<=sp){m.x=tx;m.y=ty;m.path.shift();}else{m.x+=dx/d*sp;m.y+=dy/d*sp;}
    m.step+=dt*10;
    if(riding())steer(W.rv,m.x-x0,Math.min(d,sp)/ME,dt,still());
    if(!m.path.length){m.path=null;const g=W.leg;if(g){legEnd(g);nextLeg();}else arrived();}
  }
  else if(W.rv.turn<1){steer(W.rv,0,0,dt,still());busy=true;}
  if(petStep(m,dt))busy=true;   // 🐾
  if(!W.free){const [gx,gy]=camGoal(),k=1-Math.exp(-dt*7),ex=gx-W.cam.x,ey=gy-W.cam.y;
    if(Math.abs(ex)>.4||Math.abs(ey)>.4){W.cam.x+=ex*k;W.cam.y+=ey*k;busy=true;}else{W.cam.x=gx;W.cam.y=gy;}}
  const anim=animating();
  if(busy||!W.drawn||(anim&&now-W.drawn>=IDLE_MS)){const t0=performance.now();draw();W.drawn=now||1;W.frames.push(performance.now()-t0);if(W.frames.length>240)W.frames.shift();}
  if(busy||anim||!W.drawn)W.raf=requestAnimationFrame(loop);
}
function backdrop(){
  const {W:TW,H:TH}=W.pl,bs=Math.min(W.k*W.dpr,Math.sqrt(MAX_PX/(TW*TH)));
  const key=[W.pl.key,bs.toFixed(3),W.stKey].join('|');
  if(W.bg&&W.bgKey===key)return W.bg;
  const bg=W.bg||document.createElement('canvas');bg.width=Math.ceil(TW*bs);bg.height=Math.ceil(TH*bs);
  const c=bg.getContext('2d');c.setTransform(bs,0,0,bs,0,0);
  try{back(c,W.pl,W.st,{tint:W.tintNow});}catch(e){console.warn('town: backdrop',e);}
  W.bg=bg;W.bgKey=key;W.bs=bs;return bg;
}
/** The player as one small bitmap, made again only when the look or the zoom changes. */
function sprite(){
  const sc=ME*W.k*W.dpr,look=lookOf(S()),key=JSON.stringify([look,S().journey?.gender,sc.toFixed(3),S().journey?.gadgets?.hand?.color,BB.wire(S()),myPairs(),wingOfState(S())])+(W.fly?'|fly':'');   // 📱 the phone in hand · 👶 the baby in your arms · 🤝 the pairs worn · 🪽 the wings (flying: drawn apart)
  if(W.sprite&&W.spriteKey===key)return W.sprite;
  const wide=wingOfState(S())&&!W.fly,cv=W.sprite||document.createElement('canvas'),w=Math.ceil((wide?250:110)*sc),h=Math.ceil(170*sc);cv.width=w;cv.height=h;   // 🪽 room for the larger pair
  const c=cv.getContext('2d');c.setTransform(sc,0,0,sc,w/2,h-12*sc);
  try{const F=BB.withBaby(figure(S()),S());if(W.fly&&F?.L?.wg){const {wg:_,...L}=F.L;F.L=L;}paintPlayer(c,F,CANVAS);}catch{/* look not ready */}
  W.sprite=cv;W.spriteKey=key;W.spriteFoot=[w/2,h-12*sc];return cv;
}
function draw(){
  const c=W.c;if(!c||!W.cw||!W.me||!W.pl)return;
  const g=guide(),items=W.pl.items,find=id=>items.find(it=>it.id===id);
  W.marks={glow:g.lit.map(find).filter(Boolean),arrow:g.arrow&&find(g.arrow)};
  const bg=backdrop(),d=W.dpr,k=W.k,bs=W.bs,[vw,vh]=view();
  c.setTransform(1,0,0,1,0,0);c.fillStyle='#efe0c6';c.fillRect(0,0,W.cv.width,W.cv.height);
  // The visible slice of the cached town (cut to the bitmap: some browsers draw nothing for a source past its edge).
  const sx=Math.max(0,W.cam.x),sy=Math.max(0,W.cam.y),ex=Math.min(W.pl.W,W.cam.x+vw),ey=Math.min(W.pl.H,W.cam.y+vh);
  if(ex>sx&&ey>sy)c.drawImage(bg,sx*bs,sy*bs,(ex-sx)*bs,(ey-sy)*bs,(sx-W.cam.x)*k*d,(sy-W.cam.y)*k*d,(ex-sx)*k*d,(ey-sy)*k*d);
  c.setTransform(k*d,0,0,k*d,-W.cam.x*k*d,-W.cam.y*k*d);
  const trail=remainingPath(W.me,W.legs);
  if(trail.length>1){
    c.save();c.lineCap='round';c.lineJoin='round';c.beginPath();
    trail.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));
    c.strokeStyle='#fff9e8';c.lineWidth=9/k;c.stroke();c.strokeStyle='#167b75';c.lineWidth=5/k;c.stroke();
    const end=trail.at(-1);c.fillStyle='#167b75';c.strokeStyle='#fff9e8';c.lineWidth=3/k;
    c.beginPath();c.arc(end[0],end[1],8/k,0,Math.PI*2);c.fill();c.stroke();c.restore();
  }
  const inView=it=>it.x1>W.cam.x-20&&it.x0<W.cam.x+vw+20&&it.G>W.cam.y-20&&it.G-it.h<W.cam.y+vh+20;
  const near=W.at?items.find(it=>it.key===W.at):null;
  try{marks(c,W.pl,{t:W.time,reduced:still(),glow:W.marks.glow.filter(inView),arrow:W.marks.arrow&&inView(W.marks.arrow)?W.marks.arrow:null,near});}catch(e){console.warn('town: marks',e);}
  // The player: the cached sprite, a little hop while walking; on the vehicle (./ride.js), or beside it parked.
  const sp=sprite(),m=W.me,hop=m.path?.length&&!still()?Math.abs(Math.sin(m.step))*3:0,v=W.ride,world=()=>c.setTransform(k*d,0,0,k*d,-W.cam.x*k*d,-W.cam.y*k*d);
  const me=()=>{
    if(W.fly&&!riding()){flyer(c,sp,m,k,d,world);return;}   // 🪽
    if(riding()){world();if(W.figKey!==W.spriteKey){W.figKey=W.spriteKey;W.fig=figure(S());}const pet=PET.on?petImg('sit'):null;
      drawRide(c,{x:m.x,y:m.y,s:ME,px:k*d,F:W.fig,fkey:W.spriteKey,v,r:W.rv,pet,pkey:pet?JSON.stringify(S().journey.pets.ref):''});return;}
    c.setTransform(1,0,0,1,0,0);
    c.drawImage(sp,Math.round((m.x-W.cam.x)*k*d-W.spriteFoot[0]),Math.round((m.y-W.cam.y-hop)*k*d-W.spriteFoot[1]));};
  const pk=v&&W.park,parked=()=>{world();const f=pk.face??1;drawRide(c,{x:pk.x,y:pk.y,s:ME,px:k*d,v,r:{face:f,from:f,turn:1,ang:0}});};
  const behind=PET.on&&PET.y<=m.y;if(behind)drawPet(c,world);   // 🐾 behind or in front of you, by depth
  if(pk&&pk.y<m.y){parked();me();}else if(pk){me();parked();}else me();
  if(!behind)drawPet(c,world);
  // Where the view is, top left (written only when it changes: no layout per frame).
  const dist=districtAt(W.pl,[W.cam.x+vw/2,W.cam.y+vh*.58]),dest=W.destination&&doorOf(W.destination);
  const text=dest?`${W.me.path?.length?'➜': '📍'} ${tr(W.st(dest).name)}`:`${dist.emoji} ${tr(dist.name)}`;
  if(text!==W.whereText){W.whereText=text;W.where.textContent=text;}
}

/** 🪽 The player in flight (owner 24/10 "bay thì cho cánh to hơn nha, cánh to hơn người và người k cần di chuyển nữa"):
 * their shadow on the ground; no steps, no hop: the standing sprite hovers (wings-art.js flyMotion: a float with the beat,
 * slow and wide gliding, quicker on the way), leaning a little into the way they go; the wings FLY_WING times their
 * ground size behind it (a cached flap: wingBitmap, drawn at its own pixel size), the sparkles over it. */
const WBOX=WING_BOX.map(v=>v*CLASSIC_WING.s),FLY_STATE={};
function flyer(c,sp,m,k,d,world){
  const wg=wingOfState(S()),t=still()?null:W.time,fm=flyMotion(FLY_STATE,wg,t,!!m.path?.length),lift=fm.lift*ME,o=flyShadow(fm.lift,ME);
  world();c.fillStyle=`rgba(40,30,25,${o.a.toFixed(2)})`;c.beginPath();c.ellipse(m.x,m.y+1,o.rx,o.ry,0,0,Math.PI*2);c.fill();
  const [ax,ay]=CLASSIC_WING.at,wo={s:CLASSIC_WING.s,gap:CLASSIC_WING.gap,tall:CLASSIC_WING.tall,spread:CLASSIC_WING.spread},z=ME*FLY_WING;
  c.save();c.translate(m.x,m.y-lift);c.rotate(fm.lean*FLY_LEAN*(PET.face||1));   // the body and its wings lean together
  if(wg){c.save();c.translate(ax*ME,ay*ME);c.scale(z,z);drawWings(c,CANVAS,wg,0,0,{...wo,body:false,sparkle:false,t});
    const bm=wingBitmap(CANVAS,wg,t==null?0:flapStep(fm.flap),wo,WBOX,z*k*d,'town');if(bm)c.drawImage(bm.canvas,-bm.ox,-bm.oy,bm.w,bm.h);c.restore();}
  c.drawImage(sp,-W.spriteFoot[0]/(k*d),-W.spriteFoot[1]/(k*d),sp.width/(k*d),sp.height/(k*d));
  if(wg&&t!=null){c.save();c.translate(ax*ME,ay*ME);c.scale(z,z);drawMotes(c,CANVAS,wg,0,0,wingScale(wg,CLASSIC_WING.s),t,false);c.restore();}
  c.restore();
}

/* ---- test hooks (scratch browser checks) ---- */
globalThis.__townWalk={
  state:()=>({on:visible(),me:W.me&&[Math.round(W.me.x),Math.round(W.me.y)],walking:!!W.me?.path?.length,at:W.at,card:!!W.card&&!W.card.hidden,
    cam:[Math.round(W.cam.x),Math.round(W.cam.y)],k:W.k,zoom:W.zoom,route:remainingPath(W.me,W.legs),destination:W.destination,size:W.pl&&[W.pl.W,W.pl.H],items:W.pl?.items.length,where:W.whereText,
    lit:W.marks?.glow?.map(it=>it.key)||[],arrow:W.marks?.arrow?.key||null,
    ride:W.ride?.id||null,riding:riding(),park:W.park&&[Math.round(W.park.x),Math.round(W.park.y)],toggle:W.btn&&!W.btn.hidden?W.btn.textContent:null,
    fly:W.fly,flyToggle:W.fb&&!W.fb.hidden?W.fb.textContent:null}),
  toggle:()=>{W.btn?.click();return W.ride?.id||null;},
  /** Client point of a building's sign (null when it is off the view). */
  screen:key=>{const it=W.pl?.items.find(x=>x.key===key);if(!it||!W.cv)return null;const r=W.cv.getBoundingClientRect(),x=r.left+(it.cx-W.cam.x)*W.k,y=r.top+(it.G-it.h*.55-W.cam.y)*W.k;
    return x>r.left+4&&x<r.right-4&&y>r.top+4&&y<r.bottom-4?[x,y]:null;},
  go:key=>{const it=W.pl?.items.find(x=>x.key===key);if(it)goItem(it);return !!it;},
  frames:reset=>{const f=W.frames.slice();if(reset)W.frames.length=0;return f;},
};
