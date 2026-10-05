/** Consensual friend invitations; list data and public room projections never replace player state. */
import {escapeHTML as esc,icon} from '../icons.js';
import {live} from './live.js';

const S={env:null,dlg:null,data:null,code:'',busy:false,error:'',note:'',seq:0,timer:0};
const label=k=>k==='stay'?'Ở chung':'Vào chơi';
const homeName=h=>typeof h==='string'?h:h?.name||'Nhà của bạn';
const button=(text,op,data={},disabled=false)=>`<button type="button" class="btn cream" data-hg="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${disabled?' disabled':''}>${text}</button>`;
export function homeGuestsView(data,{code='',busy=false}={}){
  if(!data)return '<p role="status">Đang mở lời mời…</p>';
  const own=data.own_home,friends=data.friends||[],incoming=data.incoming||[],outgoing=data.outgoing||[],active=data.active||[],homes=data.homes||[];
  const card=(r,type)=>`<article class="hg-card"><span class="tag">${label(r.kind)}${type==='outgoing'?' · Chờ trả lời':''}</span><h3>${esc(r.name)}</h3><p>${esc(homeName(r.home))}</p>${r.kind==='visit'?'<p class="hg-muted">Vào chơi trong 2 giờ kể từ khi đồng ý.</p>':''}<div class="hg-actions">${type==='incoming'?button('Đồng ý','answer',{id:r.id,answer:'accept'},busy)+button('Từ chối','answer',{id:r.id,answer:'decline'},busy):button(type==='outgoing'?'Hủy lời mời':r.mine?'Thu hồi quyền vào nhà':'Rời nhà',type==='outgoing'||r.mine?'revoke':'leave',{id:r.id},busy)}</div></article>`;
  return `${incoming.length?`<section aria-label="Lời mời nhận được"><h3>Lời mời dành cho bạn</h3>${incoming.map(r=>card(r,'incoming')).join('')}</section>`:''}
    <section><h3>Nhà có thể vào</h3>${homes.length?homes.map(h=>`<article class="hg-card"><span class="tag">${label(h.kind)}</span><h3>🏡 Nhà ${esc(h.name)}</h3><p>${esc(homeName(h.home))}</p>${h.kind==='stay'?'<p class="hg-muted">Vào được cả khi chủ nhà vắng mặt.</p>':'<p class="hg-muted">Vào chơi trong 2 giờ kể từ khi đồng ý.</p>'}${button('🚪 Vào nhà','enter',{code:h.code},busy)}</article>`).join(''):'<p class="hg-muted">Đồng ý lời mời của bạn bè để vào nhà.</p>'}</section>
    <section class="hg-card"><h3>Mời bạn đến nhà</h3>${own?`<p>${esc(homeName(own.home))}</p>${friends.length?`<label class="field">Chọn bạn<select class="input" data-hg-friend><option value="">Chọn một người bạn</option>${friends.map(f=>`<option value="${esc(f.code)}"${code===f.code?' selected':''}>${esc(f.name)}</option>`).join('')}</select></label><div class="hg-invite-types"><div><b>Mời vào chơi</b><p>Vào chơi trong 2 giờ kể từ khi đồng ý.</p>${button('Mời vào chơi','invite',{kind:'visit'},busy||!friends.some(f=>f.code===code))}</div><div><b>Mời ở chung</b><p>Vào nhà lâu dài, kể cả khi bạn không online. Không cần kết hôn.</p>${button('Mời ở chung','invite',{kind:'stay'},busy||!friends.some(f=>f.code===code))}</div></div>`:`<p>Kết bạn trước để gửi lời mời.</p>${button('Mở Bạn bè','friends',{},busy)}`}`:`<p>Bạn cần đang ở căn nhà mình sở hữu để mời bạn bè.</p>${button('Chọn nhà của bạn','house',{},busy)}`}</section>
    ${outgoing.length?`<section><h3>Lời mời đã gửi</h3>${outgoing.map(r=>card(r,'outgoing')).join('')}</section>`:''}
    ${active.length?`<section><h3>Quản lý người ở & khách</h3>${active.map(r=>card(r,'active')).join('')}</section>`:''}
    <p class="hg-muted">Chủ nhà có thể thu hồi quyền vào nhà; người được mời có thể từ chối hoặc rời nhà.</p>`;
}

let css;
function styles(){return css??=new Promise(resolve=>{const el=document.createElement('link');el.rel='stylesheet';el.href=globalThis.__mnlBoot?.asset?.('/css/home-guests.css')||'/css/home-guests.css';el.onload=el.onerror=resolve;document.head.append(el);setTimeout(resolve,1500);});}
function render(){if(!S.dlg)return;S.dlg.querySelector('.hg-body').innerHTML=`${S.error?`<p class="hg-error" role="alert">${esc(S.error)}</p>`:''}${S.note?`<p role="status">${esc(S.note)}</p>`:''}${homeGuestsView(S.data,S)}<div class="hg-actions">${button('Làm mới','refresh',{},S.busy)}</div>`;S.dlg.setAttribute('aria-busy',String(S.busy));}
function remember(data){S.env.api.homeGuests=data;updateNotice(data,S.env);}
function schedule(){clearTimeout(S.timer);if(S.dlg?.open)S.timer=setTimeout(()=>{if(!document.hidden&&!S.busy)refresh();else schedule();},5000);}
async function refresh(){
  const seq=++S.seq;
  try{const data=await S.env.api.json('/api/home-guests');if(seq!==S.seq||!S.dlg?.open)return;S.data=data;S.error='';remember(data);render();}
  catch(e){if(seq===S.seq&&S.dlg?.open){S.error=e.message||'Chưa tải được lời mời.';render();}}
  finally{if(seq===S.seq)schedule();}
}
export async function openHomeGuests(env,{code=''}={}){
  S.env=env;await styles();S.code=code;S.data=null;S.error='';S.note='';
  if(!S.dlg){const d=document.createElement('dialog');d.className='sheet v4-sheet medium hg-sheet';d.setAttribute('aria-labelledby','hg-title');d.innerHTML=`<header class="sheet-head"><div class="grow"><span class="eyebrow">BẠN BÈ & NHÀ</span><h2 id="hg-title">Mời bạn đến nhà</h2></div><button type="button" class="icon-btn" data-hg="close" aria-label="Đóng">${icon('x',21)}</button></header><div class="sheet-body hg-body"></div>`;document.body.append(d);S.dlg=d;
    d.addEventListener('click',e=>{if(e.target===d){d.close();return;}const el=e.target.closest('[data-hg]');if(el&&!el.disabled){e.preventDefault();act(el.dataset.hg,el.dataset);}});
    d.addEventListener('change',e=>{if(e.target.matches('[data-hg-friend]')){S.code=e.target.value;render();}});
    d.addEventListener('close',()=>{S.seq++;clearTimeout(S.timer);S.busy=false;updateNotice(S.env.api.homeGuests,S.env);});
  }
  if(!S.dlg.open)S.dlg.showModal();render();updateNotice(env.api.homeGuests,env);await refresh();
}
export async function openGuestHome(env,code){
  try{await (await import('./reno.js')).openGuestReno(env,code);}
  catch(e){env.toast?.(e.message||'Chưa vào được nhà. Hãy làm mới lời mời.','error');}
}
async function act(op,data){
  if(op==='close'){S.dlg.close();return;}if(S.busy)return;
  if(op==='refresh'){await refresh();return;}
  if(op==='enter'){S.dlg.close();await openGuestHome(S.env,data.code);return;}
  if(op==='house'||op==='friends'){S.dlg.close();S.env.act(op==='house'?'house':'friends');return;}
  let body;if(op==='invite'){if(!(S.data?.friends||[]).some(f=>f.code===S.code))return;body={code:S.code,kind:data.kind};}
  else if(['answer','revoke','leave'].includes(op))body={id:String(data.id||''),...(op==='answer'?{answer:data.answer}:{})};else return;
  const seq=++S.seq;clearTimeout(S.timer);S.busy=true;S.error='';S.note='';render();
  try{const api=S.env.api;await api.json(`/api/home-guests/${op}`,{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify(body)});if(seq!==S.seq)return;S.note=op==='invite'?'Đã gửi lời mời. Chờ bạn đồng ý.':op==='answer'&&data.answer==='accept'?'Đã đồng ý. Chọn “Vào nhà” để ghé nhé.':'Đã cập nhật lời mời.';}
  catch(e){if(seq===S.seq)S.error=e.message||'Chưa thực hiện được.';}
  finally{if(seq===S.seq){S.busy=false;const error=S.error;await refresh();if(error){S.error=error;render();}}}
}

const N={env:null,button:null,seen:new Set(),account:'',reading:false};
function updateNotice(data,env){
  if(!N.button)return;
  const incoming=data?.incoming||[];
  N.button.hidden=!incoming.length||!!S.dlg?.open;
  N.button.textContent=`🏡 ${incoming.length} lời mời đến nhà · Xem`;
  for(const row of incoming){const key=String(row.id);if(!N.seen.has(key)){N.seen.add(key);env.toast?.(`${row.name} mời bạn ${row.kind==='stay'?'ở chung':'vào chơi'}. Mở Bạn bè & nhà để trả lời.`,'hint');}}
}
/** Discover new invitations once; keep an actionable button until answered. Poll only visible tabs. */
export function homeGuestsBoot(env){
  if(N.env)return;N.env=env;styles();const b=document.createElement('button');b.type='button';b.className='btn cream hg-notice';b.hidden=true;b.addEventListener('click',()=>openHomeGuests(env));document.body.append(b);N.button=b;
  const read=async()=>{if(document.hidden||N.reading)return;const account=env.api.account?.username||'';if(account!==N.account){N.account=account;N.seen.clear();env.api.homeGuests=null;b.hidden=true;}if(!account)return;N.reading=true;
    try{const data=await env.api.json('/api/home-guests');if(account!==env.api.account?.username)return;env.api.homeGuests=data;updateNotice(data,env);}catch{/* Opening the sheet offers a retry. */}finally{N.reading=false;}};
  live.on('home_guests_changed',()=>{read();if(S.dlg?.open&&!S.busy)refresh();});
  live.on('home_changed',()=>{read();if(S.dlg?.open&&!S.busy)refresh();});
  live.on('welcome',read);document.addEventListener('visibilitychange',read);env.api.addEventListener('state',()=>{if((env.api.account?.username||'')!==N.account)read();});setInterval(read,60000);read();
}
