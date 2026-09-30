/** 🏦 Ngân hàng Phố: the player's phone-banking app (story mode).
 * Every rule and number lives in game/bank.py; this file renders api.state.journey.bank and sends
 * `jr_bk_*` commands. The only maths mirrored here is the loan schedule (bank.installment/schedule),
 * so the contract shows the exact installments and total interest before signing; the server checks
 * the total the player saw. The couple's joint account and requests come from GET /api/marriage
 * (game/couple.py) and its own /api/marriage/fund_* ops: nothing about them is decided here.
 * Its own dialog (not the shared #sheet), opened by the rail entry "Ngân hàng" (action `bank`). */
import {icon,escapeHTML as esc} from '../icons.js';
import {Sound} from '../audio.js';

const S={dlg:null,env:null,tab:'home',busy:false,flash:null,filter:'all',joint:null,jointAt:0,loan:{kind:'personal',amount:0,term:28,career:''},listening:false};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const signed=n=>`${n>0?'+':n<0?'−':''}${fmt(Math.abs(n))}`;
const pct=bp=>`${(bp/100).toLocaleString('vi-VN',{maximumFractionDigits:2})}%`;
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,op,data={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-bk="${op}"${attrs(data)}${S.busy?' disabled':''}${extra}>${label}</button>`;
const B=()=>S.env?.api?.state?.journey?.bank||{};
const J=()=>S.env?.api?.state?.journey||{};
/* "Ngày N" wording, the same words as game/days.py on_day(): counted from state.journey.life_day. */
const onDay=n=>{const d=n-(J().life_day||0);return d===0?`hôm nay (Ngày ${n})`:d===1?`Ngày ${n} (ngày mai)`:d<0?`Ngày ${n} (đã qua)`:`Ngày ${n} (còn ${d} ngày)`;};
const rid=()=>globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
const acctNo=no=>String(no||'').replace(/(\d{4})(\d{4})(\d+)/,'$1 $2 $3');
const plain=t=>String(t||'').normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/đ/g,'d').replace(/Đ/g,'D').toUpperCase();
const LOGO=`<svg class="bk-logo-mark" viewBox="0 0 32 32" aria-hidden="true"><path d="M4 13 16 5l12 8v2H4z" fill="currentColor"/><path d="M7 17h3v8H7zm7.5 0h3v8h-3zM22 17h3v8h-3zM4 26h24v3H4z" fill="currentColor" opacity=".85"/></svg>`;

/* ---- loan maths: a mirror of game/bank.py (_interest, _fits, installment, schedule) ---- */
const interest=(rest,bp)=>Math.floor((rest*bp+5000)/10000);
function fits(p,bp,n,pay){let rest=p;for(let i=0;i<n-1;i++){rest-=pay-interest(rest,bp);if(rest<=0)return true;}return rest+interest(rest,bp)<=pay;}
function installment(p,bp,n){let lo=Math.max(1,Math.ceil(p/n)),hi=p*2+10;while(lo<hi){const mid=Math.floor((lo+hi)/2);if(fits(p,bp,n,mid))hi=mid;else lo=mid+1;}return lo;}
function schedule(p,bp,term,start,period){
  const n=Math.floor(term/period),pay=installment(p,bp,n),rows=[];let rest=p;
  for(let k=1;k<=n;k++){const i=interest(rest,bp),part=k===n?rest:Math.max(0,Math.min(rest,pay-i));rows.push({k,due:start+period*k,principal:part,interest:i,amount:part+i});rest-=part;}
  return rows;
}

/* ---- stylesheet on first use ---- */
let cssReady=null;
function ensureCss(){
  if(cssReady)return cssReady;
  const href=globalThis.__mnlBoot?.asset?.('/css/bank.css')||'/css/bank.css';
  cssReady=new Promise(done=>{
    if(document.querySelector('link[data-bk-css]')){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=href;l.dataset.bkCss='';
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
  return cssReady;
}

/* ---- "ting ting" when a card is swiped anywhere in the game (app.js forwards results with card_swipe) ---- */
let tingSound=null;
export function swipeSound(api){
  const s=api?.state?.settings||{};if(s.sound===false||s.detailSfx===false)return;
  try{tingSound??=new Sound();tingSound.configure(s);tingSound.ting();}catch{/* silent */}
}

/* ---- the dialog ---- */
function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium bk-sheet';d.setAttribute('aria-labelledby','bk-title');
  d.innerHTML='<div class="bk-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-bk]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.bk,el.dataset,el);
  });
  d.addEventListener('input',e=>{if(e.target.closest('[data-bk-loan]'))onLoanField(e.target);});
  d.addEventListener('change',e=>{if(e.target.closest('[data-bk-loan]'))onLoanField(e.target);});
  d.addEventListener('submit',e=>e.preventDefault());
  d.addEventListener('close',()=>{S.flash=null;});
  S.dlg=d;return d;
}
export async function openBank(env,tab){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';env.api.addEventListener('state',()=>{const key=JSON.stringify([J().wallet,J().bank]);if(key===seen)return;seen=key;if(S.dlg?.open&&!S.busy)render();});
  }
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();if(tab)S.tab=tab;
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();loadJoint();
  if(B().unread)send('jr_bk_read',{},{quiet:true});
}
export async function bankAction(action,data,el,env){
  if(action!=='bank')return false;
  await openBank(env,data?.tab);return true;
}

async function loadJoint(force=false){
  if(!force&&Date.now()-S.jointAt<15000)return;
  S.jointAt=Date.now();
  try{const v=await S.env.api.json('/api/marriage');S.joint=v?.home?.fund?{fund:v.home.fund,requests:v.home.requests||[],debts:v.home.debts||[],partner:v.couple?.partner?.name||''}:null;}
  catch{S.joint=null;}
  if(S.dlg?.open&&!S.busy)render();
}

/** A command from the bank. `quiet` (the mark-read when the app opens): runs in the background, never sets
 * S.busy, so buttons and tabs stay usable meanwhile (it used to disable them for up to 1–1,5 s at peak), and a
 * failure stays silent; it re-renders once at the end if nothing else is in flight. */
async function send(action,payload={},{quiet=false}={}){
  const {api}=S.env;
  if(!quiet){S.busy=true;render();}
  try{
    const r=await api.command(action,payload);
    if(!quiet){const extra=(r.effects||[]).filter(Boolean);S.flash={text:[r.message,...extra].filter(Boolean).join(' '),kind:r.approved===false?'warn':'good'};}
    return r;
  }catch(e){if(!quiet)S.flash={text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{if(!quiet){S.busy=false;render();}else if(S.dlg?.open&&!S.busy)render();}
}
async function marriagePost(op,body){
  const {api}=S.env;S.busy=true;render();
  try{
    const data=await api.json(`/api/marriage/${op}`,{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify(body)});
    if(data.state&&typeof data.revision==='number')api.accept({state:data.state,revision:data.revision});
    S.flash={text:data.message||'Đã xong.',kind:'good'};S.jointAt=0;
  }catch(e){S.flash={text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};}
  finally{S.busy=false;render();loadJoint(true);}
}

const val=id=>{const el=S.dlg?.querySelector('#'+id);return el?el.value:'';};
const amountOf=id=>{const n=Number(val(id));return Number.isInteger(n)&&n>0?n:0;};
const ask=(title,msg,label,money)=>S.env.confirmAction(title,msg,label,money);  // money: {cost,pocket} → "còn thiếu" (v4/money.js)

async function onClick(op,data){
  const b=B(),R=b.rules||{};
  switch(op){
    case'close':S.dlg.close();return;
    case'tab':S.tab=data.tab;S.flash=null;render();S.dlg.querySelector('.bk-body')?.scrollTo?.(0,0);return;
    case'filter':S.filter=data.f;render();return;
    case'open':if(await ask('Mở tài khoản Ngân hàng Phố?','Miễn phí mở và duy trì. Bạn nhận số tài khoản, sổ giao dịch và điểm tín dụng khởi đầu 650.','Mở tài khoản'))send('jr_bk_open');return;
    case'deposit':{const a=amountOf('bk-amt');if(!a){S.flash={text:'Nhập số xu muốn nộp nhé.',kind:'warn'};render();return;}
      if(await ask(`Nộp ${xu(a)} vào tài khoản?`,`Tiền mặt trong ví còn ${xu(J().wallet-a)} sau khi nộp.`,`Nộp · ${xu(a)}`,{cost:a,pocket:'wallet'}))send('jr_bk_deposit',{amount:a});return;}
    case'withdraw':{const a=amountOf('bk-amt'),atm=val('bk-atm')||'own',fee=atm==='other'?R.atm_fee:0;if(!a){S.flash={text:'Nhập số xu muốn rút nhé.',kind:'warn'};render();return;}
      if(await ask(`Rút ${xu(a)} tiền mặt?`,fee?`Cây ATM khác ngân hàng thu phí ${xu(fee)}. Tài khoản bị trừ ${xu(a+fee)}.`:'Rút tại cây ATM Ngân hàng Phố, không mất phí.',`Rút · ${xu(a)}`))send('jr_bk_withdraw',{amount:a,atm});return;}
    case'save':{const term=Number(val('bk-term')),a=amountOf('bk-save-amt'),src=val('bk-save-src')||'acc',renew=!!S.dlg.querySelector('#bk-renew')?.checked&&term>0;if(!a){S.flash={text:'Nhập số xu muốn gửi nhé.',kind:'warn'};render();return;}
      const rate=term?R.term_rate[String(term)]:R.demand_rate,gain=term?termGain(a,rate,term,R):0,name=b.term_names[String(term)].toLowerCase();
      const msg=term?`${b.term_names[String(term)]} (${term} ngày sống), lãi ${pct(rate)}/năm. Đáo hạn ${onDay(J().life_day+term)}, nhận ${xu(a+gain)} (lãi ${gain?xu(gain):'dưới 1 xu'}).${renew?' Tới hạn tự tái tục: gốc và lãi gửi tiếp kỳ mới.':''} Rút trước hạn chỉ hưởng lãi không kỳ hạn ${pct(R.demand_rate)}/năm.`:`Lãi ${pct(rate)}/năm, cộng vào sổ mỗi ngày. Rút lúc nào cũng được.`;
      if(await ask(`Gửi ${xu(a)} tiết kiệm ${name}?`,msg+(src==='cash'?' Lấy từ tiền mặt.':' Lấy từ tài khoản thanh toán.'),`Gửi · ${xu(a)}`,{cost:a,pocket:src==='cash'?'wallet':'account'}))send('jr_bk_save',{amount:a,term,src,...(renew?{renew:true}:{})});return;}
    case'unsaveDemand':{const a=amountOf('bk-demand-out');if(!a){S.flash={text:'Nhập số xu muốn rút nhé.',kind:'warn'};render();return;}
      if(await ask(`Rút ${xu(a)} từ sổ không kỳ hạn?`,'Tiền về tài khoản thanh toán, không mất lãi đã cộng.',`Rút · ${xu(a)}`))send('jr_bk_unsave',{id:'demand',amount:a});return;}
    case'unsaveTerm':{const t=(b.savings?.terms||[]).find(x=>x.id===data.id);if(!t)return;
      if(await ask('Tất toán sổ trước hạn?',`Sổ đáo hạn ${onDay(t.due)}. Rút bây giờ chỉ nhận lãi không kỳ hạn ${xu(t.early)} thay vì ${xu(t.interest)} khi giữ đến hạn.`,`Tất toán · ${xu(t.amount+t.early)}`))send('jr_bk_unsave',{id:t.id,confirm:true});return;}
    case'house':S.dlg.close();(await import('./house.js')).openHouse(S.env);return;
    case'cardApply':{const o=b.card_offer||{};
      if(await ask('Nộp hồ sơ mở thẻ tín dụng?',`Ngân hàng tra cứu hồ sơ tín dụng (điểm giảm nhẹ).${o.ok?` Dự kiến hạn mức ${xu(o.limit)}.`:` Lưu ý: ${o.text}`} Sao kê mỗi ${R.card_cycle} ngày, trả hết trước hạn thì không mất lãi.`,'Nộp hồ sơ'))send('jr_bk_card_apply',{confirm:true});return;}
    case'cardPay':{const c=b.card;if(!c)return;const src=val('bk-card-src')||'acc';let payload={src},amount=0;
      if(data.what==='min'){amount=Math.max(c.past_due,c.stmt?.min_left||0);payload.what='min';}
      else if(data.what==='stmt'){amount=c.stmt?.left||0;payload.what='stmt';}
      else if(data.what==='all'){amount=c.bal;payload.what='all';}
      else{amount=amountOf('bk-card-amt');payload.amount=amount;if(!amount){S.flash={text:'Nhập số xu muốn trả nhé.',kind:'warn'};render();return;}}
      if(await ask(`Trả ${xu(amount)} cho thẻ •••• ${c.no}?`,`Trừ từ ${src==='acc'?'tài khoản thanh toán':'tiền mặt'}. Dư nợ còn ${xu(Math.max(0,c.bal-amount))}.`,`Trả · ${xu(amount)}`,{cost:amount,pocket:src==='cash'?'wallet':'account'}))send('jr_bk_card_pay',payload);return;}
    case'cardCash':{const c=b.card,a=amountOf('bk-cash-amt');if(!c||!a){S.flash={text:'Nhập số xu muốn ứng nhé.',kind:'warn'};render();return;}
      const fee=Math.max(R.cash_fee_min,Math.ceil(a*R.cash_fee_pct/100));
      if(await ask(`Ứng ${xu(a)} tiền mặt từ thẻ?`,`Phí ứng ${xu(fee)} (${R.cash_fee_pct}%, ít nhất ${xu(R.cash_fee_min)}). Lãi ${pct(R.card_bp)}/ngày tính ngay từ hôm nay, không có miễn lãi. Dư nợ tăng ${xu(a+fee)}.`,`Ứng · ${xu(a)}`))send('jr_bk_card_cash',{amount:a});return;}
    case'autopay':send('jr_bk_card_autopay',{mode:val('bk-autopay')});return;
    case'pref':send('jr_bk_settings',{pref:val('bk-pref')});return;
    case'sweep':send('jr_bk_settings',{sweep:!b.sweep});return;
    case'cardClose':if(await ask('Hủy thẻ tín dụng?','Thẻ không dùng được nữa. Muốn có thẻ mới phải nộp hồ sơ lại.','Hủy thẻ'))send('jr_bk_card_close',{confirm:true});return;
    case'loanSign':{const L=loanPreview();if(!L.ok){S.flash={text:L.why,kind:'warn'};render();return;}
      const kind=b.loan_kinds?.[S.loan.kind]?.name||'Khoản vay';
      const where=S.loan.kind==='shop'?`quỹ ${b.places?.[S.loan.career]||''}`:'tài khoản thanh toán';
      if(await ask(`Ký hợp đồng ${kind.toLowerCase()} ${xu(S.loan.amount)}?`,`Trả ${L.rows.length} kỳ, mỗi ${R.loan_period} ngày, kỳ đầu ${onDay(L.rows[0].due)}. Tổng lãi ${xu(L.interest)}, tổng phải trả ${xu(L.total)}. Tiền giải ngân vào ${where}. Trễ hạn bị phạt ${R.loan_late_pct}% kỳ đó và giảm điểm tín dụng.`,`Ký · lãi ${xu(L.interest)}`))
        send('jr_bk_loan_apply',{kind:S.loan.kind,amount:S.loan.amount,term:S.loan.term,total_interest:L.interest,confirm:true,...(S.loan.kind==='shop'?{career:S.loan.career}:{})});return;}
    case'loanPay':{const ln=(b.loans||[]).find(x=>x.id===data.id);if(!ln)return;const src=val('bk-loan-src-'+ln.id)||'acc';const amount=ln.overdue||ln.next?.amount-ln.next?.paid||0;
      if(await ask(ln.overdue?`Trả ${xu(amount)} đang quá hạn?`:`Trả trước kỳ ${ln.next.k}?`,`Trừ từ ${src==='acc'?'tài khoản thanh toán':'tiền mặt'}.`,`Trả · ${xu(amount)}`,{cost:amount,pocket:src==='cash'?'wallet':'account'}))send('jr_bk_loan_pay',{id:ln.id,src});return;}
    case'loanClose':{const ln=(b.loans||[]).find(x=>x.id===data.id);if(!ln)return;const src=val('bk-loan-src-'+ln.id)||'acc',o=ln.payoff;
      if(await ask('Tất toán khoản vay trước hạn?',`Gốc còn lại ${xu(o.principal)}${o.overdue?`, khoản quá hạn ${xu(o.overdue)}`:''}, lãi những ngày đã dùng ${xu(o.interest)}, phí trả trước hạn ${xu(o.fee)}. Tổng ${xu(o.total)}. Bạn bớt được ${xu(Math.max(0,o.saved))} tiền lãi.`,`Tất toán · ${xu(o.total)}`))send('jr_bk_loan_close',{id:ln.id,src,confirm:true});return;}
    case'jointIn':{const a=amountOf('bk-joint-amt');if(!a){S.flash={text:'Nhập số xu nhé.',kind:'warn'};render();return;}
      if(await ask(`Gửi ${xu(a)} vào quỹ chung?`,'Tiền mặt trong ví chuyển vào tài khoản chung của hai vợ chồng. Người ấy sẽ thấy giao dịch này.',`Gửi · ${xu(a)}`,{cost:a,pocket:'wallet'}))marriagePost('fund_deposit',{amount:a,rid:rid()});return;}
    case'jointOut':{const a=amountOf('bk-joint-amt');if(!a){S.flash={text:'Nhập số xu nhé.',kind:'warn'};render();return;}
      if(await ask(`Rút ${xu(a)} bằng thẻ chung?`,`Tiền về ví của bạn. Hôm nay thẻ chung còn chi được ${xu(S.joint?.fund?.daily_left)}. Người ấy nhận thông báo về giao dịch này.`,`Rút · ${xu(a)}`))marriagePost('fund_withdraw',{amount:a,rid:rid()});return;}
    case'marriage':S.dlg.close();(await import('./marriage.js')).openMarriage(S.env,'home');return;
    case'retry':render();return;
  }
}

/* ---- the new-loan form ---- */
function onLoanField(el){
  const k=el.name;
  if(k==='kind'){S.loan.kind=el.value;S.loan.amount=0;}
  else if(k==='amount')S.loan.amount=Math.max(0,Math.floor(Number(el.value)||0));
  else if(k==='term')S.loan.term=Number(el.value);
  else if(k==='career')S.loan.career=el.value;
  const box=S.dlg.querySelector('.bk-loan-preview');
  if(box&&k==='amount'){box.innerHTML=previewHTML();return;}
  render();
}
function loanPreview(){
  const b=B(),R=b.rules||{},o=b.loan_offers?.[S.loan.kind]||{};
  const a=S.loan.amount||0;
  if(!o.ok)return {ok:false,why:o.text||'Ngân hàng chưa duyệt khoản vay này.'};
  if(a<R.loan_min)return {ok:false,why:`Vay ít nhất ${xu(R.loan_min)}.`};
  if(a>o.max)return {ok:false,why:`Hạn mức hiện tại tối đa ${xu(o.max)}.`};
  if(S.loan.kind==='shop'&&!b.places?.[S.loan.career])return {ok:false,why:'Chọn tiệm nhận vốn vay nhé.'};
  const rows=schedule(a,R.loan_bp[S.loan.kind],S.loan.term,J().life_day,R.loan_period);
  const inst=rows[0].amount,int=rows.reduce((x,r)=>x+r.interest,0);
  const warn=inst>o.weekly_room?`Mỗi kỳ ${xu(inst)} vượt ${R.dti_pct}% thu nhập một tuần (${xu(o.weekly_room)}): ngân hàng sẽ không duyệt. Chọn số nhỏ hơn hoặc kỳ hạn dài hơn.`:'';
  return {ok:!warn,why:warn,rows,interest:int,total:a+int,installment:inst,warn};
}

/* ---- rendering ---- */
function keepFocus(fn){
  const a=document.activeElement,id=a&&S.dlg?.contains(a)?a.id:'',pos=id&&'selectionStart' in a?a.selectionStart:null;
  const top=S.dlg?.querySelector('.bk-body')?.scrollTop;
  fn();
  if(id){const el=S.dlg.querySelector('#'+CSS.escape(id));if(el){el.focus({preventScroll:true});try{if(pos!=null)el.setSelectionRange(pos,pos);}catch{/* number inputs */}}}
  if(top!=null){const body=S.dlg.querySelector('.bk-body');if(body)body.scrollTop=top;}
}
function render(){
  if(!S.dlg)return;
  keepFocus(()=>{S.dlg.querySelector('.bk-root').innerHTML=page();});
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
function head(sub){
  return `<header class="sheet-head bk-head"><span class="bk-logo" aria-hidden="true">${LOGO}</span><div class="grow"><span class="eyebrow">NGÂN HÀNG PHỐ · ỨNG DỤNG</span><h2 id="bk-title">Ngân hàng Phố</h2><p>${sub}</p></div>
    <button class="icon-btn" type="button" data-bk="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
}
const flash=()=>`<p class="bk-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
function page(){
  const b=B();
  if(!b.story)return head('Tài khoản, tiết kiệm, thẻ và khoản vay của riêng bạn.')+`<div class="sheet-body bk bk-body"><section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🏦</div><h3>Ngân hàng chỉ có trong chế độ hành trình</h3><p>Ở chế độ chơi tự do, mỗi nơi làm việc có quỹ riêng. Vào hành trình để có ví, tài khoản ngân hàng, thẻ và khoản vay của một nhân vật.</p></section></div>`;
  if(!b.open)return head('Tài khoản, tiết kiệm, thẻ và khoản vay của riêng bạn.')+`<div class="sheet-body bk bk-body">${flash()}${welcome(b)}</div>`;
  const tabs=[['home','Tổng quan'],['tx','Giao dịch'],['save','Tiết kiệm'],['card','Thẻ'],['loan','Vay']];
  const bar=`<div class="segmented bk-tabs" role="tablist" aria-label="Mục ngân hàng">${tabs.map(([id,l])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" class="${S.tab===id?'active':''}" data-bk="tab" data-tab="${id}">${l}${id==='card'&&b.card?.past_due||id==='loan'&&(b.loans||[]).some(x=>x.overdue)?'<i class="dot" aria-hidden="true"></i>':''}</button>`).join('')}</div>`;
  const body={home,tx,save,card,loan}[S.tab]||home;
  return head(`Số tài khoản ${acctNo(b.no)} · Ngày sống ${b.life_day}`)+`<div class="sheet-body bk bk-body">${bar}${flash()}${alerts(b)}${body(b)}</div>`;
}

function welcome(b){
  return `<section class="bk-card bk-welcome"><span class="bk-logo big" aria-hidden="true">${LOGO}</span><h3>Chào mừng tới Ngân hàng Phố</h3>
    <p>Tiền mặt trong ví vẫn là của bạn. Mở một tài khoản để có thêm:</p>
    <ul class="bk-bullets"><li><b>Tài khoản thanh toán</b>: nộp, rút ở cây ATM, sổ giao dịch có số dư từng dòng.</li>
    <li><b>Tiết kiệm</b>: không kỳ hạn ${pct(b.rules.demand_rate)}/năm, có kỳ hạn tới ${pct(Math.max(...Object.values(b.rules.term_rate)))}/năm.</li>
    <li><b>Thẻ tín dụng</b>: quẹt trước trả sau, sao kê mỗi ${b.rules.card_cycle} ngày.</li>
    <li><b>Khoản vay</b>: vay tiêu dùng, vay mở rộng tiệm, vay mua nhà, trả góp từng kỳ.</li></ul>
    <p class="bk-hint">Tiền mặt hiện có: <b>${xu(b.wallet)}</b></p>${btn('Mở tài khoản miễn phí','open',{},'primary big')}</section>`;
}
function alerts(b){
  const out=[];
  if(b.bad_until)out.push(`<p class="bk-alert bad" role="alert">⚠️ Hồ sơ đang ghi nhận <b>nợ xấu</b> tới ${onDay(b.bad_until)}: không mở thẻ, không vay mới, thẻ tạm ngưng.</p>`);
  else if(b.overdue)out.push(`<p class="bk-alert warn" role="alert">⏰ Bạn đang có khoản <b>quá hạn</b>. Trả sớm để tránh bị ghi nợ xấu (sau ${b.rules.bad_misses} lần trễ hạn).</p>`);
  if(J().wallet<0)out.push(`<p class="bk-alert warn">👛 Ví đang nợ ${xu(-J().wallet)}.${b.sweep?' Tài khoản sẽ tự bù vào sáng mai nếu còn tiền.':''}</p>`);
  return out.join('');
}

function cardVisual(c,holder){
  return `<div class="bk-plastic" role="img" aria-label="Thẻ tín dụng Ngân hàng Phố, số cuối ${esc(c.no)}">
    <div class="bk-plastic-top"><span class="bk-plastic-logo">${LOGO}<b>NGÂN HÀNG PHỐ</b></span><span class="bk-plastic-kind">CREDIT</span></div>
    <span class="bk-chip" aria-hidden="true"></span>
    <div class="bk-plastic-no">•••• •••• •••• ${esc(c.no)}</div>
    <div class="bk-plastic-foot"><span>${esc(plain(holder)||'CHỦ THẺ')}</span><span>Hạn mức ${xu(c.limit)}</span></div></div>`;
}
function limitBar(c){
  const used=Math.min(100,c.limit?Math.round(c.bal*100/c.limit):0),tone=used>70?'bad':used>30?'warn':'good';
  return `<div class="bk-limit"><div class="bk-row"><span>Đã dùng ${xu(c.bal)}</span><span>Còn ${xu(c.available)}</span></div>
    <div class="bk-bar ${tone}" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${used}" aria-label="Đã dùng ${used}% hạn mức"><i style="width:${used}%"></i></div>
    <p class="bk-hint">Đã dùng ${used}% hạn mức. Giữ dưới 30% khi chốt sao kê để điểm tín dụng tăng.</p></div>`;
}
function scoreGauge(sc,R){
  const p=Math.round((sc.value-R.score_min)*100/(R.score_max-R.score_min));
  return `<div class="bk-score ${esc(sc.tone)}"><div class="bk-score-num"><strong>${sc.value}</strong><span>${esc(sc.band)}</span></div>
    <div class="bk-gauge" role="meter" aria-valuemin="${R.score_min}" aria-valuemax="${R.score_max}" aria-valuenow="${sc.value}" aria-label="Điểm tín dụng ${sc.value}"><i style="left:${p}%"></i></div>
    <div class="bk-scale">${[R.score_min,580,670,740,R.score_max].map(n=>`<span style="left:${Math.round((n-R.score_min)*100/(R.score_max-R.score_min))}%">${n}</span>`).join('')}</div></div>`;
}

function home(b){
  const c=b.card,sv=b.savings,loanLeft=(b.loans||[]).reduce((x,l)=>x+l.left,0);
  const hero=`<section class="bk-hero"><small>Tài khoản thanh toán</small><strong class="bk-balance">${xu(b.balance)}</strong>
    <div class="bk-move"><label class="bk-field"><span>Số xu</span><input id="bk-amt" type="number" inputmode="numeric" min="1" placeholder="Ví dụ 50"></label>
    <label class="bk-field"><span>Rút ở</span><select id="bk-atm">${Object.entries(b.atms).map(([k,v])=>`<option value="${k}">${esc(v)}${k==='other'?` (phí ${xu(b.rules.atm_fee)})`:''}</option>`).join('')}</select></label></div>
    <div class="bk-actions">${btn(icon('download',17)+' Nộp tiền','deposit',{},'primary')}${btn(icon('upload',17)+' Rút tiền','withdraw',{},'ghost')}</div></section>`;
  const tile=(tab,emoji,label,value,sub)=>`<button type="button" class="bk-tile" data-bk="tab" data-tab="${tab}"${S.busy?' disabled':''}><span class="bk-tile-emoji" aria-hidden="true">${emoji}</span><span class="bk-tile-label">${label}</span><strong>${value}</strong><small>${sub}</small></button>`;
  const tiles=`<div class="bk-tiles">${tile('save','🐷','Tiết kiệm',xu(sv.total),sv.terms.length?`${sv.terms.length} sổ có kỳ hạn`:'Chưa có sổ kỳ hạn')}
    ${tile('card','💳','Thẻ tín dụng',c?xu(c.bal):'Chưa có',c?`Dư nợ · hạn mức ${xu(c.limit)}`:'Mở thẻ ở mục Thẻ')}
    ${tile('loan','📝','Khoản vay',loanLeft?xu(loanLeft):'Không nợ',loanLeft?`${b.loans.length} khoản đang trả`:'Xem hạn mức vay')}</div>`;
  const inbox=(b.inbox||[]).slice(0,6).map(m=>`<li class="${m.read?'':'new'}"><span class="bk-ib-ic" aria-hidden="true">${m.kind==='call'?'📞':'💬'}</span><div><small>Ngày sống ${m.day}</small><p>${esc(m.text)}</p></div></li>`).join('');
  const sc=b.score;
  const scoreBox=`<section class="bk-card"><h3>Điểm tín dụng</h3>${scoreGauge(sc,b.rules)}
    ${sc.log.length?`<ul class="bk-score-log">${sc.log.slice(0,5).map(r=>`<li><span>Ngày ${r.day} · ${esc(WHY[r.why]||r.why)}</span><b class="${r.delta>0?'up':'down'}">${r.delta>0?'+':'−'}${Math.abs(r.delta)}</b></li>`).join('')}</ul>`:''}
    <details class="bk-tips"><summary>Cách tăng điểm</summary><ul class="bk-bullets">${sc.tips.map(t=>`<li>${esc(t)}</li>`).join('')}</ul>
    <p class="bk-hint">Thu nhập 14 ngày gần nhất: ${xu(b.income.total)} (trung bình ${xu(b.income.avg)}/ngày, ${b.income.days} ngày có thu nhập).</p></details></section>`;
  return hero+tiles+(c?`<section class="bk-card bk-card-mini" >${cardVisual(c,b.holder)}${limitBar(c)}</section>`:'')+
    scoreBox+jointSection()+
    `<section class="bk-card"><h3>Tin nhắn & cuộc gọi</h3>${inbox?`<ul class="bk-inbox">${inbox}</ul>`:'<p class="bk-hint">Chưa có tin nhắn nào.</p>'}</section>`+
    `<section class="bk-card"><h3>Cài đặt</h3><label class="bk-toggle"><input type="checkbox" data-bk="sweep"${b.sweep?' checked':''}${S.busy?' disabled':''}><span>Tự động bù ví khi ví âm (tiền phòng, cơm nước) bằng tiền trong tài khoản</span></label></section>`;
}
const termGain=(a,rate,days,R)=>Math.floor(a*rate*days/(10000*R.year_days));   // bank.term_interest
const WHY={home_ok:'Trả góp nhà đúng hạn',home_late:'Trễ hạn trả góp nhà',home_done:'Trả xong vay mua nhà',open:'Mở tài khoản',inquiry:'Ngân hàng tra cứu hồ sơ',card_full:'Trả hết sao kê đúng hạn',card_min:'Trả tối thiểu đúng hạn',card_late:'Trễ hạn thẻ',
  loan_ok:'Trả góp đúng hạn',loan_late:'Trễ hạn trả góp',loan_done:'Tất toán khoản vay',income:'Thu nhập đều trong tuần',age:'Tài khoản thêm một tuần tuổi',
  util_low:'Dư nợ thẻ thấp',util_mid:'Dư nợ thẻ trên 30%',util_high:'Dư nợ thẻ trên 70%',bad:'Ghi nhận nợ xấu'};

function jointSection(){
  const jt=S.joint;if(!jt)return '';
  const f=jt.fund,st=S.env.api.state;
  const members=(f.members||[]).map(m=>m.name);
  const names=members.length?members:[st?.name,jt.partner].filter(Boolean);
  const hist=(f.history||[]).slice(0,6).map(r=>`<li><span>${esc(r.who||'')} · ${esc(r.label)}${r.held?' (đang xử lý)':''}</span><b class="${r.kind==='deposit'?'up':'down'}">${signed(r.kind==='deposit'?Math.abs(r.amount):-Math.abs(r.amount))}</b><small>${fmt(r.balance)}</small></li>`).join('');
  const reqs=(jt.requests||[]).map(r=>`<li>💸 ${r.mine?'Bạn xin':'Người ấy xin'} ${xu(r.amount)}${r.note?`: “${esc(r.note)}”`:''}${r.loan?' (mượn)':''}</li>`).join('');
  const debts=(jt.debts||[]).filter(d=>d.status==='open').map(d=>`<li>🧾 ${d.lender?`${esc(d.who)} còn nợ bạn`:`Bạn còn nợ ${esc(d.who)}`} ${xu(d.left)}${d.claim&&d.claim.status==='pending'?` · đòi: “${esc(d.claim.text)}”`:''}</li>`).join('');
  return `<section class="bk-card bk-joint"><h3>Tài khoản chung vợ chồng</h3>
    <div class="bk-plastic joint" role="img" aria-label="Thẻ chung Ngân hàng Phố"><div class="bk-plastic-top"><span class="bk-plastic-logo">${LOGO}<b>NGÂN HÀNG PHỐ</b></span><span class="bk-plastic-kind">THẺ CHUNG</span></div>
      <span class="bk-chip" aria-hidden="true"></span><div class="bk-plastic-no">${xu(f.balance)}</div><div class="bk-plastic-foot"><span>${esc(names.map(plain).join(' & '))}</span></div></div>
    <p class="bk-hint">Cả hai cùng thấy mọi giao dịch. Mỗi người chi hoặc rút tối đa theo hạn mức ngày; hôm nay bạn còn <b>${xu(f.daily_left)}</b>. Chọn “Ưu tiên thẻ chung” ở mục Thẻ để trả học phí, cửa sau… bằng quỹ chung.</p>
    <div class="bk-move"><label class="bk-field"><span>Số xu</span><input id="bk-joint-amt" type="number" inputmode="numeric" min="1" placeholder="Ví dụ 30"></label></div>
    <div class="bk-actions">${btn('Gửi vào quỹ chung','jointIn',{},'primary')}${btn('Rút bằng thẻ chung','jointOut',{},'ghost')}</div>
    ${reqs||debts?`<h4>Lời nhờ và sổ nợ</h4><ul class="bk-list">${reqs}${debts}</ul>`:''}
    ${hist?`<h4>Giao dịch chung</h4><ul class="bk-tx joint">${hist}</ul>`:''}
    <div class="bk-actions">${btn('Đòi tiền, trả nợ, gửi tiền: mở Hôn nhân','marriage',{},'ghost small')}</div></section>`;
}

function tx(b){
  const fl=[['all','Tất cả'],['acc','Tài khoản'],['sav','Tiết kiệm'],['card','Thẻ'],['loan','Vay']];
  const rows=(b.log||[]).filter(r=>S.filter==='all'||r.acc===S.filter);
  const label={acc:'Tài khoản',sav:'Tiết kiệm',card:'Thẻ',loan:'Vay'},bal={acc:'Số dư',sav:'Tổng tiết kiệm',card:'Dư nợ thẻ',loan:'Dư nợ vay'};
  return `<div class="segmented bk-filter" role="group" aria-label="Lọc giao dịch">${fl.map(([id,l])=>`<button type="button" class="${S.filter===id?'active':''}" aria-pressed="${S.filter===id}" data-bk="filter" data-f="${id}">${l}</button>`).join('')}</div>
    <section class="bk-card"><h3>Sao kê giao dịch</h3>${rows.length?`<ul class="bk-tx">${rows.map(r=>`<li><div class="bk-tx-main"><small>Ngày ${r.day} · ${label[r.acc]}</small><span>${esc(r.text)}</span></div>
      <div class="bk-tx-amt"><b class="${r.amt>0?'up':r.amt<0?'down':''}">${r.amt?signed(r.amt):'·'}</b><small>${bal[r.acc]} ${fmt(r.bal)}</small></div></li>`).join('')}</ul>`:'<p class="bk-hint">Chưa có giao dịch nào.</p>'}
    <p class="bk-hint">Hiện ${rows.length} giao dịch gần nhất. Giao dịch cũ hơn được lưu vào kho lưu trữ.</p></section>`;
}

function save(b){
  const R=b.rules,sv=b.savings;
  const span=t=>`${t} ngày sống`;
  const opts=R.terms.map(t=>`<option value="${t}">${esc(b.term_names[String(t)])} · ${pct(t?R.term_rate[String(t)]:R.demand_rate)}/năm</option>`).join('');
  const table=`<table class="bk-rates"><caption>Biểu lãi suất tiết kiệm (theo năm trong game)</caption><thead><tr><th scope="col">Kỳ hạn</th><th scope="col">Lãi/năm</th><th scope="col">1.000 xu nhận</th></tr></thead><tbody>
    ${R.terms.map(t=>{const r=t?R.term_rate[String(t)]:R.demand_rate;return `<tr><td>${esc(b.term_names[String(t)])}${t?`<small class="bk-hint"> · ${span(t)}</small>`:''}</td><td>${pct(r)}</td><td>${t?`${fmt(1000+termGain(1000,r,t,R))} xu khi đáo hạn`:`≈ ${(1000*R.demand_bp/10000).toLocaleString('vi-VN')} xu/ngày`}</td></tr>`;}).join('')}</tbody></table>`;
  const terms=sv.terms.map(t=>{const p=Math.round(Math.min(t.term,t.term-t.days_left)*100/t.term);return `<li class="bk-term"><div><b>${esc(t.name)} · ${xu(t.amount)}</b><small>Gửi Ngày ${t.start}, đáo hạn ${onDay(t.due)} · lãi ${esc(t.rate_text)}${t.renew?' · tự tái tục':''}</small>
    <div class="bk-bar good" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${p}" aria-label="Đã gửi ${p}% kỳ hạn"><i style="width:${p}%"></i></div>
    <small>Lãi đã tích lũy <b>${xu(t.accrued)}</b> · đến hạn nhận <b>${xu(t.value)}</b>. Rút trước hạn hôm nay chỉ được lãi ${xu(t.early)}.</small></div>${btn('Tất toán sớm','unsaveTerm',{id:t.id},'ghost small')}</li>`;}).join('');
  return `<section class="bk-hero soft"><small>Tổng tiết kiệm</small><strong class="bk-balance">${xu(sv.total)}</strong></section>
    <section class="bk-card"><h3>Gửi tiết kiệm</h3><div class="bk-move">
      <label class="bk-field"><span>Số xu</span><input id="bk-save-amt" type="number" inputmode="numeric" min="1" placeholder="Ít nhất ${R.save_min} xu nếu có kỳ hạn"></label>
      <label class="bk-field"><span>Kỳ hạn</span><select id="bk-term">${opts}</select></label>
      <label class="bk-field"><span>Lấy từ</span><select id="bk-save-src"><option value="acc">Tài khoản thanh toán</option><option value="cash">Tiền mặt trong ví</option></select></label>
      <label class="bk-toggle"><input type="checkbox" id="bk-renew"><span>Tới hạn tự tái tục (gốc và lãi gửi tiếp kỳ mới)</span></label></div>
      <div class="bk-actions">${btn('Gửi tiết kiệm','save',{},'primary')}</div>${table}
      <p class="bk-hint">1 tháng = ${R.month_days} ngày sống, 1 năm = ${R.year_days} ngày sống. Rút trước hạn chỉ được lãi không kỳ hạn.</p></section>
    <section class="bk-card bk-house-link"><h3>🏠 Tiết kiệm mua nhà</h3><p class="bk-hint">Còn thiếu bao nhiêu để trả trước 30%?</p><div class="bk-actions">${btn('Nhà của bạn','house',{},'ghost')}</div></section>
    <section class="bk-card"><h3>Không kỳ hạn · ${xu(sv.demand)}</h3><p class="bk-hint">Lãi ${pct(R.demand_rate)}/năm, cộng mỗi ngày (~${(sv.daily_milli/1000).toLocaleString('vi-VN',{maximumFractionDigits:3})} xu/ngày).</p>
      ${sv.demand?`<div class="bk-move"><label class="bk-field"><span>Rút về tài khoản</span><input id="bk-demand-out" type="number" inputmode="numeric" min="1" max="${sv.demand}" placeholder="Tối đa ${sv.demand}"></label></div><div class="bk-actions">${btn('Rút','unsaveDemand',{},'ghost')}</div>`:''}</section>
    <section class="bk-card"><h3>Sổ có kỳ hạn</h3>${terms?`<ul class="bk-list">${terms}</ul>`:'<p class="bk-hint">Chưa có sổ nào.</p>'}</section>`;
}

function card(b){
  const R=b.rules,c=b.card;
  const fees=`<section class="bk-card"><table class="bk-rates flat"><caption>Biểu phí thẻ</caption><tbody>
    <tr><th scope="row">Lãi khi không trả hết sao kê</th><td>${pct(R.card_bp)}/ngày trên dư nợ còn lại</td></tr>
    <tr><th scope="row">Trả tối thiểu</th><td>${R.card_min_pct}% sao kê, ít nhất ${xu(R.card_min_floor)}</td></tr>
    <tr><th scope="row">Phí trễ hạn</th><td>${xu(R.card_late_fee)} và giảm điểm tín dụng</td></tr>
    <tr><th scope="row">Ứng tiền mặt</th><td>${R.cash_fee_pct}% (ít nhất ${xu(R.cash_fee_min)}), lãi từ ngày đầu, tối đa ${R.cash_share}% hạn mức</td></tr>
    <tr><th scope="row">Sao kê · hạn trả</th><td>Mỗi ${R.card_cycle} ngày · ${R.card_grace} ngày sau sao kê</td></tr></tbody></table></section>`;
  const pref=`<section class="bk-card"><h3>Khi mua sắm cá nhân</h3><p class="bk-hint">Học phí, đi cửa sau… trả bằng gì khi bạn không chọn riêng.</p>
    <div class="bk-move"><label class="bk-field wide"><span>Cách trả mặc định</span><select id="bk-pref">${Object.entries(b.prefs).map(([k,v])=>`<option value="${k}"${b.pref===k?' selected':''}>${esc(v)}</option>`).join('')}</select></label></div>
    <div class="bk-actions">${btn('Lưu','pref',{},'ghost small')}</div></section>`;
  if(!c){
    const o=b.card_offer;
    return `<section class="bk-card bk-center"><div class="bk-plastic ghost" aria-hidden="true"><div class="bk-plastic-top"><span class="bk-plastic-logo">${LOGO}<b>NGÂN HÀNG PHỐ</b></span><span class="bk-plastic-kind">CREDIT</span></div><span class="bk-chip"></span><div class="bk-plastic-no">•••• •••• •••• ••••</div></div>
      <h3>Thẻ tín dụng Ngân hàng Phố</h3><p>Quẹt trước, trả sau. Trả hết dư nợ sao kê trước hạn thì không mất đồng lãi nào.</p>
      <p class="bk-alert ${o.ok?'good':'warn'}">${o.ok?`Dự kiến được duyệt hạn mức <b>${xu(o.limit)}</b>.`:esc(o.text)}</p>
      <p class="bk-hint">Hạn mức dựa trên điểm tín dụng (${b.score.value}) và thu nhập trung bình ${xu(b.income.avg)}/ngày trong ${b.income.window} ngày gần nhất. Mỗi lần nộp hồ sơ, điểm giảm nhẹ.</p>
      <div class="bk-actions center">${btn('Nộp hồ sơ mở thẻ','cardApply',{},'primary big')}</div></section>${fees}${pref}`;
  }
  const st=c.stmt;
  const stmt=st?`<div class="bk-stmt ${c.past_due?'late':''}"><h4>Sao kê kỳ ${st.n} · Ngày ${st.day}</h4>
      <dl><div><dt>Dư nợ sao kê</dt><dd>${xu(st.amount)}</dd></div><div><dt>Tối thiểu</dt><dd>${xu(st.min)}</dd></div><div><dt>Đã trả</dt><dd>${xu(st.paid)}</dd></div>
      <div><dt>Hạn thanh toán</dt><dd>${st.done?`Ngày ${st.due}`:onDay(st.due)}</dd></div></dl>
      ${c.past_due?`<p class="bk-alert bad">Quá hạn ${xu(c.past_due)}. Thẻ tạm khóa tới khi trả khoản này.</p>`:st.left&&!st.done?`<p class="bk-hint">Trả hết ${xu(st.left)} trước hạn để không mất lãi. Chỉ trả tối thiểu thì phần còn lại chịu lãi ${pct(R.card_bp)}/ngày.</p>`:st.amount?'<p class="bk-hint">Kỳ này đã xong. 👍</p>':''}</div>`
    :`<p class="bk-hint">Sao kê đầu tiên vào ${onDay(c.next_stmt)}.</p>`;
  return `<section class="bk-card">${cardVisual(c,b.holder)}${limitBar(c)}${c.locked?`<p class="bk-alert bad">${esc(c.locked)}</p>`:''}
      ${st?`<p class="bk-hint">Sao kê tiếp theo: ${onDay(c.next_stmt)}.</p>`:''}${stmt}</section>
    <section class="bk-card"><h3>Thanh toán thẻ</h3><div class="bk-move">
      <label class="bk-field"><span>Trả từ</span><select id="bk-card-src"><option value="acc">Tài khoản (${xu(b.balance)})</option><option value="cash">Tiền mặt (${xu(b.wallet)})</option></select></label>
      <label class="bk-field"><span>Số khác</span><input id="bk-card-amt" type="number" inputmode="numeric" min="1" max="${c.bal}" placeholder="Số xu"></label></div>
      <div class="bk-actions">${btn('Trả tối thiểu','cardPay',{what:'min'},'ghost',(Math.max(c.past_due,st?.min_left||0)?'':' disabled'))}${btn('Trả hết sao kê','cardPay',{what:'stmt'},'primary',st?.left?'':' disabled')}${btn('Trả toàn bộ dư nợ','cardPay',{what:'all'},'ghost',c.bal?'':' disabled')}${btn('Trả số khác','cardPay',{what:'custom'},'ghost small')}</div>
      <div class="bk-move"><label class="bk-field wide"><span>Tự động trả từ tài khoản vào ngày đến hạn</span><select id="bk-autopay">${Object.entries(b.autopays).map(([k,v])=>`<option value="${k}"${c.autopay===k?' selected':''}>${esc(v)}</option>`).join('')}</select></label></div>
      <div class="bk-actions">${btn('Lưu cách tự động trả','autopay',{},'ghost small')}</div></section>
    <section class="bk-card"><h3>Ứng tiền mặt tại ATM</h3><p class="bk-hint">Còn ứng được ${xu(Math.min(c.cash_room,c.available))}. Phí ${R.cash_fee_pct}% và lãi tính ngay, nên chỉ dùng khi thật cần.</p>
      <div class="bk-move"><label class="bk-field"><span>Số xu</span><input id="bk-cash-amt" type="number" inputmode="numeric" min="1" placeholder="Ví dụ 20"></label></div>
      <div class="bk-actions">${btn('Ứng tiền mặt','cardCash',{},'ghost')}</div></section>${fees}${pref}
    <div class="bk-actions">${btn('Hủy thẻ','cardClose',{},'ghost small danger',c.bal?' disabled':'')}</div>`;
}

function previewHTML(){
  const b=B(),L=loanPreview();
  if(!L.rows)return `<p class="bk-alert warn">${esc(L.why)}</p>`;
  return `${L.warn?`<p class="bk-alert warn">${esc(L.warn)}</p>`:''}<table class="bk-rates bk-sched"><caption>Lịch trả nợ dự kiến</caption><thead><tr><th scope="col">Kỳ</th><th scope="col">Ngày</th><th scope="col">Gốc</th><th scope="col">Lãi</th><th scope="col">Phải trả</th></tr></thead>
    <tbody>${L.rows.map(r=>`<tr><td>${r.k}</td><td>${r.due}</td><td>${fmt(r.principal)}</td><td>${fmt(r.interest)}</td><td><b>${fmt(r.amount)}</b></td></tr>`).join('')}</tbody>
    <tfoot><tr><th scope="row" colspan="3">Tổng</th><td>${fmt(L.interest)}</td><td><b>${fmt(L.total)}</b></td></tr></tfoot></table>
    <p class="bk-sum">Tổng tiền lãi: <b>${xu(L.interest)}</b> · lãi ${pct(b.rules.loan_bp[S.loan.kind])}/kỳ ${b.rules.loan_period} ngày</p>`;
}
function loan(b){
  const R=b.rules,o=b.loan_offers[S.loan.kind]||{};
  if(!S.loan.amount&&o.max)S.loan.amount=Math.min(o.max,Math.max(R.loan_min,Math.floor(o.max/2/10)*10));
  if(S.loan.kind==='shop'&&!b.places[S.loan.career])S.loan.career=Object.keys(b.places)[0]||'';
  const active=(b.loans||[]).map(ln=>`<section class="bk-card ${ln.overdue?'bk-late':''}"><h3>${ln.emoji} ${esc(ln.name)} · ${xu(ln.principal)}</h3>
    <p class="bk-hint">Ký Ngày ${ln.start}${ln.place?` · vốn vào ${esc(ln.place)}`:''} · lãi ${pct(ln.bp)}/kỳ · còn phải trả <b>${xu(ln.left)}</b></p>
    ${ln.overdue?`<p class="bk-alert bad">Quá hạn ${xu(ln.overdue)} (đã gồm phí phạt). Nộp tiền vào tài khoản là hệ thống tự trích mỗi sáng.</p>`:''}
    <table class="bk-rates bk-sched"><thead><tr><th scope="col">Kỳ</th><th scope="col">Ngày</th><th scope="col">Phải trả</th><th scope="col">Trạng thái</th></tr></thead><tbody>
    ${ln.rows.map(r=>`<tr class="${r.paid>=r.amount?'paid':r.due<=b.life_day?'late':''}"><td>${r.k}</td><td>${r.due}</td><td>${fmt(r.amount)}${r.fee?` <small>(phạt ${fmt(r.fee)})</small>`:''}</td><td>${r.paid>=r.amount?(r.late?'Đã trả trễ':'Đã trả'):r.due<=b.life_day?'Quá hạn':'Chờ'}</td></tr>`).join('')}</tbody></table>
    <div class="bk-move"><label class="bk-field"><span>Trả từ</span><select id="bk-loan-src-${esc(ln.id)}"><option value="acc">Tài khoản (${xu(b.balance)})</option><option value="cash">Tiền mặt (${xu(b.wallet)})</option></select></label></div>
    <div class="bk-actions">${btn(ln.overdue?'Trả khoản quá hạn':'Trả trước kỳ tới','loanPay',{id:ln.id},ln.overdue?'primary':'ghost')}${btn(`Tất toán sớm · ${xu(ln.payoff.total)}`,'loanClose',{id:ln.id},'ghost')}</div>
    <p class="bk-hint">Tiền trả góp tự trích từ tài khoản (thiếu thì lấy thêm tiền mặt) vào sáng ngày đến hạn. Tất toán sớm mất phí ${R.early_fee_pct}% gốc còn lại (ít nhất ${xu(R.early_fee_min)}).</p></section>`).join('');
  const kinds=Object.entries(b.loan_kinds).map(([k,v])=>`<option value="${k}"${S.loan.kind===k?' selected':''}>${v.emoji} ${esc(v.name)}</option>`).join('');
  const places=S.loan.kind==='shop'?`<label class="bk-field"><span>Tiệm nhận vốn</span><select name="career">${Object.entries(b.places).map(([k,v])=>`<option value="${k}"${S.loan.career===k?' selected':''}>${esc(v)}</option>`).join('')||'<option value="">Chưa có tiệm bạn làm chủ</option>'}</select></label>`:'';
  const form=`<section class="bk-card"><h3>Vay mới</h3><p class="bk-hint">${esc(b.loan_kinds[S.loan.kind].desc)}</p>
    <div class="bk-move" data-bk-loan>
      <label class="bk-field"><span>Loại vay</span><select name="kind">${kinds}</select></label>
      <label class="bk-field"><span>Số tiền${o.max?` (tối đa ${xu(o.max)})`:''}</span><input id="bk-loan-amt" name="amount" type="number" inputmode="numeric" min="${R.loan_min}" max="${o.max||R.loan_min}" step="10" value="${S.loan.amount||''}"></label>
      <label class="bk-field"><span>Kỳ hạn</span><select name="term">${R.loan_terms.map(t=>`<option value="${t}"${S.loan.term===t?' selected':''}>${t} ngày · ${t/R.loan_period} kỳ</option>`).join('')}</select></label>${places}</div>
    ${o.ok?'':`<p class="bk-alert warn">${esc(o.text)}</p>`}
    <div class="bk-loan-preview">${o.ok?previewHTML():''}</div>
    <p class="bk-hint">Hạn mức dựa trên thu nhập ${xu(b.income.avg)}/ngày và điểm ${b.score.value}. Tiền trả góp mỗi kỳ (cộng các khoản đang vay) không quá ${R.dti_pct}% thu nhập một tuần. Nộp hồ sơ làm điểm giảm nhẹ.</p>
    <div class="bk-actions">${btn('Xem lại & ký hợp đồng','loanSign',{},'primary',o.ok?'':' disabled')}</div></section>`;
  const H=J().home,HL=H?.own?.loan;
  const house=HL?`<section class="bk-card ${HL.overdue?'bk-late':''}"><h3>🏠 Vay mua nhà · ${xu(HL.principal)}</h3><p class="bk-hint">Lãi ${esc(HL.rate_text)} · đã trả ${HL.paid_rows}/${HL.rows.length} kỳ · còn phải trả <b>${xu(HL.left)}</b>${HL.next?` · kỳ tới ${onDay(HL.next.due)}`:''}</p>${HL.overdue?`<p class="bk-alert warn">Chậm ${xu(HL.overdue)}.</p>`:''}<div class="bk-actions">${btn('Xem ở Nhà của bạn','house',{},'ghost')}</div></section>`
    :`<section class="bk-card"><h3>🏠 Vay mua nhà</h3><p class="bk-hint">Trả trước ít nhất 30% giá nhà, phần còn lại vay tới 3 năm, trả góp mỗi tháng trong game.</p><div class="bk-actions">${btn('Nhà của bạn','house',{},'ghost')}</div></section>`;
  return (active||(HL?'':`<section class="bk-card"><p class="bk-hint">Bạn không có khoản vay nào. 🎈</p></section>`))+house+form;
}
