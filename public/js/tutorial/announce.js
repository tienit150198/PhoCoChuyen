/** Announcements: a small, friendly, non-blocking card shown once per player
 * (per id) after the game has loaded, never over an open sheet or a live
 * decision. Tapping either button remembers it (localStorage + synced
 * settings.notesSeen). Add a new entry with a new id to announce again. */
import {notesSeen,markNoteSeen} from './store.js';

/** {id, emoji, text, label, action}: `action` names a handler given to announceBoot. */
export const NOTES=[
  {id:'guide-v1',emoji:'📘',text:'Có hướng dẫn mới, có hình minh hoạ!',label:'Xem hướng dẫn',action:'guide'},
];

let E=null,card=null,shown=null,timer=0,ACTIONS={};
/** A sheet, a decision (confirm, live happening), the phone menu, the tour or another notice is up. */
const busy=()=>!!document.querySelector('dialog[open]')||document.documentElement.classList.contains('menu-open')||!!document.getElementById('tutLayer')?.isConnected||
  !!document.querySelector('.hap-choices, #aiNotice')||!!E?.ui?.paused;

function pending(){
  const seen=notesSeen(E.api);
  return NOTES.find(n=>!seen.has(n.id))||null;
}
function hide(){card?.remove();card=null;shown=null;}
function show(n){
  card=document.createElement('aside');card.className='tut-note';card.setAttribute('role','status');card.setAttribute('aria-label','Thông báo');
  card.innerHTML=`<span class="tut-note-emoji" aria-hidden="true">${n.emoji}</span><p>${n.text}</p><div class="tut-note-btns"><button type="button" class="btn ghost small" data-note="later">Để sau</button><button type="button" class="btn primary small" data-note="go">${n.label}</button></div>`;
  card.addEventListener('click',e=>{
    const b=e.target.closest('[data-note]');if(!b)return;
    markNoteSeen(E,n.id);hide();
    if(b.dataset.note==='go')ACTIONS[n.action]?.(E);
  });
  document.body.append(card);shown=n.id;place();
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
  if(busy()){if(card)card.hidden=true;return;}
  if(card){card.hidden=false;place();return;}
  const n=pending();if(n&&!shown)show(n);
}

/** Start watching. `actions` maps a note's action name to what its main button does. */
export function announceBoot(env,actions={}){
  E=env;ACTIONS=actions;
  clearInterval(timer);timer=setInterval(check,700);
  setTimeout(check,1500);
}
export const quietAll=env=>NOTES.forEach(n=>markNoteSeen(env,n.id));
