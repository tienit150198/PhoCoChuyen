/** 💬 The live socket (chat, online friends; later strolling the phố and dates): one WebSocket to the live
 * service (live/ on the server, wss://<this host>/live behind nginx). Always on but tiny: it keeps the
 * welcome (switches, me, friends, chats, unread) and the chat button with its badge; the chat dialog itself
 * (./chat.js) loads on first tap.
 *
 * It opens a socket only when the game server names one (bootstrap `live.url`, env LIVE_URL=/live on the game
 * server). app.js boots it right after the first frame; until the first welcome the chat button is a greyed
 * placeholder whose tap says "đang kết nối…" (06/10: the button used to appear only after the welcome, and a page
 * loaded during the live service's restart showed no chat for a minute or more). A welcome without `flags.chat`
 * removes it. Before a first welcome ever arrives (service restarting or down, nginx not routing /live) it retries
 * at 3, 8 and 20 s, then slowly (1, 2, 5, 10 minutes) so the game server never sees a reconnect storm; after one it reconnects with back-off (1, 2, 4, 8, 15 s, jitter), at once when the tab comes
 * back or the network returns; the chat dialog refreshes its latest history page. Close codes from
 * the service: 1012 restart (jittered return), 4001 switched off (10 minutes), 4002 another tab took over.
 *
 * For other features: live.on(type, fn) for any server frame, live.send(frame), live.flags, live.unread().
 * 💕 Dates (./dating.js, lazy): live.bonds (pids "đang tìm hiểu"), dateNav(), openDate(), benchSpot(walk) for the stroll's bench.
 * 🙂 Faces: `hello` carries this save's face code (./face-code.js faceCode: s.avatar and the wardrobe clothes); when it
 * changes (the builder, Tủ đồ) a `face` frame follows, but only to a service whose welcome `me` has `fc` (an older one
 * would answer "unknown"). `faced {pid, fc}` updates friends and DM peers. */
import {icon} from '../icons.js';
import {stylesheet} from '../lazy.js';
import {faceCode} from './face-code.js';

const RETRY=[1,2,4,8,15],SLOW=[3,8,20,60,120,300,600],PING_MS=25000,DEAD_MS=60000,CONNECT_MS=20000;
const listeners=new Map();
let env=null,ws=null,attempt=0,timer=0,pinger=0,lastFrame=0,tried=0,probing=false,fab=null,shown=false,shownDate=false,renderTimer=0,lastTotal=-1,cssAsked=false,sentFc=null,faceTimer=0;
let connectTimer=0,probeTimer=0,painted='';
/** The face code of this save ('' while the save is not loaded). */
const myFc=()=>{try{return env?.api?.state?faceCode(env.api.state):'';}catch(e){console.warn('face:',e);return '';}};
/** 🙂 After a change of face or clothes: tell a service that knows faces (once per change). */
function syncFace(){clearTimeout(faceTimer);const fc=myFc();if(!fc||fc===sentFc||!live.me||!('fc' in live.me))return;if(live.send({t:'face',fc}))sentFc=fc;}
/** Trying outfits changes the save many times a minute: one frame once the player settles (the server allows 6 a minute). */
const syncFaceSoon=(ms=2000)=>{clearTimeout(faceTimer);faceTimer=setTimeout(syncFace,ms);};
/** A read started before a rename may still contain the old name. Wait for it before a fresh read. */
async function syncName(){
  const api=env?.api;if(!api?.refresh)return;
  try{
    if(api.refreshing)await api.refreshing.catch(()=>{});
    if(api.state?.name!==live.me?.name)await api.refresh();
  }catch(e){console.warn('name refresh:',e);}
}
function adoptName(){
  const name=live.me?.name;if(typeof name!=='string'||!name.trim())return;
  if(env?.api?.account)env.api.account.display=name;
  if(env?.api?.state?.name!==name)syncName();
}

export const live={
  state:'idle',            // idle | connecting | open | down | off
  welcomed:false,          // a welcome arrived once in this page: the service exists
  flags:{},me:null,friends:[],chans:[],limits:{},
  bonds:[],                // 💕 pids "đang tìm hiểu" (both ❤️ after a date): shown on their cards
  /** Open chats ask to be resumed after a reconnect: {channel id: last message id} (set by chat.js). */
  resume:()=>({}),
  on(type,fn){if(!listeners.has(type))listeners.set(type,new Set());listeners.get(type).add(fn);return ()=>listeners.get(type)?.delete(fn);},
  send(frame){if(ws&&ws.readyState===1&&live.state==='open'){ws.send(JSON.stringify(frame));return true;}return false;},
  /** Unread messages for the badges: a chat whose notifications are off (🔔 quiet) still counts in its own row only. */
  unread(){return live.chans.reduce((n,c)=>n+(live.quiet(c)?0:(c.unread||0)),0);},
  quiet(c){return Boolean(c?.quiet&&c.quiet*1000>Date.now());},
  chan(id){return live.chans.find(c=>c.id===id)||null;},
  friend(pid){return live.friends.find(f=>f.pid===pid)||null;},
  /** Bring a chat to the top of the list (a message just arrived or was sent). */
  touch(c){const i=live.chans.indexOf(c);if(i>0){live.chans.splice(i,1);live.chans.unshift(c);}},
  /** Back in sight or back online: try again now (only once the service is known to exist and is not off); an open
   * socket that has been quiet a while (a phone back from another app) is checked with a ping, a dead one replaced.
   * force (📸 the fair's booth opened, its "Thử lại"): now whatever the state, also before a first welcome, during
   * a back-off, or over a connect that has hung for 4 s. The caller forces once per wait, never in a loop. */
  reconnect(force=false){
    if(!env?.api?.live?.url)return;
    if(live.state==='open'){if(force||Date.now()-lastFrame>PING_MS+5000)probe();return;}
    if(!force&&live.state!=='down')return;   // before a first welcome too: a tab back in sight tries again at once
    if(live.state==='connecting'&&Date.now()-tried<4000)return;
    attempt=0;clearTimeout(timer);abandon();connect();
  },
};
const emit=(type,f)=>{for(const fn of listeners.get(type)||[]){try{fn(f);}catch(e){console.warn('live:',type,e);}}for(const fn of listeners.get('*')||[]){try{fn(f);}catch(e){console.warn('live:*',e);}}};

function url(){
  const u=env?.api?.live?.url||'';
  return u.startsWith('/')?`${location.protocol==='https:'?'wss':'ws'}://${location.host}${u}`:u;
}

function connect(){
  if(ws)return;
  clearTimeout(timer);tried=Date.now();
  if(typeof WebSocket!=='function'||document.visibilityState==='hidden'&&!live.welcomed)return schedule();
  live.state='connecting';
  let sock;
  try{sock=new WebSocket(url());}catch{return schedule();}
  ws=sock;
  // A half-open transport may never emit error/close, or never send welcome.
  connectTimer=setTimeout(()=>{if(ws!==sock||live.state!=='connecting')return;console.info('[live] connection deadline');abandon();schedule();},CONNECT_MS);
  sock.onopen=()=>{if(ws!==sock)return;lastFrame=Date.now();const r=live.resume(),fc=myFc();sentFc=fc||null;
    sock.send(JSON.stringify({t:'hello',v:1,...(r&&Object.keys(r).length?{resume:r}:{}),...(fc?{fc}:{})}));};
  sock.onmessage=e=>{if(ws!==sock)return;lastFrame=Date.now();let f;try{f=JSON.parse(e.data);}catch{return;}if(f&&typeof f.t==='string')frame(f);};
  sock.onclose=e=>{
    if(ws!==sock)return;
    console.info('[live] connection closed',e.code,Boolean(e.wasClean));
    ws=null;clearSocketTimers();
    const wasOpen=live.state==='open';
    live.state=e.code===4001?'off':'down';
    emit('down',{code:e.code});paint();
    if(e.code===4001)return schedule(600);
    if(e.code===4002)return schedule(60);
    if(e.code===1012){attempt=0;return schedule(0.5+Math.random()*3.5);}
    if(wasOpen)attempt=0;
    schedule();
  };
  sock.onerror=()=>{};
}
function clearSocketTimers(){clearInterval(pinger);clearTimeout(connectTimer);clearTimeout(probeTimer);probing=false;}
/** Let go of the current socket without waiting for its close (a dead one may take minutes): 'down' when it was open. */
function abandon(){
  const s=ws;if(!s)return;
  ws=null;clearSocketTimers();
  const was=live.state==='open';live.state='down';
  try{s.close();}catch{/* already closing */}
  if(was){emit('down',{code:0});paint();}
}
/** Is the open socket alive? A ping; nothing back within 4 s: a new socket at once. */
function probe(){
  if(probing||!ws)return;
  probing=true;const t0=lastFrame,s=ws;live.send({t:'ping'});
  probeTimer=setTimeout(()=>{probing=false;if(ws===s&&live.state==='open'&&lastFrame===t0){abandon();attempt=0;connect();}},4000);
}
function schedule(secs){
  clearTimeout(timer);
  if(secs==null){const list=live.welcomed?RETRY:SLOW;secs=list[Math.min(attempt,list.length-1)]*(0.8+Math.random()*0.4);attempt++;}
  timer=setTimeout(connect,secs*1000);
}

function frame(f){
  switch(f.t){
    case'welcome':
      clearTimeout(connectTimer);
      live.welcomed=true;live.flags=f.flags||{};
      if(!['chat','street','dating','wedding','fair','home','visits','town','kara','bark'].some(k=>live.flags[k])){live.state='off';break;}
      live.state='open';attempt=0;
      live.me=f.me||null;live.friends=f.friends||[];live.chans=f.chans||[];live.limits=f.limits||{};live.bonds=f.bonds||[];
      adoptName();
      if(live.flags.dating&&(f.date||f.bench))import('./dating.js').then(m=>m.datingBoot(env,f)).catch(e=>console.warn('dating:',e));   // back in a date after a reload
      // Browser timers can pause in the background. Old frame age alone isn't
      // evidence of a dead socket: ask for a fresh reply before replacing it.
      clearInterval(pinger);pinger=setInterval(()=>{if(Date.now()-lastFrame>DEAD_MS){probe();return;}live.send({t:'ping'});},PING_MS);
      deepLink();syncFace();   // the save may have loaded after the hello
      break;
    case'state':
      if(f.friends)live.friends=f.friends;if(f.chans)live.chans=f.chans;if(f.me)live.me=f.me;
      if(f.me)adoptName();
      if(live.me){if(f.town)live.me.town=f.town;if(typeof f.online==='boolean')live.me.online=f.online;}
      break;
    case'presence':{const x=live.friend(f.pid);if(x)x.on=f.on;for(const c of live.chans)if(c.peer?.pid===f.pid)c.peer.on=f.on;break;}
    case'renamed':{
      if(typeof f.pid!=='string'||typeof f.name!=='string'||!f.name.trim())return;
      const put=x=>{if(x?.pid===f.pid)x.name=f.name;};
      put(live.me);for(const x of live.friends)put(x);
      for(const c of live.chans){put(c.peer);put(c.last);put(c.last?.reply);}
      if(f.pid===live.me?.pid)adoptName();
      window.dispatchEvent(new CustomEvent('mnl:marriage'));
      break;}
    case'prefs':if(live.me)live.me.online=f.online;if(!f.online){for(const x of live.friends)x.on=false;for(const c of live.chans)if(c.peer)c.peer.on=false;}break;
    case'muted':if(live.me){live.me.muted=f.until;live.me.town=f.until*1000>Date.now()?'muted':'ok';}break;
    case'chan':{const c=live.chan(f.chan.id);if(c)Object.assign(c,f.chan,{unread:c.unread,last:c.last});else live.chans.unshift(f.chan);break;}
    case'unchan':live.chans=live.chans.filter(c=>c.id!==f.ch);break;
    case'quiet':{const c=live.chan(f.ch);if(c){if(f.until)c.quiet=f.until;else delete c.quiet;}break;}   // 🔔 notifications of one chat
    case'bond':if(!live.bonds.includes(f.pid))live.bonds.push(f.pid);break;
    case'faced':{   // 🙂 a face changed (mine from another tab, a friend's, a DM peer's)
      const put=x=>{if(!x)return;if(f.fc)x.fc=f.fc;else delete x.fc;};
      if(f.pid===live.me?.pid)put(live.me);put(live.friend(f.pid));for(const c of live.chans)if(c.peer?.pid===f.pid)put(c.peer);
      break;}
    case'read':{const c=live.chan(f.ch);if(c){c.unread=0;c.read=Math.max(c.read||0,f.id);}break;}
    case'msg':{
      if(f.ch==='town')break;
      let c=live.chan(f.ch);
      if(!c&&f.ch.startsWith('dm:')){
        const other=f.ch.slice(3).split(':').find(p=>p!==live.me?.pid),fr=live.friend(other),theirs=f.pid===other;
        c={id:f.ch,kind:'dm',title:'',unread:0,read:0,peer:{pid:other,name:fr?.name||(theirs?f.name:'Bạn bè'),av:fr?.av||(theirs?f.av:'🌸'),friend:Boolean(fr),on:Boolean(fr?.on)}};
        live.chans.unshift(c);
      }
      if(!c)break;
      c.last=f;live.touch(c);
      if(f.pid!==live.me?.pid&&!live.viewing?.(f.ch))c.unread=(c.unread||0)+1;
      break;
    }
    case'deleted':{const c=live.chan(f.ch);if(c?.last?.id===f.id){if(f.hidden)delete c.last;else c.last={...c.last,text:'',del:1};}break;}
    case'hid':{const c=live.chan(f.ch);if(c?.last?.id===f.id)delete c.last;break;}   // 🗑️ deleted on my side (chat.js)
    case'cleared':   // 🗑️ chats emptied on my side: a DM leaves the list until someone writes, a group stays without its preview
      for(const [ch,upto] of Object.entries(f.chs||{})){
        const c=live.chan(ch);if(!c)continue;
        if(c.kind==='dm'&&(!c.last||c.last.id<=upto))live.chans=live.chans.filter(x=>x!==c);
        else{if(c.last&&c.last.id<=upto)delete c.last;c.unread=0;c.read=Math.max(c.read||0,upto);}
      }
      break;
    case'error':   // 🙂 the face frame was not taken (too fast, busy): send it again later
      if(f.ref==='face'&&f.code!=='bad'&&f.code!=='off'){sentFc=null;syncFaceSoon(Math.max(2,Number(f.wait)||0)*1000+500);}
      break;
  }
  emit(f.t,f);paint();
}

/* ---- the chat button (phone: on the scene, top right; wider screens: the rail entry) and its badge ---- */
/** Before the first welcome of a page with a live service: the placeholder (greyed, its tap says "đang kết nối…"). */
const waiting=()=>Boolean(env?.api?.live?.url)&&!live.welcomed&&live.state!=='off';
function paint(){
  const on=Boolean(live.flags.chat)&&live.welcomed,wait=!on&&waiting(),show=on||wait,n=on?live.unread():0;
  // Movement and heartbeat packets still reach all subscribers; unchanged chat UI does not touch the DOM.
  const key=[show,wait,live.state,n].join('|');
  if(key!==painted){
    document.documentElement.toggleAttribute?.('data-live-wait',wait);   // greys the button and the rail entry (liveBoot's rule)
    if(show&&!fab&&!cssAsked){cssAsked=true;stylesheet('/css/chat.css').then(paint);return;}   // the button's look comes with the chat's stylesheet
    if(show&&!fab){
      fab=document.createElement('button');fab.type='button';fab.className='live-fab';fab.dataset.action='liveChat';
      fab.setAttribute('aria-label','Chat');fab.innerHTML=`${icon('chats',22)}<em class="badge" hidden></em>`;
      (document.getElementById('stage')||document.body).append(fab);
    }
    if(fab){
      fab.hidden=!show;fab.classList.toggle('is-down',live.state!=='open');
      const b=fab.querySelector('.badge');b.hidden=!n;b.textContent=n>99?'99+':String(n);
      fab.setAttribute('aria-label',wait?'Chat · đang kết nối…':n?`Chat · ${n} tin chưa đọc`:'Chat');
    }
    painted=key;
  }
  // The rail / "Thêm" entry and its badge come from app.js (navItems reads liveNav()): re-render when they change.
  const total=on?n:wait?-2:-1,dating=Boolean(live.flags.dating)&&live.welcomed;
  if(show!==shown||total!==lastTotal||dating!==shownDate){shown=show;shownDate=dating;lastTotal=total;clearTimeout(renderTimer);renderTimer=setTimeout(()=>env?.renderMain?.(),250);}
}

/** For app.js navItems: the menu entry ([action, icon, label, badge]) when chat is on or still connecting, else null. */
export function liveNav(){return live.flags.chat&&live.welcomed?['liveChat','chats','Chat',live.unread()]:waiting()?['liveChat','chats','Chat',0]:null;}
/** 💕 The "Góc hẹn hò" entry when dates are on, else null. */
export function dateNav(){return live.flags.dating&&live.welcomed?['liveDate','coffee','Góc hẹn hò']:null;}

/* ---- opening the chat from a push (?chat=<id>) ---- */
let wanted=new URLSearchParams(location.search).get('chat');
if(wanted){try{history.replaceState(null,'','/');}catch{/* file:// */}}
function deepLink(){if(!wanted||!live.flags.chat)return;const ch=wanted;wanted=null;openChat({ch});}
export function openChat(data={}){
  if(!env)return;
  if(!live.welcomed){   // the placeholder: try now (once per tap, never a loop) and say so; a pushed chat opens on the welcome
    if(data.ch)wanted=data.ch;
    env.toast?.('💬 Chat đang kết nối… chờ xíu nha.','hint');live.reconnect(true);return;
  }
  import('./chat.js').then(m=>m.openChat(env,data)).catch(e=>console.warn('chat:',e));
}

/* ---- 💕 dates (./dating.js, its own dialog) ---- */
export function openDate(data={}){
  if(!env)return;
  import('./dating.js').then(m=>m.openDate(env,data)).catch(e=>console.warn('dating:',e));
}
/** Đi dạo (app.js, when the stroll opens): the bench of every place becomes the dating bench (dating.js addBench,
 * through walk.addSpot). Nothing loads while dates are off. */
export function benchSpot(walk){if(live.flags.dating&&live.welcomed&&walk&&env)return import('./dating.js').then(m=>m.addBench(env,walk)).catch(e=>console.warn('dating:',e));}

export function liveBoot(e){
  env=e;
  if(liveBoot.done)return;liveBoot.done=true;
  if(e.api?.live?.url){   // the placeholder's grey (the page's CSP allows inline styles), then the button at once
    const st=document.createElement('style');st.textContent='html[data-live-wait] [data-action="liveChat"]{opacity:.55;filter:grayscale(1)}';document.head.append(st);
    paint();
  }
  navigator.serviceWorker?.addEventListener('message',ev=>{
    if(ev.data?.type!=='open')return;
    const ch=new URL(ev.data.url,location.origin).searchParams.get('chat');
    if(ch){if(live.state==='open')openChat({ch});else wanted=ch;}
  });
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')live.reconnect();});
  e.api?.addEventListener?.('state',()=>{if(live.state==='open')syncFaceSoon();});   // 🙂 the builder, Tủ đồ, Nam/Nữ
  window.addEventListener('online',()=>live.reconnect());
  if(e.api?.live?.url)connect();   // no live service named by the game server: never a socket
}
