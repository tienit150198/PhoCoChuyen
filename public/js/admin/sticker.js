/** "🎨 Sticker" of the operator site (game/sticker_event.py admin_view / admin_act): the contest entries of /sticker.
 *  GET  /api/admin/sticker   every entry (newest first, thumbnails by URL), the reward rows and their gift status
 *  POST /api/admin/sticker   {act: 'reject' | 'restore', id} · {act: 'rank', id, rank: 1..10 | null} · {act: 'award'}
 *                            · {act: 'revoke', gift}: a sticker reward whose gift is still pending
 * Ranks come from the Facebook group's reactions, set here by hand; "Trao giải" (after the deadline) queues each ranked
 * entry's prize once and locks its rank. Same IP tag / same image across accounts are flagged for the clone rings. */
import {esc,hm,num,toast,tag} from './ui.js';

const ST={live:['đang thi','good'],rejected:['bị loại','bad']};
const GIFT={pending:['chờ người chơi vào phố','warn'],applied:['đã vào ví','good'],seen:['đã vào ví','good'],revoked:['đã thu hồi','bad']};
const FILTERS=[['all','Tất cả'],['live','Đang thi'],['ranked','Có hạng'],['rejected','Bị loại'],['flag','Cần xem']];

export class StickerAdmin{
  constructor(api,hooks){this.api=api;this.hooks=hooks;this.data=null;this.busy=false;this.error=null;this.filter='all';}
  reset(){this.data=null;this.error=null;}
  load(){
    if(this.busy)return;this.busy=true;this.error=null;
    this.api.get('/api/admin/sticker',30000).then(d=>{this.data=d;})
      .catch(e=>{if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}this.error=e.message;})
      .finally(()=>{this.busy=false;this.hooks.rerender();});
  }
  meta(){const d=this.data;if(!d)return 'Cuộc thi làm sticker (/sticker)';return `${num(d.total)} sticker · ${num(d.people)} người · ${d.open?'đang nhận bài':'đã đóng'}${d.awarded?' · đã trao giải':''}`;}
  reward(w,label){
    if(!w)return '';
    const [g,tone]=w.status==='revoked'?GIFT.revoked:GIFT[w.gift]||[w.gift||'?',''];
    return `<small>${label} ${num(w.coins)} xu: ${tag(g,tone)}${w.status!=='revoked'&&w.gift==='pending'?` <button type="button" class="btn ghost sm" data-act="stkRevoke" data-gift="${esc(w.id)}">Thu hồi</button>`:''}</small>`;
  }
  view(){
    if(!this.data&&!this.busy&&!this.error)this.load();
    if(this.error&&!this.data)return `<div class="notice bad"><div>${esc(this.error)}<br><button type="button" class="btn ghost sm" data-act="stkReload">Thử lại</button></div></div>`;
    if(!this.data)return '<p class="note">Đang tải…</p>';
    const d=this.data,flag=it=>it.same_ip>1||it.same_image>1;
    const pick={all:()=>true,live:it=>it.status==='live',ranked:it=>it.rank,rejected:it=>it.status==='rejected',flag}[this.filter]||(()=>true);
    const items=d.items.filter(pick);
    const ranked=d.items.filter(it=>it.rank).sort((a,b)=>a.rank-b.rank);
    const prize=r=>d.by_rank?.[r];
    const head=`<section class="card"><div class="card-head"><h2>Bảng xếp hạng <small>${num(ranked.length)}/10</small></h2></div>`+
      (ranked.length?`<ol class="stk-ranks">${ranked.map(it=>`<li><b>#${it.rank}</b> @${esc(it.username)} <small class="muted">bài #${it.id} · ${num(prize(it.rank)||0)} xu${it.prize?` · ${tag('đã trao','good')}`:''}</small></li>`).join('')}</ol>`:'<p class="note">Chưa xếp hạng bài nào. Xếp theo lượt thả cảm xúc trong nhóm Facebook, ở nút “Hạng” của từng bài.</p>')+
      `<p class="note">Hạn nộp: ${esc(hm(d.rules.end))}. ${d.open?'Trao giải mở sau hạn nộp.':'Đã hết hạn nộp.'} Mỗi tài khoản một hạng; đã trao thì hạng khóa lại.</p>`+
      `<button type="button" class="btn primary sm" data-act="stkAward"${d.open||!ranked.some(it=>!it.prize&&it.status==='live')?' disabled':''}>🏆 Trao giải</button></section>`;
    const chips=`<div class="chips">${FILTERS.map(([k,l])=>`<button type="button" class="chip${this.filter===k?' on':''}" data-act="stkFilter" data-value="${k}" aria-pressed="${this.filter===k}">${l}</button>`).join('')}</div>`;
    const row=it=>{const [label,tone]=ST[it.status]||[it.status,''];
      return `<div class="gift-user stk-row"><a href="${esc(it.img)}" target="_blank" rel="noopener" class="stk-thumb" title="Xem ảnh gốc"><img src="${esc(it.thumb)}" alt="Sticker #${it.id}" width="96" height="96" loading="lazy"></a>`+
        `<div class="grow"><b>#${it.id} · @${esc(it.username)}</b> <small class="muted">${esc(it.display)} · ${hm(it.created)} · ngày ${num(it.life_day)} ở phố · tài khoản từ ${esc(String(it.account_at||'').slice(0,10))} · ${num(Math.round(it.size/1024))} KB</small><br>`+
        `${tag(label+(it.by?' · '+esc(it.by):''),tone)}${it.rank?' '+tag('🏆 hạng '+it.rank,'good'):''}${it.same_ip>1?' '+tag(`⚠ ${it.same_ip} tài khoản cùng IP ${esc(it.ip)}`,'warn'):''}${it.same_image>1?' '+tag(`⚠ ảnh trùng ${it.same_image} tài khoản`,'warn'):''}${it.note?` <small class="muted">“${esc(it.note)}”</small>`:''}<br>`+
        `${this.reward(it.join,'Quà tham gia')}${it.prize?'<br>'+this.reward(it.prize,'Giải'):''}</div>`+
        `<div class="stk-acts">${it.status==='live'?`<button type="button" class="btn ghost sm" data-act="stkRank" data-id="${it.id}" data-rank="${it.rank||''}"${it.prize?' disabled':''}>Hạng</button><button type="button" class="btn ghost sm" data-act="stkReject" data-id="${it.id}"${it.prize?' disabled':''}>🚫 Loại</button>`:`<button type="button" class="btn ghost sm" data-act="stkRestore" data-id="${it.id}">↩︎ Nhận lại</button>`}</div></div>`;};
    return `<div class="gift-admin stk-admin${this.busy?' is-busy':''}">${head}<section class="card"><div class="card-head"><h2>Bài nộp <small>${num(items.length)}</small></h2></div>${chips}`+
      `${items.map(row).join('')||'<p class="note">Không có bài nào.</p>'}`+
      `<p class="note">Loại: bài không còn trong cuộc thi (vẫn tính vào 3 lượt nộp). Quà tham gia chưa vào ví thì thu hồi được; đã vào ví thì không. “Cần xem”: cùng IP hay cùng ảnh với tài khoản khác.</p></section></div>`;
  }
  async post(body,ok){
    try{const r=await this.api.post('/api/admin/sticker',body);toast(ok(r));this.reset();this.hooks.rerender();}
    catch(e){if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}toast(e.message||'Chưa được.','bad');}
  }
  /** true when the click was ours */
  async action(act,data){
    if(!act||!act.startsWith('stk'))return false;
    if(act==='stkReload'){this.reset();this.hooks.rerender();return true;}
    if(act==='stkFilter'){this.filter=data.value||'all';this.hooks.rerender();return true;}
    const id=Number(data.id);
    if(act==='stkReject'){const note=prompt('Loại bài này? Ghi lý do (không bắt buộc):','');if(note===null)return true;await this.post({act:'reject',id,note},()=>'Đã loại.');return true;}
    if(act==='stkRestore'){await this.post({act:'restore',id},()=>'Đã nhận lại bài.');return true;}
    if(act==='stkRank'){
      const v=prompt('Hạng của bài này (1–10). Để trống để bỏ hạng.',data.rank||'');if(v===null)return true;
      const rank=v.trim()===''?null:Number(v);
      if(rank!==null&&!(Number.isInteger(rank)&&rank>=1&&rank<=10)){toast('Hạng cần từ 1 đến 10.','bad');return true;}
      await this.post({act:'rank',id,rank},r=>r.rank?`Đã xếp hạng ${r.rank}.`:'Đã bỏ hạng.');return true;
    }
    if(act==='stkAward'){if(!confirm('Trao giải cho các bài đã xếp hạng? Xu vào ví người thắng khi họ vào phố, hạng sẽ khóa lại.'))return true;
      await this.post({act:'award'},r=>r.given.length?`Đã trao ${r.given.length} giải.`:'Không còn giải nào cần trao.');return true;}
    if(act==='stkRevoke'){if(!confirm('Thu hồi phần quà này? Người chơi sẽ không nhận được nữa.'))return true;
      await this.post({act:'revoke',gift:data.gift},()=>'Đã thu hồi.');return true;}
    return true;
  }
}
