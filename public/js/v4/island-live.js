/** 🏝️ The island room on the live socket (live/island.py), shared by both interfaces' scenes (v4/island-scene.js):
 * join with the trip id, the look and where I stand; the others' comings, walks, waves, bubbles and spots; leave.
 * Positions are the map's fractions (public/js/island-layout.js). Without a live socket (service down or off) the
 * scene still works for the player alone; a reconnect (a new welcome) joins again. Every rule is the server's.
 * 🏝️ 24/10: an island reaches past the old square (public/js/island-layout.js BOUNDS); the room still carries 0..1
 * (live/island.py clamps there): positions go out as their fraction of the bigger map and come back from it. */
import {BOUNDS} from '../island-layout.js';
import {withFish} from './look.js';   // 🎣 a walker's carried fish (`fh`, live/fish_carry.py) drawn in their hands
const BUBBLE_MS=6000,EMOTE_MS=2600,ACT_MS=5000;
const SPAN=BOUNDS[1]-BOUNDS[0];
/** A map point → the room's 0..1, and back. */
export const toWire=v=>+Math.max(0,Math.min(1,(v-BOUNDS[0])/SPAN)).toFixed(4);
export const fromWire=v=>BOUNDS[0]+(Number(v)||0)*SPAN;
const fromPt=p=>[fromWire(p?.[0]),fromWire(p?.[1])];

/** Where a walker is at `now` (ms): along [from → to] over `ms`. */
export function peerAt(p,now){
  if(!p.ms||now>=p.t0+p.ms)return p.to;
  const k=Math.max(0,(now-p.t0)/p.ms);return [p.from[0]+(p.to[0]-p.from[0])*k,p.from[1]+(p.to[1]-p.from[1])*k];
}

export function createIslandPresence({live,trip,look,gender,at,clock=()=>Date.now(),onChange=()=>{},onLeft=()=>{},onError=()=>{}}){
  const peers=new Map(),offs=[];
  let room=null,me=null,stopped=false,owner=null;
  const peer=x=>({pid:x.pid,name:String(x.name||''),lk:withFish(x.lk||{},x.fh),g:x.g||null,o:Boolean(x.o),from:fromPt([x.x,x.y]),to:fromPt([x.x,x.y]),t0:clock(),ms:0,bubble:null,emote:null,act:null});
  function join(){
    if(stopped||!live)return false;
    const [x,y]=at();
    const {fh,...bare}=look||{};   // 🎣 the carried fish goes apart as {sp, kg}: the service checks it (live/fish_carry.py)
    return live.send({t:'isl_in',trip,look:bare,g:gender,x:toWire(x),y:toWire(y),...(fh?{fh:{sp:fh.sp,kg:fh.kg}}:{})});
  }
  function event(e){
    const now=clock();
    if(e.k==='in'){peers.set(e.pid,peer(e));return;}
    if(e.k==='out'){peers.delete(e.pid);return;}
    const p=peers.get(e.pid),mine=e.pid===me;
    if(!p&&!mine)return;
    if(e.k==='mv'&&p){const here=peerAt(p,now);Object.assign(p,{from:here,to:fromPt(e.p?.[1]),t0:now,ms:Math.max(0,Number(e.ms)||0)});}
    else if(e.k==='emote')(mine?self:p).emote={e:e.e,until:now+EMOTE_MS};
    else if(e.k==='said')(mine?self:p).bubble={text:String(e.text||''),until:now+BUBBLE_MS};
    else if(e.k==='do'&&p)p.act={s:e.s,until:now+ACT_MS};
  }
  const self={bubble:null,emote:null};
  if(live){
    offs.push(live.on('isl_room',f=>{if(f.trip!==trip||stopped)return;room=f.room;me=f.me;owner=f.owner;peers.clear();for(const x of f.people||[])peers.set(x.pid,peer(x));onChange('room',f);}));
    offs.push(live.on('isl',f=>{if(f.room!==room||stopped)return;for(const e of f.ev||[])event(e);onChange('ev',f);}));
    offs.push(live.on('isl_left',f=>{if(stopped||f.why==='out')return;const was=room;room=null;peers.clear();if(was||f.why!=='other')onLeft(f.why);}));
    offs.push(live.on('welcome',()=>{if(!stopped){room=null;join();}}));
    offs.push(live.on('down',()=>{room=null;peers.clear();onChange('down');}));
    offs.push(live.on('error',f=>{if(stopped)return;if(['isl_in','isl_say','isl_mv','isl_emote','isl_do'].includes(f.ref)&&f.code!=='slow')onError(f.msg||'',f.code,f.ref);}));
  }
  return {
    peers,self,
    get me(){return me;},get owner(){return owner;},get online(){return Boolean(room);},
    start(){join();return this;},
    move(from,to,ms){if(room)live.send({t:'isl_mv',p:[from.map(toWire),to.map(toWire)],ms:Math.round(ms)});},
    emote(e){if(room)live.send({t:'isl_emote',e});else self.emote={e,until:clock()+EMOTE_MS};},
    say(text){if(room&&text)return live.send({t:'isl_say',text});return false;},
    act(s){if(room)live.send({t:'isl_do',s});},
    stop(){if(stopped)return;stopped=true;if(room)live.send({t:'isl_out'});room=null;peers.clear();offs.splice(0).forEach(off=>off());},
  };
}
