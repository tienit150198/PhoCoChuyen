/** "Chat": moderation of the live chat on the operator site. GET /api/admin/chat (reported messages waiting
 * for a decision with their context and reasons, active mutes, the last messages of Cả phố) and
 * POST /api/admin/chat {op: hide|keep, id} | {op: mute, pid, hours: 1|24|168} | {op: unmute, pid}
 * (game/live_chat.py). The live service applies a decision at once (PostgreSQL NOTIFY). Messages are not
 * deleted here (Cả phố keeps its newest 2,000, live/chat.py prune_town): "Ẩn" hides one from players, "Giữ" shows it again and closes its reports.
 * 🔎 "Tin nhắn": every chat, GET /api/admin/chat/messages (200 a page, newest first, "Tải cũ hơn" by id cursor; filter by
 * kind, chat and player; words in the text, the original or the name). A masked message shows "Gốc: …", what was typed
 * (kept since 1.2.2; older messages only have the masked text).
 * 🛟 Moderation #14 (06/10): reports with reason 'minor' (An toàn / trẻ vị thành niên) come first, highlighted; mutes of
 * N minutes ({op: mute, pid, minutes}); 🐢 slow mode for one player or all of Cả phố ({op: slow, pid|'town', seconds,
 * minutes} / {op: unslow, pid}); "Tên cần đổi": account names that fail the name filter, "Đổi tên an toàn" = {op: rename,
 * uid} (→ "Cư dân <uid>"). Never an automatic ban. */
import {esc,icon,hm,ago,num,toast,tag} from './ui.js';

const REASON={spam:'Spam',rude:'Thô tục',private:'Lộ thông tin',scam:'Lừa đảo',other:'Khác',minor:'🛟 An toàn / trẻ vị thành niên'};
const KIND={town:'Cả phố',dm:'Nhắn riêng',group:'Nhóm'};
const MUTES=[[10,'10 phút'],[30,'30 phút'],[60,'1 giờ'],[1440,'24 giờ'],[10080,'7 ngày']];   // minutes
const SLOWS=[[60,60,'1 tin/phút · 1 giờ'],[120,1440,'1 tin/2 phút · 24 giờ']];               // [seconds, minutes, label]
const TOWN_SLOWS=[[30,60,'30 giây/tin · 1 giờ'],[60,60,'1 phút/tin · 1 giờ'],[60,180,'1 phút/tin · 3 giờ']];
const BAD={display:'tên chat',pname:'tên Phố nghề',gname:'tên nhân vật'};
const KINDS=[['all','Tất cả'],['town','Cả phố'],['dm','Nhắn riêng'],['group','Nhóm']];
const blankMsgs=()=>({f:{kind:'all',q:'',pid:'',ch:''},items:[],next:null,scanned:null,busy:false,error:null,loaded:false,player:null});

export class ChatAdmin{
  /** hooks: {rerender(), forbidden()} */
  constructor(api,hooks){this.api=api;this.hooks=hooks;this.data=null;this.busy=false;this.error=null;this.saving=false;this.tab='queue';this.msgs=blankMsgs();}

  load(){
    if(this.busy)return;
    this.busy=true;this.error=null;
    this.api.get('/api/admin/chat')
      .then(d=>{this.data=d;})
      .catch(e=>{if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}this.error=e.message;})
      .finally(()=>{this.busy=false;this.hooks.rerender();});
  }
  reset(){this.data=null;this.error=null;const f=this.msgs.f;this.msgs=blankMsgs();this.msgs.f=f;}

  /** 🔎 one page of "Tin nhắn" (more=true: the next older page, appended). */
  loadMsgs(more=false){
    const M=this.msgs;if(M.busy)return;
    if(!more){M.items=[];M.next=null;M.scanned=null;}
    const q=new URLSearchParams();for(const [k,v] of Object.entries(M.f))if(v&&!(k==='kind'&&v==='all'))q.set(k,v);
    if(more&&M.next)q.set('before',M.next);
    M.busy=true;M.error=null;this.hooks.rerender();
    this.api.get('/api/admin/chat/messages?'+q,30000)
      .then(d=>{M.items=more?[...M.items,...d.items.filter(x=>!M.items.some(y=>y.id===x.id))]:d.items;M.next=d.next;M.scanned=d.scanned;M.player=d.player;M.loaded=true;})
      .catch(e=>{if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}M.error=e.message;})
      .finally(()=>{M.busy=false;this.hooks.rerender();});
  }
  msgsView(){
    const M=this.msgs,f=M.f;
    if(!M.loaded&&!M.busy&&!M.error)this.loadMsgs();
    const kinds=`<div class="seg" role="radiogroup" aria-label="Loại">${KINDS.map(([id,l])=>`<button type="button" role="radio" aria-checked="${f.kind===id}" class="${f.kind===id?'on':''}" data-act="chatKind" data-value="${id}">${l}</button>`).join('')}</div>`;
    const form=`<form class="chat-search" data-form="chatSearch" role="search">${kinds}<input type="search" name="q" value="${esc(f.q)}" maxlength="80" placeholder="Tìm chữ, tên hoặc mã người chơi" aria-label="Tìm tin nhắn"><button type="submit" class="btn primary sm"${M.busy?' disabled':''}>${icon('search',15)} Tìm</button></form>`;
    const chips=[f.pid?`<button type="button" class="chip on" data-act="chatClear" data-value="pid" title="Bỏ lọc">👤 ${esc(M.player?.name||f.pid)} <small>${esc(f.pid)}</small> ✕</button>`:'',
      f.ch?`<button type="button" class="chip on" data-act="chatClear" data-value="ch" title="Bỏ lọc">💬 ${esc(f.ch==='town'?'Cả phố':f.ch)} ✕</button>`:'',
      f.q?`<button type="button" class="chip on" data-act="chatClear" data-value="q" title="Bỏ lọc">🔎 “${esc(f.q)}” ✕</button>`:''].join('');
    const note='<p class="note">Tin bị bộ lọc che (•••) có thêm dòng <b>Gốc</b>: chữ người chơi gõ, chỉ quản trị thấy. Tin trước bản 1.2.2 chỉ còn bản đã che.</p>';
    let list;
    if(M.error&&!M.items.length)list=`<div class="notice bad">${icon('alert',16)}<div>${esc(M.error)}<br><button type="button" class="btn ghost sm" data-act="chatMsgsReload">Thử lại</button></div></div>`;
    else if(!M.items.length)list=M.busy?'<p class="note">Đang tải…</p>':`<p class="note">Không thấy tin nào${M.scanned?` (đã xem các tin sau #${num(M.scanned)})`:''}.</p>`;
    else list=`<div class="card chat-town">${M.items.map(m=>this.line(m,true,true)).join('')}</div>`;
    const more=M.next?`<div class="chat-more"><button type="button" class="btn ghost sm" data-act="chatOlder"${M.busy?' disabled':''}>${M.busy?'Đang tải…':'Tải cũ hơn'}</button>${M.scanned?`<small class="muted">đã xem đến tin #${num(M.scanned)}</small>`:''}</div>`:'';
    return `${form}${chips?`<div class="chat-filters">${chips}</div>`:''}${note}<p class="muted chat-count">${num(M.items.length)} tin${M.next?' · còn tin cũ hơn':''}</p>${list}${more}`;
  }
  meta(){const c=this.data?.counts;return c?`${c.safety?`<b class="chat-safety-count">🛟 ${num(c.safety)} báo cáo an toàn</b> · `:''}<b>${num(c.pending)}</b> tin bị báo cáo chờ xử lý · ${num(c.auto_hidden)} đang tự ẩn · ${num(this.data.mutes.length)} người bị khóa chat`:'Báo cáo, ẩn tin và khóa chat';}

  view(){
    if(!this.data&&!this.busy&&!this.error)this.load();
    if(this.error&&!this.data)return `<div class="notice bad">${icon('alert',16)}<div>${esc(this.error)}<br><button type="button" class="btn ghost sm" data-act="chatReload">Thử lại</button></div></div>`;
    if(!this.data)return '<p class="note">Đang tải…</p>';
    const d=this.data;
    const tabs=`<div class="seg" role="tablist">${[['queue',`${d.counts.safety?'🛟 ':''}Chờ xử lý (${num(d.counts.pending)})`],['msgs','Tin nhắn'],['mutes',`Đang khóa (${num(d.mutes.length)})`],['slow',`🐢 Chậm (${num((d.slows||[]).length)})`],['names',`Tên cần đổi (${num((d.names||[]).length)})`]].map(([id,l])=>
      `<button type="button" role="tab" aria-selected="${this.tab===id}" class="${this.tab===id?'on':''}" data-act="chatTab" data-value="${id}">${l}</button>`).join('')}</div>`;
    let body='';
    if(this.tab==='queue')body=d.items.length?d.items.map(m=>this.item(m)).join(''):'<p class="note">Không có tin nào bị báo cáo. 👌</p>';
    else if(this.tab==='msgs')body=this.msgsView();
    else if(this.tab==='slow')body=this.slowView();
    else if(this.tab==='names')body=this.namesView();
    else body=d.mutes.length?`<div class="card">${d.mutes.map(x=>`<div class="chat-line"><span class="grow"><b>${esc(x.name||x.pid)}</b> <small class="muted">${esc(x.pid)}</small><br><small class="muted">đến ${hm(x.until)}${x.reason?` · ${esc(x.reason)}`:''}${x.by?` · bởi @${esc(x.by)}`:''}</small></span><button type="button" class="btn ghost sm" data-act="chatUnmute" data-id="${esc(x.pid)}"${this.saving?' disabled':''}>Mở khóa</button></div>`).join('')}</div>`:'<p class="note">Không ai đang bị khóa chat.</p>';
    return `<div class="chat-admin"><div class="inbox-bar">${tabs}</div>${body}</div>`;
  }
  /** 🐢 slow mode: Cả phố for everyone, and who is slowed down now. */
  slowView(){
    const d=this.data,dis=this.saving?' disabled':'',slows=d.slows||[],town=slows.find(x=>x.pid==='town');
    const townRow=`<div class="card"><h3>Cả phố</h3><p class="note">${town?`Đang chậm: 1 tin mỗi ${num(town.every)} giây đến ${hm(town.until)}.`:'Bình thường (mặc định của máy chủ).'}</p><div class="chat-mute">${TOWN_SLOWS.map(([s,m,l])=>`<button type="button" class="chip" data-act="chatSlow" data-id="town" data-value="${s}" data-min="${m}"${dis}>🐢 ${l}</button>`).join('')}${town?`<button type="button" class="btn ghost sm" data-act="chatUnslow" data-id="town"${dis}>Tắt chế độ chậm</button>`:''}</div></div>`;
    const people=slows.filter(x=>x.pid!=='town');
    const list=people.length?`<div class="card">${people.map(x=>`<div class="chat-line"><span class="grow"><b>${esc(x.name||x.pid)}</b> <small class="muted">${esc(x.pid)}</small><br><small class="muted">1 tin/${num(x.every)} giây · đến ${hm(x.until)}${x.by?` · bởi @${esc(x.by)}`:''}</small></span><button type="button" class="btn ghost sm" data-act="chatUnslow" data-id="${esc(x.pid)}"${dis}>Bỏ chậm</button></div>`).join('')}</div>`:'<p class="note">Không ai đang bị cho chậm. Bấm 🐢 ở một tin nhắn để làm chậm người gửi.</p>';
    return townRow+list;
  }
  /** Account names that fail the name filter (game/accounts.py offending_names): renamed only by this button. */
  namesView(){
    const names=this.data.names||[],dis=this.saving?' disabled':'';
    if(!names.length)return '<p class="note">Không có tên nào vi phạm bộ lọc tên. 👌</p>';
    return `<p class="note">Không tự đổi tên ai. Bấm "Đổi tên an toàn" để đổi tên vi phạm thành tên gợi ý; tiến trình và tiền của người chơi giữ nguyên.</p><div class="card">${names.map(x=>`<div class="chat-line"><span class="grow"><b>${esc(x.display||'?')}</b> <small class="muted">@${esc(x.username)} · #${num(x.uid)}</small><br><small class="muted">${x.bad.map(k=>`${BAD[k]||k}: ${esc((k==='display'?x.display:k==='pname'?x.profile:x.character)||'')}`).join(' · ')}</small></span><button type="button" class="btn primary sm" data-act="chatRename" data-id="${x.uid}" data-value="${esc(x.safe)}"${dis}>Đổi tên an toàn → ${esc(x.safe)}</button></div>`).join('')}</div>`;
  }
  muteChips(pid){
    const dis=this.saving?' disabled':'';
    return `<span class="chat-mute">${MUTES.map(([m,l])=>`<button type="button" class="chip" data-act="chatMute" data-id="${esc(pid)}" data-value="${m}" title="Khóa chat ${l}"${dis}>🔇 ${l}</button>`).join('')}${SLOWS.map(([s,m,l])=>`<button type="button" class="chip" data-act="chatSlow" data-id="${esc(pid)}" data-value="${s}" data-min="${m}" title="Cho chậm: ${l}"${dis}>🐢 ${l}</button>`).join('')}</span>`;
  }
  line(m,actions=false,where=false){
    const state=m.deleted?tag('Đã thu hồi'):m.hidden===2?tag('Đã ẩn','bad'):m.hidden===1?tag('Tự ẩn','warn'):'';
    const who=where?`<button type="button" class="linkish" data-act="chatPid" data-id="${esc(m.pid)}" title="Xem tin của người này"><b>${esc(m.name||'?')}</b></button>`:`<b>${esc(m.name||'?')}</b>`;
    const chan=where?` <button type="button" class="chip chat-ch" data-act="chatCh" data-id="${esc(m.ch)}" title="Xem cả cuộc trò chuyện">${esc(KIND[m.kind]||m.kind)}${m.title?` · ${esc(m.title)}`:''}</button>`:'';
    const raw=m.raw&&!m.deleted?`<div class="chat-raw"><b>Gốc:</b> <span class="chat-text">${esc(m.raw)}</span></div>`:'';
    return `<div class="chat-line${m.hidden?' is-hidden':''}"><span class="chat-av" aria-hidden="true">${esc(m.av||'🌸')}</span><span class="grow">${who} <small class="muted">${hm(m.at)} · #${m.id}</small>${chan} ${state}${m.adm?` ${tag('📢 Quản trị')}`:''}${m.reports?` ${tag(`${num(m.reports)} báo cáo`,'warn')}`:''}<br><span class="chat-text">${m.deleted?'<i class="muted">(đã thu hồi)</i>':esc(m.text)}</span>${raw}</span>`+
      (actions&&!m.deleted?this.buttons(m):'')+`</div>`;
  }
  buttons(m){
    const dis=this.saving?' disabled':'';
    return `<span class="chat-btns">${m.hidden===2?`<button type="button" class="btn ghost sm" data-act="chatKeep" data-id="${m.id}"${dis}>Hiện lại</button>`:`<button type="button" class="btn ghost sm" data-act="chatHide" data-id="${m.id}"${dis}>Ẩn</button>`}`+
      `${this.muteChips(m.pid)}</span>`;
  }
  item(m){
    const reasons=Object.entries(m.reasons||{}).map(([k,n])=>tag(`${REASON[k]||k} · ${num(n)}`)).join(' ');
    const ctx=m.context.length?`<details class="chat-ctx"><summary>Ngữ cảnh (${m.context.length} tin)</summary>${m.context.map(x=>this.line(x)).join('')}</details>`:'';
    const safe=m.safety?`<p class="notice bad chat-safety-note">${icon('alert',16)} Báo cáo an toàn / trẻ vị thành niên: xem kỹ ngữ cảnh (hẹn gặp, hỏi địa chỉ, tuổi, trường, số điện thoại…). Khóa chat hoặc cho chậm nếu cần; hệ thống không tự cấm ai.</p>`:'';
    return `<article class="card chat-item${m.safety?' safety':''}"><div class="card-head"><h2>${m.safety?'🛟 ':''}${esc(KIND[m.kind]||m.kind)} <small>${ago(m.at)}</small></h2><div>${reasons}</div></div>${safe}${this.line(m)}${ctx}`+
      `<div class="chat-decide"><button type="button" class="btn primary sm" data-act="chatHide" data-id="${m.id}"${this.saving?' disabled':''}>${icon('eye',15)} Ẩn tin này</button>`+
      `<button type="button" class="btn ghost sm" data-act="chatKeep" data-id="${m.id}"${this.saving?' disabled':''}>${icon('check',15)} Giữ (không vi phạm)</button>`+
      `${this.muteChips(m.pid)}</div></article>`;
  }

  async post(body,done){
    if(this.saving)return;
    this.saving=true;this.hooks.rerender();
    try{
      const out=await this.api.post('/api/admin/chat',body);toast(done,'good');this.saving=false;this.data=null;this.load();
      if(out?.item){const i=this.msgs.items.findIndex(x=>x.id===out.item.id);if(i>=0)this.msgs.items[i]={...this.msgs.items[i],...out.item};}
    }
    catch(e){this.saving=false;if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}toast(e.message,'bad');this.hooks.rerender();}
  }
  /** true when the click was ours. */
  async action(act,ds){
    switch(act){
      case'chatReload':this.reset();this.load();this.hooks.rerender();return true;
      case'chatTab':this.tab=ds.value;this.hooks.rerender();return true;
      case'chatKind':this.msgs.f.kind=ds.value;this.msgs.f.ch='';this.loadMsgs();return true;
      case'chatPid':this.msgs.f.pid=ds.id;this.loadMsgs();return true;
      case'chatCh':this.msgs.f.ch=ds.id;this.loadMsgs();return true;
      case'chatClear':this.msgs.f[ds.value]='';this.loadMsgs();return true;
      case'chatOlder':this.loadMsgs(true);return true;
      case'chatMsgsReload':this.msgs.error=null;this.loadMsgs();return true;
      case'chatHide':await this.post({op:'hide',id:Number(ds.id)},'Đã ẩn tin nhắn.');return true;
      case'chatKeep':await this.post({op:'keep',id:Number(ds.id)},'Đã giữ tin nhắn.');return true;
      case'chatMute':{const m=Number(ds.value);await this.post({op:'mute',pid:ds.id,minutes:m},`Đã khóa chat ${MUTES.find(x=>x[0]===m)?.[1]||''}.`);return true;}
      case'chatSlow':await this.post({op:'slow',pid:ds.id,seconds:Number(ds.value),minutes:Number(ds.min)},ds.id==='town'?'Đã bật chế độ chậm cho Cả phố.':'Đã cho người này chậm lại.');return true;
      case'chatUnslow':await this.post({op:'unslow',pid:ds.id},'Đã tắt chế độ chậm.');return true;
      case'chatRename':await this.post({op:'rename',uid:Number(ds.id)},`Đã đổi tên thành “${ds.value}”.`);return true;
      case'chatUnmute':await this.post({op:'unmute',pid:ds.id},'Đã mở khóa chat.');return true;
    }
    return false;
  }
  /** The search form of "Tin nhắn"; true when it was ours. */
  async submit(form){
    if(form.dataset.form!=='chatSearch')return false;
    this.msgs.f.q=(form.elements.q?.value||'').trim().slice(0,80);this.loadMsgs();return true;
  }
}
