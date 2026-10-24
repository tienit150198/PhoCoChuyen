/** 🪴 Bày trí phòng (+ 🛠️ Sửa nhà for a home you own): wherever the player lives (gác Bà Tám, phòng trọ, the dorm's
 * bunk corner, a shared home, a home they own). Every rule lives in game/deco.py (layout, coziness, sets, guests) and
 * game/reno.py (repairs); this file draws api.state.journey.deco with v4/deco-art.js and sends `jr_deco_*` /
 * `jr_reno_fix|up`. The checks below only colour the live preview: the server decides.
 * Edit mode (since 1.4, free placement): press a piece and drag it anywhere in its zone (the floor, the wall); small
 * things snap onto tables, beds, shelves and the kitchen counter and travel with them. Drag a card up out of the
 * drawer into the room, or tap a card then tap the room, or (📍 Đặt nhanh, góp ý #443: no dragging, no aiming, every
 * button named for a screen reader) tap a card then one of the ready-made spots under it. Tap a piece for its tools
 * (flip, up/down, another room, put away, sell). ♿ Chạm chọn, chạm đặt (góp ý #443, a player who uses a screen reader):
 * a chosen piece (a card, or a piece in the room) goes where the next tap on the room lands; every cell of its zone is
 * also a real <button> named by its row and column (over the drawing), the chosen piece
 * has ⬅️⬆️⬇️➡️ one-cell steps and ✕ Bỏ chọn, and one live region outside the patched page reads every choice, move and
 * refusal. Same commands as a drag. The shop and the bag filter by 🔎 name, 🆕 Mới về, a style and a
 * category, so a phone never scrolls through every piece. Undo keeps the last moves (jr_deco_layout). 🎨 Tường & sàn: wallpaper and floor per room. The cats
 * wander and nap (cosmetic; still with reduced motion). The light follows the hour of the day.
 * Pointer moves only move a transform (no re-render); a drop sends one jr_deco_put.
 * Opened from 🏠 Nhà của bạn (v4/house.js); the back button returns there. Styles: bank.css + house.css + reno.css.
 * 🎨 Màu (bảng màu): a selected piece opens the palette picker (v4/palette.js); its colour is state.colors.deco[uid]
 * (jr_wd_deco), kept by the piece in the bag and in the next home; drawn wherever the piece is (room, photo, a table).
 * 💞 A home shared with the spouse: their pieces come from GET /api/deco/mate (game/deco_mate.py) and are drawn with
 * these (room and photo), read-only: never selected or dragged, not in the bag, not in Ấm cúng, Cất hết or undo.
 * 🎨 Trang trí giúp (game/home_coop.py, F#257): a friend the owner allowed opens the owner's home here in coop mode
 * (openCoopReno): the owner's bag only, place / move / flip / turn / reorder / put back / undo, each one a POST to
 * /api/home-guests/deco/act that the server checks and logs. No shop, paints, colours, selling or Cất hết. The owner
 * sees the friends' latest changes beside the room, each with its own Hoàn tác. */
import {icon,escapeHTML as esc} from '../icons.js';
import {Sound} from '../audio.js';
import * as A from './deco-art.js';
import {encodePhoto} from './photo-encode.js';
import {petInner,lookup as petLookup} from './pet-art.js';   // 🐾 the player's own pets live here too (game/pets.py)
import {setup as walkSetup} from './home-walk.js';
import {live} from './live.js';
import {sharedRooms,ownershipOrder,guestSession} from './home-view.js';
import {morph,railScroll,railRestore} from './home-morph.js';
import {zoomer} from './home-zoom.js';   // 🔍 phóng to, thu nhỏ căn phòng
// 👶 Bé nhà mình: the babies at home, their moments, "Bế bé đi chơi" (game/cradle.py)
import * as BB from './baby.js';
import {babyRoom,babyPortrait} from './baby-art.js';
import {flagSVG} from './bang-tag.js';   // ⚔️ 🚩 the bang's flag on the wall of my first room, while I am in that bang
import {t as tr} from './i18n.js';

const S={dlg:null,env:null,tab:'deco',room:'',edit:false,held:null,sel:'',drawer:'bag',cat:'',style:'',q:'',qTimer:0,busy:false,flash:null,
  undo:[],undoKey:'',press:null,drag:null,dragEnd:0,resetStrip:false,toTop:false,pop:'',cheer:false,photo:null,listening:false,lastLv:-1,
  try:null,nudge:null,tryTint:null,saidFlash:null,tapEnd:0,refocus:'',focusNext:[],mate:null,mateState:null,mateKey:'',mateTimer:0,mateSeq:0,coop:false,coopLog:null,coopSeq:0,troPick:''};
const guest=guestSession(S);
const ZM=zoomer();
let openSeq=0;
const readGuest=code=>S.env.api.json(`/api/home-guests/${S.coop?'deco/':''}view?code=${encodeURIComponent(code)}`);
/** 🎨 The only commands a friend decorating a home sends, as home_coop actions. */
const COOP={jr_deco_put:'put',jr_deco_pick:'pick',jr_deco_layout:'layout'};
// 'floor' only switches which villa floor's rooms the rail shows (F#280: a housemate could not reach floor 2).
const VISIT_OPS=new Set(['scroll','close','back','room','floor','guests','hwEmote','hwReply','zoom']);
const COOP_OPS=new Set([...VISIT_OPS,'floor','edit','done','drawer','cat','style','unfilter','hold','unhold','spot','cell','step','unsel','move','flip','pin','turn','zup','zdown','pick','undo','tipOk']);
const post=(url,body)=>S.env.api.json(url,{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':S.env.api.csrf},body:JSON.stringify(body)});
const U=A.U;
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const low=s=>String(s||'').slice(0,1).toLowerCase()+String(s||'').slice(1);
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
// The rail arrows (‹ ›) stay live while a command is out: scrolling the drawer changes nothing on the server.
const btn=(label,op,data={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-dc="${op}"${attrs(data)}${S.busy&&op!=='scroll'&&op!=='zoom'?' disabled':''}${extra}>${label}</button>`;
const J=()=>S.env?.api?.state?.journey||{};
/* The place you live in, its rooms and pieces (deco.public). 1.4.11: the new rooms (the bathroom, a villa's pool) come
 * as `more` [{t: template, s: skin}] with the templates in the catalogue (`kits`); here they join `rooms`. */
let vSrc=null,vOut=null;
const V=()=>{const d=(S.remote?S.remote.deco:J().deco)||null;if(!d)return d;
  if(vSrc!==d){const kits=CD().kits||{};vSrc=d;vOut={...d,rooms:[...d.rooms,...(d.more||[]).filter(m=>kits[m.t]).map(m=>({...kits[m.t],skin:m.s||{},...(m.fl?{fl:m.fl}:{})}))]};}
  return S.mate?.at===d.place?.key?{...vOut,rooms:sharedRooms(vOut.rooms,S.mate)}:vOut;};
/** The latest verified common-home capabilities, valid only for the player's current state snapshot. */
const useV=()=>{const v=V(),m=S.mate;return !S.remote&&v&&m?.at===v.place?.key&&S.mateState===S.env?.api?.state&&m.use?{...v,...m.use}:v;};
const R=()=>(S.remote?S.remote.reno:J().reno)||null;                       // the structure of a home you own (reno.public)
const CD=()=>S.env?.api?.content?.journey?.deco||{items:[],cats:[],sets:[],levels:[],skins:[]};
const CR=()=>S.env?.api?.content?.journey?.reno||{parts:[],steps:[]};
let itemMap=null,itemSrc=null;
const ITEM=k=>{const list=CD().items;if(itemSrc!==list){itemSrc=list;itemMap=new Map(list.map(i=>[i.id,i]));}return itemMap.get(k);};
const SKIN=id=>(CD().skins||[]).find(s=>s.id===id)||null;
const PART=id=>CR().parts.find(x=>x.id===id)||{};
/** 🧰 A piece a player restorer made "cổ điển" (journey.restored, game/restore_service.py): an aged patina, nothing else. */
const aged=uid=>!S.remote&&!!S.env?.api?.state?.journey?.restored?.['decor:'+uid];
const AGED=' style="filter:sepia(.55) saturate(.8) contrast(1.04)"';
const agedBy=uid=>S.env?.api?.state?.journey?.restored?.['decor:'+uid]?.by||'';
/** A piece's colour: the one being tried in the picker, else its own from the palette (state.colors.deco). */
const tintOf=uid=>S.tryTint?.uid===uid?S.tryTint.c:(S.remote?S.remote.colors:S.env?.api?.state?.colors)?.deco?.[uid]||null;
const POCKET=['account','wallet'];
const condWord=(c,p)=>c>=85?'Như mới':c>=65?'Còn tốt':c>=45?'Hơi cũ':(PART(p).flaw||'Xuống cấp');
const tone=c=>c>=65?'good':c>=45?'warn':'bad';
const MAXC=40;                                    // the meter's end: Tổ ấm trong mơ
const SAY=['Phòng hơi trống… Mochi buồn ngủ quá.','Bắt đầu dễ thương rồi nè!','Ấm áp ghê, Mochi thích lắm!','Wow, phòng xinh quá trời!','Tổ ấm trong mơ! Mochi không muốn đi đâu hết.'];
const TIP_KEY='mnl.decoTip2';
const tipSeen=()=>{try{return localStorage.getItem(TIP_KEY)==='1';}catch{return false;}};
const tipDone=()=>{try{localStorage.setItem(TIP_KEY,'1');}catch{/* private window: the tip just shows again */}};
/* 📌 Ghim (F#224): a pinned piece never starts a drag in edit mode (this device; no save key, so older builds are unaffected). */
const PIN_KEY='mnl.decoPins';let PINS=null;
const pins=()=>PINS??=(()=>{try{const a=JSON.parse(localStorage.getItem(PIN_KEY)||'[]');return new Set(Array.isArray(a)?a.filter(x=>typeof x==='string'):[]);}catch{return new Set();}})();
const isPinned=uid=>!!uid&&pins().has(uid);
function togglePin(uid){const s=pins();if(s.has(uid))s.delete(uid);else s.add(uid);try{localStorage.setItem(PIN_KEY,JSON.stringify([...s].slice(-300)));}catch{/* private window: kept for this visit */}return s.has(uid);}
const DRAG_PX=12;   // a press must travel this far before a placed piece follows the finger (was 6: pieces moved by accident)
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
  d.innerHTML='<div class="dc-root"></div><p class="sr-only dc-live" role="status" aria-live="polite" aria-atomic="true"></p>';   // ♿ say()
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    // ♿ a piece activated by TalkBack, Switch Access or a voice command: a click with no finger or mouse before it
    const g=e.target.closest?.('svg.dc-room g[data-uid]');
    if(g&&!S.drag&&!S.press&&Date.now()-S.tapEnd>700&&Date.now()-S.dragEnd>450){e.preventDefault();
      if(S.edit)choose(g.dataset.uid);else hw().tap(roomOf(S.room),{x:0,y:0},g.dataset.uid);return;}
    const el=e.target.closest('[data-dc]');if(!el||!d.contains(el)||el.disabled)return;
    if(S.drag||Date.now()-S.dragEnd<450)return;   // the click that ends a drag
    e.preventDefault();onClick(el.dataset.dc,el.dataset);
  });
  d.addEventListener('keydown',onKey);
  d.addEventListener('input',e=>{   // 🔎 the drawer's search: a short pause, then the cards follow (morph keeps the field's focus)
    const f=e.target.closest?.('[data-dc-search]');if(!f)return;
    S.q=f.value.slice(0,40);clearTimeout(S.qTimer);S.qTimer=setTimeout(()=>{S.resetStrip=true;render();},160);
  });
  d.addEventListener('wheel',e=>{if(S.tab==='deco'&&!S.photo&&e.target.closest?.('.dc-roomwrap'))ZM.wheel(d,e);},{passive:false});   // 🔍
  d.addEventListener('pointerdown',onDown);
  d.addEventListener('pointermove',onMove);
  d.addEventListener('pointerup',onUp);
  d.addEventListener('pointercancel',onCancel);
  d.addEventListener('cancel',e=>{if(S.held||S.sel){e.preventDefault();const c=chosen();S.held=null;S.sel='';if(c)say(`Đã bỏ chọn ${low(c.it.name)}.`);render();}});
  d.addEventListener('close',()=>{clearTimeout(sayT);sayBuf=[];openSeq++;ZM.reset();S.flash=null;S.held=null;S.sel='';S.photo=null;S.drag=null;S.press=null;S.try=null;clearTimeout(S.mateTimer);S.mateTimer=0;S.mateSeq++;floatGhost(null);catsStop();hw().reset();S.coop=false;S.coopSeq++;guest.close();});
  S.dlg=d;return d;
}

/** 📸 The framed photos of journey.photo_wall (game/photo_studio.py hang): their pictures for deco-art.js PHOTO_ART, then
 * the room again. Own home only (a guest's view keeps the frame's soft silhouette). */
function framedPhotos(){
  const wall=J().photo_wall;if(!wall||typeof wall!=='object'||!Object.keys(wall).length)return;
  import('./portrait.js').then(m=>m.loadWall(S.env,wall,(uid,url)=>{if(A.PHOTO_ART.get(uid)===url)return false;A.PHOTO_ART.set(uid,url);return true;},
    ()=>{if(S.dlg?.open&&!S.busy&&!S.drag&&!S.press)render();})).catch(e=>console.warn('ảnh treo:',e));
}
/** 🎣 The fish of journey.fish (game/fishing.py): each tranh cá's catch by its uid (tro) and the aquarium's (aq), as the
 * species of content.journey.fish, for deco-art.js FISH_TRO / AQUA. Own home only, like the photos. */
function fishPieces(){
  const f=J().fish,list=S.env?.api?.content?.journey?.fish?.species;A.FISH_TRO.clear();A.AQUA.length=0;
  if(!f||typeof f!=='object'||!Array.isArray(list))return;
  const by=new Map(list.map(s=>[s.id,s]));
  for(const [uid,v] of Object.entries(f.tro&&typeof f.tro==='object'?f.tro:{}))if(Array.isArray(v)&&by.has(v[0]))A.FISH_TRO.set(uid,{sp:by.get(v[0]),g:Number(v[1])||0,bg:typeof v[2]==='string'?v[2]:'kem'});
  for(const v of Array.isArray(f.aq)?f.aq:[])if(Array.isArray(v)&&by.has(v[0]))A.AQUA.push(by.get(v[0]));
}
export async function openReno(env,mode,guestCode=''){
  const seq=++openSeq;
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';
    env.api.addEventListener('state',()=>{const j=S.env.api.state?.journey,sp=S.env.api.state?.marriage?.spouse;const key=JSON.stringify([j?.deco,j?.reno,j?.wallet,S.env.api.state?.colors?.deco,sp,j?.fish?.tro,j?.fish?.aq]);if(key===seen)return;seen=key;
      if(!S.remote)fishPieces();
      if(S.dlg?.open)refreshMate();
      if(S.dlg?.open&&!S.busy&&!S.drag&&!S.press)render();});
    live.on('home_changed',()=>{refreshMate();loadCoopLog();});
    live.on('home_guests_changed',refreshMate);
    live.on('welcome',refreshMate);
    document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')refreshMate();});
  }
  await ensureCss();
  if(seq!==openSeq)return;
  const d=dialog();
  clearTimeout(S.mateTimer);S.mateSeq++;hw().reset();
  if(guestCode){
    clearTimeout(S.nudge?.t);S.nudge=null;
    S.coop=mode==='coop';
    if(!await guest.open(guestCode,readGuest)||seq!==openSeq)return;
    if(S.coop){S.undo=[];S.undoKey='';S.drawer='bag';}
  }else{S.coop=false;guest.close();}
  S.tab=mode==='fix'&&R()?'fix':'deco';S.edit=mode==='decor'||S.coop;S.held=null;S.sel='';S.flash=null;S.photo=null;S.cat='';S.style='';S.q='';S.try=null;
  const v=V();
  if(v){if(!v.rooms.some(r=>r.id===S.room))S.room=v.rooms[0]?.id||'';if(!S.remote)S.drawer=v.bag.length?'bag':'shop';}
  if(v&&!guestCode&&typeof mode==='string'&&mode.startsWith('room:')&&v.rooms.some(r=>r.id===mode.slice(5)))S.room=mode.slice(5);   // 🗺️ Tổng quan nhà: a room tapped (v4/home-overview.js)
  if(!d.open){d.showModal();d.scrollTop=0;S.toTop=true;}
  hw().reopen();
  if(!guestCode)framedPhotos();
  if(guestCode){A.FISH_TRO.clear();A.AQUA.length=0;}else fishPieces();   // 🎣 a guest sees a host's tranh cá as its shadow
  loadMate();loadHostGrant();   // its first lines run now: a room that is not shared any more drops the spouse's pieces before drawing
  render();
  if(!S.remote){loadCoopLog();BB.css();BB.loadFamily(env.api).then(()=>{if(seq!==openSeq||!S.dlg?.open||S.remote)return;render();BB.greet(env,{here:true});});}   // 👶
}
export const openGuestReno=(env,code)=>openReno(env,'visit',code);
/** 🎨 A friend's home that its owner lets you decorate (home_coop): opens straight into decorating. */
export const openCoopReno=(env,code)=>openReno(env,'coop',code);
/** 🎨 Your friends' latest changes to your home (GET /api/home-guests/deco/log), for the card beside the room. */
async function loadCoopLog(){
  if(S.remote||!S.dlg?.open||!S.env)return;
  const seq=++S.coopSeq;
  if(!['own','estate'].includes(V()?.place?.where)){if(S.coopLog){S.coopLog=null;render();}return;}   // 🏰 a villa you live in too
  let d;try{d=await S.env.api.json('/api/home-guests/deco/log');}catch{return;}
  if(seq!==S.coopSeq||S.remote||!S.dlg?.open)return;
  const changed=JSON.stringify(S.coopLog)!==JSON.stringify(d);S.coopLog=d;
  if(changed&&!S.busy&&!S.drag&&!S.press)render();
}
/** 🎨 The owner puts back what one friend change moved (POST deco/undo), then reads the home again. */
async function coopUndo(id){
  if(!Number.isInteger(id)||id<=0||S.remote)return;
  S.busy=true;paintBusy();
  try{const r=await post('/api/home-guests/deco/undo',{id});if(r.deco)S.coopLog=r.deco;S.flash={text:r.message||'Đã hoàn tác.',kind:'good'};sfx('pop');
    try{await S.env.api.refresh();}catch{/* the next command catches up */}}
  catch(e){S.flash={text:e.message||'Chưa hoàn tác được. Thử lại nhé.',kind:'bad'};sfx('error');}
  finally{S.busy=false;render();}
}
/** 💞 The spouse's pieces when this is the home both live in (each time the room opens, and after a move).
 * 🏡 F#307: also the friends living in your home, or, in a friend's home you moved into, everyone else's. */
const married=()=>S.env.api.state?.marriage?.spouse?.status==='married';
function refreshMate(){
  if(!S.dlg?.open)return;
  if(S.remote){clearTimeout(S.mateTimer);S.mateTimer=setTimeout(loadMate,120);return;}
  if((J().deco?.place?.key||'')!==S.mateKey||(!married()&&!S.mate?.stay)){S.mate=null;S.mateState=null;}
  clearTimeout(S.mateTimer);S.mateTimer=setTimeout(loadMate,120);
}
async function loadMate(){
  clearTimeout(S.mateTimer);S.mateTimer=0;
  if(S.remote){
    try{const was=JSON.stringify(S.remote);if(await guest.refresh(readGuest)&&JSON.stringify(S.remote)!==was&&S.dlg?.open&&!S.drag&&!S.press)render();}   // 23/10 lag: the 5 s visit poll redraws the whole room (every piece and figure) only when the host's home changed
    catch(e){
      if([401,403,404,409,410].includes(e.status)){S.dlg?.close();S.env.toast?.(e.message||'Lời mời vào nhà đã hết hiệu lực.','hint');return;}
    }
    if(S.remote&&S.dlg?.open)S.mateTimer=setTimeout(loadMate,5000);
    return;
  }
  const v=V(),key=v?.place?.key||'',seq=++S.mateSeq,state=S.env.api.state;S.mateKey=key;
  const where=v?.place?.where;
  if(!v||!['own','shared','estate','stay'].includes(where)||(where==='shared'&&!married())){S.mate=null;S.mateState=null;return;}
  let m=null,failed=false;
  try{m=await S.env.api.json('/api/deco/mate');}catch{failed=true;}
  if(S.mateKey!==key||seq!==S.mateSeq)return;   // moved or reopened meanwhile: the newer request decides
  if(m?.moved){S.mate=null;S.mateState=null;S.env.api.refresh?.().then(()=>{if(S.dlg?.open)render();}).catch(()=>{});return;}   // 🏡 the stay ended: the pieces are back in the bag
  const next=failed&&S.mate?.at===key?S.mate:m&&m.at===key&&Array.isArray(m.items)?m:null,changed=JSON.stringify(S.mate)!==JSON.stringify(next);S.mate=next;S.mateState=!failed&&S.env.api.state===state?state:null;
  if(changed&&S.dlg?.open&&!S.busy&&!S.drag&&!S.press)render();
  // Someone else lives here: ask again in 30 s while the room is open and the page visible (also after each own deco
  // command, on home_changed and when the page shows again). Nobody else: once per opening.
  if(S.dlg?.open&&(next||where==='stay'))S.mateTimer=setTimeout(pollMate,MATE_POLL);
}
const MATE_POLL=30000;
function pollMate(){S.mateTimer=0;if(S.dlg?.open&&document.visibilityState==='visible')loadMate();}   // hidden: the visibilitychange listener asks again

async function send(action,payload={},opts={}){
  if(S.remote)return S.coop&&COOP[action]?coopSend(action,payload,opts):null;
  const {api}=S.env;S.busy=true;paintBusy();
  try{
    const r=await api.command(action,payload);
    if(action.startsWith('jr_deco_')||action.startsWith('jr_reno_')||action==='jr_wd_deco')await loadMate();
    S.flash=opts.flash===false?null:r.duplicate&&!opts.loud?S.flash:{text:[r.message,...(r.effects||[]).filter(Boolean)].filter(Boolean).join(' '),kind:'good'};
    return r;
  }catch(e){
    if(!e.quiet){S.flash={text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};if(!opts.silent)sfx('error');}
    return null;
  }finally{S.busy=false;render();}
}
/** 🎨 A friend's change: the server checks the permission, applies it to the owner's save and logs it; the view that
 * comes back is the owner's room as it is now. A permission that ended closes the room. */
async function coopSend(action,payload,opts){
  const code=guest.code;S.busy=true;paintBusy();
  try{
    const r=await post('/api/home-guests/deco/act',{...payload,code,action:COOP[action]});
    if(r.view)guest.adopt(code,r.view);
    S.flash=r.duplicate&&!opts.loud?S.flash:{text:r.message||'',kind:'good'};
    return r;
  }catch(e){
    if([401,403,404,410].includes(e.status)){S.busy=false;S.dlg?.close();S.env.toast?.(e.message||'Quyền trang trí đã kết thúc.','hint');return null;}
    S.flash={text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};if(!opts.silent)sfx('error');
    return null;
  }finally{S.busy=false;if(S.dlg?.open)render();}
}
const ask=(title,msg,label,cost)=>S.env.confirmAction(title,msg,label,cost?{cost,pocket:POCKET}:undefined);
/** 🚶 the character walking around the room when not decorating (v4/home-walk.js), made on first use. */
let HW=null;
const hw=()=>HW??=walkSetup({S,A,V:useV,roomOf,inRoom,mateIn,hostFor,send,render,sfx,calm,roomSvg,live,babyAt,
  babyCard:()=>{const el=S.dlg?.querySelector('#dc-baby-card');el?.scrollIntoView?.({block:'nearest',behavior:calm()?'auto':'smooth'});el?.querySelector('[data-dc="bbMoment"]:not([disabled]),[data-dc="bbCarry"]')?.focus?.({preventScroll:true});}});

/* ---- the layout, as the client sees it (free units; game/deco.py check) ---- */
const roomOf=id=>(V()?.rooms||[]).find(r=>r.id===id)||null;
const items=()=>V()?.items||[];
const placed=uid=>items().find(i=>i.id===uid)||null;
/** ↻ How a piece (placed or in the bag) is turned: 0..3 (game/deco.py `rot`); a server from before sends only `face`. */
const rotOf=p=>Number.isInteger(p?.rot)&&p.rot>0&&p.rot<4?p.rot:p?.face==='back'?2:0;
/** The catalogue item as it stands: its footprint turned with it (deco-art.js turn). */
const itemOf=p=>A.turn(ITEM(p?.k),rotOf(p));
/** A piece's turn may change: a floor piece or a rug standing on the floor (the server's deco.turns). */
const canTurn=(it,p)=>!!it&&!p?.on&&(it.spot==='floor'||it.spot==='rug'||(CD().facing||[]).includes(it.id));
const ROT_WORD=['mặt trước','quay phải','mặt sau','quay trái'];
/** A placed piece as the server keeps it: {r, x, y, f[, on][, z][, rot]} in units. */
function qOf(p){const q={r:p.r,x:p.fx??p.x*U,y:p.fy??p.y*U,f:p.f||0};if(p.on)q.on=p.on;if(p.z)q.z=p.z;const t=rotOf(p);if(t)q.rot=t;return q;}
const sameQ=(a,b)=>!!a&&!!b&&a.r===b.r&&a.x===b.x&&a.y===b.y&&(a.f||0)===(b.f||0)&&(a.on||'')===(b.on||'')&&(a.z||0)===(b.z||0)&&(a.rot||0)===(b.rot||0);
/** Everything in room `rm` as {id, k, it, q}, without `skip` (`it` turned as the piece stands). */
function inRoom(rm,skip=new Set()){return items().filter(p=>p.r===rm.id&&!skip.has(p.id)&&ITEM(p.k)).map(p=>({id:p.id,k:p.k,it:itemOf(p),q:qOf(p)}));}
const ridersOf=uid=>items().filter(p=>p.on===uid).map(p=>p.id);
/** 💞 The spouse's pieces in this home (ids 'p:…'), read-only: drawn, never part of the checks above. */
const mates=()=>S.mate&&S.mate.at===V()?.place?.key?S.mate.items:[];
function mateIn(rm){return mates().filter(p=>p.r===rm.id&&ITEM(p.k)).map(p=>({id:p.id,k:p.k,it:itemOf(p),q:qOf(p),mate:true,c:p.c||null,n:p.n||''}));}
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
/** The room is full (game/deco.py room_cap): the real number and how to get more room. */
const roomFull=rm=>`${rm.name} đã bày đủ ${rm.cap} món, mức tối đa của phòng này. Muốn bày thêm: cất bớt món ít dùng vào túi đồ, bày sang phòng khác, hoặc dọn về nhà rộng hơn (phòng càng rộng càng bày được nhiều).`;
function whyText(bad,rm,it){
  const FX=CD().fix_names||{};
  if(bad.code==='fixture')return `Chỗ này vướng ${FX[bad.f.t]||'chỗ cố định'}.`;
  if(bad.code==='host_full')return 'Trên đó hết chỗ rồi. Đặt chỗ khác nhé.';
  if(bad.code==='room_full')return roomFull(rm);
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
  // anywhere, as before 2.6.0 (no snap grid)
  const q={r:rm.id,x:clamp(Math.round(x),0,z[0]),y:clamp(Math.round(y),0,z[1]),f};if(it.rot)q.rot=it.rot;return q;
}
const heldItem=()=>S.held?A.turn(ITEM(S.held.k),S.held.rot||0):null;
const roomsFor=it=>(V()?.rooms||[]).filter(r=>it.rooms.includes(r.type));
/** Where the finger holds a piece that comes from the drawer: its base a little above the finger. */
function grabFor(it){const W=it.w*A.CW;return it.spot==='wall'?[W/2,it.h*A.WR+8]:[W/2,6];}

/* ---- ♿ chạm chọn, chạm đặt (góp ý #443): no dragging, every spot named, every change read out ---- */
/** The screen reader's voice: one polite live region outside the patched page (a redraw never cuts a sentence off).
 * Lines said in the same moment are read together; the same line twice is read twice. */
let sayBuf=[],sayT=0;
function say(text){
  if(!text||!S.dlg)return;
  sayBuf.push(String(text));clearTimeout(sayT);
  sayT=setTimeout(()=>{const el=S.dlg?.querySelector?.('.dc-live'),t=[...new Set(sayBuf)].join(' ');sayBuf=[];if(!el)return;el.textContent='';setTimeout(()=>{el.textContent=t;},50);},60);
}
/** The piece a tap on the room puts down: the one held (from the drawer, or being moved), else the chosen placed one. */
function chosen(){
  if(S.held){const it=heldItem();return it?{it,uid:S.held.uid||'',src:S.held.src}:null;}
  const p=S.sel?placed(S.sel):null,it=p&&itemOf(p);return it?{it,uid:p.id,src:'sel'}:null;
}
/** Where a piece stands, in words: "hàng 2 cột 3" (hàng 1 at the back of the floor / the top of the wall, cột 1 on the
 * left), "tường hàng 1 cột 3", "trên bàn trà". */
function spotName(rm,it,q,list){
  if(q.on){const h=hostFor(rm,q,list);return `trên ${h?.fix?(CD().fix_names||{})[h.fix.t]||'kệ có sẵn':h?.it?low(h.it.name):'kệ có sẵn'}`;}
  const cell=`hàng ${Math.round(q.y/U)+1} cột ${Math.round(q.x/U)+1}`;
  return it.spot==='wall'?`tường ${cell}`:cell;
}
const posOf=p=>{const rm=roomOf(p?.r),it=itemOf(p);return rm&&it?spotName(rm,it,qOf(p),inRoom(rm)):'';};
const placedName=p=>`${ITEM(p.k)?.name||''}, ${posOf(p)}`;
/** After a move or a placing: where the piece is now. */
function sayWhere(uid){const p=placed(uid),it=ITEM(p?.k);if(it)say(`${it.name} giờ ở ${posOf(p)}.`);}
/** Choose a placed piece (a tap, Enter), or let go of it when it is the chosen one already. */
function choose(uid,toggle=true){
  const p=placed(uid);if(!p)return;
  if(S.sel===uid&&toggle){S.sel='';say(`Đã bỏ chọn ${low(ITEM(p.k)?.name)}.`);}
  else{S.held=null;S.sel=uid;say(`Đã chọn ${placedName(p)}. ${isPinned(uid)?'Món này đang ghim, bỏ ghim để dời.':'Chạm chỗ muốn đặt.'}`);}
  sfx('click');render();
}
/** Put the chosen piece at `q` (a tap, a cell, a named spot): the held one as dropAt, the chosen placed one moved. */
async function placeChosen(q){
  if(S.held)return dropAt(q);
  const p=S.sel?placed(S.sel):null,it=itemOf(p),rm=roomOf(q?.r);if(!p||!it||!rm)return;
  if(isPinned(p.id)){S.flash={text:'Món này đang ghim. Bỏ ghim rồi dời nhé.',kind:'warn'};sfx('error');render();return;}
  const bad=checkQ(rm,it,q,inRoom(rm,new Set([p.id,...ridersOf(p.id)])));
  if(bad){S.flash={text:whyText(bad,rm,it),kind:'warn'};sfx('error');render();return;}
  const to={...q,f:p.f||0};if(p.z)to.z=p.z;if(rotOf(p)&&!q.on)to.rot=rotOf(p);
  if(sameQ(to,qOf(p))){say(`${it.name} đang ở đó rồi.`);return;}
  await putPiece(p.id,to);
}
/** A spot `q` moved inside its zone (or inside what it stands on). */
function clampQ(rm,it,q,list){
  if(q.on){const h=hostBox(rm,q.on,list);return h?{...q,x:clamp(q.x,0,Math.max(0,h.w-it.w*U)),y:clamp(q.y,0,Math.max(0,h.d-it.h*U))}:q;}
  const z=zoneOf(rm,it);return z?{...q,x:clamp(q.x,0,z[0]),y:clamp(q.y,0,z[1])}:q;
}
const EDGE={l:'Đã sát mép trái rồi.',r:'Đã sát mép phải rồi.',u:'Đã sát mép trên rồi.',d:'Đã sát mép dưới rồi.'};
/** ⬅️⬆️⬇️➡️ one cell for the chosen piece; a door or a window in the way: on to the next cell it may stand on. Steps
 * pressed quickly go as one move (like the arrow keys). */
function step(p,dx,dy){
  const rm=roomOf(p.r),it=itemOf(p);if(!rm||!it)return;
  if(isPinned(p.id)){S.flash={text:'Món này đang ghim. Bỏ ghim rồi dời nhé.',kind:'warn'};sfx('error');render();return;}
  const list=inRoom(rm,new Set([p.id,...ridersOf(p.id)])),from=S.nudge?.uid===p.id?S.nudge.q:qOf(p);
  let last=from,bad=null,to=null;
  for(let i=1;i<=24&&!to;i++){
    const t=clampQ(rm,it,{...from,x:from.x+dx*U*i,y:from.y+dy*U*i},list);
    if(t.x===last.x&&t.y===last.y)break;   // the edge
    last=t;bad=checkQ(rm,it,t,list);if(!bad)to=t;
  }
  if(!to){S.flash={text:bad?whyText(bad,rm,it):EDGE[dx<0?'l':dx>0?'r':dy<0?'u':'d'],kind:'warn'};sfx('error');render();return;}
  nudgeTo(p,to,false);
}
/** ♿ The cells of the zone the chosen piece may take in `rm`, each a real button named by its row and column and what
 * is there ("hàng 2 cột 3, trống", "…, có ghế gỗ", "…, vướng cửa sổ"): over the drawing (transparent, the finger
 * still reaches the drawing under them). A cell is the piece's back left corner. */
function cellsMarkup(rm,c){
  const it=c?.it;if(!rm||!it||!it.rooms.includes(rm.type))return '';
  const z=zoneOf(rm,it);if(!z)return '';
  const list=inRoom(rm,new Set(c.uid?[c.uid,...ridersOf(c.uid)]:[]));if(list.length>=rm.cap)return '';
  const G=A.geom(rm),wall=it.spot==='wall',RH=wall?A.WR:A.FR,top=wall?G.WY:G.FY,FX=CD().fix_names||{},me=c.uid?placed(c.uid):null;
  const layer=sp=>sp==='wall'?'wall':'floor',others=list.filter(o=>!o.q.on&&layer(o.it.spot)===layer(it.spot));
  const W=it.w*U,H=it.h*U,pct=(a,b)=>`${(a/b*100).toFixed(2)}%`,cols=Math.floor(z[0]/U)+1,rows=Math.floor(z[1]/U)+1,out=[];
  for(let r=0;r<rows;r++)for(let k=0;k<cols;k++){
    const q={r:rm.id,x:k*U,y:r*U,f:me?.f||0},bad=checkQ(rm,it,q,list);
    const now=me&&me.r===rm.id&&!me.on&&Math.round(qOf(me).x/U)===k&&Math.round(qOf(me).y/U)===r;
    const has=others.filter(o=>ov(q.x,q.x+W,o.q.x,o.q.x+o.it.w*U)>0&&ov(q.y,q.y+H,o.q.y,o.q.y+o.it.h*U)>0).map(o=>low(o.it.name));
    const what=now?'đang ở đây':bad?(bad.code==='fixture'?`vướng ${FX[bad.f.t]||'chỗ cố định'}`:'không đặt được'):has.length?`có ${[...new Set(has)].join(', ')}`:'trống';
    const cls=now?' now':bad?' bad':has.length?' has':'';
    const pos=` style="left:${pct(A.PX+k*A.CW,G.W)};top:${pct(top+r*RH,G.H)};width:${pct(it.w*A.CW,G.W)};height:${pct(it.h*RH,G.H)}"`;
    out.push(`<button type="button" class="dc-cell${cls}" data-dc="cell" data-x="${q.x}" data-y="${q.y}"${pos} aria-label="${esc(`${spotName(rm,it,q,list)}, ${what}`)}"${S.busy?' disabled':''}></button>`);
  }
  const label=wall?`Chỗ đặt ${low(it.name)} trên tường: hàng 1 ở trên cùng, cột 1 bên trái`:`Chỗ đặt ${low(it.name)} trên sàn: hàng 1 ở trong cùng, cột 1 bên trái`;
  return `<div class="dc-cells over" role="group" aria-label="${esc(label)}" style="aspect-ratio:${G.W}/${G.H}">${out.join('')}</div>`;
}
/** A value inside a quoted attribute selector ([data-uid="…"]): only quotes and backslashes need escaping there. */
const attrQ=v=>String(v).replace(/["\\]/g,'\\$&');
/** ♿ Focus a redraw (or a button turning busy) took away goes back to the same control: a selector for it. */
function focusKeyOf(el){
  if(!el||el===S.dlg||!S.dlg?.contains?.(el))return '';
  if(el.matches?.('g[data-uid]'))return pieceKey(el.dataset.uid);
  if(el.matches?.('svg.dc-room'))return 'svg.dc-room';
  if(el.tagName!=='BUTTON')return '';   // a text field is never focused again by a redraw (the phone's keyboard would pop up)
  if(el.id)return `[id="${attrQ(el.id)}"]`;
  const ds=Object.entries(el.dataset||{});
  return ds.length?ds.map(([k,v])=>`[data-${k.replace(/[A-Z]/g,m=>'-'+m.toLowerCase())}="${attrQ(v)}"]`).join(''):'';
}
const pieceKey=uid=>`g[data-uid="${attrQ(uid)}"]`;

/* ---- the light of the hour: home is where you are right now, so the device's clock (a shift's clock is the shop's) ---- */
function minuteNow(){const d=new Date();return d.getHours()*60+d.getMinutes();}

/* ---- the room ---- */
function partsMap(){const v=V(),m=S.mate,r=R();if(m?.at===v?.place.key&&Array.isArray(m.parts))return Object.fromEntries(m.parts.map(p=>[p.id,p]));return r&&v?.place.where==='own'?Object.fromEntries(r.parts.map(p=>[p.id,p])):null;}
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
  return [...list].map(o=>[key(o),o]).sort((a,b)=>a[0][0]-b[0][0]||a[0][1]-b[0][1]||a[0][2]-b[0][2]||ownershipOrder(a[1],b[1],V()?.place.where==='own')).map(x=>x[1]);
}
function bbox(it,a){
  const [x,y]=a,w=it.w*A.CW,h=(A.ART[it.id]?.h||30)+4+A.lift(it);   // ↻ a turned piece reaches further back
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
  const skin={...(rm.skin0||{}),...(rm.skin||{})};if(S.try&&S.try.room===rm.id)skin[S.try.part==='wall'?'w':'f']=S.try.skin==='auto'?undefined:S.try.skin;
  const list=inRoom(rm),theirs=mateIn(rm),all=theirs.length?[...list,...theirs]:list,out=[A.roomBack(rm,G,partsMap(),Lt,uid,skin)];
  if(!S.remote&&rm.wrows&&V()?.rooms?.[0]?.id===rm.id){const fl=flagSVG(0,0);if(fl)out.push(`<g transform="translate(${G.W-A.PX-58} ${G.WY+4}) scale(${Math.min(1,rm.wrows*A.WR/80).toFixed(2)})" pointer-events="none">${fl}</g>`);}
  if(edit&&!photo&&S.held&&!S.drag)out.push(zoneMarkup(rm,heldItem(),G,list.filter(o=>o.id!==S.held.uid)));
  out.push('<g class="dc-zonelayer" pointer-events="none"></g>');
  const glows=[];
  for(const o of depthOrder(rm,all)){
    const it=o.it,a=A.anchor(it,o.q,G,hostFor(rm,o.q,all));
    const g=A.glowAt(it,a[0],a[1],o.q.f);if(g)glows.push(g);
    const body=(o.q.on?A.contact(it,a[0],a[1]):'')+A.pieceAt(it,a[0],a[1],o.q.f,o.mate?o.c:tintOf(o.id),'front',o.mate?'':o.id);
    if(photo){out.push(body);continue;}
    if(o.mate){
      const [bx,by,bw,bh]=bbox(it,a);
      out.push(edit?`<g class="dc-mate"${frontY(rm,G,o,all)} pointer-events="none" aria-hidden="true">${body}</g>`
        :`<g class="dc-mate dc-it" data-uid="${esc(o.id)}"${frontY(rm,G,o,all)} tabindex="0" role="button" aria-label="${esc(it.name)} · của ${esc(o.n||S.mate?.name||'người ấy')}">${body}<rect class="dc-hit" x="${bx}" y="${by}" width="${bw}" height="${bh}" rx="6"/></g>`);
      continue;
    }   // the spouse's may be used while walking; editing keeps every ownership control with its owner
    const [bx,by,bw,bh]=bbox(it,a);
    const sel=S.sel===o.id,pop=S.pop===o.id,ghost=S.held?.src==='room'&&S.held.uid===o.id;
    out.push(`<g class="dc-it${sel?' sel':''}${pop?' pop':''}${ghost?' ghost':''}" data-uid="${esc(o.id)}" data-k="${esc(o.k)}"${o.q.on?` data-on="${esc(o.q.on)}"`:''}${frontY(rm,G,o,list)} tabindex="0" role="button" aria-label="${esc(edit?`${it.name}, ${spotName(rm,it,o.q,all)}`:it.name)}"${edit?` aria-pressed="${sel}"`:''}><g class="dc-piece${aged(o.id)?' rs-aged':''}"${aged(o.id)?AGED:''}>${body}</g>`
      +`<rect class="dc-hit" x="${bx}" y="${by}" width="${bw}" height="${bh}" rx="6"/>${sel?`<rect class="dc-selbox" x="${bx-3}" y="${by-3}" width="${bw+6}" height="${bh+6}" rx="9"/>`:''}${pop?sparkles(bx,by,bw,bh):''}</g>`);
  }
  if(all.some(o=>o.k==='may_chieu'))out.push(A.galaxy(rm,G,Lt));   // 🌌 the star projector lights up the wall
  out.push(catsMarkup(rm,G,list,photo));
  out.push(babiesMarkup(rm,G,photo,edit));   // 👶
  if(!photo)out.push(hw().markup(rm,G));
  out.push(A.roomFront(rm,G));
  out.push(A.roomLight(G,Lt,glows,uid));
  out.push('<g class="dc-preview" pointer-events="none"></g>');
  const name=`${rm.name}: ${list.map(o=>o.it.name).join(', ')||'chưa bày gì'}`;
  return {G,svg:`<svg data-whole class="dc-room${edit?' edit':''}${S.held?' holding':''} lt-${Lt.phase}" viewBox="0 0 ${G.W} ${G.H}" role="group" aria-label="${esc(name)}" data-room="${esc(rm.id)}"${edit&&!photo?' tabindex="-1"':''}>${out.join('')}</svg>`};
}

/** ` data-y="…"`: how far forward a piece stands (its front edge; a small thing: what it stands on), for the walking
 * character's depth (v4/home-walk.js). Wall pieces and rugs: none (always behind). */
function frontY(rm,G,o,list){
  if(o.it.spot==='wall'||o.it.spot==='rug')return '';
  let y;
  if(o.q.on){const h=hostFor(rm,o.q,list);
    if(h?.fix){if(h.fix.layer==='wall')return '';y=G.FY+(h.fix.y+h.fix.h)*A.FR;}
    else if(h?.it){if(h.it.spot==='wall')return '';y=A.anchor(h.it,h.q,G,hostFor(rm,h.q,list))[1];}
    else return '';
  }else y=A.anchor(o.it,o.q,G)[1];
  return ` data-y="${y.toFixed(1)}"`;
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
function catsWanted(){const v=V();return v?.cozy?.total>=24?2:1;}
/** 🐾 The player's own pets (game/pets.py), at home only (not in a home you visit): {key, pet} for the cat list. */
function myPets(){if(S.remote)return [];const cat=S.env?.api?.content?.journey?.pets;return (J().pets?.pets||[]).map(p=>({p,L:petLookup(cat,p.b,p.c)})).filter(x=>x.L);}
function catsFor(rm,G,list){
  const want=catsWanted(),pets=myPets(),key=pets.map(x=>x.p.id+JSON.stringify(x.p.w)).join('|');
  if(CATS.room!==rm.id||CATS.list.length!==want+pets.length||CATS.key!==key){
    const spots=napSpots(rm,G,list),pick=i=>spots[i]||floorSpot(rm,G);
    CATS.room=rm.id;CATS.key=key;
    CATS.list=[...['mochi','bo'].slice(0,want).map(coat=>({coat})),...pets.map(x=>({pet:x}))].map((c,i)=>{const s=pick(i);return {...c,x:s.x,y:s.y,pose:s.pose,flip:i%2===1,to:null,until:0};});
  }
  return CATS.list;
}
const PET_POSE={walk:'walk',sleep:'sleep',melt:'sleep',loaf:'sit'};

/* ---- 👶 the babies at home (v4/baby.js, game/cradle.py): in a cradle, crawling on a mat or toddling, asleep after
 * "Ru bé ngủ" today; not the one carried out. Only in your own home. A tap walks you to the baby (v4/home-walk.js). ---- */
const BABY_K=.6;
const homeBabies=()=>S.remote?[]:BB.babies(S.env?.api?.state).filter(b=>b.id!==BB.carried(S.env?.api?.state)?.id);
const doneWith=b=>new Set((J().cradle?.did||[]).filter(k=>k.startsWith(b.id+':')).map(k=>k.slice(b.id.length+1)));
/** Where baby i stays in room rm: on the floor (a rug is fine), clear of the furniture standing there, a pool or a
 * fixture that keeps pieces off, and of the babies placed before it. */
function babySpot(rm,G,i){
  const list=inRoom(rm),pieces=list.filter(o=>!o.q.on&&o.it.spot!=='wall'&&o.it.spot!=='rug').map(o=>bbox(o.it,A.anchor(o.it,o.q,G)));
  const hit=(x,y,[bx,by,bw,bh])=>x+24>bx&&x-24<bx+bw&&y>by&&y-36<by+bh;
  const blocked=(x,y,taken)=>(rm.fix||[]).some(f=>f.layer==='floor'&&f.block&&x>A.PX+f.x*A.CW-26&&x<A.PX+(f.x+f.w)*A.CW+26&&y>G.FY+f.y*A.FR-6&&y<G.FY+(f.y+f.h)*A.FR+14)
    ||pieces.some(b=>hit(x,y,b))||taken.some(p=>Math.abs(p.x-x)<56&&Math.abs(p.y-y)<30);
  const rows=[.72,.92,.5].map(f=>G.FY+A.FR*Math.max(.9,Math.min(rm.frows-.3,rm.frows*f))),taken=[];
  let out=null;
  for(let k=0;k<=i;k++){
    out=null;
    for(const y of rows){for(const fx of [.55,.3,.75,.42,.18,.86,.64]){const x=A.PX+rm.cols*A.CW*fx;if(!blocked(x,y,taken)){out={x,y};break;}}if(out)break;}
    out??={x:A.PX+rm.cols*A.CW*.3+k*44,y:rows[0]};taken.push(out);
  }
  return out;
}
export function babyAt(uid){
  const rm=roomOf(S.room),list=homeBabies(),i=list.findIndex(b=>`baby:${b.id}`===uid);
  return rm&&i>=0?{...babySpot(rm,A.geom(rm),i),b:list[i]}:null;
}
function babiesMarkup(rm,G,photo,edit){
  return homeBabies().map((b,i)=>{
    const p=babySpot(rm,G,i),art=`<g transform="translate(${p.x.toFixed(1)} ${p.y.toFixed(1)}) scale(${BABY_K})">${babyRoom({g:b.grow,o:b.outfit},{asleep:doneWith(b).has('ru')})}</g>`;
    if(photo)return art;
    if(edit)return `<g class="dc-baby" pointer-events="none" aria-hidden="true">${art}</g>`;
    return `<g class="dc-baby" data-uid="baby:${esc(b.id)}" data-y="${p.y.toFixed(1)}" tabindex="0" role="button" aria-label="${esc(b.name)} · ${esc(BB.growName(b.grow))}">${art}<rect class="dc-hit" x="${(p.x-24).toFixed(1)}" y="${(p.y-34).toFixed(1)}" width="48" height="40" rx="8"/></g>`;
  }).join('');
}
/** The card beside the room: each baby, its three free moments of the day, carry it out or leave it home. */
function babyCard(){
  if(S.remote)return '';
  const st=S.env?.api?.state,list=BB.babies(st);if(!list.length)return '';
  const C=J().cradle,acts=C?.acts||BB.family()?.acts||[],cur=BB.carried(st);
  const rows=list.map(b=>{
    const done=doneWith(b),out=cur?.id===b.id;
    const moments=acts.map(a=>btn(`${a.emoji} ${esc(a.names?.[b.grow]||a.names?.so_sinh||'')}${done.has(a.id)?' ✓':''}`,'bbMoment',{baby:b.id,act:a.id},done.has(a.id)?'ghost small':'cream small',done.has(a.id)?' disabled':'')).join('');
    return `<div class="dc-baby-row"><div class="dc-baby-pic">${babyPortrait({g:b.grow,o:b.outfit},{size:76,asleep:!out&&done.has('ru')})}</div><div class="dc-baby-info"><b>${esc(b.name)}</b>`
      +`<small>${esc(BB.growName(b.grow))} · ${fmt(b.age)} ngày tuổi · Gắn bó ${fmt(b.bond)}/100</small>`
      +`${out?'<p class="dc-baby-out">🤱 Bé đang trong vòng tay bạn: đi dạo phố, công viên cùng nhau nhé.</p>':''}</div>`
      +`${moments?`<div class="dc-baby-acts">${moments}</div>`:''}<div class="dc-baby-acts">${btn(out?'🏡 Để bé ở nhà':'🤱 Bế bé đi chơi','bbCarry',{baby:b.id},out?'ghost small':'primary small',` aria-pressed="${out}"`)}${btn('🍼 Chăm bé','bbCare',{baby:b.id},'ghost small')}</div></div>`;
  }).join('');
  const left=C?C.spirit_left:0;
  return `<section class="bk-card dc-baby-card" id="dc-baby-card"><h3>👶 Bé nhà mình</h3>${rows}<p class="bk-hint">${acts.length?`Miễn phí, mỗi việc một lần mỗi ngày: gắn bó +1${left?`, tinh thần +1 (còn ${left} lần hôm nay)`:''}. `:''}Bế bé thì đi bộ, không đi xe.</p></section>`;
}
const catInner=c=>{
  if(c.pet){const pose=PET_POSE[c.pose]||'sit',w=c.pet.p.w||{},acc=pose==='sleep'?w:{...w,bed:null};   // its bed only under a nap
    return `<g class="dc-cat-in ${c.pose} pet-svg"><g transform="scale(${c.flip?-.62:.62} .62)">${petInner(c.pet.L.breed,c.pet.L.coat,pose,acc)}</g></g>`;}
  return `<g class="dc-cat-in ${c.pose}"><g${c.flip?' transform="scale(-1 1)"':''}>${A.catSVG(c.pose,c.coat)}</g></g>`;
};
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
  if(S.remote&&!(S.coop?COOP_OPS:VISIT_OPS).has(op))return;
  if(S.coop&&((op==='drawer'&&data.d!=='bag')||(op==='hold'&&data.src!=='bag')))return;   // the owner's bag only
  const v=V();
  switch(op){
    case'scroll':{const rail=S.dlg.querySelector(`[data-dc-rail="${data.rail}"]`);rail?.scrollBy({left:(Number(data.dir)||1)*Math.max(120,rail.clientWidth*.8),behavior:'smooth'});return;}
    case'close':S.dlg.close();return;
    case'back':{const remote=!!S.remote;S.dlg.close();if(remote)S.env.act('homeGuests');else (await import('./house.js')).openHouse(S.env);return;}
    case'guests':S.dlg.close();S.env.act('homeGuests');return;
    case'tab':S.tab=data.tab;S.flash=null;S.held=null;S.sel='';render();return;
    case'room':S.room=data.room;S.sel='';ZM.reset();render();return;
    case'floor':{const r=(V()?.rooms||[]).find(x=>floorOf(x)===Number(data.fl));if(r){S.room=r.id;S.sel='';ZM.reset();render();}return;}   // 🏰 a villa's floor
    case'zoom':ZM.button(S.dlg,data.z);return;   // 🔍 ＋ － ⤢
    case'edit':S.edit=true;S.flash=null;S.toTop=true;sfx('click');render();return;
    case'done':S.edit=false;S.held=null;S.sel='';S.flash=null;S.toTop=true;sfx('click');render();return;
    case'drawer':S.drawer=data.d;S.cat='';S.resetStrip=true;S.held=S.drawer==='skin'?null:S.held;render();return;
    case'cat':S.cat=data.cat||'';S.resetStrip=true;render();return;
    case'style':S.style=S.style===data.style?'':data.style||'';S.resetStrip=true;render();return;
    case'unfilter':S.cat='';S.style='';S.q='';S.resetStrip=true;render();return;
    case'spot':case'cell':{const c=chosen(),rm=roomOf(S.room);if(!c||!rm)return;   // 📍 Đặt nhanh (quickSpots) / ♿ a cell (cellsMarkup)
      const q={r:rm.id,x:Number(data.x)||0,y:Number(data.y)||0,f:c.uid?placed(c.uid)?.f||0:0};if(data.on)q.on=data.on;
      await placeChosen(q);return;}
    case'step':{const p=placed(data.uid);if(!p||p.id!==S.sel)return;step(p,Math.sign(Number(data.dx)||0),Math.sign(Number(data.dy)||0));return;}
    case'unsel':{const p=placed(S.sel);S.sel='';if(p){say(`Đã bỏ chọn ${low(ITEM(p.k)?.name)}.`);S.focusNext=[pieceKey(p.id),'svg.dc-room'];}render();return;}
    case'hold':{const it=ITEM(data.k);if(!it)return;
      if(S.held&&S.held.k===data.k&&S.held.src===data.src){S.held=null;say(`Đã bỏ chọn ${low(it.name)}.`);render();return;}
      S.held={k:data.k,src:data.src};S.sel='';sfx('pop');
      if(!it.rooms.includes(roomOf(S.room)?.type)){const r=roomsFor(it)[0];if(r)S.room=r.id;}
      const rm=roomOf(S.room);say(rm&&it.rooms.includes(rm.type)?`Đã chọn ${it.name}. Chạm chỗ muốn đặt trong ${low(rm.name)}.`:`Đã chọn ${it.name}. Món này không hợp chỗ ở này.`);
      render();revealRail('rooms','[aria-selected="true"]');revealRail('items','[aria-pressed="true"]');return;}
    case'unhold':{const it=heldItem();S.held=null;if(it)say(`Đã bỏ chọn ${low(it.name)}.`);render();return;}
    case'buyBag':{const it=heldItem();if(!it||S.held.src!=='shop')return;
      if(await ask(`Mua ${low(it.name)}?`,`Cất vào túi đồ, đặt lúc nào cũng được. Ấm cúng +${it.cozy} khi bày ra (mỗi loại tính một lần).`,`Mua · ${xu(it.price)}`,it.price)){
        const r=await send('jr_deco_buy',{item:it.id,confirm:true,n:nonce()});if(r){sfx('coins');S.held={k:it.id,src:'bag'};render();}}return;}
    case'move':{const p=placed(data.uid);if(!p)return;S.held={k:p.k,src:'room',uid:p.id,rot:rotOf(p)};S.sel='';sfx('pop');say(`Đang dời ${low(ITEM(p.k)?.name)}. Chạm chỗ muốn đặt, hoặc chọn phòng khác.`);render();return;}
    case'flip':{const p=placed(data.uid);if(!p)return;await putPiece(p.id,{...qOf(p),f:p.f?0:1});return;}
    case'pin':{const on=togglePin(data.uid);S.flash={text:on?'📌 Đã ghim: món này không bị kéo nhầm nữa.':'Đã bỏ ghim: kéo để dời được rồi.',kind:'good'};sfx('click');render();return;}
    case'turn':{if(S.held&&!data.uid){turnHeld();return;}const p=placed(data.uid);if(!p)return;await turnPiece(p);return;}
    case'zup':case'zdown':{const p=placed(data.uid);if(!p)return;const rm=roomOf(p.r),zs=inRoom(rm,new Set([p.id])).map(o=>o.q.z||0);
      const z=op==='zup'?Math.min(CD().z_max||99,Math.max(0,...zs)+1):Math.max(0,Math.min(...zs,p.z||0)-1);
      if(z===(p.z||0)){S.flash={text:op==='zup'?'Món này đang ở trên cùng rồi.':'Món này đang ở dưới cùng rồi.',kind:'warn'};render();return;}
      await putPiece(p.id,{...qOf(p),z});return;}
    case'tint':{const p=placed(data.uid),it=ITEM(p?.k);if(!it)return;
      (await import('./palette.js')).pickColor(S.env,{title:it.name,current:tintOf(p.id)||'goc',preview:c=>A.thumb(it,88,c),
        onTry:c=>{S.tryTint={uid:p.id,c};paintPiece(p.id);},apply:async c=>!!await send('jr_wd_deco',{uid:p.id,color:c}),
        onClose:()=>{S.tryTint=null;render();}});return;}
    case'troBg':S.troPick=S.troPick===data.uid?'':data.uid;render();return;   // 🎣 tranh cá: its background (#517)
    case'troSet':{const p=placed(data.uid);if(!p||!A.TRO_BG[data.bg])return;if(await send('jr_fish_tro',{uid:p.id,bg:data.bg}))sfx('success');return;}
    case'troSize':{const p=placed(data.uid),it=ITEM(p?.k);if(!p||!it)return;
      if(await send('jr_fish_tro',{uid:p.id,sz:it.id==='tranh_ca'?'nho':'lon'})){sfx('success');if(!placed(p.id))S.sel='';}return;}
    case'troOut':{const p=placed(data.uid);if(!p)return;   // 🎣 the fish back to the bag (#528)
      if(await S.env.confirmAction('Gỡ cá khỏi tranh?','Cá về giỏ cá, tranh mất.','Gỡ cá')&&await send('jr_fish_tro',{uid:p.id,out:true})){sfx('success');S.sel='';S.undo=S.undo.filter(u=>!(p.id in u));render();}return;}
    case'pick':return pick(data.uid);
    case'restore':S.dlg?.close();await (await import('./restore.js')).openRestore(S.env,{service:'co_dien',ref:data.uid});return;   // 🧰 Làm cổ điển by a player restorer
    case'sell':{const p=placed(data.uid)||v.bag.find(b=>b.id===data.uid),it=ITEM(p?.k);if(!it)return;
      if(await S.env.confirmAction(`Bán lại ${low(it.name)}?`,`Nhận ${xu(it.sell)} (${CD().sell_pct}% giá mua).`,`Bán · ${xu(it.sell)}`)){
        const r=await send('jr_deco_sell',{uid:p.id,confirm:true,n:nonce()});if(r){sfx('coins');S.sel='';S.undo=S.undo.filter(u=>!(p.id in u));render();}}return;}
    case'pickAll':{if(!v.items.length)return;
      if(await S.env.confirmAction('Cất hết đồ vào túi?','Mọi món đang bày ở chỗ này về túi đồ. Bấm Hoàn tác để bày lại như cũ.','Cất hết')){
        const prev=Object.fromEntries(v.items.map(p=>[p.id,qOf(p)]));
        const r=await send('jr_deco_pick',{uid:'all'});if(r){pushUndo(prev);S.sel='';sfx('click');render();}}return;}
    case'undo':return undo();
    case'coopUndo':return coopUndo(Number(data.id));
    case'stayCoop':if(data.code)await openReno(S.env,'coop',data.code);return;   // 🏡 arrange the host's furniture with their grant
    case'skin':return pickSkin(data.part,data.skin);
    case'photo':return takePhoto();
    case'photoSave':{if(!S.photo)return;const career=S.env.api.state?.current||S.env.api.state?.focus;
      S.busy=true;paintBusy();
      try{const r=await S.env.api.command('photo',{image:S.photo.image,title:S.photo.title},career);S.flash={text:r.message,kind:'good'};S.photo.saved=true;sfx('chime');}
      catch(e){if(!e.quiet)S.flash={text:e.message||'Chưa lưu được ảnh.',kind:'bad'};}
      finally{S.busy=false;render();}return;}
    case'photoClose':S.photo=null;render();return;
    case'tipOk':tipDone();render();return;
    case'bbMoment':{const b=BB.babies(S.env.api.state).find(x=>x.id===data.baby);if(!b||S.busy)return;   // 👶 a free moment
      if(b.id==='child'){const r=await send('jr_cradle_do',{baby:'child',act:data.act},{loud:true,flash:false});if(r){sfx('chime');hw().say(r.message.replace(/^\S+\s/,''),true);}return;}
      S.busy=true;paintBusy();
      try{const m=await BB.moment(S.env,b,data.act);sfx('chime');if(m)hw().say(m.replace(/^\S+\s/,''),true);}
      catch(e){if(!e.quiet){S.flash={text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};sfx('error');}}
      finally{S.busy=false;render();}return;}
    case'bbCarry':{const st=S.env.api.state,out=BB.carried(st)?.id===data.baby;BB.setCarry(out?'':data.baby);sfx('pop');
      const b=BB.babies(st).find(x=>x.id===data.baby);
      S.flash=b?{text:out?`${b.name} ở nhà ngủ ngoan.`:`Bạn bế ${b.name} rồi. Ra phố hay công viên, bé đi cùng bạn (đi bộ).`,kind:'good'}:null;render();return;}
    case'bbCare':{S.dlg.close();if(data.baby==='child')S.env.openSheet?.('home',{jrView:'household'});else S.env.act?.('marriage',{tab:'family',section:'children'});return;}
    case'relax':{const a=(V()?.relax||[]).find(x=>x.id===data.act);if(!a||!a.ok)return;
      const r=await send('jr_relax_do',{act:a.id},{loud:true});if(r)sfx('chime');return;}
    case'fix':{const r=R();const all=data.part==='all',p=r.parts.find(x=>x.id===data.part),cost=all?r.fix_all:p?.fix;if(all?!r.parts.some(x=>due(r,x)):!p||!due(r,p))return;
      const what=all?'Sửa cả nhà?':`Sửa ${low(PART(p.id).name)}?`,body=all?r.parts.filter(x=>due(r,x)).map(x=>`${PART(x.id).name} ${xu(x.fix)}`).join(' · '):`${condWord(p.c,p.id)} (${p.c}%) → như mới.${insLine(r,p)}`;
      if(await ask(what,body,`Sửa · ${xu(cost)}`,cost)){const res=await send('jr_reno_fix',{part:data.part,cost,confirm:true});if(res)sfx('success');}return;}
    case'up':{const r=R(),p=r.parts.find(x=>x.id===data.part);if(!p?.up)return;
      if(await ask(`${p.up.name}?`,`${PART(p.id).name} như mới, bền hơn. Ấm cúng +${CR().cozy_lv}.`,`Làm · ${xu(p.up.cost)}`,p.up.cost)){const res=await send('jr_reno_up',{part:p.id,lv:p.up.lv,cost:p.up.cost,confirm:true});if(res)sfx('success');}return;}
    default:if(op.startsWith('hw'))await hw().click(op,data);return;   // 🧊 the fridge (v4/home-walk.js)
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
  if(!q.on&&q.rot!=null)body.rot=q.rot;   // ↻ only a turn: without it the server keeps the piece's own
  const r=await send('jr_deco_put',body);
  if(r&&!r.duplicate){
    pushUndo(prev);cheer(r,uid);
    // more of the same kind in the bag: keep holding it (three plants in a row)
    const next=again?V().bag.find(b=>b.k===again):null;S.held=next?{k:again,src:'bag',rot:rotOf(next)}:null;S.sel=S.held?'':uid;
    S.focusNext=[pieceKey(uid)];   // ♿ the control pressed is gone (the last card of its kind): the piece itself
    render();
    sayWhere(uid);
  }
  return r;
}
/** ↻ Xoay 90° (góp ý #358): the next turn of a placed piece, where it stands when it still fits, else the nearest spot
 * where it does (the room's edge or a door in the way); nowhere near: why not. One jr_deco_put; ↶ Hoàn tác turns it back. */
async function turnPiece(p){
  const base=ITEM(p.k),rm=roomOf(p.r);if(!base||!rm||!canTurn(base,p))return;
  if(isPinned(p.id)){S.flash={text:'Món này đang ghim. Bỏ ghim rồi xoay nhé.',kind:'warn'};sfx('error');render();return;}
  const rot=(rotOf(p)+1)%4,it=A.turn(base,rot),list=inRoom(rm,new Set([p.id,...ridersOf(p.id)])),q={...qOf(p),rot};
  const to=fitNear(rm,it,q,list);
  if(!to){const bad=checkQ(rm,it,clampQ(rm,it,q,list),list)||{code:'bounds'};S.flash={text:`Xoay ${low(base.name)} không vừa chỗ này. ${whyText(bad,rm,it)}`,kind:'warn'};sfx('error');render();return;}
  const r=await putPiece(p.id,to);
  if(r&&!r.duplicate)say(`${base.name}: ${ROT_WORD[rot]}.`);
}
/** The spot nearest `q` (itself first) where `it` may stand, half a cell at a time, up to three cells away. */
function fitNear(rm,it,q,list){
  const c=clampQ(rm,it,q,list);if(!checkQ(rm,it,c,list))return c;
  let best=null,bd=1e9;
  for(let dy=-3*U;dy<=3*U;dy+=U/2)for(let dx=-3*U;dx<=3*U;dx+=U/2){
    const t=clampQ(rm,it,{...q,x:q.x+dx,y:q.y+dy},list),d=Math.hypot(t.x-q.x,t.y-q.y);
    if(d<bd&&!checkQ(rm,it,t,list)){bd=d;best=t;}
  }
  return best;
}
/** ↻ The piece in hand (from the drawer, or being moved) turns before it is put down. */
function turnHeld(){
  const h=S.held,base=ITEM(h?.k);if(!h||!canTurn(base))return;
  h.rot=((h.rot||0)+1)%4;h.turned=true;sfx('click');say(`${base.name}: ${ROT_WORD[h.rot]}.`);render();
}
async function pick(uid){
  const p=placed(uid);if(!p)return;
  const prev={[uid]:qOf(p)};for(const u of ridersOf(uid))prev[u]=qOf(placed(u));
  const r=await send('jr_deco_pick',{uid});
  if(r){pushUndo(prev);S.sel='';sfx('click');S.focusNext=['svg.dc-room'];render();}
}
async function undo(){
  const last=S.undo.pop();if(!last){render();return;}
  const r=await send('jr_deco_layout',{set:last},{loud:true});
  if(r){sfx('pop');render();}
}
/** ↻ The spot for the piece in hand with its turn (sent when it has one, or was turned back to the front). */
const heldQ=(q,h)=>{const o={...q};delete o.rot;if(!q.on&&(h.rot||h.turned))o.rot=h.rot||0;return o;};
/** Put the held piece at the free spot `q` of the current room (buying it first from the shop). */
async function dropAt(q){
  const h=S.held,it=heldItem(),rm=roomOf(S.room);if(!h||!it||!rm||!q)return;
  const bad=checkQ(rm,it,q,inRoom(rm,new Set(h.uid?[h.uid,...ridersOf(h.uid)]:[])));
  if(bad){S.flash={text:whyText(bad,rm,it),kind:'warn'};sfx('error');render();return;}
  if(h.src==='room'){await putPiece(h.uid,heldQ(q,h));return;}
  if(h.src==='bag'){const b=V().bag.find(x=>x.k===h.k);if(!b){S.held=null;render();return;}
    await putPiece(b.id,heldQ(q,h),h.k);return;}
  if(await ask(`Mua ${low(it.name)}?`,`Đặt ở ${low(rm.name)} · ấm cúng +${it.cozy} nếu chỗ này chưa có món này. Bán lại được ${CD().sell_pct}% giá.`,`Mua · ${xu(it.price)}`,it.price)){
    const put={r:q.r,x:q.x,y:q.y,f:q.f||0};if(q.on)put.on=q.on;if(h.rot&&!q.on)put.rot=h.rot;
    const r=await send('jr_deco_buy',{item:it.id,confirm:true,put,n:nonce()});
    if(r&&r.uid){if(!r.duplicate)pushUndo({[r.uid]:null});S.held=null;S.sel=r.uid;sfx('coins');cheer(r,r.uid);S.focusNext=[pieceKey(r.uid)];render();sayWhere(r.uid);}
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
  if(g&&(e.key==='Enter'||e.key===' ')&&!S.edit){e.preventDefault();hw().tap(roomOf(S.room),{x:0,y:0},g.dataset.uid);return;}   // 🚶 walk up to it and use it
  if(!S.edit&&e.target.closest?.('svg.dc-room')&&hw().key(roomOf(S.room),e))return;
  if(g&&(e.key==='Enter'||e.key===' ')){e.preventDefault();const uid=g.dataset.uid;choose(uid);S.dlg?.querySelector(pieceKey(uid))?.focus({preventScroll:true});return;}
  if(!S.edit||!S.sel||S.busy||!e.target.closest?.('svg.dc-room'))return;   // the keys belong to the room, not the drawer
  const p=placed(S.sel);if(!p)return;
  const step=e.shiftKey?U:4,d={ArrowLeft:[-step,0],ArrowRight:[step,0],ArrowUp:[0,-step],ArrowDown:[0,step]}[e.key];
  if(d){e.preventDefault();if(!isPinned(p.id))nudge(p,d);return;}
  if(e.key==='f'||e.key==='F'){e.preventDefault();putPiece(p.id,{...qOf(p),f:p.f?0:1}).then(focusSel);return;}
  if((e.key==='r'||e.key==='R')&&canTurn(ITEM(p.k),p)){e.preventDefault();onClick('turn',{uid:p.id}).then(focusSel);return;}
  if(e.key==='PageUp'||e.key==='PageDown'){e.preventDefault();onClick(e.key==='PageUp'?'zup':'zdown',{uid:p.id}).then(focusSel);return;}
  if(e.key==='Delete'||e.key==='Backspace'){e.preventDefault();pick(p.id);}
}
function nudge(p,[dx,dy]){
  const rm=roomOf(p.r),it=itemOf(p);if(!rm||!it)return;
  const from=S.nudge&&S.nudge.uid===p.id?S.nudge.q:qOf(p);
  const list=inRoom(rm,new Set([p.id,...ridersOf(p.id)]));
  nudgeTo(p,clampQ(rm,it,{...from,x:from.x+dx,y:from.y+dy},list));
}
/** Show `p` at `q` now and send the move a moment later (the next nudge or step before then replaces it). */
function nudgeTo(p,q,refocus=true){
  const n=S.nudge&&S.nudge.uid===p.id?S.nudge:{uid:p.id,q:qOf(p)};
  n.q=q;S.nudge=n;clearTimeout(n.t);
  showMove(p.id,q);
  n.t=setTimeout(async()=>{S.nudge=null;await putPiece(p.id,q);if(refocus)focusSel();},320);
}
const focusSel=()=>{if(S.sel)S.dlg?.querySelector(`g[data-uid="${CSS.escape(S.sel)}"]`)?.focus({preventScroll:true});};

/* ---- pointer: press a piece and drag it; drag a card up out of the drawer; tap to select or to drop ---- */
function svgPoint(svg,cx,cy){const m=svg.getScreenCTM();if(!m)return null;const p=new DOMPoint(cx,cy).matrixTransform(m.inverse());return {x:p.x,y:p.y};}
const roomSvg=()=>S.dlg?.querySelector('svg.dc-room');
function onDown(e){
  if(!S.photo&&e.target.closest?.('.dc-zoom')&&ZM.down(S.dlg,e)){   // 🔍 a second finger: a pinch, not a tap or a drag
    if(S.drag){const D=S.drag;S.drag=null;S.held=null;S.dragEnd=Date.now();floatGhost(null);if(D.kind==='piece')S.sel=D.uid;render();}
    S.press=null;return;
  }
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
  if(isPinned(uid))return false;   // 📌 ghim
  const p=placed(uid),rm=roomOf(p?.r),svg=roomSvg();if(!p||!rm||!svg)return false;
  const it=itemOf(p),G=A.geom(rm),list=inRoom(rm),q=qOf(p),a=A.anchor(it,q,G,hostFor(rm,q,list)),pt=svgPoint(svg,cx,cy);if(!pt)return false;
  const ride=ridersOf(uid),els=[uid,...ride].map(u=>svg.querySelector(`g[data-uid="${CSS.escape(u)}"]`)).filter(Boolean);
  const layer=els[0]?.parentNode;for(const el of els){el.classList.add('drag');layer?.append(el);}   // on top while held
  S.drag={kind:'piece',uid,k:p.k,it,rm,q0:q,a0:a,grab:[pt.x-a[0],pt.y-a[1]],els,list:inRoom(rm,new Set([uid,...ride])),q:q,bad:null};
  S.held={k:p.k,src:'room',uid,rot:rotOf(p)};S.sel='';
  svg.classList.add('dragging');
  svg.querySelector('.dc-zonelayer').innerHTML=zoneMarkup(rm,it,G,S.drag.list);
  for(const el of svg.querySelectorAll('.dc-selbox'))el.remove();
  sfx('pop');buzz(8);
  return true;
}
function onMove(e){
  if(ZM.move(S.dlg,e))return;   // 🔍 pinching or panning
  const p=S.press;if(!p||p.id!==e.pointerId)return;
  const dx=e.clientX-p.x,dy=e.clientY-p.y;
  if(!S.drag){
    if(p.kind==='room'){
      const piece=S.edit&&p.uid&&!isPinned(p.uid)&&!(S.held&&S.held.src!=='room');
      if(Math.hypot(dx,dy)<DRAG_PX)return;
      if(!piece){if(ZM.k>1&&ZM.panFrom(S.dlg,e.clientX,e.clientY))p.pan=true;return;}   // 🔍 zoomed in: one finger pans
      if(!startPieceDrag(p.uid,p.x,p.y))return;
    }else{
      if(Math.abs(dy)<12||Math.abs(dy)<Math.abs(dx)*1.2)return;   // sideways: the drawer scrolls
      const bagged=p.src==='bag'?V()?.bag.find(b=>b.k===p.k):null,rot=rotOf(bagged),it=A.turn(ITEM(p.k),rot);if(!it)return;
      try{p.el.setPointerCapture(e.pointerId);}catch{/* fine */}
      S.drag={kind:'card',k:p.k,src:p.src,it,grab:grabFor(it),q:null,bad:null,uid:bagged?.id||''};S.held={k:p.k,src:p.src,rot};S.sel='';
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
  const rm=roomOf(S.room),pt=svgPoint(svg,cx,cy),r=(svg.closest?.('.dc-roomwrap')||svg).getBoundingClientRect();   // 🔍 zoomed: the visible frame
  const inside=cx>=r.left-8&&cx<=r.right+8&&cy>=r.top-8&&cy<=r.bottom+8;
  if(D.kind==='card'){
    floatGhost(inside?null:D.it,cx,cy);
    const g=svg.querySelector('.dc-preview');
    if(!inside||!rm||!pt||!D.it.rooms.includes(rm.type)){g.innerHTML='';D.q=null;return;}
    const list=inRoom(rm),q=candidate(rm,D.it,pt.x-D.grab[0],pt.y-D.grab[1],list,0);
    if(!q){g.innerHTML='';D.q=null;return;}
    const a=A.anchor(D.it,q,A.geom(rm),hostFor(rm,q,list));D.q=q;D.bad=checkQ(rm,D.it,q,list);
    g.innerHTML=`<g class="dc-it drag${D.bad?' bad':''}">${q.on?A.contact(D.it,a[0],a[1]):''}${A.pieceAt(D.it,a[0],a[1],0,D.uid?tintOf(D.uid):null,'front',D.uid||'')}</g>`;
    return;
  }
  if(!pt)return;
  const G=A.geom(D.rm),q=candidate(D.rm,D.it,pt.x-D.grab[0],pt.y-D.grab[1],D.list,D.q0.f);
  if(!q)return;
  q.z=D.q0.z;if(!q.z)delete q.z;
  if(D.q0.rot)q.rot=D.q0.rot;
  D.q=q;D.bad=checkQ(D.rm,D.it,q,D.list);D.out=!inside;
  showMove(D.uid,q,D);
}
/** Redraw one placed piece in place (the colour being tried in the palette picker), keeping the room as it is. */
function paintPiece(uid){
  const svg=roomSvg(),p=placed(uid),rm=roomOf(p?.r),el=svg?.querySelector(`g[data-uid="${CSS.escape(uid)}"] .dc-piece`);if(!el||!rm)return;
  const list=inRoom(rm),o=list.find(x=>x.id===uid);if(!o)return;
  const a=A.anchor(o.it,o.q,A.geom(rm),hostFor(rm,o.q,list));
  el.innerHTML=(o.q.on?A.contact(o.it,a[0],a[1]):'')+A.pieceAt(o.it,a[0],a[1],o.q.f,tintOf(uid),'front',uid);
}
/** Draw `uid` (and what stands on it) at `q` without redrawing the room. */
function showMove(uid,q,D=null){
  const svg=roomSvg(),p=placed(uid),rm=roomOf(p?.r);if(!svg||!p||!rm)return;
  const it=itemOf(p),G=A.geom(rm),list=inRoom(rm),q0=qOf(p);
  const a0=A.anchor(it,q0,G,hostFor(rm,q0,list)),a=A.anchor(it,q,G,hostFor(rm,q,list.filter(o=>o.id!==uid))),dx=a[0]-a0[0],dy=a[1]-a0[1];
  const els=D?.els||[uid,...ridersOf(uid)].map(u=>svg.querySelector(`g[data-uid="${CSS.escape(u)}"]`)).filter(Boolean);
  for(const el of els){
    el.setAttribute('transform',`translate(${dx.toFixed(1)} ${dy.toFixed(1)})`);
    el.classList.toggle('bad',!!(D&&(D.bad||D.out)));
  }
}
async function onUp(e){
  const zoomed=ZM.up(S.dlg,e);
  const p=S.press;if(!p||p.id!==e.pointerId)return;
  S.press=null;S.tapEnd=Date.now();
  if(p.pan||zoomed&&!S.drag)return;   // 🔍 the end of a pan or a pinch: not a tap
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
  if(!S.edit){hw().tap(roomOf(S.room),svgPoint(svg,e.clientX,e.clientY),p.uid);return;}   // 🚶 walk there (a piece: use it)
  if(S.held){
    const rm=roomOf(S.room),it=heldItem(),pt=svgPoint(svg,e.clientX,e.clientY);
    if(p.uid&&p.uid!==S.held.uid&&S.held.src==='room'&&!(it?.spot==='top')){choose(p.uid,false);return;}
    if(rm&&it&&pt){
      const g=grabFor(it),list=inRoom(rm,new Set(S.held.uid?[S.held.uid,...ridersOf(S.held.uid)]:[]));
      const q=candidate(rm,it,pt.x-g[0],pt.y-g[1],list,S.held.src==='room'?(placed(S.held.uid)?.f||0):0);
      if(q){await dropAt(q);return;}
    }
    S.flash={text:it&&rm&&!it.rooms.includes(rm.type)?whyText({code:'type'},rm,it):'Chỗ này không đặt được.',kind:'warn'};sfx('error');render();return;
  }
  // ♿ chạm chọn, chạm đặt: a tap on a piece chooses it (again: lets go); with one chosen, a tap on the room puts it there
  // (a small thing tapped onto a table or a shelf goes up on it), as a drag would.
  const cur=S.sel?placed(S.sel):null,cit=itemOf(cur),rm=roomOf(S.room),pt=svgPoint(svg,e.clientX,e.clientY);
  const at=()=>{if(!cur||!cit||!rm||!pt)return null;const g=grabFor(cit);return candidate(rm,cit,pt.x-g[0],pt.y-g[1],inRoom(rm,new Set([cur.id,...ridersOf(cur.id)])),cur.f||0);};
  if(p.uid){
    const q=cur&&p.uid!==cur.id&&cit.spot==='top'&&!ridersOf(cur.id).includes(p.uid)?at():null;
    if(q?.on){await placeChosen(q);return;}
    choose(p.uid);return;
  }
  if(cur){
    const q=at();if(q){await placeChosen(q);return;}
    S.flash={text:cit&&rm&&!cit.rooms.includes(rm.type)?whyText({code:'type'},rm,cit):'Chỗ này không đặt được.',kind:'warn'};sfx('error');render();
  }
}
function onCancel(e){
  ZM.up(S.dlg,e);
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
    // B10: WebP or JPEG (Safari's fallback was a PNG, often over the 256 KB command cap), ≤ PHOTO_MAX characters.
    const image=encodePhoto(img,{w:W,h:H,width:W*2,bg:'#fffdf7'});
    URL.revokeObjectURL(url);
    if(!image)throw new Error('big');
    S.photo={image,title,saved:false};sfx('chime');
  }catch{S.flash={text:'Máy chưa chụp được ảnh. Thử lại nhé.',kind:'bad'};}
  finally{S.busy=false;render();}
}

/* ---- rendering ---- */
const levelIdx=total=>{const ls=[...(CD().levels||[])].sort((a,b)=>a.min-b.min);let i=-1;for(const l of ls)if(total>=l.min)i++;return Math.max(0,Math.min(4,i));};
function paintBusy(){
  if(S.busy&&!S.refocus)S.refocus=focusKeyOf(globalThis.document?.activeElement);   // ♿ a disabled button drops its focus
  S.dlg?.setAttribute('aria-busy',String(S.busy));S.dlg?.querySelectorAll('[data-dc]').forEach(b=>{if(b.tagName==='BUTTON'&&b.dataset.dc!=='scroll'&&b.dataset.dc!=='zoom')b.disabled=S.busy;});}
/** ♿ After a redraw: focus it took away (the room drawing is always new; a busy button let go of it) goes back to the
 * same control, else to S.focusNext (where the action that removed the control wants it). Focus the player moved
 * themselves is never touched; neither are text fields. */
function refocus(key){
  const want=S.focusNext;S.focusNext=[];
  const a=globalThis.document?.activeElement;if(!key||(a&&a!==document.body&&a!==S.dlg&&S.dlg.contains(a)))return;
  const el=[key,...want].map(k=>{try{return S.dlg.querySelector(k);}catch{return null;}}).find(x=>x&&!x.disabled);
  el?.focus?.({preventScroll:true});
}
function render(){
  if(!S.dlg)return;
  const fkey=focusKeyOf(globalThis.document?.activeElement)||S.refocus;if(!S.busy)S.refocus='';
  if(S.flash&&S.flash!==S.saidFlash){S.saidFlash=S.flash;say(S.flash.text);}   // ♿ the flash line is read out by say()
  catsFreeze();hw().freeze();
  // Patched in place (v4/home-morph.js), not rewritten: a rail keeps its scroll and a fling in flight goes on.
  const body=S.dlg.querySelector('.dc-body'),top=body?.scrollTop;
  const scrolls=railScroll(S.dlg);
  const v=V();
  if(v&&!S.remote&&S.undoKey!==v.place.key){S.undoKey=v.place.key;S.undo=[];CATS.room='';}
  if(v&&!S.remote){const lv=levelIdx(v.cozy.total);S.cheer=S.lastLv>=0&&lv>S.lastLv;S.lastLv=lv;}
  morph(S.dlg.querySelector('.dc-root'),page());
  const b2=S.dlg.querySelector('.dc-body');if(b2&&top!=null&&(S.toTop||b2!==body)&&b2.scrollTop!==(S.toTop?0:top))b2.scrollTop=S.toTop?0:top;
  if(S.toTop)S.dlg.scrollTop=0;
  const reset=S.resetStrip;railRestore(S.dlg,scrolls,key=>reset&&key!=='rooms');
  S.dlg.setAttribute('aria-busy',String(S.busy));
  S.pop='';S.resetStrip=false;S.toTop=false;
  ZM.apply(S.dlg);
  catsResume();if(!CATS.timer&&S.dlg.open)CATS.timer=setTimeout(catsTick,1800);
  hw().resume();hw().paint();
  refocus(fkey);
}
function head(v){
  const pl=v?.place;
  return `<header class="sheet-head bk-head rn-head"><button class="icon-btn" type="button" data-dc="back" aria-label="Về Nhà của bạn">${icon('back',21)}</button>
    <div class="grow"><span class="eyebrow">${pl?.repairs?'TRONG NHÀ':S.edit?'BÀY TRÍ PHÒNG':'TRONG PHÒNG'}</span><h2 id="dc-title">${pl?`${pl.emoji} ${esc(pl.name)}`:'Nhà của bạn'}</h2></div>
    <button class="icon-btn" type="button" data-dc="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
}
// Read out by say() (render), not as a live region of its own: the same line again is read again.
const flash=()=>`<p class="bk-flash ${S.flash?.kind||''}">${S.flash?esc(S.flash.text):''}</p>`;
function page(){
  const v=V();
  if(!v)return head(v)+`<div class="sheet-body bk dc-body"><section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🪴</div><h3>Chưa có chỗ để bày trí</h3><p>Bày trí phòng có trong chế độ hành trình.</p>${btn('🏠 Nhà của bạn','back',{},'primary')}</section></div>`;
  if(!v.rooms.some(r=>r.id===S.room))S.room=v.rooms[0]?.id||'';
  const r=R(),own=!S.remote&&v.place.repairs&&r;
  if(!own)S.tab='deco';
  const worn=own&&r.parts.some(p=>p.worn);
  const tabs=own?`<div class="segmented bk-tabs rn-tabs" role="tablist" aria-label="Trong nhà">${[['deco','🪴 Bày trí'],['fix',`🛠️ Sửa nhà${worn?'<i class="dot" aria-hidden="true"></i>':''}`]].map(([id,l])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" class="${S.tab===id?'active':''}" data-dc="tab" data-tab="${id}">${l}</button>`).join('')}</div>`:'';
  const main=S.tab==='fix'?`<div class="dc-fix">${condCard(r)}${fixPanel(r)}</div>`:decoPage(v);
  return head(v)+`<div class="sheet-body bk dc-body">${tabs}${flash()}${main}</div>${S.photo?photoView():''}`;
}
function decoPage(v){
  const rm=roomOf(S.room);if(!rm)return '';
  const use=useV();
  hw().ensure(rm);
  const svg=roomMarkup(rm,{edit:S.edit}).svg;
  const wide=!!window.matchMedia?.('(min-width:720px)').matches;   // a wide sheet: the drawer beside the room, so a card is always in reach
  const tip=S.edit&&!tipSeen()?`<div class="dc-tip" role="note"><span aria-hidden="true">👆</span><p><b>Giữ một món rồi kéo đi đâu cũng được</b><small>Hoặc chạm chọn một món rồi chạm chỗ muốn đặt. Chạm món đồ để xoay, lật, đổi phòng hoặc cất đi. Chụm hai ngón hoặc cuộn chuột để phóng to, thu nhỏ.</small></p>${btn('Hiểu rồi','tipOk',{},'ghost small')}</div>`:'';
  const bar=S.coop?(S.edit?`<div class="dc-actions">${btn('↶ Hoàn tác','undo',{},'ghost',S.undo.length?'':' disabled')}${btn('✓ Xong','done',{},'primary')}</div>`
      :`<div class="dc-actions">${btn('✏️ Trang trí giúp','edit',{},'primary')}${btn('← Bạn bè & nhà','guests',{},'ghost')}</div>`)
    :S.remote?`<div class="dc-actions">${btn('← Bạn bè & nhà','guests',{},'primary')}</div>`:S.edit
    ?`<div class="dc-actions">${btn('↶ Hoàn tác','undo',{},'ghost',S.undo.length?'':' disabled')}${btn('🎒 Cất hết','pickAll',{},'ghost',v.items.length?'':' disabled')}${btn('✓ Xong','done',{},'primary')}</div>`
    :`<div class="dc-actions">${btn(v.items.length?'✏️ Bày trí phòng':'✏️ Bắt đầu bày trí','edit',{},'primary')}${btn('📸 Chụp phòng','photo',{},'ghost')}</div>`;
  const cells=S.edit&&!S.photo?cellsMarkup(rm,chosen()):'';   // ♿ every spot a named button
  // 🏠 the chibi room as before 2.6.0 (owner 24/10: "nhà cũ chibi… trang trí cũ"): nothing drawn over it; 🔍 ＋ － ⤢ in a row above
  const stage=`<div class="dc-stage">${roomTabs(v)}${ZM.controls(btn)}<div class="dc-roomwrap"><div class="dc-zoom"${ZM.style()}>${svg}${cells}</div>${S.edit?'':`${hw().hint(use,rm)}${hw().sayHTML()}`}</div>${hw().socialPanel()}${S.edit?(S.held?heldBar(v):S.sel?tools(v):''):hw().panel(use,rm)}${tip}${bar}${S.edit&&!wide?drawer(v):''}</div>`;
  const side=S.coop?`${coopCard()}${S.edit&&wide?drawer(v):''}`:S.remote?`<section class="bk-card"><h3>🏡 Nhà ${esc(S.remote.owner.name)}</h3><p>${S.remote.access?.kind==='stay'?'Bạn ở chung tại đây, có thể vào khi chủ nhà vắng mặt.':'Bạn đang ghé chơi theo lời mời.'}</p><p class="bk-hint">Chạm sàn để đi lại, gặp bạn trong phòng và giao lưu.</p></section>`:`${S.edit?'':babyCard()}${relaxCard(use,rm)}${S.edit&&wide?drawer(v):''}${stayCard(v)}${cozyCard(v)}${coopOwnerCard(v)}${guestCard(v)}${setsCard(v)}${placeNote(v)}`;
  return `<div class="dc-grid">${stage}<div class="dc-side">${side}</div></div>`;
}
function scrollRail(key,html){
  return `<div class="dc-scroll">${btn('‹','scroll',{rail:key,dir:-1},'ghost small',' aria-label="Cuộn sang trái"')}${html}${btn('›','scroll',{rail:key,dir:1},'ghost small',' aria-label="Cuộn sang phải"')}</div>`;
}
function revealRail(key,selector){
  const rail=S.dlg.querySelector(`[data-dc-rail="${key}"]`),item=rail?.querySelector(selector);if(!item)return;
  const r=rail.getBoundingClientRect(),i=item.getBoundingClientRect();
  if(i.left<r.left)rail.scrollLeft-=r.left-i.left;
  else if(i.right>r.right)rail.scrollLeft+=i.right-r.right;
}
/** 🏰 A villa's floors (game/estates.py `fl`): the rooms rail shows one floor at a time, the floor of the room on screen. */
const floorOf=r=>Number(r?.fl)||1;
function floorTabs(v){
  const fls=[...new Set(v.rooms.map(floorOf))].sort((a,b)=>a-b);if(fls.length<2)return '';
  const cur=floorOf(roomOf(S.room));
  return `<div class="segmented dc-floors" role="tablist" aria-label="Tầng">${fls.map(f=>`<button type="button" role="tab" aria-selected="${f===cur}" class="${f===cur?'active':''}" data-dc="floor" data-fl="${f}">🏢 ${f}</button>`).join('')}</div>`;
}
function roomTabs(v){
  if(v.rooms.length<2)return '';
  const it=heldItem(),n=id=>v.items.filter(i=>i.r===id).length,fl=floorOf(roomOf(S.room)),many=new Set(v.rooms.map(floorOf)).size>1;
  return floorTabs(v)+scrollRail('rooms',`<div class="rn-rooms dc-rooms" data-dc-rail="rooms" role="tablist" aria-label="Các phòng">${v.rooms.filter(r=>!many||floorOf(r)===fl).map(r=>{const ok=it&&it.rooms.includes(r.type);
    return `<button type="button" role="tab" aria-selected="${S.room===r.id}" class="rn-room${S.room===r.id?' active':''}${ok?' ok':''}" data-dc="room" data-room="${r.id}"><span aria-hidden="true">${r.emoji}</span>${esc(r.name)}${n(r.id)?`<small${n(r.id)>=r.cap?' class="full"':''}>${n(r.id)}${S.edit?`/${r.cap}`:''}</small>`:''}</button>`;}).join('')}</div>`);
}
function heldBar(v){
  const it=heldItem(),rm=roomOf(S.room);if(!it)return '';
  const here=rm&&it.rooms.includes(rm.type),where=roomsFor(it).map(r=>low(r.name));
  const full=here&&inRoom(rm,new Set(S.held.uid?[S.held.uid]:[])).length>=rm.cap;
  const hint=!where.length?esc('Món này không hợp chỗ ở này.'):!here?`Món này đặt ở ${where.map(w=>`<i>${esc(w)}</i>`).join(', ')}.`:esc(full?`${rm.name} bày đủ ${rm.cap}/${rm.cap} món. Cất bớt hoặc bày sang phòng khác nhé.`:it.spot==='top'?'Chạm hoặc kéo vào phòng: lên bàn, kệ, giường hay sàn đều được.':S.held.src==='room'?'Chạm chỗ muốn dời tới.':'Chạm hoặc kéo vào chỗ muốn đặt.');
  const sub=S.held.src==='shop'?`${xu(it.price)} · ấm cúng +${it.cozy}`:S.held.src==='bag'?`Trong túi · ấm cúng +${it.cozy}`:'Đang dời';
  const spots=here&&!full?quickSpots(rm,it,new Set(S.held.uid?[S.held.uid,...ridersOf(S.held.uid)]:[]),S.held.src==='room'?placed(S.held.uid)?.f||0:0):[];
  const pick=spots.length?`<div class="dc-spots" role="group" aria-label="${esc(`Đặt nhanh ${low(it.name)} vào ${low(rm.name)}`)}"><small>📍 Đặt nhanh:</small>${spots.map(o=>
    btn(esc(o.label),'spot',{x:o.q.x,y:o.q.y,on:o.q.on||''},'ghost small',` aria-label="${esc(`Đặt ${low(it.name)}: ${o.label}, ${low(rm.name)}`)}"`)).join('')}</div>`:'';
  return `<div class="dc-held" role="group" aria-label="${esc(`Đang chọn ${low(it.name)}`)}">${A.thumb(it,40)}<p><b>${esc(it.name)}</b><small>${esc(sub)}</small><small class="dc-held-hint">${hint}</small></p>
    <span class="dc-held-go">${canTurn(ITEM(S.held.k))?btn(`↻ Xoay · ${ROT_WORD[S.held.rot||0]}`,'turn',{},'ghost small',' aria-label="Xoay 90 độ trước khi đặt"'):''}${S.held.src==='shop'?btn('🎒 Mua cất túi','buyBag',{},'ghost small',it.price>v.ready?' disabled':''):''}${btn('✕ Bỏ chọn','unhold',{},'ghost small')}</span>${pick}</div>`;
}
/** 📍 Đặt nhanh (góp ý #443, a player who cannot see the room): a few ready-made spots for the held piece in room `rm`,
 * as buttons a screen reader names ("Góc trái sàn", "Lên bàn trà"): no dragging, no aiming at the drawing. Each spot
 * passes the same checks as a tap (checkQ; the server decides) and overlaps the other pieces of its layer as little as
 * the room allows. Small things first try the surfaces with room left on them. */
const SPOT_WORDS={wall:['Bên trái tường','Giữa tường','Bên phải tường'],floor:['Góc trái sàn','Giữa sàn','Góc phải sàn'],rug:['Thảm bên trái','Thảm ở giữa','Thảm bên phải']};
function quickSpots(rm,it,skip=new Set(),f=0){
  if(!rm||!it||!it.rooms.includes(rm.type))return [];
  const list=inRoom(rm,skip),out=[];
  if(list.length>=rm.cap)return out;
  if(it.spot==='top'){
    for(const s of surfaces(rm,list,A.geom(rm))){
      const box=hostBox(rm,s.on,list);if(!box)continue;
      const riders=list.filter(o=>o.q.on===s.on);if(riders.length>=box.cap)continue;
      let best=0,bs=1e9;
      for(let x=0;x<=Math.max(0,box.w-it.w*U);x+=U/2){const sc=riders.reduce((a,o)=>a+ov(x,x+it.w*U,o.q.x,o.q.x+o.it.w*U),0);if(sc<bs){bs=sc;best=x;}}
      const q={r:rm.id,x:best,y:0,f,on:s.on};if(checkQ(rm,it,q,list))continue;
      const host=s.on[0]==='#'?(CD().fix_names||{})[s.on.slice(1)]||'kệ có sẵn':low(list.find(o=>o.id===s.on)?.it.name||'');
      out.push({q,label:`Lên ${host}`});
      if(out.length>=4)break;
    }
  }
  const z=zoneOf(rm,it),layer=sp=>sp==='wall'?'wall':sp==='rug'?'rug':'floor',mine=layer(it.spot);
  if(!z)return out;
  const others=list.filter(o=>!o.q.on&&layer(o.it.spot)===mine),W=it.w*U,H=it.h*U,step=U/2;
  SPOT_WORDS[mine].forEach((label,i)=>{
    const a=z[0]*i/3,b=z[0]*(i+1)/3;let best=null,bs=1e9;
    for(let x=Math.ceil(a/step)*step;x<=b+.01;x+=step)for(let y=0;y<=z[1]+.01;y+=step){
      const q={r:rm.id,x:Math.round(x),y:Math.round(y),f};if(checkQ(rm,it,q,list))continue;
      const sc=others.reduce((t,o)=>t+ov(q.x,q.x+W,o.q.x,o.q.x+o.it.w*U)*ov(q.y,q.y+H,o.q.y,o.q.y+o.it.h*U),0)*10+(mine==='floor'?q.y:Math.abs(q.y-z[1]/2));
      if(sc<bs){bs=sc;best=q;}
    }
    if(best&&!out.some(o=>!o.q.on&&o.q.x===best.x&&o.q.y===best.y))out.push({q:best,label});
  });
  return out;
}
/** The selected piece's buttons (one string each: easy to add one). */
function toolButtons(v,p,it){
  const tb=(label,op,tip,cls='')=>btn(label,op,{uid:p.id},`ghost small${cls}`,` title="${esc(tip)}" aria-label="${esc(tip)}"`);
  const tro=isTrophy(p,it),pin=isPinned(p.id),layered=it.spot==='wall'||it.spot==='rug'||!!p.on,out=[tb(pin?'📌 Đã ghim':'📌 Ghim','pin',pin?'Bỏ ghim để kéo được':'Ghim: không kéo nhầm'),tb('⇋ Lật','flip','Lật ngược'),
    ...(S.coop?[]:tro?[tb('🎨 Nền tranh','troBg','Đổi màu nền tranh'),it.id==='tranh_ca'?tb('🔽 Thu nhỏ','troSize','Tranh nhỏ 1 ô'):tb('🔼 Phóng to','troSize','Tranh lớn 2 × 2 ô')]:[tb('🎨 Màu','tint','Đổi màu')])];
  if(canTurn(it,p)){const t=rotOf(p);out.unshift(tb(`↻ Xoay · ${ROT_WORD[t]}`,'turn',`Xoay 90 độ, đang ${ROT_WORD[t]} (phím R)`,' dc-turn'));}
  if(layered)out.push(tb('⬆ Lên','zup','Đưa lên trên'),tb('⬇ Xuống','zdown','Đưa xuống dưới'));
  if(v.rooms.filter(r=>it.rooms.includes(r.type)).length>1)out.push(tb('🚪 Đổi phòng','move','Chọn vị trí hoặc phòng muốn đặt'));
  if(!S.coop&&!S.remote&&!agedBy(p.id)&&['table','bed','light','le'].includes(it.cat)&&!it.uq&&S.env?.api?.state?.journey?.story)out.push(tb('🧰 Làm cổ điển','restore','Nhờ một người chơi làm Thợ phục chế'));
  out.push(tb('🎒 Cất túi','pick','Thu hồi vào túi'));
  if(!S.coop&&tro)out.push(tb('🎣 Gỡ cá','troOut','Lấy cá ra, về giỏ cá',' danger'));
  else if(!S.coop)out.push(tb(`💰 Bán · ${xu(it.sell)}`,'sell',`Bán lại · ${xu(it.sell)}`,' danger'));
  return out;
}
/** 🎣 A tranh cá of this save (journey.fish.tro): its own background and size (game/fishing.py jr_fish_tro, góp ý #517). */
const isTrophy=(p,it)=>!S.remote&&(it?.id==='tranh_ca'||it?.id==='tranh_ca_nho')&&A.FISH_TRO.has(p?.id);
function troPicker(p){
  if(S.troPick!==p.id)return '';
  const cur=A.FISH_TRO.get(p.id)?.bg||'kem';
  return `<div class="dc-trobg" role="group" aria-label="Nền tranh">${Object.entries(A.TRO_BG).map(([k,[c]])=>
    `<button type="button" class="dc-trobg-sw${k===cur?' on':''}" data-dc="troSet" data-uid="${esc(p.id)}" data-bg="${k}" aria-pressed="${k===cur}"${S.busy?' disabled':''}><i style="background:${c}"></i>${esc(A.TRO_BG_NAMES[k])}</button>`).join('')}</div>`;
}
/** ♿ ⬅️⬆️⬇️➡️ one cell and ✕ Bỏ chọn for the chosen piece; a small thing also gets the surfaces it may go up on. */
function stepButtons(p,it){
  const sb=(label,dx,dy,tip)=>btn(label,'step',{uid:p.id,dx,dy},'ghost small dc-step',` aria-label="${esc(tip)}"`);
  const rm=roomOf(p.r),ups=it.spot==='top'?quickSpots(rm,it,new Set([p.id,...ridersOf(p.id)]),p.f||0).filter(o=>o.q.on&&o.q.on!==p.on):[];
  return `<span class="dc-steps" role="group" aria-label="${esc(`Dời ${low(it.name)} từng ô`)}">${sb('⬅️',-1,0,'Dời sang trái một ô')}${sb('⬆️',0,-1,'Dời lên một ô')}${sb('⬇️',0,1,'Dời xuống một ô')}${sb('➡️',1,0,'Dời sang phải một ô')}${btn('✕ Bỏ chọn','unsel',{},'ghost small dc-unsel')}</span>`
    +(ups.length?`<div class="dc-spots" role="group" aria-label="${esc(`Đặt ${low(it.name)} lên`)}"><small>📍 Đặt lên:</small>${ups.map(o=>btn(esc(o.label),'spot',{x:o.q.x,y:o.q.y,on:o.q.on},'ghost small',` aria-label="${esc(`Đặt ${low(it.name)}: ${o.label}`)}"`)).join('')}</div>`:'');
}
function tools(v){
  const p=placed(S.sel),it=itemOf(p);if(!it)return '';
  const by=agedBy(p.id),badge=by?`<small class="rs-badge" title="Đã phục chế bởi ${esc(by)}">✨ Cổ điển · ${esc(by)}</small>`:'';
  return `<div class="dc-tools" role="toolbar" aria-label="${esc(it.name)}"><span class="dc-tools-name">${A.thumb(it,36,tintOf(p.id))}<b>${esc(it.name)}</b><small class="dc-tools-at">${esc(posOf(p))}</small>${badge}</span>${stepButtons(p,it)}<span class="dc-tools-go">${toolButtons(v,p,it).join('')}</span>${isTrophy(p,it)?troPicker(p):''}</div>`;
}
/** 🔎 Search folds case and Vietnamese marks ("den long" finds "Đèn lồng"); an English player's own words match too. */
const fold=s=>String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d');
/** The drawer's filters: 🔎 the name, 🆕 Mới về (S.cat 'new'), a category, a style (deco.catalogue `styles`). */
function passes(it){
  if(S.cat==='new'?!it.new:S.cat&&it.cat!==S.cat)return false;
  if(S.style){const st=(CD().styles||[]).find(x=>x.id===S.style);if(st&&!st.items.includes(it.id))return false;}
  const q=fold(S.q).trim();
  return !q||fold(it.name).includes(q)||fold(tr(it.name)).includes(q);
}
function drawer(v){
  const C=CD(),types=new Set(v.rooms.map(r=>r.type)),rm=roomOf(S.room);
  const fits=it=>it.rooms.some(t=>types.has(t)),here=it=>rm&&it.rooms.includes(rm.type);
  let cards='',cats=new Set(),all=[],shownN=0,fresh=false;
  if(S.drawer==='skin')cards=skinStrip(v,rm);
  else if(S.drawer==='bag'){
    const groups=new Map();for(const b of v.bag){if(!groups.has(b.k))groups.set(b.k,[]);groups.get(b.k).push(b.id);}
    const list=[...groups.entries()].map(([k,ids])=>({it:ITEM(k),n:ids.length})).filter(x=>x.it);
    list.forEach(x=>cats.add(x.it.cat));all=list.map(x=>x.it);fresh=all.some(it=>it.new);
    const shown=list.filter(x=>passes(x.it)).sort((a,b)=>(here(b.it)-here(a.it))||(fits(b.it)-fits(a.it))||a.it.name.localeCompare(b.it.name,'vi'));
    shownN=shown.length;
    cards=shown.map(({it,n})=>card(it,'bag',`${n>1?`<i class="dc-n">×${n}</i>`:''}`,fits(it)?`Ấm cúng +${it.cozy}`:'Không hợp chỗ này',!fits(it))).join('');
    if(!list.length)cards=S.coop?'<div class="dc-empty"><p>Túi đồ của chủ nhà đang trống. Dời những món đã bày nhé!</p></div>'
      :`<div class="dc-empty"><p>Túi đồ trống. Ghé cửa hàng chọn món đầu tiên nhé!</p>${btn('🛒 Cửa hàng','drawer',{d:'shop'},'primary small')}</div>`;
  }else{
    const have=new Set([...v.items.map(i=>i.k),...v.bag.map(b=>b.k)]);
    const list=C.items.filter(it=>fits(it)&&!it.uq);list.forEach(it=>cats.add(it.cat));all=list;fresh=list.some(it=>it.new);   // 🔨 a painting won at auction is never sold
    const shown=list.filter(passes).sort((a,b)=>(here(b)-here(a))||a.price-b.price);
    shownN=shown.length;
    cards=shown.map(it=>card(it,'shop',have.has(it.id)?'<i class="dc-have">Đã có</i>':it.new?'<i class="dc-new">Mới</i>':'',`${xu(it.price)} · +${it.cozy}`,false,it.price>v.ready)).join('');
  }
  const filtered=S.drawer!=='skin'&&!!(S.cat||S.style||S.q.trim());
  if(filtered&&!shownN&&all.length)cards=`<div class="dc-empty"><p>Không có món nào hợp bộ lọc này.</p>${btn('Bỏ lọc','unfilter',{},'ghost small')}</div>`;
  const chips=S.drawer==='skin'?[]:[['','Tất cả'],...(fresh?[['new','🆕 Mới về']]:[]),...C.cats.filter(c=>cats.has(c.id)).map(c=>[c.id,`${c.emoji} ${c.name}`])];
  const styles=S.drawer==='skin'?[]:(C.styles||[]).filter(st=>all.some(it=>st.items.includes(it.id)));
  const find=S.drawer==='skin'||all.length<8?'':`<div class="dc-find"><label class="dc-search"><span aria-hidden="true">🔎</span><input type="search" data-dc-search value="${esc(S.q)}" placeholder="Tìm món: đèn, sofa, cây…" aria-label="Tìm đồ trang trí theo tên" maxlength="40" autocomplete="off" enterkeyhint="search"></label>
    <small class="dc-count" aria-live="polite">${filtered?`${shownN}/${all.length} món`:`${all.length} món`}</small></div>`;
  return `<section class="dc-drawer" aria-label="Đồ đạc">
    <div class="dc-drawer-top"><div class="segmented dc-seg" role="tablist">${(S.coop?[['bag',`🎒 Túi chủ nhà · ${v.bag.length}`]]:[['bag',`🎒 Túi · ${v.bag.length}`],['shop','🛒 Cửa hàng'],['skin','🎨 Tường & sàn']]).map(([id,l])=>`<button type="button" role="tab" aria-selected="${S.drawer===id}" class="${S.drawer===id?'active':''}" data-dc="drawer" data-d="${id}">${l}</button>`).join('')}</div>
    ${S.coop?'':`<span class="dc-money" title="Tài khoản + ví">💰 ${xu(v.ready)}</span>`}</div>
    ${find}
    ${chips.length>2?scrollRail('cats',`<div class="dc-cats" data-dc-rail="cats" role="group" aria-label="Loại đồ">${chips.map(([id,l])=>`<button type="button" class="dc-catchip${S.cat===id?' on':''}" data-dc="cat" data-cat="${id}" aria-pressed="${S.cat===id}">${l}</button>`).join('')}</div>`):''}
    ${styles.length>1?scrollRail('styles',`<div class="dc-cats dc-styles" data-dc-rail="styles" role="group" aria-label="Phong cách">${styles.map(st=>`<button type="button" class="dc-catchip dc-stylechip${S.style===st.id?' on':''}" data-dc="style" data-style="${st.id}" aria-pressed="${S.style===st.id}">${st.emoji} ${esc(st.name)}</button>`).join('')}</div>`):''}
    ${S.drawer==='skin'?cards:scrollRail('items',`<div class="dc-strip" data-dc-rail="items" role="list">${cards}</div>`)}</section>`;
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
    return `<div class="dc-skins"><h4>${title}</h4>${scrollRail(part,`<div class="dc-strip dc-skin-strip" data-dc-rail="${part}" role="list">${list.map(s=>{
      const on=cur===s.id,mine=!s.price||owned.has(s.id),poor=!mine&&s.price>v.ready;
      return `<button type="button" role="listitem" class="dc-swatch-btn${on?' on':''}${poor?' poor':''}" data-dc="skin" data-part="${part}" data-skin="${s.id}" aria-pressed="${on}"${S.busy||poor?' disabled':''}>`
        +`${A.swatch(s.id,part,58)}<b>${esc(s.name)}</b><small>${on?'Đang dùng':mine?(s.price?'Đã có':'Miễn phí'):xu(s.price)}</small></button>`;}).join('')}</div>`)}</div>`;
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
  return `<section class="bk-card dc-relax"><h3>${rm.type==='pool'||rm.type==='infinity'?'🏖️ Thư giãn bên hồ':'🛁 Thư giãn trong nhà tắm'}</h3><ul>${acts.map(row).join('')}</ul><p class="bk-hint">Miễn phí, mỗi ngày một lần.</p></section>`;
}
/** 🎨 Decorating a friend's home: whose things these are and that the owner sees (and may undo) every change. */
const until=t=>t?new Date(t*1000).toLocaleString('vi-VN',{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'}):'';
function coopCard(){
  const R0=S.remote,c=R0.coop||{},log=(c.log||[]).slice(0,6);
  return `<section class="bk-card dc-coop"><h3>🎨 Trang trí giúp nhà ${esc(R0.owner.name||'')}</h3>
    <p>Bày bằng đồ trong túi của chủ nhà: không mua, không bán, đồ và tiền không đổi chủ.</p>
    <p class="bk-hint">Mỗi thay đổi đều được ghi lại, chủ nhà xem và hoàn tác được.</p>
    ${c.expires_at?`<p class="bk-hint">Quyền trang trí đến ${esc(until(c.expires_at))}.</p>`:''}
    ${log.length?`<h4>Thay đổi gần đây</h4><ul class="dc-coop-log">${log.map(r=>`<li><p><b>${esc(r.name)}</b> <span>${esc(r.text)}</span></p>${r.undone?'<small>Đã hoàn tác</small>':''}</li>`).join('')}</ul>`:''}</section>`;
}
/** 🎨 In your own home: who may decorate it and their latest changes, each with Hoàn tác. */
function coopOwnerCard(v){
  const d=S.coopLog;if(!d||!['own','estate'].includes(v.place.where))return '';
  const log=(d.log||[]).slice(0,6),mine=d.mine||[];if(!log.length&&!mine.length)return '';
  return `<section class="bk-card dc-coop"><h3>🎨 Bạn bè trang trí giúp</h3>
    ${mine.length?`<p>Đang cho ${mine.map(m=>`<b>${esc(m.name)}</b>`).join(', ')} trang trí nhà bằng đồ trong túi của bạn.</p>`:''}
    ${log.length?`<ul class="dc-coop-log">${log.map(r=>`<li><p><b>${esc(r.name)}</b> <span>${esc(r.text)}</span></p>${r.undone?'<small>Đã hoàn tác</small>':r.undo?btn('↶ Hoàn tác','coopUndo',{id:r.id},'ghost small'):''}</li>`).join('')}</ul>`:'<p class="bk-hint">Chưa có thay đổi nào.</p>'}
    <div class="dc-actions">${btn('Quản lý quyền trang trí','guests',{},'ghost small')}</div></section>`;
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
/** 🏡 Ở chung (góp ý #330): the host's own furniture moves only with the host's 🎨 Cho trang trí grant (game/home_coop.py,
 * checked by the server on every change). With it, this opens the host's home to arrange: move, turn, put away into the
 * host's bag. Without it: how to get it. The grants come with GET /api/home-guests (deco.homes). */
function hostGrant(){
  const hg=S.env?.api?.homeGuests,stay=(hg?.homes||[]).find(h=>h.kind==='stay'&&h.here);if(!stay)return null;
  return {host:stay,grant:(hg?.deco?.homes||[]).find(h=>h.code===stay.code)||null};
}
function stayCard(v){
  if(S.remote||v?.place?.where!=='stay')return '';
  const h=hostGrant();if(!h)return '';
  return `<section class="bk-card dc-stay"><h3>🏡 Đồ của ${esc(h.host.name||'chủ nhà')}</h3>${h.grant
    ?`<p>Chủ nhà cho bạn sắp đồ giúp: dời, xoay hay cất vào túi của chủ nhà.</p><div class="dc-actions">${btn('🎨 Sắp đồ chủ nhà','stayCoop',{code:h.grant.code},'primary')}</div>`
    :'<p class="bk-hint">Đồ của chủ nhà chỉ chủ nhà dời được. Nhờ chủ nhà bật 🎨 Cho trang trí cho bạn là sắp giúp được.</p>'}</section>`;
}
/** The grants for the card above, read once when a stay home opens and nothing was read yet. */
function loadHostGrant(){
  if(S.remote||V()?.place?.where!=='stay'||S.env?.api?.homeGuests)return;
  S.env.api.json('/api/home-guests').then(d=>{if(!S.env.api.homeGuests)S.env.api.homeGuests=d;if(S.dlg?.open&&!S.busy&&!S.drag&&!S.press)render();}).catch(()=>{});
}
function placeNote(v){
  const st=v.stats||{},pl=v.place;
  const note=pl.repairs?'':pl.where==='shared'?'💞 Nhà chung: bày trí thoải mái, chuyện sửa nhà để người đứng tên lo.':pl.where==='stay'?'🏡 Ở chung nhà bạn: mua, bày, bán đồ của mình thoải mái. Sửa nhà để chủ nhà lo.':'🧾 Chỗ ở thuê: tự mua, bày, bán đồ của mình thoải mái, chỉ không sửa nhà.';
  const theirs=mates();
  const mate=theirs.length?`<p class="dc-mate-note">${S.mate.stay?'🏡':'💞'} Có cả đồ ${esc(S.mate.name)} bày (${theirs.length} món). Món của ai người nấy dời.</p>`:'';
  return `<section class="bk-card dc-placenote">${note?`<p>${note}</p>`:''}${mate}<p class="bk-hint">Dọn đi đâu, đồ đạc cũng tự gói vào túi đồ. Mua một lần, mang theo cả hành trình.</p>
    <p class="dc-stats"><span>🎒 ${fmt(v.count)} món</span><span>📌 Đã đặt ${st.placed||0} lần</span><span>☕ ${st.guests||0} lượt khách ghé</span></p></section>`;
}
function photoView(){
  const p=S.photo,can=!!(S.env.api.state?.current||S.env.api.state?.focus);
  return `<div class="dc-photo" role="dialog" aria-label="Ảnh chụp phòng"><div class="dc-photo-card"><figure><img src="${p.image}" alt="${esc(p.title)}"></figure>
    <div class="bk-actions">${can&&!p.saved?btn('💾 Lưu vào album','photoSave',{},'primary'):''}<a class="btn ghost" href="${p.image}" download="phong-cua-toi.webp">⬇️ Tải ảnh về</a>${btn('Đóng','photoClose',{},'ghost')}</div>
    ${can?'<p class="bk-hint">Album giữ sáu ảnh gần nhất của nghề đang làm.</p>':''}</div></div>`;
}

/* ---- 🛠️ Sửa nhà (a home you own) ---- */
/* 🛡️ Feedback #313: a sự cố left for later (game/rui.py) is priced here after the home insurance (r.incident: part →
 * cover %, so a part can cost 0 xu); wear and upgrades are never insured, and the card says so. */
const due=(r,p)=>p.fix>0||(r.incident||{})[p.id]!=null;
const insLine=(r,p)=>{const c=(r.incident||{})[p.id];return c?` Bảo hiểm nhà trả ${c}% sự cố.`:'';};
function insNote(r){
  const i=r.insure;
  const text=!i?'🛡️ Chưa có bảo hiểm nhà. Bảo hiểm chỉ trả sự cố (dột, vỡ ống, chập điện, cháy, ngập). Hao mòn và nâng cấp ở đây tự trả.'
    :i.wait&&i.now?`🛡️ Bảo hiểm nhà ${i.pct}%: đang chờ hiệu lực (còn ${i.wait} ngày), giờ trả ${i.now}%. Hao mòn và nâng cấp ở đây tự trả.`
    :i.wait?`🛡️ Bảo hiểm nhà ${i.pct}%: đang chờ hiệu lực (còn ${i.wait} ngày). Hao mòn và nâng cấp ở đây tự trả.`
    :`🛡️ Bảo hiểm nhà ${i.pct}%: trả sự cố (dột, vỡ ống, chập điện, cháy, ngập). Hao mòn và nâng cấp ở đây tự trả.`;
  return `<p class="bk-hint rn-ins">${esc(text)}</p>`;
}
function condCard(r){
  const worn=r.parts.filter(p=>p.worn);
  return `<section class="bk-card"><h3>Tình trạng nhà · ${r.cond}%</h3><div class="bk-bar ${tone(r.cond)}" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${r.cond}" aria-label="Tình trạng nhà"><i style="width:${r.cond}%"></i></div>
    ${worn.length?`<ul class="rn-flaws">${worn.map(p=>`<li>${PART(p.id).emoji} ${esc(PART(p.id).flaw)}</li>`).join('')}</ul>`:'<p class="bk-hint">Nhà sạch đẹp.</p>'}
    <dl class="hs-facts rn-facts"><div><dt>Đồ đạc</dt><dd>${r.count} món</dd></div><div><dt>Đã chi cho nhà</dt><dd>${xu(r.spent)}</dd></div></dl></section>`;
}
function fixPanel(r){
  const need=r.parts.filter(p=>due(r,p)),ready=r.ready;
  const short=n=>n>ready?' disabled':'';
  const all=need.length>1?`<div class="bk-actions rn-fixall">${btn(`🛠️ Sửa hết · ${xu(r.fix_all)}`,'fix',{part:'all'},'primary',short(r.fix_all))}</div>`:'';
  const rows=r.parts.map(p=>{const m=PART(p.id);
    return `<li class="rn-part ${tone(p.c)}"><div class="rn-part-top"><span class="rn-part-ico" aria-hidden="true">${m.emoji}</span><div class="grow"><b>${esc(m.name)}</b><small>${esc(condWord(p.c,p.id))} · ${p.c}%</small></div><span class="rn-lv" aria-label="Nâng cấp ${p.lv}/2">${'★'.repeat(p.lv)}${'☆'.repeat(2-p.lv)}</span></div>
      <div class="bk-bar ${tone(p.c)}" aria-hidden="true"><i style="width:${p.c}%"></i></div>
      ${(r.incident||{})[p.id]!=null?`<p class="rn-inc">🛡️ ${esc((r.incident[p.id]?`Có sự cố: bảo hiểm trả ${r.incident[p.id]}%`:'Có sự cố: chưa có bảo hiểm trả'))}</p>`:''}
      <div class="rn-part-go">${due(r,p)?btn(`Sửa · ${xu(p.fix)}`,'fix',{part:p.id},'ghost',short(p.fix)):''}${p.up?btn(`⬆ ${esc(p.up.name)} · ${xu(p.up.cost)}`,'up',{part:p.id},'ghost',short(p.up.cost)):'<span class="rn-max">Đã nâng cấp hết</span>'}</div></li>`;}).join('');
  return `<section class="bk-card"><h3>Sửa nhà</h3><p class="bk-hint">Có ${xu(ready)} (tài khoản + ví). Mỗi nâng cấp: ấm cúng +${CR().cozy_lv}.</p>${insNote(r)}${all}<ul class="rn-parts">${rows}</ul></section>`;
}
