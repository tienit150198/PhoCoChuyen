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
/** F#263/#264 (08/10, "5 tiệm quần áo không độn giá mà suy thoái cả 5"): the market is one calendar for the whole town
 * (game/quay_market.py). The run of now from the calendar the server sent (`runs`): the browser's clock picks it, so a
 * state a little old still shows the right phase. An older server (label + demand_factor only) is shown as it is. */
export function marketNow(m,now=Date.now()/1000){
  if(!m)return null;
  const runs=Array.isArray(m.runs)?m.runs:[],i=runs.findIndex(r=>now>=r.starts_at&&now<r.ends_at);
  return i<0?{...m,end:null,next:null}:{...m,...runs[i],end:runs[i].ends_at,next:runs[i+1]||null};
}
const hhmm=t=>{const d=new Date(t*1000);return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;};
const minsLeft=(t,now)=>{const m=Math.max(1,Math.ceil((t-now)/60));return m>=60?`${Math.floor(m/60)} giờ${m%60?` ${m%60} phút`:''}`:`${m} phút`;};
const hours=m=>m%60?`${fmt(m)} phút`:`${fmt(m/60)} giờ`;
/** The market box of a counter: the phase for the whole town, until when, what comes next, and (separately) what this
 * counter's own prices do to its walk-ins (business.price_effect, game/quay_business.py). */
export function marketHTML(b,now=Date.now()/1000){
 const m=marketNow(b?.market,now);if(!m)return '';
 const pct=Math.round(Number(m.demand_factor)*100),down=pct<100,up=pct>100;
 const when=m.end?`<p>Tới ${hhmm(m.end)} (còn ${minsLeft(m.end,now)}).${m.next?` <span>Sau đó: ${esc(m.next.label||'')} ${fmt(Math.round(Number(m.next.demand_factor)*100))}%.</span>`:''}</p>`:'';
 const town=m.town?`<p>${down?'Cả phố cùng lúc: mọi quầy của mọi người chơi cùng vắng khách. Không phải do giá của bạn, cũng không phải do bạn mở nhiều quầy.':'Cả phố cùng lúc: mọi quầy của mọi người chơi cùng một mức.'}</p>`:'';
 const tip=down&&m.down_minutes?`<p>Suy thoái chỉ khoảng ${hours(Number(m.down_minutes))} mỗi ngày; tính cả ngày, khách trung bình ${fmt(m.day_percent)}% nhờ những lúc hưng thịnh. Cứ để quầy bán tiếp, hoặc 🔴 Đóng quầy lúc này cho đỡ tốn lương, điện.</p>`:'';
 const pe=Number(b.price_effect);
 const price=b.price_effect==null||!Number.isFinite(pe)?'':pe<95?`<p class="qy-price-effect dear">💸 Giá menu quầy này cao hơn giá tham khảo: khách mua còn ${fmt(pe)}%. Hạ giá ở 🍽️ Menu để đông khách hơn.</p>`
   :pe>105?`<p class="qy-price-effect">🏷️ Giá menu quầy này mềm: khách mua ${fmt(pe)}% so với giá tham khảo.</p>`:`<p class="qy-price-effect">🏷️ Giá menu quầy này vừa phải: không làm khách bớt mua.</p>`;
 return `<div class="qy-market ${down?'down':'up'}"><b><span aria-hidden="true">${down?'🌧️':up?'☀️':'🌤️'}</span> ${m.town?'<span>Chợ cả phố:</span> ':''}<span>${esc(m.label||'Thị trường')}</span></b> <small>· <span>khách ${fmt(pct)}% mức thường</span></small>${when}${town}${tip}${price}</div>`;
}
/** One line over the counters while the town's market is down: every counter slows together (F#263/#264). */
export function marketBanner(stalls,now=Date.now()/1000){
 const b=(stalls||[]).map(st=>st.business).find(b=>b?.market?.town);const m=b&&marketNow(b.market,now);
 if(!m||!(Number(m.demand_factor)<1))return '';
 const pct=fmt(Math.round(Number(m.demand_factor)*100));
 return `<p class="bk-alert warn qy-market-all" role="status">${m.end?`🌧️ Chợ cả phố đang suy thoái tới ${hhmm(m.end)}: mọi quầy của mọi người chơi cùng vắng hơn (${pct}% khách). Không phải do giá hay do bạn mở nhiều quầy.`
   :`🌧️ Chợ cả phố đang suy thoái: mọi quầy của mọi người chơi cùng vắng hơn (${pct}% khách). Không phải do giá hay do bạn mở nhiều quầy.`}</p>`;
}
export function businessControls(st,button){
 const b=st.business;if(!b)return '';
 const closed=b.paused,market=b.market,protection=b.protection;
 const options=protection?.options||[];
 return `<div class="qy-economy-controls"><div class="bk-actions">${button(closed?'🟢 Mở quầy':'🔴 Đóng quầy','pause',{id:st.id,on:!closed},closed?'primary':'ghost')}</div><p class="bk-hint">${closed?'Quầy đang đóng, không nhận khách mới.':'Quầy đang mở nhận khách khi đủ hàng và vốn.'} Đơn đã nhận vẫn được phục vụ. Thời gian đóng không tạo đơn bán bù.</p>
 ${market?marketHTML(b):''}
 ${protection?`<details class="qy-protection"><summary>🛡️ ${esc(protection.label||'Bảo vệ quầy')} · ${fmt(protection.period_cost)} xu / ${Math.round((b.period_seconds||600)/60)} phút hoạt động</summary><p class="bk-hint">Gói bảo vệ giảm khả năng bị trộm khi quầy hoạt động: cơ bản −20%, tăng cường −40%. Phí theo tổng tài sản của bạn, gồm tiền, nhà, xe và đầu tư; báo giá giữ trong ngày game. Chi phí lấy từ vốn/két và ghi trong sổ.</p><div class="bk-actions">${options.map(x=>button(`${esc(x.label)}${PLAN_CUT[x.level]?` (−${PLAN_CUT[x.level]}% trộm)`:''} · ${fmt(x.period_cost)} xu`,'protection',{id:st.id,level:x.level},x.level===protection.level?'primary':'ghost',x.level===protection.level?'Đang sử dụng':'')).join('')}</div></details>`:''}${theftRiskHTML(st)}${runningCostHTML(st)}</div>`;
}
