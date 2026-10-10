/** 🧭 Chỉ đường on the 2.5D island (2.5D only: iso-boot.js / isometric-shell.js).
 *
 * - Authored civic artwork stays visible on the island. Available services get a supported wayfinding stand
 *   beside the path and an artwork hit target, like a workplace door (tap it, or walk up and press E).
 * - The 🧭 sheet lists every destination (places, Thư giãn, every workplace) with a search box. Picking one draws the
 *   route on the road and walks the avatar there; a tap on the ground, the joystick or a key stops it. On arrival the
 *   place opens (a workplace: you go in to work, as when you tap its door).
 * - The island remembers where you were on this device (localStorage mnl.isoSpot); back from work you stand at that
 *   workplace's door. Nothing here touches the save.
 */
import {escapeHTML as esc} from './icons.js';
import {createResidentDirectory} from './isometric/resident-shops.js';
import {townUtilityGroups,townServiceAvailable} from './isometric/town-utilities.js';
// v4/journey.js (emojiOf) and v4/onboard.js (FIRST_JOB) are loaded on first use: they need a document.
let emojiOf=m=>m.emoji||'✨',FIRST_JOB='milk_tea';
const helpers=()=>Promise.all([import('./v4/journey.js'),import('./v4/onboard.js')]).then(([j,o])=>{emojiOf=j.emojiOf;FIRST_JOB=o.FIRST_JOB;}).catch(()=>{});

const SPOT_KEY='mnl.isoSpot';
/** Fallback signposts; the authored town's amenities override positions and provide its civic destinations. */
export const PLACES=[
  {id:'house',icon:'🏠',label:'Nhà của bạn',action:'house',at:{x:2.8,y:6.25},on:e=>Boolean(e.api.state?.journey?.story)},
  {id:'bank',icon:'🏦',label:'Ngân hàng',action:'bank',at:{x:13.25,y:6.25},on:()=>true},
  {id:'rank',icon:'🏆',label:'Bảng xếp hạng',action:'rank',at:{x:20.25,y:6.25},on:()=>true},
  {id:'social',icon:'🛍️',label:'Phố nghề',hint:'Ghé tiệm người chơi khác',action:'social',at:{x:27.25,y:6.25},on:()=>true},
  {id:'fair',icon:'🏮',label:'Chợ đen',action:'fair',at:{x:6.25,y:13.25},on:e=>Boolean(e.api.state?.fair?.show)},
  {id:'wedding',icon:'💍',label:'Lịch cưới · Nhà cưới',action:'liveWed',at:{x:13.25,y:13.25},on:e=>Boolean(live(e)?.flags?.wedding&&live(e)?.welcomed)},
  {id:'quay',icon:'🏪',label:'Quầy của bạn',action:'quay',at:{x:20.25,y:13.25},on:e=>Boolean(e.api.state?.journey?.story&&e.api.content?.journey?.quay)},
  {id:'board',icon:'📌',label:'Nhóm phố',hint:'Bảng tin hàng xóm',action:'nhom',at:{x:6.25,y:20.25},on:()=>true},
  {id:'walk',icon:'🚶',label:'Phố đi dạo',hint:'Gặp người chơi khác',action:'liveWalk',at:{x:13.25,y:20.25},on:e=>Boolean(live(e)?.flags?.street&&live(e)?.welcomed)},
  {id:'date',icon:'💕',label:'Góc hẹn hò',action:'liveDate',at:{x:20.25,y:20.25},on:e=>Boolean(live(e)?.flags?.dating&&live(e)?.welcomed)},
  {id:'marriage',icon:'💒',label:'Hôn nhân & gia đình',action:'marriage',at:{x:27.25,y:13.25},on:()=>true},
];
const OUTINGS=[['fishing','🎣','Ao câu cá'],['boat','🚣','Bến thuyền'],['pool','🏊','Hồ bơi · thể thao']];
let cachedLive=null;
const live=e=>{try{return e.live?.()||cachedLive;}catch{return cachedLive;}};
const fold=s=>String(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/đ/g,'d').replace(/Đ/g,'D').toLowerCase();
const inside=(p,r,m=0)=>p.x>=r.x0-m&&p.x<=r.x1+m&&p.y>=r.y0-m&&p.y<=r.y1+m;
/** client/isometric/model.ts isWalkable, for points this module picks. */
function walkable(nav,p){return Boolean(nav)&&inside(p,nav.bounds)&&nav.roads.some(r=>inside(p,r))&&!nav.obstacles.some(r=>inside(p,r,nav.clearance||.14));}
function nearest(nav,p){
  if(walkable(nav,p))return p;
  for(let d=.25;d<=3;d+=.25)for(let a=0;a<16;a++){const q={x:p.x+Math.cos(a*Math.PI/8)*d,y:p.y+Math.sin(a*Math.PI/8)*d};if(walkable(nav,q))return q;}
  return null;
}

let world=null,envOf=null,line=null,unwatch=null,lineGeometry='',goingTo=null,shown=new Set(),detach=null;
const directory=createResidentDirectory();
let mappedWorld=null,mappedKey='';
function places(){
  const entries=new Map(PLACES.map(p=>[p.id,p]));
  for(const p of world?.townAmenities?.()||[])entries.set(p.id,{on:()=>true,...entries.get(p.id),...p});
  return [...entries.values()].map(p=>({...p,on:env=>p.on(env)&&townServiceAvailable(p.action,env.api.state,env.api.content,live(env),p.actionData)}));
}
function syncShops(env){
  const shops=directory.read(env.api).shops.slice(0,8),key=JSON.stringify(shops);
  if(world&&typeof world.setResidentShops==='function'&&(mappedWorld!==world||key!==mappedKey)){
    mappedWorld=world;mappedKey=key;world.setResidentShops(shops);
  }
}
async function loadShops(env){
  const target=world,request=directory.load(env.api);
  if(dlg?.open)render(env);
  await request;
  if(target!==world||envOf?.()?.api!==env.api)return;
  syncShops(env);if(dlg?.open)render(env);
}
async function visitResident(id,env){
  if(!directory.read(env.api).shops.some(p=>p.id===id))return;
  stopLine();dlg?.open&&dlg.close();await env.act('workVisit',{place:id});
}
function previewDistrict(id,env){
  const district=world?.townDistricts?.().find(d=>d.id===id);if(!district)return;
  if(!world.focusDistrict?.(id)){dlg?.open&&dlg.close();env.toast('Ra phố để xem khu này nhé.');return;}
  dlg?.open&&dlg.close();env.toast(`📍 Đang xem ${district.name}`);
}

/** The real PhaserWorld (app.js adopted it): signposts on each town rebuild, door spawn, the remembered spot. */
export function attachGuide(real,getEnv){
  detach?.();world=real;envOf=getEnv;shown=new Set();mappedWorld=null;
  const s=real.stage,signs=new Map();
  let lastMode=real.mode;
  const remove=id=>{
    const old=signs.get(id);if(!old)return false;
    signs.delete(id);shown.delete(id);
    if(old.visual)s.removeAmenityVisual?.(old.visual,old.hotspot);
    real.hotspots=real.hotspots.filter(h=>h!==old.hotspot);
    s.hits=s.hits.filter(hit=>hit.hotspot!==old.hotspot);
    if(s.removeAmenitySign)s.removeAmenitySign(old.sign);else s.removeWayfindingSign(old.sign);
    return true;
  };
  // A welcome or API update changes availability, not the terrain. Keep unchanged signs and their hit objects.
  const decorate=()=>{
    if(!s||real.mode!=='town')return;
    const env=getEnv();let changed=false;
    for(const p of places()){
      if(!p.on(env)){changed=remove(p.id)||changed;continue;}
      if(real.hotspots.some(h=>h.id==='place:'+p.id)){shown.add(p.id);continue;}
      if(signs.has(p.id))continue;
      const at=nearest(s.navigation,p.at);if(!at)continue;
      shown.add(p.id);
      const id='place:'+p.id,h={id,label:p.label,x:at.x,y:at.y,approach:at,point:real.project(at.x,at.y,0),z:0,range:1.2};
      real.hotspots.push(h);
      const visual=s.addAmenityVisual?.(p,h);
      const sign=(p.art&&visual?s.amenitySign?.(p,visual):null)||s.wayfindingSign(p.label,at,15,190,0x668574);
      h.interactionPoint=sign.getData?.('interactionPoint')||at;
      s.hits.push({hotspot:h,object:sign},{hotspot:h,footprint:{x0:at.x-.45,y0:at.y-.45,x1:at.x+.45,y1:at.y+.45}});
      signs.set(p.id,{hotspot:h,sign,visual});changed=true;
    }
    if(changed){s.requestRender?.();real.wake?.();}
  };
  const refresh=()=>{const env=getEnv();syncShops(env);decorate();if(dlg?.open)render(env);};
  const originalRebuild=s.rebuild;
  // The first town with its buildings: back at the spot remembered on this device.
  let restored=false;const restore=()=>{if(!restored&&real.mode==='town'&&layoutKey(real)>0){restored=true;restoreSpot(real);}};
  const rebuild=(...a)=>{
    // The normal scene rebuild destroys the old signs along with other static objects.
    signs.clear();shown=new Set();const r=originalRebuild.apply(s,a);restore();refresh();
    // Back from work: at that workplace's door, not in the middle of the island.
    if(lastMode==='work'&&real.mode==='town'){const door=real.hotspots.find(h=>h.id==='career:'+real.career);if(door){Object.assign(real.player,door.approach,{path:[],goal:null});real.recenter?.();}}
    lastMode=real.mode;return r;
  };
  s.rebuild=rebuild;
  // A signpost tapped (or reached): open what it stands for.
  const interact=real.onInteract;
  const onInteract=id=>{
    if(typeof id==='string'&&id.startsWith('place:')){arrive(id.slice(6));return;}
    if(typeof id==='string'&&id.startsWith('resident:')){visitResident(id.slice(9),getEnv());return;}
    if(typeof id==='string'&&id.startsWith('district:')){
      const district=real.townDistricts?.().find(d=>d.id===id.slice(9));
      if(district){stopLine();if(district.housingGroup){void import('./v4/residential.js').then(m=>m.openResidential(getEnv(),district.housingGroup)).catch(()=>getEnv().toast('Chưa mở được khu nhà. Thử lại nhé.',true));}else getEnv().toast(`📍 ${district.name} · ${district.description}`);}return;
    }
    interact(id);
  };
  real.onInteract=onInteract;
  const api=getEnv()?.api,socket=live(getEnv()),off=[];let attached=true;
  const subscribe=socket=>{for(const type of ['welcome','state','down'])off.push(socket.on(type,refresh));};
  if(socket)subscribe(socket);
  else import('./v4/live.js').then(m=>{if(!attached)return;cachedLive=m.live;subscribe(cachedLive);refresh();}).catch(e=>console.warn('Chỉ đường:',e));
  api?.addEventListener?.('state',refresh);
  document.addEventListener('mnl:lazy',refresh);  // the deferred catalogue may enable Quầy
  restore();
  refresh();
  const save=()=>{if(restored)saveSpot(real);},timer=setInterval(save,2000);
  addEventListener('pagehide',save);
  detach=()=>{
    attached=false;
    for(const unsubscribe of off)unsubscribe?.();
    api?.removeEventListener?.('state',refresh);document.removeEventListener('mnl:lazy',refresh);
    clearInterval(timer);removeEventListener('pagehide',save);stopLine();
    for(const id of [...signs.keys()])remove(id);
    if(s.rebuild===rebuild)s.rebuild=originalRebuild;
    if(real.onInteract===onInteract)real.onInteract=interact;
  };
}

function layoutKey(real){return real.stage?.buildings?.length||0;}
function saveSpot(real){
  if(real.mode!=='town'||!real.stage)return;
  try{localStorage.setItem(SPOT_KEY,JSON.stringify({x:+real.player.x.toFixed(2),y:+real.player.y.toFixed(2),n:layoutKey(real)}));}catch{/* storage blocked */}
}
function restoreSpot(real){
  let spot=null;try{spot=JSON.parse(localStorage.getItem(SPOT_KEY)||'null');}catch{/* none */}
  if(!spot||spot.n!==layoutKey(real)||real.mode!=='town'||!walkable(real.stage?.navigation,spot))return;
  Object.assign(real.player,{x:spot.x,y:spot.y,path:[],goal:null});real.recenter?.();
}

async function arrive(placeId){
  const p=places().find(x=>x.id===placeId),env=envOf?.();if(!p||!env||!p.on(env))return;
  stopLine();
  if(p.id==='social'){await openGuide(env,{filter:'shops'});return;}
  if(p.housingGroup){await (await import('./v4/residential.js')).openResidential(env,p.housingGroup);return;}
  await env.act(p.action,p.actionData);
}

/* ---- the 🧭 sheet ---- */
let dlg=null,query='',activeFilter='all';
const FILTERS=[['all','Tất cả'],['districts','Khu phố'],['places','Tiện ích'],['careers','Nơi làm việc'],['shops','Tiệm người chơi']];
function destinations(env){
  const out=[];
  for(const d of world?.townDistricts?.()||[])out.push({dest:'district:'+d.id,icon:d.icon,label:d.name,hint:d.description,features:d.features||[],color:d.color,group:'Khu phố trên đảo',filter:'districts'});
  const availablePlaces=places().filter(p=>p.on(env)&&(!world||world.mode!=='town'||shown.has(p.id)));
  for(const p of availablePlaces)out.push({dest:'place:'+p.id,icon:p.icon,label:p.label,hint:p.hint||'',group:'Tiện ích trong phố',filter:'places'});
  const actionKey=p=>p.action+':'+JSON.stringify(p.actionData||{}),mappedActions=new Set(availablePlaces.map(actionKey));
  for(const group of townUtilityGroups(env.api.state,env.api.content,live(env)))for(const item of group.items){
    if(!mappedActions.has(actionKey(item)))out.push({dest:'utility:'+(item.id||item.action),icon:item.emoji,label:item.label,hint:'Mở tiện ích',group:group.label,filter:'places',direct:true});
  }
  for(const [k,icon,label] of OUTINGS)out.push({dest:'outing:'+k,icon,label,hint:'Thư giãn, miễn phí',group:'Thư giãn',filter:'places'});
  const J=env.api.state?.journey,open=new Set(J?.unlocked||[]),free=J&&J.story===false;
  const cur=env.api.state?.current;
  for(const m of (env.api.content?.catalogue||[]).filter(c=>c.playable!==false)){
    const locked=!free&&J?.story&&!open.has(m.id)&&!env.api.state?.careers?.[m.id]?.started;
    out.push({dest:'career:'+m.id,icon:emojiOf(m),label:m.place||m.name,hint:(m.id===cur?'Nơi bạn đang làm · ':'')+(locked?'🔒 chưa mở':(m.name||'')),group:'Nơi làm việc',filter:'careers',first:m.id===FIRST_JOB&&!cur});
  }
  for(const p of directory.read(env.api).shops){
    const m=env.api.content?.catalogue?.find(c=>c.id===p.career);
    out.push({dest:'resident:'+p.id,icon:p.kind==='quay'?'🏪':emojiOf(m||{}),label:p.name,hint:`${p.ownerName} · ${p.kind==='quay'?'Quầy riêng':m?.name||'Nơi làm việc'}`,group:'Tiệm người chơi',filter:'shops',visit:true});
  }
  return out;
}
function shopIntro(env){
  const state=directory.read(env.api),own=places().find(p=>p.id==='quay')?.on(env);
  const message={idle:'Mở danh sách để tìm chỗ làm công khai của người chơi.',guest:'Đăng nhập để xem và ghé chỗ làm công khai của người chơi.',loading:'Đang tìm các chỗ làm công khai…',empty:'Chưa có chỗ làm công khai trong danh sách này. Bạn có thể mở quầy và mời hàng xóm ghé.',error:'Chưa tải được danh sách tiệm. Mở lại sau một phút để thử lại.',ready:'Ghé tiệm để xem dịch vụ và tình hình hiện tại. Một số tiệm có lối ghé trên phố ven sông.'}[state.status];
  return `<section class="iso-guide-shops"><div><span aria-hidden="true">🛍️</span><div><h3>Phố tiệm người chơi</h3><p role="status">${message}</p></div></div>${state.status==='guest'?'<button type="button" class="btn ghost" data-guide-action="login">Đăng nhập</button>':`<div class="iso-guide-shop-actions">${own?'<button type="button" class="btn primary" data-guide-action="own">Mở Quầy của bạn</button>':''}<button type="button" class="btn ghost" data-guide-action="mine">Chỗ của tôi · Quyền ghé thăm</button><button type="button" class="btn ghost" data-guide-action="public">Xem toàn bộ danh sách</button></div><p class="iso-guide-shop-note">${own?'Tạo hoặc quản lý quầy trong Quầy của bạn. ':'Quầy riêng mở sau phần giới thiệu hành trình. '}Trong Chỗ của tôi, chọn “Mọi người” để cho phép ghé thăm công khai.</p>`}</section>`;
}
function listHTML(env){
  const q=fold(query.trim()),rows=destinations(env).filter(d=>(activeFilter==='all'||d.filter===activeFilter)&&(!q||fold(d.label+' '+d.hint+' '+(d.features||[]).join(' ')).includes(q)));
  const intro=(activeFilter==='shops'||activeFilter==='all'&&!q)?shopIntro(env):'';
  if(!rows.length)return intro+(q?`<p class="iso-guide-empty">Không thấy nơi nào khớp “${esc(query)}”. Thử tên khu phố, nghề hoặc người chơi.</p>`:activeFilter==='shops'?'':'<p class="iso-guide-empty">Chưa có điểm đến trong nhóm này.</p>');
  let html=(activeFilter==='shops'?intro:'')+`<p class="iso-guide-count">${rows.length} điểm đến${q?' phù hợp':''}</p>`,group='';
  for(const d of rows){
    if(d.group!==group){if(group)html+='</div>';group=d.group;html+=`<h3>${esc(group)}</h3><div class="iso-guide-list${d.filter==='districts'?' iso-guide-districts':''}">`;}
    const district=d.filter==='districts',color=/^#[0-9a-f]{6}$/i.test(d.color)?d.color:'#567e55';
    const copy=`<span class="iso-guide-ico" aria-hidden="true">${esc(d.icon)}</span><span class="iso-guide-copy"><b>${esc(d.label)}</b>${d.hint?`<small>${esc(d.hint)}</small>`:''}${district?`<span class="iso-guide-features">${d.features.map(f=>`<span>${esc(f)}</span>`).join('')}</span>`:''}</span>`;
    if(district){
      html+=`<article class="iso-guide-row iso-guide-district" style="--district-color:${color}" aria-label="${esc(d.label)}"><div class="iso-guide-district-info">${copy}</div><div class="iso-guide-district-actions"><button type="button" class="btn ghost" data-guide-preview="${esc(d.dest.slice(9))}" aria-label="Xem khu ${esc(d.label)}">Xem khu</button><button type="button" class="btn primary" data-action="isoGo" data-dest="${esc(d.dest)}" aria-label="Đi tới ${esc(d.label)}">Đi tới ›</button></div></article>`;
    }else html+=`<button type="button" class="iso-guide-row${d.first?' is-first':''}" data-action="isoGo" data-dest="${esc(d.dest)}">${copy}<span class="iso-guide-go" aria-hidden="true">${d.direct?'Mở':d.visit?'Ghé':'Đi'} ›</span></button>`;
  }
  return html+'</div>'+(activeFilter==='all'?intro:'');
}
function render(env){if(dlg){const body=dlg.querySelector('.iso-guide-body'),html=listHTML(env);if(body.innerHTML!==html)body.innerHTML=html;for(const b of dlg.querySelectorAll?.('[data-guide-filter]')||[])b.setAttribute('aria-pressed',String(b.dataset.guideFilter===activeFilter));}}
export async function openGuide(env,{filter='all'}={}){
  await helpers();
  if(!dlg){
    dlg=document.createElement('dialog');dlg.className='sheet v4-sheet medium iso-guide-sheet';dlg.setAttribute('aria-label','Chỉ đường');
    dlg.innerHTML=`<header class="sheet-head"><div class="grow"><h2>🧭 Chỉ đường</h2><p>Chọn “Đi” để tự đi theo đường, hoặc “Mở” để dùng tiện ích. Chạm đất hoặc di chuyển để dừng đi.</p></div><button type="button" class="icon-btn" data-guide-close aria-label="Đóng">✕</button></header>
      <div class="iso-guide-search"><input type="search" class="input" placeholder="Tìm khu phố, tiện ích, nghề hoặc người chơi…" aria-label="Tìm nơi muốn tới hoặc tiện ích" autocomplete="off" enterkeyhint="search"></div>
      <nav class="iso-guide-filters" aria-label="Lọc điểm đến">${FILTERS.map(([id,label])=>`<button type="button" data-guide-filter="${id}" aria-pressed="${id==='all'}">${label}</button>`).join('')}</nav>
      <div class="sheet-body iso-guide-body"></div>`;
    document.body.append(dlg);
    const input=dlg.querySelector('input');
    input.addEventListener('input',()=>{query=input.value;render(envOf?.()||env);});
    input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();dlg.querySelector('.iso-guide-body [data-action="isoGo"]')?.click();}});
    dlg.querySelector('[data-guide-close]').addEventListener('click',()=>dlg.close());
    dlg.addEventListener('click',async e=>{
      if(e.target===dlg){dlg.close();return;}
      const current=envOf?.()||env,tab=e.target.closest('[data-guide-filter]'),preview=e.target.closest('[data-guide-preview]'),action=e.target.closest('[data-guide-action]')?.dataset.guideAction;
      if(preview){previewDistrict(preview.dataset.guidePreview,current);return;}
      if(tab){activeFilter=tab.dataset.guideFilter;render(current);if(activeFilter==='shops')await loadShops(current);return;}
      if(!action)return;
      dlg.close();
      try{
        if(action==='login')await current.act('v4AccountOpen',{mode:'login'});
        if(action==='own')await current.act('quay');
        if(action==='mine'||action==='public')await current.act('workVisit',{scope:action});
      }catch{current.toast('Chưa mở được nơi này. Thử lại nhé.',true);}
    });
  }
  query='';activeFilter=FILTERS.some(([id])=>id===filter)?filter:'all';dlg.querySelector('input').value='';render(env);
  if(!dlg.open)dlg.showModal();
  if(matchMedia('(pointer: fine)').matches)dlg.querySelector('input').focus({preventScroll:true});
  void loadShops(env);
}

/* ---- walking there ---- */
function stopLine(){unwatch?.();unwatch=null;const hadLine=Boolean(line);line?.destroy();line=null;lineGeometry='';goingTo=null;if(hadLine)world?.stage?.requestRender?.();}
function drawRoute(real){
  const s=real.stage;if(!s)return;
  const points=[real.player,...real.player.path],geometry=points.map(p=>p.x+','+p.y).join(';');
  if(geometry===lineGeometry)return;
  lineGeometry=geometry;
  if(!line){line=s.add.graphics();line.setDepth(-5000);}
  line.clear();const pts=points.map(p=>real.project(p.x,p.y,0));
  if(pts.length<2)return;
  const stroke=(width,colour,alpha)=>{line.lineStyle(width,colour,alpha);line.beginPath();line.moveTo(pts[0].x,pts[0].y);for(const p of pts.slice(1))line.lineTo(p.x,p.y);line.strokePath();};
  stroke(16,0x7a4b2e,.45);stroke(8,0xfff3da,1);   // a cream path with a brown edge: readable on grass and paving
  const end=pts[pts.length-1];line.fillStyle(0x7a4b2e,.5).fillCircle(end.x,end.y,15).fillStyle(0xc44b30,1).fillCircle(end.x,end.y,10);
  s.requestRender?.();
}
/** Walk to a real destination; directory entries beyond the eight map doors open their existing visit directly. */
export async function goTo(dest,env){
  dlg?.open&&dlg.close();
  if(dest.startsWith('utility:')){
    const item=townUtilityGroups(env.api.state,env.api.content,live(env)).flatMap(group=>group.items).find(item=>dest==='utility:'+(item.id||item.action));
    if(item){stopLine();await env.act(item.action,item.actionData);}
    return;
  }
  const real=world;
  if(!real?.stage){env.toast('Phố đang dựng, chờ một chút nhé.');return;}
  if(real.mode!=='town'){await env.act('isoTown');}
  const h=real.hotspots.find(x=>x.id===dest);
  if(!h&&dest.startsWith('resident:')){await visitResident(dest.slice(9),env);return;}
  if(!h){env.toast('Nơi này chưa có trên đảo.',true);return;}
  stopLine();goingTo=dest;
  let done=false;
  const arrived=()=>{done=true;stopLine();real.onInteract(dest);};
  real.go(dest,arrived);
  if(done)return;                       // already there: go() called back at once
  const mine=real.pending;
  if(!real.player.path.length){stopLine();return;}
  const label=h.label||dest;env.toast(`🧭 Đang tới ${label}`);
  const tick=()=>{
    if(real.pending!==mine||!real.player.path.length||real.mode!=='town'){if(!done)stopLine();return;}   // stopped: a tap, the joystick, a key
    if(real.shouldSleep?.()||real.paused||document.hidden||document.querySelector?.('dialog[open]:not(.drawer)'))return;
    drawRoute(real);
  };
  // Phaser already stops for covered/hidden/paused scenes and wakes on resume.
  // Update after its player step; a second RAF would keep redrawing a sleeping town.
  const events=real.stage.events;
  events.on('postupdate',tick);unwatch=()=>events.off('postupdate',tick);
  tick();
}

/** A brand-new player after the intro (v4/journey.js onIsoLand): on the island, with a pointer to the first job. */
export async function landNewPlayer(env){
  await helpers();
  env.closeSheet();
  const real=world;
  if(real?.stage){const first=real.hotspots.find(h=>h.id==='career:'+FIRST_JOB)||real.hotspots.find(h=>h.id.startsWith('career:'));if(first)real.stage.highlight(first.id);}
  env.toast('Chào mừng tới đảo! Tự đi tới tiệm có vòng sáng, hoặc bấm 🧭 Chỉ đường để nhân vật dẫn đường.');
}
