/** 🏫 Trường học (game/school.py): 🎓 Đại học Phố Mây with many majors, ✈️ du học một học kỳ, 📜 the degrees.
 * Loaded lazily by app.js (L.school), opened with data-action="school" (data-tab uni | abroad | deg): the menu, the
 * journey page, ✈️ Du học (v4/abroad.js). The catalogue is content.journey.school; the page's state is the view each
 * jr_sch_* command returns (result.school, never in public_state). The server grades everything and keeps the keys:
 * a quiz shows its questions one at a time, the answers go in one command, the result screen says why. */
import {icon,escapeHTML as esc} from '../icons.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(String(v))}"`).join('');
const btn=(label,action,data={},style='',disabled=false)=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}${disabled?' disabled':''}>${label}</button>`;
const st=env=>env.ui.school??={tab:'uni',data:null,quiz:null,qi:0,ans:[],order:[],result:null,major:null,apply:null,docs:[],fly:null,note:null};
const K=env=>env.api.content?.journey?.school;
const place=(api,cid)=>{const m=(api.content?.catalogue||[]).find(x=>x.id===cid);return m?(m.short||m.place):cid;};
const program=(k,pid)=>{const m=k.majors.find(x=>x.id===pid);if(m)return {...m,kind:'uni'};const t=k.terms.find(x=>x.id===pid);return t?{...t,kind:'abroad'}:null;};
const subjectsOf=p=>p.sems.flat();
const dots=(n,of)=>`<span class="sch-dots" aria-label="${n}/${of}">${Array.from({length:of},(_,i)=>`<i class="${i<n?'on':''}"></i>`).join('')}</span>`;
const mark10=m=>m==null?'':`${Math.floor(m/10)},${m%10}`;
const KIND={class:'Vào lớp',hw:'Bài tập về nhà',exam:'Thi cuối kỳ',job:'Làm thêm'};

async function run(env,op,payload={}){
  const u=st(env),r=await env.cmd(op,payload,{quiet:true});
  if(r?.school)u.data=r.school;
  return r;
}
/** Open the page: the view first (nothing changes on the server). */
export async function schoolOpen(env,data={}){
  const u=st(env);if(data?.tab)u.tab=data.tab;
  u.quiz=null;u.result=null;u.apply=null;u.major=null;
  if(!await run(env,'jr_sch_view'))return false;
  const c=u.data?.cur;if(c&&!data?.tab)u.tab=c.kind==='abroad'?'abroad':'uni';
  return !!u.data;
}

/* ------------------------------------------------------------------ the page */
function head(sub=''){
  return `<header class="sheet-head"><div class="grow"><span class="eyebrow">ĐẠI HỌC PHỐ MÂY · DU HỌC</span><h2>🏫 Trường học</h2>${sub?`<p>${sub}</p>`:''}</div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
}
function tabs(u,v){
  const row=[['uni','🎓 Đại học'],['abroad','✈️ Du học'],['deg',`📜 Bằng${v.deg.length?` (${v.deg.length})`:''}`]];
  return `<nav class="pill-tabs sch-tabs" role="tablist">${row.map(([id,label])=>`<button role="tab" type="button" aria-selected="${id===u.tab}" class="${id===u.tab?'active':''}" data-action="schTab" data-tab="${id}">${label}</button>`).join('')}</nav>`;
}
const perkLine=(api,k,careers,pct)=>`<p class="sch-perk">🎓 Tốt nghiệp: tiền công <b>+${pct}%</b> ở ${careers.map(c=>esc(place(api,c))).join(', ')}; tính như chứng chỉ khi xin việc; mở sớm các nơi đó.</p>`;

function majorCard(env,k,v,m){
  const held=v.deg.some(d=>d.p===m.id),kept=v.kept?.[m.id];
  const tag=held?'<span class="tag green">✓ Đã tốt nghiệp</span>':kept?`<span class="tag">Bảo lưu ${kept} học kỳ</span>`:'';
  return `<button type="button" class="sch-major" data-action="schMajor" data-id="${esc(m.id)}"><span class="sch-emoji" aria-hidden="true">${m.emoji}</span><span class="grow"><b>${esc(m.name)}</b><small>${esc(m.blurb)}</small><small class="muted">${m.sems.length} học kỳ · ${subjectsOf(m).length} môn · ${fmt(m.fee)} xu/học kỳ</small></span>${tag}${icon('arrow',16)}</button>`;
}
function majorDetail(env,k,v,m){
  const {api}=env,held=v.deg.some(d=>d.p===m.id),kept=v.kept?.[m.id]||0,busy=v.cur;
  const sems=m.sems.map((sem,i)=>`<div class="sch-sem"><p class="sch-eyebrow">Học kỳ ${i+1}${i<kept?' · đã học (bảo lưu)':''}</p><ul>${sem.map(s=>`<li>${s.emoji} ${esc(s.name)} <small class="muted">· ${k.rules.credits} tín chỉ</small></li>`).join('')}</ul></div>`).join('');
  const go=held?'<span class="tag green">✓ Bạn đã có bằng ngành này</span>'
    :busy?`<p class="sch-why">🔒 Bạn đang học ${esc(program(k,busy.p)?.name||'')}. Học xong hoặc thôi học trước nhé.</p>`
    :btn(`${kept?'Học tiếp':'Nhập học'} · ${fmt(m.fee)} xu`,'schEnrol',{program:m.id,name:m.name,fee:m.fee},'primary');
  return `<article class="sch-card"><button type="button" class="btn ghost small" data-action="schBack">← Các ngành</button><h3>${m.emoji} ${esc(m.name)}</h3><p>${esc(m.blurb)}</p>${sems}
    <p class="sch-perk">📅 Mỗi học kỳ: thời khóa biểu tuần, mỗi môn ${k.rules.classes} buổi (mỗi ngày tối đa ${k.rules.per_day} buổi), bài tập về nhà, thi ${k.rules.exam_q} câu (đúng từ ${k.rules.exam_pass} là đạt, trượt thì mai thi lại miễn phí).</p>
    ${perkLine(api,k,m.careers,`${k.rules.classes_pct.tb}–${k.rules.classes_pct.xuat_sac}`)}${go}</article>`;
}
function uniPage(env,k,v){
  const u=st(env);
  if(u.major){const m=k.majors.find(x=>x.id===u.major);if(m)return majorDetail(env,k,v,m);}
  return `<p class="sch-intro">${k.uni.emoji} <b>${esc(k.uni.name)}</b>: ${k.majors.length} ngành, mỗi ngành ${k.majors[0].sems.length} học kỳ. Học xong ngành này học tiếp ngành khác, mỗi ngành một tấm bằng.</p><div class="sch-majors">${k.majors.map(m=>majorCard(env,k,v,m)).join('')}</div>`;
}

function termCard(env,k,v,t){
  const {api}=env,held=v.deg.some(d=>d.p===t.id),busy=v.cur;
  const subs=subjectsOf(t).map(s=>`${s.emoji} ${esc(s.name)}`).join(' · ');
  const go=held?'<span class="tag green">✓ Đã tốt nghiệp</span>'
    :busy?'<small class="muted">Học xong chương trình đang học đã</small>'
    :btn(`Nộp hồ sơ · ${fmt(t.fee+t.visa)} xu`,'schApplyOpen',{program:t.id},'primary small');
  return `<article class="sch-card"><p class="sch-eyebrow">${t.flag} ${esc(t.country)} · ${esc(t.city)}</p><h3>${esc(t.school)}</h3><p class="small">${subs}</p><p class="small muted">Học phí ${fmt(t.fee)} xu · visa ${fmt(t.visa)} xu · 1 học kỳ · có làm thêm</p>${perkLine(api,k,t.careers,`${k.rules.classes_pct.tb}–${k.rules.classes_pct.xuat_sac}`)}${go}</article>`;
}
function applyPage(env,k,v){
  const u=st(env),t=k.terms.find(x=>x.id===u.apply);if(!t)return '';
  const picked=new Set(u.docs);
  const rows=k.docs.map(d=>`<label class="sch-doc"><input type="checkbox" data-action="schDoc" data-id="${esc(d.id)}"${picked.has(d.id)?' checked':''}> <span>${esc(d.label)}</span></label>`).join('');
  return `<article class="sch-card"><button type="button" class="btn ghost small" data-action="schBack">← Các nước</button><p class="sch-eyebrow">${t.flag} ${esc(t.country)} · ${esc(t.school)}</p><h3>📂 Chuẩn bị hồ sơ du học</h3><p class="small">Chọn đúng những giấy tờ cần nộp. Sai thì sửa lại, không mất gì cả.</p><div class="sch-docs">${rows}</div>
    ${btn(`Nộp hồ sơ · ${fmt(t.fee+t.visa)} xu`,'schApply',{program:t.id},'primary',!picked.size)}</article>`;
}
function abroadPage(env,k,v){
  const u=st(env);
  if(u.apply)return applyPage(env,k,v);
  return `<p class="sch-intro">✈️ <b>Du học một học kỳ</b>: nộp hồ sơ, phỏng vấn visa, bay sang, sống như sinh viên: lên lớp, làm thêm, đi lễ hội. Bằng du học tăng lương mọi việc làm thuê.</p><div class="sch-list">${k.terms.map(t=>termCard(env,k,v,t)).join('')}</div>
    <p class="small muted">Muốn học nhanh 4 buổi? ${btn('Khóa ngắn hạn','abroad',{tab:'study'},'ghost small')}</p>`;
}

/* ------------------------------------------------------------------ the program running */
function visaCard(k,c,p){
  return `<article class="sch-card sch-now"><p class="sch-eyebrow">${p.flag} Lãnh sự quán ${esc(p.country)}</p><h3>🛂 Phỏng vấn visa</h3><p class="sch-q">${esc(c.visa.q)}</p><div class="sch-opts">${c.visa.options.map((o,i)=>btn(esc(o),'schVisa',{option:i},'sch-opt')).join('')}</div></article>`;
}
function flyCard(k,c,p){
  return `<article class="sch-card sch-now sch-fly"><p class="sch-eyebrow">${p.flag} Tân Sơn Mây → ${esc(p.city)}</p><h3>✈️ Lên đường!</h3><ol class="sch-lines">${c.fly.map((l,i)=>`<li style="--i:${i}">${esc(l)}</li>`).join('')}</ol>${btn('🛫 Lên máy bay','schFly',{},'primary')}</article>`;
}
function todayCard(env,k,c,p){
  const name=id=>c.subjects.find(s=>s.id===id);
  let body;
  if(c.ph==='break')body=`<p>🎉 Xong học kỳ ${c.sem+1}! Điểm trung bình đang là <b>${esc(c.gpa_text)}</b>.</p>${btn(`Đóng học phí học kỳ ${c.sem+2} · ${fmt(c.next_fee)} xu`,'schNext',{fee:c.next_fee,n:c.sem+2},'primary')}`;
  else if(c.wd===6)body=`<p>☀️ Chủ nhật trường nghỉ. ${p.kind==='abroad'?'Đi làm thêm, dự lễ hội, ':''}khép một ca để sang Thứ 2 nhé.</p>`;
  else if(c.avail.length)body=`<div class="sch-opts">${c.avail.map(id=>{const s=name(id);return btn(`${s.emoji} Vào lớp ${esc(s.name)} <small>Buổi ${s.a+1}/${k.rules.classes}</small>`,'schOpen',{kind:'class',subject:id},'sch-class');}).join('')}</div>`;
  else body=`<p class="sch-wait">${c.left?'Hôm nay hết môn có lịch.':`Hôm nay đã học đủ ${k.rules.per_day} buổi.`} Khép một ca làm việc là sang ngày mới.</p>`;
  return `<article class="sch-card sch-now"><p class="sch-eyebrow">${p.kind==='abroad'?`${p.flag} ${esc(p.city)}`:`${k.uni.emoji} ${esc(k.uni.short)}`} · Học kỳ ${c.sem+1}/${c.sems}</p><h3>📅 Hôm nay: ${esc(c.wd_label)}</h3>${body}</article>`;
}
function subjectCard(k,c,s){
  const exam=s.passed?`<span class="tag green">✓ ${mark10(s.mark)} điểm · ${esc(s.letter)}</span>`
    :s.can_exam?btn(`📄 Thi${s.tries?' lại':''}`,'schOpen',{kind:'exam',subject:s.id},'primary small')
    :s.exam_today?'<small class="muted">Mai thi lại nhé</small>':'';
  const hw=s.hw>=0?`📝 Bài tập ${s.hw}/${k.rules.hw_q}`:s.a>=2?'📝 Bài tập chưa làm':'📝 Bài tập mở sau buổi 2';
  return `<li class="sch-sub${s.passed?' done':''}"><span class="sch-emoji" aria-hidden="true">${s.emoji}</span><span class="grow"><b>${esc(s.name)}</b><small>Buổi ${dots(s.a,k.rules.classes)} · ${hw}${s.tries&&!s.passed?` · thi tốt nhất ${s.ex}/${k.rules.exam_q}`:''}</small></span><span class="sch-acts">${s.can_hw?btn('📝 Làm bài','schOpen',{kind:'hw',subject:s.id},'cream small'):''}${exam}</span></li>`;
}
function weekGrid(k,c){
  const subj=id=>c.subjects.find(s=>s.id===id);
  return `<details class="sch-week"><summary>🗓️ Thời khóa biểu tuần</summary><ul>${c.week.map(r=>`<li class="${r.wd===c.wd?'today':''}"><b>${esc(r.label)}</b><span>${r.subjects.length?r.subjects.map(id=>`${subj(id).emoji} ${esc(subj(id).name)}`).join(' · '):'Nghỉ · hoạt động ngoại khóa'}</span></li>`).join('')}</ul><p class="small muted">Môn nào học đủ buổi thì buổi đó thành buổi tự chọn: học bù môn còn thiếu.</p></details>`;
}
function lifeCards(k,c,p){
  let out='';
  if(p.kind==='abroad'&&c.job)out+=`<article class="sch-card"><h3>💼 Làm thêm ở ${esc(p.city)}</h3><p class="small">Mỗi ngày một ca ngắn, ${c.job.pay[0]}–${c.job.pay[1]} xu vào ví (${c.job.n}/${c.job.max} ca).</p>${c.job.can?btn('Đi làm thêm','schOpen',{kind:'job'},'cream small'):'<small class="muted">Hôm nay làm rồi, mai nhé.</small>'}</article>`;
  const evs=c.events.filter(e=>!e.done);
  if(evs.length)out+=`<article class="sch-card"><h3>🎉 ${p.kind==='abroad'?'Lễ hội & trải nghiệm':'Hoạt động ở trường'}</h3>${c.can_event?evs.slice(0,1).map(e=>`<p><b>${e.emoji} ${esc(e.title)}</b>: ${esc(e.scene)}</p><div class="sch-opts">${e.options.map((o,i)=>btn(esc(o),'schEvent',{event:e.id,option:i},'sch-opt')).join('')}</div>`).join(''):'<p class="small muted">Hôm nay tham gia rồi, mai có hoạt động khác.</p>'}</article>`;
  return out;
}
function curPage(env,k,v){
  const c=v.cur,p=program(k,c.p);if(!p)return '';
  if(c.ph==='visa')return visaCard(k,c,p);
  if(c.ph==='fly')return flyCard(k,c,p);
  const title=p.kind==='abroad'?`${p.flag} ${esc(p.school)}`:`${p.emoji} Ngành ${esc(p.name)}`;
  const done=Object.keys(c.marks).length,total=subjectsOf(p).length;
  return `<h3 class="sch-title">${title}</h3><p class="small muted">Đã đạt ${done}/${total} môn${done?` · điểm trung bình ${esc(c.gpa_text)}`:''}</p>${todayCard(env,k,c,p)}${c.ph==='study'?`<ul class="sch-subs">${c.subjects.map(s=>subjectCard(k,c,s)).join('')}</ul>${weekGrid(k,c)}`:''}${lifeCards(k,c,p)}
    <div class="sch-foot">${btn('Thôi học','schDrop',{},'ghost small')}</div>`;
}

/* ------------------------------------------------------------------ the degrees */
function degPage(env,k,v){
  const {api}=env;
  if(!v.deg.length)return `<p class="sch-intro">Chưa có tấm bằng nào. Học xong một ngành hoặc một học kỳ du học là có bằng, kèm danh hiệu 🎓 Cử nhân hay 🌏 Du học sinh.</p>`;
  return `<div class="sch-list">${v.deg.map(d=>`<article class="sch-diploma"><div class="sch-seal" aria-hidden="true">🎓</div><span class="sch-eyebrow">TỐT NGHIỆP LOẠI ${esc(d.cls.toUpperCase())}</span><h3>${esc(d.name)}</h3><p>${esc(api.state?.name||'Bạn')} · GPA ${esc(d.gpa_text)}/4 · ${esc(d.date)}</p><p class="small">Tiền công +${d.pct}% ở ${d.careers.map(c=>esc(place(api,c))).join(', ')}</p><small class="muted">Số hiệu ${esc(d.serial)}</small>${btn('Lưu bằng để in','schCert',{program:d.p},'ghost small')}</article>`).join('')}</div>`;
}

/* ------------------------------------------------------------------ quiz and result */
function questionView(u,q){
  const n=u.quiz.qs.length,i=u.qi;
  let body='';
  if(q.k==='c')body=`<div class="sch-opts">${q.options.map(o=>btn(esc(o.label),'schPick',{v:o.i},'sch-opt')).join('')}</div>`;
  else if(q.k==='t')body=`<div class="sch-tf">${btn('✅ Đúng','schPick',{v:'true'},'sch-opt')}${btn('❌ Sai','schPick',{v:'false'},'sch-opt')}</div>`;
  else if(q.k==='o'){const seq=u.order;body=`<p class="small muted">Chạm lần lượt theo đúng thứ tự.</p><div class="sch-opts">${q.items.map(o=>{const at=seq.indexOf(o.i);return btn(`${at>=0?`<b class="sch-n">${at+1}</b> `:''}${esc(o.label)}`,'schOrder',{i:o.i},`sch-opt${at>=0?' on':''}`,at>=0);}).join('')}</div><div class="sch-row">${btn('Làm lại','schOrderReset',{},'ghost small',!seq.length)}${btn('Xong câu này','schOrderDone',{},'primary small',seq.length!==q.items.length)}</div>`;}
  else body=`<div class="sch-num"><input id="sch-num" type="number" inputmode="numeric" min="0" step="1" aria-label="Đáp số" placeholder="Đáp số">${btn('Xong câu này','schNum',{},'primary')}</div>`;
  return `<p class="sch-eyebrow">Câu ${i+1}/${n}</p><div class="sch-progress"><i style="width:${100*i/n}%"></i></div><p class="sch-q">${esc(q.text)}</p>${body}`;
}
function quizPage(env,k,v){
  const u=st(env),z=u.quiz,c=v.cur,p=c?program(k,c.p):null;
  if(z.kind==='job')return `<article class="sch-card sch-now"><p class="sch-eyebrow">💼 Làm thêm · ${esc(p?.city||'')}</p><p class="sch-scene">${esc(z.scene)}</p><p class="sch-q">${esc(z.q)}</p><div class="sch-opts">${z.options.map((o,i)=>btn(esc(o),'schJob',{option:i},'sch-opt')).join('')}</div>${btn('← Quay lại','schQuit',{},'ghost small')}</article>`;
  const s=c?.subjects.find(x=>x.id===z.subject);
  const lecture=z.kind==='class'&&u.qi===0?`<div class="sch-lecture"><p class="sch-eyebrow">Buổi ${z.n}: ${esc(z.title)}</p><ul>${z.points.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:'';
  const sub=z.kind==='exam'?`Lần thi ${z.attempt} · đúng từ ${k.rules.exam_pass}/${k.rules.exam_q} câu là đạt`:z.kind==='hw'?'Điểm cao nhất được giữ':'Sai cũng không sao: điểm danh vẫn tính';
  return `<article class="sch-card sch-now sch-quiz"><p class="sch-eyebrow">${s?`${s.emoji} ${esc(s.name)}`:''} · ${KIND[z.kind]}</p><small class="muted">${sub}</small>${lecture}${questionView(u,z.qs[u.qi])}${btn('← Để sau','schQuit',{},'ghost small')}</article>`;
}
function resultPage(env,k){
  const u=st(env),r=u.result;
  const rows=(r.rows||[]).map(x=>`<li class="${x.ok?'ok':'no'}"><b>${x.ok?'✅':'💡'} ${esc(x.text)}</b>${x.ok?'':`<small>Đáp án: ${esc(x.right)}</small>`}<small>${esc(x.why)}</small></li>`).join('');
  return `<article class="sch-card sch-now sch-result"><h3>${r.passed===false?'📄':'🎉'} Đúng ${r.right}/${r.of} câu</h3><p>${esc(r.message||'')}</p>${rows?`<ol class="sch-review">${rows}</ol>`:''}${btn('Xong','schDone',{},'primary')}</article>`;
}

export function schoolView(env){
  const u=st(env),k=K(env),v=u.data,J=env.api.state?.journey;
  if(!J?.story||!k)return head()+`<div class="sheet-body"><p class="muted">Trường học có trong hành trình.</p></div>`;
  if(!v)return head()+`<div class="sheet-body"><p class="muted">Đang mở trường…</p></div>`;
  const note=u.note?`<p class="sch-note ${u.note.ok?'good':''}" role="status">${esc(u.note.text)}</p>`:'';
  let body;
  if(u.result)body=resultPage(env,k);
  else if(u.quiz&&v.cur)body=quizPage(env,k,v);
  else if(u.tab==='deg')body=degPage(env,k,v);
  else if(v.cur&&(u.tab==='abroad')===(v.cur.kind==='abroad'))body=curPage(env,k,v);
  else body=u.tab==='abroad'?abroadPage(env,k,v):uniPage(env,k,v);
  const lines=u.fly&&!u.quiz&&!u.result?`<ol class="sch-lines sch-arrive">${u.fly.map((l,i)=>`<li style="--i:${i}">${esc(l)}</li>`).join('')}</ol>`:'';
  return head(`${k.majors.length} ngành đại học · ${k.terms.length} nước du học`)+`<div class="sheet-body sch-body">${u.quiz||u.result?'':tabs(u,v)}${note}${lines}${body}</div>`;
}

/* ------------------------------------------------------------------ actions */
async function submit(env){
  const u=st(env),z=u.quiz,op={class:'jr_sch_class',hw:'jr_sch_hw',exam:'jr_sch_exam'}[z.kind];
  const r=await run(env,op,{subject:z.subject,answers:u.ans});
  u.quiz=null;u.ans=[];u.qi=0;u.order=[];
  if(r?.quiz)u.result={...r.quiz,message:r.message};
  else u.note=null;
}
async function answer(env,v){
  const u=st(env);u.ans.push(v);u.qi++;u.order=[];
  if(u.qi>=u.quiz.qs.length)await submit(env);
}
const top=()=>document.querySelector('#sheet .sheet-body')?.scrollTo?.(0,0);

export async function schoolAction(action,data,el,env){
  if(action==='school'){if(await schoolOpen(env,data||{}))env.openSheet('school');return true;}
  if(!/^sch[A-Z]/.test(action))return false;
  const u=st(env),k=K(env);
  switch(action){
    case'schTab':u.tab=data.tab;u.major=null;u.apply=null;u.note=null;u.fly=null;break;
    case'schMajor':u.major=data.id;u.note=null;top();break;
    case'schBack':u.major=null;u.apply=null;break;
    case'schApplyOpen':u.apply=data.program;u.docs=[];u.note=null;break;
    case'schDoc':{const id=data.id;u.docs=u.docs.includes(id)?u.docs.filter(x=>x!==id):[...u.docs,id];break;}
    case'schEnrol':{
      if(!await env.confirmAction(`Nhập học ngành ${data.name}?`,`Học phí học kỳ ${fmt(data.fee)} xu. Mỗi ngày sống học tối đa ${k?.rules?.per_day||2} buổi theo thời khóa biểu.`,'Nhập học'))return true;
      const r=await run(env,'jr_sch_enrol',{program:data.program});if(r){u.major=null;u.note={text:r.message,ok:true};}break;}
    case'schApply':{const r=await run(env,'jr_sch_apply',{program:data.program,docs:u.docs});if(r){u.apply=null;u.docs=[];u.note={text:r.message,ok:true};}break;}
    case'schVisa':{const r=await run(env,'jr_sch_visa',{option:Number(data.option)});if(r)u.note={text:r.message,ok:true};break;}
    case'schFly':{const r=await run(env,'jr_sch_fly');if(r){u.fly=r.lines||null;u.note={text:r.message,ok:true};}break;}
    case'schNext':{
      if(!await env.confirmAction(`Vào học kỳ ${data.n}?`,`Học phí ${fmt(data.fee)} xu.`,'Đóng học phí'))return true;
      const r=await run(env,'jr_sch_next');if(r)u.note={text:r.message,ok:true};break;}
    case'schDrop':{
      if(!await env.confirmAction('Thôi học?','Trường hoàn một nửa học phí của các buổi chưa học. Ngành đại học được bảo lưu các học kỳ đã xong.','Thôi học'))return true;
      const r=await run(env,'jr_sch_drop',{confirm:true});if(r)u.note={text:r.message,ok:false};break;}
    case'schOpen':{
      const r=await run(env,'jr_sch_view',{view:{open:data.kind,subject:data.subject}});
      if(r&&u.data?.quiz){u.quiz=u.data.quiz;u.qi=0;u.ans=[];u.order=[];u.result=null;u.note=null;u.fly=null;top();}
      else if(r)env.toast('Bài này chưa mở lúc này.');
      break;}
    case'schPick':{const q=u.quiz?.qs[u.qi];if(!q)break;await answer(env,q.k==='t'?data.v==='true':Number(data.v));break;}
    case'schOrder':u.order=u.order.includes(Number(data.i))?u.order:[...u.order,Number(data.i)];break;
    case'schOrderReset':u.order=[];break;
    case'schOrderDone':{const q=u.quiz?.qs[u.qi];if(q&&u.order.length===q.items.length)await answer(env,[...u.order]);break;}
    case'schNum':{const x=document.querySelector('#sch-num');const n=Number(x?.value);if(!x||x.value===''||!Number.isInteger(n)||n<0){x?.focus();return true;}await answer(env,n);break;}
    case'schQuit':u.quiz=null;u.ans=[];u.qi=0;u.order=[];break;
    case'schDone':u.result=null;break;
    case'schJob':{const r=await run(env,'jr_sch_job',{option:Number(data.option)});u.quiz=null;if(r)u.result={right:r.job?.ok?1:0,of:1,message:r.message,rows:[]};break;}
    case'schEvent':{const r=await run(env,'jr_sch_event',{event:data.event,option:Number(data.option)});if(r)u.note={text:r.message,ok:true};break;}
    case'schCert':saveDiploma(u.data?.deg?.find(d=>d.p===data.program),env.api);return true;
    default:return false;
  }
  env.renderSheet();return true;
}

function saveDiploma(d,api){
  if(!d)return;
  const html=`<!doctype html><html lang="vi"><meta charset="utf-8"><title>${esc(d.name)}</title><style>body{font:18px/1.6 Georgia,serif;color:#392e26;margin:64px;max-width:860px}article{border:3px double #968572;padding:48px;text-align:center}h1{font-size:30px}small{display:block}button{padding:12px;margin:24px}@media print{button{display:none}body{margin:0}}</style><article><small>PHỐ CÓ CHUYỆN · VĂN BẰNG TRONG GAME</small><h1>🎓 ${esc(d.name)}</h1><p>Cấp cho ${esc(api.state?.name||'Người chơi')}</p><p>Tốt nghiệp loại ${esc(d.cls)} · GPA ${esc(d.gpa_text)}/4</p><p>Ngày ${esc(d.date)} · Số hiệu ${esc(d.serial)}</p><small>Ghi nhận học tập trong trò chơi, không thay văn bằng thật.</small></article><button onclick="window.print()">In bản này</button></html>`;
  const blob=new Blob([html],{type:'text/html;charset=utf-8'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=`bang-${d.p}.html`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export const view=schoolView;
export const action=schoolAction;
