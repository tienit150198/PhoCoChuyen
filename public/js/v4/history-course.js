/** 📜 Học lịch sử Việt Nam (game/history_course.py): short lessons in time order, two questions each, a final exam
 * and a certificate. The server grades every answer and keeps the keys; this page only shows its view
 * (result.history_view of each vs_* command). Looks borrow the Học kế toán sheet (accounting-school.css). */
import {icon,escapeHTML as esc} from '../icons.js';

const attr=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(String(v))}"`).join('');
const btn=(label,action,data={},tone='',disabled=false)=>`<button type="button" class="btn ${tone}" data-action="${action}"${attr(data)}${disabled?' disabled':''}>${label}</button>`;
const state=env=>env.ui.history??={tab:'learn',lesson:null,hint:{},msg:{}};
const progress=(done,total,label)=>`<div class="as-progress" role="progressbar" aria-label="${esc(label)}" aria-valuemin="0" aria-valuemax="${total}" aria-valuenow="${done}"><i style="width:${total?Math.min(100,100*done/total):0}%"></i></div>`;
const stamp=(text,tone='')=>`<span class="as-stamp ${tone}">${esc(text)}</span>`;
const LETTER='ABC';

async function run(env,command,payload={}){
  const u=state(env),r=await env.cmd(command,{...payload,view:{lesson:u.lesson}},{quiet:true});
  if(r?.history_view)u.data=r.history_view;
  return r;
}
export async function historyCourseOpen(env){
  const u=state(env);
  return !!await run(env,'vs_view')&&!!u.data;
}

function certCard(a,api){
  const c=a.cert;if(!c)return '';
  return `<article class="as-certificate hc-cert"><div class="as-seal" aria-hidden="true">📜</div><div><span class="eyebrow">CHỨNG NHẬN TRONG PHỐ CÓ CHUYỆN</span><h3>${esc(a.name)}</h3><p>${esc(api.state?.name||'Bạn')} · ${c.score}/100 · ${esc(c.date)}</p><small>Mã ${esc(c.serial)}${c.gift?` · học bổng ${c.gift} xu`:''}</small><div class="as-actions">${btn('Lưu bản để in','vsCertificate',{},'ghost small')}</div></div></article>`;
}

function indexView(a,api){
  const next=a.lessons.find(l=>!l.done);
  const list=`<ol class="hc-list">${a.lessons.map((l,i)=>`<li><button type="button" class="hc-lesson${l.done?' done':''}" data-action="vsLesson" data-lesson="${esc(l.id)}"><span class="hc-emoji" aria-hidden="true">${l.emoji}</span><span class="hc-name"><small>Bài ${i+1} · ${esc(l.era)}</small><b>${esc(l.title)}</b></span><span class="hc-mark">${l.done?'✓':`${l.solved}/${l.questions}`}</span></button></li>`).join('')}</ol>`;
  return `<section class="hc-intro"><p>Mười hai bài ngắn từ thời Hùng Vương tới ngày nay. Đọc bài rồi trả lời hai câu hỏi; trả lời sai cứ thử lại, bài sẽ tô vàng câu cần đọc lại.</p>${progress(a.done,a.total,'Tiến độ học lịch sử')}<p class="as-hint">${a.done}/${a.total} bài đã xong${a.cert?' · đã có chứng nhận':''}</p>${next?btn(a.done?'Học tiếp →':'Bắt đầu học →','vsLesson',{lesson:next.id},'primary'):btn('Thi lấy chứng nhận →','vsTab',{tab:'exam'},'primary')}</section>${certCard(a,api)}${list}`;
}

function optionButtons(q,action,data,picked){
  return `<div class="hc-options">${q.options.map((o,i)=>`<button type="button" class="hc-option${picked===o.id?' picked':''}" data-action="${action}"${attr({...data,option:o.id})}><span class="as-option-letter">${LETTER[i]}</span><span>${esc(o.label)}</span></button>`).join('')}</div>`;
}

function practice(q,i,lid,u){
  const msg=u.msg[q.id];
  if(q.solved){const right=q.options.find(o=>o.id===q.answer);return `<article class="as-question solved"><div class="as-question-title"><span class="as-question-no">✓</span><h4>${esc(q.text)}</h4></div><div class="as-answer">${esc(right?.label||'')}</div><p class="as-explain">${esc(q.why||'')}</p></article>`;}
  return `<article class="as-question"><div class="as-question-title"><span class="as-question-no">${i+1}</span><h4>${esc(q.text)}</h4></div>${optionButtons(q,'vsPick',{lesson:lid,question:q.id})}${msg?`<p class="as-feedback bad" role="status">${esc(msg)}</p>`:''}</article>`;
}

function lessonView(a,u){
  const l=a.lesson;if(!l)return `<p class="as-empty">Đang mở bài học…</p>`;
  const i=a.lessons.findIndex(x=>x.id===l.id),next=a.lessons.slice(i+1).find(x=>!x.done)||a.lessons.find(x=>!x.done&&x.id!==l.id);
  const hint=u.hint[l.id];
  return `<article class="as-reading hc-reading"><div class="as-reading-head"><span class="eyebrow">BÀI ${i+1}/${a.total} · ${esc(l.era)}</span>${stamp(l.done?'Đã xong':'Đang học',l.done?'good':'')}<h2><span aria-hidden="true">${l.emoji}</span> ${esc(l.title)}</h2></div><div class="as-lesson-body">${l.body.map((p,k)=>`<p${k===hint?' class="hc-hint"':''}>${esc(p)}</p>`).join('')}</div><section class="as-practice"><div class="as-section-title"><h3>Trả lời nhanh</h3><small>${l.questions.filter(q=>q.solved).length}/${l.questions.length} câu đúng</small></div>${l.questions.map((q,k)=>practice(q,k,l.id,u)).join('')}</section><div class="as-next">${btn('← Mục lục','vsIndex',{},'ghost small hc-back')}${l.done?(next?btn('Bài tiếp theo →','vsLesson',{lesson:next.id},'primary'):btn('Thi lấy chứng nhận →','vsTab',{tab:'exam'},'primary')):''}</div></article>`;
}

function examView(a,api){
  if(a.active){const k=a.active,q=k.question;return `<section class="as-reading hc-exam"><span class="eyebrow">BÀI THI · CÂU ${k.at+1}/${k.total}</span>${progress(k.at,k.total,'Tiến độ bài thi')}<article class="as-question"><div class="as-question-title"><span class="as-question-no">${k.at+1}</span><h4>${esc(q.text)}</h4></div>${optionButtons(q,'vsExamPick',{question:q.id})}</article><p class="as-hint">Chọn một đáp án là nộp câu đó. Kết quả và lời giải hiện sau câu cuối.</p>${btn('Bỏ bài thi','vsExamCancel',{},'ghost small')}</section>`;}
  const why=a.done<a.total?`Học xong cả ${a.total} bài (đúng hết câu hỏi mỗi bài) rồi mới thi nhé · còn ${a.total-a.done} bài.`:'';
  const gate=`<section class="as-exam-gate"><div><h3>${a.cert?'Thi lại để ôn tập':'Thi lấy chứng nhận'}</h3><p>${a.draw} câu, mỗi bài một câu · đúng từ ${a.pass_right} câu là đạt · thi lại miễn phí</p>${a.attempts?`<small>Đã thi ${a.attempts} lần · cao nhất ${a.best}/100</small>`:`<small>Thi đạt lần đầu: chứng nhận, danh hiệu 📜 Người kể sử và học bổng ${a.gift} xu (trong Hành trình).</small>`}</div>${btn('Bắt đầu thi','vsExamStart',{},'primary',!a.can_exam)}${why?`<p class="as-lock">${esc(why)}</p>`:''}</section>`;
  const r=a.review;
  const review=r?`<section class="hc-review"><div class="as-section-title"><h3>Bài thi gần nhất</h3>${stamp(`${r.right}/${a.draw} câu · ${r.score} điểm`,r.passed?'good':'warn')}</div><ol>${r.questions.map(q=>{const pick=q.options.find(o=>o.id===q.picked),right=q.options.find(o=>o.id===q.answer);return `<li class="${q.ok?'ok':'no'}"><b>${q.ok?'✓':'✗'} ${esc(q.text)}</b>${q.ok?'':`<small>Bạn chọn: ${esc(pick?.label||'')}</small>`}<small>Đáp án: ${esc(right?.label||'')}</small><small>${esc(q.why||'')}</small></li>`;}).join('')}</ol></section>`:'';
  return certCard(a,api)+gate+review;
}

export function historyCourseView(env){
  const u=state(env),a=u.data;
  const head=`<header class="sheet-head"><div class="grow"><span class="eyebrow">ĐỌC NGẮN · HỎI NHANH</span><h2>📜 Học lịch sử Việt Nam</h2><p>Từ thời Hùng Vương tới Đổi Mới</p></div><button type="button" class="icon-btn" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  if(!a)return head+`<div class="sheet-body"><p class="as-empty">Bài học đang được tải. Mở lại sau một chút nhé.</p></div>`;
  const tabs=`<nav class="as-tabs" aria-label="Học lịch sử">${[['learn','Bài học'],['exam',a.active?'Bài thi đang làm':'Thi & chứng nhận']].map(([id,t])=>btn(esc(t),'vsTab',{tab:id},u.tab===id?'as-tab on':'as-tab')).join('')}</nav>`;
  const body=u.tab==='exam'?examView(a,env.api):u.lesson?lessonView(a,u):indexView(a,env.api);
  return head+`<div class="sheet-body as-school hc-school">${tabs}${body}</div>`;
}

function saveCertificate(a,api){
  const c=a?.cert;if(!c)return;
  const html=`<!doctype html><html lang="vi"><meta charset="utf-8"><title>Chứng nhận ${esc(a.name)}</title><style>body{font:18px/1.6 Georgia,serif;color:#392e26;margin:64px;max-width:860px}article{border:1px solid #968572;padding:48px;text-align:center}h1{font-size:32px}small{display:block}button{padding:12px;margin:24px}@media print{button{display:none}body{margin:0}}</style><article><small>PHỐ CÓ CHUYỆN · CHỨNG NHẬN TRONG GAME</small><h1>📜 ${esc(a.name)}</h1><p>${esc(api.state?.name||'Người chơi')} đã học xong ${a.total} bài và thi đạt ${c.score}/100.</p><p>Ngày ${esc(c.date)} · Mã ${esc(c.serial)}</p><small>Ghi nhận học tập trong trò chơi, không thay văn bằng hay chứng chỉ.</small></article><button onclick="window.print()">In bản này</button></html>`;
  const blob=new Blob([html],{type:'text/html;charset=utf-8'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='chung-nhan-lich-su-viet-nam.html';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}

export async function historyCourseAction(action,data,el,env){
  if(!/^vs[A-Z]/.test(action))return false;
  const u=state(env);
  if(action==='vsTab'){u.tab=data.tab==='exam'?'exam':'learn';if(u.tab==='learn')u.lesson=null;}
  else if(action==='vsIndex')u.lesson=null;
  else if(action==='vsLesson'){u.tab='learn';u.lesson=data.lesson;await run(env,'vs_open',{lesson:data.lesson});env.renderSheet();document.querySelector('#sheet')?.scrollTo?.(0,0);return true;}
  else if(action==='vsPick'){
    const r=await run(env,'vs_answer',{lesson:data.lesson,question:data.question,option:data.option});
    if(r){if(r.correct){delete u.msg[data.question];delete u.hint[data.lesson];env.toast(r.message,'good');}else{u.msg[data.question]=r.message;if(Number.isInteger(r.hint))u.hint[data.lesson]=r.hint;}}
  }
  else if(action==='vsExamStart')await run(env,'vs_exam_start');
  else if(action==='vsExamPick'){const r=await run(env,'vs_exam_answer',{question:data.question,option:data.option});if(r?.exam)env.toast(r.message,r.exam.passed?'good':false);}
  else if(action==='vsExamCancel'){if(await env.confirmAction('Bỏ bài thi đang làm?','Các câu đã chọn trong lần thi này sẽ bị bỏ. Bài đã học và chứng nhận vẫn giữ nguyên.','Bỏ bài thi'))await run(env,'vs_exam_cancel',{confirm:true});}
  else if(action==='vsCertificate')saveCertificate(u.data,env.api);
  else return false;
  env.renderSheet();return true;
}
export const view=historyCourseView;
export const action=historyCourseAction;
