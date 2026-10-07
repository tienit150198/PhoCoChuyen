/** 💍 Hôn nhân và 👥 Bạn bè: bạn bè (tìm đúng tên đăng nhập), tiệm nhẫn đổi màu, cầu hôn một người bạn,
 * kế hoạch cưới, đếm ngày, thiệp kỷ niệm; sau cưới: quỹ chung, gửi tiền / xin trợ giúp / sổ nợ, tương tác
 * mỗi ngày và điểm hạnh phúc; ly hôn.
 * Every rule and every number that moves money lives on the server (game/marriage.py, friends.py,
 * couple.py; GET /api/marriage, POST /api/marriage/<op>); the planner and the ring colours only mirror
 * the price list for a live preview. Its own dialog (not the shared #sheet): opened by the rail entries
 * "Bạn bè" / "Hôn nhân", by Cài đặt → Tài khoản, the journey profile chip and the ticker. Names are
 * display names only, always escaped; nothing here ever shows a username, an account id or an IP. */
import {icon,escapeHTML as esc} from '../icons.js';
import {myPortrait} from './look.js';
import {confirmPurchase} from './payment.js';
import {familyView,familyAction,familyRefresh} from './family.js';

const S={dlg:null,env:null,view:null,catalog:null,tab:'home',plan:null,planKey:'',quote:null,qTimer:0,qSeq:0,flash:null,busy:false,
  form:{code:'',ring:'',message:'',announce:true},found:null,confirm:'',answer:{},loading:false,err:'',
  pick:{},recolor:null,fq:'',fres:null,partyAt:0,family:{},familySection:null,refresh:null,loadSeq:0,
  money:{dep:'',wd:'',send:'',note:'none',loan:false,help:'',hnote:'none',hloan:false,gift:''},repay:{},cline:{},lline:{}};
const rid=()=>globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const signed=n=>`${n>0?'+':n<0?'−':''}${fmt(Math.abs(n))} xu`;
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,mr,data={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-mr="${mr}"${attrs(data)}${S.busy?' disabled':''}${extra}>${label}</button>`;
const wallet=()=>Number(S.env?.api?.state?.journey?.wallet??S.view?.me?.wallet??0);

/* ---- stylesheet on first use ---- */
let cssReady=null;
export function ensureMarriageCss(){
  if(cssReady)return cssReady;
  const href=globalThis.__mnlBoot?.asset?.('/css/marriage.css')||'/css/marriage.css';
  cssReady=new Promise(done=>{
    if(document.querySelector('link[data-mr-css]')){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=href;l.dataset.mrCss='';
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
  return cssReady;
}

/* ---- the dialog ---- */
function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium mr-sheet';d.setAttribute('aria-labelledby','mr-title');
  d.innerHTML='<div class="mr-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}  // a tap on the backdrop
    const el=e.target.closest('[data-mr]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.mr,el.dataset,el);
  });
  d.addEventListener('change',e=>{const el=e.target.closest('[data-mr-field]');if(el)onField(el,true);});
  d.addEventListener('input',e=>{const el=e.target.closest('[data-mr-field]');if(el)onField(el,false);});
  d.addEventListener('submit',e=>e.preventDefault());
  d.addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target.dataset?.mrField==='fq'){e.preventDefault();onClick('fsearch',{},e.target);}});
  d.addEventListener('close',()=>{S.flash=null;S.refresh?.stop();S.loadSeq++;});
  S.dlg=d;return d;
}

/** Rail "Hôn nhân", Cài đặt → Tài khoản, the ticker. */
export async function openMarriage(env,tab,section){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    // Re-render only when what this dialog shows changed (a re-render under a finger would eat the tap).
    let seen='';env.api.addEventListener('state',()=>{const st=env.api.state,key=JSON.stringify([st?.journey?.wallet,st?.marriage]);if(key===seen)return;seen=key;if(S.dlg?.open&&!S.busy&&!editingFamily())render();});
    window.addEventListener('mnl:marriage',()=>{if(S.dlg?.open&&!editingFamily())load();});
  }
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureMarriageCss();
  const d=dialog();if(tab)S.tab=tab;
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();S.familySection=section||null;load();
  S.refresh??=familyRefresh({active:()=>Boolean(S.dlg?.open&&!document.hidden&&!S.busy&&!S.loading&&!(S.dlg.contains(document.activeElement)&&['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))),read:()=>S.env.api.json('/api/marriage'),apply:data=>{take(data);render();}});
  S.refresh.start();
}
export async function marriageAction(action,data,el,env){
  if(action!=='marriage'&&action!=='friends')return false;
  // "Hôn nhân" never reopens on the Bạn bè tab (a pending proposal would stay hidden there).
  await openMarriage(env,action==='friends'?'friends':data?.tab||(S.tab==='friends'?'home':''),data?.section);return true;
}

const editingFamily=()=>Boolean(S.dlg?.contains(document.activeElement)&&document.activeElement?.dataset?.mrField?.startsWith('family:'));

async function load(){
  const {api}=S.env,seq=++S.loadSeq;S.refresh?.invalidate();S.loading=true;S.err='';render();
  try{
    const data=await api.json(`/api/marriage${S.catalog?'':'?catalog=1'}`);
    if(seq!==S.loadSeq||!S.dlg?.open||api!==S.env.api)return;
    if(data.catalog)S.catalog=data.catalog;
    take(data);
  }catch(e){if(seq===S.loadSeq)S.err=e.message||'Chưa tải được mục Hôn nhân.';}
  finally{if(seq===S.loadSeq){S.loading=false;render();}}
}
function take(view){
  if(!view)return;
  if(view.state&&typeof view.revision==='number')S.env.api.accept({state:view.state,revision:view.revision});
  S.view=view;
  const h=view.home||{};
  const alerts=view.guest?0:(view.incoming?.length||0)+(view.me?.notice?1:0)+(view.wedding&&view.wedding.status==='proposed'&&!view.wedding.mine?1:0)+(view.wedding?.status==='done'&&!view.wedding.seen?1:0)
    +(h.requests||[]).filter(r=>!r.mine).length+(h.debts||[]).filter(d=>!d.lender&&d.claim?.status==='pending').length+(h.moments||[]).filter(m=>m.new).length+(view.family?.requests||[]).filter(r=>!r.mine).length;
  badges(alerts,view.friends?.incoming?.length||0);
  const married=view.couple?.status==='married';
  if(['fund','love'].includes(S.tab)&&!married)S.tab='home';
  const w=view.wedding;
  if(view.couple?.status==='engaged'&&(!w||['rejected'].includes(w.status)||(w.status==='proposed'&&w.mine))){
    const key=`${view.couple.id}:${w?.id||0}:${w?.version||0}`;
    if(!S.plan||S.planKey!==key){S.plan=w?{...w.plan,mine:w.split_mine,announce:w.announce_mine}:defaultPlan();S.plan.at??=defaultAt();S.planKey=key;S.quote=null;askQuote();}
  }
  if(S.tab==='plan'&&view.couple?.status!=='engaged')S.tab='home';
  if(!S.form.message&&S.catalog)S.form.message=S.catalog.messages[0].id;
  const owned=(view.rings||[]).filter(r=>r.status==='owned');
  if(!owned.some(r=>r.id===S.form.ring))S.form.ring=owned[0]?.id||'';
}
/** Rail badges: "Hôn nhân" (proposals, plans, the spouse's moments and asks) and "Bạn bè" (friend requests). */
export function badges(marriage,friends){
  const api=S.env?.api||null;if(api){api.marriageAlerts=marriage;api.friendAlerts=friends;}
  for(const [action,n] of [['marriage',marriage],['friends',friends]])
    document.querySelectorAll(`[data-action="${action}"]`).forEach(b=>{if(b.closest('.mr-sheet'))return;b.querySelector('em.badge')?.remove();if(n){const em=document.createElement('em');em.className='badge';em.textContent=String(n);b.append(em);}});
  document.dispatchEvent(new Event('mnl:badges'));   // the menu hub that holds them (app.js) shows the sum
}
/** `quiet` (marks like moments_seen / seen, lookups that render their own result): runs without S.busy, so the
 * buttons are never disabled by a background call; it re-renders once at the end if nothing else is in flight. */
async function post(op,body={},{quiet=false}={}){
  const {api}=S.env;
  S.refresh?.invalidate();S.loadSeq++;S.loading=false;
  if(!quiet){S.busy=true;render();}
  try{
    const data=await api.json(`/api/marriage/${op}`,{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify(body)});
    if(data.state&&typeof data.revision==='number')api.accept({state:data.state,revision:data.revision});
    if(data.view)take(data.view);
    if(data.message)S.flash={text:data.message,kind:'good'};
    return data;
  }catch(e){S.flash={text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.refresh?.invalidate();if(!quiet){S.busy=false;render();}else if(S.dlg?.open&&!S.busy)render();}
}

/* ---- the planner (a mirror of wedding_content + marriage.costs, for the live breakdown) ---- */
function defaultPlan(){return {venue:'restaurant',tables:20,menu:'tieu_chuan',ceremonies:{dam_ngo:false,an_hoi:0,gia_tien:true,le_duong:false},extras:['mc','cards'],days:S.catalog?.days?.[2]||3,mine:50,announce:true,at:defaultAt()};}
/* 💍 The wedding's real date and time (Vietnam time; game/wedding_live.py: 1 hour to 14 days ahead). */
const VN_MS=7*3600*1000;
const vnParts=at=>{const d=new Date(at*1000+VN_MS);return {date:d.toISOString().slice(0,10),time:d.toISOString().slice(11,16)};};
const atOf=(date,time)=>{const [y,m,d]=date.split('-').map(Number),[h,mi]=(time||'20:00').split(':').map(Number);return (Date.UTC(y,m-1,d,h,mi)-VN_MS)/1000;};
function defaultAt(){const now=Date.now()/1000,t=vnParts(now+86400);return atOf(t.date,'20:00');}   // tomorrow 20:00
const soon=p=>Boolean(p?.at)&&p.at<Date.now()/1000+3600;   // the server books a wedding at least 1 hour ahead (game/wedding_live.py)
/** 🎉 The live party (game/wedding_live.py party_view): the first choice is 30 minutes from now, on a 5-minute mark. */
const partyDefault=()=>Math.ceil((Date.now()/1000+30*60)/300)*300;
function partyCard(c){
  const p=c.party;if(!p)return '';
  const when=(label)=>{const at=S.partyAt||partyDefault(),v=vnParts(at),now=Date.now()/1000;
    return `<div class="mr-when"><label class="field" for="mr-pdate">Ngày<input class="input" id="mr-pdate" type="date" data-mr-field="pdate" min="${vnParts(now).date}" max="${vnParts(now+(p.max_ahead||14*86400)).date}" value="${v.date}"></label>
      <label class="field" for="mr-ptime">Giờ<input class="input" id="mr-ptime" type="time" step="300" data-mr-field="ptime" value="${v.time}"></label></div>${btn(label,'party',{},'primary')}`;};
  const perks=`<p class="mr-hint">Miễn phí. Tiệc 10 phút có MC, cỗ, múa lân, nhạc cưới. Ai có mặt được 20 xu mỗi phút, mỗi khách đến hai bạn được 15 xu.</p>`;
  if(p.state==='none')return `<section class="mr-card mr-accent"><h3>🎉 Tổ chức tiệc cưới</h3><p>Chọn ngày giờ để cả phố vào dự. Đây cũng là ngày cưới hiện trên thẻ của hai bạn.</p>${when('Chốt giờ tiệc')}${perks}</section>`;
  if(p.state==='done')return `<section class="mr-card"><h3>🎉 Tiệc cưới đã tổ chức</h3><p>${esc(p.at_label)}${p.guests?` · ${p.guests} khách đến chung vui 💛`:''}</p></section>`;
  if(p.state==='live')return `<section class="mr-card mr-accent"><h3>🎊 Tiệc cưới đang mở!</h3><p>${esc(p.at_label)}</p><div class="mr-actions">${btn('Vào dự','pgo',{id:p.id},'primary big')}${p.invited?'':btn('💌 Mời khách','pinvite',{},'cream')}</div></section>`;
  return `<section class="mr-card mr-accent"><h3>🎉 Tiệc cưới lúc ${esc(p.at_label)}</h3><p>Tiệc mở trước 5 phút ở Khu phố › Lịch cưới. Bạn bè được nhắc trước 30 phút.</p>
    <div class="mr-actions">${p.invited?'<span class="tag">💌 Đã mời bạn bè và cả phố</span>':btn('💌 Mời khách (miễn phí)','pinvite',{},'primary')}</div>
    ${p.can_move?`<details class="mr-more"><summary>Đổi giờ</summary>${when('Lưu giờ mới')}</details>`:''}${perks}</section>`;
}
const atLabel=at=>{const p=vnParts(at);return `${p.date.slice(8,10)}/${p.date.slice(5,7)}/${p.date.slice(0,4)} · ${p.time}`;};
const venueOf=id=>S.catalog.venues.find(v=>v.id===id);
function costs(p){
  const c=S.catalog,v=venueOf(p.venue),m=c.menus.find(x=>x.id===p.menu),tp=v.table_price[p.menu],seats=p.tables*c.seats;
  const sections=[
    {id:'venue',name:'Địa điểm',lines:[{label:`${v.emoji} ${v.name} · phí địa điểm`,amount:v.fee}]},
    {id:'reception',name:'Tiệc',lines:[{label:`${p.tables} bàn × ${tp} xu · thực đơn ${m.name.toLowerCase()}`,amount:p.tables*tp}]},
    {id:'ceremony',name:'Nghi lễ',lines:c.ceremonies.flatMap(x=>{
      const val=p.ceremonies[x.id];
      if(x.id==='an_hoi'){const o=x.options.find(o=>o.trays===val);return o?[{label:`${x.name} · tráp ${val} mâm`,amount:o.price}]:[];}
      return val?[{label:x.name,amount:x.price}]:[];})},
    {id:'extras',name:'Dịch vụ thêm',lines:c.extras.filter(x=>p.extras.includes(x.id)).map(x=>x.per10?{label:`${x.emoji} ${x.name} · ${seats} khách`,amount:x.per10*p.tables}:{label:`${x.emoji} ${x.name}`,amount:x.price})},
  ];
  for(const s of sections)s.subtotal=s.lines.reduce((a,l)=>a+l.amount,0);
  const total=sections.reduce((a,s)=>a+s.subtotal,0),deposit=Math.ceil(total*c.deposit_pct/100);
  return {sections,total,deposit,balance:total-deposit,seats,tp};
}
const split=(x,pct)=>{const a=Math.floor((x*pct+50)/100);return [a,x-a];};
function planBody(){const p=S.plan;return {venue:p.venue,tables:p.tables,menu:p.menu,ceremonies:{...p.ceremonies},extras:[...p.extras],days:p.days,...(p.at?{at:p.at}:{})};}
function askQuote(){
  clearTimeout(S.qTimer);const seq=++S.qSeq;
  S.qTimer=setTimeout(async()=>{
    try{const d=await S.env.api.json('/api/marriage/quote',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':S.env.api.csrf},body:JSON.stringify({plan:planBody(),mine:S.plan.mine})});
      if(seq===S.qSeq){S.quote=d.quote;paintBreakdown();}}
    catch{/* the breakdown still shows the costs */}
  },350);
}

/* ---- events ---- */
function onField(el,committed){
  const f=el.dataset.mrField,v=el.type==='checkbox'?el.checked:el.value;
  if(f.startsWith('family:')){S.family[f.slice(7)]=v;return;}
  if(f==='code'){S.form.code=v;S.found=null;return;}
  if(f==='confirm'){S.confirm=v;const b=S.dlg.querySelector('[data-mr="divorce"]');if(b)b.disabled=!v.trim();return;}
  if(f==='ring'){S.form.ring=v;return;}
  if(f==='message'){S.form.message=v;return;}
  if(f==='pannounce'){S.form.announce=v;return;}
  if(f==='answer'){S.answer[el.dataset.id]=v;return;}
  if(f==='wannounce'){S.answer.wedding=v;return;}
  if(f==='pdate'||f==='ptime'){const box=el.closest('.mr-when');const d=box?.querySelector('[data-mr-field=pdate]')?.value,t=box?.querySelector('[data-mr-field=ptime]')?.value;if(d&&t)S.partyAt=atOf(d,t);return;}
  if(f==='accept'){if(committed)post('settings',{accept:v});return;}
  if(f==='findable'){if(committed)post('friend_settings',{findable:v});return;}
  if(f==='fq'){S.fq=v;S.fres=null;return;}
  if(f==='to'){if(!committed)return;S.form.code=v;S.found=null;if(v)lookup(v);else render();return;}
  if(f.startsWith('m:')){S.money[f.slice(2)]=el.type==='checkbox'?v:v;if(committed&&(el.type==='checkbox'||el.tagName==='SELECT'))render();return;}
  if(f==='repay'){S.repay[el.dataset.id]=v;return;}
  if(f==='cline'){S.cline[el.dataset.id]=v;return;}
  if(f==='lline'){S.lline[el.dataset.id]=v;return;}
  const p=S.plan;if(!p)return;
  if(f==='tables'){p.tables=clampTables(Number(v));if(committed)render();else paintBreakdown();askQuote();return;}
  if(f==='mine'){p.mine=Math.max(0,Math.min(100,Math.round(Number(v)||0)));if(committed)render();else paintBreakdown();askQuote();return;}
  if(!committed&&el.type!=='checkbox'&&el.type!=='radio')return;
  if(f==='venue'){p.venue=v;p.tables=clampTables(p.tables);}
  else if(f==='menu')p.menu=v;
  else if(f==='days')p.days=Number(v);
  else if(f==='at_date'||f==='at_time'){const box=el.closest('.mr-when');const d=box?.querySelector('[data-mr-field=at_date]')?.value,t=box?.querySelector('[data-mr-field=at_time]')?.value;if(d&&t)p.at=atOf(d,t);}
  else if(f==='announce')p.announce=v;
  else if(f.startsWith('cer:'))p.ceremonies[f.slice(4)]=v;
  else if(f.startsWith('extra:')){const id=f.slice(6);p.extras=v?[...new Set([...p.extras,id])]:p.extras.filter(x=>x!==id);}
  render();askQuote();
}
const clampTables=n=>{const max=venueOf(S.plan.venue).max_tables;return Math.max(S.catalog.tables[0],Math.min(max,Math.round(n)||S.catalog.tables[0]));};

async function onClick(mr,data,el){
  if(S.busy&&mr.startsWith('fam:'))return;
  if(mr==='fam:request'||mr==='fam:rename'){const field=el.closest('section')?.querySelector('input[data-mr-field]');if(field&&!field.value.trim()){field.value='';field.reportValidity();return;}}
  if(await familyAction(mr,data,{env:S.env,family:S.view?.family,form:S.family,post}))return;
  const {env}=S;
  switch(mr){
    case'close':S.dlg.close();return;
    case'homeGuests':case'nav:guests':S.dlg.close();env.act('homeGuests',{code:data.code});return;
    case'workvisit':S.dlg.close();env.act('workVisit',{code:data.code});return;
    case'workdiscover':S.dlg.close();env.act('workVisit',{scope:'public'});return;
    case'tab':S.tab=data.tab;S.flash=null;S.recolor=null;render();S.dlg.scrollTop=0;
      if(data.tab==='love'&&(S.view?.home?.moments||[]).some(m=>m.new))post('moments_seen',{},{quiet:true});return;
    case'retry':load();return;
    case'nav:home':S.dlg.close();env.openSheet('home',{jrView:'home'});return;
    case'nav:personal':S.dlg.close();env.openSheet('home',{jrView:'household'});return;
    case'nav:house':S.dlg.close();(await import('./house.js')).openHouse(env);return;
    case'nav:inside':S.dlg.close();(await import('./reno.js')).openReno(env);return;
    case'register':S.dlg.close();env.ui.acctError='';env.ui.acctMode='register';env.openSheet('settings',{setTab:'account'});return;
    case'copy':{const code=S.view?.me?.code||'';try{await navigator.clipboard.writeText(code);S.flash={text:`Đã chép mã ${code}.`,kind:'good'};}catch{S.flash={text:`Mã của bạn: ${code}`,kind:'good'};}render();return;}
    case'seen':post('seen',data.wedding?{wedding:Number(data.wedding)}:{},{quiet:true});return;
    case'party':post('party',{at:S.partyAt||partyDefault()});return;
    case'pinvite':post('party_invite');return;
    case'pgo':S.dlg.close();import('./walk.js').then(m=>m.openWalk(env,{wedding:Number(data.id)})).catch(e=>console.warn('marriage: walk',e));return;
    case'ring_buy':{
      const r=S.catalog.rings.find(x=>x.id===data.tier);if(!r)return;
      const pk=pickOf(r.id),price=r.price+colorExtra(r.id,pk.metal,pk.stone),look=colorName(pk.metal,pk.stone);
      const how=await confirmPurchase(env,{title:`Mua ${r.name.toLowerCase()}?`,message:`${look}. ${xu(price)}. Nhẫn nằm trong hộp cho tới khi bạn trao đi.`,label:`Mua · ${xu(price)}`,cost:price,noJoint:true});
      if(!how)return;
      post('ring_buy',{tier:r.id,metal:pk.metal,stone:pk.stone,pay:how,rid:rid()});return;
    }
    case'mset':S.money[data.k]=data.v==='1';render();return;
    case'pick':{const pk=pickOf(data.tier);pk[data.k]=data.v;render();return;}
    case'rpick':if(S.recolor){S.recolor[data.k]=data.v;render();}return;
    case'ring_sell':{
      const r=ringById(data.ring);if(!r||r.status!=='owned'||!r.sell_price)return;
      if(!await env.confirmAction('Bán chiếc nhẫn dư?',`${r.name}: nhận ${xu(r.sell_price)} vào ví (80% giá mua). Phí đổi màu không hoàn lại. Nhẫn của hai bạn vẫn được giữ nguyên.`,'Bán nhẫn'))return;
      const result=await post('ring_sell',{ring:r.id,rid:rid()});if(result)S.recolor=null;render();return;
    }
    case'recolor':{const r=ringById(data.ring);if(r)S.recolor={ring:r.id,tier:r.tier,metal:r.metal,stone:r.stone};render();return;}
    case'recolor_cancel':S.recolor=null;render();return;
    case'recolor_do':{
      const rc=S.recolor,r=rc&&ringById(rc.ring);if(!r)return;
      const fee=recolorFee(r,rc.metal,rc.stone);
      const how=await confirmPurchase(env,{title:'Mang nhẫn ra tiệm kim hoàn?',message:`${colorName(rc.metal,rc.stone)}. Phí ${xu(fee)}.`,label:`Đổi màu · ${xu(fee)}`,cost:fee,noJoint:true});
      if(!how)return;
      const d=await post('ring_recolor',{ring:r.id,metal:rc.metal,stone:rc.stone,pay:how,rid:rid()});if(d)S.recolor=null;render();return;
    }
    case'lookup':lookup(S.form.code);return;
    case'fsearch':{
      const q=(S.dlg.querySelector('[data-mr-field="fq"]')?.value||S.fq).trim();S.fq=q;
      if(!q){S.flash={text:'Nhập đúng tên đăng nhập của bạn ấy nhé.',kind:'bad'};render();return;}
      const d=await post('friend_search',/^pcc[\s\-_.]?[0-9a-z]{6}$/i.test(q)?{code:q}:{username:q},{quiet:true});S.fres=d?(d.found||{why:d.why}):null;render();return;
    }
    case'freq':{const d=await post('friend_request',{code:data.code});if(d){S.fres=null;S.fq='';}load();return;}
    case'frespond':{
      if(data.answer==='block'&&!(await env.confirmAction('Chặn người này?','Người này sẽ không tìm thấy bạn, không gửi được lời mời kết bạn hay lời cầu hôn cho bạn nữa.','Chặn')))return;
      await post('friend_respond',{id:Number(data.id),answer:data.answer});load();return;
    }
    case'fcancel':await post('friend_cancel',{id:Number(data.id)});load();return;
    case'fremove':if(await env.confirmAction(`Hủy kết bạn với ${data.name}?`,'Hai bạn sẽ không còn trong danh sách bạn bè của nhau.','Hủy kết bạn')){await post('friend_remove',{code:data.code});load();}return;
    case'fblock':if(await env.confirmAction(`Chặn ${data.name}?`,'Người này sẽ không tìm thấy bạn, không gửi được lời mời kết bạn hay lời cầu hôn cho bạn nữa.','Chặn')){await post('friend_block',{code:data.code});load();}return;
    case'fpropose':S.tab='home';S.form.code=data.code;S.found=null;render();S.dlg.scrollTop=0;lookup(data.code);return;
    case'fund':{
      const dep=data.k==='dep',n=Math.round(Number(S.money[data.k]));
      if(!(n>0)){S.flash={text:'Nhập số xu nhé.',kind:'bad'};render();return;}
      const d=await post(dep?'fund_deposit':'fund_withdraw',{amount:n,rid:rid()});if(d)S.money[data.k]='';render();return;
    }
    case'send':{
      const n=Math.round(Number(S.money.send)),m=S.money,partner=S.view.couple.partner.name;
      if(!(n>0)){S.flash={text:'Nhập số xu muốn gửi nhé.',kind:'bad'};render();return;}
      if(!(await env.confirmAction(m.loan?`Cho ${partner} mượn ${xu(n)}?`:`Gửi ${partner} ${xu(n)}?`,m.loan?'Khoản này vào sổ nợ của hai bạn. Người ấy trả dần lúc nào cũng được.':'Tiền chuyển từ ví của bạn sang ví của người ấy.',m.loan?'Cho mượn':'Gửi',{cost:n,pocket:'wallet'})))return;
      const d=await post('send',{amount:n,note:m.note,loan:m.loan,rid:rid()});if(d)S.money.send='';render();return;
    }
    case'help_ask':{
      const n=Math.round(Number(S.money.help));if(!(n>0)){S.flash={text:'Nhập số xu cần nhờ nhé.',kind:'bad'};render();return;}
      const d=await post('help_ask',{amount:n,note:S.money.hnote,loan:S.money.hloan});if(d)S.money.help='';render();return;
    }
    case'help_answer':{
      const r=(S.view.home?.requests||[]).find(x=>x.id===Number(data.id));if(!r)return;
      if(data.answer==='accept'&&!(await env.confirmAction(`Giúp ${S.view.couple.partner.name} ${xu(r.amount)}?`,r.loan?'Khoản này vào sổ nợ, người ấy sẽ trả lại.':'Tiền chuyển từ ví của bạn sang ví của người ấy.','Giúp')))return;
      post('help_answer',{id:r.id,answer:data.answer,rid:rid()});return;
    }
    case'help_cancel':post('help_cancel',{id:Number(data.id)});return;
    case'claim':post('claim',{debt:Number(data.id),line:S.cline[data.id]||Object.keys(S.view.home.claim_lines)[0]});return;
    case'later':post('later',{debt:Number(data.id),line:S.lline[data.id]||Object.keys(S.view.home.later_lines)[0]});return;
    case'repay':{
      const d=(S.view.home?.debts||[]).find(x=>x.id===Number(data.id));if(!d)return;
      const n=data.all?d.left:Math.round(Number(S.repay[d.id]));
      if(!(n>0&&n<=d.left)){S.flash={text:`Trả từ 1 đến ${xu(d.left)} nhé.`,kind:'bad'};render();return;}
      const out=await post('repay',{debt:d.id,amount:n,rid:rid()});if(out)S.repay[d.id]='';render();return;
    }
    case'forgive':if(await env.confirmAction('Xóa khoản nợ này?','Người ấy không cần trả nữa. Sổ nợ vẫn ghi lại.','Xóa nợ'))post('forgive',{debt:Number(data.id)});return;
    case'moment':{
      const k=data.kind;
      if(k==='qua'&&!S.money.gift){S.flash={text:'Chọn một món trong túi quà nhé.',kind:'bad'};render();return;}
      const d=await post('interact',k==='qua'?{kind:k,item:S.money.gift}:{kind:k});if(d&&k==='qua')S.money.gift='';return;
    }
    case'propose':{
      const f=S.form;if(!S.found?.can)return;
      const d=await post('propose',{code:S.found.code,ring:f.ring,message:f.message,announce:f.announce});
      if(d){S.found=null;S.form.code='';}return;
    }
    case'accept':case'decline':{
      const id=Number(data.id);
      if(mr==='accept'&&!(await env.confirmAction('Nhận lời cầu hôn?','Hai bạn sẽ đính hôn. Mỗi người chỉ có một người thương cùng lúc, các lời cầu hôn khác tự đóng lại.','Đồng ý')))return;
      post('respond',{id,answer:mr,announce:S.answer[id]!==false});return;
    }
    case'block':if(await env.confirmAction('Chặn người này?','Người này sẽ không gửi lời cầu hôn cho bạn được nữa. Bạn bỏ chặn lúc nào cũng được.','Chặn'))post('block',data.id?{id:Number(data.id)}:{code:data.code});return;
    case'unblock':post('unblock',{code:data.code});return;
    case'cancel':post('cancel',{id:Number(data.id)});return;
    case'tables':S.plan.tables=clampTables(S.plan.tables+Number(data.delta));render();askQuote();return;
    case'split':S.plan.mine=Number(data.pct);render();askQuote();return;
    case'an_hoi':S.plan.ceremonies.an_hoi=Number(data.n);render();askQuote();return;
    case'plan_send':{if(soon(S.plan)){paintBreakdown();return;}   // the hour passed while the planner stayed open: show why, send nothing
      const d=await post('plan',{plan:planBody(),mine:S.plan.mine,announce:S.plan.announce});if(d){S.tab='home';S.dlg.scrollTop=0;}return;}
    case'withdraw':post('withdraw');return;
    case'reject':post('reject',{id:Number(data.id)});return;
    case'confirm':{
      const w=S.view.wedding,share=w.share_mine.deposit;
      if(!(await env.confirmAction('Chốt kế hoạch và đặt cọc?',`Phần cọc của bạn là ${xu(share)}, của ${S.view.couple.partner.name} là ${xu(w.share_partner.deposit)}. Cọc không hoàn lại nếu hủy.`,`Đặt cọc · ${xu(share)}`,{cost:share,pocket:'wallet'})))return;
      post('confirm',{id:w.id,version:w.version,announce:S.answer.wedding!==false});return;
    }
    case'divorce':{const d=await post('divorce',{confirm:S.confirm});if(d){S.confirm='';S.tab='home';}return;}
  }
}

/* ---- rendering ---- */
const focusKey=a=>{
  const ds=a.dataset,by=k=>ds[k]!==undefined?`[data-${k}="${CSS.escape(ds[k])}"]`:'';
  if(ds.mrField)return `[data-mr-field="${ds.mrField}"]${by('id')}${a.type==='radio'?`[value="${CSS.escape(a.value)}"]`:''}`;
  if(ds.mr)return `[data-mr="${ds.mr}"]${by('id')}${by('tier')}${by('tab')}${by('k')}${by('v')}${by('kind')}${by('code')}${by('answer')}`;
  return null;
};
function keepFocus(fn){
  const a=document.activeElement,key=a&&S.dlg.contains(a)?focusKey(a):null;
  const top=S.dlg.scrollTop,opened=[...S.dlg.querySelectorAll('.mr-family details[open]')].map(d=>d.dataset.familyDetails);fn();S.dlg.scrollTop=top;
  S.dlg.querySelectorAll('.mr-family details').forEach(d=>{if(opened.includes(d.dataset.familyDetails))d.open=true;});
  if(key){const el=S.dlg.querySelector(key);if(el){el.focus({preventScroll:true});if(el.setSelectionRange&&el.type==='text'){const n=el.value.length;try{el.setSelectionRange(n,n);}catch{/* not a text field */}}}}
}
function render(){
  if(!S.dlg)return;
  keepFocus(()=>{S.dlg.querySelector('.mr-root').innerHTML=page();});
  S.dlg.setAttribute('aria-busy',String(S.busy||S.loading));
  if(S.familySection&&!S.loading&&S.tab==='family'){const section=S.familySection==='children'?'children':'home',target=S.dlg.querySelector('#mr-family-invite-'+section)||S.dlg.querySelector('#mr-family-'+section);target?.scrollIntoView({block:'start'});S.familySection=null;}
}
function head(sub){
  return `<header class="sheet-head"><div class="grow"><span class="eyebrow">PHỐ CÓ CHUYỆN</span><h2 id="mr-title">${S.tab==='friends'?'👥 Bạn bè':S.tab==='family'?'🏡 Nhà &amp; Gia đình':'💍 Hôn nhân'}</h2><p>${sub}</p></div>
    <button class="icon-btn" type="button" data-mr="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
}
const flash=()=>`<p class="mr-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
function page(){
  const v=S.view;
  if(!v||!S.catalog){
    return head('Nhẫn cưới, lời cầu hôn và một đám cưới cho cả phố.')+`<div class="sheet-body mr">${S.err?`<p class="mr-flash bad" role="alert">${esc(S.err)}</p>${btn('Thử lại','retry',{},'primary')}`:'<p class="mr-loading" role="status">Đang mở sổ hôn nhân…</p>'}</div>`;
  }
  if(v.guest)return head('Nhẫn cưới, lời cầu hôn và một đám cưới cho cả phố.')+`<div class="sheet-body mr">${guest()}</div>`;
  const c=v.couple,engaged=c?.status==='engaged',married=c?.status==='married';
  const fn=v.friends?.incoming?.length||0,hn=(v.home?.moments||[]).filter(m=>m.new).length,rq=(v.home?.requests||[]).filter(r=>!r.mine).length+(v.home?.debts||[]).filter(d=>!d.lender&&d.claim?.status==='pending').length;
  const dot=n=>n?` <em class="mr-dot">${n}</em>`:'';
  const tabs=married?[['family',`🏡 Nhà & Gia đình${dot((v.family?.requests||[]).filter(r=>!r.mine).length)}`],['home','💍 Hai bạn'],['fund',`🏦 Quỹ chung${dot(rq)}`],['love',`💞 Tương tác${dot(hn)}`],['friends',`👥 Bạn bè${dot(fn)}`],['shop','💍 Kim hoàn']]
    :engaged?[['family','🏡 Nhà & Gia đình'],['home','💞 Hai bạn'],['plan','📋 Kế hoạch cưới'],['friends',`👥 Bạn bè${dot(fn)}`],['shop','💍 Kim hoàn']]
    :[['family','🏡 Nhà & Gia đình'],['friends',`👥 Bạn bè${dot(fn)}`],['home',`💌 Cầu hôn${dot(v.incoming.length)}`],['shop','💍 Tiệm nhẫn']];
  if(!tabs.some(([id])=>id===S.tab))S.tab='home';
  const tabBar=`<div class="segmented mr-tabs" role="tablist" aria-label="Mục hôn nhân">${tabs.map(([id,label])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" class="${S.tab===id?'active':''}" data-mr="tab" data-tab="${id}">${label}</button>`).join('')}</div>`;
  const body=S.tab==='family'?familyView(v.family,c,S.family):S.tab==='shop'?shop():S.tab==='friends'?friendsTab():S.tab==='fund'?fundTab():S.tab==='love'?loveTab():S.tab==='plan'&&engaged?planner():c?couple():single();
  const sub=c?(engaged?`Đã đính hôn với ${esc(c.partner.name)}`:`Đã kết hôn với ${esc(c.partner.name)}`):'Kết bạn trước, rồi mới trao nhẫn.';
  return head(sub)+`<div class="sheet-body mr">${tabBar}${flash()}${body}</div>`;
}

function guest(){
  const rings=S.catalog.rings.map(r=>`<li><span class="mr-ring-ic ${esc(r.tone)}" aria-hidden="true">${r.emoji}</span>${esc(r.name)} <b>${xu(r.price)}</b></li>`).join('');
  return `<section class="mr-card mr-guest"><div class="mr-big" aria-hidden="true">💍</div><h3>Tạo tài khoản để kết hôn</h3>
    <p>Kết hôn là chuyện giữa hai người chơi thật trên phố, nên cần một tài khoản để giữ nhẫn, lời hứa và ngày cưới của hai bạn.</p>
    ${btn('Tạo tài khoản','register',{},'primary big')}</section>
    <section class="mr-card"><h3>Có gì ở đây?</h3><ul class="mr-bullets"><li>Mua nhẫn ở tiệm vàng đầu hẻm, cầu hôn bằng mã người chơi.</li><li>Cùng nhau lên kế hoạch cưới: rạp, số bàn, thực đơn, lễ ăn hỏi, xe hoa…</li><li>Ngày cưới, hàng xóm thân quen tới dự và mừng phong bì.</li><li>Cả phố thấy tin vui chạy trên bảng tin (nếu hai bạn đồng ý).</li></ul>
    <h4>Tiệm nhẫn</h4><ul class="mr-mini-rings">${rings}</ul></section>`;
}

function notice(){
  const me=S.view.me;
  return me.notice?`<div class="mr-notice" role="status"><span aria-hidden="true">🔔</span><p>${esc(me.notice)}</p>${btn('Đã xem','seen',{},'ghost small')}</div>`:'';
}

/* ---- ring pictures: an SVG that takes the ring's metal and stone colours ---- */
let ringN=0;
function ringSVG(c,size=64,label=''){
  const id=`mrg${++ringN}`,m=esc(c?.metal||'#e6b843'),md=esc(c?.metal_dark||'#a4761a'),st=c?.stone?esc(c.stone):'',sd=esc(c?.stone_dark||'#555');
  const a11y=label?`role="img" aria-label="${esc(label)}"`:'aria-hidden="true"';
  return `<svg class="mr-ring-svg" width="${size}" height="${size}" viewBox="0 0 64 64" ${a11y} focusable="false"><defs>
    <linearGradient id="${id}m" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".22" stop-color="${m}"/><stop offset=".62" stop-color="${md}"/><stop offset=".85" stop-color="${m}"/><stop offset="1" stop-color="#fff" stop-opacity=".8"/></linearGradient>
    ${st?`<radialGradient id="${id}s" cx=".38" cy=".3" r=".85"><stop offset="0" stop-color="#fff"/><stop offset=".3" stop-color="${st}"/><stop offset="1" stop-color="${sd}"/></radialGradient>`:''}</defs>
    <ellipse cx="32" cy="41" rx="19" ry="16.5" fill="none" stroke="${md}" stroke-width="7.5" opacity=".35"/>
    <ellipse cx="32" cy="40" rx="19" ry="16.5" fill="none" stroke="url(#${id}m)" stroke-width="6"/>
    <path d="M17 33 Q32 21 47 33" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="1.4" stroke-linecap="round"/>
    ${st?`<path d="M25.5 25 L28 19.5 H36 L38.5 25 Z" fill="url(#${id}m)" stroke="${md}" stroke-width=".6"/>
    <path d="M23 13.5 L27.5 7.5 H36.5 L41 13.5 L32 25 Z" fill="url(#${id}s)" stroke="${sd}" stroke-width=".8" stroke-linejoin="round"/>
    <path d="M23 13.5 H41 M27.5 7.5 L30 13.5 L32 25 L34 13.5 L36.5 7.5" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width=".7"/>`:''}
  </svg>`;
}
const metalOf=id=>S.catalog.metals.find(x=>x.id===id)||S.catalog.metals[0];
const stoneOf=id=>S.catalog.stones.find(x=>x.id===id)||null;
const colorsOf=(metal,stone)=>{const m=metalOf(metal),st=stone?stoneOf(stone):null;return {metal:m.hex,metal_dark:m.dark,stone:st?.hex||null,stone_dark:st?.dark||null};};
const colorName=(metal,stone)=>`${metalOf(metal).name}${stone?` · ${stoneOf(stone)?.name||''}`:''}`;
function colorExtra(tier,metal,stone){  // mirror of marriage.color_extra
  const r=S.catalog.rings.find(x=>x.id===tier);if(!r)return 0;
  let e=Math.max(0,metalOf(metal).extra-metalOf(r.metal).extra);
  if(r.stone&&stone)e+=Math.max(0,stoneOf(stone).extra-stoneOf(r.stone).extra);
  return e;
}
const recolorFee=(r,metal,stone)=>S.catalog.recolor_fee+Math.max(0,colorExtra(r.tier,metal,stone)-colorExtra(r.tier,r.metal,r.stone));
function pickOf(tier){const r=S.catalog.rings.find(x=>x.id===tier);return S.pick[tier]||(S.pick[tier]={metal:r.metal,stone:r.stone});}
function ringById(id){const v=S.view;return (v.rings||[]).find(r=>r.id===id)||(v.couple?.ring?.id===id?v.couple.ring:null);}
function swatches(op,data,tier,cur){
  const r=S.catalog.rings.find(x=>x.id===tier);
  const group=(k,list,label)=>`<div class="mr-sw-group"><span class="mr-sw-label">${label}: <b>${esc((k==='metal'?metalOf(cur.metal):stoneOf(cur.stone))?.name||'')}</b></span>
    <div class="mr-swatches" role="radiogroup" aria-label="${label}">${list.map(x=>`<button type="button" role="radio" aria-checked="${cur[k]===x.id}" aria-label="${esc(x.name)}" title="${esc(x.name)}" class="mr-sw${cur[k]===x.id?' on':''}" data-mr="${op}"${attrs(data)} data-k="${k}" data-v="${x.id}" style="--sw:${esc(x.hex)};--sw2:${esc(x.dark)}"${S.busy?' disabled':''}></button>`).join('')}</div></div>`;
  return group('metal',S.catalog.metals,'Màu kim loại')+(r?.stone?group('stone',S.catalog.stones,'Màu đá'):'');
}

function single(){
  const v=S.view,me=v.me;
  const incoming=v.incoming.map(p=>`<article class="mr-card mr-proposal">
      <div class="mr-proposal-ring">${ringSVG(p.ring?.colors,112,p.ring?`${p.ring.name}, ${colorName(p.ring.metal,p.ring.stone)}`:'Nhẫn')}<div><b>${esc(p.name)} cầu hôn bạn</b><small>${esc(p.ring?.name||'')}</small>${p.ring?`<small class="mr-ring-look">${esc(colorName(p.ring.metal,p.ring.stone))}</small>`:''}</div></div>
      <blockquote>“${esc(p.message)}”</blockquote>
      <label class="mr-check"><input type="checkbox" data-mr-field="answer" data-id="${p.id}"${S.answer[p.id]===false?'':' checked'}><span>Báo tin vui cho cả phố (bảng tin chạy chữ)</span></label>
      <div class="mr-actions">${btn('💞 Đồng ý','accept',{id:p.id},'primary')}${btn('Từ chối','decline',{id:p.id},'cream')}${btn('Chặn người này','block',{id:p.id},'ghost')}</div></article>`).join('');
  const owned=v.rings.filter(r=>r.status==='owned');
  const cooldown=me.cooldown?`<p class="mr-flash warn">Bạn vừa khép lại một chuyện cũ. Có thể cầu hôn lại sau ${hoursLeft(me.cooldown)}.</p>`:'';
  const friends=(v.friends?.list||[]).filter(f=>f.status==='single');
  let form;
  if(!owned.length)form=`<p>Muốn cầu hôn thì cần một chiếc nhẫn trước đã.</p>${btn('💍 Đến tiệm nhẫn','tab',{tab:'shop'},'primary')}`;
  else if(!friends.length)form=`<p>Chỉ cầu hôn được bạn bè. Kết bạn với người ấy trước nhé.</p>${btn('👥 Mở danh sách bạn bè','tab',{tab:'friends'},'primary')}`;
  else{
    const f=S.form,found=S.found&&S.found.code===f.code?S.found:null;
    const foundLine=found?`<p class="mr-found ${found.can?'ok':'no'}" role="status">${found.can?`✓ Gửi tới <b>${esc(found.name)}</b>.`:esc(found.why||'Không gửi được lời cầu hôn tới người này.')}</p>`:'';
    const ring=owned.find(r=>r.id===f.ring)||owned[0];
    form=`<label class="field" for="mr-to">Gửi tới người bạn
        <select class="input" id="mr-to" data-mr-field="to"><option value="">Chọn một người bạn…</option>${friends.map(x=>`<option value="${esc(x.code)}"${x.code===f.code?' selected':''}>${esc(x.name)}</option>`).join('')}</select></label>${foundLine}
      <fieldset class="mr-choices"><legend>Chiếc nhẫn</legend><div class="mr-ring-pick">${ringSVG(ring.colors,72,`${ring.name}, ${colorName(ring.metal,ring.stone)}`)}<div class="mr-ring-pick-list">${owned.map(r=>`<label class="mr-choice"><input type="radio" name="mr-ring" data-mr-field="ring" value="${esc(r.id)}"${r.id===ring.id?' checked':''}><span class="mr-choice-ring"><span>${esc(r.name)}<small>${esc(colorName(r.metal,r.stone))}</small></span></span></label>`).join('')}</div></div></fieldset>
      <fieldset class="mr-choices"><legend>Lời cầu hôn</legend>${S.catalog.messages.map(m=>`<label class="mr-choice msg"><input type="radio" name="mr-msg" data-mr-field="message" value="${esc(m.id)}"${m.id===f.message?' checked':''}><span>“${esc(m.text)}”</span></label>`).join('')}</fieldset>
      <label class="mr-check"><input type="checkbox" data-mr-field="pannounce"${f.announce?' checked':''}><span>Nếu người ấy đồng ý, báo tin vui cho cả phố</span></label>
      ${btn('💍 Gửi lời cầu hôn','propose',{},'primary big full',found?.can&&me.proposals_left>0?'':' disabled')}
      <p class="mr-hint">Còn ${me.proposals_left} lượt cầu hôn hôm nay. Bị từ chối thì chiếc nhẫn vẫn là của bạn.</p>`;
  }
  const outgoing=v.outgoing.length?`<section class="mr-card"><h3>Lời cầu hôn đã gửi</h3><ul class="mr-list">${v.outgoing.map(p=>`<li><span class="mr-li-ring">${ringSVG(p.ring?.colors,30)}<span>Tới <b>${esc(p.name)}</b> · ${p.status==='pending'?'đang chờ trả lời':p.status==='declined'?'chưa nhận lời':'đã nhận lời'}</span></span>${p.status==='pending'?btn('Rút lại','cancel',{id:p.id},'ghost small'):''}</li>`).join('')}</ul></section>`:'';
  const blocks=v.blocks.length?`<section class="mr-card"><h3>Đã chặn</h3><ul class="mr-list">${v.blocks.map(b=>`<li><span>${esc(b.name)}</span>${btn('Bỏ chặn','unblock',{code:b.code},'ghost small')}</li>`).join('')}</ul></section>`:'';
  const last=v.last?.status==='divorced'?`<p class="mr-hint">Chuyện cũ đã khép lại. Mỗi người đều có quyền bắt đầu lại.</p>`:'';
  return `${notice()}${incoming?`<h3 class="mr-h">Lời cầu hôn gửi tới bạn</h3>${incoming}`:''}
    <section class="mr-card"><h3>Cầu hôn</h3>${cooldown}${form}</section>${outgoing}
    <section class="mr-card"><label class="switch-row"><span class="grow"><b>Nhận lời cầu hôn</b><small class="muted"> Tắt đi thì không ai gửi được lời mới cho bạn.</small></span><input type="checkbox" data-mr-field="accept"${me.accept?' checked':''} aria-label="Nhận lời cầu hôn"><i aria-hidden="true"></i></label></section>
    ${blocks}${last}${debtsCard()}`;
}
async function lookup(code){
  if(!code){S.found=null;render();return;}
  const d=await post('lookup',{code},{quiet:true});S.found=d?.found||null;render();
}

/* ---- 👥 Bạn bè ---- */
const STATUS={single:'Độc thân',engaged:'Đã đính hôn',married:'Đã kết hôn'};
function friendsTab(){
  const v=S.view,F=v.friends||{list:[],incoming:[],outgoing:[]},me=v.me,single=!v.couple;
  const r=S.fres;
  const result=r?(r.name?`<div class="mr-person"><span class="mr-av" aria-hidden="true">${esc(([...r.name][0]||'').toUpperCase())}</span><div class="grow"><b>${esc(r.name)}</b><small>${esc(STATUS[r.status]||'')}${r.career?` · ${esc(r.career.career)} · cấp ${r.career.level}`:''}</small></div>
      ${r.state==='friend'?'<span class="tag">Đã là bạn bè</span>':r.state==='sent'?'<span class="tag">Đã gửi lời mời</span>':btn(r.state==='received'?'Chấp nhận kết bạn':'➕ Kết bạn','freq',{code:r.code},'primary small')}</div>`
      :`<p class="mr-found no" role="status">${esc(r.why||'Không tìm thấy người chơi này.')}</p>`):'';
  const search=`<section class="mr-card"><h3>Tìm bạn</h3>
    <label class="field" for="mr-fq">Tên đăng nhập của bạn ấy
      <span class="mr-code-row"><input class="input" id="mr-fq" data-mr-field="fq" value="${esc(S.fq)}" placeholder="vd: be_na_2024" maxlength="40" autocomplete="off" autocapitalize="none" spellcheck="false">${btn(`${icon('search',18)} Tìm`,'fsearch',{},'cream')}</span></label>
    <p class="mr-hint">Gõ đúng từng ký tự: không tìm gần đúng, không có danh sách để lướt. Có mã người chơi (PCC-…) thì nhập mã cũng được. Còn ${F.searches_left??''} lượt tìm hôm nay.</p>${result}</section>`;
  const incoming=F.incoming.length?`<section class="mr-card mr-accent"><h3>Lời mời kết bạn</h3><ul class="mr-list">${F.incoming.map(x=>`<li class="mr-li-wrap"><span><b>${esc(x.name)}</b> muốn kết bạn</span><span class="mr-actions tight">${btn('Chấp nhận','frespond',{id:x.id,answer:'accept'},'primary small')}${btn('Từ chối','frespond',{id:x.id,answer:'decline'},'cream small')}${btn('Chặn','frespond',{id:x.id,answer:'block'},'ghost small')}</span></li>`).join('')}</ul></section>`:'';
  const list=F.list.length?F.list.map(x=>`<article class="mr-card mr-friend"><div class="mr-person"><span class="mr-av" aria-hidden="true">${esc(([...x.name][0]||'').toUpperCase())}</span><div class="grow"><b>${esc(x.name)}${x.spouse?' <span class="tag">Người thương</span>':x.dating?' <span class="tag">Đang tìm hiểu 💕</span>':''}</b>
      <small>${x.career?`${esc(x.career.career)} · cấp ${x.career.level}`:'Mới vào phố'} · ${esc(STATUS[x.status]||'')}${x.close?` · 🤝 ${x.close}`:''}</small>${x.wed?`<small>${esc(x.wed)}</small>`:''}</div></div>
      <div class="mr-actions tight">${btn('🏪 Ghé chỗ làm','workvisit',{code:x.code},'primary small')}${btn('🏡 Mời về nhà','homeGuests',{code:x.code},'small')}${single&&x.status==='single'?btn('💍 Cầu hôn','fpropose',{code:x.code},'primary small'):''}${x.spouse?'':btn('Hủy kết bạn','fremove',{code:x.code,name:x.name},'ghost small')+btn('Chặn','fblock',{code:x.code,name:x.name},'ghost small')}</div></article>`).join('')
    :`<section class="mr-card"><p>Chưa có bạn bè nào. Xin tên đăng nhập của người quen ngoài đời rồi tìm ở trên nhé.</p></section>`;
  const outgoing=F.outgoing.length?`<section class="mr-card"><h3>Đang chờ trả lời</h3><ul class="mr-list">${F.outgoing.map(x=>`<li><span>${esc(x.name)}</span>${btn('Rút lại','fcancel',{id:x.id},'ghost small')}</li>`).join('')}</ul></section>`:'';
  return `${notice()}${btn('🏘️ Mọi người đang làm gì?','workdiscover',{},'cream full')}${incoming}${search}<h3 class="mr-h">Bạn bè (${F.list.length})</h3>${list}${outgoing}
    <section class="mr-card"><label class="switch-row"><span class="grow"><b>Cho phép tìm tôi bằng tên đăng nhập</b><small class="muted"> Tắt đi thì chỉ ai có mã người chơi mới tìm được bạn.</small></span><input type="checkbox" data-mr-field="findable"${F.findable!==false?' checked':''} aria-label="Cho phép tìm tôi bằng tên đăng nhập"><i aria-hidden="true"></i></label>
      <p class="mr-hint">Mã người chơi của bạn: <b class="mr-code sm">${esc(me.code)}</b> ${btn('Chép mã','copy',{},'ghost small')}</p>
      <p class="mr-hint">Người khác chỉ thấy tên hiển thị <b>${esc(me.name)}</b>, không bao giờ thấy tên đăng nhập của bạn. Còn ${F.requests_left??''} lời mời kết bạn hôm nay.</p></section>`;
}
const hoursLeft=t=>{const h=Math.max(1,Math.ceil((t*1000-Date.now()-(S.env.api.clockOffset||0)*1000)/3600000));return h>=24?`${Math.ceil(h/24)} ngày`:`${h} giờ`;};

function summary(q,w){
  return `<div class="mr-summary"><p><b>${esc(venueOf(q.plan.venue).emoji)} ${esc(venueOf(q.plan.venue).name)}</b> · ${q.plan.tables} bàn · thực đơn ${esc(S.catalog.menus.find(m=>m.id===q.plan.menu).name.toLowerCase())} · ${q.plan.at?`💍 ${atLabel(q.plan.at)}`:`cưới sau ${q.plan.days} ngày sống`}</p>
    <dl class="mr-dl"><div><dt>Tổng chi phí</dt><dd>${xu(q.total)}</dd></div><div><dt>Đặt cọc (${S.catalog.deposit_pct}%)</dt><dd>${xu(q.deposit)}</dd></div><div><dt>Trả nốt ngày cưới</dt><dd>${xu(q.balance)}</dd></div>
    ${w?`<div><dt>Bạn góp ${w.split_mine}%</dt><dd>cọc ${xu(w.share_mine.deposit)} · nốt ${xu(w.share_mine.balance)}</dd></div>`:''}
    <div><dt>Khách dự kiến</dt><dd>${q.forecast.guests[0]}–${q.forecast.guests[1]} / ${q.seats}</dd></div><div><dt>Tiền mừng dự kiến</dt><dd>${xu(q.forecast.gifts[0])}–${xu(q.forecast.gifts[1])}</dd></div></dl></div>`;
}
function couple(){
  const v=S.view,c=v.couple,w=v.wedding,married=c.status==='married';
  const ring=c.ring?`<div class="mr-home-ring">${ringSVG(c.ring.colors,84,`Nhẫn của hai bạn: ${c.ring.name}, ${colorName(c.ring.metal,c.ring.stone)}`)}<small>${esc(colorName(c.ring.metal,c.ring.stone))}</small></div>`:'';
  const h=v.home||{},hp=h.happy;
  const top=married
    ?`<section class="mr-card mr-home"><div class="mr-sticker mr-me" aria-hidden="true">${myPortrait(S.env?.api?.state,64,'')}<i>${S.catalog.sticker.emoji}</i></div><div class="grow"><span class="tag">${esc(v.family?.together?S.catalog.sticker.name:'Đã kết hôn')}</span><h3>Bạn & ${esc(c.partner.name)}</h3><p>${c.wed_label?esc(c.wed_label):`Cưới ngày ${esc(w?.result?.date?viDate(w.result.date):'')}`}${w?.result?` · ${esc(w.result.venue)}`:''} · bên nhau ${c.days_together} ngày</p></div>${ring}</section>
      ${hp?`<section class="mr-card mr-glance"><button type="button" class="mr-stat" data-mr="tab" data-tab="love"><small>Điểm hạnh phúc</small><b>💗 ${hp.points}/${hp.max}</b><small>${hp.streak?`${hp.streak} ngày liền`:'Gửi một lời chào hôm nay nhé'}</small></button>
        <button type="button" class="mr-stat" data-mr="tab" data-tab="fund"><small>Quỹ chung</small><b>🏦 ${xu(h.fund?.balance||0)}</b><small>${(h.requests||[]).filter(r=>!r.mine).length?'Có lời nhờ đang chờ':'Gửi, rút, giúp nhau'}</small></button></section>`:''}`
    :`<section class="mr-card mr-home"><div class="mr-sticker" aria-hidden="true">💞</div><div class="grow"><h3>Bạn & ${esc(c.partner.name)}</h3><p>Đã đính hôn ${c.days_together?`${c.days_together} ngày`:'hôm nay'}</p></div>${ring}</section>`;
  let plan='';
  if(!married){
    if(!w||w.status==='rejected'){
      const note=w?.status==='rejected'?(w.mine?`<p class="mr-flash warn">${esc(c.partner.name)} muốn bàn lại kế hoạch. Sửa rồi gửi lại nhé.</p>`:`<p class="mr-hint">Bạn đã báo muốn bàn lại. Tự sửa kế hoạch rồi gửi cho ${esc(c.partner.name)} cũng được.</p>`):'';
      plan=`<section class="mr-card"><h3>Kế hoạch cưới</h3>${note}<p>Chọn nơi tổ chức, số bàn, thực đơn, nghi lễ và ai góp bao nhiêu. Tiền chỉ bị trừ khi cả hai cùng xác nhận.</p>${btn('📋 Lên kế hoạch cưới','tab',{tab:'plan'},'primary big')}</section>`;
    }else if(w.status==='proposed'&&w.mine){
      plan=`<section class="mr-card"><h3>Đang chờ ${esc(c.partner.name)} xác nhận</h3>${summary(w.quote,w)}<div class="mr-actions">${btn('Sửa kế hoạch','tab',{tab:'plan'},'cream')}${btn('Rút lại','withdraw',{},'ghost')}</div></section>`;
    }else if(w.status==='proposed'){
      const short=wallet()<w.share_mine.deposit;
      plan=`<section class="mr-card mr-accent"><h3>📋 ${esc(c.partner.name)} gửi kế hoạch cưới</h3>${summary(w.quote,w)}
        ${short?`<p class="mr-flash bad">Ví của bạn còn ${xu(wallet())}, chưa đủ ${xu(w.share_mine.deposit)} tiền cọc. Rút tiền lời từ nơi làm việc về ví trước nhé.</p>`:''}
        <label class="mr-check"><input type="checkbox" data-mr-field="wannounce"${S.answer.wedding===false?'':' checked'}><span>Báo tin cưới cho cả phố (bảng tin chạy chữ)</span></label>
        <div class="mr-actions">${btn(`Xác nhận & đặt cọc ${xu(w.share_mine.deposit)}`,'confirm',{},'primary',short?' disabled':'')}${btn('Muốn bàn lại','reject',{id:w.id},'cream')}</div></section>`;
    }else if(w.status==='confirmed'&&w.at){   // 💍 booked at a real date and time: the party is live (game/wedding_live.py)
      plan=`<section class="mr-card mr-countdown"><div class="mr-count" aria-hidden="true"><b>💍</b></div><div><h3>Cưới lúc ${esc(w.at_label)}</h3>
        <p>Tiệc mở trước 5 phút ở Khu phố › Lịch cưới. Bạn bè được nhắc trước 30 phút.</p></div></section>
        <section class="mr-card"><h3>Kế hoạch đã chốt</h3>${summary(w.quote,w)}<p class="mr-hint">Đã đặt cọc: bạn ${xu(w.deposit_mine)}, ${esc(c.partner.name)} ${xu(w.deposit_partner)}.</p></section>`;
    }else if(w.status==='confirmed'){
      plan=`<section class="mr-card mr-countdown"><div class="mr-count" aria-hidden="true"><b>${w.left}</b><small>ngày</small></div><div><h3>${w.left?`Còn ${w.left} ngày nữa là tới ngày cưới${Number.isInteger(v.me?.life_day)?` (Ngày ${v.me.life_day+w.left})`:''}`:'Ngày cưới đã tới!'}</h3>
        <p>Tới ngày khi một trong hai bạn sống thêm đủ ngày${w.hours_left?`, hoặc muộn nhất sau ${w.hours_left} giờ nữa`:''}. Cỗ cưới tự diễn ra kể cả khi người kia đang vắng.</p></div></section>
        <section class="mr-card"><h3>Kế hoạch đã chốt</h3>${summary(w.quote,w)}<p class="mr-hint">Đã đặt cọc: bạn ${xu(w.deposit_mine)}, ${esc(c.partner.name)} ${xu(w.deposit_partner)}. Ngày cưới trả nốt từ tiền mừng trước, thiếu thì mỗi người bù theo tỉ lệ đã chọn.</p></section>`;
    }
  }
  const result=w?.status==='done'&&w.result?resultCard(w):'';
  const word=married?'LY HON':'HUY';
  const danger=`<details class="mr-card mr-danger"><summary>${married?'Ly hôn':'Hủy hôn ước'}</summary>
    <p>${married?'Ly hôn thì hai bạn thôi là vợ chồng, nhãn “Đã về chung một nhà” được gỡ.':'Hủy hôn ước thì kế hoạch cưới dừng lại, tiền cọc không hoàn lại.'} Cả hai cần ${S.catalog.limits.remarry_hours??3} tiếng trước khi tính chuyện mới.</p>
    <label class="field" for="mr-confirm">Gõ <b>${word}</b> để xác nhận<input class="input" id="mr-confirm" data-mr-field="confirm" value="${esc(S.confirm)}" autocomplete="off" spellcheck="false"></label>
    ${btn(married?'Ly hôn':'Hủy hôn ước','divorce',{},'danger',S.confirm.trim()?'':' disabled')}</details>`;
  const split=married?`<p class="mr-hint">Nếu chia tay: quỹ chung chia đôi (lẻ 1 xu thuộc về người không đệ đơn); ai còn nợ thì trả từ phần của mình trước, phần nợ còn lại được xóa.</p>`:'';
  return `${notice()}${top}${married?`<section class="mr-card"><h3>🏡 Nhà &amp; Gia đình</h3><p>${(v.family?.requests||[]).some(r=>!r.mine)?'Có lời mời đang chờ bạn trả lời.':'Vào nhà, mời người ấy về ở và cùng chăm con.'}</p>${btn('Mở Nhà & Gia đình','tab',{tab:'family'},'primary')}</section>`:''}${partyCard(c)}${result}${plan}${danger.replace('</details>',split+'</details>')}`;
}
const viDate=d=>{const m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(d||'');return m?`${m[3]}/${m[2]}/${m[1]}`:'';};

function resultCard(w){
  const r=w.result,me=r.shares[w.side],pname=w.side==='a'?r.names.b:r.names.a,myname=w.side==='a'?r.names.a:r.names.b;
  if(!w.seen)setTimeout(()=>{if(S.view?.wedding?.id===w.id&&!S.view.wedding.seen){S.view.wedding.seen=true;post('seen',{wedding:w.id},{quiet:true});}},1200);
  const profit=r.profit;
  const close=r.close.length?`<h4>Người thân quen đã đến</h4><ul class="mr-close">${r.close.map(g=>`<li><span aria-hidden="true">${esc(g.emoji)}</span><b>${esc(g.name)}</b><small>${esc(g.tier_name)} · mừng ${xu(g.amount)}</small></li>`).join('')}</ul>`:'';
  const hl=r.highlights.length?`<h4>Khoảnh khắc</h4><ul class="mr-moments">${r.highlights.map(h=>`<li><span aria-hidden="true">${esc(h.emoji)}</span><div><b>${esc(h.name)}</b>${h.amount?` · ${xu(h.amount)}`:''}<p>${esc(h.line)}</p></div></li>`).join('')}</ul>`:'';
  const groups=r.groups.length?`<ul class="mr-groups">${r.groups.map(g=>`<li><span aria-hidden="true">${esc(g.emoji)}</span>${esc(g.name)} <b>${g.count}</b> <small>${xu(g.total)}</small></li>`).join('')}</ul>`:'';
  return `<article class="mr-photo" aria-label="Thiệp kỷ niệm đám cưới">
    <div class="mr-photo-frame"><span class="mr-photo-tag">${esc(r.mood.emoji)} ${esc(r.mood.label)}</span><div class="mr-photo-hearts" aria-hidden="true">🎊 💐 🎊</div>
      <h3>${esc(r.names.a)} <span aria-hidden="true">❤</span><span class="sr-only"> và </span> ${esc(r.names.b)}</h3>
      <p>${esc(viDate(r.date))} · ${esc(r.venue_emoji)} ${esc(r.venue)} · ${r.tables} bàn</p>
      ${r.close.length?`<p class="mr-photo-crowd" aria-hidden="true">${r.close.slice(0,8).map(g=>esc(g.emoji)).join(' ')}</p>`:''}</div>
    <dl class="mr-dl mr-result"><div><dt>Khách tới dự</dt><dd>${r.guests} / ${r.seats}${r.empty?` <small>(trống ${r.empty} ghế)</small>`:''}</dd></div>
      <div><dt>Tiền mừng</dt><dd>${xu(r.gifts)}${r.late_total?` <small>+ ${xu(r.late_total)} gửi sau</small>`:''}</dd></div>
      <div><dt>Tổng chi phí</dt><dd>${xu(r.total)}</dd></div>
      <div class="${profit>=0?'good':'bad'}"><dt>${profit>=0?'Lời':'Lỗ'}</dt><dd>${signed(profit)}</dd></div></dl>
    <p class="mr-share">Phần của bạn (${esc(myname)}, góp ${w.side==='a'?r.split_a:100-r.split_a}%): cọc ${xu(me.deposit)}, trả nốt ${xu(me.balance)}, nhận mừng ${xu(me.gift)}${me.late?` + ${xu(me.late)} gửi sau`:''} → <b class="${me.net>=0?'good':'bad'}">${signed(me.net)}</b>. ${esc(pname)} nhận phần còn lại.</p>
    ${close}${hl}${groups?`<h4>Khách mời</h4>${groups}`:''}
    <h4>Lời chúc</h4><ul class="mr-speeches">${r.speeches.map(s=>`<li>${esc(s)}</li>`).join('')}</ul><p class="mr-gossip">${esc(r.gossip)}</p></article>`;
}

function shop(){
  const v=S.view,w=wallet(),owned=v.rings||[],full=owned.length>=S.catalog.limits.rings_max;
  const cards=S.catalog.rings.map(r=>{
    const pk=pickOf(r.id),price=r.price+colorExtra(r.id,pk.metal,pk.stone),poor=w<price;
    return `<article class="mr-card mr-ring"><div class="mr-ring-prev">${ringSVG(colorsOf(pk.metal,pk.stone),88,`${r.name}, ${colorName(pk.metal,pk.stone)}`)}</div>
      <div class="mr-ring-main"><h3>${esc(r.name)}</h3><p>${esc(r.desc)}</p>${swatches('pick',{tier:r.id},r.id,pk)}</div>
      <div class="mr-ring-buy"><b>${xu(price)}</b>${price>r.price?`<small>gồm ${xu(price-r.price)} màu</small>`:''}${btn(poor?`Thiếu ${xu(price-Math.max(0,w))}`:'Mua','ring_buy',{tier:r.id},poor?'cream':'primary',poor||full?' disabled':'')}</div></article>`;
  }).join('');
  const mine=[...(v.couple?.ring?[{...v.couple.ring,wear:true}]:[]),...owned];
  const rc=S.recolor;
  const row=r=>{
    const can=r.wear||r.status==='owned',open=rc&&rc.ring===r.id;
    const editor=open?`<div class="mr-recolor"><div class="mr-recolor-prev">${ringSVG(colorsOf(rc.metal,rc.stone),96,`Màu mới: ${colorName(rc.metal,rc.stone)}`)}</div><div>${swatches('rpick',{},r.tier,rc)}
      <p class="mr-hint">Phí tiệm kim hoàn ${xu(S.catalog.recolor_fee)}${recolorFee(r,rc.metal,rc.stone)>S.catalog.recolor_fee?` + ${xu(recolorFee(r,rc.metal,rc.stone)-S.catalog.recolor_fee)} chênh lệch màu`:''}.</p>
      <div class="mr-actions">${btn(`Đổi màu · ${xu(recolorFee(r,rc.metal,rc.stone))}`,'recolor_do',{},'primary',rc.metal===r.metal&&rc.stone===r.stone||w<recolorFee(r,rc.metal,rc.stone)?' disabled':'')}${btn('Thôi','recolor_cancel',{},'ghost')}</div></div></div>`:'';
    return `<li class="mr-box-item"><div class="mr-box-row"><span class="mr-li-ring">${ringSVG(r.colors,40)}<span>${esc(r.name)}<small>${esc(colorName(r.metal,r.stone))}</small></span></span>
      ${r.wear?'<span class="tag">nhẫn của hai bạn</span>':r.status==='proposed'?'<span class="tag">đang trao đi</span>':''}${can&&!open?btn('🎨 Đổi màu','recolor',{ring:r.id},'cream small'):''}${!r.wear&&r.status==='owned'&&r.sell_price?btn(`Bán lại · ${xu(r.sell_price)}`,'ring_sell',{ring:r.id},'ghost small'):''}</div>${editor}</li>`;
  };
  const box=mine.length?`<section class="mr-card"><h3>Hộp nhẫn · tiệm kim hoàn</h3><p class="mr-hint">Đổi màu nhẫn hoặc bán nhẫn dư trong hộp để nhận lại 80% giá mua vào ví. Nhẫn đang cầu hôn và nhẫn của hai bạn không bán được.</p><ul class="mr-list mr-box">${mine.map(row).join('')}</ul></section>`:'';
  return `<p class="mr-wallet">Ví của bạn: <b>${xu(w)}</b></p>${box}<p class="mr-hint">Chọn màu kim loại và màu đá, xem trước rồi mới mua. Nhẫn trả bằng ví riêng; người ấy từ chối thì nhẫn vẫn nằm trong hộp của bạn.</p>${cards}`;
}

/* ---- 🏦 Quỹ chung, 💸 giúp nhau, 🧾 sổ nợ ---- */
const opts=(o,cur,none='Không kèm lời nhắn')=>Object.entries(o).map(([k,t])=>`<option value="${esc(k)}"${k===cur?' selected':''}>${esc(t||none)}</option>`).join('');
const ago=t=>{const s=Math.max(0,Date.now()/1000-(S.env.api.clockOffset||0)-t);return s<3600?`${Math.max(1,Math.round(s/60))} phút trước`:s<86400?`${Math.round(s/3600)} giờ trước`:`${Math.round(s/86400)} ngày trước`;};
function fundTab(){
  const v=S.view,h=v.home,f=h.fund,m=S.money,partner=esc(v.couple.partner.name),L=h.limits;
  const KIND={deposit:'Gửi vào',withdraw:'Rút ra',spend:'Thẻ chung',home:'Mua nhà',split:'Chia quỹ'};
  const hist=f.history.length?`<ul class="mr-ledger">${f.history.map(x=>`<li><span><span><b>${esc(x.who)}</b> · ${KIND[x.kind]||''}${x.label&&(x.kind==='spend'||x.kind==='home')?`: ${esc(x.label)}`:''}</span><small>${ago(x.at)}${x.held?' · đang xử lý':''}</small></span><b class="${x.kind==='deposit'?'good':''}">${x.kind==='deposit'?'+':'−'}${xu(x.amount)}</b></li>`).join('')}</ul>`:'<p class="mr-hint">Chưa có giao dịch nào.</p>';
  const money=(k,label,act,cls,max)=>`<div class="mr-money"><input class="input" type="number" inputmode="numeric" min="1" max="${max}" step="1" data-mr-field="m:${k}" value="${esc(m[k])}" placeholder="Số xu" aria-label="${esc(label)}">${btn(label,act.op,act.data,cls)}</div>`;
  const reqs=h.requests.map(r=>r.mine
    ?`<li class="mr-li-wrap"><span>Bạn ${r.loan?'hỏi mượn':'xin trợ giúp'} <b>${xu(r.amount)}</b>${r.note?`: “${esc(r.note)}”`:''}<small>Chờ ${partner} trả lời</small></span>${btn('Rút lại','help_cancel',{id:r.id},'ghost small')}</li>`
    :`<li class="mr-li-wrap mr-ask"><span><b>${partner}</b> ${r.loan?'hỏi mượn':'xin trợ giúp'} <b>${xu(r.amount)}</b>${r.note?`: “${esc(r.note)}”`:''}${r.loan?'<small>Có ghi sổ nợ</small>':''}</span><span class="mr-actions tight">${btn(`Giúp ${xu(r.amount)}`,'help_answer',{id:r.id,answer:'accept'},'primary small',wallet()<r.amount?' disabled':'')}${btn('Để lần sau','help_answer',{id:r.id,answer:'decline'},'cream small')}</span></li>`).join('');
  return `${notice()}<section class="mr-card mr-fund"><div class="mr-fund-top"><div><small>Quỹ chung của hai bạn</small><b class="mr-fund-bal">${xu(f.balance)}</b></div><div class="mr-fund-wallet"><small>Ví của bạn</small><b>${xu(wallet())}</b></div></div>
      <div class="mr-fund-grid"><div><p class="mr-label">Gửi vào quỹ chung</p>${money('dep','Gửi vào',{op:'fund',data:{k:'dep'}},'primary',L.deposit_max??L.send_max)}</div>
      <div><p class="mr-label">Rút về ví</p>${money('wd','Rút ra',{op:'fund',data:{k:'wd'}},'cream',f.balance)}<p class="mr-hint">Rút và chi theo số dư ${xu(f.balance)}, không có hạn mức mỗi ngày. ${partner} được báo mỗi lần rút.</p></div></div>
      <h4>Lịch sử quỹ</h4>${hist}</section>
    ${reqs?`<section class="mr-card mr-accent"><h3>Lời nhờ</h3><ul class="mr-list">${reqs}</ul></section>`:''}
    <section class="mr-card"><h3>💸 Gửi tiền cho ${partner}</h3>
      <label class="field" for="mr-note">Lời nhắn<select class="input" id="mr-note" data-mr-field="m:note">${opts(h.notes,m.note)}</select></label>
      <div class="segmented mr-seg" role="radiogroup" aria-label="Kiểu gửi"><button type="button" role="radio" aria-checked="${!m.loan}" class="${m.loan?'':'active'}" data-mr="mset" data-k="loan" data-v="0">🎁 Tặng luôn</button><button type="button" role="radio" aria-checked="${m.loan}" class="${m.loan?'active':''}" data-mr="mset" data-k="loan" data-v="1">🧾 Cho mượn</button></div>
      ${money('send',m.loan?'Cho mượn':'Gửi',{op:'send',data:{}},'primary',L.send_max)}
      <p class="mr-hint">${m.loan?'Cho mượn thì khoản này vào sổ nợ, người ấy trả dần lúc nào cũng được.':'Tiền đi thẳng từ ví của bạn sang ví của người ấy.'}</p></section>
    <section class="mr-card"><h3>🙏 Nhờ ${partner} giúp</h3>
      <label class="field" for="mr-hnote">Lý do<select class="input" id="mr-hnote" data-mr-field="m:hnote">${opts(h.help_notes,m.hnote,'Không nêu lý do')}</select></label>
      <label class="mr-check"><input type="checkbox" data-mr-field="m:hloan"${m.hloan?' checked':''}><span>Mượn thôi, sẽ trả lại (ghi sổ nợ)</span></label>
      ${money('help',`Xin ${m.hloan?'mượn':'trợ giúp'}`,{op:'help_ask',data:{}},'cream',L.help_max)}</section>
    ${debtsCard()}`;
}
function debtsCard(){
  const h=S.view.home;if(!h?.debts?.length)return '';
  const ST={open:'Còn nợ',paid:'Đã trả hết',forgiven:'Đã xóa nợ',settled:'Trừ khi chia quỹ',cleared:'Xóa khi chia tay'};
  const lines=h.claim_lines,later=h.later_lines;
  const row=d=>{
    const head=`<span><span><b>${d.lender?`${esc(d.who)} nợ bạn`:`Bạn nợ ${esc(d.who)}`}</b> ${xu(d.amount)}${d.repaid?` · đã trả ${xu(d.repaid)}`:''}</span>${d.note?`<small>“${esc(d.note)}”</small>`:''}<small>${ST[d.status]||''}${d.status==='open'?` · còn ${xu(d.left)}`:''} · ${ago(d.at)}</small>
      ${d.claim&&d.status==='open'?`<small class="mr-claim">${d.lender?'Bạn đã nhắc':'Được nhắc'}: “${esc(d.claim.text)}”${d.claim.status==='later'?' · đã xin khất':''}</small>`:''}</span>`;
    if(d.status!=='open')return `<li class="mr-debt done">${head}</li>`;
    const act=d.lender
      ?`<div class="mr-debt-act">${d.can_claim?`<select class="input" data-mr-field="cline" data-id="${d.id}" aria-label="Câu đòi nợ">${Object.entries(lines).map(([k,x])=>`<option value="${esc(k)}"${S.cline[d.id]===k?' selected':''}>${x.tone==='cheeky'?'😜':'🙂'} ${esc(x.text)}</option>`).join('')}</select>${btn('Đòi tiền','claim',{id:d.id},'cream small')}`:'<small class="mr-hint">Vừa nhắc rồi, để người ấy thở chút nha.</small>'}${btn('Xóa nợ','forgive',{id:d.id},'ghost small')}</div>`
      :`<div class="mr-debt-act"><input class="input" type="number" inputmode="numeric" min="1" max="${d.left}" data-mr-field="repay" data-id="${d.id}" value="${esc(S.repay[d.id]||'')}" placeholder="Số xu" aria-label="Trả bớt bao nhiêu">${btn('Trả bớt','repay',{id:d.id},'cream small')}${btn(`Trả hết ${xu(d.left)}`,'repay',{id:d.id,all:1},'primary small',wallet()<d.left?' disabled':'')}
        ${d.claim?.status==='pending'?`<select class="input" data-mr-field="lline" data-id="${d.id}" aria-label="Câu xin khất">${Object.entries(later).map(([k,t])=>`<option value="${esc(k)}"${S.lline[d.id]===k?' selected':''}>${esc(t)}</option>`).join('')}</select>${btn('Xin khất','later',{id:d.id},'ghost small')}`:''}</div>`;
    return `<li class="mr-debt">${head}${act}</li>`;
  };
  return `<section class="mr-card"><h3>🧾 Sổ nợ</h3><ul class="mr-list mr-debts">${h.debts.map(row).join('')}</ul></section>`;
}

/* ---- 💞 Tương tác ---- */
function loveTab(){
  const v=S.view,h=v.home,hp=h.happy,partner=esc(v.couple.partner.name),done=new Set(h.done_today),K=h.moments_kinds;
  const bag=Object.entries(h.bag||{}).filter(([k,n])=>n>0&&h.gifts[k]);
  const pct=Math.round(hp.points*100/hp.max);
  const kinds=Object.entries(K).filter(([k])=>k!=='qua').map(([k,x])=>`<button type="button" class="mr-moment-btn${done.has(k)?' done':''}" data-mr="moment" data-kind="${k}"${done.has(k)||S.busy?' disabled':''}><span aria-hidden="true">${x.emoji}</span><b>${esc(x.label)}</b><small>${done.has(k)?'Đã gửi hôm nay':k==='com'?`${xu(h.limits.lunch)} · +${x.points} điểm`:`+${x.points} điểm`}</small></button>`).join('');
  const gift=`<div class="mr-gift"><label class="field" for="mr-gift">🎁 Quà nhỏ từ túi quà<select class="input" id="mr-gift" data-mr-field="m:gift"${bag.length&&!done.has('qua')?'':' disabled'}><option value="">${bag.length?'Chọn một món…':'Túi quà đang trống'}</option>${bag.map(([k,n])=>`<option value="${esc(k)}"${S.money.gift===k?' selected':''}>${esc(h.gifts[k].emoji)} ${esc(h.gifts[k].name)} (${n})</option>`).join('')}</select></label>
    ${btn(done.has('qua')?'Đã tặng hôm nay':'Tặng','moment',{kind:'qua'},'cream',done.has('qua')||!S.money.gift?' disabled':'')}</div>`;
  const feed=h.moments.length?`<ul class="mr-feed">${h.moments.map(x=>`<li class="${x.mine?'mine':''}${x.new?' new':''}"><small>${x.mine?'Bạn':partner} · ${ago(x.at)}${x.new?' · <b>mới</b>':''}</small><p>${esc(x.text)}</p></li>`).join('')}</ul>`:`<p class="mr-hint">Chưa có gì. Gửi một lời chào buổi sáng cho ${partner} nhé.</p>`;
  return `${notice()}<section class="mr-card mr-happy"><div class="mr-happy-top"><div><small>Điểm hạnh phúc</small><b>💗 ${hp.points}<small>/${hp.max}</small></b></div><div><small>Chuỗi ngày</small><b>🔥 ${hp.streak}</b></div><div><small>Hôm nay</small><b>+${hp.today}</b></div></div>
      <div class="mr-bar" role="progressbar" aria-label="Điểm hạnh phúc" aria-valuemin="0" aria-valuemax="${hp.max}" aria-valuenow="${hp.points}"><i style="width:${pct}%"></i></div>
      <p class="mr-hint">Mỗi ngày có qua có lại thì điểm tăng dần (chuỗi ngày liền được thưởng thêm). Cứ ${h.limits.anniv_days} ngày sống về chung nhà là một lần kỷ niệm, điểm càng cao quà càng dày.</p></section>
    <section class="mr-card"><h3>Gửi tới ${partner}</h3><div class="mr-moments-grid">${kinds}</div>${gift}</section>
    <section class="mr-card"><h3>Nhật ký hai bạn</h3>${feed}</section>`;
}

function planner(){
  const w=S.view.wedding;
  if(w&&(w.status==='confirmed'||(w.status==='proposed'&&!w.mine)))return `<p class="mr-hint">Kế hoạch đang chờ bạn xác nhận ở mục “Hai bạn”.</p>${btn('Xem kế hoạch','tab',{tab:'home'},'primary')}`;
  // No plan being drafted (the wedding is already set, or the view changed under an open tab): nothing to edit here.
  if(!S.plan)return `<p class="mr-hint">Đám cưới của hai bạn xem ở mục “Hai bạn”.</p>${btn('Xem đám cưới','tab',{tab:'home'},'primary')}`;
  const c=S.catalog,p=S.plan,v=venueOf(p.venue),partner=esc(S.view.couple.partner.name);
  const venues=c.venues.map(x=>`<label class="mr-option"><input type="radio" name="mr-venue" data-mr-field="venue" value="${x.id}"${x.id===p.venue?' checked':''}><span><b>${x.emoji} ${esc(x.name)}</b><small>Phí ${xu(x.fee)} · tối đa ${x.max_tables} bàn</small><small>${esc(x.desc)}</small></span></label>`).join('');
  const menus=c.menus.map(m=>`<label class="mr-option"><input type="radio" name="mr-menu" data-mr-field="menu" value="${m.id}"${m.id===p.menu?' checked':''}><span><b>${esc(m.name)} · ${xu(v.table_price[m.id])}/bàn</b><small>${m.dishes.map(esc).join(' · ')}</small></span></label>`).join('');
  const anhoi=c.ceremonies.find(x=>x.id==='an_hoi');
  const cer=c.ceremonies.filter(x=>x.id!=='an_hoi').map(x=>`<label class="mr-check line"><input type="checkbox" data-mr-field="cer:${x.id}"${p.ceremonies[x.id]?' checked':''}><span><b>${esc(x.name)}</b> · ${xu(x.price)}<small>${esc(x.desc)}</small></span></label>`).join('');
  const anhoiRow=`<div class="mr-anhoi"><b>${esc(anhoi.name)}</b><small>${esc(anhoi.desc)}</small><div class="segmented" role="radiogroup" aria-label="Số mâm tráp ăn hỏi">${[{trays:0,price:0},...anhoi.options].map(o=>`<button type="button" role="radio" aria-checked="${p.ceremonies.an_hoi===o.trays}" class="${p.ceremonies.an_hoi===o.trays?'active':''}" data-mr="an_hoi" data-n="${o.trays}">${o.trays?`${o.trays} mâm · ${o.price} xu`:'Không'}</button>`).join('')}</div></div>`;
  const extras=c.extras.map(x=>`<label class="mr-check line"><input type="checkbox" data-mr-field="extra:${x.id}"${p.extras.includes(x.id)?' checked':''}><span><b>${x.emoji} ${esc(x.name)}</b> · ${x.per10?`${xu(x.per10*p.tables)} (${x.per10} xu/10 khách)`:xu(x.price)}<small>${esc(x.desc)}</small></span></label>`).join('');
  const when=vnParts(p.at||defaultAt()),first=vnParts(Date.now()/1000+3600).date,last=vnParts(Date.now()/1000+14*86400).date;
  const splits=[[50,'Chia đôi'],[60,'Bạn 60%'],[70,'Bạn 70%'],[40,'Bạn 40%'],[100,'Bạn bao hết']];
  return `<div class="mr-plan"><div class="mr-plan-form">
    <section class="mr-card"><h3>1 · Nơi tổ chức</h3><div class="mr-options">${venues}</div></section>
    <section class="mr-card"><h3>2 · Số bàn</h3><div class="mr-tables"><button type="button" class="btn cream mr-step" data-mr="tables" data-delta="-1" aria-label="Bớt một bàn">−</button>
      <input type="range" min="${c.tables[0]}" max="${v.max_tables}" value="${p.tables}" data-mr-field="tables" aria-label="Số bàn">
      <button type="button" class="btn cream mr-step" data-mr="tables" data-delta="1" aria-label="Thêm một bàn">+</button></div>
      <p class="mr-tables-n" aria-live="polite"><b>${p.tables} bàn</b> · ${p.tables*c.seats} ghế</p><p class="mr-hint">Mỗi bàn ${c.seats} người. Ghế trống vẫn phải trả tiền cỗ.</p></section>
    <section class="mr-card"><h3>3 · Thực đơn</h3><div class="mr-options">${menus}</div></section>
    <section class="mr-card"><h3>4 · Nghi lễ</h3>${cer}${anhoiRow}</section>
    <section class="mr-card"><h3>5 · Dịch vụ thêm</h3>${extras}</section>
    <section class="mr-card"><h3>6 · Ngày cưới & góp tiền</h3>
      <div class="mr-when"><label class="field" for="mr-date">Ngày cưới<input class="input" id="mr-date" type="date" data-mr-field="at_date" min="${first}" max="${last}" value="${when.date}"></label>
        <label class="field" for="mr-time">Giờ<input class="input" id="mr-time" type="time" step="300" data-mr-field="at_time" value="${when.time}"></label></div>
      <p class="mr-hint">💍 Cả phố được mời dự tiệc lúc đó.</p>
      <p class="mr-label">Ai góp bao nhiêu</p><div class="segmented mr-split" role="radiogroup" aria-label="Tỉ lệ góp">${splits.map(([pct,label])=>`<button type="button" role="radio" aria-checked="${p.mine===pct}" class="${p.mine===pct?'active':''}" data-mr="split" data-pct="${pct}">${label}</button>`).join('')}</div>
      <label class="field" for="mr-mine"><span class="mr-mine-t">${mineText()}</span><input id="mr-mine" type="range" min="0" max="100" step="5" value="${p.mine}" data-mr-field="mine"></label>
      <label class="mr-check"><input type="checkbox" data-mr-field="announce"${p.announce?' checked':''}><span>Báo tin cưới cho cả phố (cần cả hai đồng ý)</span></label></section>
    </div><aside class="mr-breakdown" aria-label="Chi phí dự tính">${breakdown()}</aside></div>`;
}
const mineText=()=>`Tự chọn: bạn góp <b>${S.plan.mine}%</b>, ${esc(S.view.couple.partner.name)} góp <b>${100-S.plan.mine}%</b>`;
function breakdown(){
  const p=S.plan,q=costs(p),[mine,theirs]=split(q.deposit,p.mine),[bm,bt]=split(q.balance,p.mine),fq=S.quote,partner=esc(S.view.couple.partner.name);
  const fc=fq&&fq.total===q.total?fq.forecast:null;
  const secs=q.sections.map(s=>`<div class="mr-bd-sec"><div class="mr-bd-row head"><span>${s.name}</span><b>${xu(s.subtotal)}</b></div>${s.lines.map(l=>`<div class="mr-bd-row"><span>${esc(l.label)}</span><span>${xu(l.amount)}</span></div>`).join('')||'<div class="mr-bd-row muted"><span>Không chọn</span><span>0 xu</span></div>'}</div>`).join('');
  const w=wallet(),short=w<mine;
  return `<h3>Bảng dự trù</h3>${secs}
    <div class="mr-bd-row total"><span>Tổng cộng</span><b>${xu(q.total)}</b></div>
    <div class="mr-bd-row"><span>Đặt cọc ${S.catalog.deposit_pct}% (khi cả hai xác nhận)</span><b>${xu(q.deposit)}</b></div>
    <div class="mr-bd-row sub"><span>Bạn ${xu(mine)} · ${partner} ${xu(theirs)}</span></div>
    <div class="mr-bd-row"><span>Trả nốt vào ngày cưới</span><b>${xu(q.balance)}</b></div>
    <div class="mr-bd-row sub"><span>Bạn ${xu(bm)} · ${partner} ${xu(bt)} (trừ vào tiền mừng trước)</span></div>
    <div class="mr-bd-fc">${fc?`<div class="mr-bd-row"><span>Khách dự kiến</span><b>${fc.guests[0]}–${fc.guests[1]} / ${q.seats}</b></div>
      <div class="mr-bd-row"><span>Tiền mừng dự kiến</span><b>${xu(fc.gifts[0])}–${xu(fc.gifts[1])}</b></div>
      <div class="mr-bd-row ${fc.gifts[0]-q.total>=0?'good':fc.gifts[1]-q.total<0?'bad':''}"><span>Lời / lỗ dự kiến</span><b>${signed(fc.gifts[0]-q.total)} … ${signed(fc.gifts[1]-q.total)}</b></div>
      <p class="mr-hint">${esc(fq.mood.emoji)} Không khí: ${esc(fq.mood.label)}. Hàng xóm càng thân càng hay tới và mừng dày.</p>`:'<p class="mr-hint" role="status">Đang ước lượng khách và tiền mừng…</p>'}</div>
    ${short?`<p class="mr-flash warn">Ví của bạn còn ${xu(w)}, chưa đủ phần cọc ${xu(mine)}.</p>`:''}
    ${soon(p)?`<p class="mr-flash bad">⏰ Giờ cưới phải cách bây giờ ít nhất 1 tiếng: chọn từ ${esc(vnParts(Date.now()/1000+3660).time)} hôm nay trở đi.</p>`:''}
    ${S.flash?.kind==='bad'?flash():''}
    ${soon(p)?`<button type="button" class="btn primary big full" disabled>Gửi kế hoạch cho ${partner}</button>`:btn(`Gửi kế hoạch cho ${partner}`,'plan_send',{},'primary big full')}
    <p class="mr-hint">Chưa trừ tiền. ${partner} xác nhận thì cả hai mới đặt cọc.</p>`;
}
function paintBreakdown(){
  const el=S.dlg?.querySelector('.mr-breakdown');if(!el||!S.plan)return;
  el.innerHTML=breakdown();
  const n=S.dlg.querySelector('.mr-tables-n');if(n)n.innerHTML=`<b>${S.plan.tables} bàn</b> · ${S.plan.tables*S.catalog.seats} ghế`;
  const m=S.dlg.querySelector('.mr-mine-t');if(m)m.innerHTML=mineText();
}
