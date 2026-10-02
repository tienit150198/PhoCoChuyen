/** Server-graded courses and the TT99 desk. Drafts are UI-only and never grant progress. */
import {icon,escapeHTML as esc} from '../icons.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const vnd=n=>n==null?'—':`${fmt(n)} đ`;
const attr=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(String(v))}"`).join('');
const btn=(label,action,data={},tone='',disabled=false)=>`<button type="button" class="btn ${tone}" data-action="${action}"${attr(data)}${disabled?' disabled':''}>${label}</button>`;
const state=env=>env.ui.accounting??={tab:'learn',course:'basic',companyTab:'documents',detailTab:'assets',reportTab:'B01',drafts:{},messages:{}};
const safeURL=url=>/^https:\/\//i.test(String(url||''))?esc(url):'#';
const source=r=>`<a href="${safeURL(r.url)}" target="_blank" rel="noopener noreferrer">${esc(r.label||'Nguồn chính thức')}${icon('arrow',12)}</a>${r.locator?`<small>${esc(r.locator)}</small>`:''}`;
const sources=rows=>rows?.length?`<details class="as-sources"><summary>Căn cứ và nguồn tra cứu</summary><ul>${rows.map(r=>`<li>${source(r)}</li>`).join('')}</ul></details>`:'';
const status=(text,tone='')=>`<span class="as-stamp ${tone}">${esc(text)}</span>`;
const progress=(done,total,label)=>`<div class="as-progress" role="progressbar" aria-label="${esc(label)}" aria-valuemin="0" aria-valuemax="${total}" aria-valuenow="${done}"><i style="width:${total?Math.min(100,100*done/total):0}%"></i></div>`;
const flow=(active='')=>`<ol class="as-flow" aria-label="Chu trình kế toán">${[['source','Chứng từ'],['entry','Bút toán'],['books','Sổ sách'],['reports','Báo cáo']].map(([id,label],i)=>`<li${id===active?' aria-current="step"':''}><span>${i+1}</span>${label}</li>`).join('')}</ol>`;
const empty=text=>`<p class="as-empty">${esc(text)}</p>`;

function tabs(list,current,action,label){return `<nav class="as-tabs" aria-label="${esc(label)}">${list.map(([id,title])=>btn(esc(title),action,{tab:id},current===id?'as-tab on':'as-tab')).join('')}</nav>`;}
function table(title,rows,columns,{total=false}={}){
  if(!rows?.length)return `<section class="as-book"><h3>${esc(title)}</h3>${empty('Chưa có số liệu ở mục này. Ghi hồ sơ đúng để sổ cập nhật.')}</section>`;
  const cell=(r,c)=>c.render?c.render(r):c.type==='money'?vnd(r[c.key]):esc(String(r[c.key]??'—'));
  const footer=total?`<tfoot><tr>${columns.map((c,i)=>`<td${c.type==='money'?' class="as-number"':''}>${i===0?'Tổng cộng':c.type==='money'?vnd(rows.reduce((n,r)=>n+Number(r[c.key]||0),0)):''}</td>`).join('')}</tr></tfoot>`:'';
  return `<section class="as-book"><div class="as-book-title"><h3>${esc(title)}</h3><small>${rows.length} dòng · VND</small></div><div class="as-table-scroll" tabindex="0" role="region" aria-label="${esc(title)}"><table class="as-table"><thead><tr>${columns.map(c=>`<th scope="col"${c.type==='money'?' class="as-number"':''}>${esc(c.label)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${columns.map(c=>`<td${c.type==='money'?' class="as-number"':''}>${cell(r,c)}</td>`).join('')}</tr>`).join('')}</tbody>${footer}</table></div></section>`;
}

const optionName=(rows,id)=>rows?.find(r=>r.id===id)?.label??id;
export function answerText(q,answer=q.answer){
  if(answer==null)return 'Chưa có câu trả lời';
  if(q.kind==='entry')return answer.map(x=>`Nợ ${esc(x.debit)} / Có ${esc(x.credit)} · ${vnd(x.amount)}`).join('<br>');
  if(q.kind==='choice')return esc(optionName(q.options,answer));
  if(q.kind==='multi')return answer.map(id=>esc(optionName(q.options,id))).join(' · ');
  if(q.kind==='number')return `${fmt(answer)} ${esc(q.unit||'đ')}`;
  if(q.kind==='order')return answer.map((id,i)=>`${i+1}. ${esc(optionName(q.items,id))}`).join('<br>');
  return Object.entries(answer).map(([id,value])=>{const f=q.kind==='match'?q.left?.find(r=>r.id===id):q.fields?.find(r=>r.id===id);return `${esc(f?.label||id)}: ${q.kind==='match'?esc(optionName(q.right,value)):f?.options?esc(optionName(f.options,value)):vnd(value)}`;}).join('<br>');
}

function questionKey(mode,id,context=''){return `${mode}|${context}|${id}`;}
function draftFor(u,key,q){
  return u.drafts[key]??={values:{},order:[],entries:q.kind==='entry'?[{debit:'',credit:'',amount:''}]:[]};
}
const numeric=(name,value,label)=>`<label class="as-field"><span>${esc(label)}</span><input class="input" name="${esc(name)}" type="number" inputmode="numeric" step="1" value="${esc(value??'')}" required></label>`;
function select(name,rows,value,label){return `<label class="as-field"><span>${esc(label)}</span><select name="${esc(name)}" required><option value="">Chọn…</option>${rows.map(r=>`<option value="${esc(r.id)}"${r.id===value?' selected':''}>${esc(r.label||(r.name?`${r.id} — ${r.name}`:r.id))}</option>`).join('')}</select></label>`;}

function questionInput(q,d,key){
  const values=d.values||{};
  switch(q.kind){
    case'choice':case'multi':return `<div class="as-options">${q.options.map((o,i)=>`<label class="as-option"><input type="${q.kind==='choice'?'radio':'checkbox'}" name="ans" value="${esc(o.id)}"${(q.kind==='choice'?values.ans===o.id:(values.ans||[]).includes(o.id))?' checked':''}${q.kind==='choice'?' required':''}><span class="as-option-letter">${String.fromCharCode(65+i)}</span><span>${esc(o.label)}</span></label>`).join('')}</div>`;
    case'number':return numeric('ans',values.ans,`Đáp số (${q.unit||'đ'})`);
    case'fields':return `<div class="as-fields">${q.fields.map(f=>f.options?select('f:'+f.id,f.options,values['f:'+f.id],f.label):numeric('f:'+f.id,values['f:'+f.id],f.label+' (VND)')).join('')}</div>`;
    case'match':return `<div class="as-fields">${q.left.map(l=>select('m:'+l.id,q.right,values['m:'+l.id],l.label)).join('')}</div>`;
    case'order':{
      const picked=d.order.filter(id=>q.items.some(x=>x.id===id));
      return `<p class="as-hint">Chọn đủ các mục theo thứ tự. Chạm dấu × để bỏ một mục.</p><ol class="as-order">${picked.map((id,i)=>`<li><b>${i+1}</b><span>${esc(optionName(q.items,id))}</span>${btn('× Bỏ','asOrderRemove',{key,index:i},'ghost small')}</li>`).join('')||'<li class="as-empty">Chưa chọn mục nào.</li>'}</ol><div class="as-actions">${q.items.filter(x=>!picked.includes(x.id)).map(x=>btn(esc(x.label),'asOrderAdd',{key,item:x.id},'ghost small')).join('')}</div>`;
    }
    case'entry':return `<p class="as-hint">Mỗi dòng là một cặp Nợ/Có cùng số tiền. Có thể thêm tối đa 8 dòng; nhập VND nguyên.</p><div class="as-entries">${d.entries.map((r,i)=>`<fieldset class="as-entry"><legend>Dòng ${i+1}</legend>${select('d:'+i,q.accounts||[],r.debit,'Tài khoản Nợ')}${select('c:'+i,q.accounts||[],r.credit,'Tài khoản Có')}${numeric('a:'+i,r.amount,'Số tiền (VND)')}${d.entries.length>1?btn('Bỏ dòng','asEntryRemove',{key,index:i},'ghost small'):''}</fieldset>`).join('')}</div>${btn('+ Thêm dòng','asEntryAdd',{key},'ghost small',d.entries.length>=8)}`;
    default:return empty('Loại câu hỏi này chưa được hỗ trợ.');
  }
}

export function questionView(q,{mode,context='',lesson='',ui,number=1,disabled=false}){
  const key=questionKey(mode,q.id,context),d=draftFor(ui,key,q),message=ui.messages[key];
  const title=`<div class="as-question-title"><span class="as-question-no">${q.solved?'✓':number}</span><h4>${esc(q.title)}</h4>${q.solved?status('Đã làm đúng','good'):''}</div>`;
  if(q.solved)return `<article class="as-question solved">${title}<p>${esc(q.prompt)}</p><div class="as-answer">${answerText(q)}</div>${q.explain?`<p class="as-explain">${esc(q.explain)}</p>`:''}</article>`;
  const schema={kind:q.kind,items:q.items,left:q.left,fields:q.fields};
  return `<article class="as-question">${title}<p class="as-prompt">${esc(q.prompt)}</p><form data-as-form="${mode}" data-key="${esc(key)}" data-question="${esc(q.id)}" data-lesson="${esc(lesson)}" data-kind="${esc(q.kind)}" data-question-data="${esc(JSON.stringify(schema))}"><fieldset class="as-question-controls"${disabled?' disabled':''}>${questionInput(q,d,key)}${message?`<p class="as-feedback ${message.correct===false?'bad':'good'}" role="status">${esc(message.text)}</p>`:''}<button type="submit" class="btn primary">${mode==='exam'?'Nộp câu và tiếp tục':mode==='company'?'Kiểm tra và ghi sổ':'Kiểm tra bài tập'}</button></fieldset></form></article>`;
}

function certificate(course,a,api){
  const c=course.certificate;
  if(!c)return '';
  return `<article class="as-certificate"><div class="as-seal" aria-hidden="true">${icon('award',30)}</div><div><span class="eyebrow">${esc(a.certificate_label||'CHỨNG NHẬN TRONG GAME')}</span><h3>${esc(course.name)}</h3><p>${esc(api.state?.name||'Bạn')} · ${c.score}/100 · ${esc(c.date)}</p><small>Mã ${esc(c.serial)} · Ghi nhận học tập trong Phố Có Chuyện</small><div class="as-actions">${btn('Lưu bản để in','asCertificate',{course:course.id},'ghost small')}</div></div></article>`;
}

function examGate(c,a){return `<section class="as-exam-gate"><div><h3>${c.certificate?'Thi lại để ôn tập':'Thi hoàn thành khóa'}</h3><p>${c.exam_count} câu · đạt từ ${c.pass_mark}/100 · miễn phí thi lại</p>${c.attempts?`<small>Đã thi ${c.attempts} lần · cao nhất ${c.best}/100</small>`:''}</div>${btn('Bắt đầu thi','asExamStart',{course:c.id},'primary',!c.can_exam)}${!c.can_exam?`<p class="as-lock">${esc(c.exam_reason)}</p>`:''}${c.id==='vn_business'?'<p class="as-hint">Cần chứng nhận Kế toán cơ bản và hoàn thành 60 bài của khóa này. Thi đạt tăng lương kế toán doanh nghiệp lên ×3, không cộng dồn khi thi lại.</p>':''}</section>`;}

function catalog(a,u,api){
  const c=a.courses.find(x=>x.id===u.course)||a.courses[0];
  if(!c)return empty('Chương trình học đang được tải.');
  const selected=a.lesson?.id?.startsWith(c.id+'_')?a.lesson:null;
  const first=c.chapters.flatMap(ch=>ch.lessons).find(l=>!l.done)||c.chapters[0]?.lessons[0];
  const index=`<aside class="as-index" aria-label="Mục lục khóa học"><div class="as-course-title"><span class="eyebrow">${c.id==='basic'?'NỀN TẢNG':'DOANH NGHIỆP · TT99'}</span><h3>${esc(c.name)}</h3><p>${c.done}/${c.total} bài hoàn thành</p>${progress(c.done,c.total,c.name)}</div>${c.chapters.map(ch=>`<details class="as-chapter" data-fold="${esc(ch.id)}"${ch.lessons.some(l=>l.id===selected?.id)||!selected&&ch===c.chapters[0]?' open':''}><summary>${esc(ch.title)}<small>${ch.lessons.filter(l=>l.done).length}/${ch.lessons.length}</small></summary><ol>${ch.lessons.map(l=>`<li><button type="button" class="as-lesson-link${l.id===selected?.id?' on':''}" data-action="asLesson" data-lesson="${esc(l.id)}"${l.id===selected?.id?' aria-current="page"':''}><span aria-hidden="true">${l.done?'✓':l.read?'◒':'○'}</span><span>${esc(l.title)}<small>${l.solved}/${l.questions} bài tập${l.done?' · hoàn thành':''}</small></span></button></li>`).join('')}</ol></details>`).join('')}</aside>`;
  const intro=`<article class="as-reading"><span class="eyebrow">BẮT ĐẦU TỪ BẢN CHẤT GIAO DỊCH</span><h2>${esc(c.name)}</h2><p>${esc(c.description)}</p><div class="as-actions">${first?btn(c.done?'Mở lại bài học':'Tiếp tục học','asLesson',{lesson:first.id},'primary'):''}</div><p class="as-hint">Đọc bài và ví dụ, rồi làm đúng ba bài tập để hoàn thành từng bài. Tiến độ được giữ trong bản lưu.</p>${flow('source')}${certificate(c,a,api)}${examGate(c,a)}</article>`;
  const reading=selected?`<article class="as-reading"><div class="as-reading-head"><span class="eyebrow">${esc(c.name)}</span>${status(selected.done?'Bài đã hoàn thành':'Đang học',selected.done?'good':'')}<h2>${esc(selected.title)}</h2></div><section class="as-objectives"><h3>Sau bài này</h3><ul>${selected.objectives.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></section><div class="as-lesson-body">${selected.body.map(p=>`<p>${esc(p)}</p>`).join('')}</div><section class="as-example"><span class="eyebrow">THEO DÕI CÁCH LÀM</span><h3>${esc(selected.example.title)}</h3><ol>${selected.example.lines.map(p=>`<li>${esc(p)}</li>`).join('')}</ol></section>${sources(selected.references)}<section class="as-practice"><div class="as-section-title"><h3>Tự làm bài tập</h3><small>${selected.questions.filter(q=>q.solved).length}/${selected.questions.length} đã đúng</small></div>${selected.questions.map((q,i)=>questionView(q,{mode:'practice',context:selected.id,lesson:selected.id,ui:u,number:i+1})).join('')}</section>${selected.done?`<div class="as-next">${status('Hoàn thành bài','good')}${first&&!first.done?btn('Bài tiếp theo →','asLesson',{lesson:first.id},'primary'):btn('Xem điều kiện thi →','asTab',{tab:'exam'},'primary')}</div>`:''}</article>`:intro;
  return tabs(a.courses.map(x=>[x.id,x.name]),c.id,'asCourse','Chọn khóa học')+`<div class="as-study-layout">${index}${reading}</div>`;
}

function examPage(a,u,api){
  const exam=a.active_exam;
  if(exam)return `<section class="as-reading as-exam"><div class="as-section-title"><span class="eyebrow">BÀI THI · ${esc(exam.name)}</span><b>Câu ${exam.at+1}/${exam.total}</b></div>${progress(exam.at,exam.total,'Tiến độ thi')}<p class="as-hint">Câu đã nộp được giữ lại. Đáp án và điểm chỉ xuất hiện sau khi nộp đủ bài.</p>${questionView(exam.question,{mode:'exam',context:exam.course,ui:u,number:exam.at+1})}<div class="as-actions">${btn('Hủy bài thi đang làm','asExamCancel',{},'ghost small')}</div></section>`;
  const c=a.courses.find(x=>x.id===u.course)||a.courses[0],review=a.review?.[c.id];
  return tabs(a.courses.map(x=>[x.id,x.name]),c.id,'asCourse','Khóa thi')+certificate(c,a,api)+examGate(c,a)+(review?`<section class="as-review"><div class="as-section-title"><h3>Kết quả gần nhất: ${review.score}/100</h3>${status(review.passed?'Đạt':'Cần ôn thêm',review.passed?'good':'warn')}</div><p class="as-hint">${review.passed?'Bạn có thể xem lại cách làm.':'Mở lại bài học có liên quan rồi thi lại miễn phí.'}</p><ol>${review.questions.map((r,i)=>`<li class="${r.correct?'good':'bad'}"><details data-fold="review-${esc(r.question.id)}"><summary><span>${r.correct?'✓':'×'} ${i+1}. ${esc(r.question.prompt)}</span></summary><div class="as-answer"><b>Bạn đã nộp:</b><br>${answerText(r.question)}</div><p class="as-explain">${esc(r.question.explain||'')}</p>${btn('Ôn bài liên quan','asLesson',{lesson:r.question.lesson_id},'ghost small')}</details></li>`).join('')}</ol></section>`:'');
}

function journal(rows,title){
  return table(title,rows.flatMap(t=>(t.entries||[]).map((r,i)=>({...r,id:t.id,title:t.title,period:t.period,line:i+1}))),[
    {key:'id',label:'Hồ sơ',render:r=>`${r.period?`<small>Tháng ${r.period}</small>`:''}<b>${esc(r.id)}</b><small>${esc(r.title)}</small>`},
    {key:'debit',label:'Nợ'},{key:'credit',label:'Có'},{key:'amount',label:'Số tiền',type:'money'},
  ]);
}
function companyDetails(book,u){
  const dt=book.details||{},groups=[['assets','TSCĐ'],['insurance','Phân bổ bảo hiểm'],['services','Dịch vụ'],['deposits','Tiền gửi kỳ hạn'],['foreign_currency','Ngoại tệ'],['parties','Công nợ'],['production','Giá thành']];
  const columns={
    assets:[['id','Mã'],['name','Tài sản'],['cost','Nguyên giá','money'],['life','Số tháng'],['accumulated','Hao mòn','money'],['net','Còn lại','money']],
    insurance:[['id','Hợp đồng'],['start','Từ tháng'],['periods','Số kỳ'],['cost','Giá trị','money'],['monthly','Mỗi kỳ','money'],['allocated','Đã phân bổ','money'],['remaining','Còn lại','money']],
    services:[['id','Hợp đồng'],['start','Từ tháng'],['periods','Số kỳ'],['total','Giá trị','money'],['recognized','Đã ghi doanh thu','money'],['remaining','Chờ phân bổ','money']],
    deposits:[['id','Hợp đồng'],['start','Từ tháng'],['maturity','Đáo hạn tháng'],['principal','Gốc','money'],['accrued','Lãi dự thu','money'],['balance','Giá trị sổ','money'],['rate','Lãi suất hồ sơ']],
    foreign_currency:[['id','Hồ sơ'],['party','Đối tượng'],['currency','Loại tiền'],['original','Nguyên tệ'],['trade_rate','Tỷ giá ban đầu'],['rate','Tỷ giá sổ'],['vnd','Giá trị VND','money']],
    parties:[['account','TK'],['party','Đối tượng'],['debit','Dư Nợ','money'],['credit','Dư Có','money']],
  };
  const tab=groups.some(([id])=>id===u.detailTab)?u.detailTab:'assets';
  const production=Object.entries(dt.production||{}).map(([key,value])=>({label:({materials:'Nguyên liệu trực tiếp',labor:'Nhân công trực tiếp',overhead:'Sản xuất chung',finished:'Sản phẩm hoàn thành',work_in_progress:'Dở dang cuối kỳ'})[key]||key,value}));
  return tabs(groups,tab,'asDetailTab','Sổ chi tiết')+(tab==='production'?table('Bảng tập hợp giá thành',production,[{key:'label',label:'Khoản mục'},{key:'value',label:'Giá trị',type:'money'}]):table(groups.find(([id])=>id===tab)[1],dt[tab]||[],columns[tab].map(([key,label,type])=>({key,label,type}))));
}
function financialReports(book,u){
  const reports=book.statements||{},tab=['B01','B02','B03','B09'].includes(u.reportTab)?u.reportTab:'B01',report=reports[tab];
  if(!report)return empty('Báo cáo đang được chuẩn bị từ sổ đã ghi.');
  const columns=[{key:'code',label:'Mã'},{key:'label',label:'Chỉ tiêu'}];
  if(tab==='B09')columns.push({key:'text',label:'Thuyết minh'});
  else columns.push({key:'value',label:'Kỳ này (VND)',type:'money'},{key:'previous',label:report.comparison||'Kỳ trước (VND)',type:'money'});
  columns.push({key:'page',label:'Trang nguồn',render:r=>esc(typeof r.page==='object'?`${r.page.part||''}/${r.page.page||''}`:String(r.page??''))});
  return tabs([['B01','B01 · Tình hình tài chính'],['B02','B02 · Kết quả'],['B03','B03 · Dòng tiền'],['B09','B09 · Thuyết minh']],tab,'asReportTab','Bốn báo cáo tài chính')+`<p class="as-hint">${esc(reports.status||'')} · Báo cáo học tập theo kỳ tháng, gồm cả các chỉ tiêu không phát sinh.</p>`+table(report.title,report.rows,columns)+sources([{label:'Mẫu TT99 và Phụ lục IV chính thức',url:reports.source_url}]);
}

function companyPage(a,u){
  const book=a.company;
  if(!book)return `<article class="as-reading"><span class="eyebrow">VĂN PHÒNG THỰC HÀNH</span><h2>Công ty CP Mây Tre Xanh</h2><p>Đi từ chứng từ đến bộ sổ và bốn báo cáo trong 12 kỳ của năm 2026. Hồ sơ dùng VND; lương trong trò chơi dùng xu.</p>${flow('source')}${btn('Nhận việc thực hành','asCompanyJoin',{},'primary',!a.company_unlocked)}${!a.company_unlocked?'<p class="as-lock">Thi đạt chứng nhận Kế toán doanh nghiệp Việt Nam để nhận việc.</p>':''}<p class="as-hint">Lương kế toán doanh nghiệp áp dụng ×3 sau khi đạt chứng nhận, không cộng dồn sau thi lại. Nghề hiện tại của bạn vẫn được giữ.</p>${sources([a.reference])}</article>`;
  const task=book.task,tab=u.companyTab||'documents',read=!!task&&!task.docs?.some(d=>d.closed);
  const workspace=task?`<div class="as-section-title"><div><span class="eyebrow">VIỆC ${book.at+1}/${book.total}</span><h3>${esc(task.title)}</h3></div>${status(read?'Đã mở nguồn':'Đọc nguồn trước',read?'good':'warn')}</div>${flow(read?'entry':'source')}<section class="as-documents">${read?(task.docs||[]).map(d=>`<article class="as-document"><small>${esc(d.id)}</small><h4>${esc(d.title)}</h4>${(d.lines||[]).map(x=>`<p>${esc(x)}</p>`).join('')}</article>`).join(''):`${btn('Mở chứng từ gốc','asInspect',{task:task.id},'primary')}<ul>${(task.docs||[]).map(d=>`<li>${esc(d.title)}</li>`).join('')}</ul>`}</section>${read?questionView(task,{mode:'company',context:book.period,ui:u,number:book.at+1}):'<p class="as-hint">Mở và đọc hồ sơ trước khi nhập bút toán. Sổ sách cập nhật sau khi câu trả lời được chấm đúng.</p>'}${sources(task.references)}`:`<article class="as-reading"><h3>Đã hoàn thành bộ sổ tháng ${book.period}</h3><p>Chứng từ, kết chuyển và bốn báo cáo đã được chấm đúng. ${book.mistakes?`Có ${book.mistakes} lần thử lại.`:''}</p>${btn(book.paid?'Đã nhận lương kỳ này':'Nhận lương ca thực hành','asCompanyFinish',{},'primary',book.paid)}${book.paid&&book.period<12?btn('Mở tháng tiếp theo →','asCompanyNext',{},'ghost'):''}${book.period===12&&book.paid?status('Hoàn thành 12 kỳ năm 2026','good'):''}</article>`;
  let body=workspace;
  if(tab==='journal')body=journal(book.journal||[],'Nhật ký kỳ hiện tại')+`<details class="as-history" data-fold="previous-journal"><summary>Nhật ký các kỳ trước · ${(book.previous_journal||[]).length} hồ sơ</summary>${journal(book.previous_journal||[],'Nhật ký các kỳ trước')}</details>`;
  if(tab==='ledger')body=table('Bảng cân đối số phát sinh',book.ledger,[{key:'account',label:'TK'},{key:'name',label:'Tên tài khoản'},...['opening_debit','opening_credit','movement_debit','movement_credit','debit','credit'].map((key,i)=>({key,label:['Đầu kỳ Nợ','Đầu kỳ Có','Phát sinh Nợ','Phát sinh Có','Cuối kỳ Nợ','Cuối kỳ Có'][i],type:'money'}))],{total:true});
  if(tab==='details')body=companyDetails(book,u);
  if(tab==='reports')body=financialReports(book,u);
  return `<div class="as-company-head"><div><span class="eyebrow">DOANH NGHIỆP THỰC HÀNH · VND</span><h2>${esc(book.name)}</h2><p>Tháng ${book.period}/2026 · ${book.at}/${book.total} việc đã xong</p></div>${status(book.paid?'Đã nhận lương':book.done?'Đã khóa sổ':'Đang ghi sổ',book.done?'good':'')}</div>${progress(book.at,book.total,'Tiến độ kỳ thực hành')}${tabs([['documents','Chứng từ & việc đang làm'],['journal','Nhật ký'],['ledger','Cân đối phát sinh'],['details','Sổ chi tiết'],['reports','Bốn báo cáo']],tab,'asCompanyTab','Hồ sơ doanh nghiệp')}<div class="as-company-body">${body}</div><details class="as-history" data-fold="company-history"><summary>Danh sách hồ sơ · ${book.at}/${book.total} đã xong</summary><ol>${book.schedule.map(t=>`<li${t.current?' aria-current="step"':''}><span>${t.done?'✓':t.current?'→':'○'}</span>${esc(t.title)}</li>`).join('')}</ol></details><p class="as-policy">${esc(book.policy)}</p>${sources(book.references)}`;
}

export function accountingSchoolView(env){
  const a=env.api.state?.accounting_school,u=state(env);
  const head=`<header class="sheet-head"><div class="grow"><span class="eyebrow">SỔ HỌC & THỰC HÀNH</span><h2>Học kế toán</h2><p>Từ hiểu nghiệp vụ đến tự lập bộ sổ</p></div><button type="button" class="icon-btn" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  if(!a)return head+`<div class="sheet-body">${empty('Chương trình đang được tải. Mở lại sau một chút để tiếp tục.')}</div>`;
  return head+`<div class="sheet-body as-school">${tabs([['learn','Bài học'],['exam',a.active_exam?'Bài thi đang làm':'Thi & chứng nhận'],['company','Doanh nghiệp thực hành']],u.tab,'asTab','Học kế toán')}<p class="as-salary">${icon('briefcase',16)} Lương kế toán doanh nghiệp: <b>×${a.salary_multiplier}</b>${a.effective_salary?` · hợp đồng áp dụng ${fmt(a.effective_salary)} xu`:''}${a.salary_multiplier===3?' · thi lại không cộng dồn':''}</p>${u.tab==='company'?companyPage(a,u):u.tab==='exam'?examPage(a,u,env.api):catalog(a,u,env.api)}</div>`;
}

export const view=accountingSchoolView;
export const action=accountingSchoolAction;
export const submit=accountingSchoolSubmit;
export const input=accountingSchoolInput;

function capture(form,u){
  const d=u.drafts[form.dataset.key];if(!d)return;
  const data=new FormData(form);
  if(form.dataset.kind==='entry')d.entries=d.entries.map((r,i)=>({debit:String(data.get('d:'+i)||''),credit:String(data.get('c:'+i)||''),amount:String(data.get('a:'+i)||'')}));
  else{d.values={};for(const [key,value] of data)d.values[key]=value;if(form.dataset.kind==='multi')d.values.ans=data.getAll('ans');}
}
export function accountingSchoolInput(target,env){
  const form=target.closest?.('form[data-as-form]');if(!form)return false;
  capture(form,state(env));return true;
}
const integer=value=>value!==''&&value!=null&&Number.isSafeInteger(Number(value))?Number(value):null;
export function readAccountingAnswer(form,u){
  capture(form,u);const q=JSON.parse(form.dataset.questionData),d=u.drafts[form.dataset.key],f=new FormData(form);
  switch(q.kind){
    case'choice':return f.get('ans');
    case'multi':{const values=f.getAll('ans');return values.length?values:null;}
    case'number':return integer(f.get('ans'));
    case'order':return d.order.length===q.items.length&&new Set(d.order).size===q.items.length&&d.order.every(id=>q.items.some(x=>x.id===id))?[...d.order]:null;
    case'entry':{const rows=d.entries.map(r=>({...r,amount:integer(r.amount)}));return rows.every(r=>r.debit&&r.credit&&r.debit!==r.credit&&r.amount>0&&r.amount<=1e9)?rows:null;}
    case'match':case'fields':{
      const rows=q.kind==='match'?q.left:q.fields,prefix=q.kind==='match'?'m:':'f:',answer={};
      for(const row of rows){const raw=f.get(prefix+row.id),value=q.kind==='fields'&&!row.options?integer(raw):raw;if(value===null||value==='')return null;answer[row.id]=value;}
      return answer;
    }
    default:return null;
  }
}

export async function accountingSchoolSubmit(form,env){
  const mode=form.dataset.asForm;if(!mode)return false;
  const u=state(env),answer=readAccountingAnswer(form,u),key=form.dataset.key;
  if(answer===null){u.messages[key]={correct:false,text:'Hoàn thành đủ câu trả lời; nhập số nguyên và kiểm tra các tài khoản trước khi nộp.'};env.renderSheet();return true;}
  const command=mode==='exam'?'as_exam_answer':mode==='company'?'as_company_answer':'as_answer';
  const payload=mode==='company'?{task:form.dataset.question,answer}:{question:form.dataset.question,answer,...(mode==='practice'?{lesson:form.dataset.lesson}:{})};
  const r=await env.cmd(command,payload,{quiet:true});
  if(r){u.messages[key]={correct:r.correct,text:r.message};if(r.correct||mode==='exam')delete u.drafts[key];if(r.exam){u.course=r.exam.course;u.tab='exam';}env.toast(r.message,r.correct===false);env.renderSheet();}
  return true;
}

function saveCertificate(course,a,api){
  const c=course.certificate;if(!c)return;
  const html=`<!doctype html><html lang="vi"><meta charset="utf-8"><title>Chứng nhận ${esc(course.name)}</title><style>body{font:18px/1.6 Georgia,serif;color:#392e26;margin:64px;max-width:860px}article{border:1px solid #968572;padding:48px;text-align:center}h1{font-size:32px}small{display:block}button{padding:12px;margin:24px}@media print{button{display:none}body{margin:0}}</style><article><small>PHỐ CÓ CHUYỆN · CHỨNG NHẬN TRONG GAME</small><h1>${esc(course.name)}</h1><p>${esc(api.state?.name||'Người chơi')} đã hoàn thành khóa học và thi đạt ${c.score}/100.</p><p>Ngày ${esc(c.date)} · Mã ${esc(c.serial)}</p><small>Ghi nhận học tập trong trò chơi, không thay văn bằng hay chứng chỉ hành nghề.</small></article><button onclick="window.print()">In bản này</button></html>`;
  const blob=new Blob([html],{type:'text/html;charset=utf-8'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=`chung-nhan-ke-toan-${course.id}.html`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export async function accountingSchoolAction(action,data,el,env){
  if(!action.startsWith('as'))return false;
  const u=state(env),a=env.api.state.accounting_school;
  if(action==='asTab')u.tab=data.tab;
  else if(action==='asCourse')u.course=data.tab;
  else if(action==='asCompanyTab')u.companyTab=data.tab;
  else if(action==='asDetailTab')u.detailTab=data.tab;
  else if(action==='asReportTab')u.reportTab=data.tab;
  else if(action==='asLesson'){if(await env.cmd('as_open',{lesson:data.lesson},{quiet:true})){u.course=a.courses.find(c=>c.chapters.some(ch=>ch.lessons.some(l=>l.id===data.lesson)))?.id||u.course;u.tab='learn';}}
  else if(action==='asOrderAdd'){const d=u.drafts[data.key];if(d&&!d.order.includes(data.item))d.order.push(data.item);}
  else if(action==='asOrderRemove')u.drafts[data.key]?.order.splice(Number(data.index),1);
  else if(action==='asEntryAdd'){const d=u.drafts[data.key];if(d&&d.entries.length<8)d.entries.push({debit:'',credit:'',amount:''});}
  else if(action==='asEntryRemove'){const d=u.drafts[data.key];if(d&&d.entries.length>1)d.entries.splice(Number(data.index),1);}
  else if(action==='asExamStart'){if(await env.cmd('as_exam_start',{course:data.course})){u.drafts=Object.fromEntries(Object.entries(u.drafts).filter(([key])=>!key.startsWith('exam|')));u.messages={};u.course=data.course;u.tab='exam';}}
  else if(action==='asExamCancel'){if(await env.confirmAction('Hủy bài thi đang làm?','Các câu đã nộp trong lần thi này sẽ bị bỏ. Bài học và chứng nhận đã có vẫn được giữ.','Hủy bài thi'))await env.cmd('as_exam_cancel',{confirm:true});}
  else if(action==='asCertificate')saveCertificate(a.courses.find(c=>c.id===data.course),a,env.api);
  else if(action==='asCompanyJoin'){if(await env.cmd('as_company_join')){u.tab='company';u.companyTab='documents';}}
  else if(action==='asInspect')await env.cmd('as_company_inspect',{task:data.task},{quiet:true});
  else if(action==='asCompanyFinish')await env.cmd('as_company_finish');
  else if(action==='asCompanyNext'){if(await env.cmd('as_company_next'))u.companyTab='documents';}
  else return false;
  env.renderSheet();return true;
}
