/** 🏝️ Đảo riêng: the map of each private island (game/island_content.py `look`), shared by both interfaces: the old
 * one's 2D walk (v4/island-walk.js) and the new one's isometric scene (client/isometric/private-island.ts). Positions
 * are fractions of the island's square map (x to the east, y to the south, 0..1), the same numbers the live room
 * sends (live/island.py isl_mv). Pure data and geometry: no DOM, no canvas.
 *   shore   the coast (walkable inside), sand  how wide the beach is, palms, villa {x,y,w,h,floors}, dock {x,y,w,h}
 *   (walkable, a boat arrives at its far end), pad {x,y,kind: heli|strip} (a helicopter / a plane arrives there),
 *   spots [{id, emoji, name, x, y, pose}] (walk up to one: a line, a pose, the others see it), deco (the island's own
 *   art: reef, rocks, steam, lighthouse, pool…), blocks (not walkable: the villa, a mountain).
 *   plots [[x, y, coast]] 🏗️ the building plots (game/island_build_content.py PLOTS: the same numbers, the same order;
 *   tests/test_island_build.py checks it). withBuilds(L, builds) adds what stands on them: blocks, spots, piers. */

import {HOUSES,splitKind} from './house-art.js';

const TAU=Math.PI*2;
/** An organic coast: an ellipse whose radius wobbles by `bumps` (one value per control point), smoothed. */
function blob(cx,cy,rx,ry,bumps,steps=48){
  const n=bumps.length,out=[];
  for(let i=0;i<steps;i++){
    const a=i/steps*TAU,f=a/TAU*n,k=Math.floor(f),t=f-k,b0=bumps[k%n],b1=bumps[(k+1)%n],w=b0+(b1-b0)*(1-Math.cos(t*Math.PI))/2;
    out.push([+(cx+Math.cos(a)*rx*w).toFixed(4),+(cy+Math.sin(a)*ry*w).toFixed(4)]);
  }
  return out;
}

export const EMOTES=[['wave','👋','Vẫy tay'],['heart','❤️','Thả tim'],['laugh','😂','Cười lớn'],['wow','😮','Ồ'],['dance','💃','Nhảy'],['cheers','🥂','Cụng ly']];

const SPOTS={
  vong:{emoji:'🛏️',name:'Võng giữa hai cây dừa',pose:'lie',lines:['Đung đưa trên võng, gió biển thổi mát rượi.','Nằm võng nghe sóng vỗ, suýt ngủ quên.']},
  lua:{emoji:'🔥',name:'Lửa trại',pose:'sit',lines:['Ngồi quanh lửa trại, nướng mấy con mực khô.','Lửa tí tách, ai cũng kể một chuyện cũ.']},
  bar:{emoji:'🍹',name:'Quầy bar bãi biển',pose:'stand',lines:['Gọi ly nước dừa ướp lạnh, cắm thêm cây dù nhỏ.','Bartender lắc một ly mocktail chanh dây.']},
  lan:{emoji:'🤿',name:'Chỗ lặn biển',pose:'swim',lines:['Lặn xuống thấy đàn cá sọc vàng bơi ngang.','Nước trong veo, nhìn rõ cả sao biển dưới đáy.']},
  nha_san:{emoji:'🛖',name:'Nhà sàn trên biển',pose:'sit',lines:['Ngồi thả chân xuống làn nước xanh dưới sàn gỗ.','Nhìn qua sàn kính thấy cá bơi ngay dưới chân.']},
  san_ho:{emoji:'🪸',name:'Rạn san hô',pose:'swim',lines:['San hô đủ màu, một chú cá hề thò đầu ra chào.','Bơi chậm qua rạn san hô, không chạm vào đâu nhé.']},
  suoi:{emoji:'♨️',name:'Suối nước nóng',pose:'swim',lines:['Ngâm mình trong suối nóng, mây trôi ngang vai.','Hơi nước bốc lên, mệt mỏi tan hết.']},
  dai:{emoji:'🔭',name:'Đài ngắm sao',pose:'stand',lines:['Chỉnh ống nhòm, thấy cả vành đai sao mờ.','Trên đỉnh đồi, mây trôi ngay dưới chân.']},
  hai_dang:{emoji:'🗼',name:'Hải đăng',pose:'stand',lines:['Leo lên ngọn hải đăng, cả vịnh trải dài trước mặt.','Ánh đèn quét một vòng qua mặt biển.']},
  ho_boi:{emoji:'🏊',name:'Hồ bơi tràn bờ',pose:'swim',lines:['Bơi ra mép hồ, biển và trời liền một màu.','Tựa mép hồ ngắm mặt trời lặn đỏ rực.']},
};
const spot=(id,x,y)=>({id,x,y,...SPOTS[id]});

export const LOOKS={
  dua:{name:'Đảo Dừa',sea:'#58b4c8',deep:'#2f8aa6',sand:'#f2dfae',grass:'#8cc56f',grassDark:'#6fae58',
    shape:[.5,.5,.38,.36,[1,.96,1.04,.98,1.02,.93,1,1.05]],shore:blob(.5,.5,.38,.36,[1,.96,1.04,.98,1.02,.93,1,1.05]),sandWidth:.07,
    palms:[[.24,.38],[.3,.3],[.2,.55],[.31,.64],[.72,.3],[.78,.42],[.62,.24],[.4,.78],[.66,.8]],
    villa:{x:.5,y:.36,w:.17,h:.11,floors:1,roof:'#b7663f',wall:'#f4e6cc'},
    dock:{x:.47,y:.82,w:.06,h:.16},pad:{x:.76,y:.58,kind:'heli'},
    spots:[spot('vong',.25,.47),spot('lua',.42,.7),spot('bar',.62,.68),spot('lan',.15,.42)],deco:[],
    plots:[[.37,.52,0],[.46,.52,0],[.55,.52,0],[.37,.61,0],[.46,.61,0],[.7,.72,1]]},
  san_ho:{name:'Đảo San Hô',sea:'#4fc3c9',deep:'#2c95ad',sand:'#f7ead0',grass:'#9fd07a',grassDark:'#7cb860',
    shape:[.48,.55,.4,.27,[1,1.05,.92,1,1.06,.95,1.02,.97]],shore:blob(.48,.55,.4,.27,[1,1.05,.92,1,1.06,.95,1.02,.97]),sandWidth:.085,
    palms:[[.17,.45],[.3,.6],[.82,.5],[.8,.42],[.16,.6],[.62,.79],[.8,.62]],
    villa:{x:.27,y:.47,w:.14,h:.09,floors:1,roof:'#4f9bb5',wall:'#fbf3e4'},
    dock:{x:.24,y:.21,w:.05,h:.28},pad:{x:.72,y:.62,kind:'heli'},
    spots:[spot('nha_san',.3,.12),spot('san_ho',.86,.32),spot('vong',.6,.55),spot('bar',.38,.62),spot('lua',.2,.62)],
    deco:[{t:'reef',x:.86,y:.28,r:.07},{t:'reef',x:.12,y:.84,r:.05},{t:'reef',x:.7,y:.9,r:.04},{t:'hut',x:.33,y:.09},{t:'hut',x:.4,y:.13}],
    walk:[{x:.33,y:.12,w:.14,h:.04}],
    plots:[[.41,.38,0],[.5,.38,0],[.59,.38,0],[.68,.38,0],[.41,.47,0],[.5,.47,0],[.37,.7,0],[.46,.7,0],[.55,.7,0],[.13,.54,1]]},
  may_da:{name:'Đảo Mây Đá',sea:'#5a9fb6',deep:'#336f8c',sand:'#cbb994',grass:'#7fa86a',grassDark:'#5f8a54',rock:'#5d5560',
    shape:[.5,.5,.39,.37,[1,.9,1.06,.96,1.04,.9,1.02,1.08,.94]],shore:blob(.5,.5,.39,.37,[1,.9,1.06,.96,1.04,.9,1.02,1.08,.94]),sandWidth:.05,
    palms:[[.14,.52],[.3,.76],[.67,.77],[.8,.58],[.2,.43]],
    villa:{x:.33,y:.38,w:.13,h:.09,floors:2,roof:'#4b4650',wall:'#e6ddd2'},
    dock:{x:.6,y:.84,w:.05,h:.14},pad:{x:.72,y:.42,kind:'heli'},
    spots:[spot('dai',.56,.24),spot('suoi',.2,.62),spot('lua',.45,.78),spot('lan',.87,.62)],
    deco:[{t:'peak',x:.56,y:.3,r:.13},{t:'steam',x:.2,y:.59},{t:'steam',x:.6,y:.18},{t:'rocks',x:.18,y:.3},{t:'rocks',x:.82,y:.8}],
    blocks:[{x:.5,y:.3,w:.14,h:.08}],
    plots:[[.26,.5,0],[.35,.5,0],[.44,.5,0],[.53,.5,0],[.62,.5,0],[.35,.59,0],[.44,.59,0],[.53,.59,0],[.62,.59,0],[.71,.59,0],[.35,.68,0],[.44,.68,0],[.53,.68,0],[.62,.68,0],[.26,.68,0],[.71,.68,1]]},
  hoang_hon:{name:'Đảo Hoàng Hôn',sea:'#e59a6a',deep:'#b4627a',sand:'#f6d6a6',grass:'#9bbf6a',grassDark:'#7da356',
    shape:[.5,.52,.43,.4,[1,1.03,.97,1.05,1,.95,1.04,.98]],shore:blob(.5,.52,.43,.4,[1,1.03,.97,1.05,1,.95,1.04,.98]),sandWidth:.06,
    palms:[[.11,.62],[.24,.68],[.88,.62],[.76,.68],[.35,.87],[.66,.86],[.14,.36]],
    villa:{x:.4,y:.31,w:.2,h:.11,floors:3,roof:'#8a4d3a',wall:'#fff4e2'},
    dock:{x:.6,y:.88,w:.06,h:.11},pad:{x:.5,y:.2,kind:'strip'},
    spots:[spot('hai_dang',.86,.36),spot('ho_boi',.5,.6),spot('bar',.3,.7),spot('vong',.72,.74),spot('lua',.42,.82)],
    deco:[{t:'strip',x:.5,y:.2,w:.56,h:.06},{t:'lighthouse',x:.86,y:.32},{t:'pool',x:.5,y:.6,w:.16,h:.06}],
    plots:[[.56,.3,0],[.65,.3,0],[.74,.3,0],[.215,.43,0],[.305,.43,0],[.215,.52,0],[.305,.52,0],[.305,.61,0],[.4,.42,0],[.49,.42,0],[.58,.42,0],[.4,.51,0],[.49,.51,0],[.58,.51,0],[.68,.43,0],[.77,.43,0],[.68,.52,0],[.77,.52,0],[.68,.61,0],[.4,.72,0],[.49,.72,0],[.58,.72,0],[.12,.52,1],[.88,.5,1]]},
};
for(const [id,L] of Object.entries(LOOKS))L.look=id;
export const LOOK_IDS=Object.keys(LOOKS);
export const layout=look=>LOOKS[look]||LOOKS.dua;

export function inPoly(pts,x,y){
  let inside=false;
  for(let i=0,j=pts.length-1;i<pts.length;j=i++){const [ax,ay]=pts[i],[bx,by]=pts[j];if((ay>y)!==(by>y)&&x<(bx-ax)*(y-ay)/(by-ay)+ax)inside=!inside;}
  return inside;
}
const inRect=(r,x,y)=>x>=r.x-r.w/2&&x<=r.x+r.w/2&&y>=r.y-r.h/2&&y<=r.y+r.h/2;
/** 🏝️ The cell of the design grid under a map point (GRID below), or -1 off it. */
function cellAt(x,y){const i=Math.floor((x-GRID.X0)/GRID.CELL),j=Math.floor((y-GRID.X0)/GRID.CELL);return i>=0&&j>=0&&i<GRID.G&&j<GRID.G?j*GRID.G+i:-1;}
/** The villa's footprint, a mountain: not walkable. */
export function blocks(L){
  const v=L.villa;return [{x:v.x,y:v.y,w:v.w*.9,h:v.h*.8},...(L.blocks||[])];
}
/** Can a player stand here? Inside the coast (a hair in from the water), on the dock or a pier, never in a block. */
export function walkable(L,x,y){
  const [lo,hi]=L.bounds||[0,1];
  if(!(x>=lo&&x<=hi&&y>=lo&&y<=hi))return false;
  if(blocks(L).some(b=>inRect(b,x,y)))return false;
  const c=L.cellSolid||L.cellWalk?cellAt(x,y):-1;   // 🏝️ the decorations: a tree, a fence in the way; a pier to walk on
  if(c>=0&&L.cellSolid?.[c])return false;
  if(inRect(L.dock,x,y)||(L.walk||[]).some(r=>inRect(r,x,y))||(c>=0&&L.cellWalk?.[c]))return true;
  return inPoly(L.shore,x,y);
}
/** A walk around what stands in the way (houses, construction sites, the villa, a mountain): the points to walk through
 * to (tx, ty), the target last; [] when there is no way. A breadth-first search on a GRID² grid of the map (built once
 * per layout object), then straightened where a straight line stays walkable. Straight lines keep working on their own:
 * a target in plain sight is one point. */
const WALK_GRID=110,grids=new WeakMap();
/** The walk grid of a layout: n² cells over its bounds (0..1, or the bigger 🏝️ design map), 110 a map unit. */
function gridOf(L){
  let g=grids.get(L);if(g)return g;
  const [lo,hi]=L.bounds||[0,1],n=Math.round(WALK_GRID*(hi-lo)),span=hi-lo,m=new Uint8Array(n*n);
  for(let j=0;j<n;j++)for(let i=0;i<n;i++)m[j*n+i]=walkable(L,lo+(i+.5)/n*span,lo+(j+.5)/n*span)?1:0;
  g={m,n,lo,span};grids.set(L,g);return g;
}
export function clearWay(L,ax,ay,bx,by){
  const n=Math.max(1,Math.ceil(Math.hypot(bx-ax,by-ay)/.004));
  for(let k=1;k<=n;k++){const t=k/n;if(!walkable(L,ax+(bx-ax)*t,ay+(by-ay)*t))return false;}
  return true;
}
export function findPath(L,[sx,sy],[tx,ty]){
  if(clearWay(L,sx,sy,tx,ty))return [[tx,ty]];
  const {m:g,n:GN,lo,span}=gridOf(L),cell=v=>Math.max(0,Math.min(GN-1,Math.floor((v-lo)/span*GN)));
  const near=(i,j)=>{if(g[j*GN+i])return j*GN+i;for(let r=1;r<6;r++)for(let dj=-r;dj<=r;dj++)for(let di=-r;di<=r;di++){const a=i+di,b=j+dj;if(a>=0&&b>=0&&a<GN&&b<GN&&g[b*GN+a])return b*GN+a;}return -1;};
  const s=near(cell(sx),cell(sy)),e=near(cell(tx),cell(ty));if(s<0||e<0)return [];
  const prev=new Int32Array(GN*GN).fill(-1),q=new Int32Array(GN*GN);let h=0,n=0;q[n++]=s;prev[s]=s;
  const D=[[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]];
  while(h<n&&prev[e]<0){const c=q[h++],ci=c%GN,cj=(c-ci)/GN;
    for(const [di,dj] of D){const a=ci+di,b=cj+dj;if(a<0||b<0||a>=GN||b>=GN)continue;const k=b*GN+a;
      if(prev[k]>=0||!g[k]||(di&&dj&&(!g[cj*GN+a]||!g[b*GN+ci])))continue;prev[k]=c;q[n++]=k;}}
  if(prev[e]<0)return [];
  const cells=[];for(let c=e;c!==s;c=prev[c])cells.push(c);cells.reverse();
  const pts=cells.map(c=>{const i=c%GN;return [lo+(i+.5)/GN*span,lo+((c-i)/GN+.5)/GN*span];});
  if(walkable(L,tx,ty))pts.push([tx,ty]);
  const out=[];let from=[sx,sy];   // straighten: from each point, the furthest one in plain sight
  for(let k=0;k<pts.length;){let far=k;for(let m=pts.length-1;m>k;m--)if(clearWay(L,from[0],from[1],pts[m][0],pts[m][1])){far=m;break;}
    out.push(pts[far]);from=pts[far];k=far+1;}
  return out;
}
/** The far end of the dock (a boat), the pad (a helicopter, a plane), the dock for the island's own boat. */
export function arrival(L,kind){
  if(kind==='heli'||kind==='plane')return [L.pad.x,L.pad.y+(L.pad.kind==='strip'?.05:.02)];
  const d=L.dock;const north=d.y<.5;return [d.x,north?d.y-d.h/2+.02:d.y+d.h/2-.02];
}
/** One step of walking from (x,y) toward (tx,ty), at most `len`: slides along a wall rather than stopping dead. */
export function step(L,x,y,tx,ty,len){
  const dx=tx-x,dy=ty-y,d=Math.hypot(dx,dy);if(d<1e-6)return [x,y,true];
  const k=Math.min(1,len/d),nx=x+dx*k,ny=y+dy*k;
  if(walkable(L,nx,ny))return [nx,ny,k>=1];
  if(walkable(L,nx,y))return [nx,y,false];
  if(walkable(L,x,ny))return [x,ny,false];
  return [x,y,true];
}
/** The walkable point nearest (x,y) along the way back toward the island's middle. */
export function nearestWalkable(L,x,y){
  if(walkable(L,x,y))return [x,y];
  const c=centre(L);
  for(let i=1;i<=40;i++){const t=i/40,px=x+(c[0]-x)*t,py=y+(c[1]-y)*t;if(walkable(L,px,py))return [px,py];}
  return c;
}
export function centre(L){
  const v=L.villa;for(const [px,py] of [[v.x,v.y+v.h*.8],[.5,.62],[.5,.5]])if(walkable(L,px,py))return [px,py];
  return arrival(L,'boat');
}
/** The spot within `r` of (x,y), nearest first. */
export function spotNear(L,x,y,r=.06){
  let best=null,bd=r;for(const s of L.spots){const d=Math.hypot(s.x-x,s.y-y);if(d<=bd){best=s;bd=d;}}return best;
}
/** Where to stand to use a spot: the spot itself, or the nearest walkable point toward the middle (a dive spot at sea). */
export const standAt=(L,s)=>nearestWalkable(L,s.x,s.y);
export const spotById=(L,id)=>L.spots.find(s=>s.id===id)||null;
export const spotLine=(s,n=0)=>s.lines[Math.abs(n|0)%s.lines.length];

/* ---- 🏗️ Xây trên đảo (game/island_build.py): what stands on the plots ------------------------------------------------ */
/** A plot's side on the map (the drawings fit inside it). */
export const PLOT_W=.072;
/** Each kind: its icon and name, a home (tap: go inside) or a leisure spot (its pose and lines). The server's catalogue
 * (content.journey.island.build) has the prices; this is what the maps need, so both renderers stay pure. */
export const BUILD_ART={
  nha_san:{emoji:'🛖',name:'Nhà sàn',home:true,pose:'stand'},
  biet_thu:{emoji:'🏡',name:'Biệt thự biển',home:true,pose:'stand'},
  lau_dai:{emoji:'🏰',name:'Lâu đài',home:true,pose:'stand'},
  cong_vien:{emoji:'🌳',name:'Công viên',pose:'sit',lines:['Ngồi ghế đá, gió biển mát rượi.','Đi dạo quanh vườn hoa, nghe chim hót.']},
  ho_boi:{emoji:'🏊',name:'Hồ bơi',pose:'swim',lines:['Bơi vài vòng, nước mát lạnh.','Nằm phao giữa hồ, nắng chiều vàng óng.']},
  golf:{emoji:'⛳',name:'Sân golf mini',pose:'stand',lines:['Vụt một gậy, bóng lăn sát lỗ!','Bóng rơi vào hố cát, cười một trận.']},
  cam_trai:{emoji:'🏕️',name:'Khu cắm trại',pose:'sit',lines:['Ngồi quanh lửa, nướng bắp thơm phức.','Nằm trong lều nghe sóng vỗ.']},
  ben_thuyen:{emoji:'⚓',name:'Bến du thuyền',pose:'stand',lines:['Ngồi mép cầu, thả chân xuống nước.','Ngắm thuyền buồm lắc lư bên bến.']},
  // 🏡 the house styles (public/js/house-art.js, 20/10): homes, a door to go inside
  ...Object.fromEntries(Object.entries(HOUSES).map(([id,h])=>[id,{emoji:h.emoji,name:h.name,home:true,pose:'stand',tier:h.tier}])),
};
/** The live room's spot id of a plot's building (live/island.py SPOT_RE: letters and _ only). */
export const plotSpot=p=>'b_'+(p<26?String.fromCharCode(97+p):p<52?'z'+String.fromCharCode(97+p-26):'zz'+String.fromCharCode(97+(p-52)%26));
/** The level standing at `now` (unix s) and whether the crew is still at work (scaffolding). */
export const levelAt=(b,now)=>b.b&&b.t<=now?b.b:b.l;
export const workAt=(b,now)=>Boolean(b.b)&&b.t>now;
/** The plot under a map point (within its square), or -1. */
export function plotAt(L,x,y){
  const h=PLOT_W/2;return (L.plots||[]).findIndex(([px,py])=>Math.abs(px-x)<=h&&Math.abs(py-y)<=h);
}
/** A ⚓ marina's pier: from the plot straight out to the water, away from the island's middle. */
export function pierOf(L,[px,py]){
  const cx=L.shore.reduce((s,p)=>s+p[0],0)/L.shore.length,cy=L.shore.reduce((s,p)=>s+p[1],0)/L.shore.length;
  const dx=px-cx,dy=py-cy,along=Math.abs(dx)>=Math.abs(dy),sx=along?Math.sign(dx)||1:0,sy=along?0:Math.sign(dy)||1;
  let len=.06;while(len<.3&&inPoly(L.shore,px+sx*(PLOT_W/2+len),py+sy*(PLOT_W/2+len)))len+=.02;
  len+=.05;const w=.035,cxp=px+sx*(PLOT_W/2+len/2),cyp=py+sy*(PLOT_W/2+len/2);
  return {rect:sx?{x:cxp,y:cyp,w:len,h:w}:{x:cxp,y:cyp,w,h:len},end:[px+sx*(PLOT_W/2+len),py+sy*(PLOT_W/2+len)],dir:[sx,sy]};
}
/** The island with its buildings (rows {p, k, l, b, t} of island_builds, `now` in the server's unix seconds): `built`
 * (what to draw), homes and construction sites are not walkable, a marina's pier is, and each finished building is a
 * spot: a leisure building to use (its pose), a home's door (go inside). Kinds this build does not know are skipped. */
export function withBuilds(L,builds,now){
  const plots=L.plots||[],built=[],spots=L.spots.filter(s=>!s.build),blocks=[...(L.blocks||[])],walk=[...(L.walk||[])];
  for(const b of builds||[]){
    // 🏝️ where it stands: its place on the design grid (L.places, from the server), else its old plot
    const [kind,look]=splitKind(b.k),at=L.places?.[b.p],art=BUILD_ART[kind];
    const pl=Array.isArray(at)?[GRID.X0+(at[0]+GRID.FOOT/2)*GRID.CELL,GRID.X0+(at[1]+GRID.FOOT/2)*GRID.CELL,plots[b.p]?.[2]||0]:plots[b.p];
    if(!pl||!art)continue;   // 🏡 '<style>__<n>': its colour
    const level=levelAt(b,now),work=workAt(b,now),r=Array.isArray(at)&&HOUSES[kind]?(at[2]|0)&3:0;
    const it={plot:b.p,x:pl[0],y:pl[1],r,coast:Boolean(pl[2]),kind,look:HOUSES[kind]?look:0,level,work,until:work?b.t:0,next:b.b||0,art};
    built.push(it);
    if(work||art.home)blocks.push({x:pl[0],y:pl[1],w:PLOT_W*.8,h:PLOT_W*.8});
    if(work||level<1)continue;
    if(kind==='ben_thuyen'){it.pier=pierOf(L,pl);walk.push(it.pier.rect);}
    const [ddx,ddy]=turn(PLOT_W*.3,PLOT_W*.62,r),door=art.home?[pl[0]+ddx,pl[1]+ddy]:[pl[0],pl[1]];
    spots.push({id:plotSpot(b.p),emoji:art.home?'🚪':art.emoji,name:art.home?`Vào ${art.name}`:art.name,x:door[0],y:door[1],
      pose:art.home?'stand':art.pose,lines:art.lines||[`${art.emoji} ${art.name}`],build:it,home:Boolean(art.home)});
  }
  return {...L,blocks,walk,spots,built};
}

/* ---- 🏝️ Thiết kế đảo (game/island_design.py): the free grid, the size tiers (🌊 lấn biển), the decorations ---------------
 * One square grid of GRID.G² cells of GRID.CELL map units from GRID.X0 covers each island and the sea around it (the map
 * reaches GRID.X0 .. GRID.X0 + G·CELL = −0.22 .. 1.22: an island grows past the old square). The server checks every
 * placement with the same numbers (game/island_design_content.py; tests/test_island_design.py runs gridCells() against
 * it); this draws and previews. Every island stands at tier 0 at least (its old coast grown 15 %). */
export const GRID={G:60,X0:-.22,CELL:.024,FOOT:3,TIERS:[1.15,1.25,1.35,1.45,1.55]};
export const BOUNDS=[GRID.X0,GRID.X0+GRID.G*GRID.CELL];
const SEA_SPOTS=new Set(['lan','san_ho','nha_san']);
/** Each decoration: [w, h (cells), where, solid, pose, cat, emoji, name] (game/island_design_content.py DECOR, the same
 * ids and numbers: tests/test_island_design.py). Prices and points come from the server's catalogue. */
export const DECOR_META={
  cay_dua:[1,1,'land',1,'','cay','🌴',"Cây dừa"],
  cay_co:[1,1,'land',1,'','cay','🌿',"Cọ quạt"],
  khom_tre:[1,1,'land',1,'','cay','🎋',"Khóm tre"],
  thong_bien:[1,1,'land',1,'','cay','🌲',"Thông biển"],
  hoa_giay:[1,1,'land',1,'','cay','🌺',"Hoa giấy"],
  cay_chuoi:[1,1,'land',1,'','cay','🍌',"Bụi chuối"],
  xuong_rong:[1,1,'land',1,'','cay','🌵',"Xương rồng"],
  bui_hoa:[1,1,'land',1,'','cay','🌼',"Bụi hoa"],
  luong_hoa:[2,1,'land',1,'','cay','🌷',"Luống hoa"],
  huong_duong:[2,1,'land',1,'','cay','🌻',"Hàng hướng dương"],
  cay_bang:[2,2,'land',1,'','cay','🌳',"Bàng biển"],
  cay_phuong:[2,2,'land',1,'','cay','🌳',"Phượng vĩ"],
  tung_canh:[1,1,'land',1,'','cay','🌲',"Tùng bonsai"],
  hoa_dao:[2,2,'land',1,'','cay','🌸',"Anh đào"],
  vuon_hoa:[3,2,'land',1,'','cay','🌷',"Vườn hoa"],
  ho_ca:[2,2,'land',0,'stand','ho','🐟',"Hồ cá koi"],
  ho_nho:[2,2,'land',0,'swim','ho','🏊',"Hồ bơi nhỏ"],
  be_suc:[2,2,'land',0,'swim','ho','♨️',"Bể sục"],
  ho_dai:[3,2,'land',0,'swim','ho','🏊',"Hồ bơi chữ nhật"],
  ho_tron:[3,3,'land',0,'swim','ho','🫧',"Hồ bơi bo tròn"],
  ho_lon:[4,3,'land',0,'swim','ho','🏖️',"Hồ bơi lớn có bậc"],
  ho_tran:[5,3,'coast',0,'swim','ho','🌅',"Hồ tràn bờ"],
  lua_trai:[1,1,'land',0,'sit','ct','🔥',"Đống lửa trại"],
  cong_hoa:[2,1,'land',0,'','ct','💐',"Cổng hoa"],
  khu_bbq:[2,2,'land',1,'stand','ct','🍖',"Khu BBQ"],
  choi_la:[2,2,'land',1,'sit','ct','🛖',"Chòi lá"],
  cau_vom:[1,3,'any',0,'','ct','🌉',"Cầu vòm gỗ"],
  suoi_da:[1,3,'land',1,'','ct','💧',"Suối đá"],
  san_choi:[3,3,'land',1,'stand','ct','🛝',"Sân chơi"],
  dai_phun:[2,2,'land',1,'','ct','⛲',"Đài phun nước"],
  nha_kinh:[3,2,'land',1,'','ct','🪴',"Nhà kính"],
  nha_thuyen:[3,3,'coast',1,'','ct','🛥️',"Nhà thuyền"],
  nha_go:[3,3,'land',1,'sit','ct','🏠',"Nhà gỗ"],
  san_tennis:[5,4,'land',0,'stand','ct','🎾',"Sân tennis"],
  bungalow_nuoc:[3,3,'pier',1,'','ct','🏝️',"Bungalow trên nước"],
  thac_nuoc:[4,3,'land',1,'','ct','🏞️',"Thác nước"],
  resort:[6,5,'land',1,'','ct','🏨',"Khu resort"],
  den_vuon:[1,1,'land',1,'','do','💡',"Đèn vườn"],
  chau_hoa:[1,1,'land',1,'','do','🪴',"Chậu hoa"],
  o_du:[1,1,'land',1,'','do','⛱️',"Ô dù bãi biển"],
  ghe_go:[2,1,'land',1,'sit','do','🪑',"Ghế gỗ"],
  cot_den:[1,1,'land',1,'','do','🏮',"Cột đèn"],
  vong:[2,1,'land',1,'lie','do','🛏️',"Võng"],
  ghe_dai:[1,2,'land',0,'lie','do','🏖️',"Ghế tắm nắng"],
  xich_du:[2,1,'land',1,'sit','do','🪢',"Xích đu"],
  bo_ban_ghe:[2,2,'land',1,'sit','do','☕',"Bàn ghế ngoài trời"],
  kinh_thien_van:[1,1,'land',1,'stand','do','🔭',"Kính thiên văn"],
  tuong_da:[1,1,'land',1,'','do','🗿',"Tượng đá"],
  loi_soi:[1,1,'land',0,'','loi','⚪',"Lối sỏi"],
  loi_da:[1,1,'land',0,'','loi','🪨',"Đường lát đá"],
  loi_gach:[1,1,'land',0,'','loi','🧱',"Gạch đỏ"],
  loi_go:[1,1,'land',0,'','loi','🟫',"Sàn gỗ"],
  rao_go:[1,1,'land',1,'','loi','🪵',"Rào gỗ"],
  rao_tre:[1,1,'land',1,'','loi','🎋',"Rào tre"],
  rao_trang:[1,1,'land',1,'','loi','🤍',"Rào trắng"],
  rao_cay:[1,1,'land',1,'','loi','🌳',"Hàng rào cây"],
  da_bien:[1,1,'any',1,'','bien','🪨',"Đá bờ biển"],
  phao_boi:[1,1,'sea',0,'','bien','🛟',"Phao bơi"],
  lau_dai_cat:[1,1,'land',1,'','bien','🏰',"Lâu đài cát"],
  da_lon:[2,2,'any',1,'','bien','⛰️',"Cụm đá lớn"],
  kayak:[1,2,'coast',1,'','bien','🛶',"Thuyền kayak"],
  cau_tau:[1,4,'pier',0,'stand','bien','⚓',"Cầu tàu gỗ"],
  du_thuyen:[2,5,'sea',1,'','bien','🛳️',"Du thuyền neo"],
  bong_chuyen:[4,3,'land',0,'stand','bien','🏐',"Sân bóng chuyền bãi biển"],
};
/** What walks on the water (a pier, a bridge): its cells are walkable wherever they are. */
const WALK_ON=new Set(['cau_tau','cau_vom']);
/** The lines a decoration with a pose says (the others: its name). */
const DECOR_LINES={
  ho_ca:['Ngắm đàn cá koi lượn dưới lá sen.','Thả nắm cám, cả đàn cá ùa tới.'],
  ho_nho:['Ngâm mình trong hồ, nắng chiều vàng óng.','Nằm phao giữa hồ, gió biển mát rượi.'],
  be_suc:['Bể sục ấm, bọt nước lách tách.','Ngâm chân trong bể sục, mỏi mệt tan hết.'],
  ho_dai:['Bơi vài vòng, nước mát lạnh.','Lặn một hơi tới mép hồ bên kia.'],
  ho_tron:['Thả mình giữa hồ, ngắm mây trôi.','Tựa mép hồ uống ly nước dừa.'],
  ho_lon:['Bơi ra đảo nhỏ giữa hồ.','Ngồi bậc lội, nước ngang lưng.'],
  ho_tran:['Bơi ra mép hồ, biển và trời liền một màu.','Tựa mép hồ tràn ngắm hoàng hôn.'],
  lua_trai:['Ngồi bên đống lửa, nghe củi nổ lách tách.','Nướng mấy củ khoai bên lửa trại.'],
  khu_bbq:['Lật xiên thịt nướng thơm lừng.','Mùi than hồng bay khắp đảo.'],
  choi_la:['Ngồi chòi lá hóng gió biển.','Nghe mưa rơi trên mái lá.'],
  san_choi:['Trượt cầu tuột một vòng, cười như trẻ con.','Đẩy xích đu lên cao tít.'],
  nha_go:['Ngồi hiên nhà gỗ ngắm biển.','Pha ấm trà ngoài hiên.'],
  san_tennis:['Giao bóng một cú thật căng!','Đánh qua lại mấy đường bóng dài.'],
  ghe_go:['Ngồi ghế gỗ nhìn ra biển.','Ngồi nghỉ chân nghe sóng vỗ.'],
  vong:['Đung đưa trên võng, suýt ngủ quên.','Nằm võng nghe gió lùa qua lá.'],
  ghe_dai:['Nằm dài tắm nắng, nghe sóng vỗ.','Đeo kính râm, nằm im ngắm trời.'],
  xich_du:['Đung đưa xích đu, gió thổi tung tóc.','Ngồi xích đu ngắm hoàng hôn.'],
  bo_ban_ghe:['Ngồi bàn ngoài trời, nhâm nhi ly cà phê.','Bày bàn ăn trưa giữa vườn.'],
  kinh_thien_van:['Ngắm tàu xa qua kính thiên văn.','Chỉnh kính, thấy cả hòn đảo bên kia.'],
  cau_tau:['Ngồi mép cầu tàu thả chân xuống nước.','Đứng cuối cầu nhìn ra khơi.'],
  bong_chuyen:['Đập bóng qua lưới, cát văng tung tóe.','Đỡ một quả bóng bổng, đẹp mắt!'],
};
export const decorMeta=kind=>{const m=DECOR_META[kind];return m?{id:kind,w:m[0],h:m[1],where:m[2],solid:Boolean(m[3]),pose:m[4],cat:m[5],emoji:m[6],name:m[7],walk:WALK_ON.has(kind)}:null;};
/** A quarter turn r (0..3, clockwise seen from above) of a local offset. */
export function turn(x,y,r){r=(r|0)&3;return r===0?[x,y]:r===1?[-y,x]:r===2?[-x,-y]:[y,-x];}
const tierScale=t=>GRID.TIERS[Math.max(0,Math.min(GRID.TIERS.length-1,t|0))];
const shores=new Map(),gridMemo=new Map();
/** The coast of `look` at size tier t (its old coast grown by GRID.TIERS[t]). */
export function shoreAt(look,t=0){
  const L=layout(look),key=L.look+'|'+t;let s=shores.get(key);if(s)return s;
  const [cx,cy,rx,ry,bumps]=L.shape,k=tierScale(t);s=blob(cx,cy,rx*k,ry*k,bumps);shores.set(key,s);return s;
}
/** How far the coast moved out at (x, y)'s bearing from the island's middle, tier t against the old coast. */
export function coastShift(look,t,x,y){
  const [cx,cy,rx,ry,bumps]=layout(look).shape;let a=Math.atan2((y-cy)/ry,(x-cx)/rx);if(a<0)a+=TAU;
  const n=bumps.length,f=a/TAU*n,k=Math.floor(f),u=f-k,b0=bumps[k%n],b1=bumps[(k+1)%n],w=b0+(b1-b0)*(1-Math.cos(u*Math.PI))/2,s=tierScale(t)-1;
  return [s*Math.cos(a)*rx*w,s*Math.sin(a)*ry*w];
}
/** What the island already has (game/island_design_content.py FIXED): [[x, y, w, h, sea]] of its old map. */
export function fixedRects(look){
  const L=layout(look),out=[],v=L.villa;
  out.push([v.x,v.y,v.w,v.h,0],[L.dock.x,L.dock.y,L.dock.w,L.dock.h,1]);
  if(L.pad.kind==='heli')out.push([L.pad.x,L.pad.y,.09,.09,0]);
  for(const s of L.spots)out.push([s.x,s.y,.03,.03,SEA_SPOTS.has(s.id)?1:0]);
  for(const d of L.deco){
    if(d.t==='reef')out.push([d.x,d.y,(d.r||.05)*1.4,(d.r||.05)*.8,1]);
    else if(d.t==='hut')out.push([d.x,d.y,.05,.04,1]);
    else if(d.t==='peak')out.push([d.x,d.y,(d.r||.12)*1.4,(d.r||.12)*.8,0]);
    else if(d.t==='steam'||d.t==='lighthouse')out.push([d.x,d.y,.05,.05,0]);
    else if(d.t==='rocks')out.push([d.x,d.y,.08,.04,0]);
    else if(d.t==='strip')out.push([d.x,d.y,d.w||.5,d.h||.06,0]);
    else if(d.t==='pool')out.push([d.x,d.y,(d.w||.14)+.015,(d.h||.06)+.015,0]);
  }
  for(const w of L.walk||[])out.push([w.x,w.y,w.w,w.h,1]);
  for(const b of L.blocks||[])out.push([b.x,b.y,b.w,b.h,0]);
  for(const [x,y] of L.palms)out.push([x,y,.02,.02,0]);
  return out;
}
const span=(lo,hi)=>[Math.max(0,Math.floor((lo-GRID.X0)/GRID.CELL+1e-9)),Math.min(GRID.G,Math.ceil((hi-GRID.X0)/GRID.CELL-1e-9))];
const cellX=i=>GRID.X0+(i+.5)*GRID.CELL;
/** {land, coast, fixed} of `look` at tier t: two Uint8Array(G²) (1: yes) and the Set of cells its own features cover
 * (the sea ones moved out with the coast). Cached. */
export function gridCells(look,t=0){
  const L=layout(look),key=L.look+'|'+t;let g=gridMemo.get(key);if(g)return g;
  const G=GRID.G,pts=shoreAt(L.look,t),land=new Uint8Array(G*G),coast=new Uint8Array(G*G),fixed=new Set();
  for(let j=0;j<G;j++){const y=cellX(j);for(let i=0;i<G;i++)if(inPoly(pts,cellX(i),y))land[j*G+i]=1;}
  for(let j=0;j<G;j++)for(let i=0;i<G;i++){if(!land[j*G+i])continue;
    for(let dj=-1;dj<=1;dj++)for(let di=-1;di<=1;di++){const a=i+di,b=j+dj;if(a<0||b<0||a>=G||b>=G||!land[b*G+a])coast[j*G+i]=1;}}
  for(let [x,y,w,h,sea] of fixedRects(L.look)){
    if(sea){const [dx,dy]=coastShift(L.look,t,x,y);x+=dx;y+=dy;}
    const [i0,i1]=span(x-w/2,x+w/2),[j0,j1]=span(y-h/2,y+h/2);
    for(let j=j0;j<j1;j++)for(let i=i0;i<i1;i++)fixed.add(j*G+i);
  }
  g={land,coast,fixed};gridMemo.set(key,g);return g;
}
/** The cells of a w × h thing at (x, y) turned r. */
export function footprint(w,h,x,y,r=0){if(r&1)[w,h]=[h,w];const out=[];for(let b=0;b<h;b++)for(let a=0;a<w;a++)out.push((y+b)*GRID.G+x+a);return out;}
/** Why a thing cannot go there ('' when it can): the server's game/island_design.py fits(), word for word. `taken`: a
 * Map or Set of the cells something already stands on. */
export function fitsWhy(look,t,w,h,where,x,y,r,taken){
  const G=GRID.G;
  if(!(Number.isInteger(x)&&Number.isInteger(y)&&x>=0&&y>=0&&x<G&&y<G))return 'Chỗ này nằm ngoài đảo.';
  const [ww,hh]=r&1?[h,w]:[w,h];if(x+ww>G||y+hh>G)return 'Chỗ này nằm ngoài đảo.';
  const {land,coast,fixed}=gridCells(look,t),cs=footprint(w,h,x,y,r);
  if(cs.some(c=>fixed.has(c)))return 'Chỗ này đã có công trình sẵn của đảo.';
  if(cs.some(c=>taken.has(c)))return 'Chỗ này đã có đồ khác. Dời đồ kia đi trước nhé.';
  const on=cs.filter(c=>land[c]).length;
  if((where==='land'||where==='coast')&&on<cs.length)return 'Phải đặt trên đất liền.';
  if(where==='coast'&&!cs.some(c=>coast[c]))return 'Phải đặt sát bờ biển.';
  if(where==='pier'&&!(on>0&&on<cs.length))return 'Đặt một đầu trên bờ, một đầu ra biển.';
  if(where==='sea'&&on)return 'Phải đặt trên mặt nước.';
  return '';
}
/** The map point at the middle of a thing of w × h cells at (x, y) turned r. */
export function cellsMiddle(w,h,x,y,r=0){const [ww,hh]=r&1?[h,w]:[w,h];return [GRID.X0+(x+ww/2)*GRID.CELL,GRID.X0+(y+hh/2)*GRID.CELL];}
/** The grid cell (top-left of a w × h thing turned r) whose middle is nearest a map point. */
export function cellOf(x,y,w=1,h=1,r=0){const [ww,hh]=r&1?[h,w]:[w,h];return [Math.round((x-GRID.X0)/GRID.CELL-ww/2),Math.round((y-GRID.X0)/GRID.CELL-hh/2)];}
const b26=n=>{let s='';n=Math.max(0,n|0);do{s=String.fromCharCode(97+n%26)+s;n=Math.floor(n/26);}while(n>0);return s;};
/** The live room's spot id of a decoration (live/island.py SPOT_RE: letters and _ only). */
export const decorSpot=id=>'d_'+b26(id);
/** The island at its size with its decorations (a design of the server: {t, d: [[id, kind, x, y, r]], b: {plot: [x,
 * y, r]}, ap}; none: tier 0, nothing placed). The coast and what lies on the water move out with the tier, the map's
 * bounds grow, each decoration gets its place (`decor`), its cells (in the way, or a pier to walk on) and its spot. The
 * buildings' places (`places`) are used by withBuilds(). */
export function withDesign(L,design){
  const look=L.look||'dua',t=Math.max(0,Math.min(GRID.TIERS.length-1,Number(design?.t)||0)),sh=(x,y)=>{const [dx,dy]=coastShift(look,t,x,y);return [x+dx,y+dy];};
  const mv=o=>{const [x,y]=sh(o.x,o.y);return {...o,x,y};};
  const G=GRID.G,cellSolid=new Uint8Array(G*G),cellWalk=new Uint8Array(G*G),decor=[],spots=[];
  for(const row of Array.isArray(design?.d)?design.d:[]){
    const [id,kind,x,y,r]=Array.isArray(row)?row:[],m=decorMeta(kind);if(!m||!Number.isInteger(x)||!Number.isInteger(y))continue;
    const rr=(r|0)&3,[ww,hh]=rr&1?[m.h,m.w]:[m.w,m.h],[mx,my]=cellsMiddle(m.w,m.h,x,y,rr);
    const it={id,kind,gx:x,gy:y,r:rr,w:ww,h:hh,x:mx,y:my,meta:m};decor.push(it);
    for(const c of footprint(m.w,m.h,x,y,rr)){if(c<0||c>=G*G)continue;if(m.solid)cellSolid[c]=1;if(m.walk)cellWalk[c]=1;}
    if(m.pose){const [fx,fy]=m.solid?[mx,my+hh*GRID.CELL/2+.012]:[mx,my];
      spots.push({id:decorSpot(id),emoji:m.emoji,name:m.name,x:fx,y:fy,pose:m.pose,lines:DECOR_LINES[kind]||[`${m.emoji} ${m.name}`],decor:it});}
  }
  const deco=L.deco.map(d=>d.t==='reef'||d.t==='hut'?mv(d):d);
  return {...L,tier:t,shore:shoreAt(look,t),bounds:BOUNDS,dock:mv(L.dock),walk:(L.walk||[]).map(mv),deco,
    spots:[...L.spots.map(s=>SEA_SPOTS.has(s.id)?mv(s):s),...spots],
    plots:(L.plots||[]).map(([x,y,c])=>c?[...sh(x,y),c]:[x,y,c]),
    places:design?.b&&typeof design.b==='object'?design.b:null,decor,cellSolid,cellWalk,paths:Boolean(design?.ap),design:design||null};
}
/** 🛤️ The footpaths (a design's `ap`): from the pier's foot to every home's door and each spot to sit, lie or stand
 * at, around what stands in the way. [[x, y], …] polylines (none when the owner turned them off). */
export function footpaths(L){
  if(!L.paths)return [];
  const d=L.dock,north=d.y<(L.shape?.[1]??.5),start=nearestWalkable(L,d.x,north?d.y+d.h/2:d.y-d.h/2),out=[];
  for(const s of L.spots){if(!(s.build||s.decor)||s.pose==='swim')continue;const p=findPath(L,start,[s.x,s.y]);if(p.length)out.push([start,...p]);}
  return out;
}
