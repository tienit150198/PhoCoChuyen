/** 🏠 Nhà của bạn: rent a better room, buy a home, a mortgage at Ngân hàng Phố (story mode).
 * Every rule and number lives in game/housing.py; this file renders api.state.journey.home and sends
 * `jr_home_*` commands. The only maths mirrored here is the mortgage schedule (housing.schedule, on top of
 * bank.installment), so the contract shows the exact installments before signing; the server checks the
 * total interest the player saw. Its own dialog (like the bank), opened with data-action="house" from the
 * journey card, the bank's savings/loan tabs and the guide. Styles: /css/bank.css + /css/house.css. */
import {icon,escapeHTML as esc} from '../icons.js';

const S={dlg:null,env:null,view:'home',busy:false,flash:null,buy:{kind:'',down:0,months:36,joint:0},joint:null,jointAt:0,listening:false};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const pct=bp=>`${(bp/100).toLocaleString('vi-VN',{maximumFractionDigits:2})}%`;
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,op,data={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-hs="${op}"${attrs(data)}${S.busy?' disabled':''}${extra}>${label}</button>`;
const J=()=>S.env?.api?.state?.journey||{};
const V=()=>J().home||{};
const onDay=n=>{const d=n-(J().life_day||0);return d===0?`hôm nay (Ngày ${n})`:d===1?`Ngày ${n} (ngày mai)`:d<0?`Ngày ${n} (đã qua)`:`Ngày ${n} (còn ${d} ngày)`;};
const months=(m)=>m%12===0?`${m/12} năm (${m} tháng)`:`${m} tháng`;

/* ---- mortgage maths: a mirror of game/bank.py (_interest, _fits, installment) and game/housing.py (schedule) ---- */
const interest=(rest,bp)=>Math.floor((rest*bp+5000)/10000);
function fits(p,bp,n,pay){let rest=p;for(let i=0;i<n-1;i++){rest-=pay-interest(rest,bp);if(rest<=0)return true;}return rest+interest(rest,bp)<=pay;}
function installment(p,bp,n){let lo=Math.max(1,Math.ceil(p/n)),hi=p*2+10;while(lo<hi){const mid=Math.floor((lo+hi)/2);if(fits(p,bp,n,mid))hi=mid;else lo=mid+1;}return lo;}
export function schedule(p,rate,n,start,period){
  const bp=Math.floor(rate/12),pay=installment(p,bp,n),rows=[];let rest=p;
  for(let k=1;k<=n;k++){const i=interest(rest,bp),part=k===n?rest:Math.max(0,Math.min(rest,pay-i));rows.push({k,due:start+period*k,principal:part,interest:i,amount:part+i});rest-=part;}
  return rows;
}

/* ---- styles on first use ---- */
let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=Promise.all([link('/css/bank.css','bk-css'),link('/css/house.css','hs-css')]);

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium bk-sheet hs-sheet';d.setAttribute('aria-labelledby','hs-title');
  d.innerHTML='<div class="hs-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-hs]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.hs,el.dataset);
  });
  d.addEventListener('input',e=>{if(e.target.closest('[data-hs-buy]'))onBuyField(e.target,false);});
  d.addEventListener('change',e=>{if(e.target.closest('[data-hs-buy]'))onBuyField(e.target,true);});
  d.addEventListener('submit',e=>e.preventDefault());
  d.addEventListener('close',()=>{S.flash=null;S.view='home';});
  S.dlg=d;return d;
}
export async function openHouse(env,kind){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';env.api.addEventListener('state',()=>{const key=JSON.stringify([J().wallet,J().home,J().bank?.balance]);if(key===seen)return;seen=key;if(S.dlg?.open&&!S.busy)render();});
  }
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();
  if(kind&&(V().market||[]).some(m=>m.id===kind))startBuy(kind);else S.view='home';
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();loadJoint();
}
export async function houseAction(action,data,el,env){
  if(action!=='house')return false;
  await openHouse(env,data?.kind);return true;
}

/* The couple's joint fund (game/couple.py via GET /api/marriage). Loading it also lets the server bring
   the spouse into a home bought since the last visit (couple.on_load). */
async function loadJoint(force=false){
  if(!force&&Date.now()-S.jointAt<15000)return;
  S.jointAt=Date.now();
  try{const v=await S.env.api.json('/api/marriage');S.joint=v?.home?.fund?{balance:v.home.fund.balance,partner:v.couple?.partner?.name||''}:null;}
  catch{S.joint=null;}
  if(S.dlg){if(S.joint)S.dlg.dataset.joint=String(S.joint.balance);else delete S.dlg.dataset.joint;}
  if(S.dlg?.open&&!S.busy)render();
}

async function send(action,payload={}){
  const {api}=S.env;S.busy=true;render();
  try{
    const r=await api.command(action,payload);
    const extra=(r.effects||[]).filter(Boolean);
    S.flash={text:[r.message,...extra].filter(Boolean).join(' '),kind:r.approved===false?'warn':'good'};
    return r;
  }catch(e){S.flash={text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;render();S.dlg?.querySelector('.hs-body')?.scrollTo?.(0,0);}
}
const ask=(title,msg,label,money)=>S.env.confirmAction(title,msg,label,money);  // money: {cost,pocket} → "còn thiếu" (v4/money.js)
const FROM_BANK=['account','wallet'];   // housing takes the account first, the rest in cash

function startBuy(kind){
  const m=(V().market||[]).find(x=>x.id===kind);if(!m)return;
  const ready=(V().have?.ready||0)+(S.joint?.balance||0);
  S.view='buy';S.buy={kind,down:Math.min(m.price,Math.max(m.down_min,Math.floor(Math.max(0,ready-m.fee)/10)*10)),months:36,joint:0};
}

async function onClick(op,data){
  const v=V(),R=v.rules||{};
  switch(op){
    case'close':S.dlg.close();return;
    case'back':S.view='home';S.flash=null;render();return;
    case'look':startBuy(data.kind);S.flash=null;render();S.dlg.querySelector('.hs-body')?.scrollTo?.(0,0);return;
    case'bank':S.dlg.close();(await import('./bank.js')).openBank(S.env,data.tab||'save');return;
    case'rent':{const m=v.market.find(x=>x.id===data.kind);if(!m)return;
      if(await ask(`Thuê ${m.name.toLowerCase()}?`,`Đặt cọc ${xu(m.deposit)} (lấy từ tài khoản trước, thiếu thì tiền mặt), trả lại khi dọn đi. Tiền phòng ${xu(m.rent)}/ngày thay cho tiền phòng ở gác Bà Tám (${xu(v.attic_rent)}/ngày).`,`Thuê · cọc ${xu(m.deposit)}`,{cost:m.deposit,pocket:FROM_BANK}))send('jr_home_rent',{kind:m.id,confirm:true});return;}
    case'leave':if(await ask('Trả phòng trọ?',`Nhận lại ${xu(v.rent?.deposit)} tiền cọc vào ví và về lại căn gác nhà Bà Tám.`,'Trả phòng'))send('jr_home_leave',{confirm:true});return;
    case'sign':{const P=preview();if(!P.ok){S.flash={text:P.why,kind:'warn'};render();return;}
      const m=P.m,loan=P.loan,b=S.buy;
      const body=`Giá ${xu(m.price)}. Trả trước ${xu(b.down)} + phí công chứng, sang tên ${xu(m.fee)} = ${xu(P.pay)}`+(b.joint?`, trong đó ${xu(b.joint)} từ quỹ chung`:'')+'. '
        +(loan?`Vay ${xu(loan)} trong ${months(b.months)}, lãi ${pct(v.offer.rate)}/năm: mỗi kỳ ${xu(P.rows[0].amount)}, cứ ${R.month_days} ngày một kỳ, tổng lãi ${xu(P.interest)}. Ngân hàng sẽ tra cứu hồ sơ tín dụng.`:'Trả đủ một lần, không vay.');
      if(await ask(`Mua ${m.name.toLowerCase()}?`,body,loan?'Ký hợp đồng mua nhà':`Mua · ${xu(P.pay)}`,{cost:Math.max(0,P.pay-(b.joint||0)),pocket:FROM_BANK})){
        const r=await send('jr_home_buy',{kind:m.id,down:b.down,confirm:true,...(b.joint?{joint:b.joint}:{}),...(loan?{months:b.months,total_interest:P.interest}:{})});
        if(r&&r.approved!==false){S.view='home';S.jointAt=0;loadJoint(true);render();}
      }return;}
    case'pay':{const L=v.own?.loan;if(!L)return;const amount=L.overdue||(L.next?L.next.amount-L.next.paid:0);
      if(await ask(L.overdue?`Trả ${xu(amount)} đang quá hạn?`:`Trả trước kỳ ${L.next.k}?`,'Lấy từ tài khoản ngân hàng trước, thiếu thì tiền mặt.',`Trả · ${xu(amount)}`,{cost:amount,pocket:FROM_BANK}))send('jr_home_pay',{});return;}
    case'payoff':{const o=v.own?.loan?.payoff;if(!o)return;
      if(await ask('Tất toán khoản vay mua nhà?',`Gốc còn lại ${xu(o.principal)}${o.overdue?`, khoản quá hạn ${xu(o.overdue)}`:''}, lãi những ngày đã dùng ${xu(o.interest)}, phí trả trước hạn ${xu(o.fee)}. Tổng ${xu(o.total)}. Bạn bớt được ${xu(Math.max(0,o.saved))} tiền lãi.`,`Tất toán · ${xu(o.total)}`,{cost:o.total,pocket:FROM_BANK}))send('jr_home_payoff',{confirm:true});return;}
    case'sell':{const o=v.own;if(!o)return;const sl=o.sell;
      if(await ask(`Bán ${o.name.toLowerCase()}?`,`Giá thị trường hôm nay ${xu(sl.value)}. Phí môi giới và thuế ${xu(sl.fee)}${sl.payoff?`, trả hết nợ vay ${xu(sl.payoff)}`:''}. Bạn nhận ${xu(sl.get)} vào ${v.have?.bank?'tài khoản ngân hàng':'ví'}${v.married?'. Người ấy sẽ dọn ra cùng bạn':''}.`,`Bán · nhận ${xu(sl.get)}`))send('jr_home_sell',{confirm:true,value:sl.value});return;}
  }
}

function onBuyField(el,full){
  const k=el.name,m=(V().market||[]).find(x=>x.id===S.buy.kind);if(!m)return;
  if(k==='down')S.buy.down=Math.max(0,Math.floor(Number(el.value)||0));
  else if(k==='months')S.buy.months=Number(el.value);
  else if(k==='joint')S.buy.joint=Math.max(0,Math.floor(Number(el.value)||0));
  else if(k==='all'){S.buy.down=el.checked?m.price:m.down_min;full=true;}
  const box=S.dlg.querySelector('.hs-preview');
  if(box&&!full){box.innerHTML=previewHTML();return;}
  render();
}
function preview(){
  const v=V(),b=S.buy,m=(v.market||[]).find(x=>x.id===b.kind),R=v.rules||{};
  if(!m)return {ok:false,why:'Chọn một căn nhà nhé.'};
  const loan=m.price-b.down,pay=b.down+m.fee,have=v.have||{},joint=b.joint||0;
  const out={m,loan,pay,rows:null,interest:0};
  if(b.down<m.down_min||b.down>m.price)return {...out,ok:false,why:`Trả trước từ ${xu(m.down_min)} (${R.down_pct}% giá nhà) tới ${xu(m.price)}.`};
  if(loan&&loan<R.loan_min)return {...out,ok:false,why:`Vay ít nhất ${xu(R.loan_min)}, hoặc trả đủ luôn nhé.`};
  if(joint>pay)return {...out,ok:false,why:`Quỹ chung chỉ cần góp tối đa ${xu(pay)}.`};
  if(joint&&joint>(S.joint?.balance||0))return {...out,ok:false,why:`Quỹ chung chỉ còn ${xu(S.joint?.balance||0)}.`};
  const short=pay-joint-have.ready;
  if(short>0)return {...out,ok:false,short,why:`Còn thiếu ${xu(short)} cho khoản trả trước và phí.`};
  if(loan){
    const o=v.offer||{};
    if(!o.ok)return {...out,ok:false,why:o.text||'Ngân hàng chưa duyệt vay mua nhà.'};
    const rows=schedule(loan,o.rate,b.months,J().life_day,R.month_days);
    const int=rows.reduce((x,r)=>x+r.interest,0);
    if(rows[0].amount>o.room)return {...out,rows,interest:int,ok:false,why:`Mỗi kỳ ${xu(rows[0].amount)} vượt ${R.dti_pct}% thu nhập một tháng (${xu(o.room)}): ngân hàng sẽ không duyệt. Trả trước nhiều hơn hoặc vay dài hơn nhé.`};
    return {...out,ok:true,rows,interest:int};
  }
  return {...out,ok:true};
}

/* ---- rendering ---- */
function keepFocus(fn){
  const a=document.activeElement,id=a&&S.dlg?.contains(a)?a.id:'',pos=id&&'selectionStart' in a?a.selectionStart:null;
  const top=S.dlg?.querySelector('.hs-body')?.scrollTop;
  fn();
  if(id){const el=S.dlg.querySelector('#'+CSS.escape(id));if(el){el.focus({preventScroll:true});try{if(pos!=null)el.setSelectionRange(pos,pos);}catch{/* number inputs */}}}
  if(top!=null){const body=S.dlg.querySelector('.hs-body');if(body)body.scrollTop=top;}
}
function render(){
  if(!S.dlg)return;
  keepFocus(()=>{S.dlg.querySelector('.hs-root').innerHTML=page();});
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
function head(){
  const v=V();
  return `<header class="sheet-head bk-head hs-head">${S.view==='buy'?`<button class="icon-btn" type="button" data-hs="back" aria-label="Quay lại">${icon('back',21)}</button>`:'<span class="hs-logo" aria-hidden="true">🏠</span>'}
    <div class="grow"><span class="eyebrow">AN CƯ · NGÀY SỐNG ${fmt(v.life_day)}</span><h2 id="hs-title">Nhà của bạn</h2><p>${v.place?.name?`Đang ở: ${esc(v.place.name)}`:'Thuê phòng, để dành, mua nhà'}</p></div>
    <button class="icon-btn" type="button" data-hs="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
}
const flash=()=>`<p class="bk-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
function page(){
  const v=V();
  if(!v.story)return head()+`<div class="sheet-body bk hs-body"><section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🏠</div><h3>Nhà cửa chỉ có trong chế độ hành trình</h3><p>Vào hành trình để thuê phòng, để dành và mua nhà cho nhân vật của bạn.</p></section></div>`;
  return head()+`<div class="sheet-body bk hs-body">${flash()}${S.view==='buy'?buyView(v):homeView(v)}</div>`;
}

/* Wallet, account and Quỹ chung are in the 💰 chip on the header (v4/money.js); savings in the 🐷 card. */
function moneyStrip(v){
  const h=v.have||{};
  return h.debt?`<p class="bk-alert warn">👛 Ví đang nợ ${xu(h.debt)}.</p>`:'';
}

function placeCard(v){
  const p=v.place||{},c=p.cost||{};
  const costLine=p.where_id==='own'||p.where_id==='shared'?`Không còn tiền phòng: chỉ điện nước ${xu(c.rent)}/ngày, cơm nước ${xu(c.meals)}/ngày.`
    :`Tiền phòng ${xu(c.rent)}/ngày, cơm nước ${xu(c.meals)}/ngày.`;
  const who=p.where_id==='shared'?`<p class="hs-tag">💞 Nhà chung với ${esc(p.with)}</p>`:p.where_id==='own'?'<p class="hs-tag">🔑 Nhà đứng tên bạn</p>':p.where_id==='rent'?'<p class="hs-tag">🧾 Đang thuê</p>':'';
  let actions='';
  if(p.where_id==='rent')actions=`<div class="bk-actions">${btn('Trả phòng, nhận lại cọc','leave',{},'ghost')}</div>`;
  const comfort=p.comfort?`<p class="bk-hint">😊 Mỗi sáng tinh thần +${p.comfort}${v.own?.loan?.late?' (tạm dừng khi đang trễ hạn trả góp)':''}.</p>`:'<p class="bk-hint">Có chỗ ở riêng thì mỗi sáng tinh thần khá hơn một chút.</p>';
  return `<section class="bk-card hs-place ${esc(p.where_id||'')}"><div class="hs-place-top"><span class="hs-emoji" aria-hidden="true">${p.emoji||'🏚️'}</span><div class="grow"><small>Nơi bạn đang ở</small><h3>${esc(p.name)}</h3><p class="bk-hint">${esc(p.where||'')}</p></div></div>
    ${who}<p>${esc(p.desc||'')}</p><p class="hs-cost">${costLine}</p>${comfort}${actions}</section>`;
}

function loanCard(v){
  const o=v.own,L=o?.loan;if(!L)return '';
  const day=v.life_day,R=v.rules;
  const rows=L.rows.map(r=>`<tr class="${r.paid>=r.amount?'paid':r.due<=day?'late':''}"><td>${r.k}</td><td>${r.due}</td><td>${fmt(r.amount)}${r.fee?` <small>(phạt ${fmt(r.fee)})</small>`:''}</td><td>${r.paid>=r.amount?(r.late?'Đã trả trễ':'Đã trả'):r.due<=day?(r.late?'Trễ hạn':'Ân hạn'):'Chờ'}</td></tr>`).join('');
  const done=L.paid_rows,pctDone=Math.round(done*100/L.rows.length);
  return `<section class="bk-card ${L.overdue?'bk-late':''}"><h3>📝 Vay mua nhà · ${xu(L.principal)}</h3>
    <p class="bk-hint">Lãi ${esc(L.rate_text)} · ${L.months} kỳ, cứ ${R.month_days} ngày một kỳ · còn phải trả <b>${xu(L.left)}</b></p>
    <div class="bk-bar good" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pctDone}" aria-label="Đã trả ${done} trên ${L.rows.length} kỳ"><i style="width:${pctDone}%"></i></div>
    <p class="bk-hint">Đã trả ${done}/${L.rows.length} kỳ.${L.next?` Kỳ tới: ${xu(L.next.amount-L.next.paid)} vào ${onDay(L.next.due)}.`:''}</p>
    ${L.overdue?`<p class="bk-alert ${L.late?'bad':'warn'}">${L.late?'Đang trễ hạn':'Đang trong thời gian ân hạn'}: ${xu(L.overdue)}. ${L.late?'Tinh thần mỗi sáng tạm không được cộng.':`Chưa tính phí trong ${R.grace} ngày đầu.`} Nộp tiền vào tài khoản là ngân hàng tự trích mỗi sáng.</p>`:''}
    <details class="hs-sched"><summary>Lịch trả góp</summary><table class="bk-rates bk-sched"><thead><tr><th scope="col">Kỳ</th><th scope="col">Ngày</th><th scope="col">Phải trả</th><th scope="col">Trạng thái</th></tr></thead><tbody>${rows}</tbody></table></details>
    <div class="bk-actions">${btn(L.overdue?'Trả khoản quá hạn':'Trả trước kỳ tới','pay',{},L.overdue?'primary':'ghost')}${btn(`Tất toán sớm · ${xu(L.payoff.total)}`,'payoff',{},'ghost')}</div>
    <p class="bk-hint">Tiền trả góp tự trích từ tài khoản (thiếu thì lấy thêm tiền mặt) vào sáng ngày đến hạn. Thiếu tiền thì có ${R.grace} ngày ân hạn không tính phí; sau đó phạt ${R.late_pct}% kỳ đó và giảm điểm tín dụng. Ngân hàng không bao giờ lấy nhà của bạn.</p></section>`;
}

function ownCard(v){
  const o=v.own;if(!o)return '';
  const grow=o.value-o.price;
  return `<section class="bk-card"><h3>${o.emoji} Căn nhà của bạn</h3>
    <dl class="hs-facts"><div><dt>Mua</dt><dd>Ngày ${o.day} · ${xu(o.price)}</dd></div><div><dt>Giá thị trường hôm nay</dt><dd>${xu(o.value)}${grow>0?` <small class="up">(+${fmt(grow)})</small>`:''}</dd></div>
    <div><dt>Điện nước</dt><dd>${xu(o.upkeep)}/ngày</dd></div><div><dt>Bán ngay thì nhận</dt><dd>${xu(o.sell.get)}</dd></div></dl>
    <p class="bk-hint">Giá nhà tăng khoảng ${pct(v.rules.grow_rate)} mỗi năm trong game. Bán mất ${v.rules.sell_fee_pct}% phí môi giới và thuế${o.loan?', tiền bán trả hết nợ vay trước':''}.</p>
    <div class="bk-actions">${btn('Bán nhà','sell',{},'ghost small danger')}</div></section>`;
}

function marketCard(v,m){
  const h=v.have||{},owned=!!v.own;
  if(m.kind==='rent'){
    const here=v.rent?.kind===m.id;
    return `<li class="hs-home"><div class="hs-home-top"><span class="hs-emoji" aria-hidden="true">${m.emoji}</span><div class="grow"><b>${esc(m.name)}</b><small>${esc(m.where)} · cho thuê</small></div><strong class="hs-price">${xu(m.rent)}<small>/ngày</small></strong></div>
      <p>${esc(m.desc)}</p><ul class="hs-points"><li>Cọc ${xu(m.deposit)}, trả lại khi dọn đi</li><li>Tinh thần +${m.comfort} mỗi sáng</li><li>${m.per_day>0?`Đắt hơn gác Bà Tám ${xu(m.per_day)}/ngày`:'Rẻ hơn hoặc bằng gác Bà Tám'}</li></ul>
      ${here?'<p class="bk-alert good">Bạn đang thuê phòng này.</p>':owned?'':m.missing?`<p class="bk-alert warn">Còn thiếu ${xu(m.missing)} tiền cọc.</p>`:''}
      ${here||owned?'':`<div class="bk-actions">${btn(`Thuê · cọc ${xu(m.deposit)}`,'rent',{kind:m.id},'ghost',m.missing?' disabled':'')}</div>`}</li>`;
  }
  const mine=v.own?.kind===m.id;
  const readyFor=Math.min(100,Math.round((h.ready||0)*100/Math.max(1,m.need)));
  return `<li class="hs-home"><div class="hs-home-top"><span class="hs-emoji" aria-hidden="true">${m.emoji}</span><div class="grow"><b>${esc(m.name)}</b><small>${esc(m.where)}</small></div><strong class="hs-price">${xu(m.price)}</strong></div>
    <p>${esc(m.desc)}</p>
    <ul class="hs-points"><li>Trả trước ít nhất ${xu(m.down_min)} + phí ${xu(m.fee)}</li><li>Hết tiền phòng: chỉ điện nước ${xu(m.upkeep)}/ngày${m.saves>0?` (đỡ ${xu(m.saves)}/ngày)`:''}</li><li>Tinh thần +${m.comfort} mỗi sáng</li></ul>
    ${mine?'<p class="bk-alert good">Đây là nhà của bạn.</p>':owned?'':`<div class="hs-need"><div class="bk-row"><span>Đã có ${xu(h.ready)}</span><span>Cần ${xu(m.need)}</span></div>
      <div class="bk-bar ${m.missing?'warn':'good'}" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${readyFor}" aria-label="Đủ ${readyFor}% khoản trả trước"><i style="width:${readyFor}%"></i></div>
      <p class="bk-hint">${m.missing?`Còn thiếu <b>${xu(m.missing)}</b> để trả trước 30%${S.joint?' (chưa tính quỹ chung)':''}.`:m.missing_all?'Đủ tiền trả trước. Phần còn lại vay ngân hàng.':'Đủ tiền mua đứt, không cần vay.'}</p></div>
      <div class="bk-actions">${btn('Xem & mua','look',{kind:m.id},m.missing?'ghost':'primary')}</div>`}</li>`;
}

function savingsCard(v){
  const b=J().bank||{},R=b.rules;
  if(!b.open)return `<section class="bk-card hs-save"><h3>🐷 Tiết kiệm mua nhà</h3><p>Mở tài khoản Ngân hàng Phố để gửi tiết kiệm có kỳ hạn (lãi theo năm) và vay mua nhà khi đủ tiền trả trước.</p><div class="bk-actions">${btn('Mở Ngân hàng','bank',{tab:'home'},'primary')}</div></section>`;
  const pick=[15,60,180].filter(t=>R.term_rate[String(t)]);
  const rows=pick.map(t=>{const r=R.term_rate[String(t)],gain=Math.floor(1000*r*t/(10000*R.year_days));return `<tr><td>${esc(b.term_names[String(t)])}</td><td>${pct(r)}/năm</td><td>+${fmt(gain)} xu</td></tr>`;}).join('');
  return `<section class="bk-card hs-save"><h3>🐷 Tiết kiệm mua nhà</h3><p>Đang để dành: sổ tiết kiệm <b>${xu(b.savings?.total)}</b>. Gửi có kỳ hạn thì lãi cao hơn; đáo hạn gốc và lãi về tài khoản để trả trước tiền nhà.</p>
    <table class="bk-rates"><caption>Gửi 1.000 xu nhận thêm</caption><thead><tr><th scope="col">Kỳ hạn</th><th scope="col">Lãi</th><th scope="col">Khi đáo hạn</th></tr></thead><tbody>${rows}</tbody></table>
    <p class="bk-hint">1 tháng trong game là ${R.month_days} ngày sống, 1 năm là ${R.year_days} ngày sống.</p>
    <div class="bk-actions">${btn('Gửi tiết kiệm','bank',{tab:'save'},'primary')}</div></section>`;
}

function homeView(v){
  const market=(v.market||[]).map(m=>marketCard(v,m)).join('');
  const log=(v.log||[]).slice(0,8).map(r=>`<li><span>Ngày ${r.day} · ${esc(r.text)}</span>${r.amt?`<b class="${r.amt>0?'up':'down'}">${r.amt>0?'+':'−'}${fmt(Math.abs(r.amt))}</b>`:''}</li>`).join('');
  return moneyStrip(v)+placeCard(v)+ownCard(v)+loanCard(v)+
    `<section class="bk-card"><h3>Nhà đang rao</h3><p class="bk-hint">Mua nhà cần trả trước ít nhất ${v.rules.down_pct}% giá và ${v.rules.buy_fee_pct}% phí công chứng, sang tên. Phần còn lại vay Ngân hàng Phố, trả góp mỗi tháng.</p><ul class="hs-market">${market}</ul></section>`+
    savingsCard(v)+(log?`<section class="bk-card"><h3>Sổ nhà cửa</h3><ul class="bk-score-log">${log}</ul></section>`:'');
}

function previewHTML(){
  const v=V(),P=preview(),R=v.rules;
  const sum=`<dl class="hs-facts"><div><dt>Trả ngay</dt><dd>${xu(P.pay||0)}</dd></div><div><dt>Vay ngân hàng</dt><dd>${xu(Math.max(0,P.loan||0))}</dd></div>
    ${P.rows?`<div><dt>Mỗi kỳ (${R.month_days} ngày)</dt><dd>${xu(P.rows[0].amount)}</dd></div><div><dt>Tổng lãi</dt><dd>${xu(P.interest)}</dd></div>`:''}</dl>`;
  const table=P.rows?`<details class="hs-sched"><summary>Lịch trả góp dự kiến (${P.rows.length} kỳ)</summary><table class="bk-rates bk-sched"><thead><tr><th scope="col">Kỳ</th><th scope="col">Ngày</th><th scope="col">Gốc</th><th scope="col">Lãi</th><th scope="col">Phải trả</th></tr></thead>
    <tbody>${P.rows.map(r=>`<tr><td>${r.k}</td><td>${r.due}</td><td>${fmt(r.principal)}</td><td>${fmt(r.interest)}</td><td><b>${fmt(r.amount)}</b></td></tr>`).join('')}</tbody></table></details>`:'';
  return sum+(P.ok?'':`<p class="bk-alert warn">${esc(P.why)}</p>`)+table;
}
function buyView(v){
  const b=S.buy,m=(v.market||[]).find(x=>x.id===b.kind),R=v.rules,o=v.offer||{},h=v.have||{};
  if(!m){S.view='home';return homeView(v);}
  const loan=m.price-b.down;
  const monthsSel=`<label class="bk-field"><span>Thời hạn vay</span><select name="months">${R.months.map(n=>`<option value="${n}"${b.months===n?' selected':''}>${months(n)} · ${n} kỳ</option>`).join('')}</select></label>`;
  const jointField=S.joint?`<label class="bk-field"><span>Lấy từ quỹ chung (còn ${xu(S.joint.balance)})</span><input id="hs-joint" name="joint" type="number" inputmode="numeric" min="0" max="${Math.min(S.joint.balance,m.price+m.fee)}" step="10" value="${b.joint||0}"></label>`:'';
  const bankNote=loan>0?(h.bank?`<p class="bk-hint">Lãi vay theo điểm tín dụng ${o.score??''}: <b>${esc(o.rate_text)}</b>. Mỗi kỳ không quá ${R.dti_pct}% thu nhập một tháng (hiện ${xu(o.room)}).${o.ok?'':` <b>${esc(o.text)}</b>`}</p>`
    :`<p class="bk-alert warn">Muốn vay phần còn lại thì mở tài khoản Ngân hàng Phố trước. ${btn('Mở Ngân hàng','bank',{tab:'home'},'ghost small')}</p>`):'';
  return `<section class="bk-card hs-buy"><div class="hs-home-top"><span class="hs-emoji big" aria-hidden="true">${m.emoji}</span><div class="grow"><small>${esc(m.where)}</small><h3>${esc(m.name)}</h3></div><strong class="hs-price">${xu(m.price)}</strong></div>
    <p>${esc(m.desc)}</p>
    <div class="bk-move" data-hs-buy>
      <label class="bk-field"><span>Trả trước (ít nhất ${xu(m.down_min)})</span><input id="hs-down" name="down" type="number" inputmode="numeric" min="${m.down_min}" max="${m.price}" step="10" value="${b.down}"></label>
      <label class="bk-toggle"><input type="checkbox" name="all"${b.down>=m.price?' checked':''}><span>Trả đủ một lần, không vay</span></label>
      ${loan>0?monthsSel:''}${jointField}</div>
    ${bankNote}
    <div class="hs-preview">${previewHTML()}</div>
    <p class="bk-hint">Tiền trả trước và phí ${xu(m.fee)} lấy ${S.joint?'từ quỹ chung (phần bạn ghi ở trên), rồi ':''}từ tài khoản ngân hàng, thiếu thì lấy tiền mặt.${v.married?' Người ấy sẽ về ở chung khi bạn có nhà.':''}</p>
    <div class="bk-actions">${btn(loan>0?'Xem lại & ký hợp đồng':'Mua nhà','sign',{},'primary big')}${btn('Quay lại','back',{},'ghost')}</div></section>`;
}
