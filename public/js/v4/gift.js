/** 🎁 "Quà từ Phố Có Chuyện" (game/system_gift.py): a private gift the operator sent to this save,
 * e.g. an apology after an outage. The server already put the coins in the wallet at load; the
 * bootstrap lists the gifts not acknowledged yet (api.gifts: id, coins, title, text).
 *
 * - One centred card per gift, one after another: the title, a big "🎁 +100 xu", the text and one
 *   button "Nhận quà 💛". The button POSTs /api/gift/seen, so the card never comes back, on any device.
 * - Same modal rules as "Có gì mới" (whatsnew.js): focus stays inside, a backdrop tap does nothing,
 *   a tap in the first moment after it pops up is ignored, reduced motion is respected. Esc counts as
 *   the button (the coins are in the wallet either way).
 * - It waits for the game to be on screen, naming the character, a new player's first 3 customers,
 *   the tutorial, and a break point (v4/popup-gate.js): no other card or question open, not over the
 *   day summary or a customer at work. It comes first of the cards that open by themselves.
 * app.js imports this module only when the bootstrap carried a gift. */
import {escapeHTML as esc} from '../icons.js';
import {quiet} from './onboard.js';
import {why,want} from './popup-gate.js';

let E=null,queue=[],dlg=null,timer=0,calm=0,openedAt=0,back=null,cssReady=null;
const fmt=n=>Number(n||0).toLocaleString('vi-VN');

/** Why the card has to wait right now ('' = it may open). */
export function blocker(env=E,doc=document){
  const s=env?.api?.state;if(!s)return 'loading';
  if(s.journey?.story&&!s.journey.intro)return 'intro';
  if(quiet(s))return 'first-customers';                   // a brand-new player's first 3 customers (v4/onboard.js)
  if(doc.hidden)return 'hidden';
  if(doc.getElementById('tutLayer')?.isConnected)return 'tour';
  for(const d of doc.querySelectorAll('dialog[open]')){
    if(d===dlg)continue;
    if(String(d.id||'').startsWith('tut'))return 'tour';
    if(d.id==='wnDialog')return 'whatsnew';
  }
  return why(dlg,{strict:false},doc);
}

function html(g){
  const more=queue.length>1?`<p class="gf-count" aria-hidden="true">1/${queue.length}</p>`:'';
  return `${more}<div class="gf-top"><p class="gf-title" id="gfTitle">${esc(g.title)}</p>`+
    `<p class="gf-amount"><span class="gf-box" aria-hidden="true">🎁</span><span>+${fmt(g.coins)} xu</span></p>`+
    `<p class="gf-where">Đã vào ví của bạn 👛</p></div>`+
    `<p class="gf-text" id="gfText">${esc(g.text)}</p>`+
    `<div class="gf-foot"><button type="button" class="btn primary big full" data-gf="ok">Nhận quà 💛</button></div>`;
}

function build(){
  if(dlg)return dlg;
  dlg=document.createElement('dialog');dlg.id='gfDialog';dlg.className='gf-dialog';
  dlg.setAttribute('aria-modal','true');dlg.setAttribute('aria-labelledby','gfTitle');dlg.setAttribute('aria-describedby','gfText');
  dlg.innerHTML='<div class="gf-card"></div>';
  document.body.append(dlg);
  dlg.addEventListener('click',e=>{
    const b=e.target.closest('button');if(!b||!dlg.contains(b))return;
    if(performance.now()-openedAt<450){e.preventDefault();return;}   // a tap already on its way when the card popped up
    if(b.dataset.gf==='ok')accept();
  });
  dlg.addEventListener('cancel',e=>{e.preventDefault();accept();});   // Esc
  dlg.addEventListener('keydown',e=>{if(e.key==='Tab'){e.preventDefault();dlg.querySelector('[data-gf="ok"]')?.focus();}});   // one button
  return dlg;
}

async function show(){
  const g=queue[0];if(!g)return;
  await cssReady;
  build();back??=document.activeElement;
  dlg.querySelector('.gf-card').innerHTML=html(g);
  if(!dlg.open)dlg.showModal();
  openedAt=performance.now();
  dlg.tabIndex=-1;dlg.focus({preventScroll:true});   // no focus ring on the first paint; Tab reaches the button
}

/** "Nhận quà": this card is read. The ack is idempotent, so it is retried through a restart; if it
 * still fails the card simply comes back on the next load (the coins are already in the wallet). */
function accept(){
  const g=queue[0];if(!g)return;
  const api=E?.api;
  const ack=api?api.json('/api/gift/seen',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify({id:g.id}),retry:true}):Promise.resolve();
  ack.catch(e=>console.warn('gift seen:',e));
  queue.shift();
  if(api)api.gifts=queue.slice();
  if(queue.length){show();return;}
  want('gift',false);dlg.close();
  if(back?.isConnected&&typeof back.focus==='function')back.focus({preventScroll:true});
  back=null;
}

function check(){
  if(!queue.length){stop();want('gift',false);return;}
  // Two calm checks in a row (about a second): never in the gap between two sheets.
  if(blocker()){calm=0;return;}
  if(++calm<2)return;
  stop();show();
}
function stop(){clearInterval(timer);timer=0;}
function loadCss(){
  if(cssReady)return cssReady;
  const href=globalThis.__mnlBoot?.asset?.('/css/gift.css')||'/css/gift.css';
  const l=document.createElement('link');l.rel='stylesheet';l.href=href;l.dataset.gfCss='1';
  cssReady=new Promise(done=>{l.onload=l.onerror=()=>done();setTimeout(done,4000);});
  document.head.append(l);
  return cssReady;
}

/** Called by app.js after the game is on screen, when api.gifts is not empty. */
export function giftBoot(env){
  try{
    E=env;
    queue=(env?.api?.gifts||[]).filter(g=>g&&typeof g.id==='string'&&Number(g.coins)>0);
    if(!queue.length)return;
    want('gift');loadCss();calm=0;stop();timer=setInterval(check,700);
  }catch(error){console.error('gift:',error);}   // never in the way of the game
}
