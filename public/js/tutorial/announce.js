/** One small, non-blocking card after the game has loaded, never over an open sheet or a live decision:
 * - an announcement (NOTES, once per player per id; none at the moment), or
 * - the first time at a workplace: "Xem hướng dẫn" or "Bỏ qua" for that place's guide, once per workplace
 *   (store.js markGuideSeen: settings.notesSeen, so on every device). Not at a brand-new player's first
 *   workplace (the first-day tips teach it), not at a place already worked past its first day, not where the
 *   work screen opens on the career's own "Giới thiệu nghề" card, not while the first-day tips run.
 * Tapping either button remembers it. The guide stays one tap away: the "?" of every work screen, Cài đặt. */
import {notesSeen,markNoteSeen,guidesFrom,markGuideSeen} from './store.js';
import {markedNew} from '../v4/onboard.js';

/** {id, emoji, text, label, action}: `action` names a handler given to announceBoot. Add an entry with a new id
 * to announce again. ("guide-v1", the "Có hướng dẫn mới" card, gave way to the per-workplace card.) */
export const NOTES=[];

/** The workplace whose guide card is due in `state` (null: none). `seen`: the note ids already seen. */
export function guideDue(state,seen){
  const cid=state?.current,c=state?.careers?.[cid];if(!cid||!c)return null;
  if(guidesFrom(seen).has(cid)||(Number(c.day)||1)>1)return null;
  // A workplace that opens on its own "Giới thiệu nghề" card (pilot, street trades, clothing…, data.intro /
  // intro_seen) already has its first-time card, with a ❔ to see it again: never both.
  if(typeof c.data?.intro==='boolean'||typeof c.data?.intro_seen==='boolean')return null;
  // A brand-new player's first workplace: the first-day tips teach it. From their second workplace on, the card.
  if(markedNew(state)&&Object.entries(state.careers).every(([id,x])=>id===cid||!x?.started))return null;
  return cid;
}

let E=null,card=null,shown=null,timer=0,ACTIONS={},tipsOn=()=>false;
/** A sheet, a decision (confirm, live happening), the phone menu, the tour or another notice is up. */
const busy=()=>!!document.querySelector('dialog[open]')||document.documentElement.classList.contains('menu-open')||!!document.getElementById('tutLayer')?.isConnected||
  !!document.querySelector('.hap-choices, #aiNotice')||!!E?.ui?.paused||tipsOn();

function pending(){
  const seen=notesSeen(E.api),n=NOTES.find(x=>!seen.has(x.id));
  if(n)return {key:n.id,emoji:n.emoji,text:n.text,label:n.label,later:'Để sau',seen:()=>markNoteSeen(E,n.id),go:()=>ACTIONS[n.action]?.(E)};
  const cid=guideDue(E.api.state,seen);
  return cid?{key:'guide:'+cid,emoji:'📘',text:'Lần đầu làm ở đây?',label:'Xem hướng dẫn',later:'Bỏ qua',seen:()=>markGuideSeen(E,cid),go:()=>ACTIONS.guide?.(E,cid)}:null;
}
function hide(){card?.remove();card=null;shown=null;}
function show(n){
  card=document.createElement('aside');card.className='tut-note';card.setAttribute('role','status');card.setAttribute('aria-label','Thông báo');card.dataset.note=n.key;
  card.innerHTML=`<span class="tut-note-emoji" aria-hidden="true">${n.emoji}</span><p>${n.text}</p><div class="tut-note-btns"><button type="button" class="btn ghost small" data-note="later">${n.later}</button><button type="button" class="btn primary small" data-note="go">${n.label}</button></div>`;
  card.addEventListener('click',e=>{
    const b=e.target.closest('[data-note]');if(!b||b===card)return;
    n.seen();hide();
    if(b.dataset.note==='go')n.go();
  });
  document.body.append(card);shown=n.key;place();
}
/** Under the top bar; on a phone just above the task card (the toasts use the top there). */
function place(){
  if(!card)return;
  const top=(document.getElementById('topbar')?.getBoundingClientRect().bottom||0)+8;
  const phone=document.documentElement.dataset.layout==='phone';
  const hud=phone?[document.getElementById('taskHUD'),document.getElementById('dock')].map(el=>el?.getBoundingClientRect()).find(r=>r&&r.height>0):null;
  const y=hud?hud.top-card.offsetHeight-10:top;
  card.style.top=Math.round(Math.max(top,y))+'px';
}
function check(){
  if(!E?.api?.state?.current)return;          // not before a workplace is on screen
  const n=pending();
  if(card&&n?.key!==shown)hide();             // moved to another workplace, or answered on another device
  if(busy()){if(card)card.hidden=true;return;}
  if(card){card.hidden=false;place();return;}
  if(n)show(n);
}

/** Start watching. `actions` maps a note's action name to what its main button does (`guide(env, career)`
 * opens that workplace's guide); `tips()` is true while the first-day tips run. */
export function announceBoot(env,actions={},{tips}={}){
  E=env;ACTIONS=actions;if(tips)tipsOn=tips;
  clearInterval(timer);timer=setInterval(check,700);
  setTimeout(check,1500);
}
export const quietAll=env=>NOTES.forEach(n=>markNoteSeen(env,n.id));
