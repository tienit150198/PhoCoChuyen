/** Tiệm quà mẹ & bé — shelf with age labels, wrapping desk with occasion cards,
 * safety advice, first-time-parent kits, a returns desk and shop surprises.
 * game/giftshop.py (day 2+) and the engine's shop_* actions are the referee. */
import {itemArt} from '../icons.js';
import {Sound} from '../audio.js';

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
    ${today.sold?`<span class="mb-chip">🎁 ${today.sold} đơn</span>`:''}${today.advised?`<span class="mb-chip good">🛡️ ${today.advised} lần tư vấn</span>`:''}</div>`;
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
    return `<div class="career-job mb">${hud(x)}<p class="mb-hint" aria-live="polite">💡 ${x.esc(nextStep(t,x))}</p>${x.ui.flash?`<p class="mb-flash" role="status">${x.esc(x.ui.flash)}</p>`:''}${eventCard(x)}${legacyEvent}${customer(t,x)}${main}
      <div class="mb-tools">${x.button('🧺 Kho & nhập hàng','warehouse',{},'ghost small')}${x.button('⭐ Đánh giá','feedback',{},'ghost small')}</div></div>`;
  },
  idle(x){return `<div class="career-job mb">${hud(x)}${eventCard(x)}</div>`;},
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
    async go(data,el,x){
      let payload={};try{payload=JSON.parse(data.payload||'{}');}catch{return;}
      await run(x,data.op,payload);
    },
  },
  tick(root){
    const modal=root.querySelector('.mb-modal');
    if(modal){
      const d=root.closest('dialog'),h=`${d?.querySelector('.sheet-head')?.offsetHeight||0}px`;
      if(d&&d.style.getPropertyValue('--job-head')!==h)d.style.setProperty('--job-head',h);
      if(!modal.contains(document.activeElement))modal.querySelector('button:not([disabled])')?.focus({preventScroll:true});
    }
  },
  summary(data,x){
    if(!data||data.sold==null)return '';
    const row=(l,v)=>`<div class="kv-row"><span>${l}</span><b>${v}</b></div>`;
    return `<article class="card space-top"><h4 class="section-title">🎁 Tiệm quà hôm nay</h4><div class="kv">${row('Đơn quà đã trao',data.sold)}${data.advised?row('Lần tư vấn an toàn',data.advised):''}${data.returns?row('Ca đổi trả',data.returns):''}${data.events?row('Chuyện bất ngờ',data.events):''}${data.fines?row('Tiền phạt',`${data.fines} xu`):''}</div></article>`;
  },
};
