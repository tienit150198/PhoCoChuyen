/** 🛵 Tự lái: the delivery career's ride, shown in a soft isometric neighbourhood by default.
 * The rider's-seat view remains selectable in the stage. Loaded by careers/delivery.js only while a leg is to be
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
 * always. Traffic-light crossings use server-issued tokens and receive server-priced receipts. Stopping at an ordinary house says
 * "Không phải nhà này"; nothing is sent.
 *
 * Both views share the same physics. delivery_isometric.js caches the illustrated ground and building sprites.
 * The rider's-seat view uses flat ground and box houses projected from the rider's eye (a tiny software 3D
 * of quads clipped at the near plane), painted far to near; people, scooters, lamps and signs are billboards; the
 * handlebars, mirrors and the speedometer are one cached bitmap. Frames are measured: a phone that cannot keep up
 * first draws fewer pixels, then opts.slow() switches the career to "Đi nhanh". */
import {t as tr} from '../v4/i18n.js';
import {lightAt} from '../v4/dayclock.js';

import {B,onRoad,gateOf,waypoint,roadRoute,navigation,mapTransform,onLeg} from './delivery_navigation.js';
import {joystickAxes,nextSpeed,nextSteer,motionSign,holdPointer} from './delivery_controls.js';
import {signalState} from '../v4/traffic.js';
import {stageFullscreen} from './delivery_fullscreen.js';
import {drawStreetPerson,drawStreetTree,drawStreetScooter} from './delivery_sprites.js';
import {drawHouseFacade,drawLandmarkFacade} from './delivery_architecture.js';
import {createIsometricRenderer,needsDrivingFrames} from './delivery_isometric.js';
export {B,onRoad,gateOf,waypoint} from './delivery_navigation.js';
const HW=5,SW=3,FRONT=HW+SW;       // half the road, the pavement, the house fronts from the street's middle
const EYE=1.35,NEAR=.35,FAR=190;
const VMAX=15;
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
const HOUSE=['#d8c9ad','#e8dec9','#cbb29a','#c0d1d2','#d9bab0','#d4d0b7','#c7c6cf','#eee5d5','#becbb8','#d8bd9f'];
const SHIRT=['#e0823a','#3b7dd8','#d94f6b','#3f9f6b','#8a5bb8','#d9b23b','#3aa6b9'];

/* ---------------------------------------------------------------- tiny helpers */
const clamp=(v,a,b)=>v<a?a:v>b?b:v;
function rng(seed){let s=seed>>>0||1;return ()=>{s^=s<<13;s>>>=0;s^=s>>17;s^=s<<5;s>>>=0;return s/4294967296;};}
const hex=h=>[parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)];
const css=([r,g,b],a=1)=>a<1?`rgba(${r|0},${g|0},${b|0},${a})`:`rgb(${r|0},${g|0},${b|0})`;
const mix=(a,b,t)=>a.map((v,i)=>v+(b[i]-v)*t);
const ESC=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

/* ---------------------------------------------------------------- the world (built once per set of stops) */
export function buildWorld(nodes){
  const R=rng(20261003),houses=[],cells=new Map(),lamps=[],trees=[],signs=[],lights=[],marks={},gardens=[],props=[];
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
        // Small open courtyards on selected north facades expose the green block interior.
        if(inX&&inY&&face==='N'&&k===1&&(cx+cy)%2===0){
          gardens.push({...b,col:'#abc49b'});trees.push({x:(b.x0+b.x1)/2,y:b.y0+3.7,r:1.5});
        }else{houses.push(b);cellAdd(cx,cy,b);}
      }
    }
  }
  // The town's edge: a house across the end of every street, so no street runs out into nothing.
  const cap=(x0,x1,y0,y1,face,cx,cy)=>cellAdd(cx,cy,{x0,x1,y0,y1,zb:0,h:[6.5,8.5,9.5][Math.floor(R()*3)],col:HOUSE[Math.floor(R()*HOUSE.length)],
    face,k:'house',no:0,shop:false,awn:null,street:'',win:2});
  for(let j=0;j<=GY;j++){const cy=clamp(j,0,GY-1);cap(-FRONT-8,-FRONT,j*B-FRONT,j*B+FRONT,'E',-1,cy);cap(GX*B+FRONT,GX*B+FRONT+8,j*B-FRONT,j*B+FRONT,'W',GX,cy);}
  for(let i=0;i<=GX;i++){const cx=clamp(i,0,GX-1);cap(i*B-FRONT,i*B+FRONT,-FRONT-8,-FRONT,'S',cx,-1);cap(i*B-FRONT,i*B+FRONT,GY*B+FRONT,GY*B+FRONT+8,'N',cx,GY);}
  // A tree stands on the pavement between two junctions, never out in a crossing street.
  const tree=(x,y,r,along)=>{const d=along-Math.round(along/B)*B;if(Math.abs(d)>HW+2.5)trees.push({x,y,r});};
  // Street furniture: lamps and trees along the pavements, a name sign and (on some corners) lights at junctions.
  for(let i=0;i<=GX;i++)for(let y=10;y<GY*B;y+=20){if(Math.abs(y%B)<9||Math.abs(y%B)>B-9)continue;const s=(y/20|0)%2?1:-1;lamps.push({x:i*B+s*(HW+.6),y});if(R()<.6){const ty=y+(y%B<B/2?1:-1)*(5+R()*4);tree(i*B-s*(HW+1.4),ty,1.2+R()*.6,ty);}}
  for(let j=0;j<=GY;j++)for(let x=10;x<GX*B;x+=20){if(Math.abs(x%B)<9||Math.abs(x%B)>B-9)continue;const s=(x/20|0)%2?1:-1;lamps.push({x,y:j*B+s*(HW+.6)});if(R()<.6){const tx=x+(x%B<B/2?1:-1)*(5+R()*4);tree(tx,j*B-s*(HW+1.4),1.2+R()*.6,tx);}}
  const LIT=new Set(['1,1','3,1','5,1','1,3','3,3','5,3','3,2','2,2','4,2']);
  for(let i=0;i<=GX;i++)for(let j=0;j<=GY;j++){
    signs.push({x:i*B-HW-1.2,y:j*B+HW+1.2,v:STREETS_V[i],h:STREETS_H[j]});
    if(LIT.has(i+','+j))lights.push({i,j,x:i*B+HW+.8,y:j*B-HW-.8,x2:i*B-HW-.8,y2:j*B+HW+.8,off:((i*7+j*3)%16)});
  }
  // Low planters sit between crossings on the pavement, outside the riding surface.
  for(let cx=0;cx<GX;cx++)for(let cy=0;cy<=GY;cy++)if((cx+cy)%2===0){
    props.push({x0:cx*B+24,x1:cx*B+26,y0:cy*B+6,y1:cy*B+7.2,zb:0,h:.6,col:'#b67f5a',face:'N',k:'garden'});
  }
  return {houses,cells,lamps,trees,signs,lights,marks,gardens,props,lit:LIT};
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
const S={el:null,cv:null,c:null,mini:null,mc:null,goal:null,say:null,slot:null,world:null,nodesKey:'',opts:null,view:globalThis.document?.documentElement?.dataset?.game==='classic'?'firstperson':'isometric',iso:null,idle:0,
  at:null,x:0,y:0,a:0,v:0,steer:0,roll:0,keys:{},btn:{},joy:{steer:0,drive:0},raf:0,last:0,t:0,w:0,h:0,dpr:1,bars:null,barsKey:'',
  pal:null,palKey:'',still:0,stopDone:false,sending:false,sayT:0,shake:0,lastRed:0,lastBump:0,inBox:'',
  npcs:[],peds:[],rain:[],frames:[],cost:[],perf:{n:0,sum:0,bad:0,skip:40},visible:true,hinted:false,miniT:0,goalT:0,fail:false};
globalThis.__dlDrive={
  stats:()=>{const f=[...S.frames].sort((a,b)=>a-b),n=f.length;const d=[...S.cost].sort((a,b)=>a-b),m=d.length;return {n,avg:n?f.reduce((s,v)=>s+v,0)/n:0,p50:n?f[n>>1]:0,p95:n?f[Math.min(n-1,Math.floor(n*.95))]:0,draw:m?d.reduce((s,v)=>s+v,0)/m:0,draw95:m?d[Math.min(m-1,Math.floor(m*.95))]:0,dpr:S.dpr,w:S.w,h:S.h};},
  state:()=>{const T=S.opts&&S.world?.marks[S.opts.target];return {x:S.x,y:S.y,a:S.a,v:S.v,at:S.at,target:S.opts?.target||null,sending:S.sending,
    gate:T?{x:T.gate.x,y:T.gate.y,gy:T.gate.gy}:null,wp:T?waypoint(S.x,S.y,T.gate):null,running:!!(S.raf||S.idle),view:S.view,B,HW};},
  reset:()=>{S.frames=[];S.cost=[];},
  look:o=>{S.dbg=o||null;if(S.opts&&o)Object.assign(S.opts,o);S.pal=null;},   // checks only: {minute, weather}
};

const ARROW='<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M12 3 4 13h5v8h6v-8h5z" fill="currentColor"/></svg>';
function build(){
  const el=document.createElement('div');el.className='dd-stage'+(S.view==='isometric'?' dd-isometric':'');
  el.innerHTML=`<canvas class="dd-cv" tabindex="0" role="img" aria-label="${ESC(tr('Xe máy: lái tới nhà có người vẫy tay'))}"></canvas>
    <div class="dd-goal" aria-live="polite"><i class="dd-arrow" aria-hidden="true">${ARROW}</i><span><b></b><small></small><span class="dd-nav-detail"></span><progress class="dd-parking" max="1" value="0" hidden aria-label="${ESC(tr('Tiến độ dừng xe'))}"></progress></span></div>
    <button type="button" class="dd-map-toggle" aria-label="${ESC(tr('Mở bản đồ'))}" aria-haspopup="dialog" aria-expanded="false"><canvas class="dd-mini" aria-hidden="true"></canvas><span>${ESC(tr('Bản đồ'))}</span></button>
    <div class="dd-tools"><button type="button" class="dd-view-toggle" aria-label="${ESC(tr('Đổi góc nhìn lái xe'))}" aria-pressed="${S.view==='isometric'}">${ESC(tr(S.view==='isometric'?'Góc nhìn người lái':'Góc nhìn 2.5D'))}</button><button type="button" class="dd-full-toggle" aria-pressed="false">⛶ ${ESC(tr('Toàn màn hình'))}</button><button type="button" class="dd-help-toggle" aria-haspopup="dialog" aria-expanded="false">${ESC(tr('Cách lái'))}</button></div>
    <section class="dd-map-panel" role="dialog" aria-modal="true" aria-label="${ESC(tr('Bản đồ khu phố'))}" hidden>
      <div class="dd-map-heading"><h3>${ESC(tr('Bản đồ khu phố'))}</h3><button type="button" class="dd-map-close">${ESC(tr('Tiếp tục lái'))}</button></div>
      <div class="dd-map-zoom"><button type="button" data-map-zoom="out" aria-label="${ESC(tr('Thu nhỏ'))}">−</button><output>100%</output><button type="button" data-map-zoom="in" aria-label="${ESC(tr('Phóng to'))}">+</button><button type="button" data-map-zoom="me">${ESC(tr('Về xe'))}</button><button type="button" data-map-zoom="all">${ESC(tr('Toàn phố'))}</button></div>
      <canvas class="dd-map-canvas" role="img" aria-label="${ESC(tr('Lộ trình theo đường phố tới điểm giao'))}"></canvas>
      <div class="dd-map-legend"><span>▲ ${ESC(tr('Bạn đang ở đây'))}</span><span>● ${ESC(tr('Điểm đến'))}</span><span>━ ${ESC(tr('Lộ trình'))}</span></div>
      <p class="dd-map-caption"></p><p>${ESC(tr('Kéo bản đồ để xem · Xe đã dừng'))}</p>
    </section>
    <section class="dd-help-panel" role="dialog" aria-modal="true" aria-label="${ESC(tr('Cách lái'))}" hidden>
      <div class="dd-map-heading"><h3>${ESC(tr('Cách lái'))}</h3><button type="button" class="dd-help-close">${ESC(tr('Tiếp tục lái'))}</button></div>
      <p>${ESC(tr('W / ↑: tiến · S / ↓: lùi · Space: phanh'))}</p><p>${ESC(tr('A / ←: rẽ trái · D / →: rẽ phải'))}</p>
      <p>${ESC(tr('Kéo núm tròn tự do: lên để tiến, xuống để lùi, kéo chéo để vừa chạy vừa rẽ. Kéo xa tâm để tăng tốc; thả tay để giảm tốc.'))}</p>
      <p>${ESC(tr('Rẽ ở giữa ngã tư. Thả ga và giữ phanh trong ô vàng trước cửa có người vẫy tay.'))}</p>
      <p>${ESC(tr('Xe đã dừng · Esc để tiếp tục'))}</p>
    </section>
    <div class="dd-signal" role="status" hidden><i aria-hidden="true">●</i><span><b></b><small></small></span><strong></strong></div>
    <div class="dd-say" role="status" aria-live="polite" hidden></div>
    <div class="dd-pads">
      <div class="dd-pad-l"><div class="dd-stick-wrap"><div class="dd-stick" tabindex="0" role="group" aria-label="${ESC(tr('Joystick lái xe. Kéo tự do để tiến, lùi và rẽ; hoặc dùng W A S D.'))}"><span class="dd-stick-knob" aria-hidden="true"></span></div><small>${ESC(tr('Kéo để lái'))}</small></div></div>
      <div class="dd-pad-r"><button type="button" class="dd-btn dd-brake" data-dd="d"><span aria-hidden="true">✋</span><small>${ESC(tr('Phanh'))}</small></button><button type="button" class="dd-btn dd-gas" data-dd="u">${ARROW}<small>${ESC(tr('Ga'))}</small></button></div>
    </div>`;
  S.el=el;S.cv=el.querySelector('.dd-cv');S.mini=el.querySelector('.dd-mini');S.goal=el.querySelector('.dd-goal');S.say=el.querySelector('.dd-say');
  S.c=S.cv.getContext('2d',{alpha:false});S.mc=S.mini.getContext('2d');
  if(!S.c)throw new Error('no 2d canvas');
  S.wake=wake;
  el.querySelector('.dd-view-toggle').addEventListener('click',()=>setView(S.view==='isometric'?'firstperson':'isometric'));
  const fullButton=el.querySelector('.dd-full-toggle');
  S.full=stageFullscreen(el,fullButton,{reset:()=>{clearInput();S.v=0;},resize:size,text:tr});
  fullButton.addEventListener('click',()=>S.full.toggle());
  const stick=el.querySelector('.dd-stick'),knob=stick.querySelector('.dd-stick-knob');
  S.resetControls=[];
  S.resetStick=holdPointer(stick,{enabled:()=>!S.overlay,start:()=>{
    S.joy={steer:0,drive:0};stick.classList.add('on');stick.focus({preventScroll:true});S.wake?.();
  },move:(e,origin)=>{
    const radius=stick.getBoundingClientRect().width*.3,dx=e.clientX-origin.x,dy=e.clientY-origin.y;
    const scale=Math.min(1,radius/(Math.hypot(dx,dy)||1));
    S.joy=joystickAxes(dx/radius,dy/radius);
    S.wake?.();
    knob.style.transform=`translate(${dx*scale}px,${dy*scale}px)`;
  },end:()=>{S.joy={steer:0,drive:0};stick.classList.remove('on');knob.style.transform='';}});
  // Pedals: held while the finger is on them (each its own pointer, so steer + gas together works).
  for(const b of el.querySelectorAll('[data-dd]')){
    const k=b.dataset.dd;
    S.resetControls.push(holdPointer(b,{enabled:()=>!S.overlay,
      start:()=>{S.btn[k]=true;b.classList.add('on');S.wake?.();},end:()=>{S.btn[k]=false;b.classList.remove('on');}}));
  }
  for(const name of ['map','help']){
    el.querySelector('.dd-'+name+'-toggle').addEventListener('click',()=>panel(name));
    el.querySelector('.dd-'+name+'-close').addEventListener('click',()=>panel(null));
  }
  S.mapZoom=1;S.mapCenter={x:120,y:80};
  for(const button of el.querySelectorAll('[data-map-zoom]'))button.addEventListener('click',()=>{
    const action=button.dataset.mapZoom;
    if(action==='all'){S.mapZoom=1;S.mapCenter={x:120,y:80};}
    else if(action==='me'){S.mapZoom=Math.max(1.5,S.mapZoom);S.mapCenter={x:S.x,y:S.y};}
    else {if(S.mapZoom===1)S.mapCenter={x:S.x,y:S.y};S.mapZoom=clamp(S.mapZoom*(action==='in'?1.5:1/1.5),1,3);}
    expandedMap();
  });
  const map=el.querySelector('.dd-map-canvas');let panStart;
  S.resetMap=holdPointer(map,{enabled:()=>S.overlay==='map',start:()=>{panStart={...S.mapCenter};},move:(e,origin)=>{
    const ratio=map.width/map.getBoundingClientRect().width,k=S.mapView.scale;
    S.mapCenter={x:panStart.x-(e.clientX-origin.x)*ratio/k,y:panStart.y-(e.clientY-origin.y)*ratio/k};expandedMap();
  }});
  new ResizeObserver(()=>size()).observe(el);
  try{new IntersectionObserver(es=>{S.visible=es.some(e=>e.isIntersecting);if(S.visible)wake();}).observe(el);}catch{/* always drawn */}
  document.addEventListener('keydown',key,true);document.addEventListener('keyup',key,true);
  addEventListener('blur',()=>{clearInput();S.v=0;});
  document.addEventListener('visibilitychange',()=>{clearInput();S.v=0;if(!document.hidden)wake();});
  setupDrivingProfile();
}
// Opt-in, DOM-readable diagnostics for measuring the actual mounted driving view.
// No panel, timer or additional sample collection exists during normal play.
function setupDrivingProfile(){
  if(new URLSearchParams(globalThis.location?.search||'').get('drivingProfile')!=='1')return;
  const panel=document.createElement('div'),output=document.createElement('output'),reset=document.createElement('button');
  panel.style.cssText='position:absolute;left:10px;top:85px;z-index:20;max-width:calc(100% - 20px);padding:6px;background:#fff9e8ed;color:#342b20;font:10px monospace;pointer-events:auto';
  output.dataset.drivingPerformance='';output.style.cssText='display:block;white-space:pre-wrap;overflow-wrap:anywhere';
  output.textContent='Driving performance: waiting for frames';reset.type='button';reset.textContent='Đo lại hiệu năng';
  reset.addEventListener('click',()=>{globalThis.__dlDrive.reset();S.profile.last=-Infinity;output.textContent='Driving performance: collecting';});
  panel.append(output,reset);S.el.append(panel);S.profile={output,last:-Infinity};
}
function drivingProfileFrame(now){
  if(now-S.profile.last<1000)return;
  S.profile.last=now;
  const stats=globalThis.__dlDrive.stats(),snapshot={...stats,fps:stats.avg?1000/stats.avg:0,view:S.view,speed:S.v,...S.iso?.stats()};
  S.profile.output.textContent=JSON.stringify(snapshot,(_key,value)=>typeof value==='number'?Math.round(value*100)/100:value);
}
function setView(view){
  S.view=view==='firstperson'?'firstperson':'isometric';
  clearInput();S.v=0;S.roll=0;S.perf.skip=30;
  S.el.classList.toggle('dd-isometric',S.view==='isometric');
  const button=S.el.querySelector('.dd-view-toggle');
  button.setAttribute('aria-pressed',String(S.view==='isometric'));
  button.textContent=tr(S.view==='isometric'?'Góc nhìn người lái':'Góc nhìn 2.5D');
  S.cv.focus({preventScroll:true});wake();
}
function resetStick(){
  S.resetStick?.();S.joy={steer:0,drive:0};
}
function clearInput(){S.keys={};S.btn={};S.steer=0;resetStick();S.resetMap?.();for(const reset of S.resetControls||[])reset();for(const b of S.el?.querySelectorAll('[data-dd]')||[])b.classList.remove('on');}
const KEYS={ArrowLeft:'l',KeyA:'l',ArrowRight:'r',KeyD:'r',ArrowUp:'u',KeyW:'u',ArrowDown:'back',KeyS:'back',Space:'d'};
function key(e){
  // Key ownership ends even if focus moved to a toolbar or a dialog while held.
  if(e.type==='keyup'&&KEYS[e.code]){S.keys[KEYS[e.code]]=false;return;}
  if(S.overlay&&live()){
    if(e.type==='keydown'&&e.code==='Escape'){e.preventDefault();e.stopPropagation();panel(null);}
    else if(e.type==='keydown'&&e.code==='Tab'){
      const targets=[...S.el.querySelector('.dd-'+S.overlay+'-panel').querySelectorAll('button:not([disabled])')],at=targets.indexOf(document.activeElement);
      if(at<0||e.shiftKey&&at===0||!e.shiftKey&&at===targets.length-1){e.preventDefault();targets[e.shiftKey?targets.length-1:0]?.focus();}
    }else if(KEYS[e.code])e.preventDefault();
    return;
  }
  if(e.type==='keydown'&&e.code==='Escape'&&S.full?.active){e.preventDefault();e.stopPropagation();S.full.exit();return;}
  if(e.type==='keydown'&&e.code==='Tab'&&S.full?.active){
    const targets=[...S.el.querySelectorAll('button:not([disabled]),[tabindex="0"]')].filter(el=>el.getClientRects().length&&!el.closest('[hidden],[inert]'));
    const at=targets.indexOf(document.activeElement);
    if(targets.length&&(at<0||e.shiftKey&&at===0||!e.shiftKey&&at===targets.length-1)){
      e.preventDefault();targets[e.shiftKey?targets.length-1:0].focus();
    }
  }
  const k=KEYS[e.code];if(!k||!live())return;
  if(e.target?.closest?.('input,textarea,select,[contenteditable="true"]'))return;
  const dlg=e.target?.closest?.('dialog');if(dlg&&!dlg.contains(S.el))return;   // a question on top of the sheet
  if(e.ctrlKey||e.metaKey||e.altKey)return;
  if(e.code==='Space'&&e.target?.closest?.('button:not([data-dd])'))return;
  e.preventDefault();S.keys[k]=e.type==='keydown';S.wake?.();
}
function panel(name){
  const previous=document.activeElement;
  S.resetMap?.();S.overlay=name;S.v=0;S.steer=0;clearInput();
  for(const b of S.el.querySelectorAll('[data-dd]'))b.classList.remove('on');
  for(const kind of ['map','help']){
    S.el.querySelector('.dd-'+kind+'-panel').hidden=name!==kind;
    S.el.querySelector('.dd-'+kind+'-toggle').setAttribute('aria-expanded',String(name===kind));
  }
  for(const child of S.el.children)if(!child.classList.contains('dd-map-panel')&&!child.classList.contains('dd-help-panel'))child.inert=Boolean(name);
  if(name){S.panelReturn=previous;if(name==='map')expandedMap();S.el.querySelector('.dd-'+name+'-close').focus();}
  else {S.last=performance.now();S.perf.skip=30;(S.panelReturn?.isConnected?S.panelReturn:S.cv).focus();wake();}
}
const live=()=>!!(S.el?.isConnected&&S.el.closest('dialog[open],#sheet[open]')&&!document.hidden);

/** Put the stage into `slot` (after a render of the work sheet) with the current state of the shift. */
export function mount(slot,opts){
  if(S.fail)return false;
  try{if(!S.el)build();}catch(error){S.fail=true;console.warn('Tự lái: không vẽ được',error);opts.fail?.();return false;}
  if(S.dbg)Object.assign(opts,S.dbg);
  S.opts=opts;S.slot=slot;
  if(S.lightTarget!==opts.target||S.lightFrom!==opts.at){S.lightTarget=opts.target;S.lightFrom=opts.at;S.lightKey='';S.lightChallenge=null;S.lightPending=false;S.lightDenied=new Set();}
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
export function park(){if(S.full?.active)S.full.exit();if(S.overlay)panel(null);if(S.raf){cancelAnimationFrame(S.raf);S.raf=0;}if(S.idle){clearTimeout(S.idle);S.idle=0;}clearInput();S.v=0;}

/** Start of a leg: the scooter at the door of the stop the courier is at, facing the way to go. */
function place(at,target){
  const W=S.world,from=W.marks[at],to=W.marks[target];
  S.at=at;S.v=0;S.steer=0;S.stopDone=true;S.sending=false;S.still=0;S.inBox='';
  clearInput();
  if(from){S.x=from.gate.x;S.y=from.gate.y-2.2;}else{S.x=B;S.y=2*B;}
  S.stopX=S.x;S.stopY=S.y;
  const wp=to?waypoint(S.x,S.y,to.gate):null;
  S.a=wp&&wp.x<S.x-1?Math.PI:0;
  seedTraffic(true);
}

function size(){
  if(!S.el?.isConnected||!S.el.clientWidth)return;   // detached while the sheet re-renders: keep the last size
  const w=Math.max(200,S.el.clientWidth);
  const expanded=S.full?.active;
  const h=expanded?Math.max(180,Math.round(S.el.clientHeight)):Math.round(clamp(w*(w<560?1.04:.62),360,Math.min(480,Math.max(360,innerHeight*.6))));
  if(!expanded)S.el.style.height=h+'px';
  const lv=S.perf.level||0,dpr=Math.min(devicePixelRatio||1,lv?1:1.5)*(lv>=2?.75:1);
  S.w=w;S.h=h;S.dpr=dpr;
  S.cv.width=Math.round(w*dpr);S.cv.height=Math.round(h*dpr);
  const mw=Math.round(clamp(w*.24,78,120)),mh=Math.round(mw*.74);
  S.mini.style.width=mw+'px';S.mini.style.height=mh+'px';S.mini.width=Math.round(mw*Math.min(2,devicePixelRatio||1));S.mini.height=Math.round(mh*Math.min(2,devicePixelRatio||1));
  S.barsKey='';if(S.overlay==='map')expandedMap();wake();
}
function wake(){if(S.idle){clearTimeout(S.idle);S.idle=0;}if(!S.raf&&S.el?.isConnected){S.last=performance.now();S.raf=requestAnimationFrame(frame);}}
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
    const pos=R()*max,o={axis,line,side,pos,dir:R()<.5?1:-1,sp:.8+R()*.6,col:SHIRT[Math.floor(R()*SHIRT.length)],hat:R()<.25,t:R()*9,variant:Math.floor(R()*12)};
    pedPos(o);
    const d=Math.hypot(o.x-S.x,o.y-S.y);
    if(d>12&&d<130)return o;
  }
  return {axis:'x',line:0,side:1,pos:0,dir:1,sp:1,col:SHIRT[1],hat:false,t:0,x:0,y:0};
}
function pedPos(o){const off=o.side*(HW+1.7);if(o.axis==='x'){o.x=o.pos;o.y=o.line*B+off;}else{o.y=o.pos;o.x=o.line*B+off;}}
function lightState(L,axis,t){const p=(t+L.off)%16;return axis==='y'?(p<6?'g':p<8?'y':'r'):(p<8?'r':p<14?'g':'y');}
const signalClock=()=>S.opts?.now?.()??S.t;
function lightAtJunction(i,j){const W=S.world;return W.lit.has(i+','+j)?W.lights.find(l=>l.i===i&&l.j===j):null;}

function moveTraffic(dt){
  const t=signalClock();
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
  const keyboardSteer=(k.r?1:0)-(k.l?1:0),keyboardDrive=((k.u||b.u)?1:0)-(k.back?1:0);
  return {steer:keyboardSteer||S.joy.steer,drive:keyboardDrive||S.joy.drive,brake:!!(k.d||b.d)};
}
function ride(dt){
  const inp=input(),o=S.opts,rain=o.weather==='rain',vmax=VMAX*(rain?.85:1)*clamp(Number(o.driveFactor)||1,1,1.6);
  S.lightHold=false;signalAhead(motionSign(S.v,inp.drive));
  if(S.sending||S.lightHold){inp.drive=0;inp.brake=true;}
  S.v=nextSpeed(S.v,inp,dt,vmax);
  S.steer=nextSteer(S.steer,inp.steer,dt);
  const speed=Math.abs(S.v),rate=1.75*(.5+.5*Math.min(1,speed/6));
  S.a+=S.steer*rate*dt*(S.v<0?-1:1);
  // Let go of the bar: it settles on the street's direction (phones: no fiddly straightening).
  if(!inp.steer&&speed>.8){const q=Math.round(S.a/(Math.PI/2))*(Math.PI/2),d=q-S.a;if(Math.abs(d)<.55)S.a+=Math.sign(d)*Math.min(Math.abs(d),1.1*dt);}
  S.a=((S.a+Math.PI)%(2*Math.PI)+2*Math.PI)%(2*Math.PI)-Math.PI;
  const nx=S.x+Math.cos(S.a)*S.v*dt,ny=S.y+Math.sin(S.a)*S.v*dt;
  if(onRoad(nx,ny)){S.x=nx;S.y=ny;}
  else if(onRoad(nx,S.y)){S.x=nx;S.v*=Math.pow(.6,dt);}
  else if(onRoad(S.x,ny)){S.y=ny;S.v*=Math.pow(.6,dt);}
  else if(speed>.5){bump(tr('Ối, lề đường!'));S.v*=.25;}
  // Scooters: a soft bump, no harm done.
  for(const n of S.npcs)if(Math.abs(n.x-S.x)<1.5&&Math.abs(n.y-S.y)<1.5&&Math.abs(S.v)>1){bump(tr('Ối! Chạy chậm thôi'));S.v*=.3;n.v=0;n.honk=1.5;}
  // Only entering the junction crosses its stop line. Waiting in front sends no crossing.
  const i=Math.round(S.x/B),j=Math.round(S.y/B),inBox=Math.abs(S.x-i*B)<HW&&Math.abs(S.y-j*B)<HW?i+','+j:'';
  if(inBox&&inBox!==S.inBox){
    const L=lightAtJunction(i,j),axis=Math.abs(Math.cos(S.a))>Math.abs(Math.sin(S.a))?'x':'y';
    if(L&&Math.abs(S.v)>.1&&o.cross){
      const key=`${o.target}:${i},${j}:${axis}`;
      if(S.lightKey===key&&S.lightChallenge&&!S.lightCrossed){
        S.lightCrossed=true;S.sending=true;
        Promise.resolve(o.cross(S.lightChallenge.token)).then(r=>{S.sending=false;if(r?.message)say(tr(r.message),4500);}).catch(()=>{S.sending=false;});
      }
    }
  }
  S.inBox=inBox;
  stops(dt);
}
function signalAhead(travel=1){
 const o=S.opts;if(!o.signal)return;
 const axis=Math.abs(Math.cos(S.a))>Math.abs(Math.sin(S.a))?'x':'y',dir=((axis==='x'?Math.cos(S.a):Math.sin(S.a))>=0?1:-1)*travel;
 const pos=axis==='x'?S.x:S.y,line=Math.round((axis==='x'?S.y:S.x)/B),next=(dir>0?Math.ceil((pos+.01)/B):Math.floor((pos-.01)/B));
 const i=axis==='x'?next:line,j=axis==='y'?next:line,L=lightAtJunction(i,j),gap=Math.abs(next*B-pos),box=S.el.querySelector('.dd-signal');
 // Off this leg's corridor the server refuses the checkpoint (dl_signal): scenery only, never ask, never hold.
 const key=`${o.target}:${i},${j}:${axis}`;
 if(!L||gap>23||!onLeg(o.nodes,o.at,o.target,i,j)||S.lightDenied?.has(key)){box.hidden=true;return;}
 box.hidden=false;
 const state=signalState(signalClock(),L.off,axis);
 box.dataset.color=state.color;
 const label=tr(state.grace?'Vừa chuyển đỏ · giữ phanh':{red:'Đèn đỏ · giữ phanh',yellow:'Đèn vàng · giảm tốc',green:'Đèn xanh · đi tiếp'}[state.color]);
 const detail=`${Math.max(0,Math.round(gap-HW))} m · ${tr('Vượt đỏ: 12 xu')}`;
 for(const [selector,text] of [['b',label],['small',detail],['strong',state.left+'s']]){const item=box.querySelector(selector);if(item.textContent!==text)item.textContent=text;}
 if((key!==S.lightKey||(!S.lightChallenge&&S.t>=(S.lightRetry||0)))&&!S.lightPending){
  S.lightPending=true;S.lightRetry=S.t+2;S.lightKey=key;S.lightChallenge=null;S.lightCrossed=false;S.lightAsked=S.t;
  // A refusal (or no answer) frees this junction: the rider must never be parked in front of it for good.
  const deny=()=>{S.lightPending=false;if(S.lightKey===key&&!S.lightChallenge)S.lightDenied?.add(key);};
  Promise.resolve(o.signal(i,j,axis)).then(r=>{S.lightPending=false;if(S.lightKey===key)S.lightChallenge=r?.traffic?.challenge||null;if(!S.lightChallenge)deny();}).catch(deny);
 }
 // A slow connection must not carry the rider through an unissued checkpoint, but only for a few seconds.
 if(gap<HW+1.5&&!S.lightChallenge&&S.lightPending&&S.t-(S.lightAsked||0)<4){S.lightHold=true;S.v=0;S.btn.u=false;S.keys.u=false;}
 else if(gap<HW+1.5&&!S.lightChallenge&&S.lightPending)S.lightDenied?.add(key);
}
function bump(text){if(S.t-S.lastBump>1.4){S.lastBump=S.t;say(text,1600);}if(!still())S.shake=.25;}

/** Standing still in front of a door: arrive (a stop), or a friendly word (an ordinary house, a stop with nothing to do). */
function stops(dt){
  // A light joystick touch can leave a bay without ever reaching 1.4 m/s.
  if(S.stopDone&&Math.hypot(S.x-S.stopX,S.y-S.stopY)>2)S.stopDone=false;
  if(Math.abs(S.v)>1.4){S.stopDone=false;S.still=0;return;}
  if(Math.abs(S.v)>.6||S.sending){S.still=0;return;}
  if(S.stopDone)return;
  S.still+=dt;if(S.still<.35)return;
  const W=S.world,o=S.opts;
  for(const L of Object.values(W.marks)){
    const g=L.gate;
    if(Math.abs(S.x-g.x)<6.5&&S.y>=g.y-HW-1&&S.y<=g.y+HW+1){
      S.stopDone=true;S.stopX=S.x;S.stopY=S.y;
      if(L.id===S.at)return;
      if(L.id!==o.target&&!o.useful?.[L.id]){say(tr('Ở đây chưa có việc'));return;}
      S.sending=true;say(`${L.emoji} ${tr('Tới rồi!')}`,1800);
      Promise.resolve(o.arrive?.(L.id)).then(r=>{S.sending=false;if(r&&r.say)say(r.say,3200);}).catch(()=>{S.sending=false;});
      return;
    }
  }
  if(S.still<.6)return;
  S.stopDone=true;S.stopX=S.x;S.stopY=S.y;
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
  if(S.overlay)return;
  const moving=needsDrivingFrames(S);
  S.t+=dt;
  ride(dt);if(S.view==='firstperson'||moving)moveTraffic(dt);
  if(S.visible&&S.w){const t0=performance.now();draw(now);S.cost.push(performance.now()-t0);if(S.cost.length>600)S.cost.shift();if(S.view==='firstperson'||moving)measure(ms);}
  if(S.sayT&&now>S.sayT){S.sayT=0;S.say.hidden=true;}
  if(S.profile&&S.visible)drivingProfileFrame(now);
  // Downscaling inside measure() calls size(), which may already have queued the next frame.
  if(S.fail||S.raf)return;
  if(S.view==='firstperson'||needsDrivingFrames(S))S.raf=requestAnimationFrame(frame);
  else S.idle=setTimeout(()=>{S.idle=0;wake();},1000);
}
/** Frame times; a phone that keeps missing them draws fewer pixels, then switches to "Đi nhanh". */
function measure(ms){
  if(S.perf.skip>0){S.perf.skip--;return;}
  S.frames.push(ms);if(S.frames.length>600)S.frames.shift();
  const P=S.perf;P.n++;P.sum+=ms;
  if(P.n<60)return;
  const avg=P.sum/P.n;P.n=0;P.sum=0;
  // Under ~24 frames a second for a few seconds: draw fewer pixels (twice); still that slow for ~8 s more: "Đi nhanh".
  const lv=P.level||0;
  if(avg>(lv>=2?50:42))P.bad++;else P.bad=0;
  if(P.bad<(lv>=2?3:2))return;
  P.bad=0;P.skip=30;
  if(lv<2){P.level=lv+1;size();return;}
  S.fail=true;park();S.opts?.slow?.();
}

function draw(now){
  const c=S.c,w=S.w,h=S.h,o=S.opts,W=S.world;
  c.setTransform(S.dpr,0,0,S.dpr,0,0);
  if(S.view==='isometric'){
    if(!S.iso)S.iso=createIsometricRenderer({onAsset:()=>{if(live()&&!S.overlay)wake();}});
    S.iso.draw(c,S,W,o,signalClock());goal(o,W);mini(o,W);return;
  }
  const pal=palette();
  // Camera: the rider's eye, a slight lean into the turn and a bob with speed.
  const calm=still(),lean=calm?0:-S.steer*.035*Math.min(1,Math.abs(S.v)/7);
  S.roll+=(lean-S.roll)*.15;
  const bob=calm?0:Math.sin(S.t*9)*.6*Math.min(1,Math.abs(S.v)/VMAX),sh=S.shake>0?(S.shake-=1/60,(Math.random()-.5)*6):0;
  cam.x=S.x;cam.y=S.y;cam.ca=Math.cos(S.a);cam.sa=Math.sin(S.a);cam.F=Math.min(w*.78,h*1.25);cam.cx=w/2+sh;cam.hz=h*.42+bob;
  c.save();
  if(S.roll){c.translate(w/2,h*.6);c.rotate(S.roll);c.translate(-w/2,-h*.6);}
  // Sky, far town, ground.
  const g=c.createLinearGradient(0,-40,0,cam.hz);g.addColorStop(0,pal.top);g.addColorStop(1,pal.bot);
  c.fillStyle=g;c.fillRect(-40,-40,w+80,cam.hz+41);
  skyDetails(c,w,pal);
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
function skyDetails(c,w,pal){
  c.save();
  const daylight=1-pal.lamps;
  if(!pal.rain&&daylight>.15){
    const sx=w*(.72-Math.sin(S.a)*.3),sy=cam.hz*.42,r=Math.max(25,w*.055);
    const glow=c.createRadialGradient(sx,sy,1,sx,sy,r*2.7);
    glow.addColorStop(0,`rgba(255,228,179,${.32*daylight})`);glow.addColorStop(1,'rgba(255,228,179,0)');
    c.fillStyle=glow;c.fillRect(sx-r*3,sy-r*3,r*6,r*6);
  }
  // Fixed formations rotate with the view; they do not jitter between frames.
  const span=w*2,offset=S.a/(Math.PI*2)*span;
  for(let i=0;i<7;i++){
    const x=((i*span/7-offset)%span+span)%span-w*.35,y=cam.hz*(.2+(i%3)*.16),s=w*(.035+(i%2)*.015);
    c.fillStyle=`rgba(239,237,226,${(pal.rain?.09:.18)*daylight})`;
    c.beginPath();c.ellipse(x,y,s*2.4,s*.27,0,0,Math.PI*2);c.ellipse(x-s*.6,y-s*.12,s,s*.37,0,0,Math.PI*2);c.ellipse(x+s*.45,y-s*.21,s*.8,s*.46,0,0,Math.PI*2);c.fill();
  }
  c.restore();
}
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
  const side=pal.tint('#c6bfae'),road=pal.tint(pal.rain?'#485258':'#64696a'),line=pal.tint('#e2dfd2'),yel=pal.tint('#d0b66a');
  for(const g of W.gardens){
    if(Math.abs((g.x0+g.x1)/2-S.x)+Math.abs((g.y0+g.y1)/2-S.y)>100)continue;
    gquad(c,g.x0,g.y0,g.x1,g.y1,pal.tint('#9fba8a'));
    gquad(c,g.x0+2,g.y0,g.x0+3,g.y1,pal.tint('#d6c5a4'));
  }
  // Pavements, then asphalt over them (junctions stay asphalt).
  for(let i=0;i<=GX;i++)gquad(c,i*B-FRONT,-FRONT,i*B+FRONT,GY*B+FRONT,side);
  for(let j=0;j<=GY;j++)gquad(c,-FRONT,j*B-FRONT,GX*B+FRONT,j*B+FRONT,side);
  for(let i=0;i<=GX;i++)gquad(c,i*B-HW,-HW,i*B+HW,GY*B+HW,road);
  for(let j=0;j<=GY;j++)gquad(c,-HW,j*B-HW,GX*B+HW,j*B+HW,road);
  // Pale kerbs outline each block without adding geometry to the streets.
  for(let x=0;x<GX;x++)for(let y=0;y<GY;y++){
    const x0=x*B+HW,y0=y*B+HW,x1=(x+1)*B-HW,y1=(y+1)*B-HW;
    if(Math.abs((x0+x1)/2-S.x)+Math.abs((y0+y1)/2-S.y)>100)continue;
    const curb=pal.tint('#ded5c2');
    gquad(c,x0,y0,x1,y0+.2,curb);gquad(c,x0,y1-.2,x1,y1,curb);
    gquad(c,x0,y0,x0+.2,y1,curb);gquad(c,x1-.2,y0,x1,y1,curb);
    // Recessed gutters and paving joints give the street a human scale.
    if(Math.abs((x0+x1)/2-S.x)+Math.abs((y0+y1)/2-S.y)<50){
      const seam=pal.tint('#aaa99c'),gutter=pal.tint('#535d5c');
      gquad(c,x0-.2,y0,x0,y1,gutter);gquad(c,x1,y0,x1+.2,y1,gutter);
      gquad(c,x0,y0-.2,x1,y0,gutter);gquad(c,x0,y1,x1,y1+.2,gutter);
      for(let n=1;n<12;n++){
        const u=x0+n*2.5,v=y0+n*2.5;
        gquad(c,u,y0+.25,u+.035,y0+2.8,seam);gquad(c,u,y1-2.8,u+.035,y1-.25,seam);
        gquad(c,x0+.25,v,x0+2.8,v+.035,seam);gquad(c,x1-2.8,v,x1-.25,v+.035,seam);
      }
      // Shallow building shade sits on pavement rather than darkening the whole road.
      gquad(c,x0+.4,y0+1.75,x1-.4,y0+2.95,'rgba(38,48,44,.12)');
      gquad(c,x0+1.7,y0+.4,x0+2.95,y1-.4,'rgba(38,48,44,.10)');
      const dx=x0+4,dy=y1-.35;
      gquad(c,dx,dy,dx+1.3,dy+.28,gutter);
      for(let n=0;n<5;n++)gquad(c,dx+.12+n*.23,dy,dx+.18+n*.23,dy+.28,seam);
    }
  }
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
  if(T&&T.id!==S.at){const g=T.gate,a=still()?.5:.35+.25*Math.sin(S.t*4);gquad(c,g.x-5.5,g.y-HW+.3,g.x+5.5,g.y-.4,`rgba(255,206,64,${a})`);}
}

/** Everything standing up within sight, with its depth. */
function collect(W,o){
  const out=[],lim=FAR,ca=cam.ca,sa=cam.sa;
  const zOf=(x,y)=>(x-cam.x)*ca+(y-cam.y)*sa,xOf=(x,y)=>-(x-cam.x)*sa+(y-cam.y)*ca;
  const viewHalf=S.w/(2*cam.F)+.12;
  const seen=(x,y,r)=>{const z=zOf(x,y);if(z<-r||z>lim+r)return null;const xr=xOf(x,y);if(Math.abs(xr)>Math.max(0,z)*viewHalf+r+6)return null;return z;};
  const cx0=Math.floor((S.x-lim)/B),cx1=Math.floor((S.x+lim)/B),cy0=Math.floor((S.y-lim)/B),cy1=Math.floor((S.y+lim)/B);
  for(let cx=Math.max(-1,cx0);cx<=Math.min(GX,cx1);cx++)for(let cy=Math.max(-1,cy0);cy<=Math.min(GY,cy1);cy++){
    const list=W.cells.get(cx+','+cy);if(!list)continue;
    if(seen(cx*B+B/2,cy*B+B/2,B*.8)===null)continue;
    for(const b of list){const z=seen((b.x0+b.x1)/2,(b.y0+b.y1)/2,8);if(z!==null)out.push({z,k:'box',o:b});}
  }
  for(const p of W.props){const z=seen((p.x0+p.x1)/2,(p.y0+p.y1)/2,2);if(z!==null&&z<65)out.push({z,k:'box',o:p});}
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
  const wall=color=>{
    if(z>65)return tint(color);
    const base=spot((x0+x1)/2,(y0+y1)/2,zb),top=spot((x0+x1)/2,(y0+y1)/2,zt);
    if(!base||!top)return tint(color);
    const wash=c.createLinearGradient(0,top.y,0,base.y);
    wash.addColorStop(0,tint(shade(color,1.04)));wash.addColorStop(.7,tint(color));wash.addColorStop(1,tint(shade(color,.87)));
    return wash;
  };
  const lightWall=wall(col),sideWall=wall(dark);
  // Walls facing the rider (back faces culled), a top when below the eye, the underside of a canopy above it.
  if(cam.y>y1)poly(c,[P(x0,y1,zb),P(x1,y1,zb),P(x1,y1,zt),P(x0,y1,zt)],lightWall);
  if(cam.y<y0)poly(c,[P(x1,y0,zb),P(x0,y0,zb),P(x0,y0,zt),P(x1,y0,zt)],lightWall);
  if(cam.x>x1)poly(c,[P(x1,y1,zb),P(x1,y0,zb),P(x1,y0,zt),P(x1,y1,zt)],sideWall);
  if(cam.x<x0)poly(c,[P(x0,y0,zb),P(x0,y1,zb),P(x0,y1,zt),P(x0,y0,zt)],sideWall);
  if(zt<EYE)poly(c,[P(x0,y0,zt),P(x1,y0,zt),P(x1,y1,zt),P(x0,y1,zt)],tint(shade(col,1.08)));
  if(zb>EYE)poly(c,[P(x0,y0,zb),P(x1,y0,zb),P(x1,y1,zb),P(x0,y1,zb)],tint(shade(col,.62)));
  if(!faceSeen(b)||z>95)return;
  if(b.k==='garden')return;
  if(b.k==='house')houseFront(c,b,z,pal);else markFront(c,b,z,pal);
}
const shadeMemo=new Map();
function shade(h,f){const k=h+f;let v=shadeMemo.get(k);if(!v){const r=hex(h).map(x=>clamp(Math.round(x*f),0,255));v='#'+r.map(x=>x.toString(16).padStart(2,'0')).join('');shadeMemo.set(k,v);}return v;}
function windowCol(pal){return pal.lamps>.45?`rgb(255,${Math.round(205+20*pal.lamps)},${Math.round(120+30*pal.lamps)})`:pal.tint('#7fa4bd');}
const facadeHelpers={fquad,label,shade,windowCol};
function houseFront(c,b,z,pal){drawHouseFacade(c,b,z,pal,facadeHelpers);}
function markFront(c,b,z,pal){drawLandmarkFacade(c,b,z,pal,facadeHelpers);}
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
const treePaints=new Map();let treePaintPalette='';
function drawTree(c,p,pal){
  const s=spot(p.x,p.y);if(!s)return;
  const variant=Math.abs(Math.round(p.x*13+p.y*7))%3;
  // The foliage is static: paint once per palette instead of tracing hundreds of
  // curves for every distant tree on every frame. Close trees retain vector detail.
  if(s.k>120){drawStreetTree(c,{x:s.x,y:s.y,k:s.k,r:p.r,variant,tint:pal.tint});return;}
  if(treePaintPalette!==S.palKey){treePaintPalette=S.palKey;treePaints.clear();}
  const radius=Math.round(p.r*4)/4,key=variant+':'+radius;
  let paint=treePaints.get(key);
  if(!paint){
    const k=80,canvas=document.createElement('canvas');
    canvas.width=Math.ceil((radius*2.5+.5)*k);canvas.height=Math.ceil((3.3+radius*1.3+.4)*k);
    const x=canvas.width/2,y=canvas.height-24,ctx=canvas.getContext('2d');
    if(!ctx){drawStreetTree(c,{x:s.x,y:s.y,k:s.k,r:p.r,variant,tint:pal.tint});return;}
    drawStreetTree(ctx,{x,y,k,r:radius,variant,tint:pal.tint});
    paint={canvas,x,y,k};treePaints.set(key,paint);
  }
  const scale=s.k/paint.k;
  c.drawImage(paint.canvas,s.x-paint.x*scale,s.y-paint.y*scale,paint.canvas.width*scale,paint.canvas.height*scale);
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
  const axis=Math.abs(cam.ca)>Math.abs(cam.sa)?'x':'y',st=lightState(L,axis,signalClock()),r=.17*k;
  const lamp=(n,on,col)=>{c.fillStyle=on?col:'#3a3f46';c.beginPath();c.arc(s.x,s.y-(4.65-n*.44)*k,r,0,Math.PI*2);c.fill();};
  lamp(0,st==='r','#ff4a3d');lamp(1,st==='y','#ffc23d');lamp(2,st==='g','#38d26b');
}
function drawNpc(c,o,pal){
  const s=spot(o.x,o.y);if(!s)return;
  const fx=o.axis==='x'?o.dir:0,fy=o.axis==='y'?o.dir:0,dot=fx*cam.ca+fy*cam.sa;
  drawStreetScooter(c,{x:s.x,y:s.y,k:s.k,col:o.col,helmet:o.hel,front:dot<-.3,tail:dot>.3,tint:pal.tint,variant:o.line});
  if(o.honk>0&&s.z<45){c.fillStyle='#fff';c.font=`700 ${Math.max(9,.5*s.k)|0}px system-ui,sans-serif`;c.textAlign='center';c.fillText(tr('Bíp!'),s.x,s.y-2.2*s.k);}
}
function drawPed(c,o,pal){
  const s=spot(o.x,o.y);if(!s)return;
  const fx=o.axis==='x'?o.dir:0,fy=o.axis==='y'?o.dir:0;
  drawStreetPerson(c,{x:s.x,y:s.y,k:s.k,col:o.col,hat:o.hat,t:o.t,wave:false,variant:o.variant||0,facing:-(fx*cam.ca+fy*cam.sa),calm:still(),tint:pal.tint});
}
function drawWorks(c,p,pal){
  const s=spot(p.x,p.y);if(!s)return;const k=s.k;
  for(let n=-1;n<=1;n++){const x=s.x+n*1.1*k;c.fillStyle='#f28c28';c.fillRect(x-.45*k,s.y-1*k,.9*k,.22*k);c.fillStyle='#fff';c.fillRect(x-.45*k,s.y-.72*k,.9*k,.16*k);c.fillStyle=pal.tint('#555');c.fillRect(x-.4*k,s.y-.5*k,.08*k,.5*k);c.fillRect(x+.32*k,s.y-.5*k,.08*k,.5*k);}
  if(s.z<40){c.font=`${Math.max(10,.9*k)|0}px system-ui,sans-serif`;c.textAlign='center';c.fillText('🚧',s.x,s.y-1.4*k);}
}
function drawCustomer(c,p,z,pal,o){
  const s=spot(p.x,p.y);if(!s)return;const k=s.k;
  drawStreetPerson(c,{x:s.x,y:s.y,k,col:'#bd7c4c',hat:false,t:S.t,wave:true,variant:2,facing:1,calm:still(),tint:pal.tint});
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
  const cx=bm.cx,cy=top+bm.cy,r=bm.r,f=clamp(Math.abs(S.v)/VMAX,0,1),a=Math.PI*.8+f*Math.PI*1.4;
  c.strokeStyle='#d9442b';c.lineWidth=2.2;c.beginPath();c.moveTo(cx,cy);c.lineTo(cx+Math.cos(a)*r*.8,cy+Math.sin(a)*r*.8);c.stroke();
  c.fillStyle='#33363d';c.beginPath();c.arc(cx,cy,2.6,0,Math.PI*2);c.fill();
  const fuel=clamp(Number(o.fuel)||0,0,100)/100,fw=r*1.3;
  c.fillStyle='#1e2024';c.fillRect(cx-fw/2-1,cy+r*.36-1,fw+2,6);
  c.fillStyle=fuel<.2?'#e2533c':fuel<.35?'#e7a23a':'#46b06a';c.fillRect(cx-fw/2,cy+r*.36,fw*fuel,4);
  c.restore();
  if(pal.dark>.35){c.fillStyle=`rgba(10,14,30,${(pal.dark-.35)*.5})`;c.fillRect(0,top,w,bm.H);}
}

/* ---------------------------------------------------------------- HUD: the way to go, a tiny map */
function routeNow(o,W){
  const T=W.marks[o.target];return T?roadRoute(S.x,S.y,T.gate):[];
}
function goal(o,W){
  const T=W.marks[o.target],b=S.goal.querySelector('b'),s=S.goal.querySelector('small'),ar=S.goal.querySelector('.dd-arrow');
  if(!T||T.id===S.at){S.goal.hidden=true;return;}
  S.goal.hidden=false;
  const route=routeNow(o,W),nav=navigation(route,S.a,T.gate),detail=S.goal.querySelector('.dd-nav-detail'),parking=S.goal.querySelector('.dd-parking');
  // opts.label(id): the page's short name for a stop (clean layout: "🏢 Mây Xanh"), else the full name.
  const name=`${T.emoji} ${o.label?.(o.target)||tr(T.name)}`;if(b.textContent!==name)b.textContent=name;
  let cue=tr({left:'Rẽ trái',right:'Rẽ phải',uturn:'Quay đầu ở ngã tư',straight:'Đi thẳng',arrive:'Giữ phanh để dừng xe'}[nav.cue]);
  if(nav.cue!=='arrive'&&nav.cue!=='straight')cue+=` · ${Math.round(nav.turnDistance)} m`;
  const arriving=nav.cue==='arrive';
  if(arriving&&S.sending&&S.stopDone)cue=tr('Tới rồi!');
  if(s.textContent!==cue)s.textContent=cue;
  const info=S.v<-.1?tr('Đang lùi · giữ phanh để dừng'):arriving?tr('Dừng trong ô vàng trước người vẫy tay'):`${Math.round(nav.distance)} m${o.terse?'':` · ${tr('theo đường phố')}`}`;
  if(detail.textContent!==info)detail.textContent=info;
  parking.hidden=!arriving;parking.value=S.sending?1:Math.abs(S.v)<=.6&&!S.stopDone?clamp(S.still/.35,0,1):0;
  ar.style.transform=`rotate(${{left:-90,right:90,uturn:180,straight:0,arrive:0}[nav.cue]}deg)`;
}
const DISTRICTS=[['Khu dân cư','#d1dfcf'],['Khu dịch vụ','#ead3ac'],['Khu nhà vườn','#bfd9cd']];
function district(x){return x<2?0:x<4?1:2;}
function drawMapGround(c,W,cw,ch,view,large,pixels){
  const k=view.scale,ox=view.ox,oy=view.oy;
  const X=x=>ox+x*k,Y=y=>oy+y*k;
  c.fillStyle='#f6efde';c.fillRect(0,0,cw,ch);
  // Every coloured parcel is inside a road block; footprints use the actual world geometry.
  for(let x=0;x<GX;x++)for(let y=0;y<GY;y++){
    c.fillStyle=DISTRICTS[district(x,y)][1];c.fillRect(X(x*B+HW),Y(y*B+HW),(B-HW*2)*k,(B-HW*2)*k);
  }
  for(const list of W.cells.values())for(const b of list){
    if(b.x0<0||b.x1>GX*B||b.y0<0||b.y1>GY*B)continue;
    c.fillStyle=b.L?'#bd9b77':'#a9b5a3';c.fillRect(X(b.x0),Y(b.y0),(b.x1-b.x0)*k,(b.y1-b.y0)*k);
  }
  for(const g of W.gardens){c.fillStyle='#759b66';c.fillRect(X(g.x0),Y(g.y0),(g.x1-g.x0)*k,(g.y1-g.y0)*k);}
  c.strokeStyle='#fffaf0';c.lineWidth=HW*2*k;c.beginPath();
  for(let i=0;i<=GX;i++){c.moveTo(X(i*B),Y(-6));c.lineTo(X(i*B),Y(GY*B+6));}
  for(let j=0;j<=GY;j++){c.moveTo(X(-6),Y(j*B));c.lineTo(X(GX*B+6),Y(j*B));}c.stroke();
  if(large){
    c.strokeStyle='#dfd4bd';c.lineWidth=Math.max(1,k*.35);c.setLineDash([3*k,4*k]);c.stroke();c.setLineDash([]);
    c.font=`600 ${12*pixels}px system-ui`;c.textAlign='center';c.textBaseline='middle';
    for(const [idx,x,y] of [[0,40,20],[1,120,140],[2,200,100]]){
      const label=tr(DISTRICTS[idx][0]),w=c.measureText(label).width;
      c.fillStyle='rgba(255,250,239,.9)';c.fillRect(X(x)-w/2-5,Y(y)-9,w+10,18);c.fillStyle='#405746';c.fillText(label,X(x),Y(y));
    }
  }
}
function drawMap(cv,o,W,large=false){
  const c=cv.getContext('2d'),cw=cv.width,ch=cv.height,pad=large?cw*.075:cw*.10;
  const view=mapTransform(cw,ch,large?S.mapZoom:1,large?S.mapCenter:undefined),k=view.scale,ox=view.ox,oy=view.oy;
  if(large){S.mapView=view;S.mapCenter=view.center;}
  const pixels=large?Math.min(2,devicePixelRatio||1):1;
  const X=x=>ox+x*k,Y=y=>oy+y*k;
  c.setTransform(1,0,0,1,0,0);c.clearRect(0,0,cw,ch);
  if(large)drawMapGround(c,W,cw,ch,view,true,pixels);
  else{
    // Streets and footprints do not move on the minimap. Keep live navigation
    // above one native-resolution bitmap instead of repainting the whole town.
    let ground=S.miniGround;
    if(!ground||ground.world!==W||ground.cv.width!==cw||ground.cv.height!==ch){
      const floor=document.createElement('canvas');floor.width=cw;floor.height=ch;
      drawMapGround(floor.getContext('2d'),W,cw,ch,view,false,1);
      ground=S.miniGround={world:W,cv:floor};
    }
    c.drawImage(ground.cv,0,0);
  }
  const route=routeNow(o,W);
  if(route.length>1){
    c.lineJoin='round';c.lineCap='round';c.beginPath();route.forEach((p,i)=>i?c.lineTo(X(p.x),Y(p.y)):c.moveTo(X(p.x),Y(p.y)));
    c.strokeStyle='#fff7dc';c.lineWidth=Math.max(4,5*k);c.stroke();c.strokeStyle='#b85b28';c.lineWidth=Math.max(2,2.6*k);c.stroke();
  }
  for(const L of Object.values(W.marks)){
    const tgt=L.id===o.target,at=L.id===S.at,use=o.useful?.[L.id];if(!large&&!tgt&&!at&&!use)continue;
    const x=X(L.gate.x),y=Y(L.gate.y-2),r=Math.max(large?5:2.5,k*(tgt?3:1.8));
    c.fillStyle=tgt?'#e5a02b':at?'#367f72':'#818d99';c.strokeStyle='#fff9e8';c.lineWidth=large?2:1.5;
    c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.fill();c.stroke();
    if(large){
      c.font=`${17*pixels}px system-ui`;c.textAlign='center';c.fillText(L.emoji,x,y-10*pixels);
      if(tgt||at||S.mapZoom>=2){
        const label=tr(L.node.label||L.name);c.font=`700 ${12*pixels}px system-ui`;
        const width=c.measureText(label).width;c.fillStyle='#fffaf0';c.fillRect(x-width/2-3*pixels,y+8*pixels,width+6*pixels,17*pixels);
        c.fillStyle='#243d37';c.fillText(label,x,y+17*pixels);
      }
    }
  }
  const x=X(S.x),y=Y(S.y),r=Math.max(large?7:4,3.7*k);
  c.save();c.translate(x,y);c.rotate(S.a);c.fillStyle='#276d66';c.strokeStyle='#fff';c.lineWidth=1.5;c.beginPath();c.moveTo(r,0);c.lineTo(-r*.7,r*.7);c.lineTo(-r*.45,0);c.lineTo(-r*.7,-r*.7);c.closePath();c.fill();c.stroke();c.restore();
  c.fillStyle='#36554b';c.font=`700 ${Math.max(10,cw*(large?.021:.07))}px system-ui`;c.textAlign='right';c.textBaseline='top';c.fillText('↑ N',cw-pad*.4,pad*.2);
}
function mini(o,W){drawMap(S.mini,o,W);}
function expandedMap(){
  const cv=S.el.querySelector('.dd-map-canvas'),w=Math.max(260,S.el.clientWidth-40),dpr=Math.min(2,devicePixelRatio||1);
  cv.width=Math.round(w*dpr);cv.height=Math.round(w*.76*dpr);drawMap(cv,S.opts,S.world,true);
  S.el.querySelector('.dd-map-zoom output').textContent=Math.round(S.mapZoom*100)+'%';
  S.el.querySelector('[data-map-zoom="out"]').disabled=S.mapZoom<=1;
  S.el.querySelector('[data-map-zoom="in"]').disabled=S.mapZoom>=3;
  const T=S.world.marks[S.opts.target],route=routeNow(S.opts,S.world);
  S.el.querySelector('.dd-map-caption').textContent=T?`${T.emoji} ${tr(T.name)} · ${Math.round(navigation(route,S.a,T.gate).distance)} m · ${tr('theo đường phố')}`:'';
}
