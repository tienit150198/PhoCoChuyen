import {escapeHTML as esc} from '../icons.js';
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const PLAN_CUT={basic:20,premium:40};
const COST_NAMES=[['wages','lương'],['rent','thuê chỗ'],['power','điện'],['environment','môi trường'],['protection','bảo vệ']];
/** ⏱️ What an open counter costs per period, and what it has paid so far (ticks live: tickRunningCosts). */
export function runningCostHTML(st){
 const b=st.business,rc=b?.running_cost;if(!rc)return '';
 const mins=Math.round((b.period_seconds||600)/60),rates=b.rates||{};
 const parts=COST_NAMES.filter(([k])=>Number(rates[k])>0).map(([k,n])=>`${n} ${fmt(rates[k])}`).join(' · ');
 return `<div class="qy-runcost" data-qk="runcost:${esc(st.id)}"><p><b>⏱️ Quầy mở tốn ${fmt(rc.per_period)} xu / ${mins} phút</b>${parts?`<small> (${parts})</small>`:''}</p>
  <p>Đã trả cho thời gian mở quầy: <b data-qy-cost="${esc(st.id)}" data-spent="${Number(rc.spent)||0}" data-rate="${(Number(rc.per_period)||0)/(b.period_seconds||600)}" data-on="${rc.accruing?1:0}" data-cursor="${Number(b.server_now)||0}">${fmt(rc.spent)} xu</b> · ${rc.accruing?'đang tính':'đang dừng'}</p>
  <p class="bk-hint">Lương, thuê chỗ, điện, phí môi trường và bảo vệ tính theo thời gian quầy mở và làm việc, kể cả lúc chưa có khách. Vắng khách thì bấm 🔴 Đóng quầy để ngừng tính.</p></div>`;
}
/** Live counter: adds the cost accrued since the server's last settlement (clamped to one period). */
export function tickRunningCosts(root,seen,now=performance.now()){
 for(const el of root?.querySelectorAll?.('[data-qy-cost]')||[]){
  const id=el.dataset.qyCost,cursor=el.dataset.cursor,spent=Number(el.dataset.spent)||0;
  let mark=seen[id];if(!mark||mark.cursor!==cursor)mark=seen[id]={cursor,at:now};
  const extra=el.dataset.on==='1'?Math.min(600,Math.max(0,(now-mark.at)/1000))*(Number(el.dataset.rate)||0):0;
  const text=`${fmt(Math.floor(spent+extra))} xu`;if(el.textContent!==text)el.textContent=text;
 }
}
/** 🕵️ The theft odds the server applies (camera, chuông, két, bảo vệ already counted). */
export function theftRiskHTML(st){
 const r=st.theft_risk;if(!r)return '';
 const pct=Number(r.pct).toLocaleString('vi-VN',{maximumFractionDigits:1});
 const when=r.per==='event'?`mỗi lần quầy có chuyện (khoảng ${fmt(r.every||12)} món bán một lần)`:'mỗi ngày bán';
 return `<p class="bk-hint qy-risk">🕵️ Rủi ro trộm: <b>${pct}%</b> ${when}. Camera −50%, chuông −25%, két sắt −20% và trộm lấy tối đa nửa két, bảo vệ cơ bản −20%, tăng cường −40%.</p>`;
}
export function businessControls(st,button){
 const b=st.business;if(!b)return '';
 const closed=b.paused,market=b.market,protection=b.protection;
 const options=protection?.options||[];
 return `<div class="qy-economy-controls"><div class="bk-actions">${button(closed?'🟢 Mở quầy':'🔴 Đóng quầy','pause',{id:st.id,on:!closed},closed?'primary':'ghost')}</div><p class="bk-hint">${closed?'Quầy đang đóng, không nhận khách mới.':'Quầy đang mở nhận khách khi đủ hàng và vốn.'} Đơn đã nhận vẫn được phục vụ. Thời gian đóng không tạo đơn bán bù.</p>
 ${market?`<div class="qy-market ${Number(market.demand_factor)<1?'down':'up'}"><b>${esc(market.label||'Thị trường')}</b><p>Lượng khách dự kiến ${fmt(Math.round(Number(market.demand_factor)*100))}% mức thường · giá menu do bạn đặt.</p></div>`:''}
 ${protection?`<details class="qy-protection"><summary>🛡️ ${esc(protection.label||'Bảo vệ quầy')} · ${fmt(protection.period_cost)} xu / ${Math.round((b.period_seconds||600)/60)} phút hoạt động</summary><p class="bk-hint">Gói bảo vệ giảm khả năng bị trộm khi quầy hoạt động: cơ bản −20%, tăng cường −40%. Phí theo tổng tài sản của bạn, gồm tiền, nhà, xe và đầu tư; báo giá giữ trong ngày game. Chi phí lấy từ vốn/két và ghi trong sổ.</p><div class="bk-actions">${options.map(x=>button(`${esc(x.label)}${PLAN_CUT[x.level]?` (−${PLAN_CUT[x.level]}% trộm)`:''} · ${fmt(x.period_cost)} xu`,'protection',{id:st.id,level:x.level},x.level===protection.level?'primary':'ghost',x.level===protection.level?'Đang sử dụng':'')).join('')}</div></details>`:''}${theftRiskHTML(st)}${runningCostHTML(st)}</div>`;
}
