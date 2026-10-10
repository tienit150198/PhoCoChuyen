/** Weekly microphone tug-of-war standings. The server decides eligibility and awards. */
import {escapeHTML as esc} from '../icons.js';

const num=n=>Number.isFinite(Number(n))?Number(n):0;
const fmt=n=>num(n).toLocaleString('vi-VN');
const rate=n=>Math.max(0,Math.min(100,num(n))).toLocaleString('vi-VN',{maximumFractionDigits:2})+'%';
const deadline=t=>num(t)>0?new Date(num(t)*1000).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'}):'00:00 thứ Hai';

function rows(list){
  return `<ol class="db-top-list">${list.map(r=>`<li${r.me?' class="is-me"':''}><span class="db-top-rank">${num(r.rank)===1?'👑':'#'+fmt(r.rank)}</span>
    <div class="db-top-person"><b>${esc(r.name||'Người chơi ẩn tên')}</b><small>${fmt(r.wins)}/${fmt(r.played)} trận thắng${r.title?` · ${esc(r.title)}`:''}</small></div>
    <div class="db-top-score"><strong>${rate(r.rate)}</strong><small>${fmt(r.reward)} xu</small></div></li>`).join('')}</ol>`;
}

export function barkCompetition(c){
  if(!c)return '<p class="db-sub">Chưa tải được bảng top tuần. Mở lại sảnh để thử lại.</p>';
  const me=c.me,prizes=c.prizes||[],top=c.rows||[];
  let progress='Đăng nhập để theo dõi thứ hạng của bạn.';
  if(me){
    progress=me.visible===false?'Bạn đang ẩn tên. Bật hiện tên trong Bảng xếp hạng để đua giải.':
      num(me.played)===0?'Chưa có trận hợp lệ trong tuần. Chơi kéo co để có tỷ lệ thắng và lên top.':
      me.rank?`Hạng ${fmt(me.rank)} · ${rate(me.rate)} thắng · ${fmt(me.wins)}/${fmt(me.played)} trận.`:'Đã đủ điều kiện · '+rate(me.rate)+' thắng · '+fmt(me.wins)+'/'+fmt(me.played)+' trận.';
    if(me.visible===false||num(me.played)===0)progress=`${rate(me.rate)} thắng · ${fmt(me.wins)}/${fmt(me.played)} trận. `+progress;
  }
  return `<details class="db-card db-competition" data-db-disclosure="top"><summary><span>🏆 Đua top tuần<small>Giải nhất ${fmt(prizes[0]?.coins)} xu</small></span><span class="db-top-arrow" aria-hidden="true">⌄</span></summary>
    <p class="db-top-me">${progress}</p>
    <p class="db-sub">Chốt ${esc(deadline(c.ends))} (giờ Việt Nam) · Xếp hạng theo tỷ lệ thắng, không yêu cầu số trận tối thiểu.</p>
    ${top.length?rows(top):`<p class="db-top-empty">Chưa có trận hợp lệ trên bảng top. Tuần này đang chờ nhà vô địch!</p>`}
    <details class="db-top-rules" data-db-disclosure="rules"><summary>Giải thưởng & cách tính</summary>
      <ul>${prizes.map(p=>`<li>Top ${fmt(p.rank)}: <b>${fmt(p.coins)} xu</b> · ${esc(p.title)}</li>`).join('')}</ul>
      <p>Tỷ lệ thắng = số thắng / tổng trận, tính cả đối thủ người chơi và chó nhà Mây. Hòa tính vào tổng trận; trận hủy hoặc hoàn cược vì chưa bắt đầu không tính. Chỉ tính các trận thực sự bắt đầu từ bản cập nhật giải tuần.</p>
      <p>Bằng tỷ lệ: nhiều trận thắng hơn, rồi đạt kết quả sớm hơn. Tên đang hiện trên bảng xếp hạng mới được đua giải. Tiền và danh hiệu được trao một lần sau khi chốt tuần, nhận khi vào game.</p>
    </details>
    ${c.previous?`<details class="db-top-rules" data-db-disclosure="previous"><summary>Kết quả tuần trước · ${esc(c.previous.week)}</summary>${c.previous.rows?.length?rows(c.previous.rows):'<p>Tuần trước chưa có người đủ điều kiện nhận giải.</p>'}</details>`:''}
  </details>`;
}
