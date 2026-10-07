/** Pet Care Mèo Mập — intake form, grooming table (body language, escapes, live rinse/dry bars), kennel, feeding
 *  station with medicine by the label, adoption interviews, and the surprises that walk in at the counter.
 *  Care loop: regulars' cards and trust, a daily care card per boarder, vaccine/deworming reminders, adoption follow-ups. */
import {reqList,fold,clean,tip,helpBtn,withWhy} from '../ui-kit.js';
import {stepRows,nextHint,stepCta,stepBar,finalGo,pending,firstTime,goAttrs,highlight,stepLine} from '../v4/guide.js';
import {restockFor,restockGo} from '../v4/restock.js';
import {keepBarAboveFooter} from './food_kit.js';
import {tomorrowCard} from './tomorrow_kit.js';
import * as SF from './stage_fold.js';
const JOB_ICON={groom:'🛁',board:'🏠',feed:'🥣',adopt:'🏡'};
const SPECIES_EMOJI={dog:'🐶',cat:'🐱'};
const MOOD={calm:'hiền',nervous:'nhát, dễ run',bitey:'hay cắn/cào',dog_aggressive:'ghét chó khác'};
const VAX={valid:['Còn hạn','green'],expired:['Hết hạn','danger'],none:['Không có sổ','danger']};
const HEAT={cool:'💨 Mát',warm:'🌬️ Ấm',hot:'🔥 Nóng'};
const R=v=>Math.floor(v+0.5);

const itemInfo=(x,id)=>(x.content.inventory?.items?.pet_care||[]).find(i=>i.id===id)||{id,name:id,emoji:'•'};
const price=(x,key)=>x.room.life?.prices?.[key]??x.cc.prices?.[key]??0;
const age=m=>m<12?`${m} tháng`:`${Math.floor(m/12)} tuổi`;
const pen=(x,id)=>x.cc.pens.find(p=>p.id===id)||{id,name:id,emoji:'🏠'};
const isGen=t=>!!t.gen;
const cmdAttr=(x,command,payload)=>`data-command="${x.esc(command)}" data-payload="${x.esc(JSON.stringify(payload))}"`;
const deskOpen=x=>!!x.room.data?.desk?.ev;
const pickup=(t,x)=>(x.room.day||t.day)+(t.needs?.nights||0);
/* ---------------------------------------------------------------- supplies a step takes (the server's own counts) */
/** What the shelf lacks for `need` ({item: qty}, as the server's need()/take() asks): [{id, need, have}], [] when enough. */
const lacks=(x,need)=>Object.entries(need).filter(([k,q])=>q>0&&x.stock(k)<q).map(([id,q])=>({id,need:q,have:x.stock(id)}));
/** The control that replaces a step the shelf cannot supply: "📦 Nhập khăn tắm" → the stock room
 * (an arrived crate is opened first, an order on the way shows when it comes). A guide step `go`. */
function lackGo(x,short,task,count=false){
  const g=restockGo(x.room,short,{task}),s=short[0],name=x.esc(itemInfo(x,s.id).name.toLowerCase());
  return {...g,lack:itemInfo(x,s.id).name,label:g.full||g.coming?g.label:g.ready?`📦 Mở thùng ${name} lên kệ`:`📦 Nhập ${name}${count?` · thiếu ${s.need-s.have}`:''}`};
}
// The bottom button keeps to one line ("📦 Nhập khăn tắm thú cưng"); the button at the step also says how many.
const lackBtn=(x,short,task,style='small primary')=>{const g=lackGo(x,short,task,true);return x.button(g.label,g.act,g.data||{},style+' pc-lack');};
/** Towels the dryer step takes first (pc_dry: 1 for a cat or a pet of 10 kg or less by what is known, else 2; once). */
const towelNeed=t=>{const n=t.needs,kg=t.facts?.kg??n.kg_said;return t.g.towels?0:n.species==='cat'||kg<=10?1:2;};
const dryLack=(t,x)=>lacks(x,{towel:towelNeed(t)});
/** pc_bath: one bottle of the chosen shampoo (the owner's own needs none) and one conditioner when ticked. */
const bathLack=(t,x,v,cond)=>{const sh=x.cc.shampoos.find(s=>s.id===v.shampoo);return sh?lacks(x,{...(sh.item?{[sh.item]:1}:{}),...(cond?{conditioner:1}:{})}):[];};

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

/* ---------------------------------------------------------------- compact bench (stage_fold.js): only the part of the job on now is open */
const opened=(x,t)=>SF.opened(x,t.id);
function part(x,t,now,key,title,body,{done=false,sum='',cls=''}={}){
  return SF.part(x,t.id,now,key,title,section(title,body,`${cls} pc-part-${key}`),{done,sum,cls:`pc-line-${key}`});
}
const reach=(t,x,gd)=>{SF.reach(x,t.id,gd,['table']);return gd;};

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

/* ---------------------------------------------------------------- clean layout (docs/UI_KIT.md, wave 5) */
/** The shop's "?" on the clean layout: today's theme, the house rules and the explanations folded off this screen. */
function helpQ(x){
  const m=x.room.data?.mod;
  return helpBtn('pc-help','🐾 Tiệm chăm thú cưng',[...(m?[{title:`${m.emoji} ${m.title}`,body:`<p>${x.esc(m.text)}</p>`,open:true}]:[]),
    {title:'📜 Nội quy tiệm',body:`<ul>${(x.cc.rules||[]).map(r=>`<li>${x.esc(r)}</li>`).join('')}</ul>`}],{tips:true,cls:'pc-helpq'});
}
/** The job's tag: its icon only on the clean layout (the header names the job). */
const jobTag=(x,t)=>{const name=x.cc.jobs?.[t.job]||t.job;
  return clean()?`<span class="tag blue" title="${x.esc(name)}" aria-label="${x.esc(name)}">${JOB_ICON[t.job]||'🐾'}</span>`:`<span class="tag blue">${JOB_ICON[t.job]||''} ${x.esc(name)}</span>`;};
/** A hands-on grooming button while the pet panics: dimmed but tappable with the server's own words and the
 * break as the fix (public_task can.pc_*, game/careers/pet_care.py _calm_enough). Only when nothing else holds it. */
function calmGate(t,op,html,off=false){
  const c=t.can?.[op];
  return !off&&c&&c!==true?withWhy(html,c):html;
}
/** The checks in a word or two on the clean layout (the full label stays in aria-label / title). */
const PART_WORD={vaccine:'Sổ tiêm',scale:'Cân',coat:'Lông',skin:'Da',ears:'Tai',nails:'Móng',body:'Sờ thân',gait:'Bước đi',mood:'Làm quen',
  bowl:'Bát ăn',energy:'Tinh thần',temp:'Nhiệt độ',home:'Chỗ ở',time:'Giờ vắng',kids:'Trẻ nhỏ',pets:'Thú nuôi',allergy:'Dị ứng'};
/** An explanation line: as before on the classic layout, listed in "?" on the clean one. HTML-safe text. */
const tipLine=(text,title)=>clean()?tip(text,title):`<p class="small muted">${text}</p>`;

/* ---------------------------------------------------------------- the day, the counter */
function todayChip(x){const m=x.room.data?.mod;return m?`<details class="pc-today"><summary aria-label="Hôm nay: ${x.esc(m.title)}"><span aria-hidden="true">${x.esc(m.emoji)}</span> <b>${x.esc(m.title)}</b></summary><small>${x.esc(m.text)}</small></details>`:'';}
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
function rules(x){return `<details class="pc-rules fold gd-rules"><summary>📜 Nội quy tiệm</summary><ul>${(x.cc.rules||[]).map(r=>`<li>${x.esc(r)}</li>`).join('')}</ul></details>`;}
/** On a task: the shop chores and the house rules as one folded line (the line says when the tables still need cleaning). */
function shopFold(x){
  const d=x.room.data||{};
  return `<details class="pc-rules gd-rules pc-shop"><summary${clean()?` aria-label="Tiệm: khử khuẩn, kho, nội quy · ${d.sanitized_today?'đã khử khuẩn':'chưa khử khuẩn hôm nay'}"`:''}>${clean()?`🏪 ${d.sanitized_today?'✅':'🧽 ⚠'}`:`🏪 Tiệm: khử khuẩn, kho, nội quy <small>${d.sanitized_today?'· ✅ đã khử khuẩn':'· 🧽 chưa khử khuẩn hôm nay'}</small>`}</summary>${foot(x)}<ul>${(x.cc.rules||[]).map(r=>`<li>${x.esc(r)}</li>`).join('')}</ul></details>`;
}
function kennelBox(x,open=false){
  const d=x.room.data||{},pens=d.pens||{},busy=Object.values(pens).filter(Boolean).length,free=x.cc.pens.filter(p=>p.unlock<=(d.level||1)).length;
  const todo=Object.values(d.stay||{}).reduce((a,s)=>a+(s.todo||0),0);
  const left=todo?`<span class="tag amber">${todo} việc chăm còn lại</span>`:busy?'<span class="tag green">đã chăm đủ hôm nay</span>':'';
  const sum=clean()?`<b aria-label="Khu lưu trú: ${busy}/${free} chuồng có bé${todo?`, ${todo} việc chăm còn lại`:''}">🏠 ${busy}/${free}${todo?` · <span class="tag amber">📋 ${todo}</span>`:''}</b>`:`<b>🏠 Khu lưu trú</b> <small>${busy}/${free} chuồng có bé</small> ${left}`;
  return `<details class="pc-card pc-kennel-box"${open&&todo?' open':''}><summary>${sum}</summary>${stayCards(x)}${kennel(x)}</details>`;
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
    return seen?`<div class="pc-found ${warnOf(part)?'warn':''}"><span class="tile-emoji" aria-hidden="true">${info.emoji}</span><div><b title="${x.esc(info.label)}">${x.esc(clean()?PART_WORD[part]||info.label:info.label)}</b><small>${x.esc(seen)}</small></div></div>`
      :clean()?`<button type="button" class="tile pc-part" ${cmdAttr(x,'pc_inspect',{task:t.id,part})} aria-label="${x.esc(info.label)}: chưa kiểm" title="${x.esc(info.label)}"><span class="tile-emoji" aria-hidden="true">${info.emoji}</span><b>${x.esc(PART_WORD[part]||info.label)}</b></button>`
      :`<button type="button" class="tile pc-part" ${cmdAttr(x,'pc_inspect',{task:t.id,part})}><span class="tile-emoji" aria-hidden="true">${info.emoji}</span><b>${x.esc(info.label)}</b><small>chưa kiểm</small></button>`;
  }).join('');
}
function intake(t,x,now=null){
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
  const form=clean()?cleanForm(t,x):`<div class="pc-form">${rows.map(([k,v])=>`<div class="pc-row"><span>${k}</span><b>${v}</b></div>`).join('')}<p class="bubble npc small">“${x.esc(n.note)}”</p></div>`;
  const warn=part=>(f.signs||[]).some(s=>x.cc.signs[s]?.part===part)||(part==='vaccine'&&f.vax&&(f.vax!=='valid'||(f.vax_until!=null&&f.vax_until<pickup(t,x))))
    ||(part==='mood'&&f.mood&&f.mood!=='calm')||(part==='scale'&&f.kg!=null&&job!=='feed'&&f.kg!==n.kg_said);
  const tiles=`<div class="pc-parts">${partTiles(t,x,warn)}</div>`;
  if(!now)return section(clean()?'📋 Phiếu nhận':'📋 Phiếu nhận bé',form)+section(clean()?'🔎 Kiểm tra':'🔎 Kiểm tra tận tay',tiles);
  // Once every check is done the form and the findings fold into one line with the facts the later steps need.
  const parts=x.cc.job_parts[job]||[],k=parts.filter(p=>t.inspected.includes(p)).length,warns=parts.filter(p=>t.found?.[p]&&warn(p)).length;
  const sum=[f.kg!=null?`${f.kg} kg`:job==='feed'?`${n.kg} kg`:'',f.mood?x.esc(MOOD[f.mood]||f.mood):'',job==='groom'&&n.rx?'💊 có đơn thuốc':'',f.skin==='sensitive'?'da nhạy cảm':'',job==='groom'&&n.short_nails?'✂️ chủ muốn móng thật ngắn':'',n.no_treat?'🚫 không bánh thưởng':'',`đã kiểm ${k}/${parts.length}`,warns?`⚠️ ${warns} điều lưu ý`:''].filter(Boolean).join(' · ');
  return part(x,t,now,'check',clean()?'📋 Phiếu nhận':'📋 Phiếu nhận bé & kiểm tra',form+(clean()?'':`<h5>🔎 Kiểm tra tận tay</h5>`)+tiles,{done:k===parts.length,sum});
}
/** The intake slip on the clean layout: one icon row per fact the later steps are scored on (the pet's name, breed and
 * age are in the ticket above): life stage, weight (what the owner said until it is weighed), temper, the services or
 * the stay, prescriptions, allergies, then the owner's own words. Labels are aria-labels; every fact stays visible. */
function cleanForm(t,x){
  const n=t.needs,f=t.facts||{},job=t.job,rows=[];
  const row=(icon,label,html)=>rows.push(`<li><span aria-hidden="true">${icon}</span><span class="sr-only">${label}: </span>${html}</li>`);
  row('🎂','Tuổi',x.esc(x.cc.stage_names[n.stage]||''));
  if(job==='feed')row('⚖️','Cân lúc nhận',`${n.kg} kg`);
  else row('⚖️','Cân nặng',f.kg!=null?`<b>${f.kg} kg</b>${f.kg!==n.kg_said?` <span class="tag amber">≠ ${n.kg_said}</span>`:' ✓'}`:`~${n.kg_said} kg <small class="muted">?</small>`);
  if(job!=='feed')row('💬','Tính khí',f.mood?`<b>${x.esc(MOOD[f.mood]||f.mood)}</b>${f.mood!==n.mood_said?` <span class="tag amber">≠ ${x.esc(MOOD[n.mood_said]||'')}</span>`:''}`:x.esc(MOOD[n.mood_said]||''));
  if(job==='groom'){
    row('🧾','Dịch vụ',n.services.map(s=>x.esc(x.cc.services[s]||s)).join(' · '));
    if(n.rx)row('💊','Đơn thuốc','<span class="tag blue">💊 Đơn thú y</span>');
    if(n.short_nails)row('✂️','Chủ muốn','Móng thật ngắn');
  }
  if(job==='board'){
    row('📒','Tiêm phòng',f.vax?`<span class="tag ${VAX[f.vax][1]}">${VAX[f.vax][0]}</span>`:'“đủ mũi rồi” <small class="muted">?</small>');
    row('🌙','Lưu trú',`${n.nights} đêm · đón <b>ngày ${pickup(t,x)}</b>`);row('🥣','Thức ăn',n.food_own?'Chủ gửi':'Hạt tiệm');
    if(n.allergy)row('🤧','Dị ứng',`<span class="tag danger">${x.esc(x.cc.allergy_names[n.allergy]||n.allergy)}</span>`);
  }
  if(job==='feed'){
    row('🥣','Thẻ ăn',`${n.meals} bữa · ${n.food==='own'?'đồ chủ gửi':'hạt tiệm'}`);
    const p=t.pen?pen(x,t.pen):null;row('🏠','Chuồng',p?`${p.emoji} ${x.esc(p.name)}`:'Lồng tạm');
    if(n.med)row('💊','Thuốc','<span class="tag blue">💊 Theo đơn</span>');
  }
  if(n.no_treat)row('🚫','Chế độ ăn','<span class="tag danger">Không bánh thưởng</span>');
  return `<div class="pc-form pc-form-clean"><ul class="pc-facts">${rows.join('')}</ul><p class="bubble npc small">“${x.esc(n.note)}”</p></div>`;
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
  // Clean layout: icons, only the current step keeps its word (all of them stay for screen readers).
  const word=s=>clean()&&s.id!==current?`<span class="sr-only">${x.esc(s.name)}</span>`:x.esc(s.name);
  return `<ol class="pc-steps${clean()?' pc-steps-ico':''}">${x.cc.steps.map(s=>`<li class="${!need[s.id]?'skip':state[s.id]?'done':s.id===current?'now':''}" title="${x.esc(s.name)}"><span>${state[s.id]?'✓':s.emoji}</span>${word(s)}</li>`).join('')}</ol>`;
}
function timerBar(kind,start,base,need,over,rate,label){
  return `<div class="pc-timer ${kind}" data-pc-timer="${kind}" data-start="${start||''}" data-base="${base}" data-need="${need}" data-over="${over}" data-rate="${rate}">
    <div class="pc-track"><b class="fill" style="transform:translateX(${Math.min(100,base/over*100)-100}%)"></b><em style="left:${need/over*100}%"></em></div>
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
  const label=g.dry?'Đang sấy…':`Khô ${Math.min(100,g.dry_pct)}%`,short=g.dry?[]:dryLack(t,x);
  // Out of towels: the dryer cannot start (the pet is towelled first), so the row offers the towels.
  return `<h5>💨 Lau & sấy</h5>${timerBar('dry',g.dry,g.dry_pct,100,x.cc.dry_over*100,100/need,label)}
    <div class="row wrap pc-heats">${g.dry?x.cmd('⏹️ Tắt máy sấy','pc_dry',{task:t.id,mode:'stop'},'primary'):['cool','warm','hot'].map(h=>x.cmd(HEAT[h],'pc_dry',{task:t.id,mode:'start',heat:h},(h==='hot'?'ghost small pc-no':'ghost small')+' pc-heat-'+h,!g.shampoo||!g.rinse_s||!!g.rinse||off||(short.length&&h!=='hot'))).join('')+(short.length?lackBtn(x,short,t.id):'')}</div>
    ${tipLine(`Lông ${n.coat==='long'?'dài':'ngắn'}: khoảng ${Math.round(need*10)/10} giây ở nấc ${heat==='cool'?'mát':'ấm'}${n.humid?' (trời ẩm, lâu gấp rưỡi)':''}.`,'💨 Sấy')}`;
}
function groomJob(t,x,now=new Set()){
  const n=t.needs,g=t.g,sv=n.services,v=ui(x,t),busy=g.rinse||g.dry,off=g.stopped||g.bolt;
  const wet=g.shampoo!=null&&g.dry_pct<100&&!g.stopped;
  let html=section(clean()?'🛁':'🛁 Bàn tắm tỉa',stepStrip(t,x)+calmTools(t,x),'pc-table');
  if(sv.includes('brush')){
    const done=!!g.brush&&(!!g.flea||g.shampoo!=null);
    html+=part(x,t,now,'brush','🪮 Chải & gỡ rối',done?`<p class="small">✓ Đã chải gỡ rối${g.flea?' · đã chải bọ chét':''}.</p>`:`<div class="row wrap">${calmGate(t,'pc_brush',x.cmd(g.brush?'✓ Đã chải gỡ rối':'🪮 Chải gỡ rối','pc_brush',{task:t.id,tool:'brush'},st(t,x,'brush'),g.brush||g.shampoo!=null||off),g.brush||g.shampoo!=null||off)}
    ${x.cmd(g.flea?'✓ Đã chải bọ chét':'🐜 Lược bọ chét','pc_brush',{task:t.id,tool:'flea'},'ghost',g.flea||g.shampoo!=null||off)}</div>`,
      {done:!!g.brush,sum:g.brush?`đã chải${g.flea?' · đã chải bọ chét':''}`:''});
  }
  if(sv.includes('bath')){
    let body;
    if(g.shampoo){
      const sh=x.cc.shampoos.find(s=>s.id===g.shampoo);
      body=`<p class="small">✓ Đã tắm ${x.esc(sh?.name||'')} ở ${g.temp}°C${g.cond?' + dầu xả':''}.</p>`;
    }else{
      const tiles=x.cc.shampoos.map(s=>{const q=s.item?x.stock(s.item):null;return `<button type="button" class="tile ${v.shampoo===s.id?'selected':''} ${q===0?'empty':''}" data-action="car:set" data-key="shampoo" data-val="${x.esc(s.id)}" aria-pressed="${v.shampoo===s.id}"><span class="tile-emoji">${s.emoji}</span><b>${x.esc(s.name)}</b><small>${q===null?'chai của chủ':'kho '+q}</small></button>`;}).join('');
      const tp=x.cc.temp,temp=v.temp,zone=temp>=tp.burn?'burn':temp>tp.high?'hot':temp<tp.low?'cold':'ok';
      const condItem=itemInfo(x,'conditioner'),condLocked=(x.room.level||1)<(condItem.unlock||1);
      body=`<div class="tile-grid pc-tiles pc-shampoos">${tiles}</div>
        ${tipLine(x.esc(x.cc.shampoos.find(s=>s.id===v.shampoo)?.note||'Chọn sữa tắm hợp với bé: tuổi, da, loài, đơn thuốc.'),'🧴 Sữa tắm')}
        <p class="small pc-bathfacts">${SPECIES_EMOJI[t.needs.species]||''} ${x.esc(x.cc.stage_names?.[t.needs.stage]||'')}${t.facts?.skin==='sensitive'?' · da nhạy cảm':t.facts?.skin?' · da thường':''}${t.needs.rx?' · 💊 có đơn bác sĩ':''}</p>
        <div class="pc-thermo ${zone}"><span>🌡️</span>${stepBtn(x,'−','temp',-1,30,45)}<b>${temp}°C</b>${stepBtn(x,'+','temp',1,30,45)}
          <small>${zone==='ok'?'✓ Ấm vừa':zone==='cold'?'🥶 Lạnh':zone==='hot'?'🥵 Hơi nóng':'⛔ BỎNG!'} · chuẩn ${tp.low}–${tp.high}°C</small></div>
        <div class="row wrap">${condLocked?`<span class="tag">🔒 Dầu xả mở ở cấp ${condItem.unlock}</span>`:setBtn(x,`✨ Dầu xả (${x.stock('conditioner')})`,'cond',!v.cond,v.cond)}
          ${(short=>short.length?x.cmd('🛁 Tắm','pc_bath',{},'ghost',true)+lackBtn(x,short,t.id):x.cmd('🛁 Tắm','pc_bath',{task:t.id,shampoo:v.shampoo,temp:v.temp,cond:!!v.cond&&!condLocked},st(t,x,'bath'),!v.shampoo||off||busy))(bathLack(t,x,v,!!v.cond&&!condLocked))}</div>`;
    }
    // Before the bath only the bath controls; after it the rinse and dry bars (the part stays open while they run).
    const bathDone=g.shampoo!=null&&g.dry_pct>=100&&!busy;
    const sum=g.shampoo?`${x.esc(x.cc.shampoos.find(s=>s.id===g.shampoo)?.name||'')} · ${g.temp}°C · xả ${Number(g.rinse_s).toFixed(1)} giây · khô ${Math.min(100,g.dry_pct)}%`:'';
    html+=part(x,t,busy?new Set(['bath']):now,'bath','🧴 Tắm · xả · sấy',g.shampoo?body+rinseBox(t,x)+dryBox(t,x):body,{done:bathDone,sum});
  }
  if(sv.includes('nails')){
    html+=part(x,t,g.nick&&!g.stanched?new Set(['nails']):now,'nails','✂️ Cắt móng',g.nails?`<p class="small">✓ ${g.nails==='short'?'Cắt ngắn':'Tỉa đầu móng'}.</p>${g.nick?(g.stanched?'<span class="tag amber">🩹 Đã cầm máu — nhớ báo chủ</span>':x.cmd(`🩹 Rắc bột cầm máu (${x.stock('styptic')})`,'pc_styptic',{task:t.id},'danger')):''}`
      :`<div class="row wrap pc-cuts">${calmGate(t,'pc_nails',x.cmd('✂️ Tỉa đầu móng','pc_nails',{task:t.id,cut:'tip'},'ghost pc-cut-tip',wet||busy||off),wet||busy||off)}${calmGate(t,'pc_nails',x.cmd('✂️ Cắt thật ngắn','pc_nails',{task:t.id,cut:'short'},'ghost pc-cut-short',wet||busy||off),wet||busy||off)}</div>
       <p class="small muted">${t.facts?.nails==='dark'?'⚫ Móng đen: chỉ tỉa đầu móng.':t.facts?.nails==='clear'?'⚪ Móng trắng, thấy tủy.':'⚫ Móng đen: chỉ tỉa đầu.'}${t.needs.short_nails?' Chủ muốn cắt thật ngắn.':''}${wet?' 💧 Sấy khô trước.':''}</p>`,
      {done:!!g.nails,sum:g.nails?(g.nails==='short'?'cắt ngắn':'tỉa đầu móng')+(g.nick?' · 🩹 rỉ máu':''):wet?'sấy khô trước':''});
  }
  if(sv.includes('ears')){
    html+=part(x,t,now,'ears','👂 Vệ sinh tai',g.ears?`<p class="small">✓ ${g.ears==='clean'?'Đã lau tai':'Bỏ qua lau tai'}.</p>`
      :`<div class="row wrap pc-ears-opts">${calmGate(t,'pc_ears',x.cmd(`☁️ Lau tai (bông ${x.stock('cotton')})`,'pc_ears',{task:t.id,how:'clean'},'ghost pc-ears-clean',wet||busy||off||x.stock('cotton')<2),wet||busy||off||x.stock('cotton')<2)}${x.stock('cotton')<2&&!wet&&!busy&&!off?lackBtn(x,lacks(x,{cotton:2}),t.id):''}${x.cmd('🙅 Bỏ qua — tai có vấn đề','pc_ears',{task:t.id,how:'skip'},'ghost pc-ears-skip',wet||busy||g.bolt)}</div>
       <p class="small muted">🔴 Tai đỏ, hôi: bỏ qua, báo chủ đi thú y.</p>`,
      {done:!!g.ears,sum:g.ears?(g.ears==='clean'?'đã lau tai':'bỏ qua lau tai'):''});
  }
  return html;
}
function groomSide(t,x,gd){
  const n=t.needs,g=t.g,f=t.facts||{},kg=f.kg??n.kg_said;
  const tier=n.species==='cat'?'groom_cat':kg<=10?'groom_s':kg<=25?'groom_m':'groom_l';
  const lines=[];
  // The same lines the server charges (_groom_charge): a bath that was dried, otherwise the brushing done.
  const bathed=n.services.includes('bath')&&g.dry_pct>0&&(!g.stopped||g.dry_pct>=100);
  if(n.services.includes('bath'))lines.push([`Tắm sấy (${n.species==='cat'?'mèo':kg<=10?'≤10 kg':kg<=25?'10–25 kg':'>25 kg'}${f.kg==null&&n.species==='dog'?', theo cân chủ khai':''})`,price(x,tier),bathed]);
  if(!bathed&&(g.brush||!n.services.includes('bath')))lines.push(['Chải lông',price(x,'brush'),!!g.brush]);
  if(n.services.includes('nails'))lines.push([g.nick?'Cắt móng (miễn phí nếu báo sự cố)':'Cắt móng',price(x,'nails'),!!g.nails&&!(g.nick&&(t.report||[]).includes('nick'))]);
  if(n.services.includes('ears'))lines.push(['Vệ sinh tai',price(x,'ears'),g.ears==='clean']);
  const total=lines.filter(l=>l[2]).reduce((a,l)=>a+l[1],0);
  const status=isGen(t)?(g.bolts?`<p class="small muted">🏃 Bé đã nhảy khỏi bàn ${g.bolts} lần.</p>`:''):g.stress>=x.cc.stress_stop?`<p class="small muted">💓 Stress ${g.stress}: bé đang hoảng.</p>`:'';
  return receiptFold('🧾 Phiếu thu',`${lines.map(([l,p,on])=>`<div class="kv ${on?'':'muted'}"><span>${x.esc(l)}</span><b>${on?x.money(p):'—'}</b></div>`).join('')}<div class="kv total"><span>Thu khi trả bé</span><b>${x.money(total)}</b></div>`,x.money(total))
    +todoFold(x,gd)+status+reportBox(t,x,gd)
    +(g.nick&&!g.stanched?`<div class="notice amber">🩸 Móng còn rỉ máu — rắc bột cầm máu trước khi trả bé.</div>`:'');
}
/** The receipt as one line ("🧾 Phiếu thu · 120 xu ▸"), open on a tap. */
function receiptFold(title,body,total){return `<details class="pc-receipt pc-fold-receipt"><summary><b>${title}</b><b class="pc-sum-total">${total}</b></summary>${body}</details>`;}
/** The checklist (the same steps as the bottom bar) folded: "📝 Việc cần làm · còn 3 ▸". */
function todoFold(x,gd,label='Việc cần làm'){
  const steps=(gd.steps||[]).filter(Boolean),k=steps.filter(s=>s.ok!==true).length;
  if(clean())return steps.length?stepRows(x,steps,label,{chip:true}):'';
  return `<details class="pc-todo-fold"><summary>📝 ${x.esc(label)} <small>· ${k?`còn ${k}`:'xong hết'}/${steps.length}</small></summary>${stepRows(x,steps,label)}</details>`;
}

/* ---------------------------------------------------------------- report to the owner */
function reportBox(t,x,gd){
  const say=ui(x,t).say,f=t.facts||{};
  const opts=x.cc.reports.filter(r=>r.jobs.includes(t.job));
  const saved=t.report||[],same=saved.length===say.length&&saved.every(r=>say.includes(r));
  const seen=(f.signs||[]).map(s=>x.cc.signs[s]?.label).filter(Boolean);
  const body=`${seen.length?`<p class="small">Bạn đã thấy: <b>${seen.map(x.esc).join(', ')}</b></p>`:''}
    <div class="stack">${opts.map(r=>`<button type="button" class="pc-say ${say.includes(r.id)?'on':''} ${r.id==='diagnose'?'risky':''}" data-action="car:say" data-id="${x.esc(r.id)}" aria-pressed="${say.includes(r.id)}"><span>${say.includes(r.id)?'☑':'☐'}</span>${x.esc(r.text)}</button>`).join('')}</div>
    <div class="row wrap space-top">${x.cmd(same&&saved.length?'✓ Đã ghi lời báo':'📝 Ghi lời báo','pc_report',{task:t.id,say},same?'ghost small':st(t,x,'report')+' small',same)}</div>
    ${tipLine('Chỉ chọn điều đã quan sát hoặc thực sự xảy ra, không chọn hết. “Cắt móng bị chảy máu” chỉ khi có sự cố; “Dừng dịch vụ” chỉ khi bạn đã dừng. Chọn xong bấm Ghi lời báo trước khi trả bé.','💬 Báo lại cho chủ')}
    <p class="small muted">🩺 Lạ thì khuyên đi thú y, không tự đoán bệnh.</p>`;
  // Open at the report step (or whenever the player opened it); before and after that it is one line.
  const now=gd?.now||new Set(['report']);
  if(now.has('report')||opened(x,t).report)return `<div class="pc-report"><h4>💬 Báo lại cho chủ</h4>${body}</div>`;
  const sum=saved.length&&same?`đã ghi ${saved.length} ý`:say.length?`đang chọn ${say.length} ý`:seen.length?`⚠️ đã thấy ${seen.length} điều cần báo`:'làm xong rồi báo';
  return `<div class="pc-report">${part(x,t,now,'report','💬 Báo lại cho chủ',body,{done:!!saved.length&&same,sum:x.esc(sum)})}</div>`;
}

/* ---------------------------------------------------------------- kennel */
function kennel(x,{pick=null,task=null,species=null,kg=null}={}){
  const d=x.room.data||{},pens=d.pens||{};
  // Empty pens above the shop's level collapse into one "🔒 N món mở ở cấp X–Y" chip.
  const shut=x.cc.pens.filter(p=>p.unlock>(d.level||1)&&!pens[p.id]);
  return `<div class="pc-pens">${x.cc.pens.filter(p=>!shut.includes(p)).map(p=>{
    const o=pens[p.id],locked=p.unlock>(d.level||1),wrongZone=species&&p.zone!==species,tooSmall=kg!=null&&kg>p.max_kg;
    const body=o?`<b>${SPECIES_EMOJI[o.species]} ${x.esc(o.pet)}</b><small>${x.esc(o.owner)} · về ngày ${o.until}</small><small>${o.meals} × ${o.grams} g · ${o.food==='own'?'đồ chủ gửi':'hạt tiệm'}</small>`
      :locked?`<small>🔒 mở ở cấp ${p.unlock}</small>`:`<small>Trống · ${p.zone==='dog'?'chó ≤ '+p.max_kg+' kg':'mèo'}</small>`;
    const cls=`pc-pen pc-pen-${p.id} ${o?'busy':''} ${locked?'locked':''} ${pick===p.id?'selected':''} ${task&&(o||locked||wrongZone||tooSmall)?'no':''} ${task&&tooSmall&&!o?'small-pen':''}`;
    const head=`<div class="row spread"><b>${p.emoji} ${x.esc(p.name)}</b><span class="tag ${p.zone==='dog'?'amber':'blue'}">${p.zone==='dog'?'Khu chó':'Tầng mèo'}</span></div>`;
    return task&&!o&&!locked&&!wrongZone&&!tooSmall?`<button type="button" class="${cls}" ${cmdAttr(x,'pc_pen',{task,pen:p.id})} aria-pressed="${pick===p.id}">${head}${body}</button>`:`<div class="${cls}">${head}${body}</div>`;
  }).join('')}</div>${SF.lockChip(shut.map(p=>p.unlock),'pc-lock')}`;
}

/* ---------------------------------------------------------------- feeding chart helper */
function chartBox(t,x,kg,known,meals,grams){
  const n=t.needs,sg=stageOf(x,n.species,n.months),g=gpk(x,n.species,kg),day=daily(x,n.species,kg,n.months);
  const bands=(x.cc.chart[n.species]||[]).map(([top,val],i,a)=>`<span class="${val===g?'on':''}">${i?`${a[i-1][0]}–`:'≤'}${top>=999?'∞':top} kg: ${val} g/kg</span>`).join('');
  return `<div class="pc-chart"><div class="pc-bands">${bands}</div>
    <p class="small">Giai đoạn <b>${x.esc(x.cc.stage_names[sg])}</b>: × ${x.cc.stage_pct[sg]}% · nên chia <b>${x.cc.meals[sg]} bữa</b>.</p>
    <p class="small">${kg} kg × ${g} g/kg × ${x.cc.stage_pct[sg]}% ≈ <b>${day} g/ngày</b> → chia ${meals} bữa ≈ <b>${Math.max(5,R(day/meals))} g/bữa</b>${known?'':' <span class="tag amber">theo cân chủ khai — cân lại cho chắc</span>'}</p>
    <div class="pc-bowl"><span>🥣</span><b>${meals} bữa × ${grams} g = ${meals*grams} g/ngày</b><small>lệch bảng cho phép ±${x.cc.tol}%</small></div></div>`;
}

function boardJob(t,x,now=new Set()){
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
  const p=t.pen?pen(x,t.pen):null;
  return intake(t,x,now)+part(x,t,now,'pen','🏠 Chọn chuồng',pens,{done:!!t.pen,sum:p?`${x.esc(p.emoji)} ${x.esc(p.name)}`:''})
    +part(x,t,now,'plan','🥣 Kế hoạch ăn',plan,{done:!!t.plan,sum:t.plan?`${t.plan.meals} × ${t.plan.grams} g · ${t.plan.food==='own'?'đồ chủ':'hạt tiệm'}${t.plan.solo?' · chơi riêng':''}`:'',cls:'pc-plan'});
}
function boardSide(t,x,gd){
  const n=t.needs,f=t.facts||{},key=n.species==='dog'?'board_dog':'board_cat',signs=f.signs||[],by=pickup(t,x);
  const vaxOk=f.vax?(f.vax==='valid'&&(f.vax_until==null||f.vax_until>=by)):null;
  // Each row checks one thing; an unchecked one is a tap that checks it (or points at the control).
  const look=part=>t.inspected.includes(part)?null:{cmd:'pc_inspect',payload:{task:t.id,part}};
  const rows=[{ok:vaxOk,label:'Sổ tiêm còn hạn tới ngày đón',note:f.vax?(f.vax_until!=null?`hạn tới ngày ${f.vax_until} · chủ đón ngày ${by}`:VAX[f.vax][0]):'chưa xem',go:look('vaccine')},
    {ok:f.kg!=null||null,label:'Cân bé',note:f.kg!=null?f.kg+' kg':'',go:look('scale')},
    {ok:t.inspected.includes('temp')?!signs.includes('fever'):null,label:'Nhiệt độ bình thường',note:signs.includes('fever')?'đang sốt':'',go:look('temp')},
    {ok:t.inspected.includes('body')?!signs.includes('cough'):null,label:'Không có dấu hiệu bệnh lây',note:signs.includes('cough')?'đang ho':'',go:look('body')},
    {ok:t.inspected.includes('mood')||null,label:'Biết tính khí',note:f.mood?MOOD[f.mood]:'',go:look('mood')},
    {ok:t.inspected.includes('gait')||null,label:'Xem dáng đi',note:signs.includes('limp')?'đi khập khiễng':'',go:look('gait')},
    {ok:t.pen?true:null,label:'Đã chọn chuồng',note:t.pen?pen(x,t.pen).name:'',go:t.pen?null:{sel:'.pc-pens'}},
    {ok:t.plan?true:null,label:'Đã ghi kế hoạch ăn',note:t.plan?`${t.plan.meals} × ${t.plan.grams} g`:'',go:t.plan?null:{sel:'.pc-plan'}}];
  const reasons=[['vaccine','📒 Sổ tiêm không đủ hạn'],['sick','🤧 Bé có dấu hiệu bệnh'],['full','🚫 Hết chuồng phù hợp']];
  const k=rows.filter(r=>r.ok!==true).length;
  const refuse=`<div class="stack pc-refuse">${reasons.map(([id,l])=>x.confirmCmd(l,'pc_refuse',{task:t.id,reason:id},`Từ chối nhận bé với lý do này? Tiệm sẽ giới thiệu ${x.cc.vet} khi cần.`,'ghost small')).join('')}</div>`;
  return receiptFold('🧾 Phiếu lưu trú',`<div class="kv"><span>${n.nights} đêm × ${x.money(price(x,key))}</span><b>${x.money(n.nights*price(x,key))}</b></div>`,x.money(n.nights*price(x,key)))
    +`<details class="pc-todo-fold"><summary>📝 Kiểm trước khi nhận <small>· ${k?`còn ${k}`:'xong hết'}/${rows.length}</small></summary>${stepRows(x,rows.map(r=>r.go?.sel?{...r,go:{act:'car:sfOpen',data:{key:r.go.sel==='.pc-pens'?'pen':'plan',sel:r.go.sel}}}:r),'Kiểm trước khi nhận')}</details>`
    +part(x,t,gd?.now||new Set(),'refuse','🙏 Hoặc từ chối lịch sự',refuse,{sum:'sổ tiêm, bệnh, hết chuồng'});
}

function medCard(t,x,now=null){
  const n=t.needs,m=n.med;if(!m)return '';
  const given=t.med?(x.cc.doses||[]).find(d=>d.id===t.med):null;
  const body=given?`<p class="small">✓ Đã cho: <b>${x.esc(given.name)}</b>, trộn vào bữa ăn.</p>`
    :`<div class="row wrap">${(x.cc.doses||[]).map(d=>x.confirmCmd(`💊 ${x.esc(d.name)}`,'pc_med',{task:t.id,dose:d.id},`Cho bé ${n.name} uống ${d.name.toLowerCase()}?`,'ghost',!t.fed)).join('')}</div>
      <p class="small muted">${t.fed?'So lời dặn của chủ với nhãn thuốc trước khi cho.':'Nhãn ghi cho cùng bữa ăn — cho bé ăn trước đã.'}</p>`;
  const card=`<p class="small"><b>${x.esc(m.name)}</b></p><p class="pc-label">🏷️ Nhãn: “${x.esc(m.label)}”</p>${body}`;
  return now?part(x,t,now,'med','💊 Thuốc theo đơn',card,{done:!!given,sum:given?`đã cho ${x.esc(given.name.toLowerCase())}`:x.esc(m.name),cls:'pc-med'}):section('💊 Thuốc theo đơn',card,'pc-med');
}
function feedJob(t,x,now=new Set()){
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
  const treat=x.cmd(`🍪 Bánh thưởng (${x.stock('treat')})`,'pc_treat',{task:t.id},'ghost small',!x.stock('treat')||t.treats>=3)+(n.no_treat?'<span class="tag danger">Chủ dặn: không bánh thưởng</span>':'');
  const chore=!!(t.walked||t.litter);
  return intake(t,x,now)+part(x,t,now,'feed','🥣 Bát ăn',bowl,{done:!!t.fed,sum:t.fed?`${t.bowl.grams} g ${t.bowl.food==='own'?'đồ chủ gửi':'hạt tiệm'}${t.ate===false?' · bé không ăn':''}`:'',cls:'pc-feedbox'})
    +medCard(t,x,now)+part(x,t,now,'chore','🐾 Vận động & vệ sinh',`<div class="row wrap">${care}${treat}</div>`,{done:chore,sum:chore?(n.species==='dog'?'đã dắt đi dạo':'khay cát sạch'):''});
}
function feedSide(t,x,gd){
  const f=t.facts||{},said=t.report||[],open=gd.now?.has('report')||opened(x,t).report;
  const signs=(f.signs||[]).map(s=>({ok:said.includes('vet_'+s)||null,label:'Báo chủ: '+(x.cc.signs[s]?.label||s),go:said.includes('vet_'+s)?null:open?{sel:'.pc-report .stack'}:{act:'car:sfOpen',data:{key:'report',sel:'.pc-report .stack'}}}));
  return receiptFold('🧾 Phí chăm sóc',`<div class="kv total"><span>Hôm nay</span><b>${x.money(price(x,'care'))}</b></div>`,x.money(price(x,'care')))
    +todoFold(x,{steps:[...gd.steps,...signs]})+reportBox(t,x,gd);
}

/* ---------------------------------------------------------------- adoption day */
function needsOf(a){
  return [a.yard?'🌳 Cần nhà có sân':'🏢 Ở căn hộ được',`⏰ Ở một mình tối đa ${a.alone} tiếng`,a.kids?'🧒 Quen trẻ nhỏ':'🚫 Sợ trẻ nhỏ',
    a.cats?'🐈 Sống chung mèo được':'🚫 Không hợp mèo',a.dogs?'🐕 Sống chung chó được':'🚫 Không hợp chó'];
}
function adoptJob(t,x,now=new Set()){
  const n=t.needs,vv=ui(x,t),done=t.status==='completed'||t.status==='referred';
  const qs=`<p class="bubble npc small">“${x.esc(n.note)}”</p><div class="pc-parts">${partTiles(t,x,()=>false)}</div>`;
  const pets=(x.cc.adoptees||[]).filter(a=>n.candidates.includes(a.id)).map(a=>{
    const on=vv.pet===a.id;
    return `<button type="button" class="pc-adoptee ${on?'selected':''}" data-action="car:set" data-key="pet" data-val="${x.esc(a.id)}" aria-pressed="${on}" ${done?'disabled':''}>
      <span class="pc-adoptee-emoji" aria-hidden="true">${x.esc(a.emoji)}</span><b>${x.esc(a.name)} <small>· ${x.esc(a.age)}</small></b><small>${x.esc(a.note)}</small>
      <ul>${needsOf(a).map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul></button>`;
  }).join('');
  const none=`<button type="button" class="pc-adoptee none ${vv.pet==='none'?'selected':''}" data-action="car:set" data-key="pet" data-val="none" aria-pressed="${vv.pet==='none'}" ${done?'disabled':''}><span class="pc-adoptee-emoji" aria-hidden="true">🤝</span><b>Chưa giao bé nào</b><small>Thật lòng giải thích, hẹn ngày hội sau.</small></button>`;
  const parts=x.cc.job_parts.adopt||[],k=parts.filter(p=>t.inspected.includes(p)).length;
  // The family's answers stay in sight next to the pets while choosing (the interview part folds once done).
  const said=parts.filter(p=>t.found?.[p]).map(p=>{const i=x.cc.parts[p]||{emoji:'🔎',label:p};return `<span class="tag">${x.esc(i.emoji)} ${x.esc(t.found[p])}</span>`;}).join('');
  const recap=k?`<div class="pc-answers"><p class="small"><b>Nhà gia đình:</b> “${x.esc(n.note)}”</p><div class="row wrap">${said}</div></div>`:'';
  return part(x,t,now,'check','🏡 Phỏng vấn nhận nuôi',qs,{done:k===parts.length,sum:`đã hỏi ${k}/${parts.length}`})+section('🐾 Các bé đang chờ nhà',`${recap}<div class="pc-adoptees">${pets}${none}</div>`);
}
function adoptSide(t,x,gd){
  return receiptFold('🧾 Phí nhận nuôi',`<div class="kv"><span>Tiêm phòng, triệt sản</span><b>${x.money(price(x,'adopt'))}</b></div>`,x.money(price(x,'adopt')))+todoFold(x,gd);
}

/* ---------------------------------------------------------------- next steps (guide.js)
 * One list per task drives the header hint, the tappable rows and the bottom bar. On a first task every
 * choice has a one-tap step for the right answer (from what the screen already shows: the ticket, the
 * checks), so the glowing bottom button always does it;
 * later tasks point at the choice and keep the challenge. Timers get a live button that turns off the tap
 * or the dryer at the right moment (pressed early it only says how long is left). */
const RINSE_PAD=0.5,DRY_PAD=6;          // stop a little past the line: server clock and rounding
const liveRinse=(t,x)=>t.g.rinse_s+(t.g.rinse?Math.max(0,x.now()-t.g.rinse):0);
const liveDry=(t,x)=>t.g.dry_pct+(t.g.dry?Math.max(0,x.now()-t.g.dry)*100/dryNeed(t,x,t.g.heat||'warm'):0);
const timerReady=(kind,t,x)=>kind==='rinse'?liveRinse(t,x)>=x.cc.rinse_min+RINSE_PAD:liveDry(t,x)>=100+DRY_PAD;
function liveLabel(kind,t,x){
  if(kind==='rinse'){const left=x.cc.rinse_min+RINSE_PAD-liveRinse(t,x);return left>0?`⏳ Đang xả… còn ${Math.max(0.1,left).toFixed(1)} giây`:'🚰 Khóa vòi · nước đã trong';}
  const v=liveDry(t,x);
  return v<100+DRY_PAD?`⏳ Đang sấy… khô ${Math.floor(Math.min(99,v))}%`:v<x.cc.dry_over*100?'⏹️ Tắt máy sấy · khô rồi':'⏹️ Tắt máy sấy ngay!';
}
/** Mood band the pet shows: the cue words on new tasks, the stress number on old ones. */
function bandOf(t,x){
  const g=t.g;
  if(!isGen(t))return (x.cc.bands||[]).find(b=>(g.stress||0)<=b.top)?.id||'relaxed';
  const book=x.cc.cues?.[t.needs.species]||{},cues=t.cues||[];
  return ['panic','stressed','uneasy'].find(b=>(book[b]||[]).some(c=>cues.includes(c)))||'relaxed';
}
const runnerSeen=t=>/chực nhảy/.test([...(t.cues||[]),t.found?.mood||''].join(' ').normalize('NFC'));
const knownBitey=t=>t.needs.mood_said==='bitey'||t.facts?.mood==='bitey';
function rightShampoo(t,x){
  const n=t.needs,f=t.facts||{},have=id=>{const s=x.cc.shampoos.find(v=>v.id===id);return !!s&&(!s.item||x.stock(s.item)>0);};
  const pool=n.rx?['medicated']:n.stage==='young'?['puppy','sensitive']:n.species==='cat'||f.skin==='sensitive'?['sensitive','puppy']:['normal','sensitive','puppy'];
  return pool.find(have)||pool[0];
}
const rightHeat=t=>t.needs.flat?'cool':'warm';
const rightCut=t=>t.facts?.nails==='clear'&&t.needs.short_nails?'short':'tip';
const rightEars=t=>(t.facts?.signs||[]).includes('ears')?'skip':'clean';
function rightSay(t,x){
  const ok=new Set(x.cc.reports.filter(r=>r.jobs.includes(t.job)).map(r=>r.id)),g=t.g||{};
  return ['done',...(t.facts?.signs||[]).map(s=>'vet_'+s),g.nick?'nick':'',g.stopped?'stopped':''].filter(id=>ok.has(id));
}
/** Same list as the server's _required: steps the owner paid for that are not done yet. */
function groomMiss(t){
  const g=t.g,sv=t.needs.services,miss=[];
  if(sv.includes('brush')&&!g.brush)miss.push('chải lông');
  if(sv.includes('bath')){if(g.shampoo==null)miss.push('tắm');else if(!(g.rinse_s>0))miss.push('xả');else if(!(g.dry_pct>0))miss.push('sấy');}
  if(sv.includes('nails')&&g.nails==null)miss.push('cắt móng');
  if(sv.includes('ears')&&g.ears==null)miss.push('xử lý tai');
  return miss;
}
/** Chart portion for a meal (the same maths the chart box shows). */
function portionOf(t,x){
  const n=t.needs,kg=t.job==='feed'?n.kg:(t.facts?.kg??n.kg_said),meals=t.job==='feed'?n.meals:x.cc.meals[stageOf(x,n.species,n.months)];
  return {meals,grams:Math.max(5,R(daily(x,n.species,kg,n.months)/meals))};
}
const within=(g,target,tol=10)=>Math.abs(g-target)*100<=tol*target;

function inspectStep(t,x,label){
  const parts=x.cc.job_parts[t.job]||[],left=parts.filter(p=>!t.inspected.includes(p)),p=left[0],info=p&&(x.cc.parts[p]||{emoji:'🔎',label:p});
  const k=parts.length-left.length;
  return {stage:'check',ok:left.length?null:true,label:`${label} (${k}/${parts.length})`,go:p?{cmd:'pc_inspect',payload:{task:t.id,part:p},label:`${info.emoji} ${x.esc(info.label)} <small>· ${k+1}/${parts.length}</small>`}:null};
}
const greetStep=t=>t.regular!=null&&!t.greeted?[{stage:'check',ok:null,label:'Chào bé khách quen, hỏi thăm lần trước',go:{cmd:'pc_greet',payload:{task:t.id},label:'👋 Gọi tên bé, hỏi thăm'}}]:[];
function reportStep(t,x,first){
  const vv=ui(x,t),saved=t.report||[],done=saidDone(t,x),signs=(t.facts?.signs||[]).length;
  const go=done?null:first?{act:'car:report',data:{say:rightSay(t,x).join(',')},label:`💬 Báo chủ: kể các bước${signs?', khuyên đi thú y':''}`}
    :vv.say.length?{cmd:'pc_report',payload:{task:t.id,say:vv.say},label:'📝 Ghi lời báo cho chủ'}:{sel:'.pc-report .stack',label:'💬 Chọn ý báo lại cho chủ'};
  return {stage:'report',ok:done||null,label:'Báo lại cho chủ',note:saved.length?`${saved.length} ý`:'',go};
}
function timerSteps(t,x){
  const g=t.g,live=kind=>`<span data-pc-live="${kind}">${liveLabel(kind,t,x)}</span>`;
  return [g.rinse&&{stage:'bath',ok:null,label:`Xả đủ ${x.cc.rinse_min} giây rồi khóa vòi`,go:{act:'car:tapoff',data:{kind:'rinse'},label:live('rinse')}},
    g.dry&&{stage:'bath',ok:null,label:'Sấy khô tới chân lông rồi tắt máy',go:{act:'car:tapoff',data:{kind:'dry'},label:live('dry')}}].filter(Boolean);
}
/** Finishing command: asks what is still open when finishing early, else the usual question. */
function finish(steps,cmd,payload,question){
  return pending(steps)?finalGo(steps,cmd,payload,{question,confirm:true}):{cmd,payload,confirm:question};
}

function groomGuide(t,x){
  const n=t.needs,g=t.g,sv=n.services,v=ui(x,t),first=firstTime(x),id=t.id,task={task:id};
  if(g.bolt)return {steps:[...timerSteps(t,x),{stage:'table',ok:null,label:'Bé nhảy khỏi bàn: đưa bé về an toàn',go:first?{cmd:'pc_catch',payload:{task:id,how:'corner'},label:'🚪 Đóng cửa, ngồi thấp, gọi tên nhỏ nhẹ'}:{sel:'.pc-bolt .pc-opts'}}]};
  const steps=[...timerSteps(t,x)],off=!!(g.rinse||g.dry);
  if(g.nick&&!g.stanched)steps.push({stage:'nails',ok:null,label:'Móng rỉ máu: rắc bột cầm máu',go:{cmd:'pc_styptic',payload:task,label:`🩹 Rắc bột cầm máu (${x.stock('styptic')})`}});
  steps.push(...greetStep(t),inspectStep(t,x,'Kiểm bé trước khi làm'));
  const work=[];
  if(!g.stopped){
    if(isGen(t)&&!g.loop&&runnerSeen(t))work.push({stage:'table',ok:null,label:'Bé hay nhảy khỏi bàn: đeo vòng giữ',go:{cmd:'pc_loop',payload:task,label:'🔗 Đeo vòng giữ cổ trên bàn'}});
    if(sv.includes('brush'))work.push({stage:'brush',ok:g.brush?true:g.shampoo!=null?false:null,label:'Chải gỡ rối trước khi tắm',go:!g.brush&&g.shampoo==null?{cmd:'pc_brush',payload:{task:id,tool:'brush'},label:'🪮 Chải gỡ rối'}:null});
    const bathed=g.shampoo!=null,dried=g.dry_pct>=100,wet=bathed&&!dried;
    if(sv.includes('bath')){
      const right=rightShampoo(t,x),sh=sid=>x.cc.shampoos.find(s=>s.id===sid)||{name:sid,emoji:'🧴'},tp=x.cc.temp;
      work.push({stage:'bath',ok:bathed||(v.shampoo?(first?v.shampoo===right:true):null),label:'Chọn sữa tắm hợp với bé',note:!bathed&&v.shampoo?sh(v.shampoo).name:'',
        go:bathed?null:first?{act:'car:set',data:{key:'shampoo',val:right},label:`${sh(right).emoji} Chọn ${x.esc(sh(right).name)}`}:{sel:'.pc-shampoos',label:'🧴 Chọn sữa tắm hợp với bé'}});
      work.push({stage:'bath',ok:bathed||(v.temp>=tp.low&&v.temp<=tp.high)||(v.temp>=tp.burn?false:null),label:`Pha nước ấm ${tp.low}–${tp.high}°C`,note:bathed?`${g.temp}°C`:`đang ${v.temp}°C`,
        go:bathed?null:first?{act:'car:temp',data:{val:tp.low+1},label:`🌡️ Pha nước ${tp.low+1}°C`}:{sel:'.pc-thermo',label:`🌡️ Chỉnh nước ${tp.low}–${tp.high}°C`}});
      const condItem=itemInfo(x,'conditioner'),cond=!!v.cond&&(x.room.level||1)>=(condItem.unlock||1);
      const bl=bathed||!v.shampoo?[]:bathLack(t,x,v,cond);
      work.push({stage:'bath',ok:bathed||null,label:'Tắm cho bé',go:bathed||!v.shampoo||off?null:bl.length?lackGo(x,bl,id):{cmd:'pc_bath',payload:{task:id,shampoo:v.shampoo,temp:v.temp,cond},label:'🛁 Tắm'}});
      const rinsed=g.rinse_s>=x.cc.rinse_min;
      if(!g.rinse)work.push({stage:'bath',ok:rinsed?true:g.dry_pct>0||g.dry?false:null,label:`Xả sạch bọt (${x.cc.rinse_min} giây)`,note:g.rinse_s?`${Number(g.rinse_s).toFixed(1)} giây`:'',
        go:!rinsed&&bathed&&!g.dry&&!g.dry_pct?{cmd:'pc_rinse',payload:{task:id,mode:'start'},label:g.rinse_s?'🚿 Mở vòi xả thêm':'🚿 Mở vòi xả'}:null});
      const heat=rightHeat(t);
      if(!g.dry)work.push({stage:'bath',ok:dried||null,label:'Sấy khô tới chân lông',note:g.dry_pct?`${Math.min(100,g.dry_pct)}%`:'',
        go:dried||!bathed||!(g.rinse_s>0)||g.rinse?null:dryLack(t,x).length?lackGo(x,dryLack(t,x),id):first?{cmd:'pc_dry',payload:{task:id,mode:'start',heat},label:`💨 Bật máy sấy nấc ${heat==='cool'?'mát':'ấm'}`}:{sel:'.pc-heats',label:'💨 Chọn nấc sấy'}});
    }
    const hands=sv.includes('nails')||(sv.includes('ears')&&rightEars(t)==='clean'&&g.ears!=='skip');
    if(hands&&n.species==='dog'&&knownBitey(t)){
      const hs=sv.includes('nails')?'nails':'ears';
      work.push({stage:hs,ok:g.consent||null,label:'Hỏi chủ đồng ý rọ mõm mềm',go:g.consent?null:{cmd:'pc_consent',payload:task,label:'🙋 Hỏi chủ đồng ý rọ mõm'}});
      work.push({stage:hs,ok:g.muzzle||null,label:'Đeo rọ mõm trước khi cầm chân bé',go:!g.muzzle&&g.consent&&!wet&&!off?{cmd:'pc_muzzle',payload:task,label:'🧢 Đeo rọ mõm mềm'}:null});
    }
    if(sv.includes('nails')&&n.species==='cat'&&knownBitey(t))
      work.push({stage:'nails',ok:g.wrap||null,label:'Quấn khăn giữ bé trước khi cắt móng',go:!g.wrap&&!wet&&!off?(x.stock('towel')?{cmd:'pc_calm',payload:{task:id,how:'wrap'},label:'🌯 Quấn khăn giữ bé'}:restockFor(x,'towel','khăn',{task:id})):null});
    if(sv.includes('nails')){
      const cut=rightCut(t);
      work.push({stage:'nails',hard:true,ok:g.nails?true:null,label:'Cắt móng an toàn',note:g.nails?(g.nails==='short'?'cắt ngắn':'tỉa đầu móng'):'',
        go:g.nails||wet||off?null:first?{cmd:'pc_nails',payload:{task:id,cut},label:cut==='short'?'✂️ Cắt thật ngắn':`✂️ Tỉa đầu móng${t.facts?.nails==='dark'?' (móng đen)':''}`}:{sel:'.pc-cuts',label:'✂️ Chọn cách cắt móng'}});
    }
    if(sv.includes('ears')){
      const how=rightEars(t);
      work.push({stage:'ears',ok:g.ears?true:null,label:'Vệ sinh tai',note:g.ears==='skip'?'bỏ qua':'',
        go:g.ears||wet||off?null:how==='clean'&&x.stock('cotton')<2?lackGo(x,lacks(x,{cotton:2}),id):first?{cmd:'pc_ears',payload:{task:id,how},label:how==='skip'?'🙅 Bỏ qua lau tai · tai có vấn đề':'☁️ Lau tai'}:{sel:'.pc-ears-opts',label:'👂 Lau tai hay bỏ qua?'}});
    }
    // Calm the pet before the next thing that upsets it (never while the tap or the dryer runs);
    // before the nails (the scariest step) until it is relaxed again.
    const band=bandOf(t,x),next=work.find(s=>s.ok!==true&&s.go);
    if(next&&!off&&(band==='stressed'||band==='panic'||(band==='uneasy'&&next.hard))){
      const how=band==='panic'?'break':'voice',c=x.cc.calm.find(k=>k.id===how)||{emoji:'🗣️',name:how};
      steps.push({stage:'table',ok:null,label:band==='panic'?'Bé đang hoảng: cho bé nghỉ đã':'Bé đang căng thẳng: dỗ bé đã',go:{cmd:'pc_calm',payload:{task:id,how},label:`${c.emoji} ${x.esc(c.name)}`}});
    }
  }
  steps.push(...work,reportStep(t,x,first));
  const miss=groomMiss(t);
  const ready=!(g.rinse||g.dry)&&(g.stopped||!miss.length)&&!(g.nick&&!g.stanched);
  return {steps,final:{label:'🐾 Trả bé & thu tiền',go:finish(steps,'pc_handover',task,'Trả bé cho chủ? Chủ sẽ nghe đúng những ý bạn đã chọn để báo.'),ready,
    why:miss.length?'Còn: '+miss.join(', '):off?'Tắt vòi / máy sấy trước':''}};
}

const REFUSE={vaccine:'Sổ tiêm không đủ hạn: từ chối lịch sự',sick:'Bé có dấu hiệu bệnh: từ chối, mời đi khám',full:'Hết chuồng phù hợp: từ chối lịch sự'};
function boardFits(t,x){
  const n=t.needs,d=x.room.data||{},kg=t.facts?.kg??n.kg_said;
  return x.cc.pens.filter(p=>p.zone===n.species&&p.unlock<=(d.level||1)&&!d.pens?.[p.id]&&kg<=p.max_kg).sort((a,b)=>a.max_kg-b.max_kg);
}
function boardGuide(t,x){
  const n=t.needs,f=t.facts||{},vv=ui(x,t),first=firstTime(x),id=t.id,signs=f.signs||[],by=pickup(t,x),fits=boardFits(t,x);
  const steps=[...greetStep(t),inspectStep(t,x,'Kiểm bé trước khi nhận')];
  const why=f.vax&&(f.vax!=='valid'||(f.vax_until!=null&&f.vax_until<by))?'vaccine':signs.includes('fever')||signs.includes('cough')?'sick':!t.pen&&!fits.length&&f.kg!=null?'full':null;
  if(why){
    steps.push({stage:'refuse',ok:null,label:REFUSE[why],go:first?{cmd:'pc_refuse',payload:{task:id,reason:why},confirm:`Từ chối nhận bé? Tiệm sẽ giới thiệu ${x.cc.vet} khi cần.`,label:`🙏 ${x.esc(REFUSE[why])}`}:{sel:'.pc-refuse',label:'🙏 Chọn lý do từ chối'}});
    return {steps,final:null};
  }
  const p0=fits[0],want=portionOf(t,x),right=vv.meals===want.meals&&within(vv.grams,want.grams,x.cc.tol)&&vv.food===(n.food_own?'own':'house')&&(!!vv.solo)===(f.mood==='dog_aggressive');
  steps.push({stage:'pen',ok:t.pen?true:null,label:'Chọn chuồng hợp loài, hợp cân nặng',note:t.pen?pen(x,t.pen).name:'',
    go:t.pen?null:first&&p0?{cmd:'pc_pen',payload:{task:id,pen:p0.id},label:`${p0.emoji} Chọn ${x.esc(p0.name)}`}:{sel:'.pc-pens',label:'🏠 Chọn chuồng'}});
  steps.push({stage:'plan',ok:t.plan?true:null,label:'Ghi kế hoạch ăn theo bảng',note:t.plan?`${t.plan.meals} × ${t.plan.grams} g`:'',
    go:t.plan?null:!first?{sel:'.pc-plan',label:'🥣 Tính khẩu phần rồi bấm 💾 Ghi'}:right?{cmd:'pc_plan',payload:{task:id,food:vv.food,meals:vv.meals,grams:vv.grams,solo:!!vv.solo},label:'💾 Ghi kế hoạch ăn'}
      :{act:'car:chart',label:`📐 Điền theo bảng: ${want.meals} bữa × ${want.grams} g`}});
  return {steps,final:{label:'🏠 Nhận bé & thu tiền',go:finish(steps,'pc_admit',{task:id},'Nhận bé vào chuồng và thu tiền lưu trú?'),ready:!!(t.pen&&t.plan&&t.inspected.includes('vaccine')),
    why:'Xem sổ tiêm, chọn chuồng và ghi kế hoạch ăn trước'}};
}
function feedGuide(t,x){
  const n=t.needs,vv=ui(x,t),first=firstTime(x),id=t.id,want=portionOf(t,x),dog=n.species==='dog';
  const steps=[...greetStep(t),inspectStep(t,x,'Xem bé trước khi cho ăn')];
  const right=vv.food===n.food&&within(vv.grams,want.grams,x.cc.tol);
  steps.push({stage:'feed',ok:t.fed||null,label:'Cho ăn đúng loại, đúng bảng',note:t.bowl?`${t.bowl.grams} g`:'',
    go:t.fed?null:!first?{sel:'.pc-feedbox',label:'🥣 Cân khẩu phần rồi cho ăn'}:right?{cmd:'pc_feed',payload:{task:id,food:vv.food,grams:vv.grams},label:`🥣 Cân ${vv.grams} g & cho ăn`}
      :{act:'car:chart',label:`📐 Cân theo bảng: ${want.grams} g`}});
  if(n.med)steps.push({stage:'med',ok:t.med?true:null,label:'Cho thuốc đúng nhãn',go:t.med||!t.fed?null:{sel:'.pc-med .row',label:'💊 Đọc nhãn, chọn liều'}});
  steps.push({stage:'chore',ok:(t.walked||t.litter)||null,label:dog?'Dắt đi dạo':'Dọn khay cát',
    go:t.walked||t.litter?null:dog?(x.stock('poop_bag')?{cmd:'pc_walk',payload:{task:id},label:'🦮 Dắt bé đi dạo'}:restockFor(x,'poop_bag','túi nhặt phân',{task:id})):{cmd:'pc_litter',payload:{task:id},label:'🧹 Dọn khay cát'}});
  steps.push(reportStep(t,x,first));
  return {steps,final:{label:'📸 Gửi ảnh & cập nhật cho chủ',go:finish(steps,'pc_handover',{task:id},'Gửi cập nhật cho chủ? Chủ sẽ đọc đúng những ý bạn đã chọn.'),
    ready:!!t.fed&&(!n.med||!!t.med),why:n.med?'Cho bé ăn và uống thuốc trước':'Cho bé ăn trước'}};
}
function adoptGuide(t,x){
  const n=t.needs,vv=ui(x,t),id=t.id,pick=vv.pet==='none'?'chưa giao bé nào':(x.cc.adoptees||[]).find(a=>a.id===vv.pet)?.name;
  const steps=[inspectStep(t,x,'Hỏi nếp nhà của gia đình'),{stage:'match',ok:vv.pet?true:null,label:'Chọn bé hợp nếp nhà',note:pick||'',go:vv.pet?null:{sel:'.pc-adoptees',label:'🐾 Chọn bé hợp nếp nhà'}}];
  return {steps,final:{label:vv.pet==='none'?'🤝 Hẹn ngày hội sau':'🏡 Giao bé về nhà mới',
    go:finish(steps,'pc_match',{task:id,pet:vv.pet},vv.pet==='none'?`Chưa giao bé nào cho ${n.family}?`:`Giao bé ${pick||''} cho ${n.family}?`),
    ready:!!vv.pet&&t.inspected.length>0,why:'Hỏi nếp nhà rồi chọn một bé'}};
}
/** {steps, final, pulse} for the task on screen. */
function taskGuide(t,x){
  if(!t.known)return {steps:[{ok:null,label:'Nhận phiếu của chủ',go:{cmd:'ask',payload:{task:t.id},label:'📋 Nhận phiếu'}}],pulse:'.pc-ask'};
  const timers=t.job==='groom'&&t.g?timerSteps(t,x):[];
  if(deskOpen(x))return {steps:[...timers,{ok:null,label:'Chọn cách xử lý chuyện ở quầy',go:{sel:'.pc-desk .pc-opts',label:'🔔 Ra quầy quyết giúp'}}]};
  return (t.job==='groom'?groomGuide:t.job==='board'?boardGuide:t.job==='feed'?feedGuide:adoptGuide)(t,x);
}
function hintOf(x,gd){
  const final=gd.final&&gd.final.ready!==false?{label:gd.final.label.replace(/^[^\p{L}]+/u,''),go:gd.final.go}:null;
  return nextHint(x,gd.steps,{final,pulse:gd.pulse||''});
}
/** Sticky bottom bar: the next step as one big button (the finish stays a small link when allowed). */
function barOf(x,gd){
  // The shared bar (ui-kit actBar via guide stepBar): the next step or the finish as the one main button.
  if(gd.final)return stepBar(x,gd.steps,gd.final,{cls:'pc-bar'});
  const n=pending(gd.steps);
  return n?.go?stepBar(x,gd.steps,null,{cls:'pc-bar'}):'';
}

const JOBS={groom:[(t,x,now)=>intake(t,x,now)+groomJob(t,x,now),groomSide],board:[boardJob,boardSide],feed:[feedJob,feedSide],adopt:[adoptJob,adoptSide]};

function ticket(t,x){
  const who=x.npc(t.npc),n=t.needs,ci=n.case?x.cc.cases?.[n.case]:null;
  const pill=clean()?`<span class="pc-tagq">${jobTag(x,t)}${helpQ(x)}</span>`:jobTag(x,t);
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

const ENDED=['completed','referred','cancelled'];
/** 🏠 The home card (app.js taskCards). A pet waiting on stock (no towel for the dryer), a pet parked with ⋯ › Để lát
 * nữa, or closing time: "Làm tiếp" alone read as stuck ("hết khăn không khép ca được"), although closing was never
 * blocked. Then the card also offers Khép ca (unfinished work is kept for tomorrow). Otherwise the shared card. */
function hudCard(c,t,x,{bell='',first='',note=''}={},next=()=>''){
  if(!c?.open||!t)return '';
  let lack=null;try{lack=pending(taskGuide(t,x).steps)?.go?.lack||null;}catch{/* no guide for this task yet */}
  const parked=(c.tasks||[]).some(k=>k.deferred&&!ENDED.includes(k.status));
  const late=!!note;   // closingNote: closing time, or no more customers today
  if(!lack&&!parked&&!late)return '';
  const why=lack?`<p class="dc-closing-line pc-hud-why" role="status">📦 <b>Hết ${x.esc(String(lack).toLowerCase())}</b> · nhập hàng rồi làm tiếp, hoặc khép ca: việc dở được giữ tới mai.</p>`
    :!late?'<p class="dc-closing-line pc-hud-why" role="status">⏸️ <b>Có bé đang để lát nữa</b> · khép ca lúc nào cũng được, việc dở được giữ tới mai.</p>':'';
  return `<article class="note-card calm-card task-card pc-hud">${note}${why}<button type="button" class="calm-what" data-action="job" data-task="${x.esc(t.id)}" title="${x.esc(t.title||'')}"><span class="npc-mini">${x.portrait(x.npc(t.npc),34)}</span><b>${next(t)}</b></button>${bell}${x.button('Khép ca','end',{},'ghost pc-hud-close')}${x.button('Làm tiếp '+x.icon('arrow',14),'job',{task:t.id},'primary'+first)}</article>`;
}
export const _test={hudCard};

export default {
  id:'pet_care',
  css:true,
  hudCard(c,t,x,o){return hudCard(c,t,x,o,t=>this.next(t,x));},
  next(t,x){
    try{const n=x&&pending(taskGuide(t,x).steps);if(n)return x.esc(stepLine(n));}catch{/* fall back to the fixed lines */}
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
    if(t.known)ui(x,t);
    const gd=t.known?reach(t,x,taskGuide(t,x)):taskGuide(t,x),hint=hintOf(x,gd);
    if(!t.known){
      // Clean layout: who and their words; the day's theme in "?", the ask as the bar's one main button.
      if(clean())return `<div class="career-job pc">${hint}${desk}<article class="card ticket"><div class="row">${x.portrait(who,56)}<div class="grow"><div class="row spread"><h3>${x.esc(who.display_name)}</h3><span class="pc-tagq">${jobTag(x,t)}${helpQ(x)}</span></div><p>“${x.esc(t.opening)}”</p></div></div></article>
        ${kennelBox(x)}${desk?'':barOf(x,gd)}</div>`;
      return `<div class="career-job pc">${hint}${desk}${todayChip(x)}<article class="card ticket"><div class="row">${x.portrait(who,56)}<div class="grow"><div class="row spread"><h3>${x.esc(who.display_name)}</h3><span class="tag blue">${JOB_ICON[t.job]||''} ${x.esc(x.cc.jobs?.[t.job]||t.job)}</span></div><p>“${x.esc(t.opening)}”</p></div></div>${x.cmd('📋 Nhận phiếu','ask',{task:t.id},'primary full pc-ask',!!desk)}</article>
        ${kennelBox(x)}</div>`;
    }
    const bar=barOf(x,gd);
    if(desk)return `<div class="career-job pc">${hint}${runningTimers(t,x)}${desk}${ticket(t,x)}${bar}</div>`;
    if(t.job==='groom'&&t.g.bolt)return `<div class="career-job pc">${hint}${runningTimers(t,x)}${boltAlert(t,x)}${ticket(t,x)}${bar}</div>`;
    const [main,side]=JOBS[t.job]||JOBS.groom;
    // The shop's other chores sit under the work as one-line folds (khu lưu trú, việc chăm sóc khác, tiệm).
    const extra=t.job==='board'||t.job==='adopt'?'':kennelBox(x);
    const n=careCount(x),care=n?`<section class="pc-card pc-care-fold">${fold(clean()?`📋 <span class="sr-only">Việc chăm sóc khác:</span> ${n}`:`📋 Việc chăm sóc khác · ${n} việc`,careBoard(x))}</section>`:'';
    return `<div class="career-job pc">${hint}${lastDesk(x)}${clean()?'':todayChip(x)}${ticket(t,x)}${regularCard(t,x)}<div class="workbench"><section class="wb-main">${main(t,x,gd.now)}</section><aside class="wb-side">${side(t,x,gd)}</aside></div>
      <div class="pc-more">${extra}${care}${shopFold(x)}</div>${bar}</div>`;
  },
  tick(root){keepBarAboveFooter(root);},
  // The running tap and dryer (v4/careers.js): the bars glide on the compositor, the words change five times a
  // second. A stop tap holds them where they were when the finger came down (tapStop).
  meters(root,x){
    // Live timer buttons (hint + bottom bar): text only, the buttons themselves stay put. Once it is time, the
    // button is a stop control too (data-tap-stop); before that a tap only says how long is left.
    const t=x.room.tasks.find(v=>v.id===x.ui.tid);
    if(t?.g)for(const el of (root.closest('dialog')||document).querySelectorAll('[data-pc-live]')){
      const kind=el.dataset.pcLive;if(!t.g[kind])continue;
      const label=liveLabel(kind,t,x),ready=timerReady(kind,t,x),b=el.closest('button');
      if(el.textContent!==label)el.textContent=label;
      if(b){b.classList.toggle('pc-ready',ready);const op=ready?(kind==='rinse'?'pc_rinse':'pc_dry'):'';if((b.dataset.tapStop||'')!==op){if(op)b.dataset.tapStop=op;else delete b.dataset.tapStop;}}
    }
    for(const el of root.querySelectorAll('[data-pc-timer]')){
      const start=Number(el.dataset.start);if(!start)continue;
      const kind=el.dataset.pcTimer,base=Number(el.dataset.base)||0,need=Number(el.dataset.need)||1,over=Number(el.dataset.over)||need*2,rate=Number(el.dataset.rate)||1;
      const value=base+Math.max(0,x.now()-start)*rate;
      const label=kind==='rinse'?`${value.toFixed(1)} giây · ${value<need?'còn bọt, xả tiếp':'nước đã trong — khóa vòi được rồi'}`
        :`${Math.floor(value)}% · ${value<need?'chân lông còn ẩm':value<over?'khô rồi — tắt máy':'quá lâu, da khô xơ!'}`;
      x.slide(el.querySelector('.fill'),value/over*100,rate/over*100,true);
      const l=el.querySelector('.pc-timer-label');if(l.textContent!==label)l.textContent=label;
      el.classList.toggle('ready',value>=need&&value<over);
      el.classList.toggle('over',value>=over);
    }
  },
  tapStop:(op,p)=>(op==='pc_rinse'||op==='pc_dry')&&p.mode==='stop',
  actions:{
    ...SF.foldActions,
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
    async temp(data,el,x){
      const t=x.room.tasks.find(v=>v.id===x.ui.tid);if(!t)return;
      ui(x,t).temp=Math.max(30,Math.min(45,Number(data.val)||37));x.render();
    },
    // Fill the portion from the chart (a first task's one-tap help).
    async chart(data,el,x){
      const t=x.room.tasks.find(v=>v.id===x.ui.tid);if(!t)return;
      const vv=ui(x,t),n=t.needs,want=portionOf(t,x);
      vv.grams=want.grams;
      if(t.job==='board'){vv.meals=want.meals;vv.food=n.food_own?'own':'house';vv.solo=t.facts?.mood==='dog_aggressive';}
      if(t.job==='feed')vv.food=n.food;
      x.render();
    },
    async report(data,el,x){
      const t=x.room.tasks.find(v=>v.id===x.ui.tid);if(!t)return;
      const vv=ui(x,t);vv.say=String(data.say||'').split(',').filter(Boolean);
      await x.send('pc_report',{task:t.id,say:vv.say});
    },
    // Live timer button: turns the tap / dryer off once it is time, else says how long is left.
    async tapoff(data,el,x){
      const t=x.room.tasks.find(v=>v.id===x.ui.tid);if(!t?.g)return;
      const kind=data.kind==='dry'?'dry':'rinse';
      if(!t.g[kind]){x.render();return;}
      if(timerReady(kind,t,x)){await x.send(kind==='rinse'?'pc_rinse':'pc_dry',{task:t.id,mode:'stop'});return;}
      highlight(document.querySelector(`#sheet[open] [data-pc-timer="${kind}"]`));
      const now=Date.now();
      if(now-(x.ui.waitToast||0)>2500){x.ui.waitToast=now;x.toast(kind==='rinse'?'Nước còn đục bọt. Nút sáng lên khi xả đủ.':'Chân lông còn ẩm. Nút sáng lên khi khô.','hint');}
    },
    async say(data,el,x){
      const t=x.room.tasks.find(v=>v.id===x.ui.tid);if(!t)return;
      const vv=ui(x,t),id=data.id;
      vv.say=vv.say.includes(id)?vv.say.filter(r=>r!==id):[...vv.say,id];
      x.render();
    },
  },
  dock:[['inventory','box','Kho','Sữa tắm, hạt, bông']],
  // Day summary: "🌅 Ngày mai" (the boarders' night, the forecast, the shelf) first, the day folded.
  summary(data,x){
    return tomorrowCard(x,data,{lift:/^(Khu lưu trú|Dự báo ngày mai)/,title:'🐾 Sổ tiệm hôm nay',labels:{staying:'Bé đang ở lại',free:'Chuồng trống'}});
  },
};
