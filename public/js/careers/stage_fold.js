/** Compact work screens (UX 2026-09): only the part of the job the next step is in stays open.
 * A finished part folds to one "✓" line, a later part to one "○" line; a tap opens it in place. The open
 * state lives in x.ui per task (not in <details>), so a re-render never shuts what the player opened and a
 * part that becomes current always opens. Nothing is dropped, only folded.
 *
 * Guide steps name their part with `stage:'<key>'`; the part of the pending step is "now". A checklist row
 * that points (sel) into a folded part opens that part first, then glows the control.
 * Careers: pet_care, pet_shop, clothing, florist, mother_baby, salon. Each career styles `.sf-line` in its own CSS. */
import {pending,highlight} from '../v4/guide.js';

/** Parts the player opened on this task. */
export function opened(x,tid){
  const u=x.ui;
  if(u.sfTid!==tid){u.sfTid=tid;u.sfOpen={};}
  return u.sfOpen;
}
/** Parts to show open: the one the next step is in (and, while the next step belongs to no part or to
 * one of `lead` — e.g. calming a pet on the table — also the part after it). Nothing left: none. */
export function nowParts(steps,lead=[]){
  const open=(steps||[]).filter(s=>s&&s.ok!==true),n=pending(steps),set=new Set();
  if(n?.stage)set.add(n.stage);
  if(n&&(!n.stage||lead.includes(n.stage))){const w=open.find(s=>s!==n&&s.stage&&!lead.includes(s.stage));if(w)set.add(w.stage);}
  return set;
}
/** Rewrites the rows that point into a folded part so a tap opens it first. Returns the set of open parts. */
export function reach(x,tid,gd,lead=[]){
  opened(x,tid);
  const now=nowParts(gd.steps,lead);
  gd.steps=(gd.steps||[]).map(s=>s&&s.go?.sel&&s.stage&&!now.has(s.stage)?{...s,go:{act:'car:sfOpen',data:{key:s.stage,sel:s.go.sel},label:s.go.label}}:s);
  gd.now=now;
  return now;
}
/** One folded part as a line: "✓ 🪮 Chải & gỡ rối · đã chải ▸". `title` and `sum` are HTML (escape first). */
export function foldLine(x,key,title,{done=false,sum='',cls=''}={}){
  return `<button type="button" class="sf-line ${done?'done':''} ${cls}" data-action="car:sfOpen" data-key="${x.esc(key)}" aria-expanded="false"><span class="sf-mark" aria-hidden="true">${done?'✓':'○'}</span><span class="sf-t"><b>${title}</b>${sum?`<small>${sum}</small>`:''}</span><i aria-hidden="true">▸</i></button>`;
}
/** The part itself when it is now or opened, else its line. `body` is the full markup of the open part. */
export function part(x,tid,now,key,title,body,opts={}){
  return now.has(key)||opened(x,tid)[key]?body:foldLine(x,key,title,opts);
}
/** Client action for the lines and the rewritten rows: open, re-render, then glow the control. */
export const foldActions={
  async sfOpen(data,el,x){
    const tid=x.ui.sfTid;if(tid==null)return;
    opened(x,tid)[data.key]=true;x.render();
    if(data.sel)setTimeout(()=>highlight([...document.querySelectorAll(`#sheet[open] ${data.sel}`)].find(e=>e.offsetParent!==null)),60);
  },
};
/** Locked items collapse to one chip: "🔒 N món mở ở cấp X–Y" (nothing when none are locked). */
export function lockChip(levels,cls=''){
  const ls=(levels||[]).map(Number).filter(Number.isFinite);if(!ls.length)return '';
  const lo=Math.min(...ls),hi=Math.max(...ls);
  return `<p class="sf-lock ${cls}"><span class="tag">🔒 ${ls.length} món mở ở cấp ${lo===hi?lo:`${lo}–${hi}`}</span></p>`;
}
