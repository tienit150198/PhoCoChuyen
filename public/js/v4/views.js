/** v0.4 shared sheets: stock & suppliers, customer feedback threads, real-life
 * situations with several points of view, and job applications. Views return
 * HTML strings; clicks go through the global data-action/data-command delegate. */
import {icon,portrait,escapeHTML as esc} from '../icons.js';
import {asset} from '../assets.js';
import {nextHint,stepCta,pending,goAttrs} from './guide.js';
import {CAREERS as GUIDE} from '../tutorial/guide-data.js';
import {certInfo,certCss} from './certificates.js';
import {lockChip} from '../careers/stage_fold.js';
import {wordsFor} from '../scenes/index.js';
import {fundLabel} from './money.js';
import {confirmPurchase} from './payment.js';
import {orderQuote,fitDraft,vans,vansLine} from './restock.js';
import {Sound} from '../audio.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
/** The workplace money word the 💰 chip uses too ("Quỹ tiệm", "Quỹ nông trại"…; v4/money.js). */
const fundName=id=>fundLabel(wordsFor(id).till);
/** Short deliveries not claimed yet (received today or yesterday) and what the supplier refunds (game/inventory.py inv_claim). */
const unclaimed=(orders,day)=>orders.filter(o=>o.status==='received'&&o.actual<o.qty&&!o.claimed&&Number(o.day)>=Number(day)-1);
const refundOf=o=>Math.max(1,Math.floor((2*o.cost*(o.qty-o.actual)+o.qty)/(2*o.qty)));
const attrs=obj=>Object.entries(obj).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const button=(label,action,data={},style='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}>${label}</button>`;
const cmdBtn=(label,command,payload={},style='',disabled=false)=>`<button type="button" class="btn ${style}" data-command="${command}" data-payload="${esc(JSON.stringify(payload))}"${disabled?' disabled':''}>${label}</button>`;
const confirmCmd=(label,command,payload={},question='',style='',disabled=false)=>`<button type="button" class="btn ${style}" data-action="v4Cmd" data-op="${command}" data-payload="${esc(JSON.stringify(payload))}" data-confirm="${esc(question)}"${disabled?' disabled':''}>${label}</button>`;
const pill=(label,kind='')=>`<span class="tag ${kind}">${label}</span>`;
const stars=n=>n?'★'.repeat(n)+'☆'.repeat(5-n):'';
const head=(title,sub='',eyebrow='')=>`<header class="sheet-head"><div class="grow">${eyebrow?`<span class="eyebrow">${eyebrow}</span>`:''}<h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
const tabs=(items,active,action)=>`<nav class="pill-tabs" role="tablist">${items.map(([id,label])=>`<button role="tab" aria-selected="${id===active}" class="${id===active?'active':''}" data-action="${action}" data-tab="${id}">${label}</button>`).join('')}</nav>`;

/* ---------------------------------------------------------------- Stock */
/** Lines of a merged order (đơn gộp, game/inventory.py) share a `group`: one van, one crate, one claim.
 * Returns shipments {id, lines, o (first line), group} in the order the lines came. */
const shipments=list=>{const out=[],seen=new Map();
  for(const o of list){if(!o.group){out.push({id:o.id,lines:[o],o,group:false});continue;}
    let g=seen.get(o.group);if(!g){g={id:o.group,lines:[],o,group:true};seen.set(o.group,g);out.push(g);}g.lines.push(o);}
  return out;};
/** What a shipment cost: the goods of every line plus the one shipping fee (kept on its first line). */
const paidOf=g=>g.lines.reduce((n,o)=>n+Number(o.cost||0)+Number(o.ship||0),0);
const COUNT_TIP='👆 Chạm từng món · giữ để đếm nhanh';
/** Counting a crate is the player's job (a crate can come short), but a tap per unit was slow (player
 * feedback #97): press and hold the crate and the goods are counted one after another, about seven a
 * second, until you let go or nothing is left uncounted. Every unit still lights up as it is counted and
 * the box shows only what was counted; tapping single goods works as before. The latest env is kept so
 * the listeners (installed once) re-render the sheet that is open now. */
const HOLD_WAIT=300,HOLD_STEP=140;
let stockEnv=null,stockOn=false;
const holdSfx=new Sound();
function tallyOne(ui,order,k){const t=(ui.invTally??={}),on=new Set(t[order]||[]);on.add(k);t[order]=[...on];
  (ui.invCount??={})[order]=String(on.size);if(ui.invTyped)delete ui.invTyped[order];return on.size;}
function stockBoot(env){
  stockEnv=env;
  if(stockOn||typeof document==='undefined')return;stockOn=true;
  if(!document.querySelector('link[data-stock-css]')){const l=document.createElement('link');l.rel='stylesheet';l.href=asset('/css/stock.css');l.dataset.stockCss='1';document.head.append(l);}
  let crate=null,key='',wait=0,beat=0,x0=0,y0=0,counted=0,swallow=0,down=false;
  const step=()=>{
    // The sheet may re-render under the finger (a state refresh): carry on in the same crate's new copy.
    if(crate&&!crate.isConnected&&key){crate=[...document.querySelectorAll('#sheet .inv-crate')].find(u=>u.querySelector('.inv-good')?.dataset.order===key)||null;crate?.classList.add('holding');}
    const b=crate?.isConnected&&crate.querySelector('.inv-good:not(.on)');
    if(!b){stop();return;}
    const ui=stockEnv.ui,n=tallyOne(ui,b.dataset.order,Number(b.dataset.i));counted++;
    b.classList.add('on','tick');b.setAttribute('aria-pressed','true');b.setAttribute('aria-label',`${b.getAttribute('aria-label')||''}, đã đếm`);
    const inp=document.getElementById('count-'+b.dataset.order);if(inp){inp.value=String(n);inp.removeAttribute('aria-invalid');}
    holdSfx.pop();
  };
  const stop=()=>{
    clearTimeout(wait);clearInterval(beat);wait=beat=0;crate?.classList.remove('holding');crate=null;
    // What was counted lands like taps do: the next step, the note "N món" (one re-render, not one per unit).
    if(counted){counted=0;swallow=down?Infinity:Date.now()+600;stockEnv?.renderSheet?.();}
  };
  document.addEventListener('pointerdown',e=>{
    const ul=e.target.closest?.('#sheet .inv-crate');
    if(!ul||e.button>0||!ul.querySelector('.inv-good:not(.on)'))return;
    stop();crate=ul;key=ul.querySelector('.inv-good')?.dataset.order||'';down=true;x0=e.clientX;y0=e.clientY;
    holdSfx.configure(stockEnv?.api?.state?.settings||{});holdSfx.unlock();
    wait=setTimeout(()=>{if(!crate)return;crate.classList.add('holding');step();beat=setInterval(step,HOLD_STEP);},HOLD_WAIT);
  });
  // A finger that slides is scrolling the sheet, not holding.
  document.addEventListener('pointermove',e=>{if(crate&&!beat&&Math.hypot(e.clientX-x0,e.clientY-y0)>10)stop();});
  for(const t of ['pointerup','pointercancel'])document.addEventListener(t,()=>{down=false;if(crate)stop();if(swallow===Infinity)swallow=Date.now()+600;});
  document.addEventListener('contextmenu',e=>{if(e.target.closest?.('#sheet .inv-crate'))e.preventDefault();});
  // The click that ends a hold is not also a tap (it would un-count the good under the finger).
  window.addEventListener('click',e=>{if(swallow&&Date.now()<swallow&&e.target.closest?.('#sheet .inv-crate')){swallow=0;e.preventDefault();e.stopImmediatePropagation();}},true);
}
/** Stock room: a status strip with ONE next step, shelf bins (count, fill,
 * goods on the way, expiry), an order card with a stepper and suppliers,
 * per-supplier drafts (đơn gộp: several lines, one fee, one delivery),
 * crates to open and count by eye (the slip may differ from what is inside),
 * and lots by days left. The server stays authoritative for every rule. */
export function inventoryView(env){
  stockBoot(env);
  const {api,ui}=env,c=api.state.careers[api.state.current],inv=c.inventory,content=api.content;
  if(!inv)return head('Nghề này không nhập hàng')+`<div class="sheet-body"><div class="empty">${icon('box',32)}<p>Không có kho nguyên liệu ở nghề này.</p></div></div>`;
  const items=content.inventory.items[api.state.current]||[],byId=Object.fromEntries(items.map(i=>[i.id,i]));
  const cap=inv.capacity,arriving=inv.arriving||{},unit=i=>i?.unit||'phần',stock=id=>inv.stock[id]||0;
  const room=id=>inv.room?.[id]??Math.max(0,cap-stock(id)-(arriving[id]||0));
  // Sent here by a "📦 Nhập hàng" button (restock.js): the items it was for, and the job to go back to.
  const focus=(ui.invFocus||[]).filter(id=>byId[id]&&!inv.locked.includes(id)),need=id=>Math.max(1,Number(ui.invNeed?.[id])||1);
  const back=ui.invReturn&&(c.tasks||[]).some(t=>t.id===ui.invReturn&&!['completed','referred','cancelled'].includes(t.status))?ui.invReturn:null;
  const mine=o=>!focus.length||focus.includes(o.item);
  const orders=inv.orders||[],ready=orders.filter(o=>o.status==='in_transit'&&o.ready_now).sort((a,b)=>mine(b)-mine(a));
  // Soonest first: the server gives each order its arrival day and time of day.
  const soon=o=>(Number(o.arrives_day)||0)*1440+(String(o.arrives_time||'').split(':').reduce((h,m)=>h*60+Number(m||0),0));
  const transit=orders.filter(o=>o.status==='in_transit'&&!o.ready_now).sort((a,b)=>mine(b)-mine(a)||soon(a)-soon(b));
  const readyS=shipments(ready),transitS=shipments(transit);
  const carts=inv.carts||[],cartOf=sid=>carts.find(k=>k.supplier===sid)||null,inCart=id=>carts.some(k=>k.lines.some(l=>l.item===id));
  const clk=inv.clock||null;
  const open=items.filter(i=>!inv.locked.includes(i.id)),lowLine=Math.max(2,Math.floor(cap*.08));
  const low=open.filter(i=>stock(i.id)+(arriving[i.id]||0)<=lowLine).sort((a,b)=>stock(a.id)-stock(b.id));
  const tonight=open.reduce((n,i)=>n+(inv.expiring[i.id]||0),0);
  const tab=['stock','orders','lots'].includes(ui.invTab)?ui.invTab:'stock';
  const name=i=>`${esc(i?.emoji||'📦')} ${esc(i?.name||'')}`;
  const today=o=>clk&&Number(o.arrives_day)===Number(clk.day)&&clk.is_open&&clk.minute<clk.close;
  const waitGo={cmd:'inv_wait',payload:{},label:`⏳ Chờ thêm ${Number(clk?.step)||20} phút`};
  const opened=g=>ui.invOpen===g.id||g.lines.some(l=>l.id===ui.invOpen)||readyS.length===1;
  const tallied=o=>(ui.invTally?.[o.id]||[]).length;
  const counted=o=>{const typed=Boolean(ui.invTyped?.[o.id])&&String(ui.invCount?.[o.id]??'').trim()!=='',k=tallied(o),n=Number(o.count_hint)||0;
    return {ok:k>=n||typed||null,note:k?`${k} món`:'',go:k<n&&!typed?{sel:`#crate-${o.id} .inv-good:not(.on)`,label:COUNT_TIP}:null};};
  const sups=supplierList(env),supOf=sid=>sups.find(x=>x.id===sid)||content.inventory.suppliers.find(x=>x.id===sid);
  // A draft open in the stock tab (đơn gộp): opened from its chip, or right after something was added.
  const pick=ui.orderItem&&byId[ui.orderItem]&&!inv.locked.includes(ui.orderItem)?byId[ui.orderItem]:null;
  const cartNow=!pick&&tab==='stock'&&ui.invCart?cartOf(ui.invCart):null;
  // Several items short: one tap puts them all in ONE draft at a supplier that sells every one of them.
  // A supplier whose draft still has room for these lines comes first (inv_cart takes at most cart_lines; `fit` leaves the rest out).
  const lineCap=Number(inv.cart_lines)||8,roomFor=(x,ids)=>{const k=cartOf(x.id);return (k?.lines.length||0)+ids.filter(id=>!k?.lines.some(l=>l.item===id)).length<=lineCap;};
  // The draft it offers is one the player can place (restock.js fitDraft): no more lines than the draft has
  // left (the nail shop, 20 items low, sent them all and inv_cart refused the lot) and trimmed to what the
  // fund pays. Under two lines: null (the single-item order form below says why). `label(n)`: the button.
  const lineFree=x=>lineCap-(cartOf(x.id)?.lines.length||0);
  const fillGo=(ids,label,qty)=>{const pref=ui.orderRush?'express':'partner',list=[sups.find(x=>x.id===pref),...sups].filter(x=>x&&ids.every(id=>sells(x,id)));
    const s=list.find(x=>roomFor(x,ids))||[...list].sort((a,b)=>lineFree(b)-lineFree(a))[0];
    if(!s||lineFree(s)<1)return null;
    const lines=fitDraft(ids.map(id=>({id,cost:byId[id].cost,q:qty(id)})),s,Math.floor((Number(c.money)||0)*.8),{free:lineFree(s),have:Number(cartOf(s.id)?.goods)||0});
    return lines.length>=2?{act:'v4CartFill',data:{supplier:s.id,items:lines.map(l=>`${l.id}:${l.q}`).join(',')},label:label(lines.length),n:lines.length}:null;};

  /* ONE next step for this room (guide.js), in order of what gets goods onto the shelf soonest. */
  const steps=[];
  const crates=focus.length?readyS.filter(g=>g.lines.some(mine)):readyS;
  for(const g of crates){
    if(!g.group){const o=g.o,i=byId[o.item];
      if(!opened(g)){steps.push({ok:null,label:`Mở thùng ${i?.name||''}`,go:{act:'v4InvOpen',data:{order:o.id},label:`📦 Mở thùng ${name(i)} & xếp lên kệ`}});continue;}
      steps.push({label:`Đếm ${i?.name||''} trong thùng`,...counted(o)});
      steps.push({ok:null,label:'Nhận vào kệ',go:{act:'v4Receive',data:{order:o.id},label:`✅ Nhận ${name(i)} lên kệ`}});
      continue;}
    if(!opened(g)){steps.push({ok:null,label:`Mở thùng gộp ${g.lines.length} món`,go:{act:'v4InvOpen',data:{order:g.id},label:`📦 Mở thùng gộp · ${g.lines.length} món`}});continue;}
    for(const o of g.lines)steps.push({label:`Đếm ${byId[o.item]?.name||''}`,...counted(o)});
    steps.push({ok:null,label:'Nhận cả thùng vào kệ',go:{act:'v4ReceiveGroup',data:{group:g.id},label:'✅ Nhận cả thùng lên kệ'}});
  }
  // A crate that came short (and no order form in hand): the claim is offered right here, not only deep in the order list (player feedback #28).
  const shorts=unclaimed(orders,c.day),shortS=shipments(shorts);
  const claimGo=g=>g.group?{cmd:'inv_claim',payload:{group:g.id},label:`📝 Khiếu nại phần thiếu · hoàn ${fmt(g.lines.reduce((n,o)=>n+refundOf(o),0))} xu`}
    :{cmd:'inv_claim',payload:{order:g.o.id},label:`📝 Khiếu nại phần thiếu · hoàn ${fmt(refundOf(g.o))} xu`};
  if(!steps.length&&shortS.length&&!pick){const g=shortS[0],o=g.o,i=byId[o.item];
    steps.push({ok:null,label:g.group?'Khiếu nại đơn gộp giao thiếu':`Khiếu nại ${i?.name||''} giao thiếu`,note:`thiếu ${g.lines.reduce((n,l)=>n+l.qty-l.actual,0)}`,go:claimGo(g)});}
  const missing=focus.filter(id=>stock(id)<need(id));
  if(!steps.length&&back&&!missing.length)steps.push({ok:null,label:'Hàng đã lên kệ: về bán tiếp',go:{act:'job',data:{task:back},label:'🛒 Hàng đã lên kệ · về bán tiếp'}});
  // Full order book (inv_order refuses): ready crates are already the steps above; else wait for the next one.
  if(!steps.length&&pick&&tab==='stock'&&room(pick.id)>0){const full=vans(inv).full,o=transit[0];
    steps.push(full&&ready[0]?{ok:null,label:'Mở thùng đã tới rồi đặt tiếp',go:{act:'v4InvOpen',data:{order:ready[0].id},label:'📦 Mở thùng đã tới & xếp lên kệ'}}
      :full&&o?{ok:null,label:'Đợi thùng về rồi đặt tiếp',note:o.left_label||o.eta_label||'',go:today(o)?waitGo:null}:{ok:null,label:`Đặt ${pick.name}`,go:{act:'v4OrderGo',data:{item:pick.id},label:`🚚 Đặt ${name(pick)}`}});}
  if(!steps.length&&cartNow&&cartNow.n&&!cartNow.short&&!cartNow.below_min&&!vans(inv).full)steps.push({ok:null,label:'Đặt đơn gộp',go:{act:'v4CartGo',data:{supplier:cartNow.supplier},label:`🚚 Đặt đơn gộp · ${cartNow.n} món`}});
  // The open draft cannot be placed yet: the reason as the step (the draft card shows it too), not another draft to fill.
  if(!steps.length&&cartNow&&cartNow.n&&(cartNow.short||cartNow.below_min))
    steps.push({ok:null,label:cartNow.short?`Bớt hàng trong đơn: ${fundName(api.state.current)} thiếu ${fmt(cartNow.short)} xu`:`Thêm hàng: đơn gộp từ ${fmt(cartNow.min_order)} xu`});
  if(!steps.length&&!cartNow){
    const want=missing.filter(id=>!arriving[id]&&room(id)>0&&!inCart(id));
    const go=want.length>=2?fillGo(want,n=>`🛒 Gộp ${n} món thiếu · một đơn`,id=>Math.min(room(id),Math.max(need(id)-stock(id),10))):null;
    if(go)steps.push({ok:null,label:`Gộp ${go.n} món thiếu vào một đơn`,go});
  }
  if(!steps.length)for(const id of missing){if(arriving[id]||inCart(id))continue;steps.push({ok:null,label:`Nhập ${byId[id].name}`,go:{act:'v4Order',data:{item:id},label:`📦 Nhập ${name(byId[id])}`}});break;}
  if(!steps.length&&focus.length&&!cartNow){const k=carts.find(k=>k.lines.some(l=>focus.includes(l.item)));
    if(k)steps.push({ok:null,label:'Đặt đơn đang soạn',go:{act:'v4Cart',data:{supplier:k.supplier,open:'1'},label:`🛒 Xem đơn đang soạn · ${k.lines.length} món`}});}
  if(!steps.length){
    const o=transit.find(mine);
    if(o&&(focus.length||back||!ready.length))steps.push({ok:null,label:`Chờ ${o.group?'đơn gộp':byId[o.item]?.name||''} về`,note:o.left_label||o.eta_label||'',go:today(o)?waitGo:null});
  }
  if(!steps.length&&!focus.length){
    const lowFree=low.filter(i=>room(i.id)>0&&!inCart(i.id)).map(i=>i.id);
    const fill=lowFree.length>=2?fillGo(lowFree,n=>`🛒 Gộp ${n} món sắp hết · một đơn`,id=>Math.min(room(id),10)):null;
    if(ready.length)steps.push({ok:null,label:'Mở thùng',go:{act:'v4InvOpen',data:{order:readyS[0].id},label:'📦 Mở thùng & xếp lên kệ'}});
    else if(carts.length&&!cartNow)steps.push({ok:null,label:'Đặt đơn đang soạn',go:{act:'v4Cart',data:{supplier:carts[0].supplier,open:'1'},label:`🛒 Xem đơn đang soạn · ${carts[0].lines.length} món`}});
    else if(fill)steps.push({ok:null,label:`Nhập thêm ${fill.n} món sắp hết`,go:fill});
    else if(low.length)steps.push({ok:null,label:`Nhập thêm ${low[0].name}`,go:{act:'v4Order',data:{item:low[0].id},label:`📦 Nhập thêm ${name(low[0])}`}});
    else if(tonight)steps.push({ok:null,label:'Xem hàng hết hạn tối nay',go:{act:'v4InvTab',data:{tab:'lots'},label:'⏰ Xem hàng hết hạn tối nay'}});
  }
  const nx=pending(steps),glow=Boolean(focus.length||back);
  const hint=steps.length?nextHint({room:c},steps,{glow}):'';
  const cta=nx?.go&&!nx.go.sel?`<button type="button" class="btn primary big gd-cta"${goAttrs(nx.go)}>${nx.go.label}</button>`:'';
  const chip=(n,label,kind,tabId)=>n?`<button type="button" class="inv-chip ${kind}" data-action="v4InvTab" data-tab="${tabId}"><b>${n}</b> ${label}</button>`:'';
  const calm=!ready.length&&!transit.length&&!tonight&&!low.length?`<span class="inv-calm">${icon('check',14)} Kho ổn.</span>`:'';
  const now=clk?`<div class="row spread"><span class="tag blue">🕑 ${esc(clk.label)}</span><small class="muted">Mở cửa ${esc(clk.open_time)}–${esc(clk.close_time)}</small></div>`:'';
  const first=transit[0],next=!ready.length&&first?`<small class="inv-next">${icon('truck',13)} ${first.group?`Đơn gộp ${transitS.find(g=>g.id===first.group)?.lines.length||''} món`:name(byId[first.item])} · <b>${esc(first.left_label||first.eta_label||'')}</b>${first.left_label&&first.eta_label?` <span class="muted">(${esc(first.eta_label)})</span>`:''}</small>`:'';
  const strip=`<section class="inv-status" aria-label="Tình trạng kho">${now}<div class="inv-chips">${chip(readyS.length,'thùng đã tới','accent','orders')}${chip(transitS.length,'đơn đang giao','info','orders')}${chip(tonight,'hết hạn tối nay','bad','lots')}${chip(low.length,'loại sắp hết','warn','stock')}${calm}</div>${next}${cta?`<div class="inv-cta">${cta}</div>`:''}</section>`;

  /* Crates at the door: always on top, one big button each; opened, the goods are tapped to count. */
  const sup=o=>supOf(o.supplier);
  const sizeNote=o=>o.size?` · size ${esc(o.size)}`:'';
  // Scatter the goods a little (stable per order) so counting is looking, not reading.
  const goodsOf=(o,i)=>{const n=Number(o.count_hint)||0,on=new Set(ui.invTally?.[o.id]||[]);let h=0;for(const ch of o.id)h=(h*31+ch.charCodeAt(0))>>>0;
    return Array.from({length:n},(_,k)=>{h=(Math.imul(h,1103515245)+12345)>>>0;const r=(h%21)-10,dy=((h>>>5)%7)-3;
      return `<li style="transform:translateY(${dy}px) rotate(${r}deg)"><button type="button" class="inv-good${on.has(k)?' on':''}" data-action="v4Tally" data-order="${esc(o.id)}" data-i="${k}" aria-pressed="${on.has(k)}" aria-label="${esc(i.name)}${on.has(k)?', đã đếm':''}">${esc(i.emoji||'📦')}</button></li>`;}).join('');};
  const counter=o=>`<div class="inv-stepper"><button type="button" class="btn ghost" data-action="v4Count" data-target="count-${esc(o.id)}" data-step="-1" aria-label="Bớt một">−</button><input id="count-${esc(o.id)}" class="input" type="number" min="0" max="60" inputmode="numeric" value="${esc(ui.invCount?.[o.id]??'')}" placeholder="0" data-v4-count="${esc(o.id)}" required><button type="button" class="btn ghost" data-action="v4Count" data-target="count-${esc(o.id)}" data-step="1" aria-label="Thêm một">+</button></div>`;
  const crate=o=>{
    const i=byId[o.item]||{name:o.item},s=sup(o),isOpen=opened({id:o.id,lines:[o]});
    const form=`<div class="inv-slip"><span>Phiếu giao ghi</span><b>${o.qty} ${esc(unit(i))}</b></div><p class="inv-tip">${COUNT_TIP}</p><ul class="inv-crate" aria-label="Trong thùng">${goodsOf(o,i)}</ul>`+
      `<form class="inv-receive" data-v4-receive="${esc(o.id)}"><label for="count-${esc(o.id)}">Bạn đếm được</label>${counter(o)}<button class="btn primary" type="button" data-action="v4Receive" data-order="${esc(o.id)}">${icon('check',15)} Nhận vào kệ</button></form>`+
      `<p class="muted small">Phiếu có thể ghi khác; thiếu thì nhận đúng số có rồi khiếu nại.</p>`;
    return `<article class="card inv-crate-card${isOpen?' open':''}" id="crate-${esc(o.id)}"><div class="row spread"><div><strong>${name(i)}${sizeNote(o)}</strong><small class="muted block">${esc(s?.emoji||'')} ${esc(s?.name||'')} · đã trả ${fmt(paidOf({lines:[o]}))} xu${o.arrives_time?` · tới lúc ${esc(o.arrives_time)}`:''}</small></div>${pill('ĐÃ TỚI','green')}</div>${isOpen?form:button(`📦 Mở thùng & xếp lên kệ`,'v4InvOpen',{order:o.id},'primary big full inv-open')}</article>`;};
  // One crate for a merged order: a slip and a pile per line, one count each, one "receive" for all.
  const groupCrate=g=>{
    const s=sup(g.o),isOpen=opened(g),list=g.lines.map(o=>`${esc(byId[o.item]?.emoji||'📦')} ${esc(byId[o.item]?.name||o.item)}${sizeNote(o)} ×${o.qty}`).join(' · ');
    const body=isOpen?`<p class="inv-tip">${COUNT_TIP}</p>`+g.lines.map(o=>{const i=byId[o.item]||{name:o.item};
        return `<div class="inv-gline" id="crate-${esc(o.id)}"><div class="inv-slip"><span>${name(i)}${sizeNote(o)}</span><b>${o.qty} ${esc(unit(i))}</b></div><ul class="inv-crate" aria-label="${esc(i.name)} trong thùng">${goodsOf(o,i)}</ul><div class="inv-receive"><label for="count-${esc(o.id)}">Đếm được</label>${counter(o)}</div></div>`;}).join('')+
      `<button class="btn primary big full" type="button" data-action="v4ReceiveGroup" data-group="${esc(g.id)}">${icon('check',15)} Nhận cả thùng lên kệ</button><p class="muted small">Phiếu có thể ghi khác; thiếu thì nhận đúng số có rồi khiếu nại.</p>`
      :`<p class="inv-gnames">${list}</p>${button(`📦 Mở thùng gộp · ${g.lines.length} món`,'v4InvOpen',{order:g.id},'primary big full inv-open')}`;
    return `<article class="card inv-crate-card inv-group${isOpen?' open':''}" id="crate-${esc(g.id)}"><div class="row spread"><div><strong>🛒 Đơn gộp · ${g.lines.length} món</strong><small class="muted block">${esc(s?.emoji||'')} ${esc(s?.name||'')} · đã trả ${fmt(paidOf(g))} xu${g.o.arrives_time?` · tới lúc ${esc(g.o.arrives_time)}`:''}</small></div>${pill('ĐÃ TỚI','green')}</div>${body}</article>`;};
  const shortCard=g=>{const s=sup(g.o),miss=g.lines.reduce((n,o)=>n+o.qty-o.actual,0);
    const title=g.group?`🛒 Đơn gộp · thiếu ${g.lines.map(o=>`${o.qty-o.actual} ${esc(byId[o.item]?.name||o.item)}`).join(', ')}`:`${name(byId[g.o.item]||{name:g.o.item})} · nhận ${g.o.actual}/${g.o.qty}`;
    const go=claimGo(g),isNext=nx?.go?.cmd==='inv_claim'&&JSON.stringify(nx.go.payload)===JSON.stringify(go.payload);
    return `<article class="card inv-short" data-order="${esc(g.o.id)}"><div class="row spread"><div class="grow"><strong>${title}</strong><small class="muted block">${esc(s?.emoji||'')} ${esc(s?.name||'')} giao thiếu ${miss}${g.group?' món':` ${esc(unit(byId[g.o.item]))}`} · đã trả ${fmt(paidOf(g))} xu</small></div>${pill('GIAO THIẾU','amber')}</div>`+
      // The one that is the next step already has the big button in the strip above.
      (isNext?'':`<div class="row wrap">${cmdBtn(go.label,'inv_claim',go.payload,'small primary')}</div>`)+'</article>';};
  const shortBox=shortS.length?`<section class="inv-door inv-shorts" aria-label="Hàng giao thiếu"><h4 class="section-title">📉 Giao thiếu · khiếu nại để được hoàn tiền</h4>${shortS.map(shortCard).join('')}</section>`:'';
  const door=readyS.length?`<section class="inv-door" aria-label="Thùng hàng đã tới"><h4 class="section-title">📦 Thùng đã tới · mở & xếp lên kệ</h4>${readyS.map(g=>g.group?groupCrate(g):crate(g.o)).join('')}</section>`:'';
  const nothing=(text='Chưa có hàng')=>`<div class="empty inv-empty">${icon('truck',30)}<p><b>${esc(text)}</b> · Đặt hàng ↓</p>${button(`${icon('plus',15)} Đặt hàng`,'v4InvTab',{tab:'stock'},'primary')}</div>`;

  let body='';
  if(tab==='stock'){
    const pct=v=>Math.max(0,Math.min(100,Math.round(v/cap*100)));
    const bin=i=>{
      const q=stock(i.id),on=arriving[i.id]||0,locked=inv.locked.includes(i.id),exp=inv.expiring[i.id]||0,soon=(inv.expiring_soon?.[i.id]||0)-exp,days=inv.days_left?.[i.id];
      const state=locked?'locked':q===0?'out':q+on<=lowLine?'low':'';
      const carted=carts.reduce((n,k)=>n+(k.lines.find(l=>l.item===i.id)?.qty||0),0);
      const flags=locked?`<span class="inv-flag">${icon('lock',11)} Mở ở cấp ${i.unlock}</span>`:[on?`<span class="inv-flag info">+${on} đang giao</span>`:'',carted?`<span class="inv-flag cart">🛒 ${carted}</span>`:'',exp?`<span class="inv-flag bad">${exp} hết hạn tối nay</span>`:soon>0?`<span class="inv-flag warn">${soon} hết hạn mai</span>`:'',q===0&&!on?'<span class="inv-flag bad">Hết hàng</span>':''].join('');
      const life=!locked&&days&&days<900&&!exp?` · còn ${days} ngày`:'';
      return `<button type="button" class="inv-bin ${state}" data-action="v4Order" data-item="${esc(i.id)}"${locked?' disabled':''} aria-label="${esc(i.name)}: ${q} trên kệ${on?`, ${on} đang giao`:''}${locked?`, mở ở cấp ${i.unlock}`:', chạm để nhập thêm'}">`+
        `<span class="inv-bin-top"><span class="inv-bin-emoji" aria-hidden="true">${esc(i.emoji||'📦')}</span><span class="inv-bin-count"><b>${locked?'—':q}</b><small>/${cap}</small></span></span>`+
        `<span class="inv-bin-name">${esc(i.name)}</span><small class="inv-bin-unit">${esc(unit(i))}${life}</small>`+
        `<span class="inv-bar" aria-hidden="true"><i style="width:${locked?0:pct(q)}%"></i><i class="on" style="width:${pct(on)}%"></i></span>`+
        `${flags?`<span class="inv-flags">${flags}</span>`:''}</button>`;};
    const shown=focus.length?items.filter(i=>focus.includes(i.id)):items;
    // Sections by group; runs of one-item groups share a section so the grid stays full.
    // Locked goods (a later level) fold into one chip under the shelf: "🔒 N món mở ở cấp X–Y" (UX 2026-09-30).
    const lockedHere=focus.length?[]:shown.filter(i=>inv.locked.includes(i.id)),unlocked=shown.filter(i=>!lockedHere.includes(i));
    const sections=[];
    for(const g of new Set(unlocked.map(i=>i.group))){const list=unlocked.filter(i=>i.group===g),last=sections.at(-1);
      if(list.length===1&&last?.single)last.names.push(groupName(g)),last.list.push(...list);else sections.push({names:[groupName(g)],list,single:list.length===1});}
    const order=list=>[...list.filter(i=>!inv.locked.includes(i.id)),...list.filter(i=>inv.locked.includes(i.id))];
    body=focus.length?`<div class="inv-focus"><span class="grow">Đang xem: ${focus.map(id=>name(byId[id])).join(', ')}</span>${button(`Xem tất cả ${icon('x',13)}`,'v4InvFocus',{},'ghost small')}</div><div class="inv-bins">${order(shown).map(bin).join('')}</div>`
      :sections.map(x=>`${sections.length>1?`<h4 class="section-title">${esc(x.names.join(' · '))}</h4>`:''}<div class="inv-bins">${order(x.list).map(bin).join('')}</div>`).join('')+lockChip(lockedHere.map(i=>i.unlock),'inv-lock');
    if(pick)body=orderCard(env,pick,{cap,stock:stock(pick.id),on:arriving[pick.id]||0,space:room(pick.id),unit:unit(pick),name:name(pick)})+body;
    else if(cartNow)body=cartCard(env,cartNow,{byId,unit})+body;
    // Drafts waiting to be placed: one chip per supplier, its count as a badge.
    if(carts.length&&!cartNow)body=`<div class="inv-carts" role="group" aria-label="Đơn đang soạn">${carts.map(k=>{const s=supOf(k.supplier);
      return `<button type="button" class="inv-cart-chip" data-action="v4Cart" data-supplier="${esc(k.supplier)}" data-open="1" aria-label="Đơn gộp ${esc(s?.name||'')}: ${k.lines.length} món, ${fmt(k.total)} xu"><span aria-hidden="true">🛒</span><b class="inv-badge">${k.lines.length}</b><span class="inv-cart-name">${esc(s?.emoji||'')} ${esc(s?.name||k.supplier)}</span><b>${fmt(k.total)} xu</b></button>`;}).join('')}</div>`+body;
  }else if(tab==='orders'){
    const waiting=g=>{const o=g.o,i=byId[o.item]||{name:o.item},s=sup(o),late=Boolean(o.late_note),pct=Math.round(Math.max(0,Math.min(1,Number(o.progress)||0))*100);
      // Waiting helps only for goods due later today; the rest arrive while you work or overnight.
      const wait=today(o)?cmdBtn(waitGo.label,'inv_wait',{},'ghost small'):'';
      const title=g.group?`🛒 Đơn gộp · ${g.lines.length} món`:`${name(i)}${sizeNote(o)} · ${o.qty} ${esc(unit(i))}`;
      const list=g.group?`<p class="inv-gnames">${g.lines.map(l=>`${esc(byId[l.item]?.emoji||'📦')} ${esc(byId[l.item]?.name||l.item)}${sizeNote(l)} ×${l.qty}`).join(' · ')}</p>`:'';
      return `<article class="card order-row${g.lines.some(mine)&&focus.length?' mine':''}"><div class="row spread"><div class="grow"><strong>${title}</strong><small class="muted block">${esc(s?.emoji||'')} ${esc(s?.name||'')} · đã trả ${fmt(paidOf(g))} xu</small></div>${pill(late?'TRỄ HẸN':`⏱ ${esc(o.left_label||'đang giao')}`,late?'amber':'blue')}</div>${list}`+
        `<div><span class="small">Dự kiến nhận: <b>${esc(o.eta_label||'đang trên đường')}</b></span>${o.window?`<small class="muted block">Hẹn giao ${esc(o.window)}</small>`:''}</div>`+
        `<span class="inv-bar" role="progressbar" aria-label="Quãng đường đã đi" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><i class="on" style="width:${pct}%"></i></span>`+
        `${late?`<p class="notice amber small">${icon('truck',15)} <span><b>${esc(s?.name||'')}:</b> “${esc(o.late_note)}”</span></p>`:''}`+
        `${wait?`<div class="row wrap"><span class="grow"></span>${wait}</div>`:''}</article>`;};
    const received=g=>{const o=g.o,i=byId[o.item]||{name:o.item},s=sup(o),short=g.lines.some(l=>l.actual<l.qty),due=g.lines.filter(l=>l.actual<l.qty&&!l.claimed);
      const rated=g.lines.every(l=>l.rating==null),ref=g.group?{group:g.id}:{order:o.id};
      let act='';
      if(due.length&&!shorts.some(l=>due.includes(l)))act+=cmdBtn('Khiếu nại phần thiếu','inv_claim',ref,'small cream');  // recent ones: the card on top
      if(rated)act+=`<div class="row wrap rate-row" role="group" aria-label="Đánh giá ${esc(s?.name||'')}">${[1,2,3,4,5].map(n=>cmdBtn('★'.repeat(n),'inv_rate',{...ref,stars:n,note:''},'ghost small')).join('')}</div>`;
      if(o.reply)act+=`<p class="bubble small"><b>${esc(s?.name||'')}:</b> ${esc(o.reply)}</p>`;
      const got=g.lines.reduce((n,l)=>n+l.actual,0),of=g.lines.reduce((n,l)=>n+l.qty,0);
      const title=g.group?`🛒 Đơn gộp ${g.lines.length} món · nhận ${got}/${of}`:`${name(i)}${sizeNote(o)} · nhận ${o.actual}/${o.qty}`;
      const list=g.group?`<p class="inv-gnames">${g.lines.map(l=>`${esc(byId[l.item]?.emoji||'📦')} ${esc(byId[l.item]?.name||l.item)}${sizeNote(l)} ${l.actual}/${l.qty}`).join(' · ')}</p>`:'';
      return `<article class="card order-row"><div class="row spread"><div><strong>${title}</strong><small class="muted block">${esc(s?.emoji||'')} ${esc(s?.name||'')} · ${fmt(paidOf(g))} xu · ngày ${o.day}</small></div>${short?pill(due.length?'GIAO THIẾU':'ĐÃ HOÀN TIỀN','amber'):o.rating?pill(stars(o.rating),'amber'):''}</div>${list}${act}</article>`;};
    const done=shipments(orders.filter(o=>o.status==='received').reverse()).slice(0,10);
    body=(transitS.length?`<h4 class="section-title">🚚 Đang giao</h4>${transitS.map(waiting).join('')}`:'')+
      (done.length?`<h4 class="section-title">Đã nhận gần đây</h4>${done.map(received).join('')}`:'')||(ready.length?'':nothing());
  }else{
    const lots=inv.lots.filter(l=>l.qty>0&&l.expires>=c.day).sort((a,b)=>a.expires-b.expires||a.received-b.received);
    body=lots.length?`<div class="inv-lots">${lots.map(l=>{const i=byId[l.item]||{name:l.item},left=l.expires-c.day+1;
      const tag=l.expires>=900?pill('không hạn',''):left<=1?pill('hết hạn tối nay','danger'):left===2?pill('còn 2 ngày','amber'):pill(`còn ${left} ngày`,'');
      return `<div class="inv-lot"><span class="inv-lot-name">${name(i)}</span><span class="inv-lot-qty"><b>${l.qty}</b> ${esc(unit(i))}</span>${tag}${confirmCmd('Bỏ lô','inv_discard',{lot:l.id},`Bỏ ${l.qty} ${unit(i)} ${i.name}? Giá trị được ghi vào hao hụt.`,'ghost small')}</div>`;}).join('')}</div>`+
      `<p class="muted small space-top">Vào trước dùng trước: lô hết hạn sớm nhất được lấy trước. Lô hết hạn được ghi hao hụt khi khép ca.</p>`:nothing();
  }
  const place=api.content.catalogue.find(x=>x.id===api.state.current)?.place||'';
  // "?" → the illustrated "Nhập hàng & xếp kệ" page, where the workplace has one (tutorial/guide-data.js).
  const help=(GUIDE[api.state.current]?.pages||[]).some(p=>p.id==='restock')?`<button type="button" class="icon-btn tut-help" data-action="tutGuide" data-career="${esc(api.state.current)}" data-tab="work" data-page="restock" aria-label="Cách nhập hàng & xếp kệ">?</button>`:'';
  return head('Kho & nhập hàng',`Mỗi loại chứa tối đa ${cap}`,'KHO · '+esc(place)).replace('<button class="icon-btn" type="button" data-action="close"',help+'<button class="icon-btn" type="button" data-action="close"')+
    `<div class="sheet-body"><details class="inv-how"><summary>❔ Nhập hàng thế nào?</summary><p class="small muted">📦 Đặt hàng → chờ thùng về → mở thùng, chạm đếm từng món → nhận lên kệ: lúc đó mới bán được.</p></details>${hint}${strip}${door}${shortBox}${tabs([['stock','Kệ hàng'],['orders',`Thùng hàng${transitS.length?` · ${transitS.length}`:''}`],['lots','Hạn dùng']],tab,'v4InvTab').replace('class="pill-tabs"','class="pill-tabs inv-tabs"')}<div class="space-top">${body}</div></div>`;
}
/** Order card: stepper + quick chips (never past the room left), suppliers,
 * a live total (wholesale tier and shipping included) and the reason when ordering is not
 * possible. "🛒 Thêm vào đơn" puts the line in the supplier's draft; "Đặt ngay" ships it alone. */
function orderCard(env,pick,{cap,stock,on,space,unit,name}){
  const {api,ui}=env,c=api.state.careers[api.state.current],sups=supplierList(env),carts=c.inventory?.carts||[];
  const sup=pickSupplier(env,pick.id),max=Math.min(30,space);
  const sizes=c.inventory?.sizes?.[pick.id]||[],chosen=orderSize(env,pick.id);
  const sizePicker=sizes.length?`<fieldset class="space-top"><legend class="field">Chọn size nhập</legend><div class="chip-row" role="group" aria-label="Size nhập ${esc(pick.name)}">${[null,...sizes].map(s=>`<button type="button" class="btn small ${chosen===s?'primary':'ghost'}" data-action="v4OrderSize" data-item="${esc(pick.id)}" data-size="${esc(s||'')}" aria-pressed="${chosen===s}">${s?`Size ${esc(s)}`:'Tự chia size'}</button>`).join('')}</div><p class="small muted">${chosen?`Toàn bộ số hàng thực nhận sẽ vào size ${esc(chosen)}.`:'Tự chia ưu tiên các size bán chạy. Chọn một size nếu đang thiếu đúng cỡ đó.'}</p></fieldset>`:'';
  // First suggestion: up to 10, never past the room left or what the till can pay.
  const afford=Math.floor(c.money/Math.max(1e-9,pick.cost*sup.factor)),qty=Math.max(1,Math.min(max||1,ui.orderQty||Math.min(10,max||1,Math.max(1,afford))));
  const q=orderQuote(pick,qty,sup),cost=q.total;
  const fn=fundName(api.state.current);
  const why=!space?'Kệ đã đầy (tính cả hàng đang giao).':vans(c.inventory).full?`${vansLine(c.inventory)}: nhận bớt thùng rồi đặt tiếp.`:cost>c.money?`${fn} còn ${fmt(c.money)} xu, thiếu ${fmt(cost-c.money)} xu.`:'';
  const chips=[5,10].filter(n=>n<max).map(n=>`<button type="button" class="chip ${n===qty?'selected':''}" data-action="v4Qty" data-set="${n}">${n}</button>`).join('')+(max?`<button type="button" class="chip ${qty===max?'selected':''}" data-action="v4Qty" data-set="${max}">${space<=30?'Đầy kệ':'Tối đa'} · ${max}</button>`:'');
  const cheapest=Math.min(...sups.filter(x=>sells(x,pick.id)).map(x=>x.factor));
  const priceWord=x=>`${x.factor===cheapest&&x.factor<1?'rẻ nhất':x.factor<1?'rẻ hơn':x.factor>1?'đắt hơn':'giá niêm yết'} ×${String(x.factor).replace('.',',')}`;
  // Suppliers as compact chips (name, when, price); the chosen one's terms and notes sit in a fold under them.
  const supplier=x=>{const ok=sells(x,pick.id),on=ok&&x.id===sup.id,k=carts.find(k=>k.supplier===x.id);
    return `<button type="button" class="choice inv-sup ${on?'selected':''}" data-action="v4Supplier" data-supplier="${esc(x.id)}" aria-pressed="${on}"${ok?'':' disabled'}><strong>${esc(x.emoji)} ${esc(x.name)}${k?` <span class="inv-badge" aria-label="đơn đang soạn ${k.lines.length} món">🛒 ${k.lines.length}</span>`:''}</strong>`+
      `<small>${ok?`<b>${esc(x.quote?.label||x.window||'')}</b> · ×${String(x.factor).replace('.',',')}`:'Không bán mặt hàng này'}</small></button>`;};
  const supMore=x=>{const notes=[priceWord(x),x.short>=15?'hay thiếu hàng':'',x.late>=12?'hay trễ hẹn':'',x.fresh?`tươi thêm ${x.fresh} ngày`:'',x.rating?`${x.rating}★`:''].filter(Boolean).join(' · ');
    const terms=x.free_from!=null?[x.ship?`ship ${x.ship} xu (miễn từ ${x.free_from})`:'',(x.bulk||[]).length?`sỉ từ ${x.bulk[0][0]}: −${x.bulk[0][1]}%`:''].filter(Boolean).join(' · '):'';
    return `<details class="inv-sup-more"><summary>${esc(x.emoji)} ${esc(x.name)}: giờ giao & điều kiện</summary><p class="small">${x.kind==='rush'||!x.window?'':`${esc(x.window)} · `}${esc(notes)}</p>${terms?`<p class="small">${esc(terms)}</p>`:''}${x.note?`<p class="small muted">${esc(x.note)}</p>`:''}</details>`;};
  const k=carts.find(k=>k.supplier===sup.id),inDraft=k?.lines.find(l=>l.item===pick.id)?.qty||0;
  // A full draft takes no new line (inv_cart): the button opens that draft to place it instead.
  const lineCap=Number(c.inventory?.cart_lines)||8,cartFull=!!k&&!inDraft&&k.lines.length>=lineCap;
  const tier=q.pct?`<span class="tag green">sỉ −${q.pct}%</span>`:q.tier&&q.tier[0]<=max?`<button type="button" class="chip inv-tier" data-action="v4Qty" data-set="${q.tier[0]}">Lấy ${q.tier[0]}: −${q.tier[1]}%</button>`:'';
  const ship=sup.free_from==null?'':q.ship?`Hàng ${fmt(q.cost)} + ship ${fmt(q.ship)} xu`:`Hàng ${fmt(q.cost)} xu · miễn ship`;
  return `<section class="card order-card inv-order" aria-label="Nhập ${esc(pick.name)}"><div class="row spread"><h3>Nhập ${name}</h3>${button(icon('x',14),'v4Order',{item:''},'ghost small')}</div>`+
    `<p class="inv-facts"><span>Trên kệ <b>${stock}</b></span><span>Đang giao <b>${on}</b></span><span>Còn chỗ <b>${space}</b></span>${vansLine(c.inventory)?`<span>${vansLine(c.inventory)}</span>`:''}<span>Giá gốc <b>${pick.cost}</b> xu/${esc(unit)}</span>${pick.life?`<span>Dùng trong <b>${pick.life}</b> ngày</span>`:''}</p>`+
    sizePicker+`<label class="field" for="order-qty">Số lượng</label><div class="inv-qty"><div class="inv-stepper"><button type="button" class="btn ghost" data-action="v4Qty" data-step="-1" aria-label="Bớt một"${qty<=1?' disabled':''}>−</button><input id="order-qty" class="input" type="number" inputmode="numeric" min="1" max="${Math.max(1,max)}" value="${qty}" data-v4-qty aria-describedby="order-total"><button type="button" class="btn ghost" data-action="v4Qty" data-step="1" aria-label="Thêm một"${qty>=max?' disabled':''}>+</button></div><span class="chip-row">${chips}</span></div>`+
    // The bill right under the number you choose: total, what the fund keeps, and why it cannot go yet.
    `<div class="inv-total inv-bill"><div class="grow"><strong id="order-total" data-cost="${pick.cost}" data-factor="${sup.factor}" data-terms="${esc(JSON.stringify({bulk:sup.bulk||[],ship:sup.ship,free_from:sup.free_from}))}" data-money="${c.money}" data-fund="${esc(fn)}" data-shelf="${stock+on}" data-cap="${cap}" data-max="${max}">Tổng: ${fmt(cost)} xu</strong> <span id="order-tier">${tier}</span><small class="block inv-after" id="order-after">${esc(fn)} còn ${fmt(Math.max(0,c.money-cost))} xu · kệ sau khi nhận ${stock+on+qty}/${cap}</small><small class="block" id="order-ship">${esc(ship)}</small><small class="block" id="order-eta">Dự kiến nhận: <b>${esc(sup.quote?.eta_label||sup.window||'')}</b></small><small class="danger-text block" id="order-why" role="status">${esc(why)}</small></div></div>`+
    `<label class="field">Nhà cung cấp</label><div class="inv-sups">${sups.map(supplier).join('')}</div>${supMore(sup)}`+
    `<div class="inv-order-go inv-order-foot">${cartFull?`<button type="button" class="btn" id="cart-add" data-action="v4Cart" data-supplier="${esc(sup.id)}" data-open="1">🛒 Đơn đủ ${lineCap} món · xem & đặt</button>`:`<button type="button" class="btn" id="cart-add" data-action="v4CartAdd" data-item="${esc(pick.id)}"${!space||inDraft>=Math.min(30,space)?' disabled':''}>🛒 Thêm vào đơn${k?` · ${k.lines.length+(inDraft?0:1)}`:''}</button>`}<button type="button" class="btn primary" id="order-go" data-action="v4OrderGo" data-item="${esc(pick.id)}"${why?' disabled':''}>${icon('truck',15)} Đặt ngay</button></div>`+
    `${cartFull?`<small class="danger-text block" role="status">Đơn ${esc(sup.name)} đủ ${lineCap} món: đặt đơn đó trước, hoặc “Đặt ngay” riêng món này.</small>`:''}<p class="muted small">Trả tiền khi đặt. Gộp nhiều món một đơn (tối đa ${lineCap} món): một lần ship. Hàng vào kệ sau khi bạn mở thùng và đếm đúng.</p></section>`;
}
/** A supplier's draft (đơn gộp): lines with −/+ and a wholesale hint, subtotal, savings, shipping,
 * the haggled discount, the total, what the fund lacks, then ONE "Đặt đơn". Server-priced (inventory.cart_view). */
function cartCard(env,k,{byId,unit}){
  const {api}=env,s=supplierList(env).find(x=>x.id===k.supplier)||{name:k.supplier,emoji:'🛒'},fn=fundName(api.state.current),sid=k.supplier;
  const qtyBtn=(l,q,label,aria,dis=false)=>`<button type="button" class="btn ghost" data-action="v4CartQty" data-supplier="${esc(sid)}" data-item="${esc(l.item)}" data-qty="${q}" aria-label="${esc(aria)}"${dis?' disabled':''}>${label}</button>`;
  const line=l=>{const i=byId[l.item]||{name:l.item},max=Math.min(30,l.room);
    const tag=l.oos?pill('Hết hàng hôm nay','danger'):l.bulk?pill(`sỉ −${l.bulk}%`,'green'):l.next_tier&&l.next_tier[0]<=max?`<button type="button" class="chip inv-tier" data-action="v4CartQty" data-supplier="${esc(sid)}" data-item="${esc(l.item)}" data-qty="${l.next_tier[0]}">Lấy ${l.next_tier[0]}: −${l.next_tier[1]}%</button>`:'';
    return `<li class="inv-cl${l.oos?' oos':''}"><span class="inv-cl-name"><span aria-hidden="true">${esc(i.emoji||'📦')}</span> <b>${esc(i.name)}${l.size?` · size ${esc(l.size)}`:''}</b>${tag?`<span class="inv-cl-tag">${tag}</span>`:''}</span>`+
      `<span class="inv-cl-qty">${qtyBtn(l,l.qty-1,'−',`Bớt một ${i.name}`)}<b aria-label="${l.qty} ${esc(unit(i))}">${l.qty}</b>${qtyBtn(l,l.qty+1,'+',`Thêm một ${i.name}`,l.qty>=max)}</span>`+
      `<b class="inv-cl-amt">${l.oos?'—':fmt(l.cost)}</b>${qtyBtn(l,0,icon('x',14),`Bỏ ${i.name} khỏi đơn`).replace('class="btn ghost"','class="icon-btn inv-cl-x"')}</li>`;};
  const rows=[];
  if(k.bulk_off||k.off)rows.push(['Tiền hàng',fmt(k.full)]);
  if(k.bulk_off)rows.push(['Giá sỉ',`−${fmt(k.bulk_off)}`]);
  if(k.off)rows.push([`Bớt ${k.pct}%`,`−${fmt(k.off)}`]);
  rows.push(['Ship',k.ship?fmt(k.ship):'Miễn phí']);
  const sum=`<dl class="inv-cart-sum">${rows.map(([a,b])=>`<div><dt>${esc(a)}</dt><dd>${esc(b)}</dd></div>`).join('')}<div class="total"><dt>Tổng</dt><dd>${fmt(k.total)} xu</dd></div></dl>`;
  const d=k.deal,talk=d?`<p class="bubble small"><b>${esc(s.name)}:</b> “${esc(d.said)}”</p>${d.lost?'<small class="warn-text block">Đơn nhỏ lại: giá bớt không còn.</small>':''}`
    :k.can_haggle?`<div class="inv-haggle" role="group" aria-label="Xin bớt"><span>💬 Xin bớt</span>${k.asks.map(p=>cmdBtn(`${p}%`,'inv_haggle',{supplier:sid,pct:p},'chip')).join('')}</div>`
    :!k.asked&&k.n?`<small class="muted block">💬 Đơn từ ${fmt(k.haggle_from)} xu được xin bớt</small>`:'';
  const why=!k.n?'Cả đơn đang hết hàng hôm nay.':k.below_min?`${s.name} nhận đơn gộp từ ${fmt(k.min_order)} xu (còn thiếu ${fmt(k.below_min)} xu hàng).`:k.short?`${fn} thiếu ${fmt(k.short)} xu.`:vans(api.state.careers[api.state.current]?.inventory).full?`Đủ ${vans(api.state.careers[api.state.current]?.inventory).cap} đơn đang về: nhận bớt thùng rồi đặt tiếp.`:'';
  return `<section class="card inv-cart" aria-label="Đơn gộp ${esc(s.name)}"><div class="row spread"><h3>🛒 Đơn gộp · ${esc(s.emoji||'')} ${esc(s.name)}</h3>${button(icon('x',14),'v4Cart',{supplier:''},'ghost small')}</div>`+
    `<ul class="inv-cart-lines">${k.lines.map(line).join('')}</ul>${sum}`+
    `${k.to_free?`<small class="muted block">Thêm ${fmt(k.to_free)} xu hàng: miễn ship</small>`:''}${talk}`+
    `<small class="block inv-cart-eta">Dự kiến: <b>${esc(k.quote?.label||'')}</b> · một chuyến</small>${why?`<small class="danger-text block" role="status">${esc(why)}</small>`:''}`+
    `<div class="inv-order-go">${confirmCmd('Bỏ đơn','inv_cart',{supplier:sid,op:'clear'},`Bỏ cả đơn ${s.name}?`,'ghost')}<button type="button" class="btn primary" id="cart-go" data-action="v4CartGo" data-supplier="${esc(sid)}"${why?' disabled':''}>${icon('truck',15)} Đặt đơn · ${fmt(k.total)} xu</button></div></section>`;
}
/** The career's suppliers with live quotes (older servers: the shared list). */
function supplierList(env){const {api}=env,c=api.state.careers[api.state.current];return c.inventory?.suppliers?.length?c.inventory.suppliers:(api.content.inventory.by_career?.[api.state.current]||api.content.inventory.suppliers);}
function sells(x,item){return !Array.isArray(x?.items)||x.items.includes(item);}
/** The chosen supplier if it sells the item, else the distributor, else the first that does. */
function pickSupplier(env,item){const sups=supplierList(env),want=sups.find(x=>x.id===(env.ui.orderSupplier||(env.ui.orderRush?'express':'partner')));
  return want&&sells(want,item)?want:sups.find(x=>x.id==='partner'&&sells(x,item))||sups.find(x=>sells(x,item))||sups[0];}
function groupName(g){return {base:'Nguyên liệu chính',pack:'Bao bì',sauce:'Sốt',broth:'Nước dùng',topping:'Topping',flower:'Hoa',filler:'Lá & hoa phụ',wrap:'Giấy gói & ruy băng',supply:'Vật tư',goods:'Hàng hóa',tool:'Dụng cụ',part:'Linh kiện',seed:'Hạt giống',feed:'Thức ăn',product:'Sản phẩm',ingredient:'Nguyên liệu',drink:'Đồ uống',bake:'Bánh',room:'Phòng',care:'Chăm sóc',coffee:'Cà phê',dry:'Hàng khô',fridge:'Tủ mát',milk:'Sữa',bike:'Xe đạp',cooker:'Nồi cơm',fan:'Quạt',headphone:'Tai nghe',laptop:'Máy tính',phone:'Điện thoại'}[g]||g;}

/* ------------------------------------------------------------ Feedback */
/** Reviews: big average, 5★→1★ bars (tap to filter), chips, cards with a reply
 * entry, and the thread. Wide sheets show list + thread side by side; narrow
 * sheets show one at a time with a back button. */
export function feedbackView(env){
  if(typeof document!=='undefined'&&!document.querySelector('link[data-reviews-css]')){const l=document.createElement('link');l.rel='stylesheet';l.href=asset('/css/reviews.css');l.dataset.reviewsCss='1';document.head.append(l);}
  const {api,ui}=env,c=api.state.careers[api.state.current];
  // Removed (reported) reviews stay in the list, struck through, but never count.
  const all=c.feed.filter(p=>p.stars||p.feedback?.removed),rated=all.filter(p=>p.stars),count=rated.length;
  const open=rated.filter(p=>p.feedback?.status==='open').length;
  const odd=p=>p.stars&&p.feedback?.clues?.length&&!p.feedback.report,flagged=rated.filter(odd).length;
  const filter=['open','flag'].includes(ui.fbFilter)?ui.fbFilter:'all',starF=Number(ui.fbStars)||0;
  const rows=all.filter(p=>(filter==='all'||(filter==='open'?p.feedback?.status==='open':odd(p)))&&(!starF||p.stars===starF));
  const selected=all.find(p=>p.id===ui.fbPost),shown=selected||rows[0];
  const dist=[5,4,3,2,1].map(s=>[s,rated.filter(p=>p.stars===s).length]),max=Math.max(1,...dist.map(d=>d[1]));
  const place=api.content.catalogue.find(x=>x.id===api.state.current)?.place||'';
  const avg=c.rating?Number(c.rating).toFixed(1):'—';
  // Chùa Gió Lành: visitors' impressions, not a shop's reviews (game/pagoda_voice.py); same stars and data.
  const pagoda=api.state.current==='pagoda',word=pagoda?'cảm nhận':'đánh giá';
  const summary=`<section class="rv-summary"><div class="rv-score"><strong>${avg}</strong><span class="stars" aria-hidden="true">${stars(Math.round(c.rating||0))||'☆☆☆☆☆'}</span><small>${count} ${word}</small></div><div class="rv-dist">${dist.map(([s,n])=>`<button type="button" class="rv-bar ${starF===s?'active':''}" data-action="v4FbStars" data-stars="${s}" aria-pressed="${starF===s}" aria-label="Lọc đánh giá ${s} sao: ${n}"><span>${s}★</span><i><em style="width:${Math.round(n/max*100)}%"></em></i><b>${n}</b></button>`).join('')}</div></section>`;
  const chips=`<div class="chip-row rv-chips"><button type="button" class="chip ${filter==='all'&&!starF?'selected':''}" data-action="v4FbFilter" data-tab="all">Tất cả · ${count}</button><button type="button" class="chip ${filter==='open'?'selected':''}" data-action="v4FbFilter" data-tab="open">${pagoda?'Cần hồi đáp':'Cần trả lời'} · ${open}</button>${flagged||filter==='flag'?`<button type="button" class="chip ${filter==='flag'?'selected':''}" data-action="v4FbFilter" data-tab="flag">${icon('flag',12)} Đáng ngờ · ${flagged}</button>`:''}${starF?`<button type="button" class="chip selected" data-action="v4FbStars" data-stars="${starF}" aria-label="Bỏ lọc ${starF} sao">${starF}★ ${icon('x',12)}</button>`:''}</div>`;
  const st=c.feedback_stats||{criteria:[]};
  const crit=st.criteria?.length?`<details class="rv-criteria"><summary>Điểm theo tiêu chí</summary>${st.criteria.map(x=>`<div class="crit"><small>${esc(x.label)}</small><div class="bar ${x.avg<=3?'low':''}"><i style="width:${x.avg*20}%"></i></div><b>${x.avg}</b></div>`).join('')}${st.improved?`<p class="muted small">${pagoda?`${st.improved} lần khách thập phương sửa sao lên sau khi đọc lời chùa hồi đáp.`:`${st.improved} lần khách sửa sao lên sau khi bạn trả lời.`}</p>`:''}</details>`:'';
  const parent=api.state.current==='teacher';
  const card=p=>{const f=p.feedback,s=f?.status;
    const tag=!f?'':f.removed?pill('Đã gỡ',''):s==='awaiting'?pill('Đang đọc…','blue'):s==='open'?`<span class="rv-reply">${icon('chat',13)} ${f.thread.some(x=>x.role==='owner')?'Khách hỏi lại':pagoda?'Hồi đáp':'Trả lời'}</span>`:f.ignored?pill('Đã bỏ qua',''):f.report==='rejected'?pill('Báo cáo bị từ chối','danger'):p.stars&&f.stars_original&&p.stars>f.stars_original?pill(`Đã sửa ★${f.stars_original} → ★${p.stars}`,'green'):f.thread.some(x=>x.role==='owner')?pill(pagoda?'Đã hồi đáp':'Đã trả lời','green'):'';
    const flags=f?.clues?.length&&!f.removed?`<span class="rv-flags">${f.clues.map(x=>`<span class="tag amber">${icon('flag',11)} ${esc(x)}</span>`).join('')}</span>`:'';
    // The latest exchange (your reply, then what the reviewer did) right under the quote.
    const peek=f&&!f.removed?rvBoxes(p,parent,true,pagoda).filter(x=>x.role!=='guest').slice(-2).map(x=>x.html).join(''):'';
    return `<button type="button" class="rv-card ${p.id===shown?.id?'active':''}${f?.removed?' removed':''}" data-action="v4FbOpen" data-post="${esc(p.id)}"><span class="persona ck-avatar" aria-hidden="true">${esc(f?.persona_emoji||'🙂')}</span><span class="grow"><span class="ck-meta"><b>${esc(p.author)}</b><small>Ngày ${p.day}</small></span>${p.stars?`<span class="stars ck-stars" aria-label="${p.stars} sao">${stars(p.stars)}</span>`:''}<span class="rv-text${p.stars&&p.stars<=2?' low':''}"><b class="rv-who">${parent?'Phụ huynh':pagoda?'Khách thập phương':'Khách'}</b> “${esc(p.text)}”</span>${flags}${peek?`<span class="rv-peek">${peek}</span>`:''}${f?.title||tag?`<span class="rv-foot">${f?.title?`<small>${esc(f.title)}</small>`:''}${tag}</span>`:''}</span></button>`;};
  const list=all.length?rows.map(card).join('')||`<p class="muted small rv-none">Không có ${word} nào ở mục này.</p>`:`<div class="empty">${icon('star',30)}<h3>Chưa có ${word} nào</h3></div>`;
  const body=all.length?`<div class="fb-layout ${selected?'has-detail':''}"><section class="fb-list">${summary}${chips}<div class="stack rv-list">${list}</div>${crit}</section><section class="fb-detail ${selected?'':'auto'}">${shown?threadView(shown,env):''}</section></div>`:list;
  return head(pagoda?'Cảm nhận của khách thập phương':'Đánh giá',esc(place),pagoda?'LỜI KHÁCH THẬP PHƯƠNG':'PHẢN HỒI')+`<div class="sheet-body">${body}</div>`;
}
function orderSize(env,item){
  const sizes=env.api.state.careers[env.api.state.current]?.inventory?.sizes?.[item]||[],value=env.ui.orderSize?.[item];
  return sizes.includes(value)?value:null;
}
function threadView(p,env){
  const f=p.feedback,api=env.api,aiOn=api.state.settings.aiConsent&&api.ai?.configured;
  const parent=api.state.current==='teacher',pagoda=api.state.current==='pagoda';
  const back=`<button type="button" class="btn ghost small rv-back" data-action="v4FbBack">${icon('back',14)} ${pagoda?'Tất cả cảm nhận':'Tất cả đánh giá'}</button>`;
  const sub=[f?.persona_name,f?.title].filter(Boolean).map(esc).join(' · ');
  const top=`<div class="row rv-head"><span class="persona big ck-avatar" aria-hidden="true">${esc(f?.persona_emoji||'🙂')}</span><div class="grow"><div class="ck-meta"><h3>${esc(p.author)}</h3><small>Ngày ${p.day}</small></div><div>${p.stars?`<span class="stars ck-stars" aria-label="${p.stars} sao">${stars(p.stars)}</span>`:''}${f&&p.stars&&p.stars!==f.stars_original?` <small class="muted">ban đầu ${f.stars_original}★</small>`:''}</div>${sub?`<small class="rv-sub">${sub}</small>`:''}</div></div>`;
  const quote=`<p class="ck-box review-text"><b class="ck-label rv-who">👤 ${parent?'Phụ huynh':pagoda?'Khách thập phương':'Khách'}</b> “${esc(p.text)}”</p>`;
  if(!f)return `<article class="card review-card">${back}${top}${quote}</article>`;
  const offered=f.thread.some(x=>x.role==='owner'&&x.offer&&x.offer!=='none');
  const crit=f.criteria.map(x=>`<div class="crit"><small>${esc(x.label)}</small><div class="bar ${x.score<=3?'low':''}"><i style="width:${x.score*20}%"></i></div><b>${x.score}</b>${x.note?`<small class="muted">${esc(x.note)}</small>`:''}</div>`).join('');
  const thread=rvBoxes(p,parent,false,pagoda).map(x=>x.html).join('');
  const canReply=f.status==='open'&&f.rounds<3;
  // Ready-made tones: the words decide what the reviewer does next.
  const worst=f.unfair?f.unfair.truth:(f.criteria.reduce((a,b)=>b.score<a.score?b:a,f.criteria[0])||{}).note||'';
  const tpl=parent?[['Nêu sự thật',`Dạ, theo sổ lớp hôm đó: ${worst}. Mong phụ huynh xem lại giúp ạ.`],['Xin lỗi','Cảm ơn phụ huynh đã góp ý. Tôi xin lỗi và sẽ điều chỉnh cách làm trong lớp ạ.'],['Mời trao đổi','Mời phụ huynh ghé lớp trao đổi trực tiếp, mình cùng giúp con nhé.'],['Đáp trả gắt','Phụ huynh không hài lòng thì chuyển lớp khác đi.']]
    :pagoda?[['Nêu sự thật',`Dạ, sổ chùa hôm đó ghi: ${worst}. Chùa gửi lại để mình cùng xem cho rõ ạ.`],['Xin lỗi','A Di Đà Phật, chùa xin lỗi vì còn thiếu sót. Thầy trụ trì đã nhắc lại cả chùa, lần sau sẽ cẩn thận hơn ạ.'],['Mời ghé lễ','Cảm ơn bác đã góp ý. Rằm tới mời bác ghé lễ, chùa sẽ đón tiếp chu đáo hơn ạ.'],['Đáp trả gắt','Không vừa ý thì đi chùa khác, ở đây không cần.']]
    :[['Nêu sự thật',`Dạ, theo phiếu ghi hôm đó: ${worst}. Bên mình gửi lại để cùng đối chiếu ạ.`],['Xin lỗi','Thành thật xin lỗi bạn vì trải nghiệm chưa tốt. Lần sau bên mình sẽ chú ý hơn và sửa quy trình ngay ạ.'],['Mời quay lại','Cảm ơn bạn đã ghé và góp ý. Mời bạn quay lại, bên mình sẽ phục vụ chu đáo hơn ạ.'],['Đáp trả gắt','Không thích thì đi chỗ khác, bên mình không tiếp loại khách như bạn.']];
  const tone=env.ui.fbTone?.post===p.id?env.ui.fbTone.tone:'free';
  const tplRow=f.tones?.length?`<div class="rv-tones" role="group" aria-label="Chọn giọng trả lời">${f.tones.map(t=>`<button type="button" class="rv-tone ${esc(t.risk)}${t.id===tone?' selected':''}" data-action="v4FbTpl" data-tone="${esc(t.id)}" data-text="${esc(t.text)}" aria-pressed="${t.id===tone}"><span aria-hidden="true">${esc(t.emoji)}</span><span class="rv-tone-txt"><b>${esc(t.label)}</b>${t.risk==='risky'?'<small>được ăn cả, ngã về không</small>':t.risk==='bad'?'<small>dễ bị chụp màn hình</small>':''}</span></button>`).join('')}<button type="button" class="rv-tone free${tone==='free'?' selected':''}" data-action="v4FbTpl" data-tone="free" data-text="" aria-pressed="${tone==='free'}"><span aria-hidden="true">✍️</span><b>Tự viết</b></button></div>`
    :`<div class="chip-row rv-tpl" role="group" aria-label="Gợi ý giọng trả lời">${tpl.map(([l,t],i)=>`<button type="button" class="chip${i===3?' rv-tpl-rude':''}" data-action="v4FbTpl" data-text="${esc(t)}">${l}</button>`).join('')}</div>`;
  const clues=f.clues?.length&&!f.report?`<div class="rv-clues" role="note">${icon('flag',14)}<div class="rv-flags">${f.clues.map(x=>`<span class="tag amber">${esc(x)}</span>`).join('')}</div></div>`:'';
  const reportQ=parent?'Báo cáo tin nhắn này với ban đại diện lớp? Chỉ tin nhắn nhầm lớp hoặc giả mới bị gỡ. Nếu là góp ý thật, phụ huynh sẽ biết và bực hơn.':pagoda?'Báo cáo cảm nhận này là giả hoặc nhầm chỗ? Chỉ cảm nhận giả, nhầm chỗ hoặc của người chưa lên chùa mới bị gỡ. Nếu là cảm nhận thật, khách sẽ biết và hạ thêm sao.':'Báo cáo đánh giá này là giả hoặc nhầm quán? Nền tảng chỉ gỡ đánh giá giả, nhầm chỗ hoặc chưa dùng dịch vụ. Nếu là trải nghiệm thật, khách sẽ biết và hạ thêm sao.';
  const policeQ='Lưu đánh giá và cuộc trao đổi làm bằng chứng, trình báo lời đe dọa đòi tiền trong game? Trao đổi trực tiếp sẽ khép; điểm đánh giá vẫn giữ nguyên.';
  const side=(f.can_report||f.can_ignore||f.can_police)?`<div class="row wrap rv-actions">${f.can_ignore?cmdBtn(`${icon('check',14)} Bỏ qua`,'fb_ignore',{post:p.id},'ghost small'):''}${f.can_police?confirmCmd('🚓 Lưu bằng chứng & trình báo','fb_police',{post:p.id},policeQ,'cream small'):''}${f.can_report?confirmCmd(`${icon('flag',14)} Báo cáo`,'fb_report',{post:p.id},reportQ,'ghost small'):''}</div>`:'';
  const verdict=f.removed?`<p class="notice green" role="status">${icon('check',16)} Đã gỡ${f.kind_label?`: ${esc(f.kind_label)}`:''}. Không còn tính vào điểm trung bình.</p>`:f.report==='rejected'?`<p class="notice amber" role="status">${icon('flag',16)} Báo cáo bị từ chối${f.kind_label?` (${esc(f.kind_label)})`:''}: đây là trải nghiệm thật.</p>`:'';
  const police=f.police?`<details class="fact-check"><summary>🚓 Đã trình báo trong game · ngày ${f.police.day}</summary><p class="small">Đã lưu lời đe dọa và ${f.police.thread.length} lượt trao đổi làm bằng chứng. Hồ sơ giữ nguyên điểm đánh giá, không bảo đảm gỡ sao.</p><blockquote>${esc(f.police.text)}</blockquote></details>`:'';
  const choice=offered?'none':(env.ui.fbOffer||'none');
  // Nothing is paid at the pagoda, so there is nothing to give back: a cup of tea or a vegetarian gift only.
  const offers=offered?[['none','Không bù']]:[['none','Không bù'],...(pagoda?['drink','gift']:['drink','gift','refund']).map(id=>[id,offerLabel(id,parent,true,pagoda)])];
  const form=canReply?`<form class="reply-box" data-v4-fb="${esc(p.id)}"><label class="field" for="fb-text">${pagoda?'Hồi đáp':'Trả lời'} ${esc(p.author)}</label>${tplRow}<input type="hidden" name="tone" value="${esc(tone)}"><textarea id="fb-text" class="input" rows="3" maxlength="600" data-preserve placeholder="${parent?'Cảm ơn, xin lỗi nếu cần, và nói rõ lớp sẽ làm gì…':pagoda?'A Di Đà Phật, cảm ơn, xin lỗi nếu cần, và nói rõ chùa sẽ làm gì…':'Cảm ơn, xin lỗi nếu cần, và nói rõ tiệm sẽ làm gì…'}" required></textarea>
    <div class="field">${pagoda?'Chút quà biếu':'Bù đắp'}</div><div class="segmented rv-offer" role="radiogroup" aria-label="${pagoda?'Chút quà biếu':'Bù đắp'}">${offers.map(([id,l])=>`<label><input type="radio" name="offer" value="${id}"${choice===id?' checked':''}><span>${l}</span></label>`).join('')}</div>
    <div class="row spread space-top"><small class="muted">Lượt ${f.rounds+1}/3</small><button class="btn primary" type="submit">${icon('send',14)} ${pagoda?'Gửi lời hồi đáp':'Gửi trả lời'}</button></div></form>`:
    f.status==='awaiting'?`<p class="notice blue">${icon('clock',16)} ${esc(p.author)} đang đọc trả lời của bạn…</p>`:f.removed||f.report?'':`<p class="rv-closed">${f.ignored?'Bạn đã bỏ qua đánh giá này.':f.own?'Nhận xét sau chuyến bay, không cần trả lời.':'Cuộc trao đổi đã khép.'}</p>`;
  // Chat 03/10: an edited review says so in words, not only with a small "ban đầu 1★".
  const edited=!f.removed&&p.stars&&f.stars_original&&p.stars!==f.stars_original?`<p class="notice ${p.stars>f.stars_original?'green':'amber'}" role="status">${icon('star',16)} ${parent?'Phụ huynh':pagoda?'Khách thập phương':'Khách'} đã sửa đánh giá: ★${f.stars_original} → ★${p.stars}</p>`:'';
  return `<article class="card review-card${f.removed?' removed':''}">${back}${top}${quote}${verdict}${police}${edited}${clues}${f.unfair?`<details class="fact-check"><summary>${icon('search',14)} Đối chiếu sự thật</summary><p class="small">Khách nói: <b>${esc(f.unfair.claim)}</b>. Sổ ghi: ${esc(f.unfair.truth)}. Bạn có thể nhắc lại dữ kiện một cách lịch sự.</p></details>`:''}
    <details class="criteria"><summary>${parent?'Phụ huynh chấm theo tiêu chí':pagoda?'Khách thập phương cảm nhận theo tiêu chí':'Khách chấm theo tiêu chí'}</summary>${crit}</details>${thread?`<div class="thread">${thread}</div>`:''}${form}${side}
    ${f.status==='open'&&f.thread.length?`<div class="row space-top">${cmdBtn('Khép trao đổi','fb_close',{post:p.id},'ghost small')}</div>`:''}</article>`;
}
const TONE_NAME={warm:'ấm áp',funny:'hài hước',sassy:'cà khịa',facts:'nêu sự thật',sorry:'xin lỗi',invite:'mời quay lại',process:'giải thích',genz:'Gen Z',silent:'ngắn gọn',harsh:'gắt'};
const PAGODA_TONE={warm:'từ tốn',funny:'tự trào',sassy:'đùa nhẹ',invite:'mời ghé lễ',process:'kể nếp chùa',genz:'trẻ trung'};
function offerLabel(id,parent,full=false,pagoda=false){
  const rows=parent?{drink:['kèm thêm một buổi','Kèm 1 buổi · 6 xu'],gift:['tặng sách 10 xu','Tặng sách · 10 xu'],refund:['hoàn 20 xu học phí','Hoàn 20 xu']}
    :pagoda?{drink:['mời chén trà 6 xu','Mời trà · 6 xu'],gift:['biếu quà chay 10 xu','Quà chay · 10 xu'],refund:['gửi lại 20 xu','Gửi lại 20 xu']}
    :{drink:['tặng quà nhỏ 6 xu','Quà nhỏ · 6 xu'],gift:['tặng voucher 10 xu','Voucher · 10 xu'],refund:['hoàn 20 xu','Hoàn 20 xu']};
  return (rows[id]||['',''])[full?1:0];}
function guestBubble(x,parent,pagoda=false){
  const side={fan:parent?'bênh lớp':pagoda?'bênh chùa':'bênh quán',troll:'hóng chuyện',other:parent?'phụ huynh khác':'khách khác'}[x.side]||'';
  const tint={fan:'ck-good',other:'ck-owner'}[x.side]||'ck-quiet';
  return `<div class="ck-box rv-guest ${tint}"><div class="ck-head"><b class="ck-label"><span aria-hidden="true">${esc(x.emoji||'💬')}</span> ${esc(x.name||'')}</b>${side?`<small class="ck-sub">${side}</small>`:''}</div><p>${esc(x.text)}</p></div>`;}
function decisionLabel(d,s){return {revise_up:`nâng lên ${s}★`,revise_down:`hạ xuống ${s}★`,argue:'muốn nói thêm',keep:'giữ nguyên'}[d]||d;}
const OFFER_COST={drink:6,gift:10,refund:20},OFFER_CHIP={drink:['Quà nhỏ','Kèm 1 buổi','Mời trà'],gift:['Voucher','Tặng sách','Quà chay'],refund:['Hoàn tiền','Hoàn tiền','Gửi lại']};
/** A review thread as boxes, one per voice: your reply (amber, with what you
 * gave as a red chip), the reviewer's answer (blue) with what it did to the
 * stars (+2★, −1★), and bystanders (quiet). Counted from the original stars. */
function rvBoxes(p,parent,inline=false,pagoda=false){
  const f=p.feedback;if(!f)return [];let now=f.stars_original||p.stars||0;
  // The chip (+1★, −6 xu…) sits on the label line so a clamped preview never hides it.
  const box=(cls,head,body,chip='')=>inline?`<span class="ck-box ${cls}"><span class="ck-head">${head}${chip}</span><span class="ck-p">${body}</span></span>`:`<div class="ck-box ${cls}"><div class="ck-head">${head}${chip}</div><p>${body}</p></div>`;
  return f.thread.map(x=>{
    if(x.role==='guest')return {role:'guest',html:guestBubble(x,parent,pagoda)};
    if(x.role==='owner'){
      const tone=x.tone&&TONE_NAME[x.tone]?`<small class="ck-sub">${pagoda&&PAGODA_TONE[x.tone]||TONE_NAME[x.tone]}</small>`:'';
      const cost=x.offer&&x.offer!=='none'&&OFFER_COST[x.offer]?`<span class="ck-delta down" title="${esc(offerLabel(x.offer,parent,false,pagoda))}">${OFFER_CHIP[x.offer][parent?1:pagoda?2:0]} · −${OFFER_COST[x.offer]} xu</span>`:'';
      return {role:'owner',html:box('ck-owner',`<b class="ck-label">👑 Bạn</b>${tone}`,esc(x.text),cost)};
    }
    let chip='';
    if((x.decision==='revise_up'||x.decision==='revise_down')&&x.stars){const d=x.stars-now;now=x.stars;chip=d?`<span class="ck-delta ${d>0?'up':'down'}" title="${esc(decisionLabel(x.decision,x.stars))}">${d>0?'+':'−'}${Math.abs(d)}★</span>`:`<span class="ck-delta flat">${decisionLabel(x.decision,x.stars)}</span>`;}
    else if(x.decision==='argue')chip=`<span class="ck-delta warn">${decisionLabel('argue')}</span>`;
    else if(x.decision==='keep')chip=`<span class="ck-delta flat">${decisionLabel('keep')}</span>`;
    return {role:'customer',html:box('ck-reply',`<b class="ck-label">💬 ${esc(p.author)}</b>`,esc(x.text),chip)};
  });
}

/* ----------------------------------------------------------- Situation */
export function situationView(env){
  const {api}=env,c=api.state.careers[api.state.current],x=c.situation;
  const list=api.content.situations?.[api.state.current]||[];
  if(!x){
    const practice=list.map(s=>`<article class="card sit-practice"><div class="grow"><strong>${esc(s.title)}</strong><small class="muted block">${s.tone==='tense'?'Căng thẳng':'Nhẹ nhàng'}${s.swap?' · có góc nhìn đổi vai':''}</small></div>${cmdBtn('Diễn tập','sit_practice',{script:s.id},'ghost small')}</article>`).join('');
    return head('Tình huống','','CHUYỆN TRONG CA')+`<div class="sheet-body"><div class="empty">${icon('sun',30)}<h3>Hôm nay chưa có chuyện gì</h3><div class="row center space-top">${button('Về quầy','close',{},'primary')}</div></div>${practice?`<h4 class="section-title">Diễn tập trước</h4><div class="stack">${practice}</div>`:''}</div>`;
  }
  const n=api.content.npcs.find(p=>p.id===x.npc);
  const facts=x.facts.map(f=>`<article class="fact ${f.text?'read':''}"><div class="row spread"><strong>${icon(f.text?'check':'search',14)} ${esc(f.title)}</strong><small class="muted">${esc(f.source)}</small></div>${f.text?`<p class="small">${esc(f.text)}</p>`:cmdBtn('Xem dữ kiện','sit_read',{fact:f.id},'ghost small')}</article>`).join('');
  let actions='';
  if(x.stage!=='resolved'){
    actions=`<h4 class="section-title">Bạn sẽ làm gì?</h4><div class="choice-grid">${x.options.map(o=>{const locked=(o.requires||[]).some(r=>!x.read.includes(r)),miss=x.practice?0:Math.max(0,(o.cost||0)-(c.money||0));return `<button class="choice ${x.choice===o.id?'selected':''}" data-command="sit_choose" data-payload="${esc(JSON.stringify({option:o.id}))}"${locked||miss?' disabled':''}><strong>${esc(o.label)}</strong><small>${o.cost?`Chi ${o.cost} xu`:''}${o.reward?` · +${o.reward} xu`:''}${locked?' · cần xem thêm dữ kiện':miss?` · thiếu ${miss} xu`:''}</small></button>`;}).join('')}</div>
      ${x.stage==='proposed'?`<div class="row space-top sit-foot">${confirmCmd(icon('check',14)+' Chốt cách xử lý','sit_confirm',{},'Chốt cách xử lý này? Kết quả sẽ ảnh hưởng tới khách, quan hệ và có thể cả đánh giá.','primary big')}</div>`:''}`;
  }else{
    actions=`<div class="outcome ${esc(x.quality)}"><span class="eyebrow">KẾT QUẢ</span><p>${esc(x.outcome)}</p></div>
      <h4 class="section-title">Mỗi người nhìn thấy điều gì</h4><div class="perspectives">${x.perspectives.map(v=>`<article class="perspective"><span class="p-emoji">${esc(v.emoji)}</span><div><b>${esc(v.who)}</b><p class="small">${esc(v.text)}</p></div></article>`).join('')}</div>
      ${x.lesson?`<p class="lesson">${icon('sparkle',15)} ${esc(x.lesson)}</p>`:''}<div class="row space-top sit-foot">${cmdBtn('Cất vào sổ','sit_dismiss',{},'primary big')}</div>`;
  }
  return head(esc(x.title),x.practice?'Diễn tập · không ảnh hưởng tiền, đánh giá hay quan hệ.':'',x.tone==='tense'?'TÌNH HUỐNG CĂNG':'CHUYỆN TRONG CA')+
   `<div class="sheet-body"><div class="situation"><div class="row sit-open">${n?portrait(n,48):''}<p class="opening grow">“${esc(x.opening)}”</p></div>${x.swap?`<details class="swap"><summary>${icon('people',14)} Thử đặt mình vào vị trí người kia</summary><p class="small">${esc(x.swap)}</p></details>`:''}
   <h4 class="section-title">Dữ kiện</h4><div class="facts">${facts}</div>${actions}</div></div>`;
}

/* ------------------------------------------------------------- Job hunt */
/** Hiring as data: each posting lists its stages (licence exam, CV, letter,
 * interview, situational test, hands-on trial). One card per step, a stepper
 * on top, and a result card that says what went right, what didn't, and when
 * you can try again. The server grades everything. */
const JOB_KIND={public:'CÔNG LẬP',community:'CỘNG ĐỒNG',corp:'DOANH NGHIỆP',startup:'KHỞI NGHIỆP',group:'TẬP ĐOÀN',firm:'CÔNG TY DỊCH VỤ',company:'CÔNG TY',branch:'CHI NHÁNH',service:'CÔNG TY DỊCH VỤ',subsidiary:'CÔNG TY CON',internship:'THỰC TẬP',
  pharmacy:'NHÀ THUỐC',station:'TRẠM DỊCH VỤ',agency:'CÔNG TY LỮ HÀNH',collab:'CỘNG TÁC VIÊN',shop:'TIỆM',hub:'BƯU CỤC',parttime:'BÁN THỜI GIAN'};
const JOB_ICON={exam:'📝',cv:'📄',letter:'✉️',interview:'🤝',test:'🎧',trial:'🛠️'};
const jobStages=p=>p?.stages||['cv','letter','interview'];
const stageName=(E,p,st)=>st==='trial'&&p?.trial_title?p.trial_title:(E.stage_names?.[st]||{exam:'Thi chứng chỉ',cv:'CV',letter:'Thư ứng tuyển',interview:'Phỏng vấn',test:'Bài thử tình huống',trial:'Làm thử tại tiệm'}[st]||st);
const certOf=(job,ex)=>ex&&(job.certs||[]).find(x=>x.id===ex.id);
const bossName=p=>p?.boss?p.boss.charAt(0).toUpperCase()+p.boss.slice(1):'';
const stepKey={interview:'questions',test:'test',trial:'trial'};

function jobStepper(E,p,cur,skipExam){
  const rows=jobStages(p).filter(st=>!(st==='exam'&&skipExam&&cur!=='exam'));
  const at=cur==='done'?rows.length:rows.indexOf(cur);
  return `<ol class="jb-steps" style="--n:${rows.length}" aria-label="Các bước tuyển dụng">${rows.map((st,i)=>`<li class="${i<at?'done':i===at?'now':''}"${i===at?' aria-current="step"':''}><span class="jb-dot">${i<at?'✓':JOB_ICON[st]||i+1}</span><small>${esc(stageName(E,p,st))}</small></li>`).join('')}</ol>`;
}
function jobPipe(E,p){return `<p class="jb-pipe small">${jobStages(p).map(st=>`<span>${JOB_ICON[st]||''} ${esc(stageName(E,p,st))}</span>`).join('<i aria-hidden="true">→</i>')}</p>`;}
function jobOpt(command,payload,label,i){
  // No command: an interview/test/trial answer, sent through v4JbAnswer (AI interviewer when allowed).
  const how=command?`data-command="${command}" data-payload="${esc(JSON.stringify(payload))}"`:`data-action="v4JbAnswer"${attrs(payload)}`;
  return `<button type="button" class="choice jb-opt" ${how}><span class="jb-key" aria-hidden="true">${'ABCD'[i]||i+1}</span><span>${esc(label)}</span></button>`;
}
function jobMeter(k,n,label){const pct=Math.round(100*k/Math.max(1,n));return `<div class="row spread jb-count"><span class="eyebrow">${label}</span><b>${k}/${n}</b></div><div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="${n}" aria-valuenow="${k}"><i style="width:${pct}%"></i></div>`;}

function examCard(ex,app){
  const sh=app.exam,next=sh.qs.find(q=>!(q in sh.answers)),q=ex.questions[next],k=Object.keys(sh.answers).length;
  return `<section class="card jb-card">${jobMeter(k+1,sh.qs.length,`${esc(ex.emoji||'📝')} ${esc(ex.name)}`)}
    <p class="small muted jb-rule">Cần đúng <b>${ex.pass_mark}/${ex.draw}</b> câu để đạt · ${esc(ex.issuer)}</p>
    ${k===0?`<p class="small">${esc(ex.intro||'')}</p>`:''}
    <p class="jb-q">Câu ${k+1}. ${esc(q.text)}</p><div class="stack jb-opts">${q.options.map((o,i)=>jobOpt('job_exam',{question:next,option:o.id},o.label,i)).join('')}</div></section>`;
}
/* The interviewer talks back: after a scripted answer they may ask one follow-up (typed
 * reply ≤200 or skip); owners in trials react to each step. Lines come from the save
 * (scripted first, AI wording when it passed the server's guards). The typed reply only
 * moves the score by the word rules in E.reply_rules. Spec: 2026-09-29-ai-interviewer-design.md */
const JB_MAX=200;
let jbWait=null; // {career,step,text} while /api/ai/interview is in flight
const aiOn=api=>!!(api.ai?.configured&&api.state?.settings?.aiConsent);
const jbWho=p=>p?.interviewer||{name:bossName(p)||'Người phỏng vấn',face:'🧑‍💼',role:''};
function jbLine(who,text,mode,canonical){
  const ai=mode==='ai';
  return `<div class="jb-line"><span class="jb-face" aria-hidden="true">${esc(who.face||'💬')}</span><div class="bubble npc jb-bubble${ai?' ai':''}"${ai?' data-no-translate':''}><span class="jb-who">${esc(who.name)}${ai?` <span class="ai-badge" title="${esc('Lời gốc: '+(canonical||''))}" aria-label="Lời do AI viết">AI</span>`:''}</span><div>${esc(text)}</div></div></div>`;
}
const jbMine=(text,pending)=>`<div class="bubble user jb-mine${pending?' pending':''}" data-no-translate><div>${esc(text)}</div></div>`;
const jbTyping=who=>`<div class="jb-line"><span class="jb-face" aria-hidden="true">${esc(who.face||'💬')}</span><div class="bubble npc typing" role="status" aria-label="${esc(who.name)} đang nói…"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span></div></div>`;
function jbScore(E,x){
  const rules=(x.rules||[]).filter(r=>E.reply_rules?.[r]);if(!rules.length&&!x.bonus)return '';
  return `<p class="jb-points ${x.bonus>0?'up':x.bonus<0?'down':''}"><b>${x.bonus>0?'+':''}${x.bonus} điểm</b>${rules.map(r=>`<span>${esc(E.reply_rules[r].label)}</span>`).join('')}</p>`;
}
function jbReplyForm(E,who,api){
  const rules=E.reply_rules||{},plus=Object.values(rules).filter(r=>r.points>0).map(r=>`${r.label} +${r.points}`).join(', ');
  return `<form class="jb-reply" data-v4-jb="reply"><textarea id="jb-reply" class="input" data-preserve rows="2" maxlength="${JB_MAX}" placeholder="Trả lời ${esc(who.name)}…" aria-label="Trả lời ${esc(who.name)}" aria-describedby="jb-reply-hint"></textarea>
    <div class="jb-reply-row"><output id="jb-reply-count" class="chat-count" aria-live="off">0/${JB_MAX}</output><button type="button" class="btn ghost small" data-action="v4JbSkip">Bỏ qua</button><button type="submit" class="btn primary small">${icon('send',15)}<span>Gửi</span></button></div>
    <p id="jb-reply-hint" class="small muted">Không bắt buộc · ${esc(plus)} · đổ lỗi, nói quá hồ sơ, thiếu tôn trọng bị trừ (±3 mỗi câu).${aiOn(api)?` ${icon('sparkle',13)} AI đóng vai người phỏng vấn, đừng gõ thông tin thật.`:''}</p></form>`;
}
/** The owner's last word after the final trial/test step (shown on the result). */
function jbLast(p,app){const x=(app?.talk||[]).slice(-1)[0];return x&&x.kind==='react'?`<div class="jb-chat">${jbLine(x.stage==='test'?{...jbWho(p),face:'😤'}:jbWho(p),x.text,x.mode,x.canonical)}</div>`:'';}
function stepCard(E,qs,p,app,stage,api){
  const ids=p[stepKey[stage]]||[],next=ids.find(q=>!(q in app.answers)),q=qs[next],k=ids.filter(q=>q in app.answers).length;
  const note=(app.notes||[]).slice(-1)[0],who=jbWho(p);
  const label=stage==='trial'?`${JOB_ICON.trial} ${esc(stageName(E,p,'trial'))} · Bước`:stage==='test'?`${JOB_ICON.test} Tình huống`:`${JOB_ICON.interview} Câu hỏi`;
  const face=stage==='test'?'😤':who.face||'💬';
  const intro=k>0?'':stage==='trial'?`<p class="notice blue small">${icon('leaf',15)}<span>${esc(bossName(p))} quan sát bạn làm từng việc thật ở tiệm. Làm ẩu một bước mất an toàn là trượt, dù các bước khác tốt.</span></p>`
    :stage==='test'?`<p class="notice blue small">${icon('leaf',15)}<span>${esc(bossName(p))} đóng vai một vị khách khó tính. Giữ bình tĩnh, nói rõ việc mình làm được.</span></p>`:'';
  const talk=(app.talk||[]).filter(x=>x.stage===stage),last=talk[talk.length-1];
  const lastQ=Object.keys(app.answers).filter(x=>ids.includes(x)).pop();
  const wait=jbWait&&jbWait.career===api.state.current?jbWait:null;
  let chat='';
  if(k>0&&last&&last.q===lastQ&&last.kind==='react')chat=jbLine(stage==='test'?{...who,face:'😤'}:who,last.text,last.mode,last.canonical);
  else if(k>0&&note)chat=`<p class="jb-narr">${esc(note)}</p>`;
  const ask=k>0&&last&&last.q===lastQ&&last.kind==='ask'?last:null;
  if(ask){
    chat+=jbLine(who,ask.text,ask.mode,ask.canonical);
    if(ask.status==='answered')chat+=jbMine(ask.reply)+jbLine(who,ask.react,ask.react_mode,ask.react_canonical)+jbScore(E,ask);
    else if(ask.status==='skipped')chat+=`<p class="jb-skip small muted">Bạn bỏ qua câu hỏi thêm.</p>`;
  }
  const open=ask?.status==='open';
  if(wait&&wait.step!=='answer')chat+=(wait.step==='reply'?jbMine(wait.text,true):'')+jbTyping(who);
  let body='';
  if(wait&&wait.step==='answer')body=`<div class="jb-line"><span class="jb-face" aria-hidden="true">${esc(face)}</span><p class="jb-q">${esc(q?.text||'')}</p></div>${jbMine(wait.text,true)}${jbTyping(who)}`;
  else if(open)body=wait?'':jbReplyForm(E,who,api);
  else if(q)body=`<div class="jb-say"><span class="jb-face" aria-hidden="true">${esc(face)}</span><p class="jb-q">${esc(q.text)}</p></div><div class="stack jb-opts">${q.options.map((o,i)=>jobOpt('',{question:next,option:o.id,label:o.label},o.label,i)).join('')}</div>`;
  const with_=stage==='test'?'':`<p class="jb-with small muted">${esc(who.face||'')} ${esc(who.name)}${who.role?` · ${esc(who.role)}`:''}</p>`;
  return `${intro}<section class="card jb-card">${jobMeter(Math.min(ids.length,k+(open?0:1)),ids.length,label)}${with_}
    ${chat?`<div class="jb-chat" role="log" aria-live="polite">${chat}</div>`:''}${body}</section>`;
}
function examReview(job){
  const rows=job.exam_review||[];if(!rows.length)return '';
  return `<ol class="jb-review">${rows.map(r=>`<li class="${r.ok?'ok':'bad'}"><b>${r.ok?'✓':'✗'} ${esc(r.text)}</b>${r.ok?'':`<small>Bạn chọn: ${esc(r.options[r.picked]||'—')}</small><small>Đúng: ${esc(r.options[r.answer]||'')} — ${esc(r.why)}</small>`}</li>`).join('')}</ol>`;
}
function scoreBar(score){return `<div class="jb-score"><div class="row spread"><span class="eyebrow">Điểm hồ sơ</span><b>${score}/100</b></div><div class="progress jb-bar"><i style="width:${Math.max(0,Math.min(100,score))}%"></i><span class="jb-mark" title="Cần 60 để được nhận"></span></div><small class="muted">Từ 60 điểm được mời nhận việc.</small></div>`;}
/** Story mode, after a failed interview: 📚 study for the certificate, 🚪 the back door, or try again later. */
function nextWays(env,p,job,examFail,when){
  const {api}=env,id=api.state.current,J=api.state.journey,ci=certInfo(api,id);
  certCss();
  const rows=[];let note='';
  if(ci){
    const g=ci.g;
    rows.push(ci.held?`<button type="button" class="btn cream" data-action="jrCerts" data-cert="${esc(g.id)}" data-career="${esc(id)}"><span>🎓 Xem chứng chỉ của bạn<small>${esc(g.name)} · ${ci.rec.best} điểm · lần sau vẫn có ${ci.bonus}% cơ hội</small></span></button>`
      :`<button type="button" class="btn primary" data-action="jrCerts" data-cert="${esc(g.id)}" data-career="${esc(id)}"><span>📚 Đi học lấy chứng chỉ<small>${esc(g.name)} · lớp ${g.fee} xu hoặc tự học miễn phí · thêm ${ci.bonus}% cơ hội được nhận</small></span></button>`);
  }
  const b=p?.backdoor;
  if(examFail)note=`<p class="ct-next-note">🚪 Chứng chỉ hành nghề phải thi thật: không có cửa sau cho bài thi này.</p>`;
  else if(b){
    const used=!!job.backdoor,poor=J.wallet<b.fee;
    const why=used?'Người quen chỉ “lo giúp” được một lần ở mỗi nơi':poor?`Ví còn ${Math.max(0,J.wallet)} xu, thiếu ${b.fee-Math.max(0,J.wallet)} xu`:'Nhờ người quen “lo giúp”, vào làm ngay';
    rows.push(`<button type="button" class="btn cream" data-action="v4Backdoor"${used||poor?' disabled':''}><span>🚪 Đi cửa sau (${b.fee} xu)<small>${esc(why)}</small></span></button>`);
  }
  rows.push(`<button type="button" class="btn ghost" data-action="jrHome"><span>Thử lại sau / Tìm việc khác<small>Ứng tuyển lại ${esc(when)}, hoặc làm ở nơi khác trong hành trình</small></span></button>`);
  return `<div class="ct-next" role="group" aria-label="Làm gì tiếp theo">${rows.join('')}</div>${note}`;
}
function resultCard(p,job,day,ex,env){
  const app=job.application||{},sh=app.exam;
  const examFail=sh&&sh.passed===false;
  const story=!!env?.api.state.journey?.story;
  // The server words the retry day on the one day counter ("từ Ngày 5 (còn 1 ngày · …)" / "bây giờ").
  const when=job.retry?.text||(job.cooldown_day>day?`từ Ngày ${job.cooldown_day} (còn ${job.cooldown_day-day} ngày)`:'bây giờ');
  const next=examFail?`Thi lại ${when} — mỗi lần thi là một bộ câu khác.`:`Ứng tuyển lại ${when}. ${jobStages(p).includes('trial')?'Tập thêm rồi xin làm thử lại nhé.':'Chọn tin phù hợp hơn hoặc sửa CV cho thật.'}`;
  return `<section class="card jb-result bad"><span class="eyebrow">${examFail?'KẾT QUẢ BÀI THI':'KẾT QUẢ ỨNG TUYỂN'}</span><h3>${examFail?`Chưa đạt: ${sh.score}/${sh.qs.length} câu`:'Chưa được nhận lần này'}</h3>
    <p class="small muted">${esc(p?.title||'')} · ${esc(p?.org||'')}</p>
    ${examFail?'':app.score!=null?scoreBar(app.score):''}${examFail?'':jbLast(p,app)}
    ${examFail?'':(app.feedback||[]).map(x=>`<p class="small">• ${esc(x)}</p>`).join('')}
    <p class="notice amber small">${icon('leaf',15)}<span><b>Bước tiếp theo:</b> ${esc(next)}</span></p>
    ${examFail?`<p class="small">Cần đúng ${ex?.pass_mark??4}/${sh.qs.length} câu. Lời giải các câu sai:</p>${examReview(job)}`:''}${story?nextWays(env,p,job,examFail,when):''}</section>`;
}
export function jobView(env){
  const {api,ui}=env,id=api.state.current,c=api.state.careers[id],job=c.job,E=api.content.employment;
  const posts=E.postings[id]||[];const qs=E.questions[id]||{};const ex=E.exams?.[id]||null;const cert=certOf(job,ex);
  const place=api.content.catalogue.find(x=>x.id===id)?.short||'';
  // Story mode: the certificate for this job (📚/🎓) and the re-apply day on the life clock.
  const J=api.state.journey,story=!!J?.story,ci=certInfo(api,id),today=story?J.life_day:c.day;
  if(ci)certCss();
  if(job.status==='hired'){
    const p=posts.find(x=>x.id===job.employer);
    // 🎖️ Thăng tiến (game/promotion.py): the step's title, the good days and a bar; a tap opens the ladder.
    const pr=c.promo,pn=pr?.next,promo=pr?`<button type="button" class="pm-strip" data-action="promo"><span aria-hidden="true">🎖️</span><b>${esc(pr.title)}</b>${pr.due?'<small>Sếp hẹn gặp</small>':pn?`<small>${pn.good}/${pn.need}</small><span class="bar"><i style="width:${Math.round(100*pn.good/Math.max(1,pn.need))}%"></i></span>`:''}</button>`:'';
    return head('Hồ sơ công việc',esc(p?.org||''),'VIỆC LÀM · '+esc(place))+`<div class="sheet-body">${promo}<article class="card"><h3>${esc(job.title)}</h3>
<p>${esc(p?.culture||'')}</p><div class="kv"><div class="kv-row"><span>Lương</span><b>${job.salary} xu/ngày${job.probation?' · thử việc 85%':''}</b></div>${p?.wage_note?`<div class="kv-row"><span>Tiền tiệm</span><b>${esc(p.wage_note)}</b></div>`:''}${cert?`<div class="kv-row"><span>Chứng chỉ</span><b>✓ ${esc(ex.name)}</b></div>`:''}${ci?.held?`<div class="kv-row"><span>Chứng chỉ nghề</span><b>${ci.g.emoji} ${esc(ci.g.name)}</b></div>`:''}${job.backdoor&&job.backdoor.posting===job.employer?`<div class="kv-row"><span>Vào làm</span><b>🚪 Qua cửa sau (${job.backdoor.fee} xu)</b></div>`:''}<div class="kv-row"><span>Ngày đã làm</span><b>${job.days_worked}</b></div>${job.probation?`<div class="kv-row"><span>Thử việc còn</span><b>${job.probation_left} ngày có làm việc</b></div>`:''}</div><p class="muted small">Lương trả khi khép ca nếu hôm đó bạn hoàn thành ít nhất một việc. Hết thử việc, đánh giá trung bình từ 3.5★ sẽ được ký chính thức.</p>${confirmCmd('Xin nghỉ việc','job_quit',{},'Nghỉ việc ở đây? Bạn cần ứng tuyển lại trước ca tiếp theo.','ghost small',c.open)}</article></div>`;
  }
  const app=job.application;
  if(job.status==='offer'){
    const p=posts.find(x=>x.id===app.posting),o=job.offer,trial=jobStages(p).includes('trial');
    return head(trial?'Được nhận vào làm 🎉':'Thư mời nhận việc 🎉',esc(p.org),'VIỆC LÀM')+`<div class="sheet-body">${o.direct?'':jobStepper(E,p,'done',!!cert)}<article class="card jb-result good"><h3>${esc(p.title)}</h3>${o.direct?'<p>Được mời thẳng, không cần phỏng vấn.</p>':scoreBar(o.score)+jbLast(p,app)}<p>Mức lương ${trial?'cứng ':''}đề nghị: <b>${o.salary} xu/ngày</b> (thử việc ${p.probation_days} ngày, nhận 85%).${p.wage_note?` ${esc(p.wage_note)}`:''}</p>${(app.feedback||[]).map(x=>`<p class="small muted">• ${esc(x)}</p>`).join('')}<div class="row wrap space-top">${confirmCmd(trial?'Nhận việc':'Ký hợp đồng thử việc','job_accept',{},`Nhận việc tại ${p.org} với ${o.salary} xu/ngày?`,'primary')}${o.negotiated?'':cmdBtn('Thương lượng lương','job_negotiate',{},'cream')}${cmdBtn('Từ chối','job_decline',{},'ghost')}</div></article></div>`;
  }
  if(job.status==='applying'&&app){
    const p=posts.find(x=>x.id===app.posting);
    let step='',guide='';
    const passed=app.exam?.passed?`<details class="notice success small jb-passed"><summary>✅ <b>Đạt ${app.exam.score}/${app.exam.qs.length}</b> · ${esc(ex?.name||'Chứng chỉ')} đã được cấp</summary>${examReview(job)}</details>`:'';
    if(app.stage==='exam'&&ex&&app.exam){
      step=examCard(ex,app);
    }else if(app.stage==='cv'){
      const sel=ui.cvStrengths||[],claims=ui.cvClaims||['fresh'];
      // What the place wants comes first, so a first CV is one tap away from a good one.
      const cvSteps=[{ok:sel.length>0||null,label:'Chọn 1–3 điểm mạnh',go:{sel:`[data-action="v4Cv"][data-kind="strength"][data-id="${esc(p.wants[0]||'')}"]`}},
        {ok:claims.length>0||null,label:'Chọn kinh nghiệm thật của bạn',go:{sel:'[data-action="v4Cv"][data-kind="claim"][data-id="fresh"]'}}];
      step=`<h3>${JOB_ICON.cv} CV</h3><p class="muted small">Nơi tuyển mong: ${p.wants.map(w=>esc(E.strengths.find(s=>s.id===w)?.name||w)).join(', ')}.</p><label class="field">Điểm mạnh (1–3)</label><div class="chip-row">${E.strengths.map(s=>`<button class="chip ${sel.includes(s.id)?'selected':''}" data-action="v4Cv" data-kind="strength" data-id="${s.id}">${esc(s.emoji)} ${esc(s.name)}</button>`).join('')}</div>
        <label class="field">Kinh nghiệm (1–4 dòng)${p.reference?' — nơi tuyển sẽ kiểm tra tham chiếu':''}</label><div class="stack">${E.claims.map(x=>`<button class="choice ${claims.includes(x.id)?'selected':''}" data-action="v4Cv" data-kind="claim" data-id="${x.id}">${esc(x.text)}</button>`).join('')}</div>
        <div class="row space-top">${stepCta({room:c},cvSteps,{label:'Nộp CV',go:{cmd:'job_cv',payload:{strengths:sel,claims}},ready:!!(sel.length&&claims.length)},{style:'primary'})}</div>`;
      guide=nextHint({room:c},cvSteps,{final:{label:'Nộp CV',go:{cmd:'job_cv',payload:{strengths:sel,claims}}}});
    }else if(app.stage==='letter'){
      const parts=ui.letter||{};
      const letterSteps=E.letter.map(slot=>({ok:parts[slot.id]!=null||null,label:`Chọn: ${slot.title}`,go:{sel:`[data-action="v4Letter"][data-slot="${esc(slot.id)}"]`}}));
      guide=nextHint({room:c},letterSteps,{final:{label:'Gửi thư',go:{cmd:'job_letter',payload:{parts}}}});
      step=`<h3>${JOB_ICON.letter} Thư ứng tuyển</h3>${E.letter.map(slot=>`<label class="field">${esc(slot.title)}</label><div class="stack">${slot.options.map(o=>`<button class="choice ${parts[slot.id]===o.id?'selected':''}" data-action="v4Letter" data-slot="${slot.id}" data-id="${o.id}">${esc(o.label)}</button>`).join('')}</div>`).join('')}
        <div class="row space-top">${stepCta({room:c},letterSteps,{label:'Gửi thư',go:{cmd:'job_letter',payload:{parts}},ready:Object.keys(parts).length>=E.letter.length},{style:'primary'})}</div>`;
    }else if(stepKey[app.stage]){
      step=stepCard(E,qs,p,app,app.stage,api);
    }
    const certNote=ci?.held&&app.stage!=='exam'?`<p class="notice success small ct-banner"><span aria-hidden="true">${ci.g.emoji}</span><span class="grow">Bạn có <b>${esc(ci.g.name)}</b>: nếu điểm chưa đủ 60, vẫn có ${ci.bonus}% cơ hội được nhận.</span></p>`:'';
    return head(esc(p.title),esc(p.org),'ỨNG TUYỂN')+`<div class="sheet-body">${guide}${jobStepper(E,p,app.stage,!!cert&&!app.exam)}${passed}${certNote}${step}<div class="row space-top">${cmdBtn('Rút hồ sơ','job_withdraw',{},'ghost small')}</div></div>`;
  }
  const lastPost=job.application&&posts.find(x=>x.id===job.application.posting);
  const rejected=job.status==='rejected'&&lastPost?resultCard(lastPost,job,today,ex,env):'';
  const wait=job.status==='rejected'&&job.cooldown_day>today;
  const certBanner=!ci?'':ci.held?`<p class="notice success small ct-banner"><span aria-hidden="true">${ci.g.emoji}</span><span class="grow"><b>${esc(ci.g.name)}</b> (${ci.rec.best} điểm): nếu điểm chưa đủ 60, bạn vẫn có ${ci.bonus}% cơ hội được nhận ở đây.</span></p>`
    :rejected?'':`<div class="notice blue small ct-banner"><span aria-hidden="true">🎓</span><span class="grow">Có <b>${esc(ci.g.name)}</b> thì khi điểm chưa đủ 60 vẫn còn ${ci.bonus}% cơ hội được nhận ở đây.</span>${button('Học và thi','jrCerts',{cert:ci.g.id,career:id},'ghost small')}</div>`;
  const certLine=ex?(cert?`<p class="notice success small">${icon('check',15)}<span><b>${esc(ex.name)}</b> đã có (ngày ${cert.day}, đúng ${cert.score}/${ex.draw}). Ứng tuyển sẽ bỏ qua bài thi.</span></p>`:`<p class="notice blue small">${icon('leaf',15)}<span>Nghề này cần <b>${esc(ex.name)}</b>: bài thi ${ex.draw} câu, đạt từ ${ex.pass_mark} câu. Thi ngay khi ứng tuyển.</span></p>`):'';
  const sub=posts.some(p=>jobStages(p).includes('trial'))?'Chủ tiệm cần gặp bạn trước. Gửi vài dòng giới thiệu, làm thử một buổi rồi nhận việc.':'Nghề này cần được tuyển dụng. Chọn nơi phù hợp, viết CV trung thực và đi phỏng vấn.';
  return head('Xin việc: '+esc(place),sub,'TUYỂN DỤNG')+`<div class="sheet-body">${rejected}${certLine}${certBanner}<div class="stack">${posts.map(p=>`<article class="card posting"><div class="row spread"><div><span class="eyebrow">${esc(p.kind==='private'?(id==='teacher'?'TƯ THỤC':'TƯ NHÂN'):JOB_KIND[p.kind]||'')}</span><h3>${esc(p.title)}</h3><small class="muted">${esc(p.org)}</small></div><b>${p.salary[0]}–${p.salary[1]} xu/ngày</b></div>${p.wage_note?`<p class="small muted">${esc(p.wage_note)}</p>`:''}<p class="small">${esc(p.culture)}</p>${jobPipe(E,p)}<div class="chip-row">${ci?.held?`<span class="chip ct-chip">🎓 +${ci.bonus}% cơ hội</span>`:''}${p.perks.map(x=>`<span class="chip">${esc(x)}</span>`).join('')}</div>
    <div class="row wrap space-top">${wait?`<p class="small muted">📅 ${jobStages(p).includes('trial')?'Xin làm thử':'Ứng tuyển'} lại ${esc(job.retry?.text||`từ Ngày ${job.cooldown_day}`)}.</p>`:''}${cmdBtn(wait?`${jobStages(p).includes('trial')?'Xin làm thử':'Ứng tuyển'} lại · Còn ${job.retry?.left??(job.cooldown_day-today)} ngày`:jobStages(p).includes('trial')?'Xin làm thử':'Ứng tuyển','job_apply',{posting:p.id},'primary',wait)}</div></article>`).join('')}</div></div>`;
}

/** One interview move. AI on: POST /api/ai/interview (runs the command, then the
 * interviewer's newest line may be reworded); otherwise, or when the route is unreachable,
 * the plain command. Returns the command result or null. */
function jbQueued(api,fn){const job=api.queue.then(fn,fn);api.queue=job.catch(()=>{});return job;}
const jbRid=()=>globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
async function jbSend(env,step,payload,text){
  const {api,cmd,toast,renderSheet}=env,career=api.state.current;
  const action=step==='answer'?'job_answer':'job_followup',body=step==='answer'?payload:step==='skip'?{skip:true}:{text:payload.text};
  if(jbWait)return null;
  if(!aiOn(api))return cmd(action,body);
  const phase=()=>{const j=api.state.careers[career]?.job;return `${j?.status}|${j?.application?.stage}`;},before=phase();
  jbWait={career,step,text};renderSheet();
  const send=()=>jbQueued(api,()=>api.post('/api/ai/interview',{career,step,...payload,request_id:jbRid(),expected_revision:api.revision},20000));
  try{
    let data;
    try{data=await send();}
    catch(error){if(error.status===409&&error.data?.state){api.accept(error.data);data=await send();}else throw error;}
    jbWait=null;api.accept(data);
    const r=data.result||{};
    if(phase()!==before&&r.message)toast(r.message,r.celebrate?'good':false);
    return r;
  }catch(error){
    jbWait=null;
    if(!error.status)return cmd(action,body); // AI route unreachable: the scripted command
    toast(error.message||'Chưa gửi được câu trả lời.',true);return null;
  }finally{jbWait=null;renderSheet();}
}

/* ------------------------------------------------------------- Actions */
const toastOr=(env,text)=>env.toast?env.toast(text,true):null;
/** The crate's real count is on screen (one tile per unit, inventory.public count_hint), so a count that
 * cannot match is caught before inv_receive refuses it: say how it is off without giving the number, and
 * light the input and the goods not tapped yet. false = send it. */
function countOff(env,id,count,what=''){
  const ui=env.ui,o=(env.api.state.careers[env.api.state.current]?.inventory?.orders||[]).find(v=>v.id===id),n=o?.count_hint;
  if(n==null||count===Number(n))return false;
  const k=(ui.invTally?.[id]||[]).length;
  const msg=count===o.qty?`${count} là số trên phiếu: thùng có thể giao thiếu, chạm đếm từng món trong thùng.`
    :k<n?'Đếm lệch: còn món chưa chạm trong thùng, chạm hết rồi nhận.':`Bạn chạm đếm được ${k} món nhưng ô ghi ${count}.`;
  toastOr(env,what?`${what}: ${msg}`:msg);
  const inp=document.getElementById('count-'+id);if(inp){inp.setAttribute('aria-invalid','true');inp.focus();}
  document.querySelectorAll(`#crate-${CSS.escape(id)} .inv-good:not(.on)`).forEach(b=>b.classList.add('miss'));
  return true;
}
export async function v4Action(action,data,el,env){
  const {api,ui,cmd,confirmAction,renderSheet,openSheet}=env;
  switch(action){
    case'v4Cmd':{const payload=JSON.parse(data.payload||'{}');if(data.confirm&&!await confirmAction('Xác nhận',data.confirm,'Đồng ý',data.cost?{cost:Number(data.cost),pocket:data.pocket||'fund'}:null,data.op==='job_quit'?{arm:700}:null))return true;if(data.confirm)payload.confirm=true;await cmd(data.op,payload);return true;}
    case'v4Backdoor':{
      // 🚪 Honest about what it is: a fee to a helper, a normal probation, maybe some whispers on day one.
      const id=api.state.current,job=api.state.careers[id]?.job,J=api.state.journey;
      await api.more?.();  // job postings: the catalogue's `more` part (api.js)
      const p=(api.content.employment.postings[id]||[]).find(x=>x.id===job?.application?.posting),b=p?.backdoor;if(!b)return true;
      const msg=`${b.helper} Phí ${fmt(b.fee)} xu. Bạn vào làm ${p.title.toLowerCase()} với lương khởi điểm ${p.salary[0]} xu/ngày, thử việc ${p.probation_days} ngày như mọi người. Ngày đầu có thể nghe vài lời xì xào.`;
      const how=await confirmPurchase(env,{title:'🚪 Đi cửa sau?',message:msg,label:`Trả ${b.fee} xu`,cost:b.fee});
      if(how)await cmd('job_backdoor',{confirm:true,pay:how});
      return true;}
    case'inventory':openSheet('inventory',{invFocus:null,invNeed:null,invReturn:null,orderRush:false});return true;
    case'v4Restock':{
      // From a "📦 Nhập hàng" button (restock.js): straight to the crate, the orders on the way, or the order form.
      const inv=api.state.careers[api.state.current]?.inventory,need={},items=[];
      for(const part of String(data.items||'').split(',')){const [id,q]=part.split(':');if(id){items.push(id);if(q)need[id]=Number(q)||1;}}
      const back=data.task||(ui.view==='job'?ui.task:null)||null;
      const pick=!data.order&&!data.wait?items.find(id=>!(inv?.locked||[]).includes(id)&&!(inv?.arriving?.[id])):null;
      openSheet('inventory',{invFocus:items,invNeed:need,invReturn:back,invTab:data.wait?'orders':'stock',invOpen:data.order||null,
        orderItem:pick||null,orderQty:0,orderRush:data.urgent==='1'});
      if(data.order)requestAnimationFrame(()=>document.getElementById('crate-'+data.order)?.scrollIntoView({block:'nearest'}));
      return true;}
    case'v4InvFocus':ui.invFocus=null;ui.orderItem=null;renderSheet(false);return true;
    case'v4Tally':{const k=Number(data.i),t=(ui.invTally??={}),on=new Set(t[data.order]||[]);on.has(k)?on.delete(k):on.add(k);t[data.order]=[...on];
      (ui.invCount??={})[data.order]=String(on.size);if(ui.invTyped)delete ui.invTyped[data.order];renderSheet();return true;}
    case'v4Receive':{const inp=document.getElementById('count-'+data.order),raw=String(inp?.value??ui.invCount?.[data.order]??'').trim();
      if(raw===''){toastOr(env,'Đếm số món trong thùng trước đã nhé.');inp?.focus();return true;}
      if(countOff(env,data.order,Number(raw)))return true;
      if(await cmd('inv_receive',{order:data.order,count:Number(raw)})){for(const k of ['invCount','invTally','invTyped'])if(ui[k])delete ui[k][data.order];if(ui.invOpen===data.order)ui.invOpen=null;renderSheet();}
      return true;}
    case'feedback':if(data.filter){ui.fbFilter=data.filter;ui.fbStars=0;ui.fbPost=null;}openSheet('feedback');return true;
    case'fbGo':ui.fbPost=data.post||null;ui.fbFilter='all';ui.fbStars=0;openSheet('feedback');return true;
    case'situation':openSheet('situation');return true;
    case'jobapp':openSheet('jobapp');return true;
    case'v4InvTab':ui.invTab=data.tab;renderSheet(false);return true;
    case'v4Order':{if(ui.orderItem!==data.item)ui.orderQty=0;ui.orderItem=data.item||null;if(ui.orderItem)ui.invCart=null;ui.invTab='stock';renderSheet(!ui.orderItem);return true;}
    /* Đơn gộp: a supplier's draft (game/inventory.py inv_cart / inv_haggle / inv_order_cart). */
    case'v4Cart':{
      if(ui.view!=='inventory'){openSheet('inventory',{invFocus:null,invNeed:null,invReturn:null,invTab:'stock',orderItem:null,invCart:data.supplier||null});return true;}
      ui.invCart=data.supplier&&(data.open||ui.invCart!==data.supplier)?data.supplier:null;ui.orderItem=null;ui.invTab='stock';renderSheet(false);return true;}
    case'v4CartAdd':{
      const item=api.content.inventory.items[api.state.current].find(i=>i.id===data.item);if(!item)return true;
      const inp=document.getElementById('order-qty'),max=Math.max(1,Number(inp?.max)||30);
      const qty=Math.max(1,Math.min(max,Number(inp?.value)||ui.orderQty||1)),sup=pickSupplier(env,item.id);
      if(await cmd('inv_cart',{supplier:sup.id,op:'add',item:item.id,qty,size:orderSize(env,item.id)})){ui.orderSupplier=sup.id;ui.orderItem=null;ui.orderQty=0;ui.invTab='stock';renderSheet(false);}
      return true;}
    case'v4CartPut':{  // a career's own stock list (grocery.js): one line straight into the draft
      if(await cmd('inv_cart',{supplier:data.supplier,op:'add',item:data.item,qty:Number(data.qty)||1}))renderSheet();return true;}
    case'v4CartQty':{if(await cmd('inv_cart',{supplier:data.supplier,op:'set',item:data.item,qty:Math.max(0,Number(data.qty)||0)},{quiet:true}))renderSheet();return true;}
    case'v4CartFill':{
      const lines=String(data.items||'').split(',').map(x=>x.split(':')).filter(([id])=>id).map(([item,q])=>({item,qty:Math.max(1,Math.min(30,Number(q)||10))}));
      if(lines.length&&await cmd('inv_cart',{supplier:data.supplier,op:'add',lines,fit:true})){ui.invCart=data.supplier;ui.orderItem=null;ui.invTab='stock';renderSheet(false);}
      return true;}
    case'v4CartGo':{
      const k=(api.state.careers[api.state.current]?.inventory?.carts||[]).find(x=>x.supplier===data.supplier);if(!k)return true;
      const s=supplierList(env).find(x=>x.id===k.supplier)||{name:k.supplier};
      if(!await confirmAction('Đặt đơn gộp?',`${k.n} món từ ${s.name}: trả ${fmt(k.total)} xu ngay${k.ship?` (ship ${fmt(k.ship)} xu)`:' (miễn ship)'}. Dự kiến: ${k.quote?.label||''}. Một chuyến, một thùng.`,'Đặt đơn',{cost:k.total,pocket:'fund'}))return true;
      if(await cmd('inv_order_cart',{supplier:k.supplier,confirm:true})){ui.invCart=null;ui.invTab='orders';renderSheet(false);}
      return true;}
    case'v4ReceiveGroup':{
      const inv=api.state.careers[api.state.current]?.inventory,lines=(inv?.orders||[]).filter(o=>o.group===data.group&&o.status==='in_transit'),counts={};
      for(const o of lines){const inp=document.getElementById('count-'+o.id),raw=String(inp?.value??ui.invCount?.[o.id]??'').trim();
        if(raw===''){const it=api.content.inventory.items[api.state.current].find(i=>i.id===o.item);toastOr(env,`Đếm ${it?.name||'từng món'} trong thùng trước đã nhé.`);inp?.focus();return true;}
        counts[o.id]=Number(raw);}
      // Same check as one crate (countOff): a line that cannot match is pointed out before inv_receive refuses the lot.
      for(const o of lines){const it=api.content.inventory.items[api.state.current].find(i=>i.id===o.item);if(countOff(env,o.id,counts[o.id],it?.name||''))return true;}
      if(lines.length&&await cmd('inv_receive',{group:data.group,counts})){for(const o of lines)for(const k of ['invCount','invTally','invTyped'])if(ui[k])delete ui[k][o.id];
        if(ui.invOpen===data.group||lines.some(o=>o.id===ui.invOpen))ui.invOpen=null;renderSheet();}
      return true;}
    case'v4Supplier':ui.orderSupplier=data.supplier;renderSheet();return true;
    case'v4OrderSize':{(ui.orderSize??={})[data.item]=data.size||null;renderSheet();return true;}
    case'v4Qty':{const inp=document.getElementById('order-qty'),max=Math.max(1,Number(inp?.max)||30),cur=Number(inp?.value)||ui.orderQty||1;
      ui.orderQty=Math.max(1,Math.min(max,data.set?Number(data.set):cur+Number(data.step||0)));renderSheet();return true;}
    case'v4Count':{const inp=document.getElementById(data.target);if(inp){inp.value=String(Math.max(0,Math.min(60,(Number(inp.value)||0)+Number(data.step||0))));(ui.invCount??={})[inp.dataset.v4Count]=inp.value;(ui.invTyped??={})[inp.dataset.v4Count]=true;}return true;}
    case'v4InvOpen':openSheet('inventory',ui.view==='inventory'?{invOpen:data.order}:{invOpen:data.order,invTab:'orders',invFocus:null,invNeed:null,invReturn:null});requestAnimationFrame(()=>document.getElementById('crate-'+data.order)?.scrollIntoView({block:'nearest'}));return true;
    case'v4OrderGo':{
      const item=api.content.inventory.items[api.state.current].find(i=>i.id===data.item);if(!item)return true;
      const inp=document.getElementById('order-qty'),max=Math.max(1,Number(inp?.max)||30);
      const qty=Math.max(1,Math.min(max,Number(inp?.value)||ui.orderQty||1));ui.orderQty=qty;
      const sup=pickSupplier(env,item.id);
      const q=orderQuote(item,qty,sup),cost=q.total,eta=sup.quote?.eta_label||sup.window||'';
      const size=orderSize(env,item.id);
      if(!await confirmAction('Đặt hàng?',`${qty} ${item.unit||'phần'} ${item.name}${size?` · size ${size}`:''} từ ${sup.name}: trả ${cost} xu ngay${q.ship?` (ship ${q.ship} xu)`:''}.${eta?` Dự kiến nhận: ${eta}.`:''} Hàng chỉ vào kho sau khi bạn đếm nhận.`,'Đặt hàng',{cost,pocket:'fund'}))return true;
      const r=await cmd('inv_order',{item:item.id,qty,size,supplier:sup.id,confirm:true});if(r){ui.orderItem=null;ui.orderQty=0;ui.invTab='orders';renderSheet(false);}
      return true;}
    case'v4FbFilter':ui.fbFilter=data.tab;ui.fbStars=0;ui.fbPost=null;renderSheet(false);return true;
    case'v4FbStars':{const s=Number(data.stars)||0;ui.fbStars=ui.fbStars===s?0:s;ui.fbFilter='all';ui.fbPost=null;renderSheet(false);return true;}
    case'v4FbBack':ui.fbPost=null;renderSheet(false);return true;
    case'v4FbTpl':{
      // Pick a tone: fill the box (still editable) and remember the tone without re-rendering.
      const ta=document.getElementById('fb-text'),form=ta?.closest('form'),tone=data.tone||'free';
      if(ta){ta.value=data.text||'';ta.focus();}
      if(form){const h=form.querySelector('input[name=tone]');if(h)h.value=data.tone?tone:'free';
        form.querySelectorAll('.rv-tone').forEach(b=>{const on=b.dataset.tone===tone;b.classList.toggle('selected',on);b.setAttribute('aria-pressed',String(on));});
        if(tone==='sorry'){const none=form.querySelector('input[name=offer][value=none]'),drink=form.querySelector('input[name=offer][value=drink]');if(none?.checked&&drink){drink.checked=true;ui.fbOffer='drink';}}}
      if(data.tone)ui.fbTone={post:ui.fbPost||form?.dataset.v4Fb,tone};
      return true;}
    case'v4FbOpen':{
      if(ui.fbPost!==data.post)ui.fbOffer='none';ui.fbPost=data.post;renderSheet(false);
      // With AI allowed, the reviewer rewrites a fresh scripted review in their own voice once.
      const {api}=env,post=(env.api.state.careers[env.api.state.current].feed||[]).find(p=>p.id===data.post);
      ui.voiceTried??=new Set();
      if(post?.feedback?.voice==='scripted'&&!post.feedback.thread.length&&api.ai?.configured&&api.state.settings.aiConsent&&!ui.voiceTried.has(post.id)){ui.voiceTried.add(post.id);api.aiReview(post.id).catch(()=>{});}
      return true;
    }
    case'v4Cv':{const key=data.kind==='strength'?'cvStrengths':'cvClaims';const cur=ui[key]||(key==='cvClaims'?['fresh']:[]);const max=key==='cvStrengths'?3:4;ui[key]=cur.includes(data.id)?cur.filter(x=>x!==data.id):cur.length<max?[...cur,data.id]:cur;renderSheet();return true;}
    case'v4Letter':ui.letter={...(ui.letter||{}),[data.slot]:data.id};renderSheet();return true;
    case'v4JbAnswer':await jbSend(env,'answer',{question:data.question,option:data.option},data.label||'');return true;
    case'v4JbSkip':await jbSend(env,'skip',{},'');return true;
  }
  return false;
}
export async function v4Submit(form,env){
  const {api,cmd}=env;
  if(form.dataset.v4Receive){const id=form.dataset.v4Receive,count=Number(form.querySelector('input').value);
    if(countOff(env,id,count))return true;
    if(await cmd('inv_receive',{order:id,count})){for(const k of ['invCount','invTally','invTyped'])if(env.ui[k])delete env.ui[k][id];if(env.ui.invOpen===id)env.ui.invOpen=null;}return true;}
  if(form.dataset.v4Jb){
    const ta=form.querySelector('textarea'),text=String(ta?.value||'').trim().slice(0,JB_MAX);
    if(!text){ta?.focus();return true;}
    if(await jbSend(env,'reply',{text},text)&&ta)ta.value='';
    return true;
  }
  if(form.dataset.v4Fb){
    const post=form.dataset.v4Fb,text=form.querySelector('textarea').value.trim(),offer=form.querySelector('input[name=offer]:checked')?.value||'none';
    const tone=form.querySelector('input[name=tone]')?.value||'free';
    if(!text)return true;
    const r=await cmd('fb_reply',{post,text,offer,tone});
    if(r){
      form.querySelector('textarea').value='';env.ui.fbOffer='none';env.ui.fbTone=null;
      // Give the reviewer a moment to "read" before answering.
      setTimeout(async()=>{const d=await api.aiFeedback(post);const msg=d?.result?.message;if(msg)env.toast(msg);},1600);
    }
    return true;
  }
  return false;
}
export function v4Input(el,env){
  if(el.id==='jb-reply'){const out=document.getElementById('jb-reply-count');if(out)out.textContent=`${el.value.length}/${JB_MAX}`;return true;}
  if(el.name==='offer'&&el.closest('[data-v4-fb]')){env.ui.fbOffer=el.value;return true;}
  if(el.id==='fb-text'&&el.closest('[data-v4-fb]')){
    // Clearing the box means writing your own words.
    if(!el.value.trim()){const f=el.closest('form'),h=f.querySelector('input[name=tone]');if(h)h.value='free';f.querySelectorAll('.rv-tone').forEach(b=>{const on=b.dataset.tone==='free';b.classList.toggle('selected',on);b.setAttribute('aria-pressed',String(on));});env.ui.fbTone=null;}
    return true;}
  if(el.dataset.v4Qty!==undefined){
    const total=document.getElementById('order-total'),d=total?.dataset||{},max=d.max!==undefined?Number(d.max):30,typed=Number(el.value)||0;
    const q=env.ui.orderQty=Math.max(1,Math.min(Math.max(1,max),typed||1));
    if(total){
      let terms={};try{terms=JSON.parse(d.terms||'{}');}catch{}
      const oq=orderQuote({cost:Number(d.cost)},q,{factor:Number(d.factor),...terms}),cost=oq.total,money=Number(d.money);
      total.textContent=`Tổng: ${fmt(cost)} xu`;
      const ship=document.getElementById('order-ship');if(ship&&terms.free_from!=null)ship.textContent=oq.ship?`Hàng ${fmt(oq.cost)} + ship ${fmt(oq.ship)} xu`:`Hàng ${fmt(oq.cost)} xu · miễn ship`;
      const tier=document.getElementById('order-tier');if(tier)tier.innerHTML=oq.pct?`<span class="tag green">sỉ −${oq.pct}%</span>`:oq.tier&&oq.tier[0]<=max?`<button type="button" class="chip inv-tier" data-action="v4Qty" data-set="${oq.tier[0]}">Lấy ${oq.tier[0]}: −${oq.tier[1]}%</button>`:'';
      const fn=d.fund||'Quỹ tiệm',after=document.getElementById('order-after');if(after)after.textContent=`${fn} còn ${fmt(Math.max(0,money-cost))} xu · kệ sau khi nhận ${Number(d.shelf)+q}/${d.cap}`;
      const inv=env.api.state.careers[env.api.state.current]?.inventory;
      const why=!max?'Kệ đã đầy (tính cả hàng đang giao).':vans(inv).full?`${vansLine(inv)}: nhận bớt thùng rồi đặt tiếp.`:typed>max?`Chỉ còn chỗ cho ${max}.`:cost>money?`${fn} còn ${fmt(money)} xu, thiếu ${fmt(cost-money)} xu.`:'';
      const w=document.getElementById('order-why');if(w)w.textContent=why;
      const go=document.getElementById('order-go');if(go)go.disabled=Boolean(why)||typed<1;
    }
    return true;
  }
  if(el.dataset.v4Count!==undefined){el.removeAttribute('aria-invalid');(env.ui.invCount??={})[el.dataset.v4Count]=el.value;(env.ui.invTyped??={})[el.dataset.v4Count]=true;return true;}
  return false;
}
