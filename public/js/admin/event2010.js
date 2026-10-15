/** "💐 Thiệp 20/10" of the operator site (game/event2010.py admin_view / admin_act; the page is /2010).
 *  GET  /api/admin/2010   totals; cards reported and not looked at yet first, then the newest (the original when the mask
 *                         changed it); the reward log, newest first, with the account's age and how many rewards share an address
 *  POST /api/admin/2010   {act: 'hide' | 'show', id}: hide = the link stops opening (kept); show = it opens again
 * Three readers' reports hide a card by themselves until an admin looks. Kill switch for new cards and rewards: MNL_2010_OFF=1. */
import {esc,hm,num,toast,tag,utcText} from './ui.js';

const STATUS={live:['đang mở','good'],hidden:['ẩn vì báo cáo','bad'],removed:['đã gỡ','bad']};
const REASON={rude:'khó nghe',spam:'spam',private:'lộ thông tin',scam:'lừa đảo',other:'khác'};
const DIR={nam_nu:'nam → nữ',nu_nam:'nữ → nam',khac:'ai cũng được'};
const GIFT={pending:['chờ vào game nhận',''],applied:['đã vào ví','good'],seen:['đã vào ví','good'],gone:['không thấy quà','bad']};   // system_gifts.status

export class Ev2010Admin{
  constructor(api,hooks){this.api=api;this.hooks=hooks;this.data=null;this.busy=false;this.error=null;}
  reset(){this.data=null;this.error=null;}
  load(){
    if(this.busy)return;this.busy=true;this.error=null;
    this.api.get('/api/admin/2010',20000).then(d=>{this.data=d;})
      .catch(e=>{if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}this.error=e.message;})
      .finally(()=>{this.busy=false;this.hooks.rerender();});
  }
  meta(){
    const d=this.data;if(!d)return 'Thiệp người chơi gửi nhau, quà 100.000 xu';
    const open=d.items.filter(x=>x.reports&&!x.reviewed).length;
    return `${num(d.totals.cards)} thiệp · ${num(d.totals.rewards)} quà (${num(d.totals.coins)} xu) · ${num(open)} thiệp bị báo cáo chờ xem${d.open?'':' · ĐÃ ĐÓNG VIẾT'}`;
  }
  view(){
    if(!this.data&&!this.busy&&!this.error)this.load();
    if(this.error&&!this.data)return `<div class="notice bad"><div>${esc(this.error)}<br><button type="button" class="btn ghost sm" data-act="evReload">Thử lại</button></div></div>`;
    if(!this.data)return '<p class="note">Đang tải…</p>';
    const d=this.data,t=d.totals;
    const row=it=>{const [label,tone]=STATUS[it.status]||[it.status,''];
      const why=Object.entries(it.reasons||{}).map(([k,n])=>`${esc(REASON[k]||k)} ×${num(n)}`).join(', ');
      return `<div class="gift-user"><div class="grow"><b>Gửi ${esc(it.to)}</b> <small class="muted">${esc(it.sender)} · @${esc(it.username||'?')} · ${esc(it.theme_name)} · ${esc(DIR[it.direction]||it.direction)} · ${hm(it.at)} · ❤ ${num(it.hearts)}${it.reports?` · ⚑ ${num(it.reports)}${why?` (${why})`:''}`:''}</small><br>`+
        `${esc(it.text)}${it.raw?`<br><small class="muted">Gốc: ${esc(it.raw)}</small>`:''}<br>${tag(label+(it.by?' · '+esc(it.by):''),tone)} <a class="muted" href="/2010/c/${esc(it.id)}" target="_blank" rel="noopener">mở link</a></div>`+
        `${it.status!=='removed'?`<button type="button" class="btn ghost sm" data-act="evHide" data-id="${esc(it.id)}">🚫 Gỡ</button>`:''}`+
        `${it.status!=='live'?`<button type="button" class="btn ghost sm" data-act="evShow" data-id="${esc(it.id)}">↩︎ Mở lại</button>`:''}</div>`;};
    const open=d.items.filter(x=>x.reports&&!x.reviewed),rest=d.items.filter(x=>!(x.reports&&!x.reviewed));
    const reward=r=>{const [g,tone]=GIFT[r.gift]||[r.gift,''],made=utcText(r.account_created),age=made?Math.max(0,(r.at-made)/86400):null;
      return `<tr><td>${hm(r.at)}</td><td>@${esc(r.username)}</td><td>${num(r.life_day)}</td><td>${age==null?'—':age<1?'<b>dưới 1 ngày</b>':num(age)+' ngày'}</td>`+
        `<td>${r.same_ip>1?`<b>${num(r.same_ip)}</b>`:'1'}</td><td>${tag(g,tone)}</td><td><a href="/2010/c/${esc(r.card)}" target="_blank" rel="noopener">thiệp</a></td></tr>`;};
    return `<div class="gift-admin${this.busy?' is-busy':''}">`+
      `<section class="card"><div class="card-head"><h2>Tổng</h2></div><p>${num(t.cards)} thiệp từ ${num(t.people)} người · ❤ ${num(t.hearts)} · ${num(t.rewards)} người nhận quà, ${num(t.coins)} xu</p>`+
      `<p class="note">Viết và nhận quà ${d.open?'đang mở':'đã đóng'} tới ${hm(d.until)}; link đọc được tới ${hm(d.read_until)}. Quà ${num(d.coins)} xu một lần mỗi tài khoản, từ ngày sống ${num(d.min_life_day)}, tối đa ${num(d.per_ip)} quà một địa chỉ mạng, ${num(d.per_day)} thiệp một ngày.</p></section>`+
      `<section class="card"><div class="card-head"><h2>Bị báo cáo, chờ xem <small>${num(open.length)}</small></h2></div>${open.map(row).join('')||'<p class="note">Không có thiệp nào bị báo cáo.</p>'}</section>`+
      `<section class="card"><div class="card-head"><h2>Mới gửi <small>${num(rest.length)}</small></h2></div>${rest.map(row).join('')||'<p class="note">Chưa có thiệp nào.</p>'}`+
      `<p class="note">Gỡ: link không mở được nữa (dữ liệu vẫn giữ). Ba người báo cáo thì thiệp tự ẩn tới khi bạn xem. Thiệp người gửi tự xóa không hiện ở đây.</p></section>`+
      `<section class="card"><div class="card-head"><h2>Quà đã tặng <small>${num(d.rewards.length)}</small></h2></div>`+
      `<div class="scroll"><table class="tbl"><thead><tr><th>Lúc</th><th>Tài khoản</th><th>Ngày sống</th><th>Tuổi tài khoản</th><th>Cùng địa chỉ</th><th>Quà</th><th></th></tr></thead><tbody>${d.rewards.map(reward).join('')||'<tr><td colspan="7" class="muted">Chưa ai nhận.</td></tr>'}</tbody></table></div>`+
      `<p class="note">"Cùng địa chỉ": số quà đã phát cho cùng một địa chỉ mạng (chỉ lưu mã băm). Nhiều tài khoản mới tạo cùng một địa chỉ là dấu hiệu nick phụ.</p></section></div>`;
  }
  /** true when the click was ours */
  async action(act,data){
    if(act==='evReload'){this.reset();this.hooks.rerender();return true;}
    if(act!=='evHide'&&act!=='evShow')return false;
    if(act==='evHide'&&!confirm('Gỡ thiệp này? Link sẽ không mở được nữa.'))return true;
    try{await this.api.post('/api/admin/2010',{act:act==='evHide'?'hide':'show',id:String(data.id)});toast(act==='evHide'?'Đã gỡ.':'Đã mở lại.');this.reset();this.hooks.rerender();}
    catch(e){if(e.status===403||e.status===401){this.hooks.forbidden(e);return true;}toast(e.message||'Chưa được.','bad');}
    return true;
  }
}
