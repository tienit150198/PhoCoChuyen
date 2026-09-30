/** In-context tips for a brand-new player: the tutorial happens while playing. One short bubble points at the
 * control that matters right now; it never dims the screen, never asks for "Tiếp", and goes away when the
 * player does the thing (or after a few seconds for a look-here tip). "×" turns the remaining tips off.
 * The full coach-mark tour (tour.js) stays in Cài đặt → Hướng dẫn → "Xem lại hướng dẫn".
 *
 * Progress survives a reload (localStorage mnl.tut.tips); the end marks the tutorial done like the tour
 * (store.js markTourDone: settings.tutorialDone follows the account). Markup only: no game rule here. */
import {markTourDone} from './store.js';

const KEY='mnl.tut.tips';
const get=()=>{try{return localStorage.getItem(KEY);}catch{return null;}};
const set=v=>{try{if(v==null)localStorage.removeItem(KEY);else localStorage.setItem(KEY,v);}catch{/* storage blocked */}};
export const tipsSaved=()=>get()!=null;

let E=null,run=null,bubble=null,timer=0,seen=false;
const $=(s,root=document)=>root.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const S=()=>E?.api?.state;
const room=()=>{const s=S();return s?.careers?.[s?.current];};
const view=()=>$('#sheet')?.open?E?.ui?.view:null;
/** Visible, enabled, on screen. */
function vis(el){
  if(!el||!el.isConnected||el.disabled)return null;
  const r=el.getBoundingClientRect();
  if(r.width<2||r.height<2||r.bottom<0||r.top>innerHeight)return null;
  const cs=getComputedStyle(el);return cs.visibility==='hidden'||cs.display==='none'?null:el;
}
const first=(sel,root=document)=>[...root.querySelectorAll(sel)].find(vis)||null;
/** The top-most open dialog (the bubble lives in the browser's top layer with it). */
const topDialog=()=>{const d=[...document.querySelectorAll('dialog[open]')];return d[d.length-1]||null;};
const calmStage=()=>!topDialog()&&!document.documentElement.classList.contains('menu-open');

/* ------------------------------------------------------------------ the tips */
/** `when`: the moment is here; `find`: the control to point at; `done`: the player did it;
 * `ttl`: a look-here tip leaves by itself after that many ms on screen. */
const TIPS=[
  {id:'work',emoji:'👆',text:'Bấm nút sáng để làm từng bước cho khách.',
    when:()=>view()==='job'&&!!room()?.open,
    find:()=>{const s=$('#sheet[open]');return s&&(first('.gd-cta',s)||first('.gd-pulse',s)||first('.sheet-body .btn.primary',s));},
    done:()=>run.acted||(room()?.metrics?.served|0)>0},
  {id:'close',emoji:'🌙',text:'Hết khách rồi: khép ca, xem tổng kết.',
    when:()=>!!room()?.open,
    find:()=>first('#sheet[open] .btn[data-action="end"]')||first('#taskHUD .btn[data-action="end"]'),
    done:()=>view()==='summary'||!room()?.open},
  {id:'journey',emoji:'🧭',ttl:9000,   // day 2: the rest of the street (on a phone it sits behind "Thêm")
    text:()=>first('#rail [data-action="home"]')?'Hành trình: việc cần làm và nơi làm khác.':'Thêm → Hành trình: việc cần làm, nơi làm khác.',
    when:()=>calmStage()&&(S()?.journey?.life_day|0)>=2,
    find:()=>first('#rail [data-action="home"]')||first('#dock [data-action="v4Menu"]'),
    done:()=>!calmStage()},   // opened Hành trình, the menu or anything else: it has done its job
];

/* ------------------------------------------------------------------ bubble */
/** A small bubble with an arrow, above or under the control; `onClose` for "×". */
export function showBubble({id,emoji,text,el,onClose,cls=''}){
  hideBubble();
  const host=topDialog()||document.body;
  bubble=document.createElement('div');bubble.className=`tut-layer tips ${cls}`.trim();bubble.dataset.tip=id;
  bubble.innerHTML=`<div class="tut-spot" aria-hidden="true"></div><div class="tut-bubble" role="status" aria-live="polite"><i class="tut-arrow" aria-hidden="true"></i>`+
    `<div class="tut-row"><span class="tut-emoji" aria-hidden="true">${esc(emoji)}</span><p class="tut-text">${esc(text)}</p>`+
    `<button type="button" class="tip-x" aria-label="Tắt gợi ý">×</button></div></div>`;
  bubble.querySelector('.tip-x').addEventListener('click',e=>{e.preventDefault();e.stopPropagation();const f=onClose;hideBubble();f?.();});
  host.append(bubble);bubble._el=el;placeBubble();
  return bubble;
}
export function hideBubble(){bubble?.remove();bubble=null;}
export const bubbleUp=()=>!!bubble?.isConnected;
/** Follow the control (a sheet scrolls, the layout changes); hide while it is off screen. */
export function placeBubble(){
  if(!bubble)return;
  const el=bubble._el,r=vis(el)?el.getBoundingClientRect():null;
  const b=bubble.querySelector('.tut-bubble'),arrow=bubble.querySelector('.tut-arrow'),spot=bubble.querySelector('.tut-spot');
  bubble.hidden=!r;if(!r)return;
  const pad=5;Object.assign(spot.style,{left:r.left-pad+'px',top:r.top-pad+'px',width:r.width+2*pad+'px',height:r.height+2*pad+'px'});
  const W=innerWidth,H=innerHeight,m=12,bw=Math.min(320,W-2*m),bh=b.offsetHeight||64;
  b.style.width=bw+'px';
  const above=r.top-14-bh>=m,below=r.bottom+14+bh<=H-m;
  const up=r.top>H*0.5?above:!below&&above;   // controls low on the screen get the bubble above them
  const top=up?r.top-pad-12-bh:r.bottom+pad+12;
  const left=Math.round(Math.min(W-bw-m,Math.max(m,r.left+r.width/2-bw/2)));
  b.style.left=left+'px';b.style.top=Math.round(Math.max(m,Math.min(H-bh-m,top)))+'px';
  arrow.dataset.side=up?'bottom':'top';arrow.hidden=false;
  arrow.style.left=Math.round(Math.min(bw-22,Math.max(10,r.left+r.width/2-left-8)))+'px';
}

/* ------------------------------------------------------------------ flow */
function tick(){
  if(!run)return;
  const tip=TIPS[run.i];
  if(!tip){finish();return;}
  if(run.shown&&(tip.done()||(tip.ttl&&performance.now()-run.shown>tip.ttl))){next();return;}
  if(!tip.when()){if(bubbleUp()&&bubble.dataset.tip===tip.id)hideBubble();return;}
  const el=tip.find(),top=topDialog();
  // Not there, or under a newer dialog (a confirm, a scene): wait out of sight.
  if(!el||top&&!top.contains(el)){if(bubbleUp())bubble.hidden=true;return;}
  if(!bubbleUp()||bubble.dataset.tip!==tip.id||bubble._el!==el||bubble.parentElement!==(top||document.body)){
    showBubble({id:tip.id,emoji:tip.emoji,text:typeof tip.text==='function'?tip.text():tip.text,el,onClose:()=>stopTips('off')});
  }else placeBubble();
  run.shown||=performance.now();
}
function next(){
  hideBubble();run.i++;run.shown=0;run.acted=false;
  if(run.i>=TIPS.length){finish();return;}
  set(TIPS[run.i].id);
}
function finish(){stopTips('done');}
export function stopTips(reason){
  if(!run)return;
  run=null;clearInterval(timer);timer=0;hideBubble();set(null);markTourDone(E);
  if(reason==='off')E?.toast?.('Đã tắt gợi ý. Xem lại ở mục Hướng dẫn 📘','hint');
}
export const tipsRunning=()=>!!run;

/** Start (or pick up after a reload) the tips of a brand-new player. */
export function startTips(env){
  E=env;watch();
  const at=TIPS.findIndex(t=>t.id===get());
  run={i:Math.max(0,at),shown:0,acted:false};set(TIPS[run.i].id);
  clearInterval(timer);timer=setInterval(tick,400);tick();
}

/** One-time wiring: a command answered after a tap on the work screen = the player did a step. */
function watch(){
  if(seen)return;seen=true;
  let clicked=false;
  document.addEventListener('click',e=>{
    const el=e.target.closest?.('[data-action],[data-command]');
    clicked=!!(el&&$('#sheet[open]')?.contains(el)&&E?.ui?.view==='job'&&!['close','jobTab','chat'].includes(el.dataset.action));
  },true);
  E?.api?.addEventListener('state',e=>{if(run&&clicked&&e.detail?.result){run.acted=true;clicked=false;}});
  const again=()=>{if(bubbleUp())placeBubble();};
  addEventListener('resize',again);addEventListener('layoutchange',again);addEventListener('scroll',again,true);
}

