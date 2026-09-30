/** Quầy trà sữa — hands-on boba counter. game/boba.py is the referee: every
 * tap is a command, the server keeps stock, patience, sealing time and grades.
 * Care loop: tea brewed in pots and pearls cooked in batches go stale by the
 * shop clock, supplier orders arrive at real times of day, the heat sealer needs
 * cleaning, the regulars' card and tomorrow's forecast. A sticky bar on phones
 * keeps the order recap and the serve button in reach. */
import {Sound} from '../audio.js';
import {keepBarAboveFooter} from './food_kit.js';
import {stepRows,nextHint,stepCta,finalGo,pending as nextOf,firstTime,stepLine} from '../v4/guide.js';

const ICE=[['none','Không đá'],['little','Ít đá'],['normal','Đá vừa'],['extra','Nhiều đá']];
const ICE_TEXT={none:'không đá',little:'ít đá',normal:'đá vừa',extra:'nhiều đá'};
const SEAL_TEXT={perfect:'✨ Nắp căng đẹp',ok:'✓ Đã dán nắp',burnt:'🟫 Nắp hơi cháy xém'};
const DONE=['completed','referred','cancelled'];

const pay=(x,o)=>x.esc(JSON.stringify(o));
const B=x=>x.room.data?.boba||{};
const ings=x=>x.content.experiences?.ingredients||[];
const ing=(x,id)=>ings(x).find(i=>i.id===id)||{id,name:id,emoji:'•',color:'#d8c7a8',group:'topping',level:1,cost:0};
const low=s=>s?s[0].toLocaleLowerCase('vi')+s.slice(1):'';
const open=t=>!DONE.includes(t.status);
const station=(x,id)=>(B(x).stations||[]).find(s=>s.id===id)||{id,unlocked:true,stock:0,level:1};
// Counter taps go through actions.go: quiet (feedback shows next to the cup), toasts only for results that matter.
const pick=(x,id)=>`data-action="job" data-task="${x.esc(id)}"`;
const cmdAttr=(x,op,payload)=>`data-action="car:go" data-op="${op}" data-payload="${pay(x,payload)}"`;
const jb=(x,label,op,payload={},style='',disabled=false)=>`<button type="button" class="btn ${style}" ${cmdAttr(x,op,payload)}${disabled?' disabled':''}>${label}</button>`;
const LOUD=new Set(['tea_serve','tea_seal','tea_event','tea_event_ok','tea_discard','tea_check','tea_prepare','tea_cups','tea_wipe','tea_order','tea_clean','tea_toss','tea_swap','tea_greet','more_work','life_mode','life_goal']);
const sfx=new Sound();
const hasGroup=(x,cup,g)=>(cup.items||[]).some(k=>ing(x,k).group===g);
const seal=x=>B(x).seal||{loose:.8,good_lo:1.4,good_hi:2.6,burn:4.2,max:5};

/* ---------------------------------------------------------------- art */
function piece(k,top,i,color){
  const y=146-top*11-(i%2)*4,x0=36+(i*9)%48;
  if(['pearls','white_pearl','popping'].includes(k))return `<circle cx="${x0+4}" cy="${y}" r="${k==='popping'?4:4.4}" fill="${color}" stroke="#00000022"/>`;
  if(k==='red_bean')return `<ellipse cx="${x0+4}" cy="${y}" rx="3.4" ry="2.4" fill="${color}"/>`;
  if(['pudding','flan'].includes(k))return i===0?`<rect x="34" y="${y-6}" width="52" height="10" rx="4" fill="${color}"/>`:'';
  return `<rect x="${x0}" y="${y-4}" width="7" height="7" rx="2" fill="${color}" stroke="#00000018"/>`;
}
export function cupArt(x,cup,small=false){
  const size=small?64:132;
  if(!cup.placed)return `<svg class="mt-cup mt-cup-empty" width="${size}" height="${size*1.2}" viewBox="0 0 120 160" role="img" aria-label="Chưa có ly trên quầy"><path d="M22 34H98L90 150Q90 154 86 154H34Q30 154 30 150Z" fill="none" stroke="currentColor" stroke-width="2.4" stroke-dasharray="6 5" opacity=".45"/><text x="60" y="102" text-anchor="middle" font-size="${small?22:17}" font-weight="800" fill="currentColor" opacity=".7">Lấy ly</text></svg>`;
  const top=cup.size==='L'?18:34,items=cup.items||[];
  const base=items.map(k=>ing(x,k)).find(i=>i.group==='base'),flavor=items.map(k=>ing(x,k)).find(i=>i.group==='flavor');
  const tops=items.map(k=>ing(x,k)).filter(i=>i.group==='topping');
  const caps=tops.filter(i=>['foam','cheese'].includes(i.id)),bits=tops.filter(i=>!['foam','cheese'].includes(i.id));
  const shape=`M22 ${top}H98L90 150Q90 154 86 154H34Q30 154 30 150Z`;
  const liquid=base?`<rect x="20" y="${top+12}" width="84" height="150" fill="${base.color}"/>`:'';
  const tint=flavor?`<rect x="20" y="104" width="84" height="60" fill="${flavor.color}" opacity=".75"/>`:'';
  const cap=caps.map((c,i)=>`<rect x="20" y="${top+8+i*7}" width="84" height="9" fill="${c.color}"/>`).join('');
  const dots=bits.map((b,t)=>Array.from({length:8},(_,i)=>piece(b.id,t,i,b.color)).join('')).join('');
  const ice=Array.from({length:{none:0,little:2,normal:3,extra:5}[cup.ice]||0},(_,i)=>`<rect x="${34+(i*17)%46}" y="${top+22+(i%2)*14}" width="15" height="15" rx="4" fill="#ffffff8c" stroke="#ffffffcc" transform="rotate(${i*13-10} ${41+(i*17)%46} ${top+29})"/>`).join('');
  const film={perfect:'#f39ab8',ok:'#e9c4d0',burnt:'#b98a5e'}[cup.seal_q]||'#e9c4d0';
  const lid=cup.dome?`<path d="M20 ${top}Q60 ${top-30} 100 ${top}Z" fill="#ffffffb0" stroke="#8a6a50" stroke-width="2"/>`:cup.sealed?`<rect x="18" y="${top-4}" width="84" height="7" rx="3" fill="${film}" stroke="#8a6a50" stroke-width="1.6"/>${cup.seal_q==='perfect'?`<path d="M30 ${top-2}H52" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".8"/>`:''}`:`<rect x="18" y="${top-4}" width="84" height="7" rx="3" fill="none" stroke="#8a6a50" stroke-width="1.6" stroke-dasharray="4 3" opacity=".5"/>`;
  const straw=cup.sealed?`<rect x="66" y="${top-34}" width="9" height="46" rx="3" fill="#e8849f" transform="rotate(14 70 ${top})"/>`:'';
  return `<svg class="mt-cup" width="${size}" height="${size*1.2}" viewBox="0 0 120 160" role="img" aria-label="Ly size ${cup.size} đang pha"><defs><clipPath id="mtClip${small?'s':''}"><path d="${shape}"/></clipPath></defs><ellipse cx="60" cy="155" rx="36" ry="4" fill="#00000018"/>${straw}<path d="${shape}" fill="#fffdf8cc"/><g clip-path="url(#mtClip${small?'s':''})">${liquid}${tint}${cap}${dots}${ice}</g><path d="${shape}" fill="none" stroke="#8a6a50" stroke-width="2.4"/>${lid}<text x="60" y="${top+30}" text-anchor="middle" font-size="12" font-weight="800" fill="#5a4436" opacity=".55">${cup.size}</text></svg>`;
}
/** "Hồng trà · chưa có topping": what is in the cup right now, in words. */
function status(x,cup){
  if(!cup.placed)return 'Chưa lấy ly';
  const items=(cup.items||[]).map(k=>ing(x,k));
  const base=items.find(i=>i.group==='base'),flavor=items.find(i=>i.group==='flavor'),tops=items.filter(i=>i.group==='topping');
  const parts=[`Ly ${cup.size}`,base?base.name:'chưa có trà'];
  if(flavor)parts.push('vị '+low(flavor.name));
  parts.push(tops.length?tops.map(i=>low(i.name)).join(', '):'chưa có topping');
  parts.push(cup.ice?ICE_TEXT[cup.ice]:'chưa thêm đá');
  parts.push(cup.sugar!=null?cup.sugar+'% đường':'chưa chọn đường');
  if(cup.sealed)parts.push(cup.dome?'nắp cầu':'đã dán nắp');
  return parts.join(' · ');
}
const face=(t,x,size=58)=>t.walkin?`<span class="mt-face" style="--s:${size}px" aria-hidden="true">${x.esc(t.walkin.emoji||'🙂')}</span>`:`<span class="mt-face portrait" style="--s:${size}px" aria-hidden="true">${x.portrait(x.npc(t.npc),size)}</span>`;
const ring=(p,inner)=>`<span class="mt-ring ${p<40?'low':p<70?'mid':''}" style="--p:${Math.max(0,Math.min(100,p))}">${inner}</span>`;

/* ---------------------------------------------------------------- counter parts */
function hud(x){
  const b=B(x),mod=b.modifier||{},st=b.streak||0;
  return `<div class="mt-hud" role="status">
    <span class="mt-chip${overtime(b)?' hot':''}">🕐 <b>${x.esc(b.clock||'08:00')}</b>${overtime(b)?' · tăng ca':''}</span>
    ${b.left!=null?`<span class="mt-chip">👥 Còn <b>${b.left}</b> khách</span>`:''}
    ${st>=2?`<span class="mt-chip hot">🔥 <b>${st}</b> ly liên tiếp</span>`:''}
    <span class="mt-chip">⭐ Tay nghề <b>${b.level||1}</b>${b.next_tier!=null?` · ${b.total||0}/${b.next_tier} ly`:''}</span>
    ${mod.title?`<span class="mt-chip mod">${x.esc(mod.emoji||'')} ${x.esc(mod.title)}</span>`:''}
  </div>`;
}
function alerts(x){
  const b=B(x),out=[];
  if(b.sealer_off)out.push(`<p class="mt-alert warn">🔌 Cúp điện: máy dán nắp đang ngưng.${b.dome?' Đang dùng nắp cầu (1 xu mỗi ly).':''}</p>`);
  if(b.office)out.push(`<p class="mt-alert info">💼 Đơn văn phòng: ${b.office.done}/${b.office.count} ly · còn ${b.office.deadline_in} nhịp${b.office.bonus?` · thưởng ${b.office.bonus} xu nếu kịp`:''}</p>`);
  if(b.mess)out.push(`<div class="mt-alert warn row-inline"><span>💦 Quầy còn vệt trà đổ.</span>${jb(x,'🧽 Lau quầy','tea_wipe',{},'small')}</div>`);
  if(b.sealer?.state==='dirty')out.push(`<div class="mt-alert warn row-inline"><span>⚙️ Máy dán nắp bám keo (${b.sealer.wear} ly): khó dán đẹp.</span>${jb(x,'🧽 Lau máy · 20 phút','tea_clean',{},'small')}</div>`);
  const w=(b.warnings||[]).filter(v=>v.where==='stock');
  if(w.length)out.push(`<div class="mt-alert warn row-inline"><span>⚠ ${w.map(v=>x.esc(v.text)).join(' · ')}</span>${x.button('🧺 Mở kho','prepare',{},'small')}</div>`);
  return out.join('');
}
const overtime=b=>b.now?.is_open&&(b.now.time||'')>(b.now.close||'20:00');
const pending=(x,id)=>(B(x).orders||[]).filter(o=>o.item===id);
const soonest=(x,id)=>pending(x,id)[0];
/** The order in hand needs something the counter has run out of: offer a swap or an express order. */
function outOfStock(t,x){
  if(!t?.known||t.cup?.sealed)return '';
  const b=B(x),want=t.needs||(t.usual?(b.notebook||[]).find(r=>r.npc===t.npc)?.usual:null);if(!want)return '';
  const items=t.cup?.items||[],rows=[];
  const miss=[...(want.flavor?[want.flavor]:[]),...want.toppings].filter(k=>!items.includes(k)&&!station(x,k).made&&station(x,k).stock===0);
  for(const k of miss){
    const i=ing(x,k),o=soonest(x,k);
    rows.push(`<div class="mt-alert warn mt-out"><span>🚫 Hết <b>${x.esc(low(i.name))}</b>${o?` · 📦 ${x.esc(o.eta_label)}`:''}</span><span class="mt-out-btns">${jb(x,'🙏 Mời khách đổi','tea_swap',{task:t.id,item:k},'small cream')}${o?'':jb(x,`⚡ Gọi hỏa tốc · ${expressCost(x,k,5)} xu`,'tea_order',{item:k,qty:5,supplier:'express',confirm:true},'small ghost')}</span></div>`);
  }
  const cups=b.cups||{},size=want.size;
  if(!t.cup?.placed&&cups[size]===0){
    const o=soonest(x,'cup_'+size),other=size==='M'?'L':'M';
    rows.push(`<div class="mt-alert warn mt-out"><span>🚫 Hết ly <b>${size}</b>${o?` · 📦 ${x.esc(o.eta_label)}`:''}</span><span class="mt-out-btns">${cups[other]?jb(x,size==='M'?'🥤 Mời lên ly L, giữ giá':'🧋 Mời xuống ly M','tea_swap',{task:t.id,item:'cup_'+size},'small cream'):''}${o?'':jb(x,`⚡ Gọi hỏa tốc · ${expressCost(x,'cup_'+size,1)} xu`,'tea_order',{item:'cup_'+size,qty:1,supplier:'express',confirm:true},'small ghost')}</span></div>`);
  }
  return rows.join('');
}
const unitCost=(x,id)=>id.startsWith('cup_')?(B(x).cup_pack?.cost||4):ing(x,id).cost||0;
const orderCost=(x,id,qty,factor)=>Math.max(1,Math.round(qty*unitCost(x,id)*factor));
const expressCost=(x,id,qty)=>orderCost(x,id,qty,B(x).express?.factor||1.35);
function eventCard(x){
  const ev=B(x).event;if(!ev)return '';
  const body=ev.stage==='open'
    ?`<p>${x.esc(ev.text)}</p><div class="mt-choices">${(ev.choices||[]).map(o=>`<button type="button" class="btn ${o.cost?'':'cream'}" ${cmdAttr(x,'tea_event',{choice:o.id})}${o.cost&&x.room.money<o.cost?' disabled':''}><span>${x.esc(o.label)}</span>${o.cost||o.hint?`<small>${o.cost?`${o.cost} xu`:''}${o.cost&&o.hint?' · ':''}${o.hint?x.esc(o.hint):''}</small>`:''}</button>`).join('')}</div>`
    :`<p class="mt-result ${ev.good?'good':'bad'}">${x.esc(ev.result||'')}</p>${(ev.effects||[]).length?`<ul class="mt-effects">${ev.effects.map(e=>`<li>${x.esc(e)}</li>`).join('')}</ul>`:''}${jb(x,ev.good?'Tuyệt, làm tiếp':'Buồn ghê, làm tiếp','tea_event_ok',{},'primary')}`;
  // Shown as a modal over the counter so it is never scrolled out of view; focus is moved in by tick().
  return `<div class="mt-modal"><section class="mt-event ${ev.stage}" role="alertdialog" aria-modal="true" aria-labelledby="mtEvTitle"><h3 id="mtEvTitle"><span aria-hidden="true">${x.esc(ev.emoji||'❗')}</span> ${x.esc(ev.title)}</h3>${body}</section></div>`;
}
function appRow(t,x){
  const b=B(x),apps=x.room.tasks.filter(v=>open(v)&&v.app);
  if(!apps.length)return '';
  const turn=b.turn||0;
  return `<section class="mt-apps" aria-label="Đơn app"><h4>📱 Đơn app <small>app giữ ${b.app_fee||20}% mỗi đơn</small></h4><div class="mt-app-list">${apps.map(a=>{
    const leftTurns=a.app.deadline-turn,pct=Math.max(0,Math.min(100,leftTurns/a.app.span*100)),n=a.needs;
    const spec=n?`${ing(x,n.base).name} ${n.size}${n.toppings.length?` · ${n.toppings.length} topping`:''}`:'';
    return `<button type="button" class="mt-app ${a.id===t?.id?'on':''} ${leftTurns<0?'late':pct<35?'hurry':''}" ${pick(x,a.id)} aria-pressed="${a.id===t?.id}">
      <b>${x.esc(a.app.code)} · ${x.esc(a.customer)}</b><small>${x.esc(spec)}${a.cup?.sealed?' · ✓ đã dán nắp':''}</small>
      <span class="mt-bar" aria-hidden="true"><i style="width:${pct}%"></i></span><small>${leftTurns>=0?`Tài xế tới sau ${leftTurns} nhịp`:'Trễ giờ lấy đơn!'}</small></button>`;}).join('')}</div></section>`;
}
function queueRow(t,x){
  const seen=new Set(),chips=[];
  for(const v of x.room.tasks){
    if(!open(v)||v.app)continue;
    const g=v.group?.id;if(g&&seen.has(g))continue;if(g)seen.add(g);
    const sibs=g?x.room.tasks.filter(s=>s.group?.id===g):[v],first=sibs.find(open)||v;
    const active=sibs.some(s=>s.id===t?.id),p=x.room.life?.mode==='calm'?100:(first.patience??100);
    chips.push(`<button type="button" class="mt-guest ${active?'on':''}" ${pick(x,first.id)} aria-pressed="${active}" aria-label="${x.esc(first.customer)}, kiên nhẫn ${p}%${g?`, ${sibs.length} ly`:''}">
      ${ring(p,face(first,x,40))}<small>${x.esc(first.customer)}</small>${g?`<em class="mt-cups-badge">${sibs.length} ly</em>`:''}</button>`);
  }
  if(!chips.length||(chips.length<2&&!t?.app))return '';
  return `<section class="mt-queue" aria-label="Hàng chờ"><h4>Hàng chờ</h4><div class="mt-queue-list">${chips.join('')}</div></section>`;
}
function tabs(t,x){
  if(!t.group)return '';
  const sibs=x.room.tasks.filter(v=>v.group?.id===t.group.id).sort((a,b)=>a.group.i-b.group.i);
  return `<div class="mt-cuptabs" role="tablist" aria-label="Các ly trong đơn">${sibs.map(v=>{
    const done=v.status==='completed',gone=DONE.includes(v.status);
    return `<button type="button" role="tab" class="mt-cuptab ${v.id===t.id?'on':''} ${done?'done':''}" ${gone?'disabled':pick(x,v.id)} aria-selected="${v.id===t.id}">${done?'✓ ':''}Ly ${v.group.i}${v.cup?.sealed&&!done?' · đã dán':''}</button>`;}).join('')}</div>`;
}
const usualText=(x,u)=>`${ing(x,u.base).name} size ${u.size}${u.flavor?`, vị ${low(ing(x,u.flavor).name)}`:''}, ${u.toppings.length?u.toppings.map(k=>low(ing(x,k).name)).join(', '):'không topping'}, ${u.sugar}% đường, ${ICE_TEXT[u.ice]}`;
/** The regulars' card: usual cup (for "như mọi khi"), what the shop has learned, and a greeting. */
function notebookFor(t,x){
  const row=(B(x).notebook||[]).find(r=>r.npc===t.npc);
  if(t.walkin||!row)return '';
  if(!row.usual&&t.usual&&t.known)return `<p class="muted small">Sổ khách quen chưa ghi ly của ${x.esc(t.customer)}. Hỏi lại khách nhé.</p>`;
  const notes=row.notes||[];
  if(!(t.usual&&t.known)&&!notes.length)return '';
  const greet=notes.length&&!t.greeted?jb(x,'👋 “Như mọi khi hả?”','tea_greet',{task:t.id},'small cream'):t.greeted?'<span class="tag green">✓ Đã chào khách quen</span>':'';
  return `<details class="mt-notebook" ${t.usual||!t.greeted?'open':''}><summary>📒 Sổ khách quen · ${x.esc(row.name)} · ghé ${row.visits} lần</summary>
    ${t.usual&&t.known&&row.usual?`<p>${x.esc(usualText(x,row.usual))}.</p>`:''}
    ${notes.length?`<ul class="mt-notes">${notes.map(n=>`<li><span aria-hidden="true">${x.esc(n.emoji)}</span> ${x.esc(n.text)}</li>`).join('')}</ul>`:''}
    ${row.next_note?`<small>Ghé đủ ${row.next_note} lần để biết thêm.</small>`:''}${greet?`<div class="mt-greet">${greet}</div>`:''}</details>`;
}
function customer(t,x){
  const calm=x.room.life?.mode==='calm',p=calm?100:(t.patience??100),b=B(x);
  const tags=[t.usual?'🔁 Như mọi khi':'',t.vip?'🎥 Đang quay video':'',t.office?'💼 Văn phòng':'',t.discount?`🏷️ Bớt ${t.discount} xu`:''].filter(Boolean);
  let meter;
  if(t.app){const left=t.app.deadline-(b.turn||0),pct=Math.max(0,Math.min(100,left/t.app.span*100));meter=`<div class="mt-patience app"><span>TÀI XẾ</span><div class="mt-bar"><i style="width:${pct}%"></i></div><small>${left>=0?`${left} nhịp`:'trễ'}</small></div>`;}
  else meter=`<div class="mt-patience ${p<40?'low':p<70?'mid':''}"><span>KIÊN NHẪN</span><div class="mt-bar" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${p}" aria-label="Kiên nhẫn"><i style="width:${p}%"></i></div><small>${calm?'thong thả':p+'%'}</small></div>`;
  const words=t.known?(t.order_text||t.opening):t.opening;
  return `<section class="mt-customer ${t.app?'is-app':''}">
    <div class="mt-who">${t.app?'<span class="mt-face" style="--s:58px" aria-hidden="true">🛵</span>':face(t,x)}<small>${x.esc(t.customer)}</small></div>
    <div class="mt-bubble">${t.app?`<span class="mt-ticket-head">PHIẾU APP ${x.esc(t.app.code)}</span>`:''}<p>“${x.esc(words)}”</p>
      ${tags.length?`<div class="mt-tags">${tags.map(v=>`<span>${x.esc(v)}</span>`).join('')}</div>`:''}
      ${meter}
      ${!t.known?jb(x,'👂 Nghe gọi món','ask',{task:t.id},'primary mt-ask'):''}
      ${notebookFor(t,x)}
      <b class="mt-price">${t.quoted_price!=null?`${t.quoted_price} xu`:''}</b>
    </div></section>`;
}
function tile(x,o){
  const zero=o.count===0&&!o.locked;
  const act=o.locked||o.disabled?'':o.cmd?cmdAttr(x,o.cmd,o.payload):'';
  return `<button type="button" class="mt-tile ${o.cls||''}${o.on?' on':''}${o.locked?' locked':''}${zero?' zero':''}"${o.k?` data-k="${x.esc(o.k)}"`:''} ${act} ${o.locked||o.disabled?'disabled':''} aria-pressed="${!!o.on}" aria-label="${x.esc(o.label||o.name)}">
    ${o.art||`<span class="mt-emo" aria-hidden="true">${o.emoji}</span>`}<b>${x.esc(o.name)}</b>${o.sub?`<small>${x.esc(o.sub)}</small>`:''}
    ${o.locked?`<small class="mt-lock">🔒 Cấp ${o.level}</small>`:o.count!=null?`<em class="mt-count${o.count===0?' zero':''}" aria-hidden="true">${o.count}</em>`:''}</button>`;
}
function shelf(t,x,group,title){
  const cup=t.cup,items=cup.items||[],b=B(x);
  const ready=t.known&&cup.placed&&!cup.sealed;
  const limit={base:1,flavor:1,topping:3}[group],have=items.filter(k=>ing(x,k).group===group).length;
  const needBase=group!=='base'&&!hasGroup(x,cup,'base');
  const all=ings(x).filter(i=>i.group===group),shut=all.filter(i=>!station(x,i.id).unlocked),list=all.filter(i=>!shut.includes(i));
  return `<section class="mt-shelf ${group}"><h4>${title}${group==='topping'?` <small>${have}/${limit}</small>`:''}</h4><div class="mt-grid">${list.map(i=>{
    const s=station(x,i.id),inCup=items.includes(i.id);
    if(s.stock===0&&!inCup){
      if(s.made){const v=verb(i.id);return tile(x,{k:i.id,name:i.name,emoji:i.emoji,count:0,cls:'restock',cmd:'tea_prepare',payload:{item:i.id,qty:5,confirm:true},sub:`${v} +5 · ${i.cost*5} xu`,label:`${i.name} đã hết. ${v} 5 phần, ${i.cost*5} xu${s.fresh?', mất 20 phút':''}`});}
      const o=soonest(x,i.id);
      if(o)return tile(x,{name:i.name,emoji:i.emoji,count:0,cls:'restock wait',disabled:true,sub:`📦 ${o.eta_label}`,label:`${i.name} đã hết, hàng tới ${o.eta_label}`});
      const cost=expressCost(x,i.id,5);
      return tile(x,{name:i.name,emoji:i.emoji,count:0,cls:'restock',cmd:'tea_order',payload:{item:i.id,qty:5,supplier:'express',confirm:true},sub:`⚡ +5 · ${cost} xu`,label:`${i.name} đã hết. Gọi hỏa tốc 5 phần, ${cost} xu, tới trong 15–30 phút`});
    }
    const disabled=!ready||inCup||have>=limit||needBase;
    return tile(x,{k:i.id,name:i.name,emoji:i.emoji,count:s.stock,on:inCup,disabled,cls:s.tired?'tired':'',sub:s.tired?(s.tired>=s.stock?(i.group==='base'?'hơi chát':'hơi cứng'):`${s.tired} phần cũ`):'',cmd:'tea_add',payload:{task:t.id,item:i.id},label:`${i.name}, còn ${s.stock} phần${s.tired?`, ${s.tired} phần để lâu`:''}${inCup?', đã có trong ly':''}`});
  }).join('')}</div>${lockChip(x,shut)}</section>`;
}
/** "🔒 3 món mở ở cấp 2–4": the locked tiles of a shelf in one line (names and levels in the tooltip). */
function lockChip(x,list){
  if(!list.length)return '';
  const lv=list.map(i=>station(x,i.id).level||i.level||1),lo=Math.min(...lv),hi=Math.max(...lv);
  const names=list.map((i,n)=>`${i.name} (cấp ${lv[n]})`).join(', ');
  return `<p class="mt-lockchip" title="${x.esc(names)}" aria-label="${x.esc(`Chưa mở: ${names}`)}">🔒 ${list.length} món mở ở cấp ${lo===hi?lo:`${lo}–${hi}`}</p>`;
}
/** The station the next step is at ('cups', 'base', 'flavor', 'topping', 'dials'); '' = none (all open). */
const STATION_OF={cup:'cups',base:'base',flavor:'flavor',topping:'topping',ice:'dials',sugar:'dials'};
/** Only the station of the next step is open; the others are one line ("✓ 🫖 Trà nền · Matcha") that a
 * tap opens. With no step to follow (a usual order read from the notebook) every station stays open. */
function stations(t,x,steps){
  const cup=t.cup||{},items=cup.items||[],n=nextOf(steps),cur=n?STATION_OF[n.k]||'':'';
  const names=g=>items.filter(k=>ing(x,k).group===g).map(k=>ing(x,k).name).join(', ');
  const done=keys=>{const r=steps.filter(s=>keys.includes(s.k));return r.length&&r.every(s=>s.ok===true);};
  const parts=[['cups',()=>cupStack(t,x),`🥤 Chồng ly${cup.placed?` · Ly ${cup.size}`:''}`,['cup']],
    ['base',()=>shelf(t,x,'base','🫖 Trà nền'),`🫖 Trà nền${names('base')?` · ${names('base')}`:''}`,['base']],
    ['flavor',()=>shelf(t,x,'flavor','🍑 Siro'),`🍑 Siro${names('flavor')?` · ${names('flavor')}`:''}`,['flavor']],
    ['topping',()=>shelf(t,x,'topping','🧋 Topping'),`🧋 Topping ${items.filter(k=>ing(x,k).group==='topping').length}/3${names('topping')?` · ${names('topping')}`:''}`,['topping']],
    ['dials',()=>dials(t,x),`🧊 Đá${cup.ice?` · ${ICE_TEXT[cup.ice]}`:''} · 🍯 Đường${cup.sugar!=null?` ${cup.sugar}%`:''}`,['ice','sugar']]];
  return parts.map(([k,html,sum,keys])=>{
    const key=`${t.id}|${cur}|${k}`,open=!steps.length||k===cur||!!x.ui.mtShelf?.[key];
    if(open)return html();
    return `<section class="mt-shelf ${k} mt-folded${done(keys)?' done':''}"><button type="button" class="mt-fold-sum" data-action="car:shelf" data-key="${x.esc(key)}" aria-expanded="false">${done(keys)?'✓ ':''}${x.esc(sum)}</button></section>`;
  }).join('');
}
const verb=id=>['pearls','white_pearl'].includes(id)?'Nấu':['foam','cheese'].includes(id)?'Đánh':'Ủ';
function cupStack(t,x){
  const b=B(x),cup=t.cup,cups=b.cups||{M:0,L:0};
  return `<section class="mt-shelf cups"><h4>🥤 Chồng ly</h4><div class="mt-grid two">${['M','L'].map(size=>{
    const on=cup.placed&&cup.size===size,locked=(cup.items||[]).length&&!on;
    if(!cups[size]){
      const o=soonest(x,'cup_'+size);
      if(o)return tile(x,{name:`Ly ${size}`,emoji:'🥤',count:0,cls:'restock wait',disabled:true,sub:`📦 ${o.eta_label}`,label:`Hết ly ${size}, hàng tới ${o.eta_label}`});
      const cost=expressCost(x,'cup_'+size,1);
      return tile(x,{name:`Ly ${size}`,emoji:'🥤',count:0,cls:'restock',cmd:'tea_order',payload:{item:'cup_'+size,qty:1,supplier:'express',confirm:true},sub:`⚡ +${b.cup_pack?.qty||20} · ${cost} xu`,label:`Hết ly ${size}. Gọi hỏa tốc ${b.cup_pack?.qty||20} ly, ${cost} xu`});
    }
    return tile(x,{k:'cup_'+size,name:`Ly ${size}`,emoji:size==='L'?'🥤':'🧋',count:cups[size],on,disabled:!t.known||cup.sealed||locked,cmd:'tea_cup',payload:{task:t.id,size},label:`Ly size ${size}, còn ${cups[size]} ly`});
  }).join('')}</div></section>`;
}
function dials(t,x){
  const cup=t.cup,ok=t.known&&cup.placed&&!cup.sealed,sugars=B(x).sugars||[0,30,50,70,100];
  const seg=(cmd,val,label,on)=>`<button type="button" class="mt-seg ${on?'on':''}" data-k="${cmd.slice(4)}-${val}" ${ok?cmdAttr(x,cmd,{task:t.id,level:val}):'disabled'} aria-pressed="${on}">${label}</button>`;
  return `<section class="mt-shelf dials"><h4>🧊 Đá</h4><div class="mt-segs four">${ICE.map(([v,l])=>seg('tea_ice',v,l,cup.ice===v)).join('')}</div>
    <h4>🍯 Đường</h4><div class="mt-segs five">${sugars.map(v=>seg('tea_sugar',v,v+'%',cup.sugar===v)).join('')}</div></section>`;
}
function sealer(t,x){
  const b=B(x),cup=t.cup,S=seal(x),auto=(b.upgrades||[]).some(u=>u.id==='sealer'&&u.owned);
  const ready=t.known&&cup.placed&&hasGroup(x,cup,'base')&&cup.sugar!=null&&cup.ice!=null&&!cup.sealed;
  if(cup.sealed)return `<div class="mt-sealer done ${cup.seal_q||''}"><b>${cup.dome?'🫧 Đã đậy nắp cầu':SEAL_TEXT[cup.seal_q]||SEAL_TEXT.ok}</b></div>`;
  if(auto)return `<div class="mt-sealer">${jb(x,'⚙️ Dán nắp tự động','tea_seal',{task:t.id},'cream full',!ready)}</div>`;
  if(b.sealer_off)return `<div class="mt-sealer">${b.dome?jb(x,'🫧 Đậy nắp cầu · 1 xu','tea_seal',{task:t.id},'cream full',!ready):'<p class="muted small">Máy dán nắp đang ngưng.</p>'}</div>`;
  const pct=v=>v/S.max*100,start=cup.seal_t||0,held=start?Math.max(0,x.now()-start):0;
  const zones=[['loose',0,S.loose],['ok',S.loose,S.good_lo],['good',S.good_lo,S.good_hi],['ok',S.good_hi,S.burn],['burn',S.burn,S.max]];
  return `<div class="mt-sealer ${start?'running':''}">
    <div class="mt-gauge" data-seal-start="${start||''}" data-s="${[S.loose,S.good_lo,S.good_hi,S.burn,S.max].join(',')}" aria-hidden="true">${zones.map(([k,a,z])=>`<i class="z ${k}" style="left:${pct(a)}%;width:${pct(z-a)}%"></i>`).join('')}<b class="mt-needle" style="left:${Math.min(100,pct(held))}%"></b></div>
    <small class="mt-gauge-label" aria-live="polite">${start?'Đang ép nhiệt…':ready?`Nắp đẹp +1 xu: ép rồi nhả tay khi kim vào vùng xanh (${S.good_lo}–${S.good_hi} giây)`:'Pha xong trà, đá, đường rồi mới dán nắp'}</small>
    <div class="mt-seal-btns">${start?jb(x,'✋ Nhả tay!','tea_seal',{task:t.id},'primary big'):jb(x,'🔥 Ép nắp','tea_seal_start',{task:t.id},'cream',!ready)}
    ${start?'':jb(x,'Dán thường','tea_seal',{task:t.id},'ghost small',!ready)}</div>${start?'':wear(x)}</div>`;
}
/** Glue on the sealing plate: the green zone narrows until someone cleans it. */
function wear(x){
  const w=B(x).sealer;if(!w||w.state==='clean')return '';
  return `<p class="mt-wear ${x.esc(w.state)}"><span>${w.state==='dirty'?'⚠ Khuôn dán bẩn: vùng xanh chỉ còn một vạch.':'Khuôn dán bám keo: vùng xanh hẹp lại.'}</span>${jb(x,'🧽 Lau máy','tea_clean',{},'ghost small')}</p>`;
}
/** One line for the sticky bar: size · toppings · sugar · ice, each ticked once the cup matches. */
function recap(t,x){
  const b=B(x),want=t.needs||(t.usual?(b.notebook||[]).find(r=>r.npc===t.npc)?.usual:null),cup=t.cup||{},items=cup.items||[];
  if(!t.known)return 'Nghe khách gọi món trước';
  if(!want)return status(x,cup);
  const tick=ok=>ok?'✓ ':'';
  const tops=want.toppings.length?want.toppings.map(k=>low(ing(x,k).name)).join(', '):'không topping';
  return [`${tick(cup.placed&&cup.size===want.size)}Ly ${want.size}`,`${tick(cup.placed&&want.toppings.every(k=>items.includes(k)))}${tops}`,
    `${tick(cup.sugar===want.sugar)}${want.sugar}% đường`,`${tick(cup.ice===want.ice)}${ICE_TEXT[want.ice]}`].map(v=>v.replace(/ /g,'\u00a0')).join(' · ');
}
function finish(t,x){
  const cup=t.cup;
  return `<div class="mt-finish">${sealer(t,x)}
    <div class="mt-minor">${x.confirmCmd('🗑️ Đổ ly','tea_discard',{task:t.id},'Đổ ly đang làm? Nguyên liệu đã dùng được ghi hao hụt và tính là một lần làm lại.','ghost small',!(cup.placed||(cup.items||[]).length))}
    ${jb(x,'🔎 So phiếu','tea_check',{task:t.id},'ghost small',!t.known||!(cup.items||[]).length||cup.sealed)}</div>
    <p class="muted small">So phiếu sai sẽ tính một lỗi.</p></div>`;
}
function nextStep(t,x,detail=true){
  if(!t)return 'Chờ khách ghé quầy';
  const ev=B(x).event;
  if(ev&&ev.stage==='open')return 'Trả lời chuyện đang xảy ra ở quầy trước đã';
  if(ev&&ev.stage==='done')return 'Đọc kết quả rồi làm tiếp';
  if(!t.known)return 'Nghe khách gọi món';
  const n=detail?t.needs:null,cup=t.cup,items=cup.items||[];
  if(cup.sealed)return t.app?'Giao ly cho tài xế':'Trao ly cho khách';
  if(!cup.placed)return n?`Lấy ly size ${n.size}`:'Lấy ly đúng cỡ khách gọi';
  if(!hasGroup(x,cup,'base'))return n?`Rót ${low(ing(x,n.base).name)}`:'Rót trà nền khách gọi';
  if(n){
    if(n.flavor&&!items.includes(n.flavor))return `Thêm siro ${low(ing(x,n.flavor).name)}`;
    const miss=n.toppings.find(k=>!items.includes(k));if(miss)return `Múc ${low(ing(x,miss).name)}`;
    if(cup.ice!==n.ice)return `Cho đá: ${ICE_TEXT[n.ice]}`;
    if(cup.sugar!==n.sugar)return `Đường ${n.sugar}%`;
  }else{
    if(cup.ice==null)return 'Chọn mức đá khách dặn';
    if(cup.sugar==null)return 'Chọn mức đường khách dặn';
  }
  return 'Ép nắp, nhả tay khi kim vào vùng xanh';
}

/* ---------------------------------------------------------------- next step (v4/guide.js) */
// A step's tap goes through actions.go like every counter tap (quiet, feedback next to the cup).
const run=(op,payload,label)=>({act:'car:go',data:{op,payload:JSON.stringify(payload)},label});
const kSel=k=>`.mt-stations [data-k="${k}"]`;
const CRIT=new Set(['cup','base','flavor','topping']);
/** The order as steps: cup, tea, syrup, toppings, ice, sugar, lid. On a first task the bottom
 * button does each step and the right tile glows; later it names the step and points at the tile. */
function brewSteps(t,x){
  const b=B(x),cup=t.cup||{},items=cup.items||[],n=t.needs,id=t.id,first=firstTime(x),sealed=!!cup.sealed;
  if(!n)return [];
  const redo={cmd:'tea_discard',payload:{task:id,confirm:true},confirm:'Ly này sai rồi. Đổ ly và pha lại từ đầu?',label:'🗑️ Đổ ly, pha lại'};
  // The right tile: tap it for the player on a first task, otherwise point at it.
  const tap=(k,op,payload,label)=>first?run(op,payload,label):{sel:kSel(k),label};
  // A needed ingredient that has run out: make more at the counter, or ask the guest to swap.
  const refill=k=>{const s=station(x,k),i=ing(x,k);
    if(s.made)return run('tea_prepare',{item:k,qty:5,confirm:true},`${verb(k)} thêm ${x.esc(low(i.name))} · ${i.cost*5} xu`);
    return {sel:'.mt-out',label:`🙏 Hết ${x.esc(low(i.name))}: mời khách đổi`};};
  const rows=[],name=k=>low(ing(x,k).name);
  const cupOk=cup.placed?cup.size===n.size:null;
  let go=null;
  if(!sealed&&cupOk!==true){
    if(cup.placed&&items.length)go=redo;
    else if(!(b.cups||{})[n.size])go={sel:'.mt-out',label:`🙏 Hết ly ${n.size}: mời khách đổi cỡ`};
    else go=tap('cup_'+n.size,'tea_cup',{task:id,size:n.size},`${n.size==='L'?'🥤':'🧋'} Lấy ly ${n.size}`);
  }
  rows.push({k:'cup',at:kSel('cup_'+n.size),ok:cupOk,label:`Lấy ly ${n.size}`,go,pulse:first&&go?.act?kSel('cup_'+n.size):go?.sel?'.mt-out .btn':''});
  const base=items.find(k=>ing(x,k).group==='base'),bOk=base?base===n.base:null;
  go=null;
  if(!sealed&&base&&!bOk)go=redo;
  else if(!sealed&&!base&&cup.placed)go=station(x,n.base).stock?tap(n.base,'tea_add',{task:id,item:n.base},`🫖 Rót ${x.esc(name(n.base))}`):refill(n.base);
  rows.push({k:'base',at:kSel(n.base),ok:bOk,label:`Rót ${name(n.base)}`,go,pulse:first&&go?.act&&go.data.op==='tea_add'?kSel(n.base):go?.sel?'.mt-out .btn':''});
  const add=(k,group,label,icon)=>{
    const has=items.includes(k);let g=null;
    if(!sealed&&!has&&base)g=station(x,k).stock?tap(k,'tea_add',{task:id,item:k},`${icon} ${x.esc(label)}`):refill(k);
    rows.push({k:group,at:kSel(k),ok:has||null,label,go:g,pulse:first&&g?.act&&g.data.op==='tea_add'?kSel(k):g?.sel?'.mt-out .btn':''});
  };
  if(n.flavor)add(n.flavor,'flavor',`Thêm siro ${name(n.flavor)}`,'🍑');
  for(const k of n.toppings)add(k,'topping',`Múc ${name(k)}`,'🧋');
  // Something the guest did not ask for: only a new cup takes it out.
  for(const k of items)if(k!==base&&k!==n.flavor&&!n.toppings.includes(k))rows.push({k:'topping',ok:false,label:`Bỏ ${name(k)} (khách không gọi)`,go:redo});
  const dial=(kind,want,have,label,icon)=>{
    const ok=have==null?null:have===want;
    const g=!sealed&&cup.placed&&!ok?tap(`${kind}-${want}`,'tea_'+kind,{task:id,level:want},`${icon} ${x.esc(label)}`):null;
    rows.push({k:kind,at:kSel(`${kind}-${want}`),ok,label,go:g,pulse:first&&g?kSel(`${kind}-${want}`):''});
  };
  dial('ice',n.ice,cup.ice,`Đá: ${ICE_TEXT[n.ice]}`,'🧊');
  dial('sugar',n.sugar,cup.sugar,`Đường ${n.sugar}%`,'🍯');
  // The lid: the bottom button always does a plain press (safe); the press-and-release game for a
  // perfect lid (+1 xu) stays on the sealer, and once it runs the bottom button lets go.
  const ready=rows.every(r=>r.ok===true),auto=(b.upgrades||[]).some(u=>u.id==='sealer'&&u.owned);
  let lid=null,note='';
  if(!sealed&&ready){
    if(auto)lid=run('tea_seal',{task:id},'⚙️ Dán nắp');
    else if(b.sealer_off){if(b.dome)lid=run('tea_seal',{task:id},'🫧 Đậy nắp cầu · 1 xu');else note='máy dán nắp đang ngưng, chờ có điện';}
    else if(cup.seal_t)lid=run('tea_seal',{task:id},'✋ Nhả tay!');
    else lid=run('tea_seal',{task:id},'✅ Dán nắp');
  }
  rows.push({k:'seal',at:'.mt-sealer',ok:sealed||null,label:'Dán nắp',note,go:lid});
  // After the lid only a wrong cup, tea, syrup or topping still matters (the guest hands it back).
  return sealed?rows.filter(r=>r.ok!==false||CRIT.has(r.k)):rows;
}
/** Python's round() (ties to even), so the app fee shown is the fee the server takes. */
const pyRound=v=>{const f=Math.floor(v),d=v-f;return d>0.5||(d===0.5&&f%2)?f+1:f;};
/** What the shop actually books for this cup, with the math when it is not the menu price. */
function netText(t,x){
  const q=t.quoted_price,off=t.discount||0,fee=t.app?pyRound(q*(B(x).app_fee||20)/100):0,net=Math.max(0,q-off-fee);
  return net===q?`${q} xu`:`${q}${off?` − bớt ${off}`:''}${fee?` − app ${fee}`:''} = ${net} xu`;
}
/** {steps, final} for the counter: the hint, the ticket rows and the bottom button all read it. */
function teaGuide(t,x){
  const ev=B(x).event,id=t.id;
  if(ev&&ev.stage==='open')return {steps:[{ok:null,label:'Chọn cách xử lý chuyện ở quầy',go:{sel:'.mt-event .mt-choices'},pulse:'.mt-event .mt-choices .btn'}]};
  if(ev&&ev.stage==='done')return {steps:[{ok:null,label:'Đọc kết quả rồi làm tiếp',go:run('tea_event_ok',{},'👍 Làm tiếp')}]};
  if(!t.known)return {steps:[{ok:null,label:'Nghe khách gọi món',go:run('ask',{task:id},'👂 Nghe gọi món'),pulse:'.mt-ask',at:'.mt-ask'}]};
  const steps=brewSteps(t,x),sealed=!!t.cup?.sealed;
  const label=`${t.app?'🛵 Giao tài xế':'🛎️ Giao món'}${t.quoted_price!=null?` · ${netText(t,x)}`:''}`;
  const go=nextOf(steps)?finalGo(steps,'tea_serve',{task:id},{question:'Khách có thể trả ly.',confirm:true}):run('tea_serve',{task:id,confirm:true},label);
  return {steps,final:{label,go,ready:sealed}};
}
function hintFor(t,x){
  const g=teaGuide(t,x);
  const final=g.final?.ready?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null;
  return nextHint(x,g.steps.filter(s=>s.ok!==false||s.go),{final});
}

/* ---------------------------------------------------------------- care loop */
const TONE={ok:'✓',warn:'!',danger:'✗'};
/** Buttons a care row offers right where it is read. */
function careBtns(r,x,sheet=false){
  const b=B(x),open=!!x.room.open;
  if(r.id.startsWith('pot-')){
    const id=r.id.slice(4),i=ing(x,id);
    return jb(x,`Nấu +5 · ${i.cost*5} xu`,'tea_prepare',{item:id,qty:5,confirm:true},'small')+(r.tone==='warn'&&station(x,id).tired?jb(x,'Đổ mẻ cũ','tea_toss',{item:id},'small ghost'):'');
  }
  if(r.id==='sealer'&&r.tone!=='ok'&&open)return jb(x,'🧽 Lau máy · 20 phút','tea_clean',{},'small');
  if(['tea','tea-empty','cups'].includes(r.id)&&!sheet)return x.button('🧺 Mở kho','prepare',{},'small ghost');
  return '';
}
function careRows(x,rows,sheet=false){
  return `<ul class="mt-care">${rows.map(r=>{const btns=careBtns(r,x,sheet);return `<li class="${x.esc(r.tone)}"><span class="mt-care-mark" aria-label="${r.tone==='ok'?'ổn':r.tone==='warn'?'cần để ý':'cần làm ngay'}">${TONE[r.tone]||'•'}</span><span class="mt-care-icon" aria-hidden="true">${x.esc(r.icon||'')}</span><span class="mt-care-text">${x.esc(r.text)}</span>${btns?`<span class="mt-care-btns">${btns}</span>`:''}</li>`;}).join('')}</ul>`;
}
/** Folded care list on the counter; opens by itself when something needs doing now. */
function careFold(x){
  const rows=B(x).care||[];if(!rows.length)return '';
  const bad=rows.filter(r=>r.tone!=='ok').length,danger=rows.some(r=>r.tone==='danger');
  const open=x.ui.mtCare??danger;
  return `<details class="mt-care-fold"${open?' open':''}><summary data-action="car:fold" data-key="mtCare"><span>🧋 Việc chăm quầy</span>${bad?`<em class="mt-care-count ${danger?'danger':''}">${bad}</em>`:'<em class="mt-care-count ok">ổn</em>'}</summary>${careRows(x,rows)}</details>`;
}
function orderRows(x){
  const list=B(x).orders||[];
  if(!list.length)return '<p class="muted small">Chưa có đơn nào đang giao.</p>';
  return `<div class="mt-rows">${list.map(o=>`<div class="mt-row mt-order ${o.late_note?'late':''}"><span class="mt-emo" aria-hidden="true">${x.esc(o.emoji)}</span><div class="grow"><b>${o.cups?`${o.qty} thùng ${x.esc(o.name)}`:`${o.qty} phần ${x.esc(o.name)}`}</b><small>${x.esc(o.supplier_name)} · dự kiến <b>${x.esc(o.eta_label)}</b> · ${x.esc(o.left_label)}</small>${o.late_note?`<small class="mt-late">⏰ ${x.esc(o.late_note)}</small>`:''}<span class="mt-bar" aria-hidden="true"><i style="width:${Math.round((o.progress||0)*100)}%"></i></span></div></div>`).join('')}</div>`;
}
/** Supplier cards for the chosen item: the live promise in plain words, price and reliability. */
function supplierPicker(x,id){
  const b=B(x),cups=id.startsWith('cup_'),qtys=cups?[1,2,3]:[5,10,20];
  const qty=qtys.includes(x.ui.mtQty)?x.ui.mtQty:qtys[0];
  const sups=b.suppliers||[],cheapest=Math.min(...sups.filter(s=>!s.items||s.items.includes(id)).map(s=>s.factor));
  return `<div class="mt-picker"><div class="mt-qty" role="group" aria-label="Số lượng">${qtys.map(q=>`<button type="button" class="mt-seg ${q===qty?'on':''}" data-action="car:qty" data-qty="${q}" aria-pressed="${q===qty}">${cups?`${q} thùng · ${q*(b.cup_pack?.qty||20)} ly`:`${q} phần`}</button>`).join('')}</div>
    <div class="mt-sups">${sups.map(s=>{
      const sells=!s.items||s.items.includes(id),cost=orderCost(x,id,qty,s.factor);
      const tags=[s.factor===cheapest?'rẻ nhất':'',s.factor>1?'đắt':'',s.late>=12?'hay trễ':''].filter(Boolean);
      return `<article class="mt-sup ${sells?'':'off'}"><div class="mt-sup-head"><span aria-hidden="true">${x.esc(s.emoji)}</span><b>${x.esc(s.name)}</b></div>
        ${sells?`<p class="mt-sup-when">${x.esc(s.quote?.label||s.window)}</p><small>${x.esc(s.window)} · giá ×${String(s.factor).replace('.',',')}${tags.length?' · '+tags.map(v=>x.esc(v)).join(' · '):''}</small>${jb(x,`Đặt · ${cost} xu`,'tea_order',{item:id,qty,supplier:s.id,confirm:true},'small primary',x.room.money<cost)}`:'<small>Không bán mặt hàng này</small>'}</article>`;}).join('')}</div></div>`;
}

/* ---------------------------------------------------------------- prepare */
const TABS=[['stock','🧺','Kho'],['upgrade','🛠️','Nâng cấp'],['price','🏷️','Giá bán'],['reviews','⭐','Đánh giá'],['recap','📒','Tổng kết']];
function board(x){
  const b=B(x),pr=b.prices||{},prices=x.room.life?.prices||{};
  const bases=ings(x).filter(i=>i.group==='base');
  return `<div class="chalkboard mt-board"><h2>🧋 Menu hôm nay</h2><div class="chalk-columns">${bases.map(i=>{const s=station(x,i.id);return `<div class="${s.unlocked?'':'locked'}"><span>${x.esc(i.name)}</span><b>${s.unlocked?`${prices[i.id]||pr.base?.[i.id]||30} xu`:`🔒 cấp ${s.level}`}</b></div>`;}).join('')}</div>
    <p class="center">Siro +${pr.flavor??6} xu · Topping +${pr.topping??5} xu · Size L +${pr.size_l??7} xu</p></div>`;
}
function stockTab(x){
  const b=B(x),pantry=x.room.life?.pantry||[],day=x.room.day,cups=b.cups||{},now=b.now||{},pick=x.ui.mtItem;
  const lot=id=>{const l=pantry.filter(v=>v.item===id&&v.qty>0&&v.expires>=day);return l.length?Math.min(...l.map(v=>v.expires)):null;};
  const batch=id=>(b.batches||[]).find(v=>v.item===id);
  const locked=i=>`<div class="mt-row locked"><span class="mt-emo" aria-hidden="true">${i.emoji}</span><div class="grow"><b>${x.esc(i.name)}</b><small>🔒 Mở ở tay nghề cấp ${station(x,i.id).level}</small></div></div>`;
  // Made at the counter: brewed pots, pearl batches, whipped foam.
  const made=ings(x).filter(i=>station(x,i.id).made).map(i=>{
    const s=station(x,i.id);if(!s.unlocked)return locked(i);
    const bt=batch(i.id),first=bt?.lots?.[0],exp=lot(i.id);
    const fresh=s.fresh?(first?`${first.made?`${verb(i.id)} ${first.made} · `:''}<span class="${first.band==='fresh'?'':'warn'}">${x.esc(first.word)}${first.band==='fresh'&&first.good_until?` tới ${first.good_until}`:first.ok_until?` · bỏ lúc ${first.ok_until}`:''}</span>${bt.lots.length>1?` · ${bt.lots.length} mẻ`:''}`:'chưa có mẻ nào'):(exp!=null?`dùng hết ngày ${exp}`:'');
    return `<div class="mt-row ${s.stock===0?'empty':''}"><span class="mt-emo" aria-hidden="true">${i.emoji}</span><div class="grow"><b>${x.esc(i.name)}</b><small><span class="mt-count-inline ${s.stock===0?'zero':''}">Còn ${s.stock}</span>${fresh?` · ${fresh}`:''}</small></div><div class="mt-row-btns">${s.tired?jb(x,'Đổ mẻ cũ','tea_toss',{item:i.id},'small ghost'):''}${jb(x,`${verb(i.id)} +5 · ${i.cost*5} xu`,'tea_prepare',{item:i.id,qty:5,confirm:true},'small')}</div></div>`;
  }).join('');
  // Bought from suppliers: cups, syrups, jellies…
  const buyRow=(id,emoji,name,have,sub)=>{
    const o=pending(x,id),on=pick===id;
    return `<div class="mt-buy ${on?'on':''}"><div class="mt-row ${have===0?'empty':''}"><span class="mt-emo" aria-hidden="true">${emoji}</span><div class="grow"><b>${x.esc(name)}</b><small><span class="mt-count-inline ${have===0?'zero':''}">Còn ${have}</span>${sub?` · ${sub}`:''}${o.length?` · 📦 ${x.esc(o[0].eta_label)}`:''}</small></div><button type="button" class="btn small ${on?'primary':''}" data-action="car:pick" data-item="${x.esc(id)}" aria-expanded="${on}">${on?'Đóng':'Đặt hàng'}</button></div>${on?supplierPicker(x,id):''}</div>`;
  };
  const cupRows=['M','L'].map(size=>buyRow('cup_'+size,'🥤',`Ly ${size}`,cups[size]||0,`${b.cup_pack?.qty||20} ly/thùng`)).join('');
  const bought=ings(x).filter(i=>!station(x,i.id).made).map(i=>{const s=station(x,i.id);if(!s.unlocked)return locked(i);const exp=lot(i.id);return buyRow(i.id,i.emoji,i.name,s.stock,`${i.cost} xu/phần${exp!=null?` · dùng hết ngày ${exp}`:''}`);}).join('');
  const night=(b.night||[]).length?`<div class="mt-night">${b.night.map(l=>`<p>${x.esc(l)}</p>`).join('')}</div>`:'';
  const wait=x.room.open&&(b.orders||[]).length?jb(x,'⏳ Chờ thêm 20 phút','tea_wait',{},'ghost small'):'';
  return `<p class="mt-now">🕑 ${now.is_open?`Bây giờ <b>${x.esc(now.time||b.clock||'')}</b>${overtime(b)?' · tăng ca, nhà cung cấp đã nghỉ':''}`:`Đã đóng cửa · mở lại ${x.esc(now.open||'08:00')}`}</p>${night}
    <h3 class="section-title">🧋 Việc chăm quầy</h3>${careRows(x,b.care||[],true)}
    <h3 class="section-title">🫖 Nồi, bình & mẻ hôm nay</h3><p class="muted small">Làm ngay tại quầy. Ủ trà, nấu trân châu mất 20 phút khi quán mở; làm trước giờ mở cửa thì không mất thời gian. Trà ủ và trân châu không để qua đêm.</p><div class="mt-rows">${made}</div>
    <h3 class="section-title">📦 Đang giao</h3>${orderRows(x)}${wait?`<p class="row wrap">${wait}</p>`:''}
    <h3 class="section-title">🛒 Đặt hàng</h3><p class="muted small">Trả tiền khi đặt. Mỗi nhà giao một kiểu: hỏa tốc 15–30 phút, xe bốn chuyến mỗi ngày, chợ chiều nay hoặc sáng mai, xưởng 1–2 ngày.</p>
    <div class="mt-rows">${cupRows}${bought}</div>`;
}
function upgradeTab(x){
  return `<div class="mt-upgrades">${(B(x).upgrades||[]).map(u=>`<article class="mt-upgrade ${u.owned?'owned':''}"><span class="mt-emo big" aria-hidden="true">${x.esc(u.emoji)}</span><div class="grow"><h4>${x.esc(u.name)}</h4><p>${x.esc(u.text)}</p></div>${u.owned?'<span class="tag green">✓ Đã lắp</span>':!u.ready?`<span class="tag">🔒 Tay nghề cấp ${u.level}</span>`:x.confirmCmd(`Lắp · ${u.price} xu`,'tea_upgrade',{id:u.id},`Lắp ${u.name} với giá ${u.price} xu?`,'primary small',x.room.money<u.price)}</article>`).join('')}</div>`;
}
function priceTab(x){
  const b=B(x),base=b.prices?.base||{},prices=x.room.life?.prices||{},closed=!x.room.open;
  return `${board(x)}<p class="muted">Đổi giá trà nền trong khoảng 75%–125% giá gốc, trước khi mở cửa.</p><div class="price-editor">${ings(x).filter(i=>i.group==='base').map(i=>{
    const s=station(x,i.id),g=base[i.id]||30,v=prices[i.id]||g;
    return `<div><strong>${x.esc(i.emoji)} ${x.esc(i.name)}${s.unlocked?'':' 🔒'}</strong><input class="input" type="number" id="price-${i.id}" min="${Math.round(g*.75)}" max="${Math.round(g*1.25)}" value="${v}" data-preserve aria-label="Giá ${x.esc(i.name)}" ${closed?'':'disabled'}>${x.button('Lưu giá','expPrice',{item:i.id},'small')}</div>`;}).join('')}</div>`;
}
function reviewsTab(x){
  const posts=(x.room.feed||[]).filter(p=>p.stars),dist=[5,4,3,2,1].map(s=>[s,posts.filter(p=>p.stars===s).length]),max=Math.max(1,...dist.map(d=>d[1]));
  return `<div class="mt-rating"><div class="mt-rating-big"><strong>${x.room.rating||'—'}</strong><small>${posts.length} đánh giá</small></div><div class="mt-dist">${dist.map(([s,n])=>`<div><span>${s}★</span><i><b style="width:${n/max*100}%"></b></i><small>${n}</small></div>`).join('')}</div></div>
    <div class="mt-reviews">${posts.slice(0,6).map(p=>`<article><div class="row spread"><b>${x.esc(p.author||'Khách')}</b><span class="mt-stars" aria-label="${p.stars} sao">${'★'.repeat(p.stars)}${'☆'.repeat(5-p.stars)}</span></div><p>${x.esc(p.text)}</p><small>Ngày ${p.day}</small></article>`).join('')||'<p class="muted">Chưa có đánh giá nào.</p>'}</div>${x.button('Đọc & trả lời đánh giá','feedback',{},'ghost')}`;
}
function recapTab(x){
  const b=B(x),h=(b.history||[]).slice().reverse(),pct=b.next_tier?Math.min(100,(b.total||0)/b.next_tier*100):100;
  return `<div class="mt-tier"><b>⭐ Tay nghề cấp ${b.level||1}</b><div class="mt-bar"><i style="width:${pct}%"></i></div><small>${b.next_tier!=null?`${b.total||0}/${b.next_tier} ly để lên cấp: mở thêm trà, topping và nâng cấp mới`:'Đã lên bậc cao nhất'}</small></div>
    ${h.length?`<div class="mt-table" role="table" aria-label="Các ngày gần đây"><div role="row" class="head"><span>Ngày</span><span>Ly</span><span>Chuẩn</span><span>Bỏ về</span><span>Thu</span></div>${h.map(r=>`<div role="row"><span>${r.day}</span><span>${r.served}</span><span>${r.perfect}</span><span>${r.walkouts}</span><span>${r.revenue} xu</span></div>`).join('')}</div>`:'<p class="muted">Khép ca đầu tiên để xem tổng kết từng ngày.</p>'}
    <h3 class="section-title">📒 Sổ khách quen</h3><div class="mt-rows">${(b.notebook||[]).map(r=>`<div class="mt-row mt-regular"><span class="mt-emo" aria-hidden="true">📒</span><div class="grow"><b>${x.esc(r.name)}</b><small>${r.usual?`${x.esc(ing(x,r.usual.base).name)} ${r.usual.size} · ${r.usual.sugar}% đường · ${ICE_TEXT[r.usual.ice]}`:'Chưa ghi ly quen'} · ghé ${r.visits} lần</small>${(r.notes||[]).map(n=>`<small class="mt-note">${x.esc(n.emoji)} ${x.esc(n.text)}</small>`).join('')}${r.next_note?`<small class="muted">Ghé đủ ${r.next_note} lần để biết thêm một điều.</small>`:''}</div></div>`).join('')}</div>`;
}
function prepare(x,tab){
  const c=x.room,b=B(x),mod=b.modifier||{},w=b.warnings||[],tm=b.tomorrow||{};
  tab=TABS.some(v=>v[0]===tab)?tab:'stock';
  const modes=x.content.experiences?.modes||[];
  const panel={stock:stockTab,upgrade:upgradeTab,price:priceTab,reviews:reviewsTab,recap:recapTab}[tab](x);
  const goals=(c.life?.goals||[]).map(g=>`<li class="${g.claimed?'done':''}"><div><strong>${x.esc(g.title)}</strong><small>Thưởng ${g.reward} xu</small></div><div class="prep-goal-end">${g.claimed?'<span class="done-mark">✓ Đã nhận</span>':g.current>=g.goal?jb(x,'Nhận quà','life_goal',{goal:g.id},'small primary'):`<b>${Math.min(g.current,g.goal)}/${g.goal}</b>`}</div></li>`).join('');
  return `<div class="preparation-topline">${x.button('← Hành trình','home',{},'ghost small')}<span>CHUẨN BỊ NGÀY ${c.day}</span>${x.button(x.icon('x',20),'close',{},'ghost small')}</div>
  <div class="life-content career-job mt mt-prep prep-v2">
    <header class="prep-head"><div class="prep-id"><span class="sign-kicker">QUẦY TRÀ SỮA</span><h1>${x.esc(c.life?.shop_name||'Trà Mây & Trân Châu')}</h1></div><div class="prep-level"><div class="prep-level-row"><span>⭐ Tay nghề cấp ${b.level||1}</span><small>${b.total||0} ly đã pha</small></div><div class="prep-xp" aria-hidden="true"><i style="width:${b.next_tier?Math.min(100,(b.total||0)/b.next_tier*100):100}%"></i></div></div>${x.button('✏️ Đổi tên','expRename',{},'small ghost')}</header>
    <section class="prep-block prep-today" aria-label="Hôm nay"><h2 class="prep-h">${c.open?'Hôm nay':`Ngày ${x.state?.journey?.story?x.state.journey.life_day:c.day}`}</h2><div class="prep-today-grid"><div class="prep-weather"><span class="prep-weather-em" aria-hidden="true">${x.esc((c.open?mod:tm).emoji||'🌤️')}</span><div><strong>${x.esc((c.open?mod:tm).title||'')}</strong><p>${x.esc(c.open?(mod.text||''):(tm.advice||''))}</p></div></div>${c.open&&tm.title&&(b.care||[]).some(r=>r.id==='tomorrow')?`<div class="prep-weather mt-tomorrow"><span class="prep-weather-em" aria-hidden="true">${x.esc(tm.emoji)}</span><div><strong>Mai: ${x.esc(tm.title)}</strong><p>${x.esc(tm.advice)}</p></div></div>`:''}${goals?`<div class="prep-quests"><h3 class="prep-sub">🌞 Nhiệm vụ hôm nay</h3><ul class="prep-goals">${goals}</ul></div>`:''}</div></section>
    ${w.length?`<div class="mt-warns">${w.map(v=>`<button type="button" class="btn mt-warn" data-action="car:prep" data-tab="${v.where==='stock'?'stock':'stock'}">⚠ ${x.esc(v.text)}</button>`).join('')}</div>`:''}
    <nav class="mt-tabs" role="tablist" aria-label="Chuẩn bị quầy">${TABS.map(([id,e,l])=>`<button type="button" role="tab" class="mt-tab ${tab===id?'on':''}" data-action="car:prep" data-tab="${id}" aria-selected="${tab===id}"><span aria-hidden="true">${e}</span> ${l}</button>`).join('')}</nav>
    <section class="mt-panel" role="tabpanel">${panel}</section>
  </div>
  <footer class="life-sticky">${x.button(c.open?'Về quầy · pha tiếp':`Mở cửa ngày ${x.state?.journey?.story?x.state.journey.life_day:c.day}`,c.open?'workbench':'start',{},'primary jumbo'+(c.metrics?.served>0?'':' gd-pulse'))}</footer>`;
}

/* ---------------------------------------------------------------- module */
let focusKey='';
/** Bring the next step's control into view once when the step changes, unless it is already
 * visible between the sheet header and the pinned bar. Scrolls only; never rebuilds the DOM. */
function focusStep(root){
  const key=root.dataset.mtKey||'';
  if(!key||key===focusKey)return;
  focusKey=key;
  const at=root.dataset.mtAt,el=at&&[...root.querySelectorAll(at)].find(e=>e.offsetParent!==null);
  if(!el)return;
  const r=el.getBoundingClientRect(),head=root.closest('dialog')?.querySelector('.sheet-head')?.getBoundingClientRect().bottom||0;
  const bar=root.querySelector('.fk-bar'),bottom=bar&&bar.offsetParent!==null?bar.getBoundingClientRect().top:innerHeight;
  if(r.top>=head&&r.bottom<=bottom)return;
  el.scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
}
export default {
  id:'milk_tea',
  css:true,
  autoNext:true,
  next(t,x){
    try{const n=x&&nextOf(teaGuide(t,x).steps);if(n)return x.esc(stepLine(n));}catch{/* fall back to the fixed lines */}
    return nextStep(t,x,(B(x).level||1)<=3);
  },
  clock(c){return c.data?.boba?.clock||'';},
  job(t,x){
    const g=teaGuide(t,x),ticket=t.known&&g.final?stepRows(x,g.steps,'Phiếu gọi món'):'';
    const layout=`<div class="mt-bench"><div class="mt-side"><section class="mt-preview">${cupArt(x,t.cup)}<div class="mt-said">${ticket?`<small class="mt-ticket-head">🧾 Phiếu gọi món</small>`:`<p class="mt-status">${x.esc(status(x,t.cup))}</p>`}${x.ui.flash?`<p class="mt-flash" role="status">${x.esc(x.ui.flash)}</p>`:''}</div>${ticket}</section>${finish(t,x)}</div>
      <div class="mt-stations">${stations(t,x,g.final?g.steps:[])}</div></div>`;
    // The order recap and the next step (then the hand-over) stay pinned above the sheet footer.
    // The mini cup keeps the result in view next to whichever station the step scrolled to.
    const cta=stepCta(x,g.steps,g.final||{label:'',go:null,ready:false},{style:'primary big grow'});
    const bar=`<div class="fk-bar mt-bar">${t.known?`<span class="mt-bar-cup" aria-hidden="true">${cupArt(x,t.cup,true)}</span>`:''}<p class="fk-next" aria-live="polite">${x.esc(recap(t,x))}</p><div class="fk-bar-btns">${cta}</div></div>`;
    // After each step the screen scrolls to the control of the next one (tick), once per step.
    const n=nextOf(g.steps),at=!n||B(x).event?'':n.go?.sel||(n.go?.cmd==='tea_discard'?'.mt-minor':'')||n.at||'';
    return `<div class="career-job mt" data-mt-at="${x.esc(at)}" data-mt-key="${x.esc(`${t.id}|${n?.label||''}|${n?.ok}`)}">${hintFor(t,x)}${hud(x)}${eventCard(x)}${alerts(x)}${(B(x).care||[]).some(r=>r.tone!=='ok')?careFold(x):''}${appRow(t,x)}${queueRow(t,x)}${customer(t,x)}${tabs(t,x)}${outOfStock(t,x)}${t.known?layout:''}${bar}</div>`;
  },
  idle(x){
    const b=B(x),waiting=x.room.tasks.filter(open),left=b.left||0,orders=b.orders||[];
    const who=waiting[0]?.customer||'khách';
    const step=waiting.length?{ok:null,label:`Mời ${who} lên quầy`,go:{act:'job',data:{task:waiting[0].id},label:`👋 Mời ${x.esc(who)} lên quầy`}}
      :left?{ok:null,label:'Mời khách tiếp theo',go:run('more_work',{},'🔔 Mời khách tiếp theo')}
      :{ok:null,label:'Khép ca hôm nay',go:{act:'end',label:'🌙 Khép ca hôm nay'}};
    const next=stepCta(x,[step],{label:'',go:null,ready:false},{style:'primary'});
    const wait=x.room.open&&orders.length&&!waiting.length?jb(x,'⏳ Chờ hàng · 20 phút','tea_wait',{},'ghost'):'';
    const night=(b.night||[]).length?`<div class="mt-night">${b.night.map(l=>`<p>${x.esc(l)}</p>`).join('')}</div>`:'';
    return `<div class="career-job mt">${B(x).event?'':nextHint(x,[step])}${hud(x)}${eventCard(x)}${alerts(x)}${night}${careFold(x)}${orders.length?`<section class="mt-orders"><h4>📦 Đang giao</h4>${orderRows(x)}</section>`:''}<div class="row wrap">${next}${wait}${x.button('🧺 Kho & đặt hàng','prepare',{},'ghost')}</div></div>`;
  },
  page(view,x){
    if(!['prepare','prices'].includes(view))return '';
    // "Bảng giá" opens on the price tab; tabs switch inside the same sheet.
    if(view==='prices'&&x.ui.lastPage!=='prices')x.ui.prep='price';
    x.ui.lastPage=view;
    return prepare(x,x.ui.prep);
  },
  actions:{
    async prep(data,el,x){x.ui.prep=data.tab;x.render();},
    async pick(data,el,x){x.ui.mtItem=x.ui.mtItem===data.item?null:data.item;x.render();},
    async shelf(data,el,x){(x.ui.mtShelf??={})[data.key]=true;x.render();},
    async qty(data,el,x){x.ui.mtQty=Number(data.qty)||null;x.render();},
    async fold(data,el,x){const d=el.closest('details');if(data.key)x.ui[data.key]=d?!d.open:!x.ui[data.key];},
    async go(data,el,x){
      let payload={};try{payload=JSON.parse(data.payload||'{}');}catch{return;}
      sfx.configure(x.state.settings||{});sfx.unlock();
      try{
        const r=await x.api.command(data.op,payload)||{};
        x.ui.flash=data.op==='ask'?'':r.message||'';
        if(r.celebrate)sfx.success();else sfx.click();
        if(r.message&&(LOUD.has(data.op)||r.celebrate||/khách mới|bỏ về|hủy|quá giờ/.test(r.message)))x.toast(r.message,r.correct===false?'error':r.celebrate?'good':false);
        for(const note of new Set(r.effects||[]))x.toast(note);
        x.render();
      }catch(error){sfx.error();x.toast(error.status?error.message:'Mất kết nối. Việc đã xác nhận vẫn được giữ, thử lại sau một chút nhé.',true);}
    },
  },
  tick(root,x){
    keepBarAboveFooter(root);
    focusStep(root);
    // First task: the pinned bottom button glows too, since the glowing tile may be out of view on a phone.
    if(root.closest('dialog')?.querySelector('.gd-next[data-first]'))root.querySelector('.fk-bar .gd-cta:not([disabled])')?.classList.add('gd-pulse');
    const modal=root.querySelector('.mt-modal');
    if(modal){
      const d=root.closest('dialog'),h=`${d?.querySelector('.sheet-head')?.offsetHeight||0}px`;
      if(d&&d.style.getPropertyValue('--job-head')!==h)d.style.setProperty('--job-head',h);
      if(!modal.contains(document.activeElement))modal.querySelector('button:not([disabled])')?.focus({preventScroll:true});
    }
    root.querySelectorAll('[data-seal-start]').forEach(el=>{
      const start=Number(el.dataset.sealStart);if(!start)return;
      const [loose,lo,hi,burn,max]=el.dataset.s.split(',').map(Number),held=Math.max(0,x.now()-start);
      el.querySelector('.mt-needle').style.left=Math.min(100,held/max*100)+'%';
      const label=el.parentElement.querySelector('.mt-gauge-label');
      if(label)label.textContent=`${held.toFixed(1)} giây · `+(held<loose?'màng chưa dính…':held<lo?'sắp được rồi…':held<=hi?'VÙNG XANH — NHẢ TAY!':held<=burn?'hơi lâu rồi…':'cháy màng mất!');
      el.classList.toggle('ready',held>=lo&&held<=hi);el.classList.toggle('over',held>burn);
    });
  },
  summary(data,x){
    if(!data||data.served==null)return '';
    const row=(l,v)=>`<div class="kv-row"><span>${l}</span><b>${v}</b></div>`;
    const tm=data.tomorrow;
    return `<article class="card space-top mt-sum"><h4 class="section-title">🧋 Quầy trà hôm nay</h4><div class="kv">${row('Ly đã trao',data.served)}${row('Ly chuẩn từng lớp',data.perfect)}${data.returned?row('Ly bị trả lại',data.returned):''}${data.walkouts?row('Khách bỏ về / đơn hủy',data.walkouts):''}${row('Doanh thu quầy',`${data.revenue} xu`)}${data.bonus?row('Thưởng thêm',`${data.bonus} xu`):''}${data.fines?row('Tiền phạt',`${data.fines} xu`):''}${data.dumped?row('Trà & trân châu bỏ cuối ca',`${data.dumped} phần`):''}${data.sealer!=null?row('Máy dán nắp',`${data.sealer} ly từ lần lau trước`):''}${data.orders?row('Đơn hàng đang giao',data.orders):''}${row('Tay nghề',`cấp ${data.level}`)}</div>
      ${tm?`<p class="mt-tomorrow-line"><span aria-hidden="true">${x.esc(tm.emoji)}</span> <b>Mai: ${x.esc(tm.title)}</b><small>${x.esc(tm.advice)}</small></p>`:''}</article>`;
  },
};
