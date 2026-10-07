/** 🔨 Nhà đấu giá đồ độc bản (game/auction.py). Story mode. The lots, the history and the named landmarks come from
 * GET /api/auction; every rule lives on the server (the minimum next bid, the account age, the escrow). A bid is the
 * command `jr_auc_bid {lot, amount, anon, label}`: the money is held (wallet then bank) and comes back at once when
 * someone bids more (POST /api/live/effects collects it). Live prices: `auction_watch` on the live socket while the
 * sheet is open; `auction_bid`, `auction_end` frames; `auction_outbid` / `auction_won` reach the page anywhere
 * (app.js imports onOutbid / onWon). Phone first, few words: one lot a screen, quick raise chips, one main button.
 * Its own dialog, opened with data-action="auction" (menu, the town map's 🔨 door) or "auctionLands" (🏞️ Danh thắng).
 * Styles: /css/spend.css + /css/auction.css. */
import {icon,escapeHTML as esc} from '../icons.js';
// Typed numbers in the − N + steppers (owner 07/10: "cho nhập số nhé").
import {qtyBox,QTY,afterTap,qtyVal} from '../qty-input.js';

const TABS=[['live','🔨','Đang đấu giá'],['past','📜','Đã chốt'],['lands','🏞️','Danh thắng'],['mine','🎁','Của tôi']];
export const ACTIONS={auction:'live',auctionLands:'lands'};
const S={dlg:null,env:null,tab:'live',lot:'',data:null,at:0,busy:false,flash:null,amount:0,anon:false,timer:0,live:null,watching:false,off:[]};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const J=()=>S.env?.api?.state?.journey||{};
const U=()=>J().uniq||null;
const CAT=()=>S.env?.api?.content?.journey?.auction||null;
const clock=()=>Date.now()/1000+(Number(S.env?.api?.clockOffset)||0);

let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=Promise.all([link('/css/spend.css','sd-css'),link('/css/auction.css','au-css')]);

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium sd-sheet au-sheet';d.setAttribute('aria-labelledby','au-title');
  d.innerHTML='<div class="sd-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-au]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.au,el.dataset);
  });
  d.addEventListener('change',e=>{if(e.target.name==='anon'){S.anon=e.target.checked;}});
  // A bid being typed: the main button says what it will pay (never under the next minimum), before the box commits.
  d.addEventListener('input',e=>{const l=lot(),b=d.querySelector('[data-au="go"]');if(!l||!b||!e.target.matches?.('input[data-qty]'))return;
    S.amount=Math.max(l.next,qtyVal(e.target));b.textContent=`Trả ${fmt(bidOf(l))} xu`;});
  d.addEventListener('close',()=>{S.flash=null;clearInterval(S.timer);S.timer=0;watch(false);});
  S.dlg=d;return d;
}

/* ---- live prices (live/auction.py): only while the sheet is open, never a polling loop ---- */
async function socket(){
  if(S.live)return S.live;
  try{const m=await import('./live.js');S.live=m.live;}catch{return null;}
  const lv=S.live;
  S.off.push(lv.on('auction_bid',onBid),lv.on('auction_end',()=>{if(S.dlg?.open){load(true);setTimeout(()=>{if(S.dlg?.open)load(true);},2500);}}),lv.on('welcome',()=>{S.watching=false;if(S.dlg?.open)watch(true);}));
  return lv;
}
async function watch(on){
  const lv=await socket();if(!lv||lv.state!=='open'||!lv.flags?.auction)return;
  if(on&&S.watching)return;
  if(lv.send({t:'auction_watch',open:!!on}))S.watching=!!on;
}
function onBid(f){
  const d=S.data;if(!d)return;
  const lot=d.lots.find(x=>x.id===f.lot);if(!lot||lot.high>f.high)return;
  Object.assign(lot,{high:f.high,bids:f.n,ends_at:f.ends,next:f.next||lot.next,who:f.name||lot.who});
  if(S.amount&&S.amount<lot.next&&lot.id===S.lot)S.amount=0;
  if(d.me?.bids&&!f.lead&&d.me.bids[lot.id]?.held)d.me.bids[lot.id].held=0;   // someone else leads now
  if(f.lead&&d.me){d.me.bids[lot.id]={amount:f.high,held:f.high};}
  if(S.dlg?.open&&!S.busy)render();
}

/** Collect a refund / a won item now (the same as on load: game/live_effects.py). */
async function collect(env){
  const api=env?.api;if(!api)return;
  try{const d=await api.json('/api/live/effects',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:'{}'});
    if(d?.paid&&d.state&&typeof d.revision==='number'){api.accept({state:d.state,revision:d.revision});env.renderMain?.();}}
  catch(e){console.warn('auction: collect',e);}
}
export async function onOutbid(env,f){
  S.env=S.env||env;await collect(env);
  const lot=S.data?.lots?.find(x=>x.id===f.lot);
  const text=`🔨 Đã bị trả cao hơn${lot?` ở “${lot.name}”`:''}: ${fmt(f.high)} xu. Tiền giữ đã về.`;
  if(S.dlg?.open){S.flash={text,kind:'bad'};load(true);}else env.toast?.(text,'hint');
}
export async function onWon(env,f){
  S.env=S.env||env;await collect(env);
  const text=`🔨 Bạn thắng đấu giá với ${fmt(f.price)} xu! Xem ở Của tôi.`;
  if(S.dlg?.open){S.flash={text,kind:'good'};load(true);}else env.toast?.(text,'good');
}

export async function openAuction(env,tab){
  S.env=env;
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();
  if(TABS.some(t=>t[0]===tab))S.tab=tab;
  S.flash=null;
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
  await collect(env);
  await load(true);
  watch(true);
  clearInterval(S.timer);S.timer=setInterval(()=>{if(!S.dlg?.open)return;const el=S.dlg.querySelector('[data-au-clock]');if(el)el.textContent=left(lot());
    if(lot()&&lot().ends_at<=clock()&&Date.now()-S.at>8000)load(true);},1000);
}
export async function auctionAction(action,data,el,env){
  if(!(action in ACTIONS))return false;
  await openAuction(env,ACTIONS[action]||data?.tab);return true;
}
async function load(force=false){
  if(!force&&S.data&&Date.now()-S.at<5000)return;
  S.at=Date.now();
  const prev=S.data;
  try{S.data=await S.env.api.json('/api/auction');}catch{S.data=S.data||{error:true,lots:[],past:[],lands:[]};}
  // Each server process caches the page ~1 s: never step back behind a bid the live socket already told us about.
  for(const l of S.data.lots||[]){const o=prev?.lots?.find(x=>x.id===l.id);if(o&&o.bids>l.bids)Object.assign(l,{high:o.high,bids:o.bids,ends_at:o.ends_at,next:o.next,who:o.who});}
  if(!S.data.lots?.some(x=>x.id===S.lot))S.lot=S.data.lots?.find(x=>x.starts_at<=clock())?.id||S.data.lots?.[0]?.id||'';
  if(S.dlg?.open)render();
}
async function send(payload){
  const {api}=S.env;S.busy=true;render();
  try{
    const r=await api.command('jr_auc_bid',payload);
    S.flash={text:r.message,kind:'good'};S.amount=0;
    return r;
  }catch(e){
    S.flash=e.quiet?null:{text:e.message||'Chưa trả giá được. Thử lại nhé.',kind:'bad'};
    if(e.data?.code==='auction_sync')await collect(S.env);
    return null;
  }finally{S.busy=false;await load(true);render();}
}

/* ---- the lot ---- */
const lot=()=>S.data?.lots?.find(x=>x.id===S.lot)||null;
const mine=l=>S.data?.me?.bids?.[l.id]||null;
const leading=l=>Boolean(mine(l)?.held);   // only the leader's money is held (game/auction.py)
function left(l){
  if(!l)return '';const t=clock();
  if(l.starts_at>t){const d=new Date(l.starts_at*1000);return `Mở lúc ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;}
  const s=Math.max(0,Math.round(l.ends_at-t));if(!s)return 'Đang chốt…';
  const h=Math.floor(s/3600),m=Math.floor(s%3600/60),x=s%60;
  return `⏳ ${h?`${h}:`:''}${String(m).padStart(h?2:1,'0')}:${String(x).padStart(2,'0')}`;
}
const cash=()=>Number(J().wallet)||0;
const ready=()=>cash()<0?0:cash()+(Number(J().bank?.balance)||0);
const heldOn=l=>Number(U()?.hold?.[l.id]||0);
const bidOf=l=>Math.max(S.amount||0,l.next);
function why(l){
  if(!l)return 'Chưa có phiên';
  const me=S.data?.me;if(!me)return 'Đăng nhập để trả giá';
  if(!me.can)return me.why||'Chưa trả giá được';
  if(l.starts_at>clock())return 'Chưa mở';
  if(l.ends_at<=clock())return 'Đã hết giờ';
  if(cash()<0)return 'Ví đang nợ';
  const need=bidOf(l)-heldOn(l);
  return ready()>=need?'':`Còn thiếu ${fmt(need-ready())} xu`;
}

/** The item's picture: a plate, a phone, a painting (drawn from its colours), a landmark or a title. */
function art(l){
  const d=l.data||{};
  if(l.kind==='plate')return `<div class="au-art au-plate" aria-hidden="true"><span>${esc(l.name)}</span></div>`;
  if(l.kind==='phone')return `<div class="au-art au-phone" aria-hidden="true"><span>📱</span><b>${esc(l.name)}</b></div>`;
  if(l.kind==='art'){const [a,b,c]=(Array.isArray(d.colors)?d.colors:[]).map(x=>/^#[0-9a-f]{6}$/i.test(x)?x:'#888');
    return `<div class="au-art au-canvas" aria-hidden="true" style="--a:${a||'#9fc5e8'};--b:${b||'#6aa84f'};--c:${c||'#e06666'}"><i></i><em>${esc(d.artist||'')}${d.year?` · ${Number(d.year)}`:''}</em></div>`;}
  if(l.kind==='land')return `<div class="au-art au-land" aria-hidden="true"><span>${esc(l.emoji)}</span><em>${esc(d.where||'')}</em></div>`;
  return `<div class="au-art au-title" aria-hidden="true"><span>${esc(l.emoji)}</span></div>`;
}
const TIER={1:'',2:'💎',3:'👑'};

/* ---- rendering ---- */
function render(){
  if(!S.dlg)return;
  const body=S.dlg.querySelector('.sd-body'),y=body?.scrollTop;
  // Another player's bid redraws the page: a bid being typed stays in its box, with the focus.
  const a=document.activeElement,typing=a?.matches?.('input[data-qty]')&&S.dlg.contains(a)?a.value:null;
  S.dlg.querySelector('.sd-root').innerHTML=page();
  if(typing!==null){const b=S.dlg.querySelector('input[data-qty]');if(b){b.value=typing;b.focus({preventScroll:true});try{b.setSelectionRange(typing.length,typing.length);}catch{/* not a text box */}}}
  if(y)S.dlg.querySelector('.sd-body').scrollTop=y;
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
const chip=(op,id,label,on,title='')=>`<button type="button" class="sd-chip${on?' on':''}" data-au="${op}" data-id="${esc(id)}" aria-pressed="${on}"${title?` aria-label="${esc(title)}" title="${esc(title)}"`:''}>${label}</button>`;

function page(){
  const t=TABS.find(x=>x[0]===S.tab)||TABS[0];
  const held=Number(U()?.held||0);
  const head=`<header class="sheet-head sd-head"><span class="sd-logo" aria-hidden="true">🔨</span><div class="grow"><h2 id="au-title">${esc(t[2])}</h2></div>
    <span class="sd-wallet" title="Ví">👛 ${fmt(Math.max(0,cash()))}</span><button class="icon-btn" type="button" data-au="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  const tabs=`<nav class="sd-tabs" role="tablist" aria-label="Nhà đấu giá">${TABS.map(([id,e,l])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" aria-label="${esc(l)}" title="${esc(l)}" class="${S.tab===id?'on':''}" data-au="tab" data-tab="${id}">${e}</button>`).join('')}</nav>`;
  if(!J().story)return head+`<div class="sheet-body sd-body"><p class="sd-empty">Chỉ có trong hành trình.</p></div>`;
  if(!S.data)return head+tabs+`<div class="sheet-body sd-body"><p class="sd-empty">⏳</p></div>`;
  const flash=`<p class="sd-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  const hold=held?`<p class="au-held" title="Đang giữ cho đấu giá">🔒 Đang giữ ${fmt(held)} xu</p>`:'';
  const inner={live,past,lands,mineTab}[S.tab==='mine'?'mineTab':S.tab]();
  let bar='';
  if(S.tab==='live'&&lot()){const l=lot(),w=why(l),n=bidOf(l);
    bar=`<footer class="sd-bar">${w?`<small class="sd-why">${esc(w)}</small>`:''}<button type="button" class="btn primary big sd-main" data-au="go"${S.busy||w?' disabled':''}>Trả ${fmt(n)} xu</button></footer>`;}
  return head+tabs+`<div class="sheet-body sd-body">${flash}${hold}${inner}</div>`+bar;
}

// Chat 07/10 16:55 ("đấu với AI hay người thật"): who bids, and that the winner's xu are gone for good (game/auction.py burns
// them). 10 words: the sheet stays within the life cap of 30 (scripts/check_word_caps.py --life).
const REAL=`<p class="au-note au-real">👥 Toàn người chơi thật. Ai thắng mất hẳn số xu.</p>`;
function live(){
  const d=S.data,lots=d.lots||[];
  if(!lots.length)return `<p class="sd-empty">🔨</p><p class="au-note">Phiên mở lúc 20:30 mỗi ngày.</p>${REAL}`;
  const l=lot()||lots[0];S.lot=l.id;
  const chips=lots.length>1?`<div class="sd-chips">${lots.map(x=>chip('lot',x.id,`${x.emoji}${TIER[x.tier]||''}`,x.id===l.id,x.name)).join('')}</div>`:'';
  const me=mine(l),lead=leading(l),out=me&&!lead&&l.high>0;
  const state=lead?`<p class="au-state good">👑 Bạn đang dẫn đầu</p>`:out?`<p class="au-state bad">⚠️ Đã bị trả cao hơn</p>`:'';
  const who=l.bids?`<span data-no-translate>${esc(l.who||'')}</span>`:'Chưa ai trả';
  const quick=(CAT()?.quick||[1,2,5]).map(k=>{const v=l.bids?l.next+(k-1)*l.step:l.start+(k-1)*l.step;return chip('amount',v,`${fmt(v)}`,bidOf(l)===v);}).join('');
  const anon=`<label class="sd-toggle"><input type="checkbox" name="anon"${S.anon?' checked':''}><span>Ẩn danh</span></label>`;
  return REAL+chips+`<section class="sd-card au-lot">${art(l)}<h3>${esc(l.emoji)} <span data-no-translate>${esc(l.name)}</span></h3>
    <div class="au-price"><b>${fmt(l.bids?l.high:l.start)} xu</b><small>${l.bids?`${l.bids} lượt · ${who}`:'Giá khởi điểm'}</small></div>
    <p class="au-clock" data-au-clock>${esc(left(l))}</p>${state}
    <div class="sd-chips sd-amounts">${quick}<label class="au-typed">${qtyBox({value:bidOf(l),min:l.next,max:1e9,money:true,label:'Trả bao nhiêu xu',go:`data-au="typed" data-id="${QTY}"`})}<small>xu</small></label></div>${anon}${help()}</section>`;
}
const help=()=>`<details class="lx-help au-help"><summary aria-label="Luật đấu giá">?</summary><ul>
  <li>Trả giá thì tiền được giữ lại. Bị trả cao hơn: tiền về ngay.</li><li>5 phút cuối có người trả: thêm 5 phút.</li>
  <li>Người thắng trả cho phố, món đồ là độc nhất.</li><li>Tài khoản đủ ${Number(CAT()?.account_days)||3} ngày mới trả giá được.</li></ul></details>`;

function past(){
  const rows=(S.data.past||[]).map(x=>`<li><span>${esc(x.emoji)}</span><b data-no-translate>${esc(x.name)}</b><em>${x.status==='sold'?`${fmt(x.price)}`:'—'}</em><small data-no-translate>${x.status==='sold'?esc(x.winner||''):'Chưa có người mua'}</small></li>`).join('');
  return rows?`<section class="sd-card"><ol class="sd-board au-past">${rows}</ol></section><p class="au-note">🔥 ${fmt(S.data.burned)} xu đã vào quỹ phố</p>`:`<p class="sd-empty">📜</p>`;
}
function lands(){
  const rows=(S.data.lands||[]).map(x=>`<li class="au-plaque"><span>${esc(x.emoji)}</span><div><b data-no-translate>${esc(x.name)}</b><small>${esc(x.where||'')}</small></div></li>`).join('');
  return rows?`<ul class="au-plaques">${rows}</ul>`:`<p class="sd-empty">🏞️</p><p class="au-note">Thắng đấu giá để đặt tên hồ, đồi, bến sông theo tên bạn.</p>`;
}
function mineTab(){
  const own=Object.entries(U()?.own||{});
  const rows=own.map(([id,x])=>`<li><span>${esc((CAT()?.kinds||[]).find(k=>k[0]===x.k)?.[1]||'🎁')}</span><b data-no-translate>${esc(x.t)}</b><em>${fmt(x.p)}</em></li>`).join('');
  return rows?`<section class="sd-card"><ol class="sd-board">${rows}</ol></section>`:`<p class="sd-empty">🎁</p><p class="au-note">Món độc bản bạn thắng sẽ ở đây.</p>`;
}

async function onClick(op,data){
  switch(op){
    case'close':S.dlg.close();return;
    case'tab':S.tab=data.tab;S.flash=null;render();S.dlg.querySelector('.sd-body')?.scrollTo?.(0,0);return;
    case'lot':S.lot=data.id;S.amount=0;S.flash=null;render();return;
    case'amount':S.amount=Number(data.id)||0;render();return;
    case'typed':S.amount=Number(data.id)||0;afterTap(render);return;   // a typed bid (qty-input.js): never under the next minimum (bidOf)
    case'go':{const l=lot();if(!l||why(l))return;await send({lot:l.id,amount:bidOf(l),anon:S.anon,label:l.name.slice(0,40)});return;}
  }
}
