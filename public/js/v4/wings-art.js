/** 🪽 Cánh, the art (game/wings.py, wings_content.py: the same style ids and tiers; owner 22/10 "cánh này là làm đẹp cho
 * người dùng nhé", "cho cánh đẹp tí, có cả mode cũ và mode mới đều hiển thị được nhé"; 23/10 "cánh mua xong ra ngoài xấu
 * quá, cho đẹp hơn đi", "cho đẹp hơn, to hơn nhé").
 * One painter for every place the character is drawn, through the pens of v4/look.js (K = CANVAS or SVG):
 *   paintWings(c,F,K,opts)  behind the classic character (paintPlayer: the wardrobe mirror, the street's walkers, the
 *                           workplace scene of boba-world.js, which flaps them from cached bitmaps with `t`), and behind /
 *                           over the 2.5D chibi (isometric/character-art.js: behind when it faces us, over its back otherwise)
 *   wingsBust(wg)           the tips peeking behind the round portrait
 *   wingIcon(wg,size)       the pair large (🛍️ Tiệm phụ kiện, the wardrobe)
 * A wing is {k: style, r: tier 0 D … 7 Huyền thoại}. Each style is drawn as a right wing in its own frame (root (0,0) at
 * the shoulder blade, x outward, y down, in the 2.5D stamp's units: it reaches ~100 out and ~85 up, past the chibi's big
 * head), mirrored for the left one. Big and layered: rows of feathers (thiên thần, phượng hoàng), a membrane on finger
 * bones (dơi, rồng), veined panes (tiên), patterned wings (bướm), one dark outline round the whole like the chibi's own.
 * The tier on top, as the pets' ranks read (v4/pet-art.js RANK_COLOR): D, C plain; B, A an edge of the tier's colour;
 * a soft glow and rays from S; richer light and sparkles at SS, SSS; a gold rim, an iridescent sheen for Huyền thoại. */
export const WING_STYLES=Object.freeze(['buom','tien','doi','thien_than','rong','phuong']);
export const WING_TIERS=Object.freeze(['D','C','B','A','S','SS','SSS','Huyền thoại']);
/** The pets' rank colours (v4/pet-art.js RANK_COLOR) and the legendaries' gold. */
export const WING_TIER_COLOR=Object.freeze(['#9aa0a6','#4caf6a','#3d8bfd','#a259ff','#f2b632','#ff6a3d','#ff4fa3','#ffd24a']);
const TOP=7,RB=['#ff5a5a','#ffb43b','#ffe55c','#5fd46a','#4fb3ff','#a77bff'];
const RIM='#2b1d1a',GOLD_RIM='#6b4210';
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
/* a light, b deep, l highlight, s line / shade, m accent; f* the feathered rows (base → tip) */
const PAL={
  buom:{a:'#8fd3ff',b:'#2c6fc4',l:'#e6f7ff',s:'#1d2748',m:'#ffd36b'},
  tien:{a:'#a6e4ff',b:'#9fd6f0',l:'#ffffff',s:'#a58cf0',m:'#fff7c2'},
  doi:{a:'#7c62a6',b:'#3a2954',l:'#a68fcc',s:'#1c1426',m:'#e6d8ff'},
  thien_than:{a:'#ffffff',b:'#cdd5f0',l:'#ffffff',s:'#9aa6cf',m:'#fff3c4',f:[['#c3cdee','#ffffff'],['#d3daf4','#ffffff'],['#e3e7f8','#ffffff'],['#eef1fb','#ffffff']]},
  rong:{a:'#5cc37f',b:'#1f6a3e',l:'#b6f0c4',s:'#123d24',m:'#f2c14e'},
  phuong:{a:'#ff6a2b',b:'#c9261d',l:'#ffd347',s:'#5a0c08',m:'#fff1a8',f:[['#8a0e16','#ff6a1a'],['#a3141a','#ff5a1c'],['#f27a22','#ffd760'],['#ff9a2e','#ffe58a']]},
};
/** Each style's size (bướm, tiên a little smaller than the big feathered and leathery ones). */
const SIZE={buom:.95,tien:.96,doi:1,thien_than:1,rong:1.04,phuong:1.02};
/** A frame: local (x, y) of a right wing → the page. ox, oy the root, s the scale, side ±1, f the flap (-1 up, open …
 * 1 down, folding a little), `tall` a stretch upward, `spread` a turn outward-down (negative: up). */
function frame(ox,oy,s,side,f,tall=1,spread=0){
  const th=spread+f*.2,co=Math.cos(th),si=Math.sin(th),sx=1-.09*(f+1);
  return (x,y)=>{const X=x*co-y*si,Y=x*si+y*co;return [ox+side*X*s*sx,oy+Y*s*(Y<0?tall:1)];};
}
/** A path from local commands [['M',x,y],['L',x,y],['Q',cx,cy,x,y],['C',…],['Z']] through the frame. */
function P(T,cmds){
  return cmds.map(([op,...v])=>{if(op==='Z')return 'Z';const out=[];for(let i=0;i<v.length;i+=2){const [x,y]=T(v[i],v[i+1]);out.push(n1(x),n1(y));}return op+out.join(' ');}).join('');
}
/** A closed smooth outline through local points (a Catmull-Rom loop as cubic curves). */
function loop(pts,k=1/6){
  const n=pts.length,cmd=[['M',...pts[0]]];
  for(let i=0;i<n;i++){const p0=pts[(i-1+n)%n],p1=pts[i],p2=pts[(i+1)%n],p3=pts[(i+2)%n];
    cmd.push(['C',p1[0]+(p2[0]-p0[0])*k,p1[1]+(p2[1]-p0[1])*k,p2[0]-(p3[0]-p1[0])*k,p2[1]-(p3[1]-p1[1])*k,p2[0],p2[1]]);}
  cmd.push(['Z']);return cmd;
}
const lerp=(a,b,t)=>a+(b-a)*t,mix=(p,q,t)=>[lerp(p[0],q[0],t),lerp(p[1],q[1],t)];
/** A feather from base b to tip t, `w` wide, rounded at the tip; `curl` bends the tip sideways (a flame's flick). */
function feather(b,t,w,curl=0){
  const dx=t[0]-b[0],dy=t[1]-b[1],L=Math.hypot(dx,dy)||1,ux=dx/L,uy=dy/L,px=-uy,py=ux;
  const at=(k,o,c=0)=>[b[0]+ux*L*k+px*(o+c),b[1]+uy*L*k+py*(o+c)];
  return [['M',...at(0,w*.32)],['C',...at(.3,w*.95),...at(.8,w,curl*.5),...at(.97,w*.45,curl)],['Q',...at(1.04,0,curl*1.1),...at(.97,-w*.45,curl)],
    ['C',...at(.8,-w,curl*.5),...at(.3,-w*.95),...at(0,-w*.32)],['Z']];
}
function star(c,K,x,y,r,col){K.P(c,[[x,y-r],[x+r*.3,y-r*.3],[x+r,y],[x+r*.3,y+r*.3],[x,y+r],[x-r*.3,y+r*.3],[x-r,y],[x-r*.3,y-r*.3]],col);}
/** The tier's edge: B, A the tier's colour; S+ that colour glowing; Huyền thoại gold. Null for D, C. */
function edgeOf(r){return r<2?null:r===TOP?'#ffd24a':WING_TIER_COLOR[r];}
/** The outline under everything (one dark rim round the whole wing, gold-brown for Huyền thoại). */
const rimOf=(r,a='')=>(r===TOP?GOLD_RIM:RIM)+a;
/* ---- the styles: each draws one right wing in its frame T; p its colours, r the tier, s the scale (line widths) ---- */
/** Feathers in rows: long primaries off the hand, secondaries hanging off the arm, two rows of coverts, the arm on top.
 * Thiên thần soft white with a blue-lilac shade; phượng hoàng long flame-tipped feathers, red to gold. */
function feathered(c,K,T,p,r,s,{fire=false}={}){
  const R=fire?1.12:1,W=[44,-70],H=[74,-80],C=[6,-62],arm=t=>[2*(1-t)*t*C[0]+t*t*W[0],2*(1-t)*t*C[1]+t*t*W[1]];
  const hand=t=>mix(W,H,t);
  // the primaries: from the hand outward and down (the outermost first: the next one lies over it)
  const pt=fire?[[112,-84],[118,-60],[116,-34],[108,-10],[94,10],[78,26]]:[[104,-72],[106,-50],[101,-28],[92,-8],[80,10],[66,24]];
  const prim=pt.map((tp,i)=>{const b=hand(1-i/(pt.length-1)*.95);return {b,t:[b[0]+(tp[0]-b[0])*R,b[1]+(tp[1]-b[1])*R],w:fire?8.6:10.5,curl:fire?(i%2?-4:4):0};});
  // the secondaries: along the arm, hanging down
  const st=fire?[[64,40],[50,50],[36,54],[22,52],[10,44]]:[[56,34],[45,42],[33,46],[21,45],[10,38]];
  const sec=st.map((tp,i)=>{const b=arm(.86-i*.15);return {b,t:tp,w:fire?9:10.5,curl:fire?(i%2?3:-3):0};});
  // the coverts: two rows of short rounded feathers over the roots of the others
  const gc=[...Array(7)].map((_,i)=>{const u=i/6,b=u<.8?arm(.22+u/.8*.74):hand((u-.8)/.2*.55),a=lerp(102,38,u)*Math.PI/180,l=lerp(26,30,u);return {b,t:[b[0]+Math.cos(a)*l,b[1]+Math.sin(a)*l],w:8.4};});
  const lc=[...Array(6)].map((_,i)=>{const u=i/5,b=u<.85?arm(.3+u/.85*.68):hand(.3),a=lerp(98,30,u)*Math.PI/180,l=lerp(15,16,u);return {b:[b[0]+1,b[1]+2],t:[b[0]+Math.cos(a)*l,b[1]+Math.sin(a)*l],w:7.6};});
  const rows=fire?[prim,sec,gc]:[prim,sec,gc,lc],cols=p.f,ridge=[['M',0,0],['Q',...C,...W],['Q',W[0]+12,W[1]-11,...H]];
  // a backing under the feathers (no gap shows the background between them)
  const back=loop([[0,4],[2,-30],[20,-60],...prim.slice(0,5).map(f=>mix(f.b,f.t,.7)),...sec.map(f=>mix(f.b,f.t,.72))]);
  // the dark rim round the whole, then the fills over it (only the outer edge keeps the rim)
  const rw=2.6*s,shapes=rows.map(row=>row.map(f=>P(T,feather(f.b,f.t,f.w,f.curl))));
  K.stroke(c,P(T,back),rimOf(r),rw);for(const row of shapes.slice(0,2))for(const d of row)K.stroke(c,d,rimOf(r),rw);
  K.stroke(c,P(T,ridge),rimOf(r),9.6*s);
  K.path(c,P(T,back),cols[1][0]);
  const edge=edgeOf(r);
  rows.forEach((row,ri)=>row.forEach((f,i)=>{
    const d=shapes[ri][i],[x1,y1]=T(...f.b),[x2,y2]=T(...f.t);K.pathG(c,d,cols[ri][0],cols[ri][1],x1,y1,x2,y2);
    K.stroke(c,d,p.s+(ri<2?(fire?'cc':'88'):'66'),(fire&&ri<2?.9:.7)*s);
    if(ri<2){const [qx,qy]=T(...mix(f.b,f.t,.12)),[ex,ey]=T(...mix(f.b,f.t,.8));K.L(c,qx,qy,ex,ey,fire?'#fff1a8a0':'#ffffffb0',.8*s);}
    if(edge&&ri===0)K.stroke(c,d,edge+(r>=4?'':'cc'),(r>=4?1.1:.9)*s);
  }));
  if(fire)for(const f of [...prim,...sec]){const a=mix(f.b,f.t,.42),[x1,y1]=T(...a),[x2,y2]=T(...f.t);K.pathG(c,P(T,feather(a,f.t,f.w*.5,f.curl*.6)),'#ffd34700','#fff3b0',x1,y1,x2,y2);}   // the flame at each tip
  // the arm: a soft rounded leading edge
  const rd=P(T,ridge);K.stroke(c,rd,fire?'#ffb43b':'#ffffff',7*s);K.stroke(c,rd,fire?'#fff1a8':'#f4f6ff',3*s);
  if(edge)K.stroke(c,rd,edge+(r>=4?'':'aa'),1.2*s);
  if(fire)for(const [x,y,k] of [[18,-56,1],[34,-72,.85],[56,-84,.7]]){const [a,b]=T(x,y),[e,f]=T(x-4,y-12*k),[g,h]=T(x+5,y-3);K.P(c,[[a,b],[g,h],[e,f]],'#ffd347');}   // little flames off the arm
}
/** A membrane on finger bones: dơi dusk purple with a thumb claw, rồng green with gold bones, spikes and scales. */
function membrane(c,K,T,p,r,s,{dragon=false}={}){
  const E=dragon?[24,-46]:[22,-42],W=dragon?[50,-82]:[46,-74];
  const F=dragon?[[108,-74],[116,-38],[104,-2],[78,26]]:[[98,-66],[106,-34],[96,-2],[70,22]],B=dragon?[[36,36],[8,18]]:[[32,30],[8,15]];
  const pull=dragon?.3:.22,dip=(a,b)=>{const m=mix(a,b,.5);return mix(m,W,pull);};
  const outline=[['M',0,0],['L',...E],['L',...W],['L',...F[0]]];
  for(let i=1;i<F.length;i++)outline.push(['Q',...dip(F[i-1],F[i]),...F[i]]);
  outline.push(['Q',...mix(mix(F[3],B[0],.5),[20,6],.25),...B[0]],['Q',18,22,...B[1]],['Q',4,10,0,0],['Z']);
  const d=P(T,outline),edge=edgeOf(r);
  K.stroke(c,d,rimOf(r),2.8*s);
  // the panels between the fingers, each its own shade: a folded, leathery look
  const tone=dragon?[['#4fb36f','#2a7c49'],['#67c884','#2f8a52'],['#4fb36f','#24703f'],['#5cbf7b','#2a7c49']]:[['#6b5293','#3a2954'],['#806aa8','#43305f'],['#6b5293','#36264f'],['#78609f','#3e2c58']];
  const panels=[[['M',...W],['L',...F[0]],['Q',...dip(F[0],F[1]),...F[1]],['Z']],[['M',...W],['L',...F[1]],['Q',...dip(F[1],F[2]),...F[2]],['Z']],
    [['M',...W],['L',...F[2]],['Q',...dip(F[2],F[3]),...F[3]],['Z']],[['M',...W],['L',...F[3]],['Q',...mix(mix(F[3],B[0],.5),[20,6],.25),...B[0]],['Q',18,22,...B[1]],['Q',4,10,0,0],['L',...E],['Z']]];
  panels.forEach((q,i)=>{const [x1,y1]=T(...W),[x2,y2]=T(...(i<3?mix(F[i],F[i+1],.5):B[0]));K.pathG(c,P(T,q),tone[i][0],tone[i][1],x1,y1,x2,y2);});
  // a soft light along the bones, the veins
  for(const f of F){const [a,b]=T(...mix(W,f,.1)),[e,g]=T(...mix(W,f,.75));K.L(c,a,b,e,g,(dragon?'#c8f5d0':'#c9b6e6')+'55',5*s);}
  for(const [a,b] of [[[30,-30],[60,6]],[[64,-40],[88,-20]],[[70,-56],[92,-50]]]){const [x1,y1]=T(...a),[x2,y2]=T(...b);K.L(c,x1,y1,x2,y2,p.s+'40',.8*s);}
  if(edge)K.stroke(c,d,edge+(r>=4?'':'cc'),1.1*s);
  // the bones: the arm thick, the fingers thinner, a rim then a light top
  const bone=dragon?'#d9b44a':p.s,boneL=dragon?'#ffe08a':'#6d5a8c',arm=P(T,[['M',0,0],['L',...E],['L',...W]]);
  K.stroke(c,arm,RIM,(dragon?6.4:5.4)*s);K.stroke(c,arm,bone,(dragon?4.4:3.6)*s);K.stroke(c,arm,boneL,1.2*s);
  for(const f of F){const q=P(T,[['M',...W],['Q',...mix(mix(W,f,.5),E,-.06),...f]]);K.stroke(c,q,RIM,(dragon?3.6:3)*s);K.stroke(c,q,bone,(dragon?2.2:1.7)*s);}
  for(const f of F)K.E(c,...T(...f),1.4*s,1.4*s,dragon?'#ffe08a':'#d8c8ee');
  // the thumb claw at the wrist
  K.P(c,[T(W[0]-4,W[1]+2),T(W[0]-3,W[1]-12),T(W[0]+5,W[1]-1)],RIM);K.P(c,[T(W[0]-2.6,W[1]+.5),T(W[0]-2.4,W[1]-9),T(W[0]+3,W[1]-1)],dragon?p.m:'#e6d8ff');
  if(dragon){
    // spikes along the arm, scales on it
    for(let i=1;i<6;i++){const u=i/6,a=u<.5?mix([0,0],E,u*2):mix(E,W,(u-.5)*2),o=[a[0]-5,a[1]-4];K.P(c,[T(a[0]-3,a[1]),T(...o),T(a[0]+2,a[1]-2)],RIM);K.P(c,[T(a[0]-2,a[1]),T(o[0]+.8,o[1]+1),T(a[0]+1.4,a[1]-1.6)],p.m);}
    for(let i=0;i<7;i++){const u=(i+.5)/7,a=u<.5?mix([0,0],E,u*2):mix(E,W,(u-.5)*2);const [x,y]=T(a[0]+3,a[1]+4);K.E(c,x,y,2.4*s,1.7*s,'#2f8a52');K.E(c,x-.4*s,y-.5*s,1.2*s,.8*s,'#9fe0b0');}
  }
}
/** Two translucent veined panes (tiên): a soft glow round them, white veins, a shine of pink and blue. */
function fairy(c,K,T,p,r,s){
  const up=[['M',0,-3],['C',6,-36,52,-86,88,-86],['C',108,-86,102,-56,72,-38],['C',48,-22,18,-8,0,-3],['Z']];
  const lo=[['M',0,2],['C',22,-6,62,-2,72,22],['C',78,38,58,46,42,36],['C',26,26,10,12,0,2],['Z']];
  const edge=edgeOf(r);
  for(const [q,tip] of [[lo,[64,30]],[up,[90,-80]]]){
    const d=P(T,q),[x1,y1]=T(0,0),[x2,y2]=T(...tip);
    K.stroke(c,d,p.a+'55',6*s);K.stroke(c,d,rimOf(r,'99'),2*s);
    K.pathG(c,d,'#ffffffcc',p.a+'99',x1,y1,x2,y2);
    const [a1,b1]=T(tip[0]*.3,tip[1]*.1+10),[a2,b2]=T(tip[0]*.8,tip[1]*.9);K.pathG(c,d,'#ffb8ec00','#ffb8ec80',a1,b1,a2,b2);
    K.stroke(c,d,edge?edge:p.s,(edge?1.3:1.1)*s);K.stroke(c,d,'#ffffffcc',.6*s);
  }
  const vein=(a,b,cc)=>K.stroke(c,P(T,[['M',...a],['Q',...cc,...b]]),'#ffffffd0',.9*s);
  vein([2,-4],[88,-82],[34,-52]);vein([12,-12],[98,-66],[56,-40]);vein([30,-36],[64,-78],[50,-54]);vein([40,-30],[86,-50],[66,-36]);
  vein([2,2],[66,26],[34,4]);vein([10,8],[48,36],[30,24]);
  for(const [x,y] of [[66,-72],[82,-58],[50,-52],[52,16],[36,22]]){const [a,b]=T(x,y);K.E(c,a,b,1.1*s,1.1*s,'#ffffffd8');}
  for(const [x,y,k] of [[90,-84,1],[66,30,.75]]){const [a,b]=T(x,y);star(c,K,a,b,3.6*k*s,'#ffffff');}
}
/** Butterfly wings: a deep root to a bright field, a dark band with white spots along the edge, eyes on both. */
function butterfly(c,K,T,p,r,s){
  const fore=[[0,-2],[4,-36],[36,-80],[84,-86],[100,-70],[90,-40],[66,-14],[30,-4]],hind=[[0,2],[34,-6],[72,4],[78,26],[60,42],[50,58],[38,50],[18,30]];
  const inner=(pts,cx,cy,k)=>pts.map(([x,y])=>[cx+(x-cx)*k,cy+(y-cy)*k]);
  const edge=edgeOf(r),fw=P(T,loop(fore)),hw=P(T,loop(hind));
  K.stroke(c,hw,rimOf(r),2.6*s);K.stroke(c,fw,rimOf(r),2.6*s);
  for(const [d,pts,cx,cy,tip] of [[hw,hind,14,10,[66,40]],[fw,fore,16,-14,[92,-74]]]){
    K.path(c,d,p.s);
    const di=P(T,loop(inner(pts,cx,cy,.8))),[x1,y1]=T(0,0),[x2,y2]=T(...tip);K.pathG(c,di,p.b,p.a,x1,y1,x2,y2);
    const [a1,b1]=T(tip[0]*.2,tip[1]*.2),[a2,b2]=T(tip[0]*.65,tip[1]*.65);K.pathG(c,P(T,loop(inner(pts,cx,cy,.55))),p.l+'00',p.l+'99',a1,b1,a2,b2);
  }
  // the veins
  for(const [x,y] of [[36,-60],[64,-72],[80,-56],[70,-30],[40,-18],[40,20],[60,24],[48,44]]){const [a,b]=T(2,0),[e,g]=T(x,y);K.L(c,a,b,e,g,p.s+'70',.8*s);}
  // white spots along the band
  for(const [x,y,z] of [[90,-78,1.6],[96,-64,1.4],[92,-48,1.2],[82,-34,1.1],[72,-82,1.3],[58,-82,1.1],[72,34,1.2],[58,48,1.1],[76,18,1]]){const [a,b]=T(x,y);K.E(c,a,b,z*s,z*s,'#ffffffe0');}
  // the eyes
  const [ex,ey]=T(50,24),[fx,fy]=T(74,-62);
  K.E(c,ex,ey,7*s,7*s,p.s);K.E(c,ex,ey,5*s,5*s,p.m);K.E(c,ex,ey,2.8*s,2.8*s,p.s);K.E(c,ex-1*s,ey-1*s,1.1*s,1.1*s,'#fff');
  K.E(c,fx,fy,4.6*s,4.6*s,p.s);K.E(c,fx,fy,3.2*s,3.2*s,p.m);K.E(c,fx-.7*s,fy-.7*s,1*s,1*s,'#fff');
  if(edge){K.stroke(c,fw,edge+(r>=4?'':'cc'),1.1*s);K.stroke(c,hw,edge+(r>=4?'':'cc'),1.1*s);}
}
const DRAW={buom:butterfly,tien:fairy,doi:(c,K,T,p,r,s)=>membrane(c,K,T,p,r,s),thien_than:(c,K,T,p,r,s)=>feathered(c,K,T,p,r,s),
  rong:(c,K,T,p,r,s)=>membrane(c,K,T,p,r,s,{dragon:true}),phuong:(c,K,T,p,r,s)=>feathered(c,K,T,p,r,s,{fire:true})};
/** Huyền thoại: a gold line round the wing and an iridescent sheen over it (drawn over the style). */
function legend(c,K,T,k,s){
  const sil={buom:[[0,-2],[36,-80],[100,-70],[66,-14],[72,4],[50,58],[0,2]],tien:[[0,-3],[88,-86],[72,-38],[72,22],[42,36],[0,2]],
    doi:[[0,0],[46,-74],[98,-66],[106,-34],[70,22],[8,15]],rong:[[0,0],[50,-82],[108,-74],[116,-38],[78,26],[8,18]],
    thien_than:[[0,0],[20,-58],[74,-80],[104,-72],[100,-28],[66,24],[30,46],[8,38]],phuong:[[0,0],[20,-58],[74,-80],[112,-84],[110,-10],[64,40],[22,52],[8,40]]}[k];
  const d=P(T,loop(sil,1/7)),[a,b]=T(0,10),[e,g]=T(100,-80);
  K.pathG(c,d,'#ffffff00','#fff3b02c',a,b,e,g);K.pathG(c,d,'#c8a0ff00','#8fe8ff22',...T(100,0),...T(10,-80));
}
/* ---- ✨ the motion and the light (owner 22/10 "cánh có hoạt họa, có tia sáng này kia nhé") ----
 * Every place gets the same beat from the same numbers, so the classic street, the workplace, the shop's SVG and the 2.5D
 * map flap alike:
 *   flapAt(k, t, walk)  the flap -1…1 at t seconds: a sine of the style's own beat, butterfly and fairy quick and light,
 *                  bat and dragon slow and heavy; standing a gentle half beat, walking the full stroke a little faster
 *   wingMotes(wg)  the sparkles drifting off the wings, a fixed list per tier (few D–A, more from S, a burst of gold or
 *                  rainbow motes for SSS / Huyền thoại); moteAt(m, t) where one is at t (a pure function: no state, no
 *                  timers, the 2.5D map moves its pooled images with it)
 *   wingPulse(t)   the glow's breath, raysAt(r, t) the slow turn of the light rays from S, burstAt(t) the ring of SSS / HT
 * A canvas pen draws a frame at `t`; the SVG pen (K.anim) writes SMIL animations once and the browser plays them. Reduced
 * motion (the setting, html / body .reduce-motion, prefers-reduced-motion): still wings, the glow and rays still, no motes. */
export const WING_BEAT=Object.freeze({buom:1.3,tien:1.5,doi:2.4,thien_than:2,rong:2.6,phuong:1.8});
const AMP={buom:1,tien:.9,doi:.75,thien_than:.8,rong:.7,phuong:.85};
const MOTES=[2,2,3,3,5,6,8,9],RAYS=[0,0,0,0,6,8,10,10];
/** The light's centre above the roots (the rays, the ring), in the wings' units before the scale. */
export const LIGHT_Y=30;
const RM=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)');
/** True while the player wants still pictures. */
export function stillMotion(){const d=globalThis.document;return !!(RM?.matches||d?.documentElement?.classList?.contains('reduce-motion')||d?.body?.classList?.contains('reduce-motion'));}
export function flapAt(k,t,walk=false){return (AMP[k]||.8)*(walk?1:.5)*Math.sin(2*Math.PI*t/((WING_BEAT[k]||2)*(walk?.7:1)));}
export const wingPulse=t=>.78+.22*Math.sin(2*Math.PI*t/2.2);
export const raysAt=(r,t)=>r>=4?{n:RAYS[r],rot:t*.22,a:.8+.2*Math.sin(2*Math.PI*t/2.2+1)}:null;
/** The ring of light SSS / Huyền thoại send out every 2.6 s: grow 0…1 and fade (null between two). */
export const burstAt=t=>{const ph=((t/2.6)%1+1)%1;return ph<.6?{ph:ph/.6,a:.6*(1-ph/.6)}:null;};
const moteCol=(r,i)=>r===TOP?(i%2?'#fff3b0':'#ffd24a'):r===6?RB[i%6]:r===5?(i%2?'#ffffff':WING_TIER_COLOR[5]):r>=1&&i%3===2?WING_TIER_COLOR[r]:'#ffffff';
/** The sparkles of a wing, in the wings' frame (the roots' centre at 0,0, up negative, before the scale): each starts at
 * (x, y), drifts (dx, dy) over `life` seconds from its offset `off` (0…1), `sz` its size; `burst` the SSS / HT motes that
 * fly out of the centre with the ring. */
const MOTE_SETS=new Map();   // 23/10 lag: the list depends only on the tier; built once per tier, not per walker per frame
export function wingMotes(wg){
  const w=cleanWing(wg);if(!w)return [];const r=w.r;let out=MOTE_SETS.get(r);if(out)return out;out=[];
  for(let i=0;i<MOTES[r];i++){const side=i%2?1:-1,u=(i*.381966)%1,v=(i*.618034)%1;
    out.push({x:side*(44+u*56),y:-80+v*100,dx:side*(6+u*10),dy:-(16+((i*.7)%1)*16),life:1.5+((i*.437)%1)*1.1,off:(i*.723)%1,sz:(r>=6?3.2:r>=4?2.8:2.3)*(i%3?1:1.3),col:moteCol(r,i),star:i%3!==1});}
  if(r>=6)for(let i=0;i<8;i++){const a=i/8*Math.PI*2+.3;out.push({x:Math.cos(a)*10,y:-LIGHT_Y+Math.sin(a)*8,dx:Math.cos(a)*84,dy:Math.sin(a)*60-8,life:2.6,off:0,sz:2.3,col:r===TOP?(i%2?'#ffe58a':'#fffbe0'):RB[i%6],star:false,burst:true});}
  out.forEach(Object.freeze);Object.freeze(out);MOTE_SETS.set(r,out);return out;   // shared: frozen so no caller edits it
}
/** Where mote `m` is at t: {x, y} in the wings' frame, `a` its opacity 0…1. */
export function moteAt(m,t){
  const ph=((t/m.life+m.off)%1+1)%1,a=m.burst?(ph<.6?Math.sin(Math.PI*Math.min(1,ph/.3)/2)*(1-ph/.6):0):Math.sin(Math.PI*ph);
  const k=m.burst?Math.min(1,ph/.6):ph;return {x:m.x+m.dx*k,y:m.y+m.dy*k,a};
}
const hexA=(col,a)=>col+Math.round(Math.max(0,Math.min(1,a))*255).toString(16).padStart(2,'0');
/** The light rays behind the wings from S (centred above the roots), turned by `rot`, faded by `k`. */
export function drawRays(c,K,r,x,y,s,rot=0,k=1){
  if(r<4)return;const n=RAYS[r],L=(r>=6?118:r===5?104:90)*s,w=(r>=6?8:7)*s,cy=y-LIGHT_Y*s;
  for(let i=0;i<n;i++){const a=rot+i/n*Math.PI*2,dx=Math.cos(a),dy=Math.sin(a),col=r===TOP?'#ffe9a0':r===6?RB[i%6]:i%2?'#ffffff':WING_TIER_COLOR[r];
    const d=`M${n1(x-dy*w)} ${n1(cy+dx*w)}L${n1(x+dx*L)} ${n1(cy+dy*L)}L${n1(x+dy*w)} ${n1(cy-dx*w)}Z`;K.pathG(c,d,hexA(col,(r>=6?.42:.32)*k),hexA(col,0),x,cy,x+dx*L,cy+dy*L);}
}
/** The ring of SSS / Huyền thoại at burst progress `ph`, opacity `a`. */
export function drawRing(c,K,r,x,y,s,ph,a){if(r<6||a<=0)return;const col=r===TOP?'#ffe58a':'#ffffff';K.ring(c,x,y-LIGHT_Y*s,(16+ph*74)*s,hexA(col,a),(2.6-ph*1.6)*s);K.ring(c,x,y-LIGHT_Y*s,(12+ph*60)*s,hexA(r===TOP?'#ffd24a':RB[Math.floor(ph*6)%6],a*.6),1.2*s);}
function mote(c,K,m,x,y,s,a){const col=hexA(m.col,a),z=m.sz*s*(.6+.4*a);if(m.star)star(c,K,x,y,z*1.4,col);else{K.E(c,x,y,z*1.6,z*1.6,hexA(m.col,a*.25));K.E(c,x,y,z*.7,z*.7,col);}}
/** The motes of `wg` at t, over the wings rooted at (x, y), scale s; `burst` true only the burst (drawn behind the body:
 * they leave from its centre), false only the drifting ones (over it), null all. */
export function drawMotes(c,K,wg,x,y,s,t,burst=null){for(const m of wingMotes(wg)){if(burst!=null&&!!m.burst!==burst)continue;const p=moteAt(m,t);if(p.a>.04)mote(c,K,m,x+p.x*s,y+p.y*s,s,p.a);}}
/** The tier behind both wings: from S a soft halo hugging each wing, richer at SS, a rainbow for SSS, gold for Huyền
 * thoại; `k` the breath (wingPulse). */
function auraBack(c,K,x,y,r,s,k=1){
  if(r<4)return;
  const both=(col,a,rx=70,ry=66,dy=24)=>{for(const side of [-1,1])K.glow(c,x+side*52*s,y-dy*s,rx*s,ry*s,col,a*k);};
  if(r===TOP){both('#ffd24a',.4,78,72);K.glow(c,x,y-34*s,60*s,50*s,'#fff3b0',.36*k);both('#fff7d6',.26,44,40,40);return;}
  if(r===6){RB.forEach((col,i)=>K.glow(c,x+(i-2.5)*26*s,y-26*s,54*s,60*s,col,.22*k));both('#ffffff',.2,54,50);return;}
  both(WING_TIER_COLOR[r],r>=5?.42:.3);if(r>=5)both('#ffffff',.22,46,42,36);
}
/** Still sparkles over the wings (a still picture: the 2.5D stamp, reduced motion): from SS. */
function auraFront(c,K,x,y,r,s,side=1){
  if(r<5)return;
  const pts=[[-78,-66],[84,-50],[-56,-24],[66,-6],[-92,-40],[44,-86]];
  pts.slice(0,r>=6?6:3).forEach(([px,py],i)=>{const col=r===TOP?(i%2?'#fff3b0':'#ffd24a'):r===6?RB[i%6]:'#ffffff';star(c,K,x+side*px*s,y+py*s,(i%3?2.2:3.2)*s,col);});
  if(r===TOP)for(const [px,py] of [[-34,-92],[30,-96],[0,-100]])K.E(c,x+px*s,y+py*s,1.6*s,1.6*s,'#ffe58a');
}
/* SMIL for the SVG pen: written once, played by the browser (no script per frame). */
const SPL='calcMode="spline" keyTimes="0;.5;1" keySplines=".45 0 .55 1;.45 0 .55 1"';
const rep=(dur,begin=0)=>`dur="${n1(dur*100)/100}s" begin="${n1(begin*100)/100}s" repeatCount="indefinite"`;
function svgFlap(k,side,ox,oy){const a=6*(AMP[k]||.8),b=WING_BEAT[k]||2,v=d=>`${n1(side*d)} ${n1(ox)} ${n1(oy)}`;return `<g><animateTransform attributeName="transform" type="rotate" values="${v(-a)};${v(a)};${v(-a)}" ${SPL} ${rep(b,-b/4)}/>`;}
function svgMote(c,K,m,x,y,s){
  const begin=-m.off*m.life,op=m.burst?'values="0;1;0;0" keyTimes="0;.15;.6;1"':'values="0;1;0" keyTimes="0;.5;1"',dx=m.dx*s,dy=m.dy*s;
  const tr=m.burst?`values="0 0;${n1(dx)} ${n1(dy)};${n1(dx)} ${n1(dy)}" keyTimes="0;.6;1"`:`values="0 0;${n1(dx)} ${n1(dy)}"`;
  c.push(`<g opacity="0"><animateTransform attributeName="transform" type="translate" ${tr} ${rep(m.life,begin)}/><animate attributeName="opacity" ${op} ${rep(m.life,begin)}/>`);mote(c,K,m,x+m.x*s,y+m.y*s,s,1);c.push('</g>');
}
function svgLights(c,K,w,x,y,s,front){
  const r=w.r;
  if(!front){
    if(r>=4){c.push(`<g><animate attributeName="opacity" values=".72;1;.72" ${SPL} ${rep(2.2)}/>`);auraBack(c,K,x,y,r,s);c.push('</g>');
      c.push(`<g><animateTransform attributeName="transform" type="rotate" values="0 ${n1(x)} ${n1(y-LIGHT_Y*s)};360 ${n1(x)} ${n1(y-LIGHT_Y*s)}" ${rep(28)}/><animate attributeName="opacity" values=".6;1;.6" ${SPL} ${rep(2.2,-1)}/>`);drawRays(c,K,r,x,y,s);c.push('</g>');}
    for(const m of wingMotes(w))if(m.burst)svgMote(c,K,m,x,y,s);
    if(r>=6){const col=r===TOP?'#ffe58a':'#ffffff';c.push(`<circle cx="${n1(x)}" cy="${n1(y-LIGHT_Y*s)}" r="${n1(16*s)}" fill="none" stroke="${col}" stroke-width="${n1(2*s)}" opacity="0"><animate attributeName="r" values="${n1(16*s)};${n1(90*s)};${n1(90*s)}" keyTimes="0;.6;1" ${rep(2.6)}/><animate attributeName="opacity" values=".6;0;0" keyTimes="0;.6;1" ${rep(2.6)}/></circle>`);}
    return;
  }
  for(const m of wingMotes(w))if(!m.burst)svgMote(c,K,m,x,y,s);
}
/** Both wings of `wg` with their roots at (x, y) (the shoulder blades' centre), `gap` apart, scale `s`; `aura` the glow
 * behind them, `body` the wings themselves, `sparkle` the sparkles over them. `t` (seconds) draws a canvas frame of the
 * motion (flap, breathing glow, turning rays, drifting motes), `walk` the walking stroke; `flap` forces a flap instead;
 * the SVG pen animates by itself unless `anim` is false or the player wants stillness. */
export function drawWings(c,K,wg,x,y,{s=1,gap=6,flap=null,sparkle=true,tall=1,spread=0,aura=true,body=true,t=null,anim=true,walk=false}={}){
  const w=cleanWing(wg);if(!w)return;
  const p=PAL[w.k],r=w.r,ss=s*(.94+.018*r),still=stillMotion();
  const live=!!K.anim&&anim&&!still,tt=t!=null&&!still&&!live?t:null,f=flap??(tt!=null?flapAt(w.k,tt,walk):0);
  if(aura){if(live)svgLights(c,K,w,x,y,ss,false);
    else{auraBack(c,K,x,y,r,ss,tt!=null?wingPulse(tt):1);const ry=tt!=null?raysAt(r,tt):null;if(ry)drawRays(c,K,r,x,y,ss,ry.rot,ry.a);
      const b=tt!=null?burstAt(tt):null;if(b)drawRing(c,K,r,x,y,ss,b.ph,b.a);if(tt!=null&&r>=6)drawMotes(c,K,w,x,y,ss,tt,true);}}
  if(body)for(const side of [-1,1]){const ox=x+side*gap*s,z=ss*SIZE[w.k],T=frame(ox,y,z,side,live?0:f,tall,spread);if(live)c.push(svgFlap(w.k,side,ox,y));DRAW[w.k](c,K,T,p,r,z);if(r===TOP)legend(c,K,T,w.k,z);if(live)c.push('</g>');}
  if(sparkle){if(live)svgLights(c,K,w,x,y,ss,true);else if(tt!=null)drawMotes(c,K,w,x,y,ss,tt,false);else auraFront(c,K,x,y,r,ss);}
}
/** The sparkles alone (the 2.5D stamp draws its wings behind the chibi, then these over it); `t` animates them. */
export function wingSparkles(c,K,wg,x,y,{s=1,t=null}={}){const w=cleanWing(wg);if(!w)return;const ss=s*(.94+.018*w.r);if(t!=null&&!stillMotion())drawMotes(c,K,w,x,y,ss,t,false);else auraFront(c,K,x,y,w.r,ss);}
/** The wings' scale for `s` (each tier a touch larger). */
export const wingScale=(wg,s=1)=>{const w=cleanWing(wg);return w?s*(.94+.018*w.r):s;};
/** On the classic character (origin at the feet; paintPlayer, boba-world.js): roots behind the shoulder blades, the
 * pair rising past the big head. F.L.wg the wing; `t` a canvas scene's clock (boba-world.js: flaps from cached bitmaps,
 * breathes, sparkles), `walk` its walking stroke, `flap` a fixed flap. */
export const CLASSIC_WING=Object.freeze({at:[0,-54],s:.72,gap:5,tall:1.04,spread:-.04});
/** The box (w, h, roots x, roots y) of a pair's cached bitmap in the wings' units at scale 1: room for the biggest
 * style at Huyền thoại, its flap and stretch. */
export const WING_BOX=Object.freeze([280,206,140,138]);
export function paintWings(c,F,K,{at=null,s=CLASSIC_WING.s,flap=null,tall=CLASSIC_WING.tall,spread=CLASSIC_WING.spread,t=null,walk=false,sparkle=true,aura=true,body=true}={}){
  const w=cleanWing(F?.L?.wg);if(!w)return;
  const [x,y]=at||CLASSIC_WING.at,o={s,gap:CLASSIC_WING.gap,tall,spread};
  // a canvas scene's frame: the wings from a cached bitmap (no paths rebuilt each frame), the light drawn around it
  const m=t!=null&&body&&!K.anim&&typeof c.getTransform==='function'?c.getTransform():null;
  if(m){const px=Math.max(.5,Math.round(Math.hypot(m.a,m.b)*4)/4),still=stillMotion(),bm=wingBitmap(K,w,still?0:flapStep(flapAt(w.k,t,walk)),o,WING_BOX.map(v=>v*s),px,'paint');
    if(bm){if(aura)drawWings(c,K,w,x,y,{...o,t,body:false,sparkle:false});c.drawImage(bm.canvas,x-bm.ox,y-bm.oy,bm.w,bm.h);if(sparkle)drawWings(c,K,w,x,y,{...o,t,aura:false,body:false});return;}}
  drawWings(c,K,w,x,y,{...o,t,walk,sparkle,aura,body,flap:flap??(t==null&&F?.wf!=null?Number(F.wf)||0:null)});
}
/** The tips peeking behind the round bust (80×80, drawn first): still, a portrait is everywhere. */
export function wingsBust(c,K,wg){const w=cleanWing(wg);if(!w)return;drawWings(c,K,w,40,64,{s:.4,gap:6,sparkle:false,anim:false});}
/** A pair large, centred in a -30…30 box (the shop's tiles): flapping and sparkling in SVG. */
export function wingIcon(c,K,wg){const w=cleanWing(wg);if(!w)return;drawWings(c,K,w,0,10,{s:.25,gap:1.5});}
/* ---- cached bitmaps for canvases that redraw often (the classic street, the workplace, the 2.5D map): a few flaps ---- */
export const FLAP_STEPS=Object.freeze([-1,-.75,-.5,-.25,0,.25,.5,.75,1]);
/** The nearest cached flap to f. */
export const flapStep=f=>FLAP_STEPS.reduce((a,b)=>Math.abs(b-f)<Math.abs(a-f)?b:a,0);
const BITMAPS=new Map();
/** The wings alone (no glow, no motes) at flap step `f` on a canvas: `opts` drawWings' (s, gap, tall, spread), `box`
 * [w, h, ox, oy] the canvas in the wings' units with the roots at (ox, oy), `px` pixels per unit. Kept (at most 160). */
export function wingBitmap(K,wg,f,opts,box,px=1,tag=''){
  const w=cleanWing(wg),doc=globalThis.document;if(!w||!doc?.createElement)return null;
  const key=JSON.stringify([tag,w.k,w.r,f,px,box,opts]);let hit=BITMAPS.get(key);if(hit){BITMAPS.delete(key);BITMAPS.set(key,hit);return hit;}
  const cv=doc.createElement('canvas');cv.width=Math.ceil(box[0]*px);cv.height=Math.ceil(box[1]*px);const q=cv.getContext?.('2d');if(!q)return null;
  q.setTransform(px,0,0,px,box[2]*px,box[3]*px);q.lineJoin='round';drawWings(q,K,w,0,0,{...opts,flap:f,aura:false,sparkle:false,anim:false});
  hit={canvas:cv,ox:box[2],oy:box[3],w:box[0],h:box[1]};BITMAPS.set(key,hit);if(BITMAPS.size>160)BITMAPS.delete(BITMAPS.keys().next().value);return hit;
}
