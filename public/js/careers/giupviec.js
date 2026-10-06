/** Giúp việc theo giờ — cô Mai's Nhà Thơm team, cleaning clients' flats by the hour (server: game/careers/giupviec.py).
 * The morning cart (wash yesterday's cloths, top up the bottles, set off), then each flat: ring the bell and hear
 * the client, pick a room, take a tool and a product from the cart, tap a surface to wipe it (one tap, one wipe),
 * top to bottom and dry before wet, lift the vase off and put it back, the ring into the tray, the cat out of the
 * way, then the client's walk-through. The server decides everything; one tap sends one command. */
import {stepRows,nextHint,finalGo,pending,stepLine,firstTime} from '../v4/guide.js';
import {data,cc,lower,tile,introCard,deskCard,dayBar,person,askCard,bottom,kitActions,meter} from './street_kit.js';

const need=t=>t.needs||{};
const SPOT=(x,k)=>(cc(x).spots||{})[k]||{name:k,emoji:'✨',lvl:1,mat:'',tools:[],products:[]};
const ROOM=(x,k)=>(cc(x).rooms||{})[k]||{name:k,emoji:'🚪'};
const TOOL=(x,k)=>(cc(x).tools||{})[k]||{name:k,short:k,emoji:'🧽'};
const PROD=(x,k)=>(cc(x).products||{})[k]||{name:k,short:k,emoji:'💧'};
const CARE=(x,k)=>(cc(x).care||{})[k]||{name:k,emoji:'📦',kind:'fragile'};
const LEVEL=(x,l)=>(cc(x).levels||{})[l]||'';
const LV_EMOJI=['⬆️','🪑','🧹','💧'];
const key=(r,s)=>`${r}.${s}`;
const stockOf=(x,k)=>Number(data(x).stock?.[k]??x.room.inventory?.stock?.[k]??0);
/** The products that clean this surface in this home (a cat or a toddler: wet floors with clean water only). */
const rightProducts=(x,n,sid)=>n.gentle&&(cc(x).floor_wet||[]).includes(sid)?['nuoc']:SPOT(x,sid).products||[];
const spotsOf=(n,room)=>(n.rooms||[]).find(r=>r.id===room)?.spots||[];
const left=(t,room)=>spotsOf(need(t),room).filter(s=>!(need(t).skip||[]).includes(key(room,s.id))&&Number(t.dirt?.[key(room,s.id)])>0).length;
const itemsIn=(t,room)=>(need(t).items||[]).filter(i=>i.room===room);
const ctl=(cmd,payload)=>`[data-command="${cmd}"][data-payload='${JSON.stringify(payload)}']`;
/** What still stops a wipe with what is in hand (the server refuses the same: giupviec.py _wipe), or '' when ready. */
const bottleOf=(x,k)=>Number(data(x).cart?.bottles?.[k]||0);
const emptyBottle=(x,k)=>!!(k&&PROD(x,k).item&&bottleOf(x,k)<=0);
function handGap(x){
  const h=data(x).hand||{};
  if(!h.tool)return 'tool';
  if(!h.product)return 'product';
  return emptyBottle(x,h.product)?'empty':'';
}
const GAP_SAY={tool:'✋ Cầm một dụng cụ ở “Trên tay” trước đã.',product:'🧴 Chọn chai (hoặc lau khô) ở “Trên tay” trước đã.',empty:'🧴 Chai đang cầm cạn rồi: bấm “Châm” cạnh chai.'};
const dots=(v,max)=>`<span class="gv-dots" aria-label="còn ${v} lượt">${Array.from({length:Math.max(max,v)},(_,i)=>`<i class="${i<v?'on':''}"></i>`).join('')}</span>`;

/* ------------------------------------------------------------ the client and their words */
function ticket(t,x,slim=false){
  if(!t.known)return askCard(x,t,'🔔 Bấm chuông, nghe khách dặn');
  const n=need(t),notes=(n.notes||[]).map(k=>{const v=(cc(x).notes||{})[k]||['📝',k];return `<span class="gv-note">${x.esc(v[0])} ${x.esc(v[1])}</span>`;}).join('');
  const focus=(n.rooms||[]).flatMap(r=>r.spots.filter(s=>s.focus).map(s=>`<span class="gv-note amber">🔍 ${x.esc(SPOT(x,s.id).name)}</span>`)).join('');
  const tags=[t.regular?'<span class="tag green">⭐ Khách quen</span>':'',n.tet?'<span class="tag amber">🧧 Tổng vệ sinh</span>':''].join('');
  if(slim)return `<article class="card gv-slim"><p><b>${x.esc(x.npc(t.npc).display_name)}</b> <span class="muted small">· ${x.esc(n.place||t.title)}</span></p>${notes||focus?`<p class="gv-notes">${notes}${focus}</p>`:''}</article>`;
  return person(x,t,`<p class="small muted">📍 ${x.esc(n.place||'')}</p>${notes||focus?`<p class="gv-notes">${notes}${focus}</p>`:''}${n.note?`<p class="small gv-said">${x.esc(n.note)}</p>`:''}`,tags?`<span class="gv-tags">${tags}</span>`:'');
}

/* ------------------------------------------------------------ the rooms of this flat */
function roomTabs(t,x){
  return `<div class="gv-rooms" role="tablist" aria-label="Phòng">${(need(t).rooms||[]).map(r=>{const k=left(t,r.id),on=t.room===r.id,R=ROOM(x,r.id);
    return tile(x,'gv_room',{task:t.id,room:r.id},`<span class="tile-emoji">${x.esc(R.emoji)}</span><b>${x.esc(R.name)}</b><small>${k?`còn ${k} chỗ`:'✓ sạch'}</small>`,`gv-room ${on?'selected':''} ${k?'':'done'}`,on)
      .replace('<button ',`<button role="tab" aria-selected="${on}" `);}).join('')}</div>`;
}

/** The surfaces of the current room, grouped by height (top first), one tile each: tap = one wipe with what is in hand. */
function roomPanel(t,x){
  const n=need(t),room=t.room;
  if(!room)return `<section class="card gv-pick"><p class="gv-lead">🚪 Chọn phòng để bắt đầu dọn.</p></section>`;
  const R=ROOM(x,room),spots=spotsOf(n,room),start=Object.fromEntries(spots.map(s=>[s.id,s.dirt]));
  const on=Object.fromEntries(itemsIn(t,room).filter(i=>t.items?.[i.id]==='on').map(i=>[i.spot,i]));
  const levels=[...new Set(spots.map(s=>SPOT(x,s.id).lvl))].sort((a,b)=>a-b),gap=handGap(x);
  const groups=levels.map(l=>{const tiles=spots.filter(s=>SPOT(x,s.id).lvl===l).map(s=>{const sp=SPOT(x,s.id),k=key(room,s.id),v=Number(t.dirt?.[k]||0);
      const skip=(n.skip||[]).includes(k),item=on[s.id];
      const tagLine=skip?'<em class="gv-skip">🚫 Để nguyên</em>':item?`<em class="gv-on">${x.esc(CARE(x,item.id).emoji)} ${x.esc(CARE(x,item.id).name)}</em>`:s.focus?'<em class="gv-focus">🔍 Lau kỹ</em>':'';
      return tile(x,'gv_wipe',{task:t.id,spot:s.id},`<span class="tile-emoji">${x.esc(sp.emoji)}</span><b>${x.esc(sp.name)}</b><small>${x.esc(sp.mat||'')}</small>${skip?'':v?dots(v,start[s.id]):'<span class="gv-clean">✨ sạch</span>'}${tagLine}`,
        `gv-spot ${v&&!skip?'':'clean'} ${skip?'skip':''} ${item?'has-item':''} lv${l}`,t.stage!=='work'||!!gap);}).join('');
    return `<div class="gv-level"><h4 class="section-title">${LV_EMOJI[l]||''} ${x.esc(LEVEL(x,l))}</h4><div class="tile-grid gv-spots">${tiles}</div></div>`;}).join('');
  const care=itemsIn(t,room).map(i=>{const c=CARE(x,i.id),st=t.items?.[i.id];
    if(st==='on')return x.cmd(`${x.esc(c.emoji)} ${x.esc(c.move||c.name)}`,'gv_move',{task:t.id,item:i.id},'small gv-move');
    if(st==='off'&&c.kind==='fragile')return x.cmd(`${x.esc(c.emoji)} ${x.esc(c.back||c.name)}`,'gv_back',{task:t.id,item:i.id},'small gv-back');
    const said={off:c.kind==='pet'?'đã bế ra':'đang để ngoài',back:'đã đặt lại',safe:'trong khay',broken:'đã vỡ'}[st]||'';
    return `<span class="tag ${st==='broken'?'red':'green'}">${x.esc(c.emoji)} ${x.esc(said)}</span>`;}).join('');
  return `<section class="card gv-room-card"><h4>${x.esc(R.emoji)} ${x.esc(R.name)} <small class="muted">còn ${left(t,room)} chỗ</small></h4>
    ${care?`<div class="gv-care">${care}</div>`:''}${gap?`<p class="gv-lead gv-gap" role="status">${x.esc(GAP_SAY[gap])}</p>`:''}${groups}</section>`;
}

/** What is in hand: one tool, one product (or dry). */
function handPanel(x){
  const d=data(x),h=d.hand||{},b=d.cart?.bottles||{};
  const tools=Object.entries(cc(x).tools||{}).map(([k,v])=>x.cmd(`<span aria-hidden="true">${x.esc(v.emoji)}</span> ${x.esc(v.short)}${v.note?`<small>${x.esc(v.note)}</small>`:''}`,'gv_tool',{tool:k},`small gv-chip ${h.tool===k?'primary':'ghost'}`)
    .replace('<button ',`<button aria-pressed="${h.tool===k}" `)).join('');
  const prods=Object.entries(cc(x).products||{}).map(([k,v])=>{const uses=v.item?Number(b[k]||0):null;
    const chip=x.cmd(`<span aria-hidden="true">${x.esc(v.emoji)}</span> ${x.esc(v.short)}${uses!=null?`<small>${uses?`${uses} lượt`:'cạn'}</small>`:''}`,'gv_product',{product:k},`small gv-chip ${h.product===k?'primary':'ghost'} ${uses===0?'empty':''}`,uses===0)
      .replace('<button ',`<button aria-pressed="${h.product===k}" `);
    if(uses!==0)return chip;
    // An empty bottle: refill it right here from the stock room (gv_fill works mid-job), the chip itself stays locked.
    const s=stockOf(x,v.item);
    return `<span class="gv-chip-pair">${chip}${x.cmd(`🧴 Châm <small>${s?`📦 ${s}`:'hết kho'}</small>`,'gv_fill',{product:k},'small gv-fill-now',!s)}</span>`;}).join('');
  return `<section class="card gv-hand"><h4>🧺 Trên tay <small class="muted">${h.tool?x.esc(TOOL(x,h.tool).name):'chưa cầm gì'}${h.product?` · ${x.esc(lower(PROD(x,h.product).name))}`:''}</small></h4>
    <div class="gv-chips" role="group" aria-label="Dụng cụ">${tools}</div><div class="gv-chips" role="group" aria-label="Chai">${prods}</div></section>`;
}

/* ------------------------------------------------------------ the morning cart */
function setupPanel(t,x){
  const d=data(x),cart=d.cart||{},full=Number(cc(x).bottle||12);
  const rows=(cc(x).bottles||[]).map(p=>{const v=PROD(x,p),n=Number(cart.bottles?.[p]||0),s=stockOf(x,v.item);
    return `<li><span class="gv-bottle">${x.esc(v.emoji)} ${x.esc(v.short)}</span>${meter(n,full,n<Number(cc(x).bottle_low||3)?'low':'')}<small>${n}/${full}</small>${x.cmd(`Châm đầy <small>📦 ${s}</small>`,'gv_fill',{product:p},'small gv-fill',n>=full||!s)}</li>`;}).join('');
  return `<section class="card gv-setup"><h4>🧺 Khăn lau</h4><div class="sk-row">${cart.cloths==='clean'?'<span class="tag green">✓ Khăn sạch, ba màu</span>':x.cmd('🧺 Giặt khăn','gv_wash',{},'primary gv-wash')}</div>
    <h4 class="section-title">🧴 Chai trên xe</h4><ul class="gv-bottles">${rows}</ul><p class="small muted">${x.esc(need(t).note||'')}</p></section>`;
}
function setupSteps(t,x){
  const d=data(x),cart=d.cart||{},low=Number(cc(x).bottle_low||3)+3,rows=[];
  rows.push({ok:cart.cloths==='clean'?true:null,label:'Giặt khăn hôm qua',go:{cmd:'gv_wash',payload:{},label:'🧺 Giặt khăn'}});
  for(const p of cc(x).bottles||[]){const n=Number(cart.bottles?.[p]||0),v=PROD(x,p);
    if(n<low)rows.push({ok:null,label:`Châm chai ${lower(v.short)}`,note:`còn ${n} lượt`,go:stockOf(x,v.item)?{cmd:'gv_fill',payload:{product:p},label:`${v.emoji} Châm đầy`}:null});}
  return rows;
}

/* ------------------------------------------------------------ học nghề: the first flats with cô Mai */
function learnCard(x,full=true){
  const l=data(x).learn;if(!l?.on)return '';
  return `<p class="gv-learn" aria-label="Học nghề">🧺 Học nghề với cô Mai · nhà ${Math.min(l.n+1,l.of)}/${l.of} · <b>${x.esc(l.title||'')}</b>${full?`<small>${x.esc(l.text||'')}</small>`:''}</p>`;
}

/* ------------------------------------------------------------ the guide */
const CART_GO={sel:'.gv-cart-go',label:'🧺 Về soạn xe'};
const liveSetup=x=>(x.room.tasks||[]).find(v=>v.kind==='setup'&&!['completed','cancelled','referred'].includes(v.status));
/** The cart never went out today (skipped, or the morning task was dropped when leaving mid-shift): no flat
 * can be cleaned, so the bench gives way to one button back to the cart. A live morning task just opens
 * (the app's own "job" action); a dropped one is reopened by the server first (gv_cart, actions.cart). */
function cartBack(x){
  const s=liveSetup(x),go=s?x.button(CART_GO.label,'job',{task:s.id},'primary full gv-cart-go'):x.button(CART_GO.label,'car:cart',{},'primary full gv-cart-go');
  return `<section class="card gv-cart-back"><p class="gv-lead">🧺 Xe đồ nghề chưa soạn: giặt khăn, châm chai rồi mới lên đường tới nhà khách được.</p>${go}</section>`;
}
const isFirst=x=>firstTime(x)||!(Number(data(x).stats?.jobs)>0);
function jobSteps(t,x){
  const d=data(x),n=need(t),h=d.hand||{},rows=[],teach=!!d.learn?.on||isFirst(x);
  for(const r of n.rooms||[]){
    const R=ROOM(x,r.id);
    if(t.room!==r.id){const k=left(t,r.id),back=itemsIn(t,r.id).some(i=>t.items?.[i.id]==='off'&&CARE(x,i.id).kind==='fragile');
      rows.push({ok:k||back?null:true,label:`Dọn ${lower(R.name)}`,note:k?`còn ${k} chỗ`:'',go:k||back?{cmd:'gv_room',payload:{task:t.id,room:r.id},label:`${R.emoji} Sang ${lower(R.name)}`}:null});continue;}
    for(const i of itemsIn(t,r.id))if(t.items?.[i.id]==='on'){const c=CARE(x,i.id);
      rows.push({ok:null,label:c.move||c.name,go:teach?{cmd:'gv_move',payload:{task:t.id,item:i.id},label:`${c.emoji} ${c.move||c.name}`}:{sel:ctl('gv_move',{task:t.id,item:i.id}),label:`${c.emoji} ${c.move||c.name}`}});}
    const spots=[...r.spots].sort((a,b)=>SPOT(x,a.id).lvl-SPOT(x,b.id).lvl);
    for(const s of spots){const k=key(r.id,s.id),v=Number(t.dirt?.[k]||0),sp=SPOT(x,s.id);
      if((n.skip||[]).includes(k))continue;
      if(!v){rows.push({ok:true,label:sp.name});continue;}
      const wipe={cmd:'gv_wipe',payload:{task:t.id,spot:s.id}};
      const gap=handGap(x),fill=k=>({cmd:'gv_fill',payload:{product:k},label:`${PROD(x,k).emoji} Châm chai ${lower(PROD(x,k).short)}`});
      let go={sel:ctl(wipe.cmd,wipe.payload),label:`${sp.emoji} ${sp.name}`};
      if(teach){const tools=sp.tools||[],prods=rightProducts(x,n,s.id),want=prods.includes(h.product)?h.product:prods[0];
        if(!tools.includes(h.tool))go={cmd:'gv_tool',payload:{tool:tools[0]},label:`${TOOL(x,tools[0]).emoji} Cầm ${lower(TOOL(x,tools[0]).name)}`};
        else if(emptyBottle(x,want))go=fill(want);
        else if(!prods.includes(h.product))go={cmd:'gv_product',payload:{product:prods[0]},label:`${PROD(x,prods[0]).emoji} ${prods[0]==='kho'?'Lau khô':`Dùng ${lower(PROD(x,prods[0]).name)}`}`};
        else go={...wipe,label:`${sp.emoji} ${TOOL(x,h.tool).verb||'Lau'} ${lower(sp.name)}`};}
      else if(gap==='empty')go={sel:ctl('gv_fill',{product:h.product}),label:fill(h.product).label};
      else if(gap)go={sel:'.gv-hand',label:gap==='tool'?'✋ Cầm dụng cụ trước':'🧴 Chọn chai trước'};
      rows.push({ok:null,label:sp.name,note:`${v} lượt`,go});}
    for(const i of itemsIn(t,r.id))if(t.items?.[i.id]==='off'&&CARE(x,i.id).kind==='fragile'){const c=CARE(x,i.id);
      rows.push({ok:null,label:c.back||c.name,go:left(t,r.id)?null:{cmd:'gv_back',payload:{task:t.id,item:i.id},label:`${c.emoji} ${c.back||c.name}`}});}
  }
  return rows;
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện vừa xảy ra',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'gv_intro',payload:{},label:'🧹 Vào việc thôi!'}}],final:null};
  if(t.kind==='setup'){const steps=setupSteps(t,x);return {steps,final:{label:'🛵 LÊN ĐƯỜNG',go:finalGo(steps,'gv_open',{task:t.id}),ready:true}};}
  if(!d.cart?.out)return {steps:[{ok:null,label:'Soạn xe, lên đường trước',go:CART_GO}],final:null};
  if(!t.known)return {steps:[{ok:null,label:'Nghe khách dặn',go:{cmd:'ask',payload:{task:t.id},label:'🔔 Bấm chuông, nghe khách dặn'}}],final:null,pulse:'.sk-ask'};
  const steps=jobSteps(t,x),started=!!t.room||Number(t.scrubs)>0;
  return {steps,first:!!d.learn?.on,final:{label:'🚪 MỜI KHÁCH KIỂM NHÀ',go:finalGo(steps,'gv_check',{task:t.id}),ready:started,why:'chọn phòng để bắt đầu'}};
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse,glow:!!g.first});

/* ------------------------------------------------------------ idle: the cart between flats */
function cartView(x){
  const d=data(x),c=d.cart||{},b=c.bottles||{},s=d.stats||{};
  const bottles=(cc(x).bottles||[]).map(p=>`${x.esc(PROD(x,p).emoji)} ${Number(b[p]||0)}`).join(' · ');
  return `<section class="card gv-idle"><h4>🧺 Xe đồ nghề</h4><p class="small">${c.cloths==='clean'?'✓ Khăn sạch':'🧺 Khăn cần giặt'} · ${bottles}</p>
    <p class="small muted">🧹 ${Number(s.jobs||0)} nhà đã dọn · ⭐ ${Number(s.perfect||0)} nhà khách khen sạch · 💍 ${Number(s.kept||0)} món đồ quý đã cất giữ</p></section>`;
}

export default {
  id:'giupviec',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='setup'?'Giặt khăn, châm chai':!data(x).cart?.out?'Về soạn xe':!t.known?'Bấm chuông, nghe khách dặn':'Dọn nhà cho khách';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    const top=`${introCard(x,'gv_intro','🧹')}${deskCard(x,'gv_desk','Chuyện ở nhà khách')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk gv">${hint}${top}${bottom(x,g)}</div>`;
    if(t.kind==='setup')return `<div class="career-job sk gv">${hint}${top}${dayBar(x)}<div class="workbench"><section class="wb-main">${setupPanel(t,x)}</section><aside class="wb-side">${stepRows(x,g.steps,'Soạn xe')}</aside></div>${bottom(x,g)}</div>`;
    if(!d.cart?.out)return `<div class="career-job sk gv">${hint}${top}${t.known?ticket(t,x,true):''}${cartBack(x)}${dayBar(x)}${bottom(x,g)}</div>`;
    if(!t.known)return `<div class="career-job sk gv">${hint}${top}${learnCard(x)}${ticket(t,x)}${dayBar(x)}${bottom(x,g)}</div>`;
    const bench=`${roomTabs(t,x)}<div class="workbench"><section class="wb-main">${roomPanel(t,x)}</section><aside class="wb-side">${t.room?handPanel(x):''}${stepRows(x,g.steps,'Việc trong nhà')}</aside></div>`;
    return `<div class="career-job sk gv">${hint}${top}${learnCard(x,!t.room)}${ticket(t,x,!!t.room)}${bench}${dayBar(x)}${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x),top=`${introCard(x,'gv_intro','🧹')}${deskCard(x,'gv_desk','Chuyện ở nhà khách')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro){const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện vừa xảy ra',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'gv_intro',payload:{},label:'🧹 Vào việc thôi!'}}],final:null};
      return `<div class="career-job sk gv">${hintFor(g,x)}${top}${bottom(x,g)}</div>`;}
    return `<div class="career-job sk gv">${top}${dayBar(x)}${x.room.open&&!d.cart?.out?cartBack(x):''}${cartView(x)}</div>`;
  },
  summary(sum,x){
    if(!sum||sum.jobs==null)return '';
    const row=(l,v)=>`<div class="kv-row"><span>${l}</span><b>${v}</b></div>`,tm=sum.tomorrow,names={chai_kinh:'chai lau kính',chai_da_nang:'chai tẩy rửa dịu',chai_dau_mo:'chai tẩy dầu mỡ',chai_toilet:'chai tẩy bồn cầu',chai_lau_san:'can nước lau sàn'};
    const lines=[sum.low?.length?`📦 Sắp hết: ${sum.low.map(k=>x.esc(names[k]||k)).join(' · ')}`:''].filter(Boolean);
    const plan=`<section class="gv-plan" aria-label="Ngày mai"><h4 class="section-title">🌅 Ngày mai</h4>${tm?`<p class="gv-tomorrow"><span aria-hidden="true">${x.esc(tm.emoji)}</span> <b>Mai: ${x.esc(tm.label)}</b><small>${x.esc(tm.hint)}</small></p>`:''}${lines.length?`<ul class="gv-plan-list">${lines.map(l=>`<li>${l}</li>`).join('')}</ul>`:''}${x.button('🧺 Mở Kho','warehouse',{},'primary small gv-plan-go')}</section>`;
    const kv=`<div class="kv">${row('Nhà đã dọn',sum.jobs)}${row('Phòng',sum.rooms)}${row('Khách khen sạch',`${sum.perfect}/${sum.jobs}`)}${row('Tiền công',`${x.fmt?x.fmt(sum.earned):sum.earned} xu`)}</div>${(sum.lines||[]).length?`<ul class="small">${sum.lines.map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul>`:''}${sum.note?`<p class="small muted">${x.esc(sum.note)}</p>`:''}`;
    return `<article class="card space-top gv-sum">${plan}<details class="gv-sum-more"><summary>🧹 Hôm nay · ${sum.jobs} nhà · ${sum.perfect} nhà khen sạch${sum.earned?` · 💵 ${x.fmt?x.fmt(sum.earned):sum.earned} xu`:''}</summary>${kv}</details></article>`;
  },
  actions:{...kitActions,
    // 🧺 Về soạn xe when today's morning task is gone: the server reopens it, then the sheet opens it like a tap on it.
    async cart(d,el,x){const r=await x.send('gv_cart',{},{quiet:true});if(!r)return;x.render();setTimeout(()=>document.querySelector('.gv-cart-back [data-action="job"]')?.click(),0);}},
  dock:[['inventory','box','Kho tổ giúp việc','Chai lau kính, tẩy rửa, nước lau sàn…']],
};
