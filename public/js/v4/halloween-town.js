/** 🎃 The 2.5D town at Halloween (game/halloween.py, v4/halloween-data.js), from 26/10 to the end of the grace day:
 * - a dusk tint, a moon, a garland of pumpkin lanterns and, now and then, a few bats crossing the sky (a little ghost at the
 *   night of 31/10). One DOM layer over the canvas (the Phaser scene is never redrawn for it), decoration only: aria-hidden,
 *   no pointer events, nothing moves with reduced motion, hidden inside a workplace.
 * - 🎃 the pumpkin hunt on foot: reaching a signpost of the town ('place:<amenity>', iso-guide.js) asks the server once a day
 *   per place whether a pumpkin hides there (POST /api/halloween/walk); a find is a toast. The place opens as usual.
 * attachHalloweenTown(world,getEnv) is idempotent (iso-boot.js calls it when the season shows). */
import {stylesheet} from '../lazy.js';
import {hwNow,hwOpen,hwNight,vnDay} from './halloween-data.js';

const PLACES=new Set(['bank','temple','cinema','cafe','spa','karaoke','walk','date','wedding','auction','pets','garage','travel','board','rank','gadgets']);
const ASKED='mnl.hween.asked';
const RM=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)');
const still=()=>Boolean(RM?.matches)||document.documentElement.classList.contains('reduce-motion');
const BAT='<svg viewBox="0 0 28 12" width="24" height="11" aria-hidden="true"><path d="M14 4c-1-2-3-3-5-1-2-2-6-2-9 1 3 0 4 2 4 4 2-1 4-1 5 1 1-2 3-2 5-1 1-2 3-2 5-1 0-2 1-4 4-4-3-3-7-3-9-1-2-2-4-1-5 1z" fill="#1f1235"/></svg>';
const MOON='<svg class="hw-moon" viewBox="0 0 44 44" aria-hidden="true"><circle cx="22" cy="22" r="17" fill="#fde68a"/><circle cx="30" cy="16" r="15" fill="rgba(42,23,71,.92)"/></svg>';
const GHOST='<svg class="hw-ghost" viewBox="0 0 28 38" aria-hidden="true"><path d="M14 0c9 0 14 8 14 18v20l-5-4-4 4-5-4-5 4-4-4-5 4V18C0 8 5 0 14 0z" fill="#f5f3ff"/><circle cx="9" cy="16" r="2.4" fill="#2a1747"/><circle cx="19" cy="16" r="2.4" fill="#2a1747"/></svg>';
let layer=null,bats=null,flying=null,timer=0,mode='town',attached=new WeakSet(),getEnv=null;

function asked(){try{const v=JSON.parse(localStorage.getItem(ASKED)||'{}');return v&&v.day===vnDay()?v:{day:vnDay(),k:[]};}catch{return {day:vnDay(),k:[]};}}
function remember(v){try{localStorage.setItem(ASKED,JSON.stringify(v));}catch{/* storage blocked */}}

/** Show, refresh or hide the layer for the season's status and the scene's mode. */
export function paint(host=document.getElementById('stage')){
  const on=Boolean(hwNow())&&mode==='town';
  if(!on){if(layer)layer.hidden=true;return;}
  if(!layer){
    if(!host)return;
    stylesheet('/css/halloween.css');
    layer=document.createElement('div');layer.className='hw-town';layer.setAttribute('aria-hidden','true');
    layer.innerHTML=`<div class="hw-tint"></div>${MOON}<div class="hw-garland">${Array.from({length:9},(_,i)=>`<i style="--d:${[4,8,10,8,4,8,10,8,4][i]}"></i>`).join('')}</div>${GHOST}<div class="hw-bats" hidden>${BAT}${BAT}${BAT}</div>`;
    host.append(layer);bats=layer.querySelector('.hw-bats');
    [...bats.children].forEach((b,i)=>{b.style.left=[0,22,40][i]+'px';b.style.top=[0,10,-4][i]+'px';});
    later(5000);
  }
  layer.hidden=false;
  layer.classList.toggle('night',hwNight());
  layer.querySelector('.hw-ghost').style.display=hwNight()?'':'none';
}
function later(ms){clearTimeout(timer);timer=setTimeout(fly,ms);}
function fly(){
  if(!layer?.isConnected||layer.hidden||document.hidden||still()||typeof bats?.animate!=='function'){later(25000);return;}
  const w=layer.clientWidth,h=layer.clientHeight;if(w<200||h<200){later(25000);return;}
  const ltr=Math.random()<.5,y0=h*(.14+Math.random()*.22),y1=y0+(Math.random()-.5)*h*.2,from=ltr?-70:w+20,to=ltr?w+20:-70;
  bats.hidden=false;
  try{
    flying=bats.animate([{transform:`translate3d(${from}px,${y0}px,0) scaleX(${ltr?1:-1})`},{transform:`translate3d(${(from+to)/2}px,${y0-30}px,0) scaleX(${ltr?1:-1})`},{transform:`translate3d(${to}px,${y1}px,0) scaleX(${ltr?1:-1})`}],
      {duration:Math.max(5000,w*10),easing:'ease-in-out'});
    flying.onfinish=()=>{bats.hidden=true;flying=null;later((hwNight()?15000:30000)+Math.random()*30000);};
  }catch{bats.hidden=true;}
}

/** 🎃 A signpost reached: does a pumpkin hide here today? Once a day per place on this device; the place opens anyway. */
async function walk(place){
  const env=getEnv?.();if(!env?.api?.account||!hwOpen()||!PLACES.has(place))return;
  const a=asked();if(a.k.includes(place))return;
  a.k.push(place);remember(a);
  try{
    const r=await env.api.post('/api/halloween/walk',{place});
    if(r?.found){env.toast?.(r.message||'🎃 Bạn tìm thấy một quả bí ngô!','good');document.dispatchEvent(new Event('mnl:hween-candy'));}
  }catch{/* the riddle in the sheet still works */}
}

export function attachHalloweenTown(world,envFn){
  getEnv=typeof envFn==='function'?envFn:()=>envFn;
  if(!world||attached.has(world))return;
  attached.add(world);
  const previous=world.onInteract;
  if(typeof previous==='function')world.onInteract=id=>{if(typeof id==='string'&&id.startsWith('place:'))void walk(id.slice(6));previous(id);};
  mode=world.mode||'town';
  document.addEventListener('mnl:iso-mode',e=>{mode=e.detail?.mode||mode;paint();});
  document.addEventListener('mnl:hween',()=>paint());
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)paint();});
  setInterval(()=>paint(),60000);   // the night begins, the season ends
  paint();
}
