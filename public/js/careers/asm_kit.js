/** Assembly kit (0.9.5): the careers where one order has many parts (the florist's stems,
 * the repair shop's intake slip…). Player feedback #11 / #29: "pick hoa lâu quá", "làm sao
 * biết khách gửi phụ kiện nào". Three shared pieces, styled in calm.css ("Assembly"):
 *  - reqPin: what the customer asked for, one chip per requirement with a live ✓ / ✗,
 *    pinned under the sheet header while the player scrolls the parts;
 *  - nextLine: one plain "Bước tiếp: …" line (the bottom button does it);
 *  - stepper: − n + on a part the order already holds (several at once, not one tap each).
 * Pure string builders plus pinTop(root), which keeps the pin under the sticky header. */

const MARK={true:'✓',false:'✗',null:''};

/** chips: [{ok:true|false|null, icon, text, title?, act?, info?}]. `act` (data-* attributes) makes a chip a button. */
export function reqPin(x,{title='Khách cần',sub='',chips=[],tabs=''}){
  // `info` chips (a budget, a deadline) are facts to keep in mind, not something to tick: not counted.
  const need=chips.filter(c=>!c.info),done=need.filter(c=>c.ok===true).length,bad=need.filter(c=>c.ok===false).length;
  const chip=c=>{
    const cls=`asm-chip${c.ok===true?' ok':c.ok===false?' bad':''}`,inner=`<i aria-hidden="true">${MARK[c.ok===true?'true':c.ok===false?'false':'null']||x.esc(c.icon||'•')}</i><span>${x.esc(c.text)}</span>`;
    const said=c.ok===true?'đã đúng':c.ok===false?'chưa đúng':'chưa có';
    return c.act?`<li><button type="button" class="${cls}" ${c.act} aria-label="${x.esc(c.title||c.text)}: ${said}">${inner}</button></li>`
      :`<li class="${cls}" title="${x.esc(c.title||c.text)}" aria-label="${x.esc(c.title||c.text)}: ${said}">${inner}</li>`;
  };
  return `<section class="asm-pin" aria-label="${x.esc(title)}"><p class="asm-pin-head"><b>🧾 ${x.esc(title)}</b>${sub?`<span class="asm-pin-sub">${sub}</span>`:''}${need.length?`<small class="asm-pin-n${bad?' bad':done===need.length?' ok':''}">${done}/${need.length} ✓</small>`:''}</p>
    <ul class="asm-chips">${chips.map(chip).join('')}</ul>${tabs}</section>`;
}

/** "Bước tiếp: …" from a guide step ({label, note}); '' when nothing is left. */
export function nextLine(x,step,done='Xong hết, giao cho khách thôi!'){
  const text=step?`${step.label}${step.note?` · ${step.note}`:''}`:done;
  return `<p class="asm-next" aria-live="polite"><b>Bước tiếp:</b> <span>${x.esc(text)}</span></p>`;
}

/** − n + for a part. minus/plus are ready attribute strings (data-command… or data-action…), '' = disabled. */
export function stepper(x,{n,minus,plus,label}){
  const b=(attrs,sign,word)=>`<button type="button" class="asm-step" ${attrs||'disabled'} aria-label="${word} ${x.esc(label)}">${sign}</button>`;
  return `<div class="asm-stepper" role="group" aria-label="${x.esc(label)}">${b(minus,'−','Bớt 1')}<b aria-live="polite">${x.esc(String(n))}</b>${b(plus,'+','Thêm 1')}</div>`;
}

/** Keep the pin right under the sheet's sticky header (its height changes with the hint line). */
export function pinTop(root){
  const head=root.closest('dialog')?.querySelector('.sheet-head');
  const h=head&&getComputedStyle(head).position==='sticky'?head.offsetHeight:0;
  if(root.dataset.asmTop!==String(h)){root.dataset.asmTop=String(h);root.style.setProperty('--asm-top',h+'px');}
  // Its own height, for a sticky side column that must sit below it (wide sheets).
  const p=root.querySelector('.asm-pin')?.offsetHeight||0;
  if(root.dataset.asmPin!==String(p)){root.dataset.asmPin=String(p);root.style.setProperty('--asm-pin',p+'px');}
}
