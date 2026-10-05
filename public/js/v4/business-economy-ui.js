import {escapeHTML as esc} from '../icons.js';
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
export function businessControls(st,button){
 const b=st.business;if(!b)return '';
 const closed=b.paused,market=b.market,protection=b.protection;
 const options=protection?.options||[];
 return `<div class="qy-economy-controls"><div class="bk-actions">${button(closed?'🟢 Mở quầy':'🔴 Đóng quầy','pause',{id:st.id,on:!closed},closed?'primary':'ghost')}</div><p class="bk-hint">${closed?'Quầy đang đóng, không nhận khách mới.':'Quầy đang mở nhận khách khi đủ hàng và vốn.'} Đơn đã nhận vẫn được phục vụ. Thời gian đóng không tạo đơn bán bù.</p>
 ${market?`<div class="qy-market ${Number(market.demand_factor)<1?'down':'up'}"><b>${esc(market.label||'Thị trường')}</b><p>Lượng khách dự kiến ${fmt(Math.round(Number(market.demand_factor)*100))}% mức thường · giá menu do bạn đặt.</p></div>`:''}
 ${protection?`<details class="qy-protection"><summary>🛡️ ${esc(protection.label||'Bảo vệ quầy')} · ${fmt(protection.period_cost)} xu / ${Math.round((b.period_seconds||600)/60)} phút hoạt động</summary><p class="bk-hint">Gói bảo vệ giảm nguy cơ trộm khi quầy hoạt động. Phí theo tổng tài sản của bạn, gồm tiền, nhà, xe và đầu tư; báo giá giữ trong ngày game. Chi phí lấy từ vốn/két và ghi trong sổ.</p><div class="bk-actions">${options.map(x=>button(`${esc(x.label)} · ${fmt(x.period_cost)} xu`,'protection',{id:st.id,level:x.level},x.level===protection.level?'primary':'ghost',x.level===protection.level?'Đang sử dụng':'')).join('')}</div></details>`:''}</div>`;
}
