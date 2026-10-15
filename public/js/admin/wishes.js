/** "🌳 Ước nguyện" of the operator site (game/chua_wish.py admin_view / admin_act).
 *  GET  /api/admin/wishes   wishes reported and not looked at yet first, then the newest (the original when the mask changed it)
 *  POST /api/admin/wishes   {act: 'hide' | 'show', id}: hide = nobody sees it again; show = back on its tree (never deleted)
 * Three players' reports hide a wish by themselves until an admin looks. Kill switch for new wishes: MNL_WISH_OFF=1. */
import {esc,hm,num,toast,tag} from './ui.js';

const STATUS={live:['đang treo','good'],hidden:['ẩn vì báo cáo','bad'],removed:['đã gỡ','bad'],down:['người viết tự gỡ','']};
const REASON={rude:'khó nghe',spam:'spam',private:'lộ thông tin',scam:'lừa đảo',other:'khác'};

export class WishAdmin{
  constructor(api,hooks){this.api=api;this.hooks=hooks;this.data=null;this.busy=false;this.error=null;}
  reset(){this.data=null;this.error=null;}
  load(){
    if(this.busy)return;this.busy=true;this.error=null;
    this.api.get('/api/admin/wishes',20000).then(d=>{this.data=d;})
      .catch(e=>{if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}this.error=e.message;})
      .finally(()=>{this.busy=false;this.hooks.rerender();});
  }
  meta(){const d=this.data;if(!d)return 'Điều ước người chơi treo ở chùa';const open=d.items.filter(x=>x.reports&&!x.reviewed).length+(d.cards||[]).filter(x=>x.reports&&!x.reviewed).length;return `${num(open)} điều ước / lời chúc bị báo cáo chờ xem${d.off?' · ĐANG TẮT TREO MỚI (MNL_WISH_OFF)':''}`;}
  view(){
    if(!this.data&&!this.busy&&!this.error)this.load();
    if(this.error&&!this.data)return `<div class="notice bad"><div>${esc(this.error)}<br><button type="button" class="btn ghost sm" data-act="wsReload">Thử lại</button></div></div>`;
    if(!this.data)return '<p class="note">Đang tải…</p>';
    const row=it=>{const [label,tone]=STATUS[it.status]||[it.status,''];
      const why=Object.entries(it.reasons||{}).map(([k,n])=>`${esc(REASON[k]||k)} ×${num(n)}`).join(', ');
      return `<div class="gift-user"><div class="grow"><b>${esc(it.tree_name)}</b> <small class="muted">${esc(it.name||'Ẩn danh')} · @${esc(it.username||'khách')} · ${hm(it.at)} · 🙏 ${num(it.prayers)}${it.reports?` · ⚑ ${num(it.reports)}${why?` (${why})`:''}`:''}</small><br>`+
        `${esc(it.text)}${it.raw?`<br><small class="muted">Gốc: ${esc(it.raw)}</small>`:''}<br>${tag(label+(it.by?' · '+esc(it.by):''),tone)}</div>`+
        `${it.status==='live'||it.status==='hidden'?`<button type="button" class="btn ghost sm" data-act="wsHide" data-id="${it.id}">🚫 Gỡ</button>`:''}`+
        `${it.status==='hidden'||it.status==='removed'?`<button type="button" class="btn ghost sm" data-act="wsShow" data-id="${it.id}">↩︎ Treo lại</button>`:''}</div>`;};
    const open=this.data.items.filter(x=>x.reports&&!x.reviewed),rest=this.data.items.filter(x=>!(x.reports&&!x.reviewed));
    return `<div class="gift-admin${this.busy?' is-busy':''}"><section class="card"><div class="card-head"><h2>Bị báo cáo, chờ xem <small>${num(open.length)}</small></h2></div>`+
      `${open.map(row).join('')||'<p class="note">Không có điều ước nào bị báo cáo.</p>'}</section>`+
      `<section class="card"><div class="card-head"><h2>Mới treo <small>${num(rest.length)}</small></h2></div>${rest.map(row).join('')||'<p class="note">Chưa có điều ước nào.</p>'}`+
      `<p class="note">Gỡ: không ai thấy điều ước đó nữa (dữ liệu vẫn giữ). Ba người báo cáo thì điều ước tự ẩn tới khi bạn xem.</p></section>${this.cardsView()}</div>`;
  }
  /** 📜 old lời chúc their owners shared (the old "Bảng chung"), hanging in the wish garden since 15/10: the same controls. */
  cardsView(){
    const cards=this.data.cards||[];
    const row=it=>{const [label,tone]=STATUS[it.status]||[it.status,''];
      const why=Object.entries(it.reasons||{}).map(([k,n])=>`${esc(REASON[k]||k)} ×${num(n)}`).join(', ');
      return `<div class="gift-user"><div class="grow"><b>📜 ${esc(it.tree_name)}</b> <small class="muted">@${esc(it.username||'khách')} · ngày ${num(it.day)} · 🙏 ${num(it.prayers)}${it.reports?` · ⚑ ${num(it.reports)}${why?` (${why})`:''}`:''}</small><br>`+
        `${esc(it.text)}<br>${tag(label+(it.by?' · '+esc(it.by):''),tone)}</div>`+
        `${it.status==='live'||it.status==='hidden'?`<button type="button" class="btn ghost sm" data-act="wsHide" data-card="${it.card}">🚫 Gỡ</button>`:''}`+
        `${it.status==='hidden'||it.status==='removed'?`<button type="button" class="btn ghost sm" data-act="wsShow" data-card="${it.card}">↩︎ Treo lại</button>`:''}</div>`;};
    return `<section class="card"><div class="card-head"><h2>📜 Lời chúc cũ người chơi chia sẻ <small>${num(cards.length)}</small></h2></div>${cards.map(row).join('')||'<p class="note">Chưa có lời chúc cũ nào được chia sẻ.</p>'}`+
      `<p class="note">Thẻ lời chúc cũ chủ thẻ đã chọn Công khai, giờ treo trong Vườn ước nguyện (bị báo cáo lên trước). Gỡ: không ai thấy nữa, kể cả khi chủ chia sẻ lại; thẻ vẫn nằm trong bản lưu của chủ.</p></section>`;
  }
  /** true when the click was ours */
  async action(act,data){
    if(act==='wsReload'){this.reset();this.hooks.rerender();return true;}
    if(act!=='wsHide'&&act!=='wsShow')return false;
    const card=data.card!==undefined;
    if(act==='wsHide'&&!confirm(card?'Gỡ lời chúc này khỏi vườn?':'Gỡ điều ước này khỏi cây?'))return true;
    try{await this.api.post('/api/admin/wishes',{act:act==='wsHide'?'hide':'show',...card?{card:Number(data.card)}:{id:Number(data.id)}});toast(act==='wsHide'?'Đã gỡ.':'Đã treo lại.');this.reset();this.hooks.rerender();}
    catch(e){if(e.status===403||e.status===401){this.hooks.forbidden(e);return true;}toast(e.message||'Chưa được.','bad');}
    return true;
  }
}
