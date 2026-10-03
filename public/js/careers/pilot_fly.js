/** ✈️ Tự bay — the pilot's cockpit, first person (career pilot: ./pilot.js; server: game/careers/pilot.py).
 * Out of the windscreen, drawn on one canvas with no library: the sky and the ground split at the horizon, the
 * runway in perspective with its lights and the PAPI (2 white 2 red is on the glide path), fields, sea, hills or
 * the city around it, clouds, a storm cell, rain on the glass and the wipers, the city lights at night. Below,
 * the panel: attitude with the flight director's magenta bars, the speed, altitude and heading tapes.
 * The player flies three short parts; the autopilot does the rest as a time-lapse:
 *   the take-off roll (throttle up, hold the centre line, pull up when the captain calls it) → pl_takeoff;
 *   a weather cell on the track when the hop has one (bank around it) → pl_decide deviate / through / over;
 *   the approach and landing (the 1,000 ft and 200 ft gates, the flare) → pl_gate / pl_around with `flown`.
 * Other decisions (turbulence, a sick passenger, a storm over the field, the rain set-up) are the workbench's own
 * panels shown over the panel (opts.ask). The server judges everything; nothing here is money. No crash, no game
 * over: too low or off the runway, the captain takes the aircraft and goes around.
 * Controls: phones drag the yoke pad (or the windscreen) and the throttle; desktop ← → bank, ↑ ↓ pitch (↓ pulls
 * the nose up, as a yoke does), W / S throttle, G go around. The overlay lives in the job sheet next to its
 * content (renders never touch it) and closes itself when the hop is on the ground or the sheet goes. */
import {t as tr} from '../v4/i18n.js';

const KT=.514444,FT=.3048,D2R=Math.PI/180,G=9.81;
const LEN=1800,HALF=15,AIM=300,GS=3*D2R,DOT=.35*D2R,RWY_HDG=180;
const VREF=115,VR=110,A_T=3,K_D=3.9e-4,EYE=3.2,NEAR=.6;
const TIPS='mnl.plFlyTips',FD_KEY='mnl.plFd';
const clamp=(v,a,b)=>v<a?a:v>b?b:v,lerp=(a,b,k)=>a+(b-a)*k,sgn=v=>v<0?-1:1;
const RM=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)');
const still=()=>Boolean(RM?.matches)||document.documentElement.classList.contains('reduce-motion')||document.body.classList.contains('reduce-motion');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const store=(k,v)=>{try{if(v===undefined)return localStorage.getItem(k);localStorage.setItem(k,v);}catch{/* storage blocked */}return null;};
function rngOf(seed){let s=0;for(const ch of String(seed))s=(s*31+ch.charCodeAt(0))>>>0;return ()=>{s=(s+0x6D2B79F5)>>>0;let t=s;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return ((t^t>>>14)>>>0)/4294967296;};}

let okCanvas=null;
/** Can this browser draw the cockpit? (else the workbench stays on Bay nhanh) */
export function canFly(){
  if(okCanvas===null){try{okCanvas=!!document.createElement('canvas').getContext('2d')&&typeof requestAnimationFrame==='function'&&typeof ResizeObserver==='function';}catch{okCanvas=false;}}
  return okCanvas;
}

/* ================================================================ state */
const F={el:null,cv:null,c:null,dpr:1,W:0,H:0,L:null,x:null,t:null,tid:'',opts:{},phase:'',ph:{},raf:0,last:0,time:0,
  busy:false,say:'',sayUntil:0,sayKey:'',queue:[],tip:'',tipUntil:0,ask:'',hidden:false,seenCheck:0,fd:true,lite:false,
  stats:{n:0,sum:0,max:0,win:0,winN:0,slow:0,start:0},scene:null,wx:null,input:{pitch:0,roll:0,kp:0,kr:0,pad:null,thr:null},keys:new Set(),
  sprites:null,flash:0,drops:[],wiper:0,fallback:false};
const S={x:0,h:0,z:0,psi:0,th:0,ph:0,V:0,T:0,Tt:0,vs:0,ground:true,gear:true,ap:false,shake:0,tl:0};

export const isOpen=()=>Boolean(F.el&&F.tid);
export const flyingTask=()=>F.tid;

/** Open the cockpit for task `t` at its stage. opts: ask(t,x) → decision markup, fallback(why) → back to Bay nhanh,
 * done() → the hop is on the ground (the workbench shows the parking step). */
export function open(x,t,opts={}){
  if(!canFly()||!t)return false;
  F.opts=opts;F.x=x;F.t=t;
  if(F.tid!==t.id||!F.el){build();F.tid=t.id;F.phase='';}
  F.fd=store(FD_KEY)!=='0';
  start();
  return true;
}
/** The workbench's latest context and task (after each render, a few times a second). */
export function sync(x,t){
  if(!F.el)return;
  F.x=x;
  if(t&&t.id===F.tid)F.t=t;
  const d=x.room.data||{};
  if(d.desk?.ev||d.odd?.ev){close();return;}   // somebody needs an answer first: the workbench shows them
  const t2=F.t||{};
  if(!['start','cruise','approach'].includes(t2.stage)&&F.phase!=='rollout'){close();return;}
  const fits=F.phase==='ask'&&(F.ph.arrive?t2.stage==='approach':t2.stage==='cruise');
  const ask=F.opts.ask&&fits?F.opts.ask(t2,x):'';
  if(ask!==F.ask){F.ask=ask;const box=F.el.querySelector('.pl-fly-ask');box.innerHTML=ask;box.hidden=!ask;}
}
export function close(){
  cancelAnimationFrame(F.raf);F.raf=0;
  window.removeEventListener('keydown',onKey,true);window.removeEventListener('keyup',onKey,true);
  F.ro?.disconnect();F.ro=null;
  F.el?.remove();F.el=null;F.tid='';F.phase='';F.ask='';F.keys.clear();F.input.pad=null;
}

/* ================================================================ the overlay */
function build(){
  close();
  const el=document.createElement('div');
  el.className='pl-fly';el.setAttribute('role','application');el.setAttribute('aria-label',tr('Buồng lái'));
  el.innerHTML=`<canvas class="pl-fly-cv" aria-hidden="true"></canvas>
    <div class="pl-fly-top"><span class="pl-fly-phase"></span><button type="button" class="pl-fly-fd" aria-pressed="true">${esc(tr('🟣 Gợi ý'))}</button><button type="button" class="pl-fly-fast">${esc(tr('⏩ Bay nhanh'))}</button></div>
    <p class="pl-fly-say" role="status" aria-live="polite" hidden></p>
    <p class="pl-fly-tip" hidden></p>
    <button type="button" class="pl-fly-ga" hidden>${esc(tr('↗️ BAY LẠI'))}</button>
    <div class="pl-fly-yoke" aria-label="${esc(tr('Cần lái: kéo để lái'))}"><span class="pl-fly-knob" aria-hidden="true"></span><small>${esc(tr('Kéo để lái'))}</small></div>
    <div class="pl-fly-thr" role="slider" aria-label="${esc(tr('Cần ga'))}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" tabindex="0"><span class="pl-fly-thr-knob" aria-hidden="true"></span><small>${esc(tr('Cần ga'))}</small></div>
    <p class="pl-fly-keys" hidden>${esc(tr('← → nghiêng · ↑ ↓ mũi (↓ kéo lên) · W/S ga · G bay lại'))}</p>
    <div class="pl-fly-ask career-job pl" hidden></div>`;
  (document.querySelector('#sheet[open]')||document.body).append(el);
  F.el=el;F.cv=el.querySelector('canvas');F.c=F.cv.getContext('2d',{alpha:false});
  if(!F.c){F.el.remove();F.el=null;okCanvas=false;return;}
  el.querySelector('.pl-fly-fast').addEventListener('click',()=>leave('manual'));
  el.querySelector('.pl-fly-fd').addEventListener('click',e=>{F.fd=!F.fd;store(FD_KEY,F.fd?'1':'0');e.currentTarget.setAttribute('aria-pressed',String(F.fd));});
  el.querySelector('.pl-fly-ga').addEventListener('click',()=>goAround('player'));
  yokeOn(el.querySelector('.pl-fly-yoke'));yokeOn(F.cv,true);throttleOn(el.querySelector('.pl-fly-thr'));
  el.addEventListener('wheel',e=>e.preventDefault(),{passive:false});
  el.querySelector('.pl-fly-fd').setAttribute('aria-pressed',String(store(FD_KEY)!=='0'));
  window.addEventListener('keydown',onKey,true);window.addEventListener('keyup',onKey,true);
  F.ro=new ResizeObserver(()=>size());F.ro.observe(el);
  size();
  F.stats={n:0,sum:0,max:0,win:0,winN:0,slow:0,start:performance.now()};F.lite=false;
  F.thrShown=-1;F.last=performance.now();F.raf=requestAnimationFrame(frame);
}
function size(){
  if(!F.el)return;
  const W=F.el.clientWidth||innerWidth,H=F.el.clientHeight||innerHeight;
  F.dpr=Math.min(F.lite?1:2,Math.max(1,devicePixelRatio||1));
  F.W=W;F.H=H;F.cv.width=Math.round(W*F.dpr);F.cv.height=Math.round(H*F.dpr);
  const tall=H>W*1.15;
  const vh=Math.round(tall?H*.47:H*.64),ph=Math.round(tall?clamp(H*.27,170,236):clamp(H-vh,150,300));
  F.L={tall,view:{x:0,y:0,w:W,h:vh},panel:{x:0,y:vh,w:W,h:ph},f:Math.max(W,vh*1.25)*.9};
  F.el.dataset.layout=tall?'tall':'wide';
  F.el.style.setProperty('--pl-fly-view',vh+'px');F.el.style.setProperty('--pl-fly-panel',(vh+ph)+'px');
  F.sprites=null;
}
/** Back to Bay nhanh: the player's switch, or the page could not keep up. */
function leave(why){
  const fn=F.opts.fallback;close();fn?.(why);
}

/* ================================================================ input */
function yokeOn(el,view=false){
  let id=null,ox=0,oy=0;
  const knob=F.el.querySelector('.pl-fly-knob'),R=view?90:58;
  const set=(dx,dy)=>{const kx=clamp(dx,-R,R),ky=clamp(dy,-R,R);F.input.pad=[kx/R,ky/R];if(knob)knob.style.transform=`translate(${kx*58/R}px,${ky*58/R}px)`;};
  el.addEventListener('pointerdown',e=>{if(id!==null||F.phase==='ask')return;id=e.pointerId;ox=e.clientX;oy=e.clientY;el.setPointerCapture?.(id);set(0,0);e.preventDefault();});
  el.addEventListener('pointermove',e=>{if(e.pointerId!==id)return;set(e.clientX-ox,e.clientY-oy);});
  const end=e=>{if(e.pointerId!==id)return;id=null;F.input.pad=null;if(knob)knob.style.transform='';};
  el.addEventListener('pointerup',end);el.addEventListener('pointercancel',end);
}
function throttleOn(el){
  let id=null;
  const at=e=>{const r=el.getBoundingClientRect(),pad=18;F.input.thr=clamp(1-(e.clientY-r.top-pad)/(r.height-2*pad),0,1);S.Tt=F.input.thr;};
  el.addEventListener('pointerdown',e=>{if(id!==null)return;id=e.pointerId;el.setPointerCapture?.(id);at(e);e.preventDefault();});
  el.addEventListener('pointermove',e=>{if(e.pointerId===id)at(e);});
  const end=e=>{if(e.pointerId===id)id=null;};
  el.addEventListener('pointerup',end);el.addEventListener('pointercancel',end);
  el.addEventListener('keydown',e=>{if(e.key==='ArrowUp'||e.key==='ArrowRight'){S.Tt=clamp(S.Tt+.1,0,1);e.preventDefault();e.stopPropagation();}if(e.key==='ArrowDown'||e.key==='ArrowLeft'){S.Tt=clamp(S.Tt-.1,0,1);e.preventDefault();e.stopPropagation();}});
}
const KEYS={ArrowLeft:1,ArrowRight:1,ArrowUp:1,ArrowDown:1,a:1,d:1,w:1,s:1,g:1,A:1,D:1,W:1,S:1,G:1};
function onKey(e){
  if(!F.el||F.hidden||!KEYS[e.key]||e.ctrlKey||e.metaKey||e.altKey)return;
  if(e.target?.closest?.('input,textarea,select,.pl-fly-ask'))return;
  e.preventDefault();e.stopPropagation();
  const k=e.key.length===1?e.key.toLowerCase():e.key;
  if(e.type==='keydown'){if(k==='g'&&!e.repeat)goAround('player');F.keys.add(k);F.el.querySelector('.pl-fly-keys').hidden=true;}
  else F.keys.delete(k);
}
/** This frame's stick: the pad (or the windscreen) wins over the keys; keys ease in and out. */
function readInput(dt){
  const I=F.input,k=F.keys;
  const tp=(k.has('ArrowDown')?1:0)-(k.has('ArrowUp')?1:0),trl=(k.has('ArrowRight')||k.has('d')?1:0)-(k.has('ArrowLeft')||k.has('a')?1:0);
  I.kp=lerp(I.kp,tp,clamp(dt*6,0,1));I.kr=lerp(I.kr,trl,clamp(dt*6,0,1));
  if(k.has('w'))S.Tt=clamp(S.Tt+dt*.6,0,1);
  if(k.has('s'))S.Tt=clamp(S.Tt-dt*.6,0,1);
  I.pitch=I.pad?I.pad[1]:I.kp;I.roll=I.pad?I.pad[0]:I.kr;
}

/* ================================================================ talk */
/** One line at a time from the captain (🧑‍✈️) or the tower (📻); `key` says each one once. */
function say(text,{key='',ms=3200,now=false}={}){
  if(key){if(F.ph.said?.has(key))return;(F.ph.said??=new Set()).add(key);}
  const line={text:tr(text),ms};
  if(now||!F.say||F.time>F.sayUntil-400){F.queue=[];show(line);}else F.queue.push(line);
}
function show(line){
  F.say=line.text;F.sayUntil=F.time+line.ms/1000;
  const p=F.el?.querySelector('.pl-fly-say');if(p){p.textContent=line.text;p.hidden=false;}
}
function talkTick(){
  if(!F.say||F.time<F.sayUntil)return;
  const next=F.queue.shift();
  if(next){show(next);return;}
  F.say='';const p=F.el?.querySelector('.pl-fly-say');if(p)p.hidden=true;
}
/** The first time each part comes up: one short line on how. */
function tip(part,text){
  let seen=[];try{seen=JSON.parse(store(TIPS)||'[]');}catch{seen=[];}
  if(!Array.isArray(seen))seen=[];
  if(seen.includes(part))return;
  seen.push(part);store(TIPS,JSON.stringify(seen.slice(-12)));
  F.tip=tr(text);F.tipUntil=F.time+9;
  const p=F.el.querySelector('.pl-fly-tip');p.textContent=F.tip;p.hidden=false;
  if(!matchMedia('(pointer:coarse)').matches)F.el.querySelector('.pl-fly-keys').hidden=false;
}
function chip(text){const p=F.el?.querySelector('.pl-fly-phase');const s=tr(text);if(p&&p.textContent!==s)p.textContent=s;}

/* ================================================================ talking to the server */
async function send(command,payload={},quiet=true){
  if(!F.x)return null;
  F.busy=true;
  try{return await F.x.send(command,{task:F.tid,...payload},{quiet});}
  catch{return null;}
  finally{F.busy=false;}
}
/** The server said no (a refusal, no network): the workbench's panels take over from where the hop is. */
function lost(){const fn=F.opts.done;close();fn?.();}

/* ================================================================ the hop, part by part */
const task=()=>F.t||{};
const data=()=>F.x?.room?.data||{};
const skyNow=()=>{const sk=data().sky;return sk&&sk.task===F.tid?sk:null;};
function lightOf(){
  const m=Number(F.x?.room?.day_clock?.minute);
  if(!Number.isFinite(m))return 'day';
  return m<345?'dawn':m<1050?'day':m<1110?'dusk':'night';
}
function sceneOf(name){
  const n=String(name||'');
  if(/Côn Đảo|Phú Quốc/.test(n))return 'sea';
  if(/Đà Lạt|Buôn Ma Thuột/.test(n))return 'hills';
  if(/Thành phố/.test(n))return 'city';
  return 'delta';
}
function start(){
  const t=task();
  F.hidden=false;F.el.hidden=false;
  if(F.phase)return;                                // already flying this hop
  if(t.stage==='start')enterTakeoff();
  else if(t.stage==='cruise')enterCruise();
  else if(t.stage==='approach')enterArrival(false);
  else{close();}
}
function setPhase(name,extra={}){
  F.phase=name;F.ph={t0:F.time,said:new Set(),...extra};
  const ga=F.el.querySelector('.pl-fly-ga');ga.hidden=name!=='approach'||!canAround();ga.classList.remove('hot');
  F.el.dataset.phase=name;
  F.el.classList.toggle('auto',['climb','cruise','descent','ask','around','hold'].includes(name));
  if(name!=='ask'&&F.ask){F.ask='';const box=F.el.querySelector('.pl-fly-ask');box.innerHTML='';box.hidden=true;}
}
function world(where,light=lightOf(),bare=false){
  F.scene=makeScene(sceneOf(where),light,`${F.tid}-${where}`,bare);
}

/* ---------------------------------------------------------------- take-off */
function enterTakeoff(){
  const t=task(),leg=t.needs?.leg||t.leg||{};
  world(leg.frm);
  const r=rngOf(F.tid+'to');
  Object.assign(S,{x:(r()-.5)*4,h:0,z:40,psi:(r()-.5)*.02,th:0,ph:0,V:0,T:0,Tt:0,vs:0,ground:true,gear:true,ap:false,shake:0,tl:1.4});
  F.wx={cw:(r()-.5)*6*KT,gust:.12,base:0,vis:20000,rain:0,cell:null,storm:false};
  F.input.thr=null;
  setPhase('takeoff',{rot:false,sent:false,maxOff:0,early:0,lift:0,assist:false,late:false});
  chip('🛫 Cất cánh');
  say(`📻 Đài: ${leg.code||'Cánh Cò'}, cho phép cất cánh.`,{ms:2600});
  say('🧑‍✈️ Đẩy ga lên hết nhé em.',{ms:3200});
  tip('takeoff','Đẩy cần ga lên hết, giữ vạch giữa. Chị hô thì kéo lên.');
}
function stepTakeoff(dt){
  const P=F.ph,kt=S.V/KT;
  if(S.ground){
    if(kt>=80)say('🧑‍✈️ Tám mươi.',{key:'80',ms:1600});
    if(kt>=VR){say('🧑‍✈️ Cất mũi! Kéo nhẹ về phía mình.',{key:'vr',ms:2600,now:true});P.rot=true;}
    if(F.input.pitch>.35&&kt<VR-12&&F.time-P.early>3){P.early=F.time;say('🧑‍✈️ Chưa đủ tốc độ, chờ chút.',{now:true,ms:1800});}
    const off=Math.abs(S.x);P.maxOff=Math.max(P.maxOff,off);
    if(off>8)say('🧑‍✈️ Giữ vạch giữa!',{key:'cl'+Math.floor(F.time/4),ms:1800});
    if(kt>=VR+14&&S.th<5*D2R){say('🧑‍✈️ Kéo lên… đó, chị đỡ tay.',{key:'help',ms:2400,now:true});P.assist=true;P.late=true;}
    if(F.time-P.t0>9&&S.Tt<.3)say('🧑‍✈️ Đẩy cần ga lên nào.',{key:'thr',ms:2600});
  }else{
    if(!P.sent){
      P.sent=true;P.lift=F.time;
      say('🧑‍✈️ Rời đất rồi. Thu càng!',{now:true,ms:2400});
      send('pl_takeoff').then(r=>{if(!r){lost();return;}P.reply=r;});
    }
    if(S.h>30)S.gear=false;
    if(S.V<100*KT)S.th=lerp(S.th,6*D2R,dt);           // too slow up here: the captain eases the nose down
    P.assist=false;
    if(P.reply&&(S.h>120||F.time-P.lift>9)){
      const good=P.maxOff<6&&!P.late;
      if(P.reply.message)say(P.reply.message,{ms:4200});
      say(good?'🧑‍✈️ Cất cánh đẹp! Lái tự động nhé.':'🧑‍✈️ Lái tự động. Em nghỉ tay chút.',{ms:2600});
      enterClimb();
    }
  }
}

/* ---------------------------------------------------------------- the autopilot's time-lapses */
function enterClimb(){
  setPhase('climb',{h0:S.h,z0:S.z,dur:3.2});
  S.ap=true;S.gear=false;chip('⏩ Lái tự động · lên 12.000 ft');
}
function stepClimb(dt){
  const P=F.ph,k=clamp((F.time-P.t0)/P.dur,0,1);
  S.h=lerp(P.h0,3660,k*k);S.z+=S.V*dt*6;S.V=lerp(S.V,105,clamp(dt*1.2,0,1));S.th=lerp(S.th,(k<.85?7:1)*D2R,clamp(dt*3,0,1));S.ph=lerp(S.ph,0,clamp(dt*6,0,1));
  if(k<1)return;
  const t=task();
  if(t.stage==='start')return;                       // the take-off is still on its way to the server
  enterCruise();
}
function enterCruise(){
  const t=task(),leg=t.needs?.leg||{},ev=t.needs?.event;
  world(t.where||leg.to,lightOf(),true);           // up here: the sky and the clouds below, no airfield
  Object.assign(S,{h:Math.max(S.h,3660),V:Math.max(S.V,105),ground:false,gear:false,ap:true});
  if(t.stage==='cruise'&&ev?.kind==='cell'){enterCell();return;}
  if(t.stage==='cruise'){setPhase('ask');chip('✈️ Trên đường bay');say(`${ev?.emoji||'✈️'} ${ev?.title||''}`,{ms:3000});return;}
  enterDescent();
}
function stepCruise(dt){
  // An answer on the workbench's panel moves the hop on: off to the approach.
  const t=task();
  S.z+=S.V*dt*3;
  if(t.stage==='approach'){F.ph.after??=F.time;if(F.time-F.ph.after>1.2)enterDescent();}
  else if(t.stage!=='cruise')lost();
}
function enterDescent(){
  const t=task();
  setPhase('descent',{h0:S.h,dur:2.8});
  S.ap=true;chip(`⏩ Xuống dần về ${t.where||''}`);
}
function stepDescent(dt){
  const P=F.ph,k=clamp((F.time-P.t0)/P.dur,0,1);
  S.h=lerp(P.h0,900,k);S.th=lerp(S.th,-2*D2R,clamp(dt*3,0,1));S.ph=lerp(S.ph,0,clamp(dt*6,0,1));S.V=lerp(S.V,75,clamp(dt*2,0,1));S.z+=S.V*dt*6;
  if(k<1)return;
  const t=task();
  if(t.stage!=='approach')return;                    // still waiting for the last answer
  enterArrival(true);
}
/** At the approach: the weather over the field, the airport's rain report, or straight to the hand-over. */
function enterArrival(fromAir){
  const t=task();
  world(t.where);
  if(!fromAir)Object.assign(S,{h:900,V:75,ground:false,gear:false,ap:true,th:0,ph:0});
  const sk=skyNow();
  if(t.problem||(sk&&!sk.set)){
    weather();
    Object.assign(S,{x:0,z:AIM-11000,h:t.problem?900:650,psi:0,th:0,ph:0,V:t.problem?80:72,ap:true,ground:false,gear:!t.problem});
    setPhase('ask',{arrive:true,at0:t.at});
    chip(t.problem?`⛈️ Tới ${t.where||''}`:`🌧️ Bản tin ${t.where||''}`);
    if(t.problem)say(t.problem==='storm'?'📻 Đài: giông đang ở trên sân bay.':'📻 Đài: sương còn dày, dưới mức tối thiểu.',{ms:3600});
    else say(`📻 Đài: ${sk.name||'mưa'} ở ${t.where||''}. Cài đặt tiếp cận nhé.`,{ms:3600});
    return;
  }
  if(!t.fly){lost();return;}                         // an older server: the gate cards
  enterApproach();
}
function stepArriveAsk(dt){
  const t=task(),sk=skyNow();
  S.z+=S.V*dt*.6;
  if(t.stage!=='approach'){lost();return;}
  if(t.problem||(sk&&!sk.set))return;
  F.ph.after??=F.time;
  if(F.time-F.ph.after<1)return;
  if(t.arrive==='hold'){enterHold('⏩ Bay chờ 20 phút',true);return;}
  if(t.at&&t.at!==F.ph.at0&&(t.arrive==='divert'||sk?.set?.go==='divert')){enterHold(`⏩ Bay đi ${t.at}`,false);return;}
  if(!t.fly){lost();return;}
  enterApproach();
}
function enterHold(label,circle){
  setPhase('hold',{dur:3,circle});S.ap=true;chip(label);
}
function stepHold(dt){
  const P=F.ph,k=clamp((F.time-P.t0)/P.dur,0,1);
  if(P.circle){S.psi+=dt*2.1;S.ph=lerp(S.ph,20*D2R,clamp(dt*3,0,1));}else{S.ph=lerp(S.ph,0,clamp(dt*3,0,1));}
  S.z+=S.V*dt*4;
  if(k<1)return;
  const t=task();
  if(t.stage!=='approach'){lost();return;}
  if(!t.fly){lost();return;}
  enterApproach();
}

/* ---------------------------------------------------------------- the cell on the track */
function enterCell(){
  const r=rngOf(F.tid+'cell');
  Object.assign(S,{x:0,z:0,h:3660,psi:0,th:alpha(110),ph:0,V:110,T:.6,Tt:.6,ground:false,gear:false,ap:false});
  F.wx={cw:0,gust:.2,base:0,vis:30000,rain:0,cell:{x:(r()-.5)*500,z:10500,r:2300},storm:false};
  setPhase('cell',{minD:1e9,inside:false,maxGain:0,sent:false});
  chip('⛈️ Vòng tránh giông');
  say('📻 Radar: mây giông ngay trên đường bay. Vòng tránh nhé!',{ms:3600});
  tip('cell','Nghiêng cánh để vòng qua đám mây giông, qua rồi thì về hướng cũ.');
}
function stepCell(){
  const P=F.ph,c=F.wx.cell,dx=S.x-c.x,dz=S.z-c.z,d=Math.hypot(dx,dz);
  P.minD=Math.min(P.minD,d);P.maxGain=Math.max(P.maxGain,S.h-3660);
  const inside=d<c.r;
  if(inside&&!P.inside){P.inside=true;say('🧑‍✈️ Rung quá! Ra khỏi mây ngay!',{now:true,ms:2400});}
  S.shake=inside?1:Math.max(0,1-(d-c.r)/1500)*.35;
  if(!P.sent&&(S.z>c.z+c.r+1200||F.time-P.t0>45)){
    P.sent=true;
    const opt=!P.inside?'deviate':P.maxGain>500?'over':'through';
    if(opt==='deviate')say('🧑‍✈️ Đẹp! Qua rồi, về hướng cũ nhé.',{now:true,ms:2600});
    send('pl_decide',{option:opt}).then(r=>{if(!r){lost();return;}if(r.message)say(r.message,{ms:4000});P.done=F.time;});
  }
  if(P.done&&F.time-P.done>1.4)enterDescent();
}

/* ---------------------------------------------------------------- the approach, flown */
function weather(){
  const t=task(),sk=skyNow(),fly=t.fly||{kt:VREF,dots:0,sink:700,wind:8,rwy:true},wx=t.needs?.wx?.id;
  const r=rngOf(`${F.tid}-${t.ap}-${t.at||''}`),first=!t.ap;
  const stormLand=t.arrive==='land';
  const w={cw:(r()<.5?-1:1)*fly.wind*KT,gust:.12,base:0,vis:20000,rain:0,cell:null,storm:false,cellSide:0,wipers:true};
  if(wx==='wind')w.gust=.55;
  if(fly.wind>28)w.gust=1;
  if(wx==='cloud')w.base=900*FT;
  if(first&&!fly.rwy)w.base=140*FT;
  if(sk&&!(t.at&&sk.set?.go==='divert')){
    w.rain=sk.kind==='squall'?1:.8;w.vis=sk.vis||2000;w.gust=Math.max(w.gust,(sk.gust||0)/20);
    if(sk.cell){w.cellSide=sk.cell==='left'?-1:1;w.cell={x:w.cellSide*2600,z:AIM-4200,r:1500};}
    w.wipers=sk.set?sk.set.wipers:true;
  }
  if(t.problem==='storm'||(stormLand&&wx==='storm')){w.storm=true;w.rain=Math.max(w.rain,.9);w.gust=Math.max(w.gust,.9);if(t.problem)w.cell={x:0,z:AIM+400,r:2200};}
  if(t.problem==='fog'||(stormLand&&wx==='fog')){w.vis=300;w.base=90*FT;}
  F.wx=w;
  return w;
}
function enterApproach(){
  const t=task(),fly=t.fly||{kt:VREF,dots:0,sink:700,wind:8,rwy:true};
  world(t.where);
  const w=weather();
  const r=rngOf(`${F.tid}-ho-${t.ap}-${t.arounds}`),late=t.gate>=1;
  const h0=(late?820:1300)*FT,dist=h0/Math.tan(GS);
  const dots=late?0:(fly.dots||0)*(fly.dots>=2?1:(r()<.5?-1:1));
  const V=(late?VREF:fly.kt||VREF)*KT,vs=-(late?650:fly.sink||700)/60*FT,gam=Math.asin(clamp(vs/V,-.3,.1));
  Object.assign(S,{x:(r()-.5)*(late?16:70),z:AIM-dist,h:h0+dots*dist*Math.tan(DOT),psi:Math.asin(clamp(-w.cw/V,-.3,.3)),ph:0,V,
    th:gam+alpha(V),T:trim(V,gam),ground:false,gear:true,ap:false,shake:0});
  S.Tt=S.T;F.input.thr=null;
  setPhase('approach',{g1:late?{stable:true,sent:true}:null,g2:null,g1sent:late,touch:null,callH:1e9,sent:false,auto:false,lowSay:0});
  chip(`🛬 Tiếp cận ${t.where||''}`);
  const lines=[];
  if((fly.kt||0)>122&&!late)lines.push('Tàu đang nhanh quá, giảm ga ngay!');
  else if(fly.dots>=2&&!late)lines.push('Mình đang cao, xuống dốc hơn chút.');
  else if((fly.sink||0)>1000&&!late)lines.push('Xuống gấp quá, kéo nhẹ lên!');
  say(`🧑‍✈️ Em cầm lái nhé. Giữ 2 trắng 2 đỏ, ${VREF} knot.${lines.length?' '+lines[0]:''}`,{now:true,ms:4200});
  if(Math.abs(w.cw)/KT>=14)say(`📻 Đài: gió ngang ${Math.round(Math.abs(w.cw)/KT)} knot.`,{ms:2600});
  tip('approach','2 trắng 2 đỏ là đúng dốc. Chị hô thì ghìm mũi cho êm.');
}
const alpha=V=>3*D2R*clamp((VREF*KT/Math.max(V,30))**2,.4,2.4);
const trim=(V,gam)=>clamp((K_D*V*V+G*Math.sin(gam))/A_T,0,1);
/** The approach as flown right now: the 1,000 ft gate's words (110–120 kt, 1 dot, 1,000 ft/min), a little kinder. */
function judge(){
  const kt=S.V/KT,dist=Math.max(60,AIM-S.z),dev=(Math.atan2(S.h,dist)-GS)/DOT,loc=Math.atan2(S.x,dist+LEN-AIM)/(1.25*D2R),sink=-S.vs/FT*60;
  const why=kt>122?'nhanh quá':kt<106?'chậm quá':dev>1.3?'cao quá':dev<-1.3?'thấp quá':sink>1100?'xuống gấp quá':Math.abs(loc)>1.5?'lệch tim đường băng':'';
  return {stable:!why,why,kt,dev,loc,sink};
}
function stepApproach(){
  const P=F.ph,t=task(),hft=S.h/FT,w=F.wx;
  if(S.ground)return;
  if(hft<=1000&&!P.g1){
    const j=judge();P.g1={stable:j.stable,why:j.why};
    say(j.stable?'🧑‍✈️ Một nghìn. Ổn định.':`🧑‍✈️ Một nghìn, chưa ổn định: ${j.why}. Bay lại?`,{now:true,ms:j.stable?2200:3600});
    if(!j.stable)F.el.querySelector('.pl-fly-ga').classList.add('hot');
  }
  if(P.g1&&!P.g1sent&&hft<=850){
    P.g1sent=true;F.el.querySelector('.pl-fly-ga').classList.remove('hot');
    if(!P.g1.stable)say('🧑‍✈️ Chưa ổn định mà vẫn xuống… chị ghi lại nhé.',{now:true,ms:2800});
    send('pl_gate',{flown:{stable:P.g1.stable}}).then(r=>{if(!r)lost();});
  }
  if(hft<=500)say('🧑‍✈️ Năm trăm.',{key:'500',ms:1400});
  if(hft<=200&&!P.g2){
    const j=judge(),fly=t.fly||{};
    P.g2={stable:j.stable,why:j.why};
    let line=j.stable?'🧑‍✈️ Hai trăm. Thấy đường băng. Hạ cánh!':`🧑‍✈️ Hai trăm, ${j.why}. Bay lại?`;
    if(!t.ap&&fly.rwy===false)line='🧑‍✈️ Hai trăm… chưa thấy đường băng!';
    else if((fly.wind||0)>28)line=`🧑‍✈️ Gió ngang ${fly.wind} knot, quá giới hạn!`;
    say(line,{now:true,ms:3000});
    if(!j.stable||!t.ap&&(fly.rwy===false||(fly.wind||0)>28))F.el.querySelector('.pl-fly-ga').classList.add('hot');
  }
  for(const [h,s] of [[50,'Năm mươi'],[30,'Ba mươi'],[10,'Mười']])if(hft<=h)say(`🔊 ${s}.`,{key:'ra'+h,ms:900,now:h===30});
  if(hft<=25&&S.Tt>.15){S.Tt=0;say('🧑‍✈️ Thu ga, ghìm mũi!',{key:'flare',now:true,ms:1600});}
  // The captain takes it: far too low short of the runway, or not lined up at all.
  const dist=AIM-S.z;
  if(!P.auto&&((hft<160&&dist>1200)||(hft<70&&(S.z<-150||Math.abs(S.x)>40))||hft>2000)){
    P.auto=true;say(hft>2000?'🧑‍✈️ Mình bay lại cho chắc.':'🧑‍✈️ Thấp quá! Chị cầm lái, bay lại.',{now:true,ms:2600});goAround('captain');
  }
}
/** Wheels on the ground: how it went, and the last gate to the server. */
function touchdown(){
  const P=F.ph;if(P.touch)return;
  const sink=Math.max(0,-S.vs/FT*60),long=S.z>AIM+500,short=S.z<-20,off=Math.abs(S.x)>HALF;
  const touch=sink>360?'firm':long?'long':'soft';
  P.touch={touch,sink};
  const stable=(P.g2?P.g2.stable:judge().stable)&&!off&&!short;
  say(touch==='soft'?'🧑‍✈️ Êm quá!':touch==='firm'?'🧑‍✈️ Hơi mạnh tay rồi.':'🧑‍✈️ Hơi xa chút.',{now:true,ms:1800});
  F.el.querySelector('.pl-fly-ga').hidden=true;
  setPhase('rollout',{touch});
  F.ph.stable=stable;
  const go=()=>send('pl_gate',{flown:{stable,touch}},false).then(r=>{if(!r){lost();return;}F.ph.reply=r;});
  // The 1,000 ft gate first (a quick descent can beat it), then the landing.
  if(!P.g1sent)send('pl_gate',{flown:{stable:P.g1?P.g1.stable:true}}).then(r=>r?go():lost());else go();
}
function stepRollout(dt){
  const P=F.ph;
  S.Tt=0;S.T=0;S.th=lerp(S.th,0,dt*2);S.ph=lerp(S.ph,0,dt*4);S.x=lerp(S.x,0,dt*.6);S.psi=lerp(S.psi,0,dt*2);
  if(S.V<35*KT&&P.reply&&!P.end){P.end=F.time;say('🅿️ Lăn vào bến…',{ms:2000});chip('🅿️ Lăn vào bến');}
  if(P.end&&F.time-P.end>2){const fn=F.opts.done;close();fn?.();}
}

/* ---------------------------------------------------------------- the go-around */
function canAround(){const t=task();return !((t.arounds||0)>=2&&t.at);}
function goAround(who){
  if(F.phase!=='approach'||S.ground)return;
  const P=F.ph;
  if(!canAround()){say('🧑‍✈️ Dầu chỉ đủ hạ cánh lần này. Mình xuống thôi.',{now:true,ms:2600});return;}
  const j=P.g2||(P.g1&&!P.g1sent?P.g1:null)||judge();
  setPhase('around',{who,dur:3.2,at0:task().at});
  S.Tt=1;S.ap=true;chip('↗️ Bay lại');
  if(who==='player')say('🧑‍✈️ Bay lại! Ga hết, ngóc mũi.',{now:true,ms:2400});
  send('pl_around',{flown:{stable:who==='captain'?false:j.stable}}).then(r=>{if(!r){lost();return;}F.ph.reply=r;if(r.message)say(r.message,{ms:4200});});
}
function stepAround(dt){
  const P=F.ph,k=(F.time-P.t0)/P.dur;
  S.th=lerp(S.th,9*D2R,dt*2);S.ph=lerp(S.ph,0,dt*3);
  if(S.h>60)S.gear=false;
  if(k<1||!P.reply)return;
  const t=task();
  if(t.stage!=='approach'){lost();return;}
  if(t.at&&t.at!==P.at0)say(`↪️ Đi sân bay dự bị ${t.at}.`,{ms:2600});
  enterApproach();
}

/* ================================================================ flight model */
const TIMELAPSE=['climb','descent','ask','hold'];
function physics(dt){
  const w=F.wx||{cw:0,gust:0},ph=F.phase,I=F.input;
  S.T=lerp(S.T,S.Tt,clamp(dt*1.4,0,1));
  // The tapes and the flight director run in real time; the trip itself runs faster (a ~1 minute approach).
  const scale=ph==='takeoff'?1.5:ph==='cell'?5:ph==='approach'?(S.h>100*FT?3:S.h>40*FT?2:1.3):ph==='rollout'?1.6:2;
  const dts=dt*scale;
  if(['takeoff','cell','approach'].includes(ph)&&!S.ap){
    if(S.ground){
      const pull=Math.max(I.pitch,F.ph.assist?.8:0);
      if(S.V>=(VR-8)*KT&&pull>0)S.th+=pull*4*D2R*dt;else S.th=lerp(S.th,0,clamp(dt*3,0,1));
      S.psi+=I.roll*7*D2R*dt*clamp(S.V/15,.2,1);S.ph=0;
    }else{
      S.th+=I.pitch*5.5*D2R*dt;
      S.ph+=I.roll*28*D2R*dt;
      if(Math.abs(I.roll)<.08)S.ph=lerp(S.ph,0,clamp(dt*.7,0,1));   // the wings come level by themselves, slowly
    }
  }else if(ph==='around'){S.th=lerp(S.th,9*D2R,clamp(dt*1.5,0,1));S.ph=lerp(S.ph,0,clamp(dt*3,0,1));}
  S.th=clamp(S.th,-12*D2R,16*D2R);S.ph=clamp(S.ph,-32*D2R,32*D2R);
  // Bumps: a smooth wobble, stronger in gusts and inside a cell.
  const gu=(w.gust||0)+S.shake*1.4,calm=still()?.35:1,tg=F.time;
  const n1=Math.sin(tg*1.7)+.6*Math.sin(tg*3.1+1)+.3*Math.sin(tg*7.3+2),n2=Math.sin(tg*1.3+4)+.5*Math.sin(tg*2.9+3)+.3*Math.sin(tg*6.1+1);
  if(!S.ground&&gu>0&&!TIMELAPSE.includes(ph)){S.th+=n1*.5*D2R*gu*dt*calm;S.ph+=n2*4*D2R*gu*dt*calm;}
  if(S.ground){
    const brake=ph==='rollout'?2.6:0;
    S.V=Math.max(0,S.V+(S.T*A_T-.12-K_D*S.V*S.V-brake)*dts);
    S.vs=0;S.h=0;
    S.z+=S.V*Math.cos(S.psi)*dts;S.x+=(S.V*Math.sin(S.psi)+w.cw*.12*clamp(S.V/30,0,1))*dts;
    if(Math.abs(S.x)>HALF-3){S.x=sgn(S.x)*(HALF-3);S.psi*=.5;}
    if(ph==='takeoff'&&S.V>=(VR-2)*KT&&S.th>=5*D2R){S.ground=false;S.h=.3;}
    return;
  }
  if(TIMELAPSE.includes(ph)){S.vs=0;return;}         // the autopilot's time-lapse moves the aircraft itself
  const gam=clamp(S.th-alpha(S.V),-14*D2R,16*D2R);
  S.vs=S.V*Math.sin(gam)+(gu?n2*1.1*gu*calm:0);
  if(S.vs<0&&S.h<12*FT&&ph==='approach')S.vs*=.6;     // the air cushion just above the runway
  S.h+=S.vs*dts;
  if(ph==='cell')S.V=lerp(S.V,110,clamp(dt,0,1));    // the autothrottle holds the cruise
  else S.V=clamp(S.V+(S.T*A_T-K_D*S.V*S.V-G*Math.sin(gam))*dts,25,160);
  S.psi+=G*Math.tan(S.ph)/Math.max(S.V,40)*dts;
  S.x+=(S.V*Math.cos(gam)*Math.sin(S.psi)+w.cw+(gu?n1*1.4*gu:0))*dts;
  S.z+=S.V*Math.cos(gam)*Math.cos(S.psi)*dts;
  if(S.h<=0){
    S.h=0;
    if(ph==='approach'){S.ground=true;touchdown();S.th=Math.max(S.th,0);}
    else if(ph==='takeoff')S.ground=true;
    else S.h=1;
  }
}
/** Where the flight director points: pitch and bank the captain would fly now (radians). */
function director(){
  const ph=F.phase,w=F.wx||{cw:0};
  if(ph==='takeoff')return S.ground?{th:S.V>=VR*KT?8*D2R:0,ph:0,steer:clamp(-S.x*.08-S.psi*3,-1,1)}:{th:8*D2R,ph:clamp(-S.psi*2,-.3,.3)};
  if(ph==='cell'){
    const c=w.cell,P=F.ph;let want=0;
    if(c&&S.z<c.z+c.r*.2){P.side??=Math.abs(S.psi)>.06?sgn(S.psi):1;want=P.side*24*D2R;}
    else if(c&&S.z<c.z+c.r+1500)want=sgn(S.x-c.x)*4*D2R;
    else want=clamp(-S.x/4000,-.3,.3);
    return {th:alpha(S.V)-clamp((S.h-3660)*.0004,-.05,.05),ph:clamp((want-S.psi)*2.5,-25*D2R,25*D2R)};
  }
  if(ph==='approach'||ph==='rollout'){
    const dist=Math.max(30,AIM-S.z),hgs=Math.max(0,dist*Math.tan(GS)),dev=S.h-hgs;
    let gam=clamp(-3-dev*.05,-6,-.6)*D2R;
    if(S.h<35*FT)gam=-.8*D2R;
    const vx=S.V*Math.sin(S.psi)+w.cw;
    const want=clamp(-S.x*.0016-vx*.035,-.3,.3)+Math.asin(clamp(-w.cw/Math.max(S.V,40),-.3,.3));
    return {th:gam+alpha(S.V)+(S.h<35*FT?1.5*D2R:0),ph:clamp((want-S.psi)*3,-20*D2R,20*D2R)};
  }
  return {th:2*D2R,ph:0};
}
/** The autopilot while the player waits (a decision, the hold): wings level, nose on the horizon. */
function autopilot(dt){
  if(!S.ap||!['ask','hold'].includes(F.phase))return;
  S.th=lerp(S.th,1*D2R,clamp(dt,0,1));if(F.phase!=='hold')S.ph=lerp(S.ph,0,clamp(dt*2,0,1));
}

/* ================================================================ the frame */
function frame(now){
  F.raf=requestAnimationFrame(frame);
  const raw=now-F.last;F.last=now;
  if(!F.el)return;
  // The sheet closed or moved to another page: hold still (and the job's own render will reopen us).
  if(++F.seenCheck%20===0){const here=!!document.querySelector('#sheet[open] #sheetContent .career-job.pl')&&F.el.isConnected;F.hidden=!here;F.el.hidden=!here;}
  if(F.hidden||document.hidden)return;
  const dt=Math.min(.05,Math.max(0,raw/1000));
  F.time+=dt;
  measure(raw,now);
  readInput(dt);
  try{
    autopilot(dt);
    physics(dt);
    if(F.phase==='takeoff')stepTakeoff(dt);
    else if(F.phase==='climb')stepClimb(dt);
    else if(F.phase==='ask')(F.ph.arrive?stepArriveAsk:stepCruise)(dt);
    else if(F.phase==='descent')stepDescent(dt);
    else if(F.phase==='cell')stepCell(dt);
    else if(F.phase==='approach')stepApproach(dt);
    else if(F.phase==='rollout')stepRollout(dt);
    else if(F.phase==='around')stepAround(dt);
    else if(F.phase==='hold')stepHold(dt);
    if(!F.el)return;
    talkTick();
    const tv=Math.round(S.Tt*100);
    if(tv!==F.thrShown){F.thrShown=tv;const th=F.el.querySelector('.pl-fly-thr');th.style.setProperty('--thr',String(S.Tt));th.setAttribute('aria-valuenow',String(tv));}
    if(F.tip&&F.time>F.tipUntil){F.tip='';F.el.querySelector('.pl-fly-tip').hidden=true;}
    draw();
  }catch(error){console.error(error);leave('error');}
}
/** Frame time: the page drops its extras when the phone struggles, and goes back to Bay nhanh when it still can't. */
function measure(raw,now){
  const s=F.stats;
  if(now-s.start<1500||raw<=0||raw>1000)return;
  s.n++;s.sum+=raw;s.max=Math.max(s.max,raw);s.win+=raw;s.winN++;
  if(s.win<2500)return;
  const avg=s.win/s.winN;s.win=0;s.winN=0;
  if(avg>40&&!F.lite){F.lite=true;size();return;}
  s.slow=avg>70?s.slow+1:0;
  if(s.slow>=2&&!F.fallback){F.fallback=true;F.x?.toast?.(tr('Máy hơi chậm: chuyển sang Bay nhanh.'));leave('slow');}
}
/** For the browser checks: where the aircraft is and what the director wants (read-only). */
globalThis.__plFly={
  state:()=>{const d=F.el?director():{th:0,ph:0};const j=F.phase==='approach'?judge():null;
    return {phase:F.phase,open:!!F.el,kt:S.V/KT,ft:S.h/FT,th:S.th/D2R,ph:S.ph/D2R,psi:S.psi/D2R,x:S.x,z:S.z,T:S.T,ground:S.ground,
      fdTh:d.th/D2R,fdPh:d.ph/D2R,steer:d.steer||0,stable:j?.stable??null,why:j?.why||'',say:F.say,ask:!!F.ask,busy:F.busy};},
  stats:()=>{const s=F.stats;return {frames:s.n,avg:s.n?s.sum/s.n:0,max:s.max,lite:F.lite,dpr:F.dpr};},
};

/* ================================================================ drawing */
const SKY={day:['#3d7fc4','#a9d1f0','#dcecf7'],dawn:['#4a5d8f','#f0a878','#f7d6b0'],dusk:['#2b3566','#d9805c','#f2b98e'],night:['#050a1c','#0f1d3d','#1b2a4c']};
const GROUND={sea:['#2b6f9e','#2f7fae'],delta:['#5f8f3e','#6e9c48'],hills:['#3f6b3c','#4b7a43'],city:['#6f7d68','#7a876f']};
const DARK={sea:['#071526','#0a1a2e'],delta:['#0b140b','#0e1a0e'],hills:['#081108','#0b160b'],city:['#0e110e','#121612']};
function makeScene(kind,light,seed,bare=false){
  const r=rngOf(seed),night=light==='night',sc={kind,light,night,bare,patches:[],boxes:[],lights:[],clouds:[],hills:[]};
  const fieldCols=night?['#0d180d','#101d10','#0b150b']:kind==='delta'?['#7aa84f','#93b65a','#5d8f3a','#b8b45c','#6f9e45']:kind==='hills'?['#46753f','#3b6637','#557f45','#2f5a2f']:kind==='city'?['#7d8a72','#6d7a64','#8e9682','#a19f8c']:['#d9c9a0','#6f9a52','#5f8a48'];
  // The airfield's grass and its apron, always there.
  sc.patches.push({pts:[[-140,-700],[140,-700],[140,LEN+400],[-140,LEN+400]],col:night?'#0e1a0e':kind==='sea'?'#7ea35c':'#78a052'});
  sc.patches.push({pts:[[80,300],[260,300],[260,900],[80,900]],col:night?'#1c1f24':'#9a9c98'});
  sc.patches.push({pts:[[48,0],[66,0],[66,LEN],[48,LEN]],col:night?'#16191d':'#7d8084'});          // the taxiway
  if(kind==='sea'){
    // An island: sand and green around the runway, the sea beyond.
    const isl=[];for(let i=0;i<14;i++){const a=i/14*Math.PI*2,rr=lerp(1700,2600,r());isl.push([Math.sin(a)*rr*1.1,LEN/2+Math.cos(a)*rr*1.5]);}
    sc.patches.unshift({pts:isl.map(([x,z])=>[x*1.08,z]),col:night?'#141a12':'#e2d3a6'},{pts:isl,col:night?'#0f1a0f':'#5f8f45'});
  }else{
    for(let i=0;i<46;i++){
      const cx=(r()-.5)*9000,cz=(r()-.3)*14000;if(Math.abs(cx)<260&&cz>-900&&cz<LEN+600)continue;
      const w=lerp(250,900,r()),d=lerp(250,1100,r());
      sc.patches.push({pts:[[cx-w,cz-d],[cx+w,cz-d],[cx+w,cz+d],[cx-w,cz+d]],col:fieldCols[i%fieldCols.length]});
    }
    if(kind==='delta'){const xs=-900-r()*800;sc.patches.push({pts:[[xs,-12000],[xs+160,-12000],[xs+420,15000],[xs+260,15000]],col:night?'#0b1420':'#7b8f86'});}
  }
  // The terminal and the tower beside the apron.
  sc.boxes.push({x:200,z:600,w:60,d:130,h:14,col:'#e7e3d8',roof:'#b9b3a6',win:true},{x:120,z:930,w:8,d:8,h:34,col:'#d9d5ca',roof:'#5d7d96',win:true});
  if(kind==='city'||kind==='delta'){
    const n=kind==='city'?60:14;
    for(let i=0;i<n;i++){const side=r()<.5?-1:1,x=side*lerp(500,4200,r()),z=lerp(-3000,6000,r());
      sc.boxes.push({x,z,w:lerp(20,70,r()),d:lerp(20,70,r()),h:kind==='city'?lerp(12,90,r()):lerp(6,14,r()),col:['#d8d2c4','#c9c3b5','#e8e1d0','#b8b6ad'][i%4],roof:'#8d8a82',win:kind==='city'});}
  }
  if(night){
    const n=kind==='city'?420:kind==='sea'?40:140;
    for(let i=0;i<n;i++){const side=r()<.5?-1:1;sc.lights.push([side*lerp(400,kind==='city'?6000:3500,r()),lerp(-6000,9000,r()),r()<.7?'#ffcf7a':'#fff2c9']);}
  }
  if(kind==='hills')for(let i=0;i<9;i++)sc.hills.push([i/9+r()*.05,lerp(.012,.035,r())]);
  if(bare){sc.patches=sc.patches.slice(kind==='sea'?2:3).filter(p=>p.pts.length===4);sc.boxes=sc.boxes.slice(2);}
  for(let i=0;i<16;i++)sc.clouds.push({x:(r()-.5)*16000,y:lerp(550,1400,r()),z:(r()-.2)*22000,s:lerp(380,900,r()),k:i%3});
  for(let i=0;i<10;i++)sc.clouds.push({x:(r()-.5)*30000,y:lerp(2500,3300,r()),z:(r())*60000,s:lerp(900,1800,r()),k:i%3});
  return sc;
}
function sprites(){
  if(F.sprites)return F.sprites;
  const mk=(w,h,paint)=>{const cv=document.createElement('canvas');cv.width=w;cv.height=h;paint(cv.getContext('2d'),w,h);return cv;};
  const puff=(c,x,y,r,col)=>{const g=c.createRadialGradient(x,y,r*.1,x,y,r);g.addColorStop(0,col);g.addColorStop(1,'rgba(255,255,255,0)');c.fillStyle=g;c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.fill();};
  const cloud=(seed,dark=false)=>mk(256,128,(c,w,h)=>{const r=rngOf(seed);for(let i=0;i<14;i++)puff(c,lerp(40,216,r()),lerp(54,92,r()),lerp(22,48,r()),dark?'rgba(70,76,92,.95)':'rgba(255,255,255,.92)');});
  F.sprites={clouds:[cloud('a'),cloud('b'),cloud('c')],cell:mk(256,384,(c)=>{const r=rngOf('cell');
    for(let i=0;i<34;i++){const y=lerp(40,360,r()),wd=lerp(40,110,1-Math.abs(y-120)/300);puff(c,128+(r()-.5)*wd*1.4,y,lerp(30,62,r()),`rgba(${52+r()*20|0},${58+r()*20|0},${74+r()*20|0},.96)`);}
    const g=c.createLinearGradient(0,300,0,384);g.addColorStop(0,'rgba(60,66,80,.0)');g.addColorStop(1,'rgba(60,66,80,.55)');c.fillStyle=g;c.fillRect(70,300,116,84);})};
  return F.sprites;
}
/* camera: yaw ψ, pitch θ (roll is the canvas' rotation) */
const C={x:0,y:0,z:0,sy:0,cy:1,sp:0,cp:1,f:400,cx:0,cyy:0};
const P3=new Float64Array(3);
function cam(wx,wy,wz){
  const dx=wx-C.x,dy=wy-C.y,dz=wz-C.z;
  const x1=dx*C.cy-dz*C.sy,z1=dx*C.sy+dz*C.cy;
  P3[0]=x1;P3[1]=dy*C.cp-z1*C.sp;P3[2]=dy*C.sp+z1*C.cp;
}
const sx=(x,z)=>C.cx+C.f*x/z,sy=(y,z)=>C.cyy-C.f*y/z;
/** A flat polygon on the ground (y = 0) or anywhere, clipped at the near plane. */
function polygon(c,pts,col,y=0){
  const n=pts.length,cs=[];
  for(let i=0;i<n;i++){const p=pts[i];cam(p[0],p.length>2?p[1]:y,p.length>2?p[2]:p[1]);cs.push([P3[0],P3[1],P3[2]]);}
  const out=[];
  for(let i=0;i<n;i++){
    const a=cs[i],b=cs[(i+1)%n],ia=a[2]>=NEAR,ib=b[2]>=NEAR;
    if(ia)out.push(a);
    if(ia!==ib){const k=(NEAR-a[2])/(b[2]-a[2]);out.push([lerp(a[0],b[0],k),lerp(a[1],b[1],k),NEAR]);}
  }
  if(out.length<3)return;
  c.beginPath();
  for(let i=0;i<out.length;i++){const p=out[i],X=sx(p[0],p[2]),Y=sy(p[1],p[2]);i?c.lineTo(X,Y):c.moveTo(X,Y);}
  c.closePath();c.fillStyle=col;c.fill();
}
/** A light (or a point): screen x, y and how far (0 when behind). */
function point(wx,wy,wz){cam(wx,wy,wz);const z=P3[2];if(z<NEAR)return null;return [sx(P3[0],z),sy(P3[1],z),z];}

function draw(){
  const c=F.c,L=F.L,dpr=F.dpr,V=L.view,sc=F.scene??=makeScene('delta','day','x'),w=F.wx||{};
  c.setTransform(dpr,0,0,dpr,0,0);
  // ---- the world through the windscreen
  c.save();c.beginPath();c.rect(V.x,V.y,V.w,V.h);c.clip();
  const shake=(S.shake*2+((w.gust||0)>.5&&!S.ground?.6:0)+(S.ground&&S.V>5?.25+S.V/80:0))*(still()?.3:1);
  const jx=shake?Math.sin(F.time*37)*shake:0,jy=shake?Math.cos(F.time*41)*shake:0;
  C.f=L.f;C.cx=V.w/2+jx;C.cyy=V.h*.42+jy;
  C.x=S.x;C.y=S.h+EYE;C.z=S.z;C.sy=Math.sin(S.psi);C.cy=Math.cos(S.psi);C.sp=Math.sin(S.th);C.cp=Math.cos(S.th);
  c.translate(C.cx,C.cyy);c.rotate(-S.ph);c.translate(-C.cx,-C.cyy);
  const hy=C.cyy+C.f*Math.tan(S.th),big=Math.hypot(V.w,V.h)*1.5,sky=SKY[sc.light]||SKY.day;
  let g=c.createLinearGradient(0,hy-V.h*1.1,0,hy);g.addColorStop(0,sky[0]);g.addColorStop(.7,sky[1]);g.addColorStop(1,sky[2]);
  c.fillStyle=g;c.fillRect(C.cx-big,hy-big*2,big*2,big*2);
  if(sc.night)stars(c,hy,big);
  if(sc.light==='dawn'||sc.light==='dusk'){const sxp=C.cx+(sc.light==='dawn'?-.35:.35)*V.w-S.psi*C.f;g=c.createRadialGradient(sxp,hy-6,2,sxp,hy-6,90);g.addColorStop(0,'rgba(255,214,150,.95)');g.addColorStop(1,'rgba(255,214,150,0)');c.fillStyle=g;c.fillRect(sxp-90,hy-96,180,96);}
  const gr=(sc.night?DARK:GROUND)[sc.kind]||GROUND.delta;
  g=c.createLinearGradient(0,hy,0,hy+V.h);g.addColorStop(0,gr[1]);g.addColorStop(1,gr[0]);
  c.fillStyle=g;c.fillRect(C.cx-big,hy,big*2,big*2);
  if(sc.hills.length)hills(c,hy,sc);
  for(const p of sc.patches)polygon(c,p.pts,p.col);
  if(!sc.bare)runway(c,sc,w);
  boxes(c,sc);
  if(sc.night)cityLights(c,sc);
  // haze where the ground meets the sky
  g=c.createLinearGradient(0,hy-2,0,hy+V.h*.16);g.addColorStop(0,sc.night?'rgba(27,42,76,.95)':'rgba(214,230,240,.85)');g.addColorStop(1,'rgba(214,230,240,0)');
  c.fillStyle=g;c.fillRect(C.cx-big,hy-2,big*2,V.h*.16+2);
  clouds(c,sc,w);
  c.restore();
  weatherFx(c,V,sc,w);
  frameOfWindow(c,V);
  panel(c);
}
function stars(c,hy,big){
  c.fillStyle='rgba(255,255,255,.75)';const r=rngOf('stars');
  for(let i=0;i<70;i++){const x=C.cx+(r()-.5)*big*1.4-S.psi*C.f*.2,y=hy-r()*big*.6-8;c.fillRect(x,y,1.3,1.3);}
}
function hills(c,hy,sc){
  c.fillStyle=sc.night?'#06100a':'#567d66';c.beginPath();
  const W=F.L.view.w,off=-S.psi*C.f;c.moveTo(C.cx-W*2,hy+1);
  for(let i=0;i<=40;i++){const u=i/40,x=C.cx-W*2+u*W*4;let hgt=0;for(const [p,a] of sc.hills)hgt+=a*Math.max(0,1-Math.abs(((u*2+off/W/2)%1+1)%1-p)*9);c.lineTo(x,hy-hgt*F.L.view.h*3);}
  c.lineTo(C.cx+W*2,hy+1);c.closePath();c.fill();
}
function runway(c,sc,w){
  const night=sc.night,fogHide=w.base&&S.h>w.base;
  polygon(c,[[-HALF-6,-20],[HALF+6,-20],[HALF+6,LEN+20],[-HALF-6,LEN+20]],night?'#121519':'#8d9a7b');
  polygon(c,[[-HALF,0],[HALF,0],[HALF,LEN],[-HALF,LEN]],night?'#24272c':'#4a4d52');
  const paint=night?'rgba(220,224,230,.55)':'#f2f2ee';
  // threshold bars, the aiming point, touchdown zone, centre line
  for(let i=0;i<8;i++){const x=-HALF+2+i*3.6+(i>=4?1.6:0);polygon(c,[[x,6],[x+2.2,6],[x+2.2,36],[x,36]],paint);}
  polygon(c,[[-9,AIM-20],[-5,AIM-20],[-5,AIM+25],[-9,AIM+25]],paint);polygon(c,[[5,AIM-20],[9,AIM-20],[9,AIM+25],[5,AIM+25]],paint);
  for(const z of [150,450,600]){polygon(c,[[-9,z],[-6.5,z],[-6.5,z+22],[-9,z+22]],paint);polygon(c,[[6.5,z],[9,z],[9,z+22],[6.5,z+22]],paint);}
  for(let z=60;z<LEN-40;z+=50){const d=AIM-S.z>6000&&z%100?null:1;if(d)polygon(c,[[-.45,z],[.45,z],[.45,z+28],[-.45,z+28]],paint);}
  polygon(c,[[-HALF,0],[-HALF+.6,0],[-HALF+.6,LEN],[-HALF,LEN]],paint);polygon(c,[[HALF-.6,0],[HALF,0],[HALF,LEN],[HALF-.6,LEN]],paint);
  if(fogHide&&S.h>w.base+30)return;
  // lights: the edges, the threshold (green), the end (red), the approach lights
  const bright=night||sc.light==='dusk'||w.vis<5000||w.rain;
  const dot=(p,col,r0)=>{if(!p)return;const r=Math.max(r0*.6,Math.min(r0*2.2,r0*900/p[2]));c.fillStyle=col;c.fillRect(p[0]-r/2,p[1]-r/2,r,r);};
  if(bright){
    for(let z=0;z<=LEN;z+=60){dot(point(-HALF-1,.3,z),'#fff6d8',1.6);dot(point(HALF+1,.3,z),'#fff6d8',1.6);}
    for(let x=-HALF;x<=HALF;x+=3){dot(point(x,.3,-1),'#5dff8a',1.8);dot(point(x,.3,LEN+1),'#ff4d4d',1.6);}
    for(let z=-60;z>=-660;z-=60){dot(point(0,.5,z),'#fffbe8',2);if(z%180===0)for(let x=-12;x<=12;x+=4)dot(point(x,.5,z),'#fffbe8',1.6);}
  }
  papi(c,night||bright);
}
/** PAPI: four lights left of the runway at the aiming point; each white above its angle, red below. */
function papi(c,glow){
  const p=point(-HALF-22,.6,AIM);if(!p)return;
  const dist=Math.max(1,AIM-S.z),ang=Math.atan2(S.h+EYE,dist)/D2R,lim=[2.5,2.83,3.17,3.5];
  const gap=Math.max(5,Math.min(30,9*C.f/p[2])),r=Math.max(2.4,Math.min(7,2.2*C.f/p[2]));
  for(let i=0;i<4;i++){
    const x=p[0]-(3-i)*gap,white=ang>lim[i];
    if(glow){c.fillStyle=white?'rgba(255,255,255,.28)':'rgba(255,60,60,.28)';c.beginPath();c.arc(x,p[1],r*2.4,0,Math.PI*2);c.fill();}
    c.fillStyle=white?'#ffffff':'#ff3b3b';c.beginPath();c.arc(x,p[1],r,0,Math.PI*2);c.fill();
  }
}
function boxes(c,sc){
  const list=[];
  for(const b of sc.boxes){cam(b.x,0,b.z);if(P3[2]<NEAR||P3[2]>16000)continue;list.push([P3[2],b]);}
  list.sort((a,b)=>b[0]-a[0]);
  for(const [,b] of list){
    const x0=b.x-b.w/2,x1=b.x+b.w/2,z0=b.z-b.d/2,z1=b.z+b.d/2,h=b.h;
    const sideX=S.x<b.x?x0:x1,shade=sc.night?'#1d2027':b.col;
    polygon(c,[[sideX,0,z0],[sideX,0,z1],[sideX,h,z1],[sideX,h,z0]],sc.night?'#16191f':shadeOf(b.col,.82));
    const faceZ=S.z<b.z?z0:z1;
    polygon(c,[[x0,0,faceZ],[x1,0,faceZ],[x1,h,faceZ],[x0,h,faceZ]],shade);
    if(S.h+EYE>h)polygon(c,[[x0,h,z0],[x1,h,z0],[x1,h,z1],[x0,h,z1]],sc.night?'#2a2d33':b.roof);
    if(sc.night&&b.win){const p=point(b.x,h*.6,faceZ);if(p){c.fillStyle='rgba(255,210,120,.85)';const s=Math.max(1,Math.min(8,b.w*C.f/p[2]*.6));c.fillRect(p[0]-s/2,p[1]-1,s,Math.max(1,s*.25));}}
  }
}
function shadeOf(hex,k){const n=parseInt(hex.slice(1),16);return `rgb(${(n>>16&255)*k|0},${(n>>8&255)*k|0},${(n&255)*k|0})`;}
function cityLights(c,sc){
  for(const [x,z,col] of sc.lights){const p=point(x,0,z);if(!p||p[2]>14000)continue;const r=Math.max(1,Math.min(3,700/p[2]));c.fillStyle=col;c.fillRect(p[0],p[1],r,r);}
}
function clouds(c,sc,w){
  const sp=sprites(),list=[];
  const cl=F.lite?sc.clouds.filter((_,i)=>i%2===0):sc.clouds;
  for(const k of cl){cam(k.x,k.y,k.z);if(P3[2]<NEAR*20||P3[2]>40000)continue;list.push([P3[2],k,P3[0],P3[1]]);}
  if(w.cell){cam(w.cell.x,0,w.cell.z);if(P3[2]>NEAR*40)list.push([P3[2],{cell:true,s:w.cell.r*1.8},P3[0],P3[1]]);}
  list.sort((a,b)=>b[0]-a[0]);
  const maxW=F.L.view.w*2.6;
  for(const [z,k,x,y] of list){
    if(k.cell){
      const wd=Math.min(maxW*2,k.s*C.f/z),ht=wd*1.5,X=sx(x,z)-wd/2,Y=sy(y,z)-ht;
      c.globalAlpha=sc.night?.75:1;c.drawImage(sp.cell,X,Y+ht*.06,wd,ht);c.globalAlpha=1;
      if(F.flash>F.time&&!still()){c.fillStyle='rgba(255,255,255,.55)';c.fillRect(X+wd*.3,Y+ht*.35,wd*.4,ht*.4);}
      continue;
    }
    const wd=k.s*C.f/z;if(wd<4||wd>maxW)continue;
    c.globalAlpha=sc.night?.35:.9;c.drawImage(sp.clouds[k.k],sx(x,z)-wd/2,sy(y,z)-wd/4,wd,wd/2);c.globalAlpha=1;
  }
}
/** Rain on the glass, the wipers, a lightning flash, low cloud and fog, and the inside of a cell. */
function weatherFx(c,V,sc,w){
  // inside a cloud layer / the low cloud on a no-runway day / fog
  let fog=0;
  if(w.base&&S.h>w.base)fog=clamp((S.h-w.base)/25,0,.94);
  if(w.vis<5000)fog=Math.max(fog,clamp(1-w.vis/5000,0,.85)*(S.h>20?1:.8));
  if(F.phase==='cell'&&S.shake>.9)fog=Math.max(fog,.82);
  for(const k of (F.scene?.clouds||[]))if(Math.abs(S.h-k.y)<k.s*.18&&Math.abs(S.x-k.x)<k.s*.5&&Math.abs(S.z-k.z)<k.s*.5)fog=Math.max(fog,.8);
  if(fog>.01){c.fillStyle=sc.night?`rgba(30,36,48,${fog})`:`rgba(205,212,220,${fog})`;c.fillRect(V.x,V.y,V.w,V.h);}
  if(w.storm||w.cell||F.phase==='cell'){if(!still()&&Math.random()<.004)F.flash=F.time+.12;if(F.flash>F.time&&!still()){c.fillStyle='rgba(255,255,255,.25)';c.fillRect(V.x,V.y,V.w,V.h);}}
  const rain=(w.rain||0)+(F.phase==='cell'&&S.shake>.5?.8:0);
  if(rain>0&&!S.ground||rain>0&&S.V>2){
    const n=F.lite?18:46,r=rngOf('rain'+Math.floor(F.time*14));
    c.strokeStyle='rgba(220,230,245,.55)';c.lineWidth=1.2;c.beginPath();
    for(let i=0;i<n*rain;i++){const x=r()*V.w,y=r()*V.h,l=6+r()*10;c.moveTo(x,y);c.lineTo(x-l*.3,y+l);}c.stroke();
    // drops sit on the glass until a wiper stroke takes them
    if(F.drops.length<(F.lite?30:70)&&Math.random()<rain*.9)F.drops.push([Math.random()*V.w,Math.random()*V.h*.92,1.5+Math.random()*2.5]);
    if(w.wipers!==false){F.wiper=(F.wiper+.016*2.2)%2;const a=(F.wiper<1?F.wiper:2-F.wiper)*Math.PI*.85+Math.PI*.075,cx=V.w*.5,cy=V.h+20;
      const ex=cx-Math.cos(a)*V.h*1.05,ey=cy-Math.sin(a)*V.h*1.05;
      F.drops=F.drops.filter(d=>{const s=(d[0]-cx)*(ey-cy)-(d[1]-cy)*(ex-cx);return Math.abs(s)/Math.hypot(ex-cx,ey-cy)>14;});
      c.strokeStyle='#15181d';c.lineWidth=4;c.beginPath();c.moveTo(cx,cy);c.lineTo(ex,ey);c.stroke();}
    c.fillStyle='rgba(225,235,250,.5)';for(const d of F.drops){c.beginPath();c.arc(d[0],d[1],d[2],0,Math.PI*2);c.fill();}
  }else if(F.drops.length)F.drops.length=0;
}
function frameOfWindow(c,V){
  c.fillStyle='#1b2027';
  c.beginPath();c.moveTo(0,0);c.lineTo(V.w*.07,0);c.lineTo(V.w*.025,V.h);c.lineTo(0,V.h);c.closePath();c.fill();
  c.beginPath();c.moveTo(V.w,0);c.lineTo(V.w*.93,0);c.lineTo(V.w*.975,V.h);c.lineTo(V.w,V.h);c.closePath();c.fill();
  c.fillRect(0,0,V.w,6);
  // the glareshield
  c.beginPath();c.moveTo(0,V.h);c.lineTo(0,V.h-16);c.quadraticCurveTo(V.w/2,V.h-30,V.w,V.h-16);c.lineTo(V.w,V.h);c.closePath();c.fill();
}

/* ---------------------------------------------------------------- the panel */
function panel(c){
  const L=F.L,P=L.panel,W=F.W,H=F.H;
  c.fillStyle='#232a33';c.fillRect(0,P.y,W,H-P.y);
  let g=c.createLinearGradient(0,P.y,0,P.y+14);g.addColorStop(0,'#11151a');g.addColorStop(1,'#232a33');c.fillStyle=g;c.fillRect(0,P.y,W,14);
  const pw=Math.min(W-16,L.tall?W-16:480),ph=P.h-34,px=(W-pw)/2,py=P.y+8;
  pfd(c,px,py,pw,ph);
  // a line of small readouts under the attitude: throttle, wind, who flies, the gear
  const y=py+ph+17;
  c.font='600 12px system-ui,-apple-system,sans-serif';c.textBaseline='middle';
  const thr=Math.round(S.T*100),wind=Math.round(Math.abs(F.wx?.cw||0)/KT);
  c.fillStyle='#9fb0c2';c.textAlign='left';c.fillText(`${tr('CẦN GA')} ${thr}%`,px+4,y);
  const bx=px+4+c.measureText(`${tr('CẦN GA')} 100%`).width+6;c.fillStyle='#3d4a59';c.fillRect(bx,y-4,40,8);c.fillStyle=thr>85?'#f0b44c':'#6fd38a';c.fillRect(bx,y-4,40*S.T,8);
  c.textAlign='center';c.fillStyle=wind>28?'#ff7a6b':'#9fb0c2';c.fillText(wind?`${tr('GIÓ')} ${(F.wx?.cw||0)>0?'→':'←'} ${wind} kt`:tr('GIÓ nhẹ'),px+pw*.5,y);
  c.textAlign='right';c.fillStyle=S.ap?'#6fd38a':'#d6dde6';c.fillText(S.ap?tr('LÁI TỰ ĐỘNG'):tr('BẠN CẦM LÁI'),px+pw-4,y);
}
function pfd(c,x,y,w,h){
  const R=8;c.fillStyle='#07090c';roundRect(c,x,y,w,h,R);c.fill();
  const tw=Math.max(46,Math.min(62,w*.15)),aw=w-tw*2-12,ax=x+tw+6,ay=y+4,ah=h-30,acx=ax+aw/2,acy=ay+ah/2;
  const ppd=ah/36;
  // attitude
  c.save();roundRect(c,ax,ay,aw,ah,6);c.clip();
  c.translate(acx,acy);c.rotate(-S.ph);
  const off=S.th/D2R*ppd,big=aw*2;
  c.fillStyle='#2e7fd0';c.fillRect(-big,-big+off,big*2,big);c.fillStyle='#8a5a2b';c.fillRect(-big,off,big*2,big);
  c.strokeStyle='#fff';c.lineWidth=1.5;c.beginPath();c.moveTo(-big,off);c.lineTo(big,off);c.stroke();
  c.font='600 10px system-ui,sans-serif';c.fillStyle='#fff';c.textAlign='center';c.textBaseline='middle';
  for(let p=-20;p<=20;p+=5){if(!p)continue;const yy=off-p*ppd,l=p%10?aw*.1:aw*.2;c.beginPath();c.moveTo(-l,yy);c.lineTo(l,yy);c.stroke();if(!(p%10)){c.fillText(String(Math.abs(p)),-l-10,yy);c.fillText(String(Math.abs(p)),l+10,yy);}}
  c.restore();
  // bank scale and pointer
  c.save();c.translate(acx,acy);c.strokeStyle='#fff';c.lineWidth=1.5;const rr=ah*.42;
  for(const a of [-45,-30,-20,-10,0,10,20,30,45]){const t=(a-90)*D2R,l=a%30?5:9;c.beginPath();c.moveTo(Math.cos(t)*rr,Math.sin(t)*rr);c.lineTo(Math.cos(t)*(rr+l),Math.sin(t)*(rr+l));c.stroke();}
  c.rotate(-S.ph);c.fillStyle='#fff';c.beginPath();c.moveTo(0,-rr+1);c.lineTo(-5,-rr+9);c.lineTo(5,-rr+9);c.closePath();c.fill();c.restore();
  // flight director: magenta bars, where to put the nose and the wings
  if(F.fd&&!S.ap&&['takeoff','cell','approach'].includes(F.phase)){
    const d=director(),dy=clamp((S.th-d.th)/D2R*ppd,-ah*.42,ah*.42),dx=clamp((d.ph-S.ph)/D2R*2.4,-aw*.42,aw*.42);
    c.strokeStyle='#ff4fd8';c.lineWidth=3;c.beginPath();c.moveTo(acx-aw*.28,acy+dy);c.lineTo(acx+aw*.28,acy+dy);c.moveTo(acx+dx,acy-ah*.32);c.lineTo(acx+dx,acy+ah*.32);c.stroke();
  }
  // the aircraft
  c.strokeStyle='#ffd23d';c.lineWidth=4;c.beginPath();c.moveTo(acx-aw*.3,acy);c.lineTo(acx-aw*.1,acy);c.lineTo(acx-aw*.1,acy+7);c.moveTo(acx+aw*.3,acy);c.lineTo(acx+aw*.1,acy);c.lineTo(acx+aw*.1,acy+7);c.stroke();
  c.fillStyle='#ffd23d';c.fillRect(acx-3,acy-3,6,6);
  // glide path and localizer on the approach
  if(['approach','rollout'].includes(F.phase)&&S.z<AIM){
    const j=judge();const gy=acy-clamp(j.dev,-2.4,2.4)*ah*.16,gx=acx+clamp(j.loc,-2.4,2.4)*aw*.16;
    c.fillStyle='#fff';for(const k of [-2,-1,1,2]){c.beginPath();c.arc(ax+aw-8,acy+k*ah*.16,2.2,0,Math.PI*2);c.fill();c.beginPath();c.arc(acx+k*aw*.16,ay+ah-8,2.2,0,Math.PI*2);c.fill();}
    diamond(c,ax+aw-8,acy+(acy-gy),'#ff4fd8');diamond(c,gx,ay+ah-8,'#ff4fd8');
  }
  // radio height near the ground
  const hft=S.h/FT;
  if(hft<2500&&!S.ap){c.font='700 14px system-ui,sans-serif';c.fillStyle='#6fd38a';c.textAlign='center';c.fillText(String(Math.round(hft/10)*10),acx,ay+ah-24);}
  // speed tape (left)
  const kt=S.V/KT,bug=F.phase==='takeoff'?VR:F.phase==='approach'?VREF:null;
  tape(c,x+4,ay,tw,ah,kt,10,3,v=>String(Math.round(v)),bug,kt<100&&!S.ground&&F.phase!=='climb'?'#ff5a4f':'#fff',true);
  // altitude tape (right)
  tape(c,x+w-tw-4,ay,tw,ah,hft,100,.32,v=>String(Math.round(v)),null,'#fff',false);
  c.font='600 10px system-ui,sans-serif';c.fillStyle='#9fb0c2';c.textAlign='center';
  const vs=Math.round(S.vs/FT*60/50)*50;if(Math.abs(vs)>=100&&!S.ap)c.fillText((vs>0?'+':'')+vs,x+w-tw/2-4,ay+ah+8);
  // heading strip
  const hdg=((RWY_HDG+S.psi/D2R)%360+360)%360,hy=y+h-22,hw=aw;
  c.save();c.beginPath();c.rect(ax,hy,hw,20);c.clip();c.fillStyle='#1a2027';c.fillRect(ax,hy,hw,20);
  c.strokeStyle='#cfd6de';c.fillStyle='#cfd6de';c.lineWidth=1;c.font='600 10px system-ui,sans-serif';c.textAlign='center';c.textBaseline='middle';
  for(let d=Math.floor((hdg-30)/5)*5;d<=hdg+30;d+=5){const xx=acx+(d-hdg)*3.2;c.beginPath();c.moveTo(xx,hy);c.lineTo(xx,hy+(d%10?4:7));c.stroke();if(d%30===0)c.fillText(String(((d%360)+360)%360/10|0).padStart(2,'0'),xx,hy+14);}
  c.restore();
  c.fillStyle='#000';c.strokeStyle='#fff';roundRect(c,acx-18,hy-1,36,14,3);c.fill();c.stroke();c.fillStyle='#fff';c.textAlign='center';c.font='700 11px system-ui,sans-serif';c.fillText(String(Math.round(hdg)).padStart(3,'0'),acx,hy+6);
}
function diamond(c,x,y,col){c.fillStyle=col;c.beginPath();c.moveTo(x,y-5);c.lineTo(x+4,y);c.lineTo(x,y+5);c.lineTo(x-4,y);c.closePath();c.fill();}
function tape(c,x,y,w,h,v,step,ppu,fmt,bug,col,left){
  c.save();c.beginPath();c.rect(x,y,w,h);c.clip();c.fillStyle='#2c333d';c.fillRect(x,y,w,h);
  const cy=y+h/2,span=h/2/ppu;
  c.strokeStyle='#cfd6de';c.fillStyle='#cfd6de';c.lineWidth=1;c.font='600 10px system-ui,sans-serif';c.textBaseline='middle';c.textAlign=left?'right':'left';
  for(let k=Math.floor((v-span)/step)*step;k<=v+span;k+=step){if(k<0)continue;const yy=cy-(k-v)*ppu;
    c.beginPath();left?(c.moveTo(x+w,yy),c.lineTo(x+w-6,yy)):(c.moveTo(x,yy),c.lineTo(x+6,yy));c.stroke();
    if(k%(step*2)===0)c.fillText(fmt(k),left?x+w-9:x+9,yy);}
  if(bug!=null){const by=clamp(cy-(bug-v)*ppu,y+4,y+h-4);c.fillStyle='#ff4fd8';c.beginPath();if(left){c.moveTo(x+w,by);c.lineTo(x+w-8,by-5);c.lineTo(x+w-8,by+5);}else{c.moveTo(x,by);c.lineTo(x+8,by-5);c.lineTo(x+8,by+5);}c.closePath();c.fill();}
  c.restore();
  c.fillStyle='#000';c.strokeStyle=col;c.lineWidth=1.5;roundRect(c,x+1,cy-10,w-2,20,3);c.fill();c.stroke();
  c.fillStyle=col;c.font='700 13px system-ui,sans-serif';c.textAlign='center';c.textBaseline='middle';c.fillText(fmt(v),x+w/2,cy+1);
}
function roundRect(c,x,y,w,h,r){c.beginPath();c.moveTo(x+r,y);c.arcTo(x+w,y,x+w,y+h,r);c.arcTo(x+w,y+h,x,y+h,r);c.arcTo(x,y+h,x,y,r);c.arcTo(x,y,x+w,y,r);c.closePath();}
