/** Server-owned NPC competition. Display only earned standings and published case options. */
import {escapeHTML as esc} from '../icons.js';
const number=value=>Number.isFinite(Number(value))?Math.max(0,Number(value)):0;
const command=(label,name,payload={})=>`<button type="button" class="btn primary full" data-command="${name}" data-payload="${esc(JSON.stringify(payload))}">${esc(label)}</button>`;
const progress=(value,max,label)=>`<progress value="${Math.min(number(value),Math.max(1,number(max)))}" max="${Math.max(1,number(max))}" aria-label="${esc(label)}"></progress>`;

function standings(c){
  const rows=c.standings||[];
  return `<div class="cc-board"><h4>Bảng đồng nghiệp · ca đã khép</h4><ol class="cc-standings">${rows.map(row=>{
    const rank=number(row.rank),tied=rows.filter(other=>number(other.rank)===rank).length>1;
    return `<li class="cc-standing${row.is_player?' is-player':''}"><span class="cc-rank" aria-label="${tied?'Đồng hạng':'Hạng'} ${rank}">${rank}</span><div><b>${esc(row.name)}</b><small>${row.is_player?'Bạn · ':''}${esc(row.strength)}</small>${tied?`<small>Đồng hạng ${rank}</small>`:''}</div><strong>${number(row.score)}<small>điểm</small></strong></li>`;
  }).join('')}</ol><p class="small muted">Bạn cùng 3 đồng nghiệp NPC. Điểm bằng nhau cùng hạng.</p></div>`;
}

function evidence(today={}){
  if(!number(today.completed)&&!(today.components||[]).length)return '<div class="cc-evidence"><h4>Minh chứng hôm nay</h4><p class="small muted">Chưa có việc tự làm được ghi nhận hôm nay.</p></div>';
  return `<div class="cc-evidence"><h4>Minh chứng hôm nay</h4><p class="small">${number(today.completed)} việc · ${number(today.score)}/100 điểm tạm tính</p><ul class="cc-components">${(today.components||[]).map(component=>`<li><span>${esc(component.label)}<small>trọng số ${number(component.weight)}</small></span><b>${number(component.score)}/100</b></li>`).join('')}</ul><p class="small muted">Dựa trên đánh giá công bằng và tiêu chí có minh chứng. Điểm được chuẩn hóa theo trọng số hiện có; khép ca để chốt.</p></div>`;
}

function leadership(c){
  const item=c.case;
  if(!item)return '';
  if(item.result)return `<div class="cc-case cc-case-result" role="status"><h4>${esc(item.result.title||'Tình huống lãnh đạo')}</h4><p class="small">Đã ghi nhận lựa chọn hôm nay.</p><p>${esc(item.result.feedback)}</p></div>`;
  if(item.active){
    const active=item.active;
    return `<div class="cc-case"><p class="pm-eyebrow">TÌNH HUỐNG LÃNH ĐẠO · NPC</p><h4>${esc(active.title)}</h4><p>${esc(active.text)}</p><div class="cc-options">${(active.options||[]).map(option=>command(option.label,'competition_answer',{option:option.id})).join('')}</div><p class="small muted">Một lựa chọn mỗi tình huống; kết quả được lưu khi trả lời.</p></div>`;
  }
  return `<div class="cc-case"><h4>Tình huống lãnh đạo</h4><p class="small muted">${esc(item.reason||'Giao việc, kiểm tra và ghi nhận công sức của đồng nghiệp NPC.')}</p>${item.unlocked&&item.ready?command('Nhận tình huống hôm nay','competition_start'):''}</div>`;
}

function result(c){
  const last=c.last_result;
  if(!last)return '';
  const award=c.reward?.cash===false?`${number(last.spirit)} tinh thần`:`${number(last.bonus)} xu`;
  return `<div class="cc-result${last.good?' is-good':''}" role="status"><p class="pm-eyebrow">NHẬN XÉT KỲ ${number(last.period)}</p><h4>${esc(c.recognizer)}</h4><p>${esc(last.message)}</p><p class="small">Hạng ${number(last.rank)} · ${number(last.score)}/100 điểm trung bình · ${award}</p></div>`;
}

function nextLeague(next){
  if(!next)return '<p class="cc-top">Đã đạt hạng thi đua cao nhất.</p>';
  return `<div class="cc-next"><h4>Hạng tiếp theo: ${esc(next.title)}</h4><ul class="cc-requirements">${(next.requirements||[]).map(requirement=>`<li class="${requirement.met?'is-met':''}"><div><span>${requirement.met?'✓':'○'} ${esc(requirement.label)}</span><b>${number(requirement.got)}/${number(requirement.need)}</b></div>${progress(requirement.got,requirement.need,requirement.label)}</li>`).join('')}</ul><p class="small muted">Hạng thi đua ghi nhận kết quả làm việc. Chức vụ vẫn theo lộ trình thăng tiến.</p></div>`;
}

export function competitionCard(c,{compact=false}={}){
  if(!c)return '';
  const period=c.period||{},league=Math.min(4,number(c.league)),reward=c.reward||{};
  const heading=`<p class="pm-eyebrow">THI ĐUA NGHỀ · Hạng ${league+1}/5</p><h3>Thi đua cùng đồng nghiệp</h3><p><b>${esc(c.title)}</b> · Kỳ ${number(period.number)||1}</p>`;
  const counter=`${number(period.worked_days)}/${number(period.total_days)||10} ca`;
  if(compact)return `<section class="lx-card cc-card" aria-label="Thi đua cùng đồng nghiệp">${heading}<p class="small">${counter} · ${number(period.score)} điểm đã chốt</p><button type="button" class="btn ghost full" data-action="promo">${c.case?.active?'Tiếp tục tình huống':'Xem bảng thi đua'}</button></section>`;
  const benefit=reward.cash===false?`Không thưởng xu · tối đa ${number(reward.spirit_cap)} tinh thần mỗi kỳ.`:`Thưởng tối đa ${number(reward.cap)} xu mỗi kỳ và không quá ${Math.round(number(reward.rate)*100)}% thu nhập tự làm đủ điều kiện.`;
  return `<section class="pm-card cc-card" aria-label="Thi đua cùng đồng nghiệp">${heading}<ol class="cc-leagues" aria-label="Năm hạng thi đua">${Array.from({length:5},(_,index)=>`<li class="cc-league${index===league?' is-current':index<league?' is-past':''}"${index===league?' aria-current="step"':''}>${index+1}</li>`).join('')}</ol><p class="small muted">${esc(c.focus)}</p><div class="cc-period"><div><b>${counter}</b><span>${number(period.score)} điểm đã chốt</span></div>${progress(period.worked_days,period.total_days||10,'Tiến độ kỳ thi đua')}<p class="small muted">Mỗi kỳ gồm 10 ca có tự làm việc. Ngày trống không tăng tiến độ.</p></div>${standings(c)}${result(c)}${evidence(c.today)}${leadership(c)}${nextLeague(c.next)}<p class="small cc-benefit">${benefit}</p><details class="cc-rules"><summary>Thưởng và cách tính kỳ</summary><p>Chỉ phần thu nhập cơ bản từ việc tự làm trong ngày được trả công mới tính vào quỹ thưởng. Cần còn lượt nhận thu nhập khi chốt kỳ; thưởng không nhân theo trang bị, vốn hay nhân viên.</p><p>Việc nhận rồi bỏ dở làm giảm kết quả. Tình huống lãnh đạo chỉ tác động đồng nghiệp NPC; trả lời không tạo tiền thưởng riêng.</p></details></section>`;
}
