/** 🔥 Nghề x3 trong tuần (game/x3_week.py → state.x3 {x, week, days, day, today}): every career has one day a week
 * when closing its shift pays the day's net X times. A centred card with the week's list opens by itself once a
 * week at a break point (v4/popup-gate.js: after a gift and "Có gì mới", never over the day summary, the work
 * screen or another card; over a calm sheet such as the journey home it may), and any time from the banner on the Nơi làm việc list
 * (data-action="x3Week"). What week was shown is kept in localStorage (a lost key only shows the card again).
 * It borrows the "Có gì mới" card's look (css/whatsnew.css). app.js loads this module lazily (x3Boot). */
import {icon,escapeHTML as esc} from '../icons.js';
import {emojiOf} from './journey.js';
import {quiet,turn,want} from './popup-gate.js';
import {firstDay} from './onboard.js';

const KEY='mnl.x3.week',DOW=['Thứ Hai','Thứ Ba','Thứ Tư','Thứ Năm','Thứ Sáu','Thứ Bảy','Chủ nhật'];
let E=null,dlg=null,timer=0,calm=0,back=null,openedAt=0,auto=false;
const seen=()=>{try{return localStorage.getItem(KEY)||'';}catch{return 'blocked';}};
const mark=w=>{try{localStorage.setItem(KEY,w);}catch{/* storage blocked */}};
const X=()=>E?.api?.state?.x3||null;
const dm=(week,i)=>{const d=new Date(Date.parse(`${week}T00:00:00Z`)+i*864e5);return `${String(d.getUTCDate()).padStart(2,'0')}/${String(d.getUTCMonth()+1).padStart(2,'0')}`;};
const meta=id=>E?.api?.content?.catalogue?.find(m=>m.id===id)||{id,short:id};

function html(){
  const x=X(),J=E.api.state.journey||{},open=new Set(J.unlocked||[]);
  const row=(ids,i)=>`<li class="${i===x.day?'on':i<x.day?'past':''}"><b>${DOW[i]} <small>${dm(x.week,i)}</small>${i===x.day?' <em>hôm nay</em>':''}</b>
    <span class="x3-jobs">${ids.map(id=>{const m=meta(id);return `<span class="x3-job${open.has(id)?'':' lk'}"><i aria-hidden="true">${emojiOf(m)}</i>${esc(m.short||id)}</span>`;}).join('')}</span></li>`;
  // Today first, in sight; the whole week (and how the bonus is paid) one tap away (owner 03/10: "chữ ít thôi").
  const today=x.days[x.day]?row(x.days[x.day],x.day):'',days=x.days.map(row).join('');
  return `<header class="wn-head"><span class="wn-spark" aria-hidden="true">🔥</span><div class="grow"><h2 id="x3Title">Tuần này nghề nào lời x${x.x}?</h2><p class="wn-meta">Từ ${dm(x.week,0)} đến ${dm(x.week,6)}</p></div>`+
    `<button type="button" class="icon-btn wn-x" data-x3="close" aria-label="Đóng">${icon('x',22)}</button></header>`+
    `<div class="wn-body"><p class="x3-how">Làm nghề của hôm nay rồi khép ca: lời x${x.x}.</p><ol class="x3-week">${today}</ol>`+
    `<details class="x3-more"><summary>Cả tuần</summary><p class="x3-how">Đúng ngày của nghề nào, làm nghề đó rồi khép ca là được thưởng thêm gấp đôi tiền lời của ngày vào ví: cả ngày lời x${x.x}. Tuần nào nghề nào cũng có một ngày.</p><ol class="x3-week">${days}</ol></details></div>`+
    `<footer class="wn-foot"><button type="button" class="btn primary big full" data-x3="close">Biết rồi</button></footer>`;
}
function build(){
  if(dlg)return dlg;
  dlg=document.createElement('dialog');dlg.id='x3Dialog';dlg.className='wn-dialog x3-dialog';
  dlg.setAttribute('aria-modal','true');dlg.setAttribute('aria-labelledby','x3Title');
  dlg.innerHTML='<div class="wn-card"></div>';
  document.body.append(dlg);
  dlg.addEventListener('click',e=>{
    const b=e.target.closest('button');if(!b||!dlg.contains(b))return;
    if(auto&&performance.now()-openedAt<450){e.preventDefault();return;}   // a tap already on its way
    if(b.dataset.x3==='close')close();
  });
  dlg.addEventListener('cancel',e=>{e.preventDefault();close();});
  return dlg;
}
function css(){
  if(document.querySelector('link[data-wn-css]'))return;
  const l=document.createElement('link');l.rel='stylesheet';l.dataset.wnCss='1';
  l.href=globalThis.__mnlBoot?.asset?.('/css/whatsnew.css')||'/css/whatsnew.css';document.head.append(l);
}
export function openX3(env=E,{byItself=false}={}){
  E=env||E;const x=X();if(!x?.days)return;
  css();build();auto=byItself;back=document.activeElement;
  dlg.querySelector('.wn-card').innerHTML=html();
  if(!dlg.open)dlg.showModal();
  openedAt=performance.now();dlg.tabIndex=-1;dlg.focus({preventScroll:true});
  mark(x.week);
}
function close(){
  if(!dlg?.open)return;
  dlg.close();
  if(back?.isConnected&&typeof back.focus==='function')back.focus({preventScroll:true});
  back=null;
}
/** The week's card may open by itself: a story player past their first day who has not seen this week yet. */
function due(){
  const s=E?.api?.state,x=s?.x3,J=s?.journey;
  return !!(x?.week&&J?.story&&J.intro&&!firstDay(s)&&seen()!==x.week&&seen()!=='blocked');
}
function check(){
  if(!due()){calm=0;want('x3',false);return;}
  want('x3');
  if(!quiet(dlg)||!turn('x3')){calm=0;return;}   // a gift or "Có gì mới" first; never over the summary, the work or another card
  if(++calm<2)return;
  calm=0;want('x3',false);openX3(E,{byItself:true});
}
/** Called once by app.js after the game is on screen. */
export function x3Boot(env){
  try{
    E=env;
    document.addEventListener('click',e=>{
      const b=e.target.closest?.('[data-action="x3Week"]');if(!b||b.disabled)return;
      e.preventDefault();e.stopImmediatePropagation();
      openX3(E);
    },true);
    clearInterval(timer);timer=setInterval(check,1000);   // also catches a new week while the game stays open
  }catch(error){console.error('x3week:',error);}   // never in the way of the game
}
