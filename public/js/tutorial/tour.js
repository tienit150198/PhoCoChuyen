/** First-run tour: coach marks over the REAL game UI. A spotlight dims the
 * rest and rings one element, a small bubble says 1–2 short lines.
 *
 * - Never blocks: the layer ignores pointer events (only the bubble takes
 *   taps), so the player can always tap straight through to the game.
 * - Advances by itself when the player does the highlighted thing (a step's
 *   `done()` is checked every frame against the live state/DOM), otherwise
 *   with "Tiếp". A step whose element never shows up is skipped quietly.
 * - Modal sheets live in the browser's top layer, so the layer is mounted
 *   inside the top-most open dialog (like the toasts). An element hidden
 *   under another sheet shows a small "close this first" bubble instead.
 * - Honours reduced motion (no pulse, no glide, instant scroll).
 * Markup and data only; the game rules stay on the server. */
import {saveRun,markTourDone} from './store.js';

let E=null,run=null,layer=null,raf=0,last={},seen=null;
const $=(s,root=document)=>root.querySelector(s);
const reduced=()=>document.documentElement.classList.contains('reduce-motion')||matchMedia('(prefers-reduced-motion: reduce)').matches;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

/* ------------------------------------------------------------ live context */
const S=()=>E?.api?.state;
const J=()=>S()?.journey;
const ui=()=>E?.ui||{};
const room=()=>{const s=S();return s?.careers?.[s.current||s.focus];};
/** Visible on screen (not display:none, not zero-sized). */
function vis(el){
  if(typeof el==='string')el=$(el);
  if(!el||!el.isConnected)return null;
  const r=el.getBoundingClientRect();
  if(r.width<2||r.height<2)return null;
  const cs=getComputedStyle(el);if(cs.visibility==='hidden'||cs.display==='none')return null;
  return el;
}
const firstVis=(sel,root=document)=>[...root.querySelectorAll(sel)].find(el=>vis(el)&&!el.disabled)||null;
/** Open modal dialogs, most recently opened last. */
const stack=[];
function topDialog(){
  for(let i=stack.length-1;i>=0;i--){const d=stack[i];if(d.open&&d.isConnected&&d.id!=='tutWelcome')return d;stack.splice(i,1);}
  // Dialogs opened before we started watching.
  const open=[...document.querySelectorAll('dialog[open]')].filter(d=>d.id!=='tutWelcome');
  return open[open.length-1]||null;
}
const inIntro=()=>!!(J()?.story&&!J()?.intro);
const introStep=()=>{const j=J();if(!j)return '';return j.gender&&ui().jrStep!=='who'?'job':ui().jrStep||'arrive';};
const sheetView=()=>$('#sheet')?.open?ui().view:null;
/** The next thing to press on a work screen: a marked next control first, then the first live main button in view. */
function nextControl(){
  const sheet=$('#sheet[open]');if(!sheet||ui().view!=='job')return null;
  const marked=firstVis('[data-next],.is-next,.next-step,.pulse-next',sheet);if(marked)return marked;
  const H=innerHeight,inView=el=>{const r=el.getBoundingClientRect();return r.bottom>0&&r.top<H;};
  const all=[...sheet.querySelectorAll('.sheet-body .btn.primary, .sheet-body [data-command].btn')].filter(el=>vis(el)&&!el.disabled);
  return all.find(inView)||all[0]||null;
}

/* ------------------------------------------------------------------ steps */
/** Each step: emoji + 1–2 short lines (text may depend on the moment). `when` =
 * applies now, `plan` = expected in this run (for the progress dots), `find` =
 * the element to ring (null + center = a centred card), `done` = the player did it. */
const STEPS=[
  {id:'street',emoji:'🏘️',text:'Khu phố của bạn: một đời, nhiều nghề.',center:true,
    find:()=>vis('#sheet[open] .jr-street')},
  {id:'who',emoji:'✏️',text:()=>introStep()==='arrive'?'Bấm để chào khu phố.':'Chọn nhân vật, đặt tên.',
    when:()=>inIntro()&&introStep()!=='job',plan:inIntro,
    find:()=>vis('#sheet[open] .jr-intro .jr-who')||firstVis('#sheet[open] .jr-intro .btn.primary'),
    done:()=>!inIntro()||introStep()==='job'},
  {id:'journey',emoji:'🧭',text:'Bấm mở Hành trình.',
    when:()=>!inIntro()&&sheetView()!=='home',plan:()=>!inIntro(),
    find:()=>vis('#jrHud:not([hidden])')||vis('#rail [data-action="home"]')||vis('.brand'),
    done:()=>sheetView()==='home'},
  {id:'pick',emoji:'🏪',text:'Chọn một tiệm để làm.',
    when:()=>sheetView()==='home',wait:2500,
    find:()=>firstVis('#sheet[open] .jr-first-jobs .jr-job')||firstVis('#sheet[open] .jr-cta')||firstVis('#sheet[open] [data-action="choose"]'),
    done:()=>run.flags.chose&&sheetView()!=='home'},
  {id:'hire',emoji:'📝',text:'Xin việc trước, làm theo từng bước.',center:true,
    when:()=>{const j=room()?.job;return !!(j?.required&&j.status!=='hired');},plan:()=>false,
    find:()=>ui().view==='jobapp'?firstVis('#sheet[open] .sheet-body .btn.primary'):null,
    done:()=>{const j=room()?.job;return !j?.required||j.status==='hired';}},
  {id:'open',emoji:'☀️',text:'Bấm Mở cửa.',wait:4000,
    when:()=>room()&&!room().open,
    find:()=>firstVis('#sheet[open] [data-action="start"]')||vis('#taskHUD [data-action="prepare"]'),
    done:()=>!!room()?.open},
  {id:'money',emoji:'🪙',text:'Quỹ tiệm: tiền của tiệm.',stage:true,
    find:()=>vis('#topbar .cozy-till')},
  // Calm screen (0.8.4): the wallet chip left the stage; the wallet sits in the status sheet behind the day.
  {id:'wallet',emoji:'👛',stage:true,
    text:()=>vis('#jrHud:not([hidden])')?(run.shown.includes('journey')?'Ví của bạn, trả tiền phòng.':'Ví của bạn. Bấm để mở Hành trình.'):'Bấm ngày: ví của bạn, tinh thần, đánh giá.',
    when:()=>!!J()?.story,plan:()=>!!J()?.story,find:()=>vis('#jrHud:not([hidden])')||vis('#topbar .hud-day')},
  {id:'task',emoji:'📋',text:'Bấm Làm tiếp.',stage:true,
    when:()=>!!room()?.open,
    find:()=>vis('#taskHUD .task-card')||vis('#taskHUD .note-card'),
    done:()=>sheetView()==='job'},
  {id:'do',emoji:'👆',text:'Bấm nút nổi bật.',wait:2500,
    when:()=>sheetView()==='job',find:nextControl,
    done:()=>run.flags.acted},
  {id:'close',emoji:'🌙',text:'Hết khách: Khép ca, xem tổng kết.',center:true,final:true,
    img:'/icons/tutorial/day-summary.webp',
    find:()=>firstVis('#taskHUD [data-action="end"]')||firstVis('#sheet[open] [data-action="end"]'),
    done:()=>sheetView()==='summary'},
];

/* ------------------------------------------------------------------ layer */
function mount(){
  if(!layer){
    layer=document.createElement('div');layer.id='tutLayer';layer.className='tut-layer';
    layer.innerHTML='<div class="tut-dim"></div><div class="tut-spot" aria-hidden="true"></div><div class="tut-bubble" role="dialog" aria-live="polite" aria-label="Hướng dẫn"><i class="tut-arrow" aria-hidden="true"></i><div class="tut-body"></div></div>';
    layer.querySelector('.tut-bubble').addEventListener('click',onBubble);
  }
  const host=topDialog()||document.body;
  if(layer.parentElement!==host)host.append(layer);
  return layer;
}
function onBubble(e){
  const b=e.target.closest('[data-tut]');if(!b)return;
  e.preventDefault();e.stopPropagation();
  if(b.dataset.tut==='next')next(true);
  else if(b.dataset.tut==='skip')stopTour('skip');
}

const textOf=step=>typeof step.text==='function'?step.text():step.text;
function bubbleHTML(step,covered){
  const plan=run.order.filter(id=>run.plan.includes(id)||id===step.id),n=plan.indexOf(step.id)+1;
  const dots=`<span class="tut-dots" role="img" aria-label="Bước ${n}/${plan.length}">${plan.map((_,i)=>`<i class="${i<n?'on':''}"></i>`).join('')}</span>`;
  const text=covered?'Xong bảng này rồi đi tiếp nhé.':textOf(step);
  const emoji=covered?'👀':step.emoji;
  return `<div class="tut-row"><span class="tut-emoji" aria-hidden="true">${emoji}</span><p class="tut-text">${esc(text)}</p></div>`+
    (step.img&&!covered?`<img class="tut-pic" src="${step.img}" alt="" width="360" height="282" loading="lazy">`:'')+
    `<div class="tut-foot">${dots}<span class="grow"></span><button type="button" class="btn ghost small tut-skip" data-tut="skip">Bỏ qua</button>`+
    `<button type="button" class="btn primary small tut-next" data-tut="next">${step.final?'Xong 🎉':'Tiếp'}</button></div>`;
}

/** Where the bubble goes: under the target, else above, else pinned to the bottom. */
function place(bubble,arrow,r){
  const W=innerWidth,H=innerHeight,m=12,bw=Math.min(340,W-2*m),bh=bubble.offsetHeight||120;
  bubble.style.width=bw+'px';
  if(!r){bubble.style.left=Math.round((W-bw)/2)+'px';bubble.style.top=Math.round(Math.max(m,(H-bh)/2))+'px';arrow.hidden=true;return;}
  const below=r.bottom+14+bh<=H-m,above=r.top-14-bh>=m;
  let top,side;
  if(below&&(r.top>H*0.55?!above:true)){top=r.bottom+14;side='top';}
  else if(above){top=r.top-14-bh;side='bottom';}
  else{top=H-bh-m-(parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--safe-b'))||0);side='';}
  const left=Math.round(Math.min(W-bw-m,Math.max(m,r.left+r.width/2-bw/2)));
  bubble.style.left=left+'px';bubble.style.top=Math.round(top)+'px';
  arrow.hidden=!side;arrow.dataset.side=side;
  arrow.style.left=Math.round(Math.min(bw-22,Math.max(10,r.left+r.width/2-left-8)))+'px';
}

function frame(){
  raf=0;if(!run)return;
  const step=STEPS.find(s=>s.id===run.order[run.i]);
  if(!step){finish();return;}
  if(step.done?.()){next(false);return schedule();}
  const el=step.find?.()||null,top=topDialog();
  const covered=!!(el&&top&&!top.contains(el))||(!el&&step.stage&&!!top);
  const now=performance.now();
  if(!el&&!step.center&&!covered){
    // Not there (yet): wait a moment for sheets to open, then move on quietly.
    if(now-run.t0>(step.wait||1200)){next(false);return schedule();}
    if(layer)layer.hidden=true;return schedule();
  }
  run.t0=el||covered?now:run.t0;
  const L=mount();L.hidden=false;L.dataset.step=step.id;
  const spot=L.querySelector('.tut-spot'),dim=L.querySelector('.tut-dim'),bubble=L.querySelector('.tut-bubble'),arrow=L.querySelector('.tut-arrow'),body=L.querySelector('.tut-body');
  const key=step.id+(covered?':c':'')+textOf(step);
  if(last.key!==key){
    last={key};body.innerHTML=bubbleHTML(step,covered);
    L.classList.toggle('still',reduced());
    if(el&&!covered)ensureInView(el);
    if(!run.shown.includes(step.id))run.shown.push(step.id);
  }
  const r=el&&!covered?el.getBoundingClientRect():null;
  const pad=6,rect=r?[Math.round(r.left-pad),Math.round(r.top-pad),Math.round(r.width+2*pad),Math.round(r.height+2*pad)]:null;
  const sig=JSON.stringify([rect,innerWidth,innerHeight,bubble.offsetHeight]);
  if(last.sig!==sig){
    last.sig=sig;
    spot.hidden=!rect;dim.hidden=!!rect;
    if(rect){const [x,y,w,h]=rect;Object.assign(spot.style,{left:x+'px',top:y+'px',width:w+'px',height:h+'px'});}
    place(bubble,arrow,r&&{left:r.left-pad,top:r.top-pad,right:r.right+pad,bottom:r.bottom+pad,width:r.width+2*pad,height:r.height+2*pad});
  }
  schedule();
}
const schedule=()=>{if(run&&!raf)raf=requestAnimationFrame(frame);};
function ensureInView(el){
  const r=el.getBoundingClientRect(),seen=Math.min(r.bottom,innerHeight)-Math.max(r.top,0);
  if(seen>=Math.min(r.height,innerHeight)*0.6)return;   // mostly on screen already (sticky bars too)
  try{el.scrollIntoView({block:'center',behavior:reduced()?'auto':'smooth'});}catch{el.scrollIntoView();}
}

/* ------------------------------------------------------------------ flow */
function next(manual){
  if(!run)return;
  const cur=STEPS.find(s=>s.id===run.order[run.i]);
  if(manual&&cur?.final){finish();return;}
  if(!manual&&cur&&!run.shown.includes(cur.id))drop(cur.id);   // never showed up
  run.i++;
  // Skip steps that do not apply right now (already open, not in the intro…).
  while(run.i<run.order.length){const s=STEPS.find(x=>x.id===run.order[run.i]);if(!s.when||s.when())break;drop(s.id);run.i++;}
  if(run.i>=run.order.length){finish();return;}
  run.t0=performance.now();run.flags={chose:false,acted:false,clicked:false};last={};
  saveRun(run.order[run.i]);schedule();
}
const drop=id=>{run.plan=run.plan.filter(x=>x!==id);};
function finish(){
  const was=!!run;stopTour('done');
  if(was)E?.toast?.('Xong! Xem lại ở mục Hướng dẫn 📘','hint');
}

/** Real clicks: note what the player just did (choose a place, act on a work screen). */
function onClick(e){
  if(!run)return;
  const el=e.target.closest?.('[data-action],[data-command]');if(!el)return;
  if(el.dataset.action==='choose')run.flags.chose=true;
  const sheet=$('#sheet');
  if(sheet?.open&&sheet.contains(el)&&ui().view==='job'&&!['close','jobTab','chat'].includes(el.dataset.action))run.flags.clicked=true;
}
/** A command answered after a click on the work screen = the player did a step. */
function onState(e){
  if(!run)return;
  if(run.flags.clicked&&e.detail?.result)run.flags.acted=true;
  schedule();
}

export function startTour(env,{at}={}){
  E=env;watch();
  const order=STEPS.map(s=>s.id);
  let i=Math.max(0,at?order.indexOf(at):0);
  run={order,i,t0:performance.now(),flags:{chose:false,acted:false,clicked:false},shown:[],plan:[]};last={};
  run.plan=order.slice(i).filter(id=>{const s=STEPS.find(x=>x.id===id);return s.plan?s.plan():true;});
  // Drop steps that cannot apply in this run (the intro, the wallet of a story-less save).
  const s=STEPS[i];if(s.when&&!s.when()){run.i=i-1;next(false);}else saveRun(order[i]);
  schedule();
}
export function stopTour(reason){
  if(!run)return;
  run=null;if(raf)cancelAnimationFrame(raf);raf=0;
  layer?.remove();last={};
  markTourDone(E);
  if(reason==='skip')E?.toast?.('Xem lại ở mục Hướng dẫn 📘','hint');
}
export const tourRunning=()=>!!run;

/** One-time wiring: dialog order, clicks, state and layout changes. */
function watch(){
  if(seen)return;seen=true;
  stack.push(...document.querySelectorAll('dialog[open]'));
  new MutationObserver(recs=>{
    for(const r of recs){const d=r.target;if(!(d instanceof HTMLDialogElement))continue;
      const i=stack.indexOf(d);if(i>=0)stack.splice(i,1);if(d.open)stack.push(d);}
    if(run){last.sig='';schedule();}
  }).observe(document.body,{subtree:true,attributes:true,attributeFilter:['open']});
  document.addEventListener('click',onClick,true);
  E?.api?.addEventListener('state',onState);
  const again=()=>{if(run){last.sig='';schedule();}};
  addEventListener('resize',again);addEventListener('layoutchange',again);addEventListener('scroll',again,true);
}
