/** 🧭 "Hướng dẫn": the first-day coach of every workplace (owner 21/10: "ngày đầu mình cho hướng dẫn các nghề cả nhập
 * hàng, mua bán, rồi đóng cửa… ở mode cũ và mới luôn").
 *
 * Step by step over the REAL work screen: the control of the step is ringed (the rest dimmed), a small bubble says
 * what to do in a few words, and the step moves on by itself when the player does it (a tap on that control the game
 * accepts). Shared steps open the shift first and close it at the end with the day's summary (coach-core.js);
 * each workplace's own steps come from ./coach-content.js (game/coach/*.py, written from the guide's steps).
 *
 * - Never in the way: the layer takes no taps (only the bubble does); "Bỏ qua" skips a step, "Tắt hướng dẫn" stops.
 * - A control that is not on screen (the other layout, a closed tab, the work sheet closed, not yet its turn): the ring
 *   goes to what opens it, or the bubble says where it is. A control scrolled away is brought into view once.
 * - Both work layouts (gọn/đầy đủ) and both towns (2.5D, classic): controls are found by data-coach, data-action /
 *   data-command selectors, then by their visible label.
 * - Who gets it: a save that began with the coach ("cn1") on every workplace's first day, by itself; everyone else
 *   once per workplace a "🧭 Có hướng dẫn mới cho nghề này" chip they can open or close. Always again from the work
 *   sheet's ⋯ → "🧭 Hướng dẫn". Remembered in settings.notesSeen (store.js markCoach): nothing new in the save.
 * - Honours reduced motion (no pulse, no glide, instant scroll). Markup only: the game rules stay on the server. */
import {coachSeen,markCoach,markGuideSeen,markNoteSeen,COACH_NEW} from './store.js';
import {CoachRun,planFor,norm,labelHit,labelScore} from './coach-core.js';
import {t as tr} from '../v4/i18n.js';

const KEY='mnl.coach.run',LAYER='coachLayer',CHIP='coachChip';
let fb={},E=null,DATA=null,loading=null,run=null,layer=null,timer=0,raf=0,chip=null,wired=false,last={},drawn=null,starting=false;
const $=(s,root=document)=>root.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const reduced=()=>document.documentElement.classList.contains('reduce-motion')||matchMedia('(prefers-reduced-motion: reduce)').matches;
const get=()=>{try{return JSON.parse(localStorage.getItem(KEY)||'null');}catch{return null;}};
const put=v=>{try{if(v)localStorage.setItem(KEY,JSON.stringify(v));else localStorage.removeItem(KEY);}catch{/* storage blocked */}};
const L=s=>tr(s);   // every line through the English pack (Vietnamese is the source)

/* ------------------------------------------------------------ live context */
const S=()=>E?.api?.state;
const room=cid=>S()?.careers?.[cid||S()?.current];
const sheetOpen=()=>!!$('#sheet')?.open;
const view=()=>sheetOpen()?E?.ui?.view:null;
function vis(el){
  if(!el||!el.isConnected)return null;
  const r=el.getBoundingClientRect();if(r.width<2||r.height<2)return null;
  const cs=getComputedStyle(el);if(cs.visibility==='hidden'||cs.display==='none')return null;
  if(el.closest(`#${LAYER},#${CHIP},.tut-layer,[hidden],details:not([open])>:not(summary)`))return null;
  return el;
}
/** The open dialogs, most recently opened last (the toast host keeps the same order). */
function topDialog(){const d=[...document.querySelectorAll('dialog[open]')].filter(x=>x.id!=='tutWelcome');return d[d.length-1]||null;}
const firstVis=(sel,root=document)=>{let off=null;for(const el of root.querySelectorAll(sel)){if(!vis(el))continue;if(!el.disabled)return el;off??=el;}return off;};
const CTRL='button,[role="button"],[role="tab"],[data-action],[data-command],summary,a[href],[data-coach]';
/** What a control says: its words and its aria-label. */
const said=el=>[el.innerText||el.textContent||'',el.getAttribute('aria-label')||'',el.getAttribute('title')||''];

/** The game's own "next step" line and the sheet header repeat a step's words and command: a control there is only
 * ringed when the real one is not on screen. */
const ASIDE='.gd-next,.gd-hint,.sheet-head,.ui-chip,.ui-head-chip';
/** The town's "next job" card and button repeat the job's next words: never a step's control by its label (a tap
 * there only opens the work sheet). */
const OPENERS='#isoHUD [data-action="isoMission"],#taskHUD [data-action="job"],#taskHUD .task-card';
/** Dimmed "say why" controls (ui-kit whyAttrs: .is-why, aria-disabled) count as not pressable. */
const off=el=>!!(el.disabled||el.matches?.('.is-why,[aria-disabled="true"]'));
/** The bottom bar's small "hoặc …" link finishes early behind a "Còn N bước" question: the real button wins. */
const early=el=>/^\s*hoặc\s/i.test(el.innerText||'');
/** A step's control: data-coach / selectors first, then the label words (Vietnamese and the English pack). The best
 * one wins: a selector over a label, a button that says exactly the label over one that only mentions it, one that
 * can be pressed over a disabled one, the work itself over the header's hint. */
function find(spec,root){
  if(!spec)return null;
  let best=null,score=0;
  const take=(el,k)=>{k=k*4+(off(el)?0:2)+(el.closest(ASIDE)||early(el)?0:1);if(k>score){best=el;score=k;}};
  for(const sel of spec.s||[]){
    let list=[];try{list=root.querySelectorAll(sel);}catch{/* a bad selector never stops the coach */}
    for(const el of list)if(vis(el))take(el,4);
  }
  if(spec.k?.length){
    const want=[...new Set(spec.k.flatMap(k=>[norm(k),norm(L(k))]))];
    for(const el of root.querySelectorAll(CTRL)){
      const k=Math.max(...said(el).map(x=>labelScore(x,want)));
      if(k&&vis(el)&&!el.closest(OPENERS))take(el,k);
    }
  }
  return best;
}
/** Does a tapped control belong to this step? */
function owns(spec,el){
  if(!spec||!el)return false;
  for(const sel of spec.s||[]){try{if(el.closest(sel))return true;}catch{/* skip */}}
  if(!spec.k?.length)return false;
  const want=spec.k.flatMap(k=>[norm(k),norm(L(k))]);
  if(el.closest(OPENERS))return false;
  for(let x=el;x&&x!==document.body;x=x.parentElement){if(x.matches?.(CTRL)&&said(x).some(t=>labelHit(t,want)))return true;}
  return false;
}

/* Shared controls (classic town #taskHUD, 2.5D #isoHUD, the work sheet). */
const OPEN_AT=[['#sheet[open] [data-action="start"]','Bấm Mở cửa để bắt đầu ngày làm.'],['#sheet[open] [data-action="startHere"]','Bấm Mở ca để bắt đầu ngày làm.'],['#taskHUD [data-action="prepare"]','Bấm Chuẩn bị ngày mới, rồi mở cửa.'],
  ['#isoHUD [data-action="isoOpen"]','Bấm Mở ca để bắt đầu ngày làm.'],['#isoHUD [data-action="isoPrepare"]','Bấm Chuẩn bị ngày mới, rồi mở cửa.'],
  ['#isoHUD [data-action="isoWork"]','Bấm vào tiệm trước.'],['#taskHUD [data-action="start"]','Bấm Mở cửa để bắt đầu ngày làm.']];
const JOB_AT=['#sheet[open] [data-action="nextJob"]','#taskHUD .btn[data-action="job"]','#taskHUD [data-action="job"]','#isoHUD [data-action="isoMission"]','#taskHUD .task-card','#isoHUD [data-action="isoWork"]','#taskHUD [data-command="more_work"]','#sheet[open] [data-command="more_work"]'];
const END_AT=['#sheet[open] [data-action="end"]','#taskHUD [data-action="end"]','#isoHUD [data-action="isoEnd"]'];
/** The first shared control on screen; one under an open sheet does not count (the classic town is a sheet). */
function pick(list){const top=topDialog();for(const it of list){const [sel,text]=Array.isArray(it)?it:[it,''];const el=firstVis(sel);if(el&&(!top||top.contains(el)))return {el,text};}return null;}
/** The way out of a sheet that covers the work (the town map, Hành trình…). */
const backOut=()=>{const b=firstVis('#sheet[open] [data-action="close"]');return b?{nav:b,navText:'Đóng bảng này, quay lại việc.'}:{};};
/** Another guide is on screen (the tour, the welcome card): the coach waits out of sight. */
const otherGuide=()=>!!(document.getElementById('tutLayer')?.isConnected||$('#tutWelcome[open]'));

/** The first later step of the walk that the game's own guidance points at now, or null. */
function ahead(root){
  let best=null;
  for(const el of root.querySelectorAll('.gd-pulse,.gd-cta,.gd-hint,[data-next]')){
    if(!vis(el)||el.disabled)continue;
    const j=run.which(st=>owns(st,el));
    if(j!=null&&j>run.i&&(best==null||j<best))best=j;
  }
  return best;
}
/** What is on screen for step `s` (CoachRun.frame's probe). */
function probe(s){
  const cid=run.cid,c=room(cid),st=S();
  if(!c||st?.current!==cid||otherGuide()||E?.ui?.paused)return {hold:true};
  const top=topDialog(),v=view();
  // A confirm or another sheet over the work: wait (unless this step's control is in it).
  const root=top||document;
  if(top&&top.id!=='sheet'){const el=s.kind?null:find(s,top);return el?{el}:{hold:true};}
  if(s.kind==='open'){if(c.open)return {done:true};const p=pick(OPEN_AT);return p?{el:p.el,text:p.text}:top?backOut():{};}
  if(v==='summary'&&s.kind!=='sum')return {done:true};          // the day is closed: on to the summary
  if(s.kind==='close'){if(!c.open&&c.shift_summary)return {done:true};const p=pick(END_AT);return p?{el:p.el,dock:true}:{dock:true};}
  if(s.kind==='sum'){if(v==='summary'){const el=firstVis('#sheet[open] .sum-stats')||firstVis('#sheet[open] .sheet-body');return el?{el}:{hold:true};}
    return run.shown.has('sum')?{done:true}:{nav:firstVis('#sheet[open] [data-action="summary"]')||null,navText:'Bấm xem tổng kết ngày.'};}
  if(!c.open){const p=pick(OPEN_AT);return p?{nav:p.el,navText:p.text}:top?backOut():{hold:true};}
  const el=find(s,root);if(el)return {el};
  // Its tab/fold, unless that one is already open (then the control is just not there yet).
  const via=s.v&&find(s.v,root);if(via&&!via.matches('[aria-selected="true"],[aria-pressed="true"],[aria-expanded="true"],[aria-current],.primary,.active,.on,.is-active,details[open]>summary'))return {via};
  // The game's own next step (the first-task pulse, the bottom button, the header hint) is a LATER step of this walk:
  // the player is already past this one (the customer came in by herself, say): go there.
  if(!s.x&&v==='job'){const j=ahead(root);if(j!=null)return {jump:j};}
  if((s.at||'job')==='job'&&v!=='job'&&!s.o){   // an optional step away from the work screen is just not for now
    if(top){const next=firstVis('#sheet[open] [data-action="nextJob"]');return next?{nav:next,navText:'Bấm Làm tiếp để vào việc.'}:backOut();}
    const p=pick(JOB_AT);return p?{nav:p.el,navText:'Bấm Làm tiếp để vào việc.'}:{};
  }
  return {};
}

/* ------------------------------------------------------------------ layer */
function css(){
  if(document.querySelector('link[data-coach-css]'))return;
  const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.('/css/coach.css')||'/css/coach.css';l.dataset.coachCss='1';document.head.append(l);
}
function mount(){
  if(!layer){
    css();
    layer=document.createElement('div');layer.id=LAYER;layer.className='tut-layer coach-layer';
    layer.innerHTML='<div class="tut-spot coach-spot" aria-hidden="true"></div><div class="tut-bubble coach-bubble" role="dialog" aria-live="polite" aria-label="Hướng dẫn"><i class="tut-arrow" aria-hidden="true"></i><div class="coach-body"></div></div>';
    layer.querySelector('.coach-bubble').addEventListener('click',onBubble);
  }
  const host=topDialog()||document.body;
  if(layer.parentElement!==host)host.append(layer);
  return layer;
}
function onBubble(e){
  const b=e.target.closest('[data-coach-btn]');if(!b)return;
  e.preventDefault();e.stopPropagation();
  const what=b.dataset.coachBtn;
  if(what==='off'){stopCoach('off');return;}
  if(what==='skip'||what==='next'){if(run.final){finish();return;}run.skip();saveRun();last={};tick();}
}
/** The guide line under "Chi tiết": [[Nút]] in bold (the English pack translates the line whole, marks included). */
const marks=d=>esc(L(d)).replace(/\[\[(.+?)\]\]/g,'<b class="coach-key">$1</b>');
const detail=marks;
function bubbleHTML(f){
  const s=f.step,mode=f.mode;
  const head=mode==='nav'?(f.text||'Bấm Làm tiếp để vào việc.'):mode==='via'?(s.v?.t||'Mở mục này trước.'):s.t;
  const where=mode==='fallback'?(s.w||'Chưa thấy nút này: làm tiếp, tới lượt là nó hiện.'):mode==='nav'||mode==='via'?s.t:'';
  const text=(mode==='spot'||mode==='dock-spot')&&f.text?f.text:head;
  const main=s.x||mode==='text'?['next',run.final?'Xong 🎉':'Tiếp']:s.kind==='sum'?['next','Xong 🎉']:['skip','Bỏ qua'];
  // The close step stays up while the player keeps working: one slim line, no footer.
  if(mode==='dock'||mode==='dock-spot'||f.slim)return `<div class="tut-row coach-dock"><span class="tut-emoji" aria-hidden="true">${esc(s.e)}</span><p class="tut-text">${marks(text)}</p>`+
    `<button type="button" class="btn ghost small coach-skip" data-coach-btn="skip">${esc(L('Bỏ qua'))}</button>`+
    `<button type="button" class="icon-btn coach-x" data-coach-btn="off" aria-label="${esc(L('Tắt hướng dẫn'))}">✕</button></div>`;
  return `<div class="tut-row"><span class="tut-emoji" aria-hidden="true">${esc(mode==='nav'?'👉':s.e||'👉')}</span><div class="coach-words"><p class="tut-text">${marks(text)}</p>`+
    (where?`<p class="coach-where">${marks(where)}</p>`:'')+
    (s.d?`<details class="coach-more"><summary>${esc(L('Chi tiết'))}</summary><p>${detail(s.d)}</p></details>`:'')+`</div></div>`+
    `<div class="tut-foot coach-foot"><span class="coach-n" aria-label="${esc(L('Bước'))} ${run.n}/${run.total}">${run.n}/${run.total}</span><span class="grow"></span>`+
    `<button type="button" class="btn ghost small" data-coach-btn="off">${esc(L('Tắt hướng dẫn'))}</button>`+
    `<button type="button" class="btn ${main[0]==='next'?'primary':'ghost coach-skip'} small" data-coach-btn="${main[0]}">${esc(L(main[1]))}</button></div>`;
}
/** Under the target, else above it, else at the bottom; no target: under the sheet's header (where the work screen
 * keeps its hint) so the bottom bar stays free. */
function place(bubble,arrow,r){
  const W=innerWidth,H=innerHeight,m=10,bw=Math.min(340,W-2*m),bh=bubble.offsetHeight||110;
  bubble.style.width=bw+'px';
  if(!r){
    const head=$('dialog[open] .sheet-head')?.getBoundingClientRect(),top=head&&head.bottom>0?head.bottom+8:(document.getElementById('topbar')?.getBoundingClientRect().bottom||0)+(m+48);
    bubble.style.left=Math.round((W-bw)/2)+'px';bubble.style.top=Math.round(Math.min(H-bh-m,Math.max(m,top)))+'px';arrow.hidden=true;return;
  }
  const below=r.bottom+14+bh<=H-m,above=r.top-14-bh>=m;
  let top,side;
  if(below&&(r.top>H*0.55?!above:true)){top=r.bottom+14;side='top';}
  else if(above){top=r.top-14-bh;side='bottom';}
  else{top=Math.max(m,Math.min(H-bh-m,r.top>H/2?m:H-bh-m));side='';}
  const left=Math.round(Math.min(W-bw-m,Math.max(m,r.left+r.width/2-bw/2)));
  bubble.style.left=left+'px';bubble.style.top=Math.round(top)+'px';
  arrow.hidden=!side;arrow.dataset.side=side;
  arrow.style.left=Math.round(Math.min(bw-22,Math.max(10,r.left+r.width/2-left-8)))+'px';
}
function ensureInView(el){
  const r=el.getBoundingClientRect();
  // The sheet's sticky header and bottom bar cover part of the screen: what is under them is not "in view".
  const d=el.closest('dialog');let top=0,bottom=innerHeight;
  if(d){
    const hd=d.querySelector('.sheet-head'),head=hd?.getBoundingClientRect();if(head&&head.bottom>0&&!hd.contains(el))top=head.bottom;
    for(const bar of d.querySelectorAll('.sheet-foot,.ui-bar,.gd-ctas')){
      if(bar.contains(el)||!vis(bar))continue;const b=bar.getBoundingClientRect(),pos=getComputedStyle(bar).position;
      if((pos==='sticky'||pos==='fixed')&&b.top>innerHeight*0.4)bottom=Math.min(bottom,b.top);
    }
  }
  const seen=Math.min(r.bottom,bottom)-Math.max(r.top,top);
  if(seen>=Math.min(r.height,bottom-top)*0.8)return;
  let box=el.parentElement;
  while(box&&box!==d&&!(box.scrollHeight>box.clientHeight+2&&/auto|scroll/.test(getComputedStyle(box).overflowY)))box=box.parentElement;
  const by=r.top+r.height/2-(top+bottom)/2;
  if(box&&box.scrollHeight>box.clientHeight+2){try{box.scrollBy({top:by,behavior:reduced()?'auto':'smooth'});}catch{box.scrollTop+=by;}}
  else try{el.scrollIntoView({block:'center',behavior:reduced()?'auto':'smooth'});}catch{el.scrollIntoView?.();}
}

/** Draw a frame of the run. */
function draw(f){
  drawn=f;
  if(!f||f.mode==='hidden'||f.mode==='end'){if(layer)layer.hidden=true;return;}
  const L0=mount();L0.hidden=false;
  const spot=L0.querySelector('.coach-spot'),bubble=L0.querySelector('.coach-bubble'),arrow=L0.querySelector('.tut-arrow'),body=L0.querySelector('.coach-body');
  const ringed=['spot','via','nav','dock-spot'].includes(f.mode)?f.el:null;
  // Dock (the close step while the player still works): no dim, only a ring on the button when it is there.
  L0.classList.toggle('coach-calm',f.mode==='dock'||f.mode==='dock-spot'||f.mode==='fallback'||f.mode==='text');
  L0.classList.toggle('still',reduced());
  const key=[f.step?.id,f.mode,f.text||'',run.n,f.slim?1:0].join('|');
  if(last.key!==key){
    const open=body.querySelector('.coach-more')?.open&&last.step===f.step?.id;
    last={key,step:f.step?.id};body.innerHTML=bubbleHTML(f);
    if(open)body.querySelector('.coach-more').open=true;
    if(ringed&&last.el!==ringed)ensureInView(ringed);
  }
  last.el=ringed;
  const r=ringed?.getBoundingClientRect()||null,pad=6;
  const box=r&&{x:Math.max(0,Math.round(r.left-pad)),y:Math.max(0,Math.round(r.top-pad))};
  const rect=r?[box.x,box.y,Math.min(innerWidth,Math.round(r.right+pad))-box.x,Math.min(innerHeight,Math.round(r.bottom+pad))-box.y]:null;
  const sig=JSON.stringify([rect,innerWidth,innerHeight,bubble.offsetHeight,f.mode]);
  if(last.sig!==sig){
    last.sig=sig;spot.hidden=!rect;
    if(rect){const [x,y,w,h]=rect;Object.assign(spot.style,{left:x+'px',top:y+'px',width:w+'px',height:h+'px'});}
    place(bubble,arrow,r&&{left:r.left-pad,top:r.top-pad,right:r.right+pad,bottom:r.bottom+pad,width:r.width+2*pad,height:r.height+2*pad});
  }
}
function tick(){
  if(!run)return;
  // The player went to work somewhere else: this walk ends quietly (⋯ → 🧭 Hướng dẫn starts it again), so the new
  // place gets its own chip or walk.
  const cur=S()?.current;if(cur&&cur!==run.cid){stopCoach('away',{quiet:true});return;}
  const f=run.frame(probe,{busy:()=>(E?.api?.waiting|0)>0});
  // A "where is it" bubble that stays (its control comes later in the day): after a few seconds, one slim line.
  if(f.mode==='fallback'){if(fb.id!==f.step.id)fb={id:f.step.id,at:performance.now()};f.slim=performance.now()-fb.at>5000;}else fb={};
  if(f.mode==='end'){finish();return;}
  draw(f);
}
const again=()=>{if(run&&!raf)raf=requestAnimationFrame(()=>{raf=0;if(drawn&&run){last.sig='';draw(drawn);}});};

/* ------------------------------------------------------------------ flow */
const saveRun=()=>{if(run)put({c:run.cid,i:run.steps[run.i]?.id||'',t:Date.now()});};
/** Load the words (once), then run the coach at `cid` from the start (or from the saved step `at`). */
export async function startCoach(env,cid,{at=null,auto=false}={}){
  E=env||E;wire();
  if(!cid||starting)return false;
  starting=true;
  try{await loadCoach();}finally{starting=false;}
  if(!DATA?.careers?.[cid])return false;
  stopCoach('restart',{quiet:true});hideChip();
  const steps=planFor(DATA,cid),k=at?steps.findIndex(s=>s.id===at):0;
  run=new CoachRun({cid,steps,at:Math.max(0,k),now:()=>performance.now()});
  markCoach(E,cid);markGuideSeen(E,cid);   // offered: no chip again, and no "Lần đầu làm ở đây?" card on top of it
  saveRun();last={};
  clearInterval(timer);timer=setInterval(tick,160);tick();
  return true;
}
export function stopCoach(reason,{quiet=false}={}){
  if(!run)return;
  const cid=run.cid;run=null;clearInterval(timer);timer=0;put(null);
  layer?.remove();last={};drawn=null;
  if(reason==='done')markCoach(E,cid,{done:true});
  if(!quiet&&reason==='off')E?.toast?.(L('Đã tắt. Xem lại: ⋯ → 🧭 Hướng dẫn'),'hint');
  clearInterval(watchT);watchT=setInterval(check,900);
}
function finish(){if(!run)return;stopCoach('done');E?.toast?.(L('Xong hướng dẫn nghề này! Xem lại: ⋯ → 🧭 Hướng dẫn'),'good');}
export const coachRunning=()=>!!run;
/** Read-only view for the browser walkthrough (scripts/browser_coach.py): where the run is and what is ringed. */
globalThis.__mnlCoach={get:()=>run?{cid:run.cid,i:run.i,id:run.step?.id||'',n:run.n,total:run.total,mode:drawn?.mode||'',t:drawn?.step?.t||''}:null,el:()=>drawn?.el||null,chip:()=>!!chip?.isConnected};
/** The coach or its chip is on screen (announce.js / tips.js keep their own notes away meanwhile). */
export const coachOn=()=>!!run||!!chip?.isConnected;
export function loadCoach(){
  loading??=import('./coach-content.js').then(m=>{DATA=m.default||null;}).catch(error=>{console.error('coach:',error);loading=null;});
  return loading;
}

/** Taps: a tap on the step's control (or a later step's: the player knew the way) moves the run on once the game
 * answers. */
function onClick(e){
  if(!run||e.target.closest?.(`#${LAYER}`))return;
  const el=e.target.closest?.(CTRL+',input,select,textarea,label');if(!el||off(el)||el.closest(OPENERS))return;
  // A control that sends a command counts once the game takes it; a tab, a fold, a field after a short pause.
  const cmd=!!el.closest('[data-command],[data-action="v4Cmd"],[data-action="expDo"],[data-op]');
  const f=drawn;
  if(f?.mode==='spot'&&f.el&&(f.el===el||f.el.contains(el)||el.contains(f.el))&&!f.step.kind){run.tap(run.i,{cmd});return;}
  const j=run.which(s=>owns(s,el));if(j!=null)run.tap(j,{cmd});
}

/* ------------------------------------------------------------------ who gets it */
/** A save named with this onboarding, still on its first life day, no workplace worked yet: it starts with the coach. */
function freshSave(s){
  const seen=String(s?.settings?.notesSeen||'').split(',');
  return seen.includes('onb1')&&!!s?.journey?.story&&(Number(s.journey.life_day)||1)<=1&&
    Object.values(s.careers||{}).every(c=>!c||(Number(c.day)||1)<=1&&!(Number(c.metrics?.served)>0));
}
/** The player is at work at `cid` and nothing comes first (the story intro, the job application, another guide). */
function ready(s,cid){
  const c=s?.careers?.[cid],J=s?.journey;
  if(!c||J?.story&&!J.intro)return false;
  if(c.job?.required&&c.job.status!=='hired')return false;
  if(otherGuide()||E?.ui?.paused||document.documentElement.classList.contains('menu-open'))return false;
  const top=topDialog();return !top||top.id==='sheet';
}
/** 'auto' (start now), 'chip' (offer it), or null, for the current workplace of `state`. Exported for the tests. */
export function coachDue(s,seen){
  const cid=s?.current,c=s?.careers?.[cid];
  if(!cid||!c||seen.offered.has(cid))return null;
  return seen.native&&(Number(c.day)||1)<=1&&!c.shift_summary?'auto':'chip';
}
let watchT=0;
function check(){
  const s=S();if(!s||run)return;
  const seen=coachSeen(E.api);
  if(!seen.native&&freshSave(s)){markNoteSeen(E,COACH_NEW);seen.native=true;}
  const cid=s.current,due=coachDue(s,seen);
  if(!due||!ready(s,cid)){hideChip();return;}
  // Only on the work screen or the town (not over another sheet such as the stock or the summary).
  const v=view();if(v&&v!=='job'&&v!=='home'){hideChip();return;}   // the classic town is the 'home' sheet (v4/town-walk.js)
  if(due==='auto'){hideChip();startCoach(E,cid,{auto:true});return;}
  showChip(cid);
}
function showChip(cid){
  const host=topDialog()||document.body;
  if(chip?.dataset.career===cid&&chip.parentElement===host){placeChip();return;}
  hideChip();css();
  // Its own classes: the 2.5D phone layout folds the announce pill (.tut-pill) to an icon, this one keeps its words.
  chip=document.createElement('aside');chip.id=CHIP;chip.className='coach-chip';chip.setAttribute('role','status');chip.dataset.career=cid;
  chip.innerHTML=`<button type="button" class="coach-chip-go" data-chip="go"><span class="coach-chip-emoji" aria-hidden="true">🧭</span><span class="coach-chip-text">${esc(L('Có hướng dẫn mới cho nghề này'))}</span><b>${esc(L('Xem'))}</b></button><button type="button" class="coach-chip-x" data-chip="x" aria-label="${esc(L('Để sau'))}">✕</button>`;
  chip.addEventListener('click',e=>{
    const b=e.target.closest('[data-chip]');if(!b)return;
    e.preventDefault();e.stopPropagation();
    const id=chip?.dataset.career;hideChip();
    if(b.dataset.chip==='go')startCoach(E,id);else{markCoach(E,id);E?.toast?.(L('Xem lại: ⋯ → 🧭 Hướng dẫn'),'hint');}
  });
  host.append(chip);placeChip();
}
/** Under the sheet's header (inside the work sheet) or the top bar (the town), never over the bottom buttons. */
function placeChip(){
  if(!chip)return;
  chip.hidden=!!document.querySelector('details.head-more[open]');   // the ⋯ menu is open under it
  const inSheet=chip.parentElement?.tagName==='DIALOG';
  chip.classList.toggle('in-sheet',inSheet);
  // The 2.5D town: coach.css puts it above the main button, where the scene's notes go (nothing to measure).
  if(!inSheet&&document.documentElement.dataset.game==='isometric'){chip.style.top='';return;}
  const head=inSheet?chip.parentElement.querySelector('.sheet-head')?.getBoundingClientRect():null;
  const top=head&&head.bottom>0?head.bottom+6:(document.getElementById('topbar')?.getBoundingClientRect().bottom||0)+8;
  chip.style.top=Math.round(top)+'px';
}
function hideChip(){chip?.remove();chip=null;}

/* ------------------------------------------------------------------ boot */
function wire(){
  if(wired)return;wired=true;
  document.addEventListener('click',onClick,true);
  const api=E?.api;
  // A wrong answer the game takes but keeps the player on (result.correct === false) does not move the walk on.
  api?.addEventListener?.('result',e=>{if(run&&(!e.detail?.career||e.detail.career===run.cid))run.answered(e.detail?.result?.correct!==false);});
  api?.addEventListener?.('rejected',()=>{if(run)run.answered(false);});
  api?.addEventListener?.('state',()=>{if(run)tick();});
  addEventListener('resize',again);addEventListener('layoutchange',again);addEventListener('scroll',again,true);
}
/** Start watching (tutorial/index.js): pick up a run left by a reload, else the chip / the automatic start. */
export function coachBoot(env){
  E=env;wire();
  const saved=get(),cid=env?.api?.state?.current;
  if(saved&&saved.c===cid&&Date.now()-(Number(saved.t)||0)<12*3600e3)setTimeout(()=>startCoach(env,cid,{at:saved.i,auto:true}),900);
  else if(saved)put(null);
  clearInterval(watchT);watchT=setInterval(check,900);
}
