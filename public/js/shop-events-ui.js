import {escapeHTML as esc} from './icons.js';

/** Shared, non-modal owner event card. All prices/outcomes come from the server. */
export function shopEventCard(view,button){
  if(!view)return '';
  const event=view.pending,recent=view.recent||[];
  if(!event&&!recent.length)return '';
  return `<section class="shop-event-card" aria-label="Chuyện ở tiệm">
    <header><span class="eyebrow">${event?'VIỆC CẦN XỬ LÝ':'CHUYỆN Ở TIỆM'}</span>${view.camera?'<small>📹 Camera · giảm 50% nguy cơ trộm</small>':''}</header>
    ${event?`<h3>${esc(event.title)}</h3><p>${esc(event.text)}</p><div class="shop-event-choices">${event.choices.map(choice=>button(`<b>${esc(choice.label)}</b><small>${esc(choice.effect||'')}${choice.cost>0?` · ${Number(choice.cost).toLocaleString('vi-VN')} xu`:''}</small>`,event,choice)).join('')}</div>`:''}
    ${view.reputation_effect?`<p class="muted small">${esc(view.reputation_effect)}</p>`:''}
    ${recent.length?`<details class="shop-event-history"><summary>Đã xử lý gần đây</summary>${[...recent].reverse().slice(0,4).map(row=>`<p><b>${esc(row.title||'Chuyện ở tiệm')}</b><br>${esc(row.text||row.message||'')}</p>`).join('')}</details>`:''}
  </section>`;
}
