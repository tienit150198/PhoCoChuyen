/** Tiệm quà mẹ & bé — shelf with age labels, wrapping desk with occasion cards,
 * safety advice, first-time-parent kits, a returns desk and shop surprises.
 * game/giftshop.py (day 2+) and the engine's shop_* actions are the referee.
 * The care corner (regular families, subscription pickups, the diaper & formula
 * shelf, the baby-shower registry) is refereed by game/careers/mother_baby.py. */
import {itemArt} from '../icons.js';
import {Sound} from '../audio.js';
import {reqList,fold} from '../ui-kit.js';

const DONE=['completed','referred','cancelled'];
const USE_EMOJI={sleep:'🌙',bath:'🛁',feed:'🍼',play:'🧸',wear:'🧦',card:'💌'};
const RESOLVE=[['refund','💵 Hoàn tiền','Trả lại đúng giá món'],['exchange','🔁 Đổi món mới','Lấy món mới trên kệ'],['credit','🎟️ Phiếu mua hàng','Giá trị bằng món, dùng lần sau'],['decline','🙏 Từ chối nhẹ nhàng','Giải thích chính sách của tiệm']];
const TOPICS=[['age','👶 Bé được bao lâu rồi?'],['need','💭 Nhà mình đang lo nhất điều gì?'],['budget','👛 Mình định chi khoảng bao nhiêu?']];

const G=x=>x.room.data?.gift||{};
const pay=(x,o)=>x.esc(JSON.stringify(o));
// Shop taps go through actions.go: the result shows in one status line instead of a toast per tap.
const cmdAttr=(x,command,payload)=>`data-action="car:go" data-op="${command}" data-payload="${pay(x,payload)}"`;
const qb=(x,label,command,payload={},style='',disabled=false)=>`<button type="button" class="btn ${style}" ${cmdAttr(x,command,payload)}${disabled?' disabled':''}>${label}</button>`;
const sfx=new Sound();
async function run(x,op,payload){
  sfx.configure(x.state.settings||{});sfx.unlock();
  try{
    const r=await x.api.command(op,payload)||{};
    x.ui.flash=op==='ask'?'':r.message||'';
    if(r.celebrate)sfx.success();else if(r.correct===false)sfx.error();else sfx.click();
    if(r.message&&(r.celebrate||r.correct===false||/khách mới|bỏ về|hủy|quá giờ/.test(r.message)))x.toast(r.message,r.correct===false?'error':r.celebrate?'good':false);
    for(const note of new Set(r.effects||[]))x.toast(note);
    x.render();return r;
  }catch(error){sfx.error();x.toast(error.status?error.message:'Mất kết nối. Việc đã xác nhận vẫn được giữ, thử lại sau một chút nhé.',true);return null;}
}
const product=(x,id)=>(x.content.products||[]).find(p=>p.id===id)||{id,name:id,price:0,icon:'box',color:'cream'};
const price=(x,id)=>x.room.life?.prices?.[id]||product(x,id).price;
const label=(x,id)=>(G(x).labels||{})[id]||null;
const open=t=>!DONE.includes(t.status);
const count=b=>Object.values(b||{}).reduce((a,v)=>a+v,0);
const total=(x,b)=>Object.entries(b||{}).reduce((a,[k,v])=>a+price(x,k)*v,0);

/* ---------------------------------------------------------------- art for the new shelf items */
const ART={
  rattle:`<rect x="40" y="46" width="8" height="34" rx="4" fill="#caa06a"/><circle cx="44" cy="82" r="6" fill="#e2b979"/><circle cx="44" cy="32" r="20" fill="#f3d9a4" stroke="#b98d55" stroke-width="2.5"/><circle cx="36" cy="28" r="3.5" fill="#e59aa9"/><circle cx="50" cy="26" r="3.5" fill="#8fbfb0"/><circle cx="46" cy="39" r="3.5" fill="#9fb6dc"/>`,
  teether:`<circle cx="44" cy="46" r="24" fill="none" stroke="#9fd0bd" stroke-width="11"/><circle cx="44" cy="46" r="24" fill="none" stroke="#ffffff66" stroke-width="3" stroke-dasharray="4 7"/><circle cx="44" cy="17" r="7" fill="#f2b8c6"/><circle cx="68" cy="58" r="6" fill="#f6d488"/>`,
  bottle:`<path d="M36 14h16l2 10H34Z" fill="#f2b8c6"/><rect x="31" y="22" width="26" height="8" rx="3" fill="#9fb6dc"/><path d="M30 30h28v46q0 6-6 6H36q-6 0-6-6Z" fill="#eef6fb" stroke="#8aa9c4" stroke-width="2.5"/><path d="M30 58h28v18q0 6-6 6H36q-6 0-6-6Z" fill="#fbf4e3"/><path d="M50 40h6M50 50h6M50 60h6M50 70h6" stroke="#8aa9c4" stroke-width="2"/>`,
  bib:`<path d="M22 24q22-16 44 0l2 34q-24 30-48 0Z" fill="#f2b8c6" stroke="#c9879a" stroke-width="2.5"/><path d="M32 24q12 12 24 0" fill="#fffaf2" stroke="#c9879a" stroke-width="2.5"/><path d="M30 58q14 10 28 0v10q-14 8-28 0Z" fill="#e59aa9"/><circle cx="44" cy="44" r="5" fill="#fff4f6"/>`,
  socks:`<path d="M20 18h16v34q0 6 6 9l8 4q6 4 2 10t-12 2L22 68q-4-3-3-10Z" fill="#f4ead6" stroke="#b99f7a" stroke-width="2.2"/><path d="M48 22h16v34q0 6 6 9l6 3q5 4 1 9t-11 1L50 72q-4-3-3-10Z" fill="#dcebf4" stroke="#7fa3bd" stroke-width="2.2"/><path d="M20 24h16M48 28h16" stroke="#e59aa9" stroke-width="3"/>`,
  book:`<rect x="16" y="20" width="56" height="56" rx="8" fill="#bfe0cf" stroke="#6f9c86" stroke-width="2.5"/><path d="M44 20v56" stroke="#6f9c86" stroke-width="2.5"/><path d="M16 30l-5 4 5 4-5 4 5 4-5 4 5 4" fill="none" stroke="#f6d488" stroke-width="3"/><circle cx="30" cy="44" r="7" fill="#f6d488"/><path d="M52 40q6-8 12 0q-6 8-12 0Z" fill="#f2b8c6"/><path d="M56 58h10" stroke="#fffaf2" stroke-width="3" stroke-linecap="round"/>`,
  blanket:`<path d="M14 34q30-14 60 0v38q-30 10-60 0Z" fill="#cfe1f1" stroke="#7fa3bd" stroke-width="2.5"/><path d="M14 34q30 12 60 0" fill="none" stroke="#7fa3bd" stroke-width="2"/><path d="M32 56a7 7 0 0112-5 6 6 0 016 10H34a5 5 0 01-2-5" fill="#ffffff"/><path d="M20 66q24 8 48 0" stroke="#ffffffaa" stroke-width="3" fill="none"/>`,
  envelope:`<rect x="24" y="12" width="40" height="66" rx="5" fill="#d9483b" stroke="#a8322a" stroke-width="2"/><path d="M24 20q20 16 40 0" fill="#c23a2f"/><circle cx="44" cy="46" r="10" fill="#f3c55a" stroke="#c99a2e" stroke-width="2"/><path d="M40 46h8M44 42v8" stroke="#a8322a" stroke-width="2"/>`,
};
function art(p,size=72){
  if(!ART[p.icon])return itemArt(p.icon,size,p.color);
  return `<svg class="item-art" width="${size}" height="${size}" viewBox="0 0 88 96" role="img" aria-label="${p.name}"><ellipse cx="44" cy="87" rx="28" ry="5" fill="#4c463214"/>${ART[p.icon]}</svg>`;
}

/* ---------------------------------------------------------------- helpers */
function guestOf(t,x){
  const g=t.gift?.guest;if(g)return {name:g.name,emoji:g.emoji,npc:null};
  const n=x.npc(t.npc);return {name:n.display_name,emoji:null,npc:n};
}
const face=(g,x,size=58)=>g.emoji?`<span class="mb-face" style="--s:${size}px" aria-hidden="true">${x.esc(g.emoji)}</span>`:`<span class="mb-face portrait" style="--s:${size}px" aria-hidden="true">${x.portrait(g.npc,size)}</span>`;
function legacyRequest(t,x){
  const n=t.needs;if(!n)return null;
  const paper=(x.content.papers||[]).find(p=>p.id===n.paper);
  return `Cần ${n.qty} × ${product(x,n.product).name}, tối đa ${n.budget} xu${n.gift?`, gói giấy ${paper?paper.name.toLocaleLowerCase('vi'):n.paper}`:', không cần gói'}.`;
}
function draft(t,x){
  const d=(x.ui.drafts??={})[t.id]??={paper:t.pack?.paper||'cream',ribbon:t.pack?.ribbon||'gold',tag:t.pack?.tag||null,card:t.pack?.card||'Gửi bé một ngày thật dịu dàng.'};
  return d;
}
function stage(t){
  const kind=t.gift?.kind;
  if(kind==='return')return 'return';
  if(!Object.keys(t.basket||{}).length)return 'shelf';
  if(t.needs?.gift&&!t.pack)return 'pack';
  return 'checkout';
}

/* ---------------------------------------------------------------- parts */
function hud(x){
  const g=G(x),mod=g.modifier||{},left=x.room.tasks.filter(open).length,today=g.today||{};
  return `<div class="mb-hud" role="status">${mod.title?`<span class="mb-chip mod">${x.esc(mod.emoji||'')} ${x.esc(mod.title)}</span>`:''}
    ${g.date?`<span class="mb-chip">📅 ${x.esc(g.date)}</span>`:''}<span class="mb-chip">🛍️ Còn <b>${left}</b> khách</span>
    ${today.sold?`<span class="mb-chip">🎁 ${today.sold} đơn</span>`:''}${g.care?.due?`<span class="mb-chip warn">📦 ${g.care.due} hẹn lấy gói</span>`:''}${today.advised?`<span class="mb-chip good">🛡️ ${today.advised} lần tư vấn</span>`:''}</div>`;
}
function eventCard(x){
  const ev=G(x).event;if(!ev)return '';
  let body='';
  if(ev.stage==='open'){
    let extra='';
    if(ev.kind==='formula'){
      const pulled=new Set(ev.facts?.pulled||[]);
      extra=`<div class="mb-cans">${(ev.facts?.cans||[]).map(c=>`<button type="button" class="mb-can ${pulled.has(c.id)?'pulled':''}" ${cmdAttr(x,'gift_event',{can:c.id})} aria-pressed="${pulled.has(c.id)}"><span aria-hidden="true">🥫</span><b>${x.esc(c.name)}</b><small>HSD ${x.esc(c.date)}</small>${pulled.has(c.id)?'<em>Đã rút</em>':''}</button>`).join('')}</div>`;
    }
    if(ev.kind==='fake'&&ev.facts?.labels?.length)extra=`<ul class="mb-labels">${ev.facts.labels.map(l=>`<li>🏷️ ${x.esc(l)}</li>`).join('')}</ul>`;
    body=`<p>${x.esc(ev.text)}</p>${extra}<div class="mb-choices">${(ev.choices||[]).map(o=>`<button type="button" class="btn ${o.id==='done'?'primary':'cream'}" ${cmdAttr(x,'gift_event',{choice:o.id})}${o.cost&&x.room.money<o.cost?' disabled':''}><span>${x.esc(o.label)}</span>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}</button>`).join('')}</div>`;
  }else body=`<p class="mb-result ${ev.good?'good':'bad'}">${x.esc(ev.result||'')}</p>${(ev.effects||[]).length?`<ul class="mb-effects">${ev.effects.map(e=>`<li>${x.esc(e)}</li>`).join('')}</ul>`:''}${qb(x,'Làm tiếp','gift_event_ok',{},'primary')}`;
  // A modal over the shop so it is never scrolled out of view; tick() moves focus into it.
  return `<div class="mb-modal"><section class="mb-event" role="alertdialog" aria-modal="true" aria-labelledby="mbEvTitle"><h3 id="mbEvTitle"><span aria-hidden="true">${x.esc(ev.emoji||'❗')}</span> ${x.esc(ev.title)}</h3>${body}</section></div>`;
}
function customer(t,x){
  const g=guestOf(t,x),p=x.room.life?.mode==='calm'?100:(t.patience??100),v=t.gift||{};
  const words=t.known?(v.request||legacyRequest(t,x)||t.opening):t.opening;
  const facts=[];
  if(t.known&&v.age!=null)facts.push(`👶 Bé ${v.age>=12?`${Math.floor(v.age/12)} tuổi`:`${v.age} tháng`}`);
  if(t.known&&t.needs?.budget!=null&&v.kind!=='return')facts.push(`👛 Tối đa ${t.needs.budget} xu`);
  if(v.discount)facts.push(`🏷️ Bớt ${v.discount} xu`);
  return `<section class="mb-customer"><div class="mb-who">${face(g,x)}<small>${x.esc(g.name)}</small></div>
    <div class="mb-bubble">${t.known&&t.opening!==words?`<p class="mb-hello">${x.esc(t.opening)}</p>`:''}<p>“${x.esc(words)}”</p>
      ${facts.length?`<div class="mb-tags">${facts.map(f=>`<span>${x.esc(f)}</span>`).join('')}</div>`:''}
      <div class="mb-patience ${p<40?'low':p<70?'mid':''}"><span>KIÊN NHẪN</span><div class="mb-bar"><i style="width:${p}%"></i></div><small>${p}%</small></div>
      <div class="row wrap">${!t.known?qb(x,'💬 Hỏi nhu cầu','ask',{task:t.id},'primary'):''}${x.button('Trò chuyện','chat',{npc:t.npc,task:t.id},'ghost small')}</div>
    </div></section>`;
}
function steps(t,x,tab){
  if(t.gift?.kind==='return')return '';
  const list=[['shelf','Kệ hàng'],...(t.needs?.gift?[['pack','Gói quà']]:[]),['checkout','Thu ngân']];
  return `<nav class="mb-steps" aria-label="Bước phục vụ">${list.map(([id,l],i)=>`<button type="button" class="${tab===id?'on':''}" data-action="car:tab" data-tab="${id}" aria-pressed="${tab===id}"><span>${i+1}</span>${l}</button>`).join('')}</nav>`;
}
function kitDesk(t,x){
  const k=t.gift?.kit||{asked:[],answers:[]};
  return `<section class="mb-desk"><h4>🍼 Hỏi han bố mẹ lần đầu</h4><p class="muted small">Hỏi đúng điều cần biết rồi mới chọn đồ. Bộ đồ gọn thôi: tối đa 4 loại, 6 món.</p>
    <div class="mb-qa">${TOPICS.map(([id,q])=>{const a=k.answers.find(v=>v.topic===id);return a?`<div class="mb-answer"><b>${x.esc(q)}</b><p>“${x.esc(a.text)}”</p></div>`:qb(x,x.esc(q),'gift_ask',{task:t.id,topic:id},'cream');}).join('')}</div></section>`;
}
function safetyNote(t,x){
  const v=t.gift||{},n=t.needs||{},want=product(x,n.product),lb=label(x,n.product);
  if(v.swap)return `<p class="mb-note good">🛡️ Khách đã đồng ý đổi sang <b>${x.esc(product(x,v.swap).name)}</b>. Lấy đúng món này nhé.</p>`;
  return `<p class="mb-note">🔎 Khách hỏi <b>${x.esc(want.name)}</b>${lb?` — hộp ghi “${x.esc(lb.label)}”`:''}. Đọc nhãn tuổi rồi quyết định: bán đúng món, hoặc chọn “Gợi ý thay” trên một món hợp hơn.</p>`;
}
function bulkList(t,x){
  const items=t.gift?.items||{};
  return `<section class="mb-desk"><h4>🎉 Danh sách đặt tiệc</h4><ul class="mb-check">${Object.entries(items).map(([k,q])=>{const have=t.basket?.[k]||0;return `<li class="${have===q?'ok':have>q?'bad':''}"><span aria-hidden="true">${have===q?'✓':have>q?'✗':'○'}</span>${x.esc(product(x,k).name)} <b>${have}/${q}</b></li>`;}).join('')}</ul></section>`;
}
function shelf(t,x){
  const v=t.gift||{},filter=x.ui.filter||'all',uses=G(x).uses||{};
  const safety=v.kind==='safety'&&!v.swap&&t.known;
  const list=(x.content.products||[]).filter(p=>filter==='all'||label(x,p.id)?.use===filter);
  const chips=`<div class="mb-filters" role="group" aria-label="Lọc kệ">${[['all','Tất cả'],...Object.entries(uses)].map(([id,l])=>`<button type="button" class="mb-filter ${filter===id?'on':''}" data-action="car:filter" data-use="${id}" aria-pressed="${filter===id}">${USE_EMOJI[id]||'🛒'} ${x.esc(l)}</button>`).join('')}</div>`;
  const cards=list.map(p=>{
    const lb=label(x,p.id),stock=x.room.available?.[p.id]??0,inBasket=t.basket?.[p.id]||0,asked=v.kind==='safety'&&t.needs?.product===p.id;
    const canPick=t.known&&x.room.open&&stock>0&&v.kind!=='return';
    return `<article class="mb-card ${inBasket?'on':''} ${asked?'asked':''}"><div class="mb-art">${art(p,64)}<em class="mb-stock ${stock<=0?'zero':''}" aria-label="Còn ${stock}">${stock}</em>${inBasket?`<em class="mb-inbasket">×${inBasket}</em>`:''}</div>
      <h5>${x.esc(p.name)}</h5>${lb?`<span class="mb-label ${lb.warn?'warn':''}" title="${x.esc(lb.warn||'')}">🏷️ ${x.esc(lb.label)}</span>`:''}${asked?'<span class="mb-asked">Khách hỏi món này</span>':''}
      <div class="mb-card-foot"><b class="mb-price">${price(x,p.id)} xu</b><div class="mb-card-btns">${inBasket?`<button type="button" class="btn small ghost" ${cmdAttr(x,'basket_remove',{task:t.id,item:p.id})} aria-label="Bớt một ${x.esc(p.name)}">−</button>`:''}<button type="button" class="btn small ${canPick?'primary':''}" ${canPick?cmdAttr(x,'shop_pick',{task:t.id,item:p.id}):'disabled'} aria-label="Thêm ${x.esc(p.name)} vào giỏ">＋ Thêm</button></div></div>
      ${safety&&!asked&&lb?.use!=='card'?`<button type="button" class="btn small cream full" ${cmdAttr(x,'gift_advise',{task:t.id,item:p.id})}>💬 Gợi ý thay</button>`:''}</article>`;
  }).join('');
  return `${chips}<div class="mb-shelf">${cards||'<p class="muted">Không có món nào trong nhóm này.</p>'}</div>`;
}
function packDesk(t,x){
  const d=draft(t,x),papers=x.content.papers||[],ribbons=x.content.ribbons||[],paper=papers.find(p=>p.id===d.paper)||papers[0]||{},ribbon=ribbons.find(r=>r.id===d.ribbon)||ribbons[0]||{};
  const tags=t.gift?G(x).tags||[]:[];
  return `<section class="mb-pack"><div class="mb-gift" style="--paper:${x.esc(paper.color||'#ecd9af')};--ribbon:${x.esc(ribbon.color||'#c19444')}" role="img" aria-label="Hộp quà giấy ${x.esc(paper.name||'')}"><i class="mb-bow"></i>${d.tag?`<span class="mb-card-tag">💌 ${x.esc((tags.find(v=>v.id===d.tag)||{}).text||'')}</span>`:''}</div>
    <div class="mb-pack-form"><h4>Giấy gói</h4><div class="mb-swatches">${papers.map(p=>`<button type="button" class="mb-swatch ${p.id===d.paper?'on':''}" data-action="car:paper" data-value="${p.id}" aria-pressed="${p.id===d.paper}"><i style="background:${x.esc(p.color)}"></i>${x.esc(p.name)}</button>`).join('')}</div>
    <h4>Nơ</h4><div class="mb-swatches">${ribbons.map(r=>`<button type="button" class="mb-swatch ${r.id===d.ribbon?'on':''}" data-action="car:ribbon" data-value="${r.id}" aria-pressed="${r.id===d.ribbon}"><i style="background:${x.esc(r.color)}"></i>${x.esc(r.name)}</button>`).join('')}</div>
    ${tags.length?`<h4>Thiệp đúng dịp</h4><div class="mb-swatches tags">${tags.map(v=>`<button type="button" class="mb-swatch ${v.id===d.tag?'on':''}" data-action="car:tag" data-value="${v.id}" aria-pressed="${v.id===d.tag}">💌 ${x.esc(v.text)}</button>`).join('')}</div>`:''}
    <label class="field">Lời chúc riêng<input class="input" id="mb-card" maxlength="100" data-car="card" data-preserve value="${x.esc(d.card)}"></label>
    ${x.button('🎀 Gói món quà này','car:pack',{task:t.id},'primary')}${t.pack?`<p class="mb-note good">Đã gói giấy ${x.esc((papers.find(p=>p.id===t.pack.paper)||{}).name||'')}${t.pack.tag?` · thiệp “${x.esc((tags.find(v=>v.id===t.pack.tag)||{}).text||'')}”`:''}. Đổi lại trước khi giao vẫn miễn phí.</p>`:''}
    <p class="small muted">Vật liệu gói: 5 xu khi giao.</p></div></section>`;
}
function checkout(t,x){
  const sum=total(x,t.basket),b=t.needs?.budget,over=b!=null&&sum>b;
  const rows=Object.entries(t.basket||{}).map(([k,q])=>`<div class="kv-row"><span>${q} × ${x.esc(product(x,k).name)}</span><b>${price(x,k)*q} xu</b></div>`).join('');
  return `<section class="mb-till"><h4>🧾 Kiểm lại trước khi trao</h4><div class="kv">${rows||'<p class="muted">Giỏ còn trống.</p>'}<div class="kv-row total"><span>Tổng tiền hàng</span><b class="${over?'bad':''}">${sum} xu${b!=null?` / ${b} xu`:''}</b></div>${t.gift?.discount?`<div class="kv-row"><span>Bớt cho khách</span><b>−${t.gift.discount} xu</b></div>`:''}<div class="kv-row"><span>Gói quà</span><b>${t.pack?'Đã gói · 5 xu':t.needs?.gift?'Chưa gói':'Không cần'}</b></div></div>
    ${t.checked?'<p class="mb-note good">✓ Đã soát lại giỏ và gói quà. Đọc lại lời khách dặn lần cuối rồi trao nhé.</p>':''}
    <div class="row wrap">${qb(x,'✓ Kiểm đơn','shop_check',{task:t.id},'ghost',!count(t.basket))}<button type="button" class="btn primary" data-action="car:deliver" data-task="${x.esc(t.id)}" data-sum="${sum}" data-pack="${t.pack?1:0}"${t.checked?'':' disabled'}>🛍️ Thanh toán & giao · ${sum} xu</button></div></section>`;
}
function returnDesk(t,x){
  const r=t.gift?.ret;if(!r)return '';
  const seen=new Set(r.seen||[]),p=product(x,r.item);
  const book=r.book?`<div class="mb-book" role="table" aria-label="Sổ bán hàng"><div role="row" class="head"><span>Ngày</span><span>Món</span><span>Giá</span><span>Trả bằng</span></div>${r.book.map(l=>`<div role="row"><span>${x.esc(l.date)}</span><span>${x.esc(product(x,l.item).name)}</span><span>${l.price} xu</span><span>${x.esc(l.pay)}</span></div>`).join('')||'<div role="row"><span>Không có dòng nào</span></div>'}</div>`:'';
  const ready=seen.has('tag')&&seen.has('item');
  return `<section class="mb-desk mb-return"><div class="mb-return-item">${art(p,72)}<div><h4>${x.esc(p.name)}</h4><p class="small">Khách nói mua ngày <b>${x.esc(r.said_date)}</b> · giá ${p.price} xu</p></div></div>
    <div class="mb-inspect">${seen.has('book')?'':qb(x,'📖 Tra sổ bán hàng','gift_book',{task:t.id},'cream')}${seen.has('tag')?'':qb(x,'🏷️ Xem tem','gift_inspect',{task:t.id,part:'tag'},'cream')}${seen.has('item')?'':qb(x,'🔍 Xem kỹ món hàng','gift_inspect',{task:t.id,part:'item'},'cream')}</div>
    ${r.tag?`<p class="mb-finding">🏷️ ${x.esc(r.tag)}</p>`:''}${r.look?`<p class="mb-finding">🔍 ${x.esc(r.look)}</p>`:''}${book}
    <h4>Cách xử lý</h4>${ready?'':'<p class="mb-note">Xem tem và món hàng trước khi quyết định cho công bằng với cả hai bên.</p>'}
    <div class="mb-resolve">${RESOLVE.map(([id,l,sub])=>`<button type="button" class="btn ${ready?'cream':'ghost'}" data-action="v4Cmd" data-op="gift_resolve" data-payload="${pay(x,{task:t.id,choice:id})}" data-confirm="${x.esc(`${l.replace(/^\S+\s/,'')}: chốt cách này với khách?`)}"><span>${l}</span><small>${sub}</small></button>`).join('')}</div>
    ${r.verdict?`<p class="mb-note">${x.esc(r.verdict)}</p>`:''}</section>`;
}
/* ---------------------------------------------------------------- pinned request: what the customer asked, always in view */
function requestStrip(t,x){
  if(!t.known||!t.needs)return '';
  const v=t.gift||{},n=t.needs,g=G(x),bits=[];
  if(v.kind==='return'){const r=v.ret||{};bits.push(`↩️ Đổi trả ${product(x,r.item).name}`,`mua ngày ${r.said_date||'?'}`);}
  else if(v.kind==='kit'){const k=v.kit||{},left=3-(k.asked||[]).length;bits.push(`🍼 Bộ đồ gọn cho bố mẹ lần đầu${v.age!=null?` · bé ${v.age?`${v.age} tháng`:'vài tuần'}`:''}`);if(left>0)bits.push(`còn ${left} câu nên hỏi`);}
  else if(v.kind==='bulk'){bits.push('🎉 '+Object.entries(v.items||{}).map(([k,q])=>`${q} ${product(x,k).name}`).join(' · '));}
  else if(v.kind==='occasion'&&v.pick==='open')bits.push(`🎁 1 món hợp dịp${v.age!=null?` · bé ${v.age>=12?`${Math.floor(v.age/12)} tuổi`:`${v.age} tháng`}`:''}`);
  else{const id=v.swap||n.product;if(id)bits.push(`🎯 ${n.qty} × ${product(x,id).name}`);if(v.kind==='safety'&&v.age!=null)bits.push(`bé ${v.age} tháng`);}
  if(v.kind!=='return'){
    if(n.budget!=null)bits.push(`≤ ${n.budget} xu`);
    if(n.gift)bits.push(`gói ${(g.papers||{})[n.paper]||n.paper}${v.kind==='occasion'||v.kind==='bulk'?' + thiệp đúng dịp':''}`);
  }
  const sum=total(x,t.basket),over=n.budget!=null&&sum>n.budget,cnt=count(t.basket);
  const tray=v.kind==='return'?'':`<b class="mb-strip-tray ${over?'bad':''}" aria-label="Giỏ ${cnt} món, ${sum} xu">🧺 ${cnt?`${cnt} món · ${sum} xu`:'trống'}</b>`;
  return `<div class="mb-strip" role="note" aria-label="Khách dặn"><span class="mb-strip-text">${x.esc(bits.join(' · '))}</span>${tray}</div>`;
}

/* ---------------------------------------------------------------- care corner: families, pickups, shelf, registry */
const C=x=>G(x).care||{};
const hearts=n=>'♥'.repeat(n)+'♡'.repeat(Math.max(0,5-n));
const kg=v=>v==null?'':`${Math.floor(v/10)},${v%10} kg`;
const pickOf=(x,fid)=>((x.ui.pick??={})[fid]??={});
function carePriceOf(x,f,pk){const c=C(x),pr=c.prices||{};return (pr.diaper||0)+(f.milk&&pk.lot&&pk.lot!=='none'?pr.formula||0:0);}
function pickupCard(x,f){
  const c=C(x),pk=pickOf(x,f.id),busy=!x.room.open;
  const last=f.visits?`Lần trước (ngày ${f.last}): size <b>${x.esc(f.last_size||'?')}</b>${f.last_kg?` · ${kg(f.last_kg)}`:''}${f.last_prod_name?` · ${x.esc(f.last_prod_name)}`:''}`:'Lần đầu lấy gói ở tiệm.';
  const news=f.news?`<p class="mb-care-say">“${x.esc(f.news)}”</p>`:f.can_ask?`<div class="row wrap">${qb(x,'⚖️ Hỏi thăm & cân bé','gift_care_ask',{family:f.id},'cream',busy)}<small class="muted">Chưa biết hôm nay bé nặng bao nhiêu.</small></div>`:'';
  const sizes=(c.sizes||[]).map(sz=>{const n=(c.diapers||{})[sz.id]??0,on=pk.size===sz.id;return `<button type="button" class="mb-opt ${on?'on':''}" data-action="car:pick" data-fam="${f.id}" data-k="size" data-v="${sz.id}" aria-pressed="${on}"${n<1?' disabled':''}><b>${x.esc(sz.id)}</b><small>${x.esc(sz.range)}</small><em>${n<1?'hết':`còn ${n}`}</em></button>`;}).join('');
  let milk='';
  if(f.milk){
    const lots=(c.lots||[]).map(l=>{const on=pk.lot===l.id,bad=l.expired||l.recalled;return `<button type="button" class="mb-opt lot ${on?'on':''} ${bad?'bad':''}" data-action="car:pick" data-fam="${f.id}" data-k="lot" data-v="${x.esc(l.id)}" aria-pressed="${on}"><b>${x.esc(l.name)}</b><small>${x.esc(l.id)} · HSD ${x.esc(l.date)} · ${l.qty} hộp</small>${l.recalled?'<em class="bad">⚠️ Bị thu hồi</em>':l.expired?'<em class="bad">⛔ Quá hạn</em>':l.left<=1?'<em>Sắp hết hạn</em>':''}</button>`;}).join('');
    const none=pk.lot==='none';
    milk=`<h5>🥫 Hộp sữa · bé dùng ${x.esc(f.feeding.replace(/^Sữa /,''))} <small class="muted">(số 1: ${x.esc((c.formulas||[])[0]?.range||'')}, số 2: từ ${c.stage_weeks||26} tuần)</small></h5><div class="mb-opts">${lots}<button type="button" class="mb-opt ${none?'on':''}" data-action="car:pick" data-fam="${f.id}" data-k="lot" data-v="none" aria-pressed="${none}"><b>🚫 Không có hộp hợp</b><small>Chỉ trao bỉm, hẹn sữa lần sau</small></button></div>`;
  }
  const q=f.question?`<div class="mb-care-q"><p class="mb-care-say">${x.esc(f.parent)} hỏi: “${x.esc(f.question.text)}”</p><div class="mb-opts one">${f.question.options.map(o=>{const on=pk.advice===o.id;return `<button type="button" class="mb-opt ${on?'on':''}" data-action="car:pick" data-fam="${f.id}" data-k="advice" data-v="${o.id}" aria-pressed="${on}"><span>💬 ${x.esc(o.label)}</span></button>`;}).join('')}</div></div>`:'';
  const ready=pk.size&&(!f.milk||pk.lot)&&(!f.question||pk.advice);
  const rows=[{ok:pk.size?true:null,icon:'🧷',label:'Chọn size bỉm theo cân nặng hôm nay',value:pk.size||''}];
  if(f.milk)rows.push({ok:pk.lot?true:null,icon:'🥫',label:'Chọn hộp sữa đúng loại, còn hạn',value:pk.lot&&pk.lot!=='none'?pk.lot:pk.lot?'không có':''});
  if(f.question)rows.push({ok:pk.advice?true:null,icon:'💬',label:'Trả lời câu khách hỏi'});
  return `<article class="mb-pick ${f.late?'late':''}"><header><span class="mb-face" style="--s:40px" aria-hidden="true">${x.esc(f.emoji)}</span><div class="grow"><b>${x.esc(f.parent)} · bé ${x.esc(f.baby)}</b><small>${f.weeks} tuần · ${x.esc(f.feeding)} · <span class="mb-hearts" aria-label="${x.esc(f.trust_name)}">${hearts(f.trust)}</span> ${x.esc(f.trust_name)}</small></div>${f.late?'<span class="tag amber">Hạn cuối hôm nay</span>':''}</header>
    <p class="small mb-care-last">${last}</p>${news}
    <h5>🧷 Size bỉm</h5><div class="mb-opts sizes">${sizes}</div>${milk}${q}
    ${reqList(rows,x.esc,'Gói định kỳ của '+f.parent)}
    <button type="button" class="btn primary full" data-action="car:hand" data-fam="${f.id}"${ready&&!busy?'':' disabled'}>🤲 Trao gói · ${carePriceOf(x,f,pk)} xu</button></article>`;
}
function registryCard(x){
  const c=C(x),reg=c.reg;if(!reg||reg.state!=='open')return '';
  const busy=!x.room.open,names=c.item_names||{};
  const rows=reg.lines.map(l=>{
    const mark=l.aside?'✓':l.bought?'!':'○',state=l.aside?'Đã để riêng vào hộp':l.bought?'Bạn bè đã mua · cần để riêng':`Chưa ai mua`;
    const btns=[!l.aside&&l.bought?qb(x,`📦 Để riêng <small>(kệ ${l.stock})</small>`,'gift_care_aside',{line:l.id},l.stock>=l.qty?'primary small':'ghost small',busy||l.stock<l.qty):'',
      !l.aside&&!l.swapped?`<button type="button" class="btn ghost small" data-action="car:swapOpen" data-line="${l.id}" aria-expanded="${x.ui.swapLine===l.id}">💬 Gợi ý đổi</button>`:''].join('');
    const picker=x.ui.swapLine===l.id&&!l.aside&&!l.swapped?`<div class="mb-opts one">${(reg.swaps[l.orig]||[]).map(k=>qb(x,`→ ${x.esc(names[k]||k)}`,'gift_care_swap',{line:l.id,item:k},'cream small',busy)).join('')}<small class="muted">Chỉ đổi khi nhãn hộp chưa hợp bé sơ sinh. Chị Ly đồng ý thì bạn bè mua món mới.</small></div>`:'';
    return `<li class="mb-reg-line ${l.aside?'ok':l.bought?'todo':''}"><span class="mb-reg-mark" aria-hidden="true">${mark}</span><div class="grow"><b>${l.qty} × ${x.esc(l.name)}</b><span class="mb-label ${l.warn?'warn':''}">🏷️ ${x.esc(l.label)}</span><small class="mb-reg-state">${x.esc(state)}${l.bought||l.aside?'':` · dự kiến ngày ${l.bought_day}`}${l.swapped?` · đã đổi từ ${x.esc(l.orig_name)}`:''}</small>${btns?`<div class="row wrap">${btns}</div>`:''}${picker}</div></li>`;
  }).join('');
  const boxed=reg.lines.filter(l=>l.aside).length,missing=reg.lines.filter(l=>l.bought&&!l.aside).length;
  const canGo=c.day>=reg.shower-1&&boxed>0;
  return `<article class="mb-reg"><header><b>🎀 Quà mừng bé ${x.esc(c.fam?.find(f=>f.id===reg.family)?.baby||'')} · ${x.esc(c.fam?.find(f=>f.id===reg.family)?.parent||'')}</b><small>Tiệc ngày ${x.esc(reg.shower_date)} · giao hộp từ ngày ${reg.shower-1}</small></header>
    <p class="small muted">Bạn bè đặt từng món trong danh sách. Món đã có người mua thì lấy trên kệ để riêng; đọc nhãn tuổi, món nào chưa hợp bé sơ sinh thì gợi ý đổi.</p>
    <ul class="mb-reg-list">${rows}</ul>
    <button type="button" class="btn ${canGo?'primary':'ghost'} full" data-action="car:shower" data-missing="${missing}"${canGo&&!busy?'':' disabled'}>🎁 Giao hộp quà mừng${missing?` · còn ${missing} món chưa để riêng`:''}</button></article>`;
}
function shelfFold(x){
  const c=C(x),busy=!x.room.open,pr=c.prices||{},qty=id=>(x.ui.oq??={})[id]??2;
  const coming=id=>(c.orders||[]).filter(o=>o.item===id).reduce((a,o)=>a+o.qty,0);
  const stepper=(id,cost)=>`<span class="mb-step"><button type="button" class="btn ghost small" data-action="car:oq" data-item="${id}" data-d="-1" aria-label="Bớt">−</button><b>${qty(id)}</b><button type="button" class="btn ghost small" data-action="car:oq" data-item="${id}" data-d="1" aria-label="Thêm">＋</button><button type="button" class="btn small" data-action="car:order" data-item="${id}" data-cost="${cost}"${busy?' disabled':''}>Đặt · ${cost*qty(id)} xu</button></span>`;
  const drows=(c.sizes||[]).map(sz=>{const n=(c.diapers||{})[sz.id]??0,on=coming(sz.id);return `<li class="mb-shelf-row ${n?'':'out'}"><div class="grow"><b>Bỉm ${x.esc(sz.id)} <small>· ${x.esc(sz.range)}</small></b><small>Còn <b>${n}</b> gói${on?` · +${on} về sáng mai`:''}</small></div>${stepper(sz.id,pr.diaper_cost||0)}</li>`;}).join('');
  const lots=(c.lots||[]).map(l=>{const bad=l.expired||l.recalled;return `<li class="mb-shelf-row ${bad?'bad':''}"><div class="grow"><b>${x.esc(l.name)}</b> <small>${x.esc(l.id)} · ${l.qty} hộp · HSD ${x.esc(l.date)}</small>${l.recalled?'<small class="bad">⚠️ Lô bị thu hồi: rút ra, hãng hoàn tiền</small>':l.expired?'<small class="bad">⛔ Quá hạn: rút khỏi kệ</small>':l.left<=2?`<small>Còn ${l.left} ngày: bán lô này trước</small>`:''}</div>${bad?qb(x,'🧹 Rút khỏi kệ','gift_care_pull',{lot:l.id},'danger small',busy):''}</li>`;}).join('')||'<li class="muted small">Kệ sữa trống.</li>';
  const frows=(c.formulas||[]).map(fm=>{const n=(c.lots||[]).filter(l=>l.p===fm.id).reduce((a,l)=>a+l.qty,0),on=coming(fm.id);return `<li class="mb-shelf-row"><div class="grow"><b>${x.esc(fm.name)} <small>· ${x.esc(fm.range)}</small></b><small>Còn <b>${n}</b> hộp${on?` · +${on} về sáng mai`:''}</small></div>${stepper(fm.id,pr.formula_cost||0)}</li>`;}).join('');
  const notices=(c.notices||[]).map(n=>`<p class="mb-note">📣 Ngày ${x.esc(n.date)}: hãng thu hồi lô <b>${x.esc(n.lot)}</b> (${x.esc(n.name)}) vì lỗi hàn nắp.</p>`).join('');
  const nPacks=Object.values(c.diapers||{}).reduce((a,v)=>a+v,0),nCans=(c.lots||[]).reduce((a,l)=>a+l.qty,0);
  const body=`${notices}<h5>🥫 Lô sữa trên kệ</h5><ul class="mb-shelf-list">${lots}</ul><h5>🧷 Bỉm theo size</h5><ul class="mb-shelf-list">${drows}</ul><h5>🛒 Đặt thêm sữa</h5><ul class="mb-shelf-list">${frows}</ul><p class="small muted">Hàng đặt hôm nay về sáng mai. Bán: bỉm ${pr.diaper} xu/gói, sữa ${pr.formula} xu/hộp.</p>`;
  const tag=c.alerts?` <span class="tag danger">${c.alerts} lô cần rút</span>`:'';
  return fold(`🧺 Kệ bỉm sữa · ${nPacks} gói · ${nCans} hộp${tag}`,body,!!c.alerts);
}
function bookFold(x){
  const c=C(x);
  const rows=(c.fam||[]).map(f=>{
    const when=f.status==='expecting'?`dự sinh ngày ${x.esc(f.born_date)}`:f.status==='soon'?`lần đầu ghé ngày ${f.first}`:f.due?'<b>hẹn lấy gói hôm nay</b>':`lấy gói ngày ${f.next}`;
    const sz=f.last_size?` · size ${x.esc(f.last_size)}`:'',w=f.last_kg?` · ${kg(f.last_kg)}`:'';
    return `<li><span class="mb-face" style="--s:34px" aria-hidden="true">${x.esc(f.emoji)}</span><div class="grow"><b>${x.esc(f.parent)} · bé ${x.esc(f.baby)}</b><small>${f.weeks!=null?`${f.weeks} tuần · `:''}${x.esc(f.feeding)}${sz}${w}</small><small>${when}${f.missed?` · lỡ hẹn ${f.missed} lần`:''}</small></div><span class="mb-hearts" title="${x.esc(f.trust_name)}" aria-label="${x.esc(f.trust_name)}">${hearts(f.trust)}</span></li>`;
  }).join('');
  const log=(c.log||[]).length?`<h5>📓 Gần đây</h5><ul class="mb-care-log">${c.log.slice().reverse().map(l=>`<li><small>Ngày ${l.day}</small> ${x.esc(l.text)}</li>`).join('')}</ul>`:'';
  return fold(`📒 Sổ bé quen · ${(c.fam||[]).length} gia đình`,`<ul class="mb-book-list">${rows}</ul><p class="small muted">${x.esc(c.rule||'')} Từ “${x.esc((c.trust_names||[])[c.tells_weight||2]||'')}”, bố mẹ tự kể cân nặng; từ “${x.esc((c.trust_names||[])[c.tips_from||3]||'')}”, họ gửi chút bồi dưỡng khi gói đúng.</p>${log}`);
}
function careCount(x){const c=C(x);return (c.due||0)+(c.alerts||0)+(c.reg?.state==='open'&&c.reg.lines.some(l=>l.bought&&!l.aside)?1:0);}
function careCorner(x,always){
  const c=C(x);if(!c.ready)return '';
  const open=always||x.ui.careOpen===true,n=careCount(x);
  const due=(c.fam||[]).filter(f=>f.due);
  const inner=`<span class="mb-care-title">🍼 Góc bỉm sữa & khách quen</span>${c.due?`<span class="tag amber">📦 ${c.due} hẹn lấy gói</span>`:''}${c.alerts?`<span class="tag danger">⚠️ ${c.alerts} lô cần rút</span>`:''}${!c.due&&!c.alerts?`<small>${n?'Có việc cần làm':'Không có hẹn hôm nay'}</small>`:''}`;
  const head=always?`<h4 class="mb-care-head static">${inner}</h4>`:`<button type="button" class="mb-care-head" data-action="car:careToggle" aria-expanded="${open}">${inner}<i aria-hidden="true">${open?'▴':'▾'}</i></button>`;
  if(!open)return `<section class="mb-care">${head}</section>`;
  return `<section class="mb-care">${head}<div class="mb-care-body">${due.map(f=>pickupCard(x,f)).join('')}${registryCard(x)}${shelfFold(x)}${bookFold(x)}</div></section>`;
}

function nextStep(t,x){
  if(!t)return 'Chờ khách ghé tiệm';
  const ev=G(x).event;if(ev?.stage==='open')return 'Xử lý chuyện đang xảy ra ở tiệm';
  if(!t.known)return 'Hỏi nhu cầu khách';
  const v=t.gift||{};
  if(v.kind==='return'){const s=v.ret?.seen||[];if(!s.includes('book'))return 'Tra sổ bán hàng';if(!s.includes('tag'))return 'Xem tem trên món hàng';if(!s.includes('item'))return 'Xem kỹ món hàng';return 'Chọn cách đổi trả công bằng';}
  if(v.kind==='kit'&&(v.kit?.asked||[]).length<3)return 'Hỏi thêm: tuổi bé, điều đang lo, ngân sách';
  if(v.kind==='safety'&&!v.swap&&!count(t.basket))return 'Đọc nhãn tuổi trên hộp trước khi lấy';
  if(!count(t.basket))return 'Lấy hàng trên kệ';
  if(t.needs?.gift&&!t.pack)return 'Tới bàn gói quà';
  if(!t.checked)return 'Kiểm đơn trước khi giao';
  return 'Thanh toán & trao quà';
}

export default {
  id:'mother_baby',
  css:true,
  next:(t,x)=>nextStep(t,x),
  job(t,x){
    if(x.ui.tabFor!==t.id){x.ui.tabFor=t.id;x.ui.tab=stage(t);x.ui.filter='all';x.ui.flash='';}
    let tab=x.ui.tab;if(tab==='pack'&&!t.needs?.gift)tab='checkout';
    const v=t.gift||{};
    let main='';
    if(!t.known)main='';
    else if(v.kind==='return')main=returnDesk(t,x);
    else{
      const top=v.kind==='kit'?kitDesk(t,x):v.kind==='bulk'?bulkList(t,x):v.kind==='safety'?safetyNote(t,x):'';
      const panel=tab==='pack'?packDesk(t,x):tab==='checkout'?checkout(t,x):shelf(t,x);
      const basket=count(t.basket)?`<p class="mb-basket">🧺 Giỏ: ${Object.entries(t.basket).map(([k,q])=>`${q} × ${x.esc(product(x,k).name)}`).join(', ')} · <b>${total(x,t.basket)} xu</b></p>`:'';
      main=`${top}${steps(t,x,tab)}${basket}${panel}`;
    }
    const legacyEvent=x.room.event&&x.room.event.stage!=='resolved'?`<p class="mb-note">📣 Có chuyện ở tiệm đang chờ bạn. ${x.button('Xem ngay','event',{},'small')}</p>`:'';
    return `<div class="career-job mb">${requestStrip(t,x)}${hud(x)}<p class="mb-hint" aria-live="polite">💡 ${x.esc(nextStep(t,x))}</p>${x.ui.flash?`<p class="mb-flash" role="status">${x.esc(x.ui.flash)}</p>`:''}${eventCard(x)}${legacyEvent}${customer(t,x)}${main}${careCorner(x,false)}
      <div class="mb-tools">${x.button('🧺 Kho & nhập hàng','warehouse',{},'ghost small')}${x.button('⭐ Đánh giá','feedback',{},'ghost small')}</div></div>`;
  },
  idle(x){return `<div class="career-job mb">${hud(x)}${eventCard(x)}${careCorner(x,true)}</div>`;},
  actions:{
    async tab(data,el,x){x.ui.tab=data.tab;x.render();},
    async filter(data,el,x){x.ui.filter=data.use;x.render();},
    async paper(data,el,x){const t=x.room.tasks.find(v=>v.id===x.room.active_task);if(t){draft(t,x).paper=data.value;x.render();}},
    async ribbon(data,el,x){const t=x.room.tasks.find(v=>v.id===x.room.active_task);if(t){draft(t,x).ribbon=data.value;x.render();}},
    async tag(data,el,x){const t=x.room.tasks.find(v=>v.id===x.room.active_task);if(t){draft(t,x).tag=data.value;x.render();}},
    async card(data,el,x){const t=x.room.tasks.find(v=>v.id===x.room.active_task);if(t)draft(t,x).card=String(data.value||'').slice(0,100);},
    async pack(data,el,x){
      const t=x.room.tasks.find(v=>v.id===data.task);if(!t)return;
      const d=draft(t,x),input=el.closest('.career-job')?.querySelector('#mb-card');if(input)d.card=input.value.slice(0,100);
      const payload={task:t.id,paper:d.paper,ribbon:d.ribbon,card:d.card||'Gửi bé một ngày thật dịu dàng.'};
      if(t.gift&&d.tag)payload.tag=d.tag;
      const r=await run(x,'shop_pack',payload);
      if(r){x.ui.tab='checkout';x.render();}
    },
    async deliver(data,el,x){
      // The customer looks at the gift at the counter: a mistake shows as their reaction.
      if(!await x.ask('Trao món quà cho khách?',`Thu ${data.sum} xu tiền hàng${data.pack==='1'?', trừ 5 xu vật liệu gói':''} và trao quà cho khách?`,'Thanh toán & giao'))return;
      const r=await run(x,'shop_deliver',{task:data.task});if(!r)return;
      const done=(x.api.state?.careers?.mother_baby?.tasks||[]).find(v=>v.id===data.task),re=done?.reaction;
      if(re&&re.line){
        const who=done.gift?.guest?.name||'Khách',msg=`${who}: “${re.line}”${re.cut?` (−${re.cut} xu)`:''}`;
        x.ui.flash=msg;x.toast(msg,['discount','refund','walkout','refuse'].includes(re.kind)?'error':false);x.render();
      }
    },
    async careToggle(data,el,x){x.ui.careOpen=!x.ui.careOpen;x.render();},
    async pick(data,el,x){const pk=pickOf(x,data.fam);pk[data.k]=pk[data.k]===data.v?undefined:data.v;x.ui.careOpen=true;x.render();},
    async swapOpen(data,el,x){x.ui.swapLine=x.ui.swapLine===data.line?null:data.line;x.ui.careOpen=true;x.render();},
    async oq(data,el,x){const q=(x.ui.oq??={});q[data.item]=Math.max(1,Math.min(4,(q[data.item]??2)+Number(data.d||0)));x.ui.careOpen=true;x.render();},
    async order(data,el,x){
      const q=(x.ui.oq??={})[data.item]??2,cost=Number(data.cost||0)*q,c=C(x);
      const name=(c.sizes||[]).some(s=>s.id===data.item)?`bỉm ${data.item}`:`hộp ${(c.formulas||[]).find(f=>f.id===data.item)?.name||data.item}`;
      if(!await x.ask('Đặt thêm hàng?',`Đặt ${q} × ${name}, trả ${cost} xu ngay. Hàng về kệ sáng mai.`,'Đặt hàng'))return;
      await run(x,'gift_care_order',{item:data.item,qty:q,confirm:true});
    },
    async hand(data,el,x){
      const f=(C(x).fam||[]).find(v=>v.id===data.fam);if(!f)return;
      const pk=pickOf(x,f.id),lot=f.milk&&pk.lot&&pk.lot!=='none'?pk.lot:null;
      const what=`bỉm ${pk.size}${lot?` + hộp sữa ${lot}`:''}`;
      if(!await x.ask(`Trao gói cho ${f.parent}?`,`Trao ${what}, thu ${carePriceOf(x,f,pk)} xu.`,'Trao gói'))return;
      const r=await run(x,'gift_care_hand',{family:f.id,size:pk.size,lot,advice:f.question?pk.advice:null,confirm:true});
      if(r)delete x.ui.pick[f.id];
    },
    async shower(data,el,x){
      const miss=Number(data.missing||0);
      if(!await x.ask('Giao hộp quà mừng?',miss?`Còn ${miss} món bạn bè đã mua mà chưa để riêng. Giao hộp thiếu món đó?`:'Gói hộp quà (5 xu giấy gói) và giao cho chị Ly trước tiệc?','Giao hộp'))return;
      await run(x,'gift_care_shower',{confirm:true});
    },
    async go(data,el,x){
      let payload={};try{payload=JSON.parse(data.payload||'{}');}catch{return;}
      await run(x,data.op,payload);
    },
  },
  tick(root){
    // The sheet head is sticky; the modal and the pinned request strip sit just under it.
    const d=root.closest('dialog'),h=`${d?.querySelector('.sheet-head')?.offsetHeight||0}px`;
    if(d&&d.style.getPropertyValue('--job-head')!==h)d.style.setProperty('--job-head',h);
    const modal=root.querySelector('.mb-modal');
    if(modal&&!modal.contains(document.activeElement))modal.querySelector('button:not([disabled])')?.focus({preventScroll:true});
  },
  summary(data,x){
    if(!data||data.sold==null)return '';
    const row=(l,v)=>`<div class="kv-row"><span>${l}</span><b>${v}</b></div>`;
    const care=Array.isArray(data.care?.lines)&&data.care.lines.length?`<h4 class="section-title space-top">🍼 Góc bỉm sữa & khách quen</h4><ul class="mb-care-log">${data.care.lines.map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul>`:'';
    return `<article class="card space-top"><h4 class="section-title">🎁 Tiệm quà hôm nay</h4><div class="kv">${row('Đơn quà đã trao',data.sold)}${data.advised?row('Lần tư vấn an toàn',data.advised):''}${data.returns?row('Ca đổi trả',data.returns):''}${data.events?row('Chuyện bất ngờ',data.events):''}${data.fines?row('Tiền phạt',`${data.fines} xu`):''}</div>${care}</article>`;
  },
};
