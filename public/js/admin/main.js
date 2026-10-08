/** Operator site (/admin): sign in with a game account listed in ADMIN_USERS, then
 * "Tổng quan" (stats), "Góp ý" (feedback inbox) and "Hệ thống" (server). Every
 * number comes from the admin endpoints, which re-check the account on each call;
 * this page only decides what to draw. Nothing secret is rendered or stored: the
 * CSRF token stays in memory, the session in its HttpOnly cookie.
 *
 * Loading: one GET /api/admin/stats/summary draws the first screen (skeletons until
 * then). The save-derived cards load when they scroll into view and "Hệ thống" when it
 * opens (GET /api/admin/stats/section, drawn by ./sections.js, imported on demand).
 * Changing the range aborts the request still running for the old one. The "Trực tiếp"
 * band (…/section?name=live: active players, commands/min, latency, DB size) is polled
 * every LIVE_MS while "Tổng quan" is shown; it costs the server a few index reads. The
 * "Thời gian chơi" card (…?name=playtime) loads when it scrolls into view, like the saves cards.
 * "Giữ chân" (…?name=retention, drawn by ./retention.js, imported when the view opens): retention by start
 * day, the new-player funnel, where players drop off, careers, sources, load times, client errors; its
 * tables also download as one CSV (…&format=csv).
 * "Tổng quan đầu tư" (…?name=invest, drawn by ./invest.js): the job's copy of game/admin_kpi.py (computed in the
 * background every 10 minutes while this page asks for it), in tabs with a period selector; CSV per tab
 * (…&part=…) and a printable report (#bao-cao, not in the menu).
 * "Tặng xu" (./gifts.js): accounts by username with their gifts, a gift of coins per player, "Quà đã tặng". */
import {AdminAPI} from './api.js';
import {Inbox} from './inbox.js';
import {ChatAdmin} from './chat.js';  // 💬 Chat: reports, hide, mute (live chat)
import {KaraAdmin} from './karaoke.js';  // 🎤 Phòng hát: reports, banned songs, room tools
import {GiftAdmin} from './gifts.js';
import {WedInviteAdmin} from './wedinvite.js';  // 💌 Thiệp cưới: the cards sent to the whole server, delete one  // 🎁 Tặng xu: accounts, a gift of coins per player, "Quà đã tặng"
import {UsersAdmin} from './users.js';
import {overviewView,liveView,skeleton,skelCard} from './stats.js';
import {esc,icon,hm,ago,num,toast} from './ui.js';

const api=new AdminAPI();
const root=document.getElementById('root');
const VIEWS={'tong-quan':['Tổng quan','chart'],'dau-tu':['Tổng quan đầu tư','trend'],'giu-chan':['Giữ chân','loop'],'nguoi-dung':['Người dùng','user'],'gop-y':['Góp ý','inbox'],'chat':['Chat','chat'],'phong-hat':['Phòng hát','music'],'tang-xu':['Tặng xu','gift'],'thiep-cuoi':['Thiệp cưới','send'],'he-thong':['Hệ thống','server'],
  'bao-cao':['Báo cáo số liệu','print']};
const HIDDEN=new Set(['bao-cao']);  // reached from "Xuất báo cáo", not listed in the menu
const INVEST_VIEWS=new Set(['dau-tu','bao-cao']);  // drawn from …/section?name=invest only (no summary request)
const STATS_VIEWS=new Set(['tong-quan','giu-chan','he-thong',...INVEST_VIEWS]);  // views drawn from the stats endpoints
const RANGES=[7,30,90];
const REFRESH_MS=60000;
const LIVE_MS=15000;
const RANGE_DEBOUNCE_MS=180;
const MORE={daily:14,careers:8,tables:12};  // rows shown before "Xem thêm"; each click adds as many again

const store={
  get(k,d){try{const v=localStorage.getItem('pcc-admin-'+k);return v==null?d:JSON.parse(v);}catch{return d;}},
  set(k,v){try{localStorage.setItem('pcc-admin-'+k,JSON.stringify(v));}catch{/* private mode: keep in memory */}},
};

const ui={screen:'loading',view:'tong-quan',navOpen:false,login:{error:'',busy:false,replace:false,user:''},unread:null};
const stats={range:RANGES.includes(store.get('range',7))?store.get('range',7):7,byRange:{},busy:false,error:null,auto:store.get('auto',true)!==false,ctl:null,timer:0,retry:0,pending:false,
  sections:{saves:{data:null,at:0,busy:false,error:null},system:{data:null,at:0,busy:false,error:null},playtime:{data:null,at:0,busy:false,error:null},
    retention:{data:null,at:0,busy:false,error:null},invest:{data:null,at:0,busy:false,error:null}},more:{...MORE},
  inv:{tab:store.get('inv-tab','tong'),period:['7','30','90','0'].includes(String(store.get('inv-period','30')))?String(store.get('inv-period','30')):'30'},
  ret:{funnel:['today','yesterday','d7','d30'].includes(store.get('ret-funnel','d7'))?store.get('ret-funnel','d7'):'d7',src:'d7',err:'today'},
  live:{data:null,at:0,busy:false,error:null,ctl:null}};
let sectionsMod=null;  // ./sections.js once imported
const loadSectionsMod=()=>sectionsMod?Promise.resolve(sectionsMod):import('./sections.js').then(m=>(sectionsMod=m));
const chatAdmin=new ChatAdmin(api,{rerender:()=>{if(ui.screen==='app'&&ui.view==='chat')renderView();},forbidden:()=>reauth()});
const karaAdmin=new KaraAdmin(api,{rerender:()=>{if(ui.screen==='app'&&ui.view==='phong-hat')renderView();},forbidden:()=>reauth()});
const giftAdmin=new GiftAdmin(api,{rerender:()=>{if(ui.screen==='app'&&ui.view==='tang-xu')renderView();},forbidden:()=>reauth()});
const wiAdmin=new WedInviteAdmin(api,{rerender:()=>{if(ui.screen==='app'&&ui.view==='thiep-cuoi')renderView();},forbidden:()=>reauth()});
const usersAdmin=new UsersAdmin(api,{rerender:()=>{if(ui.screen==='app'&&ui.view==='nguoi-dung')renderView();},forbidden:()=>reauth()});
let retMod=null;  // ./retention.js once imported ("Giữ chân")
const loadRetMod=()=>retMod?Promise.resolve(retMod):import('./retention.js').then(m=>(retMod=m));
let invMod=null;  // ./invest.js once imported ("Tổng quan đầu tư" and its printable report)
const loadInvMod=()=>invMod?Promise.resolve(invMod):import('./invest.js').then(m=>(invMod=m));
const modFor=name=>name==='retention'?loadRetMod():name==='invest'?loadInvMod():loadSectionsMod();
const inbox=new Inbox(api,{
  rerender:()=>{if(ui.screen==='app'&&ui.view==='gop-y')renderView();},
  counts:c=>{ui.unread=c?.new??ui.unread;renderBadge();},
  forbidden:()=>reauth(),
});

/* ---- theme ------------------------------------------------------------------------ */
const media=matchMedia('(prefers-color-scheme: dark)');
function theme(){return document.documentElement.dataset.theme||(media.matches?'dark':'light');}
function applyTheme(t){if(t)document.documentElement.dataset.theme=t;else delete document.documentElement.dataset.theme;}
applyTheme(store.get('theme',null));
function themeButton(){
  const dark=theme()==='dark';
  return `<button type="button" class="side-btn" data-act="theme" aria-label="${dark?'Chuyển sang giao diện sáng':'Chuyển sang giao diện tối'}">${icon(dark?'sun':'moon',17)}<span>${dark?'Giao diện sáng':'Giao diện tối'}</span></button>`;
}

/* ---- auth ----------------------------------------------------------------------------- */
async function boot(){
  ui.screen='loading';render();
  try{await api.bootstrap();}
  catch(e){ui.screen='offline';ui.bootError=e.message;render();return;}
  decide();
}
function decide(){
  ui.screen=api.admin?'app':api.account?'denied':'login';
  if(ui.screen==='app'){route(false);ensureStats();}
  render();
}
/** A 401/403 from an admin endpoint: the session changed (signed out elsewhere, removed
 * from ADMIN_USERS, CSRF rotated). Ask the server again who we are. */
let reauthing=null;
function reauth(){
  usersAdmin.close(true,false);
  reauthing??=api.bootstrap().then(()=>{
    if(!api.admin)toast(api.account?'Tài khoản này không còn quyền vận hành.':'Phiên đăng nhập đã hết. Đăng nhập lại nhé.','bad');
    resetStats();inbox.reset();chatAdmin.reset();karaAdmin.reset();giftAdmin.reset();wiAdmin.reset();usersAdmin.reset();decide();
  }).catch(e=>toast(e.message,'bad')).finally(()=>{reauthing=null;});
  return reauthing;
}
async function login(form){
  const L=ui.login,user=form.username.value.trim(),pass=form.password.value;
  L.user=user;
  if(!user||!pass){L.error='Nhập tên đăng nhập và mật khẩu.';render();(user?form.password:form.username).focus();return;}
  if(L.busy)return;
  L.busy=true;L.error='';render();
  try{
    await api.login(user,pass,L.replace);
    ui.login={error:'',busy:false,replace:false,user:''};
    decide();
    if(api.admin)toast(`Chào @${api.account?.username||user}!`,'good');
    return;
  }catch(e){
    if(e.code==='confirm_replace'){L.replace=true;L.error='';}
    else if(e.status===403||e.code==='session_missing'){L.error='Phiên vừa được làm mới. Bấm đăng nhập lại nhé.';try{await api.bootstrap();}catch{/* the next try reports it */}}
    else L.error=e.message||'Không đăng nhập được. Thử lại nhé.';
  }
  L.busy=false;render();
  const pw=document.getElementById('login-pass');if(pw&&!L.replace){pw.value='';pw.focus();}else if(pw)pw.value=pass;
}
async function logout(){
  try{await api.logout();toast('Đã đăng xuất.');}
  catch(e){toast(e.message,'bad');}
  resetStats();inbox.reset();chatAdmin.reset();karaAdmin.reset();giftAdmin.reset();wiAdmin.reset();usersAdmin.reset();ui.unread=null;ui.navOpen=false;
  decide();
}

/* ---- stats data ----------------------------------------------------------------------- */
function resetStats(){
  stats.ctl?.abort();stats.ctl=null;clearTimeout(stats.timer);clearTimeout(stats.retry);stats.byRange={};stats.busy=false;stats.error=null;stats.pending=false;stats.retry=0;
  for(const s of Object.values(stats.sections)){s.ctl?.abort();clearTimeout(s.retry);Object.assign(s,{data:null,at:0,busy:false,error:null,ctl:null,retry:0,pending:false});}
  stats.live.ctl?.abort();Object.assign(stats.live,{data:null,at:0,busy:false,error:null,ctl:null});
}
const tooFast=e=>e.status===429?'Làm mới hơi dồn dập. Chờ một chút nhé.':e.message;
function ensureStats(){
  if(INVEST_VIEWS.has(ui.view)){ensureSection('invest');return;}
  const e=stats.byRange[stats.range];if(!e||Date.now()-e.at>REFRESH_MS)loadStats();
  if(ui.view==='tong-quan'&&(!stats.live.data||Date.now()-stats.live.at>LIVE_MS))loadLive();
  if(ui.view==='he-thong'){ensureSection('system');ensureSection('saves');}
  if(ui.view==='giu-chan')ensureSection('retention');
}
/** The first screen for the current range. A request still running for another range is aborted. */
function loadStats(fresh=false){
  const range=stats.range;
  if(stats.ctl&&stats.busyRange===range&&!fresh)return;
  stats.ctl?.abort();clearTimeout(stats.timer);clearTimeout(stats.retry);stats.retry=0;
  const ctl=stats.ctl=new AbortController();
  stats.busy=true;stats.busyRange=range;stats.error=null;renderTools();
  api.summary(range,{fresh,signal:ctl.signal})
    .then(d=>{
      // A cold/busy server answers {pending} while it computes in the background: keep the placeholders, ask again.
      if(d.pending){stats.pending=true;stats.retry=setTimeout(()=>{stats.retry=0;if(stats.range===range)loadStats();},Math.max(1500,d.retry_ms||3000));return;}
      stats.pending=false;stats.byRange[range]={data:d,at:Date.now()};api.setNames(d.names);ui.unread=d.feedback?.unread??ui.unread;renderBadge();})
    .catch(e=>{if(e.aborted)return;if(e.status===403||e.status===401){reauth();return;}stats.error=tooFast(e);})
    .finally(()=>{
      if(stats.ctl!==ctl)return;  // superseded: the newer request draws
      stats.ctl=null;stats.busy=false;
      if(ui.screen==='app'&&STATS_VIEWS.has(ui.view))renderView();else renderTools();
    });
}
/** The live counters. A failure keeps the last numbers on screen (with a short note). */
function loadLive(){
  const L=stats.live;if(L.busy)return;
  const ctl=L.ctl=new AbortController();L.busy=true;
  api.section('live',{signal:ctl.signal})
    .then(d=>{if(d.pending){L.error='Máy chủ đang bận, thử lại sau.';return;}L.data=d;L.at=Date.now();L.error=null;})
    .catch(e=>{if(e.aborted)return;if(e.status===403||e.status===401){reauth();return;}L.error=e.status?tooFast(e):e.message;})
    .finally(()=>{if(L.ctl!==ctl)return;L.busy=false;L.ctl=null;if(ui.screen==='app'&&ui.view==='tong-quan')renderLive();});
}
/** Redraw only the live band (the rest of the page, its open details and focus stay as they are). */
function renderLive(){
  const el=document.querySelector('#view .live');
  if(!el){renderView();return;}
  const tmp=document.createElement('div');tmp.innerHTML=liveView(stats.live.data,{error:stats.live.error});
  el.replaceWith(tmp.firstElementChild);
}
setInterval(()=>{
  if(ui.screen!=='app'||!stats.auto||ui.view!=='tong-quan'||document.hidden)return;
  loadLive();
},LIVE_MS);
function ensureSection(name){
  const s=stats.sections[name];
  if(s&&!s.busy&&!s.error&&!s.retry&&(!s.data||Date.now()-s.at>REFRESH_MS))loadSection(name);
}
/** A part loaded on demand (saves | system | playtime | retention); its renderer module is fetched alongside. */
function loadSection(name,fresh=false){
  const s=stats.sections[name];if(!s||s.busy)return;
  const ctl=s.ctl=new AbortController();
  s.busy=true;s.error=null;
  if(name==='retention'&&ui.view==='giu-chan'||name==='invest'&&INVEST_VIEWS.has(ui.view))renderTools();
  Promise.all([api.section(name,{fresh,signal:ctl.signal}),modFor(name)])
    .then(([d])=>{
      // First pass after a server restart still running: keep the placeholders, ask again.
      if(d.pending){s.pending=d.progress||true;s.retry=setTimeout(()=>{s.retry=0;loadSection(name);},Math.max(1000,d.retry_ms||3000));return;}
      s.data=d;s.at=Date.now();s.pending=false;if(d.names)api.setNames(d.names);
    })
    .catch(e=>{if(e.aborted)return;if(e.status===403||e.status===401){reauth();return;}s.error=e.status?tooFast(e):e.message||'Không tải được phần này.';})
    .finally(()=>{if(s.ctl!==ctl)return;s.busy=false;s.ctl=null;if(ui.screen==='app'&&STATS_VIEWS.has(ui.view))renderView();});
}
/** Sections worth refreshing on the current view (the saves cards show on both). */
const shown=name=>name==='invest'?INVEST_VIEWS.has(ui.view):INVEST_VIEWS.has(ui.view)?false:
  name==='retention'?ui.view==='giu-chan':name==='saves'||(name==='playtime'?ui.view==='tong-quan':ui.view==='he-thong');
setInterval(()=>{
  if(ui.screen!=='app'||!stats.auto||!STATS_VIEWS.has(ui.view)||document.hidden)return;
  if(!INVEST_VIEWS.has(ui.view))loadStats();
  for(const [name,s] of Object.entries(stats.sections))if(s.data&&shown(name))loadSection(name);
},REFRESH_MS);
/** Range buttons: the choice shows at once; the request goes out once the clicking settles. */
function pickRange(n){
  if(!RANGES.includes(n)||n===stats.range)return;
  stats.range=n;store.set('range',n);stats.error=null;
  stats.ctl?.abort();stats.ctl=null;stats.busy=false;clearTimeout(stats.timer);
  const e=stats.byRange[n];
  if(!e||Date.now()-e.at>REFRESH_MS){stats.busy=true;stats.busyRange=n;stats.timer=setTimeout(loadStats,RANGE_DEBOUNCE_MS);}
  renderView();
}
/* The save-derived cards load when one of their placeholders comes near the viewport. */
const lazyObserver='IntersectionObserver' in window?new IntersectionObserver(entries=>{
  for(const en of entries)if(en.isIntersecting){lazyObserver.unobserve(en.target);ensureSection(en.target.dataset.lazy);}
},{rootMargin:'200px 0px'}):null;
function watchLazy(view){
  lazyObserver?.disconnect();  // the previous placeholders were replaced
  view.querySelectorAll('[data-lazy]').forEach(el=>{if(lazyObserver)lazyObserver.observe(el);else ensureSection(el.dataset.lazy);});
}
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&ui.screen==='app'&&stats.auto&&STATS_VIEWS.has(ui.view))ensureStats();});

/* ---- routing -------------------------------------------------------------------------------- */
function route(focus=true){
  const h=location.hash.slice(1);
  ui.view=VIEWS[h]?h:'tong-quan';ui.navOpen=false;
  if(ui.screen!=='app')return;
  if(STATS_VIEWS.has(ui.view))ensureStats();
  render();
  if(focus){scrollTo(0,0);document.getElementById('view-title')?.focus({preventScroll:true});}
}
addEventListener('hashchange',()=>route(true));

/* ---- screens ---------------------------------------------------------------------------- */
const brand=(sub='Trang vận hành')=>`<div class="brand"><img src="/icons/logo-64.png" alt="" width="32" height="32"><span><b>Phố Có Chuyện</b><small>${sub}</small></span></div>`;

function loginView(){
  const L=ui.login;
  const confirm=L.replace?`<div class="notice warn" role="alert">${icon('alert',16)}<div><b>Trình duyệt này đang có tiến trình chơi chưa gắn tài khoản.</b> Đăng nhập sẽ thay nó bằng tiến trình của tài khoản vận hành. Bấm “Vẫn đăng nhập” nếu bạn đồng ý.</div></div>`:'';
  return `<main class="auth"><div class="auth-card">
    ${brand()}
    <h1>Đăng nhập vận hành</h1>
    <p class="muted">Dùng tài khoản game có quyền vận hành.</p>
    <form class="auth-form" data-form="login" novalidate>
      <label for="login-user">Tên đăng nhập</label>
      <input id="login-user" name="username" autocomplete="username" autocapitalize="none" autocorrect="off" spellcheck="false" maxlength="64" value="${esc(L.user)}" required>
      <label for="login-pass">Mật khẩu</label>
      <input id="login-pass" name="password" type="password" autocomplete="current-password" maxlength="128" required>
      ${L.error?`<div class="notice bad" role="alert">${icon('alert',16)}<div>${esc(L.error)}</div></div>`:''}
      ${confirm}
      <button class="btn primary full" type="submit"${L.busy?' disabled':''}>${icon('lock',16)} ${L.busy?'Đang kiểm tra…':L.replace?'Vẫn đăng nhập':'Đăng nhập'}</button>
      ${L.replace?'<button class="btn ghost full" type="button" data-act="cancelReplace">Thôi, không đăng nhập</button>':''}
    </form>
    <p class="auth-foot"><a href="/">← Về trang game</a><button type="button" class="link" data-act="theme">${theme()==='dark'?'Giao diện sáng':'Giao diện tối'}</button></p>
  </div></main>`;
}
function deniedView(){
  return `<main class="auth"><div class="auth-card">
    ${brand()}
    <div class="denied-mark">${icon('lock',26)}</div>
    <h1>Tài khoản này không có quyền vận hành</h1>
    <p class="muted">Bạn đang đăng nhập với <b>@${esc(api.account?.username||'')}</b>. Đăng xuất rồi đăng nhập bằng tài khoản vận hành nhé.</p>
    <button class="btn primary full" type="button" data-act="logout">${icon('exit',16)} Đăng xuất</button>
    <p class="note">Đăng xuất ở đây cũng đăng xuất khỏi game trên trình duyệt này.</p>
    <p class="auth-foot"><a href="/">← Về trang game</a></p>
  </div></main>`;
}
function offlineView(){
  return `<main class="auth"><div class="auth-card">${brand()}<div class="notice bad" role="alert">${icon('alert',16)}<div>${esc(ui.bootError||'Không kết nối được máy chủ.')}</div></div>
    <button class="btn primary full" type="button" data-act="retry">${icon('refresh',16)} Thử lại</button></div></main>`;
}
function appView(){
  const nav=Object.entries(VIEWS).filter(([id])=>!HIDDEN.has(id)).map(([id,[label,ic]])=>`<a href="#${id}" class="${ui.view===id?'on':''}"${ui.view===id?' aria-current="page"':''}>${icon(ic,18)}<span>${label}</span>${id==='gop-y'?'<span class="badge" data-badge hidden></span>':''}</a>`).join('');
  return `<div class="app${ui.navOpen?' nav-open':''}">
    <aside class="side">
      <div class="side-top">${brand('Vận hành')}<button type="button" class="menu-btn" data-act="nav" aria-expanded="${ui.navOpen}" aria-controls="side-menu" aria-label="${ui.navOpen?'Đóng menu':'Mở menu'}">${icon(ui.navOpen?'x':'menu',22)}</button></div>
      <div class="side-menu" id="side-menu">
        <nav class="nav" aria-label="Mục vận hành">${nav}</nav>
        <div class="side-foot">
          <div class="me">${icon('user',16)}<span><b>@${esc(api.account?.username||'')}</b><small>Người vận hành</small></span></div>
          ${themeButton()}
          <a class="side-btn" href="/" target="_blank" rel="noopener">${icon('external',17)}<span>Mở trang game</span></a>
          <button type="button" class="side-btn danger" data-act="logout">${icon('exit',17)}<span>Đăng xuất</span></button>
        </div>
      </div>
    </aside>
    <main class="main">
      <header class="main-head"><div class="title"><h1 id="view-title" tabindex="-1">${VIEWS[ui.view][0]}</h1><p class="meta" data-meta></p></div><div class="tools" data-tools></div></header>
      <div class="view" id="view"></div>
    </main>
  </div>`;
}

/* ---- rendering ----------------------------------------------------------------------------- */
function render(){
  root.removeAttribute('aria-busy');root.className='';
  if(ui.screen==='loading'){root.className='boot';root.innerHTML='<p class="boot-note">Đang mở trang vận hành…</p>';return;}
  if(ui.screen==='offline'){root.innerHTML=offlineView();return;}
  if(ui.screen==='login'){
    const had=document.activeElement?.id;
    root.innerHTML=loginView();
    const f=document.getElementById(had==='login-pass'||ui.login.error&&ui.login.user?'login-pass':'login-user');
    if(!ui.login.busy)f?.focus();
    return;
  }
  if(ui.screen==='denied'){root.innerHTML=deniedView();return;}
  root.innerHTML=appView();
  renderView();renderBadge();
}
function renderBadge(){
  const b=root.querySelector('[data-badge]');if(!b)return;
  b.hidden=!ui.unread;b.textContent=ui.unread>99?'99+':String(ui.unread||'');
  b.setAttribute('aria-label',`${num(ui.unread)} chưa đọc`);
}
function renderTools(){
  const tools=root.querySelector('[data-tools]'),meta=root.querySelector('[data-meta]');if(!tools)return;
  if(ui.view==='nguoi-dung'){
    tools.innerHTML=`<button type="button" class="btn ghost sm" data-act="usersReload"${usersAdmin.busy?' disabled':''}>${icon('refresh',15)}<span>Tải lại</span></button>`;
    meta.innerHTML=usersAdmin.meta();
    return;
  }
  if(ui.view==='phong-hat'){
    tools.innerHTML=`<button type="button" class="btn ghost sm" data-act="karaReload"${karaAdmin.busy?' disabled':''}>${icon('refresh',15)}<span>Tải lại</span></button>`;
    meta.innerHTML=karaAdmin.meta();
    return;
  }
  if(ui.view==='thiep-cuoi'){
    tools.innerHTML=`<button type="button" class="btn ghost sm" data-act="wiReload"${wiAdmin.busy?' disabled':''}>${icon('refresh',15)}<span>Tải lại</span></button>`;
    meta.innerHTML=wiAdmin.meta();
    return;
  }
  if(ui.view==='tang-xu'){
    tools.innerHTML=`<button type="button" class="btn ghost sm" data-act="giftReload"${giftAdmin.busy?' disabled':''}>${icon('refresh',15)}<span>Tải lại</span></button>`;
    meta.innerHTML=giftAdmin.meta();
    return;
  }
  if(ui.view==='chat'){
    tools.innerHTML=`<button type="button" class="btn ghost sm" data-act="chatReload"${chatAdmin.busy?' disabled':''}>${icon('refresh',15)}<span>Tải lại</span></button>`;
    meta.innerHTML=chatAdmin.meta();
    return;
  }
  if(ui.view==='gop-y'){
    tools.innerHTML=`<button type="button" class="btn ghost sm" data-act="fbReload"${inbox.busy?' disabled':''}>${icon('refresh',15)}<span>Tải lại</span></button>`;
    const c=inbox.data?.counts,total=c?Object.values(c).reduce((a,b)=>a+b,0):null;
    meta.innerHTML=c?`${num(total)} góp ý · <b>${num(c.new||0)}</b> chưa đọc · ${num(c.seen||0)} đã xem · ${num(c.done||0)} xong`:'Hộp thư góp ý của người chơi';
    return;
  }
  if(ui.view==='giu-chan'){
    const r=stats.sections.retention,d=r.data;
    tools.innerHTML=`<button type="button" class="btn ghost sm" data-act="retCsv"${d?'':' disabled'}>${icon('download',15)}<span>CSV</span></button>
      <label class="switch" title="Tự làm mới mỗi 60 giây"><input type="checkbox" data-act="auto"${stats.auto?' checked':''}><span class="knob" aria-hidden="true"></span><span>Tự làm mới</span></label>
      <button type="button" class="btn ghost sm" data-act="refresh"${r.busy?' disabled':''}>${icon('refresh',15)}<span>${r.busy?'Đang tải…':'Làm mới'}</span></button>`;
    meta.innerHTML=d?`Cập nhật ${hm(d.generated_at)}${d.cached&&d.age>5?` (bản đệm ${num(d.age)} giây)`:''} · giờ Việt Nam`:r.busy?'Đang tính số liệu…':'Người chơi rời đi ở đâu, lúc nào';
    return;
  }
  if(INVEST_VIEWS.has(ui.view)){
    const s=stats.sections.invest,d=s.data,rep=ui.view==='bao-cao';
    const per=`<div class="seg" role="radiogroup" aria-label="Kỳ tính">${[['7','7 ngày'],['30','30 ngày'],['90','90 ngày'],['0','Tất cả']].map(([v,l])=>`<button type="button" role="radio" aria-checked="${stats.inv.period===v}" class="${stats.inv.period===v?'on':''}" data-act="invPeriod" data-value="${v}">${l}</button>`).join('')}</div>`;
    const part=rep?'all':invMod?.PART?.[stats.inv.tab]||'all';
    tools.innerHTML=`${per}
      <button type="button" class="btn ghost sm" data-act="invCsv" data-part="${part}"${d?'':' disabled'} title="${part==='all'?'Mọi phần trong một tệp CSV':'CSV của phần đang xem'}">${icon('download',15)}<span>CSV</span></button>
      ${rep?`<button type="button" class="btn primary sm" data-act="print"${d?'':' disabled'}>${icon('print',15)}<span>In / Lưu PDF</span></button><a class="btn ghost sm" href="#dau-tu">${icon('back',15)}<span>Quay lại</span></a>`
        :`<a class="btn ghost sm" href="#bao-cao"${d?'':' aria-disabled="true"'}>${icon('print',15)}<span>Xuất báo cáo</span></a>`}
      <button type="button" class="btn ghost sm" data-act="refresh"${s.busy?' disabled':''}>${icon('refresh',15)}<span>${s.busy?'Đang tải…':'Làm mới'}</span></button>`;
    meta.innerHTML=d?`Số liệu lúc ${hm(d.generated_at)} · giờ Việt Nam · tính nền mỗi 10 phút khi trang mở${d.next_in?` (lần sau ~${num(Math.ceil(d.next_in/60))} phút)`:''}`:s.busy?'Đang tính số liệu…':'Số liệu cho nhà đầu tư, người mua hoặc nhận nhượng quyền';
    return;
  }
  const e=stats.byRange[stats.range],d=e?.data,busy=stats.busy||(ui.view==='he-thong'&&stats.sections.system.busy);
  const seg=ui.view==='tong-quan'?`<div class="seg" role="radiogroup" aria-label="Khoảng thời gian">${RANGES.map(n=>`<button type="button" role="radio" aria-checked="${stats.range===n}" class="${stats.range===n?'on':''}" data-act="range" data-range="${n}">${n} ngày</button>`).join('')}</div>`:'';
  tools.innerHTML=`${seg}
    <label class="switch" title="Tự làm mới mỗi 60 giây"><input type="checkbox" data-act="auto"${stats.auto?' checked':''}><span class="knob" aria-hidden="true"></span><span>Tự làm mới</span></label>
    <button type="button" class="btn ghost sm" data-act="refresh"${busy?' disabled':''}>${icon('refresh',15)}<span>${busy?'Đang tải…':'Làm mới'}</span></button>`;
  const at=d?.computed_at??d?.generated_at;
  meta.innerHTML=d?`Cập nhật ${hm(at)}${d.stale?` (bản tính nền, ${ago(at)})`:d.cached&&d.age>5?` (bản đệm ${num(d.age)} giây)`:''} · ${d.range} ngày · giờ Việt Nam${stats.auto?' · tự làm mới mỗi phút':''}`:stats.busy?'Đang tính số liệu…':'';
}
function renderView(){
  const view=document.getElementById('view');if(!view)return;
  const open=new Set([...view.querySelectorAll('details[open] > summary')].map(s=>s.textContent));
  const focusAct=document.activeElement?.closest?.('#view')?document.activeElement.dataset.act+'|'+(document.activeElement.dataset.id||'')+'|'+(document.activeElement.dataset.status||document.activeElement.dataset.value||''):null;
  if(ui.view==='nguoi-dung')view.innerHTML=usersAdmin.view();
  else if(ui.view==='gop-y')view.innerHTML=inbox.view();
  else if(ui.view==='chat')view.innerHTML=chatAdmin.view();
  else if(ui.view==='tang-xu')view.innerHTML=giftAdmin.view();
  else if(ui.view==='thiep-cuoi')view.innerHTML=wiAdmin.view();
  else if(ui.view==='phong-hat')view.innerHTML=karaAdmin.view();
  else if(ui.view==='giu-chan')view.innerHTML=`<div class="stats ret${stats.sections.retention.busy&&stats.sections.retention.data?' is-busy':''}">${retentionBody()}</div>`;
  else if(INVEST_VIEWS.has(ui.view))view.innerHTML=`<div class="stats inv-view${stats.sections.invest.busy&&stats.sections.invest.data?' is-busy':''}">${investBody()}</div>`;
  else{
    const e=stats.byRange[stats.range],d=e?.data;
    let body;
    if(stats.error&&!d)body=`<div class="notice bad">${icon('alert',16)}<div>${esc(stats.error)}<br><button type="button" class="btn ghost sm" data-act="refresh">Thử lại</button></div></div>`;
    else if(!d)body=(ui.view==='tong-quan'?live():'')+(stats.pending?`<p class="note">Máy chủ đang bận nên số liệu được tính ở chế độ nền, chờ chút nhé…</p>`:'')+(ui.view==='he-thong'?systemSkeleton():skeleton());
    else body=(stats.error?`<div class="notice warn">${icon('alert',16)}<div>${esc(stats.error)} Đang hiện số liệu cũ.</div></div>`:'')+(ui.view==='he-thong'?systemBody(d):overviewView(d,{...savesParts(),playtime:playtimePart()},stats.more,stats.live));
    view.innerHTML=`<div class="stats${stats.busy&&d?' is-busy':''}" aria-busy="${stats.busy}">${body}</div>`;
    view.querySelectorAll('details > summary').forEach(s=>{if(open.has(s.textContent))s.parentElement.open=true;});
    watchLazy(view);
  }
  if(focusAct){const [act,id,val]=focusAct.split('|');const el=[...view.querySelectorAll(`[data-act="${act}"]`)].find(x=>(x.dataset.id||'')===id&&((x.dataset.status||x.dataset.value||'')===val));el?.focus({preventScroll:true});}
  renderTools();
}

const live=()=>liveView(stats.live.data,{error:stats.live.error});
/** The four save-derived cards: drawn by ./sections.js once loaded, else placeholders. */
function savesParts(){
  const s=stats.sections.saves;
  if(s.data&&sectionsMod)return sectionsMod.savesCards(s.data,id=>api.career(id),stats.more);
  const err=s.error&&!s.busy?s.error:'';
  const p=s.pending,read=p&&p.total?` (đã đọc ${num(p.done)}/${num(p.total)})`:'';
  const ph=title=>skelCard(title,{lazy:'saves',error:err,note:p?`Máy chủ đang đọc các lượt chơi lần đầu${read}, chờ chút nhé…`:''});
  return {careers:ph('Nghề được chơi nhiều'),economy:ph('Kinh tế'),play:ph('Cách chơi'),life:ph('Đời sống & Nhóm cư dân'),foot:''};
}
/** "Thời gian chơi": drawn by ./sections.js once loaded, else a placeholder loaded on scroll. */
function playtimePart(){
  const s=stats.sections.playtime;
  if(s.data&&sectionsMod)return sectionsMod.playtimeCard(s.data);
  const err=s.error&&!s.busy?s.error:'';
  return skelCard('Thời gian chơi',{lazy:'playtime',error:err,note:s.pending?'Máy chủ đang cộng số liệu các ngày trước, chờ chút nhé…':''});
}
/** "Giữ chân": drawn by ./retention.js once loaded, else placeholders (or the error with a retry). */
function retentionBody(){
  const s=stats.sections.retention;
  if(s.data&&retMod)return retMod.retentionView(s.data,stats.ret,id=>api.career(id));
  if(s.error&&!s.busy)return `<div class="notice bad">${icon('alert',16)}<div>${esc(s.error)}<br><button type="button" class="btn ghost sm" data-act="retrySection" data-name="retention">Thử lại</button></div></div>`;
  const k=`<div class="kpi skel-kpi"><span class="kpi-label">&nbsp;</span><b class="kpi-num">&nbsp;</b><small class="kpi-sub">&nbsp;</small></div>`;
  return (s.pending?'<p class="note">Máy chủ đang tính số liệu, chờ chút nhé…</p>':'')+`<div class="kpis k4 skel" aria-hidden="true">${k.repeat(4)}</div>${skelCard('Quay lại theo ngày bắt đầu',{lines:6})}<div class="cols"><div class="col">${skelCard('Phễu người mới',{lines:8})}</div><div class="col">${skelCard('Trước và sau 0.9.16')}${skelCard('Theo nghề')}</div></div>`;
}
/** "Tổng quan đầu tư" / its printable report: drawn by ./invest.js once loaded, else placeholders. */
function investBody(){
  const s=stats.sections.invest;
  if(s.data&&invMod){
    const name=id=>api.career(id);
    return ui.view==='bao-cao'?invMod.reportView(s.data,stats.inv,name):invMod.investView(s.data,stats.inv,name);
  }
  if(s.error&&!s.busy)return `<div class="notice bad">${icon('alert',16)}<div>${esc(s.error)}<br><button type="button" class="btn ghost sm" data-act="retrySection" data-name="invest">Thử lại</button></div></div>`;
  const k=`<div class="kpi skel-kpi"><span class="kpi-label">&nbsp;</span><b class="kpi-num">&nbsp;</b><small class="kpi-sub">&nbsp;</small></div>`;
  return (s.pending?'<p class="note">Máy chủ đang tính số liệu lần đầu (chạy nền, không ảnh hưởng người chơi), chờ chút nhé…</p>':'')+
    `<div class="kpis k4 skel" aria-hidden="true">${k.repeat(8)}</div>${skelCard('Người hoạt động mỗi ngày',{lines:6})}`;
}
/** A CSV of the stats endpoint (it needs the CSRF header, so no plain link). */
async function downloadCsv(btn,query,file){
  btn.disabled=true;
  try{
    const res=await fetch(`/api/admin/stats/section?${query}&format=csv`,{credentials:'same-origin',cache:'no-store',headers:{'X-Game-CSRF':api.csrf}});
    if(!res.ok)throw new Error(res.status===429?'Chờ một chút rồi thử lại nhé.':res.status===503?'Số liệu đang được tính, thử lại sau ít phút nhé.':`Lỗi ${res.status}`);
    const url=URL.createObjectURL(await res.blob()),a=document.createElement('a');
    a.href=url;a.download=file;document.body.append(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),10000);
  }catch(e){toast(e.message||'Không tải được CSV.','bad');}
  finally{btn.disabled=false;}
}
const retentionCsv=btn=>downloadCsv(btn,'name=retention',`giu-chan-${stats.sections.retention.data?.today||'hom-nay'}.csv`);
const investCsv=btn=>{const part=btn.dataset.part||'all';return downloadCsv(btn,`name=invest&part=${encodeURIComponent(part)}`,`tong-quan-dau-tu-${part}-${stats.sections.invest.data?.today||'hom-nay'}.csv`);};
function systemSkeleton(){
  return `<div class="kpis k4 skel" aria-hidden="true">${'<div class="kpi skel-kpi"><span class="kpi-label">&nbsp;</span><b class="kpi-num">&nbsp;</b><small class="kpi-sub">&nbsp;</small></div>'.repeat(4)}</div>`+
    `<div class="cols"><div class="col">${skelCard('Bảng dữ liệu',{lines:8})}</div><div class="col">${skelCard('Môi trường')}${skelCard('Số liệu thống kê')}</div></div>`;
}
function systemBody(d){
  const sys=stats.sections.system;
  if(sys.data&&sectionsMod)return sectionsMod.systemView(d,sys.data,stats.sections.saves.data,api,stats.more);
  if(sys.error&&!sys.busy)return `<div class="notice bad">${icon('alert',16)}<div>${esc(sys.error)}<br><button type="button" class="btn ghost sm" data-act="retrySection" data-name="system">Thử lại</button></div></div>`;
  return systemSkeleton();
}

/* ---- events -------------------------------------------------------------------------------- */
root.addEventListener('click',async ev=>{
  const go=ev.target.closest('[data-go]');
  if(go){location.hash=go.dataset.go;return;}
  if(ev.target.closest('.nav a')&&ui.navOpen){ui.navOpen=false;}
  const el=ev.target.closest('[data-act]');if(!el||el.tagName==='INPUT')return;
  const act=el.dataset.act;
  switch(act){
    case'theme':{const t=theme()==='dark'?'light':'dark';applyTheme(t);store.set('theme',t);render();return;}
    case'nav':ui.navOpen=!ui.navOpen;render();return;
    case'logout':el.disabled=true;await logout();return;
    case'retry':boot();return;
    case'cancelReplace':ui.login.replace=false;ui.login.error='';render();return;
    case'range':pickRange(Number(el.dataset.range));return;
    case'refresh':{
      stats.error=null;if(!INVEST_VIEWS.has(ui.view))loadStats(true);if(ui.view==='tong-quan')loadLive();
      for(const [name,s] of Object.entries(stats.sections))if(s.data&&shown(name)){s.error=null;loadSection(name,true);}
      return;
    }
    case'retrySection':{const s=stats.sections[el.dataset.name];if(!s)return;s.error=null;loadSection(el.dataset.name);renderView();return;}
    case'retSeg':{const k=el.dataset.key,v=el.dataset.value;if(!(k in stats.ret))return;stats.ret[k]=v;if(k==='funnel')store.set('ret-funnel',v);renderView();return;}
    case'retCsv':retentionCsv(el);return;
    case'invCsv':investCsv(el);return;
    case'invTab':{const v=el.dataset.value;if(!invMod?.TABS.some(([k])=>k===v))return;stats.inv.tab=v;store.set('inv-tab',v);renderView();
      document.querySelector('.tabs [aria-current]')?.focus({preventScroll:true});return;}
    case'invPeriod':{const v=el.dataset.value;if(!['7','30','90','0'].includes(v))return;stats.inv.period=v;store.set('inv-period',v);renderView();return;}
    case'info':showTip(el,true);return;
    case'print':print();return;
    case'more':{const k=el.dataset.key;if(!(k in MORE))return;stats.more[k]+=MORE[k];renderView();return;}
    case'fbReload':inbox.reset();renderView();return;
  }
  if(usersAdmin.action(act,el.dataset,el))return;
  if(giftAdmin.action(act,el.dataset,el))return;
  if(await karaAdmin.action(act,el.dataset))return;
  if(await wiAdmin.action(act,el.dataset))return;
  if(await chatAdmin.action(act,el.dataset))return;
  await inbox.action(act,el.dataset);
});
root.addEventListener('change',ev=>{
  if(ev.target.dataset.act==='auto'){stats.auto=ev.target.checked;store.set('auto',stats.auto);if(stats.auto)ensureStats();renderTools();}
});
root.addEventListener('input',ev=>{usersAdmin.input(ev.target);inbox.input(ev.target);});
root.addEventListener('submit',async ev=>{
  ev.preventDefault();
  const f=ev.target;
  if(f.dataset.form==='login'){await login(f);return;}
  if(usersAdmin.submit(f))return;
  if(giftAdmin.submit(f))return;
  if(await chatAdmin.submit(f))return;
  await inbox.submit(f);
});
addEventListener('keydown',ev=>{if(ev.key==='Escape'&&ui.navOpen){ui.navOpen=false;render();}});
media.addEventListener?.('change',()=>{if(!document.documentElement.dataset.theme&&ui.screen==='app')render();});

/* Hover tooltip for chart bars ([data-tip]); a single floating element. */
const tip=document.createElement('div');tip.className='tip';tip.setAttribute('role','presentation');tip.hidden=true;document.body.append(tip);
/* The ⓘ buttons (.info) carry long definitions: a wider, wrapping tip, also shown on tap and keyboard focus
 * (phones have no hover); it stays until the next tap elsewhere. */
let tipPinned=null;
function showTip(t,pin=false){
  tip.textContent=t.dataset.tip;tip.classList.toggle('wide',t.classList.contains('info'));tip.hidden=false;
  const r=t.getBoundingClientRect(),w=tip.offsetWidth,h=tip.offsetHeight;
  tip.style.left=`${Math.max(8,Math.min(innerWidth-w-8,r.left+r.width/2-w/2))}px`;
  tip.style.top=`${r.top-h-6<8?Math.min(innerHeight-h-8,r.bottom+6):r.top-h-6}px`;
  tipPinned=pin?t:null;
}
root.addEventListener('pointerover',ev=>{
  const t=ev.target.closest('[data-tip]');if(!t){if(!tipPinned)tip.hidden=true;return;}
  showTip(t,tipPinned===t);
});
root.addEventListener('pointerdown',ev=>{if(tipPinned&&!ev.target.closest('.info')){tipPinned=null;tip.hidden=true;}});
root.addEventListener('focusin',ev=>{const t=ev.target.closest?.('.info[data-tip]');if(t)showTip(t,true);});
root.addEventListener('focusout',ev=>{if(ev.target===tipPinned){tipPinned=null;tip.hidden=true;}});
root.addEventListener('pointerleave',()=>{if(!tipPinned)tip.hidden=true;});
addEventListener('scroll',()=>{tip.hidden=true;tipPinned=null;},{passive:true});

boot();
