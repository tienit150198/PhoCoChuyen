/** "🛎️ Phố dịch vụ" of the operator site (game/service_market.py admin_view / admin_act).
 *  GET  /api/admin/svc       buyers' reports (open first) with both players and the order, and the market's totals
 *                            (deals, xu traded, xu burned by the 5 % fee, xu in escrow, listings)
 *  POST /api/admin/svc       {op: 'close', order, note}: the operator closes a report with a note. Nothing automatic:
 *                            no refund, no fine, no ban from here (owner 21/10 "no auto-punish").
 *  GET  /api/admin/townfair  🎪 Hội chợ việc làm (game/town_fair.py): its status, the switches and the last fairs
 *  POST /api/admin/townfair  {op: 'weekly', on} | {op: 'open_now', hours} | {op: 'close_special'}. MNL_FAIR_OFF stops it all. */
import {esc,hm,num,toast,tag} from './ui.js';

export class SvcAdmin{
  constructor(api,hooks){this.api=api;this.hooks=hooks;this.data=null;this.fair=null;this.busy=false;this.error=null;}
  reset(){this.data=null;this.fair=null;this.error=null;}
  load(){
    if(this.busy)return;this.busy=true;this.error=null;
    this.api.get('/api/admin/townfair',20000).then(f=>{this.fair=f;}).catch(()=>{this.fair=null;}).finally(()=>this.hooks.rerender());
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
      `<p class="note">Khách báo cáo trong ${R.flag_hours} giờ sau khi giao. Không tự động hoàn tiền hay phạt ai: xem rồi đóng kèm ghi chú.</p></section>${this.fairView()}</div>`;
  }
  /** 🎪 Hội chợ việc làm: weekly Saturday 14:00–17:00, a one-off fair now, the last fairs */
  fairView(){
    const f=this.fair;if(!f)return '';
    const st={open:'đang mở',soon:'sắp mở',closed:'chưa tới giờ',off:'tắt bằng MNL_FAIR_OFF'}[f.fair.state]||f.fair.state;
    const ev=e=>`<div class="gift-user"><div class="grow"><b>${esc(e.id)}</b> <small class="muted">${hm(e.starts)} → ${hm(e.ends)} · ${e.kind==='special'?'đặc biệt':'hằng tuần'}</small><br><small>${num(e.booths)} gian · ${num(e.stamps)} tem · ${num(e.rewards)} quà đã đổi</small> ${tag(e.status==='final'?'đã chốt':'đang mở',e.status==='final'?'good':'warn')}</div></div>`;
    return `<section class="card"><div class="card-head"><h2>🎪 Hội chợ việc làm</h2></div>`+
      `<p>Trạng thái: <b>${esc(st)}</b>${f.fair.starts?` · ${hm(f.fair.starts)} → ${hm(f.fair.ends)}`:''} · lịch hằng tuần (thứ Bảy 14:00–17:00): <b>${f.weekly?'bật':'tắt'}</b>${f.special?` · đặc biệt tới ${hm(f.special.ends)}`:''}</p>`+
      `<div class="row"><button type="button" class="btn ghost sm" data-act="tfWeekly" data-on="${f.weekly?'0':'1'}">${f.weekly?'Tắt lịch hằng tuần':'Bật lịch hằng tuần'}</button>`+
      `${f.fair.state==='open'?'':'<button type="button" class="btn ghost sm" data-act="tfOpen">Mở hội chợ ngay…</button>'}${f.special&&f.special.ends*1000>Date.now()?'<button type="button" class="btn ghost sm" data-act="tfClose">Đóng hội chợ đặc biệt</button>':''}</div>`+
      `${(f.events||[]).map(ev).join('')||'<p class="note">Chưa có kỳ nào.</p>'}<p class="note">Giảm ${f.rules.pcts[0]}–${f.rules.pcts[f.rules.pcts.length-1]}% trên giá Phố dịch vụ của chính người bán, không dưới giá gốc. Quà chỉ là danh hiệu / khung. Bảng chốt sau ${f.rules.settle_hours} giờ.</p></section>`;
  }
  /** true when the click was ours */
  async action(act,data){
    if(act==='svcReload'){this.reset();this.hooks.rerender();return true;}
    if(act==='tfWeekly'||act==='tfOpen'||act==='tfClose'){
      let body;
      if(act==='tfWeekly')body={op:'weekly',on:data.on==='1'};
      else if(act==='tfClose'){if(!confirm('Đóng hội chợ đặc biệt ngay?'))return true;body={op:'close_special'};}
      else{const h=prompt('Mở hội chợ trong mấy giờ? (1–6)','2');if(h===null)return true;body={op:'open_now',hours:Number(h)};}
      try{this.fair=await this.api.post('/api/admin/townfair',body);toast('Đã lưu.');this.hooks.rerender();}
      catch(e){if(e.status===403||e.status===401){this.hooks.forbidden(e);return true;}toast(e.message||'Chưa được.','bad');}
      return true;
    }
    if(act!=='svcClose')return false;
    const note=prompt('Ghi chú khi đóng báo cáo:','');if(note===null)return true;
    try{this.data=await this.api.post('/api/admin/svc',{op:'close',order:data.order,note});toast('Đã đóng.');this.hooks.rerender();}
    catch(e){if(e.status===403||e.status===401){this.hooks.forbidden(e);return true;}toast(e.message||'Chưa được.','bad');}
    return true;
  }
}
