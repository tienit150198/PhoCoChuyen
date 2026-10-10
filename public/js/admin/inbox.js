/** "Góp ý": the operator's feedback inbox on the standalone site. Same API as the in-game
 * inbox (public/js/v4/feedback.js): GET /api/admin/feedback?status&kind&before and
 * POST /api/admin/feedback {id, status?, reply?}. List + detail; on a phone the detail
 * replaces the list (with a back button). */
import {esc,icon,ago,stamp,num,KINDS,kindOf,STATUS,tag,toast} from './ui.js';

const REPLY_MAX=10000;   // owner 10/10 (game/player_feedback.py)
const STATUSES=[['new','Mới'],['seen','Đã xem'],['done','Xong']];
const CTX_LABEL={career:'Nghề',day:'Ngày trong nghề',life_day:'Ngày đời',view:'Màn hình',layout:'Bố cục',screen:'Kích thước',lang:'Ngôn ngữ',version:'Phiên bản',ua:'Trình duyệt'};
const LAYOUT={phone:'điện thoại',tablet:'máy tính bảng',desktop:'máy tính'};

export class Inbox{
  /** hooks: {rerender(), counts(counts), forbidden(error)} */
  constructor(api,hooks){this.api=api;this.hooks=hooks;this.filter={status:'new',kind:''};this.data=null;this.busy=false;this.error=null;this.sel=null;this.drafts={};this.saving=false;}

  load(more=false){
    if(this.busy)return;
    clearTimeout(this.timer);
    this.busy=true;this.error=null;
    const before=more?this.data?.next:null,ctl=this.ctl=new AbortController();
    this.api.inbox(this.filter,before,ctl.signal)
      .then(d=>{this.data=more&&this.data?{...d,items:[...this.data.items,...d.items]}:d;this.hooks.counts(d.counts);})
      .catch(e=>{if(e.aborted)return;if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}this.error=e.message;})
      .finally(()=>{if(this.ctl!==ctl)return;this.ctl=null;this.busy=false;this.hooks.rerender();});
  }
  /** Drop what is shown (and any request still running for it); view() loads again. */
  reset(){this.ctl?.abort();this.ctl=null;this.busy=false;clearTimeout(this.timer);this.data=null;this.sel=null;this.error=null;}
  /** Filter chips: the choice shows at once, the list loads once the clicking settles. */
  refilter(){
    this.reset();this.busy=true;
    this.timer=setTimeout(()=>{this.busy=false;this.load();},200);
    this.hooks.rerender();
  }
  get items(){return this.data?.items||[];}
  item(id){return this.items.find(x=>x.id===id);}

  /* ---- view -------------------------------------------------------------------- */
  view(){
    if(!this.data&&!this.busy&&!this.error)this.load();
    const d=this.data,counts=d?.counts||{},total=Object.values(counts).reduce((a,b)=>a+b,0);
    const statusSeg=[['','Tất cả',total],...STATUSES.map(([s,l])=>[s,l,counts[s]||0])].map(([s,l,n])=>
      `<button type="button" role="radio" aria-checked="${this.filter.status===s}" class="${this.filter.status===s?'on':''}" data-act="fbFilter" data-field="status" data-value="${s}">${l}<em>${d?num(n):'·'}</em></button>`).join('');
    const kindChips=[['','Mọi loại',''],...KINDS.map(([k,e,l])=>[k,l,e])].map(([k,l,e])=>
      `<button type="button" class="chip${this.filter.kind===k?' on':''}" aria-pressed="${this.filter.kind===k}" data-act="fbFilter" data-field="kind" data-value="${k}">${e?`<span aria-hidden="true">${e}</span> `:''}${l}</button>`).join('');
    const bar=`<div class="inbox-bar"><div class="seg" role="radiogroup" aria-label="Lọc theo trạng thái">${statusSeg}</div><div class="chips" role="group" aria-label="Lọc theo loại">${kindChips}</div></div>`;
    let list;
    if(this.error&&!d)list=`<div class="notice bad">${icon('alert',16)}<div>${esc(this.error)}<br><button type="button" class="btn ghost sm" data-act="fbReload">Thử lại</button></div></div>`;
    else if(!d)list=`<div class="loading" role="status">${icon('sparkle',22)}<p>Đang tải góp ý…</p></div>`;
    else if(!d.items.length)list=`<div class="empty">${icon('inbox',26)}<p>Không có góp ý nào ở mục này.</p></div>`;
    else list=`<ul class="fb-list" aria-label="Danh sách góp ý">${d.items.map(it=>this.row(it)).join('')}</ul>`+
      (d.next?`<div class="more-row"><button type="button" class="btn ghost sm" data-act="fbMore"${this.busy?' disabled':''}>${this.busy?'Đang tải…':'Xem thêm'}</button></div>`:
        `<p class="note center">Đã hiện hết ${num(d.items.length)} góp ý.</p>`);
    const it=this.sel!=null?this.item(this.sel):null;
    const detail=it?this.detail(it):`<div class="empty">${icon('eye',26)}<p>Chọn một góp ý để đọc và trả lời.</p></div>`;
    return `<div class="inbox${it?' has-sel':''}${this.busy&&d?' is-busy':''}">${bar}<div class="panes"><div class="pane-list">${list}</div><div class="pane-detail" aria-live="polite">${detail}</div></div></div>`;
  }
  row(it){
    const [,emo,label]=kindOf(it.kind),[st,tone]=STATUS[it.status]||STATUS.new;
    const who=it.account?`@${esc(it.account)}`:`khách #${esc(it.player)}`;
    const first=esc((it.text||'').split('\n')[0].slice(0,140));
    return `<li><button type="button" class="fb-row ${it.status}${this.sel===it.id?' on':''}" data-act="fbOpen" data-id="${it.id}" aria-current="${this.sel===it.id}">
      <span class="fb-kind" title="${esc(label)}" aria-label="${esc(label)}">${emo}</span>
      <span class="fb-main"><span class="fb-first">${first}</span><small>${who} · ${ago(it.created_at)} · #${it.id}${it.reply?` · ${icon('send',11)} đã đáp`:''}</small></span>
      ${tag(st,tone)}</button></li>`;
  }
  context(ctx){
    const rows=Object.entries(ctx||{}).map(([k,v])=>{
      const val=k==='career'?`${esc(this.api.career(v))} <small>(${esc(v)})</small>`:k==='layout'?esc(LAYOUT[v]||v):esc(v);
      return `<div><dt>${esc(CTX_LABEL[k]||k)}</dt><dd>${val}</dd></div>`;
    });
    return rows.length?`<dl class="kv kv2 ctx">${rows.join('')}</dl>`:'<p class="note">Không có ngữ cảnh.</p>';
  }
  detail(it){
    const [,emo,label]=kindOf(it.kind),[st,tone]=STATUS[it.status]||STATUS.new;
    const who=it.account?`tài khoản @${esc(it.account)}`:`khách #${esc(it.player)}`;
    const draft=this.drafts[it.id]??it.reply??'';
    const len=[...draft].length;
    return `<article class="fb-detail">
      <button type="button" class="btn ghost sm back" data-act="fbClose">${icon('back',15)} Danh sách</button>
      <header class="fb-dhead"><span class="fb-dkind"><span aria-hidden="true">${emo}</span> ${esc(label)}</span>${tag(st,tone)}<small>#${it.id}</small></header>
      <p class="fb-meta">${who} · gửi ${stamp(it.created_at)} (${ago(it.created_at)})${it.updated_at&&it.updated_at-it.created_at>1?` · cập nhật ${ago(it.updated_at)}`:''}</p>
      <div class="fb-text">${esc(it.text)}</div>
      <div class="fb-status" role="group" aria-label="Đổi trạng thái"><span class="fb-status-l">Trạng thái</span><div class="seg">${STATUSES.map(([s,l])=>
        `<button type="button" class="${it.status===s?'on':''}" aria-pressed="${it.status===s}" data-act="fbStatus" data-id="${it.id}" data-status="${s}"${this.saving?' disabled':''}>${it.status===s?icon('check',13):''}${l}</button>`).join('')}</div></div>
      <form class="fb-reply" data-form="reply" data-id="${it.id}">
        <label for="fb-reply-${it.id}">Lời đáp cho người chơi <small>(người chơi thấy ngay dưới góp ý của họ)</small></label>
        <textarea id="fb-reply-${it.id}" name="reply" rows="6" maxlength="${REPLY_MAX}" placeholder="Cảm ơn bạn, mình đã sửa trong bản tới…">${esc(draft)}</textarea>
        <div class="fb-reply-foot"><output class="count${len>REPLY_MAX-30?' near':''}" data-count>${len}/${REPLY_MAX}</output>
          ${it.reply?`<button type="button" class="btn ghost sm" data-act="fbClearReply" data-id="${it.id}"${this.saving?' disabled':''}>Xóa lời đáp</button>`:''}
          <button type="submit" class="btn primary sm"${this.saving?' disabled':''}>${icon('send',14)} ${it.reply?'Cập nhật lời đáp':'Gửi lời đáp'}</button></div>
        ${it.reply&&it.replied_at?`<p class="note">Đã đáp ${ago(it.replied_at)}.</p>`:''}
      </form>
      <h3 class="sub">Ngữ cảnh gửi kèm</h3>${this.context(it.context)}
    </article>`;
  }

  /* ---- actions -------------------------------------------------------------------- */
  patch(item){
    const i=this.items.findIndex(x=>x.id===item.id);if(i<0)return;
    const old=this.items[i].status,c=this.data.counts;
    if(old!==item.status&&c){c[old]=Math.max(0,(c[old]||0)-1);c[item.status]=(c[item.status]||0)+1;this.hooks.counts(c);}
    this.data.items[i]=item;
  }
  async save(body,okMessage){
    if(this.saving)return null;
    this.saving=true;this.hooks.rerender();
    try{const d=await this.api.update(body);this.patch(d.item);toast(okMessage,'good');return d.item;}
    catch(e){if(e.status===403||e.status===401){this.hooks.forbidden(e);return null;}toast(e.message,'bad');return null;}
    finally{this.saving=false;this.hooks.rerender();}
  }
  async action(act,data){
    switch(act){
      case'fbFilter':if(this.filter[data.field]===data.value)return true;this.filter[data.field]=data.value;this.refilter();return true;
      case'fbReload':this.reset();this.hooks.rerender();return true;
      case'fbMore':this.load(true);this.hooks.rerender();return true;
      case'fbOpen':this.sel=Number(data.id);if(this.item(this.sel)?.context?.career)this.api.loadNames().then(ok=>{if(ok)this.hooks.rerender();});this.hooks.rerender();document.querySelector('.pane-detail')?.scrollTo?.(0,0);if(matchMedia('(max-width: 899px)').matches)scrollTo(0,0);return true;
      case'fbClose':{const id=this.sel;this.sel=null;this.hooks.rerender();document.querySelector(`.fb-row[data-id="${id}"]`)?.focus();return true;}
      case'fbStatus':await this.save({id:Number(data.id),status:data.status},'Đã đổi trạng thái.');return true;
      case'fbClearReply':{const it=await this.save({id:Number(data.id),reply:''},'Đã xóa lời đáp.');if(it)delete this.drafts[it.id];return true;}
    }
    return false;
  }
  input(el){
    const form=el.closest('form[data-form="reply"]');if(!form)return false;
    this.drafts[Number(form.dataset.id)]=el.value;
    const out=form.querySelector('[data-count]'),n=[...el.value].length;
    if(out){out.textContent=`${n}/${REPLY_MAX}`;out.classList.toggle('near',n>REPLY_MAX-30);}
    return true;
  }
  async submit(form){
    if(form.dataset.form!=='reply')return false;
    const id=Number(form.dataset.id),reply=(form.querySelector('textarea')?.value||'').trim(),cur=this.item(id);
    if(!reply){toast('Viết lời đáp trước đã nhé.','bad');form.querySelector('textarea')?.focus();return true;}
    // Replying also marks a new note as seen (as in the game's inbox).
    const it=await this.save({id,reply,...(cur?.status==='new'?{status:'seen'}:{})},'Đã gửi lời đáp.');
    if(it)delete this.drafts[id];
    return true;
  }
}
