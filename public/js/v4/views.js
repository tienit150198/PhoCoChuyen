/** v0.4 shared sheets: stock & suppliers, customer feedback threads, real-life
 * situations with several points of view, and job applications. Views return
 * HTML strings; clicks go through the global data-action/data-command delegate. */
import {icon,portrait,escapeHTML as esc} from '../icons.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const attrs=obj=>Object.entries(obj).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const button=(label,action,data={},style='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}>${label}</button>`;
const cmdBtn=(label,command,payload={},style='',disabled=false)=>`<button type="button" class="btn ${style}" data-command="${command}" data-payload="${esc(JSON.stringify(payload))}"${disabled?' disabled':''}>${label}</button>`;
const confirmCmd=(label,command,payload={},question='',style='',disabled=false)=>`<button type="button" class="btn ${style}" data-action="v4Cmd" data-op="${command}" data-payload="${esc(JSON.stringify(payload))}" data-confirm="${esc(question)}"${disabled?' disabled':''}>${label}</button>`;
const pill=(label,kind='')=>`<span class="tag ${kind}">${label}</span>`;
const stars=n=>n?'★'.repeat(n)+'☆'.repeat(5-n):'';
const head=(title,sub='',eyebrow='')=>`<header class="sheet-head"><div class="grow">${eyebrow?`<span class="eyebrow">${eyebrow}</span>`:''}<h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
const tabs=(items,active,action)=>`<nav class="pill-tabs" role="tablist">${items.map(([id,label])=>`<button role="tab" aria-selected="${id===active}" class="${id===active?'active':''}" data-action="${action}" data-tab="${id}">${label}</button>`).join('')}</nav>`;

/* ---------------------------------------------------------------- Stock */
/** Stock room: a status strip with ONE next step, shelf bins (count, fill,
 * goods on the way, expiry), an order card with a stepper and suppliers,
 * crates to open and count by eye (the slip may differ from what is inside),
 * and lots by days left. The server stays authoritative for every rule. */
export function inventoryView(env){
  const {api,ui}=env,c=api.state.careers[api.state.current],inv=c.inventory,content=api.content;
  if(!inv)return head('Nghề này không nhập hàng','Công việc dựa vào hồ sơ và thời gian của bạn.')+`<div class="sheet-body"><div class="empty">${icon('box',32)}<p>Không có kho nguyên liệu ở nghề này.</p></div></div>`;
  const items=content.inventory.items[api.state.current]||[],byId=Object.fromEntries(items.map(i=>[i.id,i]));
  const cap=inv.capacity,arriving=inv.arriving||{},unit=i=>i?.unit||'phần',stock=id=>inv.stock[id]||0;
  const room=id=>inv.room?.[id]??Math.max(0,cap-stock(id)-(arriving[id]||0));
  const orders=inv.orders||[],ready=orders.filter(o=>o.status==='in_transit'&&o.ready_now),transit=orders.filter(o=>o.status==='in_transit'&&!o.ready_now);
  const open=items.filter(i=>!inv.locked.includes(i.id)),lowLine=Math.max(2,Math.floor(cap*.15));
  const low=open.filter(i=>stock(i.id)+(arriving[i.id]||0)<=lowLine).sort((a,b)=>stock(a.id)-stock(b.id));
  const tonight=open.reduce((n,i)=>n+(inv.expiring[i.id]||0),0);
  const tab=['stock','orders','lots'].includes(ui.invTab)?ui.invTab:'stock';
  const name=i=>`${esc(i?.emoji||'📦')} ${esc(i?.name||'')}`;
  // One primary next step, in order of urgency.
  let cta='';
  if(ready.length)cta=button(`${icon('box',15)} Mở thùng ${name(byId[ready[0].item])}`,'v4InvOpen',{order:ready[0].id},'primary');
  else if(low.length)cta=button(`${icon('plus',15)} Nhập thêm ${name(low[0])}`,'v4Order',{item:low[0].id},'primary');
  else if(tonight)cta=button(`${icon('clock',15)} Xem hàng hết hạn tối nay`,'v4InvTab',{tab:'lots'},'primary');
  const chip=(n,label,kind,tabId)=>n?`<button type="button" class="inv-chip ${kind}" data-action="v4InvTab" data-tab="${tabId}"><b>${n}</b> ${label}</button>`:'';
  const calm=!ready.length&&!transit.length&&!tonight&&!low.length?`<span class="inv-calm">${icon('check',14)} Kho ổn. Chạm một ô để nhập thêm.</span>`:'';
  const strip=`<section class="inv-status" aria-label="Tình trạng kho"><div class="inv-chips">${chip(ready.length,'thùng đã tới','accent','orders')}${chip(transit.length,'đơn đang giao','info','orders')}${chip(tonight,'hết hạn tối nay','bad','lots')}${chip(low.length,'loại sắp hết','warn','stock')}${calm}</div>${cta?`<div class="inv-cta">${cta}</div>`:''}</section>`;
  let body='';
  if(tab==='stock'){
    const pct=v=>Math.max(0,Math.min(100,Math.round(v/cap*100)));
    const bin=i=>{
      const q=stock(i.id),on=arriving[i.id]||0,locked=inv.locked.includes(i.id),exp=inv.expiring[i.id]||0,soon=(inv.expiring_soon?.[i.id]||0)-exp,days=inv.days_left?.[i.id];
      const state=locked?'locked':q===0?'out':q+on<=lowLine?'low':'';
      const flags=locked?`<span class="inv-flag">${icon('lock',11)} Mở ở cấp ${i.unlock}</span>`:[on?`<span class="inv-flag info">+${on} đang giao</span>`:'',exp?`<span class="inv-flag bad">${exp} hết hạn tối nay</span>`:soon>0?`<span class="inv-flag warn">${soon} hết hạn mai</span>`:'',q===0&&!on?'<span class="inv-flag bad">Hết hàng</span>':''].join('');
      const life=!locked&&days&&days<900&&!exp?` · còn ${days} ngày`:'';
      return `<button type="button" class="inv-bin ${state}" data-action="v4Order" data-item="${esc(i.id)}"${locked?' disabled':''} aria-label="${esc(i.name)}: ${q} trên kệ${on?`, ${on} đang giao`:''}${locked?`, mở ở cấp ${i.unlock}`:', chạm để nhập thêm'}">`+
        `<span class="inv-bin-top"><span class="inv-bin-emoji" aria-hidden="true">${esc(i.emoji||'📦')}</span><span class="inv-bin-count"><b>${locked?'—':q}</b><small>/${cap}</small></span></span>`+
        `<span class="inv-bin-name">${esc(i.name)}</span><small class="inv-bin-unit">${esc(unit(i))}${life}</small>`+
        `<span class="inv-bar" aria-hidden="true"><i style="width:${pct(q)}%"></i><i class="on" style="width:${pct(on)}%"></i></span>`+
        `${flags?`<span class="inv-flags">${flags}</span>`:''}</button>`;};
    // Sections by group; runs of one-item groups share a section so the grid stays full.
    const sections=[];
    for(const g of new Set(items.map(i=>i.group))){const list=items.filter(i=>i.group===g),last=sections.at(-1);
      if(list.length===1&&last?.single)last.names.push(groupName(g)),last.list.push(...list);else sections.push({names:[groupName(g)],list,single:list.length===1});}
    const order=list=>[...list.filter(i=>!inv.locked.includes(i.id)),...list.filter(i=>inv.locked.includes(i.id))];
    body=sections.map(x=>`${sections.length>1?`<h4 class="section-title">${esc(x.names.join(' · '))}</h4>`:''}<div class="inv-bins">${order(x.list).map(bin).join('')}</div>`).join('');
    const pick=ui.orderItem&&byId[ui.orderItem];
    if(pick&&!inv.locked.includes(pick.id))body=orderCard(env,pick,{cap,stock:stock(pick.id),on:arriving[pick.id]||0,space:room(pick.id),unit:unit(pick),name:name(pick)})+body;
  }else if(tab==='orders'){
    const sup=o=>content.inventory.suppliers.find(x=>x.id===o.supplier);
    const crate=o=>{
      const i=byId[o.item]||{name:o.item},s=sup(o),n=Number(o.count_hint)||0;
      // Scatter the goods a little (stable per order) so counting is looking, not reading.
      let h=0;for(const ch of o.id)h=(h*31+ch.charCodeAt(0))>>>0;
      const goods=Array.from({length:n},()=>{h=(Math.imul(h,1103515245)+12345)>>>0;const r=(h%21)-10,dy=((h>>>5)%7)-3;return `<li style="transform:translateY(${dy}px) rotate(${r}deg)"><span role="img" aria-label="${esc(i.name)}">${esc(i.emoji||'📦')}</span></li>`;}).join('');
      const opened=ui.invOpen===o.id||ready.length===1;
      const form=`<div class="inv-slip"><span>Phiếu giao ghi</span><b>${o.qty} ${esc(unit(i))}</b></div><ul class="inv-crate" aria-label="Trong thùng">${goods}</ul>`+
        `<form class="inv-receive" data-v4-receive="${esc(o.id)}"><label for="count-${esc(o.id)}">Bạn đếm được</label><div class="inv-stepper"><button type="button" class="btn ghost" data-action="v4Count" data-target="count-${esc(o.id)}" data-step="-1" aria-label="Bớt một">−</button><input id="count-${esc(o.id)}" class="input" type="number" min="0" max="60" inputmode="numeric" value="${esc(ui.invCount?.[o.id]??'')}" placeholder="0" data-v4-count="${esc(o.id)}" required><button type="button" class="btn ghost" data-action="v4Count" data-target="count-${esc(o.id)}" data-step="1" aria-label="Thêm một">+</button></div><button class="btn primary" type="submit">${icon('check',15)} Nhận vào kệ</button></form>`+
        `<p class="muted small">Đếm từng món thật trong thùng. Phiếu có thể ghi khác; thiếu thì nhận đúng số có rồi khiếu nại.</p>`;
      return `<article class="card inv-crate-card${opened?' open':''}" id="crate-${esc(o.id)}"><div class="row spread"><div><strong>${name(i)}</strong><small class="muted block">${esc(s?.emoji||'')} ${esc(s?.name||'')} · đã trả ${fmt(o.cost)} xu</small></div>${pill('ĐÃ TỚI','green')}</div>${opened?form:button(`${icon('box',15)} Mở thùng & đếm`,'v4InvOpen',{order:o.id},'primary')}</article>`;};
    const waiting=o=>{const i=byId[o.item]||{name:o.item},s=sup(o),left=Math.max(1,(o.ready||0)-(c.turn||0));
      return `<article class="card order-row"><div class="row spread"><div><strong>${name(i)} · ${o.qty} ${esc(unit(i))}</strong><small class="muted block">${esc(s?.emoji||'')} ${esc(s?.name||'')} · đã trả ${fmt(o.cost)} xu</small></div>${pill(`TỚI SAU ${left} NHỊP`,'amber')}</div><div class="row wrap"><span class="muted small grow">Làm việc khác một chút, hoặc chờ một nhịp rồi mở thùng.</span>${cmdBtn('Chờ một nhịp','advance',{},'ghost small')}</div></article>`;};
    const received=o=>{const i=byId[o.item]||{name:o.item},s=sup(o),short=o.actual<o.qty;
      let act='';
      if(short&&!o.claimed)act+=cmdBtn('Khiếu nại phần thiếu','inv_claim',{order:o.id},'small cream');
      if(o.rating==null)act+=`<div class="row wrap rate-row" role="group" aria-label="Đánh giá ${esc(s?.name||'')}">${[1,2,3,4,5].map(n=>cmdBtn('★'.repeat(n),'inv_rate',{order:o.id,stars:n,note:''},'ghost small')).join('')}</div>`;
      if(o.reply)act+=`<p class="bubble small"><b>${esc(s?.name||'')}:</b> ${esc(o.reply)}</p>`;
      return `<article class="card order-row"><div class="row spread"><div><strong>${name(i)} · nhận ${o.actual}/${o.qty}</strong><small class="muted block">${esc(s?.emoji||'')} ${esc(s?.name||'')} · ${fmt(o.cost)} xu · ngày ${o.day}</small></div>${short?pill(o.claimed?'ĐÃ HOÀN TIỀN':'GIAO THIẾU','amber'):o.rating?pill(stars(o.rating),'amber'):''}</div>${act}</article>`;};
    const done=orders.filter(o=>o.status==='received').reverse().slice(0,10);
    body=(ready.length?`<h4 class="section-title">Thùng đã tới · mở và đếm</h4>${ready.map(crate).join('')}`:'')+
      (transit.length?`<h4 class="section-title">Đang giao</h4>${transit.map(waiting).join('')}`:'')+
      (done.length?`<h4 class="section-title">Đã nhận gần đây</h4>${done.map(received).join('')}`:'')||`<div class="empty">${icon('truck',30)}<p>Chưa có đơn nhập nào. Chạm một ô trong Kệ hàng để nhập.</p></div>`;
  }else{
    const lots=inv.lots.filter(l=>l.qty>0&&l.expires>=c.day).sort((a,b)=>a.expires-b.expires||a.received-b.received);
    body=lots.length?`<div class="inv-lots">${lots.map(l=>{const i=byId[l.item]||{name:l.item},left=l.expires-c.day+1;
      const tag=l.expires>=900?pill('không hạn',''):left<=1?pill('hết hạn tối nay','danger'):left===2?pill('còn 2 ngày','amber'):pill(`còn ${left} ngày`,'');
      return `<div class="inv-lot"><span class="inv-lot-name">${name(i)}</span><span class="inv-lot-qty"><b>${l.qty}</b> ${esc(unit(i))}</span>${tag}${confirmCmd('Bỏ lô','inv_discard',{lot:l.id},`Bỏ ${l.qty} ${unit(i)} ${i.name}? Giá trị được ghi vào hao hụt.`,'ghost small')}</div>`;}).join('')}</div>`+
      `<p class="muted small space-top">Vào trước dùng trước: lô hết hạn sớm nhất được lấy trước. Lô hết hạn được ghi hao hụt khi khép ca.</p>`:`<div class="empty">${icon('box',30)}<p>Kho trống.</p></div>`;
  }
  const place=api.content.catalogue.find(x=>x.id===api.state.current)?.place||'';
  return head('Kho & nhập hàng',`Mỗi loại chứa tối đa ${cap} · ${fmt(c.money)} xu trong két`,'KHO · '+esc(place))+
    `<div class="sheet-body">${strip}${tabs([['stock','Kệ hàng'],['orders',`Thùng hàng${ready.length?` · ${ready.length} tới`:''}`],['lots','Hạn dùng']],tab,'v4InvTab')}<div class="space-top">${body}</div></div>`;
}
/** Order card: stepper + quick chips (never past the room left), suppliers,
 * a live total and the reason when ordering is not possible. */
function orderCard(env,pick,{cap,stock,on,space,unit,name}){
  const {api,ui}=env,c=api.state.careers[api.state.current],inv=c.inventory,sups=api.content.inventory.suppliers;
  const sup=sups.find(x=>x.id===(ui.orderSupplier||'partner'))||sups[0],max=Math.min(30,space);
  // First suggestion: up to 10, never past the room left or what the till can pay.
  const afford=Math.floor(c.money/Math.max(1e-9,pick.cost*sup.factor)),qty=Math.max(1,Math.min(max||1,ui.orderQty||Math.min(10,max||1,Math.max(1,afford))));
  const cost=Math.max(1,Math.ceil(pick.cost*qty*sup.factor));
  const why=!space?'Kệ đã đầy (tính cả hàng đang giao).':cost>c.money?`Chưa đủ xu: cần ${fmt(cost)}, két có ${fmt(c.money)}.`:'';
  const chips=[5,10].filter(n=>n<max).map(n=>`<button type="button" class="chip ${n===qty?'selected':''}" data-action="v4Qty" data-set="${n}">${n}</button>`).join('')+(max?`<button type="button" class="chip ${qty===max?'selected':''}" data-action="v4Qty" data-set="${max}">${space<=30?'Đầy kệ':'Tối đa'} · ${max}</button>`:'');
  const supplier=x=>{const r=inv.suppliers.find(y=>y.id===x.id)?.rating;return `<button type="button" class="choice ${x.id===sup.id?'selected':''}" data-action="v4Supplier" data-supplier="${x.id}" aria-pressed="${x.id===sup.id}"><strong>${esc(x.emoji)} ${esc(x.name)}</strong><small>${x.lead===0?'Có ngay':`Tới sau ${x.lead} nhịp`} · ${x.factor<1?'rẻ hơn':x.factor>1?'đắt hơn':'giá niêm yết'} ×${x.factor}${r?` · ${r}★`:''}</small><small class="muted">${esc(x.note)}</small></button>`;};
  return `<section class="card order-card inv-order" aria-label="Nhập ${esc(pick.name)}"><div class="row spread"><h3>Nhập ${name}</h3>${button(icon('x',14),'v4Order',{item:''},'ghost small')}</div>`+
    `<p class="inv-facts"><span>Trên kệ <b>${stock}</b></span><span>Đang giao <b>${on}</b></span><span>Còn chỗ <b>${space}</b></span><span>Giá gốc <b>${pick.cost}</b> xu/${esc(unit)}</span>${pick.life?`<span>Dùng trong <b>${pick.life}</b> ngày</span>`:''}</p>`+
    `<label class="field" for="order-qty">Số lượng</label><div class="inv-qty"><div class="inv-stepper"><button type="button" class="btn ghost" data-action="v4Qty" data-step="-1" aria-label="Bớt một"${qty<=1?' disabled':''}>−</button><input id="order-qty" class="input" type="number" inputmode="numeric" min="1" max="${Math.max(1,max)}" value="${qty}" data-v4-qty aria-describedby="order-total"><button type="button" class="btn ghost" data-action="v4Qty" data-step="1" aria-label="Thêm một"${qty>=max?' disabled':''}>+</button></div><span class="chip-row">${chips}</span></div>`+
    `<label class="field">Nhà cung cấp</label><div class="choice-grid">${sups.map(supplier).join('')}</div>`+
    `<div class="inv-total"><div class="grow"><strong id="order-total" data-cost="${pick.cost}" data-factor="${sup.factor}" data-money="${c.money}" data-shelf="${stock+on}" data-cap="${cap}" data-max="${max}">Tổng: ${fmt(cost)} xu</strong><small class="muted block" id="order-after">Két còn ${fmt(Math.max(0,c.money-cost))} xu · kệ sau khi nhận ${stock+on+qty}/${cap}</small><small class="danger-text block" id="order-why" role="status">${esc(why)}</small></div>`+
    `<button type="button" class="btn primary" id="order-go" data-action="v4OrderGo" data-item="${esc(pick.id)}"${why?' disabled':''}>${icon('truck',15)} Đặt hàng</button></div>`+
    `<p class="muted small">Trả tiền khi đặt. Hàng vào kệ sau khi bạn mở thùng và đếm đúng.</p></section>`;
}
function groupName(g){return {base:'Nguyên liệu chính',pack:'Bao bì',sauce:'Sốt',broth:'Nước dùng',topping:'Topping',flower:'Hoa',filler:'Lá & hoa phụ',wrap:'Giấy gói & ruy băng',supply:'Vật tư',goods:'Hàng hóa',tool:'Dụng cụ',part:'Linh kiện',seed:'Hạt giống',feed:'Thức ăn',product:'Sản phẩm',ingredient:'Nguyên liệu',drink:'Đồ uống',bake:'Bánh',room:'Phòng',care:'Chăm sóc',coffee:'Cà phê',dry:'Hàng khô',fridge:'Tủ mát',milk:'Sữa',bike:'Xe đạp',cooker:'Nồi cơm',fan:'Quạt',headphone:'Tai nghe',laptop:'Máy tính',phone:'Điện thoại'}[g]||g;}

/* ------------------------------------------------------------ Feedback */
/** Reviews: big average, 5★→1★ bars (tap to filter), chips, cards with a reply
 * entry, and the thread. Wide sheets show list + thread side by side; narrow
 * sheets show one at a time with a back button. */
export function feedbackView(env){
  if(typeof document!=='undefined'&&!document.querySelector('link[data-reviews-css]')){const l=document.createElement('link');l.rel='stylesheet';l.href='/css/reviews.css';l.dataset.reviewsCss='1';document.head.append(l);}
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
  const summary=`<section class="rv-summary"><div class="rv-score"><strong>${avg}</strong><span class="stars" aria-hidden="true">${stars(Math.round(c.rating||0))||'☆☆☆☆☆'}</span><small>${count} đánh giá</small></div><div class="rv-dist">${dist.map(([s,n])=>`<button type="button" class="rv-bar ${starF===s?'active':''}" data-action="v4FbStars" data-stars="${s}" aria-pressed="${starF===s}" aria-label="Lọc đánh giá ${s} sao: ${n}"><span>${s}★</span><i><em style="width:${Math.round(n/max*100)}%"></em></i><b>${n}</b></button>`).join('')}</div></section>`;
  const chips=`<div class="chip-row rv-chips"><button type="button" class="chip ${filter==='all'&&!starF?'selected':''}" data-action="v4FbFilter" data-tab="all">Tất cả · ${count}</button><button type="button" class="chip ${filter==='open'?'selected':''}" data-action="v4FbFilter" data-tab="open">Chưa trả lời · ${open}</button>${flagged||filter==='flag'?`<button type="button" class="chip ${filter==='flag'?'selected':''}" data-action="v4FbFilter" data-tab="flag">${icon('flag',12)} Đáng ngờ · ${flagged}</button>`:''}${starF?`<button type="button" class="chip selected" data-action="v4FbStars" data-stars="${starF}" aria-label="Bỏ lọc ${starF} sao">${starF}★ ${icon('x',12)}</button>`:''}</div>`;
  const st=c.feedback_stats||{criteria:[]};
  const crit=st.criteria?.length?`<details class="rv-criteria"><summary>Điểm theo tiêu chí</summary>${st.criteria.map(x=>`<div class="crit"><small>${esc(x.label)}</small><div class="bar ${x.avg<=3?'low':''}"><i style="width:${x.avg*20}%"></i></div><b>${x.avg}</b></div>`).join('')}${st.improved?`<p class="muted small">${st.improved} lần khách sửa sao lên sau khi bạn trả lời.</p>`:''}</details>`:'';
  const card=p=>{const f=p.feedback,s=f?.status;
    const tag=!f?'':f.removed?pill('Đã gỡ',''):s==='awaiting'?pill('Đang đọc…','blue'):s==='open'?`<span class="rv-reply">${icon('chat',13)} ${f.thread.length?'Khách hỏi lại':'Trả lời'}</span>`:f.ignored?pill('Đã bỏ qua',''):f.report==='rejected'?pill('Báo cáo bị từ chối','danger'):pill('Đã trả lời','green');
    const flags=f?.clues?.length&&!f.removed?`<span class="rv-flags">${f.clues.map(x=>`<span class="tag amber">${icon('flag',11)} ${esc(x)}</span>`).join('')}</span>`:'';
    return `<button type="button" class="rv-card ${p.id===shown?.id?'active':''}${f?.removed?' removed':''}" data-action="v4FbOpen" data-post="${esc(p.id)}"><span class="persona">${esc(f?.persona_emoji||'🙂')}</span><span class="grow"><span class="rv-top"><b>${esc(p.author)}</b>${p.stars?`<span class="stars" aria-label="${p.stars} sao">${stars(p.stars)}</span>`:''}</span><span class="rv-text">${esc(p.text)}</span>${flags}<small class="muted">Ngày ${p.day}${f?.title?` · ${esc(f.title)}`:''}</small></span><span class="rv-side">${tag}</span></button>`;};
  const list=all.length?rows.map(card).join('')||`<p class="muted small rv-none">Không có đánh giá nào ở mục này.</p>`:`<div class="empty">${icon('star',30)}<h3>Chưa có đánh giá nào</h3><p class="muted small">Làm xong việc cho khách, họ sẽ để lại lời nhắn ở đây.</p></div>`;
  const body=all.length?`<div class="fb-layout ${selected?'has-detail':''}"><section class="fb-list">${summary}${chips}<div class="stack rv-list">${list}</div>${crit}</section><section class="fb-detail ${selected?'':'auto'}">${shown?threadView(shown,env):''}</section></div>`:list;
  return head('Đánh giá',esc(place),'KHÁCH NÓI GÌ')+`<div class="sheet-body">${body}</div>`;
}
function threadView(p,env){
  const f=p.feedback,api=env.api,aiOn=api.state.settings.aiConsent&&api.ai?.configured;
  const back=`<button type="button" class="btn ghost small rv-back" data-action="v4FbBack">${icon('back',14)} Tất cả đánh giá</button>`;
  const top=`<div class="row rv-head"><span class="persona big">${esc(f?.persona_emoji||'🙂')}</span><div class="grow"><h3>${esc(p.author)}</h3>${p.stars?`<span class="stars" aria-label="${p.stars} sao">${stars(p.stars)}</span>`:''}${f&&p.stars&&p.stars!==f.stars_original?` <small class="muted">ban đầu ${f.stars_original}★</small>`:''}<small class="muted block">Ngày ${p.day}${f?.title?` · ${esc(f.title)}`:''}</small></div>${f?.persona_name?pill(esc(f.persona_name)):''}</div>`;
  if(!f)return `<article class="card review-card">${back}${top}<p class="review-text">“${esc(p.text)}”</p></article>`;
  const offered=f.thread.some(x=>x.role==='owner'&&x.offer&&x.offer!=='none');
  const crit=f.criteria.map(x=>`<div class="crit"><small>${esc(x.label)}</small><div class="bar ${x.score<=3?'low':''}"><i style="width:${x.score*20}%"></i></div><b>${x.score}</b>${x.note?`<small class="muted">${esc(x.note)}</small>`:''}</div>`).join('');
  const parent=api.state.current==='teacher';
  const thread=f.thread.map(x=>x.role==='guest'?guestBubble(x,parent):`<div class="bubble ${x.role==='owner'?'mine':'rv-said '+(x.decision||'')}"><small class="muted">${x.role==='owner'?'Bạn':esc(p.author)}${x.role==='owner'&&x.tone&&TONE_NAME[x.tone]?' · '+TONE_NAME[x.tone]:''}${x.offer&&x.offer!=='none'?' · '+offerLabel(x.offer,parent):''}${x.decision?' · '+decisionLabel(x.decision,x.stars):''}</small><p>${esc(x.text)}</p></div>`).join('');
  const canReply=f.status==='open'&&f.rounds<3;
  // Ready-made tones: the words decide what the reviewer does next.
  const worst=f.unfair?f.unfair.truth:(f.criteria.reduce((a,b)=>b.score<a.score?b:a,f.criteria[0])||{}).note||'';
  const tpl=parent?[['Nêu sự thật',`Dạ, theo sổ lớp hôm đó: ${worst}. Mong phụ huynh xem lại giúp ạ.`],['Xin lỗi','Cảm ơn phụ huynh đã góp ý. Tôi xin lỗi và sẽ điều chỉnh cách làm trong lớp ạ.'],['Mời trao đổi','Mời phụ huynh ghé lớp trao đổi trực tiếp, mình cùng giúp con nhé.'],['Đáp trả gắt','Phụ huynh không hài lòng thì chuyển lớp khác đi.']]
    :[['Nêu sự thật',`Dạ, theo phiếu ghi hôm đó: ${worst}. Bên mình gửi lại để cùng đối chiếu ạ.`],['Xin lỗi','Thành thật xin lỗi bạn vì trải nghiệm chưa tốt. Lần sau bên mình sẽ chú ý hơn và sửa quy trình ngay ạ.'],['Mời quay lại','Cảm ơn bạn đã ghé và góp ý. Mời bạn quay lại, bên mình sẽ phục vụ chu đáo hơn ạ.'],['Đáp trả gắt','Không thích thì đi chỗ khác, bên mình không tiếp loại khách như bạn.']];
  const tone=env.ui.fbTone?.post===p.id?env.ui.fbTone.tone:'free';
  const tplRow=f.tones?.length?`<div class="rv-tones" role="group" aria-label="Chọn giọng trả lời">${f.tones.map(t=>`<button type="button" class="rv-tone ${esc(t.risk)}${t.id===tone?' selected':''}" data-action="v4FbTpl" data-tone="${esc(t.id)}" data-text="${esc(t.text)}" aria-pressed="${t.id===tone}"${t.risk==='risky'?' title="Có thể được lòng, cũng có thể phản tác dụng"':''}><span aria-hidden="true">${esc(t.emoji)}</span><span class="rv-tone-txt"><b>${esc(t.label)}</b>${t.risk==='risky'?'<small>được ăn cả, ngã về không</small>':t.risk==='bad'?'<small>dễ bị chụp màn hình</small>':''}</span></button>`).join('')}<button type="button" class="rv-tone free${tone==='free'?' selected':''}" data-action="v4FbTpl" data-tone="free" data-text="" aria-pressed="${tone==='free'}"><span aria-hidden="true">✍️</span><b>Tự viết</b></button></div>`
    :`<div class="chip-row rv-tpl" role="group" aria-label="Gợi ý giọng trả lời">${tpl.map(([l,t],i)=>`<button type="button" class="chip${i===3?' rv-tpl-rude':''}" data-action="v4FbTpl" data-text="${esc(t)}">${l}</button>`).join('')}</div>`;
  const clues=f.clues?.length&&!f.report?`<div class="rv-clues" role="note">${icon('flag',14)}<div class="rv-flags">${f.clues.map(x=>`<span class="tag amber">${esc(x)}</span>`).join('')}</div></div>`:'';
  const reportQ=parent?'Báo cáo tin nhắn này với ban đại diện lớp? Chỉ tin nhắn nhầm lớp hoặc giả mới bị gỡ. Nếu là góp ý thật, phụ huynh sẽ biết và bực hơn.':'Báo cáo đánh giá này là giả hoặc nhầm quán? Nền tảng chỉ gỡ đánh giá giả, nhầm chỗ hoặc chưa dùng dịch vụ. Nếu là trải nghiệm thật, khách sẽ biết và hạ thêm sao.';
  const side=(f.can_report||f.can_ignore)?`<div class="row wrap rv-actions">${f.can_ignore?cmdBtn(`${icon('check',14)} Bỏ qua`,'fb_ignore',{post:p.id},'ghost small'):''}${f.can_report?confirmCmd(`${icon('flag',14)} Báo cáo`,'fb_report',{post:p.id},reportQ,'ghost small'):''}</div>`:'';
  const verdict=f.removed?`<p class="notice green" role="status">${icon('check',16)} Đã gỡ${f.kind_label?`: ${esc(f.kind_label)}`:''}. Không còn tính vào điểm trung bình.</p>`:f.report==='rejected'?`<p class="notice amber" role="status">${icon('flag',16)} Báo cáo bị từ chối${f.kind_label?` (${esc(f.kind_label)})`:''}: đây là trải nghiệm thật.</p>`:'';
  const choice=offered?'none':(env.ui.fbOffer||'none');
  const offers=offered?[['none','Không bù']]:[['none','Không bù'],...['drink','gift','refund'].map(id=>[id,offerLabel(id,parent,true)])];
  const form=canReply?`<form class="reply-box" data-v4-fb="${esc(p.id)}"><label class="field" for="fb-text">Trả lời ${esc(p.author)}</label>${tplRow}<input type="hidden" name="tone" value="${esc(tone)}"><textarea id="fb-text" class="input" rows="3" maxlength="600" data-preserve placeholder="${parent?'Cảm ơn, xin lỗi nếu cần, và nói rõ lớp sẽ làm gì…':'Cảm ơn, xin lỗi nếu cần, và nói rõ tiệm sẽ làm gì…'}" required></textarea>
    <div class="field">Bù đắp</div><div class="segmented rv-offer" role="radiogroup" aria-label="Bù đắp">${offers.map(([id,l])=>`<label><input type="radio" name="offer" value="${id}"${choice===id?' checked':''}><span>${l}</span></label>`).join('')}</div>
    <div class="row spread space-top"><small class="muted">Lượt ${f.rounds+1}/3</small><button class="btn primary" type="submit">${icon('send',14)} Gửi trả lời</button></div></form>`:
    f.status==='awaiting'?`<p class="notice blue">${icon('clock',16)} ${esc(p.author)} đang đọc trả lời của bạn…</p>`:f.removed||f.report?'':`<p class="muted small">${f.ignored?'Bạn đã bỏ qua đánh giá này.':'Cuộc trao đổi đã khép.'}</p>`;
  return `<article class="card review-card${f.removed?' removed':''}">${back}${top}<p class="review-text">“${esc(p.text)}”</p>${verdict}${clues}${f.unfair?`<details class="fact-check"><summary>${icon('search',14)} Đối chiếu sự thật</summary><p class="small">Khách nói: <b>${esc(f.unfair.claim)}</b>. Sổ ghi: ${esc(f.unfair.truth)}. Bạn có thể nhắc lại dữ kiện một cách lịch sự.</p></details>`:''}
    <details class="criteria"><summary>${parent?'Phụ huynh chấm theo tiêu chí':'Khách chấm theo tiêu chí'}</summary>${crit}</details>${thread?`<div class="thread">${thread}</div>`:''}${form}${side}
    ${f.status==='open'&&f.thread.length?`<div class="row space-top">${cmdBtn('Khép trao đổi','fb_close',{post:p.id},'ghost small')}</div>`:''}</article>`;
}
const TONE_NAME={warm:'ấm áp',funny:'hài hước',sassy:'cà khịa',facts:'nêu sự thật',sorry:'xin lỗi',invite:'mời quay lại',process:'giải thích',genz:'Gen Z',silent:'ngắn gọn',harsh:'gắt'};
function offerLabel(id,parent,full=false){
  const rows=parent?{drink:['kèm thêm một buổi','Kèm 1 buổi · 6 xu'],gift:['tặng sách 10 xu','Tặng sách · 10 xu'],refund:['hoàn 20 xu học phí','Hoàn 20 xu']}
    :{drink:['tặng quà nhỏ 6 xu','Quà nhỏ · 6 xu'],gift:['tặng voucher 10 xu','Voucher · 10 xu'],refund:['hoàn 20 xu','Hoàn 20 xu']};
  return (rows[id]||['',''])[full?1:0];}
function guestBubble(x,parent){
  const side={fan:parent?'bênh lớp':'bênh quán',troll:'hóng chuyện',other:parent?'phụ huynh khác':'khách khác'}[x.side]||'';
  return `<div class="bubble rv-guest ${esc(x.side||'')}"><small class="muted"><span aria-hidden="true">${esc(x.emoji||'💬')}</span> ${esc(x.name||'')}${side?` · ${side}`:''}</small><p>${esc(x.text)}</p></div>`;}
function decisionLabel(d,s){return {revise_up:`nâng lên ${s}★`,revise_down:`hạ xuống ${s}★`,argue:'muốn nói thêm',keep:'giữ nguyên'}[d]||d;}

/* ----------------------------------------------------------- Situation */
export function situationView(env){
  const {api}=env,c=api.state.careers[api.state.current],x=c.situation;
  const list=api.content.situations?.[api.state.current]||[];
  if(!x){
    const practice=list.map(s=>`<article class="card sit-practice"><div class="grow"><strong>${esc(s.title)}</strong><small class="muted block">${s.tone==='tense'?'Căng thẳng':'Nhẹ nhàng'}${s.swap?' · có góc nhìn đổi vai':''}</small></div>${cmdBtn('Diễn tập','sit_practice',{script:s.id},'ghost small')}</article>`).join('');
    return head('Tình huống','','CHUYỆN TRONG CA')+`<div class="sheet-body"><div class="empty">${icon('sun',30)}<h3>Hôm nay chưa có chuyện gì</h3><p class="muted small">Khi có chuyện cần bạn xử lý, nó sẽ hiện ở đây.</p><div class="row center space-top">${button('Về quầy','close',{},'primary')}</div></div>${practice?`<h4 class="section-title">Diễn tập trước</h4><div class="stack">${practice}</div>`:''}</div>`;
  }
  const n=api.content.npcs.find(p=>p.id===x.npc);
  const facts=x.facts.map(f=>`<article class="fact ${f.text?'read':''}"><div class="row spread"><strong>${icon(f.text?'check':'search',14)} ${esc(f.title)}</strong><small class="muted">${esc(f.source)}</small></div>${f.text?`<p class="small">${esc(f.text)}</p>`:cmdBtn('Xem dữ kiện','sit_read',{fact:f.id},'ghost small')}</article>`).join('');
  let actions='';
  if(x.stage!=='resolved'){
    actions=`<h4 class="section-title">Bạn sẽ làm gì?</h4><div class="choice-grid">${x.options.map(o=>{const locked=(o.requires||[]).some(r=>!x.read.includes(r));return `<button class="choice ${x.choice===o.id?'selected':''}" data-command="sit_choose" data-payload="${esc(JSON.stringify({option:o.id}))}"${locked?' disabled':''}><strong>${esc(o.label)}</strong><small>${o.cost?`Chi ${o.cost} xu`:''}${o.reward?` · +${o.reward} xu`:''}${locked?' · cần xem thêm dữ kiện':''}</small></button>`;}).join('')}</div>
      ${x.stage==='proposed'?`<div class="row space-top sit-foot">${confirmCmd(icon('check',14)+' Chốt cách xử lý','sit_confirm',{},'Chốt cách xử lý này? Kết quả sẽ ảnh hưởng tới khách, quan hệ và có thể cả đánh giá.','primary big')}</div>`:''}`;
  }else{
    actions=`<div class="outcome ${esc(x.quality)}"><span class="eyebrow">KẾT QUẢ</span><p>${esc(x.outcome)}</p></div>
      <h4 class="section-title">Mỗi người nhìn thấy điều gì</h4><div class="perspectives">${x.perspectives.map(v=>`<article class="perspective"><span class="p-emoji">${esc(v.emoji)}</span><div><b>${esc(v.who)}</b><p class="small">${esc(v.text)}</p></div></article>`).join('')}</div>
      ${x.lesson?`<p class="lesson">${icon('sparkle',15)} ${esc(x.lesson)}</p>`:''}<div class="row space-top sit-foot">${cmdBtn('Cất vào sổ','sit_dismiss',{},'primary big')}</div>`;
  }
  return head(esc(x.title),x.practice?'Diễn tập · không ảnh hưởng tiền, đánh giá hay quan hệ.':'Đọc dữ kiện trước khi quyết định.',x.tone==='tense'?'TÌNH HUỐNG CĂNG':'CHUYỆN TRONG CA')+
   `<div class="sheet-body"><div class="situation"><div class="row sit-open">${n?portrait(n,48):''}<p class="opening grow">“${esc(x.opening)}”</p></div>${x.swap?`<details class="swap"><summary>${icon('people',14)} Thử đặt mình vào vị trí người kia</summary><p class="small">${esc(x.swap)}</p></details>`:''}
   <h4 class="section-title">Dữ kiện</h4><div class="facts">${facts}</div>${actions}</div></div>`;
}

/* ------------------------------------------------------------- Job hunt */
export function jobView(env){
  const {api,ui}=env,id=api.state.current,c=api.state.careers[id],job=c.job,E=api.content.employment;
  const posts=E.postings[id]||[];const qs=E.questions[id]||{};
  const place=api.content.catalogue.find(x=>x.id===id)?.short||'';
  if(job.status==='hired'){
    const p=posts.find(x=>x.id===job.employer);
    return head('Hồ sơ công việc',esc(p?.org||''),'VIỆC LÀM · '+esc(place))+`<div class="sheet-body"><article class="card"><h3>${esc(job.title)}</h3><p>${esc(p?.culture||'')}</p><div class="kv"><div class="kv-row"><span>Lương</span><b>${job.salary} xu/ngày${job.probation?' · thử việc 85%':''}</b></div><div class="kv-row"><span>Ngày đã làm</span><b>${job.days_worked}</b></div>${job.probation?`<div class="kv-row"><span>Thử việc còn</span><b>${job.probation_left} ngày có làm việc</b></div>`:''}</div><p class="muted small">Lương trả khi khép ca nếu hôm đó bạn hoàn thành ít nhất một việc. Hết thử việc, đánh giá trung bình từ 3.5★ sẽ được ký chính thức.</p>${confirmCmd('Xin nghỉ việc','job_quit',{},'Nghỉ việc ở đây? Bạn cần ứng tuyển lại trước ca tiếp theo.','ghost small',c.open)}</article></div>`;
  }
  const app=job.application;
  if(job.status==='offer'){
    const p=posts.find(x=>x.id===app.posting),o=job.offer;
    return head('Thư mời nhận việc 🎉',esc(p.org),'VIỆC LÀM')+`<div class="sheet-body"><article class="card"><h3>${esc(p.title)}</h3><p>${o.direct?'Được mời thẳng, không cần phỏng vấn.':`Điểm hồ sơ: <b>${o.score}/100</b>.`} Mức lương đề nghị: <b>${o.salary} xu/ngày</b> (thử việc ${p.probation_days} ngày, nhận 85%).</p>${(app.feedback||[]).map(x=>`<p class="small muted">• ${esc(x)}</p>`).join('')}<div class="row wrap space-top">${confirmCmd('Ký hợp đồng thử việc','job_accept',{},`Nhận việc tại ${p.org} với ${o.salary} xu/ngày?`,'primary')}${o.negotiated?'':cmdBtn('Thương lượng lương','job_negotiate',{},'cream')}${cmdBtn('Từ chối','job_decline',{},'ghost')}</div></article></div>`;
  }
  if(job.status==='applying'&&app){
    const p=posts.find(x=>x.id===app.posting);
    let step='';
    if(app.stage==='cv'){
      const sel=ui.cvStrengths||[],claims=ui.cvClaims||['fresh'];
      step=`<h3>Bước 1 · CV</h3><p class="muted small">Nơi tuyển mong: ${p.wants.map(w=>esc(E.strengths.find(s=>s.id===w)?.name||w)).join(', ')}.</p><label class="field">Điểm mạnh (1–3)</label><div class="chip-row">${E.strengths.map(s=>`<button class="chip ${sel.includes(s.id)?'selected':''}" data-action="v4Cv" data-kind="strength" data-id="${s.id}">${esc(s.emoji)} ${esc(s.name)}</button>`).join('')}</div>
        <label class="field">Kinh nghiệm (1–4 dòng) — nơi tuyển sẽ kiểm tra tham chiếu</label><div class="stack">${E.claims.map(x=>`<button class="choice ${claims.includes(x.id)?'selected':''}" data-action="v4Cv" data-kind="claim" data-id="${x.id}">${esc(x.text)}</button>`).join('')}</div>
        <div class="row space-top">${cmdBtn('Nộp CV','job_cv',{strengths:sel,claims},'primary',!sel.length||!claims.length)}</div>`;
    }else if(app.stage==='letter'){
      const parts=ui.letter||{};
      step=`<h3>Bước 2 · Thư ứng tuyển</h3>${E.letter.map(slot=>`<label class="field">${esc(slot.title)}</label><div class="stack">${slot.options.map(o=>`<button class="choice ${parts[slot.id]===o.id?'selected':''}" data-action="v4Letter" data-slot="${slot.id}" data-id="${o.id}">${esc(o.label)}</button>`).join('')}</div>`).join('')}
        <div class="row space-top">${cmdBtn('Gửi thư','job_letter',{parts},'primary',Object.keys(parts).length<E.letter.length)}</div>`;
    }else if(app.stage==='interview'){
      const next=p.questions.find(q=>!(q in app.answers));const q=qs[next];
      step=`<h3>Bước 3 · Phỏng vấn</h3><p class="muted small">Câu ${Object.keys(app.answers).length+1}/${p.questions.length}</p>${(app.notes||[]).slice(-1).map(n=>`<p class="bubble small">${esc(n)}</p>`).join('')}${q?`<article class="card"><p><b>${esc(q.text)}</b></p><div class="stack">${q.options.map(o=>cmdBtn(esc(o.label),'job_answer',{question:next,option:o.id},'ghost full left')).join('')}</div></article>`:''}`;
    }
    return head(esc(p.title),esc(p.org),'ỨNG TUYỂN')+`<div class="sheet-body">${step}<div class="row space-top">${cmdBtn('Rút hồ sơ','job_withdraw',{},'ghost small')}</div></div>`;
  }
  const rejected=job.status==='rejected'?`<p class="notice amber">${icon('leaf',15)} Lần trước chưa được nhận (${esc(job.application?.feedback?.join(' ')||'')}). Có thể nộp lại từ ngày ${job.cooldown_day}.</p>`:'';
  return head('Xin việc: '+esc(place),'Nghề này cần được tuyển dụng. Chọn nơi phù hợp, viết CV trung thực và đi phỏng vấn.','TUYỂN DỤNG')+`<div class="sheet-body">${rejected}<div class="stack">${posts.map(p=>`<article class="card posting"><div class="row spread"><div><span class="eyebrow">${esc({public:'CÔNG LẬP',private:id==='teacher'?'TƯ THỤC':'TƯ NHÂN',community:'CỘNG ĐỒNG',corp:'DOANH NGHIỆP',startup:'KHỞI NGHIỆP',group:'TẬP ĐOÀN',firm:'CÔNG TY DỊCH VỤ',company:'CÔNG TY',branch:'CHI NHÁNH',service:'CÔNG TY DỊCH VỤ',subsidiary:'CÔNG TY CON',internship:'THỰC TẬP'}[p.kind]||'')}</span><h3>${esc(p.title)}</h3><small class="muted">${esc(p.org)}</small></div><b>${p.salary[0]}–${p.salary[1]} xu/ngày</b></div><p class="small">${esc(p.culture)}</p><div class="chip-row">${p.perks.map(x=>`<span class="chip">${esc(x)}</span>`).join('')}</div>
    <div class="row wrap space-top">${cmdBtn('Ứng tuyển','job_apply',{posting:p.id},'primary')}</div></article>`).join('')}</div></div>`;
}

/* ------------------------------------------------------------- Actions */
export async function v4Action(action,data,el,env){
  const {api,ui,cmd,confirmAction,renderSheet,openSheet}=env;
  switch(action){
    case'v4Cmd':{const payload=JSON.parse(data.payload||'{}');if(data.confirm&&!await confirmAction('Xác nhận',data.confirm,'Đồng ý'))return true;if(data.confirm)payload.confirm=true;await cmd(data.op,payload);return true;}
    case'inventory':openSheet('inventory');return true;
    case'feedback':if(data.filter){ui.fbFilter=data.filter;ui.fbStars=0;ui.fbPost=null;}openSheet('feedback');return true;
    case'fbGo':ui.fbPost=data.post||null;ui.fbFilter='all';ui.fbStars=0;openSheet('feedback');return true;
    case'situation':openSheet('situation');return true;
    case'jobapp':openSheet('jobapp');return true;
    case'v4InvTab':ui.invTab=data.tab;renderSheet(false);return true;
    case'v4Order':{if(ui.orderItem!==data.item)ui.orderQty=0;ui.orderItem=data.item||null;ui.invTab='stock';renderSheet(!ui.orderItem);return true;}
    case'v4Supplier':ui.orderSupplier=data.supplier;renderSheet();return true;
    case'v4Qty':{const inp=document.getElementById('order-qty'),max=Math.max(1,Number(inp?.max)||30),cur=Number(inp?.value)||ui.orderQty||1;
      ui.orderQty=Math.max(1,Math.min(max,data.set?Number(data.set):cur+Number(data.step||0)));renderSheet();return true;}
    case'v4Count':{const inp=document.getElementById(data.target);if(inp){inp.value=String(Math.max(0,Math.min(60,(Number(inp.value)||0)+Number(data.step||0))));(ui.invCount??={})[inp.dataset.v4Count]=inp.value;}return true;}
    case'v4InvOpen':openSheet('inventory',{invOpen:data.order,invTab:'orders'});requestAnimationFrame(()=>document.getElementById('crate-'+data.order)?.scrollIntoView({block:'nearest'}));return true;
    case'v4OrderGo':{
      const item=api.content.inventory.items[api.state.current].find(i=>i.id===data.item);if(!item)return true;
      const inp=document.getElementById('order-qty'),max=Math.max(1,Number(inp?.max)||30);
      const qty=Math.max(1,Math.min(max,Number(inp?.value)||ui.orderQty||1));ui.orderQty=qty;
      const sup=api.content.inventory.suppliers.find(x=>x.id===(ui.orderSupplier||'partner'));
      const cost=Math.max(1,Math.ceil(item.cost*qty*sup.factor));
      if(!await confirmAction('Đặt hàng?',`${qty} ${item.unit||'phần'} ${item.name} từ ${sup.name}: trả ${cost} xu ngay. Hàng chỉ vào kho sau khi bạn đếm nhận.`,'Đặt hàng'))return true;
      const r=await cmd('inv_order',{item:item.id,qty,supplier:sup.id,confirm:true});if(r){ui.orderItem=null;ui.orderQty=0;ui.invTab='orders';renderSheet(false);}
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
  }
  return false;
}
export async function v4Submit(form,env){
  const {api,cmd}=env;
  if(form.dataset.v4Receive){const id=form.dataset.v4Receive,count=Number(form.querySelector('input').value);
    if(await cmd('inv_receive',{order:id,count})){if(env.ui.invCount)delete env.ui.invCount[id];if(env.ui.invOpen===id)env.ui.invOpen=null;}return true;}
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
  if(el.name==='offer'&&el.closest('[data-v4-fb]')){env.ui.fbOffer=el.value;return true;}
  if(el.id==='fb-text'&&el.closest('[data-v4-fb]')){
    // Clearing the box means writing your own words.
    if(!el.value.trim()){const f=el.closest('form'),h=f.querySelector('input[name=tone]');if(h)h.value='free';f.querySelectorAll('.rv-tone').forEach(b=>{const on=b.dataset.tone==='free';b.classList.toggle('selected',on);b.setAttribute('aria-pressed',String(on));});env.ui.fbTone=null;}
    return true;}
  if(el.dataset.v4Qty!==undefined){
    const total=document.getElementById('order-total'),d=total?.dataset||{},max=d.max!==undefined?Number(d.max):30,typed=Number(el.value)||0;
    const q=env.ui.orderQty=Math.max(1,Math.min(Math.max(1,max),typed||1));
    if(total){
      const cost=Math.max(1,Math.ceil(Number(d.cost)*q*Number(d.factor))),money=Number(d.money);
      total.textContent=`Tổng: ${fmt(cost)} xu`;
      const after=document.getElementById('order-after');if(after)after.textContent=`Két còn ${fmt(Math.max(0,money-cost))} xu · kệ sau khi nhận ${Number(d.shelf)+q}/${d.cap}`;
      const why=!max?'Kệ đã đầy (tính cả hàng đang giao).':typed>max?`Chỉ còn chỗ cho ${max}.`:cost>money?`Chưa đủ xu: cần ${fmt(cost)}, két có ${fmt(money)}.`:'';
      const w=document.getElementById('order-why');if(w)w.textContent=why;
      const go=document.getElementById('order-go');if(go)go.disabled=Boolean(why)||typed<1;
    }
    return true;
  }
  if(el.dataset.v4Count!==undefined){(env.ui.invCount??={})[el.dataset.v4Count]=el.value;return true;}
  return false;
}
