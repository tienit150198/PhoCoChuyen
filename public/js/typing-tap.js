/** ⌨️ Typing on phones (owner 22/10: "nhiều người than k hiển thị bàn phím của game đó, nên nhập này kia k đc"; iPhone
 * players: a tap on the bank's amount showed no keyboard, Dán did nothing, a typed amount was not taken).
 *
 * The tap. iOS opens the keyboard only for a focus made inside the touch itself: a field focused earlier by script (a
 * sheet's showModal() on its first field, a redraw that put the focus back) has focus but no keyboard. A touch that
 * ends on a typing field without moving focuses it right there; a field that already has focus is
 * focused again (WebKit treats that as "show its keyboard again", Chrome ignores it), never blurred first: whenever
 * html.kb-open was not (yet) set, the 2.5.2.4 blur() + focus() dropped the keyboard for a moment, moved the caret,
 * sent change / focusout (a qty box clamped and re-selected its number) and closed the Dán bubble of a second tap.
 * A finger that slides is scrolling: no focus (2.5.2.4 popped the keyboard for a scroll that began on a field).
 *
 * Whole-number fields (<input type=number> without a decimal step: the bank's amounts, Chuyển khoản, rent, loans…).
 * The game writes money as "1.000.000" (vi-VN). Pasted into a number field that is nothing on iPhone (bad input, the
 * bank said "Nhập số xu…") and 1 on Chrome ("1.000000"); "50.000" typed on Android was 50. A paste keeps its digits only, and a
 * typed "." or "," is left out (these fields never take decimals). The screens' own input listeners see the result.
 * Pure DOM, installed once per document (app.js); tests/typing_tap.mjs. */
import {digits} from './qty-input.js';

export const TYPING='input:not([type=checkbox]):not([type=radio]):not([type=range]):not([type=file]):not([type=button]):not([type=submit]):not([type=reset]):not([type=color]):not([type=image]):not([type=hidden]),textarea,[contenteditable]:not([contenteditable="false"])';
/** Someone is typing: a text field has focus (an auto-opening card waits: it would take the focus and close the phone
 * keyboard mid-word; v4/break-gate.js, v4/journey.js scenes, v4/life.js). */
export function typingNow(doc=globalThis.document){const a=doc?.activeElement;return !!a&&a!==doc.body&&!!a.matches?.(TYPING);}
/** How far (CSS px) a finger may slide and still be a tap (ui-kit.js TAP_SLOP). */
export const SLOP=10;

/** The typing field a touch on `t` lies on. (Not a <label>'s field: the label's own click focuses it, and focusing it
 * in the touch first had the mousedown on the label blur it in between.) */
export const typingTarget=t=>t?.closest?.(TYPING)||null;
/** Whether a touch that ended on field `f` should focus it now. */
export function tapFocus(f,{active=null,kbOpen=false,moved=false}={}){
  if(!f||f.disabled||f.readOnly||moved)return false;
  return active!==f||!kbOpen;   // already typing with its keyboard up: leave it (the caret, Dán) to the browser
}

const wholeStep=s=>s==null||s===''||(s!=='any'&&Number.isInteger(Number(s))&&Number(s)>=1);
/** An <input type=number> that only ever holds a whole number (no step, or a whole step). */
export const wholeNumber=el=>el?.tagName==='INPUT'&&String(el.type).toLowerCase()==='number'&&wholeStep(el.getAttribute?.('step'));
/** What a paste puts in a whole-number field: its digits ("1.000.000 xu" → "1000000"); null: leave the paste alone
 * (digits only already, or no digit at all). */
export function pastedWhole(text){
  const t=String(text??'').trim();
  if(!/\D/.test(t))return null;
  return digits(t)||null;
}
/** Typed text with a separator ("." "," a space) for a whole-number field: what the field holds afterwards (the
 * digits appended to what it has), or null when nothing is to be done. */
export function typedWhole(have,data){
  const d=String(data??'');
  if(!/[.,\s]/.test(d))return null;
  return digits(String(have??'')+d);
}

function put(el,v){
  if(el.value!==v)el.value=v;
  el.dispatchEvent(new Event('input',{bubbles:true}));
}

/** Once per document: the listeners. */
export function installTyping(doc=globalThis.document){
  if(!doc||typeof doc.addEventListener!=='function'||doc._typingOn)return;doc._typingOn=true;
  const o={passive:true,capture:true};let start=null;
  doc.addEventListener('touchstart',e=>{const p=e.touches?.[0];start=p&&e.touches.length===1?{x:p.clientX,y:p.clientY,moved:false}:null;},o);
  doc.addEventListener('touchmove',e=>{const p=e.touches?.[0];if(start&&p&&Math.hypot(p.clientX-start.x,p.clientY-start.y)>SLOP)start.moved=true;},o);
  doc.addEventListener('touchcancel',()=>{start=null;},o);
  doc.addEventListener('touchend',e=>{
    if(e.touches?.length)return;
    const moved=!start||start.moved;start=null;
    const f=typingTarget(e.target),active=doc.activeElement;
    if(!tapFocus(f,{active,kbOpen:!!doc.documentElement?.classList?.contains('kb-open'),moved}))return;
    try{if(active===f)f.focus({preventScroll:true});else f.focus();}catch{/* detached */}
  },o);
  doc.addEventListener('paste',e=>{
    const el=e.target;if(!wholeNumber(el)||el.disabled||el.readOnly)return;
    const v=pastedWhole(e.clipboardData?.getData?.('text/plain')??e.clipboardData?.getData?.('text'));
    if(v==null)return;
    e.preventDefault();put(el,v);
  },true);
  doc.addEventListener('beforeinput',e=>{
    const el=e.target;if(!wholeNumber(el)||e.inputType!=='insertText'||e.isComposing)return;
    const v=typedWhole(el.value,e.data);if(v==null)return;
    e.preventDefault();if(v!==String(el.value??''))put(el,v);
  },true);
}
