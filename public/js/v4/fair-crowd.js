/** 🏮 Đi hội cùng nhau: the other players walking the fairground right now (live/fair.py over the live socket,
 * ./live.js), drawn among the stalls by ./fair-walk.js. Silent by design (owner, 03/10): nobody is announced coming
 * or going, no toast, no chat; they are simply there, walking. The walk joins when it mounts and leaves when the sheet
 * closes; on a stall page the player stays, standing at that stall (owner, 03/10: "chơi trò gì thì bên ngoài thấy
 * người ta đứng trò đó"): their walks carry `s`, the stall, and the others draw them at their own fairground's stand
 * of it, a little apart from each other, with the stall's badge over the name. An older live service does not relay
 * `s`: they are still seen standing there (where the walk put them), only without the badge.
 * Positions travel as fractions of the floor (the landscape and portrait fairgrounds differ): a walk is the path this
 * client walks ([[x,y],...], 0..1) and how long it takes here; the others replay it from where they see the walker.
 * A live service without the room (no welcome.flags.fair) or no socket at all: nobody else is drawn, nothing is sent.
 * 🛵 Someone riding their vehicle (./ride.js) says so on every walk (`r`: {v, c}, optional; an older peer or service
 * leaves it out and they are drawn walking): drawn on it while they move or stand about, beside it parked while they
 * play a stall. A vehicle this build cannot draw: walking.
 * 💑 Husband and wife (live/coride.py): `b` on someone is the driver they sit behind (drawn on that vehicle, behind);
 * my own walks coming back with `b` mean I sit behind (onBack), without it I am on foot again; `taken` (fair_room) /
 * `fair_taken`: the spouse drives the vehicle I asked for (onTaken).
 * Light: at most CAP others (the server's instance size), each a cached sprite; frames only while someone walks. */
import {live} from './live.js';
import {lookOf,figureOf,paintPlayer,CANVAS} from './look.js';
import {fromWire,drawRide,rider,steer,halfOf,topOf} from './ride.js';

const CAP=30,GAP=260,PTS=16,AV_W=110,AV_H=160;
/** Where the 1st, 2nd… of the others at one stall stand around its stand point (scene units; the stand itself is mine). */
const AROUND=[[50,6],[-50,6],[100,14],[-100,14],[25,28],[-25,28],[75,32],[-75,32]];
const word=v=>typeof v==='string'&&/^[a-z]{1,8}$/.test(v)?v:null;
const ok=()=>Boolean(live.flags?.fair)&&live.state==='open';
const r3=v=>Math.round(Math.min(1,Math.max(0,v))*1000)/1000;
/** A vehicle on the wire ({v, c}: short words) or null. */
const rideOf=r=>r&&typeof r==='object'&&typeof r.v==='string'&&/^[a-z0-9_]{1,24}$/.test(r.v)&&(r.c==null||typeof r.c==='string'&&/^[a-z0-9_]{0,24}$/.test(r.c))
  ?{v:r.v,c:r.c||'',...(pidOf(r.o)?{o:r.o}:{})}:null;
/** A live pid (16 hex) or null. */
const pidOf=v=>typeof v==='string'&&/^[0-9a-f]{16}$/.test(v)?v:null;

/** state(): the save (look, gender); content(): the static lists (the garage's, to draw a vehicle); redraw(): a frame
 * is due; still(): reduced motion (the others jump). */
export function crowd({state,content=()=>null,redraw,still,onBack=()=>{},onTaken=()=>{}}){
  const C={want:false,room:null,me:null,at:null,s:null,r:null,people:new Map(),pend:null,sentAt:0,timer:0,retry:0,joining:false,back:null};
  let fontEpoch=0;
  globalThis.document?.fonts?.addEventListener?.('loadingdone',()=>{fontEpoch++;redraw();});
  const clear=()=>{const was=C.back;C.room=null;C.me=null;C.joining=false;C.people.clear();clearTimeout(C.timer);C.pend=null;C.back=null;if(was)onBack(null,null);redraw();};

  /** `r`: the vehicle ridden ({v, c}, ./ride.js wire) or none. */
  function join(at,r){
    C.want=true;if(at)C.at=at.map(r3);if(r!==undefined)C.r=rideOf(r);
    if(C.room||C.joining||!ok())return;
    const st=state()||{};
    C.joining=live.send({t:'fair_in',look:lookOf(st),g:st.journey?.gender??null,x:C.at?.[0]??.2,y:C.at?.[1]??.95,...(C.s?{s:C.s}:{}),...(C.r?{r:C.r}:{})});
  }
  function leave(){
    if(!C.want&&!C.room)return;
    C.want=false;C.s=null;clearTimeout(C.retry);
    if(C.room||C.joining)live.send({t:'fair_out'});
    clear();
  }
  /** My walk (scene points already turned into fractions, the first where I stand), ms long here; `s`: the stall I
   * play at its end (none: walking about), `r` the vehicle ridden (none: on foot). Staying put only to change `s` or
   * `r` keeps a walk still waiting to be sent. */
  function walk(path,ms,s=null,r=null){
    if(!path?.length)return;
    C.at=path[path.length-1].map(r3);C.s=word(s);C.r=rideOf(r);
    if(!C.room)return;
    let p=path.map(q=>q.map(r3));
    if(p.length>PTS){const n=p.length;p=Array.from({length:PTS},(_,i)=>p[Math.round(i*(n-1)/(PTS-1))]);}
    const put=p.every(q=>Math.abs(q[0]-p[0][0])<.01&&Math.abs(q[1]-p[0][1])<.01);
    C.pend=put&&C.pend?{p:C.pend.p,ms:C.pend.ms}:{p,ms:Math.max(0,Math.round(ms))};
    if(C.s)C.pend.s=C.s;
    if(C.r)C.pend.r=C.r;
    const wait=C.sentAt+GAP-performance.now();clearTimeout(C.timer);
    if(wait<=0)flush();else C.timer=setTimeout(flush,wait);
  }
  function flush(){if(!C.pend||!C.room)return;if(C.back){C.pend=null;return;}live.send({t:'fair_mv',...C.pend});C.pend=null;C.sentAt=performance.now();}
  /** 💑 Sit behind `to` (my spouse riding here); null: get off at `at` (fractions, where I am). */
  function back(to,at=null){
    if(!C.room)return;
    if(to){clearTimeout(C.timer);C.pend=null;live.send({t:'fair_back',to});return;}
    live.send({t:'fair_back',to:null,...(at?{x:r3(at[0]),y:r3(at[1])}:{})});
  }
  /** My own walk as the room hears it: with `b` I sit behind that driver, without it I am on foot (where it ends). */
  function mine(e){
    const b=pidOf(e.b),end=Array.isArray(e.p)&&e.p.length?e.p[e.p.length-1]:null;
    if(b===C.back)return;
    C.back=b;if(!b&&end)C.at=end.map(r3);
    onBack(b,end);
  }

  /* ---- the others ---- */
  function person(e){return {pid:e.pid,name:e.name||'',lk:e.lk,g:e.g,x:e.x,y:e.y,s:word(e.s),r:rideOf(e.r),b:pidOf(e.b),path:null,t0:0,ms:0,len:0,sp:null,spk:'',rv:rider(),lx:null,fig:null,fk:'p'+JSON.stringify([e.lk,e.g])};}
  function add(e){if(e.pid===C.me||C.people.has(e.pid)||C.people.size>=CAP||typeof e.x!=='number')return;C.people.set(e.pid,person(e));}
  function move(e){
    const q=C.people.get(e.pid);if(!q||!Array.isArray(e.p)||!e.p.length)return;
    q.s=word(e.s);q.r=rideOf(e.r);q.b=pidOf(e.b);   // every walk says them anew (an older live service never sends them)
    const end=e.p[e.p.length-1];
    if(still()||!(e.ms>0)){q.x=end[0];q.y=end[1];q.path=null;return;}
    const now=performance.now(),[x,y]=at(q,now),path=[[x,y],...e.p.slice(1)];   // from where this player sees them
    let len=0;for(let i=1;i<path.length;i++)len+=Math.hypot(path[i][0]-path[i-1][0],path[i][1]-path[i-1][1]);
    if(len<1e-4){q.x=end[0];q.y=end[1];q.path=null;return;}
    q.path=path;q.len=len;q.t0=now;q.ms=Math.min(3000,e.ms);q.x=end[0];q.y=end[1];
  }
  /** Where someone is now (fractions) and whether they are walking. */
  function at(q,now){
    if(!q.path)return [q.x,q.y,false];
    const k=(now-q.t0)/q.ms;if(k>=1){q.path=null;return [q.x,q.y,false];}
    let left=k*q.len;
    for(let i=1;i<q.path.length;i++){const a=q.path[i-1],b=q.path[i],seg=Math.hypot(b[0]-a[0],b[1]-a[1]);
      if(left<=seg&&seg>0){const u=left/seg;return [a[0]+(b[0]-a[0])*u,a[1]+(b[1]-a[1])*u,true];}left-=seg;}
    return [q.x,q.y,false];
  }

  live.on('fair_room',f=>{
    C.joining=false;
    if(!C.want){live.send({t:'fair_out'});return;}
    C.room=f.room;C.me=f.me;C.people.clear();
    for(const e of (f.people||[]).slice(0,CAP))add(e);
    if(f.taken)onTaken(f.taken);
    redraw();
  });
  live.on('fair',f=>{
    if(!C.room||!Array.isArray(f.ev))return;
    for(const e of f.ev){
      if(e.pid===C.me){if(e.k==='mv')mine(e);continue;}
      if(e.k==='in')add(e);else if(e.k==='out')C.people.delete(e.pid);else if(e.k==='mv')move(e);
    }
    redraw();
  });
  live.on('fair_taken',f=>{if(C.room)onTaken(f);});
  live.on('fair_left',f=>{if(f.why==='other'){C.want=false;clear();}});   // another tab of mine walks the fair now
  live.on('welcome',()=>{C.room=null;C.joining=false;C.people.clear();if(C.want)join();});
  live.on('down',()=>{if(C.room||C.people.size)clear();C.joining=false;});
  live.on('error',f=>{
    if(f.ref==='fair_in'){C.joining=false;
      if(f.code==='slow'&&C.want){clearTimeout(C.retry);C.retry=setTimeout(()=>{if(C.want)join();},(Math.max(1,Number(f.wait)||1)+.5)*1000);}}
    else if(f.ref==='fair_mv'&&f.code==='not_in'){C.room=null;C.people.clear();if(C.want)join();redraw();}
  });

  /* ---- drawing (scene units: `xy` maps fractions onto this fairground, `scale(y)` is the figure's size there) ---- */
  function sprite(q,px){
    const key=String(Math.round(px*100));if(q.sp&&q.spk===key)return q.sp;
    const cv=q.sp||document.createElement('canvas');cv.width=Math.ceil(AV_W*px);cv.height=Math.ceil(AV_H*px);
    const c=cv.getContext('2d');c.setTransform(px,0,0,px,55*px,150*px);c.clearRect(-55,-150,AV_W,AV_H);
    try{paintPlayer(c,figureOf(q.lk,q.g),CANVAS);}catch(e){console.warn('hội chợ: look',e);}
    q.sp=cv;q.spk=key;return cv;
  }
  /** [[depth y, draw]] for each other walker (sorted with the stalls and me by the caller); fills q.sx/q.sy for tags.
   * snap(p): someone standing still is put on free floor of this layout (theirs may be the other one), `key` names it;
   * stand(s): this layout's stand point of stall s (null: no such stall here), where someone playing it stands. */
  function items(c,{xy,scale,px,unit=px,t,snap,key,stand,me=null}){
    const out=[],now=performance.now(),slot=new Map(),ct=content(),pill=new Map();
    for(const q of C.people.values())if(q.b&&(q.b===C.me||C.people.get(q.b)?.r))pill.set(q.b,q);   // 💑 who sits behind whom
    for(const q of C.people.values()){
      q.on=Boolean(q.b&&pill.get(q.b)===q);q.byMe=false;if(q.on)continue;   // drawn behind their driver (me: by the caller, who sets byMe)
      const [u,v,moving]=at(q,now);let [x,y]=xy(u,v);
      const st=!moving&&q.s&&stand?stand(q.s):null;
      if(st){const i=slot.get(q.s)||0,k=`${q.s},${i},${key}`,d=AROUND[i%AROUND.length];slot.set(q.s,i+1);
        if(q.snk!==k){const p=[st[0]+d[0],st[1]+d[1]];q.snk=k;q.snp=snap?.(p)||p;}[x,y]=q.snp;}
      else if(!moving&&snap){const k=`${u},${v},${key}`;if(q.snk!==k){q.snk=k;q.snp=snap([x,y])||[x,y];}[x,y]=q.snp;}
      const s=scale(y);q.sx=x;q.sy=y;q.top=y-132*s;
      if(q.rk!==q.r){q.rk=q.r;q.ride=q.r&&fromWire(q.r,ct);}
      const ride=q.ride;
      if(ride){   // 🛵 on their vehicle; at a stall, on foot beside it
        const dt=Math.min(.1,Math.max(0,(now-(q.lt||now))/1000));
        if(q.lx!=null)steer(q.rv,x-q.lx,Math.abs(x-q.lx)/s,dt,still());q.lx=x;q.lt=now;
        if(!moving&&st){const px_=x+(x<st[0]?-1:1)*(halfOf(ride)*s+14),f=q.rv.face;
          out.push([y+4,()=>drawRide(c,{x:px_,y:y+4,s,px:unit,v:ride,r:{face:f,from:f,turn:1,ang:0}})]);}
        else{q.fig??=figureOf(q.lk,q.g);q.top=y-topOf(ride)*s;
          const b=pill.get(q.pid),F2=b?(b.fig??=figureOf(b.lk,b.g)):C.back===q.pid&&me?me.F:null,fk2=b?b.fk:F2?me.fk:'';
          if(b){b.sx=x;b.sy=y;b.top=q.top-16/s;}
          out.push([y,()=>drawRide(c,{x,y,s,px:unit,F:q.fig,fkey:q.fk,F2,fkey2:fk2,v:ride,r:q.rv})]);continue;}
      }
      out.push([y,()=>{const sp=sprite(q,px),bob=moving&&!still()?-Math.abs(Math.sin(t*9+x*.05))*3:0;
        c.drawImage(sp,x-55*s,y-150*s+bob,AV_W*s,AV_H*s);}]);
    }
    return out;
  }
  /** Small names over the others (screen units; `fallback` for a player without a name); badge(s): the emoji of
   * the stall someone plays ('': none), in a small bubble over their name. */
  function tags(c,{sx,sy,fallback,badge,dpr=1}){
    if(!C.people.size)return;
    for(const q of C.people.values()){
      if(typeof q.sx!=='number'||q.on&&q.b===C.me&&!q.byMe)continue;
      const name=q.name||fallback,x=sx(q.sx),y=sy(q.top)-8;
      const b=q.s&&badge?badge(q.s):'';
      const px=Math.max(1,Math.min(2,dpr)),key=JSON.stringify([name,b,px,fontEpoch]);
      if(q.tag?.key!==key){
        // One small bitmap per room member; replacing/leaving the room drops it with that member.
        const cv=document.createElement('canvas'),t=cv.getContext('2d');t.font='700 10px "Trebuchet MS",sans-serif';
        const w=Math.max(22,Math.ceil(t.measureText(name).width+10)),h=40;
        cv.width=Math.ceil(w*px);cv.height=Math.ceil(h*px);t.setTransform(px,0,0,px,0,0);
        t.textAlign='center';t.textBaseline='middle';t.font='700 10px "Trebuchet MS",sans-serif';
        t.fillStyle='rgba(255,250,240,.82)';t.beginPath();t.roundRect?t.roundRect(0,23.5,w,15,7.5):t.rect(0,23.5,w,15);t.fill();
        t.fillStyle='#4a3226';t.fillText(name,w/2,31.5);
        if(b){
          t.fillStyle='rgba(255,250,240,.95)';t.strokeStyle='rgba(143,45,42,.6)';t.lineWidth=1;
          t.beginPath();t.arc(w/2,11,10,Math.PI*.62,Math.PI*2.38);t.lineTo(w/2,24);t.closePath();t.fill();t.stroke();
          t.font='12px "Segoe UI Emoji","Apple Color Emoji","Noto Color Emoji",sans-serif';t.fillStyle='#4a3226';t.fillText(b,w/2,12);
        }
        q.tag={key,cv,w,h};
      }
      c.drawImage(q.tag.cv,x-q.tag.w/2,y-31,q.tag.w,q.tag.h);
    }
  }
  const busy=()=>{for(const q of C.people.values())if(q.path||q.rv.turn<1)return true;return false;};
  /** Where someone is now (fractions; null: not here) and whether they ride. */
  const where=pid=>{const q=C.people.get(pid);if(!q)return null;const [x,y,m]=at(q,performance.now());return {x,y,moving:m,r:q.r,b:q.b,name:q.name,rv:q.rv};};
  /** The one sitting behind pid (a person entry) or null. */
  const pillion=pid=>{for(const q of C.people.values())if(q.b===pid)return q;return null;};

  return {join,leave,walk,items,tags,busy,back,where,pillion,me:()=>C.me,behind:()=>C.back,coride:()=>Boolean(live.flags?.coride),
    state:()=>({on:Boolean(C.room),room:C.room,me:C.me,s:C.s,back:C.back,people:[...C.people.values()].map(q=>{const [x,y,m]=at(q,performance.now());return {pid:q.pid,name:q.name,x,y,walking:m,s:q.s,ride:q.r?.v||null,b:q.b};})})};
}
