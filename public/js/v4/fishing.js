/** 🎣 Câu cá (game/fishing.py is the authority, every number in game/fishing_content.py). A full-screen lake: one canvas
 * (sky, far shore, the water in the rod's zones Gần / Vừa / Xa / Sâu with distance buoys for the rod in hand, in perspective
 * so a 2 km cast lands by the horizon, the dock, the player, the line, the bobber, ripples, splashes, rain) and plain
 * elements over it: the HUD, the power meter, the cast's distance counter, the tension meter, the catch card,
 * and three stalls on the bank: 🎣 Quầy bán cần (rods, bait, baskets), 📖 Bảng bộ sưu tập (Sổ cá, 🐋 Cá lớn nhất,
 * 📖 Bộ sưu tập, the top 3 on the board) and 🐟 Quầy thu mua (the fish bag, the trader who sometimes haggles).
 *
 * A round: hold (the meter fills) and release, or just tap → jr_fish_cast {spot, power}: casting never fails (owner 24/10
 * "quăng dễ hơn … tầm quăng random"). The server picks how far it went (random over the rod's reach, the power only
 * nudging it), the zone, whether and when something bites (and what: never told here). The bobber flies while a counter
 * ticks the metres up ("🎯 1.234 m!", 🚀 past far_share of the rod's longest, 🏅 a new longest cast), splashes at `splash`, nibbles at `nib`, and at `bite` dips hard with "!", a big "Giật!" and a buzz, and a glowing
 * ring around the bobber (and a bar in the button) counts the rod's window down. A tap → jr_fish_hook {round, ms}: `ms` is
 * how long after this page drew the bite the player tapped (performance.now()), so a slow save or network never makes a
 * timely tap late. A tap during the nibbles only says "Chưa cắn đâu" (hook_scare of them; one more scares the fish:
 * {round, early}); on a rỉa mồi round (`gone`, nothing bites) a tap ends it as before. The fight is played here with what the hook answered (secs,
 * pull, dart, green zone width, `heavy`, a fated `snap_at`) by v4/fish-reel.js: hold to reel, release to ease; the green
 * is wide, the needle slow and drifting back toward it, the yellow reels in too (slower); only a long stay in the
 * flashing red snaps the line, a long slack lets the fish go. jr_fish_land {round, ok}: the server checks the time and
 * says what it was. The catch jumps out of the water and its card opens (🏆 a town record, 📖 a new species, 🏅 a best).
 *
 * 👥 Hồ câu đông vui (owner 24/10 "map câu cá nhiều người vào vẫn thấy được nhé … để ai câu lên con gì mình nhìn được ấy"):
 * with the live service on, everyone at the spot shares the lake (v4/fish-lake.js, live/fish_lake.py, no cap): each one
 * drawn as their character on the long boardwalk (my own too, instead of the old stick fisher), their casts, bites and
 * reels on the shared water, the fish they land leaping into their hands (only the server's word: after their
 * jr_fish_land committed), the 🎣 feed of the last catches, a big banner for 🟡 Huyền thoại / 🔴 Cổ đại, a tap on someone
 * for their mini card, 💬 bubbles to the people near, ◀ ▶ to look along a crowd. Without it: the single player's lake.
 *
 * Opened by app.js `fishing` (Khu phố), the outings' 🎣 Câu cá, the town map's leisure place and the island's 🎣 chip
 * (spot 'dao' with the trip). Old-Safari safe (scripts/check_old_safari.mjs), no library: one rAF loop while open. */
import {escapeHTML as esc} from '../icons.js';
import {stylesheet} from '../lazy.js';
import {fishSvg,drawFish,fmtKg,fmtLen,scaleSvg,RARITY_COLORS,TRO_BG,TRO_BG_NAMES} from './fish-art.js';
import {reelStart,reelStep,MID,RED} from './fish-reel.js';
import {createLake,drawLake,sprite,bubble} from './fish-lake.js';
import {posOf,spacing,figScale,screenX,extent,clampCam,offscreen,hitPeer,tierOf,feedLine,waterPoint,catchPose,panBy,glide,wheelPx,scrollOf,camAt,farFromMe} from './fish-lake-layout.js';
import {TYPING} from '../typing-tap.js';
import {drawRod,rodTipOf,rodLook,lineColor,rodSvg} from './fish-rod.js';
import {figure,lookOf,portrait,withWings} from './look.js';
import {avatar as hfAvatar} from './honour-frames.js';
import {chips as hnChips} from './honours.js';
import {nameAttrs as stName} from './style-tag.js';

const FILL=.9;               // s: the power meter fills, then stays full (a tap casts too)
const PERSP=.3;              // the lake's perspective: a buoy at PERSP × the view's depth sits half way to the horizon
const MARKS=[10,20,30,50,100,200,300,500,1000,1500,2000,3000,5000];   // m: the buoys, the ones that suit the rod in hand
const MEDAL=['🥇','🥈','🥉'];
const F={env:null,dlg:null,cv:null,ctx:null,raf:0,last:0,spot:'ho',trip:'',phase:'idle',pressing:false,c0:0,power:0,
  r:null,f:null,bob:null,fx:[],rings:[],drops:[],waves:null,stars:null,jump:null,line:null,panel:null,tab:{shop:'rod',board:'dex'},
  open:-1,rec:null,recAt:0,boards:{},detail:null,dims:{w:0,h:0,dpr:1},msgT:0,busy:false,timers:[],prevPause:null,onState:null,nibDone:0,twitch:0,
  lake:null,cam:0,camTo:null,meFig:null,lastAct:'',panAt:0,feedN:-1,bannerT:0,pcard:null,pan:null,sb:null,vel:0,sbKey:'',dotsKey:'',mnt:null};

const C=()=>F.env?.api?.content?.journey?.fish||null;
const P=()=>F.env?.api?.state?.journey?.fish||{fresh:true,rod:'tre',rods:['tre'],bait:{},use:'',gio:0,cap:20,bag:[],dex:{},tot:{},ms:[],carry:0,aq:[],tro:{},deal:null};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const clock=()=>performance.now()/1000;
const clamp=(v,a,b)=>v<a?a:v>b?b:v;
const wallet=()=>Math.max(0,Number(F.env?.api?.state?.journey?.wallet)||0);
const bankBal=()=>Math.max(0,Number(F.env?.api?.state?.journey?.bank?.balance)||0);   // the server pays from the wallet first, then the bank account (auction._take)
const funds=()=>wallet()+bankBal();
let SPM=null;
const spOf=id=>{if(!SPM){SPM=new Map();for(const s of C()?.species||[])SPM.set(s.id,s);}return SPM.get(id)||null;};
const rods=()=>C()?.rods||[];
const rodOf=id=>rods().find(r=>r.id===id)||rods()[0]||{id:'tre',name:'Cần tre',emoji:'🎋',reach:[15,80],zones:[62,100,150],line:6,color:'#c8a85a'};
const reachOf=r=>Array.isArray(r?.reach)&&r.reach.length===2?r.reach.map(Number):[15,80];
const myRod=()=>rodOf(P().rod);
const spotOf=id=>(C()?.spots||[]).find(s=>s.id===id)||{id,name:id,emoji:'🎣',water:'#4aa3c7',deep:'#1f5f86',shore:'#7bbf6a'};
const rar=r=>(C()?.rarities||[])[r]||{name:'',emoji:'⚪',color:RARITY_COLORS[r]||'#b8c0c8'};
const secs=n=>`${String(+Number(n).toFixed(2)).replace('.',',')}s`;
const km=m=>String(+(m/1000).toFixed(2)).replace('.',',');
const fmtM=m=>`${fmt(Math.round(m))} m`;                                     // the cast: big numbers ("1.234 m")
const shortM=m=>m>=1000?`${km(m)} km`:`${fmt(Math.round(m))} m`;            // buoys ("1,5 km")
const reachTxt=([lo,hi])=>hi>=1000?`${km(lo)}–${km(hi)} km`:`${fmt(lo)}–${fmt(hi)} m`;   // the rod stall ("0,5–2 km")
const kgLine=kg=>kg>=1000?`${String(+(kg/1000).toFixed(1)).replace('.',',')} tấn`:`${fmt(kg)} kg`;
const pct=p=>p>=10?`${Math.round(p)}%`:`${String(+p.toFixed(1)).replace('.',',')}%`;
/** 🍀 the rod's odds: % per rarity of the fish it hooks in its farthest zone (game/fishing_content.rod_odds), under 0,05 % left out. */
const oddsHTML=r=>{
  if(!Array.isArray(r?.odds))return r?.luck?`<small>🍀 ×${esc(String(r.luck).replace('.',','))}</small>`:'';   // an older server
  const z=(C()?.zones||[])[r.far]?.name;
  return `<small class="fs-odds">🍀 ${z?`<span>${esc('Vùng '+z)}</span>: `:''}${r.odds.map((p,i)=>p>=.05?`${esc(rar(i).emoji)} ${pct(p)}`:'').filter(Boolean).join(' · ')}</small>`;};
const priceOf=f=>Number(f?.pr)||0;   // journey.fish.bag[].pr: game/fishing_content.price, before haggling
const vibrate=p=>{try{navigator.vibrate?.(p);}catch{/* not on iOS */}};
const later=(fn,ms)=>{const id=setTimeout(fn,ms);F.timers.push(id);return id;};

/* ---------------------------------------------------------------- open / close */
export async function openFishing(env,{spot='',trip=''}={}){
  if(env.api?.state?.jail){await env.act?.('jail');return;}
  if(!env.api?.state?.journey?.story){env.toast?.('Câu cá kiếm tiền chỉ có trong hành trình.',true);return;}
  if(!env.api?.content?.journey?.fish){env.toast?.('Hồ câu chưa mở, tải lại trang nhé.',true);return;}
  F.env=env;SPM=null;
  await stylesheet('/css/fishing.css');
  F.trip=typeof trip==='string'&&/^[0-9a-f]{16}$/.test(trip)?trip:'';
  F.spot=F.trip?'dao':['ho','song','bien'].includes(spot)?spot:(F.spot&&F.spot!=='dao'?F.spot:'ho');
  const d=dialog();
  if(!d.open)d.showModal();
  if(env.world&&F.prevPause===null){F.prevPause=Boolean(env.world.paused);env.world.paused=true;}
  noTyping();document.addEventListener('focusin',guard,true);   // ⌨️ #515
  F.onState=()=>{F.meFig=null;paintHud();if(F.panel)paintPanel();};
  env.api.addEventListener?.('state',F.onState);
  F.meFig=null;idle('');paintSpots();paintHud();resize();loadRecords();joinLake();
  if(P().fresh)say('🎣 Giữ rồi thả để quăng, xa gần hên xui! Càng xa cá càng to.',5000);
  cancelAnimationFrame(F.raf);F.last=0;F.raf=requestAnimationFrame(tick);
}
export async function fishingAction(action,data,el,env){if(action!=='fishing')return false;await openFishing(env,data||{});return true;}

function dialog(){
  if(F.dlg)return F.dlg;
  const d=document.createElement('dialog');d.className='fs-sheet';d.setAttribute('aria-label','Câu cá');
  d.innerHTML=`<div class="fs-root">
    <header class="fs-top"><button type="button" class="fs-x" data-fs="close" aria-label="Đóng">✕</button><nav class="fs-spots" aria-label="Chỗ câu"></nav><span class="fs-sky"></span></header>
    <div class="fs-stage">
      <canvas class="fs-cv" aria-label="Mặt hồ"></canvas>
      <div class="fs-hud"><button type="button" class="fs-chip fs-gear" data-fs="shop"></button><button type="button" class="fs-chip fs-bagb" data-fs="market"></button></div>
      <div class="fs-say" role="status" aria-live="polite" hidden></div>
      <div class="fs-bite" aria-hidden="true" hidden>❗ Giật!</div><p class="sr-only fs-sr" role="status" aria-live="assertive"></p>
      <div class="fs-meter" hidden><i></i></div><span class="fs-pow" hidden></span>
      <div class="fs-dist" aria-live="polite" hidden><b></b><small></small></div>
      <div class="fs-ten" hidden><div class="fs-ten-bar"><b></b><i></i></div><div class="fs-ten-row"><span>🐟</span><span class="fs-prog"><i></i></span><span>🧍</span></div></div>
      <div class="fs-bank">
        <button type="button" class="fs-stall fs-st-shop" data-fs="shop"><span class="fs-roof"></span><b>🎣 Quầy bán cần</b><small>Cần · mồi · giỏ</small></button>
        <button type="button" class="fs-stall fs-st-board" data-fs="board"><span class="fs-roof"></span><b>📖 Bảng bộ sưu tập</b><ol class="fs-top3"></ol></button>
        <button type="button" class="fs-stall fs-st-market" data-fs="market"><span class="fs-roof"></span><b>🐟 Quầy thu mua</b><small>Bán cá · lái trả giá</small></button>
      </div>
      <div class="fs-feed" hidden><button type="button" class="fs-feed-n" data-fs="feed"></button><button type="button" class="fs-feed-line" data-fs="feed"></button><button type="button" class="fs-feed-say" data-fs="sayOpen" aria-label="Nói với người câu gần đây">💬</button></div>
      <ol class="fs-feed-all" hidden></ol>
      <form class="fs-sayrow" hidden><input type="text" maxlength="120" enterkeyhint="send" placeholder="Nói với người câu gần đây…" aria-label="Lời nói"><button type="submit" class="fs-btn primary small">Nói</button><button type="button" class="fs-btn small" data-fs="sayClose" aria-label="Đóng">✕</button></form>
      <div class="fs-banner" role="status" aria-live="polite" hidden></div>
      <button type="button" class="fs-pan l" data-fs="pan" data-dir="-1" aria-label="Xem bên trái hồ" hidden></button><button type="button" class="fs-pan r" data-fs="pan" data-dir="1" aria-label="Xem bên phải hồ" hidden></button>
      <div class="fs-scroll" role="scrollbar" aria-orientation="horizontal" aria-label="Xem dọc bờ hồ" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50" tabindex="0" hidden><canvas class="fs-sdots" aria-hidden="true"></canvas><i class="fs-sthumb"></i><b class="fs-sme" aria-hidden="true"></b></div>
      <button type="button" class="fs-home" data-fs="home" hidden>📍 Về chỗ tôi</button>
      <div class="fs-pcard" hidden></div>
      <div class="fs-card" hidden></div>
    </div>
    <footer class="fs-bar"><button type="button" class="fs-go">🎣 Giữ để quăng</button><small class="fs-tip"></small></footer>
    <section class="fs-panel" hidden></section>
  </div>`;
  document.body.append(d);
  F.cv=d.querySelector('.fs-cv');F.ctx=F.cv.getContext('2d');
  const go=d.querySelector('.fs-go'),stage=d.querySelector('.fs-stage');
  const down=e=>{if(e.button>0)return;e.preventDefault();noTyping();
    try{e.currentTarget.setPointerCapture?.(e.pointerId);}catch{/* fine */}press(e.timeStamp);};
  const up=e=>{e.preventDefault();release();};
  go.addEventListener('pointerdown',down);go.addEventListener('pointerup',up);go.addEventListener('pointercancel',up);
  // ↔️ the lake itself: a drag pans along the boardwalk (idle), a tap on a fisher opens their card, else it casts / reels
  F.cv.addEventListener('pointerdown',cvDown);F.cv.addEventListener('pointermove',cvMove);F.cv.addEventListener('pointerup',cvUp);F.cv.addEventListener('pointercancel',cvUp);
  F.cv.addEventListener('wheel',cvWheel,{passive:false});
  // ⌨️ #515 (iOS: holding the reel button popped the keyboard up): the press targets never start a touch's default (no
  // focus, no selection, no callout) and nothing outside the lake may take the focus while it is open (noTyping, guard)
  for(const el of [go,F.cv])el.addEventListener('touchstart',e=>{if(e.cancelable)e.preventDefault();noTyping();},{passive:false});
  const bar=d.querySelector('.fs-scroll');
  bar.addEventListener('pointerdown',sbDown);bar.addEventListener('pointermove',sbMove);bar.addEventListener('pointerup',sbUp);bar.addEventListener('pointercancel',sbUp);
  bar.addEventListener('keydown',e=>{const k={ArrowLeft:-3,ArrowRight:3,PageUp:-10,PageDown:10}[e.key];if(!k)return;e.preventDefault();lookAt((F.camTo??F.cam)+k);});
  go.addEventListener('contextmenu',e=>e.preventDefault());stage.addEventListener('contextmenu',e=>e.preventDefault());
  d.addEventListener('keydown',e=>{if((e.key===' '||e.key==='Enter')&&!F.panel&&!e.repeat&&(e.target===go||e.target===d)){e.preventDefault();press(e.timeStamp);}});
  d.addEventListener('keyup',e=>{if((e.key===' '||e.key==='Enter')&&!F.panel&&(e.target===go||e.target===d)){e.preventDefault();release();}});
  d.addEventListener('click',e=>{const el=e.target.closest('[data-fs]');if(!el||!d.contains(el))return;e.preventDefault();act(el.dataset.fs,el.dataset.fs==='sayOpen'?{tap:e.isTrusted}:el.dataset).catch(err=>say(err?.message||'Có lỗi nhỏ, thử lại nhé.'));});
  d.addEventListener('cancel',e=>{e.preventDefault();if(F.panel){closePanel();return;}if(!d.querySelector('.fs-pcard').hidden){hidePeerCard();return;}close();});
  d.querySelector('.fs-sayrow').addEventListener('submit',e=>{e.preventDefault();const inp=e.currentTarget.querySelector('input'),text=inp.value.trim();if(!text)return;
    if(F.lake?.say(text)){inp.value='';e.currentTarget.hidden=true;}else say('Chưa nói được: đang mất kết nối, thử lại sau nhé.');});
  d.addEventListener('close',stop);
  if(typeof ResizeObserver==='function'){F.ro=new ResizeObserver(()=>resize());F.ro.observe(stage);}
  else window.addEventListener('resize',resize);
  F.dlg=d;return d;
}
async function close(){
  if(['fight','hooking'].includes(F.phase)&&F.env?.confirmAction&&!(await F.env.confirmAction('Bỏ con cá đang cắn câu?','Rời hồ bây giờ là mất con này.','Rời hồ')))return;
  F.dlg?.close();
}
function stop(){
  cancelAnimationFrame(F.raf);F.raf=0;for(const id of F.timers)clearTimeout(id);F.timers=[];
  F.env?.api?.removeEventListener?.('state',F.onState);
  if(F.env?.world&&F.prevPause!==null){F.env.world.paused=F.prevPause;F.env.world.wake?.();}
  F.prevPause=null;F.r=null;F.f=null;F.phase='idle';F.panel=null;biteFx(false);F.pan=null;F.sb=null;F.vel=0;
  document.removeEventListener('focusin',guard,true);
  F.lake?.stop();F.lake=null;F.camTo=null;hidePeerCard();
}

/* ---------------------------------------------------------------- server */
async function send(action,payload){
  try{return await F.env.api.command(action,payload);}
  catch(e){if(e?.data?.code==='too_early')throw e;if(!e?.quiet)say(e?.message||'Chưa gửi được, thử lại nhé.');return null;}
}
async function loadRecords(force=false){
  if(!force&&F.rec&&Date.now()-F.recAt<30000){paintTop3();return F.rec;}
  try{F.rec=await F.env.api.json('/api/fish/records');F.recAt=Date.now();}catch{F.rec=F.rec||{records:{},tops:{}};}
  paintTop3();if(F.panel==='board'||F.panel==='dex')paintPanel();
  return F.rec;
}

/* ---------------------------------------------------------------- 👥 the shared lake (v4/fish-lake.js) */
/** What the shared lake holds now (scripts/browser_fishing_shared.py and the devtools; read only). */
export function lakeView(){
  const L=F.lake,g=F.dims.w?geo():null,r=F.cv?.getBoundingClientRect();
  return {left:Math.round(r?.left||0),top:Math.round(r?.top||0),open:Boolean(F.dlg?.open),online:Boolean(L?.online),n:L?.count||1,me:L?.me||null,cam:F.cam,phase:F.phase,
    peers:[...(L?.peers.values()||[])].map(p=>({pid:p.pid,name:p.name,s:p.s,whole:Boolean(p.lk),x:g?Math.round(screenX(posOf(p.s),F.cam,g.sp,g.w)):null,
      y:g?g.py:null,a:p.a?.k||null,got:p.got?{s:p.got.s,g:p.got.g,r:p.got.r}:null,said:p.said?.text||null})),
    feed:(L?.feed||[]).map(lineOf),banner:F.dlg?.querySelector('.fs-banner')?.hidden===false?F.dlg.querySelector('.fs-banner').innerText:''};
}
let lakeSeq=0;
/** Join this spot's live lake (again after a spot change); nothing without the live service. */
async function joinLake(){
  const seq=++lakeSeq;F.lake?.stop();F.lake=null;F.cam=0;F.camTo=null;F.lastAct='';F.feedN=-1;hidePeerCard();paintFeed();
  const env=F.env;let live=env?.live?.()||null;
  if(!live){try{const m=await import('./live.js');env?.bootLive?.(m);live=m.live;}catch{return;}}
  if(seq!==lakeSeq||!F.dlg?.open||!live?.on)return;
  const st=env.api?.state,J=st?.journey||{};
  F.lake=createLake({live,spot:F.spot,trip:F.trip,me:{look:lookOf(st),gender:J.gender,fh:J.fish?.wear,rod:P().rod},on:{
    change:k=>{if(k==='room'){F.cam=myPos();F.camTo=null;}paintFeed();},
    catch:onCatch,card:paintPeerCard,
    error:f=>{if(!['off','unknown'].includes(f.code))say(f.msg||'Hồ câu chung đang trục trặc, bạn vẫn câu được nhé.');},
    left:why=>{if(why==='other')say('Bạn đang câu ở thẻ khác.');}}}).start();
}
/** My cosmetic hint for the others ('cast', 'bite', 'reel', 'lost', 'idle'); one 'idle' after a round, not one per tap. */
function lakeAct(k,extra={}){
  if(!F.lake?.online)return;
  if(k==='idle'&&['','idle','lost'].includes(F.lastAct))return;
  F.lastAct=k;F.lake.act(k,extra);
}
/** The view follows my place unless I looked along the boardwalk (a drag, the wheel, the bar, ◀ ▶, a feed line); a
 * cast looks back at me. A drag moves it with the finger, a fling glides on and slows down. */
function camera(t,dt){
  const L=F.lake;if(!L?.online){F.cam=0;F.vel=0;paintScroll();return;}
  const ext=lakeExt();
  if(F.pan?.moved||F.sb){/* the finger has it */}
  else if(F.vel){F.cam+=F.vel*dt;const c=clampCam(F.cam,ext);F.vel=c!==F.cam?0:glide(F.vel,dt);F.cam=c;F.camTo=F.cam;}
  else{const to=clampCam(F.camTo??L.pos,ext);F.cam+=(to-F.cam)*Math.min(1,dt*6);if(Math.abs(to-F.cam)<.005)F.cam=to;}
  L.view(F.cam);
  paintScroll();
  if(t-F.panAt>.3){F.panAt=t;paintPan();}
}
const lakeExt=()=>{const L=F.lake;return extent(L?.online?[...L.peers.values(),{s:L.slot}]:[]);};
/** Look at place `pos` (eased there), kept over the boardwalk. */
function lookAt(pos){F.vel=0;F.camTo=clampCam(pos,lakeExt());}
/** ↔️ The lake can be panned now: idle (no round on), no sheet open, a crowd wider than the view. */
function panOK(){
  if(F.panel||!['idle','card','lost'].includes(F.phase)||!F.lake?.online)return false;
  const g=geo();return scrollOf(F.cam,lakeExt(),g.sp,g.w).can;
}
const HOLD_MS=200,SLOP=8;
/** A finger on the lake. Idle with a crowd: wait to see whether it drags (pan), taps (a fisher's card, else a cast)
 * or stays down (HOLD_MS: the power meter, as before). During a round: the press itself (bite, reel), at once. */
function cvDown(e){
  if(e.button>0)return;e.preventDefault();noTyping();
  try{F.cv.setPointerCapture?.(e.pointerId);}catch{/* fine */}
  if(!panOK()){if(tapPeer(e.clientX,e.clientY))return;press(e.timeStamp);return;}
  F.vel=0;
  const P={id:e.pointerId,x0:e.clientX,y0:e.clientY,t0:e.timeStamp,cam0:F.cam,moved:false,lx:e.clientX,lt:e.timeStamp,v:0,held:false};
  P.timer=setTimeout(()=>{if(F.pan===P&&!P.moved){P.held=true;if(!tapPeer(P.x0,P.y0,true))press(P.t0);else F.pan=null;}},HOLD_MS);
  F.pan=P;
}
function cvMove(e){
  const P=F.pan;if(!P||e.pointerId!==P.id||P.held)return;
  const dx=e.clientX-P.x0,dy=e.clientY-P.y0;
  if(!P.moved){if(Math.abs(dx)<SLOP||Math.abs(dx)<Math.abs(dy)*.7)return;P.moved=true;clearTimeout(P.timer);hidePeerCard();}
  const g=geo(),ms=Math.max(1,e.timeStamp-P.lt),v=-(e.clientX-P.lx)/g.sp/(ms/1000);
  P.v=P.v*.6+v*.4;P.lx=e.clientX;P.lt=e.timeStamp;
  F.cam=panBy(P.cam0,dx,g.sp,lakeExt());F.camTo=F.cam;
}
function cvUp(e){
  if(e.type==='pointerup')e.preventDefault();
  const P=F.pan;
  if(!P||e.pointerId!==P.id){release();return;}
  clearTimeout(P.timer);F.pan=null;
  if(P.held){release();return;}
  if(P.moved){if(e.type==='pointerup'&&e.timeStamp-P.lt<90)F.vel=Math.max(-60,Math.min(60,P.v));return;}   // a fling glides on
  if(e.type!=='pointerup')return;
  if(tapPeer(P.x0,P.y0))return;   // 👥 a tap on another fisher: their card, not a cast
  press(P.t0);release();          // a plain tap casts, as before
}
/** The mouse wheel, a trackpad's sideways swipe: along the boardwalk. */
function cvWheel(e){
  if(!panOK())return;
  const px=wheelPx(e);if(!px)return;e.preventDefault();
  const g=geo();lookAt((F.camTo??F.cam)+px/g.sp);
}
/** The bar under the boardwalk: drag its thumb, or tap a spot to look there. */
function sbDown(e){
  if(e.button>0)return;e.preventDefault();noTyping();
  const el=e.currentTarget,r=el.getBoundingClientRect(),g=geo(),o=scrollOf(F.cam,lakeExt(),g.sp,g.w),at=(e.clientX-r.left)/Math.max(1,r.width);
  F.sb={id:e.pointerId,off:at>=o.left&&at<=o.left+o.width?at-o.left:o.width/2};F.vel=0;
  try{el.setPointerCapture?.(e.pointerId);}catch{/* fine */}
  sbMove(e);
}
function sbMove(e){
  const B=F.sb;if(!B||e.pointerId!==B.id)return;
  const r=e.currentTarget.getBoundingClientRect(),g=geo(),at=(e.clientX-r.left)/Math.max(1,r.width);
  F.cam=camAt(at-B.off,lakeExt(),g.sp,g.w);F.camTo=F.cam;
}
function sbUp(e){if(F.sb&&e.pointerId===F.sb.id)F.sb=null;}
/** The bar (where the view is along the whole crowd, a tick per fisher, 📍 me) and the 📍 Về chỗ tôi button. */
function paintScroll(){
  const d=F.dlg;if(!d||!F.dims.w)return;
  const bar=d.querySelector('.fs-scroll'),home=d.querySelector('.fs-home'),L=F.lake,g=geo();
  const ext=lakeExt(),o=scrollOf(F.cam,ext,g.sp,g.w,myPos()),show=Boolean(L?.online)&&o.can&&!F.panel;
  if(bar.hidden!==!show)bar.hidden=!show;
  const far=show&&farFromMe(F.cam,myPos(),g.sp,g.w)&&['idle','card','lost'].includes(F.phase)&&!F.pan?.moved&&!F.sb;
  if(home.hidden!==!far)home.hidden=!far;
  if(!show)return;
  const key=`${o.left.toFixed(4)}|${o.width.toFixed(4)}|${o.me.toFixed(4)}`;
  if(key!==F.sbKey){F.sbKey=key;
    const th=bar.querySelector('.fs-sthumb');th.style.left=`${o.left*100}%`;th.style.width=`${Math.max(4,o.width*100)}%`;
    bar.querySelector('.fs-sme').style.left=`${o.me*100}%`;
    bar.setAttribute('aria-valuenow',String(Math.round(o.left/Math.max(1e-6,1-o.width)*100)));}
  const n=L.peers.size,dk=`${n}|${ext}|${myPos()}|${bar.clientWidth}|${g.sp}`;
  if(dk!==F.dotsKey){F.dotsKey=dk;   // a tick per fisher: how the crowd spreads along the boardwalk
    const cv=bar.querySelector('.fs-sdots'),w=bar.clientWidth||100,h=bar.clientHeight||10,dpr=F.dims.dpr,q=cv.getContext('2d');
    cv.width=Math.round(w*dpr);cv.height=Math.round(h*dpr);q.setTransform(dpr,0,0,dpr,0,0);q.fillStyle='rgba(255,255,255,.55)';
    const half=g.w/2/g.sp,total=ext[1]-ext[0]+2*half;
    for(const p of L.peers.values()){const x=(posOf(p.s)-ext[0]+half)/total*w;q.fillRect(Math.round(x),2,1.5,h-4);}
    bar.title=`👥 ${fmt(L.count)} người câu dọc bờ hồ`;}
}
/** ⌨️ #515: no typing field keeps the focus under a press (iOS keeps its keyboard up for a focused field). */
function noTyping(){const a=document.activeElement;if(a&&a!==document.body&&a.matches?.(TYPING))try{a.blur();}catch{/* detached */}}
/** ⌨️ #515: while the lake is open, a field behind it (a work screen's form, the chat) never takes the focus; the lake's
 * own 💬 line only once its 💬 button opened it. */
function guard(e){
  const t=e.target;if(!F.dlg?.open||!t?.matches?.(TYPING))return;
  if(F.dlg.contains(t)){if(t.closest('[hidden]'))t.blur();return;}
  const box=t.closest('dialog[open]');if(box&&box!==F.dlg&&!box.contains(F.dlg))return;   // a sheet opened over the lake
  t.blur();
}
function paintPan(){
  const d=F.dlg;if(!d)return;const g=geo(),o=offscreen([...(F.lake?.peers.values()||[])],F.cam,g.sp,g.w);
  const l=d.querySelector('.fs-pan.l'),r=d.querySelector('.fs-pan.r'),off=Boolean(F.panel)||['charge','fight'].includes(F.phase);
  l.hidden=off||!o.left;r.hidden=off||!o.right;
  const lt=`◀ ${fmt(o.left)}`,rt=`${fmt(o.right)} ▶`;if(l.textContent!==lt)l.textContent=lt;if(r.textContent!==rt)r.textContent=rt;
  l.setAttribute('aria-label',`Xem ${o.left} người câu bên trái`);r.setAttribute('aria-label',`Xem ${o.right} người câu bên phải`);
}
const lineOf=e=>feedLine(e,spOf(e.s),rar(e.r));
/** 🎣 The feed: how many fish here, the last catch in one line, all of them (the last 20) on a tap. */
function paintFeed(){
  const d=F.dlg;if(!d)return;
  const L=F.lake,on=Boolean(L?.online),bar=d.querySelector('.fs-feed');bar.hidden=!on;
  if(!on){d.querySelector('.fs-feed-all').hidden=true;d.querySelector('.fs-sayrow').hidden=true;return;}
  d.querySelector('.fs-feed-n').textContent=`👥 ${fmt(L.count)}`;
  d.querySelector('.fs-feed-n').title=`${fmt(L.count)} người đang câu ở đây`;d.querySelector('.fs-feed-n').setAttribute('aria-label',`${fmt(L.count)} người đang câu ở đây`);
  const last=L.feed[L.feed.length-1],line=d.querySelector('.fs-feed-line');
  line.textContent=last?lineOf(last):L.count>1?`${fmt(L.count)} người đang câu ở ${spotOf(F.spot).name}. Ai câu được gì sẽ hiện ở đây!`:'Chưa có ai khác ở đây. Câu con đầu tiên nào!';
  if(L.feed.length!==F.feedN){if(F.feedN>=0&&last){line.classList.remove('new');void line.offsetWidth;line.classList.add('new');}F.feedN=L.feed.length;}
  const all=d.querySelector('.fs-feed-all');
  if(!all.hidden)all.innerHTML=L.feed.length?L.feed.slice().reverse().map(e=>`<li style="--rc:${esc(rar(e.r).color||RARITY_COLORS[e.r]||'#ccc')}"><button type="button" data-fs="feedPid" data-pid="${esc(e.pid)}">${esc(lineOf(e))}</button></li>`).join('')
    :'<li class="fs-empty">Chưa ai câu được con nào. Bạn mở hàng nhé!</li>';
}
/** Someone landed a fish (the server's word): the feed, and the lake-wide banner for 🟡 Huyền thoại / 🔴 Cổ đại. */
function onCatch(e,p,mine){
  paintFeed();
  if(mine||!e.s||tierOf(e.r)!=='legend')return;
  const el=F.dlg?.querySelector('.fs-banner'),R=rar(e.r),sp=spOf(e.s);if(!el)return;
  el.style.setProperty('--rc',R.color||RARITY_COLORS[e.r]);
  el.innerHTML=`<b>${esc(R.emoji)} ${esc(String(R.name||'').toUpperCase())}!</b><span><span data-no-translate>${esc(p?.name||e.feed?.name||'')}</span> vừa câu được ${esc(sp?.name||'')} ${esc(fmtKg(e.g))}</span>`;
  el.hidden=false;el.classList.remove('go');void el.offsetWidth;el.classList.add('go');vibrate([30,30,30]);
  clearTimeout(F.bannerT);F.bannerT=setTimeout(()=>{el.hidden=true;},4800);
  if(p&&!CALM){const g=geo();if(Math.abs(posOf(p.s)-F.cam)>g.w/2/g.sp&&['idle','card','lost'].includes(F.phase))F.camTo=posOf(p.s);}   // look at it
}
/** A tap on another fisher (not during a round): their mini card (`peek`: only whether one is there). */
function tapPeer(cx,cy,peek=false){
  const L=F.lake;if(!L?.peers.size||!['idle','card','lost'].includes(F.phase))return false;
  const g=geo(),r=F.cv.getBoundingClientRect(),hit=hitPeer([...L.peers.values()],cx-r.left,cy-r.top,{cam:F.cam,sp:g.sp,w:g.w,py:g.py,scale:g.scale});
  if(!hit)return false;if(peek)return true;
  F.pcard={pid:hit.pid,data:null};paintPeerCard();L.card(hit.pid);return true;
}
function paintPeerCard(f){
  const el=F.dlg?.querySelector('.fs-pcard');if(!el||!F.pcard)return;
  if(f){if(f.pid!==F.pcard.pid)return;F.pcard.data=f;}
  const p=F.lake?.peers.get(F.pcard.pid);if(!p){hidePeerCard();return;}
  const api=F.env?.api,d=F.pcard.data,fish=(x,label)=>{if(!x)return '';const sp=spOf(x.s),R=rar(x.r);
    return `<li style="--rc:${esc(R.color||'#ccc')}">${sp?fishSvg(sp,{w:44,h:22}):''}<span>${label}: <b>${esc(sp?.name||x.s)}</b> ${esc(fmtKg(x.g))} <small>${esc(R.emoji)} ${esc(R.name)}</small></span></li>`;};
  const pic=hfAvatar(p.tt,p.st,portrait(withWings(p.lk||{},p.wg),p.g,52,p.name),api);
  el.innerHTML=`<button type="button" class="fs-x" data-fs="pcardX" aria-label="Đóng">✕</button><div class="fs-pc-who">${pic}<div><b data-no-translate${stName(api,p.st)}>${esc(p.name)}</b>${p.tt?`<small>${hnChips(api,p.tt,2)}</small>`:''}<small class="fs-pc-rod">${rodSvg(p.rod||'tre',24)} ${esc(rodOf(p.rod||'tre').emoji)} ${esc(rodOf(p.rod||'tre').name)}</small></div></div>${d?.nt?.t?`<p class="fs-pc-note" data-no-translate>💭 ${esc(d.nt.t)}</p>`:''}
    ${!d?'<p class="fs-note">Đang xem…</p>':`<ul class="fs-pc-fish">${fish(d.today,'🐟 Hôm nay')}${fish(d.best,'🐋 Lớn nhất')}${d.dex?`<li><span>📖 Sổ cá: <b>${fmt(d.dex)}</b> loài</span></li>`:''}${!d.today&&!d.best&&!d.dex?'<li><span>Chưa có con cá nào để khoe.</span></li>':''}</ul>`}`;
  el.hidden=false;
}
function hidePeerCard(){F.pcard=null;const el=F.dlg?.querySelector('.fs-pcard');if(el){el.hidden=true;el.innerHTML='';}}

/* ---------------------------------------------------------------- input and rounds */
/** `at`: the event's timeStamp (performance.now() time of the touch: the handler itself may run a frame late). */
function press(at){
  if(F.panel)return;
  noTyping();const sr=F.dlg?.querySelector('.fs-sayrow');if(sr&&!sr.hidden)sr.hidden=true;   // ⌨️ #515: a press closes the 💬 line and its keyboard
  F.pressing=true;F.dlg?.querySelector('.fs-go')?.classList.add('down');
  if(F.phase==='idle'||F.phase==='card'){hideCard();hidePeerCard();F.camTo=null;F.phase='charge';F.c0=clock();F.power=0;meters();paintMeter();paintGo();return;}
  if(F.phase==='wait'&&F.r?.biteL){nibbleTap();return;}   // a fish (or junk) is coming: not yet
  if(F.phase==='wait'||F.phase==='bite'){hook(false,at);return;}
  if(F.phase==='fight'&&F.f)F.f.hold=true;
}
function release(){
  if(!F.pressing)return;F.pressing=false;F.dlg?.querySelector('.fs-go')?.classList.remove('down');
  if(F.phase==='charge'){cast(F.power);return;}
  if(F.phase==='fight'&&F.f)F.f.hold=false;
}
function idle(tip){
  F.phase='idle';F.r=null;F.f=null;F.bob=null;F.line=null;F.jump=null;biteFx(false);distFx(null);lakeAct('idle');
  meters();paintGo(tip);
}
async function cast(power){
  const p=Math.round(clamp(power,0,1)*1000)/1000;
  F.phase='casting';meters();paintGo();
  const t0=clock();
  const res=await send('jr_fish_cast',{spot:F.spot,power:p,...(F.trip?{trip:F.trip}:{})});
  if(!res||!res.cast){idle();if(F.env?.api?.state?.journey?.fish?.bag?.length>=P().cap)openPanel('market');return;}
  const c=res.cast,got=clock(),off=c.now!=null?c.now-got:0;   // server time = local + off (the answer's own clock)
  const L=ts=>ts-off,lat=(Math.random()-.5)*.55;
  F.bob={d:Number(c.dist)||0,lat,x:0,y:0,dip:0};
  F.castL=got;
  // The bite is drawn at the same distance from this answer as the server put it from its own clock (`now`): a slow
  // answer only draws it later, and the tap is measured from when it is drawn (shownL), so that costs nothing.
  F.r={id:c.id,dist:Number(c.dist)||0,zone:c.zone,huge:!!c.huge,best:!!c.best,splashL:Math.max(got+.6,L(c.splash)),nib:(c.nib||[]).map(L),biteL:c.bite!=null?L(c.bite):0,
    goneL:c.gone!=null?L(c.gone):0,window:Number(c.window)||C()?.hook_window||1,shownL:0,early:0,earlyL:0,t0};
  F.nibDone=0;F.twitch=0;
  lakeAct('cast',{d:F.r.dist,x:Math.round(lat*1000)/1000,rod:P().rod});   // 👥 the others see it fly (a cosmetic hint)
  if(res.bait_used&&P().bait?.[res.bait_used]==null)say('Hết mồi rồi, mua thêm ở 🎣 Quầy bán cần nhé.');
  F.phase='fly';paintGo();distFx('fly');
}
/** A tap while the bobber only nibbles: a short note, the round goes on. After hook_scare of them (taps closer than .45 s
 * count once) the next one scares the fish off. */
function nibbleTap(){
  const r=F.r,t=clock(),max=Number(C()?.hook_scare)||3;
  if(t-r.earlyL<.45){r.earlyL=t;return;}
  r.earlyL=t;r.early++;
  if(r.early>max){hook(true);return;}
  if(F.bob)F.bob.dip=Math.max(F.bob.dip,.2);vibrate(10);
  say(r.early===max?'Chưa cắn đâu! Giật nữa là cá sợ chạy đó.':'Chưa cắn đâu, chờ chút…',1600);
}
async function hook(scare=false,at=0){
  const r=F.r;if(!r)return;
  const now=clock(),tap=at>0&&at/1000<=now&&at/1000>now-1?at/1000:now;
  const early=F.phase==='wait',ms=F.phase==='bite'&&r.shownL?Math.max(0,Math.round((tap-r.shownL)*1000)):null;
  F.phase='hooking';paintGo();biteFx(false);
  if(F.bob)F.bob.dip=early?.25:1;
  const res=await send('jr_fish_hook',scare?{round:r.id,early:true}:ms!=null?{round:r.id,ms}:{round:r.id});
  if(F.r!==r)return;
  if(!res){idle();return;}
  const h=res.hook||{};
  if(h.wait){F.phase='bite';say(res.message||'Chưa cắn đâu, chờ chút…',1600);paintGo();return;}   // the server had not reached the bite yet
  if(h.lost){
    fleeFx();lakeAct('lost');say(res.message||(h.lost==='early'?'😱 Giật sớm quá, cá chạy mất!':'💨 Cá nhả mồi mất rồi!'));
    F.phase='lost';paintGo();later(()=>{if(F.phase==='lost')idle(h.lost==='early'?'Đợi phao chìm hẳn rồi mới giật nhé.':'');},1100);return;
  }
  startFight(h);
}
function startFight(h){
  const t=clock();
  F.f=reelStart(h,F.pressing);F.f.t0=t;
  F.phase='fight';vibrate([30,30,60]);distFx(null);lakeAct('reel');
  if(F.f.heavy)say('⚠️ Cá nặng quá sức dây! Coi chừng đứt…',2600);
  meters();paintGo();
}
async function endFight(kind){
  const r=F.r;if(!r||!F.f)return;
  F.phase='landing';const f=F.f;meters();paintGo();
  if(kind==='snap'){snapFx();say(f.heavy&&f.snapAt?'💥 Phựt! Cá quá nặng, đứt dây rồi.':'💥 Phựt! Căng quá đứt dây rồi.');}
  else if(kind==='slack'){fleeFx();say('🐟 Dây chùng quá, cá giãy thoát mất!');}
  // A slow save (prod 25/10: jr_fish_* 1,5–2,4 s on big saves) never costs the fish: "Đang kéo lên…" while it lands;
  // a "too early" (the server's clock), a save that moved meanwhile (409, dropped quietly by api.js) or no answer at
  // all are asked again (the same round: the server answers a landed one as a duplicate, never twice).
  let res=null,err=null;
  const wait=ms=>new Promise(done=>later(done,ms));
  for(let i=0;i<6;i++){
    err=null;
    try{res=await F.env.api.command('jr_fish_land',{round:r.id,ok:kind==='ok'});
      if(res?.duplicate&&!res.land&&i<5){await wait(500);continue;}   // landed by this tab already: ask for what it was
      break;}
    catch(e){
      err=e;const code=e?.data?.code||'';
      if(code==='too_early'&&i<5){await wait(700);continue;}
      if((e?.conflict||!e?.status||e.status>=500)&&i<5){await wait(500+i*400);continue;}
      break;
    }
  }
  if(F.r!==r)return;
  const land=res?.land;
  if(!land){if(err&&!err.quiet)say(err.message||'Chưa ghi được lượt câu.');idle();return;}
  if(land.res==='fish'&&!land.catch){say(res.message||'🎣 Lên cá rồi! Xem trong 🧺 giỏ nhé.',3200);idle();return;}   // an answer replayed (duplicate)
  if(land.res==='fish'||land.res==='junk'){F.lastAct='';jump(land,res);return;}   // 👥 the service tells the others (the commit's word)
  lakeAct('lost');
  if(kind==='ok'||land.res==='snap'){if(land.res==='snap')snapFx();say(res.message||'Mất cá rồi!',3200);}
  F.phase='lost';paintGo();later(()=>{if(F.phase==='lost')idle();},1200);
}
/** The catch leaps out of the water to the dock, then its card. */
function jump(land,res){
  const g=geo(),fromD=Math.max(1,(F.r?.dist||10)*.12),sp=land.catch?spOf(land.catch.s):null;
  const pose=sp?catchPose(land.catch.g,g.scale):null;   // 🐋 as long as it weighs: a big one lands on the boardwalk beside me
  F.jump={t0:clock(),dur:1.05,sp,junk:land.res==='junk'?(C()?.junk||[]).find(j=>j.id===land.junk):null,
    x0:g.px+(F.bob?.lat||0)*g.half(g.yOf(fromD))*.4,y0:g.yOf(fromD),x1:pose?.big?g.px+pose.dx:g.px+6,y1:pose?.big?g.py+pose.dy:g.py-70,len:pose?Math.max(18,pose.len):30,big:!!pose?.big};
  splashAt(F.jump.x0,F.jump.y0,16,'#e8f8ff');
  F.phase='jump';F.f=null;F.line=null;meters();paintGo();vibrate(land.res==='fish'&&land.catch?.r>=4?[40,40,120]:30);
  later(()=>showCard(land,res),1000);
}

/* ---------------------------------------------------------------- the loop */
function tick(){
  F.raf=requestAnimationFrame(tick);
  const t=clock(),dt=F.last?Math.min(.05,t-F.last):0;F.last=t;
  step(t,dt);draw(t);
}
function step(t,dt){
  if(F.phase==='charge'){
    F.power=Math.min(1,(t-F.c0)/FILL);paintMeter();
  }else if(F.phase==='fly'&&F.r&&t>=F.r.splashL){
    const [x,y]=bobXY();
    splashAt(x,y,F.r.huge?22:12,'#dff6ff');ring(x,y,F.r.huge?1.8:1.2);F.phase='wait';paintGo();distFx('land');
  }else if(F.phase==='fly'&&F.r){
    const u=clamp((t-F.castL)/Math.max(.3,F.r.splashL-F.castL),0,1);distTick(F.r.dist*(1-Math.pow(1-u,3)));
  }else if(F.phase==='wait'&&F.r){
    const r=F.r;
    while(F.nibDone<r.nib.length&&t>=r.nib[F.nibDone]){F.nibDone++;F.bob.dip=.35;const p=bobXY();ring(p[0],p[1],.7);vibrate(8);}
    if(Math.random()<dt*.35){F.bob.dip=Math.max(F.bob.dip,.12);}   // a fake twitch: the wind, a leaf
    if(r.biteL&&t>=r.biteL){
      F.phase='bite';r.shownL=clock();F.bob.dip=1;const p=bobXY();ring(p[0],p[1],1.6);splashAt(p[0],p[1],8,'#ffffff');
      vibrate([90,40,180]);F.env?.sound?.alert?.();paintGo();biteFx(true);lakeAct('bite');
    }
    else if(r.goneL&&t>=r.goneL){
      F.phase='lost';const p=bobXY();ring(p[0],p[1],.8);say('🐟 Cá rỉa mất mồi rồi! Quăng lại nhé.');lakeAct('lost');
      send('jr_fish_hook',{round:r.id}).catch(()=>{});   // closes the round on the server (nothing to win)
      paintGo();later(()=>{if(F.phase==='lost')idle();},1200);
    }
  }else if(F.phase==='bite'&&F.r){
    const r=F.r,left=1-(t-r.shownL)/r.window;
    biteLeft(left);
    if(left<0){   // the window ran out on this screen: the server closes the round as late
      F.phase='lost';biteFx(false);fleeFx();say('💨 Chậm tay rồi, cá nhả mồi mất!');paintGo();lakeAct('lost');
      send('jr_fish_hook',{round:r.id,ms:Math.ceil((t-r.shownL)*1000)}).then(()=>later(()=>{if(F.phase==='lost'&&F.r===r)idle();},700)).catch(()=>{});
    }
  }else if(F.phase==='fight'&&F.f){fight(t,dt);}
  if(F.bob)F.bob.dip=Math.max(0,F.bob.dip-dt*(F.phase==='bite'?.15:1.6));
  camera(t,dt);
}
function fight(t,dt){
  const f=F.f,wasRed=f.tau>RED,{end,dart}=reelStep(f,dt);
  if(dart){const p=fishXY();splashAt(p[0],p[1],6,'#e8f8ff');vibrate(12);}
  if(f.tau>RED&&!wasRed&&t-(f.warnL||0)>2.5){f.warnL=t;say('⚠️ Căng quá! Thả tay ra cho dây chùng chút!',1800);vibrate([20,20,20]);}
  paintTension();
  if(end)endFight(end);
}

/* ---------------------------------------------------------------- geometry */
function resize(){
  if(!F.cv)return;
  const w=F.cv.clientWidth,h=F.cv.clientHeight;if(!w||!h)return;
  const dpr=Math.min(2,window.devicePixelRatio||1);
  F.dims={w,h,dpr};F.cv.width=Math.round(w*dpr);F.cv.height=Math.round(h*dpr);F.ctx.setTransform(dpr,0,0,dpr,0,0);
  F.waves=null;F.stars=null;
  const bank=F.dlg?.querySelector('.fs-bank')?.offsetHeight||112;F.bankH=bank;
  const meter=F.dlg?.querySelector('.fs-meter');
  if(meter){meter.style.top=`${Math.round(h*.2)}px`;meter.style.height=`${Math.round(h-bank-h*.2-40)}px`;}
  const bar=F.dlg?.querySelector('.fs-scroll');if(bar)bar.style.bottom=`${Math.max(0,bank-6)}px`;F.dotsKey='';   // ↔️ just under the boardwalk (over its posts)
}
/** The lake in perspective, as deep as the rod in hand throws (M: a little past its longest cast, at the horizon). */
/** 👥 With others at the lake I stand at my place on the boardwalk (px: where the view puts it; a crowd packs closer). */
function geo(){
  const {w,h}=F.dims,bank=F.bankH||112,shore=h-bank,hor=Math.max(46,h*.14),M=reachOf(myRod())[1]*1.08,K=M*PERSP;
  const top=hor+8,bottom=shore-28,frac=d=>(d/(d+K))/(M/(M+K));
  const yOf=d=>bottom-(bottom-top)*clamp(frac(Math.max(0,d)),0,1);
  const half=y=>{const u=clamp((y-hor)/(shore-hor),0,1);return w*(.17+.36*u);};
  const sp=spacing(F.lake?.count||1,w),scale=figScale(sp),px=screenX(myPos(),F.cam,sp,w);
  return {w,h,shore,hor,M,yOf,half,px,py:shore-20,sp,scale};
}
const myPos=()=>F.lake?.online?F.lake.pos:0;
function bobXY(){const g=geo(),b=F.bob;if(!b)return [g.px,g.py];return waterPoint(g,g.px,b.d,b.lat);}
function fishXY(){
  const g=geo(),f=F.f,b=F.bob;if(!b||!f)return bobXY();
  const d=b.d*(1-f.prog)+1,[x,y]=waterPoint(g,g.px,d,b.lat*(1-f.prog*.8)),t=clock();
  return [x+Math.sin(t*1.7+f.seed)*g.half(y)*.12*(.4+f.pull)+f.sway*f.dl*30,y];
}

/* ---------------------------------------------------------------- effects */
function ring(x,y,s=1){F.rings.push({x,y,t0:clock(),s});if(F.rings.length>24)F.rings.shift();}
function splashAt(x,y,n,c){for(let i=0;i<n;i++){const a=-Math.PI*(.15+.7*Math.random());F.fx.push({x,y,vx:Math.cos(a)*(40+Math.random()*70)*(Math.random()<.5?-1:1),vy:Math.sin(a)*(90+Math.random()*120),t0:clock(),life:.5+Math.random()*.4,c});}if(F.fx.length>160)F.fx.splice(0,F.fx.length-160);}
/** The bite's big "Giật!" (on) or its end; the button's countdown bar (--left, 1 → 0). */
function biteFx(on){
  const d=F.dlg;if(!d)return;const el=d.querySelector('.fs-bite');
  if(el){el.hidden=!on;el.classList.remove('go');if(on){void el.offsetWidth;el.classList.add('go');}}
  if(on)biteLeft(1);else d.querySelector('.fs-go')?.style.removeProperty('--left');
  const sr=d.querySelector('.fs-sr');if(sr)sr.textContent=on?'Cá cắn câu! Giật ngay!':'';   // ♿ the big "Giật!" is drawn only: a screen reader hears it
}
function biteLeft(left){F.dlg?.querySelector('.fs-go')?.style.setProperty('--left',clamp(left,0,1).toFixed(3));}
function fleeFx(){const p=F.f?fishXY():bobXY();ring(p[0],p[1],1);ring(p[0]+16,p[1]-4,.6);splashAt(p[0],p[1],6,'#e8f8ff');}
/** The cast's distance over the lake: `fly` counts up with the bobber, `land` the big "🎯 1.234 m!" (🚀 a monster cast,
 * 🏅 the longest yet), then a small chip while the round goes on; null hides it. */
function distFx(mode){
  const el=F.dlg?.querySelector('.fs-dist');if(!el)return;
  clearTimeout(F.distT);
  if(!mode||!F.r){el.hidden=true;el.className='fs-dist';return;}
  const r=F.r,zn=(C()?.zones||[])[r.zone]?.name||ZN[r.zone]||'';
  el.hidden=false;
  if(mode==='fly'){el.className='fs-dist fly';distTick(0);el.querySelector('small').textContent='';return;}
  el.className=`fs-dist land${r.huge?' huge':''}`;void el.offsetWidth;el.classList.add('pop');
  el.querySelector('b').textContent=`🎯 ${fmtM(r.dist)}!`;
  el.querySelector('small').textContent=[r.huge?'🚀 Quăng siêu xa!':'',r.best?'🏅 Kỷ lục quăng mới!':''].filter(Boolean).join(' ')||`Vùng ${zn}`;
  if(r.huge||r.best)F.dlg.querySelector('.fs-say').hidden=true;   // the big number has the stage
  vibrate(r.huge?[30,30,30,30,90]:15);
  F.distT=later(()=>{if(F.r===r&&!el.hidden){el.className='fs-dist mini';el.querySelector('b').textContent=`🎯 ${fmtM(r.dist)}`;el.querySelector('small').textContent=`Vùng ${zn}`;}},2400);
}
function distTick(m){const b=F.dlg?.querySelector('.fs-dist b');if(b)b.textContent=`🎯 ${fmtM(m)}`;}
function snapFx(){const p=F.f?fishXY():bobXY();splashAt(p[0],p[1],10,'#ffffff');F.line={snap:clock()};vibrate([80,30,80]);}

/* ---------------------------------------------------------------- drawing */
function draw(t){
  const ctx=F.ctx;if(!ctx||!F.dims.w)return;
  const g=geo(),{w,h}=F.dims,S=spotOf(F.spot),cond=P().cond||{},night=cond.night!=null?cond.night:isNight(),rain=!!cond.rain;
  ctx.clearRect(0,0,w,h);
  // sky
  const sky=ctx.createLinearGradient(0,0,0,g.hor);
  if(night){sky.addColorStop(0,'#0b1430');sky.addColorStop(1,rain?'#2a3446':'#28365e');}
  else{sky.addColorStop(0,rain?'#7e93a3':'#7fc8f0');sky.addColorStop(1,rain?'#b4c1c9':'#d8f0fb');}
  ctx.fillStyle=sky;ctx.fillRect(0,0,w,g.hor+2);
  if(night){
    if(!F.stars){F.stars=[];for(let i=0;i<40;i++)F.stars.push([Math.random()*w,Math.random()*g.hor*.9,Math.random()*1.4+.4,Math.random()*6]);}
    if(!rain)for(const s of F.stars){ctx.globalAlpha=.5+.5*Math.sin(t*1.5+s[3]);ctx.fillStyle='#fff';ctx.fillRect(s[0],s[1],s[2],s[2]);}
    ctx.globalAlpha=1;ctx.fillStyle='#fdf3c8';ctx.beginPath();ctx.arc(w*.82,g.hor*.38,11,0,7);ctx.fill();
  }else if(!rain){ctx.fillStyle='#fff3b0';ctx.beginPath();ctx.arc(w*.84,g.hor*.4,13,0,7);ctx.fill();}
  farShore(ctx,g,S,night,t);
  // water
  const wat=ctx.createLinearGradient(0,g.hor,0,g.shore);
  wat.addColorStop(0,night?shadeHex(S.deep,.55):S.deep);wat.addColorStop(1,night?shadeHex(S.water,.6):S.water);
  ctx.fillStyle=wat;ctx.fillRect(0,g.hor,w,g.shore-g.hor);
  zones(ctx,g,night);
  waves(ctx,g,t,night);
  for(const r of F.rings){const a=(t-r.t0)/1.4;if(a>1)continue;const rad=(6+40*a)*r.s*(.4+.6*(r.y-g.hor)/(g.shore-g.hor));ctx.strokeStyle=`rgba(255,255,255,${(1-a)*.7})`;ctx.lineWidth=1.5;ctx.beginPath();ctx.ellipse(r.x,r.y,rad,rad*.32,0,0,7);ctx.stroke();}
  F.rings=F.rings.filter(r=>t-r.t0<1.4);
  // the fish under the water while fighting
  if(F.f&&(F.phase==='fight'||F.phase==='landing')){
    const [fx,fy]=fishXY(),u=clamp((fy-g.hor)/(g.shore-g.hor),0,1),len=(18+22*F.f.pull)*(.45+.7*u);
    ctx.globalAlpha=.45;ctx.fillStyle='#0a2233';ctx.beginPath();ctx.ellipse(fx,fy+4,len*.55,len*.18,Math.sin(t*3)*.15,0,7);ctx.fill();ctx.globalAlpha=1;
    if(F.f.dl>0){ring(fx,fy,.4);}
  }
  bank(ctx,g,S,night);
  drawLake(ctx,g,F.lake||NOBODY,t,{cam:F.cam,sp:g.sp,scale:g.scale,py:g.py,dpr:F.dims.dpr,dark:night,api:F.env?.api,spOf,rarOf:rar,junkEmoji:id=>(C()?.junk||[]).find(j=>j.id===id)?.emoji,calm:CALM});
  dock(ctx,g,night);
  lineAndBobber(ctx,g,t);
  player(ctx,g,t,night);
  // splashes
  for(const p of F.fx){const a=t-p.t0;if(a>p.life)continue;ctx.globalAlpha=1-a/p.life;ctx.fillStyle=p.c;ctx.beginPath();ctx.arc(p.x+p.vx*a,p.y-p.vy*a+260*a*a,2.2,0,7);ctx.fill();}
  ctx.globalAlpha=1;F.fx=F.fx.filter(p=>t-p.t0<p.life);
  if(F.jump)leap(ctx,t);
  if(rain){
    if(!F.drops.length)for(let i=0;i<70;i++)F.drops.push([Math.random()*w,Math.random()*h,300+Math.random()*200]);
    ctx.strokeStyle='rgba(220,235,245,.45)';ctx.lineWidth=1;ctx.beginPath();
    for(const d of F.drops){const y=(d[1]+t*d[2])%h;ctx.moveTo(d[0],y);ctx.lineTo(d[0]-3,y+10);}
    ctx.stroke();
  }
}
function isNight(){const hr=(new Date(Date.now()+7*3600000)).getUTCHours();return hr<6||hr>=18;}
function shadeHex(hex,k){const m=/^#?([0-9a-f]{6})$/i.exec(String(hex||''));if(!m)return hex;const n=parseInt(m[1],16);return `rgb(${Math.round((n>>16&255)*k)},${Math.round((n>>8&255)*k)},${Math.round((n&255)*k)})`;}
function farShore(ctx,g,S,night,t){
  const {w}=g,y=g.hor;
  ctx.fillStyle=night?'#16263a':shadeHex(S.shore,.75);
  if(F.spot==='ho'){   // trees and the town's roofs
    ctx.fillRect(0,y-8,w,10);
    for(let i=0;i<12;i++){const x=i*w/11,hh=10+((i*37)%9);ctx.fillStyle=night?'#122033':'#3f7f4a';ctx.beginPath();ctx.arc(x,y-6,hh*.7,0,7);ctx.fill();}
    for(let i=0;i<5;i++){const x=w*.12+i*w*.19;ctx.fillStyle=night?'#2a3550':'#d9cbb4';ctx.fillRect(x,y-20,16,14);ctx.fillStyle=night?'#40304a':'#c0533a';ctx.beginPath();ctx.moveTo(x-3,y-20);ctx.lineTo(x+8,y-29);ctx.lineTo(x+19,y-20);ctx.fill();
      if(night){ctx.fillStyle='#ffd77a';ctx.fillRect(x+6,y-15,4,4);}}
  }else if(F.spot==='song'){   // the far bank and a bridge
    ctx.fillRect(0,y-6,w,8);ctx.strokeStyle=night?'#2c3b55':'#7c6a55';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(w*.05,y-4);ctx.quadraticCurveTo(w*.5,y-34,w*.95,y-4);ctx.stroke();
    ctx.lineWidth=1.5;for(let i=1;i<10;i++){const x=w*.05+i*w*.09,yy=y-4-30*Math.sin(Math.PI*i/10);ctx.beginPath();ctx.moveTo(x,yy);ctx.lineTo(x,y-4);ctx.stroke();}
  }else if(F.spot==='bien'){   // the horizon, a ship, a lighthouse
    ctx.fillStyle=night?'#0f2140':'#9cc9e6';ctx.fillRect(0,y-3,w,4);
    const sx=(t*6)%(w+80)-40;ctx.fillStyle=night?'#2c3550':'#5b6470';ctx.fillRect(sx,y-10,34,7);ctx.fillRect(sx+8,y-17,12,7);
    ctx.fillStyle=night?'#2a3550':'#f2f2f2';ctx.fillRect(w*.86,y-34,8,32);ctx.fillStyle='#d23b3b';ctx.fillRect(w*.86,y-26,8,5);
    if(night){ctx.fillStyle=`rgba(255,240,170,${.5+.5*Math.sin(t*2)})`;ctx.beginPath();ctx.arc(w*.86+4,y-37,4,0,7);ctx.fill();}
  }else{   // 🏝️ palm islets
    for(const [cx,r] of [[w*.2,26],[w*.72,34]]){ctx.fillStyle=night?'#22304a':'#f1dfa6';ctx.beginPath();ctx.ellipse(cx,y,r,6,0,Math.PI,0);ctx.fill();
      ctx.strokeStyle=night?'#1a2a3a':'#7a5a2a';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(cx,y-4);ctx.quadraticCurveTo(cx+4,y-18,cx+2,y-28);ctx.stroke();
      ctx.fillStyle=night?'#183020':'#2f9a4a';for(let k=0;k<5;k++){const a=-Math.PI+k*Math.PI/4;ctx.beginPath();ctx.ellipse(cx+2+Math.cos(a)*9,y-28+Math.sin(a)*4,10,3,a,0,7);ctx.fill();}}
  }
}
const ZN=['Gần','Vừa','Xa','Sâu'];
/** The buoys for a lake `M` metres deep: round distances, each about twice the one before, up to the rod's longest. */
function marks(M){
  const top=M/1.08,out=[];
  for(const m of MARKS){if(m<M*.08||m>top)continue;if(!out.length||m>=out[out.length-1]*1.8)out.push(m);}
  return out.slice(-4);
}
/** The rod's zones (where Vừa, Xa, Sâu start for the rod in hand) as bands, and its buoys. No reach line: the cast is random. */
function zones(ctx,g,night){
  const zs=C()?.zones||ZN.map(name=>({name})),cut=myRod().zones||[62,100,150];
  ctx.font='700 11px system-ui,sans-serif';ctx.textBaseline='middle';
  zs.forEach((z,i)=>{
    const from=Math.min(i?Number(cut[i-1])||0:0,g.M),to=Math.min(i<cut.length?Number(cut[i])||0:g.M,g.M),y0=g.yOf(from),y1=g.yOf(to);if(to<=from)return;
    ctx.fillStyle=i%2?'rgba(255,255,255,.035)':'rgba(0,20,40,.06)';ctx.fillRect(0,y1,g.w,y0-y1);
    if(y0-y1<13)return;
    ctx.fillStyle=night?'rgba(220,235,255,.55)':'rgba(255,255,255,.75)';ctx.textAlign='left';ctx.fillText(z.name||ZN[i],8,(y0+y1)/2);
  });
  ctx.textAlign='center';
  for(const m of marks(g.M)){
    const y=g.yOf(m),hw=g.half(y),s=.55+.45*(y-g.hor)/(g.shore-g.hor);
    for(const x of [g.px-hw*.92,g.px+hw*.92]){ctx.fillStyle='#ff6a3d';ctx.beginPath();ctx.arc(x,y-3*s,4.5*s,0,7);ctx.fill();ctx.fillStyle='#fff';ctx.fillRect(x-4.5*s,y-3.5*s,9*s,1.6*s);}
    ctx.fillStyle='rgba(255,255,255,.85)';ctx.font=`700 ${Math.round(9+3*s)}px system-ui,sans-serif`;ctx.fillText(shortM(m),g.px+hw*.92,y-12*s);
  }
}
function waves(ctx,g,t,night){
  if(!F.waves){F.waves=[];for(let i=0;i<46;i++)F.waves.push([Math.random(),Math.random(),Math.random()*6]);}
  ctx.strokeStyle=night?'rgba(180,210,255,.18)':'rgba(255,255,255,.35)';ctx.lineWidth=1.2;ctx.beginPath();
  for(const [fx,fd,ph] of F.waves){const y=g.yOf(fd*g.M),hw=g.half(y),x=g.px+(fx*2-1)*hw+Math.sin(t*.6+ph)*6,len=4+10*(y-g.hor)/(g.shore-g.hor);
    if(Math.sin(t*.9+ph)<-.3)continue;ctx.moveTo(x-len,y);ctx.quadraticCurveTo(x,y-2.5,x+len,y);}
  ctx.stroke();
}
function bank(ctx,g,S,night){
  const {w,h}=g;
  ctx.fillStyle=night?shadeHex(S.shore,.45):S.shore;ctx.fillRect(0,g.shore,w,h-g.shore);
  ctx.fillStyle=night?'rgba(0,0,0,.18)':'rgba(255,255,255,.18)';ctx.fillRect(0,g.shore,w,4);
  ctx.fillStyle=night?'rgba(255,255,255,.04)':'rgba(0,0,0,.06)';for(let i=0;i<w;i+=18)ctx.fillRect(i+((i*7)%9),g.shore+14+((i*13)%40),6,2);
}
function dock(ctx,g,night){
  const x=g.px-24,y=g.shore-34;
  ctx.fillStyle=night?'#4a3a28':'#9a6b3c';ctx.fillRect(x,y,48,40);
  ctx.strokeStyle=night?'#2e2416':'#6e4a26';ctx.lineWidth=1;for(let i=1;i<6;i++){ctx.beginPath();ctx.moveTo(x,y+i*7);ctx.lineTo(x+48,y+i*7);ctx.stroke();}
  ctx.fillStyle=night?'#3a2c1c':'#7a5230';ctx.fillRect(x-3,y-2,6,14);ctx.fillRect(x+45,y-2,6,14);
}
/** The rod: its butt in the hands, its tip `a` radians right of straight up (the water); charging swings it back. */
function rodTip(g,t){
  let a=.35;
  if(F.phase==='charge')a=.35+1.5*F.power;
  else if(F.phase==='fight'&&F.f)a=.45+.5*F.f.tau+Math.sin(t*20)*.03*F.f.tau;
  else if(F.phase==='fly'||F.phase==='casting')a=.08;
  const L=(58+40*g.scale)*rodLook(P().rod).len,bx=g.px+24*g.scale,by=g.py-40*g.scale;   // 🎣 a better rod is longer
  return {bx,by,x:bx+Math.sin(a)*L,y:by-Math.cos(a)*L,a};
}
function lineAndBobber(ctx,g,t){
  const tip=rodTip(g,t),id=P().rod;
  const bend=F.phase==='fight'&&F.f?F.f.tau*16:0,R={bx:tip.bx,by:tip.by,cx:(tip.bx+tip.x)/2+bend*.3,cy:(tip.by+tip.y)/2-bend*.2,x:tip.x+bend*.5,y:tip.y+bend,s:1,t,calm:CALM};
  drawRod(ctx,id,R);   // 🎣 each rod its own look (v4/fish-rod.js)
  const [tx,ty]=rodTipOf(id,R),lc=lineColor(id);
  if(!F.bob||F.phase==='jump')return;
  let bx,by;
  if(F.phase==='fly'&&F.bob){
    const target=bobXY(),end=(F.r?.splashL)||F.castL+1,u=clamp((t-F.castL)/Math.max(.3,end-F.castL),0,1);
    bx=tx+(target[0]-tx)*u;by=ty+(target[1]-ty)*u-Math.sin(Math.PI*u)*(40+130*clamp(F.bob.d/g.M,0,1));
  }else if(F.phase==='fight'||F.phase==='landing'){
    [bx,by]=F.f?fishXY():bobXY();
  }else{
    [bx,by]=bobXY();
    by+=Math.sin(t*2.2)*1.4+F.bob.dip*(F.phase==='bite'||F.phase==='hooking'?9:6);
  }
  const snapped=F.line?.snap&&t-F.line.snap<1.2;
  ctx.strokeStyle=lc;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(tx,ty);
  if(snapped){ctx.quadraticCurveTo(tx+10,ty+30,tx+4,ty+60);ctx.stroke();return;}
  const sag=F.phase==='fight'&&F.f?(1-F.f.tau)*30:22;
  ctx.quadraticCurveTo((tx+bx)/2,Math.max(ty,by)-(Math.abs(by-ty)*.25)+sag,bx,by);ctx.stroke();
  if(F.phase==='fight'||F.phase==='landing')return;
  // the bobber
  ctx.fillStyle='#ffffff';ctx.beginPath();ctx.arc(bx,by-3,4,Math.PI,0);ctx.fill();
  ctx.fillStyle='#e8392b';ctx.beginPath();ctx.arc(bx,by-3,4,0,Math.PI);ctx.fill();
  ctx.fillStyle='#222';ctx.fillRect(bx-.6,by-11,1.2,5);
  if(F.phase==='bite'||F.phase==='hooking'){
    let top=28;
    if(F.phase==='bite'&&F.r?.shownL){   // the countdown: a glowing ring that shrinks and empties as the window runs out
      const left=clamp(1-(t-F.r.shownL)/F.r.window,0,1),R=15+21*left,col=left>.5?'#3ddc84':left>.25?'#ffd34d':'#ff4d3d';
      ctx.save();ctx.lineCap='round';
      ctx.strokeStyle='rgba(255,255,255,.28)';ctx.lineWidth=4;ctx.beginPath();ctx.arc(bx,by-3,R,0,7);ctx.stroke();
      ctx.shadowColor=col;ctx.shadowBlur=16;ctx.strokeStyle=col;ctx.lineWidth=5;
      ctx.beginPath();ctx.arc(bx,by-3,R,-Math.PI/2,-Math.PI/2+2*Math.PI*left);ctx.stroke();
      ctx.shadowBlur=0;ctx.fillStyle='#fff';ctx.font='900 13px system-ui,sans-serif';ctx.textAlign='center';ctx.textBaseline='top';
      ctx.strokeStyle='rgba(0,0,0,.55)';ctx.lineWidth=3;const txt=`${(left*F.r.window).toFixed(1).replace('.',',')}s`;
      ctx.strokeText(txt,bx,by+R+2);ctx.fillText(txt,bx,by+R+2);
      ctx.restore();top=R+16;
    }
    const s=1+.15*Math.sin(t*18);ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(bx,by-top,13*s,0,7);ctx.fill();
    ctx.fillStyle='#e8392b';ctx.font=`900 ${Math.round(20*s)}px system-ui,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('!',bx,by-top+1);
  }
}
/** Me, as my character (look.js figure: the look, the wings, the fish carried), painted once into a canvas (fish-lake.js
 * sprite) and leaning back with the cast and the fight; with others here a small "Bạn" over my head and my bubble. */
function player(ctx,g,t,night){
  const x=g.px,y=g.py;
  const lean=F.phase==='charge'?-F.power*4:F.phase==='fight'&&F.f?-F.f.tau*5:0;
  if(!F.meFig){try{F.meFig=figure(F.env?.api?.state);}catch{F.meFig=null;}}
  ctx.save();ctx.translate(x,y);ctx.rotate(lean*Math.PI/180);
  ctx.fillStyle='rgba(0,0,0,.25)';ctx.beginPath();ctx.ellipse(0,4,30*g.scale,4,0,0,7);ctx.fill();
  const s=F.meFig?sprite(null,null,{},g.scale,F.dims.dpr,F.meFig):null;
  if(s)ctx.drawImage(s.cv,-s.ox,-s.oy,s.w,s.h);
  ctx.restore();
  const said=F.lake?.self.said;let top=y-128*g.scale-6;
  if(F.lake?.peers.size){ctx.font='800 10px system-ui,sans-serif';const tw=ctx.measureText('Bạn').width+12;
    ctx.fillStyle='#ffd34d';ctx.beginPath();if(ctx.roundRect)ctx.roundRect(x-tw/2,top-15,tw,15,7);else ctx.rect(x-tw/2,top-15,tw,15);ctx.fill();
    ctx.fillStyle='#3a2a00';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('Bạn',x,top-7.5);top-=18;}
  if(said){const age=t-said.t0;if(age>6)F.lake.self.said=null;else bubble(ctx,x,top,said.text,age>5.5?(6-age)/.5:1,night);}
}
const NOBODY={peers:new Map(),self:{}};
const CALM=(()=>{try{return matchMedia('(prefers-reduced-motion: reduce)').matches;}catch{return false;}})();
function leap(ctx,t){
  const j=F.jump,u=clamp((t-j.t0)/j.dur,0,1);
  const x=j.x0+(j.x1-j.x0)*u,y=j.y0+(j.y1-j.y0)*u-Math.sin(Math.PI*u)*(90+(j.big?j.len*.3:0));
  if(j.sp)drawFish(ctx,j.sp,x,y,j.len,{angle:u>=1&&j.big?0:Math.sin(t*14)*.3-.4+u*.6,flip:j.big||j.x1<j.x0,wiggle:(t*3)%1});
  else{ctx.font='28px system-ui,sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(j.junk?.emoji||'🥾',x,y);}
}

/* ---------------------------------------------------------------- HUD and meters */
function paintSpots(){
  const nav=F.dlg?.querySelector('.fs-spots');if(!nav)return;
  const ids=F.trip?['dao']:['ho','song','bien'];
  nav.innerHTML=ids.map(id=>{const s=spotOf(id);return `<button type="button" class="fs-spot${id===F.spot?' on':''}" data-fs="spot" data-id="${esc(id)}" aria-pressed="${id===F.spot}">${esc(s.emoji)} ${esc(s.name)}</button>`;}).join('');
}
function paintHud(){
  if(!F.dlg)return;
  const p=P(),rod=myRod(),b=(C()?.baits||[]).find(x=>x.id===p.use),n=b?p.bait?.[b.id]||0:0;
  const gear=F.dlg.querySelector('.fs-gear');gear.textContent=`${rod.emoji} ${rod.name} · ${b?`${b.emoji} ×${fmt(n)}`:'không mồi'}`;
  gear.setAttribute('aria-label',`${rod.name}, ${b?`${b.name?`mồi ${b.name}`:'mồi'} ×${fmt(n)}`:'không mồi'}. Quầy bán cần`);
  const bag=F.dlg.querySelector('.fs-bagb'),cnt=(p.bag||[]).length;bag.textContent=`🧺 ${cnt}/${p.cap||20}`;bag.setAttribute('aria-label',`Giỏ cá ${cnt}/${p.cap||20}. Quầy thu mua`);bag.classList.toggle('full',cnt>=(p.cap||20));
  const c=p.cond||{},night=c.night!=null?c.night:isNight();
  F.dlg.querySelector('.fs-sky').textContent=`${night?'🌙':'☀️'}${c.rain?' 🌧️':''}`;
  F.dlg.querySelector('.fs-sky').title=`${night?'Ban đêm':'Ban ngày'}${c.rain?', trời mưa':''}: có loài chỉ cắn câu lúc này`;
}
function paintTop3(){
  const ol=F.dlg?.querySelector('.fs-top3');if(!ol)return;
  const top=F.rec?.tops?.fish_big||[];
  ol.innerHTML=top.length?top.slice(0,3).map(r=>`<li class="${r.me?'me':''}">${MEDAL[r.rank-1]||''} <span data-no-translate>${esc(r.name||'?')}</span> ${esc(fmtKg(r.score))}</li>`).join('')
    :'<li>🐋 Chưa ai lên bảng</li><li>Câu con đầu tiên nào!</li>';
}
function paintGo(tip){
  const b=F.dlg?.querySelector('.fs-go'),s=F.dlg?.querySelector('.fs-tip');if(!b)return;
  const ph=F.phase;b.className='fs-go'+(ph==='bite'?' hook':ph==='fight'?' reel':['wait','casting','fly','hooking','landing','jump','lost'].includes(ph)?' wait':'');
  b.textContent={idle:'🎣 Giữ để quăng',card:'🎣 Giữ để quăng tiếp',charge:'Thả tay để quăng!',casting:'Vút…',fly:'Vút…',wait:'Chờ phao chìm… (chạm = Giật)',bite:'❗ GIẬT!',hooking:'Giật!',
    fight:'💪 Giữ để kéo · thả để nhả',landing:'Đang kéo lên…',jump:'Lên rồi!',lost:'…'}[ph]||'🎣';
  if(s)s.textContent=tip!=null&&tip!==''?tip:{idle:'Giữ rồi thả để quăng, xa gần hên xui!',card:'Giữ rồi thả để quăng, xa gần hên xui!',charge:'Thả tay là bay! Đầy vạch thì xa hơn chút.',wait:'Phao rung nhẹ là cá rỉa. Phao chìm hẳn + “!” mới giật.',
    bite:'Chạm Giật trước khi vòng sáng tắt!',fight:'Giữ để kéo, vạch nháy đỏ thì thả tay.'}[ph]||'';
}
function meters(){
  const d=F.dlg;if(!d)return;
  d.querySelector('.fs-meter').hidden=F.phase!=='charge';d.querySelector('.fs-pow').hidden=F.phase!=='charge';
  d.querySelector('.fs-ten').hidden=!(F.phase==='fight');
  if(F.phase==='fight'&&F.f){const bar=d.querySelector('.fs-ten-bar b');bar.style.left=`${(MID-F.f.green/2)*100}%`;bar.style.width=`${F.f.green*100}%`;}
}
function paintMeter(){
  const d=F.dlg;if(!d)return;
  const m=d.querySelector('.fs-meter'),p=d.querySelector('.fs-pow'),full=F.power>=1;
  m.querySelector('i').style.height=`${F.power*100}%`;m.classList.toggle('full',full);
  p.textContent=full?'🔥 Hết cỡ!':`💪 ${Math.round(F.power*100)}%`;
  p.style.top=`${m.offsetTop+m.offsetHeight*(1-F.power)-10}px`;
}
function paintTension(){
  const d=F.dlg,f=F.f;if(!d||!f)return;
  d.querySelector('.fs-ten-bar i').style.left=`${f.tau*100}%`;
  d.querySelector('.fs-prog i').style.width=`${f.prog*100}%`;
  d.querySelector('.fs-ten').classList.toggle('red',f.tau>RED);
}
function say(text,ms=3200){
  const el=F.dlg?.querySelector('.fs-say');if(!el||!text)return;
  el.textContent=text;el.hidden=false;clearTimeout(F.msgT);F.msgT=setTimeout(()=>{el.hidden=true;},ms);
}

/* ---------------------------------------------------------------- the catch card */
function showCard(land,res){
  F.jump=null;F.r=null;F.bob=null;F.phase='card';paintGo();distFx(null);
  const el=F.dlg?.querySelector('.fs-card');if(!el)return;
  if(land.res==='junk'){
    const j=(C()?.junk||[]).find(x=>x.id===land.junk)||{emoji:'🥾',name:'Rác'};
    el.style.setProperty('--rc','#9aa7b0');
    el.innerHTML=`<div style="font-size:64px">${esc(j.emoji)}</div><h3>${esc(j.name)}</h3><p class="fs-price">${esc(res.message||'Coi như dọn sạch hồ!')}</p><div class="fs-card-acts"><button type="button" class="fs-btn primary" data-fs="again">🎣 Câu tiếp</button></div>`;
    el.hidden=false;return;
  }
  const c=land.catch,sp=spOf(c.s)||{id:c.s,name:c.s,r:c.r},R=rar(c.r),fx=(res.effects||[]).filter(x=>!/Kỷ lục loài/.test(x));
  el.style.setProperty('--rc',R.color||RARITY_COLORS[c.r]);
  const ban=c.rec?'<span class="fs-ban rec">🏆 Kỷ lục mới của cả phố!</span>':c.new?'<span class="fs-ban new">📖 Loài mới vào Sổ cá!</span>':c.pb?'<span class="fs-ban pb">🏅 Kỷ lục mới của bạn!</span>':'';
  el.innerHTML=`${c.r>=5?`<div class="fs-confetti">${Array.from({length:26},(_,i)=>`<i style="left:${(i*37)%100}%;background:${['#ffcf26','#ff8a1c','#ff3b3b','#3d7bff','#43b05c','#a855f7'][i%6]};animation-delay:${(i%7)*.08}s"></i>`).join('')}</div>`:''}
    ${ban}${fishSvg({...sp,r:c.r},{w:220,h:110,title:sp.name})}<h3>${esc(sp.name)}</h3><span class="fs-rar">${esc(R.emoji)} ${esc(R.name)}</span>
    <p class="fs-kg">${esc(fmtKg(c.g))} <small>📏 ${esc(fmtLen(c.g/1000))}</small></p><div class="fs-scale">${scaleSvg({...sp,r:c.r},c.g/1000,{title:`Cá dài ${fmtLen(c.g/1000)}, so với người`})}</div><p class="fs-price">Giá lái: ~${fmt(c.price)} xu · ${esc(spotOf(c.spot).emoji)} ${esc(spotOf(c.spot).name)}</p>
    ${fx.length?`<ul class="fs-fx">${fx.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:''}
    <div class="fs-card-acts"><button type="button" class="fs-btn primary" data-fs="again">🎣 Câu tiếp</button>${c.r>=(C()?.carry_min||3)?`<button type="button" class="fs-btn blue" data-fs="carry" data-id="${c.i}">💪 Vác đi dạo</button>`:''}<button type="button" class="fs-btn" data-fs="release" data-id="${c.i}">🌊 Thả</button></div>`;
  el.hidden=false;
  if(c.r>=5)vibrate([50,40,50,40,200]);
  if(c.rec||c.new)loadRecords(true);
}
function hideCard(){const el=F.dlg?.querySelector('.fs-card');if(el){el.hidden=true;el.innerHTML='';}}

/* ---------------------------------------------------------------- actions */
async function act(a,ds){
  switch(a){
    case'close':if(F.panel){closePanel();return;}await close();return;
    case'spot':if(!['idle','card'].includes(F.phase)){say('Đang câu dở, xong con này đã nhé!');return;}
      if(ds.id&&ds.id!==F.spot){F.spot=ds.id;F.waves=null;hideCard();idle();paintSpots();joinLake();say(`${spotOf(F.spot).emoji} ${spotOf(F.spot).name}: ${spotOf(F.spot).hint||''}`);}return;
    case'again':hideCard();idle();return;
    case'feed':{const el=F.dlg.querySelector('.fs-feed-all');el.hidden=!el.hidden;if(!el.hidden)paintFeed();return;}
    case'feedPid':{const p=F.lake?.peers.get(ds.pid);if(p){lookAt(posOf(p.s));F.dlg.querySelector('.fs-feed-all').hidden=true;}return;}
    case'sayOpen':{   // only a real tap on 💬, never in the middle of a cast or a fight (#515)
      if(!ds.tap||F.pressing||['charge','hooking','fight'].includes(F.phase))return;
      const f=F.dlg.querySelector('.fs-sayrow');f.hidden=!f.hidden;if(!f.hidden)f.querySelector('input').focus();else noTyping();return;}
    case'sayClose':noTyping();F.dlg.querySelector('.fs-sayrow').hidden=true;return;
    case'pan':{const g=geo(),o=offscreen([...(F.lake?.peers.values()||[])],F.cam,g.sp,g.w),left=Number(ds.dir)<0,to=left?o.lp:o.rp;
      if(to!=null)lookAt(to+(left?1:-1)*Math.max(0,g.w/2/g.sp-1.5));return;}
    case'pcardX':hidePeerCard();return;
    case'home':F.vel=0;F.camTo=null;return;   // 📍 back to my place
    case'shop':case'market':case'board':case'dex':
      if(!['idle','card','lost'].includes(F.phase)){say('Đang câu dở, xong con này đã nhé!');return;}
      openPanel(a);return;
    case'panelX':closePanel();return;
    case'tab':F.tab[ds.p]=ds.t;if(ds.p==='board'&&ds.t!=='dex')loadBoard(ds.t);paintPanel();return;
    case'buy':{
      const kind=ds.kind,item=ds.item,n=Number(ds.n)||1;
      if(kind==='rod'||kind==='gio'){
        const x=kind==='rod'?rodOf(item):(C()?.baskets||[]).find(b=>b.id===item);
        if(x?.price>funds()){say(`Còn thiếu ${fmt(x.price-funds())} xu (tính cả ví và ngân hàng).`);return;}
        if(x?.price>0&&F.env.confirmAction&&!(await F.env.confirmAction(`Mua ${x.name}?`,`Giá ${fmt(x.price)} xu. Trả từ ví (${fmt(wallet())} xu) trước, thiếu thì lấy ngân hàng (${fmt(bankBal())} xu).`,'Mua')))return;
      }
      const r=await send('jr_fish_buy',{kind,item,...(kind==='bait'&&n>1?{n}:{})});if(r?.message)say(r.message);paintPanel();return;}
    case'equip':{const r=await send('jr_fish_equip',ds.rod!=null?{rod:ds.rod}:{bait:ds.bait||''});if(r?.message)say(r.message);paintPanel();return;}
    case'sell':case'sellAll':{
      const ids=a==='sell'?[Number(ds.id)]:sellable().map(f=>f.i);if(!ids.length){say('Không có cá nào để bán.');return;}
      const r=await send('jr_fish_sell',{ids});if(r){say(r.message||'');F.open=-1;paintPanel();}return;}
    case'deal':{const r=await send('jr_fish_deal',{pick:ds.pick});if(r){say(r.message||'',4200);paintPanel();}return;}
    case'keep':{const f=(P().bag||[]).find(x=>x.i===Number(ds.id));if(!f)return;const r=await send('jr_fish_keep',{id:f.i,on:!f.k});if(r)paintPanel();return;}
    case'release':{
      const id=Number(ds.id),r=await send('jr_fish_release',{ids:[id]});
      if(r){say([r.message,...(r.effects||[])].filter(Boolean).join(' '));if(F.phase==='card'){hideCard();idle();const g=geo();ring(g.px,g.yOf(4),1.4);}F.open=-1;paintPanel();}return;}
    case'carry':{const id=Number(ds.id),on=P().carry!==id||F.phase==='card';const r=await send('jr_fish_carry',{id:on?id:0});if(r){say(r.message||'');paintPanel();}return;}
    case'mount':{const id=Number(ds.id);F.mnt=F.mnt?.id===id?null:{id,sz:'lon',bg:'kem'};paintPanel();return;}   // 🖼️ choose the size and background first (#517)
    case'mntSz':if(F.mnt&&['lon','nho'].includes(ds.sz)){F.mnt.sz=ds.sz;paintPanel();}return;
    case'mntBg':if(F.mnt&&TRO_BG[ds.bg]){F.mnt.bg=ds.bg;paintPanel();}return;
    case'mntGo':{const m=F.mnt;if(!m)return;
      const r=await send('jr_fish_mount',{id:m.id,...(m.sz!=='lon'?{sz:m.sz}:{}),...(m.bg!=='kem'?{bg:m.bg}:{})});
      if(r){say(r.message||'',4200);F.mnt=null;F.open=-1;paintPanel();}return;}
    case'aqua':{const r=await send('jr_fish_aqua',ds.out!=null?{out:Number(ds.out)}:{id:Number(ds.id)});if(r){say(r.message||'');F.open=-1;paintPanel();}return;}
    case'row':F.open=F.open===Number(ds.id)?-1:Number(ds.id);paintPanel();return;
    case'sp':F.detail=ds.id;paintPanel();return;
    case'spBack':F.detail=null;paintPanel();return;
  }
}
const sellable=()=>(P().bag||[]).filter(f=>!f.k&&!(f.o<0));   // not ⭐ kept, not refused today

/* ---------------------------------------------------------------- the sheets */
function openPanel(kind){
  F.panel=kind==='dex'?'board':kind;if(kind==='dex')F.tab.board='dex';F.detail=null;F.open=-1;F.mnt=null;
  if(F.panel==='board'){loadRecords();if(F.tab.board!=='dex')loadBoard(F.tab.board);}
  paintPanel();
}
function closePanel(){F.panel=null;F.detail=null;const el=F.dlg?.querySelector('.fs-panel');if(el){el.hidden=true;el.innerHTML='';}}
function paintPanel(){
  const el=F.dlg?.querySelector('.fs-panel');if(!el||!F.panel)return;
  const keep=el.querySelector('.fs-pb')?.scrollTop||0;
  const [title,body]=F.panel==='shop'?['🎣 Quầy bán cần',shopHTML()]:F.panel==='market'?['🐟 Quầy thu mua',marketHTML()]:['📖 Bảng bộ sưu tập',boardHTML()];
  el.innerHTML=`<header class="fs-ph"><h3>${title}</h3><button type="button" class="fs-x" data-fs="panelX" aria-label="Đóng">✕</button></header><div class="fs-pb">${body}</div>${F.panel==='market'?dealHTML():''}`;
  el.hidden=false;const pb=el.querySelector('.fs-pb');if(pb)pb.scrollTop=keep;
}
const tabs=(p,list)=>`<div class="fs-tabs" role="tablist">${list.map(([id,label])=>`<button type="button" role="tab" class="${F.tab[p]===id?'on':''}" aria-selected="${F.tab[p]===id}" data-fs="tab" data-p="${p}" data-t="${id}">${label}</button>`).join('')}</div>`;
const fbtn=(label,a,data={},cls='')=>`<button type="button" class="fs-btn small ${cls}" data-fs="${a}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(String(v))}"`).join('')}>${label}</button>`;

function shopHTML(){
  const p=P(),c=C(),t=F.tab.shop;
  let out=tabs('shop',[['rod','🎣 Cần câu'],['bait','🪱 Mồi'],['gio','🧺 Giỏ']])+`<p class="fs-note">👛 Ví: <b>${fmt(wallet())} xu</b>${bankBal()?` · 🏦 Ngân hàng: <b>${fmt(bankBal())} xu</b>`:''}</p>`;
  if(t==='rod'){
    out+=`<p class="fs-note">Cần xịn quăng xa hơn (📏 xa gần hên xui, ra vùng Xa, Sâu có cá to), dây chịu cá nặng hơn, ra cá hiếm và cá to nhiều hơn hẳn.</p><p class="fs-note">🍀 Tỷ lệ mỗi hạng cá khi quăng tới vùng xa nhất của cần (chưa tính chỗ câu, mồi).</p><p class="fs-note">Mua cần nào cũng được, không cần mua theo thứ tự.</p><ul class="fs-list">${c.rods.map(r=>{
      const own=(p.rods||[]).includes(r.id),cur=p.rod===r.id;
      return `<li class="fs-item${cur?' cur':''}"><span class="fs-ico fs-rodico" style="--c:${esc(r.color||'#eee')}">${rodSvg(r.id,40)}<i>${esc(r.emoji)}</i></span><div class="fs-it"><b>${esc(r.name)}</b><small>📏 ${esc(reachTxt(reachOf(r)))} · 🧵 ${esc(kgLine(r.line))}</small>${oddsHTML(r)}<small>⏱️ Giật ${secs(r.hook||C()?.hook_window||1)}</small>${r.ancient?'<small class="fs-anc">🔴 Câu được cá Cổ đại</small>':''}</div>
        ${cur?'<span class="fs-tag">Đang cầm</span>':own?fbtn('Cầm','equip',{rod:r.id}):fbtn(r.price?`${fmt(r.price)} xu`:'Miễn phí','buy',{kind:'rod',item:r.id},'primary')}</li>`;}).join('')}</ul>`;
  }else if(t==='bait'){
    out+=`<p class="fs-note">Mồi tốt tăng cơ hội gặp cá hiếm. Mỗi lần quăng tốn 1 mồi đang dùng.</p><ul class="fs-list"><li class="fs-item${!p.use?' cur':''}"><span class="fs-ico">🎣</span><div class="fs-it"><b>Không mồi đặc biệt</b><small>Mồi cơm thường, miễn phí</small></div>${!p.use?'<span class="fs-tag">Đang dùng</span>':fbtn('Dùng','equip',{bait:''})}</li>
      ${c.baits.map(b=>{const have=p.bait?.[b.id]||0,cur=p.use===b.id;
        return `<li class="fs-item${cur?' cur':''}"><span class="fs-ico">${esc(b.emoji)}</span><div class="fs-it"><b>${esc(b.name)}${have?` · còn ${fmt(have)}`:''}</b><small>${esc(b.hint||'')}</small>${b.hook>0?`<small>⏱️ Giật +${secs(b.hook)}</small>`:''}<small>${fmt(b.price)} xu / ${fmt(b.n)} mồi</small></div>
        <span style="display:flex;flex-direction:column;gap:4px">${fbtn('Mua','buy',{kind:'bait',item:b.id},'primary')}${have?(cur?'<span class="fs-tag">Đang dùng</span>':fbtn('Dùng','equip',{bait:b.id})):fbtn('×5','buy',{kind:'bait',item:b.id,n:5})}</span></li>`;}).join('')}</ul>`;
  }else{
    out+=`<p class="fs-note">Giỏ to chứa được nhiều cá hơn trước khi phải ra quầy bán.</p><ul class="fs-list">${c.baskets.map((b,i)=>{
      const cur=(p.gio||0)===i,own=i<=(p.gio||0);
      return `<li class="fs-item${cur?' cur':''}"><span class="fs-ico">${esc(b.emoji||'🧺')}</span><div class="fs-it"><b>${esc(b.name)}</b><small>Chứa ${fmt(b.cap)} con</small></div>${cur?'<span class="fs-tag">Đang dùng</span>':own?'<span class="fs-tag">Đã có</span>':fbtn(b.price?`${fmt(b.price)} xu`:'Miễn phí','buy',{kind:'gio',item:b.id},'primary')}</li>`;}).join('')}</ul>`;
  }
  return out;
}

function bagSorted(){return (P().bag||[]).slice().sort((a,b)=>((spOf(b.s)?.r||0)-(spOf(a.s)?.r||0))||(b.g-a.g));}
function marketHTML(){
  const p=P(),bag=bagSorted(),sell=sellable(),sum=sell.reduce((a,f)=>a+priceOf(f),0);
  let out=`<p class="fs-note">🧺 Giỏ ${fmt(bag.length)}/${fmt(p.cap||20)} con. Lái cá đôi khi trả giá thấp: chốt luôn, mặc cả, hoặc giữ cá bán sau.</p>`;
  out+=sell.length?`<div class="fs-sum"><span>Bán hết ${fmt(sell.length)} con (trừ ⭐ đang giữ): ~${fmt(sum)} xu</span>${fbtn('💰 Bán hết','sellAll',{},'primary')}</div>`:'';
  if(!bag.length)out+='<p class="fs-empty">Giỏ trống trơn. Ra hồ câu vài con đã nhé! 🎣</p>';
  out+=`<ul class="fs-list">${bag.map(f=>{
    const sp=spOf(f.s)||{name:f.s,r:0},R=rar(sp.r),price=priceOf(f),open=F.open===f.i;
    const off=f.o<0?'<small class="fs-off">Lái không mua con này hôm nay</small>':f.o>0?`<small class="fs-off">Lái trả ${f.o}%: ~${fmt(Math.floor(price*f.o/100))} xu</small>`:'';
    return `<li class="fs-fish" style="--rc:${esc(R.color||'#ccc')}">${fishSvg(sp,{w:64,h:32})}<div class="fs-it"><b>${esc(sp.name)}${f.k?' ⭐':''}${p.carry===f.i?' 💪':''}</b><small>${esc(fmtKg(f.g))} · 📏 ${esc(fmtLen(f.g/1000))} · ${esc(R.name)} · ~${fmt(price)} xu</small>${off}</div>
      <span style="display:flex;gap:4px">${f.o<0?'':fbtn('Bán','sell',{id:f.i},'primary')}${fbtn(open?'▴':'⋯','row',{id:f.i})}</span>
      ${open?`<div class="fs-fish-acts">${fbtn(f.k?'☆ Bỏ giữ':'⭐ Giữ','keep',{id:f.i})}${sp.r>=(C()?.carry_min||3)?fbtn(p.carry===f.i?'🧺 Cất':'💪 Vác','carry',{id:p.carry===f.i?0:f.i}):''}${fbtn('🖼️ Treo tranh','mount',{id:f.i},F.mnt?.id===f.i?'on':'')}${fbtn('🐠 Thả bể','aqua',{id:f.i})}${fbtn('🌊 Thả về hồ','release',{id:f.i})}</div>${F.mnt?.id===f.i?mountHTML(sp,f):''}`:''}</li>`;}).join('')}</ul>`;
  const aq=p.aq||[];
  out+=`<h4 style="margin:12px 0 4px">🐠 Bể cá ở nhà (${aq.length}/${C()?.aquarium||8})</h4>${aq.length?`<ul class="fs-list">${aq.map(([s,g],k)=>{const sp=spOf(s)||{name:s,r:0};return `<li class="fs-fish" style="--rc:${esc(rar(sp.r).color||'#ccc')}">${fishSvg(sp,{w:64,h:32})}<div class="fs-it"><b>${esc(sp.name)}</b><small>${esc(fmtKg(g))}</small></div>${fbtn('Vớt về giỏ','aqua',{out:k})}</li>`;}).join('')}</ul>`:'<p class="fs-note">Thả cá đẹp vào bể (có bể cá trong nhà thì cá bơi ở đó).</p>'}`;
  out+=`<p class="fs-note">🖼️ Tranh cá: ${Object.keys(p.tro||{}).length}/${C()?.trophies||12} (treo ở Trang trí nhà).</p>`;
  return out;
}
/** 🖼️ Treo tranh: big (2 × 2) or small (1 × 1), and the board's colour, with a preview; changeable later in Bày trí phòng. */
function mountHTML(sp,f){
  const m=F.mnt,[bg,top]=TRO_BG[m.bg]||TRO_BG.kem,small=m.sz==='nho',w=small?56:96,h=small?46:70;
  const pick=(a,k,label,on,extra='')=>`<button type="button" class="fs-btn small fs-mnt-opt${on?' on':''}" data-fs="${a}" data-${k[0]}="${esc(k[1])}" aria-pressed="${on}">${extra}${esc(label)}</button>`;
  return `<div class="fs-mnt" role="group" aria-label="Treo tranh cá">
    <div class="fs-mnt-pre" aria-hidden="true"><span class="fs-mnt-fr" style="width:${w}px;height:${h}px;background:linear-gradient(${top} 0 45%,${bg} 45%)">${fishSvg(sp,{w:w-14,h:h-22})}<i>${esc(fmtKg(f.g))}</i></span></div>
    <div class="fs-mnt-row"><small>Cỡ</small>${pick('mntSz',['sz','lon'],'Lớn 2×2',!small)}${pick('mntSz',['sz','nho'],'Nhỏ 1×1',small)}</div>
    <div class="fs-mnt-row"><small>Nền</small>${Object.keys(TRO_BG).map(k=>pick('mntBg',['bg',k],TRO_BG_NAMES[k],m.bg===k,`<i class="fs-mnt-sw" style="background:${TRO_BG[k][0]}"></i>`)).join('')}</div>
    ${fbtn('🖼️ Làm tranh','mntGo',{},'primary')}</div>`;
}
function dealHTML(){
  const d=P().deal;if(!d)return '';
  return `<div class="fs-deal" role="dialog" aria-label="Lái cá trả giá"><div class="fs-face">🧔🏻</div><b>Lái cá trả giá!</b>
    <p>“${fmt(d.ids.length)} con này anh trả <b>${fmt(d.offer)} xu</b> thôi” (giá đủ ${fmt(d.full)} xu, ${d.pct}%).</p>
    <div class="fs-card-acts">${fbtn('🤝 Chốt','deal',{pick:'accept'},'primary')}${fbtn('🗣️ Mặc cả','deal',{pick:'bargain'},'blue')}${fbtn('🙅 Thôi, giữ cá','deal',{pick:'decline'})}</div>
    <p class="fs-note" style="margin:8px 0 0">Mặc cả: có khi được đủ giá, có khi còn hơn, cũng có khi lái phẩy tay không mua nữa.</p></div>`;
}

/* 📖 Sổ cá + the boards */
function boardHTML(){
  const t=F.tab.board;
  let out=tabs('board',[['dex','📖 Sổ cá'],['fish_big','🐋 Cá lớn'],['fish_all','🐋 Mọi thời'],['fish_dex','📚 Sưu tập']]);
  if(t==='dex')return out+(F.detail?detailHTML(F.detail):dexHTML());
  return out+boardList(t);
}
function dexHTML(){
  const p=P(),c=C(),dex=p.dex||{},rec=F.rec?.records||{},ms=p.ms||[],have=id=>(dex[id]?.[0]||0)>0;
  const all=c.species.length,got=c.species.filter(s=>have(s.id)).length;
  let out=`<div class="fs-dex-head"><b>Đã câu ${fmt(got)}/${fmt(all)} loài</b><small>${fmt(p.tot?.fish||0)} con đã câu</small></div><div class="fs-bar2"><i style="width:${all?got/all*100:0}%"></i></div>`;
  out+=`<p class="fs-far">🎯 Cú quăng xa nhất: <b>${p.far>0?esc(fmtM(p.far)):'chưa có'}</b></p>`;
  const titles=new Map((c.titles||[]).map(x=>[x.id,x]));
  out+=`<details class="fs-ms"><summary><b>🎁 Phần thưởng sưu tập</b></summary><ul>
    ${c.rarities.map((R,r)=>`<li>${ms.includes(`r${r}`)?'<span class="fs-done">✓</span>':'○'} Đủ cá ${esc(R.emoji)} ${esc(R.name)}: +${fmt(c.tier_reward[r])} xu</li>`).join('')}
    ${c.spots.map(s=>`<li>${ms.includes(`s_${s.id}`)?'<span class="fs-done">✓</span>':'○'} Đủ cá ${esc(s.emoji)} ${esc(s.name)}: +${fmt(c.spot_reward)} xu + danh hiệu</li>`).join('')}
    <li>${ms.includes('all')?'<span class="fs-done">✓</span>':'○'} Đủ ${fmt(all)} loài: danh hiệu 🎣 Thần câu + khung riêng</li></ul>
    <p class="fs-note" style="margin:6px 0 0">Danh hiệu: ${[...titles.values()].map(x=>`${esc(x.emoji)} ${esc(x.name)}`).join(' · ')}</p></details>`;
  c.rarities.forEach((R,r)=>{
    const list=c.species.filter(s=>s.r===r),n=list.filter(s=>have(s.id)).length;
    out+=`<div class="fs-dex-head" style="--rc:${esc(R.color)}"><b>${esc(R.emoji)} ${esc(R.name)}</b><small>${n}/${list.length}${ms.includes(`r${r}`)?' · ✓ đã thưởng':` · thưởng ${fmt(c.tier_reward[r])} xu`}</small></div>
      <div class="fs-bar2" style="--rc:${esc(R.color)}"><i style="width:${list.length?n/list.length*100:0}%"></i></div><div class="fs-grid">${list.map(s=>{
        const row=dex[s.id],ok=have(s.id),rc=rec[s.id];
        if(!ok)return `<button type="button" class="fs-cell unk" data-fs="sp" data-id="${esc(s.id)}">${fishSvg(s,{w:80,h:40,silhouette:true})}<b>???</b><small>${esc(s.spots.map(x=>spotOf(x).emoji).join(''))}${s.cond?` ${esc(s.cond.split(' ')[0])}`:''}</small></button>`;
        return `<button type="button" class="fs-cell got" style="--rc:${esc(R.color)}" data-fs="sp" data-id="${esc(s.id)}">${row[1]?`<span class="fs-len" title="Con lớn nhất dài ${esc(fmtLen(row[1]/1000))}">📏 ${esc(fmtLen(row[1]/1000).replace('~',''))}</span>`:''}${fishSvg(s,{w:80,h:40})}<b>${esc(s.name)}</b><small>${row[1]?`🏅 ${esc(fmtKg(row[1]))} · `:''}×${fmt(row[0])}</small>${rc?`<small class="fs-rec">🏆 ${esc(fmtKg(rc.g))}${rc.me?' (bạn)':''}</small>`:''}</button>`;
      }).join('')}</div>`;
  });
  return out;
}
function detailHTML(id){
  const s=spOf(id);if(!s)return '';
  const row=P().dex?.[id],ok=(row?.[0]||0)>0,R=rar(s.r),rc=F.rec?.records?.[id];
  return `<div class="fs-detail">${fbtn('← Sổ cá','spBack')}<div>${fishSvg(s,{w:240,h:120,silhouette:!ok,title:ok?s.name:'?'})}</div><h3 style="margin:2px 0">${ok?esc(s.name):'???'}</h3><span class="fs-rar" style="display:inline-block;padding:2px 10px;border-radius:99px;background:${esc(R.color)};color:#fff;font-weight:800;font-size:12px">${esc(R.emoji)} ${esc(R.name)}</span>
    <dl><dt>Ở đâu</dt><dd>${s.spots.map(x=>`${esc(spotOf(x).emoji)} ${esc(spotOf(x).name)}`).join(', ')}</dd>${s.cond?`<dt>Khi nào</dt><dd>${esc(s.cond)}</dd>`:''}<dt>Gợi ý</dt><dd>${esc(s.hint||'')}</dd>
    ${ok?`<dt>Nặng</dt><dd>${esc(fmtKg(s.w[0]*1000))} – ${esc(fmtKg(s.w[1]*1000))}</dd><dt>Dài</dt><dd>${esc(fmtLen(s.w[0]))} – ${esc(fmtLen(s.w[1]))}</dd><dt>Bạn câu</dt><dd>${fmt(row[0])} con${row[1]?` · lớn nhất ${esc(fmtKg(row[1]))}`:''}</dd>${row[1]?`<dd class="fs-scale">${scaleSvg(s,row[1]/1000,{title:`Con lớn nhất dài ${fmtLen(row[1]/1000)}, so với người`})}</dd>`:''}`:''}
    <dt>Kỷ lục phố</dt><dd>${rc?`🏆 ${esc(fmtKg(rc.g))} · <span data-no-translate>${esc(rc.name)}</span>${rc.me?' (bạn)':''}`:'Chưa ai câu được'}</dd></dl></div>`;
}
async function loadBoard(board,force=false){
  const hit=F.boards[board];if(!force&&hit&&Date.now()-hit.at<30000)return;
  F.boards[board]={...(hit||{}),busy:true,at:hit?.at||0};
  try{const d=await F.env.api.json(`/api/leaderboard?board=${board}&limit=30`);F.boards[board]={...d,at:Date.now()};}
  catch(e){F.boards[board]={error:e?.message||'Chưa tải được bảng.',at:Date.now()};}
  if(F.panel==='board'&&F.tab.board===board)paintPanel();
}
function boardList(board){
  const d=F.boards[board];
  const rule={fish_big:'🐋 Con cá nặng nhất mỗi người câu trong tuần này (thứ Hai đến Chủ nhật, giờ Việt Nam).',fish_all:'🐋 Con cá nặng nhất mỗi người từng câu.',
    fish_dex:'📚 Số loài trong Sổ cá. Bằng nhau: nhiều loài hiếm hơn (🔴 trước), rồi ai đạt trước.'}[board];
  let out=`<p class="fs-note">${rule}</p>`;
  if(!d||(!d.rows&&!d.error))return out+'<p class="fs-empty">Đang tải…</p>';
  if(d.error)return out+`<p class="fs-empty">${esc(d.error)}</p>`;
  const w=d.weekly;
  if(w?.tiers?.length)out+=`<div class="fs-reward"><b>🏅 Danh hiệu & thưởng tuần</b><ul>${w.tiers.map(t=>`<li>${esc(t.emoji)} <b>${esc(t.name)}</b> · ${esc(t.label)}${t.reward>0?` · 🎁 ${fmt(t.reward)} xu`:''}</li>`).join('')}</ul></div>`;
  const score=r=>board==='fish_dex'?`${fmt(r.score)}<small>loài</small>`:`${esc(fmtKg(r.score))}<small>${esc(spOf(r.sp)?.name||'')}</small>`;
  const sub=r=>board==='fish_dex'?(r.rc||[]).map((n,i)=>n?`${rar(i).emoji}${n}`:'').filter(Boolean).reverse().join(' '):'';
  const me=d.me;
  if(me&&me.rank)out+=`<p class="fs-note">Bạn: hạng <b>${fmt(me.rank)}</b>${me.visible===false?' (đang ẩn tên)':''}.</p>`;
  else if(me)out+=`<p class="fs-note">${board==='fish_dex'?'Câu được loài đầu tiên để lên bảng.':'Câu một con cá để lên bảng.'}</p>`;
  if(!d.rows.length)return out+'<p class="fs-empty">Chưa ai lên bảng. Bạn mở hàng nhé! 🎣</p>';
  return out+`<ol class="fs-rows">${d.rows.map(r=>`<li class="fs-row${r.me?' me':''}"><span class="fs-rk">${r.rank<=3?MEDAL[r.rank-1]:r.rank}</span><div class="fs-it"><b data-no-translate>${esc(r.name||'?')}</b>${r.title?`<small>${esc(r.title.emoji)} ${esc(r.title.name)}</small>`:''}${sub(r)?`<small>${esc(sub(r))}</small>`:''}</div><span class="fs-sc">${score(r)}</span></li>`).join('')}</ol>`;
}
