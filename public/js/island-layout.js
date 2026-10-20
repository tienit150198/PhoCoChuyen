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
    shore:blob(.5,.5,.38,.36,[1,.96,1.04,.98,1.02,.93,1,1.05]),sandWidth:.07,
    palms:[[.24,.38],[.3,.3],[.2,.55],[.31,.64],[.72,.3],[.78,.42],[.62,.24],[.4,.78],[.66,.8]],
    villa:{x:.5,y:.36,w:.17,h:.11,floors:1,roof:'#b7663f',wall:'#f4e6cc'},
    dock:{x:.47,y:.82,w:.06,h:.16},pad:{x:.76,y:.58,kind:'heli'},
    spots:[spot('vong',.25,.47),spot('lua',.42,.7),spot('bar',.62,.68),spot('lan',.15,.42)],deco:[],
    plots:[[.37,.52,0],[.46,.52,0],[.55,.52,0],[.37,.61,0],[.46,.61,0],[.7,.72,1]]},
  san_ho:{name:'Đảo San Hô',sea:'#4fc3c9',deep:'#2c95ad',sand:'#f7ead0',grass:'#9fd07a',grassDark:'#7cb860',
    shore:blob(.48,.55,.4,.27,[1,1.05,.92,1,1.06,.95,1.02,.97]),sandWidth:.085,
    palms:[[.17,.45],[.3,.6],[.82,.5],[.8,.42],[.16,.6],[.62,.79],[.8,.62]],
    villa:{x:.27,y:.47,w:.14,h:.09,floors:1,roof:'#4f9bb5',wall:'#fbf3e4'},
    dock:{x:.24,y:.21,w:.05,h:.28},pad:{x:.72,y:.62,kind:'heli'},
    spots:[spot('nha_san',.3,.12),spot('san_ho',.86,.32),spot('vong',.6,.55),spot('bar',.38,.62),spot('lua',.2,.62)],
    deco:[{t:'reef',x:.86,y:.28,r:.07},{t:'reef',x:.12,y:.84,r:.05},{t:'reef',x:.7,y:.9,r:.04},{t:'hut',x:.33,y:.09},{t:'hut',x:.4,y:.13}],
    walk:[{x:.33,y:.12,w:.14,h:.04}],
    plots:[[.41,.38,0],[.5,.38,0],[.59,.38,0],[.68,.38,0],[.41,.47,0],[.5,.47,0],[.37,.7,0],[.46,.7,0],[.55,.7,0],[.13,.54,1]]},
  may_da:{name:'Đảo Mây Đá',sea:'#5a9fb6',deep:'#336f8c',sand:'#cbb994',grass:'#7fa86a',grassDark:'#5f8a54',rock:'#5d5560',
    shore:blob(.5,.5,.39,.37,[1,.9,1.06,.96,1.04,.9,1.02,1.08,.94]),sandWidth:.05,
    palms:[[.14,.52],[.3,.76],[.67,.77],[.8,.58],[.2,.43]],
    villa:{x:.33,y:.38,w:.13,h:.09,floors:2,roof:'#4b4650',wall:'#e6ddd2'},
    dock:{x:.6,y:.84,w:.05,h:.14},pad:{x:.72,y:.42,kind:'heli'},
    spots:[spot('dai',.56,.24),spot('suoi',.2,.62),spot('lua',.45,.78),spot('lan',.87,.62)],
    deco:[{t:'peak',x:.56,y:.3,r:.13},{t:'steam',x:.2,y:.59},{t:'steam',x:.6,y:.18},{t:'rocks',x:.18,y:.3},{t:'rocks',x:.82,y:.8}],
    blocks:[{x:.5,y:.3,w:.14,h:.08}],
    plots:[[.26,.5,0],[.35,.5,0],[.44,.5,0],[.53,.5,0],[.62,.5,0],[.35,.59,0],[.44,.59,0],[.53,.59,0],[.62,.59,0],[.71,.59,0],[.35,.68,0],[.44,.68,0],[.53,.68,0],[.62,.68,0],[.26,.68,0],[.71,.68,1]]},
  hoang_hon:{name:'Đảo Hoàng Hôn',sea:'#e59a6a',deep:'#b4627a',sand:'#f6d6a6',grass:'#9bbf6a',grassDark:'#7da356',
    shore:blob(.5,.52,.43,.4,[1,1.03,.97,1.05,1,.95,1.04,.98]),sandWidth:.06,
    palms:[[.11,.62],[.24,.68],[.88,.62],[.76,.68],[.35,.87],[.66,.86],[.14,.36]],
    villa:{x:.4,y:.31,w:.2,h:.11,floors:3,roof:'#8a4d3a',wall:'#fff4e2'},
    dock:{x:.6,y:.88,w:.06,h:.11},pad:{x:.5,y:.2,kind:'strip'},
    spots:[spot('hai_dang',.86,.36),spot('ho_boi',.5,.6),spot('bar',.3,.7),spot('vong',.72,.74),spot('lua',.42,.82)],
    deco:[{t:'strip',x:.5,y:.2,w:.56,h:.06},{t:'lighthouse',x:.86,y:.32},{t:'pool',x:.5,y:.6,w:.16,h:.06}],
    plots:[[.56,.3,0],[.65,.3,0],[.74,.3,0],[.215,.43,0],[.305,.43,0],[.215,.52,0],[.305,.52,0],[.305,.61,0],[.4,.42,0],[.49,.42,0],[.58,.42,0],[.4,.51,0],[.49,.51,0],[.58,.51,0],[.68,.43,0],[.77,.43,0],[.68,.52,0],[.77,.52,0],[.68,.61,0],[.4,.72,0],[.49,.72,0],[.58,.72,0],[.12,.52,1],[.88,.5,1]]},
};
export const LOOK_IDS=Object.keys(LOOKS);
export const layout=look=>LOOKS[look]||LOOKS.dua;

export function inPoly(pts,x,y){
  let inside=false;
  for(let i=0,j=pts.length-1;i<pts.length;j=i++){const [ax,ay]=pts[i],[bx,by]=pts[j];if((ay>y)!==(by>y)&&x<(bx-ax)*(y-ay)/(by-ay)+ax)inside=!inside;}
  return inside;
}
const inRect=(r,x,y)=>x>=r.x-r.w/2&&x<=r.x+r.w/2&&y>=r.y-r.h/2&&y<=r.y+r.h/2;
/** The villa's footprint, a mountain: not walkable. */
export function blocks(L){
  const v=L.villa;return [{x:v.x,y:v.y,w:v.w*.9,h:v.h*.8},...(L.blocks||[])];
}
/** Can a player stand here? Inside the coast (a hair in from the water), on the dock or a pier, never in a block. */
export function walkable(L,x,y){
  if(!(x>=0&&x<=1&&y>=0&&y<=1))return false;
  if(blocks(L).some(b=>inRect(b,x,y)))return false;
  if(inRect(L.dock,x,y)||(L.walk||[]).some(r=>inRect(r,x,y)))return true;
  return inPoly(L.shore,x,y);
}
/** A walk around what stands in the way (houses, construction sites, the villa, a mountain): the points to walk through
 * to (tx, ty), the target last; [] when there is no way. A breadth-first search on a GRID² grid of the map (built once
 * per layout object), then straightened where a straight line stays walkable. Straight lines keep working on their own:
 * a target in plain sight is one point. */
const GRID=110,grids=new WeakMap();
function gridOf(L){
  let g=grids.get(L);if(g)return g;
  g=new Uint8Array(GRID*GRID);
  for(let j=0;j<GRID;j++)for(let i=0;i<GRID;i++)g[j*GRID+i]=walkable(L,(i+.5)/GRID,(j+.5)/GRID)?1:0;
  grids.set(L,g);return g;
}
export function clearWay(L,ax,ay,bx,by){
  const n=Math.max(1,Math.ceil(Math.hypot(bx-ax,by-ay)/.004));
  for(let k=1;k<=n;k++){const t=k/n;if(!walkable(L,ax+(bx-ax)*t,ay+(by-ay)*t))return false;}
  return true;
}
export function findPath(L,[sx,sy],[tx,ty]){
  if(clearWay(L,sx,sy,tx,ty))return [[tx,ty]];
  const g=gridOf(L),cell=v=>Math.max(0,Math.min(GRID-1,Math.floor(v*GRID)));
  const near=(i,j)=>{if(g[j*GRID+i])return j*GRID+i;for(let r=1;r<6;r++)for(let dj=-r;dj<=r;dj++)for(let di=-r;di<=r;di++){const a=i+di,b=j+dj;if(a>=0&&b>=0&&a<GRID&&b<GRID&&g[b*GRID+a])return b*GRID+a;}return -1;};
  const s=near(cell(sx),cell(sy)),e=near(cell(tx),cell(ty));if(s<0||e<0)return [];
  const prev=new Int32Array(GRID*GRID).fill(-1),q=new Int32Array(GRID*GRID);let h=0,n=0;q[n++]=s;prev[s]=s;
  const D=[[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]];
  while(h<n&&prev[e]<0){const c=q[h++],ci=c%GRID,cj=(c-ci)/GRID;
    for(const [di,dj] of D){const a=ci+di,b=cj+dj;if(a<0||b<0||a>=GRID||b>=GRID)continue;const k=b*GRID+a;
      if(prev[k]>=0||!g[k]||(di&&dj&&(!g[cj*GRID+a]||!g[b*GRID+ci])))continue;prev[k]=c;q[n++]=k;}}
  if(prev[e]<0)return [];
  const cells=[];for(let c=e;c!==s;c=prev[c])cells.push(c);cells.reverse();
  const pts=cells.map(c=>{const i=c%GRID;return [(i+.5)/GRID,((c-i)/GRID+.5)/GRID];});
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
export const plotSpot=p=>'b_'+(p<26?String.fromCharCode(97+p):'z'+String.fromCharCode(97+p-26));
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
    const [kind,look]=splitKind(b.k),pl=plots[b.p],art=BUILD_ART[kind];if(!pl||!art)continue;   // 🏡 '<style>__<n>': its colour
    const level=levelAt(b,now),work=workAt(b,now);
    const it={plot:b.p,x:pl[0],y:pl[1],coast:Boolean(pl[2]),kind,look:HOUSES[kind]?look:0,level,work,until:work?b.t:0,next:b.b||0,art};
    built.push(it);
    if(work||art.home)blocks.push({x:pl[0],y:pl[1],w:PLOT_W*.8,h:PLOT_W*.8});
    if(work||level<1)continue;
    if(kind==='ben_thuyen'){it.pier=pierOf(L,pl);walk.push(it.pier.rect);}
    const door=art.home?[pl[0]+PLOT_W*.3,pl[1]+PLOT_W*.62]:[pl[0],pl[1]];
    spots.push({id:plotSpot(b.p),emoji:art.home?'🚪':art.emoji,name:art.home?`Vào ${art.name}`:art.name,x:door[0],y:door[1],
      pose:art.home?'stand':art.pose,lines:art.lines||[`${art.emoji} ${art.name}`],build:it,home:Boolean(art.home)});
  }
  return {...L,blocks,walk,spots,built};
}
