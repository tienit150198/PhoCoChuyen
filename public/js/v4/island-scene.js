/** 🏝️ Đảo riêng: being on the island (a trip of game/island_trips.py). One controller for both interfaces: the new
 * one draws with Phaser (client/isometric/private-island.ts, inside the isometric bundle), the old one with a 2D canvas
 * (v4/island-walk.js); this owns walking (tap, arrows / WASD, the spot buttons), the boat or plane arriving, the live
 * room (v4/island-live.js: others walking, waving, talking), names and bubbles over heads, the hour running out.
 * "← Về phố" just goes home: the trip goes on, the dialog (v4/island.js) brings the player back.
 * 🏗️ The island's buildings (trip.builds, game/island_build.py) stand on both maps (withBuilds): scaffolding until their
 * hour, then the building; a leisure building is a spot (walk up: its pose, and actions.use() for the small daily tinh
 * thần), a home's door opens its inside view; the owner's 🏗️ opens the build mode (actions.build). A trip has no time
 * limit since 19/10 (trip.unlimited). 🏝️ 24/10: the island at its size with its decorations (withDesign: the owner's
 * from the save, journey.isld, a visitor's from the trip's `design`), redrawn when the owner changes it. */
import {layout,arrival,step,walkable,nearestWalkable,spotNear,standAt,spotById,spotLine,EMOTES,withBuilds,withDesign,footpaths,workAt,findPath} from '../island-layout.js';
import {createIslandPresence,peerAt} from './island-live.js';
import {lookOf} from './look.js';
import {newInterface} from '../interface-mode.js';

const SPEED=.16,ARRIVE_MS=2600,SEND_MS=320;
const VEHICLE_ICON={solo:'🚤',boat:'🛥️',heli:'🚁',plane:'✈️'};

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ease=t=>1-Math.pow(1-Math.max(0,Math.min(1,t)),3);

/** Where the boat or plane comes from and where it stays: a boat moors beside the end of the pier, a helicopter comes
 * down onto its pad, a plane lands along the strip (or onto the pad of an island with no strip). */
export function vehicleRoute(L,kind,big=false){
  if(kind==='heli')return {kind,big,from:[L.pad.x,L.pad.y],at:[L.pad.x,L.pad.y],lift:260,dir:1};
  if(kind==='plane'){const at=L.pad.kind==='strip'?[L.pad.x+.12,L.pad.y]:[L.pad.x,L.pad.y];return {kind,big,from:[at[0]-.7,at[1]],at,lift:150,dir:1};}
  // Moored on the side of the pier where there is water (San Hô's pier turns east into the stilt houses).
  const d=L.dock,north=d.y<.5,end=d.y+(north?-d.h/2+.03:d.h/2-.03),east=[d.x+d.w/2+.045,end],at=walkable(L,...east)?[d.x-d.w/2-.045,end]:east;
  return {kind:kind==='solo'?'solo':'boat',big,from:[at[0]+(at[0]<d.x?-.06:.06),north?-.25:1.25],at,lift:0,dir:north?-1:1};
}
/** The vehicle `t` (0..1) into its arrival. */
export function vehicleAt(r,t){
  const k=ease(t),[x,y]=k>=1?r.at:[r.from[0]+(r.at[0]-r.from[0])*k,r.from[1]+(r.at[1]-r.from[1])*k];
  return {kind:r.kind,big:r.big,x,y,lift:r.lift*(1-k),dir:r.dir};
}
/** Where I step off: the end of the pier, or beside the pad. */
export const landing=(L,kind)=>arrival(L,kind==='heli'||kind==='plane'?kind:'boat');
/** Facing for the illustrated figures: east is south-east on the isometric screen, south is south-west. */
export function facing(dx,dy,prev='se'){
  if(Math.abs(dx)+Math.abs(dy)<1e-6)return prev;
  return Math.abs(dx)>=Math.abs(dy)?(dx>=0?'se':'nw'):(dy>=0?'sw':'ne');
}
const minutesLeft=(ends,now)=>Math.max(0,Math.ceil((ends-now)/60));
/** "5g 12p" / "40p": a construction's time left. */
export const hoursLeft=s=>{const m=Math.max(1,Math.ceil(s/60)),h=Math.floor(m/60);return h?`${h}g${m%60?` ${m%60}p`:''}`:`${m}p`;};

/** The session without the DOM: tests drive it with a fake view, renderer, live socket and clock. */
export function createIslandSession(env,{trip,view,loadRenderer,loadLive=async()=>null,actions={},clock=()=>performance.now(),wall=()=>Date.now()/1000,
  raf=fn=>requestAnimationFrame(fn),caf=id=>cancelAnimationFrame(id),reduced=false,onClose=()=>{},skew=0}){
  /** 🏝️ The island's design: the owner's own save (fresh after every change in the build mode), else the trip's. */
  const iid=trip.island?.id;
  const designOf=()=>(trip.mine&&iid&&env.api.state?.journey?.isld?.i?.[iid])||trip.design||null;
  let design=designOf(),base=withDesign(layout(trip.island?.look),design),paths=footpaths(base),pathKey=JSON.stringify(paths);
  const kind=trip.visit?'solo':trip.kind||'solo',route=vehicleRoute(base,kind,!trip.visit&&(trip.seats||0)>=12),[sx,sy]=landing(base,kind);
  /** The server's unix time (the buildings' hours are the server's). */
  const serverNow=()=>wall()+skew;
  let builds=Array.isArray(trip.builds)?trip.builds:[],L=withBuilds(base,builds,serverNow()),buildKey='';
  const me={x:sx,y:sy,target:null,dir:'se',left:false,walking:false,spot:null,pose:null,sent:[sx,sy],sendAt:0};
  const keys=new Set(),arriveMs=reduced?0:ARRIVE_MS;
  let renderer=null,presence=null,frameId=0,closed=false,started=false,t0=0,last=0,previousPause=false,arrived=false,statusAt=-1e9,why=null,signsAt=-1e9,pingOff=null;
  const look=lookOf(env.api.state),gender=env.api.state?.journey?.gender==='male'||env.api.state?.journey?.gender==='female'?env.api.state.journey.gender:null;

  function close(reason=null){
    if(closed)return;closed=true;why=reason;caf(frameId);
    presence?.stop();pingOff?.();renderer?.destroy();renderer=null;env.api.removeEventListener?.('state',onState);view.destroy();
    if(started&&env.world){env.world.paused=previousPause;env.world.wake?.();}
    const said={ended:'Chủ đảo đã kết thúc chuyến chơi. Mọi người về phố nhé.',time:'Hết giờ chơi trên đảo, thuyền đưa mọi người về phố.',
      changed:'Bạn đã rời chuyến ra đảo này.',other:'Bạn đang ở trên đảo ở một cửa sổ khác.',gone:'Chuyến ra đảo đã kết thúc.'}[reason];
    if(said)env.toast?.(said);
    onClose(reason);
  }
  function onState(){if(env.api.state?.jail){close();return;}if(trip.mine)redesign(designOf());view.fun?.(funList());}
  /** 🏖️ Chơi trên đảo (game/island_fun.py): the beach activities and the daily chest, done ones marked. */
  function funList(){
    const B=env.api.content?.journey?.homelife?.beach,done=env.api.state?.journey?.homelife?.beach||{};
    if(!B||!actions.fun)return [];
    return [...(actions.chest?[{id:'chest',emoji:'🎁',name:'Rương báu',done:Boolean(done.chest),chest:true}]:[]),
      ...(B.acts||[]).map(a=>({...a,done:(done.did||[]).includes(a.id)}))];
  }
  let funBusy=false;
  async function fun(id,quiet=false){
    if(funBusy||closed)return '';funBusy=true;
    try{const line=await (id==='chest'?actions.chest?.():actions.fun?.(id));if(line&&!quiet&&!closed)view.notice(line);return line||'';}
    finally{funBusy=false;}
  }
  const go=(x,y,spot=null)=>{
    if(!arrived)return;
    const [tx,ty]=nearestWalkable(L,x,y),path=findPath(L,[me.x,me.y],[tx,ty]);   // around the houses and the sites
    me.path=path.length?path:[[tx,ty]];me.target=me.path.shift();me.spot=spot;me.pose=null;
    const d=Math.hypot(me.target[0]-me.x,me.target[1]-me.y);send(me.target,d/SPEED*1000);
  };
  function send(to,ms){if(!presence)return;presence.move([me.x,me.y],to,Math.min(6000,ms));me.sent=to;me.sendAt=clock();}
  function tap(clientX,clientY){
    const p=renderer?.toMap(clientX,clientY);if(!p)return;
    const half=.036,here=L.built.find(b=>Math.abs(b.x-p[0])<=half&&Math.abs(b.y-p[1])<=half)||null;   // a building under the finger
    if(here&&here.work&&trip.mine&&actions.build){actions.build(here.plot);return;}   // the owner: a site, its sheet
    if(here&&!here.work&&here.level>=1){const sp=L.spots.find(x=>x.build?.plot===here.plot);if(sp){const [x,y]=standAt(L,sp);go(x,y,sp);return;}}
    const s=spotNear(L,p[0],p[1],.06);
    if(s){const [x,y]=standAt(L,s);go(x,y,s);}else go(p[0],p[1]);
  }
  function useSpot(id){const s=spotById(L,id);if(s){const [x,y]=standAt(L,s);go(x,y,s);}}
  function reachSpot(s){
    me.spot=null;
    if(s.home){me.pose=null;view.inside?.({kind:s.build.kind,tier:s.build.art.tier||0,level:s.build.level,name:s.build.art.name,emoji:s.build.art.emoji,owner:trip.owner?.name||'',mine:Boolean(trip.mine)});return;}
    me.pose=s.pose;
    view.notice(`${s.emoji} ${spotLine(s,Math.floor(clock()/1000))}`);presence?.act(s.id);
    const act=!s.build&&env.api.content?.journey?.homelife?.beach?.spots?.[s.id];   // 🏖️ the campfire, the reef…: its activity, once a day
    if(act&&!(env.api.state?.journey?.homelife?.beach?.did||[]).includes(act))fun(act,true).then(line=>{if(line&&!closed)view.notice(line);}).catch(()=>{});
    if(s.build)Promise.resolve(actions.use?.(s.build.plot)).then(line=>{if(line&&!closed)view.notice(`${s.emoji} ${spotLine(s,Math.floor(clock()/1000))} ${line}`);}).catch(()=>{});
  }
  /** 🏗️ The buildings changed (a new list from the server, or a construction's hour is over): the map, the spots. */
  function rebuild(list=builds){
    builds=Array.isArray(list)?list:[];
    const now=serverNow(),key=JSON.stringify(builds.map(b=>[b.p,b.k,b.l,b.b,workAt(b,now)]));
    if(key===buildKey)return;buildKey=key;
    L=withBuilds(base,builds,now);renderer?.setBuilds?.(L.built);view.spots?.(chips(L.spots));
    const next=footpaths(L),pk=JSON.stringify(next);if(pk!==pathKey){pathKey=pk;paths=next;renderer?.setLayout?.(base,paths);}   // 🛤️ to the homes' doors too
    if(!walkable(L,me.x,me.y)){const [x,y]=nearestWalkable(L,me.x,me.y);me.x=x;me.y=y;}
  }
  /** 🏝️ The island's design changed (the owner built, moved, lấn biển): the map, the spots, the footpaths. */
  let designKey=JSON.stringify(design);
  function redesign(next){
    const key=JSON.stringify(next||null);if(key===designKey||closed)return;designKey=key;design=next;
    base=withDesign(layout(trip.island?.look),design);paths=footpaths(base);buildKey='';rebuild(builds);
    renderer?.setLayout?.(base,paths);
  }
  let reloading=0;
  async function reload(){
    if(!actions.reload||closed||Date.now()-reloading<1500)return;reloading=Date.now();
    try{const t=await actions.reload();if(t&&!closed){if(!trip.mine&&t.design)redesign(t.design);rebuild(t.builds);}}catch{/* the map keeps what it had */}
  }
  function key(code,down){
    const map={ArrowUp:'u',KeyW:'u',ArrowDown:'d',KeyS:'d',ArrowLeft:'l',KeyA:'l',ArrowRight:'r',KeyD:'r'};
    const k=map[code];if(!k)return false;if(down)keys.add(k);else keys.delete(k);return true;
  }
  function walk(dt,t){
    let vx=(keys.has('r')?1:0)-(keys.has('l')?1:0),vy=(keys.has('d')?1:0)-(keys.has('u')?1:0);
    const was=[me.x,me.y];
    if(vx||vy){
      me.target=null;me.path=null;me.spot=null;me.pose=null;const n=Math.hypot(vx,vy);vx/=n;vy/=n;
      const [nx,ny]=step(L,me.x,me.y,me.x+vx,me.y+vy,SPEED*dt);me.x=nx;me.y=ny;
      if(t-me.sendAt>=SEND_MS){const ahead=step(L,me.x,me.y,me.x+vx,me.y+vy,SPEED*SEND_MS/1000);send([ahead[0],ahead[1]],SEND_MS);}
    }else if(me.target){
      const [nx,ny,done]=step(L,me.x,me.y,me.target[0],me.target[1],SPEED*dt);me.x=nx;me.y=ny;
      const stuck=Math.hypot(nx-was[0],ny-was[1])<1e-7;
      if(done&&me.path?.length){me.target=me.path.shift();send(me.target,Math.hypot(me.target[0]-me.x,me.target[1]-me.y)/SPEED*1000);}   // the next bend
      else if(done||stuck){const s=me.spot;me.target=null;me.path=null;if(s&&Math.hypot(me.x-standAt(L,s)[0],me.y-standAt(L,s)[1])<.03)reachSpot(s);else me.spot=null;}
    }
    const dx=me.x-was[0],dy=me.y-was[1];me.walking=Math.hypot(dx,dy)>1e-6;
    if(me.walking){me.dir=facing(dx,dy,me.dir);if(Math.abs(dx)>1e-6)me.left=dx<0;}
    // Stopped short of where the others think I am (a wall, a key let go): tell them where I stand.
    if(!me.walking&&!me.target&&presence&&Math.hypot(me.sent[0]-me.x,me.sent[1]-me.y)>.004)send([me.x,me.y],0);
  }
  function people(t){
    const out=[],now=clock();
    out.push({id:'me',me:true,name:'Bạn',x:me.x,y:me.y,look,gender:gender||'none',dir:me.dir,left:me.left,walking:me.walking,pose:me.pose,hidden:!arrived,
      bubble:presence?.self.bubble&&presence.self.bubble.until>now?presence.self.bubble.text:null,emote:presence?.self.emote&&presence.self.emote.until>now?presence.self.emote.e:null});
    for(const p of presence?.peers.values()||[]){
      const [x,y]=peerAt(p,now),moving=p.ms>0&&now<p.t0+p.ms,dx=p.to[0]-p.from[0],dy=p.to[1]-p.from[1];
      if(moving){p.dir=facing(dx,dy,p.dir||'se');if(Math.abs(dx)>1e-6)p.left=dx<0;}
      const act=p.act&&p.act.until>now?spotById(L,p.act.s):null;
      out.push({id:p.pid,name:p.name,owner:p.o,x,y,look:p.lk,gender:p.g||'none',dir:p.dir||'se',left:!!p.left,walking:moving,pose:moving?null:act?.pose||null,
        bubble:p.bubble&&p.bubble.until>now?p.bubble.text:null,emote:p.emote&&p.emote.until>now?p.emote.e:null,act:act?act.emoji:null});
    }
    void t;return out;
  }
  function status(){
    const left=minutesLeft(trip.ends,wall()),n=1+(presence?.peers.size||0);
    if(left<=0){close('time');return;}
    rebuild();   // a construction whose hour is over stands now
    const ve=trip.vehicle?.emoji||VEHICLE_ICON[kind],vn=String(trip.vehicle?.name||'');   // the island's own boat is named '🚤 Xuồng của đảo': its icon once
    const veh=trip.visit?'🌍 Khách ghé đảo':trip.vehicle?(vn.startsWith(ve)?vn:`${ve} ${vn}`):`${VEHICLE_ICON.solo} Xuồng của đảo`;
    const time=trip.unlimited||left>60*24*365?'':` · còn ${left} phút`;
    view.status(`${veh} · ${n} người trên đảo${time}`+(presence&&!presence.online?' · đang kết nối lại…':''));
  }
  function tick(t){
    if(closed||!renderer)return;
    const dt=Math.min(.05,Math.max(0,(t-last)/1000));last=t;
    const a=arriveMs?Math.min(1,(t-t0)/arriveMs):1;
    if(a>=1&&!arrived){arrived=true;view.arrived?.();}
    if(arrived)walk(dt,t);
    const list=people(t);
    if(trip.mine&&globalThis.document?.querySelector?.('dialog.isl-ed[open]'))return;   // 🛠️ the build mode covers the island: draw nothing under it
    renderer.frame({people:list,vehicle:vehicleAt(route,a),focus:[me.x,me.y]},t);
    const head=renderer.personHeight||90;
    view.tags(list.filter(p=>!p.hidden).map(p=>{const s=renderer.toScreen(p.x,p.y);return s&&{...p,sx:s[0],sy:s[1]-head-(p.pose==='swim'?-head*.35:0)};}).filter(Boolean));
    if(view.signs&&t-signsAt>500){signsAt=t;const now=serverNow();   // ⏳ how long the crews still work
      view.signs(L.built.filter(b=>b.work).map(b=>{const s=renderer.toScreen(b.x,b.y,0);return s&&{id:'b'+b.plot,sx:s[0],sy:s[1]+6,text:`⏳ ${hoursLeft(b.until-now)}`};}).filter(Boolean));}
    if(t-statusAt>1000){statusAt=t;status();}
    if(!closed)frameId=raf(tick);
  }
  view.onClose(()=>close());
  view.onTap(tap);view.onKey(key);view.onSpot(useSpot);
  view.onEmote(e=>{if(presence)presence.emote(e);});
  view.onSay(text=>{const ok=presence?.say(text);if(!ok)view.notice('Chưa nói được: đang mất kết nối, thử lại sau nhé.');return ok;});
  view.onEnd?.(async()=>{try{if(await actions.end?.()===false)return;close('ended');}catch(e){view.notice(e.message||'Chưa kết thúc được chuyến này.');}});
  view.onBuild?.(()=>actions.build?.(-1));
  view.onFun?.(id=>{fun(id).catch(()=>{});});

  async function start(){
    if(started||closed)return;
    if(env.api.state?.jail){close();return;}
    started=true;
    if(env.world){previousPause=env.world.paused;env.world.paused=true;}
    env.closeSheet?.();env.api.addEventListener?.('state',onState);view.open(L,trip);
    try{
      renderer=await loadRenderer(view,base);if(closed){renderer?.destroy();renderer=null;return;}
      renderer.setLayout?.(base,paths);renderer.setBuilds?.(L.built);view.spots?.(chips(L.spots));view.fun?.(funList());buildKey='';rebuild();
      if(!trip.mine&&!trip.design)reload();   // 🏝️ opened from a list without its design: read the trip once
      view.ready();
      const live=await loadLive().catch(()=>null);if(closed)return;
      if(live?.on)pingOff=live.on('island_ping',f=>{if(f.trip===trip.id&&f.why==='seat')reload();});   // 🏗️ the owner built or razed something
      if(live)presence=createIslandPresence({live,trip:trip.id,look,gender,at:()=>[me.x,me.y],clock,
        onChange:()=>{},onLeft:w=>close(w),onError:(msg,code)=>{if(code==='no_island')close('gone');else view.notice(msg);}}).start();
      t0=last=clock();frameId=raf(tick);
    }catch(error){if(!closed){env.toast?.(error?.message||'Chưa mở được đảo. Thử lại nhé.',true);close();}}
  }
  return {start,close,tick,tap,useSpot,key,rebuild,reload,redesign,
    get me(){return me;},get arrived(){return arrived;},get why(){return why;},get presence(){return presence;},get closed(){return closed;},get layout(){return L;}};
}

/** The spot buttons: every place once, a decoration's kind once (twenty sun loungers are one button). */
function chips(list){const seen=new Set();return list.filter(s=>{if(!s.decor)return true;const k=s.decor.kind;if(seen.has(k))return false;seen.add(k);return true;});}
const spotChips=list=>list.map(s=>`<button type="button" class="isl-chip${s.build?' isl-chip-b':''}" data-spot="${esc(s.id)}">${esc(s.emoji)} ${esc(s.name)}</button>`).join('');
/** 🏠 What a home holds at each level: [emoji, left %, bottom %, size px] on the floor, the wall's and the floor's colours. */
const ROOMS={
  nha_san:{wall:'#e8c98f',floor:'#b5844f',items:[['🛏️',18,8,46],['🪔',70,40,30],['🏺',82,10,34]],more:[['🪑',48,6,34],['🪴',6,34,34]],most:[['🎣',62,48,30],['🧺',36,26,30]]},
  biet_thu:{wall:'#f4efe6',floor:'#d9c7a8',items:[['🛋️',20,8,52],['📺',62,44,36],['🪴',86,10,40]],more:[['🛏️',56,6,48],['🖼️',30,62,32]],most:[['🛁',78,26,40],['🎹',6,20,40]]},
  lau_dai:{wall:'#cfc6b8',floor:'#8f8476',items:[['🪑',30,8,44],['🕯️',12,44,30],['🛡️',72,58,34]],more:[['🎹',58,6,50],['🖼️',36,62,34]],most:[['🏆',86,30,34],['📚',4,10,44],['💎',48,40,26]]},
  // 🏡 the house styles (public/js/house-art.js): a few of their own, the rest by tier (TIER_ROOMS)
  nha_tranh:{wall:'#d9b98a',floor:'#9c7a52',items:[['🛏️',18,8,44],['🍚',70,40,30],['🏺',84,10,34]],more:[['🪑',48,6,34],['🐓',8,30,30]],most:[['🧺',62,48,30],['🌾',36,26,30]]},
  nha_cay:{wall:'#c99a62',floor:'#8a6236',items:[['🛏️',20,8,44],['🔭',72,42,32],['🪴',86,10,34]],more:[['📚',48,6,36],['🧸',8,30,30]],most:[['🪁',60,50,30],['✨',34,30,26]]},
  hai_dang:{wall:'#eef1f4',floor:'#7d8a96',items:[['🛏️',20,8,44],['🧭',70,42,32],['⚓',84,10,34]],more:[['🗺️',46,60,34],['🪑',8,8,34]],most:[['🔭',60,30,34],['📻',34,44,28]]},
  nha_nhat:{wall:'#efe6d2',floor:'#c9b98a',items:[['🍵',20,8,40],['🏮',72,44,32],['🎎',84,10,34]],more:[['🪷',46,6,34],['🖼️',30,62,32]],most:[['🎋',62,30,34],['🪭',8,40,30]]},
  hanok:{wall:'#efe3cb',floor:'#a8855a',items:[['🍵',20,8,40],['🏺',74,10,38],['🪭',70,48,28]],more:[['🛏️',46,6,46],['🖼️',30,62,32]],most:[['🪷',86,30,32],['🥢',8,40,28]]},
  hoang_cung:{wall:'#b8433a',floor:'#7a3a26',items:[['🪑',30,8,46],['🏮',12,48,32],['🐉',74,58,36]],more:[['🎋',58,6,46],['🖼️',36,62,34]],most:[['🏆',86,30,34],['🪭',4,12,40],['💎',48,40,26]]},
};
const TIER_ROOMS={1:ROOMS.nha_san,2:{wall:'#f2dfb4',floor:'#a77a4d',items:[['🛏️',18,8,46],['🏮',70,44,30],['🪴',84,10,36]],more:[['🪑',48,6,34],['🖼️',30,62,32]],most:[['🎐',60,50,30],['🧺',6,30,30]]},3:ROOMS.biet_thu,4:ROOMS.lau_dai};
function roomHtml(info){
  const r=ROOMS[info.kind]||TIER_ROOMS[info.tier]||ROOMS.nha_san,lv=Math.max(1,Math.min(3,Number(info.level)||1));
  const items=[...r.items,...(lv>1?r.more:[]),...(lv>2?r.most:[])];
  return `<div class="isl-room" style="--wall:${r.wall};--floor:${r.floor}"><div class="isl-room-wall"><span class="isl-room-window" aria-hidden="true"></span>${lv>2?'<span class="isl-room-lamp" aria-hidden="true">💡</span>':''}</div><div class="isl-room-floor"></div>
    ${items.map(([e,x,y,size])=>`<span class="isl-room-item" style="left:${x}%;bottom:${y}%;font-size:${size}px" aria-hidden="true">${e}</span>`).join('')}</div>
    <div class="isl-inside-bar"><p><b>${esc(info.emoji)} ${esc(info.name)}</b> · ${'⭐'.repeat(lv)}${info.mine?'':` · ${esc(info.owner)}`}</p><button type="button" class="btn primary" data-out>Ra ngoài</button></div>`;
}

/** The fullscreen dialog: the stage, names and bubbles, the spots, emotes and the chat line. */
export function createView(){
  const previous=document.activeElement,dialog=document.createElement('dialog');
  dialog.className='isl-scene';dialog.setAttribute('data-island-scene','');dialog.setAttribute('aria-labelledby','islSceneTitle');
  const listeners=[],on=(t,n,fn,o)=>{t.addEventListener(n,fn,o);listeners.push(()=>t.removeEventListener(n,fn,o));};
  const cb={close:()=>{},tap:()=>{},key:()=>false,spot:()=>{},emote:()=>{},say:()=>true,end:null,build:null,fun:()=>{}};
  let tagCache=new Map(),signCache=new Map(),noticeTimer=0;
  const release=()=>{for(const c of ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','KeyW','KeyA','KeyS','KeyD'])cb.key(c,false);};
  function bind(canvas){
    let down=null;
    on(canvas,'pointerdown',e=>{down=[e.clientX,e.clientY];});
    on(canvas,'pointerup',e=>{if(down&&Math.hypot(e.clientX-down[0],e.clientY-down[1])<14)cb.tap(e.clientX,e.clientY);down=null;});
    on(canvas,'keydown',e=>{if(cb.key(e.code,true))e.preventDefault();});
    on(canvas,'keyup',e=>{if(cb.key(e.code,false))e.preventDefault();});
    on(canvas,'blur',release);
  }
  const view={
    canvas:null,dialog,
    onClose:fn=>{cb.close=fn;},onTap:fn=>{cb.tap=fn;},onKey:fn=>{cb.key=fn;},onSpot:fn=>{cb.spot=fn;},onEmote:fn=>{cb.emote=fn;},onSay:fn=>{cb.say=fn;},onEnd:fn=>{cb.end=fn;},onBuild:fn=>{cb.build=fn;},onFun:fn=>{cb.fun=fn;},
    open(L,trip){
      const owner=trip.mine;
      dialog.innerHTML=`<div class="isl-layout">
        <header class="isl-top"><div class="isl-title"><h2 id="islSceneTitle">${esc(trip.island?.emoji||'🏝️')} ${esc(trip.island?.name||L.name)}</h2><p data-status role="status">Đang ra đảo…</p></div>
          <div class="isl-top-actions">${owner?'<button type="button" class="btn ghost isl-build-btn" data-build aria-label="Xây trên đảo" title="Xây trên đảo">🏗️</button><button type="button" class="btn ghost" data-end aria-label="Kết thúc chuyến chơi">Kết thúc</button>':''}<button type="button" class="btn" data-close>← Về phố</button></div></header>
        <div class="isl-stage"><canvas tabindex="0" aria-label="${esc(L.name)}: chạm để đi, chạm vào một chỗ chơi để tới đó; dùng mũi tên hoặc W A S D để di chuyển."></canvas>
          <div class="isl-tags" aria-hidden="true"></div><p class="isl-loading" role="status">${esc(trip.kind==='heli'?'🚁 Trực thăng đang hạ cánh…':trip.kind==='plane'?'✈️ Máy bay đang hạ cánh…':'🛥️ Thuyền đang cập bến…')}</p>
          <p class="isl-notice" role="status" aria-live="polite" hidden></p></div>
        <footer class="isl-bar">
          <div class="isl-row isl-fun" role="group" aria-label="Chơi trên đảo" hidden></div>
          <div class="isl-row isl-spots" role="group" aria-label="Chỗ chơi trên đảo">${spotChips(chips(L.spots))}</div>
          <div class="isl-row isl-emotes" role="group" aria-label="Biểu cảm">${EMOTES.map(([id,e,name])=>`<button type="button" class="isl-emo" data-emote="${id}" aria-label="${esc(name)}" title="${esc(name)}">${e}</button>`).join('')}</div>
          <form class="isl-say"><input type="text" maxlength="120" autocomplete="off" enterkeyhint="send" placeholder="Nói gì đó với mọi người…" aria-label="Nói với mọi người trên đảo"><button type="submit" class="btn primary">Gửi</button></form>
        </footer></div>`;
      view.canvas=dialog.querySelector('canvas');
      const canvas=view.canvas,input=dialog.querySelector('.isl-say input');
      on(dialog,'cancel',e=>{e.preventDefault();if(dialog.querySelector('.isl-inside')){view.inside(null);return;}cb.close();});
      on(dialog,'click',e=>{const b=e.target.closest('button');if(!b)return;
        if(b.hasAttribute('data-out')){view.inside(null);return;}
        if(b.hasAttribute('data-close'))cb.close();else if(b.hasAttribute('data-end'))cb.end?.();else if(b.hasAttribute('data-build'))cb.build?.();
        else if(b.dataset.spot)cb.spot(b.dataset.spot);else if(b.dataset.emote)cb.emote(b.dataset.emote);else if(b.dataset.fun)cb.fun(b.dataset.fun);});
      on(dialog,'submit',e=>{e.preventDefault();const text=input.value.trim();if(text&&cb.say(text)!==false)input.value='';});
      bind(canvas);
      on(window,'pagehide',()=>cb.close());
      document.body.append(dialog);dialog.showModal();
    },
    /** 🏖️ The beach activities and the chest (game/island_fun.py), done ones faded. */
    fun(list){const row=dialog.querySelector('.isl-fun');if(!row)return;
      const html=list.map(a=>`<button type="button" class="isl-chip${a.chest?' chest':''}${a.done?' done':''}" data-fun="${esc(a.id)}"${a.done?' aria-pressed="true"':''}>${esc(a.emoji)} ${esc(a.name)}${a.done?' ✓':''}</button>`).join('');
      if(row._html!==html){row.innerHTML=html;row._html=html;}row.hidden=!list.length;},
    /** 🏗️ The spot buttons again (a building finished, was built or razed). */
    spots(list){const row=dialog.querySelector('.isl-spots');const html=spotChips(list);if(row&&row._html!==html){row.innerHTML=html;row._html=html;}},
    /** ⏳ The construction sites' time left, under each one. */
    signs(list){
      const box=dialog.querySelector('.isl-tags');if(!box)return;const seen=new Set();
      for(const x of list){seen.add(x.id);let el=signCache.get(x.id);if(!el){el=document.createElement('span');el.className='isl-sign';box.append(el);signCache.set(x.id,el);}
        if(el.textContent!==x.text)el.textContent=x.text;el.style.transform=`translate(${Math.round(x.sx)}px,${Math.round(x.sy)}px) translate(-50%,0)`;}
      for(const [id,el] of signCache)if(!seen.has(id)){el.remove();signCache.delete(id);}
    },
    /** 🏠 Inside a home (null: back outside): a room that fills up with its level. */
    inside(info){
      const stage=dialog.querySelector('.isl-layout');if(!stage)return;stage.querySelector('.isl-inside')?.remove();
      if(!info)return;
      const el=document.createElement('div');el.className='isl-inside';el.setAttribute('role','group');el.setAttribute('aria-label',`Bên trong ${info.name}`);
      el.innerHTML=roomHtml(info);stage.append(el);el.querySelector('[data-out]')?.focus({preventScroll:true});
    },
    /** A fresh canvas for the 2D fallback when the new interface's renderer could not start on the first one. */
    swapCanvas(){const fresh=view.canvas.cloneNode(false);view.canvas.replaceWith(fresh);view.canvas=fresh;bind(fresh);return fresh;},
    ready(){dialog.querySelector('.isl-loading')?.remove();view.canvas?.focus({preventScroll:true});},
    arrived(){},
    status(text){const p=dialog.querySelector('[data-status]');if(p&&p.textContent!==text)p.textContent=text;},
    notice(text){const p=dialog.querySelector('.isl-notice');if(!p)return;p.textContent=text;p.hidden=false;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>{p.hidden=true;},5000);},
    tags(list){
      const box=dialog.querySelector('.isl-tags');if(!box)return;const seen=new Set();
      for(const p of list){
        seen.add(p.id);let el=tagCache.get(p.id);
        if(!el){el=document.createElement('div');el.className='isl-tag'+(p.me?' me':'');box.append(el);tagCache.set(p.id,el);el._html='';}
        const html=`${p.bubble?`<span class="isl-bubble">${esc(p.bubble)}</span>`:''}${p.emote?`<span class="isl-emote">${esc((EMOTES.find(x=>x[0]===p.emote)||[])[1]||'')}</span>`:''}<b>${p.owner?'👑 ':''}${esc(p.name)}${p.act?` ${esc(p.act)}`:''}</b>`;
        if(el._html!==html){el.innerHTML=html;el._html=html;}
        el.style.transform=`translate(${Math.round(p.sx)}px,${Math.round(p.sy)}px) translate(-50%,-100%)`;
      }
      for(const [id,el] of tagCache)if(!seen.has(id)){el.remove();tagCache.delete(id);}
    },
    destroy(){clearTimeout(noticeTimer);listeners.splice(0).forEach(off=>off());if(dialog.open)dialog.close();dialog.remove();tagCache.clear();signCache.clear();if(previous?.isConnected)previous.focus?.({preventScroll:true});},
  };
  return view;
}

/** The renderer for this player's interface: Phaser on the new one (the 2D walk if it cannot start), the 2D walk on the old one. */
export async function loadRendererFor(env,view,L){
  if(newInterface(env.api.state)){
    try{
      const m=await import('../isometric/phaser-world.js');
      if(typeof m.PrivateIslandRenderer==='function'){
        const r=new m.PrivateIslandRenderer(view.canvas,L);let timer;   // 🏝️ the session sends the designed island (setLayout) once it runs
        const ok=await Promise.race([r.ready.then(()=>true),new Promise(res=>{timer=setTimeout(()=>res(false),15000);})]).finally(()=>clearTimeout(timer));
        if(ok)return r;r.destroy();
      }
    }catch(e){console.warn('island:',e);}
    view.swapCanvas();
  }
  const {createWalkRenderer}=await import('./island-walk.js');
  return createWalkRenderer(view.canvas,L);
}

let active=null;
/** Open the island of `trip` (a trip view from GET /api/island). `actions.end` ends it (the owner's button); 🏗️
 * `actions.build(plot)` opens the build sheet, `actions.use(plot)` a leisure building's tinh thần, `actions.reload()`
 * the trip again (its buildings); `skew`: the server's clock minus this device's (seconds). */
export function openIslandScene(env,trip,{actions={},onClose=()=>{},skew=0}={}){
  if(active)return active;
  if(env.api.state?.jail)return env.act?.('jail');
  active=(async()=>{
    try{
      const {stylesheet}=await import('../lazy.js');await stylesheet('/css/island.css');
      const L=layout(trip.island?.look);
      const reduced=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches||false;
      const session=createIslandSession(env,{trip,view:createView(),actions,reduced,skew,
        loadRenderer:(view,designed)=>loadRendererFor(env,view,designed||L),
        loadLive:async()=>{const network=await import('./live.js');env.bootLive?.(network);return network.live;},
        onClose:why=>{active=null;onClose(why);}});
      await session.start();return session;
    }catch(e){active=null;env.toast?.(e?.message||'Chưa mở được đảo. Thử lại nhé.',true);}
  })();
  return active;
}
