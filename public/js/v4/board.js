/** Nhóm Cư Dân Phố: the neighbourhood group board (a Zalo/Facebook-style feed
 * shared by every workplace). Markup and requests only: every rule lives in
 * game/board.py; the feed comes from GET /api/board, posts and replies go
 * through POST /api/ai/board (authored replies first, AI wording when allowed).
 * Entry points: the rail/"Thêm" item and the chat-head button over the scene
 * (data-action="nhom"), and boardEntry() on the journey home.
 * Design: docs/superpowers/specs/2026-09-29-board-design.md */
import {icon,escapeHTML as esc} from '../icons.js';
import {myPortrait} from './look.js';

const REACTS=[['heart','❤️','Thương'],['haha','😂','Haha'],['wow','😮','Wow'],['sad','😢','Buồn'],['angry','😡','Giận']];
const R=Object.fromEntries(REACTS.map(([k,e])=>[k,e]));
const SHOW=2;          // comments shown before "xem thêm"
const B={data:null,cast:null,rev:-1,loading:null,open:new Set(),pending:null,mention:false,older:[],fresh:new Set(),opened:0,error:''};
let E=null;

const en=api=>api.state?.settings?.lang==='en';
const aiOn=api=>!!(api.ai?.configured&&api.state?.settings?.aiConsent);
const rid=()=>globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
const who=(id,api)=>id==='player'?{name:api.state?.name||'Bạn',emoji:'🙂',tag:'Bạn',color:'',job:''}:(B.cast?.[id]||{name:id,emoji:'🙂',tag:'',color:''});
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');

/** Life-time "2 giờ trước": minutes today, or whole life days for older posts. */
export function ago(a){
  if(!a)return '';
  if(a.m==null)return a.d===1?'Hôm qua':`${a.d} ngày trước`;
  if(a.m<3)return 'Vừa xong';
  if(a.m<60)return `${a.m} phút trước`;
  return `${Math.floor(a.m/60)} giờ trước`;
}

export const boardUnread=api=>Math.min(99,Number(api.state?.board?.unread||0));

/* ---------------------------------------------------------------- data */
function queued(api,fn){const job=api.queue.then(fn,fn);api.queue=job.catch(()=>{});return job;}

async function fetchBoard(api,{older=false}={}){
  if(B.loading&&!older)return B.loading;
  const before=older&&B.older.length?B.older[B.older.length-1].seq:(older&&B.data?.posts?.length?B.data.posts[B.data.posts.length-1].seq:null);
  // apos: where the archive continues once the posts kept in the save run out (game/board_ai.get_view).
  const apos=older?B.data?.apos:null;
  const job=api.json(`/api/board${before!=null?`?before=${before}${apos!=null?`&apos=${apos}`:''}`:''}`).then(data=>{
    B.cast=data.cast||B.cast;
    if(older){B.older=[...B.older,...(data.board?.posts||[])];B.data.older=data.board?.older;B.data.apos=data.board?.apos??null;}
    else{mark(data.board);B.data=data.board;B.rev=data.board?.rev??-1;}
    B.error='';return data;
  }).catch(e=>{B.error=e?.message||'Chưa tải được nhóm.';return null;});
  if(!older){B.loading=job;job.finally(()=>{B.loading=null;});}
  return job;
}

/** Remember which lines are new since the last render so they can slide in one by one. */
function mark(board){
  if(!board)return;
  const known=new Set();
  for(const p of B.data?.posts||[]){known.add(p.id);for(const c of p.cmts)known.add(c.id);}
  B.fresh=new Set();
  if(!B.data)return;
  for(const p of board.posts){if(!known.has(p.id))B.fresh.add(p.id);for(const c of p.cmts)if(!known.has(c.id))B.fresh.add(c.id);}
}

function accept(api,data){
  if(data?.cast)B.cast=data.cast;
  if(data?.board){mark(data.board);B.data=data.board;B.rev=data.board.rev;B.older=[];}
  if(data?.state)api.accept(data);
}

async function seen(env){
  const {api,cmd}=env,upto=B.data?.rev;
  if(!upto||!boardUnread(api))return;
  await cmd('bd_seen',{upto},{quiet:true});
}

/** Post or reply through /api/ai/board; on a lost connection, the plain command. */
async function send(env,body,fallback){
  const {api,cmd,toast,renderSheet}=env;
  const go=()=>queued(api,()=>api.post('/api/ai/board',{...body,career:api.state.current,request_id:rid(),expected_revision:api.revision},25000));
  try{
    let data;
    try{data=await go();}
    catch(error){if(error.status===409&&error.data?.state){api.accept(error.data);data=await go();}else throw error;}
    accept(api,data);return data;
  }catch(error){
    if(!error.status&&fallback){const r=await cmd(fallback[0],fallback[1],{quiet:true});if(r)await fetchBoard(api);return r?{result:r}:null;}
    toast(error.message||'Chưa gửi được.',true);return null;
  }finally{B.pending=null;renderSheet();}
}

/* ---------------------------------------------------------------- markup */
const short=n=>String(n||'').replace(/ \(.*\)$/,'');
const NAMES=()=>[...new Set(Object.values(B.cast||{}).flatMap(c=>[c.name,short(c.name)]))].sort((a,b)=>b.length-a.length);
function rich(text){
  let out=esc(text);
  const names=NAMES();
  if(names.length){
    const re=new RegExp('@('+names.map(n=>esc(n).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('|')+')','g');
    out=out.replace(re,'<b class="bd-at">@$1</b>');
  }
  return out.replace(/\n/g,'<br>');
}

function avatar(id,api,size=''){
  if(id==='player')return `<span class="bd-av ${size} me look" aria-hidden="true">${myPortrait(api.state,size==='sm'?30:42,'')}</span>`;  // 👗 in the outfit from Tủ đồ
  const w=who(id,api);
  return `<span class="bd-av ${size} ${id==='player'?'me':''}"${w.color?` style="--who:${esc(w.color)}"`:''} aria-hidden="true">${w.emoji}</span>`;
}

function tag(id,api){
  const w=who(id,api);if(id==='player')return `<span class="bd-tag me">Bạn</span>`;
  return w.tag?`<span class="bd-tag"${w.color?` style="--who:${esc(w.color)}"`:''}><i aria-hidden="true"></i>${esc(w.tag)}</span>`:'';
}

function comment(c,api,i){
  const w=who(c.who,api),ai=c.mode==='ai',mine=c.who==='player';
  const fresh=B.fresh.has(c.id)&&!mine;
  const own=mine||ai?' data-no-translate':'';
  return `<li class="bd-cmt${mine?' mine':''}${fresh?' bd-in':''}"${fresh?` style="--i:${i}"`:''}>${avatar(c.who,api,'sm')}
    <div class="bd-bubble"><div class="bd-cmt-head"><b>${esc(w.name)}</b>${mine?'':tag(c.who,api)}${ai?`<span class="ai-badge" title="${esc('Lời gốc: '+(c.canonical||''))}" aria-label="Viết bằng AI">AI</span>`:''}</div>
    <p${own}>${rich(c.text)}</p><small>${esc(ago(c.ago))}</small></div></li>`;
}

function reacts(p){
  const total=Object.values(p.react).reduce((a,b)=>a+b,0);
  const top=REACTS.filter(([k])=>p.react[k]>0).sort((a,b)=>p.react[b[0]]-p.react[a[0]]).slice(0,3).map(([,e])=>e).join('');
  const btns=p.archived?'':REACTS.map(([k,e,l])=>`<button type="button" class="bd-react${p.mine===k?' on':''}" data-action="bdReact"${attrs({post:p.id,r:k})} aria-pressed="${p.mine===k}" aria-label="${l}${p.react[k]?`: ${p.react[k]}`:''}"><span aria-hidden="true">${e}</span>${p.react[k]?`<small>${p.react[k]}</small>`:''}</button>`).join('');
  return `<div class="bd-react-row"><span class="bd-react-sum" aria-hidden="true">${top?`${top} ${total}`:''}</span><span class="bd-react-sum">${p.cmts.length?`${p.cmts.length} bình luận`:''}</span></div><div class="bd-reacts" role="group" aria-label="Bày tỏ cảm xúc">${btns}</div>`;
}

function rumourBar(p,api,D){
  const r=p.rumour;if(!r||(p.archived&&r.state==='open'))return '';
  const by=who(r.by,api).name;
  if(r.state!=='open'){
    const done={clarify:'Bạn đã giải thích.',joke:'Bạn đã cười trừ cho qua.',confront:'Bạn đã hỏi thẳng.',ignore:'Bạn đã chọn im lặng.'}[r.state]||'';
    return `<p class="bd-rumour-note">${icon('shield',14)} Tin đồn về bạn · ${esc(done)}</p>`;
  }
  const tones=(D.tones||[]).map(t=>`<button type="button" class="chip bd-tone" data-action="bdTone"${attrs({post:p.id,tone:t.id})}><span aria-hidden="true">${t.emoji}</span> ${esc(t.id==='confront'?`Hỏi thẳng @${by}`:t.label)}</button>`).join('');
  return `<div class="bd-rumour" role="note"><p><b>👀 Đang có người bàn tán về bạn.</b> Chuyện chưa ai kiểm chứng, nói ra dễ làm tổn thương. Bạn muốn phản hồi thế nào?</p><div class="chip-row">${tones}</div></div>`;
}

function postCard(p,api,D){
  const w=who(p.who,api),mine=p.who==='player';
  const open=B.open.has(p.id),hidden=Math.max(0,p.cmts.length-SHOW);
  const list=open?p.cmts:p.cmts.slice(-SHOW);
  const pend=B.pending&&B.pending.post===p.id?`<li class="bd-cmt mine pending">${avatar('player',api,'sm')}<div class="bd-bubble"><p data-no-translate>${rich(B.pending.text)}</p></div></li>${typing()}`:'';
  const more=hidden&&!open?`<button type="button" class="bd-more" data-action="bdMore"${attrs({post:p.id})}>Xem thêm ${hidden} bình luận</button>`:open&&hidden?`<button type="button" class="bd-more" data-action="bdLess"${attrs({post:p.id})}>Thu gọn</button>`:'';
  const kind=p.kind==='ctx'?'<span class="bd-kind">Nhắc tới bạn</span>':p.kind==='life'?'<span class="bd-kind">Chuyện trong hẻm</span>':'';
  return `<article class="bd-post${mine?' mine':''}${p.rumour?' rumour':''}${p.new?' unread':''}${B.fresh.has(p.id)?' bd-in':''}" id="bd-${esc(p.id)}" aria-label="Bài của ${esc(w.name)}">
    <header class="bd-head">${avatar(p.who,api)}<div class="bd-who"><div class="bd-name"><b>${esc(w.name)}</b>${tag(p.who,api)}</div><small>${esc(ago(p.ago))}${w.job&&!mine?` · ${esc(w.job)}`:''}</small></div>${kind}</header>
    <p class="bd-text"${mine?' data-no-translate':''}>${rich(p.text)}</p>
    ${rumourBar(p,api,D)}
    ${reacts(p)}
    <ul class="bd-cmts" aria-label="Bình luận">${more?`<li class="bd-more-row">${more}</li>`:''}${list.map((c,i)=>comment(c,api,i)).join('')}${pend}</ul>
    ${p.archived?'':`<form class="bd-reply" data-bd-form="reply"${attrs({post:p.id})}>${avatar('player',api,'sm')}<input name="text" type="text" maxlength="${D.limits?.reply||300}" placeholder="${mine?'Trả lời hàng xóm…':`Trả lời ${esc(w.name)}…`}" aria-label="Viết bình luận" data-preserve id="bd-r-${esc(p.id)}" autocomplete="off"><button type="submit" class="icon-btn bd-send" aria-label="Gửi bình luận">${icon('send',17)}</button></form>`}
  </article>`;
}

function typing(){return `<li class="bd-cmt typing" role="status" aria-label="Hàng xóm đang trả lời…"><span class="bd-av sm" aria-hidden="true">💬</span><div class="bd-bubble"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span><small>Hàng xóm đang trả lời…</small></div></li>`;}

function composer(env,D){
  const {api}=env,left=D.limits?.left??20;
  const chips=B.mention?`<div class="bd-mentions" role="group" aria-label="Nhắc tên hàng xóm">${Object.entries(B.cast||{}).map(([id,c])=>`<button type="button" class="chip bd-mchip" data-action="bdAt"${attrs({name:short(c.name)})}><span aria-hidden="true">${c.emoji}</span> ${esc(short(c.name))}</button>`).join('')}</div>`:'';
  const pend=B.pending?.post==='new'?`<div class="bd-post mine pending"><header class="bd-head">${avatar('player',api)}<div class="bd-who"><div class="bd-name"><b>${esc(who('player',api).name)}</b></div><small>Đang đăng…</small></div></header><p class="bd-text" data-no-translate>${rich(B.pending.text)}</p><ul class="bd-cmts">${typing()}</ul></div>`:'';
  return `<form class="bd-compose" data-bd-form="post">
      <div class="bd-compose-top">${avatar('player',api)}<textarea id="bd-new" name="text" rows="2" maxlength="${D.limits?.post||500}" placeholder="Hỏi hàng xóm, kể chuyện, rao đồ… Gõ @ để nhắc tên ai đó." aria-label="Viết bài lên nhóm" data-preserve></textarea></div>
      ${chips}
      <div class="bd-compose-foot"><button type="button" class="btn ghost small${B.mention?' on':''}" data-action="bdMention" aria-expanded="${B.mention}">@ Nhắc tên</button>
        <small class="bd-left">${left?`Còn ${left} bài hôm nay`:'Hết lượt đăng hôm nay'}</small>
        <button type="submit" class="btn primary small"${left?'':' disabled'}>${icon('send',15)} Đăng</button></div>
      ${aiOn(api)?`<small class="bd-ai-note">${icon('sparkle',12)} Hàng xóm trả lời bằng AI · đừng gõ thông tin thật</small>`:''}
    </form>${pend}`;
}

function cover(env,D){
  const faces=Object.values(B.cast||{}).slice(0,7).map(c=>`<span aria-hidden="true">${c.emoji}</span>`).join('');
  return `<section class="bd-cover" aria-label="Giới thiệu nhóm"><div class="bd-faces">${faces}<em>+${Math.max(0,(D.members||1)-7)}</em></div>
    <p><b>${D.members||0} thành viên</b> · nhóm kín của khu phố</p>
    <details class="bd-rules"><summary>Nội quy nhóm</summary><ul><li>Nói năng lịch sự, không xúc phạm ai.</li><li>Không đăng số điện thoại, địa chỉ, tài khoản.</li><li>Tin chưa rõ thì đừng lan, có gì hỏi thẳng nhau.</li></ul></details></section>`;
}

/** The "Nhóm phố" sheet (view `nhom`). */
export function boardView(env){
  const {api}=env,D=B.data;
  const head=`<header class="sheet-head bd-sheet-head"><div class="grow"><span class="eyebrow">KHU PHỐ · NHÓM KÍN</span><h2>Nhóm Cư Dân Phố</h2>${D?`<p>${D.story?`Ngày sống ${D.life_day} · `:''}${boardUnread(api)?`${boardUnread(api)} tin mới`:'Đã xem hết tin mới'}</p>`:''}</div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  if(!D)return head+`<div class="sheet-body bd"><p class="muted bd-loading">${B.error?esc(B.error):'Đang mở nhóm…'}</p>${B.error?`<button type="button" class="btn ghost small" data-action="bdReload">Thử lại</button>`:''}</div>`;
  const posts=[...D.posts,...B.older];
  const older=(B.older.length?B.data.older:D.older)?`<button type="button" class="btn ghost full bd-older" data-action="bdOlder">Xem bài cũ hơn</button>`:'';
  return head+`<div class="sheet-body bd">${cover(env,D)}${composer(env,D)}
    <div class="bd-feed" role="feed" aria-busy="${!!B.pending}">${posts.map(p=>postCard(p,api,D)).join('')||'<p class="muted">Nhóm còn yên ắng…</p>'}</div>${older}</div>`;
}

/** A card for the journey home: unread count and the latest line. */
export function boardEntry(env){
  const {api}=env,S=api.state?.board;if(!S)return '';
  const n=boardUnread(api),L=S.latest;
  return `<button type="button" class="jr-card bd-entry" data-action="nhom"><span class="bd-entry-icon" aria-hidden="true">💬</span><span class="grow"><b>Nhóm Cư Dân Phố</b>${L?`<small><span aria-hidden="true">${L.emoji}</span> ${esc(L.name)}: ${esc(L.text)}</small>`:'<small>Hàng xóm đang rôm rả</small>'}</span>${S.rumour?'<span class="tag amber">👀 Có người nhắc bạn</span>':n?`<span class="bd-count">${n}</span>`:''}${icon('arrow',16)}</button>`;
}

/* ---------------------------------------------------------------- wiring */
async function openBoard(env){
  const {api,openSheet,renderSheet}=env;
  B.open.clear();B.older=[];B.opened=Date.now();
  openSheet('nhom');
  await fetchBoard(api);renderSheet();
  await seen(env);
  // At most a couple of AI neighbour exchanges a life day, generated lazily when the board opens.
  if(aiOn(api)&&B.data?.ai?.left>0){
    try{const data=await queued(api,()=>api.post('/api/ai/board',{op:'open'},20000));if(data?.mode==='ai'){accept(api,data);if(env.ui.view==='nhom')renderSheet();await seen(env);}}
    catch{/* the authored board is already there */}
  }
}

/** The stage no longer carries a floating "Nhóm phố" pill (calm screen): the board lives in the rail /
 * "Thêm" menu with its unread badge, and as a tile in the status sheet. Drop a pill left by an older build. */
function fab(){
  document.getElementById('bdFab')?.remove();
}

export function boardBoot(env){
  E=env;fab();
  let t;
  env.api.addEventListener('state',()=>{
    fab();
    const rev=env.api.state?.board?.rev;
    if(env.ui.view==='nhom'&&rev!=null&&rev!==B.rev&&!B.pending){clearTimeout(t);t=setTimeout(async()=>{await fetchBoard(env.api);if(env.ui.view==='nhom')env.renderSheet();seen(env);},250);}
  });
}

/** data-action handler. Returns true when handled. */
export async function boardAction(action,data,el,env){
  if(action!=='nhom'&&!action?.startsWith('bd'))return false;
  E=E||env;
  const {api,ui,cmd,renderSheet}=env;
  switch(action){
    case'nhom':await openBoard(env);return true;
    case'bdReload':await fetchBoard(api);renderSheet();return true;
    case'bdMore':B.open.add(data.post);renderSheet();return true;
    case'bdLess':B.open.delete(data.post);renderSheet();return true;
    case'bdOlder':await fetchBoard(api,{older:true});renderSheet();return true;
    case'bdMention':B.mention=!B.mention;renderSheet();return true;
    case'bdAt':{const ta=document.getElementById('bd-new');if(ta){const v=ta.value,add=`@${data.name} `;ta.value=(v&&!/\s$/.test(v)?v+' ':v)+add;ta.focus();}B.mention=false;renderSheet();document.getElementById('bd-new')?.focus();return true;}
    case'bdReact':{
      const p=[...(B.data?.posts||[]),...B.older].find(x=>x.id===data.post);if(!p)return true;
      const r=p.mine===data.r?null:data.r;
      const res=await cmd('bd_react',{post:p.id,r},{quiet:true});
      if(res){if(p.mine)p.react[p.mine]=Math.max(0,p.react[p.mine]-1);p.mine=res.mine;if(p.mine)p.react[p.mine]+=1;renderSheet();}
      return true;}
    case'bdTone':{
      if(B.pending)return true;
      const p=B.data?.posts.find(x=>x.id===data.post);if(!p)return true;
      B.pending={post:p.id,text:data.tone==='ignore'?'🤐':({clarify:'Mình giải thích một chút…',joke:'😄',confront:'@'+who(p.rumour?.by,api).name+' …'}[data.tone]||'…')};B.open.add(p.id);renderSheet();
      const out=await send(env,{op:'reply',post:p.id,tone:data.tone},['bd_reply',{post:p.id,tone:data.tone}]);
      if(out)await seen(env);
      return true;}
  }
  return false;
}

/** Composer and reply forms (data-bd-form). */
export async function boardSubmit(f,env){
  const kind=f.dataset.bdForm;if(!kind)return false;
  const {api,renderSheet}=env;
  if(B.pending)return true;
  const input=f.querySelector('[name="text"]'),text=(input?.value||'').trim();
  if(!text){input?.focus();return true;}
  if(kind==='post'){
    B.pending={post:'new',text};input.value='';renderSheet();
    const out=await send(env,{op:'post',text},['bd_post',{text}]);
    if(!out){const ta=document.getElementById('bd-new');if(ta&&!ta.value)ta.value=text;}
    else{document.getElementById('sheet')?.scrollTo?.({top:0,behavior:'smooth'});await seen(env);}
    return true;
  }
  if(kind==='reply'){
    const post=f.dataset.post;
    B.pending={post,text};B.open.add(post);input.value='';renderSheet();
    const out=await send(env,{op:'reply',post,text},['bd_reply',{post,text}]);
    if(!out){const el=document.getElementById('bd-r-'+post);if(el&&!el.value)el.value=text;}
    else await seen(env);
    return true;
  }
  return false;
}
