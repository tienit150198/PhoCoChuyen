/** Đầu tư cá nhân: savings at the neighbourhood bank, Mây Coin (a fictional
 * crypto) and the occasional "lãi khủng" project. Markup only: every rule and
 * number lives in game/invest.py (state.invest = invest.public()).
 * Buttons use data-action="iv…" (investAction) or journey's `jrView`.
 * Design: docs/superpowers/specs/2026-09-29-invest-design.md */
import {icon,escapeHTML as esc} from '../icons.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const signed=n=>`${n>0?'+':n<0?'−':''}${fmt(Math.abs(n))} xu`;
const price=(p,R)=>(p/(R?.cent||100)).toLocaleString('vi-VN',{maximumFractionDigits:2});
const coins=(u,R)=>(u/(R?.coin||1000)).toLocaleString('vi-VN',{maximumFractionDigits:3});
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,action,data={},style='',extra='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}${extra}>${label}</button>`;
const CHIPS=[50,100,200,'all'];
const LOG_ICON={buy:'🪙',sell:'💱',save:'🏦',withdraw:'👛',interest:'🌱',pump:'📈',crash:'📉',scam_offer:'📣',scam_join:'💸',scam_pay:'💸',scam_gone:'🕳️',scam_decline:'🛡️',scam_news:'📰'};

const stateOf=env=>env.api.state?.invest;
const pick=(env,box)=>env.ui[box==='save'?'ivSave':'ivCoin']??100;
const payload=v=>v==='all'?{all:true}:{amount:Number(v)};
const label=v=>v==='all'?'Tất cả':`${fmt(v)} xu`;

function head(title,sub){
  return `<header class="sheet-head jr-head iv-head"><button type="button" class="btn ghost small jr-back" data-action="jrView" data-view="wallet" aria-label="Quay lại ví">${icon('back',18)}</button><div class="grow"><span class="eyebrow">VÍ CỦA BẠN</span><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div></header>`;
}

/** Inline SVG sparkline of the recent Mây Coin prices (oldest → newest). */
export function sparkline(prices,{cost=null,R=null,w=320,h=84}={}){
  const pts=(prices||[]).filter(Number.isFinite);
  if(pts.length<2)return '';
  const lo=Math.min(...pts,cost??Infinity),hi=Math.max(...pts,cost??-Infinity),pad=8,span=Math.max(1,hi-lo);
  const X=i=>pad+i*(w-2*pad)/(pts.length-1),Y=v=>h-pad-(v-lo)*(h-2*pad)/span;
  const line=pts.map((v,i)=>`${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(' ');
  const up=pts[pts.length-1]>=pts[0],first=pts[0],last=pts[pts.length-1];
  const hits=pts.map((v,i)=>{const x0=i?(X(i-1)+X(i))/2:0,x1=i<pts.length-1?(X(i)+X(i+1))/2:w;
    const ago=pts.length-1-i;return `<rect x="${x0.toFixed(1)}" y="0" width="${(x1-x0).toFixed(1)}" height="${h}" fill="transparent"><title>${ago?`${ago} ngày trước`:'Hôm nay'}: ${price(v,R)} xu</title></rect>`;}).join('');
  const costLine=cost!=null?`<line class="iv-cost" x1="${pad}" x2="${w-pad}" y1="${Y(cost).toFixed(1)}" y2="${Y(cost).toFixed(1)}"/>`:'';
  const summary=`Giá Mây Coin ${pts.length} ngày: từ ${price(first,R)} xu tới ${price(last,R)} xu, thấp nhất ${price(Math.min(...pts),R)}, cao nhất ${price(Math.max(...pts),R)}.`;
  return `<svg class="iv-spark ${up?'up':'down'}" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(summary)}">
    <path class="iv-area" d="M${X(0).toFixed(1)},${h-pad} L${line.replace(/ /g,' L')} L${X(pts.length-1).toFixed(1)},${h-pad} Z"/>
    ${costLine}<polyline class="iv-line" points="${line}"/>
    <circle class="iv-dot" cx="${X(pts.length-1).toFixed(1)}" cy="${Y(last).toFixed(1)}" r="4.5"/>${hits}</svg>`;
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
    <div class="iv-card-top"><span class="iv-emoji" aria-hidden="true">🏦</span><div class="grow"><span class="eyebrow">Ngân hàng phố</span><h3 id="ivBankT">Gửi tiết kiệm</h3><p class="muted small">Lãi ${rate}/ngày, cộng vào sổ mỗi ${R.term} ngày. Không bao giờ lỗ vốn.</p>${S.earned?`<span class="tag green iv-earned">Đã nhận lãi ${xu(S.earned)}</span>`:''}</div></div>
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
      <div class="iv-kv"><span>Trị giá hôm nay</span><b>${xu(C.value)}</b></div>
      <div class="iv-kv"><span>Tiền đã bỏ vào (gồm phí)</span><b>${xu(C.basis)}</b></div>
      <div class="iv-kv iv-pnl ${C.unrealised>=0?'gain':'loss'}"><span>${C.unrealised>=0?'Lãi tạm tính':'Lỗ tạm tính'}</span><b>${signed(C.unrealised)}</b></div></div>`
    :`<p class="muted small">Bạn chưa có Mây Coin.</p>`;
  const buyAmt=v==='all'?I.wallet:amt,sellAmt=v==='all'?C.value:amt;
  const preview=buyAmt>=R.min_trade?`Mua ${xu(buyAmt)}: phí ${R.fee_pct}% = ${xu(fee(buyAmt))}.`:`Lệnh ít nhất ${xu(R.min_trade)}.`;
  return `<section class="jr-card iv-card iv-coin" aria-labelledby="ivCoinT">
    <div class="iv-card-top"><span class="iv-emoji" aria-hidden="true">☁️</span><div class="grow"><span class="eyebrow">Tiền ảo · chỉ có trong game</span><h3 id="ivCoinT">Mây Coin</h3></div>
      <div class="iv-price"><strong>${price(C.price,R)} xu</strong><span class="iv-change ${dir}">${dir==='up'?'▲':dir==='down'?'▼':'•'} ${ch>0?'+':''}${ch}% <small>hôm nay</small></span></div></div>
    <figure class="iv-chart">${sparkline(C.prices,{cost,R})}<figcaption>${C.prices.length} ngày gần đây${cost!=null?` · <span class="iv-cost-key" aria-hidden="true"></span> giá vốn của bạn ${price(cost,R)} xu`:''}</figcaption></figure>
    ${hold}
    ${C.realised||C.fees?`<div class="iv-kv small"><span>Đã chốt lãi/lỗ · phí đã trả</span><b class="${C.realised>=0?'gain':'loss'}">${signed(C.realised)} · ${xu(C.fees)}</b></div>`:''}
    ${chips(env,'coin')}
    <div class="iv-actions">${btn(`Mua ${v==='all'?'hết ví':label(v)}`,'ivBuy',{},'primary',buyAmt<R.min_trade||buyAmt>I.wallet?' disabled':'')}${btn(`Bán ${v==='all'?'hết coin':label(v)}`,'ivSell',{},'cream',!C.units||(v!=='all'&&(sellAmt>C.value||sellAmt<R.min_trade))?' disabled':'')}</div>
    <p class="iv-hint">${esc(preview)}</p>
  </section>`;
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

function teaser(env,I){
  const pct=Math.min(100,Math.round(Math.max(0,I.max_wallet)*100/I.need));
  return head('Đầu tư','')+`<div class="sheet-body jr-body iv">
    <section class="jr-card iv-card iv-teaser"><div class="iv-card-top"><span class="iv-emoji" aria-hidden="true">🔒</span><div class="grow"><span class="eyebrow">Sắp mở</span><h3>Khi ví từng có ${xu(I.need)}</h3></div></div>
      <div class="jr-bar iv-bar" role="progressbar" aria-label="Tiến tới mở mục đầu tư" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><i style="width:${pct}%"></i></div>
      <p class="small iv-progress"><b>${xu(Math.min(I.max_wallet,I.need))}</b> / ${xu(I.need)} · số dư cao nhất từng có</p>
      <figure class="iv-chart preview">${sparkline(I.coin.prices,{R:I.rules})}<figcaption>Mây Coin ${I.coin.prices.length} ngày qua · xem trước</figcaption></figure></section></div>`;
}

/** The "Đầu tư" sheet (journey home view `invest`). */
export function investView(env){
  const I=stateOf(env);
  if(!I)return head('Đầu tư','')+`<div class="sheet-body jr-body"><p class="muted">Ngân hàng phố chưa mở cửa…</p></div>`;
  if(!I.unlocked)return teaser(env,I);
  const total=I.saving.balance+I.coin.value;
  return head('Đầu tư','')+`<div class="sheet-body jr-body iv">
    <section class="iv-strip" aria-live="polite"><div><small>Ví của bạn</small><b>${xu(I.wallet)}</b></div><div><small>Đang đầu tư</small><b>${xu(total)}</b></div></section>
    <div class="notice amber iv-risk">${icon('alert',17)}<div><b>Tiền ảo có thể mất trắng. Chỉ dùng tiền nhàn rỗi.</b><p>Tiền phòng, cơm nước vẫn trừ vào ví mỗi ngày. Nhớ chừa lại nhé.</p></div></div>
    ${I.scam?.stage==='offer'?scamCard(env,I):''}
    <div class="iv-grid">${savingCard(env,I)}${coinCard(env,I)}</div>
    ${I.scam&&I.scam.stage!=='offer'?scamCard(env,I):''}
    ${badges(I)}${logList(I)}
  </div>`;
}

/** A small card for the wallet sheet: teaser while locked, entry once open. */
export function investEntry(env){
  const I=stateOf(env);if(!I)return '';
  if(!I.unlocked){
    const pct=Math.min(100,Math.round(Math.max(0,I.max_wallet)*100/I.need));
    return `<button type="button" class="jr-card iv-entry locked" data-action="jrView" data-view="invest"><span class="iv-emoji" aria-hidden="true">🔒</span><span class="grow"><b>Đầu tư · mở khi ví từng có ${xu(I.need)}</b><span class="jr-bar iv-bar" aria-hidden="true"><i style="width:${pct}%"></i></span></span>${icon('lock',16)}</button>`;
  }
  const offer=I.scam?.stage==='offer';
  return `<button type="button" class="jr-card iv-entry" data-action="jrView" data-view="invest"><span class="iv-emoji" aria-hidden="true">📈</span><span class="grow"><b>Đầu tư</b><small>Tiết kiệm ${xu(I.saving.balance)} · Mây Coin ${xu(I.coin.value)}</small></span>${offer?'<span class="tag amber">1 lời mời mới</span>':''}${icon('arrow',16)}</button>`;
}

/** data-action="iv…" handler. Returns true when handled. */
export async function investAction(action,data,el,env){
  if(!action?.startsWith('iv'))return false;
  const {ui,cmd,renderSheet,confirmAction}=env,I=stateOf(env);if(!I)return true;
  const ask=(t,x,l)=>confirmAction?confirmAction(t,x,l):Promise.resolve(true);
  switch(action){
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
}
