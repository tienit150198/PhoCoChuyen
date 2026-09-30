/** The air crew's own shell (pilot, flight_attendant): Hãng bay Cánh Cò instead of a shop.
 * Pieces the two career modules hand to the app through their optional hooks (v4/careers.js context):
 *   hudCard   the boarding pass on the main screen (app.js taskCards),
 *   board     "Bảng giờ bay", today's flights as a departures board (app.js queueView, the dock's first button),
 *   page      'prepare' → the crew room, 'prices' → "Sổ bay", the flight log (the nav's "Sổ bay" replaces Sổ tiệm),
 *   daySummary the top of the end-of-day sheet in airline terms (app.js summaryView; the shared notes stay),
 *   nav/spots the menu without shop-only entries, and the scene spots that would open Sổ tiệm.
 * Each module passes a small cfg: its crew, how a task reads as a row, the stats it keeps. Styles: air_kit.css. */
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const upper=s=>String(s||'').toLocaleUpperCase('vi-VN');
const ended=t=>['completed','cancelled','referred'].includes(t.status);
const dayNo=x=>x.state?.journey?.story?x.state.journey.life_day:x.room.day;
const npcId=(cfg,i)=>`${cfg.id}_npc_${String(i+1).padStart(2,'0')}`;

/** Today's flights of this career, in slot order. */
function today(x){
  const c=x.room;
  return (c.tasks||[]).filter(t=>t.day===c.day&&t.leg).sort((a,b)=>Number(a.id.slice(-2))-Number(b.id.slice(-2)));
}
/** The sheet head every crew page uses (same classes as the shared sheets). */
function head(x,eyebrow,title,sub=''){
  return `<header class="sheet-head air-head"><div class="grow"><span class="eyebrow">${esc(eyebrow)}</span><h2>${esc(title)}</h2>${sub?`<p>${esc(sub)}</p>`:''}</div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${x.icon('x',21)}</button></header>`;
}
/** A departures board: time · flight · to · gate · status. Rows still to fly open that job. */
export function boardRows(x,cfg,tasks,{tap=true}={}){
  if(!tasks.length)return `<div class="air-board air-board-empty"><p>Lịch bay hôm nay có khi báo danh.</p></div>`;
  const rows=tasks.map(t=>{const r=cfg.row(t),go=tap&&!ended(t);
    const cells=`<span class="ab-time">${esc(t.leg.dep)}</span><span class="ab-code">${esc(t.leg.code)}</span><span class="ab-to">${esc(upper(r.to||t.leg.to))}</span><span class="ab-gate">${esc(t.leg.gate)}</span><span class="ab-status ${esc(r.tone||'')}">${esc(r.status)}</span>`;
    return go?`<button type="button" class="ab-row${t.id===x.room.active_task?' now':''}" data-action="job" data-task="${esc(t.id)}">${cells}</button>`:`<div class="ab-row done">${cells}</div>`;}).join('');
  return `<div class="air-board" role="table" aria-label="Bảng giờ bay"><div class="ab-row ab-head" role="row"><span>GIỜ</span><span>CHUYẾN</span><span>ĐẾN</span><span>CỬA</span><span>TÌNH TRẠNG</span></div>${rows}</div>`;
}
/** "Bảng giờ bay": the whole day on one board, and the one way on (another hop, or the end of the shift). */
export function board(x,cfg){
  const c=x.room,list=today(x),left=list.filter(t=>!ended(t)).length;
  const foot=c.open?`<footer class="sheet-foot"><p>${c.day_completed} ${esc(cfg.done_word)} xong</p><div class="row wrap">${x.cmd(`✈️ ${esc(cfg.more)}`,'more_work',{},left?'ghost':'primary',left>=4)}${x.button('Tan ca','end',{},'ghost')}</div></footer>`
    :`<footer class="sheet-foot"><p></p><div class="row wrap">${x.button('Vào phòng tổ bay','prepare',{},'primary')}</div></footer>`;
  return head(x,`BẢNG GIỜ BAY · NGÀY ${dayNo(x)}`,cfg.airline,'Sân bay Thành phố')+`<div class="sheet-body air-sheet">${boardRows(x,cfg,list)}</div>`+foot;
}
/** The boarding pass on the main screen: the flight in hand and its next step; or the roster before the shift. */
export function hudCard(c,t,x,cfg,{bell='',first='',wrap=false,note=''}={}){
  if(!c.open){
    return `<article class="note-card calm-card air-pass air-off"><div class="air-pass-top"><span class="air-pass-code">${esc(cfg.role)}</span><span class="air-pass-route">${esc(cfg.airline)}</span></div>
      <div class="air-pass-row">${x.button(`🪪 Vào phòng tổ bay · báo danh ${esc(c.day_clock?.open_time||'05:30')}`,'prepare',{},'primary big grow'+first)}${c.shift_summary?`<button type="button" class="icon-btn hud-sum" data-action="summary" aria-label="Xem ngày vừa qua">${x.icon('clipboard',18)}</button>`:''}${bell}</div></article>`;
  }
  if(!t){
    const main=wrap?x.button('Tan ca hôm nay','end',{},'primary big grow gd-pulse'):x.cmd(`✈️ ${esc(cfg.more)}`,'more_work',{},'primary big grow');
    const side=wrap?`<button type="button" class="icon-btn hud-sum" data-command="more_work" data-payload="{}" aria-label="${esc(cfg.more)}">${x.icon('plus',18)}</button>`:`<button type="button" class="icon-btn hud-sum" data-action="end" aria-label="Tan ca hôm nay">${x.icon('exit',18)}</button>`;
    return `<article class="note-card calm-card air-pass air-off"><div class="air-pass-top"><span class="air-pass-code">${esc(cfg.role)}</span><span class="air-pass-route">Hết ${esc(cfg.done_word)} đang chờ</span></div><div class="air-pass-row">${note}${main}${side}${bell}</div></article>`;
  }
  const leg=t.leg||{},who=x.npc(t.npc);
  return `<article class="note-card calm-card task-card air-pass">
    <div class="air-pass-top"><span class="air-pass-code">${esc(leg.code||'')}</span><span class="air-pass-route"><b>${esc(upper(leg.frm))}</b><i aria-hidden="true">✈</i><b>${esc(upper(t.where||leg.to))}</b></span><span class="air-pass-when">${esc(leg.dep||'')} · Cửa ${esc(leg.gate||'')}</span></div>
    <div class="air-pass-row">${note}<button type="button" class="calm-what" data-action="job" data-task="${esc(t.id)}" title="${esc(t.title)}"><span class="npc-mini">${x.portrait(who,34)}</span><b>${esc(cfg.next(t))}</b></button>${bell}${x.button('Làm tiếp '+x.icon('arrow',14),'job',{task:t.id},'primary'+first)}</div></article>`;
}
/** The crew room ('prepare'): the day's weather, the departures board, who flies today, the day's goals, then report for duty. */
export function crewRoom(x,cfg){
  const c=x.room,d=c.data||{},m=d.mod||{},list=today(x),people=x.cc.people||[];
  const crew=cfg.crew.map(i=>{const p=people[i];if(!p)return '';return `<li>${x.portrait(x.npc(npcId(cfg,i)),40)}<div><b>${esc(p.name)}</b><small>${esc(p.role)}</small></div></li>`;}).join('');
  const goals=(c.life?.goals||[]).map(g=>`<li class="${g.claimed?'done':''}"><div class="grow"><b>${esc(g.title)}</b><small>Thưởng ${g.reward} xu</small></div>${g.claimed?'<span class="tag green">✓</span>':g.current>=g.goal?x.cmd('Nhận','life_goal',{goal:g.id},'small primary'):`<b class="air-goal-n">${Math.min(g.current,g.goal)}/${g.goal}</b>`}</li>`).join('');
  const first=c.metrics?.served>0?'':' gd-pulse';
  const cta=c.open?x.button(esc(cfg.back),'workbench',{},'primary jumbo'):x.button(`🪪 Báo danh · vào ca ngày ${dayNo(x)}`,'start',{},'primary jumbo'+first);
  return head(x,`PHÒNG TỔ BAY · NGÀY ${dayNo(x)}`,cfg.airline,cfg.role_line)+`<div class="sheet-body air-sheet">
    <section class="air-wx"><span aria-hidden="true">${esc(m.emoji||'🌤️')}</span><div class="grow"><b>${esc(m.label||'')}</b><small>${esc(m.hint||'')}</small></div><span class="air-hours">${esc(c.day_clock?.open_time||'05:30')}–${esc(c.day_clock?.close_time||'19:30')}</span></section>
    <h4 class="air-h">Lịch bay hôm nay</h4>${boardRows(x,cfg,list,{tap:c.open})}
    <h4 class="air-h">Tổ bay</h4><ul class="air-crew">${crew}</ul>
    ${goals?`<h4 class="air-h">Mục tiêu hôm nay</h4><ul class="air-goals">${goals}</ul>`:''}
  </div><footer class="sheet-foot air-foot">${cta}</footer>`;
}
/** "Sổ bay" ('prices'): the career's own log instead of Sổ tiệm: big numbers, then the latest entries. */
export function flightLog(x,cfg){
  const {tiles,rows}=cfg.log(x);
  return head(x,'SỔ BAY',cfg.airline,cfg.role_line)+`<div class="sheet-body air-sheet"><div class="air-tiles">${tiles.map(([v,l])=>`<div><b>${esc(v)}</b><small>${esc(l)}</small></div>`).join('')}</div>
    <h4 class="air-h">Gần đây</h4>${rows.length?`<ul class="air-log">${rows.map(r=>`<li><span class="ab-time">${esc(r.day)}</span><b>${esc(r.code)}</b><span class="grow">${esc(r.text)}</span><span class="ab-status ${esc(r.tone||'')}">${esc(r.status)}</span></li>`).join('')}</ul>`:'<p class="small muted">Chưa có chuyến nào trong sổ.</p>'}</div>`+
    `<footer class="sheet-foot"><p></p><div class="row wrap">${x.button('Đóng','close',{},'primary')}</div></footer>`;
}
/** The top of the end-of-day sheet: the day's flights on a closed board and a few airline numbers. */
export function daySummary(s,x,cfg){
  const data=s.career||{},done=(x.room.tasks||[]).filter(t=>t.day===s.day&&t.leg&&t.status==='completed'),rv=s.reviews||{};
  const tiles=[...cfg.close(data,s),[rv.count?`★ ${rv.average}`:'—',rv.count?`${rv.count} nhận xét`:'chưa có nhận xét']];
  return {eyebrow:'TAN CA BAY',title:`Ngày ${s.journey?.life_day??s.day} · sổ bay`,
    top:`<div class="air-sum">${s.clock?.finish?`<p class="air-sum-line">🛬 Tan ca lúc <b>${esc(s.clock.finish)}</b>. Về tới hẻm kịp cơm tối.</p>`:''}<div class="air-tiles">${tiles.map(([v,l])=>`<div><b>${esc(v)}</b><small>${esc(l)}</small></div>`).join('')}</div>${boardRows(x,cfg,done,{tap:false})}</div>`};
}
/** The menu without shop-only entries: Sổ tiệm becomes "Sổ bay" (the 'prices' page), a few words change. */
export function nav(items,cfg){
  const words={prepare:['briefcase','Phòng tổ bay'],feedback:['star','Nhận xét'],people:['people','Tổ bay & khách quen']};
  return items.map(it=>it[0]==='operations'?['prices','book','Sổ bay',0]:words[it[0]]?[it[0],words[it[0]][0],words[it[0]][1],it[3]]:it);
}
/** Scene spots that open Sổ tiệm in a shop (rent, security) lead to the crew room here. */
export const SPOTS={'ops:property':'prepare','ops:security':'prepare',officer:'prepare'};
/** The career's own pages, or '' for the shared ones (and the shared lock card while the story keeps it closed). */
export function page(view,x,cfg){
  const J=x.state?.journey;if(J?.story&&!(J.unlocked||[]).includes(cfg.id))return '';
  if(view==='prepare')return crewRoom(x,cfg);
  if(view==='prices')return flightLog(x,cfg);
  return '';
}
