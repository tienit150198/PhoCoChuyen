/** 💐 Thiệp 20/10 (/2010, its own page: public/js/event2010.js, game/event2010.py). In the game, while writing is open
 * (isometric/town-utilities.js ev2010Open):
 * - a centred card opens by itself once on this device at a calm moment (v4/break-gate.js, after a gift, "Có gì mới"
 *   and a couple's wedding card; before the x3 week), never on a new neighbour's first day: "Viết thiệp" → /2010;
 * - the way back: /2010's "Đăng nhập" / "Tạo tài khoản" leave a mark (mnl.ev2010.back, for an hour); once this
 *   page has an account, a card offers "Quay lại viết thiệp".
 * It borrows the "Có gì mới" card's look (css/whatsnew.css). app.js loads this module lazily (ev2010Boot). */
import {icon} from '../icons.js';
import {quiet,turn,want} from './break-gate.js';
import {firstDay} from './onboard.js';
import {ev2010Open} from '../isometric/town-utilities.js';

const KEY='mnl.ev2010.seen',BACK='mnl.ev2010.back',BACK_MS=3600e3;
let E=null,dlg=null,timer=0,calm=0,back=null,openedAt=0;
const get=k=>{try{return localStorage.getItem(k)||'';}catch{return 'blocked';}};
const set=(k,v)=>{try{if(v==null)localStorage.removeItem(k);else localStorage.setItem(k,v);}catch{/* storage blocked */}};
const returning=()=>{const t=Number(get(BACK))||0;return t>0&&Date.now()-t<BACK_MS;};

const ART=`<svg class="ev10-art" viewBox="0 0 220 92" aria-hidden="true">
  <g transform="translate(70 18)"><rect width="80" height="56" rx="7" fill="#fff4f7" stroke="#f3a5bd" stroke-width="2"/><path d="M2 4 40 33 78 4" fill="none" stroke="#f3a5bd" stroke-width="2"/>
  <path d="M40 22c-5-7-15-3-12 5 2 5 12 11 12 11s10-6 12-11c3-8-7-12-12-5z" fill="#e8467c"/></g>
  <g fill="#e8467c"><circle cx="34" cy="40" r="9"/><circle cx="27" cy="33" r="6" fill="#ff8fb1"/><circle cx="41" cy="31" r="6" fill="#ff8fb1"/></g>
  <path d="M34 49v30M34 64c-8-2-12-8-12-8s8 0 12 5" stroke="#5c9a5a" stroke-width="3" fill="#7cb879" stroke-linecap="round"/>
  <g transform="translate(186 40)"><g fill="#ffd166">${[0,72,144,216,288].map(a=>`<ellipse rx="5" ry="10" transform="rotate(${a}) translate(0 -9)"/>`).join('')}</g><circle r="6" fill="#e07a1f"/></g>
  <path d="M186 50v30" stroke="#5c9a5a" stroke-width="3" stroke-linecap="round"/>
  <g fill="#ff8fb1"><path d="M58 12l2 5 5 2-5 2-2 5-2-5-5-2 5-2z"/><path d="M164 8l1.6 4 4 1.6-4 1.6-1.6 4-1.6-4-4-1.6 4-1.6z"/></g></svg>`;

function html(again){
  const J=E.api.state.journey||{},acct=E.api.account,ok=acct&&(!J.story||Number(J.life_day)>=3);
  const gift=ok?'Gửi tấm thiệp đầu tiên, Phố tặng bạn 100.000 xu.':acct?'Từ ngày sống thứ 3, tấm thiệp đầu tiên được Phố tặng 100.000 xu.':'Có tài khoản, tấm thiệp đầu tiên được Phố tặng 100.000 xu.';
  const title=again?'Quay lại viết thiệp nhé':'Phố đang mùa thiệp 20/10',meta=again?'Tài khoản đã sẵn sàng':'Đến hết 21/10';
  const body=again?'<p class="ev10-line">Thiệp bạn đang viết dở vẫn còn. Viết nốt rồi gửi link cho người ấy nhé.</p>'
    :'<p class="ev10-line">Viết vài dòng tặng mẹ, chị, bạn thân hay người thương. Chọn một mẫu thiệp xinh rồi gửi link, người nhận bấm là đọc được.</p>';
  return `<header class="wn-head ev10-head"><span class="wn-spark" aria-hidden="true">💐</span><div class="grow"><h2 id="ev10Title">${title}</h2><p class="wn-meta">${meta}</p></div>`+
    `<button type="button" class="icon-btn wn-x" data-ev10="close" aria-label="Đóng">${icon('x',22)}</button></header>`+
    `<div class="wn-body">${ART}${body}<p class="ev10-gift">🎁 ${gift}</p></div>`+
    `<footer class="wn-foot ev10-foot"><a class="btn primary big full ev10-go" href="/2010" data-ev10="go">${again?'Viết tiếp':'Viết thiệp ngay'}</a><button type="button" class="btn ghost full" data-ev10="close">Để sau</button></footer>`;
}
function build(){
  if(dlg)return dlg;
  dlg=document.createElement('dialog');dlg.id='ev10Dialog';dlg.className='wn-dialog ev10-dialog';
  dlg.setAttribute('aria-modal','true');dlg.setAttribute('aria-labelledby','ev10Title');
  dlg.innerHTML='<div class="wn-card"></div>';
  document.body.append(dlg);
  dlg.addEventListener('click',e=>{
    const b=e.target.closest('[data-ev10]');if(!b||!dlg.contains(b))return;
    if(performance.now()-openedAt<450){e.preventDefault();return;}   // a tap already on its way
    if(b.dataset.ev10==='close'){e.preventDefault();close();}
    else set(BACK,null);   // "Viết thiệp": the link goes on to /2010
  });
  dlg.addEventListener('cancel',e=>{e.preventDefault();close();});
  return dlg;
}
function css(){
  if(document.querySelector('link[data-wn-css]'))return;
  const l=document.createElement('link');l.rel='stylesheet';l.dataset.wnCss='1';
  l.href=globalThis.__mnlBoot?.asset?.('/css/whatsnew.css')||'/css/whatsnew.css';document.head.append(l);
}
function open(again){
  css();build();back=document.activeElement;
  dlg.querySelector('.wn-card').innerHTML=html(again);
  if(!dlg.open)dlg.showModal();
  openedAt=performance.now();dlg.tabIndex=-1;dlg.focus({preventScroll:true});
  set(KEY,'1');if(again)set(BACK,null);
}
function close(){
  if(!dlg?.open)return;
  dlg.close();
  if(back?.isConnected&&typeof back.focus==='function')back.focus({preventScroll:true});
  back=null;
}
/** Which card is due: 'back' (signed in after /2010 sent the player here), 'news' (not seen on this device), ''. */
export function due(s,account,{seen=get(KEY),coming=returning(),open=ev2010Open()}={}){
  if(!open||!s||seen==='blocked')return '';
  if(coming)return account?'back':'';   // still on the account form: nothing over it
  return !seen&&!firstDay(s)&&s.journey?.intro!==false?'news':'';
}
function check(){
  const kind=due(E?.api?.state,E?.api?.account);
  if(!kind){calm=0;want('ev2010',false);if(!ev2010Open()||get(KEY)&&!returning())clearInterval(timer);return;}
  want('ev2010');
  if(!quiet(dlg)||!turn('ev2010')){calm=0;return;}   // a gift, "Có gì mới" and a wedding card first; never over the work
  if(++calm<2)return;
  calm=0;want('ev2010',false);open(kind==='back');
}
/** Called once by app.js after the game is on screen, while writing is open. */
export function ev2010Boot(env){
  try{E=env;clearInterval(timer);timer=setInterval(check,1000);}
  catch(error){console.error('ev2010:',error);}   // never in the way of the game
}
