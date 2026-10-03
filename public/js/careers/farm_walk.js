/** Nông trại "🚶 Tự đi": the farm as a small world to walk in, from the eyes (the tool in your hands) or from
 * behind your own character, and the ride with the produce to the buyer.
 *
 * Canvas 2D, no library: a perspective camera over a flat world (ground shapes, boxes, sprites), drawn back to
 * front. Everything shown comes from the room data the workbench already has (the beds, the coop, the cold room,
 * the order); nothing here decides or sends anything on its own. The buttons under the stage are the workbench's
 * own buttons (public/js/careers/farm.js); arriving at the buyer calls hooks.deliver, which sends the same
 * `fa_deliver` as the "🚚 GIAO HÀNG" button. farm.js puts the stage into #fvHost on every tick (a re-render may
 * replace the host): the stage, its canvas and where you stand live here for the whole page session.
 *
 * World units are metres: x to the east, z to the north, y up. yaw 0 looks north. */
import {figure,paintLegs,paintAcc} from '../v4/look.js';
import {R,E,L,P} from '../scenes/kit.js';
import {t as tr} from '../v4/i18n.js';

const NEAR=0.08,REACH=1.05,RAD=0.32,WALK=3.3,TURN=2.3,EYE=1.55,TAU=Math.PI*2;
const BEDS={P1:[-5,8],P2:[0,8],P3:[5,8],P4:[-5,12.5],P5:[0,12.5],P6:[5,12.5]},BX=1.6,BZ=0.8,BH=0.32;
const FIELD={x0:-13.3,x1:13.3,z0:-5.3,z1:25.3};
// Where you can stand to work (footprints [x0, z0, x1, z1]; you work it from within REACH of its edge).
const SPOT={...Object.fromEntries(Object.entries(BEDS).map(([k,[x,z]])=>[k,[x-BX,z-BZ,x+BX,z+BZ]])),
  tank:[8.9,5.8,10.1,9.6],coop:[-11,15.6,-3.6,19],shed:[7,16,11.5,19.5],pack:[-12.6,-1.2,-6.6,1.6],
  bike:[-6.1,-2.45,-3.9,-1.55],truck:[6.6,-4.6,11.2,-2.5],board:[2.5,-4.5,3.1,-3.9]};
const SOLID=[...Object.keys(BEDS).map(k=>SPOT[k]),[8.9,8.4,10.1,9.6],[8.9,5.8,10.1,7],[-11,16,-7,18.6],[-7,15.6,-3.6,19],SPOT.shed,
  [-12.6,-1.2,-9.6,1.6],[-8.6,-0.5,-6.6,0.5],SPOT.bike,[7,-4.3,11.2,-2.6],[2.65,-4.35,2.95,-4.05],[11.4,1.3,12.8,2.7]];
const HOME={x:0,z:-3.4,yaw:0};
const SUN=norm3([-0.45,0.8,-0.4]);

/* ------------------------------------------------------------------ state */
const W={el:null,cv:null,c:null,ro:null,w:0,h:0,dpr:1,q:1,x:null,hooks:null,raf:0,timer:0,last:0,t:0,
  me:{...HOME,pitch:0.1,bob:0,moving:0,tool:null},cam:'fp',joy:null,look:null,keys:new Set(),
  near:null,auto:null,ride:null,fx:[],hens:[],seen:null,calm:0,hint:0,perf:{n:0,sum:0,ms:0,bad:0,gaps:0,shown:0},dirty:false,
  sky:null,fogRGB:[230,240,236],moved:0,broken:false};

const clamp=(v,a,b)=>v<a?a:v>b?b:v;
function norm3(v){const l=Math.hypot(...v)||1;return v.map(a=>a/l);}
function wrap(a){a%=TAU;return a>Math.PI?a-TAU:a<-Math.PI?a+TAU:a;}
const coarse=()=>!!matchMedia?.('(pointer: coarse)').matches;
const reduced=()=>matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const farm=()=>W.x?.room?.data||{plots:[],cold:[],coop:{}};
const task=()=>{const x=W.x,id=x?.ui?.fvTask;return id?(x.room.tasks||[]).find(t=>t.id===id)||null:null;};
const cropOf=id=>(W.x?.cc?.crops||[]).find(c=>c.id===id)||(id==='egg'?W.x?.cc?.egg:null)||{id,name:id,emoji:'•'};

/* ------------------------------------------------------------------ public API (farm.js) */
/** Put the stage into `host` (again, after a re-render replaced it) and keep drawing while it shows. */
export function mount(host,x,hooks){
  W.x=x;W.hooks=hooks;
  if(W.broken){hooks.broken?.(x);return;}
  let fresh=false;
  if(!W.el){if(!build()){W.broken=true;hooks.broken?.(x);return;}fresh=true;if(hooks.hint?.())W.hint=W.t+0.001;}
  if(W.el.parentNode!==host){host.insertBefore(W.el,host.firstChild);fresh=true;}
  const cam=x.ui.fvCam==='tp'?'tp':'fp';if(cam!==W.cam){W.cam=cam;fresh=true;}
  observe();changes();
  // Called five times a second: only a stage that stopped (hidden, put back) or changed starts drawing again.
  if(fresh||(!W.raf&&!W.timer))wake();
}
export function camera(cam){W.cam=cam==='tp'?'tp':'fp';wake();}
/** Walk there by yourself (the 📍 button, or a tap on a place in the world). */
export function go(to){
  if(W.ride||!SPOT[to])return;
  const path=route(SPOT[to]);
  if(!path){face(to);return;}
  if(reduced()||!path.length){const e=path.at(-1)||W.me;W.me.x=e.x;W.me.z=e.z;face(to);W.auto=null;sense(true);wake();return;}
  let len=0,a=W.me;for(const b of path){len+=Math.hypot(b.x-a.x,b.z-a.z);a=b;}
  // A brisk walk: at most about a second, so a tap on 📍 never leaves you waiting.
  W.auto={path,to,speed:Math.max(4.2,len/1.1)};wake();
}
export function honk(){W.fx.push({k:'honk',t:0,life:1.1});wake();}
/** The ride to the buyer: `o` = {task, npc, place, sign, crate, items}. Resolves after the hand-over. */
export function ride(o){
  if(W.ride)return;
  const r=W.ride={...o,state:'load',t:0,x:0,z:2,yaw:0,v:0,steer:0,beep:0,deco:rideWorld(o)};
  W.me.tool=null;W.joy=null;W.look=null;
  W.hooks?.ride?.(W.x,{place:o.place,state:'ride'});wake();
  return r;
}
/** The order being delivered, or null. */
export function riding(){return W.ride?.task||null;}

/* ------------------------------------------------------------------ the stage element */
function build(){
  const el=document.createElement('div');el.className='fv-stage';el.setAttribute('data-morph-keep','');
  const cv=document.createElement('canvas');cv.className='fv-cv';
  cv.setAttribute('role','img');cv.setAttribute('aria-label',tr('Nông trại: đi quanh vườn, tới gần một chỗ để làm việc'));
  let c=null;try{c=cv.getContext('2d',{alpha:false});}catch{c=null;}
  if(!c||typeof c.ellipse!=='function'||typeof c.roundRect!=='function')return false;
  el.append(cv);W.el=el;W.cv=cv;W.c=c;
  input(cv);
  return true;
}
function observe(){
  if(W.ro||!globalThis.ResizeObserver)return;
  W.ro=new ResizeObserver(()=>{W.dirty=true;wake();});W.ro.observe(W.el);
}
function size(){
  const r=W.el.getBoundingClientRect(),dpr=Math.min(2,globalThis.devicePixelRatio||1)*W.q;
  const w=Math.max(1,Math.round(r.width)),h=Math.max(1,Math.round(r.height));
  if(w===W.w&&h===W.h&&dpr===W.dpr)return;
  W.w=w;W.h=h;W.dpr=dpr;W.cv.width=Math.round(w*dpr);W.cv.height=Math.round(h*dpr);
}
const alive=()=>W.el?.isConnected&&!document.hidden&&!!W.el.closest('dialog[open]')&&W.el.getClientRects().length>0;
function wake(){W.calm=0;if(!W.raf){clearTimeout(W.timer);W.timer=0;W.last=0;W.raf=requestAnimationFrame(loop);}}
function loop(now){
  W.raf=0;
  if(!alive()){W.last=0;return;}
  // The canvas is sized here, not in the ResizeObserver callback (a resize there is a layout change inside it).
  if(!W.w||W.dirty){W.dirty=false;size();}
  const raw=W.last?now-W.last:0,dt=raw?Math.min(0.05,raw/1000):1/60;W.last=now;W.t+=dt;
  step(dt);
  const t0=performance.now();
  try{draw();}catch(error){console.error(error);W.broken=true;W.hooks?.broken?.(W.x);return;}
  perf(performance.now()-t0,raw);
  // Nothing moving: a calm 10 frames a second for the wind in the leaves, the hens and the clouds.
  if(++W.calm>90&&!busy())W.timer=setTimeout(()=>{W.timer=0;W.raf=requestAnimationFrame(loop);},90);
  else W.raf=requestAnimationFrame(loop);
}
const busy=()=>!!(W.joy||W.look||W.keys.size||W.auto||W.ride||W.fx.length||W.hint);
/** Frame time, measured while something moves (walking, the ride): data-ms (drawing) and data-gap (between frames)
 * on the stage. A phone that cannot keep up draws fewer pixels first; still too slow, the workbench goes back to
 * its buttons (hooks.slow), once. */
function perf(ms,gap){
  const P=W.perf;P.ms=P.ms?P.ms*0.9+ms*0.1:ms;
  if(++P.shown>=30){P.shown=0;W.el.dataset.ms=P.ms.toFixed(1);}
  if(!busy()||!gap||gap>400)return;   // calm frames are slowed on purpose; a long gap is a pause, not a slow phone
  P.n++;P.sum+=ms;P.gaps+=gap;
  if(P.n<45)return;
  const g=P.gaps/P.n,cpu=P.sum/P.n;P.n=0;P.sum=0;P.gaps=0;
  W.el.dataset.gap=g.toFixed(1);W.el.dataset.busy=cpu.toFixed(1);W.el.dataset.q=String(W.q);
  if(g>70||cpu>45){
    if(++P.bad<2)return;P.bad=0;
    if(W.q>0.55){W.q=W.q>0.8?0.75:0.55;size();return;}
    W.hooks?.slow?.(W.x);
  }else P.bad=0;
}

/* ------------------------------------------------------------------ input */
function input(cv){
  cv.addEventListener('pointerdown',e=>{
    if(e.button>0)return;
    const r=cv.getBoundingClientRect(),px=e.clientX-r.left,py=e.clientY-r.top;
    try{cv.setPointerCapture(e.pointerId);}catch{/* not capturable */}
    // Left part: the stick (it appears where the thumb lands). Right part: drag to look around.
    if(px<r.width*0.45&&!W.joy)W.joy={id:e.pointerId,ox:px,oy:py,dx:0,dy:0,t:performance.now()};
    else if(!W.look)W.look={id:e.pointerId,x:px,y:py,sx:px,sy:py,t:performance.now()};
    W.auto=null;wake();e.preventDefault();
  });
  const move=e=>{
    const r=cv.getBoundingClientRect(),px=e.clientX-r.left,py=e.clientY-r.top;
    if(W.joy?.id===e.pointerId){const R=joyR(),dx=px-W.joy.ox,dy=py-W.joy.oy,l=Math.hypot(dx,dy),k=l>R?R/l:1;W.joy.dx=dx*k/R;W.joy.dy=dy*k/R;W.joy.far=Math.max(W.joy.far||0,l);}
    else if(W.look?.id===e.pointerId){
      const dx=px-W.look.x,dy=py-W.look.y;W.look.x=px;W.look.y=py;
      if(W.ride)return;
      W.me.yaw=wrap(W.me.yaw+dx*0.0065);
      if(W.cam==='fp')W.me.pitch=clamp(W.me.pitch+dy*0.004,-0.35,0.6);
    }
    wake();
  };
  const up=e=>{
    const r=cv.getBoundingClientRect(),px=e.clientX-r.left,py=e.clientY-r.top;
    const quick=g=>g&&performance.now()-g.t<350;
    if(W.joy?.id===e.pointerId){if(quick(W.joy)&&(W.joy.far||0)<10)tap(px,py);W.joy=null;}
    else if(W.look?.id===e.pointerId){if(quick(W.look)&&Math.hypot(px-W.look.sx,py-W.look.sy)<10)tap(px,py);W.look=null;}
    wake();
  };
  cv.addEventListener('pointermove',move);
  cv.addEventListener('pointerup',up);
  cv.addEventListener('pointercancel',e=>{if(W.joy?.id===e.pointerId)W.joy=null;if(W.look?.id===e.pointerId)W.look=null;});
  cv.addEventListener('contextmenu',e=>e.preventDefault());
  const typing=e=>e.target?.closest?.('input,textarea,select,[contenteditable="true"]');
  addEventListener('keydown',e=>{
    if(!alive()||typing(e)||e.ctrlKey||e.metaKey||e.altKey||document.querySelector('#confirmDialog[open]'))return;
    const k=KEYS[e.key.length===1?e.key.toLowerCase():e.key];if(!k)return;
    if(k==='act'){const b=document.querySelector('#sheet[open] .fv-acts .gd-cta:not([disabled]),#sheet[open] .fv-acts .fv-btn:not([disabled])');if(b){e.preventDefault();b.click();}return;}
    W.keys.add(k);W.auto=null;e.preventDefault();wake();
  });
  addEventListener('keyup',e=>{const k=KEYS[e.key.length===1?e.key.toLowerCase():e.key];if(k)W.keys.delete(k);});
  addEventListener('blur',()=>W.keys.clear());
}
const KEYS={w:'f',ArrowUp:'f',s:'b',ArrowDown:'b',a:'l',ArrowLeft:'l',d:'r',ArrowRight:'r',q:'sl',e:'act',Enter:'act'};
const joyR=()=>Math.max(38,Math.min(60,W.w*0.13));
/** A short tap on the world: walk to the place under the finger. */
function tap(px,py){
  if(W.ride){honk();return;}
  const V=view();let best=null,bd=1e9;
  for(const [id,s] of Object.entries(SPOT)){
    const cx=(s[0]+s[2])/2,cz=(s[1]+s[3])/2,h=id.startsWith('P')?0.5:1.2,p=cam3(V,cx,h,cz);
    if(p[2]<NEAR)continue;
    const sx=V.cx+V.f*p[0]/p[2],sy=V.cy-V.f*p[1]/p[2],rad=Math.max(28,V.f*Math.max(s[2]-s[0],s[3]-s[1])*0.55/p[2]),d=Math.hypot(sx-px,sy-py);
    if(d<rad&&p[2]<bd){bd=p[2];best=id;}
  }
  if(best)go(best);
}

/* ------------------------------------------------------------------ walking */
function step(dt){
  for(const f of W.fx)f.t+=dt;W.fx=W.fx.filter(f=>f.t<f.life);
  if(W.ride){rideStep(dt);return;}
  const me=W.me,k=W.keys;
  let fwd=0,turn=0,side=0;
  if(W.joy){fwd=-W.joy.dy;turn=W.joy.dx;if(Math.abs(fwd)<0.12)fwd=0;if(Math.abs(turn)<0.12)turn=0;}
  if(k.has('f'))fwd=1;if(k.has('b'))fwd=-0.7;if(k.has('l'))turn=-1;if(k.has('r'))turn=1;if(k.has('sl'))side=-1;
  if(fwd||turn||side)W.auto=null;
  me.yaw=wrap(me.yaw+turn*TURN*dt*(W.joy?0.85:1));
  let vx=0,vz=0;
  const sn=Math.sin(me.yaw),cs=Math.cos(me.yaw);
  if(fwd||side){vx=(sn*fwd+cs*side)*WALK;vz=(cs*fwd-sn*side)*WALK;}
  if(W.auto){
    const a=W.auto,n=a.path[0];
    if(!n){W.auto=null;face(a.to);}
    else{
      const dx=n.x-me.x,dz=n.z-me.z,d=Math.hypot(dx,dz),s=a.speed*dt;
      me.yaw=wrap(me.yaw+wrap(Math.atan2(dx,dz)-me.yaw)*Math.min(1,dt*12));
      if(d<=s){me.x=n.x;me.z=n.z;a.path.shift();if(!a.path.length){W.auto=null;face(a.to);}}
      else{me.x+=dx/d*s;me.z+=dz/d*s;}
      me.moving=1;me.bob+=dt*a.speed*2.2;W.moved+=a.speed*dt;
    }
  }
  if(vx||vz){
    const nx=me.x+vx*dt,nz=me.z+vz*dt;
    if(free(nx,me.z))me.x=nx;if(free(me.x,nz))me.z=nz;
    me.bob+=dt*Math.hypot(vx,vz)*2.4;me.moving=1;W.moved+=Math.hypot(vx,vz)*dt;
  }else if(!W.auto)me.moving=Math.max(0,me.moving-dt*4);
  if(W.hint&&(W.moved>2||W.t-W.hint>9))W.hint=0;
  sense(false);
  hens(dt);
}
function free(x,z){
  if(x<FIELD.x0+RAD||x>FIELD.x1-RAD||z<FIELD.z0+RAD||z>FIELD.z1-RAD)return false;
  for(const s of SOLID)if(x>s[0]-RAD&&x<s[2]+RAD&&z>s[1]-RAD&&z<s[3]+RAD)return false;
  return true;
}
const gap=(s,x,z)=>Math.hypot(Math.max(s[0]-x,0,x-s[2]),Math.max(s[1]-z,0,z-s[3]));
/** The place you are at: the nearest one within reach, the one in front of you winning a tie. A small margin
 * keeps the buttons from flickering on a border. */
function sense(force){
  const me=W.me;let best=null,bd=1e9;
  for(const [id,s] of Object.entries(SPOT)){
    const d=gap(s,me.x,me.z);if(d>REACH)continue;
    const cx=(s[0]+s[2])/2-me.x,cz=(s[1]+s[3])/2-me.z,ahead=(Math.sin(me.yaw)*cx+Math.cos(me.yaw)*cz)/(Math.hypot(cx,cz)||1);
    const score=d+0.5*(1-ahead);if(score<bd){bd=score;best=id;}
  }
  if(!force&&best!==W.near&&W.near&&SPOT[W.near]&&gap(SPOT[W.near],me.x,me.z)<REACH+0.15&&best)return;
  if(best===W.near)return;
  W.near=best;W.hooks?.near?.(W.x,best);
}
function face(to){const s=SPOT[to];if(!s)return;const me=W.me;me.yaw=Math.atan2((s[0]+s[2])/2-me.x,(s[1]+s[3])/2-me.z);me.pitch=BEDS[to]?0.38:0.1;sense(true);}
/** Grid walk (half a metre a cell) to the closest cell within reach of the footprint. */
function route(s){
  const C=0.5,nx=Math.ceil((FIELD.x1-FIELD.x0)/C),nz=Math.ceil((FIELD.z1-FIELD.z0)/C),cell=(i,j)=>({x:FIELD.x0+(i+0.5)*C,z:FIELD.z0+(j+0.5)*C});
  const at=(x,z)=>[clamp(Math.floor((x-FIELD.x0)/C),0,nx-1),clamp(Math.floor((z-FIELD.z0)/C),0,nz-1)];
  const [si,sj]=at(W.me.x,W.me.z),seen=new Float32Array(nx*nz).fill(Infinity),from=new Int32Array(nx*nz).fill(-1);
  const goal=(i,j)=>{const p=cell(i,j),d=gap(s,p.x,p.z);return d<=REACH-0.25&&d>=0.25;};
  if(gap(s,W.me.x,W.me.z)<=REACH-0.1)return [];
  const open=[[0,si,sj]];seen[sj*nx+si]=0;let end=-1;
  while(open.length){
    let bi=0;for(let i=1;i<open.length;i++)if(open[i][0]<open[bi][0])bi=i;
    const [d,i,j]=open.splice(bi,1)[0];if(d>seen[j*nx+i])continue;
    if(goal(i,j)){end=j*nx+i;break;}
    for(const [di,dj,w] of [[1,0,1],[-1,0,1],[0,1,1],[0,-1,1],[1,1,1.41],[1,-1,1.41],[-1,1,1.41],[-1,-1,1.41]]){
      const a=i+di,b=j+dj;if(a<0||b<0||a>=nx||b>=nz)continue;
      const p=cell(a,b);if(!free(p.x,p.z))continue;
      if(di&&dj){const q1=cell(i+di,j),q2=cell(i,j+dj);if(!free(q1.x,q1.z)||!free(q2.x,q2.z))continue;}
      const nd=d+w;if(nd<seen[b*nx+a]){seen[b*nx+a]=nd;from[b*nx+a]=j*nx+i;open.push([nd,a,b]);}
    }
  }
  if(end<0)return null;
  const cells=[];for(let k=end;k>=0&&k!==sj*nx+si;k=from[k])cells.unshift(cell(k%nx,Math.floor(k/nx)));
  // Pull the string: keep a corner only where the straight line would bump into something.
  const out=[];let a={x:W.me.x,z:W.me.z};
  for(let i=0;i<cells.length;i++){const nxt=cells[i+1];if(nxt&&clear(a,nxt))continue;out.push(cells[i]);a=cells[i];}
  return out;
}
function clear(a,b){const n=Math.ceil(Math.hypot(b.x-a.x,b.z-a.z)/0.2);for(let i=1;i<=n;i++){const t=i/n;if(!free(a.x+(b.x-a.x)*t,a.z+(b.z-a.z)*t))return false;}return true;}

/* ------------------------------------------------------------------ what changed (the effect of a command) */
function changes(){
  const d=farm(),snap={plots:Object.fromEntries((d.plots||[]).map(p=>[p.id,{m:p.moisture,c:p.crop,w:p.weeds,g:p.growth,s:p.seen,o:p.compost||p.npk}])),nest:d.coop?.nest||0,fed:!!d.fed_today};
  const was=W.seen;W.seen=snap;if(!was)return;
  for(const [id,p] of Object.entries(snap.plots)){
    const o=was.plots[id];if(!o)continue;const [x,z]=BEDS[id];
    if(p.m>o.m+4)W.fx.push({k:'water',x,z,t:0,life:1.4});
    if(o.c&&!p.c)W.fx.push({k:'pop',x,z,t:0,life:1.2,e:cropOf(o.c).emoji});
    if(!o.c&&p.c)W.fx.push({k:'seed',x,z,t:0,life:1});
    if(p.w<o.w)W.fx.push({k:'weed',x,z,t:0,life:0.9});
    if(p.o&&!o.o)W.fx.push({k:'feed',x,z,t:0,life:1});
  }
  if(snap.nest<was.nest)W.fx.push({k:'pop',x:-9,z:15.4,t:0,life:1.2,e:'🥚'});
  if(snap.fed&&!was.fed)W.fx.push({k:'grain',x:-5.3,z:17.3,t:0,life:1.6});
  if(W.fx.length)wake();
}

/* ------------------------------------------------------------------ camera + projection */
function view(){
  const w=W.w,h=W.h,f=w/2/Math.tan(Math.min(1.25,0.62+w/h*0.32)/2);
  let x,y,z,yaw,pitch;
  if(W.ride){const r=W.ride;x=r.x;z=r.z;y=1.28;yaw=r.yaw;pitch=0.05;}
  else if(W.cam==='tp'){
    const me=W.me,back=behind(me);
    x=me.x-Math.sin(me.yaw)*back;z=me.z-Math.cos(me.yaw)*back;y=1.15+back*0.45;yaw=me.yaw;pitch=0.32;
  }else{const me=W.me,b=reduced()?0:Math.sin(me.bob)*0.035*me.moving;x=me.x;z=me.z;y=EYE+b;yaw=me.yaw;pitch=me.pitch;}
  return {x,y,z,yaw,pitch,f,cx:w/2,cy:h*0.46,s:Math.sin(yaw),c:Math.cos(yaw),sp:Math.sin(pitch),cp:Math.cos(pitch)};
}
/** How far behind you the third-person camera can stand (it stops before a wall, the fence or the coop). */
function behind(me){
  let d=3.4;const sn=Math.sin(me.yaw),cs=Math.cos(me.yaw);
  for(let t=0.6;t<=3.4;t+=0.2){const x=me.x-sn*t,z=me.z-cs*t;
    if(x<FIELD.x0-1||x>FIELD.x1+1||z<FIELD.z0-1||z>FIELD.z1+1){d=t-0.2;break;}
    let hit=false;for(const s of [SPOT.coop,SPOT.shed,[-12.6,-1.2,-9.6,1.6],[7,-4.3,11.2,-2.6]])if(x>s[0]&&x<s[2]&&z>s[1]&&z<s[3])hit=true;
    if(hit){d=t-0.2;break;}}
  return Math.max(1.2,d);
}
function cam3(V,x,y,z){const dx=x-V.x,dy=y-V.y,dz=z-V.z,X=dx*V.c-dz*V.s,Z=dx*V.s+dz*V.c;return [X,dy*V.cp+Z*V.sp,Z*V.cp-dy*V.sp];}
function clip(P){
  const out=[];
  for(let i=0;i<P.length;i++){const a=P[i],b=P[(i+1)%P.length],ia=a[2]>=NEAR,ib=b[2]>=NEAR;
    if(ia)out.push(a);
    if(ia!==ib){const t=(NEAR-a[2])/(b[2]-a[2]);out.push([a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,NEAR]);}}
  return out;
}
/** A flat polygon (world points [x,y,z, x,y,z, …]) clipped at the eye and filled. */
function poly(c,V,pts,col,edge){
  let P=[];for(let i=0;i<pts.length;i+=3)P.push(cam3(V,pts[i],pts[i+1],pts[i+2]));
  if(P.every(p=>p[2]<NEAR))return false;
  P=clip(P);if(P.length<3)return false;
  c.beginPath();for(let i=0;i<P.length;i++){const p=P[i],sx=V.cx+V.f*p[0]/p[2],sy=V.cy-V.f*p[1]/p[2];if(i)c.lineTo(sx,sy);else c.moveTo(sx,sy);}
  c.closePath();c.fillStyle=col;c.fill();
  if(edge){c.strokeStyle=edge;c.lineWidth=1;c.stroke();}
  return true;
}
function line3(c,V,a,b,col,wm){
  let A=cam3(V,a[0],a[1],a[2]),B=cam3(V,b[0],b[1],b[2]);
  if(A[2]<NEAR&&B[2]<NEAR)return;
  const cut=(p,q)=>{const t=(NEAR-p[2])/(q[2]-p[2]);return [p[0]+(q[0]-p[0])*t,p[1]+(q[1]-p[1])*t,NEAR];};
  if(A[2]<NEAR)A=cut(A,B);else if(B[2]<NEAR)B=cut(B,A);
  c.strokeStyle=col;c.lineWidth=Math.max(1,wm*V.f*2/(A[2]+B[2]));c.lineCap='round';c.beginPath();
  c.moveTo(V.cx+V.f*A[0]/A[2],V.cy-V.f*A[1]/A[2]);c.lineTo(V.cx+V.f*B[0]/B[2],V.cy-V.f*B[1]/B[2]);c.stroke();
}
/** Screen point and scale (px per metre) of a world point, or null behind the eye. */
function spot(V,x,y,z){const p=cam3(V,x,y,z);if(p[2]<NEAR*2)return null;const k=V.f/p[2];return {x:V.cx+p[0]*k,y:V.cy-p[1]*k,k,d:p[2]};}

/* colours: light and distance haze, cached */
const RGB=new Map(),TONE=new Map();
function rgb(hex){let v=RGB.get(hex);if(!v){const n=parseInt(hex.slice(1,7),16);v=[n>>16&255,n>>8&255,n&255];RGB.set(hex,v);}return v;}
function tone(hex,l=1,fog=0){
  const L=Math.round(l*24)/24,F=Math.round(fog*20)/20,key=hex+L+'|'+F;let s=TONE.get(key);
  if(!s){const [r,g,b]=rgb(hex),[fr,fg,fb]=W.fogRGB,m=(v,f)=>Math.round(clamp(v*L,0,255)*(1-F)+f*F);s=`rgb(${m(r,fr)},${m(g,fg)},${m(b,fb)})`;if(TONE.size>5000)TONE.clear();TONE.set(key,s);}
  return s;
}
const haze=d=>clamp((d-16)/75,0,0.62);

/* ------------------------------------------------------------------ meshes */
function cross(a,b){return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];}
function quad(pts,col,out){const n=norm3(cross([pts[3]-pts[0],pts[4]-pts[1],pts[5]-pts[2]],[pts[6]-pts[0],pts[7]-pts[1],pts[8]-pts[2]]));
  const mx=pts.filter((_,i)=>i%3===0),mz=pts.filter((_,i)=>i%3===2),c=[mx.reduce((a,b)=>a+b)/mx.length,0,mz.reduce((a,b)=>a+b)/mz.length];
  // Normals point away from the middle of the shape they belong to.
  if(out&&(n[0]*(c[0]-out[0])+n[2]*(c[2]-out[2])+n[1]*(pts[1]-out[1]))<0){n[0]=-n[0];n[1]=-n[1];n[2]=-n[2];}
  return {p:pts,n,col,dec:[]};}
function box(x0,x1,y0,y1,z0,z1,col,top=col){
  const o=[(x0+x1)/2,(y0+y1)/2,(z0+z1)/2];
  return {o,faces:[
    quad([x0,y0,z0,x1,y0,z0,x1,y1,z0,x0,y1,z0],col,o),quad([x0,y0,z1,x1,y0,z1,x1,y1,z1,x0,y1,z1],col,o),
    quad([x0,y0,z0,x0,y0,z1,x0,y1,z1,x0,y1,z0],col,o),quad([x1,y0,z0,x1,y0,z1,x1,y1,z1,x1,y1,z0],col,o),
    quad([x0,y1,z0,x1,y1,z0,x1,y1,z1,x0,y1,z1],top,o)]};
}
/** A small house: walls, a gable roof along x (overhang e) and its two gables. */
function house(x0,x1,z0,z1,h,rh,wall,roof,e=0.25){
  const m=box(x0,x1,0,h,z0,z1,wall),zm=(z0+z1)/2,o=m.o;m.faces.pop();
  m.faces.push(quad([x0,h,z0,x0,h,z1,x0,h+rh,zm],wall,o),quad([x1,h,z0,x1,h,z1,x1,h+rh,zm],wall,o));
  const ro=[o[0],h-1,o[2]];
  m.faces.push(quad([x0-e,h-0.12,z0-e,x1+e,h-0.12,z0-e,x1+e,h+rh,zm,x0-e,h+rh,zm],roof,ro),quad([x0-e,h-0.12,z1+e,x1+e,h-0.12,z1+e,x1+e,h+rh,zm,x0-e,h+rh,zm],roof,ro));
  return m;
}
/** A flat shape on a face (door, window), drawn right after it when that face shows. */
function decal(m,i,pts,col){m.faces[i].dec.push({p:pts,col});return m;}
function drawMesh(c,V,m){
  const d=cam3(V,m.o[0],m.o[1],m.o[2])[2],fog=haze(d);
  for(const f of m.faces){
    const p=f.p;if((V.x-p[0])*f.n[0]+(V.y-p[1])*f.n[1]+(V.z-p[2])*f.n[2]<=0)continue;
    const l=0.7+0.32*Math.max(0,f.n[0]*SUN[0]+f.n[1]*SUN[1]+f.n[2]*SUN[2]);
    const col=tone(f.col,l,fog);
    if(poly(c,V,p,col,col))for(const k of f.dec)poly(c,V,k.p,tone(k.col,l,fog));
  }
}

/* ------------------------------------------------------------------ the farm, built once */
let STATIC=null;
function statics(){
  if(STATIC)return STATIC;
  const S={meshes:[],trees:[],posts:[],flowers:[]};
  // Coop (door and nest box on its south face), shed (barn doors), cold room (blue door), packing table.
  const coop=house(-11,-7,16,18.6,1.9,0.9,'#fff1dc','#d9786a');
  decal(coop,0,[-9.5,0,15.99,-8.5,0,15.99,-8.5,1.3,15.99,-9.5,1.3,15.99],'#8a6a55');
  decal(coop,0,[-10.7,0.55,15.98,-9.8,0.55,15.98,-9.8,0.95,15.98,-10.7,0.95,15.98],'#c79b6a');
  S.meshes.push(coop);
  const shed=house(7,11.5,16,19.5,2.4,1.2,'#f1d2a6','#d9786a');
  decal(shed,0,[8.2,0,15.99,9.25,0,15.99,9.25,1.8,15.99,8.2,1.8,15.99],'#d9786a');
  decal(shed,0,[9.25,0,15.99,10.3,0,15.99,10.3,1.8,15.99,9.25,1.8,15.99],'#c9675a');
  S.meshes.push(shed);
  const cold=box(-12.6,-9.6,0,2.2,-1.2,1.6,'#f4f6f2','#dfe6e4');
  decal(cold,3,[-9.59,0,-0.6,-9.59,0,0.6,-9.59,1.8,0.6,-9.59,1.8,-0.6],'#8fc3d8');
  S.meshes.push(cold);
  S.meshes.push(box(-8.6,-6.6,0.78,0.88,-0.5,0.5,'#d8ab80'));
  for(const [x,z] of [[-8.5,-0.42],[-6.7,-0.42],[-8.5,0.42],[-6.7,0.42]])S.meshes.push(box(x-0.05,x+0.05,0,0.78,z-0.05,z+0.05,'#a97b55'));
  // Tank on its stand (the round tank and the well are sprites), hay bale.
  for(const [x,z] of [[9.05,8.55],[9.95,8.55],[9.05,9.45],[9.95,9.45]])S.meshes.push(box(x-0.05,x+0.05,0,1.5,z-0.05,z+0.05,'#9aa3a6'));
  S.meshes.push(box(11.4,12.8,0,0.9,1.3,2.7,'#ecd38a','#f3df9f'));
  // The trader's truck by the gate: cab, bed, crates of greens.
  S.truck=[box(7,8.4,0.45,1.9,-4.2,-2.7,'#7aa6c8','#8db6d4'),box(8.4,11.2,0.45,0.75,-4.25,-2.65,'#5f7f98'),box(8.4,11.2,0.75,1.15,-4.25,-4.15,'#6f97b7'),
    box(8.4,11.2,0.75,1.15,-2.75,-2.65,'#6f97b7'),box(11.1,11.2,0.75,1.15,-4.25,-2.65,'#6f97b7'),box(8.7,9.5,0.75,1.15,-3.9,-3.1,'#9cc56c'),box(9.7,10.5,0.75,1.1,-3.9,-3.1,'#e2a25c')];
  decal(S.truck[0],2,[6.99,1.15,-4.0,6.99,1.15,-2.9,6.99,1.75,-2.9,6.99,1.75,-4.0],'#cfe8f2');
  for(const [x,z] of [[7.6,-4.27],[7.6,-2.63],[10.3,-4.3],[10.3,-2.6]])S.truck.push(box(x-0.35,x+0.35,0,0.55,z-0.08,z+0.08,'#3f4448'));
  // The farmhouse up the hill and the trees around the field.
  S.far=[house(-3,3,30,34.5,2.6,1.6,'#fff3dd','#d9786a')];
  decal(S.far[0],0,[-0.5,0,29.99,0.5,0,29.99,0.5,1.7,29.99,-0.5,1.7,29.99],'#c9855f');
  const rnd=seeded(7);
  for(let i=0;i<46;i++){const a=i/46*TAU,r=19+rnd()*7,x=Math.sin(a)*r*0.95,z=10+Math.cos(a)*r*1.1;if(z<-9&&Math.abs(x)<4)continue;S.trees.push({x,z,s:0.8+rnd()*0.6,kind:rnd()<0.3?'palm':rnd()<0.6?'round':'bush'});}
  for(let i=0;i<9;i++)S.flowers.push({x:-12.6+i*0.55,z:24.9,s:0.8+rnd()*0.3});
  for(let i=0;i<8;i++)S.flowers.push({x:12.4-i*0.6,z:-4.9,s:0.8+rnd()*0.3});
  // Fence posts all round, with the gate open in the south side.
  const F=FIELD,step=2.2;
  for(let x=F.x0;x<=F.x1+0.01;x+=step){if(Math.abs(x)>1.8)S.posts.push([x,F.z0]);S.posts.push([x,F.z1]);}
  for(let z=F.z0+step;z<F.z1-0.01;z+=step){S.posts.push([F.x0,z]);S.posts.push([F.x1,z]);}
  // The run's low wire fence.
  S.run=[[-7,15.6],[-3.6,15.6],[-3.6,19],[-7,19]];
  return STATIC=S;
}
function seeded(s){return ()=>{s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}

/* ------------------------------------------------------------------ drawing */
function draw(){
  const c=W.c,V=view();
  c.setTransform(W.dpr,0,0,W.dpr,0,0);
  const wx=weather();
  sky(c,V,wx);
  if(W.ride)rideScene(c,V,wx);else farmScene(c,V,wx);
  overlays(c,V,wx);
}
function weather(){
  const d=farm(),id=d.weather?.id||'sun';
  if(W.sky!==id){W.sky=id;const f={sun:'#e8f4ee',hot:'#fbefd2',cloud:'#e2e8e4',rain:'#cdd6d5',wind:'#e6f2ef'}[id]||'#e8f4ee';W.fogRGB=rgb(f);TONE.clear();}
  return id;
}
const SKY={sun:['#9fd3ea','#e8f4ee'],hot:['#f2c47f','#fbefd2'],cloud:['#b7c5cb','#e2e8e4'],rain:['#8d9ca6','#cdd6d5'],wind:['#a5d5e6','#e6f2ef']};
const GRASS={sun:['#b9d792','#86b864'],hot:['#cfd78a','#9fba5d'],cloud:['#b2cf96','#83ad68'],rain:['#a6c491','#76a061'],wind:['#bad993','#85b763']};
function sky(c,V,wx){
  const w=W.w,h=W.h,hy=V.cy-V.f*Math.tan(V.pitch),[top,low]=SKY[wx]||SKY.sun;
  const g=c.createLinearGradient(0,Math.min(0,hy-V.f),0,Math.max(1,hy));g.addColorStop(0,top);g.addColorStop(1,low);
  c.fillStyle=g;c.fillRect(0,0,w,Math.max(0,hy)+2);
  // The sun (to the south-east, a little high) and the clouds, on the sky dome.
  const dome=(az,el)=>{const da=wrap(az-V.yaw);if(Math.abs(da)>1.2)return null;return {x:V.cx+V.f*Math.tan(da),y:hy-V.f*Math.tan(el)};};
  const s=dome(2.4,0.55);
  if(s&&wx!=='rain'){const r=wx==='hot'?34:26;E(c,s.x,s.y,r*1.8,r*1.8,wx==='hot'?'#fff3c466':'#fff8d855');E(c,s.x,s.y,r,r,wx==='hot'?'#ffe49a':'#fff1b8');}
  const n=wx==='cloud'||wx==='rain'?9:wx==='hot'?2:5;
  for(let i=0;i<n;i++){const p=dome(i*2.1+W.t*0.004+(i%3)*0.4,0.18+(i*37%10)/40);if(!p)continue;const k=(wx==='rain'?'#c4ccd0':'#ffffff');cloud(c,p.x,p.y,0.7+(i%3)*0.25,k);}
  // Far hills: two bands that turn with you.
  const band=(amp,base,col,ph)=>{c.beginPath();c.moveTo(0,h);for(let px=0;px<=w+6;px+=6){const th=V.yaw+Math.atan((px-V.cx)/V.f);const e=base+amp*(0.55+0.3*Math.sin(th*3+ph)+0.15*Math.sin(th*7+ph*2));c.lineTo(px,hy-V.f*e);}c.lineTo(w,h);c.closePath();c.fillStyle=col;c.fill();};
  band(0.05,0.012,wx==='rain'?'#a9bab6':'#b8d3c4',1);band(0.035,0.004,wx==='rain'?'#97b096':'#a6c993',2.4);
  const [far,near]=GRASS[wx]||GRASS.sun,gg=c.createLinearGradient(0,Math.max(0,hy),0,h);gg.addColorStop(0,far);gg.addColorStop(1,near);
  c.fillStyle=gg;c.fillRect(0,Math.max(0,hy),w,h-Math.max(0,hy)+1);
}
function cloud(c,x,y,s,col){E(c,x,y,32*s,15*s,col);E(c,x-24*s,y+5*s,20*s,11*s,col);E(c,x+26*s,y+4*s,22*s,12*s,col);E(c,x+4*s,y-9*s,19*s,13*s,col);}

function farmScene(c,V,wx){
  const S=statics(),d=farm(),t=task(),Q=[];
  // Ground: paths of packed earth, the bed field, the yard by the packing table, the road out of the gate.
  const G=(pts,col)=>poly(c,V,pts,tone(col,1,0.1));
  const rect=(x0,z0,x1,z1,col)=>G([x0,0,z0,x1,0,z0,x1,0,z1,x0,0,z1],col);
  rect(-1.3,-14,1.3,21,'#e2cda2');rect(-13,3.4,13,4.8,'#e2cda2');rect(-8.2,10,9,10.5,'#ddc79b');
  rect(-7.4,6.6,7.4,14.2,'#cdb085');rect(-13,-2,-4,2.4,'#e5d2a9');rect(-12,14.6,12,15.4,'#e2cda2');rect(4,-5.2,12.2,-1.8,'#e5d2a9');
  rect(-1.4,-40,1.4,-5.3,'#d7c7a6');
  // Static meshes, sorted with everything else by distance.
  const add=(o,fn)=>{const p=cam3(V,o[0],o[1],o[2]);if(p[2]>-3)Q.push([p[2],fn]);};
  for(const m of S.meshes)add(m.o,()=>drawMesh(c,V,m));
  for(const m of S.far)add(m.o,()=>drawMesh(c,V,m));
  add([9.3,0.8,-3.4],()=>{for(const m of [...S.truck].sort((a,b)=>cam3(V,...b.o)[2]-cam3(V,...a.o)[2]))drawMesh(c,V,m);});
  for(const tr_ of S.trees)add([tr_.x,1,tr_.z],()=>tree(c,V,tr_));
  for(const f of S.flowers)add([f.x,0.5,f.z],()=>{const p=spot(V,f.x,0,f.z);if(p)sunflower(c,p,f.s,W.t);});
  for(let i=0;i<S.posts.length;i++){const [px,pz]=S.posts[i];add([px,0.6,pz],()=>post(c,V,px,pz,S.posts,i));}
  add([-5.3,0.4,17.3],()=>run(c,V,S.run));
  // Beds, the tank and well, the coop's hens and eggs, the crate, the scooter, the signs, the people.
  for(const p of d.plots||[]){const b=BEDS[p.id];if(b)add([b[0],0.2,b[1]],()=>bed(c,V,p,b));}
  add([9.5,1.6,9],()=>{const q=spot(V,9.5,0,9);if(q)tank(c,q,!!d.nopump);});
  add([9.5,0.6,6.4],()=>{const q=spot(V,9.5,0,6.4);if(q)well(c,q);});
  for(const hn of W.hens)add([hn.x,0.2,hn.z],()=>{const q=spot(V,hn.x,0,hn.z);if(q)hen(c,q,hn,W.t,(d.coop?.mood??80)<35);});
  add([-10.2,0.8,15.7],()=>eggs(c,V,d.coop?.nest||0));
  add([-7.6,1,0],()=>crate(c,V,t,d));
  add([-5,0.5,-2],()=>bike(c,V,t));
  for(const s of signs(d,t))add([s.x,s.y,s.z],()=>sign(c,V,s));
  add([12.1,1,2],()=>{const q=spot(V,12.1,0.9,2);if(q)cat(c,q,W.t);});
  add([6.2,0.8,-4.7],()=>{const q=spot(V,6.2,0,-4.75);if(q)person(c,q,{hair:'#3c2f28',top:'#8fb3cf',skin:'#e9c3a0',hat:true,wave:W.near==='truck'});});
  if(d.bees)add([0,1,10],()=>bees(c,V));
  if(W.cam==='tp')add([W.me.x,0.8,W.me.z],()=>{const q=spot(V,W.me.x,0,W.me.z);if(q)player(c,q);});
  for(const f of W.fx)add([f.x??0,1,f.z??0],()=>effect(c,V,f));
  const target=W.x?.ui?.fvTarget;
  if(target&&SPOT[target]&&target!==W.near){const s=SPOT[target],x=(s[0]+s[2])/2,z=(s[1]+s[3])/2;add([x,2.5,z],()=>marker(c,V,x,z,target));}
  Q.sort((a,b)=>b[0]-a[0]);
  for(const [,fn] of Q)fn();
  if(wx==='rain')rain(c);
  if(wx==='wind')leaves(c);
}

/* ---- beds */
const SOIL=(p,m)=>p.moisture<m.dry?'#d8b78c':p.moisture<m.low?'#c49d72':p.moisture>m.wet?'#5f4330':p.moisture>m.high?'#71503a':'#8e6545';
function bed(c,V,p,[x,z]){
  const m=W.x.cc.moisture||{dry:25,low:40,high:80,wet:90},th=W.x.cc.thresholds||{young:70,ripe:100,over:140,rotten:180};
  const mesh=box(x-BX,x+BX,0,BH,z-BZ,z+BZ,'#b98a5c',SOIL(p,m));drawMesh(c,V,mesh);
  const top=(px,pz,r,col)=>poly(c,V,circle(px,BH+0.005,pz,r,7),col);
  if(p.moisture>m.high)for(const [dx,dz] of [[-0.9,0.2],[0.6,-0.25],[1.1,0.3]])top(x+dx,z+dz,0.22,'#8eb7c8aa');
  if(p.compost&&!p.crop)for(const [dx,dz] of [[-1,-0.3],[0,0.3],[1,-0.2],[-0.4,0.1]])top(x+dx,z+dz,0.12,'#5a3d2a');
  // Plants, back to front; a thirsty bed droops; ripe fruit shows; weeds and the pests you found are there too.
  const pts=[];
  if(p.crop){
    const tall=p.crop==='tomato'||p.crop==='cucumber',cols=tall?3:4,rows=tall?1:2;
    for(let i=0;i<cols;i++)for(let j=0;j<rows;j++)pts.push([x+(-1.05+i*2.1/(cols-1)),z+(rows>1?(j?0.32:-0.32):0),i*3+j]);
  }
  for(let i=0;i<p.weeds;i++)pts.push([x-1.3+i*1.1,z+(i%2?0.55:-0.55),'w']);
  const pp=pts.map(q=>({q,s:spot(V,q[0],BH,q[1])})).filter(o=>o.s).sort((a,b)=>b.s.d-a.s.d);
  const thirst=p.moisture<m.dry?1:p.moisture<m.low?0.55:0;
  const stage=!p.crop?null:p.growth>=th.rotten?'rotten':p.growth>=th.over?'over':p.growth>=th.ripe?'ripe':p.growth>=(th.ripe-15)?'almost':p.growth>=th.young*0.55?'young':'sprout';
  for(const {q,s} of pp){if(q[2]==='w')weed(c,s);else plant(c,s,p.crop,stage,thirst,q[2],(p.seen||0)>0&&p.scouted_today?q[2]%3===0:false);}
}
function circle(x,y,z,r,n){const a=[];for(let i=0;i<n;i++){const t=i/n*TAU;a.push(x+Math.cos(t)*r,y,z+Math.sin(t)*r*0.8);}return a;}
function weed(c,s){const k=s.k,h=0.22*k;if(h<2)return;for(const a of [-0.5,0,0.5])L(c,s.x,s.y,s.x+Math.sin(a)*h*0.7,s.y-h*(1-Math.abs(a)*0.3),'#8fa63c',Math.max(1,0.03*k));}
/** One plant. `stage`: sprout … rotten; `thirst` 0–1 droops it and fades its green; `bug`: a caterpillar on it. */
function plant(c,s,crop,stage,thirst,seed,bug){
  const k=s.k,sw=Math.sin(W.t*1.7+seed)*(W.sky==='wind'?0.05:0.02)*k,size={sprout:0.3,young:0.62,almost:0.88,ripe:1,over:1.04,rotten:0.7}[stage]||1;
  if(k*size*0.4<1.5){E(c,s.x,s.y-1,1.5,1.5,'#6b9b4a');return;}
  const green=thirst>0.8?'#a7a65a':thirst>0?'#86a74e':stage==='over'?'#a9b44f':'#5e9e46',light=thirst>0.8?'#c4bf74':thirst>0?'#a5c063':stage==='over'?'#c8c867':'#86c25d';
  const droop=thirst*0.9;
  if(stage==='rotten'){E(c,s.x,s.y-0.04*k,0.24*k,0.07*k,'#7b5a3a');E(c,s.x+0.06*k,s.y-0.07*k,0.12*k,0.05*k,'#8f6b45');return;}
  if(stage==='sprout'){L(c,s.x,s.y,s.x+sw,s.y-0.09*k,green,Math.max(1,0.015*k));c.save();c.translate(s.x+sw,s.y-0.09*k);
    E(c,-0.035*k,0,0.04*k,0.018*k,light);E(c,0.035*k,0,0.04*k,0.018*k,light);c.restore();return;}
  const leaf=(ang,len,wid,col)=>{const a=ang+(ang>0?droop:-droop);c.save();c.translate(s.x+sw*0.6,s.y-0.04*k*size);c.rotate(a);c.beginPath();c.ellipse(0,-len*k/2,wid*k,len*k/2,0,0,TAU);c.fillStyle=col;c.fill();c.restore();};
  if(crop==='lettuce'){const r=0.2*size*k;E(c,s.x,s.y-r*0.55,r*1.15,r*0.75*(1-droop*0.3),green);E(c,s.x,s.y-r*0.75,r*0.85,r*0.6,light);E(c,s.x,s.y-r*0.9,r*0.45,r*0.35,'#c6e58f');return;}
  if(crop==='muong'){for(const [a,l] of [[-0.55,0.3],[-0.25,0.38],[0,0.42],[0.25,0.38],[0.55,0.3]])leaf(a,l*size,0.035*size,(a*100|0)%2?green:light);return;}
  if(crop==='herbs'){for(const [a,l] of [[-0.7,0.22],[-0.3,0.28],[0.1,0.3],[0.45,0.26],[0.8,0.2]])leaf(a,l*size,0.05*size,(a*10|0)%2?green:light);E(c,s.x+sw,s.y-0.2*size*k,0.07*size*k,0.05*size*k,light);return;}
  // Tomato on a stake, cucumber on a trellis: leaves up the stem, the fruit when it is there.
  const H=(crop==='tomato'?0.85:0.75)*size;
  L(c,s.x,s.y,s.x,s.y-(crop==='tomato'?0.95:1.05)*k,'#b08a5e',Math.max(1,0.025*k));
  if(crop==='cucumber')L(c,s.x-0.25*k,s.y-0.95*k,s.x+0.25*k,s.y-0.95*k,'#b08a5e',Math.max(1,0.02*k));
  L(c,s.x,s.y,s.x+sw,s.y-H*k,green,Math.max(1,0.03*k));
  for(let i=0;i<4;i++){const y=s.y-H*k*(0.25+i*0.22),side=i%2?1:-1,lr=(crop==='cucumber'?0.13:0.1)*size*k;
    c.save();c.translate(s.x+sw*(i/4)+side*lr*0.8,y+droop*lr*1.2);c.rotate(side*(0.5+droop));E(c,0,0,lr,lr*0.6,i%2?green:light);c.restore();}
  if(stage==='young')return;
  const ripe=stage==='ripe'||stage==='over';
  if(crop==='tomato'){for(const [dx,dy] of [[-0.09,0.45],[0.1,0.55],[-0.04,0.68]]){const r=(ripe?0.065:0.045)*k;E(c,s.x+dx*k,s.y-dy*k*size,r,r,stage==='over'?'#b8432f':ripe?'#e2533c':'#8fbf5a');if(ripe)E(c,s.x+dx*k-r*0.3,s.y-dy*k*size-r*0.3,r*0.3,r*0.3,'#ffffff66');}}
  else for(const [dx,dy] of [[-0.12,0.4],[0.12,0.55]]){c.save();c.translate(s.x+dx*k,s.y-dy*k*size);c.rotate(0.15);E(c,0,0,(ripe?0.035:0.025)*k,(ripe?0.12:0.07)*k,stage==='over'?'#c9b048':ripe?'#3f8a3a':'#9ccf6a');c.restore();}
  if(bug){c.save();c.translate(s.x+0.08*k,s.y-H*k*0.6);for(let i=0;i<4;i++)E(c,i*0.022*k,Math.sin(W.t*4+i)*0.006*k,0.014*k,0.014*k,'#9acb3c');E(c,0.09*k,0,0.016*k,0.016*k,'#5b7d27');c.restore();}
}
/* ---- the rest of the farm */
function tree(c,V,t){
  const s=spot(V,t.x,0,t.z);if(!s)return;const k=s.k*t.s,fog=haze(s.d);
  if(k<0.6)return;
  E(c,s.x,s.y,0.9*k,0.22*k,tone('#5f7f4a',0.8,fog));
  if(t.kind==='palm'){c.strokeStyle=tone('#9a7a55',1,fog);c.lineWidth=Math.max(1,0.18*k);c.beginPath();c.moveTo(s.x,s.y);c.quadraticCurveTo(s.x+0.3*k,s.y-2.2*k,s.x+0.15*k,s.y-4.2*k);c.stroke();
    for(let i=0;i<6;i++){const a=i/6*TAU+0.3;c.save();c.translate(s.x+0.15*k,s.y-4.2*k);c.rotate(a);E(c,0.9*k,0.15*k,1*k,0.22*k,tone(i%2?'#6fa45a':'#86b96a',1,fog));c.restore();}return;}
  L(c,s.x,s.y,s.x,s.y-1.4*k,tone('#a97b55',1,fog),Math.max(1,0.22*k));
  if(t.kind==='bush'){E(c,s.x,s.y-1.2*k,1.3*k,1*k,tone('#7fb06a',1,fog));E(c,s.x-0.4*k,s.y-1.5*k,0.7*k,0.6*k,tone('#94c486',1,fog));return;}
  E(c,s.x,s.y-2.4*k,1.5*k,1.4*k,tone('#86b875',1,fog));E(c,s.x-0.5*k,s.y-2.9*k,0.8*k,0.7*k,tone('#a3cd92',1,fog));E(c,s.x+0.6*k,s.y-2.2*k,0.7*k,0.6*k,tone('#78aa68',1,fog));
}
function sunflower(c,s,sz,t){const k=s.k*sz;if(k<2)return;const sw=Math.sin(t*1.3+s.x)*0.04*k;L(c,s.x,s.y,s.x+sw,s.y-1.1*k,'#7fae63',Math.max(1,0.04*k));
  for(let i=0;i<8;i++){const a=i*TAU/8;E(c,s.x+sw+Math.cos(a)*0.11*k,s.y-1.1*k+Math.sin(a)*0.11*k,0.06*k,0.06*k,'#f6c847');}E(c,s.x+sw,s.y-1.1*k,0.07*k,0.07*k,'#9a6a45');}
function post(c,V,x,z,all,i){
  const fog=0.1;line3(c,V,[x,0,z],[x,1,z],tone('#c9a27f',1,fog),0.09);
  const n=all[i+1]||null;if(!n)return;
  // Rails to the next post along the same side.
  if((Math.abs(n[0]-x)<0.01||Math.abs(n[1]-z)<0.01)&&Math.hypot(n[0]-x,n[1]-z)<2.3){line3(c,V,[x,0.75,z],[n[0],0.75,n[1]],tone('#ecd0a8',1,fog),0.06);line3(c,V,[x,0.4,z],[n[0],0.4,n[1]],tone('#ecd0a8',1,fog),0.06);}
}
function run(c,V,pts){for(let i=0;i<pts.length;i++){const a=pts[i],b=pts[(i+1)%pts.length];if(i===3)continue;line3(c,V,[a[0],0,a[1]],[a[0],0.8,a[1]],'#a98d6c',0.05);line3(c,V,[a[0],0.8,a[1]],[b[0],0.8,b[1]],'#b89c7c',0.03);line3(c,V,[a[0],0.4,a[1]],[b[0],0.4,b[1]],'#cdbb9f',0.02);}}
function tank(c,s,dry){const k=s.k;if(k<1)return;const x=s.x,y=s.y-1.5*k,w=0.55*k,h=1.15*k;
  R(c,x-w,y-h,w*2,h,'#dfe5e8',w*0.3,'#9aa3a6',Math.max(1,0.02*k));E(c,x,y-h,w,w*0.25,'#eef2f4');
  // Level window: water you can see, or an empty tank with a red mark when the pump station is cut.
  const lw=0.12*k,lh=0.85*h;R(c,x-lw/2,y-h*0.92,lw,lh,'#ffffff',lw/2,'#9aa3a6',1);
  const lvl=dry?0.06:0.82;R(c,x-lw/2+1,y-h*0.92+lh*(1-lvl),lw-2,lh*lvl,dry?'#e7a593':'#7fb7d6',lw/2);
  if(dry){L(c,x-w*0.5,y-h*0.6,x+w*0.5,y-h*0.2,'#c0533f',Math.max(2,0.05*k));L(c,x+w*0.5,y-h*0.6,x-w*0.5,y-h*0.2,'#c0533f',Math.max(2,0.05*k));}
  L(c,x+w,y-0.2*k,x+w+0.3*k,y+1.3*k,'#9aa3a6',Math.max(1,0.04*k));}
function well(c,s){const k=s.k;if(k<1)return;const x=s.x,y=s.y;E(c,x,y,0.75*k,0.22*k,'#00000022');R(c,x-0.6*k,y-0.7*k,1.2*k,0.7*k,'#c8c2b4',0.12*k,'#9a9384',1);E(c,x,y-0.7*k,0.6*k,0.16*k,'#5d7f8f');
  L(c,x-0.55*k,y-0.7*k,x-0.55*k,y-1.6*k,'#a97b55',Math.max(1,0.07*k));L(c,x+0.55*k,y-0.7*k,x+0.55*k,y-1.6*k,'#a97b55',Math.max(1,0.07*k));
  P(c,[[x-0.8*k,y-1.55*k],[x,y-1.95*k],[x+0.8*k,y-1.55*k]],'#d9786a');L(c,x-0.5*k,y-1.3*k,x+0.5*k,y-1.3*k,'#8a6a55',Math.max(1,0.04*k));R(c,x-0.08*k,y-1.3*k,0.16*k,0.25*k,'#9fb5bf',0.03*k);}
function hen(c,s,h,t,sad){const k=s.k*0.0105;if(k<0.08)return;const peck=sad?0:Math.max(0,Math.sin(t*2.2+h.i*1.7))**8,bob=Math.sin(t*3+h.i)*0.8;
  c.save();c.translate(s.x,s.y);c.scale(h.face*k,k);E(c,0,1,15,4,'#5c4a3a22');L(c,-4,-6,-4,0,'#e3a24a',2);L(c,4,-6,4,0,'#e3a24a',2);
  P(c,[[-12,-16+bob],[-22,-30+bob],[-17,-14+bob]],'#f1e6d4');E(c,0,-14+bob,16,12,'#fffaf0');E(c,-3,-14+bob,9,6,'#efe3cf');
  const hy=-27+bob+peck*10+(sad?6:0),hx=10+peck*4;E(c,hx,hy,8,8,'#fffaf0');E(c,hx,hy-8,4,3.5,'#e5806e');E(c,hx-4,hy-7,3,3,'#e5806e');
  P(c,[[hx+7,hy-1],[hx+13,hy+1],[hx+7,hy+3]],'#f2b84b');E(c,hx+6,hy+6,2,3,'#e5806e');E(c,hx+3,hy-1,1.5,sad?0.6:1.8,'#5a4337');c.restore();}
function hens(dt){
  const n=Math.min(10,farm().coop?.hens??0);
  while(W.hens.length<n){const i=W.hens.length,r=seeded(i+3);W.hens.push({i,x:-6.6+r()*2.6,z:16+r()*2.6,tx:0,tz:0,wait:r()*3,face:1});}
  W.hens.length=n;
  const slow=(farm().coop?.mood??80)<35?0.4:1;
  for(const h of W.hens){h.wait-=dt;if(h.wait>0)continue;
    if(!h.tx){const r=Math.random;h.tx=-6.7+r()*2.8;h.tz=15.9+r()*2.8;}
    const dx=h.tx-h.x,dz=h.tz-h.z,d=Math.hypot(dx,dz),s=0.5*slow*dt;
    if(d<s){h.tx=0;h.wait=1+Math.random()*3;}else{h.x+=dx/d*s;h.z+=dz/d*s;h.face=dx>=0?1:-1;}}
}
function eggs(c,V,n){const shown=Math.min(10,n);for(let i=0;i<shown;i++){const s=spot(V,-10.65+(i%5)*0.19,0.97,15.9-(i>4?0.12:0));if(s)E(c,s.x,s.y-0.05*s.k,0.06*s.k,0.08*s.k,i<(farm().coop?.stale||0)?'#efe0c4':'#fffaf0');}}
/** The packing table: the crate of this order (carton or paper bag), what is in it, its label. */
function crate(c,V,t,d){
  const known=t&&t.known,items=known?t.crate||[]:[],carton=known?t.needs?.kind==='contract':true;
  const m=box(-7.95,-7.25,0.88,carton?1.2:1.28,-0.25,0.25,carton?'#d8b07a':'#e9d6ae');drawMesh(c,V,m);
  let n=0;for(const e of items)for(let i=0;i<Math.min(6,e.qty)&&n<12;i++,n++){const s=spot(V,-7.85+(n%4)*0.16,carton?1.25:1.32,-0.15+Math.floor(n/4)*0.14);if(s){const col=e.crop==='egg'?'#fffaf0':e.crop==='tomato'?'#e2533c':e.crop==='cucumber'?'#3f8a3a':'#7cbf55';E(c,s.x,s.y,0.07*s.k,0.06*s.k,col);}}
  if(known&&t.label){const s=spot(V,-7.6,1.05,-0.27);if(s)R(c,s.x-0.14*s.k,s.y-0.08*s.k,0.28*s.k,0.16*s.k,t.label==='organic'?'#9fd18a':'#ffffff',0.03*s.k,'#7b7f66',1);}
  // Lots waiting in the cold room: small stacked boxes by its door.
  const lots=(d.cold||[]).slice(0,6);lots.forEach((l,i)=>{const b=box(-9.5+(i%3)*0.36,-9.18+(i%3)*0.36,Math.floor(i/3)*0.3,0.28+Math.floor(i/3)*0.3,-1.15,-0.85,l.crop==='egg'?'#f3e7cf':'#c9d8b6');drawMesh(c,V,b);});
}
/** The farm's scooter by the yard; the order's crate rides on its rack once something is packed. */
function bike(c,V,t){
  const z0=-2.15,z1=-1.85,parts=[box(-5.75,-4.35,0.25,0.52,z0,z1,'#e66f5c','#f08a78'),box(-5.45,-4.75,0.52,0.66,z0+0.02,z1-0.02,'#5b4a44'),box(-4.48,-4.33,0.25,0.98,z0,z1,'#e66f5c'),
    box(-5.95,-5.55,0,0.4,-2.06,-1.94,'#3f4448'),box(-4.55,-4.15,0,0.4,-2.06,-1.94,'#3f4448'),box(-4.32,-4.02,0.62,0.86,z0,z1,'#c9a066')];
  if(t?.known&&(t.crate||[]).length)parts.push(box(-6,-5.4,0.66,0.98,-2.25,-1.75,t.needs?.kind==='contract'?'#d8b07a':'#e9d6ae'));
  parts.sort((a,b)=>cam3(V,...b.o)[2]-cam3(V,...a.o)[2]);for(const p of parts)drawMesh(c,V,p);
  line3(c,V,[-4.36,1.05,-2.35],[-4.36,1.05,-1.65],'#4b4f52',0.04);
}
/** Signs on posts: the beds (crop and when it is ready), the coop, the shed, the cold room, the weather board,
 * the market price board on the truck, the order on the packing table. Text is drawn once into a small canvas. */
function signs(d,t){
  const out=[],m=W.x.cc.moisture||{low:40,dry:25,high:80};
  for(const p of d.plots||[]){const b=BEDS[p.id];if(!b)continue;const c=p.crop?cropOf(p.crop):null;
    const [line,tone_]=bedLine(p,m);
    out.push({x:b[0]-1.25,y:0.78,z:b[1]-0.98,w:0.95,h:0.5,key:`b|${p.id}|${c?.id}|${line}|${Math.round(p.moisture/10)}`,paint:g=>board(g,[`${p.id}  ${c?c.emoji+' '+c.name:'🟫 '+tr('Luống trống')}`,line],tone_,p.crop?p.moisture:null,m)});
    const bub=bubble(p,m);if(bub)out.push({x:b[0],y:1.55,z:b[1],bubble:bub});}
  out.push({x:-9,y:2.35,z:15.95,w:1.5,h:0.42,key:'coop',paint:g=>plate(g,'CHUỒNG GÀ')});
  out.push({x:9.25,y:2.25,z:15.95,w:1.5,h:0.42,key:'shed',paint:g=>plate(g,'NHÀ KHO')});
  out.push({x:-11.1,y:2.45,z:-1.25,w:1.4,h:0.42,key:'cold',paint:g=>plate(g,'KHO MÁT')});
  const w=d.weather||{},f=(d.outlook||[])[0]||d.forecast||{};
  out.push({x:2.8,y:1.35,z:-4.2,w:1.4,h:0.85,key:`sky|${w.id}|${f.id}`,paint:g=>board(g,[`${tr('Hôm nay')}: ${w.emoji||''} ${tr(w.name||'')}`,`${tr('Mai')}: ${f.emoji||''} ${tr(f.name||'')}`],'',null,null,true)});
  const mk=d.market;if(mk?.rows){const rows=mk.rows.filter(r=>(d.cold||[]).some(l=>l.crop===r.crop)).concat(mk.rows).slice(0,3);
    out.push({x:9.6,y:1.95,z:-4.3,w:1.5,h:0.9,key:`mk|${rows.map(r=>r.crop+r.index+r.sold).join()}`,paint:g=>board(g,[tr('Chợ đầu mối'),...rows.map(r=>`${cropOf(r.crop).emoji} ${(r.next_a/10).toLocaleString('vi-VN',{maximumFractionDigits:1})} xu ${r.index>=125?'↑':r.index<=80?'↓':'·'}`)],'',null,null,true)});}
  if(t){const who=W.x.npc(t.npc).display_name,items=t.known?Object.entries(t.needs.items).map(([k,q])=>`${cropOf(k).emoji}${(t.crate||[]).filter(e=>e.crop===k).reduce((a,e)=>a+e.qty,0)}/${q}`).join(' '):'📞';
    out.push({x:-7.6,y:1.75,z:0.62,w:1.3,h:0.62,key:`ord|${who}|${items}|${t.label}`,paint:g=>board(g,[who,items],t.label?'good':'',null,null,true)});}
  return out;
}
function bedLine(p,m){
  if(!p.crop)return [p.compost?tr('Đã bón lót · gieo được'):tr('Gieo được'),''];
  if(p.stage==='rotten')return [tr('Hỏng · dọn luống'),'bad'];
  if(p.safe_in)return [tr(`Cách ly ${p.safe_in} nhịp`),'bad'];
  if(p.moisture<m.low)return [tr('Khát nước'),'water'];
  if(p.stage==='ripe')return [tr('Thu được!'),'good'];
  if(p.stage==='over')return [tr('Quá lứa'),'warn'];
  const n=p.eta;return [n==null?'':n===0?tr('Chín hôm nay'):n===1?tr('Chín mai'):tr(`Chín sau ${n} ngày`),''];
}
function bubble(p,m){
  if(!p.crop)return null;
  if(p.moisture<m.low)return '💧';
  if(p.stage==='ripe'||p.stage==='over')return '🧺';
  if((p.seen||0)>0&&p.scouted_today)return '🐛';
  if(p.weeds>=2)return '🌾';
  return null;
}
const CANVAS=new Map();
function tex(key,w,h,paint){let g=CANVAS.get(key);if(!g){g=document.createElement('canvas');g.width=w;g.height=h;paint(g.getContext('2d'),w,h);if(CANVAS.size>80)CANVAS.clear();CANVAS.set(key,g);}return g;}
const FONT='"Trebuchet MS", "Segoe UI", sans-serif';
function plate(g,text){const w=g.canvas.width,h=g.canvas.height;R(g,2,2,w-4,h-4,'#fff6e4',14,'#c9a27f',3);g.font=`800 ${Math.round(h*0.48)}px ${FONT}`;g.textAlign='center';g.textBaseline='middle';g.fillStyle='#6b4c34';
  const s=tr(text),wd=g.measureText(s).width;if(wd>w-20){g.font=`800 ${Math.round(h*0.48*(w-20)/wd)}px ${FONT}`;}g.fillText(s,w/2,h/2+2);}
/** A small board: lines of text, an optional tone for the second line and a water bar along the bottom. */
function board(g,lines,tn,moist,m,wide=false){
  const w=g.canvas.width,h=g.canvas.height;R(g,3,3,w-6,h-6,'#fff6e4',16,'#c9a27f',4);
  const col={good:'#3f7d36',bad:'#b4432f',warn:'#a86b18',water:'#2f6d94'}[tn]||'#6b4c34';
  const n=lines.length,lh=(h-(moist!=null?26:14))/n;
  lines.forEach((s,i)=>{const big=i===0&&!wide?0.52:0.5;let size=Math.round(lh*big);g.font=`${i===0?800:700} ${size}px ${FONT}`;
    const wd=g.measureText(s).width;if(wd>w-24){size=Math.max(10,Math.floor(size*(w-24)/wd));g.font=`${i===0?800:700} ${size}px ${FONT}`;}
    g.fillStyle=i===1?col:'#5d4330';g.textAlign='center';g.textBaseline='middle';g.fillText(s,w/2,10+lh*(i+0.5));});
  if(moist!=null){const x=18,y=h-20,bw=w-36;R(g,x,y,bw,9,'#e8dcc4',5);R(g,x,y,Math.max(9,bw*clamp(moist,0,100)/100),9,moist<m.low?'#e0a35a':moist>m.high?'#5c7fa0':'#6fb0d8',5);
    for(const v of [m.low,m.high])R(g,x+bw*v/100-1,y-2,2,13,'#7b6a55',1);}
}
function sign(c,V,s){
  if(s.bubble){const p=spot(V,s.x,s.y+Math.sin(W.t*2+s.x)*0.05,s.z);if(!p||p.d>30)return;const r=clamp(0.2*p.k,11,26);E(c,p.x,p.y,r,r,'#ffffffee');c.font=`${Math.round(r*1.15)}px ${FONT}`;c.textAlign='center';c.textBaseline='middle';c.fillText(s.bubble,p.x,p.y+1);return;}
  const p=spot(V,s.x,s.y,s.z);if(!p||p.d<0.9)return;
  const sw=s.w*p.k,sh=s.h*p.k;if(sw<6)return;
  // A sign right in front of the eye fades out instead of filling the view.
  const near=clamp((p.d-0.9)/1.1,0,1);if(near<1)c.globalAlpha=near;
  L(c,p.x,p.y+sh/2,p.x,p.y+(s.y)*p.k,tone('#a97b55',1,haze(p.d)),Math.max(1,0.06*p.k));
  const img=tex(s.key,Math.round(s.w*200),Math.round(s.h*200),g=>s.paint(g));
  c.globalAlpha=Math.min(near,1-haze(p.d)*0.6);c.drawImage(img,p.x-sw/2,p.y-sh/2,sw,sh);c.globalAlpha=1;
}
function cat(c,s,t){const k=s.k*0.012;if(k<0.1)return;c.save();c.translate(s.x,s.y);c.scale(k,k);E(c,0,0,26,14,'#f2d6b0');E(c,-18,-14,13,12,'#f2d6b0');P(c,[[-28,-22],[-24,-34],[-18,-24]],'#e2b892');P(c,[[-16,-24],[-10,-34],[-8,-22]],'#e2b892');
  const z=Math.sin(t*1.5)>0;L(c,-23,-15,-19,-15,'#805a49',1.5);L(c,-15,-15,-11,-15,'#805a49',1.5);if(z){c.font=`700 12px ${FONT}`;c.fillStyle='#8a6a55';c.fillText('z',10,-30);}
  c.beginPath();c.moveTo(24,0);c.quadraticCurveTo(40,-4,34,-18);c.strokeStyle='#e2b892';c.lineWidth=5;c.stroke();c.restore();}
function bees(c,V){for(let i=0;i<7;i++){const x=Math.sin(W.t*1.3+i*2)*6,z=10+Math.cos(W.t*0.9+i)*3,s=spot(V,x,1+Math.sin(W.t*5+i)*0.2,z);if(!s)continue;const r=Math.max(1.5,0.04*s.k);E(c,s.x,s.y,r,r*0.8,'#f2c84b');L(c,s.x-r*0.3,s.y-r*0.8,s.x-r*0.3,s.y+r*0.8,'#5a4337',Math.max(1,r*0.3));E(c,s.x,s.y-r,r*0.7,r*0.4,'#ffffffaa');}}
function marker(c,V,x,z,id){
  const tall=id.startsWith('P')?1.5:id==='coop'||id==='shed'?3.6:2.4;
  const p=spot(V,x,tall+0.25+Math.sin(W.t*3)*0.12,z);if(!p)return;const r=clamp(0.22*p.k,9,22);
  P(c,[[p.x-r,p.y-r],[p.x+r,p.y-r],[p.x,p.y+r*0.6]],'#f2a93b');E(c,p.x,p.y-r*1.35,r*0.75,r*0.75,'#f2a93b');E(c,p.x,p.y-r*1.35,r*0.38,r*0.38,'#fff6e4');
}
function rain(c){c.strokeStyle='#ffffff88';c.lineWidth=1;c.beginPath();for(let i=0;i<70;i++){const x=(i*97+W.t*40)%W.w,y=(i*53+W.t*520)%W.h;c.moveTo(x,y);c.lineTo(x-3,y+12);}c.stroke();}
function leaves(c){for(let i=0;i<8;i++){const x=(i*131+W.t*90)%(W.w+40)-20,y=(i*71+Math.sin(W.t+i)*30+W.t*15)%W.h;c.save();c.translate(x,y);c.rotate(W.t*3+i);E(c,0,0,5,2.4,i%2?'#9cc56c':'#c6d77a');c.restore();}}
function effect(c,V,f){
  const k=f.t/f.life;
  if(f.k==='water'||f.k==='grain'){for(let i=0;i<14;i++){const a=i*0.9,dx=Math.sin(a)*1.2*((i%5)/5),dz=Math.cos(a)*0.5*((i%3)/3),y=1.2-((k*2+i*0.07)%1)*1.1;const s=spot(V,f.x+dx,y,f.z+dz);if(s)E(c,s.x,s.y,Math.max(1.5,0.03*s.k),Math.max(2,0.05*s.k),f.k==='water'?'#7fb7d6cc':'#e8c86acc');}return;}
  if(f.k==='pop'){const s=spot(V,f.x,1+k*1.2,f.z);if(!s)return;c.globalAlpha=1-k;c.font=`${Math.round(clamp(0.45*s.k,18,44))}px ${FONT}`;c.textAlign='center';c.textBaseline='middle';c.fillText(f.e||'✨',s.x,s.y);c.globalAlpha=1;return;}
  if(f.k==='weed'||f.k==='seed'||f.k==='feed'){for(let i=0;i<8;i++){const s=spot(V,f.x-1.2+i*0.35,0.4+Math.sin(k*3+i)*0.3+k*0.6,f.z+(i%2?0.3:-0.3));if(s)E(c,s.x,s.y,Math.max(1.5,0.03*s.k),Math.max(1.5,0.03*s.k),f.k==='weed'?'#8fa63c':f.k==='seed'?'#c9a066':'#6b4a33');}}
}

/* ------------------------------------------------------------------ people */
const F_=()=>{try{return figure(W.x.state);}catch{return null;}};
function work(){const m=(W.x?.content?.catalogue||[]).find(c=>c.id==='farm');const col=/^#[0-9a-f]{6}$/i.test(m?.color||'')?m.color:'#5f8f3e';return {primary:col,dark:'#41612a'};}
/** You, from behind (third person): the look from the wardrobe, the farm's work clothes when they are on. */
function player(c,s){
  const F=F_();if(!F)return;const sc=s.k*1.62/140,me=W.me,step=me.moving?Math.sin(me.bob*1.6)*3:0,pal=work();
  const top=F.L.uniform?pal.primary:F.topC||F.classic,sk=F.skin;
  c.save();c.translate(s.x,s.y);c.scale(sc,sc);
  paintLegs(c,F,step);
  R(c,-23,-52,46,36,top,15);E(c,-25,-36+step*0.6,8,14,sk.hand);E(c,25,-36-step*0.6,8,14,sk.hand);
  if(F.L.uniform){if(F.g==='male'){R(c,-15,-34,30,14,pal.dark,6);L(c,-11,-34,-14,-52,pal.dark,4);L(c,11,-34,14,-52,pal.dark,4);}
    else{L(c,-15,-49,12,-27,'#fff7e8',3);L(c,15,-49,-12,-27,'#fff7e8',3);E(c,-6,-24,6,3.5,'#fff7e8');E(c,6,-24,6,3.5,'#fff7e8');}}
  E(c,-29,-74,5,8,sk.ear);E(c,29,-74,5,8,sk.ear);
  const hair=F.hair,h=F.L.hair;
  if(F.long)R(c,-28,-92,56,64,hair,22);else if(h==='toc_bob')R(c,-31,-99,62,46,hair,20);
  E(c,0,-84,32,35,hair);
  if(h==='toc_duoi_ngua'){E(c,0,-66,8,18,hair);E(c,0,-84,4,4,'#e0708a');}
  else if(h==='toc_bui')E(c,0,-113,16,14,hair);
  else if(h==='toc_xoan')for(const [x,y,r] of [[-24,-100,13],[24,-100,13],[0,-112,14],[-30,-80,9],[30,-80,9]])E(c,x,y,r,r,hair);
  if(['non_la','mu_len','no_toc','tui_cheo'].includes(F.L.acc))paintAcc(c,F);
  if(W.me.tool==='can')can(c,30,-30,0.9);else if(W.me.tool==='basket')basket(c,-30,-26,0.7);
  c.restore();
}
/** Someone met in the world (front view, the scene's style). */
function person(c,s,o){
  const sc=s.k*1.6/140;if(sc<0.02)return;c.save();c.translate(s.x,s.y);c.scale(sc,sc);
  E(c,0,0,26,8,'#4a3b2a22');R(c,-19,-20,15,20,'#6d6a7a',5);R(c,4,-20,15,20,'#6d6a7a',5);R(c,-21,-7,19,10,'#5b4a44',5);R(c,3,-7,19,10,'#5b4a44',5);
  R(c,-23,-52,46,36,o.top,15);E(c,-25,-36,8,14,o.skin);
  if(o.wave){const a=Math.sin(W.t*6)*6;L(c,20,-46,34+a,-82,o.top,11);E(c,34+a,-84,8,8,o.skin);}else E(c,25,-36,8,14,o.skin);
  E(c,0,-84,33,35,o.hair);E(c,-29,-71,5,8,o.skin);E(c,29,-71,5,8,o.skin);E(c,0,-77,29,28,o.skin);
  c.beginPath();c.moveTo(-30,-88);c.bezierCurveTo(-33,-119,19,-120,31,-90);c.quadraticCurveTo(19,-93,7,-105);c.quadraticCurveTo(5,-88,-12,-84);c.quadraticCurveTo(-17,-91,-16,-101);c.quadraticCurveTo(-21,-89,-30,-88);c.fillStyle=o.hair;c.fill();
  for(const ex of [-11,11]){E(c,ex,-78,5,7,'#705140');E(c,ex-1.3,-80.4,1.8,2.3,'#fffdf3');}
  E(c,-20,-67,7,4,'#efa7a0');E(c,20,-67,7,4,'#efa7a0');c.beginPath();c.arc(0,-66,4,0,Math.PI);c.strokeStyle='#b17c69';c.lineWidth=1.6;c.stroke();
  if(o.hat){P(c,[[-46,-103],[0,-140],[46,-103]],'#f3dfa8');E(c,0,-103,46,5,'#e2c784');}
  c.restore();
}

/* ------------------------------------------------------------------ first person: hands and tools */
function overlays(c,V,wx){
  if(W.ride){handlebars(c);rideHud(c);}
  else if(W.cam==='fp')hands(c);
  joy(c);
  if(W.hint)tip(c,tr('Đi tới luống rau để chăm'),W.h*0.24);
  const h=W.fx.find(f=>f.k==='honk');if(h)tip(c,tr('Bíp bíp!'),W.h*0.3);
}
/** Which tool your hands hold: it follows the place you are at. */
function toolFor(){
  const n=W.near,d=farm();if(!n)return null;
  if(BEDS[n]){const p=(d.plots||[]).find(q=>q.id===n),m=W.x.cc.moisture||{low:40};if(!p?.crop)return 'seeds';if(p.stage==='ripe'||p.stage==='over')return 'basket';if(p.moisture<m.low)return 'can';return 'hoe';}
  if(n==='tank')return 'can';if(n==='coop'||n==='pack'||n==='truck')return 'basket';return null;
}
function hands(c){
  const tool=W.me.tool=toolFor();if(!tool)return;
  const F=F_(),skin=F?.skin?.hand||'#f5d5ba',sleeve=F?.L?.uniform?work().primary:F?.topC||F?.classic||'#8a9a74';
  const w=W.w,h=W.h,u=Math.min(w,h*0.8)/390,bob=Math.sin(W.me.bob)*6*u*W.me.moving,pour=W.fx.find(f=>f.k==='water');
  c.save();c.translate(0,bob);
  const arm=(x0,y0,x1,y1)=>{L(c,x0,y0,x1,y1,sleeve,34*u);E(c,x1,y1,15*u,17*u,skin);};
  if(tool==='can'){const tilt=pour?Math.min(1,pour.t*3)*0.5:0;arm(w+20*u,h+30*u,w-110*u,h-70*u);
    c.save();c.translate(w-95*u,h-95*u);c.rotate(-tilt);can(c,0,0,2.2*u*1.6);c.restore();
    if(pour)for(let i=0;i<10;i++){const k=(pour.t*3+i*0.1)%1;E(c,w-230*u-k*40*u-i*3*u,h-150*u+k*90*u,3*u,5*u,'#7fb7d6cc');}}
  else if(tool==='basket'){arm(-20*u,h+30*u,w*0.5-70*u,h-60*u);arm(w+20*u,h+30*u,w*0.5+70*u,h-60*u);basket(c,w*0.5,h-40*u,2.4*u);}
  else if(tool==='seeds'){arm(-20*u,h+30*u,90*u,h-80*u);R(c,62*u,h-150*u,64*u,78*u,'#e9d6ae',10*u,'#b98a5c',2);c.font=`${Math.round(30*u)}px ${FONT}`;c.textAlign='center';c.fillText('🌱',94*u,h-108*u);E(c,90*u,h-80*u,15*u,17*u,skin);}
  else{arm(w+20*u,h+30*u,w-90*u,h-60*u);L(c,w-60*u,h+20*u,w-190*u,h-220*u,'#b08a5e',12*u);P(c,[[w-210*u,h-240*u],[w-160*u,h-250*u],[w-150*u,h-215*u],[w-200*u,h-212*u]],'#9aa3a6');E(c,w-90*u,h-60*u,15*u,17*u,skin);}
  c.restore();
}
function can(c,x,y,s){c.save();c.translate(x,y);c.scale(s,s);R(c,-12,-14,24,22,'#6fae8f',5,'#4f8a6f',1.5);L(c,10,-6,26,-20,'#6fae8f',4);E(c,27,-21,4,3,'#4f8a6f');c.beginPath();c.arc(-2,-14,9,Math.PI,0);c.strokeStyle='#4f8a6f';c.lineWidth=3;c.stroke();c.restore();}
function basket(c,x,y,s){c.save();c.translate(x,y);c.scale(s,s);c.beginPath();c.arc(0,-18,24,Math.PI,0);c.strokeStyle='#a97b55';c.lineWidth=4;c.stroke();
  P(c,[[-30,-18],[30,-18],[24,10],[-24,10]],'#d9b27a');for(let i=-2;i<=2;i++)L(c,i*11,-16,i*9,8,'#b98a5c',1.5);L(c,-28,-8,28,-8,'#b98a5c',1.5);
  const t=task(),items=t?.crate||[];let n=0;for(const e of items)for(let i=0;i<Math.min(3,e.qty)&&n<6;i++,n++)E(c,-18+n*7.5,-20-(n%2)*4,6,5,e.crop==='egg'?'#fffaf0':e.crop==='tomato'?'#e2533c':'#7cbf55');
  c.restore();}
function joy(c){
  if(!W.joy&&(W.ride||!coarse()))return;
  const R_=joyR(),j=W.joy,x=j?j.ox:R_+18,y=j?j.oy:W.h-R_-18;
  E(c,x,y,R_,R_,j?'#ffffff40':'#ffffff26');c.strokeStyle='#ffffff99';c.lineWidth=2;c.beginPath();c.arc(x,y,R_,0,TAU);c.stroke();
  E(c,x+(j?j.dx*R_:0),y+(j?j.dy*R_:0),R_*0.42,R_*0.42,j?'#fff6e4ee':'#fff6e4aa');
}
function tip(c,text,y=W.h*0.24){c.font=`700 ${W.w<480?15:17}px ${FONT}`;const w=c.measureText(text).width+28;R(c,W.w/2-w/2,y-18,w,36,'#fff6e4ee',18,'#c9a27f',1.5);c.fillStyle='#5d4330';c.textAlign='center';c.textBaseline='middle';c.fillText(text,W.w/2,y+1);}

/* ------------------------------------------------------------------ the ride to the buyer */
const ROAD_LEN=140,ROAD_W=2.3;
const roadX=z=>2.4*Math.sin(z/26)+1.2*Math.sin(z/11+1)-1.2*Math.sin(1);
function rideWorld(o){
  const r=seeded(([...String(o.task||'')].reduce((a,ch)=>a+ch.charCodeAt(0),0))||5),D={palms:[],poles:[],houses:[],paddies:[]};
  for(let z=6;z<ROAD_LEN+30;z+=7+r()*6){const side=r()<0.5?-1:1;D.palms.push({x:roadX(z)+side*(3.4+r()*5),z,s:0.9+r()*0.4,kind:r()<0.55?'palm':r()<0.5?'round':'bush'});}
  for(let z=10;z<ROAD_LEN;z+=24)D.poles.push({x:roadX(z)-3.1,z});
  for(let z=0;z<ROAD_LEN+40;z+=12)for(const side of [-1,1]){const x=roadX(z+6)+side*(ROAD_W+1.4);D.paddies.push({x0:side>0?x:x-11,x1:side>0?x+11:x,z0:z,z1:z+11.4,col:['#a9d27a','#9cc86a','#c4cf62','#a8cfc6'][Math.floor(r()*4)]});}
  for(const [z,side,col] of [[40,-1,'#f6e7cf'],[96,1,'#f1dcc8'],[128,-1,'#e9f0dc']]){const x=roadX(z)+side*6.2;D.houses.push(house(x-1.6,x+1.6,z-1.4,z+1.4,2.2,1,col,'#c9675a'));}
  const ex=roadX(ROAD_LEN)+5.4;D.shop=house(ex-2.2,ex+2.2,ROAD_LEN-2,ROAD_LEN+2,2.6,1.1,'#fff3dd','#d9786a');
  decal(D.shop,2,[ex-2.21,0,ROAD_LEN-0.9,ex-2.21,0,ROAD_LEN+0.9,ex-2.21,1.9,ROAD_LEN+0.9,ex-2.21,1.9,ROAD_LEN-0.9],'#c9855f');
  D.buffalo={z:ROAD_LEN*0.62,x:0,dir:1};
  return D;
}
function rideStep(dt){
  const r=W.ride;r.t+=dt;
  if(r.state==='load'){if(r.t>0.7){r.state='ride';r.t=0;}return;}
  if(r.state==='done'){if(r.t>1.6)rideEnd();return;}
  if(r.state==='arrive'||r.state==='hand')return;
  let fwd=0,steer=0;const k=W.keys;
  if(W.joy){fwd=-W.joy.dy;steer=W.joy.dx;}
  if(k.has('f'))fwd=1;if(k.has('b'))fwd=-1;if(k.has('l'))steer=-1;if(k.has('r'))steer=1;
  const left=ROAD_LEN-r.z,want=left<12?Math.max(0,left*0.9):fwd>0.2?14:fwd<-0.2?3.5:10;
  r.v+=clamp(want-r.v,-9*dt,4*dt);
  // Forgiving: with no hand on the bars the scooter keeps to the middle of the road.
  const ahead=Math.atan2(roadX(r.z+4)-roadX(r.z),4),off=r.x-roadX(r.z);
  if(Math.abs(steer)>0.1)r.yaw=wrap(r.yaw+steer*1.3*dt*clamp(r.v/8,0.4,1.3));
  else r.yaw+=(ahead-clamp(off*0.18,-0.35,0.35)-r.yaw)*Math.min(1,dt*1.8);
  r.yaw=clamp(wrap(r.yaw),-1,1);r.steer+=(steer-r.steer)*Math.min(1,dt*6);
  r.x+=Math.sin(r.yaw)*r.v*dt;r.z+=Math.cos(r.yaw)*r.v*dt;
  const o=r.x-roadX(r.z);if(Math.abs(o)>ROAD_W+0.4)r.v=Math.max(3,r.v-6*dt);
  if(Math.abs(o)>ROAD_W+2.2)r.x=roadX(r.z)+Math.sign(o)*(ROAD_W+2.2);
  // The buffalo takes its time across the road: you slow down, give it a beep, no harm done.
  const b=r.deco.buffalo;b.x+=b.dir*0.6*dt;if(Math.abs(b.x)>5)b.dir*=-1;
  const bx=roadX(b.z)+b.x;if(b.z-r.z>0&&b.z-r.z<9&&Math.abs(bx-r.x)<2.2){r.v=Math.min(r.v,2.2);if(!r.beep){r.beep=1;honk();}}
  if(r.z>=ROAD_LEN-1.6&&r.v<0.6){r.state='arrive';r.t=0;r.v=0;arrive();}
}
async function arrive(){
  const r=W.ride;
  if(!r)return;
  const mark=document.createElement('i');mark.className='fv-arrived';mark.hidden=true;W.el.append(mark);
  r.state='hand';W.hooks?.ride?.(W.x,{place:r.place,state:'hand'});
  let ok=null;try{ok=await W.hooks?.deliver?.(W.x,r.task);}catch{ok=null;}
  if(W.ride!==r)return;
  r.state='done';r.t=0;r.ok=!!ok;wake();
}
function rideEnd(){
  W.ride=null;W.el.querySelector('.fv-arrived')?.remove();
  W.me.x=-5;W.me.z=-3.4;W.me.yaw=0;W.near=null;sense(true);
  W.hooks?.ride?.(W.x,null);wake();
}
export function cancelRide(){if(W.ride){W.ride=null;W.el?.querySelector('.fv-arrived')?.remove();}}
function rideScene(c,V,wx){
  const D=W.ride.deco,Q=[],z0=W.ride.z-4,z1=W.ride.z+120;
  for(const p of D.paddies){if(p.z1<z0||p.z0>z1)continue;poly(c,V,[p.x0,0,p.z0,p.x1,0,p.z0,p.x1,0,p.z1,p.x0,0,p.z1],tone(p.col,1,haze(((p.z0+p.z1)/2)-W.ride.z)));}
  // The canal under the little bridge, then the road (concrete, light), drawn in short pieces along its bends.
  poly(c,V,[-40,0.01,92,40,0.01,92,40,0.01,96,-40,0.01,96],tone('#7fb3c9',1,haze(94-W.ride.z)));
  for(let z=Math.max(-4,Math.floor(z0/3)*3);z<Math.min(ROAD_LEN+24,z1);z+=3){const a=roadX(z),b=roadX(z+3),f=haze(z-W.ride.z);
    poly(c,V,[a-ROAD_W-0.6,0.015,z,a+ROAD_W+0.6,0.015,z,b+ROAD_W+0.6,0.015,z+3.05,b-ROAD_W-0.6,0.015,z+3.05],tone('#cfc29a',1,f));
    poly(c,V,[a-ROAD_W,0.02,z,a+ROAD_W,0.02,z,b+ROAD_W,0.02,z+3.05,b-ROAD_W,0.02,z+3.05],tone(z>=92&&z<96?'#d9cdb8':'#dcd8cc',1,f));}
  const stop=ROAD_LEN,sx=roadX(stop);poly(c,V,circle(sx,0.03,stop,1.6,12),'#f2a93baa');
  const add=(x,y,z,fn)=>{const p=cam3(V,x,y,z);if(p[2]>-2&&p[2]<130)Q.push([p[2],fn]);};
  for(const t of D.palms)add(t.x,1,t.z,()=>tree(c,V,t));
  for(const p of D.poles)add(p.x,3,p.z,()=>{line3(c,V,[p.x,0,p.z],[p.x,5,p.z],tone('#b9b3a8',1,haze(p.z-W.ride.z)),0.14);line3(c,V,[p.x,4.6,p.z],[p.x,4.6,p.z+24],'#55555588',0.015);});
  for(const m of D.houses)add(m.o[0],m.o[1],m.o[2],()=>drawMesh(c,V,m));
  for(const s of [-1,1])add(roadX(94)+s*(ROAD_W+0.2),0.6,94,()=>line3(c,V,[roadX(92)+s*(ROAD_W+0.2),0.7,92],[roadX(96)+s*(ROAD_W+0.2),0.7,96],'#c9a27f',0.08));
  add(D.shop.o[0],D.shop.o[1],D.shop.o[2],()=>drawMesh(c,V,D.shop));
  const sg=W.ride.sign;add(sx+3.6,2.9,stop-0.3,()=>sign(c,V,{x:sx+3.2,y:3.15,z:stop-2.1,w:2.4,h:0.6,key:'shop|'+sg,paint:g=>plate(g,sg)}));
  add(sx+2.4,0.8,stop+0.2,()=>{const q=spot(V,sx+2.6,0,stop+0.4);if(q)person(c,q,{...W.ride.look,wave:true});});
  add(-1,2,-1,()=>{const q=spot(V,roadX(14)-4.6,0,14);if(q)sign(c,V,{x:roadX(14)-4.2,y:1.4,z:14,w:1.8,h:0.6,key:'to|'+sg,paint:g=>board(g,[`→ ${sg}`,`${ROAD_LEN} m`],'',null,null,true)});});
  const b=D.buffalo;add(roadX(b.z)+b.x,1,b.z,()=>{const q=spot(V,roadX(b.z)+b.x,0,b.z);if(q)buffalo(c,q,b.dir);});
  Q.sort((a,b)=>b[0]-a[0]);for(const [,fn] of Q)fn();
  if(wx==='rain')rain(c);
}
function buffalo(c,s,dir){const k=s.k*0.011;if(k<0.05)return;c.save();c.translate(s.x,s.y);c.scale(dir*k,k);E(c,0,2,90,14,'#00000022');
  for(const x of [-50,-30,30,50])R(c,x-7,-50,14,52,'#5d5a5e',6);E(c,0,-70,70,38,'#6b676d');E(c,72,-92,26,22,'#6b676d');
  c.beginPath();c.arc(82,-118,26,Math.PI*1.1,Math.PI*1.9);c.strokeStyle='#e9e2d3';c.lineWidth=7;c.stroke();E(c,86,-94,3,3,'#2d2a2e');c.restore();}
function handlebars(c){
  const w=W.w,h=W.h,u=Math.min(w,h*0.8)/390,r=W.ride,tilt=(reduced()?0:-r.steer*0.08),F=F_(),skin=F?.skin?.hand||'#f5d5ba',sleeve=F?.L?.uniform?work().primary:F?.topC||F?.classic||'#8a9a74';
  c.save();c.translate(w/2,h+10*u);c.rotate(tilt);
  // The front basket with the order's produce, the speedometer, the bars, the mirrors, your hands.
  R(c,-70*u,-150*u,140*u,70*u,'#d9b27a',14*u,'#b98a5c',2);for(let i=-3;i<=3;i++)L(c,i*18*u,-146*u,i*16*u,-84*u,'#b98a5c',1.5);
  const items=(task()?.crate)||[];let n=0;for(const e of items)for(let i=0;i<Math.min(4,e.qty)&&n<9;i++,n++)E(c,(-50+n*12.5)*u,(-150-(n%2)*8)*u,10*u,8*u,e.crop==='egg'?'#fffaf0':e.crop==='tomato'?'#e2533c':e.crop==='cucumber'?'#3f8a3a':'#7cbf55');
  R(c,-150*u,-78*u,300*u,60*u,'#e66f5c',26*u);E(c,0,-60*u,34*u,30*u,'#fff6e4');c.strokeStyle='#5d4330';c.lineWidth=3*u;c.beginPath();const a=-Math.PI*0.9+clamp(r.v/14,0,1)*Math.PI*0.8;c.moveTo(0,-56*u);c.lineTo(Math.cos(a)*24*u,-56*u+Math.sin(a)*24*u);c.stroke();
  L(c,-190*u,-88*u,190*u,-88*u,'#4b4f52',14*u);for(const s of [-1,1]){L(c,s*150*u,-92*u,s*175*u,-170*u,'#4b4f52',5*u);E(c,s*178*u,-180*u,20*u,15*u,'#cfd8dc');E(c,s*178*u,-180*u,15*u,10*u,'#9fc3d6');
    L(c,s*260*u,40*u,s*195*u,-80*u,sleeve,36*u);E(c,s*192*u,-88*u,17*u,19*u,skin);}
  c.restore();
}
function rideHud(c){
  const r=W.ride,left=Math.max(0,Math.round(ROAD_LEN-r.z));
  const text=r.state==='done'?(r.ok?tr('Đã giao hàng!'):tr('Chưa giao được, quay về trại')):r.state==='hand'||r.state==='arrive'?tr('Đang giao hàng…'):`🏁 ${tr(r.sign)} · ${tr(`còn ${left} m`)}`;
  tip(c,text,W.h*0.08);
  const bw=Math.min(240,W.w-60),x=W.w/2-bw/2,y=W.h*0.08+24;R(c,x,y,bw,6,'#ffffff88',3);R(c,x,y,bw*clamp(r.z/ROAD_LEN,0,1),6,'#f2a93b',3);
  if(r.state==='load'){c.fillStyle=`rgba(255,246,228,${1-r.t/0.7})`;c.fillRect(0,0,W.w,W.h);}
  if(r.state==='done'){c.fillStyle=`rgba(255,246,228,${clamp((r.t-1)/0.6,0,1)})`;c.fillRect(0,0,W.w,W.h);}
}
