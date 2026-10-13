/** Bình An: dossier cards, an editable timeline, invoice arithmetic and case decisions. */
import {data,act,amountBox,kitInput,kitActions} from './street_kit.js';
const current=t=>t.needs?.steps?.[t.at];
const draft=(x,key)=>(x.ui.lawDraft??={})[key]??=[];
function progress(x){
  const d=data(x),m=d.milestone||{};
  return `<section class="lw-progress card"><h4>⚖️ Hồ sơ vững vàng</h4><p>${m.qualified||0}/${m.required_cases||120} hồ sơ không phải sửa · ${m.active_days||0}/${m.required_days||30} ngày có hoàn tất hồ sơ.</p><p class="small">Cần tới ngày nghề ${m.required_day||40} để mở đủ bước soát cuối. Ca rỗng không tăng tiến trình.</p>${m.earned?'<strong>Đã đạt mốc Hồ sơ vững vàng.</strong>':''}<p class="small">Lương ngày theo hợp đồng. Thưởng hồ sơ 4–7 xu trước hệ số; giảm khi phải sửa.</p></section>`;
}
function invoices(n,x){
  return `<section class="lw-invoices card"><h4>Chứng từ gốc · xu</h4><ul>${(n.invoices||[]).map(i=>`<li><span>${x.esc(i.code)}</span><b>${x.fmt(i.amount)} xu</b></li>`).join('')}</ul><p>Đã nhận: ${x.fmt(n.credit||0)} xu · Giới hạn theo phiếu: ${x.fmt(n.cap||0)} xu</p>${n.duplicate?`<p>${x.esc(n.duplicate)}</p>`:''}</section>`;
}
function paperwork(t,x){
  const n=t.needs;
  return `<section class="lw-rule"><h4>Quy tắc của hồ sơ</h4><p>${x.esc(n.rule)}</p><small>${x.esc(n.disclaimer)}</small></section><div class="lw-docs">${(n.documents||[]).map(d=>`<article class="lw-document"><h4>${x.esc(d.title)}</h4><p>${x.esc(d.text)}</p></article>`).join('')}</div>${current(t)?.type==='amount'&&t.stage==='work'?'':invoices(n,x)}`;
}
function work(t,x){
  const s=current(t);if(!s)return '<p>Hồ sơ đã bàn giao.</p>';
  const key=t.id+':'+s.id,got=draft(x,key);
  let body='';
  if(s.type==='choice')body=s.options.map(o=>x.cmd(x.esc(o.label),'lw_submit',{task:t.id,step:s.id,value:o.id},'lw-option')).join('');
  else if(s.type==='amount')body=amountBox(x,key,0,{min:0,max:10000,label:'Khoản yêu cầu theo chứng từ',send:'Đối chiếu khoản yêu cầu',cmd:'lw_submit',payload:{task:t.id,step:s.id},field:'value'}).replace('car:amtSend','car:lawAmount').replace('data-extra=',`data-task="${x.esc(t.id)}" data-step="${x.esc(s.id)}" data-extra=`);
  else{
    const by=Object.fromEntries(s.options.map(o=>[o.id,o.label]));
    body=(s.type==='order'&&got.length?`<ol class="lw-timeline">${got.map(id=>`<li>${x.esc(by[id])}</li>`).join('')}</ol>`:'')+s.options.map(o=>act(x,x.esc(o.label),'select',{key,item:o.id},`lw-option ${got.includes(o.id)?'selected':''}`,` aria-pressed="${got.includes(o.id)}"`)).join('');
    const count=s.type==='multi'?2:3;
    body+=`<p class="small" aria-live="polite">Đã chọn ${got.length}/${count}. Chạm mục đã chọn để bỏ.</p>${act(x,s.type==='multi'?'Gắn cặp chứng cứ':'Chốt dòng thời gian','submit',{key,task:t.id,step:s.id},'primary',got.length===count?'':' disabled')}${act(x,'Xếp lại','reset',{key},'ghost')}`;
  }
  const question=s.type==='amount'?`Cộng các chứng từ gốc dưới đây, mỗi mã tính một lần. ${x.fmt(t.needs.cap)} xu là mức trần, không phải tổng chứng từ. Nếu tổng nhỏ hơn mức trần, dùng tổng đó; nếu lớn hơn, dùng mức trần. Sau đó trừ ${x.fmt(t.needs.credit)} xu đã nhận, kết quả thấp nhất là 0.`:s.question;
  return `<section class="lw-work card" aria-label="Bước hồ sơ"><p class="lw-step">Bước ${t.at+1}/${t.needs.steps.length}</p><h3>${x.esc(s.title)}</h3><p>${x.esc(question)}</p>${s.type==='amount'?invoices(t.needs,x):''}<div class="lw-controls">${body}</div>${t.last_feedback?`<p class="lw-feedback" role="status">${x.esc(t.last_feedback)}</p>`:''}</section>`;
}
export default {
  id:'lawyer',css:true,
  next(t,x){return x.esc(!t.known?'Hỏi khách để mở hồ sơ':current(t)?.title||'Hồ sơ đã bàn giao');},
  job(t,x){return `<div class="career-job lw"><header><h3>⚖️ ${x.esc(t.title)}</h3><p>${x.esc(t.opening||'')}</p></header>${!t.known?x.cmd('Hỏi khách và mở hồ sơ','ask',{task:t.id},'primary sk-ask'):`${work(t,x)}${paperwork(t,x)}`}${progress(x)}</div>`;},
  idle(x){return `<div class="career-job lw"><p>Đọc tài liệu gốc, trình bày có căn cứ. Hồ sơ mới sẽ tới theo nhịp ca.</p>${progress(x)}</div>`;},
  input:kitInput,
  actions:{...kitActions,
    async select(d,el,x){const got=draft(x,d.key),i=got.indexOf(d.item);if(i>=0)got.splice(i,1);else if(got.length<3)got.push(d.item);x.render();},
    async reset(d,el,x){(x.ui.lawDraft??={})[d.key]=[];x.render();},
    async submit(d,el,x){await x.send('lw_submit',{task:d.task,step:d.step,value:[...draft(x,d.key)]});},
    async lawAmount(d,el,x){const v=Number((x.ui.amt||{})[d.key]??0);if(!Number.isInteger(v)||v<0||v>10000)return;await x.send('lw_submit',{task:d.task,step:d.step,value:v});},
  },
};
