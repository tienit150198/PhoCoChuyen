/** Real shared-map presence over the existing authenticated /live socket.
 * Phaser owns drawing and feet coordinates; game tasks/saves never enter this transport.
 * All careers use iso-town-v1. A room holds at most 30 real players and updates at 4/s.
 * 🚗 `r` (live/town.py): the vehicle ridden (world.getRide, isometric/vehicle-art.js), sent on joining and when it changes.
 * 🐾 `pt` (owner 19/10 "đi đâu cũng cho dẫn theo"): the pet walking beside you (journey.pets.ref, game/pets.py walk_ref:
 * {b, c, n, a, r, x}), the same way; the scene draws everyone's (isometric/phaser-world.ts).
 * ⚔️ `bg` (live/bangs.py): another walker's bang tag, drawn as a second line of their name tag in the bang's ink
 * (v4/bang-tag.js tagLine); a 🎖️ badge goes before the name. My own look carries the bang uniform while I wear it
 * (bang-tag.js withBang), so everyone sees it.
 * 🤝 `pr` (live/charms.py): the friendship pairs a walker wears, {kind: count}, read by the service from the game's table and
 * kept beside the look (`look.pr`, v4/look.js withPairs) so the scene draws them; never sent by this client.
 */
import {live} from './v4/live.js';
import {sitePresence} from './v4/site-presence.js';
import {createTownSocial} from './isometric-social.js';
import {lookOf,withPairs,cleanPairs} from './v4/look.js';
import {leisurePresence,publicActivity} from './isometric/leisure-presence.js';
import {withBang,tagLine,tagInk,badge} from './v4/bang-tag.js';

const MAP='iso-town-v1',GAP=270,POLL=100,JOIN_WAIT=12000;
const DIRECTIONS=new Set(['se','sw','ne','nw']);

function publicPoint(value){
  if(!value||!Number.isFinite(value.x)||!Number.isFinite(value.y))return null;
  return {x:Math.round(value.x*1000)/1000,y:Math.round(value.y*1000)/1000,
    direction:DIRECTIONS.has(value.direction)?value.direction:'se'};
}
/** 🚗 {v, c, p?} short strings, or null (the scene checks it again: model.ts publicRide). */
function publicRide(r){
  if(!r||typeof r!=='object'||typeof r.v!=='string'||r.v.length>24)return null;
  return {v:r.v,c:typeof r.c==='string'?r.c.slice(0,24):'',...(typeof r.p==='string'&&r.p&&r.p.length<=24?{p:r.p}:{})};
}
/** 🐾 {b, c, n?, a?, r?, x?} of a pet, or null (the service cleaned it: live/street.py clean_pet). */
export function publicPet(p){
  if(!p||typeof p!=='object'||typeof p.b!=='string'||p.b.length>24||!Number.isInteger(p.c))return null;
  const out={b:p.b,c:p.c,a:Array.isArray(p.a)?p.a.filter(x=>typeof x==='string').slice(0,3):[]};
  if(typeof p.n==='string'&&p.n)out.n=p.n.slice(0,16);
  if(Number.isInteger(p.r)&&p.r>=1&&p.r<=6)out.r=p.r;
  if(typeof p.x==='string'&&p.x.length<=12)out.x=p.x;
  return out;
}
function publicPeer(value){
  const point=publicPoint(value);
  if(!point||typeof value.pid!=='string'||!value.pid||value.pid.length>40)return null;
  const activity=publicActivity(value.activity);
  if(value.activity!=null&&!activity)return null;
  return {pid:value.pid,name:typeof value.name==='string'?value.name.slice(0,24):'Mây',
    look:withPairs(value.lk&&typeof value.lk==='object'?value.lk:{},value.pr),pr:cleanPairs(value.pr),
    gender:value.g==='female'||value.g==='male'?value.g:null,fc:typeof value.fc==='string'?value.fc:'',...point,...(activity?{activity}:{}),...(publicRide(value.r)?{r:publicRide(value.r)}:{}),...(publicPet(value.pt)?{pt:publicPet(value.pt)}:{}),...bangOf(value.bg)};
}
/** ⚔️ {tag, ink, badge} for the name tag, or {} without a bang. */
export function bangOf(bg){
  const tag=tagLine(bg,true);if(!tag)return {};
  const b=badge(bg);return {tag:tag.slice(0,40),ink:tagInk(bg),...(b?{badge:b}:{}),...(bg.u===1?{bu:1}:{})};   // bu: the bang uniform is worn
}
function appearance(state){
  const look=withBang(lookOf(state)),g=state?.journey?.gender==='female'?'female':state?.journey?.gender==='male'?'male':null;
  return {look,g,key:JSON.stringify([look,g])};
}

/** Injectable transport/clock for deterministic protocol tests. Only bootIsometricTown is needed by app.js. */
export function createTownPresence(envGetter,options={}){
  const socket=options.transport||live,doc=options.document||globalThis.document,
    events=options.events||globalThis.window,now=options.now||(()=>Date.now()),leisure=options.leisure||leisurePresence;
  let socialEnabled=false;
  let room=null,me=null,joining=null,joinedPoint=null,lastPoint=null,lastSent=0,
    joinedAppearance=null,lastAppearance=null,
    anchor=null,joinedActivity=null,lastActivity=null,pendingActivityClear=false,
    interval=null,started=false,taken=false,seq=0,retryAt=0,statusNode=null,lastStatus='',lastWorld=null,
    joinedRide='null',lastRide='null',joinedPet='null',lastPet='null';
  const ride=()=>{try{return publicRide(world()?.getRide?.())}catch{return null;}};
  const myPet=()=>publicPet(env()?.api?.state?.journey?.pets?.ref);
  const peers=new Map(),off=[];
  const env=()=>typeof envGetter==='function'?envGetter():envGetter;
  const world=()=>env()?.world;
  const point=()=>{
    try{const at=publicPoint(world()?.getPresence?.());if(at){anchor=at;return at;}}catch{}
    return leisure.current?anchor:null;
  };
  const wanted=()=>!sitePresence.active&&!env()?.api?.state?.jail&&!taken&&doc?.visibilityState!=='hidden'&&Boolean(point());
  const enabled=()=>socket.state==='open'&&Boolean(socket.flags?.town);

  function updateSocial(){
    const active=!!room&&wanted()&&!leisure.current&&world()?.mode==='town';
    world()?.setSocialEnabled?.(active&&socialEnabled);
    options.social?.update({room,me,peers:[...peers.values()],active,enabled:socialEnabled});
  }
  function draw(){
    const w=world();
    if(w!==lastWorld){lastWorld?.setRemotePlayers?.([]);lastWorld=w;}
    const all=[...peers.values()];
    w?.setRemotePlayers?.(all.filter(peer=>!peer.activity));
    leisure.updatePeers(all);
    updateSocial();
  }
  function status(){
    updateSocial();
    const inTown=!sitePresence.active&&!env()?.api?.state?.jail&&Boolean(point())&&doc?.visibilityState!=='hidden';
    let text=room?`Khu phố trực tuyến · ${peers.size} người cùng dạo`:
      taken?'Khu phố đang mở ở tab khác':
      !env()?.api?.live?.url?'Chưa bật kết nối khu phố':
      socket.state==='open'&&!socket.flags?.town?'Khu phố trực tuyến đang tắt':
      socket.state==='open'?'Đang vào khu phố…':
      socket.state==='connecting'?'Đang kết nối khu phố…':
      socket.state==='down'?'Khu phố mất kết nối':
      socket.state==='off'?'Khu phố trực tuyến không khả dụng':'Khu phố chưa kết nối';
    if(options.status){options.status(text,inTown);return;}
    if(!statusNode&&doc?.createElement){
      statusNode=doc.getElementById('townPresenceStatus')||doc.createElement('div');
      statusNode.id='townPresenceStatus';statusNode.className='town-presence-status';
      statusNode.setAttribute('role','status');statusNode.setAttribute('aria-live','polite');
      statusNode.setAttribute('aria-atomic','true');
      // Layout belongs to the responsive HUD stylesheet. Keep this node outside
      // #isoHUD so shell rerenders cannot replace its live status announcement.
      if(!statusNode.parentNode)(doc.getElementById('stage')||doc.getElementById('world')?.parentNode||doc.body)?.append(statusNode);
    }
    // A server without the shared town (LIVE_TOWN off, no live service) says nothing: there is nothing to wait for.
    const unavailable=!room&&(!env()?.api?.live?.url||socket.state==='off'||socket.state==='open'&&!socket.flags?.town);
    if(statusNode){const hide=!inTown||unavailable,on=room?'true':'false';   // written only when they change: this runs 10 times a second
      if(statusNode.hidden!==hide)statusNode.hidden=hide;if(statusNode.dataset.connected!==on)statusNode.dataset.connected=on;
      if(text!==lastStatus){statusNode.textContent=text;lastStatus=text;}}
  }
  function clear(){joinedRide='null';lastRide='null';socialEnabled=false;room=null;me=null;joining=null;joinedPoint=null;lastPoint=null;joinedAppearance=null;lastAppearance=null;joinedActivity=null;lastActivity=null;pendingActivityClear=false;peers.clear();draw();status();}
  function leave(){
    if(room||joining)socket.send({t:'town_out',cid:`town-out-${++seq}`});
    clear();
  }
  function join(){
    if(!wanted()||!enabled()||room||joining||now()<retryAt)return;
    const at=point(),state=env()?.api?.state,activity=leisure.current;
    if(!at)return;
    const cid=`town-in-${++seq}`,look=appearance(state),r=ride(),pt=myPet();
    if(socket.send({t:'town_in',cid,map:MAP,...at,look:look.look,g:look.g,...(activity?{activity}:{}),...(r?{r}:{}),...(pt?{pt}:{})})){
      joining={cid,at:now()};joinedPoint=at;joinedAppearance=look.key;joinedActivity=activity;joinedRide=JSON.stringify(r);joinedPet=JSON.stringify(pt);status();
    }
  }
  function sync(){
    updateSocial();
    if(!wanted()||!enabled()){if(room||joining)leave();else status();return;}
    if(joining&&now()-joining.at>JOIN_WAIT){joining=null;retryAt=now()+2000;}
    if(!room){join();return;}
    const at=point(),activity=pendingActivityClear?null:leisure.current;
    if(!at||now()-lastSent<GAP)return;
    const look=appearance(env()?.api?.state),lookChanged=look.key!==lastAppearance,r=ride(),rideKey=JSON.stringify(r),rideChanged=rideKey!==lastRide;
    const pt=myPet(),petKey=JSON.stringify(pt),petChanged=petKey!==lastPet;
    if(!lookChanged&&!rideChanged&&!petChanged&&lastPoint&&at.x===lastPoint.x&&at.y===lastPoint.y&&at.direction===lastPoint.direction&&JSON.stringify(activity)===JSON.stringify(lastActivity))return;
    // Update the public outfit in this room; rejoining would reset the treasure lease/checkpoint.
    if(socket.send({t:'town_mv',...at,...(lookChanged?{look:look.look,g:look.g}:{}),...(activity||lastActivity?{activity}:{}),...(rideChanged?{r}:{}),...(petChanged?{pt}:{})})){lastSent=now();lastPoint=at;lastAppearance=look.key;lastActivity=activity;lastRide=rideKey;lastPet=petKey;pendingActivityClear=false;}
  }
  function onActivity(sample){
    // Preserve the exit even if another scene opens before the next 4 Hz send.
    // Its first position belongs to a new local coordinate space, not a teleport.
    if(sample===null&&(lastActivity||joining&&joinedActivity))pendingActivityClear=true;
    sync();
  }
  function onMode(){taken=false;retryAt=0;sync();}
  function start(){
    if(started)return api;started=true;
    off.push(sitePresence.subscribe(()=>sync()),socket.on('welcome',()=>{clear();retryAt=0;sync();}),
      socket.on('down',()=>{clear();}),
      socket.on('town_room',f=>{
        if(f.map!==MAP||sitePresence.active)return;
        if(!wanted()||!enabled()){socket.send({t:'town_out',cid:`town-out-${++seq}`});clear();return;}
        if(f.cid&&f.cid!==joining?.cid)return; // a late reply from an earlier town/work switch
        if(socket.flags?.treasure&&Number.isFinite(f.x)&&Number.isFinite(f.y)){
          world()?.correctPresence?.({x:f.x,y:f.y});joinedPoint=point();
        }
        socialEnabled=f.social===true;room=f.room;me=f.me;joining=null;lastPoint=joinedPoint;lastAppearance=joinedAppearance;lastActivity=joinedActivity;lastRide=joinedRide;lastPet=joinedPet;lastSent=now();peers.clear();
        for(const value of Array.isArray(f.people)?f.people:[]){const p=publicPeer(value);if(p&&p.pid!==me)peers.set(p.pid,p);}
        draw();status();
      }),
      socket.on('town',f=>{
        if(!room||f.room!==room||!wanted())return;
        let changed=false;
        for(const e of Array.isArray(f.ev)?f.ev:[]){
          if(e.pid===me)continue;
          if(e.k==='out'){changed=peers.delete(e.pid)||changed;}
          else if(e.k==='in'){const p=publicPeer(e);if(p){peers.set(p.pid,p);changed=true;}}
          else if(e.k==='mv'&&peers.has(e.pid)){
            const at=publicPoint(e),activity=publicActivity(e.activity);
            if(at&&(e.activity==null||activity)){
              const peer=peers.get(e.pid);Object.assign(peer,at);
              if(Object.hasOwn(e,'pr'))peer.pr=cleanPairs(e.pr);
              if(Object.hasOwn(e,'lk')){peer.look=e.lk&&typeof e.lk==='object'?e.lk:{};peer.gender=e.g==='female'||e.g==='male'?e.g:null;}
              if(Object.hasOwn(e,'lk')||Object.hasOwn(e,'pr')){const {pr:_,...lk}=peer.look||{};peer.look=withPairs(lk,peer.pr);}
              if(Object.hasOwn(e,'activity')){if(activity)peer.activity=activity;else delete peer.activity;}
              if(Object.hasOwn(e,'r')){const r=publicRide(e.r);if(r)peer.r=r;else delete peer.r;}
              if(Object.hasOwn(e,'pt')){const pt=publicPet(e.pt);if(pt)peer.pt=pt;else delete peer.pt;}
              if(Object.hasOwn(e,'bg')){delete peer.tag;delete peer.ink;delete peer.badge;delete peer.bu;Object.assign(peer,bangOf(e.bg));}
              changed=true;
            }
          }
        }
        if(changed){draw();status();}
      }),
      socket.on('town_left',f=>{
        if(f.why==='other'){taken=true;clear();return;}
        // Local leave already cleared peers. A late out reply must not clear a newer room.
      }),
      socket.on('renamed',f=>{const p=peers.get(f.pid);if(p&&typeof f.name==='string'){p.name=f.name.slice(0,24);draw();}}),
      socket.on('faced',f=>{const p=peers.get(f.pid);if(p&&typeof f.fc==='string'){p.fc=f.fc;draw();}}),
      socket.on('error',f=>{
        if(f.ref===joining?.cid||f.ref==='town_in'){
          joining=null;retryAt=now()+Math.max(1000,(Number(f.wait)||2)*1000);status();
        }else if(f.ref==='town_mv'){
          if(f.code==='not_in'){clear();retryAt=now()+1000;}
          else lastAppearance=null; // A rejected movement may also have carried the latest outfit.
        }
        // Invalid/speed samples wait for the walker to advance; no rejoin/teleport loop.
      }));
    events?.addEventListener?.('mnl:iso-mode',onMode);
    off.push(leisure.observeLocal(onActivity));
    doc?.addEventListener?.('visibilitychange',sync);
    interval=setInterval(sync,POLL);sync();return api;
  }
  function stop(){
    if(!started)return;leave();started=false;clearInterval(interval);interval=null;
    for(const unsubscribe of off.splice(0))unsubscribe();
    events?.removeEventListener?.('mnl:iso-mode',onMode);doc?.removeEventListener?.('visibilitychange',sync);
    if(statusNode)statusNode.hidden=true;
    options.social?.stop();
  }
  const api={start,stop,sync};return api;
}

let singleton=null;
export function bootIsometricTown(envGetter){
  if(!singleton)singleton=createTownPresence(envGetter,{social:createTownSocial(envGetter)}).start();
  return singleton;
}
