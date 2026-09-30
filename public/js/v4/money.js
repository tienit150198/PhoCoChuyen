/** 💰 Money in sight while spending (v0.9.5, player feedback: "muốn mua đồ mà không biết còn bao nhiêu
 * tiền, phải ra màn hình chính xem").
 *
 * One small chip, "👛 Ví 1.234 xu · 🏪 Quỹ tiệm 560 xu", hangs on the bottom edge of the header of whatever
 * sheet the player spends or moves money in (stock room, work screens, shop, bank, rings, classes…): it
 * adds no height to the header and is redrawn after every command. The same line sits in every confirm
 * dialog that talks money, with "còn thiếu N xu" when the price is over the balance it comes out of.
 *
 * Which pockets a sheet shows is decided in ONE place, the `scope(dialog)` callback app.js passes to
 * moneyBoot: null (no chip), {fund:null} (the wallet only) or {fund:careerId} (wallet + that place's fund).
 * The pure helpers below (no DOM) are unit-tested by tests/money_chip.mjs. */
import {asset} from '../assets.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

/** Big sums shortened on phones so the chip stays one line: 125.400 → 125,4k, 3.373.500 → 3,37tr. */
export function shortXu(n,phone=false){
  const v=Number(n||0),a=Math.abs(v);
  if(!phone||a<1e5)return `${fmt(v)} xu`;
  return a>=999950?`${(v/1e6).toLocaleString('vi-VN',{maximumFractionDigits:2})}tr xu`:`${(v/1e3).toLocaleString('vi-VN',{maximumFractionDigits:1})}k xu`;
}

/** What players call the workplace's money: the place's own word when it is a fund ("Quỹ lớp",
 * "Quỹ bộ phận"…), otherwise "Quỹ tiệm" (never "Ví …", which is the player's own wallet). */
export function fundLabel(till){
  const t=String(till||'').trim();
  if(/^Quỹ\s+\S/.test(t)||t==='Túi tiền lẻ')return t;
  return 'Quỹ tiệm';
}

/** The balances a scope shows, from the game state: {wallet, fund, fundName}; null when nothing to show. */
export function balances(state,scope,till=''){
  if(!state||!scope)return null;
  const j=state.journey,c=scope.fund?state.careers?.[scope.fund]:null;
  // Free play (no story) has no personal wallet: every place keeps its own fund.
  const wallet=j&&j.story!==false&&Number.isFinite(Number(j.wallet))?Number(j.wallet):null;
  const fund=c&&Number.isFinite(Number(c.money))?Number(c.money):null;
  if(wallet==null&&fund==null)return null;
  return {wallet,fund,fundName:fundLabel(till)};
}

/** The chip's inner markup (also the confirm dialog line). */
export function chipHTML(b,{phone=false}={}){
  if(!b)return '';
  const part=(ico,label,v,cls)=>`<span class="mn-part ${cls}${v<0?' neg':''}"><span aria-hidden="true">${ico}</span> ${esc(label)} <b>${esc(v<0?'−'+shortXu(-v,phone):shortXu(v,phone))}</b></span>`;
  const bits=[];
  if(b.wallet!=null)bits.push(part('👛','Ví',b.wallet,'mn-wallet'));
  if(b.fund!=null)bits.push(part('🏪',b.fundName||'Quỹ tiệm',b.fund,'mn-fund'));
  return bits.join('<span class="mn-sep" aria-hidden="true">·</span>');
}
/** Plain text of the same line (tests, screen-reader labels). */
export function chipText(b){
  if(!b)return '';
  const bits=[];
  if(b.wallet!=null)bits.push(`Ví ${b.wallet<0?'âm '+fmt(-b.wallet):fmt(b.wallet)} xu`);
  if(b.fund!=null)bits.push(`${b.fundName||'Quỹ tiệm'} ${fmt(b.fund)} xu`);
  return bits.join(', ');
}

/** The one price in a text ("… · 45 xu?", "1.200 xu"), or null when there is none or several. */
export function priceIn(...texts){
  const found=new Set();
  for(const t of texts)for(const m of String(t||'').matchAll(/(\d{1,3}(?:\.\d{3})+|\d+)\s*xu\b/gu))found.add(Number(m[1].replace(/\./g,'')));
  return found.size===1?[...found][0]:null;
}
/** Spending words a confirm starts with (title, question or button). Earning or moving money out of an
 * account ("Rút", "Thu", "Bán", "Nhận", "Trả máy"…) is never read as a price. */
const SPEND=/^(?:mua|nhập|đặt|thuê|thanh toán|nộp|đóng|chi|thay|sắm|cọc|tặng|đăng ký)(?=\s|$)/iu;
const lead=t=>String(t||'').replace(/^[^\p{L}\d]+/u,'').trim();
export function isSpend(...texts){return texts.some(t=>SPEND.test(lead(t)));}

/** How much is missing to pay `cost` out of `pocket` ('wallet' | 'fund'); 0 when it is enough. */
export function shortfall(b,cost,pocket){
  if(!b||!(cost>0))return 0;
  const have=pocket==='wallet'?b.wallet:b.fund;
  if(have==null)return 0;
  return Math.max(0,cost-Math.max(0,have));
}

/** The money block of a confirm dialog. `money`: {cost, pocket} from the caller when it knows them;
 * otherwise a confirm that starts with a spending word and names exactly one price is read as paid from
 * the workplace fund (on a work sheet) or the wallet (elsewhere). Nothing when no money is involved. */
export function confirmMoney(b,texts,money=null){
  if(!b)return '';
  const talks=money||texts.some(t=>/\d\s*xu\b/u.test(String(t||'')));
  if(!talks)return '';
  let cost=money?.cost??null,pocket=money?.pocket||null;
  if(cost==null&&isSpend(...texts))cost=priceIn(...texts);
  if(!pocket)pocket=b.fund!=null?'fund':'wallet';
  const miss=shortfall(b,Number(cost)||0,pocket);
  const where=pocket==='wallet'?'Ví':(b.fundName||'Quỹ tiệm');
  return `<p class="mn-confirm" data-testid="money-confirm">${chipHTML(b)}</p>`+
    (miss?`<p class="mn-short" role="status">⚠️ ${esc(where)} còn thiếu <b>${fmt(miss)} xu</b> cho khoản này.</p>`:'');
}

/* ---------------------------------------------------------------- the chip in sheet headers (DOM) */
const HEADS='.sheet-head,.preparation-topline';
let booted=null;

/** Start keeping the chip in the header of every open sheet. `scope(dialog)` (see top), `till()` the
 * current workplace's money word, `phone()` true on the phone layout. */
export function moneyBoot({api,scope,till=()=>'',phone=()=>false,css=asset('/css/money.css')}){
  if(booted||typeof document==='undefined')return;
  booted={api,scope,till,phone};
  if(css&&!document.querySelector('link[data-money-css]')){const l=document.createElement('link');l.rel='stylesheet';l.href=css;l.dataset.moneyCss='1';document.head.append(l);}
  let queued=false;
  const later=()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;syncAll();});};
  const watched=new WeakSet();
  const mo=new MutationObserver(later);
  const watch=d=>{if(watched.has(d))return;watched.add(d);mo.observe(d,{childList:true,subtree:true,attributes:true,attributeFilter:['open']});};
  const scan=()=>{for(const d of document.querySelectorAll('dialog'))watch(d);};
  scan();
  // Dialogs made on first use (bank, marriage…) are appended to <body>.
  new MutationObserver(recs=>{if(recs.some(r=>[...r.addedNodes].some(n=>n.nodeName==='DIALOG'))){scan();later();}}).observe(document.body,{childList:true});
  api.addEventListener?.('state',later);
  document.addEventListener('sheetrender',()=>syncAll());
  later();
}

/** Balances for a dialog (null: no chip there). */
export function dialogBalances(d){
  if(!booted||!d)return null;
  let sc=null;try{sc=booted.scope(d);}catch{sc=null;}
  return balances(booted.api.state,sc,sc?.fund?booted.till(sc.fund):'');
}

function syncAll(){
  if(!booted)return;
  for(const d of document.querySelectorAll('dialog'))sync(d);
}
function sync(d){
  if(d.id==='confirmDialog')return;   // the confirm has its own line (confirmMoney)
  const b=d.open?dialogBalances(d):null,head=b?d.querySelector(HEADS):null;
  for(const el of d.querySelectorAll('.mn-chip'))if(el.parentElement!==head)el.remove();
  if(!head)return;
  let chip=head.querySelector(':scope>.mn-chip');
  const html=chipHTML(b,{phone:booted.phone()});
  if(!chip){
    chip=document.createElement('span');chip.className='mn-chip';chip.dataset.testid='money-chip';
    head.append(chip);
  }
  if(chip._html===html)return;
  chip.innerHTML=html;chip._html=html;
  // A balance that changed since this sheet last showed it gives the chip a short bump (no forced layout).
  if(d._mnLast&&d._mnLast!==html){chip.classList.remove('mn-bump');requestAnimationFrame(()=>requestAnimationFrame(()=>chip.isConnected&&chip.classList.add('mn-bump')));}
  d._mnLast=html;
}
