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
import {paintCounter} from './quay-scene.js';
import {figure} from './look.js';
import {RIDE,rideSVG} from './quay-ride.js';

const S={md:{},lk:{},run:null,anchor:'',anchorAt:0,dlg:null,env:null,view:'list',tab:'mine',pick:null,busy:false,flash:null,listening:false,open:{},help:{},wage:{},hire:null,loading:false,to:{}};
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
    e.preventDefault();S.anchor=selOf(el);S.anchorAt=performance.now();onClick(el.dataset.qy,el.dataset,el);
  });
  d.addEventListener('input',e=>{const t=e.target;if(t.name==='qy-name'&&S.pick)S.pick.name=t.value;
    if(t.name==='qy-sign'){const st=stallOf(t.dataset.id);if(st){lookDraft(st).name=t.value;paintCanvases();}}});
  d.addEventListener('submit',e=>e.preventDefault());
  // the spacer under the page goes away as the player scrolls back up (never while a render is holding the spot)
  d.addEventListener('scroll',()=>{const top=d.scrollTop,up=top<(d._qyTop??top);d._qyTop=top;
    const sp=d.querySelector('.qy-spacer'),h=sp?.offsetHeight||0;if(!h||!up||S.hold)return;
    const spare=d.scrollHeight-(top+d.clientHeight);if(spare>1)sp.style.height=`${Math.max(0,h-spare)}px`;},{passive:true});
  for(const ev of ['wheel','touchstart','keydown'])d.addEventListener(ev,()=>{S.hold=null;},{passive:true});
  d.addEventListener('close',()=>{S.flash=null;S.view='list';S.pick=null;S.run=null;});
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
  if(!d.open){d.showModal();toTop();}
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
    case'back':S.view='list';S.pick=null;render();toTop();return;
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
    case'step':{const k=data.key;const base=S.wage[k]??Number(data.wage);S.wage[k]=Math.min(Number(data.max||1e6),Math.max(Number(data.min||1),base+Number(data.by)));render();return;}
    case'tab':S.tab=data.tab;S.flash=null;render();toTop();if(S.tab==='jobs')loadHire();return;
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
    default:onSelf(op,data);
  }
}

/* ---- rendering ----
 * The dialog itself is the scroller (.sheet: overflow-y auto), not .qy-body. Every render patches the page in place
 * (morph, like fair.js): only the nodes that changed are touched, so the tapped button and the focus stay and the
 * dialog never loses its height for a moment. The control just tapped is then held at the same spot on screen (a
 * flash line or a part opening above it may change heights); a part that shrinks leaves a spacer under the page
 * until the player scrolls back up, so nothing jumps to the top (owner 03/10: "bấm vào là tự scroll lên"). */
const keyOf=n=>n.nodeType!==1?'':(n.getAttribute('data-qk')||'')+'|'+(n.getAttribute('data-qy')||'')+'|'+(n.getAttribute('data-id')||'')+(n.nodeName==='SECTION'?'|'+n.className:'');
const same=(a,b)=>a.nodeType===b.nodeType&&a.nodeName===b.nodeName&&keyOf(a)===keyOf(b);
function morph(from,to){
  if(from.nodeType!==1){if(from.nodeValue!==to.nodeValue)from.nodeValue=to.nodeValue;return;}
  if(from.hasAttribute('data-qy-live')){   // drawn by script (the counter's canvas, its own width/height): only its label follows
    const l=to.getAttribute('aria-label');if(l!==null&&from.getAttribute('aria-label')!==l)from.setAttribute('aria-label',l);return;}
  for(const {name} of [...from.attributes])if(!to.hasAttribute(name))from.removeAttribute(name);
  for(const {name,value} of [...to.attributes])if(from.getAttribute(name)!==value)from.setAttribute(name,value);
  const a=[...from.childNodes].filter(n=>!n.classList?.contains('mn-line')),b=[...to.childNodes];   // the header's money chip (v4/money.js) stays
  let i=0,j=0;
  for(;j<b.length;j++){
    const n=b[j],o=a[i];
    if(!o){from.append(n);continue;}
    if(same(o,n)){morph(o,n);i++;continue;}
    if(a[i+1]&&same(a[i+1],n)){o.remove();morph(a[i+1],n);i+=2;continue;}   // a node went away
    if(b[j+1]&&same(o,b[j+1])){from.insertBefore(n,o);continue;}   // a node came in
    from.replaceChild(n,o);i++;
  }
  for(;i<a.length;i++)a[i].remove();
}
const tplEl=document.createElement('template');
const DATA=['qy','id','part','key','by','level','cand','staff','item','tab','to','code','sign','k','j'];
/** A selector that finds "the same control" again after a render (its data-qy and the data that says which one). */
function selOf(el){
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
  const top=d.scrollTop,a=document.activeElement,asel=a&&d.contains(a)?selOf(a):'';
  fn();
  holdAt(d,sel,y0,top);
  if(asel&&!a.isConnected)bySel(asel)?.focus({preventScroll:true});
  // a few frames more: the canvas, the fonts or the money chip may still settle; the player's own scroll ends it
  const hold=S.hold={};let n=0;
  const tick=()=>{if(S.hold!==hold||!S.dlg)return;if(sel||top>0)holdAt(d,sel,y0,top);if(++n<12)requestAnimationFrame(tick);else S.hold=null;};
  requestAnimationFrame(tick);
}
function render(){
  if(!S.dlg)return;
  keep(()=>{const root=S.dlg.querySelector('.qy-root');tplEl.innerHTML=page();
    const box=document.createElement('div');box.append(tplEl.content);box.className=root.className;morph(root,box);});
  S.dlg.setAttribute('aria-busy',String(S.busy));
  paintCanvases();
}
/** A new page (another view, another tab): from the top, no spacer. */
function toTop(){S.anchor='';S.hold=null;if(!S.dlg)return;const sp=S.dlg.querySelector('.qy-spacer');if(sp)sp.style.height='0px';S.dlg.scrollTop=0;}
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
  if(S.view==='run'&&stallOf(S.run?.sid))return head()+`<div class="sheet-body bk qy-body">${runView(stallOf(S.run.sid))}</div>`;
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
  const status=st.due?`Chờ đóng ${xu(st.due)} tiền thuê`:st.closed?'Đóng cửa chờ chủ':!st.staff.length?(cat.menus?'Chưa thuê ai: tự đứng quầy nhé':'Chưa có người đứng quầy'):
    `Hôm nay ${cat.weather[today.w]||''} · ${cat.pace[today.pace]||''}${today.x3?' · 🔥':''}`;
  const week=st.hist.reduce((a,h)=>a+h[2],0);
  const part=S.open[st.id]||'';
  const alerts=[
    st.case?`<div class="bk-alert bad qy-row"><span>🚨 ${st.case.all?'Mất cả két':'Trộm lấy'} ${xu(st.case.lost)}</span>${st.case.rep?'<small>Đã báo công an</small>':btn('Báo công an','police',{id:st.id},'small')}</div>`:'',
    st.due?`<div class="bk-alert warn qy-row"><span>🧾 Nợ tiền thuê ${xu(st.due)}</span>${btn('Đóng tiền','pay',{id:st.id},'small primary')}</div>`:'',
    !st.closed&&st.left<=1&&st.till>0?`<p class="bk-alert warn">Ghé thu két kẻo quầy đóng nhé.</p>`:'',
  ].join('');
  const self=!!cat.menus&&!!st.menu;   // 🧑‍🍳 a server with the board (1.5.3+)
  const tabs=[...(self?[['menu','🍽️ Menu'],['look','🎨 Trang trí']]:[]),['staff',`👥 Người (${st.staff.length}/${P.slots||1})`],['stock','📦 Hàng'],['fund','💼 Vốn'],['up','🛠️ Nâng cấp']];
  return `<section class="bk-card qy-stall" data-qk="st:${st.id}">
    ${self?`<canvas class="qy-scene" data-qy-live data-cv="${st.id}" role="img" aria-label="${esc(`Quầy ${st.name}`)}"></canvas>`:''}
    <div class="qy-top"><span class="qy-tile" aria-hidden="true">${P.emoji||'🏪'}<i>${T.emoji}</i></span>
      <div class="grow"><h3>${esc(st.name)}</h3><p class="qy-line">${esc(status)}</p></div></div>
    ${alerts}
    ${self?selfRow(st):''}
    <div class="qy-till"><div><small>Két</small><strong>${xu(st.till)}</strong>${st.hist.length?`<small>${st.hist.length} ngày qua: ${week>=0?'+':'−'}${xu(Math.abs(week))}</small>`:''}</div>
      ${btn(st.closed&&!st.due&&!st.till?'Mở lại quầy':'Thu két','till',{id:st.id},self?'':'primary',st.till||st.closed?'':'Két đang trống')}</div>
    <div class="segmented qy-tabs" role="tablist">${tabs.map(([k,l])=>`<button type="button" role="tab" aria-selected="${part===k}" class="${part===k?'active':''}" data-qy="more" data-id="${st.id}" data-part="${k}">${l}</button>`).join('')}</div>
    ${part==='menu'?menuPart(st):part==='look'?lookPart(st):part==='staff'?staffPart(st,P):part==='stock'?stockPart(st):part==='fund'?fundPart(st):part==='up'?upPart(st):''}
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

/* ======================================================================== 🧑‍🍳 tự tay (game/quay_self.py) */
const dishes=st=>CAT()?.menus?.[st.trade]||[];
const dishOf=(st,k)=>dishes(st).find(d=>d.id===k)||{id:k,emoji:'•',name:k,base:1,band:[1,1]};
const clone=o=>JSON.parse(JSON.stringify(o));
const menuDraft=st=>S.md[st.id]??=clone(st.menu);
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
  const r=st.run,rate=st.rate||[0,0];
  const day=r?.x?btn('✅ Xem kết quả hôm nay','runopen',{id:st.id},'ghost')
    :r?btn('🧑‍🍳 Vào quầy tiếp','runopen',{id:st.id},'primary')
    :btn('🧑‍🍳 Đứng quầy hôm nay','runstart',{id:st.id},'primary',st.due?'Đóng tiền thuê trước nhé':'');
  const on=!!st.online;
  return `<div class="qy-self">${day}
    <button type="button" class="qy-switch${on?' on':''}" role="switch" aria-checked="${on}" data-qy="online" data-id="${st.id}"${S.busy?' disabled':''}>
      <span class="qy-knob" aria-hidden="true"></span>📱 Bán online${on&&rate[0]?` <small>${stars(rate[1])} · ${rate[0]}</small>`:''}</button></div>`;
}

function menuPart(st){
  const m=menuDraft(st),max=CAT().menu_max||4,changed=!sameMenu(m,st.menu);
  const rows=dishes(st).map(d=>{const on=m.on.includes(d.id),p=m.p[d.id]??d.base,[lo,hi]=d.band;
    return `<li class="qy-dish${on?' on':''}"><button type="button" class="qy-dish-pick" data-qy="dish" data-id="${st.id}" data-k="${d.id}" aria-pressed="${on}"${!on&&m.on.length>=max?' disabled':''}>
        <span class="qy-up-emoji" aria-hidden="true">${d.emoji}</span><span class="grow"><b>${esc(d.name)}</b><small>Giá gốc ${xu(d.base)}</small></span><span class="qy-check" aria-hidden="true">${on?'✓':'＋'}</span></button>
      ${on?`<span class="qy-step">${btn('−','dprice',{id:st.id,k:d.id,by:-1},'small ghost',p<=lo?'Thấp nhất rồi':'')}<b>${fmt(p)}</b>${btn('＋','dprice',{id:st.id,k:d.id,by:1},'small ghost',p>=hi?'Cao nhất rồi':'')}</span>`:''}</li>`;}).join('');
  const [k,line]=feel(st,m);
  return `<div class="qy-part"><p class="qy-line">Chọn tối đa ${max} món bán hôm nay, tự đặt giá. ${helpBtn('menu')}</p>
    ${helpText('menu','Giá cao thì mỗi món lời hơn nhưng ít khách hơn. Giá mềm thì đông, khách quý quầy. Nhiều món thì thêm chút khách.')}
    <ul class="qy-list">${rows}</ul>
    <p class="qy-feel ${k}">${line}</p>
    <div class="bk-actions">${btn('Lưu menu','menusave',{id:st.id},'primary',!changed?'Chưa đổi gì':!m.on.length?'Chọn ít nhất 1 món':'')}${changed?btn('Hoàn tác','menureset',{id:st.id},'ghost'):''}</div></div>`;
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
      <div class="qy-person-act"><span class="qy-step">${btn('−','tables',{id:st.id,by:-1},'small ghost',lk.t<=0?'Hết rồi':'')}<b>${lk.t}/${most}</b>${btn('＋','tables',{id:st.id,by:1},'small ghost',lk.t>=most?'Đủ chỗ rồi':'')}</span></div></div>`:''}
    <div class="bk-actions">${btn(cost?`Lưu · ${xu(cost)}`:'Lưu','looksave',{id:st.id},'primary',changed?'':'Chưa đổi gì')}${changed?btn('Hoàn tác','lookreset',{id:st.id},'ghost'):''}</div></div>`;
}

/* ---- the day at the counter ---- */
const R=()=>S.run;
const freshRun=sid=>({sid,step:'pick',tray:[],change:0,phone:false,pack:null,hint:''});
function runView(st){
  const r=st.run;
  if(!r)return `<section class="bk-card bk-center"><p>Hôm nay chưa mở hàng.</p><div class="bk-actions center">${btn('🧑‍🍳 Đứng quầy','runstart',{id:st.id},'primary')}${btn('Về quầy','back',{},'ghost')}</div></section>`;
  const waiting=(r.orders||[]).filter(o=>!o.stars).length;
  const bar=`<div class="qy-runbar"><span title="Khách">🧍 ${r.i}/${r.k}</span><span title="Doanh thu tạm">💰 ${xu(r.rv)}</span>${r.stars?`<span>${stars(r.stars)}</span>`:''}
    ${st.online&&!r.x?`<button type="button" class="qy-phone-btn${R().phone?' on':''}" data-qy="phone" data-id="${st.id}" aria-pressed="${R().phone}" aria-label="Đơn online">📱${waiting?`<i>${waiting}</i>`:''}</button>`:''}
    ${r.x?'':btn('Đóng ca','runclose',{id:st.id},'small ghost')}</div>`;
  let panel;
  if(r.x)panel=summary(st,r);
  else if(R().pack)panel=packPanel(st,r);
  else if(R().phone)panel=phonePanel(st,r);
  else if(r.ev)panel=eventCard(st,r.ev);
  else if(r.cust)panel=customerPanel(st,r.cust);
  else panel=`<section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">${r.out?'📦':'🌙'}</div><h3>${r.out?'Hết hàng rồi!':'Hết khách xếp hàng'}</h3>
    <p>${waiting?`Còn ${waiting} đơn online chờ giao.`:'Đóng ca để tính tiền cả ngày nhé.'}</p><div class="bk-actions center">${waiting?btn('📱 Xem đơn','phone',{id:st.id},'ghost'):''}${btn('🏁 Đóng ca','runclose',{id:st.id},'primary')}</div></section>`;
  return `<section class="bk-card qy-run" data-qk="run:${st.id}">${bar}
    <canvas class="qy-scene" data-qy-live data-cv="${st.id}" role="img" aria-label="${esc(`Quầy ${st.name}`)}"></canvas>${flash()}</section>${panel}`;
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
  return `<section class="bk-card qy-cust"><div class="qy-say"><b>${esc(c.name)}</b><p>“${esc(c.say)}”</p></div>${body}</section>`;
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
    body=`<p class="qy-line">${left?`Theo đường chấm xanh tới 📍. Ngã tư thứ ${pk.picks.length+1}:`:'Tới nơi rồi!'}</p>${rideSVG(o.route,pk.picks)}
      ${left?`<div class="qy-turns">${btn('⬅️ Rẽ trái','turn',{id:st.id,k:'L'},'ghost')}${btn('⬆️ Đi thẳng','turn',{id:st.id,k:'S'},'ghost')}${btn('➡️ Rẽ phải','turn',{id:st.id,k:'R'},'ghost')}</div>`
        :`<div class="bk-actions">${btn('🤝 Giao tận tay','deliver',{id:st.id},'primary')}${btn('↺ Chạy lại','turnreset',{id:st.id},'ghost')}</div>`}`;}
  return `<section class="bk-card qy-pack"><div class="qy-say"><b>#${o.j+1} ${esc(o.name)} · ${esc(o.addr)}</b><p>${itemsLine(st,o.items)}</p>${o.note?`<p class="qy-note">📝 ${esc(o.note)}</p>`:''}</div>${body}</section>`;
}
function summary(st,r){
  const s=r.sum||{};
  return `<section class="bk-card bk-center qy-sum"><div class="bk-big-emoji" aria-hidden="true">🏁</div><h3>Đóng ca rồi!</h3>
    <ul class="qy-sumlist"><li><span>Khách bạn phục vụ</span><b>${fmt(s.hand)}</b></li>${s.on?`<li><span>Đơn online</span><b>${fmt(s.on)}</b></li>`:''}
      <li><span>Khách cả ngày</span><b>${fmt(s.n)}</b></li><li><span>Doanh thu</span><b>${xu(s.rev)}</b></li>
      <li><span>Lời</span><b class="${s.net>=0?'up':'down'}">${s.net>=0?'+':'−'}${xu(Math.abs(s.net||0))}</b></li>${s.st?`<li><span>Khách chấm</span><b>${stars(s.st)}</b></li>`:''}</ul>
    <p class="qy-muted">Tiền đã vào két. Mai ghé đứng quầy tiếp nhé!</p><div class="bk-actions center">${btn('Về quầy','back',{},'primary')}</div></section>`;
}

/** The 🧑‍🍳 taps. Returns true when it was one. */
function onSelf(op,data){
  const st=stallOf(data.id);
  const u=R();
  switch(op){
    case'runstart':send('jr_quay_start',{stall:data.id}).then(r=>{if(r){S.view='run';S.run=freshRun(data.id);S.flash={text:r.message,kind:'good'};render();toTop();}});return true;
    case'runopen':S.view='run';S.run=freshRun(data.id);S.flash=null;render();toTop();return true;
    case'online':if(st)send('jr_quay_online',{stall:st.id,on:!st.online});return true;
    case'dish':{if(!st)return true;const m=menuDraft(st),i=m.on.indexOf(data.k);
      if(i>=0){if(m.on.length>1)m.on.splice(i,1);}else if(m.on.length<(CAT().menu_max||4))m.on.push(data.k);
      render();return true;}
    case'dprice':{if(!st)return true;const m=menuDraft(st),d=dishOf(st,data.k),p=(m.p[data.k]??d.base)+Number(data.by);
      m.p[data.k]=Math.max(d.band[0],Math.min(d.band[1],p));render();return true;}
    case'menureset':delete S.md[data.id];render();return true;
    case'menusave':{if(!st)return true;const m=menuDraft(st),ds=dishes(st);
      const p=Object.fromEntries(ds.map(d=>[d.id,m.p[d.id]??d.base]));
      send('jr_quay_menu',{stall:st.id,on:ds.map(d=>d.id).filter(k=>m.on.includes(k)),p}).then(r=>{if(r){delete S.md[st.id];render();}});return true;}
    case'color':if(st){lookDraft(st).c=Number(data.k);render();}return true;
    case'decor':{if(!st)return true;const lk=lookDraft(st),i=lk.d.indexOf(data.k);if(i>=0)lk.d.splice(i,1);else if(lk.d.length<(CAT().decor_max||3))lk.d.push(data.k);render();return true;}
    case'tables':{if(!st)return true;const lk=lookDraft(st),most=CAT().tables[st.place]?.[0]||0;lk.t=Math.max(0,Math.min(most,lk.t+Number(data.by)));render();return true;}
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
    case'pack':if(u){u.pack={j:Number(data.j),bag:[],seal:false,tool:false,note:false,step:'pack',picks:[]};render();toTop();}return true;
    case'unpack':if(u){u.pack=null;render();}return true;
    case'bag':if(u?.pack&&u.pack.bag.length<6){u.pack.bag.push(data.k);render();}return true;
    case'unbag':if(u?.pack){u.pack.bag.splice(Number(data.k),1);render();}return true;
    case'ptog':if(u?.pack){u.pack[data.k]=!u.pack[data.k];render();}return true;
    case'packdone':if(u?.pack){u.pack.step='way';render();}return true;
    case'way':{if(!u?.pack||!st)return true;
      const o=(st.run?.orders||[]).find(x=>x.j===u.pack.j);
      if(data.k==='ship'){ship(st,u,'ship');return true;}
      if(RIDE.external&&o){Promise.resolve(RIDE.external(o)).then(route=>{if(Array.isArray(route)){u.pack.picks=route.slice(0,3);ship(st,u,'self');}}).catch(()=>{u.pack.step='ride';render();});return true;}
      u.pack.step='ride';render();return true;}
    case'turn':if(u?.pack&&u.pack.picks.length<3){u.pack.picks.push(data.k);render();}return true;
    case'turnreset':if(u?.pack){u.pack.picks=[];render();}return true;
    case'deliver':if(u?.pack&&st)ship(st,u,'self');return true;
    case'runclose':{if(!st)return true;const left=st.run&&!st.run.x&&(st.run.cust||st.run.ev);
      const go=()=>send('jr_quay_close',{stall:st.id}).then(r=>{if(r){if(u){u.phone=false;u.pack=null;}if(!stallOf(st.id)?.run){S.view='list';S.run=null;}render();toTop();}});
      if(left)ask('Đóng ca sớm?','Khách còn lại trong ngày do nhân viên (nếu có) và bạn bán tiếp như thường.','Đóng ca').then(ok=>{if(ok)go();});else go();
      return true;}
  }
  return false;
}
function ship(st,u,way){
  const pk=u.pack;
  send('jr_quay_ship',{stall:st.id,order:pk.j,items:pk.bag,seal:pk.seal,tool:pk.tool,note:pk.note,way,...(way==='self'?{route:pk.picks}:{})})
    .then(r=>{if(r){u.pack=null;u.phone=true;render();}});
}

/* ---- the counter's canvas: drawn after each render, only when what it shows changed ---- */
function paintCanvases(){
  if(!S.dlg)return;
  const cat=CAT();if(!cat?.menus)return;
  for(const cv of S.dlg.querySelectorAll('canvas[data-cv]')){
    const st=stallOf(cv.dataset.cv);if(!st?.menu)continue;
    const m=S.md[st.id]||st.menu,lk=S.lk[st.id]||{...st.look,name:st.name};
    const inRun=S.view==='run'&&S.run?.sid===st.id,r=st.run;
    const o={place:st.place,name:(lk.name||'').trim()||st.name,color:cat.colors[lk.c]?.[1],decor:lk.d,tables:lk.t,
      menu:m.on.map(k=>{const d=dishOf(st,k);return {emoji:d.emoji,name:d.name,price:m.p[k]??d.base};}),
      me:inRun||!st.staff.length,staff:st.staff.length,cust:inRun&&r?.cust?r.cust.look:null,queue:inRun?(r?.queue||[]):[],online:!!st.online,closed:st.closed&&!inRun};
    const key=JSON.stringify(o)+'|'+cv.clientWidth;
    if(cv._key===key)continue;cv._key=key;
    try{paintCounter(cv,{...o,me:o.me?figure(S.env.api.state):null});}catch(e){console.warn('quay scene',e);}
  }
}
