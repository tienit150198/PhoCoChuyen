/** 🎣 Câu cá (game/fishing.py is the authority, every number in game/fishing_content.py). A full-screen lake: one canvas
 * (sky, far shore, the water in zones Gần / Vừa / Xa / Sâu with distance buoys, the dock, the player, the line, the
 * bobber, ripples, splashes, rain) and plain elements over it: the HUD, the power meter, the tension meter, the catch card,
 * and three stalls on the bank: 🎣 Quầy bán cần (rods, bait, baskets), 📖 Bảng bộ sưu tập (Sổ cá, 🐋 Cá lớn nhất,
 * 📖 Bộ sưu tập, the top 3 on the board) and 🐟 Quầy thu mua (the fish bag, the trader who sometimes haggles).
 *
 * A round: hold to charge (the power swings; past POWER_SWEET the line may tangle), release → jr_fish_cast {spot, power}.
 * The server picks how far it went, the zone, whether and when something bites (and what: never told here). The bobber
 * flies, splashes at `splash`, nibbles at `nib`, and at `bite` dips hard with "!" and a buzz: tap within the window →
 * jr_fish_hook (a tap before the bite scares the fish). The fight is played here with what the hook answered (secs,
 * pull, dart, green zone width, `heavy`, a fated `snap_at`): hold to reel, release to ease, keep the needle in the green;
 * too long in the red snaps the line, too slack lets the fish go. jr_fish_land {round, ok}: the server checks the time and
 * says what it was. The catch jumps out of the water and its card opens (🏆 a town record, 📖 a new species, 🏅 a best).
 *
 * Opened by app.js `fishing` (Khu phố), the outings' 🎣 Câu cá, the town map's leisure place and the island's 🎣 chip
 * (spot 'dao' with the trip). Old-Safari safe (scripts/check_old_safari.mjs), no library: one rAF loop while open. */
import {escapeHTML as esc} from '../icons.js';
import {stylesheet} from '../lazy.js';
import {fishSvg,drawFish,fmtKg,RARITY_COLORS} from './fish-art.js';

const PERIOD=1.7;            // s: one swing of the power meter
const K=34;                  // m: the perspective of the lake (a buoy at K metres sits half way to the horizon)
const RED=.9,SLACK=.1,RED_MAX=1.1,SLACK_MAX=2.6,MID=.55;
const MARKS=[10,20,40,65,100,120];
const MEDAL=['🥇','🥈','🥉'];
const F={env:null,dlg:null,cv:null,ctx:null,raf:0,last:0,spot:'ho',trip:'',phase:'idle',pressing:false,c0:0,power:0,
  r:null,f:null,bob:null,fx:[],rings:[],drops:[],waves:null,stars:null,jump:null,line:null,panel:null,tab:{shop:'rod',board:'dex'},
  open:-1,rec:null,recAt:0,boards:{},detail:null,dims:{w:0,h:0,dpr:1},msgT:0,busy:false,timers:[],prevPause:null,onState:null,nibDone:0,twitch:0};

const C=()=>F.env?.api?.content?.journey?.fish||null;
const P=()=>F.env?.api?.state?.journey?.fish||{fresh:true,rod:'tre',rods:['tre'],bait:{},use:'',gio:0,cap:20,bag:[],dex:{},tot:{},ms:[],carry:0,aq:[],tro:{},deal:null};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const clock=()=>performance.now()/1000;
const clamp=(v,a,b)=>v<a?a:v>b?b:v;
const wallet=()=>Math.max(0,Number(F.env?.api?.state?.journey?.wallet)||0);
let SPM=null;
const spOf=id=>{if(!SPM){SPM=new Map();for(const s of C()?.species||[])SPM.set(s.id,s);}return SPM.get(id)||null;};
const rods=()=>C()?.rods||[];
const rodOf=id=>rods().find(r=>r.id===id)||rods()[0]||{id:'tre',name:'Cần tre',emoji:'🎋',range:20,line:6,luck:1,color:'#c8a85a'};
const myRod=()=>rodOf(P().rod);
const spotOf=id=>(C()?.spots||[]).find(s=>s.id===id)||{id,name:id,emoji:'🎣',max:100,water:'#4aa3c7',deep:'#1f5f86',shore:'#7bbf6a'};
const rar=r=>(C()?.rarities||[])[r]||{name:'',emoji:'⚪',color:RARITY_COLORS[r]||'#b8c0c8'};
const kgLine=kg=>kg>=1000?`${String(+(kg/1000).toFixed(1)).replace('.',',')} tấn`:`${fmt(kg)} kg`;
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
  F.onState=()=>{paintHud();if(F.panel)paintPanel();};
  env.api.addEventListener?.('state',F.onState);
  idle('');paintSpots();paintHud();resize();loadRecords();
  if(P().fresh)say('🎣 Giữ nút để lấy lực, thả tay để quăng. Quăng xa ra cá to!',5000);
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
      <div class="fs-meter" hidden><i></i><s></s></div><span class="fs-pow" hidden></span>
      <div class="fs-ten" hidden><div class="fs-ten-bar"><b></b><i></i></div><div class="fs-ten-row"><span>🐟</span><span class="fs-prog"><i></i></span><span>🧍</span></div></div>
      <div class="fs-bank">
        <button type="button" class="fs-stall fs-st-shop" data-fs="shop"><span class="fs-roof"></span><b>🎣 Quầy bán cần</b><small>Cần · mồi · giỏ</small></button>
        <button type="button" class="fs-stall fs-st-board" data-fs="board"><span class="fs-roof"></span><b>📖 Bảng bộ sưu tập</b><ol class="fs-top3"></ol></button>
        <button type="button" class="fs-stall fs-st-market" data-fs="market"><span class="fs-roof"></span><b>🐟 Quầy thu mua</b><small>Bán cá · lái trả giá</small></button>
      </div>
      <div class="fs-card" hidden></div>
    </div>
    <footer class="fs-bar"><button type="button" class="fs-go">🎣 Giữ để quăng</button><small class="fs-tip"></small></footer>
    <section class="fs-panel" hidden></section>
  </div>`;
  document.body.append(d);
  F.cv=d.querySelector('.fs-cv');F.ctx=F.cv.getContext('2d');
  const go=d.querySelector('.fs-go'),stage=d.querySelector('.fs-stage');
  const down=e=>{if(e.button>0)return;e.preventDefault();try{e.currentTarget.setPointerCapture?.(e.pointerId);}catch{/* fine */}press();};
  const up=e=>{e.preventDefault();release();};
  go.addEventListener('pointerdown',down);go.addEventListener('pointerup',up);go.addEventListener('pointercancel',up);
  F.cv.addEventListener('pointerdown',down);F.cv.addEventListener('pointerup',up);F.cv.addEventListener('pointercancel',up);
  go.addEventListener('contextmenu',e=>e.preventDefault());stage.addEventListener('contextmenu',e=>e.preventDefault());
  d.addEventListener('keydown',e=>{if((e.key===' '||e.key==='Enter')&&!F.panel&&!e.repeat&&(e.target===go||e.target===d)){e.preventDefault();press();}});
  d.addEventListener('keyup',e=>{if((e.key===' '||e.key==='Enter')&&!F.panel&&(e.target===go||e.target===d)){e.preventDefault();release();}});
  d.addEventListener('click',e=>{const el=e.target.closest('[data-fs]');if(!el||!d.contains(el))return;e.preventDefault();act(el.dataset.fs,el.dataset).catch(err=>say(err?.message||'Có lỗi nhỏ, thử lại nhé.'));});
  d.addEventListener('cancel',e=>{e.preventDefault();if(F.panel){closePanel();return;}close();});
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
  F.prevPause=null;F.r=null;F.f=null;F.phase='idle';F.panel=null;
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

/* ---------------------------------------------------------------- input and rounds */
function press(){
  if(F.panel)return;
  F.pressing=true;F.dlg?.querySelector('.fs-go')?.classList.add('down');
  if(F.phase==='idle'||F.phase==='card'){hideCard();F.phase='charge';F.c0=clock();F.power=0;meters();paintMeter();paintGo();return;}
  if(F.phase==='wait'||F.phase==='bite'){hook();return;}
  if(F.phase==='fight'&&F.f)F.f.hold=true;
}
function release(){
  if(!F.pressing)return;F.pressing=false;F.dlg?.querySelector('.fs-go')?.classList.remove('down');
  if(F.phase==='charge'){cast(F.power);return;}
  if(F.phase==='fight'&&F.f)F.f.hold=false;
}
function idle(tip){
  F.phase='idle';F.r=null;F.f=null;F.bob=null;F.line=null;F.jump=null;
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
  F.bob={d:c.dist,lat,x:0,y:0,dip:0};
  F.castL=got;
  if(c.tangle){
    F.phase='tangle';F.bob.splashL=got+.9;F.bob.tangle=true;vibrate(40);
    say(res.message||'🪢 Dây rối mất rồi!');paintGo('Quăng nhẹ tay hơn chút nhé (vạch đỏ là rối dây).');
    later(()=>{if(F.phase==='tangle')idle();},1900);return;
  }
  F.r={id:c.id,dist:c.dist,zone:c.zone,splashL:Math.max(got+.6,L(c.splash)),nib:(c.nib||[]).map(L),biteL:c.bite!=null?L(c.bite):0,
    goneL:c.gone!=null?L(c.gone):0,window:c.window||C()?.hook_window||1.4,t0};
  F.nibDone=0;F.twitch=0;
  if(res.bait_used&&P().bait?.[res.bait_used]==null)say('Hết mồi rồi, mua thêm ở 🎣 Quầy bán cần nhé.');
  F.phase='fly';paintGo();
}
async function hook(){
  const r=F.r;if(!r)return;
  const early=F.phase==='wait';
  F.phase='hooking';paintGo();
  if(F.bob)F.bob.dip=early?.25:1;
  const res=await send('jr_fish_hook',{round:r.id});
  if(F.r!==r)return;
  if(!res){idle();return;}
  const h=res.hook||{};
  if(h.lost){
    fleeFx();say(res.message||(h.lost==='early'?'😱 Giật sớm quá, cá chạy mất!':'💨 Cá nhả mồi mất rồi!'));
    F.phase='lost';paintGo();later(()=>{if(F.phase==='lost')idle(h.lost==='early'?'Đợi phao chìm hẳn rồi mới giật nhé.':'');},1100);return;
  }
  startFight(h);
}
function startFight(h){
  const t=clock();
  F.f={secs:Math.max(1.5,Number(h.secs)||3),pull:clamp(Number(h.pull)||.2,0,1),dart:clamp(Number(h.dart)||.1,0,1),green:clamp(Number(h.green)||.3,.12,.6),
    heavy:!!h.heavy,snapL:h.snap_at!=null?t+Number(h.snap_at):0,t0:t,tau:.42,prog:0,red:0,slack:0,hold:F.pressing,dl:0,dv:0,seed:Math.random()*6,sway:0};
  F.phase='fight';vibrate([30,30,60]);
  if(F.f.heavy)say('⚠️ Cá nặng quá sức dây! Coi chừng đứt…',2600);
  meters();paintGo();
}
async function endFight(kind){
  const r=F.r;if(!r||!F.f)return;
  F.phase='landing';const f=F.f;meters();paintGo();
  if(kind==='snap'){snapFx();say(f.heavy&&f.snapL?'💥 Phựt! Cá quá nặng, đứt dây rồi.':'💥 Phựt! Căng quá đứt dây rồi.');}
  else if(kind==='slack'){fleeFx();say('🐟 Dây chùng quá, cá giãy thoát mất!');}
  let res=null;
  for(let i=0;i<4;i++){
    try{res=await F.env.api.command('jr_fish_land',{round:r.id,ok:kind==='ok'});break;}
    catch(e){
      if(e?.data?.code==='too_early'&&i<3){await new Promise(done=>later(done,700));continue;}
      if(!e?.quiet)say(e?.message||'Chưa ghi được lượt câu.');break;
    }
  }
  if(F.r!==r)return;
  const land=res?.land;
  if(!land){idle();return;}
  if(land.res==='fish'||land.res==='junk'){jump(land,res);return;}
  if(kind==='ok'||land.res==='snap'){if(land.res==='snap')snapFx();say(res.message||'Mất cá rồi!',3200);}
  F.phase='lost';paintGo();later(()=>{if(F.phase==='lost')idle();},1200);
}
/** The catch leaps out of the water to the dock, then its card. */
function jump(land,res){
  const g=geo(),fromD=Math.max(1,(F.r?.dist||10)*.12),sp=land.catch?spOf(land.catch.s):null;
  F.jump={t0:clock(),dur:1.05,sp,junk:land.res==='junk'?(C()?.junk||[]).find(j=>j.id===land.junk):null,
    x0:g.px+(F.bob?.lat||0)*g.half(g.yOf(fromD))*.4,y0:g.yOf(fromD),x1:g.px+6,y1:g.py-70,len:sp?clamp(34+sp.r*8,34,90):30};
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
    F.power=.5-.5*Math.cos(2*Math.PI*(t-F.c0)/PERIOD);paintMeter();
  }else if(F.phase==='fly'&&F.r&&t>=F.r.splashL){
    const g=geo(),y=g.yOf(F.r.dist),x=g.px+F.bob.lat*g.half(y);
    splashAt(x,y,12,'#dff6ff');ring(x,y,1.2);F.phase='wait';paintGo();
  }else if(F.phase==='wait'&&F.r){
    const r=F.r;
    while(F.nibDone<r.nib.length&&t>=r.nib[F.nibDone]){F.nibDone++;F.bob.dip=.35;const p=bobXY();ring(p[0],p[1],.7);vibrate(8);}
    if(Math.random()<dt*.35){F.bob.dip=Math.max(F.bob.dip,.12);}   // a fake twitch: the wind, a leaf
    if(r.biteL&&t>=r.biteL){F.phase='bite';F.bob.dip=1;const p=bobXY();ring(p[0],p[1],1.6);splashAt(p[0],p[1],8,'#ffffff');vibrate([60,40,140]);F.env?.sound?.alert?.();paintGo();}
    else if(r.goneL&&t>=r.goneL){
      F.phase='lost';const p=bobXY();ring(p[0],p[1],.8);say('🐟 Cá rỉa mất mồi rồi! Quăng lại nhé.');
      send('jr_fish_hook',{round:r.id}).catch(()=>{});   // closes the round on the server (nothing to win)
      paintGo();later(()=>{if(F.phase==='lost')idle();},1200);
    }
  }else if(F.phase==='bite'&&F.r&&t>F.r.biteL+F.r.window+1){
    const r=F.r;F.phase='lost';fleeFx();say('💨 Chậm tay rồi, cá nhả mồi mất!');paintGo();
    send('jr_fish_hook',{round:r.id}).then(res=>{if(res?.hook&&!res.hook.lost&&F.r===r)startFight(res.hook);else later(()=>{if(F.phase==='lost')idle();},700);}).catch(()=>{});
  }else if(F.phase==='fight'&&F.f){fight(t,dt);}
  if(F.bob)F.bob.dip=Math.max(0,F.bob.dip-dt*(F.phase==='bite'?.15:1.6));
}
function fight(t,dt){
  const f=F.f,g0=MID-f.green/2,g1=MID+f.green/2;
  if(f.dl>0){f.dl-=dt;f.tau+=f.dv*dt;}
  else if(Math.random()<dt*(.2+f.dart*1.1)){
    f.dl=.25+Math.random()*.25;f.dv=(.55+f.pull*1.05)*(Math.random()<.8?1:-.6);f.sway=(Math.random()<.5?-1:1);
    const p=fishXY();splashAt(p[0],p[1],6,'#e8f8ff');vibrate(12);
  }
  f.tau+=(f.hold?(.42+.2*f.pull):-(.62-.14*f.pull))*dt+f.pull*.12*Math.sin(t*2.4+f.seed)*dt;
  f.tau=clamp(f.tau,0,1);
  if(f.hold){f.prog+=dt/(f.secs*(f.tau>=g0&&f.tau<=g1?.85:f.tau>g1?1.7:3.2));}
  else f.prog-=dt*(.025+.05*f.pull);
  f.prog=clamp(f.prog,0,1);
  f.red=f.tau>RED?f.red+dt:Math.max(0,f.red-dt*.7);
  f.slack=f.tau<SLACK&&!f.hold?f.slack+dt:Math.max(0,f.slack-dt*1.5);
  paintTension();
  if(f.snapL&&t>=f.snapL){endFight('snap');return;}
  if(f.red>RED_MAX){endFight('snap');return;}
  if(f.slack>SLACK_MAX){endFight('slack');return;}
  if(f.prog>=1)endFight('ok');
}

/* ---------------------------------------------------------------- geometry */
function resize(){
  if(!F.cv)return;
  const w=F.cv.clientWidth,h=F.cv.clientHeight;if(!w||!h)return;
  const dpr=Math.min(2,window.devicePixelRatio||1);
  F.dims={w,h,dpr};F.cv.width=Math.round(w*dpr);F.cv.height=Math.round(h*dpr);F.ctx.setTransform(dpr,0,0,dpr,0,0);
  F.waves=null;F.stars=null;
  const bank=F.dlg?.querySelector('.fs-bank')?.offsetHeight||112;F.bankH=bank;
  const meter=F.dlg?.querySelector('.fs-meter'),ten=F.dlg?.querySelector('.fs-ten');
  if(meter){meter.style.top=`${Math.round(h*.2)}px`;meter.style.height=`${Math.round(h-bank-h*.2-40)}px`;}
}
function geo(){
  const {w,h}=F.dims,bank=F.bankH||112,shore=h-bank,hor=Math.max(46,h*.14),M=spotOf(F.spot).max||100;
  const top=hor+8,bottom=shore-28,frac=d=>(d/(d+K))/(M/(M+K));
  const yOf=d=>bottom-(bottom-top)*clamp(frac(Math.max(0,d)),0,1);
  const half=y=>{const u=clamp((y-hor)/(shore-hor),0,1);return w*(.17+.36*u);};
  return {w,h,shore,hor,M,yOf,half,px:w/2,py:shore-20,tipX:w/2+22,tipY:shore-74};
}
function bobXY(){const g=geo(),b=F.bob;if(!b)return [g.px,g.py];const y=g.yOf(b.d);return [g.px+b.lat*g.half(y),y];}
function fishXY(){
  const g=geo(),f=F.f,b=F.bob;if(!b||!f)return bobXY();
  const d=b.d*(1-f.prog)+1,y=g.yOf(d),t=clock();
  return [g.px+(b.lat*(1-f.prog*.8))*g.half(y)+Math.sin(t*1.7+f.seed)*g.half(y)*.12*(.4+f.pull)+f.sway*f.dl*30,y];
}

/* ---------------------------------------------------------------- effects */
function ring(x,y,s=1){F.rings.push({x,y,t0:clock(),s});if(F.rings.length>24)F.rings.shift();}
function splashAt(x,y,n,c){for(let i=0;i<n;i++){const a=-Math.PI*(.15+.7*Math.random());F.fx.push({x,y,vx:Math.cos(a)*(40+Math.random()*70)*(Math.random()<.5?-1:1),vy:Math.sin(a)*(90+Math.random()*120),t0:clock(),life:.5+Math.random()*.4,c});}if(F.fx.length>160)F.fx.splice(0,F.fx.length-160);}
function fleeFx(){const p=F.f?fishXY():bobXY();ring(p[0],p[1],1);ring(p[0]+16,p[1]-4,.6);splashAt(p[0],p[1],6,'#e8f8ff');}
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
  dock(ctx,g,night);
  lineAndBobber(ctx,g,t);
  player(ctx,g,t);
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
function zones(ctx,g,night){
  const zs=C()?.zones||[{to:20},{to:40},{to:65},{to:999}],rod=myRod();
  let from=0;ctx.font='700 11px system-ui,sans-serif';ctx.textBaseline='middle';
  zs.forEach((z,i)=>{
    const to=Math.min(z.to,g.M),y0=g.yOf(from),y1=g.yOf(to);if(to<=from)return;
    ctx.fillStyle=i%2?'rgba(255,255,255,.035)':'rgba(0,20,40,.06)';ctx.fillRect(0,y1,g.w,y0-y1);
    ctx.fillStyle=night?'rgba(220,235,255,.55)':'rgba(255,255,255,.75)';ctx.textAlign='left';ctx.fillText(z.name||ZN[i],8,(y0+y1)/2);
    from=to;
  });
  ctx.textAlign='center';
  for(const m of MARKS){
    if(m>g.M)continue;const y=g.yOf(m),hw=g.half(y),s=.55+.45*(y-g.hor)/(g.shore-g.hor);
    for(const x of [g.px-hw*.92,g.px+hw*.92]){ctx.fillStyle='#ff6a3d';ctx.beginPath();ctx.arc(x,y-3*s,4.5*s,0,7);ctx.fill();ctx.fillStyle='#fff';ctx.fillRect(x-4.5*s,y-3.5*s,9*s,1.6*s);}
    ctx.fillStyle='rgba(255,255,255,.85)';ctx.font=`700 ${Math.round(9+3*s)}px system-ui,sans-serif`;ctx.fillText(`${m}m`,g.px+hw*.92,y-12*s);
  }
  const ry=g.yOf(Math.min(rod.range,g.M));   // how far this rod reaches
  ctx.setLineDash([6,5]);ctx.strokeStyle='rgba(255,224,90,.75)';ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(g.px-g.half(ry)*.8,ry);ctx.lineTo(g.px+g.half(ry)*.8,ry);ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle='rgba(255,224,90,.95)';ctx.font='800 10px system-ui,sans-serif';ctx.fillText(`🎣 tầm cần ${rod.range}m`,g.px,ry-8);
}
function waves(ctx,g,t,night){
  if(!F.waves){F.waves=[];for(let i=0;i<46;i++)F.waves.push([Math.random(),Math.random()*g.M,Math.random()*6]);}
  ctx.strokeStyle=night?'rgba(180,210,255,.18)':'rgba(255,255,255,.35)';ctx.lineWidth=1.2;ctx.beginPath();
  for(const [fx,d,ph] of F.waves){const y=g.yOf(d),hw=g.half(y),x=g.px+(fx*2-1)*hw+Math.sin(t*.6+ph)*6,len=4+10*(y-g.hor)/(g.shore-g.hor);
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
  const L=62,bx=g.px+10,by=g.py-30;
  return {bx,by,x:bx+Math.sin(a)*L,y:by-Math.cos(a)*L,a};
}
function lineAndBobber(ctx,g,t){
  const tip=rodTip(g,t);
  ctx.strokeStyle='#5a3a1a';ctx.lineWidth=3;ctx.lineCap='round';ctx.beginPath();ctx.moveTo(tip.bx,tip.by);
  const bend=F.phase==='fight'&&F.f?F.f.tau*16:0;ctx.quadraticCurveTo((tip.bx+tip.x)/2+bend*.3,(tip.by+tip.y)/2-bend*.2,tip.x+bend*.5,tip.y+bend);ctx.stroke();
  const rc=myRod().color||'#c8a85a';ctx.strokeStyle=rc;ctx.lineWidth=1.6;ctx.stroke();
  const tx=tip.x+bend*.5,ty=tip.y+bend;
  if(!F.bob||F.phase==='jump')return;
  let bx,by;
  if((F.phase==='fly'||F.phase==='tangle')&&F.bob){
    const target=F.bob.tangle?[g.px+30,g.yOf(Math.min(F.bob.d,6))]:bobXY(),end=F.bob.splashL||(F.r?.splashL)||F.castL+1,u=clamp((t-F.castL)/Math.max(.3,end-F.castL),0,1);
    bx=tx+(target[0]-tx)*u;by=ty+(target[1]-ty)*u-Math.sin(Math.PI*u)*Math.min(160,40+F.bob.d*1.6);
    if(F.bob.tangle&&u>=1){ctx.strokeStyle='#eee';ctx.lineWidth=1;ctx.beginPath();for(let k=0;k<12;k++){const a=k*1.7+t*3;ctx.lineTo(bx+Math.cos(a)*8,by+Math.sin(a)*5);}ctx.stroke();}
  }else if(F.phase==='fight'||F.phase==='landing'){
    [bx,by]=F.f?fishXY():bobXY();
  }else{
    [bx,by]=bobXY();
    by+=Math.sin(t*2.2)*1.4+F.bob.dip*(F.phase==='bite'||F.phase==='hooking'?9:6);
  }
  const snapped=F.line?.snap&&t-F.line.snap<1.2;
  ctx.strokeStyle='rgba(255,255,255,.85)';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(tx,ty);
  if(snapped){ctx.quadraticCurveTo(tx+10,ty+30,tx+4,ty+60);ctx.stroke();return;}
  const sag=F.phase==='fight'&&F.f?(1-F.f.tau)*30:22;
  ctx.quadraticCurveTo((tx+bx)/2,Math.max(ty,by)-(Math.abs(by-ty)*.25)+sag,bx,by);ctx.stroke();
  if(F.phase==='fight'||F.phase==='landing')return;
  // the bobber
  ctx.fillStyle='#ffffff';ctx.beginPath();ctx.arc(bx,by-3,4,Math.PI,0);ctx.fill();
  ctx.fillStyle='#e8392b';ctx.beginPath();ctx.arc(bx,by-3,4,0,Math.PI);ctx.fill();
  ctx.fillStyle='#222';ctx.fillRect(bx-.6,by-11,1.2,5);
  if(F.phase==='bite'||F.phase==='hooking'){
    const s=1+.15*Math.sin(t*18);ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(bx,by-28,13*s,0,7);ctx.fill();
    ctx.fillStyle='#e8392b';ctx.font=`900 ${Math.round(20*s)}px system-ui,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('!',bx,by-27);
  }
}
function player(ctx,g,t){
  const x=g.px,y=g.py,J=F.env?.api?.state?.journey||{},male=J.gender==='male';
  const lean=F.phase==='charge'?-F.power*4:F.phase==='fight'&&F.f?-F.f.tau*5:0;
  ctx.save();ctx.translate(x,y);ctx.rotate(lean*Math.PI/180);
  ctx.fillStyle='rgba(0,0,0,.25)';ctx.beginPath();ctx.ellipse(0,4,14,4,0,0,7);ctx.fill();
  ctx.fillStyle='#2d3e50';ctx.fillRect(-7,-14,5,16);ctx.fillRect(2,-14,5,16);           // legs
  ctx.fillStyle=male?'#2f7fd6':'#e0607e';ctx.beginPath();ctx.moveTo(-10,-14);ctx.lineTo(10,-14);ctx.lineTo(8,-36);ctx.lineTo(-8,-36);ctx.fill();   // shirt
  ctx.fillStyle='#f3c9a0';ctx.beginPath();ctx.arc(0,-44,8,0,7);ctx.fill();               // head
  ctx.fillStyle='#e7c14a';ctx.beginPath();ctx.ellipse(0,-50,13,3.5,0,0,7);ctx.fill();ctx.beginPath();ctx.arc(0,-51,7,Math.PI,0);ctx.fill();   // nón
  ctx.fillStyle='#f3c9a0';ctx.fillRect(6,-33,8,4);                                       // arm to the rod
  // the carried fish on the shoulder
  const w=P().carry&&(P().bag||[]).find(f=>f.i===P().carry),sp=w&&spOf(w.s);
  if(sp)drawFish(ctx,sp,-10,-36,26,{angle:-.5,flip:true,glow:true});
  ctx.restore();
}
function leap(ctx,t){
  const j=F.jump,u=clamp((t-j.t0)/j.dur,0,1);
  const x=j.x0+(j.x1-j.x0)*u,y=j.y0+(j.y1-j.y0)*u-Math.sin(Math.PI*u)*90;
  if(j.sp)drawFish(ctx,j.sp,x,y,j.len,{angle:Math.sin(t*14)*.3-.4+u*.6,flip:j.x1<j.x0,wiggle:(t*3)%1});
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
  const bag=F.dlg.querySelector('.fs-bagb'),cnt=(p.bag||[]).length;bag.textContent=`🧺 ${cnt}/${p.cap||20}`;bag.classList.toggle('full',cnt>=(p.cap||20));
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
  const ph=F.phase;b.className='fs-go'+(ph==='bite'?' hook':ph==='fight'?' reel':['wait','casting','fly','hooking','landing','jump','lost','tangle'].includes(ph)?' wait':'');
  b.textContent={idle:'🎣 Giữ để quăng',card:'🎣 Giữ để quăng tiếp',charge:'Thả tay để quăng!',casting:'Vút…',fly:'Vút…',wait:'Chờ phao chìm… (chạm = Giật)',bite:'❗ GIẬT!',hooking:'Giật!',
    fight:'💪 Giữ để kéo · thả để nhả',landing:'Kéo lên…',jump:'Lên rồi!',lost:'…',tangle:'Gỡ dây…'}[ph]||'🎣';
  if(s)s.textContent=tip!=null&&tip!==''?tip:{idle:'Lực mạnh ra xa, cá to hơn. Vạch đỏ dễ rối dây.',charge:'Thả ở vạch bạn muốn: xa hơn = cá lớn hơn.',wait:'Phao rung nhẹ là cá rỉa. Phao chìm hẳn + “!” mới giật.',
    bite:'Nhanh tay lên!',fight:'Kim trong vùng xanh. Đỏ lâu: đứt dây. Chùng lâu: sổng cá.'}[ph]||'';
}
function meters(){
  const d=F.dlg;if(!d)return;
  d.querySelector('.fs-meter').hidden=F.phase!=='charge';d.querySelector('.fs-pow').hidden=F.phase!=='charge';
  d.querySelector('.fs-ten').hidden=!(F.phase==='fight');
  if(F.phase==='charge'){
    const m=d.querySelector('.fs-meter'),sweet=C()?.power_sweet||.95,rod=myRod();
    m.querySelector('s').style.height=`${(1-sweet)*100}%`;
    m.querySelectorAll('u,em').forEach(x=>x.remove());
    let from=0;for(const z of C()?.zones||[]){const to=Math.min(z.to,rod.range);if(to>from&&to<rod.range){const f=to/rod.range;m.insertAdjacentHTML('beforeend',`<u style="bottom:${(f/1.0)*100}%"></u>`);}from=to;}
  }
  if(F.phase==='fight'&&F.f){const bar=d.querySelector('.fs-ten-bar b');bar.style.left=`${(MID-F.f.green/2)*100}%`;bar.style.width=`${F.f.green*100}%`;}
}
function paintMeter(){
  const d=F.dlg;if(!d)return;
  const m=d.querySelector('.fs-meter'),p=d.querySelector('.fs-pow'),rod=myRod(),sweet=C()?.power_sweet||.95;
  m.querySelector('i').style.height=`${F.power*100}%`;
  const est=Math.round(F.power*rod.range),zs=C()?.zones||[],z=zs.findIndex(x=>est<x.to);
  p.textContent=`${F.power>sweet?'⚠️ ':''}~${est}m · ${(zs[z<0?zs.length-1:z]||{}).name||''}`;
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
  F.jump=null;F.r=null;F.bob=null;F.phase='card';paintGo();
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
    <p class="fs-kg">${esc(fmtKg(c.g))}</p><p class="fs-price">Giá lái: ~${fmt(c.price)} xu · ${esc(spotOf(c.spot).emoji)} ${esc(spotOf(c.spot).name)}</p>
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
      if(ds.id&&ds.id!==F.spot){F.spot=ds.id;F.waves=null;hideCard();idle();paintSpots();say(`${spotOf(F.spot).emoji} ${spotOf(F.spot).name}: ${spotOf(F.spot).hint||''}`);}return;
    case'again':hideCard();idle();return;
    case'shop':case'market':case'board':case'dex':
      if(!['idle','card','lost','tangle'].includes(F.phase)){say('Đang câu dở, xong con này đã nhé!');return;}
      openPanel(a);return;
    case'panelX':closePanel();return;
    case'tab':F.tab[ds.p]=ds.t;if(ds.p==='board'&&ds.t!=='dex')loadBoard(ds.t);paintPanel();return;
    case'buy':{
      const kind=ds.kind,item=ds.item,n=Number(ds.n)||1;
      if(kind==='rod'||kind==='gio'){
        const x=kind==='rod'?rodOf(item):(C()?.baskets||[]).find(b=>b.id===item);
        if(x?.price>0&&F.env.confirmAction&&!(await F.env.confirmAction(`Mua ${x.name}?`,`Giá ${fmt(x.price)} xu. Ví đang có ${fmt(wallet())} xu.`,'Mua')))return;
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
    case'mount':{const r=await send('jr_fish_mount',{id:Number(ds.id)});if(r){say(r.message||'',4200);F.open=-1;paintPanel();}return;}
    case'aqua':{const r=await send('jr_fish_aqua',ds.out!=null?{out:Number(ds.out)}:{id:Number(ds.id)});if(r){say(r.message||'');F.open=-1;paintPanel();}return;}
    case'row':F.open=F.open===Number(ds.id)?-1:Number(ds.id);paintPanel();return;
    case'sp':F.detail=ds.id;paintPanel();return;
    case'spBack':F.detail=null;paintPanel();return;
  }
}
const sellable=()=>(P().bag||[]).filter(f=>!f.k&&!(f.o<0));   // not ⭐ kept, not refused today

/* ---------------------------------------------------------------- the sheets */
function openPanel(kind){
  F.panel=kind==='dex'?'board':kind;if(kind==='dex')F.tab.board='dex';F.detail=null;F.open=-1;
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
  let out=tabs('shop',[['rod','🎣 Cần câu'],['bait','🪱 Mồi'],['gio','🧺 Giỏ']])+`<p class="fs-note">👛 Ví: <b>${fmt(wallet())} xu</b></p>`;
  if(t==='rod'){
    out+=`<p class="fs-note">Cần xịn quăng xa hơn (ra vùng Xa, Sâu có cá to), dây chịu cá nặng hơn, may mắn gặp cá hiếm hơn.</p><ul class="fs-list">${c.rods.map(r=>{
      const own=(p.rods||[]).includes(r.id),cur=p.rod===r.id;
      return `<li class="fs-item${cur?' cur':''}"><span class="fs-ico" style="--c:${esc(r.color||'#eee')}">${esc(r.emoji)}</span><div class="fs-it"><b>${esc(r.name)}</b><small>📏 ${fmt(r.range)} m · 🧵 ${esc(kgLine(r.line))} · 🍀 ×${String(r.luck).replace('.',',')}</small>${r.ancient?'<small class="fs-anc">🔴 Câu được cá Cổ đại</small>':''}</div>
        ${cur?'<span class="fs-tag">Đang cầm</span>':own?fbtn('Cầm','equip',{rod:r.id}):fbtn(r.price?`${fmt(r.price)} xu`:'Miễn phí','buy',{kind:'rod',item:r.id},'primary')}</li>`;}).join('')}</ul>`;
  }else if(t==='bait'){
    out+=`<p class="fs-note">Mồi tốt tăng cơ hội gặp cá hiếm. Mỗi lần quăng tốn 1 mồi đang dùng.</p><ul class="fs-list"><li class="fs-item${!p.use?' cur':''}"><span class="fs-ico">🎣</span><div class="fs-it"><b>Không mồi đặc biệt</b><small>Mồi cơm thường, miễn phí</small></div>${!p.use?'<span class="fs-tag">Đang dùng</span>':fbtn('Dùng','equip',{bait:''})}</li>
      ${c.baits.map(b=>{const have=p.bait?.[b.id]||0,cur=p.use===b.id;
        return `<li class="fs-item${cur?' cur':''}"><span class="fs-ico">${esc(b.emoji)}</span><div class="fs-it"><b>${esc(b.name)}${have?` · còn ${fmt(have)}`:''}</b><small>${esc(b.hint||'')}</small><small>${fmt(b.price)} xu / ${fmt(b.n)} mồi</small></div>
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
    return `<li class="fs-fish" style="--rc:${esc(R.color||'#ccc')}">${fishSvg(sp,{w:64,h:32})}<div class="fs-it"><b>${esc(sp.name)}${f.k?' ⭐':''}${p.carry===f.i?' 💪':''}</b><small>${esc(fmtKg(f.g))} · ${esc(R.name)} · ~${fmt(price)} xu</small>${off}</div>
      <span style="display:flex;gap:4px">${f.o<0?'':fbtn('Bán','sell',{id:f.i},'primary')}${fbtn(open?'▴':'⋯','row',{id:f.i})}</span>
      ${open?`<div class="fs-fish-acts">${fbtn(f.k?'☆ Bỏ giữ':'⭐ Giữ','keep',{id:f.i})}${sp.r>=(C()?.carry_min||3)?fbtn(p.carry===f.i?'🧺 Cất':'💪 Vác','carry',{id:p.carry===f.i?0:f.i}):''}${fbtn('🖼️ Treo tranh','mount',{id:f.i})}${fbtn('🐠 Thả bể','aqua',{id:f.i})}${fbtn('🌊 Thả về hồ','release',{id:f.i})}</div>`:''}</li>`;}).join('')}</ul>`;
  const aq=p.aq||[];
  out+=`<h4 style="margin:12px 0 4px">🐠 Bể cá ở nhà (${aq.length}/${C()?.aquarium||8})</h4>${aq.length?`<ul class="fs-list">${aq.map(([s,g],k)=>{const sp=spOf(s)||{name:s,r:0};return `<li class="fs-fish" style="--rc:${esc(rar(sp.r).color||'#ccc')}">${fishSvg(sp,{w:64,h:32})}<div class="fs-it"><b>${esc(sp.name)}</b><small>${esc(fmtKg(g))}</small></div>${fbtn('Vớt về giỏ','aqua',{out:k})}</li>`;}).join('')}</ul>`:'<p class="fs-note">Thả cá đẹp vào bể (có bể cá trong nhà thì cá bơi ở đó).</p>'}`;
  out+=`<p class="fs-note">🖼️ Tranh cá: ${Object.keys(p.tro||{}).length}/${C()?.trophies||12} (treo ở Trang trí nhà).</p>`;
  return out;
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
        return `<button type="button" class="fs-cell got" style="--rc:${esc(R.color)}" data-fs="sp" data-id="${esc(s.id)}">${fishSvg(s,{w:80,h:40})}<b>${esc(s.name)}</b><small>${row[1]?`🏅 ${esc(fmtKg(row[1]))} · `:''}×${fmt(row[0])}</small>${rc?`<small class="fs-rec">🏆 ${esc(fmtKg(rc.g))}${rc.me?' (bạn)':''}</small>`:''}</button>`;
      }).join('')}</div>`;
  });
  return out;
}
function detailHTML(id){
  const s=spOf(id);if(!s)return '';
  const row=P().dex?.[id],ok=(row?.[0]||0)>0,R=rar(s.r),rc=F.rec?.records?.[id];
  return `<div class="fs-detail">${fbtn('← Sổ cá','spBack')}<div>${fishSvg(s,{w:240,h:120,silhouette:!ok,title:ok?s.name:'?'})}</div><h3 style="margin:2px 0">${ok?esc(s.name):'???'}</h3><span class="fs-rar" style="display:inline-block;padding:2px 10px;border-radius:99px;background:${esc(R.color)};color:#fff;font-weight:800;font-size:12px">${esc(R.emoji)} ${esc(R.name)}</span>
    <dl><dt>Ở đâu</dt><dd>${s.spots.map(x=>`${esc(spotOf(x).emoji)} ${esc(spotOf(x).name)}`).join(', ')}</dd>${s.cond?`<dt>Khi nào</dt><dd>${esc(s.cond)}</dd>`:''}<dt>Gợi ý</dt><dd>${esc(s.hint||'')}</dd>
    ${ok?`<dt>Nặng</dt><dd>${esc(fmtKg(s.w[0]*1000))} – ${esc(fmtKg(s.w[1]*1000))}</dd><dt>Bạn câu</dt><dd>${fmt(row[0])} con${row[1]?` · lớn nhất ${esc(fmtKg(row[1]))}`:''}</dd>`:''}
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
