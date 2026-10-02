/** "Có gì mới": a centred card with the release notes (game/whats_new.py →
 * whatsnew-data.js). It opens by itself once per release for returning players,
 * after the game is up, and any time from Cài đặt → Cách chơi → "Có gì mới".
 *
 * - What the player has read is settings.whatsNewSeen in the save, so it
 *   follows the account across devices. localStorage only stands in while the
 *   save has no such key (an older server).
 * - A notice for returning players: it waits for a break point (v4/popup-gate.js): never over the
 *   day summary, a customer on the work screen, the tutorial or another card, and after a
 *   🎁 gift card. A brand-new player never gets it: naming the character marks
 *   the current notes as read on the server (journey._welcome_settings), and a save
 *   still in its first life day is marked here, silently (older saves named before that).
 * - Modal dialog: focus stays inside, Esc closes, a backdrop tap does nothing
 *   (no accidental dismissal), a tap in the first moment after it pops up is
 *   ignored, reduced motion is respected.
 * app.js loads this module lazily after the first frame (whatsNewBoot); the
 * settings button carries data-action="whatsNew", handled here. */
import NOTES from './whatsnew-data.js';
import {language} from './i18n.js';
import {icon,escapeHTML as esc} from '../icons.js';
import {firstDay} from './onboard.js';
import {why,turn,want} from './popup-gate.js';

const KEY='mnl.wn.seen';
const VERSION=/^\d{1,3}(\.\d{1,3}){1,2}$/;
const parse=v=>{const p=String(v).split('.').map(Number);while(p.length<3)p.push(0);return p;};
/** <0, 0, >0 like a sort; "" is older than any release. */
export function compare(a,b){
  if(!a||!b)return (a?1:0)-(b?1:0);
  const x=parse(a),y=parse(b);
  for(let i=0;i<3;i++)if(x[i]!==y[i])return x[i]-y[i];
  return 0;
}
export const LATEST=NOTES[0]?.version||'';

const store={
  get(){try{const v=localStorage.getItem(KEY)||'';return VERSION.test(v)?v:'';}catch{return '';}},
  set(v){try{localStorage.setItem(KEY,v);}catch{/* storage blocked */}},
};
/** The release this player has read up to: the save's value; localStorage only when the save has none. */
export function seenVersion(state){
  const v=state?.settings?.whatsNewSeen;
  return typeof v==='string'?v:store.get();
}
/** A release the player has not read yet exists. */
export const due=state=>!!LATEST&&compare(LATEST,seenVersion(state))>0;

let E=null,timer=0,calmTicks=0,dlg=null,auto=false,openedAt=0,back=null,older=false,done=false,sent='',cssReady=null;
const reduced=()=>document.documentElement.classList.contains('reduce-motion')||document.body.classList.contains('reduce-motion')||matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Why the card has to wait right now ('' = it may open): loading, a hidden tab, naming the
 * character, the tutorial (the tour or its welcome card), then the shared popup rule
 * (v4/popup-gate.js: another card or question, the day summary, the evening, a customer at work,
 * the phone menu, a gift card still to come). The first day is fine. */
export function blocker(env=E,doc=document){
  const s=env?.api?.state;if(!s)return 'loading';
  const J=s.journey;
  if(J?.story&&!J.intro)return 'intro';                   // naming the character, first steps in the street
  if(doc.hidden)return 'hidden';
  if(doc.getElementById('tutLayer')?.isConnected)return 'tour';
  for(const d of doc.querySelectorAll('dialog[open]')){
    if(d!==dlg&&String(d.id||'').startsWith('tut'))return 'tour';   // the tutorial's welcome card
  }
  return why(dlg,{strict:false},doc)||(turn('whatsnew')?'':'turn');
}

/* ------------------------------------------------------------ markup */
function when(date){
  const [y,m,d]=String(date).split('-').map(Number);
  if(!y||!m||!d)return esc(date);
  const text=language()==='en'
    ?new Date(Date.UTC(y,m-1,d)).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'})
    :`${String(d).padStart(2,'0')}/${String(m).padStart(2,'0')}/${y}`;
  return `<time datetime="${esc(date)}">${text}</time>`;
}
const stamp=n=>`<span>Bản ${esc(n.version)}</span><span aria-hidden="true"> · </span>${when(n.date)}`;
/** A "Thử ngay" target is live when the game shows a control with that action somewhere (rail, menu, sheet). */
const control=go=>go?.action?document.querySelector(`[data-action="${CSS.escape(go.action)}"]`):null;
function items(n,ni){
  return `<ul class="wn-list">${n.items.map((it,i)=>{
    const tryIt=control(it.go)?`<button type="button" class="btn small wn-try" data-wn-go="${ni}:${i}">Thử ngay</button>`:'';
    return `<li class="wn-item"><span class="wn-emoji" aria-hidden="true">${esc(it.emoji)}</span><div class="wn-line"><p>${esc(it.text)}</p>${tryIt}</div></li>`;
  }).join('')}</ul>`;
}
function html(){
  const seen=seenVersion(E?.api?.state);
  // Opened by itself: every release not read yet (up to two), newest first. From Settings: the latest.
  let fresh=auto?NOTES.filter(n=>compare(n.version,seen)>0).slice(0,2):[];
  if(!fresh.length)fresh=NOTES.slice(0,1);
  const rest=NOTES.filter(n=>!fresh.includes(n)),top=fresh[0];
  const more=fresh.slice(1).map(n=>`<section class="wn-block"><h3 class="wn-sub">${stamp(n)}</h3>${items(n,NOTES.indexOf(n))}</section>`).join('');
  const old=rest.length?`<button type="button" class="wn-more" data-wn="older" aria-expanded="${older}" aria-controls="wnOlder">${older?'Ẩn các bản trước':'Xem các bản trước'}</button>`+
    `<div id="wnOlder" class="wn-older"${older?'':' hidden'}>${rest.map(n=>`<section class="wn-block"><h3 class="wn-sub">${stamp(n)}</h3>${items(n,NOTES.indexOf(n))}</section>`).join('')}</div>`:'';
  return `<header class="wn-head"><span class="wn-spark" aria-hidden="true">✨</span><div class="grow"><h2 id="wnTitle">Có gì mới ở Phố Có Chuyện</h2><p class="wn-meta" id="wnMeta">${stamp(top)}</p></div>`+
    `<button type="button" class="icon-btn wn-x" data-wn="close" aria-label="Đóng">${icon('x',22)}</button></header>`+
    `<div class="wn-body">${items(top,NOTES.indexOf(top))}${more}${old}</div>`+
    `<footer class="wn-foot"><button type="button" class="btn primary big full" data-wn="close">Đã hiểu</button></footer>`;
}

/* ------------------------------------------------------------ dialog */
const focusables=()=>[...dlg.querySelectorAll('button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])')].filter(el=>!el.disabled&&el.offsetParent!==null);
function build(){
  if(dlg)return dlg;
  dlg=document.createElement('dialog');dlg.id='wnDialog';dlg.className='wn-dialog';
  dlg.setAttribute('aria-modal','true');dlg.setAttribute('aria-labelledby','wnTitle');dlg.setAttribute('aria-describedby','wnMeta');
  dlg.innerHTML='<div class="wn-card"></div>';
  document.body.append(dlg);
  dlg.addEventListener('click',onClick);
  dlg.addEventListener('cancel',e=>{e.preventDefault();close();});   // Esc
  dlg.addEventListener('keydown',e=>{
    if(e.key==='Escape'){e.preventDefault();close();return;}
    if(e.key!=='Tab')return;
    const f=focusables();if(!f.length){e.preventDefault();return;}
    const first=f[0],last=f[f.length-1],at=document.activeElement;
    if(e.shiftKey&&(at===first||at===dlg||!dlg.contains(at))){e.preventDefault();last.focus();}
    else if(!e.shiftKey&&(at===last||!dlg.contains(at))){e.preventDefault();first.focus();}
  });
  return dlg;
}
function render(){dlg.querySelector('.wn-card').innerHTML=html();}
function onClick(e){
  const b=e.target.closest('button');if(!b||!dlg.contains(b))return;
  // A tap already on its way when the card popped up must not close it unread.
  if(auto&&performance.now()-openedAt<450){e.preventDefault();return;}
  if(b.dataset.wn==='close'){close();return;}
  if(b.dataset.wn==='older'){
    older=!older;render();
    const t=older?dlg.querySelector('#wnOlder .wn-sub'):null;
    dlg.querySelector('[data-wn="older"]')?.focus({preventScroll:true});
    if(t)t.scrollIntoView({block:'start',behavior:reduced()?'auto':'smooth'});
    return;
  }
  if(b.dataset.wnGo){
    const [ni,i]=b.dataset.wnGo.split(':').map(Number),go=NOTES[ni]?.items?.[i]?.go;
    close(false);
    if(go)setTimeout(()=>tryIt(go),60);
  }
}
/** Press the game's own control for this feature (with its data when the note gives some). */
function tryIt(go){
  const el=control(go);if(!el)return;
  if(!go.data||!Object.keys(go.data).length){el.click();return;}
  const b=document.createElement('button');b.type='button';b.hidden=true;b.dataset.action=go.action;
  for(const [k,v] of Object.entries(go.data))b.dataset[k]=v;
  document.body.append(b);b.click();setTimeout(()=>b.remove(),1500);
}

export async function openWhatsNew(env=E,{byItself=false}={}){
  E=env||E;if(!NOTES.length)return;
  await cssReady;
  build();auto=byItself;older=false;back=document.activeElement;
  render();
  if(!dlg.open)dlg.showModal();
  openedAt=performance.now();
  dlg.querySelector('.wn-body').scrollTop=0;
  dlg.tabIndex=-1;dlg.focus({preventScroll:true});   // no focus ring on the first paint; Tab moves into the card
  if(auto)markSeen();
}
function close(restore=true){
  if(!dlg?.open)return;
  markSeen();dlg.close();
  if(restore&&back?.isConnected&&typeof back.focus==='function')back.focus({preventScroll:true});
  back=null;
}
/** Remember the latest release as read: in the save (follows the account), and locally as a stand-in. */
function markSeen(){
  done=true;stopWatch();want('whatsnew',false);
  const st=E?.api?.state;if(!LATEST||!st)return;
  store.set(LATEST);
  if(sent===LATEST||compare(LATEST,st.settings?.whatsNewSeen||'')<=0)return;
  sent=LATEST;
  E.api.command('settings',{whatsNewSeen:LATEST},st.current||st.focus).catch(()=>{});   // an older server only loses the sync
}

/** A named save in its first life day is a new player: the notes count as read, and nothing opens. */
function newcomer(){
  const s=E?.api?.state,J=s?.journey;
  if(!due(s)||!firstDay(s)||!(J?.intro||J?.gender)||dlg?.open)return;
  markSeen();
}

/* ------------------------------------------------------------ watching */
function check(){
  if(done||!due(E?.api?.state)){stopWatch();want('whatsnew',false);return;}
  // Two calm checks in a row (about a second): never in the gap between two sheets.
  if(blocker()){calmTicks=0;return;}
  if(++calmTicks<2)return;
  stopWatch();openWhatsNew(E,{byItself:true});
}
function stopWatch(){clearInterval(timer);timer=0;}
function loadCss(){
  if(cssReady)return cssReady;
  const href=globalThis.__mnlBoot?.asset?.('/css/whatsnew.css')||'/css/whatsnew.css';
  const have=document.querySelector('link[data-wn-css]');
  if(have)return cssReady=Promise.resolve();
  const l=document.createElement('link');l.rel='stylesheet';l.href=href;l.dataset.wnCss='1';
  cssReady=new Promise(done=>{l.onload=l.onerror=()=>done();setTimeout(done,4000);});
  document.head.append(l);
  return cssReady;
}

/** Called once by app.js after the game is on screen. */
export function whatsNewBoot(env){
  try{
    E=env;loadCss();
    document.addEventListener('click',e=>{
      const b=e.target.closest?.('[data-action="whatsNew"]');if(!b||b.disabled)return;
      e.preventDefault();e.stopImmediatePropagation();   // handled here, not by app.js
      openWhatsNew(E);
    },true);
    if(due(env.api?.state)){stopWatch();calmTicks=0;want('whatsnew');timer=setInterval(check,700);}
    env.api?.addEventListener?.('state',newcomer);newcomer();
  }catch(error){console.error('whatsnew:',error);}   // never in the way of the game
}
