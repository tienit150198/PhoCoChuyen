/** 🔒 "Giữ lại cho ca của tôi" (B4 part 2, F#243 / F#247): a per-item floor the staff never sell below, so the owner's
 * own shift still has stock. One stepper row per item in the stock room (Kho: workplace_business ops_keep) and in a
 * counter's 📦 tab (quay_business jr_quay_keep). Each tap sends the new number; the server keeps it and says it back. */
import {escapeHTML as esc} from './icons.js';

export const KEEP_MAX=999;
/** 0,1,…,10, then 15,20,…,50, then by tens: few taps for a big floor, exact for a small one. */
export const keepUp=n=>Math.min(KEEP_MAX,n<10?n+1:n<50?n+5:n+10);
export const keepDown=n=>Math.max(0,n<=10?n-1:n<=50?n-5:n-10);

/** The stepper: `attrs(qty)` gives the button's data attributes (a command or a page action) for that new number. */
export function keepStepper(n,attrs,name=''){
  n=Math.max(0,Number(n)||0);
  const b=(q,label,aria,off)=>`<button type="button" class="btn ghost" ${attrs(q)} aria-label="${esc(aria)}"${off?' disabled':''}>${label}</button>`;
  return `<div class="keep-row" data-testid="keep-row"><span>🔒 Giữ cho ca bạn</span><div class="inv-stepper keep-step">${b(keepDown(n),'−',`Giữ ít ${name} hơn`,n<=0)}<output aria-label="Số giữ lại${name?` ${esc(name)}`:''}">${n}</output>${b(keepUp(n),'+',`Giữ thêm ${name}`,n>=KEEP_MAX)}</div></div>`;
}

/** A workplace item (Kho): one the staff orders can take (business.keepable, sent by a server that knows ops_keep),
 * shown once the place has staff, or while a floor is set. */
export function keepRow(c,item,name=''){
  const n=Number(c?.ops?.business_keep?.[item])||0;
  if(!(c?.ops?.business?.keepable||[]).includes(item))return '';
  if(!n&&!(c?.ops?.staff||[]).some(e=>e.status==='hired'))return '';
  return keepStepper(n,q=>`data-command="ops_keep" data-payload="${esc(JSON.stringify({item,qty:q}))}"`,name);
}

/** "🔒 Giữ 5 ly giấy, 3 sữa cho bạn" for the away card: `kept` is [[id, name, n], …] (at most two named). */
export function keptLine(kept){
  if(!Array.isArray(kept)||!kept.length)return '';
  const low=s=>s?s.charAt(0).toLowerCase()+s.slice(1):s;
  const named=kept.slice(0,2).map(([,name,n])=>`${Number(n)||0} ${low(String(name||''))}`);
  return `🔒 Giữ lại ${named.join(', ')}${kept.length>2?`, +${kept.length-2} món`:''} cho bạn`;
}
