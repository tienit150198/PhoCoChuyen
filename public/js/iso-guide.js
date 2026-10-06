/** 🧭 Chỉ đường on the 2.5D island (2.5D only: iso-boot.js / isometric-shell.js).
 *
 * - Places that are sheets, not buildings (Nhà, Ngân hàng, Bảng xếp hạng, Hội chợ, Lịch cưới, Quầy…), get a signpost
 *   on a crossroads of the island: a hotspot like a workplace door (tap it, or walk up and press E).
 * - The 🧭 sheet lists every destination (places, Thư giãn, every workplace) with a search box. Picking one draws the
 *   route on the road and walks the avatar there; a tap on the ground, the joystick or a key stops it. On arrival the
 *   place opens (a workplace: you go in to work, as when you tap its door).
 * - The island remembers where you were on this device (localStorage mnl.isoSpot); back from work you stand at that
 *   workplace's door. Nothing here touches the save.
 */
import {escapeHTML as esc} from './icons.js';
// v4/journey.js (emojiOf) and v4/onboard.js (FIRST_JOB) are loaded on first use: they need a document.
let emojiOf=m=>m.emoji||'✨',FIRST_JOB='milk_tea';
const helpers=()=>Promise.all([import('./v4/journey.js'),import('./v4/onboard.js')]).then(([j,o])=>{emojiOf=j.emojiOf;FIRST_JOB=o.FIRST_JOB;}).catch(()=>{});

const SPOT_KEY='mnl.isoSpot';
/** Signposts on road crossings (x, y on the island grid; roads every 7 cells, see client/isometric/model.ts townRoads). */
export const PLACES=[
  {id:'house',icon:'🏠',label:'Nhà của bạn',action:'house',at:{x:2.8,y:6.25},on:e=>Boolean(e.api.state?.journey?.story)},
  {id:'bank',icon:'🏦',label:'Ngân hàng',action:'bank',at:{x:13.25,y:6.25},on:()=>true},
  {id:'rank',icon:'🏆',label:'Bảng xếp hạng',action:'rank',at:{x:20.25,y:6.25},on:()=>true},
  {id:'social',icon:'🛍️',label:'Phố nghề',hint:'Ghé tiệm người chơi khác',action:'social',at:{x:27.25,y:6.25},on:()=>true},
  {id:'fair',icon:'🏮',label:'Hội chợ',action:'fair',at:{x:6.25,y:13.25},on:e=>Boolean(e.api.state?.fair?.show)},
  {id:'wedding',icon:'💍',label:'Lịch cưới · Nhà cưới',action:'liveWed',at:{x:13.25,y:13.25},on:e=>Boolean(live(e)?.flags?.wedding&&live(e)?.welcomed)},
  {id:'quay',icon:'🏪',label:'Quầy của bạn',action:'quay',at:{x:20.25,y:13.25},on:e=>Boolean(e.api.state?.journey?.story&&e.api.content?.journey?.quay)},
  {id:'board',icon:'📌',label:'Nhóm phố',hint:'Bảng tin hàng xóm',action:'nhom',at:{x:6.25,y:20.25},on:()=>true},
  {id:'walk',icon:'🚶',label:'Phố đi dạo',hint:'Gặp người chơi khác',action:'liveWalk',at:{x:13.25,y:20.25},on:e=>Boolean(live(e)?.flags?.street&&live(e)?.welcomed)},
  {id:'date',icon:'💕',label:'Góc hẹn hò',action:'liveDate',at:{x:20.25,y:20.25},on:e=>Boolean(live(e)?.flags?.dating&&live(e)?.welcomed)},
  {id:'marriage',icon:'💒',label:'Hôn nhân & gia đình',action:'marriage',at:{x:27.25,y:13.25},on:()=>true},
];
const OUTINGS=[['fishing','🎣','Ao câu cá'],['boat','🚣','Bến thuyền'],['pool','🏊','Hồ bơi · thể thao']];
const live=e=>{try{return e.live?.()||null;}catch{return null;}};
const fold=s=>String(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/đ/g,'d').replace(/Đ/g,'D').toLowerCase();
const inside=(p,r,m=0)=>p.x>=r.x0-m&&p.x<=r.x1+m&&p.y>=r.y0-m&&p.y<=r.y1+m;
/** client/isometric/model.ts isWalkable, for points this module picks. */
function walkable(nav,p){return Boolean(nav)&&inside(p,nav.bounds)&&nav.roads.some(r=>inside(p,r))&&!nav.obstacles.some(r=>inside(p,r,nav.clearance||.14));}
function nearest(nav,p){
  if(walkable(nav,p))return p;
  for(let d=.25;d<=3;d+=.25)for(let a=0;a<16;a++){const q={x:p.x+Math.cos(a*Math.PI/8)*d,y:p.y+Math.sin(a*Math.PI/8)*d};if(walkable(nav,q))return q;}
  return null;
}

let world=null,envOf=null,line=null,watch=0,goingTo=null,shown=new Set();

/** The real PhaserWorld (app.js adopted it): signposts on each town rebuild, door spawn, the remembered spot. */
export function attachGuide(real,getEnv){
  world=real;envOf=getEnv;
  const stage=()=>real.stage;
  let lastMode=real.mode;
  const decorate=()=>{
    const s=stage();if(!s||real.mode!=='town')return;
    shown=new Set();const env=envOf();
    for(const p of PLACES){
      if(!p.on(env))continue;
      const at=nearest(s.navigation,p.at);if(!at)continue;
      shown.add(p.id);
      const id='place:'+p.id,h={id,label:p.label,x:at.x,y:at.y,approach:at,point:at,z:0,range:1.2};
      real.hotspots.push(h);
      const f=real.project(at.x,at.y,0),post=s.add.graphics();
      post.fillStyle(0x7a5a3f,1).fillRect(f.x-2,f.y-46,4,46).fillStyle(0x5f4330,.25).fillEllipse(f.x,f.y,22,8);post.setDepth(f.y+.2);
      const sign=s.add.text(f.x,f.y-44,`${p.icon} ${p.label}`,{fontFamily:'"Be Vietnam Pro","Segoe UI",sans-serif',fontSize:'15px',fontStyle:'600',color:'#5a3d2b',backgroundColor:'#fff3dae8',padding:{x:9,y:5}}).setOrigin(.5,1).setDepth(f.y+.3);
      s.staticObjects.push(post,sign);
      s.hits.push({hotspot:h,object:sign},{hotspot:h,footprint:{x0:at.x-.45,y0:at.y-.45,x1:at.x+.45,y1:at.y+.45}});
    }
    // Back from work: at that workplace's door, not in the middle of the island.
    if(lastMode==='work'){const door=real.hotspots.find(h=>h.id==='career:'+real.career);if(door){Object.assign(real.player,door.approach,{path:[],goal:null});real.recenter?.();}}
    s.requestRender?.();
  };
  const rebuild=stage().rebuild.bind(stage());
  // The first town with its buildings: back at the spot remembered on this device.
  let restored=false;const restore=()=>{if(!restored&&real.mode==='town'&&layoutKey(real)>0){restored=true;restoreSpot(real);}};
  stage().rebuild=(...a)=>{const r=rebuild(...a);restore();decorate();lastMode=real.mode;return r;};
  // A signpost tapped (or reached): open what it stands for.
  const interact=real.onInteract;
  real.onInteract=id=>{if(typeof id==='string'&&id.startsWith('place:')){arrive(id.slice(6));return;}interact(id);};
  restore();
  decorate();
  setInterval(()=>{if(restored)saveSpot(real);},2000);
  addEventListener('pagehide',()=>{if(restored)saveSpot(real);});
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
  const p=PLACES.find(x=>x.id===placeId),env=envOf?.();if(!p||!env)return;
  stopLine();
  await env.act(p.action);
}

/* ---- the 🧭 sheet ---- */
let dlg=null,query='';
function destinations(env){
  const out=[];
  for(const p of PLACES)if(shown.has(p.id)||(!world&&p.on(env)))out.push({dest:'place:'+p.id,icon:p.icon,label:p.label,hint:p.hint||'',group:'Trong phố'});
  for(const [k,icon,label] of OUTINGS)out.push({dest:'outing:'+k,icon,label,hint:'Thư giãn, miễn phí',group:'Thư giãn'});
  const J=env.api.state?.journey,open=new Set(J?.unlocked||[]),free=J&&J.story===false;
  const cur=env.api.state?.current;
  for(const m of (env.api.content?.catalogue||[]).filter(c=>c.playable!==false)){
    const locked=!free&&J?.story&&!open.has(m.id)&&!env.api.state?.careers?.[m.id]?.started;
    out.push({dest:'career:'+m.id,icon:emojiOf(m),label:m.place||m.name,hint:(m.id===cur?'Nơi bạn đang làm · ':'')+(locked?'🔒 chưa mở':(m.name||'')),group:'Nơi làm việc',first:m.id===FIRST_JOB&&!cur});
  }
  return out;
}
function listHTML(env){
  const q=fold(query.trim()),rows=destinations(env).filter(d=>!q||fold(d.label+' '+d.hint).includes(q));
  if(!rows.length)return `<p class="iso-guide-empty">Không thấy nơi nào tên “${esc(query)}”.</p>`;
  let html='',group='';
  for(const d of rows){
    if(d.group!==group){if(group)html+='</div>';group=d.group;html+=`<h3>${esc(group)}</h3><div class="iso-guide-list" role="list">`;}
    html+=`<button type="button" role="listitem" class="iso-guide-row${d.first?' is-first':''}" data-action="isoGo" data-dest="${esc(d.dest)}"><span class="iso-guide-ico" aria-hidden="true">${d.icon}</span><span class="iso-guide-copy"><b>${esc(d.label)}</b>${d.hint?`<small>${esc(d.hint)}</small>`:''}</span><span class="iso-guide-go" aria-hidden="true">Đi ›</span></button>`;
  }
  return html+'</div>';
}
function render(env){if(dlg)dlg.querySelector('.iso-guide-body').innerHTML=listHTML(env);}
export async function openGuide(env){
  await helpers();
  if(!dlg){
    dlg=document.createElement('dialog');dlg.className='sheet v4-sheet medium iso-guide-sheet';dlg.setAttribute('aria-label','Chỉ đường');
    dlg.innerHTML=`<header class="sheet-head"><div class="grow"><h2>🧭 Chỉ đường</h2><p>Chọn nơi muốn tới: nhân vật tự đi theo đường. Chạm đất hoặc di chuyển để dừng.</p></div><button type="button" class="icon-btn" data-guide-close aria-label="Đóng">✕</button></header>
      <div class="iso-guide-search"><input type="search" class="input" placeholder="Tìm nơi: ngân hàng, phở, hội chợ…" aria-label="Tìm nơi muốn tới" autocomplete="off" enterkeyhint="search"></div>
      <div class="sheet-body iso-guide-body"></div>`;
    document.body.append(dlg);
    const input=dlg.querySelector('input');
    input.addEventListener('input',()=>{query=input.value;render(envOf?.()||env);});
    input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();dlg.querySelector('.iso-guide-row')?.click();}});
    dlg.querySelector('[data-guide-close]').addEventListener('click',()=>dlg.close());
    dlg.addEventListener('click',e=>{if(e.target===dlg)dlg.close();});
  }
  query='';dlg.querySelector('input').value='';render(env);
  if(!dlg.open)dlg.showModal();
  if(matchMedia('(pointer: fine)').matches)dlg.querySelector('input').focus({preventScroll:true});
}

/* ---- walking there ---- */
function stopLine(){cancelAnimationFrame(watch);watch=0;line?.destroy();line=null;goingTo=null;world?.stage?.requestRender?.();}
function drawRoute(real){
  const s=real.stage;if(!s)return;
  if(!line){line=s.add.graphics();line.setDepth(-5000);}
  line.clear();const pts=[real.player,...real.player.path].map(p=>real.project(p.x,p.y,0));
  if(pts.length<2)return;
  const stroke=(width,colour,alpha)=>{line.lineStyle(width,colour,alpha);line.beginPath();line.moveTo(pts[0].x,pts[0].y);for(const p of pts.slice(1))line.lineTo(p.x,p.y);line.strokePath();};
  stroke(16,0x7a4b2e,.45);stroke(8,0xfff3da,1);   // a cream path with a brown edge: readable on grass and paving
  const end=pts[pts.length-1];line.fillStyle(0x7a4b2e,.5).fillCircle(end.x,end.y,15).fillStyle(0xc44b30,1).fillCircle(end.x,end.y,10);
  s.requestRender?.();
}
/** Walk to a destination of the 🧭 sheet: 'career:<id>', 'outing:<kind>' or 'place:<id>'. */
export async function goTo(dest,env){
  dlg?.open&&dlg.close();
  const real=world;
  if(!real?.stage){env.toast('Phố đang dựng, chờ một chút nhé.');return;}
  if(real.mode!=='town'){await env.act('isoTown');}
  const h=real.hotspots.find(x=>x.id===dest);
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
    drawRoute(real);watch=requestAnimationFrame(tick);
  };
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
