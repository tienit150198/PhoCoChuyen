/** Server-authored scale, site and contract actions. No client prices or rewards. */
import {escapeHTML as esc} from '../icons.js';

const number=value=>Number.isFinite(Number(value))?Number(value).toLocaleString('vi-VN'):'0';
const coins=value=>`${number(value)} xu`;
const PHASE={offer:'Hợp đồng đề nghị',planning:'Lập phương án',stock:'Chuẩn bị vật tư',
  staffing:'Phân ca',running:'Xử lý công việc',exception:'Xử lý phát sinh',acceptance:'Nghiệm thu',settled:'Đã đối soát'};
const COSTS={revenue:'Doanh thu',materials:'Vật tư tiêu dùng',wages:'Lương đội ngũ',premises:'Mặt bằng · bảo trì',loss:'Hao hụt',tax:'Thuế',net:'Lãi sau chi phí'};

function field(f){
  const name=esc(f.name),label=esc(f.label||f.name);
  if(Array.isArray(f.options))return `<label>${label}<select name="${name}" data-scale-field>${f.options.map(o=>`<option value="${esc(o.value)}"${String(o.value)===String(f.value)?' selected':''}>${esc(o.label)}</option>`).join('')}</select></label>`;
  const numeric=f.type==='number';
  return `<label>${label}<input data-scale-field name="${name}" type="${numeric?'number':'text'}" value="${esc(f.value??'')}"${numeric?` min="${number(f.min??1).replaceAll('.','')}" max="${number(f.max??4000).replaceAll('.','')}" step="1" inputmode="numeric"`:' maxlength="60"'} required></label>`;
}

function action(a){
  if(!/^scale_[a-z_]+$/.test(a.command||''))return '';
  const fields=(a.fields||[]).map(field).join('');
  return `<fieldset class="scale-action"><legend class="sr-only">${esc(a.label)}</legend>${fields}<button type="button" class="btn ${a.primary===false?'ghost':'primary'} full" data-action="scaleSubmit" data-command-name="${esc(a.command)}" data-payload="${esc(JSON.stringify(a.payload||{}))}"${a.disabled?' disabled':''}>${esc(a.label)}</button>${a.reason?`<small class="muted">${esc(a.reason)}</small>`:''}</fieldset>`;
}

function ledger(q){
  if(!q)return '';
  return `<dl class="scale-ledger">${Object.entries(COSTS).filter(([k])=>q[k]!=null).map(([k,label])=>`<div class="${k==='net'?'scale-net':''}"><dt>${label}</dt><dd>${coins(q[k])}</dd></div>`).join('')}</dl>`;
}

function requirements(rows){
  return `<ul class="scale-requirements">${(rows||[]).map(r=>`<li class="${r.met?'is-met':''}"><span>${r.met?'✓':'○'} ${esc(r.label)}</span>${r.got!=null?`<b>${number(r.got)} / ${number(r.need)}</b>`:''}${r.reason?`<small>${esc(r.reason)}</small>`:''}</li>`).join('')}</ul>`;
}

function contractCard(c,kind,site){
  if(!c)return '';
  return `<article class="scale-contract"><p class="pm-eyebrow">${esc(PHASE[c.phase]||c.phase||'Hợp đồng quản lý')}</p><h4>${esc(c.title||c.id)}</h4>${c.description?`<p>${esc(c.description)}</p>`:''}${c.evidence?`<ul>${c.evidence.map(s=>`<li>${esc(s)}</li>`).join('')}</ul>`:''}
    ${c.progress?`<p class="small">${esc(c.progress)}</p>`:''}
    ${kind==='agency'?'<p class="scale-note">Vật tư và đội ngũ dùng ngân sách cơ quan. Chỉ phụ cấp nghiệm thu được chuyển vào quỹ nghề.</p>':''}
    ${c.quote?`<details class="scale-receipt"${c.phase==='offer'?' open':''}><summary>Dự toán và vốn cam kết</summary>${ledger(c.quote)}${c.working_capital!=null?`<p>Cần có trong quỹ: <b>${coins(c.working_capital)}</b></p>`:''}</details>`:''}
    ${(c.materials||[]).filter(m=>!site||m.site===site).map(m=>`<div class="scale-material"><b>${esc(m.name)}</b><span>${number(m.available)} / ${number(m.required)} ${esc(m.unit||'đơn vị')}</span>${m.detail?`<small>${esc(m.detail)}</small>`:''}${(m.actions||[]).map(action).join('')}</div>`).join('')}
    ${(c.jobs||[]).filter(j=>!site||j.site===site).map(j=>`<div class="scale-job"><b>${esc(j.label)}</b><p class="small">${esc(j.detail||'')}</p>${(j.actions||[]).map(action).join('')}</div>`).join('')}
    ${(c.actions||[]).map(action).join('')}
    ${c.result?`<div class="scale-result" role="status"><p>${esc(c.result.message||'Đã lưu biên nhận ca.')}</p>${ledger(c.result)}</div>`:''}</article>`;
}

export function scaleCard(s,{compact=false,site=null}={}){
  if(!s)return '';
  const community=s.kind==='community',agency=s.kind==='agency';
  const head=`<p class="pm-eyebrow">${community?'CÔNG QUẢ CỘNG ĐỒNG':agency?'PHẠM VI ĐƯỢC GIAO':'MỞ RỘNG CƠ SỞ'} · ${number(s.tier)}/8</p><h3>${esc(s.title||'Bắt đầu từ công việc hằng ngày')}</h3>`;
  if(compact)return `<section class="lx-card scale-card">${head}<p class="small">${esc(s.next?`Mốc tiếp theo: ${s.next.title}`:'Đã đạt quy mô cao nhất.')}</p><button class="btn ghost full" type="button" data-action="promo">Xem mở rộng</button></section>`;
  const n=s.next;
  const selected=(s.sites||[]).find(x=>x.id===site);
  if(!selected)site=null;
  const crewActions=(s.actions||[]).filter(a=>a.command.startsWith('scale_crew_'));
  const otherActions=(s.actions||[]).filter(a=>!a.command.startsWith('scale_crew_'));
  const stock=s.stock;
  const scopedFields=a=>!site?a:{...a,fields:(a.fields||[]).map(f=>{
    if(f.name==='source'||f.name==='site'&&a.command!=='scale_stock_move')return {...f,value:site,options:(f.options||[]).filter(o=>o.value===site)};
    if(f.name==='site'&&a.command==='scale_stock_move'){const options=(f.options||[]).filter(o=>o.value!==site);return {...f,options,value:options[0]?.value};}
    return f;
  })};
  const stockActions=(stock?.actions||[]).filter(a=>!site||!(a.site||a.payload?.site)||(a.site||a.payload.site)===site).map(scopedFields);

  return `<section class="pm-card scale-card" aria-label="Mở rộng nghề">${head}${s.focus?`<p>${esc(s.focus)}</p>`:''}
    ${s.limits&&!agency&&!community?`<div class="scale-limits"><span>Kho <b>${number(s.limits.stock)}</b> / mã</span><span>Mỗi lần nhập <b>${number(s.limits.order)}</b> / dòng</span></div><p class="small muted">Quy mô mở cách tổ chức phục vụ. Kho và hạn mức nhập dùng các nâng cấp đã mua.</p>`:''}
    ${n?`<article class="scale-next"><p class="pm-eyebrow">MỐC TIẾP THEO</p><h4>${esc(n.title)}</h4><strong class="scale-fee">${n.fee?coins(n.fee):agency?'Giao phạm vi mới':'Ghi nhận tiến độ'}</strong>${n.benefit?`<p>${esc(n.benefit)}</p>`:''}${requirements(n.requirements)}${action({command:'scale_upgrade',label:n.fee?`Nâng quy mô · ${coins(n.fee)}`:agency?'Nhận phạm vi mới':'Ghi nhận mốc công quả',payload:{expected_tier:s.tier},disabled:!n.can_buy,reason:n.reason})}${n.quote?`<details class="scale-receipt"><summary>Dự toán một ca đầy nhu cầu</summary>${ledger(n.quote)}<p class="small">Lãi cho toàn bộ mạng lưới. Kết quả thực tế còn tùy khối lượng nghiệm thu và chi phí.</p></details>`:''}</article>`:''}
    ${s.stages?`<details class="pm-more"><summary>Lộ trình 8 mốc</summary><ol class="scale-path">${s.stages.map(t=>`<li><span>${esc(t.title)}</span><b>${t.fee?coins(t.fee):'Theo tiến độ'}</b></li>`).join('')}</ol></details>`:''}
    ${s.quota&&!community?`<p class="scale-quota">Còn <b>${number(s.quota.available)}</b> suất quản lý · +${number(s.quota.daily)}/ngày thực · giữ tối đa ${number(s.quota.cap)}</p>`:''}
    ${selected?`<p class="scale-note">Đang điều phối tại <b>${esc(selected.name)}</b> <button class="btn ghost" data-action="scaleAllSites">Xem toàn mạng</button></p>`:''}
    ${contractCard(s.contract,s.kind,site)}${otherActions.map(action).join('')}
    ${stock?.items?.length?`<details class="scale-stock"${s.contract?.phase==='stock'?' open':''}><summary>Kho vật tư điều phối</summary><p class="small">Vật tư này dùng cho hợp đồng quản lý. Sức chứa tính chung mọi cơ sở, gồm hàng đang về và giữ chỗ.</p>${stock.items.map(m=>`<article><h4>${esc(m.name)}</h4><p>${number(m.occupied)}/${number(m.capacity)} thùng · tối đa ${number(m.order)} thùng/lần</p>${m.locations.filter(x=>!site||x.site===site).map(x=>`<p class="small">${esc(x.name)}: ${number(x.units)} ${esc(m.unit)} · tự do ${number(x.available)}</p>`).join('')}</article>`).join('')}${stockActions.map(action).join('')}</details>`:''}
    ${crewActions.length?`<details class="scale-crew"><summary>Đội ngũ · ${(s.crew||[]).length} người</summary>${(s.crew||[]).map(p=>`<p class="small">${esc(p.name)} · ${esc(p.role)}</p>`).join('')}${crewActions.map(action).join('')}</details>`:''}
    <details class="scale-guest"><summary>Thăm cơ sở bạn bè</summary><label>Mã cơ sở<input name="scale-guest-code" maxlength="120" placeholder="Dán mã cơ sở công khai" /></label><button class="btn ghost full" data-action="scaleVisitGuest">Đi đến cơ sở</button></details>
    ${(s.sites||[]).length?`<details class="scale-sites" open><summary>Các cơ sở · ${s.sites.length}</summary>${s.sites.map(site=>`<article><div><b>${esc(site.name)}</b><small>${number(site.resources)} ${esc(s.resource_name||'vị trí')} · ${number(site.crew_count)} người</small></div><button type="button" class="btn ghost" data-action="scaleVisit" data-site="${esc(site.id)}">Vào cơ sở ↗</button>${(!selected||site.id===selected.id?site.actions||[]:[]).map(action).join('')}</article>`).join('')}</details>`:''}
    ${(s.resources||[]).length?`<details class="scale-resources"><summary>Phân công ${esc(s.resource_name||'tài nguyên')}</summary>${s.resources.filter(r=>!site||r.site===site).map(r=>`<article><b>${esc(r.label||r.id)}</b><p class="small">${esc(r.site_name||r.site||'Chưa bố trí')} · ${r.busy?'Đang có việc':'Sẵn sàng'}${r.crew_name?` · ${esc(r.crew_name)}`:''}</p>${(r.actions||[]).map(scopedFields).map(action).join('')}</article>`).join('')}</details>`:''}
    ${(s.history||[]).length?`<details class="scale-history"><summary>Biên nhận ca gần đây</summary>${s.history.slice(-8).reverse().map(r=>`<article><b>${esc(r.id)}</b><p>${esc(r.message||'')}</p>${ledger(r)}</article>`).join('')}</details>`:''}
    <details class="pm-more"><summary>Cách lên quy mô</summary><p>Ngày thực đạt chuẩn: ít nhất 3 việc tự làm không lỗi và tỷ lệ sạch từ 80%. Từ mốc thứ hai còn cần một ca quản lý nghiệm thu trong ngày. Đổi ngày nghề không tăng ngày thực.</p><p>${community?'Đi chùa, thắp hương và thẻ chúc vẫn theo cách chơi hiện có.':agency?'Phạm vi dự án không thay chức vụ, cấp hàm hoặc quyền nghiệp vụ.':'Cơ sở phụ dùng chung quyền số quầy của tài khoản. Nhân lực và hàng hóa cần được bố trí trước khi vận hành.'}</p></details>
  </section>`;
}

export async function scaleAction(name,data,el,env){
  if(name==='scaleAllSites'){env.ui.scaleSite=null;env.renderSheet?.();return true;}
  if(name==='scaleVisitGuest'){
    const code=el?.closest?.('.scale-guest')?.querySelector('[name="scale-guest-code"]')?.value?.trim();
    if(!code){env.toast?.('Nhập mã cơ sở công khai trước nhé.');return true;}
    const {openScaleSiteGuest}=await import('./scale-site.js');
    await openScaleSiteGuest(env,code);return true;
  }
  if(name==='scaleVisit'){
    const {openScaleSite}=await import('./scale-site.js');
    await openScaleSite(env,data.site);return true;
  }
  if(name!=='scaleSubmit')return false;
  if(el?.disabled)return true;
  const command=data.commandName||data.command;
  if(!/^scale_[a-z_]+$/.test(command||''))throw new Error('Thao tác mở rộng không hợp lệ.');
  const payload=JSON.parse(data.payload||'{}');
  for(const field of el?.closest?.('.scale-action')?.querySelectorAll('[data-scale-field]')||[]){
    if(!field.reportValidity())return true;
    payload[field.name]=field.type==='number'?Number(field.value):field.value;
  }
  if(el)el.disabled=true;
  try{await env.cmd(command,payload);env.renderSheet?.();}
  finally{if(el)el.disabled=false;}
  return true;
}
