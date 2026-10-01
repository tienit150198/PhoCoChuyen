/** 💬 Chat: Cả phố (everyone online), Tin nhắn (friends 1:1 and groups) and Bạn bè (who is online).
 * Its own dialog (not the shared #sheet), opened by the chat button on the scene, the menu entry "Chat" and a
 * push (?chat=<id>). Everything goes through the live socket (./live.js); the rules (who may write where,
 * slow mode, filters, blocks, reports) are the live service's (live/chat.py): this file only draws.
 * No guide, no tips (owner, 01/10): icons, short labels, one-line empty states. Player text is always escaped
 * and marked data-no-translate.
 * 📌 Admins (live.me.adm, decided by the server from ADMIN_USERS): a "📢 Quản trị" badge on their messages (frames
 * with adm), http(s) links in those messages only become links; the pinned message sits in a bar above Cả phố
 * (tap: whole text). An admin taps any Cả phố message → "📌 Ghim tin này" in its action row; "Bỏ ghim" there and
 * on the bar. */
import {icon,escapeHTML as esc} from '../icons.js';
import {live} from './live.js';
import {stylesheet} from '../lazy.js';

const S={dlg:null,env:null,tab:'town',thread:null,view:null,threads:new Map(),
  town:{msgs:[],more:false,joined:false,why:'ok',wait:0,n:0,loaded:false,pin:null},pinOpen:false,
  act:null,report:null,confirm:null,flash:'',flashTimer:0,pending:new Map(),pick:new Set(),gtitle:'',members:null,
  nextTown:0,cd:0,older:false,synced:0,bound:false};
const TABS=[['town','Cả phố'],['inbox','Tin nhắn'],['friends','Bạn bè']];
const REASONS=[['spam','Spam'],['rude','Thô tục'],['scam','Lừa đảo'],['private','Lộ thông tin'],['other','Khác']];
const rid=()=>Math.random().toString(36).slice(2,10)+Date.now().toString(36).slice(-4);
const me=()=>live.me?.pid;
const dmId=pid=>{const [a,b]=[me(),pid].sort();return `dm:${a}:${b}`;};
const coarse=()=>matchMedia('(pointer:coarse)').matches;
const adm=()=>Boolean(live.me?.adm);   // the server says so (ADMIN_USERS); every admin action is checked there again

/* ---- css + dialog ------------------------------------------------------------------------------- */
const css=()=>stylesheet('/css/chat.css');   // the same link the chat button loaded (./live.js)
function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium chat-sheet';d.setAttribute('aria-label','Chat');
  d.innerHTML=`<div class="ch-root"><header class="ch-head"></header><div class="ch-net" hidden>${icon('refresh',14)} Đang kết nối lại…</div>
    <div class="ch-pinbar" hidden></div><div class="ch-body"></div><div class="ch-flash" role="status" aria-live="polite" hidden></div>
    <form class="ch-compose" hidden><textarea rows="1" enterkeyhint="send" autocomplete="off" aria-label="Tin nhắn" placeholder="Nhắn gì đó…"></textarea>
    <button type="submit" class="ch-send" aria-label="Gửi">${icon('send',20)}</button><small class="ch-count" hidden></small></form>
    <p class="ch-ro" hidden></p></div>`;
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    if(e.target.closest('a[href]'))return;   // a link in an admin message opens (a new tab), nothing else
    const el=e.target.closest('[data-ch-act]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onAct(el.dataset.chAct,el.dataset,el);
  });
  d.addEventListener('close',onClose);
  d.addEventListener('keydown',e=>{
    if(e.key==='Escape')e.stopPropagation();   // closes the chat only, never pauses the game behind it
    if((e.key==='Enter'||e.key===' ')&&e.target.matches?.('[role="button"][data-ch-act]')){e.preventDefault();onAct(e.target.dataset.chAct,e.target.dataset,e.target);}
  });   // closes the chat only, never pauses the game behind it
  const ta=d.querySelector('textarea');
  ta.addEventListener('input',()=>{grow(ta);counter();});
  ta.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing&&!coarse()){e.preventDefault();submit();}});
  d.querySelector('.ch-compose').addEventListener('submit',e=>{e.preventDefault();submit();});
  d.addEventListener('input',e=>{if(e.target.dataset.chField==='gtitle'){S.gtitle=e.target.value;const b=d.querySelector('[data-ch-act="groupMake"]');if(b)b.disabled=!canMake();}});
  d.addEventListener('change',e=>{
    if(e.target.dataset.chField==='online')live.send({t:'prefs',online:e.target.checked});
    if(e.target.dataset.chField==='pick'){const p=e.target.value;e.target.checked?S.pick.add(p):S.pick.delete(p);const b=d.querySelector('[data-ch-act="groupMake"],[data-ch-act="groupAddGo"]');if(b)b.disabled=!canMake();}
  });
  d.querySelector('.ch-body').addEventListener('scroll',onScroll,{passive:true});
  S.dlg=d;return d;
}
const grow=ta=>{ta.style.height='auto';ta.style.height=Math.min(ta.scrollHeight,112)+'px';};

/** The menu entry, the chat button and a push: open on a tab or straight into a chat ({ch}). */
export async function openChat(env,data={}){
  S.env=env;bind();await css();
  const d=dialog();
  if(data.ch){if(data.ch==='town'){S.thread=null;S.tab='town';}else openThread(data.ch,false);}
  else if(!d.open&&!S.thread)S.tab=live.unread()?'inbox':S.tab;
  S.view=null;S.act=null;S.report=null;S.confirm=null;
  if(!d.open){d.showModal();d.scrollTop=0;}
  if(Date.now()-S.synced>15000||live.me&&!live.me.account){S.synced=Date.now();live.send({t:'sync'});}   // a guest who just registered: chat at once
  enter();render(true);
}

/* ---- live frames --------------------------------------------------------------------------------- */
function bind(){
  if(S.bound)return;S.bound=true;
  live.viewing=ch=>Boolean(S.dlg?.open&&S.thread===ch&&document.visibilityState==='visible');
  live.resume=()=>{const t=S.thread&&S.threads.get(S.thread),last=t?.msgs.at(-1)?.id;return last?{[S.thread]:last}:{};};
  live.on('welcome',()=>{S.town.joined=false;if(S.dlg?.open){enter();render();}});
  live.on('down',()=>{S.town.joined=false;if(S.dlg?.open)render();});
  live.on('joined',f=>{
    const T=S.town,after=T.msgs.at(-1)?.id||0;
    if(f.inc)T.msgs=[...T.msgs,...f.msgs.filter(m=>m.id>after)];else{T.msgs=f.msgs;T.more=f.more;}
    T.loaded=true;T.why=f.why;T.wait=f.wait;T.at=Date.now();T.n=f.n;
    if('pin' in f){if(T.pin?.id!==f.pin?.id)S.pinOpen=false;T.pin=f.pin||null;}
    if(f.why==='ok'&&f.wait>0)S.nextTown=Date.now()+f.wait*1000;
    if(S.dlg?.open)render(true);
  });
  live.on('msg',f=>{
    const mine=f.cid&&S.pending.has(f.cid);if(mine)S.pending.delete(f.cid);
    if(f.ch==='town'){
      if(f.n)S.town.n=f.n;
      if(!S.town.msgs.some(m=>m.id===f.id)){S.town.msgs.push(f);S.town.msgs.sort((a,b)=>a.id-b.id);if(S.town.msgs.length>400)S.town.msgs.splice(0,S.town.msgs.length-400);}
      if(f.pid===me()&&f.wait){S.nextTown=Date.now()+f.wait*1000;countdown();}
    }else{
      const t=S.threads.get(f.ch);if(t&&t.loaded&&!t.msgs.some(m=>m.id===f.id)){t.msgs.push(f);t.msgs.sort((a,b)=>a.id-b.id);}
      if(f.to&&S.thread===dmId(f.to)&&f.ch!==S.thread)S.thread=f.ch;
      if(live.viewing(f.ch)&&f.pid!==me()){live.send({t:'read',ch:f.ch,id:f.id});const c=live.chan(f.ch);if(c)c.unread=0;}
    }
    if(S.dlg?.open)render(f.pid===me());
  });
  live.on('history',f=>{
    if(f.ch==='town'){S.town.msgs=[...f.msgs,...S.town.msgs.filter(m=>!f.msgs.some(x=>x.id===m.id))].sort((a,b)=>a.id-b.id);S.town.more=f.more;S.older=false;render(false,true);return;}
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
  live.on('deleted',f=>{
    if(f.ch==='town'&&S.town.pin?.id===f.id)S.town.pin=null;
    const list=f.ch==='town'?S.town.msgs:S.threads.get(f.ch)?.msgs;if(!list)return;
    const i=list.findIndex(m=>m.id===f.id);if(i<0)return;
    if(f.hidden)list.splice(i,1);else list[i]={...list[i],text:'',del:1};
    if(S.dlg?.open)render();
  });
  live.on('error',f=>{
    if(S.pending.has(f.ref)){const p=S.pending.get(f.ref);S.pending.delete(f.ref);const ta=S.dlg?.querySelector('textarea');if(ta&&!ta.value){ta.value=p.text;grow(ta);}}
    if(f.code==='slow'&&f.wait&&(S.tab==='town'&&!S.thread)){S.nextTown=Date.now()+f.wait*1000;countdown();}
    if(f.code==='new'){S.town.why='new';S.town.wait=f.wait;S.town.at=Date.now();}
    if(f.code==='muted'&&live.me){live.me.town='muted';live.me.muted=f.until;}
    if(f.ref==='pin'||f.ref==='unpin')S.pinning=false;
    if(f.code==='no_chat'&&S.thread?.startsWith('dm:')&&!live.chan(S.thread)){const t=thread(S.thread);t.loaded=true;t.busy=false;t.more=false;if(S.dlg?.open)render();return;}   // a first chat with this friend: nothing yet
    if(S.dlg?.open){flash(f.msg||'Không gửi được.');render();}
  });
  live.on('chan',f=>{if(f.open&&S.dlg?.open){S.view=null;S.pick.clear();S.gtitle='';openThread(f.chan.id);}else if(S.dlg?.open)render();});
  live.on('unchan',f=>{if(S.thread===f.ch){S.thread=null;S.tab='inbox';S.view=null;}if(S.dlg?.open)render();});
  live.on('members',f=>{S.members=f;if(S.dlg?.open)render();});
  live.on('blocked',f=>{
    for(const list of [S.town.msgs,...[...S.threads.values()].map(t=>t.msgs)])for(let i=list.length-1;i>=0;i--)if(list[i].pid===f.pid&&f.on)list.splice(i,1);
    if(f.on&&S.town.pin?.pid===f.pid)S.town.pin=null;
    if(f.on&&S.thread&&live.chan(S.thread)?.peer?.pid===f.pid){S.thread=null;S.tab='inbox';}
    if(S.dlg?.open){flash(f.on?'Đã chặn. Hai bạn không thấy tin của nhau nữa.':'Đã bỏ chặn.');render();}
  });
  live.on('reported',()=>{if(S.dlg?.open){flash('Đã báo cáo. Cảm ơn bạn!');render();}});
  live.on('state',f=>{if(f.town){S.town.why=f.town;S.town.wait=f.wait||0;S.town.at=Date.now();}if(S.dlg?.open)render();});
  for(const t of ['presence','prefs','muted','read'])live.on(t,()=>{if(S.dlg?.open)render();});
}
function thread(ch){let t=S.threads.get(ch);if(!t){t={msgs:[],more:false,loaded:false,busy:false};S.threads.set(ch,t);}return t;}
function markRead(ch){const c=live.chan(ch),t=S.threads.get(ch),last=t?.msgs.at(-1);if(c&&last&&(c.unread||last.id>(c.read||0))){live.send({t:'read',ch,id:last.id});c.unread=0;c.read=last.id;}}

/** What the screen shows needs: join Cả phố while it is on screen, load an open chat. */
function enter(){
  const onTown=S.dlg?.open&&!S.thread&&S.tab==='town'&&!S.view;
  if(onTown&&!S.town.joined&&live.state==='open'){S.town.joined=live.send({t:'join',ch:'town',...(S.town.msgs.length?{after:S.town.msgs.at(-1).id}:{})});}
  if(!onTown&&S.town.joined){live.send({t:'leave',ch:'town'});S.town.joined=false;}
  if(S.thread){const t=thread(S.thread);if(!t.loaded&&!t.busy&&live.state==='open'){t.busy=live.send({t:'history',ch:S.thread});}}
}
function onClose(){if(S.town.joined){live.send({t:'leave',ch:'town'});S.town.joined=false;}S.act=null;S.report=null;clearTimeout(S.cd);}
function openThread(ch,draw=true){S.thread=ch;S.view=null;S.act=null;S.report=null;S.confirm=null;S.tab='inbox';const t=thread(ch);if(t.loaded)markRead(ch);if(draw){enter();render(true);}}

/* ---- actions ----------------------------------------------------------------------------------- */
function onAct(act,d,el){
  switch(act){
    case'close':S.dlg.close();return;
    case'tab':S.tab=d.tab;S.thread=null;S.view=null;S.act=null;S.report=null;break;
    case'back':if(S.view==='add'){S.view='members';break;}if(S.view){S.view=null;S.pick.clear();break;}S.thread=null;S.act=null;S.report=null;S.confirm=null;break;
    case'open':openThread(d.ch);return;
    case'dm':{const c=live.chans.find(x=>x.peer?.pid===d.pid);openThread(c?c.id:dmId(d.pid));return;}
    case'older':{if(S.older)return;const list=S.thread?thread(S.thread).msgs:S.town.msgs;S.older=live.send({t:'history',ch:S.thread||'town',before:list[0]?.id||0});break;}
    case'msg':{const id=Number(d.id);S.act=S.act===id?null:id;S.report=null;S.confirm=null;break;}
    case'del':live.send({t:'del',id:Number(d.id)});S.act=null;break;
    case'pin':if(live.send({t:'pin',id:Number(d.id)}))S.pinning=true;S.act=null;break;   // 📌 admins (the server checks)
    case'unpin':if(live.send({t:'unpin'}))S.pinning=true;S.act=null;break;
    case'pinOpen':S.pinOpen=!S.pinOpen;renderPin();return;
    case'report':S.report=Number(d.id);break;
    case'reason':live.send({t:'report',id:Number(d.id),reason:d.reason});S.act=null;S.report=null;
      {const list=S.thread?thread(S.thread).msgs:S.town.msgs,i=list.findIndex(m=>m.id===Number(d.id));if(i>=0)list.splice(i,1);}break;   // gone for me at once
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
  if(!live.send(frame))return;
  S.pending.set(cid,{ch,text});ta.value='';grow(ta);counter();
  if(ch==='town'&&!adm()){S.nextTown=Date.now()+(live.limits.town_every||10)*1000;countdown();}   // admins: no slow mode
}

/* ---- drawing ----------------------------------------------------------------------------------- */
function flash(text){S.flash=text;clearTimeout(S.flashTimer);S.flashTimer=setTimeout(()=>{S.flash='';const f=S.dlg?.querySelector('.ch-flash');if(f)f.hidden=true;},3800);}
const hm=at=>{const d=new Date(at*1000),now=new Date();const t=d.toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit'});return d.toDateString()===now.toDateString()?t:`${d.getDate()}/${d.getMonth()+1}`;};
const av=(a,cls='')=>`<span class="ch-av ${cls}" aria-hidden="true">${esc(a||'🌸')}</span>`;
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

function head(){
  const x=`<button type="button" class="icon-btn" data-ch-act="close" aria-label="Đóng">${icon('x',20)}</button>`;
  const back=`<button type="button" class="icon-btn" data-ch-act="back" aria-label="Quay lại">${icon('chevron',20,'ch-back-ico')}</button>`;
  if(S.view==='group')return `${back}<h2 class="grow">Nhóm mới</h2>${x}`;
  if(S.view==='members'||S.view==='add'){const c=live.chan(S.thread);return `${back}<h2 class="grow" data-no-translate>${esc(c?.title||'Nhóm')}</h2>${x}`;}
  if(S.thread){
    const c=live.chan(S.thread),grp=c?.kind==='group'||S.thread.startsWith('g:');
    const peer=c?.peer||live.friend(S.thread.slice(3).split(':').find(p=>p!==me()))||{};
    const title=grp?esc(c?.title||'Nhóm'):esc(peer.name||'Bạn bè');
    const sub=grp?`${c?.n||''} người`:peer.on?'Đang online':'';
    const more=grp?`<button type="button" class="icon-btn" data-ch-act="members" aria-label="Thành viên">${icon('people',19)}</button>`:
      (peer.pid?`<button type="button" class="ch-mini${S.confirm==='block:'+peer.pid?' warn':''}" data-ch-act="block" data-pid="${esc(peer.pid)}">${S.confirm==='block:'+peer.pid?'Chặn thật?':'Chặn'}</button>`:'');
    return `${back}${grp?av('👥','md'):`<span class="ch-av-wrap">${av(peer.av,'md')}${dot(peer.on)}</span>`}<div class="grow ch-title"><h2 data-no-translate>${title}</h2>${sub?`<small>${sub}</small>`:''}</div>${more}${x}`;
  }
  const n=live.unread(),on=live.friends.filter(f=>f.on).length;
  const date=live.flags.dating?`<button type="button" class="icon-btn ch-date" data-ch-act="date" aria-label="Góc hẹn hò" title="Góc hẹn hò">${icon('heart',19)}</button>`:'';   // 💕 v4/dating.js
  return `<div class="ch-tabs grow" role="tablist">${TABS.map(([id,label])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" class="${S.tab===id?'on':''}" data-ch-act="tab" data-tab="${id}">${label}${id==='inbox'&&n?`<em class="badge">${n>99?'99+':n}</em>`:''}${id==='friends'&&on?`<i class="ch-on-n">${on}</i>`:''}</button>`).join('')}</div>${date}${x}`;
}

function msgList(list,kind,more){
  if(!list.length)return '';
  let out=more?`<button type="button" class="ch-older" data-ch-act="older"${S.older?' disabled':''}>${S.older?'Đang tải…':'Xem cũ hơn'}</button>`:'';
  let prev=null;
  for(const m of list){
    const mine=m.pid===me(),first=!prev||prev.pid!==m.pid||m.at-prev.at>300;
    const name=!mine&&first&&kind!=='dm'?`<b class="ch-name"><span data-no-translate>${esc(m.name)}</span>${badge(m)}</b>`:'';
    const bar=S.act===m.id?actBar(m,mine,kind):'';
    const pinned=kind==='town'&&S.town.pin?.id===m.id?'<i class="ch-pinned" aria-label="Đang ghim">📌</i>':'';
    // an admin message with links: a div acting as the button (a link cannot sit inside a <button>)
    const bub=m.adm&&!m.del?`<div role="button" tabindex="0" class="ch-bub adm" data-ch-act="msg" data-id="${m.id}"><span data-no-translate>${text(m)}</span><time>${pinned}${hm(m.at)}</time></div>`:
      `<button type="button" class="ch-bub${m.del?' del':''}" data-ch-act="msg" data-id="${m.id}"${m.del?' disabled':''}><span data-no-translate>${m.del?'':lines(m.text)}</span>${m.del?'<i>Tin nhắn đã thu hồi</i>':''}<time>${pinned}${hm(m.at)}</time></button>`;
    out+=`<div class="ch-msg${mine?' mine':''}${first?' first':''}${m.adm?' adm':''}">${mine?'':first?av(m.av):'<span class="ch-av gap"></span>'}<div class="ch-col">${name}${bub}${bar}</div></div>`;
    prev=m;
  }
  return out;
}
function actBar(m,mine,kind){
  // 📌 an admin on Cả phố: pin this message (or unpin it), first in the row
  const pin=kind==='town'&&adm()?(S.town.pin?.id===m.id?`<button type="button" class="ch-mini pin" data-ch-act="unpin">📌 Bỏ ghim</button>`:
    `<button type="button" class="ch-mini pin" data-ch-act="pin" data-id="${m.id}">📌 Ghim tin này</button>`):'';
  if(mine)return `<div class="ch-actbar wrap">${pin}<button type="button" class="ch-mini" data-ch-act="del" data-id="${m.id}">${icon('trash',14)} Thu hồi</button></div>`;
  if(S.report===m.id)return `<div class="ch-actbar wrap">${REASONS.map(([k,l])=>`<button type="button" class="ch-mini" data-ch-act="reason" data-id="${m.id}" data-reason="${k}">${l}</button>`).join('')}</div>`;
  const friend=live.friend(m.pid);
  if(m.adm){   // nobody reports or blocks the Ban quản lý
    const row=pin+(friend&&kind!=='dm'?`<button type="button" class="ch-mini" data-ch-act="dm" data-pid="${esc(m.pid)}">${icon('chat',14)} Nhắn riêng</button>`:'');
    return row?`<div class="ch-actbar wrap">${row}</div>`:'';
  }
  return `<div class="ch-actbar wrap">${pin}${friend&&kind!=='dm'?`<button type="button" class="ch-mini" data-ch-act="dm" data-pid="${esc(m.pid)}">${icon('chat',14)} Nhắn riêng</button>`:''}`+
    `<button type="button" class="ch-mini" data-ch-act="report" data-id="${m.id}">${icon('flag',14)} Báo cáo</button>`+
    `<button type="button" class="ch-mini${S.confirm==='block:'+m.pid?' warn':''}" data-ch-act="block" data-pid="${esc(m.pid)}">${S.confirm==='block:'+m.pid?'Chặn thật?':'Chặn'}</button></div>`;
}
const empty=(ico,text,btn='')=>`<div class="ch-empty">${icon(ico,30)}<p>${text}</p>${btn}</div>`;

function body(){
  if(live.state!=='open'&&!live.welcomed)return empty('refresh','Đang kết nối…');
  if(S.view==='group'||S.view==='add'){
    const inGroup=new Set((S.members?.members||[]).map(m=>m.pid));
    const list=live.friends.filter(f=>S.view!=='add'||!inGroup.has(f.pid));
    const max=(live.limits.group_max||20)-1-(S.view==='add'?inGroup.size-1:0);
    return (S.view==='group'?`<label class="ch-field"><span>Tên nhóm</span><input data-ch-field="gtitle" maxlength="40" value="${esc(S.gtitle)}" data-no-translate></label>`:'')+
      (list.length?`<p class="ch-label">Chọn bạn · tối đa ${max}</p><div class="ch-picks">${list.map(f=>`<label class="ch-pick">${av(f.av)}<span class="grow" data-no-translate>${esc(f.name)}</span>${dot(f.on)}<input type="checkbox" data-ch-field="pick" value="${esc(f.pid)}"${S.pick.has(f.pid)?' checked':''}></label>`).join('')}</div>`:empty('user','Chưa có bạn để mời.'))+
      `<button type="button" class="btn primary full ch-make" data-ch-act="${S.view==='add'?'groupAddGo':'groupMake'}"${canMake()?'':' disabled'}>${S.view==='add'?'Thêm vào nhóm':'Lập nhóm'}</button>`;
  }
  if(S.view==='members'){
    const M=S.members;if(!M)return empty('people','Đang tải…');
    const owner=M.owner===me();
    return `<div class="ch-rows">${M.members.map(m=>`<div class="ch-row static">${`<span class="ch-av-wrap">${av(m.av,'md')}${dot(m.on)}</span>`}<span class="grow"><b data-no-translate>${esc(m.name)}</b>${m.role==='owner'?'<small>Trưởng nhóm</small>':''}</span>`+
      (owner&&m.pid!==me()?`<button type="button" class="ch-mini${S.confirm==='kick:'+m.pid?' warn':''}" data-ch-act="kick" data-pid="${esc(m.pid)}">${S.confirm==='kick:'+m.pid?'Mời ra thật?':'Mời ra'}</button>`:'')+`</div>`).join('')}</div>`+
      `<div class="ch-foot">${owner&&M.members.length<(live.limits.group_max||20)?`<button type="button" class="btn ghost" data-ch-act="groupAdd">${icon('plus',16)} Thêm bạn</button>`:''}<button type="button" class="btn ghost${S.confirm==='leave'?' warn':''}" data-ch-act="leave">${icon('exit',16)} ${S.confirm==='leave'?'Rời thật?':'Rời nhóm'}</button></div>`;
  }
  if(S.thread){
    const t=thread(S.thread);
    if(!t.loaded)return empty('chat','Đang tải…');
    const kind=S.thread.startsWith('g:')?'group':'dm';
    return t.msgs.length?msgList(t.msgs,kind,t.more):empty('chats','Gửi lời chào đầu tiên 👋');
  }
  if(S.tab==='town'){
    const T=S.town;
    if(!T.loaded)return empty('chats','Đang vào phố…');
    return (T.n?`<p class="ch-here">${icon('eye',13)} ${T.n} người đang xem</p>`:'')+(T.msgs.length?msgList(T.msgs,'town',T.more):empty('chats','Phố đang yên. Mở lời trước nhé!'));
  }
  if(S.tab==='inbox'){
    const rows=live.chans.map(c=>{
      const grp=c.kind==='group',p=c.peer||{},last=c.last;
      const prev=last?(last.del?'Tin nhắn đã thu hồi':`${last.pid===me()?'Bạn: ':grp?esc(last.name)+': ':''}${esc(last.text)}`):grp?`${c.n||''} người`:'';
      return `<button type="button" class="ch-row" data-ch-act="open" data-ch="${esc(c.id)}"><span class="ch-av-wrap">${av(grp?'👥':p.av,'md')}${grp?'':dot(p.on)}</span>`+
        `<span class="grow"><b data-no-translate>${esc(grp?c.title:p.name||'Bạn bè')}</b><small data-no-translate>${prev}</small></span>`+
        `<span class="ch-meta">${last?`<time>${hm(last.at)}</time>`:''}${c.unread?`<em class="badge">${c.unread>99?'99+':c.unread}</em>`:''}</span></button>`;
    }).join('');
    const make=live.friends.length?`<button type="button" class="ch-new" data-ch-act="groupNew">${icon('plus',16)} Nhóm mới</button>`:'';
    return make+(rows?`<div class="ch-rows">${rows}</div>`:empty('chat','Chưa có tin nhắn.',live.friends.length?`<button type="button" class="btn ghost" data-ch-act="tab" data-tab="friends">Nhắn bạn bè</button>`:''));
  }
  // friends
  const list=[...live.friends].sort((a,b)=>(b.on-a.on)||a.name.localeCompare(b.name,'vi'));
  const toggle=`<label class="ch-switch"><span>Hiện online</span><input type="checkbox" role="switch" data-ch-field="online"${live.me?.online!==false?' checked':''}><i aria-hidden="true"></i></label>`;
  if(!list.length)return toggle+empty('user',live.me?.account?'Chưa có bạn bè.':'Có tài khoản để kết bạn.',`<button type="button" class="btn ghost" data-ch-act="friends">${icon('user',16)} ${live.me?.account?'Tìm bạn':'Kết bạn'}</button>`);
  return toggle+`<div class="ch-rows">${list.map(f=>`<button type="button" class="ch-row" data-ch-act="dm" data-pid="${esc(f.pid)}"><span class="ch-av-wrap">${av(f.av,'md')}${dot(f.on)}</span><span class="grow"><b data-no-translate>${esc(f.name)}</b>${live.bonds?.includes(f.pid)?'<small class="ch-bond">Đang tìm hiểu 💕</small>':f.on?'<small class="ch-online">Đang online</small>':''}</span>${icon('chat',18)}</button>`).join('')}</div>`;
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
    `<b class="ch-pin-name"><span data-no-translate>${esc(p.name)}</span>${badge(p)}</b><p data-no-translate>${text(p)}</p></div>`+
    (adm()?`<button type="button" class="ch-mini" data-ch-act="unpin">Bỏ ghim</button>`:'')+`</div>`;
}

function render(bottom=false,keepFromBottom=false){
  const d=S.dlg;if(!d)return;
  renderPin();
  const b=d.querySelector('.ch-body'),fromBottom=b.scrollHeight-b.scrollTop-b.clientHeight,atBottom=fromBottom<60;
  d.querySelector('.ch-head').innerHTML=head();
  d.querySelector('.ch-net').hidden=!(live.welcomed&&live.state!=='open');
  b.innerHTML=body();
  b.dataset.view=S.view||(S.thread?'thread':S.tab);
  if(keepFromBottom)b.scrollTop=b.scrollHeight-b.clientHeight-fromBottom;
  else if(bottom||atBottom)b.scrollTop=b.scrollHeight;
  const f=d.querySelector('.ch-flash');f.hidden=!S.flash;f.textContent=S.flash;
  const c=compose(),form=d.querySelector('.ch-compose'),ro=d.querySelector('.ch-ro'),ta=form.querySelector('textarea');
  form.hidden=!c||Boolean(c.ro);ro.hidden=!c?.ro;ro.textContent=c?.ro||'';
  if(c?.act==='account'){const b=document.createElement('button');b.type='button';b.className='btn primary small';b.dataset.chAct='account';b.textContent='Tạo tài khoản';ro.append(' ',b);}
  const town=!S.thread;ta.maxLength=town?(adm()?(live.limits.admin_len||500):(live.limits.town_len||300)):(live.limits.text_len||1000);
  ta.placeholder=town?'Nhắn cả phố…':'Nhắn tin…';
  counter();countdown();
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
  const b=S.dlg.querySelector('.ch-body');
  if(b.scrollTop<40&&!S.older&&b.querySelector('.ch-older:not([disabled])'))onAct('older',{},null);
}
