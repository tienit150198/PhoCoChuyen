/** "🎃 Halloween" of the operator site (game/halloween.py admin_view; the plan: docs/HALLOWEEN_2026.md).
 *  GET /api/admin/halloween   the season's state, totals (players, candy earned / in hand, xu bags paid), candy by kind,
 *                             the board's top 30 with each account's age, the xu bags newest first with how many accounts
 *                             took one from the same network (only a keyed hash of it is stored).
 * Read only. Kill switch: MNL_HALLOWEEN_OFF=1 (nothing earned or exchanged; rows kept). */
import {esc,hm,num,tag,utcText} from './ui.js';

const STATE={before:['chưa mở',''],open:['đang diễn ra','good'],grace:['ngày đổi kẹo','good'],over:['đã khép','bad'],off:['TẮT (MNL_HALLOWEEN_OFF)','bad']};
const KIND={checkin:'Điểm danh',pump:'Bí ngô đúng',miss:'Bí ngô sai',knock:'Gõ cửa (khách)',host:'Chủ nhà được',giant:'Bí ngô khổng lồ',buy:'Đổi quà',swap:'Đổi xu',final:'Chốt bảng'};

export class HalloweenAdmin{
  constructor(api,hooks){this.api=api;this.hooks=hooks;this.data=null;this.busy=false;this.error=null;}
  reset(){this.data=null;this.error=null;}
  load(){
    if(this.busy)return;this.busy=true;this.error=null;
    this.api.get('/api/admin/halloween',20000).then(d=>{this.data=d;})
      .catch(e=>{if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}this.error=e.message;})
      .finally(()=>{this.busy=false;this.hooks.rerender();});
  }
  meta(){
    const d=this.data;if(!d)return 'Lễ hội Ma Phố 26–31/10, kẹo và quà';
    const t=d.totals;
    return `${(STATE[d.off?'off':d.state]||[d.state])[0]} · ${num(t.players)} người chơi · ${num(t.earned)} kẹo kiếm · ${num(t.swaps)} túi xu (${num(t.xu)} xu)`;
  }
  view(){
    if(!this.data&&!this.busy&&!this.error)this.load();
    if(this.error&&!this.data)return `<div class="notice bad"><div>${esc(this.error)}<br><button type="button" class="btn ghost sm" data-act="hwReload">Thử lại</button></div></div>`;
    if(!this.data)return '<p class="note">Đang tải…</p>';
    const d=this.data,t=d.totals,[label,tone]=STATE[d.off?'off':d.state]||[d.state,''];
    const age=(c,at)=>{const made=utcText(c),a=made?Math.max(0,(at-made)/86400):null;return a==null?'—':a<1?'<b>dưới 1 ngày</b>':num(a)+' ngày';};
    const now=Date.now()/1000;
    const kinds=Object.entries(d.kinds||{}).map(([k,v])=>`<tr><td>${esc(KIND[k]||k)}</td><td>${num(v.n)}</td><td>${num(v.candy)}</td></tr>`).join('');
    const top=d.top.map(r=>`<tr><td>${num(r.rank)}</td><td>@${esc(r.username||'?')}</td><td>${num(r.earned)}</td><td>${num(r.candy)}</td><td>${age(r.created,now)}</td></tr>`).join('');
    const swaps=d.swaps.map(r=>`<tr><td>${hm(r.at)}</td><td>@${esc(r.username||'?')}</td><td>${age(r.created,r.at)}</td><td>${r.same_ip>1?`<b>${num(r.same_ip)}</b>`:'1'}</td></tr>`).join('');
    return `<div class="gift-admin${this.busy?' is-busy':''}">`+
      `<section class="card"><div class="card-head"><h2>Tổng</h2></div><p>${tag(label,tone)} Kiếm kẹo từ ${hm(d.starts)} tới ${hm(d.ends)}, đổi quà tới ${hm(d.until)}; Đêm hội hóa trang từ ${hm(d.night)}.</p>`+
      `<p>${num(t.players)} người có kẹo · ${num(t.earned)} kẹo đã kiếm · ${num(t.candy)} kẹo còn trong túi · ${num(t.swaps)} túi xu = ${num(t.xu)} xu đã ra</p>`+
      `<p class="note">Trần: điểm danh 10/ngày, 5 bí ngô × 5, 10 lượt gõ cửa × 4 (ghẹo 1), chủ nhà 2/khách tối đa 15 khách/ngày, đêm 31/10 ×2 + bí ngô khổng lồ 30. Túi xu 20.000 tối đa 3 lần/tài khoản (tài khoản ≥ 3 ngày, ngày sống ≥ 3, ≤ 3 tài khoản/mạng). Tắt: MNL_HALLOWEEN_OFF=1.</p></section>`+
      `<section class="card"><div class="card-head"><h2>Kẹo theo loại</h2></div><div class="scroll"><table class="tbl"><thead><tr><th>Loại</th><th>Lượt</th><th>Kẹo</th></tr></thead><tbody>${kinds||'<tr><td colspan="3" class="muted">Chưa có.</td></tr>'}</tbody></table></div></section>`+
      `<section class="card"><div class="card-head"><h2>Bảng kẹo <small>top ${num(d.top.length)}</small></h2></div><div class="scroll"><table class="tbl"><thead><tr><th>#</th><th>Tài khoản</th><th>Đã kiếm</th><th>Còn</th><th>Tuổi tài khoản</th></tr></thead><tbody>${top||'<tr><td colspan="5" class="muted">Chưa ai có kẹo.</td></tr>'}</tbody></table></div>`+
      `<p class="note">Top 10 nhận danh hiệu tự động lúc 0:00 ngày 01/11 (một lần).</p></section>`+
      `<section class="card"><div class="card-head"><h2>Túi xu đã đổi <small>${num(d.swaps.length)}</small></h2></div><div class="scroll"><table class="tbl"><thead><tr><th>Lúc</th><th>Tài khoản</th><th>Tuổi tài khoản</th><th>Cùng mạng</th></tr></thead><tbody>${swaps||'<tr><td colspan="4" class="muted">Chưa ai đổi.</td></tr>'}</tbody></table></div>`+
      `<p class="note">"Cùng mạng": số tài khoản đã đổi túi xu từ cùng một mạng (chỉ lưu mã băm). Nhiều tài khoản mới cùng mạng là dấu hiệu nick phụ.</p></section></div>`;
  }
  /** true when the click was ours */
  async action(act){
    if(act!=='hwReload')return false;
    this.reset();this.hooks.rerender();return true;
  }
}
