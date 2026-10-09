/** 🎆 Pháo hoa cả phố: the show every online player sees (owner 08/10: "phải có bắn toàn server cho mọi người thấy chứ
 * k phải là chỉ có chữ nhé. Và có thông báo dài luôn").
 *
 * The live service (live/fireworks.py) sends `fireworks {id, size, name, wish, ago}` to every open page when someone
 * buys a show in Mua sắm → 🎆 Mạnh Thường Quân (game/lux.py); a page that connects just after gets it in its welcome
 * (`fw`). This draws bursts over the page on a canvas (pointer-events: none: play goes on underneath) and shows a
 * banner at the top: who, which size, their wish (a fixed list, game/lux_content.py FW_WISHES), a ✕ and a
 * "🎆 Bắn pháo hoa" button that opens the shop on it (#274 "bắn pháo hoa chỗ nào z?"). Bigger sizes: more rockets,
 * longer, a finale. A blocked giver arrives without name and wish (the sky only).
 *
 * Never in the way of play (#299 #300 #301, 09/10):
 *  - The full show plays only on an open screen: the workplace with no sheet open, or the 🗺️ home sheet. In any other
 *    dialog (a fair stall like phóng dao, a work task, jail, a menu) the page shows a small chip "🎆 X đang bắn pháo
 *    hoa" with "Xem" instead; a show on screen ends by itself when such a dialog opens.
 *  - Its layers live inside the topmost modal dialog when one is open (a top-layer popover there). A popover outside
 *    the open modal dialog is inert: a tap on its ✕ fell through to the dialog's backdrop, and the fair closes on a
 *    backdrop tap, so "bấm x thì thoát hoạt động". Taps on the banner and the chip stop at them; Escape during a show
 *    closes the show only. Nothing takes focus.
 *  - ⚙️ Cài đặt → Cách chơi → 🎆 Hiệu ứng pháo hoa: Bật (default) / Chỉ báo nhỏ (the chip only) / Tắt. Kept on this
 *    device (localStorage: the server's settings refuse unknown keys, game/engine.py). The buyer always sees their own.
 *
 * prefers-reduced-motion (or the game's Giảm chuyển động): a few slow blooms that fade in place, no rising rockets, no
 * trails, no flash. Silent (no recording fits; the game's audio must be CC0). Shows queue (at most QUEUE_MAX waiting),
 * one id plays once per tab. */
import {escapeHTML as esc} from '../icons.js';

const SIZES={
  nho:{verb:'vừa bắn pháo hoa nhỏ mừng cả phố!',sky:'Pháo hoa nhỏ đang nở trên phố!',show:6,banner:9,rockets:8,sparks:28,r:.2,finale:0},
  lon:{verb:'vừa bắn pháo hoa lớn mừng cả phố!',sky:'Pháo hoa lớn đang nở trên phố!',show:9,banner:12,rockets:16,sparks:36,r:.26,finale:5},
  dai_tiec:{verb:'vừa mở đại tiệc pháo hoa mừng cả phố!',sky:'Đại tiệc pháo hoa trên phố!',show:13,banner:15,rockets:28,sparks:42,r:.3,finale:10},
};
/** Names the server writes for a guest or an anonymous giver: words to translate, not a player's name. */
const PLAIN_NAMES=new Set(['Một người hàng xóm','Một người hàng xóm giấu tên','Bạn']);
const COLORS=['#ff5d73','#ffd25e','#6fe3a8','#6ec8ff','#c792ff','#ff9f5a','#ffffff','#ff7ad9'];
const QUEUE_MAX=6,SPARK_MAX=1200,SEEN_KEY='mnl-fw-seen',MODE_KEY='mnl.fw.mode',CHIP_SECS=8,MINE_MS=30000;
/** ⚙️ Hiệu ứng pháo hoa: [id, label]. */
export const FW_MODES=[['on','Bật'],['small','Chỉ báo nhỏ'],['off','Tắt']];
const S={env:null,cur:null,queue:[],seen:new Set(),chip:null,mine:null};
try{for(const k of JSON.parse(sessionStorage.getItem(SEEN_KEY)||'[]'))if(typeof k==='string')S.seen.add(k);}catch{/* storage blocked */}

const reduced=()=>{
  try{if(document.documentElement?.classList?.contains('reduce-motion')||document.body?.classList?.contains('reduce-motion')||S.env?.api?.state?.settings?.reduceMotion)return true;}catch{/* no page */}
  try{return matchMedia('(prefers-reduced-motion: reduce)').matches;}catch{return false;}
};
const sizeOf=id=>SIZES[id]||SIZES.lon;
function remember(id){
  S.seen.add(id);
  try{sessionStorage.setItem(SEEN_KEY,JSON.stringify([...S.seen].slice(-8)));}catch{/* storage blocked */}
}

/** This device's choice: 'on' | 'small' | 'off' (anything else, or storage blocked: 'on'). */
export function fwMode(){
  if(S.modeHere)return S.modeHere;   // chosen in this tab (storage may be blocked)
  try{const v=localStorage.getItem(MODE_KEY);return FW_MODES.some(m=>m[0]===v)?v:'on';}catch{return 'on';}
}
export function setFwMode(v){
  if(!FW_MODES.some(m=>m[0]===v))return false;
  try{localStorage.setItem(MODE_KEY,v);}catch{/* storage blocked: this tab only */}
  S.modeHere=v;
  if(v!=='on'&&S.cur&&!S.cur.mine&&!S.cur.forced)finish(S.cur,true);
  if(v==='off')hideChip();
  return true;
}
const mode=fwMode;

/** What to show: the buyer's own show always plays; otherwise the setting, and never the full show over a game. */
export function howToShow({mode='on',busy=false,mine=false}={}){
  if(mine)return 'full';
  if(mode==='off')return 'none';
  return mode==='small'||busy?'chip':'full';
}

/** The topmost open modal dialog (taps reach only it and what is inside it), or null. */
export function topModal(doc=globalThis.document){
  if(!doc?.querySelectorAll)return null;
  const open=[...doc.querySelectorAll('dialog[open]')].filter(d=>{try{return d.matches(':modal');}catch{return true;}});
  if(open.length<2)return open[0]||null;
  try{   // several stacked: the one a tap in the middle reaches (the others are inert under it)
    const hit=doc.elementFromPoint(Math.round((globalThis.innerWidth||360)/2),Math.round((globalThis.innerHeight||640)/2))?.closest?.('dialog[open]');
    if(hit&&open.includes(hit))return hit;
  }catch{/* no layout */}
  return open[open.length-1];
}
/** An open screen: no dialog, or the 🗺️ home sheet (the town map, the list). Anything else is play in progress. */
export function idleScreen(top,env=S.env){
  if(globalThis.document?.fullscreenElement)return false;
  return !top||(top.id==='sheet'&&env?.ui?.view==='home');
}
const busyNow=()=>!idleScreen(topModal());

/** The buyer's page: the next show of this size coming back from the server is theirs (lux.js after a purchase). */
export function markMine(size){S.mine=size?{size,until:Date.now()+MINE_MS}:null;}   // null: the purchase was refused
function takeMine(f){
  const m=S.mine;if(!m||Date.now()>m.until||m.size!==f.size)return false;
  S.mine=null;return true;
}

/** A `fireworks` frame (or a welcome's `fw`): play it now, after the one on screen, or a chip. */
export function onFireworks(env,f){
  S.env=env||S.env;
  if(!f||typeof f.id!=='string'||!f.id||S.seen.has(f.id)||S.cur?.f.id===f.id||S.queue.some(x=>x.id===f.id))return;
  const z=sizeOf(f.size),ago=Math.max(0,Number(f.ago)||0);
  if(ago>=z.banner-3)return;   // over already
  remember(f.id);
  const g={...f,ago,mine:f.mine===true||takeMine(f)};
  if(S.cur&&!S.cur.done&&howToShow({mode:mode(),busy:busyNow(),mine:g.mine})==='full'){
    if(S.queue.length>=QUEUE_MAX)S.queue.shift();S.queue.push({...g,ago:0});return;
  }
  route(g);
}
/** The buyer's own page when the live socket is not open (no broadcast will come back to it). */
export function playLocal(env,size,wish=''){
  S.env=env||S.env;onFireworks(env,{id:`local-${Date.now()}`,size,name:'Bạn',wish,ago:0,mine:true});
}
function route(f){
  const how=howToShow({mode:mode(),busy:busyNow(),mine:f.mine});
  if(how==='full')play(f);
  else if(how==='chip')chip(f);
}

function css(){
  if(document.querySelector('style[data-fw-css]'))return;
  const s=document.createElement('style');s.dataset.fwCss='';
  s.textContent=`.fw-root{position:fixed;inset:0;width:100%;height:100%;max-width:none;max-height:none;margin:0;padding:0;border:0;background:transparent;overflow:hidden;pointer-events:none;z-index:2147482000;color:inherit}
.fw-root::backdrop,.fw-chip::backdrop{display:none}
.fw-tint{position:absolute;inset:0;pointer-events:none;background:linear-gradient(180deg,rgba(14,14,52,.5) 0%,rgba(22,18,70,.4) 40%,rgba(28,20,74,.18) 66%,rgba(28,20,74,0) 86%);opacity:0;transition:opacity .9s ease}
.fw-root.on .fw-tint{opacity:1}
.fw-root canvas{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.fw-banner{position:absolute;left:50%;top:calc(env(safe-area-inset-top,0px) + 12px);transform:translate(-50%,-14px);opacity:0;transition:opacity .45s ease,transform .45s ease;
  width:min(480px,calc(100vw - 24px));box-sizing:border-box;display:flex;align-items:center;gap:10px;padding:9px 8px 10px 12px;border-radius:18px;pointer-events:auto;
  background:linear-gradient(135deg,#3b2468,#7a2f63 60%,#b5532f);color:#fff;box-shadow:0 10px 30px rgba(20,8,40,.45),inset 0 0 0 1px rgba(255,230,160,.35);
  font:600 14px/1.35 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.fw-root.on .fw-banner{opacity:1;transform:translate(-50%,0)}
.fw-root.out .fw-banner{opacity:0;transform:translate(-50%,-14px)}
.fw-ico{font-size:28px;line-height:1;flex:none;animation:fw-pop 1.6s ease-in-out infinite}
.fw-text{flex:1;min-width:0}
.fw-text b{color:#ffe08a;font-weight:800;overflow-wrap:anywhere}
.fw-wish{display:block;margin-top:2px;font-weight:600;font-style:italic;color:#ffeccc}
.fw-acts{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.fw-go,.fw-calm{display:inline-block;padding:5px 11px;border:0;border-radius:99px;background:#ffd25e;color:#4a2412;font-family:inherit;font-weight:700;font-size:13px;line-height:1.2;cursor:pointer}
.fw-calm{background:rgba(255,255,255,.16);color:#fff}
.fw-x{flex:none;align-self:flex-start;width:32px;height:32px;border:0;border-radius:50%;background:rgba(255,255,255,.16);color:#fff;font:700 16px/32px system-ui,sans-serif;cursor:pointer;padding:0}
.fw-x:focus-visible,.fw-go:focus-visible,.fw-calm:focus-visible,.fw-chip button:focus-visible{outline:2px solid #fff;outline-offset:2px}
.fw-bar{position:absolute;left:14px;right:14px;bottom:4px;height:3px;border-radius:2px;background:rgba(255,255,255,.22);overflow:hidden}
.fw-bar i{display:block;height:100%;background:#ffd25e;transform-origin:left;animation:fw-bar linear forwards}
.fw-big .fw-banner{font-size:15px;padding:11px 8px 12px 14px}
.fw-big .fw-ico{font-size:32px}
.fw-chip{position:fixed;inset:auto;left:calc(env(safe-area-inset-left,0px) + 10px);top:calc(env(safe-area-inset-top,0px) + 8px);right:auto;bottom:auto;margin:0;z-index:2147482001;
  box-sizing:border-box;max-width:min(360px,calc(100vw - 84px));display:flex;align-items:center;gap:6px;padding:4px 4px 4px 10px;border:0;border-radius:99px;overflow:hidden;
  background:rgba(59,36,104,.92);color:#fff;box-shadow:0 4px 14px rgba(20,8,40,.3);font:600 13px/1.3 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;pointer-events:auto;
  opacity:0;transform:translateY(-8px);transition:opacity .3s ease,transform .3s ease}
.fw-chip.on{opacity:1;transform:none}
.fw-chip-t{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fw-chip-t b{color:#ffe08a}
.fw-chip button{flex:none;border:0;border-radius:99px;font:700 12px/1 system-ui,sans-serif;cursor:pointer;padding:6px 10px;background:#ffd25e;color:#4a2412}
.fw-chip .fw-chip-x{width:26px;height:26px;padding:0;background:rgba(255,255,255,.16);color:#fff}
@keyframes fw-pop{0%,100%{transform:scale(1)}50%{transform:scale(1.18) rotate(-6deg)}}
@keyframes fw-bar{from{transform:scaleX(1)}to{transform:scaleX(0)}}
@media (prefers-reduced-motion:reduce){.fw-ico{animation:none}.fw-banner{transition:opacity .45s ease}.fw-chip{transition:opacity .3s ease;transform:none}}
.reduce-motion .fw-ico{animation:none}`;
  document.head.append(s);
}

/** Into the top layer, inside the modal dialog that takes taps (never an inert layer over it), or the page. */
function mount(el,host){
  host.append(el);
  if(typeof el.showPopover==='function'){try{el.popover='manual';el.showPopover();}catch{/* fixed + z-index */}}
}
function unmount(el){
  try{el.hidePopover?.();}catch{/* not shown as one */}
  el.remove();
}
/** Taps on the banner and the chip stop there: the dialog under them (its backdrop-closes, its sheet drag) never sees them. */
function own(el){
  for(const t of ['click','pointerdown','pointerup','mousedown','touchstart','touchend'])el.addEventListener(t,e=>e.stopPropagation());
}

/** What the giver may do next: the shop on fireworks (story mode only, where Mua sắm exists). */
const canShoot=()=>{const j=S.env?.api?.state?.journey;return Boolean(j?.story&&j.lux&&S.env?.act);};

function who(f){
  const name=String(f.name||'').trim();
  return name?(PLAIN_NAMES.has(name)?`<b>${esc(name)}</b>`:`<b data-no-translate>${esc(name)}</b>`):'';
}
function banner(f,z,secs){
  const wish=String(f.wish||'').trim(),name=who(f);
  const line=name?`${name} <span>${esc(z.verb)}</span>`:`<span>${esc(z.sky)}</span>`;
  const go=canShoot()&&f.name!=='Bạn'?'<button type="button" class="fw-go" data-fw="go">🎆 Bắn pháo hoa</button>':'';
  const calm=f.mine||f.forced?'':'<button type="button" class="fw-calm" data-fw="calm">🔕 Chỉ báo nhỏ</button>';
  return `<div class="fw-banner" role="status" aria-live="polite"><span class="fw-ico" aria-hidden="true">🎆</span>
    <div class="fw-text"><div>${line}</div>${wish?`<q class="fw-wish">${esc(wish)}</q>`:''}${go||calm?`<div class="fw-acts">${go}${calm}</div>`:''}</div>
    <button type="button" class="fw-x" data-fw="x" aria-label="Đóng pháo hoa" title="Đóng pháo hoa">✕</button><span class="fw-bar" aria-hidden="true"><i style="animation-duration:${secs}s"></i></span></div>`;
}

/* ---- the small chip (a game or a sheet is open, or "Chỉ báo nhỏ") ---- */
function chip(f){
  css();hideChip();
  if(globalThis.document?.fullscreenElement)return;   // a fullscreen game: nothing at all
  const el=document.createElement('div');el.className='fw-chip';el.setAttribute('role','status');el.setAttribute('aria-live','polite');
  const name=who(f),line=name?`${name} <span>đang bắn pháo hoa</span>`:'<span>Đang có pháo hoa trên phố</span>';
  el.innerHTML=`<span aria-hidden="true">🎆</span><span class="fw-chip-t">${line}</span><button type="button" class="fw-chip-go" data-fw="see">Xem</button>`
    +'<button type="button" class="fw-chip-x" data-fw="x" aria-label="Đóng" title="Đóng">✕</button>';
  own(el);
  const c=S.chip={el,f,timer:0};
  el.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-fw]');if(!b)return;
    hideChip(c);
    if(b.dataset.fw==='see'){if(S.cur)finish(S.cur,true,false);play({...f,ago:0,forced:true});}
  });
  mount(el,topModal()||document.body);
  requestAnimationFrame(()=>el.classList.add('on'));
  c.timer=setTimeout(()=>hideChip(c),CHIP_SECS*1000);
}
function hideChip(c=S.chip){
  if(!c)return;clearTimeout(c.timer);
  if(S.chip===c)S.chip=null;
  c.el.classList.remove('on');setTimeout(()=>unmount(c.el),320);
}

/* ---- the show ---- */
function play(f){
  css();
  const z=sizeOf(f.size),calm=reduced(),ago=f.ago||0;
  const root=document.createElement('div');root.className='fw-root'+(f.size==='dai_tiec'?' fw-big':'');
  const bannerSecs=Math.max(5,z.banner-ago),showSecs=Math.max(3,z.show-ago);
  root.innerHTML=`<div class="fw-tint"></div><canvas aria-hidden="true"></canvas>${banner(f,z,bannerSecs)}`;
  const top=topModal(),host=top||document.body;
  mount(root,host);
  const cur=S.cur={f,root,host,top,forced:!!f.forced,mine:!!f.mine,raf:0,timers:[],watch:0,done:false,keys:null};
  own(root);
  root.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-fw]');if(!b)return;
    if(b.dataset.fw==='go'){finish(cur,true);S.env?.act?.('luxFw');}
    else if(b.dataset.fw==='calm'){setFwMode('small');finish(cur,true);S.env?.toast?.('🎆 Từ giờ chỉ báo nhỏ. Đổi lại ở Cài đặt → Cách chơi.','hint');}
    else finish(cur,true);   // ✕: the show only
  });
  // Escape during the show closes the show, not the dialog under it.
  cur.keys=e=>{if((e.key==='Escape'||e.key==='Esc')&&!cur.done){e.preventDefault();e.stopPropagation();finish(cur,true);}};
  document.addEventListener('keydown',cur.keys,true);
  requestAnimationFrame(()=>root.classList.add('on'));
  sky(cur,root.querySelector('canvas'),z,showSecs,calm,ago);
  cur.timers.push(setTimeout(()=>root.querySelector('.fw-tint')?.style.setProperty('opacity','0'),showSecs*1000));
  cur.timers.push(setTimeout(()=>finish(cur,false),bannerSecs*1000));
  cur.watch=setInterval(()=>watch(cur),400);
}
/** A show on screen while the player moves on: a game or a sheet opening ends it; back on an open screen it follows. */
export function watch(cur=S.cur){
  if(!cur||cur.done)return;
  if(!cur.root.isConnected){finish(cur,true);return;}
  const top=topModal();
  // "Xem" from the chip (or the buyer's own show) stays over the dialog it was asked in; anything else gives way
  if(!idleScreen(top)&&!((cur.forced||cur.mine)&&top===cur.top)){finish(cur,true);return;}
  const host=top||document.body;
  if(host!==cur.host){unmount(cur.root);mount(cur.root,host);cur.host=host;}
}

function finish(cur,quick,next=true){
  if(cur.done)return;cur.done=true;
  for(const t of cur.timers)clearTimeout(t);
  clearInterval(cur.watch);cancelAnimationFrame(cur.raf);
  if(cur.keys)document.removeEventListener('keydown',cur.keys,true);
  cur.root.classList.add('out');cur.root.querySelector('.fw-tint')?.style.setProperty('opacity','0');
  const cv=cur.root.querySelector('canvas');if(cv)cv.style.cssText+=';transition:opacity .4s;opacity:0';
  if(S.cur===cur)S.cur=null;
  setTimeout(()=>{unmount(cur.root);
    if(!next||S.cur)return;
    const n=S.queue.shift();if(n)route(n);},quick?420:520);
}

/* ---- the sky ---- */
function plan(z,secs,calm,ago){
  // Rockets spread over the show (the last ~2.5 s left for the sparks to fall), a finale for the bigger sizes.
  const n=Math.max(2,Math.round(z.rockets*(calm?.35:1)*Math.min(1,secs/z.show))),span=Math.max(1,secs-2.6),out=[];
  for(let i=0;i<n;i++)out.push({t:(i+.3*Math.random())*span/n,kind:i%5===4?'willow':i%3===2?'ring':'peony'});
  const fin=calm?Math.ceil(z.finale/4):z.finale;
  if(fin&&secs>=z.show-1)for(let i=0;i<fin;i++)out.push({t:span-.9+Math.random()*.9,kind:i%2?'ring':'peony'});
  if(ago<.5&&!calm)out.unshift({t:.05,kind:'peony'});   // something right away
  return out.sort((a,b)=>a.t-b.t);
}

function sky(cur,cv,z,secs,calm,ago){
  const c=cv.getContext('2d');if(!c)return;
  const dpr=Math.min(1.5,window.devicePixelRatio||1);let W=0,H=0;
  const fit=()=>{W=window.innerWidth||360;H=window.innerHeight||640;cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);c.setTransform(dpr,0,0,dpr,0,0);c.lineCap='round';};
  fit();
  const rockets=plan(z,secs,calm,ago),sparks=[],flying=[];let next=0,start=0,last=0;
  const R=()=>Math.min(W,H*1.1)*z.r;
  // under the banner (it covers the top of a phone), never lower than the middle of the screen or so (the darker part)
  const top0=()=>{const b=cur.root.querySelector('.fw-banner');const r=b?.getBoundingClientRect?.();return r&&r.bottom>0?r.bottom:H*.08;};
  function burst(x,y,kind){
    const col=COLORS[(Math.random()*COLORS.length)|0],col2=COLORS[(Math.random()*COLORS.length)|0],n=calm?Math.round(z.sparks*.6):z.sparks,r=R()*(.75+Math.random()*.4);
    for(let i=0;i<n&&sparks.length<SPARK_MAX;i++){
      const a=i/n*Math.PI*2+Math.random()*.12,sp=(kind==='ring'?1:.35+Math.random()*.65)*r*(calm?.55:1);
      sparks.push({x,y,vx:Math.cos(a)*sp,vy:Math.sin(a)*sp,life:0,max:(kind==='willow'?2.6:1.7)+Math.random()*.5,col:kind==='willow'?'#ffd77a':i%3===0?col2:col,w:kind==='willow'?1.8:2.6,
        drag:kind==='willow'?1.6:2.4,g:kind==='willow'?40:70});
    }
    if(!calm)sparks.push({x,y,vx:0,vy:0,life:0,max:.3,flash:R()*.42});
  }
  function frame(ts){
    if(cur.done)return;
    if(!start){start=ts;last=ts;}
    const t=(ts-start)/1000,dt=Math.min(.05,(ts-last)/1000);last=ts;
    if(W!==window.innerWidth||H!==window.innerHeight)fit();
    while(next<rockets.length&&rockets[next].t<=t){
      const k=rockets[next++],top=Math.min(H*.4,top0()+R()*.55),x=W*(.12+Math.random()*.76),y=top+Math.random()*Math.max(20,H*.56-top);
      if(calm)burst(x,y,k.kind);else flying.push({x,y0:H+10,y,tx:x+(Math.random()-.5)*30,age:0,dur:.75+Math.random()*.35,kind:k.kind});
    }
    // fade what was drawn (trails), keeping the page visible under it
    c.globalCompositeOperation='destination-out';c.fillStyle=calm?'rgba(0,0,0,1)':'rgba(0,0,0,.24)';c.fillRect(0,0,W,H);
    c.globalCompositeOperation='source-over';
    for(let i=flying.length-1;i>=0;i--){
      const r=flying[i];r.age+=dt;const p=Math.min(1,r.age/r.dur),e=1-(1-p)*(1-p),y=r.y0+(r.y-r.y0)*e,x=r.x+(r.tx-r.x)*(1-e);
      c.fillStyle='#fff3c4';c.globalAlpha=1;c.beginPath();c.arc(x,y,2.2,0,Math.PI*2);c.fill();
      c.fillStyle='rgba(255,200,120,.55)';c.fillRect(x-1,y+3,2,12);
      if(p>=1){flying.splice(i,1);burst(x,y,r.kind);}
    }
    for(let i=sparks.length-1;i>=0;i--){
      const s=sparks[i];s.life+=dt;if(s.life>=s.max){sparks.splice(i,1);continue;}
      const a=1-s.life/s.max;
      if(s.flash){const r=s.flash*(1.2-a*.5),g=c.createRadialGradient(s.x,s.y,0,s.x,s.y,r);g.addColorStop(0,'rgba(255,250,225,.9)');g.addColorStop(.35,'rgba(255,220,150,.35)');g.addColorStop(1,'rgba(255,200,120,0)');
        c.globalAlpha=a;c.fillStyle=g;c.fillRect(s.x-r,s.y-r,r*2,r*2);continue;}
      const k=Math.exp(-s.drag*dt);s.vx*=k;s.vy=s.vy*k+s.g*dt;s.x+=s.vx*dt;s.y+=s.vy*dt;
      c.globalAlpha=calm?Math.min(1,s.life*3)*a:a;
      if(calm){const w=s.w*1.6;c.fillStyle=s.col;c.fillRect(s.x-w/2,s.y-w/2,w,w);continue;}
      // a short streak along the motion, a bright head; the last moments twinkle
      c.strokeStyle=s.col;c.lineWidth=s.w*(.7+a*.9);c.beginPath();c.moveTo(s.x-s.vx*.045,s.y-s.vy*.045);c.lineTo(s.x,s.y);c.stroke();
      if(a<.35&&Math.random()<.5)continue;
      c.fillStyle=a>.6?'#fffbe8':s.col;const w=s.w*(1+a);c.fillRect(s.x-w/2,s.y-w/2,w,w);
    }
    c.globalAlpha=1;
    if(t<secs+.5||sparks.length||flying.length)cur.raf=requestAnimationFrame(frame);
    else c.clearRect(0,0,W,H);
  }
  cur.raf=requestAnimationFrame(frame);
}
