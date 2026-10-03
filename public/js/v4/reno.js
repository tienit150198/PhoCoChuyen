/** 🪴 Bày trí phòng (+ 🛠️ Sửa nhà for a home you own): wherever the player lives (gác Bà Tám, phòng trọ, the dorm's
 * bunk corner, a shared home, a home they own). Every rule lives in game/deco.py (layout, coziness, sets, guests) and
 * game/reno.py (repairs); this file draws api.state.journey.deco with v4/deco-art.js and sends `jr_deco_*` /
 * `jr_reno_fix|up`. The checks below only colour the live preview: the server decides.
 * Edit mode (since 1.4, free placement): press a piece and drag it anywhere in its zone (the floor, the wall); small
 * things snap onto tables, beds, shelves and the kitchen counter and travel with them. Drag a card up out of the
 * drawer into the room, or tap a card then tap the room. Tap a piece for its tools (flip, up/down, another room, put
 * away, sell). Undo keeps the last moves (jr_deco_layout). 🎨 Tường & sàn: wallpaper and floor per room. The cats
 * wander and nap (cosmetic; still with reduced motion). The light follows the hour of the day.
 * Pointer moves only move a transform (no re-render); a drop sends one jr_deco_put.
 * Opened from 🏠 Nhà của bạn (v4/house.js); the back button returns there. Styles: bank.css + house.css + reno.css.
 * 🎨 Màu (bảng màu): a selected piece opens the palette picker (v4/palette.js); its colour is state.colors.deco[uid]
 * (jr_wd_deco), kept by the piece in the bag and in the next home; drawn wherever the piece is (room, photo, a table).
 * 💞 A home shared with the spouse: their pieces come from GET /api/deco/mate (game/deco_mate.py) and are drawn with
 * these (room and photo), read-only: never selected or dragged, not in the bag, not in Ấm cúng, Cất hết or undo. */
import {icon,escapeHTML as esc} from '../icons.js';
import {Sound} from '../audio.js';
import * as A from './deco-art.js';

const S={dlg:null,env:null,tab:'deco',room:'',edit:false,held:null,sel:'',drawer:'bag',cat:'',busy:false,flash:null,
  undo:[],undoKey:'',press:null,drag:null,dragEnd:0,resetStrip:false,toTop:false,pop:'',cheer:false,photo:null,listening:false,lastLv:-1,
  try:null,nudge:null,tryTint:null,mate:null,mateKey:''};
const U=A.U;
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const low=s=>String(s||'').slice(0,1).toLowerCase()+String(s||'').slice(1);
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,op,data={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-dc="${op}"${attrs(data)}${S.busy?' disabled':''}${extra}>${label}</button>`;
const J=()=>S.env?.api?.state?.journey||{};
/* The place you live in, its rooms and pieces (deco.public). 1.4.11: the new rooms (the bathroom, a villa's pool) come
 * as `more` [{t: template, s: skin}] with the templates in the catalogue (`kits`); here they join `rooms`. */
let vSrc=null,vOut=null;
const V=()=>{const d=J().deco||null;if(!d?.more?.length)return d;
  if(vSrc!==d){const kits=CD().kits||{};vSrc=d;vOut={...d,rooms:[...d.rooms,...d.more.filter(m=>kits[m.t]).map(m=>({...kits[m.t],skin:m.s||{}}))]};}
  return vOut;};
const R=()=>J().reno||null;                       // the structure of a home you own (reno.public)
const CD=()=>S.env?.api?.content?.journey?.deco||{items:[],cats:[],sets:[],levels:[],skins:[]};
const CR=()=>S.env?.api?.content?.journey?.reno||{parts:[],steps:[]};
let itemMap=null,itemSrc=null;
const ITEM=k=>{const list=CD().items;if(itemSrc!==list){itemSrc=list;itemMap=new Map(list.map(i=>[i.id,i]));}return itemMap.get(k);};
const SKIN=id=>(CD().skins||[]).find(s=>s.id===id)||null;
const PART=id=>CR().parts.find(x=>x.id===id)||{};
/** A piece's colour: the one being tried in the picker, else its own from the palette (state.colors.deco). */
const tintOf=uid=>S.tryTint?.uid===uid?S.tryTint.c:S.env?.api?.state?.colors?.deco?.[uid]||null;
const POCKET=['account','wallet'];
const condWord=(c,p)=>c>=85?'Như mới':c>=65?'Còn tốt':c>=45?'Hơi cũ':(PART(p).flaw||'Xuống cấp');
const tone=c=>c>=65?'good':c>=45?'warn':'bad';
const MAXC=40;                                    // the meter's end: Tổ ấm trong mơ
const SAY=['Phòng hơi trống… Mochi buồn ngủ quá.','Bắt đầu dễ thương rồi nè!','Ấm áp ghê, Mochi thích lắm!','Wow, phòng xinh quá trời!','Tổ ấm trong mơ! Mochi không muốn đi đâu hết.'];
const TIP_KEY='mnl.decoTip2';
const tipSeen=()=>{try{return localStorage.getItem(TIP_KEY)==='1';}catch{return false;}};
const tipDone=()=>{try{localStorage.setItem(TIP_KEY,'1');}catch{/* private window: the tip just shows again */}};
const calm=()=>document.body.classList.contains('reduce-motion')||!!globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const nonce=()=>(globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`).replace(/[^A-Za-z0-9_-]/g,'').slice(0,32);

/* ---- sounds (settings: sound, detailSfx) ---- */
let snd=null;
function sfx(name){
  const st=S.env?.api?.state?.settings||{};if(st.sound===false)return;
  try{snd??=new Sound();snd.configure(st);snd[name]?.();}catch{/* silent */}
}
const buzz=ms=>{try{if(!calm())navigator.vibrate?.(ms);}catch{/* no vibration here */}};

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
  d.addEventListener('close',()=>{S.flash=null;S.held=null;S.sel='';S.photo=null;S.drag=null;S.press=null;S.try=null;floatGhost(null);catsStop();});
  S.dlg=d;return d;
}

export async function openReno(env,mode){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';
    env.api.addEventListener('state',()=>{const j=S.env.api.state?.journey;const key=JSON.stringify([j?.deco,j?.reno,j?.wallet,S.env.api.state?.colors?.deco]);if(key===seen)return;seen=key;
      if(S.dlg?.open&&(V()?.place?.key||'')!==S.mateKey)loadMate();
      if(S.dlg?.open&&!S.busy&&!S.drag&&!S.press)render();});
  }
  await ensureCss();
  const d=dialog();
  S.tab=mode==='fix'&&R()?'fix':'deco';S.edit=mode==='decor';S.held=null;S.sel='';S.flash=null;S.photo=null;S.cat='';S.try=null;
  const v=V();
  if(v){if(!v.rooms.some(r=>r.id===S.room))S.room=v.rooms[0]?.id||'';S.drawer=v.bag.length?'bag':'shop';}
  if(!d.open){d.showModal();d.scrollTop=0;S.toTop=true;}
  loadMate();   // its first lines run now: a room that is not shared any more drops the spouse's pieces before drawing
  render();
}
/** 💞 The spouse's pieces when this is the home both live in (each time the room opens, and after a move). */
async function loadMate(){
  const v=V(),key=v?.place?.key||'';S.mateKey=key;
  if(!v||!['own','shared'].includes(v.place.where)||S.env.api.state?.marriage?.spouse?.status!=='married'){S.mate=null;return;}
  let m=null;
  try{m=await S.env.api.json('/api/deco/mate');}catch{/* a home never blocks the room: just our own pieces */}
  if(S.mateKey!==key)return;   // moved meanwhile: the newer request decides
  const had=!!S.mate;S.mate=m&&m.at===key&&Array.isArray(m.items)&&m.items.length?m:null;
  if((had||S.mate)&&S.dlg?.open&&!S.busy&&!S.drag&&!S.press)render();
}

async function send(action,payload={},opts={}){
  const {api}=S.env;S.busy=true;paintBusy();
  try{
    const r=await api.command(action,payload);
    S.flash=r.duplicate&&!opts.loud?S.flash:{text:[r.message,...(r.effects||[]).filter(Boolean)].filter(Boolean).join(' '),kind:'good'};
    return r;
  }catch(e){
    if(!e.quiet){S.flash={text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};if(!opts.silent)sfx('error');}
    return null;
  }finally{S.busy=false;render();}
}
const ask=(title,msg,label,cost)=>S.env.confirmAction(title,msg,label,cost?{cost,pocket:POCKET}:undefined);

/* ---- the layout, as the client sees it (free units; game/deco.py check) ---- */
const roomOf=id=>(V()?.rooms||[]).find(r=>r.id===id)||null;
const items=()=>V()?.items||[];
const placed=uid=>items().find(i=>i.id===uid)||null;
/** A placed piece as the server keeps it: {r, x, y, f[, on][, z]} in units. */
function qOf(p){const q={r:p.r,x:p.fx??p.x*U,y:p.fy??p.y*U,f:p.f||0};if(p.on)q.on=p.on;if(p.z)q.z=p.z;return q;}
const sameQ=(a,b)=>!!a&&!!b&&a.r===b.r&&a.x===b.x&&a.y===b.y&&(a.f||0)===(b.f||0)&&(a.on||'')===(b.on||'')&&(a.z||0)===(b.z||0);
/** Everything in room `rm` as {id, k, it, q}, without `skip`. */
function inRoom(rm,skip=new Set()){return items().filter(p=>p.r===rm.id&&!skip.has(p.id)&&ITEM(p.k)).map(p=>({id:p.id,k:p.k,it:ITEM(p.k),q:qOf(p)}));}
const ridersOf=uid=>items().filter(p=>p.on===uid).map(p=>p.id);
/** 💞 The spouse's pieces in this home (ids 'p:…'), read-only: drawn, never part of the checks above. */
const mates=()=>S.mate&&S.mate.at===V()?.place?.key?S.mate.items:[];
function mateIn(rm){return mates().filter(p=>p.r===rm.id&&ITEM(p.k)).map(p=>({id:p.id,k:p.k,it:ITEM(p.k),q:qOf(p),mate:true,c:p.c||null}));}
/** What `q` stands on: {it, q} (a placed piece) or {fix} (a fixture), or null. */
function hostFor(rm,q,list){
  if(!q.on)return null;
  if(q.on[0]==='#'){const f=rm.fix.find(f=>f.t===q.on.slice(1));return f?{fix:f}:null;}
  const h=list.find(o=>o.id===q.on);return h?{it:h.it,q:h.q}:null;
}
function hostBox(rm,on,list){
  if(on[0]==='#'){const f=rm.fix.find(f=>f.t===on.slice(1)&&(f.top||f.ledge));return f?{w:f.w*U,d:f.layer==='wall'?0:f.h*U,cap:f.w*(f.hold||2)}:null;}
  const h=list.find(o=>o.id===on);if(!h||h.q.on)return null;
  if(h.it.spot==='floor'&&h.it.surface)return {w:h.it.w*U,d:h.it.h*U,cap:h.it.w*h.it.h*2};
  if(h.it.spot==='wall'&&h.it.ledge)return {w:h.it.w*U,d:0,cap:h.it.w*2};
  return null;
}
function zoneOf(rm,it){const rows=it.spot==='wall'?rm.wrows:rm.frows,xm=rm.cols*U-it.w*U,ym=rows*U-it.h*U;return rows&&xm>=0&&ym>=0?[xm,ym]:null;}
const ov=(a0,a1,b0,b1)=>Math.max(0,Math.min(a1,b1)-Math.max(a0,b0));
function blockedBy(rm,it,x,y){
  const layer=it.spot==='wall'?'wall':'floor',w=it.w*U,h=it.h*U;
  for(const f of rm.fix){
    if(f.layer!==layer||!f.block||(it.spot==='rug'&&f.rug)||(f.allow||[]).some(t=>it.tags.includes(t)))continue;
    if(ov(x,x+w,f.x*U,(f.x+f.w)*U)>U/2&&ov(y,y+h,f.y*U,(f.y+f.h)*U)>U/2)return f;
  }
  return null;
}
/** deco.check: null when `it` may stand at `q` among `list` (the others in the room). */
function checkQ(rm,it,q,list){
  if(!it.rooms.includes(rm.type))return {code:'type'};
  if(q.on){
    const h=it.spot==='top'&&hostBox(rm,q.on,list);if(!h)return {code:'support'};
    if(list.filter(o=>o.q.on===q.on).length>=h.cap)return {code:'host_full'};
  }else{
    const z=zoneOf(rm,it);if(!z)return {code:'bounds'};
    const f=blockedBy(rm,it,q.x,q.y);if(f)return {code:'fixture',f};
  }
  if(list.length>=rm.cap)return {code:'room_full'};
  return null;
}
function whyText(bad,rm,it){
  const FX=CD().fix_names||{};
  if(bad.code==='fixture')return `Chỗ này vướng ${FX[bad.f.t]||'chỗ cố định'}.`;
  if(bad.code==='host_full')return 'Trên đó hết chỗ rồi. Đặt chỗ khác nhé.';
  if(bad.code==='room_full')return `${rm.name} bày đủ ${rm.cap} món rồi. Thu hồi bớt món khác nhé.`;
  if(bad.code==='type')return `${it.name} không hợp đặt ở ${low(rm.name)}.`;
  if(bad.code==='support')return `${it.name} chỉ đặt lên bàn, kệ, giường hoặc sàn trống thôi.`;
  return 'Chỗ này không đặt được.';
}
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
/** The surfaces a small thing may stand on in `rm`: their top in pixels and how to turn a point into a spot. */
function surfaces(rm,list,G){
  const out=[];
  for(const o of list){
    if(o.q.on)continue;
    const a=A.anchor(o.it,o.q,G),left=a[0];
    if(o.it.spot==='floor'&&o.it.surface)out.push({on:o.id,left,w:o.it.w*U,d:o.it.h*U,yA:A.geom(rm).FY+(o.q.y+U)*A.SF-6-o.it.surface,wall:false});
    else if(o.it.spot==='wall'&&o.it.ledge)out.push({on:o.id,left,w:o.it.w*U,d:0,yA:a[1]+o.it.ledge,wall:true});
  }
  for(const f of rm.fix){
    if(!(f.top||f.ledge))continue;
    const left=A.PX+f.x*A.CW;
    if(f.layer==='wall')out.push({on:'#'+f.t,left,w:f.w*U,d:0,yA:G.WY+f.y*A.WR+f.ledge,wall:true});
    else out.push({on:'#'+f.t,left,w:f.w*U,d:f.h*U,yA:G.FY+(f.y*U+U)*A.SF-6-f.top,wall:false});
  }
  return out;
}
/** The spot under a point: (ax, ay) is where the piece's origin would be. null: no zone for it here. */
function candidate(rm,it,ax,ay,list,f){
  const G=A.geom(rm),W=it.w*A.CW;
  if(it.spot==='top'){
    let best=null,bd=1e9;
    for(const s of surfaces(rm,list,G)){
      const cx=ax+W/2,yB=s.yA+Math.max(0,s.d-U)*A.SF;
      if(cx<s.left-6||cx>s.left+s.w*A.SX+6)continue;
      const dy=ay<s.yA?s.yA-ay:ay>yB?ay-yB:0;if(dy>(s.wall?14:12))continue;
      if(dy<bd||dy===bd){bd=dy;best=s;}
    }
    if(best){
      const q={r:rm.id,x:clamp(Math.round((ax-best.left)/A.SX),0,Math.max(0,best.w-it.w*U)),y:clamp(Math.round((ay-best.yA)/A.SF),0,Math.max(0,best.d-it.h*U)),f,on:best.on};
      return q;
    }
  }
  const z=zoneOf(rm,it);if(!z)return null;
  let x=(ax-A.PX)/A.SX,y;
  if(it.spot==='wall')y=(ay-G.WY)/A.SW;
  else if(it.spot==='top')y=(ay+6-G.FY)/A.SF-U;
  else y=(ay+3-G.FY)/A.SF-it.h*U;
  return {r:rm.id,x:clamp(Math.round(x),0,z[0]),y:clamp(Math.round(y),0,z[1]),f};
}
const heldItem=()=>S.held?ITEM(S.held.k):null;
const roomsFor=it=>(V()?.rooms||[]).filter(r=>it.rooms.includes(r.type));
/** Where the finger holds a piece that comes from the drawer: its base a little above the finger. */
function grabFor(it){const W=it.w*A.CW;return it.spot==='wall'?[W/2,it.h*A.WR+8]:[W/2,6];}

/* ---- the light of the hour: home is where you are right now, so the device's clock (a shift's clock is the shop's) ---- */
function minuteNow(){const d=new Date();return d.getHours()*60+d.getMinutes();}

/* ---- the room ---- */
function partsMap(){const r=R();return r&&V()?.place.where==='own'?Object.fromEntries(r.parts.map(p=>[p.id,p])):null;}
/** Back to front: rugs, the wall (and what stands on wall shelves), then the floor by its front edge, each small
 * thing right after what it stands on. `z` orders pieces at the same depth. */
function depthOrder(rm,list){
  const byId=new Map(list.map(o=>[o.id,o])),key=o=>{
    const it=o.it,q=o.q;
    if(q.on){
      if(q.on[0]==='#'){const f=rm.fix.find(f=>f.t===q.on.slice(1));if(f?.layer==='wall')return [1,(q.z||0)+100,q.x];return [2,(f?(f.y+f.h)*U:U)-.5+q.y/1000,q.z||0];}
      const h=byId.get(q.on);if(!h)return [9,0,0];const hk=key(h);return [hk[0],hk[1]+.001+q.y/100000,(hk[2]||0)+.01+(q.z||0)/1000];
    }
    if(it.spot==='rug')return [0,q.z||0,q.y];
    if(it.spot==='wall')return [1,q.z||0,q.y];
    return [2,q.y+(it.spot==='top'?U:it.h*U),q.z||0];
  };
  return [...list].map(o=>[key(o),o]).sort((a,b)=>a[0][0]-b[0][0]||a[0][1]-b[0][1]||a[0][2]-b[0][2]).map(x=>x[1]);
}
function bbox(it,a){
  const [x,y]=a,w=it.w*A.CW,h=(A.ART[it.id]?.h||30)+4;
  if(it.spot==='wall')return [x,y,w,it.h*A.WR];
  if(it.spot==='rug')return [x,y-it.h*A.FR,w,it.h*A.FR];
  return [x,y-h,w,h+2];
}
const sparkles=(x,y,w,h)=>`<g class="dc-sparks" aria-hidden="true">${[[.1,.1,'#ffd34d'],[.9,.2,'#ff9ec0'],[.5,-.05,'#9fe0ff'],[.05,.75,'#b8f0a0'],[.95,.8,'#ffd34d']].map(([a,b,c],i)=>
  `<path class="dc-spark s${i}" d="M${(x+w*a).toFixed(1)} ${(y+h*b-6).toFixed(1)}l2 4.5l4.5 1.5l-4.5 1.5l-2 4.5l-2-4.5l-4.5-1.5l4.5-1.5z" fill="${c}"/>`).join('')}</g>`;
/** Where pieces may go while one is held or dragged: its zone and the surfaces (small things). */
function zoneMarkup(rm,it,G,list){
  if(!it||!it.rooms.includes(rm.type))return '';
  const z=zoneOf(rm,it),out=[];
  if(it.spot==='wall'&&rm.wrows)out.push(`<rect class="dc-zone" x="${A.PX}" y="${G.WY}" width="${rm.cols*A.CW}" height="${rm.wrows*A.WR}" rx="8"/>`);
  else if(it.spot!=='wall'&&z)out.push(`<rect class="dc-zone" x="${A.PX}" y="${G.FY}" width="${rm.cols*A.CW}" height="${rm.frows*A.FR}" rx="8"/>`);
  for(const f of rm.fix)if(f.block&&f.layer===(it.spot==='wall'?'wall':'floor')&&!(it.spot==='rug'&&f.rug)&&!(f.allow||[]).some(t=>it.tags.includes(t))){
    const y=f.layer==='wall'?G.WY+f.y*A.WR:G.FY+f.y*A.FR,h=f.layer==='wall'?f.h*A.WR:f.h*A.FR;
    out.push(`<rect class="dc-nogo" x="${A.PX+f.x*A.CW+3}" y="${y+3}" width="${f.w*A.CW-6}" height="${h-6}" rx="6"/>`);
  }
  if(it.spot==='top')for(const s of surfaces(rm,list,G))out.push(`<rect class="dc-surf" x="${s.left+3}" y="${s.yA-5}" width="${s.w*A.SX-6}" height="${Math.max(0,s.d-U)*A.SF+8}" rx="4"/>`);
  return `<g class="dc-ok" pointer-events="none">${out.join('')}</g>`;
}

/** One room as SVG markup. opts: edit (zones, selection), photo (no hit areas, no selection). */
function roomMarkup(rm,opts={}){
  const v=V(),G=A.geom(rm),Lt=A.lightAt(minuteNow()),edit=!!opts.edit,photo=!!opts.photo,uid=(photo?'p':'')+rm.id;
  const skin={...(rm.skin||{})};if(S.try&&S.try.room===rm.id)skin[S.try.part==='wall'?'w':'f']=S.try.skin==='auto'?undefined:S.try.skin;
  const list=inRoom(rm),theirs=mateIn(rm),all=theirs.length?[...list,...theirs]:list,out=[A.roomBack(rm,G,partsMap(),Lt,uid,skin)];
  if(edit&&!photo&&S.held&&!S.drag)out.push(zoneMarkup(rm,heldItem(),G,list.filter(o=>o.id!==S.held.uid)));
  out.push('<g class="dc-zonelayer" pointer-events="none"></g>');
  const glows=[];
  for(const o of depthOrder(rm,all)){
    const it=o.it,a=A.anchor(it,o.q,G,hostFor(rm,o.q,all));
    const g=A.glowAt(it,a[0],a[1],o.q.f);if(g)glows.push(g);
    const body=(o.q.on?A.contact(it,a[0],a[1]):'')+A.pieceAt(it,a[0],a[1],o.q.f,o.mate?o.c:tintOf(o.id));
    if(photo){out.push(body);continue;}
    if(o.mate){out.push(`<g class="dc-mate" pointer-events="none" aria-hidden="true">${body}</g>`);continue;}   // the spouse's: not ours to move
    const [bx,by,bw,bh]=bbox(it,a);
    const sel=S.sel===o.id,pop=S.pop===o.id,ghost=S.held?.src==='room'&&S.held.uid===o.id;
    out.push(`<g class="dc-it${sel?' sel':''}${pop?' pop':''}${ghost?' ghost':''}" data-uid="${esc(o.id)}" data-k="${esc(o.k)}"${o.q.on?` data-on="${esc(o.q.on)}"`:''} tabindex="${edit?0:-1}" role="button" aria-label="${esc(it.name)}"><g class="dc-piece">${body}</g>`
      +`<rect class="dc-hit" x="${bx}" y="${by}" width="${bw}" height="${bh}" rx="6"/>${sel?`<rect class="dc-selbox" x="${bx-3}" y="${by-3}" width="${bw+6}" height="${bh+6}" rx="9"/>`:''}${pop?sparkles(bx,by,bw,bh):''}</g>`);
  }
  out.push(catsMarkup(rm,G,list,photo));
  out.push(A.roomFront(rm,G));
  out.push(A.roomLight(G,Lt,glows,uid));
  out.push('<g class="dc-preview" pointer-events="none"></g>');
  const name=`${rm.name}: ${list.map(o=>o.it.name).join(', ')||'chưa bày gì'}`;
  return {G,svg:`<svg class="dc-room${edit?' edit':''}${S.held?' holding':''} lt-${Lt.phase}" viewBox="0 0 ${G.W} ${G.H}" role="group" aria-label="${esc(name)}" data-room="${esc(rm.id)}">${out.join('')}</svg>`};
}

/* ---- 🐈 the cats: Mochi always, Bơ too once the room is Rất ấm cúng. They wander and nap on rugs, beds, sofas
 * (CSS transitions on one transform each; a timer every few seconds; still with reduced motion). ---- */
const CATS={room:'',list:[],timer:0};
const NAP={sofa:['sleep',-27],giuong:['sleep','bed'],nem:['sleep',-9],o_meo:['sleep',-9],ghe_luoi:['loaf',-25],tham:['melt','rug'],tham_hoa:['melt','rug'],ghe_may:['loaf',-24],
  ghe_tam_nang:['sleep',-20],tham_tam:['melt','rug'],sap_go:['sleep',-22]};
function napSpots(rm,G,list){
  const out=[];
  for(const o of list){
    if(o.q.on)continue;const n=NAP[o.it.id];if(!n)continue;
    const a=A.anchor(o.it,o.q,G),W=o.it.w*A.CW;
    const y=n[1]==='rug'?a[1]-o.it.h*A.FR/2+3:n[1]==='bed'?a[1]-o.it.h*A.FR*.55:a[1]+n[1];
    out.push({x:a[0]+W*(o.it.w>2?.4:.5),y,pose:n[0]});
  }
  if(rm.type==='bunk')out.push({x:A.PX+A.CW*2.6,y:G.FY+A.FR*1.3,pose:'sleep'});
  return out;
}
function floorSpot(rm,G){
  for(let i=0;;i++){   // not in the pool (or on a fixture that keeps pieces off)
    const s={x:A.PX+18+Math.random()*(rm.cols*A.CW-36),y:G.FY+A.FR*.55+Math.random()*Math.max(4,rm.frows*A.FR-A.FR*.7),pose:Math.random()<.5?'loaf':'sleep'};
    if(i>8||!(rm.fix||[]).some(f=>f.t==='pool'&&s.x>A.PX+f.x*A.CW-14&&s.x<A.PX+(f.x+f.w)*A.CW+14&&s.y>G.FY+f.y*A.FR-4&&s.y<G.FY+(f.y+f.h)*A.FR+12))return s;
  }
}
function catsWanted(){const v=V();return v&&v.cozy.total>=24?2:1;}
function catsFor(rm,G,list){
  const want=catsWanted();
  if(CATS.room!==rm.id||CATS.list.length!==want){
    const spots=napSpots(rm,G,list),pick=i=>spots[i]||floorSpot(rm,G);
    CATS.room=rm.id;
    CATS.list=['mochi','bo'].slice(0,want).map((coat,i)=>{const s=pick(i);return {coat,x:s.x,y:s.y,pose:s.pose,flip:i%2===1,to:null,until:0};});
  }
  return CATS.list;
}
const catInner=c=>`<g class="dc-cat-in ${c.pose}"><g${c.flip?' transform="scale(-1 1)"':''}>${A.catSVG(c.pose,c.coat)}</g></g>`;
function catsMarkup(rm,G,list,photo){
  const cats=catsFor(rm,G,list);
  if(photo)return cats.map(c=>`<g transform="translate(${c.x.toFixed(1)} ${c.y.toFixed(1)})">${catInner(c)}</g>`).join('');
  return `<g class="dc-cats" pointer-events="none" aria-hidden="true">${cats.map((c,i)=>`<g class="dc-cat" data-cat="${i}" style="transform:translate(${c.x.toFixed(1)}px,${c.y.toFixed(1)}px)">${catInner(c)}</g>`).join('')}</g>`;
}
/** Before the room is redrawn: where each walking cat is right now. */
function catsFreeze(){
  for(const el of S.dlg?.querySelectorAll('.dc-cat')||[]){
    const c=CATS.list[+el.dataset.cat];if(!c||!c.to)continue;
    const m=new DOMMatrixReadOnly(getComputedStyle(el).transform);c.x=m.e;c.y=m.f;
  }
}
/** After it is redrawn: walking cats carry on to where they were going. */
function catsResume(){
  const now=performance.now();
  for(const el of S.dlg?.querySelectorAll('.dc-cat')||[]){
    const c=CATS.list[+el.dataset.cat];if(!c?.to)continue;
    const left=Math.max(0,c.until-now);
    if(left<60){arrive(c,el);continue;}
    void el.getBoundingClientRect();
    el.style.transitionDuration=`${left}ms`;el.style.transform=`translate(${c.to.x.toFixed(1)}px,${c.to.y.toFixed(1)}px)`;
  }
}
function arrive(c,el){
  if(!c.to)return;c.x=c.to.x;c.y=c.to.y;c.pose=c.to.pose;c.to=null;
  if(el){el.style.transitionDuration='0ms';el.style.transform=`translate(${c.x.toFixed(1)}px,${c.y.toFixed(1)}px)`;el.innerHTML=catInner(c);}
}
function catsStop(){clearTimeout(CATS.timer);CATS.timer=0;for(const c of CATS.list)if(c.to)arrive(c,null);}
function catsTick(){
  clearTimeout(CATS.timer);CATS.timer=0;
  if(!S.dlg?.open||calm()||document.hidden){if(S.dlg?.open)CATS.timer=setTimeout(catsTick,6000);return;}
  const rm=roomOf(S.room),svg=roomSvg();
  if(rm&&svg&&!S.drag){
    const G=A.geom(rm),list=inRoom(rm),spots=napSpots(rm,G,list),now=performance.now();
    for(const [i,c] of CATS.list.entries()){
      const el=svg.querySelector(`.dc-cat[data-cat="${i}"]`);if(!el)continue;
      if(c.to){if(now>=c.until)arrive(c,el);continue;}
      if(Math.random()<(c.pose==='sleep'||c.pose==='melt'?.35:.6)){
        const free=spots.filter(s=>!CATS.list.some(o=>o!==c&&Math.hypot(o.x-s.x,o.y-s.y)<20));
        const s=free.length&&Math.random()<.6?free[Math.random()*free.length|0]:floorSpot(rm,G);
        const dist=Math.hypot(s.x-c.x,s.y-c.y);if(dist<8)continue;
        const ms=Math.round(dist/26*1000);
        c.flip=s.x<c.x;c.pose='walk';c.to=s;c.until=now+ms;
        el.innerHTML=catInner(c);void el.getBoundingClientRect();
        el.style.transitionDuration=`${ms}ms`;el.style.transform=`translate(${s.x.toFixed(1)}px,${s.y.toFixed(1)}px)`;
        setTimeout(()=>{const e2=roomSvg()?.querySelector(`.dc-cat[data-cat="${i}"]`);if(c.to===s)arrive(c,e2);},ms+30);
      }
    }
  }
  CATS.timer=setTimeout(catsTick,3500+Math.random()*4500);
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
    case'drawer':S.drawer=data.d;S.cat='';S.resetStrip=true;S.held=S.drawer==='skin'?null:S.held;render();return;
    case'cat':S.cat=data.cat||'';S.resetStrip=true;render();return;
    case'hold':{const it=ITEM(data.k);if(!it)return;
      if(S.held&&S.held.k===data.k&&S.held.src===data.src){S.held=null;render();return;}
      S.held={k:data.k,src:data.src};S.sel='';sfx('pop');
      if(!it.rooms.includes(roomOf(S.room)?.type)){const r=roomsFor(it)[0];if(r)S.room=r.id;}
      render();return;}
    case'unhold':S.held=null;render();return;
    case'buyBag':{const it=heldItem();if(!it||S.held.src!=='shop')return;
      if(await ask(`Mua ${low(it.name)}?`,`Cất vào túi đồ, đặt lúc nào cũng được. Ấm cúng +${it.cozy} khi bày ra (mỗi loại tính một lần).`,`Mua · ${xu(it.price)}`,it.price)){
        const r=await send('jr_deco_buy',{item:it.id,confirm:true,n:nonce()});if(r){sfx('coins');S.held={k:it.id,src:'bag'};render();}}return;}
    case'move':{const p=placed(data.uid);if(!p)return;S.held={k:p.k,src:'room',uid:p.id};S.sel='';sfx('pop');render();return;}
    case'flip':{const p=placed(data.uid);if(!p)return;await putPiece(p.id,{...qOf(p),f:p.f?0:1});return;}
    case'zup':case'zdown':{const p=placed(data.uid);if(!p)return;const rm=roomOf(p.r),zs=inRoom(rm,new Set([p.id])).map(o=>o.q.z||0);
      const z=op==='zup'?Math.min(CD().z_max||99,Math.max(0,...zs)+1):Math.max(0,Math.min(...zs,p.z||0)-1);
      if(z===(p.z||0)){S.flash={text:op==='zup'?'Món này đang ở trên cùng rồi.':'Món này đang ở dưới cùng rồi.',kind:'warn'};render();return;}
      await putPiece(p.id,{...qOf(p),z});return;}
    case'tint':{const p=placed(data.uid),it=ITEM(p?.k);if(!it)return;
      (await import('./palette.js')).pickColor(S.env,{title:it.name,current:tintOf(p.id)||'goc',preview:c=>A.thumb(it,88,c),
        onTry:c=>{S.tryTint={uid:p.id,c};paintPiece(p.id);},apply:async c=>!!await send('jr_wd_deco',{uid:p.id,color:c}),
        onClose:()=>{S.tryTint=null;render();}});return;}
    case'pick':return pick(data.uid);
    case'sell':{const p=placed(data.uid)||v.bag.find(b=>b.id===data.uid),it=ITEM(p?.k);if(!it)return;
      if(await S.env.confirmAction(`Bán lại ${low(it.name)}?`,`Nhận ${xu(it.sell)} (${CD().sell_pct}% giá mua).`,`Bán · ${xu(it.sell)}`)){
        const r=await send('jr_deco_sell',{uid:p.id,confirm:true,n:nonce()});if(r){sfx('coins');S.sel='';S.undo=S.undo.filter(u=>!(p.id in u));render();}}return;}
    case'pickAll':{if(!v.items.length)return;
      if(await S.env.confirmAction('Cất hết đồ vào túi?','Mọi món đang bày ở chỗ này về túi đồ. Bấm Hoàn tác để bày lại như cũ.','Cất hết')){
        const prev=Object.fromEntries(v.items.map(p=>[p.id,qOf(p)]));
        const r=await send('jr_deco_pick',{uid:'all'});if(r){pushUndo(prev);S.sel='';sfx('click');render();}}return;}
    case'undo':return undo();
    case'skin':return pickSkin(data.part,data.skin);
    case'photo':return takePhoto();
    case'photoSave':{if(!S.photo)return;const career=S.env.api.state?.current||S.env.api.state?.focus;
      S.busy=true;paintBusy();
      try{const r=await S.env.api.command('photo',{image:S.photo.image,title:S.photo.title},career);S.flash={text:r.message,kind:'good'};S.photo.saved=true;sfx('chime');}
      catch(e){if(!e.quiet)S.flash={text:e.message||'Chưa lưu được ảnh.',kind:'bad'};}
      finally{S.busy=false;render();}return;}
    case'photoClose':S.photo=null;render();return;
    case'tipOk':tipDone();render();return;
    case'relax':{const a=(V()?.relax||[]).find(x=>x.id===data.act);if(!a||!a.ok)return;
      const r=await send('jr_relax_do',{act:a.id},{loud:true});if(r)sfx('chime');return;}
    case'fix':{const r=R();const all=data.part==='all',p=r.parts.find(x=>x.id===data.part),cost=all?r.fix_all:p?.fix;if(!cost)return;
      const what=all?'Sửa cả nhà?':`Sửa ${low(PART(p.id).name)}?`,body=all?r.parts.filter(x=>x.fix).map(x=>`${PART(x.id).name} ${xu(x.fix)}`).join(' · '):`${condWord(p.c,p.id)} (${p.c}%) → như mới.`;
      if(await ask(what,body,`Sửa · ${xu(cost)}`,cost)){const res=await send('jr_reno_fix',{part:data.part,cost,confirm:true});if(res)sfx('success');}return;}
    case'up':{const r=R(),p=r.parts.find(x=>x.id===data.part);if(!p?.up)return;
      if(await ask(`${p.up.name}?`,`${PART(p.id).name} như mới, bền hơn. Ấm cúng +${CR().cozy_lv}.`,`Làm · ${xu(p.up.cost)}`,p.up.cost)){const res=await send('jr_reno_up',{part:p.id,lv:p.up.lv,cost:p.up.cost,confirm:true});if(res)sfx('success');}return;}
  }
}

function pushUndo(prev){S.undo.push(prev);if(S.undo.length>20)S.undo.shift();}
/** After a change: the pop-in and sparkles, a chime when a set is done. */
function cheer(r,uid){
  if(uid)S.pop=uid;
  const set=/🎉/.test(r?.message||'');
  sfx(set?'chime':'pop');
}
/** Move / flip / reorder a placed piece (or place one from the bag) at the free spot `q`. */
async function putPiece(uid,q,again=''){
  const prev={[uid]:placed(uid)?qOf(placed(uid)):null};
  for(const u of ridersOf(uid))prev[u]=qOf(placed(u));
  const body={uid,r:q.r,x:q.x,y:q.y,f:q.f||0};if(q.on)body.on=q.on;if(q.z!=null)body.z=q.z;
  const r=await send('jr_deco_put',body);
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
  const prev={[uid]:qOf(p)};for(const u of ridersOf(uid))prev[u]=qOf(placed(u));
  const r=await send('jr_deco_pick',{uid});
  if(r){pushUndo(prev);S.sel='';sfx('click');render();}
}
async function undo(){
  const last=S.undo.pop();if(!last){render();return;}
  const r=await send('jr_deco_layout',{set:last},{loud:true});
  if(r){sfx('pop');render();}
}
/** Put the held piece at the free spot `q` of the current room (buying it first from the shop). */
async function dropAt(q){
  const h=S.held,it=heldItem(),rm=roomOf(S.room);if(!h||!it||!rm||!q)return;
  const bad=checkQ(rm,it,q,inRoom(rm,new Set(h.uid?[h.uid,...ridersOf(h.uid)]:[])));
  if(bad){S.flash={text:whyText(bad,rm,it),kind:'warn'};sfx('error');render();return;}
  if(h.src==='room'){await putPiece(h.uid,q);return;}
  if(h.src==='bag'){const b=V().bag.find(x=>x.k===h.k);if(!b){S.held=null;render();return;}
    await putPiece(b.id,q,h.k);return;}
  if(await ask(`Mua ${low(it.name)}?`,`Đặt ở ${low(rm.name)} · ấm cúng +${it.cozy} nếu chỗ này chưa có món này. Bán lại được ${CD().sell_pct}% giá.`,`Mua · ${xu(it.price)}`,it.price)){
    const put={r:q.r,x:q.x,y:q.y,f:q.f||0};if(q.on)put.on=q.on;
    const r=await send('jr_deco_buy',{item:it.id,confirm:true,put,n:nonce()});
    if(r&&r.uid){if(!r.duplicate)pushUndo({[r.uid]:null});S.held=null;S.sel=r.uid;sfx('coins');cheer(r,r.uid);render();}
  }else render();
}
/** 🎨 a wallpaper or a floor for this room: free ones at once, a priced one after a look and a yes. */
async function pickSkin(part,skin){
  const rm=roomOf(S.room),sk=SKIN(skin),v=V();if(!rm||!sk)return;
  const cur=rm.skin?.[part==='wall'?'w':'f']||'auto';if(cur===skin)return;
  const owned=new Set(v.owned||[]),pay=sk.price&&!owned.has(skin)?sk.price:0;
  if(pay){
    S.try={room:rm.id,part,skin};render();
    const ok=await ask(`Mua ${low(sk.name)}?`,`Mua một lần, phòng nào cũng dùng được. Đang xem thử trong ${low(rm.name)}.`,`Mua · ${xu(pay)}`,pay);
    S.try=null;if(!ok){render();return;}
  }
  const r=await send('jr_deco_skin',{r:rm.id,part,skin,confirm:pay>0,n:nonce()});
  if(r){sfx(pay?'coins':'pop');render();}
}

/* ---- keyboard: arrows nudge the selected piece (Shift: a whole cell), F flips it, PageUp/PageDown order it,
 * Delete puts it back in the bag. Nudges wait a moment and go as one move. ---- */
function onKey(e){
  const g=e.target.closest?.('g[data-uid]');
  if(g&&(e.key==='Enter'||e.key===' ')){e.preventDefault();if(!S.edit)S.edit=true;S.sel=S.sel===g.dataset.uid?'':g.dataset.uid;render();focusSel();return;}
  if(!S.edit||!S.sel||S.busy||!e.target.closest?.('svg.dc-room'))return;   // the keys belong to the room, not the drawer
  const p=placed(S.sel);if(!p)return;
  const step=e.shiftKey?U:4,d={ArrowLeft:[-step,0],ArrowRight:[step,0],ArrowUp:[0,-step],ArrowDown:[0,step]}[e.key];
  if(d){e.preventDefault();nudge(p,d);return;}
  if(e.key==='f'||e.key==='F'){e.preventDefault();putPiece(p.id,{...qOf(p),f:p.f?0:1}).then(focusSel);return;}
  if(e.key==='PageUp'||e.key==='PageDown'){e.preventDefault();onClick(e.key==='PageUp'?'zup':'zdown',{uid:p.id}).then(focusSel);return;}
  if(e.key==='Delete'||e.key==='Backspace'){e.preventDefault();pick(p.id);}
}
function nudge(p,[dx,dy]){
  const rm=roomOf(p.r),it=ITEM(p.k);if(!rm||!it)return;
  const n=S.nudge&&S.nudge.uid===p.id?S.nudge:{uid:p.id,q:qOf(p)};
  const list=inRoom(rm,new Set([p.id,...ridersOf(p.id)]));
  let q={...n.q,x:n.q.x+dx,y:n.q.y+dy};
  if(q.on){const h=hostBox(rm,q.on,list);if(h){q.x=clamp(q.x,0,Math.max(0,h.w-it.w*U));q.y=clamp(q.y,0,Math.max(0,h.d-it.h*U));}}
  else{const z=zoneOf(rm,it);if(z){q.x=clamp(q.x,0,z[0]);q.y=clamp(q.y,0,z[1]);}}
  n.q=q;S.nudge=n;clearTimeout(n.t);
  showMove(p.id,q);
  n.t=setTimeout(async()=>{S.nudge=null;await putPiece(p.id,q);focusSel();},320);
}
const focusSel=()=>{if(S.sel)S.dlg?.querySelector(`g[data-uid="${CSS.escape(S.sel)}"]`)?.focus({preventScroll:true});};

/* ---- pointer: press a piece and drag it; drag a card up out of the drawer; tap to select or to drop ---- */
function svgPoint(svg,cx,cy){const m=svg.getScreenCTM();if(!m)return null;const p=new DOMPoint(cx,cy).matrixTransform(m.inverse());return {x:p.x,y:p.y};}
const roomSvg=()=>S.dlg?.querySelector('svg.dc-room');
function onDown(e){
  if(S.busy||e.button>0||S.photo)return;
  const svg=e.target.closest?.('svg.dc-room'),card=e.target.closest?.('.dc-buycard');
  if(svg){
    const g=e.target.closest('g[data-uid]');
    S.press={kind:'room',id:e.pointerId,x:e.clientX,y:e.clientY,uid:g?.dataset.uid||''};
    try{svg.setPointerCapture(e.pointerId);}catch{/* fine */}
  }else if(card&&S.edit&&!card.disabled){
    S.press={kind:'card',id:e.pointerId,x:e.clientX,y:e.clientY,k:card.dataset.k,src:card.dataset.src,el:card};
  }
}
/** Start dragging the placed piece `uid` from the pointer at (cx, cy). */
function startPieceDrag(uid,cx,cy){
  const p=placed(uid),rm=roomOf(p?.r),svg=roomSvg();if(!p||!rm||!svg)return false;
  const it=ITEM(p.k),G=A.geom(rm),list=inRoom(rm),q=qOf(p),a=A.anchor(it,q,G,hostFor(rm,q,list)),pt=svgPoint(svg,cx,cy);if(!pt)return false;
  const ride=ridersOf(uid),els=[uid,...ride].map(u=>svg.querySelector(`g[data-uid="${CSS.escape(u)}"]`)).filter(Boolean);
  const layer=els[0]?.parentNode;for(const el of els){el.classList.add('drag');layer?.append(el);}   // on top while held
  S.drag={kind:'piece',uid,k:p.k,it,rm,q0:q,a0:a,grab:[pt.x-a[0],pt.y-a[1]],els,list:inRoom(rm,new Set([uid,...ride])),q:q,bad:null};
  S.held={k:p.k,src:'room',uid};S.sel='';
  svg.classList.add('dragging');
  svg.querySelector('.dc-zonelayer').innerHTML=zoneMarkup(rm,it,G,S.drag.list);
  for(const el of svg.querySelectorAll('.dc-selbox'))el.remove();
  sfx('pop');buzz(8);
  return true;
}
function onMove(e){
  const p=S.press;if(!p||p.id!==e.pointerId)return;
  const dx=e.clientX-p.x,dy=e.clientY-p.y;
  if(!S.drag){
    if(p.kind==='room'){
      if(!S.edit||!p.uid||Math.hypot(dx,dy)<6)return;
      if(S.held&&S.held.src!=='room')return;
      if(!startPieceDrag(p.uid,p.x,p.y))return;
    }else{
      if(Math.abs(dy)<12||Math.abs(dy)<Math.abs(dx)*1.2)return;   // sideways: the drawer scrolls
      const it=ITEM(p.k);if(!it)return;
      try{p.el.setPointerCapture(e.pointerId);}catch{/* fine */}
      S.drag={kind:'card',k:p.k,src:p.src,it,grab:grabFor(it),q:null,bad:null,uid:p.src==='bag'?(V()?.bag.find(b=>b.k===p.k)?.id||''):''};S.held={k:p.k,src:p.src};S.sel='';
      if(!it.rooms.includes(roomOf(S.room)?.type)){const r=roomsFor(it)[0];if(r){S.room=r.id;render();}}
      const svg=roomSvg(),rm=roomOf(S.room);if(svg&&rm){svg.querySelector('.dc-zonelayer').innerHTML=zoneMarkup(rm,it,A.geom(rm),inRoom(rm));svg.classList.add('dragging');}
      p.el.classList.add('lifted');
      sfx('pop');buzz(8);
    }
  }
  dragTo(e.clientX,e.clientY);
}
/** Follow the finger: the piece itself (a transform, nothing redrawn), green where it may land, red where not. */
function dragTo(cx,cy){
  const D=S.drag,svg=roomSvg();if(!D||!svg)return;
  const rm=roomOf(S.room),pt=svgPoint(svg,cx,cy),r=svg.getBoundingClientRect();
  const inside=cx>=r.left-8&&cx<=r.right+8&&cy>=r.top-8&&cy<=r.bottom+8;
  if(D.kind==='card'){
    floatGhost(inside?null:D.it,cx,cy);
    const g=svg.querySelector('.dc-preview');
    if(!inside||!rm||!pt||!D.it.rooms.includes(rm.type)){g.innerHTML='';D.q=null;return;}
    const list=inRoom(rm),q=candidate(rm,D.it,pt.x-D.grab[0],pt.y-D.grab[1],list,0);
    if(!q){g.innerHTML='';D.q=null;return;}
    const a=A.anchor(D.it,q,A.geom(rm),hostFor(rm,q,list));D.q=q;D.bad=checkQ(rm,D.it,q,list);
    g.innerHTML=`<g class="dc-it drag${D.bad?' bad':''}">${q.on?A.contact(D.it,a[0],a[1]):''}${A.pieceAt(D.it,a[0],a[1],0,D.uid?tintOf(D.uid):null)}</g>`;
    return;
  }
  if(!pt)return;
  const G=A.geom(D.rm),q=candidate(D.rm,D.it,pt.x-D.grab[0],pt.y-D.grab[1],D.list,D.q0.f);
  if(!q)return;
  q.z=D.q0.z;if(!q.z)delete q.z;
  D.q=q;D.bad=checkQ(D.rm,D.it,q,D.list);D.out=!inside;
  showMove(D.uid,q,D);
}
/** Redraw one placed piece in place (the colour being tried in the palette picker), keeping the room as it is. */
function paintPiece(uid){
  const svg=roomSvg(),p=placed(uid),rm=roomOf(p?.r),el=svg?.querySelector(`g[data-uid="${CSS.escape(uid)}"] .dc-piece`);if(!el||!rm)return;
  const list=inRoom(rm),o=list.find(x=>x.id===uid);if(!o)return;
  const a=A.anchor(o.it,o.q,A.geom(rm),hostFor(rm,o.q,list));
  el.innerHTML=(o.q.on?A.contact(o.it,a[0],a[1]):'')+A.pieceAt(o.it,a[0],a[1],o.q.f,tintOf(uid));
}
/** Draw `uid` (and what stands on it) at `q` without redrawing the room. */
function showMove(uid,q,D=null){
  const svg=roomSvg(),p=placed(uid),rm=roomOf(p?.r);if(!svg||!p||!rm)return;
  const it=ITEM(p.k),G=A.geom(rm),list=inRoom(rm),q0=qOf(p);
  const a0=A.anchor(it,q0,G,hostFor(rm,q0,list)),a=A.anchor(it,q,G,hostFor(rm,q,list.filter(o=>o.id!==uid))),dx=a[0]-a0[0],dy=a[1]-a0[1];
  const els=D?.els||[uid,...ridersOf(uid)].map(u=>svg.querySelector(`g[data-uid="${CSS.escape(u)}"]`)).filter(Boolean);
  for(const el of els){
    el.setAttribute('transform',`translate(${dx.toFixed(1)} ${dy.toFixed(1)})`);
    el.classList.toggle('bad',!!(D&&(D.bad||D.out)));
  }
}
async function onUp(e){
  const p=S.press;if(!p||p.id!==e.pointerId)return;
  S.press=null;
  if(S.drag){
    const D=S.drag;dragTo(e.clientX,e.clientY);
    S.drag=null;S.dragEnd=Date.now();floatGhost(null);
    if(D.kind==='piece'){
      const rm=D.rm;
      if(!D.q||D.out||sameQ(D.q,D.q0)){S.held=null;S.sel=D.uid;render();return;}
      if(D.bad){S.held=null;S.sel=D.uid;S.flash={text:whyText(D.bad,rm,D.it),kind:'warn'};sfx('error');render();return;}
      S.held=null;await putPiece(D.uid,D.q);return;
    }
    if(D.q){await dropAt(D.q);return;}
    render();return;
  }
  if(p.kind!=='room')return;   // a card: its click event holds it
  const svg=roomSvg();if(!svg)return;
  if(!S.edit){S.edit=true;S.sel=p.uid;sfx('click');render();return;}
  if(S.held){
    const rm=roomOf(S.room),it=heldItem(),pt=svgPoint(svg,e.clientX,e.clientY);
    if(p.uid&&p.uid!==S.held.uid&&S.held.src==='room'&&!(it?.spot==='top')){S.held=null;S.sel=p.uid;render();return;}
    if(rm&&it&&pt){
      const g=grabFor(it),list=inRoom(rm,new Set(S.held.uid?[S.held.uid,...ridersOf(S.held.uid)]:[]));
      const q=candidate(rm,it,pt.x-g[0],pt.y-g[1],list,S.held.src==='room'?(placed(S.held.uid)?.f||0):0);
      if(q){await dropAt(q);return;}
    }
    S.flash={text:it&&rm&&!it.rooms.includes(rm.type)?whyText({code:'type'},rm,it):'Chỗ này không đặt được.',kind:'warn'};sfx('error');render();return;
  }
  if(p.uid){S.sel=S.sel===p.uid?'':p.uid;sfx('click');render();return;}
  if(S.sel){S.sel='';render();}
}
function onCancel(e){
  if(S.press?.id!==e.pointerId)return;
  const card=S.press.kind==='card'&&!S.drag;S.press=null;
  if(card)return;   // the drawer took the swipe
  if(S.drag){const D=S.drag;S.drag=null;S.held=null;floatGhost(null);if(D.kind==='piece')S.sel=D.uid;render();}
}
function floatGhost(it,cx,cy){
  let el=S.dlg?.querySelector('.dc-float');
  if(!it){el?.remove();return;}
  if(!el){el=document.createElement('div');el.className='dc-float';el.setAttribute('aria-hidden','true');el.innerHTML=A.thumb(it,64,S.drag?.uid?tintOf(S.drag.uid):null);S.dlg.append(el);}
  const r=S.dlg.getBoundingClientRect(),inside=getComputedStyle(S.dlg).transform!=='none';
  el.style.left=`${cx-(inside?r.left:0)-32}px`;el.style.top=`${cy-(inside?r.top:0)-72}px`;
}

/* ---- the photo: the room in a polaroid, drawn to a canvas ---- */
async function takePhoto(){
  const v=V(),rm=roomOf(S.room);if(!v||!rm)return;
  catsFreeze();
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
function render(){
  if(!S.dlg)return;
  catsFreeze();
  const body=S.dlg.querySelector('.dc-body'),top=body?.scrollTop,strip=S.dlg.querySelector('.dc-strip'),left=strip?.scrollLeft;
  const v=V();
  if(v&&S.undoKey!==v.place.key){S.undoKey=v.place.key;S.undo=[];CATS.room='';}
  if(v){const lv=levelIdx(v.cozy.total);S.cheer=S.lastLv>=0&&lv>S.lastLv;S.lastLv=lv;}
  S.dlg.querySelector('.dc-root').innerHTML=page();
  const b2=S.dlg.querySelector('.dc-body');if(b2&&top!=null)b2.scrollTop=S.toTop?0:top;
  if(S.toTop)S.dlg.scrollTop=0;
  const s2=S.dlg.querySelector('.dc-strip');if(s2&&left!=null&&!S.resetStrip)s2.scrollLeft=left;
  S.dlg.setAttribute('aria-busy',String(S.busy));
  S.pop='';S.resetStrip=false;S.toTop=false;
  catsResume();
  if(!CATS.timer&&S.dlg.open)CATS.timer=setTimeout(catsTick,1800);
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
  const wide=!!window.matchMedia?.('(min-width:720px)').matches;   // a wide sheet: the drawer beside the room, so a card is always in reach
  const tip=S.edit&&!tipSeen()?`<div class="dc-tip" role="note"><span aria-hidden="true">👆</span><p><b>Giữ một món rồi kéo đi đâu cũng được</b><small>Đồ nhỏ thả lên bàn, kệ, giường sẽ đứng trên đó. Chạm món đồ để lật, đổi phòng hoặc cất đi.</small></p>${btn('Hiểu rồi','tipOk',{},'ghost small')}</div>`:'';
  const bar=S.edit
    ?`<div class="dc-actions">${btn('↶ Hoàn tác','undo',{},'ghost',S.undo.length?'':' disabled')}${btn('🎒 Cất hết','pickAll',{},'ghost',v.items.length?'':' disabled')}${btn('✓ Xong','done',{},'primary')}</div>`
    :`<div class="dc-actions">${btn(v.items.length?'✏️ Bày trí phòng':'✏️ Bắt đầu bày trí','edit',{},'primary')}${btn('📸 Chụp phòng','photo',{},'ghost')}</div>`;
  const stage=`<div class="dc-stage">${roomTabs(v)}<div class="dc-roomwrap">${svg}${S.edit?'':'<span class="dc-hint" aria-hidden="true">Chạm phòng để bày trí</span>'}</div>${S.edit?(S.held?heldBar(v):S.sel?tools(v):''):''}${tip}${bar}${S.edit&&!wide?drawer(v):''}</div>`;
  return `<div class="dc-grid">${stage}<div class="dc-side">${relaxCard(v,rm)}${S.edit&&wide?drawer(v):''}${cozyCard(v)}${guestCard(v)}${setsCard(v)}${placeNote(v)}</div></div>`;
}
function roomTabs(v){
  if(v.rooms.length<2)return '';
  const it=heldItem(),n=id=>v.items.filter(i=>i.r===id).length;
  return `<div class="rn-rooms dc-rooms" role="tablist" aria-label="Các phòng">${v.rooms.map(r=>{const ok=it&&it.rooms.includes(r.type);
    return `<button type="button" role="tab" aria-selected="${S.room===r.id}" class="rn-room${S.room===r.id?' active':''}${ok?' ok':''}" data-dc="room" data-room="${r.id}"><span aria-hidden="true">${r.emoji}</span>${esc(r.name)}${n(r.id)?`<small>${n(r.id)}</small>`:''}</button>`;}).join('')}</div>`;
}
function heldBar(v){
  const it=heldItem(),rm=roomOf(S.room);if(!it)return '';
  const here=rm&&it.rooms.includes(rm.type),where=roomsFor(it).map(r=>low(r.name));
  const full=here&&inRoom(rm,new Set(S.held.uid?[S.held.uid]:[])).length>=rm.cap;
  const hint=!where.length?esc('Món này không hợp chỗ ở này.'):!here?`Món này đặt ở ${where.map(w=>`<i>${esc(w)}</i>`).join(', ')}.`:esc(full?`${rm.name} bày đủ ${rm.cap} món rồi.`:it.spot==='top'?'Chạm hoặc kéo vào phòng: lên bàn, kệ, giường hay sàn đều được.':S.held.src==='room'?'Chạm chỗ muốn dời tới.':'Chạm hoặc kéo vào chỗ muốn đặt.');
  const sub=S.held.src==='shop'?`${xu(it.price)} · ấm cúng +${it.cozy}`:S.held.src==='bag'?`Trong túi · ấm cúng +${it.cozy}`:'Đang dời';
  return `<div class="dc-held" role="status">${A.thumb(it,40)}<p><b>${esc(it.name)}</b><small>${esc(sub)}</small><small class="dc-held-hint">${hint}</small></p>
    <span class="dc-held-go">${S.held.src==='shop'?btn('🎒 Mua cất túi','buyBag',{},'ghost small',it.price>v.ready?' disabled':''):''}${btn('Thôi','unhold',{},'ghost small')}</span></div>`;
}
/** The selected piece's buttons (one string each: easy to add one). */
function toolButtons(v,p,it){
  const tb=(label,op,tip,cls='')=>btn(label,op,{uid:p.id},`ghost small${cls}`,` title="${esc(tip)}" aria-label="${esc(tip)}"`);
  const layered=it.spot==='wall'||it.spot==='rug'||!!p.on,out=[tb('⇋ Lật','flip','Lật ngược'),tb('🎨 Màu','tint','Đổi màu')];
  if(layered)out.push(tb('⬆ Lên','zup','Đưa lên trên'),tb('⬇ Xuống','zdown','Đưa xuống dưới'));
  if(v.rooms.filter(r=>it.rooms.includes(r.type)).length>1)out.push(tb('🚪 Đổi phòng','move','Sang phòng khác'));
  out.push(tb('🎒 Cất túi','pick','Thu hồi vào túi'),tb(`💰 Bán · ${xu(it.sell)}`,'sell',`Bán lại · ${xu(it.sell)}`,' danger'));
  return out;
}
function tools(v){
  const p=placed(S.sel),it=ITEM(p?.k);if(!it)return '';
  return `<div class="dc-tools" role="toolbar" aria-label="${esc(it.name)}"><span class="dc-tools-name">${A.thumb(it,36,tintOf(p.id))}<b>${esc(it.name)}</b></span><span class="dc-tools-go">${toolButtons(v,p,it).join('')}</span></div>`;
}
function drawer(v){
  const C=CD(),types=new Set(v.rooms.map(r=>r.type)),rm=roomOf(S.room);
  const fits=it=>it.rooms.some(t=>types.has(t)),here=it=>rm&&it.rooms.includes(rm.type);
  let cards='',cats=new Set();
  if(S.drawer==='skin')cards=skinStrip(v,rm);
  else if(S.drawer==='bag'){
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
  const chips=S.drawer==='skin'?[]:[['','Tất cả'],...C.cats.filter(c=>cats.has(c.id)).map(c=>[c.id,`${c.emoji} ${c.name}`])];
  return `<section class="dc-drawer" aria-label="Đồ đạc">
    <div class="dc-drawer-top"><div class="segmented dc-seg" role="tablist">${[['bag',`🎒 Túi · ${v.bag.length}`],['shop','🛒 Cửa hàng'],['skin','🎨 Tường & sàn']].map(([id,l])=>`<button type="button" role="tab" aria-selected="${S.drawer===id}" class="${S.drawer===id?'active':''}" data-dc="drawer" data-d="${id}">${l}</button>`).join('')}</div>
    <span class="dc-money" title="Tài khoản + ví">💰 ${xu(v.ready)}</span></div>
    ${chips.length>2?`<div class="dc-cats">${chips.map(([id,l])=>`<button type="button" class="dc-catchip${S.cat===id?' on':''}" data-dc="cat" data-cat="${id}" aria-pressed="${S.cat===id}">${l}</button>`).join('')}</div>`:''}
    ${S.drawer==='skin'?cards:`<div class="dc-strip" role="list">${cards}</div>`}</section>`;
}
/** 🎨 the wallpapers and floors this room may take, as swatches. */
function skinStrip(v,rm){
  if(!rm)return '';
  const owned=new Set(v.owned||[]),all=CD().skins||[];
  const fitsSkin=(s,part)=>{
    if(s.part!==part&&s.part!=='both')return false;
    if(part==='wall'&&(rm.out||!rm.wrows))return false;
    if(s.id==='auto')return true;
    if((CD().no_skin||[]).includes(rm.type))return false;
    return s.types?s.types.includes(rm.type):!['bunk','yard'].includes(rm.type);
  };
  const row=(part,title)=>{
    const list=all.filter(s=>fitsSkin(s,part));if(list.length<2)return '';
    const cur=rm.skin?.[part==='wall'?'w':'f']||'auto';
    return `<div class="dc-skins"><h4>${title}</h4><div class="dc-strip dc-skin-strip" role="list">${list.map(s=>{
      const on=cur===s.id,mine=!s.price||owned.has(s.id),poor=!mine&&s.price>v.ready;
      return `<button type="button" role="listitem" class="dc-swatch-btn${on?' on':''}${poor?' poor':''}" data-dc="skin" data-part="${part}" data-skin="${s.id}" aria-pressed="${on}"${S.busy||poor?' disabled':''}>`
        +`${A.swatch(s.id,part,58)}<b>${esc(s.name)}</b><small>${on?'Đang dùng':mine?(s.price?'Đã có':'Miễn phí'):xu(s.price)}</small></button>`;}).join('')}</div></div>`;
  };
  const out=row('wall','Giấy dán tường')+row('floor',rm.type==='bunk'?'Ga giường':'Sàn nhà');
  return out||`<div class="dc-empty"><p>Chỗ này giữ nguyên như vậy là đẹp rồi.</p></div>`;
}
function card(it,src,badge,sub,off=false,poor=false){
  const on=S.held&&S.held.k===it.id&&S.held.src===src;
  return `<button type="button" role="listitem" class="dc-buycard${on?' on':''}${off?' off':''}${poor?' poor':''}" data-dc="hold" data-k="${it.id}" data-src="${src}"${S.busy||off?' disabled':''} aria-pressed="${!!on}">
    <span class="dc-card-pic">${A.thumb(it,58,src==='bag'?tintOf(V()?.bag.find(b=>b.k===it.id)?.id):null)}</span>${badge}<b>${esc(it.name)}</b><small>${esc(sub)}</small></button>`;
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
    `Ấm cúng từ ${C.guest_min} điểm thì hàng xóm hay ghé chơi khen phòng.`,'Từ 24 điểm, bé mèo Bơ dọn tới ở cùng Mochi.'].filter(Boolean);
  const guest=`<details class="dc-why"><summary>Điểm tính thế nào?</summary><ul>${why.map(t=>`<li>${esc(t)}</li>`).join('')}</ul></details>`;
  return `<section class="bk-card dc-cozy${S.cheer?' cheer':''}"><div class="dc-cozy-top"><span class="dc-mochi-wrap">${A.mascot(lv,68)}</span><div class="grow"><small>Ấm cúng</small><b><span class="dc-num">${c.total}</span> ${esc(c.level)}</b><p class="dc-say">${esc(SAY[lv])}</p></div></div>
    <div class="dc-meter" role="meter" aria-label="Ấm cúng" aria-valuemin="0" aria-valuemax="${MAXC}" aria-valuenow="${Math.min(MAXC,c.total)}"><i style="width:${Math.min(100,c.total/MAXC*100)}%"></i>${marks}</div>
    <p class="dc-break"><span>Đồ đạc ${c.items}</span><span>Bộ góc ${c.sets}</span>${own?`<span>Nâng cấp nhà ${c.up}</span>`:''}</p>
    ${perk}${next}${guest}</section>`;
}
/** 🏊 the pool's and the bathroom's moment of the day (game/relax.py), under the room it belongs to. */
function relaxCard(v,rm){
  const acts=(v.relax||[]).filter(a=>a.room===rm.id);if(!acts.length)return '';
  const row=a=>`<li>${btn(`${a.emoji} ${esc(a.name)}`,'relax',{act:a.id},a.ok?'primary':'ghost',a.ok?'':' disabled')}<small>${a.done?'✓ Hôm nay rồi':a.ok?`😊 Tinh thần +${a.spirit}`:esc(a.why)}</small></li>`;
  return `<section class="bk-card dc-relax"><h3>${rm.type==='pool'?'🏖️ Thư giãn bên hồ':'🛁 Thư giãn trong nhà tắm'}</h3><ul>${acts.map(row).join('')}</ul><p class="bk-hint">Miễn phí, mỗi ngày một lần.</p></section>`;
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
  const theirs=mates();
  const mate=theirs.length?`<p class="dc-mate-note">💞 Có cả đồ ${esc(S.mate.name)} bày (${theirs.length} món). Món của ai người nấy dời.</p>`:'';
  return `<section class="bk-card dc-placenote">${note?`<p>${note}</p>`:''}${mate}<p class="bk-hint">Dọn đi đâu, đồ đạc cũng tự gói vào túi đồ. Mua một lần, mang theo cả hành trình.</p>
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
