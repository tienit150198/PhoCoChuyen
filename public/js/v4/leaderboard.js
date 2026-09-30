/** Bảng xếp hạng: "Top trải nghiệm" (overall + one board per workplace) and "Top chứng chỉ".
 * Every number comes from GET /api/leaderboard (game/leaderboard.py), computed from the saves on
 * the server. Names are display names only, always escaped. The privacy switch
 * "Hiện tên tôi trên bảng xếp hạng" posts to /api/leaderboard/visibility; it lives here and in
 * Cài đặt → Dữ liệu (lbPrivacyRow). Actions: rank (open), lbKind, lbBoard, lbMore, lbVisible, lbRetry, lbName. */
import {icon,escapeHTML as esc} from '../icons.js';
import {emojiOf} from './journey.js';
import {myPortrait} from './look.js';

const FRESH_MS=10000;
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const stars=v=>v?`${Number(v).toLocaleString('vi-VN',{minimumFractionDigits:1,maximumFractionDigits:1})}★`:'';
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,action,data={},style='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}>${label}</button>`;
const MEDALS=['🥇','🥈','🥉'];

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
  api.json(`/api/leaderboard?${board==='certs'?'board=certs':`career=${encodeURIComponent(board)}`}&limit=50`)
    .then(d=>{s.data[board]={...d,at:Date.now()};if(d.me)ui.lbMe=d.me;})
    .catch(e=>{s.data[board]={error:e.message||'Chưa tải được bảng xếp hạng.',at:Date.now()};})
    .finally(()=>{s.busy[board]=false;if(ui.view==='rank'||ui.view==='settings')env.renderSheet();});
}

const metaOf=(api,id)=>api.content.catalogue.find(m=>m.id===id)||{id,short:id,place:id};
const placeOf=(api,id)=>{const m=metaOf(api,id);return m.place||m.short||id;};
/** Workplaces from the catalogue the server sent (new careers appear by themselves). */
const careerIds=api=>api.content.catalogue.map(m=>m.id).filter(id=>api.state.careers?.[id]);

function rule(api,board){
  if(board==='certs')return 'Xếp theo số chứng chỉ đã có, rồi tổng điểm thi cao nhất, rồi ai có sớm hơn.';
  if(board==='all')return 'Điểm là XP trưởng thành: XP ở mọi nơi làm, cộng 80 cho mỗi nơi đã phục vụ khách. Bằng điểm thì ai thạo nhiều nghề hơn, rồi làm nhiều ngày hơn đứng trước.';
  return `Điểm là XP ở ${placeOf(api,board)}. Bằng điểm thì ai làm nhiều ngày hơn, rồi được nhiều sao hơn đứng trước.`;
}
/** The small line under a name: the one or two numbers that break ties. */
function statsLine(board,r){
  if(board==='certs')return [`${fmt(r.best)} điểm thi`,r.day?`có từ Ngày ${fmt(r.day)}`:''].filter(Boolean).join(' · ');
  if(board==='all')return [`Trưởng thành cấp ${fmt(r.level)}`,`${fmt(r.mastered)} nghề thạo`,`${fmt(r.days)} ngày`].join(' · ');
  return [`Cấp ${fmt(r.level)}`,`${fmt(r.days)} ngày`,stars(r.stars)].filter(Boolean).join(' · ');
}
function scoreBox(board,r){
  return board==='certs'?`<span class="lb-score"><b>${fmt(r.score)}</b><small>chứng chỉ</small></span>`:`<span class="lb-score"><b>${fmt(r.score)}</b><small>XP</small></span>`;
}
function rowHTML(board,r){
  const medal=r.rank<=3?`<span class="lb-medal" aria-hidden="true">${MEDALS[r.rank-1]}</span>`:'';
  return `<li class="lb-row${r.me?' me':''}${r.rank<=3?` top top${r.rank}`:''}"><span class="lb-rank" aria-label="Hạng ${r.rank}">${medal||`<b>${r.rank}</b>`}</span>
    <span class="lb-who"><span class="lb-name-line"><b class="lb-name" data-no-translate>${esc(r.name)}</b>${r.guest?'<span class="tag lb-guest">khách</span>':''}${r.me?'<span class="tag blue">Bạn</span>':''}</span><small>${esc(statsLine(board,r))}</small></span>
    ${scoreBox(board,r)}</li>`;
}

function meCard(env,board,d){
  const {api}=env,me=d.me;if(!me)return '';
  const where=board==='certs'?'':board==='all'?'':` ở ${placeOf(api,board)}`;
  let main;
  if(me.rank==null){
    main=board==='certs'?'Bạn chưa có chứng chỉ nào. Thi đỗ chứng chỉ đầu tiên để có tên trên bảng này.'
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

export function leaderboardView(env){
  const {api,ui}=env,s=store(ui);ensureCss();
  const kind=s.kind==='certs'?'certs':'exp';
  let board=kind==='certs'?'certs':s.board;
  if(board!=='all'&&board!=='certs'&&!api.state.careers?.[board])board=s.board='all';
  load(env,board);
  const d=s.data[board];
  const tab=(id,label,ico)=>`<button type="button" role="tab" aria-selected="${kind===id}" class="${kind===id?'active':''}" data-action="lbKind" data-kind="${id}"><span aria-hidden="true">${ico}</span> ${label}</button>`;
  let body;
  if(!d)body=`<div class="lb-loading" role="status">${icon('sparkle',24)}<p class="muted">Đang tải bảng xếp hạng…</p></div>`;
  else if(d.error)body=`<div class="notice danger">${icon('alert',17)}<div>${esc(d.error)}</div></div>${btn(icon('refresh',15)+' Thử lại','lbRetry',{board},'small')}`;
  else{
    const [title,text]=emptyText(api,board);
    body=meCard(env,board,d)+(d.rows.length?`<ol class="lb-list" aria-label="Top ${d.rows.length}">${d.rows.map(r=>rowHTML(board,r)).join('')}</ol>`
      :`<div class="empty lb-empty">${icon('award',30)}<h3>${esc(title)}</h3><p class="muted small">${esc(text)}</p></div>`);
  }
  const head=`<header class="sheet-head"><div class="grow"><span class="eyebrow">KHU PHỐ</span><h2>Bảng xếp hạng</h2><p>Ai dày dạn nhất phố? Mọi con số tính từ những gì đã làm trong game.</p></div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  return head+`<div class="sheet-body lb">
    <div class="segmented lb-kinds" role="tablist" aria-label="Loại bảng">${tab('exp','Trải nghiệm','🏆')}${tab('certs','Chứng chỉ','📜')}</div>
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
    case'rank':await Promise.race([ensureCss(),new Promise(r=>setTimeout(r,800))]);openSheet('rank');showChip(s.board);return true;
    case'lbKind':s.kind=data.kind==='certs'?'certs':'exp';renderSheet(false);showChip(s.board);return true;
    case'lbBoard':s.board=data.board||'all';s.kind='exp';renderSheet();showChip(s.board);return true;
    case'lbMore':s.more=!s.more;renderSheet(false);if(!s.more)showChip(s.board);return true;
    case'lbRetry':load(env,data.board||s.board,true);renderSheet();return true;
    case'lbVisible':{const on=el?.type==='checkbox'?el.checked:data.on==='1';await setVisible(env,on);return true;}
    case'lbName':openSheet('home',{jrView:'profile'});return true;
  }
  return false;
}
