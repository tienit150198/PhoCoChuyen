import {escapeHTML as esc,icon} from '../icons.js';

export function equipmentView(c,career,upgrades){
 const items=upgrades.filter(u=>u.kind==='equipment'&&u.careers.includes(career)),owned=new Set(c.upgrades),current=items.filter(u=>owned.has(u.id)).at(-1),fmt=n=>Number(n).toLocaleString('vi-VN');
 return `<section class="work-equipment" aria-labelledby="work-equipment-title"><div class="row spread wrap"><div><span class="eyebrow">THIẾT BỊ NGHỀ</span><h3 id="work-equipment-title">Làm nhanh hơn</h3></div><span class="tag green">${current?`Đã lắp bậc ${current.gear_tier} · +${current.gear_rate-100}%`:'Thiết bị cơ bản'}</span></div><p>Trả bằng quỹ của nghề này. Chọn bậc để xem đúng tác dụng trước khi mua; công việc đang chạy giữ tốc độ lúc bắt đầu.</p><div class="upgrade-grid">${items.map(u=>{const installed=owned.has(u.id),missing=u.requires&&!owned.has(u.requires),short=c.money<u.price,disabled=installed||missing||short;return `<article class="upgrade-card"><div class="row spread">${icon('settings',27)}<span class="tag">+${u.gear_rate-100}% tốc độ</span></div><h3>${esc(u.name)}</h3><p>${esc(u.description)}</p><button class="btn ${installed?'ghost':'primary'} full" type="button" data-action="buyUpgrade" data-item="${u.id}"${disabled?' disabled':''}>${installed?'Đã lắp':missing?`Cần bậc ${u.gear_tier-1} trước`:short?`Thiếu ${fmt(u.price-c.money)} xu`:`Lắp thiết bị · ${fmt(u.price)} xu`}</button></article>`;}).join('')}</div></section>`;
}

// Reads only confirmed state. No sales, currency or clocks are simulated here.
export function hasWorkingStaff(state){return Object.values(state?.careers||{}).some(c=>c.business_running||c.ops?.business?.status==='running');}

export function staffRefreshPaused(ui,counterOpen=false,fairOpen=false){return !!(ui.busy||ui.ivBusy||ui.view==='home'&&ui.jrView==='invest'||counterOpen||fairOpen);}

export function staffRefresh({state,refresh,busy,visible=()=>!document.hidden,interval=30000,lastSync=()=>0,now=()=>Date.now()}){
 let stopped=false,pending=false;
 const timer=setInterval(async()=>{if(stopped||pending||busy()||!visible()||now()-lastSync()<interval||!hasWorkingStaff(state()))return;pending=true;try{await refresh();}catch{/* next visible tick retries */}finally{pending=false;}},interval);
 return ()=>{stopped=true;clearInterval(timer);};
}
