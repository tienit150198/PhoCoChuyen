/** 🚶 Đi dạo khu phố: online players stroll Bờ hồ, Chợ đêm, Công viên or Phố đi bộ together (live/street.py,
 * switch LIVE_STREET). Its own full-screen dialog, opened from the menu entry "Đi dạo" (app.js). Everything goes
 * through the live socket (./live.js); the server decides (walkable areas, instances, rate limits, filters,
 * blocks); this file draws: a canvas scene at 60 fps (positions interpolated from the server's paths), speech
 * bubbles, emotes, the tám chuyện tables, the happenings, a player's card and coffee for two.
 * No guide, tips or intro screen (owner, 01/10): it opens straight into the place, icons and short labels.
 * Player text is drawn as is on the canvas (never translated) and escaped in the DOM.
 *
 * Hook for other features (phase 3's dating bench lives in this scene):
 *   const {walk}=await import('./walk.js');
 *   walk.addSpot({
 *     id:'dating-bench',             // unique; addSpot again with the same id replaces it
 *     place:'*',                     // a place id (boho, chodem, congvien, phodibo, cafe) or '*' for every public place
 *     at:'bench',                    // a named spot of the place (geo.spots: every public place has a 'bench'), or {x,y}
 *     r:44,                          // tap radius in world units (the world is 600 × 900)
 *     draw(c,{x,y,t,night,place}){}, // optional: drawn on the ground, under people, world units
 *     tap({x,y,place,room}){},       // a tap on it; return false to let the player simply walk there
 *   });
 *   walk.removeSpot(id)              walk.spot('bench') → {x,y} of the current place's spot, or null
 *   walk.on('enter'|'leave',fn)      → unsubscribe; 'enter' gets {place, room, private}
 *   walk.state()                     → {open, place, room, me, people:[{pid,name,x,y,seat,said,emote}], tables, happening, envelope, view}
 *   walk.moveTo(x,y)  walk.toast(text)  walk.open(env,{place})
 *
 * 💍 Wedding parties (live/wedding.py) use the same scene: walk.open(env,{wedding:<id>}) (from the "Lịch cưới" sheet,
 * ./wedding.js) sends `wed_in`; the header shows the couple and the clock, 📸 takes the group photo (the taker's canvas
 * is uploaded to POST /api/wedding/photo for the couple's Kỷ niệm), later guests watch from outside the gate.
 * The party's show (the MC, neighbours, kids, lion dance, lights, music) is ./wedfeast.js, on the party clock.
 * At a wedding, what people said stays on the "Lời chúc" board (bubbles fade fast, the keyboard hides them), and a
 * guest can give the couple a red envelope (🧧: POST /api/marriage/envelope, then `wed_env` tells the room).
 */
import {icon,escapeHTML as esc} from '../icons.js';
import {live,openChat} from './live.js';
import {stylesheet} from '../lazy.js';
import {lookOf,figureOf,paintPlayer,CANVAS,portrait} from './look.js';
import {paintPlace,paintLion,paintVendor,paintEnvelope,EDGE,WORLD} from '../scenes/stroll.js';
import * as feast from './wedfeast.js';

const W=WORLD.w,H=WORLD.h,AV=.5,LOG_MAX=40,BUBBLE_MS=6000,EMO_MS=2600,MOVE_GAP=260,PLACE_KEY='mnl.walk.place',WSOUND_KEY='mnl.wed.sound';
const EMOTES=[['wave','👋'],['heart','❤️'],['laugh','😂'],['wow','😮'],['pray','🙏']];
const EMO=Object.fromEntries(EMOTES);
const REASONS=[['spam','Spam'],['rude','Thô tục'],['scam','Lừa đảo'],['private','Lộ thông tin'],['other','Khác']];
const MINE=new Set(['walk_places','walk_in','walk_out','move','say','emote','sit','stand','topic','card','invite','invite_reply','grab','report','block','wed_in','wed_photo']);
const S={env:null,dlg:null,cv:null,ctx:null,stage:null,room:null,geo:null,speed:170,people:new Map(),tables:[],hap:null,envl:null,
  offs:[],off:0,places:[],k:1,ox:0,oy:0,dpr:1,cw:0,ch:0,bg:null,bgKey:'',raf:0,lastDraw:0,card:null,invite:null,sent:null,
  toastTimer:0,moveAt:0,moveTimer:0,pending:null,lastPublic:null,bound:false,hideTimer:0,paused:false,floaters:[],emotes:false,
  picker:false,down:null,topicKey:'',want:null,wedding:null,wed:null,photo:null,ended:null,burst:0,clock:'',wsound:true,log:[],logOpen:false,logKey:'',envp:null};
try{S.wsound=localStorage.getItem(WSOUND_KEY)!=='0';}catch{/* storage blocked */}
const spots=new Map(),hooks={enter:new Set(),leave:new Set()};
const night=()=>document.documentElement.dataset.theme==='dem';
const nowS=()=>Date.now()/1000+S.off;
const me=()=>S.room&&S.people.get(S.room.me);
const partyS=()=>S.wed?nowS()-S.wed.at:-1e9;
/** The wedding music plays while this player is at a party that is on (and has not muted it). */
function syncMusic(){feast.music(Boolean(S.dlg?.open&&S.wed&&S.room&&!S.ended&&S.wsound&&feast.lively(partyS())),partyS);}
const emit=(k,d)=>{for(const fn of hooks[k])try{fn(d);}catch(e){console.warn('walk:',k,e);}};
const css=()=>stylesheet('/css/walk.css');

/* ---- geometry (live/street.py Geo, the same rules: rectangles, junctions) ---- */
const inside=(x,y)=>S.geo.walk.some(([x0,y0,x1,y1])=>x>=x0-.5&&x<=x1+.5&&y>=y0-.5&&y<=y1+.5);
function clamp(x,y){let best=null,bd=Infinity;for(const [x0,y0,x1,y1] of S.geo.walk){const cx=Math.min(Math.max(x,x0),x1),cy=Math.min(Math.max(y,y0),y1),d=(cx-x)**2+(cy-y)**2;if(d<bd){bd=d;best=[cx,cy];}}return best;}
function segOk(a,b){const n=Math.max(1,Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])/5));for(let i=0;i<=n;i++){const t=i/n;if(!inside(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))return false;}return true;}
function route(a,b){
  if(segOk(a,b))return [a,b];
  const J=S.geo.junctions,nodes=[a,...J,b],n=nodes.length,dist=Array(n).fill(Infinity),prev=Array(n).fill(-1),done=Array(n).fill(false);dist[0]=0;
  for(;;){let u=-1;for(let i=0;i<n;i++)if(!done[i]&&dist[i]<Infinity&&(u<0||dist[i]<dist[u]))u=i;if(u<0||u===n-1)break;done[u]=true;
    for(let v=1;v<n;v++)if(!done[v]&&segOk(nodes[u],nodes[v])){const d=dist[u]+Math.hypot(nodes[v][0]-nodes[u][0],nodes[v][1]-nodes[u][1]);if(d<dist[v]){dist[v]=d;prev[v]=u;}}}
  if(dist[n-1]===Infinity)return [a,a];
  const out=[];for(let u=n-1;u>=0;u=prev[u])out.unshift(nodes[u]);return out;
}
/** Where a path walked since t0 is at t: [x, y, moving]. */
function posAt(p,t0,t){
  let left=Math.max(0,t-t0)*S.speed;
  for(let i=0;i<p.length-1;i++){const a=p[i],b=p[i+1],seg=Math.hypot(b[0]-a[0],b[1]-a[1]);if(left<=seg&&seg>0){const k=left/seg;return [a[0]+(b[0]-a[0])*k,a[1]+(b[1]-a[1])*k,true];}left-=seg;}
  const e=p[p.length-1];return [e[0],e[1],false];
}

/* ---- the public hook ---- */
export const walk={
  addSpot(s){if(s&&s.id)spots.set(s.id,s);S.bgKey='';},
  removeSpot(id){spots.delete(id);},
  spot(name){const s=S.geo?.spots?.[name];return s?{x:s[0],y:s[1]}:null;},
  on(k,fn){hooks[k]?.add(fn);return ()=>hooks[k]?.delete(fn);},
  state(){const t=nowS();return {open:Boolean(S.dlg?.open),place:S.room?.place||null,room:S.room?.room||null,me:S.room?.me||null,
    people:[...S.people.values()].map(p=>{const [x,y]=posAt(p.p,p.at,t);return {pid:p.pid,name:p.name,x,y,seat:p.s,said:p.bub?.text||null,emote:p.emo?.e||null};}),
    tables:S.tables.map(tb=>({seats:tb.seats,topic:tb.topic})),happening:S.hap?.k||null,envelope:S.envl?{id:S.envl.id,x:S.envl.x,y:S.envl.y}:null,
    view:{k:S.k,ox:S.ox,oy:S.oy}};},
  moveTo(x,y){go(x,y);},
  toast(text){toast(text);},
  open(env,data){return openWalk(env,data);},
};

/* ---- dialog ---- */
function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet walk-sheet';d.setAttribute('aria-label','Đi dạo');
  d.innerHTML=`<div class="wk-root"><header class="wk-head"></header><div class="wk-places" hidden></div>
    <div class="wk-net" hidden>${icon('refresh',14)} Đang kết nối lại…</div>
    <div class="wk-stage"><canvas class="wk-canvas" role="img" tabindex="0"></canvas>
      <div class="wk-topic" hidden></div><div class="wk-banner" hidden></div><div class="wk-card" hidden></div><div class="wk-invite" hidden></div><div class="wk-end" hidden></div>
      <div class="wk-wishes" hidden></div><div class="wk-envp" role="dialog" aria-label="Phong bì mừng cưới" hidden></div>
      <div class="wk-toast" role="status" aria-live="polite" hidden></div></div>
    <div class="wk-emotes" hidden>${EMOTES.map(([k,e])=>`<button type="button" data-wk="emote" data-e="${k}" aria-label="${k}">${e}</button>`).join('')}</div>
    <form class="wk-say"><button type="button" class="wk-emo-btn" data-wk="emotes" aria-label="Biểu cảm" aria-expanded="false">😊</button>
      <input type="text" maxlength="120" enterkeyhint="send" autocomplete="off" aria-label="Nói" placeholder="Nói gì đó…">
      <button type="submit" class="wk-send" aria-label="Nói">${icon('send',20)}</button></form></div>`;
  document.body.append(d);
  S.stage=d.querySelector('.wk-stage');S.cv=d.querySelector('canvas');S.ctx=S.cv.getContext('2d');
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-wk]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();act(el.dataset.wk,el.dataset);
  });
  d.addEventListener('close',onClose);
  d.addEventListener('keydown',e=>{if(e.key==='Escape')e.stopPropagation();});
  d.querySelector('.wk-say').addEventListener('submit',e=>{e.preventDefault();say();});
  S.cv.addEventListener('pointerdown',e=>{S.down={x:e.clientX,y:e.clientY,t:performance.now()};});
  S.cv.addEventListener('pointerup',e=>{const d0=S.down;S.down=null;if(!d0||Math.hypot(e.clientX-d0.x,e.clientY-d0.y)>12||performance.now()-d0.t>700)return;tap(e.clientX,e.clientY);});
  S.cv.addEventListener('keydown',e=>{const k={ArrowLeft:[-50,0],ArrowRight:[50,0],ArrowUp:[0,-50],ArrowDown:[0,50]}[e.key];const m=me();if(!k||!m)return;e.preventDefault();const [x,y]=posAt(m.p,m.at,nowS());go(x+k[0],y+k[1]);});
  let sizing=0;new ResizeObserver(()=>{cancelAnimationFrame(sizing);sizing=requestAnimationFrame(size);}).observe(S.stage);   // next frame: never inside the observer's own layout pass
  S.dlg=d;return d;
}

/** The menu entry: open on the last place (or the busiest), straight into the scene. */
export async function openWalk(env,data={}){
  S.env=env;bind();await css();
  const d=dialog();
  if(!d.open){d.showModal();}
  S.paused=false;
  const wid=Number.isInteger(data.wedding)?data.wedding:null;
  if(wid===null&&S.room?.room?.startsWith('wed:'))leaveLocal();   // from a wedding back to the street
  S.wedding=wid;S.ended=null;S.want=wid!==null?'wed':data.place||null;
  head();net();paintOverlays();
  if(wid!==null){if(S.room?.room!==`wed:${wid}`)enter();loop();return;}
  live.send({t:'walk_places'});
  if(S.room&&!data.place)return;
  if(data.place)enter(data.place);
  loop();
}

function onClose(){
  if(S.room)live.send({t:'walk_out'});
  const was=S.room;leaveLocal();feast.music(false);
  cancelAnimationFrame(S.raf);S.raf=0;
  if(was)emit('leave',{place:was.place,room:was.room});
}
function leaveLocal(){S.log=[];S.logOpen=false;S.envp=null;paintLog();S.room=null;S.geo=null;S.people.clear();S.tables=[];S.hap=null;S.envl=null;S.card=null;S.invite=null;S.floaters=[];S.photo=null;syncMusic();paintOverlays();}

function enter(place){
  const st=S.env?.api?.state||{},me={look:lookOf(st),g:st.journey?.gender??null,title:st.journey?.equipped??null,titles:Array.isArray(st.journey?.worn)?st.journey.worn.map(w=>w.id):undefined};
  if(S.wedding!==null){S.want='wed';live.send({t:'wed_in',id:S.wedding,...me});return;}
  S.want=place;
  live.send({t:'walk_in',place,...me});
}

/* ---- live frames ---- */
function bind(){
  if(S.bound)return;S.bound=true;
  const open=()=>Boolean(S.dlg?.open);
  live.on('welcome',()=>{net();if(open()&&!S.paused){S.room=null;if(S.wedding!==null){if(!S.ended)enter();return;}const p=S.lastPublic||pick();if(p)enter(p);else live.send({t:'walk_places'});}});
  live.on('down',()=>net());
  live.on('walk_places',f=>{
    S.places=f.places||[];head();
    if(open()&&!S.room&&!S.paused&&!S.want&&S.wedding===null)enter(pick());
  });
  live.on('walk_room',f=>{
    if(!open()){live.send({t:'walk_out'});return;}
    sample(f.at);
    const before=S.room;
    S.room=f;S.geo=f.geo;S.speed=f.speed||170;S.want=null;S.card=null;S.invite=null;S.sent=null;S.floaters=[];
    S.people=new Map(f.people.map(p=>[p.pid,person(p)]));
    S.tables=f.tables;S.hap=f.hap;S.envl=f.env;S.bgKey='';
    S.wed=f.wed||null;S.wedding=f.wed?f.wed.id:null;S.photo=null;if(f.wed)S.ended=null;
    if(!f.private){S.lastPublic=f.place;try{localStorage.setItem(PLACE_KEY,f.place);}catch{/* storage blocked */}}
    S.places=S.places.map(p=>p.id===f.place?{...p,n:f.people.length}:p);
    head();paintOverlays();size();loop();syncMusic();
    if(before&&before.room!==f.room)emit('leave',{place:before.place,room:before.room});
    emit('enter',{place:f.place,room:f.room,private:f.private});
  });
  live.on('walk',f=>{
    if(!S.room)return;sample(f.at);
    let seats=false;
    for(const e of f.ev){
      if(e.k==='mv'){const p=S.people.get(e.pid);if(!p)continue;
        if(p.pid===S.room.me&&p.pred&&Math.hypot(e.p.at(-1)[0]-p.pred[0],e.p.at(-1)[1]-p.pred[1])<1.5)continue;   // my own move, already walking
        p.p=e.p;p.at=e.at;p.pred=null;}
      else if(e.k==='in'){if(!S.people.has(e.pid))S.people.set(e.pid,person(e));}
      else if(e.k==='out'){S.people.delete(e.pid);if(S.card?.pid===e.pid)S.card=null;if(S.invite?.pid===e.pid)S.invite=null;seats=true;}
      else if(e.k==='tb'){S.tables[e.i]=Object.assign(S.tables[e.i]||{},e);seats=true;}
    }
    for(const p of S.people.values())p.s=null;
    S.tables.forEach((t,i)=>t.seats?.forEach((pid,k)=>{const p=pid&&S.people.get(pid);if(p)p.s=[i,k];}));
    if(seats)paintOverlays();head(true);
  });
  live.on('said',f=>{const p=S.room&&f.ch===S.room.room&&S.people.get(f.pid);if(!p)return;p.bub={text:f.text,id:f.id,t0:performance.now()};p.said={id:f.id,text:f.text};
    if(S.wedding!==null)logAdd({id:f.id,name:p.name,text:f.text});});
  live.on('deleted',f=>{if(!S.room||f.ch!==S.room.room)return;for(const p of S.people.values()){if(p.bub?.id===f.id)p.bub=null;if(p.said?.id===f.id)p.said=null;}
    const n=S.log.length;S.log=S.log.filter(l=>l.id!==f.id);if(S.log.length!==n)paintLog();});
  live.on('emoted',f=>{const p=S.people.get(f.pid);if(p)p.emo={e:EMO[f.e]||'👋',t0:performance.now()};});
  live.on('happen',f=>{if(!S.room)return;sample(f.at);S.hap={...f,end:f.at+f.dur};if(f.k==='env')S.envl={id:f.id,x:f.x,y:f.y,until:f.until};});
  live.on('happen_end',f=>{
    if(S.envl?.id===f.id)S.envl=null;if(S.hap?.id===f.id)S.hap=null;
    const p=f.pid&&S.people.get(f.pid);if(p)S.floaters.push({pid:f.pid,text:`🧧 +${f.n}`,t0:performance.now()});
  });
  live.on('grabbed',f=>{toast(`🧧 +${f.n} xu vào ví`);payNow();});
  live.on('card',f=>{if(S.card?.pid===f.pid){S.card={...S.card,...f,loading:false};paintOverlays();}});
  live.on('invited',f=>{if(!open())return;S.invite={...f,t0:Date.now()};paintOverlays();});
  live.on('invite_sent',f=>{S.sent=f;toast('☕ Đã rủ, chờ bạn ấy nhé…');});
  live.on('invite_no',()=>{S.sent=null;toast('Bạn ấy bận rồi, lần sau nhé!');});
  live.on('walk_left',f=>{
    if(f.why==='other'&&open()){leaveLocal();S.paused=true;head();toast('Bạn đang dạo ở một tab khác.');}
    if(f.why==='wed_end'&&open()&&S.wed){S.ended=S.ended||{n:null};leaveLocal();head();paintOverlays();}
  });
  live.on('wed_start',f=>{if(S.wed?.id!==f.id)return;S.burst=performance.now();toast('🎊 Lễ cưới bắt đầu!');});
  live.on('wed_end',f=>{if(S.wed?.id!==f.id)return;S.ended={n:f.n};syncMusic();head();paintOverlays();});
  live.on('wed_xu',f=>{
    if(f.why==='account'){toast('Tạo tài khoản để nhận lộc cưới mỗi phút nhé!');return;}
    if(f.why==='cap'){toast('Hôm nay bạn đã nhận lộc ở 2 đám cưới rồi. Vẫn được tính là khách nha 💛');return;}
    const m=me();if(m)S.floaters.push({pid:m.pid,text:`+${f.n} xu`,t0:performance.now()});
    if(S.wed)S.wed.mins=f.k;payNow();});
  live.on('wed_paid',()=>payNow());
  live.on('wed_env',f=>{if(S.wed?.id!==f.id)return;   // 🧧 a guest gave the couple a red envelope
    logAdd({env:f.n,name:f.name,text:f.text});
    S.floaters.push({pid:f.pid,text:`🧧 ${f.n} xu`,t0:performance.now()});
    if(S.wed.pids?.includes(S.room?.me)){toast(`🧧 ${f.name} mừng ${f.n} xu`);payNow();}});
  live.on('wed_photo',f=>{if(S.wed?.id!==f.id)return;S.photo={...f,taken:false};S.wed.photos=f.n;head();});
  live.on('reported',()=>{if(open())toast('Đã báo cáo, cảm ơn bạn.');});
  live.on('error',f=>{
    if(!open()||!MINE.has(f.ref))return;
    if(f.code==='slow'&&(f.ref==='move'||f.ref==='walk_places'))return;
    if(f.code==='not_in'){if(S.lastPublic)enter(S.lastPublic);return;}
    if(f.ref==='walk_in')S.want=null;
    toast(f.msg||'Có lỗi, thử lại nhé.');
  });
}
function sample(at){if(typeof at!=='number')return;S.offs.push(at-Date.now()/1000);if(S.offs.length>12)S.offs.shift();S.off=Math.max(...S.offs);}
function person(p){return {pid:p.pid,name:p.name,ti:p.ti,lk:p.lk,g:p.g,p:p.p,at:p.at,s:p.s,sp:null,spk:'',bub:null,emo:null,said:null,pred:null};}
function pick(){
  let saved=null;try{saved=localStorage.getItem(PLACE_KEY);}catch{/* storage blocked */}
  if(S.places.some(p=>p.id===saved))return saved;
  const busy=[...S.places].sort((a,b)=>b.n-a.n)[0];return busy?.n?busy.id:'boho';
}
async function payNow(){
  const api=S.env?.api;if(!api)return;
  try{const d=await api.json('/api/live/effects',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:'{}'});
    if(d?.paid&&d.state&&typeof d.revision==='number'){api.accept({state:d.state,revision:d.revision});S.env.renderMain?.();}
    if(d?.gifts?.length){api.gifts=d.gifts;import('./gift.js').then(m=>m.giftBoot(S.env)).catch(e=>console.warn('walk: gift',e));}}   // the private card (a party's total, the race)
  catch(e){console.warn('walk: pay',e);}
}
const VN=new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',hour12:false});
export const wedDate=at=>{const p=Object.fromEntries(VN.formatToParts(new Date(at*1000)).map(x=>[x.type,x.value]));return `${p.day}/${p.month}/${p.year} · ${p.hour}:${p.minute}`;};
const mmss=s=>{s=Math.max(0,Math.round(s));const h=Math.floor(s/3600),m=Math.floor(s%3600/60),x=s%60;return h?`${h}:${String(m).padStart(2,'0')}:${String(x).padStart(2,'0')}`:`${m}:${String(x).padStart(2,'0')}`;};
function wedClock(){const w=S.wed;if(!w)return '';const t=nowS();return S.ended?'Tiệc đã tàn':t<w.at?`⏳ ${mmss(w.at-t)}`:`🎊 ${mmss(w.end-t)}`;}
/** The group photo: a 3:2 frame around everyone (as this player sees them: avatars, name tags, bubbles) with the
 * couple's names on a band, small enough for the 64 KB upload (webp, else jpeg). Kỷ niệm shows it as a polaroid. */
function frameOf(){
  const pts=[...S.people.values()].filter(p=>typeof p.x==='number');
  let x0=Math.min(...pts.map(p=>p.x))-70,x1=Math.max(...pts.map(p=>p.x))+70,y0=Math.min(...pts.map(p=>p.y))-130,y1=Math.max(...pts.map(p=>p.y))+30;
  if(!pts.length)[x0,x1,y0,y1]=[0,W,150,550];
  let w=Math.max(360,x1-x0,(y1-y0)*1.5),h=w/1.5;w=Math.min(w,W*1.4);h=w/1.5;
  const cx=(x0+x1)/2,cy=(y0+y1)/2;return [cx-w/2,cy-h/2,w,h];
}
async function capture(n){
  const w=S.wed,api=S.env?.api;if(!w||!api||!S.cv)return;
  const [fx,fy,fw,fh]=frameOf(),d=S.dpr,sx=(S.ox+fx*S.k)*d,sy=(S.oy+fy*S.k)*d;let data='';
  for(const ow of [480,360,300]){
    const oh=Math.round(ow/1.5),out=document.createElement('canvas');out.width=ow;out.height=oh;
    const c=out.getContext('2d');c.fillStyle=night()?'#1d1c26':'#efe6d6';c.fillRect(0,0,ow,oh);c.drawImage(S.cv,sx,sy,fw*S.k*d,fh*S.k*d,0,0,ow,oh);
    c.fillStyle='rgba(255,253,248,.88)';c.fillRect(0,oh-40,ow,40);c.textAlign='center';c.textBaseline='middle';
    c.fillStyle='#b8432c';c.font=`700 ${Math.round(ow/28)}px "Trebuchet MS",sans-serif`;c.fillText(`💍 ${w.a} & ${w.b} · ${wedDate(w.at)}`,ow/2,oh-20);
    for(let q=.8;q>=.35;q-=.15){data=out.toDataURL('image/webp',q);if(!data.startsWith('data:image/webp'))data=out.toDataURL('image/jpeg',q);if(data.length*.75<=44*1024)break;}
    if(data.length*.75<=44*1024)break;
  }
  try{await api.json('/api/wedding/photo',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify({wedding:w.id,n,image:data})});
    toast('📸 Đã lưu vào Kỷ niệm của cô dâu chú rể');}
  catch(e){toast(e?.message||'Chưa lưu được ảnh.');}
}

/* ---- actions ---- */
function act(a,d){
  switch(a){
    case'close':S.dlg.close();return;
    case'photo':live.send({t:'wed_photo'});return;
    case'env':S.envp=S.envp?null:{amount:(S.wed?.envs||[20])[1]??20,wish:0,busy:false};paintEnvp();return;
    case'envAmt':if(S.envp){S.envp.amount=Number(d.n);paintEnvp();}return;
    case'envWish':if(S.envp){S.envp.wish=Number(d.n);paintEnvp();}return;
    case'envSend':sendEnvelope();return;
    case'log':S.logOpen=!S.logOpen;paintLog();return;
    case'wsound':S.wsound=!S.wsound;try{localStorage.setItem(WSOUND_KEY,S.wsound?'1':'0');}catch{/* storage blocked */}syncMusic();head();return;
    case'account':S.dlg.close();S.env?.act?.('v4AccountOpen',{mode:'register'});return;   // v4/account.js
    case'places':S.picker=!S.picker;if(S.picker)live.send({t:'walk_places'});head();return;
    case'go':S.picker=false;head();if(d.place!==S.room?.place)enter(d.place);return;
    case'back':if(S.lastPublic)enter(S.lastPublic);return;
    case'emotes':S.emotes=!S.emotes;S.dlg.querySelector('.wk-emotes').hidden=!S.emotes;S.dlg.querySelector('.wk-emo-btn').setAttribute('aria-expanded',String(S.emotes));return;
    case'emote':live.send({t:'emote',e:d.e});S.emotes=false;S.dlg.querySelector('.wk-emotes').hidden=true;return;
    case'topic':live.send({t:'topic'});return;
    case'stand':live.send({t:'stand'});return;
    case'cardClose':S.card=null;break;
    case'friend':friend();return;
    case'dm':{const pid=S.card?.pid;if(!pid)return;const [x,y]=[live.me?.pid,pid].sort();S.card=null;paintOverlays();openChat({ch:`dm:${x}:${y}`});return;}
    case'cafe':if(S.card){live.send({t:'invite',pid:S.card.pid});S.card=null;}break;
    case'more':if(S.card)S.card.more=!S.card.more;break;
    case'report':if(S.card)S.card.report=true;break;
    case'reason':if(S.card?.said){live.send({t:'report',id:S.card.said.id,reason:d.reason});S.card=null;}break;
    case'block':if(S.card){live.send({t:'block',pid:S.card.pid});S.people.delete(S.card.pid);toast('Đã chặn. Hai bạn sẽ không thấy nhau nữa.');S.card=null;}break;
    case'inviteYes':if(S.invite){live.send({t:'invite_reply',id:S.invite.id,ok:true});S.invite=null;}break;
    case'inviteNo':if(S.invite){live.send({t:'invite_reply',id:S.invite.id,ok:false});S.invite=null;}break;
  }
  paintOverlays();
}
async function friend(){
  const c=S.card,api=S.env?.api;if(!c||!api)return;
  if(!live.me?.account){toast('Tạo tài khoản để kết bạn nhé.');return;}
  if(!c.code){toast('Bạn ấy chưa có tài khoản để kết bạn.');return;}
  c.busy=true;paintOverlays();
  try{const d=await api.json('/api/marriage/friend_request',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify({code:c.code})});
    toast(d?.message||'Đã gửi lời mời kết bạn.');if(S.card===c){c.sentFriend=true;}}
  catch(e){toast(e?.message||'Chưa gửi được, thử lại nhé.');}
  finally{c.busy=false;paintOverlays();}
}
function say(){
  const input=S.dlg.querySelector('.wk-say input'),text=input.value.trim();
  if(!text||!S.room)return;
  if(live.send({t:'say',text}))input.value='';
}
/** Walk to (x,y): drawn at once (the same route as the server), sent at most every MOVE_GAP ms. */
function go(x,y){
  const m=me();if(!m||!S.geo)return;
  const t=nowS(),[cx,cy]=posAt(m.p,m.at,t),target=clamp(x,y);
  m.p=route([cx,cy],target);m.at=t;m.pred=target;
  S.pending=target;
  const wait=S.moveAt+MOVE_GAP-performance.now();
  clearTimeout(S.moveTimer);
  const send=()=>{if(!S.pending)return;live.send({t:'move',x:Math.round(S.pending[0]*10)/10,y:Math.round(S.pending[1]*10)/10});S.pending=null;S.moveAt=performance.now();};
  if(wait<=0)send();else S.moveTimer=setTimeout(send,wait);
}
function tap(cx,cy){
  if(!S.room||!S.geo)return;
  const r=S.cv.getBoundingClientRect(),x=(cx-r.left-S.ox)/S.k,y=(cy-r.top-S.oy)/S.k,t=nowS();
  if(S.card||S.picker){S.card=null;S.picker=false;head();paintOverlays();}
  if(S.envl&&Math.hypot(x-S.envl.x,y-S.envl.y)<42){live.send({t:'grab',id:S.envl.id});return;}
  for(const s of spots.values()){const at=spotAt(s);if(at&&Math.hypot(x-at[0],y-at[1])<(s.r||40)){try{if(s.tap?.({x:at[0],y:at[1],place:S.room.place,room:S.room.room})!==false)return;}catch(e){console.warn('walk spot:',e);}}}
  let hit=null,hd=Infinity;
  for(const p of S.people.values()){if(p.pid===S.room.me)continue;const [px,py]=posAt(p.p,p.at,t);if(Math.abs(x-px)<28&&y>py-72&&y<py+8){const d=Math.hypot(x-px,y-(py-30));if(d<hd){hd=d;hit=p;}}}
  if(hit){S.card={pid:hit.pid,name:hit.name,ti:hit.ti,lk:hit.lk,g:hit.g,said:hit.said,loading:true};live.send({t:'card',pid:hit.pid});paintOverlays();return;}
  const ti=(S.geo.tables||[]).findIndex(tb=>Math.hypot(x-tb.x,y-tb.y)<44);
  if(ti>=0){live.send({t:'sit',table:ti});return;}
  go(x,y);
}
function spotAt(s){
  if(!S.room||(s.place!=='*'&&s.place!==S.room.place)||(s.place==='*'&&S.room.private))return null;
  if(typeof s.at==='string'){const p=S.geo.spots?.[s.at];return p?[p[0],p[1]]:null;}
  return s.at&&typeof s.at.x==='number'?[s.at.x,s.at.y]:null;
}

/* ---- the DOM bits: header, places, topic card, player card, invite, toast ---- */
function count(){return S.room?S.people.size:0;}
function head(light=false){
  if(!S.dlg)return;
  const h=S.dlg.querySelector('.wk-head'),r=S.room;
  const n=count(),label=r?`${r.icon} ${r.name}`:'🚶 Đi dạo';
  if(light&&h.dataset.n===String(n)&&h.dataset.room===(r?.room||''))return;
  h.dataset.n=String(n);h.dataset.room=r?.room||'';
  h.classList.toggle('wk-head-wed',S.wedding!==null);
  if(S.wedding!==null){   // 💍 the couple, the clock, the photo
    const w=S.wed,photo=w&&!w.overflow&&!S.ended&&r&&w.photos<w.photos_max;
    h.innerHTML=`<div class="wk-where wk-wed"><b data-no-translate>${esc(w?`💍 ${w.a} & ${w.b}`:'💍 Đám cưới')}</b>${r?`<small class="wk-n" aria-label="${n} khách">${n}</small>`:''}</div>
      <span class="wk-clock" aria-live="off">${wedClock()}</span>${w&&!S.ended&&w.overflow!=='account'?`<span class="wk-lucky" title="Lộc cưới">💰 ${w.xu||20} xu/phút</span>`:''}<span class="grow"></span>
      ${canGive()?`<button type="button" class="icon-btn wk-env-btn" data-wk="env" aria-label="Mừng phong bì cô dâu chú rể" aria-expanded="${Boolean(S.envp)}">🧧</button>`:''}
      ${r&&!S.ended?`<button type="button" class="icon-btn" data-wk="wsound" aria-label="${S.wsound?'Tắt nhạc cưới':'Bật nhạc cưới'}" aria-pressed="${S.wsound}">${S.wsound?'🔊':'🔇'}</button>`:''}
      ${photo?`<button type="button" class="icon-btn wk-photo-btn" data-wk="photo" aria-label="Chụp ảnh chung">📸</button>`:''}
      <button type="button" class="icon-btn" data-wk="close" aria-label="Đóng">${icon('x',20)}</button>`;
    S.dlg.querySelector('.wk-places').hidden=true;S.picker=false;
    S.dlg.querySelector('.wk-say').hidden=Boolean(w?.overflow||S.ended);
    if(S.cv)S.cv.setAttribute('aria-label',w?`Đám cưới ${w.a} và ${w.b}: ${n} khách`:'Đám cưới');
    return;
  }
  S.dlg.querySelector('.wk-say').hidden=false;
  h.innerHTML=(r?.private
    ?`<button type="button" class="wk-where" data-wk="back">${icon('back',16)}<b>${esc(label)}</b></button>`
    :`<button type="button" class="wk-where" data-wk="places" aria-expanded="${S.picker}"><b>${esc(label)}</b>${r?`<small class="wk-n" aria-label="${n} người ở đây">${n}</small>`:''}${icon('chevron',14,'wk-chev')}</button>`)+
    `<span class="grow"></span><button type="button" class="icon-btn" data-wk="close" aria-label="Đóng">${icon('x',20)}</button>`;
  const pl=S.dlg.querySelector('.wk-places');pl.hidden=!S.picker;
  if(S.picker)pl.innerHTML=S.places.map(p=>`<button type="button" class="wk-chip${p.id===r?.place?' on':''}" data-wk="go" data-place="${esc(p.id)}"><span>${p.icon}</span><b>${esc(p.name)}</b><small>${p.n}</small></button>`).join('');
  if(S.cv)S.cv.setAttribute('aria-label',r?`${r.name}: ${n} người đang dạo`:'Đi dạo');
}
/** 🧧 A guest with an account at a party that is on (the couple get the envelopes, they do not give them). */
function canGive(){const w=S.wed,r=S.room;return Boolean(w&&r&&!S.ended&&w.envs&&w.overflow!=='account'&&live.me?.account&&!w.pids?.includes(r.me));}
/** The wishes board: what was said at the party, newest last (3 lines; tap to see the last 40). */
function logAdd(l){S.log.push(l);if(S.log.length>LOG_MAX)S.log.splice(0,S.log.length-LOG_MAX);paintLog();}
function paintLog(){
  const el=S.dlg?.querySelector('.wk-wishes');if(!el)return;
  if(S.wedding===null||!S.log.length||S.ended){el.hidden=true;S.logKey='';return;}
  const key=`${S.logOpen}|${S.log.length}|${S.log.map(l=>l.id??l.name+l.env).join(',')}`;
  if(key===S.logKey&&!el.hidden)return;   // unchanged: keep where the reader scrolled
  S.logKey=key;
  const rows=(S.logOpen?S.log:S.log.slice(-3)).map(l=>`<p class="${l.env?'wk-wish env':'wk-wish'}"><b data-no-translate>${esc(l.name||'Khách')}</b> ${l.env?`🧧 mừng ${l.env} xu${l.text?`: ${esc(l.text)}`:''}`:`<span data-no-translate>${esc(l.text)}</span>`}</p>`).join('');
  el.classList.toggle('open',S.logOpen);
  el.innerHTML=`<button type="button" class="wk-wish-head" data-wk="log" aria-expanded="${S.logOpen}">📜 Lời chúc <small>${S.log.length}</small><span>${S.logOpen?'Thu gọn':'Xem hết'}</span></button><div class="wk-wish-list">${rows}</div>`;
  el.hidden=false;
  const list=el.querySelector('.wk-wish-list');list.scrollTop=list.scrollHeight;
}
function paintEnvp(){
  const el=S.dlg?.querySelector('.wk-envp');if(!el)return;const e=S.envp,w=S.wed;
  const b=S.dlg.querySelector('.wk-env-btn');if(b)b.setAttribute('aria-expanded',String(Boolean(e)));
  if(!e||!w||!canGive()){el.hidden=true;return;}
  el.innerHTML=`<div class="wk-who"><span class="wk-env-ico" aria-hidden="true">🧧</span><p class="grow"><b>Mừng cô dâu chú rể</b><small>Chia đôi cho <span data-no-translate>${esc(w.a)}</span> và <span data-no-translate>${esc(w.b)}</span> · tối đa ${w.env_max} xu mỗi đám</small></p>
      <button type="button" class="icon-btn" data-wk="env" aria-label="Đóng">${icon('x',18)}</button></div>
    <div class="wk-acts wrap">${w.envs.map(n=>`<button type="button" class="wk-pill${n===e.amount?' primary':''}" data-wk="envAmt" data-n="${n}" aria-pressed="${n===e.amount}">${n} xu</button>`).join('')}</div>
    <div class="wk-acts wrap">${w.wishes.map((t,i)=>`<button type="button" class="wk-pill${i===e.wish?' on':''}" data-wk="envWish" data-n="${i}" aria-pressed="${i===e.wish}">${esc(t)}</button>`).join('')}</div>
    <div class="wk-acts"><button type="button" class="wk-pill primary wk-env-go" data-wk="envSend"${e.busy?' disabled':''}>🧧 Gửi phong bì ${e.amount} xu</button></div>`;
  el.hidden=false;
}
async function sendEnvelope(){
  const e=S.envp,w=S.wed,api=S.env?.api;if(!e||!w||!api||e.busy)return;
  e.busy=true;e.rid=e.rid||`e${Date.now().toString(36)}${Math.random().toString(36).slice(2,10)}`;paintEnvp();
  try{const d=await api.json('/api/marriage/envelope',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify({wedding:w.id,amount:e.amount,wish:e.wish,rid:e.rid})});
    if(d?.state&&typeof d.revision==='number'){api.accept({state:d.state,revision:d.revision});S.env.renderMain?.();}
    if(d?.rid)live.send({t:'wed_env',rid:d.rid});
    S.envp=null;toast(d?.message||'Đã gửi phong bì 🧧');}
  catch(x){e.busy=false;e.rid=null;toast(x?.message||'Chưa gửi được, thử lại nhé.');}
  paintEnvp();
}
function net(){if(!S.dlg)return;S.dlg.querySelector('.wk-net').hidden=live.state==='open';}
function mySeat(){const m=me();return m?.s?S.tables[m.s[0]]:null;}
function paintOverlays(){
  if(!S.dlg)return;
  const bn=S.dlg.querySelector('.wk-banner');bn.hidden=!(S.wed?.overflow&&!S.ended);
  if(!bn.hidden)bn.innerHTML=S.wed.overflow==='account'   // guests watch; accounts take part and count (owner, 1.0.1)
    ?`Bạn đang xem từ ngoài cổng. <button type="button" class="wk-pill primary" data-wk="account">Tạo tài khoản</button> để vào dự và nhận lộc mỗi phút.`
    :'Đông quá! Bạn đứng ngoài cổng xem, vẫn được tính là khách 🎉';
  const en=S.dlg.querySelector('.wk-end');en.hidden=!S.ended;
  paintLog();paintEnvp();
  if(S.ended)en.innerHTML=`<p class="wk-end-t">💍 Tiệc đã tàn</p>${S.ended.n!=null?`<p>${S.ended.n} khách đến chung vui 💛</p>`:''}<button type="button" class="wk-pill primary" data-wk="close">Đóng</button>`;
  const tp=S.dlg.querySelector('.wk-topic'),tb=mySeat();
  if(tb&&tb.topic){
    const n=(tb.seats||[]).filter(Boolean).length,key=`${tb.topic}|${tb.votes}|${n}`;
    if(tp.hidden||S.topicKey!==key){S.topicKey=key;
      tp.innerHTML=`<p class="wk-topic-q">${esc(tb.topic)}</p><div class="wk-topic-acts"><button type="button" class="wk-pill" data-wk="topic">${icon('refresh',14)} Đổi chủ đề${tb.votes?` <em>${tb.votes}/${n}</em>`:''}</button>
        <button type="button" class="wk-pill" data-wk="stand">Đứng dậy</button></div><i class="wk-time"></i>`;}
    tp.hidden=false;
  }else{tp.hidden=true;S.topicKey='';}
  const cd=S.dlg.querySelector('.wk-card'),c=S.card;
  if(c){
    const acts=[];
    if(!c.loading){
      if(c.friend)acts.push(`<button type="button" class="wk-pill" data-wk="dm">${icon('chat',15)} Nhắn riêng</button>`);
      else if(c.account)acts.push(`<button type="button" class="wk-pill" data-wk="friend"${c.busy||c.sentFriend?' disabled':''}>${icon('user',15)} ${c.sentFriend?'Đã mời':'Kết bạn'}</button>`);
      if(c.cafe)acts.push(`<button type="button" class="wk-pill" data-wk="cafe">${icon('coffee',15)} Rủ đi cà phê</button>`);
      acts.push(`<button type="button" class="wk-pill wk-more" data-wk="more" aria-label="Thêm" aria-expanded="${Boolean(c.more)}">⋯</button>`);
    }
    const more=c.more?(c.report?`<div class="wk-acts wrap">${REASONS.map(([k,l])=>`<button type="button" class="wk-pill" data-wk="reason" data-reason="${k}">${l}</button>`).join('')}</div>`
      :`<div class="wk-acts">${c.said?`<button type="button" class="wk-pill" data-wk="report">${icon('flag',14)} Báo cáo lời vừa nói</button>`:''}<button type="button" class="wk-pill warn" data-wk="block">Chặn</button></div>`):'';
    cd.innerHTML=`<div class="wk-who">${portrait(c.lk,c.g,48,c.name)}<div class="grow"><b data-no-translate>${esc(c.name)}</b>${c.ti?`<small>${esc(c.ti)}</small>`:''}${c.friend?'<small class="wk-friend">Bạn bè</small>':''}</div>
      <button type="button" class="icon-btn" data-wk="cardClose" aria-label="Đóng">${icon('x',18)}</button></div>${c.said&&c.more&&c.report?`<p class="wk-said" data-no-translate>“${esc(c.said.text)}”</p>`:''}
      <div class="wk-acts">${acts.join('')}</div>${more}`;
    cd.hidden=false;
  }else cd.hidden=true;
  const iv=S.dlg.querySelector('.wk-invite'),i=S.invite;
  if(i){iv.innerHTML=`<div class="wk-who">${portrait(i.lk,i.g,40,i.name)}<p class="grow"><b data-no-translate>${esc(i.name)}</b> rủ bạn đi cà phê ☕</p></div>
      <div class="wk-acts"><button type="button" class="wk-pill primary" data-wk="inviteYes">Đi</button><button type="button" class="wk-pill" data-wk="inviteNo">Để sau</button></div>
      <i class="wk-bar" style="animation-duration:${Math.max(1,(i.ttl||30)-(Date.now()-i.t0)/1000)}s"></i>`;iv.hidden=false;}
  else iv.hidden=true;
}
function toast(text){
  if(!S.dlg)return;const el=S.dlg.querySelector('.wk-toast');el.textContent=text;el.hidden=false;
  clearTimeout(S.toastTimer);S.toastTimer=setTimeout(()=>{el.hidden=true;},2800);
}

/* ---- canvas ---- */
function size(){
  if(!S.stage||!S.cv)return;
  const w=S.stage.clientWidth,h=S.stage.clientHeight;if(!w||!h)return;
  S.dpr=Math.min(2,window.devicePixelRatio||1);S.cw=w;S.ch=h;
  const cw=Math.round(w*S.dpr),chh=Math.round(h*S.dpr);if(S.cv.width!==cw||S.cv.height!==chh){S.cv.width=cw;S.cv.height=chh;}
  S.k=Math.min(w/W,h/H);S.ox=(w-W*S.k)/2;S.oy=(h-H*S.k)/2;S.bgKey='';
}
function background(){
  const key=`${S.room.place}|${S.cw}x${S.ch}|${S.dpr}|${night()}`;
  if(S.bgKey===key&&S.bg)return S.bg;
  const cv=S.bg||document.createElement('canvas');cv.width=S.cv.width;cv.height=S.cv.height;
  const c=cv.getContext('2d');c.setTransform(1,0,0,1,0,0);c.fillStyle=EDGE[S.room.place]||'#e8dcc6';c.fillRect(0,0,cv.width,cv.height);
  c.setTransform(S.dpr*S.k,0,0,S.dpr*S.k,S.dpr*S.ox,S.dpr*S.oy);
  paintPlace(c,S.room.place,S.geo,night());
  S.bg=cv;S.bgKey=key;return cv;
}
function sprite(p){
  const key=`${S.k}|${S.dpr}`;if(p.sp&&p.spk===key)return p.sp;
  const s=AV*S.k*S.dpr,cv=document.createElement('canvas');cv.width=Math.ceil(110*s);cv.height=Math.ceil(160*s);
  const c=cv.getContext('2d');c.setTransform(s,0,0,s,55*s,150*s);
  try{paintPlayer(c,figureOf(p.lk,p.g),CANVAS);}catch(e){console.warn('walk: look',e);}
  p.sp=cv;p.spk=key;return cv;
}
const npcs=new Map();   // the wedding show's characters (./wedfeast.js), cached like the players' sprites
function npcSprite(id,lk,g){let p=npcs.get(id);if(!p||p.lk!==lk){p={lk,g,sp:null,spk:''};npcs.set(id,p);}return sprite(p);}
function loop(){if(!S.raf&&S.dlg?.open)S.raf=requestAnimationFrame(frame);}
function frame(ts){
  S.raf=0;if(!S.dlg?.open)return;
  if(document.visibilityState!=='visible'){S.raf=requestAnimationFrame(frame);return;}
  const t=nowS(),busy=!S.room||[...S.people.values()].some(p=>p.bub||p.emo||posAt(p.p,p.at,t)[2])||S.hap||S.envl||S.floaters.length||spots.size;
  const show=S.wed&&!S.ended&&feast.lively(t-S.wed.at);   // the party's lights and dancers: ~25 fps is plenty
  if(busy||(show&&ts-S.lastDraw>38)||ts-S.lastDraw>120){S.lastDraw=ts;draw(ts,t);}
  S.raf=requestAnimationFrame(frame);
}
function draw(ts,t){
  const c=S.ctx,dpr=S.dpr;if(!c||!S.cw)return;
  c.setTransform(1,0,0,1,0,0);
  if(!S.room||!S.geo){c.fillStyle=night()?'#1d1c26':'#efe6d6';c.fillRect(0,0,S.cv.width,S.cv.height);return;}
  c.drawImage(background(),0,0);
  c.setTransform(dpr*S.k,0,0,dpr*S.k,dpr*S.ox,dpr*S.oy);
  const sec=ts/1000,dark=night();
  for(const s of spots.values()){const at=spotAt(s);if(at&&s.draw)try{s.draw(c,{x:at[0],y:at[1],t:sec,night:dark,place:S.room.place});}catch(e){console.warn('walk spot:',e);}}
  if(S.envl){const left=(S.envl.until-t)/45;if(left<=0)S.envl=null;else paintEnvelope(c,S.envl.x,S.envl.y,sec,left);}
  const fx=S.wed&&!S.ended?{w:S.wed,s:t-S.wed.at,sec,dark,sprite:npcSprite,av:AV}:null;
  if(fx)feast.ground(c,fx);
  const myPid=S.room.me,list=[];
  for(const p of S.people.values()){const [x,y,moving]=posAt(p.p,p.at,t);p.x=x;p.y=y;p.moving=moving;list.push(p);}
  list.sort((a,b)=>a.y-b.y);
  for(const p of list){
    if(p.pid===myPid){c.fillStyle=dark?'rgba(255,170,130,.38)':'rgba(196,75,48,.25)';c.beginPath();c.ellipse(p.x,p.y+2,22,8,0,0,Math.PI*2);c.fill();}
    const bob=p.moving?-Math.abs(Math.sin(sec*11+p.x*.05))*3:0,sp=sprite(p);
    c.drawImage(sp,p.x-55*AV,p.y-150*AV+bob,110*AV,160*AV);
  }
  const h=S.hap;
  if(h&&h.k!=='env'){const span=h.end-h.at,f=(t-h.at)/span;
    if(f>1)S.hap=null;else if(f>=0){const x=h.rtl?W+90-(W+180)*f:-90+(W+180)*f;
      if(h.k==='lion')paintLion(c,x,h.y,sec,h.rtl);else paintVendor(c,x,h.y,h.who,sec);}}
  if(fx)feast.over(c,fx);
  c.setTransform(dpr,0,0,dpr,0,0);
  const now=performance.now(),k=S.k,sx=x=>S.ox+x*k,sy=y=>S.oy+y*k;
  if(fx)feast.talk(c,{...fx,sx,sy,tag,bubble});
  for(const p of list){
    const top=sy(p.y-132*AV)-4;
    tag(c,sx(p.x),top,p.name,p.ti,p.pid===myPid,dark);
    let above=top-(p.ti?30:20);
    if(p.bub){const age=now-p.bub.t0;if(age>BUBBLE_MS)p.bub=null;else above=bubble(c,sx(p.x),above,p.bub.text,age>BUBBLE_MS-500?(BUBBLE_MS-age)/500:1,dark)-4;}
    if(p.emo){const age=now-p.emo.t0;if(age>EMO_MS)p.emo=null;else{c.globalAlpha=Math.min(1,(EMO_MS-age)/600);c.font='26px serif';c.textAlign='center';c.textBaseline='bottom';c.fillText(p.emo.e,sx(p.x),above-age/90);c.globalAlpha=1;}}
  }
  if(h&&h.k==='vendor'){const f=(t-h.at)/(h.end-h.at);if(f>=0&&f<=1){const x=h.rtl?W+90-(W+180)*f:-90+(W+180)*f;bubble(c,sx(x),sy(h.y-44),h.text,1,dark);}}
  if(h&&h.k==='lion'){const f=(t-h.at)/(h.end-h.at);if(f>=0&&f<=1){const x=h.rtl?W+90-(W+180)*f:-90+(W+180)*f;bubble(c,sx(x),sy(h.y-36),'Tùng tùng cắc! 🦁',1,dark);}}
  S.floaters=S.floaters.filter(fl=>{const age=now-fl.t0,p=S.people.get(fl.pid);if(age>2200||!p)return false;
    c.globalAlpha=Math.min(1,(2200-age)/500);c.font='800 15px "Trebuchet MS",sans-serif';c.textAlign='center';c.textBaseline='bottom';
    c.fillStyle='#b8322c';c.fillText(fl.text,sx(p.x),sy(p.y-132*AV)-34-age/40);c.globalAlpha=1;return true;});
  if(S.wed){
    const ck=wedClock();if(ck!==S.clock){S.clock=ck;const el=S.dlg.querySelector('.wk-clock');if(el)el.textContent=ck;syncMusic();}
    if(S.burst){const age=now-S.burst;if(age>3500)S.burst=0;else for(let i=0;i<22;i++){const x=S.ox+(120+(i*137)%360)*k,y=S.oy+(300-(age/12)*(1+i%3*.25))*k;
      c.globalAlpha=Math.max(0,1-age/3500);c.font='20px serif';c.textAlign='center';c.fillText(['💖','🎉','🌸','💕'][i%4],x+Math.sin(age/300+i)*10,y+(i%5)*24);c.globalAlpha=1;}}
    const ph=S.photo;
    if(ph){const left=ph.at-t;
      if(left>0){c.fillStyle='rgba(0,0,0,.25)';c.fillRect(0,0,S.cw,S.ch);c.fillStyle='#fff';c.font='800 64px "Trebuchet MS",sans-serif';c.textAlign='center';c.textBaseline='middle';
        c.fillText(String(Math.ceil(left)),S.cw/2,S.ch/2);c.font='700 16px "Trebuchet MS",sans-serif';c.fillText('📸 Cười lên nào!',S.cw/2,S.ch/2+52);}
      else{if(!ph.taken){ph.taken=true;if(ph.pid===myPid)capture(ph.n);}
        c.fillStyle=`rgba(255,255,255,${Math.max(0,.85+left*2)})`;c.fillRect(0,0,S.cw,S.ch);if(left<-.45)S.photo=null;}}
  }
  const tb=mySeat(),bar=S.dlg.querySelector('.wk-time');
  if(tb&&bar&&tb.until){bar.style.transform=`scaleX(${Math.max(0,Math.min(1,(tb.until-t)/120))})`;}
}
function tag(c,x,y,name,title,mine,dark){
  c.textAlign='center';c.textBaseline='bottom';
  c.font='700 11.5px "Trebuchet MS",sans-serif';const nw=c.measureText(name).width;
  let tw=0;if(title){c.font='600 9.5px "Trebuchet MS",sans-serif';tw=c.measureText(title).width;}
  const w=Math.max(nw,tw)+12,hgt=title?28:17;
  c.fillStyle=dark?'rgba(24,24,34,.78)':'rgba(255,253,248,.86)';c.beginPath();c.roundRect(x-w/2,y-hgt,w,hgt,8);c.fill();
  c.font='700 11.5px "Trebuchet MS",sans-serif';c.fillStyle=mine?(dark?'#ff9b7d':'#b8432c'):(dark?'#f1ede6':'#4a3b35');c.fillText(name,x,y-(title?13:2.5));
  if(title){c.font='600 9.5px "Trebuchet MS",sans-serif';c.fillStyle=dark?'#bdb6ad':'#8a7a70';c.fillText(title,x,y-2);}
}
/** A speech bubble whose tail points at (x, bottom); returns its top. Player text as is (not translated). */
function bubble(c,x,bottom,text,alpha,dark){
  c.font='600 13px "Trebuchet MS",sans-serif';
  const max=170,words=String(text).split(/\s+/),lines=[];let line='';
  for(const w of words){const tryL=line?line+' '+w:w;if(c.measureText(tryL).width<=max||!line)line=tryL;else{lines.push(line);line=w;}if(lines.length===3)break;}
  if(lines.length<3&&line)lines.push(line);
  if(lines.length===3&&words.join(' ').length>lines.join(' ').length)lines[2]=lines[2].replace(/.{0,2}$/,'…');
  const lw=Math.min(max,Math.max(...lines.map(l=>c.measureText(l).width))),w=lw+18,h=lines.length*16+10,top=bottom-h-6;
  c.globalAlpha=alpha;c.fillStyle=dark?'#2b2a36':'#fffdf8';c.strokeStyle=dark?'#4a4858':'#e3d6c6';c.lineWidth=1;
  c.beginPath();c.roundRect(x-w/2,top,w,h,10);c.fill();c.stroke();
  c.beginPath();c.moveTo(x-6,top+h-.5);c.lineTo(x,bottom);c.lineTo(x+6,top+h-.5);c.closePath();c.fill();
  c.fillStyle=dark?'#f1ede6':'#3c302b';c.textAlign='center';c.textBaseline='top';
  lines.forEach((l,i)=>c.fillText(l,x,top+6+i*16));c.globalAlpha=1;
  return top;
}

/* ---- a hidden tab leaves the street after a minute; back in sight, back on the street ---- */
document.addEventListener('visibilitychange',()=>{
  if(!S.dlg?.open)return;
  if(document.visibilityState==='hidden'){clearTimeout(S.hideTimer);S.hideTimer=setTimeout(()=>{if(S.room){live.send({t:'walk_out'});leaveLocal();S.paused=true;}},60000);}
  else{clearTimeout(S.hideTimer);if(S.paused&&live.state==='open'){S.paused=false;enter(S.lastPublic||pick());}}
});
