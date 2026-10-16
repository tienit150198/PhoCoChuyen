/** 🏝️ The island room on the live socket (live/island.py), shared by both interfaces' scenes (v4/island-scene.js):
 * join with the trip id, the look and where I stand; the others' comings, walks, waves, bubbles and spots; leave.
 * Positions are the map's fractions (public/js/island-layout.js). Without a live socket (service down or off) the
 * scene still works for the player alone; a reconnect (a new welcome) joins again. Every rule is the server's. */
const BUBBLE_MS=6000,EMOTE_MS=2600,ACT_MS=5000;

/** Where a walker is at `now` (ms): along [from → to] over `ms`. */
export function peerAt(p,now){
  if(!p.ms||now>=p.t0+p.ms)return p.to;
  const k=Math.max(0,(now-p.t0)/p.ms);return [p.from[0]+(p.to[0]-p.from[0])*k,p.from[1]+(p.to[1]-p.from[1])*k];
}

export function createIslandPresence({live,trip,look,gender,at,clock=()=>Date.now(),onChange=()=>{},onLeft=()=>{},onError=()=>{}}){
  const peers=new Map(),offs=[];
  let room=null,me=null,stopped=false,owner=null;
  const peer=x=>({pid:x.pid,name:String(x.name||''),lk:x.lk||{},g:x.g||null,o:Boolean(x.o),from:[x.x,x.y],to:[x.x,x.y],t0:clock(),ms:0,bubble:null,emote:null,act:null});
  function join(){
    if(stopped||!live)return false;
    const [x,y]=at();
    return live.send({t:'isl_in',trip,look,g:gender,x:+x.toFixed(4),y:+y.toFixed(4)});
  }
  function event(e){
    const now=clock();
    if(e.k==='in'){peers.set(e.pid,peer(e));return;}
    if(e.k==='out'){peers.delete(e.pid);return;}
    const p=peers.get(e.pid),mine=e.pid===me;
    if(!p&&!mine)return;
    if(e.k==='mv'&&p){const here=peerAt(p,now);Object.assign(p,{from:here,to:e.p[1],t0:now,ms:Math.max(0,Number(e.ms)||0)});}
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
    move(from,to,ms){if(room)live.send({t:'isl_mv',p:[from.map(v=>+v.toFixed(4)),to.map(v=>+v.toFixed(4))],ms:Math.round(ms)});},
    emote(e){if(room)live.send({t:'isl_emote',e});else self.emote={e,until:clock()+EMOTE_MS};},
    say(text){if(room&&text)return live.send({t:'isl_say',text});return false;},
    act(s){if(room)live.send({t:'isl_do',s});},
    stop(){if(stopped)return;stopped=true;if(room)live.send({t:'isl_out'});room=null;peers.clear();offs.splice(0).forEach(off=>off());},
  };
}
