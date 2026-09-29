/** Teacher: "Kế hoạch lớp" — lessons in many subjects, grading, parent
 * meetings, covering a colleague, a school-year calendar of events and the
 * class notebook (each kid's trust, how they learn and their small story).
 * Laid out like a teacher's planner: the year's months, today's page of
 * entries, the one being prepared, notes after class and the log. */
import {icon,escapeHTML as esc} from '../icons.js';
import {procedureView} from './procedure.js';
import {titled,bindClassApi,clBubbles,clReply,classVoice} from './teach-tour.js';

const pill=(label,kind='')=>`<span class="tag ${kind}">${label}</span>`;
const cmdBtn=(label,command,payload={},style='',disabled=false)=>`<button type="button" class="btn ${style}" data-command="${command}" data-payload="${esc(JSON.stringify(payload))}"${disabled?' disabled':''}>${label}</button>`;
const head=(title,sub)=>`<header class="sheet-head"><div class="grow"><span class="eyebrow">LỚP HỌC MẦM NẮNG</span><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
const KIND_TAG={lesson:'green',grading:'blue',meeting:'amber',event:'danger',duty:'blue'};
const GRADE={great:['Tuyệt vời','green'],ok:['Khá ổn','amber'],rough:['Còn vụng','']};
const STYLE_ICON={look:'🖼️',hands:'🧩',talk:'💬',short:'⏱️'};

const face=w=>w<35?'😢':w<45?'😕':w>=65?'😊':'🙂';
function bars(p,subjects){
  return `<div class="cl-bars">${subjects.map(s=>{const v=p.prog[s.id],tone=v<40?'bad':v<55?'warn':'good';return `<div class="cl-bar ${tone}" role="meter" aria-label="${esc(s.label)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${v}"><span>${s.emoji} ${esc(s.label)}</span><i><b style="width:${v}%"></b></i><strong>${v}</strong></div>`;}).join('')}</div>`;
}

function notebook(kids,care){
  if(!kids?.length)return '';
  const met=kids.filter(k=>k.trust>0||k.style),row=id=>care?.pupils?.find(p=>p.id===id);
  const card=k=>{const p=row(k.id);return `<li class="nb-kid"><span class="tt-face" aria-hidden="true">${k.emoji}</span><div class="grow"><div class="nb-row"><b>${esc(k.name)}</b>${k.style?`<span class="tag green">${STYLE_ICON[k.style]} ${esc(k.style_label)}</span>`:'<span class="tag">❓ Chưa rõ cách học</span>'}</div>${p?`${bars(p,care.subjects)}<p class="cl-mood">${face(p.well)} ${esc(p.mood)} · 🙋 ${esc(p.voice_label)}</p>`:''}<div class="nb-trust" role="meter" aria-label="Tin tưởng" aria-valuemin="0" aria-valuemax="12" aria-valuenow="${k.trust}"><i style="width:${Math.round(k.trust/12*100)}%"></i></div><small class="muted">${esc(k.trait)}${k.next?` · ${k.trust}/${k.next} 💛 tới chuyện mới`:' · 🌟 Đã trọn chuyện'}</small>${k.story.length?`<ul class="nb-story">${k.story.map(s=>`<li>✨ ${esc(s)}</li>`).join('')}</ul>`:''}</div></li>`;};
  return `<details class="nb"><summary><b>📒 Sổ chủ nhiệm</b><small>Đã thân với ${met.length}/${kids.length} bạn</small></summary><ul class="nb-list">${kids.map(card).join('')}</ul></details>`;
}

/* ---- care loop: who needs attention, parents, homework, seats ---- */
function watch(care){
  const rows=[];
  for(const p of care.pupils){
    if(p.behind.length)rows.push(['bad',`${p.emoji} ${p.name} đang hổng ${p.behind.join(', ')}`]);
    if(p.flags.includes('sad'))rows.push(['bad',`${p.emoji} ${p.name} buồn, thu mình`]);
    else if(p.flags.includes('low'))rows.push(['warn',`${p.emoji} ${p.name} cần động viên`]);
    if(p.flags.includes('opening'))rows.push(['good',`${p.emoji} ${p.name} bắt đầu dám hỏi 🌱`]);
  }
  const log=care.log.length?`<ul class="cl-log">${care.log.map(l=>`<li><small>Ngày ${l.day}</small> ${esc(l.text)}</li>`).join('')}</ul>`:'';
  return `<article class="cp-page cl-watch"><h3><span>👀 Cần để ý</span><small>${rows.length?rows.length+' điều':'Cả lớp ổn'}</small></h3>${rows.length?`<ul class="cl-flags">${rows.map(([tone,text])=>`<li class="${tone}">${esc(text)}</li>`).join('')}</ul>`:'<p class="small muted">Chưa bạn nào bị hổng bài hay buồn.</p>'}${log}</article>`;
}

function trustMeter(n){return `<span class="cl-trust" role="meter" aria-label="Tin tưởng" aria-valuemin="0" aria-valuemax="10" aria-valuenow="${n}"><i style="width:${n*10}%"></i></span>`;}

function inbox(care,open){
  const rows=care.parents.map(p=>{
    const key='par:'+p.kid,body={kind:'parent',pupil:p.kid},last=p.thread[p.thread.length-1];
    if(open&&p.waiting&&last?.mode==='scripted')classVoice(key,body);
    const st=p.waiting?(p.late?['danger','Trả lời muộn']:['amber','Chờ trả lời']):p.called?['green','✓ Đã liên lạc']:p.overdue?['danger','Lâu chưa liên lạc']:p.due?['amber','Đến hẹn']:null;
    const reply=!open?'<p class="small muted">Mở ca để nhắn phụ huynh.</p>':!p.can?'<p class="small muted">Hôm nay đã nhắn rồi, mai nhắn tiếp nhé.</p>':clReply(key,body,p.options,200,p.waiting?`Trả lời ${p.name}…`:`Nhắn ${p.name}…`);
    return `<details class="cl-par${p.waiting?' waiting':''}" data-kid="${esc(p.kid)}"><summary><span class="tt-face" aria-hidden="true">${p.emoji}</span><span class="grow"><b>${esc(p.name)}</b><small>${esc(p.rel)}</small><em data-no-translate>${esc(last?last.text:'Chưa có tin nhắn.')}</em></span><span class="cl-par-side">${st?pill(st[1],st[0]):''}${trustMeter(p.trust)}</span></summary><div class="cl-par-body">${p.thread.length?'':`<p class="small muted">Chưa nhắn gì với ${esc(p.name)}.</p>`}${clBubbles(p.thread,key,{typing:`${p.name} đang nhắn…`})}${reply}</div></details>`;
  }).join('');
  return `<article class="cp-page cl-inbox"><h3><span>💌 Phụ huynh</span><small>${care.waiting?`${care.waiting} tin chờ · `:''}Tuần này ${care.called}/${care.goal}</small></h3><p class="small muted">Mỗi phụ huynh cần nghe tin về con khoảng mỗi tuần. Trả lời cụ thể, đúng việc của con; không kể chuyện con nhà khác.</p><div class="cl-pars">${rows}</div></article>`;
}

function homework(care,open){
  const hw=care.hw,todo=care.books.filter(b=>!b.mark),done=care.books.length-todo.length;
  const give=hw.today?`<p class="cl-hw-now">✓ Đã giao bài ${esc(hw.today.subject)} (${esc(hw.today.size)}) cho ${hw.today.count} bạn. Mai các bạn nộp vở.</p>`:hw.can&&open?`<p class="cl-hw-now">Giao bài ${esc(hw.subject)} về nhà:</p><div class="cp-actions">${hw.sizes.map(s=>cmdBtn(esc(s.label),'cl_hw',{size:s.id},'small')).join('')}</div>`:'<p class="small muted">Dạy xong một tiết rồi giao bài về nhà. Bài nộp vào hôm sau.</p>';
  const card=b=>`<li class="cl-book"><div class="cl-book-top"><span class="tt-face" aria-hidden="true">${b.emoji}</span><div><b>${esc(b.name)}</b><small>${esc(b.subject)} · ${esc(b.size)}</small></div></div><p>📓 ${esc(b.clue)}</p><div class="cl-marks">${care.marks.map(m=>cmdBtn(`${m.emoji} ${esc(m.label)}`,'cl_hw_mark',{book:b.id,mark:m.id},'small ghost',!open)).join('')}</div></li>`;
  return `<article class="cp-page cl-hw"><h3><span>📚 Bài về nhà</span><small>${todo.length?`${todo.length} vở chờ chấm`:done?`Đã chấm ${done} vở`:''}</small></h3>${give}${todo.length?`<ul class="cl-books">${todo.map(card).join('')}</ul>`:''}</article>`;
}

function seatPlan(care,open){
  const lock=!open||care.busy;
  const seat=s=>{
    const others=care.seats.filter(x=>x.kid!==s.kid);
    return `<li class="cl-seat${s.notes.some(n=>n.tone==='bad')?' bad':s.notes.length?' good':''}"><div class="cl-seat-top"><span class="tt-face" aria-hidden="true">${s.emoji}</span><b>${esc(s.name)}</b>${s.window?'<span class="cl-win" role="img" aria-label="Cạnh cửa sổ">🪟</span>':''}</div>${s.notes.map(n=>`<small class="${n.tone}">${n.tone==='good'?'↑':'↓'} ${esc(n.text)}</small>`).join('')}${lock?'':`<details class="cl-swap"><summary>Đổi chỗ</summary><div>${others.map(o=>cmdBtn(`${o.emoji} ${esc(o.name)}`,'cl_seat',{a:s.kid,b:o.kid},'small ghost')).join('')}</div></details>`}</li>`;
  };
  const rows=[0,1,2,3].map(r=>`<li class="cl-desk"><small>Bàn ${r+1}${r===0?' · gần bảng':r===3?' · cuối lớp':''}</small><ul>${care.seats.filter(s=>s.row===r).map(seat).join('')}</ul></li>`).join('');
  return `<article class="cp-page cl-seats"><h3><span>🪑 Sơ đồ chỗ ngồi</span><small>${care.busy?'Đang trong tiết':'Bục giảng ở trên'}</small></h3><p class="small muted">Chỗ ngồi và bạn cùng bàn đổi cách các bạn học mỗi tiết.</p><ol class="cl-room">${rows}</ol></article>`;
}

const kind=(k,label,tag='')=>`<span class="cp-kind">${pill(esc(label),KIND_TAG[k])}${tag&&tag!==label?`<small>${esc(tag)}</small>`:''}</span>`;

export function classroomView(env){
  const {api}=env,room=api.state.careers[api.state.current],raw=room.classroom;
  bindClassApi(api);
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
    const care=cl.care?`${watch(cl.care)}${inbox(cl.care,open)}${homework(cl.care,open)}${seatPlan(cl.care,open)}`:'';
    body=`${recap}${open?'':`<div class="notice">${icon('sun',17)}<div>Mở ca (vào lớp) để bắt đầu hoạt động hôm nay.</div></div>`}${today}${care}${notebook(cl.notebook,cl.care)}${log}`;
  }
  return head('Kế hoạch lớp','')+`<div class="sheet-body classroom-v4"><div class="cp">${date}${months}${body}</div></div>`;
}
