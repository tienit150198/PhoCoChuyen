/** Typed number in every "− N +" stepper (owner, 07/10: "mấy cái con số nhập hàng, mua vàng,.. đang phải bấm cộng mệt
 * quá, cho nhập số nhé"). The − / + buttons and the quick chips stay; the number between them is a box you type in.
 * docs/UI_KIT.md "Typed quantity".
 *
 *   qtyBox({value, min, max, label})                 a plain field: the screen reads it, as it read its old <input>
 *   qtyBox({value, min, max, label, go: attrs(QTY)}) the number was text: the box does what a tap does, with the
 *                                                     typed number put where QTY sits (a command, a page action)
 *
 * In the box: digits only (a paste of "1.000" is 1000), the whole number selected on focus so typing replaces it,
 * Enter or leaving the box clamps it to [min, max] (empty or 0 → min, never NaN) and updates the totals the way a tap
 * does. `money` shows 1.000 separators while the box is not being typed in (read it with qtyVal). The server still
 * checks every number. */

/** The stand-in number a stepper's own `attrs(q)` is called with; the typed number replaces it. */
export const QTY=987654321;
const ESC={'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>ESC[c]);
const num=(v,d)=>{const n=Number(v);return v===''||v==null||!Number.isFinite(n)?d:n;};

/** "1.000", "12 phân", "-5" → "1000", "12", "5": only digits, no leading zeros, at most 12 of them. */
export const digits=s=>String(s??'').replace(/\D+/g,'').replace(/^0+(?=\d)/,'').slice(0,12);
/** What the box holds as a whole number in [min, max]: empty, 0 or nonsense → min. With `step` (guests by 5), the
 * nearest number min + k × step. */
export function clampQty(raw,min=0,max=1e12,step=1){
  const lo=Math.ceil(num(min,0)),hi=Math.max(lo,Math.floor(num(max,1e12))),st=Math.max(1,Math.floor(num(step,1))),d=digits(raw);
  let n=d?Number(d):0;
  if(!n)return lo;
  if(st>1)n=lo+Math.round((n-lo)/st)*st;
  if(n>hi)n=lo+Math.floor((hi-lo)/st)*st;
  return Math.max(lo,n);
}
/** The limits a box was drawn with. */
const lim=el=>[el.getAttribute('data-min'),el.getAttribute('data-max'),el.getAttribute('data-step')||1];
const clampEl=(el,raw)=>clampQty(raw,...lim(el));
/** 1000 → "1.000" for money, "1000" otherwise. */
export const fmtQty=(n,money=false)=>money?Math.round(Number(n)||0).toLocaleString('vi-VN'):String(Math.round(Number(n)||0));
/** The number in a box, whatever it shows ("1.000" → 1000); 0 when empty. */
export const qtyVal=el=>Number(digits(el?.value))||0;

/** The box. `go`: what a tap does for the typed number: an attribute string (`data-command="…" data-payload="…"`,
 * `data-action="…" data-set="…"`) or a whole button's HTML, with QTY where the number goes. Without `go`, the box is
 * a field the screen reads. `live`: run `go` on every keystroke too (a page-only number, e.g. the gold to buy, so the
 * price follows the typing). `attrs`: extra attributes (id, data-*, disabled). */
export function qtyBox({value=0,min=0,max=1e12,step=1,label='Số lượng',money=false,go='',live=false,cls='',attrs='',placeholder=''}={}){
  const lo=Math.ceil(num(min,0)),hi=Math.max(lo,Math.floor(num(max,1e12)));
  const v=value===''||value==null?'':Math.round(num(value,lo)),width=Math.max(2,Math.min(9,String(hi).length+(money&&hi>=1000?Math.floor((String(hi).length-1)/3):0)));
  return `<input class="qty-in${cls?' '+cls:''}" type="text" inputmode="numeric" pattern="[0-9]*" autocomplete="off" enterkeyhint="done" `+
    `data-qty data-min="${lo}" data-max="${hi}"${step>1?` data-step="${Math.floor(step)}"`:''} min="${lo}" max="${hi}" value="${v===''?'':esc(fmtQty(v,money))}" data-qty-was="${v}"`+
    `${money?' data-qty-money':''}${go?` data-qty-go="${esc(go)}"`:''}${live?' data-qty-live':''}${placeholder?` placeholder="${esc(placeholder)}"`:''} style="--qch:${width}" aria-label="${esc(label)}"${attrs?' '+attrs:''}>`;
}

/** Run the stepper's own tap for number n: a hidden button built from `go`, clicked where the stepper sits, so the
 * page's usual click routing (commands, page actions, a dialog's own handler) does the work. */
function fire(el,n){
  const go=String(el.getAttribute('data-qty-go')||'').split(String(QTY)).join(String(n));
  if(!go)return;
  const doc=el.ownerDocument,t=doc.createElement('template');
  t.innerHTML=go.trim().startsWith('<')?go:`<button type="button" ${go}></button>`;
  const b=t.content.firstElementChild;if(!b)return;
  b.hidden=true;b.removeAttribute('disabled');b.setAttribute('aria-hidden','true');
  const host=el.parentElement||doc.body;host.appendChild(b);
  try{b.click();}finally{b.remove();}
}

/** Typed value → the box (clamped) and, for a stepper box, its tap. `final`: Enter, leaving, or a change. */
export function commit(el,final=true){
  if(!el?.hasAttribute?.('data-qty'))return null;
  const n=clampEl(el,el.value);
  const money=el.hasAttribute('data-qty-money'),focused=el.ownerDocument?.activeElement===el;
  if(final){const show=money&&!focused?fmtQty(n,true):String(n);if(el.value!==show)el.value=show;}
  if(el.hasAttribute('data-qty-go')){
    const was=num(el.getAttribute('data-qty-was'),NaN),sent=el.getAttribute('data-qty-sent');
    if(n!==was&&String(n)!==sent){el.setAttribute('data-qty-sent',String(n));el._qtyAt=Date.now();fire(el,n);}
  }
  return n;
}

/** For a screen that redraws by innerHTML: leaving the box by tapping a button (the box commits on that press) must
 * not redraw that button away under the finger. Run `fn` (the redraw) now, or once the tap's click is done. The
 * state is set before; only the drawing waits. */
let pressed=false;
export function afterTap(fn){
  if(!pressed||typeof window==='undefined'){fn();return;}
  let done=false;const run=()=>{if(done)return;done=true;window.removeEventListener('click',later);setTimeout(fn,0);};
  const later=()=>run();
  window.addEventListener('click',later,{once:true});setTimeout(run,700);
}
const box=t=>t?.closest?.('input[data-qty]')||null;
/** Once per document: the listeners every box shares. */
export function installQty(doc=globalThis.document){
  if(!doc||typeof doc.addEventListener!=='function'||doc._qtyOn)return;doc._qtyOn=true;   // a test's stand-in document may have no events
  doc.addEventListener('pointerdown',()=>{pressed=true;},true);
  for(const ev of ['pointerup','pointercancel'])doc.addEventListener(ev,()=>{setTimeout(()=>{pressed=false;},0);},true);
  doc.addEventListener('focusin',e=>{const el=box(e.target);if(!el)return;
    if(el.hasAttribute('data-qty-money'))el.value=digits(el.value);
    el._qtySel=true;
    const all=()=>{try{el.setSelectionRange(0,el.value.length);}catch{try{el.select();}catch{/* not selectable */}}};
    all();setTimeout(()=>{if(doc.activeElement===el)all();},0);});
  // A mouse click into the box would put the caret back where it landed: keep the whole number selected.
  doc.addEventListener('mouseup',e=>{const el=box(e.target);if(el?._qtySel){el._qtySel=false;e.preventDefault();}},true);
  // Capture: digits only before any screen's own input listener reads the box.
  doc.addEventListener('input',e=>{const el=box(e.target);if(!el)return;el._qtySel=false;
    const v=digits(el.value);   // over the max is fine while typing: leaving the box clamps it ("1.000" pasted → 1000)
    if(el.value!==v)el.value=v;
    if(el.hasAttribute('data-qty-live')&&el.hasAttribute('data-qty-go')&&v)commit(el,false);},true);
  doc.addEventListener('keydown',e=>{const el=box(e.target);if(!el||e.key!=='Enter'||e.isComposing)return;
    commit(el,true);el.dispatchEvent(new Event('input',{bubbles:true}));
    if(el.form)return;   // in a form, Enter still sends it as before (now with the clamped number)
    e.preventDefault();el.blur();},true);
  // A change (leaving the box after typing): clamp first, so the screen's own change/input listeners see the clamped
  // number; a field box tells them again with an input event when the clamp changed what was typed.
  doc.addEventListener('change',e=>{const el=box(e.target);if(!el)return;const before=el.value;commit(el,true);
    if(el.value!==before&&!el.hasAttribute('data-qty-go'))el.dispatchEvent(new Event('input',{bubbles:true}));},true);
  doc.addEventListener('focusout',e=>{const el=box(e.target);if(!el)return;el._qtySel=false;
    const before=el.value;commit(el,true);
    if(el.hasAttribute('data-qty-money'))el.value=fmtQty(clampEl(el,el.value),true);
    if(el.value!==before&&!el.hasAttribute('data-qty-go'))el.dispatchEvent(new Event('input',{bubbles:true}));});
  // A − / + tapped right after a typed number went out, before the screen redrew: the button still carries the old
  // number + 1. Step from the typed number instead.
  doc.addEventListener('click',e=>{
    const b=e.target?.closest?.('button');if(!b||b.hidden)return;
    const el=b.parentElement?.querySelector?.(':scope > input[data-qty][data-qty-sent]');
    if(!el||el===b||Date.now()-(el._qtyAt||0)>2500)return;
    const sent=Number(el.getAttribute('data-qty-sent')),was=num(el.getAttribute('data-qty-was'),NaN);if(sent===was)return;
    const t=(b.textContent||'').trim(),step=t==='−'||t==='-'?-1:t==='+'||t==='＋'?1:0;if(!step)return;
    e.preventDefault();e.stopImmediatePropagation();
    el.value=String(clampEl(el,sent+step));commit(el,true);},true);
  // A box someone typed in no longer follows its value attribute, and some screens patch the page in place instead of
  // redrawing it. When a redraw brings a new number (or drops the typed number's mark: the server said no), the box
  // shows the page's number again, unless the player is typing in it.
  if(typeof MutationObserver==='function'&&doc.documentElement){
    new MutationObserver(list=>{for(const m of list){const el=m.target;
      if(el.nodeName!=='INPUT'||!el.hasAttribute('data-qty')||doc.activeElement===el)continue;
      if(m.attributeName==='data-qty-sent'&&el.hasAttribute('data-qty-sent'))continue;   // just sent: keep showing it
      const v=el.getAttribute('value')??'';if(el.value!==v)el.value=v;}})
      .observe(doc.documentElement,{subtree:true,attributes:true,attributeFilter:['value','data-qty-sent']});
  }
}
if(typeof document!=='undefined')installQty(document);
