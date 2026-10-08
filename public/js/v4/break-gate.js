/** One popup at a time. The cards that open by themselves (🎁 gift, ✨ Có gì mới, 🔥 x3 tuần, 📖 Truyện nghề)
 * wait here for a break point instead of each keeping its own rule, so the day summary, a customer on the
 * work screen and the first-time cards are never covered, and two cards never open together.
 *
 * - quiet(): a calm screen. No other dialog is open, the sheet is closed or shows a calm page (not the day
 *   summary, not the evening, not the work screen), the phone menu is shut and the tutorial tour is not up.
 * - free(): what a one-time notice (gift, Có gì mới) needs: the same, except that the work screen may show
 *   its "task done" card (no customer waiting on it).
 * - turn(name): no card ranked before this one is waiting (gift → Có gì mới → x3 → story → 🛡️ rủi ro); want(name) /
 *   want(name,false) say when a card is due or done.
 * - whenQuiet(fn): run fn at the next quiet moment: when the sheet closes, else checked every 1.5 s, for
 *   2 minutes at most (then the next scene or state change asks again, as before).
 * DOM only (no game rule); safe to import from any module. */
const RANK={gift:0,whatsnew:1,wedinvite:1.5,x3:2,story:3,rui:4};   // 💌 v4/wedinvite.js: a couple's card, after Có gì mới
const waiting=new Set();
export function want(name,on=true){if(on)waiting.add(name);else waiting.delete(name);}
export const turn=name=>![...waiting].some(n=>n!==name&&(RANK[n]??9)<(RANK[name]??9));

/** Why the open sheet is not calm ('' = closed or calm): 'summary', 'evening', 'work' or 'done' (the task-done card). */
export function sheetBusy(doc=document){
  const s=doc.getElementById('sheet');if(!s?.open)return '';
  if(s.classList.contains('cozy-summary')||s.querySelector('.summary-v6'))return 'summary';
  if(s.classList.contains('nd-sheet'))return 'evening';
  if(s.classList.contains('cozy-job'))return s.querySelector('.done-body')?'done':'work';
  return '';
}
/** Why a card may not open now ('' = it may). `self`: the asking card's own dialog; `strict`: quiet() rules. */
export function why(self=null,{strict=true}={},doc=document){
  if(doc.hidden)return 'hidden';
  if(doc.getElementById('tutLayer')?.isConnected)return 'tour';
  if(doc.documentElement.classList.contains('menu-open'))return 'menu';
  for(const d of doc.querySelectorAll('dialog[open]'))if(d!==self&&d.id!=='sheet')return d.id||'dialog';
  const s=sheetBusy(doc);
  if(s&&(strict||s!=='done'))return s;
  return '';
}
export const quiet=(self=null)=>!why(self);
export const free=(self=null)=>!why(self,{strict:false});

const jobs=new Map();   // fn → {until, timer}
export function whenQuiet(fn,{ms=120000,every=1500}={}){
  if(typeof document==='undefined'||jobs.has(fn))return;
  const job={until:Date.now()+ms,timer:0};
  const sheet=document.getElementById('sheet');
  const stop=()=>{clearInterval(job.timer);sheet?.removeEventListener('close',soon);jobs.delete(fn);};
  const run=()=>{
    if(!jobs.has(fn))return;
    if(Date.now()>job.until){stop();return;}
    if(!quiet())return;
    stop();
    try{fn();}catch(error){console.error('popup-gate:',error);}
  };
  // After the sheet closes, give the next sheet a moment (a summary → evening hop is a re-render, a close → open is not).
  function soon(){setTimeout(run,300);}
  sheet?.addEventListener('close',soon);
  job.timer=setInterval(run,every);
  jobs.set(fn,job);
}
