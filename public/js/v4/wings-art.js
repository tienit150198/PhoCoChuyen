/** 🪽 Cánh, the art (game/wings.py, wings_content.py: the same style ids and tiers; owner 22/10 "cánh này là làm đẹp cho
 * người dùng nhé", "cho cánh đẹp tí, có cả mode cũ và mode mới đều hiển thị được nhé").
 * One painter for every place the character is drawn, through the pens of v4/look.js (K = CANVAS or SVG):
 *   paintWings(c,F,K,opts)  behind the classic character (paintPlayer: the wardrobe mirror, the street's walkers, the
 *                           workplace scene of boba-world.js, which flaps them gently with `flap`), and behind / over the
 *                           2.5D chibi (isometric/character-art.js: behind when it faces us, over its back otherwise)
 *   wingsBust(wg)           the tips peeking behind the round portrait
 *   wingIcon(wg,size)       the pair large (🛍️ Tiệm phụ kiện, the wardrobe)
 * A wing is {k: style, r: tier 0 D … 7 Huyền thoại}. Each style is drawn as a right wing in its own frame (root (0,0) at
 * the shoulder blade, x outward, y down), mirrored for the left one. Layered feathers or membranes with a soft gradient,
 * a dark rim so they read on any background, and the tier on top, as the pets' ranks read (v4/pet-art.js RANK_COLOR):
 * a trim of the tier's colour from C, a soft glow from S, sparkles from SS, a rainbow from SSS, gold for Huyền thoại. */
export const WING_STYLES=Object.freeze(['buom','tien','doi','thien_than','rong','phuong']);
export const WING_TIERS=Object.freeze(['D','C','B','A','S','SS','SSS','Huyền thoại']);
/** The pets' rank colours (v4/pet-art.js RANK_COLOR) and the legendaries' gold. */
export const WING_TIER_COLOR=Object.freeze(['#9aa0a6','#4caf6a','#3d8bfd','#a259ff','#f2b632','#ff6a3d','#ff4fa3','#ffd24a']);
const TOP=7,RB=['#ff5a5a','#ffb43b','#ffe55c','#5fd46a','#4fb3ff','#a77bff'];
const RIM='#2b1d1a';
/** {k, r} with a known style and tier, or null (a newer build's style, a bad frame). */
export function cleanWing(wg){
  if(!wg||typeof wg!=='object'||Array.isArray(wg)||!WING_STYLES.includes(wg.k))return null;
  const r=Math.trunc(Number(wg.r));return Number.isFinite(r)&&r>=0&&r<=TOP?{k:wg.k,r}:null;
}
/** The worn wing of a state (journey.wings: own, on), or null. */
export function wingOfState(state){
  const w=state?.journey?.wings,x=w&&Array.isArray(w.own)?w.own.find(o=>o?.id===w.on):null;
  return x?cleanWing(x):null;
}
const n1=v=>Math.round(v*10)/10;
const PAL={
  buom:{a:'#7cc6f2',b:'#2f6fb3',l:'#e2f5ff',s:'#1f2a44',m:'#ffd36b'},
  tien:{a:'#cdeffb',b:'#9fd6f0',l:'#ffffff',s:'#b7a6ff',m:'#fff7c2'},
  doi:{a:'#5a4772',b:'#2e2140',l:'#8a73a8',s:'#1c1426',m:'#c9b6e6'},
  thien_than:{a:'#ffffff',b:'#d7dcf0',l:'#ffffff',s:'#b9c1dd',m:'#fff3c4'},
  rong:{a:'#3f9a62',b:'#1f5a37',l:'#9fdcb0',s:'#173f28',m:'#f2c14e'},
  phuong:{a:'#ff5a2b',b:'#c9261d',l:'#ffd347',s:'#8e1a12',m:'#fff1a8'},
};
/** A frame: local (x, y) of a right wing → the page. ox, oy the root, s the scale, side ±1, f the flap (-1…1), `tall` a
 * stretch upward (the classic character has a big head: the wings rise above its shoulders), `spread` a lean outward. */
function frame(ox,oy,s,side,f,tall=1,spread=0){
  const th=spread+f*.16,co=Math.cos(th),si=Math.sin(th),sx=1-.1*Math.abs(f);
  return (x,y)=>{const X=x*co-y*si,Y=x*si+y*co;return [ox+side*X*s*sx,oy+Y*s*(Y<0?tall:1)];};
}
/** A path from local commands [['M',x,y],['L',x,y],['Q',cx,cy,x,y],['C',…],['Z']] through the frame. */
function P(T,cmds){
  return cmds.map(([op,...v])=>{if(op==='Z')return 'Z';const out=[];for(let i=0;i<v.length;i+=2){const [x,y]=T(v[i],v[i+1]);out.push(n1(x),n1(y));}return op+out.join(' ');}).join('');
}
/** A feather from local (x, y) pointing at `deg` (0 outward, 90 down), `len` long and `w` wide, rounded at the tip. */
function feather(x,y,deg,len,w){
  const a=deg*Math.PI/180,dx=Math.cos(a),dy=Math.sin(a),px=-dy,py=dx;
  const at=(t,o)=>[x+dx*len*t+px*o,y+dy*len*t+py*o];
  const [ax,ay]=at(.22,w),[bx,by]=at(.9,w*.75),[tx,ty]=at(1,0),[cx,cy]=at(.9,-w*.75),[dx2,dy2]=at(.22,-w);
  return [['M',x,y],['C',ax,ay,bx,by,tx,ty],['C',cx,cy,dx2,dy2,x,y],['Z']];
}
function star(c,K,x,y,r,col){K.P(c,[[x,y-r],[x+r*.3,y-r*.3],[x+r,y],[x+r*.3,y+r*.3],[x,y+r],[x-r*.3,y+r*.3],[x-r,y],[x-r*.3,y-r*.3]],col);}
const lerp=(a,b,t)=>a+(b-a)*t;
/** Points along the arm (a quadratic root → c → tip), t 0…1. */
const arm=(c,tip,t)=>[2*(1-t)*t*c[0]+t*t*tip[0],2*(1-t)*t*c[1]+t*t*tip[1]];
/** Fill with a gradient from the root to `to` (local), a dark rim under it. */
function shape(c,K,T,cmds,c1,c2,to,rim=2.2,s=1){
  const d=P(T,cmds),[x1,y1]=T(0,0),[x2,y2]=T(to[0],to[1]);
  if(rim)K.stroke(c,d,RIM+'cc',rim*s);
  K.pathG(c,d,c1,c2,x1,y1,x2,y2);
  return d;
}
/* ---- the styles: each draws one right wing in its frame T; p its colours, r the tier, trim the tier's colour ---- */
function feathered(c,K,T,p,r,trim,s,{fire=false}={}){
  // the arm sweeps up and out to the wrist; the feathers fan from it, the long primaries at the tip pointing out and down,
  // the secondaries near the shoulder pointing down: the broad rounded wing of a dove (or a phoenix's flame)
  const C=[4,-46],TIP=[30,-60];
  const rows=[[9,.1,1,[100,70],[24,38],[4.2,5.4],fire?p.b:p.b,fire?p.a:p.a],[7,.06,.9,[104,78],[16,27],[4.6,5],fire?p.a:p.a,fire?p.l:p.l],[6,.03,.78,[108,86],[9,15],[4,4.4],p.l,fire?p.m:'#ffffff']];
  rows.forEach(([n,t0,t1,deg,len,w,c1,c2],row)=>{
    for(let i=0;i<n;i++){const t=lerp(t0,t1,i/(n-1)),[x,y]=arm(C,TIP,t),dg=lerp(deg[0],deg[1],t),ln=lerp(len[0],len[1],t),wd=lerp(w[0],w[1],t);
      const f=feather(x,y,dg,ln,wd),a=dg*Math.PI/180,d=shape(c,K,T,f,c2,c1,[x+Math.cos(a)*ln,y+Math.sin(a)*ln],1.6,s);
      if(row===0&&r>=1)K.stroke(c,d,trim,.9*s);
      const [qx,qy]=T(x+Math.cos(a)*ln*.15,y+Math.sin(a)*ln*.15),[ex,ey]=T(x+Math.cos(a)*ln*.78,y+Math.sin(a)*ln*.78);K.L(c,qx,qy,ex,ey,'#ffffff80',.7*s);}
  });
  const ridge=P(T,[['M',0,0],['Q',C[0],C[1],TIP[0],TIP[1]]]);
  K.stroke(c,ridge,RIM+'aa',6.4*s);K.stroke(c,ridge,fire?p.l:p.a,4.4*s);K.stroke(c,ridge,'#ffffff90',1.4*s);
  if(r>=1){const [ax,ay]=T(TIP[0],TIP[1]);K.E(c,ax,ay,2.2*s,2.2*s,RIM);K.E(c,ax,ay,1.5*s,1.5*s,trim);}
  if(fire)for(const [x,y,k] of [[42,-26,1],[40,-6,.8],[30,8,.7]]){const [ax,ay]=T(x-6,y-6),[bx,by]=T(x+4,y+14*k);K.stroke(c,`M${n1(ax)} ${n1(ay)}Q${n1(bx)} ${n1(ay)} ${n1(bx)} ${n1(by)}`,p.l,1.6*s);K.E(c,bx,by,1.6*s,1.6*s,p.m);}
}
function butterfly(c,K,T,p,r,trim,s){
  const edge=r>=1?trim:p.b;
  const up=[['M',0,0],['C',4,-26,24,-62,38,-56],['C',46,-50,36,-18,0,0],['Z']],lo=[['M',0,2],['C',18,0,34,10,28,24],['C',22,32,6,18,0,4],['Z']];
  shape(c,K,T,lo,p.a,edge,[28,24],2.2,s);shape(c,K,T,up,p.a,edge,[38,-56],2.2,s);
  K.path(c,P(T,[['M',2,-2],['C',6,-22,20,-46,30,-44],['C',34,-38,26,-16,2,-2],['Z']]),p.l+'b0');
  K.path(c,P(T,[['M',2,3],['C',14,3,24,10,20,18],['C',16,22,6,14,2,5],['Z']]),p.l+'90');
  for(const [x,y] of [[12,-14],[20,-30],[28,-44],[14,8],[22,14]]){const [a,b]=T(1,0),[ex,ey]=T(x,y);K.L(c,a,b,ex,ey,p.b+'90',.8*s);}
  const [ex,ey]=T(30,-42),[fx,fy]=T(21,16);
  K.E(c,ex,ey,5.4*s,5.4*s,p.s);K.E(c,ex,ey,3.4*s,3.4*s,p.m);K.E(c,ex-.8*s,ey-.9*s,1.2*s,1.2*s,'#fff');
  K.E(c,fx,fy,3.2*s,3.2*s,p.s);K.E(c,fx,fy,1.8*s,1.8*s,p.m);
  for(const [x,y] of [[40,-52],[42,-44],[36,-34],[30,20],[24,25]]){const [a,b]=T(x,y);K.E(c,a,b,1.3*s,1.3*s,'#ffffffd0');}
}
function fairy(c,K,T,p,r,trim,s){
  const edge=r>=1?trim:'#ffffff';
  const up=[['M',0,0],['C',2,-34,24,-72,34,-66],['C',42,-60,22,-24,0,0],['Z']],lo=[['M',0,2],['C',18,-2,38,8,32,20],['C',26,26,8,12,0,4],['Z']];
  for(const d of [lo,up]){const q=P(T,d);K.stroke(c,q,RIM+'66',2*s);K.pathG(c,q,p.a+'cc',p.s+'88',...T(0,0),...T(30,-50));K.stroke(c,q,edge,1.2*s);}
  for(const [x,y] of [[30,-60],[26,-40],[18,-22],[26,14],[20,18]]){const [a,b]=T(2,0),[ex,ey]=T(x,y);K.stroke(c,`M${n1(a)} ${n1(b)}L${n1(ex)} ${n1(ey)}`,'#ffffffb0',.8*s);}
  for(const [x,y,k] of [[34,-62,1],[22,-44,.7],[30,16,.8],[12,-30,.6]]){const [a,b]=T(x,y);star(c,K,a,b,3*k*s,'#ffffff');}
}
function membrane(c,K,T,p,r,trim,s,{dragon=false}={}){
  const edge=r>=1?trim:p.s;
  const el=[12,-28],wr=dragon?[20,-56]:[18,-50],tips=dragon?[[44,-46],[44,-18],[34,8]]:[[40,-38],[40,-12],[28,10]];
  const m=[['M',0,0],['L',el[0],el[1]],['L',wr[0],wr[1]],['L',tips[0][0],tips[0][1]],['Q',34,-30,tips[1][0],tips[1][1]],['Q',30,-2,tips[2][0],tips[2][1]],['Q',14,6,0,4],['Z']];
  shape(c,K,T,m,p.l,p.a,[40,0],2.4,s);
  K.path(c,P(T,[['M',4,-2],['L',el[0]+1,el[1]+4],['L',wr[0]+2,wr[1]+8],['Q',28,-20,26,-4],['Q',18,2,4,2],['Z']]),p.a+'90');
  K.stroke(c,P(T,m),edge,1.1*s);
  const bone=dragon?3.2:2.4;
  K.stroke(c,P(T,[['M',0,0],['L',el[0],el[1]],['L',wr[0],wr[1]]]),p.s,bone*s);
  for(const t of tips)K.stroke(c,P(T,[['M',wr[0],wr[1]],['L',t[0],t[1]]]),p.b,bone*.6*s);
  K.P(c,[T(wr[0]-2,wr[1]),T(wr[0]+1,wr[1]-7),T(wr[0]+3,wr[1]-1)],dragon?p.m:p.l);   // the claw
  if(dragon){
    for(let i=1;i<6;i++){const t=i/6,x=lerp(0,el[0],t*2>1?1:t*2),y=lerp(0,el[1],t*2>1?1:t*2),[ax,ay]=t>.5?[lerp(el[0],wr[0],(t-.5)*2),lerp(el[1],wr[1],(t-.5)*2)]:[x,y];
      K.P(c,[T(ax-2.4,ay+1),T(ax-4.5,ay-5),T(ax+1,ay-1)],p.b);}
    for(const [x,y] of [[26,-30],[30,-16],[22,-6],[16,-18]]){const [a,b]=T(x,y);K.E(c,a,b,2*s,1.2*s,p.l+'90');}
  }
}
const DRAW={buom:butterfly,tien:fairy,doi:(c,K,T,p,r,t,s)=>membrane(c,K,T,p,r,t,s),thien_than:(c,K,T,p,r,t,s)=>feathered(c,K,T,p,r,t,s),
  rong:(c,K,T,p,r,t,s)=>membrane(c,K,T,p,r,t,s,{dragon:true}),phuong:(c,K,T,p,r,t,s)=>feathered(c,K,T,p,r,t,s,{fire:true})};
/** The tier behind both wings: a glow from S, a rainbow for SSS, gold for Huyền thoại (centred between the roots). */
function auraBack(c,K,x,y,r,s){
  if(r<4)return;
  if(r===TOP){K.glow(c,x,y-30*s,70*s,56*s,'#ffd24a',.55);K.glow(c,x,y-34*s,46*s,36*s,'#fff3b0',.5);return;}
  if(r===6){RB.forEach((col,i)=>K.glow(c,x+(i-2.5)*9*s,y-30*s,44*s,44*s,col,.22));return;}
  K.glow(c,x,y-28*s,58*s,46*s,WING_TIER_COLOR[r],r>=5?.45:.32);
}
/** Sparkles over the wings: from SS; a shower of rainbow stars for SSS; gold motes for Huyền thoại. */
function auraFront(c,K,x,y,r,s,side=1){
  if(r<5)return;
  const pts=[[-40,-70],[42,-58],[-30,-30],[36,-16],[-46,-48],[24,-84]];
  pts.slice(0,r>=6?6:3).forEach(([px,py],i)=>{const col=r===TOP?(i%2?'#fff3b0':'#ffd24a'):r===6?RB[i%6]:'#ffffff';star(c,K,x+side*px*s,y+py*s,(i%3?2:3)*s,col);});
  if(r===TOP)for(const [px,py] of [[-20,-96],[18,-100],[0,-108]])K.E(c,x+px*s,y+py*s,1.6*s,1.6*s,'#ffe58a');
}
/** Both wings of `wg` with their roots at (x, y) (the shoulder blades' centre), `gap` apart, scale `s`, flap `flap` -1…1;
 * `aura` the glow behind them, `body` the wings themselves, `sparkle` the sparkles over them. */
export function drawWings(c,K,wg,x,y,{s=1,gap=6,flap=0,sparkle=true,tall=1,spread=0,aura=true,body=true}={}){
  const w=cleanWing(wg);if(!w)return;
  const p=PAL[w.k],r=w.r,trim=WING_TIER_COLOR[r],ss=s*(.94+.018*r);
  if(aura)auraBack(c,K,x,y,r,ss);
  if(body)for(const side of [-1,1]){const T=frame(x+side*gap*s,y,ss,side,flap,tall,spread);DRAW[w.k](c,K,T,p,r,trim,ss);}
  if(sparkle)auraFront(c,K,x,y,r,ss);
}
/** The sparkles alone (the 2.5D stamp draws its wings behind the chibi, then these over it). */
export function wingSparkles(c,K,wg,x,y,{s=1}={}){const w=cleanWing(wg);if(w)auraFront(c,K,x,y,w.r,s*(.94+.018*w.r));}
/** On the classic character (origin at the feet; paintPlayer, boba-world.js): roots behind the shoulders. F.L.wg the
 * wing, F.wf the flap (-1…1, set by an animated scene). */
export function paintWings(c,F,K,{at=null,s=1.12,flap=null,tall=1.45,spread=.1}={}){
  const w=cleanWing(F?.L?.wg);if(!w)return;
  const [x,y]=at||[0,-46];
  drawWings(c,K,w,x,y,{s,gap:6,tall,spread,flap:flap??(Number(F?.wf)||0)});
}
/** The tips peeking behind the round bust (80×80, drawn first). */
export function wingsBust(c,K,wg){const w=cleanWing(wg);if(!w)return;drawWings(c,K,w,40,70,{s:.62,gap:10,sparkle:false});}
/** A pair large, centred in a -30…30 box (the shop's tiles). */
export function wingIcon(c,K,wg){const w=cleanWing(wg);if(!w)return;drawWings(c,K,w,0,14,{s:.62,gap:3});}
