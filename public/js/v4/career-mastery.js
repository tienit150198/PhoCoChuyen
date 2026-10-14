/** Lifetime craft recognition, independent of the current employer and formal rank. */
import {escapeHTML as esc} from '../icons.js';
const command=(label,action,payload={})=>`<button type="button" class="btn primary full" data-command="${action}" data-payload="${esc(JSON.stringify(payload))}">${esc(label)}</button>`;
const benefit=n=>`Tối đa +${n} xu khi khép ngày đạt chuẩn, nếu còn lượt nhận thu nhập.`;
const requirements=m=>(m.next?.requirements||[]).map(r=>`<li class="${r.met?'is-met':''}"><div><span>${r.met?'✓':'○'} ${esc(r.label)}</span><b>${r.got}/${r.need}</b></div>${r.id==='days'&&!r.met?`<small class="cm-hint">${r.hint?esc(r.hint):'Ngày nghề có ≥3 việc sạch, ≥80%; cộng khi khép ca.'}</small>`:''}<progress value="${Math.min(r.got,r.need)}" max="${Math.max(1,r.need)}" aria-label="${esc(r.label)}">${r.got}/${r.need}</progress></li>`).join('');
export function masteryCard(m,{compact=false}={}){
  if(!m)return '';
  const current=`<h3>${esc(m.badge||'🌱')} ${esc(m.title)}</h3>`;
  const next=m.next?`<p class="small">Hướng tới: <b>${esc(m.next.title)}</b></p>`:'<p class="small">Đã đạt đủ ba bậc tay nghề lâu năm.</p>';
  if(compact)return `<section class="lx-card" aria-label="Tay nghề lâu năm"><p class="eyebrow">TAY NGHỀ LÂU NĂM · BẬC ${m.tier}/3</p>${current}${next}<p class="small">${m.clean} việc sạch lỗi · ${m.qualified_days} ngày đạt chuẩn</p><button type="button" class="btn ghost full" data-action="promo">${m.exam?'Tiếp tục xét tay nghề':'Xem lộ trình tay nghề'}</button></section>`;
  const exam=m.exam;
  let action='',review='';
  if(exam){
    if(exam.complete)review=`<div class="cm-review"><h4>Đã trả lời ${exam.total} câu</h4><p>Nộp bài để nhận kết quả xét tay nghề.</p>${command('Nộp bài xét tay nghề','mastery_finish')}</div>`;
    else if(exam.question){
      const q=exam.question;
      review=`<div class="cm-review"><p class="eyebrow">Câu ${exam.index+1}/${exam.total}</p><h4>${esc(q.text)}</h4><div class="cm-options">${q.options.map(o=>command(o.label,'mastery_answer',{option:o.id})).join('')}</div><p class="small muted">Bài xét lưu sau mỗi câu; có thể quay lại tiếp tục.</p></div>`;
    }
  }else if(m.ready&&!m.retry_good_days)action=command('Bắt đầu xét tay nghề · 4 câu','mastery_start');
  else if(m.next)action='<button type="button" class="btn ghost full" data-action="close">Tiếp tục rèn nghề</button>';
  const result=m.last_result?`<p class="cm-result${m.last_result.passed?'':' is-failed'}" role="status">${m.last_result.passed?'✓ Đã đạt bài xét':'Bài xét chưa đạt'} · ${m.last_result.score}/${m.last_result.total} điểm.${!m.last_result.passed?' Cần ít nhất 7/8 điểm.':''}</p>`:'';
  const retry=m.retry_good_days?`<p class="cm-retry">Làm thêm ${m.retry_good_days} ngày đạt chuẩn để xét lại. Tiến độ tay nghề đã có được giữ nguyên.</p>`:'';
  const today=m.today?`<p class="small">${m.today.line?esc(m.today.line):`Hôm nay: ${m.today.clean}/${m.today.completed} việc sạch lỗi · ${m.today.qualified?'đạt chuẩn, khép ca để ghi nhận':'đang rèn nghề'}`}.</p>`:'';
  return `<section class="pm-card cm-card" aria-label="Tay nghề lâu năm"><p class="pm-eyebrow">TAY NGHỀ LÂU NĂM · BẬC ${m.tier}/3</p>${current}${next}${m.bonus?`<p class="cm-benefit">${benefit(m.bonus)}</p>`:''}${!exam&&m.next?`<ul class="cm-requirements">${requirements(m)}</ul><p class="small">Bậc tiếp theo: ${benefit(m.next.bonus||[0,6,12,20][m.next.tier])}</p>`:''}${result}${retry}${review}${today}${action}<details class="pm-more"><summary>Cách ghi nhận tay nghề</summary><p>Ngày đạt chuẩn: tự hoàn thành ít nhất 3 việc sạch lỗi, chiếm ít nhất 80% số việc hoàn thành trong ngày. Chỉ tính việc được tạo và tự làm xong trong cùng ngày nghề; việc giữ từ ngày cũ không tính. Khép ca để ghi nhận; ca bỏ dở không tính.</p><p>Thưởng chỉ trả khi còn lượt ngày nghề được nhận thu nhập, tối đa một lần mỗi ngày nghề; không nhân theo hệ số nghề. Hết lượt nhận thu nhập vẫn ghi nhận tiến độ, không cộng thưởng.</p><p>Đủ cả ba mốc rồi làm bài xét 4 câu, đạt từ 7/8 điểm. Không mất phí. Danh hiệu tay nghề giữ lại khi đổi nơi làm việc; chức vụ và cấp hàm vẫn theo lộ trình riêng.</p></details></section>`;
}
