/** Salon Tóc Gió — phone-first stylist chair (plugin career UI).
 * The server decides every result: answers, the bowl formula, timer zones, the mirror, the review and the money.
 * Local state is only what is being picked before sending (services, tubes, parts, length, products) and the open step tab.
 * The bowl preview runs the server's own verdict (salon_mix.js) on what the stylist has found out; nothing is mixed until "Trộn bát".
 * Care loop: the client card (formula, hair health, patch test, last cut), follow-up bookings and the jar of clean tool sets. */
import {reqList,fold} from '../ui-kit.js';
import {stepRows,nextHint,stepCta,finalGo,pending,firstTime,stepLine} from '../v4/guide.js';
import {restockFor,restockButton} from '../v4/restock.js';
import {keepBarAboveFooter} from './food_kit.js';
import {blend,mix,levelOk,levelText,bowlCheck,previewInputs,recipeWant,target} from './salon_mix.js';
const CHEM=['color','bleach','toner'];
const ZONE_TEXT={under:'chưa đủ giờ',ideal:'đúng giờ',over:'hơi quá giờ',damage:'quá giờ, tóc gãy'};
const STAGES={consult:['💬','Tư vấn'],plan:['🤝','Chốt'],color:['🎨','Pha màu'],wash:['🫧','Gội'],cut:['✂️','Cắt'],finish:['💨','Hoàn thiện'],bill:['🧾','Thanh toán']};
const TITLES={consult:'Tư vấn trên ghế',plan:'Chốt phương án với khách',color:'Bàn pha màu',wash:'Bồn gội',cut:'Ghế cắt',finish:'Phục hồi & sấy',bill:'Thanh toán & tiễn khách'};

const svc=(x,id)=>x.cc.services?.find(s=>s.id===id)||{id,name:id,emoji:'•'};
const price=(x,id)=>x.room.life?.prices?.[id]??x.cc.prices?.[id]??0;
const started=t=>Boolean(t.done.length||t.bowl||t.timer||t.cut.steps.length);
const levelColor=(x,l)=>x.cc.levels?.find(v=>v.level===l)?.color||'';
const retail=(x,id)=>x.cc.retail?.find(r=>r.id===id)||{id,name:id,emoji:'•',price:0};
const dyeOf=(x,id)=>x.cc.dyes?.find(d=>d.id===id)||null;
const chemLeft=t=>(t.plan?.services||[]).filter(s=>CHEM.includes(s)&&!t.done.includes(s));
const fmtRatio=r=>String(r).replace(':','∶');
const caseOf=t=>t.needs?.case||null;
const rushLeft=(t,x)=>t.due_turn==null?null:t.due_turn-(x.room.turn||0);
const bandName=(x,id)=>x.cc.bands?.find(b=>b.id===id)?.name||id||'';
const cmdAttr=(x,command,payload)=>`data-command="${command}" data-payload="${x.esc(JSON.stringify(payload))}"`;
const itemName=(x,id)=>(x.content.inventory?.items?.salon||[]).find(i=>i.id===id)?.name||id;
const carAttr=(x,action,data)=>`data-action="car:${action}" ${Object.entries(data).map(([k,v])=>`data-${k}="${x.esc(v)}"`).join(' ')}`;
const care=x=>x.cc.care||{};
const cardOf=(x,t)=>x.room.data?.cards?.[t.npc]||null;
const cardFormula=(x,t)=>(x.room.data?.card_for||[]).includes(t.id)?cardOf(x,t)?.formula||null:null;
const deskBusy=x=>!!x.room.data?.desk?.ev;

function ui(x,t){
  const u=x.ui[t.id]??={services:[],sessions:1,kind:null,a:null,b:null,pa:1,pb:1,shade:null,dev:null,ratio:null,len:2,products:[],book:[],tab:null,tabAt:null,init:false};
  if(!u.init&&t.needs){u.services=[...t.needs.services];u.init=true;}
  if(t.patch_done&&!u.patchSync){u.services=u.services.filter(s=>s!=='color'&&s!=='toner');u.patchSync=true;}
  const key=t.plan?t.plan.services.join(',')+'/'+t.plan.sessions:'';
  if(key&&u.planKey!==key){u.services=[...t.plan.services];u.sessions=t.plan.sessions;u.planKey=key;}
  return u;
}

/* ---------- mixing maths: salon_mix.js, a port of the server's bowl_check (tests/test_salon_mix_parity.py) ---------- */
const mixOf=(x,a,b,pa,pb,warm)=>mix(x.cc,a,b,pa,pb,warm);

/* ---------- stages ---------- */
function stages(t){
  const list=['consult','plan'],svcs=t.plan?.services||t.needs.services;
  if(svcs.some(s=>CHEM.includes(s))||Object.keys(t.results||{}).length)list.push('color');
  list.push('wash');
  if(svcs.includes('cut'))list.push('cut');
  if(svcs.some(s=>s==='treatment'||s==='style'))list.push('finish');
  list.push('bill');
  return list;
}
function current(t){
  if(!t.plan)return 'consult';
  if(t.timer||t.bowl||chemLeft(t).length)return 'color';
  if(!t.washed)return 'wash';
  const p=t.plan.services.filter(s=>!t.done.includes(s));
  if(p.includes('cut'))return 'cut';
  if(p.includes('treatment')||p.includes('style'))return 'finish';
  return 'bill';
}
function nav(t,x,list,at,tab){
  const ai=list.indexOf(at);
  return `<nav class="sl-nav" style="--n:${list.length}" aria-label="Các bước làm tóc">${list.map((s,i)=>{
    const [e,l]=STAGES[s],open=i<=ai||(s==='plan'&&!t.plan),done=i<ai;
    return `<button type="button" class="${done?'done':''} ${s===at?'now':''} ${s===tab?'open':''}" ${carAttr(x,'tab',{task:t.id,tab:s,at})} aria-current="${s===tab?'step':'false'}" ${open?'':'disabled'}><span aria-hidden="true">${done?'✓':e}</span>${x.esc(l)}</button>`;
  }).join('')}</nav>`;
}

/* ---------- shared bits ---------- */
function todayChip(x,fold=false){const d=x.room.data?.today;if(!d)return '';
  // On a job the day's theme is one line; tap to read the detail.
  return fold?`<details class="sl-today sl-today-fold"><summary><span aria-hidden="true">${x.esc(d.emoji)}</span> <b>Hôm nay: ${x.esc(d.title)}</b></summary><small>${x.esc(d.text)}</small></details>`
    :`<p class="sl-today"><span aria-hidden="true">${x.esc(d.emoji)}</span> <b>Hôm nay: ${x.esc(d.title)}</b> <small>${x.esc(d.text)}</small></p>`;}
function deskCard(x){
  const ev=x.room.data?.desk?.ev;if(!ev)return '';
  const who=x.npc(ev.npc);
  const opts=ev.options.map((o,i)=>`<button type="button" class="btn ghost sl-opt" ${cmdAttr(x,'sl_desk',{option:o.id})} ${o.cost>x.room.money?'disabled':''}><b>${x.esc(o.label)}</b>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}</button>`).join('');
  return `<section class="sl-desk ${x.esc(ev.tone||'')}" role="alert" aria-live="assertive"><div class="sl-desk-head"><span class="sl-desk-emoji" aria-hidden="true">${x.esc(ev.emoji)}</span><div><small>CHUYỆN Ở QUẦY</small><h3>${x.esc(ev.title)}</h3></div>${x.portrait(who,40)}</div>
    <p>${x.esc(ev.text)}</p><div class="sl-opts">${opts}</div></section>`;
}
function lastDesk(x){const l=x.room.data?.desk?.last;if(!l||l.day!==x.room.day)return '';return `<p class="sl-last ${l.good===true?'good':l.good===false?'bad':''}" aria-live="polite"><span aria-hidden="true">${x.esc(l.emoji)}</span> <b>${x.esc(l.title)}:</b> ${x.esc(l.outcome)}</p>`;}
function calmBar(t){
  const v=Math.max(0,Math.min(100,Number(t.calm)||0));
  return `<div class="sl-calm ${v<20?'bad':v<40?'warn':'ok'}" role="meter" aria-label="Bé bình tĩnh" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${v}"><span>🧒 Bé bình tĩnh</span><div class="bar"><i style="width:${v}%"></i></div><b>${v}</b></div>`;
}
function jar(x){
  const d=x.room.data||{},n=Number(d.clean)||0,max=d.clean_max||care(x).clean_sets||4;
  return `<span class="sl-jar ${n?'':'nil'}" role="meter" aria-label="Bộ lược kéo đã khử khuẩn" aria-valuemin="0" aria-valuemax="${max}" aria-valuenow="${n}">${Array.from({length:max},(_,i)=>`<i class="${i<n?'on':''}"></i>`).join('')}<b>🧼 ${n}/${max} bộ sạch</b></span>`;
}
function foot(x,folded=false){
  const d=x.room.data||{},busy=deskBusy(x),n=Number(d.clean)||0,max=d.clean_max||4;
  const label=n>=max?'✅ Hũ khử khuẩn đầy':n?'🧴 Ngâm lại bộ':'🧴 Khử khuẩn dụng cụ';
  const body=`<div class="sl-foot">${jar(x)}<p class="row wrap">${x.cmd(label,'sl_sanitize',{},n?'ghost small':'primary small',n>=max||busy)}${x.button('📦 Kho thuốc & vật tư','inventory',{},'ghost small')}</p></div>`;
  // During a job: one line that still shows how many clean sets are left (open while the jar is empty).
  if(!folded)return body;
  return `<details class="sl-foot-fold"><summary>🧼 Dụng cụ sạch ${n}/${max} bộ <small>· khử khuẩn, kho</small></summary>${body}</details>`;
}

/* ---------- care loop: client card, bookings ---------- */
function healthWord(x,h){return (care(x).health_words||[]).find(([lim])=>h>=lim)?.[1]||'';}
function healthBar(x,h,label='Sức khỏe tóc'){
  const weak=h<(care(x).weak||50);
  return `<div class="sl-hp ${weak?'weak':h<70?'mid':''}" role="meter" aria-label="${x.esc(label)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${h}"><span>💧 ${x.esc(label)}</span><div class="bar"><i style="width:${h}%"></i></div><b>${h} · ${x.esc(healthWord(x,h))}</b></div>`;
}
function cardRows(x,cd,withHealth=true){
  const f=cd.formula,rows=[];
  rows.push(['💇','Tóc',cd.hair||'Chưa hỏi lịch sử hóa chất']);
  if(f)rows.push(['🎨',`Công thức màu · ngày ${f.day}`,`${f.text}`,`ra ${f.target}${f.hit?'':' · lần đó lệch màu, đừng chép y'}`,f.hit?'':'warn']);
  rows.push(['🩹','Thử dị ứng',cd.allergy?'Sổ dị ứng: từng phản ứng — không nhuộm':cd.patch_file?'Có hồ sơ thử dị ứng':cd.patch_day?`Sổ tiệm: thử ngày ${cd.patch_day}`:'Chưa có kết quả',null,cd.allergy?'danger':'']);
  if(cd.cut)rows.push(['✂️',`Lần cắt trước · ngày ${cd.cut.day}`,`bớt ${cd.cut.removed} cm`,cd.cut.short?'bị lẹm — lần sau chỉ tỉa ít':`giữ dáng: tỉa tối đa ${cd.trim_cap} cm`,cd.cut.short?'warn':'']);
  if(cd.next)rows.push(['📅','Lịch hẹn',`${cd.next.label} ngày ${cd.next.due}`]);
  return `${withHealth?healthBar(x,cd.health):''}<ul class="sl-card-rows">${rows.map(([i,l,v,n,tone])=>`<li class="${tone?'tone-'+tone:''}"><span aria-hidden="true">${i}</span><span><small>${x.esc(l)}</small><b>${x.esc(v)}</b>${n?`<em>${x.esc(n)}</em>`:''}</span></li>`).join('')}</ul>`;
}
function cardFold(t,x){
  const cd=cardOf(x,t);if(!cd||t.regular==null)return '';
  const match=!!cardFormula(x,t),weak=t.weak;
  const hp=t.health!=null?healthBar(x,t.health,'Sức khỏe tóc hôm nay'):'';
  return `<section class="sl-card">${fold(`📇 Thẻ khách quen · ${x.esc(cd.trust_name)} · ${cd.visits} lần ghé`,`${hp}${cardRows(x,cd,false)}`,!t.plan&&(match||!!weak))}</section>`;
}
function apptUi(x,a){return x.ui['appt:'+a.id]??={a:null,b:null,pa:1,pb:1,dev:null,len:1};}
function apptCard(x,a){
  const cd=x.room.data?.cards?.[a.npc]||{},busy=deskBusy(x),who=x.npc(a.npc),u=apptUi(x,a);
  let body='',payload={id:a.id},ready=true;
  if(a.kind==='roots'&&cd.formula){
    const f=cd.formula;
    const tubes=x.cc.dyes.map(d=>{const role=u.a===d.id?'A':u.b===d.id?'B':'',q=x.stock(d.id);return `<button type="button" class="sl-tube mini ${role?'selected':''}" ${carAttr(x,'aTube',{id:a.id,v:d.id})} aria-pressed="${!!role}" aria-label="Tuýp ${x.esc(d.code)}, còn ${q}" ${q||role?'':'disabled'}>${role?`<i class="sl-role" aria-hidden="true">${role}</i>`:''}<span class="sl-cap" style="--sw:${x.esc(d.color)}"></span><b>${x.esc(d.code)}</b></button>`;}).join('');
    const part=(w,id,p)=>id?`<div class="sl-part"><span><i class="sl-role" aria-hidden="true">${w.toUpperCase()}</i> ${x.esc(dyeOf(x,id)?.code||'')}</span><button type="button" class="btn small ghost" ${carAttr(x,'aPart',{id:a.id,which:w,d:-1})} aria-label="Bớt một phần" ${p<=1?'disabled':''}>−</button><b>${p} phần</b><button type="button" class="btn small ghost" ${carAttr(x,'aPart',{id:a.id,which:w,d:1})} aria-label="Thêm một phần" ${p>=3?'disabled':''}>+</button></div>`:'';
    const devs=[10,20,30].map(v=>`<button type="button" class="sl-seg ${u.dev===v?'on':''}" ${carAttr(x,'aDev',{id:a.id,v})} aria-pressed="${u.dev===v}">${v} vol</button>`).join('');
    const m=u.a?mixOf(x,u.a,u.b,u.pa,u.b?u.pb:0,0):null;
    const prev=m?`<p class="sl-preview small"><span class="sl-dish" style="--sw:${x.esc(m.color)}" aria-hidden="true"></span><span>Bát: level ${x.esc(levelText(m))} · ${x.esc(bandName(x,m.band))}</span></p>`:'';
    body=`<p class="sl-note">📇 Thẻ: <b>${x.esc(f.text)}</b> → ${x.esc(f.target)}</p>
      <div class="row wrap">${x.button('📇 Pha theo thẻ','car:aCard',{id:a.id},'small')}</div>
      <div class="sl-tubes mini">${tubes}</div><div class="sl-parts">${part('a',u.a,u.pa)}${part('b',u.b,u.pb)}</div>
      <div class="sl-segs">${devs}</div>${prev}`;
    payload={id:a.id,shade:u.a,parts:[u.pa,u.b?u.pb:0],dev:u.dev};if(u.b)payload.shade2=u.b;
    ready=!!(u.a&&u.dev);
  }else if(a.kind==='trim'){
    body=`<p class="sl-note">📇 Thẻ: tỉa giữ dáng tối đa <b>${cd.trim_cap||2} cm</b>${cd.cut?.short?' (lần trước bị lẹm)':''}.</p>
      <div class="sl-len"><span>Tỉa</span><button type="button" class="btn small ghost" ${carAttr(x,'aLen',{id:a.id,d:-1})} aria-label="Bớt 1 cm" ${u.len<=1?'disabled':''}>−</button><b>${u.len} cm</b><button type="button" class="btn small ghost" ${carAttr(x,'aLen',{id:a.id,d:1})} aria-label="Thêm 1 cm" ${u.len>=6?'disabled':''}>+</button></div>`;
    payload={id:a.id,length:u.len};
  }else{
    body=`${cd.health!=null?healthBar(x,cd.health):''}<p class="small">💧 Keratin còn ${x.stock('keratin')} lượt.</p>`;
    ready=x.stock('keratin')>0;
  }
  const late=(x.room.day||0)-a.due;
  const inChair=(x.room.tasks||[]).some(v=>v.npc===a.npc&&v.day===x.room.day&&!['completed','referred','cancelled'].includes(v.status));
  const covers={roots:'nhuộm màu',trim:'cắt',care:'phục hồi'}[a.kind];
  if(inChair)body=`<p class="sl-note good">💺 ${x.esc(a.who)} cũng đang chờ ghế hôm nay — nếu lượt đó có ${covers}, lịch hẹn này được gộp luôn.</p>`+body;
  return `<article class="sl-appt"><div class="row">${x.portrait(who,40)}<div class="grow"><b>${x.esc(a.emoji)} ${x.esc(a.label)} · ${x.esc(a.who)}${a.price!=null?` · ${x.esc(x.money(a.price))} (dưới 3★ trả nửa)`:''}</b><small class="muted">Hẹn ngày ${a.due}${late>0?` · đã chờ ${late} ngày, hạn chót ngày ${a.until}`:` · chờ được tới ngày ${a.until}`}</small></div></div>
    ${body}<div class="sl-cta">${x.cmd(`${a.emoji} Làm ${a.label.toLowerCase()} cho khách`,'sl_appt',payload,'primary full',!ready||busy)}</div></article>`;
}
function apptBook(x,open){
  const list=x.room.data?.appts||[],day=x.room.day||0;
  const ready=list.filter(a=>a.ready),later=list.filter(a=>a.state==='open'&&!a.ready),done=list.filter(a=>a.state==='done'&&a.due<=day);
  if(!ready.length&&!later.length&&!done.length)return '';
  const checklist=ready.length||done.length?reqList([...ready.map(a=>({ok:null,icon:a.emoji,label:`${a.who} — ${a.label.toLowerCase()}`,value:`ngày ${a.due}`,tone:day>=a.until?'danger':''})),...done.filter(a=>a.due>=day-(care(x).keep||2)).map(a=>({ok:true,icon:a.emoji,label:`${a.who} — ${a.label.toLowerCase()}`,value:`${a.stars}★`}))],x.esc,'Khách hẹn hôm nay'):'';
  const soon=later.length?fold(`🗓️ Hẹn sắp tới · ${later.length}`,`<ul class="sl-soon">${later.map(a=>`<li><span>${x.esc(a.emoji)} ${x.esc(a.who)}</span><small>${x.esc(a.label)} · ngày ${a.due}</small></li>`).join('')}</ul>`):'';
  const body=`${checklist}${ready.map(a=>apptCard(x,a)).join('')}${soon}`;
  const head=ready.length?`📅 Sổ hẹn · ${ready.length} khách tới hôm nay`:`📅 Sổ hẹn · ${later.length} hẹn sắp tới`;
  return `<section class="sl-book">${fold(head,body,open&&ready.length>0)}</section>`;
}
function regularsBook(x){
  const cards=Object.values(x.room.data?.cards||{}).sort((a,b)=>b.last-a.last);
  if(!cards.length)return '';
  const rows=cards.map(cd=>`<li class="sl-regular">${fold(`<b>${x.esc(cd.name)}</b> <small>${x.esc(cd.trust_name)} · ${cd.visits} lần · tóc ${cd.health} ${x.esc(cd.health_word.toLowerCase())}</small>`,cardRows(x,cd))}</li>`).join('');
  return `<section class="sl-book">${fold(`📇 Sổ khách quen · ${cards.length} thẻ`,`<ul class="sl-regulars">${rows}</ul>`)}</section>`;
}
function bookBlock(t,x){
  const kinds=t.bookable||[],u=ui(x,t),ap=care(x).appts||{},day=x.room.day||t.day;
  if(!kinds.length)return '';
  const chips=kinds.map(k=>{const a=ap[k]||{label:k,emoji:'📅',days:0},on=u.book.includes(k);return `<button type="button" class="sl-chip ${on?'on':''}" ${carAttr(x,'book',{task:t.id,id:k})} aria-pressed="${on}">${x.esc(a.emoji)} ${x.esc(a.label)} · ngày ${day+a.days}<small>${x.esc(a.why||'')}</small></button>`;}).join('');
  return `<h5 class="sl-sub" title="Khách quay lại, nhớ làm trong ${care(x).keep||2} ngày">📅 Hẹn lần tới</h5><div class="sl-chips">${chips}</div>`;
}
function rules(x){
  return `<details class="sl-rules gd-rules"><summary>📜 Quy tắc pha màu</summary><ul>${x.cc.rules.map(r=>`<li>${x.esc(r)}</li>`).join('')}</ul>
    <div class="sl-levels">${x.cc.levels.map(l=>`<span style="--sw:${x.esc(l.color)}" title="${x.esc(l.name)}"><i></i>${l.level}</span>`).join('')}</div></details>`;
}

/** "🎨 Bảng màu": a reference card, closed by default. Only the salon's fixed shades (x.cc levels, dyes, toners) and
 * how tube codes and two-tube bowls read in general: nothing about the client in the chair, nothing selected or
 * marked, no verdict (the player still picks every tube). */
const FAM_WORD={N:'tự nhiên',A:'tro, lạnh',G:'vàng, ấm',R:'đỏ, ấm đậm'};
function palette(x){
  const lv=(x.cc.levels||[]).map(l=>`<li><span class="sl-pal-sw" style="--sw:${x.esc(l.color)}" aria-hidden="true"></span><b>${l.level}</b> ${x.esc(l.name)}</li>`).join('');
  const dy=(x.cc.dyes||[]).map(d=>`<li><span class="sl-cap" style="--sw:${x.esc(d.color)}" aria-hidden="true"></span><span><b>${x.esc(d.code)}</b> ${x.esc(d.tone)}<small>level ${d.level} · ánh ${x.esc(FAM_WORD[d.fam]||'')}</small></span></li>`).join('');
  const tn=(x.cc.toners||[]).map(d=>`<li><span class="sl-cap" style="--sw:${x.esc(d.color)}" aria-hidden="true"></span><span><b>${x.esc(d.code)}</b> ${x.esc(d.tone)}</span></li>`).join('');
  return `<details class="sl-rules sl-palette"><summary>🎨 Bảng màu</summary>
    <p class="small">Mã tuýp: số trước dấu chấm là level (1 đen → 10 bạch kim), số sau là ánh: .0 tự nhiên · .1 tro lạnh · .3 vàng ấm · .6 đỏ.</p>
    <h5 class="sl-sub">Level tóc</h5><ul class="sl-pal-levels">${lv}</ul>
    <h5 class="sl-sub">Tuýp nhuộm trong tủ</h5><ul class="sl-pal-tubes">${dy}</ul>
    ${tn?`<h5 class="sl-sub">Toner</h5><ul class="sl-pal-tubes">${tn}</ul>`:''}
    <h5 class="sl-sub">Pha hai tuýp</h5><ul><li>Level bát = trung bình theo số phần: 1 phần 3.0 + 1 phần 7.3 ra level 5; 2 phần 3.0 + 1 phần 6.1 ra level 4.</li><li>Ánh tro kéo màu lạnh đi, ánh vàng hay đỏ kéo màu ấm lên; tuýp .0 giữ màu tự nhiên.</li><li>Thuốc nhuộm không làm sáng màu nhuộm cũ: muốn sáng hơn thì tẩy trước, rồi toner khử ánh còn lại.</li></ul></details>`;
}

function ticket(t,x){
  const who=x.npc(t.npc),n=t.needs,ph=n.photo,cs=caseOf(t),ci=cs?x.cc.cases?.[cs]:null,left=rushLeft(t,x);
  const sw=ph.level?`<span class="sl-swatch" style="--sw:${x.esc(levelColor(x,ph.level))}" aria-hidden="true"></span>`:'<span class="sl-swatch cut" aria-hidden="true">✂️</span>';
  const patch={file:['🩹 Có hồ sơ thử dị ứng','green'],log:['🩹 Sổ tiệm: đã thử','green'],none:['🩹 Chưa thử dị ứng','danger'],allergy:['🩹 Sổ dị ứng: từng phản ứng','danger']}[t.patch_record]||null;
  const tags=[t.budget!=null?x.pill('💰 '+x.money(t.budget),'amber'):x.pill('💰 chưa hỏi ngân sách')];
  if(ci)tags.push(`<span class="tag sl-case">${x.esc(ci.emoji)} ${x.esc(ci.label)}</span>`);
  if(left!=null)tags.push(`<span class="tag ${left>=0?(left<=4?'danger':'green'):'danger'} sl-rush">⏱️ ${left>=0?`còn ${left} nhịp · +${x.esc(x.money(n.rush.bonus))}`:'đã trễ hẹn'}</span>`);
  if(patch)tags.push(x.pill(patch[0],patch[1]));
  if(t.reacted)tags.push(x.pill('🚫 Không nhuộm: có phản ứng','danger'));
  if(t.plan)tags.push(x.pill(`🗓️ ${t.plan.sessions} buổi`,t.plan.overpromise?'danger':''));
  if(t.health!=null)tags.push(x.pill(`💧 Tóc ${t.health}/100 · ${healthWord(x,t.health).toLowerCase()}`,t.weak?'danger':''));
  if(t.mistakes)tags.push(x.pill(`⚠️ ${t.mistakes} lỗi`,'danger'));
  const photoLine=ph.level?`<small>${x.esc(ph.tone)} · level ${ph.level}${ph.filtered&&!t.real?' · ảnh có filter?':''}</small>`:'';
  const real=t.real?`<p class="sl-real">📸 Ảnh gốc: level ${t.real.level} · ${x.esc(bandName(x,t.real.tone))}</p>`:'';
  // Compact ticket: who + patience, the services, and the customer's reference photo as one thumbnail row.
  return `<article class="sl-ticket compact"><div class="row">${x.portrait(who,40)}<div class="grow">
      <div class="row spread wrap"><h3>${x.esc(who.display_name)}</h3><div class="patience" title="Kiên nhẫn"><div class="bar ${t.patience<50?'low':''}"><i style="width:${Number(t.patience)||0}%"></i></div><small>${Number(t.patience)||0}%</small></div></div>
      <p class="sl-want">${n.services.map(s=>`${svc(x,s).emoji} ${x.esc(svc(x,s).name)}`).join(' · ')}</p></div></div>
    ${t.plan?'':`<p class="small sl-wantline">${x.esc(n.want)}</p>`}
    <div class="sl-photo slim">${sw}<div class="grow"><b>📸 ${x.esc(ph.style)}</b>${photoLine}</div></div>${real}
    <details class="sl-more"><summary>💬 Lời dặn của khách</summary>${t.plan?`<p class="small">${x.esc(n.want)}</p>`:''}<p class="muted small">“${x.esc(n.note)}”</p></details>
    ${t.calm!=null&&!t.done.includes('cut')?calmBar(t):''}
    <div class="row wrap sl-tags">${tags.join('')}</div>
    ${cardFold(t,x)}
  </article>`;
}

/* ---------- panels ---------- */
function consult(t,x){
  const qa=x.cc.topics.map(q=>{
    const a=t.answers?.[q.id];
    return `<div class="sl-qa ${a?'done':''}">${a?`<p class="sl-q" title="${x.esc(q.ask)}">${q.emoji} ${x.esc(q.label)}</p><p class="sl-a">${x.esc(a)}</p>`:x.cmd(`${q.emoji} ${x.esc(q.label)}`,'sl_consult',{task:t.id,topic:q.id},'ghost small')}</div>`;
  }).join('');
  const zones=x.cc.zones.map(z=>{
    const f=t.findings?.[z.id];
    return `<button type="button" class="sl-zone ${z.id} ${f?'seen':''}" ${cmdAttr(x,'sl_inspect',{task:t.id,zone:z.id})} ${f?'disabled':''}><b>${z.emoji} ${x.esc(z.label)}</b>${f?`<small>${x.esc(f)}</small>`:''}</button>`;
  }).join('');
  const dye=t.needs.services.some(s=>s==='color'||s==='toner'),bleach=t.needs.services.includes('bleach');
  const tests=[];
  if(caseOf(t)==='photo')tests.push(t.photo_seen&&t.real?`<p class="sl-note">📸 ${x.esc(t.real.text)}</p>`:x.cmd('📸 Soi ảnh gốc chưa qua filter','sl_photo',{task:t.id},'small'));
  if(dye){
    if(t.patch_record==='allergy')tests.push('<p class="sl-note bad">🩹 Sổ dị ứng của tiệm ghi khách từng phản ứng với thuốc nhuộm — không thử lại, không nhuộm.</p>');
    else if(t.reacted)tests.push('<p class="sl-note bad">🩹 Vùng thử đỏ rát: đã ghi sổ dị ứng, bỏ phần màu.</p>');
    else tests.push(t.patch_done?'<p class="sl-note good">🩹 Đã chấm thử sau tai · hẹn nhuộm từ ngày sau.</p>'
      :x.cmd('🩹 Thử dị ứng sau tai','sl_patch',{task:t.id},'small',t.patch_record==='file'||t.patch_record==='log'));
  }
  if(bleach)tests.push(t.strand_text?`<p class="sl-note">🧵 ${x.esc(t.strand_text)}</p>`:x.cmd('🧵 Thử một lọn sau gáy','sl_strand',{task:t.id},'small'));
  const cta=t.plan?'':`<div class="sl-cta">${x.button('🤝 Sang chốt phương án →','car:tab',{task:t.id,tab:'plan',at:'consult'},'full')}</div>`;
  return `<div class="sl-qa-list">${qa}</div>
    <div class="sl-look"><h5 class="sl-sub">Xem tóc tận tay</h5><div class="sl-zones">${zones}</div></div>
    ${tests.length?`<div class="sl-tests"><h5 class="sl-sub">Thử & soi trước khi làm</h5><div class="stack">${tests.join('')}</div></div>`:''}${cta}`;
}

function planPanel(t,x){
  const u=ui(x,t),n=t.needs;
  if(started(t)&&t.plan)return `<p>${t.plan.services.map(s=>`${svc(x,s).emoji} ${x.esc(svc(x,s).name)}`).join(' · ')}</p><p class="small muted">${t.plan.sessions>1?`Lộ trình ${t.plan.sessions} buổi — hôm nay là buổi 1.`:'Làm trong một buổi.'} Báo giá ${x.money(t.quote)}.</p>`;
  const tiles=x.cc.services.map(s=>{
    const on=u.services.includes(s.id),asked=n.services.includes(s.id),advise=!asked&&s.id==='treatment'&&t.weak;
    return `<button type="button" class="sl-tile ${on?'selected':''} ${asked?'':advise?'advise':'extra'}" ${carAttr(x,'svc',{task:t.id,id:s.id})} aria-pressed="${on}"><span class="sl-emoji" aria-hidden="true">${s.emoji}</span><b>${x.esc(s.name)}</b><small>${x.money(price(x,s.id))} · ${asked?'khách yêu cầu':advise?'tóc yếu — nên phục hồi':'mời thêm'}</small></button>`;
  }).join('');
  const quote=u.services.reduce((a,s)=>a+price(x,s),0);
  const seg=[1,2,3].map(v=>`<button type="button" class="sl-seg ${u.sessions===v?'on':''}" ${carAttr(x,'sessions',{task:t.id,v})} aria-pressed="${u.sessions===v}">${v} buổi</button>`).join('');
  let warn=caseOf(t)==='photo'&&!t.photo_seen?'<p class="sl-note">📸 Chưa soi ảnh gốc — hứa theo ảnh filter là dễ vỡ mộng.</p>':'';
  if(t.weak)warn+=`<p class="sl-note bad">💧 Tóc ${t.health}/100 — yếu. Tóc dưới ${care(x).bleach_stop||30} thì chưa tẩy được.</p>`;
  const picked=x.cc.services.map(s=>s.id).filter(s=>u.services.includes(s));
  const same=!!t.plan&&u.sessions===t.plan.sessions&&picked.length===t.plan.services.length&&picked.every(s=>t.plan.services.includes(s));
  const label=!t.plan?'🤝 Chốt với khách':same?'✓ Đã chốt phương án này':'🔁 Chốt lại phương án';
  return `${warn}
    <div class="sl-grid">${tiles}</div>
    <h5 class="sl-sub">Số buổi để tới ảnh mẫu</h5><div class="sl-segs">${seg}</div>
    <div class="sl-cta"><b>Báo giá hôm nay: ${x.money(quote)}</b>${x.cmd(label,'sl_plan',{task:t.id,services:picked,sessions:u.sessions},'full',!u.services.length||same)}</div>`;
}

function timerBar(t,x){
  const tm=t.timer,w=tm.window,scale=Math.round(w.over*1.3);
  const pct=v=>Math.min(100,v/scale*100);
  const el=Math.max(0,x.now()-tm.start);
  return `<div class="sl-timer" data-sl-start="${tm.start}" data-under="${w.under}" data-ideal="${w.ideal}" data-over="${w.over}" data-scale="${scale}">
    <div class="sl-track"><i class="z under" style="width:${pct(w.under)}%"></i><i class="z ideal" style="left:${pct(w.under)}%;width:${pct(w.ideal)-pct(w.under)}%"></i><i class="z over" style="left:${pct(w.ideal)}%;width:${pct(w.over)-pct(w.ideal)}%"></i><i class="z damage" style="left:${pct(w.over)}%;width:${100-pct(w.over)}%"></i><b class="sl-fill" style="transform:translateX(${pct(el)-100}%)"></b></div>
    <div class="row spread wrap"><small class="sl-label" aria-live="off">${el.toFixed(1)} giây</small><small class="muted">Vùng xanh: ${w.under}–${w.ideal} giây${tm.fragile?' · tóc đã qua hóa chất':''}${tm.fast?' · trời nóng, thuốc lên nhanh':''}</small></div>
  </div>`;
}
function timerCard(t,x){
  return `<section class="sl-sec focus sl-timer-card"><div class="sl-bowl on"><span class="sl-emoji" aria-hidden="true">⏱️</span><div class="grow"><b>Đang ủ ${x.esc(svc(x,t.timer.kind).name.toLowerCase())}</b>${timerBar(t,x)}</div></div>${x.cmd('🚿 Xả thuốc ngay','sl_rinse',{task:t.id},'full sl-rinse-top')}</section>`;
}
function bowlLabel(x,b){
  if(b.kind==='bleach')return 'Bột tẩy';
  if(b.kind==='toner'){const s=x.cc.toners.find(d=>d.id===b.shade);return s?`${s.code} · ${s.tone}`:'Toner';}
  const a=dyeOf(x,b.shade);if(!a)return 'Thuốc nhuộm';
  if(b.mix?.b){const c=dyeOf(x,b.mix.b);return `${b.mix.pa} phần ${a.code} + ${b.mix.pb} phần ${c?c.code:'?'}`;}
  return `${b.mix?`${b.mix.pa} phần `:''}${a.code} · ${a.tone}`;
}
function bowlColour(x,b){
  if(b.kind==='bleach')return '';
  if(b.kind==='toner')return x.cc.toners.find(d=>d.id===b.shade)?.color||'';
  const a=dyeOf(x,b.shade);if(!a)return '';
  if(b.mix?.b){const c=dyeOf(x,b.mix.b);if(c)return blend([[a.color,b.mix.pa],[c.color,b.mix.pb]]);}
  return a.color;
}

/* ---------- the bowl preview ("bảng pha màu dự tính") ----------
 * Every pick shows what the bowl will give and what Linh will say, from the same rules the server applies
 * (bowlCheck) and only what has been found out. Nothing is mixed until "Trộn bát". */
const TONE_WORD={ash:'tro lạnh',cool:'hơi lạnh',natural:'tự nhiên',warm:'hơi ấm',deep:'ấm đậm'};
const CHART_WORD={ash:'tro',cool:'lạnh',natural:'tự nhiên',warm:'ấm',deep:'đậm'};
const CHART_RATIOS=[[1,1],[2,1],[3,1],[3,2]];
const levelName=(x,lv)=>x.cc.levels?.find(l=>l.level===Math.max(1,Math.min(10,Math.floor(lv+0.5))))?.name||'';
const num=n=>String(Math.round(n*100)/100).replace('.',',');
const cap1=s=>s.charAt(0).toUpperCase()+s.slice(1);
const pLine=(icon,text,tone='')=>`<li class="${tone}"><span aria-hidden="true">${icon}</span><span>${text}</span></li>`;
function colourVerdict(v,inp){
  if(inp.photoBlind)return ['📸 Ảnh có filter — soi ảnh gốc rồi hãy so','warn'];
  if(!inp.want)return ['Khách không cần bát nhuộm','bad'];
  if(v.hit)return v.nat_ok?['✓ Khớp màu khách cần','good']:['≠ Thiếu nền tự nhiên — thêm tuýp x.0','bad'];
  const bits=[];
  if(!v.level_ok){const d=v.dlv/v.mix.den;bits.push(`${d>0?'sáng':'tối'} hơn ${num(Math.abs(d))} tông`);}
  if(!v.band_ok)bits.push(v.dband>0?'ấm quá — thêm tuýp tro':'lạnh quá — thêm tuýp ánh vàng, đỏ');
  return ['≠ '+cap1(bits.join(' · ')),'bad'];
}
function devLine(x,t,u,v,inp){
  if(inp.photoBlind||!inp.want)return '';
  if(inp.want.dev==null)return pLine('🌱','Xem chân tóc để biết cần oxy mấy vol'+((t.grey==null)?' và có tóc bạc không':''));
  if(!u.dev)return '';
  const n=v.dev_note,dev=u.dev;
  if(n==='ok')return pLine('🧴',`Oxy ${dev} vol hợp${v.tones>0?` · nâng ${v.tones} tông`:''}`,'good');
  if(n==='dev40')return pLine('🧴','Oxy 40 vol không bao giờ thoa sát da đầu','bad');
  if(n==='weak')return pLine('🧴',v.cap?`Oxy ${dev} chỉ nâng ${v.cap} tông — cần ${v.need} vol`:`Oxy ${dev} không nâng tông — cần ${v.need} vol`,'bad');
  if(n==='cover')return pLine('🧴',`Phủ tóc bạc cần oxy ${v.need} vol`,'bad');
  if(n==='strong')return pLine('🧴',`Oxy ${dev} mạnh quá — chỉ cần ${v.need} vol`,'bad');
  return pLine('🧴',`Cần oxy ${v.need} vol`,'bad');
}
function colourPreview(t,x,u){
  const inp=previewInputs(t),tg=target(t);
  const v=bowlCheck(x.cc,'color',u.a,{b:u.b||null,pa:u.pa,pb:u.b?u.pb:0},u.dev,u.ratio,inp.want,inp.warm,inp.photoBlind,inp.lift);
  const m=v.mix;if(!m)return '';
  const [vt,vc]=colourVerdict(v,inp),lines=[];
  lines.push(devLine(x,t,u,v,inp));
  if(v.block)lines.push(pLine('🚫',`Màu nhuộm cũ (level ${inp.lift.dyed}) không nâng được — phải tẩy`,'bad'));
  if(inp.want&&u.ratio&&u.ratio!==inp.want.ratio)lines.push(pLine('🥣',`Thuốc nhuộm trộn ${fmtRatio(inp.want.ratio)} với oxy`,'bad'));
  if((t.grey||0)>=50)lines.push(pLine('🤍',`Tóc bạc ${t.grey}%: nền x.0 ${m.nat}/${m.den} phần${v.nat_ok?'':' — cần một nửa'}`,v.nat_ok?'good':'bad'));
  if(!t.findings?.lengths)lines.push(pLine('〰️','Chưa xem thân tóc — ánh thật có thể lệch'));
  else if(inp.warm)lines.push(pLine('🟠','Thân tóc ánh cam: bát ấm thêm một bậc (đã tính)'));
  const side=(sw,label,name,lv,dish)=>`<div class="sl-mp-side">${dish?`<span class="sl-dish big" style="--sw:${x.esc(sw)}" aria-hidden="true"></span>`:`<span class="sl-swatch" style="--sw:${x.esc(sw)}" aria-hidden="true"></span>`}<small>${label}</small><b>${x.esc(name)}</b><small>level ${x.esc(lv)}</small></div>`;
  const want=tg?side(levelColor(x,tg.level),t.real?'Ảnh gốc':'Khách cần',`${levelName(x,tg.level)} · ${TONE_WORD[tg.band]}`,String(tg.level),false):'';
  return `<div class="sl-mixprev" aria-live="polite"><div class="sl-mp-pair">${side(m.color,'Bát ra',`${levelName(x,m.lv/m.den)} · ${TONE_WORD[m.band]}`,v.text,true)}${want?`<span class="sl-mp-arrow" aria-hidden="true">→</span>${want}`:''}</div>
    <p class="sl-mp-verdict ${vc}">${x.esc(vt)}</p>${lines.filter(Boolean).length?`<ul class="sl-mp-lines">${lines.join('')}</ul>`:''}</div>`;
}
/** Bleach and toner bowls: the recipe check only (which toner once the bleach shows its tint, developer, ratio). */
function recipePreview(t,x,u){
  const kind=u.kind,want=recipeWant(t,kind);
  if(!want||(!u.dev&&!u.ratio&&!(kind==='toner'&&u.shade)))return '';
  const v=bowlCheck(x.cc,kind,kind==='bleach'?null:u.shade,null,u.dev,u.ratio,want),lines=[];
  const tn=kind==='toner'?x.cc.toners.find(d=>d.id===u.shade):null;
  if(kind==='toner'&&u.shade)lines.push(want.shade==null?pLine('🔎','Tẩy, xả xong mới soi được ánh nền')
    :want.shade===u.shade?pLine('💜','Khử đúng ánh đang có','good'):pLine('💜','Toner này không khử đúng ánh đang có','bad'));
  const name=kind==='bleach'?'Bột tẩy':'Toner';
  if(u.dev)lines.push(v.dev_note==='ok'?pLine('🧴',`Oxy ${u.dev} vol hợp`,'good'):v.dev_note==='dev40'?pLine('🧴','Oxy 40 vol không bao giờ thoa sát da đầu','bad'):pLine('🧴',`${name} dùng oxy ${want.dev} vol`,'bad'));
  if(u.ratio)lines.push(u.ratio===want.ratio?pLine('🥣',`Tỷ lệ ${fmtRatio(u.ratio)} hợp`,'good'):pLine('🥣',`${name} trộn ${fmtRatio(want.ratio)}`,'bad'));
  const ok=!v.issue;
  return `<div class="sl-mixprev" aria-live="polite">${tn?`<div class="sl-mp-pair"><div class="sl-mp-side"><span class="sl-dish big" style="--sw:${x.esc(tn.color)}" aria-hidden="true"></span><small>Bát ra</small><b>${x.esc(tn.tone)}</b></div></div>`:''}
    <p class="sl-mp-verdict ${ok?'good':'bad'}">${ok?'✓ Đúng bảng pha':'≠ Chưa đúng bảng pha'}</p><ul class="sl-mp-lines">${lines.join('')}</ul></div>`;
}
/** Bảng pha màu: tube × tube at one part ratio (row tube gets the first number); a tap fills the bowl. */
function mixChart(t,x,u){
  const inp=previewInputs(t),[p,q]=CHART_RATIOS.find(r=>r.join(':')===u.chartR)||CHART_RATIOS[0];
  const dyes=x.cc.dyes,head=d=>`<span class="sl-ch-head"><span class="sl-cap" style="--sw:${x.esc(d.color)}" aria-hidden="true"></span>${x.esc(d.code)}</span>`;
  const seg=CHART_RATIOS.map(r=>{const k=r.join(':');return `<button type="button" class="sl-seg ${k===(u.chartR||'1:1')?'on':''}" ${carAttr(x,'chartR',{task:t.id,v:k})} aria-pressed="${k===(u.chartR||'1:1')}">${r.join('∶')}</button>`;}).join('');
  const rows=dyes.map(a=>`${head(a)}${dyes.map(b=>{
    const same=a.id===b.id,pa=same?1:p,pb=same?0:q;
    const v=bowlCheck(x.cc,'color',a.id,{b:same?null:b.id,pa,pb},null,null,inp.want,inp.warm,inp.photoBlind,null);
    const m=v.mix,hit=!inp.photoBlind&&v.hit&&v.nat_ok,on=u.a===a.id&&(same?!u.b:u.b===b.id&&u.pa===pa&&u.pb===pb);
    const label=same?`${a.code}`:`${pa} phần ${a.code} + ${pb} phần ${b.code}`;
    return `<button type="button" class="sl-cell ${hit?'hit':''} ${on?'on':''} ${same?'solo':''} ${x.stock(a.id)&&(same||x.stock(b.id))?'':'out'}" ${carAttr(x,'cell',{task:t.id,a:a.id,b:same?'':b.id,pa,pb})} aria-label="${x.esc(`${label}: level ${v.text} ${TONE_WORD[m.band]}${hit?', khớp':''}`)}"><i style="--sw:${x.esc(m.color)}" aria-hidden="true">${hit?'✓':''}</i><b>${x.esc(v.text)}</b><small>${CHART_WORD[m.band]}</small></button>`;
  }).join('')}`).join('');
  return `<div class="sl-chart"><div class="sl-segs sl-ch-ratios" role="group" aria-label="Tỷ lệ hàng ∶ cột">${seg}</div>
    <p class="sl-ch-line">${p===q?'Mỗi tuýp 1 phần':`Hàng ${p} phần + cột ${q} phần`} · chạm ô để thử</p>
    <div class="sl-ch-grid" role="group" aria-label="Bảng pha màu"><span></span>${dyes.map(head).join('')}${rows}</div></div>`;
}

function mixer(t,x,u){
  const tubes=x.cc.dyes.map(d=>{
    const q=x.stock(d.id),role=u.a===d.id?'A':u.b===d.id?'B':'';
    return `<button type="button" class="sl-tube ${role?'selected':''}" ${carAttr(x,'tube',{task:t.id,v:d.id})} aria-pressed="${!!role}" aria-label="Tuýp ${x.esc(d.code)} ${x.esc(d.tone)}, còn ${q}${role?`, đang là tuýp ${role}`:''}" ${q||role?'':'disabled'}>${role?`<i class="sl-role" aria-hidden="true">${role}</i>`:''}<span class="sl-cap" style="--sw:${x.esc(d.color)}"></span><b>${x.esc(d.code)}</b><small>${x.esc(d.tone)}</small><em>${q}</em></button>`;
  }).join('');
  const part=(which,id,p)=>{const d=dyeOf(x,id);return `<div class="sl-part"><span><i class="sl-role" aria-hidden="true">${which.toUpperCase()}</i> ${x.esc(d?.code||'')}</span><button type="button" class="btn small ghost" ${carAttr(x,'part',{task:t.id,which,d:-1})} aria-label="Bớt một phần ${x.esc(d?.code||'')}" ${p<=1?'disabled':''}>−</button><b>${p} phần</b><button type="button" class="btn small ghost" ${carAttr(x,'part',{task:t.id,which,d:1})} aria-label="Thêm một phần ${x.esc(d?.code||'')}" ${p>=3?'disabled':''}>+</button></div>`;};
  const notes=[],cf=cardFormula(x,t);
  const cardLine=cf?`<div class="sl-note good sl-cardmix"><span>📇 Thẻ khách: <b>${x.esc(cf.text)}</b> → ${x.esc(cf.target)}</span>${x.button('📇 Pha theo thẻ','car:mixCard',{task:t.id},'small')}</div>`:'';
  if(caseOf(t)==='photo'&&!t.photo_seen)notes.push('📸 Ảnh mẫu có filter: soi ảnh gốc ở bước tư vấn để biết màu thật.');
  const chartBtn=`<button type="button" class="btn ghost small sl-chart-btn ${u.chart?'on':''}" ${carAttr(x,'chart',{task:t.id})} aria-expanded="${!!u.chart}">🎨 Bảng pha màu</button>`;
  return `${cardLine}<div class="row spread wrap sl-tubes-head"><h5 class="sl-sub">Tủ tuýp · chọn 1–2 tuýp</h5>${chartBtn}</div>${u.chart?mixChart(t,x,u):''}<div class="sl-tubes">${tubes}</div>
    ${u.a?`<div class="sl-parts">${part('a',u.a,u.pa)}${u.b?part('b',u.b,u.pb):''}</div>`:''}
    ${notes.map(v=>`<p class="sl-note">${x.esc(v)}</p>`).join('')}`;
}

function colorPanel(t,x){
  const left=chemLeft(t),u=ui(x,t);
  const results=Object.entries(t.results||{}).map(([k,r])=>`<li class="${r.zone==='ideal'&&r.ok?'ok':r.zone==='damage'||r.zone==='under'?'bad':'warn'}">${svc(x,k).emoji} ${x.esc(svc(x,k).name)}: ${x.esc(ZONE_TEXT[r.zone])} (${r.secs} giây)${r.ok?'':' · công thức lệch'}</li>`).join('');
  const mixRes=t.mix_result?`<p class="sl-note"><span class="sl-dot" style="--sw:${x.esc(t.mix_result.color)}" aria-hidden="true"></span> Màu đã lên: level ${x.esc(t.mix_result.level)} · ${x.esc(bandName(x,t.mix_result.band))}</p>`:'';
  const tail=`${results?`<ul class="sl-results">${results}</ul>`:''}${mixRes}${rules(x)}${palette(x)}`;
  if(t.timer)return tail;
  if(t.bowl){
    const b=t.bowl;
    return `<div class="sl-bowl"><span class="sl-dish" style="--sw:${x.esc(bowlColour(x,b))}" aria-hidden="true"></span><div class="grow"><b>Bát ${x.esc(svc(x,b.kind).name.toLowerCase())}</b><small>${x.esc(bowlLabel(x,b))} + oxy ${b.dev} vol · ${fmtRatio(b.ratio)}</small></div></div>
      ${b.ok?'':'<p class="sl-note bad">⚠️ Linh chê công thức bát này — nên đổ đi pha lại.</p>'}
      <div class="sl-cta">${x.cmd('🖌️ Thoa từ chân tới ngọn','sl_apply',{task:t.id},'full')}${x.confirmCmd('🗑️ Đổ bát, pha lại','sl_dump',{task:t.id,confirm:true},'Đổ bát thuốc này? Thuốc đã pha được ghi hao hụt.',b.ok?'danger small':'full')}</div>${tail}`;
  }
  if(!left.length)return tail||'<p class="muted small">Không còn phần hóa chất nào.</p>';
  if(!u.kind||!left.includes(u.kind))u.kind=left[0];
  const tabs=left.length>1?`<div class="sl-segs">${left.map(k=>`<button type="button" class="sl-seg ${u.kind===k?'on':''}" ${carAttr(x,'kind',{task:t.id,v:k})} aria-pressed="${u.kind===k}">${svc(x,k).emoji} ${x.esc(svc(x,k).name)}</button>`).join('')}</div>`:'';
  const mixing=u.kind==='color'&&t.gen;
  let pick='';
  if(u.kind==='bleach')pick=`<p class="small">⚗️ Bột tẩy · còn ${x.stock('bleach')} gói · giấy bạc ${x.stock('foil')} xấp</p>`;
  else if(mixing)pick=mixer(t,x,u);
  else{
    const list=u.kind==='color'?x.cc.dyes:x.cc.toners;
    if(!list.some(d=>d.id===u.shade))u.shade=null;
    pick=`<h5 class="sl-sub">Tủ tuýp ${u.kind==='toner'?'toner':'thuốc nhuộm'}</h5><div class="sl-tubes">${list.map(d=>{const q=x.stock(d.id);return `<button type="button" class="sl-tube ${u.shade===d.id?'selected':''}" ${carAttr(x,'shade',{task:t.id,v:d.id})} aria-pressed="${u.shade===d.id}" ${q?'':'disabled'}><span class="sl-cap" style="--sw:${x.esc(d.color)}"></span><b>${x.esc(d.code)}</b><small>${x.esc(d.tone)}</small><em>${q}</em></button>`;}).join('')}</div>`;
  }
  const devs=x.cc.devs.map(v=>{const q=x.stock('dev_'+v);return `<button type="button" class="sl-seg ${u.dev===v?'on':''} ${v===40?'hot':''}" ${carAttr(x,'dev',{task:t.id,v})} aria-pressed="${u.dev===v}" ${q||u.dev===v?'':'disabled'}>${v} vol<small>${q}</small></button>`;}).join('');
  const ratios=x.cc.ratios.map(r=>`<button type="button" class="sl-seg ${u.ratio===r?'on':''}" ${carAttr(x,'ratio',{task:t.id,v:r})} aria-pressed="${u.ratio===r}">${fmtRatio(r)}</button>`).join('');
  const {payload,ready,out,blocked}=bowlOrder(t,x,u);
  const outNote=out.length?`<div class="sl-note bad rs-inline"><span>📦 Hết ${out.map(id=>x.esc(itemName(x,id))).join(', ')} · hoặc chọn loại khác</span>${restockButton(x.room,out,{task:t.id},'small')}</div>`:'';
  return `${tabs}${pick}
    <h5 class="sl-sub">Oxy trợ nhuộm</h5><div class="sl-segs sl-devs">${devs}</div>
    <h5 class="sl-sub">Tỷ lệ thuốc ∶ oxy</h5><div class="sl-segs sl-ratios">${ratios}</div>
    ${blocked?'<p class="sl-note">Tẩy và xả xong rồi mới phủ toner.</p>':''}${mixing?(u.a?colourPreview(t,x,u):''):t.gen?recipePreview(t,x,u):''}${outNote}
    <div class="sl-cta">${x.cmd('🥣 Trộn bát','sl_mix',payload,'full sl-mix-go',!ready||blocked)}</div>${tail}`;
}
/** What "Trộn bát" sends with the current picks, and whether it can be sent. */
function bowlOrder(t,x,u){
  const mixing=u.kind==='color'&&t.gen;
  const blocked=u.kind==='toner'&&t.plan.services.includes('bleach')&&!t.done.includes('bleach');
  let payload,ready;
  if(mixing){payload={task:t.id,kind:'color',shade:u.a,parts:[u.pa,u.b?u.pb:0],dev:u.dev,ratio:u.ratio};if(u.b)payload.shade2=u.b;ready=!!(u.a&&u.dev&&u.ratio);}
  else{payload={task:t.id,kind:u.kind,dev:u.dev,ratio:u.ratio};if(u.kind!=='bleach')payload.shade=u.shade;ready=!!(u.dev&&u.ratio&&(u.kind==='bleach'||u.shade));}
  const need=[u.dev?'dev_'+u.dev:null,...(mixing?[u.a,u.b]:[u.kind==='bleach'?'bleach':u.shade]),u.kind==='bleach'?'foil':null].filter(Boolean);
  const out=need.filter(id=>!x.stock(id));
  if(out.length)ready=false;
  return {payload,ready:ready&&!blocked,out,blocked,mixing};
}

/** What sl_wash / sl_treat take from the shelf (game/careers/salon.py): one of each, refused when one is out. */
const WASH_ITEMS=['shampoo','conditioner','towel'],TREAT_ITEMS=['keratin'];
const outOf=(x,ids)=>ids.filter(id=>!x.stock(id));
/** "📦 Hết Khăn tắm: nhập ở Kho" + the restock button, shown before the tap instead of after it. */
const outLine=(x,t,out)=>out.length?`<div class="sl-note bad rs-inline"><span>📦 Hết ${out.map(id=>x.esc(itemName(x,id))).join(', ')}: nhập ở Kho</span>${restockButton(x.room,out,{task:t.id},'small')}</div>`:'';
function washPanel(t,x){
  const kid=caseOf(t)==='kid'&&t.calm!=null,out=t.washed?[]:outOf(x,WASH_ITEMS);
  return `${t.washed?'<p class="small">✅ Tóc đã gội, xả sạch.</p>':''}
    ${kid&&!t.washed?'<p class="sl-note">🧒 Bé nào gội xong cũng hay vẩy nước, bớt ngồi yên một chút.</p>':''}${outLine(x,t,out)}
    <div class="sl-cta">${x.cmd('🫧 Gội & xả','sl_wash',{task:t.id},'full',t.washed||!!t.timer||out.length>0)}</div>`;
}

function cutPanel(t,x){
  const u=ui(x,t),c=t.cut,s=c.steps,done=t.done.includes('cut'),kid=caseOf(t)==='kid'&&t.calm!=null,ask=t.cut_ask;
  // The client's word at the mirror (server-side, survives a reload): "still long" → cut more; "layers?" → layer.
  const next=!s.includes('section')?'section':!s.includes('guide')||ask==='long'?'guide':ask==='layers'?'layers':'check';
  const on=id=>id==='check'?done:s.includes(id);
  const step=(id,label,cond,payload={})=>`<li class="${on(id)?'done':''}">${(id==='check'?(l,c,p,st,dis)=>x.button(l,'car:cutCheck',{task:t.id,n:s.length},st,dis):x.cmd)(label,'sl_cut',{task:t.id,step:id,...payload},id===next&&!done?'primary':on(id)&&id!=='guide'?'ghost small':'small',done||!cond||!t.washed)}</li>`;
  let calm='';
  if(kid&&!done){
    const tools=(x.cc.calm_tools||[]).map(k=>`<button type="button" class="sl-chip ${t.soothed.includes(k.id)?'on':''}" ${cmdAttr(x,'sl_calm',{task:t.id,tool:k.id})} ${t.soothed.includes(k.id)?'disabled':''}><b>${k.emoji} ${x.esc(k.label)}</b></button>`).join('');
    calm=`<div class="sl-kid">${calmBar(t)}${t.calm<40?'<p class="sl-note bad">⚠️ Bé đang giãy — cầm kéo lúc này dễ lẹm. Dỗ bé trước đã.</p>':''}<h5 class="sl-sub">Dỗ bé (nghe bố kể thói quen của bé)</h5><div class="sl-calm-tools">${tools}</div></div>`;
  }
  return `${calm}
    <div class="sl-len"><span>Độ dài cắt bớt</span><button type="button" class="btn small ghost" ${carAttr(x,'len',{task:t.id,d:-1})} aria-label="Bớt 1 cm">−</button><b>${u.len} cm</b><button type="button" class="btn small ghost" ${carAttr(x,'len',{task:t.id,d:1})} aria-label="Thêm 1 cm">+</button><small class="muted">Đã bớt tổng ${c.removed} cm${c.short?' · ⚠️ lẹm':''}</small></div>
    ${ask==='long'&&!done?'<p class="sl-note">🪞 Khách soi gương thấy còn dài — chọn số cm rồi cắt thêm, soi lại.</p>':''}
    <ol class="sl-steps">${step('section','1 · Chia vùng',!s.length)}${step('guide',s.includes('guide')?`2 · Cắt thêm (${u.len} cm)`:`2 · Cắt đường chuẩn (${u.len} cm)`,s.includes('section'),{length:u.len})}${step('layers','3 · Tỉa tầng',s.includes('guide')&&!s.includes('layers'))}${step('check','4 · Soi đối xứng & chốt',s.includes('guide'))}</ol>
    ${done?'<p class="sl-note good">✂️ Đã cắt xong.</p>':''}`;
}

function finishPanel(t,x){
  const ps=t.plan.services,parts=[];
  if(ps.includes('treatment')){const done=t.done.includes('treatment'),out=done?[]:outOf(x,TREAT_ITEMS);
    parts.push(`<div class="sl-cta"><p class="small">💧 Keratin phục hồi · còn ${x.stock('keratin')} lượt</p>${outLine(x,t,out)}${x.cmd(done?'✅ Đã phục hồi':'💧 Thoa keratin & hấp','sl_treat',{task:t.id},'full',done||out.length>0)}</div>`);}
  if(ps.includes('style')){
    const wait=ps.includes('treatment')&&!t.done.includes('treatment');
    parts.push(`<h5 class="sl-sub">Kiểu sấy hợp thói quen & dịp của khách</h5><div class="sl-grid sl-finishes">${x.cc.finishes.map(f=>`<button type="button" class="sl-tile ${t.styled===f.id?'selected':''}" ${cmdAttr(x,'sl_style',{task:t.id,finish:f.id})} ${t.done.includes('style')||wait?'disabled':''}><span class="sl-emoji" aria-hidden="true">${f.emoji}</span><b>${x.esc(f.name)}</b><small>${x.esc(f.note)}</small></button>`).join('')}</div>`);
  }
  return parts.join('')||'<p class="muted small">Không có phần hoàn thiện.</p>';
}

function receipt(t,x,folded=false){
  const ps=t.plan?.services||[];
  const rows=ps.map(s=>`<li class="${t.done.includes(s)?'ok':''}"><span>${t.done.includes(s)?'✓':'○'} ${svc(x,s).emoji} ${x.esc(svc(x,s).name)}</span><b>${x.money(price(x,s))}</b></li>`).join('');
  const fee=t.patch_fee?`<li class="ok"><span>✓ 🩹 Thử dị ứng</span><b>${x.money(t.patch_fee)}</b></li>`:'';
  if(folded){
    const done=ps.filter(s=>t.done.includes(s)).length,sum=ps.reduce((a,s)=>a+price(x,s),0)+(t.patch_fee||0);
    return `<details class="sl-bill sl-bill-fold"><summary><b>🧾 Phiếu dịch vụ</b><small>${ps.length?`${done}/${ps.length} xong · ${x.money(sum)}`:'chưa chốt phương án'}</small></summary><ul>${rows||'<li class="muted">Chưa chốt phương án</li>'}${fee}</ul></details>`;
  }
  return `<div class="sl-bill"><h4>🧾 Phiếu dịch vụ</h4><ul>${rows||'<li class="muted">Chưa chốt phương án</li>'}${fee}</ul></div>`;
}

/** The money the checkout will count: the services as quoted, the products only if the client takes them,
 * the rush thank-you only when on time (same rules as sl_checkout). */
function billLines(t,x,retailSum){
  const svcSum=(t.quote||0)+(t.patch_fee||0),left=rushLeft(t,x),bonus=left!=null&&left>=0?(t.needs?.rush?.bonus||0):0;
  const row=(k,v,cls='')=>`<p class="row spread ${cls}"><span>${k}</span><b>${x.money(v)}</b></p>`;
  return row('Dịch vụ',svcSum)+(retailSum?row('Sản phẩm mời (khách có thể không lấy)',retailSum):'')+(bonus?row('Tiền gấp nếu kịp giờ',bonus):'')
    +(retailSum||bonus?row('Tạm tính tối đa',svcSum+retailSum+bonus):'')+'<small class="muted">Làm sai, khách có thể bớt tiền dịch vụ.</small>';
}

function billPanel(t,x){
  const u=ui(x,t),ps=t.plan?.services||[];
  const shelf=(x.cc.retail||[]).map(r=>{const on=u.products.includes(r.id),q=x.stock(r.id);return `<button type="button" class="sl-chip ${on?'on':''}" ${carAttr(x,'product',{task:t.id,id:r.id})} aria-pressed="${on}" ${q?'':'disabled'}>${r.emoji} ${x.esc(r.name)} · ${x.money(r.price)}<small>${q} trên kệ</small></button>`;}).join('');
  const retailSum=u.products.reduce((a,id)=>a+retail(x,id).price,0);
  const pending=ps.filter(s=>!t.done.includes(s));
  const ready=t.plan&&!pending.length&&!t.bowl&&!t.timer;
  return `${receipt(t,x)}
    <h5 class="sl-sub" title="Chỉ mời khi hợp tóc và vừa ngân sách">🛍️ Sản phẩm hợp tóc (tùy chọn)</h5><div class="sl-chips">${shelf}</div>
    ${bookBlock(t,x)}
    ${billLines(t,x,retailSum)}
    <div class="sl-cta">${x.confirmCmd('💳 Thanh toán & tiễn khách','sl_checkout',{task:t.id,products:u.products,book:u.book.filter(k=>(t.bookable||[]).includes(k)),confirm:true},'Thanh toán cho khách? Khách sẽ soi gương và đánh giá đúng những gì đã làm; sản phẩm không hợp sẽ bị từ chối.','full',!ready)}</div>
    ${pending.length&&t.plan?`<small class="muted">Còn: ${pending.map(s=>x.esc(svc(x,s).name.toLowerCase())).join(', ')}</small>`:''}`;
}

function mirror(t,x){
  const lk=t.look||{};
  const len=Math.max(4,Math.min(46,lk.length||10));
  return `<div class="sl-mirror" role="img" aria-label="Gương: tóc level ${lk.level||'?'}, dài khoảng ${lk.length||'?'} cm">
    <div class="sl-glass"><div class="sl-head" style="--hair:${x.esc(lk.color||'')};--len:${len}"><i class="sl-back"></i><i class="sl-face"></i><i class="sl-fringe"></i></div></div>
    <small>Level ${lk.level||'?'} · dài ~${lk.length||'?'} cm</small></div>`;
}

/** Scroll the sheet so `el` sits just under the sticky header (only when it is out of view). */
let revealed='';
function reveal(root,el){
  const dialog=root.closest('dialog');if(!dialog||!el)return;
  let box=root.parentElement;
  while(box&&box!==dialog.parentElement&&!(box.scrollHeight>box.clientHeight&&/(auto|scroll)/.test(getComputedStyle(box).overflowY)))box=box.parentElement;
  if(!box||box===dialog.parentElement)return;
  const top=(dialog.querySelector('.sheet-head')?.getBoundingClientRect().bottom||box.getBoundingClientRect().top)+8;
  const bottom=root.querySelector('.sl-bar')?.getBoundingClientRect().top||innerHeight;
  const r=el.getBoundingClientRect(),room=bottom-8-top;
  if(r.top>=top&&r.bottom<=bottom-8)return;
  // Fits: show all of it (its end first, where new results land); too tall: its top under the header.
  const by=r.height<=room?(r.bottom>bottom-8?r.bottom-(bottom-8):r.top-top):r.top-top;
  box.scrollBy({top:by,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
}

const PANELS={consult,plan:planPanel,color:colorPanel,wash:washPanel,cut:cutPanel,finish:finishPanel,bill:billPanel};

/* ---------- next step (v4/guide.js) ----------
 * The chair as steps: the header hint, the bottom button and the checklist all come from guideOf().
 * On a first task every decision is made for the stylist from what the screen already shows
 * (answers, findings, the photo, the colour table); later the button points at the choice instead. */
const nfc=s=>String(s||'').normalize('NFC');
const NUM_WORD={'một':1,'hai':2,'ba':3,'bốn':4,'năm':5,'sáu':6};
/** What to ask and which zones to look at before planning these services. */
function consultNeeds(t){
  const s=t.needs.services,chem=s.some(k=>CHEM.includes(k)),care=s.includes('treatment'),asks=[],looks=[];
  if(chem||care)asks.push('history');
  if(s.includes('color')||s.includes('toner'))asks.push('patch');
  if(s.includes('style')||caseOf(t)==='kid')asks.push('lifestyle');
  if(s.includes('cut'))asks.push('length');
  if(s.includes('color'))looks.push('roots');
  if(chem||care)looks.push('lengths');
  if(s.includes('cut')||care)looks.push('ends');
  if(chem)looks.push('scalp');
  return {asks,looks};
}
/** The honest plan from what was found out: no dye without a patch result, no chemicals on a hurt scalp, sessions from the strand test. */
function smartPlan(t,x){
  const noDye=t.patch_done||t.reacted||['none','allergy'].includes(t.patch_record);
  const hurt=/không thoa hóa chất/.test(nfc(t.findings?.scalp));
  const weak=t.health!=null&&t.health<(care(x).bleach_stop||30);
  const keep=t.needs.services.filter(s=>!(noDye&&(s==='color'||s==='toner'))&&!(hurt&&CHEM.includes(s))&&!(weak&&(s==='bleach'||s==='toner')));
  const m=/(\d)\s*buổi/.exec(nfc(t.strand_text));
  return {services:x.cc.services.map(s=>s.id).filter(id=>keep.includes(id)),sessions:m?Number(m[1]):1};
}
/** The bowl the colour table gives for this client (tubes that hit level and tone, developer by lift, ratio by kind). */
function smartMix(t,x,kind){
  if(kind==='bleach')return {kind,dev:20,ratio:'1:2'};
  if(kind==='toner')return {kind,shade:/khói|bạc|tro|lạnh/i.test(nfc(t.needs.photo?.tone))?'toner_silver':'toner_beige',dev:10,ratio:'1:2'};
  const tg=target(t);if(!tg||!t.gen)return null;
  const warm=t.base_warm||0,grey=(t.grey||0)>=50,dyes=x.cc.dyes.filter(d=>x.stock(d.id)>0);
  const hit=m=>m&&levelOk(m,tg.level)&&m.band===tg.band&&(!grey||2*m.nat>=m.den);
  let best=null;
  for(const d of dyes)if(!best&&hit(mixOf(x,d.id,null,1,0,warm)))best={a:d.id,b:null,pa:1,pb:1};
  for(let den=2;den<=6&&!best;den++)for(const a of dyes)for(const b of dyes)for(let pa=1;pa<=3&&!best;pa++){
    const pb=den-pa;if(a!==b&&pb>=1&&pb<=3&&hit(mixOf(x,a.id,b.id,pa,pb,warm)))best={a:a.id,b:b.id,pa,pb};
  }
  if(!best)return null;
  const lift=tg.level-(t.look?.level||tg.level),cover=(t.grey||0)>0||/phủ bạc/i.test(nfc(t.needs.want));
  return {kind,...best,dev:t.recipe?.color?.dev??(lift>=3?30:lift>=1||cover?20:10),ratio:'1:1'};
}
function mixText(x,m){
  const code=id=>dyeOf(x,id)?.code||x.cc.toners.find(d=>d.id===id)?.code||'';
  const tubes=m.kind==='bleach'?'bột tẩy':m.kind==='toner'?code(m.shade):m.b?`${m.pa} phần ${code(m.a)} + ${m.pb} phần ${code(m.b)}`:code(m.a);
  return `${tubes} · oxy ${m.dev} vol · ${fmtRatio(m.ratio)}`;
}
const sameMix=(u,m)=>u.dev===m.dev&&u.ratio===m.ratio&&(m.kind==='bleach'||(m.kind==='toner'?u.shade===m.shade:u.a===m.a&&(u.b||null)===m.b&&u.pa===m.pa&&(!m.b||u.pb===m.pb)));
/** Centimetres to take off, read from what the client said about length and what the ends showed. */
function smartLen(t){
  const say=nfc(t.answers?.length),ends=nfc(t.findings?.ends);
  let m=/dài\s*(\d+)\s*phân.*?(\d+)\s*[–-]\s*(\d+)\s*phân/.exec(say);
  if(m)return Math.max(1,Number(m[1])-Math.round((Number(m[2])+Number(m[3]))/2));
  for(const s of [say,ends]){
    m=/(\d+)\s*(?:[–-]\s*\d+\s*)?(?:cm|phân)/.exec(s);if(m)return Math.max(1,Math.min(10,Number(m[1])));
    m=/(một|hai|ba|bốn|năm|sáu)(?:\s+(?:một|hai|ba|bốn|năm|sáu))?\s+phân/.exec(s);if(m)return NUM_WORD[m[1]];
  }
  return null;
}
const wantsLayers=t=>/tầng/.test(nfc(`${t.needs.want} ${t.needs.photo?.style||''}`));
function smartFinish(t){
  const s=nfc(`${t.needs.want} ${t.needs.photo?.style||''}`).toLowerCase();
  return /búi/.test(s)?'updo':/phồng|sóng/.test(s)?'volume':/suôn|thẳng/.test(s)?'sleek':'natural';
}
function smartCalm(t){
  const s=nfc(t.answers?.lifestyle);
  return /hoạt hình/.test(s)?'cartoon':/khủng long/.test(s)?'toy':/tượng đá/.test(s)?'game':/bố/.test(s)?'lap':null;
}
/** The tab on screen (same rule as job()). */
function viewTab(t,u){
  const list=stages(t),at=current(t),ai=list.indexOf(at);
  if(u.tab!=null&&u.tabAt!==at)u.tab=null;
  const reach=s=>list.includes(s)&&(list.indexOf(s)<=ai||(s==='plan'&&!t.plan));
  return {list,at,tab:u.tab&&reach(u.tab)?u.tab:at};
}
const svcNames=(x,ids)=>ids.map(s=>svc(x,s).name.toLowerCase()).join(', ');

/** {steps, final, timer} for this client right now. */
function guideOf(t,x){
  const id=t.id,first=firstTime(x),d=x.room.data||{};
  if(t.timer)return {steps:[{ok:null,label:'Chờ vùng xanh rồi xả thuốc',go:{sel:'.sl-timer'}}],timer:true};
  if(d.desk?.ev)return {steps:[{ok:null,label:'Ra quầy: chọn một cách xử lý',go:{sel:'.sl-desk .sl-opts'},pulse:first?'.sl-desk .sl-opt':''}]};
  const steps=[];
  if(!t.tools&&!(Number(d.clean)>0)&&current(t)!=='bill')
    steps.push({ok:null,label:'Khử khuẩn dụng cụ',go:{cmd:'sl_sanitize',payload:{},label:'🧴 Khử khuẩn dụng cụ'}});
  if(!t.known){
    steps.push({ok:null,label:'Mời khách ngồi, nghe mong muốn',go:{cmd:'ask',payload:{task:id},label:'💬 Mời ngồi & nghe mong muốn'}});
    return {steps};
  }
  const u=ui(x,t),{at,tab}=viewTab(t,u);
  if(!t.plan){
    const {asks,looks}=consultNeeds(t),topic=k=>x.cc.topics.find(q=>q.id===k),zone=k=>x.cc.zones.find(z=>z.id===k);
    const q=asks.find(k=>!t.asked.includes(k)),z=looks.find(k=>!t.inspected.includes(k));
    if(asks.length)steps.push({ok:q?null:true,label:`Hỏi: ${asks.map(k=>topic(k).label.toLowerCase()).join(', ')}`,note:`${asks.filter(k=>t.asked.includes(k)).length}/${asks.length}`,
      go:q&&{cmd:'sl_consult',payload:{task:id,topic:q},label:`${topic(q).emoji} Hỏi khách: ${x.esc(topic(q).label.toLowerCase())}`}});
    if(looks.length)steps.push({ok:z?null:true,label:`Xem tận tay: ${looks.map(k=>zone(k).label.toLowerCase()).join(', ')}`,note:`${looks.filter(k=>t.inspected.includes(k)).length}/${looks.length}`,
      go:z&&{cmd:'sl_inspect',payload:{task:id,zone:z},label:`${zone(z).emoji} Xem ${x.esc(zone(z).label.toLowerCase())}`}});
    if(caseOf(t)==='photo'&&!t.photo_seen)steps.push({ok:null,label:'Soi ảnh gốc chưa qua filter',go:{cmd:'sl_photo',payload:{task:id},label:'📸 Soi ảnh gốc'}});
    const dye=t.needs.services.some(s=>s==='color'||s==='toner');
    if(dye&&t.patch_record==='none'&&!t.patch_done&&!t.reacted)
      steps.push({ok:null,label:'Thử dị ứng sau tai',go:{cmd:'sl_patch',payload:{task:id},label:'🩹 Thử dị ứng sau tai'}});
    if(t.needs.services.includes('bleach')&&!t.strand)steps.push({ok:null,label:'Thử một lọn trước khi tẩy',go:{cmd:'sl_strand',payload:{task:id},label:'🧵 Thử một lọn sau gáy'}});
    let go=null;
    if(first){const p=smartPlan(t,x);if(p.services.length)go={cmd:'sl_plan',payload:{task:id,...p},label:`🤝 Chốt: ${x.esc(svcNames(x,p.services))}${p.sessions>1?` · ${p.sessions} buổi`:''}`};}
    else if(tab!=='plan')go={act:'car:tab',data:{task:id,tab:'plan',at},label:'🤝 Sang chốt phương án'};
    else if(u.services.length){const picked=x.cc.services.map(s=>s.id).filter(s=>u.services.includes(s));
      go={cmd:'sl_plan',payload:{task:id,services:picked,sessions:u.sessions},label:`🤝 Chốt: ${x.esc(svcNames(x,picked))}${u.sessions>1?` · ${u.sessions} buổi`:''}`};}
    else go={sel:'.sl-grid',label:'👉 Chọn dịch vụ cho khách'};
    steps.push({ok:null,label:'Chốt phương án với khách',go});
    return {steps};
  }
  if(at==='color'){
    const b=t.bowl;
    if(b){
      if(b.ok)steps.push({ok:null,label:'Thoa thuốc',go:{cmd:'sl_apply',payload:{task:id},label:'🖌️ Thoa thuốc từ chân tới ngọn'}});
      else steps.push({ok:false,label:'Bát sai: đổ, pha lại',go:{cmd:'sl_dump',payload:{task:id,confirm:true},confirm:'Đổ bát thuốc này? Thuốc đã pha được ghi hao hụt.',label:'🗑️ Đổ bát, pha lại'}});
      return {steps};
    }
    const left=chemLeft(t);if(!u.kind||!left.includes(u.kind))u.kind=left[0];
    const o=bowlOrder(t,x,u),kind=u.kind,sm=first?smartMix(t,x,kind):null,here=tab==='color';
    const go=sel=>here?{sel}:{act:'car:tab',data:{task:id,tab:'color',at},label:'🎨 Về bàn pha màu'};
    if(sm){
      steps.push({ok:sameMix(u,sm)||null,label:`Lấy thuốc theo bảng pha: ${mixText(x,sm)}`,go:sameMix(u,sm)?null:{act:'car:autoMix',data:{task:id},label:`✨ Lấy theo bảng: ${x.esc(mixText(x,sm))}`}});
    }else{
      const tube=kind==='bleach'||(o.mixing?!!u.a:!!u.shade);
      steps.push({ok:tube||null,label:kind==='bleach'?'Bột tẩy':kind==='toner'?'Chọn tuýp toner':'Chọn tuýp màu',go:tube?null:go('.sl-tubes')});
      steps.push({ok:u.dev?true:null,label:'Chọn oxy',go:u.dev?null:go('.sl-devs')});
      steps.push({ok:u.ratio?true:null,label:'Chọn tỷ lệ thuốc ∶ oxy',go:u.ratio?null:go('.sl-ratios')});
    }
    steps.push({ok:null,label:`Trộn bát ${svc(x,kind).name.toLowerCase()}`,go:o.ready?{cmd:'sl_mix',payload:o.payload,label:'🥣 Trộn bát'}:o.out.length?restockFor(x,o.out,o.out.map(k=>itemName(x,k)).join(', '),{task:id}):null});
    return {steps};
  }
  if(at==='wash'){const out=outOf(x,WASH_ITEMS);steps.push({ok:null,label:'Gội & xả cho khách',go:out.length?restockFor(x,out,out.map(k=>itemName(x,k)).join(', '),{task:id}):{cmd:'sl_wash',payload:{task:id},label:'🫧 Gội & xả'}});return {steps};}
  if(at==='cut'){
    const s=t.cut.steps,cut=(step,extra={})=>({cmd:'sl_cut',payload:{task:id,step,...extra}});
    if(caseOf(t)==='kid'&&t.calm!=null&&!s.includes('guide')&&t.calm<40+(s.includes('section')?0:12+3*(Number(d.tier)||0))){
      const best=first&&smartCalm(t),tool=best&&!t.soothed.includes(best)?best:null;
      steps.push({ok:null,label:'Dỗ bé ngồi yên',go:tool?{cmd:'sl_calm',payload:{task:id,tool},label:`${x.cc.calm_tools.find(k=>k.id===tool)?.emoji||'🧒'} Dỗ bé: ${x.esc(x.cc.calm_tools.find(k=>k.id===tool)?.label||'')}`}:{sel:'.sl-calm-tools',label:'🧒 Chọn cách dỗ bé'}});
      return {steps};
    }
    const len=first?smartLen(t)??u.len:u.len;
    // A symmetry check the client did not accept ("còn dài" / "mẫu có tầng") reopens the step it asks for
    // (t.cut_ask comes from the server, so it is still there after a reload; also after layering: feedback #67).
    const fail=t.cut_ask||null;
    steps.push({ok:s.includes('section')||null,label:'Chia vùng tóc',go:s.includes('section')?null:{...cut('section'),label:'✂️ Chia vùng tóc'}});
    const more=fail==='long',canGuide=s.includes('section')&&(!s.includes('guide')||more);
    const guideGo=!canGuide?null:first&&!more||u.lenSet?{...cut('guide',{length:len}),label:`✂️ ${more?'Cắt thêm':'Cắt đường chuẩn · bớt'} ${len} cm`}:{sel:'.sl-len',label:`📏 Chọn số cm cắt ${more?'thêm':'bớt'}`};
    steps.push({ok:s.includes('guide')&&!more||null,label:more?'Khách thấy còn dài: cắt thêm':'Cắt đường chuẩn',note:s.includes('guide')?`đã bớt ${t.cut.removed} cm`:'',go:guideGo});
    const layers=(first&&wantsLayers(t))||fail==='layers';
    if(layers)steps.push({ok:s.includes('layers')||null,label:'Tỉa tầng nhẹ (mẫu có tầng)',go:s.includes('guide')&&!s.includes('layers')?{...cut('layers'),label:'✂️ Tỉa tầng'}:null});
    steps.push({ok:null,label:'Soi đối xứng & chốt',go:s.includes('guide')&&!more&&(!layers||s.includes('layers'))?{act:'car:cutCheck',data:{task:id,n:s.length},label:'🪞 Soi đối xứng & chốt'}:null});
    return {steps};
  }
  if(at==='finish'){
    const ps=t.plan.services;
    if(ps.includes('treatment')){const out=outOf(x,TREAT_ITEMS);
      steps.push({ok:t.done.includes('treatment')||null,label:'Thoa keratin & hấp',go:t.done.includes('treatment')?null:out.length?restockFor(x,out,out.map(k=>itemName(x,k)).join(', '),{task:id}):{cmd:'sl_treat',payload:{task:id},label:'💧 Thoa keratin & hấp'}});}
    if(ps.includes('style')&&!t.done.includes('style')){
      const wait=ps.includes('treatment')&&!t.done.includes('treatment'),f=first?smartFinish(t):null,fin=x.cc.finishes.find(v=>v.id===f);
      steps.push({ok:null,label:'Sấy tạo kiểu',go:wait?null:fin?{cmd:'sl_style',payload:{task:id,finish:fin.id},label:`${fin.emoji} Sấy: ${x.esc(fin.name.toLowerCase())}`}:{sel:'.sl-finishes',label:'💨 Chọn kiểu sấy hợp khách'}});
    }
    return {steps};
  }
  return {steps,bill:true};
}
/** The finishing button: pay and see the client off once every service is done. */
function billFinal(t,x,steps){
  const u=ui(x,t),ps=t.plan?.services||[],ready=!!t.plan&&ps.every(s=>t.done.includes(s))&&!t.bowl&&!t.timer;
  return {label:'💳 Thanh toán & tiễn khách',ready,go:finalGo(steps,'sl_checkout',{task:t.id,products:u.products,book:u.book.filter(k=>(t.bookable||[]).includes(k))},{question:'Khách sẽ soi gương và đánh giá.',confirm:true})};
}
/** While the dye processes: the bottom button counts down, then turns into "rinse" in the green zone (tick() swaps them). */
function timerCta(t,x){
  const tm=t.timer,w=tm.window||{under:0},s=Math.max(0,x.now()-tm.start),on=s>=w.under;
  return `<button type="button" class="btn primary big grow gd-cta sl-wait" data-action="v4Go" data-sel=".sl-timer"${on?' hidden':''}><span>⏳ Chờ vùng xanh · còn <b class="sl-left">${Math.max(1,Math.ceil(w.under-s))}</b> giây</span></button>`
    +`<button type="button" class="btn primary big grow gd-cta sl-rinse-go" ${cmdAttr(x,'sl_rinse',{task:t.id})}${on?'':' hidden'}>🚿 Xả thuốc ngay!</button>`;
}
function guideBits(t,x){
  const g=guideOf(t,x),first=firstTime(x);
  const final=g.bill?billFinal(t,x,g.steps):null;
  const hint=nextHint(x,g.steps,{final:final?.ready?{label:'Thanh toán & tiễn khách',go:final.go}:null});
  const cta=g.timer?timerCta(t,x):stepCta(x,g.steps,final||{label:'💳 Thanh toán & tiễn khách',go:null,ready:false});
  const k=g.steps.filter(s=>s&&s.ok!==true).length;
  return {g,hint,bar:`<div class="sl-bar"${first?' data-first="1"':''}>${cta}</div>`,rows:g.steps.length?`<details class="sl-todo-fold"><summary>📝 Việc cần làm <small>· ${k?`còn ${k}`:'xong hết'}/${g.steps.length}</small></summary>${stepRows(x,g.steps,'Việc cần làm')}</details>`:''};
}

export default {
  id:'salon',
  css:true,
  next(t,x){
    try{const n=x?.room&&pending(guideOf(t,x).steps);if(n)return stepLine(n);}catch{/* fall back to the fixed lines */}
    if(t.timer)return 'Xả thuốc khi thanh vào vùng xanh';
    if(x?.room?.data?.desk?.ev)return 'Có chuyện ở quầy cần quyết';
    if(!t.known)return x?.room?.data&&!x.room.data.clean?'Khử khuẩn dụng cụ, rồi mời khách ngồi':'Mời khách ngồi, nghe mong muốn';
    if(!t.plan){
      if(caseOf(t)==='photo'&&!t.photo_seen&&t.asked.length)return 'Soi ảnh gốc trước khi hứa màu';
      return t.asked.length<2?'Hỏi lịch sử tóc & xem tận tay':'Chốt phương án thật lòng';
    }
    if(t.bowl)return t.bowl.ok?'Thoa bát thuốc vừa pha':'Đổ bát pha sai, pha lại';
    const left=chemLeft(t);
    if(left.length)return 'Pha bát '+({color:'nhuộm',bleach:'tẩy',toner:'toner'}[left[0]]);
    if(!t.washed)return 'Gội & xả cho khách';
    const p=t.plan.services.filter(s=>!t.done.includes(s));
    if(p.includes('cut'))return caseOf(t)==='kid'&&t.calm<40?'Dỗ bé ngồi yên rồi mới cắt':'Cắt theo trình tự';
    if(p.includes('treatment'))return 'Phục hồi keratin';
    if(p.includes('style'))return 'Sấy tạo kiểu';
    return 'Thanh toán, tư vấn sản phẩm';
  },
  idle(x){
    const d=x.room.data||{};
    const stats=`<div class="row wrap sl-stats">${x.pill(`💇 ${d.day_served||0} khách hôm nay`)}${x.pill(`🧾 ${d.served||0} khách tất cả`)}${d.appts_done?x.pill(`📅 ${d.appts_done} lượt hẹn`,'green'):''}${d.mixes?x.pill(`🎨 ${d.mixes} bát pha trúng`,'green'):''}${d.rush_on_time?x.pill(`⏱️ ${d.rush_on_time} lần kịp giờ`,'green'):''}${d.kids_calm?x.pill(`🧒 ${d.kids_calm} bé cắt êm`,'green'):''}${d.allergy?x.pill(`🩹 ${d.allergy} khách trong sổ dị ứng`,'amber'):''}</div>`;
    const steps=d.desk?.ev?[{ok:null,label:'Ra quầy: chọn một cách xử lý',go:{sel:'.sl-desk .sl-opts'},pulse:firstTime(x)?'.sl-desk .sl-opt':''}]
      :!(Number(d.clean)>0)&&x.room.open?[{ok:null,label:'Khử khuẩn dụng cụ',go:{cmd:'sl_sanitize',payload:{},label:'🧴 Khử khuẩn dụng cụ'}}]:[];
    return `<div class="career-job sl sl-idle">${nextHint(x,steps,{cta:false})}${deskCard(x)}${lastDesk(x)}${todayChip(x)}${foot(x)}${apptBook(x,true)}${stats}${regularsBook(x)}${rules(x)}</div>`;
  },
  job(t,x){
    const desk=deskCard(x),who=x.npc(t.npc),gb=guideBits(t,x);
    if(!t.known){
      const back=t.regular!=null?`<p class="sl-note good">📇 Khách quen quay lại — thẻ khách đã có công thức, sức khỏe tóc và lần cắt trước.</p>`:'';
      return `<div class="career-job sl">${gb.hint}${desk}${todayChip(x,true)}<article class="sl-ticket"><div class="row">${x.portrait(who,56)}<div class="grow"><h3>${x.esc(who.display_name)}</h3><p>“${x.esc(t.opening)}”</p></div></div>${back}</article>${foot(x,true)}${apptBook(x,false)}${gb.bar}</div>`;
    }
    if(desk)return `<div class="career-job sl">${gb.hint}${t.timer?timerCard(t,x):''}${desk}${ticket(t,x)}${gb.bar}</div>`;
    const u=ui(x,t),{list,at,tab}=viewTab(t,u);
    const back=tab!==at&&!(tab==='plan'&&!t.plan)?` <button type="button" class="btn ghost small" ${carAttr(x,'tab',{task:t.id,tab:at,at})}>Về bước đang làm</button>`:'';
    // After a step the panel (or the running timer) scrolls up under the header so the result is in view (tick → reveal).
    const key=[t.id,tab,at,t.asked.length,t.inspected.length,t.bowl?1:0,t.timer?1:0,t.cut.steps.length,t.done.length].join('|');
    const moved=!!t.plan||t.asked.length+t.inspected.length>0||tab!==at;
    const nx=pending(gb.g.steps)?.go?.cmd,focus=tab!=='consult'?'':nx==='sl_inspect'?'.sl-look':nx==='sl_consult'?'.sl-qa-list':/^sl_(patch|photo|strand)$/.test(nx||'')?'.sl-tests':'';
    const panel=`<section class="sl-sec sl-panel ${tab===at?'focus':''}" data-sl-key="${x.esc(key)}" data-sl-reveal="${moved?1:0}" data-sl-focus="${focus}" aria-live="polite"><h4 class="section-title">${STAGES[tab][0]} ${x.esc(TITLES[tab])}${back}</h4>${PANELS[tab](t,x)}</section>`;
    return `<div class="career-job sl">${gb.hint}${t.timer?timerCard(t,x):''}${lastDesk(x)}${ticket(t,x)}${nav(t,x,list,at,tab)}
      <div class="sl-bench"><div class="sl-main">${panel}${foot(x,true)}${apptBook(x,false)}</div>
      <aside class="sl-side">${gb.rows}${mirror(t,x)}${tab==='bill'?'':receipt(t,x,true)}</aside></div>${gb.bar}</div>`;
  },
  actions:{
    tab(d,el,x){const u=x.ui[d.task];if(!u)return;u.tab=d.tab;u.tabAt=d.at;x.render();},
    svc(d,el,x){const u=x.ui[d.task];if(!u)return;u.services=u.services.includes(d.id)?u.services.filter(s=>s!==d.id):[...u.services,d.id];x.render();},
    sessions(d,el,x){const u=x.ui[d.task];if(u){u.sessions=Number(d.v);x.render();}},
    kind(d,el,x){const u=x.ui[d.task];if(u){u.kind=d.v;u.shade=null;x.render();}},
    shade(d,el,x){const u=x.ui[d.task];if(u){u.shade=d.v;x.render();}},
    tube(d,el,x){
      const u=x.ui[d.task];if(!u)return;const v=d.v;
      if(u.a===v){u.a=u.b;u.pa=u.b?u.pb:1;u.b=null;u.pb=1;}
      else if(u.b===v){u.b=null;u.pb=1;}
      else if(!u.a){u.a=v;u.pa=1;}
      else{u.b=v;u.pb=u.pb||1;}
      x.render();
    },
    part(d,el,x){const u=x.ui[d.task];if(!u)return;const k=d.which==='b'?'pb':'pa';u[k]=Math.max(1,Math.min(3,(u[k]||1)+Number(d.d)));x.render();},
    dev(d,el,x){const u=x.ui[d.task];if(u){u.dev=Number(d.v);x.render();}},
    chart(d,el,x){const u=x.ui[d.task];if(u){u.chart=!u.chart;x.render();}},
    chartR(d,el,x){const u=x.ui[d.task];if(u){u.chartR=d.v;x.render();}},
    cell(d,el,x){
      const u=x.ui[d.task];if(!u)return;
      Object.assign(u,{a:d.a,b:d.b||null,pa:Number(d.pa)||1,pb:d.b?Number(d.pb)||1:1,chart:false});x.render();
      // The chart folds away; the preview with the full verdict comes into view.
      requestAnimationFrame(()=>document.querySelector('.career-job.sl .sl-mixprev')?.scrollIntoView({block:'nearest',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'}));
    },
    ratio(d,el,x){const u=x.ui[d.task];if(u){u.ratio=d.v;x.render();}},
    len(d,el,x){const u=x.ui[d.task];if(u){u.len=Math.max(1,Math.min(10,u.len+Number(d.d)));u.lenSet=true;x.render();}},
    async cutCheck(d,el,x){
      const u=x.ui[d.task];if(!u)return;
      const r=await x.send('sl_cut',{task:d.task,step:'check'});if(!r)return;
      // Turned down, the server keeps the client's request (t.cut_ask) and the extra cm is picked again;
      // accepted, the cut is done and the length no longer matters.
      u.lenSet=false;
      x.render();
    },
    autoMix(d,el,x){
      const u=x.ui[d.task],t=(x.room.tasks||[]).find(v=>v.id===d.task);if(!u||!t)return;
      const left=chemLeft(t);if(!u.kind||!left.includes(u.kind))u.kind=left[0];
      const m=smartMix(t,x,u.kind);if(!m)return;
      if(m.kind==='color')Object.assign(u,{a:m.a,b:m.b,pa:m.pa,pb:m.b?m.pb:1});else if(m.kind==='toner')u.shade=m.shade;
      Object.assign(u,{dev:m.dev,ratio:m.ratio,tab:null});x.render();
    },
    product(d,el,x){const u=x.ui[d.task];if(!u)return;u.products=u.products.includes(d.id)?u.products.filter(p=>p!==d.id):[...u.products,d.id].slice(-3);x.render();},
    book(d,el,x){const u=x.ui[d.task];if(!u)return;u.book=u.book.includes(d.id)?u.book.filter(k=>k!==d.id):[...u.book,d.id];x.render();},
    mixCard(d,el,x){
      const u=x.ui[d.task],t=(x.room.tasks||[]).find(v=>v.id===d.task),f=t&&cardFormula(x,t);if(!u||!f)return;
      Object.assign(u,{a:f.shade,b:f.b,pa:f.pa,pb:f.b?f.pb:1,dev:f.dev,ratio:f.ratio});x.render();
    },
    aTube(d,el,x){
      const u=x.ui['appt:'+d.id];if(!u)return;const v=d.v;
      if(u.a===v){u.a=u.b;u.pa=u.b?u.pb:1;u.b=null;u.pb=1;}else if(u.b===v){u.b=null;u.pb=1;}else if(!u.a){u.a=v;u.pa=1;}else{u.b=v;}
      x.render();
    },
    aPart(d,el,x){const u=x.ui['appt:'+d.id];if(!u)return;const k=d.which==='b'?'pb':'pa';u[k]=Math.max(1,Math.min(3,(u[k]||1)+Number(d.d)));x.render();},
    aDev(d,el,x){const u=x.ui['appt:'+d.id];if(u){u.dev=Number(d.v);x.render();}},
    aLen(d,el,x){const u=x.ui['appt:'+d.id];if(u){u.len=Math.max(1,Math.min(6,u.len+Number(d.d)));x.render();}},
    aCard(d,el,x){
      const u=x.ui['appt:'+d.id],a=(x.room.data?.appts||[]).find(v=>v.id===d.id),f=a&&x.room.data?.cards?.[a.npc]?.formula;if(!u||!f)return;
      Object.assign(u,{a:f.shade,b:f.b,pa:f.pa,pb:f.b?f.pb:1,dev:f.dev});x.render();
    },
  },
  tick(root,x){
    keepBarAboveFooter(root);
    const p=root.querySelector('.sl-panel[data-sl-key]');
    if(p&&p.dataset.slKey!==revealed){revealed=p.dataset.slKey;if(p.dataset.slReveal==='1')reveal(root,root.querySelector('.sl-timer-card')||(p.dataset.slFocus&&p.querySelector(p.dataset.slFocus))||p);}
  },
  // The dye timer (v4/careers.js): the bar glides on the compositor, the words change five times a second.
  // "Xả thuốc" holds it where it was when the finger came down (tapStop).
  meters(root,x){
    root.querySelectorAll('[data-sl-start]').forEach(el=>{
      const start=Number(el.dataset.slStart);if(!start)return;
      const s=Math.max(0,x.now()-start),w=el.dataset;
      const under=Number(w.under),ideal=Number(w.ideal),over=Number(w.over),scale=Number(w.scale);
      x.slide(el.querySelector('.sl-fill'),s/scale*100,100/scale,true);
      el.querySelector('.sl-label').textContent=s.toFixed(1)+' giây · '+(s<under?'chưa đủ giờ':s<=ideal?'XẢ NGAY!':s<=over?'quá giờ rồi':'tóc đang cháy!');
      el.classList.toggle('ready',s>=under&&s<=ideal);el.classList.toggle('late',s>ideal);
      // Bottom bar: count down, then swap to "rinse" in the green zone (attributes and text only, never new nodes).
      const on=s>=under,wait=root.querySelector('.sl-wait'),go=root.querySelector('.sl-rinse-go'),left=root.querySelector('.sl-wait .sl-left');
      if(left)left.textContent=String(Math.max(1,Math.ceil(under-s)));
      if(wait&&wait.hidden!==on)wait.hidden=on;
      if(go&&go.hidden===on){go.hidden=!on;if(on&&root.querySelector('.sl-bar[data-first]'))go.classList.add('gd-pulse');}
      root.querySelector('.sl-rinse-top')?.classList.toggle('primary',on);
    });
  },
  tapStop:op=>op==='sl_rinse',
  dock:[['inventory','box','Kho','Thuốc & vật tư']],
};
