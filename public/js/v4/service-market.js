/** 🛎️ Phố dịch vụ: players serve players across careers (game/service_market.py holds every rule and number).
 * Three tabs: 🔎 Tìm (the directory: by career, sorted by ⭐ uy tín, 💰 giá, 🟢 online, 🤝 nhiều đơn), 📥 Đơn (my talks
 * and orders, both sides: the server lists each order's next actions), 🧰 Của tôi (the services I sell: bật/tắt, ×1–×10
 * or 🤝 thương lượng, the floor shown, my reputation and khách quen).
 * Buyer: pick a provider → see the price (or offer one) → confirm → the money is held → the provider works → confirm & ⭐.
 * GET /api/svc/dir|provider|inbox|mine|catalog · POST /api/svc/order|offer|answer|take|decline|cancel|done|confirm|rate|flag|settings.
 * One rid per confirmed order/offer, the same one on a retry (the server holds the money once per rid).
 * Own-flow listings (x.own: 🏥 a player's birth room, 📸 a photographer's package): the card shows the module's price and
 * rating and its button opens the module's own sheet (x.open = {action, data, label}); never an order or ×N here. */
import {escapeHTML as esc,icon} from '../icons.js';
import {stylesheet} from '../lazy.js';
import {avInner} from './face.js';
import {focusSnapshot,restoreInputFocus} from './quay-business-ui.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const rid=()=>globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
const TABS=[['dir','🔎','Tìm dịch vụ'],['inbox','📥','Đơn của tôi'],['mine','🧰','Dịch vụ của tôi']];
const SORTS=[['rating','⭐ Uy tín'],['price','💰 Giá'],['online','🟢 Online'],['deals','🤝 Nhiều đơn']];
const STATUS={talk:'Đang trả giá',held:'Đã giữ tiền · chờ nhận đơn',working:'Đang làm',delivered:'Đã giao · chờ xác nhận',ready:'Đang thanh toán',refund:'Đang hoàn tiền',
  done:'Xong',refunded:'Đã hoàn tiền',declined:'Bị từ chối',cancelled:'Đã hủy',expired:'Hết hạn',linked:'Đã chốt giá',
  requested:'Chờ nhận đơn',accepted:'Đang làm',completed:'Xong',refund_pending:'Đang hoàn tiền',failed:'Không thành'};
const ACT={accept:'Đồng ý',counter:'Trả giá',decline:'Từ chối',cancel:'Hủy',take:'Nhận đơn',done:'Xong việc',confirm:'Đã nhận · xác nhận',rate:'⭐ Đánh giá',flag:'🚩 Báo cáo'};
const MAIN=new Set(['accept','take','done','confirm']);
/** 🏨 a room of a homestay / hotel player (game/hotel_stay.py): its stay is run in 🏨 Sổ phòng, not by "Xong việc" */
const isStay=o=>['homestay','hotel'].includes(o.career)&&/^stay_/.test(o.service);
const WED=new Set(['tiec_cuoi','hoa_cuoi','vay_cuoi','trang_diem_cuoi']);   // 💒 game/wed_services.py: done step by step in Đơn cưới
/** the module sheets an own-flow listing may open (app.js handleAction): 🏥 Nhà & Gia đình, 📸 Tiệm ảnh */
const OWN=new Set(['marriage','photoStudio']);
const itemKey=x=>`${x.pid}.${x.career}.${x.service}`;
const S={dlg:null,env:null,tab:'dir',view:null,dir:null,inbox:null,mine:null,cat:null,card:null,pick:null,career:'',sort:'rating',busy:false,
  flash:null,step:'',open:{},draft:{},timer:0,seq:0};

function ensureCss(){return Promise.all([stylesheet('/css/spend.css'),stylesheet('/css/service-market.css')]);}
const api=()=>S.env.api;
const wallet=()=>Math.max(0,Number(api().state?.journey?.wallet)||0);
const face=w=>`<span class="svc-av" aria-hidden="true">${avInner({fc:w?.fc,av:w?.avatar||'🙂'})}</span>`;
const stars=r=>r?.n?`<span class="svc-stars">⭐ <b>${String(r.avg).replace('.',',')}</b> <small>(${fmt(r.n)})</small></span>`:'<span class="svc-stars none">⭐ <small>Chưa có đánh giá</small></span>';
const btn=(label,op,data={},cls='ghost',extra='')=>`<button type="button" class="btn ${cls}" data-svc="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${S.busy?' disabled':''}${extra}>${label}</button>`;
const draft=id=>S.draft[id]??={price:'',stars:5,comment:'',text:'',note:'',qty:1};
const careerName=c=>S.cat?.services?.find(s=>s.career===c)?.career_name||c;

export async function openServiceMarket(env,data={}){
  S.env=env;
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet?.();
  await ensureCss();
  if(!S.dlg){
    const d=document.createElement('dialog');
    d.className='sheet v4-sheet medium sd-sheet svc-sheet';d.setAttribute('aria-labelledby','svc-title');
    d.innerHTML='<div class="sd-root"></div>';document.body.append(d);S.dlg=d;
    d.addEventListener('click',e=>{if(e.target===d){d.close();return;}const el=e.target.closest('[data-svc]');if(!el||el.disabled)return;e.preventDefault();click(el.dataset.svc,el.dataset);});
    d.addEventListener('input',input);d.addEventListener('change',input);
    d.addEventListener('close',()=>{clearInterval(S.timer);S.seq++;document.removeEventListener('visibilitychange',visible);});
  }
  S.flash=null;S.step='';S.pick=null;S.card=null;
  S.tab=data.tab||(data.inbox?'inbox':data.pid?'dir':S.tab||'dir');
  if(data.career&&!data.pid){S.tab='dir';S.card=null;S.career=data.career;}   // 🧰 Phục chế đồ: straight to the restorers
  if(!S.dlg.open){S.dlg.showModal();S.dlg.scrollTop=0;}
  render();
  if(!S.cat)S.cat=await api().json('/api/svc/catalog').catch(()=>null);
  if(data.pid)await openProvider(data.pid,data);else await load();
  document.addEventListener('visibilitychange',visible);
  clearInterval(S.timer);S.timer=setInterval(()=>{if(!document.hidden&&S.dlg?.open&&!S.busy&&S.tab==='inbox'&&!S.step)load(true);},15000);
}
function visible(){if(!document.hidden&&S.dlg?.open)load(true);}

async function load(quiet=false){
  const seq=++S.seq;if(!quiet){S.loading=true;render();}
  try{
    if(S.tab==='dir'&&!S.card){const q=new URLSearchParams({sort:S.sort});if(S.career)q.set('career',S.career);S.dir=await api().json('/api/svc/dir?'+q);}
    else if(S.tab==='inbox'){S.inbox=await api().json('/api/svc/inbox');api().svcAlerts=S.inbox.alerts||0;document.dispatchEvent(new Event('mnl:badges'));}
    else if(S.tab==='mine'){S.mine=await api().json('/api/svc/mine');}
    if(seq!==S.seq)return;
  }catch(e){if(seq===S.seq)S.flash={kind:'bad',text:e.message||'Chưa tải được. Thử lại nhé.'};}
  finally{if(seq===S.seq){S.loading=false;render();}}
}

async function openProvider(pid,data={}){
  S.tab='dir';S.step='';S.flash=null;S.loading=true;render();
  try{
    const v=await api().json('/api/svc/provider?pid='+encodeURIComponent(pid));
    S.card=v;
    const item=v.items.find(x=>(!data.career||x.career===data.career)&&(!data.service||x.service===data.service))||v.items[0]||null;
    S.pick=item?{item,offer:data.offer_id?item.offers?.find(o=>o.offer_id===data.offer_id):item.offers?.[0]||null}:null;
  }catch(e){S.flash={kind:'bad',text:e.message||'Chưa tải được.'};S.card=null;}
  finally{S.loading=false;render();}
}

async function post(route,body,after){
  if(S.busy)return null;S.busy=true;S.flash=null;render();
  try{
    const r=await api().post('/api/svc/'+route,body);
    S.flash=r?.message?{kind:'good',text:r.message}:null;
    api().refresh?.().catch(()=>{});
    if(after)await after(r);
    return r;
  }catch(e){S.flash={kind:'bad',text:e.message||'Chưa gửi được. Thử lại nhé.'};return null;}
  finally{S.busy=false;render();}
}

function input(e){
  const t=e.target,k=t.dataset.k,f=t.dataset.f;if(!f)return;
  if(f==='career'){S.career=t.value;load();return;}
  if(k&&f){draft(k)[f]=t.value;if(f==='price'&&S.card)render();}
  if(f==='set'){const m=S.mine?.services?.find(x=>`${x.career}.${x.service}`===t.dataset.id);if(m){m._dirty=true;if(t.name==='note')m.note=t.value;}}
}

async function click(op,d){
  if(op==='close'){S.dlg.close();return;}
  if(op==='tab'){S.tab=d.tab;S.card=null;S.pick=null;S.step='';S.flash=null;await load();return;}
  if(op==='sort'){S.sort=d.sort;await load();return;}
  if(op==='more'){const q=new URLSearchParams({sort:S.sort,offset:S.dir?.next||0});if(S.career)q.set('career',S.career);try{const v=await api().json('/api/svc/dir?'+q);S.dir={...v,items:[...(S.dir?.items||[]),...v.items]};}catch(e){S.flash={kind:'bad',text:e.message};}render();return;}
  if(op==='provider'){await openProvider(d.pid,{career:d.career,service:d.service});return;}
  if(op==='own'){const x=[...(S.dir?.items||[]),...(S.card?.items||[])].find(i=>itemKey(i)===d.id);await openOwn(x?.open);return;}
  if(op==='setup'){const m=S.mine?.services?.find(i=>`${i.career}.${i.service}`===d.id);await openOwn(m?.setup);return;}
  if(op==='back'){if(S.step){S.step='';render();return;}S.card=null;S.pick=null;await load();return;}
  if(op==='pickItem'){const item=S.card.items.find(x=>`${x.career}.${x.service}`===d.id);S.pick={item,offer:item?.offers?.[0]||null};S.step='';render();return;}
  if(op==='pickOffer'){S.pick.offer=S.pick.item.offers.find(o=>o.offer_id===d.id)||null;render();return;}
  if(op==='qty'){const x=draft(key());x.qty=Math.max(1,Math.min(S.pick.item.qty_max||1,(Number(x.qty)||1)+Number(d.n)));render();return;}
  if(op==='chip'){draft(key()).price=String(d.n);render();return;}
  if(op==='review'){S.step='confirm';render();return;}
  if(op==='buy'){await buy();return;}
  if(op==='toggle'){S.open[d.id]=S.open[d.id]===d.what?'':d.what;render();return;}
  if(op==='do'){await act(d.action,d.id);return;}
  if(op==='star'){draft(d.id).stars=Number(d.n);render();return;}
  if(op==='legacy'){S.dlg.close();await (await import('./workplace-visit.js')).openWorkplaceVisit(S.env,{inbox:true});return;}
  if(op==='place'){S.dlg.close();await (await import('./workplace-visit.js')).openWorkplaceVisit(S.env,{place:d.place});return;}
  if(op==='hotel'){S.dlg.close();await (await import('./hotel-stay.js')).openHotel(S.env,{order:d.id||'',tab:d.tab||''});return;}
  if(op==='wed'){S.dlg.close();await (await import('./wed-services.js')).openWedServices(S.env,{tab:'work'});return;}
  if(op==='set')return setting(d);
  if(op==='retry'){await load();return;}
}

/** 🏥 / 📸 the module's own sheet (its own booking, escrow and payout): the market only lists it. */
async function openOwn(link){
  if(!link||!OWN.has(link.action)||!S.env?.act)return;
  S.dlg.close();await S.env.act(link.action,{...(link.data||{})});
}

const key=()=>S.pick?`${S.pick.item.pid}.${S.pick.item.career}.${S.pick.item.service}.${S.pick.offer?.offer_id||''}`:'';
/** The price this order would cost (fixed), or the offer typed (thương lượng). */
function priceOf(){
  const it=S.pick?.item,x=draft(key());if(!it)return 0;
  if(it.legacy){const o=S.pick.offer;return it.mode==='nego'?Number(x.price)||0:(o?.price||0);}
  const qty=Math.max(1,Number(x.qty)||1);
  return it.mode==='nego'?Number(x.price)||0:it.price*qty;
}
function bounds(){const it=S.pick?.item,qty=Math.max(1,Number(draft(key()).qty)||1);if(!it)return [0,0];const o=it.legacy?S.pick.offer:null;return o?[o.lo,o.hi]:[it.lo*qty,it.hi*qty];}

async function buy(){
  const it=S.pick.item,x=draft(key()),price=priceOf(),nego=it.mode==='nego';
  const body={pid:it.pid,career:it.career,service:it.service,note:x.note||''};
  if(it.legacy){if(!S.pick.offer)return;body.place=S.pick.offer.place;body.offer_id=S.pick.offer.offer_id;}else body.qty=Math.max(1,Number(x.qty)||1);
  if(nego)body.price=price;else body.expected_price=price;
  const fp=JSON.stringify(body);if(x.fp!==fp){x.fp=fp;x.rid=rid();}
  body.rid=x.rid;
  const r=await post(nego?'offer':'order',body);
  if(r){x.rid=null;x.fp=null;S.step='';S.card=null;S.pick=null;S.tab='inbox';S.focus=r.order?.id||'';await load(true);}
}

async function act(action,id){
  const x=draft(id);
  if(action==='counter'){if(S.open[id]!=='counter'){S.open[id]='counter';render();return;}const n=Number(x.price);if(!n)return;await post('answer',{order:id,op:'counter',price:n},()=>{S.open[id]='';x.price='';return load(true);});return;}
  if(action==='rate'){if(S.open[id]!=='rate'){S.open[id]='rate';render();return;}await post('rate',{order:id,stars:x.stars||5,comment:x.comment||''},()=>{S.open[id]='';return load(true);});return;}
  if(action==='flag'){if(S.open[id]!=='flag'){S.open[id]='flag';render();return;}await post('flag',{order:id,text:x.text||''},()=>{S.open[id]='';return load(true);});return;}
  const row=S.inbox?.items?.find(o=>o.id===id);
  if(action==='accept'){await post('answer',{order:id,op:'accept',ask:row?.ask},()=>load(true));return;}
  // a second tap within 4 s confirms the ones that stop or move money
  if(['decline','cancel'].includes(action)&&S.arm!==action+id){S.arm=action+id;clearTimeout(S.armT);S.armT=setTimeout(()=>{S.arm='';render();},4000);render();return;}
  S.arm='';
  await post(action,{order:id},()=>load(true));
}

async function setting(d){
  const m=S.mine?.services?.find(x=>`${x.career}.${x.service}`===d.id);if(!m)return;
  if(d.what==='on')m.on=!m.on;
  if(d.what==='mode')m.mode=d.mode;
  if(d.what==='mult')m.mult=Math.max(S.mine.rules.mult_min,Math.min(S.mine.rules.mult_max,(m.mult||3)+Number(d.n)));
  if(d.what==='save'||d.what==='on'){
    await post('settings',{career:m.career,service:m.service,on:m.on,mode:m.mode,mult:m.mult,note:m.note||''},r=>{if(r?.mine)S.mine=r.mine;});
    return;
  }
  m._dirty=true;render();
}
/** 🏥 / 📸 set up in the module (price, open / closed): shown here, with a link there (no ×N, no switch). */
function ownSetting(m){
  const id=`${m.career}.${m.service}`;
  return `<article class="svc-set svc-own${m.on?' on':''}" data-k="${esc(id)}"><div class="svc-row"><span class="sd-ico" aria-hidden="true">${esc(m.icon)}</span><div class="grow"><b>${esc(m.name)}</b><small class="svc-muted">${esc(m.desc||m.career_name)}</small></div>
    <span class="svc-pill ${m.on?'s-working':'s-cancelled'}">${m.on?'🟢 Đang hiện':'⚪ Chưa hiện'}</span></div>
    ${m.why?`<p class="sd-why">${esc(m.why)}</p>`:''}${m.price?`<p class="svc-total"><span>${m.note?esc(m.note):'Giá của bạn'}</span><b>${fmt(m.price)} xu</b></p>`:''}
    <p class="svc-note">Giá và mở / đóng đặt ở mục riêng của nghề; khách đặt và trả tiền ở đó.</p>${btn(`${esc(m.setup?.label||'Cài đặt')} ›`,'setup',{id},'ghost full')}</article>`;
}
const unit=(m,mult)=>Math.max(m.lo,Math.min(m.hi,m.base*mult));

/* ---------------------------------------------------------------- views */
function render(){
  if(!S.dlg)return;
  const root=S.dlg.querySelector('.sd-root'),top=S.dlg.scrollTop,focus=focusSnapshot(document.activeElement?.closest?.('.svc-sheet')?document.activeElement:null);
  root.innerHTML=page();
  S.dlg.scrollTop=top;if(focus?.id)restoreInputFocus(root,focus);
  S.dlg.setAttribute('aria-busy',String(!!(S.busy||S.loading)));
}
function page(){
  const t=TABS.find(x=>x[0]===S.tab)||TABS[0],alerts=Number(api().svcAlerts)||0;
  const head=`<div class="svc-stick"><header class="sheet-head sd-head"><span class="sd-logo" aria-hidden="true">🛎️</span><div class="grow"><h2 id="svc-title">Phố dịch vụ</h2><small class="svc-sub">${esc(t[2])}</small></div>
    <span class="sd-wallet" title="Ví">👛 ${fmt(wallet())}</span><button class="icon-btn" type="button" data-svc="close" aria-label="Đóng">${icon('x',21)}</button></header>
    <nav class="sd-tabs" role="tablist" aria-label="Phố dịch vụ">${TABS.map(([id,e,l])=>`<button type="button" role="tab" aria-selected="${t[0]===id}" aria-label="${esc(l)}" title="${esc(l)}" class="${t[0]===id?'on':''}" data-svc="tab" data-tab="${id}">${e}${id==='inbox'&&alerts?`<em class="badge">${alerts}</em>`:''}</button>`).join('')}</nav></div>`;
  const flash=`<p class="sd-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  let body='',foot='';
  if(S.tab==='dir'&&S.card){[body,foot]=providerView();}
  else if(S.tab==='dir')body=dirView();
  else if(S.tab==='inbox')body=inboxView();
  else body=mineView();
  return head+`<div class="sheet-body sd-body">${body}</div>`+`<div class="sd-bar svc-bar">${flash}${foot}</div>`;
}

function dirView(){
  const v=S.dir;if(!v)return S.loading?'<p class="sd-empty">⏳</p>':`<p class="sd-empty">🛎️</p>${btn('Thử lại','retry')}`;
  const careers=[...new Set((v.counts||[]).map(c=>c.career))];
  const filter=`<div class="svc-filter"><label class="sd-select"><span class="sr-only">Nghề</span><select data-f="career"><option value="">Tất cả nghề</option>${careers.map(c=>`<option value="${esc(c)}"${S.career===c?' selected':''}>${esc(careerName(c))}</option>`).join('')}</select></label></div>
    <div class="sd-chips svc-sorts" role="group" aria-label="Sắp xếp">${SORTS.map(([k,l])=>`<button type="button" class="sd-chip${S.sort===k?' on':''}" data-svc="sort" data-sort="${k}" aria-pressed="${S.sort===k}">${l}</button>`).join('')}</div>`;
  if(!v.items.length)return filter+`<section class="sd-card svc-empty"><p class="tp-big">🛎️</p><h3>Chưa có ai mở dịch vụ</h3><p class="svc-note">Bạn mở dịch vụ của mình ở 🧰 nhé.</p>${btn('🧰 Dịch vụ của tôi','tab',{tab:'mine'},'primary')}</section>`;
  return filter+`<div class="svc-list">${v.items.map(card).join('')}</div>${v.next!=null?btn('Xem thêm','more',{},'ghost full'):''}`;
}
function priceLine(x){
  return x.mode==='nego'?`<span class="svc-price nego">🤝 <small>từ</small> <b>${fmt(x.lo)}</b> <small>xu</small></span>`
    :`<span class="svc-price"><b>${fmt(x.price)}</b> <small>xu</small>${x.mult?` <i class="svc-mult">×${x.mult}</i>`:''}</span>`;
}
function card(x){
  if(x.own)return ownCard(x);
  return `<button type="button" class="svc-card${x.mine?' mine':''}" data-svc="provider" data-pid="${esc(x.pid)}" data-career="${esc(x.career)}" data-service="${esc(x.service)}"${x.available===false?' aria-disabled="true"':''}>
    ${face(x.who)}<span class="grow"><b class="svc-name">${esc(x.who?.name||'')}${x.online?' <i class="svc-on" title="Đang online">●</i>':''}</b>
    <span class="svc-what">${esc(x.icon)} ${esc(x.name)} <small>· ${esc(careerName(x.career))}</small></span>
    <span class="svc-meta">${stars(x.rep)}${x.rep?.deals?` <small>· ${fmt(x.rep.deals)} đơn</small>`:''}</span></span>
    <span class="svc-right">${priceLine(x)}${x.available===false?'<small class="svc-off">Tạm nghỉ</small>':''}</span></button>`;
}

/** 🏥 / 📸 a provider of an own-flow listing: tap opens the module's order sheet (its own price, its own escrow). */
function ownCard(x){
  return `<button type="button" class="svc-card svc-own${x.mine?' mine':''}" data-svc="own" data-id="${esc(itemKey(x))}">
    ${face(x.who)}<span class="grow"><b class="svc-name">${esc(x.who?.name||'')}${x.online?' <i class="svc-on" title="Đang online">●</i>':''}</b>
    <span class="svc-what">${esc(x.icon)} ${esc(x.name)}${x.note?` · <small>${esc(x.note)}</small>`:''} <small>· ${esc(careerName(x.career))}</small></span>
    <span class="svc-meta">${stars(x.rep)}${x.rep?.deals?` <small>· ${fmt(x.rep.deals)} ${esc(x.unit)}</small>`:''}</span></span>
    <span class="svc-right"><span class="svc-price"><b>${fmt(x.price)}</b> <small>xu</small></span><span class="svc-open">${esc(x.open?.label||'Mở')} ›</span></span></button>`;
}

function providerView(){
  const v=S.card;if(!v)return [S.loading?'<p class="sd-empty">⏳</p>':'',''];
  const head=`${btn('‹ Quay lại','back',{},'ghost svc-back')}<section class="sd-card svc-who">${face(v.who)}<div class="grow"><h3>${esc(v.who.name)}${v.online?' <i class="svc-on">●</i>':''}</h3>
    <p class="svc-meta">${stars(v.rep)} <small>· ${fmt(v.rep.deals)} đơn · 🤝 ${fmt(v.rep.regulars)} khách quen</small></p><small class="svc-muted">${v.online?'Đang online':'Đang vắng'}</small></div></section>`;
  const extra=(v.reviews?.length?`<section class="svc-sec"><h3 class="tp-h">⭐ Đánh giá gần đây</h3>${v.reviews.map(r=>`<article class="svc-order small"><div class="svc-row">${face(r.who)}<div class="grow"><b>${esc(r.who?.name||'')}</b><small class="svc-muted svc-gold">${'★'.repeat(Math.max(1,Math.min(5,r.stars|0)))}</small></div></div>${r.comment?`<p>${esc(r.comment)}</p>`:''}</article>`).join('')}</section>`:'')
    +(v.mine&&v.regulars?.length?`<section class="svc-sec"><h3 class="tp-h">🤝 Khách quen</h3>${v.regulars.map(r=>`<div class="svc-row svc-reg">${face(r)}<b class="grow">${esc(r.name)}</b><small class="svc-muted">${fmt(r.n)} đơn</small></div>`).join('')}</section>`:'');
  if(!v.items.length)return [head+'<p class="svc-note">Người này đang tạm nghỉ mọi dịch vụ.</p>'+extra,''];
  const tabs=v.items.length>1?`<div class="sd-chips">${v.items.map(x=>`<button type="button" class="sd-chip${S.pick?.item===x?' on':''}" data-svc="pickItem" data-id="${esc(x.career+'.'+x.service)}">${esc(x.icon)} ${esc(x.name)}</button>`).join('')}</div>`:'';
  const it=S.pick?.item;if(!it)return [head+tabs+extra,''];
  if(it.own){   // its module books and holds the money: a button to its sheet, no order here
    const body=head+tabs+`<section class="sd-card svc-buy"><h3>${esc(it.icon)} ${esc(it.name)}</h3>${it.desc?`<p class="svc-muted">${esc(it.desc)}</p>`:''}${it.note?`<p class="svc-quote">“${esc(it.note)}”</p>`:''}
      <p class="svc-total"><span>Giá</span><b>${fmt(it.price)} xu</b></p><p class="svc-note">Đặt, giữ tiền và thanh toán ở mục riêng của nghề này (không qua đơn Phố dịch vụ).</p></section>${extra}`;
    return [body,it.mine?'<p class="sd-why">Đây là dịch vụ của bạn.</p>':btn(`${esc(it.open?.label||'Mở')} ›`,'own',{id:itemKey(it)},'primary sd-main')];
  }
  const x=draft(key()),nego=it.mode==='nego',[lo,hi]=bounds(),price=priceOf();
  if(S.step==='confirm')return confirmView(head,it,x,price,nego);
  const offers=it.legacy?(it.offers?.length?`<div class="svc-offers" role="radiogroup" aria-label="Chọn việc">${it.offers.map(o=>`<button type="button" role="radio" aria-checked="${S.pick.offer===o}" class="sd-item${S.pick.offer===o?' on':''}" data-svc="pickOffer" data-id="${esc(o.offer_id)}"><b>${esc(o.label)}</b><em>${nego?'🤝 ':''}${fmt(nego?o.lo:o.price)} xu</em></button>`).join('')}</div>${btn('🏡 Ghé chỗ làm','place',{place:it.offers[0].place},'ghost')}`:'<p class="svc-note">Chỗ làm này chưa có việc nhận khách lúc này.</p>'):'';
  const qty=!it.legacy&&it.qty_max>1?`<div class="svc-qty"><span>Số ${esc(it.unit)}</span>${btn('−','qty',{n:-1},'ghost')}<b>${fmt(x.qty||1)}</b>${btn('+','qty',{n:1},'ghost')}</div>`:'';
  const chips=nego?[1,2,3,5].map(m=>{const base=it.legacy?(S.pick.offer?.base||0):(it.base||0)*Math.max(1,Number(x.qty)||1);const n=Math.max(lo,Math.min(hi,base*m));return n?`<button type="button" class="sd-chip${Number(x.price)===n?' on':''}" data-svc="chip" data-n="${n}">${fmt(n)}</button>`:'';}).join(''):'';
  const priceBox=nego?`<label class="svc-field"><span>Giá bạn trả (xu)</span><input id="svc-offer-${esc(key())}" data-k="${esc(key())}" data-f="price" type="number" inputmode="numeric" min="${lo}" max="${hi}" value="${esc(x.price)}" placeholder="${fmt(lo)} – ${fmt(hi)}"></label><div class="sd-chips svc-chips">${chips}</div><p class="svc-note">Từ ${fmt(lo)} đến ${fmt(hi)} xu. Người bán đồng ý, trả giá lại hoặc từ chối.</p>`
    :`<p class="svc-total"><span>Giá</span><b>${fmt(price)} xu</b>${it.mult?`<i class="svc-mult">×${it.mult}</i>`:''}</p>`;
  const body=head+tabs+`<section class="sd-card svc-buy"><h3>${esc(it.icon)} ${esc(it.name)}</h3>${it.desc&&!it.legacy?`<p class="svc-muted">${esc(it.desc)}</p>`:''}${it.note?`<p class="svc-quote">“${esc(it.note)}”</p>`:''}
    ${offers}${qty}${priceBox}
    <label class="svc-field"><span>Lời nhắn (không bắt buộc)</span><input id="svc-note-${esc(key())}" data-k="${esc(key())}" data-f="note" type="text" maxlength="160" value="${esc(x.note)}" placeholder="Ví dụ: làm giúp mình buổi tối nhé"></label></section>
    <details class="svc-rules"><summary>Tiền được giữ thế nào?</summary><ul><li>Tiền lấy từ ví, thiếu thì từ tài khoản. Không cho nợ.</li><li>Người bán xong việc và bạn xác nhận thì người bán nhận tiền (Phố giữ 5%).</li><li>Hủy, bị từ chối hoặc quá hạn: hoàn đủ tiền.</li><li>Có vấn đề: báo cáo trong 24 giờ sau khi giao.</li></ul></details>${extra}`;
  const ready=it.legacy?!!S.pick.offer:true,ok=ready&&price>=lo&&price<=hi&&!it.mine&&it.available!==false;
  const foot=it.mine?'<p class="sd-why">Đây là dịch vụ của bạn.</p>':btn(nego?(price?`🤝 Gửi giá ${fmt(price)} xu`:'🤝 Gửi giá'):`Đặt · ${fmt(price)} xu`,'review',{},'primary sd-main',ok?'':' disabled');
  return [body,foot];
}
function confirmView(head,it,x,price,nego){
  const short=price>wallet()+Number(api().state?.journey?.bank?.balance||0);
  const body=head+`<section class="sd-card svc-confirm"><h3>Kiểm tra lại nhé</h3><dl class="svc-dl"><div><dt>Dịch vụ</dt><dd>${esc(it.icon)} ${esc(it.name)}${S.pick.offer?` · ${esc(S.pick.offer.label)}`:''}</dd></div>
    ${!it.legacy&&it.qty_max>1?`<div><dt>Số lượng</dt><dd>${fmt(x.qty||1)} ${esc(it.unit)}</dd></div>`:''}<div><dt>${nego?'Giá bạn trả':'Giá'}</dt><dd><b>${fmt(price)} xu</b></dd></div>${x.note?`<div><dt>Lời nhắn</dt><dd>«${esc(x.note)}»</dd></div>`:''}</dl>
    <p class="svc-note">${nego?'Chưa trừ tiền. Khi hai bên chốt giá, tiền mới được giữ.':'Tiền được giữ ngay. Người bán xong việc, bạn xác nhận thì mới trả.'}</p>${short?'<p class="sd-why">Ví và tài khoản chưa đủ tiền.</p>':''}</section>`;
  return [body,btn('Sửa','back',{},'ghost')+btn(nego?'Gửi giá':`Giữ ${fmt(price)} xu & đặt`,'buy',{},'primary sd-main',short&&!nego?' disabled':'')];
}

function inboxView(){
  const v=S.inbox;if(!v)return S.loading?'<p class="sd-empty">⏳</p>':btn('Thử lại','retry');
  const need=[],live=[],past=[];
  for(const o of v.items){const mine=o.actions.some(a=>MAIN.has(a)||a==='rate'||a==='counter');(['done','refunded','declined','cancelled','expired','linked'].includes(o.status)?(o.actions.includes('rate')?need:past):mine?need:live).push(o);}
  const sec=(title,rows,empty)=>rows.length?`<section class="svc-sec"><h3 class="tp-h">${title} <small>${rows.length}</small></h3>${rows.map(order).join('')}</section>`:(empty?`<p class="svc-note">${empty}</p>`:'');
  const legacy=v.legacy?.length?`<section class="svc-sec"><h3 class="tp-h">🏡 Đơn ở chỗ làm <small>${v.legacy.length}</small></h3>${v.legacy.slice(0,8).map(o=>`<article class="svc-order small"><div class="svc-row"><b>${esc(o.name||o.place_name||'Đơn')}</b><span class="svc-pill s-${esc(o.status)}">${esc(STATUS[o.status]||o.status)}</span></div><p class="svc-muted">${o.role==='buyer'?'Bạn đặt':'Khách'}: ${esc(o.other?.name||'')} · ${fmt(o.price)} xu</p></article>`).join('')}${btn('🏡 Mở sổ khách chỗ làm','legacy',{},'ghost full')}</section>`:'';
  if(!v.items.length&&!v.legacy?.length)return `<section class="sd-card svc-empty"><p class="tp-big">📥</p><h3>Chưa có đơn nào</h3><p class="svc-note">Tìm một dịch vụ ở 🔎 nhé.</p>${btn('🔎 Tìm dịch vụ','tab',{tab:'dir'},'primary')}</section>`;
  return sec('🔔 Cần bạn',need,'')+sec('⏳ Đang diễn ra',live,'')+legacy+sec('✅ Đã xong',past.slice(0,20),'');
}
function order(o){
  const x=draft(o.id),role=o.role==='buyer'?'Người bán':'Khách',talk=o.status==='talk';
  const price=talk?`<span class="svc-price"><b>${fmt(o.ask)}</b> <small>xu</small></span>`:`<span class="svc-price"><b>${fmt(o.price)}</b> <small>xu</small></span>`;
  const turn=talk?`<p class="svc-turn">${o.ask_by===o.role?'Bạn vừa trả giá · chờ người kia':'Đến lượt bạn trả lời'} <small>· lượt ${o.rounds}/${o.max_rounds}</small></p>`:'';
  const money=o.status==='done'&&o.role==='provider'?`<p class="svc-muted">Bạn nhận ${fmt(o.paid)} xu · phí ${fmt(o.fee)} xu</p>`:o.status==='refunded'&&o.role==='buyer'?`<p class="svc-muted">Đã hoàn ${fmt(o.price)} xu về ví</p>`:'';
  const res=o.result?`<p class="svc-result">🎁 ${esc(Object.values(o.result).filter(v=>typeof v==='string'||typeof v==='number').slice(0,3).join(' · '))}</p>`:'';
  const open=S.open[o.id];
  const forms=open==='counter'?`<div class="svc-form"><label class="svc-field"><span>Giá của bạn (xu) · từ ${fmt(o.lo)} đến ${fmt(o.hi)}</span><input id="svc-c-${esc(o.id)}" data-k="${esc(o.id)}" data-f="price" type="number" inputmode="numeric" min="${o.lo}" max="${o.hi}" value="${esc(x.price)}"></label>${btn('Gửi giá','do',{action:'counter',id:o.id},'primary')}</div>`
    :open==='rate'?`<div class="svc-form"><div class="svc-starpick" role="radiogroup" aria-label="Số sao">${[1,2,3,4,5].map(n=>`<button type="button" role="radio" aria-checked="${(x.stars||5)===n}" class="svc-star${(x.stars||5)>=n?' on':''}" data-svc="star" data-id="${esc(o.id)}" data-n="${n}" aria-label="${n} sao">★</button>`).join('')}</div><label class="svc-field"><span>Nhận xét (không bắt buộc)</span><input id="svc-r-${esc(o.id)}" data-k="${esc(o.id)}" data-f="comment" type="text" maxlength="300" value="${esc(x.comment)}"></label>${btn('Gửi đánh giá','do',{action:'rate',id:o.id},'primary')}</div>`
    :open==='flag'?`<div class="svc-form"><label class="svc-field"><span>Chuyện gì đã xảy ra?</span><textarea id="svc-f-${esc(o.id)}" data-k="${esc(o.id)}" data-f="text" maxlength="300" rows="3">${esc(x.text)}</textarea></label><p class="svc-note">Quản trị sẽ xem. Không tự trừ tiền ai.</p>${btn('Gửi báo cáo','do',{action:'flag',id:o.id},'primary')}</div>`:'';
  const stay=isStay(o)&&!['refunded','declined','cancelled','expired'].includes(o.status);
  const wed=WED.has(o.service)&&o.role==='provider'&&o.status==='working';   // 💒 a wedding order: its job is done in Đơn cưới (v4/wed-services.js)
  const acts=(wed?btn('💒 Làm đơn cưới','wed',{},'primary'):'')+(stay&&o.status!=='held'?o.actions.filter(a=>a!=='done'&&a!=='decline'):o.actions).filter(a=>!(wed&&a==='done')).map(a=>{const armed=S.arm===a+o.id;return btn(armed?'Bấm lần nữa':(ACT[a]||a),'do',{action:a,id:o.id},MAIN.has(a)?'primary':armed?'danger':'ghost');}).join('');
  return `<article class="svc-order${S.focus===o.id?' focus':''}" data-k="${esc(o.id)}"><div class="svc-row">${face(o.other)}<div class="grow"><b>${esc(o.icon)} ${esc(o.name)}${o.qty>1?` <small>× ${o.qty}</small>`:''}</b><small class="svc-muted">${role}: ${esc(o.other?.name||'')}</small>${o.label?`<small class="svc-muted">${esc(o.label)}</small>`:''}</div>${price}</div>
    <p><span class="svc-pill s-${esc(o.status)}">${esc(STATUS[o.status]||o.status)}</span>${o.flagged?' <span class="svc-pill s-flag">🚩 Đã báo cáo</span>':''}</p>${turn}${o.note?`<blockquote>${esc(o.note)}</blockquote>`:''}${res}${money}
    ${acts||stay?`<div class="svc-acts">${acts}${stay?btn('🏨 Sổ phòng','hotel',{id:o.id,tab:o.role==='provider'?'host':'guest'},o.status==='working'?'primary':'ghost'):''}</div>`:''}${forms}</article>`;
}

function mineView(){
  const v=S.mine;if(!v)return S.loading?'<p class="sd-empty">⏳</p>':btn('Thử lại','retry');
  const R=v.rules;
  const rep=`<section class="sd-card svc-rep"><div class="svc-row"><div class="grow"><h3>Uy tín của bạn</h3><p class="svc-meta">${stars(v.rep)} <small>· ${fmt(v.rep.deals)} đơn · 🤝 ${fmt(v.rep.regulars)} khách quen</small></p></div>${btn('Xem thẻ','provider',{pid:v.pid},'ghost')}</div>
    <p class="svc-note">Khách trả ×${R.default_mult} giá thường. Bạn nhận ${100-R.fee_pct}%, Phố giữ ${R.fee_pct}%.</p></section>`;
  if(!v.services.length)return rep+'<p class="svc-note">Vào làm một nghề để mở dịch vụ cho người chơi khác.</p>';
  const groups=new Map();for(const m of v.services){const g=m.career_name||m.career;if(!groups.has(g))groups.set(g,[]);groups.get(g).push(m);}
  return rep+[...groups].map(([g,rows])=>`<section class="svc-sec"><h3 class="tp-h">${esc(g)}</h3>${rows.map(svcSetting).join('')}</section>`).join('');
}
function svcSetting(m){
  if(m.own)return ownSetting(m);
  const id=`${m.career}.${m.service}`,R=S.mine.rules,price=unit(m,m.mult||R.default_mult),nego=m.mode==='nego';
  return `<article class="svc-set${m.on?' on':''}" data-k="${esc(id)}"><div class="svc-row"><span class="sd-ico" aria-hidden="true">${esc(m.icon)}</span><div class="grow"><b>${esc(m.name)}</b><small class="svc-muted">${esc(m.legacy?m.career_name:(m.desc||m.career_name))}</small></div>
    <button type="button" class="svc-switch${m.on?' on':''}" role="switch" aria-checked="${!!m.on}" aria-label="Bật dịch vụ" data-svc="set" data-id="${esc(id)}" data-what="on"${m.why&&!m.on?' disabled':''}${S.busy?' disabled':''}><i></i></button></div>
    ${m.why?`<p class="sd-why">${esc(m.why)}</p>`:''}
    <div class="sd-chips svc-mode" role="group" aria-label="Cách tính giá">${btn('Giá cố định','set',{id,what:'mode',mode:'fixed'},!nego?'sd-chip on':'sd-chip')}${btn('🤝 Thương lượng','set',{id,what:'mode',mode:'nego'},nego?'sd-chip on':'sd-chip')}</div>
    ${nego?`<p class="svc-note">Khách trả giá từ <b>${fmt(m.lo)}</b> đến <b>${fmt(m.hi)}</b> xu, bạn đồng ý hoặc trả lại.</p>`
      :`<div class="svc-mult-row">${btn('−','set',{id,what:'mult',n:-1},'ghost',m.mult<=R.mult_min?' disabled':'')}<b class="svc-mult big">×${m.mult}</b>${btn('+','set',{id,what:'mult',n:1},'ghost',m.mult>=R.mult_max?' disabled':'')}<span class="svc-eq">= <b>${fmt(price)}</b> xu</span></div>`}
    <p class="svc-muted">Giá thường ${fmt(m.base)} xu${m.floor>m.base?` · giá sàn ${fmt(m.floor)} xu`:''}</p>
    <label class="svc-field"><span>Lời giới thiệu (không bắt buộc)</span><input name="note" id="svc-n-${esc(id)}" data-f="set" data-id="${esc(id)}" type="text" maxlength="80" value="${esc(m.note||'')}" placeholder="Ví dụ: Nhận đơn buổi tối"></label>
    ${m._dirty?btn('Lưu','set',{id,what:'save'},'primary full'):''}</article>`;
}
