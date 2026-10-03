/** 🛵 Tự lái: the delivery career's ride, seen from the rider's seat (owner, 03/10: "tự điều khiển xe đi và ở góc
 * nhìn thứ nhất… thông tin trải ra thì dễ chơi và vui hơn"). Loaded by careers/delivery.js only while a leg is to be
 * ridden in Tự lái mode.
 *
 * The neighbourhood is the route map's 7×5 grid of junctions (content nodes x 0–6, y 0–4), one map block ("ô phố")
 * being B metres of street. Every stop on the map is a landmark on the corner next to its junction, its sign over the
 * door; the stop to ride to has its person waving on the pavement and a bobbing ▼ over them. Ordinary houses carry
 * their number on a blue plate by the gate, the junctions a street-name sign, some of them traffic lights; scooters
 * ride in their lane and stop at red, people walk the pavements. Rain on rain days, the light of the shift's hour.
 *
 * Nothing here is game state: stopping in front of a stop calls opts.arrive(node), which sends the same commands as
 * the tap flow ("Đi nhanh": dl_plan if needed, then dl_ride main road); the server prices the leg by its blocks as
 * always. A bump, the kerb or a red light only slow the scooter and say a word. Stopping at an ordinary house says
 * "Không phải nhà này"; nothing is sent.
 *
 * Drawn with the 2D canvas, no library: flat ground and box houses projected from the rider's eye (a tiny software 3D
 * of quads clipped at the near plane), painted far to near; people, scooters, lamps and signs are billboards; the
 * handlebars, mirrors and the speedometer are one cached bitmap. Frames are measured: a phone that cannot keep up
 * first draws fewer pixels, then opts.slow() switches the career to "Đi nhanh". */
import {t as tr} from '../v4/i18n.js';
import {lightAt} from '../v4/dayclock.js';

export const B=40;                 // one map block in metres
const HW=5,SW=3,FRONT=HW+SW;       // half the road, the pavement, the house fronts from the street's middle
const EYE=1.35,NEAR=.35,FAR=190;
const VMAX=15,ACC=7,BRAKE=16,DRAG=1.8;
const GX=6,GY=4;                   // last junction index on each axis
const RM=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)');
const still=()=>Boolean(RM?.matches)||document.documentElement.classList.contains('reduce-motion')||document.body.classList.contains('reduce-motion');

/* Street names (vertical streets x=0…6, then horizontal y=0…4). */
const STREETS_V=['Đường Khế Ngọt','Đường Mây Chiều','Đường Bồ Câu','Đường Gió Lộng','Đường Mèo Mướp','Đường Sứ Trắng','Đường Cỏ May'];
const STREETS_H=['Đường Hoàng Hôn','Đường Lá Me','Đường Chợ Chiều','Đường Hoa Giấy','Đường Phượng Vĩ'];
/* What each stop looks like: walls, height, awning, a shape. */
const LOOK={
  hub:{col:'#f2c14e',h:8,awn:'#c8452f',shape:'shop'},gas:{col:'#e9e4da',h:4,awn:'#d9442b',shape:'gas'},
  com:{col:'#f4d6a6',h:7,awn:'#3f8f5a',shape:'shop'},bun:{col:'#f1b98f',h:7,awn:'#b8402f',shape:'shop'},
  tra:{col:'#f7c6d6',h:7,awn:'#8a5bb8',shape:'shop'},apt:{col:'#a9c6dd',h:19,shape:'tower'},
  alley:{col:'#d8c3a0',h:6,shape:'arch'},school:{col:'#f3d36a',h:10,shape:'school'},
  market:{col:'#e3b778',h:5,awn:'#2f7fb8',shape:'market'},office:{col:'#8fa9bf',h:27,shape:'tower'},
  villa:{col:'#f3efe4',h:7,shape:'villa'},vet:{col:'#c9e3cf',h:7,awn:'#3b8f87',shape:'shop'},
  garage:{col:'#9aa3ad',h:6,awn:'#e07a2f',shape:'garage'},
};
const HOUSE=['#f3d9b1','#f6e6c8','#e9c7a3','#cfe0e8','#f2cfc4','#e6e0b8','#d9d2e6','#f7efe0','#cde3c6','#f0c9a0'];
const SHIRT=['#e0823a','#3b7dd8','#d94f6b','#3f9f6b','#8a5bb8','#d9b23b','#3aa6b9'];

/* ---------------------------------------------------------------- tiny helpers */
const clamp=(v,a,b)=>v<a?a:v>b?b:v;
function rng(seed){let s=seed>>>0||1;return ()=>{s^=s<<13;s>>>=0;s^=s>>17;s^=s<<5;s>>>=0;return s/4294967296;};}
const hex=h=>[parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)];
const css=([r,g,b],a=1)=>a<1?`rgba(${r|0},${g|0},${b|0},${a})`:`rgb(${r|0},${g|0},${b|0})`;
const mix=(a,b,t)=>a.map((v,i)=>v+(b[i]-v)*t);
const ESC=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

/** Is (x,y) on a street (with room for the scooter)? */
export function onRoad(x,y,m=.6){
  const i=Math.round(x/B),j=Math.round(y/B);
  if(i>=0&&i<=GX&&Math.abs(x-i*B)<=HW-m&&y>=-HW+m&&y<=GY*B+HW-m)return true;
  return j>=0&&j<=GY&&Math.abs(y-j*B)<=HW-m&&x>=-HW+m&&x<=GX*B+HW-m;
}
/** Where a stop's door is: its landmark stands on the corner north-east of its junction (north-west on the last
 * street), facing the street; `x` is the door, `y` the street it faces. */
export function gateOf(n){
  const gx=Number(n.x)||0,gy=Number(n.y)||0,east=gx<GX;
  return {x:gx*B+(east?FRONT+6:-FRONT-6),y:gy*B,gx,gy,east};
}
/** The next point to ride to on the way to `T` (a gateOf): along this street to the target's street (turning in the
 * middle of a junction), then to the door. The ▲ of the HUD points at it. */
export function waypoint(px,py,T){
  const i=Math.round(px/B),j=Math.round(py/B),onH=Math.abs(py-j*B)<=HW+.5,onV=Math.abs(px-i*B)<=HW+.5;
  const ti=clamp(Math.round(T.x/B),0,GX);
  let w;
  if(onH&&j===T.gy)w={x:T.x,y:T.y-2,last:true};                 // on the target's street: to the door
  else if(onV&&(i===ti||!onH))w={x:i*B,y:T.gy*B};                // on the right avenue (or between junctions on one)
  else w={x:ti*B,y:j*B};                                         // along this street to the target's avenue
  // In a junction, line up with the street about to be taken (its middle) before turning, so the arrow never cuts a corner.
  if(onH&&onV){
    const across=w.y===j*B||w.last?Math.abs(py-j*B)>1.5:Math.abs(px-i*B)>1.5;
    if(across)return {x:i*B,y:j*B};
  }
  return w;
}

/* ---------------------------------------------------------------- the world (built once per set of stops) */
export function buildWorld(nodes){
  const R=rng(20261003),houses=[],cells=new Map(),lamps=[],trees=[],signs=[],lights=[],marks={};
  const cellAdd=(cx,cy,o)=>{const k=cx+','+cy;(cells.get(k)||cells.set(k,[]).get(k)).push(o);};
  // Landmarks: two house slots of the south row of the corner cell.
  const taken=new Set();
  for(const [id,n] of Object.entries(nodes||{})){
    const g=gateOf(n),cx=g.east?g.gx:g.gx-1,cy=g.gy-1,slot=g.east?0:2;
    taken.add(`${cx},${cy},S,${slot}`);taken.add(`${cx},${cy},S,${slot+1}`);
    const x0=cx*B+FRONT+slot*6,x1=x0+12,y1=g.gy*B-FRONT,look=LOOK[id]||{col:'#e8d9bd',h:7,shape:'shop'};
    const L={id,node:n,gate:g,x0,x1,y1,look,emoji:n.emoji||'📍',name:n.name||id};
    marks[id]=L;
    for(const b of landmarkBoxes(L))cellAdd(cx,cy,b);
  }
  // Ordinary houses: narrow tube houses along every side of a block that faces a street.
  for(let cx=-1;cx<=GX;cx++)for(let cy=-1;cy<=GY;cy++){
    const inX=cx>=0&&cx<GX,inY=cy>=0&&cy<GY;
    const x0=cx*B+FRONT,x1=(cx+1)*B-FRONT,y0=cy*B+FRONT,y1=(cy+1)*B-FRONT;
    const rows=[];
    if(inX&&cy+1<=GY&&cy>=-1)rows.push(['S',cy+1]);          // faces the street y=(cy+1)·B
    if(inX&&cy>=0)rows.push(['N',cy]);                        // faces y=cy·B
    if(inY&&cx+1<=GX)rows.push(['E',cx+1]);                   // faces x=(cx+1)·B
    if(inY&&cx>=0)rows.push(['W',cx]);
    const full=!(inX&&inY);                                   // a block on the edge has one row, the whole side
    for(const [face,line] of rows){
      const along=face==='S'||face==='N',n=along||full?4:2,len=along||full?(x1-x0):(y1-y0-15.2),start=along||full?0:7.6,w=len/n;
      for(let k=0;k<n;k++){
        if(face==='S'&&taken.has(`${cx},${cy},S,${k}`))continue;
        if(!full&&k===n-1&&(face==='W'&&taken.has(`${cx},${cy},S,0`)||face==='E'&&taken.has(`${cx},${cy},S,3`)))continue;   // a landmark's yard
        const d=6+R()*1.5,h=[5.5,6.5,8.5,9.5,11.5][Math.floor(R()*5)],col=HOUSE[Math.floor(R()*HOUSE.length)];
        let b;
        if(face==='S')b={x0:x0+k*w,x1:x0+(k+1)*w,y0:y1-d,y1};
        else if(face==='N')b={x0:x0+k*w,x1:x0+(k+1)*w,y0,y1:y0+d};
        else if(face==='E')b={x0:x1-d,x1,y0:y0+start+k*w,y1:y0+start+(k+1)*w};
        else b={x0,x1:x0+d,y0:y0+start+k*w,y1:y0+start+(k+1)*w};
        // Street numbers: odd on the north / west side, even on the south / east side, rising east / south.
        const idx=along?cx*4+k:cy*4+(full?k:k+1),odd=face==='S'||face==='E';
        Object.assign(b,{zb:0,h,col,face,k:'house',no:Math.max(1,odd?2*idx+1:2*idx+2),shop:R()<.45,awn:R()<.5?SHIRT[Math.floor(R()*SHIRT.length)]:null,
          street:along?STREETS_H[line]:STREETS_V[line],win:R()<.5?1:2});
        houses.push(b);cellAdd(cx,cy,b);
      }
    }
  }
  // Street furniture: lamps and trees along the pavements, a name sign and (on some corners) lights at junctions.
  for(let i=0;i<=GX;i++)for(let y=10;y<GY*B;y+=20){if(Math.abs(y%B)<9||Math.abs(y%B)>B-9)continue;const s=(y/20|0)%2?1:-1;lamps.push({x:i*B+s*(HW+.6),y});if(R()<.6)trees.push({x:i*B-s*(HW+1.4),y:y+5+R()*4,r:1.2+R()*.6});}
  for(let j=0;j<=GY;j++)for(let x=10;x<GX*B;x+=20){if(Math.abs(x%B)<9||Math.abs(x%B)>B-9)continue;const s=(x/20|0)%2?1:-1;lamps.push({x,y:j*B+s*(HW+.6)});if(R()<.6)trees.push({x:x+5+R()*4,y:j*B-s*(HW+1.4),r:1.2+R()*.6});}
  const LIT=new Set(['1,1','3,1','5,1','1,3','3,3','5,3','3,2','2,2','4,2']);
  for(let i=0;i<=GX;i++)for(let j=0;j<=GY;j++){
    signs.push({x:i*B-HW-1.2,y:j*B+HW+1.2,v:STREETS_V[i],h:STREETS_H[j]});
    if(LIT.has(i+','+j))lights.push({i,j,x:i*B+HW+.8,y:j*B-HW-.8,x2:i*B-HW-.8,y2:j*B+HW+.8,off:((i*7+j*3)%16)});
  }
  return {houses,cells,lamps,trees,signs,lights,marks,lit:LIT};
}
/** The boxes a stop is built of (all on its south row, front face south). */
function landmarkBoxes(L){
  const {x0,x1,y1,look}=L,col=look.col,out=[];
  const box=(a,b,c,d,zb,h,o={})=>out.push({x0:a,x1:b,y0:c,y1:d,zb,h,col,face:'S',k:'mark',L,...o});
  switch(look.shape){
    case 'gas':
      box(x0+1,x1-1,y1-9,y1-6,0,look.h,{sign:true});
      box(x0,x1,y1-5,y1+.6,4.3,.7,{col:'#d9442b',canopy:true});
      box(x0+3,x0+3.8,y1-2.4,y1-1.6,0,1.6,{col:'#c93d2a',pump:true});box(x1-3.8,x1-3,y1-2.4,y1-1.6,0,1.6,{col:'#c93d2a',pump:true});
      box(x0+.4,x0+.8,y1-.4,y1,0,4.3,{col:'#eeeeee'});box(x1-.8,x1-.4,y1-.4,y1,0,4.3,{col:'#eeeeee'});
      break;
    case 'villa':
      box(x0,x1,y1-.5,y1,0,2.2,{gate:true,col:'#efe7d4'});
      box(x0+2,x1-2,y1-11,y1-4,0,look.h,{sign:true,win:2});
      break;
    case 'arch':
      box(x0+1,x0+1.6,y1-.6,y1,0,4.6,{col:'#b9483a'});box(x1-1.6,x1-1,y1-.6,y1,0,4.6,{col:'#b9483a'});
      box(x0+1,x1-1,y1-.6,y1,4.0,1.1,{col:'#b9483a',sign:true,arch:true});
      box(x0,x0+4.5,y1-7,y1-1.5,0,5.5,{col:'#e7c9a1',win:1});box(x1-4.5,x1,y1-7,y1-1.5,0,6.5,{col:'#d8e2c8',win:1});
      break;
    case 'market':box(x0,x1,y1-8,y1,0,look.h,{sign:true,awn:look.awn,stalls:true});break;
    case 'garage':box(x0,x1,y1-8,y1,0,look.h,{sign:true,awn:look.awn,open:true});break;
    case 'tower':box(x0+.5,x1-.5,y1-10,y1,0,look.h,{sign:true,tower:true});break;
    case 'school':box(x0,x1,y1-8,y1,0,look.h,{sign:true,win:3});break;
    default:box(x0,x1,y1-8,y1,0,look.h,{sign:true,awn:look.awn,shopfront:true});
  }
  return out;
}

/* ---------------------------------------------------------------- the stage */
const S={el:null,cv:null,c:null,mini:null,mc:null,goal:null,say:null,slot:null,world:null,nodesKey:'',opts:null,
  at:null,x:0,y:0,a:0,v:0,steer:0,roll:0,keys:{},btn:{},raf:0,last:0,t:0,w:0,h:0,dpr:1,bars:null,barsKey:'',
  pal:null,palKey:'',still:0,stopDone:false,sending:false,sayT:0,shake:0,lastRed:0,lastBump:0,inBox:'',
  npcs:[],peds:[],rain:[],frames:[],cost:[],perf:{n:0,sum:0,bad:0,skip:40},visible:true,hinted:false,miniT:0,goalT:0,fail:false};
globalThis.__dlDrive={
  stats:()=>{const f=[...S.frames].sort((a,b)=>a-b),n=f.length;const d=[...S.cost].sort((a,b)=>a-b),m=d.length;return {n,avg:n?f.reduce((s,v)=>s+v,0)/n:0,p50:n?f[n>>1]:0,p95:n?f[Math.min(n-1,Math.floor(n*.95))]:0,draw:m?d.reduce((s,v)=>s+v,0)/m:0,draw95:m?d[Math.min(m-1,Math.floor(m*.95))]:0,dpr:S.dpr,w:S.w,h:S.h};},
  state:()=>{const T=S.opts&&S.world?.marks[S.opts.target];return {x:S.x,y:S.y,a:S.a,v:S.v,at:S.at,target:S.opts?.target||null,sending:S.sending,
    gate:T?{x:T.gate.x,y:T.gate.y,gy:T.gate.gy}:null,wp:T?waypoint(S.x,S.y,T.gate):null,running:!!S.raf,B,HW};},
  reset:()=>{S.frames=[];S.cost=[];},
};

const ARROW='<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M12 3 4 13h5v8h6v-8h5z" fill="currentColor"/></svg>';
const TRI=d=>`<svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true"><path d="${d<0?'M17 4 6 12l11 8z':'M7 4l11 8-11 8z'}" fill="currentColor"/></svg>`;
function build(){
  const el=document.createElement('div');el.className='dd-stage';
  el.innerHTML=`<canvas class="dd-cv" tabindex="0" role="img" aria-label="${ESC(tr('Xe máy: lái tới nhà có người vẫy tay'))}"></canvas>
    <div class="dd-goal" aria-live="polite"><i class="dd-arrow" aria-hidden="true">${ARROW}</i><span><b></b><small></small></span></div>
    <canvas class="dd-mini" aria-hidden="true"></canvas>
    <div class="dd-say" role="status" aria-live="polite" hidden></div>
    <div class="dd-pads">
      <div class="dd-pad-l"><button type="button" class="dd-btn" data-dd="l" aria-label="${ESC(tr('Rẽ trái'))}">${TRI(-1)}</button><button type="button" class="dd-btn" data-dd="r" aria-label="${ESC(tr('Rẽ phải'))}">${TRI(1)}</button></div>
      <div class="dd-pad-r"><button type="button" class="dd-btn dd-brake" data-dd="d"><span aria-hidden="true">✋</span><small>${ESC(tr('Phanh'))}</small></button><button type="button" class="dd-btn dd-gas" data-dd="u">${ARROW}<small>${ESC(tr('Ga'))}</small></button></div>
    </div>`;
  S.el=el;S.cv=el.querySelector('.dd-cv');S.mini=el.querySelector('.dd-mini');S.goal=el.querySelector('.dd-goal');S.say=el.querySelector('.dd-say');
  S.c=S.cv.getContext('2d',{alpha:false});S.mc=S.mini.getContext('2d');
  if(!S.c)throw new Error('no 2d canvas');
  // Pedals: held while the finger is on them (each its own pointer, so steer + gas together works).
  for(const b of el.querySelectorAll('[data-dd]')){
    const k=b.dataset.dd,on=e=>{e.preventDefault();S.btn[k]=true;b.classList.add('on');try{b.setPointerCapture(e.pointerId);}catch{/* old browser */}},
      off=()=>{S.btn[k]=false;b.classList.remove('on');};
    b.addEventListener('pointerdown',on);b.addEventListener('pointerup',off);b.addEventListener('pointercancel',off);b.addEventListener('lostpointercapture',off);
    b.addEventListener('contextmenu',e=>e.preventDefault());
  }
  new ResizeObserver(()=>size()).observe(el);
  try{new IntersectionObserver(es=>{S.visible=es.some(e=>e.isIntersecting);if(S.visible)wake();}).observe(el);}catch{/* always drawn */}
  document.addEventListener('keydown',key,true);document.addEventListener('keyup',key,true);
  addEventListener('blur',()=>{S.keys={};S.btn={};});
  document.addEventListener('visibilitychange',()=>{S.keys={};if(!document.hidden)wake();});
}
const KEYS={ArrowLeft:'l',KeyA:'l',ArrowRight:'r',KeyD:'r',ArrowUp:'u',KeyW:'u',ArrowDown:'d',KeyS:'d',Space:'d'};
function key(e){
  const k=KEYS[e.code];if(!k||!live())return;
  if(e.target?.closest?.('input,textarea,select,[contenteditable="true"]'))return;
  const dlg=e.target?.closest?.('dialog');if(dlg&&!dlg.contains(S.el))return;   // a question on top of the sheet
  if(e.ctrlKey||e.metaKey||e.altKey)return;
  e.preventDefault();S.keys[k]=e.type==='keydown';
}
const live=()=>!!(S.el?.isConnected&&S.el.closest('dialog[open],#sheet[open]')&&!document.hidden);

/** Put the stage into `slot` (after a render of the work sheet) with the current state of the shift. */
export function mount(slot,opts){
  if(S.fail)return false;
  try{if(!S.el)build();}catch(error){S.fail=true;console.warn('Tự lái: không vẽ được',error);opts.fail?.();return false;}
  S.opts=opts;S.slot=slot;
  const key=JSON.stringify(Object.entries(opts.nodes||{}).map(([k,n])=>[k,n.x,n.y]));
  if(key!==S.nodesKey){S.world=buildWorld(opts.nodes);S.nodesKey=key;S.at=null;}
  if(S.at!==opts.at){place(opts.at,opts.target);}
  if(S.el.parentNode!==slot){slot.append(S.el);size();}
  if(opts.first&&!S.hinted){S.hinted=true;setTimeout(()=>say(tr('Lái tới nhà có người vẫy tay'),5200),400);}
  wake();
  return true;
}
/** The player chose Tự lái again after a fallback: try once more at full size. */
export function again(){S.fail=false;S.perf={n:0,sum:0,bad:0,skip:40,level:0};if(S.el)size();}
/** The work sheet moved on (no leg to ride): the frames stop. */
export function park(){if(S.raf){cancelAnimationFrame(S.raf);S.raf=0;}S.keys={};S.btn={};}

/** Start of a leg: the scooter at the door of the stop the courier is at, facing the way to go. */
function place(at,target){
  const W=S.world,from=W.marks[at],to=W.marks[target];
  S.at=at;S.v=0;S.steer=0;S.stopDone=true;S.sending=false;S.still=0;S.inBox='';
  if(from){S.x=from.gate.x;S.y=from.gate.y-2.2;}else{S.x=B;S.y=2*B;}
  const wp=to?waypoint(S.x,S.y,to.gate):null;
  S.a=wp&&wp.x<S.x-1?Math.PI:0;
  seedTraffic(true);
}

function size(){
  if(!S.el)return;
  const w=Math.max(200,S.el.clientWidth||S.slot?.clientWidth||360);
  const h=Math.round(clamp(w*(w<560?1.04:.62),300,Math.min(480,Math.max(300,innerHeight*.6))));
  S.el.style.height=h+'px';
  const lv=S.perf.level||0,dpr=Math.min(devicePixelRatio||1,lv?1:1.5)*(lv>=2?.75:1);
  S.w=w;S.h=h;S.dpr=dpr;
  S.cv.width=Math.round(w*dpr);S.cv.height=Math.round(h*dpr);
  const mw=Math.round(clamp(w*.24,78,120)),mh=Math.round(mw*.74);
  S.mini.style.width=mw+'px';S.mini.style.height=mh+'px';S.mini.width=Math.round(mw*Math.min(2,devicePixelRatio||1));S.mini.height=Math.round(mh*Math.min(2,devicePixelRatio||1));
  S.barsKey='';
}
function wake(){if(!S.raf&&S.el?.isConnected){S.last=performance.now();S.raf=requestAnimationFrame(frame);}}
function say(text,ms=2600){
  if(!S.say)return;S.say.textContent=text;S.say.hidden=false;S.sayT=performance.now()+ms;
}

/* ---------------------------------------------------------------- traffic: scooters in their lane, people on the pavement */
function seedTraffic(all){
  const R=Math.random;
  if(all){S.npcs=[];S.peds=[];}
  while(S.npcs.length<12)S.npcs.push(spawnNpc(R,true));
  while(S.peds.length<14)S.peds.push(spawnPed(R));
}
function spawnNpc(R,near){
  for(let k=0;k<20;k++){
    const axis=R()<.5?'x':'y',line=axis==='x'?Math.floor(R()*(GY+1)):Math.floor(R()*(GX+1)),max=(axis==='x'?GX:GY)*B;
    const pos=R()*max,dir=R()<.5?1:-1,o={axis,line,pos,dir,sp:5.5+R()*3,v:0,col:SHIRT[Math.floor(R()*SHIRT.length)],hel:HOUSE[Math.floor(R()*HOUSE.length)],turned:-1,honk:0};
    npcPos(o);
    const d=Math.hypot(o.x-S.x,o.y-S.y);
    if(d>(near?25:70)&&d<160)return o;
  }
  return {axis:'x',line:0,pos:0,dir:1,sp:6,v:0,col:SHIRT[0],hel:HOUSE[0],turned:-1,honk:0,x:0,y:0};
}
function npcPos(o){
  // Right-hand traffic: the lane right of the way the scooter faces.
  if(o.axis==='x'){o.x=o.pos;o.y=o.line*B+o.dir*2.3;}else{o.y=o.pos;o.x=o.line*B-o.dir*2.3;}
}
function spawnPed(R){
  for(let k=0;k<20;k++){
    const axis=R()<.5?'x':'y',line=axis==='x'?Math.floor(R()*(GY+1)):Math.floor(R()*(GX+1)),side=R()<.5?1:-1,max=(axis==='x'?GX:GY)*B;
    const pos=R()*max,o={axis,line,side,pos,dir:R()<.5?1:-1,sp:.8+R()*.6,col:SHIRT[Math.floor(R()*SHIRT.length)],hat:R()<.35,t:R()*9};
    pedPos(o);
    const d=Math.hypot(o.x-S.x,o.y-S.y);
    if(d>12&&d<130)return o;
  }
  return {axis:'x',line:0,side:1,pos:0,dir:1,sp:1,col:SHIRT[1],hat:false,t:0,x:0,y:0};
}
function pedPos(o){const off=o.side*(HW+1.7);if(o.axis==='x'){o.x=o.pos;o.y=o.line*B+off;}else{o.y=o.pos;o.x=o.line*B+off;}}
function lightState(L,axis,t){const p=(t+L.off)%16;return axis==='y'?(p<6?'g':p<8?'y':'r'):(p<8?'r':p<14?'g':'y');}
function lightAtJunction(i,j){const W=S.world;return W.lit.has(i+','+j)?W.lights.find(l=>l.i===i&&l.j===j):null;}

function moveTraffic(dt){
  const t=S.t;
  for(let n=0;n<S.npcs.length;n++){
    const o=S.npcs[n];
    let want=o.sp;
    // A red (or yellow) light ahead: stop at the line.
    const max=(o.axis==='x'?GX:GY)*B,next=o.dir>0?Math.ceil((o.pos+.01)/B)*B:Math.floor((o.pos-.01)/B)*B,gap=(next-o.pos)*o.dir;
    if(next>=0&&next<=max){
      const k=next/B,L=o.axis==='x'?lightAtJunction(k,o.line):lightAtJunction(o.line,k);
      if(L&&gap>HW+1&&gap<HW+7&&lightState(L,o.axis,t)!=='g')want=0;
    }
    // Do not ride into the courier: wait behind them, honk once.
    const dx=S.x-o.x,dy=S.y-o.y,fw=o.axis==='x'?dx*o.dir:dy*o.dir,side=o.axis==='x'?Math.abs(dy):Math.abs(dx);
    if(fw>0&&fw<6&&side<2.2){want=0;if(!o.honk&&S.v<1){o.honk=1.2;}}
    o.honk=Math.max(0,o.honk-dt);
    o.v+=clamp(want-o.v,-9*dt,3*dt);
    const before=o.pos;o.pos+=o.dir*o.v*dt;
    // At a junction: sometimes turn.
    const cross=Math.floor(before/B)!==Math.floor(o.pos/B);
    if(cross){
      const k=Math.round(o.pos/B);
      if(k>=0&&k*B<=max&&o.turned!==k&&Math.random()<.35){
        const oldLine=o.line,oldAxis=o.axis;o.axis=oldAxis==='x'?'y':'x';o.line=k;o.pos=oldLine*B;o.turned=oldLine;
        const lim=(o.axis==='x'?GX:GY)*B;o.dir=o.pos<=0?1:o.pos>=lim?-1:(Math.random()<.5?1:-1);
      }else o.turned=-1;
    }
    if(o.pos<-HW||o.pos>max+HW){o.dir=-o.dir;o.pos=clamp(o.pos,-HW,max+HW);}
    npcPos(o);
    if(Math.hypot(o.x-S.x,o.y-S.y)>170)S.npcs[n]=spawnNpc(Math.random,false);
  }
  for(let n=0;n<S.peds.length;n++){
    const o=S.peds[n],max=(o.axis==='x'?GX:GY)*B;o.t+=dt;o.pos+=o.dir*o.sp*dt;
    if(o.pos<0||o.pos>max||Math.random()<dt*.03)o.dir=-o.dir;
    pedPos(o);
    if(Math.hypot(o.x-S.x,o.y-S.y)>150)S.peds[n]=spawnPed(Math.random);
  }
}

/* ---------------------------------------------------------------- riding */
function input(){
  const k=S.keys,b=S.btn;
  return {steer:((k.r||b.r)?1:0)-((k.l||b.l)?1:0),gas:!!(k.u||b.u),brake:!!(k.d||b.d)};
}
function ride(dt){
  const inp=input(),o=S.opts,rain=o.weather==='rain',vmax=VMAX*(rain?.85:1);
  if(S.sending){inp.gas=false;inp.brake=true;}
  if(inp.brake)S.v=Math.max(0,S.v-BRAKE*dt);
  else if(inp.gas)S.v=Math.min(vmax,S.v+ACC*dt*(1-S.v/(vmax*1.08)));
  else S.v=Math.max(0,S.v-DRAG*dt);
  S.steer+=clamp(inp.steer-S.steer,-6*dt,6*dt);
  const rate=1.75*(.5+.5*Math.min(1,S.v/6));
  S.a+=S.steer*rate*dt;
  // Let go of the bar: it settles on the street's direction (phones: no fiddly straightening).
  if(!inp.steer&&S.v>.8){const q=Math.round(S.a/(Math.PI/2))*(Math.PI/2),d=q-S.a;if(Math.abs(d)<.55)S.a+=Math.sign(d)*Math.min(Math.abs(d),1.1*dt);}
  S.a=((S.a+Math.PI)%(2*Math.PI)+2*Math.PI)%(2*Math.PI)-Math.PI;
  const nx=S.x+Math.cos(S.a)*S.v*dt,ny=S.y+Math.sin(S.a)*S.v*dt;
  if(onRoad(nx,ny)){S.x=nx;S.y=ny;}
  else if(onRoad(nx,S.y)){S.x=nx;S.v*=Math.pow(.6,dt);}
  else if(onRoad(S.x,ny)){S.y=ny;S.v*=Math.pow(.6,dt);}
  else if(S.v>.5){bump(tr('Ối, lề đường!'));S.v*=.25;}
  // Scooters: a soft bump, no harm done.
  for(const n of S.npcs)if(Math.abs(n.x-S.x)<1.5&&Math.abs(n.y-S.y)<1.5&&S.v>1){bump(tr('Ối! Chạy chậm thôi'));S.v*=.3;n.v=0;n.honk=1.5;}
  // Junction boxes: a red light run is said once, nothing else.
  const i=Math.round(S.x/B),j=Math.round(S.y/B),inBox=Math.abs(S.x-i*B)<HW&&Math.abs(S.y-j*B)<HW?i+','+j:'';
  if(inBox&&inBox!==S.inBox){
    const L=lightAtJunction(i,j),axis=Math.abs(Math.cos(S.a))>Math.abs(Math.sin(S.a))?'x':'y';
    if(L&&S.v>2.5&&lightState(L,axis,S.t)==='r'&&S.t-S.lastRed>6){S.lastRed=S.t;say(tr('🚦 Đèn đỏ! Lần sau chờ đèn xanh nhé'));}
  }
  S.inBox=inBox;
  stops(dt);
}
function bump(text){if(S.t-S.lastBump>1.4){S.lastBump=S.t;say(text,1600);}if(!still())S.shake=.25;}

/** Standing still in front of a door: arrive (a stop), or a friendly word (an ordinary house, a stop with nothing to do). */
function stops(dt){
  if(S.v>1.4){S.stopDone=false;S.still=0;return;}
  if(S.v>.6||S.stopDone||S.sending)return;
  S.still+=dt;if(S.still<.35)return;
  const W=S.world,o=S.opts;
  for(const L of Object.values(W.marks)){
    const g=L.gate;
    if(Math.abs(S.x-g.x)<6.5&&S.y>=g.y-HW-1&&S.y<=g.y+HW+1){
      S.stopDone=true;
      if(L.id===S.at)return;
      if(L.id!==o.target&&!o.useful?.[L.id]){say(tr('Ở đây chưa có việc'));return;}
      S.sending=true;say(`${L.emoji} ${tr('Tới rồi!')}`,1800);
      Promise.resolve(o.arrive?.(L.id)).then(r=>{S.sending=false;if(r&&r.say)say(r.say,3200);}).catch(()=>{S.sending=false;});
      return;
    }
  }
  if(S.still<.6)return;
  S.stopDone=true;
  if(!o.target)return;
  // An ordinary house: the courier by its kerb.
  for(const b of W.houses){
    if(b.face==='S'||b.face==='N'){
      const fy=b.face==='S'?b.y1:b.y0;if(Math.abs(S.y-fy)>FRONT-HW+2.6||S.x<b.x0-1||S.x>b.x1+1)continue;
    }else{
      const fx=b.face==='E'?b.x1:b.x0;if(Math.abs(S.x-fx)>FRONT-HW+2.6||S.y<b.y0-1||S.y>b.y1+1)continue;
    }
    say(`${tr('Không phải nhà này')} · ${tr('số')} ${b.no}`);return;
  }
}

/* ---------------------------------------------------------------- light, colours */
const SKY=[[960,'#86bde8','#f5e6c6'],[1050,'#76a6da','#f6cf96'],[1110,'#5f74b0','#f0a573'],[1140,'#33407a','#c98272'],[1200,'#1d2552','#4d4c7c'],[1290,'#10173a','#2a315c'],[1440,'#10173a','#2a315c']];
function palette(){
  const o=S.opts,minute=Number(o.minute)||17*60,rain=o.weather==='rain',key=Math.round(minute/2)+(rain?'r':'s');
  if(S.pal&&S.palKey===key)return S.pal;
  const L=lightAt(minute),m=((minute%1440)+1440)%1440;let i=0;while(i<SKY.length-2&&SKY[i+1][0]<=m)i++;
  const [a,t0,b0]=SKY[i],[b,t1,b1]=SKY[i+1],f=b>a?clamp((m-a)/(b-a),0,1):0;
  let top=mix(hex(t0),hex(t1),f),bot=mix(hex(b0),hex(b1),f);
  if(rain){top=mix(top,[96,104,118],.55);bot=mix(bot,[140,146,156],.55);}
  const k=L.rgb.map(v=>1-L.alpha+L.alpha*v/255),wet=rain?.82:1,cache=new Map();
  const tint=h=>{let c=cache.get(h);if(!c){const v=hex(h);c=css(rain?mix(v.map((x,n)=>x*k[n]*wet),[120,124,130],.18):v.map((x,n)=>x*k[n]));cache.set(h,c);}return c;};
  S.pal={top:css(top),bot:css(bot),fog:bot,lamps:L.lamps,rain,storm:rain&&(o.signs||[]).some(s=>s.kind==='flood'),tint,dark:L.alpha};
  S.palKey=key;
  return S.pal;
}

/* ---------------------------------------------------------------- projection */
const cam={x:0,y:0,ca:1,sa:0,F:300,cx:0,hz:0};
function toCam(wx,wy,h){const dx=wx-cam.x,dy=wy-cam.y;return [-dx*cam.sa+dy*cam.ca,h,dx*cam.ca+dy*cam.sa];}
function proj(p){return [cam.cx+p[0]/p[2]*cam.F,cam.hz+(EYE-p[1])/p[2]*cam.F];}
function clip(ps){
  const out=[];
  for(let i=0;i<ps.length;i++){
    const a=ps[i],b=ps[(i+1)%ps.length],ia=a[2]>=NEAR,ib=b[2]>=NEAR;
    if(ia)out.push(a);
    if(ia!==ib){const t=(NEAR-a[2])/(b[2]-a[2]);out.push([a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,NEAR]);}
  }
  return out;
}
function poly(c,ps,fill){
  const q=clip(ps);if(q.length<3)return false;
  c.beginPath();
  for(let i=0;i<q.length;i++){const s=proj(q[i]);if(i)c.lineTo(s[0],s[1]);else c.moveTo(s[0],s[1]);}
  c.closePath();c.fillStyle=fill;c.fill();return true;
}
const gquad=(c,x0,y0,x1,y1,fill)=>poly(c,[toCam(x0,y0,0),toCam(x1,y0,0),toCam(x1,y1,0),toCam(x0,y1,0)],fill);
/** A point on a box's street face: u 0..1 left → right as seen from the street, v metres up. */
function facePt(b,u,v){
  switch(b.face){
    case 'S':return toCam(b.x0+(b.x1-b.x0)*u,b.y1,v);
    case 'N':return toCam(b.x1-(b.x1-b.x0)*u,b.y0,v);
    case 'E':return toCam(b.x1,b.y1-(b.y1-b.y0)*u,v);
    default:return toCam(b.x0,b.y0+(b.y1-b.y0)*u,v);
  }
}
function fquad(c,b,u0,u1,v0,v1,fill){
  const p=[facePt(b,u0,v0),facePt(b,u1,v0),facePt(b,u1,v1),facePt(b,u0,v1)];
  if(p[0][2]<NEAR||p[1][2]<NEAR||p[2][2]<NEAR||p[3][2]<NEAR)return null;
  const s=p.map(proj);
  c.beginPath();c.moveTo(s[0][0],s[0][1]);c.lineTo(s[1][0],s[1][1]);c.lineTo(s[2][0],s[2][1]);c.lineTo(s[3][0],s[3][1]);c.closePath();
  if(fill){c.fillStyle=fill;c.fill();}
  return s;
}
const faceSeen=b=>b.face==='S'?cam.y>b.y1:b.face==='N'?cam.y<b.y0:b.face==='E'?cam.x>b.x1:cam.x<b.x0;

/* ---------------------------------------------------------------- frame */
function frame(now){
  S.raf=0;
  if(!S.el?.isConnected||!S.opts){return;}
  const dt=Math.min(.05,Math.max(0,(now-S.last)/1000)),ms=now-S.last;S.last=now;
  if(!live()){park();return;}
  S.t+=dt;
  ride(dt);moveTraffic(dt);
  if(S.visible){const t0=performance.now();draw(now);S.cost.push(performance.now()-t0);if(S.cost.length>600)S.cost.shift();measure(ms);}
  if(S.sayT&&now>S.sayT){S.sayT=0;S.say.hidden=true;}
  S.raf=requestAnimationFrame(frame);
}
/** Frame times; a phone that keeps missing them draws fewer pixels, then switches to "Đi nhanh". */
function measure(ms){
  if(S.perf.skip>0){S.perf.skip--;return;}
  S.frames.push(ms);if(S.frames.length>600)S.frames.shift();
  const P=S.perf;P.n++;P.sum+=ms;
  if(P.n<60)return;
  const avg=P.sum/P.n;P.n=0;P.sum=0;
  if(avg>42)P.bad++;else P.bad=0;
  if(P.bad<2)return;
  P.bad=0;P.skip=30;P.level=(P.level||0)+1;
  if(P.level<=2){size();return;}
  P.level=2;S.fail=true;park();S.opts?.slow?.();
}

function draw(now){
  const c=S.c,w=S.w,h=S.h,pal=palette(),o=S.opts,W=S.world;
  c.setTransform(S.dpr,0,0,S.dpr,0,0);
  // Camera: the rider's eye, a slight lean into the turn and a bob with speed.
  const calm=still(),lean=calm?0:-S.steer*.035*Math.min(1,S.v/7);
  S.roll+=(lean-S.roll)*.15;
  const bob=calm?0:Math.sin(S.t*9)*.6*Math.min(1,S.v/VMAX),sh=S.shake>0?(S.shake-=1/60,(Math.random()-.5)*6):0;
  cam.x=S.x;cam.y=S.y;cam.ca=Math.cos(S.a);cam.sa=Math.sin(S.a);cam.F=w*.78;cam.cx=w/2+sh;cam.hz=h*.42+bob;
  c.save();
  if(S.roll){c.translate(w/2,h*.6);c.rotate(S.roll);c.translate(-w/2,-h*.6);}
  // Sky, far town, ground.
  const g=c.createLinearGradient(0,-40,0,cam.hz);g.addColorStop(0,pal.top);g.addColorStop(1,pal.bot);
  c.fillStyle=g;c.fillRect(-40,-40,w+80,cam.hz+41);
  skyline(c,w,pal);
  c.fillStyle=pal.tint('#a9a78a');c.fillRect(-40,cam.hz,w+80,h-cam.hz+60);
  ground(c,pal,o,W);
  // Mist over the far ground (the far things fade in by themselves).
  const fg=c.createLinearGradient(0,cam.hz-2,0,cam.hz+h*.07);fg.addColorStop(0,css(pal.fog,.9));fg.addColorStop(1,css(pal.fog,0));
  c.fillStyle=fg;c.fillRect(-40,cam.hz-2,w+80,h*.07+2);
  // Things, far to near.
  const things=collect(W,o);
  things.sort((p,q)=>q.z-p.z);
  for(const th of things)drawThing(c,th,pal,o);
  c.restore();
  if(pal.rain)rain(c,w,h,pal);
  if(pal.lamps>.35)headlight(c,w,h,pal);
  bars(c,w,h,pal,o);
  if(++S.goalT>=6){S.goalT=0;goal(o,W);}
  if(++S.miniT>=5){S.miniT=0;mini(o,W);}
}

const SKYRING=(()=>{const R=rng(7);return Array.from({length:36},()=>[.6+R()*.5,10+R()*26]);})();
function skyline(c,w,pal){
  // A ring of far buildings around the town, turning with the heading.
  const n=SKYRING.length,span=w*3.2,off=(((S.a/(2*Math.PI))*span)%span+span)%span;
  c.fillStyle=css(mix(pal.fog,[60,66,90],.32));
  c.beginPath();
  for(let k=0;k<n*2;k++){
    const [fw,fh]=SKYRING[k%n],x=k*span/n-off-span*.25,bw=span/n*fw,bh=fh;
    if(x>w+20||x+bw<-20)continue;
    c.rect(x,cam.hz-bh,bw,bh+1);
  }
  c.fill();
  if(pal.lamps>.4){c.fillStyle=`rgba(255,214,140,${.5*pal.lamps})`;const R2=rng(11);for(let k=0;k<60;k++){const x=((k*53.7+R2()*40-off)%(w+40)+w+40)%(w+40)-20,y=cam.hz-4-R2()*22;c.fillRect(x,y,1.6,1.6);}}
}

function ground(c,pal,o,W){
  const side=pal.tint('#cfc4ae'),road=pal.tint(pal.rain?'#4c5057':'#5e6168'),line=pal.tint('#efe9d8'),yel=pal.tint('#e7bf43');
  // Pavements, then asphalt over them (junctions stay asphalt).
  for(let i=0;i<=GX;i++)gquad(c,i*B-FRONT,-FRONT,i*B+FRONT,GY*B+FRONT,side);
  for(let j=0;j<=GY;j++)gquad(c,-FRONT,j*B-FRONT,GX*B+FRONT,j*B+FRONT,side);
  for(let i=0;i<=GX;i++)gquad(c,i*B-HW,-HW,i*B+HW,GY*B+HW,road);
  for(let j=0;j<=GY;j++)gquad(c,-HW,j*B-HW,GX*B+HW,j*B+HW,road);
  // Hazards of the day on the street by their stop (the server applies them; here they are only seen).
  for(const s of o.signs||[]){
    const L=W.marks[s.node];if(!L)continue;const g=L.gate;
    if(s.kind==='flood')gquad(c,g.x-14,g.y-HW,g.x+10,g.y+HW,`rgba(90,140,190,${pal.rain?.55:.4})`);
  }
  // Centre lines: dashed on the street the scooter is on, a thin line on the others.
  const i0=Math.round(S.x/B),j0=Math.round(S.y/B),onV=Math.abs(S.x-i0*B)<=HW+.5,onH=Math.abs(S.y-j0*B)<=HW+.5;
  for(let i=0;i<=GX;i++){
    if(Math.abs(i*B-S.x)>FAR)continue;
    for(let j=0;j<GY;j++){
      const y0=j*B+HW+1,y1=(j+1)*B-HW-1;if(Math.abs((y0+y1)/2-S.y)>FAR+B)continue;
      if(onV&&i===i0&&Math.abs((y0+y1)/2-S.y)<B*2.2){for(let y=y0;y<y1-2;y+=6)gquad(c,i*B-.12,y,i*B+.12,y+3,line);}
      else gquad(c,i*B-.1,y0,i*B+.1,y1,yel);
    }
  }
  for(let j=0;j<=GY;j++){
    if(Math.abs(j*B-S.y)>FAR)continue;
    for(let i=0;i<GX;i++){
      const x0=i*B+HW+1,x1=(i+1)*B-HW-1;if(Math.abs((x0+x1)/2-S.x)>FAR+B)continue;
      if(onH&&j===j0&&Math.abs((x0+x1)/2-S.x)<B*2.2){for(let x=x0;x<x1-2;x+=6)gquad(c,x,j*B-.12,x+3,j*B+.12,line);}
      else gquad(c,x0,j*B-.1,x1,j*B+.1,yel);
    }
  }
  // Zebra crossings at the junctions with lights, near the scooter.
  for(const L of W.lights){
    const cx=L.i*B,cy=L.j*B;if(Math.abs(cx-S.x)+Math.abs(cy-S.y)>70)continue;
    for(let k=-3;k<=3;k++){
      const u=k*1.3;
      gquad(c,cx+u-.4,cy-HW-2.6,cx+u+.4,cy-HW-.6,line);gquad(c,cx+u-.4,cy+HW+.6,cx+u+.4,cy+HW+2.6,line);
      gquad(c,cx-HW-2.6,cy+u-.4,cx-HW-.6,cy+u+.4,line);gquad(c,cx+HW+.6,cy+u-.4,cx+HW+2.6,cy+u+.4,line);
    }
  }
  // The stop to ride to: a glowing bay on the street in front of its door.
  const T=W.marks[o.target];
  if(T&&T.id!==S.at){const g=T.gate,a=.35+.25*Math.sin(S.t*4);gquad(c,g.x-5.5,g.y-HW+.3,g.x+5.5,g.y-.4,`rgba(255,206,64,${a})`);}
}

/** Everything standing up within sight, with its depth. */
function collect(W,o){
  const out=[],lim=FAR,ca=cam.ca,sa=cam.sa;
  const zOf=(x,y)=>(x-cam.x)*ca+(y-cam.y)*sa,xOf=(x,y)=>-(x-cam.x)*sa+(y-cam.y)*ca;
  const seen=(x,y,r)=>{const z=zOf(x,y);if(z<-r||z>lim+r)return null;const xr=xOf(x,y);if(Math.abs(xr)>Math.max(0,z)*.75+r+6)return null;return z;};
  const cx0=Math.floor((S.x-lim)/B),cx1=Math.floor((S.x+lim)/B),cy0=Math.floor((S.y-lim)/B),cy1=Math.floor((S.y+lim)/B);
  for(let cx=Math.max(-1,cx0);cx<=Math.min(GX,cx1);cx++)for(let cy=Math.max(-1,cy0);cy<=Math.min(GY,cy1);cy++){
    const list=W.cells.get(cx+','+cy);if(!list)continue;
    if(seen(cx*B+B/2,cy*B+B/2,B*.8)===null)continue;
    for(const b of list){const z=seen((b.x0+b.x1)/2,(b.y0+b.y1)/2,8);if(z!==null)out.push({z,k:'box',o:b});}
  }
  for(const p of W.lamps){const z=seen(p.x,p.y,1);if(z!==null&&z<130)out.push({z,k:'lamp',o:p});}
  for(const p of W.trees){const z=seen(p.x,p.y,2);if(z!==null&&z<150)out.push({z,k:'tree',o:p});}
  for(const p of W.signs){const z=seen(p.x,p.y,1);if(z!==null&&z<110)out.push({z,k:'sign',o:p});}
  for(const p of W.lights){let z=seen(p.x,p.y,1);if(z!==null&&z<130)out.push({z,k:'light',o:p,a:1});z=seen(p.x2,p.y2,1);if(z!==null&&z<130)out.push({z,k:'light',o:p,a:2});}
  for(const p of S.npcs){const z=seen(p.x,p.y,1);if(z!==null&&z<140)out.push({z,k:'npc',o:p});}
  for(const p of S.peds){const z=seen(p.x,p.y,1);if(z!==null&&z<90)out.push({z,k:'ped',o:p});}
  for(const s of o.signs||[]){if(s.kind!=='works')continue;const L=W.marks[s.node];if(!L)continue;const x=L.gate.x+(L.gate.east?-10:10),y=L.gate.y+HW-1.2,z=seen(x,y,3);if(z!==null)out.push({z,k:'works',o:{x,y}});}
  const T=W.marks[o.target];
  if(T&&T.id!==S.at){const x=T.gate.x,y=T.gate.y-HW-1.6,z=seen(x,y,2);if(z!==null)out.push({z:z-.01,k:'cust',o:{x,y,L:T}});}
  return out;
}

function drawThing(c,th,pal,o){
  const z=th.z,fog=z>FAR*.6?clamp(1-(z-FAR*.6)/(FAR*.4),0,1):1;
  if(fog<=.02)return;
  c.globalAlpha=fog;
  switch(th.k){
    case 'box':drawBox(c,th.o,z,pal);break;
    case 'lamp':drawLamp(c,th.o,z,pal);break;
    case 'tree':drawTree(c,th.o,pal);break;
    case 'sign':drawSign(c,th.o,z,pal);break;
    case 'light':drawLight(c,th.o,th.a,pal);break;
    case 'npc':drawNpc(c,th.o,pal);break;
    case 'ped':drawPed(c,th.o,pal,false);break;
    case 'works':drawWorks(c,th.o,pal);break;
    case 'cust':drawCustomer(c,th.o,z,pal,o);break;
  }
  c.globalAlpha=1;
}

/* ---------------------------------------------------------------- houses and stops */
function drawBox(c,b,z,pal){
  const {x0,x1,y0,y1,zb}=b,zt=zb+b.h,col=b.col,dark=b.canopy?'#a8321f':shade(col,.8);
  const P=(x,y,hh)=>toCam(x,y,hh);
  const tint=pal.tint;
  // Walls facing the rider (back faces culled), a top when below the eye, the underside of a canopy above it.
  if(cam.y>y1)poly(c,[P(x0,y1,zb),P(x1,y1,zb),P(x1,y1,zt),P(x0,y1,zt)],tint(col));
  if(cam.y<y0)poly(c,[P(x1,y0,zb),P(x0,y0,zb),P(x0,y0,zt),P(x1,y0,zt)],tint(col));
  if(cam.x>x1)poly(c,[P(x1,y1,zb),P(x1,y0,zb),P(x1,y0,zt),P(x1,y1,zt)],tint(dark));
  if(cam.x<x0)poly(c,[P(x0,y0,zb),P(x0,y1,zb),P(x0,y1,zt),P(x0,y0,zt)],tint(dark));
  if(zt<EYE)poly(c,[P(x0,y0,zt),P(x1,y0,zt),P(x1,y1,zt),P(x0,y1,zt)],tint(shade(col,1.08)));
  if(zb>EYE)poly(c,[P(x0,y0,zb),P(x1,y0,zb),P(x1,y1,zb),P(x0,y1,zb)],tint(shade(col,.62)));
  if(!faceSeen(b)||z>95)return;
  if(b.k==='house')houseFront(c,b,z,pal);else markFront(c,b,z,pal);
}
const shadeMemo=new Map();
function shade(h,f){const k=h+f;let v=shadeMemo.get(k);if(!v){const r=hex(h).map(x=>clamp(Math.round(x*f),0,255));v='#'+r.map(x=>x.toString(16).padStart(2,'0')).join('');shadeMemo.set(k,v);}return v;}
function windowCol(pal){return pal.lamps>.45?`rgb(255,${Math.round(205+20*pal.lamps)},${Math.round(120+30*pal.lamps)})`:pal.tint('#7fa4bd');}
function houseFront(c,b,z,pal){
  const floors=Math.max(1,Math.floor(b.h/3)),tint=pal.tint,wc=windowCol(pal);
  // Ground floor: a roll-up shutter or a gate; a little awning; windows above.
  if(b.shop)fquad(c,b,.12,.88,0,2.5,tint('#8d929a'));else{fquad(c,b,.18,.62,0,2.2,tint('#6f5a48'));}
  if(b.awn)fquad(c,b,.05,.95,2.55,2.95,tint(b.awn));
  if(z<70)for(let f=1;f<floors;f++){
    const v0=f*3+.7;
    if(b.win===1)fquad(c,b,.3,.7,v0,v0+1.4,wc);else{fquad(c,b,.14,.44,v0,v0+1.4,wc);fquad(c,b,.56,.86,v0,v0+1.4,wc);}
  }
  // The number plate by the gate: blue, white number, readable near by.
  const s=fquad(c,b,.68,.9,1.7,2.3,'#2c63b8');
  if(s&&z<38){
    const cx=(s[0][0]+s[1][0]+s[2][0]+s[3][0])/4,cy=(s[0][1]+s[1][1]+s[2][1]+s[3][1])/4,fh=Math.abs(s[3][1]-s[0][1])*.8;
    if(fh>=6){c.fillStyle='#fff';c.font=`700 ${fh|0}px system-ui,sans-serif`;c.textAlign='center';c.textBaseline='middle';c.fillText(String(b.no),cx,cy+.5);}
  }
}
function markFront(c,b,z,pal){
  const L=b.L,tint=pal.tint,wc=windowCol(pal);
  if(b.pump||b.canopy)return;
  if(b.tower){const fl=Math.floor(b.h/3);for(let f=1;f<fl&&z<80;f++){const v=f*3+.6;for(let k=0;k<4;k++)fquad(c,b,.06+k*.235,.06+k*.235+.17,v,v+1.5,wc);}fquad(c,b,.38,.62,0,2.6,tint('#3d4a55'));}
  if(b.shopfront||b.open){fquad(c,b,.08,.92,0,2.7,tint(b.open?'#2f3338':'#6b4d3a'));if(z<60&&b.shopfront)fquad(c,b,.14,.86,.9,2.4,wc);}
  if(b.stalls){for(let k=0;k<4;k++)fquad(c,b,.05+k*.24,.05+k*.24+.2,.8,1.4,tint(['#e6a23c','#7cb342','#e57373','#ffd54f'][k]));}
  if(b.awn)for(let k=0;k<6;k++)fquad(c,b,k/6,(k+1)/6,2.75,3.25,tint(k%2?'#f5efe3':b.awn));
  if(b.win&&!b.tower){const fl=Math.max(1,Math.floor(b.h/3));for(let f=b.gate?0:1;f<fl&&z<80;f++){const v=f*3+.7;for(let k=0;k<b.win;k++){const u=(k+.5)/b.win;fquad(c,b,u-.12,u+.12,v,v+1.4,wc);}}}
  if(b.gate){fquad(c,b,.35,.65,0,2.1,tint('#5b4636'));}
  if(b.arch&&z<70){const s=fquad(c,b,.1,.9,.1,.9,'#7a2c22');if(s)label(c,s,L.name,'#ffe7a8');return;}
  if(!b.sign)return;
  // The sign over the door: emoji and the stop's name.
  const top=b.h>9?Math.min(b.h-.4,6.8):b.h-.3,s=fquad(c,b,.06,.94,top-1.6,top,tint('#fbf6ea'));
  if(s)label(c,s,`${L.emoji} ${L.name}`,'#3b2a1e');
}
function label(c,s,text,col){
  const w=Math.hypot(s[1][0]-s[0][0],s[1][1]-s[0][1]),hh=Math.abs(s[3][1]-s[0][1]);if(w<26||hh<6)return;
  const cx=(s[0][0]+s[1][0]+s[2][0]+s[3][0])/4,cy=(s[0][1]+s[1][1]+s[2][1]+s[3][1])/4;
  let fh=Math.min(hh*.62,w/5),t=tr(text);
  c.font=`700 ${fh|0}px system-ui,sans-serif`;
  const m=c.measureText(t).width;if(m>w*.92){fh*=w*.92/m;c.font=`700 ${fh|0}px system-ui,sans-serif`;}
  if(fh<5)return;
  c.fillStyle=col;c.textAlign='center';c.textBaseline='middle';c.fillText(t,cx,cy+.5);
}

/* ---------------------------------------------------------------- billboards */
/** Screen point and pixels-per-metre of a ground point, or null behind the eye. */
function spot(x,y,hh=0){const p=toCam(x,y,hh);if(p[2]<NEAR*2)return null;const s=proj(p);return {x:s[0],y:s[1],k:cam.F/p[2],z:p[2]};}
function drawLamp(c,p,z,pal){
  const s=spot(p.x,p.y);if(!s)return;const k=s.k;
  c.fillStyle=pal.tint('#5a6068');c.fillRect(s.x-.08*k,s.y-5.2*k,.16*k,5.2*k);
  c.fillRect(s.x-.08*k,s.y-5.2*k,.9*k,.12*k);
  const on=pal.lamps;
  c.fillStyle=on>.3?'#fff2c4':pal.tint('#d8d4c8');c.fillRect(s.x+.55*k,s.y-5.15*k,.45*k,.2*k);
  if(on>.3&&z<90){
    c.globalCompositeOperation='lighter';
    const r=3.2*k,g=c.createRadialGradient(s.x+.8*k,s.y-5*k,0,s.x+.8*k,s.y-5*k,r);g.addColorStop(0,`rgba(255,220,150,${.45*on})`);g.addColorStop(1,'rgba(255,220,150,0)');
    c.fillStyle=g;c.fillRect(s.x+.8*k-r,s.y-5*k-r,r*2,r*2);
    c.globalCompositeOperation='source-over';
  }
}
function drawTree(c,p,pal){
  const s=spot(p.x,p.y);if(!s)return;const k=s.k,r=p.r*k;
  c.fillStyle=pal.tint('#6b4f36');c.fillRect(s.x-.13*k,s.y-2.4*k,.26*k,2.4*k);
  c.fillStyle=pal.tint('#4f8a4a');c.beginPath();c.arc(s.x,s.y-3*k,r,0,Math.PI*2);c.fill();
  c.fillStyle=pal.tint('#64a35a');c.beginPath();c.arc(s.x-r*.3,s.y-3.3*k,r*.62,0,Math.PI*2);c.fill();
}
function drawSign(c,p,z,pal){
  const s=spot(p.x,p.y);if(!s)return;const k=s.k;
  c.fillStyle=pal.tint('#6d737c');c.fillRect(s.x-.06*k,s.y-3.4*k,.12*k,3.4*k);
  // Two plates, one per street: the one the rider rides across reads first.
  const along=Math.abs(cam.ca)>Math.abs(cam.sa),names=along?[p.v,p.h]:[p.h,p.v];
  for(let n=0;n<2;n++){
    const y=s.y-(3.4-n*.62)*k,w=2.6*k,hh=.5*k;
    c.fillStyle='#1f5fae';c.fillRect(s.x-w/2,y,w,hh);
    if(z<55&&hh>=7){
      c.fillStyle='#fff';let fh=hh*.62;c.font=`700 ${fh|0}px system-ui,sans-serif`;
      const t=tr(names[n]),m=c.measureText(t).width;if(m>w*.94){fh*=w*.94/m;c.font=`700 ${fh|0}px system-ui,sans-serif`;}
      if(fh>=5){c.textAlign='center';c.textBaseline='middle';c.fillText(t,s.x,y+hh/2+.5);}
    }
  }
}
function drawLight(c,L,which,pal){
  const x=which===1?L.x:L.x2,y=which===1?L.y:L.y2,s=spot(x,y);if(!s)return;const k=s.k;
  c.fillStyle=pal.tint('#4b5058');c.fillRect(s.x-.07*k,s.y-3.6*k,.14*k,3.6*k);
  c.fillStyle='#22262c';c.fillRect(s.x-.28*k,s.y-4.9*k,.56*k,1.4*k);
  // The colour for the way the rider is riding.
  const axis=Math.abs(cam.ca)>Math.abs(cam.sa)?'x':'y',st=lightState(L,axis,S.t),r=.17*k;
  const lamp=(n,on,col)=>{c.fillStyle=on?col:'#3a3f46';c.beginPath();c.arc(s.x,s.y-(4.65-n*.44)*k,r,0,Math.PI*2);c.fill();};
  lamp(0,st==='r','#ff4a3d');lamp(1,st==='y','#ffc23d');lamp(2,st==='g','#38d26b');
}
function rider(c,x,y,k,col,hel,front,tail,pal){
  // A scooter and its rider, seen from behind or from the front.
  c.fillStyle='#24272c';c.fillRect(x-.16*k,y-.62*k,.32*k,.62*k);
  c.fillStyle=pal.tint(col);c.fillRect(x-.36*k,y-1.0*k,.72*k,.5*k);
  c.fillStyle=pal.tint(shade(col,.75));c.fillRect(x-.3*k,y-1.55*k,.6*k,.62*k);
  c.fillStyle=pal.tint(hel);c.beginPath();c.arc(x,y-1.75*k,.22*k,0,Math.PI*2);c.fill();
  if(front){c.fillStyle='#fff6c8';c.fillRect(x-.1*k,y-.95*k,.2*k,.12*k);}
  else if(tail){c.fillStyle='#ff3b30';c.fillRect(x-.1*k,y-.78*k,.2*k,.1*k);}
}
function drawNpc(c,o,pal){
  const s=spot(o.x,o.y);if(!s)return;
  const fx=o.axis==='x'?o.dir:0,fy=o.axis==='y'?o.dir:0,dot=fx*cam.ca+fy*cam.sa;
  rider(c,s.x,s.y,s.k,o.col,o.hel,dot<-.3,dot>.3,pal);
  if(o.honk>0&&s.z<45){c.fillStyle='#fff';c.font=`700 ${Math.max(9,.5*s.k)|0}px system-ui,sans-serif`;c.textAlign='center';c.fillText(tr('Bíp!'),s.x,s.y-2.2*s.k);}
}
function person(c,x,y,k,col,hat,t,wave){
  const leg=Math.sin(t*6)*.12*k;
  c.strokeStyle='#3a3530';c.lineWidth=Math.max(1,.13*k);c.beginPath();c.moveTo(x-.1*k,y-.8*k);c.lineTo(x-.1*k+leg,y);c.moveTo(x+.1*k,y-.8*k);c.lineTo(x+.1*k-leg,y);c.stroke();
  c.fillStyle=col;c.fillRect(x-.24*k,y-1.42*k,.48*k,.66*k);
  c.fillStyle='#e8c09a';c.beginPath();c.arc(x,y-1.6*k,.17*k,0,Math.PI*2);c.fill();
  if(hat){c.fillStyle='#e9d39a';c.beginPath();c.moveTo(x-.42*k,y-1.62*k);c.lineTo(x+.42*k,y-1.62*k);c.lineTo(x,y-1.98*k);c.closePath();c.fill();}
  else{c.fillStyle='#2e2622';c.beginPath();c.arc(x,y-1.66*k,.17*k,Math.PI,0);c.fill();}
  if(wave){const a=-1.2+Math.sin(t*7)*.5;c.strokeStyle=col;c.lineWidth=Math.max(1.5,.12*k);c.beginPath();c.moveTo(x+.22*k,y-1.32*k);c.lineTo(x+.22*k+Math.cos(a)*.6*k,y-1.32*k+Math.sin(a)*.6*k);c.stroke();
    c.fillStyle='#e8c09a';c.beginPath();c.arc(x+.22*k+Math.cos(a)*.66*k,y-1.32*k+Math.sin(a)*.66*k,.09*k,0,Math.PI*2);c.fill();}
}
function drawPed(c,o,pal){const s=spot(o.x,o.y);if(!s)return;person(c,s.x,s.y,s.k,pal.tint(o.col),o.hat,o.t,false);}
function drawWorks(c,p,pal){
  const s=spot(p.x,p.y);if(!s)return;const k=s.k;
  for(let n=-1;n<=1;n++){const x=s.x+n*1.1*k;c.fillStyle='#f28c28';c.fillRect(x-.45*k,s.y-1*k,.9*k,.22*k);c.fillStyle='#fff';c.fillRect(x-.45*k,s.y-.72*k,.9*k,.16*k);c.fillStyle=pal.tint('#555');c.fillRect(x-.4*k,s.y-.5*k,.08*k,.5*k);c.fillRect(x+.32*k,s.y-.5*k,.08*k,.5*k);}
  if(s.z<40){c.font=`${Math.max(10,.9*k)|0}px system-ui,sans-serif`;c.textAlign='center';c.fillText('🚧',s.x,s.y-1.4*k);}
}
function drawCustomer(c,p,z,pal,o){
  const s=spot(p.x,p.y);if(!s)return;const k=s.k;
  person(c,s.x,s.y,k,'#e0823a',false,S.t,true);
  // A bubble with what is waiting there, and a ▼ that can be seen from the far end of the street.
  const emo=o.useful?.[o.target]?.emoji||'👋';
  if(z<70){const fs=Math.max(12,.75*k);c.font=`${fs|0}px system-ui,sans-serif`;c.textAlign='center';c.textBaseline='middle';c.fillStyle='rgba(255,255,255,.92)';c.beginPath();c.arc(s.x,s.y-2.45*k,fs*.75,0,Math.PI*2);c.fill();c.fillStyle='#000';c.fillText(emo,s.x,s.y-2.45*k+1);}
  const m=Math.max(9,.5*k),y=s.y-Math.max(3.2*k,40)+Math.sin(S.t*4)*4;
  c.fillStyle='#ffcf3f';c.strokeStyle='#7a5200';c.lineWidth=1.5;c.beginPath();c.moveTo(s.x-m,y-m*1.2);c.lineTo(s.x+m,y-m*1.2);c.lineTo(s.x,y);c.closePath();c.fill();c.stroke();
}

/* ---------------------------------------------------------------- weather, headlight, the bike */
function rain(c,w,h,pal){
  const n=pal.storm?110:70;
  if(S.rain.length!==n){S.rain=[];for(let k=0;k<n;k++)S.rain.push([Math.random()*w,Math.random()*h,.6+Math.random()*.6]);}
  c.strokeStyle='rgba(220,230,245,.45)';c.lineWidth=1;c.beginPath();
  const lean=-S.steer*.3-.15;
  for(const d of S.rain){
    d[1]+=(14+S.v*.6)*d[2];d[0]+=lean*8*d[2];
    if(d[1]>h){d[1]=-10;d[0]=Math.random()*w;}if(d[0]<0)d[0]+=w;if(d[0]>w)d[0]-=w;
    c.moveTo(d[0],d[1]);c.lineTo(d[0]+lean*10*d[2],d[1]+12*d[2]);
  }
  c.stroke();
  c.fillStyle='rgba(120,130,150,.10)';c.fillRect(0,0,w,h);
}
function headlight(c,w,h,pal){
  c.globalCompositeOperation='lighter';
  const a=.16*pal.lamps,g=c.createRadialGradient(w/2,h*.78,10,w/2,h*.62,w*.6);g.addColorStop(0,`rgba(255,236,190,${a})`);g.addColorStop(1,'rgba(255,236,190,0)');
  c.fillStyle=g;c.beginPath();c.moveTo(w*.38,h*.86);c.lineTo(w*.62,h*.86);c.lineTo(w*.98,cam.hz+8);c.lineTo(w*.02,cam.hz+8);c.closePath();c.fill();
  c.globalCompositeOperation='source-over';
}
/** Handlebars, mirrors, the dashboard: drawn once per size into a bitmap, turned with the bar. */
function barsBitmap(w,h){
  const key=w+'x'+h+'@'+S.dpr;if(S.bars&&S.barsKey===key)return S.bars;
  const cv=document.createElement('canvas');cv.width=Math.round(w*S.dpr);cv.height=Math.round(h*.42*S.dpr);
  const c=cv.getContext('2d');c.scale(S.dpr,S.dpr);
  const H=h*.42,by=H*.72;   // bar line inside the bitmap
  // Mirrors on their stalks.
  for(const sx of [-1,1]){
    const mx=w/2+sx*w*.4,my=H*.16,rx=Math.max(20,w*.058),ry=Math.max(13,H*.1);
    c.strokeStyle='#2d3036';c.lineWidth=Math.max(3,w*.009);c.beginPath();c.moveTo(w/2+sx*w*.3,by-4);c.quadraticCurveTo(w/2+sx*w*.36,H*.45,mx-sx*rx*.3,my+ry*.8);c.stroke();
    c.fillStyle='#2b2e33';c.beginPath();c.ellipse(mx,my,rx+3,ry+3,sx*.08,0,Math.PI*2);c.fill();
    const g=c.createLinearGradient(0,my-ry,0,my+ry);g.addColorStop(0,'#c9dcef');g.addColorStop(.48,'#a8bfd6');g.addColorStop(.5,'#6d7178');g.addColorStop(1,'#55595f');
    c.fillStyle=g;c.beginPath();c.ellipse(mx,my,rx,ry,sx*.08,0,Math.PI*2);c.fill();
    c.fillStyle='rgba(255,255,255,.35)';c.beginPath();c.ellipse(mx-rx*.35,my-ry*.35,rx*.35,ry*.18,-.4,0,Math.PI*2);c.fill();
  }
  // Cowl and dashboard.
  c.fillStyle='#33363d';c.beginPath();c.moveTo(w*.2,H+2);c.bezierCurveTo(w*.26,H*.55,w*.74,H*.55,w*.8,H+2);c.closePath();c.fill();
  c.fillStyle='#e0823a';c.beginPath();c.moveTo(w*.2,H+2);c.bezierCurveTo(w*.24,H*.78,w*.3,H*.7,w*.36,H*.68);c.lineTo(w*.36,H*.74);c.bezierCurveTo(w*.3,H*.78,w*.26,H*.86,w*.25,H+2);c.closePath();c.fill();
  c.beginPath();c.moveTo(w*.8,H+2);c.bezierCurveTo(w*.76,H*.78,w*.7,H*.7,w*.64,H*.68);c.lineTo(w*.64,H*.74);c.bezierCurveTo(w*.7,H*.78,w*.74,H*.86,w*.75,H+2);c.closePath();c.fill();
  // The bar, out to the grips under the player's thumbs (the pedals sit there).
  c.strokeStyle='#3c4048';c.lineWidth=Math.max(7,w*.022);c.lineCap='round';c.beginPath();c.moveTo(-w*.02,by+8);c.quadraticCurveTo(w*.5,by-14,w*1.02,by+8);c.stroke();
  c.strokeStyle='#1d1f23';c.lineWidth=Math.max(10,w*.03);c.beginPath();c.moveTo(-w*.02,by+8);c.lineTo(w*.06,by+5);c.moveTo(w*1.02,by+8);c.lineTo(w*.94,by+5);c.stroke();
  // Speedometer face.
  const r=Math.max(20,Math.min(w*.07,H*.2)),cx=w/2,cy=H*.82;
  c.fillStyle='#1e2024';c.beginPath();c.arc(cx,cy,r+4,0,Math.PI*2);c.fill();
  c.fillStyle='#f6f2e8';c.beginPath();c.arc(cx,cy,r,0,Math.PI*2);c.fill();
  c.strokeStyle='#33363d';c.lineWidth=1.4;
  for(let k=0;k<=8;k++){const a=Math.PI*.8+k/8*Math.PI*1.4;c.beginPath();c.moveTo(cx+Math.cos(a)*r*.78,cy+Math.sin(a)*r*.78);c.lineTo(cx+Math.cos(a)*r*.94,cy+Math.sin(a)*r*.94);c.stroke();}
  S.bars={cv,H,cx,cy,r};S.barsKey=key;
  return S.bars;
}
function bars(c,w,h,pal,o){
  const bm=barsBitmap(w,h),top=h-bm.H,turn=still()?0:S.steer*.045;
  c.save();c.translate(w/2,h+bm.H*.6);c.rotate(turn);c.translate(-w/2,-(h+bm.H*.6));
  c.drawImage(bm.cv,0,top,w,bm.H);
  // Needle and the fuel bar under it.
  const cx=bm.cx,cy=top+bm.cy,r=bm.r,f=clamp(S.v/VMAX,0,1),a=Math.PI*.8+f*Math.PI*1.4;
  c.strokeStyle='#d9442b';c.lineWidth=2.2;c.beginPath();c.moveTo(cx,cy);c.lineTo(cx+Math.cos(a)*r*.8,cy+Math.sin(a)*r*.8);c.stroke();
  c.fillStyle='#33363d';c.beginPath();c.arc(cx,cy,2.6,0,Math.PI*2);c.fill();
  const fuel=clamp(Number(o.fuel)||0,0,100)/100,fw=r*1.3;
  c.fillStyle='#1e2024';c.fillRect(cx-fw/2-1,cy+r*.36-1,fw+2,6);
  c.fillStyle=fuel<.2?'#e2533c':fuel<.35?'#e7a23a':'#46b06a';c.fillRect(cx-fw/2,cy+r*.36,fw*fuel,4);
  c.restore();
  if(pal.dark>.35){c.fillStyle=`rgba(10,14,30,${(pal.dark-.35)*.5})`;c.fillRect(0,top,w,bm.H);}
}

/* ---------------------------------------------------------------- HUD: the way to go, a tiny map */
function goal(o,W){
  const T=W.marks[o.target],b=S.goal.querySelector('b'),s=S.goal.querySelector('small'),ar=S.goal.querySelector('.dd-arrow');
  if(!T||T.id===S.at){S.goal.hidden=true;return;}
  S.goal.hidden=false;
  const g=T.gate,d=Math.abs(S.x-g.x)+Math.abs(S.y-(g.y-2)),wp=waypoint(S.x,S.y,g);
  const name=`${T.emoji} ${tr(T.name)}`;if(b.textContent!==name)b.textContent=name;
  const blocks=d<16?tr('Dừng xe trước cửa'):`${Math.max(1,Math.round(d/B*2)/2).toLocaleString('vi-VN')} ${tr('ô')}`;
  if(s.textContent!==blocks)s.textContent=blocks;
  const ang=Math.atan2(wp.y-S.y,wp.x-S.x)-S.a;
  ar.style.transform=`rotate(${ang}rad)`;   // ⬆ = straight on
}
function mini(o,W){
  const c=S.mc,cw=S.mini.width,ch=S.mini.height,k=Math.min(cw/(GX+1.2),ch/(GY+1.2)),ox=(cw-GX*k)/2,oy=(ch-GY*k)/2;
  c.setTransform(1,0,0,1,0,0);c.clearRect(0,0,cw,ch);
  c.fillStyle='rgba(24,28,36,.82)';c.fillRect(0,0,cw,ch);
  c.strokeStyle='rgba(230,226,214,.55)';c.lineWidth=Math.max(1.5,k*.16);c.beginPath();
  for(let i=0;i<=GX;i++){c.moveTo(ox+i*k,oy);c.lineTo(ox+i*k,oy+GY*k);}
  for(let j=0;j<=GY;j++){c.moveTo(ox,oy+j*k);c.lineTo(ox+GX*k,oy+j*k);}
  c.stroke();
  for(const L of Object.values(W.marks)){
    const x=ox+L.gate.x/B*k,y=oy+(L.gate.y/B-.18)*k,tgt=L.id===o.target,use=o.useful?.[L.id];
    if(!tgt&&!use)continue;
    c.fillStyle=tgt?'#ffcf3f':'#8fc3ff';c.beginPath();c.arc(x,y,tgt?k*(.2+.06*Math.sin(S.t*5)):k*.12,0,Math.PI*2);c.fill();
  }
  const x=ox+S.x/B*k,y=oy+S.y/B*k;
  c.save();c.translate(x,y);c.rotate(S.a);c.fillStyle='#ff6b4a';c.beginPath();c.moveTo(k*.3,0);c.lineTo(-k*.18,k*.18);c.lineTo(-k*.18,-k*.18);c.closePath();c.fill();c.restore();
}
