/** Renders game/procedures.py steps as forms and reads the answer back.
 * Used by the teacher's "Kế hoạch lớp" and available to paperwork careers. */
import {icon,escapeHTML as esc} from '../icons.js';

const label=(list,id)=>list?.find(x=>x.id===id)?.label??id;

function solvedText(st){
  const a=st.answer;
  switch(st.kind){
    case'choice':return esc(label(st.options,a));
    case'multi':return (a||[]).map(x=>esc(label(st.options,x))).join(' · ');
    case'number':return esc(Number(a).toLocaleString('vi-VN'));
    case'order':return (a||[]).map((x,i)=>`${i+1}. ${esc(label(st.items,x))}`).join('<br>');
    case'match':return Object.entries(a||{}).map(([l,r])=>`${esc(label(st.left,l))} → ${esc(label(st.right,r))}`).join('<br>');
    case'fields':return Object.entries(a||{}).map(([k,v])=>{const f=st.fields.find(x=>x.id===k);return `${esc(f?.label||k)}: ${esc(f?.options?label(f.options,v):v)}`;}).join('<br>');
    case'entry':return (a||[]).map(x=>`Nợ ${esc(x.debit)} / Có ${esc(x.credit)}: ${esc(x.amount)}`).join('<br>');
  }
  return '';
}

function input(st,ui){
  const id=st.id;
  switch(st.kind){
    case'choice':return `<div class="choice-list">${st.options.map(o=>`<label class="choice"><input type="radio" name="ans" value="${esc(o.id)}" required><span>${esc(o.label)}</span></label>`).join('')}</div>`;
    case'multi':return `<div class="choice-list">${st.options.map(o=>`<label class="choice"><input type="checkbox" name="ans" value="${esc(o.id)}"><span>${esc(o.label)}</span></label>`).join('')}</div>`;
    case'number':return `<label class="field">Đáp số<input class="input" type="number" inputmode="numeric" name="ans" required step="1"></label>`;
    case'order':{
      // Tap-to-order: the chosen sequence lives in ui.order[id] between renders.
      const picked=(ui.order??={})[id]??=[];
      const rest=st.items.filter(x=>!picked.includes(x.id));
      return `<ol class="order-picked">${picked.map((x,i)=>`<li><span>${i+1}</span>${esc(label(st.items,x))}<button type="button" class="icon-btn small ghost" data-action="procUnpick" data-step="${esc(id)}" data-index="${i}" aria-label="Bỏ">${icon('x',14)}</button></li>`).join('')||'<li class="muted small">Chạm vào các mục bên dưới theo đúng thứ tự.</li>'}</ol>
        <div class="order-pool">${rest.map(x=>`<button type="button" class="chip-btn" data-action="procPick" data-step="${esc(id)}" data-item="${esc(x.id)}">${esc(x.label)}</button>`).join('')}</div>`;
    }
    case'match':return `<div class="match-grid">${st.left.map(l=>`<label class="field"><span>${esc(l.label)}</span><select name="m:${esc(l.id)}" required><option value="">Chọn…</option>${st.right.map(r=>`<option value="${esc(r.id)}">${esc(r.label)}</option>`).join('')}</select></label>`).join('')}</div>`;
    case'fields':return `<div class="match-grid">${st.fields.map(f=>`<label class="field"><span>${esc(f.label)}</span>${f.options?`<select name="f:${esc(f.id)}" required><option value="">Chọn…</option>${f.options.map(o=>`<option value="${esc(o.id)}">${esc(o.label)}</option>`).join('')}</select>`:`<input class="input" type="number" inputmode="numeric" name="f:${esc(f.id)}" required step="1">`}</label>`).join('')}</div>`;
  }
  return `<p class="muted">Bước này chưa có giao diện.</p>`;
}

/** steps: public steps from the server; command: action name for submit. */
export function procedureView(steps,{command,ui,extra={}}){
  return `<ol class="proc-steps">${steps.map((st,i)=>{
    const head=`<div class="proc-head"><span class="proc-no">${st.state==='solved'?icon('check',14):i+1}</span><b>${esc(st.title)}</b></div>`;
    if(st.state==='solved')return `<li class="proc-step solved">${head}<div class="proc-answer">${solvedText(st)}</div>${st.explain?`<p class="proc-explain">${esc(st.explain)}</p>`:''}</li>`;
    if(st.state==='locked')return `<li class="proc-step locked">${head}</li>`;
    return `<li class="proc-step current">${head}<p>${esc(st.prompt)}</p><form class="proc-form" data-proc-form="${esc(command)}" data-step="${esc(st.id)}" data-kind="${esc(st.kind)}" data-extra="${esc(JSON.stringify(extra))}">${input(st,ui)}<button class="btn primary" type="submit">Kiểm tra</button></form></li>`;
  }).join('')}</ol>`;
}

/** Builds the answer for a step form; returns null (and toasts) when incomplete. */
export function readAnswer(form,ui){
  const kind=form.dataset.kind,step=form.dataset.step,f=new FormData(form);
  switch(kind){
    case'choice':return f.get('ans');
    case'multi':{const v=f.getAll('ans');return v.length?v:null;}
    case'number':{const v=f.get('ans');return v===''||v===null?null:Math.trunc(Number(v));}
    case'order':{const v=ui.order?.[step]||[];return v.length?[...v]:null;}
    case'match':case'fields':{
      const out={},prefix=kind==='match'?'m:':'f:';
      for(const [k,v] of f.entries()){if(!k.startsWith(prefix))continue;if(v==='')return null;const el=form.elements[k];out[k.slice(2)]=el?.type==='number'?Math.trunc(Number(v)):v;}
      return out;
    }
  }
  return null;
}

export async function procedureSubmit(form,env){
  const command=form.dataset.procForm;if(!command)return false;
  const {ui,cmd,toast}=env;
  const answer=readAnswer(form,ui);
  if(answer===null){toast('Hoàn thành câu trả lời trước khi kiểm tra nhé.',true);return true;}
  const extra=JSON.parse(form.dataset.extra||'{}');
  const r=await cmd(command,{...extra,step:form.dataset.step,answer},{quiet:true});
  if(r){toast(r.message,!r.correct);if(r.correct&&ui.order)delete ui.order[form.dataset.step];}
  return true;
}

export function procedureAction(action,data,el,env){
  const {ui,renderSheet}=env;
  if(action==='procPick'){const list=(ui.order??={})[data.step]??=[];if(!list.includes(data.item))list.push(data.item);renderSheet();return true;}
  if(action==='procUnpick'){const list=ui.order?.[data.step];if(list){list.splice(Number(data.index),1);renderSheet();}return true;}
  return false;
}
