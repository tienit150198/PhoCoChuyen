/** 🧰 Xưởng phục chế Hồn Xưa: one ticket stage on screen; the server grades every choice (game/careers/restore.py).
 * Both layouts (gọn / đầy đủ, owner 19/10): the how-to lines go to the folded notes and "?" tips; every label and choice
 * stays. Other players' orders (their broken vehicles, worn home parts, furniture made cổ điển) are worked at 🧰 Bàn thợ
 * (v4/restore.js), reached from the card at the bottom in both layouts. */
import {tip} from '../ui-kit.js';
const STAGES=['inspect','talk','parts','clean','fix','finish','check','deliver'];
const NAMES={inspect:'Đọc dấu hiệu',talk:'Chốt yêu cầu',parts:'Linh kiện',clean:'Làm sạch',fix:'Phục hồi',finish:'Hoàn thiện',check:'Kiểm đồ',deliver:'Trả khách'};
const CHECKS={stable:'Món đồ chắc, không lung lay',photo:'Chụp ảnh trước và sau phục chế',note:'Ghi đúng tuổi đồ và hạng mục lên phiếu',care:'Dặn khách cách giữ gìn'};
const draft=(x,id,stage)=>(x.ui.restore??={})[`${id}:${stage}`]??={};
const rules=x=>`<ul class="rs-rules">${(x.cc.rules||[]).map(s=>`<li>${x.esc(s)}</li>`).join('')}</ul>`;
const book=x=>`<details class="rs-book"><summary>Sổ nghề phục chế và tiến trình nghề</summary>${rules(x)}</details>`;
const stats=x=>{const s=x.room.data?.stats||{};return `<div class="rs-stats"><b>${s.good||0} / 100 phiếu đạt · ${s.active_days||0} / 30 ngày làm</b>${tip('Thợ vững tay cần đủ cả hai mốc. Nghệ nhân Hồn Xưa: 180 phiếu đạt và 45 ngày có trả đồ.','','span')}</div>`;};
const desk=x=>`<section class="card rs-desk"><button type="button" class="btn ghost rs-desk-go" data-action="restoreDesk" data-tab="bench" data-coach="restore-desk">🧰 Bàn thợ · đồ của người chơi</button>${tip('Bật dịch vụ ở 🛎️ Phố dịch vụ; người chơi khác gửi xe hỏng, phần nhà xuống cấp hay đồ gỗ muốn làm cổ điển.','','p')}</section>`;
const button=(x,t)=>`<button type="button" class="btn primary rs-submit" data-action="car:send" data-task="${x.esc(t.id)}" data-stage="${x.esc(t.stage)}">${t.stage==='deliver'?'Đối chiếu và trả đồ':'Xác nhận '+x.esc((NAMES[t.stage]||'bước này').toLowerCase())}</button>`;
const opts=(x,rows,cur,ph)=>`<option value="">${x.esc(ph)}</option>`+(rows||[]).map(o=>`<option value="${x.esc(o.id)}"${cur===o.id?' selected':''}>${x.esc(o.label)}</option>`).join('');
const attrs=(x,t,field)=>`data-rs-task="${x.esc(t.id)}" data-rs-stage="${x.esc(t.stage)}" data-rs-field="${x.esc(field)}"`;
function select(x,t,field,label,rows,ph){
  const st=draft(x,t.id,t.stage),id=`rs-${t.id}-${t.stage}-${field}`;
  return `<label for="${id}" class="rs-field-label">${x.esc(label)}</label><select class="input" id="${id}" ${attrs(x,t,field)}>${opts(x,rows,st[field],ph)}</select>`;
}
function radios(x,t,field,rows,name){
  const st=draft(x,t.id,t.stage);
  return rows.map(o=>`<label class="rs-tick"><input type="radio" name="${x.esc(name)}" value="${x.esc(o.id)}" ${attrs(x,t,field)}${st[field]===o.id?' checked':''}>${x.esc(o.label)}</label>`).join('');
}
function stageBody(x,t){
  const n=t.needs;
  if(t.stage==='inspect')return `<div class="rs-list" data-coach="restore-signs">${n.signs.map(s=>`<article class="rs-row"><p>${x.esc(s.text)}</p>${select(x,t,s.id,'Hư hỏng này là',t.options,'Chọn tên hư hỏng…')}</article>`).join('')}</div>`;
  if(t.stage==='talk')return `<div class="rs-list" data-coach="restore-talk">${n.demands.map(d=>`<fieldset class="rs-row rs-demand"><legend>🌀 Khách dặn</legend><p class="rs-quote">${x.esc(d.text)}</p>${radios(x,t,d.id,d.options,`rs-${t.id}-${d.id}`)}</fieldset>`).join('')}</div>`;
  if(t.stage==='parts')return `<div class="rs-list" data-coach="restore-parts">${n.parts.map(p=>`<article class="rs-row"><p><b>🔩 ${x.esc(p.name)}</b>${p.missing?' <span class="tag warn">Ngăn linh kiện đã hết</span>':' <span class="tag">Còn trong ngăn</span>'}</p>${select(x,t,p.id,'Lo linh kiện này',t.options,'Chọn cách lo…')}</article>`).join('')}</div>`;
  if(t.stage==='clean')return `<fieldset class="rs-row" data-coach="restore-clean"><legend>🧽 Chất liệu: ${x.esc(n.material_name)}</legend>${radios(x,t,'choice',t.options,`rs-${t.id}-clean`)}</fieldset>`;
  if(t.stage==='fix')return `<div class="rs-list" data-coach="restore-fix">${(t.found||[]).map(f=>`<article class="rs-row">${select(x,t,f.id,f.name,t.options,'Chọn cách phục hồi…')}</article>`).join('')}</div>`;
  if(t.stage==='finish'){
    const asked=(t.work?.talk&&n.demands.length)?`<p class="rs-note">🌀 Đã chốt với khách: ${n.demands.map(d=>x.esc(d.options.find(o=>o.id===t.work.talk[d.id])?.label||'')).join(' · ')}</p>`:'';
    const surface=n.surface?`<p class="rs-note">🔍 Bề mặt: <b>${x.esc(n.surface)}</b>${n.surface_kind?` · ${x.esc(n.surface_kind)}`:''}</p>`:'';
    return `<fieldset class="rs-row" data-coach="restore-finish"><legend>✨ Hoàn thiện</legend>${surface}${asked}${radios(x,t,'choice',t.options,`rs-${t.id}-finish`)}</fieldset>`;
  }
  if(t.stage==='check'){const st=draft(x,t.id,t.stage);return `<fieldset class="rs-row" data-coach="restore-checks"><legend>🔎 Kiểm lần cuối</legend>${Object.entries(CHECKS).map(([k,v])=>`<label class="rs-tick"><input type="checkbox" ${attrs(x,t,k)}${st[k]?' checked':''}>${x.esc(v)}</label>`).join('')}</fieldset>`;}
  if(t.stage==='deliver'){
    const st=draft(x,t.id,t.stage),tags=[...n.tag_options];
    if(Number(t.id.split('-').at(-1))%2)tags.reverse();else tags.push(tags.shift());   // where the right ticket sits says nothing
    return `<fieldset class="rs-row" data-coach="restore-tags"><legend>🎫 Phiếu khách xuất trình</legend>${tags.map(g=>`<label class="rs-tick"><input type="radio" name="rs-tag-${x.esc(t.id)}" value="${x.esc(g)}" ${attrs(x,t,'tag')}${st.tag===g?' checked':''}>${x.esc(g)}</label>`).join('')}</fieldset>`;
  }
  return '';
}
export default {
  id:'restore',css:true,
  next(t){return !t.known?'Hỏi khách và nhận phiếu':NAMES[t.stage]||'Phiếu đã xong';},
  job(t,x){
    if(!t.known)return `<div class="career-job rs"><article class="card rs-intro"><h3>🧰 Xưởng phục chế Hồn Xưa</h3><p>${x.esc(t.opening||'')}</p>${tip('Nghe khách kể, nhận phiếu rồi đọc từng dấu hiệu hư hỏng.','','p')}${x.cmd('Hỏi khách và nhận phiếu','ask',{task:t.id},'primary')}</article>${book(x)}${desk(x)}</div>`;
    const n=t.needs,at=STAGES.indexOf(t.stage);
    const progress=`<ol class="rs-progress" aria-label="Các bước phục chế">${STAGES.map((s,i)=>`<li class="${i===at?'now':i<at?'done':''}"${i===at?' aria-current="step"':''}>${i<at?'✓':i+1} ${x.esc(NAMES[s])}</li>`).join('')}</ol>`;
    const head=`<header class="rs-ticket"><span>PHIẾU PHỤC CHẾ · ${x.esc(n.tag)}</span><h3>${x.esc(n.item)}</h3><p class="rs-chips"><span class="tag">${x.esc(n.material_name)}</span>${n.surface?`<span class="tag">${x.esc(n.surface)}</span>`:''}<span class="tag">${n.damages} chỗ hư</span><span class="tag">${n.demands.length} yêu cầu khách</span><span class="tag">Chất lượng ${t.quality}%</span><span class="tag">Công ${n.net} xu sau ${n.cost} xu vật tư</span></p></header>`;
    const issue=t.last_issue?`<p class="rs-repair" role="status">${x.esc(t.last_issue)}</p>`:'';
    const stage=t.stage==='done'?'':`<section class="rs-stage" data-stage="${x.esc(t.stage)}"><h3>${x.esc(x.cc.stages?.[t.stage]||NAMES[t.stage])}</h3>${tip(t.instruction||'','','p')}${issue}${stageBody(x,t)}${button(x,t)}</section>`;
    return `<div class="career-job rs">${head}${progress}${stage}${book(x)}${stats(x)}${desk(x)}</div>`;
  },
  idle(x){return `<div class="career-job rs"><article class="card rs-intro"><h3>🧰 Xưởng phục chế Hồn Xưa</h3>${tip('Khách mang đồ xưa tới: đọc dấu hiệu, chốt yêu cầu oái oăm, lo linh kiện, làm sạch, phục hồi, hoàn thiện rồi trả đúng phiếu.','','p')}${tip('Xưởng ứng vật tư theo phiếu, trừ một lần khi thu tiền. Sai thì sửa ngay tại bước đó; công giảm theo chất lượng.','','p')}</article>${stats(x)}${book(x)}${desk(x)}</div>`;},
  input(el,x){
    const d=el.dataset||{};if(!d.rsField)return false;
    if(el.type==='radio'&&!el.checked)return true;
    draft(x,d.rsTask,d.rsStage)[d.rsField]=el.type==='checkbox'?el.checked:el.value;
    return true;
  },
  actions:{
    async send(d,el,x){
      const st=draft(x,d.task,d.stage),p={task:d.task};
      if(d.stage==='check')p.checks=Object.keys(st).filter(k=>st[k]===true);
      else if(d.stage==='deliver')p.tag=st.tag;
      else if(d.stage==='clean'||d.stage==='finish')p.choice=st.choice;
      else p.choices={...st};
      await x.send('phc_'+d.stage,p);
    },
  },
  page(view,x){return view==='car:notes'?`<header class="sheet-head"><h2>Sổ nghề phục chế Hồn Xưa</h2><button type="button" class="btn ghost" data-action="close">Đóng</button></header><div class="sheet-body career-job rs">${rules(x)}${stats(x)}${desk(x)}</div>`:'';},
  dock:[['car:notes','book','Sổ nghề','Dấu hiệu hư hỏng, cách phục hồi, các mốc nghề']],
};
