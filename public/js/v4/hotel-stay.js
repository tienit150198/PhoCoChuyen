/** 🏨 Sổ phòng: a homestay / hotel player rents rooms to other players (game/hotel_stay.py holds every rule and number;
 * the price, escrow, 95 % / 5 % and refunds are Phố dịch vụ's).
 * Two tabs: 🛎️ Quầy đón khách (the host: confirm a booking, check a guest in with a room and the arrival quirk, the night's
 * "oái oăm" situations and the guest's requests, check-out) and 🧳 Phòng của tôi (the guest: I'm here, requests,
 * leave early, the rest I got, ⭐ rating). The server lists each stay's next actions.
 * GET /api/hotel/view · POST /api/hotel/confirm|decline|cancel|arrive|checkin|handle|ask|leave|checkout · /api/svc/rate. */
import {escapeHTML as esc,icon} from '../icons.js';
import {stylesheet} from '../lazy.js';
import {avInner} from './face.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const TABS=[['host','🛎️','Quầy đón khách'],['guest','🧳','Phòng của tôi']];
const STAGE={held:'Chờ chủ nhà xác nhận',booked:'Đã đặt · chờ khách tới',arrived:'Khách đang ở quầy',in:'Đang ở',out:'Đã trả phòng',gone:'Đã hủy · hoàn tiền'};
const GSTAGE={held:'Chờ chủ nhà xác nhận',booked:'Đã xác nhận · tới nơi thì bấm “Tôi tới rồi”',arrived:'Chờ chủ nhà nhận phòng',in:'Đang ở',out:'Đã trả phòng',gone:'Đã hủy · hoàn tiền'};
const S={dlg:null,env:null,tab:'',v:null,busy:false,loading:false,flash:null,pick:{},arm:'',armT:0,timer:0,tick:0,seq:0,skew:0,stars:{},focus:''};

function ensureCss(){return Promise.all([stylesheet('/css/spend.css'),stylesheet('/css/hotel-stay.css')]);}
const api=()=>S.env.api;
const wallet=()=>Math.max(0,Number(api().state?.journey?.wallet)||0);
const face=w=>`<span class="hs-av" aria-hidden="true">${avInner({fc:w?.fc,av:w?.avatar||'🙂'})}</span>`;
const btn=(label,op,data={},cls='ghost',extra='')=>`<button type="button" class="btn ${cls}" data-hs="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${S.busy?' disabled':''}${extra}>${label}</button>`;
const nowS=()=>Date.now()/1000+S.skew;
function left(due){const s=Math.max(0,Math.round(due-nowS()));const h=Math.floor(s/3600),m=Math.floor(s%3600/60);return s<=0?'Hết giờ':h?`${h} giờ ${m} phút`:m?`${m} phút`:`${s} giây`;}
const moodFace=m=>m>=85?'😍':m>=70?'😊':m>=50?'🙂':m>=30?'😕':'😠';

export async function openHotel(env,data={}){
  S.env=env;
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet?.();
  await ensureCss();
  if(!S.dlg){
    const d=document.createElement('dialog');
    d.className='sheet v4-sheet medium sd-sheet hs-sheet';d.setAttribute('aria-labelledby','hs-title');
    d.innerHTML='<div class="sd-root"></div>';document.body.append(d);S.dlg=d;
    d.addEventListener('click',e=>{if(e.target===d){d.close();return;}const el=e.target.closest('[data-hs]');if(!el||el.disabled)return;e.preventDefault();click(el.dataset.hs,el.dataset);});
    d.addEventListener('close',()=>{clearInterval(S.timer);clearInterval(S.tick);S.seq++;document.removeEventListener('visibilitychange',visible);});
  }
  S.flash=null;S.focus=data.order||'';
  if(data.tab)S.tab=data.tab;
  if(!S.dlg.open){S.dlg.showModal();S.dlg.scrollTop=0;}
  render();
  await load();
  document.addEventListener('visibilitychange',visible);
  clearInterval(S.timer);S.timer=setInterval(()=>{if(!document.hidden&&S.dlg?.open&&!S.busy)load(true);},15000);
  clearInterval(S.tick);S.tick=setInterval(()=>{if(!S.dlg?.open)return;S.dlg.querySelectorAll('[data-due]').forEach(el=>{el.textContent=left(Number(el.dataset.due));});},1000);
}
function visible(){if(!document.hidden&&S.dlg?.open)load(true);}

function pickTab(v){
  if(S.tab)return;
  const mine=v.guest.stays.length+v.guest.pending.length,host=v.host.stays.length+v.host.pending.length;
  const hit=S.focus&&[...v.guest.stays,...v.guest.pending].some(x=>x.id===S.focus);
  S.tab=hit?'guest':(host||v.careers.length)&&!(mine&&!host)?'host':'guest';
}
async function load(quiet=false){
  const seq=++S.seq;if(!quiet){S.loading=true;render();}
  try{const v=await api().json('/api/hotel/view');if(seq!==S.seq)return;S.v=v;S.skew=(Number(v.now)||Date.now()/1000)-Date.now()/1000;pickTab(v);}
  catch(e){if(seq===S.seq)S.flash={kind:'bad',text:e.message||'Chưa tải được. Thử lại nhé.'};}
  finally{if(seq===S.seq){S.loading=false;render(quiet);}}   // 23/10 lag: a background poll redraws only when the page changed
}
async function post(route,body){
  if(S.busy)return null;S.busy=true;S.flash=null;render();
  try{
    const r=await api().post(route,body);
    S.flash=r?.message?{kind:'good',text:r.message}:null;
    if(r?.view){S.v=r.view;S.skew=(Number(r.view.now)||Date.now()/1000)-Date.now()/1000;}
    api().refresh?.().then(()=>render()).catch(()=>{});   // the wallet chip follows the save (a cost paid, a stay paid)
    return r;
  }catch(e){S.flash={kind:'bad',text:e.message||'Chưa gửi được. Thử lại nhé.'};return null;}
  finally{S.busy=false;render();}
}
/** decline / cancel move money back: a second tap within 4 s confirms */
function armed(key){if(S.arm===key)return true;S.arm=key;clearTimeout(S.armT);S.armT=setTimeout(()=>{S.arm='';render();},4000);render();return false;}

async function click(op,d){
  if(op==='close'){S.dlg.close();return;}
  if(op==='tab'){S.tab=d.tab;S.flash=null;render();return;}
  if(op==='retry'){await load();return;}
  if(op==='market'){S.dlg.close();S.env.act('svcMarket',{tab:d.tab||'dir'});return;}
  if(op==='room'){(S.pick[d.id]??={}).room=d.room;render();return;}
  if(op==='quirk'){(S.pick[d.id]??={}).quirk=d.pick;render();return;}
  if(op==='star'){S.stars[d.id]=Number(d.n);render();return;}
  const id=d.id;
  if(op==='confirm'){await post('/api/hotel/confirm',{order:id});return;}
  if(op==='decline'||op==='cancel'){if(!armed(op+id))return;S.arm='';await post('/api/hotel/'+op,{order:id});return;}
  if(op==='arrive'||op==='leave'){await post('/api/hotel/'+op,{order:id});return;}
  if(op==='checkin'){const p=S.pick[id]||{};if(!p.room||!p.quirk)return;const r=await post('/api/hotel/checkin',{order:id,room:p.room,pick:p.quirk});if(r)delete S.pick[id];return;}
  if(op==='handle'){await post('/api/hotel/handle',{order:id,ev:d.ev,pick:d.pick});return;}
  if(op==='ask'){await post('/api/hotel/ask',{order:id,ask:d.ask});return;}
  if(op==='checkout'){await post('/api/hotel/checkout',{order:id,pick:d.pick});return;}
  if(op==='rate'){
    if(S.busy)return;S.busy=true;S.flash=null;render();
    try{const r=await api().post('/api/svc/rate',{order:id,stars:S.stars[id]||5});S.flash={kind:'good',text:r?.message||'Cảm ơn bạn đã đánh giá!'};}
    catch(e){S.flash={kind:'bad',text:e.message||'Chưa gửi được.'};}
    finally{S.busy=false;}
    await load(true);return;
  }
}

/* ---------------------------------------------------------------- views */
function render(same=false){
  if(!S.dlg)return;
  const root=S.dlg.querySelector('.sd-root'),top=S.dlg.scrollTop,html=page();
  if(!(same&&root._h===html)){root.innerHTML=html;root._h=html;S.dlg.scrollTop=top;}
  S.dlg.setAttribute('aria-busy',String(!!(S.busy||S.loading)));
}
function page(){
  const t=TABS.find(x=>x[0]===S.tab)||TABS[0],v=S.v;
  const need=v?v.host.stays.filter(x=>hostNeeds(x)).length+v.host.pending.length:0;
  const head=`<div class="hs-stick"><header class="sheet-head sd-head"><span class="sd-logo" aria-hidden="true">🏨</span><div class="grow"><h2 id="hs-title">Sổ phòng</h2><small class="hs-sub">${esc(t[2])}</small></div>
    <span class="sd-wallet" title="Ví">👛 ${fmt(wallet())}</span><button class="icon-btn" type="button" data-hs="close" aria-label="Đóng">${icon('x',21)}</button></header>
    <nav class="sd-tabs" role="tablist" aria-label="Sổ phòng">${TABS.map(([id,e,l])=>`<button type="button" role="tab" aria-selected="${t[0]===id}" aria-label="${esc(l)}" title="${esc(l)}" class="${t[0]===id?'on':''}" data-hs="tab" data-tab="${id}">${e} <small>${esc(l)}</small>${id==='host'&&need?`<em class="badge">${need}</em>`:''}</button>`).join('')}</nav></div>`;
  const flash=`<p class="sd-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  let body;
  if(!v)body=S.loading?'<p class="sd-empty">⏳</p>':`<p class="sd-empty">🏨</p>${btn('Thử lại','retry')}`;
  else body=(v.off?'<p class="hs-off">🛑 Sổ phòng đang tạm đóng nhận khách mới. Phòng đã đặt vẫn trả phòng / hoàn tiền bình thường.</p>':'')+(t[0]==='host'?hostView(v):guestView(v));
  return head+`<div class="sheet-body sd-body">${body}</div><div class="sd-bar hs-bar">${flash}</div>`;
}
const hostNeeds=x=>x.actions.includes('checkin')||x.actions.includes('checkout')||x.events.some(e=>e.st==='open'&&e.opts);
const sec=(title,rows,fn)=>rows.length?`<section class="hs-sec"><h3 class="tp-h">${title} <small>${rows.length}</small></h3>${rows.map(fn).join('')}</section>`:'';
const svcLine=x=>`${esc(x.icon)} ${esc(x.name)}${x.qty>1?` · ${x.qty} ${esc(x.unit)}`:''}`;

function hostView(v){
  const c=v.card,selling=v.selling.length;
  const intro=!v.careers.length&&!v.host.stays.length&&!v.host.pending.length
    ?`<section class="sd-card hs-empty"><p class="tp-big">🏨</p><h3>Chưa có phòng cho thuê</h3><p class="hs-note">Làm nghề Homestay hoặc Khách sạn để cho người chơi khác thuê phòng.</p></section>`
    :`<section class="sd-card hs-desk"><div class="hs-row"><div class="grow"><h3>Quầy đón khách</h3>
      <p class="hs-meta">${c.stays?`${moodFace(c.mood)} Hài lòng TB <b>${c.mood}%</b> · ${fmt(c.stays)} lượt khách · xử lý ${fmt(c.handled)} · bỏ lỡ ${fmt(c.missed)}`:'Chưa có lượt khách nào.'}</p></div></div>
      ${selling?`<p class="hs-note">Đang mở ${selling} loại phòng ở 🛎️ Phố dịch vụ. Khách trả ×${v.rules.default_mult} giá thường, bạn nhận ${100-v.rules.fee_pct}% khi trả phòng.</p>${btn('🧰 Giá & bật/tắt phòng','market',{tab:'mine'},'ghost')}`
        :`<p class="hs-note">Bạn chưa mở bán phòng nào. Mở ở 🛎️ Phố dịch vụ › 🧰 Dịch vụ của tôi.</p>${btn('🧰 Mở bán phòng','market',{tab:'mine'},'primary')}`}</section>`;
  const need=v.host.stays.filter(hostNeeds),live=v.host.stays.filter(x=>x.stage==='in'&&!hostNeeds(x)),booked=v.host.stays.filter(x=>x.stage==='booked'),past=v.host.stays.filter(x=>x.stage==='out'||x.stage==='gone');
  const empty=!need.length&&!live.length&&!booked.length&&!v.host.pending.length&&(v.careers.length||past.length)?'<p class="hs-note hs-center">Chưa có khách nào đang chờ. Khách đặt phòng sẽ hiện ở đây.</p>':'';
  return intro+(v.host.pending.length||need.length?`<section class="hs-sec"><h3 class="tp-h">🔔 Cần bạn <small>${v.host.pending.length+need.length}</small></h3>${v.host.pending.map(pendingHost).join('')}${need.map(hostCard).join('')}</section>`:'')
    +sec('⏳ Đang ở',live,hostCard)+sec('📅 Chờ khách tới',booked,hostCard)+empty+sec('✅ Gần đây',past.slice(0,10),pastCard);
}
function pendingHost(p){
  const arm=S.arm==='decline'+p.id;
  return `<article class="hs-card${S.focus===p.id?' focus':''}"><div class="hs-row">${face(p.who)}<div class="grow"><b>${esc(p.who?.name||'')}</b><small class="hs-muted">${svcLine(p)}</small></div><span class="hs-price"><b>${fmt(p.price)}</b> <small>xu</small></span></div>
    <p><span class="hs-pill s-held">🔔 Đặt phòng mới · tiền đã giữ</span></p>${p.note?`<blockquote>${esc(p.note)}</blockquote>`:''}
    <div class="hs-acts">${btn('✅ Xác nhận phòng','confirm',{id:p.id},'primary')}${btn(arm?'Bấm lần nữa':'Từ chối','decline',{id:p.id},arm?'danger':'ghost')}</div></article>`;
}
function stayHead(x,who){
  return `<div class="hs-row">${face(who)}<div class="grow"><b>${esc(who?.name||'')}${x.partner&&x.role==='host'?` <small>& ${esc(x.partner.name)}</small>`:''}</b><small class="hs-muted">${svcLine(x)}${x.room?` · ${esc(x.room.icon)} ${esc(x.room.name)}`:''}</small></div><span class="hs-price"><b>${fmt(x.price)}</b> <small>xu</small></span></div>`;
}
function hostCard(x){
  const arm=S.arm==='decline'+x.id;
  let body='';
  if(x.stage==='arrived'){
    const p=S.pick[x.id]||{},q=x.quirk;
    body+=x.wish?`<p class="hs-say"><span>${esc(x.wish.icon)}</span> “${esc(x.wish.text)}”</p>`:'';
    body+=x.temper?`<p class="hs-hint">${esc(x.temper.icon)} ${esc(x.temper.hint)}</p>`:'';
    if(q)body+=`<div class="hs-ev open"><p class="hs-evt"><span class="hs-evi">${esc(q.icon)}</span>${esc(q.text)}</p><div class="hs-opts" role="radiogroup" aria-label="Cách xử lý">${q.opts.map(o=>`<button type="button" role="radio" aria-checked="${p.quirk===o.id}" class="hs-opt${p.quirk===o.id?' on':''}" data-hs="quirk" data-id="${esc(x.id)}" data-pick="${esc(o.id)}"${S.busy?' disabled':''}><span>${esc(o.label)}</span>${o.cost?`<em class="hs-cost">−${o.cost} xu</em>`:''}</button>`).join('')}</div></div>`;
    body+=`<p class="hs-lbl">Xếp phòng</p><div class="hs-rooms" role="radiogroup" aria-label="Chọn phòng">${(x.rooms||[]).map(r=>`<button type="button" role="radio" aria-checked="${p.room===r.id}" class="hs-room${p.room===r.id?' on':''}" data-hs="room" data-id="${esc(x.id)}" data-room="${esc(r.id)}"${r.busy||S.busy?' disabled':''}><b>${esc(r.icon)} ${esc(r.name)}</b><small>${r.busy?'Đang có khách':esc(r.note)}</small></button>`).join('')}</div>`;
    body+=`<div class="hs-acts">${btn('🔑 Nhận phòng','checkin',{id:x.id},'primary',p.room&&p.quirk?'':' disabled')}${btn(arm?'Bấm lần nữa':'Hủy lượt','decline',{id:x.id},arm?'danger':'ghost')}</div>`;
  }else if(x.stage==='booked'){
    body+=`<p class="hs-note">Khách chưa tới. Quá ${S.v.rules.arrive_hours} giờ không tới thì tự hủy, hoàn tiền khách.</p><div class="hs-acts">${btn(arm?'Bấm lần nữa':'Hủy lượt','decline',{id:x.id},arm?'danger':'ghost')}</div>`;
  }else if(x.stage==='in'){
    body+=`<p class="hs-time">⏳ <span data-due="${x.due}">${left(x.due)}</span>${x.late?' <small>· đã cho trả muộn</small>':''}${x.want_out?' <span class="hs-pill s-out">🧳 Khách muốn trả phòng</span>':''}</p>${moodBar(x.mood)}`;
    for(const e of x.events.filter(e=>e.st==='open'&&e.opts))body+=evCard(x,e);
    if(x.actions.includes('checkout')&&x.out_quirk){
      const q=x.out_quirk;
      body+=`<div class="hs-ev open out"><p class="hs-lbl">🧾 Trả phòng</p><p class="hs-evt"><span class="hs-evi">${esc(q.icon)}</span>${esc(q.text)}</p><div class="hs-opts">${q.opts.map(o=>btn(`<span>${esc(o.label)}</span>${o.cost?`<em class="hs-cost">−${o.cost} xu</em>`:''}`,'checkout',{id:x.id,pick:o.id},'hs-opt')).join('')}</div><p class="hs-muted">Chọn một cách là trả phòng luôn: bạn nhận ${100-S.v.rules.fee_pct}% tiền phòng.</p></div>`;
    }
    body+=log(x,true);
  }
  return `<article class="hs-card${S.focus===x.id?' focus':''}">${stayHead(x,x.guest)}<p><span class="hs-pill s-${esc(x.stage)}">${esc(STAGE[x.stage]||x.stage)}</span></p>${body}</article>`;
}
function evCard(x,e){
  const who=e.k==='ask'?`<span class="hs-pill s-ask">🙋 Khách nhờ</span> `:'';
  return `<div class="hs-ev open"><p class="hs-evt"><span class="hs-evi">${esc(e.icon)}</span>${who}${esc(e.text)}</p><div class="hs-opts">${e.opts.map(o=>btn(`<span>${esc(o.label)}</span>${o.cost?`<em class="hs-cost">−${o.cost} xu</em>`:''}`,'handle',{id:x.id,ev:e.key,pick:o.id},'hs-opt')).join('')}</div></div>`;
}
const moodBar=m=>`<div class="hs-mood" role="img" aria-label="Hài lòng ${m}%"><span>${moodFace(m)}</span><i><b style="width:${Math.max(0,Math.min(100,m))}%"></b></i><small>${m}%</small></div>`;
function log(x,host){
  const rows=x.events.filter(e=>e.st!=='open'&&(e.reply||e.text));
  if(!rows.length)return '';
  return `<details class="hs-log"${host?'':' open'}><summary>Nhật ký phòng (${rows.length})</summary><ul>${rows.map(e=>`<li class="${e.st==='miss'?'miss':''}"><span>${esc(e.icon)}</span><span>${esc(e.reply||e.text)}${host&&e.d?` <small class="${e.d>0?'up':'down'}">${e.d>0?'+':''}${e.d}</small>`:''}</span></li>`).join('')}</ul></details>`;
}
function pastCard(x){
  const st=x.result?.stay;
  return `<article class="hs-card small">${stayHead(x,x.role==='host'?x.guest:x.host)}<p><span class="hs-pill s-${esc(x.stage)}">${esc((x.role==='host'?STAGE:GSTAGE)[x.stage]||x.stage)}</span>${st?` <span class="hs-muted hs-inline">${moodFace(st.mood)} Hài lòng ${st.mood}%${st.auto?' · tự trả phòng':''}</span>`:''}</p></article>`;
}

function guestView(v){
  const g=v.guest,live=g.stays.filter(x=>x.stage!=='out'&&x.stage!=='gone'),past=g.stays.filter(x=>x.stage==='out'||x.stage==='gone');
  if(!live.length&&!g.pending.length&&!past.length)return `<section class="sd-card hs-empty"><p class="tp-big">🧳</p><h3>Chưa đặt phòng nào</h3><p class="hs-note">Thuê phòng của người chơi làm Homestay hoặc Khách sạn: ngủ một đêm cho tỉnh táo, no bụng, tinh thần lên. Mỗi ngày được nghỉ một lần.</p>${btn('🔎 Tìm phòng ở Phố dịch vụ','market',{tab:'dir'},'primary')}</section>`;
  return sec('⏳ Đang chờ xác nhận',g.pending,pendingGuest)+sec('🛏️ Phòng của tôi',live,guestCard)+sec('✅ Đã ở',past.slice(0,10),guestPast)
    +(live.length||g.pending.length?'':`<div class="hs-acts">${btn('🔎 Đặt phòng khác','market',{tab:'dir'},'ghost full')}</div>`);
}
function pendingGuest(p){
  const arm=S.arm==='cancel'+p.id;
  return `<article class="hs-card">${`<div class="hs-row">${face(p.who)}<div class="grow"><b>${esc(p.who?.name||'')}</b><small class="hs-muted">${svcLine(p)}</small></div><span class="hs-price"><b>${fmt(p.price)}</b> <small>xu</small></span></div>`}
    <p><span class="hs-pill s-held">${esc(GSTAGE.held)}</span></p><p class="hs-muted">Tiền đã giữ. Chủ nhà từ chối hoặc 24 giờ chưa xác nhận: hoàn đủ.</p><div class="hs-acts">${btn(arm?'Bấm lần nữa':'Hủy đặt phòng','cancel',{id:p.id},arm?'danger':'ghost')}</div></article>`;
}
function guestCard(x){
  const arm=S.arm==='cancel'+x.id;
  let body='',acts='';
  if(x.stage==='booked'){body+=`<p class="hs-note">Tới nơi thì bấm “Tôi tới rồi” để chủ nhà nhận phòng cho bạn.</p>`;acts+=btn('🧳 Tôi tới rồi','arrive',{id:x.id},'primary');}
  if(x.stage==='arrived')body+=`<p class="hs-note">🛎️ Bạn đang ở quầy, chờ chủ nhà nhận phòng…${x.waited>=S.v.rules.wait_min*60?' Chủ nhà đang vắng: bạn có thể hủy để được hoàn đủ tiền.':''}</p>`;
  if(x.actions.includes('cancel'))acts+=btn(arm?'Bấm lần nữa':'Hủy · hoàn tiền','cancel',{id:x.id},arm?'danger':'ghost');
  if(x.stage==='in'){
    body+=`<p class="hs-time">⏳ Còn <span data-due="${x.due}">${left(x.due)}</span>${x.late?' <small>· được trả muộn</small>':''}</p>`;
    const open=x.events.filter(e=>e.st==='open'&&e.k==='ask');
    if(open.length)body+=`<p class="hs-muted">🙋 Đang chờ chủ nhà: ${open.map(e=>esc(e.ask||e.text)).join(', ')}</p>`;
    if(x.actions.includes('ask')&&x.asks?.length)body+=`<p class="hs-lbl">Nhờ chủ nhà <small>(tối đa ${S.v.rules.ask_max} việc mỗi lượt)</small></p><div class="sd-chips hs-asks">${x.asks.map(a=>btn(`${esc(a.icon)} ${esc(a.label)}`,'ask',{id:x.id,ask:a.id},'sd-chip')).join('')}</div>`;
    if(x.want_out)body+=`<p class="hs-note">🧳 Đã báo trả phòng. Chủ nhà làm thủ tục, hoặc tự trả sau ${S.v.rules.grace_min} phút.</p>`;
    if(x.actions.includes('leave'))acts+=btn('🧳 Trả phòng sớm','leave',{id:x.id},'ghost');
    body+=log(x,false);
  }
  return `<article class="hs-card${S.focus===x.id?' focus':''}">${stayHead(x,x.host)}<p><span class="hs-pill s-${esc(x.stage)}">${esc(GSTAGE[x.stage]||x.stage)}</span>${x.partner?` <small class="hs-muted hs-inline">💞 cùng ${esc(x.partner_me?x.guest.name:x.partner.name)}</small>`:''}</p>${body}${acts?`<div class="hs-acts">${acts}</div>`:''}</article>`;
}
function restLine(r){return r?[r.wake?`😴 +${r.wake} tỉnh táo`:'',r.full?`🍳 +${r.full} no bụng`:'',r.spirit?`✨ +${r.spirit} tinh thần`:''].filter(Boolean).join(' · '):'';}
function guestPast(x){
  const res=x.result,st=res?.stay;
  if(x.stage==='gone'||!st)return pastCard(x);
  const mine=x.partner_me?res.rest?.partner:res.rest?.guest;
  const rest=restLine(mine);
  const n=S.stars[x.id]||st.stars||5;
  const rate=x.actions.includes('rate')?`<div class="hs-rate"><p class="hs-lbl">⭐ Chấm điểm chủ nhà</p><div class="svc-starpick hs-stars" role="radiogroup" aria-label="Số sao">${[1,2,3,4,5].map(k=>`<button type="button" role="radio" aria-checked="${n===k}" class="hs-star${n>=k?' on':''}" data-hs="star" data-id="${esc(x.id)}" data-n="${k}" aria-label="${k} sao">★</button>`).join('')}</div>${btn('Gửi đánh giá','rate',{id:x.id},'primary')}</div>`:x.rated?'<p class="hs-muted">Đã đánh giá. Cảm ơn bạn!</p>':'';
  return `<article class="hs-card">${stayHead(x,x.host)}<p><span class="hs-pill s-out">${esc(GSTAGE.out)}</span> <span class="hs-muted hs-inline">${moodFace(st.mood)} Hài lòng ${st.mood}%</span></p>
    <p class="hs-rest">${rest?`🌙 ${rest}`:'🌙 Hôm nay bạn đã nghỉ ngơi một lần rồi: lượt này không cộng thêm.'}</p>${log(x,false)}${rate}</article>`;
}
