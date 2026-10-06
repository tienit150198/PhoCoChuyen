/** Shared building blocks for readable career screens: a requirement list
 * (what is asked, and whether it is done yet), a folded aside for flavour
 * text, and a look-up table for menus and price lists. Pure string builders;
 * pass the career context's `esc`. Styles live in app.css ("UI kit").
 *
 * UI foundation ("gọn hơn, clean hơn, ít chữ hơn", docs/UI_KIT.md):
 *  - actBar: the one bottom bar of a work screen (next step on the left, the one main button on the right);
 *  - whyAttrs / whyTap: a dimmed but tappable button that says why it cannot go yet, with a fix button;
 *  - headChip: a pinned card's one-line digest as a chip in the sheet header (phones); a tap opens the card;
 *  - helpBtn: a "?" that opens a small sheet with the rules, formulas and intros folded away;
 *  - wordBudget: counts the words a screen shows (dev warning; scripts/check_word_caps.py asserts it). */

const MARK={true:['ok','✓','đúng'],false:['bad','✗','sai'],null:['','○','chưa làm']};
const ESC={'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'};
const e=s=>String(s??'').replace(/[&<>"']/g,c=>ESC[c]);

/** rows: [{ok:true|false|null, icon, label, value, note, tone:'danger'|'warn'}] */
export function reqList(rows,esc,label='Yêu cầu'){
  return `<ul class="req-list" aria-label="${esc(label)}">${rows.map(r=>{
    const [cls,mark,said]=MARK[r.ok===true?'true':r.ok===false?'false':'null'];
    return `<li class="req-row ${cls}${r.tone?' tone-'+esc(r.tone):''}"><span class="req-mark" aria-label="${said}">${mark}</span>${r.icon?`<span class="req-icon" aria-hidden="true">${esc(r.icon)}</span>`:''}<span class="req-label">${esc(r.label)}${r.note?`<small>${esc(r.note)}</small>`:''}</span>${r.value?`<b class="req-value">${esc(r.value)}</b>`:''}</li>`;
  }).join('')}</ul>`;
}

/** One-line summary that opens to the full text (summary/body are HTML). */
export function fold(summary,body,open=false){
  return `<details class="fold"${open?' open':''}><summary>${summary}</summary><div class="fold-body">${body}</div></details>`;
}

/** groups: [{title, rows:[{icon, name, price, stock, tags:[{label,tone}], locked}]}] */
export function refTable(groups,esc){
  return groups.map(g=>`<section class="ref-group"><h3>${esc(g.title)}</h3><ul class="ref-list">${g.rows.map(r=>`<li class="ref-row${r.locked?' locked':''}">
    <span class="ref-icon" aria-hidden="true">${esc(r.icon||'')}</span>
    <span class="ref-name"><b>${esc(r.name)}</b>${(r.tags||[]).length||r.stock!=null?`<span class="ref-tags">${(r.tags||[]).map(t=>`<span class="ref-tag${t.tone?' '+esc(t.tone):''}">${esc(t.label)}</span>`).join('')}${r.stock!=null?`<small class="ref-stock">${esc(String(r.stock))}</small>`:''}</span>`:''}</span>
    <b class="ref-price">${esc(String(r.price??''))}</b></li>`).join('')}</ul></section>`).join('');
}

/* ================================================================ UI foundation */

/** The switch: html[data-clean] (v4/shell.js applyClean). Phones by default; Cài đặt → Giao diện can turn it
 * off (or on everywhere), and the server can turn it off for everyone (MNL_CLEAN_UI=off). */
export const clean=()=>typeof document!=='undefined'&&document.documentElement.hasAttribute('data-clean');

/** The one bottom bar of a work screen.
 *   next: HTML for the left slot (a chip: the next step, a pointer "👆 …", a count, or '' for none);
 *   main: HTML of the main button(s) (exactly one .btn.primary per screen, and it lives here);
 *   top:  an optional full-width row above (route totals, the last result);
 *   cls:  the career's own bar class (kept as a hook: .sk-bar, .fk-bar …); attrs: extra attributes.
 * Layout lives in app.css (.ui-bar): one row, the next slot shrinks and ellipsises, the main button keeps
 * 40–60% of the width. A bar with nothing in it is ''. */
export function actBar({next='',main='',top='',cls='',attrs=''}={}){
  if(!next&&!main&&!top)return '';
  return `<div class="ui-bar${cls?' '+cls:''}"${attrs}>${top?`<div class="ui-bar-top">${top}</div>`:''}${next?`<div class="ui-bar-next">${next}</div>`:''}${main?`<div class="ui-bar-main">${main}</div>`:''}</div>`;
}

/** A guide-style `go` ({cmd,payload}|{act,data}|{sel}) as data-* attributes (same shapes as v4/guide.js goAttrs). */
export function fixAttrs(go){
  if(!go)return '';
  if(go.cmd)return ` data-command="${e(go.cmd)}" data-payload="${e(JSON.stringify(go.payload||{}))}"`;
  if(go.act)return ` data-action="${e(go.act)}"${Object.entries(go.data||{}).map(([k,v])=>` data-${e(k)}="${e(v)}"`).join('')}`;
  if(go.sel)return ` data-action="v4Go" data-sel="${e(go.sel)}"`;
  return '';
}

/** Attributes for a control that cannot go yet: dimmed (.is-why) but still tappable, aria-disabled, the reason
 * (≤ 8 words, names the thing) and an optional fix ({cmd|act|sel, label}). `can` is what the server sent for
 * this action: true (go) or {why, fix}; anything else means nothing to say. Returns '' when the control can go. */
export function whyAttrs(can){
  if(!can||can===true||!can.why)return '';
  return ` aria-disabled="true" data-why="${e(can.why)}"${can.fix?` data-fix="${e(JSON.stringify(can.fix))}"`:''}`;
}
/** Add whyAttrs to a ready-made button's markup (the first <button …>), plus the .is-why class. */
export function withWhy(html,can){
  const a=whyAttrs(can);if(!a)return html;
  return String(html).replace(/<button\b([^>]*?)\sclass="([^"]*)"/,(m,pre,cls)=>`<button${pre} class="${cls} is-why"`).replace(/<button\b/,`<button${a}`).replace(/\sdisabled(?=[\s>])/,'');
}

/** A tap on a dimmed button: the reason (and its fix) in the bar's next slot for a few seconds, never a toast. */
export function whyTap(el){
  const why=el.dataset.why||'';if(!why)return false;
  let fix=null;try{fix=el.dataset.fix?JSON.parse(el.dataset.fix):null;}catch{fix=null;}
  const line=`<span class="ui-why" role="status"><span aria-hidden="true">⚠</span> <span class="ui-why-tx">${e(why)}</span></span>${fix?`<button type="button" class="btn small ui-why-fix"${fixAttrs(fix)}>${e(fix.label||'Sửa')}</button>`:''}`;
  const bar=el.closest('.ui-bar')||el.closest('dialog,#app')?.querySelector('.ui-bar');
  let slot=bar?.querySelector(':scope>.ui-bar-next');
  if(bar&&!slot){slot=document.createElement('div');slot.className='ui-bar-next';const main=bar.querySelector(':scope>.ui-bar-main');if(main)main.before(slot);else bar.append(slot);}
  if(!slot){   // no bar on this screen: one line right under the control
    slot=el.nextElementSibling?.classList.contains('ui-why-line')?el.nextElementSibling:null;
    if(!slot){slot=document.createElement('div');slot.className='ui-why-line';el.after(slot);}
  }
  slot.querySelector('.ui-bar-note')?.remove();slot.classList.remove('has-note');   // the reason supersedes a passing note
  if(!slot._ui)slot._ui=slot.innerHTML;
  slot.innerHTML=line;slot.classList.add('is-why');
  clearTimeout(slot._t);
  slot._t=setTimeout(()=>{if(!slot.isConnected)return;if(slot.classList.contains('ui-why-line'))slot.remove();else{slot.innerHTML=slot._ui;slot._ui=null;slot.classList.remove('is-why');}},5000);
  el.classList.remove('ui-shake');requestAnimationFrame(()=>el.classList.add('ui-shake'));
  return true;
}

/** A pinned card's digest as a header chip on phones: `icon` + a short `text` (≤ 3 words, numbers welcome).
 * `target`: a selector for the card. While data-clean is on, guide.js moves the chip into the sheet header and the
 * card stops pinning; a tap opens the card as a popover under the header (a second tap, or ✕, closes it). */
export function headChip(icon,text,target,{label='',tone='',flow=false}={}){
  return `<button type="button" class="ui-chip${tone?' '+e(tone):''}" data-ui-head${flow?'="flow"':''} data-ui-pop="${e(target)}" aria-expanded="false" aria-label="${e(label||text)}"><span aria-hidden="true">${e(icon)}</span><b>${e(text)}</b><i aria-hidden="true">›</i></button>`;
}

/* The "?" sheet: rules, formulas and intros live here, never on the work screen. Content is kept by key at render
 * time (pure strings); the dialog is built once on first use. */
const HELP=new Map();
/** sections: [{title, body (HTML), open?}] or an HTML string. Returns the "?" button.
 * tips: also list, at the top, the explanations this screen folded away (every `.ui-tip` in the same sheet). */
export function helpBtn(key,title,sections,{label='?',cls='',tips=false}={}){
  HELP.set(String(key),{title,sections});
  return `<button type="button" class="icon-btn ui-q${cls?' '+e(cls):''}" data-ui-help="${e(key)}"${tips?' data-ui-tips':''} aria-label="${e('Giải thích: '+title)}">${e(label)}</button>`;
}
/** An explanation (a rule, a tile's description, a long hint): shown inline on the classic layout; on the clean
 * layout it is hidden from the work screen and listed in the "?" sheet (helpBtn {tips:true}). `title` names what
 * it explains ("Pít-tông cao su"). Pass HTML-safe text. */
export function tip(text,title='',tag='small'){
  if(!text)return '';
  return `<${tag} class="ui-tip"${title?` data-tip="${e(title)}"`:''}>${text}</${tag}>`;
}
function tipsOf(root){
  const seen=new Set(),rows=[];
  for(const t of root?.querySelectorAll('.ui-tip')||[]){
    const text=t.textContent.replace(/\s+/g,' ').trim(),name=t.dataset.tip||'';
    const k=name+'|'+text;if(!text||seen.has(k))continue;seen.add(k);
    rows.push(`<li>${name?`<b>${e(name)}</b>: `:''}${e(text)}</li>`);
  }
  return rows.length?{title:'Trên màn này',body:`<ul>${rows.join('')}</ul>`,open:true}:null;
}
/** The same content as a full section list (for a page that has room for it, e.g. the guide hub). */
export function helpBody(sections){
  const list=typeof sections==='string'?[{title:'',body:sections,open:true}]:sections||[];
  return list.map((s,i)=>s.title?`<details class="ui-help-sec"${s.open||i===0?' open':''}><summary>${e(s.title)}</summary><div>${s.body}</div></details>`:`<div class="ui-help-sec">${s.body}</div>`).join('');
}
function openHelp(key,btn){
  const h=HELP.get(String(key));if(!h)return false;
  const extra=btn?.hasAttribute('data-ui-tips')?tipsOf(btn.closest('dialog')):null;
  const sections=extra?[extra,...(typeof h.sections==='string'?[{title:'',body:h.sections}]:h.sections||[]).map(x=>({...x,open:false}))]:h.sections;
  let d=document.getElementById('uiHelp');
  if(!d){d=document.createElement('dialog');d.id='uiHelp';d.className='ui-help';document.body.append(d);
    d.addEventListener('click',ev=>{if(ev.target===d||ev.target.closest('[data-ui-help-x]'))d.close();});}
  d.innerHTML=`<header class="ui-help-head"><h2>${e(h.title)}</h2><button type="button" class="icon-btn" data-ui-help-x aria-label="Đóng">✕</button></header><div class="ui-help-body">${helpBody(sections)}</div>`;
  if(!d.open)d.showModal();
  return true;
}

/** Header chips: on a phone with data-clean, move a work screen's chips into its sheet header (after the title).
 * Called after every sheet render (v4/guide.js applyGuide). */
export function placeChips(dialog){
  if(!dialog)return;
  const head=dialog.querySelector('#sheetContent .sheet-head');if(!head)return;
  // flow chips (the digest of a card that never pinned: a checklist, a booking list) join the screen's in-flow chip
  // row (.ui-chiprow, the street kit's day line) so the header stays one row; without one they go to the header.
  const row2=dialog.querySelector('.sheet-body .ui-chiprow');
  if(row2){const flow=[...dialog.querySelectorAll('.sheet-body [data-ui-head="flow"]')].filter(c=>!row2.contains(c)&&!c.closest('details:not([open])'));
    if(flow.length)row2.prepend(...flow);}
  const old=[...head.querySelectorAll(':scope>.ui-chips')];
  const chips=[...dialog.querySelectorAll('.sheet-body [data-ui-head]')].filter(c=>!c.closest('details:not([open])')&&!c.closest('.ui-chiprow'));
  // No chip left in the body: either the screen has none (drop the row), or this is a second pass over the same
  // markup (a re-render with nothing changed skips the DOM) and the chips already sit in the header: keep those whose
  // card is still on the page (wave 4: the milk tea ticket chip vanished on the counter's repeated passes).
  if(!chips.length){
    const live=o=>[...o.querySelectorAll('[data-ui-pop]')].some(c=>{try{return !!dialog.querySelector(c.dataset.uiPop);}catch{return false;}});
    old.forEach(o=>{if(!live(o))o.remove();});
    if(!head.querySelector(':scope>.ui-chips'))dialog.removeAttribute('data-ui-chips');
    return;
  }
  let row=old[0];
  if(!row){row=document.createElement('div');row.className='ui-chips';head.querySelector(':scope>.grow')?.after(row)||head.append(row);}
  for(const o of old.slice(1))o.remove();
  row.replaceChildren(...chips);
  dialog.setAttribute('data-ui-chips','');
}
function closePops(root=document){
  for(const c of root.querySelectorAll('.ui-pop'))c.classList.remove('ui-pop');
  for(const c of root.querySelectorAll('[data-ui-pop][aria-expanded="true"]'))c.setAttribute('aria-expanded','false');
}
function togglePop(chip){
  const dialog=chip.closest('dialog')||document;
  let card=null;try{card=dialog.querySelector(chip.dataset.uiPop);}catch{card=null;}
  if(!card)return;
  const open=!card.classList.contains('ui-pop');
  closePops(dialog);
  if(open){card.classList.add('ui-pop');chip.setAttribute('aria-expanded','true');}
}

/** A label in at most `max` words for the clean layout (numbers are free): cut at the first clause, then at `max`
 * words, never ending on a little word ("lúc", "cùng"…). On the classic layout the whole label. */
const LITTLE=new Set(['lúc','từ','ra','vào','trong','cùng','và','với','cho','của','ở','để','mọi','các','những','một','bằng','theo','khi','thì','là','đi','lên','xuống','hay','hoặc']);
export function few(s,max=3,force=false){
  const full=String(s||'').trim();if(!force&&!clean())return full;
  const head=full.split(/[,;(:—–]|\s-\s/)[0].trim(),out=[];let n=0;
  for(const w of head.split(/\s+/)){const word=/\p{L}/u.test(w);if(word&&n>=max)break;out.push(w);if(word)n++;}
  while(out.length>1&&(LITTLE.has(out[out.length-1].toLowerCase())||!/[\p{L}\p{N}]/u.test(out[out.length-1])))out.pop();
  return out.join(' ')||full;
}
/* ---------------------------------------------------------------- word budget (dev) */
export const WORD_CAPS={work:25,intro:30,toast:8,life:30};
const visibleWords=root=>{
  const vw=innerWidth,vh=innerHeight;let n=0;
  const tw=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  for(let t;(t=tw.nextNode());){
    const s=t.textContent.trim();if(!s)continue;
    const p=t.parentElement;if(!p||p.closest('.sr-only,[hidden],details:not([open])>:not(summary),script,style,.gd-dup,.ui-bar-note'))continue;
    const rg=document.createRange();rg.selectNodeContents(t);
    const r=[...rg.getClientRects()].find(r=>r.width>=1&&r.height>=1&&r.bottom>0&&r.top<vh&&r.right>0&&r.left<vw);if(!r)continue;
    if(p.checkVisibility&&!p.checkVisibility({opacityProperty:true,visibilityProperty:true}))continue;
    for(const k of s.split(/\s+/))if(/\p{L}/u.test(k))n++;
  }
  return n;
};
/** {words, kind, cap, over}: the words on screen in this dialog (and its toasts). kind: 'intro' when the
 * street-kit intro card is up, else 'work' for a work sheet. Dev builds warn in the console when over. */
export function wordBudget(dialog){
  if(!dialog?.open||typeof document==='undefined')return null;
  const kind=dialog.querySelector('.sk-intro,.td-intro')?'intro':dialog.querySelector('.career-job')?'work':'life';
  const words=visibleWords(dialog);
  // A note is transient: it is not part of the screen's words, it has its own cap (8).
  const toasts=[...document.querySelectorAll('#toasts>.toast'),...dialog.querySelectorAll('.ui-bar-note:not(.open)')].filter(t=>t.getClientRects().length).map(t=>(t.innerText.match(/\S+/g)||[]).filter(k=>/\p{L}/u.test(k)).length);
  const out={words,kind,cap:WORD_CAPS[kind],toast:Math.max(0,...toasts),over:words>WORD_CAPS[kind]||toasts.some(n=>n>WORD_CAPS.toast)};
  dialog.dataset.words=String(words);
  return out;
}
let devWarn=null;
const isDev=()=>{try{return devWarn??=(localStorage.getItem('mnl.wordcap')==='1'||/^(localhost|127\.0\.0\.1)$/.test(location.hostname));}catch{return false;}};
/** Called after a work screen renders (v4/action-bar.js syncBar): warns once per screen and count. */
export function warnBudget(dialog){
  if(!isDev())return;
  clearTimeout(warnBudget.t);
  warnBudget.t=setTimeout(()=>{const b=wordBudget(dialog);if(!b?.over)return;
    const key=`${b.kind}:${b.words}:${b.toast}`;if(dialog._wb===key)return;dialog._wb=key;
    console.warn(`text budget: ${b.words} words on a ${b.kind} screen (cap ${b.cap})${b.toast>WORD_CAPS.toast?`, toast ${b.toast} words (cap ${WORD_CAPS.toast})`:''}`);},400);
}

/* ---------------------------------------------------------------- one listener for all of it */
if(typeof document!=='undefined'&&!globalThis.__uiKit){
  globalThis.__uiKit=true;
  // Capture: runs before app.js's click delegate, so a dimmed button never sends its command.
  document.addEventListener('click',ev=>{
    const t=ev.target;if(!t?.closest)return;
    const why=t.closest('[aria-disabled="true"][data-why]');
    if(why){ev.preventDefault();ev.stopImmediatePropagation();whyTap(why);return;}
    const q=t.closest('[data-ui-help]');
    if(q){ev.preventDefault();ev.stopImmediatePropagation();openHelp(q.dataset.uiHelp,q);return;}
    const chip=t.closest('[data-ui-pop]');
    if(chip){ev.preventDefault();ev.stopImmediatePropagation();togglePop(chip);return;}
    // A tap outside an open popover card closes it.
    const pop=document.querySelector('.ui-pop');
    if(pop&&!pop.contains(t))closePops();
  },true);
}
