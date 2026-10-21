/** Nếp Thơm: one batch stage on screen; server grades every choice and receipt. */
// Compact layout (owner 19/10: every career has both sides): the how-to lines go to "?"; every label and choice stays.
import {clean,tip,buildUp,withArt} from '../ui-kit.js';
const STAGES=['inspect','sort','treat','wash','dry','finish','check','deliver'];
const NAMES={inspect:'Kiểm nhãn',sort:'Tách giỏ',treat:'Xử lý vết',wash:'Giặt',dry:'Làm khô',finish:'Ủi / gấp',check:'Kiểm đồ',deliver:'Trả khách'};
const CHECKS={count:'Đủ số món trên phiếu',stains:'Đã xử lý vết bẩn',dry:'Đồ đã khô đúng cách',finish:'Nếp ủi và gấp / treo đúng',tag:'Tem mỗi món khớp phiếu'};
const draft=(x,id,stage)=>(x.ui.laundry??={})[`${id}:${stage}`]??={};
const rules=x=>`<ul class="ld-rules">${(x.cc.rules||[]).map(s=>`<li>${x.esc(s)}</li>`).join('')}</ul>`;
const book=x=>`<details class="ld-book"><summary>Bảng chăm vải và tiến trình nghề</summary>${rules(x)}</details>`;
const stats=x=>{const s=x.room.data?.stats||{};return `<div class="ld-stats"><b>${s.good||0} / 100 phiếu đạt · ${s.active_days||0} / 30 ngày làm</b>${tip('Thợ vững tay cần đủ cả hai mốc. Nghệ nhân: 180 phiếu đạt và 45 ngày có trả đồ.','','span')}</div>`;};
const button=(x,t)=>`<button type="button" class="btn primary ld-submit" data-action="car:send" data-task="${x.esc(t.id)}" data-stage="${x.esc(t.stage)}">${t.stage==='deliver'?'Đối chiếu và trả đồ':'Xác nhận '+x.esc(NAMES[t.stage]||'bước này')}</button>`;
function control(x,t,g){
  const state=draft(x,t.id,t.stage),id=`ld-${t.id}-${t.stage}-${g.id}`;
  const attrs=`data-ld-task="${x.esc(t.id)}" data-ld-stage="${x.esc(t.stage)}" data-ld-field="${x.esc(g.id)}"`;
  if(t.stage==='inspect')return `<label class="ld-tick" for="${id}"><input id="${id}" type="checkbox" ${attrs}${state[g.id]?' checked':''}>Đã kiểm màu, nhãn và vết bẩn</label>`;
  if(['check','deliver','done'].includes(t.stage))return '';
  const opts=(t.options||[]).map(o=>`<option value="${x.esc(o.id)}"${state[g.id]===o.id?' selected':''}>${x.esc(o.label)}</option>`).join('');
  return `<label for="${id}" class="ld-field-label">${x.esc(NAMES[t.stage])} cho ${x.esc(g.name)}</label><select class="input" id="${id}" ${attrs}><option value="">Chọn cách xử lý…</option>${opts}</select>`;
}
function checks(x,t){
  const state=draft(x,t.id,t.stage);
  return `<fieldset class="ld-checks" data-coach="laundry-checks"><legend>Kiểm lần cuối · ${t.needs.quantity} món</legend>${Object.entries(CHECKS).map(([k,v])=>`<label class="ld-tick"><input type="checkbox" data-ld-task="${x.esc(t.id)}" data-ld-stage="check" data-ld-field="${k}"${state[k]?' checked':''}>${x.esc(v)}</label>`).join('')}</fieldset>`;
}
function tags(x,t){
  const state=draft(x,t.id,t.stage),opts=[...t.needs.tag_options];
  // Stable display order varies by ticket; location in a list never conveys correctness.
  if(Number(t.id.split('-').at(-1))%2)opts.reverse();else opts.push(opts.shift());
  return `<fieldset class="ld-checks" data-coach="laundry-checks"><legend>Phiếu khách xuất trình</legend>${opts.map(tag=>`<label class="ld-tick"><input type="radio" name="ld-tag" value="${x.esc(tag)}" data-ld-task="${x.esc(t.id)}" data-ld-stage="deliver" data-ld-field="tag"${state.tag===tag?' checked':''}>${x.esc(tag)}</label>`).join('')}</fieldset>`;
}
/* The customer's pile as it goes through the shop (owner 21/10, like the milk-tea cup): a basket of dirty clothes, the
   water in the wash, the drying rack, then the bag that goes home. A piece stays grey until its choice for this step is
   picked (input() lights it without a redraw); a stain shows until the stain step is done. */
const LOOK={cotton:'👕',poly:'🎽',silk:'🧣',linen:'👔',wool:'🧶',shell:'🧥',towel:'🛁'};
const STAGE_ICON={inspect:'🔍',sort:'🧺',treat:'🧴',wash:'🫧',dry:'☀️',finish:'👔',check:'✅',deliver:'🛍️',done:'🛍️'};
const picked=(x,t,g)=>{const s=draft(x,t.id,t.stage);return t.stage==='inspect'?s[g.id]===true:!!s[g.id];};
function pileArt(x,t){
  const at=STAGES.indexOf(t.stage),gs=t.needs?.garments||[],chooses=at>=0&&at<=5;
  const items=gs.map(g=>({e:LOOK[g.material]||'👕',t:g.name,cls:[`ld-c-${g.color}`,g.stain&&g.stain!=='none'&&(at<0?false:at<=2)?'ld-stain':'',chooses&&!picked(x,t,g)?'todo':''].filter(Boolean).join(' ')}));
  const kind=t.stage==='dry'?'bench':at>=5||at<0?'bag':'basket';
  const n=chooses?gs.filter(g=>picked(x,t,g)).length:gs.length;
  return buildUp({kind,items,fill:t.stage==='wash'?55:null,color:'#9fd3f0',caption:`${STAGE_ICON[t.stage]||'🧺'} ${n}/${gs.length}`,label:'Đồ của khách',cls:'ld-build'});
}
export default {
  id:'laundry',css:true,
  next(t){return !t.known?'Hỏi khách và nhận phiếu':NAMES[t.stage]||'Phiếu đã xong';},
  job(t,x){
    if(!t.known)return `<div class="career-job ld"><article class="card"><h3>🧺 Tiệm Nếp Thơm</h3>${tip('Nghe khách dặn, nhận số phiếu rồi kiểm từng món.','','p')}${x.cmd('Hỏi khách và nhận phiếu','ask',{task:t.id},'primary')}</article>${book(x)}</div>`;
    const n=t.needs,at=STAGES.indexOf(t.stage);
    const progress=`<ol class="ld-progress" aria-label="Các bước giặt ủi">${STAGES.map((s,i)=>`<li class="${i===at?'now':i<at?'done':''}"${i===at?' aria-current="step"':''}>${i<at?'✓':i+1} ${x.esc(NAMES[s])}</li>`).join('')}</ol>`;
    const garments=n.garments.map(g=>`<article class="ld-garment"><div class="ld-garment-head"><span aria-hidden="true">👕</span><h4>${x.esc(g.name)}</h4></div><p>${x.esc(g.description)}</p><p class="ld-label"><b>Nhãn chăm vải</b> ${x.esc(g.label)}</p><p><b>Khách dặn:</b> ${x.esc(g.packing)} · <b>Tem:</b> ${x.esc(g.tag)}</p>${control(x,t,g)}</article>`).join('');
    return `<div class="career-job ld"><header class="ld-ticket">${withArt(`<span>PHIẾU GIẶT · ${x.esc(n.tag)}</span><h3>${x.esc(t.title||'Tiệm Nếp Thơm')}</h3><p>${n.quantity} món · Chất lượng ${t.quality}% · Công chuẩn ${n.net} xu sau ${n.cost} xu vật tư</p>`,pileArt(x,t))}</header>${progress}<section class="ld-stage" data-stage="${x.esc(t.stage)}"><h3>${x.esc(x.cc.stages?.[t.stage]||NAMES[t.stage]||'Đã hoàn tất')}</h3><p>${x.esc(t.instruction||'')}</p>${t.last_issue?`<p class="ld-repair" role="status">${x.esc(t.last_issue)}</p>`:''}<div class="ld-garments" data-coach="laundry-items">${garments}</div>${t.stage==='check'?checks(x,t):t.stage==='deliver'?tags(x,t):''}${t.stage!=='done'?button(x,t):''}</section>${book(x)}${stats(x)}</div>`;
  },
  idle(x){return `<div class="career-job ld"><article class="card"><h3>🧺 Tiệm giặt ủi Nếp Thơm</h3>${tip('Nhận phiếu 2–4 món, đọc nhãn, tách màu và vải, xử lý vết, giặt, làm khô rồi ủi / gấp. Đối chiếu tem trước khi trả đồ.','','p')}${tip('Tiệm ứng vật tư theo phiếu, trừ một lần khi thu tiền. Sai thì sửa ngay tại bước hiện tại; công giảm theo chất lượng.','','p')}</article>${stats(x)}${book(x)}</div>`;},
  input(el,x){
    const d=el.dataset||{};if(!d.ldField)return false;
    draft(x,d.ldTask,d.ldStage)[d.ldField]=el.type==='checkbox'?el.checked:el.value;
    // Light the piece in the pile preview (no redraw: the selects keep focus).
    const g=el.closest?.('.ld-garment'),root=el.closest?.('.career-job'),pile=root?.querySelector('.ld-build');
    if(g&&pile){const i=[...g.parentElement.children].indexOf(g),pc=pile.querySelectorAll('.ck-piece')[i],on=el.type==='checkbox'?el.checked:!!el.value;
      pc?.classList.toggle('todo',!on);const cap=pile.querySelector('figcaption');
      if(cap){const all=pile.querySelectorAll('.ck-piece').length,left=pile.querySelectorAll('.ck-piece.todo').length;cap.textContent=cap.textContent.replace(/\d+\/\d+$/,`${all-left}/${all}`);}}
    return true;
  },
  actions:{
    async send(d,el,x){
      const state=draft(x,d.task,d.stage),payload={task:d.task};
      if(d.stage==='inspect')payload.items=Object.keys(state).filter(k=>state[k]===true);
      else if(d.stage==='check')payload.checks=Object.keys(state).filter(k=>state[k]===true);
      else if(d.stage==='deliver')payload.tag=state.tag;
      else payload.choices={...state};
      await x.send('ld_'+d.stage,payload);
    },
  },
  page(view,x){return view==='car:notes'?`<header class="sheet-head"><h2>Bảng chăm vải Nếp Thơm</h2><button type="button" class="btn ghost" data-action="close">Đóng</button></header><div class="sheet-body career-job ld">${rules(x)}${stats(x)}</div>`:'';},
  dock:[['car:notes','book','Bảng chăm vải','Nhãn giặt, xử lý vết, các mốc nghề']],
};
