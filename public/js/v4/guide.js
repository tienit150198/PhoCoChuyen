/** Next-step guide for every work screen (onboarding v0.7).
 *
 * A work screen describes what is left to do as steps:
 *   {ok:true|false|null, label, note?, go?}
 * ok=true is done, false is wrong (needs fixing), null is not done yet. `go` says
 * how to do it:
 *   {cmd, payload, confirm?}     one tap sends the command (confirm asks first)
 *   {act:'car:tab', data:{…}}    one tap runs a client action (module or shell)
 *   {sel:'css selector'}         scroll to the control that does it and highlight it
 * plus an optional `label` for the button (defaults to the step's label). A step may also
 * name `pulse`: the exact control to glow on a first task (e.g. the right choice when the
 * step is a decision), since a first task must be doable by pressing what glows.
 *
 * The same steps drive three things: tappable checklist rows (stepRows), the
 * one-line "Bước tiếp theo" hint that the host pins in the sheet header
 * (nextHint), and the bottom button (stepCta), which always does the next step
 * or names it, never a mute grey button. A button that only points (go.sel) looks
 * and reads like a pointer ("👆 Chạm: Ly M", outlined): pressing it makes the control
 * glow under a small ▼, it never does the step. On the first task in a career the
 * next control pulses gently (applyGuide). While a work screen has its button bar
 * pinned at the bottom, notes (toasts) sit in one line right above it (placeToasts).
 * Pure string builders + one DOM pass. */
import {escapeHTML as esc} from '../icons.js';
import {syncBar} from './action-bar.js';
import {whyAttrs,placeChips,clean,actBar} from '../ui-kit.js';

/** The next step: the first one not done yet that can be done from here (wrong ones count
 * as not done); a step with no way to do it (sold out, waiting) only counts when nothing else is left. */
export function pending(steps){
  const open=(steps||[]).filter(s=>s&&s.ok!==true);
  return open.find(s=>s.go)||open[0]||null;
}
/** Steps still open, for "Còn 2 bước". */
export const left=steps=>(steps||[]).filter(s=>s&&s.ok!==true).length;

/** How the finishing button sends `cmd`: straight through (with confirm:true when the server asks
 * for it) once every step is done, otherwise after a question that names what is still open. */
export function finalGo(steps,cmd,payload={},{question='',confirm=false}={}){
  const n=pending(steps);
  if(!n)return {cmd,payload:confirm?{...payload,confirm:true}:payload};
  const k=left(steps);
  return {cmd,payload,confirm:`Còn ${k} bước chưa xong: ${n.label}.${question?' '+question:''} Vẫn làm luôn?`};
}

const attrsOf=data=>Object.entries(data||{}).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');

/** data-* attributes that make any element perform a step through the global click delegate. */
export function goAttrs(go){
  if(!go)return '';
  // go.cost / go.pocket ('fund' by default, 'wallet'): the confirm then says how much is missing (v4/money.js).
  if(go.cmd&&go.confirm)return ` data-action="v4Cmd" data-op="${esc(go.cmd)}" data-payload="${esc(JSON.stringify(go.payload||{}))}" data-confirm="${esc(go.confirm)}"${go.cost?` data-cost="${esc(go.cost)}" data-pocket="${esc(go.pocket||'fund')}"`:''}`;
  if(go.cmd)return ` data-command="${esc(go.cmd)}" data-payload="${esc(JSON.stringify(go.payload||{}))}"`;
  if(go.act)return ` data-action="${esc(go.act)}"${attrsOf(go.data)}`;
  if(go.sel)return ` data-action="v4Go" data-sel="${esc(go.sel)}"`;
  return '';
}

/** A step the bottom button can only point at (no command or action to send). */
export const pointsOnly=go=>!!(go&&go.sel&&!go.cmd&&!go.act);
/** A label as plain words, without the leading "👉"/emoji and a trailing arrow: "🧋 Lấy ly M" → "Lấy ly M".
 * `html`: the label is markup (a go.label); a step's own label is plain text. */
export function bareLabel(s,html=true){
  return (html?plainText(s):String(s??'').replace(/\s+/g,' ').trim()).replace(/^[\p{Extended_Pictographic}\p{Emoji_Modifier}\u200d\ufe0f\s]+/u,'').replace(/\s*[→›]$/,'').trim();
}

/** First task in this career (no customer served yet): the next control pulses. */
export const firstTime=x=>!((x?.room?.metrics?.served)>0);

/** Checklist rows: done rows stay plain, the rest become buttons with a small "→". */
export function stepRows(x,steps,label='Việc cần làm'){
  return `<ul class="checklist gd-list" aria-label="${esc(label)}">${(steps||[]).filter(Boolean).map(s=>{
    const cls=s.ok===true?'ok':s.ok===false?'bad':'',mark=s.ok===true?'✓':s.ok===false?'✗':'○';
    const tap=s.ok!==true&&s.go?` role="button" tabindex="0"${goAttrs(s.go)}`:'';
    return `<li class="${cls}${tap?' gd-todo':''}"${tap}><span>${mark}</span>${esc(s.label)}${s.note?`<small>${esc(s.note)}</small>`:''}${tap?'<i class="gd-go" aria-hidden="true">→</i>':''}</li>`;
  }).join('')}</ul>`;
}

/** Same as stepRows for code that already has its own list markup: attributes + arrow for one row. */
export const todoAttrs=s=>s&&s.ok!==true&&s.go?` role="button" tabindex="0"${goAttrs(s.go)}`:'';
export const todoArrow=s=>s&&s.ok!==true&&s.go?'<i class="gd-go" aria-hidden="true">→</i>':'';

/** Where the first-time pulse goes: the bottom button when it does the step, else the control. */
function pulseSel(step,cta){
  if(step&&'pulse' in step)return step.pulse||'';   // '' = nothing to light (the right choice is unknown)
  if(!step?.go)return '';
  if(step.go.sel)return step.go.sel;
  return cta?'.gd-cta':'.gd-next .gd-hint';
}

/** One line: "Bước tiếp theo · <label> →", tapping it does the step (or jumps to it).
 * When nothing is left it offers `final` ({label (text), go}) or just says `done`. The host
 * moves it into the sticky sheet header, so it is always in view. */
export function nextHint(x,steps,{done='',final=null,cta=true,pulse='',glow=false}={}){
  let n=pending(steps);
  if(!n&&final?.go)n={label:final.label,go:final.go};
  if(!n&&!done)return '';
  // `glow`: pulse the next control even after the first task (a detour the player was sent on, e.g. restocking).
  const first=glow||firstTime(x)?' data-first="1"':'';
  if(!n)return `<div class="gd-next done" role="status"${first}${pulse?` data-pulse="${esc(pulse)}"`:''}><small>Bước tiếp theo</small><b>${esc(done)}</b></div>`;
  const sel=pulse||pulseSel(n,cta);
  const tap=goAttrs(n.go);
  return `<div class="gd-next" role="status"${first}${sel?` data-pulse="${esc(sel)}"`:''}><small>Bước tiếp theo</small><button type="button" class="gd-hint"${tap}><b>${n.go?.label||esc(n.label)}</b>${n.note?`<span class="gd-note">${esc(n.note)}</span>`:''}${/[→›]\s*$/.test(plainText(n.go?.label||n.label))?'':'<i aria-hidden="true">→</i>'}</button></div>`;
}

/** Markup or escaped text as plain text (tags dropped, the usual entities decoded). */
export function plainText(s){
  return String(s??'').replace(/<[^>]*>/g,'').replace(/&(amp|lt|gt|quot|#39);/g,(_,k)=>({amp:'&',lt:'<',gt:'>',quot:'"','#39':"'"})[k]).replace(/\s+/g,' ').trim();
}
/** The next step as one plain line, worded like the "Bước tiếp theo" hint (its button label when it
 * has one, "📷 Quét 2 ổ bánh mì" rather than the checklist row "2 ổ bánh mì"). Career modules return it
 * from next(), which the main screen's task card shows as its one line. */
export function stepLine(n){
  if(!n)return '';
  const line=plainText(n.go?.label||'').replace(/^👉\s*/,'').replace(/\s*[→›]$/,'').trim();
  return line||plainText(n.label);
}

/** The bottom button. `final` = {label, go, ready, style?}: the finishing action (label is HTML).
 * - nothing left, or the next step has no way to do it: the finishing button;
 * - otherwise a big button that does (or points to) the next step; when the finish is
 *   already allowed it stays reachable as a small "or finish now" link under it. */
export function stepCta(x,steps,final,{style='primary big grow'}={}){
  const n=pending(steps);
  final=gate(final);
  // Not ready yet: dimmed but tappable (a tap says why and offers the fix, ui-kit whyTap), never a mute grey button.
  const fin=(cls,why='')=>`<button type="button" class="btn ${cls}${why?' is-why':''}"${goAttrs(final.go)}${why?whyAttrs({why,fix:final.fix}):''}>${final.label}</button>`;
  if(!n||!n.go){
    if(final.ready!==false)return fin(`${style} gd-cta gd-final`);
    // The server's reason is a sentence of its own; the page's guess names the step still open.
    if(final.said)return `<div class="gd-ctas">${fin(style,final.why)}<small class="gd-why">${esc(final.why)}</small></div>`;
    const why=n?n.label:(final.why||'');
    return `<div class="gd-ctas">${fin(style,why?`Còn: ${why}`:'Chưa xong')}${why?`<small class="gd-why">Còn bước: ${esc(why)}</small>`:''}</div>`;
  }
  // Pointer: outlined, with a hand, "👆 <what to tap>"; applyGuide names the control itself once it is on screen.
  const say=pointsOnly(n.go)?(n.go.label&&bareLabel(n.go.label))||bareLabel(n.label,false):'';
  const outline=['btn',...style.split(/\s+/).filter(c=>c&&c!=='primary'),'gd-cta','gd-point'].join(' ');
  const step=say?`<button type="button" class="${outline}"${goAttrs(n.go)} data-say="${esc(say)}" aria-label="${esc('Chỉ chỗ: '+say)}">👆 ${esc(say)}</button>`
    :`<button type="button" class="btn ${style} gd-cta"${goAttrs(n.go)}>${n.go.label||`👉 ${esc(n.label)}`}</button>`;
  if(final.ready===false)return step;
  return `<div class="gd-ctas">${step}<button type="button" class="gd-alt"${goAttrs(final.go)}>hoặc ${final.alt||final.label}</button></div>`;
}

/** The server's pre-check for the finishing action (final.can: true | {why, fix}, from the career's public
 * view, game/careers/kit.py check) overrides the client's own guess: same rules as the refusal. */
function gate(final){
  const can=final?.can;
  if(!final||can===undefined||can===null)return final||{label:'',go:null,ready:false};
  if(can===true)return final;
  return {...final,ready:false,why:can.why||final.why,fix:can.fix||final.fix,said:!!can.why};
}

/** The bottom bar's two slots for ui-kit actBar ({next, main}): one row, the next step on the left, the one main
 * button on the right (docs/UI_KIT.md).
 * - the next step is a command: it is the main button; finishing early, when allowed, is a quiet link on the left;
 * - the next step only points (go.sel): "👆 <what>" on the left, the finishing button on the right (secondary
 *   while steps are left, dimmed with its reason when it cannot go yet);
 * - nothing left: the finishing button alone. */
export function barParts(x,steps,final,{style='primary big'}={}){
  final=gate(final);
  const n=pending(steps),has=!!(final.label&&final.go);
  const fin=(cls,why='')=>`<button type="button" class="btn ${cls} gd-final${why?' is-why':''}"${goAttrs(final.go)}${why?whyAttrs({why,fix:final.fix}):''}>${final.label}</button>`;
  const note=(t,cls='')=>`<span class="ui-note${cls?' '+cls:''}">${t}</span>`;
  if(!n||!n.go){
    if(!has)return {next:n?note(esc(n.label)):'',main:''};
    if(final.ready!==false)return {next:'',main:fin(`${style} gd-cta`)};
    const why=final.said?final.why:n?n.label:(final.why||'');
    return {next:why?note(`<span aria-hidden="true">⏳</span> ${esc(why)}`,'gd-why'):'',main:fin(style.replace(/\bprimary\b/,'').trim()+' gd-cta',why||'Chưa xong')};
  }
  const say=pointsOnly(n.go)?(n.go.label&&bareLabel(n.go.label))||bareLabel(n.label,false):'';
  if(say){
    const chip=`<button type="button" class="btn ui-next gd-cta gd-point"${goAttrs(n.go)} data-say="${esc(say)}" aria-label="${esc('Chỉ chỗ: '+say)}">👆 ${esc(say)}</button>`;
    if(!has)return {next:'',main:chip};
    const quiet=style.replace(/\bprimary\b/,'').trim();
    return {next:chip,main:final.ready===false?fin(quiet,final.why||n.label):fin(quiet)};
  }
  const step=`<button type="button" class="btn ${style} gd-cta"${goAttrs(n.go)}>${n.go.label||`👉 ${esc(n.label)}`}</button>`;
  if(!has||final.ready===false)return {next:'',main:step};
  return {next:`<button type="button" class="gd-alt"${goAttrs(final.go)}>hoặc ${final.alt||final.label}</button>`,main:step};
}

/** A whole bottom bar from the guide: barParts in ui-kit actBar. `note` fills the left slot when the guide has
 * nothing for it (a count like "3/6"); `top` is a full-width row above; `cls` the career's own hook class. */
export function stepBar(x,steps,final,{cls='',top='',note='',style}={}){
  const {next,main}=barParts(x,steps,final||{label:'',go:null,ready:false},style?{style}:{});
  return actBar({next:next||note,main,top,cls});
}

/* ---------------------------------------------------------------- host side */

const calm=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Scroll to a control and make it glow for a moment (scroll:false: it is in view already, keep the screen still). */
export function highlight(el,{scroll=true}={}){
  if(!el)return false;
  const box=el.closest('details:not([open])');if(box)box.open=true;
  if(scroll||box){el.scrollIntoView({block:'center',behavior:calm()?'auto':'smooth'});uncover(el);}
  // The glow restarts two frames later instead of through a forced reflow (void el.offsetWidth).
  el.classList.remove('gd-flash');clearTimeout(el._gd);
  requestAnimationFrame(()=>requestAnimationFrame(()=>{if(!el.isConnected)return;el.classList.add('gd-flash');clearTimeout(el._gd);el._gd=setTimeout(()=>el.classList.remove('gd-flash'),2400);}));
  return true;
}

/** The pinned thing (sticky or fixed: the sheet header, an order ticket, the button bar) drawn over `el`'s top
 * or bottom edge, or null when both edges show. */
function coverOf(el){
  const r=el.getBoundingClientRect(),x=r.left+r.width/2,pad=Math.min(12,r.height/2);
  for(const y of [r.top+pad,r.bottom-pad]){
    if(y<0||y>innerHeight)return document.documentElement;   // off screen
    const hit=document.elementFromPoint(x,y);
    if(!hit||el.contains(hit)||hit.closest('.toasts,.gd-mark'))continue;   // a passing note is not in the way
    for(let e=hit;e&&e!==document.body;e=e.parentElement){
      const p=getComputedStyle(e).position;
      if(p==='sticky'||p==='fixed')return e;
    }
  }
  return null;
}
/** Centring a control ignores what is pinned over the page (a phone's order ticket under the header): once the
 * scroll ends, a control still under one is moved just clear of it. */
function uncover(el){
  let sc=el.parentElement;
  while(sc&&!/(auto|scroll)/.test(getComputedStyle(sc).overflowY))sc=sc.parentElement;
  if(!sc)return;
  let done=false;
  const fix=()=>{
    if(done)return;done=true;sc.removeEventListener('scrollend',fix);
    if(!el.isConnected)return;
    const c=coverOf(el);if(!c||c===document.documentElement)return;
    const r=el.getBoundingClientRect(),k=c.getBoundingClientRect();
    const by=k.top<=r.top?-(k.bottom+8-r.top):r.bottom+8-k.top;
    if(Math.abs(by)<sc.clientHeight/2)sc.scrollBy({top:by,behavior:calm()?'auto':'smooth'});
  };
  sc.addEventListener('scrollend',fix);
  setTimeout(fix,calm()?60:700);   // no scrollend (nothing to scroll, older browsers)
}

/** Two controls that perform the same step (payload compared as data, so key order does not matter). */
function sameGo(a,b){
  const d=a.dataset,e=b.dataset;
  if((d.command||'')!==(e.command||'')||(d.action||'')!==(e.action||'')||(d.op||'')!==(e.op||''))return false;
  const norm=v=>{try{const o=JSON.parse(v||'{}');return JSON.stringify(Object.keys(o).sort().map(k=>[k,o[k]]));}catch{return v||'';}};
  return norm(d.payload)===norm(e.payload);
}

/** Called after every sheet render: pin the hint in the header and pulse the next control
 * on a first task. Never blocks: the pulse is decoration only. */
export function applyGuide(dialog){
  if(!dialog)return;
  // A hint inside a shut fold (e.g. the between-orders panel folded under a finished task) stays there.
  const hint=[...dialog.querySelectorAll('.sheet-body .gd-next')].find(h=>!h.closest('details:not([open])'));
  const head=dialog.querySelector('.sheet-head .grow');
  if(hint&&head){
    head.querySelector(':scope>p')?.remove();head.append(hint);
    // The bottom button (or a desk's "Việc bây giờ" card) already shows and does this step: the header keeps
    // the line for screen readers only (role=status), so the header stays one line. A hint whose note has words
    // (e.g. an allergy) not written anywhere in the body stays in sight; a bare count ("1/3", "P3: 67/100") does not.
    const body=dialog.querySelector('.sheet-body'),note=hint.querySelector('.gd-note')?.textContent.trim();
    const open=e=>!e.closest('details:not([open])'),b=hint.querySelector('.gd-hint');
    // A control in the body that does exactly what the hint does (same command/action and payload).
    const twin=b&&body&&(b.dataset.command||(b.dataset.action&&b.dataset.action!=='v4Go'))?[...body.querySelectorAll('button:not([disabled]),[role="button"]')].find(c=>open(c)&&sameGo(c,b)):null;
    const dup=!!body&&(!note||!/\p{L}{2}/u.test(note)||body.textContent.includes(note))&&(!!twin||[...body.querySelectorAll('.gd-cta:not([disabled])')].some(open)||[...body.querySelectorAll('.dw-now')].some(open));
    hint.classList.toggle('gd-dup',dup);hint._twin=dup?twin:null;
    if(b){if(dup)b.tabIndex=-1;else b.removeAttribute('tabindex');}
  }
  pointers(dialog);
  if(clean())placeChips(dialog);
  const cur=hint||dialog.querySelector('.gd-next');
  if(cur?.dataset.first&&cur.dataset.pulse){
    const sel=cur.classList.contains('gd-dup')?cur.dataset.pulse.replace('.gd-next .gd-hint','.gd-cta'):cur.dataset.pulse;
    // The sheet may not be shown yet on its first render: pick by markup, not by layout.
    let el=cur._twin&&cur.dataset.pulse.includes('.gd-next .gd-hint')&&!dialog.querySelector('.sheet-body .gd-cta:not([disabled])')?cur._twin
      :[...dialog.querySelectorAll(sel)].find(e=>!e.disabled&&!e.closest('[hidden],details:not([open])>:not(summary)'));
    // A pointer never pulses itself (it does nothing on its own): the control it points at does.
    if(el?.matches('.gd-point'))el=goTarget(dialog,el.dataset.sel).el;
    el?.classList.add('gd-pulse');
  }
  placeToasts(dialog);
}

// checkVisibility needs styles only (offsetParent forced a full layout on every tap); old browsers: offsetParent.
const shown=e=>typeof e.checkVisibility==='function'?e.checkVisibility():e.offsetParent!==null;

/** The control a pointer step names: {el, one} (one = a single control, not a set of options). */
function goTarget(root,sel){
  let all=[];try{all=[...root.querySelectorAll(sel||'')];}catch{/* a bad selector points nowhere */}
  const seen=all.filter(shown);
  let el=seen[0]||all[0]||null;
  // Several matches (a set of options): glow the group that holds them, not the first one, which would read
  // as "pick this" (the step never suggests an answer). A group as wide as the whole sheet: the first one.
  if(seen.length>1){let box=seen[0].parentElement;while(box&&!seen.every(e=>box.contains(e)))box=box.parentElement;
    if(box&&!box.matches('.sheet-body,#sheetContent,dialog,body,.career-job'))el=box;}
  return {el,one:(seen.length||all.length)===1};
}

/** A control's short name for "Chạm: …": its label up to the first comma ("Trà sữa, còn 20 phần" → "Trà sữa"),
 * or its first line of words. '' when it is not one tappable control or has no short name. */
export function tapName(el){
  if(!el?.matches?.('button,[role="button"],a[href],label,summary,select,input'))return '';
  const line=s=>String(s||'').split(/\n/).map(l=>bareLabel(l.split(/[,.;:·(]/)[0],false)).find(l=>/\p{L}{2}/u.test(l))||'';
  const name=line(el.getAttribute('aria-label'))||line(el.textContent);
  return name.length<=24?name:'';
}

/** Bottom buttons that only point (data-action="v4Go"): outlined, "👆 Chạm: <the control>", read as
 * "Chỉ chỗ: …". Also covers the buttons a few careers write themselves; one with its own markup inside
 * (e.g. the salon's countdown) keeps it. Text is only written when it changes. */
function pointers(dialog){
  for(const b of dialog.querySelectorAll('.gd-cta[data-action="v4Go"]')){
    if(b.firstElementChild)continue;
    const say=b.dataset.say||bareLabel(b.textContent,false);
    if(!say)continue;
    const {el,one}=goTarget(dialog,b.dataset.sel),name=one?tapName(el):'';
    const text=`👆 ${name?`Chạm: ${name}`:say}`;
    b.classList.add('gd-point');b.classList.remove('primary');
    if(b.dataset.say!==say)b.dataset.say=say;
    if(b.dataset.tap!==name)b.dataset.tap=name;
    if(b.dataset.shown!==text){b.textContent=text;b.dataset.shown=text;b.setAttribute('aria-label',`Chỉ chỗ: ${name||say}`);}
  }
}

/** The control is on screen and not under the sticky header, a pinned order ticket or the button bar. */
function inView(el){
  const r=el.getBoundingClientRect();
  return !!(r.width&&r.height)&&!coverOf(el);
}

/** The pinned bar that holds the bottom button (sticky or fixed), or null when the button scrolls with the page.
 * A career's bar that holds its own buttons instead (the office stamp row) names itself with data-cta-bar. */
function barOf(dialog){
  const cta=[...dialog.querySelectorAll('.gd-cta,[data-cta-bar]')].find(e=>e.getClientRects().length&&!e.closest('details:not([open])'));
  for(let e=cta;e&&e!==dialog;e=e.parentElement){
    const p=getComputedStyle(e).position;
    if(p==='sticky'||p==='fixed')return e;
  }
  return null;
}

/** Toasts over a work screen with a pinned button bar: one calm line right above the bar, as wide as the bar,
 * instead of under the header where the customer and the order are (guide.css #sheet[data-gd-bar]). Measured
 * after each render and whenever a toast arrives. */
function placeToasts(dialog){
  if(!dialog||dialog.id!=='sheet')return;
  watchToasts(dialog);
  const bar=dialog.open?barOf(dialog):null,r=bar?.getBoundingClientRect();
  syncBar(dialog,r?.height?bar:null);   // the shared phone bar (v4/action-bar.js, css/compact.css)
  if(!r||!r.height){if(dialog.hasAttribute('data-gd-bar'))dialog.removeAttribute('data-gd-bar');return;}
  // A short screen leaves the bar halfway up (it sticks only once the page is taller than the sheet): the
  // note goes just under it, in the empty space, rather than over the customer above it.
  const where=innerHeight-r.bottom>=72?'below':'above';
  const set=(k,v)=>{if(dialog.style.getPropertyValue(k)!==v)dialog.style.setProperty(k,v);};
  set('--cta-bar-h',`${Math.max(0,Math.round(innerHeight-r.top))}px`);
  set('--cta-bar-b',`${Math.round(r.bottom)}px`);
  set('--cta-bar-x',`${Math.round(r.left+r.width/2)}px`);
  set('--cta-bar-w',`${Math.round(r.width)}px`);
  if(dialog.getAttribute('data-gd-bar')!==where)dialog.setAttribute('data-gd-bar',where);
  // "Ở ngay trên: …" is about one step: once its pointer is gone (the step is done), so is the line.
  const box=document.getElementById('toasts');
  for(const t of box?.querySelectorAll('.gd-say:not(.leaving)')||[])
    if(![...dialog.querySelectorAll('.gd-point')].some(b=>b.dataset.sel===t.dataset.sel))t.remove();
}
/* Measured again when a toast arrives (it may come before the new screen is drawn) and when the sheet's
 * content changes height (a customer card growing moves a bar that is not stuck to the bottom yet). */
let toastWatch=null,sizeWatch=null;
function watchToasts(dialog){
  const box=document.getElementById('toasts');
  if(box&&!toastWatch&&typeof MutationObserver==='function'){
    toastWatch=new MutationObserver(()=>{const d=box.parentElement;if(d?.id==='sheet'&&box.children.length)placeToasts(d);});
    toastWatch.observe(box,{childList:true});
  }
  const content=dialog.querySelector('#sheetContent');
  if(content&&!sizeWatch&&typeof ResizeObserver==='function'){
    sizeWatch=new ResizeObserver(()=>{if(dialog.open&&box?.children.length)placeToasts(dialog);});
    sizeWatch.observe(content);
  }
}

/** A short line in the toast spot (right above the bar): "Ở ngay trên: chạm Ly M". A tap closes it. */
function sayLine(dialog,text,sel=''){
  const box=document.getElementById('toasts');
  if(!box||!text)return;
  if(dialog?.open&&box.parentElement!==dialog)dialog.append(box);
  placeToasts(dialog);
  const el=document.createElement('div');el.className='toast hint gd-say';el.dataset.msg=text;el.dataset.sel=sel;
  const face=document.createElement('span');face.className='hint-face';face.setAttribute('aria-hidden','true');face.textContent='👆';
  el.append(face,document.createTextNode(text));
  const leave=()=>{clearTimeout(el._t);el.classList.add('leaving');setTimeout(()=>el.remove(),320);};
  el.addEventListener('click',leave);
  box.append(el);
  while(box.children.length>1)box.firstElementChild.remove();   // one note at a time, the newest wins (as app.js toast)
  el._t=setTimeout(leave,2600);
}

/** A small ▼ over the control for as long as it glows; it follows the control while the sheet scrolls to it.
 * Static under reduced motion (guide.css). */
let mark=null;
function markOver(dialog,el){
  mark?.remove();
  if(!el||!dialog)return;
  const m=mark=document.createElement('span');m.className='gd-mark';m.setAttribute('aria-hidden','true');m.innerHTML='<i>▼</i>';
  dialog.append(m);
  const end=performance.now()+2400;
  const step=now=>{
    if(m!==mark||!el.isConnected||now>end||!dialog.open){m.remove();if(m===mark)mark=null;return;}
    const r=el.getBoundingClientRect();
    m.style.transform=`translate(${Math.round(r.left+r.width/2)}px,${Math.round(r.top)}px)`;
    m.hidden=!r.width&&!r.height;
    requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

/** data-action="v4Go": scroll to the named control. Returns true when handled. The bottom pointer button
 * also puts a ▼ over it (a single control only), and when it was in view already, says so above the button ("Ở ngay trên: …"). */
export function guideAction(action,data,el){
  if(action!=='v4Go')return false;
  const root=el.closest('dialog')||document;
  const target=goTarget(root,data.sel).el;
  const point=el.matches('.gd-point')&&root!==document;
  const there=point&&!!target&&!target.closest('details:not([open])')&&inView(target);
  if(!highlight(target,{scroll:!there})&&el.closest('.gd-next'))highlight(root.querySelector('.gd-cta'));
  if(point&&target){
    // The ▼ only over one control: over a set of options (the group glows) it would land on one of them and
    // read as "pick this" (the step never suggests an answer).
    if(target.matches('button,[role="button"],a[href],label,summary,select,input'))markOver(root,target);
    if(there){const what=el.dataset.tap||el.dataset.say||'';sayLine(root,`Ở ngay trên: ${el.dataset.tap?'chạm '+what:what.charAt(0).toLowerCase()+what.slice(1)}`,el.dataset.sel);}
  }
  return true;
}

// Rows are <li role="button">: Enter and Space work like a click.
if(typeof document!=='undefined')document.addEventListener('keydown',e=>{
  if((e.key==='Enter'||e.key===' ')&&e.target?.matches?.('li.gd-todo[role="button"]')){e.preventDefault();e.target.click();}
});
