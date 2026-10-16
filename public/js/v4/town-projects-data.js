/** 🏗️ Công trình của phố: the page data (GET /api/town, game/town_projects.py view) shared by the panel
 * (v4/town-projects.js), the 2.5D island (iso-guide.js → PhaserWorld.setTownProjects) and the old town map
 * (scenes/town-place.js lots `lm:tp_<id>`, v4/town-walk.js). One request a minute at most, unless the panel asks;
 * no DOM here (tests/town-projects-client.mjs). */
export const TOWN_PROJECT_IDS=['cong_vien','rap_phim','thu_vien','san_van_dong','cau_ra_dao','benh_vien'];
const FRESH_MS=60_000;
const T={view:null,at:0,pending:null,listeners:new Set()};

/** Server time now, from the last page (its `now`) and the time since it came. */
export function serverNow(view=T.view,since=T.at,clock=Date.now()){
  return view&&Number.isFinite(view.now)?view.now+Math.max(0,clock-since)/1000:clock/1000;
}
/** Each lot's stage for the maps: soon (empty plot, "Sắp xây"), funding (raising money: pct), building (left: hours
 * to go), done. A build past its time shows as done before the server's lazy check writes it. */
export function stagesOf(view,t=serverNow(view)){
  const list=Array.isArray(view?.projects)?view.projects:[];
  return TOWN_PROJECT_IDS.map(id=>{
    const p=list.find(x=>x?.id===id);
    let stage=['soon','funding','building','done'].includes(p?.status)?p.status:'soon';
    if(stage==='building'&&Number(p.ready)>0&&Number(p.ready)<=t)stage='done';
    const goal=Math.max(1,Number(p?.goal)||1),pct=stage==='funding'?Math.max(0,Math.min(99,Math.floor((Number(p.raised)||0)*100/goal))):0;
    const left=stage==='building'?Math.max(1,Math.min(48,Math.ceil((Number(p.ready)-t)/3600))):0;
    return {id,stage,pct,left};
  });
}
export const peekTown=()=>T.view;
export function onTown(fn){T.listeners.add(fn);return ()=>T.listeners.delete(fn);}
/** A fresh page from the panel (after a contribution): every map follows. */
export function setTown(view){
  if(!view||!Array.isArray(view.projects))return;
  T.view=view;T.at=Date.now();
  for(const fn of [...T.listeners]){try{fn(view);}catch(e){console.warn('town projects:',e);}}
}
/** The page, cached a minute (`force`: now). Never throws: the last page, or null. */
export async function loadTown(api,{force=false}={}){
  if(!api?.json)return T.view;
  if(!force&&T.view&&Date.now()-T.at<FRESH_MS)return T.view;
  if(T.pending)return T.pending;
  T.pending=(async()=>{
    try{setTown(await api.json('/api/town'));}
    catch{/* the map keeps its last look; the panel says it could not load */}
    finally{T.pending=null;}
    return T.view;
  })();
  return T.pending;
}
/** The 2.5D island: paint each lot for its stage now, and load the page in the background when it is old. */
export function syncWorld(world,api){
  if(!world||typeof world.setTownProjects!=='function')return;
  if(T.view)world.setTownProjects(stagesOf(T.view));
  if(!T.view||Date.now()-T.at>=FRESH_MS)loadTown(api).then(v=>{if(v)world.setTownProjects(stagesOf(v));});
}
/** "2 ngày 3 giờ", "5 giờ 12 phút", "12 phút": what a countdown says. */
export function leftText(secs){
  const s=Math.max(0,Math.round(Number(secs)||0)),d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);
  if(d)return `${d} ngày ${h} giờ`;
  if(h)return `${h} giờ ${m} phút`;
  return m?`${m} phút`:'Sắp xong';
}
export function resetTownForTests(){T.view=null;T.at=0;T.pending=null;T.listeners.clear();}
