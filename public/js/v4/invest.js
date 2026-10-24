/** Đầu tư cá nhân: gold, savings at the neighbourhood bank, Mây Coin (a fictional
 * crypto) and the occasional "lãi khủng" project. Markup only: every rule and
 * number lives in game/invest.py (state.invest = invest.public()).
 * Buttons use data-action="iv…" (investAction) or journey's `jrView`.
 * Design: docs/superpowers/specs/2026-09-29-invest-design.md */
import {icon,escapeHTML as esc} from '../icons.js';
import {marketBoot,refreshQuotes,changeRange,changeAsset,marketView} from './invest-market.js';
import {marketChart,rangeControls} from './invest-chart.js';
// Typed numbers in the − N + steppers (owner 07/10: "cho nhập số nhé").
import {qtyBox,QTY} from '../qty-input.js';

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
const BOX={save:'ivSave',coin:'ivCoin',san:'svAmt'};
const pick=(env,box)=>env.ui[BOX[box]||'ivCoin']??100;
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
    return `<button type="button" class="chip ${on?'selected':''}" data-action="ivAmt" data-box="${box}" data-v="${v}" aria-pressed="${on}"${v!=='all'&&limit!=null&&v>limit?' data-over="1"':''}>${label(v)}</button>`;}).join('')}`+
    // Any other amount, typed (owner 07/10): the chips stay for the usual ones.
    `<label class="iv-typed">${qtyBox({value:cur==='all'?'':cur,min:1,max:1e9,money:true,label:'Số xu khác',placeholder:'Số khác',live:true,go:`data-action="ivAmt" data-box="${box}" data-v="${QTY}"`})}<small>xu</small></label></div>`;
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
const MAX_PHAN=100000;   // game/vang.py MAX_PHAN: 10 000 chỉ a buy, and held at most
const goldClamp=n=>Math.max(1,Math.min(MAX_PHAN,Math.floor(Number(n)||1)));
const goldQty=env=>goldClamp(env.ui.ivGoldQty??10);   // 1 chỉ until the player picks
/** The most `have` xu buys (cost_of rounds up per phân: n × buy ≤ have × 10), within what the shop keeps. */
const goldMaxBuy=(G,have)=>Math.max(0,Math.min(MAX_PHAN-(G.phan||0),Math.floor(Math.max(0,have)*10/Math.max(1,G.buy))));
const goldCost=(n,G)=>Math.ceil(n*G.buy/10);
const goldWorth=(n,G)=>Math.floor(n*G.sell/10);
function goldCard(env,G){
  if(!G)return '<section class="jr-card iv-card"><p>Chưa tải được giá vàng. Mở lại mục Đầu tư để thử nhé.</p></section>';
  const n=goldQty(env),sellN=Math.min(n,G.phan),gain=G.value-G.cost;
  const change=G.y?(G.p-G.y)*100/G.y:0;
  const J=env.api.state.journey||{},have=Math.max(0,J.wallet||0)+(J.bank?.balance||0);
  const cost=G.phan?G.cost*10/G.phan:null;
  const maxBuy=J.wallet<0?0:goldMaxBuy(G,have);
  return `<section class="jr-card iv-card iv-gold" aria-labelledby="ivGoldT">
    <div class="iv-card-top"><span class="iv-emoji" aria-hidden="true">🪙</span><div class="grow"><span class="eyebrow">Tiệm vàng Kim Phát</span><h3 id="ivGoldT">Vàng</h3></div><div class="iv-price"><strong>${xu(G.p)}/chỉ</strong><span class="iv-change ${change>=0?'up':'down'}">${change>=0?'▲ +':'▼ '}${change.toLocaleString('vi-VN',{maximumFractionDigits:1})}% <small>${G.market_clock?'so với phiên trước':'hôm nay'}</small></span></div></div>
    ${marketNews(G.market_news|| (G.news?{title:G.news,active:true,direction:change>=0?'up':'down'}:null))}
    ${marketChart(env,'gold',G.hist,G.market_clock)}
    <div class="iv-hold"><div class="iv-kv"><span>Đang giữ</span><b>${goldAmount(G.phan)}</b></div><div class="iv-kv"><span>Bán ngay được</span><b>${xu(G.value)}</b></div><div class="iv-kv"><span>Tiền đã bỏ vào</span><b>${xu(G.cost)}</b></div><div class="iv-kv iv-pnl ${gain>=0?'gain':'loss'}"><span>${gain>=0?'Lãi tạm tính':'Lỗ tạm tính'}</span><b>${signed(gain)}</b></div></div>
    <p class="iv-hint">Tiệm bán ${xu(G.buy)}/chỉ · mua lại ${xu(G.sell)}/chỉ.${G.market_clock?' Biến động so với phiên trước. Giá được chốt khi máy chủ nhận lệnh.':''}</p>
    <div class="iv-gold-quantity" role="group" aria-label="Số vàng giao dịch">${btn('−','ivGoldStep',{d:-1},'cream',' aria-label="Bớt vàng"')}<label class="iv-gold-typed">${qtyBox({value:Math.floor(n/10),min:0,max:MAX_PHAN/10,label:'Số chỉ vàng',go:`data-action="ivGoldQty" data-chi="${QTY}"`,live:true})}<small>chỉ</small></label><label class="iv-gold-typed">${qtyBox({value:n%10,min:0,max:9,label:'Số phân vàng lẻ',go:`data-action="ivGoldQty" data-phan="${QTY}"`,live:true})}<small>phân</small></label>${btn('+','ivGoldStep',{d:1},'cream',' aria-label="Thêm vàng"')}</div>
    <div class="iv-gold-chips">${[[10,'1 chỉ'],[50,'5 chỉ'],[100,'10 chỉ']].map(([q,label])=>btn(label,'ivGoldQty',{n:q},q===n?'primary small':'cream small',` aria-pressed="${q===n}"`)).join('')}${maxBuy>0?btn(`Mua tối đa · ${goldAmount(maxBuy)}`,'ivGoldQty',{n:maxBuy},maxBuy===n?'primary small':'cream small',` aria-pressed="${maxBuy===n}"`):''}${G.phan?btn(`Cả ${goldAmount(G.phan)} đang giữ`,'ivGoldQty',{n:G.phan},G.phan===n?'primary small':'cream small',` aria-pressed="${G.phan===n}"`):''}</div>
    <div class="iv-actions">${btn(`Mua · ${xu(goldCost(n,G))}`,'ivGoldBuy',{},'primary',J.wallet<0||goldCost(n,G)>have||G.phan+n>MAX_PHAN?' disabled':'')}${btn(`Bán · ${xu(goldWorth(sellN,G))}`,'ivGoldSell',{},'cream',!sellN?' disabled':'')}</div>
    <p class="iv-hint">1 chỉ = 10 phân. Mua bằng ví, thiếu thì lấy từ tài khoản ngân hàng; bán nhận xu vào ví. Giá mua/bán đã gồm chênh lệch 2,5% mỗi chiều.</p>
  </section>`;
}

function marketTiles(I,G,selected,S,B){
  const assets=[{id:'coin',name:'Mây Coin',emoji:'☁️',price:price(I.coin.price,I.rules)+' xu',value:I.coin.value,change:I.coin.change,locked:!I.unlocked},
    {id:'gold',name:'Vàng',emoji:'🪙',price:G?xu(G.p)+'/chỉ':'Đang tải',value:G?.value||0,change:G?.y?(G.p-G.y)*100/G.y:0}];
  const tile=a=>`<button type="button" class="iv-market-tile ${selected===a.id?'selected':''}" data-action="ivMarket" data-market="${a.id}" aria-pressed="${selected===a.id}"><span>${a.emoji} ${a.name}</span><strong>${a.price}</strong><small class="${a.change>=0?'gain':'loss'}">${a.change>=0?'▲ +':'▼ '}${a.change.toLocaleString('vi-VN',{maximumFractionDigits:1})}%</small><small>${a.locked?'Mở khi ví từng có 500 xu':`Đang giữ ${xu(a.value)}`}</small></button>`;
  const on=S&&(selected==='san'||S.assets.some(a=>a.id===selected));
  const san=S?`<button type="button" class="iv-market-tile sv-tile ${on?'selected':''}" data-action="ivMarket" data-market="san" aria-pressed="${!!on}"><span>🎢 Sàn Phố</span><strong>${S.assets.length} mã</strong><small>Coin & cổ phiếu</small><small>Đang giữ ${xu(sanTotal(S,B))}</small></button>`:'';
  return `<div class="iv-market-tabs${san?' three':''}" role="group" aria-label="Chọn tài sản">${assets.map(tile).join('')}${san}</div>`;
}
const sanTotal=(S,B)=>S?Object.entries(S.hold).reduce((t,[id,h])=>t+(B?.assets?.[id]?sanVal(h,B.assets[id],S.rules):h.value||0),0):0;

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


/* ------------------------------------------------------------------ 🎢 Sàn Phố (game/san.py, game/market_wild.py) */
const pct=n=>`${n>0?'+':n<0?'−':''}${Math.abs(Number(n)||0).toLocaleString('vi-VN',{maximumFractionDigits:1})}%`;
const sanOf=env=>env.api.state?.san||null;
/** Units in the board's split terms: a split (1→10) or merge (10→1) since the state was read keeps the value. */
const uOf=(h,q)=>{const d=(h?.e||0)-(q?.e??h?.e??0);return !h?0:d>0?h.units*10**d:d<0?Math.max(1,Math.floor(h.units/10**-d)):h.units;};
const sanVal=(h,q,R)=>h&&!h.dead&&q?.price>0?Math.floor(uOf(h,q)*q.price/(R.coin*R.cent)):0;
/** Big moves flash once: the rows whose price changed at the newest tick, for 2,5 s after it arrived. */
function flashOf(env,B){
  if(!B?.assets)return {};
  const ui=env.ui;
  if(ui.svTick!==B.tick){
    const seen=ui.svSeen||{},f={};
    for(const [id,a] of Object.entries(B.assets))if(seen[id]!=null&&a.price!==seen[id])f[id]=a.price>seen[id]?'up':'down';
    ui.svSeen=Object.fromEntries(Object.entries(B.assets).map(([id,a])=>[id,a.price]));
    ui.svFlash=f;ui.svFlashAt=Date.now();ui.svTick=B.tick;
  }
  return Date.now()-(ui.svFlashAt||0)<2500?ui.svFlash||{}:{};
}
function miniSpark(points){
  const pts=(points||[]).filter(v=>v>0);if(pts.length<2)return '<span class="sv-spark"></span>';
  const lo=Math.min(...pts),hi=Math.max(...pts),w=56,h=22,span=Math.max(1,hi-lo);
  const line=pts.map((v,i)=>`${(i*w/(pts.length-1)).toFixed(1)},${(h-2-(v-lo)*(h-4)/span).toFixed(1)}`).join(' ');
  return `<svg class="sv-spark ${pts.at(-1)>=pts[0]?'up':'down'}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${line}"/></svg>`;
}
function sanTicker(B){
  const rows=(B?.ticker||[]).slice(0,3);
  if(!rows.length)return '';
  return `<div class="sv-ticker" role="status" aria-label="Tin nóng thị trường">${rows.map(r=>`<p class="${r.sign>0?'up':r.sign<0?'down':''}"><span aria-hidden="true">${r.sign>0?'📈':r.sign<0?'📉':'📰'}</span> ${esc(r.text)}${r.kind!=='mover'&&r.move?` <b>${pct(r.move)}</b>`:''}</p>`).join('')}</div>`;
}
function sanList(env,S,B){
  const tab=env.ui.svTab==='stock'?'stock':'coin',flash=flashOf(env,B),R=S.rules;
  const rows=S.assets.filter(a=>a.kind===tab).map(a=>{
    const q=B?.assets?.[a.id],h=S.hold[a.id],p=q?.price,dead=!!q?.delisted,ch=q?.ch1h??0,on=env.ui.ivMarket===a.id;
    const held=h?(h.dead?' · đã mất':` · giữ ${xu(sanVal(h,q,R))}`):'';
    return `<button type="button" class="sv-row${flash[a.id]?' flash-'+flash[a.id]:''}${on?' selected':''}${a.open?'':' locked'}" data-action="ivMarket" data-market="${a.id}" aria-pressed="${on}">
      <span class="sv-emo" aria-hidden="true">${a.emoji}</span>
      <span class="sv-name"><b>${esc(a.name)}</b><small>${esc(a.sym)}${a.risky?' · ⚠️':''}${a.open?held:` · 🔒 ${fmt(a.unlock)} xu`}</small></span>
      ${miniSpark(q?.spark)}
      <span class="sv-q"><b>${dead?'Hủy niêm yết':p!=null?price(p,R)+' xu':'…'}</b><small class="${ch>0?'gain':ch<0?'loss':''}">${dead?'':pct(ch)+' 1 giờ'}</small></span></button>`;}).join('');
  return `<section class="sv" aria-labelledby="svT"><div class="sv-head"><h3 id="svT">🎢 Sàn Phố</h3><nav class="sv-tabs" aria-label="Loại tài sản">${[['coin','Coin'],['stock','Cổ phiếu']].map(([k,l])=>`<button type="button" data-action="ivSanTab" data-tab="${k}" aria-pressed="${tab===k}">${l}</button>`).join('')}</nav></div>
    ${sanTicker(B)}
    <div class="sv-list">${rows}</div>
    <p class="iv-hint">Giá chung cả phố, đổi mỗi 10 phút, lên xuống rất mạnh. Không có cách chơi nào chắc thắng: chỉ dùng tiền nhàn rỗi.</p></section>`;
}
function sanCard(env,S,B,id){
  const a=S.assets.find(x=>x.id===id);if(!a)return '';
  const q=B?.assets?.[id],h=S.hold[id],R=S.rules,J=env.api.state.journey||{},wallet=J.wallet||0;
  const p=q?.price??0,dead=!!q?.delisted,ch=q?.ch1h??0,unit=a.kind==='stock'?'cp':a.sym;
  const v=pick(env,'san'),fee=x=>Math.max(1,Math.ceil(x*a.fee/100));
  const value=sanVal(h,q,R),pnl=value-(h?.basis||0);
  const was=h&&!h.dead?Math.round((h.peak||0)*10**((q?.e??h.e??0)-(h.e||0))):0,peak=Math.max(was,h&&!h.dead?p:0);
  const peakVal=h?Math.floor(uOf(h,q)*peak/(R.coin*R.cent)):0,peakNet=peakVal>1?peakVal-fee(peakVal):0;
  const regret=h&&!h.dead&&peakNet>h.basis&&peakVal*100>=value*110;
  const buyAmt=v==='all'?wallet:Number(v),sellAmt=v==='all'?value:Number(v);
  const news=q?.news?.active?`<aside class="iv-news ${q.news.direction==='down'?'down':'up'}"><small>📰 Tin trên sàn</small><b>${esc(q.news.title)}</b>${q.news.move?`<span>Giá phản ứng ${pct(q.news.move)}</span>`:''}</aside>`:'';
  const hold=h?(h.dead?`<p class="sv-dead">🕳️ ${esc(a.name)} đã bị hủy niêm yết: ${xu(h.basis)} bạn bỏ vào đã mất.</p>`
    :`<div class="iv-hold"><div class="iv-kv"><span>Đang giữ</span><b>${coins(uOf(h,q),R)} ${esc(unit)}</b></div><div class="iv-kv"><span>Trị giá hiện tại</span><b>${xu(value)}</b></div><div class="iv-kv"><span>Tiền đã bỏ vào (gồm phí)</span><b>${xu(h.basis)}</b></div><div class="iv-kv iv-pnl ${pnl>=0?'gain':'loss'}"><span>${pnl>=0?'Lãi tạm tính':'Lỗ tạm tính'}</span><b>${signed(pnl)}</b></div></div>`
      +(regret?`<p class="sv-regret">😢 Nếu bán lúc đỉnh (${price(peak,R)} xu) bạn đã có <b>${xu(peakNet)}</b>.</p>`:''))
    :`<p class="muted small">Bạn chưa có ${esc(a.name)}.</p>`;
  const locked=!a.open?`<p class="iv-hint">🔒 Mở khi ví của bạn từng có ${xu(a.unlock)}.</p>`:!S.open?`<p class="iv-hint">Sàn chưa mở cửa.</p>`:'';
  const canTrade=a.open&&S.open&&!dead;
  return `<section class="jr-card iv-card iv-coin sv-card${a.risky?' risky':''}" aria-labelledby="svCardT">
    <div class="iv-card-top"><span class="iv-emoji" aria-hidden="true">${a.emoji}</span><div class="grow"><span class="eyebrow">${a.kind==='stock'?'Cổ phiếu':'Coin'} · ${esc(a.sector)}${q?.regime?` · ${esc(q.regime)}`:''}</span><h3 id="svCardT">${esc(a.name)} <small>${esc(a.sym)}</small></h3></div>
      <div class="iv-price"><strong>${dead?'0 xu':price(p,R)+' xu'}</strong><span class="iv-change ${ch>0?'up':ch<0?'down':'flat'}">${ch>0?'▲':ch<0?'▼':'•'} ${pct(ch)} <small>1 giờ · ${pct(q?.ch24h??0)} 24 giờ</small></span></div></div>
    ${a.risky?`<p class="sv-warn">${esc(a.desc)}</p>`:`<p class="muted small">${esc(a.desc)}</p>`}
    ${dead?`<p class="sv-dead">🕳️ Đang bị hủy niêm yết. Coin sẽ niêm yết lại sau một ngày, giá khởi điểm.</p>`:''}
    ${news}
    ${marketChart(env,id,q?.spark||[],q?{timestamps:(q.spark||[]).map((_,i,s)=>B.as_of-(s.length-1-i)*3600)}:null,R.cent,{name:a.name,price:p,as_of:B?.as_of})}
    ${hold}${locked}
    ${canTrade?chips(env,'san'):''}
    ${canTrade?`<div class="iv-actions">${btn(`Mua ${v==='all'?'hết ví':label(v)}`,'ivSanBuy',{a:id},'primary',buyAmt<R.min_trade||buyAmt>wallet?' disabled':'')}${btn(`Bán ${v==='all'?'hết':label(v)}`,'ivSanSell',{a:id},'cream',!h||h.dead||(v!=='all'&&(sellAmt>value||sellAmt<R.min_trade))?' disabled':'')}</div>
    <p class="iv-hint">Phí ${a.fee}% mỗi lần mua và bán${buyAmt>=R.min_trade?` (mua ${xu(buyAmt)}: phí ${xu(fee(buyAmt))})`:''}. Giá chốt khi máy chủ nhận lệnh.</p>`:''}
  </section>`;
}

/** The "Đầu tư" sheet (journey home view `invest`). */
export function investView(env){
  const I=stateOf(env);
  if(!I)return head('Đầu tư','')+`<div class="sheet-body jr-body"><p class="muted">Ngân hàng phố chưa mở cửa…</p></div>`;
  const {G,B}=marketView(env),S=sanOf(env),sv=S&&(env.ui.ivMarket==='san'||S.assets.some(a=>a.id===env.ui.ivMarket));
  const selected=sv?env.ui.ivMarket:env.ui.ivMarket==='gold'||!env.ui.ivMarket&&!I.unlocked?'gold':'coin';
  const total=I.saving.balance+I.coin.value+(G?.value||0)+sanTotal(S,B);
  const locked=`<section class="jr-card iv-card iv-teaser"><h3>☁️ Mây Coin</h3><p>Mở khi ví của bạn từng có ${xu(I.need)}. Bạn vẫn có thể mua bán vàng ngay.</p><figure class="iv-chart">${sparkline(I.coin.prices,{R:I.rules,clock:I.coin.market_clock})}<figcaption>${I.coin.market_clock?'Giá coin chung cả phố · 10 phút/phiên':'Giá coin theo ngày sống'} · xem trước</figcaption></figure></section>`;
  return head('Đầu tư','')+`<div class="sheet-body jr-body iv">
    <section class="iv-strip" aria-live="polite"><div><small>Ví của bạn</small><b>${xu(I.wallet)}</b></div><div><small>Đang đầu tư</small><b>${xu(total)}</b></div></section>
    ${marketTiles(I,G,selected,S,B)}<p class="iv-clock">${marketClock(I.coin.market_clock||G?.market_clock)}</p>
    <div class="row spread wrap">${btn(env.ui.ivRefreshing?'Đang cập nhật…':'Cập nhật giá','ivRefresh',{},'ghost small',env.ui.ivRefreshing||env.ui.ivBusy?' disabled':'')}<small class="muted">Giá chốt khi mua / bán</small></div>
    ${env.ui.ivRefreshError?`<p class="iv-hint" role="status">${esc(env.ui.ivRefreshError)}</p>`:''}
    ${selected==='san'?'':rangeControls(env)}
    <div class="iv-market-detail" aria-busy="${!!env.ui.ivBusy}"><fieldset class="iv-trading"${env.ui.ivBusy?' disabled':''}>${sv?(selected==='san'?'':sanCard(env,S,B,selected))+sanList(env,S,B):selected==='gold'?goldCard(env,G):I.unlocked?coinCard(env,I):locked}</fieldset></div>
    ${I.unlocked?`<details class="iv-extra"><summary>Sổ tiết kiệm & nhật ký</summary><fieldset class="iv-trading"${env.ui.ivBusy?' disabled':''}>${savingCard(env,I)}${I.scam?scamCard(env,I):''}</fieldset>${badges(I)}${logList(I)}</details>`:''}
  </div>`;
}

/** A small card for the wallet sheet: teaser while locked, entry once open. */
export function investEntry(env){
  const I=stateOf(env);if(!I)return '';
  const S=sanOf(env),hold=S?sanTotal(S,marketView(env).B):0;
  return `<button type="button" class="jr-card iv-entry" data-action="jrView" data-view="invest"><span class="iv-emoji" aria-hidden="true">📈</span><span class="grow"><b>Đầu tư</b><small>Mây Coin ${xu(I.coin.value)} · Vàng ${xu(env.api.state.vang?.value||0)}${hold?` · Sàn Phố ${xu(hold)}`:''}</small></span>${icon('arrow',16)}</button>`;
}

export function investBoot(env){marketBoot(env);}

/** data-action="iv…" handler. Returns true when handled. */
export async function investAction(action,data,el,env){
  if(!action?.startsWith('iv'))return false;
  const {ui,cmd,renderSheet,confirmAction}=env,I=stateOf(env);if(!I)return true;
  const ask=(t,x,l)=>confirmAction?confirmAction(t,x,l):Promise.resolve(true);
  const trade=['ivSave','ivWithdraw','ivBuy','ivSell','ivScamJoin','ivScamDecline','ivGoldBuy','ivGoldSell','ivSanBuy','ivSanSell'].includes(action);
  if(trade&&ui.ivBusy)return true;
  if(trade){ui.ivBusy=true;renderSheet();}
  try{
  switch(action){
    case'ivRefresh':await refreshQuotes(env);return true;
    case'ivRange':changeRange(env,data.range);return true;
    case'ivMarket':{const S=sanOf(env),m=data.market;
      changeAsset(env,m==='gold'||m==='coin'?m:S&&(m==='san'||S.assets.some(a=>a.id===m))?m:'coin');return true;}
    case'ivSanTab':ui.svTab=data.tab==='stock'?'stock':'coin';renderSheet();return true;
    case'ivSanBuy':{const S=sanOf(env),a=S?.assets.find(x=>x.id===data.a),v=pick(env,'san');if(!a)return true;
      if((a.risky||v==='all')&&!(await ask(`Mua ${a.name}?`,a.risky?a.desc:`Bạn sẽ mua bằng toàn bộ ${xu(I.wallet)} trong ví. Giá có thể rơi rất mạnh bất cứ lúc nào.`,'Vẫn mua')))return true;
      await cmd('jr_san_buy',{a:a.id,...payload(v)});return true;}
    case'ivSanSell':{const S=sanOf(env),a=S?.assets.find(x=>x.id===data.a);if(!a)return true;
      await cmd('jr_san_sell',{a:a.id,...payload(pick(env,'san'))});return true;}
    // A whole number of phân (a chip), or one part typed: the chỉ box keeps the odd phân, the phân box keeps the chỉ.
    case'ivGoldQty':{const n=goldQty(env),chi=Math.floor(Number(data.chi)),phan=Math.floor(Number(data.phan));
      ui.ivGoldQty=goldClamp(data.chi!=null&&Number.isFinite(chi)?Math.max(0,chi)*10+n%10:data.phan!=null&&Number.isFinite(phan)?Math.floor(n/10)*10+Math.max(0,Math.min(9,phan)):data.n);renderSheet();return true;}
    case'ivGoldStep':{const n=goldQty(env);ui.ivGoldQty=goldClamp(n+(Number(data.d)>0?1:-1)*(n>=10?10:1));renderSheet();return true;}
    case'ivGoldBuy':{const G=marketView(env).G;if(!G)return true;const n=goldQty(env),cost=goldCost(n,G);
      if(await (confirmAction?confirmAction(`Mua ${goldAmount(n)} vàng?`,`Giá tiệm bán ${xu(G.buy)}/chỉ.`,`Mua · ${xu(cost)}`,{cost,pocket:['wallet','account']}):Promise.resolve(true)))await cmd('jr_vang_buy',{phan:n});return true;}
    case'ivGoldSell':{const G=marketView(env).G;if(!G?.phan)return true;const n=Math.min(goldQty(env),G.phan);
      if(await ask(`Bán ${goldAmount(n)} vàng?`,'Tiền bán vàng vào ví.',`Bán · nhận ${xu(goldWorth(n,G))}`))await cmd('jr_vang_sell',n===G.phan?{all:true}:{phan:n});return true;}
    case'ivAmt':ui[BOX[data.box]||'ivCoin']=data.v==='all'?'all':Number(data.v);renderSheet();return true;
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
