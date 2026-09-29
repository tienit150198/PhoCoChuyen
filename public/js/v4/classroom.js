/** Teacher: "Kế hoạch lớp" — lessons in many subjects, grading, parent
 * meetings, covering a colleague, a school-year calendar of events and the
 * class notebook (each kid's trust, how they learn and their small story).
 * Laid out like a teacher's planner: the year's months, today's page of
 * entries, the one being prepared, notes after class and the log. */
import {icon,escapeHTML as esc} from '../icons.js';
import {procedureView} from './procedure.js';
import {titled} from './teach-tour.js';

const pill=(label,kind='')=>`<span class="tag ${kind}">${label}</span>`;
const cmdBtn=(label,command,payload={},style='')=>`<button type="button" class="btn ${style}" data-command="${command}" data-payload="${esc(JSON.stringify(payload))}">${label}</button>`;
const head=(title,sub)=>`<header class="sheet-head"><div class="grow"><span class="eyebrow">LỚP HỌC MẦM NẮNG</span><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
const KIND_TAG={lesson:'green',grading:'blue',meeting:'amber',event:'danger',duty:'blue'};
const GRADE={great:['Tuyệt vời','green'],ok:['Khá ổn','amber'],rough:['Còn vụng','']};
const STYLE_ICON={look:'🖼️',hands:'🧩',talk:'💬',short:'⏱️'};

function notebook(kids){
  if(!kids?.length)return '';
  const met=kids.filter(k=>k.trust>0||k.style);
  const card=k=>`<li class="nb-kid"><span class="tt-face" aria-hidden="true">${k.emoji}</span><div class="grow"><div class="nb-row"><b>${esc(k.name)}</b>${k.style?`<span class="tag green">${STYLE_ICON[k.style]} ${esc(k.style_label)}</span>`:'<span class="tag">❓ Chưa rõ cách học</span>'}</div><div class="nb-trust" role="meter" aria-label="Tin tưởng" aria-valuemin="0" aria-valuemax="12" aria-valuenow="${k.trust}"><i style="width:${Math.round(k.trust/12*100)}%"></i></div><small class="muted">${esc(k.trait)}${k.next?` · ${k.trust}/${k.next} 💛 tới chuyện mới`:' · 🌟 Đã trọn chuyện'}</small>${k.story.length?`<ul class="nb-story">${k.story.map(s=>`<li>✨ ${esc(s)}</li>`).join('')}</ul>`:''}</div></li>`;
  return `<details class="nb"><summary><b>📒 Sổ chủ nhiệm</b><small>Đã thân với ${met.length}/${kids.length} bạn</small></summary><ul class="nb-list">${kids.map(card).join('')}</ul></details>`;
}

const kind=(k,label,tag='')=>`<span class="cp-kind">${pill(esc(label),KIND_TAG[k])}${tag&&tag!==label?`<small>${esc(tag)}</small>`:''}</span>`;

export function classroomView(env){
  const {api}=env,room=api.state.careers[api.state.current],raw=room.classroom;
  if(!raw)return head('Kế hoạch lớp','Chỉ dành cho nghề giáo viên.')+`<div class="sheet-body"></div>`;
  const cl=titled(raw,api.state),open=room.open,day=room.day||1,week=(day-1)%4+1;
  const months=`<ol class="cp-months" aria-label="Lịch năm học">${cl.calendar.map((m,i)=>`<li class="${i===cl.month_index?'now':i<cl.month_index?'past':''}"${i===cl.month_index?' aria-current="date"':''}><b>${esc(m.month)}</b><span>${m.events.map(e=>`<i role="img" aria-label="${esc(e.title)}">${esc(e.emoji)}</i>`).join(' ')||'·'}</span></li>`).join('')}</ol>`;
  const date=`<p class="cp-date"><b>📅 ${esc(cl.month)} · Tuần ${week}</b><span>Ngày ${day} của năm học</span></p>`;
  let body='';
  if(cl.active){
    const a=cl.active;
    const notes=a.facts.length?`<details class="fold" open><summary>📌 Ghi chú cần đọc · ${a.facts.length}</summary><div class="fold-body cp-notes">${a.facts.map(f=>`<div class="cp-note"><b>${esc(f.title)}</b><p>${esc(f.text)}</p></div>`).join('')}</div></details>`:'';
    body=`<article class="cp-page cp-active"><h3><span>✍️ Đang soạn</span>${a.mistakes?`<small>${a.mistakes} lần thử lại</small>`:''}</h3>${kind(a.kind,a.tag)}<div class="cp-main"><h4>${esc(a.emoji)} ${esc(a.title)}</h4><p>${esc(a.intro)}</p></div></article>
      ${notes}
      <section class="cp-steps">${procedureView(a.steps,{command:'cl_submit',ui:env.ui})}</section>
      <div class="cp-actions">${a.done?cmdBtn(icon('check',16)+' Hoàn thành hoạt động','cl_finish',{},'primary'):''}${cmdBtn('Tạm gác','cl_quit',{},'ghost')}</div>`;
  }else{
    const recap=cl.recap?`<article class="cp-page cp-recap"><h3><span>📝 Nhận xét sau giờ</span>${pill(...GRADE[cl.recap.grade])}</h3><div class="cp-main"><h4>${esc(cl.recap.title)}</h4></div><div class="perspectives">${cl.recap.perspectives.map(v=>`<div class="perspective"><span class="who">${esc(v.emoji)} <b>${esc(v.who)}</b></span><p>“${esc(v.text)}”</p></div>`).join('')}</div><p class="lesson">💡 ${esc(cl.recap.lesson)}</p></article>`:'';
    const rows=cl.offers.map(o=>`<li class="cp-row kind-${esc(o.kind)}">${kind(o.kind,o.kind_label,o.tag)}<div class="cp-main"><h4>${esc(o.emoji)} ${esc(o.title)}</h4><p>${esc(o.intro)}</p></div><div class="cp-meta"><small>${o.steps} bước · +${o.reward} xu</small>${open?cmdBtn('Bắt đầu '+icon('chevron',13),'cl_start',{activity:o.id},'small primary'):''}</div></li>`).join('');
    const today=`<article class="cp-page"><h3><span>🗒️ Việc hôm nay</span><small>${cl.offers.length} mục</small></h3>${rows?`<ul class="cp-rows">${rows}</ul>`:'<p class="small muted">Hôm nay đã làm hết các mục trong sổ.</p>'}</article>`;
    const log=cl.history.length?`<article class="cp-page"><h3><span>📚 Đã làm gần đây</span></h3><ul class="cp-log">${cl.history.map(h=>`<li><span aria-hidden="true">${esc(h.emoji)}</span><span>${esc(h.title)} <small>· ngày ${h.day}</small></span>${pill(...GRADE[h.grade])}</li>`).join('')}</ul></article>`:'';
    body=`${recap}${open?'':`<div class="notice">${icon('sun',17)}<div>Mở ca (vào lớp) để bắt đầu hoạt động hôm nay.</div></div>`}${today}${notebook(cl.notebook)}${log}`;
  }
  return head('Kế hoạch lớp','')+`<div class="sheet-body classroom-v4"><div class="cp">${date}${months}${body}</div></div>`;
}
