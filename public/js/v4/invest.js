/** Đầu tư cá nhân: gold, savings at the neighbourhood bank, Mây Coin (a fictional
 * crypto) and the occasional "lãi khủng" project. Markup only: every rule and
 * number lives in game/invest.py (state.invest = invest.public()).
 * Buttons use data-action="iv…" (investAction) or journey's `jrView`.
 * Design: docs/superpowers/specs/2026-09-29-invest-design.md */
import {icon,escapeHTML as esc} from '../icons.js';
import {marketBoot,refreshQuotes,changeRange,marketView} from './invest-market.js';
import {marketChart,rangeControls} from './invest-chart.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const signed=n=>`${n>0?'+':n<0?'−':''}${fmt(Math.abs(n))} xu`;
const price=(p,R)=>(p/(R?.cent||100)).toLocaleString('vi-VN',{maximumFractionDigits:2});
const coins=(u,R)=>(u/(R?.coin||1000)).toLocaleString('vi-VN',{maximumFractionDigits:3});
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,action,data={},style='',extra='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}${extra}>${label}</button>`;
const CHIPS=[50,100,200,'all'];
const LOG_ICON={buy:'🪙',sell:'💱',save:'🏦',withdraw:'👛',interest:'🌱',pump:'📈',crash:'📉',scam_offer:'📣',scam_join:'💸',scam_pay:'💸',scam_gone:'🕳️',scam_decline:'🛡️',scam_news:'📰'};

const stateOf=env=>marketView(env).I;
const pick=(env,box)=>env.ui[box==='save'?'ivSave':'ivCoin']??100;
const payload=v=>v==='all'?{all:true}:{amount:Number(v)};
const label=v=>v==='all'?'Tất cả':`${fmt(v)} xu`;

function head(title,sub){
  return `<header class="sheet-head jr-head iv-head"><button type="button" class="btn ghost small jr-back" data-action="jrView" data-view="wallet" aria-label="Quay lại ví">${icon('back',18)}</button><div class="grow"><span class="eyebrow">TÀI SẢN CỦA BẠN</span><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div><button type="button" class="icon-btn" data-action="close" aria-label="Đóng">${icon('x',20)}</button></header>`;
}

/** Inline SVG sparkline of the recent Mây Coin prices (oldest → newest). */
export function sparkline(prices,{cost=null,R=null,w=320,h=84,name='Mây Coin',clock=null}={}){
  const pts=(prices||[]).filter(Number.isFinite);
  if(pts.length<2)return '';
  const lo=Math.min(...pts,cost??Infinity),hi=Math.max(...pts,cost??-Infinity),pad=8,span=Math.max(1,hi-lo);
  const X=i=>pad+i*(w-2*pad)/(pts.length-1),Y=v=>h-pad-(v-lo)*(h-2*pad)/span;
  const line=pts.map((v,i)=>`${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(' ');
  const up=pts[pts.length-1]>=pts[0],first=pts[0],last=pts[pts.length-1];
  const hits=pts.map((v,i)=>{const x0=i?(X(i-1)+X(i))/2:0,x1=i<pts.length-1?(X(i)+X(i+1))/2:w;
    const ago=pts.length-1-i,when=clock?`${ago?`${ago} phiên trước`:'Phiên hiện tại'}${clock.timestamps?.[i]?` · ${marketTime(clock.timestamps[i])}`:''}`:ago?`${ago} ngày trước`:'Hôm nay';return `<rect x="${x0.toFixed(1)}" y="0" width="${(x1-x0).toFixed(1)}" height="${h}" fill="transparent"><title>${esc(when)}: ${price(v,R)} xu</title></rect>`;}).join('');
  const costLine=cost!=null?`<line class="iv-cost" x1="${pad}" x2="${w-pad}" y1="${Y(cost).toFixed(1)}" y2="${Y(cost).toFixed(1)}"/>`:'';
  const summary=`Giá ${name} ${pts.length} ${clock?'phiên 10 phút':'ngày'}: từ ${price(first,R)} xu tới ${price(last,R)} xu, thấp nhất ${price(Math.min(...pts),R)}, cao nhất ${price(Math.max(...pts),R)}.`;
  return `<svg class="iv-spark ${up?'up':'down'}" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(summary)}">
    <path class="iv-area" d="M${X(0).toFixed(1)},${h-pad} L${line.replace(/ /g,' L')} L${X(pts.length-1).toFixed(1)},${h-pad} Z"/>
    ${costLine}<polyline class="iv-line" points="${line}"/>
    <circle class="iv-dot" cx="${X(pts.length-1).toFixed(1)}" cy="${Y(last).toFixed(1)}" r="4.5"/>${hits}</svg>`;
}

const marketTime=t=>new Date(t*1000).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'});
function marketClock(C){
  if(!C)return 'Vàng đổi giá theo ngày thực · Coin đổi giá theo ngày sống.';
  return `Giá chung cả phố · 1 giờ thực = 1 ngày thị trường.<br>Ngày thị trường ${fmt(C.market_day)} · Giá đổi mỗi 10 phút, kể cả khi bạn offline.<br>Giá đang xem: ${esc(marketTime(C.as_of))} (giờ Việt Nam).`;
}

function chips(env,box,limit){
  const cur=pick(env,box);
  return `<div class="chip-row iv-chips" role="group" aria-label="Chọn số xu">${CHIPS.map(v=>{const on=String(cur)===String(v);
    return `<button type="button" class="chip ${on?'selected':''}" data-action="ivAmt" data-box="${box}" data-v="${v}" aria-pressed="${on}"${v!=='all'&&limit!=null&&v>limit?' data-over="1"':''}>${label(v)}</button>`;}).join('')}</div>`;
}

/* ------------------------------------------------------------------ cards */
function savingCard(env,I){
  const S=I.saving,R=I.rules,v=pick(env,'save'),amt=v==='all'?I.wallet:Number(v);
  const rate=`${Math.floor(R.rate_milli/10)},${R.rate_milli%10}%`;
  const term=S.balance?`<div class="iv-kv"><span>Lãi kỳ này (chưa cộng)</span><b>${xu(S.pending)}</b></div><div class="iv-kv"><span>Còn tới ngày cộng lãi</span><b>${fmt(S.term_left)} ngày</b></div><div class="iv-kv"><span>Lãi mỗi ngày khoảng</span><b>${(S.daily_milli/1000).toLocaleString('vi-VN',{maximumFractionDigits:1})} xu</b></div>`:'';
  return `<section class="jr-card iv-card iv-bank" aria-labelledby="ivBankT">
    <div class="iv-card-top"><span class="iv-emoji" aria-hidden="true">🏦</span><div class="grow"><span class="eyebrow">Ngân hàng phố</span><h3 id="ivBankT">Gửi tiết kiệm</h3><p class="muted small">Lãi ${rate}/ngày${R.save_tier?` cho ${xu(R.save_tier)} đầu, phần trên lãi ${Math.floor(R.rate_hi_milli/10)},${R.rate_hi_milli%10}%/ngày`:''}, cộng vào sổ mỗi ${R.term} ngày. Không bao giờ lỗ vốn.</p>${S.flat&&R.save_tier&&S.balance>R.save_tier?`<p class="muted small">Kỳ này vẫn tính ${rate}/ngày cho cả sổ, từ kỳ sau tính theo bậc.</p>`:''}${S.earned?`<span class="tag green iv-earned">Đã nhận lãi ${xu(S.earned)}</span>`:''}</div></div>
    <div class="iv-big"><small>Sổ tiết kiệm</small><strong>${xu(S.balance)}</strong></div>
    ${term}
    ${chips(env,'save')}
    <div class="iv-actions">${btn(`Gửi ${v==='all'?'hết ví':label(v)}`,'ivSave',{},'primary',I.wallet<1||amt>I.wallet?' disabled':'')}${btn(`Rút ${v==='all'?'hết sổ':label(v)}`,'ivWithdraw',{},'cream',!S.balance||(v!=='all'&&amt>S.balance)?' disabled':'')}</div>
    ${S.balance&&S.pending?`<p class="iv-hint">${icon('clock',14)} Rút trước ngày cộng lãi thì mất ${xu(S.pending)} lãi của kỳ này.</p>`:''}
  </section>`;
}

function coinCard(env,I){
  const C=I.coin,R=I.rules,v=pick(env,'coin'),amt=v==='all'?I.wallet:Number(v);
  const fee=a=>Math.max(1,Math.ceil(a*R.fee_pct/100));
  const cost=C.units?Math.round(C.basis*R.coin*R.cent/C.units):null;
  const ch=C.change,dir=ch>0?'up':ch<0?'down':'flat';
  const hold=C.units?`<div class="iv-hold">
      <div class="iv-kv"><span>Đang giữ</span><b>${coins(C.units,R)} MÂY</b></div>
      <div class="iv-kv"><span>Trị giá hiện tại</span><b>${xu(C.value)}</b></div>
      <div class="iv-kv"><span>Tiền đã bỏ vào (gồm phí)</span><b>${xu(C.basis)}</b></div>
      <div class="iv-kv iv-pnl ${C.unrealised>=0?'gain':'loss'}"><span>${C.unrealised>=0?'Lãi tạm tính':'Lỗ tạm tính'}</span><b>${signed(C.unrealised)}</b></div></div>`
    :`<p class="muted small">Bạn chưa có Mây Coin.</p>`;
  const buyAmt=v==='all'?I.wallet:amt,sellAmt=v==='all'?C.value:amt;
  const preview=buyAmt>=R.min_trade?`Mua ${xu(buyAmt)}: phí ${R.fee_pct}% = ${xu(fee(buyAmt))}.`:`Lệnh ít nhất ${xu(R.min_trade)}.`;
  return `<section class="jr-card iv-card iv-coin" aria-labelledby="ivCoinT">
    <div class="iv-card-top"><span class="iv-emoji" aria-hidden="true">☁️</span><div class="grow"><span class="eyebrow">Tiền ảo · chỉ có trong game</span><h3 id="ivCoinT">Mây Coin</h3></div>
      <div class="iv-price"><strong>${price(C.price,R)} xu</strong><span class="iv-change ${dir}">${dir==='up'?'▲':dir==='down'?'▼':'•'} ${ch>0?'+':''}${Number(ch).toLocaleString('vi-VN',{maximumFractionDigits:2})}% <small>${C.market_clock?'so với phiên trước':'hôm nay'}</small></span></div></div>
    ${marketNews(C.market_news)}
    ${marketChart(env,'coin',C.prices,C.market_clock,R.cent)}
    ${hold}
    ${C.realised||C.fees?`<div class="iv-kv small"><span>Đã chốt lãi/lỗ · phí đã trả</span><b class="${C.realised>=0?'gain':'loss'}">${signed(C.realised)} · ${xu(C.fees)}</b></div>`:''}
    ${chips(env,'coin')}
    <div class="iv-actions">${btn(`Mua ${v==='all'?'hết ví':label(v)}`,'ivBuy',{},'primary',buyAmt<R.min_trade||buyAmt>I.wallet?' disabled':'')}${btn(`Bán ${v==='all'?'hết coin':label(v)}`,'ivSell',{},'cream',!C.units||(v!=='all'&&(sellAmt>C.value||sellAmt<R.min_trade))?' disabled':'')}</div>
    <p class="iv-hint">${esc(preview)} Giá được chốt khi máy chủ nhận lệnh.</p>
  </section>`;
}

function marketNews(news){
  if(!news?.active||!news.title)return '';
  const up=news.direction==='up';
  return `<aside class="iv-news ${up?'up':'down'}"><small>📰 Tin thị trường trong game</small><b>${esc(news.title)}</b><span>${up?'Đang hỗ trợ đà tăng':'Đang tạo áp lực giảm'}</span></aside>`;
}
const goldAmount=n=>n<10?`${n} phân`:`${(n/10).toLocaleString('vi-VN',{maximumFractionDigits:1})} chỉ`;
const goldQty=env=>Math.max(1,Math.min(100000,Math.floor(Number(env.ui.ivGoldQty)||1)));
const goldCost=(n,G)=>Math.ceil(n*G.buy/10);
const goldWorth=(n,G)=>Math.floor(n*G.sell/10);
function goldCard(env,G){
  if(!G)return '<section class="jr-card iv-card"><p>Chưa tải được giá vàng. Mở lại mục Đầu tư để thử nhé.</p></section>';
  const n=goldQty(env),sellN=Math.min(n,G.phan),gain=G.value-G.cost;
  const change=G.y?(G.p-G.y)*100/G.y:0;
  const J=env.api.state.journey||{},have=Math.max(0,J.wallet||0)+(J.bank?.balance||0);
  const cost=G.phan?G.cost*10/G.phan:null;
  return `<section class="jr-card iv-card iv-gold" aria-labelledby="ivGoldT">
    <div class="iv-card-top"><span class="iv-emoji" aria-hidden="true">🪙</span><div class="grow"><span class="eyebrow">Tiệm vàng Kim Phát</span><h3 id="ivGoldT">Vàng</h3></div><div class="iv-price"><strong>${xu(G.p)}/chỉ</strong><span class="iv-change ${change>=0?'up':'down'}">${change>=0?'▲ +':'▼ '}${change.toLocaleString('vi-VN',{maximumFractionDigits:1})}% <small>${G.market_clock?'so với phiên trước':'hôm nay'}</small></span></div></div>
    ${marketNews(G.market_news|| (G.news?{title:G.news,active:true,direction:change>=0?'up':'down'}:null))}
    ${marketChart(env,'gold',G.hist,G.market_clock)}
    <div class="iv-hold"><div class="iv-kv"><span>Đang giữ</span><b>${goldAmount(G.phan)}</b></div><div class="iv-kv"><span>Bán ngay được</span><b>${xu(G.value)}</b></div><div class="iv-kv"><span>Tiền đã bỏ vào</span><b>${xu(G.cost)}</b></div><div class="iv-kv iv-pnl ${gain>=0?'gain':'loss'}"><span>${gain>=0?'Lãi tạm tính':'Lỗ tạm tính'}</span><b>${signed(gain)}</b></div></div>
    <p class="iv-hint">Tiệm bán ${xu(G.buy)}/chỉ · mua lại ${xu(G.sell)}/chỉ.${G.market_clock?' Biến động so với phiên trước. Giá được chốt khi máy chủ nhận lệnh.':''}</p>
    <div class="iv-gold-quantity" role="group" aria-label="Số vàng giao dịch">${btn('−','ivGoldStep',{d:-1},'cream',' aria-label="Bớt vàng"')}<b>${goldAmount(n)}</b>${btn('+','ivGoldStep',{d:1},'cream',' aria-label="Thêm vàng"')}</div>
    <div class="iv-gold-chips">${[[1,'1 phân'],[10,'1 chỉ'],[50,'5 chỉ']].map(([q,label])=>btn(label,'ivGoldQty',{n:q},q===n?'primary small':'cream small',` aria-pressed="${q===n}"`)).join('')}</div>
    <div class="iv-actions">${btn(`Mua · ${xu(goldCost(n,G))}`,'ivGoldBuy',{},'primary',J.wallet<0||goldCost(n,G)>have||G.phan+n>100000?' disabled':'')}${btn(`Bán · ${xu(goldWorth(sellN,G))}`,'ivGoldSell',{},'cream',!sellN?' disabled':'')}</div>
    <p class="iv-hint">1 chỉ = 10 phân. Mua bằng ví, thiếu thì lấy từ tài khoản ngân hàng; bán nhận xu vào ví. Giá mua/bán đã gồm chênh lệch 2,5% mỗi chiều.</p>
  </section>`;
}

function marketTiles(I,G,selected){
  const assets=[{id:'coin',name:'Mây Coin',emoji:'☁️',price:price(I.coin.price,I.rules)+' xu',value:I.coin.value,change:I.coin.change,locked:!I.unlocked},
    {id:'gold',name:'Vàng',emoji:'🪙',price:G?xu(G.p)+'/chỉ':'Đang tải',value:G?.value||0,change:G?.y?(G.p-G.y)*100/G.y:0}];
  return `<div class="iv-market-tabs" role="group" aria-label="Chọn tài sản">${assets.map(a=>`<button type="button" class="iv-market-tile ${selected===a.id?'selected':''}" data-action="ivMarket" data-market="${a.id}" aria-pressed="${selected===a.id}"><span>${a.emoji} ${a.name}</span><strong>${a.price}</strong><small class="${a.change>=0?'gain':'loss'}">${a.change>=0?'▲ +':'▼ '}${a.change.toLocaleString('vi-VN',{maximumFractionDigits:1})}%</small><small>${a.locked?'Mở khi ví từng có 500 xu':`Đang giữ ${xu(a.value)}`}</small></button>`).join('')}</div>`;
}

function scamCard(env,I){
  const X=I.scam;if(!X)return '';
  const flags=`<details class="iv-flags"><summary>${icon('shield',15)} Cô Lụa dặn: dấu hiệu cần để ý</summary><ul>${X.flags.map(f=>`<li>${esc(f)}</li>`).join('')}</ul></details>`;
  const top=`<div class="iv-card-top"><span class="iv-emoji" aria-hidden="true">${X.emoji}</span><div class="grow"><span class="eyebrow">Tin nhắn lạ · Lời mời đầu tư</span><h3>${esc(X.name)}</h3></div></div>`;
  if(X.stage==='offer'){
    const opts=[50,100,200].map(a=>btn(`Góp ${xu(a)}`,'ivScamJoin',{amount:a},'ghost small',a>I.wallet?' disabled':'')).join('');
    return `<section class="jr-card iv-card iv-scam" aria-label="Lời mời đầu tư">${top}
      <blockquote class="iv-pitch">“${esc(X.pitch)}”</blockquote>
      <p class="muted small">Lời mời còn ${fmt(X.days_left)} ngày.</p>${flags}
      <div class="iv-actions wrap">${opts}${btn('Không, cảm ơn','ivScamDecline',{},'cream small')}</div></section>`;
  }
  if(X.stage==='joined')return `<section class="jr-card iv-card iv-scam" aria-label="Dự án bạn đã góp tiền">${top}
      <div class="iv-kv"><span>Bạn đã góp</span><b>${xu(X.stake)}</b></div><div class="iv-kv"><span>Đã nhận “lãi”</span><b>${xu(X.paid)}</b></div>
      <button type="button" class="btn ghost small full" disabled>Rút vốn · hệ thống đang bảo trì…</button>${flags}</section>`;
  return `<section class="jr-card iv-card iv-scam quiet" aria-label="Lời mời đầu tư đã qua">${top}<p class="muted small">${X.stage==='declined'?'Bạn đã từ chối lời mời này.':'Lời mời đã hết hạn, bạn không tham gia.'}</p></section>`;
}

function logList(I){
  if(!I.log.length)return '';
  return `<h3 class="jr-sub">Nhật ký đầu tư</h3><ul class="jr-history iv-log">${I.log.slice(0,12).map(r=>`<li><span aria-hidden="true">${LOG_ICON[r.kind]||'•'}</span><span class="grow">${esc(r.text)}<small>Ngày sống ${fmt(r.day)}</small></span></li>`).join('')}</ul>`;
}

function badges(I){
  if(!I.badges.length)return '';
  return `<h3 class="jr-sub">Huy hiệu đầu tư</h3><div class="iv-badges">${I.badges.map(b=>`<div class="iv-badge"><span aria-hidden="true">${b.emoji}</span><div><b>${esc(b.name)}</b><small>${esc(b.desc)}</small></div></div>`).join('')}</div>`;
}

/** The "Đầu tư" sheet (journey home view `invest`). */
export function investView(env){
  const I=stateOf(env);
  if(!I)return head('Đầu tư','')+`<div class="sheet-body jr-body"><p class="muted">Ngân hàng phố chưa mở cửa…</p></div>`;
  const G=marketView(env).G,selected=env.ui.ivMarket==='gold'||!env.ui.ivMarket&&!I.unlocked?'gold':'coin';
  const total=I.saving.balance+I.coin.value+(G?.value||0);
  const locked=`<section class="jr-card iv-card iv-teaser"><h3>☁️ Mây Coin</h3><p>Mở khi ví của bạn từng có ${xu(I.need)}. Bạn vẫn có thể mua bán vàng ngay.</p><figure class="iv-chart">${sparkline(I.coin.prices,{R:I.rules,clock:I.coin.market_clock})}<figcaption>${I.coin.market_clock?'Giá coin chung cả phố · 10 phút/phiên':'Giá coin theo ngày sống'} · xem trước</figcaption></figure></section>`;
  return head('Đầu tư','')+`<div class="sheet-body jr-body iv">
    <section class="iv-strip" aria-live="polite"><div><small>Ví của bạn</small><b>${xu(I.wallet)}</b></div><div><small>Đang đầu tư</small><b>${xu(total)}</b></div></section>
    ${marketTiles(I,G,selected)}<p class="iv-clock">${marketClock(I.coin.market_clock||G?.market_clock)}</p>
    <div class="row spread wrap">${btn(env.ui.ivRefreshing?'Đang cập nhật…':'Cập nhật giá','ivRefresh',{},'ghost small',env.ui.ivRefreshing||env.ui.ivBusy?' disabled':'')}<small class="muted">Giá chốt khi mua / bán</small></div>
    ${env.ui.ivRefreshError?`<p class="iv-hint" role="status">${esc(env.ui.ivRefreshError)}</p>`:''}
    ${rangeControls(env)}
    <div class="iv-market-detail" aria-busy="${!!env.ui.ivBusy}"><fieldset class="iv-trading"${env.ui.ivBusy?' disabled':''}>${selected==='gold'?goldCard(env,G):I.unlocked?coinCard(env,I):locked}</fieldset></div>
    ${I.unlocked?`<details class="iv-extra"><summary>Sổ tiết kiệm & nhật ký</summary><fieldset class="iv-trading"${env.ui.ivBusy?' disabled':''}>${savingCard(env,I)}${I.scam?scamCard(env,I):''}</fieldset>${badges(I)}${logList(I)}</details>`:''}
  </div>`;
}

/** A small card for the wallet sheet: teaser while locked, entry once open. */
export function investEntry(env){
  const I=stateOf(env);if(!I)return '';
  return `<button type="button" class="jr-card iv-entry" data-action="jrView" data-view="invest"><span class="iv-emoji" aria-hidden="true">📈</span><span class="grow"><b>Đầu tư</b><small>Mây Coin ${xu(I.coin.value)} · Vàng ${xu(env.api.state.vang?.value||0)}</small></span>${icon('arrow',16)}</button>`;
}

export function investBoot(env){marketBoot(env);}

/** data-action="iv…" handler. Returns true when handled. */
export async function investAction(action,data,el,env){
  if(!action?.startsWith('iv'))return false;
  const {ui,cmd,renderSheet,confirmAction}=env,I=stateOf(env);if(!I)return true;
  const ask=(t,x,l)=>confirmAction?confirmAction(t,x,l):Promise.resolve(true);
  const trade=['ivSave','ivWithdraw','ivBuy','ivSell','ivScamJoin','ivScamDecline','ivGoldBuy','ivGoldSell'].includes(action);
  if(trade&&ui.ivBusy)return true;
  if(trade){ui.ivBusy=true;renderSheet();}
  try{
  switch(action){
    case'ivRefresh':await refreshQuotes(env);return true;
    case'ivRange':changeRange(env,data.range);return true;
    case'ivMarket':ui.ivMarket=data.market==='gold'?'gold':'coin';ui.ivPoint=null;renderSheet();return true;
    case'ivGoldQty':ui.ivGoldQty=Math.max(1,Math.min(100000,Math.floor(Number(data.n)||1)));renderSheet();return true;
    case'ivGoldStep':{const n=goldQty(env);ui.ivGoldQty=Math.max(1,Math.min(100000,n+(Number(data.d)>0?1:-1)*(n>=10?10:1)));renderSheet();return true;}
    case'ivGoldBuy':{const G=marketView(env).G;if(!G)return true;const n=goldQty(env),cost=goldCost(n,G);
      if(await (confirmAction?confirmAction(`Mua ${goldAmount(n)} vàng?`,`Giá tiệm bán ${xu(G.buy)}/chỉ.`,`Mua · ${xu(cost)}`,{cost,pocket:['wallet','account']}):Promise.resolve(true)))await cmd('jr_vang_buy',{phan:n});return true;}
    case'ivGoldSell':{const G=marketView(env).G;if(!G?.phan)return true;const n=Math.min(goldQty(env),G.phan);
      if(await ask(`Bán ${goldAmount(n)} vàng?`,'Tiền bán vàng vào ví.',`Bán · nhận ${xu(goldWorth(n,G))}`))await cmd('jr_vang_sell',n===G.phan?{all:true}:{phan:n});return true;}
    case'ivAmt':ui[data.box==='save'?'ivSave':'ivCoin']=data.v==='all'?'all':Number(data.v);renderSheet();return true;
    case'ivSave':await cmd('iv_save',payload(pick(env,'save')));return true;
    case'ivWithdraw':{const v=pick(env,'save'),S=I.saving;
      if(S.pending&&!(await ask('Rút trước kỳ hạn?',`Kỳ này bạn đã có ${xu(S.pending)} tiền lãi. Rút bây giờ thì mất khoản lãi đó (tiền gốc vẫn giữ nguyên). Còn ${fmt(S.term_left)} ngày nữa là tới ngày cộng lãi.`,'Vẫn rút')))return true;
      await cmd('iv_withdraw',payload(v));return true;}
    case'ivBuy':{const v=pick(env,'coin');
      if(v==='all'&&!(await ask('Dồn hết ví vào Mây Coin?',`Bạn sẽ mua bằng toàn bộ ${xu(I.wallet)} trong ví. Mai vẫn phải trả tiền phòng và cơm nước. Giá coin có thể giảm mạnh bất cứ ngày nào.`,'Vẫn mua')))return true;
      await cmd('iv_buy',payload(v));return true;}
    case'ivSell':await cmd('iv_sell',payload(pick(env,'coin')));return true;
    case'ivScamJoin':{const a=Number(data.amount),X=I.scam;
      if(!X||!(await ask(`Chuyển ${xu(a)} cho ${X.name}?`,'Tiền chuyển đi rồi chỉ dự án mới trả lại được. Bạn chắc chứ?','Chuyển tiền')))return true;
      await cmd('iv_scam_join',{amount:a});return true;}
    case'ivScamDecline':await cmd('iv_scam_decline',{});return true;
  }
  return false;
  }finally{if(trade){ui.ivBusy=false;renderSheet();}}
}
