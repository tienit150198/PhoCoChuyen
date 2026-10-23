/** 🛠️ Chế độ xây (game/island_design.py, game/island_build.py): the owner's island full screen, phone first. The map is
 * the old interface's walk (v4/island-walk.js) moved and zoomed by the finger (pinch, wheel, ＋ －), the grid over it while
 * something is being placed. Pick a building, a decoration from the shop or one from 📦 Kho: it stands on the map as a
 * ghost, green where it fits and red where it does not (public/js/island-layout.js fitsWhy, the server's own rules), drag
 * it, ⟳ turn it, ✓ place it. Tap what stands on the island: ✥ dời, ⟳ xoay, 📦 cất kho, 🏗️ chi tiết. 🌊 Lấn biển grows
 * the island a size (jr_isle_expand), 🛤️ lối mòn draws the footpaths (jr_isle_opt). Every rule, price and point is the
 * server's: this sends jr_isle_place / dmove / store / bmove / build and draws api.state.journey.isld after each. */
import {escapeHTML as esc} from '../icons.js';
import {layout,withDesign,withBuilds,footpaths,GRID,decorMeta,fitsWhy,footprint,cellsMiddle,cellOf} from '../island-layout.js';
import {splitKind} from '../house-art.js';
import {paintDecorItem,previewDecorItem,paintBuildingModel,previewBuilding} from '../island-decor-art.js';
import {createWalkRenderer,FLAT} from './island-walk.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const E={dlg:null,env:null,iid:'',look:'',r:null,cam:null,fitS:1,raf:0,tab:'cay',ghost:null,sel:'',busy:false,flash:null,flashTimer:0,
  ptr:new Map(),drag:null,pinch:null,L:null,key:'',taken:new Map(),onClose:null,openDetail:null,skew:0,off:null,why:''};

/* ---- what the server sent ---- */
const J=()=>E.env?.api?.state?.journey||{};
const CAT=()=>E.env?.api?.content?.journey?.island||null;
const BC=()=>CAT()?.build||null;
const DC=()=>BC()?.design||null;
const ISLE=()=>(CAT()?.islands||[]).find(i=>i.id===E.iid)||null;
const design=()=>J().isld?.i?.[E.iid]||null;
const kho=()=>J().isld?.inv||{};
const plots=()=>J().islb?.p?.[E.iid]||{};
const KIND=k=>{const id=splitKind(String(k||''))[0];return (BC()?.buildings||[]).find(b=>b.id===id)||null;};
const ITEM=id=>(DC()?.decor||[]).find(d=>d.id===id)||null;
const now=()=>Date.now()/1000+E.skew;
const tier=()=>Number(design()?.t)||0;
const rows=()=>Object.entries(plots()).map(([p,e])=>({p:Number(p),k:e.k,l:e.l,b:e.b,t:e.t}));
const cash=()=>Number(J().wallet)||0;
/** The money rule of game/lux.py ready_why: the wallet, then the bank; never with the wallet in debt. */
const moneyWhy=price=>cash()<0?'Ví đang nợ':cash()+(Number(J().bank?.balance)||0)>=price?'':`Còn thiếu ${fmt(price-cash()-(Number(J().bank?.balance)||0))} xu`;

/** {cell: tag} of what stands on the island ('b<plot>' a building, 'd<id>' a decoration; game/island_design.py
 * occupied()), `skip` left out. */
export function occupiedCells(d,builds,skip=''){
  const out=new Map(),F=GRID.FOOT;
  for(const [p,pos] of Object.entries(d?.b||{})){const tag='b'+p;if(tag===skip||!builds[p]||!Array.isArray(pos))continue;
    for(const c of footprint(F,F,pos[0],pos[1],pos[2]||0))if(!out.has(c))out.set(c,tag);}
  for(const row of Array.isArray(d?.d)?d.d:[]){const [id,kind,x,y,r]=row,m=decorMeta(kind),tag='d'+id;if(tag===skip||!m)continue;
    for(const c of footprint(m.w,m.h,x,y,r||0))if(!out.has(c))out.set(c,tag);}
  return out;
}
/** What a tag stands for: {tag, kind, name, emoji, x, y, r, w, h, where, rot, id | plot}. */
function thing(tag){
  const d=design();if(!tag||!d)return null;
  if(tag[0]==='d'){const row=(d.d||[]).find(v=>'d'+v[0]===tag),m=row&&decorMeta(row[1]),it=row&&ITEM(row[1]);if(!m)return null;
    return {tag,src:'item',id:row[0],kind:row[1],name:m.name,emoji:m.emoji,x:row[2],y:row[3],r:row[4]||0,w:m.w,h:m.h,where:m.where,rot:it?it.rot!==false:true};}
  const plot=tag.slice(1),e=plots()[plot],pos=d.b?.[plot],k=e&&KIND(e.k);if(!k||!pos)return null;
  return {tag,src:'bld',plot:Number(plot),kind:k.id,look:splitKind(String(e.k))[1]||0,name:k.name,emoji:k.emoji,x:pos[0],y:pos[1],r:pos[2]||0,
    w:GRID.FOOT,h:GRID.FOOT,where:k.coast?'coast':'land',rot:Boolean(k.looks?.length),level:e.l};
}

/* ---- the map ---- */
function rebuild(force=false){
  const d=design(),hide=E.ghost?.tag||'',key=JSON.stringify([d,plots(),hide,E.look]);
  if(!force&&key===E.key)return;E.key=key;
  const dd=d?{...d,d:(d.d||[]).filter(v=>'d'+v[0]!==hide)}:null;
  const base=withDesign(layout(E.look),dd);
  E.L=withBuilds(base,rows().filter(r=>'b'+r.p!==hide),now());
  E.taken=occupiedCells(d,plots(),hide);
  E.r?.setLayout(base,footpaths(E.L));E.r?.setBuilds(E.L.built);
  if(E.ghost)check();
}
/** The camera that shows the whole island (its coast at this size) on the stage. */
function fit(){
  const [w,h]=E.r?.size||[360,480],pts=E.L?.shore||[[0,0],[1,1]];
  let x0=Infinity,x1=-Infinity,y0=Infinity,y1=-Infinity;for(const [x,y] of pts){x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y);}
  const m=.08,S=Math.max(120,Math.min(w/(x1-x0+m*2),h/((y1-y0+m*2)*FLAT)));
  E.fitS=S;E.cam={S,ox:w/2-(x0+x1)/2*S,oy:h/2-(y0+y1)/2*S*FLAT};
}
const toMap=(sx,sy)=>[(sx-E.cam.ox)/E.cam.S,(sy-E.cam.oy)/(E.cam.S*FLAT)];
function local(e){const b=E.cv.getBoundingClientRect();return [e.clientX-b.left,e.clientY-b.top];}
function zoom(f,sx,sy){
  const [w,h]=E.r?.size||[360,480];if(sx==null){sx=w/2;sy=h/2;}
  const [mx,my]=toMap(sx,sy),S=Math.max(E.fitS*.7,Math.min(Math.max(E.fitS*5,2400),E.cam.S*f));
  E.cam={S,ox:sx-mx*S,oy:sy-my*S*FLAT};clampCam();
}
function clampCam(){
  const [w,h]=E.r?.size||[360,480],[lo,hi]=[GRID.X0,GRID.X0+GRID.G*GRID.CELL],c=E.cam;
  c.ox=Math.max(w*.5-hi*c.S,Math.min(w*.5-lo*c.S,c.ox));c.oy=Math.max(h*.5-hi*c.S*FLAT,Math.min(h*.5-lo*c.S*FLAT,c.oy));
}

/* ---- the ghost: what is being placed ---- */
/** Start placing: a decoration of the shop or the kho, a new building, or something already on the island (moved). */
function pick(src,kind,{r=0,at=null,ok=false}={}){
  let g;
  if(src==='shop'||src==='kho'){const it=ITEM(kind),m=decorMeta(kind);if(!it||!m)return;
    g={src,kind,name:it.name,emoji:it.emoji,w:m.w,h:m.h,where:m.where,rot:it.rot!==false,price:src==='kho'?0:it.price,pts:it.pts,r:0};}
  else if(src==='bnew'){const k=KIND(kind);if(!k)return;
    g={src,kind:k.id,name:k.name,emoji:k.emoji,w:GRID.FOOT,h:GRID.FOOT,where:k.coast?'coast':'land',rot:Boolean(k.looks?.length),price:k.levels[0].price,hours:k.levels[0].hours,pts:k.pts,r:0,look:0};}
  else return;
  if(g.rot)g.r=r&3;g.ok=ok;
  E.sel='';E.ghost=g;rebuild();
  const [w,h]=E.r?.size||[360,480],[mx,my]=at||toMap(w/2,h*.45);place(mx,my,true);
  if(!at&&E.cam.S<E.fitS*1.5){const [cx,cy]=cellsMiddle(g.w,g.h,g.x,g.y,g.r),S=E.fitS*(g.w*g.h>4?1.6:2.2);E.cam={S,ox:w/2-cx*S,oy:h*.45-cy*S*FLAT};clampCam();}   // close enough to see it
  panel();
}
/** A cheap decoration (a tree, a lamp, a path stone) is placed again and again: after one, the next of the same stands
 * beside it (the purchase asked once). A dear one, a building or a move ends there. */
const AGAIN_MAX=1_000_000;
/** Move what stands on the island: it leaves the map, its ghost takes its place. */
function lift(tag){const t=thing(tag);if(!t)return;E.sel='';E.ghost={...t,from:[t.x,t.y,t.r]};rebuild();check();panel();}
/** The ghost to the cell nearest a map point; `seek`: the nearest place it fits around there. */
function place(mx,my,seek=false){
  const g=E.ghost;if(!g)return;let [x,y]=cellOf(mx,my,g.w,g.h,g.r);
  if(seek&&why(x,y,g.r)){
    outer:for(let rad=1;rad<24;rad++)for(let dy=-rad;dy<=rad;dy++)for(let dx=-rad;dx<=rad;dx++){
      if(Math.max(Math.abs(dx),Math.abs(dy))!==rad)continue;if(!why(x+dx,y+dy,g.r)){x+=dx;y+=dy;break outer;}}
  }
  if(x===g.x&&y===g.y)return;g.x=x;g.y=y;check();
}
function why(x,y,r){const g=E.ghost;return fitsWhy(E.look,tier(),g.w,g.h,g.where,x,y,r,E.taken);}
/** Why the ghost cannot be placed where it is ('' when it can): the place, then the island's limits and the money. */
function check(){
  const g=E.ghost;if(!g)return '';
  let w=why(g.x,g.y,g.r);
  if(!w&&(g.src==='shop'||g.src==='kho')){const it=ITEM(g.kind),d=design(),n=(d?.d||[]).filter(v=>v[1]===g.kind).length;
    if(it&&n>=it.max)w=`Mỗi đảo tối đa ${it.max} ${it.name}.`;
    else if((d?.d||[]).length>=(DC()?.items_max||300))w=`Mỗi đảo tối đa ${DC()?.items_max||300} món trang trí.`;
    else if(g.src==='kho'&&!(kho()[g.kind]>0))w='Kho đã hết món này.';
    else if(g.src==='shop')w=moneyWhy(g.price);}
  if(!w&&g.src==='bnew')w=buildWhy(KIND(g.kind))||moneyWhy(g.price);
  E.why=w;bar();return w;
}
/** Why building `k` cannot start on this island ('' when it can): the big islands, how many, the crews. */
function buildWhy(k){
  const bc=BC(),i=ISLE();if(!k||!bc||!i)return 'Chưa xây được.';
  if(k.big&&i.price<bc.big_from)return 'Chỉ đảo lớn';
  const all=Object.values(plots());
  if(k.max&&all.filter(e=>splitKind(String(e.k))[0]===k.id).length>=k.max)return `Mỗi đảo ${k.max}`;
  const busy=all.filter(e=>e.b&&e.t>now()).length;if(busy>=(bc.crews||2))return `Cả ${bc.crews||2} đội thợ đang bận`;
  return '';
}
function turnGhost(){
  const g=E.ghost;if(!g?.rot)return;const [mx,my]=cellsMiddle(g.w,g.h,g.x,g.y,g.r);g.r=(g.r+1)&3;g.x=null;place(mx,my,true);check();
}

/* ---- drawing over the map: the grid, the ghost, what is chosen ---- */
function viewAt(P,cam,mx,my){
  const k=cam.S/900,ctx=E.ctx;
  return {zs:k,depth:(x,y)=>y,light:(nx,ny,nz)=>Math.max(.66,Math.min(1.14,.86+.14*ny+.24*nz+.1*nx)),
    P:(x,y,z)=>{const [a,b]=P(mx+x,my+y);return [a,b-z*k];},
    fill(pts,color,alpha=1){ctx.globalAlpha=alpha;ctx.fillStyle=color;ctx.beginPath();pts.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fill();ctx.globalAlpha=1;},
    circle(x,y,r,color,alpha=1){ctx.globalAlpha=alpha;ctx.fillStyle=color;ctx.beginPath();ctx.arc(x,y,Math.max(.5,r),0,Math.PI*2);ctx.fill();ctx.globalAlpha=1;},
    line(a,b,color,lw){ctx.strokeStyle=color;ctx.lineWidth=lw;ctx.lineCap='round';ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();}};
}
function cellRect(ctx,P,x,y,w,h){const [a,b]=P(GRID.X0+x*GRID.CELL,GRID.X0+y*GRID.CELL),[c,d]=P(GRID.X0+(x+w)*GRID.CELL,GRID.X0+(y+h)*GRID.CELL);return [a,b,c-a,d-b];}
function overlay(ctx,P,cam,t){
  const g=E.ghost,C=GRID.CELL,X0=GRID.X0;
  if(g&&g.x!=null){
    const [ww,hh]=g.r&1?[g.h,g.w]:[g.w,g.h],R=10,i0=Math.max(0,g.x-R),i1=Math.min(GRID.G,g.x+ww+R),j0=Math.max(0,g.y-R),j1=Math.min(GRID.G,g.y+hh+R);
    ctx.strokeStyle='rgba(255,255,255,.28)';ctx.lineWidth=1;ctx.beginPath();
    for(let i=i0;i<=i1;i++){const [a,b]=P(X0+i*C,X0+j0*C),[,d]=P(X0+i*C,X0+j1*C);ctx.moveTo(a,b);ctx.lineTo(a,d);}
    for(let j=j0;j<=j1;j++){const [a,b]=P(X0+i0*C,X0+j*C),[c]=P(X0+i1*C,X0+j*C);ctx.moveTo(a,b);ctx.lineTo(c,b);}
    ctx.stroke();
    const ok=!E.why,[a,b,w,h]=cellRect(ctx,P,g.x,g.y,ww,hh),pulse=.3+.12*Math.sin(t/260);
    ctx.fillStyle=ok?`rgba(70,210,110,${pulse})`:`rgba(235,70,60,${pulse+.08})`;ctx.fillRect(a,b,w,h);
    ctx.strokeStyle=ok?'#3fd07a':'#ff5a4a';ctx.lineWidth=2.5;ctx.strokeRect(a,b,w,h);
    const [mx,my]=cellsMiddle(g.w,g.h,g.x,g.y,g.r),v=viewAt(P,cam,mx,my);
    try{if(g.src==='bnew'||g.src==='bld')paintBuildingModel(g.kind,Math.max(1,g.level||1),g.look||0,g.r,v);else paintDecorItem(g.kind,g.r,v);}catch{/* an unknown kind: the square alone */}
    const [hx,hy]=P(mx,my+hh*C/2);ctx.fillStyle=ok?'#2fa463':'#d9483b';ctx.beginPath();ctx.arc(hx,hy+14,11,0,Math.PI*2);ctx.fill();
    ctx.fillStyle='#fff';ctx.font='bold 13px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('✥',hx,hy+14.5);
  }
  if(E.sel){const s=thing(E.sel);if(s){const [ww,hh]=s.r&1?[s.h,s.w]:[s.w,s.h],[a,b,w,h]=cellRect(ctx,P,s.x,s.y,ww,hh);
    ctx.setLineDash([6,4]);ctx.lineDashOffset=-t/60;ctx.strokeStyle='#ffd75a';ctx.lineWidth=2.5;ctx.strokeRect(a,b,w,h);ctx.setLineDash([]);
    ctx.fillStyle='rgba(255,215,90,.18)';ctx.fillRect(a,b,w,h);}}
}
function loop(t){
  if(!E.r||!E.dlg?.open)return;
  try{E.r.frame({people:[],vehicle:null,camera:E.cam,overlay},t);}catch{/* the next frame tries again */}
  E.raf=requestAnimationFrame(loop);
}

/* ---- the finger on the map ---- */
function onDown(e){
  E.cv.setPointerCapture?.(e.pointerId);const [x,y]=local(e);E.ptr.set(e.pointerId,[x,y]);
  if(E.ptr.size===2){const [p,q]=[...E.ptr.values()];E.pinch={d:Math.hypot(p[0]-q[0],p[1]-q[1])||1,S:E.cam.S};E.drag=null;return;}
  const g=E.ghost;let on=false;
  if(g&&g.x!=null){const [mx,my]=toMap(x,y),[ww,hh]=g.r&1?[g.h,g.w]:[g.w,g.h],gx=(mx-GRID.X0)/GRID.CELL,gy=(my-GRID.X0)/GRID.CELL;
    on=gx>=g.x-1.5&&gx<=g.x+ww+1.5&&gy>=g.y-1.5&&gy<=g.y+hh+2.5;}
  E.drag={id:e.pointerId,x,y,x0:x,y0:y,moved:false,ghost:on,touch:e.pointerType==='touch'};
}
function onMove(e){
  if(!E.ptr.has(e.pointerId))return;const [x,y]=local(e);E.ptr.set(e.pointerId,[x,y]);
  if(E.pinch&&E.ptr.size>=2){const [p,q]=[...E.ptr.values()],d=Math.hypot(p[0]-q[0],p[1]-q[1])||1;zoom(E.pinch.S*d/E.pinch.d/E.cam.S,(p[0]+q[0])/2,(p[1]+q[1])/2);return;}
  const dr=E.drag;if(!dr||dr.id!==e.pointerId)return;
  if(!dr.moved&&Math.hypot(x-dr.x0,y-dr.y0)>6)dr.moved=true;
  if(!dr.moved)return;
  if(dr.ghost){const [mx,my]=toMap(x,y-(dr.touch?28:0));place(mx,my);}
  else{E.cam.ox+=x-dr.x;E.cam.oy+=y-dr.y;clampCam();}
  dr.x=x;dr.y=y;
}
function onUp(e){
  const dr=E.drag;E.ptr.delete(e.pointerId);
  if(E.ptr.size<2)E.pinch=null;
  if(!dr||dr.id!==e.pointerId)return;E.drag=null;
  if(dr.moved)return;
  const [mx,my]=toMap(dr.x0,dr.y0);
  if(E.ghost){place(mx,my);return;}
  const G=GRID.G,i=Math.floor((mx-GRID.X0)/GRID.CELL),j=Math.floor((my-GRID.X0)/GRID.CELL);let tag='';
  const all=occupiedCells(design(),plots());
  for(const dj of [0,1,2,3]){if(i<0||i>=G||j+dj<0||j+dj>=G)continue;const c=(j+dj)*G+i;if(all.has(c)){tag=all.get(c);break;}}
  E.sel=tag===E.sel?'':tag;panel();
}

/* ---- the panel under the map ---- */
function head(){
  const d=design(),i=ISLE(),t=tier(),name=DC()?.tiers?.[t]?.name||'';
  return `<header class="isl-ed-head"><button type="button" class="isl-ed-x" data-ed="close" aria-label="Đóng">✕</button>
    <div class="isl-ed-title"><h2 id="isl-ed-title">🛠️ ${esc(i?.name||'Đảo')}</h2><small>${esc(name)} · ✨ ${fmt(d?.pts||0)} điểm</small></div>
    <span class="isl-ed-wallet" title="Ví">👛 ${fmt(Math.max(0,cash()))}</span></header>`;
}
function tabs(){
  const cats=DC()?.cats||[],n=Object.values(kho()).reduce((a,v)=>a+v,0);
  const list=[['b','🏠 Nhà'],...cats.map(([id,label])=>[id,label]),['kho',`📦 Kho${n?` ${n}`:''}`]];
  return `<nav class="isl-ed-tabs" role="tablist" aria-label="Danh mục">${list.map(([id,label])=>`<button type="button" role="tab" class="${E.tab===id?'on':''}" data-ed="tab" data-id="${esc(id)}" aria-selected="${E.tab===id}">${esc(label)}</button>`).join('')}</nav>`;
}
function cards(){
  const d=design(),count=k=>(d?.d||[]).filter(v=>v[1]===k).length;
  if(E.tab==='b'){
    const all=(BC()?.buildings||[]).slice().sort((a,b)=>(a.cat==='home')===(b.cat==='home')?a.levels[0].price-b.levels[0].price:a.cat==='home'?-1:1);
    return all.map(k=>{const w=buildWhy(k);
      return `<button type="button" class="isl-ed-card${w?' off':''}" data-ed="pick" data-src="bnew" data-id="${esc(k.id)}"${w?' aria-disabled="true"':''}><canvas data-pv="${esc(k.id)}" data-pk="b" aria-hidden="true"></canvas>
        <b>${esc(k.name)}</b><small>${fmt(k.levels[0].price)} xu</small><i>✨${k.pts}${k.coast?' · ⚓':''}</i>${w?`<em>${esc(w)}</em>`:''}</button>`;}).join('');
  }
  if(E.tab==='kho'){
    const have=Object.entries(kho()).filter(([k,n])=>n>0&&ITEM(k));
    if(!have.length)return `<p class="isl-ed-empty">Kho trống. Đồ cất vào kho hoặc đồ trên bờ cũ khi lấn biển sẽ nằm ở đây, đặt lại miễn phí.</p>`;
    return have.map(([k,n])=>{const it=ITEM(k),w=count(k)>=it.max?`Đủ ${it.max}`:'';
      return `<button type="button" class="isl-ed-card${w?' off':''}" data-ed="pick" data-src="kho" data-id="${esc(k)}"><canvas data-pv="${esc(k)}" data-pk="d" aria-hidden="true"></canvas>
        <b>${esc(it.name)}</b><small>📦 ×${n} · miễn phí</small><i>✨${it.pts}</i>${w?`<em>${esc(w)}</em>`:''}</button>`;}).join('');
  }
  return (DC()?.decor||[]).filter(it=>it.cat===E.tab).map(it=>{const n=count(it.id),w=n>=it.max?`Đủ ${it.max}`:'',k=kho()[it.id]||0;
    return `<button type="button" class="isl-ed-card${w?' off':''}" data-ed="pick" data-src="${k?'kho':'shop'}" data-id="${esc(it.id)}"${w?' aria-disabled="true"':''}><canvas data-pv="${esc(it.id)}" data-pk="d" aria-hidden="true"></canvas>
      <b>${esc(it.name)}</b><small>${k?`📦 ×${k} · miễn phí`:`${fmt(it.price)} xu`}</small><i>✨${it.pts}${n?` · có ${n}`:''}</i>${w?`<em>${esc(w)}</em>`:''}</button>`;}).join('');
}
function tools(){
  const d=design(),t=tier(),tiers=DC()?.tiers||[],next=tiers[t+1],price=DC()?.expand?.[E.iid]?.[t]||0;
  const grow=next?`<button type="button" class="isl-ed-tool" data-ed="expand"${E.busy?' disabled':''}>🌊 Lấn biển<small>${fmt(price)} xu · ✨+${next.pts}</small></button>`
    :`<span class="isl-ed-tool done">🌊 Đảo đã rộng nhất</span>`;
  const on=Boolean(d?.ap);
  return `<div class="isl-ed-tools">${grow}<button type="button" class="isl-ed-tool" data-ed="paths" aria-pressed="${on}"${E.busy?' disabled':''}>🛤️ Lối mòn<small>${on?'Đang bật':'Đang tắt'}</small></button></div>`;
}
function bar(){
  const el=E.dlg?.querySelector('.isl-ed-why');if(!el||!E.ghost)return;   // the ghost's bar (not yet drawn: panel() calls again)
  const g=E.ghost,w=E.why;
  el.textContent=w||(g.src==='item'||g.src==='bld'?'Kéo tới chỗ mới rồi chạm ✓.':'Kéo để chọn chỗ, chạm ✓ để đặt.');
  el.classList.toggle('bad',Boolean(w));
  const ok=E.dlg.querySelector('[data-ed="ok"]');if(ok)ok.disabled=Boolean(w)||E.busy;
}
function panel(){
  const root=E.dlg?.querySelector('.isl-ed-panel');if(!root)return;
  E.dlg.querySelector('.isl-ed-headbox').innerHTML=head();
  let html;
  if(E.ghost){const g=E.ghost,cost=g.src==='shop'||g.src==='bnew'?`${fmt(g.price)} xu`:g.src==='kho'?'Từ kho · miễn phí':'Dời chỗ · miễn phí';
    html=`<div class="isl-ed-bar"><div class="isl-ed-what"><span aria-hidden="true">${g.emoji}</span><b>${esc(g.name)}</b><small>${esc(cost)}${g.pts&&g.src!=='item'&&g.src!=='bld'?` · ✨+${g.pts}`:''}</small></div>
      <p class="isl-ed-why" role="status"></p><div class="isl-ed-btns"><button type="button" class="btn" data-ed="cancel">✕ Hủy</button>
      ${g.rot?'<button type="button" class="btn" data-ed="rot">⟳ Xoay</button>':''}<button type="button" class="btn primary" data-ed="ok">✓ Đặt</button></div></div>`;}
  else if(E.sel&&thing(E.sel)){const s=thing(E.sel);
    html=`<div class="isl-ed-bar"><div class="isl-ed-what"><span aria-hidden="true">${s.emoji}</span><b>${esc(s.name)}</b>${s.src==='bld'?`<small>⭐ cấp ${s.level||0}</small>`:''}</div>
      <div class="isl-ed-btns"><button type="button" class="btn" data-ed="move">✥ Dời</button>${s.rot?'<button type="button" class="btn" data-ed="turn">⟳ Xoay</button>':''}
      ${s.src==='item'?'<button type="button" class="btn" data-ed="store">📦 Cất kho</button>':''}${s.src==='bld'&&E.openDetail?'<button type="button" class="btn" data-ed="detail">🏗️ Chi tiết</button>':''}
      <button type="button" class="btn" data-ed="unsel" aria-label="Bỏ chọn">✕</button></div></div>`;}
  else html=`${tools()}${tabs()}<div class="isl-ed-cards">${cards()}</div>`;
  root.innerHTML=html;root.setAttribute('aria-busy',String(E.busy));
  for(const cv of root.querySelectorAll('canvas[data-pv]')){try{cv.dataset.pk==='b'?previewBuilding(cv,cv.dataset.pv):previewDecorItem(cv,cv.dataset.pv);}catch{/* no picture */}}
  if(E.ghost){check();}
}
function say(text,kind='good'){
  const el=E.dlg?.querySelector('.isl-ed-flash');if(!el)return;clearTimeout(E.flashTimer);
  el.textContent=text||'';el.className=`isl-ed-flash ${kind}`;el.hidden=!text;
  E.flashTimer=setTimeout(()=>{el.hidden=true;},kind==='bad'?5000:3500);
}
async function send(action,payload){
  if(E.busy)return null;E.busy=true;panel();
  try{const r=await E.env.api.command(action,payload);say([r?.message,...(r?.effects||[])].filter(Boolean).join(' '),r?.refused?'bad':'good');return r;}
  catch(e){say(e?.message||'Chưa làm được. Thử lại nhé.','bad');return null;}
  finally{E.busy=false;rebuild();panel();}
}

/* ---- the buttons ---- */
async function onClick(op,data){
  const env=E.env;
  switch(op){
    case'close':close();return;
    case'tab':E.tab=data.id;panel();return;
    case'pick':pick(data.src,data.id);return;
    case'cancel':E.ghost=null;rebuild();panel();return;
    case'rot':turnGhost();return;
    case'unsel':E.sel='';panel();return;
    case'move':lift(E.sel);return;
    case'zin':zoom(1.35);return;
    case'zout':zoom(1/1.35);return;
    case'fit':fit();return;
    case'detail':{const s=thing(E.sel);if(s?.src==='bld'){const fn=E.openDetail;close();fn?.(s.plot);}return;}
    case'store':{const s=thing(E.sel);if(!s||s.src!=='item')return;const r=await send('jr_isle_store',{island:E.iid,id:s.id});if(r&&!r.refused)E.sel='';panel();return;}
    case'turn':{const s=thing(E.sel);if(!s?.rot)return;
      const [mx,my]=cellsMiddle(s.w,s.h,s.x,s.y,s.r),r=(s.r+1)&3,[x,y]=cellOf(mx,my,s.w,s.h,r),taken=occupiedCells(design(),plots(),s.tag);
      const w=fitsWhy(E.look,tier(),s.w,s.h,s.where,x,y,r,taken);if(w){say(w,'bad');return;}
      await send(s.src==='item'?'jr_isle_dmove':'jr_isle_bmove',s.src==='item'?{island:E.iid,id:s.id,x,y,r}:{island:E.iid,plot:s.plot,x,y,r});return;}
    case'ok':{const g=E.ghost;if(!g||check())return;let r=null;
      if(g.src==='shop'){
        if(!g.ok&&!await env.confirmAction(`Mua ${g.name}?`,`${fmt(g.price)} xu, trả từ ví rồi tới tài khoản. ✨ +${g.pts} điểm Đảo đẹp. Cất kho, dời chỗ sau đều miễn phí.`,'Mua và đặt'))return;
        r=await send('jr_isle_place',{island:E.iid,kind:g.kind,x:g.x,y:g.y,r:g.r,confirm:true});}
      else if(g.src==='kho')r=await send('jr_isle_place',{island:E.iid,kind:g.kind,x:g.x,y:g.y,r:g.r});
      else if(g.src==='bnew'){
        if(!await env.confirmAction(`Xây ${g.name}?`,`${fmt(g.price)} xu, trả từ ví rồi tới tài khoản. Xong sau ${g.hours} giờ, trong lúc đó có giàn giáo.`,'Xây'))return;
        r=await send('jr_isle_build',{island:E.iid,kind:g.kind,x:g.x,y:g.y,r:g.r,confirm:true});}
      else if(g.src==='item')r=await send('jr_isle_dmove',{island:E.iid,id:g.id,x:g.x,y:g.y,r:g.r});
      else if(g.src==='bld')r=await send('jr_isle_bmove',{island:E.iid,plot:g.plot,x:g.x,y:g.y,r:g.r});
      if(r&&!r.refused){E.ghost=null;rebuild();
        const more=g.src==='kho'?kho()[g.kind]>0:g.src==='shop'&&g.price<=AGAIN_MAX;
        if(more)pick(g.src,g.kind,{r:g.r,at:cellsMiddle(g.w,g.h,g.x,g.y,g.r),ok:g.src==='shop'});   // one more of the same, beside it
        panel();}
      return;}
    case'expand':{
      const t=tier(),next=DC()?.tiers?.[t+1],price=DC()?.expand?.[E.iid]?.[t]||0,i=ISLE();if(!next||!price)return;
      const m=moneyWhy(price);if(m){say(m,'bad');return;}
      if(!await env.confirmAction(`Lấn biển ${i?.name||''}?`,`${fmt(price)} xu, trả từ ví rồi tới tài khoản. Đảo rộng thêm (${next.name}), ✨ +${next.pts} điểm. Đồ vướng bờ mới được cất vào kho.`,'Lấn biển'))return;
      const r=await send('jr_isle_expand',{island:E.iid,confirm:true});if(r&&!r.refused){rebuild(true);fit();}return;}
    case'paths':await send('jr_isle_opt',{island:E.iid,paths:!design()?.ap});return;
  }
}

/* ---- open / close ---- */
let cssReady=null;
const ensureCss=()=>cssReady??=new Promise(done=>{
  if(document.querySelector('link[data-isl-css]')){done();return;}
  const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.('/css/island.css')||'/css/island.css';l.setAttribute('data-isl-css','');
  l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
});
function onState(){if(!E.dlg?.open)return;if(!J().island?.own?.[E.iid]){close();return;}const before=E.key;rebuild();if(E.key!==before&&!E.busy)panel();}
function close(){
  if(!E.dlg)return;const d=E.dlg,done=E.onClose;E.dlg=null;
  cancelAnimationFrame(E.raf);E.r?.destroy();E.r=null;E.env?.api?.removeEventListener?.('state',onState);E.off?.();E.off=null;
  E.ghost=null;E.sel='';E.ptr.clear();E.drag=null;E.pinch=null;clearTimeout(E.flashTimer);
  if(d.open)d.close();d.remove();done?.();
}
/** 🛠️ Open the build mode on island `iid` (one the player owns). `onClose` after it closes; `openDetail(plot)`: a
 * building's sheet (upgrade, paint, phá dỡ: v4/island.js); `skew`: the server's clock minus this device's. */
export async function openIslandEditor(env,iid,{onClose=null,openDetail=null,skew=0}={}){
  const isle=(env?.api?.content?.journey?.island?.islands||[]).find(i=>i.id===iid);
  if(!isle||!env.api.state?.journey?.island?.own?.[iid])return false;
  if(E.dlg)close();
  await ensureCss();
  Object.assign(E,{env,iid,look:isle.look,onClose,openDetail,skew:Number(skew)||0,ghost:null,sel:'',key:'',busy:false});
  const d=document.createElement('dialog');d.className='isl-ed';d.setAttribute('aria-labelledby','isl-ed-title');
  d.innerHTML=`<div class="isl-ed-headbox"></div><div class="isl-ed-stage"><canvas class="isl-ed-cv" aria-label="Bản đồ đảo: kéo để xem, chụm hai ngón để phóng to"></canvas>
    <div class="isl-ed-zoom"><button type="button" data-ed="zin" aria-label="Phóng to">＋</button><button type="button" data-ed="zout" aria-label="Thu nhỏ">－</button><button type="button" data-ed="fit" aria-label="Xem cả đảo">⤢</button></div>
    <p class="isl-ed-flash" role="status" hidden></p></div><div class="isl-ed-panel"></div>`;
  document.body.append(d);E.dlg=d;
  d.addEventListener('click',e=>{const el=e.target.closest('[data-ed]');if(!el||!d.contains(el)||el.disabled||el.getAttribute('aria-disabled')==='true')return;e.preventDefault();onClick(el.dataset.ed,el.dataset);});
  d.addEventListener('cancel',e=>{e.preventDefault();if(E.ghost){E.ghost=null;rebuild();panel();}else if(E.sel){E.sel='';panel();}else close();});
  d.showModal();
  E.cv=d.querySelector('canvas');E.ctx=E.cv.getContext('2d');
  rebuild(true);panel();   // the panel first: the map gets the height that is left
  E.r=createWalkRenderer(E.cv,E.L);E.key='';rebuild(true);fit();
  E.cv.addEventListener('pointerdown',onDown);E.cv.addEventListener('pointermove',onMove);
  for(const ev of ['pointerup','pointercancel'])E.cv.addEventListener(ev,onUp);
  E.cv.addEventListener('wheel',e=>{e.preventDefault();const [x,y]=local(e);zoom(e.deltaY<0?1.15:1/1.15,x,y);},{passive:false});
  // the panel grows and shrinks under the map: the map stays where it is (what is under the finger does not jump)
  const ro=typeof ResizeObserver==='function'?new ResizeObserver(()=>{if(E.r){E.r.resize();clampCam();}}):null;ro?.observe(d.querySelector('.isl-ed-stage'));E.off=()=>ro?.disconnect();
  env.api.addEventListener('state',onState);
  E.raf=requestAnimationFrame(loop);
  return true;
}
/** For tests: the build mode's state. */
export const editorState=()=>E;
