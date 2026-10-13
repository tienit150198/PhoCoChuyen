/** Professional learning and jobs. Prices, instructions and commands come from the server. */
import {escapeHTML as esc} from '../icons.js';
import {t} from './i18n.js';

const text=value=>esc(t(String(value??'')));
const rows=value=>Array.isArray(value)?value:[];
const finite=value=>Number.isFinite(Number(value))?Number(value):0;
const number=value=>finite(value).toLocaleString('vi-VN');
const coins=value=>`${number(value)} ${text('xu')}`;
const commandOK=value=>typeof value==='string'&&/^special_[a-z_]+$/.test(value);
const PHASE={offered:'Đơn chuyên môn đề nghị',working:'Thực hiện đơn',offer:'Đơn chuyên môn đề nghị',stock:'Chuẩn bị vật tư',ready:'Sẵn sàng cam kết',committed:'Đã cam kết',running:'Thực hiện đơn',work:'Thực hiện đơn',acceptance:'Kiểm tra và bàn giao',settled:'Đã quyết toán'};
const COSTS={revenue:'Doanh thu / phụ cấp',materials:'Vật tư',wages:'Công / dịch vụ trực tiếp',premises:'Mặt bằng',loss:'Hao hụt',tax:'Thuế',net:'Thực nhận sau chi phí'};
const safeName=name=>typeof name==='string'&&/^[a-zA-Z][a-zA-Z0-9_]*$/.test(name)&&!['constructor','prototype','__proto__'].includes(name);

function field(f){
  if(!f||!safeName(f.name))return '';
  const label=text(f.label||f.name),name=esc(f.name);
  if(f.type==='select'||Array.isArray(f.options))return `<label>${label}<select name="${name}" data-special-field required>${rows(f.options).map(o=>`<option value="${esc(o.value)}"${String(o.value)===String(f.value)?' selected':''}>${text(o.label??o.value)}</option>`).join('')}</select></label>`;
  const numeric=f.type==='number';
  const bounds=numeric?`${f.min!=null?` min="${finite(f.min)}"`:''}${f.max!=null?` max="${finite(f.max)}"`:''} step="1" inputmode="numeric"`:' maxlength="240"';
  return `<label>${label}<input name="${name}" data-special-field type="${numeric?'number':'text'}" value="${esc(f.value??'')}"${bounds} required></label>`;
}

function action(a){
  if(!a||!commandOK(a.command))return '';
  return `<fieldset class="special-action"${a.disabled?' disabled':''}><legend class="sr-only">${text(a.label)}</legend>${rows(a.fields).map(field).join('')}<button type="button" class="btn ${a.primary===false?'ghost':'primary'} full" data-action="specialSubmit" data-command-name="${esc(a.command)}" data-payload="${esc(JSON.stringify(a.payload||{}))}"${a.disabled?' disabled':''}>${text(a.label)}</button>${a.reason?`<small class="muted">${text(a.reason)}</small>`:''}</fieldset>`;
}
const actions=list=>rows(list).map(action).join('');
const instructions=list=>rows(list).length?`<ol class="special-instructions">${rows(list).map(s=>`<li>${text(s)}</li>`).join('')}</ol>`:'';

function ledger(q){
  if(!q)return '';
  return `<dl class="special-ledger">${Object.entries(COSTS).filter(([key])=>q[key]!=null).map(([key,label])=>`<div${key==='net'?' class="special-net"':''}><dt>${text(label)}</dt><dd>${coins(q[key])}</dd></div>`).join('')}</dl>`;
}

function requirements(list){
  return `<ul class="special-requirements">${rows(list).map(r=>`<li${r.met?' class="is-met"':''}><span>${r.met?'✓':'○'} ${text(r.label)}</span>${r.got!=null?`<b>${number(r.got)} / ${number(r.need)}</b>`:''}${r.reason?`<small>${text(r.reason)}</small>`:''}</li>`).join('')}</ul>`;
}

function studyCard(s){
  if(!s)return '';
  return `<article class="special-study"><p class="pm-eyebrow">${text('HỌC VÀ THỰC HÀNH')}</p><h4>${text(s.title)}</h4><p class="small muted">${text('Thực hành và thử lại miễn phí, không sinh tiền hoặc XP.')}</p>${instructions(s.instructions)}${s.progress?`<p class="special-progress">${text(s.progress)}</p>`:''}${s.feedback?`<div class="special-feedback" role="status">${text(typeof s.feedback==='object'?s.feedback.message:s.feedback)}</div>`:''}${actions(s.actions)}</article>`;
}

function jobCard(j,kind){
  if(!j)return '';
  return `<article class="special-job"><p class="pm-eyebrow">${text(PHASE[j.phase]||j.phase||'Đơn chuyên môn')}</p><h4>${text(j.title)}</h4>${j.description?`<p>${text(j.description)}</p>`:''}${j.quantity!=null?`<p class="special-quantity"><span>${text('Khối lượng')}</span><b>${number(j.quantity)} ${text(j.unit||'bộ')}</b></p>`:''}${kind==='agency'?`<p class="special-note">${text('Vật tư được cấp hiện vật. Ngân sách và tiền khách không phải thu nhập; chỉ phụ cấp được quyết toán.')}</p>`:''}${kind==='community'?`<p class="special-note">${text('Công quả không tạo thu nhập; tinh thần tối đa 100.')}</p>`:''}${j.quote?`<details class="special-receipt"${['offer','offered'].includes(j.phase)?' open':''}><summary>${text('Dự toán toàn đơn')}</summary>${ledger(j.quote)}<p class="small muted">${text('Tính theo khối lượng của đơn, không nhân thu nhập theo nhân viên hoặc thi đua.')}</p></details>`:''}${instructions(j.instructions)}${j.detail?Array.isArray(j.detail)?instructions(j.detail):`<p class="small">${text(j.detail)}</p>`:''}${actions(j.actions)}</article>`;
}

function stockCard(stock,job){
  if(!stock||!rows(stock.items).length&&!rows(stock.actions).length)return '';
  const stockActions=rows(stock.actions),items=rows(stock.items);
  const code=a=>a.code||a.sku||a.payload?.code||a.payload?.sku;
  const unscoped=stockActions.filter(a=>!items.some(m=>m.code&&m.code===code(a)));
  const preparing=['stock','offer','offered'].includes(job?.phase);
  return `<details class="special-stock"${preparing?' open':''}><summary>${text('Kho chuyên môn')} · ${number(items.length)} ${text('mã vật tư')}</summary><p class="small muted">${text('Vật tư riêng cho đơn chuyên môn. Mỗi mã dùng sức chứa và hạn mức nhập đã mua.')}</p>${items.map(m=>`<details class="special-stock-item"><summary><span>${text(m.name)}</span><small>${number(m.available)} ${text(m.unit)} ${text('sẵn có')}</small></summary><p class="small">${text('Tồn kho')}: <b>${number(m.units)}</b> ${text(m.unit)} · ${text('Sức chứa')}: ${number(m.capacity)} · ${text('Nhập tối đa')}: ${number(m.order)}</p>${m.unit_cost!=null?`<p class="small">${text('Giá nhập mỗi đơn vị')}: <b>${coins(m.unit_cost)}</b></p>`:''}${actions(stockActions.filter(a=>m.code&&m.code===code(a)))}${actions(m.actions)}</details>`).join('')}${actions(unscoped)}</details>`;
}

export function specialismCard(s){
  if(!s)return '';
  const n=s.next,community=s.kind==='community';
  return `<section class="pm-card special-card" aria-label="${text('Chuyên môn nghề')}"><p class="pm-eyebrow">${text('CHUYÊN MÔN NGHỀ')} · ${number(s.tier)}/10</p><h3>${text('Học một nghề, làm một đơn thật')}</h3><p class="small muted">${text('Học theo gói, thực hành đúng rồi nhận đơn chuyên môn. Chứng chỉ và chức vụ hiện có được giữ nguyên.')}</p>${s.quota&&!community?`<p class="special-quota">${text('Còn')} <b>${number(s.quota.available)}</b> ${text('suất dùng chung với quản lý')} · +${number(s.quota.daily)} / ${text('ngày thực')} · ${text('tối đa')} ${number(s.quota.cap)}</p>`:''}${studyCard(s.study)}${jobCard(s.job,s.kind)}${actions(s.actions)}${stockCard(s.stock,s.job)}
    ${n?`<article class="special-next"><p class="pm-eyebrow">${text('GÓI TIẾP THEO')}</p><h4>${text(n.title)}</h4><p class="special-fee"><span>${text('Học phí')}</span><strong>${finite(n.fee)===0?text('Miễn phí'):coins(n.fee)}</strong></p><p class="small muted">${text(community?'Học và thực hành công quả miễn phí.':'Học phí cá nhân, trừ quỹ nghề một lần khi đăng ký, kể cả nghề công vụ.')}</p>${n.benefit?`<p>${text(n.benefit)}</p>`:''}${requirements(n.requirements)}${n.action?action({...n.action,disabled:n.action.disabled||n.can_enrol===false,reason:n.action.reason||n.reason}):''}${n.quote?`<details class="special-receipt"><summary>${text('Dự toán khi mở gói')}</summary>${ledger(n.quote)}</details>`:''}</article>`:''}
    ${rows(s.catalog).length?`<details class="special-path"><summary>${text('Lộ trình 10 gói chuyên môn')}</summary><ol>${rows(s.catalog).map(p=>`<li${p.unlocked?' class="is-unlocked"':''}><span>${p.unlocked?'✓ ':''}${text(p.title)}</span><small>${text('Học phí')}: <b>${finite(p.fee)===0?text('Miễn phí'):coins(p.fee)}</b></small></li>`).join('')}</ol></details>`:''}
    ${rows(s.history).length?`<details class="special-history"><summary>${text('Biên nhận chuyên môn gần đây')}</summary>${rows(s.history).slice(-8).reverse().map(r=>`<article><h4>${text(r.title||'Đơn chuyên môn')}</h4>${r.message?`<p>${text(r.message)}</p>`:''}${ledger(r)}</article>`).join('')}</details>`:''}
  </section>`;
}

export async function specialismAction(name,data,el,env){
  if(name!=='specialSubmit')return false;
  if(el?.disabled)return true;
  const command=data?.commandName||data?.command;
  if(!commandOK(command))throw new Error(t('Thao tác chuyên môn không hợp lệ.'));
  const payload=JSON.parse(data.payload||'{}');
  if(!payload||typeof payload!=='object'||Array.isArray(payload))throw new Error(t('Dữ liệu chuyên môn không hợp lệ.'));
  const form=el?.closest?.('.special-action');
  for(const field of form?.querySelectorAll('[data-special-field]')||[]){
    if(!safeName(field.name))throw new Error(t('Trường nhập chuyên môn không hợp lệ.'));
    if(!field.reportValidity())return true;
    if(field.type==='number'){
      const value=Number(field.value);
      if(!String(field.value).trim()||!Number.isSafeInteger(value))return true;
      payload[field.name]=value;
    }else payload[field.name]=field.value;
  }
  if(el)el.disabled=true;
  const wasDisabled=form?.disabled;
  if(form)form.disabled=true;
  try{await env.cmd(command,payload);env.renderSheet?.();}
  finally{if(el)el.disabled=false;if(form)form.disabled=wasDisabled;}
  return true;
}
