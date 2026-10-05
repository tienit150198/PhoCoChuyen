import {escapeHTML as esc} from './icons.js';
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
export function staffLifeCard(view,button){
 if(!view)return '';
 const e=view.pending,recent=view.recent||[],employees=view.employees||[];
 if(!e&&!recent.length&&!employees.length)return '';
 return `<section class="shop-event-card staff-life-card" aria-label="Chuyện nhân viên"><header><span class="eyebrow">ĐỘI NGŨ NPC</span></header>
 ${e?`<h3>${esc(e.title)}</h3><p><b>${esc(e.name)}</b> · ${esc(e.text)}</p><div class="shop-event-choices">${e.choices.map(ch=>button(`<b>${esc(ch.label)}</b><small>${esc(ch.effect||'')}${ch.cost?` · ${fmt(ch.cost)} xu`:''}</small>`,e,ch)).join('')}</div>`:''}
 ${employees.length?`<details><summary>Lương và tinh thần nhân viên</summary>${employees.map(x=>`<p><b>${esc(x.name)}</b> · lương ${fmt(x.wage)} xu · tinh thần ${fmt(x.morale)}/100</p>`).join('')}</details>`:''}
 ${recent.length?`<details><summary>Chuyện đã xử lý</summary>${[...recent].reverse().slice(0,5).map(x=>`<p><b>${esc(x.name||x.title||'Nhân viên')}</b> · ${esc(x.text||x.message||'')}${x.cost?` · ${fmt(x.cost)} xu`:''}</p>`).join('')}</details>`:''}</section>`;
}
