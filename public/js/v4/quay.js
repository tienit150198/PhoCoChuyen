/** 🏪 Quầy của bạn: your own counter, run by staff you hire (story mode).
 * Every rule and number lives in game/quay.py; this file renders api.state.journey.quay with the static numbers
 * (content.journey.quay) and sends `jr_quay_*` commands. Its own dialog (like Xe & phương tiện), opened with
 * data-action="quay" from the "Ngân hàng & nhà" hub. Owner style: one short line and one obvious button per card,
 * explanations behind "?". Styles: /css/bank.css + /css/quay.css.
 * 💼 Làm thêm (game/quay_hire.py): another player's counter hires you for a shift, or you hire a player for yours;
 * GET /api/quay and POST /api/quay/<op> (the wage is escrowed by the server, paid once when the shift's day closes).
 * 🧑‍🍳 Tự tay (game/quay_self.py): the board (🍽️ Menu), the look (🎨 Trang trí) with a live preview of the counter
 * (./quay-scene.js), "Bán online", and the day at your own counter (S.view 'run'): serve each customer by hand (their
 * dishes from your board, the change from the coin drawer, a thank-you), pack and ship the phone's online orders
 * (./quay-ride.js), answer the day's tricky moments, then "Đóng ca". The client sends steps; the server prices them.
 * An older server (no content.journey.quay.menus): none of this shows. */
import {icon,escapeHTML as esc} from '../icons.js';
import {avInner} from './face.js';
import {visitorSelectionValid} from './workplace-visit-ui.js';
import {paintCounter} from './quay-scene.js';
import {figure} from './look.js';
import {confirmPurchase} from './payment.js';
import {RIDE,rideSVG,turnChoices} from './quay-ride.js';
import {signalHTML,mountSignals} from './traffic.js';
import {cloneMenu,selectDishes,menuPayload,filterDishes,pricePreview,restockQuote,createQuayPoller,focusSnapshot,restoreInputFocus,syncDraftValue} from './quay-business-ui.js';
import {businessControls,tickRunningCosts,theftRiskHTML,marketBanner} from './business-economy-ui.js';
import {staffLifeCard} from '../staff-life-ui.js';
import {ownerQueueHTML,ownerArrivalText,counterActivity,counterActivityHTML} from './quay-owner-queue.js';
import {shopEventCard} from '../shop-events-ui.js';
import {createQuaySync} from './quay-sync.js';
import {stallAway,stallAwayCard} from '../away-report.js';   // B4: 🧾 Lúc bạn vắng
import {keepStepper} from '../keep-ui.js';   // 🔒 Giữ lại cho ca của tôi (B4 part 2)
// Typed numbers in the − N + steppers (owner 07/10: "cho nhập số nhé").
import {qtyBox,QTY} from '../qty-input.js';
// "Tất cả" (F#290): lắp hết thiết bị, thuê đủ chỗ, reusing the per-item commands one by one.
import {buyAllPlan,quayHave,hireAllPlan,runAll} from './select-all.js';
// Clean layout (docs/UI_KIT.md, wave 5): ui-kit.js clean(), guarded so the node tests can load this file.
const clean=()=>typeof document!=='undefined'&&!!document.documentElement?.hasAttribute?.('data-clean');

const PAGE_SIZE=12;
const S={page:0,md:{},lk:{},run:null,anchor:'',anchorAt:0,dlg:null,env:null,view:'list',tab:'mine',pick:null,busy:false,flash:null,listening:false,open:{},help:{},wage:{},hire:null,loading:false,to:{}};
S.search={};S.stockDraft={};S.visit=null;S.visitor=null;S.visitorDraft={};S.syncFailed=false;S.poller=null;S.account=null;
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,op,data={},cls='',why='')=>`<button type="button" class="btn ${cls}" data-qy="${op}"${attrs(data)}${S.busy||why?' disabled':''}${why?` title="${esc(why)}"`:''}>${label}</button>`;
const J=()=>S.sync?.journey()||S.env?.api?.state?.journey||{};
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
  // A drag can retarget its click to <dialog>. Only a complete backdrop gesture dismisses it.
  const outside=e=>{const r=d.getBoundingClientRect();return e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom;};
  let backdropPress=false;
  d.addEventListener('pointerdown',e=>{backdropPress=e.button===0&&e.target===d&&outside(e);});
  d.addEventListener('pointercancel',()=>{backdropPress=false;});
  d.addEventListener('click',e=>{
    const dismiss=backdropPress&&e.target===d&&outside(e);backdropPress=false;
    if(dismiss){d.close();return;}
    const el=e.target.closest('[data-qy]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();S.anchor=selOf(el);S.anchorAt=performance.now();onClick(el.dataset.qy,el.dataset,el);
  });
  d.addEventListener('input',e=>{const t=e.target;if(t.name==='qy-price'){const st=stallOf(t.dataset.id);if(st){menuDraft(st).p[t.dataset.k]=t.value;render();}return;}if(t.name==='qy-search'){S.search[t.dataset.id]=t.value;render();return;}if(t.name==='qy-stock'){(S.stockDraft[t.dataset.id]??={})[t.dataset.k]=t.value;render();return;}if(t.name==='qy-name'&&S.pick)S.pick.name=t.value;
    if(t.name==='qy-sign'){const st=stallOf(t.dataset.id);if(st){lookDraft(st).name=t.value;paintCanvases();}}});
  d.addEventListener('submit',e=>e.preventDefault());
  // the spacer under the page goes away as the player scrolls back up (never while a render is holding the spot)
  d.addEventListener('scroll',()=>{const top=d.scrollTop,up=top<(d._qyTop??top);d._qyTop=top;
    const sp=d.querySelector('.qy-spacer'),h=sp?.offsetHeight||0;if(!h||!up||S.hold)return;
    const spare=d.scrollHeight-(top+d.clientHeight);if(spare>1)sp.style.height=`${Math.max(0,h-spare)}px`;},{passive:true});
  for(const ev of ['wheel','touchstart','keydown'])d.addEventListener(ev,()=>{S.hold=null;},{passive:true});
  d.addEventListener('close',()=>{import('./workplace-visit.js').then(m=>m.workVisitsOwnerFocus(S.env)).catch(()=>{});S.poller?.stop();S.flash=null;S.view='list';S.pick=null;S.run=null;});
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')S.poller?.stop();else if(d.open)S.poller?.start();});
  setInterval(()=>{if(d.open)tickRunningCosts(d,S.costSeen??={});},1000);   // ⏱️ the open counter's running cost, live
  S.dlg=d;return d;
}
export async function openQuay(env,data={}){
  const account=env.api.account?.username||'';if(account!==S.account){S.md={};S.lk={};S.search={};S.stockDraft={};S.visitorDraft={};S.account=account;}
  S.env=env;
  if(S.syncApi!==env.api){
    S.sync?.dispose();S.syncApi=env.api;
    S.sync=createQuaySync(env.api,()=>{if(S.dlg?.open&&!S.busy)render();});
  }
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();
  S.focusedVisitorPlace=null;S.view='list';S.pick=null;S.hire=null;S.visitor=data.visitor||null;if(env.api.quayInvites>0&&!data.visitor)S.tab='jobs';   // 💼 a friend's invitation waits: open on it
  if(S.visitor){const st=V()?.stalls?.find(st=>st.business?.visitor_orders?.some(o=>String(o.id)===String(S.visitor)));if(st){S.visit=st.id;S.view='visitor';}}
  if(!d.open){d.showModal();toTop();}
  render();
  S.poller??=createQuayPoller({refresh:()=>S.sync.refresh(),active:()=>!!S.dlg?.open&&!S.busy&&document.visibilityState!=='hidden',failed:failed=>{if(S.syncFailed!==failed){S.syncFailed=failed;if(S.dlg?.open)render();}}});S.poller.start();
  if(S.tab==='jobs')loadHire();
}
export async function quayAction(action,data,el,env){
  if(action!=='quay')return false;
  await openQuay(env,data);return true;
}

async function send(action,payload={}){
  S.busy=true;render();
  try{
    const r=await S.sync.command(action,payload);
    S.flash={text:[r.message,...(r.effects||[]).filter(Boolean)].filter(Boolean).join(' '),kind:'good'};
    return r;
  }catch(e){S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;render();}
}
/** The same command for each payload, one at a time (select-all.js runAll); stops at the first refusal, whose
 * message comes back as `why`. One busy spell and one flash for the whole run. */
async function sendAll(payloads,action){
  S.busy=true;render();let why='';
  try{
    const r=await runAll(payloads,async p=>{try{return await S.sync.command(action,p);}catch(e){why=e.quiet?'':(e.message||'');return null;}});
    return {...r,why};
  }finally{S.busy=false;render();}
}
async function preparePayment(){
  try{await S.sync.ensureCurrent();return true;}
  catch(e){S.flash={text:e.message||'Chưa đồng bộ được số dư. Thử lại nhé.',kind:'bad'};render();return false;}
}
const ask=async(title,msg,label,money)=>!money||await preparePayment()?S.env.confirmAction(title,msg,label,money):false;
/* 💼 hired players: the server's view (offers, my offers, friends) and its ops */
const took=d=>{if(d?.state&&typeof d.revision==='number')S.env.api.accept({state:d.state,revision:d.revision});};
async function loadHire(){
  if(S.loading)return;S.loading=true;
  try{const d=await S.env.api.json('/api/quay');took(d);S.hire=d;S.env.api.quayInvites=(d.board||[]).filter(b=>b.invite).length;}
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
    case'visit':S.visit=data.id;S.view='visit';S.flash=null;render();toTop();return;
    case'pause':send('jr_quay_pause',{stall:data.id,on:data.on==='true'});return;
    case'keep':send('jr_quay_keep',{stall:data.id,dish:String(data.k||''),qty:Number(data.n)||0});return;   // 🔒 Giữ cho ca
    case'protection':{const st=stallOf(data.id),plan=st?.business?.protection?.options?.find(x=>x.level===data.level);if(!plan)return;if(await ask('Đổi gói bảo vệ quầy?',`${plan.label} · ${xu(plan.period_cost)} / ${Math.round((st.business.period_seconds||600)/60)} phút hoạt động, lấy từ két/vốn quầy.`,'Chọn gói'))await send('jr_quay_protection',{stall:data.id,level:data.level});return;}
    case'staffEvent':{const st=stallOf(data.id),event=st?.staff_life?.pending,choice=event?.choices?.find(x=>x.id===data.choice);if(!event||event.id!==data.event||!choice)return;if(await ask(event.title,`${choice.label}${choice.cost?` · ${xu(choice.cost)} từ két/vốn`:''}. ${choice.effect||''}`,'Xác nhận'))await send('jr_quay_staff_event',{stall:data.id,event:event.id,choice:choice.id,confirm:true});return;}
    case'restock':{const st=stallOf(data.id);if(!st)return;const quote=restockQuote(S.stockDraft[st.id],st.business?.stock||[]);if(!quote){S.flash={text:'Nhập số lượng nguyên dương cho ít nhất một món.',kind:'bad'};render();return;}if(await ask('Nhập hàng vào kho quầy?',`${quote.count} phần nguyên liệu · ${xu(quote.total)} từ két/vốn quầy.`,`Nhập hàng · ${xu(quote.total)}`)){const pendingDraft=JSON.stringify(S.stockDraft[st.id]);const r=await send('jr_quay_restock',{stall:st.id,items:quote.items});if(r&&JSON.stringify(S.stockDraft[st.id])===pendingDraft){delete S.stockDraft[st.id];render();}}return;}
    case'close':S.dlg.close();return;
    case'help':S.help[data.key]=!S.help[data.key];render();return;
    case'back':S.view='list';S.pick=null;render();toTop();return;
    case'courier':S.dlg.close();S.env.openSheet('home',{jrView:'courier'});return;
    case'page':S.page=Math.max(0,Number(data.page)||0);render();toTop();return;
    case'prepare':{const st=stallOf(data.id);if(!st)return;const enabled=data.enabled==='true';
      if(!enabled&&data.kind!=='security'&&!await ask('Tắt kiểm tra hằng ngày?','Quầy có thể vi phạm khi kiểm tra. Bạn có thể bật lại bất cứ lúc nào.','Tắt kiểm tra'))return;
      send('jr_quay_prepare',{stall:data.id,kind:data.kind,enabled});return;}
    case'incident':send('jr_quay_incident',{stall:data.id,choice:data.choice});return;
    case'new':{const can=V()?.can||[];S.view='open';S.pick={trade:can[0]||'',place:'xe',name:''};S.flash=null;render();toTop();return;}
    case'trade':if(S.pick){S.pick.trade=data.id;render();}return;
    case'place':if(S.pick){S.pick.place=data.id;render();}return;
    case'open':{const p=S.pick,P=place(p?.place);if(!p?.trade||!P.id)return;
      const total=P.price+P.fund;
      if(await ask(`Mở ${P.name.toLowerCase()}?`,`${xu(P.price)} + ${xu(P.fund)} vốn quầy.`,`Mở quầy · ${xu(total)}`,{cost:total,pocket:['wallet','account']})){
        const name=(p.name||'').trim();
        const r=await send('jr_quay_open',{trade:p.trade,place:p.place,...(name?{name}:{}),confirm:true});
        if(r){S.view='list';S.pick=null;render();toTop();}
      }return;}
    case'more':S.open[data.id]=S.open[data.id]===data.part?'':data.part;render();return;
    case'till':send('jr_quay_till',{stall:data.id,...(data.to?{to:data.to}:{})});return;
    case'fund':{const amount=num(`#qy-fund-${data.id}`);if(!amount){S.flash={text:'Nhập số xu nhé.',kind:'bad'};render();return;}
      send('jr_quay_fund',{stall:data.id,amount:data.sign==='-'?-Math.abs(amount):Math.abs(amount)});return;}
    case'order':send('jr_quay_order',{stall:data.id,level:data.level});return;
    case'step':{const k=data.key;const base=S.wage[k]??Number(data.wage),to=data.set!==undefined?Number(data.set)||0:base+Number(data.by);S.wage[k]=Math.min(Number(data.max||1e6),Math.max(Number(data.min||1),to));render();return;}
    case'tab':S.tab=data.tab;S.flash=null;render();toTop();if(S.tab==='jobs')loadHire();return;
    case'reload':S.hire=null;loadHire();return;
    case'to':S.to[data.id]=data.code||'';render();return;
    case'post':{const st=stallOf(data.id);if(!st)return;const w=S.wage[`p:${st.id}`]??Number(data.wage);
      if(!await preparePayment())return;
      const current=stallOf(st.id);if(!current)return;
      const src=await confirmPurchase(S.env,{title:'Đăng ca làm thêm?',message:`Giữ ${xu(w)} để trả lương ca này. Nếu hủy hoặc hết hạn, tiền hoàn về nguồn đã chọn. Quỹ chung đã đóng thì hoàn về ví người chi.`,label:`Đăng ca · ${xu(w)}`,cost:w,noCredit:true,defaultMethod:'stall',extraSources:[{id:'stall',label:'Két và vốn quầy',balance:current.till+current.fund,text:'Giữ lương từ két và vốn quầy.'}]});
      if(src)hireSend('post',{stall:st.id,wage:w,src,rid:globalThis.crypto.randomUUID(),...(S.to[st.id]?{to:S.to[st.id]}:{})});return;}
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
    case'buyAll':{const st=stallOf(data.id);if(!st||S.busy)return;const plan=buyAllPlan(CAT()?.items,st.items,st.place,quayHave(J()));if(!plan.fit.length)return;
      const all=plan.fit.length===plan.todo.length,names=plan.fit.map(it=>`${it.emoji} ${it.name.toLowerCase()}`).join(', ');
      const msg=all?`Sẽ lắp: ${names}. Tổng ${xu(plan.total)} từ ví, thiếu mới lấy tài khoản.`:`Đủ tiền cho ${plan.fit.length}/${plan.todo.length} món, lắp món rẻ trước: ${names}. Tổng ${xu(plan.fitTotal)}. Món còn lại để lần sau.`;
      if(!await ask(all?`Lắp tất cả ${plan.todo.length} món?`:`Lắp ${plan.fit.length} món?`,msg,`Lắp · ${xu(plan.fitTotal)}`,{cost:plan.fitTotal,pocket:['wallet','account']}))return;
      const r=await sendAll(plan.fit.map(it=>({stall:st.id,item:it.id,confirm:true})),'jr_quay_buy');
      S.flash={text:r.done===r.total&&all?`🛠️ Đã lắp đủ ${r.done} món.`:`🛠️ Đã lắp ${r.done}/${plan.todo.length} món.${r.why?' '+r.why:all?'':' Món còn lại chờ đủ xu nhé.'}`,kind:r.done?'good':'bad'};render();return;}
    case'hireAll':{const st=stallOf(data.id);if(!st||S.busy)return;const P=place(st.place),plan=hireAllPlan(st.cands,st.staff.length,P.slots||1,rowWage(st));if(plan.length<2)return;
      const per=st.business?`${Math.round(st.business.period_seconds/60)} phút hoạt động`:'ngày';
      if(!await ask(`Thuê ${plan.length} người?`,`Lương mỗi ${per}: ${plan.map(c=>`${c.name} ${xu(c.wage)}`).join(', ')}. Trả dần từ két/vốn quầy khi làm.`,'Thuê tất cả'))return;
      const r=await sendAll(plan.map(c=>({stall:st.id,cand:c.id,wage:c.wage})),'jr_quay_hire');
      for(const c of plan.slice(0,r.done))delete S.wage[`c:${st.id}:${c.id}`];
      S.flash={text:r.done===r.total?`👥 ${r.done} người đã nhận việc.`:`👥 ${r.done}/${r.total} người đã nhận việc.${r.why?' '+r.why:''}`,kind:r.done?'good':'bad'};render();return;}
    case'police':send('jr_quay_police',{stall:data.id});return;
    case'ownerEvent':if(!S.busy)send('jr_quay_event',{stall:data.id,event:data.event,choice:data.choice,confirm:true});return;
    case'pay':send('jr_quay_pay',{stall:data.id});return;
    case'sell':{const st=stallOf(data.id);if(!st)return;
      if(await ask(`Sang nhượng ${st.name}?`,'Nhận lại một nửa giá chỗ, cả két và vốn quầy.',`Sang nhượng · ${xu(st.sell)}`))send('jr_quay_sell',{stall:data.id,confirm:true});return;}
    default:onSelf(op,data);
  }
}

/* ---- rendering ----
 * The dialog itself is the scroller (.sheet: overflow-y auto), not .qy-body. Every render patches the page in place
 * (morph, like fair.js): only the nodes that changed are touched, so the tapped button and the focus stay and the
 * dialog never loses its height for a moment. The control just tapped is then held at the same spot on screen (a
 * flash line or a part opening above it may change heights); a part that shrinks leaves a spacer under the page
 * until the player scrolls back up, so nothing jumps to the top (owner 03/10: "bấm vào là tự scroll lên"). */
const keyOf=n=>n.nodeType!==1?'':(n.getAttribute('data-qk')||n.id||'')+'|'+(n.getAttribute('data-qy')||'')+'|'+(n.getAttribute('data-id')||'')+(['SECTION','DETAILS'].includes(n.nodeName)?'|'+n.className:'')+(n.nodeName==='DETAILS'&&!n.className?'|'+n.querySelector('summary')?.textContent:'');
const same=(a,b)=>a.nodeType===b.nodeType&&a.nodeName===b.nodeName&&keyOf(a)===keyOf(b);
function morph(from,to){
  if(from.nodeType!==1){if(from.nodeValue!==to.nodeValue)from.nodeValue=to.nodeValue;return;}
  if(from.hasAttribute('data-qy-live')){   // drawn by script (the counter's canvas, its own width/height): only its label follows
    const l=to.getAttribute('aria-label');if(l!==null&&from.getAttribute('aria-label')!==l)from.setAttribute('aria-label',l);return;}
  // Native disclosure state belongs to the reader, not to a fresh server-state template.
  for(const {name} of [...from.attributes])if(!to.hasAttribute(name)&&!(from.nodeName==='DETAILS'&&name==='open'))from.removeAttribute(name);
  for(const {name,value} of [...to.attributes])if(from.getAttribute(name)!==value)from.setAttribute(name,value);
  if(from.nodeName==='INPUT'&&['qy-price','qy-search','qy-stock'].includes(from.name))syncDraftValue(from,to.value);
  const a=[...from.childNodes].filter(n=>!n.classList?.contains('mn-line')),b=[...to.childNodes];   // the header's money chip (v4/money.js) stays
  let i=0,j=0;
  for(;j<b.length;j++){
    const n=b[j],o=a[i];
    if(!o){from.append(n);continue;}
    if(same(o,n)){morph(o,n);i++;continue;}
    if(n.nodeName==='DETAILS'){
      const match=a.findIndex((node,index)=>index>i&&same(node,n));
      if(match>=0){const kept=a.splice(match,1)[0];from.insertBefore(kept,o);morph(kept,n);continue;}
    }
    if(a[i+1]&&same(a[i+1],n)){o.remove();morph(a[i+1],n);i+=2;continue;}   // a node went away
    if(b[j+1]&&same(o,b[j+1])){from.insertBefore(n,o);continue;}   // a node came in
    from.replaceChild(n,o);i++;
  }
  for(;i<a.length;i++)a[i].remove();
}
const tplEl=document.createElement('template');
const DATA=['qy','id','part','key','by','level','cand','staff','item','tab','to','code','sign','k','j','on','event','choice'];
/** A selector that finds "the same control" again after a render (its data-qy and the data that says which one). */
function selOf(el){
  if(el?.id)return `#${CSS.escape(el.id)}`;
  if(!el?.dataset?.qy)return '';
  return DATA.filter((k,i)=>DATA.indexOf(k)===i&&el.dataset[k]!==undefined).map(k=>`[data-${k}="${CSS.escape(el.dataset[k])}"]`).join('');
}
const bySel=sel=>sel?S.dlg.querySelector(`.qy-root ${sel}`):null;
function anchorEl(d){
  if(S.anchor&&performance.now()-S.anchorAt<1200){const el=bySel(S.anchor);if(el)return el;}
  if(d.scrollTop<1)return null;
  const top=d.getBoundingClientRect().top+60;   // under the sticky header
  for(const el of d.querySelectorAll('.qy-root [data-qy]'))if(el.getBoundingClientRect().top>=top)return el;
  return null;
}
function spacer(){
  let sp=S.dlg.querySelector('.qy-spacer');
  if(!sp){sp=document.createElement('div');sp.className='qy-spacer';sp.setAttribute('aria-hidden','true');S.dlg.append(sp);}
  return sp;
}
function holdAt(d,sel,y0,top){
  const sp=spacer(),an=bySel(sel);
  let want=top;
  if(an){const y=an.getBoundingClientRect().top;want=d.scrollTop+y-y0;}   // held at the same spot on screen (scrollTop read after
  // the layout: a page that got shorter has already been clamped by the browser)
  const room=d.scrollHeight-sp.offsetHeight-d.clientHeight;   // how far the page itself can scroll
  sp.style.height=want>room+1?`${Math.ceil(want-room)}px`:'0px';
  if(Math.abs(d.scrollTop-want)>1)d.scrollTop=want;
  d._qyTop=d.scrollTop;
}
function keep(fn){
  const d=S.dlg,an=anchorEl(d),sel=selOf(an),y0=an?an.getBoundingClientRect().top:0;
  const top=d.scrollTop,a=document.activeElement,asel=a&&d.contains(a)?selOf(a):'',input=a&&d.contains(a)&&a.matches('input,textarea')?focusSnapshot(a):null;
  fn();
  holdAt(d,sel,y0,top);
  if(asel&&!a.isConnected)bySel(asel)?.focus({preventScroll:true});
  if(input&&a!==document.activeElement)restoreInputFocus(d,input);
  // a few frames more: the canvas, the fonts or the money chip may still settle; the player's own scroll ends it
  const hold=S.hold={};let n=0;
  const tick=()=>{if(S.hold!==hold||!S.dlg)return;if(sel||top>0)holdAt(d,sel,y0,top);if(++n<12)requestAnimationFrame(tick);else S.hold=null;};
  requestAnimationFrame(tick);
}
function render(){
  if(!S.dlg)return;
  if(S.run){const st=stallOf(S.run.sid),r=st?.run,key=r?.cust?`${r.i}:${r.cust.name}`:null;
    if(S.run.customerKey!==undefined&&S.run.customerKey!==key)Object.assign(S.run,{step:'pick',tray:[],change:0,hint:''});S.run.customerKey=key;
    if(S.run.pack?.orderId){const order=r?.orders?.find(o=>o.j===S.run.pack.j);if(!order||order.id!==S.run.pack.orderId){const submitted=S.run.pack.submitting;S.run.pack=null;if(!submitted)S.flash={text:'Đơn này đã được cập nhật. Chọn đơn đang chờ để đóng gói tiếp nhé.',kind:'good'};}}
  }
  keep(()=>{const root=S.dlg.querySelector('.qy-root');tplEl.innerHTML=page();
    const box=document.createElement('div');box.append(tplEl.content);box.className=root.className;morph(root,box);});
  S.dlg.setAttribute('aria-busy',String(S.busy));
  paintCanvases();
}
/** A new page (another view, another tab): from the top, no spacer. */
function toTop(){S.anchor='';S.hold=null;if(!S.dlg)return;const sp=S.dlg.querySelector('.qy-spacer');if(sp)sp.style.height='0px';S.dlg.scrollTop=0;}
const helpBtn=key=>`<button type="button" class="qy-help" data-qy="help" data-key="${key}" aria-label="Giải thích" aria-expanded="${!!S.help[key]}">?</button>`;
const helpText=(key,text)=>S.help[key]?`<p class="bk-hint qy-hint">${text}</p>`:'';
/** An explanation paragraph (where the money goes, how an invite works): on the clean layout it folds behind the quầy's
 * own "?" (one tap shows it in place); on the classic layout it shows as before. */
const why=(key,text)=>clean()?`<p class="qy-why">${helpBtn(key)}</p>${helpText(key,text)}`:`<p class="bk-hint">${text}</p>`;
function head(){
  const v=V(),n=v?.stalls?.length||0,till=(v?.stalls||[]).reduce((a,x)=>a+x.till,0);
  const back=S.view!=='list'?`<button class="icon-btn" type="button" data-qy="back" aria-label="Quay lại">${icon('back',21)}</button>`:'<span class="qy-logo" aria-hidden="true">🏪</span>';
  return `<header class="sheet-head bk-head">${back}
    <div class="grow"><span class="eyebrow">NGÀY SỐNG ${fmt(J().life_day)}</span><h2 id="qy-title">Quầy của bạn</h2><p>${n?`${n} quầy · két ${xu(till)}`:'Mở quầy, thuê người, thu két'}</p>${btn('🛵 Sổ shipper','courier',{},'small ghost')}</div>
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
  if(S.view==='run'&&stallOf(S.run?.sid))return head()+`<div class="sheet-body bk qy-body">${runView(stallOf(S.run.sid))}</div>`;
  if(S.view==='visitor'&&stallOf(S.visit))return head()+`<div class="sheet-body bk qy-body">${visitorPanel(stallOf(S.visit))}</div>`;
  if(S.view==='visit'&&stallOf(S.visit))return head()+`<div class="sheet-body bk qy-body">${visitView(stallOf(S.visit))}</div>`;
  const inner=S.view==='open'?openView(v):listView(v);
  return head()+`<div class="sheet-body bk qy-body">${tabs}${flash()}${inner}</div>`;
}

function mainTabs(){
  const invites=S.hire?.board?(S.hire.board.filter(b=>b.invite).length):(S.env?.api?.quayInvites||0);
  const dot=V()?.shift?' <i class="qy-dot" aria-label="Có ca"></i>':invites?` <span class="qy-badge" aria-label="${invites} lời mời">${invites}</span>`:'';
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
    ${why('shift',`Ca làm ở tiệm ${esc(trade(sh.career).name)} của chính bạn: hàng nhập dùng quỹ nghề của bạn, nên quỹ đó hết thì nhập hàng không được. Vốn quầy chủ góp ở lại quầy của chủ, không chuyển sang bạn. Xong ca: bạn nhận ${xu(sh.wage)} lương, quầy chủ nhận phần doanh thu.`)}
    <div class="bk-actions">${btn('Vào làm','go',{career:sh.career},'primary')}${btn('Bỏ ca','quit',{},'ghost')}</div></section>`:'';
  const rows=(h.board||[]).map(b=>`<li class="qy-person"><div class="grow"><b>${b.emoji} ${esc(b.name)}</b>${b.invite?' <span class="qy-tag">Mời bạn</span>':''}<small>${esc(b.owner)} · ${xu(b.wage)}</small>${b.locked&&!h.lock?`<small class="qy-locked">🔒 ${esc(b.locked)}</small>`:''}</div>
      <div class="qy-person-act">${btn('Nhận ca','accept',{id:b.id},'small primary',sh?'Bạn đang có một ca':b.locked?'Chưa nhận được':'')}${b.invite?btn('Từ chối','decline',{id:b.id},'small ghost'):''}</div></li>`).join('');
  const board=`<section class="bk-card"><h3>Quầy cần người ${helpBtn('jobs')}</h3>
    ${helpText('jobs',`Nhận một ca, làm một ngày đúng nghề đó. Xong ${R.tasks||2} việc rồi khép ca là lương vào ví. Bỏ ca lúc nào cũng được, không mất gì.`)}
    ${h.lock?`<p class="bk-hint">${esc(h.lock)}</p>`:''}${rows?`<ul class="qy-list">${rows}</ul>`:h.lock?'':'<p class="bk-hint">Chưa có quầy nào cần người. Ghé lại sau nhé.</p>'}</section>`;
  return mine+board;
}
const JOB_LINE={open:x=>x.to?(x.blocked?`🔒 ${x.blocked}`:`Đã gửi lời mời. Chờ ${x.to} mở 🏪 Quầy của bạn → 💼 Làm thêm để nhận`):'Đang chờ người nhận',taken:x=>`${x.worker} đang làm ca`,paid:x=>`${x.worker} xong ca: +${xu(x.earned)} vào két`,
  lapsed:()=>'Ca chưa đủ việc: lương về lại',quit:x=>`${x.worker||'Người làm'} bận: lương về lại`,declined:x=>`${x.to||'Bạn ấy'} bận: lương về lại`,
  expired:()=>'Hết hạn: lương về lại',cancelled:()=>'Đã hủy',gone:()=>'Đã hủy'};
function hirePart(st){
  const h=S.hire;
  if(!h){loadHire();return '<p class="bk-hint">Đang tải…</p>';}
  if(h.error)return `<p class="bk-hint">${esc(h.error)}</p>`;
  const R=h.rules||{},max=Math.max(R.wage_min||10,Math.min(R.wage_max||120,st.value||0)),min=R.wage_min||10;
  const offers=(h.mine||[]).filter(x=>x.stall===st.id).map(x=>`<li class="qy-person"><div class="grow"><b>💼 ${xu(x.wage)}</b><small>${esc(x.refund_pending?'Lương giữ chỗ đang chờ quỹ chung có chỗ để hoàn.':(JOB_LINE[x.status]||(()=>''))(x))}</small></div>
      ${x.status==='open'?`<div class="qy-person-act">${btn('Hủy','cancel',{id:x.id},'small ghost')}</div>`:''}</li>`).join('');
  const k=`p:${st.id}`,w=Math.min(max,S.wage[k]??Math.min(30,max));
  const to=S.to[st.id]||'';
  const friends=h.friends||[],chosen=friends.find(f=>f.code===to);
  const chips=[{code:'',name:'Ai cũng được'},...friends].map(f=>
    `<button type="button" class="qy-chip${to===f.code?' on':''}" data-qy="to" data-id="${st.id}" data-code="${esc(f.code)}"${f.eligible===false?' disabled':''}>${esc(f.name)}${f.eligible===false?` · chờ ${f.wait_hours} giờ`:''}</button>`).join('');
  const slots=place(st.place).slots||1,pending=(h.mine||[]).filter(x=>x.stall===st.id&&['open','taken'].includes(x.status)).length>=slots;
  const form=h.lock?`<p class="bk-hint">${esc(h.lock)}</p>`:`${why('invite',`Mời bạn bè: chọn tên bạn bên dưới rồi gửi lời mời. Bạn ấy vào Quầy của bạn → Quầy cần người để nhận ca. Kết bạn xong là mời được ngay.`)}<div class="qy-chips">${chips}</div>
    ${!friends.length?'<p class="bk-hint">Chưa có bạn bè. Kết bạn trong mục Bạn bè rồi quay lại đây nhé.</p>':''}
    ${pending?`<p class="bk-hint">Quầy này đăng tối đa ${slots} ca cùng lúc (bằng số chỗ đứng) và đã đủ. Muốn đổi từ “Ai cũng được” sang mời riêng, hủy một ca đang chờ rồi chọn tên bạn và gửi lại.</p>`:''}
    <div class="qy-person"><div class="grow"><small>Lương một ca</small></div><div class="qy-person-act">${stepper(k,w,st.id,'',min,max)}${btn(to?'Gửi lời mời':'Đăng ca công khai','post',{id:st.id,wage:w},'small primary',st.closed?'Quầy đang đóng':pending?'Quầy đã đủ ca':to&&(!chosen||chosen.eligible===false)?'Bạn này hiện chưa nhận lời mời được':'')}</div></div>`;
  return `<h4>🙋 Thuê người chơi ${helpBtn('hire')}</h4>
    ${helpText('hire',`Một người chơi làm một ngày nghề này cho quầy, ở tiệm của chính họ: hàng họ nhập dùng quỹ nghề của họ, vốn quầy bạn góp vẫn ở lại quầy. Xong ${R.tasks||2} việc thì họ nhận lương, két nhận tiền bán. Chọn nguồn giữ lương trước khi đăng: két/vốn quầy, ví, tài khoản hoặc quỹ chung. Không dùng tín dụng. Không ai làm thì hoàn về nguồn đã chọn.`)}
    ${offers?`<ul class="qy-list">${offers}</ul>`:''}${form}`;
}

/* The counters, or the first one to open. */
function listView(v){
  if(!v.stalls.length){
    if(v.lock)return `<section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🏪</div><h3>Chưa mở được quầy</h3><p>${esc(v.lock)}</p>${helpBtn('lock')}${helpText('lock',`Làm ${CAT().served} việc ở một nghề bán hàng rồi quay lại.`)}</section>`;
    return `<section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🏪</div><h3>Mở quầy đầu tiên</h3><p>Bán món bạn rành, thuê người đứng quầy.</p>
      <div class="bk-actions center">${btn('Mở quầy','new',{},'primary')}</div>${helpBtn('first')}${helpText('first',`Thuê nhân viên để quầy bán cả lúc bạn offline, tới khi hết nguyên liệu hoặc tiền lương. Chưa thuê ai thì bạn tự đứng quầy hoặc giao hàng. Nhập nguyên liệu và giữ đủ vốn để tiệm tiếp tục hoạt động.`)}</section>${hiredReceipts(v.receipts)}`;
  }
  const more=(CAT().unlimited||v.stalls.length<CAT().max)&&!v.lock?`<div class="bk-actions center">${btn('＋ Mở thêm quầy','new',{},'ghost')}</div>`:'';
  const pages=Math.ceil(v.stalls.length/PAGE_SIZE);S.page=Math.min(S.page,pages-1);
  const nav=pages>1?`<nav class="bk-actions center" aria-label="Trang quầy">${btn('‹ Trước','page',{page:S.page-1},'small',S.page?'':'Trang đầu')}<span>${fmt(v.stalls.length)} quầy · ${S.page+1}/${pages}</span>${btn('Sau ›','page',{page:S.page+1},'small',S.page<pages-1?'':'Trang cuối')}</nav>`:'';
  return marketBanner(v.stalls)+nav+v.stalls.slice(S.page*PAGE_SIZE,(S.page+1)*PAGE_SIZE).map(stallCard).join('')+nav+more+hiredReceipts(v.receipts);
}

const ownerEvents=st=>shopEventCard(st.shop_events,(label,e,ch)=>btn(label,'ownerEvent',{id:st.id,event:e.id,choice:ch.id},'shop-event-choice',ch.affordable===false?'Chưa đủ tiền':''));
function stallCard(st){
  const P=place(st.place),T=trade(st.trade),cat=CAT();
  const today=st.today||{};
  const status=st.business?st.business.reason:st.due?`Chờ đóng ${xu(st.due)} chi phí quầy`:st.economy?.paused?'Tạm dừng: kiểm hàng và vệ sinh':st.closed?'Đóng cửa chờ chủ':!st.staff.length?(cat.menus?'Chưa thuê ai: tự đứng quầy nhé':'Chưa có người đứng quầy'):
    `Hôm nay ${cat.weather[today.w]||''} · ${cat.pace[today.pace]||''}${today.x3?' · 🔥':''}`;
  const week=st.hist.reduce((a,h)=>a+h[2],0);
  const part=S.open[st.id]||'';
  const alerts=[
    st.case?`<div class="bk-alert bad qy-row"><span>🚨 ${st.case.all?'Mất cả két':'Trộm lấy'} ${xu(st.case.lost)}</span>${st.case.rep?'<small>Đã báo công an</small>':btn('Báo công an','police',{id:st.id},'small')}</div>`:'',
    st.due?`<div class="bk-alert warn qy-row"><span>🧾 Chi phí chưa trả ${xu(st.due)}</span>${btn('Đóng tiền','pay',{id:st.id},'small primary')}</div>`:'',
    !st.business&&!st.closed&&st.left<=1&&st.till>0?`<p class="bk-alert warn">Ghé thu két kẻo quầy đóng nhé.</p>`:'',
  ].join('');
  const self=!!cat.menus&&!!st.menu;   // 🧑‍🍳 a server with the board (1.5.3+)
  const tabs=[...(self?[['menu','🍽️ Menu'],['look','🎨 Trang trí']]:[]),['staff',`👥 Nhân viên ${st.staff.length}/${P.slots||1} chỗ`],['stock','📦 Hàng'],['fund','💼 Vốn'],['up','🛠️ Nâng cấp'],...(st.economy?[['economy','🧾 Sổ quầy & an toàn']]:[])];
  return `<section class="bk-card qy-stall" data-qk="st:${st.id}">
    ${self?`<canvas class="qy-scene" data-qy-live data-cv="${st.id}" role="img" aria-label="${esc(`Quầy ${st.name}`)}"></canvas>${counterActivityHTML(st,esc)}`:''}
    <div class="qy-top"><span class="qy-tile" aria-hidden="true">${P.emoji||'🏪'}<i>${T.emoji}</i></span>
      <div class="grow"><h3>${esc(st.name)}</h3><p class="qy-line">${esc(status)}</p></div></div>
    ${stallAwayCard(stallAway(st,S.env?.api?.state?.name,id=>dishOf(st,id).name))}${alerts}${ownerEvents(st)}
    ${self?selfRow(st):''}${businessPanel(st)}${visitorQueue(st)}
    <div class="qy-till"><div><small>Két</small><strong>${xu(st.till)}</strong>${st.hist.length?`<small>${st.hist.length} ngày qua: ${week>=0?'+':'−'}${xu(Math.abs(week))}</small>`:''}</div>
      ${btn(st.closed&&!st.due&&!st.till?'Mở lại quầy':'Thu két','till',{id:st.id},self?'':'primary',st.till||st.closed?'':'Két đang trống')}</div>
    <p class="qy-line">Ai bán, lãi tính thế nào? ${helpBtn(`sales:${st.id}`)}</p>
    ${helpText(`sales:${st.id}`,'Nhân viên tự bán cả khi bạn offline, tới khi hết hàng hoặc hết tiền vận hành. Chọn “Tự đứng quầy” để tự phục vụ và giao hàng; chưa thuê ai thì đóng quầy không sinh doanh thu. Ca thuê người chơi được ghi riêng.')}
    ${helpText(`sales:${st.id}`,`Lời ngày = doanh thu − tiền hàng (kể cả hàng hư) − lương − điện − phí online/giao hàng (nếu có). Lượng bán tùy thời tiết, khách, menu, lượng hàng và sức phục vụ. Chuyện phát sinh trong ca cũng có thể tăng hoặc giảm lời. Sổ quầy đã trừ thuê chỗ theo ngày có bán, vật tư, bảo vệ, thuế và thiệt hại sự cố. Quầy tự động tính hàng và chi phí cho phần thời gian thực sự hoạt động, kể cả khi bạn offline; không tự rút ví hay ngân hàng khi thiếu vốn.`)}
    <div class="segmented qy-tabs" role="tablist">${tabs.map(([k,l])=>`<button type="button" role="tab" aria-selected="${part===k}" class="${part===k?'active':''}" data-qy="more" data-id="${st.id}" data-part="${k}">${l}</button>`).join('')}</div>
    ${part==='menu'?menuPart(st):part==='look'?lookPart(st):part==='staff'?staffPart(st,P):part==='stock'?stockPart(st):part==='fund'?fundPart(st):part==='up'?upPart(st):part==='economy'?economyPart(st):''}
  </section>`;
}

function hiredReceipts(rows){
  if(!rows?.length)return '';
  const source={stall:'két/vốn quầy',cash:'ví',account:'tài khoản ngân hàng',joint:'quỹ chung'};
  return `<details class="bk-card"><summary>💼 Biên nhận ca người chơi (${rows.length})</summary>${why('receipts',`Lương đã giữ trước từ nguồn ghi trên biên nhận. Số vào két/ví chỉ trừ thuế; không trừ lương, hàng hay thuê chỗ lần nữa. Lãi ca tính cả khoản lương đã giữ. Biên nhận tách khỏi ngày tự bán và được tính vào thuế chung của chủ.`)}<ul class="qy-list">${[...rows].reverse().map(r=>`<li><b>${esc(r.label)} · ngày ${r.d}</b><p>Doanh thu ${xu(r.rev)} · lương đã giữ ${xu(r.wage)} từ ${source[r.source]||''}</p><p>GTGT ${xu(r.vat)} · thu nhập ${xu(r.income)} · lãi ca ${xu(r.net)}</p><small>${r.pocket==='wallet'?'Vào ví':'Vào két'} ${xu(r.cash_net)} sau thuế</small></li>`).join('')}</ul></details>`;
}

function economyPart(st){
  const e=st.economy,tax=CAT().tax||{},c=e.costs;
  const rows=c?[['Doanh thu',e.revenue],['Hàng, lương, điện, giao hàng',-c.base],['Thuê chỗ',-c.rent],['Vật tư & vệ sinh',-c.supplies],['Bảo vệ',-c.security],['Thuế GTGT (game)',-c.vat],['Thuế thu nhập (game)',-c.income],['Thiệt hại / xử lý vi phạm',-c.incident],['Lời sau mọi chi phí',e.net]]:[];
  const ledger=rows.length?`<dl>${rows.map(([name,n])=>`<div class="qy-row"><dt>${name}</dt><dd>${n<0?'−':n>0?'+':''}${xu(Math.abs(n))}</dd></div>`).join('')}</dl>`:'<p class="bk-hint">Bán một ngày để có sổ thu chi.</p>';
  const controls=[['hygiene','Kiểm hàng & vệ sinh','Ngừng bán hàng hỏng; kiểm tra an toàn đạt khi bật.'],['invoices','Lưu chứng từ','Lưu hóa đơn, sổ hàng để đối chiếu khi kiểm tra.'],...(st.business?[]:[['security','Bảo vệ quầy',`${xu(e.security_fee)} / ngày có bán: giảm 20% khả năng bị trộm và giảm thiệt hại trộm cướp.`]])].map(([kind,label,line])=>`<div class="qy-person"><div class="grow"><b>${label} · ${e[kind]?'Bật':'Tắt'}</b><small>${line}</small></div>${btn(e[kind]?'Tắt':'Bật','prepare',{id:st.id,kind,enabled:!e[kind]},'small')}</div>`).join('');
  const incident=e.incident;
  const names={theft:'Trộm két',robbery:'Cướp tiền bán hàng',food_check:'Kiểm tra vệ sinh',police_check:'Kiểm tra chứng từ',extortion:'Bị đòi tiền bảo kê'};
  const states={open:'đang chờ xử lý',clear:'đạt, không phạt',violation:'có vi phạm',repaired:'đã khắc phục',reported:'đã lưu bằng chứng và báo công an',refused:'đã từ chối'};
  const risk=incident?`<p class="bk-alert">${names[incident.kind]||''}: ${states[incident.status]||''}${incident.loss?` · thiệt hại ${xu(incident.loss)}`:''}</p>${incident.kind==='extortion'&&incident.status==='open'?`<div class="bk-actions">${btn('Lưu bằng chứng & báo công an','incident',{id:st.id,choice:'report'},'small primary')}${btn('Từ chối trả tiền','incident',{id:st.id,choice:'refuse'},'small')}</div>`:''}`:'';
  return `${st.business?why('table',`Bảng dưới dành cho ca thuê người chơi và kỳ cũ. Hoạt động liên tục ghi thuế thu nhập trên lãi dương, phí môi trường và bảo vệ riêng; xem chi phí và lãi hiện tại trong bảng vận hành của quầy.`):''}<h4>🧾 ${st.business?'Sổ ca thuê & kỳ trước':'Sổ quầy & an toàn'}</h4>${ledger}${why('tax',`Mức xu trong game, không phải mức thuế ngoài đời: GTGT ${tax.vat_pct||2}% phần doanh thu vượt ${xu(tax.revenue_allowance||1000)}; thu nhập ${tax.income_pct||5}% phần lãi dương vượt ${xu(tax.profit_allowance||200)} mỗi ${tax.period||30} ngày sống. Cộng chung mọi quầy của chủ; lỗ được bù trong kỳ. Không có lệ phí môn bài.`)}${why('supplies',`Vật tư và vệ sinh: ${e.supplies_pct}% doanh thu. Lời thay đổi theo khách và chi phí; một sự cố có thể làm cả ngày lỗ. Các khoản phí chỉ trừ ở quầy có bán.`)}${risk}${controls}${hiredReceipts(e.receipts)}`;
}

function stepper(key,value,id,extra,min=1,max=1e4){   // wages: 1..10 000 xu, as game/quay.py checks
  const box=qtyBox({value,min,max,money:true,label:'Lương (xu)',live:true,go:`data-qy="step"${attrs({id,key,set:QTY,wage:value,min,max})}`});
  return `<span class="qy-step">${btn('−','step',{id,key,by:-1,wage:value,min,max},'small ghost')}${box}${btn('＋','step',{id,key,by:1,wage:value,min,max},'small ghost')}</span>${extra||''}`;
}
function staffPart(st,P){
  const rows=st.staff.map(x=>{const k=`s:${st.id}:${x.id}`,w=S.wage[k]??x.wage;
    return `<li class="qy-person"><div class="grow"><b>${MOOD(x.mo)} ${esc(x.name)}</b>${x.g?' <span title="Rất cẩn thận">⭐</span>':''}<small>Lương ${xu(x.wage)}/${st.business?`${Math.round(st.business.period_seconds/60)} phút hoạt động`:'ngày'} · xin ${xu(x.ask)}</small></div>
      <div class="qy-person-act">${stepper(k,w,st.id)}${w!==x.wage?btn('Lưu','wage',{id:st.id,staff:x.id,wage:w},'small primary'):btn('Cho nghỉ','fire',{id:st.id,staff:x.id,name:x.name},'small ghost')}</div></li>`;}).join('');
  const cands=(st.cands||[]).map(c=>{const k=`c:${st.id}:${c.id}`,w=S.wage[k]??c.ask;
    return `<li class="qy-person"><div class="grow"><b>${esc(c.name)}</b>${c.g?' ⭐':''}<small>${esc(c.bio)}</small><small>Xin ${xu(c.ask)}/${st.business?`${Math.round(st.business.period_seconds/60)} phút hoạt động`:'ngày'}</small></div>
      <div class="qy-person-act">${stepper(k,w,st.id)}${btn('Thuê','hire',{id:st.id,cand:c.id,wage:w},'small primary')}</div></li>`;}).join('');
  return `<div class="qy-part"><p class="bk-hint">${esc(P.name||'Quầy')} có ${P.slots||1} chỗ đứng cho nhân viên (Xe đẩy 1, Sạp chợ 2, Ki-ốt 3). Số quầy bạn mở thì không giới hạn.</p>${rows?`<ul class="qy-list">${rows}</ul>`:''}
    ${cands?`<h4>Đang tìm việc ${helpBtn('cand')}</h4>${helpText('cand','Tự đặt lương. Trả cao thì vui, bán đắt hàng hơn. Dưới 60% mức xin là họ không nhận.')}${hireAllRow(st,P)}<ul class="qy-list">${cands}</ul>`:''}
    ${!rows&&!cands?'<p class="bk-hint">Chưa có ai.</p>':''}${hirePart(st)}</div>`;
}
/* 👥 Thuê đủ chỗ (F#290): two or more free places and people to fill them, each at the wage on their row. */
const rowWage=st=>c=>S.wage[`c:${st.id}:${c.id}`]??c.ask;
function hireAllRow(st,P){
  const plan=hireAllPlan(st.cands,st.staff.length,P.slots||1,rowWage(st));
  if(plan.length<2)return '';
  return `<div class="bk-actions qy-all">${btn(`👥 Thuê tất cả · ${plan.length} người`,'hireAll',{id:st.id},'primary')}</div>`;
}
function stockPart(st){
  const cat=CAT();
  if(st.business){const b=st.business,rows=b.stock||[],draft=S.stockDraft[st.id]||{},quote=restockQuote(draft,rows);
    // F#232: staff sell only the board. A stocked dish that is off it says so, with a one-tap fix (older counters kept
    // their three-dish default board; restocking a dish now turns it on by itself).
    const on=st.menu?.on,off=on?rows.filter(row=>row.qty>0&&!on.includes(row.id)).map(row=>row.id):[];
    const offAll=off.length>1?`<p class="bk-alert warn qy-off-menu">${off.length} món có hàng chưa bật ở Menu. ${btn('Bật tất cả món có hàng','menuon',{id:st.id,k:off.join(',')},'small primary')}</p>`:'';
    return `<div class="qy-part"><h4>Kho nguyên liệu · ${fmt(b.stock_total)} phần</h4>${why('stock',`Nhập đúng số phần bạn muốn bán. Tiền lấy từ két/vốn quầy; giữ lại tiền lương để nhân viên tiếp tục làm. Nhân viên chỉ bán món đã bật ở Menu.`)}${offAll}<ul class="qy-list">${rows.map(row=>{const dish=dishOf(st,row.id),isOff=off.includes(row.id);return `<li class="qy-stock-item" data-qk="stock:${st.id}:${row.id}"><span><b>${dish.emoji} ${esc(dish.name)}</b><small>Còn ${fmt(row.qty)} · ${xu(row.cost)} / phần</small>${isOff?`<small class="qy-off-tag">Chưa bật ở Menu ${btn('Bật','menuon',{id:st.id,k:row.id},'small ghost')}</small>`:''}${'keep' in row&&(st.staff.length||row.keep)?keepStepper(row.keep,q=>`data-qy="keep"${attrs({id:st.id,k:row.id,n:q})}${S.busy?' disabled':''}`,dish.name):''}</span><label><span>Nhập thêm</span>${qtyBox({value:draft[row.id]??'',min:0,max:20000,label:`Nhập thêm ${dish.name}`,placeholder:'0',attrs:`name="qy-stock" id="qy-stock-${st.id}-${row.id}" data-id="${st.id}" data-k="${row.id}"`})}</label></li>`;}).join('')}</ul><p class="qy-stock-quote">${quote?`${fmt(quote.count)} phần · tổng ${xu(quote.total)}`:'Nhập số lượng để xem tổng tiền'}<small>Két + vốn hiện có: ${xu(st.till+st.fund)}</small></p><div class="bk-actions">${btn(quote?`Nhập hàng · ${xu(quote.total)}`:'Nhập hàng','restock',{id:st.id},'primary',!quote?'Nhập số lượng trước':quote.total>st.till+st.fund?'Két và vốn chưa đủ':'')}${btn('Xem tiệm','visit',{id:st.id},'ghost')}</div></div>`;
  }
  return `<div class="qy-part"><p class="qy-line">Hôm nay ${cat.weather[st.today?.w]||''} · ${cat.pace[st.today?.pace]||''} · khoảng ${fmt(st.today?.n)} khách ${helpBtn('stock')}</p>
    ${helpText('stock','Ít: không lo ế. Nhiều: không lo hết hàng. Hàng tươi (hoa, bánh) ế thì hư.')}
    <div class="segmented qy-order" role="radiogroup" aria-label="Nhập hàng">${cat.orders.map(o=>`<button type="button" role="radio" aria-checked="${st.order===o.id}" class="${st.order===o.id?'active':''}" data-qy="order" data-id="${st.id}" data-level="${o.id}"${S.busy?' disabled':''}>${esc(o.name)}</button>`).join('')}</div>
    ${st.hist.length?`<ol class="qy-days">${st.hist.slice().reverse().map(h=>`<li><span>Ngày ${fmt(h[0])}</span><span>${fmt(h[1])} khách</span><b class="${h[2]>=0?'up':'down'}">${h[2]>=0?'+':'−'}${xu(Math.abs(h[2]))}</b></li>`).join('')}</ol>`:''}</div>`;
}
function fundPart(st){
  return `<div class="qy-part"><p class="qy-line">Vốn quầy <b>${xu(st.fund)}</b> ${helpBtn('fund')}</p>
    ${helpText('fund','Tiền hàng, lương, điện, phí online, thuê chỗ, vật tư, bảo vệ và thuế lấy từ két trước, thiếu mới lấy vốn quầy. Góp vốn dùng ví trước, thiếu mới lấy tài khoản ngân hàng; không dùng thẻ tín dụng. Xem từng khoản trong Sổ quầy & an toàn. Chi phí chưa trả hiện trên thẻ quầy và tạm dừng quầy; chủ chọn Đóng tiền để trả.')}
    ${helpText('fund','Muốn góp vốn bằng quỹ chung: rút từ quỹ chung về ví ở Ngân hàng, rồi Góp vào vốn quầy.')}
    <div class="qy-fund"><label class="bk-field"><span>Số xu</span>${qtyBox({value:50,min:1,max:1e9,label:'Số xu',attrs:`id="qy-fund-${st.id}"`})}</label>
      ${btn('Góp vào','fund',{id:st.id,sign:'+'},'primary')}${btn('Rút ra','fund',{id:st.id,sign:'-'},'ghost')}</div>
    <div class="bk-actions">${btn('Két vào vốn','till',{id:st.id,to:'fund'},'ghost',st.till?'':'Két đang trống')}${btn(`Sang nhượng · ${xu(st.sell)}`,'sell',{id:st.id},'danger')}</div></div>`;
}
function upPart(st){
  const items=CAT().items.map(it=>{const have=st.items.includes(it.id);
    return `<li class="qy-up${have?' on':''}"><span class="qy-up-emoji" aria-hidden="true">${it.emoji}</span><div class="grow"><b>${esc(it.name)}</b><small>${esc(it.line)}</small></div>
      ${have?'<span class="qy-have">✓</span>':btn(xu(it.price[st.place]),'buy',{id:st.id,item:it.id},'small')}</li>`;}).join('');
  return `<div class="qy-part">${theftRiskHTML(st)}${buyAllRow(st)}<ul class="qy-list">${items}</ul></div>`;
}
/* 🛠️ Lắp tất cả (F#290): only with two or more items left; the total is what the money there pays, cheapest first. */
function buyAllRow(st){
  const plan=buyAllPlan(CAT()?.items,st.items,st.place,quayHave(J()));
  if(plan.todo.length<2)return '';
  const all=plan.fit.length===plan.todo.length;
  const label=all?`🛠️ Lắp tất cả · tổng ${xu(plan.total)}`:plan.fit.length?`🛠️ Lắp ${plan.fit.length}/${plan.todo.length} món · ${xu(plan.fitTotal)}`:`🛠️ Lắp tất cả · tổng ${xu(plan.total)}`;
  return `<div class="bk-actions qy-all">${btn(label,'buyAll',{id:st.id},'primary',plan.fit.length?'':`Cần ${xu(plan.todo[0].price)} cho món rẻ nhất`)}</div>`;
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

/* ======================================================================== 🧑‍🍳 tự tay (game/quay_self.py) */
const dishes=st=>CAT()?.menus?.[st.trade]||[];
const dishOf=(st,k)=>dishes(st).find(d=>d.id===k)||{id:k,emoji:'•',name:k,base:1,band:[1,1]};
const clone=o=>JSON.parse(JSON.stringify(o));
const menuDraft=st=>S.md[st.id]??=cloneMenu(st.menu);
const lookDraft=st=>S.lk[st.id]??={...clone(st.look),name:st.name};
const sameMenu=(a,b)=>JSON.stringify([[...a.on].sort(),[...a.on].sort().map(k=>a.p[k])])===JSON.stringify([[...b.on].sort(),[...b.on].sort().map(k=>b.p[k])]);
/** Customers' feeling about a board: the average dish against the trade's usual price (its first three dishes). */
function feel(st,m){
  const ds=dishes(st),ref=ds.slice(0,3).reduce((a,d)=>a+d.base,0)/3,avg=m.on.reduce((a,k)=>a+(m.p[k]??dishOf(st,k).base),0)/Math.max(1,m.on.length);
  const pct=100*avg/ref;
  return pct<=90?['cheap','Giá mềm: khách thích 😊']:pct>=115?['dear','Hơi đắt: khách sẽ ít hơn']:['fair','Giá vừa phải 👍'];
}
const stars=v=>v?`⭐ ${(v/10).toFixed(1)}`:'';

function selfRow(st){
 const r=st.run,rate=st.rate||[0,0],on=!!st.online;
 const label=r&&!r.x?'🧑‍🍳 Tiếp tục tự đứng quầy':'🧑‍🍳 Tự đứng quầy';
 return `<div class="qy-self">${st.staff.length?btn('🏪 Vào xem tiệm','visit',{id:st.id},'primary'):''}${btn(label,r&&!r.x?'runopen':'runstart',{id:st.id},st.staff.length?'ghost':'primary',st.due?'Đóng chi phí còn thiếu trước nhé':st.business?.paused&&(!r||r.x)?'Mở quầy để bắt đầu nhận khách':'')}<button type="button" class="qy-switch${on?' on':''}" role="switch" aria-checked="${on}" data-qy="online" data-id="${st.id}"${S.busy?' disabled':''}><span class="qy-knob" aria-hidden="true"></span>📱 Bán online${on&&rate[0]?` <small>${stars(rate[1])} · ${rate[0]}</small>`:''}</button></div>`;
}
/** #19: what the staffed counter makes an hour (market now) and a day (24 h), from quay_business.income. */
function quayIncome(b){
 const i=b.income;if(!i||!i.hour||!i.day)return '';
 const sign=n=>`${n>=0?'+':'−'}${xu(Math.abs(n))}`,cls=n=>n<0?'loss':'';
 const h=i.stock_hours,left=h==null?'':h>=24?' Hàng còn đủ bán hơn 1 ngày.':` Hàng còn đủ bán khoảng ${h<1?`${Math.max(1,Math.round(h*60))} phút`:`${fmt(h)} giờ`}.`;
 return `<div class="qy-income" data-testid="qy-income"><div><small>Lãi 1 giờ · chợ ${esc(i.market||'')}</small><strong class="${cls(i.hour.net)}">≈ ${sign(i.hour.net)}</strong><small>${fmt(Math.round(i.hour.sold))} món · thu ${xu(i.hour.revenue)}</small></div><div><small>Lãi 1 ngày (24 giờ)</small><strong class="${cls(i.day.net)}">≈ ${sign(i.day.net)}</strong><small>nếu đủ hàng, đủ vốn</small></div><p>Ước tính theo menu, giá, nhân viên, chợ lúc này${b.status==='running'?'':' (khi quầy bán lại)'}; đã trừ hàng, lương, điện, thuế, cộng thưởng.${left}</p></div>`;
}
function businessPanel(st,detail=false){
 const b=st.business;if(!b)return '';
 const label={running:'Nhân viên đang bán',paused:'Quầy đang tạm dừng',no_staff:'Chờ bạn tự đứng quầy',out_of_stock:b.kept?.length?'🔒 Đang giữ hàng cho bạn':'Đã hết nguyên liệu',no_funds:'Thiếu tiền vận hành'}[b.status]||'Đang cập nhật quầy';
 const recent=(b.recent||[]).slice(-5).reverse(),expense=b.expenses||{};
 const controls=businessControls(st,btn)+staffLifeCard(st.staff_life,(label,e,ch)=>btn(label,'staffEvent',{id:st.id,event:e.id,choice:ch.id},'shop-event-choice',ch.affordable===false?'Két/vốn chưa đủ':''));
 return `<section class="qy-business" data-qk="business:${st.id}"><div class="qy-business-heading"><span class="qy-business-dot ${b.status==='running'?'running':''}" aria-hidden="true"></span><b>${label}</b></div><p>${esc(b.reason||'')}</p>${controls}<div class="qy-business-numbers"><div><small>Nguyên liệu còn</small><strong>${fmt(b.stock_total)} phần</strong></div><div><small>Đã bán</small><strong>${fmt(b.sold)} món</strong></div><div><small>Lãi đã ghi sổ</small><strong class="${b.net<0?'loss':''}">${xu(b.net)}</strong></div></div>${quayIncome(b)}<p class="qy-business-note">Lãi sau chi phí được thưởng thêm: nhân viên bán ${Number(b.staff_bonus_percent??40)}%, bạn tự bán ${Number(b.bonus_percent??40)}%. Đã cộng: ${xu(b.profit_bonus||0)}. ${Number(b.speed_factor||1)>1?`Thiết bị ×${Number(b.speed_factor).toFixed(2)} · Nhân viên xử lý đơn nhanh hơn. `:''}Lương ${xu(b.wage)} / ${Math.round((b.period_seconds||600)/60)} phút hoạt động · ${st.staff.length?'Nhân viên tiếp tục bán khi bạn rời game, tới khi hết hàng hoặc hết tiền.':'Quầy chỉ bán khi bạn tự phục vụ hoặc giao hàng.'}</p>${b.unpaid_fines?`<p class="bk-alert warn">Còn ${xu(b.unpaid_fines)} tiền phạt chưa trả, đã tính vào lãi. Khoản này sẽ trừ từ tiền bán hàng hoặc vốn bổ sung của quầy.</p>`:''}${S.syncFailed?'<p class="qy-sync-error" role="status">Chưa kết nối được để cập nhật. Số liệu đang giữ là lần xác nhận gần nhất.</p>':''}${detail?`<details class="qy-ledger"><summary>Doanh thu ${xu(b.revenue)} · xem chi phí</summary><dl>${[['Nguyên liệu','goods'],['Lương','wages'],['Thuê chỗ','rent'],['Điện','power'],['Online / giao hàng','online'],['Thuế kỳ cũ','tax'],['Thuế thu nhập','income_tax'],['Phí môi trường','environment'],['Bảo vệ quầy','protection'],['Thiệt hại','loss']].map(([label,key])=>`<div><dt>${label}</dt><dd>${xu(expense[key])}</dd></div>`).join('')}</dl></details><h4>Vừa bán tại quầy</h4>${recent.length?`<ul class="qy-recent">${recent.map(event=>`<li data-qk="sale:${esc(event.id)}"><span>${dishOf(st,event.dish).emoji} ${esc(dishOf(st,event.dish).name)} ×${fmt(event.qty)}<small>${event.channel==='online'?'Đơn online':'Khách tại quầy'}${event.stars?` · ${event.stars}/5 sao`:''}${event.name?` · ${esc(event.name)}`:''}</small>${event.text?`<small>${esc(event.text)}</small>`:''}</span><b>${xu(event.total)}</b></li>`).join('')}</ul>`:'<p class="bk-hint">Chưa có lượt bán được ghi nhận. Sổ sẽ cập nhật khi nhân viên bán được hàng.</p>'}`:''}</section>`;
}
function visitorQueue(st){const rows=(st.business?.visitor_orders||[]).filter(o=>o.status==='queued');return rows.length?`<section class="qy-part"><h4>Khách người chơi · ${rows.length}</h4>${rows.map(o=>`<div class="row"><span style="width:44px;flex:none">${avInner({fc:o.buyer?.fc,av:'🙂'})}</span><div class="grow"><b>${esc(o.buyer?.name||'Khách')}</b><small class="muted block">${esc(dishOf(st,o.dish).name)} · ${o.staffed?'Nhân viên đang phục vụ':'Đã thanh toán'}</small></div>${o.staffed?'':btn('Phục vụ','visitor',{id:st.id,key:o.id},'primary small')}</div>`).join('')}</section>`:'';}
function focusVisitorRoom(st){if(S.focusedVisitorPlace===st.id)return;S.focusedVisitorPlace=st.id;import('./workplace-visit.js').then(m=>m.workVisitsOwnerFocus(S.env,{kind:'quay',target:st.id,host:S.dlg})).catch(()=>{});}
function visitorPanel(st){focusVisitorRoom(st);const o=(st.business?.visitor_orders||[]).find(o=>String(o.id)===String(S.visitor));if(!o||o.status!=='queued')return `<section class="bk-card">${flash()}<h3>Đơn khách đã được cập nhật</h3>${btn('Về quầy','back',{},'primary')}</section>`;const d=S.visitorDraft[S.visitor]??={items:[],step:'pick'};return `<section class="bk-card">${flash()}<div class="row"><span style="width:64px;flex:none">${avInner({fc:o.buyer?.fc,av:'🙂'})}</span><div><h3>${esc(o.buyer?.name||'Khách')} đang làm khách</h3><p>${esc(dishOf(st,o.dish).name)} · Đã trả ${xu(o.price)}</p></div></div>${o.note?`<p class="qy-order-note">${esc(o.note)}</p>`:''}${o.staffed?'<p>Nhân viên đang thực hiện đơn này.</p>':d.step==='pick'?`<h4>Chọn món vào khay</h4><div class="qy-tiles">${dishes(st).map(item=>`<button type="button" class="qy-tile-btn ${d.items.includes(item.id)?'on':''}" data-qy="vtray" data-id="${st.id}" data-k="${esc(item.id)}" aria-pressed="${d.items.includes(item.id)}"><span>${item.emoji}</span><b>${esc(item.name)}</b></button>`).join('')}</div><p>Khay: ${d.items.map(id=>esc(dishOf(st,id).name)).join(', ')||'Chưa có món'}</p>${btn('Kiểm khay & bàn giao','vcheck',{id:st.id},'primary',!d.items.length?'Chọn món trước':'')}`:`<p>✓ Đúng món · khách đã trả tiền, không cần thối lại.</p>${btn('😊 Giao món & cảm ơn','vserve',{id:st.id},'primary')}`}${btn('Về quầy','back',{},'ghost')}</section>`;}
function visitView(st){focusVisitorRoom(st);
 return `<section class="bk-card qy-visit"><div class="qy-visit-title"><span>SAU QUẦY · ${esc(st.name)}</span><small>Khách và số liệu từ sổ bán hàng</small></div><canvas class="qy-scene qy-scene-first" data-qy-live data-cv="${st.id}" role="img" aria-label="Góc nhìn sau quầy ${esc(st.name)}"></canvas>${counterActivityHTML(st,esc)}${flash()}${businessPanel(st,true)}<div class="bk-actions">${btn('📦 Nhập thêm hàng','visitstock',{id:st.id},'primary')}${btn('Tự đứng quầy',st.run&&!st.run.x?'runopen':'runstart',{id:st.id},'ghost')}${btn('Quản lý tiệm','back',{},'ghost')}</div></section>`;
}
function menuPart(st){
 const m=menuDraft(st),ds=dishes(st),changed=!sameMenu(m,st.menu),query=S.search[st.id]||'',payload=menuPayload(m,ds);
 const rows=filterDishes(ds,query).map(d=>{const on=m.on.includes(d.id),p=m.p[d.id]??d.base,preview=pricePreview(p,d.cost,d.base);
 return `<li class="qy-dish${on?' on':''}" data-qk="dish:${st.id}:${d.id}"><button type="button" class="qy-dish-pick" data-qy="dish" data-id="${st.id}" data-k="${d.id}" aria-pressed="${on}"><span class="qy-up-emoji" aria-hidden="true">${d.emoji}</span><span class="grow"><b>${esc(d.name)}</b><small>Nguyên liệu ${xu(d.cost)} · tham khảo ${xu(d.base)}</small></span><span class="qy-check" aria-hidden="true">${on?'✓':'＋'}</span></button>${on?`<label class="qy-price-field"><span>Giá bán (xu)</span><input id="qy-price-${st.id}-${d.id}" name="qy-price" data-id="${st.id}" data-k="${d.id}" type="number" inputmode="numeric" min="1" max="1000000" step="1" value="${esc(p)}" aria-invalid="${!preview.valid}"/></label><div class="qy-price-feedback ${preview.kind||'loss'}">${preview.valid?`Chênh lệch sau nguyên liệu: <b>${xu(preview.margin)}</b>. `:''}${preview.label}</div>`:''}</li>`;}).join('');
 return `<div class="qy-part"><p class="qy-line">Đang chọn ${m.on.length}/${ds.length} món. Bạn có thể chọn toàn bộ danh mục.</p><div class="qy-menu-tools"><label class="bk-field"><span>Tìm món</span><input type="search" id="qy-search-${st.id}" name="qy-search" data-id="${st.id}" value="${esc(query)}" placeholder="Tên món…"/></label>${btn('Chọn tất cả','dishall',{id:st.id},'small ghost')}</div><ul class="qy-list">${rows||'<li class="bk-hint">Không có món trùng từ tìm kiếm.</li>'}</ul><p class="qy-menu-disclaimer">Chênh lệch trên chưa trừ lương, thuê chỗ, điện, thuế và phí giao hàng. Phản ứng giá là gợi ý; lượng bán và đánh giá thật được ghi trong sổ quầy.</p><div class="bk-actions">${btn('Lưu menu & giá','menusave',{id:st.id},'primary',!payload?'Kiểm tra giá và chọn ít nhất một món':!changed?'Chưa đổi gì':'')}${changed?btn('Hoàn tác','menureset',{id:st.id},'ghost'):''}</div></div>`;
}

function lookPart(st){
  const lk=lookDraft(st),cat=CAT(),[most,each]=cat.tables[st.place]||[0,0],max=cat.decor_max||3;
  const changed=lk.c!==st.look.c||lk.t!==st.look.t||(lk.name||'').trim()!==st.name||JSON.stringify([...lk.d].sort())!==JSON.stringify([...st.look.d].sort());
  const cost=Math.max(0,lk.t-st.look.t)*each;
  const sw=cat.colors.map(([id,hex,name],i)=>`<button type="button" class="qy-sw${lk.c===i?' on':''}" data-qy="color" data-id="${st.id}" data-k="${i}" style="--sw:${hex}" aria-pressed="${lk.c===i}" aria-label="${esc(name)}" title="${esc(name)}"></button>`).join('');
  const deco=cat.decor.map(([id,emo,name])=>{const on=lk.d.includes(id);
    return `<button type="button" class="qy-chip${on?' on':''}" data-qy="decor" data-id="${st.id}" data-k="${id}" aria-pressed="${on}"${!on&&lk.d.length>=max?' disabled':''}>${emo} ${esc(name)}</button>`;}).join('');
  return `<div class="qy-part">
    <label class="bk-field"><span>Tên trên bảng hiệu</span><input name="qy-sign" data-id="${st.id}" maxlength="24" value="${esc(lk.name??st.name)}"></label>
    <h4>Màu mái che</h4><div class="qy-swatches">${sw}</div>
    <h4>Trang trí <small class="qy-muted">(tối đa ${max}, miễn phí)</small></h4><div class="qy-chips">${deco}</div>
    ${most?`<div class="qy-person"><div class="grow"><b>🪑 Bàn ghế</b><small>${xu(each)} một bộ · thêm khách ngồi lại</small></div>
      <div class="qy-person-act"><span class="qy-step">${btn('−','tables',{id:st.id,by:-1},'small ghost',lk.t<=0?'Hết rồi':'')}${qtyBox({value:lk.t,min:0,max:most,label:'Số bộ bàn ghế',live:true,go:`data-qy="tables"${attrs({id:st.id,set:QTY})}`})}<small>/${most}</small>${btn('＋','tables',{id:st.id,by:1},'small ghost',lk.t>=most?'Đủ chỗ rồi':'')}</span></div></div>`:''}
    <div class="bk-actions">${btn(cost?`Lưu · ${xu(cost)}`:'Lưu','looksave',{id:st.id},'primary',changed?'':'Chưa đổi gì')}${changed?btn('Hoàn tác','lookreset',{id:st.id},'ghost'):''}</div></div>`;
}

/* ---- the day at the counter ---- */
const R=()=>S.run;
const freshRun=sid=>({sid,step:'pick',tray:[],change:0,phone:false,pack:null,hint:''});
function runView(st){focusVisitorRoom(st);
  const r=st.run;
  if(!r)return `<section class="bk-card bk-center qy-owner-opening">${flash()}<h3>${S.busy?'Đang vào quầy của bạn…':'Chưa vào được quầy'}</h3><p>${S.busy?'Đang lấy menu và đơn khách. Bạn có thể tự bán ở đây khi muốn.':'Bạn có thể thử mở lại hoặc về quản lý quầy để kiểm tra hàng và chi phí.'}</p><div class="bk-actions center">${btn(S.busy?'Đang mở quầy…':'🧑‍🍳 Thử đứng quầy lại','runstart',{id:st.id},'primary')}${btn('Về quầy','back',{},'ghost')}</div></section>`;
  const waiting=(r.orders||[]).filter(o=>!o.stars).length;
  const bar=`<div class="qy-runbar"><span title="Khách đã phục vụ">🧍 ${r.i} khách</span><span title="Doanh thu đã bán">💰 ${xu(r.rv)}</span>${r.stars?`<span>${stars(r.stars)}</span>`:''}
    ${r.crowd?.length>1?`<span title="Khách chờ tới lượt">${r.crowd.length-1} chờ</span>`:''}
    ${st.online&&!r.x?`<button type="button" class="qy-phone-btn${R().phone?' on':''}" data-qy="phone" data-id="${st.id}" aria-pressed="${R().phone}" aria-label="Đơn online">📱${waiting?`<i>${waiting}</i>`:''}</button>`:''}
    ${r.x?'':btn('Rời quầy','runclose',{id:st.id},'small ghost')}</div>`;
  let panel;
  if(r.x)panel=summary(st,r);
  else if(R().pack)panel=packPanel(st,r);
  else if(R().phone)panel=phonePanel(st,r);
  else if(r.ev)panel=eventCard(st,r.ev);
  else if(r.cust)panel=customerPanel(st,r.cust);
  else panel=`<section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">${r.out?'📦':'☕'}</div><h3>${r.out?'Cần nhập thêm nguyên liệu':'Bạn đã đứng quầy'}</h3>
    <p>${esc(r.out?'Nhập thêm món trong menu để phục vụ khách.':ownerArrivalText(r,st.business))}</p>${waiting?`<p>Còn ${waiting} đơn online chờ giao.</p>`:''}<div class="bk-actions center">${waiting?btn('📱 Xem đơn','phone',{id:st.id},'ghost'):''}${r.out?btn('Nhập hàng','visitstock',{id:st.id},'primary'):''}${btn('Rời quầy','runclose',{id:st.id},'ghost')}</div></section>`;
  return `<section class="bk-card qy-run" data-qk="run:${st.id}">${bar}${flash()}</section>${ownerEvents(st)}${panel}
    <canvas class="qy-scene qy-scene-first" data-qy-live data-cv="${st.id}" role="img" aria-label="${esc(`Góc nhìn của bạn sau quầy ${st.name}`)}"></canvas>${!r.x?ownerQueueHTML(r,esc):''}`;
}
function trayChips(st,list,op){
  if(!list.length)return '<p class="qy-muted">Chạm món bên dưới để bỏ vào.</p>';
  return `<div class="qy-chips">${list.map((k,i)=>`<button type="button" class="qy-chip on" data-qy="${op}" data-id="${st.id}" data-k="${i}" aria-label="${esc(`Bỏ ${dishOf(st,k).name} ra`)}">${dishOf(st,k).emoji} ${esc(dishOf(st,k).name)} ✕</button>`).join('')}</div>`;
}
function dishTiles(st,op){
  return `<div class="qy-tiles">${st.menu.on.map(k=>{const d=dishOf(st,k);return `<button type="button" class="qy-tile-btn" data-qy="${op}" data-id="${st.id}" data-k="${k}"${S.busy?' disabled':''}>
    <span aria-hidden="true">${d.emoji}</span><b>${esc(d.name)}</b><small>${xu(st.menu.p[k])}</small></button>`;}).join('')}</div>`;
}
function customerPanel(st,c){
  const u=R();
  let body;
  if(u.step==='pick')body=`<h4>Khay</h4>${trayChips(st,u.tray,'untray')}${u.hint?`<p class="qy-hint-say">${esc(u.hint)}</p>`:''}${dishTiles(st,'tray')}
    <div class="bk-actions">${btn('💵 Tính tiền','charge',{id:st.id},'primary',u.tray.length?'':'Chọn món trước')}</div>`;
  else if(u.step==='pay'){
    const due=c.pay-c.total,coins=(CAT().coins||[1,2,5,10,20,50,100]).filter(v=>v<=Math.max(5,c.pay));
    body=`<p class="qy-bill">Tổng <b>${xu(c.total)}</b> · Khách đưa <b>${xu(c.pay)}</b></p>
      ${due?`<p class="qy-bill">Bạn thối: <b class="qy-change">${xu(u.change)}</b> ${u.change?btn('↺','coinreset',{id:st.id},'small ghost'):''}</p>
      <div class="qy-coins">${coins.map(v=>`<button type="button" class="qy-coin" data-qy="coin" data-id="${st.id}" data-k="${v}">${fmt(v)}</button>`).join('')}</div>`
      :'<p class="qy-bill">Khách đưa vừa đủ 👍</p>'}
      <div class="bk-actions">${btn(due?'🤲 Trả tiền thối':'🤲 Nhận tiền','paid',{id:st.id},'primary')}</div>`;
  }else body=`<p class="qy-bill">Đưa món cho khách và…</p><div class="bk-actions">${btn('😊 Cảm ơn, hẹn gặp lại!','serve',{id:st.id,k:1},'primary')}${btn('Xong','serve',{id:st.id,k:0},'ghost')}</div>`;
  return `<section class="bk-card qy-cust"><div class="qy-say"><b>${esc(c.name)}</b>${c.temperament?`<span class="qy-customer-temper ${esc(c.mood||'calm')}">${c.mood==='angry'?'😤 Đang giục lớn':c.mood==='impatient'?'😠 Sốt ruột':c.temperament==='relaxed'?'🙂 Dễ tính':'😐 Khó tính'}</span>`:''}<p>“${esc(c.say)}”</p>${c.mood&&c.mood!=='calm'?`<p class="qy-customer-call" aria-live="polite">${esc(c.speech)}</p>`:''}</div>${body}</section>`;
}
function eventCard(st,ev){
  return `<section class="bk-card qy-event"><div class="qy-top"><span class="qy-tile" aria-hidden="true">${ev.emoji}</span><div class="grow"><h3>${esc(ev.title)}</h3><p class="qy-line">${esc(ev.text)}</p></div></div>
    <div class="qy-picks">${ev.picks.map(([k,label])=>btn(esc(label),'pick',{id:st.id,k},'ghost')).join('')}</div></section>`;
}
const itemsLine=(st,items)=>{const n={};for(const k of items)n[k]=(n[k]||0)+1;return Object.entries(n).map(([k,c])=>`${dishOf(st,k).emoji} ${esc(dishOf(st,k).name)}${c>1?` ×${c}`:''}`).join(' · ');};
function phonePanel(st,r){
  const list=(r.orders||[]).map(o=>`<article class="qy-order${o.stars?' done':''}" data-qk="o:${o.j}">
      <header><b>#${o.j+1} ${esc(o.name)}</b><span class="qy-tag">${o.cod?'💵 Trả khi nhận':'✅ Đã trả qua app'}</span></header>
      <p>${itemsLine(st,o.items)}</p>${o.note?`<p class="qy-note">📝 ${esc(o.note)}</p>`:''}
      <small>📍 ${esc(o.addr)} · ${xu(o.total)}</small>
      ${o.stars?`<p class="qy-done">Đã giao · ${'⭐'.repeat(o.stars)}</p>`:`<div class="bk-actions">${btn('📦 Đóng gói','pack',{id:st.id,j:o.j},'primary small',r.out?'Hết hàng':'')}</div>`}</article>`).join('');
  return `<section class="bk-card qy-phone"><div class="qy-phone-top"><b>📱 Đơn online</b><span>${stars((st.rate||[])[1])}</span></div>
    ${list||'<p class="qy-muted">Chưa có đơn. Đơn tới trong lúc bạn bán hàng.</p>'}
    <div class="bk-actions">${btn('← Về quầy','phone',{id:st.id},'ghost')}</div></section>`;
}
function packPanel(st,r){
  const u=R(),pk=u.pack,o=(r.orders||[]).find(x=>x.j===pk.j);
  if(!o)return '';
  const T=CAT().tools?.[st.trade]||['🥤','Dụng cụ'],fee=Math.max(2,Math.round(o.total*(CAT().online?.ship||12)/100));
  const tog=(k,label)=>`<button type="button" class="qy-chip${pk[k]?' on':''}" data-qy="ptog" data-id="${st.id}" data-k="${k}" aria-pressed="${!!pk[k]}">${label}</button>`;
  let body;
  if(pk.step==='pack')body=`<h4>Túi hàng</h4>${trayChips(st,pk.bag,'unbag')}${dishTiles(st,'bag')}
    <h4>Đóng gói ${helpBtn('pack')}</h4>${helpText('pack','Đồ ăn uống cần dụng cụ, trừ khi khách dặn không lấy. Có lời dặn thì dán ghi chú lên túi.')}
    <div class="qy-chips">${tog('seal','🔒 Dán kín')}${tog('tool',`${T[0]} ${esc(T[1])}`)}${tog('note','📝 Dán ghi chú')}</div>
    <div class="bk-actions">${btn('Xong, đi giao','packdone',{id:st.id},'primary',pk.bag.length?'':'Bỏ món vào túi trước')}${btn('Để sau','unpack',{id:st.id},'ghost')}</div>`;
  else if(pk.step==='way')body=`<p class="qy-line">Giao bằng gì?</p><div class="qy-picks">${btn('🛵 Tự chạy đi giao','way',{id:st.id,k:'self'},'primary')}${btn(`📦 Gọi shipper · ${xu(fee)}`,'way',{id:st.id,k:'ship'},'ghost')}</div>`;
  else{const left=3-pk.picks.length;
    body=`<p class="qy-line">${left?`Nhìn biển chỉ đường phía trước. Ngã tư thứ ${pk.picks.length+1}:`:'Tới nơi rồi!'}</p>${Number(o.drive_factor||st.run?.drive_factor||1)>1?`<p class="bk-hint">Trang bị giao hàng ×${Number(o.drive_factor||st.run?.drive_factor).toFixed(2)} · Chuẩn bị chuyến tiếp theo nhanh hơn.</p>`:''}${rideSVG(o.route,pk.picks)}${left?signalHTML(pk.signal||o.ride?.traffic):''}${o.ride?.traffic?.receipts?.some(r=>r.fine)?`<p class="notice">🚦 Phạt giao thông: ${o.ride.traffic.receipts.reduce((n,r)=>n+r.fine,0)} xu · đã ghi vào chi phí quầy. Biên nhận lưu trong sổ quầy.</p>`:''}
      ${left?`<div class="qy-turns">${turnChoices(pk.picks).map(c=>btn(`${c.emoji} ${c.label}`,'turn',{id:st.id,k:c.k},'ghost')).join('')}</div>`
        :`<div class="bk-actions">${btn('🤝 Giao tận tay','deliver',{id:st.id},'primary')}</div>`}`;}
  return `<section class="bk-card qy-pack"><div class="qy-say"><b>#${o.j+1} ${esc(o.name)} · ${esc(o.addr)}</b><p>${itemsLine(st,o.items)}</p>${o.note?`<p class="qy-note">📝 ${esc(o.note)}</p>`:''}</div>${body}</section>`;
}
function summary(st,r){
  const s=r.sum||{};
  return `<section class="bk-card bk-center qy-sum"><div class="bk-big-emoji" aria-hidden="true">🏁</div><h3>Đóng ca rồi!</h3>
    <ul class="qy-sumlist"><li><span>Khách bạn phục vụ</span><b>${fmt(s.hand)}</b></li>${s.on?`<li><span>Đơn online</span><b>${fmt(s.on)}</b></li>`:''}
      <li><span>Khách trong lượt này</span><b>${fmt(s.n)}</b></li><li><span>Doanh thu</span><b>${xu(s.rev)}</b></li>
      <li><span>Lời</span><b class="${s.net>=0?'up':'down'}">${s.net>=0?'+':'−'}${xu(Math.abs(s.net||0))}</b></li>${s.st?`<li><span>Khách chấm</span><b>${stars(s.st)}</b></li>`:''}</ul>
    <p class="qy-muted">Tiền đã vào két. Bạn có thể mở lượt phục vụ tiếp khi sẵn sàng.</p><div class="bk-actions center">${btn('Về quầy','back',{},'primary')}</div></section>`;
}

/** The 🧑‍🍳 taps. Returns true when it was one. */
function onSelf(op,data){
  const st=stallOf(data.id);
  const u=R();
  switch(op){
    case'visitor':S.visitor=data.key;S.visit=data.id;S.view='visitor';render();toTop();return true;
    case'vtray':{const d=S.visitorDraft[S.visitor]??={items:[],step:'pick'};d.items=[data.k];render();return true;}
    case'vcheck':{const o=st?.business?.visitor_orders?.find(o=>String(o.id)===String(S.visitor)),d=S.visitorDraft[S.visitor];if(visitorSelectionValid(o,d?.items)){d.step='thanks';}else S.flash={text:'Chọn đúng món trên phiếu của khách nhé.',kind:'bad'};render();return true;}
    case'vserve':{const o=st?.business?.visitor_orders?.find(o=>String(o.id)===String(S.visitor)),d=S.visitorDraft[S.visitor];if(!visitorSelectionValid(o,d?.items)||d.step!=='thanks')return true;send('jr_quay_serve',{stall:st.id,visitor_id:o.id,items:d.items,change:0,smile:true}).then(r=>{if(r){delete S.visitorDraft[S.visitor];S.view='list';S.visitor=null;render();}});return true;}
    case'visitstock':S.view='list';S.open[data.id]='stock';render();toTop();return true;
    case'dishall':if(st){selectDishes(menuDraft(st),dishes(st));render();}return true;
    case'menuon':{if(!st?.menu)return true;const add=String(data.k||'').split(',').filter(k=>k&&!st.menu.on.includes(k));if(!add.length)return true;   // F#232: turn stocked dishes on, keeping the prices
      if(S.md[st.id]&&sameMenu(S.md[st.id],st.menu))delete S.md[st.id];
      send('jr_quay_menu',{stall:st.id,on:[...st.menu.on,...add]});return true;}
    case'runstart':{
      if(!st)return true;
      S.tab='mine';S.view='run';S.run=freshRun(data.id);S.flash=null;toTop();
      if(st.run&&!st.run.x){render();return true;}
      send('jr_quay_start',{stall:data.id}).then(()=>{render();toTop();});return true;}
    case'runopen':S.tab='mine';S.view='run';S.run=freshRun(data.id);S.flash=null;render();toTop();return true;
    case'online':if(st)send('jr_quay_online',{stall:st.id,on:!st.online});return true;
    case'dish':{if(!st)return true;const m=menuDraft(st),i=m.on.indexOf(data.k);
      if(i>=0){if(m.on.length>1)m.on.splice(i,1);}else m.on.push(data.k);
      render();return true;}
    case'dprice':{if(!st)return true;const m=menuDraft(st),d=dishOf(st,data.k),p=(m.p[data.k]??d.base)+Number(data.by);
      m.p[data.k]=Math.max(d.band[0],Math.min(d.band[1],p));render();return true;}
    case'menureset':delete S.md[data.id];render();return true;
    case'menusave':{if(!st)return true;const m=menuDraft(st),ds=dishes(st);
      const payload=menuPayload(m,ds);if(!payload){S.flash={text:'Giá phải là số nguyên dương, tối đa 1.000.000 xu.',kind:'bad'};render();return true;}
      const submitted=JSON.stringify(payload);send('jr_quay_menu',{stall:st.id,...payload}).then(r=>{if(r&&JSON.stringify(menuPayload(menuDraft(st),ds))===submitted){delete S.md[st.id];render();}});return true;}
    case'color':if(st){lookDraft(st).c=Number(data.k);render();}return true;
    case'decor':{if(!st)return true;const lk=lookDraft(st),i=lk.d.indexOf(data.k);if(i>=0)lk.d.splice(i,1);else if(lk.d.length<(CAT().decor_max||3))lk.d.push(data.k);render();return true;}
    case'tables':{if(!st)return true;const lk=lookDraft(st),most=CAT().tables[st.place]?.[0]||0;lk.t=Math.max(0,Math.min(most,data.set!==undefined?Number(data.set)||0:lk.t+Number(data.by)));render();return true;}
    case'lookreset':delete S.lk[data.id];render();return true;
    case'looksave':{if(!st)return true;const lk=lookDraft(st),each=CAT().tables[st.place]?.[1]||0,cost=Math.max(0,lk.t-st.look.t)*each;
      const name=(lk.name||'').trim()||st.name;
      const go=()=>send('jr_quay_look',{stall:st.id,c:lk.c,d:lk.d,t:lk.t,...(name!==st.name?{name}:{}),...(cost?{confirm:true}:{})}).then(r=>{if(r){delete S.lk[st.id];render();}});
      if(cost)ask('Mua bàn ghế?',`${lk.t-st.look.t} bộ cho ${st.name}.`,`Mua · ${xu(cost)}`,{cost,pocket:['wallet','account']}).then(ok=>{if(ok)go();});else go();
      return true;}
    case'tray':if(u&&u.tray.length<6){u.tray.push(data.k);u.hint='';render();}return true;
    case'untray':if(u){u.tray.splice(Number(data.k),1);u.hint='';render();}return true;
    case'charge':{const c=st?.run?.cust;if(!u||!c)return true;
      if([...u.tray].sort().join()!==[...c.items].sort().join()){u.hint=`${c.name}: “Ủa, mình gọi ${c.items.map(k=>dishOf(st,k).name.toLowerCase()).join(' với ')} mà.”`;render();return true;}
      u.step='pay';u.change=0;u.hint='';render();return true;}
    case'coin':if(u){u.change+=Number(data.k);render();}return true;
    case'coinreset':if(u){u.change=0;render();}return true;
    case'paid':if(u){u.step='thanks';render();}return true;
    case'serve':{if(!u||!st)return true;const c=st.run?.cust,due=c?c.pay-c.total:0;
      send('jr_quay_serve',{stall:st.id,items:u.tray,change:due?u.change:0,smile:data.k==='1'}).then(r=>{if(r){Object.assign(u,{step:'pick',tray:[],change:0,hint:''});render();}});return true;}
    case'pick':send('jr_quay_choose',{stall:data.id,pick:data.k});return true;
    case'phone':if(u){u.phone=!u.phone;u.pack=null;render();toTop();}return true;
    case'pack':if(u){u.pack={j:Number(data.j),orderId:st?.run?.orders?.find(o=>o.j===Number(data.j))?.id,bag:[],seal:false,tool:false,note:false,step:'pack',picks:[]};render();toTop();}return true;
    case'unpack':if(u){u.pack=null;render();}return true;
    case'bag':if(u?.pack&&u.pack.bag.length<6){u.pack.bag.push(data.k);render();}return true;
    case'unbag':if(u?.pack){u.pack.bag.splice(Number(data.k),1);render();}return true;
    case'ptog':if(u?.pack){u.pack[data.k]=!u.pack[data.k];render();}return true;
    case'packdone':if(u?.pack){u.pack.step='way';render();}return true;
    case'way':{if(!u?.pack||!st)return true;
      const o=(st.run?.orders||[]).find(x=>x.j===u.pack.j);
      if(data.k==='ship'){ship(st,u,'ship');return true;}
      if(RIDE.external&&o){Promise.resolve(RIDE.external(o)).then(route=>{if(Array.isArray(route)){u.pack.picks=route.slice(0,3);ship(st,u,'self');}}).catch(()=>{u.pack.step='ride';render();});return true;}
      send('jr_quay_signal',{stall:st.id,order:u.pack.j,order_id:u.pack.orderId}).then(r=>{if(r&&u.pack){u.pack.picks=r.picks||[];u.pack.signal=r.traffic;u.pack.step='ride';render();}});return true;}
    case'turn':if(u?.pack&&u.pack.picks.length<3&&u.pack.signal?.challenge){const pk=u.pack;
      send('jr_quay_cross',{stall:st.id,order:pk.j,order_id:pk.orderId,turn:data.k,token:pk.signal.challenge.token}).then(async r=>{if(!r)return;pk.picks=r.picks;pk.signal=r.traffic;
        if(pk.picks.length<3){const next=await send('jr_quay_signal',{stall:st.id,order:pk.j,order_id:pk.orderId});if(next)pk.signal=next.traffic;}render();});}return true;
    case'deliver':if(u?.pack&&st)ship(st,u,'self');return true;
    case'runclose':{if(!st)return true;const left=st.run&&!st.run.x&&(st.run.cust||st.run.ev);
      const go=()=>send('jr_quay_close',{stall:st.id}).then(r=>{if(r){if(u){u.phone=false;u.pack=null;}if(!stallOf(st.id)?.run){S.view='list';S.run=null;}render();toTop();}});
      if(left)ask('Rời quầy?','Chốt những món bạn đã phục vụ. Nếu có nhân viên, họ tiếp tục vận hành theo hàng và vốn còn lại.','Rời quầy').then(ok=>{if(ok)go();});else go();
      return true;}
  }
  return false;
}
function ship(st,u,way){
  const pk=u.pack;pk.submitting=true;
  send('jr_quay_ship',{stall:st.id,order:pk.j,order_id:pk.orderId,items:pk.bag,seal:pk.seal,tool:pk.tool,note:pk.note,way,...(way==='self'?{route:pk.picks}:{})})
    .then(r=>{pk.submitting=false;if(r){u.pack=null;u.phone=true;}render();});
}

/* ---- the counter's canvas: drawn after each render, only when what it shows changed ---- */
function paintCanvases(){
  if(!S.dlg)return;
  mountSignals(S.dlg);
  const cat=CAT();if(!cat?.menus)return;
  for(const cv of S.dlg.querySelectorAll('canvas[data-cv]')){
    const st=stallOf(cv.dataset.cv);if(!st?.menu)continue;
    const m=S.md[st.id]||st.menu,lk=S.lk[st.id]||{...st.look,name:st.name};
    const inRun=S.view==='run'&&S.run?.sid===st.id,observe=S.view==='visit'&&S.visit===st.id,r=st.run,activity=counterActivity(st);
    const actors=[...activity.current,...activity.completed].map(p=>({...p,emoji:p.dish?dishOf(st,p.dish).emoji:''}));
    const o={place:st.place,name:(lk.name||'').trim()||st.name,color:cat.colors[lk.c]?.[1],decor:lk.d,tables:lk.t,
      menu:m.on.map(k=>{const d=dishOf(st,k);return {emoji:d.emoji,name:d.name,price:m.p[k]??d.base};}),
      me:inRun||!st.staff.length,staff:st.staff.length,actors,online:!!st.online,closed:activity.closed,
      firstPerson:inRun||observe,observe,reason:st.business?.reason||'',orderLabel:inRun?r?.cust?.name||'':'',
      activityLabel:activity.current.length?`${activity.current.length} khách tại quầy`:activity.completed.length?`${activity.completed.length} lượt vừa mua xong`:''};
    const key=JSON.stringify(o)+'|'+cv.clientWidth;
    if(cv._key===key)continue;cv._key=key;
    try{paintCounter(cv,{...o,me:o.me?figure(S.env.api.state):null});}catch(e){console.warn('quay scene',e);}
  }
}
