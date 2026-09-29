/** Tiệm Sửa Đồ Chú Tư — repair bench (plugin career UI).
 * Server decides every result (readings, quote reply, final test, used-part luck, money).
 * Local state here is only what the player is ticking before sending, and which step tab is open.
 * Phone first: one step panel at a time, one primary button per panel. */
import {reqList,fold} from '../ui-kit.js';
const STEPS=['Nhận máy','Đo kiểm','Báo giá','Sửa','Bàn giao'];
const MODE={live:'cấp điện',open:'mở máy',any:'đo ngoài'};

const items=x=>x.content.inventory?.items?.repair||[];
const itemOf=(x,id)=>items(x).find(i=>i.id===id)||{id,name:id,emoji:'•',price:0};
const devOf=(x,t)=>x.cc.devices?.[t.needs.device]||{name:'Máy',emoji:'🔧',safety:[],marks:[],accessories:[],labor:0};
const faultOf=(x,dev,id)=>[...(x.cc.faults?.[dev]||[]),...(x.cc.extras?.[dev]||[])].find(f=>f.id===id)||{id,name:id,parts:{none:null},supplies:[],mult:1};
const local=(x,t)=>{x.ui.rp??={};return x.ui.rp[t.id]??={marks:[],acc:[],consent:false,grades:{},tab:null};};
const attrs=(x,obj)=>Object.entries(obj).map(([k,v])=>`data-${k}="${x.esc(v)}"`).join(' ');
const cmdAttr=(x,command,payload)=>`data-command="${command}" data-payload="${x.esc(JSON.stringify(payload))}"`;
const carAttr=(x,action,data)=>`data-action="car:${action}" ${attrs(x,data)}`;
const dataDevice=(x,t)=>(x.cc.data_devices||['phone']).includes(t.needs.device);
const sameSet=(a=[],b=[])=>a.length===b.length&&a.every(v=>b.includes(v));
function tile(x,{emoji,label,sub,cls='',attr='',off=false}){
  return `<button type="button" class="tile ${cls}" ${attr} ${off?'disabled':''}><span class="tile-emoji" aria-hidden="true">${x.esc(emoji)}</span><b>${x.esc(label)}</b>${sub!=null&&sub!==''?`<small>${x.esc(sub)}</small>`:''}</button>`;
}
const locked=(x,id)=>!!id&&(x.room.inventory?.locked||[]).includes(id);
function labor(x,t,fault){const dev=t.needs.device,base=x.room.life?.prices?.[dev]??devOf(x,t).labor;return Math.round(base*fault.mult);}
function line(x,t,fault,grade){const item=fault.parts[grade];const part=item?(itemOf(x,item).price||0):0;const l=labor(x,t,fault);return {labor:l,part,price:l+part,item};}
function defaultGrade(x,t,fault){const keys=Object.keys(fault.parts).filter(g=>!locked(x,fault.parts[g]));const pref=['compatible','standard','none','genuine','used'];
  if(t.needs.genuine_only)return keys.find(g=>g==='genuine')||keys.find(g=>g!=='compatible'&&g!=='used')||keys[0];
  return pref.find(g=>keys.includes(g))||keys[0]||Object.keys(fault.parts)[0];}
function gradeFor(x,t,f){const u=local(x,t),fault=faultOf(x,t.needs.device,f);const g=u.grades[f];return g&&g in fault.parts?g:defaultGrade(x,t,fault);}
function stage(t){const b=t.bench,open=t.open_scope||[];if(!b.intake)return 0;if(b.final==='pass')return 4;if(!b.diagnosis&&!open.length)return 1;if(open.some(f=>!b.approved[f]))return 2;if(open.length||b.opened)return 3;return 4;}
const caseOf=t=>t.needs?.case||null;
const rushLeft=(t,x)=>t.due_turn==null?null:t.due_turn-(x.room.turn||0);
/* care loop: the server computes every waiting word (clock, arrivals, promises) */
const care=x=>x.room.data?.care||{tasks:{},shelf:[],sources:{},shelf_max:2};
const tview=(x,t)=>care(x).tasks?.[t.id]||{orders:{}};
const who=(x,id)=>x.npc(id)?.display_name||'Khách';
const openTasks=x=>(x.room.tasks||[]).filter(t=>!['completed','referred','cancelled'].includes(t.status));
const shelved=x=>openTasks(x).filter(t=>t.bench?.shelf);
const lowerFirst=s=>s?s[0].toLowerCase()+s.slice(1):'';
const pct=n=>`${Number(n)||0}%`;

/* ---------- shared bits ---------- */
function todayChip(x){const d=x.room.data?.today,k=care(x);if(!d)return '';
  const clock=k.clock&&k.open?`<span class="rp-clock" title="Giờ ở tiệm">🕙 ${x.esc(k.clock)}</span>`:'';
  return `<p class="rp-today" title="${x.esc(d.text)}">${clock}<span class="rp-today-title"><span aria-hidden="true">${x.esc(d.emoji)}</span> <b>Hôm nay: ${x.esc(d.title)}</b></span> <small>${x.esc(d.text)}</small></p>`;}

/* ---------- care: calls, comebacks, shelf, tools, regulars ---------- */
function callCard(x,t){
  const v=tview(x,t),sh=t.bench.shelf,dev=devOf(x,t);
  const truth=v.eta?`Nói thật: đồ về ${v.eta}`:'Nói thật: đang làm';
  const risky=v.eta_days>0;
  return `<div class="rp-call" role="status"><p><span aria-hidden="true">📞</span> <b>${x.esc(who(x,t.npc))}</b> gọi: “${x.esc(dev.name)} ${x.esc(sh.tag)} xong chưa?” <small>Đang hẹn: ${x.esc(v.promise||'')}</small></p>
    <div class="rp-btns">${x.cmd(`🗣️ ${x.esc(truth)}`,'rp_answer',{task:t.id,reply:'truth'},'small primary')}${x.cmd(`🙂 Trấn an: “chiều nay xong”${risky?' ⚠️':''}`,'rp_answer',{task:t.id,reply:'soothe'},'small ghost')}</div>
    ${risky?'<p class="small muted">Đồ chưa về hôm nay — hứa “chiều nay” là hứa lèo.</p>':''}</div>`;
}
function backCard(x,r){
  const ago=Math.max(0,(x.room.day||0)-r.handed),money=x.room.money??0;
  return `<div class="rp-back ${r.covered?'':'expired'}" role="status"><p><span aria-hidden="true">📒</span> <b>${x.esc(r.who)}</b> mang “${x.esc(r.title)}” quay lại: “${x.esc(r.left)}”</p>
    <p class="small">Tiệm soi lại: ${x.esc(r.cause_text)}. Phiếu ${r.days?`${r.days} ngày`:'không bảo hành'}, giao ${ago} ngày trước — ${r.covered?'<b>còn hạn bảo hành</b>':'<b>đã hết hạn</b>'}.</p>
    <div class="rp-btns">${x.confirmCmd(`🛡️ Sửa lại miễn phí (tiệm chịu ${x.esc(x.money(r.cost))})`,'rp_back',{id:r.id,choice:'redo'},`Sửa lại miễn phí, tiệm chịu ${r.cost} xu linh kiện?`,'small primary',money<r.cost)}${x.confirmCmd(`🧾 Tính tiền ${x.esc(x.money(r.price))}`,'rp_back',{id:r.id,choice:'charge'},r.covered?'Phiếu còn hạn bảo hành mà vẫn tính tiền? Khách sẽ rất bực.':`Hết hạn bảo hành: báo giá sửa lại ${r.price} xu?`,'small ghost')}</div></div>`;
}
function alerts(x,compact=false){
  const callers=shelved(x).filter(t=>tview(x,t).call),backs=x.room.data?.comebacks||[];
  const cards=backs.map(r=>backCard(x,r)).join('')+callers.map(t=>callCard(x,t)).join('');
  if(!cards)return '';
  if(compact&&callers.length+backs.length>1){
    const sum=[backs.length?`📒 ${backs.length} máy quay lại bảo hành`:'',callers.length?`📞 ${callers.length} khách gọi hỏi`:''].filter(Boolean).join(' · ');
    return `<section class="rp-alerts rp-alerts-fold" aria-label="Khách đang chờ trả lời">${fold(`<b>${x.esc(sum)}</b> — trả lời`,`<div class="rp-alerts">${cards}</div>`)}</section>`;
  }
  return `<section class="rp-alerts" aria-label="Khách đang chờ trả lời">${cards}</section>`;
}
function orderRows(x,t){
  return Object.entries(tview(x,t).orders||{}).filter(([,o])=>!o.used).map(([,o])=>{const it=itemOf(x,o.item),src=x.cc.sources?.[o.src]||{emoji:'📦'};
    return {ok:o.arrived?true:null,icon:src.emoji,label:it.name,note:o.arrived?'đã về, lắp được rồi':`đặt riêng · về ${o.when}`};});
}
function shelfRows(x,t){
  const b=t.bench,open=t.open_scope||[],fixed=Object.keys(b.fixed||{}).length>0,v=tview(x,t);
  const quoted=open.length?(open.every(f=>b.approved[f])?true:b.quote?.status==='declined'?false:null):fixed?true:null;
  return [
    {ok:b.diagnosis||open.length||fixed?true:null,icon:'🔎',label:'Chốt lỗi'},
    {ok:quoted,icon:'📨',label:'Khách duyệt báo giá'},
    ...orderRows(x,t),
    {ok:b.final==='pass'?true:b.final==='fail'?false:null,icon:'▶️',label:'Sửa xong, chạy thử đạt'},
    {ok:null,icon:'🤝',label:'Gọi khách tới lấy',note:`hẹn ${v.promise||''}`,tone:v.due<0?'danger':v.due===0?'warn':''},
  ];
}
function promiseTone(v){return v.due<0?'danger':v.due===0?'amber':'green';}
function shelfCard(x,t){
  const sh=t.bench.shelf,v=tview(x,t),dev=devOf(x,t);
  return `<article class="rp-shelfcard"><div class="rp-shelfhead"><span class="rp-tagchip">🏷️ ${x.esc(sh.tag)}</span><span class="rp-dev" aria-hidden="true">${x.esc(dev.emoji)}</span><div class="grow"><b>${x.esc(dev.name)}</b><small>${x.esc(who(x,t.npc))}${sh.auto?' · ở lại qua đêm':''}</small></div><span class="tag ${promiseTone(v)}">${v.due<0?'⚠️ ':''}hẹn ${x.esc(v.promise||'')}</span></div>
    ${reqList(shelfRows(x,t),x.esc,'Tiến độ máy '+sh.tag)}<div class="rp-btns">${x.button('🔧 Làm tiếp máy này','job',{task:t.id},'small primary')}</div></article>`;
}
function shelfPanel(x,skip){
  const rows=shelved(x).filter(t=>t.id!==skip),k=care(x);if(!rows.length)return '';
  const ready=rows.filter(t=>orderRows(x,t).some(r=>r.ok)||t.bench.final==='pass').length;
  const late=rows.filter(t=>tview(x,t).due<0).length;
  return `<section class="rp-shelf-panel"><h4 class="section-title">🗄️ Kệ máy chờ <small class="muted">${rows.length} máy${ready?` · ${ready} làm được ngay`:''}${late?` · <b class="rp-late">${late} trễ hẹn</b>`:''}</small></h4><div class="rp-shelfgrid">${rows.map(t=>shelfCard(x,t)).join('')}</div><p class="small muted">Tối đa ${k.shelf_max||2} máy hẹn khách; tới giờ đóng cửa, máy nào còn ở tiệm sẽ ở lại qua đêm.</p></section>`;
}
function shelfFold(x,skip){
  const rows=shelved(x).filter(t=>t.id!==skip);if(!rows.length)return '';
  const late=rows.filter(t=>tview(x,t).due<0).length;
  const sum=`🗄️ Kệ máy chờ: ${rows.map(t=>`${x.esc(t.bench.shelf.tag)} ${x.esc(devOf(x,t).emoji)}`).join(' · ')}${late?` · ⚠️ ${late} trễ hẹn`:''}`;
  return fold(sum,`<div class="rp-shelfgrid">${rows.map(t=>shelfCard(x,t)).join('')}</div>`);
}
function shelfBanner(t,x){
  const sh=t.bench.shelf,v=tview(x,t),others=openTasks(x).some(o=>o.id!==t.id&&!o.deferred);
  const parts=orderRows(x,t).map(r=>`${r.icon} ${r.label}: ${r.value}`).join(' · ');
  const next=others?x.button('➡️ Sang khách đang chờ','nextJob',{},'small ghost'):x.cmd('➕ Đón khách mới','more_work',{},'small ghost',openTasks(x).length>=4);
  return `<div class="rp-banner ${promiseTone(v)}" role="status"><p><b>🏷️ ${x.esc(sh.tag)} · máy đang nằm trên kệ</b> — hẹn ${x.esc(who(x,t.npc))} <b>${x.esc(v.promise||'')}</b>${sh.moved?' (đã báo dời hẹn)':''}${parts?`<br><small>${x.esc(parts)}</small>`:''}</p><div class="rp-btns">${next}</div></div>`;
}
function promiseFold(t,x){
  const b=t.bench,k=care(x),v=tview(x,t),full=shelved(x).length>=(k.shelf_max||2);
  if(b.shelf||!b.intake||b.returned||caseOf(t)==='buyin')return '';
  const words=['Hôm nay','Mai','Ngày kia','3 ngày nữa'];
  const btns=(x.cc.promise_days||[0,1,2,3]).map(d=>{const early=d<(v.eta_days||0);
    return x.confirmCmd(`${early?'⚠️ ':''}${words[d]||d+' ngày'}`,'rp_shelf',{task:t.id,days:d},`Hẹn ${who(x,t.npc)} ${lowerFirst(words[d]||'')} tới lấy máy?${early?' Đồ chưa về kịp ngày đó — dễ trễ hẹn.':''}`,early?'small ghost':'small',full);}).join('');
  const eta=v.eta?`Đồ về ${v.eta} → hẹn sớm nhất: ${lowerFirst(words[v.eta_days]||v.eta_days+' ngày nữa')}.`:'Đồ đã đủ: hẹn hôm nay cũng được.';
  return fold('🗄️ Hẹn khách, để máy lại tiệm',`<p class="small">${x.esc(eta)} Khách về nhà chờ, không mất kiên nhẫn ở quầy; mỗi sáng khách sẽ gọi hỏi.</p><div class="rp-btns">${btns}</div>${full?`<p class="small muted">Kệ đã đủ ${k.shelf_max||2} máy hẹn — làm xong bớt một máy trước.</p>`:''}`);
}
function toolRows(x){
  const tl=x.room.data?.tools||{tip:100,meter:100},info=x.cc.tools||{};
  return Object.entries(info).map(([k,v])=>({ok:tl[k]>=v.low?true:false,icon:v.emoji,label:v.name,note:tl[k]<v.low?v.effect:'',value:pct(tl[k]),tone:tl[k]<v.low?'warn':''}));
}
function toolButtons(x,only){
  const tl=x.room.data?.tools||{tip:100,meter:100},cost=x.cc.tool_costs||{tip:4,meter:2},cl=x.cc.tip_clean||{max:80},money=x.room.money??0;
  const tip=`${x.cmd('🧽 Lau mũi hàn','rp_tool',{tool:'tip',how:'clean'},'small',tl.tip>=cl.max||!x.stock('solder'))}${x.confirmCmd(`🔥 Mũi mới · ${x.esc(x.money(cost.tip))}`,'rp_tool',{tool:'tip',how:'replace'},`Thay mũi hàn mới (${cost.tip} xu)?`,'small ghost',tl.tip>=100||money<cost.tip)}`;
  const meter=x.confirmCmd(`📟 Pin 9V mới · ${x.esc(x.money(cost.meter))}`,'rp_tool',{tool:'meter',how:'battery'},`Thay pin 9V cho đồng hồ đo (${cost.meter} xu)?`,only==='meter'?'small primary':'small ghost',tl.meter>=100||money<cost.meter);
  return `<div class="rp-btns">${only==='meter'?'':tip}${only==='tip'?'':meter}</div>`;
}
function toolsFold(x,open=false){
  const low=toolRows(x).filter(r=>r.ok===false).length;
  return fold(`🧰 Dụng cụ${low?` · ⚠️ ${low} món cần chăm`:' · ổn'}`,`${reqList(toolRows(x),x.esc,'Dụng cụ trên bàn thợ')}${toolButtons(x)}<p class="small muted">Lau mũi hàn tốn 1 đoạn thiếc, sáng lại tới ${(x.cc.tip_clean||{max:80}).max}%.</p>`,open||low>0);
}
function toolWarn(x,tool){
  const tl=x.room.data?.tools||{},v=x.cc.tools?.[tool];if(!v||(tl[tool]??100)>=v.low)return '';
  return `<div class="rp-toolwarn" role="status"><p class="small"><b>${x.esc(v.emoji)} ${x.esc(v.name)} còn ${pct(tl[tool])}.</b> ${x.esc(v.effect)}</p>${toolButtons(x,tool)}</div>`;
}
function regularCard(t,x){
  const rec=x.room.data?.regulars?.[t.npc];if(!rec||!rec.visits)return '';
  const names=x.cc.trust_names||[],name=names[rec.trust]||'',hearts='♥'.repeat(rec.trust)+'♡'.repeat(Math.max(0,5-rec.trust));
  const same=(rec.history||[]).filter(h=>h.device===t.needs.device).slice(-1)[0];
  const last=same?`<p class="small"><b>Lần trước (ngày ${same.day}):</b> ${x.esc(faultOf(x,same.device,same.fault).name)} · ${x.esc(x.cc.grades?.[same.grade]?.short||same.grade)} · ${same.days?`BH ${same.days} ngày`:'không BH'}</p>`:'';
  const habit=x.cc.habits?.[t.npc];
  const stretch=rec.trust>=(x.cc.trust_stretch||3)?'<p class="small">💛 Tin tiệm: báo giá hơi quá ngân sách (tới 10%) khách vẫn gật.</p>':'';
  return fold(`💛 Khách quen · ${x.esc(name)} <span class="rp-hearts" aria-label="tin cậy ${rec.trust}/5">${hearts}</span> · ${rec.visits} lần`,
    `${last}${habit?`<p class="small"><b>Thói quen:</b> ${x.esc(habit)}</p>`:''}${stretch}${rec.ontime||rec.late?`<p class="small muted">Đúng hẹn ${rec.ontime||0} · trễ hẹn ${rec.late||0}</p>`:''}`);
}
function regularsBook(x){
  const regs=Object.entries(x.room.data?.regulars||{});if(!regs.length)return '';
  const names=x.cc.trust_names||[];
  const rows=regs.sort((a,b)=>b[1].trust-a[1].trust||b[1].visits-a[1].visits).map(([id,r])=>`<li><div class="grow"><b>${x.esc(who(x,id))}</b><small>${x.esc(names[r.trust]||'')} · ${r.visits} lần${r.ontime?` · đúng hẹn ${r.ontime}`:''}${r.late?` · trễ hẹn ${r.late}`:''}</small></div><span class="rp-hearts" aria-label="tin cậy ${r.trust}/5">${'♥'.repeat(r.trust)}${'♡'.repeat(Math.max(0,5-r.trust))}</span></li>`).join('');
  return fold(`💛 Sổ khách quen (${regs.length})`,`<ul class="rp-regs">${rows}</ul><p class="small muted">Sửa sạch, trả đúng hẹn thì khách tin thêm; khách tin thì chờ bình tĩnh hơn, và từ “${x.esc(names[x.cc.trust_stretch||3]||'')}” chịu báo giá quá ngân sách tới 10%.</p>`);
}

function deskCard(x){
  const ev=x.room.data?.desk?.ev;if(!ev)return '';
  const who=x.npc(ev.npc);
  const opts=ev.options.map((o,i)=>`<button type="button" class="btn ${i===0?'primary':'ghost'} rp-opt" ${cmdAttr(x,'rp_desk',{option:o.id})} ${o.cost>x.room.money?'disabled':''}><b>${x.esc(o.label)}</b>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}</button>`).join('');
  return `<section class="rp-desk ${x.esc(ev.tone)}" role="alert" aria-live="assertive"><div class="rp-desk-head"><span class="rp-desk-emoji" aria-hidden="true">${x.esc(ev.emoji)}</span><div><small>CHUYỆN Ở QUẦY</small><h3>${x.esc(ev.title)}</h3></div>${x.portrait(who,40)}</div>
    <p>${x.esc(ev.text)}</p><div class="rp-opts">${opts}</div><p class="small-note">Quyết xong chuyện này rồi làm tiếp máy trên bàn nhé.</p></section>`;
}
function lastDesk(x){const l=x.room.data?.desk?.last;if(!l||l.day!==x.room.day)return '';return `<p class="rp-last ${l.good===true?'good':l.good===false?'bad':''}" aria-live="polite"><span aria-hidden="true">${x.esc(l.emoji)}</span> <b>${x.esc(l.title)}:</b> ${x.esc(l.outcome)}</p>`;}

function ticket(t,x){
  const who=x.npc(t.npc),n=t.needs,dev=devOf(x,t),cs=caseOf(t),cinfo=cs?x.cc.cases?.[cs]:null,left=rushLeft(t,x);
  const tags=[`<span class="tag blue">${x.esc(dev.emoji)} ${x.esc(dev.name)}</span>`];
  if(cs!=='buyin')tags.push(`<span class="tag amber">💰 tối đa ${x.esc(x.money(n.budget))}</span>`);
  if(n.genuine_only)tags.push('<span class="tag">🏷️ chỉ hàng chính hãng</span>');
  if(cinfo)tags.push(`<span class="tag rp-case">${x.esc(cinfo.emoji)} ${x.esc(cinfo.label)}</span>`);
  if(left!=null)tags.push(`<span class="tag ${left>=0?(left<=4?'danger':'green'):'danger'} rp-rush">⏱️ ${left>=0?`còn ${left} nhịp · +${x.esc(x.money(n.rush.bonus))}`:'đã trễ hẹn gấp'}</span>`);
  return `<article class="card rp-ticket"><div class="row">${x.portrait(who,44)}<div class="grow">
    <div class="row spread wrap"><h3>${x.esc(who.display_name)}</h3><div class="patience" title="Kiên nhẫn"><div class="bar ${t.patience<50?'low':''}"><i style="width:${Number(t.patience)||0}%"></i></div><small>${Number(t.patience)||0}%</small></div></div>
    <p class="rp-symptom">“${x.esc(n.symptom)}”</p><div class="row wrap rp-tags">${tags.join('')}</div>
    <details class="rp-note"><summary>Lời dặn của khách</summary><p class="small">${x.esc(n.note)}</p>${n.request?`<p class="small"><b>Khách nhờ thêm:</b> “${x.esc(n.request)}”</p>`:''}${n.claim?`<p class="small"><b>Phiếu:</b> ${x.esc(n.claim.said)}</p>`:''}</details>
    ${regularCard(t,x)}
  </div></div></article>`;
}

function steps(t,x,at,tab){return `<nav class="rp-steps" aria-label="Quy trình sửa">${STEPS.map((s,i)=>`<button type="button" class="${i<at?'done':''} ${i===at?'now':''} ${i===tab?'open':''}" ${carAttr(x,'tab',{task:t.id,tab:i})} aria-current="${i===tab?'step':'false'}" ${i>at&&i!==0?'disabled':''}><span>${i<at?'✓':i+1}</span>${x.esc(s)}</button>`).join('')}</nav>`;}

function device(t,x){
  const b=t.bench,dev=devOf(x,t),n=t.needs;
  const marks=(n.marks||[]).map((m,i)=>`<span class="rp-mark m${i}" title="${x.esc(x.cc.marks[m]?.label||m)}">${x.esc(x.cc.marks[m]?.emoji||'•')}</span>`).join('');
  const installed=Object.entries(b.fixed||{}).map(([f,g])=>{const fd=faultOf(x,n.device,f),it=fd.parts[g]?itemOf(x,fd.parts[g]):null;return `<span class="tag green">${x.esc(it?it.emoji:'🧽')} ${x.esc(fd.name)}</span>`;}).join('');
  const safe=(b.safe||[]).length>=dev.safety.length;
  const stamp=b.final==='pass'?'<b class="rp-stamp ok">ĐẠT</b>':b.final==='fail'?'<b class="rp-stamp bad">CHƯA ĐẠT</b>':'';
  return `<div class="rp-device ${b.opened?'opened':''}" aria-label="${x.esc(dev.name)} trên bàn thợ"><div class="rp-mat"><span class="rp-big" aria-hidden="true">${x.esc(dev.emoji)}</span>${marks}${stamp}</div>
    <div class="row wrap rp-state"><span class="tag ${b.opened?'amber':''}">${b.opened?'🔓 đang mở':'🔒 đang đóng'}</span><span class="tag ${safe?'green':''}">${safe?'🔌✖ đã an toàn':'⚡ còn điện'}</span></div>
    ${installed?`<div class="row wrap">${installed}</div>`:''}</div>`;
}

/* ---------- 0 · intake ---------- */
function intakeView(t,x){
  const b=t.bench,n=t.needs,dev=devOf(x,t),u=local(x,t),dd=dataDevice(x,t);
  if(b.intake){
    const mk=b.intake.marks.map(m=>x.cc.marks[m]?.emoji+' '+x.cc.marks[m]?.label).join(', ')||'không có vết';
    const ac=b.intake.accessories.map(a=>x.cc.accessories[a]?.emoji+' '+x.cc.accessories[a]?.label).join(', ')||'không kèm gì';
    return `<dl class="kv rp-kv"><dt>Tình trạng</dt><dd>${x.esc(mk)}</dd><dt>Phụ kiện</dt><dd>${x.esc(ac)}</dd>${dd?`<dt>Dữ liệu</dt><dd>${b.data_ok?'<span class="tag green">🔓 Khách cho mở khóa kiểm tra</span>':'<span class="tag danger">🔒 Không cho xem dữ liệu</span>'}</dd>`:''}</dl>`;
  }
  const markTiles=dev.marks.map(m=>{const v=x.cc.marks[m]||{emoji:'•',label:m},on=u.marks.includes(m);return tile(x,{emoji:v.emoji,label:v.label,sub:on?'đã ghi':'',cls:on?'selected':'',attr:carAttr(x,'mark',{task:t.id,id:m})+` aria-pressed="${on}"`});}).join('');
  const accTiles=dev.accessories.map(a=>{const v=x.cc.accessories[a]||{emoji:'•',label:a},on=u.acc.includes(a);return tile(x,{emoji:v.emoji,label:v.label,sub:on?'đã nhận':'',cls:on?'selected':'',attr:carAttr(x,'acc',{task:t.id,id:a})+` aria-pressed="${on}"`});}).join('');
  return `<p class="small muted">Nhìn máy trên thảm, chạm đúng những vết thật sự thấy.</p>
    <div class="tile-grid rp-grid">${markTiles}</div>
    <p class="small muted space-top">Khách đưa kèm những gì?</p>
    <div class="tile-grid rp-grid">${accTiles}</div>
    ${dd?`<button type="button" class="btn rp-consent ${u.consent?'on':''}" ${carAttr(x,'consent',{task:t.id})} aria-pressed="${u.consent}">${u.consent?'☑️':'⬜'} Đã hỏi khách có cho mở khóa / xem dữ liệu không</button>`:''}
    <div class="rp-cta"><button type="button" class="btn primary" ${carAttr(x,'intake',{task:t.id})} ${dd&&!u.consent?'disabled':''}>📝 Ghi phiếu nhận máy</button></div>
    ${dd&&!u.consent?'<p class="small muted">Máy có dữ liệu riêng: hỏi khách về mở khóa / xem dữ liệu rồi mới ghi phiếu.</p>':''}`;
}

/* ---------- shell (safety + open/close) ---------- */
function shellBar(t,x,primary){
  const b=t.bench,dev=devOf(x,t),done=b.safe||[],allSafe=done.length>=dev.safety.length;
  const next=dev.safety.find(s=>!done.includes(s));
  const chips=dev.safety.map(s=>{const v=x.cc.safety[s]||{emoji:'•',label:s},ok=done.includes(s);
    return `<button type="button" class="btn small ${ok?'rp-ok':primary&&s===next&&!b.opened?'primary':'ghost'}" ${cmdAttr(x,'rp_safety',{task:t.id,step:s})} ${ok||b.opened?'disabled':''}>${ok?'✅':x.esc(v.emoji)} ${x.esc(v.label)}</button>`;}).join('');
  const open=b.opened?x.cmd(`🔩 ${x.esc(dev.close)}`,'rp_close',{task:t.id},'ghost small'):allSafe?x.cmd(`🔧 ${x.esc(dev.open)}`,'rp_open',{task:t.id},primary?'primary small':'small',b.final==='pass')
    :x.confirmCmd(`🔧 ${x.esc(dev.open)}`,'rp_open',{task:t.id},'Chưa làm đủ bước an toàn! Mở máy lúc này có thể bị giật, bỏng hoặc chập. Vẫn mở?','danger small',b.final==='pass');
  return `<div class="rp-shell"><span class="rp-shell-label">Vỏ máy</span><div class="row wrap">${b.opened?'':chips}${open}</div></div>`;
}

/* ---------- 1 · tests ---------- */
function testsView(t,x){
  const b=t.bench,dev=t.needs.device,tests=x.cc.tests?.[dev]||[];
  const tiles=tests.map(ts=>{const done=b.tests.some(r=>r.id===ts.id);let why='';
    if(done)why='đã đo';else if(ts.mode==='live'&&b.opened)why='đang mở máy';else if(ts.mode==='open'&&!b.opened)why='cần mở máy';else if(ts.consent&&!b.data_ok)why='🔒 khách không cho';
    return tile(x,{emoji:ts.emoji,label:ts.name,sub:why||MODE[ts.mode]+(ts.consent?' · cần đồng ý':''),cls:done?'selected':why?'locked':'',attr:cmdAttr(x,'rp_test',{task:t.id,test:ts.id}),off:!!why});}).join('');
  const log=b.tests.length?`<ol class="rp-readings" aria-live="polite">${b.tests.map(r=>{const ts=tests.find(v=>v.id===r.id)||{name:r.id,emoji:'•'};return `<li><span aria-hidden="true">${x.esc(ts.emoji)}</span><div><b>${x.esc(ts.name)}</b><small>${x.esc(r.reading)}</small></div></li>`;}).join('')}</ol>`:'<p class="muted small">Mỗi phép đo tốn một nhịp — chọn phép đo loại được nhiều giả thuyết nhất.</p>';
  const hyp=(t.needs.hypotheses||[]).map(f=>{const fd=faultOf(x,dev,f),out=b.ruled_out.includes(f),chosen=b.diagnosis===f,fixed=f in b.fixed;
    return `<li class="rp-hyp ${out?'out':''} ${chosen?'chosen':''}"><div class="grow"><b>${x.esc(fd.name)}</b><small>${fixed?'✓ đã xử lý':chosen?'📌 đang chốt':out?'✗ số đo đã loại':'? còn khả nghi'}</small></div>
      ${chosen||fixed||b.final==='pass'?'':x.cmd('Chốt','rp_diagnose',{task:t.id,fault:f},out?'ghost small':'small')}</li>`;}).join('');
  const found=(b.found||[]).map(f=>`<li class="rp-hyp found"><div class="grow"><b>🔎 ${x.esc(faultOf(x,dev,f).name)}</b><small>${f in b.fixed?'✓ đã xử lý':'phát hiện khi mở máy — cần báo giá thêm'}</small></div></li>`).join('');
  return `${toolWarn(x,'meter')}${shellBar(t,x,false)}<div class="tile-grid rp-grid space-top">${tiles}</div>${log}<h5 class="rp-sub">Bảng giả thuyết</h5><ul class="rp-hyps">${hyp}${found}</ul>`;
}

/* ---------- 2 · quote (+ warranty book, water evidence) ---------- */
function claimPanel(t,x){
  const b=t.bench,dev=t.needs.device;
  if(!b.book)return `<div class="rp-claim"><p class="small">Khách mang phiếu <b>${x.esc(t.needs.claim.slip)}</b>. Tra sổ trước khi hứa hẹn gì.</p>${x.cmd('📒 Tra sổ bảo hành','rp_book',{task:t.id},'primary')}</div>`;
  const bk=b.book,marks=bk.marks.map(m=>x.cc.marks[m]?.emoji+' '+x.cc.marks[m]?.label).join(', ')||'không vết gì';
  const state=bk.left>=0?`<span class="tag green">còn ${bk.left} ngày</span>`:`<span class="tag danger">quá hạn ${-bk.left} ngày</span>`;
  const book=`<dl class="kv rp-kv rp-book"><dt>Phiếu</dt><dd>${x.esc(bk.slip)} · sửa cách đây ${bk.ago} ngày</dd><dt>Đã sửa</dt><dd>${x.esc(faultOf(x,dev,bk.fault).name)} (${x.esc(x.cc.grades[bk.grade]?.short||bk.grade)})</dd><dt>Bảo hành</dt><dd>${bk.days} ngày ${state}</dd><dt>Tình trạng lúc đó</dt><dd>${x.esc(marks)}</dd></dl>`;
  const decided=b.claim?`<p class="small"><span class="tag ${b.claim==='cover'?'green':'amber'}">${b.claim==='cover'?'Đã ghi: bảo hành':'Đã ghi: tính tiền'}</span></p>`:'';
  const can=!!b.diagnosis&&!Object.keys(b.approved||{}).length;
  return `<div class="rp-claim">${book}${decided}<div class="row wrap">${x.cmd('🛡️ Bảo hành, khách không trả','rp_claim',{task:t.id,choice:'cover'},b.claim?'ghost small':'small',!can||b.claim==='cover')}${x.cmd('🧾 Ngoài bảo hành, tính tiền','rp_claim',{task:t.id,choice:'charge'},b.claim?'ghost small':'small',!can||b.claim==='charge')}</div>
    ${!b.diagnosis?'<p class="small muted">Chốt lỗi trước đã — bảo hành chỉ tính cho đúng lỗi cũ.</p>':''}</div>`;
}
function quoteView(t,x){
  const b=t.bench,dev=t.needs.device,open=(t.open_scope||[]),level=x.room.level,cs=caseOf(t);
  const last=b.quote?`<p class="notice ${b.quote.status==='accepted'?'green':'amber'} small" aria-live="polite">Báo giá lần ${b.quote.rounds}: ${x.esc(x.money(b.quote.total))} · Khách: “${x.esc(b.quote.reason)}”</p>`:'';
  const approved=Object.entries(b.approved||{}).map(([f,v])=>`<span class="tag green">✓ ${x.esc(faultOf(x,dev,f).name)} · ${x.esc(x.cc.grades[v.grade]?.short||v.grade)} · ${x.esc(x.money(v.price))}</span>`).join(' ');
  const pending=open.filter(f=>!b.approved[f]);
  let pre='';
  if(cs==='warranty')pre+=claimPanel(t,x);
  const waterRead=b.tests.find(r=>r.id==='water_tag');
  if(waterRead&&pending.includes('water')&&!b.shown)pre+=`<div class="notice amber small">Khách vẫn quả quyết máy chưa dính nước. ${x.cmd('📸 Cho khách xem tem báo nước','rp_show',{task:t.id},'primary small')}</div>`;
  else if(pending.includes('water')&&!b.shown)pre+=`<p class="notice amber small">Khách quả quyết chưa từng làm ướt máy. Có bằng chứng trong máy thì khách mới chịu nghe.</p>`;
  if(!pending.length)return `${pre}${last}<p class="small">${approved||'<span class="muted">Chốt lỗi để lập báo giá.</span>'}</p>`;
  const blocked=cs==='warranty'&&!b.claim;
  let total=0;
  const rows=pending.map(f=>{const fd=faultOf(x,dev,f),sel=gradeFor(x,t,f);
    const opts=Object.keys(fd.parts).map(g=>{const ln=line(x,t,fd,g),gr=x.cc.grades[g]||{name:g,warranty:0},lk=locked(x,ln.item),it=ln.item?itemOf(x,ln.item):null;
      if(g===sel)total+=ln.price;
      const src=x.cc.source_of?.[g],q=ln.item?x.stock(ln.item):null;
      const have=ln.item?(q>0?`còn ${q}`:src?`hết · ${src==='city'?'hãng về':'Lâm giao'} ${care(x).sources?.[src]?.when||''}`:'hết trên kệ'):'';
      const sub=`${have?have+' · ':''}${ln.price} xu · BH ${gr.warranty} ngày${gr.durable?' · '+gr.durable:''}`;
      return tile(x,{emoji:it?it.emoji:'🧽',label:gr.name,sub:lk?`🔒 mở ở cấp ${it.unlock} (bạn cấp ${level})`:sub,cls:(g===sel?'selected ':'')+(lk?'locked ':'')+(g==='used'?'rp-used':''),attr:carAttr(x,'grade',{task:t.id,fault:f,grade:g})+` aria-pressed="${g===sel}"`,off:lk});}).join('');
    return `<div class="rp-qrow"><b>${x.esc(fd.name)}</b><div class="tile-grid rp-grid">${opts}</div></div>`;}).join('');
  const cover=cs==='warranty'&&b.claim==='cover';
  const spent=(b.quote?.rounds||0)>=(x.cc.quote_rounds||6);
  return `${pre}${last}${approved?`<p class="small">${approved}</p>`:''}${rows}
    <p class="small muted">Đồ tháo máy rẻ nhưng hên xui — nhớ cắm thử trước khi lắp.</p>
    ${spent?`<p class="notice amber small">Khách đã nghe ${b.quote.rounds} lần báo giá, không muốn nghe thêm. Làm phần khách đã đồng ý, hoặc trả máy.</p>`:''}
    <div class="rp-cta rp-total"><span>Gửi khách: <b>${cover?'0 xu (bảo hành)':x.esc(x.money(total))}</b></span>
    <button type="button" class="btn ${spent?'ghost':'primary'}" ${carAttr(x,'quote',{task:t.id})} ${blocked||spent?'disabled':''}>📨 Gửi báo giá</button></div>`;
}

/* ---------- 3 · fix ---------- */
function fixView(t,x){
  const b=t.bench,dev=t.needs.device,devc=devOf(x,t),open=t.open_scope||[],level=x.room.level;
  const needOpen=open.length>0&&!b.opened;
  const btns=open.map(f=>{const fd=faultOf(x,dev,f),ap=b.approved[f];
    if(ap){
      const used=ap.grade==='used',item=fd.parts[ap.grade],tested=(b.checked||[]).includes(f);
      const o=tview(x,t).orders?.[f],mine=o&&!o.used&&o.item===item,src=x.cc.source_of?.[ap.grade];
      const lacking=!!item&&!mine&&!x.stock(item);
      const waiting=mine&&!o.arrived;
      let order='';
      if(mine)order=`<span class="tag ${o.arrived?'green':'amber'} rp-order">${x.esc(x.cc.sources?.[o.src]?.emoji||'📦')} ${x.esc(itemOf(x,item).name)} ${o.arrived?'đã về':'về '+x.esc(o.when)}</span>`;
      else if(lacking&&src){const sv=x.cc.sources?.[src]||{},cost=(itemOf(x,item).cost||0)+(sv.ship||0);
        order=x.confirmCmd(`<b>${x.esc(sv.emoji||'📦')} Hết trên kệ — đặt riêng · ${x.esc(x.money(cost))}</b><small>${x.esc(sv.name||'')} giao ${x.esc(care(x).sources?.[src]?.when||'')}</small>`,'rp_order',{task:t.id,fault:f},`Đặt riêng ${itemOf(x,item).name} cho máy này: ${cost} xu (gồm ${sv.ship||0} xu giao). ${sv.rule||''}`,'small rp-orderbtn',(x.room.money??0)<cost);}
      else if(lacking)order=`<p class="small muted">Hết ${x.esc(itemOf(x,item).name)} trên kệ — mở Kho nhập thêm, hoặc báo giá lại loại khác.</p>`;
      const test=used&&!tested?x.cmd(`🧪 Cắm thử ${x.esc(itemOf(x,item).name.toLowerCase())} (còn ${x.stock(item)})`,'rp_parttest',{task:t.id,fault:f},b.opened?'primary':'small',!x.stock(item)):'';
      const fix=x.cmd(`🛠️ Sửa: ${x.esc(fd.name)} · ${x.esc(x.cc.grades[ap.grade]?.short||'')}${used&&tested?' ✓ đã thử':''}${waiting?' · chờ đồ':''}`,'rp_fix',{task:t.id,fault:f},b.opened&&(!used||tested)&&!waiting&&!lacking?'primary':'ghost',!b.opened||waiting||(lacking&&!mine));
      return `<div class="rp-fixrow">${order}${test}${fix}</div>`;
    }
    return x.confirmCmd(`⚠️ Sửa “${x.esc(fd.name)}” khi khách chưa duyệt`,'rp_fix',{task:t.id,fault:f,grade:gradeFor(x,t,f)},'Khách CHƯA đồng ý báo giá cho việc này. Sửa khi chưa được đồng ý là lỗi nghiêm trọng: khách sẽ rất bực và đòi bớt tiền. Vẫn làm?','danger small',!b.opened);}).join('');
  const groups=[dev,'supply'];
  const shelf=items(x).filter(i=>groups.includes(i.group)).map(i=>{const q=x.stock(i.id),lk=locked(x,i.id);
    return `<li class="${lk?'locked':''} ${q===0?'empty':''}"><span aria-hidden="true">${x.esc(i.emoji)}</span><span class="grow">${x.esc(i.name)}</span><b>${lk?`🔒 ${i.unlock}`:q}</b></li>`;}).join('');
  const closeCta=!open.length&&b.opened?`<div class="rp-cta">${x.cmd(`🔩 ${x.esc(devc.close)}`,'rp_close',{task:t.id},'primary')}</div>`:'';
  const solder=open.some(f=>(faultOf(x,dev,f).supplies||[]).includes('solder'));
  return `${solder?toolWarn(x,'tip'):''}${shellBar(t,x,needOpen)}
    ${btns?`<div class="stack space-top">${btns}</div>`:`<p class="muted small space-top">${b.final==='pass'?'Đã sửa xong.':'Mọi hạng mục đã xử lý.'}</p>`}${closeCta}
    <details class="rp-shelfbox space-top"><summary>Kệ linh kiện ${x.esc(devc.name.toLowerCase())} (cấp ${level})</summary><ul class="rp-shelf">${shelf}</ul></details>`;
}

/* ---------- 4 · finish ---------- */
function finishView(t,x){
  const b=t.bench,fixedAny=Object.keys(b.fixed||{}).length>0,cs=caseOf(t);
  if(b.final!=='pass'){
    const why=b.opened?'Lắp máy lại trước khi chạy thử.':!fixedAny?'Chưa sửa gì — chạy thử lúc này vẫn y như cũ.':'';
    return `${b.final==='fail'?'<p class="notice amber small">Lần chạy thử trước chưa đạt — xem lại bảng giả thuyết.</p>':''}<div class="rp-cta">${x.cmd('▶️ Chạy thử lần cuối','rp_final',{task:t.id},'primary',b.opened||!fixedAny)}</div>${why?`<p class="small muted">${x.esc(why)}</p>`:''}${fixedAny&&!b.opened?`<div class="rp-return">${x.confirmCmd('📦 Giao máy luôn, không chạy thử','rp_handover',{task:t.id},'Giao máy khi chưa chạy thử và không có phiếu bảo hành? Nếu máy vẫn hỏng, khách sẽ không vui đâu.','ghost small')}</div>`:''}`;
  }
  const days=(x.cc.warranty||[0,7,30,90]).map(d=>x.cmd(d?`${d} ngày`:'Không BH','rp_warranty',{task:t.id,days:d},b.warranty===d?'primary small':'ghost small',b.warranty!=null)).join('');
  let privacy='';
  if(cs==='privacy'&&b.data_req==null)privacy=`<div class="rp-privacy"><p class="small"><b>Khách nhờ:</b> “${x.esc(t.needs.request)}”</p><div class="row wrap">${x.cmd('🙅 Từ chối, chỉ sửa phần cứng','rp_data',{task:t.id,choice:'refuse'},'small')}${x.confirmCmd(`📂 Làm theo, thu thêm ${x.cc.data_fee||15} xu`,'rp_data',{task:t.id,choice:'copy'},'Dữ liệu này không phải của người đang nhờ. Vẫn làm theo lời khách?','ghost small')}</div></div>`;
  else if(cs==='privacy')privacy=`<p class="small"><span class="tag ${b.data_req==='refuse'?'green':'amber'}">${b.data_req==='refuse'?'Đã từ chối chuyện dữ liệu':'Đã làm theo lời khách'}</span></p>`;
  const ready=b.warranty!=null&&!b.opened&&!(cs==='privacy'&&b.data_req==null);
  return `<p class="notice green small">✅ Chạy thử đạt.</p>
    <p class="small muted">Bảo hành theo linh kiện: chính hãng 90 · tương thích/thay mới 30 · tháo máy, vệ sinh 7 · máy vô nước không bảo hành.</p>
    <div class="row wrap rp-days">${days}</div>${privacy}
    <div class="rp-cta">${x.confirmCmd('✅ Bàn giao & thu tiền','rp_handover',{task:t.id},'Trả máy, phụ kiện và phiếu bảo hành; thu tiền đúng báo giá khách đã duyệt?','primary big',!ready)}</div>`;
}

function returnLink(t,x){const b=t.bench,fixedAny=Object.keys(b.fixed||{}).length>0,fee=x.cc.check_fee||10;
  if(b.final==='pass')return '';
  return `<div class="rp-return">${x.confirmCmd('↩️ Trả máy không sửa','rp_return',{task:t.id},`Trả máy nguyên trạng kèm phụ kiện${b.tests.length?` và thu phí kiểm tra ${fee} xu`:''}? Dùng khi khách không đồng ý giá hoặc sửa không đáng tiền.`,'ghost small',fixedAny||b.opened)}</div>`;}

/* ---------- buy-in (second-hand phone) ---------- */
function buyinView(t,x){
  const b=t.bench,n=t.needs,cheap=n.offer<n.worth*0.45;
  const imei=b.imei==null?x.cmd('📡 Tra IMEI máy báo mất','rp_imei',{task:t.id},'primary'):`<span class="tag ${b.imei==='reported'?'danger':'green'}">📡 ${b.imei==='reported'?'KHỚP máy báo mất':'Không có trong danh sách báo mất'}</span>`;
  const papers=b.papers==null?x.cmd('🪪 Hỏi hóa đơn & căn cước','rp_papers',{task:t.id},b.imei==null?'ghost':'primary'):`<span class="tag ${b.papers==='ok'?'green':'amber'}">🪪 ${b.papers==='ok'?'Hóa đơn, căn cước khớp tên':'Không có giấy tờ'}</span>`;
  return `<section class="rp-panel"><h4 class="section-title">Máy khách muốn bán</h4>
    <dl class="kv rp-kv"><dt>Giá khách đòi</dt><dd><b>${x.esc(x.money(n.offer))}</b> ${cheap?'<span class="tag amber">rẻ bất thường</span>':''}</dd><dt>Giá chợ máy cùng đời</dt><dd>${x.esc(x.money(n.worth))}</dd></dl>
    <div class="stack space-top">${imei}${papers}</div>
    <h5 class="rp-sub">Quyết định</h5>
    <div class="row wrap rp-deal">${x.confirmCmd(`🤝 Mua ${x.esc(x.money(n.offer))}`,'rp_deal',{task:t.id,choice:'buy'},'Mua lại máy này? Máy sạch thì tháo được màn và pin để dành; máy gian thì mất trắng.','small')}
      ${x.confirmCmd('🙅 Từ chối khéo','rp_deal',{task:t.id,choice:'refuse'},'Từ chối mua máy này?','ghost small')}
      ${x.confirmCmd('🚓 Báo công an phường','rp_deal',{task:t.id,choice:'report'},'Báo công an phường về chiếc máy này? Nếu máy sạch, người bán bị nghi oan.','ghost small')}</div></section>`;
}

function book(x){const rows=(x.room.data?.book||[]).slice().reverse().slice(0,5);if(!rows.length)return '';
  return `<details class="rp-bookbox"><summary>📒 Sổ bảo hành (${(x.room.data?.book||[]).length})</summary><ul>${rows.map(r=>`<li><b>${x.esc(r.slip)}</b> · ${x.esc(r.title)} · ${r.days?`${r.days} ngày`:'không BH'}</li>`).join('')}</ul></details>`;}

export default {
  id:'repair',
  css:true,
  next(t,x){
    if(x?.room?.data?.desk?.ev)return 'Có chuyện ở quầy cần quyết';
    if(t.bench?.shelf&&x?.room?.data?.care?.tasks?.[t.id]?.call)return 'Khách gọi hỏi — trả lời điện thoại';
    if(!t.known)return 'Nghe khách kể bệnh của máy';
    const b=t.bench,open=t.open_scope||[],cs=caseOf(t);
    if(cs==='buyin')return b.imei==null||b.papers==null?'Kiểm nguồn gốc máy':'Quyết: mua, từ chối hay báo';
    if(!b.intake)return 'Ghi phiếu nhận máy';
    if(b.final==='pass')return b.warranty==null?'Ghi phiếu bảo hành':cs==='privacy'&&b.data_req==null?'Trả lời khách chuyện dữ liệu':'Bàn giao & thu tiền';
    if(!b.diagnosis&&!open.length)return 'Đo kiểm để khoanh vùng lỗi';
    if(cs==='warranty'&&!b.book)return 'Tra sổ bảo hành';
    if(cs==='warranty'&&!b.claim&&open.some(f=>!b.approved[f]))return 'Quyết: bảo hành hay tính tiền';
    if(open.some(f=>!b.approved[f]))return b.quote?.status==='declined'?'Khách chê giá — báo lại hoặc trả máy':'Báo giá cho khách duyệt';
    const waitPart=Object.values(x?.room?.data?.care?.tasks?.[t.id]?.orders||{}).find(o=>!o.used&&!o.arrived);
    if(waitPart&&!open.some(f=>!b.approved[f]))return b.shelf?`Trên kệ ${b.shelf.tag} · đồ về ${waitPart.when}`:`Chờ đồ về ${waitPart.when} — hẹn khách để máy lại?`;
    if(open.length&&!b.opened)return 'Làm an toàn rồi mở máy';
    if(open.length)return 'Thay / sửa theo báo giá';
    if(b.opened)return 'Lắp máy lại';
    return 'Chạy thử lần cuối';
  },
  idle(x){
    const d=x.room.data||{};
    const stats=`<div class="row wrap rp-stats"><span class="tag">🛠️ ${d.repaired||0} máy đã sửa</span>${d.used_scrapped?`<span class="tag">🧪 ${d.used_scrapped} đồ tháo máy bị loại</span>`:''}${d.rush_on_time?`<span class="tag green">⏱️ ${d.rush_on_time} lần kịp giờ gấp</span>`:''}</div>`;
    return `<div class="career-job rp rp-idle">${deskCard(x)}${alerts(x)}${lastDesk(x)}${todayChip(x)}${shelfPanel(x)}${stats}${toolsFold(x)}${regularsBook(x)}${book(x)}</div>`;
  },
  job(t,x){
    const desk=deskCard(x);
    if(!t.known){
      const who=x.npc(t.npc);
      return `<div class="career-job rp">${desk}${alerts(x)}${todayChip(x)}<article class="card rp-ticket"><div class="row">${x.portrait(who,52)}<div class="grow"><h3>${x.esc(who.display_name)}</h3><p>“${x.esc(t.opening)}”</p></div></div><div class="rp-cta">${x.cmd('📝 Hỏi khách kể bệnh của máy','ask',{task:t.id},'primary full',!!desk)}</div></article>${shelfFold(x)}</div>`;
    }
    if(desk)return `<div class="career-job rp">${desk}${ticket(t,x)}</div>`;
    const top=alerts(x,true);
    if(caseOf(t)==='buyin')return `<div class="career-job rp">${top}${lastDesk(x)}${ticket(t,x)}${buyinView(t,x)}${shelfFold(x)}</div>`;
    const at=stage(t),u=local(x,t);
    const tab=u.tab!=null&&u.tab<=at?u.tab:at;
    const views=[intakeView,testsView,quoteView,fixView,finishView];
    const titles=['Phiếu nhận máy','Đo kiểm & giả thuyết','Báo giá cho khách','Mở máy & thay sửa','Chạy thử, bảo hành, bàn giao'];
    const panel=`<section class="rp-panel ${tab===at?'focus':''}" aria-live="polite"><h4 class="section-title">${tab+1} · ${x.esc(titles[tab])}${tab!==at?` <button type="button" class="btn ghost small" ${carAttr(x,'tab',{task:t.id,tab:at})}>Về bước đang làm</button>`:''}</h4>${views[tab](t,x)}</section>`;
    const banner=t.bench.shelf?shelfBanner(t,x):'';
    return `<div class="career-job rp">${top}${lastDesk(x)}${banner}${ticket(t,x)}${steps(t,x,at,tab)}<div class="workbench"><div class="wb-main">${panel}${promiseFold(t,x)}${t.bench.intake?returnLink(t,x):''}
      <p class="rp-foot">${x.button('📦 Kho & nhập linh kiện','inventory',{},'ghost small')}</p>${shelfFold(x,t.id)}</div>
      <aside class="wb-side">${device(t,x)}</aside></div></div>`;
  },
  actions:{
    async mark(data,el,x){const u=x.ui.rp?.[data.task];if(!u)return;u.marks=u.marks.includes(data.id)?u.marks.filter(v=>v!==data.id):[...u.marks,data.id];x.render();},
    async acc(data,el,x){const u=x.ui.rp?.[data.task];if(!u)return;u.acc=u.acc.includes(data.id)?u.acc.filter(v=>v!==data.id):[...u.acc,data.id];x.render();},
    async consent(data,el,x){const u=x.ui.rp?.[data.task];if(!u)return;u.consent=!u.consent;x.render();},
    async tab(data,el,x){x.ui.rp??={};const u=x.ui.rp[data.task]??={marks:[],acc:[],consent:false,grades:{},tab:null};u.tab=Number(data.tab);x.render();},
    async intake(data,el,x){const u=x.ui.rp?.[data.task]||{marks:[],acc:[],consent:false};await x.send('rp_intake',{task:data.task,marks:u.marks,accessories:u.acc,consent:u.consent});const v=x.ui.rp?.[data.task];if(v)v.tab=null;},
    async grade(data,el,x){x.ui.rp??={};const u=x.ui.rp[data.task]??={marks:[],acc:[],consent:false,grades:{},tab:null};u.grades[data.fault]=data.grade;x.render();},
    async quote(data,el,x){
      const t=x.room.tasks.find(v=>v.id===data.task);if(!t)return;
      const grades={};for(const f of (t.open_scope||[]).filter(f=>!t.bench.approved[f]))grades[f]=gradeFor(x,t,f);
      const u=x.ui.rp?.[t.id];if(u)u.tab=null;
      await x.send('rp_quote',{task:t.id,grades});
    },
  },
  dock:[['inventory','box','Linh kiện','Nhập & đếm hàng']],
};
