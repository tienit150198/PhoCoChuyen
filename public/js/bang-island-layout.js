/** ⚔️ Đảo bang: the map of a bang's island (game/bang_island.py), shared by both interfaces: the old one's 2D walk
 * (v4/bang-island-walk.js) and the new one's isometric scene (client/isometric/bang-island.ts). Positions are fractions
 * of the island's square map (x to the east, y to the south, 0..1), the numbers the live room sends
 * (live/bang_island.py bisl_mv). Pure data and geometry: no DOM, no canvas.
 *
 * The island is laid out along the screen: at(a, b) turns "a to the right, b towards the viewer" (both from the
 * middle, the isometric screen's axes) into map x, y, so the gate and the pier face the camera and the hall sits in the
 * middle. Each facility has a fixed slot: rect {x, y, w, h} (map axes: a diamond on screen), `solid` (not walkable),
 * `door` (where a player stands to use it, in front of it). Decorative plots (`plots`) and spots (`spots`) around.
 *
 * 🏝️ Levels (owner 21/10, game/bang_content.py ISLE_*): layout(level, building) is the map of an island of that level
 * (1…5). Level 1 is the island as it was before 21/10 (LAYOUT). Each level adds a zone of land on one side (ZONES: a
 * lobe of the coast, a plot, a spot, a road, trees): 2 🥋 Võ đường (east), 3 🍵 Trà đình (west), 4 🛕 Bảo tháp (north,
 * behind the hall), 5 🗼 Hải đăng at the east tip, the lobes grown and gold lanterns along the roads. The facilities never
 * move (the same map fractions on every level: the live room's positions mean the same place for everyone). While the
 * next level is being built (`building`), its land shows as a raw sand bank with a work site (`site`): not walkable. */

const TAU=Math.PI*2,R2=Math.SQRT1_2,EDGE=.012;
/** Screen-aligned (a right, b towards the viewer) → map [x, y]. */
export const at=(a,b)=>[+(.5+(a+b)*R2).toFixed(4),+(.5+(b-a)*R2).toFixed(4)];
/** Map [x, y] → screen-aligned [a, b]. */
export const screenOf=(x,y)=>[((x-.5)-(y-.5))*R2,((x-.5)+(y-.5))*R2];
/** The radius of a bumpy circle at angle t0 (`bumps`: radius factors around it, eased between). */
function bumpy(r,bumps,t0){
  const n=bumps.length,f=t0/TAU*n,k=Math.floor(f),t=f-k,b0=bumps[k%n],b1=bumps[(k+1)%n];
  return r*(b0+(b1-b0)*(1-Math.cos(t*Math.PI))/2);
}
/** A coast around (cx, cy): the bumpy circle, pushed out by `lobes` ({c: map angle, R: radius at its middle, w: half
 * width in radians}: a rounded cape), `steps` points. */
function blob(cx,cy,r,bumps,steps=64,lobes=[]){
  const out=[];
  for(let i=0;i<steps;i++){
    const t0=i/steps*TAU,base=bumpy(r,bumps,t0);let rr=base;
    for(const l of lobes){const d=Math.abs(((t0-l.c)%TAU+TAU*1.5)%TAU-Math.PI);if(d<l.w)rr=Math.max(rr,l.R*Math.sqrt(1-(d/l.w)**2));}
    // a cape never leaves the map's square (positions are 0..1 fractions): a little margin of sea inside it
    if(rr>base)rr=Math.max(base,Math.min(rr,(.5-EDGE)/Math.max(Math.abs(Math.cos(t0)),Math.abs(Math.sin(t0)))));
    out.push([+(cx+Math.cos(t0)*rr).toFixed(4),+(cy+Math.sin(t0)*rr).toFixed(4)]);
  }
  return out;
}
const rectAt=(a,b,w,h=w)=>{const [x,y]=at(a,b);return {x,y,w,h};};
/** A strip `wd` wide from screen point p to q, as a map polygon (a pier, a road). */
function strip(p,q,wd){
  const [a0,b0]=p,[a1,b1]=q,dx=a1-a0,dy=b1-b0,l=Math.hypot(dx,dy)||1,nx=-dy/l*wd/2,ny=dx/l*wd/2;
  return [at(a0+nx,b0+ny),at(a1+nx,b1+ny),at(a1-nx,b1-ny),at(a0-nx,b0-ny)];
}
/** The point in front of a slot's diamond (towards the viewer), `gap` further on. */
function front(r,gap=.035){const [a,b]=screenOf(r.x,r.y);return at(a,b+(r.w+r.h)/2*R2+gap);}

export const SIZE=24;   // tiles per side in the isometric scene (a private island: 14)
export const EMOTES=[['wave','👋','Vẫy tay'],['heart','❤️','Thả tim'],['laugh','😂','Cười lớn'],['wow','😮','Ồ'],['bow','🙇','Vái chào'],['cheers','🥂','Cụng ly'],['fight','⚔️','Hô khẩu hiệu']];
/** The facilities in game/bang_island.py FACILITY_IDS order (tests keep the two equal). */
export const FACILITY_IDS=['dai_sanh','kho_bang','xuong_may','san_pet','den_vang','tuong_bang','cong_bang'];

const slot=(id,a,b,w,extra={})=>{const r=rectAt(a,b,w,extra.h??w);return {id,...r,solid:extra.solid!==false,door:extra.door?at(...extra.door):front(r,extra.gap),pose:extra.pose||'stand'};};
const SLOTS={
  dai_sanh:slot('dai_sanh',0,-.12,.17,{gap:.03}),
  kho_bang:slot('kho_bang',-.27,-.235,.1),
  den_vang:slot('den_vang',.27,-.235,.1),
  xuong_may:slot('xuong_may',-.3,.03,.1),
  san_pet:slot('san_pet',.285,.055,.13,{solid:false,door:[.285,.055]}),   // a flat yard: walk in, the spot is its middle
  tuong_bang:slot('tuong_bang',0,.095,.05,{gap:.03,pose:'bow'}),
  cong_bang:slot('cong_bang',0,.35,.03,{solid:false,door:[0,.3]}),     // the gate: two pillars, the way through between them
};
const GATE={a:0,b:.35,half:.085,post:.032};   // the pillars stand at a = ±half
const SPOT_INFO={
  ben_tau:{emoji:'⚓',name:'Bến tàu',pose:'stand',lines:['Thuyền của bang cập bến, sóng vỗ vào chân cầu.','Đứng ở bến nhìn cả lãnh địa sáng đèn.']},
  vuon_hoa:{emoji:'🌺',name:'Vườn hoa',pose:'sit',lines:['Ngồi bên vườn hoa của bang, hương thơm nhẹ.','Hoa nở đủ màu, ai trong bang cũng chăm một khóm.']},
  ao_sen:{emoji:'🪷',name:'Ao sen',pose:'sit',lines:['Ngồi bên ao sen, cá chép đỏ bơi quanh.','Sen nở thơm cả quảng trường.']},
  rung_truc:{emoji:'🎋',name:'Rừng trúc',pose:'stand',lines:['Gió lùa qua rừng trúc nghe xào xạc.','Bóng trúc mát rượi, chỗ tập võ ưa thích.']},
  den_long:{emoji:'🏮',name:'Dãy đèn lồng',pose:'stand',lines:['Đèn lồng đỏ đung đưa, cả bang cùng treo.','Ánh đèn lồng chiếu lên mặt nước.']},
  doi_thong:{emoji:'🌲',name:'Đồi thông',pose:'sit',lines:['Ngồi trên đồi thông sau đại sảnh, nhìn ra biển.','Thông reo, mây trôi chầm chậm.']},
  // 🏝️ the zones of the island's levels 2…5 (21/10)
  vo_duong:{emoji:'🥋',name:'Võ đường',pose:'stand',lines:['Lên võ đài so tài vài đường quyền với đồng môn.','Tiếng hô vang cả bờ đông.']},
  tra_dinh:{emoji:'🍵',name:'Trà đình',pose:'sit',lines:['Ngồi trà đình nhấp chén trà, ngắm cá koi.','Gió hồ mát, trà thơm, chuyện bang rôm rả.']},
  bao_thap:{emoji:'🛕',name:'Bảo tháp',pose:'bow',lines:['Thắp nén hương ở bảo tháp, cầu cho cả bang.','Đứng trên đồi tháp nhìn trọn lãnh địa.']},
  hai_dang:{emoji:'🗼',name:'Hải đăng',pose:'stand',lines:['Ngọn hải đăng của bang soi sáng cả vịnh.','Gió biển lồng lộng dưới chân hải đăng.']},
};
const spot=(id,a,b,stand)=>({id,...SPOT_INFO[id],x:at(a,b)[0],y:at(a,b)[1],stand:stand?at(...stand):null});

const SHORE=[.5,.5,.45,[1,.97,1.03,.99,1.02,.95,1.01,1.04,.98,1.02]];
export const LAYOUT={
  name:'Đảo bang',size:SIZE,level:1,sea:'#4fb0c6',deep:'#2b7f9e',sand:'#f0dcae',grass:'#86c06a',grassDark:'#68a653',stone:'#d9cdb8',stoneDark:'#b9aa90',
  shore:blob(...SHORE),sandWidth:.045,
  plaza:{c:at(0,.095),r:.105},                  // the stone square around the statue
  roads:[strip([0,.39],[0,0],.06),strip([0,.095],[-.3,.13],.045),strip([0,.095],[.285,.06],.045),
    strip([-.08,-.03],[-.27,-.15],.04),strip([.08,-.03],[.27,-.15],.04)],
  dock:strip([0,.365],[0,.55],.07),
  gate:GATE,
  slots:SLOTS,
  plots:[
    {id:'vuon_hoa',kind:'flowers',...rectAt(-.165,.255,.055),solid:true},
    {id:'ao_sen',kind:'pond',...rectAt(.165,.255,.06),solid:true},
    {id:'rung_truc',kind:'bamboo',...rectAt(-.385,-.105,.045),solid:true},
    {id:'den_long',kind:'lanterns',...rectAt(.385,-.105,.04),solid:false},
    {id:'doi_thong',kind:'pines',...rectAt(0,-.335,.06),solid:true},
    {id:'dummies',kind:'dummies',...rectAt(-.3,.215,.035),solid:false},
  ],
  spots:[spot('ben_tau',0,.52),spot('vuon_hoa',-.165,.255,[-.165,.315]),spot('ao_sen',.165,.255,[.165,.32]),
    spot('rung_truc',-.385,-.105,[-.33,-.07]),spot('den_long',.385,-.105,[.35,-.06]),spot('doi_thong',0,-.335,[.07,-.3])],
  palms:[[-.36,.22],[.36,.22],[-.25,.33],[.25,.33],[-.41,.07],[.41,.08],[-.17,-.36],[.17,-.36],[-.25,-.33],[.25,-.33]].map(([a,b])=>at(a,b)),
  trees:[[-.13,.2],[.13,.2],[-.16,-.24],[.16,-.24],[-.39,-.03],[.39,-.03]].map(([a,b])=>at(a,b)),
};

/* ---- 🏝️ the island's levels ------------------------------------------------------------------------------------- */
export const ISLE_MAX=5;
const Q=Math.PI/4;   // map angles of the screen's sides: east (right) −Q, west 3Q, north (behind the hall) −3Q, south Q
/** One zone a level (index = level − 2): the cape it adds (lobes: every level's lobes up to it are kept, a later one
 * may grow an earlier cape), its plot (a rect in screen-aligned a, b), its spot, a road to it, trees. */
export const ZONES=[
  {level:2,id:'vo_duong',name:'Võ đường',lobes:[{c:-Q,R:.63,w:.55}],plot:{kind:'ring',a:.5,b:-.03,w:.085,solid:false},spot:[.5,-.03,null],
    road:[[.33,.06],[.47,-.01],.042],palms:[[.55,.08],[.54,-.13]],trees:[[.44,-.15]]},
  {level:3,id:'tra_dinh',name:'Trà đình',lobes:[{c:3*Q,R:.63,w:.55}],plot:{kind:'teahouse',a:-.53,b:-.03,w:.07,solid:true},spot:[-.53,-.03,[-.455,.05]],
    road:[[-.3,.13],[-.45,.06],.042],palms:[[-.58,.09]],trees:[[-.5,-.14],[-.47,-.06]]},
  {level:4,id:'bao_thap',name:'Bảo tháp',lobes:[{c:-3*Q,R:.64,w:.5}],plot:{kind:'pagoda',a:0,b:-.535,w:.06,solid:true},spot:[0,-.535,[.075,-.47]],
    road:[[.1,-.29],[.075,-.45],.04],palms:[],trees:[[-.13,-.52],[.1,-.52],[-.08,-.6]]},
  {level:5,id:'hai_dang',name:'Hải đăng',lobes:[{c:-Q,R:.69,w:.8},{c:3*Q,R:.68,w:.8},{c:-3*Q,R:.67,w:.75},{c:Q-.62,R:.53,w:.32},{c:Q+.62,R:.53,w:.32}],plot:{kind:'lighthouse',a:.635,b:0,w:.04,solid:true},
    spot:[.635,0,[.585,.05]],road:[[.47,-.01],[.585,.04],.036],palms:[[-.63,-.06]],trees:[],
    lamps:[[-.07,.28],[.07,.28],[-.07,.16],[.07,.16],[-.2,.155],[.2,.15],[-.16,-.08],[.16,-.08],[.4,.03],[-.4,.1]]},
];
const zoneShore=level=>blob(...SHORE,level>1?128:64,ZONES.filter(z=>z.level<=level).flatMap(z=>z.lobes));
const zonePlot=z=>({id:z.id,kind:z.plot.kind,...rectAt(z.plot.a,z.plot.b,z.plot.w),solid:z.plot.solid});
const layouts=new Map();
/** The map of an island of `level` (1…ISLE_MAX), with the work site of `building` (the level being built, or 0). */
export function layout(level=1,building=0){
  const lv=Math.max(1,Math.min(ISLE_MAX,Math.floor(Number(level)||1))),to=building>lv&&building<=ISLE_MAX?Math.floor(building):0,key=lv+'|'+to;
  if(lv===1&&!to)return LAYOUT;
  let L=layouts.get(key);if(L)return L;
  const zones=ZONES.filter(z=>z.level<=lv);
  L={...LAYOUT,level:lv,shore:lv>1?zoneShore(lv):LAYOUT.shore,
    roads:[...LAYOUT.roads,...zones.map(z=>strip(z.road[0],z.road[1],z.road[2]))],
    plots:[...LAYOUT.plots,...zones.map(zonePlot)],
    spots:[...LAYOUT.spots,...zones.map(z=>spot(z.id,z.spot[0],z.spot[1],z.spot[2]))],
    palms:[...LAYOUT.palms,...zones.flatMap(z=>z.palms.map(([a,b])=>at(a,b)))],
    trees:[...LAYOUT.trees,...zones.flatMap(z=>z.trees.map(([a,b])=>at(a,b)))],
    lamps:zones.flatMap(z=>(z.lamps||[]).map(([a,b])=>at(a,b))),
    ...(lv>=4?{stone:'#e6dccb',stoneDark:'#bfae92'}:{}),...(lv>=5?{stone:'#eadcb4',stoneDark:'#c9a85a',gold:true}:{})};
  if(to){const z=ZONES.find(x=>x.level===to);L.site={level:to,id:z.id,name:z.name,kind:z.plot.kind,shore:zoneShore(to),...rectAt(z.plot.a,z.plot.b,z.plot.w)};}
  layouts.set(key,L);
  return L;
}
export const slotById=(L,id)=>L.slots[id]||null;

export function inPoly(pts,x,y){
  let inside=false;
  for(let i=0,j=pts.length-1;i<pts.length;j=i++){const [ax,ay]=pts[i],[bx,by]=pts[j];if((ay>y)!==(by>y)&&x<(bx-ax)*(y-ay)/(by-ay)+ax)inside=!inside;}
  return inside;
}
export const inRect=(r,x,y)=>x>=r.x-r.w/2&&x<=r.x+r.w/2&&y>=r.y-r.h/2&&y<=r.y+r.h/2;
/** The gate's two pillars, as small map rects. */
export function gatePosts(L){const g=L.gate;return [-1,1].map(s=>rectAt(g.a+s*g.half,g.b,g.post));}
/** What nobody walks through: the solid facilities (a hair inside their slot), the solid plots, the gate's pillars. */
export function blocks(L){
  const out=[];
  for(const s of Object.values(L.slots))if(s.solid)out.push({x:s.x,y:s.y,w:s.w*.9,h:s.h*.9,id:s.id});
  for(const p of L.plots)if(p.solid)out.push({x:p.x,y:p.y,w:p.w*.9,h:p.h*.9,id:p.id});
  for(const g of gatePosts(L))out.push({...g,id:'cong_bang'});
  return out;
}
let cache=null;
/** Can a player stand here? On the island (inside the coast) or the pier, never in a block. */
export function walkable(L,x,y){
  if(!(x>=0&&x<=1&&y>=0&&y<=1))return false;
  if(!cache||cache.L!==L)cache={L,blocks:blocks(L)};
  if(cache.blocks.some(b=>inRect(b,x,y)))return false;
  return inPoly(L.dock,x,y)||inPoly(L.shore,x,y);
}
/** Where one arrives: the far end of the pier. */
export const arrival=L=>at(0,.52);
/** One step of walking from (x,y) toward (tx,ty), at most `len`: slides along a wall rather than stopping dead. */
export function step(L,x,y,tx,ty,len){
  const dx=tx-x,dy=ty-y,d=Math.hypot(dx,dy);if(d<1e-6)return [x,y,true];
  const k=Math.min(1,len/d),nx=x+dx*k,ny=y+dy*k;
  if(walkable(L,nx,ny))return [nx,ny,k>=1];
  if(walkable(L,nx,y))return [nx,y,false];
  if(walkable(L,x,ny))return [x,ny,false];
  return [x,y,true];
}
export const centre=L=>L.plaza.c;
/** Can one walk straight from a to b (sampled every ~.004)? */
export function clearLine(L,a,b){
  const d=Math.hypot(b[0]-a[0],b[1]-a[1]),n=Math.max(1,Math.ceil(d/.004));
  for(let i=1;i<=n;i++){const t=i/n;if(!walkable(L,a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))return false;}
  return true;
}
const GRID=96,grids=new WeakMap();
function gridOf(L){
  let g=grids.get(L);if(g)return g;
  g=new Uint8Array(GRID*GRID);for(let j=0;j<GRID;j++)for(let i=0;i<GRID;i++)g[j*GRID+i]=walkable(L,(i+.5)/GRID,(j+.5)/GRID)?1:0;
  grids.set(L,g);return g;
}
/** 🏝️ A walk from a to b around what stands in the way (21/10: a bigger island has far zones behind the gate and the
 * facilities): the straight line when it is clear, else a breadth-first route on a GRID×GRID grid of the map, its
 * corners cut wherever the line stays walkable. [[x, y], …] ending at b (b itself if nothing connects). */
export function findPath(L,a,b){
  if(clearLine(L,a,b))return [b];
  const g=gridOf(L),cell=([x,y])=>{const i=Math.max(0,Math.min(GRID-1,Math.floor(x*GRID))),j=Math.max(0,Math.min(GRID-1,Math.floor(y*GRID)));return j*GRID+i;};
  const near=k=>{if(g[k])return k;const i0=k%GRID,j0=(k-i0)/GRID;let best=-1,bd=1e9;
    for(let j=Math.max(0,j0-4);j<=Math.min(GRID-1,j0+4);j++)for(let i=Math.max(0,i0-4);i<=Math.min(GRID-1,i0+4);i++){const c=j*GRID+i,d=(i-i0)**2+(j-j0)**2;if(g[c]&&d<bd){bd=d;best=c;}}return best;};
  const s=near(cell(a)),t=near(cell(b));if(s<0||t<0)return [b];
  const prev=new Int32Array(GRID*GRID).fill(-1);prev[s]=s;const q=[s];
  for(let h=0;h<q.length&&prev[t]<0;h++){const k=q[h],i=k%GRID,j=(k-i)/GRID;
    for(const [di,dj] of [[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]]){const ni=i+di,nj=j+dj;if(ni<0||nj<0||ni>=GRID||nj>=GRID)continue;
      const n=nj*GRID+ni;if(prev[n]>=0||!g[n]||(di&&dj&&(!g[j*GRID+ni]||!g[nj*GRID+i])))continue;prev[n]=k;q.push(n);}}
  if(prev[t]<0)return [b];
  const cells=[];for(let k=t;k!==s;k=prev[k])cells.push([(k%GRID+.5)/GRID,(Math.floor(k/GRID)+.5)/GRID]);
  const pts=[...cells.reverse(),b],out=[];let from=a;
  for(let i=0;i<pts.length;){let j=pts.length-1;while(j>i&&!clearLine(L,from,pts[j]))j--;out.push(pts[j]);from=pts[j];i=j+1;}
  return out;
}
/** The walkable point nearest (x,y) on the way back toward the plaza. */
export function nearestWalkable(L,x,y){
  if(walkable(L,x,y))return [x,y];
  const c=centre(L);
  for(let i=1;i<=60;i++){const t=i/60,px=x+(c[0]-x)*t,py=y+(c[1]-y)*t;if(walkable(L,px,py))return [px,py];}
  return c;
}
/** Where to stand to use a facility or a spot. */
export const doorOf=(L,id)=>{const s=L.slots[id];if(s)return nearestWalkable(L,...s.door);const p=L.spots.find(x=>x.id===id);return p?nearestWalkable(L,...(p.stand||[p.x,p.y])):null;};
export const spotById=(L,id)=>L.spots.find(s=>s.id===id)||null;
export const spotLine=(s,n=0)=>s.lines[Math.abs(n|0)%s.lines.length];
/** The facility under a map point (its slot, a little generous), else null. */
export function facilityAt(L,x,y,pad=.02){
  let best=null,bd=1e9;
  for(const s of Object.values(L.slots)){
    const r=s.id==='cong_bang'?{x:s.x,y:s.y,w:.13,h:.13}:s;
    if(Math.abs(x-r.x)<=r.w/2+pad&&Math.abs(y-r.y)<=r.h/2+pad){const d=Math.hypot(x-r.x,y-r.y);if(d<bd){bd=d;best=s;}}
  }
  return best;
}
/** The decorative spot within `r` of (x,y), nearest first. */
export function spotNear(L,x,y,r=.05){let best=null,bd=r;for(const s of L.spots){const d=Math.hypot(s.x-x,s.y-y);if(d<=bd){best=s;bd=d;}}return best;}
/** Every id a player may "do" in the live room (facilities and spots): live/bang_island.py keeps the same list. */
export const SPOT_IDS=[...FACILITY_IDS,...Object.keys(SPOT_INFO)];
/** The look of a facility at `level`: 0 not built, 1 (1–3), 2 (4–6), 3 (7–10) (game/bang_island.py band). */
export const band=level=>level<=0?0:level<=3?1:level<=6?2:3;
/** Arrow keys and W A S D walk along the screen (the map is turned 45°): [dx, dy] on the map. */
export const SCREEN_KEYS={u:[-R2,-R2],d:[R2,R2],l:[-R2,R2],r:[R2,-R2]};
