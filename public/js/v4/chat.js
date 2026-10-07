/** 💬 Chat: Cả phố (everyone online), Tin nhắn (friends 1:1 and groups) and Bạn bè (who is online).
 * Its own dialog (not the shared #sheet), opened by the chat button on the scene, the menu entry "Chat" and a
 * push (?chat=<id>). Everything goes through the live socket (./live.js); the rules (who may write where,
 * slow mode, filters, blocks, reports) are the live service's (live/chat.py): this file only draws.
 * No guide, no tips (owner, 01/10): icons, short labels, one-line empty states. Player text is always escaped
 * and marked data-no-translate.
 * 📌 Admins (live.me.adm, decided by the server from ADMIN_USERS): a "📢 Quản trị" badge on their messages (frames
 * with adm), http(s) links in those messages only become links; the pinned message sits in a bar above Cả phố
 * (tap: whole text). An admin taps any Cả phố message → "📌 Ghim tin này" in its action row; "Bỏ ghim" there and
 * on the bar.
 * 😍 Reactions: press and hold a message (LP_MS; touch or mouse; moving or scrolling cancels it) for the emoji bar;
 * one reaction per person per message (the same one again takes it back); chips with counts under the bubble,
 * mine highlighted, a chip toggles it. A tap still opens the message's action row (report, delete, 📌 for admins).
 * 🙂 Faces: a message, friend, peer or member with `fc` (live/faces.py) shows the drawn face in the clothes the player
 * wears (./face.js), else its emoji `av`; a `faced` frame redraws that player everywhere here. Mine: Bạn bè tab → builder.
 * 🗑️ Deleting (owner, 03/10; only when the service says welcome.flags.chatdel, an older one keeps the old row): holding a
 * message (or a right click) opens the emoji bar AND its action row: "Xóa ở phía tôi" (any message, a recalled one too:
 * gone from my screens only) and, on mine, "Thu hồi" for 24 h (for everyone); both ask "…thật?" first. Tin nhắn: "Chọn"
 * (or holding a row) ticks chats, "Xóa" empties them for me only (a DM leaves the list until someone writes again).
 * 🚫 Tin nhắn → "Đã chặn" (welcome.flags.blocks; feedback #93): who I blocked, "Bỏ chặn" each.
 * 🛟 Safety (moderation #14): my own message back with `safety` (live/filters.py safety_cue: hẹn gặp, địa chỉ, số điện
 * thoại, zalo/fb/ig…) opens a friendly notice once per device (SAFETY_KEY); the report reasons have "An toàn / trẻ vị
 * thành niên" (reason 'minor': first in the admin queue). Nothing is blocked by it. */
import {icon,escapeHTML as esc} from '../icons.js';
import {live} from './live.js';
import {stylesheet} from '../lazy.js';
import {avInner} from './face.js';
import {faceCode} from './face-code.js';
import {nameAttrs,frameAttrs,titleChip} from './style-tag.js';   // 🎨 `st` of the week (live/styles.py)
import {chips as hnChips,list as hnList,titles as hnTitles,inlineMax} from './honours.js';   // 🏅 `tt`: every honour title held now (live/honours.py)

const S={dlg:null,env:null,tab:'town',thread:null,view:null,bodyHTML:null,threads:new Map(),
  town:{msgs:[],more:false,joined:false,why:'ok',wait:0,n:0,loaded:false,pin:null},pinOpen:false,reactFor:null,lp:null,
  act:null,report:null,confirm:null,flash:'',flashTimer:0,pending:new Map(),pick:new Set(),gtitle:'',members:null,
  nextTown:0,cd:0,older:false,synced:0,bound:false,notifyOpen:false,notify:null,
  sel:null,blocks:null,unblocking:null,reply:null,composeEpoch:0,failed:new Map()};   // 🗑️ chats ticked in "Chọn" (a Set, null = not choosing); 🚫 the blocked list
const TABS=[['town','Cả phố'],['inbox','Tin nhắn'],['friends','Bạn bè']];
const friendRequests=new Map();   // message id -> pending/sent; only an explicit player's tap starts a request
const REASONS=[['minor','🛟 An toàn / trẻ vị thành niên'],['spam','Spam'],['rude','Thô tục'],['scam','Lừa đảo'],['private','Lộ thông tin'],['other','Khác']];
const SAFETY_KEY='pcc.chat.safety.v1';   // 🛟 the notice was read on this device
const SAFETY_TEXT='Nhắc nhẹ nè 💛 Ở phố mình chơi vui là chính, nhưng đừng gửi địa chỉ nhà, trường, số điện thoại hay nick Zalo/FB/IG/TikTok cho người mới quen, và đừng hẹn gặp người lạ ngoài đời nha. Bạn dưới 18 tuổi thì càng cần cẩn thận hơn. Ai làm bạn thấy không ổn: chạm vào tin nhắn → Báo cáo → “An toàn / trẻ vị thành niên”, hoặc kể với người lớn bạn tin tưởng.';
const safetySeen=()=>{try{return localStorage.getItem(SAFETY_KEY)==='1';}catch{return false;}};
const rid=()=>Math.random().toString(36).slice(2,10)+Date.now().toString(36).slice(-4);
const me=()=>live.me?.pid;
const dmId=pid=>{const [a,b]=[me(),pid].sort();return `dm:${a}:${b}`;};
const coarse=()=>matchMedia('(pointer:coarse)').matches;
const REACTS=['❤️','😂','😮','😢','👍','🔥'];   // live/chat.py REACTS, same order
const LP_MS=450,LP_MOVE=10;   // a long press: held this long, moved less than this (px)
const QUIET_FOREVER=4102444800;   // live/chat.py QUIET_FOREVER: notifications off (not just for 8 hours)
const CALL_SHOW=900;              // 📣 a dating-corner invitation shows this long (s) on Cả phố
/** Cả phố holds messages (numeric ids) and 📣 invitation lines (sys, placed after the message they followed: k). */
const byK=(a,b)=>(a.k??a.id)-(b.k??b.id);
const lastId=list=>{for(let i=list.length-1;i>=0;i--)if(!list[i].sys)return list[i].id;return 0;};
const clock=at=>new Date(at*1000).toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit'});
const adm=()=>Boolean(live.me?.adm);   // the server says so (ADMIN_USERS); every admin action is checked there again
const DEL=()=>Boolean(live.flags.chatdel&&live.me?.account);   // 🗑️ the service deletes on my side (an account's)
const RECALL_S=86400,CLEAR_MAX=20;   // live/chat.py RECALL_SECS (Thu hồi for 24 h), CLEAR_MAX (chats per "Xóa")
const canRecall=m=>!m.del&&(adm()||Date.now()/1000-m.at<RECALL_S);

/* ---- css + dialog ------------------------------------------------------------------------------- */
const css=()=>stylesheet('/css/chat.css');   // the same link the chat button loaded (./live.js)
function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium chat-sheet';d.setAttribute('aria-label','Chat');
  d.innerHTML=`<div class="ch-root"><header class="ch-head"></header><div class="ch-net" hidden>${icon('refresh',14)} Đang kết nối lại…</div>
    <div class="ch-pinbar" hidden></div><div class="ch-body"></div><div class="ch-flash" role="status" aria-live="polite" hidden></div>
    <div class="ch-safety" role="status" aria-live="polite" hidden></div>
    <form class="ch-compose" hidden><div class="ch-reply-compose" hidden></div><textarea rows="1" enterkeyhint="send" autocomplete="off" aria-label="Tin nhắn" placeholder="Nhắn gì đó…"></textarea>
    <button type="submit" class="ch-send" aria-label="Gửi">${icon('send',20)}</button><small class="ch-count" hidden></small></form>
    <p class="ch-ro" hidden></p></div>`;
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    // the click that ends a long press: swallowed wherever it lands (the bar may have opened under the finger)
    if(S.lp?.fired&&(!S.lp.up||Date.now()-S.lp.up<400)){S.lp=null;e.preventDefault();return;}
    if(e.target.closest('a[href]'))return;   // a link in an admin message opens (a new tab), nothing else
    const el=e.target.closest('[data-ch-act]');
    if(!el||!d.contains(el)||el.disabled){
      let redraw=false;
      if(S.reactFor!=null&&!e.target.closest('.ch-react-bar')){S.reactFor=null;redraw=true;}
      if(S.honFor!=null&&!e.target.closest('.hn-pop')){S.honFor=null;redraw=true;}   // 🏅 a tap elsewhere closes the titles
      if(redraw)render();return;}
    e.preventDefault();onAct(el.dataset.chAct,el.dataset,el);
  });
  // 😍 press and hold a message: the emoji bar
  d.addEventListener('pointerdown',lpStart);
  d.addEventListener('pointermove',e=>{if(S.lp?.timer&&Math.hypot(e.clientX-S.lp.x,e.clientY-S.lp.y)>LP_MOVE)lpCancel();},{passive:true});
  for(const t of ['pointerup','pointercancel','pointerleave'])d.addEventListener(t,lpEnd,{passive:true});
  d.addEventListener('contextmenu',e=>{   // no menu / callout on a held bubble; a right click opens what holding opens
    const b=e.target.closest('.ch-bub[data-id]'),row=selRow(e.target);
    if(!b&&!row)return;
    e.preventDefault();
    if(S.lp?.fired)return;   // a held finger already opened it
    if(row)selStart(row.dataset.ch);else if(!b.classList.contains('del')||DEL())openReact(Number(b.dataset.id));
  });
  d.addEventListener('close',onClose);
  d.addEventListener('keydown',e=>{
    if(e.key==='Escape'){e.stopPropagation();if(S.reactFor!=null){e.preventDefault();S.reactFor=null;render();}}   // closes the chat only, never pauses the game behind it
    if((e.key==='Enter'||e.key===' ')&&e.target.matches?.('[role="button"][data-ch-act]')){e.preventDefault();onAct(e.target.dataset.chAct,e.target.dataset,e.target);}
  });   // closes the chat only, never pauses the game behind it
  const ta=d.querySelector('textarea');
  ta.addEventListener('input',()=>{S.composeEpoch++;grow(ta);counter();});
  ta.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing&&!coarse()){e.preventDefault();submit();}});
  d.querySelector('.ch-compose').addEventListener('submit',e=>{e.preventDefault();submit();});
  d.addEventListener('input',e=>{if(e.target.dataset.chField==='gtitle'){S.gtitle=e.target.value;const b=d.querySelector('[data-ch-act="groupMake"]');if(b)b.disabled=!canMake();}});
  d.addEventListener('change',e=>{
    if(e.target.dataset.chField==='online')live.send({t:'prefs',online:e.target.checked});
    if(e.target.dataset.chField==='pick'){const p=e.target.value;e.target.checked?S.pick.add(p):S.pick.delete(p);const b=d.querySelector('[data-ch-act="groupMake"],[data-ch-act="groupAddGo"]');if(b)b.disabled=!canMake();}
    if(e.target.dataset.chField==='selch'&&S.sel){   // 🗑️ a chat ticked for "Xóa"
      const ch=e.target.value;
      if(e.target.checked&&S.sel.size>=CLEAR_MAX){e.target.checked=false;flash(`Mỗi lần xóa tối đa ${CLEAR_MAX} cuộc trò chuyện.`);}
      else if(e.target.checked)S.sel.add(ch);else S.sel.delete(ch);
      S.confirm=null;render();
    }
  });
  d.querySelector('.ch-body').addEventListener('scroll',onScroll,{passive:true});
  S.dlg=d;S.bodyHTML=null;return d;
}
function lpStart(e){
  if(e.button>0)return;
  lpCancel();S.lp=null;
  const row=selRow(e.target);
  if(row){   // 🗑️ holding a chat of the list: "Chọn" with it ticked
    const ch=row.dataset.ch;
    S.lp={x:e.clientX,y:e.clientY,fired:0,timer:setTimeout(()=>{if(!S.lp)return;S.lp.timer=0;S.lp.fired=Date.now();selStart(ch);},LP_MS)};
    return;
  }
  const b=e.target.closest('.ch-bub[data-id]');
  if(!b||(b.classList.contains('del')&&!DEL())||e.target.closest('a[href]'))return;
  const id=Number(b.dataset.id);
  S.lp={id,x:e.clientX,y:e.clientY,fired:0,timer:setTimeout(()=>{if(!S.lp)return;S.lp.timer=0;S.lp.fired=Date.now();openReact(id);},LP_MS)};
}
function lpCancel(){if(S.lp?.timer){clearTimeout(S.lp.timer);S.lp.timer=0;}}
function lpEnd(){lpCancel();if(S.lp?.fired&&!S.lp.up)S.lp.up=Date.now();}   // the finger is up: its click comes right after
/** A held message: its action row (🗑️ delete, report…) and, when I may react, the emoji bar above it. */
function openReact(id){
  const m=listOf(S.thread||'town')?.find(x=>x.id===id);
  S.act=id;S.reactFor=null;S.report=null;S.confirm=null;
  try{navigator.vibrate?.(12);}catch{/* not allowed */}
  if(m?.del){render();return;}   // a recalled message: only "Xóa ở phía tôi"
  if(live.me&&!live.me.account){flash('Tạo tài khoản để thả cảm xúc nhé.');render();return;}
  if(live.me?.muted&&live.me.muted*1000>Date.now()&&!adm()){flash('Bạn đang bị tạm khóa chat.');render();return;}
  S.reactFor=id;
  render();
}
/** 🗑️ A row of the chat list that holding (or a right click) ticks, when deleting is on. */
const selRow=t=>!S.sel&&!S.thread&&!S.view&&S.tab==='inbox'&&DEL()?t.closest('.ch-row[data-ch-act="open"]'):null;
function selStart(ch){S.sel=new Set(ch?[ch]:[]);S.confirm=null;try{navigator.vibrate?.(12);}catch{/* not allowed */}render();}
/** 🗑️ Chats emptied on my side (here or in another tab): {ch: newest id gone}; a DM leaves the list (live.js). */
function dropCleared(chs){for(const [ch,upto] of Object.entries(chs||{})){redactReplies({ch,upto});const t=S.threads.get(ch);if(t)t.msgs=t.msgs.filter(m=>m.id>upto);}}
/** 🗑️ One message gone from my screens. */
function dropMsg(ch,id){
  redactReplies({ch,id});
  const list=listOf(ch),i=list?list.findIndex(m=>m.id===id):-1;if(i>=0)list.splice(i,1);
  const c=live.chan(ch);if(c?.last?.id===id)delete c.last;
  if(S.act===id)S.act=null;if(S.reactFor===id)S.reactFor=null;
}
/** The list a message of channel ch is in (Cả phố or an open chat). */
const listOf=ch=>ch==='town'?S.town.msgs:S.threads.get(ch)?.msgs;
const grow=ta=>{ta.style.height='auto';ta.style.height=Math.min(ta.scrollHeight,112)+'px';};
const composeChannel=()=>S.thread||'town';
function resetReply(){S.reply=null;S.composeEpoch++;}
/** Remove quoted originals from every cache, including quotes whose original is not loaded. */
function redactReplies({ch,id,upto,pid}){
  const matches=(q,channel)=>q&&(pid?q.pid===pid:channel===ch&&(id!=null?q.id===id:q.id<=upto));
  const scrub=(m,channel)=>{if(matches(m?.reply,channel))m.reply={id:m.reply.id,unavailable:true};};
  for(const m of S.town.msgs)scrub(m,'town');scrub(S.town.pin,'town');
  for(const [channel,t] of S.threads)for(const m of t.msgs)scrub(m,channel);
  for(const c of live.chans)scrub(c.last,c.id);
  if(matches(S.reply,S.reply?.ch))resetReply();
  for(const p of [...S.pending.values(),...S.failed.values()])if(matches(p.reply,p.ch))p.reply=null;
}
function restoreFailed(ch){
  const p=S.failed.get(ch),ta=S.dlg?.querySelector?.('textarea');
  if(!p||!ta||ta.value||S.reply)return;
  ta.value=p.text;S.reply=p.reply;S.failed.delete(ch);S.composeEpoch++;grow(ta);
}
function replyQuote(q){
  if(!q||!Number.isSafeInteger(q.id)||q.id<1)return '';
  if(q.unavailable)return '<span class="ch-quote unavailable">Tin nhắn không còn khả dụng</span>';
  return `<span class="ch-quote"><b data-no-translate>${esc(q.name||'Bạn')}${hnChips(S.env?.api,q.tt,1,false)}</b><span data-no-translate>${esc(String(q.text||'').slice(0,180))}</span></span>`;
}
function renderReply(){
  const box=S.dlg?.querySelector?.('.ch-reply-compose');if(!box)return;
  const q=S.reply?.ch===composeChannel()?S.reply:null;box.hidden=!q;
  box.innerHTML=q?`<div class="ch-reply-preview"><small>Đang trả lời</small>${replyQuote(q)}</div><button type="button" class="ch-mini" data-ch-act="replyCancel" aria-label="Hủy trả lời">Hủy trả lời</button>`:'';
}

/** The menu entry, the chat button and a push: open on a tab or straight into a chat ({ch}). */
export async function openChat(env,data={}){
  S.env=env;bind();await css();
  const d=dialog();
  if(data.ch){if(data.ch==='town'){if(S.thread)resetReply();S.thread=null;S.tab='town';}else openThread(data.ch,false);}
  else if(!d.open&&!S.thread)S.tab=live.unread()?'inbox':S.tab;
  S.view=null;S.act=null;S.report=null;S.confirm=null;
  if(!d.open){S.bodyHTML=null;d.showModal();d.scrollTop=0;}
  if(Date.now()-S.synced>15000||live.me&&!live.me.account){S.synced=Date.now();live.send({t:'sync'});}   // a guest who just registered: chat at once
  restoreFailed(composeChannel());enter();render(true);
}

/* ---- live frames --------------------------------------------------------------------------------- */
function bind(){
  if(S.bound)return;S.bound=true;
  live.on('friend_card',async f=>{
    if(friendRequests.get(f.id)!=='pending'||typeof f.code!=='string')return;
    friendRequests.set(f.id,'sending');const api=S.env?.api;
    try{
      const d=await api.json('/api/marriage/friend_request',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify({code:f.code})});
      friendRequests.set(f.id,'sent');flash(d.message||'Đã gửi lời mời kết bạn.');live.send({t:'sync'});
    }catch(e){friendRequests.delete(f.id);flash(e.message||'Chưa gửi được, thử lại nhé.');}
    if(S.dlg?.open)render();
  });
  live.viewing=ch=>Boolean(S.dlg?.open&&S.thread===ch&&document.visibilityState==='visible');
  // Resume is capped at 50 oldest missed messages. Fetch a complete latest page
  // after reconnect so a long absence cannot leave a gap in cached history.
  live.resume=()=>({});
  live.on('welcome',()=>{S.threads.clear();S.older=false;S.town.joined=false;if(S.dlg?.open){enter();render();}});
  live.on('down',()=>{S.town.joined=false;if(S.dlg?.open)render();});
  live.on('renamed',f=>{
    const put=x=>{if(x?.pid===f.pid)x.name=f.name;};
    for(const list of [S.town.msgs,S.town.pin?[S.town.pin]:[],...[...S.threads.values()].map(t=>t.msgs)])
      for(const m of list){put(m);put(m.reply);}
    for(const m of S.members?.members||[])put(m);
    put(S.reply);for(const p of [...S.pending.values(),...S.failed.values()])put(p.reply);
    if(S.dlg?.open)render();
  });
  live.on('faced',f=>{   // 🙂 someone's face changed: their lines here too (live.js updates friends and peers)
    for(const list of [S.town.msgs,S.town.pin?[S.town.pin]:[],...[...S.threads.values()].map(t=>t.msgs)])
      for(const m of list)if(m.pid===f.pid){if(f.fc)m.fc=f.fc;else delete m.fc;}
    for(const m of S.members?.members||[])if(m.pid===f.pid){if(f.fc)m.fc=f.fc;else delete m.fc;}
    if(S.dlg?.open)render();
  });
  live.on('joined',f=>{
    const T=S.town,after=lastId(T.msgs);
    if(f.inc)T.msgs=[...T.msgs,...f.msgs.filter(m=>m.id>after)];else{T.msgs=f.msgs;T.more=f.more;}
    T.loaded=true;T.why=f.why;T.wait=f.wait;T.at=Date.now();T.n=f.n;
    if('pin' in f){if(T.pin?.id!==f.pin?.id)S.pinOpen=false;T.pin=f.pin||null;}
    if(f.why==='ok'&&f.wait>0)S.nextTown=Date.now()+f.wait*1000;
    if(S.dlg?.open)render(true);
  });
  live.on('msg',f=>{
    const mine=f.cid&&S.pending.has(f.cid);if(mine)S.pending.delete(f.cid);
    if(f.safety&&f.pid===me()&&!safetySeen())S.safety=true;   // 🛟 once per device
    if(f.ch==='town'){
      if(f.n)S.town.n=f.n;
      if(!S.town.msgs.some(m=>m.id===f.id)){S.town.msgs.push(f);S.town.msgs.sort(byK);if(S.town.msgs.length>400)S.town.msgs.splice(0,S.town.msgs.length-400);}
      if(f.pid===me()&&f.wait){S.nextTown=Date.now()+f.wait*1000;countdown();}
    }else{
      const t=S.threads.get(f.ch);if(t&&!t.msgs.some(m=>m.id===f.id)){t.msgs.push(f);t.msgs.sort((a,b)=>a.id-b.id);}
      if(f.to&&S.thread===dmId(f.to)&&f.ch!==S.thread)S.thread=f.ch;
      if(live.viewing(f.ch)&&f.pid!==me()){live.send({t:'read',ch:f.ch,id:f.id});const c=live.chan(f.ch);if(c)c.unread=0;}
    }
    if(S.dlg?.open)render(f.pid===me());
  });
  live.on('history',f=>{
    if(f.ch==='town'){S.town.msgs=[...f.msgs,...S.town.msgs.filter(m=>!f.msgs.some(x=>x.id===m.id))].sort(byK);S.town.more=f.more;S.older=false;render(false,true);return;}
    const t=thread(f.ch);t.msgs=[...f.msgs,...t.msgs.filter(m=>!f.msgs.some(x=>x.id===m.id))].sort((a,b)=>a.id-b.id);t.more=f.more;t.loaded=true;t.busy=false;
    const first=!f.before;S.older=false;
    if(first)markRead(f.ch);
    if(S.dlg?.open)render(first,!first);
  });
  live.on('missed',f=>{const t=S.threads.get(f.ch);if(!t)return;for(const m of f.msgs)if(!t.msgs.some(x=>x.id===m.id))t.msgs.push(m);t.msgs.sort((a,b)=>a.id-b.id);if(S.dlg?.open)render(true);});
  live.on('pinned',f=>{
    const was=S.town.pin;S.town.pin=f.pin||null;S.pinOpen=false;
    if(S.pinning){S.pinning=false;flash(f.pin?'Đã ghim lên đầu Cả phố.':'Đã bỏ ghim.');}
    if(S.dlg?.open&&(was?.id!==S.town.pin?.id||S.flash))render();
  });
  live.on('call',f=>{   // 📣 someone on the dating bench invites Cả phố: a line with a button (never stored)
    const T=S.town;if(f.ch!=='town'||T.msgs.some(m=>m.sys&&m.id===f.id))return;
    const last=T.msgs.filter(m=>!m.sys).at(-1)?.id||0;
    T.msgs.push({...f,sys:'date',id:f.id,k:last+.5});T.msgs.sort(byK);
    if(S.dlg?.open)render();
  });
  live.on('quiet',f=>{if(S.dlg?.open){if(S.notify===f.ch){S.notify=null;flash(f.until?(f.until>=QUIET_FOREVER?'Đã tắt thông báo của cuộc trò chuyện này.':`Tắt thông báo đến ${clock(f.until)}.`):'Đã bật thông báo.');}render();}});
  live.on('reacts',f=>{   // 😍 counts of one message changed (f.by reacted f.e, or took theirs back)
    const m=listOf(f.ch)?.find(x=>x.id===f.id);if(!m)return;
    m.r=f.r;if(f.by===me())m.my=f.e||undefined;
    if(S.dlg?.open)render();
  });
  live.on('deleted',f=>{
    redactReplies({ch:f.ch,id:f.id});
    if(f.ch==='town'&&S.town.pin?.id===f.id)S.town.pin=null;
    const list=f.ch==='town'?S.town.msgs:S.threads.get(f.ch)?.msgs;
    const i=list?.findIndex(m=>m.id===f.id)??-1;
    if(i>=0){if(f.hidden)list.splice(i,1);else list[i]={...list[i],text:'',del:1,r:undefined,my:undefined,reply:undefined};}   // its reactions and quote go with it
    if(S.dlg?.open)render();
  });
  live.on('error',f=>{
    if(f.ref==='history'){S.older=false;for(const t of S.threads.values())if(t.busy){t.busy=false;t.error=true;}}
    if(f.ref==='friend_card'){for(const [id,status] of friendRequests)if(status==='pending')friendRequests.delete(id);}
    if(f.ref==='face')return;   // 🙂 the avatar sync (live.js) tries again by itself
    const p=S.pending.get(f.ref);
    if(f.code==='gone'&&p?.reply)redactReplies({ch:p.ch,id:p.reply.id});
    if(p){S.pending.delete(f.ref);const ta=S.dlg?.querySelector?.('textarea');
      if(S.dlg?.open&&!S.view&&p.ch===composeChannel()&&p.epoch===S.composeEpoch&&ta&&!ta.value&&!S.reply){ta.value=p.text;S.reply=p.reply;S.composeEpoch++;grow(ta);}
      else S.failed.set(p.ch,p);
    }
    if(f.code==='slow'&&f.wait&&p?.ch==='town'){S.nextTown=Date.now()+f.wait*1000;countdown();}   // only a town message starts the town wait
    if(f.code==='new'){S.town.why='new';S.town.wait=f.wait;S.town.at=Date.now();}
    if(f.code==='muted'&&live.me){live.me.town='muted';live.me.muted=f.until;}
    if(f.ref==='pin'||f.ref==='unpin')S.pinning=false;
    if(f.ref==='unblock')S.unblocking=null;
    if(f.code==='no_chat'&&S.thread?.startsWith('dm:')&&!live.chan(S.thread)){const t=thread(S.thread);t.loaded=true;t.busy=false;t.more=false;if(S.dlg?.open)render();return;}   // a first chat with this friend: nothing yet
    if(S.dlg?.open){flash(f.msg||'Không gửi được.');render();}
  });
  live.on('chan',f=>{if(f.open&&S.dlg?.open){S.view=null;S.pick.clear();S.gtitle='';openThread(f.chan.id);}else if(S.dlg?.open)render();});
  live.on('unchan',f=>{if(S.thread===f.ch){resetReply();S.thread=null;S.tab='inbox';S.view=null;}if(S.dlg?.open)render();});
  live.on('members',f=>{S.members=f;if(S.dlg?.open)render();});
  live.on('blocked',f=>{
    if(f.on)redactReplies({pid:f.pid});
    for(const list of [S.town.msgs,...[...S.threads.values()].map(t=>t.msgs)])for(let i=list.length-1;i>=0;i--)if(list[i].pid===f.pid&&f.on)list.splice(i,1);
    if(f.on&&S.town.pin?.pid===f.pid)S.town.pin=null;
    if(f.on&&S.thread&&(live.chan(S.thread)?.peer?.pid===f.pid||S.thread===dmId(f.pid))){resetReply();S.thread=null;S.tab='inbox';}   // (a DM emptied on my side is not in the list)
    if(!f.on&&S.blocks)S.blocks=S.blocks.filter(b=>b.pid!==f.pid);S.unblocking=null;   // 🚫 off the list
    if(!f.on){clearTimeout(S.syncT);S.syncT=setTimeout(()=>live.send({t:'sync'}),1500);}   // unblocked: friends and chats come back (one sync for several)
    if(S.dlg?.open){flash(f.on?'Đã chặn. Hai bạn không thấy tin của nhau nữa.':'Đã bỏ chặn.');render();}
  });
  live.on('reported',()=>{if(S.dlg?.open){flash(S.safeReport?'Đã báo cáo an toàn. Ban quản lý sẽ xem trước tiên. Cảm ơn bạn nhiều 💛':'Đã báo cáo. Cảm ơn bạn!');S.safeReport=false;render();}});
  live.on('hid',f=>{dropMsg(f.ch,f.id);if(S.dlg?.open)render();});            // 🗑️ deleted on my side (maybe in another tab)
  live.on('reply_hidden',f=>{redactReplies({pid:f.pid});if(S.dlg?.open)render();});
  live.on('cleared',f=>{dropCleared(f.chs);if(S.dlg?.open)render();});
  live.on('blocks',f=>{S.blocks=f.list||[];for(const p of S.blocks)redactReplies({pid:p.pid});S.unblocking=null;if(S.dlg?.open)render();});   // 🚫 who I blocked
  live.on('state',f=>{if(f.town){S.town.why=f.town;S.town.wait=f.wait||0;S.town.at=Date.now();}if(S.dlg?.open){enter();render();}});
  for(const t of ['presence','prefs','muted','read'])live.on(t,()=>{if(S.dlg?.open)render();});
}
function thread(ch){let t=S.threads.get(ch);if(!t){t={msgs:[],more:false,loaded:false,busy:false,error:false};S.threads.set(ch,t);}return t;}
/** A refreshed inbox may know a message that this cached thread missed. Reload
 * the latest page before marking it read; older messages remain in server history. */
function currentThread(ch){
  const t=thread(ch);
  if(t.loaded&&(live.chan(ch)?.last?.id||0)>lastId(t.msgs))Object.assign(t,{msgs:[],more:false,loaded:false,busy:false,error:false});
  return t;
}
function markRead(ch){const c=live.chan(ch),t=S.threads.get(ch),last=t?.msgs.at(-1);if(c&&last&&(c.unread||last.id>(c.read||0))){live.send({t:'read',ch,id:last.id});c.unread=0;c.read=last.id;}}

/** What the screen shows needs: join Cả phố while it is on screen, load an open chat. */
function enter(){
  const onTown=S.dlg?.open&&!S.thread&&S.tab==='town'&&!S.view;
  if(onTown&&!S.town.joined&&live.state==='open'){S.town.joined=live.send({t:'join',ch:'town',...(lastId(S.town.msgs)?{after:lastId(S.town.msgs)}:{})});}
  if(!onTown&&S.town.joined){live.send({t:'leave',ch:'town'});S.town.joined=false;}
  if(S.thread){const t=currentThread(S.thread);if(!t.loaded&&!t.busy&&live.state==='open'){t.error=false;t.busy=live.send({t:'history',ch:S.thread});}}
}
function onClose(){S.bodyHTML=null;resetReply();if(S.town.joined){live.send({t:'leave',ch:'town'});S.town.joined=false;}S.act=null;S.report=null;clearTimeout(S.cd);}
function openThread(ch,draw=true){if(S.thread!==ch)resetReply();S.thread=ch;S.notifyOpen=false;S.view=null;S.act=null;S.report=null;S.confirm=null;S.tab='inbox';restoreFailed(ch);const t=currentThread(ch);if(t.loaded)markRead(ch);if(draw){enter();render(true);}}

/* ---- actions ----------------------------------------------------------------------------------- */
function onAct(act,d,el){
  if(act!=='react')S.reactFor=null;
  if(act!=='honours')S.honFor=null;
  switch(act){
    case'honours':S.honFor=S.honFor===d.id?null:d.id;break;   // 🏅 tapping a name with titles (or "+N"): all of them
    case'workvisit':S.dlg.close();S.env.act('workVisit',{pid:d.pid});return;
    case'friend':{
      const id=Number(d.id);if(!live.me?.account||!live.me?.friend_card||friendRequests.has(id))return;
      friendRequests.set(id,'pending');
      if(!live.send({t:'friend_card',id})){friendRequests.delete(id);flash('Chưa kết nối được. Thử lại nhé.');}
      setTimeout(()=>{if(friendRequests.get(id)==='pending'){friendRequests.delete(id);if(S.dlg?.open)render();}},15000);
      break;
    }
    case'close':S.dlg.close();return;
    case'tab':resetReply();S.tab=d.tab;S.thread=null;S.view=null;S.act=null;S.report=null;S.sel=null;S.confirm=null;break;
    case'back':if(S.view==='add'){S.view='members';break;}if(S.view){S.view=null;S.pick.clear();break;}resetReply();S.thread=null;S.act=null;S.report=null;S.confirm=null;break;
    case'open':openThread(d.ch);return;
    case'historyRetry':if(S.thread){const t=thread(S.thread);t.error=false;t.busy=false;}break;
    case'dm':{const c=live.chans.find(x=>x.peer?.pid===d.pid);openThread(c?c.id:dmId(d.pid));return;}
    case'older':{if(S.older)return;const list=S.thread?thread(S.thread).msgs:S.town.msgs;S.older=live.send({t:'history',ch:S.thread||'town',before:list.find(m=>!m.sys)?.id||0});break;}
    case'msg':{const id=Number(d.id);S.act=S.act===id?null:id;S.report=null;S.confirm=null;break;}
    case'reply':{const ch=composeChannel(),m=listOf(ch)?.find(m=>m.id===Number(d.id));if(!m||m.del||m.sys||!Number.isSafeInteger(m.id)||m.id<1)return;
      S.composeEpoch++;S.reply={ch,id:m.id,pid:m.pid,name:m.name,text:String(m.text||'').slice(0,180)};S.act=null;S.report=null;S.confirm=null;render();S.dlg?.querySelector?.('textarea')?.focus();return;}
    case'replyCancel':resetReply();renderReply();S.dlg?.querySelector?.('textarea')?.focus();return;
    case'del':if(S.confirm!=='del:'+d.id){S.confirm='del:'+d.id;break;}live.send({t:'del',id:Number(d.id)});S.act=null;S.confirm=null;break;   // Thu hồi (for everyone)
    case'hide':{   // 🗑️ Xóa ở phía tôi: gone here at once, the server tells my other tabs
      if(S.confirm!=='hide:'+d.id){S.confirm='hide:'+d.id;break;}
      const id=Number(d.id),ch=S.thread||'town';S.confirm=null;
      if(live.send({t:'hide',id})){dropMsg(ch,id);flash('Đã xóa ở phía bạn.');}
      break;}
    case'selMode':selStart(null);return;
    case'selCancel':S.sel=null;S.confirm=null;break;
    case'clearGo':{   // 🗑️ the ticked chats, emptied on my side (asks once more first)
      const chs=[...(S.sel||[])];if(!chs.length)break;
      if(S.confirm!=='clear'){S.confirm='clear';break;}
      S.confirm=null;
      if(live.send({t:'clear',chs})){
        for(const ch of chs){redactReplies({ch,upto:Infinity});const c=live.chan(ch);if(c?.kind==='dm')live.chans=live.chans.filter(x=>x!==c);else if(c){delete c.last;c.unread=0;}S.threads.delete(ch);}
        S.sel=null;flash(chs.length>1?`Đã xóa ${chs.length} cuộc trò chuyện ở phía bạn.`:'Đã xóa cuộc trò chuyện ở phía bạn.');
      }
      break;}
    case'blocks':S.view='blocks';S.sel=null;S.confirm=null;live.send({t:'blocks'});break;   // 🚫 the list (the answer redraws)
    case'unblock':if(live.send({t:'unblock',pid:d.pid}))S.unblocking=d.pid;break;
    case'pin':if(live.send({t:'pin',id:Number(d.id)}))S.pinning=true;S.act=null;break;   // 📌 admins (the server checks)
    case'unpin':if(live.send({t:'unpin'}))S.pinning=true;S.act=null;break;
    case'pinOpen':S.pinOpen=!S.pinOpen;renderPin();return;
    case'react':live.send({t:'react',id:Number(d.id),e:d.e});S.reactFor=null;break;   // the server toggles: the same one again takes it back
    case'report':S.report=Number(d.id);break;
    case'safetyOk':S.safety=false;try{localStorage.setItem(SAFETY_KEY,'1');}catch{}break;
    case'reason':live.send({t:'report',id:Number(d.id),reason:d.reason});S.act=null;S.report=null;
      if(d.reason==='minor')S.safeReport=true;   // the thanks says the admins look at it first
      dropMsg(composeChannel(),Number(d.id));break;   // gone for me at once
    case'block':if(S.confirm!=='block:'+d.pid){S.confirm='block:'+d.pid;break;}live.send({t:'block',pid:d.pid});S.confirm=null;S.act=null;break;
    case'groupNew':S.view='group';S.pick.clear();S.gtitle='';break;
    case'groupMake':if(canMake())live.send({t:'group_new',title:S.gtitle.trim(),pids:[...S.pick],cid:rid()});return;
    case'members':S.view='members';S.members=null;live.send({t:'members',ch:S.thread});break;
    case'groupAdd':S.view='add';S.pick.clear();break;
    case'groupAddGo':if(S.pick.size){live.send({t:'group_add',ch:S.thread,pids:[...S.pick]});S.view='members';S.members=null;setTimeout(()=>live.send({t:'members',ch:S.thread}),300);}break;
    case'kick':if(S.confirm!=='kick:'+d.pid){S.confirm='kick:'+d.pid;break;}live.send({t:'group_kick',ch:S.thread,pid:d.pid});S.confirm=null;S.members=null;setTimeout(()=>live.send({t:'members',ch:S.thread}),300);break;
    case'leave':if(S.confirm!=='leave'){S.confirm='leave';break;}live.send({t:'group_leave',ch:S.thread});S.confirm=null;break;
    case'friends':S.dlg.close();S.env?.act?.('friends');return;   // Bạn bè (v4/marriage.js): find friends, requests
    case'account':S.dlg.close();S.env?.act?.('v4AccountOpen',{mode:'register'});return;   // guests: register to chat (v4/account.js)
    case'date':S.dlg.close();import('./live.js').then(m=>m.openDate());return;   // 💕 Góc hẹn hò (v4/dating.js)
    case'avatar':S.dlg.close();S.env?.act?.('jrAvatar');return;   // 🙂 the builder (v4/avatar.js)
    case'notifyMenu':S.notifyOpen=!S.notifyOpen;break;
    case'notify':if(live.send({t:'notify',ch:S.thread,v:d.v}))S.notify=S.thread;S.notifyOpen=false;break;   // 🔔 the server answers `quiet`
    case'retry':live.reconnect();break;
  }
  enter();render(act==='open'||act==='tab'||act==='back');
}
const canMake=()=>S.view==='add'?S.pick.size>0:S.pick.size>0&&S.gtitle.trim().length>0;

function submit(){
  const ta=S.dlg.querySelector('textarea'),text=ta.value.trim();if(!text||live.state!=='open')return;
  const cid=rid(),ch=S.thread||'town';
  if(ch==='town'&&Date.now()<S.nextTown)return;
  let frame;
  if(ch.startsWith('dm:')&&!live.chan(ch)){const c=live.chans.find(x=>x.id===ch);const peer=c?.peer?.pid||ch.slice(3).split(':').find(p=>p!==me());frame={t:'send',to:peer,text,cid};}
  else frame={t:'send',ch,text,cid};
  const reply=S.reply?.ch===ch?{...S.reply}:null;if(reply)frame.reply_to=reply.id;
  if(!live.send(frame))return;
  resetReply();S.pending.set(cid,{ch,text,reply,epoch:S.composeEpoch});ta.value='';grow(ta);counter();renderReply();
  if(ch==='town'&&!adm()){S.nextTown=Date.now()+(live.limits.town_every||10)*1000;countdown();}   // admins: no slow mode
}

/* ---- drawing ----------------------------------------------------------------------------------- */
function flash(text){S.flash=text;clearTimeout(S.flashTimer);S.flashTimer=setTimeout(()=>{S.flash='';const f=S.dlg?.querySelector('.ch-flash');if(f)f.hidden=true;},3800);}
const hm=at=>{const d=new Date(at*1000),now=new Date();const t=d.toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit'});return d.toDateString()===now.toDateString()?t:`${d.getDate()}/${d.getMonth()+1}`;};
/** An avatar: a person or a message {av, fc} (its face, else its emoji), or an emoji string ('👥'). */
const av=(a,cls='')=>{const fr=typeof a==='object'&&a?.st?frameAttrs(S.env?.api,a.st):{cls:'',attrs:''};return `<span class="ch-av ${cls}${fr.cls}"${fr.attrs} aria-hidden="true">${typeof a==='string'?esc(a):avInner(a)}</span>`;};   // 🎨 a frame of the week (st.f)
const dot=on=>on?'<i class="ch-on" aria-label="Đang online"></i>':'';
const lines=t=>esc(t).replace(/\n/g,'<br>');
/** An admin message (adm): http(s) addresses become links (new tab, no opener, no referrer); the rest escaped. */
const URLS=/https?:\/\/[^\s<>"']+/gi;
function rich(t){
  t=String(t||'');
  let out='',last=0;
  for(const m of t.matchAll(URLS)){
    const u=m[0].replace(/[.,;:!?)\]}»”’]+$/,'');
    let ok=false;try{const x=new URL(u);ok=x.protocol==='https:'||x.protocol==='http:';}catch{ok=false;}
    out+=lines(t.slice(last,m.index))+(ok?`<a class="ch-link" href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(u)}</a>`:lines(u));
    last=m.index+u.length;
  }
  return out+lines(t.slice(last));
}
const text=m=>m.adm?rich(m.text):lines(m.text);
const badge=m=>m.adm?'<em class="ch-adm">📢 Quản trị</em>':'';

/** 🏅 A DM peer's titles: the `tt` of their newest message in the open chat (null when none). */
function peerTitles(pid){
  const L=pid&&S.thread?thread(S.thread).msgs:null;if(!L)return null;
  for(let i=L.length-1;i>=0;i--)if(L[i].pid===pid&&!L[i].sys)return hnTitles(S.env?.api,L[i].tt).length?L[i].tt:null;
  return null;
}
function head(){
  const x=`<button type="button" class="icon-btn" data-ch-act="close" aria-label="Đóng">${icon('x',20)}</button>`;
  const back=`<button type="button" class="icon-btn" data-ch-act="back" aria-label="Quay lại">${icon('chevron',20,'ch-back-ico')}</button>`;
  if(S.view==='group')return `${back}<h2 class="grow">Nhóm mới</h2>${x}`;
  if(S.view==='blocks')return `${back}<h2 class="grow">Đã chặn</h2>${x}`;
  if(S.view==='members'||S.view==='add'){const c=live.chan(S.thread);return `${back}<h2 class="grow" data-no-translate>${esc(c?.title||'Nhóm')}</h2>${x}`;}
  if(S.thread){
    const c=live.chan(S.thread),grp=c?.kind==='group'||S.thread.startsWith('g:');
    const peer=c?.peer||live.friend(S.thread.slice(3).split(':').find(p=>p!==me()))||{};
    const title=grp?esc(c?.title||'Nhóm'):esc(peer.name||'Bạn bè');
    const ptt=grp?null:peerTitles(peer.pid||S.thread.slice(3).split(':').find(p=>p!==me())),hon=ptt?`<button type="button" class="hn-btn hn-head" data-ch-act="honours" data-id="peer" aria-expanded="${S.honFor==='peer'}">${hnChips(S.env?.api,ptt,inlineMax())}</button>`:'';
    const sub=(grp?`${c?.n||''} người`:peer.on?'Đang online':'')+hon;
    const q=live.quiet(c),bell=c?`<button type="button" class="icon-btn ch-bell${q?' off':''}" data-ch-act="notifyMenu" aria-expanded="${Boolean(S.notifyOpen)}" aria-label="Thông báo: ${q?'Tắt':'Bật'}" title="Thông báo: ${q?'Tắt':'Bật'}"><span aria-hidden="true">${q?'🔕':'🔔'}</span></button>`:'';
    const more=(!grp&&peer.pid?`<button type="button" class="ch-mini" data-ch-act="workvisit" data-pid="${esc(peer.pid)}">Ghé chỗ làm</button>`:'')+bell+(grp?`<button type="button" class="icon-btn" data-ch-act="members" aria-label="Thành viên">${icon('people',19)}</button>`:
      (peer.pid?`<button type="button" class="ch-mini${S.confirm==='block:'+peer.pid?' warn':''}" data-ch-act="block" data-pid="${esc(peer.pid)}">${S.confirm==='block:'+peer.pid?'Chặn thật?':'Chặn'}</button>`:''));
    return `${back}${grp?av('👥','md'):`<span class="ch-av-wrap">${av(peer,'md')}${dot(peer.on)}</span>`}<div class="grow ch-title"><h2 data-no-translate>${title}</h2>${sub?`<small>${sub}</small>`:''}</div>${more}${x}`;
  }
  const n=live.unread(),on=live.friends.filter(f=>f.on).length;
  const date=live.flags.dating?`<button type="button" class="icon-btn ch-date" data-ch-act="date" aria-label="Góc hẹn hò" title="Góc hẹn hò">${icon('heart',19)}</button>`:'';   // 💕 v4/dating.js
  return `<div class="ch-tabs grow" role="tablist">${TABS.map(([id,label])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" class="${S.tab===id?'on':''}" data-ch-act="tab" data-tab="${id}">${label}${id==='inbox'&&n?`<em class="badge">${n>99?'99+':n}</em>`:''}${id==='friends'&&on?`<i class="ch-on-n">${on}</i>`:''}</button>`).join('')}</div>${date}${x}`;
}

/** A message's name row: 🎨 colour and bought title, 🏅 honour chips (tap: every title, in a small popover). */
function nameRow(m){
  const api=S.env?.api,inner=`<span data-no-translate${nameAttrs(api,m.st)}>${esc(m.name)}</span>${titleChip(api,m.st)}${badge(m)}`;
  if(!hnTitles(api,m.tt).length)return `<b class="ch-name">${inner}</b>`;
  const key=String(m.id),open=S.honFor===key;
  return `<button type="button" class="ch-name hn-btn" data-ch-act="honours" data-id="${key}" aria-expanded="${open}">${inner}${hnChips(api,m.tt,inlineMax())}</button>`+
    (open?hnList(api,m.tt,m.name):'');
}
function msgList(list,kind,more){
  if(!list.length)return '';
  let out=more?`<button type="button" class="ch-older" data-ch-act="older"${S.older?' disabled':''}>${S.older?'Đang tải…':'Xem cũ hơn'}</button>`:'';
  let prev=null;
  for(const m of list){
    if(m.sys){if(m.sys==='date'&&Date.now()/1000-m.at<CALL_SHOW)out+=callLine(m);prev=null;continue;}
    const mine=m.pid===me(),first=!prev||prev.pid!==m.pid||m.at-prev.at>300;
    const name=!mine&&first&&kind!=='dm'?nameRow(m):'';   // 🎨 colour + title of the week, 🏅 honour titles
    const bar=S.act===m.id?actBar(m,mine,kind):'';
    const pinned=kind==='town'&&S.town.pin?.id===m.id?'<i class="ch-pinned" aria-label="Đang ghim">📌</i>':'';
    // an admin message with links: a div acting as the button (a link cannot sit inside a <button>)
    const quote=m.del?'':replyQuote(m.reply);
    const bub=m.adm&&!m.del?`<div role="button" tabindex="0" class="ch-bub adm" data-ch-act="msg" data-id="${m.id}">${quote}<span data-no-translate>${text(m)}</span><time>${pinned}${hm(m.at)}</time></div>`:
      `<button type="button" class="ch-bub${m.del?' del':''}" data-ch-act="msg" data-id="${m.id}"${m.del&&!DEL()?' disabled':''}>${quote}<span data-no-translate>${m.del?'':lines(m.text)}</span>${m.del?'<i>Tin nhắn đã thu hồi</i>':''}<time>${pinned}${hm(m.at)}</time></button>`;
    out+=`<div class="ch-msg${mine?' mine':''}${first?' first':''}${m.adm?' adm':''}">${mine?'':first?av(m):'<span class="ch-av gap"></span>'}<div class="ch-col">${name}${bub}${reactBar(m)}${chips(m)}${bar}</div></div>`;
    prev=m;
  }
  return out;
}
/** 📣 "X đang chờ ở góc hẹn hò 💕" with a button that opens Góc hẹn hò (live/dating.py date_call). */
function callLine(m){
  const mine=m.pid===me();
  return `<div class="ch-sys" role="note"><span class="ch-sys-txt">💕 <b data-no-translate>${esc(m.name)}</b> ${mine?'(bạn) ':''}đang chờ ở góc hẹn hò</span>`+
    (mine?'':`<button type="button" class="ch-mini ch-sys-go" data-ch-act="date">Ghé góc hẹn hò</button>`)+`</div>`;
}
/** 🔔 The notification choices of the open chat (under the header). */
function notifyMenu(){
  const c=live.chan(S.thread);if(!S.notifyOpen||!c)return '';
  const q=live.quiet(c),forever=q&&c.quiet>=QUIET_FOREVER;
  const opt=(v,label,on)=>`<button type="button" class="ch-mini${on?' on':''}" data-ch-act="notify" data-v="${v}" aria-pressed="${on}">${label}</button>`;
  return `<div class="ch-notify" role="group" aria-label="Thông báo"><p>${q?(forever?'🔕 Đang tắt thông báo':`🔕 Tắt đến ${clock(c.quiet)}`):'🔔 Đang bật thông báo'}</p>`+
    `<div class="ch-actbar wrap">${opt('on','🔔 Bật',!q)}${opt('8h','🔕 Tắt 8 giờ',q&&!forever)}${opt('off','🔕 Tắt',forever)}</div>`+
    `<small>Tắt: không báo về máy, không tính vào số tin chưa đọc. Tin vẫn tới như thường.</small></div>`;
}
/** 😍 The emoji bar of a held message (mine highlighted). */
function reactBar(m){
  if(S.reactFor!==m.id||m.del)return '';
  return `<div class="ch-react-bar" role="toolbar" aria-label="Thả cảm xúc">${REACTS.map(e=>`<button type="button" class="ch-emo${m.my===e?' on':''}" data-ch-act="react" data-id="${m.id}" data-e="${e}" aria-pressed="${m.my===e}" aria-label="${e}">${e}</button>`).join('')}</div>`;
}
/** 😍 Counts under the bubble; a chip toggles that reaction. */
function chips(m){
  const r=m.r&&!m.del?Object.entries(m.r).filter(([,n])=>n>0):[];
  if(!r.length)return '';
  return `<div class="ch-reacts">${r.map(([e,n])=>`<button type="button" class="ch-chip${m.my===e?' on':''}" data-ch-act="react" data-id="${m.id}" data-e="${esc(e)}" aria-pressed="${m.my===e}">${esc(e)} <b>${n}</b></button>`).join('')}</div>`;
}
function actBar(m,mine,kind){
  // 🗑️ "Xóa ở phía tôi" last in every row (a recalled message: alone); "Thu hồi" on mine for 24 h. Both ask again first.
  const ask=k=>S.confirm===k+':'+m.id;
  const hide=DEL()?`<button type="button" class="ch-mini${ask('hide')?' warn':''}" data-ch-act="hide" data-id="${m.id}">${icon('trash',14)} ${ask('hide')?'Xóa thật?':'Xóa ở phía tôi'}</button>`:'';
  if(m.del)return hide?`<div class="ch-actbar wrap">${hide}</div>`:'';
  const reply=!m.sys&&Number.isSafeInteger(m.id)&&m.id>0?`<button type="button" class="ch-mini" data-ch-act="reply" data-id="${m.id}" aria-label="Trả lời ${esc(m.name||'tin nhắn')}">↩ Trả lời</button>`:'';
  // 📌 an admin on Cả phố: pin this message (or unpin it), first in the row
  const pin=kind==='town'&&adm()?(S.town.pin?.id===m.id?`<button type="button" class="ch-mini pin" data-ch-act="unpin">📌 Bỏ ghim</button>`:
    `<button type="button" class="ch-mini pin" data-ch-act="pin" data-id="${m.id}">📌 Ghim tin này</button>`):'';
  if(mine){
    const rec=canRecall(m)?`<button type="button" class="ch-mini${ask('del')?' warn':''}" data-ch-act="del" data-id="${m.id}">${icon('refresh',14)} ${ask('del')?'Thu hồi thật?':'Thu hồi'}</button>`:'';
    return pin+reply+rec+hide?`<div class="ch-actbar wrap">${pin}${reply}${rec}${hide}</div>`:'';
  }
  if(S.report===m.id)return `<div class="ch-actbar wrap">${REASONS.map(([k,l])=>`<button type="button" class="ch-mini" data-ch-act="reason" data-id="${m.id}" data-reason="${k}">${l}</button>`).join('')}</div>`;
  const friend=live.friend(m.pid);
  const status=friendRequests.get(m.id),add=!friend&&!m.del&&live.me?.account&&live.me?.friend_card?
    `<button type="button" class="ch-mini" data-ch-act="friend" data-id="${m.id}"${status?' disabled':''}>${icon('user',14)} ${status==='sent'?'Đã gửi lời mời':status?'Đang gửi…':'Kết bạn'}</button>`:'';
  if(m.adm){   // nobody reports or blocks the Ban quản lý
    const row=pin+reply+add+(friend&&kind!=='dm'?`<button type="button" class="ch-mini" data-ch-act="dm" data-pid="${esc(m.pid)}">${icon('chat',14)} Nhắn riêng</button>`:'')+hide;
    return row?`<div class="ch-actbar wrap">${row}</div>`:'';
  }
  return `<div class="ch-actbar wrap">${pin}${reply}${add}${friend&&kind!=='dm'?`<button type="button" class="ch-mini" data-ch-act="dm" data-pid="${esc(m.pid)}">${icon('chat',14)} Nhắn riêng</button>`:''}`+
    `<button type="button" class="ch-mini" data-ch-act="report" data-id="${m.id}">${icon('flag',14)} Báo cáo</button>`+
    `<button type="button" class="ch-mini${S.confirm==='block:'+m.pid?' warn':''}" data-ch-act="block" data-pid="${esc(m.pid)}">${S.confirm==='block:'+m.pid?'Chặn thật?':'Chặn'}</button>${hide}</div>`;
}
const empty=(ico,text,btn='')=>`<div class="ch-empty">${icon(ico,30)}<p>${text}</p>${btn}</div>`;

function body(){
  if(live.state!=='open'&&!live.welcomed)return empty('refresh','Đang kết nối…');
  if(S.view==='group'||S.view==='add'){
    const inGroup=new Set((S.members?.members||[]).map(m=>m.pid));
    const list=live.friends.filter(f=>S.view!=='add'||!inGroup.has(f.pid));
    const max=(live.limits.group_max||20)-1-(S.view==='add'?inGroup.size-1:0);
    return (S.view==='group'?`<label class="ch-field"><span>Tên nhóm</span><input data-ch-field="gtitle" maxlength="40" value="${esc(S.gtitle)}" data-no-translate></label>`:'')+
      (list.length?`<p class="ch-label">Chọn bạn · tối đa ${max}</p><div class="ch-picks">${list.map(f=>`<label class="ch-pick">${av(f)}<span class="grow" data-no-translate>${esc(f.name)}</span>${dot(f.on)}<input type="checkbox" data-ch-field="pick" value="${esc(f.pid)}"${S.pick.has(f.pid)?' checked':''}></label>`).join('')}</div>`:empty('user','Chưa có bạn để mời.'))+
      `<button type="button" class="btn primary full ch-make" data-ch-act="${S.view==='add'?'groupAddGo':'groupMake'}"${canMake()?'':' disabled'}>${S.view==='add'?'Thêm vào nhóm':'Lập nhóm'}</button>`;
  }
  if(S.view==='blocks'){   // 🚫 who I blocked (feedback #93)
    const L=S.blocks;if(!L)return empty('refresh','Đang tải…');
    if(!L.length)return empty('user','Bạn chưa chặn ai.');
    return `<div class="ch-rows">${L.map(b=>`<div class="ch-row static"><span class="ch-av-wrap">${av(b,'md')}</span><span class="grow"><b data-no-translate>${esc(b.name)}</b></span>`+
      `<button type="button" class="ch-mini" data-ch-act="unblock" data-pid="${esc(b.pid)}"${S.unblocking===b.pid?' disabled':''}>Bỏ chặn</button></div>`).join('')}</div>`;
  }
  if(S.view==='members'){
    const M=S.members;if(!M)return empty('people','Đang tải…');
    const owner=M.owner===me();
    return `<div class="ch-rows">${M.members.map(m=>`<div class="ch-row static">${`<span class="ch-av-wrap">${av(m,'md')}${dot(m.on)}</span>`}<span class="grow"><b data-no-translate>${esc(m.name)}</b>${m.role==='owner'?'<small>Trưởng nhóm</small>':''}</span>`+
      (owner&&m.pid!==me()?`<button type="button" class="ch-mini${S.confirm==='kick:'+m.pid?' warn':''}" data-ch-act="kick" data-pid="${esc(m.pid)}">${S.confirm==='kick:'+m.pid?'Mời ra thật?':'Mời ra'}</button>`:'')+`</div>`).join('')}</div>`+
      `<div class="ch-foot">${owner&&M.members.length<(live.limits.group_max||20)?`<button type="button" class="btn ghost" data-ch-act="groupAdd">${icon('plus',16)} Thêm bạn</button>`:''}<button type="button" class="btn ghost${S.confirm==='leave'?' warn':''}" data-ch-act="leave">${icon('exit',16)} ${S.confirm==='leave'?'Rời thật?':'Rời nhóm'}</button></div>`;
  }
  if(S.thread){
    const t=thread(S.thread);
    if(!t.loaded)return t.error?empty('chat','Không tải được tin nhắn.')+'<button type="button" class="btn primary full" data-ch-act="historyRetry">Thử lại</button>':empty('chat','Đang tải…');
    const kind=S.thread.startsWith('g:')?'group':'dm';
    const peer=kind==='dm'&&S.honFor==='peer'?(live.chan(S.thread)?.peer||{}):null,ptt=peer?peerTitles(peer.pid||S.thread.slice(3).split(':').find(p=>p!==me())):null;
    return notifyMenu()+(ptt?hnList(S.env?.api,ptt,peer.name||''):'')+(t.msgs.length?msgList(t.msgs,kind,t.more):empty('chats','Gửi lời chào đầu tiên 👋'));
  }
  if(S.tab==='town'){
    const T=S.town;
    if(!T.loaded)return empty('chats','Đang vào phố…');
    return (T.n?`<p class="ch-here">${icon('eye',13)} ${T.n} người đang xem</p>`:'')+(T.msgs.length?msgList(T.msgs,'town',T.more):empty('chats','Phố đang yên. Mở lời trước nhé!'));
  }
  if(S.tab==='inbox'){
    const sel=DEL()?S.sel:null;   // 🗑️ "Chọn": rows become tick boxes
    const rows=live.chans.map(c=>{
      const grp=c.kind==='group',p=c.peer||{},last=c.last,q=live.quiet(c);
      const prev=last?(last.del?'Tin nhắn đã thu hồi':`${last.pid===me()?'Bạn: ':grp?esc(last.name)+': ':''}${esc(last.text)}`):grp?`${c.n||''} người`:'';
      const who=`<span class="ch-av-wrap">${av(grp?'👥':p,'md')}${grp?'':dot(p.on)}</span>`+
        `<span class="grow"><b data-no-translate>${esc(grp?c.title:p.name||'Bạn bè')}</b><small data-no-translate>${prev}</small></span>`;
      if(sel)return `<label class="ch-row ch-selrow${sel.has(c.id)?' on':''}">${who}<input type="checkbox" data-ch-field="selch" value="${esc(c.id)}"${sel.has(c.id)?' checked':''} aria-label="Chọn"></label>`;
      return `<button type="button" class="ch-row${q?' quiet':''}" data-ch-act="open" data-ch="${esc(c.id)}">${who}`+
        `<span class="ch-meta">${last?`<time>${hm(last.at)}</time>`:''}${q||c.unread?`<span class="ch-meta-r">${q?'<i class="ch-q" aria-label="Đã tắt thông báo">🔕</i>':''}${c.unread?`<em class="badge${q?' mute':''}">${c.unread>99?'99+':c.unread}</em>`:''}</span>`:''}</span></button>`;
    }).join('');
    if(sel){
      const n=sel.size,ask=S.confirm==='clear';
      return `<div class="ch-tools"><span class="grow">${n?`Đã chọn ${n}`:'Chọn cuộc trò chuyện để xóa'}</span><button type="button" class="ch-mini" data-ch-act="selCancel">Hủy</button></div>`+
        `<div class="ch-rows">${rows}</div><div class="ch-selfoot"><button type="button" class="btn ${ask?'warn':'ghost'} full" data-ch-act="clearGo"${n?'':' disabled'}>${icon('trash',16)} ${ask?`Xóa ${n} cuộc trò chuyện?`:`Xóa${n?` (${n})`:''}`}</button>`+
        `<small>Chỉ xóa ở phía bạn, người kia vẫn còn tin nhắn.</small></div>`;
    }
    const make=live.friends.length?`<button type="button" class="ch-new" data-ch-act="groupNew">${icon('plus',16)} Nhóm mới</button>`:'';
    const tools=(live.flags.blocks?`<button type="button" class="ch-mini" data-ch-act="blocks">🚫 Đã chặn${S.blocks?.length?` (${S.blocks.length})`:''}</button>`:'')+
      (rows&&DEL()?`<button type="button" class="ch-mini" data-ch-act="selMode">${icon('trash',14)} Chọn</button>`:'')+make;
    return (tools?`<div class="ch-tools">${tools}</div>`:'')+(rows?`<div class="ch-rows">${rows}</div>`:empty('chat','Chưa có tin nhắn.',live.friends.length?`<button type="button" class="btn ghost" data-ch-act="tab" data-tab="friends">Nhắn bạn bè</button>`:''));
  }
  // friends
  const list=[...live.friends].sort((a,b)=>(b.on-a.on)||a.name.localeCompare(b.name,'vi'));
  const mine=live.me?{av:live.me.av,fc:S.env?.api?.state?faceCode(S.env.api.state):live.me.fc}:null;
  const toggle=(mine?`<button type="button" class="ch-row ch-me" data-ch-act="avatar"><span class="ch-av-wrap">${av(mine,'md')}</span><span class="grow"><b>Ảnh đại diện</b><small>Đổi gương mặt, áo theo Tủ đồ</small></span>${icon('arrow',16)}</button>`:'')+
    `<label class="ch-switch"><span>Hiện online</span><input type="checkbox" role="switch" data-ch-field="online"${live.me?.online!==false?' checked':''}><i aria-hidden="true"></i></label>`;
  if(!list.length)return toggle+empty('user',live.me?.account?'Chưa có bạn bè.':'Có tài khoản để kết bạn.',`<button type="button" class="btn ghost" data-ch-act="friends">${icon('user',16)} ${live.me?.account?'Tìm bạn':'Kết bạn'}</button>`);
  return toggle+`<div class="ch-rows">${list.map(f=>`<div class="ch-friend-work"><button type="button" class="ch-row" data-ch-act="dm" data-pid="${esc(f.pid)}"><span class="ch-av-wrap">${av(f,'md')}${dot(f.on)}</span><span class="grow"><b data-no-translate>${esc(f.name)}</b>${live.bonds?.includes(f.pid)?'<small class="ch-bond">Đang tìm hiểu 💕</small>':f.on?'<small class="ch-online">Đang online</small>':''}</span><span class="ch-friend-action" title="Nhắn tin" aria-hidden="true">${icon('chat',18)}</span></button><button type="button" class="ch-friend-action" data-ch-act="workvisit" data-pid="${esc(f.pid)}" title="Ghé chỗ làm" aria-label="Ghé chỗ làm của ${esc(f.name)}">${icon('store',18)}</button></div>`).join('')}</div>`;
}

/** What the composer may do on this screen: null = hidden, {ro: line} = read-only, {} = write. */
function compose(){
  if(S.view)return null;
  if(!S.thread&&S.tab!=='town')return null;
  if(live.state!=='open')return {ro:'Mất kết nối. Đang thử lại…'};
  if(live.me?.muted&&live.me.muted*1000>Date.now())return {ro:`Bạn đang bị tạm khóa chat đến ${new Date(live.me.muted*1000).toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit'})}.`};
  if(live.me&&!live.me.account)return {ro:'Tạo tài khoản để chat.',act:'account'};   // guests read only (owner, 01/10)
  if(S.thread){
    if(!live.me?.name)return {ro:'Đặt tên nhân vật để nhắn.'};
    if(S.thread.startsWith('dm:')){const c=live.chan(S.thread),p=c?.peer;if(c&&p&&p.friend===false&&!live.friend(p.pid))return {ro:'Hai bạn không còn là bạn bè.'};}
    return {};
  }
  const T=S.town;
  if(T.why==='new'){const left=Math.max(1,Math.ceil((T.wait-(Date.now()-(T.at||Date.now()))/1000)/60));return {ro:`Người mới vào phố: đọc trước, ${left} phút nữa nhắn được.`};}
  if(T.why==='name'&&!live.me?.name)return {ro:'Đặt tên nhân vật để nhắn.'};
  return {};
}

/** 📌 The pinned bar above Cả phố: 📌, the name (and the admin badge), two lines of text (tap: all of it). */
function renderPin(){
  const d=S.dlg;if(!d)return;
  const bar=d.querySelector('.ch-pinbar'),p=S.town.pin,show=Boolean(p)&&!S.thread&&S.tab==='town'&&!S.view&&S.town.loaded;
  bar.hidden=!show;
  if(!show){bar.innerHTML='';return;}
  bar.innerHTML=`<div class="ch-pin${S.pinOpen?' open':''}"><span class="ch-pin-ico" aria-hidden="true">📌</span>`+
    `<div class="ch-pin-main" role="button" tabindex="0" data-ch-act="pinOpen" aria-expanded="${S.pinOpen}" aria-label="Tin đang ghim">`+
    `<b class="ch-pin-name"><span data-no-translate>${esc(p.name)}</span>${badge(p)}</b>${replyQuote(p.reply)}<p data-no-translate>${text(p)}</p></div>`+
    (adm()?`<button type="button" class="ch-mini" data-ch-act="unpin">Bỏ ghim</button>`:'')+`</div>`;
}

function render(bottom=false,keepFromBottom=false){
  const d=S.dlg;if(!d)return;
  renderPin();
  const b=d.querySelector('.ch-body'),fromBottom=b.scrollHeight-b.scrollTop-b.clientHeight,atBottom=fromBottom<60;
  d.querySelector('.ch-head').innerHTML=head();
  d.querySelector('.ch-net').hidden=!(live.welcomed&&live.state!=='open');
  // Presence/read updates usually change only the header. Keep message nodes (and focus) intact.
  // Forms still redraw from state: a locally toggled preference may have failed to save.
  const html=body(),messages=!S.view&&(S.thread||S.tab==='town');
  if(!messages||html!==S.bodyHTML)b.innerHTML=html;
  S.bodyHTML=messages?html:null;
  b.dataset.view=S.view||(S.thread?'thread':S.tab);
  if(keepFromBottom)b.scrollTop=b.scrollHeight-b.clientHeight-fromBottom;
  else if(bottom||atBottom)b.scrollTop=b.scrollHeight;
  const f=d.querySelector('.ch-flash');f.hidden=!S.flash;f.textContent=S.flash;
  const sf=d.querySelector('.ch-safety');sf.hidden=!S.safety;
  if(S.safety&&!sf.firstChild)sf.innerHTML=`<p><b>🛟 Giữ an toàn nha</b> ${esc(SAFETY_TEXT)}</p><button type="button" class="btn primary small" data-ch-act="safetyOk">Mình hiểu rồi</button>`;
  else if(!S.safety)sf.textContent='';
  const c=compose(),form=d.querySelector('.ch-compose'),ro=d.querySelector('.ch-ro'),ta=form.querySelector('textarea');
  form.hidden=!c||Boolean(c.ro);ro.hidden=!c?.ro;ro.textContent=c?.ro||'';
  if(c?.act==='account'){const b=document.createElement('button');b.type='button';b.className='btn primary small';b.dataset.chAct='account';b.textContent='Tạo tài khoản';ro.append(' ',b);}
  const town=!S.thread;ta.maxLength=town?(adm()?(live.limits.admin_len||500):(live.limits.town_len||300)):(live.limits.text_len||1000);
  ta.placeholder=town?'Nhắn cả phố…':'Nhắn tin…';
  renderReply();counter();countdown();
}
function counter(){
  const d=S.dlg;if(!d)return;const ta=d.querySelector('textarea'),c=d.querySelector('.ch-count'),max=ta.maxLength;
  const n=ta.value.length;c.hidden=!(max>0&&n>max*.8);c.textContent=`${n}/${max}`;
}
function countdown(){
  const d=S.dlg;if(!d)return;clearTimeout(S.cd);
  const btn=d.querySelector('.ch-send'),left=Math.ceil((S.nextTown-Date.now())/1000),town=!S.thread&&S.tab==='town';
  if(town&&left>0){btn.disabled=true;btn.classList.add('wait');btn.innerHTML=`<b>${left}</b>`;btn.setAttribute('aria-label',`Chờ ${left} giây`);S.cd=setTimeout(countdown,250);}
  else{btn.disabled=false;btn.classList.remove('wait');if(!btn.querySelector('svg'))btn.innerHTML=icon('send',20);btn.setAttribute('aria-label','Gửi');}
}
function onScroll(){
  lpCancel();
  const b=S.dlg.querySelector('.ch-body');
  if(b.scrollTop<40&&!S.older&&b.querySelector('.ch-older:not([disabled])'))onAct('older',{},null);
}
