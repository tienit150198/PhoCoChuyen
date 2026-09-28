/** Teacher: "Kế hoạch lớp" — lessons in many subjects, grading, parent
 * meetings, covering a colleague, a school-year calendar of events and the
 * class notebook (each kid's trust, how they learn and their small story). */
import {icon,escapeHTML as esc} from '../icons.js';
import {procedureView} from './procedure.js';
import {titled} from './teach-tour.js';

const pill=(label,kind='')=>`<span class="tag ${kind}">${label}</span>`;
const cmdBtn=(label,command,payload={},style='')=>`<button type="button" class="btn ${style}" data-command="${command}" data-payload="${esc(JSON.stringify(payload))}">${label}</button>`;
const head=(title,sub)=>`<header class="sheet-head"><div class="grow"><span class="eyebrow">LỚP HỌC MẦM NẮNG</span><h2>${title}</h2><p>${sub}</p></div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
const KIND_TAG={lesson:'green',grading:'blue',meeting:'amber',event:'danger',duty:'blue'};
const GRADE={great:['Tuyệt vời','green'],ok:['Khá ổn','amber'],rough:['Còn vụng','']};
const STYLE_ICON={look:'🖼️',hands:'🧩',talk:'💬',short:'⏱️'};

function notebook(kids){
  if(!kids?.length)return '';
  const met=kids.filter(k=>k.trust>0||k.style);
  const card=k=>`<li class="nb-kid"><span class="tt-face" aria-hidden="true">${k.emoji}</span><div class="grow"><div class="nb-row"><b>${esc(k.name)}</b>${k.style?`<span class="tag green" title="${esc(k.style_label)}">${STYLE_ICON[k.style]} ${esc(k.style_label)}</span>`:'<span class="tag">❓ Chưa rõ cách học</span>'}</div><div class="nb-trust" role="meter" aria-label="Tin tưởng" aria-valuemin="0" aria-valuemax="12" aria-valuenow="${k.trust}"><i style="width:${Math.round(k.trust/12*100)}%"></i></div><small class="muted">${esc(k.trait)}${k.next?` · ${k.trust}/${k.next} 💛 tới chuyện mới`:' · 🌟 Đã trọn chuyện'}</small>${k.story.length?`<ul class="nb-story">${k.story.map(s=>`<li>✨ ${esc(s)}</li>`).join('')}</ul>`:''}</div></li>`;
  return `<details class="nb"><summary><b>📒 Sổ chủ nhiệm</b><small>Đã thân với ${met.length}/${kids.length} bạn</small></summary><p class="small muted">Giúp đúng cách, xử lý chuyện trong lớp tử tế và phản hồi phiếu riêng từng bạn để các bạn tin mình hơn.</p><ul class="nb-list">${kids.map(card).join('')}</ul></details>`;
}

export function classroomView(env){
  const {api}=env,room=api.state.careers[api.state.current],raw=room.classroom;
  if(!raw)return head('Kế hoạch lớp','Chỉ dành cho nghề giáo viên.')+`<div class="sheet-body"></div>`;
  const cl=titled(raw,api.state),open=room.open;
  const cal=`<div class="school-cal" aria-label="Lịch năm học">${cl.calendar.map((m,i)=>`<div class="cal-month ${i===cl.month_index?'now':''}"><b>${esc(m.month)}</b><span>${m.events.map(e=>esc(e.emoji)).join(' ')||'·'}</span></div>`).join('')}</div>`;
  let body='';
  if(cl.active){
    const a=cl.active;
    body=`<article class="card class-active"><div class="row wrap">${pill(esc(a.tag),KIND_TAG[a.kind])}<h3 class="grow">${esc(a.emoji)} ${esc(a.title)}</h3>${a.mistakes?pill(`${a.mistakes} lần thử lại`,'amber'):''}</div><p>${esc(a.intro)}</p></article>
      <div class="workbench"><section class="wb-main">${procedureView(a.steps,{command:'cl_submit',ui:env.ui})}
        <div class="row wrap space-top">${a.done?cmdBtn(icon('check',16)+' Hoàn thành hoạt động','cl_finish',{},'primary'):''}${cmdBtn('Tạm gác','cl_quit',{},'ghost small')}</div></section>
      <aside class="wb-side"><h4 class="section-title">${icon('clipboard',15)} Thông tin cần đọc</h4>${a.facts.map(f=>`<div class="fact-card"><b>${esc(f.title)}</b><p>${esc(f.text)}</p></div>`).join('')}</aside></div>`;
  }else{
    const recap=cl.recap?`<article class="card recap"><div class="row"><h3 class="grow">${esc(cl.recap.title)}</h3>${pill(...GRADE[cl.recap.grade])}</div><div class="perspectives">${cl.recap.perspectives.map(v=>`<div class="perspective"><span class="who">${esc(v.emoji)} <b>${esc(v.who)}</b></span><p>“${esc(v.text)}”</p></div>`).join('')}</div><p class="lesson">💡 ${esc(cl.recap.lesson)}</p></article>`:'';
    body=`${recap}${open?'':`<div class="notice">${icon('sun',17)}<div>Mở ca (vào lớp) để bắt đầu hoạt động hôm nay.</div></div>`}
      <h4 class="section-title">Hôm nay trong lịch · ${esc(cl.month)}</h4>
      <div class="activity-grid">${cl.offers.map(o=>`<article class="activity-card kind-${esc(o.kind)}"><div class="row"><span class="activity-emoji">${esc(o.emoji)}</span><div class="grow">${pill(esc(o.kind_label),KIND_TAG[o.kind])}${o.tag&&o.tag!==o.kind_label?' '+pill(esc(o.tag)):''}<h4>${esc(o.title)}</h4></div></div><p class="small">${esc(o.intro)}</p><div class="row spread"><small class="muted">${o.steps} bước · thưởng ${o.reward} xu</small>${open?cmdBtn('Bắt đầu '+icon('chevron',13),'cl_start',{activity:o.id},'small primary'):''}</div></article>`).join('')}</div>
      ${notebook(cl.notebook)}
      ${cl.history.length?`<h4 class="section-title">Đã làm gần đây</h4><ul class="history-list">${cl.history.map(h=>`<li><span>${esc(h.emoji)}</span><span class="grow">${esc(h.title)} <small class="muted">· ngày ${h.day}</small></span>${pill(...GRADE[h.grade])}</li>`).join('')}</ul>`:''}`;
  }
  return head('Kế hoạch lớp','Tiết học nhiều môn, chấm bài, gặp phụ huynh, dạy thay và các ngày hội theo lịch năm học.')+`<div class="sheet-body classroom-v4">${cal}${body}</div>`;
}
