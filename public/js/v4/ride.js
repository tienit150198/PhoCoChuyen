/** 🛵 Đi xe quanh phố (owner 03/10, góp ý #122 "Mua xe rồi mà chưa có cái gì sử dụng đến xe"): a player who owns a
 * road vehicle (game/garage.py: the two-wheelers and the cars; never a boat or a plane) rides it on the walkable
 * maps instead of walking: the town (./town-walk.js), the fair (./fair-walk.js, two-wheelers only: a car waits at
 * the gate) and the strolls (./walk.js, two-wheelers only). Free: no fuel, no xu, nothing sent to the game server
 * (the garage's once-a-day ride out stays the garage's own); only the live presence carries what someone rides.
 *   choice(state,content,{two})  the vehicle ridden now ({id, kind, name, emoji, hex, plate}) or null (walking):
 *                                 a vehicle the save owns and that is not broken, the toggle not set to walking;
 *                                 the garage's "đang đi" first, else the first owned in catalogue order
 *   next(...)                     the toggle: each owned vehicle in turn, then walking, then the first again
 *                                 (remembered in this browser: localStorage mnl.ride / mnl.ride.pick)
 *   wire(v) / fromWire(r,content) what the live presence carries ({v: id, c: paint id}), and back
 *   drawRide(c,o)                 the vehicle with the character seated on it (or parked, empty), wheels turning;
 *                                 the body and the rider are one cached bitmap per look, vehicle, side and size,
 *                                 a frame adds only the shadow and the two wheels (cheap phones)
 *   steer(r,dx,dist,dt)           the side it faces, the turn (a short squash through the middle), the wheels' angle
 * The art faces left (the front at -x) in character units (the character is about 140 tall, origin at its feet). */
import {paintPlayer,CANVAS} from './look.js';
import {R,E,L,P,bloom} from '../scenes/kit.js';

/** Garage vehicle id → how it is drawn. An id this build does not know: by its group (bike: a scooter, car: a small car). */
export const KINDS={xe_dap:'bicycle',xe_dap_dien:'ebike',xe_so:'cub',xe_ga:'scooter',o_to_mini:'mini',o_to_suv:'suv',mui_tran:'convertible',sieu_xe:'super'};
const BY_GROUP={bike:'scooter',car:'mini'};
export const TWO=new Set(['bicycle','ebike','cub','scooter']);
/** How much faster than walking. */
export const FAST={bicycle:1.45,ebike:1.6,cub:1.8,scooter:1.8,mini:2,suv:2,convertible:2.1,super:2.3};
const PREF='mnl.ride',PICK='mnl.ride.pick',PAINT_ID=/^[a-z0-9_]{1,24}$/;
const TURN_S=.24;

/* ------------------------------------------------------------ which vehicle */
const own=(o,k)=>typeof k==='string'&&Object.prototype.hasOwnProperty.call(o,k)?o[k]:null;   // never '__proto__' & co.
const kindOf=(id,group)=>own(KINDS,id)||own(BY_GROUP,group)||null;
/* ---- 💑 the husband's / wife's vehicles (GET /api/garage/spouse, game/couple.py): theirs to ride too ---- */
let SP=null,SP_AT=0,SP_GO=null;
/** {pid (their live id), name, cars} or null (not married, a guest, an older server, not loaded yet). */
export const spouse=()=>SP;
/** Load it (at most once a minute; `force`: now). Never throws. */
export function loadSpouse(api,force=false){
  if(!api?.json)return Promise.resolve(SP);
  if(SP_GO)return SP_GO;
  if(!force&&SP_AT&&Date.now()-SP_AT<60000)return Promise.resolve(SP);
  SP_GO=api.json('/api/garage/spouse').then(d=>{const q=d?.spouse;
    SP=q&&typeof q.pid==='string'&&/^[0-9a-f]{16}$/.test(q.pid)&&Array.isArray(q.cars)?{pid:q.pid,name:String(q.name||'').slice(0,24)||'Người ấy',cars:q.cars,ride:q.ride}:null;return SP;})
    .catch(()=>SP).finally(()=>{SP_AT=Date.now();SP_GO=null;});
  return SP_GO;
}
/** For tests: set the spouse as the server would send it. */
export function setSpouse(q){SP=q||null;SP_AT=Date.now();}
function entries(cars,cat,two,owner){
  const out=[];
  for(const c of cars){
    if(!c||typeof c.id!=='string'||c.broken!=null)continue;
    const it=(cat.vehicles||[]).find(v=>v.id===c.id),kind=it&&kindOf(it.id,it.group);
    if(!kind||(two&&!TWO.has(kind)))continue;
    const paint=(cat.paints||[]).find(p=>p.id===c.color)||(cat.paints||[]).find(p=>p.id===it.paint);
    out.push({id:it.id,key:owner?`${owner.pid}:${it.id}`:it.id,kind,name:it.name||'',emoji:it.emoji||'🛵',hex:/^#[0-9a-f]{6}$/i.test(paint?.hex||'')?paint.hex:'#d9534f',
      paint:paint?.id||'',plate:typeof c.plate==='string'?c.plate:'',...(owner?{o:owner.pid,owner:owner.name}:{})});
  }
  return out;
}
/** Every vehicle the save can ride now (owned, a road vehicle, not broken), the garage's "đang đi" first, then the
 * spouse's ("Xe của <tên>", their own "đang đi" first). */
export function options(state,content,{two=false}={}){
  const J=state?.journey,g=J?.story?J.garage:null,cat=content?.journey?.garage;
  if(!J?.story||!cat)return [];
  const out=g&&Array.isArray(g.cars)?entries(g.cars,cat,two,null):[];
  const main=out.findIndex(v=>v.id===g?.ride);
  if(main>0)out.unshift(...out.splice(main,1));
  if(SP){const theirs=entries(SP.cars,cat,two,SP),m=theirs.findIndex(v=>v.id===SP.ride);if(m>0)theirs.unshift(...theirs.splice(m,1));out.push(...theirs);}
  return out;
}
function read(){
  try{return {on:localStorage.getItem(PREF)!=='0',pick:localStorage.getItem(PICK)||null};}catch{return {on:true,pick:null};}
}
function write(on,pick){
  try{localStorage.setItem(PREF,on?'1':'0');if(pick)localStorage.setItem(PICK,pick);}catch{/* storage blocked: this visit only */}
  MEM.on=on;if(pick)MEM.pick=pick;
}
const MEM={on:null,pick:null};   // when storage is blocked the choice still holds for this visit
function pref(){const p=read();return {on:MEM.on===null?p.on:MEM.on,pick:MEM.pick||p.pick};}
/** Owns something to ride here (the toggle shows only then). */
export const canRide=(state,content,o)=>options(state,content,o).length>0;
/** The vehicle ridden now, or null (walking). */
export function choice(state,content,o){
  const list=options(state,content,o);if(!list.length)return null;
  const p=pref();if(!p.on)return null;
  return list.find(v=>v.key===p.pick)||list[0];
}
/** The toggle: the next owned vehicle, then walking, then the first again. Returns the new choice. */
export function next(state,content,o){
  const list=options(state,content,o);if(!list.length)return null;
  const now=choice(state,content,o),i=now?list.findIndex(v=>v.key===now.key):-1;
  const v=i<0?list[0]:list[i+1]||null;
  write(Boolean(v),v?.key||null);
  return v;
}
/** The toggle's words: what the player does now (a tap changes it). */
export const label=v=>v?v.owner?`${v.emoji} Xe của ${v.owner}`:`${v.emoji} Đi xe`:'🚶 Đi bộ';
export const speedOf=v=>v?FAST[v.kind]||1.5:1;
/** For the live presence: {v, c} (the plate stays the owner's own: game/garage.py). */
export const wire=v=>v?{v:v.id,c:v.paint||'',...(v.o?{o:v.o}:{})}:null;
/** Someone else's vehicle from the live presence (null: walking, or one this build cannot draw). */
export function fromWire(r,content){
  if(!r||typeof r!=='object'||typeof r.v!=='string')return null;
  const cat=content?.journey?.garage,it=(cat?.vehicles||[]).find(v=>v.id===r.v),kind=kindOf(r.v,it?.group);
  if(!kind)return null;
  const paint=(cat?.paints||[]).find(p=>p.id===(PAINT_ID.test(r.c||'')?r.c:it?.paint));
  return {id:r.v,kind,name:it?.name||'',emoji:it?.emoji||'🛵',hex:/^#[0-9a-f]{6}$/i.test(paint?.hex||'')?paint.hex:'#d9534f',paint:paint?.id||'',plate:''};
}

/* ------------------------------------------------------------ colours */
const rgbOf=h=>{const n=parseInt(String(h).slice(1,7),16)||0;return [n>>16&255,n>>8&255,n&255];};
const mix=(a,b,t)=>{const x=rgbOf(a),y=rgbOf(b);return `rgb(${x.map((v,i)=>Math.round(v+(y[i]-v)*t)).join(',')})`;};
function paints(hex){
  const light=rgbOf(hex).reduce((s,v)=>s+v,0)>600;
  return {p:hex,d:mix(hex,'#000000',light?.3:.32),l:mix(hex,'#ffffff',.38),line:light?'#9a9087':mix(hex,'#000000',.45)};
}
const TIRE='#3f3a38',RIM='#e4dfd6',HUB='#9b938d',CHROME='#c9c3bb',SEAT='#6f5a4f',GLASS='#cfe6ee',LAMP='#fff2bf',TAIL='#e2533c';

/* ------------------------------------------------------------ the art (facing left) */
const arc=(c,x,y,r,a0,a1,col,w)=>{c.beginPath();c.arc(x,y,r,a0,a1);c.strokeStyle=col;c.lineWidth=w;c.lineCap='round';c.stroke();};
/** One more closed shape on the current path (the windows: several shapes make one clip). */
const poly=(c,pts)=>{pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();};
/** The plate (biển tên) at the back; its words only when they can be read at this size, always left to right. */
function plateAt(c,x,y,w,h,text,fl,px){
  R(c,x,y,w,h,'#fffaf0',2.5,'#8b8480',1);
  if(!text||h*px<7)return;
  c.save();c.translate(x+w/2,y+h/2+.5);c.scale(fl,1);
  c.font=`800 ${h*.72}px "Trebuchet MS",sans-serif`;c.textAlign='center';c.textBaseline='middle';c.fillStyle='#3a3230';
  const tw=c.measureText(text).width;if(tw>w-2)c.scale((w-2)/tw,1);
  c.fillText(text,0,0);c.restore();
}
/* Each: wheels [[x, r]], seat [x, y] (the character's feet), ps (its size), grips (hands on the bars), clip (windows),
 * back (behind the rider), front (over the rider), half (shadow), plate [x, y, w, h]. */
const ART={
  bicycle:{wheels:[[-44,22],[42,22]],seat:[20,-40],ps:1,half:62,grips:[[-34,-75],[-27,-73]],
    back(c,P,v){
      const f=P.p,w=4.5;
      L(c,42,-22,4,-24,f,w);L(c,42,-22,20,-56,f,w);L(c,4,-24,22,-58,f,w);L(c,20,-52,-28,-60,f,w);L(c,4,-24,-28,-56,f,w);
      L(c,-29,-64,-33,-50,P.d,6);L(c,-31,-52,-44,-22,'#9aa1a8',3.5);
      E(c,4,-24,7,7,'#8b8480');E(c,4,-24,3,3,'#5b524c');
      arc(c,42,-22,26,Math.PI*1.1,Math.PI*1.75,P.d,3);
      L(c,-30,-62,-32,-74,'#8b8480',3);L(c,-38,-74,-22,-76,'#5b524c',4);
      R(c,10,-64,24,7,SEAT,4);
      if(v.id==='xe_dap'){R(c,-72,-90,32,22,'#c99a5a',6,'#9a6f3c',1.5);for(const x of [-64,-56,-48])L(c,x,-87,x,-70,'#b3844b',1);bloom(c,-62,-92,7,'#f19cb5');bloom(c,-50,-94,6,'#fff3d6');}
      E(c,-36,-66,3.5,3.5,LAMP);
    }},
  ebike:{wheels:[[-44,22],[42,22]],seat:[20,-40],ps:1,half:62,grips:[[-34,-75],[-27,-73]],
    back(c,P){
      const f=P.p;
      c.beginPath();c.moveTo(-29,-60);c.quadraticCurveTo(-18,-26,4,-24);c.strokeStyle=f;c.lineWidth=8;c.lineCap='round';c.stroke();
      L(c,42,-22,4,-24,f,4.5);L(c,42,-22,20,-56,f,4.5);L(c,4,-24,22,-58,f,5);
      R(c,-24,-50,20,12,'#4b4f52',4);R(c,-21,-48,6,8,'#7fd38a',2);
      L(c,-29,-64,-33,-50,P.d,6);L(c,-31,-52,-44,-22,'#9aa1a8',3.5);
      arc(c,42,-22,26,Math.PI*1.05,Math.PI*1.8,f,4);arc(c,-44,-22,26,Math.PI*1.2,Math.PI*1.9,f,4);
      L(c,22,-56,50,-54,'#8b8480',3);
      E(c,4,-24,7,7,'#8b8480');
      L(c,-30,-62,-32,-74,'#8b8480',3);L(c,-38,-74,-22,-76,'#5b524c',4);
      R(c,10,-64,24,7,SEAT,4);
      E(c,-37,-66,4.5,4,LAMP);
    }},
  cub:{wheels:[[-54,19],[50,19]],seat:[22,-62],ps:1,half:78,grips:[[-46,-108],[-37,-106]],plate:[64,-74,22,12],
    back(c,P){
      R(c,-14,-48,34,24,'#8b8480',7);L(c,4,-26,70,-30,'#d8d2c8',5);
      R(c,-10,-84,74,12,'#3f3a38',6);R(c,48,-86,30,4,'#8b8480',2);
      L(c,-42,-92,-54,-19,'#9aa1a8',4);
    },
    front(c,P){
      c.beginPath();c.moveTo(-40,-98);c.quadraticCurveTo(-30,-48,-2,-44);c.lineTo(22,-44);c.strokeStyle=P.p;c.lineWidth=13;c.lineCap='round';c.stroke();
      R(c,12,-78,58,30,P.p,13,P.line,1.5);R(c,20,-70,40,4,'#ffffff55',2);
      arc(c,50,-19,24,Math.PI*1.08,Math.PI*1.9,P.p,6);arc(c,-54,-19,23,Math.PI*1.15,Math.PI*1.85,P.p,6);
      P_(c,[[-52,-46],[-46,-94],[-34,-94],[-30,-46]],P.l);
      R(c,-60,-112,30,10,'#6f6a6a',5);E(c,-58,-100,8,9,CHROME);E(c,-59,-100,6,7,LAMP);
      R(c,72,-66,6,9,TAIL,3);
    }},
  scooter:{wheels:[[-54,17],[50,17]],seat:[24,-64],ps:1,half:84,grips:[[-48,-107],[-36,-105]],plate:[60,-46,22,12],
    back(c,P){R(c,-44,-34,62,10,'#efe2cf',5,'#c9b49a',1.2);R(c,-4,-86,62,14,SEAT,7);R(c,4,-84,40,4,'#ffffff30',2);},
    front(c,P){
      R(c,-2,-74,82,50,P.p,24,P.line,1.5);E(c,50,-26,22,7,P.d);R(c,10,-56,56,6,'#ffffff50',3);
      P_(c,[[-60,-30],[-50,-100],[-34,-100],[-36,-30]],P.p);c.strokeStyle=P.line;c.lineWidth=1.5;c.stroke();
      arc(c,-54,-17,20,Math.PI*1.05,Math.PI*1.95,P.p,7);
      R(c,-64,-112,34,9,'#6f6a6a',4);E(c,-62,-96,7,8,LAMP);L(c,-38,-110,-32,-124,'#8b8480',2.5);E(c,-31,-127,6,4,'#cfe0e6');
      R(c,76,-62,6,10,TAIL,3);
    }},
  mini:{wheels:[[-48,18],[50,18]],seat:[-20,-12],ps:.74,half:84,plate:[56,-44,24,12],
    clip(c){poly(c,[[-46,-58],[-33,-94],[-4,-96],[-4,-58]]);poly(c,[[4,-58],[4,-96],[28,-96],[46,-58]]);},
    back(c,P){
      c.beginPath();c.moveTo(-54,-54);c.bezierCurveTo(-48,-84,-40,-104,-20,-104);c.lineTo(30,-104);c.bezierCurveTo(46,-104,54,-80,60,-54);c.closePath();c.fillStyle=P.p;c.fill();
      P_(c,[[-46,-58],[-33,-94],[-4,-96],[-4,-58]],GLASS);P_(c,[[4,-58],[4,-96],[28,-96],[46,-58]],GLASS);
    },
    front(c,P){
      glare(c,[[-40,-62],[-30,-90]],[[10,-62],[14,-90]]);
      L(c,0,-58,0,-98,P.p,6);R(c,-82,-62,164,40,P.p,20,P.line,1.5);
      arches(c,P,[[-48,18],[50,18]]);
      L(c,0,-60,2,-30,P.line,1.2);R(c,-18,-52,11,3,'#ffffff90',1.5);R(c,8,-52,11,3,'#ffffff90',1.5);
      R(c,-60,-62,120,5,'#ffffff40',2.5);
      E(c,-78,-46,6,6,LAMP);R(c,74,-54,6,11,TAIL,3);R(c,-86,-32,14,8,CHROME,4);R(c,72,-32,14,8,CHROME,4);
    }},
  suv:{wheels:[[-56,21],[58,21]],seat:[-28,-16],ps:.8,half:98,plate:[64,-48,26,13],
    clip(c){poly(c,[[-58,-68],[-46,-104],[-12,-104],[-12,-68]]);poly(c,[[-4,-68],[-4,-104],[30,-104],[30,-68]]);poly(c,[[38,-68],[38,-104],[66,-104],[72,-68]]);},
    back(c,P){
      P_(c,[[-66,-62],[-52,-112],[72,-114],[84,-62]],P.p);R(c,-44,-122,108,5,'#5b5552',2);L(c,-36,-117,-36,-112,'#5b5552',3);L(c,56,-117,56,-112,'#5b5552',3);
      P_(c,[[-58,-68],[-46,-104],[-12,-104],[-12,-68]],GLASS);P_(c,[[-4,-68],[-4,-104],[30,-104],[30,-68]],GLASS);P_(c,[[38,-68],[38,-104],[66,-104],[72,-68]],'#b9d4de');
    },
    front(c,P){
      glare(c,[[-50,-72],[-40,-100]],[[4,-72],[8,-100]]);
      L(c,-8,-66,-8,-108,P.p,7);L(c,34,-66,34,-108,P.p,7);
      R(c,-92,-70,184,46,P.p,14,P.line,1.5);arches(c,P,[[-56,21],[58,21]]);
      L(c,-8,-68,-6,-30,P.line,1.2);L(c,34,-68,34,-30,P.line,1.2);R(c,-26,-58,12,3,'#ffffff90',1.5);R(c,14,-58,12,3,'#ffffff90',1.5);
      R(c,-80,-70,160,5,'#ffffff40',2.5);
      R(c,-92,-64,10,10,LAMP,3);R(c,86,-64,7,14,TAIL,3);R(c,-96,-36,18,10,'#5b5552',4);R(c,80,-36,18,10,'#5b5552',4);
    }},
  convertible:{wheels:[[-58,19],[60,19]],seat:[-6,-26],ps:.8,half:100,grips:[[-34,-74],[-28,-71]],plate:[68,-44,24,12],
    back(c,P){R(c,-24,-66,84,12,'#8a5a3c',5);R(c,10,-90,16,30,'#8a5a3c',7);R(c,34,-86,14,26,'#8a5a3c',7);},
    front(c,P){
      R(c,-96,-60,192,36,P.p,16,P.line,1.5);c.beginPath();c.moveTo(-96,-46);c.quadraticCurveTo(-70,-66,-40,-60);c.lineTo(-96,-60);c.closePath();c.fillStyle=P.p;c.fill();
      arches(c,P,[[-58,19],[60,19]]);
      L(c,-88,-44,88,-44,'#f3efe6',2.5);L(c,-4,-58,-2,-30,P.line,1.2);R(c,-20,-52,12,3,'#ffffff90',1.5);
      P_(c,[[-46,-60],[-34,-94],[-28,-94],[-38,-60]],'#cfe6ee99');L(c,-46,-60,-34,-96,CHROME,3);
      E(c,-32,-68,3,10,'#6b4c34');
      E(c,-90,-50,7,6,LAMP);R(c,88,-56,6,10,TAIL,3);R(c,-100,-32,22,7,CHROME,3.5);R(c,80,-32,22,7,CHROME,3.5);
    }},
  super:{wheels:[[-58,19],[56,19]],seat:[0,-14],ps:.6,half:100,plate:[66,-40,24,12],
    clip(c){poly(c,[[-40,-50],[-18,-86],[32,-88],[62,-52]]);},
    back(c,P){P_(c,[[-40,-50],[-18,-86],[32,-88],[62,-52]],'#3b4a58');},
    front(c,P){
      c.beginPath();poly(c,[[-40,-50],[-18,-86],[32,-88],[62,-52]]);c.fillStyle='#9fc6d840';c.fill();
      glare(c,[[-26,-54],[-8,-82]]);
      P_(c,[[-100,-28],[-94,-42],[-44,-52],[-40,-50],[62,-52],[100,-52],[100,-24],[-100,-22]],P.p);
      c.strokeStyle=P.line;c.lineWidth=1.5;c.stroke();
      P_(c,[[6,-44],[34,-46],[40,-30],[12,-30]],'#2f2b2b');
      arches(c,P,[[-58,19],[56,19]]);
      L(c,-96,-36,-72,-42,LAMP,3);R(c,94,-50,6,10,TAIL,2);
      L(c,80,-52,82,-64,'#2f2b2b',3);L(c,96,-52,96,-64,'#2f2b2b',3);R(c,74,-70,30,6,P.d,3);
    }},
};
function P_(c,pts,fill){P(c,pts,fill);}
/** The dark wheel wells over the top of the wheels (drawn in the body: the wheels themselves turn under it). */
function arches(c,P,wheels){for(const [x,r] of wheels){c.beginPath();c.arc(x,-r,r+4,Math.PI,0);c.closePath();c.fillStyle='#3a3330';c.fill();}}
/** A soft white shine across the windows (over whoever sits inside). */
function glare(c,...lines){for(const [a,b] of lines)L(c,a[0],a[1],b[0],b[1],'#ffffff66',4);}

/** The two wheels at angle `ang`, facing left (the caller flips): drawn every frame, under the cached body. */
function wheels(c,A,kind,ang){
  const car=!TWO.has(kind);
  for(const [x,r] of A.wheels){
    const y=-r;
    if(kind==='bicycle'||kind==='ebike'){
      c.beginPath();c.arc(x,y,r-2,0,Math.PI*2);c.strokeStyle=TIRE;c.lineWidth=4.5;c.stroke();
      c.strokeStyle='#b8b0a8';c.lineWidth=1.2;c.beginPath();
      for(let i=0;i<4;i++){const a=-ang+i*Math.PI/4,dx=Math.cos(a)*(r-4),dy=Math.sin(a)*(r-4);c.moveTo(x-dx,y-dy);c.lineTo(x+dx,y+dy);}
      c.stroke();E(c,x,y,3,3,HUB);continue;
    }
    E(c,x,y,r,r,TIRE);
    if(kind==='convertible')E(c,x,y,r*.72,r*.72,'#f3efe6');
    E(c,x,y,r*(car?.52:.5),r*(car?.52:.5),kind==='super'?'#e0b84a':car?'#cfd3d8':RIM);
    c.fillStyle=car?'#8d9299':HUB;
    const n=car?5:3;
    for(let i=0;i<n;i++){const a=-ang+i*Math.PI*2/n;if(car){c.beginPath();c.arc(x+Math.cos(a)*r*.32,y+Math.sin(a)*r*.32,r*.08,0,Math.PI*2);c.fill();}
      else L(c,x,y,x+Math.cos(a)*r*.48,y+Math.sin(a)*r*.48,HUB,2);}
    E(c,x,y,r*.14,r*.14,'#6f6a6a');
  }
}

/* ------------------------------------------------------------ the rider, cached */
const BOX={x:116,up:228,down:16};   // the bitmap: 232 wide, from 228 above the ground to 16 below
const CACHE=new Map();
/** The pen without the character's own ground shadow (it sits on a seat, not on the ground). */
const SEATED={...CANVAS};
function body(F,fkey,v,face,px,rider,F2=null,fkey2=''){
  const two=F2&&TWO.has(v.kind);
  const key=`${fkey}|${v.id}|${v.kind}|${v.hex}|${v.plate||''}|${face}|${Math.round(px*100)}|${rider?1:0}|${two?fkey2:''}`;
  let cv=CACHE.get(key);if(cv)return cv;
  if(CACHE.size>96)CACHE.clear();
  cv=document.createElement('canvas');cv.width=Math.ceil(BOX.x*2*px);cv.height=Math.ceil((BOX.up+BOX.down)*px);
  const c=cv.getContext('2d'),A=ART[v.kind]||ART.scooter,P=paints(v.hex),fl=face<0?1:-1;
  c.setTransform(px,0,0,px,BOX.x*px,BOX.up*px);
  try{
    c.save();c.scale(fl,1);A.back(c,P,v);c.restore();
    if(two){   // 💑 the spouse behind the driver, a little higher, hands on the driver
      c.save();const [sx,sy]=A.seat,ps=A.ps*.93;c.translate((sx+36)*fl,sy-12);c.scale(ps,ps);
      let first=true;SEATED.E=(cc,...a)=>{if(first){first=false;return;}CANVAS.E(cc,...a);};
      paintPlayer(c,F2,SEATED,fl>0?{l:[-30,-62],r:[-26,-58]}:{l:[26,-58],r:[30,-62]});
      c.restore();
    }
    if(rider&&F){
      c.save();
      if(A.clip){c.scale(fl,1);c.beginPath();A.clip(c);c.clip();c.scale(fl,1);}
      const [sx,sy]=A.seat,ps=A.ps;c.translate(sx*fl,sy);c.scale(ps,ps);
      let arms=null;
      if(A.grips){const g=A.grips.map(([x,y])=>[(x*fl-sx*fl)/ps,(y-sy)/ps]);arms=fl>0?{l:g[0],r:g[1]}:{l:g[1],r:g[0]};}
      let first=true;SEATED.E=(cc,...a)=>{if(first){first=false;return;}CANVAS.E(cc,...a);};
      paintPlayer(c,F,SEATED,arms);
      c.restore();
    }
    c.save();c.scale(fl,1);A.front?.(c,P,v);if(A.plate){const [x,y,w,h]=A.plate;plateAt(c,x,y,w,h,v.plate,fl,px);}c.restore();
  }catch(e){console.warn('ride: art',e);}
  CACHE.set(key,cv);return cv;
}

/** A rider's motion state: which side it faces, the turn under way, the wheels' angle. */
export const rider=(face=-1)=>({face,from:face,turn:1,ang:0});
/** Moved by dx (this frame), dist along the road, dt seconds: turn when the way changes, roll the wheels. */
export function steer(r,dx,dist,dt,still=false){
  if(Math.abs(dx)>.15){const f=dx<0?-1:1;if(f!==r.face){r.from=r.turn<.5?r.from:r.face;r.face=f;r.turn=still?1:0;}}
  if(r.turn<1)r.turn=Math.min(1,r.turn+dt/TURN_S);
  if(!still)r.ang=(r.ang+dist/20)%(Math.PI*200);
}
/** Draw at (x, y) in the context's units: s = the character's size there, px = device pixels per unit (for a sharp
 * bitmap), F/fkey = the rider's figure and a key for its look (null F: parked, empty), v = the vehicle, r = rider(). */
export function drawRide(c,{x,y,s,px,F=null,fkey='',F2=null,fkey2='',v,r,bob=0}){
  const A=ART[v.kind]||ART.scooter,k=r.turn<1?Math.cos(r.turn*Math.PI):1,face=r.turn<.5?r.from:r.face;
  c.save();c.translate(x,y);
  E(c,0,2*s,A.half*s,8*s,'#7a5e4428');
  c.scale(s*Math.max(.06,Math.abs(k)),s);c.translate(0,-bob);
  c.save();c.scale(face<0?1:-1,1);wheels(c,A,v.kind,r.ang);c.restore();
  const cv=body(F,fkey,v,face,s*px,Boolean(F),F2,fkey2);
  c.drawImage(cv,-BOX.x,-BOX.up,BOX.x*2,BOX.up+BOX.down);
  c.restore();
}
/** How far the vehicle reaches either side of its middle (character units): where to park it beside a door. */
export const halfOf=v=>(ART[v?.kind]||ART.scooter).half;
/** The top of the rider's head over the ground (character units), for name tags and bubbles. */
export const topOf=v=>{const A=ART[v?.kind]||ART.scooter;return -(A.seat[1])+132*A.ps;};
