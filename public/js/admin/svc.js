/** "🛎️ Phố dịch vụ" of the operator site (game/service_market.py admin_view / admin_act).
 *  GET  /api/admin/svc       buyers' reports (open first) with both players and the order, and the market's totals
 *                            (deals, xu traded, xu burned by the 5 % fee, xu in escrow, listings)
 *  POST /api/admin/svc       {op: 'close', order, note}: the operator closes a report with a note. Nothing automatic:
 *                            no refund, no fine, no ban from here (owner 21/10 "no auto-punish"). */
import {esc,hm,num,toast,tag} from './ui.js';

export class SvcAdmin{
  constructor(api,hooks){this.api=api;this.hooks=hooks;this.data=null;this.busy=false;this.error=null;}
  reset(){this.data=null;this.error=null;}
  load(){
    if(this.busy)return;this.busy=true;this.error=null;
    this.api.get('/api/admin/svc',20000).then(d=>{this.data=d;})
      .catch(e=>{if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}this.error=e.message;})
      .finally(()=>{this.busy=false;this.hooks.rerender();});
  }
  meta(){const d=this.data;if(!d)return 'Người chơi phục vụ người chơi';const n=d.flags.filter(f=>f.status==='open').length;return `${num(d.totals.deals)} đơn xong · đã đốt ${num(d.totals.burned)} xu${n?` · ${num(n)} báo cáo mở`:''}`;}
  view(){
    if(!this.data&&!this.busy&&!this.error)this.load();
    if(this.error&&!this.data)return `<div class="notice bad"><div>${esc(this.error)}<br><button type="button" class="btn ghost sm" data-act="svcReload">Thử lại</button></div></div>`;
    if(!this.data)return '<p class="note">Đang tải…</p>';
    const t=this.data.totals,R=this.data.rules;
    const who=p=>`${esc(p?.name||'—')}${p?.code?` <small class="muted">${esc(p.code)}</small>`:''}`;
    const row=f=>`<div class="gift-user"><div class="grow"><b>${esc(f.info?.name||f.order)}</b> <small class="muted">${num(f.info?.price||0)} xu · ${esc(f.info?.status||'')}${f.src==='wo'?' · đơn chỗ làm':''} · ${hm(f.at)}</small>`+
      `<br><small>Khách: ${who(f.buyer)} → Người bán: ${who(f.provider)}</small><br>“${esc(f.text)}”<br>${tag(f.status==='open'?'đang mở':'đã đóng',f.status==='open'?'bad':'good')}${f.note?` <small class="muted">${esc(f.note)}</small>`:''}</div>`+
      `${f.status==='open'?`<button type="button" class="btn ghost sm" data-act="svcClose" data-order="${esc(f.order)}">✔︎ Đóng</button>`:''}</div>`;
    return `<div class="gift-admin${this.busy?' is-busy':''}"><section class="card"><div class="card-head"><h2>Tổng</h2></div>`+
      `<p>${num(t.deals)} đơn xong · ${num(t.xu)} xu giao dịch · <b>${num(t.burned)} xu đã đốt</b> (phí ${R.fee_pct}%) · ${num(t.open)} đơn đang giữ ${num(t.escrow)} xu · ${num(t.listings)} dịch vụ đang mở</p>`+
      `<p class="note">Luật: giá người chơi ×${R.default_mult} (người bán chọn ×${R.mult_min}–×${R.mult_max} hoặc thương lượng, tối đa ${R.max_rounds} lượt), một đơn tối đa ${num(R.max_price)} xu, mỗi cặp ${R.pair_day} đơn/ngày và ${num(R.pair_week_xu)} xu/tuần, cùng mạng không giao dịch (vợ chồng được), tài khoản dưới ${R.new_days} ngày chung trần chuyển khoản.</p></section>`+
      `<section class="card"><div class="card-head"><h2>Báo cáo <small>${num(this.data.flags.length)}</small></h2></div>${this.data.flags.map(row).join('')||'<p class="note">Chưa có báo cáo nào.</p>'}`+
      `<p class="note">Khách báo cáo trong ${R.flag_hours} giờ sau khi giao. Không tự động hoàn tiền hay phạt ai: xem rồi đóng kèm ghi chú.</p></section></div>`;
  }
  /** true when the click was ours */
  async action(act,data){
    if(act==='svcReload'){this.reset();this.hooks.rerender();return true;}
    if(act!=='svcClose')return false;
    const note=prompt('Ghi chú khi đóng báo cáo:','');if(note===null)return true;
    try{this.data=await this.api.post('/api/admin/svc',{op:'close',order:data.order,note});toast('Đã đóng.');this.hooks.rerender();}
    catch(e){if(e.status===403||e.status===401){this.hooks.forbidden(e);return true;}toast(e.message||'Chưa được.','bad');}
    return true;
  }
}
