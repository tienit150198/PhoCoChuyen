import {escapeHTML as esc} from '../icons.js';
import {RANGES,rangeOf} from './invest-market.js';
const label=n=>Number(n).toLocaleString('vi-VN',{maximumFractionDigits:2});
const time=t=>new Date(t*1000).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
export function rangeControls(env){return `<nav class="iv-ranges" aria-label="Khung thời gian biểu đồ">${RANGES.map(r=>`<button type="button" data-action="ivRange" data-range="${r}" aria-pressed="${rangeOf(env)===r}">${r}</button>`).join('')}</nav><p class="iv-range-note">H = giờ · D = ngày · W = tuần · M = 30 ngày ngoài đời</p>`;}
export function marketChart(env,asset,fallback,clock,unit=1){
 const q=env.ui.ivQuotes?.[rangeOf(env)],source=q?.[asset]?.points;
 const current=asset==='coin'?env.api.state.invest.coin:env.api.state.vang,latest=current.market_clock;
 let points=source||fallback.map((p,i)=>[(clock?.timestamps||latest?.timestamps)?.[i],p]).filter(p=>Number.isFinite(p[0]));
 if(!points.length)return '<figure class="iv-chart"><p>Chưa có lịch sử giá cho biểu đồ.</p></figure>';
 if(latest&&latest.as_of>points.at(-1)[0])points=[...points,[latest.as_of,asset==='coin'?current.price:current.p]];
 const values=points.map(p=>p[1]/unit),lo=Math.min(...values),hi=Math.max(...values),pad=Math.max((hi-lo)*.12,hi*.001,1/unit),min=lo-pad,max=hi+pad;
 const w=520,h=218,left=64,right=10,top=12,bottom=40,x=i=>left+(w-left-right)*(points.length===1?.5:(points[i][0]-points[0][0])/(points.at(-1)[0]-points[0][0])),y=p=>top+(max-p)/(max-min)*(h-top-bottom);
 const line=values.map((p,i)=>`${x(i).toFixed(1)},${y(p).toFixed(1)}`).join(' '),gain=values.at(-1)>=values[0];
 const grid=[max,(max+min)/2,min].map(p=>`<g><line x1="${left}" x2="${w-right}" y1="${y(p)}" y2="${y(p)}"/><text x="${left-7}" y="${y(p)+4}" text-anchor="end">${label(p)}</text></g>`).join('');
 const ix=Math.max(0,Math.min(points.length-1,Number.isInteger(env.ui.ivPoint)?env.ui.ivPoint:points.length-1));
 const p=points[ix],change=(values.at(-1)-values[0])*100/values[0];
 const limited=q&&q.epoch>q.as_of-({'1H':3600,'1D':86400,'3D':259200,'1W':604800,'1M':2592000}[rangeOf(env)]);
 return `<figure class="iv-chart iv-timeline"><div class="iv-chart-reading"><strong>${label(p[1]/unit)} xu${asset==='gold'?'/chỉ':''}</strong><span>${esc(time(p[0]))}</span><b class="${gain?'gain':'loss'}">${change>=0?'+':''}${label(change)}% trong dữ liệu hiển thị</b></div><svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Biểu đồ ${asset==='coin'?'Mây Coin':'vàng'} ${rangeOf(env)}, trục giá theo xu và thời gian thực" class="iv-price-chart ${gain?'up':'down'}"><g class="iv-chart-grid">${grid}</g><polyline points="${line}"/><circle cx="${x(ix)}" cy="${y(p[1]/unit)}" r="4"/><text class="iv-chart-date" x="${left}" y="${h-10}">${esc(time(points[0][0]))}</text><text class="iv-chart-date" x="${w-right}" y="${h-10}" text-anchor="end">${esc(time(points.at(-1)[0]))}</text></svg><label class="iv-chart-scrub">Kéo để xem giá từng mốc<input type="range" data-iv-point min="0" max="${points.length-1}" value="${ix}" aria-label="Xem giá tại thời điểm"${points.length<2?' disabled':''}></label><figcaption>${limited?'Thị trường mới mở, đang hiển thị toàn bộ lịch sử đã có.':'Lịch sử giá theo thời gian thực.'} ${points.length} điểm giá${source?'':' · bấm Cập nhật giá để tải khung đã chọn'}.</figcaption></figure>`;
}
