/** "🎤 Phòng hát" of the operator site (game/karaoke.py admin_view / admin_act; the rooms: live/karaoke.py).
 *  GET  /api/admin/karaoke   open reports by target (🛟 'minor' first), banned songs, the public rooms
 *  POST /api/admin/karaoke   {act: skip | close | end_round, room} · {act: kick, pid} · {act: ban | unban, vid} ·
 *                            {act: mute, pid, minutes} · {act: keep, target}
 * Room acts reach the live service at once (NOTIFY); in a room an admin also has the same buttons under ⋯. */
import {esc,icon,hm,num,toast,tag} from './ui.js';

const REASON={spam:'Spam',rude:'Thô lỗ',private:'Riêng tư',scam:'Lừa đảo',other:'Khác',minor:'🛟 An toàn / trẻ vị thành niên'};

export class KaraAdmin{
  constructor(api,hooks){this.api=api;this.hooks=hooks;this.data=null;this.busy=false;this.error=null;}
  reset(){this.data=null;this.error=null;}
  load(){
    if(this.busy)return;this.busy=true;this.error=null;
    this.api.get('/api/admin/karaoke',20000).then(d=>{this.data=d;})
      .catch(e=>{if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}this.error=e.message;})
      .finally(()=>{this.busy=false;this.hooks.rerender();});
  }
  meta(){const d=this.data;return d?`${num(d.items.length)} mục bị báo cáo · ${num(d.banned.length)} bài bị cấm`:'Phòng hát: báo cáo, cấm bài, đóng phòng';}
  view(){
    if(!this.data&&!this.busy&&!this.error)this.load();
    if(this.error&&!this.data)return `<div class="notice bad">${icon('alert',16)}<div>${esc(this.error)}<br><button type="button" class="btn ghost sm" data-act="karaReload">Thử lại</button></div></div>`;
    if(!this.data)return '<p class="note">Đang tải…</p>';
    const d=this.data;
    const rooms=d.rooms.map(r=>`<div class="gift-user"><div class="grow"><b>${esc(r)}</b></div>${['skip','end_round','close'].map(a=>`<button type="button" class="btn ghost sm" data-act="kara" data-value="${a}" data-id="${esc(r)}">${{skip:'⏭ Bỏ bài',end_round:'🧩 Dừng đố',close:'🔒 Đóng 10 phút'}[a]}</button>`).join('')}</div>`).join('');
    const items=d.items.length?d.items.map(it=>this.item(it)).join(''):'<p class="note">Không có báo cáo nào chờ.</p>';
    const banned=d.banned.length?d.banned.map(b=>`<div class="gift-user"><div class="grow"><b>${esc(b.title||b.vid)}</b> <small class="muted">${esc(b.vid)} · ${esc(b.by)} · ${hm(b.at)}</small></div><button type="button" class="btn ghost sm" data-act="kara" data-value="unban" data-id="${esc(b.vid)}">Bỏ cấm</button></div>`).join(''):'<p class="note">Chưa cấm bài nào.</p>';
    return `<div class="gift-admin${this.busy?' is-busy':''}">
      <section class="card"><div class="card-head"><h2>Báo cáo <small>${num(d.items.length)}</small></h2></div>${items}</section>
      <section class="card"><div class="card-head"><h2>Phòng công khai</h2></div>${rooms}<p class="note">Mời ra: 1 giờ mọi phòng. Khóa chat: dùng chung với tab Chat.</p></section>
      <section class="card"><div class="card-head"><h2>Bài bị cấm <small>${num(d.banned.length)}</small></h2></div>${banned}</section></div>`;
  }
  item(it){
    const reasons=Object.entries(it.reasons).map(([k,n])=>tag(`${REASON[k]||k} × ${n}`,k==='minor'?'bad':'')).join(' ');
    const what=it.kind==='v'?`🎵 <b>${esc(it.title||it.ref)}</b> <small class="muted">${esc(it.ref)}${it.banned?' · đã cấm':''}</small>`:`👤 <b>${esc(it.name||it.ref)}</b> <small class="muted">${esc(it.ref)}</small>`;
    const msgs=(it.msgs||[]).map(m=>`<li><small class="muted">${hm(m.at)} ${esc(m.ch)}</small> ${esc(m.text)}</li>`).join('');
    const acts=it.kind==='v'?`<button type="button" class="btn primary sm" data-act="kara" data-value="ban" data-id="${esc(it.ref)}">🚫 Cấm bài</button>`:
      `<button type="button" class="btn primary sm" data-act="kara" data-value="mute" data-id="${esc(it.ref)}">🔇 Khóa 1 giờ</button><button type="button" class="btn ghost sm" data-act="kara" data-value="kick" data-id="${esc(it.ref)}">🚪 Mời ra</button>`;
    return `<div class="gift-user${it.safety?' safety':''}"><div class="grow">${what}<br>${reasons}${msgs?`<ul class="kara-msgs">${msgs}</ul>`:''}</div>${acts}<button type="button" class="btn ghost sm" data-act="kara" data-value="keep" data-id="${esc(it.target)}">Bỏ qua</button></div>`;
  }
  /** true when the click was ours */
  async action(act,data){
    if(act==='karaReload'){this.reset();this.hooks.rerender();return true;}
    if(act!=='kara')return false;
    const a=data.value,id=data.id,body={act:a};
    if(['skip','close','end_round'].includes(a))body.room=id;else if(['ban','unban'].includes(a))body.vid=id;else if(a==='keep')body.target=id;else body.pid=id;
    if(a==='mute')body.minutes=60;
    if(['close','ban','mute','kick'].includes(a)&&!confirm('Chắc chắn?'))return true;
    try{await this.api.post('/api/admin/karaoke',body);toast('Đã xong.');this.reset();this.hooks.rerender();}
    catch(e){if(e.status===403||e.status===401){this.hooks.forbidden(e);return true;}toast(e.message||'Chưa được.','bad');}
    return true;
  }
}
