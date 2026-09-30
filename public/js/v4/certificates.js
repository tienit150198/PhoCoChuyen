/* 🎓 Thi chứng chỉ (v0.9, story mode): the certificate centre (journey view 'certs'),
 * the home entry, the profile badges and the titles section. Certificates belong to the
 * player (state.journey.certificates) and cover related hired jobs; holding one gives a
 * failed interview at those places a second chance (content.journey.certs.bonus %).
 * Server: game/certificates.py. The exam key stays on the server until a paper is graded;
 * the practice quiz is a separate bank checked here in the browser. */
import {icon,escapeHTML as esc} from '../icons.js';
import {asset} from '../assets.js';

const attrs=obj=>Object.entries(obj).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,action,data={},style='',extra='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}${extra}>${label}</button>`;
const fmt=n=>Number(n||0).toLocaleString('vi-VN');

export function certCss(){
  if(typeof document!=='undefined'&&!document.querySelector('link[data-cert-css]')){const l=document.createElement('link');l.rel='stylesheet';l.href=asset('/css/certificates.css');l.dataset.certCss='1';document.head.append(l);}
}

const K=api=>api.content?.journey?.certs||null;
const placeOf=(api,cid)=>{const m=api.content.catalogue.find(x=>x.id===cid);return m?(m.place||m.short):cid;};
const held=rec=>!!(rec&&rec.earned_day!=null);

/** The certificate group for a hired job, and what the player holds of it. */
export function certInfo(api,cid){
  const k=K(api),J=api.state?.journey;if(!k||!J?.story)return null;
  const gid=k.by_career?.[cid],g=k.groups.find(x=>x.id===gid);if(!g)return null;
  const rec=J.certificates?.[gid]||null;
  return {g,rec,held:held(rec),bonus:k.bonus,cap:k.cap,studying:J.study?.cert===gid};
}

/* ------------------------------------------------------------------ home, profile, titles */
export function certsEntry(env){
  const {api}=env,J=api.state.journey,k=K(api);if(!J?.story||!k)return '';
  certCss();
  const got=k.groups.filter(g=>held(J.certificates?.[g.id])).length,st=J.study;
  const g=st&&k.groups.find(x=>x.id===st.cert);
  const line=st&&g?(st.ready_now?`${g.emoji} Bài thi ${g.name} đã mở`:`${g.emoji} Đang học · thi từ Ngày ${fmt(st.ready)}${st.days_left?` (còn ${st.days_left} ngày)`:''}`):'Học rồi thi lấy chứng chỉ nghề';
  return `<button type="button" class="jr-card ct-entry" data-action="jrCerts"><span class="ct-entry-icon" aria-hidden="true">🎓</span><span class="grow"><b>Thi chứng chỉ</b><small>${esc(line)}</small></span>${st?.ready_now?'<span class="tag green">Vào thi</span>':`<span class="ct-count">${got}/${k.groups.length}</span>`}${icon('arrow',16)}</button>`;
}

/** Earned certificates as badges (profile card). */
export function certBadges(env){
  const {api}=env,J=api.state.journey,k=K(api);if(!J?.story||!k)return '';
  const rows=k.groups.filter(g=>held(J.certificates?.[g.id]));if(!rows.length)return '';
  certCss();
  return `<div class="ct-badges" aria-label="Chứng chỉ đã có">${rows.map(g=>{const r=J.certificates[g.id];
    return `<button type="button" class="ct-badge" data-action="jrCerts" data-cert="${esc(g.id)}" title="${esc(`${g.name} · điểm cao nhất ${r.best}`)}"><span aria-hidden="true">${g.emoji}</span><b>${esc(g.short)}</b><i>${r.best}</i></button>`;}).join('')}</div>`;
}

/** The certificates section of the titles page. */
export function certTitles(env){
  const {api}=env,J=api.state.journey,k=K(api);if(!J?.story||!k)return '';
  certCss();
  const got=k.groups.filter(g=>held(J.certificates?.[g.id])).length;
  const tiles=k.groups.map(g=>{const r=J.certificates?.[g.id];
    if(held(r))return `<button type="button" class="jr-title earned" data-action="jrCerts" data-cert="${esc(g.id)}"><span class="jr-title-emoji" aria-hidden="true">${g.emoji}</span><b>${esc(g.name)}</b><small>${esc(g.issuer)}</small><em>Ngày sống ${fmt(r.earned_day)} · điểm cao nhất ${r.best}</em></button>`;
    return `<button type="button" class="jr-title" data-action="jrCerts" data-cert="${esc(g.id)}"><span class="jr-title-emoji" aria-hidden="true">${g.emoji}</span><b>${esc(g.name)}</b><small>${r?`Đã thi ${r.attempts} lần · cao nhất ${r.best} điểm`:'Chưa thi'}</small><em>Học và thi ở 🎓 Thi chứng chỉ</em></button>`;}).join('');
  return `<section class="jr-title-cat"><h3>Chứng chỉ nghề <small>${got}/${k.groups.length}</small></h3><div class="jr-title-grid">${tiles}</div></section>`;
}

/* ------------------------------------------------------------------ the centre */
function head(title,sub){
  return `<header class="sheet-head jr-head"><button type="button" class="btn ghost small jr-back" data-action="jrView" data-view="home" aria-label="Quay lại hành trình">${icon('back',18)}</button><div class="grow"><span class="eyebrow">HÀNH TRÌNH</span><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div></header>`;
}
const MODE={class:'Lớp cấp tốc',self:'Tự học'};

function examCard(env,k,g,st){
  const p=st.paper,next=p.qs.find(q=>!(q in p.answers)),q=g.questions[next],n=Object.keys(p.answers).length;
  if(!q)return '';
  const pct=Math.round(100*n/p.qs.length),h=q.hint,shown=!!(h&&(env.ui.certHint||{})[next]);
  const tip=!h?'':shown?`<p class="ct-hint"><span aria-hidden="true">📖</span><span><b>Nhớ lại bài học:</b> ${esc(g.notes[h.note]||'')}</span></p>`
    :`<button type="button" class="btn ghost small ct-hint-btn" data-action="jrCertHint" data-q="${esc(next)}">💡 Gợi ý (miễn phí)</button>`;
  return `<section class="card ct-exam" aria-label="Bài thi"><div class="row spread"><span class="eyebrow">${esc(g.emoji)} Bài thi · lần ${p.attempt}</span><b>Câu ${n+1}/${p.qs.length}</b></div>
    <div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="${p.qs.length}" aria-valuenow="${n}"><i style="width:${pct}%"></i></div>
    <p class="small muted">Đúng <b>${k.pass_mark}/${k.draw}</b> là đạt · phân vân cứ bấm 💡, không trừ điểm.</p>
    <p class="ct-q">${esc(q.text)}</p>
    <div class="ct-opts">${q.options.map((o,i)=>{const off=shown&&o.id===h.off;
      return `<button type="button" class="choice ct-opt${off?' ct-off':''}" data-command="jr_cert_answer" data-payload="${esc(JSON.stringify({question:next,option:o.id}))}"${off?' disabled aria-label="Đáp án đã loại"':''}><span class="ct-key" aria-hidden="true">${'ABCD'[i]}</span><span>${esc(o.label)}</span></button>`;}).join('')}</div>${tip}</section>`;
}

function practice(env,g){
  const pick=(env.ui.certPractice||{})[g.id]||{};
  const rows=g.practice.map((q,i)=>{const got=pick[i];
    return `<li class="ct-pq"><p><b>${i+1}.</b> ${esc(q.text)}</p><div class="ct-opts">${q.options.map(o=>{const cls=got==null?'':o.id===q.answer?' ok':o.id===got?' bad':'';
      return `<button type="button" class="choice ct-opt${cls}" data-action="jrCertPractice" data-cert="${esc(g.id)}" data-q="${i}" data-option="${esc(o.id)}"${got!=null?' disabled':''}>${esc(o.label)}</button>`;}).join('')}</div>
      ${got!=null?`<p class="small ${got===q.answer?'ct-good':'ct-bad'}">${got===q.answer?'✓ Đúng.':'✗ Chưa đúng.'} ${esc(q.why)}</p>`:''}</li>`;}).join('');
  const done=Object.keys(pick).length,right=g.practice.filter((q,i)=>pick[i]===q.answer).length;
  return `<div class="ct-box"><h4 class="ct-h">✏️ Làm thử ${g.practice.length} câu${done===g.practice.length?` · đúng ${right}/${done}`:''}</h4><p class="small muted">Câu làm thử không tính điểm và khác đề thi thật.</p><ol class="ct-practice">${rows}</ol>${done?btn('Làm lại','jrCertPractice',{cert:g.id,reset:1},'ghost small'):''}</div>`;
}

function studyCard(env,k,g,st){
  const list=`<ul class="ct-notes">${g.notes.map(n=>`<li>${esc(n)}</li>`).join('')}</ul>`;
  const notes=st.ready_now?`<details class="ct-box"><summary>📖 Mở sách: ${g.notes.length} ý chính</summary>${list}</details>`
    :`<div class="ct-box"><h4 class="ct-h">📖 Bài học · ${g.notes.length} ý chính</h4>${list}</div>`;
  const status=st.ready_now?examCard(env,k,g,st)
    :`<p class="notice blue small">${icon('leaf',15)}<span><b>Bài thi mở từ Ngày ${fmt(st.ready)}</b> (còn ${st.days_left} ngày${st.days_left===1?' · sau khi khép ca hôm nay':''}). Làm một ngày ở đâu đó rồi quay lại thi nhé.</span></p>`;
  return `<section class="jr-card ct-study" aria-label="Khóa đang học"><div class="ct-top"><span class="ct-emoji" aria-hidden="true">${g.emoji}</span><div class="grow"><span class="eyebrow">Đang học · ${MODE[st.mode]}${st.fee?` · đã đóng ${fmt(st.fee)} xu`:''}</span><h3>${esc(g.name)}</h3></div></div>
    ${status}${notes}${st.ready_now?`<details class="ct-box"><summary>✏️ Làm thử trước (không tính điểm)</summary>${practice(env,g)}</details>`:practice(env,g)}
    <div class="row wrap">${btn('Bỏ khóa học','jrCertDrop',{},'ghost small')}</div></section>`;
}

function againButtons(api,g){
  const J=api.state.journey,C=api.state.careers;
  const ids=g.careers.filter(cid=>C[cid]&&J.unlocked?.includes(cid)&&C[cid].job?.required&&C[cid].job.status!=='hired');
  return ids.map(cid=>btn(`${icon('briefcase',15)} Xin việc ở ${esc(placeOf(api,cid))}`,'choose',{career:cid},'primary')).join('');
}

function paperCard(env,k){
  const {api}=env,P=api.state.journey.cert_paper;if(!P)return '';
  const g=k.groups.find(x=>x.id===P.cert);if(!g)return '';
  const bad=P.review.filter(r=>!r.ok);
  const list=`<ol class="jb-review">${P.review.map(r=>`<li class="${r.ok?'ok':'bad'}"><b>${r.ok?'✓':'✗'} ${esc(r.text)}</b>${r.ok?'':`<small>Bạn chọn: ${esc(r.options[r.picked]||'—')}</small><small>Đúng: ${esc(r.options[r.answer]||'')} — ${esc(r.why)}</small>`}</li>`).join('')}</ol>`;
  const J=api.state.journey,fee=g.retake_fee,poor=J.wallet<fee;
  const again=P.passed?againButtons(api,g):J.study?'':`<button type="button" class="btn primary" data-action="jrCertEnrol" data-cert="${esc(g.id)}" data-mode="class"${poor?' disabled':''}>📚 Ôn & thi lại ngay · ${fmt(fee)} xu</button>${btn(`📖 Tự học, thi từ Ngày ${fmt(J.life_day+k.self_days)}`,'jrCertEnrol',{cert:g.id,mode:'self'},'cream')}`;
  return `<section class="card ct-result ${P.passed?'good':'bad'}"><span class="eyebrow">Bài thi gần nhất · Ngày ${fmt(P.day)}</span>
    <h3>${g.emoji} ${esc(g.name)}: ${P.passed?'Đạt':'Chưa đạt'}</h3>
    <div class="ct-score"><b>${P.score}</b><span>điểm · đúng ${P.right}/${k.draw} câu</span></div>
    ${P.passed?`<p class="small">Tỷ lệ được nhận +${k.bonus}% (tối đa ${k.cap}%) ở ${g.careers.map(cid=>esc(placeOf(api,cid))).join(', ')} khi điểm phỏng vấn chưa đủ 60.</p>`
      :`<p class="small">Cần đúng ${k.pass_mark}/${k.draw} câu. Xem lời giải bên dưới rồi thi lại: mỗi lần là một đề khác, vẫn có 💡 gợi ý.</p>`}
    ${again?`<div class="ct-actions">${again}</div>`:''}
    <details class="ct-box"${!P.passed&&bad.length?' open':''}><summary>Xem lời giải (${bad.length?`${bad.length} câu sai`:'đúng hết'})</summary>${list}</details></section>`;
}

function groupCard(env,k,g,focus){
  const {api}=env,J=api.state.journey,r=J.certificates?.[g.id],st=J.study,has=held(r);
  const fee=r?.attempts?g.retake_fee:g.fee,max=r&&r.best>=100;
  let actions='';
  if(st?.cert===g.id)actions=`<p class="small muted">Đang học khóa này (ở trên).</p>`;
  else if(st)actions=`<p class="small muted">Đang học một khóa khác. Thi xong hoặc bỏ khóa đó rồi đăng ký tiếp nhé.</p>`;
  else if(max)actions=`<p class="small ct-good">Điểm tối đa rồi. Giỏi quá!</p>`;
  else{
    const poor=J.wallet<fee;
    actions=`<div class="ct-actions">
      <button type="button" class="btn primary ct-big" data-action="jrCertEnrol" data-cert="${esc(g.id)}" data-mode="class"${poor?' disabled':''}><span>📚 ${r?.attempts?'Lớp ôn':'Lớp cấp tốc'} · ${fmt(fee)} xu</span><small>${poor?`Ví còn ${fmt(Math.max(0,J.wallet))} xu, thiếu ${fmt(fee-Math.max(0,J.wallet))} xu`:k.class_days?`Thi từ Ngày ${fmt(J.life_day+k.class_days)}`:'Học xong thi ngay hôm nay'}</small></button>
      <button type="button" class="btn cream ct-big" data-action="jrCertEnrol" data-cert="${esc(g.id)}" data-mode="self"><span>📖 Tự học · miễn phí</span><small>Thi từ Ngày ${fmt(J.life_day+k.self_days)}${k.self_days===1?' (ngày mai)':` (còn ${k.self_days} ngày)`}</small></button></div>`;
  }
  const status=has?`<span class="tag green">✓ Đã có · ${r.best} điểm</span>`:r?`<span class="tag amber">Đã thi ${r.attempts} lần · cao nhất ${r.best}</span>`:'<span class="tag">Chưa có</span>';
  return `<article class="jr-card ct-group${focus?' focus':''}${has?' earned':''}" id="ct-${esc(g.id)}"><div class="ct-top"><span class="ct-emoji" aria-hidden="true">${g.emoji}</span><div class="grow"><h3>${esc(g.name)}</h3><small class="muted">${esc(g.issuer)}</small></div></div>
    <div class="ct-status">${status}</div>
    <p class="small">${esc(g.intro)}</p>
    <p class="small muted">Dùng cho: ${g.careers.filter(cid=>api.state.careers[cid]).map(cid=>esc(placeOf(api,cid))).join(', ')}</p>
    ${actions}</article>`;
}

export function certsView(env){
  const {api,ui}=env,J=api.state.journey,k=K(api);
  certCss();
  const title='🎓 Thi chứng chỉ';
  if(!J?.story||!k)return head(title,'')+`<div class="sheet-body jr-body"><p class="muted">Thi chứng chỉ có trong hành trình.</p></div>`;
  const st=J.study,sg=st&&k.groups.find(x=>x.id===st.cert);
  const focus=ui.certFocus&&k.groups.some(g=>g.id===ui.certFocus)?ui.certFocus:null;
  const order=[...k.groups].sort((a,b)=>(b.id===focus)-(a.id===focus));
  const lead=`Đề ngắn ${k.draw} câu, đúng ${k.pass_mark} là đạt, được mở sách và có 💡 gợi ý. Có chứng chỉ thì khi phỏng vấn chưa đủ điểm vẫn thêm ${k.bonus}% cơ hội được nhận.`;
  return head(title,esc(lead))+`<div class="sheet-body jr-body ct-body">
    ${sg?studyCard(env,k,sg,st):''}${paperCard(env,k)}
    <h3 class="jr-sub">Các chứng chỉ · ví còn ${fmt(J.wallet)} xu</h3>
    <div class="ct-grid">${order.map(g=>groupCard(env,k,g,g.id===focus)).join('')}</div></div>`;
}

/* ------------------------------------------------------------------ actions */
export async function certAction(action,data,el,env){
  const {api,ui,cmd,confirmAction,renderSheet,openSheet}=env,k=K(api),J=api.state.journey;
  switch(action){
    case'jrCerts':
      ui.jrView='certs';ui.certFocus=data.cert||null;ui.certCareer=data.career||null;
      if(ui.view==='home')renderSheet(false);else openSheet('home');
      document.getElementById('sheet')?.scrollTo?.(0,0);return true;
    case'jrCertEnrol':{
      const g=k?.groups.find(x=>x.id===data.cert);if(!g)return true;
      const payload={cert:g.id,mode:data.mode};if(ui.certCareer&&g.careers.includes(ui.certCareer))payload.career=ui.certCareer;
      if(data.mode==='class'){
        const r=J.certificates?.[g.id],fee=r?.attempts?g.retake_fee:g.fee;
        const ok=await confirmAction(`Đăng ký ${r?.attempts?'lớp ôn':'lớp cấp tốc'}?`,`${g.name}: học phí ${fee} xu trừ vào ví (ví còn ${J.wallet} xu). ${k.class_days?`Bài thi mở từ Ngày ${J.life_day+k.class_days}.`:'Học xong vào thi luôn hôm nay.'}`,`Đóng ${fee} xu`,{cost:fee,pocket:'wallet'});
        if(!ok)return true;
      }
      ui.certPractice={...(ui.certPractice||{}),[g.id]:{}};ui.certHint={};
      if(await cmd('jr_cert_enrol',payload))document.getElementById('sheet')?.scrollTo?.(0,0);
      return true;}
    case'jrCertDrop':
      if(await confirmAction('Bỏ khóa học?','Học phí đã đóng không được hoàn. Muốn thi thì đăng ký lại từ đầu.','Bỏ khóa'))await cmd('jr_cert_drop',{confirm:true});
      return true;
    case'jrCertHint':
      ui.certHint={...(ui.certHint||{}),[data.q]:true};renderSheet(false);return true;
    case'jrCertPractice':{
      const all={...(ui.certPractice||{})};
      if(data.reset)all[data.cert]={};else all[data.cert]={...(all[data.cert]||{}),[data.q]:data.option};
      ui.certPractice=all;renderSheet(false);return true;}
  }
  return false;
}
