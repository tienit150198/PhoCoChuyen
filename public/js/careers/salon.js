/** Salon Tóc Gió — phone-first stylist chair (plugin career UI).
 * The server decides every result: answers, the bowl formula, timer zones, the mirror, the review and the money.
 * Local state is only what is being picked before sending (services, tubes, parts, length, products) and the open step tab.
 * The two-tube bowl preview mirrors the server maths (average level, tone band) using only what the stylist has found out. */
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

function ui(x,t){
  const u=x.ui[t.id]??={services:[],sessions:1,kind:null,a:null,b:null,pa:1,pb:1,shade:null,dev:null,ratio:null,len:2,products:[],tab:null,tabAt:null,init:false};
  if(!u.init&&t.needs){u.services=[...t.needs.services];u.init=true;}
  if(t.patch_done&&!u.patchSync){u.services=u.services.filter(s=>s!=='color'&&s!=='toner');u.patchSync=true;}
  const key=t.plan?t.plan.services.join(',')+'/'+t.plan.sessions:'';
  if(key&&u.planKey!==key){u.services=[...t.plan.services];u.sessions=t.plan.sessions;u.planKey=key;}
  return u;
}

/* ---------- mixing maths (same thresholds as the server) ---------- */
function bandOf(tn,den){if(tn<=-12*den)return 'ash';if(tn<=-3*den)return 'cool';if(tn<3*den)return 'natural';if(tn<18*den)return 'warm';return 'deep';}
function blend(rows){
  const tot=rows.reduce((a,r)=>a+r[1],0);let out='#';
  for(let i=0;i<3;i++){const v=rows.reduce((a,[c,p])=>a+parseInt(c.slice(1+2*i,3+2*i),16)*p,0)/tot;out+=Math.floor(v+0.5).toString(16).padStart(2,'0');}
  return out;
}
function mixOf(x,a,b,pa,pb,warm){
  const rows=[[dyeOf(x,a),pa]];if(b&&pb)rows.push([dyeOf(x,b),pb]);
  if(rows.some(r=>!r[0]))return null;
  const tone=x.cc.tone||{N:0,A:-1,G:1,R:2};
  const den=rows.reduce((s,r)=>s+r[1],0),lv=rows.reduce((s,[d,p])=>s+d.level*p,0);
  const tn=rows.reduce((s,[d,p])=>s+(tone[d.fam]||0)*20*p,0)+warm*20*den;
  const nat=rows.reduce((s,[d,p])=>s+(d.fam==='N'?p:0),0);
  return {den,lv,tn,nat,band:bandOf(tn,den),color:blend(rows.map(([d,p])=>[d.color,p]))};
}
const levelOk=(m,l)=>Math.abs(m.lv-l*m.den)*4<=m.den;
const levelText=m=>(m.lv/m.den).toFixed(2).replace(/0+$/,'').replace(/\.$/,'').replace('.',',');
function target(t){
  if(t.real)return {level:t.real.level,band:t.real.tone};
  const ph=t.needs?.photo;return ph?.level&&ph.band?{level:ph.level,band:ph.band}:null;
}

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
function todayChip(x){const d=x.room.data?.today;return d?`<p class="sl-today" title="${x.esc(d.text)}"><span aria-hidden="true">${x.esc(d.emoji)}</span> <b>Hôm nay: ${x.esc(d.title)}</b> <small>${x.esc(d.text)}</small></p>`:'';}
function deskCard(x){
  const ev=x.room.data?.desk?.ev;if(!ev)return '';
  const who=x.npc(ev.npc);
  const opts=ev.options.map((o,i)=>`<button type="button" class="btn ghost sl-opt" ${cmdAttr(x,'sl_desk',{option:o.id})} ${o.cost>x.room.money?'disabled':''}><b>${x.esc(o.label)}</b>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}</button>`).join('');
  return `<section class="sl-desk ${x.esc(ev.tone||'')}" role="alert" aria-live="assertive"><div class="sl-desk-head"><span class="sl-desk-emoji" aria-hidden="true">${x.esc(ev.emoji)}</span><div><small>CHUYỆN Ở QUẦY</small><h3>${x.esc(ev.title)}</h3></div>${x.portrait(who,40)}</div>
    <p>${x.esc(ev.text)}</p><div class="sl-opts">${opts}</div><p class="small-note">Thuốc đang ủ vẫn xả được bất cứ lúc nào; việc khác chờ quyết xong chuyện này.</p></section>`;
}
function lastDesk(x){const l=x.room.data?.desk?.last;if(!l||l.day!==x.room.day)return '';return `<p class="sl-last ${l.good===true?'good':l.good===false?'bad':''}" aria-live="polite"><span aria-hidden="true">${x.esc(l.emoji)}</span> <b>${x.esc(l.title)}:</b> ${x.esc(l.outcome)}</p>`;}
function calmBar(t){
  const v=Math.max(0,Math.min(100,Number(t.calm)||0));
  return `<div class="sl-calm ${v<20?'bad':v<40?'warn':'ok'}" role="meter" aria-label="Bé bình tĩnh" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${v}"><span>🧒 Bé bình tĩnh</span><div class="bar"><i style="width:${v}%"></i></div><b>${v}</b></div>`;
}
function foot(x){
  const d=x.room.data||{},busy=!!d.desk?.ev;
  return `<p class="row wrap sl-foot">${x.cmd(d.sanitized_today?'✅ Đã khử khuẩn hôm nay':'🧴 Khử khuẩn dụng cụ','sl_sanitize',{},'ghost small',!!d.sanitized_today||busy)}${x.button('📦 Kho thuốc & vật tư','inventory',{},'ghost small')}</p>`;
}
function rules(x){
  return `<details class="sl-rules"><summary>📋 Bảng pha màu</summary><ul>${x.cc.rules.map(r=>`<li>${x.esc(r)}</li>`).join('')}</ul>
    <div class="sl-levels">${x.cc.levels.map(l=>`<span style="--sw:${x.esc(l.color)}" title="${x.esc(l.name)}"><i></i>${l.level}</span>`).join('')}</div></details>`;
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
  if(t.mistakes)tags.push(x.pill(`⚠️ ${t.mistakes} lỗi`,'danger'));
  const photoLine=ph.level?`<small>${x.esc(ph.tone)} · level ${ph.level}${ph.filtered&&!t.real?' · ảnh có filter?':''}</small>`:'';
  const real=t.real?`<p class="sl-real">📸 Ảnh gốc: level ${t.real.level} · ${x.esc(bandName(x,t.real.tone))}</p>`:'';
  return `<article class="sl-ticket"><div class="row">${x.portrait(who,48)}<div class="grow">
      <div class="row spread wrap"><h3>${x.esc(who.display_name)}</h3><div class="patience" title="Kiên nhẫn"><div class="bar ${t.patience<50?'low':''}"><i style="width:${Number(t.patience)||0}%"></i></div><small>${Number(t.patience)||0}%</small></div></div>
      <p class="sl-want">${n.services.map(s=>`${svc(x,s).emoji} ${x.esc(svc(x,s).name)}`).join(' · ')}</p>
      ${t.plan?'':`<p class="small">${x.esc(n.want)}</p>`}</div></div>
    <div class="sl-photo">${sw}<div class="grow"><small class="muted">Ảnh mẫu khách đưa</small><b>${x.esc(ph.style)}</b>${photoLine}</div></div>${real}
    ${t.plan?`<details class="sl-more"><summary>Lời dặn của khách</summary><p class="small">${x.esc(n.want)}</p><p class="muted small">“${x.esc(n.note)}”</p></details>`:`<p class="muted small">“${x.esc(n.note)}”</p>`}
    ${t.calm!=null&&!t.done.includes('cut')?calmBar(t):''}
    <div class="row wrap sl-tags">${tags.join('')}</div>
  </article>`;
}

/* ---------- panels ---------- */
function consult(t,x){
  const qa=x.cc.topics.map(q=>{
    const a=t.answers?.[q.id];
    return `<div class="sl-qa ${a?'done':''}">${a?`<p class="sl-q">${q.emoji} ${x.esc(q.ask)}</p><p class="sl-a">${x.esc(a)}</p>`:x.cmd(`${q.emoji} ${x.esc(q.label)}`,'sl_consult',{task:t.id,topic:q.id},'ghost small')}</div>`;
  }).join('');
  const zones=x.cc.zones.map(z=>{
    const f=t.findings?.[z.id];
    return `<button type="button" class="sl-zone ${z.id} ${f?'seen':''}" ${cmdAttr(x,'sl_inspect',{task:t.id,zone:z.id})} ${f?'disabled':''}><b>${z.emoji} ${x.esc(z.label)}</b>${f?`<small>${x.esc(f)}</small>`:'<small>Chạm để xem kỹ</small>'}</button>`;
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
  const cta=t.plan?'':`<div class="sl-cta">${x.button('🤝 Sang chốt phương án →','car:tab',{task:t.id,tab:'plan',at:'consult'},'primary full')}</div>`;
  return `<p class="muted small">Hỏi trước, xem tận mắt rồi mới hứa. Câu trả lời của khách được ghi vào phiếu.</p>
    <div class="sl-qa-list">${qa}</div>
    <h5 class="sl-sub">Xem tóc tận tay</h5><div class="sl-zones">${zones}</div>
    ${tests.length?`<h5 class="sl-sub">Thử & soi trước khi làm</h5><div class="stack">${tests.join('')}</div>`:''}${cta}`;
}

function planPanel(t,x){
  const u=ui(x,t),n=t.needs;
  if(started(t)&&t.plan)return `<p>${t.plan.services.map(s=>`${svc(x,s).emoji} ${x.esc(svc(x,s).name)}`).join(' · ')}</p><p class="small muted">${t.plan.sessions>1?`Lộ trình ${t.plan.sessions} buổi — hôm nay là buổi 1.`:'Làm trong một buổi.'} Báo giá ${x.money(t.quote)}.</p>`;
  const tiles=x.cc.services.map(s=>{
    const on=u.services.includes(s.id),asked=n.services.includes(s.id);
    return `<button type="button" class="sl-tile ${on?'selected':''} ${asked?'':'extra'}" ${carAttr(x,'svc',{task:t.id,id:s.id})} aria-pressed="${on}"><span class="sl-emoji" aria-hidden="true">${s.emoji}</span><b>${x.esc(s.name)}</b><small>${x.money(price(x,s.id))} · ${asked?'khách yêu cầu':'mời thêm'}</small></button>`;
  }).join('');
  const quote=u.services.reduce((a,s)=>a+price(x,s),0);
  const seg=[1,2,3].map(v=>`<button type="button" class="sl-seg ${u.sessions===v?'on':''}" ${carAttr(x,'sessions',{task:t.id,v})} aria-pressed="${u.sessions===v}">${v} buổi</button>`).join('');
  const warn=caseOf(t)==='photo'&&!t.photo_seen?'<p class="sl-note">📸 Chưa soi ảnh gốc — hứa theo ảnh filter là dễ vỡ mộng.</p>':'';
  const picked=x.cc.services.map(s=>s.id).filter(s=>u.services.includes(s));
  const same=!!t.plan&&u.sessions===t.plan.sessions&&picked.length===t.plan.services.length&&picked.every(s=>t.plan.services.includes(s));
  const label=!t.plan?'🤝 Chốt với khách':same?'✓ Đã chốt phương án này':'🔁 Chốt lại phương án';
  return `<p class="muted small">Chỉ hứa điều làm được hôm nay. Bỏ bớt dịch vụ phải có lý do an toàn; ảnh mẫu xa quá thì chia buổi.</p>${warn}
    <div class="sl-grid">${tiles}</div>
    <h5 class="sl-sub">Số buổi để tới ảnh mẫu</h5><div class="sl-segs">${seg}</div>
    <div class="sl-cta"><b>Báo giá hôm nay: ${x.money(quote)}</b>${x.cmd(label,'sl_plan',{task:t.id,services:picked,sessions:u.sessions},same?'full':'primary full',!u.services.length||same)}</div>`;
}

function timerBar(t,x){
  const tm=t.timer,w=tm.window,scale=Math.round(w.over*1.3);
  const pct=v=>Math.min(100,v/scale*100);
  const el=Math.max(0,x.now()-tm.start);
  return `<div class="sl-timer" data-sl-start="${tm.start}" data-under="${w.under}" data-ideal="${w.ideal}" data-over="${w.over}" data-scale="${scale}">
    <div class="sl-track"><i class="z under" style="width:${pct(w.under)}%"></i><i class="z ideal" style="left:${pct(w.under)}%;width:${pct(w.ideal)-pct(w.under)}%"></i><i class="z over" style="left:${pct(w.ideal)}%;width:${pct(w.over)-pct(w.ideal)}%"></i><i class="z damage" style="left:${pct(w.over)}%;width:${100-pct(w.over)}%"></i><b class="sl-fill" style="width:${pct(el)}%"></b></div>
    <div class="row spread wrap"><small class="sl-label" aria-live="off">${el.toFixed(1)} giây</small><small class="muted">Vùng xanh: ${w.under}–${w.ideal} giây${tm.fragile?' · tóc đã qua hóa chất':''}${tm.fast?' · trời nóng, thuốc lên nhanh':''}</small></div>
  </div>`;
}
function timerCard(t,x){
  return `<section class="sl-sec focus sl-timer-card"><div class="sl-bowl on"><span class="sl-emoji" aria-hidden="true">⏱️</span><div class="grow"><b>Đang ủ ${x.esc(svc(x,t.timer.kind).name.toLowerCase())}</b>${timerBar(t,x)}</div></div>${x.cmd('🚿 Xả thuốc ngay','sl_rinse',{task:t.id},'primary full')}</section>`;
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

function mixer(t,x,u){
  const tg=target(t),warm=t.base_warm||0;
  const tubes=x.cc.dyes.map(d=>{
    const q=x.stock(d.id),role=u.a===d.id?'A':u.b===d.id?'B':'';
    return `<button type="button" class="sl-tube ${role?'selected':''}" ${carAttr(x,'tube',{task:t.id,v:d.id})} aria-pressed="${!!role}" aria-label="Tuýp ${x.esc(d.code)} ${x.esc(d.tone)}, còn ${q}${role?`, đang là tuýp ${role}`:''}" ${q||role?'':'disabled'}>${role?`<i class="sl-role" aria-hidden="true">${role}</i>`:''}<span class="sl-cap" style="--sw:${x.esc(d.color)}"></span><b>${x.esc(d.code)}</b><small>${x.esc(d.tone)}</small><em>${q}</em></button>`;
  }).join('');
  const m=u.a?mixOf(x,u.a,u.b,u.pa,u.b?u.pb:0,warm):null;
  const part=(which,id,p)=>{const d=dyeOf(x,id);return `<div class="sl-part"><span><i class="sl-role" aria-hidden="true">${which.toUpperCase()}</i> ${x.esc(d?.code||'')}</span><button type="button" class="btn small ghost" ${carAttr(x,'part',{task:t.id,which,d:-1})} aria-label="Bớt một phần ${x.esc(d?.code||'')}" ${p<=1?'disabled':''}>−</button><b>${p} phần</b><button type="button" class="btn small ghost" ${carAttr(x,'part',{task:t.id,which,d:1})} aria-label="Thêm một phần ${x.esc(d?.code||'')}" ${p>=3?'disabled':''}>+</button></div>`;};
  let preview='<p class="sl-preview muted small">Chạm một tuýp để làm nền (A); chạm thêm tuýp thứ hai (B) nếu cần pha. Chạm lại để bỏ.</p>';
  if(m){
    const lvOk=tg?levelOk(m,tg.level):null,bdOk=tg?m.band===tg.band:null;
    const chips=[];
    if(tg){chips.push(`<span class="tag ${lvOk?'green':'danger'}">${lvOk?'✓':'≠'} độ sáng</span>`,`<span class="tag ${bdOk?'green':'danger'}">${bdOk?'✓':'≠'} ánh màu</span>`);}
    if((t.grey||0)>=50){const g=2*m.nat>=m.den;chips.push(`<span class="tag ${g?'green':'danger'}">${g?'✓':'≠'} nền tự nhiên ${m.nat}/${m.den}</span>`);}
    preview=`<div class="sl-preview" aria-live="polite"><span class="sl-dish big" style="--sw:${x.esc(m.color)}" aria-hidden="true"></span><div class="grow"><b>Bát ra: level ${x.esc(levelText(m))} · ${x.esc(bandName(x,m.band))}</b>${tg?`<small>Cần: level ${tg.level} · ${x.esc(bandName(x,tg.band))}${t.real?' (theo ảnh gốc)':''}</small>`:''}<div class="row wrap">${chips.join('')}</div></div></div>`;
  }
  const notes=[];
  if(caseOf(t)==='photo'&&!t.photo_seen)notes.push('📸 Ảnh mẫu có filter: soi ảnh gốc ở bước tư vấn để biết màu thật.');
  if(!t.findings?.lengths)notes.push('〰️ Chưa xem thân tóc: nền màu cũ có thể kéo lệch ánh mà ô xem trước chưa biết.');
  else if(warm)notes.push('🟠 Thân tóc ánh cam đồng: trên tóc này bát ấm thêm một bậc (ô xem trước đã tính).');
  if(t.grey==null&&!t.findings?.roots)notes.push('🌱 Chưa xem chân tóc: có tóc bạc thì cần đủ nền tự nhiên.');
  return `<h5 class="sl-sub">Tủ tuýp · chọn 1–2 tuýp</h5><div class="sl-tubes">${tubes}</div>
    ${u.a?`<div class="sl-parts">${part('a',u.a,u.pa)}${u.b?part('b',u.b,u.pb):''}</div>`:''}
    ${preview}${notes.map(v=>`<p class="sl-note">${x.esc(v)}</p>`).join('')}`;
}

function colorPanel(t,x){
  const left=chemLeft(t),u=ui(x,t);
  const results=Object.entries(t.results||{}).map(([k,r])=>`<li class="${r.zone==='ideal'&&r.ok?'ok':r.zone==='damage'||r.zone==='under'?'bad':'warn'}">${svc(x,k).emoji} ${x.esc(svc(x,k).name)}: ${x.esc(ZONE_TEXT[r.zone])} (${r.secs} giây)${r.ok?'':' · công thức lệch'}</li>`).join('');
  const mixRes=t.mix_result?`<p class="sl-note"><span class="sl-dot" style="--sw:${x.esc(t.mix_result.color)}" aria-hidden="true"></span> Màu đã lên: level ${x.esc(t.mix_result.level)} · ${x.esc(bandName(x,t.mix_result.band))}</p>`:'';
  const tail=`${results?`<ul class="sl-results">${results}</ul>`:''}${mixRes}${rules(x)}`;
  if(t.timer)return `<p class="sl-note">⏱️ Thanh ủ đang chạy ở đầu phiếu — xả khi vào vùng xanh.</p>${tail}`;
  if(t.bowl){
    const b=t.bowl;
    return `<div class="sl-bowl"><span class="sl-dish" style="--sw:${x.esc(bowlColour(x,b))}" aria-hidden="true"></span><div class="grow"><b>Bát ${x.esc(svc(x,b.kind).name.toLowerCase())}</b><small>${x.esc(bowlLabel(x,b))} + oxy ${b.dev} vol · ${fmtRatio(b.ratio)}</small></div></div>
      ${b.ok?'':'<p class="sl-note bad">⚠️ Linh chê công thức bát này — nên đổ đi pha lại.</p>'}
      <div class="sl-cta">${x.cmd('🖌️ Thoa từ chân tới ngọn','sl_apply',{task:t.id},b.ok?'primary full':'full')}${x.confirmCmd('🗑️ Đổ bát, pha lại','sl_dump',{task:t.id,confirm:true},'Đổ bát thuốc này? Thuốc đã pha được ghi hao hụt.',b.ok?'danger small':'primary full')}</div>${tail}`;
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
  const blocked=u.kind==='toner'&&t.plan.services.includes('bleach')&&!t.done.includes('bleach');
  let payload,ready;
  if(mixing){payload={task:t.id,kind:'color',shade:u.a,parts:[u.pa,u.b?u.pb:0],dev:u.dev,ratio:u.ratio};if(u.b)payload.shade2=u.b;ready=!!(u.a&&u.dev&&u.ratio);}
  else{payload={task:t.id,kind:u.kind,dev:u.dev,ratio:u.ratio};if(u.kind!=='bleach')payload.shade=u.shade;ready=!!(u.dev&&u.ratio&&(u.kind==='bleach'||u.shade));}
  const need=[u.dev?'dev_'+u.dev:null,...(mixing?[u.a,u.b]:[u.kind==='bleach'?'bleach':u.shade]),u.kind==='bleach'?'foil':null].filter(Boolean);
  const out=need.filter(id=>!x.stock(id));
  if(out.length)ready=false;
  const outNote=out.length?`<p class="sl-note bad">📦 Hết ${out.map(id=>x.esc(itemName(x,id))).join(', ')} — mở Kho nhập thêm hoặc chọn loại khác.</p>`:'';
  return `<p class="muted small">Pha theo bảng pha màu. Thoa xong, thanh ủ chạy theo giây thật — xả khi vào vùng xanh.</p>${tabs}${pick}
    <h5 class="sl-sub">Oxy trợ nhuộm</h5><div class="sl-segs">${devs}</div>
    <h5 class="sl-sub">Tỷ lệ thuốc ∶ oxy</h5><div class="sl-segs">${ratios}</div>
    ${blocked?'<p class="sl-note">Tẩy và xả xong rồi mới phủ toner.</p>':''}${outNote}
    <div class="sl-cta">${x.cmd('🥣 Trộn bát','sl_mix',payload,'primary full',!ready||blocked)}</div>${tail}`;
}

function washPanel(t,x){
  const kid=caseOf(t)==='kid'&&t.calm!=null;
  return `<p class="small">${t.washed?'✅ Tóc đã gội, xả sạch.':'Nhuộm/tẩy làm trên tóc khô; cắt, phục hồi, sấy cần tóc sạch.'}</p>
    ${kid&&!t.washed?'<p class="sl-note">🧒 Bé nào gội xong cũng hay vẩy nước, bớt ngồi yên một chút.</p>':''}
    <div class="sl-cta">${x.cmd('🫧 Gội & xả','sl_wash',{task:t.id},'primary full',t.washed||!!t.timer)}</div>`;
}

function cutPanel(t,x){
  const u=ui(x,t),c=t.cut,s=c.steps,done=t.done.includes('cut'),kid=caseOf(t)==='kid'&&t.calm!=null;
  const next=!s.includes('section')?'section':!s.includes('guide')?'guide':'check';
  const step=(id,label,cond,payload={})=>`<li class="${s.includes(id)?'done':''}">${x.cmd(label,'sl_cut',{task:t.id,step:id,...payload},id===next&&!done?'primary':s.includes(id)&&id!=='guide'?'ghost small':'small',done||!cond||!t.washed)}</li>`;
  let calm='';
  if(kid&&!done){
    const tools=(x.cc.calm_tools||[]).map(k=>`<button type="button" class="sl-chip ${t.soothed.includes(k.id)?'on':''}" ${cmdAttr(x,'sl_calm',{task:t.id,tool:k.id})} ${t.soothed.includes(k.id)?'disabled':''}><b>${k.emoji} ${x.esc(k.label)}</b></button>`).join('');
    calm=`<div class="sl-kid">${calmBar(t)}${t.calm<40?'<p class="sl-note bad">⚠️ Bé đang giãy — cầm kéo lúc này dễ lẹm. Dỗ bé trước đã.</p>':''}<h5 class="sl-sub">Dỗ bé (nghe bố kể thói quen của bé)</h5><div class="sl-calm-tools">${tools}</div></div>`;
  }
  return `${calm}<p class="muted small">Chia vùng → cắt đường chuẩn → tỉa tầng (nếu mẫu có) → soi đối xứng. Cắt lẹm thì không nối lại được — cắt ít, kiểm nhiều.</p>
    <div class="sl-len"><span>Độ dài cắt bớt</span><button type="button" class="btn small ghost" ${carAttr(x,'len',{task:t.id,d:-1})} aria-label="Bớt 1 cm">−</button><b>${u.len} cm</b><button type="button" class="btn small ghost" ${carAttr(x,'len',{task:t.id,d:1})} aria-label="Thêm 1 cm">+</button><small class="muted">Đã bớt tổng ${c.removed} cm${c.short?' · ⚠️ lẹm':''}</small></div>
    <ol class="sl-steps">${step('section','1 · Chia vùng',!s.length)}${step('guide',`2 · Cắt đường chuẩn (${u.len} cm)`,s.includes('section')&&!s.includes('layers'),{length:u.len})}${step('layers','3 · Tỉa tầng',s.includes('guide')&&!s.includes('layers'))}${step('check','4 · Soi đối xứng & chốt',s.includes('guide'))}</ol>
    ${done?'<p class="sl-note good">✂️ Đã cắt xong.</p>':''}`;
}

function finishPanel(t,x){
  const ps=t.plan.services,parts=[];
  if(ps.includes('treatment'))parts.push(`<div class="sl-cta"><p class="small">💧 Keratin phục hồi · còn ${x.stock('keratin')} lượt</p>${x.cmd(t.done.includes('treatment')?'✅ Đã phục hồi':'💧 Thoa keratin & hấp','sl_treat',{task:t.id},t.done.includes('treatment')?'full':'primary full',t.done.includes('treatment'))}</div>`);
  if(ps.includes('style')){
    const wait=ps.includes('treatment')&&!t.done.includes('treatment');
    parts.push(`<h5 class="sl-sub">Kiểu sấy hợp thói quen & dịp của khách</h5><div class="sl-grid">${x.cc.finishes.map(f=>`<button type="button" class="sl-tile ${t.styled===f.id?'selected':''}" ${cmdAttr(x,'sl_style',{task:t.id,finish:f.id})} ${t.done.includes('style')||wait?'disabled':''}><span class="sl-emoji" aria-hidden="true">${f.emoji}</span><b>${x.esc(f.name)}</b><small>${x.esc(f.note)}</small></button>`).join('')}</div>`);
  }
  return parts.join('')||'<p class="muted small">Không có phần hoàn thiện.</p>';
}

function receipt(t,x){
  const ps=t.plan?.services||[];
  const rows=ps.map(s=>`<li class="${t.done.includes(s)?'ok':''}"><span>${t.done.includes(s)?'✓':'○'} ${svc(x,s).emoji} ${x.esc(svc(x,s).name)}</span><b>${x.money(price(x,s))}</b></li>`).join('');
  const fee=t.patch_fee?`<li class="ok"><span>✓ 🩹 Thử dị ứng</span><b>${x.money(t.patch_fee)}</b></li>`:'';
  return `<div class="sl-bill"><h4>🧾 Phiếu dịch vụ</h4><ul>${rows||'<li class="muted">Chưa chốt phương án</li>'}${fee}</ul></div>`;
}

function billPanel(t,x){
  const u=ui(x,t),ps=t.plan?.services||[],left=rushLeft(t,x);
  const shelf=(x.cc.retail||[]).map(r=>{const on=u.products.includes(r.id),q=x.stock(r.id);return `<button type="button" class="sl-chip ${on?'on':''}" ${carAttr(x,'product',{task:t.id,id:r.id})} aria-pressed="${on}" ${q?'':'disabled'}>${r.emoji} ${x.esc(r.name)} · ${x.money(r.price)}<small>${q} trên kệ</small></button>`;}).join('');
  const retailSum=u.products.reduce((a,id)=>a+retail(x,id).price,0);
  const pending=ps.filter(s=>!t.done.includes(s));
  const ready=t.plan&&!pending.length&&!t.bowl&&!t.timer;
  return `${receipt(t,x)}
    <h5 class="sl-sub">Tư vấn sản phẩm (chỉ khi hợp tóc & ngân sách)</h5><div class="sl-chips">${shelf}</div>
    <p class="row spread"><span>Tạm tính</span><b>${x.money((t.quote||0)+(t.patch_fee||0)+retailSum)}</b></p>
    ${left!=null?`<p class="small">⏱️ ${left>=0?`Còn ${left} nhịp để kịp giờ khách hẹn.`:'Đã trễ giờ khách hẹn.'}</p>`:''}
    <div class="sl-cta">${x.confirmCmd('💳 Thanh toán & tiễn khách','sl_checkout',{task:t.id,products:u.products,confirm:true},'Thanh toán cho khách? Khách sẽ soi gương và đánh giá đúng những gì đã làm; sản phẩm không hợp sẽ bị từ chối.','primary full',!ready)}</div>
    ${pending.length&&t.plan?`<small class="muted">Còn: ${pending.map(s=>x.esc(svc(x,s).name.toLowerCase())).join(', ')}</small>`:''}`;
}

function mirror(t,x){
  const lk=t.look||{};
  const len=Math.max(4,Math.min(46,lk.length||10));
  return `<div class="sl-mirror" role="img" aria-label="Gương: tóc level ${lk.level||'?'}, dài khoảng ${lk.length||'?'} cm">
    <div class="sl-glass"><div class="sl-head" style="--hair:${x.esc(lk.color||'')};--len:${len}"><i class="sl-back"></i><i class="sl-face"></i><i class="sl-fringe"></i></div></div>
    <small>Level ${lk.level||'?'} · dài ~${lk.length||'?'} cm</small></div>`;
}

const PANELS={consult,plan:planPanel,color:colorPanel,wash:washPanel,cut:cutPanel,finish:finishPanel,bill:billPanel};

export default {
  id:'salon',
  css:true,
  next(t,x){
    if(t.timer)return 'Xả thuốc khi thanh vào vùng xanh';
    if(x?.room?.data?.desk?.ev)return 'Có chuyện ở quầy cần quyết';
    if(!t.known)return 'Mời khách ngồi, nghe mong muốn';
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
    const stats=`<div class="row wrap sl-stats">${x.pill(`💇 ${d.day_served||0} khách hôm nay`)}${x.pill(`🧾 ${d.served||0} khách tất cả`)}${d.mixes?x.pill(`🎨 ${d.mixes} bát pha trúng`,'green'):''}${d.rush_on_time?x.pill(`⏱️ ${d.rush_on_time} lần kịp giờ`,'green'):''}${d.kids_calm?x.pill(`🧒 ${d.kids_calm} bé cắt êm`,'green'):''}${d.allergy?x.pill(`🩹 ${d.allergy} khách trong sổ dị ứng`,'amber'):''}</div>`;
    return `<div class="career-job sl sl-idle">${deskCard(x)}${lastDesk(x)}${todayChip(x)}${stats}${foot(x)}${rules(x)}</div>`;
  },
  job(t,x){
    const desk=deskCard(x),who=x.npc(t.npc);
    if(!t.known){
      return `<div class="career-job sl">${desk}${todayChip(x)}<article class="sl-ticket"><div class="row">${x.portrait(who,56)}<div class="grow"><h3>${x.esc(who.display_name)}</h3><p>“${x.esc(t.opening)}”</p></div></div><div class="sl-cta">${x.cmd('💬 Mời ngồi & nghe mong muốn','ask',{task:t.id},'primary full',!!desk)}</div></article></div>`;
    }
    if(desk)return `<div class="career-job sl">${t.timer?timerCard(t,x):''}${desk}${ticket(t,x)}</div>`;
    const u=ui(x,t),list=stages(t),at=current(t),ai=list.indexOf(at);
    if(u.tab!=null&&u.tabAt!==at)u.tab=null;
    const reach=s=>list.includes(s)&&(list.indexOf(s)<=ai||(s==='plan'&&!t.plan));
    const tab=u.tab&&reach(u.tab)?u.tab:at;
    const back=tab!==at&&!(tab==='plan'&&!t.plan)?` <button type="button" class="btn ghost small" ${carAttr(x,'tab',{task:t.id,tab:at,at})}>Về bước đang làm</button>`:'';
    const panel=`<section class="sl-sec sl-panel ${tab===at?'focus':''}" aria-live="polite"><h4 class="section-title">${STAGES[tab][0]} ${x.esc(TITLES[tab])}${back}</h4>${PANELS[tab](t,x)}</section>`;
    return `<div class="career-job sl">${t.timer?timerCard(t,x):''}${lastDesk(x)}${ticket(t,x)}${nav(t,x,list,at,tab)}
      <div class="sl-bench"><div class="sl-main">${panel}${foot(x)}</div>
      <aside class="sl-side">${mirror(t,x)}${tab==='bill'?'':receipt(t,x)}</aside></div></div>`;
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
    ratio(d,el,x){const u=x.ui[d.task];if(u){u.ratio=d.v;x.render();}},
    len(d,el,x){const u=x.ui[d.task];if(u){u.len=Math.max(1,Math.min(10,u.len+Number(d.d)));x.render();}},
    product(d,el,x){const u=x.ui[d.task];if(!u)return;u.products=u.products.includes(d.id)?u.products.filter(p=>p!==d.id):[...u.products,d.id].slice(-3);x.render();},
  },
  tick(root,x){
    root.querySelectorAll('[data-sl-start]').forEach(el=>{
      const start=Number(el.dataset.slStart);if(!start)return;
      const s=Math.max(0,x.now()-start),w=el.dataset;
      const under=Number(w.under),ideal=Number(w.ideal),over=Number(w.over),scale=Number(w.scale);
      el.querySelector('.sl-fill').style.width=Math.min(100,s/scale*100)+'%';
      el.querySelector('.sl-label').textContent=s.toFixed(1)+' giây · '+(s<under?'chưa đủ giờ':s<=ideal?'XẢ NGAY!':s<=over?'quá giờ rồi':'tóc đang cháy!');
      el.classList.toggle('ready',s>=under&&s<=ideal);el.classList.toggle('late',s>ideal);
    });
  },
  dock:[['inventory','box','Kho','Thuốc & vật tư']],
};
