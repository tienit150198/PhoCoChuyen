/** Assembly kit (0.9.5): the careers where one order has many parts (the florist's stems,
 * the repair shop's intake slip…). Player feedback #11 / #29: "pick hoa lâu quá", "làm sao
 * biết khách gửi phụ kiện nào". Three shared pieces, styled in calm.css ("Assembly"):
 *  - reqPin: what the customer asked for, one chip per requirement with a live ✓ / ✗,
 *    pinned under the sheet header while the player scrolls the parts;
 *  - nextLine: one plain "Bước tiếp: …" line (the bottom button does it);
 *  - stepper: − n + on a part the order already holds (several at once, not one tap each).
 * Pure string builders plus pinTop(root), which keeps the pin under the sticky header (and under the
 * money chip that hangs off it), and asmActions (spread into a career's actions: the pin folds to one line). */

const MARK={true:'✓',false:'✗',null:''};

const stepText=step=>step?`${step.label}${step.note?` · ${step.note}`:''}`:'';

/** chips: [{ok:true|false|null, icon, text, title?, act?, info?}]. `act` (data-* attributes) makes a chip a button.
 * key: the order's id; with it, tapping the header row folds the pin to one line ("Khách cần · 3/6 ✓ ·
 * Bước tiếp …", the pin is tall on a phone). A requirement turning ✗ opens it again. next: the guide step. */
export function reqPin(x,{title='Khách cần',sub='',chips=[],tabs='',key='',next=null}){
  // `info` chips (a budget, a deadline) are facts to keep in mind, not something to tick: not counted.
  const need=chips.filter(c=>!c.info),done=need.filter(c=>c.ok===true).length,bad=need.filter(c=>c.ok===false).length;
  const folds=x.ui.asmFold||{};
  if(bad&&folds[key])delete folds[key];
  const folded=!!(key&&folds[key]);
  const chip=c=>{
    const cls=`asm-chip${c.ok===true?' ok':c.ok===false?' bad':''}`,inner=`<i aria-hidden="true">${MARK[c.ok===true?'true':c.ok===false?'false':'null']||x.esc(c.icon||'•')}</i><span>${x.esc(c.text)}</span>`;
    const said=c.ok===true?'đã đúng':c.ok===false?'chưa đúng':'chưa có';
    return c.act?`<li><button type="button" class="${cls}" ${c.act} aria-label="${x.esc(c.title||c.text)}: ${said}">${inner}</button></li>`
      :`<li class="${cls}" title="${x.esc(c.title||c.text)}" aria-label="${x.esc(c.title||c.text)}: ${said}">${inner}</li>`;
  };
  const n=need.length?`<small class="asm-pin-n${bad?' bad':done===need.length?' ok':''}">${done}/${need.length} ✓</small>`:'';
  const nextTxt=stepText(next);
  const inner=folded
    ?`<b>🧾 ${x.esc(title)}</b>${n}${nextTxt?`<span class="asm-pin-next"><b class="sr-only">Bước tiếp:</b>→ ${x.esc(nextTxt)}</span>`:''}`
    :`<b>🧾 ${x.esc(title)}</b>${sub?`<span class="asm-pin-sub">${sub}</span>`:''}${n}`;
  const head=key
    ?`<button type="button" class="asm-pin-head asm-fold" data-action="car:asmFold" data-key="${x.esc(key)}" aria-expanded="${!folded}" title="${folded?'Mở phiếu khách':'Thu gọn phiếu khách'}">${inner}<i class="asm-fold-ico" aria-hidden="true">${folded?'▾':'▴'}</i></button>`
    :`<p class="asm-pin-head">${inner}</p>`;
  return `<section class="asm-pin${folded?' folded':''}" aria-label="${x.esc(title)}">${head}
    ${folded?'':`<ul class="asm-chips">${chips.map(chip).join('')}</ul>`}${tabs}</section>`;
}

/** Spread into a career's `actions` (data-action="car:asmFold"). */
export const asmActions={
  async asmFold(d,el,x){const f=(x.ui.asmFold??={});if(f[d.key])delete f[d.key];else f[d.key]=true;x.render();},
};

/** The guide's final button as a step ({label}), once it is ready: what "Bước tiếp" says when no step is left. */
export function finalStep(final){
  return final&&final.go&&final.ready!==false&&final.label?{label:String(final.label).replace(/<[^>]*>/g,'').trim()}:null;
}

/** The next step as one plain line above the bottom button ("Vớt mì khi thanh vào vùng xanh"); "Bước tiếp:"
 * is for screen readers only (owner 03/10: "chữ ít thôi"). '' when nothing is left. */
export function nextLine(x,step,done='Xong hết, giao cho khách thôi!'){
  const text=step?stepText(step):done;
  if(!text)return '';
  return `<p class="asm-next" aria-live="polite"><b class="sr-only">Bước tiếp:</b><span>${x.esc(text)}</span></p>`;
}

/** − n + for a part. minus/plus are ready attribute strings (data-command… or data-action…), '' = disabled. */
export function stepper(x,{n,minus,plus,label}){
  const b=(attrs,sign,word)=>`<button type="button" class="asm-step" ${attrs||'disabled'} aria-label="${word} ${x.esc(label)}">${sign}</button>`;
  return `<div class="asm-stepper" role="group" aria-label="${x.esc(label)}">${b(minus,'−','Bớt 1')}<b aria-live="polite">${x.esc(String(n))}</b>${b(plus,'+','Thêm 1')}</div>`;
}

/** Stuck = sitting at its sticky offset (it then covers the gap under the header). */
function stuck(dlg){
  const p=dlg.querySelector('.asm-pin'),hd=dlg.querySelector('.sheet-head');if(!p||!hd)return;
  const top=parseFloat(getComputedStyle(p).top)||0;
  p.classList.toggle('stuck',p.getBoundingClientRect().top<=hd.getBoundingClientRect().top+top+1);
}
const setVar=(el,k,v)=>{if(el.dataset[k]!==v){el.dataset[k]=v;el.style.setProperty('--'+k.replace(/[A-Z]/g,c=>'-'+c.toLowerCase()),v);}};

/** Keep the pin right under the sheet's sticky header (its height changes with the hint line), below
 * the money chip hanging off the header's bottom edge (v4/money.js), with the header's own colour
 * filling that gap once the pin is stuck (scroll listener on the sheet, set once). */
export function pinTop(root){
  const dlg=root.closest('dialog'),head=dlg?.querySelector('.sheet-head');
  const sticky=!!head&&getComputedStyle(head).position==='sticky';
  const chip=sticky?head.querySelector(':scope>.mn-chip'):null;
  const gap=chip?Math.max(0,Math.ceil(chip.getBoundingClientRect().bottom-head.getBoundingClientRect().bottom))+4:0;
  const h=sticky?head.offsetHeight+gap:0;
  setVar(root,'asmTop',h+'px');
  setVar(root,'asmGap',gap+'px');
  if(sticky){const bg=getComputedStyle(head).backgroundColor;
    setVar(root,'asmFill',/^transparent$|rgba\([^)]*,\s*0\)$/.test(bg)?getComputedStyle(dlg).backgroundColor:bg);}
  // Its own height, for a sticky side column that must sit below it (wide sheets).
  const pin=root.querySelector('.asm-pin');
  setVar(root,'asmPin',(pin?.offsetHeight||0)+'px');
  if(!pin||!sticky)return;
  stuck(dlg);
  // Scroll events do not bubble; a capturing listener on the dialog hears whichever part scrolls.
  if(!dlg._asmScroll){dlg._asmScroll=true;dlg.addEventListener('scroll',()=>stuck(dlg),{passive:true,capture:true});}
}
