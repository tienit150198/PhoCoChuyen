/** Quầy trà sữa — hands-on boba counter. game/boba.py is the referee: every
 * tap is a command, the server keeps stock, patience, sealing time and grades. */
import {lifeNav} from '../experience-ui.js';
import {Sound} from '../audio.js';

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
const LOUD=new Set(['tea_serve','tea_seal','tea_event','tea_event_ok','tea_discard','tea_check','tea_prepare','tea_cups','tea_wipe','more_work','life_mode','life_goal']);
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
  if(!cup.placed)return `<svg class="mt-cup empty" width="${size}" height="${size*1.2}" viewBox="0 0 120 160" role="img" aria-label="Chưa có ly trên quầy"><path d="M22 34H98L90 150Q90 154 86 154H34Q30 154 30 150Z" fill="none" stroke="currentColor" stroke-width="2.4" stroke-dasharray="6 5" opacity=".45"/><text x="60" y="100" text-anchor="middle" font-size="13" fill="currentColor" opacity=".6">Lấy ly</text></svg>`;
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
    <span class="mt-chip">🕐 <b>${x.esc(b.clock||'08:00')}</b></span>
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
  const w=(b.warnings||[]).filter(v=>v.where==='stock');
  if(w.length)out.push(`<div class="mt-alert warn row-inline"><span>⚠ ${w.map(v=>x.esc(v.text)).join(' · ')}</span>${x.button('🧺 Mở kho','prepare',{},'small')}</div>`);
  return out.join('');
}
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
function notebookFor(t,x){
  const row=(B(x).notebook||[]).find(r=>r.npc===t.npc);
  if(!row?.usual)return `<p class="muted small">Sổ khách quen chưa ghi ly của ${x.esc(t.customer)}. Hỏi lại khách nhé.</p>`;
  const u=row.usual;
  return `<details class="mt-notebook" open><summary>📒 Sổ khách quen: ${x.esc(row.name)}</summary><p>${x.esc(ing(x,u.base).name)} size ${u.size}${u.flavor?`, vị ${x.esc(low(ing(x,u.flavor).name))}`:''}, ${u.toppings.length?x.esc(u.toppings.map(k=>low(ing(x,k).name)).join(', ')):'không topping'}, ${u.sugar}% đường, ${ICE_TEXT[u.ice]}.</p><small>Đã ghé ${row.visits} lần</small></details>`;
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
      ${!t.known?jb(x,'👂 Nghe gọi món','ask',{task:t.id},'primary'):''}
      ${t.known&&t.usual?notebookFor(t,x):''}
      <b class="mt-price">${t.quoted_price!=null?`${t.quoted_price} xu`:''}</b>
    </div></section>`;
}
function tile(x,o){
  const zero=o.count===0&&!o.locked;
  const act=o.locked||o.disabled?'':o.cmd?cmdAttr(x,o.cmd,o.payload):'';
  return `<button type="button" class="mt-tile ${o.cls||''}${o.on?' on':''}${o.locked?' locked':''}${zero?' zero':''}" ${act} ${o.locked||o.disabled?'disabled':''} aria-pressed="${!!o.on}" aria-label="${x.esc(o.label||o.name)}">
    ${o.art||`<span class="mt-emo" aria-hidden="true">${o.emoji}</span>`}<b>${x.esc(o.name)}</b>${o.sub?`<small>${x.esc(o.sub)}</small>`:''}
    ${o.locked?`<small class="mt-lock">🔒 Cấp ${o.level}</small>`:o.count!=null?`<em class="mt-count${o.count===0?' zero':''}" aria-hidden="true">${o.count}</em>`:''}</button>`;
}
function shelf(t,x,group,title){
  const cup=t.cup,items=cup.items||[],b=B(x);
  const ready=t.known&&cup.placed&&!cup.sealed;
  const limit={base:1,flavor:1,topping:3}[group],have=items.filter(k=>ing(x,k).group===group).length;
  const needBase=group!=='base'&&!hasGroup(x,cup,'base');
  const list=ings(x).filter(i=>i.group===group);
  return `<section class="mt-shelf ${group}"><h4>${title}${group==='topping'?` <small>${have}/${limit}</small>`:''}</h4><div class="mt-grid">${list.map(i=>{
    const s=station(x,i.id),inCup=items.includes(i.id);
    if(!s.unlocked)return tile(x,{name:i.name,emoji:i.emoji,locked:true,level:s.level,label:`${i.name}, mở ở cấp ${s.level}`});
    if(s.stock===0&&!inCup)return tile(x,{name:i.name,emoji:i.emoji,count:0,cls:'restock',cmd:'tea_prepare',payload:{item:i.id,qty:5,confirm:true},sub:`+5 · ${i.cost*5} xu`,label:`${i.name} đã hết. Chuẩn bị thêm 5 phần, ${i.cost*5} xu`});
    const disabled=!ready||inCup||have>=limit||needBase;
    return tile(x,{name:i.name,emoji:i.emoji,count:s.stock,on:inCup,disabled,cmd:'tea_add',payload:{task:t.id,item:i.id},label:`${i.name}, còn ${s.stock} phần${inCup?', đã có trong ly':''}`});
  }).join('')}</div></section>`;
}
function cupStack(t,x){
  const b=B(x),cup=t.cup,cups=b.cups||{M:0,L:0};
  return `<section class="mt-shelf cups"><h4>🥤 Chồng ly</h4><div class="mt-grid two">${['M','L'].map(size=>{
    const on=cup.placed&&cup.size===size,locked=(cup.items||[]).length&&!on;
    if(!cups[size])return tile(x,{name:`Ly ${size}`,emoji:'🥤',count:0,cls:'restock',cmd:'tea_cups',payload:{size,confirm:true},sub:`+${b.cup_pack?.qty||20} · ${b.cup_pack?.cost||4} xu`,label:`Hết ly ${size}. Nhập thêm`});
    return tile(x,{name:`Ly ${size}`,emoji:size==='L'?'🥤':'🧋',count:cups[size],on,disabled:!t.known||cup.sealed||locked,cmd:'tea_cup',payload:{task:t.id,size},label:`Ly size ${size}, còn ${cups[size]} ly`});
  }).join('')}</div></section>`;
}
function dials(t,x){
  const cup=t.cup,ok=t.known&&cup.placed&&!cup.sealed,sugars=B(x).sugars||[0,30,50,70,100];
  const seg=(cmd,val,label,on)=>`<button type="button" class="mt-seg ${on?'on':''}" ${ok?cmdAttr(x,cmd,{task:t.id,level:val}):'disabled'} aria-pressed="${on}">${label}</button>`;
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
  const quick=x.state?.settings?.reduceMotion;
  return `<div class="mt-sealer ${start?'running':''}">
    <div class="mt-gauge" data-seal-start="${start||''}" data-s="${[S.loose,S.good_lo,S.good_hi,S.burn,S.max].join(',')}" aria-hidden="true">${zones.map(([k,a,z])=>`<i class="z ${k}" style="left:${pct(a)}%;width:${pct(z-a)}%"></i>`).join('')}<b class="mt-needle" style="left:${Math.min(100,pct(held))}%"></b></div>
    <small class="mt-gauge-label" aria-live="polite">${start?'Đang ép nhiệt…':`Ép nắp rồi nhả tay khi kim vào vùng xanh (${S.good_lo}–${S.good_hi} giây)`}</small>
    <div class="mt-seal-btns">${start?jb(x,'✋ Nhả tay!','tea_seal',{task:t.id},'primary big'):jb(x,'🔥 Ép nắp','tea_seal_start',{task:t.id},quick?'cream':'primary',!ready)}
    ${start?'':jb(x,'Dán thường','tea_seal',{task:t.id},'ghost small',!ready)}</div></div>`;
}
function finish(t,x){
  const cup=t.cup,label=t.app?'🛵 Giao tài xế':'🛎️ Giao món';
  return `<div class="mt-finish">${sealer(t,x)}
    ${jb(x,`${label}${t.quoted_price!=null?` · ${t.quoted_price} xu`:''}`,'tea_serve',{task:t.id,confirm:true},'primary jumbo mt-serve',!cup.sealed)}
    <div class="mt-minor">${x.confirmCmd('🗑️ Đổ ly','tea_discard',{task:t.id},'Đổ ly đang làm? Nguyên liệu đã dùng được ghi hao hụt và tính là một lần làm lại.','ghost small',!(cup.placed||(cup.items||[]).length))}
    ${jb(x,'🔎 So phiếu','tea_check',{task:t.id},'ghost small',!t.known||!(cup.items||[]).length||cup.sealed)}</div>
    <p class="muted small">So phiếu sai sẽ tính một lỗi.</p></div>`;
}
function hint(t,x){
  const lv=B(x).level||1,text=nextStep(t,x,lv<=3);
  return `<p class="mt-hint" aria-live="polite"><span aria-hidden="true">💡</span> ${x.esc(text)}</p>`;
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

/* ---------------------------------------------------------------- prepare */
const TABS=[['stock','🧺','Kho'],['upgrade','🛠️','Nâng cấp'],['price','🏷️','Giá bán'],['reviews','⭐','Đánh giá'],['recap','📒','Tổng kết']];
function board(x){
  const b=B(x),pr=b.prices||{},prices=x.room.life?.prices||{};
  const bases=ings(x).filter(i=>i.group==='base');
  return `<div class="chalkboard mt-board"><h2>🧋 Menu hôm nay</h2><div class="chalk-columns">${bases.map(i=>{const s=station(x,i.id);return `<div class="${s.unlocked?'':'locked'}"><span>${x.esc(i.name)}</span><b>${s.unlocked?`${prices[i.id]||pr.base?.[i.id]||30} xu`:`🔒 cấp ${s.level}`}</b></div>`;}).join('')}</div>
    <p class="center">Siro +${pr.flavor??6} xu · Topping +${pr.topping??5} xu · Size L +${pr.size_l??7} xu</p></div>`;
}
function stockTab(x){
  const b=B(x),pantry=x.room.life?.pantry||[],day=x.room.day,cups=b.cups||{};
  const lot=id=>{const l=pantry.filter(v=>v.item===id&&v.qty>0&&v.expires>=day);return l.length?Math.min(...l.map(v=>v.expires)):null;};
  const cupRows=['M','L'].map(size=>`<div class="mt-row"><span class="mt-emo" aria-hidden="true">🥤</span><div class="grow"><b>Ly ${size}</b><small>Còn ${cups[size]||0} ly</small></div>${jb(x,`+${b.cup_pack?.qty||20} ly · ${b.cup_pack?.cost||4} xu`,'tea_cups',{size,confirm:true},'small')}</div>`).join('');
  const groups=[['base','🫖 Trà nền'],['flavor','🍑 Siro'],['topping','🧋 Topping']];
  return `<h3 class="section-title">🥤 Chồng ly</h3><div class="mt-rows">${cupRows}</div>${groups.map(([g,title])=>`<h3 class="section-title">${title}</h3><div class="mt-rows">${ings(x).filter(i=>i.group===g).map(i=>{
    const s=station(x,i.id),exp=lot(i.id),soon=exp!=null&&exp<=day;
    if(!s.unlocked)return `<div class="mt-row locked"><span class="mt-emo" aria-hidden="true">${i.emoji}</span><div class="grow"><b>${x.esc(i.name)}</b><small>🔒 Mở ở tay nghề cấp ${s.level}</small></div></div>`;
    return `<div class="mt-row ${s.stock===0?'empty':''}"><span class="mt-emo" aria-hidden="true">${i.emoji}</span><div class="grow"><b>${x.esc(i.name)}</b><small><span class="mt-count-inline ${s.stock===0?'zero':''}">Còn ${s.stock}</span>${exp!=null?` · <span class="${soon?'warn':''}">dùng hết ngày ${exp}</span>`:''} · ${i.cost} xu/phần</small></div>${jb(x,`+5 · ${i.cost*5} xu`,'tea_prepare',{item:i.id,qty:5,confirm:true},'small')}</div>`;}).join('')}</div>`).join('')}<p class="muted small">Trân châu, foam và kem cheese chỉ giữ được trong ngày.</p>`;
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
    <h3 class="section-title">📒 Sổ khách quen</h3><div class="mt-rows">${(b.notebook||[]).map(r=>`<div class="mt-row"><span class="mt-emo" aria-hidden="true">📒</span><div class="grow"><b>${x.esc(r.name)}</b><small>${r.usual?`${x.esc(ing(x,r.usual.base).name)} ${r.usual.size} · ${r.usual.sugar}% đường · ${ICE_TEXT[r.usual.ice]}`:'Chưa ghi ly quen'} · ghé ${r.visits} lần</small></div></div>`).join('')}</div>`;
}
function prepare(x,tab){
  const c=x.room,b=B(x),mod=b.modifier||{},w=b.warnings||[];
  tab=TABS.some(v=>v[0]===tab)?tab:'stock';
  const modes=x.content.experiences?.modes||[];
  const panel={stock:stockTab,upgrade:upgradeTab,price:priceTab,reviews:reviewsTab,recap:recapTab}[tab](x);
  const goals=(c.life?.goals||[]).map(g=>`<li class="${g.claimed?'done':''}"><div><strong>${x.esc(g.title)}</strong><small>Thưởng ${g.reward} xu</small></div><div class="prep-goal-end">${g.claimed?'<span class="done-mark">✓ Đã nhận</span>':g.current>=g.goal?jb(x,'Nhận quà','life_goal',{goal:g.id},'small primary'):`<b>${Math.min(g.current,g.goal)}/${g.goal}</b>`}</div></li>`).join('');
  return `<div class="preparation-topline">${x.button('← Hành trình','home',{},'ghost small')}<span>CHUẨN BỊ NGÀY ${c.day}</span>${x.button(x.icon('x',20),'close',{},'ghost small')}</div>
  <div class="life-content career-job mt mt-prep prep-v2">
    <header class="prep-head"><div class="prep-id"><span class="sign-kicker">QUẦY TRÀ SỮA</span><h1>${x.esc(c.life?.shop_name||'Trà Mây & Trân Châu')}</h1></div><div class="prep-level"><div class="prep-level-row"><span>⭐ Tay nghề cấp ${b.level||1}</span><small>${b.total||0} ly đã pha</small></div><div class="prep-xp" aria-hidden="true"><i style="width:${b.next_tier?Math.min(100,(b.total||0)/b.next_tier*100):100}%"></i></div></div>${x.button('✏️ Đổi tên','expRename',{},'small ghost')}</header>
    <section class="prep-block prep-today" aria-label="Hôm nay"><h2 class="prep-h">Hôm nay</h2><div class="prep-today-grid"><div class="prep-weather"><span class="prep-weather-em" aria-hidden="true">${x.esc(mod.emoji||'🌤️')}</span><div><strong>${x.esc(mod.title||'')}</strong><p>${x.esc(mod.text||'')}</p></div></div>${goals?`<div class="prep-quests"><h3 class="prep-sub">🌞 Nhiệm vụ hôm nay</h3><ul class="prep-goals">${goals}</ul></div>`:''}</div></section>
    ${w.length?`<div class="mt-warns">${w.map(v=>`<button type="button" class="btn mt-warn" data-action="car:prep" data-tab="${v.where==='stock'?'stock':'stock'}">⚠ ${x.esc(v.text)}</button>`).join('')}</div>`:''}
    <nav class="mt-tabs" role="tablist" aria-label="Chuẩn bị quầy">${TABS.map(([id,e,l])=>`<button type="button" role="tab" class="mt-tab ${tab===id?'on':''}" data-action="car:prep" data-tab="${id}" aria-selected="${tab===id}"><span aria-hidden="true">${e}</span> ${l}</button>`).join('')}</nav>
    <section class="mt-panel" role="tabpanel">${panel}</section>
  </div>
  <footer class="life-sticky">${x.button(c.open?'Về quầy · pha tiếp':`Mở cửa ngày ${c.day}`,c.open?'workbench':'start',{},'primary jumbo')}</footer>`;
}

/* ---------------------------------------------------------------- module */
export default {
  id:'milk_tea',
  css:true,
  autoNext:true,
  next(t,x){return nextStep(t,x,(B(x).level||1)<=3);},
  clock(c){return c.data?.boba?.clock||'';},
  job(t,x){
    const layout=`<div class="mt-bench"><div class="mt-side"><section class="mt-preview">${cupArt(x,t.cup)}<div class="mt-said"><p class="mt-status">${x.esc(status(x,t.cup))}</p>${x.ui.flash?`<p class="mt-flash" role="status">${x.esc(x.ui.flash)}</p>`:''}</div></section>${finish(t,x)}</div>
      <div class="mt-stations">${cupStack(t,x)}${shelf(t,x,'base','🫖 Trà nền')}${shelf(t,x,'flavor','🍑 Siro')}${shelf(t,x,'topping','🧋 Topping')}${dials(t,x)}</div></div>`;
    return `<div class="career-job mt">${hud(x)}${hint(t,x)}${eventCard(x)}${alerts(x)}${appRow(t,x)}${queueRow(t,x)}${customer(t,x)}${tabs(t,x)}${t.known?layout:''}
      <div class="mt-tools">${x.button('🧺 Kho & nâng cấp','prepare',{},'ghost small')}${x.button('⭐ Đánh giá','feedback',{},'ghost small')}</div></div>`;
  },
  idle(x){
    const b=B(x),waiting=x.room.tasks.filter(open),left=b.left||0;
    const next=waiting.length?x.button(`👋 Mời ${x.esc(waiting[0].customer||'khách')} lên quầy`,'job',{task:waiting[0].id},'primary'):left?jb(x,'🔔 Mời khách tiếp theo','more_work',{},'primary'):x.button('🌙 Khép ca hôm nay','end',{},'primary');
    const tip=waiting.length||left?'':'<p class="mt-hint">💡 Hết khách hôm nay rồi.</p>';
    return `<div class="career-job mt">${hud(x)}${eventCard(x)}${alerts(x)}${tip}<div class="row wrap">${next}${x.button('🧺 Kho & nâng cấp','prepare',{},'ghost')}</div></div>`;
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
    return `<article class="card space-top mt-sum"><h4 class="section-title">🧋 Quầy trà hôm nay</h4><div class="kv">${row('Ly đã trao',data.served)}${row('Ly chuẩn từng lớp',data.perfect)}${data.returned?row('Ly bị trả lại',data.returned):''}${data.walkouts?row('Khách bỏ về / đơn hủy',data.walkouts):''}${row('Doanh thu quầy',`${data.revenue} xu`)}${data.bonus?row('Thưởng thêm',`${data.bonus} xu`):''}${data.fines?row('Tiền phạt',`${data.fines} xu`):''}${row('Tay nghề',`cấp ${data.level}`)}</div></article>`;
  },
};
