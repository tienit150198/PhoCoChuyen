/** 💰 Tiền công +% · 🎉 Tuần lễ tay nghề · 🧰 Bộ đồ nghề / 🤝 Mối khách quen / ⏩ Làm nhanh (game/pay_boost.py).
 *
 * View only: every number comes from the server (state.payweek, career.paykit, a command's result.payboost).
 * - payBar(c,state,t): the work sheet's event banner (🎉 +20 %, today's Chuyên cần) and the ⏩ Làm nhanh button when the
 *   step in hand may be filled by one tap.
 * - payDone(t): the done screen's "Lương cơ bản + Tăng lương + Tuần lễ tay nghề + Đồ nghề + Boa" line for the job just
 *   finished (the last result's payboost, kept here; a reload shows nothing, the money is in the cash book anyway).
 * - paySection(c): the 🧰 Bộ đồ nghề shop at the top of the Thiết bị sheet (⋯ → 🧰 Bộ đồ nghề).
 * An older server sends none of these: nothing shows. */
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const esq=v=>esc(JSON.stringify(v));
let last=null,booted=false;

/** Remember the breakdown of the last finished job (api 'result' events). */
export function payBoot(api){
  if(booted||!api?.addEventListener)return;booted=true;
  api.addEventListener('result',e=>{const p=e.detail?.result?.payboost;if(p&&typeof p==='object')last={...p,at:Date.now()};});
  css();
}

function css(){
  if(typeof document==='undefined'||document.getElementById('paykit-css'))return;
  const st=document.createElement('style');st.id='paykit-css';
  st.textContent=`.pay-bar{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;margin:0 0 10px;padding:8px 12px;border-radius:14px;background:linear-gradient(90deg,#fff3c4,#ffe0ef);color:#5b3a00;font-size:.9rem;line-height:1.35}
.pay-bar b{font-weight:700}.pay-bar .pay-streak{margin-left:auto;font-weight:600}
.pay-fast{margin:0 0 10px}.pay-fast .btn{width:100%}
.pay-done{margin:10px auto 0;max-width:420px;padding:10px 12px;border-radius:14px;background:#f2fbf3;color:#20502a;font-size:.92rem;text-align:left}
.pay-done ul{margin:6px 0 0;padding:0;list-style:none}.pay-done li{display:flex;justify-content:space-between;gap:8px}
.pay-done li.total{border-top:1px dashed #9cc7a4;margin-top:4px;padding-top:4px;font-weight:700}
.pay-shop .pay-now{font-size:.92rem}.pay-shop .tag.gold{background:#fff1c1;color:#6b4a00}
.pay-fast-steps{margin:6px 0 0;padding:0;list-style:none;display:grid;gap:2px;line-height:1.4}
.pay-fast-steps li{display:flex;justify-content:space-between;gap:8px}.pay-fast-steps b{font-weight:600;white-space:nowrap}
html[data-layout="phone"] .upgrade-card>.pay-fast-steps{grid-column:2/-1;margin-top:4px}`;
  document.head.append(st);
}

/** 🎉 the event banner and ⏩ the step ready, over the job in hand. */
export function payBar(c,state,t){
  const w=state?.payweek,k=c?.paykit;let html='';
  if(w&&typeof w==='object'){
    const streak=w.got?`✅ Chuyên cần hôm nay xong${w.streak>1?` · ${w.streak} ngày liên tiếp`:''}`:`Chuyên cần ${fmt(w.jobs)}/${fmt(w.need)} việc · thưởng ${fmt(w.next)} xu`;
    html+=`<div class="pay-bar" role="status" data-coach="payweek"><span>🎉 <b>Tuần lễ tay nghề</b> · +${fmt(w.pct)}% tiền công tới hết ${esc(w.until_text)}</span><span class="pay-streak">${esc(streak)}</span></div>`;
  }
  const r=k?.fast?.ready;
  if(r&&t&&r.task===t.id)html+=`<div class="pay-fast"><button type="button" class="btn cream" data-action="v4Cmd" data-op="payk_fast" data-payload="${esq({task:t.id})}" data-coach="payk-fast">⏩ Làm nhanh: ${esc(r.label)}</button></div>`;
  return html;
}

/** The pay of the job just finished, piece by piece. */
export function payDone(t){
  const p=last;if(!p||!t||p.ref!==t.id||Date.now()-p.at>10*60e3)return '';
  const rows=[['Lương cơ bản',p.base],['💰 Tăng tiền công',p.raise],['🎉 Tuần lễ tay nghề',p.event],['🧰 Đồ nghề',p.tools],['🤝 Khách quen boa',p.tip],['🎉 Chuyên cần',p.streak]].filter(([,v])=>Number(v)>0);
  if(rows.length<2)return '';
  const total=rows.reduce((a,[,v])=>a+Number(v),0);
  return `<section class="pay-done" aria-label="Tiền công việc này"><b>💵 Tiền công việc này</b><ul>${rows.map(([l,v],i)=>`<li><span>${i?'<i>+</i> ':''}${esc(l)}</span><span>${fmt(v)} xu</span></li>`).join('')}<li class="total"><span>Tổng</span><span>${fmt(total)} xu</span></li></ul><button type="button" class="btn ghost small" data-action="decor" data-coach="paykit-tip">🧰 Bộ đồ nghề: kiếm thêm</button></section>`;
}

/** 🧰 Bộ đồ nghề: the shop of the career (the Thiết bị sheet). */
export function paySection(c){
  const k=c?.paykit;if(!k||typeof k!=='object')return '';
  const money=Number(c.money)||0;
  const buy=(item,label,price,question)=>money<price?`<button class="btn ghost full" type="button" disabled>Thiếu ${fmt(price-money)} xu</button>`
    :`<button class="btn primary full" type="button" data-action="v4Cmd" data-op="payk_buy" data-payload="${esq({item})}" data-cost="${price}" data-pocket="fund" data-confirm="${esc(question)}">${esc(label)} · ${fmt(price)} xu</button>`;
  const now=`<p class="pay-now">💵 Tiền công nghề này đang <b>+${fmt(k.total)}%</b>: tăng lương +${fmt(k.raise_pct)}%${k.event_pct?` · 🎉 Tuần lễ tay nghề +${fmt(k.event_pct)}%`:''}${k.tool_pct?` · 🧰 đồ nghề +${fmt(k.tool_pct)}%`:''}.${k.off?' Đang tạm nghỉ.':''}</p>`;
  const next=(k.tools||[]).find(x=>x.n===k.tier+1),have=(k.tools||[]).find(x=>x.n===k.tier);
  const tool=`<article class="upgrade-card" data-paykit="tool"><div class="row spread"><span class="upgrade-icon" aria-hidden="true">🧰</span><span class="tag gold">${have?`Bậc ${fmt(have.n)} · +${fmt(have.pct)}%`:'Chưa có'}</span></div><h3>🧰 ${esc(next?next.name:have?.name||'Bộ đồ nghề')}</h3><p>${next?`Đồ nghề tốt hơn: mọi việc của nghề này +${fmt(next.pct)}% tiền công (thay bậc trước).`:'Đã đủ bộ đồ nghề tốt nhất. Tay nghề lên tầm nghệ nhân!'}</p>${next?buy('tool',`Lên bậc ${next.n}`,next.price,`Mua 🧰 ${next.name}? Trả bằng quỹ nghề.`):`<button class="btn ghost full" type="button" disabled>✓ Bậc cao nhất</button>`}</article>`;
  const book=`<article class="upgrade-card" data-paykit="book"><div class="row spread"><span class="upgrade-icon" aria-hidden="true">🤝</span><span class="tag">${k.book?'Đã có':'Khách quen'}</span></div><h3>🤝 Mối khách quen</h3><p>Ghi nhớ khách quen: khoảng ${fmt(k.tip_chance)}% việc xong được khách boa thêm ${fmt(k.tip_pct)}% tiền công.</p>${k.book?`<button class="btn ghost full" type="button" disabled>✓ Đã có</button>`:buy('book','Mua',k.book_price,'Mua 🤝 Mối khách quen? Trả bằng quỹ nghề.')}</article>`;
  const f=k.fast;
  const fast=f?`<article class="upgrade-card" data-paykit="fast"><div class="row spread"><span class="upgrade-icon" aria-hidden="true">⏩</span><span class="tag">${f.owned?'Đã có':'Tay quen'}</span></div><h3>⏩ Làm nhanh</h3><p>Bước nào bạn đã tự làm đúng ${fmt(f.need)} lần thì làm bằng một chạm. Vẫn được chấm như làm tay.</p>${(f.steps||[]).length?`<ul class="pay-fast-steps muted small" aria-label="Số lần đã làm đúng">${f.steps.map(x=>`<li><span>${x.n>=f.need?'✅':'⏳'} ${esc(x.label||'')}</span><b>${fmt(x.n)}/${fmt(f.need)}</b></li>`).join('')}</ul>`:''}${f.owned?`<button class="btn ghost full" type="button" disabled>✓ Đã có</button>`:buy('fast','Mua',f.price,'Mua ⏩ Làm nhanh? Trả bằng quỹ nghề.')}</article>`:'';
  return `<section class="space-top pay-shop" data-gear-group="paykit" aria-label="Bộ đồ nghề"><div class="row spread wrap"><h3>🧰 Bộ đồ nghề</h3><span class="tag green">+${fmt(k.total)}%</span></div>${now}<div class="upgrade-grid">${tool}${book}${fast}</div></section>`;
}
