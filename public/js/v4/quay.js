/** 🏪 Quầy của bạn: your own counter, run by staff you hire (story mode).
 * Every rule and number lives in game/quay.py; this file renders api.state.journey.quay with the static numbers
 * (content.journey.quay) and sends `jr_quay_*` commands. Its own dialog (like Xe & phương tiện), opened with
 * data-action="quay" from the "Ngân hàng & nhà" hub. Owner style: one short line and one obvious button per card,
 * explanations behind "?". Styles: /css/bank.css + /css/quay.css.
 * 💼 Làm thêm (game/quay_hire.py): another player's counter hires you for a shift, or you hire a player for yours;
 * GET /api/quay and POST /api/quay/<op> (the wage is escrowed by the server, paid once when the shift's day closes). */
import {icon,escapeHTML as esc} from '../icons.js';

const S={dlg:null,env:null,view:'list',tab:'mine',pick:null,busy:false,flash:null,listening:false,open:{},help:{},wage:{},hire:null,loading:false,to:{}};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,op,data={},cls='',why='')=>`<button type="button" class="btn ${cls}" data-qy="${op}"${attrs(data)}${S.busy||why?' disabled':''}${why?` title="${esc(why)}"`:''}>${label}</button>`;
const J=()=>S.env?.api?.state?.journey||{};
const V=()=>J().quay;
const CAT=()=>S.env?.api?.content?.journey?.quay||null;
const place=id=>CAT()?.places.find(p=>p.id===id)||{};
const trade=id=>CAT()?.trades?.[id]||{emoji:'🏪',name:id};
const MOOD=m=>m>=80?'😄':m>=55?'🙂':m>=35?'😐':'😟';

/* ---- styles on first use ---- */
let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=Promise.all([link('/css/bank.css','bk-css'),link('/css/quay.css','qy-css')]);

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium bk-sheet qy-sheet';d.setAttribute('aria-labelledby','qy-title');
  d.innerHTML='<div class="qy-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-qy]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.qy,el.dataset,el);
  });
  d.addEventListener('input',e=>{const t=e.target;if(t.name==='qy-name'&&S.pick)S.pick.name=t.value;});
  d.addEventListener('submit',e=>e.preventDefault());
  d.addEventListener('close',()=>{S.flash=null;S.view='list';S.pick=null;});
  S.dlg=d;return d;
}
export async function openQuay(env){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';env.api.addEventListener('state',()=>{const key=JSON.stringify([J().wallet,J().quay]);if(key===seen)return;seen=key;if(S.dlg?.open&&!S.busy)render();});
  }
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();
  S.view='list';S.pick=null;S.hire=null;
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
  if(S.tab==='jobs')loadHire();
}
export async function quayAction(action,data,el,env){
  if(action!=='quay')return false;
  await openQuay(env);return true;
}

async function send(action,payload={}){
  const {api}=S.env;S.busy=true;render();
  try{
    const r=await api.command(action,payload);
    S.flash={text:[r.message,...(r.effects||[]).filter(Boolean)].filter(Boolean).join(' '),kind:'good'};
    return r;
  }catch(e){S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;render();}
}
const ask=(title,msg,label,money)=>S.env.confirmAction(title,msg,label,money);
/* 💼 hired players: the server's view (offers, my offers, friends) and its ops */
const took=d=>{if(d?.state&&typeof d.revision==='number')S.env.api.accept({state:d.state,revision:d.revision});};
async function loadHire(){
  if(S.loading)return;S.loading=true;
  try{const d=await S.env.api.json('/api/quay');took(d);S.hire=d;}
  catch(e){S.hire={error:e.status===404?'Quầy đang dọn hàng. Mở lại sau ít phút nhé.':(e.message||'Chưa tải được. Thử lại nhé.')};}
  finally{S.loading=false;render();}
}
async function hireSend(op,body={}){
  S.busy=true;render();
  try{const d=await S.env.api.post(`/api/quay/${op}`,body);took(d);if(d.message)S.flash={text:d.message,kind:'good'};S.busy=false;await loadHire();return d;}
  catch(e){S.flash={text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;render();}
}
const stallOf=id=>(V()?.stalls||[]).find(x=>x.id===id);
const num=(sel,fallback=0)=>{const v=Number(S.dlg?.querySelector(sel)?.value);return Number.isFinite(v)?Math.round(v):fallback;};

async function onClick(op,data){
  switch(op){
    case'close':S.dlg.close();return;
    case'help':S.help[data.key]=!S.help[data.key];render();return;
    case'back':S.view='list';S.pick=null;render();return;
    case'new':{const can=V()?.can||[];S.view='open';S.pick={trade:can[0]||'',place:'xe',name:''};S.flash=null;render();S.dlg.querySelector('.qy-body')?.scrollTo?.(0,0);return;}
    case'trade':if(S.pick){S.pick.trade=data.id;render();}return;
    case'place':if(S.pick){S.pick.place=data.id;render();}return;
    case'open':{const p=S.pick,P=place(p?.place);if(!p?.trade||!P.id)return;
      const total=P.price+P.fund;
      if(await ask(`Mở ${P.name.toLowerCase()}?`,`${xu(P.price)} + ${xu(P.fund)} vốn quầy.`,`Mở quầy · ${xu(total)}`,{cost:total,pocket:['wallet','account']})){
        const name=(p.name||'').trim();
        const r=await send('jr_quay_open',{trade:p.trade,place:p.place,...(name?{name}:{}),confirm:true});
        if(r){S.view='list';S.pick=null;render();}
      }return;}
    case'more':S.open[data.id]=S.open[data.id]===data.part?'':data.part;render();return;
    case'till':send('jr_quay_till',{stall:data.id,...(data.to?{to:data.to}:{})});return;
    case'fund':{const amount=num(`#qy-fund-${data.id}`);if(!amount){S.flash={text:'Nhập số xu nhé.',kind:'bad'};render();return;}
      send('jr_quay_fund',{stall:data.id,amount:data.sign==='-'?-Math.abs(amount):Math.abs(amount)});return;}
    case'order':send('jr_quay_order',{stall:data.id,level:data.level});return;
    case'step':{const k=data.key;const base=S.wage[k]??Number(data.wage);S.wage[k]=Math.min(Number(data.max||1e6),Math.max(Number(data.min||1),base+Number(data.by)));render();return;}
    case'tab':S.tab=data.tab;S.flash=null;render();if(S.tab==='jobs')loadHire();return;
    case'reload':S.hire=null;loadHire();return;
    case'to':S.to[data.id]=data.code||'';render();return;
    case'post':{const st=stallOf(data.id);if(!st)return;const w=S.wage[`p:${st.id}`]??Number(data.wage);
      if(await ask('Đăng ca làm thêm?',`Giữ ${xu(w)} từ két và vốn quầy. Không ai làm thì về lại.`,`Đăng ca · ${xu(w)}`))
        hireSend('post',{stall:st.id,wage:w,...(S.to[st.id]?{to:S.to[st.id]}:{})});return;}
    case'cancel':hireSend('cancel',{id:data.id});return;
    case'accept':hireSend('accept',{id:data.id});return;
    case'decline':hireSend('decline',{id:data.id});return;
    case'quit':if(await ask('Bỏ ca này?','Không mất gì cả. Lương về lại cho chủ quầy.','Bỏ ca'))hireSend('quit');return;
    case'go':S.dlg.close();await S.env.act('choose',{career:data.career});return;
    case'hire':{const k=`c:${data.id}:${data.cand}`;send('jr_quay_hire',{stall:data.id,cand:data.cand,wage:S.wage[k]??Number(data.wage)}).then(r=>{if(r)delete S.wage[k];});return;}
    case'wage':{const k=`s:${data.id}:${data.staff}`;send('jr_quay_wage',{stall:data.id,staff:data.staff,wage:S.wage[k]??Number(data.wage)}).then(r=>{if(r)delete S.wage[k];});return;}
    case'fire':if(await ask(`Cho ${data.name} nghỉ?`,'','Cho nghỉ'))send('jr_quay_fire',{stall:data.id,staff:data.staff,confirm:true});return;
    case'buy':{const st=stallOf(data.id),it=CAT()?.items.find(x=>x.id===data.item);if(!st||!it)return;const price=it.price[st.place];
      if(await ask(`Lắp ${it.name.toLowerCase()}?`,it.line,`Lắp · ${xu(price)}`,{cost:price,pocket:['wallet','account']}))send('jr_quay_buy',{stall:data.id,item:data.item,confirm:true});return;}
    case'police':send('jr_quay_police',{stall:data.id});return;
    case'pay':send('jr_quay_pay',{stall:data.id});return;
    case'sell':{const st=stallOf(data.id);if(!st)return;
      if(await ask(`Sang nhượng ${st.name}?`,'Nhận lại một nửa giá chỗ, cả két và vốn quầy.',`Sang nhượng · ${xu(st.sell)}`))send('jr_quay_sell',{stall:data.id,confirm:true});return;}
  }
}

/* ---- rendering ---- */
function render(){
  if(!S.dlg)return;
  const body=S.dlg.querySelector('.qy-body'),top=body?.scrollTop;
  S.dlg.querySelector('.qy-root').innerHTML=page();
  if(top)S.dlg.querySelector('.qy-body').scrollTop=top;
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
const helpBtn=key=>`<button type="button" class="qy-help" data-qy="help" data-key="${key}" aria-label="Giải thích" aria-expanded="${!!S.help[key]}">?</button>`;
const helpText=(key,text)=>S.help[key]?`<p class="bk-hint qy-hint">${text}</p>`:'';
function head(){
  const v=V(),n=v?.stalls?.length||0,till=(v?.stalls||[]).reduce((a,x)=>a+x.till,0);
  const back=S.view!=='list'?`<button class="icon-btn" type="button" data-qy="back" aria-label="Quay lại">${icon('back',21)}</button>`:'<span class="qy-logo" aria-hidden="true">🏪</span>';
  return `<header class="sheet-head bk-head">${back}
    <div class="grow"><span class="eyebrow">NGÀY SỐNG ${fmt(J().life_day)}</span><h2 id="qy-title">Quầy của bạn</h2><p>${n?`${n} quầy · két ${xu(till)}`:'Mở quầy, thuê người, thu két'}</p></div>
    <button class="icon-btn" type="button" data-qy="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
}
const flash=()=>`<p class="bk-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
function page(){
  const v=V(),cat=CAT();
  const note=(t,p,extra='')=>head()+`<div class="sheet-body bk qy-body"><section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🏪</div><h3>${t}</h3><p>${p}</p>${extra}</section></div>`;
  if(!cat)return note('Quầy đang dọn hàng','Mở lại sau ít phút nhé.');   // an older server: no counters yet
  if(!J().story)return note('Chỉ có trong hành trình','Vào hành trình để mở quầy riêng.');
  const tabs=S.view==='open'?'':mainTabs();
  if(S.tab==='jobs'&&S.view!=='open')return head()+`<div class="sheet-body bk qy-body">${tabs}${flash()}${jobsView()}</div>`;
  if(!v)return head()+`<div class="sheet-body bk qy-body">${tabs}<section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🏪</div><h3>Chưa mở được quầy</h3><p>Mở từ chương ${cat.chapter}.</p>${helpBtn('lock')}${helpText('lock',`Làm ${cat.served} việc ở một nghề bán hàng (trà sữa, tạp hóa, hoa…) rồi quay lại.`)}</section></div>`;
  const inner=S.view==='open'?openView(v):listView(v);
  return head()+`<div class="sheet-body bk qy-body">${tabs}${flash()}${inner}</div>`;
}

function mainTabs(){
  const dot=V()?.shift?' <i class="qy-dot" aria-label="Có ca"></i>':'';
  return `<div class="segmented qy-main" role="tablist">${[['mine','🏪 Quầy của tôi'],['jobs',`💼 Làm thêm${dot}`]].map(([k,l])=>
    `<button type="button" role="tab" aria-selected="${S.tab===k}" class="${S.tab===k?'active':''}" data-qy="tab" data-tab="${k}">${l}</button>`).join('')}</div>`;
}

/* 💼 Làm thêm: my shift, then the counters that need someone. */
function jobsView(){
  const h=S.hire,sh=V()?.shift;
  if(!h)return '<section class="bk-card bk-center"><p class="bk-hint">Đang tải…</p></section>';
  if(h.error)return `<section class="bk-card bk-center"><p>${esc(h.error)}</p><div class="bk-actions center">${btn('Thử lại','reload',{},'ghost')}</div></section>`;
  const R=h.rules||{};
  const mine=sh?`<section class="bk-card qy-shift"><div class="qy-top"><span class="qy-tile" aria-hidden="true">💼<i>${trade(sh.career).emoji}</i></span>
      <div class="grow"><h3>${esc(sh.name)}</h3><p class="qy-line">${esc(sh.who)} · ${xu(sh.wage)}</p></div></div>
    <p class="qy-line">Làm ${esc(trade(sh.career).name)}: xong ${R.tasks||2} việc rồi khép ca.</p>
    <div class="bk-actions">${btn('Vào làm','go',{career:sh.career},'primary')}${btn('Bỏ ca','quit',{},'ghost')}</div></section>`:'';
  const rows=(h.board||[]).map(b=>`<li class="qy-person"><div class="grow"><b>${b.emoji} ${esc(b.name)}</b>${b.invite?' <span class="qy-tag">Mời bạn</span>':''}<small>${esc(b.owner)} · ${xu(b.wage)}</small></div>
      <div class="qy-person-act">${btn('Nhận ca','accept',{id:b.id},'small primary',sh?'Bạn đang có một ca':'')}${b.invite?btn('Từ chối','decline',{id:b.id},'small ghost'):''}</div></li>`).join('');
  const board=`<section class="bk-card"><h3>Quầy cần người ${helpBtn('jobs')}</h3>
    ${helpText('jobs',`Nhận một ca, làm một ngày đúng nghề đó. Xong ${R.tasks||2} việc rồi khép ca là lương vào ví. Bỏ ca lúc nào cũng được, không mất gì.`)}
    ${h.lock?`<p class="bk-hint">${esc(h.lock)}</p>`:rows?`<ul class="qy-list">${rows}</ul>`:'<p class="bk-hint">Chưa có quầy nào cần người. Ghé lại sau nhé.</p>'}</section>`;
  return mine+board;
}
const JOB_LINE={open:x=>x.to?`Chờ ${x.to} trả lời`:'Đang chờ người nhận',taken:x=>`${x.worker} đang làm ca`,paid:x=>`${x.worker} xong ca: +${xu(x.earned)} vào két`,
  lapsed:()=>'Ca chưa đủ việc: lương về lại',quit:x=>`${x.worker||'Người làm'} bận: lương về lại`,declined:x=>`${x.to||'Bạn ấy'} bận: lương về lại`,
  expired:()=>'Hết hạn: lương về lại',cancelled:()=>'Đã hủy',gone:()=>'Đã hủy'};
function hirePart(st){
  const h=S.hire;
  if(!h){loadHire();return '<p class="bk-hint">Đang tải…</p>';}
  if(h.error)return `<p class="bk-hint">${esc(h.error)}</p>`;
  const R=h.rules||{},max=Math.max(R.wage_min||10,Math.min(R.wage_max||120,st.value||0)),min=R.wage_min||10;
  const offers=(h.mine||[]).filter(x=>x.stall===st.id).map(x=>`<li class="qy-person"><div class="grow"><b>💼 ${xu(x.wage)}</b><small>${esc((JOB_LINE[x.status]||(()=>''))(x))}</small></div>
      ${x.status==='open'?`<div class="qy-person-act">${btn('Hủy','cancel',{id:x.id},'small ghost')}</div>`:''}</li>`).join('');
  const k=`p:${st.id}`,w=Math.min(max,S.wage[k]??Math.min(30,max));
  const to=S.to[st.id]||'';
  const chips=[['','Ai cũng được'],...(h.friends||[]).slice(0,8).map(f=>[f.code,f.name])].map(([code,name])=>
    `<button type="button" class="qy-chip${to===code?' on':''}" data-qy="to" data-id="${st.id}" data-code="${esc(code)}">${esc(name)}</button>`).join('');
  const form=h.lock?`<p class="bk-hint">${esc(h.lock)}</p>`:`<div class="qy-chips">${chips}</div>
    <div class="qy-person"><div class="grow"><small>Lương một ca</small></div><div class="qy-person-act">${stepper(k,w,st.id,'',min,max)}${btn('Đăng ca','post',{id:st.id,wage:w},'small primary',st.closed?'Quầy đang đóng':'')}</div></div>`;
  return `<h4>🙋 Thuê người chơi ${helpBtn('hire')}</h4>
    ${helpText('hire',`Một người chơi làm một ngày nghề này cho quầy. Xong ${R.tasks||2} việc thì họ nhận lương, két nhận tiền bán. Lương giữ trước từ két, không ai làm thì về lại.`)}
    ${offers?`<ul class="qy-list">${offers}</ul>`:''}${form}`;
}

/* The counters, or the first one to open. */
function listView(v){
  if(!v.stalls.length){
    if(v.lock)return `<section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🏪</div><h3>Chưa mở được quầy</h3><p>${esc(v.lock)}</p>${helpBtn('lock')}${helpText('lock',`Làm ${CAT().served} việc ở một nghề bán hàng rồi quay lại.`)}</section>`;
    return `<section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🏪</div><h3>Mở quầy đầu tiên</h3><p>Bán món bạn rành, thuê người đứng quầy.</p>
      <div class="bk-actions center">${btn('Mở quầy','new',{},'primary')}</div>${helpBtn('first')}${helpText('first',`Mỗi ngày sống, quầy tự bán. Hôm đông hôm vắng, đa số ngày có lời. Nhớ ghé thu két: ${CAT().left} ngày không thu, quầy đóng chờ bạn.`)}</section>`;
  }
  const more=v.stalls.length<CAT().max&&!v.lock?`<div class="bk-actions center">${btn('＋ Mở thêm quầy','new',{},'ghost')}</div>`:'';
  return v.stalls.map(stallCard).join('')+more;
}

function stallCard(st){
  const P=place(st.place),T=trade(st.trade),cat=CAT();
  const today=st.today||{};
  const status=st.due?`Chờ đóng ${xu(st.due)} tiền thuê`:st.closed?'Đóng cửa chờ chủ':!st.staff.length?'Chưa có người đứng quầy':
    `Hôm nay ${cat.weather[today.w]||''} · ${cat.pace[today.pace]||''}${today.x3?' · 🔥':''}`;
  const week=st.hist.reduce((a,h)=>a+h[2],0);
  const part=S.open[st.id]||'';
  const alerts=[
    st.case?`<div class="bk-alert bad qy-row"><span>🚨 ${st.case.all?'Mất cả két':'Trộm lấy'} ${xu(st.case.lost)}</span>${st.case.rep?'<small>Đã báo công an</small>':btn('Báo công an','police',{id:st.id},'small')}</div>`:'',
    st.due?`<div class="bk-alert warn qy-row"><span>🧾 Nợ tiền thuê ${xu(st.due)}</span>${btn('Đóng tiền','pay',{id:st.id},'small primary')}</div>`:'',
    !st.closed&&st.left<=1&&st.till>0?`<p class="bk-alert warn">Ghé thu két kẻo quầy đóng nhé.</p>`:'',
  ].join('');
  const tabs=[['staff',`👥 Người (${st.staff.length}/${P.slots||1})`],['stock','📦 Hàng'],['fund','💼 Vốn'],['up','🛠️ Nâng cấp']];
  return `<section class="bk-card qy-stall">
    <div class="qy-top"><span class="qy-tile" aria-hidden="true">${P.emoji||'🏪'}<i>${T.emoji}</i></span>
      <div class="grow"><h3>${esc(st.name)}</h3><p class="qy-line">${esc(status)}</p></div></div>
    ${alerts}
    <div class="qy-till"><div><small>Két</small><strong>${xu(st.till)}</strong>${st.hist.length?`<small>${st.hist.length} ngày qua: ${week>=0?'+':'−'}${xu(Math.abs(week))}</small>`:''}</div>
      ${btn(st.closed&&!st.due&&!st.till?'Mở lại quầy':'Thu két','till',{id:st.id},'primary',st.till||st.closed?'':'Két đang trống')}</div>
    <div class="segmented qy-tabs" role="tablist">${tabs.map(([k,l])=>`<button type="button" role="tab" aria-selected="${part===k}" class="${part===k?'active':''}" data-qy="more" data-id="${st.id}" data-part="${k}">${l}</button>`).join('')}</div>
    ${part==='staff'?staffPart(st,P):part==='stock'?stockPart(st):part==='fund'?fundPart(st):part==='up'?upPart(st):''}
  </section>`;
}

function stepper(key,value,id,extra,min=1,max=1e6){
  return `<span class="qy-step">${btn('−','step',{id,key,by:-1,wage:value,min,max},'small ghost')}<b>${fmt(value)}</b>${btn('＋','step',{id,key,by:1,wage:value,min,max},'small ghost')}</span>${extra||''}`;
}
function staffPart(st,P){
  const rows=st.staff.map(x=>{const k=`s:${st.id}:${x.id}`,w=S.wage[k]??x.wage;
    return `<li class="qy-person"><div class="grow"><b>${MOOD(x.mo)} ${esc(x.name)}</b>${x.g?' <span title="Rất cẩn thận">⭐</span>':''}<small>Lương ${xu(x.wage)}/ngày · xin ${xu(x.ask)}</small></div>
      <div class="qy-person-act">${stepper(k,w,st.id)}${w!==x.wage?btn('Lưu','wage',{id:st.id,staff:x.id,wage:w},'small primary'):btn('Cho nghỉ','fire',{id:st.id,staff:x.id,name:x.name},'small ghost')}</div></li>`;}).join('');
  const cands=(st.cands||[]).map(c=>{const k=`c:${st.id}:${c.id}`,w=S.wage[k]??c.ask;
    return `<li class="qy-person"><div class="grow"><b>${esc(c.name)}</b>${c.g?' ⭐':''}<small>${esc(c.bio)}</small><small>Xin ${xu(c.ask)}/ngày</small></div>
      <div class="qy-person-act">${stepper(k,w,st.id)}${btn('Thuê','hire',{id:st.id,cand:c.id,wage:w},'small primary')}</div></li>`;}).join('');
  return `<div class="qy-part">${rows?`<ul class="qy-list">${rows}</ul>`:''}
    ${cands?`<h4>Đang tìm việc ${helpBtn('cand')}</h4>${helpText('cand','Tự đặt lương. Trả cao thì vui, bán đắt hàng hơn. Dưới 60% mức xin là họ không nhận.')}<ul class="qy-list">${cands}</ul>`:''}
    ${!rows&&!cands?'<p class="bk-hint">Chưa có ai.</p>':''}${hirePart(st)}</div>`;
}
function stockPart(st){
  const cat=CAT();
  return `<div class="qy-part"><p class="qy-line">Hôm nay ${cat.weather[st.today?.w]||''} · ${cat.pace[st.today?.pace]||''} · khoảng ${fmt(st.today?.n)} khách ${helpBtn('stock')}</p>
    ${helpText('stock','Ít: không lo ế. Nhiều: không lo hết hàng. Hàng tươi (hoa, bánh) ế thì hư.')}
    <div class="segmented qy-order" role="radiogroup" aria-label="Nhập hàng">${cat.orders.map(o=>`<button type="button" role="radio" aria-checked="${st.order===o.id}" class="${st.order===o.id?'active':''}" data-qy="order" data-id="${st.id}" data-level="${o.id}"${S.busy?' disabled':''}>${esc(o.name)}</button>`).join('')}</div>
    ${st.hist.length?`<ol class="qy-days">${st.hist.slice().reverse().map(h=>`<li><span>Ngày ${fmt(h[0])}</span><span>${fmt(h[1])} khách</span><b class="${h[2]>=0?'up':'down'}">${h[2]>=0?'+':'−'}${xu(Math.abs(h[2]))}</b></li>`).join('')}</ol>`:''}</div>`;
}
function fundPart(st){
  return `<div class="qy-part"><p class="qy-line">Vốn quầy <b>${xu(st.fund)}</b> ${helpBtn('fund')}</p>
    ${helpText('fund','Tiền hàng, lương, điện lấy từ két trước, thiếu mới lấy vốn. Hết vốn thì quầy nghỉ ngày đó.')}
    <div class="qy-fund"><label class="bk-field"><span>Số xu</span><input type="number" inputmode="numeric" min="1" step="10" id="qy-fund-${st.id}" value="50"></label>
      ${btn('Góp vào','fund',{id:st.id,sign:'+'},'primary')}${btn('Rút ra','fund',{id:st.id,sign:'-'},'ghost')}</div>
    <div class="bk-actions">${btn('Két vào vốn','till',{id:st.id,to:'fund'},'ghost',st.till?'':'Két đang trống')}${btn(`Sang nhượng · ${xu(st.sell)}`,'sell',{id:st.id},'danger')}</div></div>`;
}
function upPart(st){
  const items=CAT().items.map(it=>{const have=st.items.includes(it.id);
    return `<li class="qy-up${have?' on':''}"><span class="qy-up-emoji" aria-hidden="true">${it.emoji}</span><div class="grow"><b>${esc(it.name)}</b><small>${esc(it.line)}</small></div>
      ${have?'<span class="qy-have">✓</span>':btn(xu(it.price[st.place]),'buy',{id:st.id,item:it.id},'small')}</li>`;}).join('');
  return `<div class="qy-part"><ul class="qy-list">${items}</ul></div>`;
}

/* Opening a counter: what, where, a name. */
function openView(v){
  const p=S.pick||{},cat=CAT(),P=place(p.place);
  const trades=Object.keys(cat.trades).map(id=>{const T=cat.trades[id],ok=v.can.includes(id);
    return `<button type="button" class="qy-chip${p.trade===id?' on':''}" data-qy="trade" data-id="${id}"${ok&&!S.busy?'':' disabled'}${ok?'':` title="Làm ${cat.served} việc ở nghề này trước"`}>${T.emoji} ${esc(T.name)}</button>`;}).join('');
  const places=cat.places.map(x=>`<button type="button" class="qy-place${p.place===x.id?' on':''}" data-qy="place" data-id="${x.id}"><span class="qy-up-emoji" aria-hidden="true">${x.emoji}</span>
    <span class="grow"><b>${esc(x.name)}</b><small>${xu(x.price)} · ${x.slots} người · thuê ${xu(x.rent)}/tháng</small></span></button>`).join('');
  return `<section class="bk-card"><h3>Bán gì?</h3><div class="qy-chips">${trades}</div></section>
    <section class="bk-card"><h3>Ở đâu? ${helpBtn('place')}</h3>${helpText('place','Chỗ to thì đông khách, nhiều người đứng, nhưng tiền thuê cao hơn.')}<div class="qy-places">${places}</div></section>
    <section class="bk-card"><label class="bk-field"><span>Tên quầy</span><input name="qy-name" maxlength="24" value="${esc(p.name||'')}" placeholder="${esc(`${trade(p.trade).name||''} ${S.env.api.state?.name||''}`.trim())}"></label>
      <div class="bk-actions">${btn(`Mở quầy · ${xu((P.price||0)+(P.fund||0))}`,'open',{},'primary',p.trade?'':'Chọn món bán trước')}</div></section>`;
}
