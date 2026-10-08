/** "💌 Thiệp cưới" of the operator site (game/wed_invite.py admin_view / admin_act).
 *  GET  /api/admin/wedinvite   the last 50 cards sent to the whole server (the original text when the chat's mask changed it)
 *  POST /api/admin/wedinvite   {act: 'delete', id}: the card is never shown again (no refund)
 * Kill switch for everything: MNL_WED_INVITE_OFF=1 on the game server. */
import {esc,hm,num,toast,tag} from './ui.js';

export class WedInviteAdmin{
  constructor(api,hooks){this.api=api;this.hooks=hooks;this.data=null;this.busy=false;this.error=null;}
  reset(){this.data=null;this.error=null;}
  load(){
    if(this.busy)return;this.busy=true;this.error=null;
    this.api.get('/api/admin/wedinvite',20000).then(d=>{this.data=d;})
      .catch(e=>{if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}this.error=e.message;})
      .finally(()=>{this.busy=false;this.hooks.rerender();});
  }
  meta(){const d=this.data;return d?`${num(d.items.filter(x=>x.status==='live').length)} thiệp đang hiện${d.off?' · ĐANG TẮT (MNL_WED_INVITE_OFF)':''}`:'Thiệp mời cưới gửi cả phố';}
  view(){
    if(!this.data&&!this.busy&&!this.error)this.load();
    if(this.error&&!this.data)return `<div class="notice bad"><div>${esc(this.error)}<br><button type="button" class="btn ghost sm" data-act="wiReload">Thử lại</button></div></div>`;
    if(!this.data)return '<p class="note">Đang tải…</p>';
    const rows=this.data.items.map(it=>`<div class="gift-user"><div class="grow"><b>${esc(it.a)} 💞 ${esc(it.b)}</b> <small class="muted">@${esc(it.username||'?')} · ${hm(it.at)} · ${it.party?'có tiệc':'thông báo'} · 🎉 ${num(it.cheers)}</small><br>`+
      `${esc(it.text)}${it.raw?`<br><small class="muted">Gốc: ${esc(it.raw)}</small>`:''}<br>${it.status==='live'?tag('đang hiện','good'):tag(`đã gỡ${it.by?' · '+esc(it.by):''}`,'bad')}</div>`+
      `${it.status==='live'?`<button type="button" class="btn ghost sm" data-act="wiDelete" data-id="${it.id}">🗑️ Gỡ thiệp</button>`:''}</div>`).join('');
    return `<div class="gift-admin${this.busy?' is-busy':''}"><section class="card"><div class="card-head"><h2>Thiệp mời cưới <small>${num(this.data.items.length)}</small></h2></div>`+
      `${rows||'<p class="note">Chưa có thiệp nào.</p>'}<p class="note">Gỡ thiệp: không ai thấy thiệp đó nữa, người gửi không được hoàn xu.</p></section></div>`;
  }
  /** true when the click was ours */
  async action(act,data){
    if(act==='wiReload'){this.reset();this.hooks.rerender();return true;}
    if(act!=='wiDelete')return false;
    if(!confirm('Gỡ thiệp này khỏi cả phố?'))return true;
    try{await this.api.post('/api/admin/wedinvite',{act:'delete',id:Number(data.id)});toast('Đã gỡ thiệp.');this.reset();this.hooks.rerender();}
    catch(e){if(e.status===403||e.status===401){this.hooks.forbidden(e);return true;}toast(e.message||'Chưa được.','bad');}
    return true;
  }
}
