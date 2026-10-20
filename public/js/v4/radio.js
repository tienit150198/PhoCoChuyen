/** radio.js — 📻 Đơn lên sóng at Đài phát thanh Sóng Mây (game/radio_station.py, owner 21/10). One dialog:
 *   the DJ's orders from other players (📢 a shop's ad, 🎵 a song with a message, bought in 🛎️ Phố dịch vụ): the line as it will
 *   run on the town ticker, the server's moderation verdict, the background music or the song to pick, a "đã đọc kỹ" box,
 *   🔴 Lên sóng (POST /api/radio/air: takes and delivers the order; the market pays 95 %) or Từ chối (POST /api/svc/decline: the
 *   buyer gets everything back);
 *   what is on the ticker now (at most the server's cap), the day's caps, and my own lines (as buyer or DJ) to take down.
 * Every rule is the server's; this file shows and sends. Opened by app.js handleAction('radioDesk'). Styles: /css/radio.css.
 * Phone first (390 px), also landscape. Text goes in escaped. */
import {escapeHTML as esc,icon} from '../icons.js';
import {stylesheet} from '../lazy.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const S={dlg:null,env:null,busy:false,flash:null,desk:null,svc:null,pick:{},ok:{}};
const STATUS={held:'⏳ Chờ bạn nhận',working:'🎙️ Đã nhận, chờ lên sóng'};
const KIND={quang_cao:['📢','Quảng cáo tiệm'],tang_bai:['🎵','Bài hát tặng']};
const api=()=>S.env.api;
let COUNT={at:0,n:0,go:null};

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium rd-sheet';d.setAttribute('aria-labelledby','rd-title');
  d.innerHTML='<div class="rd-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-rd]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.rd,el.dataset).catch(err=>{console.warn('📻',err);flash(err.message||'Chưa làm được. Thử lại nhé.',false);});
  });
  d.addEventListener('change',e=>{const t=e.target;
    if(t.dataset.rdPick!=null){S.pick[t.dataset.rdPick]=t.value;render();}
    else if(t.dataset.rdOk!=null){S.ok[t.dataset.rdOk]=t.checked;render();}});
  return S.dlg=d;
}
function flash(text,good=true){S.flash=text?{text,good}:null;render();}
async function load(){
  // my two services as Phố dịch vụ has them (on / off; 🎵 locked until the DJ is past probation: its `why`, or not listed)
  api().json('/api/svc/mine').then(m=>{S.svc=(m.services||[]).filter(x=>x.career==='radio');render();}).catch(()=>{});
  try{S.desk=await api().json('/api/radio/desk');COUNT={at:Date.now(),n:waiting(S.desk),go:null};}
  catch(e){S.flash={text:e.message||'Chưa tải được. Thử lại nhé.',good:false};}
  render();
}
const waiting=d=>(d?.orders||[]).filter(o=>o.status==='held'||o.status==='working').length;
async function post(url,body){
  if(S.busy)return null;S.busy=true;render();
  try{const r=await api().post(url,body,20000);
    if(r?.state&&typeof r.revision==='number')api().accept({state:r.state,revision:r.revision});
    S.flash=r?.message?{text:r.message,good:true}:null;return r;}
  catch(e){S.flash={text:e.message||'Chưa gửi được. Thử lại nhé.',good:false};return null;}
  finally{S.busy=false;render();}
}

/** app.js handleAction('radioDesk'). */
export async function radioAction(env){
  S.env=env;await stylesheet('/css/radio.css');
  const d=dialog();S.flash=null;
  if(!d.open){d.showModal();d.scrollTop=0;}
  S.desk=null;render();await load();
}
/** The badge on 📻 Đơn lên sóng (careers/radio.js): the orders waiting, cached half a minute. */
export function queueCount(env){
  S.env=S.env||env;
  if(Date.now()-COUNT.at<30000)return Promise.resolve(COUNT.n);
  return COUNT.go??=env.api.json('/api/radio/desk').then(d=>{COUNT={at:Date.now(),n:waiting(d),go:null};return COUNT.n;})
    .catch(()=>{COUNT.go=null;return COUNT.n;});
}

async function onClick(op,data){
  if(op==='close'){S.dlg.close();return;}
  if(op==='reload'){await load();return;}
  if(op==='air'){
    const o=(S.desk?.orders||[]).find(x=>x.id===data.id);if(!o)return;
    const r=await post('/api/radio/air',{order:o.id,pick:S.pick[o.id]||o.picks[0]?.id,ok:Boolean(S.ok[o.id])});
    if(r){delete S.pick[o.id];delete S.ok[o.id];await load();}
    return;
  }
  if(op==='decline'){const r=await post('/api/svc/decline',{order:data.id});if(r)await load();return;}
  if(op==='hide'){const r=await post('/api/radio/hide',{line:data.id});if(r)await load();return;}
  if(op==='market'){S.dlg.close();await S.env.act?.('svcMarket',{tab:'mine'});}
}

/** The empty desk's line: what is on, what to switch on, and why 🎵 is not there yet (only what applies). */
function svcHint(){
  if(!S.svc)return '';
  const ad=S.svc.find(x=>x.service==='quang_cao'),song=S.svc.find(x=>x.service==='tang_bai');
  const songWhy=!song?'Gửi bài hát tặng cần DJ: làm phát thanh viên hết thử việc trước đã.':song.why||'';
  const on=[ad?.on&&'📢 quảng cáo',song?.on&&!song.why&&'🎵 bài hát tặng'].filter(Boolean);
  const off=[ad&&!ad.on&&'📢 quảng cáo',song&&!song.on&&!song.why&&'🎵 bài hát tặng'].filter(Boolean);
  let out=on.length?`<p class="rd-muted rd-center">Đang nhận ${on.join(' và ')}. Đơn mới của người chơi hiện ở đây.</p>`:'';
  if(off.length)out+=`<p class="rd-muted rd-center">Chưa bật ${off.join(' và ')}: bật ở 🛎️ Phố dịch vụ → 🧰 Dịch vụ của tôi để người chơi đặt.</p>${btn('🛎️ Mở Phố dịch vụ','market',{},'ghost full')}`;
  if(songWhy)out+=`<p class="rd-muted rd-center">🔒 ${esc(songWhy)}</p>`;
  return out;
}

/* ---------------------------------------------------------------- render */
function render(){
  if(!S.dlg)return;
  const root=S.dlg.querySelector('.rd-root'),top=S.dlg.scrollTop;
  root.innerHTML=page();
  S.dlg.setAttribute('aria-busy',String(S.busy));
  S.dlg.scrollTop=top;
}
const btn=(label,op,data={},cls='',off=false)=>`<button type="button" class="btn ${cls}" data-rd="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${S.busy||off?' disabled':''}>${label}</button>`;
function page(){
  const head=`<header class="sheet-head rd-head"><span class="rd-logo" aria-hidden="true">📻</span><div class="grow"><h2 id="rd-title">Đơn lên sóng</h2><small>Đài phát thanh Sóng Mây · FM 99,9</small></div>
    <button class="icon-btn" type="button" data-rd="reload" aria-label="Tải lại"${S.busy?' disabled':''}><span aria-hidden="true">↻</span></button><button class="icon-btn" type="button" data-rd="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  const fl=S.flash?`<p class="rd-flash ${S.flash.good?'good':'bad'}" role="status">${esc(S.flash.text)}</p>`:'';
  return head+`<div class="sheet-body rd-body">${fl}${body()}</div>`;
}
function caps(c){
  return `<p class="rd-caps"><span>🔴 Trên sóng ${fmt(c.live)}/${fmt(c.live_max)}</span><span>🎙️ Hôm nay bạn lên sóng ${fmt(c.dj)}/${fmt(c.dj_max)}</span></p>
    <p class="rd-muted">Mỗi dòng chạy trên bảng tin cả phố: quảng cáo ${fmt(c.minutes?.quang_cao)} phút, bài hát tặng ${fmt(c.minutes?.tang_bai)} phút. Mỗi người mua tối đa ${fmt(c.buyer_max)} lượt một ngày.</p>`;
}
function orderCard(o){
  const [emoji,name]=KIND[o.kind]||['📻','Đơn'],pick=S.pick[o.id]||o.picks[0]?.id,ok=Boolean(S.ok[o.id]);
  const picks=`<fieldset class="rd-picks"><legend>${o.kind==='tang_bai'?'Chọn bài hát':'Chọn nhạc nền'}</legend>${o.picks.map(p=>`<label class="rd-pickrow${p.id===pick?' on':''}"><input type="radio" name="rd-pick-${esc(o.id)}" value="${esc(p.id)}" data-rd-pick="${esc(o.id)}"${p.id===pick?' checked':''}><span>${esc(p.label)}</span></label>`).join('')}</fieldset>`;
  const verdict=o.why?`<p class="rd-why" role="alert">⛔ ${esc(o.why)} Từ chối để khách nhận lại đủ tiền.</p>`
    :`<p class="rd-preview" aria-label="Dòng sẽ chạy trên bảng tin">${esc(o.preview)}</p>`;
  const check=o.why?'':`<label class="rd-okrow"><input type="checkbox" data-rd-ok="${esc(o.id)}"${ok?' checked':''}> <span>Đã đọc kỹ: không link, không số điện thoại, không lời xúc phạm ai</span></label>`;
  return `<article class="rd-order ${esc(o.status)}"><div class="rd-order-top"><span class="rd-kind" aria-hidden="true">${emoji}</span><div class="grow"><b>${esc(o.who)}</b><small><span>${esc(name)}</span> · <b>${fmt(o.price)} xu</b> · <span>${esc(STATUS[o.status]||o.status)}</span></small></div></div>
    <p class="rd-note">✏️ “${esc(o.note)}”</p>${verdict}${o.why?'':picks}${check}
    <div class="rd-row">${btn('Từ chối · hoàn tiền','decline',{id:o.id},'ghost')}${o.why?'':btn('🔴 Lên sóng','air',{id:o.id},'primary',!ok)}</div></article>`;
}
function lineRow(l){
  const tag=l.live?'<span class="rd-pill live">🔴 Đang chạy</span>':l.hidden?`<span class="rd-pill">Đã gỡ${l.hidden_by==='admin'?' (quản trị)':''}</span>`:'<span class="rd-pill">Đã hết giờ</span>';
  return `<li class="rd-line"><p>${esc(l.text)}</p><div class="rd-line-foot"><small>${esc(l.slot)}${l.role==='buyer'?' · bạn đặt':l.role==='dj'?' · bạn đọc':''}</small>${tag}${l.can_hide?btn('Gỡ khỏi bảng tin','hide',{id:l.id},'ghost small'):''}</div></li>`;
}
function body(){
  const d=S.desk;
  if(!d)return '<p class="rd-empty" role="status">⏳</p>';
  if(d.off)return '<p class="rd-empty">📻</p><p class="rd-muted rd-center">Đài Sóng Mây đang tạm nghỉ nhận đơn lên sóng. Quay lại sau nhé.</p>';
  const orders=d.orders.length?d.orders.map(orderCard).join('')
    :`<div class="rd-none"><p class="rd-empty" aria-hidden="true">🎙️</p><p class="rd-muted rd-center">Chưa có đơn nào chờ lên sóng.</p>${svcHint()}</div>`;
  const live=d.live.length?`<ul class="rd-lines">${d.live.map(lineRow).join('')}</ul>`:'<p class="rd-muted">Bảng tin chưa có dòng nào của người chơi.</p>';
  const mine=d.mine.length?`<details class="rd-mine"><summary>Dòng của tôi (${fmt(d.mine.length)})</summary><ul class="rd-lines">${d.mine.map(lineRow).join('')}</ul></details>`:'';
  return caps(d.caps)+`<h4>Đơn chờ lên sóng</h4>${orders}<h4>Đang chạy trên bảng tin</h4>${live}${mine}`;
}
