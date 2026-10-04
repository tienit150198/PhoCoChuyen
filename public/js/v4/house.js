/** 🏠 Nhà của bạn: rent a better room, buy a home, a mortgage at Ngân hàng Phố (story mode).
 * Every rule and number lives in game/housing.py; this file renders api.state.journey.home and sends
 * `jr_home_*` commands. The only maths mirrored here is the mortgage schedule (housing.schedule, on top of
 * bank.installment), so the contract shows the exact installments before signing; the server checks the
 * total interest the player saw. Its own dialog (like the bank), opened with data-action="house" from the
 * journey card, the bank's savings/loan tabs and the guide. Styles: /css/bank.css + /css/house.css. */
import {icon,escapeHTML as esc} from '../icons.js';
import {portrait,myPortrait} from './look.js';

const S={dlg:null,env:null,view:'home',busy:false,flash:null,buy:{kind:'',down:0,months:36,joint:0,move_in:true},joint:null,jointAt:0,listening:false};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const pct=bp=>`${(bp/100).toLocaleString('vi-VN',{maximumFractionDigits:2})}%`;
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,op,data={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-hs="${op}"${attrs(data)}${S.busy?' disabled':''}${extra}>${label}</button>`;
const J=()=>S.env?.api?.state?.journey||{};
const V=()=>J().home||{};
const care=c=>c>0?`<span>🧾 Bảo trì ${xu(c)}/tháng</span>`:'';   // 🧾 game/upkeep.py (absent: an older server)
const onDay=n=>{const d=n-(J().life_day||0);return d===0?`hôm nay (Ngày ${n})`:d===1?`Ngày ${n} (ngày mai)`:d<0?`Ngày ${n} (đã qua)`:`Ngày ${n} (còn ${d} ngày)`;};
const months=(m)=>m%12===0?`${m/12} năm (${m} tháng)`:`${m} tháng`;
const lname=s=>String(s||'').slice(0,1).toLowerCase()+String(s||'').slice(1);   // housing.lname: "Biệt thự Sông Hồng" → "biệt thự Sông Hồng"
const byPrice=list=>[...list].sort((a,b)=>a.price-b.price);
/* 🏘️ Several homes (housing.py VERSION 2): `own` is the one you live in, `props` the others (empty or let). A server
   from before sends no props / can_buy: one home at a time, as then. */
const PROPS=v=>Array.isArray(v.props)?v.props:[];
const MINE=v=>[...(v.own?[v.own]:[]),...PROPS(v)];
const HOME=(v,id)=>MINE(v).find(x=>x.id===id)||v.own;
const canBuy=v=>v.can_buy?v.can_buy:{ok:!v.own,why:''};
const withId=(o,x)=>x&&Array.isArray(V().props)?{...o,id:x.id}:o;   // a server from before knows only the home you live in
/* The homes on the market: the static list (content.journey.homes, housing.catalogue) joined by id with what the
   state says is still missing (housing.public market rows). */
const CAT=()=>S.env?.api?.content?.journey?.homes||{groups:[],homes:[]};
function MK(){const live=new Map((V().market||[]).map(r=>[r.id,r]));return CAT().homes.filter(c=>live.has(c.id)).map(c=>({...c,...live.get(c.id)}));}
const tone=gid=>(CAT().groups.find(g=>g.id===gid)||{}).color||'';
const toneStyle=gid=>{const c=tone(gid);return c?` style="--hs-tone:${esc(c)}"`:'';};

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
  if(kind&&MK().some(m=>m.id===kind))startBuy(kind);else S.view='home';
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
  }catch(e){S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}  // quiet: api.js, the save moved under the tap twice
  finally{S.busy=false;render();S.dlg?.querySelector('.hs-body')?.scrollTo?.(0,0);}
}
const ask=(title,msg,label,money)=>S.env.confirmAction(title,msg,label,money);  // money: {cost,pocket} → "còn thiếu" (v4/money.js)
const FROM_BANK=['account','wallet'];   // housing takes the account first, the rest in cash

function startBuy(kind){
  const m=MK().find(x=>x.id===kind);if(!m)return;
  const ready=(V().have?.ready||0)+(S.joint?.balance||0);
  S.view='buy';S.buy={kind,down:Math.min(m.price,Math.max(m.down_min,Math.floor(Math.max(0,ready-m.fee)/10)*10)),months:36,joint:0,move_in:!V().own&&!V().shared};   // living in a home already (yours or the spouse's): the new one stays empty unless ticked (feedback #137)
}

async function onClick(op,data){
  const v=V(),R=v.rules||{};
  switch(op){
    case'close':S.dlg.close();return;
    case'back':S.view='home';S.flash=null;render();return;
    case'look':startBuy(data.kind);S.flash=null;render();S.dlg.querySelector('.hs-body')?.scrollTo?.(0,0);return;
    case'bank':S.dlg.close();(await import('./bank.js')).openBank(S.env,data.tab||'save');return;
    case'inside':S.dlg.close();(await import('./reno.js')).openReno(S.env,data.mode);return;   // 🛠️ Trong nhà: xem, sửa, trang trí
    case'garage':S.dlg.close();(await import('./garage.js')).openGarage(S.env);return;   // 🚗 the vehicle parked out front
    case'family':S.dlg.close();S.env.openSheet('home',{jrView:'household'});return;
    case'rent':{const m=MK().find(x=>x.id===data.kind);if(!m)return;
      const was=v.rent,back=was?.deposit||0,bed=m.id===DORM,unit=bed?'Tiền giường':'Tiền phòng';
      const body=(was?`Trả ${lname(was.name)}, nhận lại cọc ${xu(back)}. `:'')+`Cọc ${xu(m.deposit)}, trả lại khi dọn đi. ${unit} ${xu(m.rent)}/ngày (gác Bà Tám: ${xu(v.attic_rent)}).`+(bed?' Ở ghép với 3 bạn cùng phòng.':'');
      const cost=m.deposit-back;
      if(await ask(was?`Chuyển sang ${lname(m.name)}?`:`Thuê ${lname(m.name)}?`,body,was?'Chuyển chỗ ở':`Thuê · cọc ${xu(m.deposit)}`,cost>0?{cost,pocket:FROM_BANK}:undefined))send('jr_home_rent',{kind:m.id,confirm:true});return;}
    case'leave':{const bed=v.rent?.kind===DORM;
      if(await ask(bed?'Trả giường ký túc xá?':'Trả phòng trọ?',`Nhận lại ${xu(v.rent?.deposit)} tiền cọc, về gác Bà Tám.`,bed?'Trả giường':'Trả phòng'))send('jr_home_leave',{confirm:true});return;}
    case'sign':{const P=preview();if(!P.ok){S.flash={text:P.why,kind:'warn'};render();return;}
      const m=P.m,loan=P.loan,b=S.buy;
      const multi=Array.isArray(v.props),moveIn=!multi||b.move_in;
      const body=`Trả ngay ${xu(P.pay)} (gồm phí ${xu(m.fee)})`+(b.joint?`, ${xu(b.joint)} từ quỹ chung`:'')+'. '
        +(loan?`Vay ${xu(loan)}, ${b.months} kỳ × ${xu(P.rows[0].amount)}, lãi ${pct(v.offer.rate)}/năm.`:'Không vay.')
        +(multi?(moveIn?(v.own?` Dọn về ở căn mới, ${lname(v.own.name)} để trống.`:' Dọn về ở căn mới.'):' Căn mới để trống, chưa dọn về.'):'');
      if(await ask(`Mua ${lname(m.name)}?`,body,loan?'Ký hợp đồng mua nhà':`Mua · ${xu(P.pay)}`,{cost:Math.max(0,P.pay-(b.joint||0)),pocket:FROM_BANK})){
        const r=await send('jr_home_buy',{kind:m.id,down:b.down,confirm:true,...(multi?{move_in:moveIn}:{}),...(b.joint&&moveIn?{joint:b.joint}:{}),...(loan?{months:b.months,total_interest:P.interest}:{})});
        if(r&&r.approved!==false){S.view='home';S.jointAt=0;loadJoint(true);render();}
      }return;}
    case'pay':{const x=HOME(v,data.id),L=x?.loan;if(!L)return;const amount=L.overdue||(L.next?L.next.amount-L.next.paid:0);
      if(await ask(L.overdue?`Trả ${xu(amount)} đang quá hạn?`:`Trả trước kỳ ${L.next.k}?`,x.live===false?x.name:'',`Trả · ${xu(amount)}`,{cost:amount,pocket:FROM_BANK}))send('jr_home_pay',withId({},x));return;}
    case'payoff':{const x=HOME(v,data.id),o=x?.loan?.payoff;if(!o)return;
      if(await ask(x.live===false?`Tất toán khoản vay mua ${lname(x.name)}?`:'Tất toán khoản vay mua nhà?',`Gốc ${xu(o.principal)}${o.overdue?` + quá hạn ${xu(o.overdue)}`:''} + lãi ${xu(o.interest)} + phí ${xu(o.fee)}. Bớt được ${xu(Math.max(0,o.saved))} tiền lãi.`,`Tất toán · ${xu(o.total)}`,{cost:o.total,pocket:FROM_BANK}))send('jr_home_payoff',withId({confirm:true},x));return;}
    case'sell':{const o=HOME(v,data.id);if(!o)return;const sl=o.sell,live=o.live!==false;
      const after=live?(PROPS(v).length?'. Bạn về gác Bà Tám (muốn ở căn khác thì dọn qua đó trước rồi hãy bán)':'')+(v.married?'. Người ấy dọn ra cùng bạn':''):o.let?`. ${o.let.name} trả nhà, gửi nốt tiền thuê`:'';
      if(await ask(`Bán ${lname(o.name)}?`,`Giá hôm nay ${xu(sl.value)}, phí ${xu(sl.fee)}${sl.payoff?`, trả nợ vay ${xu(sl.payoff)}`:''}. Nhận ${xu(sl.get)} vào ${v.have?.bank?'tài khoản':'ví'}${after}.`,`Bán · nhận ${xu(sl.get)}`))send('jr_home_sell',withId({confirm:true,value:sl.value},o));return;}
    case'move':{const x=HOME(v,data.id);if(!x||x.live!==false)return;const back=v.rent?.deposit||0;
      const body=`Thuê xe chở đồ ${xu(R.move_fee)}.`+(v.own?` ${v.own.name} sẽ để trống.`:'')+(back?` Trả phòng trọ, nhận lại cọc ${xu(back)}.`:'')+' Đồ trang trí gói vào túi đồ, bày lại ở nhà mới.'+(v.married?' Người ấy dọn về cùng bạn.':'');
      if(await ask(`Dọn về ${lname(x.name)}?`,body,`Dọn nhà · ${xu(R.move_fee)}`,R.move_fee>back?{cost:R.move_fee-back,pocket:FROM_BANK}:undefined))send('jr_home_move',{id:x.id,confirm:true});return;}
    case'moveShared':{const sh=v.shared;if(!sh||!v.own)return;   // 💞 back to the spouse's home (housing.py jr_home_move to='shared')
      if(await ask(`Về ở chung ${lname(sh.home)}?`,`Thuê xe chở đồ ${xu(R.move_fee)}. ${v.own.name} sẽ để trống, vẫn là nhà của bạn. Đồ trang trí gói vào túi đồ.`,`Dọn nhà · ${xu(R.move_fee)}`,{cost:R.move_fee,pocket:FROM_BANK}))send('jr_home_move',{to:'shared',confirm:true});return;}
    case'let':{const x=HOME(v,data.id);if(!x||x.live!==false||x.let)return;
      if(await ask(`Cho thuê ${lname(x.name)}?`,`Người thuê trả ${xu(x.let_rent)}/tháng (${R.month_days} ngày), vào đúng ngày trả góp của căn này. Họ tự trả điện nước. Muốn dọn về thì lấy lại nhà lúc nào cũng được.`,'Cho thuê'))send('jr_home_let',{id:x.id,on:true,confirm:true});return;}
    case'unlet':{const x=HOME(v,data.id);if(!x?.let)return;
      if(await ask(`Lấy lại ${lname(x.name)}?`,`${x.let.name} dọn đi, gửi nốt tiền thuê những ngày đã ở. Căn nhà để trống, không tốn gì.`,'Lấy lại nhà'))send('jr_home_let',{id:x.id,on:false,confirm:true});return;}
  }
}

function onBuyField(el,full){
  const k=el.name,m=MK().find(x=>x.id===S.buy.kind);if(!m)return;
  if(k==='down')S.buy.down=Math.max(0,Math.floor(Number(el.value)||0));
  else if(k==='months')S.buy.months=Number(el.value);
  else if(k==='joint')S.buy.joint=Math.max(0,Math.floor(Number(el.value)||0));
  else if(k==='all'){S.buy.down=el.checked?m.price:m.down_min;full=true;}
  else if(k==='move_in'){S.buy.move_in=el.checked;if(!el.checked)S.buy.joint=0;full=true;}
  const box=S.dlg.querySelector('.hs-preview');
  if(box&&!full){box.innerHTML=previewHTML();const sb=S.dlg.querySelector('[data-hs="sign"]');if(sb)sb.disabled=S.busy||!preview().ok;return;}
  render();
}
function preview(){
  const v=V(),b=S.buy,m=MK().find(x=>x.id===b.kind),R=v.rules||{};
  if(!m)return {ok:false,why:'Chọn một căn nhà nhé.'};
  const loan=m.price-b.down,pay=b.down+m.fee,have=v.have||{},joint=b.joint||0;
  const out={m,loan,pay,rows:null,interest:0};
  if(!canBuy(v).ok)return {...out,ok:false,why:canBuy(v).why||'Bạn đang có nhà rồi.'};
  if(b.down<m.down_min||b.down>m.price)return {...out,ok:false,why:`Trả trước từ ${xu(m.down_min)} (${R.down_pct}% giá nhà) tới ${xu(m.price)}.`};
  if(loan&&loan<R.loan_min)return {...out,ok:false,why:`Vay ít nhất ${xu(R.loan_min)}, hoặc trả đủ luôn nhé.`};
  if(joint>pay)return {...out,ok:false,why:`Quỹ chung chỉ cần góp tối đa ${xu(pay)}.`};
  if(joint&&joint>(S.joint?.balance||0))return {...out,ok:false,why:`Quỹ chung chỉ còn ${xu(S.joint?.balance||0)}.`};
  if(joint&&Array.isArray(v.props)&&!b.move_in)return {...out,ok:false,why:'Quỹ chung chỉ góp mua căn nhà cả hai cùng về ở.'};
  const short=pay-joint-have.ready;
  if(short>0)return {...out,ok:false,short,why:`Còn thiếu ${xu(short)} cho khoản trả trước và phí.`};
  if(loan){
    const o=v.offer||{};
    if(!o.ok)return {...out,ok:false,why:o.text||'Ngân hàng chưa duyệt vay mua nhà.'};
    if((o.score??0)<(m.score||0))return {...out,ok:false,why:`Vay mua ${lname(m.name)} cần điểm tín dụng từ ${m.score} (bạn đang có ${o.score}). Trả đủ một lần, hoặc giữ điểm tốt thêm ít lâu nhé.`};
    const rows=schedule(loan,o.rate,b.months,J().life_day,R.month_days);
    const int=rows.reduce((x,r)=>x+r.interest,0);
    if(rows[0].amount>o.room)return {...out,rows,interest:int,ok:false,why:`Trả góp vượt ${R.dti_pct}% thu nhập: mỗi kỳ ${xu(rows[0].amount)}, tối đa ${xu(o.room)}${o.others?` (đã trừ ${xu(o.others)} trả góp các căn đang vay)`:''}. Ngân hàng sẽ không duyệt. Trả trước nhiều hơn hoặc vay dài hơn nhé.`};
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

/* "Bước tiếp theo" (the guide's line, v4/guide.js look): the one thing to do now on the way to a home of your own. */
function nextStep(v){
  const h=v.have||{},late=MINE(v).find(x=>x.loan?.overdue),L=late?.loan,homes=byPrice(MK().filter(m=>m.kind==='own'));
  const empty=PROPS(v).find(x=>!x.let&&x.move?.ok);
  let go=null;
  if(L?.overdue)go=L.overdue<=(h.ready||0)?{op:'pay',data:withId({},late),label:`⏰ Trả ${xu(L.overdue)} trả góp đang quá hạn`}:{op:'bank',data:{tab:'home'},label:'🏦 Nộp tiền vào tài khoản để trả góp',note:`thiếu ${xu(L.overdue-(h.ready||0))}`};
  else if(!v.own&&!v.shared&&empty)go={op:'move',data:{id:empty.id},label:`🚚 Dọn về ${lname(empty.name)}`,note:'nhà của bạn đang để trống'};
  else if(!v.own&&!v.shared){
    // The dearest home whose down payment is there and whose 3-year installment the bank would take (as startBuy fills the form).
    const o=v.offer||{},R=v.rules||{},ok=m=>{const down=Math.min(m.price,Math.max(m.down_min,Math.floor(Math.max(0,(h.ready||0)-m.fee)/10)*10)),loan=m.price-down;
      return !loan||(o.ok&&(o.score??0)>=(m.score||0)&&loan>=(R.loan_min||0)&&schedule(loan,o.rate,36,0,R.month_days||5)[0].amount<=o.room);};
    const cash=homes.filter(m=>!m.missing),can=cash.filter(ok).pop()||cash[0],next=homes.find(m=>m.missing);
    if(can)go={op:'look',data:{kind:can.id},label:`🔑 Xem & mua ${lname(can.name)}`};
    else if(!h.bank)go={op:'bank',data:{tab:'home'},label:'🏦 Mở tài khoản Ngân hàng Phố'};
    else if(next)go={op:'bank',data:{tab:'save'},label:'🐷 Gửi tiết kiệm mua nhà',note:`còn thiếu ${xu(next.missing)} cho ${lname(next.name)}`};
  }
  if(!go)return '';
  return `<div class="gd-next hs-next" role="status"><small>Bước tiếp theo</small><button type="button" class="gd-hint" data-hs="${go.op}"${attrs(go.data||{})}${S.busy?' disabled':''}><b>${esc(go.label)}</b>${go.note?`<span class="gd-note">${esc(go.note)}</span>`:''}<i aria-hidden="true">→</i></button></div>`;
}

/* 🛏️ Ký túc xá Hẻm 7 (housing.dorm_view): two bunk beds, the three roommates on theirs, you on the bottom bed by the
   window, and one roommate's line of the day. */
const DORM='ky_tuc_xa';
function bedHTML(D,id){
  const m=D.mates.find(x=>x.bed===id),me=D.you===id,st=S.env?.api?.state;
  const face=me?myPortrait(st,40,'Bạn'):m?portrait(m.look,m.gender,40,m.name):'';
  return `<div class="hs-bed ${id.endsWith('top')?'top':'low'}${me?' me':''}"><span class="hs-bed-face">${face}</span><span class="hs-bed-name">${me?'Bạn':esc(m?.name||'')}</span></div>`;
}
function dormRoom(D){
  if(!D?.mates)return '';
  const bunk=side=>`<div class="hs-bunk">${bedHTML(D,side+'_top')}${bedHTML(D,side+'_bottom')}<i class="hs-ladder" aria-hidden="true"></i></div>`;
  const names=D.mates.map(m=>m.name).join(', ');
  const line=D.line?`<div class="hs-dorm-say"><span class="hs-dorm-say-face" aria-hidden="true">${(()=>{const m=D.mates.find(x=>x.id===D.line.who);return m?portrait(m.look,m.gender,36,m.name):'';})()}</span><p><b>${esc(D.line.name)}</b> ${esc(D.line.text)}</p></div>`:'';
  return `<figure class="hs-dorm"><div class="hs-dorm-room" role="img" aria-label="Phòng bốn giường tầng: ${esc(names)} và bạn"><span class="hs-dorm-window" aria-hidden="true"></span>${bunk('left')}${bunk('right')}</div>
    <figcaption><ul class="hs-mates">${D.mates.map(m=>`<li><span aria-hidden="true">${m.emoji}</span><span><b>${esc(m.name)}</b><small>${esc(m.role)}</small></span></li>`).join('')}</ul></figcaption></figure>${line}`;
}
function placeCard(v){
  const p=v.place||{},c=p.cost||{},bed=p.kind===DORM;
  const costLine=`${p.where_id==='own'||p.where_id==='shared'?'Điện nước':bed?'Tiền giường':'Tiền phòng'} ${xu(c.rent)} · cơm ${xu(c.meals)} mỗi ngày`;
  const who=p.where_id==='shared'?`<p class="hs-tag">💞 Nhà chung với ${esc(p.with)}</p>`:p.where_id==='own'?'<p class="hs-tag">🔑 Nhà đứng tên bạn</p>':bed?'<p class="hs-tag">👥 Ở ghép · giường dưới cạnh cửa sổ</p>':p.where_id==='rent'?'<p class="hs-tag">🧾 Đang thuê</p>':'';
  let actions='';
  const DC=J().deco,deco=DC?`<p class="hs-chips"><span>🪴 Ấm cúng ${DC.cozy.total} · ${esc(DC.cozy.level)}</span>${DC.bag.length?`<span>🎒 ${DC.bag.length} món trong túi</span>`:''}</p>`:'';
  const setUp=DC?btn(bed?'🚪 Về góc giường':p.where_id==='shared'?'🚪 Vào nhà':'🚪 Vào phòng','inside',{},'primary'):'';   // 🚶 rentals, the attic, a shared home: walk in, decor inside (v4/home-walk.js)
  if(p.where_id==='rent')actions=`${bed?dormRoom(p.dorm):''}${deco}<div class="bk-actions">${setUp}${btn(bed?'Trả giường, nhận lại cọc':'Trả phòng, nhận lại cọc','leave',{},'ghost')}</div>`;
  else if(p.where_id==='own'&&J().reno){const R=J().reno,worn=R.parts.filter(x=>x.worn).length;
    actions=`<p class="hs-chips"><span>🪴 Ấm cúng ${R.cozy}</span><span>🛠️ ${worn?`${worn} chỗ cần sửa`:'Nhà sạch đẹp'}</span></p><div class="bk-actions">${btn('🚪 Vào nhà','inside',{},'primary')}${worn?btn('🛠️ Sửa nhà','inside',{mode:'fix'},'ghost'):''}</div>`;}
  else if(DC)actions=`${deco}<div class="bk-actions">${setUp}</div>`;
  actions+=parked();
  actions+=`<div class="bk-actions">${btn('🏡 Gia đình · Thú cưng','family',{},'ghost')}</div>`;
  const comfort=p.comfort?`<p class="bk-hint"><span>😊 Tinh thần +${p.comfort} mỗi sáng</span>${v.own?.loan?.late?' <span>(tạm dừng khi trễ hạn trả góp)</span>':''}</p>`:'';
  return `<section class="bk-card hs-place ${esc(p.where_id||'')}"${toneStyle(p.group)}><div class="hs-place-top"><span class="hs-emoji" aria-hidden="true">${p.emoji||'🏚️'}</span><div class="grow"><small>Nơi bạn đang ở</small><h3>${esc(p.name)}</h3><small>${esc(p.where||'')}</small></div></div>
    ${who}<p class="hs-cost">${costLine}</p>${comfort}${p.perk&&!bed?`<p class="bk-hint">${esc(p.perk)}</p>`:''}${actions}</section>`;
}

/* 🚗 The vehicle the player rides (game/garage.py), parked out front: one line, a tap opens the garage. */
function parked(){
  const g=J().garage,c=g?.ride&&g.cars?.find(x=>x.id===g.ride),it=c&&(S.env?.api?.content?.journey?.garage?.vehicles||[]).find(x=>x.id===c.id);
  if(!it)return '';
  const hex=(S.env.api.content.journey.garage.paints||[]).find(x=>x.id===c.color)?.hex||'';
  return `<div class="bk-actions"><button type="button" class="btn ghost small" data-hs="garage"${S.busy?' disabled':''}><span aria-hidden="true">🅿️ ${it.emoji}</span> ${hex?`<i style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${esc(hex)}" aria-hidden="true"></i>`:''}${esc(it.name)} đậu trước nhà</button></div>`;
}
function loanCard(v,o=v.own){
  const L=o?.loan;if(!L)return '';
  const day=v.life_day,R=v.rules;
  const rows=L.rows.map(r=>`<tr class="${r.paid>=r.amount?'paid':r.due<=day?'late':''}"><td>${r.k}</td><td>${r.due}</td><td>${fmt(r.amount)}${r.fee?` <small>(phạt ${fmt(r.fee)})</small>`:''}</td><td>${r.paid>=r.amount?(r.late?'Đã trả trễ':'Đã trả'):r.due<=day?(r.late?'Trễ hạn':'Ân hạn'):'Chờ'}</td></tr>`).join('');
  const done=L.paid_rows,pctDone=Math.round(done*100/L.rows.length);
  const ready=v.have?.ready||0,due=L.overdue||(L.next?L.next.amount-L.next.paid:0),short=n=>n>ready?` <small>(thiếu ${fmt(n-ready)})</small>`:'';
  return `<section class="bk-card ${L.overdue?'bk-late':''}"><h3>📝 ${o.live===false?`Vay mua ${esc(lname(o.name))}`:'Vay mua nhà'} · ${xu(L.principal)}</h3>
    <p class="bk-hint">${esc(L.rate_text)} · ${L.months} kỳ × ${R.month_days} ngày · còn nợ <b>${xu(L.left)}</b></p>
    <div class="bk-bar good" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pctDone}" aria-label="Đã trả ${done} trên ${L.rows.length} kỳ"><i style="width:${pctDone}%"></i></div>
    <p class="bk-hint">Đã trả ${done}/${L.rows.length} kỳ.${L.next?` Kỳ tới ${xu(L.next.amount-L.next.paid)}, ${onDay(L.next.due)}.`:''}</p>
    ${L.overdue?`<p class="bk-alert ${L.late?'bad':'warn'}">${L.late?'Trễ hạn':'Ân hạn'}: ${xu(L.overdue)}. ${L.late?(o.live===false?'Đã tính phí trễ hạn.':'Tinh thần tạm không được cộng.'):`Chưa tính phí trong ${R.grace} ngày.`}</p>`:''}
    <details class="hs-sched"><summary>Lịch trả góp</summary><table class="bk-rates bk-sched"><thead><tr><th scope="col">Kỳ</th><th scope="col">Ngày</th><th scope="col">Phải trả</th><th scope="col">Trạng thái</th></tr></thead><tbody>${rows}</tbody></table></details>
    <div class="bk-actions">${btn(`${L.overdue?'Trả khoản quá hạn':'Trả trước kỳ tới'} · ${xu(due)}${short(due)}`,'pay',{id:o.id},L.overdue?'primary':'ghost',due>ready?' disabled':'')}${btn(`Tất toán sớm · ${xu(L.payoff.total)}${short(L.payoff.total)}`,'payoff',{id:o.id},'ghost',L.payoff.total>ready?' disabled':'')}</div>
    <p class="bk-hint">Mỗi kỳ tự trích từ tài khoản, thiếu thì lấy tiền mặt. Thiếu tiền: ${R.grace} ngày ân hạn, không phạt.</p></section>`;
}

function ownCard(v){
  const o=v.own;if(!o)return '';
  const grow=o.value-o.price;
  return `<section class="bk-card"><h3>${o.emoji} ${esc(o.name)}</h3>
    <dl class="hs-facts"><div><dt>Ngày mua</dt><dd>Ngày ${o.day} · ${xu(o.price)}</dd></div><div><dt>Giá thị trường hôm nay</dt><dd>${xu(o.value)}${grow>0?` <small class="up">(+${fmt(grow)})</small>`:''}</dd></div>
    <div><dt>Điện nước</dt><dd>${xu(o.upkeep)}/ngày</dd></div>${o.care?`<div><dt>Phí bảo trì</dt><dd>${xu(o.care)}/tháng</dd></div>`:''}<div><dt>Bán ngay thì nhận</dt><dd>${xu(o.sell.get)}</dd></div></dl>
    <p class="bk-hint">Giá nhà tăng ~${pct(v.rules.grow_rate)} mỗi năm. Bán mất ${v.rules.sell_fee_pct}% phí.</p>
    <div class="bk-actions">${btn('Bán nhà','sell',{id:o.id},'ghost small danger')}</div></section>`;
}

/* 💞 Living in a home of your own while the spouse's home is still there (feedback #137): the way back to it. */
function sharedCard(v){
  const sh=v.shared;if(!sh||!v.own)return '';
  const ready=(v.have?.ready||0)>=(v.rules?.move_fee||0);
  return `<section class="bk-card hs-prop"><div class="hs-home-top"><span class="hs-emoji" aria-hidden="true">${sh.emoji||'💞'}</span><div class="grow"><small>Nhà chung với ${esc(sh.name)}</small><h3>${esc(sh.home)}</h3></div></div>
    <p class="bk-hint">Bạn đang ở ${esc(lname(v.own.name))}. Muốn về ở chung thì dọn về đây, ${esc(lname(v.own.name))} vẫn là nhà của bạn.</p>
    <div class="bk-actions">${btn(`💞 Về ở chung · ${xu(v.rules?.move_fee)}`,'moveShared',{},'primary',ready?'':' disabled')}</div></section>`;
}

/* 🏘️ Another home you own: empty or let (a home from 6.000 xu pays its phí bảo trì either way); move in, let it, take it back, sell it. */
function propCard(v,x){
  const grow=x.value-x.price,L=x.let,mv=x.move||{},sl=x.sell||{};
  const status=L?`<p class="hs-tag let">${L.emoji} Cho thuê · ${esc(L.name)}</p>`:'<p class="hs-tag idle">🔑 Đang để trống</p>';
  const fee=x.care?` Phí bảo trì ${xu(x.care)}/tháng.`:'';
  const rent=L?`<p class="bk-hint">Tiền thuê ${xu(L.rent)}/tháng · kỳ tới ${onDay(L.next)}${L.next_amount!==L.rent?` (${xu(L.next_amount)} cho số ngày đã ở)`:''}${L.owed?` · đang khất ${xu(L.owed)}`:''}.${fee}</p>`
    :`<p class="bk-hint">${x.care?`Để trống vẫn tốn phí bảo trì ${xu(x.care)}/tháng.`:'Để trống không tốn gì.'} Cho thuê được khoảng ${xu(x.let_rent)}/tháng.</p>`;
  const acts=L?btn('Lấy lại nhà','unlet',{id:x.id},'ghost')
    :btn(`🚚 Dọn về ở · ${xu(mv.fee)}`,'move',{id:x.id},'primary',mv.ok?'':' disabled')+btn('Cho thuê','let',{id:x.id},'ghost');
  const why=[!L&&!mv.ok?mv.why:'',sl.ok===false?sl.why:''].filter(Boolean).map(t=>`<p class="bk-hint">${esc(t)}</p>`).join('');
  return `<section class="bk-card hs-prop"${toneStyle(x.group)}><div class="hs-home-top"><span class="hs-emoji" aria-hidden="true">${x.emoji}</span><div class="grow"><small>${esc(x.where)}</small><h3>${esc(x.name)}</h3></div></div>${status}
    <dl class="hs-facts"><div><dt>Ngày mua</dt><dd>Ngày ${x.day} · ${xu(x.price)}</dd></div><div><dt>Giá thị trường hôm nay</dt><dd>${xu(x.value)}${grow>0?` <small class="up">(+${fmt(grow)})</small>`:''}</dd></div>
    <div><dt>Còn nợ vay</dt><dd>${x.loan?xu(x.loan.left):'Không'}</dd></div><div><dt>Bán ngay thì nhận</dt><dd>${xu(sl.get)}</dd></div></dl>
    ${rent}<div class="bk-actions">${acts}${btn('Bán nhà','sell',{id:x.id},'ghost small danger',sl.ok===false?' disabled':'')}</div>${why}</section>`;
}

/* One listing, phone first: the price and the monthly installment up front, "thiếu N xu" when it is not there yet. */
function monthly(v,m){
  const o=v.offer||{},R=v.rules||{},loan=m.price-m.down_min;
  return loan>=(R.loan_min||0)?schedule(loan,o.rate,36,0,R.month_days||5)[0].amount:0;
}
function marketCard(v,m){
  const h=v.have||{},owned=!!v.own,full=!canBuy(v).ok;
  if(m.kind==='rent'){
    const here=v.rent?.kind===m.id,moving=!!v.rent&&!here,bed=m.id===DORM;
    const cheaper=m.rent<(v.attic_rent||0)?`<span class="up">rẻ hơn gác Bà Tám ${xu(v.attic_rent-m.rent)}/ngày</span>`:'';
    return `<li class="hs-home${here?' mine':''}"${toneStyle(m.group)}><div class="hs-home-top"><span class="hs-emoji" aria-hidden="true">${m.emoji}</span><div class="grow"><b>${esc(m.name)}</b><small>${esc(m.where)}</small></div><strong class="hs-price">${xu(m.rent)}<small>/ngày</small></strong></div>
      ${bed?`<p>${esc(m.desc)}</p>`:''}<p class="hs-chips"><span>🔒 Cọc ${xu(m.deposit)}</span>${m.comfort?`<span>😊 +${m.comfort}/ngày</span>`:''}${m.perk?`<span>${esc(m.perk)}</span>`:''}${cheaper}</p>
      ${here?`<p class="bk-alert good">${bed?'Bạn đang ở giường dưới phòng này.':'Bạn đang thuê phòng này.'}</p>`:owned?'':`<div class="hs-go">${m.missing?`<span class="hs-miss">thiếu ${xu(m.missing)}</span>`:'<span class="hs-ok">✓ Đủ tiền cọc</span>'}${btn(moving?'Chuyển qua đây':'Thuê','rent',{kind:m.id},m.missing?'ghost':'primary',m.missing?' disabled':'')}</div>`}</li>`;
  }
  const mine=MINE(v).some(x=>x.kind===m.id),o=v.offer||{},per=monthly(v,m);
  const scoreShort=o.score!=null&&m.score>(v.rules?.home_score||0)&&o.score<m.score;
  const status=m.missing?`<span class="hs-miss">thiếu ${xu(m.missing)}${S.joint?' <small>(chưa tính quỹ chung)</small>':''}</span>`
    :scoreShort&&m.missing_all?`<span class="hs-miss soft">cần điểm tín dụng ${m.score}</span>`:`<span class="hs-ok">✓ ${m.missing_all?'Đủ trả trước':'Đủ mua đứt'}</span>`;
  return `<li class="hs-home${mine?' mine':''}"${toneStyle(m.group)}><div class="hs-home-top"><span class="hs-emoji" aria-hidden="true">${m.emoji}</span><div class="grow"><b>${esc(m.name)}</b><small>${esc(m.where)}</small></div><strong class="hs-price">${xu(m.price)}</strong></div>
    <p class="hs-terms"><span>Trả trước <b>${xu(m.need)}</b></span>${per?`<span>Góp <b>${xu(per)}</b>/tháng</span>`:''}</p>
    <p class="hs-chips"><span>😊 +${m.comfort}/ngày</span><span>⚡ ${xu(m.upkeep)}/ngày</span>${care(m.care)}${m.perk?`<span>${esc(m.perk)}</span>`:''}${m.score>(v.rules?.home_score||0)?`<span>🏦 Điểm ${m.score}+</span>`:''}</p>
    ${mine?'<p class="bk-alert good">Đây là nhà của bạn.</p>':full?'':`<div class="hs-go">${status}${btn('Xem & mua','look',{kind:m.id},m.missing?'ghost':'primary')}</div>`}</li>`;
}
function marketGroups(v){
  const market=MK();
  return CAT().groups.map(g=>{
    const list=market.filter(m=>m.group===g.id);if(!list.length)return '';
    return `<div class="hs-group"${toneStyle(g.id)}><h4><span class="hs-group-ico" aria-hidden="true">${g.emoji}</span>${esc(g.name)}<small>${list.length}</small></h4><ul class="hs-market">${list.map(m=>marketCard(v,m)).join('')}</ul></div>`;
  }).join('');
}

function savingsCard(v){
  const b=J().bank||{},R=b.rules;
  if(!b.open)return `<section class="bk-card hs-save"><h3>🐷 Tiết kiệm mua nhà</h3><p class="bk-hint">Có tài khoản Ngân hàng Phố mới gửi tiết kiệm và vay mua nhà được.</p><div class="bk-actions">${btn('Mở Ngân hàng','bank',{tab:'home'},'primary')}</div></section>`;
  const pick=[15,60,180].filter(t=>R.term_rate[String(t)]);
  const rows=pick.map(t=>{const r=R.term_rate[String(t)],gain=Math.floor(1000*r*t/(10000*R.year_days));return `<tr><td>${esc(b.term_names[String(t)])}</td><td>${pct(r)}/năm</td><td>+${fmt(gain)} xu</td></tr>`;}).join('');
  return `<section class="bk-card hs-save"><h3>🐷 Tiết kiệm mua nhà</h3><p>Sổ tiết kiệm: <b>${xu(b.savings?.total)}</b></p>
    <table class="bk-rates"><caption>Gửi 1.000 xu nhận thêm</caption><thead><tr><th scope="col">Kỳ hạn</th><th scope="col">Lãi</th><th scope="col">Khi đáo hạn</th></tr></thead><tbody>${rows}</tbody></table>
    <p class="bk-hint">1 tháng = ${R.month_days} ngày sống, 1 năm = ${R.year_days} ngày sống.</p>
    <div class="bk-actions">${btn('Gửi tiết kiệm','bank',{tab:'save'},'primary')}</div></section>`;
}

function homeView(v){
  const log=(v.log||[]).slice(0,8).map(r=>`<li><span>Ngày ${r.day} · ${esc(r.text)}</span>${r.amt?`<b class="${r.amt>0?'up':'down'}">${r.amt>0?'+':'−'}${fmt(Math.abs(r.amt))}</b>`:''}</li>`).join('');
  const more=PROPS(v).map(x=>propCard(v,x)+loanCard(v,x)).join('');
  const cap=Array.isArray(v.props)&&MINE(v).length?` Có thể có tới ${v.rules.owned_max} căn${canBuy(v).ok?'':`: ${esc(canBuy(v).why)}`}.`:'';
  const bill=v.care?.month?`<p class="bk-hint hs-care">🧾 Phí bảo trì các căn của bạn khoảng ${xu(v.care.month)}/tháng, trừ cùng hóa đơn ${onDay(v.care.next)}: tiền mặt trước, thiếu thì lấy từ tài khoản, không bao giờ làm ví âm.</p>`:'';
  return moneyStrip(v)+nextStep(v)+placeCard(v)+sharedCard(v)+ownCard(v)+loanCard(v)+more+bill+
    `<section class="bk-card hs-listing"><h3>Nhà đang rao</h3><p class="bk-hint">Trả trước ${v.rules.down_pct}% + phí, còn lại vay 3 năm.${cap}</p>${marketGroups(v)}</section>`+
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
  const b=S.buy,m=MK().find(x=>x.id===b.kind),R=v.rules,o=v.offer||{},h=v.have||{};
  if(!m){S.view='home';return homeView(v);}
  const loan=m.price-b.down;
  const monthsSel=`<label class="bk-field"><span>Thời hạn vay</span><select name="months">${R.months.map(n=>`<option value="${n}"${b.months===n?' selected':''}>${months(n)} · ${n} kỳ</option>`).join('')}</select></label>`;
  const multi=Array.isArray(v.props)&&Boolean(v.own||PROPS(v).length||v.shared),moveIn=!multi||b.move_in;
  const moveField=multi?`<label class="bk-toggle"><input type="checkbox" name="move_in"${b.move_in?' checked':''}><span>Dọn về ở căn này${v.own?` (${esc(lname(v.own.name))} để trống)`:v.shared?` (thôi ở chung ${esc(lname(v.shared.home))})`:''}</span></label>`
    +(b.move_in?'':`<p class="bk-hint">${m.care?`Để trống vẫn tốn phí bảo trì ${xu(m.care)}/tháng.`:'Để trống không tốn gì.'} Cho thuê được khoảng ${xu(m.let_rent)}/tháng.</p>`):'';
  const jointField=S.joint&&moveIn?`<label class="bk-field"><span>Lấy từ quỹ chung (còn ${xu(S.joint.balance)})</span><input id="hs-joint" name="joint" type="number" inputmode="numeric" min="0" max="${Math.min(S.joint.balance,m.price+m.fee)}" step="10" value="${b.joint||0}"></label>`:'';
  const bankNote=loan>0?(h.bank?`<p class="bk-hint">Lãi <b>${esc(o.rate_text)}</b> (điểm tín dụng ${o.score??''}${m.score>R.home_score?`, căn này cần từ ${m.score}`:''}). Mỗi kỳ tối đa ${xu(o.room)}${o.others?` (đã trừ ${xu(o.others)} trả góp các căn đang vay)`:''}.${o.ok?'':` <b>${esc(o.text)}</b>`}</p>`
    :`<p class="bk-alert warn">Cần tài khoản Ngân hàng Phố để vay. ${btn('Mở Ngân hàng','bank',{tab:'home'},'ghost small')}</p>`):'';
  return `<section class="bk-card hs-buy"${toneStyle(m.group)}><div class="hs-home-top"><span class="hs-emoji big" aria-hidden="true">${m.emoji}</span><div class="grow"><small>${esc(m.where)}</small><h3>${esc(m.name)}</h3></div><strong class="hs-price">${xu(m.price)}</strong></div>
    <p>${esc(m.desc)}</p><p class="hs-chips"><span>😊 +${m.comfort}/ngày</span><span>⚡ ${xu(m.upkeep)}/ngày</span>${care(m.care)}${m.perk?`<span>${esc(m.perk)}</span>`:''}</p>
    ${m.care?`<p class="bk-hint">Căn này có phí bảo trì khoảng ${xu(m.care)}/tháng (${R.month_days} ngày sống), dù ở, để trống hay cho thuê.</p>`:''}
    <div class="bk-move" data-hs-buy>
      <label class="bk-field"><span>Trả trước (ít nhất ${xu(m.down_min)})</span><input id="hs-down" name="down" type="number" inputmode="numeric" min="${m.down_min}" max="${m.price}" step="10" value="${b.down}"></label>
      <label class="bk-toggle"><input type="checkbox" name="all"${b.down>=m.price?' checked':''}><span>Trả đủ một lần, không vay</span></label>
      ${loan>0?monthsSel:''}${moveField}${jointField}</div>
    ${bankNote}
    <div class="hs-preview">${previewHTML()}</div>
    ${v.married&&moveIn?'<p class="bk-hint">💞 Có nhà rồi, người ấy về ở chung.</p>':''}
    <div class="bk-actions">${btn(loan>0?'Xem lại & ký hợp đồng':'Mua nhà','sign',{},'primary big',preview().ok?'':' disabled')}${btn('Quay lại','back',{},'ghost')}</div></section>`;
}
