/** Real shared-map presence over the existing authenticated /live socket.
 * Phaser owns drawing and feet coordinates; game tasks/saves never enter this transport.
 * All careers use iso-town-v1. A room holds at most 30 real players and updates at 4/s.
 */
import {live} from './v4/live.js';
import {lookOf} from './v4/look.js';
import {leisurePresence,publicActivity} from './isometric/leisure-presence.js';

const MAP='iso-town-v1',GAP=270,POLL=100,JOIN_WAIT=12000;
const DIRECTIONS=new Set(['se','sw','ne','nw']);

function publicPoint(value){
  if(!value||!Number.isFinite(value.x)||!Number.isFinite(value.y))return null;
  return {x:Math.round(value.x*1000)/1000,y:Math.round(value.y*1000)/1000,
    direction:DIRECTIONS.has(value.direction)?value.direction:'se'};
}
function publicPeer(value){
  const point=publicPoint(value);
  if(!point||typeof value.pid!=='string'||!value.pid||value.pid.length>40)return null;
  const activity=publicActivity(value.activity);
  if(value.activity!=null&&!activity)return null;
  return {pid:value.pid,name:typeof value.name==='string'?value.name.slice(0,24):'Mây',
    look:value.lk&&typeof value.lk==='object'?value.lk:{},
    gender:value.g==='female'||value.g==='male'?value.g:null,fc:typeof value.fc==='string'?value.fc:'',...point,...(activity?{activity}:{})};
}

/** Injectable transport/clock for deterministic protocol tests. Only bootIsometricTown is needed by app.js. */
export function createTownPresence(envGetter,options={}){
  const socket=options.transport||live,doc=options.document||globalThis.document,
    events=options.events||globalThis.window,now=options.now||(()=>Date.now()),leisure=options.leisure||leisurePresence;
  let room=null,me=null,joining=null,joinedPoint=null,lastPoint=null,lastSent=0,
    anchor=null,joinedActivity=null,lastActivity=null,pendingActivityClear=false,
    interval=null,started=false,taken=false,seq=0,retryAt=0,statusNode=null,lastStatus='',lastWorld=null;
  const peers=new Map(),off=[];
  const env=()=>typeof envGetter==='function'?envGetter():envGetter;
  const world=()=>env()?.world;
  const point=()=>{
    try{const at=publicPoint(world()?.getPresence?.());if(at){anchor=at;return at;}}catch{}
    return leisure.current?anchor:null;
  };
  const wanted=()=>!env()?.api?.state?.jail&&!taken&&doc?.visibilityState!=='hidden'&&Boolean(point());
  const enabled=()=>socket.state==='open'&&Boolean(socket.flags?.town);

  function draw(){
    const w=world();
    if(w!==lastWorld){lastWorld?.setRemotePlayers?.([]);lastWorld=w;}
    const all=[...peers.values()];
    w?.setRemotePlayers?.(all.filter(peer=>!peer.activity));
    leisure.updatePeers(all);
  }
  function status(){
    const inTown=!env()?.api?.state?.jail&&Boolean(point())&&doc?.visibilityState!=='hidden';
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
    if(statusNode){statusNode.hidden=!inTown||unavailable;statusNode.dataset.connected=room?'true':'false';
      if(text!==lastStatus){statusNode.textContent=text;lastStatus=text;}}
  }
  function clear(){room=null;me=null;joining=null;joinedPoint=null;lastPoint=null;joinedActivity=null;lastActivity=null;pendingActivityClear=false;peers.clear();draw();status();}
  function leave(){
    if(room||joining)socket.send({t:'town_out',cid:`town-out-${++seq}`});
    clear();
  }
  function join(){
    if(!wanted()||!enabled()||room||joining||now()<retryAt)return;
    const at=point(),state=env()?.api?.state,activity=leisure.current;
    if(!at)return;
    const cid=`town-in-${++seq}`;
    if(socket.send({t:'town_in',cid,map:MAP,...at,look:lookOf(state),g:state?.journey?.gender==='female'?'female':state?.journey?.gender==='male'?'male':null,...(activity?{activity}:{})})){
      joining={cid,at:now()};joinedPoint=at;joinedActivity=activity;status();
    }
  }
  function sync(){
    if(!wanted()||!enabled()){if(room||joining)leave();else status();return;}
    if(joining&&now()-joining.at>JOIN_WAIT){joining=null;retryAt=now()+2000;}
    if(!room){join();return;}
    const at=point(),activity=pendingActivityClear?null:leisure.current;
    if(!at||now()-lastSent<GAP||lastPoint&&at.x===lastPoint.x&&at.y===lastPoint.y&&at.direction===lastPoint.direction&&JSON.stringify(activity)===JSON.stringify(lastActivity))return;
    if(socket.send({t:'town_mv',...at,...(activity||lastActivity?{activity}:{})})){lastSent=now();lastPoint=at;lastActivity=activity;pendingActivityClear=false;}
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
    off.push(socket.on('welcome',()=>{clear();retryAt=0;sync();}),
      socket.on('down',()=>{clear();}),
      socket.on('town_room',f=>{
        if(f.map!==MAP)return;
        if(!wanted()||!enabled()){socket.send({t:'town_out',cid:`town-out-${++seq}`});clear();return;}
        if(f.cid&&f.cid!==joining?.cid)return; // a late reply from an earlier town/work switch
        if(socket.flags?.treasure&&Number.isFinite(f.x)&&Number.isFinite(f.y)){
          world()?.correctPresence?.({x:f.x,y:f.y});joinedPoint=point();
        }
        room=f.room;me=f.me;joining=null;lastPoint=joinedPoint;lastActivity=joinedActivity;lastSent=now();peers.clear();
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
              if(Object.hasOwn(e,'activity')){if(activity)peer.activity=activity;else delete peer.activity;}
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
        }else if(f.ref==='town_mv'&&f.code==='not_in'){clear();retryAt=now()+1000;}
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
  }
  const api={start,stop,sync};return api;
}

let singleton=null;
export function bootIsometricTown(envGetter){
  if(!singleton)singleton=createTownPresence(envGetter).start();
  return singleton;
}
