/** portrait.js — 📸 Chụp ảnh cho người chơi (game/photo_studio.py, owner 21/10). One dialog, four screens:
 *   studio  the photographer's queue (📸 Tiệm ảnh Tách Tách: "Khách đặt chụp"): Nhận / ✕, the price list, open/closed
 *   shoot   the session, a real mini-game: backdrop, light, framing, pose, face, prop on the camera's screen (the buyer's
 *           own character from the look snapshot, ./portrait-art.js), then the shutter: 3-2-1, the subject settles,
 *           holds the pose with eyes open, blinks, then the pose is gone: tap 📸 in the hold. SHOTS shots, each judged
 *           by the server from the elapsed time; then pick the best, retouch lightly (4 sliders) and deliver
 *   order   the buyer's sheet from a photographer's place (work visit, profile card): package, who comes along, the wish
 *           (backdrop, mood), the price (the list price or an offer between the floor and the cap), the portfolio
 *   album   🖼️ the buyer's photos: Đặt làm ảnh hồ sơ, Treo trong nhà, Lưu ảnh, Ẩn ở tiệm thợ; orders on their way
 * Every rule and every price is the server's (POST /api/photo/<op>, GET /api/photo/<sub>); this file shows and sends.
 * Opened by app.js handleAction('photo', {tab, place}). Styles: /css/portrait.css. Phone first (390 px). */
import {escapeHTML as esc,icon} from '../icons.js';
import {stylesheet} from '../lazy.js';
import {paintPhoto,photoURL,PRODUCT} from './portrait-art.js';
import {POSE,FACE} from './booth-poses.js';
import {PROPS} from './photo-frames.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const S={dlg:null,env:null,view:'studio',busy:false,flash:null,cat:null,
  studio:null,order:null,sess:null,set:null,tab:'bd',shots:[],beat:null,pick:0,rt:{sang:0,am:0,min:0,vig:0},result:null,cam:null,
  place:null,form:null,album:null,photo:null,old:false};
const PROP_EMOJI=Object.fromEntries(PROPS.map(p=>[p.id,p.emoji]));
const Q_TAG={good:['ok','✓ Ảnh đẹp'],early:['bad','💨 Nhòe'],blink:['bad','😑 Nhắm mắt'],late:['bad','↪️ Hết dáng']};
const STATUS={open:'⏳ Chờ thợ nhận',shoot:'📷 Đang chụp',done:'✓ Đã giao',declined:'✕ Thợ từ chối',cancelled:'Đã hủy',expired:'⌛ Quá hạn'};
const api=()=>S.env.api;
const petCat=()=>api()?.content?.journey?.pets||null;
const C=()=>S.studio?.catalog||S.place?.catalog||S.album?.catalog||null;
const pkgOf=id=>(C()?.pkgs||[]).find(p=>p.id===id)||{id,name:id,emoji:'📸'};
const named=(list,id)=>(list||[]).find(x=>x.id===id)||{id,name:id,emoji:'✨'};
const stars=n=>'★'.repeat(Math.max(0,Math.min(5,n)))+'☆'.repeat(Math.max(0,5-Math.min(5,n)));
const rid=()=>{try{return crypto.randomUUID().replace(/-/g,'').slice(0,24);}catch{return Math.random().toString(36).slice(2)+Date.now().toString(36);}};

/* ---------------------------------------------------------------- the dialog */
function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium pt-sheet';d.setAttribute('aria-labelledby','pt-title');
  d.innerHTML='<div class="pt-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){close();return;}
    const el=e.target.closest('[data-pt]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.pt,el.dataset).catch(err=>{console.warn('📸',err);flash(err.message||'Chưa làm được. Thử lại nhé.',false);});
  });
  d.addEventListener('input',e=>{const t=e.target;if(t.dataset.rt){S.rt[t.dataset.rt]=Number(t.value);const o=t.closest('label')?.querySelector('output');if(o)o.textContent=signed(Number(t.value));paintPick();}
    else if(t.dataset.ptNote!=null&&S.form)S.form.note=t.value.slice(0,80);});
  d.addEventListener('close',()=>{stopCam();});
  return S.dlg=d;
}
const signed=v=>v>0?`+${v}`:String(v);
function close(){stopCam();S.dlg?.close();}
function flash(text,good=true){S.flash=text?{text,good}:null;render();}
async function get(sub,q={}){return api().json('/api/photo/'+sub+'?'+new URLSearchParams(Object.entries(q).filter(([,v])=>v!==''&&v!=null)));}
async function post(op,body){
  if(S.busy)return null;S.busy=true;render();
  try{const r=await api().post('/api/photo/'+op,body,20000);
    if(r?.state&&typeof r.revision==='number')api().accept({state:r.state,revision:r.revision});
    S.flash=r?.message?{text:r.message,good:true}:null;return r;}
  catch(e){S.flash={text:e.message||'Chưa gửi được. Thử lại nhé.',good:false};return null;}
  finally{S.busy=false;render();}
}

/** app.js handleAction('photo', data): tab studio | order (data.place) | album. */
export async function photoAction(env,data={}){
  S.env=env;await stylesheet('/css/portrait.css');
  const d=dialog();S.flash=null;S.result=null;
  const tab=data.tab||'album';
  if(!d.open){d.showModal();d.scrollTop=0;}
  if(tab==='studio')await openStudio();
  else if(tab==='order')await openOrder(data.place,data.pkg);
  else await openAlbum();
}
async function openStudio(){S.view='studio';S.studio=null;render();try{S.studio=await get('studio');}catch(e){S.flash={text:e.message,good:false};}render();}
async function openOrder(place,pkg){S.view='order';S.place=null;S.form=null;render();
  try{S.place=await get('place',{place});S.form=defaults(S.place);
    if(pkg&&(S.place.pkgs||[]).some(x=>x.id===pkg)&&ok(pkg,S.place.can||{}))formSet('pkg',pkg);   // 🛎️ Phố dịch vụ: the package the card showed
  }catch(e){S.flash={text:e.message,good:false};}render();}
async function openAlbum(old=false,before=null){S.view='album';S.old=old;if(!before)S.album=null;render();
  try{const r=await get('album',{old:old?'1':'',before});if(r?.state&&typeof r.revision==='number')api().accept({state:r.state,revision:r.revision});
    S.album=before&&S.album?{...r,photos:[...S.album.photos,...r.photos]}:r;}catch(e){S.flash={text:e.message,good:false};}render();}

/** The badge of the photographer's queue (photobooth.js): the open orders waiting, cached a little. */
let COUNT={at:0,n:0,go:null};
export function queueCount(env){
  S.env=S.env||env;
  if(Date.now()-COUNT.at<30000)return Promise.resolve(COUNT.n);
  return COUNT.go??=env.api.json('/api/photo/studio').then(d=>{COUNT={at:Date.now(),n:(d?.queue||[]).filter(o=>o.status==='open'||o.status==='shoot').length,go:null};return COUNT.n;})
    .catch(()=>{COUNT.go=null;return COUNT.n;});
}

/* ---------------------------------------------------------------- render */
function render(){
  if(!S.dlg)return;
  const root=S.dlg.querySelector('.pt-root'),top=S.dlg.scrollTop;
  root.innerHTML=page();
  S.dlg.setAttribute('aria-busy',String(S.busy));
  S.dlg.scrollTop=top;
  paintAll(root);
}
function head(emoji,title,back=''){
  return `<header class="sheet-head pt-head">${back?`<button class="icon-btn" type="button" data-pt="${back}" aria-label="Quay lại">${icon('back',20)}</button>`:''}
    <span class="pt-logo" aria-hidden="true">${emoji}</span><div class="grow"><h2 id="pt-title">${esc(title)}</h2></div>
    <button class="icon-btn" type="button" data-pt="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
}
const flashBox=()=>S.flash?`<p class="pt-flash ${S.flash.good?'good':'bad'}" role="status">${esc(S.flash.text)}</p>`:'';
const wait=()=>'<p class="pt-empty" role="status">⏳</p>';
const btn=(label,op,data={},cls='')=>`<button type="button" class="btn ${cls}" data-pt="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${S.busy?' disabled':''}>${label}</button>`;
function page(){
  switch(S.view){
    case'studio':return head('📸','Khách đặt chụp')+`<div class="sheet-body pt-body">${flashBox()}${studioView()}</div>`;
    case'shoot':return head('📷',`Chụp cho ${S.order?.buyer?.name||''}`,'studio')+`<div class="sheet-body pt-body">${flashBox()}${shootView()}</div>`;
    case'pick':return head('🖼️','Chọn ảnh & chỉnh','studio')+`<div class="sheet-body pt-body">${flashBox()}${pickView()}</div>`;
    case'done':return head('🎉','Đã giao ảnh','studio')+`<div class="sheet-body pt-body">${flashBox()}${doneView()}</div>`;
    case'order':return head('📸',S.place?`Tiệm ảnh · ${S.place.shooter.name}`:'Tiệm ảnh')+`<div class="sheet-body pt-body">${flashBox()}${orderView()}</div>`;
    case'photo':return head('🖼️','Ảnh của bạn','album')+`<div class="sheet-body pt-body">${flashBox()}${photoView()}</div>`;
    default:return head('🖼️','Album ảnh')+`<div class="sheet-body pt-body">${flashBox()}${albumView()}</div>`;
  }
}

/* ---------------------------------------------------------------- pictures: drawn after each render */
const PAINT=new Map();let SEQ=0;
/** <img> of a photo (album, portfolio, shots): its JPEG is made after the render. */
function img(photo,width,cls='',alt='Ảnh chụp',preview=false){const k='p'+(++SEQ);PAINT.set(k,{photo,width,preview});return `<img class="pt-img ${cls}" data-pt-img="${k}" alt="${esc(alt)}" width="${width}" height="${Math.round(width*(preview?1.18:1.25))}">`;}
function paintAll(root){
  for(const im of root.querySelectorAll('img[data-pt-img]')){const job=PAINT.get(im.dataset.ptImg);if(!job)continue;
    photoURL(job.photo,{width:job.width*2,cat:petCat(),preview:job.preview}).then(url=>{if(url&&im.isConnected)im.src=url;});}
  PAINT.clear();
  const cam=root.querySelector('canvas[data-pt-cam]');if(cam){if(S.cam)S.cam.phase='';else paintCam(cam);}   // a countdown draws its own frames
  const pk=root.querySelector('canvas[data-pt-pick]');if(pk)paintPick();
}

/* ---------------------------------------------------------------- 📸 studio: the queue */
function studioView(){
  const s=S.studio;if(!s)return wait();
  if(!s.shooter)return `<p class="pt-empty">📸</p><p class="pt-muted pt-center">Mở Tiệm ảnh Tách Tách để nhận chụp cho người chơi khác.</p>`;
  const now=Date.now()/1000;
  const card=o=>{const p=pkgOf(o.pkg),w=o.wish||{},left=Math.max(0,o.until-now),h=Math.floor(left/3600);
    const wb=w.bd&&w.bd!=='any'?named(C().backdrops,w.bd):null,wm=w.mood&&w.mood!=='any'?named(C().moods,w.mood):null;
    const who=[o.snap?.mate?`💑 ${esc(o.snap.mate.n)}`:'',o.snap?.baby?`👶 ${esc(o.snap.baby.n)}`:'',o.snap?.pet?`🐾 ${esc(o.snap.pet.n||'')}`:'',o.snap?.shop?`${PRODUCT[o.snap.shop.p]||'🎁'} ${esc(o.snap.shop.n)}`:''].filter(Boolean).join(' · ');
    return `<article class="pt-order ${o.status}"><div class="pt-order-top"><span class="pt-pk">${p.emoji}</span><div class="grow"><b>${esc(o.buyer.name)}</b><small>${esc(p.name)} · <b>${fmt(o.price)} xu</b>${o.price<o.list?` <i class="pt-offer">trả giá</i>`:''}</small></div>
      <span class="pt-left" title="Còn">⏳ ${h}h</span></div>
      ${who?`<p class="pt-who">${who}</p>`:''}${o.note?`<p class="pt-note-in">✏️ ${esc(o.note)}</p>`:''}<p class="pt-wish">${wb?`<span>${wb.emoji} ${esc(wb.name)}</span>`:'<span>🎲 Phông tùy thợ</span>'}${wm?`<span>${wm.emoji} ${esc(wm.name)}</span>`:''}</p>
      <div class="pt-row">${o.status==='open'?btn('✓ Nhận đơn','accept',{id:o.id},'primary')+btn('✕','decline',{id:o.id},'ghost'):btn(`📷 Chụp${o.sess?.shots?.length?` (${o.sess.shots.length}/${C().shots})`:''}`,'shoot',{id:o.id},'primary')+btn('✕','decline',{id:o.id},'ghost')}</div></article>`;};
  const q=s.queue||[];
  const prices=(s.pkgs||[]).map(p=>`<div class="pt-price"><span>${p.emoji} ${esc(p.name)}</span><span class="pt-step">${btn('−','price',{pkg:p.id,d:-50},'ghost small')}<b>${fmt(p.price)}</b>${btn('+','price',{pkg:p.id,d:50},'ghost small')}</span></div>`).join('');
  return `<p class="pt-stats"><span>✓ ${fmt(s.stats.done)} ảnh</span><span>★ ${s.stats.stars||'–'}</span><span>${s.open?'🟢 Đang nhận đơn':'⚪ Tạm nghỉ'}</span></p>
    ${q.length?q.map(card).join(''):'<p class="pt-empty">🕊️</p><p class="pt-muted pt-center">Chưa có khách đặt. Bạn bè ghé tiệm sẽ thấy nút 📸 Đặt chụp.</p>'}
    <details class="pt-more"><summary>⚙️ Bảng giá · nhận đơn</summary>${prices}
      <p class="pt-muted">Giá NPC ×${C().mult} mặc định · phí phố ${C().burn}% khi giao ảnh.</p>
      <div class="pt-row">${btn(s.open?'⚪ Tạm nghỉ nhận đơn':'🟢 Mở nhận đơn','open',{v:s.open?'0':'1'},'ghost')}</div></details>
    ${(s.recent||[]).length?`<details class="pt-more"><summary>🕘 Đơn gần đây</summary>${s.recent.map(o=>`<p class="pt-line"><span>${pkgOf(o.pkg).emoji} ${esc(o.buyer.name)}</span><span>${STATUS[o.status]||o.status}${o.status==='done'?` · +${fmt(o.pay)}`:''}</span></p>`).join('')}</details>`:''}`;
}

/* ---------------------------------------------------------------- 📷 the session */
const TABS=[['bd','🎨','Phông'],['light','💡','Ánh sáng'],['frame','🖼️','Khung hình'],['pose','🧍','Dáng'],['face','😊','Biểu cảm'],['prop','🎀','Đạo cụ']];
function shootPhoto(over={}){const o=S.order;return {pkg:o.pkg,snap:o.snap,set:{...S.set},q:null,rt:null,by:'',day:'',...over};}
function startSession(o){
  const c=C(),w=o.wish||{},snap=o.snap||{};
  S.order=o;S.view='shoot';S.shots=(o.sess?.shots||[]).slice();S.beat=o.sess?.beat||null;S.pick=0;S.rt={sang:0,am:0,min:0,vig:0};S.result=null;
  const bd=w.bd&&w.bd!=='any'?w.bd:o.pkg==='san_pham'?'ban_sp':o.pkg==='doi'?'cuoi':'kem';
  S.set={bd,light:'mem',frame:pkgOf(o.pkg).fit?.[0]||'nua',pose:snap.mate?'tim_to':'v',face:'auto',prop:'none',...(S.shots.at(-1)?.set||{})};
  S.tab=o.pkg==='san_pham'?'bd':'bd';
  if(S.shots.length>=c.shots){S.view='pick';}
  render();
}
function chips(tab){
  const c=C(),o=S.order,two=!!o.snap?.mate,prod=o.pkg==='san_pham';
  let list=[];
  if(tab==='bd')list=c.backdrops.filter(b=>b.group!=='island'||o.snap?.isl).map(b=>[b.id,b.emoji,b.name]);
  if(tab==='light')list=c.lights.map(l=>[l.id,l.emoji,l.name]);
  if(tab==='frame')list=c.framings.map(f=>[f.id,f.emoji,f.name]);
  if(tab==='pose')list=[...(two?c.group_poses:[]),...c.poses].map(id=>[id,POSE[id]?.emoji||'🧍',POSE[id]?.name||id]);
  if(tab==='face')list=c.faces.map(id=>[id,FACE[id]?.emoji||'✨',FACE[id]?.name||id]);
  if(tab==='prop')list=c.props.map(id=>[id,id==='none'?'🚫':PROP_EMOJI[id]||'🎀',id==='none'?'Không':(PROPS.find(p=>p.id===id)?.name||id)]);
  if(prod&&['pose','face','prop'].includes(tab))return '<p class="pt-muted">Chụp sản phẩm: chọn phông, đèn và khung là đủ.</p>';
  return `<div class="pt-chips" role="radiogroup">${list.map(([id,e,n])=>`<button type="button" class="pt-chip ${S.set[tab]===id?'on':''}" role="radio" aria-checked="${S.set[tab]===id}" data-pt="set" data-k="${tab}" data-v="${esc(id)}"${S.cam?' disabled':''}><span aria-hidden="true">${e}</span>${esc(n)}</button>`).join('')}</div>`;
}
function wishLine(){
  const c=C(),w=S.order.wish||{},wb=w.bd&&w.bd!=='any'?named(c.backdrops,w.bd):null,wm=w.mood&&w.mood!=='any'?named(c.moods,w.mood):null,p=pkgOf(S.order.pkg);
  return `<p class="pt-wish"><span>${p.emoji} ${esc(p.name)}</span>${wb?`<span class="want" title="${esc('Khách muốn')}">🎯 ${wb.emoji} ${esc(wb.name)}</span>`:''}${wm?`<span class="want" title="${esc('Khách muốn')}">🎯 ${wm.emoji} ${esc(wm.name)}</span>`:''}</p>`;
}
function shootView(){
  const c=C(),n=S.shots.length;
  const slots=Array.from({length:c.shots},(_,i)=>{const s=S.shots[i];if(!s)return `<li class="pt-slot empty">${i+1}</li>`;
    const [cls,t]=Q_TAG[s.q]||['',''];return `<li class="pt-slot">${img(shootPhoto({set:s.set,q:s.q}),72,'','Kiểu '+(i+1),true)}<span class="pt-q ${cls}">${t}</span></li>`;}).join('');
  return `${wishLine()}<div class="pt-cam ${S.cam?'live':''}" data-pt-camwrap><canvas data-pt-cam class="pt-cv" role="img" aria-label="Màn hình máy ảnh"></canvas>
      <div class="pt-count" aria-live="polite"></div><div class="pt-ring" aria-hidden="true"></div></div>
    <nav class="pt-tabs" role="tablist">${TABS.map(([k,e,l])=>`<button type="button" role="tab" class="${S.tab===k?'on':''}" aria-selected="${S.tab===k}" data-pt="tab" data-k="${k}"><span aria-hidden="true">${e}</span><small>${esc(l)}</small></button>`).join('')}</nav>
    ${chips(S.tab)}
    <ol class="pt-slots">${slots}</ol>
    <div class="pt-bar">${S.cam?`<button type="button" class="btn primary pt-snap" data-pt="snap">📸 Bấm!</button>`:btn(`📸 Chụp kiểu ${n+1}/${c.shots}`,'go',{}, 'primary pt-snap')}</div>
    <p class="pt-muted pt-center">Đếm 3-2-1 · chờ khách đứng yên, mở mắt · bấm ngay lúc đó.</p>`;
}
/** The camera's screen: the photo as it would be now (or the moment of the countdown). */
function paintCam(cv,moment=null){
  const w=Math.min(360,cv.parentElement?.clientWidth||360),r=Math.min(2,globalThis.devicePixelRatio||1);
  return paintPhoto(cv,shootPhoto(),{scale:w*r/436,cat:petCat(),moment,preview:true}).then(()=>{cv.style.width=w+'px';});
}
/* the countdown: 3-2-1 (count), the subject settles (lead), holds (hold), blinks (blink), then the pose is gone */
async function go(){
  if(S.cam||!S.beat)return;
  const cv=S.dlg.querySelector('canvas[data-pt-cam]');if(!cv)return;
  const frames={};const w=cv.width;
  for(const m of ['settle','hold','blink','late']){const t=document.createElement('canvas');await paintPhoto(t,shootPhoto(),{scale:w/436,cat:petCat(),moment:m,preview:true});frames[m]=t;}
  S.cam={t0:performance.now(),frames,beat:S.beat,raf:0,phase:''};
  render();
  const b=S.cam.beat,end=b.count+b.lead+b.hold+b.blink+2.2;
  const tick=()=>{
    if(!S.cam)return;
    const el=(performance.now()-S.cam.t0)/1000,x=el-b.count;
    const phase=el<b.count?'count':x<b.lead?'settle':x<=b.lead+b.hold?'hold':x<=b.lead+b.hold+b.blink?'blink':'late';
    const box=S.dlg.querySelector('[data-pt-camwrap]'),c=box?.querySelector('canvas');
    if(box&&phase!==S.cam.phase){S.cam.phase=phase;box.dataset.phase=phase;
      const src=frames[phase==='count'?'settle':phase];
      if(c&&src){if(c.width!==src.width||c.height!==src.height){c.width=src.width;c.height=src.height;c.style.width=Math.round(src.width/Math.min(2,globalThis.devicePixelRatio||1))+'px';}
        const k=c.getContext('2d');k.setTransform(1,0,0,1,0,0);k.clearRect(0,0,c.width,c.height);k.drawImage(src,0,0);}}
    const cnt=box?.querySelector('.pt-count');if(cnt){const t=phase==='count'?String(3-Math.floor(el)):phase==='hold'?'📸':'';if(cnt.textContent!==t)cnt.textContent=t;}
    if(el>end){snap(el);return;}
    S.cam.raf=requestAnimationFrame(tick);
  };
  S.cam.raf=requestAnimationFrame(tick);
}
function stopCam(){if(S.cam?.raf)cancelAnimationFrame(S.cam.raf);S.cam=null;}
async function snap(el){
  if(!S.cam)return;
  const t=el??(performance.now()-S.cam.t0)/1000;stopCam();
  const n=S.shots.length,r=await post('shot',{id:S.order.id,n,set:S.set,el:Math.round(t*1000)/1000});
  if(!r){render();return;}
  S.shots.push(r.shot);S.beat=r.beat;S.flash={text:r.shot.q==='good'?'✓ Đẹp! Khách đứng yên, mở mắt.':Q_TAG[r.shot.q][1],good:r.shot.q==='good'};
  if(!r.left){S.view='pick';S.pick=Math.max(0,S.shots.findIndex(s=>s.q==='good'));}
  render();
}

/* ---------------------------------------------------------------- 🖼️ pick the best, retouch, deliver */
function pickView(){
  const c=C(),R=c.retouch,names={sang:'☀️ Độ sáng',am:'🌡️ Độ ấm',min:'✨ Mịn da',vig:'⭕ Viền tối'};
  const over=Object.entries(S.rt).reduce((t,[k,v])=>t+Math.abs(v),0)>c.retouch_over;
  return `${wishLine()}<div class="pt-cam"><canvas data-pt-pick class="pt-cv" role="img" aria-label="Ảnh đã chọn"></canvas></div>
    <ol class="pt-slots pick">${S.shots.map((s,i)=>{const [cls,t]=Q_TAG[s.q]||['',''];return `<li><button type="button" class="pt-slot ${S.pick===i?'on':''}" data-pt="pick" data-i="${i}" aria-pressed="${S.pick===i}">${img(shootPhoto({set:s.set,q:s.q}),72,'','Kiểu '+(i+1),true)}<span class="pt-q ${cls}">${t}</span></button></li>`;}).join('')}</ol>
    <div class="pt-sliders">${Object.entries(R).map(([k,[lo,hi]])=>`<label><span>${names[k]}</span><input type="range" min="${lo}" max="${hi}" step="1" value="${S.rt[k]}" data-rt="${k}"><output>${signed(S.rt[k])}</output></label>`).join('')}</div>
    ${over?'<p class="pt-flash bad">Chỉnh hơi quá tay rồi.</p>':''}
    <div class="pt-bar">${btn('🖼️ Giao ảnh','deliver',{},'primary')}</div>`;
}
function paintPick(){
  const cv=S.dlg?.querySelector('canvas[data-pt-pick]');const s=S.shots[S.pick];if(!cv||!s)return;
  const w=Math.min(360,cv.parentElement?.clientWidth||360),r=Math.min(2,globalThis.devicePixelRatio||1);
  paintPhoto(cv,shootPhoto({set:s.set,q:s.q,rt:{...S.rt}}),{scale:w*r/436,cat:petCat(),preview:true}).then(()=>{cv.style.width=w+'px';});
}
function doneView(){
  const r=S.result;if(!r)return wait();
  return `<div class="pt-done"><p class="pt-stars" aria-label="${r.stars} sao">${stars(r.stars)}</p>
    ${r.misses?.length?`<ul class="pt-misses">${r.misses.map(m=>`<li>${esc(m)}</li>`).join('')}</ul>`:'<p class="pt-muted pt-center">Khách rất ưng ý!</p>'}
    <p class="pt-pay">+${fmt(r.pay)} xu <small>(phí phố ${fmt(r.burn)} xu)</small></p>
    <div class="pt-bar">${btn('📸 Về sổ khách','studio',{},'primary')}</div></div>`;
}

/* ---------------------------------------------------------------- 🛒 the buyer's order sheet */
function defaults(p){
  const can=p?.can||{},first=(p?.pkgs||[]).find(x=>ok(x.id,can))?.id||'chan_dung',pk=(p?.pkgs||[]).find(x=>x.id===first);
  return {pkg:first,price:pk?.price||0,mate:false,baby:'',pet:'',bd:'any',mood:'any',shop:can.shops?.[0]?.c||'',product:'tra_sua',note:''};
}
function ok(pkg,can){return pkg==='doi'?!!can.mate:pkg==='day_thang'?!!can.babies?.length:pkg==='gia_dinh'?!!(can.mate||can.babies?.length||can.pets?.length):pkg==='san_pham'?!!can.shops?.length:true;}
function why(pkg){return {doi:'Cần người thương',day_thang:'Cần có bé',gia_dinh:'Cần người thương, bé hoặc pet',san_pham:'Cần một chỗ làm'}[pkg]||'';}
function orderView(){
  const p=S.place;if(!p)return wait();
  const f=S.form,can=p.can||{},c=C(),pk=(p.pkgs||[]).find(x=>x.id===f.pkg)||{};
  const folio=(p.photos||[]).length?`<div class="pt-folio" aria-label="Ảnh thợ đã chụp">${p.photos.map(ph=>img({...ph.data,id:ph.id},96,'',`Ảnh ${pkgOf(ph.pkg).name}`)).join('')}</div>`:'';
  const opt=(k,v,label,on)=>`<button type="button" class="pt-chip ${on?'on':''}" data-pt="form" data-k="${k}" data-v="${esc(v)}" aria-pressed="${on}">${label}</button>`;
  const pkgs=(p.pkgs||[]).map(x=>{const good=ok(x.id,can);return `<button type="button" class="pt-pkg ${f.pkg===x.id?'on':''}" data-pt="form" data-k="pkg" data-v="${x.id}"${good?'':' disabled'} aria-pressed="${f.pkg===x.id}"><span class="pt-pk">${x.emoji}</span><b>${esc(x.name)}</b><small>${good?`${fmt(x.price)} xu`:esc(why(x.id))}</small></button>`;}).join('');
  const along=[];
  if(can.mate&&f.pkg!=='san_pham')along.push(opt('mate',f.mate?'0':'1',`💑 ${esc(can.mate.n)}`,f.mate||f.pkg==='doi'));
  if(can.babies?.length&&f.pkg!=='san_pham')for(const b of can.babies)along.push(opt('baby',f.baby===b.id&&f.pkg!=='day_thang'?'':b.id,`👶 ${esc(b.n)}`,f.baby===b.id));
  if(can.pets?.length&&f.pkg!=='san_pham')for(const pt of can.pets.slice(0,6))along.push(opt('pet',f.pet===pt.id?'':pt.id,`🐾 ${esc(pt.n||'Bé cưng')}`,f.pet===pt.id));
  const prod=f.pkg==='san_pham'?`<h4>🛍️ Món chụp</h4><div class="pt-chips">${c.products.map(x=>opt('product',x.id,`${x.emoji} ${esc(x.name)}`,f.product===x.id)).join('')}</div>
    ${can.shops?.length>1?`<div class="pt-chips">${can.shops.map(s=>opt('shop',s.c,esc(s.n),f.shop===s.c)).join('')}</div>`:''}`:'';
  const bds=[['any','🎲','Thợ chọn'],...c.backdrops.filter(b=>(b.group!=='island'||can.island)&&(b.group!=='product'||f.pkg==='san_pham')).map(b=>[b.id,b.emoji,b.name])];
  const moods=f.pkg==='san_pham'?'':`<h4>😊 Không khí</h4><div class="pt-chips">${c.moods.map(m=>opt('mood',m.id,`${m.emoji} ${esc(m.name)}`,f.mood===m.id)).join('')}</div>`;
  const offer=f.price<pk.price;
  const mine=(p.orders||[]).filter(o=>['open','shoot'].includes(o.status));
  return `<p class="pt-stats"><span>✓ ${fmt(p.stats.done)} ảnh</span><span>★ ${p.stats.stars||'–'}</span><span>${p.open?'🟢 Đang nhận':'⚪ Tạm nghỉ'}</span></p>${folio}
    ${p.self?'<p class="pt-muted pt-center">Đây là tiệm của bạn.</p>':`
    <h4>📦 Gói chụp</h4><div class="pt-pkgs">${pkgs}</div>
    ${along.length?`<h4>👥 Đi cùng</h4><div class="pt-chips">${along.join('')}</div>`:''}${prod}
    <h4>🎨 Phông nền</h4><div class="pt-chips">${bds.map(([id,e,n])=>opt('bd',id,`${e} ${esc(n)}`,f.bd===id)).join('')}</div>${moods}
    <h4>💰 Giá</h4><div class="pt-price big"><span class="pt-step">${btn('−','fprice',{d:-50},'ghost small')}<b>${fmt(f.price)} xu</b>${btn('+','fprice',{d:50},'ghost small')}</span>
      <small>${offer?'Trả giá: thợ có thể từ chối':`Giá của thợ · ${fmt(pk.floor)}–${fmt(pk.cap)} xu`}</small></div>
    <label class="pt-note"><span>✏️ Lời nhắn</span><input type="text" maxlength="80" value="${esc(f.note)}" data-pt-note placeholder="Ví dụ: chụp xinh nha!"></label>
    ${mine.length?mine.map(o=>`<p class="pt-line"><span>${pkgOf(o.pkg).emoji} ${esc(pkgOf(o.pkg).name)}</span><span>${STATUS[o.status]}</span></p>`).join(''):''}
    <div class="pt-bar">${btn(`📸 Đặt chụp · ${fmt(f.price)} xu`,'order',{},'primary')}</div>
    <p class="pt-muted pt-center">Xu được giữ đến khi thợ giao ảnh vào 🖼️ Album. Hủy trước khi thợ nhận: hoàn đủ.</p>`}`;
}

/* ---------------------------------------------------------------- 🖼️ the album */
function albumView(){
  const a=S.album;if(!a)return wait();
  const going=(a.orders||[]).filter(o=>['open','shoot'].includes(o.status)||o.status!=='done');
  const ords=going.length?`<section class="pt-going">${going.slice(0,6).map(o=>`<p class="pt-line"><span>${pkgOf(o.pkg).emoji} ${esc(o.shooter.name)} · ${fmt(o.price)} xu</span><span>${STATUS[o.status]||o.status}${o.status==='open'?' '+btn('Hủy','cancel',{id:o.id},'ghost small'):''}</span></p>`).join('')}</section>`:'';
  const grid=(a.photos||[]).length?`<div class="pt-grid">${a.photos.map((p,i)=>`<button type="button" class="pt-tile" data-pt="view" data-i="${i}">${img({...p.data,id:p.id},150,'',`Ảnh ${pkgOf(p.pkg).name} của ${p.by.name}`)}<span>${a.pfp===p.id?'🙂 ':''}${stars(p.stars)}</span></button>`).join('')}</div>`
    :`<p class="pt-empty">🖼️</p><p class="pt-muted pt-center">${S.old?'Chưa có ảnh cũ.':'Chưa có ảnh. Ghé 📸 Tiệm ảnh của bạn bè để đặt chụp nhé.'}</p>`;
  const more=a.more?`<div class="pt-row">${btn('Xem thêm','more',{},'ghost')}</div>`:'';
  const old=!S.old&&a.archived?`<div class="pt-row">${btn(`🗄️ Xem cũ hơn (${fmt(a.archived)})`,'old',{},'ghost')}</div>`:S.old?`<div class="pt-row">${btn('← Ảnh mới','new',{},'ghost')}</div>`:'';
  return `${S.old?'':ords}${grid}${more}${old}`;
}
function photoView(){
  const p=S.photo;if(!p)return wait();
  const pfp=S.album?.pfp===p.id;
  return `<figure class="pt-big">${img({...p.data,id:p.id},300,'big',`Ảnh ${pkgOf(p.pkg).name}`)}<figcaption>${stars(p.stars)} · 📸 ${esc(p.by.name)}</figcaption></figure>
    <div class="pt-actions">${btn(pfp?'🙂 Bỏ ảnh hồ sơ':'🙂 Đặt làm ảnh hồ sơ','pfp',{id:pfp?'':p.id},pfp?'ghost':'primary')}
      ${btn('🖼️ Treo trong nhà','hang',{id:p.id},'ghost')}${btn('💾 Lưu ảnh','save',{},'ghost')}
      ${btn(p.folio?'👁 Ẩn ở tiệm thợ':'👁 Hiện ở tiệm thợ','folio',{id:p.id,show:p.folio?'0':'1'},'ghost')}</div>`;
}

/* ---------------------------------------------------------------- taps */
async function onClick(op,d){
  switch(op){
    case'close':close();return;
    case'studio':stopCam();await openStudio();return;
    case'album':await openAlbum(S.old);return;
    case'accept':{const r=await post('accept',{id:d.id});if(r?.order){await openStudio();const o=(S.studio?.queue||[]).find(x=>x.id===d.id);if(o)startSession(o);}return;}
    case'decline':{if(!await S.env.confirmAction('Từ chối đơn chụp?','Tiền giữ trả lại khách.','Từ chối'))return;await post('decline',{id:d.id});await openStudio();return;}
    case'shoot':{const o=(S.studio?.queue||[]).find(x=>x.id===d.id);if(o)startSession(o);return;}
    case'price':{const s=S.studio,p=s.pkgs.find(x=>x.id===d.pkg);if(!p)return;const v=Math.max(p.floor,Math.min(p.cap,p.price+Number(d.d)));if(v===p.price)return;
      const r=await post('studio',{prices:{[p.id]:v}});if(r?.shooter)S.studio=r;render();return;}
    case'open':{const r=await post('studio',{open:d.v==='1'});if(r?.shooter)S.studio=r;render();return;}
    case'tab':S.tab=d.k;render();return;
    case'set':S.set={...S.set,[d.k]:d.v};render();return;
    case'go':await go();return;
    case'snap':await snap();return;
    case'pick':S.pick=Number(d.i)||0;render();return;
    case'deliver':{const r=await post('deliver',{id:S.order.id,pick:S.pick,rt:S.rt});if(r?.photo){S.result=r;S.view='done';COUNT.at=0;render();}return;}
    case'form':formSet(d.k,d.v);render();return;
    case'fprice':{const pk=S.place.pkgs.find(x=>x.id===S.form.pkg);S.form.price=Math.max(pk.floor,Math.min(pk.cap,S.form.price+Number(d.d)));render();return;}
    case'order':return order();
    case'cancel':{if(!await S.env.confirmAction('Hủy đơn chụp?','Xu giữ trả lại ví.','Hủy đơn'))return;await post('cancel',{id:d.id});await openAlbum();return;}
    case'view':{S.photo=S.album.photos[Number(d.i)];S.view='photo';render();return;}
    case'more':return openAlbum(S.old,S.album?.next);
    case'old':return openAlbum(true);
    case'new':return openAlbum(false);
    case'pfp':{const r=await post('pfp',{id:d.id||null});if(r&&S.album)S.album.pfp=r.pfp;render();return;}
    case'hang':{await post('hang',{id:d.id});return;}
    case'folio':{const show=d.show==='1',r=await post('folio',{id:d.id,show});if(r&&S.photo){S.photo.folio=show;}render();return;}
    case'save':return save();
  }
}
function formSet(k,v){
  const f=S.form,p=S.place;
  if(k==='pkg'){const pk=p.pkgs.find(x=>x.id===v),can=p.can||{};f.pkg=v;f.price=pk?.price||f.price;
    if(v==='day_thang'&&!f.baby)f.baby=can.babies?.[0]?.id||'';
    if(v==='gia_dinh'&&can.mate)f.mate=true;
    if(v==='gia_dinh'&&!f.mate&&!f.baby&&!f.pet)f.baby=can.babies?.[0]?.id||'',f.pet=f.baby?'':can.pets?.[0]?.id||'';
    return;}
  if(k==='mate'){f.mate=v==='1';return;}
  f[k]=v;
}
async function order(){
  const f=S.form,p=S.place,pk=pkgOf(f.pkg);
  if(!await S.env.confirmAction(`Đặt chụp ${pk.name}?`,`${fmt(f.price)} xu được giữ đến khi ${p.shooter.name} giao ảnh.`,'📸 Đặt chụp'))return;
  f.rid=f.rid||rid();
  const body={rid:f.rid,place:p.place,pkg:f.pkg,price:f.price,wish:{bd:f.bd,mood:f.pkg==='san_pham'?'any':f.mood},note:f.note,
    mate:f.pkg==='doi'||(f.pkg!=='san_pham'&&f.mate),baby:f.pkg!=='san_pham'&&f.baby?f.baby:null,
    pet:f.pkg!=='san_pham'&&f.pet?f.pet:null,shop:f.pkg==='san_pham'?f.shop:null,product:f.pkg==='san_pham'?f.product:null};
  const r=await post('order',body);
  if(r?.order){f.rid=null;S.env.toast?.(r.message||'📸 Đã đặt chụp!','good');await openAlbum();}
}
async function save(){
  const p=S.photo;if(!p)return;
  try{const cv=document.createElement('canvas');await paintPhoto(cv,{...p.data,id:p.id},{scale:2,cat:petCat()});
    const url=cv.toDataURL('image/png'),a=document.createElement('a');a.href=url;a.download=`anh-pho-co-chuyen-${p.id.slice(-6)}.png`;document.body.append(a);a.click();a.remove();}
  catch(e){flash('Chưa lưu được ảnh. Thử lại nhé.',false);}
}

/* ---------------------------------------------------------------- 🖼️ framed photos at home and the profile photo */
const WALL=new Map();
/** The photos of journey.photo_wall as small JPEGs for the frames (deco-art.js PHOTO_ART), then `done()` redraws. */
export async function loadWall(env,wall,setArt,done){
  const ids=Object.entries(wall||{}).filter(([,id])=>typeof id==='string');if(!ids.length)return;
  let changed=false;
  await Promise.all(ids.map(async([uid,id])=>{
    let p=WALL.get(id);
    if(!p){if(WALL.size>40)WALL.clear();p=env.api.json('/api/photo/one?id='+encodeURIComponent(id)).then(r=>r?.photo?photoURL({...r.photo.data,id},{width:200,preview:true,cat:env.api.content?.journey?.pets||null}):'').catch(()=>'');WALL.set(id,p);}
    const url=await p;if(url&&setArt(uid,url))changed=true;
  }));
  if(changed)done?.();
}
/** <img> markup for a profile photo (social.js profile card), filled after it is drawn. */
export function pfpImg(photo,size=96){
  if(!photo?.data)return '';
  const k='pf'+(++SEQ);
  queueMicrotask(()=>{photoURL({...photo.data,id:photo.id},{width:size*2,preview:true}).then(url=>{const im=document.querySelector(`img[data-pt-pf="${k}"]`);if(im&&url)im.src=url;});});
  return `<img class="pt-pfp" data-pt-pf="${k}" alt="Ảnh hồ sơ" width="${size}" height="${Math.round(size*1.18)}">`;
}
