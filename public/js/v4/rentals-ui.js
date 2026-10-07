import {escapeHTML as esc} from '../icons.js';
const xu=n=>Number(n||0).toLocaleString('vi-VN')+' xu';
// F#225: the wall-clock end of a player tenant's paid period (dd/mm, Vietnam time).
export const paidDate=t=>{const d=new Date(Number(t)*1000+7*3600e3),p=n=>String(n).padStart(2,'0');return `${p(d.getUTCDate())}/${p(d.getUTCMonth()+1)}`;};
export const rentalRetryable=error=>!error?.status||error.status>=500||[408,429].includes(error.status);
export const rentalPrice=value=>{const n=Number(String(value??'').trim());return Number.isSafeInteger(n)&&n>0&&n<=1000000000?n:null;};
export function rentalDemandHint(value,reference){const ask=rentalPrice(value);if(!ask)return 'Nhập số xu nguyên dương.';const chance=Math.max(0,Math.min(90,Math.floor((300*reference-100*ask)/(4*Math.max(1,reference)))));return `${chance>=50?'Dễ tìm khách':chance>0?'Khó tìm khách hơn':'Giá quá cao: NPC chưa thuê'} · khoảng ${chance}% cơ hội mỗi ngày.`;}
export function propertyNews(news){return news?.title?`<p class="rental-news">📰 ${esc(news.title)}${news.phase==='recovery'?'<br><small>Ảnh hưởng đang giảm dần.</small>':''}</p>`:'';}
export function rentalMarketView(data,homes,drafts,button){
  if(!data)return '<p role="status">Đang tải chợ thuê nhà…</p>';
  if(data.error)return `<p class="bk-alert bad">${esc(data.error)}</p>${button('Thử lại','rentalReload',{},'primary')}`;
  const period=data.rules?.period_days||5;
  const lease=data.tenancy;
  const terms=data.rules?.terms||`Trả trước ${period} ngày sống của người thuê. Hết kỳ cần gia hạn; giá đã ký không tự tăng.`;
  const current=lease?`<section class="rental-card"><span class="eyebrow">NHÀ BẠN ĐANG THUÊ</span><h3>${esc(lease.name)}</h3><p>Chủ nhà: ${esc(lease.owner_name||'Người chơi')} · ${xu(lease.rent)}/${period} ngày</p><p>Đã trả tới ngày sống ${Number(lease.end_day)} của bạn.</p><div class="bk-actions">${button('🚪 Vào nhà','inside',{},'primary')}${button('Gia hạn','rentalRenew',{id:lease.id},'ghost')}${button('Trả nhà','rentalLeave',{id:lease.id},'ghost')}</div></section>`:'';
  const own=homes.map(home=>{
    const row=(data.mine||[]).find(r=>r.property===home.id&&['listing','leased'].includes(r.status));
    const ad=home.rental_ad;
    let status;
    if(home.let)status=`<p>${esc(home.let.name)} đang thuê · ${xu(home.let.rent)}/kỳ.</p>${button('Lấy lại nhà NPC','unlet',{id:home.id},'ghost')}`;
    else if(row)status=`<p>${row.status==='leased'?`${esc(row.tenant_name||'Người chơi')} đang thuê${row.paid_until?` · hết hạn ngày ${paidDate(row.paid_until)}`:` tới ngày ${Number(row.end_day)} của người thuê`}.`:`Đã đăng ${xu(row.rent)}/kỳ; đang chờ người chơi.`}</p>${row.status!=='leased'?button('Gỡ tin','rentalCancel',{id:row.id},'ghost'):row.reclaim?button('Lấy lại nhà','rentalReclaim',{id:row.id},'ghost'):''}`;   // F#225: after the paid period the owner may reclaim
    else if(ad)status=`<p>Đang tìm NPC · ${xu(ad.rent)}/kỳ. ${Number(ad.demand_pct||0)}% cơ hội tìm khách mỗi ngày.</p>${button('Gỡ tin NPC','unlet',{id:home.id},'ghost')}`;
    else status=`<label class="rental-price" for="rent-${esc(home.id)}">Giá cho thuê / ${period} ngày<input id="rent-${esc(home.id)}" data-rental-price="${esc(home.id)}" data-reference="${Number(home.let_rent)}" type="number" inputmode="numeric" min="1" step="1" value="${esc(drafts[home.id]??home.let_rent)}"></label><output class="bk-hint" data-rental-demand aria-live="polite">${rentalDemandHint(drafts[home.id]??home.let_rent,home.let_rent)}</output><div class="bk-actions">${button('Tìm khách NPC','rentalNpc',{id:home.id},'primary')}${button('Đăng cho người chơi','rentalList',{id:home.id},'ghost')}</div>`;
    return `<article class="rental-card"><h3>${esc(home.emoji||'🏠')} ${esc(home.name)}</h3><p>Tham khảo ${xu(home.let_rent)}/kỳ · định giá cao sẽ khó tìm khách hơn.</p>${propertyNews(home.market_news)}${status}</article>`;
  }).join('');
  const market=(data.market||[]).map(row=>`<article class="rental-card"><h3>${esc(row.emoji||'🏠')} ${esc(row.name)}</h3><p>Chủ nhà ${esc(row.owner_name)}</p><strong>${xu(row.rent)} / ${period} ngày</strong>${row.market_rent?`<p>Giá tham khảo ${xu(row.market_rent)}/kỳ</p>`:''}${propertyNews(row.market_news)}<div class="bk-actions">${button('Xem & thuê','rentalAccept',{id:row.id},'primary',lease?' disabled':'')}</div></article>`).join('');
  return `<p class="bk-hint">${esc(terms)}</p>${data.locked?`<p class="bk-alert warn">${esc(data.locked)}</p>`:''}${current}<h3>Nhà của bạn cho thuê</h3>${own||'<p class="bk-hint">Mua thêm một căn, để trống để đăng cho thuê.</p>'}<h3>Thuê nhà người chơi</h3>${market||'<p class="bk-hint">Chưa có tin phù hợp. Bạn có thể quay lại sau.</p>'}<div class="bk-actions">${data.next_offset!=null?button('Xem thêm nhà','rentalMore',{},'primary'):''}${button('Làm mới chợ nhà','rentalReload',{},'ghost')}</div>`;
}
