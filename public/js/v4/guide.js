/** Next-step guide for every work screen (onboarding v0.7).
 *
 * A work screen describes what is left to do as steps:
 *   {ok:true|false|null, label, note?, go?}
 * ok=true is done, false is wrong (needs fixing), null is not done yet. `go` says
 * how to do it:
 *   {cmd, payload, confirm?}     one tap sends the command (confirm asks first)
 *   {act:'car:tab', data:{…}}    one tap runs a client action (module or shell)
 *   {sel:'css selector'}         scroll to the control that does it and highlight it
 * plus an optional `label` for the button (defaults to the step's label).
 *
 * The same steps drive three things: tappable checklist rows (stepRows), the
 * one-line "Bước tiếp theo" hint that the host pins in the sheet header
 * (nextHint), and the bottom button (stepCta), which always does the next step
 * or names it, never a mute grey button. On the first task in a career the next
 * control pulses gently (applyGuide). Pure string builders + one DOM pass. */
import {escapeHTML as esc} from '../icons.js';

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
  if(go.cmd&&go.confirm)return ` data-action="v4Cmd" data-op="${esc(go.cmd)}" data-payload="${esc(JSON.stringify(go.payload||{}))}" data-confirm="${esc(go.confirm)}"`;
  if(go.cmd)return ` data-command="${esc(go.cmd)}" data-payload="${esc(JSON.stringify(go.payload||{}))}"`;
  if(go.act)return ` data-action="${esc(go.act)}"${attrsOf(go.data)}`;
  if(go.sel)return ` data-action="v4Go" data-sel="${esc(go.sel)}"`;
  return '';
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
  if(!step?.go)return '';
  if(step.go.sel)return step.go.sel;
  return cta?'.gd-cta':'.gd-next .gd-hint';
}

/** One line: "Bước tiếp theo · <label> →", tapping it does the step (or jumps to it).
 * When nothing is left it offers `final` ({label (text), go}) or just says `done`. The host
 * moves it into the sticky sheet header, so it is always in view. */
export function nextHint(x,steps,{done='',final=null,cta=true,pulse=''}={}){
  let n=pending(steps);
  if(!n&&final?.go)n={label:final.label,go:final.go};
  if(!n&&!done)return '';
  const first=firstTime(x)?' data-first="1"':'';
  if(!n)return `<div class="gd-next done" role="status"${first}${pulse?` data-pulse="${esc(pulse)}"`:''}><small>Bước tiếp theo</small><b>${esc(done)}</b></div>`;
  const sel=pulse||pulseSel(n,cta);
  const tap=goAttrs(n.go);
  return `<div class="gd-next" role="status"${first}${sel?` data-pulse="${esc(sel)}"`:''}><small>Bước tiếp theo</small><button type="button" class="gd-hint"${tap}><b>${n.go?.label||esc(n.label)}</b>${n.note?`<span class="gd-note">${esc(n.note)}</span>`:''}<i aria-hidden="true">→</i></button></div>`;
}

/** The bottom button. `final` = {label, go, ready, style?}: the finishing action (label is HTML).
 * - nothing left, or the next step has no way to do it: the finishing button;
 * - otherwise a big button that does (or points to) the next step; when the finish is
 *   already allowed it stays reachable as a small "or finish now" link under it. */
export function stepCta(x,steps,final,{style='primary big grow'}={}){
  const n=pending(steps);
  const fin=(cls,dis=false)=>`<button type="button" class="btn ${cls}"${goAttrs(final.go)}${dis?' disabled':''}>${final.label}</button>`;
  if(!n||!n.go){
    if(final.ready!==false)return fin(`${style} gd-cta gd-final`);
    const why=n?n.label:(final.why||'');
    return `<div class="gd-ctas">${fin(style,true)}${why?`<small class="gd-why">Còn bước: ${esc(why)}</small>`:''}</div>`;
  }
  const label=n.go.label||`👉 ${esc(n.label)}`;
  const step=`<button type="button" class="btn ${style} gd-cta"${goAttrs(n.go)}>${label}</button>`;
  if(final.ready===false)return step;
  return `<div class="gd-ctas">${step}<button type="button" class="gd-alt"${goAttrs(final.go)}>hoặc ${final.alt||final.label}</button></div>`;
}

/* ---------------------------------------------------------------- host side */

/** Scroll to a control and make it glow for a moment. */
export function highlight(el){
  if(!el)return false;
  const box=el.closest('details:not([open])');if(box)box.open=true;
  el.scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
  el.classList.remove('gd-flash');void el.offsetWidth;el.classList.add('gd-flash');
  clearTimeout(el._gd);el._gd=setTimeout(()=>el.classList.remove('gd-flash'),2400);
  return true;
}

/** Called after every sheet render: pin the hint in the header and pulse the next control
 * on a first task. Never blocks: the pulse is decoration only. */
export function applyGuide(dialog){
  if(!dialog)return;
  const hint=dialog.querySelector('.sheet-body .gd-next');
  const head=dialog.querySelector('.sheet-head .grow');
  if(hint&&head){head.querySelector(':scope>p')?.remove();head.append(hint);}
  const cur=hint||dialog.querySelector('.gd-next');
  if(cur?.dataset.first&&cur.dataset.pulse){
    // The sheet may not be shown yet on its first render: pick by markup, not by layout.
    const el=[...dialog.querySelectorAll(cur.dataset.pulse)].find(e=>!e.disabled&&!e.closest('[hidden],details:not([open])>:not(summary)'));
    el?.classList.add('gd-pulse');
  }
}

/** data-action="v4Go": scroll to the named control. Returns true when handled. */
export function guideAction(action,data,el){
  if(action!=='v4Go')return false;
  const root=el.closest('dialog')||document;
  const target=[...root.querySelectorAll(data.sel||'')].find(e=>e.offsetParent!==null)||root.querySelector(data.sel||'');
  if(!highlight(target)&&el.closest('.gd-next'))highlight(root.querySelector('.gd-cta'));
  return true;
}

// Rows are <li role="button">: Enter and Space work like a click.
document.addEventListener('keydown',e=>{
  if((e.key==='Enter'||e.key===' ')&&e.target?.matches?.('li.gd-todo[role="button"]')){e.preventDefault();e.target.click();}
});
