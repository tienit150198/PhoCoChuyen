/** "⚔️ Bang" of the operator site (game/bang.py admin_view / admin_act).
 *  GET  /api/admin/bang?q=   every bang (newest first): name, leader, members, fund, status, hidden
 *  POST /api/admin/bang      {op: 'hide' | 'show' | 'rename', id, name?}: an offensive name is hidden (it leaves the lists,
 *                            its members' tags go) or renamed (the same rules as a player name); never deleted.
 *                            {op: 'code_hide' | 'code_show', id, kind: 'pub' | 'in'}: 📜 hide or show one of its rules
 *                            texts (📢 công khai, 📜 nội bộ; game/bang_code.py): the text stays, logged in the bang. */
import {esc,hm,num,toast,tag} from './ui.js';

export class BangAdmin{
  constructor(api,hooks){this.api=api;this.hooks=hooks;this.data=null;this.busy=false;this.error=null;this.q='';}
  reset(){this.data=null;this.error=null;}
  load(){
    if(this.busy)return;this.busy=true;this.error=null;
    this.api.get('/api/admin/bang?q='+encodeURIComponent(this.q),20000).then(d=>{this.data=d;})
      .catch(e=>{if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}this.error=e.message;})
      .finally(()=>{this.busy=false;this.hooks.rerender();});
  }
  meta(){const d=this.data;if(!d)return 'Bang của người chơi';const n=d.bangs.filter(b=>b.status==='active').length,h=d.bangs.filter(b=>b.hidden).length;return `${num(n)} bang đang hoạt động${h?` · ${num(h)} đang ẩn`:''}`;}
  view(){
    if(!this.data&&!this.busy&&!this.error)this.load();
    if(this.error&&!this.data)return `<div class="notice bad"><div>${esc(this.error)}<br><button type="button" class="btn ghost sm" data-act="bgReload">Thử lại</button></div></div>`;
    if(!this.data)return '<p class="note">Đang tải…</p>';
    const KIND={pub:'📢 Nội quy công khai',in:'📜 Nội quy nội bộ'};
    const code=b=>['pub','in'].map(k=>{const c=b.code?.[k];if(!c?.text)return '';
      return `<div class="bg-adm-code"><small><b>${KIND[k]}</b> · bản ${num(c.ver)}${c.at?` · ${hm(c.at)}`:''}${c.hidden?` · ${tag('đang ẩn','bad')}${c.hidden_by?` bởi ${esc(c.hidden_by)}`:''}`:''}</small>`+
        `<pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:4px 0;font:inherit;font-size:.85rem${c.hidden?';opacity:.6':''}">${esc(c.text)}</pre>`+
        `<button type="button" class="btn ghost sm" data-act="${c.hidden?'bgCodeShow':'bgCodeHide'}" data-id="${esc(b.id)}" data-kind="${k}">${c.hidden?'↩︎ Hiện lại nội quy':'🚫 Ẩn nội quy này'}</button></div>`;}).join('');
    const row=b=>`<div class="gift-user"><div class="grow"><b>${esc(b.emoji)} ${esc(b.name)}</b> <small class="muted">${esc(b.leader)} · @${esc(b.user||'—')} · ${num(b.n)} người · quỹ ${num(b.fund)} xu · đã góp ${num(b.given)} · đã xây ${num(b.spent)}${b.burned?` · đốt ${num(b.burned)}`:''} · ${hm(b.created)}</small>`+
      `${b.motto?`<br><small>“${esc(b.motto)}”</small>`:''}<br>${tag(b.status==='active'?(b.hidden?'đang ẩn':'hoạt động'):'đã giải tán',b.hidden||b.status!=='active'?'bad':'good')}${b.note?` <small class="muted">${esc(b.note)}</small>`:''}${code(b)}</div>`+
      `${b.hidden?`<button type="button" class="btn ghost sm" data-act="bgShow" data-id="${esc(b.id)}">↩︎ Hiện lại</button>`:`<button type="button" class="btn ghost sm" data-act="bgHide" data-id="${esc(b.id)}">🚫 Ẩn</button>`}`+
      `<button type="button" class="btn ghost sm" data-act="bgRename" data-id="${esc(b.id)}" data-name="${esc(b.name)}">✏️ Đổi tên</button></div>`;
    return `<div class="gift-admin${this.busy?' is-busy':''}"><section class="card"><div class="card-head"><h2>Bang <small>${num(this.data.bangs.length)}</small></h2></div>`+
      `<div class="row" data-act-form="bgSearch"><input type="search" name="q" value="${esc(this.q)}" placeholder="Tìm tên bang" maxlength="30"><button type="button" class="btn ghost sm" data-act="bgSearch">Tìm</button></div>`+
      `${this.data.bangs.map(row).join('')||'<p class="note">Chưa có bang nào.</p>'}`+
      `<p class="note">Ẩn: bang rời danh sách và bảng xếp hạng, thẻ tên của thành viên biến mất (thành viên vẫn ở trong bang, không mất gì). Đổi tên: theo luật tên người chơi, không trùng. Ẩn nội quy: chữ vẫn giữ trong dữ liệu, người chơi không thấy nữa, người xin vào không cần đồng ý nội quy đã ẩn. Không bao giờ xóa dữ liệu; quỹ bang chỉ góp, không rút.</p></section></div>`;
  }
  /** true when the click was ours */
  async action(act,data){
    if(act==='bgReload'){this.reset();this.hooks.rerender();return true;}
    if(act==='bgSearch'){this.q=String(document.querySelector('[data-act-form="bgSearch"] input')?.value||'').slice(0,30);this.reset();this.hooks.rerender();return true;}
    if(!['bgHide','bgShow','bgRename','bgCodeHide','bgCodeShow'].includes(act))return false;
    let body;
    if(act==='bgCodeHide'||act==='bgCodeShow'){
      if(act==='bgCodeHide'&&!confirm('Ẩn nội quy này? Chữ vẫn được giữ, có thể hiện lại.'))return true;
      body={op:act==='bgCodeHide'?'code_hide':'code_show',id:data.id,kind:data.kind};
    }
    else if(act==='bgRename'){const name=prompt('Tên mới cho bang:',data.name||'');if(!name)return true;body={op:'rename',id:data.id,name};}
    else{if(act==='bgHide'&&!confirm('Ẩn bang này? Thành viên vẫn giữ mọi thứ.'))return true;body={op:act==='bgHide'?'hide':'show',id:data.id};}
    try{const d=await this.api.post('/api/admin/bang',body);this.data=d;toast(act==='bgHide'||act==='bgCodeHide'?'Đã ẩn.':act==='bgShow'||act==='bgCodeShow'?'Đã hiện lại.':'Đã đổi tên.');this.hooks.rerender();}
    catch(e){if(e.status===403||e.status===401){this.hooks.forbidden(e);return true;}toast(e.message||'Chưa được.','bad');}
    return true;
  }
}
