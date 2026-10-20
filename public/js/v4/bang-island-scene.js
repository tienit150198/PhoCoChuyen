/** ⚔️ Đảo bang: being on the bang's island. One controller for both interfaces: the new one draws with Phaser
 * (client/isometric/bang-island.ts, inside the isometric bundle), the old one with a 2D canvas (v4/bang-island-walk.js);
 * this owns walking (tap, arrows / W A S D along the screen, the facility chips), the live room (v4/bang-island-live.js:
 * others walking, gesturing, talking), names, bubbles and the facility labels over the map, and the facility panel
 * (level, next level, the build timer, the buttons the Bang / pet branches wire: v4/bang-island.js actions).
 * The island's data is the server's answer (GET /api/bang-island: game/bang_island.py island_view). 🏝️ Its `isle`
 * (level, an upgrade being built) picks the map (layoutOf: bang-island-layout.js layout(level, building)); when an
 * upgrade starts or ends the map is drawn again (relayout). */
import {layout,arrival,step,findPath,nearestWalkable,facilityAt,spotNear,doorOf,spotById,spotLine,EMOTES,SCREEN_KEYS,FACILITY_IDS} from '../bang-island-layout.js';
import {createBangPresence,peerAt} from './bang-island-live.js';
import {lookOf} from './look.js';
import {newInterface} from '../interface-mode.js';

const SPEED=.15,SEND_MS=320,REFRESH_MS=5000;
const ROLE_BADGE={bang_chu:'👑',pho_bang:'⭐',truong_lao:'🎖️',tinh_anh:'✨'};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

/** 1 giờ 05 phút / 12 phút 30 giây / 45 giây: how long a build still takes. */
export function timeLeft(secs){
  const s=Math.max(0,Math.ceil(secs)),d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60),r=s%60;
  if(d)return `${d} ngày ${h} giờ`;
  if(h)return `${h} giờ ${String(m).padStart(2,'0')} phút`;
  if(m)return `${m} phút ${String(r).padStart(2,'0')} giây`;
  return `${r} giây`;
}
/** Facing for the illustrated figures from a step on the map. */
export function facing(dx,dy,prev='se'){
  if(Math.abs(dx)+Math.abs(dy)<1e-6)return prev;
  return Math.abs(dx)>=Math.abs(dy)?(dx>=0?'se':'nw'):(dy>=0?'sw':'ne');
}
/** The map for the server's view of the bang: its island's level, and the next level's work site while it is built. */
export const layoutOf=bang=>layout(bang?.isle?.level||1,bang?.isle?.state==='building'?bang.isle.to||0:0);
/** The renderers' facility looks from the server's view. */
export const looks=bang=>({name:bang.name,emoji:bang.emoji,color:bang.color,facilities:(bang.facilities||[]).map(f=>({id:f.id,level:f.level,band:f.band,state:f.state})),
  ...(bang.hall?{hall:{style:String(bang.hall.style||''),look:Number(bang.hall.look)||0}}:{}),...(Array.isArray(bang.decor)?{decor:bang.decor.map(String)}:{})});   // 🏯🎏 20/10 (game/bang_extra.py)

/** The session without the DOM: tests drive it with a fake view, renderer, live socket and clock. */
export function createBangIslandSession(env,{isle,view,loadRenderer,loadLive=async()=>null,actions={},clock=()=>performance.now(),wall=()=>Date.now()/1000,
  raf=fn=>requestAnimationFrame(fn),caf=id=>cancelAnimationFrame(id),onClose=()=>{}}){
  let bang=isle.bang,skew=(Number(isle.now)||wall())-wall(),L=layoutOf(bang);
  const [sx,sy]=arrival(L);
  const me={x:sx,y:sy,target:null,route:null,dir:'ne',left:false,walking:false,goal:null,pose:null,sent:[sx,sy],sendAt:0};
  const keys=new Set();
  let renderer=null,presence=null,frameId=0,closed=false,started=false,last=0,previousPause=false,statusAt=-1e9,why=null,panel=null,refreshAt=0,refreshing=null;
  const look=lookOf(env.api.state),gender=env.api.state?.journey?.gender==='male'||env.api.state?.journey?.gender==='female'?env.api.state.journey.gender:null;
  const serverNow=()=>wall()+skew,doorsOf=()=>new Map(FACILITY_IDS.map(id=>[id,doorOf(L,id)]));
  let doors=doorsOf(),relaying=null;
  const fac=id=>(bang.facilities||[]).find(f=>f.id===id)||null;

  function close(reason=null){
    if(closed)return;closed=true;why=reason;caf(frameId);
    presence?.stop();renderer?.destroy();renderer=null;env.api.removeEventListener?.('state',onState);view.destroy();
    if(started&&env.world){env.world.paused=previousPause;env.world.wake?.();}
    const said={changed:'Bạn không còn ở trong bang này nữa.',ended:'Đảo bang đã đóng.',other:'Bạn đang ở đảo bang ở một cửa sổ khác.',gone:'Bạn chưa vào được đảo bang.',full:'Đảo bang đang đông quá, chờ chút nhé.'}[reason];
    if(said)env.toast?.(said);
    onClose(reason);
  }
  function onState(){if(env.api.state?.jail)close();}
  function send(to,ms){if(!presence)return;presence.move([me.x,me.y],to,Math.min(6000,ms));me.sent=to;me.sendAt=clock();}
  /** Walk to (x, y) around what stands in the way (findPath: waypoints, each leg sent to the room as it starts). */
  function go(x,y,goal=null){
    const [tx,ty]=nearestWalkable(L,x,y);me.route=findPath(L,[me.x,me.y],[tx,ty]);me.goal=goal;me.pose=null;leg();
  }
  function leg(){const to=me.route.shift();me.target=to;send(to,Math.hypot(to[0]-me.x,to[1]-me.y)/SPEED*1000);}
  /** Walk up to a facility (and open its panel at once) or a decorative spot. */
  function visit(id){
    const d=doorOf(L,id);if(!d)return;
    if(FACILITY_IDS.includes(id))openPanel(id);
    go(d[0],d[1],id);
  }
  function tap(clientX,clientY){
    const p=renderer?.toMap(clientX,clientY);if(!p)return;
    const f=facilityAt(L,p[0],p[1]);if(f){visit(f.id);return;}
    const s=spotNear(L,p[0],p[1]);if(s){visit(s.id);return;}
    go(p[0],p[1]);
  }
  function reach(id){
    me.goal=null;
    const s=spotById(L,id);
    if(s){me.pose=s.pose;view.notice(`${s.emoji} ${spotLine(s,Math.floor(clock()/1000))}`);}
    else me.pose=L.slots[id]?.pose==='bow'?'bow':null;
    presence?.act(id);
  }
  function key(code,down){
    const map={ArrowUp:'u',KeyW:'u',ArrowDown:'d',KeyS:'d',ArrowLeft:'l',KeyA:'l',ArrowRight:'r',KeyD:'r'};
    const k=map[code];if(!k)return false;if(down)keys.add(k);else keys.delete(k);return true;
  }
  function walk(dt,t){
    let vx=0,vy=0;for(const k of keys){vx+=SCREEN_KEYS[k][0];vy+=SCREEN_KEYS[k][1];}
    const was=[me.x,me.y];
    if(Math.hypot(vx,vy)>1e-6){
      me.target=null;me.route=null;me.goal=null;me.pose=null;const n=Math.hypot(vx,vy);vx/=n;vy/=n;
      const [nx,ny]=step(L,me.x,me.y,me.x+vx,me.y+vy,SPEED*dt);me.x=nx;me.y=ny;
      if(t-me.sendAt>=SEND_MS){const ahead=step(L,me.x,me.y,me.x+vx,me.y+vy,SPEED*SEND_MS/1000);send([ahead[0],ahead[1]],SEND_MS);}
    }else if(me.target){
      const [nx,ny,done]=step(L,me.x,me.y,me.target[0],me.target[1],SPEED*dt);me.x=nx;me.y=ny;
      const stuck=Math.hypot(nx-was[0],ny-was[1])<1e-7;
      if(done&&me.route?.length&&Math.hypot(nx-me.target[0],ny-me.target[1])<1e-4){leg();}   // a waypoint: the next leg
      else if(done||stuck){const g=me.goal;me.target=null;me.route=null;const d=g&&doorOf(L,g);if(g&&d&&Math.hypot(me.x-d[0],me.y-d[1])<.03)reach(g);else me.goal=null;}
    }
    const dx=me.x-was[0],dy=me.y-was[1];me.walking=Math.hypot(dx,dy)>1e-6;
    if(me.walking){me.dir=facing(dx,dy,me.dir);if(Math.abs(dx-dy)>1e-6)me.left=dx-dy<0;}
    if(!me.walking&&!me.target&&presence&&Math.hypot(me.sent[0]-me.x,me.sent[1]-me.y)>.004)send([me.x,me.y],0);
  }
  function people(){
    const out=[],now=clock();
    out.push({id:'me',me:true,name:'Bạn',x:me.x,y:me.y,look,gender:gender||'none',dir:me.dir,left:me.left,walking:me.walking,pose:me.pose,badge:ROLE_BADGE[isle.me?.role]||'',
      bubble:presence?.self.bubble&&presence.self.bubble.until>now?presence.self.bubble.text:null,emote:presence?.self.emote&&presence.self.emote.until>now?presence.self.emote.e:null});
    for(const p of presence?.peers.values()||[]){
      const [x,y]=peerAt(p,now),moving=p.ms>0&&now<p.t0+p.ms,dx=p.to[0]-p.from[0],dy=p.to[1]-p.from[1];
      if(moving){p.dir=facing(dx,dy,p.dir||'se');if(Math.abs(dx-dy)>1e-6)p.left=dx-dy<0;}
      const act=p.act&&p.act.until>now?p.act.s:null,spot=act&&spotById(L,act),f=act&&fac(act);
      out.push({id:p.pid,name:p.name,x,y,look:p.lk,gender:p.g||'none',dir:p.dir||'se',left:!!p.left,walking:moving,pose:moving?null:spot?.pose||(act==='tuong_bang'?'bow':null),
        badge:p.guest?'🧳':ROLE_BADGE[p.role]||'',bubble:p.bubble&&p.bubble.until>now?p.bubble.text:null,emote:p.emote&&p.emote.until>now?p.emote.e:null,act:spot?spot.emoji:f?f.emoji:null});
    }
    return out;
  }
  /* ---- the facility panel ---------------------------------------------------------------------------------------- */
  function openPanel(id){const f=fac(id);if(!f)return;panel={id,msg:null,busy:false};view.panel(f,panelState());}
  const panelState=()=>({now:serverNow(),busy:panel?.busy,msg:panel?.msg,guest:isle.me?.kind==='guest'});
  async function runAction(op){
    if(!panel||panel.busy)return;const id=panel.id;panel.busy=true;view.panel(fac(id),panelState());
    try{const r=await actions.run?.(id,op);if(panel?.id===id)panel.msg={text:r?.message||'Đã ghi nhận.',kind:r?.placeholder?'soon':'good'};if(r?.bang)update(r);}
    catch(e){if(panel?.id===id)panel.msg={text:e?.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};}
    finally{if(panel?.id===id){panel.busy=false;view.panel(fac(id),panelState());}}
  }
  /** A fresh answer from the server (a build finished, an upgrade started, another member changed something). */
  function update(next){
    if(!next?.bang||next.bang.id!==bang.id)return;
    bang=next.bang;if(Number.isFinite(next.now))skew=next.now-wall();
    renderer?.setBang?.(looks(bang));view.facilities?.(bang.facilities);
    if(panel)view.panel(fac(panel.id),panelState());
    relayout();
  }
  /** 🏝️ The island grew (or its next level's work started / ended): the new map, drawn again from scratch. */
  function relayout(){
    const next=layoutOf(bang);if(next===L||closed)return;
    L=next;doors=doorsOf();view.spots?.(L.spots);
    if(!renderer||relaying)return;
    const old=renderer;renderer=null;old.destroy();view.swapCanvas?.();
    relaying=Promise.resolve(loadRenderer(view,looks(bang),L)).then(r=>{if(closed){r?.destroy?.();return;}renderer=r;},()=>{if(!closed)close('gone');})
      .finally(()=>{relaying=null;if(!closed&&layoutOf(bang)!==L)relayout();});
  }
  async function refresh(force=false){
    if(closed||refreshing||(!force&&clock()<refreshAt))return;
    refreshAt=clock()+REFRESH_MS;
    refreshing=(async()=>{try{const next=await actions.refresh?.();if(!closed&&next)update(next);}catch{/* the next tick tries again */}finally{refreshing=null;}})();
    return refreshing;
  }
  function labels(){
    const now=serverNow();
    return (bang.facilities||[]).map(f=>{const a=renderer.anchor?.(f.id);const s=a&&renderer.toScreen(a.x,a.y,a.lift);if(!s)return null;
      const building=f.state==='building',left=building?Math.max(0,f.ready_at-now):0,d=doors.get(f.id);
      const near=panel?.id===f.id||Boolean(d&&Math.hypot(d[0]-me.x,d[1]-me.y)<.09);
      return {id:f.id,emoji:f.emoji,name:f.name,level:f.level,building,left,near,sx:s[0],sy:s[1]};}).filter(Boolean);
  }
  function status(){
    const n=1+(presence?.peers.size||0),online=Number.isFinite(bang.members_online)?` · ${bang.members_online} thành viên online`:'';
    const is=bang.isle||{level:1},cap=is.cap||presence?.cap||0,grow=is.state==='building'?` · 🚧 lên cấp ${is.to}: ${timeLeft(Math.max(0,is.ready_at-serverNow()))}`:'';
    view.status(`🏝️ Đảo cấp ${is.level}${grow} · 👥 ${n}${cap?`/${cap}`:''}${online}`+(presence&&!presence.online?' · đang kết nối lại…':''));
    view.isle?.(is,serverNow());
    // A build that just finished: ask the server (it decides), at most every few seconds.
    if((bang.facilities||[]).some(f=>f.state==='building'&&f.ready_at<=serverNow())||is.state==='building'&&is.ready_at<=serverNow())refresh();
    if(panel)view.panel(fac(panel.id),panelState());
  }
  function tick(t){
    if(closed)return;
    if(!renderer){frameId=raf(tick);return;}   // being drawn again (relayout)
    const dt=Math.min(.05,Math.max(0,(t-last)/1000));last=t;
    walk(dt,t);
    const list=people();
    renderer.frame({people:list,focus:[me.x,me.y],shift:panel?view.covered?.()||0:0},t);
    const head=renderer.personHeight||90;
    view.tags(list.filter(p=>!p.hidden).map(p=>{const s=renderer.toScreen(p.x,p.y);return s&&{...p,sx:s[0],sy:s[1]-head};}).filter(Boolean));
    view.labels?.(labels());
    if(t-statusAt>1000){statusAt=t;status();}
    if(!closed)frameId=raf(tick);
  }
  view.onClose(()=>close());
  view.onTap(tap);view.onKey(key);view.onVisit(visit);
  view.onEmote(e=>{if(presence)presence.emote(e);});
  view.onSay(text=>{const ok=presence?.say(text);if(!ok)view.notice('Chưa nói được: đang mất kết nối, thử lại sau nhé.');return ok;});
  view.onAction(op=>runAction(op));
  view.onPanelClose(()=>{panel=null;view.panel(null);});
  view.onIsle?.(()=>{env.act?.('bang',{tab:'build'});});   // 🏝️ the island's level chip: the Bang sheet's island card

  async function start(){
    if(started||closed)return;
    if(env.api.state?.jail){close();return;}
    started=true;
    if(env.world){previousPause=env.world.paused;env.world.paused=true;}
    env.closeSheet?.();env.api.addEventListener?.('state',onState);view.open(L,isle);
    try{
      renderer=await loadRenderer(view,looks(bang),L);if(closed){renderer?.destroy();renderer=null;return;}
      view.ready();
      const live=await loadLive().catch(()=>null);if(closed)return;
      if(live)presence=createBangPresence({live,bang:bang.id,look,gender,at:()=>[me.x,me.y],clock,
        onLeft:w=>close(w),onView:()=>refresh(true),onError:(msg,code)=>{if(code==='no_bang_island')close('gone');else if(code==='full')close('full');else view.notice(msg);}}).start();
      last=clock();frameId=raf(tick);
    }catch(error){if(!closed){env.toast?.(error?.message||'Chưa mở được đảo bang. Thử lại nhé.',true);close();}}
  }
  return {start,close,tick,tap,visit,key,update,refresh,runAction,
    get layout(){return L;},get me(){return me;},get why(){return why;},get presence(){return presence;},get closed(){return closed;},get bang(){return bang;},get panel(){return panel;}};
}

const spotChips=list=>list.map(s=>`<button type="button" class="bisl-chip ghost" data-visit="${esc(s.id)}">${esc(s.emoji)} ${esc(s.name)}</button>`).join('');
/** The fullscreen dialog: the stage, names, bubbles and facility labels, the panel, the chips, gestures, chat. */
export function createView(){
  const previous=document.activeElement,dialog=document.createElement('dialog');
  dialog.className='bisl-scene';dialog.setAttribute('data-bang-island','');dialog.setAttribute('aria-labelledby','bislTitle');
  const listeners=[],on=(t,n,fn,o)=>{t.addEventListener(n,fn,o);listeners.push(()=>t.removeEventListener(n,fn,o));};
  const cb={close:()=>{},tap:()=>{},key:()=>false,visit:()=>{},emote:()=>{},say:()=>true,action:()=>{},panelClose:()=>{},isle:()=>{}};
  const tagCache=new Map(),labelCache=new Map();let noticeTimer=0,panelHTML='',cover=null,wide=null;
  const release=()=>{for(const c of ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','KeyW','KeyA','KeyS','KeyD'])cb.key(c,false);};
  function bind(canvas){
    let down=null;
    on(canvas,'pointerdown',e=>{down=[e.clientX,e.clientY];});
    on(canvas,'pointerup',e=>{if(down&&Math.hypot(e.clientX-down[0],e.clientY-down[1])<14)cb.tap(e.clientX,e.clientY);down=null;});
    on(canvas,'keydown',e=>{if(cb.key(e.code,true))e.preventDefault();});
    on(canvas,'keyup',e=>{if(cb.key(e.code,false))e.preventDefault();});
    on(canvas,'blur',release);
  }
  const chip=f=>`<button type="button" class="bisl-chip${f.state==='building'?' is-building':''}" data-visit="${esc(f.id)}">${esc(f.emoji)} <span>${esc(f.name)}</span> <b>${f.level?`${f.level}`:'–'}</b>${f.state==='building'?' 🚧':''}</button>`;
  const view={
    canvas:null,dialog,
    onClose:fn=>{cb.close=fn;},onTap:fn=>{cb.tap=fn;},onKey:fn=>{cb.key=fn;},onVisit:fn=>{cb.visit=fn;},onEmote:fn=>{cb.emote=fn;},onSay:fn=>{cb.say=fn;},
    onAction:fn=>{cb.action=fn;},onPanelClose:fn=>{cb.panelClose=fn;},onIsle:fn=>{cb.isle=fn;},
    open(L,isle){
      const b=isle.bang,colour=/^#[0-9a-f]{6}$/i.test(b.color)?b.color:'#c2410c';
      dialog.style.setProperty('--bang',colour);
      dialog.innerHTML=`<div class="bisl-layout">
        <header class="bisl-top"><span class="bisl-flag" aria-hidden="true">${esc(b.emoji)}</span><div class="bisl-title"><h2 id="bislTitle">${esc(b.name)}</h2><p data-status role="status">⚔️ Đảo bang · đang cập bến…</p></div>
          <div class="bisl-top-actions"><button type="button" class="btn bisl-isle" data-isle aria-label="Đảo bang: cấp và mở rộng">🏝️ <b>${esc(b.isle?.level||1)}</b></button><button type="button" class="btn" data-close>← Về phố</button></div></header>
        <div class="bisl-stage"><canvas tabindex="0" aria-label="${esc(L.name)}: chạm để đi, chạm vào một công trình để xem; dùng mũi tên hoặc W A S D để di chuyển."></canvas>
          <div class="bisl-labels" aria-hidden="true"></div><div class="bisl-tags" aria-hidden="true"></div>
          <p class="bisl-loading" role="status">⛵ Thuyền bang đang cập bến…</p>
          <p class="bisl-notice" role="status" aria-live="polite" hidden></p>
          <section class="bisl-panel" data-panel hidden aria-live="polite"></section></div>
        <footer class="bisl-bar">
          <div class="bisl-row bisl-facs" role="group" aria-label="Công trình của bang">${(b.facilities||[]).map(chip).join('')}</div>
          <div class="bisl-row bisl-more"><div class="bisl-emotes" role="group" aria-label="Biểu cảm">${EMOTES.map(([id,e,name])=>`<button type="button" class="bisl-emo" data-emote="${id}" aria-label="${esc(name)}" title="${esc(name)}">${e}</button>`).join('')}</div>
          <div class="bisl-spots" role="group" aria-label="Chỗ chơi trên đảo">${spotChips(L.spots)}</div></div>
          <form class="bisl-say"><input type="text" maxlength="120" autocomplete="off" enterkeyhint="send" placeholder="Nói gì đó với cả bang…" aria-label="Nói với mọi người trên đảo bang"><button type="submit" class="btn primary">Gửi</button></form>
        </footer></div>`;
      view.canvas=dialog.querySelector('canvas');
      const input=dialog.querySelector('.bisl-say input');
      on(dialog,'cancel',e=>{e.preventDefault();if(!dialog.querySelector('[data-panel]').hidden)cb.panelClose();else cb.close();});
      on(dialog,'click',e=>{const el=e.target.closest('button');if(!el)return;
        if(el.hasAttribute('data-close'))cb.close();else if(el.hasAttribute('data-isle'))cb.isle();else if(el.dataset.visit)cb.visit(el.dataset.visit);else if(el.dataset.emote)cb.emote(el.dataset.emote);
        else if(el.dataset.op&&!el.disabled)cb.action(el.dataset.op);else if(el.hasAttribute('data-panel-close'))cb.panelClose();});
      on(dialog,'submit',e=>{e.preventDefault();const text=input.value.trim();if(text&&cb.say(text)!==false)input.value='';});
      bind(view.canvas);
      on(window,'pagehide',()=>cb.close());on(window,'resize',()=>{cover=null;wide=null;});
      document.body.append(dialog);dialog.showModal();
    },
    swapCanvas(){const fresh=view.canvas.cloneNode(false);view.canvas.replaceWith(fresh);view.canvas=fresh;bind(fresh);return fresh;},
    ready(){dialog.querySelector('.bisl-loading')?.remove();view.canvas?.focus({preventScroll:true});},
    status(text){const p=dialog.querySelector('[data-status]');if(p&&p.textContent!==text)p.textContent=text;},
    notice(text){const p=dialog.querySelector('.bisl-notice');if(!p)return;p.textContent=text;p.hidden=false;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>{p.hidden=true;},5000);},
    spots(list){const row=dialog.querySelector('.bisl-spots');if(row){const html=spotChips(list);if(row._html!==html){row.innerHTML=html;row._html=html;}}},
    /** 🏝️ The island's chip: its level, 🚧 while the next one is built. */
    isle(is){const b=dialog.querySelector('[data-isle]');if(!b)return;const html=`🏝️ <b>${esc(is?.level||1)}</b>${is?.state==='building'?' 🚧':''}`;if(b._html!==html){b.innerHTML=html;b._html=html;}},
    facilities(list){const row=dialog.querySelector('.bisl-facs');if(row){const html=list.map(chip).join('');if(row._html!==html){row.innerHTML=html;row._html=html;}}},
    tags(list){
      const box=dialog.querySelector('.bisl-tags');if(!box)return;const seen=new Set();
      for(const p of list){
        seen.add(p.id);let el=tagCache.get(p.id);
        if(!el){el=document.createElement('div');el.className='bisl-tag'+(p.me?' me':'');box.append(el);tagCache.set(p.id,el);el._html='';el._tf='';}
        const html=`${p.bubble?`<span class="bisl-bubble">${esc(p.bubble)}</span>`:''}${p.emote?`<span class="bisl-emote">${esc((EMOTES.find(x=>x[0]===p.emote)||[])[1]||'')}</span>`:''}<b>${p.badge?esc(p.badge)+' ':''}${esc(p.name)}${p.act?` ${esc(p.act)}`:''}</b>`;
        if(el._html!==html){el.innerHTML=html;el._html=html;}
        const tf=`translate(${Math.round(p.sx)}px,${Math.round(p.sy)}px) translate(-50%,-100%)`;if(el._tf!==tf){el.style.transform=tf;el._tf=tf;}
      }
      for(const [id,el] of tagCache)if(!seen.has(id)){el.remove();tagCache.delete(id);}
    },
    /** The facility labels over the map: name and level, the build timer while building. A label that would cover
     * one nearer the viewer moves up above it (the nearer one keeps its place). */
    labels(list){
      const box=dialog.querySelector('.bisl-labels');if(!box)return;
      if(wide===null)wide=(box.clientWidth||0)>=900;
      const placed=[];
      for(const l of [...list].sort((a,b)=>b.sy-a.sy)){
        let el=labelCache.get(l.id);
        if(!el){el=document.createElement('div');el.className='bisl-label';box.append(el);labelCache.set(l.id,el);el._html='';el._tf='';}
        // A phone shows a small chip (sign, level, 🚧); the facility nearby, the one whose panel is open and a wide screen show the name and timer.
        const full=wide||l.near,html=full?`<b>${esc(l.emoji)} <span>${esc(l.name)}</span> <em>${l.level?l.level:'–'}</em></b>${l.building?`<i>🚧 ${esc(timeLeft(l.left))}</i>`:''}`
          :`<b title="${esc(l.name)}">${esc(l.emoji)} <em>${l.level?l.level:'–'}</em>${l.building?' 🚧':''}</b>`;
        if(el._html!==html){el.innerHTML=html;el._html=html;el.classList.toggle('is-building',l.building);el.classList.toggle('is-chip',!full);el._w=el.offsetWidth||120;el._h=el.offsetHeight||26;}
        let x=Math.round(l.sx),y=Math.round(l.sy);const w=el._w,h=el._h+6;
        for(let pass=0;pass<4;pass++){const hit=placed.find(r=>Math.abs(r.x-x)<(r.w+w)/2&&y>r.y-r.h&&y-h<r.y);if(!hit)break;y=hit.y-hit.h;}
        placed.push({x,y,w,h});
        const tf=`translate(${x}px,${y}px) translate(-50%,-100%)`;if(el._tf!==tf){el.style.transform=tf;el._tf=tf;}
      }
    },
    /** How much of the stage's bottom the panel covers (half of it, CSS px), 0 when it sits on the side. */
    covered(){
      if(cover!==null)return cover;const p=dialog.querySelector('[data-panel]'),st=dialog.querySelector('.bisl-stage');if(!p||p.hidden||!st)return cover=0;
      const a=p.getBoundingClientRect(),b=st.getBoundingClientRect();return cover=a.width>b.width*.7?Math.max(0,b.bottom-a.top)/2:0;},
    /** The panel of one facility (null closes it). */
    panel(f,st={}){
      const box=dialog.querySelector('[data-panel]');if(!box)return;
      if(!f){box.hidden=true;box.innerHTML='';panelHTML='';cover=null;return;}
      const building=f.state==='building',left=building?Math.max(0,f.ready_at-st.now):0;
      const next=building?`<p class="bisl-build">🚧 Đang xây lên <b>cấp ${f.to}</b> · còn <b data-left></b></p>`
        :f.next?`<p>Cấp tiếp theo: <b>${f.next}</b>${f.next_band!==f.band?' · đổi diện mạo mới':''}</p>`:'<p>🏆 Đã đạt cấp tối đa.</p>';
      const html=`<header><h3>${esc(f.emoji)} ${esc(f.name)}</h3><button type="button" class="bisl-x" data-panel-close aria-label="Đóng">✕</button></header>
        <p class="bisl-lv">${f.level?`Cấp ${f.level}/${f.max} · bậc ${esc(f.band_name)}`:'Chưa xây · đất trống'}</p>
        <p class="bisl-desc">${esc(f.desc||'')}</p>${next}${f.note?`<p class="bisl-note">${esc(f.note)}</p>`:''}
        <div class="bisl-acts">${(f.actions||[]).map(a=>`<button type="button" class="btn${a.op==='nang_cap'?'':' primary'}" data-op="${esc(a.op)}"${st.busy?' disabled':''}>${esc(a.emoji)} ${esc(a.label)}</button>`).join('')}</div>
        ${st.msg?`<p class="bisl-msg ${esc(st.msg.kind)}" role="status">${esc(st.msg.text)}</p>`:''}`;
      if(html!==panelHTML){box.innerHTML=html;panelHTML=html;cover=null;}
      const t=box.querySelector('[data-left]');if(t){const txt=timeLeft(left);if(t.textContent!==txt)t.textContent=txt;}
      box.hidden=false;
    },
    destroy(){clearTimeout(noticeTimer);listeners.splice(0).forEach(off=>off());if(dialog.open)dialog.close();dialog.remove();tagCache.clear();labelCache.clear();if(previous?.isConnected)previous.focus?.({preventScroll:true});},
  };
  return view;
}

/** The renderer for this player's interface: Phaser on the new one (the 2D walk if it cannot start), the 2D walk on the old one. */
export async function loadRendererFor(env,view,L,bang){
  if(newInterface(env.api.state)){
    try{
      const m=await import('../isometric/phaser-world.js');
      if(typeof m.BangIslandRenderer==='function'){
        const r=new m.BangIslandRenderer(view.canvas,L,bang);let timer;
        const ok=await Promise.race([r.ready.then(()=>true),new Promise(res=>{timer=setTimeout(()=>res(false),15000);})]).finally(()=>clearTimeout(timer));
        if(ok)return r;r.destroy();
      }
    }catch(e){console.warn('bang island:',e);}
    view.swapCanvas();
  }
  const {createBangWalkRenderer}=await import('./bang-island-walk.js');
  return createBangWalkRenderer(view.canvas,L,bang);
}
