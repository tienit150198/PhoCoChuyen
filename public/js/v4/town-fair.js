/** 🎪 Hội chợ việc làm: the weekly town fair where every career opens a booth (game/town_fair.py holds every rule and
 * number; prices, escrow, 95 % / 5 % and refunds are Phố dịch vụ's, v4/service-market.js).
 * Four tabs: 🎪 Dạo hội chợ (the booths by group, shows first: the fair price beside the usual one, "Đặt" opens Phố dịch
 * vụ on that provider and service, 👀 watch a show for the career's 🎟️ stamp), 🧑‍🔧 Gian của tôi (open a booth for one of my
 * careers with a discount, the shows, the "oái oăm" moments and their choices, the mood), 🎟️ Sổ tem (my stamps and the
 * cosmetics they unlock) and 🏆 Bảng (most served, best booth score, the archive of past fairs).
 * GET /api/townfair/view|board · POST /api/townfair/open|pct|close|show|moment|watch|claim. Phone first (390×844), landscape
 * phones keep the head slim (css/town-fair.css). */
import {escapeHTML as esc,icon} from '../icons.js';
import {stylesheet} from '../lazy.js';
import {avInner} from './face.js';
import {setFair,serverNow,leftText} from './town-fair-data.js';
import {needsFor,needKey,goNeed} from './svc-needs.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const TABS=[['walk','🎪','Dạo hội chợ'],['booth','🧑‍🔧','Gian của tôi'],['stamps','🎟️','Sổ tem'],['board','🏆','Bảng']];
const WEEKDAY=['Chủ nhật','thứ Hai','thứ Ba','thứ Tư','thứ Năm','thứ Sáu','thứ Bảy'];
const S={picked:false,dlg:null,env:null,tab:'walk',v:null,board:null,boardEvent:'',busy:false,loading:false,flash:null,group:'',pct:20,career:'',timer:0,tick:0,seq:0,emoji:null,more:[],needs:{}};
/** Careers the catalogue sends without an emoji (journey.js falls back to ✨): the one their guide uses, so the booth
 * reads "🧰 Phục chế" like the career itself (tutorial/guide-content.js). */
const CAREER_EMOJI={restore:'🧰',research:'🔬',radio:'📻',moto:'🏍️',vet:'🩺',kol:'📱',singer:'🎤',actor:'🎬',hotel:'🛎️',banquet:'👨‍🍳',reception:'🔑',teller:'🏦',oil:'🛢️',railway:'🚦',nurse:'🏥',
  lighthouse:'🗼',rescue:'📞',lifeguard:'🛟',library:'📚',police:'👮',zpop:'💿',art_studio:'🎨',lawyer:'⚖️',laundry:'🧺',post_office:'✉️',customs:'🛃',
  pilot:'🧑‍✈️',flight_attendant:'💁'};

const ensureCss=()=>Promise.all([stylesheet('/css/spend.css'),stylesheet('/css/town-fair.css')]);
const api=()=>S.env.api;
const wallet=()=>Math.max(0,Number(api().state?.journey?.wallet)||0);
const face=w=>`<span class="tf-av" aria-hidden="true">${avInner({fc:w?.fc,av:w?.avatar||'🙂'})}</span>`;
const btn=(label,op,data={},cls='ghost',extra='')=>`<button type="button" class="btn ${cls}" data-tf="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${S.busy?' disabled':''}${extra}>${label}</button>`;
const moodFace=m=>m>=85?'😍':m>=70?'😊':m>=50?'🙂':m>=30?'😕':'😠';
const emo=c=>{try{const m=api().content?.catalogue?.find(x=>x.id===c),e=S.emoji&&m?S.emoji(m):'🎪';return e==='✨'&&CAREER_EMOJI[c]||e;}catch{return '🎪';}};
const when=t=>{const d=new Date(t*1000+7*3600e3);return `${WEEKDAY[d.getUTCDay()]} ${String(d.getUTCHours()).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')}`;};
const hhmm=t=>{const d=new Date(t*1000+7*3600e3);return `${String(d.getUTCHours()).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')}`;};

export async function openTownFair(env,data={}){
  S.env=env;
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet?.();
  await ensureCss();
  if(!S.emoji)S.emoji=await import('./journey.js').then(m=>m.emojiOf).catch(()=>null);
  if(!S.dlg){
    const d=document.createElement('dialog');
    d.className='sheet v4-sheet medium sd-sheet tf-sheet';d.setAttribute('aria-labelledby','tf-title');
    d.innerHTML='<div class="sd-root"></div>';document.body.append(d);S.dlg=d;
    d.addEventListener('click',e=>{if(e.target===d){d.close();return;}const el=e.target.closest('[data-tf]');if(!el||el.disabled)return;e.preventDefault();click(el.dataset.tf,el.dataset);});
    d.addEventListener('close',()=>{clearInterval(S.timer);clearInterval(S.tick);S.seq++;document.removeEventListener('visibilitychange',visible);});
  }
  S.flash=null;if(data.tab&&TABS.some(t=>t[0]===data.tab))S.tab=data.tab;
  if(!S.dlg.open){S.dlg.showModal();S.dlg.scrollTop=0;}
  render();
  await load();
  document.addEventListener('visibilitychange',visible);
  clearInterval(S.timer);S.timer=setInterval(()=>{if(!document.hidden&&S.dlg?.open&&!S.busy)S.tab==='board'?loadBoard(true):load(true);},20000);
  clearInterval(S.tick);S.tick=setInterval(()=>{if(!S.dlg?.open)return;let over=false;S.dlg.querySelectorAll('[data-due]').forEach(el=>{const at=Number(el.dataset.due);el.textContent=leftText(at);if(at<=serverNow())over=true;});if(over&&!S.busy&&!S.loading)load(true);},1000);
}
function visible(){if(!document.hidden&&S.dlg?.open)load(true);}

async function load(quiet=false){
  const seq=++S.seq;if(!quiet){S.loading=true;render();}
  try{
    const v=await api().json('/api/townfair/view'+(S.group?`?group=${encodeURIComponent(S.group)}`:''));
    if(seq!==S.seq)return;S.v=v;S.more=[];setFair(v.fair);refreshNeeds(v.booths);
    if(!quiet&&!S.picked){S.picked=true;if(v.mine&&S.tab==='walk'&&(v.mine.moment||!v.booths.length))S.tab='booth';}
    if(S.tab==='board'&&!S.board)loadBoard(true);
  }catch(e){if(seq===S.seq)S.flash={kind:'bad',text:e.message||'Chưa tải được. Thử lại nhé.'};}
  finally{if(seq===S.seq){S.loading=false;render();}}
}
async function loadMore(){
  const v=S.v;if(!v?.next||S.busy)return;S.busy=true;render();
  try{const r=await api().json(`/api/townfair/view?offset=${v.next}`+(S.group?`&group=${encodeURIComponent(S.group)}`:''));S.more=[...S.more,...r.booths];S.v={...v,next:r.next};refreshNeeds(r.booths);}
  catch(e){S.flash={kind:'bad',text:e.message||'Chưa tải được.'};}
  finally{S.busy=false;render();}
}
function refreshNeeds(booths){
  const items=(booths||[]).filter(b=>!b.mine).flatMap(b=>b.items||[]);
  needsFor(api(),items).then(n=>{if(Object.keys(n).length){S.needs={...S.needs,...n};render();}}).catch(()=>{});
}
async function loadBoard(quiet=false){
  if(!quiet){S.loading=true;render();}
  try{S.board=await api().json('/api/townfair/board'+(S.boardEvent?`?event=${encodeURIComponent(S.boardEvent)}`:''));}
  catch(e){S.flash={kind:'bad',text:e.message||'Chưa tải được bảng.'};}
  finally{S.loading=false;render();}
}
async function post(route,body){
  if(S.busy)return null;S.busy=true;S.flash=null;render();
  try{
    const r=await api().post('/api/townfair/'+route,body);
    S.flash=r?.message?{kind:'good',text:r.message}:null;
    if(r?.view){S.v=r.view;S.more=[];setFair(r.view.fair);}
    if(route==='claim')api().refresh?.().then(()=>render()).catch(()=>{});   // the title is in the save now
    return r;
  }catch(e){S.flash={kind:'bad',text:e.message||'Chưa gửi được. Thử lại nhé.'};return null;}
  finally{S.busy=false;render();}
}

async function click(op,d){
  if(op==='close'){S.dlg.close();return;}
  if(op==='tab'){S.tab=d.tab;S.flash=null;render();if(S.tab==='board')await loadBoard(Boolean(S.board));return;}
  if(op==='retry'){await load();return;}
  if(op==='group'){S.group=d.group||'';await load(true);return;}
  if(op==='more'){await loadMore();return;}
  if(op==='order'){S.dlg.close();S.env.act('svcMarket',{pid:d.pid,career:d.career,service:d.service,...(d.offer?{offer_id:d.offer}:{})});return;}
  if(op==='market'){S.dlg.close();S.env.act('svcMarket',{tab:'mine'});return;}
  if(op==='style'){S.dlg.close();S.env.act('spendStyle');return;}
  if(op==='pickc'){S.career=d.career;render();return;}
  if(op==='pickp'){S.pct=Number(d.pct);if(S.v?.mine)await post('pct',{pct:S.pct});else render();return;}
  if(op==='open'){const c=S.career||S.v?.mine?.career;if(!c)return;await post('open',{career:c,pct:S.v?.mine?.pct||S.pct});return;}
  if(op==='shut'){await post('close',{});return;}
  if(op==='show'){await post('show',{show:d.show});return;}
  if(op==='moment'){await post('moment',{key:d.key,pick:d.pick});return;}
  if(op==='watch'){await post('watch',{pid:d.pid});return;}
  if(op==='claim'){await post('claim',{event:d.event,tier:Number(d.tier)});return;}
  if(op==='event'){S.boardEvent=d.event||'';await loadBoard();return;}
  if(op==='need'){const n=S.needs[d.id];if(!n?.go)return;S.dlg.close();await goNeed(S.env,n.go);return;}
}

/* ---------------------------------------------------------------- views */
function render(){
  if(!S.dlg)return;
  const root=S.dlg.querySelector('.sd-root'),top=S.dlg.scrollTop;
  root.innerHTML=page();S.dlg.scrollTop=top;
  S.dlg.setAttribute('aria-busy',String(!!(S.busy||S.loading)));
}
function statusLine(f){
  if(!f)return 'Gian hàng của mọi nghề';
  if(f.state==='open')return `Đang mở · còn <b data-due="${f.ends}">${leftText(f.ends)}</b>`;
  if(f.state==='soon')return `Mở lúc ${esc(when(f.starts))} · còn <b data-due="${f.starts}">${leftText(f.starts)}</b>`;
  if(f.state==='off')return 'Đang tạm nghỉ';
  return f.starts?`Kỳ sau: ${esc(when(f.starts))}`:'Mỗi thứ Bảy, 14:00–17:00';
}
function page(){
  const v=S.v,f=v?.fair,t=TABS.find(x=>x[0]===S.tab)||TABS[0];
  const need=v?.mine?.moment?1:0,ready=(v?.stamps?.tiers||[]).filter(x=>x.ready).length;
  const head=`<div class="tf-stick"><header class="sheet-head sd-head tf-head"><span class="sd-logo tf-logo" aria-hidden="true">🎪</span><div class="grow"><h2 id="tf-title">Hội chợ việc làm</h2><small class="tf-sub">${statusLine(f)}</small></div>
    <span class="sd-wallet" title="Ví">👛 ${fmt(wallet())}</span><button class="icon-btn" type="button" data-tf="close" aria-label="Đóng">${icon('x',21)}</button></header>
    <p class="tf-status">${statusLine(f)}</p>
    <div class="tf-bunting" aria-hidden="true"></div>
    <nav class="sd-tabs tf-tabs" role="tablist" aria-label="Hội chợ việc làm">${TABS.map(([id,e,l])=>`<button type="button" role="tab" aria-selected="${t[0]===id}" aria-label="${esc(l)}" title="${esc(l)}" class="${t[0]===id?'on':''}" data-tf="tab" data-tab="${id}">${e} <small>${esc(l)}</small>${id==='booth'&&need?'<em class="badge">!</em>':id==='stamps'&&ready?`<em class="badge">${ready}</em>`:''}</button>`).join('')}</nav></div>`;
  const flash=`<p class="sd-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  let body;
  if(!v)body=S.loading?'<p class="sd-empty">⏳</p>':`<p class="sd-empty">🎪</p>${btn('Thử lại','retry')}`;
  else body=t[0]==='walk'?walkView(v):t[0]==='booth'?boothView(v):t[0]==='stamps'?stampsView(v):boardView();
  return head+`<div class="sheet-body sd-body tf-body">${body}</div><div class="sd-bar tf-bar">${flash}</div>`;
}
function closedCard(v){
  const f=v.fair||{};
  const txt=f.state==='off'?'Hội chợ đang tạm nghỉ. Hẹn bạn kỳ sau nhé.':f.state==='soon'?`Hội chợ mở lúc ${esc(when(f.starts))}.</p><p class="tf-count">⏳ <b data-due="${f.starts}">${leftText(f.starts)}</b>`:`Hội chợ mở mỗi thứ Bảy, 14:00–17:00.${f.starts?`</p><p class="tf-count">Kỳ sau: ${esc(when(f.starts))}`:''}`;
  return `<section class="sd-card tf-hero"><p class="tf-big" aria-hidden="true">🎪🎡🏮</p><h3>Hội chợ việc làm</h3><p class="tf-note">${txt}</p>
    <ul class="tf-how"><li>🧑‍🔧 Mỗi người dựng một gian cho nghề của mình, giảm 10–30% giá ở 🛎️ Phố dịch vụ.</li><li>🎭 Trình diễn nghề, xử lý mấy chuyện oái oăm để gian được yêu.</li><li>🎟️ Khách đặt dịch vụ hoặc xem trình diễn được tem nghề đó. Đủ tem đổi danh hiệu, khung.</li></ul>
    ${btn('🏆 Xem bảng các kỳ trước','tab',{tab:'board'},'ghost full')}</section>`;
}

/* 🎪 Dạo hội chợ */
function walkView(v){
  if(v.fair?.state!=='open')return closedCard(v);
  const all=[...v.booths,...S.more];
  const showing=all.filter(b=>b.show).length,total=Object.values(v.counts||{}).reduce((a,b)=>a+b,0);
  const chips=[['','🎪','Tất cả',total],['show','🎭','Đang diễn',null],...(v.groups||[]).map(g=>[g.id,g.icon,g.name,v.counts?.[g.id]||0])];
  const intro=`<section class="tf-strip"><span>🎪 ${fmt(total)} gian hàng</span><span>🎟️ ${fmt(v.stamps?.n||0)} tem của bạn</span>${v.mine?`<span>${moodFace(v.mine.mood)} Gian bạn ${v.mine.mood}</span>`:btn('🧑‍🔧 Dựng gian','tab',{tab:'booth'},'primary tf-cta')}</section>`;
  const filter=`<nav class="sd-chips tf-groups" aria-label="Lọc gian hàng">${chips.map(([id,e,l,n])=>`<button type="button" class="sd-chip${S.group===id?' on':''}" data-tf="group" data-group="${id}" aria-pressed="${S.group===id}">${e} <span>${esc(l)}</span>${n!=null?` <small>${n}</small>`:''}</button>`).join('')}</nav>`;
  const list=all.length?`<div class="tf-grid">${all.map(boothCard).join('')}</div>`:`<p class="tf-note tf-center">${S.group?'Chưa có gian nào trong nhóm này.':'Chưa có gian nào. Dựng gian đầu tiên đi!'}</p>`;
  return intro+filter+(showing&&S.group!=='show'?`<p class="tf-live">🎭 ${showing} gian đang trình diễn: xem ngay để lấy tem!</p>`:'')+list+(v.next?`<div class="tf-acts">${btn('Xem thêm gian','more',{},'ghost full')}</div>`:'');
}
function priceHTML(i){
  if(i.mode==='nego')return `<span class="tf-price"><b>🤝 Thương lượng</b></span>`;
  return `<span class="tf-price">${i.fair&&i.usual>i.price?`<s>${fmt(i.usual)}</s> `:''}<b>${fmt(i.price)}</b> <small>xu</small></span>`;
}
function boothCard(b){
  const items=(b.items||[]).filter(i=>i.available!==false);
  const show=b.show?`<div class="tf-show"><p><span class="tf-showi" aria-hidden="true">${esc(b.show.icon)}</span><b>${esc(b.show.name)}</b> <small>còn <span data-due="${b.show.until}">${leftText(b.show.until)}</span></small></p><p class="tf-line">${esc(b.show.line)}</p>
      ${b.mine?'':b.watched?'<p class="tf-ok">✓ Bạn đã xem tiết mục này</p>':btn(`👀 Xem trình diễn${b.stamped?'':' · +🎟️'}`,'watch',{pid:b.pid},'primary full')}</div>`:'';
  const rows=items.length?`<ul class="tf-items">${items.map(i=>{const n=b.mine?null:S.needs[needKey(i.career,i.service)];
      return `<li><span class="tf-ii" aria-hidden="true">${esc(i.icon)}</span><span class="grow"><b>${esc(i.name)}</b>${i.label?`<small>${esc(i.label)}</small>`:''}</span>${priceHTML(i)}${b.mine?'':btn('Đặt','order',{pid:b.pid,career:i.career,service:i.service,offer:i.offer_id||''},'primary tf-order',n?.hard?' disabled':'')}</li>${n?`<li class="tf-need${n.hard?' hard':''}" role="note"><p>${n.hard?'🔒':'💡'} ${esc(n.why)}</p>${n.go?btn(esc(n.go.label),'need',{id:needKey(i.career,i.service)},n.hard?'primary':'ghost'):''}</li>`:''}`;}).join('')}</ul>`
    :`<p class="tf-muted">${b.mine?'Gian của bạn chưa có dịch vụ nào đang bật.':'Gian này đang trưng bày, chưa nhận đơn. Ghé xem trình diễn nhé!'}</p>`;
  return `<article class="tf-booth g-${esc(b.group)}${b.show?' live':''}${b.mine?' mine':''}"><div class="tf-awning" aria-hidden="true"></div>
    <div class="tf-row">${face(b.who)}<div class="grow"><b class="tf-name">${esc(b.who?.name||'')}${b.mine?' <small>(bạn)</small>':''}</b><small class="tf-career"><span>${emo(b.career)} ${esc(b.career_name)}</span>${b.online?' · <span class="tf-on">● online</span>':''}</small></div>
      <span class="tf-off" title="Giảm giá hội chợ">−${b.pct}%</span></div>
    <p class="tf-meta"><span title="Điểm gian hàng">${moodFace(b.mood)} ${b.mood}</span><span>🛎️ ${fmt(b.served)} lượt khách</span>${b.watchers?`<span>👀 ${fmt(b.watchers)}</span>`:''}${b.stamped?'<span class="tf-stamp">🎟️ đã có tem</span>':''}</p>
    ${show}${rows}</article>`;
}

/* 🧑‍🔧 Gian của tôi */
function pctPicker(cur){
  return `<div class="tf-pcts" role="radiogroup" aria-label="Giảm giá hội chợ">${(S.v?.rules?.pcts||[10,15,20,25,30]).map(p=>`<button type="button" role="radio" aria-checked="${p===cur}" class="tf-pct${p===cur?' on':''}" data-tf="pickp" data-pct="${p}"${S.busy?' disabled':''}>−${p}%</button>`).join('')}</div>`;
}
function boothView(v){
  if(v.fair?.state!=='open')return closedCard(v);
  const m=v.mine;
  if(!m){
    const can=v.can_open||[];
    if(!can.length)return `<section class="sd-card tf-hero"><p class="tf-big" aria-hidden="true">🧑‍🔧</p><h3>Bạn chưa có nghề để dựng gian</h3><p class="tf-note">Vào làm một nghề trong hành trình, kỳ sau dựng gian nhé. Hôm nay bạn vẫn đi dạo, xem trình diễn và góp tem được.</p>${btn('🎪 Đi dạo hội chợ','tab',{tab:'walk'},'primary full')}</section>`;
    if(!S.career||!can.some(c=>c.career===S.career))S.career=(can.find(c=>c.career===api().state?.current)||can[0]).career;
    return `<section class="sd-card tf-setup"><h3>🧑‍🔧 Dựng gian hàng</h3><p class="tf-note">Chọn nghề cho gian. Dịch vụ bạn đang bật ở 🛎️ Phố dịch vụ của nghề đó sẽ giảm giá tới hết hội chợ (không thấp hơn giá gốc). Mỗi kỳ một gian.</p>
      <p class="tf-lbl">Nghề</p><div class="tf-careers" role="radiogroup" aria-label="Nghề của gian">${can.map(c=>`<button type="button" role="radio" aria-checked="${S.career===c.career}" class="tf-career-pick${S.career===c.career?' on':''}" data-tf="pickc" data-career="${esc(c.career)}"${S.busy?' disabled':''}><span aria-hidden="true">${emo(c.career)}</span>${esc(c.name)}</button>`).join('')}</div>
      <p class="tf-lbl">Giảm giá hội chợ</p>${pctPicker(S.pct)}
      <div class="tf-acts">${btn('🎪 Dựng gian','open',{},'primary full')}</div></section>`;
  }
  const items=m.items||[];
  const showWait=m.show_next>serverNow()&&!m.show;
  const shows=m.show?`<div class="tf-show"><p><span class="tf-showi" aria-hidden="true">${esc(m.show.icon)}</span><b>${esc(m.show.name)}</b> <small>còn <span data-due="${m.show.until}">${leftText(m.show.until)}</span> · 👀 ${m.show.watching}</small></p><p class="tf-line">${esc(m.show.line)}</p></div>`
    :m.shows>=m.shows_max?`<p class="tf-muted">Bạn đã diễn đủ ${m.shows_max} lần kỳ này.</p>`
    :`${showWait?`<p class="tf-muted">Nghỉ tay, diễn tiếp sau <span data-due="${m.show_next}">${leftText(m.show_next)}</span>.</p>`:''}<div class="tf-menu">${m.menu.map(x=>btn(`<span aria-hidden="true">${esc(x.icon)}</span> ${esc(x.name)}`,'show',{show:x.id},'tf-opt',showWait||!m.open?' disabled':'')).join('')}</div>`;
  const mo=m.moment?`<section class="tf-moment" aria-live="polite"><p class="tf-evt"><span class="tf-evi" aria-hidden="true">${esc(m.moment.icon)}</span><span>${esc(m.moment.text)}</span></p><p class="tf-muted">Trả lời trong <b data-due="${m.moment.due}">${leftText(m.moment.due)}</b>, không thì gian mất điểm.</p>
      <div class="tf-opts">${m.moment.opts.map(o=>btn(esc(o.label),'moment',{key:m.moment.key,pick:o.id},'tf-opt')).join('')}</div></section>`:'';
  const log=m.log?.length?`<details class="tf-log"><summary>Nhật ký gian (${m.log.length})</summary><ul>${m.log.map(e=>`<li><span aria-hidden="true">${esc(e.icon)}</span><span>${esc(e.text)} ${e.d?`<small class="${e.d>0?'up':'down'}">${e.d>0?'+':''}${e.d}</small>`:''}</span></li>`).join('')}</ul></details>`:'';
  return mo+`<section class="sd-card tf-mine${m.open?'':' shut'}"><div class="tf-awning" aria-hidden="true"></div><div class="tf-row"><span class="tf-big1" aria-hidden="true">${emo(m.career)}</span><div class="grow"><h3>Gian ${esc(m.career_name)}</h3><small class="tf-muted">${m.open?'Đang mở':'Đã dọn · giá trở lại như thường'}</small></div><span class="tf-off">−${m.pct}%</span></div>
      <div class="tf-mood" role="img" aria-label="Điểm gian hàng ${m.mood}"><span>${moodFace(m.mood)}</span><i><b style="width:${Math.max(0,Math.min(100,m.mood))}%"></b></i><small>${m.mood}</small></div>
      <p class="tf-meta"><span>🛎️ ${fmt(m.served)} lượt khách</span><span>🎭 ${m.shows}/${m.shows_max}</span><span>👀 ${fmt(m.watchers)}</span><span>😵 ${m.handled} xử lý · ${m.missed} lỡ</span></p>
      <p class="tf-lbl">Giảm giá hội chợ</p>${pctPicker(m.pct)}
      <p class="tf-lbl">Dịch vụ đang bán</p>${items.length?`<ul class="tf-items">${items.map(i=>`<li><span class="tf-ii" aria-hidden="true">${esc(i.icon)}</span><span class="grow"><b>${esc(i.name)}</b></span>${priceHTML(i)}</li>`).join('')}</ul>`:'<p class="tf-muted">Chưa bật dịch vụ nào của nghề này. Bật ở 🧰 Dịch vụ của tôi để khách đặt được.</p>'}
      <div class="tf-acts">${btn('🧰 Giá & bật/tắt dịch vụ','market',{},'ghost')}${m.open?btn('Dọn gian','shut',{},'ghost'):btn('🎪 Mở lại gian','open',{},'primary')}</div></section>
    <section class="sd-card"><h3>🎭 Trình diễn</h3><p class="tf-note">Khách xem trong ${Math.round((S.v.rules?.show_seconds||300)/60)} phút được 🎟️ tem nghề của bạn. Mỗi lần diễn gian thêm điểm.</p>${shows}</section>${log}`;
}

/* 🎟️ Sổ tem */
function stampsView(v){
  const c=v.stamps||{};
  if(!c.event)return closedCard(v);
  const got=new Map((c.stamps||[]).map(s=>[s.career,s]));
  const tiers=(c.tiers||[]).map(t=>{const pct=Math.min(100,Math.round((c.n||0)/t.need*100));
    return `<li class="tf-tier${t.got?' got':t.ready?' ready':''}"><span class="tf-tieri" aria-hidden="true">${esc(t.emoji)}</span><span class="grow"><b>${esc(t.name)}</b><small>${t.kind==='frame'?'Khung ảnh':'Danh hiệu'} · ${t.need} tem</small><i class="tf-prog"><b style="width:${pct}%"></b></i></span>
      ${t.got?'<em class="tf-ok">✓ Đã đổi</em>':t.ready?btn('Đổi quà','claim',{event:c.event,tier:t.tier},'primary'):`<em class="tf-muted">${c.n||0}/${t.need}</em>`}</li>`;}).join('');
  const cards=(c.stamps||[]).length?`<div class="tf-stamps">${c.stamps.map(s=>`<span class="tf-stampcard" title="${esc(s.career_name)}"><span aria-hidden="true">${emo(s.career)}</span><small>${esc(s.career_name)}</small><em>${s.src==='show'?'🎭':'🛎️'}</em></span>`).join('')}</div>`
    :'<p class="tf-note tf-center">Chưa có tem nào. Đặt dịch vụ ở một gian hoặc xem trình diễn để được tem nghề đó.</p>';
  return `<section class="sd-card"><h3>🎟️ Sổ tem kỳ này <small class="tf-muted">${c.n||0} tem</small></h3>${cards}<p class="tf-muted">Mỗi nghề một tem: 🛎️ đơn đã xong ở gian của nghề đó, hoặc 🎭 xem trình diễn. Đơn đặt trong giờ hội chợ, xong trong ${S.v.rules?.settle_hours||48} giờ sau vẫn tính.</p></section>
    <section class="sd-card"><h3>🎁 Đổi quà</h3><ul class="tf-tiers">${tiers}</ul><p class="tf-muted">Quà là danh hiệu / khung giữ mãi, đeo ở 🎨 Phong cách. Mỗi mốc đổi một lần mỗi kỳ.</p>${btn('🎨 Mở Phong cách','style',{},'ghost full')}</section>`;
}

/* 🏆 Bảng */
const medal=i=>i===1?'🥇':i===2?'🥈':i===3?'🥉':`#${i}`;
function boardRows(rows,kind){
  if(!rows?.length)return '<p class="tf-muted">Chưa có gian nào lên bảng.</p>';
  return `<ol class="tf-rank">${rows.map(r=>`<li><span class="tf-medal">${medal(r.rank)}</span>${face(r.who)}<span class="grow"><b>${esc(r.who?.name||'')}</b><small>${emo(r.career)} ${esc(r.career_name)}</small></span>
    <span class="tf-score">${kind==='served'?`<b>${fmt(r.served)}</b><small>lượt khách</small>`:`<b>${r.score}</b><small>${r.n?`⭐ ${String(r.avg).replace('.',',')}`:'điểm gian'}</small>`}</span></li>`).join('')}</ol>`;
}
function boardView(){
  const b=S.board;
  if(!b)return S.loading?'<p class="sd-empty">⏳</p>':`<p class="sd-empty">🏆</p>${btn('Thử lại','tab',{tab:'board'})}`;
  const ev=b.event;
  const past=(b.past||[]).length>1?`<nav class="sd-chips tf-past" aria-label="Các kỳ hội chợ">${b.past.map(p=>`<button type="button" class="sd-chip${ev&&p.id===ev.id?' on':''}" data-tf="event" data-event="${esc(p.id)}">${p.kind==='special'?'✨':'🎪'} ${esc(dayOf(p.starts))}</button>`).join('')}</nav>`:'';
  if(!ev)return `<section class="sd-card tf-hero"><p class="tf-big" aria-hidden="true">🏆</p><h3>Chưa có kỳ hội chợ nào</h3><p class="tf-note">Bảng xếp hạng hiện ở đây khi hội chợ đầu tiên mở.</p></section>`;
  const note=ev.final?`Đã chốt · ${fmt(b.booths)} gian · ${fmt(b.orders)} đơn · ${fmt(b.stamps)} tem`:`Đang tính · chốt lúc ${esc(when(ev.settles))} (đơn xong muộn vẫn được tính)`;
  return past+`<section class="sd-card"><h3>🎪 Kỳ hội chợ ${esc(dayOf(ev.starts))} <small class="tf-muted">${hhmm(ev.starts)}–${hhmm(ev.ends)}</small></h3><p class="tf-muted">${note}</p></section>
    <section class="sd-card"><h3>🛎️ Phục vụ nhiều nhất</h3>${boardRows(b.served,'served')}</section>
    <section class="sd-card"><h3>🌟 Điểm gian hàng</h3>${boardRows(b.rated,'rated')}<p class="tf-muted">Điểm = không khí của gian (trình diễn, xử lý chuyện oái oăm) cộng trừ theo sao khách chấm. Top ${S.v?.rules?.top||3} mỗi bảng nhận danh hiệu khi chốt.</p></section>`;
}
function dayOf(t){const d=new Date(t*1000+7*3600e3);return `${String(d.getUTCDate()).padStart(2,'0')}/${String(d.getUTCMonth()+1).padStart(2,'0')}`;}
