/** Bảng xếp hạng: "Top trải nghiệm" (overall + one board per workplace), "Top danh hiệu", "Top chứng chỉ" and
 * 💰 "Top tài phú" (net worth: "Tiền của bạn" plus Mây savings, vehicles and Quầy riêng, minus the fair's Vay nóng;
 * not Mây Coin, gold or the couple's Quỹ chung, game/wealth.py), each with its weekly titles (🏅 Danh hiệu tuần, game/lb_titles.py: who holds them, refreshed daily).
 * Every number comes from GET /api/leaderboard (game/leaderboard.py), computed from the saves on
 * the server. Names are display names only, always escaped. The privacy switch
 * "Hiện tên tôi trên bảng xếp hạng" posts to /api/leaderboard/visibility; it lives here and in
 * Cài đặt → Dữ liệu (lbPrivacyRow). Actions: rank (open), lbKind, lbBoard, lbMore, lbVisible, lbRetry, lbName. */
import {icon,escapeHTML as esc} from '../icons.js';
import {emojiOf} from './journey.js';
import {myPortrait} from './look.js';
import {live} from './live.js';

const FRESH_MS=10000;
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const stars=v=>v?`${Number(v).toLocaleString('vi-VN',{minimumFractionDigits:1,maximumFractionDigits:1})}★`:'';
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,action,data={},style='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}>${label}</button>`;
const MEDALS=['🥇','🥈','🥉'];
const OWN=['certs','titles','wealth'];   // boards with their own tab (the rest are "Trải nghiệm" boards)

/* ---- stylesheet on first use (not on the first paint of the game) ---- */
let cssReady=null;
function ensureCss(){
  if(cssReady)return cssReady;
  const href=globalThis.__mnlBoot?.asset?.('/css/leaderboard.css')||'/css/leaderboard.css';
  cssReady=new Promise(done=>{
    if(document.querySelector('link[data-lb-css]')){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=href;l.dataset.lbCss='';
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
  return cssReady;
}

/* ---- data: one cached answer per board, refreshed after FRESH_MS ---- */
const store=ui=>ui.lb??={kind:'exp',board:'all',data:{},busy:{}};
function load(env,board,force=false){
  const {api,ui}=env,s=store(ui),hit=s.data[board];
  if(s.busy[board]||(!force&&hit&&!hit.error&&Date.now()-hit.at<FRESH_MS))return;
  s.busy[board]=true;
  api.json(`/api/leaderboard?${OWN.includes(board)?`board=${board}`:`career=${encodeURIComponent(board)}`}&limit=50`)
    .then(d=>{s.data[board]={...d,at:Date.now()};if(d.me)ui.lbMe=d.me;})
    .catch(e=>{s.data[board]={error:e.message||'Chưa tải được bảng xếp hạng.',at:Date.now()};})
    .finally(()=>{s.busy[board]=false;if(ui.view==='rank'||ui.view==='settings')env.renderSheet();});
}

const metaOf=(api,id)=>api.content.catalogue.find(m=>m.id===id)||{id,short:id,place:id};
const placeOf=(api,id)=>{const m=metaOf(api,id);return m.place||m.short||id;};
/** Workplaces from the catalogue the server sent (new careers appear by themselves). */
const careerIds=api=>api.content.catalogue.map(m=>m.id).filter(id=>api.state.careers?.[id]);

function rule(api,board){
  if(board==='wealth')return 'Tài sản ròng như ở “Tiền của bạn”, cộng tiết kiệm Mây, xe và quầy riêng theo giá bán lại, trừ mọi nợ kể cả vay nóng hội chợ. Chưa tính Mây Coin, vàng (giá đổi từng phút) và Quỹ chung. Bằng nhau: ai nhiều tài sản hơn, rồi ai đạt trước.';
  if(board==='titles')return 'Xếp theo số danh hiệu trò chơi đã có, rồi danh hiệu bí mật, rồi ai có sớm hơn.';
  if(board==='certs')return 'Xếp theo số chứng chỉ đã có, rồi tổng điểm thi cao nhất, rồi ai có sớm hơn.';
  if(board==='all')return 'Điểm là XP trưởng thành: XP ở mọi nơi làm, cộng 80 cho mỗi nơi đã phục vụ khách. Bằng điểm thì ai thạo nhiều nghề hơn, rồi làm nhiều ngày hơn đứng trước.';
  return `Điểm là XP ở ${placeOf(api,board)}. Bằng điểm thì ai làm nhiều ngày hơn, rồi được nhiều sao hơn đứng trước.`;
}
/** The small line under a name: the one or two numbers that break ties. */
function statsLine(board,r){
  if(board==='wealth')return 'Tài sản ròng · chưa tính coin, vàng, Quỹ chung';
  if(board==='titles')return [r.secret?`${fmt(r.secret)} bí mật`:'',r.day?`mới nhất Ngày ${fmt(r.day)}`:''].filter(Boolean).join(' · ');
  if(board==='certs')return [`${fmt(r.best)} điểm thi`,r.day?`có từ Ngày ${fmt(r.day)}`:''].filter(Boolean).join(' · ');
  if(board==='all')return [`Trưởng thành cấp ${fmt(r.level)}`,`${fmt(r.mastered)} nghề thạo`,`${fmt(r.days)} ngày`].join(' · ');
  return [`Cấp ${fmt(r.level)}`,`${fmt(r.days)} ngày`,stars(r.stars)].filter(Boolean).join(' · ');
}
function scoreBox(board,r){
  if(board==='wealth')return `<span class="lb-score"><b>${fmt(r.score)}</b><small>xu</small></span>`;
  if(board==='titles')return `<span class="lb-score"><b>${fmt(r.score)}</b><small>danh hiệu</small></span>`;
  return board==='certs'?`<span class="lb-score"><b>${fmt(r.score)}</b><small>chứng chỉ</small></span>`:`<span class="lb-score"><b>${fmt(r.score)}</b><small>XP</small></span>`;
}
function rowHTML(board,r){
  const medal=r.rank<=3?`<span class="lb-medal" aria-hidden="true">${MEDALS[r.rank-1]}</span>`:'';
  return `<li class="lb-row${r.me?' me':''}${r.rank<=3?` top top${r.rank}`:''}"><span class="lb-rank" aria-label="Hạng ${r.rank}">${medal||`<b>${r.rank}</b>`}</span>
    <span class="lb-who"><span class="lb-name-line"><b class="lb-name" data-no-translate>${esc(r.name)}</b>${r.guest?'<span class="tag lb-guest">khách</span>':''}${r.me?'<span class="tag blue">Bạn</span>':''}</span>${r.title?`<span class="lb-held">${esc(r.title.emoji)} ${esc(r.title.name)}</span>`:''}<small>${esc(statsLine(board,r))}</small></span>
    ${scoreBox(board,r)}</li>`;
}

/* ---- 🏅 Danh hiệu tuần (game/lb_titles.py): the holders of this board's titles, refreshed once a day ---- */
const vnTime=t=>new Date(t*1000).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'});
function holdersText(list){
  if(!list.length)return '<i>Chưa ai giữ</i>';
  const shown=list.slice(0,3).map(h=>h.me?'<b>Bạn</b>':`<span data-no-translate>${esc(h.name)}</span>`).join(', ');
  return list.length>3?`${shown} <i>+${list.length-3} người</i>`:shown;
}
function tierRows(tiers){
  return tiers.map(t=>`<li class="${t.holders.some(h=>h.me)?'me':''}"><span class="lb-week-emoji" aria-hidden="true">${esc(t.emoji)}</span><span class="lb-week-who"><b>${esc(t.name)}</b><small>${esc(t.label)} · ${holdersText(t.holders)}</small></span></li>`).join('');
}
function weeklyHTML(w){
  if(!w)return '';
  const left=Math.max(0,Math.ceil((w.ends-Date.now()/1000)/86400));
  const when=w.updated?`Cập nhật hằng ngày · lần cuối ${vnTime(w.updated)}`:'Cập nhật hằng ngày';
  const last=w.last?`<details class="lb-week-last"><summary>Tuần trước</summary><ul class="lb-week-tiers">${tierRows(w.last.tiers)}</ul></details>`:'';
  return `<section class="lb-week" aria-label="Danh hiệu tuần này"><div class="lb-week-head"><b>🏅 Danh hiệu tuần này</b><small>${esc(when)} · chốt sau ${left} ngày</small></div>
    <ul class="lb-week-tiers">${tierRows(w.tiers)}</ul>${last}</section>`;
}

function meCard(env,board,d){
  const {api}=env,me=d.me;if(!me)return '';
  const where=OWN.includes(board)||board==='all'?'':` ở ${placeOf(api,board)}`;
  let main;
  if(me.rank==null){
    main=board==='wealth'?(api.state.journey?.story===false?'Bảng này chỉ tính người chơi theo câu chuyện: chơi tự do không có ví riêng.':'Tài sản ròng của bạn chưa trên 0 xu. Trả bớt nợ, để dành thêm là có tên trên bảng.')
      :board==='titles'?'Bạn chưa có danh hiệu nào. Hoàn thành việc đầu tiên là có ngay.'
      :board==='certs'?'Bạn chưa có chứng chỉ nào. Thi đỗ chứng chỉ đầu tiên để có tên trên bảng này.'
      :board==='all'?'Hoàn thành việc đầu tiên để có tên trên bảng này.':`Bạn chưa làm ở ${placeOf(api,board)}. Làm việc đầu tiên ở đó để có tên trên bảng này.`;
    return `<section class="lb-me empty-me" aria-label="Vị trí của bạn"><span class="lb-me-rank" aria-hidden="true">—</span><div class="lb-me-text"><span class="lb-name-line"><span class="lb-me-av" aria-hidden="true">${myPortrait(api.state,28,'')}</span><b>Bạn</b></span><p>${main}</p></div></section>`;
  }
  const total=Math.max(d.total||0,me.visible?me.rank:0);
  const place=me.visible?`Hạng ${fmt(me.rank)}${total?` / ${fmt(total)}`:''}${where}`:`Nếu hiện tên, bạn đứng hạng ${fmt(me.rank)}${where}.`;
  const hide=me.visible?`<p class="lb-me-note">Tên hiện là <b data-no-translate>${esc(me.name)}</b>.</p>`
    :me.can_show?`<p class="lb-me-note">Tên bạn đang ẩn.</p>${btn(icon('eye',16)+' Hiện tên tôi','lbVisible',{on:'1'},'primary small lb-me-btn')}`
    :`<p class="lb-me-note">Đặt tên cho nhân vật (khác “Mây”) để có tên trên bảng.</p>${btn(icon('user',16)+' Đặt tên nhân vật','lbName',{},'small lb-me-btn')}`;
  return `<section class="lb-me${me.visible?'':' hidden-me'}" aria-label="Vị trí của bạn"><span class="lb-me-rank"><small>Hạng</small><b>${fmt(me.rank)}</b></span>
    <div class="lb-me-text"><span class="lb-name-line"><span class="lb-me-av" aria-hidden="true">${myPortrait(api.state,28,'')}</span><b>Bạn</b>${me.account?'':'<span class="tag lb-guest">khách</span>'}</span><p class="lb-me-place">${place}</p><small>${esc(statsLine(board,me))}</small>${hide}</div>${scoreBox(board,me)}</section>`;
}

function emptyText(api,board){
  if(board==='wealth')return ['Chưa ai lên bảng','Có tài sản ròng trên 0 xu là có tên trên bảng này.'];
  if(board==='titles')return ['Chưa ai có danh hiệu','Làm việc ở phố để nhận danh hiệu đầu tiên nhé.'];
  if(board==='certs')return ['Chưa ai có chứng chỉ','Thi đỗ chứng chỉ đầu tiên để mở hàng bảng này nhé.'];
  if(board==='all')return ['Bảng còn trống','Chưa ai hiện tên trên bảng. Làm việc đầu tiên rồi bật “Hiện tên tôi” để mở hàng nhé.'];
  return ['Bảng còn trống',`Chưa ai hiện tên ở ${placeOf(api,board)}. Bạn thử làm người đầu tiên nhé.`];
}

// Places you have worked come first; the rest wait behind "Nghề khác" so ~20 chips don't bury the board.
function pickerHTML(api,board,more){
  const chip=(id,emoji,label,act='lbBoard')=>`<button type="button" class="lb-chip${board===id?' active':''}" data-action="${act}" data-board="${esc(id)}" aria-pressed="${board===id}"><span aria-hidden="true">${emoji}</span>${esc(label)}</button>`;
  const worked=id=>{const c=api.state.careers?.[id];return !!(c&&((c.xp||0)>0||c.started));};
  const ids=careerIds(api),mine=ids.filter(id=>worked(id)||id===board),rest=ids.filter(id=>!mine.includes(id));
  const one=id=>{const m=metaOf(api,id);return chip(id,emojiOf(m),m.short||m.place||id);};
  const toggle=rest.length?`<button type="button" class="lb-chip lb-more" data-action="lbMore" aria-expanded="${!!more}"><span aria-hidden="true">${more?'−':'＋'}</span>${more?'Thu gọn':`Nghề khác (${rest.length})`}</button>`:'';
  return `<nav class="lb-picker${more?' open':''}" aria-label="Chọn bảng">${chip('all','🌟','Tất cả')}${mine.map(one).join('')}${more?rest.map(one).join(''):''}${toggle}</nav>`;
}

/* ---- 💍 "Khách mời của tuần" (GET /api/wedding/race, game/wedding_live.py): weddings attended (at least a minute of the party) this week ---- */
const wedOn=()=>Boolean(live.flags?.wedding&&live.welcomed);
function loadWed(env,force=false){
  const {api,ui}=env,s=store(ui),hit=s.data.__wed;
  if(s.busy.__wed||(!force&&hit&&!hit.error&&Date.now()-hit.at<FRESH_MS))return;
  s.busy.__wed=true;
  api.json('/api/wedding/race').then(d=>{s.data.__wed={...d,at:Date.now()};}).catch(e=>{s.data.__wed={error:e.message||'Chưa tải được bảng.',at:Date.now()};})
    .finally(()=>{s.busy.__wed=false;if(ui.view==='rank')env.renderSheet();});
}
function wedBody(env){
  const d=store(env.ui).data.__wed;loadWed(env);
  if(!d)return `<div class="lb-loading" role="status">${icon('sparkle',24)}<p class="muted">Đang tải bảng xếp hạng…</p></div>`;
  if(d.error)return `<div class="notice danger">${icon('alert',17)}<div>${esc(d.error)}</div></div>`;
  const left=Math.max(0,Math.ceil((d.ends-Date.now()/1000)/86400));
  const row=r=>`<li class="lb-row${r.me?' me':''}${r.rank<=3?` top top${r.rank}`:''}"><span class="lb-rank" aria-label="Hạng ${r.rank}">${r.rank<=3?`<span class="lb-medal" aria-hidden="true">${MEDALS[r.rank-1]}</span>`:`<b>${r.rank}</b>`}</span>
    <span class="lb-who"><span class="lb-name-line"><b class="lb-name" data-no-translate>${esc(r.name)}</b>${r.me?'<span class="tag blue">Bạn</span>':''}</span></span>
    <span class="lb-score"><b>${fmt(r.n)}</b><small>đám cưới</small></span></li>`;
  const prizes=`<p class="lb-rule">🥇 ${fmt(d.prizes[0].xu)} xu + ${esc(d.prizes[0].title)} · 🥈🥉 ${fmt(d.prizes[1].xu)} xu + ${esc(d.prizes[1].title)}. Bằng nhau thì ai đạt trước đứng trên. Còn ${left} ngày.</p>`;
  const mine=d.mine!=null?`<p class="lb-me-note">Tuần này bạn đã dự ${fmt(d.mine)} đám cưới.</p>`:'';
  const last=d.last?.winners?.length?`<h3 class="space-top">Tuần trước</h3><ol class="lb-list">${d.last.winners.map(w=>`<li class="lb-row${w.me?' me':''}"><span class="lb-rank"><span class="lb-medal" aria-hidden="true">${MEDALS[w.rank-1]}</span></span><span class="lb-who"><span class="lb-name-line"><b class="lb-name" data-no-translate>${esc(w.name)}</b></span><small>${esc(w.title)}</small></span><span class="lb-score"><b>${fmt(w.n)}</b><small>đám cưới</small></span></li>`).join('')}</ol>`:'';
  return prizes+mine+(d.top.length?`<ol class="lb-list">${d.top.map(row).join('')}</ol>`:`<div class="empty lb-empty">${icon('award',30)}<h3>Tuần này chưa ai dự cưới</h3><p class="muted small">Dự một đám cưới để có tên.</p></div>`)+last;
}

/** The board kinds: 4 tabs, 5 with 💍 Khách mời (lb-kinds.four / .five; on a phone 2 × 2 or 3 + 2, whole words). */
function kindsHTML(tab){
  const tabs=[tab('exp','Trải nghiệm','🏆'),tab('titles','Danh hiệu','🎖️'),tab('certs','Chứng chỉ','📜'),tab('wealth','Tài phú','💰')];
  if(wedOn())tabs.push(tab('wed','Khách mời','💍'));
  return `<div class="segmented lb-kinds ${tabs.length>4?'five':'four'}" role="tablist" aria-label="Loại bảng">${tabs.join('')}</div>`;
}

export function leaderboardView(env){
  const {api,ui}=env,s=store(ui);ensureCss();
  if(s.kind==='wed'&&wedOn()){
    const tab=(id,label,ico)=>`<button type="button" role="tab" aria-selected="${id==='wed'}" class="${id==='wed'?'active':''}" data-action="lbKind" data-kind="${id}"><span aria-hidden="true">${ico}</span> ${label}</button>`;
    return `<header class="sheet-head"><div class="grow"><span class="eyebrow">KHU PHỐ</span><h2>Khách mời của tuần</h2></div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',20)}</button></header>
      <div class="sheet-body lb">${kindsHTML(tab)}${wedBody(env)}</div>`;
  }
  const kind=OWN.includes(s.kind)?s.kind:'exp';
  let board=kind==='exp'?s.board:kind;
  if(kind==='exp'&&board!=='all'&&!api.state.careers?.[board])board=s.board='all';
  load(env,board);
  const d=s.data[board];
  const tab=(id,label,ico)=>`<button type="button" role="tab" aria-selected="${kind===id}" class="${kind===id?'active':''}" data-action="lbKind" data-kind="${id}"><span aria-hidden="true">${ico}</span> ${label}</button>`;
  let body;
  if(!d)body=`<div class="lb-loading" role="status">${icon('sparkle',24)}<p class="muted">Đang tải bảng xếp hạng…</p></div>`;
  else if(d.error)body=`<div class="notice danger">${icon('alert',17)}<div>${esc(d.error)}</div></div>${btn(icon('refresh',15)+' Thử lại','lbRetry',{board},'small')}`;
  else{
    const [title,text]=emptyText(api,board);
    body=weeklyHTML(d.weekly)+meCard(env,board,d)+(d.rows.length?`<ol class="lb-list" aria-label="Top ${d.rows.length}">${d.rows.map(r=>rowHTML(board,r)).join('')}</ol>`
      :`<div class="empty lb-empty">${icon('award',30)}<h3>${esc(title)}</h3><p class="muted small">${esc(text)}</p></div>`);
  }
  const head=`<header class="sheet-head"><div class="grow"><span class="eyebrow">KHU PHỐ</span><h2>Bảng xếp hạng</h2><p>Ai dày dạn nhất phố? Mọi con số tính từ những gì đã làm trong game.</p></div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  return head+`<div class="sheet-body lb">
    ${kindsHTML(tab)}
    ${kind==='exp'?pickerHTML(api,board,s.more):''}
    <p class="lb-rule">${esc(rule(api,board))}</p>
    ${body}
    ${privacyNote(env)}</div>`;
}

function privacyNote(env){
  const me=env.ui.lbMe;if(!me)return '';
  return `<p class="lb-privacy">${icon('shield',15)} <span>${me.account?'Tài khoản hiện tên hiển thị theo mặc định.':'Khách chỉ hiện tên khi tự bật.'} Không ai thấy tên đăng nhập hay thông tin khác của bạn.</span>${me.visible?btn('Ẩn tên tôi','lbVisible',{on:'0'},'ghost small'):''}</p>`;
}

/** Cài đặt → Dữ liệu → Quyền riêng tư: the same switch. */
export function lbPrivacyRow(env){
  const {ui}=env,me=ui.lbMe;
  if(!me){load(env,'all');return `<label class="switch-row"><span class="grow"><b>Hiện tên tôi trên bảng xếp hạng</b><small class="muted block">Đang kiểm tra…</small></span><input type="checkbox" role="switch" disabled><i aria-hidden="true"></i></label>`;}
  const note=me.account?'Tài khoản hiện tên hiển thị theo mặc định.':me.can_show?'Khách chỉ hiện tên nhân vật khi bạn bật.':'Đặt tên cho nhân vật (khác “Mây”) để có tên trên bảng.';
  return `<label class="switch-row"><span class="grow"><b>Hiện tên tôi trên bảng xếp hạng</b><small class="muted block">${note}</small></span><input type="checkbox" role="switch" data-action="lbVisible" ${me.visible?'checked':''}><i aria-hidden="true"></i></label>`;
}

async function setVisible(env,on){
  const {api,ui,toast,renderSheet}=env,s=store(ui);
  try{
    const r=await api.post('/api/leaderboard/visibility',{visible:on});
    ui.lbMe={...(ui.lbMe||{}),...r};s.data={};toast(r.message,on&&!r.can_show?false:'good');
  }catch(e){toast(e.message||'Chưa lưu được. Thử lại sau nhé.',true);}
  renderSheet();
}

// Keep the chosen workplace chip in sight in the one-row phone picker (sideways only).
function showChip(board){
  requestAnimationFrame(()=>{
    const c=document.querySelector(`.lb-chip[data-board="${CSS.escape(board)}"]`),p=c?.parentElement;
    if(!c||!p||p.scrollWidth<=p.clientWidth)return;
    const cr=c.getBoundingClientRect(),pr=p.getBoundingClientRect();
    p.scrollLeft+=cr.left-pr.left-(pr.width-cr.width)/2;
  });
}

export async function leaderboardAction(action,data,el,env){
  const {ui,openSheet,renderSheet}=env,s=store(ui);
  switch(action){
    case'rank':{await Promise.race([ensureCss(),new Promise(r=>setTimeout(r,800))]);
      const b=data?.board;if(OWN.includes(b))s.kind=b;else if(b){s.kind='exp';s.board=b;}   // a 🏅 chip opens its own board
      openSheet('rank');showChip(s.board);return true;}
    case'lbKind':s.kind=[...OWN,'wed'].includes(data.kind)?data.kind:'exp';renderSheet(false);showChip(s.board);return true;
    case'lbBoard':s.board=data.board||'all';s.kind='exp';renderSheet();showChip(s.board);return true;
    case'lbMore':s.more=!s.more;renderSheet(false);if(!s.more)showChip(s.board);return true;
    case'lbRetry':load(env,data.board||s.board,true);renderSheet();return true;
    case'lbVisible':{const on=el?.type==='checkbox'?el.checked:data.on==='1';await setVisible(env,on);return true;}
    case'lbName':openSheet('home',{jrView:'profile'});return true;
  }
  return false;
}
