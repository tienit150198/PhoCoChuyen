/** "Chat": moderation of the live chat on the operator site. GET /api/admin/chat (reported messages waiting
 * for a decision with their context and reasons, active mutes, the last messages of Cả phố) and
 * POST /api/admin/chat {op: hide|keep, id} | {op: mute, pid, hours: 1|24|168} | {op: unmute, pid}
 * (game/live_chat.py). The live service applies a decision at once (PostgreSQL NOTIFY). Messages are not
 * deleted here (Cả phố keeps its newest 2,000, live/chat.py prune_town): "Ẩn" hides one from players, "Giữ" shows it again and closes its reports. */
import {esc,icon,hm,ago,num,toast,tag} from './ui.js';

const REASON={spam:'Spam',rude:'Thô tục',private:'Lộ thông tin',scam:'Lừa đảo',other:'Khác'};
const KIND={town:'Cả phố',dm:'Nhắn riêng',group:'Nhóm'};
const MUTES=[[1,'1 giờ'],[24,'24 giờ'],[168,'7 ngày']];

export class ChatAdmin{
  /** hooks: {rerender(), forbidden()} */
  constructor(api,hooks){this.api=api;this.hooks=hooks;this.data=null;this.busy=false;this.error=null;this.saving=false;this.tab='queue';}

  load(){
    if(this.busy)return;
    this.busy=true;this.error=null;
    this.api.get('/api/admin/chat')
      .then(d=>{this.data=d;})
      .catch(e=>{if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}this.error=e.message;})
      .finally(()=>{this.busy=false;this.hooks.rerender();});
  }
  reset(){this.data=null;this.error=null;}
  meta(){const c=this.data?.counts;return c?`<b>${num(c.pending)}</b> tin bị báo cáo chờ xử lý · ${num(c.auto_hidden)} đang tự ẩn · ${num(this.data.mutes.length)} người bị khóa chat`:'Báo cáo, ẩn tin và khóa chat';}

  view(){
    if(!this.data&&!this.busy&&!this.error)this.load();
    if(this.error&&!this.data)return `<div class="notice bad">${icon('alert',16)}<div>${esc(this.error)}<br><button type="button" class="btn ghost sm" data-act="chatReload">Thử lại</button></div></div>`;
    if(!this.data)return '<p class="note">Đang tải…</p>';
    const d=this.data;
    const tabs=`<div class="seg" role="tablist">${[['queue',`Chờ xử lý (${num(d.counts.pending)})`],['town','Cả phố'],['mutes',`Đang khóa (${num(d.mutes.length)})`]].map(([id,l])=>
      `<button type="button" role="tab" aria-selected="${this.tab===id}" class="${this.tab===id?'on':''}" data-act="chatTab" data-value="${id}">${l}</button>`).join('')}</div>`;
    let body='';
    if(this.tab==='queue')body=d.items.length?d.items.map(m=>this.item(m)).join(''):'<p class="note">Không có tin nào bị báo cáo. 👌</p>';
    else if(this.tab==='town')body=d.town.length?`<div class="card chat-town">${d.town.map(m=>this.line(m,true)).join('')}</div>`:'<p class="note">Cả phố chưa có tin nào.</p>';
    else body=d.mutes.length?`<div class="card">${d.mutes.map(x=>`<div class="chat-line"><span class="grow"><b>${esc(x.name||x.pid)}</b> <small class="muted">${esc(x.pid)}</small><br><small class="muted">đến ${hm(x.until)}${x.reason?` · ${esc(x.reason)}`:''}${x.by?` · bởi @${esc(x.by)}`:''}</small></span><button type="button" class="btn ghost sm" data-act="chatUnmute" data-id="${esc(x.pid)}"${this.saving?' disabled':''}>Mở khóa</button></div>`).join('')}</div>`:'<p class="note">Không ai đang bị khóa chat.</p>';
    return `<div class="chat-admin"><div class="inbox-bar">${tabs}</div>${body}</div>`;
  }
  line(m,actions=false){
    const state=m.deleted?tag('Đã thu hồi'):m.hidden===2?tag('Đã ẩn','bad'):m.hidden===1?tag('Tự ẩn','warn'):'';
    return `<div class="chat-line${m.hidden?' is-hidden':''}"><span class="chat-av" aria-hidden="true">${esc(m.av||'🌸')}</span><span class="grow"><b>${esc(m.name||'?')}</b> <small class="muted">${hm(m.at)}</small> ${state}${m.reports?` ${tag(`${num(m.reports)} báo cáo`,'warn')}`:''}<br><span class="chat-text">${m.deleted?'<i class="muted">(đã thu hồi)</i>':esc(m.text)}</span></span>`+
      (actions&&!m.deleted?this.buttons(m):'')+`</div>`;
  }
  buttons(m){
    const dis=this.saving?' disabled':'';
    return `<span class="chat-btns">${m.hidden===2?`<button type="button" class="btn ghost sm" data-act="chatKeep" data-id="${m.id}"${dis}>Hiện lại</button>`:`<button type="button" class="btn ghost sm" data-act="chatHide" data-id="${m.id}"${dis}>Ẩn</button>`}`+
      `<span class="chat-mute">${MUTES.map(([h,l])=>`<button type="button" class="chip" data-act="chatMute" data-id="${esc(m.pid)}" data-value="${h}" title="Khóa chat ${l}"${dis}>🔇 ${l}</button>`).join('')}</span></span>`;
  }
  item(m){
    const reasons=Object.entries(m.reasons||{}).map(([k,n])=>tag(`${REASON[k]||k} · ${num(n)}`)).join(' ');
    const ctx=m.context.length?`<details class="chat-ctx"><summary>Ngữ cảnh (${m.context.length} tin)</summary>${m.context.map(x=>this.line(x)).join('')}</details>`:'';
    return `<article class="card chat-item"><div class="card-head"><h2>${esc(KIND[m.kind]||m.kind)} <small>${ago(m.at)}</small></h2><div>${reasons}</div></div>${this.line(m)}${ctx}`+
      `<div class="chat-decide"><button type="button" class="btn primary sm" data-act="chatHide" data-id="${m.id}"${this.saving?' disabled':''}>${icon('eye',15)} Ẩn tin này</button>`+
      `<button type="button" class="btn ghost sm" data-act="chatKeep" data-id="${m.id}"${this.saving?' disabled':''}>${icon('check',15)} Giữ (không vi phạm)</button>`+
      `<span class="chat-mute">${MUTES.map(([h,l])=>`<button type="button" class="chip" data-act="chatMute" data-id="${esc(m.pid)}" data-value="${h}"${this.saving?' disabled':''}>🔇 ${l}</button>`).join('')}</span></div></article>`;
  }

  async post(body,done){
    if(this.saving)return;
    this.saving=true;this.hooks.rerender();
    try{await this.api.post('/api/admin/chat',body);toast(done,'good');this.saving=false;this.data=null;this.load();}
    catch(e){this.saving=false;if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}toast(e.message,'bad');this.hooks.rerender();}
  }
  /** true when the click was ours. */
  async action(act,ds){
    switch(act){
      case'chatReload':this.reset();this.load();this.hooks.rerender();return true;
      case'chatTab':this.tab=ds.value;this.hooks.rerender();return true;
      case'chatHide':await this.post({op:'hide',id:Number(ds.id)},'Đã ẩn tin nhắn.');return true;
      case'chatKeep':await this.post({op:'keep',id:Number(ds.id)},'Đã giữ tin nhắn.');return true;
      case'chatMute':{const h=Number(ds.value);await this.post({op:'mute',pid:ds.id,hours:h},`Đã khóa chat ${MUTES.find(x=>x[0]===h)?.[1]||''}.`);return true;}
      case'chatUnmute':await this.post({op:'unmute',pid:ds.id},'Đã mở khóa chat.');return true;
    }
    return false;
  }
}
