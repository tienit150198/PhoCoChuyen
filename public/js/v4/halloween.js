/** 🎃 Lễ hội Ma Phố (game/halloween.py holds every rule and number; the plan: docs/HALLOWEEN_2026.md).
 * - openHalloween(env,data): the sheet, four tabs: 🎃 Hôm nay (the day's theme, ✅ điểm danh, the pumpkin riddles, 🎭 the
 *   giant pumpkin of the night), 🚪 Gõ cửa (Cho kẹo hay bị ghẹo: doors of friends and of players of the season, a username,
 *   who knocked on my door and "Gõ lại"), 🎁 Đổi kẹo (cosmetics, a pet piece, a capped bag of xu) and 🏆 Bảng kẹo.
 *   GET /api/halloween · POST /api/halloween/checkin|guess|giant|knock|buy (an exchange answers with the save: api.accept).
 * - halloweenBoot(env): the centred start card, once a Vietnam day on a device while candy is earned (and once more when the
 *   night begins), at a calm moment (v4/break-gate.js, after a gift, Có gì mới and the 20/10 card), never on a new
 *   neighbour's first day, never to a player who already checked in today: "🍬 Nhận kẹo" checks in and opens the sheet.
 * Phone first (390×844); text from the server goes in escaped. */
import {escapeHTML as esc,icon} from '../icons.js';
import {stylesheet} from '../lazy.js';
import {avInner} from './face.js';
import {quiet,turn,want} from './break-gate.js';
import {firstDay} from './onboard.js';
import {setHween,hwNow,hwOpen,hwNight,serverNow,vnDay} from './halloween-data.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const TABS=[['today','🎃','Hôm nay'],['knock','🚪','Gõ cửa'],['shop','🎁','Đổi kẹo'],['board','🏆','Bảng kẹo']];
const S={dlg:null,env:null,tab:'today',v:null,busy:false,loading:false,flash:null,pick:{},user:'',seq:0,tick:0};
const css=()=>Promise.all([stylesheet('/css/spend.css'),stylesheet('/css/halloween.css')]);
const api=()=>S.env.api;
const face=w=>`<span class="hw-av" aria-hidden="true">${avInner({fc:w?.fc,av:w?.avatar||'🙂'})}</span>`;
const btn=(label,op,data={},cls='ghost',extra='')=>`<button type="button" class="btn ${cls}" data-hw="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${S.busy?' disabled':''}${extra}>${label}</button>`;
function left(at){
  const s=Math.max(0,Math.round(at-serverNow())),d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);
  return d?`${d} ngày ${h} giờ`:h?`${h} giờ ${m} phút`:`${m} phút`;
}

/* ---------------------------------------------------------------- the sheet */
export async function openHalloween(env,data={}){
  S.env=env;
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet?.();
  await css();
  if(!S.dlg){
    const d=document.createElement('dialog');
    d.className='sheet v4-sheet medium sd-sheet hw-sheet';d.setAttribute('aria-labelledby','hw-title');
    d.innerHTML='<div class="sd-root"></div>';document.body.append(d);S.dlg=d;
    d.addEventListener('click',e=>{if(e.target===d){d.close();return;}const el=e.target.closest('[data-hw]');if(!el||el.disabled)return;e.preventDefault();click(el.dataset.hw,el.dataset);});
    d.addEventListener('input',e=>{if(e.target.matches('[data-hw-user]'))S.user=e.target.value;});
    d.addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target.matches('[data-hw-user]')){e.preventDefault();click('knockuser',{});}});
    d.addEventListener('close',()=>{clearInterval(S.tick);S.seq++;});
  }
  S.flash=data.flash?{kind:'good',text:String(data.flash)}:null;
  if(data.tab&&TABS.some(t=>t[0]===data.tab))S.tab=data.tab;
  if(!S.dlg.open){S.dlg.showModal();S.dlg.scrollTop=0;}
  render();
  await load();
  clearInterval(S.tick);S.tick=setInterval(()=>{if(S.dlg?.open)S.dlg.querySelectorAll('[data-due]').forEach(el=>{el.textContent=left(Number(el.dataset.due));});},30000);
}

async function load(quiet=false){
  const seq=++S.seq;if(!quiet){S.loading=true;render();}
  try{const v=await api().json('/api/halloween');if(seq!==S.seq)return;S.v=v;sync(v);}
  catch(e){if(seq===S.seq)S.flash={kind:'bad',text:e.message||'Chưa tải được. Thử lại nhé.'};}
  finally{if(seq===S.seq){S.loading=false;render();}}
}
function sync(v){
  if(!v)return;
  setHween(['open','grace'].includes(v.state)?{state:v.state,starts:v.starts,ends:v.ends,until:v.until,night:v.night,now:v.now,day:v.day?.n||0,title:v.day?.title||'',icon:v.day?.icon||'🎃'}:null);
}

async function post(route,body){
  if(S.busy)return null;S.busy=true;S.flash=null;render();
  try{
    const since=api().accepted,r=await api().post('/api/halloween/'+route,body);
    S.flash=r?.message?{kind:r.found===false&&route==='guess'?'warn':'good',text:r.message}:null;
    if(r?.view){S.v=r.view;sync(r.view);}
    if(r?.state&&typeof r.revision==='number')api().accept?.(r,since);   // 🎁 an exchange paid into the save at once
    if(route==='guess')delete S.pick[body.spot];
    if(route==='knock')S.user='';
    return r;
  }catch(e){S.flash={kind:'bad',text:e.message||'Chưa gửi được. Thử lại nhé.'};return null;}
  finally{S.busy=false;render();}
}

async function click(op,d){
  if(op==='close'){S.dlg.close();return;}
  if(op==='tab'){S.tab=d.tab;S.flash=null;render();S.dlg.scrollTop=0;return;}
  if(op==='retry'){await load();return;}
  if(op==='login'){S.dlg.close();S.env.act?.('v4AccountOpen',{mode:'login'});return;}
  if(op==='checkin'){await post('checkin',{});return;}
  if(op==='giant'){await post('giant',{});return;}
  if(op==='pick'){S.pick[Number(d.spot)]=d.place;render();return;}
  if(op==='guess'){const i=Number(d.spot),p=S.pick[i];if(!p)return;await post('guess',{spot:i,place:p});return;}
  if(op==='knock'){await post('knock',{to:d.pid});return;}
  if(op==='knockuser'){const u=(S.user||'').trim();if(!u){S.flash={kind:'bad',text:'Gõ tên đăng nhập của nhà muốn ghé nhé.'};render();return;}await post('knock',{to:u});return;}
  if(op==='buy'){await post('buy',{item:d.item});return;}
  if(op==='style'){S.dlg.close();S.env.act?.('spendStyle');return;}
  if(op==='pets'){S.dlg.close();S.env.act?.('pets');return;}
}

function render(){
  if(!S.dlg)return;
  const root=S.dlg.querySelector('.sd-root'),top=S.dlg.scrollTop,focus=document.activeElement?.matches?.('[data-hw-user]');
  root.innerHTML=page();S.dlg.scrollTop=top;
  if(focus){const i=root.querySelector('[data-hw-user]');if(i){i.focus({preventScroll:true});i.setSelectionRange?.(i.value.length,i.value.length);}}
  S.dlg.setAttribute('aria-busy',String(!!(S.busy||S.loading)));
}

function sub(v){
  if(!v)return 'Halloween 26–31/10';
  if(v.state==='open'){
    const d=v.day;
    if(v.night_on)return `🎭 Đêm hội hóa trang · còn <b data-due="${v.ends}">${left(v.ends)}</b>`;
    return d?`Ngày ${d.n}/6 · ${esc(d.title)}`:'Đang diễn ra';
  }
  if(v.state==='grace')return `Đổi kẹo đến hết 01/11 · còn <b data-due="${v.until}">${left(v.until)}</b>`;
  if(v.state==='off')return 'Đang tạm nghỉ';
  return v.state==='before'?'Mở từ 0:00 ngày 26/10':'Đã khép lại';
}
const ART=`<svg class="hw-art" viewBox="0 0 360 64" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
  <g fill="#f5f3ff" opacity=".75"><circle cx="96" cy="10" r="1.2"/><circle cx="150" cy="22" r="1"/><circle cx="190" cy="8" r="1.3"/><circle cx="244" cy="16" r="1"/><circle cx="286" cy="6" r="1.2"/></g>
  <g fill="#1f1235"><path d="M206 12q6-6 12 0q-3-1-6 3q-3-4-6-3z"/><path d="M232 26q4-4 8 0q-2-1-4 2q-2-3-4-2z"/></g>
  <path d="M0 64q60-14 120-2t120-4 120 2v4H0z" fill="#1f1235" opacity=".55"/></svg>`;

function page(){
  const v=S.v,t=TABS.find(x=>x[0]===S.tab)||TABS[0];
  const candy=v?.me?`<span class="hw-candy" title="Kẹo của bạn">🍬 ${fmt(v.me.candy)}</span>`:'';
  const head=`<div class="hw-stick"><header class="sheet-head sd-head hw-head${v?.night_on?' night':''}">${ART}<span class="sd-logo hw-logo" aria-hidden="true">🎃</span><div class="grow"><h2 id="hw-title">Lễ hội Ma Phố</h2><small class="hw-sub">${sub(v)}</small></div>
    ${candy}<button class="icon-btn hw-x" type="button" data-hw="close" aria-label="Đóng">${icon('x',21)}</button></header>
    <nav class="sd-tabs hw-tabs" role="tablist" aria-label="Lễ hội Ma Phố">${TABS.map(([id,e,l])=>`<button type="button" role="tab" aria-selected="${t[0]===id}" aria-label="${esc(l)}" title="${esc(l)}" class="${t[0]===id?'on':''}" data-hw="tab" data-tab="${id}">${e} <small>${esc(l)}</small>${badge(id)}</button>`).join('')}</nav></div>`;
  const flash=`<p class="sd-flash hw-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  let body;
  if(!v)body=S.loading?'<p class="sd-empty">🎃⏳</p>':`<p class="sd-empty">🎃</p>${btn('Thử lại','retry')}`;
  else if(!['open','grace'].includes(v.state))body=closed(v);
  else if(!v.account)body=guest(v);
  else body=t[0]==='today'?today(v):t[0]==='knock'?knock(v):t[0]==='shop'?shop(v):board(v);
  return `${head}<div class="hw-bar">${flash}</div><div class="sd-body hw-body">${body}</div>`;
}
function badge(id){
  const v=S.v;if(!v?.account||v.state!=='open')return '';
  if(id==='today'){const n=(v.checkin?.done?0:1)+(v.pumpkins||[]).filter(p=>p.status==='open').length+(v.giant?.on&&!v.giant.done?1:0);return n?`<em class="badge">${n}</em>`:'';}
  if(id==='knock'){const n=(v.knock?.visitors||[]).filter(x=>!x.back).length;return n?`<em class="badge">${n}</em>`:'';}
  return '';
}
function closed(v){
  return `<div class="card hw-hero"><p class="hw-big" aria-hidden="true">🎃👻🦇</p><p>${v.state==='before'?'Lễ hội Ma Phố mở từ 0 giờ ngày 26/10. Hẹn bạn nhé!':v.state==='off'?'Lễ hội Ma Phố đang tạm nghỉ một chút.':'Lễ hội Ma Phố 2026 đã khép lại. Cảm ơn bạn đã chơi cùng cả phố!'}</p></div>`;
}
function guest(v){
  return `<div class="card hw-hero"><p class="hw-big" aria-hidden="true">🎃🍬</p><p>Đăng nhập tài khoản để săn bí ngô, gõ cửa xin kẹo và đổi quà Halloween nhé.</p>${btn('Đăng nhập / tạo tài khoản','login',{},'primary full')}</div>${rules(v)}`;
}
function rules(v){
  const r=v.rules||{};
  return `<details class="card hw-rules"><summary>📜 Luật lễ hội</summary><ul>
    <li>✅ Điểm danh mỗi ngày: ${r.checkin} kẹo (ngày khai hội thêm 5).</li>
    <li>🎃 Mỗi ngày ${r.pumpkins} quả bí ngô nấp quanh phố: đọc câu đố, chọn đúng nơi được ${r.pump} kẹo. Mỗi quả chỉ đoán một lần. Ở phố 2.5D, đi tới đúng nơi là nhặt luôn.</li>
    <li>🚪 Gõ cửa nhà người chơi khác (mỗi nhà một lần một ngày, tối đa ${r.knocks} nhà): thường được ${r.treat} kẹo, đôi khi bị ghẹo chỉ được ${r.trick}. Chủ nhà được ${r.host} kẹo cho mỗi khách (tối đa ${r.hosted} khách một ngày). Tài khoản cần đủ ${r.knock_age} ngày tuổi.</li>
    <li>🎭 31/10 từ 19:00 đến nửa đêm: mọi viên kẹo nhân ${r.mult}, bí ngô khổng lồ cho thêm ${r.giant} kẹo.</li>
    <li>🎁 Kẹo đổi quà đến hết 01/11. Túi ${fmt(r.swap_coins)} xu đổi tối đa ${r.swap_max} lần (tài khoản từ ${r.swap_age} ngày tuổi, nhân vật từ ngày sống thứ ${r.swap_life}).</li>
    <li>🏆 Bảng kẹo tính kẹo kiếm được, đổi quà không làm tụt hạng. Top ${r.top} nhận danh hiệu lúc 0:00 ngày 01/11.</li></ul></details>`;
}

function today(v){
  const d=v.day,parts=[];
  if(v.state==='grace')parts.push(`<div class="card hw-day"><p class="hw-day-t">🌙 ${esc(v.grace_line)}</p>${btn('🎁 Đi đổi kẹo','tab',{tab:'shop'},'primary full')}</div>`);
  else{
    parts.push(`<div class="card hw-day${v.night_on?' night':''}"><p class="hw-day-k">${d?`Ngày ${d.n}/6`:''}</p><p class="hw-day-t">${esc(d?.icon||'🎃')} ${esc(d?.title||'Lễ hội Ma Phố')}</p><p class="hw-day-l">${esc(d?.line||'')}</p>${v.night_on?'<p class="hw-night">🎭 Đêm hội hóa trang: mọi viên kẹo ×2 tới nửa đêm!</p>':''}</div>`);
    const c=v.checkin;
    parts.push(`<div class="card hw-row-card"><span class="hw-ic" aria-hidden="true">✅</span><div class="grow"><b>Điểm danh hôm nay</b><small class="hw-muted">${c.done?(v.day?.n>=6?`Đã nhận ${c.n} kẹo.`:`Đã nhận ${c.n} kẹo. Mai ghé tiếp nhé!`):`Nhận ${c.n} kẹo, mỗi ngày một lần.`}</small></div>${c.done?'<i class="hw-ok">✓</i>':btn(`🍬 +${c.n}`,'checkin',{},'primary')}</div>`);
    const g=v.giant;
    if(g.on||d?.n===6)parts.push(`<div class="card hw-row-card hw-giant"><span class="hw-ic" aria-hidden="true">🎃</span><div class="grow"><b>Bí ngô khổng lồ</b><small class="hw-muted">${g.on?(g.done?'Bạn đã gõ rồi, kẹo đã vào túi!':`Gõ một cái, nhận ${g.n} kẹo.`):'Hiện ra ở công viên từ 19:00 tối nay.'}</small></div>${g.on&&!g.done?btn(`🔨 +${g.n}`,'giant',{},'primary'):g.done?'<i class="hw-ok">✓</i>':''}</div>`);
    const ps=v.pumpkins||[],found=ps.filter(p=>p.status==='found').length;
    parts.push(`<h3 class="hw-h">🎃 Săn bí ngô · ${found}/${ps.length}</h3><p class="hw-note">Mỗi quả một lần đoán, đoán sai là nó lăn mất. Ở phố 2.5D, đi tới đúng nơi là nhặt được luôn.</p>`);
    parts.push(`<div class="hw-pumpkins">${ps.map(pumpkin).join('')}</div>`);
  }
  parts.push(rules(v));
  return parts.join('');
}
function pumpkin(p){
  const st=p.status;
  if(st!=='open')return `<div class="card hw-pk ${st}"><p class="hw-riddle">“${esc(p.riddle)}”</p><p class="hw-pk-r">${st==='found'?`🎃 Ở ${esc(p.place)} · +${p.n} kẹo`:`💨 Lăn mất rồi · nó nấp ở ${esc(p.place)}`}</p></div>`;
  const pick=S.pick[p.i];
  return `<div class="card hw-pk"><p class="hw-riddle"><span aria-hidden="true">🎃</span> “${esc(p.riddle)}”</p>
    <div class="hw-choices" role="group" aria-label="Bí ngô nấp ở đâu?">${p.choices.map(c=>`<button type="button" class="sd-chip${pick===c.id?' on':''}" aria-pressed="${pick===c.id}" data-hw="pick" data-spot="${p.i}" data-place="${esc(c.id)}"${S.busy?' disabled':''}>${esc(c.name)}</button>`).join('')}</div>
    ${btn(pick?'🔦 Soi chỗ này':'Chọn một nơi rồi soi','guess',{spot:p.i},'primary full',pick?'':' disabled')}</div>`;
}

function person(w,extra=''){return `<div class="hw-person">${face(w)}<span class="grow"><b>${esc(w?.name||'Hàng xóm')}</b>${extra}</span>`;}
function knock(v){
  const k=v.knock,parts=[];
  if(v.state!=='open')return `<div class="card hw-hero"><p>🌙 Mùa gõ cửa đã khép lại. Kẹo trong túi vẫn đổi quà đến hết 01/11.</p></div>`;
  parts.push(`<div class="hw-strip"><span>🚪 Còn <b>${k.left}</b>/${k.max} lượt gõ hôm nay</span><span>🏠 Khách nhà bạn: <b>${k.hosted}</b>/${k.host_max}</span></div>`);
  if(!k.old)parts.push('<p class="hw-warn">Tài khoản cần đủ 1 ngày tuổi mới đi xin kẹo được. Mai quay lại nhé!</p>');
  parts.push(`<p class="hw-note">“Cho kẹo hay bị ghẹo?” Gõ cửa nhà hàng xóm: thường được ${v.rules.treat} kẹo, đôi khi bị ghẹo chỉ được ${v.rules.trick}. Chủ nhà cũng được ${v.rules.host} kẹo nên cứ gõ thoải mái!</p>`);
  parts.push(`<div class="card hw-user"><label for="hwUser"><b>Gõ cửa theo tên đăng nhập</b></label><div class="hw-user-row"><input id="hwUser" data-hw-user type="text" inputmode="text" autocomplete="off" autocapitalize="none" spellcheck="false" maxlength="40" placeholder="vd. lan_pho" value="${esc(S.user)}">${btn('🚪 Gõ','knockuser',{},'primary',k.left&&k.old?'':' disabled')}</div></div>`);
  const vis=k.visitors||[];
  if(vis.length)parts.push(`<h3 class="hw-h">🔔 Ai đã gõ cửa nhà bạn hôm nay</h3><div class="hw-list">${vis.map(x=>`${person(x.who,'<small class="hw-muted">ghé xin kẹo</small>')}${x.back?'<i class="hw-ok">Đã gõ lại ✓</i>':btn('Gõ lại','knock',{pid:x.who?.pid||''},'ghost',k.left&&k.old&&x.who?.pid?'':' disabled')}</div>`).join('')}</div>`);
  parts.push(`<h3 class="hw-h">🏘️ Nhà đang treo đèn bí ngô</h3>`);
  parts.push((k.doors||[]).length?`<div class="hw-list">${k.doors.map(d=>`${person(d,d.friend?'<small class="hw-tag">bạn bè</small>':'')}${btn('🚪 Gõ cửa','knock',{pid:d.pid},'primary',k.left&&k.old?'':' disabled')}</div>`).join('')}</div>`
    :'<p class="hw-note">Chưa thấy nhà nào mới. Rủ bạn bè vào lễ hội, hoặc gõ theo tên đăng nhập ở trên nhé.</p>');
  const mine=k.mine||[];
  if(mine.length)parts.push(`<h3 class="hw-h">🍬 Nhà bạn đã ghé hôm nay</h3><div class="hw-list">${mine.map(x=>`${person(x.who,`<small class="hw-muted">${x.trick?'👻 bị ghẹo':'🍬 cho kẹo'}</small>`)}<i class="hw-plus">+${x.n}</i></div>`).join('')}</div>`);
  return parts.join('');
}

function shop(v){
  const parts=[`<div class="hw-strip"><span>🍬 Bạn có <b>${fmt(v.me.candy)}</b> kẹo</span><span>Đã kiếm cả mùa: <b>${fmt(v.me.earned)}</b></span></div>`,
    '<p class="hw-note">Đồ đổi bằng kẹo là đồ giữ mãi, không mua được bằng xu. Đeo ở 🎨 Phong cách.</p><div class="hw-shop">'];
  for(const it of v.shop||[]){
    const act=it.owned?`<i class="hw-ok">${it.kind==='xu'?'Đã đổi đủ':'Đã có ✓'}</i>`:it.short?`<small class="hw-short">Thiếu ${fmt(it.short)} kẹo</small>`:'';
    parts.push(`<div class="card hw-item${it.owned?' owned':''}"><span class="hw-item-e" aria-hidden="true">${esc(it.emoji)}</span><div class="grow"><b>${esc(it.name)}</b><small class="hw-muted">${esc(it.line)}${it.kind==='xu'&&!it.owned?` · còn ${it.left} lần`:''}</small></div>
      <div class="hw-item-buy"><span class="hw-cost">🍬 ${fmt(it.cost)}</span>${act||btn('Đổi','buy',{item:it.id},'primary')}</div></div>`);
  }
  parts.push(`</div><div class="hw-acts">${btn('🎨 Mở Phong cách','style')}${btn('🐾 Tủ đồ thú cưng','pets')}</div>`);
  return parts.join('');
}

function board(v){
  const rows=v.board||[],me=v.me||{};
  const medal=r=>r===1?'🥇':r===2?'🥈':r===3?'🥉':r;
  return `<div class="hw-strip"><span>Hạng của bạn: <b>${me.rank?'#'+me.rank:'chưa có'}</b></span><span>Kẹo kiếm được: <b>${fmt(me.earned)}</b></span></div>
    <p class="hw-note">Top 1–3: 👑 Vua Kẹo Halloween 2026 + 🎃 Khung bí ngô vàng. Top 4–10: 🍬 Top 10 săn kẹo 2026. Trao lúc 0:00 ngày 01/11. Đổi quà không làm tụt hạng.</p>
    ${rows.length?`<ol class="hw-board">${rows.map(r=>`<li class="${r.me?'me':''}"><span class="hw-rank">${medal(r.rank)}</span>${face(r.who)}<b class="grow">${esc(r.who?.name||'Người chơi')}</b><span class="hw-cost">🍬 ${fmt(r.earned)}</span></li>`).join('')}</ol>`
      :'<p class="sd-empty">🏆</p><p class="hw-note hw-center">Chưa ai có kẹo. Điểm danh để mở hàng nhé!</p>'}`;
}

/* ---------------------------------------------------------------- the start card */
const KEY='mnl.hween.card';
let E=null,cdlg=null,timer=0,calm=0,openedAt=0,back=null,checked='',booting=false;
const get=k=>{try{return localStorage.getItem(k)||'';}catch{return 'blocked';}};
const set=(k,v)=>{try{localStorage.setItem(k,v);}catch{/* storage blocked */}};
/** The card's key for now: the Vietnam day, and a second one when the night begins. */
export const cardKey=(night=hwNight(),day=vnDay())=>day+(night?':night':'');
/** Whether the card is due: the season open, a story save past its first day with an account, not shown for this key. */
export function due(s,account,{seen=get(KEY),open=hwOpen(),key=cardKey()}={}){
  if(!open||!s||!account||seen==='blocked'||seen===key)return false;
  return Boolean(s.journey?.story)&&!firstDay(s)&&s.journey?.intro!==false;
}
const CARD_ART=`<svg class="hw-card-art" viewBox="0 0 240 96" aria-hidden="true">
  <rect width="240" height="96" rx="14" fill="#2a1747"/><circle cx="196" cy="26" r="16" fill="#fde68a"/><circle cx="203" cy="21" r="15" fill="#2a1747"/>
  <g fill="#f5f3ff" opacity=".9"><circle cx="30" cy="18" r="1.4"/><circle cx="70" cy="10" r="1"/><circle cx="150" cy="16" r="1.2"/><circle cx="226" cy="58" r="1"/></g>
  <g fill="#120a24"><path d="M100 22q7-8 14 0q-4-1-7 4q-3-5-7-4z"/><path d="M128 34q5-6 10 0q-3-1-5 3q-2-4-5-3z"/></g>
  <g transform="translate(62 44)"><ellipse cx="26" cy="26" rx="26" ry="21" fill="#f97316"/><ellipse cx="26" cy="26" rx="11" ry="21" fill="#fb923c"/><path d="M26 6V0" stroke="#4d7c0f" stroke-width="5" stroke-linecap="round"/>
    <path d="M15 22l5-6 4 6zM37 22l-5-6-4 6z" fill="#fde047"/><path d="M14 31q12 9 24 0l-4 5-4-3-4 3-4-3-4 3z" fill="#fde047"/></g>
  <g transform="translate(134 52)"><path d="M14 0c9 0 14 8 14 18v20l-5-4-4 4-5-4-5 4-4-4-5 4V18C0 8 5 0 14 0z" fill="#f5f3ff"/><circle cx="9" cy="16" r="2.4" fill="#2a1747"/><circle cx="19" cy="16" r="2.4" fill="#2a1747"/></g>
  <path d="M0 86q60-10 120 0t120 0v10H0z" fill="#120a24"/></svg>`;
function cardHTML(v){
  const d=v?.day,night=v?.night_on,n=v?.checkin?.n||10;
  const title=night?'🎭 Đêm hội hóa trang!':d?.n===1?'🎃 Lễ hội Ma Phố khai hội!':`${d?.icon||'🎃'} ${d?.title||'Lễ hội Ma Phố'}`;
  const meta=night?'31/10 · từ 19:00 tới nửa đêm':`Halloween · ngày ${d?.n||1}/6 (26–31/10)`;
  const line=night?'Mọi viên kẹo nhân đôi, bí ngô khổng lồ đang chờ ở công viên. Hóa trang rồi ra phố thôi!':(d?.line||'');
  return `<header class="wn-head hw-card-head"><span class="wn-spark" aria-hidden="true">🎃</span><div class="grow"><h2 id="hwCardTitle">${esc(title)}</h2><p class="wn-meta">${esc(meta)}</p></div>`+
    `<button type="button" class="icon-btn wn-x" data-hwc="close" aria-label="Đóng">${icon('x',22)}</button></header>`+
    `<div class="wn-body">${CARD_ART}<p class="hw-card-line">${esc(line)}</p><ul class="hw-card-list"><li>🍬 Điểm danh mỗi ngày</li><li>🎃 Săn bí ngô quanh phố</li><li>🚪 Gõ cửa xin kẹo nhà hàng xóm</li><li>🎁 Đổi danh hiệu, khung, màu tên độc quyền</li></ul></div>`+
    `<footer class="wn-foot hw-card-foot"><button type="button" class="btn primary big full" data-hwc="go">🍬 Nhận ${n} kẹo · vào lễ hội</button><button type="button" class="btn ghost full" data-hwc="close">Để sau</button></footer>`;
}
function buildCard(){
  if(cdlg)return cdlg;
  cdlg=document.createElement('dialog');cdlg.id='hwCard';cdlg.className='wn-dialog hw-card';
  cdlg.setAttribute('aria-modal','true');cdlg.setAttribute('aria-labelledby','hwCardTitle');
  cdlg.innerHTML='<div class="wn-card"></div>';document.body.append(cdlg);
  cdlg.addEventListener('click',e=>{
    const b=e.target.closest('[data-hwc]');if(!b||!cdlg.contains(b))return;
    e.preventDefault();if(performance.now()-openedAt<450)return;   // a tap already on its way
    if(b.dataset.hwc==='close'){closeCard();return;}
    go();
  });
  cdlg.addEventListener('cancel',e=>{e.preventDefault();closeCard();});
  return cdlg;
}
async function go(){
  const env=E;closeCard();
  let flash='';
  try{const r=await env.api.post('/api/halloween/checkin',{});flash=r?.message||'';}catch(e){flash=e?.data?.code==='done'?'':String(e?.message||'');}
  openHalloween(env,{tab:'today',flash}).catch(e=>console.warn('halloween:',e));
}
function closeCard(){
  if(!cdlg?.open)return;cdlg.close();
  if(back?.isConnected&&typeof back.focus==='function')back.focus({preventScroll:true});back=null;
}
async function check(){
  const s=E?.api?.state,key=cardKey();
  if(!due(s,E?.api?.account,{key})){calm=0;want('hween',false);return;}
  if(checked===key){want('hween',false);return;}
  want('hween');
  if(!quiet(cdlg)||!turn('hween')){calm=0;return;}
  if(++calm<2||booting)return;
  calm=0;booting=true;
  try{
    await css();await stylesheet('/css/whatsnew.css');
    const v=await E.api.json('/api/halloween');sync(v);
    if(!v?.account||v.state!=='open'||(v.checkin?.done&&!v.night_on)){checked=key;set(KEY,key);want('hween',false);return;}
    if(!quiet(cdlg))return;
    buildCard();back=document.activeElement;
    cdlg.querySelector('.wn-card').innerHTML=cardHTML(v);
    if(!cdlg.open)cdlg.showModal();
    openedAt=performance.now();cdlg.tabIndex=-1;cdlg.focus({preventScroll:true});
    set(KEY,key);checked=key;want('hween',false);
  }catch(e){console.warn('halloween card:',e);checked=key;want('hween',false);}
  finally{booting=false;}
}
/** Called by app.js after the game is on screen while the season shows (and when it begins during a visit). */
export function halloweenBoot(env){
  try{E=env;if(timer)return;timer=setInterval(()=>{if(!hwNow()){clearInterval(timer);timer=0;want('hween',false);return;}check();},1200);}
  catch(error){console.error('halloween:',error);}   // never in the way of the game
}
