/** 🧰 Phục chế đồ: players' broken or worn things restored by a 🧰 Thợ phục chế player (game/restore_service.py holds
 * every rule; money, prices and the 95 % / 5 % go through 🛎️ Phố dịch vụ, v4/service-market.js).
 * Three tabs: 🧳 Mang đồ đi (what my save can bring: a vehicle broken by rủi ro, a worn part of my home, a piece of furniture
 * to make cổ điển → a ticket, then the restorers in Phố dịch vụ), 🧰 Bàn thợ (the orders I took as a restorer: three steps,
 * then Giao đồ), ✨ Đã phục chế (the marks "đã phục chế bởi …" in my save).
 * GET /api/restore/mine|bench · POST /api/restore/ticket|drop|work · POST /api/svc/take|decline|done. */
import {escapeHTML as esc} from '../icons.js';
import {stylesheet} from '../lazy.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const TABS=[['mine','🧳','Mang đồ đi'],['bench','🧰','Bàn thợ'],['marks','✨','Đã phục chế']];
const STATUS={open:'Chờ chọn thợ',bound:'Thợ đang làm',done:'Đã xong',held:'Chờ thợ nhận',working:'Đang làm'};
const stars=g=>'⭐'.repeat(Math.max(1,Math.min(3,Number(g)||1)));
const S={dlg:null,env:null,tab:'mine',mine:null,bench:null,busy:false,flash:null,pick:null,style:'giu',seq:0};
const api=()=>S.env.api;
const btn=(label,op,data={},cls='ghost')=>`<button type="button" class="btn ${cls}" data-rs="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${S.busy?' disabled':''}>${label}</button>`;

export async function openRestore(env,data={}){
  S.env=env;
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet?.();
  await Promise.all([stylesheet('/css/spend.css'),stylesheet('/css/restore.css')]);
  if(!S.dlg){
    const d=document.createElement('dialog');
    d.className='sheet v4-sheet medium sd-sheet rs-sheet';d.setAttribute('aria-labelledby','rs-title');
    d.innerHTML='<div class="sd-root"></div>';document.body.append(d);S.dlg=d;
    d.addEventListener('click',e=>{if(e.target===d){d.close();return;}const el=e.target.closest('[data-rs]');if(!el||el.disabled)return;e.preventDefault();click(el.dataset.rs,el.dataset);});
    d.addEventListener('change',e=>{const t=e.target;if(t.name==='rs-style'){S.style=t.value;}});
  }
  S.flash=null;S.tab=TABS.some(t=>t[0]===data.tab)?data.tab:'mine';
  S.pick=data.service||data.ref||data.kind?{service:data.service||'',ref:data.ref||'',kind:data.kind||''}:null;
  if(!S.dlg.open){S.dlg.showModal();S.dlg.scrollTop=0;}
  render();await load();
}

async function load(){
  const seq=++S.seq;S.loading=true;render();
  try{
    if(S.tab==='bench')S.bench=await api().json('/api/restore/bench');
    else S.mine=await api().json('/api/restore/mine');
    if(seq!==S.seq)return;
    if(S.pick&&S.mine)resolvePick();
  }catch(e){if(seq===S.seq)S.flash={kind:'bad',text:e.message||'Chưa tải được. Thử lại nhé.'};}
  finally{if(seq===S.seq){S.loading=false;render();}}
}

/** An entry from elsewhere (rủi ro's broken list, a furniture piece): the item it names, in whichever service holds it. */
function resolvePick(){
  const p=S.pick;
  for(const s of S.mine.services){
    const it=s.items.find(x=>x.ref===p.ref||(p.kind==='nha'&&s.id==='nha'&&x.ref.startsWith(p.ref+':')));
    if(it&&(!p.service||p.service===s.id)){S.pick={service:s.id,ref:it.ref,found:true};return;}
  }
  S.pick=null;
}

async function post(route,body,after){
  if(S.busy)return null;S.busy=true;S.flash=null;render();
  try{
    const r=await api().post(route,body);
    S.flash=r?.message?{kind:r.ok===false?'bad':'good',text:r.message}:null;
    api().refresh?.().catch(()=>{});
    if(after)await after(r);
    return r;
  }catch(e){S.flash={kind:'bad',text:e.message||'Chưa gửi được. Thử lại nhé.'};return null;}
  finally{S.busy=false;render();}
}

async function click(op,d){
  if(op==='close'){S.dlg.close();return;}
  if(op==='tab'){S.tab=d.tab;S.flash=null;await load();return;}
  if(op==='pick'){S.pick={service:d.service,ref:d.ref,found:true};S.style='giu';render();return;}
  if(op==='unpick'){S.pick=null;render();return;}
  if(op==='ticket'){
    const r=await post('/api/restore/ticket',{service:d.service,ref:d.ref,style:S.style});
    if(r){S.pick=null;await load();await market(d.service);}return;}
  if(op==='market'){await market(d.service);return;}
  if(op==='drop'){await post('/api/restore/drop',{ticket:d.ticket},load);return;}
  if(op==='take'||op==='decline'||op==='done'){await post('/api/svc/'+op,{order:d.order},load);return;}
  if(op==='work'){await post('/api/restore/work',{order:d.order,pick:d.pick},load);return;}
  if(op==='retry'){await load();return;}
}

async function market(service){
  S.dlg.close();
  await (await import('./service-market.js')).openServiceMarket(S.env,{career:'restore',service});
}

function render(){
  if(!S.dlg)return;
  const tabs=`<nav class="sd-tabs rs-tabs" role="tablist" aria-label="Phục chế đồ">${TABS.map(([id,e,l])=>`<button type="button" role="tab" class="${S.tab===id?'on':''}" aria-selected="${S.tab===id}" aria-label="${esc(l)}" data-rs="tab" data-tab="${id}"${S.busy?' disabled':''}>${e} <span class="rs-tl">${esc(l)}</span></button>`).join('')}</nav>`;
  const flash=S.flash?`<p class="rs-flash ${S.flash.kind}" role="status">${esc(S.flash.text)}</p>`:'';
  const body=S.loading&&!(S.tab==='bench'?S.bench:S.mine)?'<p class="rs-empty">Đang tải…</p>':S.tab==='bench'?benchView():S.tab==='marks'?marksView():mineView();
  S.dlg.querySelector('.sd-root').innerHTML=`<header class="sheet-head sd-head rs-head"><span class="sd-logo" aria-hidden="true">🧰</span><div class="grow"><h2 id="rs-title">Phục chế đồ</h2><small class="rs-sub">Thợ là người chơi · giá qua 🛎️ Phố dịch vụ</small></div><button type="button" class="btn ghost" data-rs="close">Đóng</button></header>${tabs}<div class="sheet-body rs-body">${flash}${body}</div>`;
}

function offLine(v){return v?.off?'<p class="rs-flash bad" role="status">Xưởng phục chế đang tạm nghỉ, quay lại sau nhé.</p>':'';}

function mineView(){
  const v=S.mine;if(!v)return `<p class="rs-empty">Chưa tải được.</p>${btn('Thử lại','retry')}`;
  if(S.pick?.found)return pickView(v);
  const tickets=v.tickets.length?`<h3 class="rs-h">📋 Phiếu đang gửi</h3><ul class="rs-list">${v.tickets.map(t=>`<li class="rs-item"><span class="grow"><b>${esc(t.label)}</b><small>${esc(STATUS[t.status]||t.status)} · ${esc(v.styles[t.style]||'')}</small></span>${t.status==='open'?btn('🛎️ Chọn thợ','market',{service:t.service},'primary small')+btn('Rút','drop',{ticket:t.id},'ghost small'):''}</li>`).join('')}</ul>`:'';
  const groups=v.services.map(s=>`<section class="rs-svc"><h3 class="rs-h"><span aria-hidden="true">${s.icon}</span> ${esc(s.name)} <small>· từ ${fmt(s.base*3)} xu</small></h3><p class="rs-desc">${esc(s.desc)}</p>${s.items.length?`<ul class="rs-list">${s.items.map(x=>`<li class="rs-item"><span class="grow"><b>${esc(x.label)}</b><small>${esc(x.detail)}</small></span>${x.ticket?'<span class="tag">Đã gửi</span>':btn('Mang tới thợ','pick',{service:s.id,ref:x.ref},'small')}</li>`).join('')}</ul>`:'<p class="rs-none">Không có món nào cần làm.</p>'}</section>`).join('');
  return `${offLine(v)}${tickets}${groups}<p class="rs-foot">Giá mặc định gấp 3 giá thợ thường; thợ nhận 95%, 5% là phí phố. Hủy hay thợ từ chối: hoàn đủ tiền.</p>`;
}

function pickView(v){
  const s=v.services.find(x=>x.id===S.pick.service),it=s?.items.find(x=>x.ref===S.pick.ref);
  if(!s||!it){S.pick=null;return mineView();}
  const styles=Object.entries(v.styles).map(([k,l])=>`<label class="rs-tick"><input type="radio" name="rs-style" value="${esc(k)}"${S.style===k?' checked':''}>${esc(l)}</label>`).join('');
  return `<article class="rs-card"><h3>${s.icon} ${esc(s.name)}</h3><p><b>${esc(it.label)}</b> · ${esc(it.detail)}</p><fieldset class="rs-styles"><legend>Dặn thợ</legend>${styles}</fieldset><p class="rs-desc">Ghi phiếu xong, chọn thợ ở 🛎️ Phố dịch vụ. Thợ làm xong là món đồ được phục hồi, có dấu “đã phục chế bởi …”.</p><div class="rs-actions">${btn('Ghi phiếu & chọn thợ','ticket',{service:s.id,ref:it.ref},'primary')}${btn('Quay lại','unpick')}</div></article>`;
}

function benchView(){
  const v=S.bench;if(!v)return `<p class="rs-empty">Chưa tải được.</p>${btn('Thử lại','retry')}`;
  const rows=v.orders.map(o=>{
    const t=o.ticket;
    const head=`<header class="rs-oh"><b>${o.icon} ${esc(o.name)}</b><small>${esc(o.buyer||'Khách')} · ${fmt(o.price)} xu · ${esc(STATUS[o.status]||o.status)}</small></header>`;
    const item=t?`<p class="rs-desc">Món: <b>${esc(t.label)}</b> · Khách dặn: <b>${esc(t.style_name)}</b></p>`:'<p class="rs-desc">Khách chưa gửi món nào cho dịch vụ này.</p>';
    const note=o.note?`<p class="rs-note">“${esc(o.note)}”</p>`:'';
    let act='';
    if(o.status==='held')act=btn('Nhận đơn','take',{order:o.order},'primary')+btn('Từ chối','decline',{order:o.order});
    else if(o.ready)act=btn('🎁 Giao đồ','done',{order:o.order},'primary');
    else if(o.step)act=`<p class="rs-step">Bước ${o.at+1}/${o.steps}: <b>${esc(o.step.title)}</b>${o.wrong?` <small>· sai ${o.wrong} lần</small>`:''}</p><div class="rs-opts" data-coach="restore-bench">${o.step.options.map(p=>btn(esc(p.label),'work',{order:o.order,pick:p.id},'small')).join('')}</div>`;
    else act=btn('Từ chối · hoàn tiền khách','decline',{order:o.order});
    return `<li class="rs-order">${head}${item}${note}<div class="rs-actions">${act}</div></li>`;
  }).join('');
  return `${offLine(v)}<p class="rs-desc">Bật dịch vụ phục chế ở 🛎️ Phố dịch vụ → Dịch vụ của tôi. Đơn mới hiện ở đây: nhận đơn, làm ba bước, giao đồ là nhận tiền.</p>${rows?`<ul class="rs-list">${rows}</ul>`:'<p class="rs-none">Chưa có đơn nào.</p>'}<p class="rs-foot">Đã phục chế cho người chơi: <b>${fmt(v.done)}</b> món.</p>`;
}

function marksView(){
  const v=S.mine;if(!v)return `<p class="rs-empty">Chưa tải được.</p>${btn('Thử lại','retry')}`;
  return v.marks.length?`<ul class="rs-list">${v.marks.map(m=>`<li class="rs-item"><span class="grow"><b>${esc(m.name)}</b><small>✨ Đã phục chế bởi ${esc(m.by)} · ${stars(m.g)} · ngày ${fmt(m.d)}</small></span></li>`).join('')}</ul>`:'<p class="rs-none">Chưa có món nào được phục chế.</p>';
}
