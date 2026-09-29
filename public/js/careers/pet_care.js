/** Pet Care Mèo Mập — intake form, grooming table (body language, escapes, live rinse/dry bars), kennel, feeding
 *  station with medicine by the label, adoption interviews, and the surprises that walk in at the counter.
 *  Care loop: regulars' cards and trust, a daily care card per boarder, vaccine/deworming reminders, adoption follow-ups. */
import {reqList,fold} from '../ui-kit.js';
const JOB_ICON={groom:'🛁',board:'🏠',feed:'🥣',adopt:'🏡'};
const SPECIES_EMOJI={dog:'🐶',cat:'🐱'};
const MOOD={calm:'hiền',nervous:'nhát, dễ run',bitey:'hay cắn/cào',dog_aggressive:'ghét chó khác'};
const VAX={valid:['Còn hạn','green'],expired:['Hết hạn','danger'],none:['Không có sổ','danger']};
const HEAT={cool:'💨 Mát',warm:'🌬️ Ấm',hot:'🔥 Nóng'};
const R=v=>Math.floor(v+0.5);

const itemInfo=(x,id)=>(x.content.inventory?.items?.pet_care||[]).find(i=>i.id===id)||{id,name:id,emoji:'•'};
const price=(x,key)=>x.room.life?.prices?.[key]??0;
const age=m=>m<12?`${m} tháng`:`${Math.floor(m/12)} tuổi`;
const pen=(x,id)=>x.cc.pens.find(p=>p.id===id)||{id,name:id,emoji:'🏠'};
const isGen=t=>!!t.gen;
const cmdAttr=(x,command,payload)=>`data-command="${x.esc(command)}" data-payload="${x.esc(JSON.stringify(payload))}"`;
const deskOpen=x=>!!x.room.data?.desk?.ev;
const pickup=(t,x)=>(x.room.day||t.day)+(t.needs?.nights||0);

/* ---------------------------------------------------------------- chart maths (the published game rule, shown to the player) */
function stageOf(x,species,months){if(months<12)return'young';return months>=(species==='dog'?96:120)?'senior':'adult';}
function gpk(x,species,kg){return (x.cc.chart[species]||[]).find(([top])=>kg<=top)?.[1]||0;}
function daily(x,species,kg,months){return R(kg*gpk(x,species,kg)*x.cc.stage_pct[stageOf(x,species,months)]/100);}

/* ---------------------------------------------------------------- local scratch state per task */
function ui(x,t){
  if(x.ui.tid!==t.id){
    const n=t.needs||{};
    x.ui.tid=t.id;
    const pl=t.plan||t.bowl||{};
    x.ui.v={shampoo:null,temp:34,cond:false,food:pl.food||n.food||(n.food_own?'own':'house'),meals:pl.meals||2,grams:pl.grams||(n.kg?Math.max(5,R(n.kg*10)):50),
      solo:!!pl.solo,say:[...(t.report||[])],pet:t.match||null};
  }
  return x.ui.v;
}
const setBtn=(x,label,key,val,on,extra='')=>`<button type="button" class="btn small ${on?'primary':'ghost'} ${extra}" data-action="car:set" data-key="${x.esc(key)}" data-val="${x.esc(String(val))}" aria-pressed="${on}">${label}</button>`;
const stepBtn=(x,label,key,delta,min,max)=>`<button type="button" class="btn small ghost pc-q" data-action="car:step" data-key="${x.esc(key)}" data-delta="${delta}" data-min="${min}" data-max="${max}" aria-label="${x.esc(key)} ${delta>0?'+':''}${delta}">${label}</button>`;

function checklist(x,rows){
  return `<ul class="checklist">${rows.map(([ok,label,note])=>`<li class="${ok===true?'ok':ok===false?'bad':''}"><span>${ok===true?'✓':ok===false?'✗':'○'}</span>${x.esc(label)}${note?`<small>${x.esc(note)}</small>`:''}</li>`).join('')}</ul>`;
}
function section(title,body,cls=''){return `<section class="pc-card ${cls}"><h4 class="section-title">${title}</h4>${body}</section>`;}

/* ---------------------------------------------------------------- the one step that matters now (only it gets the primary colour) */
function saidDone(t,x){const say=ui(x,t).say,saved=t.report||[];return saved.length>0&&saved.length===say.length&&saved.every(r=>say.includes(r));}
// The cue box already says it in words; the highlight must not point at work while the pet shows panic.
function panicSeen(t,x){const p=x.cc.cues?.[t.needs?.species]?.panic||[];return isGen(t)&&(t.cues||[]).some(c=>p.includes(c));}
function focus(t,x){
  if(!t.known)return 'ask';
  if(t.job==='groom'){
    const g=t.g,sv=t.needs.services;
    if(g.bolt)return '';
    if(g.rinse)return 'rinse_stop';
    if(g.dry)return 'dry_stop';
    if(g.nick&&!g.stanched)return 'styptic';
    if(!g.stopped&&panicSeen(t,x))return '';
    if(!g.stopped){
      if(sv.includes('brush')&&!g.brush)return 'brush';
      if(sv.includes('bath')&&!g.shampoo)return 'bath';
      if(sv.includes('bath')&&g.rinse_s<(x.cc.rinse_min||8)&&!g.dry_pct)return 'rinse';
      if(sv.includes('bath')&&g.dry_pct<100)return '';
      if(sv.includes('nails')&&!g.nails)return '';
      if(sv.includes('ears')&&!g.ears)return '';
    }
    return saidDone(t,x)?'handover':'report';
  }
  if(t.job==='board')return !t.plan?'plan':'admit';
  if(t.job==='feed'){
    if(!t.fed)return 'feed';
    if(t.needs.med&&!t.med)return '';
    if(!(t.walked||t.litter))return t.needs.species==='dog'?'walk':'litter';
    return saidDone(t,x)?'handover':'report';
  }
  return 'match';
}
const st=(t,x,key,alt='ghost')=>focus(t,x)===key?'primary':alt;

/* ---------------------------------------------------------------- the day, the counter */
function todayChip(x){const m=x.room.data?.mod;return m?`<p class="pc-today"><span aria-hidden="true">${x.esc(m.emoji)}</span> <b>Hôm nay: ${x.esc(m.title)}</b> <small>${x.esc(m.text)}</small></p>`:'';}
function deskCard(x){
  const ev=x.room.data?.desk?.ev;if(!ev)return '';
  const who=x.npc(ev.npc);
  const opts=ev.options.map(o=>`<button type="button" class="btn ghost pc-opt" ${cmdAttr(x,'pc_desk',{option:o.id})} ${o.cost>x.room.money?'disabled':''}><b>${x.esc(o.label)}</b>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}</button>`).join('');
  return `<section class="pc-desk ${x.esc(ev.tone||'')}" role="alert" aria-live="assertive"><div class="pc-desk-head"><span class="pc-desk-emoji" aria-hidden="true">${x.esc(ev.emoji)}</span><div class="grow"><small>CHUYỆN Ở QUẦY</small><h3>${x.esc(ev.title)}</h3></div>${x.portrait(who,40)}</div>
    <p>${x.esc(ev.text)}</p><div class="pc-opts">${opts}</div></section>`;
}
function lastDesk(x){const l=x.room.data?.desk?.last;if(!l||l.day!==x.room.day)return '';return `<p class="pc-last ${l.good===true?'good':l.good===false?'bad':''}" aria-live="polite"><span aria-hidden="true">${x.esc(l.emoji)}</span> <b>${x.esc(l.title)}:</b> ${x.esc(l.outcome)}</p>`;}
function foot(x){
  const d=x.room.data||{},busy=deskOpen(x);
  return `<p class="row wrap pc-foot">${x.cmd(d.sanitized_today?'✅ Đã khử khuẩn chuồng hôm nay':'🧽 Khử khuẩn chuồng & bàn tắm','pc_sanitize',{},'ghost small',!!d.sanitized_today||busy)}${x.button('📦 Kho & nhập hàng','inventory',{},'ghost small')}</p>`;
}
function rules(x){return `<details class="pc-rules"><summary>📋 Nội quy tiệm</summary><ul>${(x.cc.rules||[]).map(r=>`<li>${x.esc(r)}</li>`).join('')}</ul></details>`;}
function kennelBox(x,open=false){
  const d=x.room.data||{},pens=d.pens||{},busy=Object.values(pens).filter(Boolean).length,free=x.cc.pens.filter(p=>p.unlock<=(d.level||1)).length;
  const todo=Object.values(d.stay||{}).reduce((a,s)=>a+(s.todo||0),0);
  const left=todo?`<span class="tag amber">${todo} việc chăm còn lại</span>`:busy?'<span class="tag green">đã chăm đủ hôm nay</span>':'';
  return `<details class="pc-card pc-kennel-box"${open&&todo?' open':''}><summary><b>🏠 Khu lưu trú</b> <small>${busy}/${free} chuồng có bé</small> ${left}</summary>${stayCards(x)}${kennel(x)}</details>`;
}

/* ---------------------------------------------------------------- care loop: one card per boarder, today's chores */
const petKey=t=>`${parseInt(String(t.npc).split('_').pop(),10)-1}:${t.needs?.name}`;
const bookOf=(t,x)=>x.room.data?.book?.[petKey(t)]||null;
const hearts=n=>'★'.repeat(n)+'☆'.repeat(Math.max(0,5-n));
function vital(label,word,v){
  const tone=v>=75?'good':v>=55?'':'warn';
  return `<div class="pc-vital ${tone}"><span>${label} <b>${word}</b></span><div class="pc-vbar" aria-hidden="true"><i style="width:${Math.max(0,Math.min(100,v))}%"></i></div></div>`;
}
function stayCard(x,pid,st){
  const v=x.room.data.pens[pid],p=pen(x,pid),dog=v.species==='dog',busy=deskOpen(x);
  const rows=[{ok:st.meals>=st.need?true:null,icon:'🥣',label:'Bữa ăn theo thẻ',value:`${st.meals}/${st.need}`,note:`${v.grams} g/bữa · ${v.food==='own'?'đồ chủ gửi':'hạt của tiệm'}`},
    {ok:st.chore?true:null,icon:dog?'🦮':'🧹',label:dog?'Dắt đi dạo':'Dọn khay cát'}];
  if(st.rx)rows.push({ok:st.med?true:null,icon:'💊',label:st.rx.name,note:'Nhãn: '+st.rx.label});
  if(st.warn_info)rows.push({ok:st.warn_ok?true:null,icon:st.warn_info.emoji,label:st.warn_info.label,note:st.warn_info.fix,tone:st.warn_ok?'':'warn'});
  rows.push({ok:st.played?true:null,icon:'🧸',label:'Chơi, vỗ về',note:st.fav_text?`bé mê ${st.fav_text}`:'không bắt buộc, bé vui hơn'});
  const food=v.food==='house'?x.stock(x.cc.house_food[v.species]):null;
  const btns=[x.cmd(`🥣 Cho ăn${food!==null?` <small>(kho ${food})</small>`:''}`,'pc_stay',{pen:pid,do:'feed'},st.meals<st.need&&!(st.warn==='appetite'&&!st.played)?'primary small':'ghost small',busy||st.meals>=st.need||food===0),
    dog?x.cmd(`🦮 Dắt đi dạo <small>(túi ${x.stock('poop_bag')})</small>`,'pc_stay',{pen:pid,do:'walk'},'ghost small',busy||st.chore||!x.stock('poop_bag'))
      :x.cmd('🧹 Dọn khay cát','pc_stay',{pen:pid,do:'litter'},'ghost small',busy||st.chore),
    x.cmd('🧸 Chơi, vỗ về','pc_stay',{pen:pid,do:'play'},st.warn&&!st.warn_ok&&st.warn!=='upset'?'primary small':'ghost small',busy||st.played),
    x.cmd('📞 Gọi báo chủ','pc_stay',{pen:pid,do:'call'},st.warn==='upset'&&!st.called?'primary small':'ghost small',busy||st.called)].join('');
  const med=st.rx&&!st.med?`<div class="row wrap pc-doses"><small>💊 Liều theo nhãn:</small>${(x.cc.doses||[]).map(d=>x.confirmCmd(x.esc(d.name),'pc_stay',{pen:pid,do:'med',dose:d.id},`Cho bé ${v.pet} uống ${d.name.toLowerCase()}? Nhãn: “${st.rx.label}”`,'ghost small',busy||!st.meals)).join('')}</div>${st.meals?'':'<p class="small muted">Cho ăn trước — thuốc uống cùng bữa.</p>'}`:'';
  const log=(st.log||[]).length?fold('📓 Nhật ký chăm sóc',`<ul class="pc-log">${st.log.map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul>`):'';
  return `<article class="pc-stay ${st.todo?'':'done'}"><div class="pc-stay-head"><b>${SPECIES_EMOJI[v.species]} ${x.esc(v.pet)}</b><small>${x.esc(p.name)} · ${x.esc(v.owner)} đón ngày ${v.until}</small></div>
    <div class="pc-vitals">${vital('😊 Tinh thần',x.esc(st.mood_word),st.mood)}${vital('💚 Sức khỏe',x.esc(st.health_word),st.health)}</div>
    ${reqList(rows,x.esc,'Việc chăm bé '+v.pet+' hôm nay')}<div class="row wrap pc-stay-btns">${btns}</div>${med}${log}</article>`;
}
function stayCards(x){
  const st=x.room.data?.stay||{},ids=x.cc.pens.map(p=>p.id).filter(id=>st[id]&&x.room.data.pens?.[id]);
  if(!ids.length)return '';
  return `<div class="pc-stays">${ids.map(id=>stayCard(x,id,st[id])).join('')}</div>`;
}

/* ---------------------------------------------------------------- care loop: regulars, reminders, follow-up calls */
function regularCard(t,x){
  const r=bookOf(t,x);if(!r||t.regular==null)return '';
  const rows=[['Tin tiệm',`<span class="pc-hearts" aria-label="${r.trust}/5">${hearts(r.trust)}</span> ${x.esc(r.trust_name)}`],['Đã ghé',`${r.visits} lần · lần trước ngày ${r.last}`]];
  rows.push(['Tính khí',r.mood?`<b>${x.esc(MOOD[r.mood]||r.mood)}</b>`:'<span class="muted">chưa ghi</span>']);
  if(r.allergy)rows.push(['Dị ứng',`<span class="tag danger">${x.esc(x.cc.allergy_names[r.allergy]||r.allergy)}</span>`]);
  if(r.nails)rows.push(['Móng',r.nails==='dark'?'<span class="tag amber">Móng đen — chỉ tỉa đầu móng</span>':'Móng trắng, thấy tủy']);
  if(r.kg)rows.push(['Cân lần trước',`${r.kg} kg`]);
  if((r.told||[]).length)rows.push(['Lần trước đã báo',x.esc(r.told.map(s=>x.cc.signs[s]?.label||s).join(', '))]);
  const favOn=r.fav_text&&t.regular>=(x.cc.fav_at||2);
  rows.push(['Món bé mê',r.fav_text?`${x.esc(r.fav_text)} ${favOn?'<span class="tag green">dùng khi dỗ bé</span>':`<span class="tag">mở khi bé “${x.esc((x.cc.trust_names||[])[x.cc.fav_at||2]||'')}”</span>`}`:'<span class="muted">chủ chưa kể</span>']);
  const due=[r.vax_due!=null?`💉 tiêm nhắc ngày ${r.vax_due}`:'',r.worm_due!=null?`🪱 tẩy giun ngày ${r.worm_due}`:''].filter(Boolean).join(' · ');
  if(due)rows.push(['Lịch hẹn',due]);
  const open=!['completed','referred','cancelled'].includes(t.status);
  const greet=open&&!t.greeted?`<div class="row wrap">${x.cmd('👋 Gọi tên bé, hỏi thăm lần trước','pc_greet',{task:t.id},'ghost small',deskOpen(x))}</div>`:t.greeted?'<p class="small muted">✓ Đã chào bé và hỏi thăm chủ.</p>':'';
  const body=`<div class="pc-form">${rows.map(([k,v])=>`<div class="pc-row"><span>${k}</span><b>${v}</b></div>`).join('')}</div>${greet}`;
  return `<section class="pc-card pc-regular">${fold(`⭐ Khách quen · ${x.esc(r.trust_name)} · ${r.visits} lần ghé`,body,!t.greeted&&open)}</section>`;
}
function dueList(x){
  const due=x.room.data?.due||[],busy=deskOpen(x),late=x.cc.remind_late||2;
  if(!due.length)return '';
  const row=r=>`<li class="pc-due ${r.late>late?'late':r.late?'warn':''}"><span aria-hidden="true">${r.kind==='vax'?'💉':'🪱'}</span><div class="grow"><b>${x.esc(r.name)}</b> <small>${x.esc(r.owner)} · ${r.kind==='vax'?'tiêm nhắc':'tẩy giun'} ${r.late?`trễ ${r.late} ngày`:`ngày ${r.due}`}</small></div>${x.cmd('📱 Nhắn chủ','pc_remind',{pet:r.pet,kind:r.kind},'ghost small',busy)}</li>`;
  const more=due.length>4?fold(`Xem thêm ${due.length-4} lịch nhắc`,`<ul class="pc-dues">${due.slice(4).map(row).join('')}</ul>`):'';
  return section('📅 Nhắc lịch tiêm & tẩy giun',`<ul class="pc-dues">${due.slice(0,4).map(row).join('')}</ul>${more}<p class="small muted">Nhắc đúng hạn (trễ tối đa ${late} ngày) chủ thêm tin tiệm. Khi bé ghé vẫn phải xem sổ tiêm thật.</p>`);
}
function followCards(x){
  const calls=x.room.data?.follow||[],busy=deskOpen(x);
  if(!calls.length)return '';
  return section('📞 Hỏi thăm bé đã nhận nuôi',calls.map(f=>f.ready?`<div class="pc-follow"><p><b>${x.esc(f.emoji)} ${x.esc(f.name)} · ${x.esc(f.family)}</b></p><p class="bubble npc small">“${x.esc(f.q)}”</p>
    <div class="pc-opts">${f.options.map(o=>`<button type="button" class="btn ghost pc-opt" ${cmdAttr(x,'pc_follow',{id:f.id,option:o.id})} ${busy?'disabled':''}><b>${x.esc(o.label)}</b></button>`).join('')}</div></div>`
    :`<p class="small">${x.esc(f.emoji)} Ngày ${f.due}: gọi hỏi thăm bé <b>${x.esc(f.name)}</b> ở nhà ${x.esc(f.family)}.</p>`).join(''));
}
function bookFold(x){
  const book=Object.values(x.room.data?.book||{}).sort((a,b)=>b.last-a.last||b.trust-a.trust);
  if(!book.length)return '';
  const rows=book.slice(0,24).map(r=>`<li><span aria-hidden="true">${SPECIES_EMOJI[r.species]}</span><div class="grow"><b>${x.esc(r.name)}</b> <small>${x.esc(r.breed)} · ${x.esc(r.owner)} · ngày ${r.last}</small></div><span class="pc-hearts" title="${x.esc(r.trust_name)}" aria-label="${x.esc(r.trust_name)}">${hearts(r.trust)}</span></li>`).join('');
  return `<section class="pc-card">${fold(`📒 Sổ khách quen · ${book.length} bé`,`<ul class="pc-book">${rows}</ul>`)}</section>`;
}
function careBoard(x){return followCards(x)+dueList(x);}
function careCount(x){const d=x.room.data||{};return (d.due||[]).length+(d.follow||[]).filter(f=>f.ready).length;}

/* ---------------------------------------------------------------- intake form + inspection */
function partTiles(t,x,warnOf){
  return (x.cc.job_parts[t.job]||[]).map(part=>{
    const info=x.cc.parts[part]||{emoji:'🔎',label:part},seen=t.found?.[part];
    return seen?`<div class="pc-found ${warnOf(part)?'warn':''}"><span class="tile-emoji" aria-hidden="true">${info.emoji}</span><div><b>${x.esc(info.label)}</b><small>${x.esc(seen)}</small></div></div>`
      :`<button type="button" class="tile pc-part" ${cmdAttr(x,'pc_inspect',{task:t.id,part})}><span class="tile-emoji" aria-hidden="true">${info.emoji}</span><b>${x.esc(info.label)}</b><small>chưa kiểm</small></button>`;
  }).join('');
}
function intake(t,x){
  const n=t.needs,f=t.facts||{},job=t.job;
  const rows=[['Bé',`${SPECIES_EMOJI[n.species]} ${x.esc(n.name)} · ${x.esc(n.breed)}`],['Tuổi',`${age(n.months)} · ${x.esc(x.cc.stage_names[n.stage]||'')}`]];
  if(job==='feed')rows.push(['Cân lúc nhận',`${n.kg} kg`]);
  else rows.push(['Cân nặng',f.kg!=null?`<b>${f.kg} kg</b> ${f.kg!==n.kg_said?`<span class="tag amber">chủ khai ${n.kg_said} kg</span>`:'<span class="tag green">đúng</span>'}`:`chủ khai ~${n.kg_said} kg <span class="muted">(chưa cân)</span>`]);
  if(job!=='feed')rows.push(['Tính khí',f.mood?`<b>${x.esc(MOOD[f.mood]||f.mood)}</b>${f.mood!==n.mood_said?` <span class="tag amber">chủ nói ${x.esc(MOOD[n.mood_said]||'')}</span>`:''}`:`chủ nói: ${x.esc(MOOD[n.mood_said]||'')}`]);
  if(job==='groom'){
    rows.push(['Dịch vụ',n.services.map(s=>x.esc(x.cc.services[s]||s)).join(' · ')]);
    if(n.rx)rows.push(['Đơn thuốc','<span class="tag blue">💊 Có đơn bác sĩ thú y (sữa tắm trị liệu)</span>']);
    if(n.short_nails)rows.push(['Chủ muốn','Cắt móng thật ngắn']);
  }
  if(job==='board'){
    rows.push(['Tiêm phòng',f.vax?`<span class="tag ${VAX[f.vax][1]}">${VAX[f.vax][0]}</span>`:'chủ nói “đủ mũi rồi” <span class="muted">(chưa xem sổ)</span>']);
    rows.push(['Lưu trú',`${n.nights} đêm · chủ đón <b>ngày ${pickup(t,x)}</b>`],['Thức ăn',n.food_own?'Chủ gửi kèm':'Hạt của tiệm']);
    if(n.allergy)rows.push(['Dị ứng',`<span class="tag danger">${x.esc(x.cc.allergy_names[n.allergy]||n.allergy)}</span>`]);
  }
  if(job==='feed'){
    rows.push(['Thẻ ăn',`${n.meals} bữa/ngày · ${n.food==='own'?'thức ăn chủ gửi':'hạt của tiệm'}`]);
    const p=t.pen?pen(x,t.pen):null;rows.push(['Chuồng',p?`${p.emoji} ${x.esc(p.name)}`:'Lồng tạm ở quầy']);
    if(n.med)rows.push(['Thuốc','<span class="tag blue">💊 Có thuốc theo đơn</span>']);
  }
  if(n.no_treat)rows.push(['Chế độ ăn','<span class="tag danger">Không bánh thưởng</span>']);
  const form=`<div class="pc-form">${rows.map(([k,v])=>`<div class="pc-row"><span>${k}</span><b>${v}</b></div>`).join('')}<p class="bubble npc small">“${x.esc(n.note)}”</p></div>`;
  const warn=part=>(f.signs||[]).some(s=>x.cc.signs[s]?.part===part)||(part==='vaccine'&&f.vax&&(f.vax!=='valid'||(f.vax_until!=null&&f.vax_until<pickup(t,x))))
    ||(part==='mood'&&f.mood&&f.mood!=='calm')||(part==='scale'&&f.kg!=null&&job!=='feed'&&f.kg!==n.kg_said);
  return section('📋 Phiếu nhận bé',form)+section('🔎 Kiểm tra tận tay',`<div class="pc-parts">${partTiles(t,x,warn)}</div>`);
}

/* ---------------------------------------------------------------- grooming */
function stressBar(x,g){
  const s=g.stress,stop=x.cc.stress_stop;
  return `<div class="pc-stress ${s>=stop?'bad':s>=60?'warn':'good'}" role="meter" aria-label="Stress của bé" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${s}"><div class="row spread"><b>💓 Stress của bé</b><b>${s}/100</b></div>
    <div class="pc-meter"><i style="width:${s}%"></i><em style="left:${stop}%" title="Ngưỡng dừng"></em></div>
    <small>${s>=stop?'Bé hoảng rồi! Dỗ dành, cho nghỉ hoặc dừng dịch vụ — không làm tiếp.':s>=60?'Bé bắt đầu run. Nói nhỏ, làm chậm lại.':'Bé đang bình tĩnh.'} Cao nhất: ${g.peak}</small></div>`;
}
function cueBox(t,x){
  const sp=t.needs.species,cues=t.cues||[],bands=x.cc.bands||[],book=x.cc.cues?.[sp]||{};
  const guide=bands.map(b=>`<li><b>${x.esc(b.name)}:</b> ${(book[b.id]||[]).map(x.esc).join(' · ')}</li>`).join('');
  return `<div class="pc-cues" role="status" aria-live="polite"><b>🐾 Bé đang:</b><ul>${cues.map(c=>`<li>${x.esc(c)}</li>`).join('')}</ul>
    <details><summary>Đọc tín hiệu cơ thể thế nào?</summary><ul class="pc-guide">${guide}</ul><p class="small muted">Từ “Căng thẳng” trở lên: dỗ hoặc cho nghỉ rồi mới làm tiếp. “Hoảng sợ” thì dừng tay.</p></details></div>`;
}
function calmTools(t,x){
  const n=t.needs,g=t.g,cat=n.species==='cat',f=t.facts||{},gen=isGen(t),off=g.stopped||g.bolt;
  const knownBitey=n.mood_said==='bitey'||f.mood==='bitey';
  const tools=x.cc.calm.filter(c=>c.id!=='wrap'||cat).map(c=>{
    const stock=c.id==='treat'?x.stock('treat'):c.id==='wrap'?x.stock('towel'):null;
    const no=(stock!==null&&!stock)||(c.id==='break'&&(g.rinse||g.dry));
    return x.cmd(`${c.emoji} ${x.esc(c.name)}${stock!==null?` <small>(${stock})</small>`:''}${gen?'':` <small>−${c.drop}</small>`}`,'pc_calm',{task:t.id,how:c.id},'ghost small',no||off);
  }).join('');
  let muzzle='';
  if(!cat&&knownBitey)muzzle=g.muzzle?'<span class="tag blue">🧢 Đang đeo rọ mõm mềm</span>':g.consent?x.cmd('🧢 Đeo rọ mõm mềm','pc_muzzle',{task:t.id},'ghost small',off):x.cmd('🙋 Hỏi chủ đồng ý rọ mõm','pc_consent',{task:t.id},'ghost small',off);
  if(cat)muzzle=`${x.cmd('🧢 Rọ mõm','pc_muzzle',{task:t.id},'ghost small pc-no',off)}${g.wrap?'<span class="tag blue">🌯 Đã quấn khăn</span>':''}`;
  const loop=!gen?'':g.loop?'<span class="tag blue">🔗 Đang đeo vòng giữ trên bàn</span>':x.cmd('🔗 Đeo vòng giữ cổ trên bàn','pc_loop',{task:t.id},'ghost small',off);
  const r=bookOf(t,x),fav=gen&&r?.fav_text&&t.regular>=(x.cc.fav_at||2)?x.cmd(`💛 ${x.esc(r.fav_text)}${r.fav_kind==='treat'?` <small>(${x.stock('treat')})</small>`:''}`,'pc_calm',{task:t.id,how:'fav'},'ghost small',off||(r.fav_kind==='treat'&&!x.stock('treat'))):'';
  return `${gen?cueBox(t,x):stressBar(x,g)}<div class="row wrap pc-tools">${fav}${tools}${muzzle}${loop}</div>
    <div class="row wrap">${x.confirmCmd('⏹️ Dừng dịch vụ','pc_stop',{task:t.id},'Dừng giữa chừng? Bé được lau khô, trả chủ và chỉ tính phần đã làm.','danger small',off||!!(g.rinse||g.dry))}</div>${g.rinse||g.dry?'<p class="small muted">Muốn dừng: khóa vòi / tắt máy sấy trước.</p>':''}`;
}
function boltAlert(t,x){
  const opts=(x.cc.catch||[]).map(c=>{
    const no=c.id==='lure'&&!x.stock('treat');
    return `<button type="button" class="btn ghost pc-opt" ${cmdAttr(x,'pc_catch',{task:t.id,how:c.id})} ${no?'disabled':''}><b>${x.esc(c.emoji)} ${x.esc(c.name)}</b><small>${x.esc(c.note)}${c.id==='lure'?` · còn ${x.stock('treat')} bánh`:''}</small></button>`;
  }).join('');
  return `<section class="pc-bolt" role="alert" aria-live="assertive"><h4>⚠️ Bé nhảy khỏi bàn, lao về phía cửa!</h4><div class="pc-opts">${opts}</div></section>`;
}
function stepStrip(t,x){
  const n=t.needs,g=t.g,sv=n.services;
  const state={brush:g.brush,bath:g.shampoo!=null,rinse:g.rinse_s>=x.cc.rinse_min,dry:g.dry_pct>=100,nails:g.nails!=null,ears:g.ears!=null};
  const need={brush:sv.includes('brush'),bath:sv.includes('bath'),rinse:sv.includes('bath'),dry:sv.includes('bath'),nails:sv.includes('nails'),ears:sv.includes('ears')};
  const current=x.cc.steps.find(s=>need[s.id]&&!state[s.id])?.id;
  return `<ol class="pc-steps">${x.cc.steps.map(s=>`<li class="${!need[s.id]?'skip':state[s.id]?'done':s.id===current?'now':''}"><span>${state[s.id]?'✓':s.emoji}</span>${x.esc(s.name)}</li>`).join('')}</ol>`;
}
function timerBar(kind,start,base,need,over,rate,label){
  return `<div class="pc-timer ${kind}" data-pc-timer="${kind}" data-start="${start||''}" data-base="${base}" data-need="${need}" data-over="${over}" data-rate="${rate}">
    <div class="pc-track"><b class="fill" style="width:${Math.min(100,base/over*100)}%"></b><em style="left:${need/over*100}%"></em></div>
    <small class="pc-timer-label" aria-live="polite">${label}</small></div>`;
}
function dryNeed(t,x,heat){const n=t.needs;return (x.cc.dry_need[n.coat]||6)*(heat==='cool'?1.5:1)*(n.humid?1.5:1);}
function rinseBox(t,x){
  const g=t.g,label=g.rinse?'Đang xả…':`Đã xả ${Number(g.rinse_s).toFixed(1)} giây / cần ${x.cc.rinse_min}`;
  return `<h5>🚿 Xả sạch bọt</h5>${timerBar('rinse',g.rinse,g.rinse_s,x.cc.rinse_min,x.cc.rinse_min*2,1,label)}
    <div class="row wrap">${g.rinse?x.cmd('🚰 Khóa vòi','pc_rinse',{task:t.id,mode:'stop'},'primary'):x.cmd('🚿 Mở vòi xả','pc_rinse',{task:t.id,mode:'start'},st(t,x,'rinse'),!g.shampoo||g.dry_pct>0||!!g.dry||g.stopped||g.bolt)}</div>`;
}
function dryBox(t,x){
  const n=t.needs,g=t.g,heat=g.heat||'warm',need=dryNeed(t,x,heat),off=g.stopped||g.bolt;
  const label=g.dry?'Đang sấy…':`Khô ${Math.min(100,g.dry_pct)}%`;
  return `<h5>💨 Lau & sấy</h5>${timerBar('dry',g.dry,g.dry_pct,100,x.cc.dry_over*100,100/need,label)}
    <div class="row wrap">${g.dry?x.cmd('⏹️ Tắt máy sấy','pc_dry',{task:t.id,mode:'stop'},'primary'):['cool','warm','hot'].map(h=>x.cmd(HEAT[h],'pc_dry',{task:t.id,mode:'start',heat:h},h==='hot'?'ghost small pc-no':'ghost small',!g.shampoo||!g.rinse_s||!!g.rinse||off)).join('')}</div>
    <p class="small muted">Lông ${n.coat==='long'?'dài':'ngắn'}: khoảng ${Math.round(need*10)/10} giây ở nấc ${heat==='cool'?'mát':'ấm'}${n.humid?' (trời ẩm, lâu gấp rưỡi)':''}.</p>`;
}
function groomJob(t,x){
  const n=t.needs,g=t.g,sv=n.services,v=ui(x,t),busy=g.rinse||g.dry,off=g.stopped||g.bolt;
  const wet=g.shampoo!=null&&g.dry_pct<100&&!g.stopped;
  let html=section('🛁 Bàn tắm tỉa',stepStrip(t,x)+calmTools(t,x));
  if(sv.includes('brush'))html+=section('🪮 Chải & gỡ rối',g.brush&&(g.flea||g.shampoo)?`<p class="small">✓ Đã chải gỡ rối${g.flea?' · đã chải bọ chét':''}.</p>`:`<div class="row wrap">${x.cmd(g.brush?'✓ Đã chải gỡ rối':'🪮 Chải gỡ rối','pc_brush',{task:t.id,tool:'brush'},st(t,x,'brush'),g.brush||g.shampoo!=null||off)}
    ${x.cmd(g.flea?'✓ Đã chải bọ chét':'🐜 Lược bọ chét','pc_brush',{task:t.id,tool:'flea'},'ghost',g.flea||g.shampoo!=null||off)}</div><p class="small muted">Luôn gỡ rối trước khi tắm: nước làm cục rối bết thành nùi.</p>`);
  if(sv.includes('bath')){
    let body;
    if(g.shampoo){
      const sh=x.cc.shampoos.find(s=>s.id===g.shampoo);
      body=`<p class="small">✓ Đã tắm ${x.esc(sh?.name||'')} ở ${g.temp}°C${g.cond?' + dầu xả':''}.</p>`;
    }else{
      const tiles=x.cc.shampoos.map(s=>{const q=s.item?x.stock(s.item):null;return `<button type="button" class="tile ${v.shampoo===s.id?'selected':''} ${q===0?'empty':''}" data-action="car:set" data-key="shampoo" data-val="${x.esc(s.id)}" aria-pressed="${v.shampoo===s.id}"><span class="tile-emoji">${s.emoji}</span><b>${x.esc(s.name)}</b><small>${q===null?'chai của chủ':'kho '+q}</small></button>`;}).join('');
      const tp=x.cc.temp,temp=v.temp,zone=temp>=tp.burn?'burn':temp>tp.high?'hot':temp<tp.low?'cold':'ok';
      const condItem=itemInfo(x,'conditioner'),condLocked=(x.room.level||1)<(condItem.unlock||1);
      body=`<div class="tile-grid pc-tiles">${tiles}</div>
        <p class="small muted">${x.esc(x.cc.shampoos.find(s=>s.id===v.shampoo)?.note||'Chọn sữa tắm hợp với bé: tuổi, da, loài, đơn thuốc.')}</p>
        <div class="pc-thermo ${zone}"><span>🌡️</span>${stepBtn(x,'−','temp',-1,30,45)}<b>${temp}°C</b>${stepBtn(x,'+','temp',1,30,45)}
          <small>${zone==='ok'?'Ấm vừa — thử cổ tay thấy dễ chịu':zone==='cold'?'Lạnh — bé sẽ run':zone==='hot'?'Hơi nóng':'BỎNG! Tuyệt đối không'}</small></div>
        <p class="small muted">Nước tắm thú: ${tp.low}–${tp.high}°C.</p>
        <div class="row wrap">${condLocked?`<span class="tag">🔒 Dầu xả mở ở cấp ${condItem.unlock}</span>`:setBtn(x,`✨ Dầu xả (${x.stock('conditioner')})`,'cond',!v.cond,v.cond)}
          ${x.cmd('🛁 Tắm','pc_bath',{task:t.id,shampoo:v.shampoo,temp:v.temp,cond:!!v.cond&&!condLocked},st(t,x,'bath'),!v.shampoo||off||busy)}</div>`;
    }
    html+=section('🧴 Tắm · xả · sấy',body+rinseBox(t,x)+dryBox(t,x));
  }
  if(sv.includes('nails')){
    html+=section('✂️ Cắt móng',g.nails?`<p class="small">✓ ${g.nails==='short'?'Cắt ngắn':'Tỉa đầu móng'}.</p>${g.nick?(g.stanched?'<span class="tag amber">🩹 Đã cầm máu — nhớ báo chủ</span>':x.cmd(`🩹 Rắc bột cầm máu (${x.stock('styptic')})`,'pc_styptic',{task:t.id},'danger')):''}`
      :`<div class="row wrap">${x.cmd('✂️ Tỉa đầu móng','pc_nails',{task:t.id,cut:'tip'},'ghost',wet||busy||off)}${x.cmd('✂️ Cắt thật ngắn','pc_nails',{task:t.id,cut:'short'},'ghost',wet||busy||off)}</div>
       <p class="small muted">Móng trắng thấy được tủy hồng; móng đen thì không — chỉ tỉa từng chút.${wet?' Bé còn ướt, sấy xong đã.':''}</p>`);
  }
  if(sv.includes('ears')){
    html+=section('👂 Vệ sinh tai',g.ears?`<p class="small">✓ ${g.ears==='clean'?'Đã lau tai':'Bỏ qua lau tai'}.</p>`
      :`<div class="row wrap">${x.cmd(`☁️ Lau tai (bông ${x.stock('cotton')})`,'pc_ears',{task:t.id,how:'clean'},'ghost',wet||busy||off)}${x.cmd('🙅 Bỏ qua — tai có vấn đề','pc_ears',{task:t.id,how:'skip'},'ghost',wet||busy||g.bolt)}</div>
       <p class="small muted">Tai đỏ, mùi hôi, bé đau: không lau sâu — báo chủ đưa đi bác sĩ thú y.</p>`);
  }
  return html;
}
function groomSide(t,x){
  const n=t.needs,g=t.g,f=t.facts||{},kg=f.kg??n.kg_said;
  const tier=n.species==='cat'?'groom_cat':kg<=10?'groom_s':kg<=25?'groom_m':'groom_l';
  const lines=[];
  if(n.services.includes('bath'))lines.push([`Tắm sấy (${n.species==='cat'?'mèo':kg<=10?'≤10 kg':kg<=25?'10–25 kg':'>25 kg'}${f.kg==null&&n.species==='dog'?', theo cân chủ khai':''})`,price(x,tier),g.dry_pct>0&&(!g.stopped||g.dry_pct>=100)]);
  else lines.push(['Chải lông',price(x,'brush'),g.brush]);
  if(n.services.includes('nails'))lines.push([g.nick?'Cắt móng (miễn phí nếu báo sự cố)':'Cắt móng',price(x,'nails'),!!g.nails&&!(g.nick&&(t.report||[]).includes('nick'))]);
  if(n.services.includes('ears'))lines.push(['Vệ sinh tai',price(x,'ears'),g.ears==='clean']);
  const total=lines.filter(l=>l[2]).reduce((a,l)=>a+l[1],0);
  const rows=[[t.inspected.length>=4||null,'Kiểm bé trước khi làm',`${t.inspected.length}/${x.cc.job_parts.groom.length} phần`]];
  // Same list as the server's _required: steps the owner paid for that are not done yet.
  const sv=n.services,miss=[];
  if(sv.includes('brush')&&!g.brush)miss.push('chải lông');
  if(sv.includes('bath')){if(g.shampoo==null)miss.push('tắm');else if(!(g.rinse_s>0))miss.push('xả');else if(!(g.dry_pct>0))miss.push('sấy');}
  if(sv.includes('nails')&&g.nails==null)miss.push('cắt móng');
  if(sv.includes('ears')&&g.ears==null)miss.push('xử lý tai');
  if(n.services.includes('bath'))rows.push([g.shampoo?true:null,'Tắm đúng nhiệt độ',g.temp?g.temp+'°C':''],[g.rinse_s>=x.cc.rinse_min?true:g.rinse_s>0?false:null,'Xả sạch bọt',''],[g.dry_pct>=100?true:g.dry_pct>0?false:null,'Khô tới chân lông',g.dry_pct?g.dry_pct+'%':'']);
  if(g.nick)rows.push([g.stanched,'Cầm máu móng','']);
  if(isGen(t))rows.push([g.bolt?false:g.bolts?false:null,'Bé ở yên trên bàn',g.bolts?`nhảy khỏi bàn ${g.bolts} lần`:'']);
  else rows.push([g.stress<x.cc.stress_stop,'Bé không hoảng',`stress ${g.stress}`]);
  return `<div class="pc-receipt"><h4>🧾 Phiếu thu</h4>${lines.map(([l,p,on])=>`<div class="kv ${on?'':'muted'}"><span>${x.esc(l)}</span><b>${on?x.money(p):'—'}</b></div>`).join('')}<div class="kv total"><span>Thu khi trả bé</span><b>${x.money(total)}</b></div></div>
    ${checklist(x,rows)}${reportBox(t,x)}
    ${miss.length&&!g.stopped?`<p class="small muted">Còn: ${x.esc(miss.join(', '))}</p>`:''}${g.nick&&!g.stanched?`<div class="notice amber">🩸 Móng còn rỉ máu — rắc bột cầm máu trước khi trả bé.</div>`:''}
    ${x.confirmCmd('🐾 Trả bé & thu tiền','pc_handover',{task:t.id},'Trả bé cho chủ? Chủ sẽ nghe đúng những ý bạn đã chọn để báo.',st(t,x,'handover','ghost')+' big full',!!(g.rinse||g.dry||g.bolt)||(!g.stopped&&miss.length>0)||!!(g.nick&&!g.stanched))}`;
}

/* ---------------------------------------------------------------- report to the owner */
function reportBox(t,x){
  const say=ui(x,t).say,f=t.facts||{};
  const opts=x.cc.reports.filter(r=>r.jobs.includes(t.job));
  const saved=t.report||[],same=saved.length===say.length&&saved.every(r=>say.includes(r));
  const seen=(f.signs||[]).map(s=>x.cc.signs[s]?.label).filter(Boolean);
  return `<div class="pc-report"><h4>💬 Báo lại cho chủ</h4>${seen.length?`<p class="small">Bạn đã thấy: <b>${seen.map(x.esc).join(', ')}</b></p>`:''}
    <div class="stack">${opts.map(r=>`<button type="button" class="pc-say ${say.includes(r.id)?'on':''} ${r.id==='diagnose'?'risky':''}" data-action="car:say" data-id="${x.esc(r.id)}" aria-pressed="${say.includes(r.id)}"><span>${say.includes(r.id)?'☑':'☐'}</span>${x.esc(r.text)}</button>`).join('')}</div>
    <div class="row wrap space-top">${x.cmd(same&&saved.length?'✓ Đã ghi lời báo':'📝 Ghi lời báo','pc_report',{task:t.id,say},same?'ghost small':st(t,x,'report')+' small',same)}</div>
    <p class="small muted">Thấy dấu hiệu lạ thì khuyên đi bác sĩ thú y. Không tự chẩn đoán, không khuyên thuốc.</p></div>`;
}

/* ---------------------------------------------------------------- kennel */
function kennel(x,{pick=null,task=null,species=null,kg=null}={}){
  const d=x.room.data||{},pens=d.pens||{};
  return `<div class="pc-pens">${x.cc.pens.map(p=>{
    const o=pens[p.id],locked=p.unlock>(d.level||1),wrongZone=species&&p.zone!==species,tooSmall=kg!=null&&kg>p.max_kg;
    const body=o?`<b>${SPECIES_EMOJI[o.species]} ${x.esc(o.pet)}</b><small>${x.esc(o.owner)} · về ngày ${o.until}</small><small>${o.meals} × ${o.grams} g · ${o.food==='own'?'đồ chủ gửi':'hạt tiệm'}</small>`
      :locked?`<small>🔒 mở ở cấp ${p.unlock}</small>`:`<small>Trống · ${p.zone==='dog'?'chó ≤ '+p.max_kg+' kg':'mèo'}</small>`;
    const cls=`pc-pen ${o?'busy':''} ${locked?'locked':''} ${pick===p.id?'selected':''} ${task&&(o||locked||wrongZone||tooSmall)?'no':''} ${task&&tooSmall&&!o?'small-pen':''}`;
    const head=`<div class="row spread"><b>${p.emoji} ${x.esc(p.name)}</b><span class="tag ${p.zone==='dog'?'amber':'blue'}">${p.zone==='dog'?'Khu chó':'Tầng mèo'}</span></div>`;
    return task&&!o&&!locked&&!wrongZone&&!tooSmall?`<button type="button" class="${cls}" ${cmdAttr(x,'pc_pen',{task,pen:p.id})} aria-pressed="${pick===p.id}">${head}${body}</button>`:`<div class="${cls}">${head}${body}</div>`;
  }).join('')}</div>`;
}

/* ---------------------------------------------------------------- feeding chart helper */
function chartBox(t,x,kg,known,meals,grams){
  const n=t.needs,sg=stageOf(x,n.species,n.months),g=gpk(x,n.species,kg),day=daily(x,n.species,kg,n.months);
  const bands=(x.cc.chart[n.species]||[]).map(([top,val],i,a)=>`<span class="${val===g?'on':''}">${i?`${a[i-1][0]}–`:'≤'}${top>=999?'∞':top} kg: ${val} g/kg</span>`).join('');
  return `<div class="pc-chart"><div class="pc-bands">${bands}</div>
    <p class="small">Giai đoạn <b>${x.esc(x.cc.stage_names[sg])}</b>: × ${x.cc.stage_pct[sg]}% · nên chia <b>${x.cc.meals[sg]} bữa</b>.</p>
    <p class="small">${kg} kg × ${g} g/kg × ${x.cc.stage_pct[sg]}% ≈ <b>${day} g/ngày</b>${known?'':' <span class="tag amber">theo cân chủ khai — cân lại cho chắc</span>'}</p>
    <div class="pc-bowl"><span>🥣</span><b>${meals} bữa × ${grams} g = ${meals*grams} g/ngày</b><small>lệch bảng cho phép ±${x.cc.tol}%</small></div></div>`;
}

function boardJob(t,x){
  const n=t.needs,f=t.facts||{},vv=ui(x,t),kg=f.kg??n.kg_said;
  const pens=kennel(x,{pick:t.pen,task:t.id,species:n.species,kg:f.kg??null});
  const food=['own','house'].map(k=>{
    const item=k==='house'?itemInfo(x,x.cc.house_food[n.species]):null,bad=k==='house'&&n.allergy&&item?.allergen===n.allergy;
    const off=k==='own'&&!n.food_own;
    return `<button type="button" class="tile ${vv.food===k?'selected':''} ${off?'locked':''}" data-action="car:set" data-key="food" data-val="${k}" ${off?'disabled':''}><span class="tile-emoji">${k==='own'?'🎒':item?.emoji||'🥣'}</span><b>${k==='own'?'Đồ chủ gửi':x.esc(item?.name||'Hạt của tiệm')}</b><small>${off?'chủ không gửi':k==='house'?`kho ${x.stock(x.cc.house_food[n.species])}${bad?' · ⚠️ chứa '+x.esc(x.cc.allergy_names[n.allergy]):''}`:'không trừ kho'}</small></button>`;
  }).join('');
  const plan=`<div class="tile-grid pc-tiles">${food}</div>
    <div class="row wrap pc-steppers"><span>Số bữa</span>${stepBtn(x,'−','meals',-1,1,4)}<b>${vv.meals}</b>${stepBtn(x,'+','meals',1,1,4)}
      <span>Gram/bữa</span>${stepBtn(x,'−10','grams',-10,5,900)}${stepBtn(x,'−1','grams',-1,5,900)}<b>${vv.grams}</b>${stepBtn(x,'+1','grams',1,5,900)}${stepBtn(x,'+10','grams',10,5,900)}</div>
    ${n.species==='dog'?`<div class="row wrap">${setBtn(x,vv.solo?'🚫 Chơi riêng':'🐕‍🦺 Chơi chung giờ sân','solo',!vv.solo,vv.solo)}<small class="muted">Chó ghét chó khác phải chơi riêng.</small></div>`:''}
    ${chartBox(t,x,kg,f.kg!=null,vv.meals,vv.grams)}
    <div class="row wrap">${x.cmd(t.plan?'💾 Ghi lại kế hoạch':'💾 Ghi kế hoạch ăn','pc_plan',{task:t.id,food:vv.food,meals:vv.meals,grams:vv.grams,solo:!!vv.solo},t.plan?'ghost':st(t,x,'plan'),vv.food==='own'&&!n.food_own)}
      ${t.plan?`<span class="tag green">Thẻ: ${t.plan.meals} × ${t.plan.grams} g · ${t.plan.food==='own'?'đồ chủ':'hạt tiệm'}${t.plan.solo?' · chơi riêng':''}</span>`:''}</div>`;
  return intake(t,x)+section('🏠 Chọn chuồng',pens)+section('🥣 Kế hoạch ăn',plan);
}
function boardSide(t,x){
  const n=t.needs,f=t.facts||{},key=n.species==='dog'?'board_dog':'board_cat',signs=f.signs||[],by=pickup(t,x);
  const vaxOk=f.vax?(f.vax==='valid'&&(f.vax_until==null||f.vax_until>=by)):null;
  const rows=[[vaxOk,'Sổ tiêm còn hạn tới ngày đón',f.vax?(f.vax_until!=null?`hạn tới ngày ${f.vax_until} · chủ đón ngày ${by}`:VAX[f.vax][0]):'chưa xem'],[f.kg!=null||null,'Cân bé',f.kg!=null?f.kg+' kg':''],
    [t.inspected.includes('temp')?!signs.includes('fever'):null,'Nhiệt độ bình thường',signs.includes('fever')?'đang sốt':''],
    [t.inspected.includes('body')?!signs.includes('cough'):null,'Không có dấu hiệu bệnh lây',signs.includes('cough')?'đang ho':''],
    [t.inspected.includes('mood')||null,'Biết tính khí',f.mood?MOOD[f.mood]:''],[t.pen?true:null,'Đã chọn chuồng',t.pen?pen(x,t.pen).name:''],[t.plan?true:null,'Đã ghi kế hoạch ăn',t.plan?`${t.plan.meals} × ${t.plan.grams} g`:'']];
  const reasons=[['vaccine','📒 Sổ tiêm không đủ hạn'],['sick','🤧 Bé có dấu hiệu bệnh'],['full','🚫 Hết chuồng phù hợp']];
  return `<div class="pc-receipt"><h4>🧾 Phiếu lưu trú</h4><div class="kv"><span>${n.nights} đêm × ${x.money(price(x,key))}</span><b>${x.money(n.nights*price(x,key))}</b></div></div>
    ${checklist(x,rows)}
    ${x.confirmCmd('🏠 Nhận bé & thu tiền','pc_admit',{task:t.id},'Nhận bé vào chuồng và thu tiền lưu trú?',st(t,x,'admit')+' big full',!t.pen||!t.plan||!t.inspected.includes('vaccine'))}
    <h4 class="space-top">Hoặc từ chối lịch sự</h4><div class="stack">${reasons.map(([id,l])=>x.confirmCmd(l,'pc_refuse',{task:t.id,reason:id},`Từ chối nhận bé với lý do này? Tiệm sẽ giới thiệu ${x.cc.vet} khi cần.`,'ghost small')).join('')}</div>`;
}

function medCard(t,x){
  const n=t.needs,m=n.med;if(!m)return '';
  const given=t.med?(x.cc.doses||[]).find(d=>d.id===t.med):null;
  const body=given?`<p class="small">✓ Đã cho: <b>${x.esc(given.name)}</b>, trộn vào bữa ăn.</p>`
    :`<div class="row wrap">${(x.cc.doses||[]).map(d=>x.confirmCmd(`💊 ${x.esc(d.name)}`,'pc_med',{task:t.id,dose:d.id},`Cho bé ${n.name} uống ${d.name.toLowerCase()}?`,'ghost',!t.fed)).join('')}</div>
      <p class="small muted">${t.fed?'So lời dặn của chủ với nhãn thuốc trước khi cho.':'Nhãn ghi cho cùng bữa ăn — cho bé ăn trước đã.'}</p>`;
  return section('💊 Thuốc theo đơn',`<p class="small"><b>${x.esc(m.name)}</b></p><p class="pc-label">🏷️ Nhãn: “${x.esc(m.label)}”</p>${body}`,'pc-med');
}
function feedJob(t,x){
  const n=t.needs,vv=ui(x,t);
  let bowl;
  if(t.fed)bowl=`<p class="small">✓ Đã cho ăn ${t.bowl.grams} g ${t.bowl.food==='own'?'đồ chủ gửi':'hạt của tiệm'}. ${t.ate===false?'<span class="tag danger">Bé không ăn</span>':'<span class="tag green">Bé ăn hết</span>'}</p>`;
  else{
    const food=['own','house'].map(k=>{const off=k==='own'&&n.food!=='own',item=itemInfo(x,x.cc.house_food[n.species]);
      return `<button type="button" class="tile ${vv.food===k?'selected':''} ${off?'locked':''}" data-action="car:set" data-key="food" data-val="${k}" ${off?'disabled':''}><span class="tile-emoji">${k==='own'?'🎒':item.emoji}</span><b>${k==='own'?'Đồ chủ gửi':x.esc(item.name)}</b><small>${off?'chủ không gửi':k==='house'?'kho '+x.stock(x.cc.house_food[n.species]):'để trong tủ'}</small></button>`;}).join('');
    bowl=`<div class="tile-grid pc-tiles">${food}</div>
      <div class="row wrap pc-steppers"><span>Gram/bữa</span>${stepBtn(x,'−10','grams',-10,5,900)}${stepBtn(x,'−1','grams',-1,5,900)}<b>${vv.grams}</b>${stepBtn(x,'+1','grams',1,5,900)}${stepBtn(x,'+10','grams',10,5,900)}</div>
      ${chartBox(t,x,n.kg,true,n.meals,vv.grams)}
      ${x.cmd('🥣 Cân & cho ăn','pc_feed',{task:t.id,food:vv.food,grams:vv.grams},st(t,x,'feed'),vv.food==='own'&&n.food!=='own')}`;
  }
  const care=n.species==='dog'?(t.walked?'<span class="tag green">✓ Đã dắt đi dạo</span>':x.cmd(`🦮 Dắt đi dạo (túi ${x.stock('poop_bag')})`,'pc_walk',{task:t.id},st(t,x,'walk'),!x.stock('poop_bag')))
    :(t.litter?'<span class="tag green">✓ Khay cát sạch</span>':x.cmd('🧹 Dọn khay cát','pc_litter',{task:t.id},st(t,x,'litter')));
  const treat=x.cmd(`🍪 Bánh thưởng (${x.stock('treat')})`,'pc_treat',{task:t.id},'ghost small',!x.stock('treat')||t.treats>=3);
  return intake(t,x)+section('🥣 Bát ăn',bowl)+medCard(t,x)+section('🐾 Vận động & vệ sinh',`<div class="row wrap">${care}${treat}</div>`);
}
function feedSide(t,x){
  const n=t.needs,f=t.facts||{};
  const rows=[[t.inspected.includes('bowl')||null,'Xem bát tối qua',''],[t.inspected.includes('energy')||null,'Quan sát tinh thần',''],
    [t.fed||null,'Cho ăn đúng thẻ',t.bowl?t.bowl.grams+' g':''],...(n.med?[[t.med?true:null,'Cho thuốc theo nhãn','']]:[]),[(t.walked||t.litter)||null,n.species==='dog'?'Dắt đi dạo':'Dọn khay cát',''],
    ...(f.signs||[]).map(s=>[(t.report||[]).includes('vet_'+s),'Báo chủ: '+(x.cc.signs[s]?.label||s),''])];
  return `<div class="pc-receipt"><h4>🧾 Phí chăm sóc</h4><div class="kv total"><span>Hôm nay</span><b>${x.money(price(x,'care'))}</b></div></div>
    ${checklist(x,rows)}${reportBox(t,x)}
    ${x.confirmCmd('📸 Gửi ảnh & cập nhật cho chủ','pc_handover',{task:t.id},'Gửi cập nhật cho chủ? Chủ sẽ đọc đúng những ý bạn đã chọn.',st(t,x,'handover','ghost')+' big full',!t.fed||(!!n.med&&!t.med))}`;
}

/* ---------------------------------------------------------------- adoption day */
function needsOf(a){
  return [a.yard?'🌳 Cần nhà có sân':'🏢 Ở căn hộ được',`⏰ Ở một mình tối đa ${a.alone} tiếng`,a.kids?'🧒 Quen trẻ nhỏ':'🚫 Sợ trẻ nhỏ',
    a.cats?'🐈 Sống chung mèo được':'🚫 Không hợp mèo',a.dogs?'🐕 Sống chung chó được':'🚫 Không hợp chó'];
}
function adoptJob(t,x){
  const n=t.needs,vv=ui(x,t),done=t.status==='completed'||t.status==='referred';
  const qs=`<p class="bubble npc small">“${x.esc(n.note)}”</p><div class="pc-parts">${partTiles(t,x,()=>false)}</div>`;
  const pets=(x.cc.adoptees||[]).filter(a=>n.candidates.includes(a.id)).map(a=>{
    const on=vv.pet===a.id;
    return `<button type="button" class="pc-adoptee ${on?'selected':''}" data-action="car:set" data-key="pet" data-val="${x.esc(a.id)}" aria-pressed="${on}" ${done?'disabled':''}>
      <span class="pc-adoptee-emoji" aria-hidden="true">${x.esc(a.emoji)}</span><b>${x.esc(a.name)} <small>· ${x.esc(a.age)}</small></b><small>${x.esc(a.note)}</small>
      <ul>${needsOf(a).map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul></button>`;
  }).join('');
  const none=`<button type="button" class="pc-adoptee none ${vv.pet==='none'?'selected':''}" data-action="car:set" data-key="pet" data-val="none" aria-pressed="${vv.pet==='none'}" ${done?'disabled':''}><span class="pc-adoptee-emoji" aria-hidden="true">🤝</span><b>Chưa giao bé nào</b><small>Thật lòng giải thích, hẹn ngày hội sau.</small></button>`;
  return section('🏡 Phỏng vấn nhận nuôi',qs)+section('🐾 Các bé đang chờ nhà',`<div class="pc-adoptees">${pets}${none}</div>`);
}
function adoptSide(t,x){
  const n=t.needs,vv=ui(x,t),asked=t.inspected.length,total=(x.cc.job_parts.adopt||[]).length;
  const pick=vv.pet==='none'?'chưa giao bé nào':(x.cc.adoptees||[]).find(a=>a.id===vv.pet)?.name;
  const rows=[[asked>=total?true:asked?null:false,'Hỏi đủ nếp nhà',`${asked}/${total} câu`],[vv.pet?true:null,'Chọn bé hợp nếp nhà',pick||'']];
  return `<div class="pc-receipt"><h4>🧾 Phí nhận nuôi</h4><div class="kv"><span>Tiêm phòng, triệt sản</span><b>${x.money(price(x,'adopt'))}</b></div></div>
    ${checklist(x,rows)}
    ${x.confirmCmd(vv.pet==='none'?'🤝 Hẹn ngày hội sau':'🏡 Giao bé về nhà mới','pc_match',{task:t.id,pet:vv.pet},vv.pet==='none'?`Chưa giao bé nào cho ${n.family}?`:`Giao bé ${pick||''} cho ${n.family}?`,'primary big full',!vv.pet||!asked)}
    <p class="small muted">Nhà có người dị ứng lông thì chưa giao bé nào.</p>`;
}

const JOBS={groom:[(t,x)=>intake(t,x)+groomJob(t,x),groomSide],board:[boardJob,boardSide],feed:[feedJob,feedSide],adopt:[adoptJob,adoptSide]};

function ticket(t,x){
  const who=x.npc(t.npc),n=t.needs,ci=n.case?x.cc.cases?.[n.case]:null;
  const pill=`<span class="tag blue">${JOB_ICON[t.job]||''} ${x.esc(x.cc.jobs?.[t.job]||t.job)}</span>`;
  const line=t.job==='adopt'?`<p class="small"><span class="pc-pet">🏡 ${x.esc(n.family)}</span> · ${n.candidates.length} bé đang chờ nhà</p>`
    :`<p class="small"><span class="pc-pet">${SPECIES_EMOJI[n.species]} ${x.esc(n.name)}</span> ${x.esc(n.breed)} · ${age(n.months)}</p>`;
  const reg=t.regular!=null?bookOf(t,x):null;
  const tags=[reg?`<span class="tag green">⭐ Khách quen · ${x.esc(reg.trust_name)}</span>`:'',ci?`<span class="tag amber pc-case">${x.esc(ci.emoji)} ${x.esc(ci.label)}</span>`:'',n.humid?'<span class="tag blue">🌧️ Trời ẩm</span>':''].join('');
  return `<article class="card ticket"><div class="row">${x.portrait(who,48)}<div class="grow"><div class="row spread"><h3>${x.esc(who.display_name)}</h3>${pill}</div>
    ${line}${tags?`<div class="row wrap pc-tags">${tags}</div>`:''}
    <div class="patience" title="Kiên nhẫn"><div class="bar ${t.patience<50?'low':''}"><i style="width:${t.patience}%"></i></div><small>${t.patience}%</small></div></div></div></article>`;
}
function runningTimers(t,x){
  if(t.job!=='groom'||!(t.g.rinse||t.g.dry))return '';
  return section('⏱️ Đang chạy',(t.g.rinse?rinseBox(t,x):'')+(t.g.dry?dryBox(t,x):''),'pc-running');
}

export default {
  id:'pet_care',
  css:true,
  next(t,x){
    if(t.job==='groom'&&t.g){
      if(t.g.rinse)return 'Khóa vòi khi đủ giây';
      if(t.g.dry)return 'Tắt máy sấy khi khô';
    }
    if(x?.room?.data?.desk?.ev)return 'Có chuyện ở quầy cần quyết';
    if(!t.known)return 'Nhận phiếu của chủ';
    if(t.job==='groom'){
      const g=t.g,sv=t.needs.services;
      if(g.bolt)return 'Đưa bé về bàn an toàn';
      if(g.nick&&!g.stanched)return 'Cầm máu móng ngay';
      if(g.stopped)return 'Báo chủ & trả bé';
      const todo=[[sv.includes('brush')&&!g.brush,'Chải gỡ rối'],[sv.includes('bath')&&!g.shampoo,'Tắm đúng sữa tắm, đúng nhiệt độ'],
        [sv.includes('bath')&&g.rinse_s<(x.cc.rinse_min||8),'Xả sạch bọt'],[sv.includes('bath')&&g.dry_pct<100,'Sấy khô tới chân lông'],
        [sv.includes('nails')&&!g.nails,'Cắt móng an toàn'],[sv.includes('ears')&&!g.ears,'Vệ sinh tai (hoặc bỏ qua)']].find(([need])=>need);
      if(!todo)return 'Báo chủ & trả bé';
      if((g.stress!=null&&g.stress>=(x.cc.stress_stop||80))||panicSeen(t,x))return 'Bé hoảng — dỗ dành hoặc dừng';
      if(t.inspected.length<3&&!g.brush&&!g.shampoo)return 'Kiểm bé trước khi làm';
      return todo[1];
    }
    if(t.job==='board'){
      if(!t.inspected.includes('vaccine'))return 'Xem sổ tiêm';
      if(!t.pen)return 'Chọn chuồng';
      if(!t.plan)return 'Lập kế hoạch ăn';
      return 'Nhận bé hoặc từ chối';
    }
    if(t.job==='adopt'){
      if(!t.inspected.length)return 'Phỏng vấn gia đình';
      if(t.inspected.length<(x.cc.job_parts?.adopt||[]).length)return 'Hỏi thêm về nếp nhà';
      return 'Chọn bé hợp nếp nhà';
    }
    if(!t.fed)return 'Cho ăn đúng bảng khẩu phần';
    if(t.needs.med&&!t.med)return 'Cho thuốc đúng nhãn';
    if(!(t.walked||t.litter))return t.needs.species==='dog'?'Dắt bé đi dạo':'Dọn khay cát';
    return 'Nhắn cập nhật cho chủ';
  },
  idle(x){
    const d=x.room.data||{};
    const stats=`<div class="row wrap pc-stats">${x.pill(`🐾 ${d.day_done||0} việc hôm nay`)}${d.admitted?x.pill(`🏠 ${d.admitted} bé đã lưu trú`):''}${d.stays_good?x.pill(`💚 ${d.stays_good} ngày lưu trú chăm đủ`,'green'):''}${d.reminders?x.pill(`📅 ${d.reminders} lần nhắc lịch`):''}${d.adopted?x.pill(`🏡 ${d.adopted} bé có nhà mới`,'green'):''}${d.meds?x.pill(`💊 ${d.meds} liều thuốc đúng nhãn`,'green'):''}${d.fevers?x.pill(`🌡️ ${d.fevers} bé sốt được phát hiện`,'amber'):''}${d.bolts?x.pill(`🏃 ${d.bolts} lần bé nhảy khỏi bàn`,'amber'):''}</div>`;
    return `<div class="career-job pc pc-idle">${deskCard(x)}${lastDesk(x)}${todayChip(x)}${stats}${kennelBox(x,true)}${careBoard(x)}${bookFold(x)}${foot(x)}${rules(x)}</div>`;
  },
  job(t,x){
    const desk=deskCard(x),who=x.npc(t.npc);
    if(!t.known){
      return `<div class="career-job pc">${desk}${todayChip(x)}<article class="card ticket"><div class="row">${x.portrait(who,56)}<div class="grow"><div class="row spread"><h3>${x.esc(who.display_name)}</h3><span class="tag blue">${JOB_ICON[t.job]||''} ${x.esc(x.cc.jobs?.[t.job]||t.job)}</span></div><p>“${x.esc(t.opening)}”</p></div></div>${x.cmd('📋 Nhận phiếu','ask',{task:t.id},'primary full',!!desk)}</article>
        ${kennelBox(x)}</div>`;
    }
    if(desk)return `<div class="career-job pc">${runningTimers(t,x)}${desk}${ticket(t,x)}</div>`;
    if(t.job==='groom'&&t.g.bolt)return `<div class="career-job pc">${runningTimers(t,x)}${boltAlert(t,x)}${ticket(t,x)}</div>`;
    const [main,side]=JOBS[t.job]||JOBS.groom;
    const extra=t.job==='board'||t.job==='adopt'?'':kennelBox(x);
    const n=careCount(x),care=n?`<section class="pc-card">${fold(`📋 Việc chăm sóc khác · ${n} việc`,careBoard(x))}</section>`:'';
    return `<div class="career-job pc">${lastDesk(x)}${todayChip(x)}${ticket(t,x)}${regularCard(t,x)}<div class="workbench"><section class="wb-main">${main(t,x)}${extra}
      ${care}${foot(x)}${rules(x)}</section><aside class="wb-side">${side(t,x)}</aside></div></div>`;
  },
  tick(root,x){
    root.querySelectorAll('[data-pc-timer]').forEach(el=>{
      const start=Number(el.dataset.start);if(!start)return;
      const kind=el.dataset.pcTimer,base=Number(el.dataset.base)||0,need=Number(el.dataset.need)||1,over=Number(el.dataset.over)||need*2,rate=Number(el.dataset.rate)||1;
      const value=base+Math.max(0,x.now()-start)*rate;
      const label=kind==='rinse'?`${value.toFixed(1)} giây · ${value<need?'còn bọt, xả tiếp':'nước đã trong — khóa vòi được rồi'}`
        :`${Math.floor(value)}% · ${value<need?'chân lông còn ẩm':value<over?'khô rồi — tắt máy':'quá lâu, da khô xơ!'}`;
      el.querySelector('.fill').style.width=Math.min(100,value/over*100)+'%';
      el.querySelector('.pc-timer-label').textContent=label;
      el.classList.toggle('ready',value>=need&&value<over);
      el.classList.toggle('over',value>=over);
    });
  },
  actions:{
    async set(data,el,x){
      const t=x.room.tasks.find(v=>v.id===x.ui.tid);if(!t)return;
      const vv=ui(x,t),key=data.key;
      if(!['shampoo','food','cond','solo','pet'].includes(key))return;
      vv[key]=key==='cond'||key==='solo'?data.val==='true':data.val;
      x.render();
    },
    async step(data,el,x){
      const t=x.room.tasks.find(v=>v.id===x.ui.tid);if(!t)return;
      const vv=ui(x,t),key=data.key;
      if(!['temp','meals','grams'].includes(key))return;
      vv[key]=Math.max(Number(data.min),Math.min(Number(data.max),(Number(vv[key])||0)+Number(data.delta)));
      x.render();
    },
    async say(data,el,x){
      const t=x.room.tasks.find(v=>v.id===x.ui.tid);if(!t)return;
      const vv=ui(x,t),id=data.id;
      vv.say=vv.say.includes(id)?vv.say.filter(r=>r!==id):[...vv.say,id];
      x.render();
    },
  },
  dock:[['inventory','box','Kho','Sữa tắm, hạt, bông']],
};
