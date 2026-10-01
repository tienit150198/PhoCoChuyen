/** 🪴 Bày trí phòng (+ 🛠️ Sửa nhà for a home you own): wherever the player lives (gác Bà Tám, phòng trọ, the dorm's
 * bunk corner, a shared home, a home they own). Every rule lives in game/deco.py (layout, coziness, sets, guests) and
 * game/reno.py (repairs); this file draws api.state.journey.deco with v4/deco-art.js and sends `jr_deco_*` /
 * `jr_reno_fix|up`. The checks below (where a piece may stand) only light the free cells: the server decides.
 * Edit mode: hold a piece (tap it in the bag or the shop), then tap a lit cell; or drag a piece (from the room, or
 * up out of the drawer) and drop it. Undo keeps the last moves (jr_deco_layout puts pieces back where they were).
 * Opened from 🏠 Nhà của bạn (v4/house.js); the back button returns there. Styles: bank.css + house.css + reno.css. */
import {icon,escapeHTML as esc} from '../icons.js';
import {Sound} from '../audio.js';
import * as A from './deco-art.js';

const S={dlg:null,env:null,tab:'deco',room:'',edit:false,held:null,sel:'',drawer:'bag',cat:'',busy:false,flash:null,
  undo:[],undoKey:'',press:null,drag:null,dragEnd:0,resetStrip:false,toTop:false,pop:'',cheer:false,photo:null,listening:false,lastLv:-1};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const low=s=>String(s||'').slice(0,1).toLowerCase()+String(s||'').slice(1);
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,op,data={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-dc="${op}"${attrs(data)}${S.busy?' disabled':''}${extra}>${label}</button>`;
const J=()=>S.env?.api?.state?.journey||{};
const V=()=>J().deco||null;                       // the place you live in, its rooms and pieces (deco.public)
const R=()=>J().reno||null;                       // the structure of a home you own (reno.public)
const CD=()=>S.env?.api?.content?.journey?.deco||{items:[],cats:[],sets:[],levels:[]};
const CR=()=>S.env?.api?.content?.journey?.reno||{parts:[],steps:[]};
let itemMap=null,itemSrc=null;
const ITEM=k=>{const list=CD().items;if(itemSrc!==list){itemSrc=list;itemMap=new Map(list.map(i=>[i.id,i]));}return itemMap.get(k);};
const PART=id=>CR().parts.find(x=>x.id===id)||{};
const POCKET=['account','wallet'];
const condWord=(c,p)=>c>=85?'Như mới':c>=65?'Còn tốt':c>=45?'Hơi cũ':(PART(p).flaw||'Xuống cấp');
const tone=c=>c>=65?'good':c>=45?'warn':'bad';
const MAXC=40;                                    // the meter's end: Tổ ấm trong mơ
const SAY=['Phòng hơi trống… Mochi buồn ngủ quá.','Bắt đầu dễ thương rồi nè!','Ấm áp ghê, Mochi thích lắm!','Wow, phòng xinh quá trời!','Tổ ấm trong mơ! Mochi không muốn đi đâu hết.'];
const TIP_KEY='mnl.decoTip';
const tipSeen=()=>{try{return localStorage.getItem(TIP_KEY)==='1';}catch{return false;}};
const tipDone=()=>{try{localStorage.setItem(TIP_KEY,'1');}catch{/* private window: the tip just shows again */}};

/* ---- sounds (settings: sound, detailSfx) ---- */
let snd=null;
function sfx(name){
  const st=S.env?.api?.state?.settings||{};if(st.sound===false)return;
  try{snd??=new Sound();snd.configure(st);snd[name]?.();}catch{/* silent */}
}

/* ---- styles on first use ---- */
let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=Promise.all([link('/css/bank.css','bk-css'),link('/css/house.css','hs-css'),link('/css/reno.css','rn-css')]);

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium bk-sheet rn-sheet dc-sheet';d.setAttribute('aria-labelledby','dc-title');
  d.innerHTML='<div class="dc-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-dc]');if(!el||!d.contains(el)||el.disabled)return;
    if(S.drag||Date.now()-S.dragEnd<450)return;   // the click that ends a drag
    e.preventDefault();onClick(el.dataset.dc,el.dataset);
  });
  d.addEventListener('keydown',onKey);
  d.addEventListener('pointerdown',onDown);
  d.addEventListener('pointermove',onMove);
  d.addEventListener('pointerup',onUp);
  d.addEventListener('pointercancel',onCancel);
  d.addEventListener('cancel',e=>{if(S.held||S.sel){e.preventDefault();S.held=null;S.sel='';render();}});
  d.addEventListener('close',()=>{S.flash=null;S.held=null;S.sel='';S.photo=null;S.drag=null;S.press=null;floatGhost(null);});
  S.dlg=d;return d;
}

export async function openReno(env,mode){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';
    env.api.addEventListener('state',()=>{const j=S.env.api.state?.journey;const key=JSON.stringify([j?.deco,j?.reno,j?.wallet]);if(key===seen)return;seen=key;if(S.dlg?.open&&!S.busy&&!S.drag&&!S.press)render();});
  }
  await ensureCss();
  const d=dialog();
  S.tab=mode==='fix'&&R()?'fix':'deco';S.edit=mode==='decor';S.held=null;S.sel='';S.flash=null;S.photo=null;S.cat='';
  const v=V();
  if(v){if(!v.rooms.some(r=>r.id===S.room))S.room=v.rooms[0]?.id||'';S.drawer=v.bag.length?'bag':'shop';}
  if(!d.open){d.showModal();d.scrollTop=0;S.toTop=true;}
  render();
}

async function send(action,payload={},opts={}){
  const {api}=S.env;S.busy=true;paintBusy();
  try{
    const r=await api.command(action,payload);
    S.flash={text:[r.message,...(r.effects||[]).filter(Boolean)].filter(Boolean).join(' '),kind:'good'};
    return r;
  }catch(e){
    if(!e.quiet){S.flash={text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};if(!opts.silent)sfx('error');}
    return null;
  }finally{S.busy=false;render();}
}
const ask=(title,msg,label,cost)=>S.env.confirmAction(title,msg,label,cost?{cost,pocket:POCKET}:undefined);

/* ---- the layout, as the client sees it ---- */
const roomOf=id=>(V()?.rooms||[]).find(r=>r.id===id)||null;
const placed=uid=>(V()?.items||[]).find(i=>i.id===uid)||null;
const posOf=uid=>{const p=placed(uid);return p?[p.r,p.x,p.y,p.f]:null;};
const cellKey=(x,y)=>x+','+y;
const rowsFor=(rm,it)=>it.spot==='wall'?rm.wrows:rm.frows;

/** {wall,floor,rug,top: Map cell → uid|'#fixture'; surf: Map cell → height} of one room, leaving out `skip`. */
function occupancy(rm,skip=new Set()){
  const o={wall:new Map(),floor:new Map(),rug:new Map(),top:new Map(),surf:new Map()};
  for(const f of rm.fix)for(let i=0;i<f.w;i++)for(let k=0;k<f.h;k++){const c=cellKey(f.x+i,f.y+k);o[f.layer].set(c,'#'+f.t);if(f.surface)o.surf.set(c,f.surface);}
  for(const p of V().items){
    if(p.r!==rm.id||skip.has(p.id))continue;const it=ITEM(p.k);if(!it)continue;
    for(let i=0;i<it.w;i++)for(let k=0;k<it.h;k++){const c=cellKey(p.x+i,p.y+k);o[it.spot].set(c,p.id);if(it.spot==='floor'&&it.surface)o.surf.set(c,it.surface);}
  }
  return o;
}
/** deco.fit: null when the piece may stand there. */
function fit(rm,it,x,y,o){
  if(!it.rooms.includes(rm.type))return 'type';
  const rows=rowsFor(rm,it);if(!rows)return 'nowall';
  if(x<0||y<0||x+it.w>rm.cols||y+it.h>rows)return 'bounds';
  for(let i=0;i<it.w;i++)for(let k=0;k<it.h;k++){
    const c=cellKey(x+i,y+k);
    if(o[it.spot].get(c))return 'taken';
    if(it.spot==='floor'&&!it.surface&&o.top.get(c))return 'covers';
    if(it.spot==='top'){const u=o.floor.get(c);if(u&&!o.surf.get(c))return 'support';}
  }
  return null;
}
/** The small things standing on a surface piece (they move with it). */
function riders(uid){
  const p=placed(uid),it=p&&ITEM(p.k);if(!it||it.spot!=='floor'||!it.surface)return [];
  return V().items.filter(q=>q.id!==uid&&q.r===p.r&&ITEM(q.k)?.spot==='top'&&q.x>=p.x&&q.x<p.x+it.w&&q.y>=p.y&&q.y<p.y+it.h).map(q=>q.id);
}
/** Every spot the held piece may take in room `rm`: [{x,y,surf}]. */
function anchors(rm,it,moving){
  if(!rm||!it||!it.rooms.includes(rm.type))return [];
  const skip=new Set(moving?[moving,...riders(moving)]:[]),o=occupancy(rm,skip),rows=rowsFor(rm,it),out=[];
  for(let x=0;x+it.w<=rm.cols;x++)for(let y=0;y+it.h<=rows;y++)if(!fit(rm,it,x,y,o))out.push({x,y,surf:it.spot==='top'?(o.surf.get(cellKey(x,y))||0):0});
  return out;
}
const heldItem=()=>S.held?ITEM(S.held.k):null;
const roomsFor=it=>(V()?.rooms||[]).filter(r=>it.rooms.includes(r.type));

/** The spot nearest to a point (room units) among `list`, or null when the point is too far from any. */
function snap(rm,it,list,sx,sy){
  if(!list.length)return null;
  const G=A.geom(rm);
  if(it.spot==='top'){   // a cup on a table: the table's top first
    let best=null,bd=22;
    for(const a of list){if(!a.surf)continue;const cx=A.PX+a.x*A.CW+A.CW/2,cy=G.FY+(a.y+1)*A.FR-6-a.surf;const d=Math.hypot(cx-sx,cy-sy);if(d<bd){bd=d;best=a;}}
    if(best)return best;
  }
  const fx=(sx-A.PX)/A.CW-it.w/2,fy=it.spot==='wall'?(sy-G.WY)/A.WR-it.h/2:(sy-G.FY)/A.FR-it.h/2;
  let best=null,bd=1.6;
  for(const a of list){const d=Math.hypot(a.x-fx,(a.y-fy)*1.1);if(d<bd){bd=d;best=a;}}
  return best;
}

/* ---- the room ---- */
function partsMap(){const r=R();return r&&V()?.place.where==='own'?Object.fromEntries(r.parts.map(p=>[p.id,p])):null;}
function surfUnder(rm,p,it,all){
  if(it.spot!=='top')return 0;
  for(const q of all){if(q.id===p.id)continue;const u=ITEM(q.k);if(u?.spot==='floor'&&u.surface&&p.x>=q.x&&p.x<q.x+u.w&&p.y>=q.y&&p.y<q.y+u.h)return u.surface;}
  const f=rm.fix.find(f=>f.layer==='floor'&&f.surface&&p.x>=f.x&&p.x<f.x+f.w&&p.y>=f.y&&p.y<f.y+f.h);
  return f?f.surface:0;
}
/** Back to front: rugs, the wall, then the floor by its front row (a cup right after the table it stands on). */
function depthOrder(rm,list){
  const key=p=>{const it=ITEM(p.k);if(!it)return [9,0];
    if(it.spot==='rug')return [0,p.y];if(it.spot==='wall')return [1,p.y];
    if(it.spot==='top'){const host=list.find(q=>{const u=ITEM(q.k);return u?.spot==='floor'&&u.surface&&p.x>=q.x&&p.x<q.x+u.w&&p.y>=q.y&&p.y<q.y+u.h;});
      return [2,host?host.y+ITEM(host.k).h+.1:p.y+1.1];}
    return [2,p.y+it.h];};
  return [...list].sort((a,b)=>{const ka=key(a),kb=key(b);return ka[0]-kb[0]||ka[1]-kb[1];});
}
function bbox(it,p,G,surf){
  const x=A.PX+p.x*A.CW,w=it.w*A.CW,h=(A.ART[it.id]?.h||30)+4;
  if(it.spot==='wall')return [x,G.WY+p.y*A.WR,w,it.h*A.WR];
  if(it.spot==='rug')return [x,G.FY+p.y*A.FR,w,it.h*A.FR];
  const base=it.spot==='top'?G.FY+(p.y+1)*A.FR-6-surf:G.FY+(p.y+it.h)*A.FR-3;
  return [x,base-h,w,h+2];
}
const sparkles=(x,y,w,h)=>`<g class="dc-sparks" aria-hidden="true">${[[.1,.1,'#ffd34d'],[.9,.2,'#ff9ec0'],[.5,-.05,'#9fe0ff'],[.05,.75,'#b8f0a0'],[.95,.8,'#ffd34d']].map(([a,b,c],i)=>
  `<path class="dc-spark s${i}" d="M${(x+w*a).toFixed(1)} ${(y+h*b-6).toFixed(1)}l2 4.5l4.5 1.5l-4.5 1.5l-2 4.5l-2-4.5l-4.5-1.5l4.5-1.5z" fill="${c}"/>`).join('')}</g>`;

/** One room as SVG markup. opts: edit (grid, highlights), photo (no hit areas, no selection). */
function roomMarkup(rm,opts={}){
  const v=V(),G=A.geom(rm),isN=A.night(),all=v.items.filter(p=>p.r===rm.id),edit=!!opts.edit,photo=!!opts.photo;
  const out=[A.roomBack(rm,G,partsMap(),isN,(photo?'p':'')+rm.id)];
  if(edit){   // the grid: hanging spots on the wall, cells on the floor
    const g=[];
    for(let x=0;x<=rm.cols;x++){const px=A.PX+x*A.CW;if(rm.wrows)g.push(`M${px} ${G.WY}v${rm.wrows*A.WR}`);g.push(`M${px} ${G.FY}v${rm.frows*A.FR}`);}
    for(let y=0;y<=rm.wrows;y++)if(rm.wrows)g.push(`M${A.PX} ${G.WY+y*A.WR}h${rm.cols*A.CW}`);
    for(let y=0;y<=rm.frows;y++)g.push(`M${A.PX} ${G.FY+y*A.FR}h${rm.cols*A.CW}`);
    out.push(`<path class="dc-lines" d="${g.join('')}"/>`);
  }
  const moving=S.held?.uid&&S.drag?S.held.uid:'';
  for(const p of depthOrder(rm,all)){
    const it=ITEM(p.k);if(!it)continue;
    const surf=surfUnder(rm,p,it,all),[bx,by,bw,bh]=bbox(it,p,G,surf);
    const sel=!photo&&S.sel===p.id,pop=!photo&&S.pop===p.id,ghost=!photo&&(moving===p.id||(S.held?.src==='room'&&S.held.uid===p.id));
    const body=A.pieceSVG(it,p.x,p.y,p.f,G,surf);
    if(photo){out.push(body);continue;}
    out.push(`<g class="dc-it${sel?' sel':''}${pop?' pop':''}${ghost?' ghost':''}" data-uid="${esc(p.id)}" tabindex="${edit?0:-1}" role="button" aria-label="${esc(it.name)}"><g class="dc-piece">${body}</g>`
      +`<rect class="dc-hit" x="${bx}" y="${by}" width="${bw}" height="${bh}" rx="6"/>${sel?`<rect class="dc-selbox" x="${bx-3}" y="${by-3}" width="${bw+6}" height="${bh+6}" rx="9"/>`:''}${pop?sparkles(bx,by,bw,bh):''}</g>`);
  }
  out.push(A.roomFront(rm,G));
  if(isN){
    out.push(`<rect width="${G.W}" height="${G.H}" fill="#1d2448" opacity=".24" pointer-events="none"/>`);
    const glows=[];
    for(const p of all){const it=ITEM(p.k);if(!it)continue;const g=A.glowAt(it,p.x,p.y,p.f,G,surfUnder(rm,p,it,all));if(g)glows.push(`<circle cx="${g[0].toFixed(1)}" cy="${g[1].toFixed(1)}" r="${g[2]}" fill="url(#dcGlow${photo?'p':''})"/>`);}
    if(glows.length)out.push(`<defs><radialGradient id="dcGlow${photo?'p':''}"><stop offset="0" stop-color="#fff1b0" stop-opacity=".75"/><stop offset=".55" stop-color="#ffe08a" stop-opacity=".28"/><stop offset="1" stop-color="#ffe08a" stop-opacity="0"/></radialGradient></defs><g pointer-events="none">${glows.join('')}</g>`);
  }
  if(edit&&S.held){   // where the held piece may go
    const it=heldItem(),list=anchors(rm,it,S.held.src==='room'?S.held.uid:'');
    const cells=new Map();
    for(const a of list){if(it.spot==='top'&&a.surf)continue;for(let i=0;i<it.w;i++)for(let k=0;k<it.h;k++)cells.set(cellKey(a.x+i,a.y+k),[a.x+i,a.y+k]);}
    const rects=[...cells.values()].map(([x,y])=>it.spot==='wall'?`<rect x="${A.PX+x*A.CW+2}" y="${G.WY+y*A.WR+2}" width="${A.CW-4}" height="${A.WR-4}" rx="6"/>`:`<rect x="${A.PX+x*A.CW+2}" y="${G.FY+y*A.FR+2}" width="${A.CW-4}" height="${A.FR-4}" rx="6"/>`).join('');
    const dots=list.filter(a=>a.surf).map(a=>`<circle cx="${A.PX+a.x*A.CW+A.CW/2}" cy="${G.FY+(a.y+1)*A.FR-6-a.surf-4}" r="7"/>`).join('');
    out.push(`<g class="dc-ok" pointer-events="none">${rects}${dots}</g>`);
  }
  out.push('<g class="dc-preview" pointer-events="none"></g>');
  const name=`${rm.name}: ${all.map(p=>ITEM(p.k)?.name).filter(Boolean).join(', ')||'chưa bày gì'}`;
  return {G,svg:`<svg class="dc-room${edit?' edit':''}${S.held?' holding':''}" viewBox="0 0 ${G.W} ${G.H}" role="group" aria-label="${esc(name)}" data-room="${esc(rm.id)}">${out.join('')}</svg>`};
}

/* ---- clicks ---- */
async function onClick(op,data){
  const v=V();
  switch(op){
    case'close':S.dlg.close();return;
    case'back':S.dlg.close();(await import('./house.js')).openHouse(S.env);return;
    case'tab':S.tab=data.tab;S.flash=null;S.held=null;S.sel='';render();return;
    case'room':S.room=data.room;S.sel='';render();return;
    case'edit':S.edit=true;S.flash=null;S.toTop=true;sfx('click');render();return;
    case'done':S.edit=false;S.held=null;S.sel='';S.flash=null;S.toTop=true;sfx('click');render();return;
    case'drawer':S.drawer=data.d;S.cat='';S.resetStrip=true;render();return;
    case'cat':S.cat=data.cat||'';S.resetStrip=true;render();return;
    case'hold':{const it=ITEM(data.k);if(!it)return;
      if(S.held&&S.held.k===data.k&&S.held.src===data.src){S.held=null;render();return;}
      S.held={k:data.k,src:data.src};S.sel='';sfx('pop');
      if(!it.rooms.includes(roomOf(S.room)?.type)){const r=roomsFor(it)[0];if(r)S.room=r.id;}
      render();return;}
    case'unhold':S.held=null;render();return;
    case'buyBag':{const it=heldItem();if(!it||S.held.src!=='shop')return;
      if(await ask(`Mua ${low(it.name)}?`,`Cất vào túi đồ, đặt lúc nào cũng được. Ấm cúng +${it.cozy} khi bày ra (mỗi loại tính một lần).`,`Mua · ${xu(it.price)}`,it.price)){
        const r=await send('jr_deco_buy',{item:it.id,confirm:true});if(r){sfx('coins');S.held={k:it.id,src:'bag'};render();}}return;}
    case'move':{const p=placed(data.uid);if(!p)return;S.held={k:p.k,src:'room',uid:p.id};S.sel='';sfx('pop');render();return;}
    case'flip':{const p=placed(data.uid);if(!p)return;await placeUid(p.id,p.r,p.x,p.y,p.f?0:1);return;}
    case'pick':return pick(data.uid);
    case'sell':{const p=placed(data.uid)||v.bag.find(b=>b.id===data.uid),it=ITEM(p?.k);if(!it)return;
      if(await S.env.confirmAction(`Bán lại ${low(it.name)}?`,`Nhận ${xu(it.sell)} (${CD().sell_pct}% giá mua).`,`Bán · ${xu(it.sell)}`)){
        const r=await send('jr_deco_sell',{uid:p.id,confirm:true});if(r){sfx('coins');S.sel='';S.undo=S.undo.filter(u=>!(p.id in u));render();}}return;}
    case'pickAll':{if(!v.items.length)return;
      if(await S.env.confirmAction('Cất hết đồ vào túi?','Mọi món đang bày ở chỗ này về túi đồ. Bấm Hoàn tác để bày lại như cũ.','Cất hết')){
        const prev=Object.fromEntries(v.items.map(p=>[p.id,[p.r,p.x,p.y,p.f]]));
        const r=await send('jr_deco_pick',{uid:'all'});if(r){pushUndo(prev);S.sel='';sfx('click');render();}}return;}
    case'undo':return undo();
    case'photo':return takePhoto();
    case'photoSave':{if(!S.photo)return;const career=S.env.api.state?.current||S.env.api.state?.focus;
      S.busy=true;paintBusy();
      try{const r=await S.env.api.command('photo',{image:S.photo.image,title:S.photo.title},career);S.flash={text:r.message,kind:'good'};S.photo.saved=true;sfx('chime');}
      catch(e){if(!e.quiet)S.flash={text:e.message||'Chưa lưu được ảnh.',kind:'bad'};}
      finally{S.busy=false;render();}return;}
    case'photoClose':S.photo=null;render();return;
    case'tipOk':tipDone();render();return;
    case'fix':{const r=R();const all=data.part==='all',p=r.parts.find(x=>x.id===data.part),cost=all?r.fix_all:p?.fix;if(!cost)return;
      const what=all?'Sửa cả nhà?':`Sửa ${low(PART(p.id).name)}?`,body=all?r.parts.filter(x=>x.fix).map(x=>`${PART(x.id).name} ${xu(x.fix)}`).join(' · '):`${condWord(p.c,p.id)} (${p.c}%) → như mới.`;
      if(await ask(what,body,`Sửa · ${xu(cost)}`,cost)){const res=await send('jr_reno_fix',{part:data.part,cost,confirm:true});if(res)sfx('success');}return;}
    case'up':{const r=R(),p=r.parts.find(x=>x.id===data.part);if(!p?.up)return;
      if(await ask(`${p.up.name}?`,`${PART(p.id).name} như mới, bền hơn. Ấm cúng +${CR().cozy_lv}.`,`Làm · ${xu(p.up.cost)}`,p.up.cost)){const res=await send('jr_reno_up',{part:p.id,lv:p.up.lv,cost:p.up.cost,confirm:true});if(res)sfx('success');}return;}
  }
}

function pushUndo(prev){S.undo.push(prev);if(S.undo.length>20)S.undo.shift();}
/** After a change: the pop-in, a chime when a set is done, Mochi's cheer when the level rises. */
function cheer(r,uid){
  if(uid)S.pop=uid;
  const set=/🎉/.test(r?.message||'');
  sfx(set?'chime':'pop');
}
async function placeUid(uid,room,x,y,f,again=''){
  const before=posOf(uid),prev={[uid]:before};
  for(const u of riders(uid))prev[u]=posOf(u);
  const r=await send('jr_deco_place',{uid,room,x,y,f});
  if(r&&!r.duplicate){
    pushUndo(prev);cheer(r,uid);
    // more of the same kind in the bag: keep holding it (three plants in a row)
    S.held=again&&V().bag.some(b=>b.k===again)?{k:again,src:'bag'}:null;S.sel=S.held?'':uid;
    render();
  }
  return r;
}
async function pick(uid){
  const p=placed(uid);if(!p)return;
  const prev={[uid]:[p.r,p.x,p.y,p.f]};for(const u of riders(uid))prev[u]=posOf(u);
  const r=await send('jr_deco_pick',{uid});
  if(r){pushUndo(prev);S.sel='';sfx('click');render();}
}
async function undo(){
  const last=S.undo.pop();if(!last){render();return;}
  const r=await send('jr_deco_layout',{set:last});
  if(r){sfx('pop');render();}
}
/** Put the held piece at spot `a` of the current room (buying it first from the shop). */
async function dropAt(a){
  const h=S.held,it=heldItem(),rm=roomOf(S.room);if(!h||!it||!rm||!a)return;
  if(h.src==='room'){const p=placed(h.uid);await placeUid(h.uid,rm.id,a.x,a.y,p?.f||0);return;}
  if(h.src==='bag'){const b=V().bag.find(x=>x.k===h.k);if(!b){S.held=null;render();return;}
    await placeUid(b.id,rm.id,a.x,a.y,0,h.k);return;}
  if(await ask(`Mua ${low(it.name)}?`,`Đặt ở ${low(rm.name)} · ấm cúng +${it.cozy} nếu chỗ này chưa có món này. Bán lại được ${CD().sell_pct}% giá.`,`Mua · ${xu(it.price)}`,it.price)){
    const r=await send('jr_deco_buy',{item:it.id,confirm:true,room:rm.id,x:a.x,y:a.y});
    if(r&&r.uid){if(!r.duplicate)pushUndo({[r.uid]:null});S.held=null;S.sel=r.uid;sfx('coins');cheer(r,r.uid);render();}
  }
}

/* ---- keyboard: arrows move the selected piece, F flips it, Delete puts it back in the bag ---- */
function onKey(e){
  const g=e.target.closest?.('g[data-uid]');
  if(g&&(e.key==='Enter'||e.key===' ')){e.preventDefault();if(!S.edit)S.edit=true;S.sel=S.sel===g.dataset.uid?'':g.dataset.uid;render();focusSel();return;}
  if(!S.edit||!S.sel||S.busy||!e.target.closest?.('svg.dc-room'))return;   // the keys belong to the room, not the drawer
  const p=placed(S.sel);if(!p)return;
  const d={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[e.key];
  if(d){e.preventDefault();placeUid(p.id,p.r,p.x+d[0],p.y+d[1],p.f).then(focusSel);return;}
  if(e.key==='f'||e.key==='F'){e.preventDefault();placeUid(p.id,p.r,p.x,p.y,p.f?0:1).then(focusSel);return;}
  if(e.key==='Delete'||e.key==='Backspace'){e.preventDefault();pick(p.id);}
}
const focusSel=()=>{if(S.sel)S.dlg?.querySelector(`g[data-uid="${CSS.escape(S.sel)}"]`)?.focus({preventScroll:true});};

/* ---- pointer: tap a lit cell, drag a piece in the room, drag a card up out of the drawer ---- */
function svgPoint(svg,cx,cy){const m=svg.getScreenCTM();if(!m)return null;const p=new DOMPoint(cx,cy).matrixTransform(m.inverse());return {x:p.x,y:p.y};}
const roomSvg=()=>S.dlg?.querySelector('svg.dc-room');
function onDown(e){
  if(S.busy||e.button>0)return;
  const svg=e.target.closest?.('svg.dc-room'),card=e.target.closest?.('.dc-card');
  if(svg){
    const g=e.target.closest('g[data-uid]');
    S.press={kind:'room',id:e.pointerId,x:e.clientX,y:e.clientY,uid:g?.dataset.uid||''};
    try{svg.setPointerCapture(e.pointerId);}catch{/* fine */}
  }else if(card&&S.edit&&!card.disabled){
    S.press={kind:'card',id:e.pointerId,x:e.clientX,y:e.clientY,k:card.dataset.k,src:card.dataset.src,el:card};
  }
}
function onMove(e){
  const p=S.press;if(!p||p.id!==e.pointerId)return;
  const dx=e.clientX-p.x,dy=e.clientY-p.y;
  if(!S.drag){
    if(p.kind==='room'){
      if(!S.edit||!p.uid||S.held&&S.held.uid!==p.uid||Math.hypot(dx,dy)<8)return;
      const q=placed(p.uid);if(!q)return;
      S.drag={kind:'room'};S.held={k:q.k,src:'room',uid:q.id};S.sel='';
    }else{
      if(Math.abs(dy)<12||Math.abs(dy)<Math.abs(dx)*1.2)return;   // sideways: the drawer scrolls
      const it=ITEM(p.k);if(!it)return;
      try{p.el.setPointerCapture(e.pointerId);}catch{/* fine */}
      S.drag={kind:'card'};S.held={k:p.k,src:p.src};S.sel='';
      if(!it.rooms.includes(roomOf(S.room)?.type)){const r=roomsFor(it)[0];if(r){S.room=r.id;render();}}
      floatGhost(it,e.clientX,e.clientY);
    }
    sfx('pop');paintRoom();
  }
  if(S.drag.kind==='card')floatGhost(heldItem(),e.clientX,e.clientY);
  preview(e.clientX,e.clientY);
}
function spotAt(cx,cy){
  const svg=roomSvg(),rm=roomOf(S.room),it=heldItem();if(!svg||!rm||!it)return null;
  const r=svg.getBoundingClientRect();if(cx<r.left-10||cx>r.right+10||cy<r.top-10||cy>r.bottom+10)return null;
  const pt=svgPoint(svg,cx,cy);if(!pt)return null;
  return snap(rm,it,anchors(rm,it,S.held.src==='room'?S.held.uid:''),pt.x,pt.y);
}
function preview(cx,cy){
  const svg=roomSvg(),g=svg?.querySelector('.dc-preview'),rm=roomOf(S.room),it=heldItem();if(!g||!rm||!it)return;
  const a=spotAt(cx,cy);
  if(!a){g.innerHTML='';S.drag&&(S.drag.at=null);return;}
  if(S.drag?.at&&S.drag.at.x===a.x&&S.drag.at.y===a.y)return;
  if(S.drag)S.drag.at=a;
  const G=A.geom(rm),f=S.held.src==='room'?(placed(S.held.uid)?.f||0):0;
  const [bx,by,bw,bh]=bbox(it,a,G,a.surf);
  g.innerHTML=`<rect class="dc-hot" x="${bx-3}" y="${by-3}" width="${bw+6}" height="${bh+6}" rx="9"/><g opacity=".75">${A.pieceSVG(it,a.x,a.y,f,G,a.surf)}</g>`;
}
async function onUp(e){
  const p=S.press;if(!p||p.id!==e.pointerId)return;
  S.press=null;
  if(S.drag){
    const a=spotAt(e.clientX,e.clientY),kind=S.drag.kind;
    S.drag=null;S.dragEnd=Date.now();floatGhost(null);
    if(a){await dropAt(a);return;}
    if(kind==='room'){S.held=null;S.flash={text:'Chỗ này không đặt được. Thả vào ô sáng màu nhé.',kind:'warn'};sfx('error');}
    render();return;
  }
  if(p.kind!=='room')return;   // a card: its click event holds it
  const svg=roomSvg();if(!svg)return;
  if(!S.edit){S.edit=true;S.sel=p.uid;sfx('click');render();return;}
  if(S.held){
    const a=spotAt(e.clientX,e.clientY);
    if(a){await dropAt(a);return;}
    if(p.uid&&p.uid!==S.held.uid&&S.held.src==='room'){S.held=null;S.sel=p.uid;render();return;}
    S.flash={text:'Chỗ này không đặt được. Chạm vào ô sáng màu nhé.',kind:'warn'};sfx('error');render();return;
  }
  if(p.uid){S.sel=S.sel===p.uid?'':p.uid;sfx('click');render();return;}
  if(S.sel){S.sel='';render();}
}
function onCancel(e){
  if(S.press?.id!==e.pointerId)return;
  const card=S.press.kind==='card'&&!S.drag;S.press=null;
  if(card)return;   // the drawer took the swipe
  if(S.drag){S.drag=null;S.held=null;floatGhost(null);render();}
}
function floatGhost(it,cx,cy){
  let el=S.dlg?.querySelector('.dc-float');
  if(!it){el?.remove();return;}
  if(!el){el=document.createElement('div');el.className='dc-float';el.setAttribute('aria-hidden','true');el.innerHTML=A.thumb(it,64);S.dlg.append(el);}
  const r=S.dlg.getBoundingClientRect(),inside=getComputedStyle(S.dlg).transform!=='none';
  el.style.left=`${cx-(inside?r.left:0)-32}px`;el.style.top=`${cy-(inside?r.top:0)-72}px`;
}

/* ---- the photo: the room in a polaroid, drawn to a canvas ---- */
async function takePhoto(){
  const v=V(),rm=roomOf(S.room);if(!v||!rm)return;
  const {G,svg}=roomMarkup(rm,{photo:true});
  const pad=14,cap=54,W=G.W+pad*2,H=G.H+pad+cap;
  const inner=svg.replace(/^<svg[^>]*>/,'').replace(/<\/svg>$/,'');
  const title=`${v.place.name} · ${rm.name}`.slice(0,60),day=J().life_day;
  const src=`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><rect width="${W}" height="${H}" rx="10" fill="#fffdf7"/>`
    +`<svg x="${pad}" y="${pad}" width="${G.W}" height="${G.H}" viewBox="0 0 ${G.W} ${G.H}">${inner}</svg><rect x="${pad}" y="${pad}" width="${G.W}" height="${G.H}" fill="none" stroke="#e8dcc8"/>`
    +`<text x="${pad+2}" y="${G.H+pad+26}" font-family="system-ui,sans-serif" font-size="15" font-weight="700" fill="#5b4535">${esc(title)}</text>`
    +`<text x="${pad+2}" y="${G.H+pad+44}" font-family="system-ui,sans-serif" font-size="12" fill="#a08a74">Ngày ${day} · Ấm cúng ${v.cozy.total}</text>`
    +`<g transform="translate(${W-pad-46} ${G.H+pad-34}) scale(.62)">${A.mascot(levelIdx(v.cozy.total),64).replace(/^<svg[^>]*>/,'').replace(/<\/svg>$/,'')}</g></svg>`;
  S.busy=true;paintBusy();
  try{
    const url=URL.createObjectURL(new Blob([src],{type:'image/svg+xml'}));
    const img=new Image();img.decoding='async';
    await new Promise((ok,bad)=>{img.onload=ok;img.onerror=bad;img.src=url;});
    let scale=2,image='';
    for(const q of [.86,.72,.55]){
      const c=document.createElement('canvas');c.width=Math.round(W*scale);c.height=Math.round(H*scale);
      const x=c.getContext('2d');x.drawImage(img,0,0,c.width,c.height);
      image=c.toDataURL('image/webp',q);if(!image.startsWith('data:image/webp'))image=c.toDataURL('image/png');
      if(image.length<=440000)break;scale=1.5;
    }
    URL.revokeObjectURL(url);
    if(image.length>440000)throw new Error('big');
    S.photo={image,title,saved:false};sfx('chime');
  }catch{S.flash={text:'Máy chưa chụp được ảnh. Thử lại nhé.',kind:'bad'};}
  finally{S.busy=false;render();}
}

/* ---- rendering ---- */
const levelIdx=total=>{const ls=[...(CD().levels||[])].sort((a,b)=>a.min-b.min);let i=-1;for(const l of ls)if(total>=l.min)i++;return Math.max(0,Math.min(4,i));};
function paintBusy(){S.dlg?.setAttribute('aria-busy',String(S.busy));S.dlg?.querySelectorAll('[data-dc]').forEach(b=>{if(b.tagName==='BUTTON')b.disabled=S.busy;});}
function paintRoom(){
  const old=roomSvg(),rm=roomOf(S.room);if(!old||!rm)return;
  const {svg}=roomMarkup(rm,{edit:S.edit}),t=document.createElement('div');t.innerHTML=svg;
  const neu=t.firstChild;
  // keep the element (it holds the pointer capture), swap its insides
  old.innerHTML=neu.innerHTML;old.setAttribute('class',neu.getAttribute('class'));
}
function render(){
  if(!S.dlg)return;
  const body=S.dlg.querySelector('.dc-body'),top=body?.scrollTop,strip=S.dlg.querySelector('.dc-strip'),left=strip?.scrollLeft;
  const v=V();
  if(v&&S.undoKey!==v.place.key){S.undoKey=v.place.key;S.undo=[];}
  if(v){const lv=levelIdx(v.cozy.total);S.cheer=S.lastLv>=0&&lv>S.lastLv;S.lastLv=lv;}
  S.dlg.querySelector('.dc-root').innerHTML=page();
  const b2=S.dlg.querySelector('.dc-body');if(b2&&top!=null)b2.scrollTop=S.toTop?0:top;
  if(S.toTop)S.dlg.scrollTop=0;
  const s2=S.dlg.querySelector('.dc-strip');if(s2&&left!=null&&!S.resetStrip)s2.scrollLeft=left;
  S.dlg.setAttribute('aria-busy',String(S.busy));
  S.pop='';S.resetStrip=false;S.toTop=false;
}
function head(v){
  const pl=v?.place;
  return `<header class="sheet-head bk-head rn-head"><button class="icon-btn" type="button" data-dc="back" aria-label="Về Nhà của bạn">${icon('back',21)}</button>
    <div class="grow"><span class="eyebrow">${pl?.repairs?'TRONG NHÀ':'BÀY TRÍ PHÒNG'}</span><h2 id="dc-title">${pl?`${pl.emoji} ${esc(pl.name)}`:'Nhà của bạn'}</h2></div>
    <button class="icon-btn" type="button" data-dc="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
}
const flash=()=>`<p class="bk-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
function page(){
  const v=V();
  if(!v)return head(v)+`<div class="sheet-body bk dc-body"><section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🪴</div><h3>Chưa có chỗ để bày trí</h3><p>Bày trí phòng có trong chế độ hành trình.</p>${btn('🏠 Nhà của bạn','back',{},'primary')}</section></div>`;
  if(!v.rooms.some(r=>r.id===S.room))S.room=v.rooms[0]?.id||'';
  const r=R(),own=v.place.repairs&&r;
  if(!own)S.tab='deco';
  const worn=own&&r.parts.some(p=>p.worn);
  const tabs=own?`<div class="segmented bk-tabs rn-tabs" role="tablist" aria-label="Trong nhà">${[['deco','🪴 Bày trí'],['fix',`🛠️ Sửa nhà${worn?'<i class="dot" aria-hidden="true"></i>':''}`]].map(([id,l])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" class="${S.tab===id?'active':''}" data-dc="tab" data-tab="${id}">${l}</button>`).join('')}</div>`:'';
  const main=S.tab==='fix'?`<div class="dc-fix">${condCard(r)}${fixPanel(r)}</div>`:decoPage(v);
  return head(v)+`<div class="sheet-body bk dc-body">${tabs}${flash()}${main}</div>${S.photo?photoView():''}`;
}
function decoPage(v){
  const rm=roomOf(S.room);if(!rm)return '';
  const {svg}=roomMarkup(rm,{edit:S.edit});
  const tip=S.edit&&!tipSeen()?`<div class="dc-tip" role="note"><span aria-hidden="true">👆</span><p><b>Chạm một món trong túi rồi chạm chỗ trống để đặt</b><small>Kéo món đồ trong phòng để dời chỗ.</small></p>${btn('Hiểu rồi','tipOk',{},'ghost small')}</div>`:'';
  const bar=S.edit
    ?`<div class="dc-bar">${btn('↶ Hoàn tác','undo',{},'ghost',S.undo.length?'':' disabled')}${btn('🎒 Cất hết','pickAll',{},'ghost',v.items.length?'':' disabled')}${btn('✓ Xong','done',{},'primary')}</div>`
    :`<div class="dc-bar">${btn(v.items.length?'✏️ Bày trí phòng':'✏️ Bắt đầu bày trí','edit',{},'primary')}${btn('📸 Chụp phòng','photo',{},'ghost')}</div>`;
  const stage=`<div class="dc-stage">${roomTabs(v)}<div class="dc-roomwrap">${svg}${S.edit?'':'<span class="dc-hint" aria-hidden="true">Chạm phòng để bày trí</span>'}</div>${S.edit?(S.held?heldBar(v):S.sel?tools(v):''):''}${tip}${bar}${S.edit?drawer(v):''}</div>`;
  return `<div class="dc-grid">${stage}<div class="dc-side">${cozyCard(v)}${guestCard(v)}${setsCard(v)}${placeNote(v)}</div></div>`;
}
function roomTabs(v){
  if(v.rooms.length<2)return '';
  const it=heldItem(),n=id=>v.items.filter(i=>i.r===id).length;
  return `<div class="rn-rooms dc-rooms" role="tablist" aria-label="Các phòng">${v.rooms.map(r=>{const ok=it&&it.rooms.includes(r.type);
    return `<button type="button" role="tab" aria-selected="${S.room===r.id}" class="rn-room${S.room===r.id?' active':''}${ok?' ok':''}" data-dc="room" data-room="${r.id}"><span aria-hidden="true">${r.emoji}</span>${esc(r.name)}${n(r.id)?`<small>${n(r.id)}</small>`:''}</button>`;}).join('')}</div>`;
}
function heldBar(v){
  const it=heldItem(),rm=roomOf(S.room);if(!it)return '';
  const here=rm&&it.rooms.includes(rm.type),list=here?anchors(rm,it,S.held.src==='room'?S.held.uid:''):[];
  const where=roomsFor(it).map(r=>low(r.name));
  const hint=!where.length?esc('Món này không hợp chỗ ở này.'):!here?`Món này đặt ở ${where.map(w=>`<i>${esc(w)}</i>`).join(', ')}.`:esc(!list.length?'Phòng này hết chỗ cho món này rồi.':S.held.src==='room'?'Chạm ô sáng màu để dời tới đó.':'Chạm ô sáng màu để đặt.');
  const sub=S.held.src==='shop'?`${xu(it.price)} · ấm cúng +${it.cozy}`:S.held.src==='bag'?`Trong túi · ấm cúng +${it.cozy}`:'Đang dời';
  return `<div class="dc-held" role="status">${A.thumb(it,40)}<p><b>${esc(it.name)}</b><small>${esc(sub)}</small><small class="dc-held-hint">${hint}</small></p>
    <span class="dc-held-go">${S.held.src==='shop'?btn('🎒 Mua cất túi','buyBag',{},'ghost small',it.price>v.ready?' disabled':''):''}${btn('Thôi','unhold',{},'ghost small')}</span></div>`;
}
function tools(v){
  const p=placed(S.sel),it=ITEM(p?.k);if(!it)return '';
  return `<div class="dc-tools" role="toolbar" aria-label="${esc(it.name)}">${A.thumb(it,36)}<b>${esc(it.name)}</b>
    ${btn('↔ Dời','move',{uid:p.id},'ghost small')}${btn('⇋ Lật','flip',{uid:p.id},'ghost small')}${btn('🎒 Thu hồi','pick',{uid:p.id},'ghost small')}${btn(`💰 Bán lại · ${xu(it.sell)}`,'sell',{uid:p.id},'ghost small danger')}</div>`;
}
function drawer(v){
  const C=CD(),types=new Set(v.rooms.map(r=>r.type)),rm=roomOf(S.room);
  const fits=it=>it.rooms.some(t=>types.has(t)),here=it=>rm&&it.rooms.includes(rm.type);
  let cards='',cats=new Set();
  if(S.drawer==='bag'){
    const groups=new Map();for(const b of v.bag){if(!groups.has(b.k))groups.set(b.k,[]);groups.get(b.k).push(b.id);}
    const list=[...groups.entries()].map(([k,ids])=>({it:ITEM(k),n:ids.length})).filter(x=>x.it);
    list.forEach(x=>cats.add(x.it.cat));
    const shown=list.filter(x=>!S.cat||x.it.cat===S.cat).sort((a,b)=>(here(b.it)-here(a.it))||(fits(b.it)-fits(a.it))||a.it.name.localeCompare(b.it.name,'vi'));
    cards=shown.map(({it,n})=>card(it,'bag',`${n>1?`<i class="dc-n">×${n}</i>`:''}`,fits(it)?`Ấm cúng +${it.cozy}`:'Không hợp chỗ này',!fits(it))).join('');
    if(!list.length)cards=`<div class="dc-empty"><p>Túi đồ trống. Ghé cửa hàng chọn món đầu tiên nhé!</p>${btn('🛒 Cửa hàng','drawer',{d:'shop'},'primary small')}</div>`;
  }else{
    const have=new Set([...v.items.map(i=>i.k),...v.bag.map(b=>b.k)]);
    const list=C.items.filter(fits);list.forEach(it=>cats.add(it.cat));
    const shown=list.filter(it=>!S.cat||it.cat===S.cat).sort((a,b)=>(here(b)-here(a))||a.price-b.price);
    cards=shown.map(it=>card(it,'shop',have.has(it.id)?'<i class="dc-have">Đã có</i>':'',`${xu(it.price)} · +${it.cozy}`,false,it.price>v.ready)).join('');
  }
  const chips=[['','Tất cả'],...C.cats.filter(c=>cats.has(c.id)).map(c=>[c.id,`${c.emoji} ${c.name}`])];
  return `<section class="dc-drawer" aria-label="Đồ đạc">
    <div class="dc-drawer-top"><div class="segmented dc-seg" role="tablist">${[['bag',`🎒 Túi đồ · ${v.bag.length}`],['shop','🛒 Cửa hàng']].map(([id,l])=>`<button type="button" role="tab" aria-selected="${S.drawer===id}" class="${S.drawer===id?'active':''}" data-dc="drawer" data-d="${id}">${l}</button>`).join('')}</div>
    <span class="dc-money" title="Tài khoản + ví">💰 ${xu(v.ready)}</span></div>
    ${chips.length>2?`<div class="dc-cats">${chips.map(([id,l])=>`<button type="button" class="dc-chip${S.cat===id?' on':''}" data-dc="cat" data-cat="${id}" aria-pressed="${S.cat===id}">${l}</button>`).join('')}</div>`:''}
    <div class="dc-strip" role="list">${cards}</div></section>`;
}
function card(it,src,badge,sub,off=false,poor=false){
  const on=S.held&&S.held.k===it.id&&S.held.src===src;
  return `<button type="button" role="listitem" class="dc-card${on?' on':''}${off?' off':''}${poor?' poor':''}" data-dc="hold" data-k="${it.id}" data-src="${src}"${S.busy||off?' disabled':''} aria-pressed="${!!on}">
    <span class="dc-card-pic">${A.thumb(it,58)}</span>${badge}<b>${esc(it.name)}</b><small>${esc(sub)}</small></button>`;
}
function cozyCard(v){
  const c=v.cozy,lv=levelIdx(c.total),C=CD(),own=v.place.where==='own';
  const marks=(C.levels||[]).filter(l=>l.min>0&&l.min<=MAXC).map(l=>`<b style="left:${l.min/MAXC*100}%" title="${esc(l.name)}"></b>`).join('');
  let perk='';
  if(own){
    if(c.perk&&!c.off)perk=`<p class="rn-perk on">😊 +${c.perk} tinh thần mỗi sáng</p>`;
    else if(c.perk&&c.off==='late')perk=`<p class="rn-perk">😊 +${c.perk} tinh thần tạm dừng khi trễ hạn trả góp</p>`;
    else if(c.perk)perk=`<p class="rn-perk">🛠️ Sửa nhà tới ${CR().cozy_cond}% để có +${c.perk} tinh thần mỗi sáng</p>`;
  }else if(c.perk)perk=`<p class="rn-perk on">😊 +${c.perk} tinh thần mỗi sáng</p>`;
  const next=c.next?`<p class="bk-hint">Thêm ${c.next.min-c.total} điểm: +${c.next.spirit} tinh thần mỗi sáng.</p>`:'';
  const steps=[...(c.steps||[])].sort((a,b)=>a.min-b.min).map(s=>`+${s.spirit} từ ${s.min} điểm`).join(', ');
  const why=[`Mỗi loại đồ tính điểm một lần, món trùng không cộng thêm.`,`Bày đủ một bộ góc trong cùng một phòng được cộng thêm.`,
    own?`Mỗi nâng cấp nhà: ấm cúng +${CR().cozy_lv}.`:'',
    own?`Tinh thần mỗi sáng: ${steps} (nhà sửa tới ${CR().cozy_cond}%, không trễ hạn trả góp).`:`Chỗ ở thuê hoặc ở nhờ: tinh thần ${steps}, tối đa +${Math.max(1,...(c.steps||[]).map(s=>s.spirit))} mỗi sáng.`,
    `Ấm cúng từ ${C.guest_min} điểm thì hàng xóm hay ghé chơi khen phòng.`].filter(Boolean);
  const guest=`<details class="dc-why"><summary>Điểm tính thế nào?</summary><ul>${why.map(t=>`<li>${esc(t)}</li>`).join('')}</ul></details>`;
  return `<section class="bk-card dc-cozy${S.cheer?' cheer':''}"><div class="dc-cozy-top"><span class="dc-mochi-wrap">${A.mascot(lv,68)}</span><div class="grow"><small>Ấm cúng</small><b><span class="dc-num">${c.total}</span> ${esc(c.level)}</b><p class="dc-say">${esc(SAY[lv])}</p></div></div>
    <div class="dc-meter" role="meter" aria-label="Ấm cúng" aria-valuemin="0" aria-valuemax="${MAXC}" aria-valuenow="${Math.min(MAXC,c.total)}"><i style="width:${Math.min(100,c.total/MAXC*100)}%"></i>${marks}</div>
    <p class="dc-break"><span>Đồ đạc ${c.items}</span><span>Bộ góc ${c.sets}</span>${own?`<span>Nâng cấp nhà ${c.up}</span>`:''}</p>
    ${perk}${next}${guest}</section>`;
}
function guestCard(v){
  const g=v.guest;if(!g)return '';
  return `<section class="bk-card dc-guest"><span class="dc-guest-face" aria-hidden="true">${g.emoji}</span><p><b>${esc(g.name)} ghé chơi hôm nay</b><span>${esc(g.text)}</span></p></section>`;
}
function setsCard(v){
  const C=CD(),meta=Object.fromEntries((C.sets||[]).map(s=>[s.id,s])),rooms=Object.fromEntries(v.rooms.map(r=>[r.id,r.name]));
  const list=[...v.sets].sort((a,b)=>(b.done-a.done)||(b.have/b.need-a.have/a.need));
  if(!list.length)return '';
  const row=s=>{const m=meta[s.id]||{};
    return `<li class="${s.done?'done':''}"><span class="dc-set-ico" aria-hidden="true">${m.emoji||'✨'}</span><div class="grow"><b>${esc(m.name||s.id)}</b>
      <small>${s.done?`Hoàn thành${v.rooms.length>1&&rooms[s.room]?` · ${esc(rooms[s.room])}`:''}`:`${s.have}/${s.need} · còn thiếu ${missList(s.miss)}`}</small></div><em>+${m.bonus||0}</em></li>`;};
  const done=list.filter(s=>s.done).length,show=Math.max(done+3,4),more=list.slice(show);
  return `<section class="bk-card dc-sets-card"><h3>🏅 Bộ góc xinh · ${done}/${list.length}</h3><ul class="dc-sets">${list.slice(0,show).map(row).join('')}</ul>
    ${more.length?`<details class="dc-more"><summary>Xem thêm ${more.length} bộ góc</summary><ul class="dc-sets">${more.map(row).join('')}</ul></details>`:''}</section>`;
}
/** "một chậu cây ×2, kệ sách": each wish in its own element (the English layer translates them one by one). */
const missList=list=>list.map(w=>{const m=String(w).match(/^(.*) ×(\d+)$/);return m?`<i>${esc(m[1])}</i> ×${m[2]}`:`<i>${esc(w)}</i>`;}).join(', ');
function placeNote(v){
  const st=v.stats||{},pl=v.place;
  const note=pl.repairs?'':pl.where==='shared'?'💞 Nhà chung: bày trí thoải mái, chuyện sửa nhà để người đứng tên lo.':'🧾 Chỗ ở thuê: chỉ bày đồ trang trí, không sửa nhà được.';
  return `<section class="bk-card dc-note">${note?`<p>${note}</p>`:''}<p class="bk-hint">Dọn đi đâu, đồ đạc cũng tự gói vào túi đồ. Mua một lần, mang theo cả hành trình.</p>
    <p class="dc-stats"><span>🎒 ${v.count}/${v.max} món</span><span>📌 Đã đặt ${st.placed||0} lần</span><span>☕ ${st.guests||0} lượt khách ghé</span></p></section>`;
}
function photoView(){
  const p=S.photo,can=!!(S.env.api.state?.current||S.env.api.state?.focus);
  return `<div class="dc-photo" role="dialog" aria-label="Ảnh chụp phòng"><div class="dc-photo-card"><figure><img src="${p.image}" alt="${esc(p.title)}"></figure>
    <div class="bk-actions">${can&&!p.saved?btn('💾 Lưu vào album','photoSave',{},'primary'):''}<a class="btn ghost" href="${p.image}" download="phong-cua-toi.webp">⬇️ Tải ảnh về</a>${btn('Đóng','photoClose',{},'ghost')}</div>
    ${can?'<p class="bk-hint">Album giữ sáu ảnh gần nhất của nghề đang làm.</p>':''}</div></div>`;
}

/* ---- 🛠️ Sửa nhà (a home you own) ---- */
function condCard(r){
  const worn=r.parts.filter(p=>p.worn);
  return `<section class="bk-card"><h3>Tình trạng nhà · ${r.cond}%</h3><div class="bk-bar ${tone(r.cond)}" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${r.cond}" aria-label="Tình trạng nhà"><i style="width:${r.cond}%"></i></div>
    ${worn.length?`<ul class="rn-flaws">${worn.map(p=>`<li>${PART(p.id).emoji} ${esc(PART(p.id).flaw)}</li>`).join('')}</ul>`:'<p class="bk-hint">Nhà sạch đẹp.</p>'}
    <dl class="hs-facts rn-facts"><div><dt>Đồ đạc</dt><dd>${r.count} món</dd></div><div><dt>Đã chi cho nhà</dt><dd>${xu(r.spent)}</dd></div></dl></section>`;
}
function fixPanel(r){
  const need=r.parts.filter(p=>p.fix),ready=r.ready;
  const short=n=>n>ready?' disabled':'';
  const all=need.length>1?`<div class="bk-actions rn-fixall">${btn(`🛠️ Sửa hết · ${xu(r.fix_all)}`,'fix',{part:'all'},'primary',short(r.fix_all))}</div>`:'';
  const rows=r.parts.map(p=>{const m=PART(p.id);
    return `<li class="rn-part ${tone(p.c)}"><div class="rn-part-top"><span class="rn-part-ico" aria-hidden="true">${m.emoji}</span><div class="grow"><b>${esc(m.name)}</b><small>${esc(condWord(p.c,p.id))} · ${p.c}%</small></div><span class="rn-lv" aria-label="Nâng cấp ${p.lv}/2">${'★'.repeat(p.lv)}${'☆'.repeat(2-p.lv)}</span></div>
      <div class="bk-bar ${tone(p.c)}" aria-hidden="true"><i style="width:${p.c}%"></i></div>
      <div class="rn-part-go">${p.fix?btn(`Sửa · ${xu(p.fix)}`,'fix',{part:p.id},'ghost',short(p.fix)):''}${p.up?btn(`⬆ ${esc(p.up.name)} · ${xu(p.up.cost)}`,'up',{part:p.id},'ghost',short(p.up.cost)):'<span class="rn-max">Đã nâng cấp hết</span>'}</div></li>`;}).join('');
  return `<section class="bk-card"><h3>Sửa nhà</h3><p class="bk-hint">Có ${xu(ready)} (tài khoản + ví). Mỗi nâng cấp: ấm cúng +${CR().cozy_lv}.</p>${all}<ul class="rn-parts">${rows}</ul></section>`;
}
