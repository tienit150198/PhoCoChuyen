/** Server-owned business entitlements. Rendering never starts or extends an inspection. */
import {escapeHTML as esc} from '../icons.js';
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const active=l=>l?.enabled&&['grace','restricted'].includes(l.status);
const deadline=l=>Number.isFinite(l?.deadline)&&l.deadline>0?new Date(l.deadline*1000).toLocaleString('vi-VN'):'';
const learn=id=>id?`<button type="button" class="btn primary" data-qy="licenseLearn" data-cert="${esc(id)}">📖 Học và thi chứng chỉ</button>`:'';

export function licensePanel(l){
  if(!l?.enabled)return '';
  const pending=(l.courses||[]).slice(0,l.required_level||0).filter(c=>!c.earned);
  const fees=pending.map(c=>`<li>${esc(c.name)} · ${fmt(c.enrol_fee??c.fee)} xu${c.enrol_fee<c.fee?' (thi lại)':''}</li>`).join('');
  const text=l.status==='restricted'
    ?`${fmt(l.blocked_ids?.length)} quầy tạm dừng nhận đơn mới vì quá hạn bổ sung giấy. Các đơn đã nhận vẫn được hoàn tất.`
    :l.status==='grace'?`Bạn có 72 giờ từ khi nhận biên bản để bổ sung chứng chỉ. Trong hạn, các quầy cũ vẫn bán bình thường.`
    :l.status==='compliant'?'Bạn đã đủ chứng chỉ cho quy mô hiện tại.':'Học theo quy mô quầy: cơ bản cho xe đẩy và sạp, nâng cao cho ki-ốt, quản lý chuỗi từ ba ki-ốt.';
  return `<section class="bk-card qy-license" aria-label="Chứng chỉ kinh doanh"><h3>${active(l)?'🚔 Công an kiểm tra':'🎓 Lộ trình kinh doanh'}</h3>
    <p>${text}</p>${active(l)&&deadline(l)?`<p><b>Hạn bổ sung: ${esc(deadline(l))}</b></p>`:''}
    ${fees?`<details><summary>Học phí các cấp còn thiếu</summary><ul>${fees}</ul><p>Học lần lượt; phí mỗi cấp gồm một lần thi. Thi lại trả nửa học phí hiện hành. Không thu theo từng quầy.</p></details>`:''}
    ${l.status==='restricted'?'<p>Quầy bị hạn chế không phát sinh chi phí tự động trong lúc dừng; đơn tồn vẫn tính giá vốn, thuế và chi phí trực tiếp. Tiền, hàng và nhân viên được giữ nguyên.</p>':''}
    <div class="bk-actions">${learn(l.next_cert)}</div></section>`;
}

export function licenseRequirement(r,l){
  if(!r)return '';
  const c=(l?.courses||[]).find(c=>c.id===r.next_cert);
  return `<div class="qy-license-requirement"><p>${r.allowed?(r.required_level?'✅ Đã đủ chứng chỉ':'✅ Không cần chứng chỉ cho xe đẩy đầu tiên'):esc(r.reason||'Cần bổ sung chứng chỉ trước khi mở rộng.')}</p>
    ${r.allowed?'':`${c?`<p>Khóa tiếp theo: ${esc(c.name)} · ${fmt(c.enrol_fee??c.fee)} xu. Học phí tách riêng vốn mở quầy.</p>`:''}${learn(r.next_cert)}`}</div>`;
}

export function licenseNotice(l){
  if(!active(l))return '';
  return `<button type="button" class="btn business-license-notice" data-action="quay" data-inspection="true"><span aria-hidden="true">🚔</span><span><b>${l.status==='restricted'?'Quầy cần bổ sung chứng chỉ':'Bổ sung chứng chỉ kinh doanh'}</b><small>${l.status==='restricted'?`${fmt(l.blocked_ids?.length)} quầy đang bị hạn chế`:`Hạn: ${esc(deadline(l))}`} · Xem biên bản</small></span></button>`;
}

export function mountLicenseNotice(journey){
  const html=licenseNotice(journey?.quay?.business_license);
  let box=document.getElementById('business-license-notice');
  if(!html){box?.remove();return;}
  if(!box){box=document.createElement('aside');box.id='business-license-notice';box.setAttribute('aria-label','Thông báo kiểm tra kinh doanh');document.getElementById('app')?.append(box);}
  if(box.innerHTML!==html)box.innerHTML=html;
}

export function preferStall(ids,preferred,id){
  if(!ids.includes(id))return [];
  return [...new Set([id,...preferred,...ids])].filter(x=>ids.includes(x));
}
