/** 💬 The live socket (chat, online friends; later strolling the phố and dates): one WebSocket to the live
 * service (live/ on the server, wss://<this host>/live behind nginx). Always on but tiny: it keeps the
 * welcome (switches, me, friends, chats, unread) and the chat button with its badge; the chat dialog itself
 * (./chat.js) loads on first tap.
 *
 * It opens a socket only when the game server names one (bootstrap `live.url`, env LIVE_URL=/live on the game
 * server), and nothing shows until the service says `welcome.flags.chat`. Before a first welcome ever arrives
 * (service down, nginx not routing /live) it retries slowly (1, 2, 5, 10 minutes) so the game server never sees a
 * reconnect storm; after one it reconnects with back-off (1, 2, 4, 8, 15 s, jitter), at once when the tab comes
 * back or the network returns, and resumes from the last message id it holds per open chat. Close codes from
 * the service: 1012 restart (jittered return), 4001 switched off (10 minutes), 4002 another tab took over.
 *
 * For other features: live.on(type, fn) for any server frame, live.send(frame), live.flags, live.unread(). */
import {icon} from '../icons.js';
import {stylesheet} from '../lazy.js';

const RETRY=[1,2,4,8,15],SLOW=[60,120,300,600],PING_MS=25000,DEAD_MS=60000;
const listeners=new Map();
let env=null,ws=null,attempt=0,timer=0,pinger=0,lastFrame=0,fab=null,shown=false,renderTimer=0,lastTotal=-1,cssAsked=false;

export const live={
  state:'idle',            // idle | connecting | open | down | off
  welcomed:false,          // a welcome arrived once in this page: the service exists
  flags:{},me:null,friends:[],chans:[],limits:{},
  /** Open chats ask to be resumed after a reconnect: {channel id: last message id} (set by chat.js). */
  resume:()=>({}),
  on(type,fn){if(!listeners.has(type))listeners.set(type,new Set());listeners.get(type).add(fn);return ()=>listeners.get(type)?.delete(fn);},
  send(frame){if(ws&&ws.readyState===1&&live.state==='open'){ws.send(JSON.stringify(frame));return true;}return false;},
  unread(){return live.chans.reduce((n,c)=>n+(c.unread||0),0);},
  chan(id){return live.chans.find(c=>c.id===id)||null;},
  friend(pid){return live.friends.find(f=>f.pid===pid)||null;},
  /** Bring a chat to the top of the list (a message just arrived or was sent). */
  touch(c){const i=live.chans.indexOf(c);if(i>0){live.chans.splice(i,1);live.chans.unshift(c);}},
  /** Back in sight or back online: try again now (only once the service is known to exist and is not off). */
  reconnect(){if(live.welcomed&&live.state==='down'){attempt=0;clearTimeout(timer);connect();}},
};
const emit=(type,f)=>{for(const fn of listeners.get(type)||[]){try{fn(f);}catch(e){console.warn('live:',type,e);}}for(const fn of listeners.get('*')||[]){try{fn(f);}catch(e){console.warn('live:*',e);}}};

function url(){
  const u=env?.api?.live?.url||'';
  return u.startsWith('/')?`${location.protocol==='https:'?'wss':'ws'}://${location.host}${u}`:u;
}

function connect(){
  clearTimeout(timer);
  if(typeof WebSocket!=='function'||document.visibilityState==='hidden'&&!live.welcomed)return schedule();
  live.state='connecting';
  let sock;
  try{sock=new WebSocket(url());}catch{return schedule();}
  ws=sock;
  sock.onopen=()=>{lastFrame=Date.now();const r=live.resume();sock.send(JSON.stringify({t:'hello',v:1,...(r&&Object.keys(r).length?{resume:r}:{})}));};
  sock.onmessage=e=>{lastFrame=Date.now();let f;try{f=JSON.parse(e.data);}catch{return;}if(f&&typeof f.t==='string')frame(f);};
  sock.onclose=e=>{
    if(ws!==sock)return;
    ws=null;clearInterval(pinger);
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
function schedule(secs){
  clearTimeout(timer);
  if(secs==null){const list=live.welcomed?RETRY:SLOW;secs=list[Math.min(attempt,list.length-1)]*(0.8+Math.random()*0.4);attempt++;}
  timer=setTimeout(connect,secs*1000);
}

function frame(f){
  switch(f.t){
    case'welcome':
      live.welcomed=true;live.flags=f.flags||{};
      if(!live.flags.chat&&!live.flags.street&&!live.flags.dating){live.state='off';break;}
      live.state='open';attempt=0;
      live.me=f.me||null;live.friends=f.friends||[];live.chans=f.chans||[];live.limits=f.limits||{};
      clearInterval(pinger);pinger=setInterval(()=>{if(Date.now()-lastFrame>DEAD_MS){ws?.close();return;}live.send({t:'ping'});},PING_MS);
      deepLink();
      break;
    case'state':
      if(f.friends)live.friends=f.friends;if(f.chans)live.chans=f.chans;if(f.me)live.me=f.me;
      if(live.me){if(f.town)live.me.town=f.town;if(typeof f.online==='boolean')live.me.online=f.online;}
      break;
    case'presence':{const x=live.friend(f.pid);if(x)x.on=f.on;for(const c of live.chans)if(c.peer?.pid===f.pid)c.peer.on=f.on;break;}
    case'prefs':if(live.me)live.me.online=f.online;if(!f.online){for(const x of live.friends)x.on=false;for(const c of live.chans)if(c.peer)c.peer.on=false;}break;
    case'muted':if(live.me){live.me.muted=f.until;live.me.town=f.until*1000>Date.now()?'muted':'ok';}break;
    case'chan':{const c=live.chan(f.chan.id);if(c)Object.assign(c,f.chan,{unread:c.unread,last:c.last});else live.chans.unshift(f.chan);break;}
    case'unchan':live.chans=live.chans.filter(c=>c.id!==f.ch);break;
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
  }
  emit(f.t,f);paint();
}

/* ---- the chat button (phone: on the scene, top right; wider screens: the rail entry) and its badge ---- */
function paint(){
  const on=Boolean(live.flags.chat)&&live.welcomed;
  if(on&&!fab&&!cssAsked){cssAsked=true;stylesheet('/css/chat.css').then(paint);return;}   // the button's look comes with the chat's stylesheet
  if(on&&!fab){
    fab=document.createElement('button');fab.type='button';fab.className='live-fab';fab.dataset.action='liveChat';
    fab.setAttribute('aria-label','Chat');fab.innerHTML=`${icon('chats',22)}<em class="badge" hidden></em>`;
    (document.getElementById('stage')||document.body).append(fab);
  }
  if(fab){
    fab.hidden=!on;fab.classList.toggle('is-down',live.state!=='open');
    const n=live.unread(),b=fab.querySelector('.badge');b.hidden=!n;b.textContent=n>99?'99+':String(n);
    fab.setAttribute('aria-label',n?`Chat · ${n} tin chưa đọc`:'Chat');
  }
  // The rail / "Thêm" entry and its badge come from app.js (navItems reads liveNav()): re-render when they change.
  const total=on?live.unread():-1;
  if(on!==shown||total!==lastTotal){shown=on;lastTotal=total;clearTimeout(renderTimer);renderTimer=setTimeout(()=>env?.renderMain?.(),250);}
}

/** For app.js navItems: the menu entry ([action, icon, label, badge]) when chat is on, else null. */
export function liveNav(){return live.flags.chat&&live.welcomed?['liveChat','chats','Chat',live.unread()]:null;}

/* ---- opening the chat from a push (?chat=<id>) ---- */
let wanted=new URLSearchParams(location.search).get('chat');
if(wanted){try{history.replaceState(null,'','/');}catch{/* file:// */}}
function deepLink(){if(!wanted||!live.flags.chat)return;const ch=wanted;wanted=null;openChat({ch});}
export function openChat(data={}){
  if(!env)return;
  import('./chat.js').then(m=>m.openChat(env,data)).catch(e=>console.warn('chat:',e));
}

export function liveBoot(e){
  env=e;
  if(liveBoot.done)return;liveBoot.done=true;
  navigator.serviceWorker?.addEventListener('message',ev=>{
    if(ev.data?.type!=='open')return;
    const ch=new URL(ev.data.url,location.origin).searchParams.get('chat');
    if(ch){if(live.state==='open')openChat({ch});else wanted=ch;}
  });
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')live.reconnect();});
  window.addEventListener('online',()=>live.reconnect());
  if(e.api?.live?.url)connect();   // no live service named by the game server: never a socket
}
