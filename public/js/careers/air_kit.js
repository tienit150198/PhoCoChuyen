/** The air crew's own shell (pilot, flight_attendant): Hãng bay Cánh Cò instead of a shop.
 * Pieces the two career modules hand to the app through their optional hooks (v4/careers.js context):
 *   hudCard   the boarding pass on the main screen (app.js taskCards),
 *   board     "Bảng giờ bay", today's flights as a departures board (app.js queueView, the dock's first button),
 *   page      'prepare' → the crew room, 'prices' → "Sổ bay", the flight log (the nav's "Sổ bay" replaces Sổ tiệm),
 *   daySummary the top of the end-of-day sheet in airline terms (app.js summaryView; the shared notes stay),
 *   nav/spots the menu without shop-only entries, and the scene spots that would open Sổ tiệm.
 * Each module passes a small cfg: its crew, how a task reads as a row, the stats it keeps. Styles: air_kit.css.
 * Also the chuyện oái oăm (server: game/careers/air_odd.py): oddCard lets the player answer in their own way
 * (a tone, one or two things to say, whom to bring in, how many units in a bargain), restCard asks for rest days,
 * and the crew record (conduct, fatigue) shows in the crew room and on the boarding pass. */
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const upper=s=>String(s||'').toLocaleUpperCase('vi-VN');
const ended=t=>['completed','cancelled','referred'].includes(t.status);
const dayNo=x=>x.state?.journey?.story?x.state.journey.life_day:x.room.day;
const npcId=(cfg,i)=>`${cfg.id}_npc_${String(i+1).padStart(2,'0')}`;
const odd=x=>(x.room.data||{}).odd||{};
const car=(x,label,action,d={},cls='',extra='')=>`<button type="button" class="${cls}" data-action="car:${action}"${Object.entries(d).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${extra}>${label}</button>`;

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
  const foot=c.open?`<footer class="sheet-foot"><p>${c.day_completed} ${esc(cfg.done_word)} xong</p><div class="row wrap">${c.more_gate?'':x.cmd(`✈️ ${esc(cfg.more)}`,'more_work',{},left?'ghost':'primary')}${x.button('Tan ca','end',{},c.more_gate&&!left?'primary':'ghost')}</div></footer>`
    :`<footer class="sheet-foot"><p></p><div class="row wrap">${x.button('Vào phòng tổ bay','prepare',{},'primary')}</div></footer>`;
  return head(x,`BẢNG GIỜ BAY · NGÀY ${dayNo(x)}`,cfg.airline,'Sân bay Thành phố')+`<div class="sheet-body air-sheet">${boardRows(x,cfg,list)}</div>`+foot;
}
/** The boarding pass on the main screen: the flight in hand and its next step; or the roster before the shift. */
export function hudCard(c,t,x,cfg,{bell='',first='',wrap=false,note=''}={}){
  const role=odd(x).conduct?.demoted?cfg.role_down:cfg.role;
  if(!c.open){
    return `<article class="note-card calm-card air-pass air-off"><div class="air-pass-top"><span class="air-pass-code">${esc(role)}</span><span class="air-pass-route">${esc(cfg.airline)}</span></div>
      <div class="air-pass-row">${x.button(`🪪 Vào phòng tổ bay · báo danh ${esc(c.day_clock?.open_time||'05:30')}`,'prepare',{},'primary big grow'+first)}${c.shift_summary?`<button type="button" class="icon-btn hud-sum" data-action="summary" aria-label="Xem ngày vừa qua">${x.icon('clipboard',18)}</button>`:''}${bell}</div></article>`;
  }
  if(!t){
    const main=wrap||c.more_gate?x.button('Tan ca hôm nay','end',{},'primary big grow gd-pulse'):x.cmd(`✈️ ${esc(cfg.more)}`,'more_work',{},'primary big grow');
    const side=c.more_gate?'':wrap?`<button type="button" class="icon-btn hud-sum" data-command="more_work" data-payload="{}" aria-label="${esc(cfg.more)}">${x.icon('plus',18)}</button>`:`<button type="button" class="icon-btn hud-sum" data-action="end" aria-label="Tan ca hôm nay">${x.icon('exit',18)}</button>`;
    return `<article class="note-card calm-card air-pass air-off"><div class="air-pass-top"><span class="air-pass-code">${esc(role)}</span><span class="air-pass-route">Hết ${esc(cfg.done_word)} đang chờ</span></div><div class="air-pass-row">${note}${main}${side}${bell}</div></article>`;
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
    <h4 class="air-h">Hồ sơ của bạn</h4>${record(x)}${restCard(x,cfg)}
    ${goals?`<h4 class="air-h">Mục tiêu hôm nay</h4><ul class="air-goals">${goals}</ul>`:''}
  </div><footer class="sheet-foot air-foot">${cta}</footer>`;
}
/** "Sổ bay" ('prices'): the career's own log instead of Sổ tiệm: big numbers, then the latest entries. */
export function flightLog(x,cfg){
  const {tiles,rows}=cfg.log(x);
  return head(x,'SỔ BAY',cfg.airline,cfg.role_line)+`<div class="sheet-body air-sheet"><div class="air-tiles">${tiles.map(([v,l])=>`<div><b>${esc(v)}</b><small>${esc(l)}</small></div>`).join('')}</div>
    <h4 class="air-h">Hồ sơ</h4>${record(x)}${oddLog(x)}
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

/* ------------------------------------------------------------ chuyện oái oăm */
const HOW={back:'Xong chuyện',report:'Đã báo',give:'Chiều theo',stuck:'Bỏ ngỏ',deal:'Đã chốt',lawful:'Đúng luật',penalty:'Bị phạt',lapse:'Bỏ ngỏ'};
const KIND={charm:'Lời mời khó từ chối',harass:'Quấy rối',demand:'Yêu cầu oái oăm',corner:'Làm tắt',bargain:'Mặc cả với hãng'};
/** The crew record: conduct level and fatigue, as two chips. */
export function record(x){
  const o=odd(x),cd=o.conduct||{},lv=cd.level||'ok';
  const f=o.fatigue||0,bar=[0,1,2,3,4,5].map(i=>`<i class="${i<f?'on':''}"></i>`).join('');
  return `<div class="air-record"><span class="air-chip lv-${esc(lv)}">${lv==='ok'?'✅':lv==='note'?'📝':lv==='warn'?'⚠️':'⚖️'} ${esc(cd.label||'Hồ sơ sạch')}</span>
    <span class="air-chip air-tired ${o.tired?'bad':''}" aria-label="Độ mệt ${f}">😮‍💨 Mệt <span class="air-bar" aria-hidden="true">${bar}</span></span></div>`;
}
/** The encounters of the last days, one line each. */
function oddLog(x){
  const rows=(odd(x).log||[]).slice().reverse();
  if(!rows.length)return '';
  return `<ul class="air-log">${rows.map(r=>`<li><span class="ab-time">N${r.day}</span><span aria-hidden="true">${esc(r.emoji)}</span><span class="grow">${esc(r.title)}</span><span class="ab-status ${r.good===true?'done':r.good===false?'late':''}">${esc(HOW[r.how]||'')}</span></li>`).join('')}</ul>`;
}
/** The player's answer, kept in x.ui while they compose it (reset when a new encounter or round comes). */
function draft(x,ev){
  const key=`${ev.id}:${ev.round}`;
  if(x.ui.odd?.key!==key)x.ui.odd={key,tone:'',say:[],to:'self',n:ev.bargain?0:null};
  return x.ui.odd;
}
/** Someone around the job wants something: answer in your own tone and words, and choose whom to bring in. */
export function oddCard(x,cfg){
  const o=odd(x),ev=o.ev;
  if(!ev){
    const last=o.last,key=last?`odd-${last.script}-${last.day}-${(o.log||[]).length}`:'';
    if(last&&last.day===x.room.day&&x.ui.seen!==key)
      return `<div class="air-odd-last ${last.good===true?'good':last.good===false?'bad':''}" role="status"><span aria-hidden="true">${esc(last.emoji)}</span><p><b>${esc(last.title)}</b> · ${esc(last.outcome)}</p>${car(x,'✕','seen',{key},'btn ghost small air-x',' aria-label="Đã đọc"')}</div>`;
    return '';
  }
  const u=draft(x,ev),who=ev.npc?x.portrait(x.npc(ev.npc),40):`<span class="air-odd-av" aria-hidden="true">${esc(ev.emoji)}</span>`;
  const seg=(list,cur,act)=>list.map(i=>car(x,esc(i.label),act,{v:i.id},`air-seg${cur===i.id?' on':''}`,` aria-pressed="${cur===i.id}"`)).join('');
  const words=ev.words.map(w=>car(x,esc(w.label),'oddSay',{v:w.id},`air-word${u.say.includes(w.id)?' on':''}${w.id==='yes'?' give':''}`,` aria-pressed="${u.say.includes(w.id)}"`)).join('');
  const b=ev.bargain;
  const count=b?`<div class="air-odd-row"><small>Nhận</small><div class="air-stepper">${car(x,'−','oddN',{v:-1},'air-seg',' aria-label="Bớt"')}<b>${u.n}/${b.ask} ${esc(b.unit)}</b>${car(x,'+','oddN',{v:1},'air-seg',' aria-label="Thêm"')}<small class="air-limit">hợp lý ≤ ${b.limit}</small></div></div>`:'';
  const ready=u.tone&&u.say.length;
  const payload={tone:u.tone||'soft',say:u.say,to:u.to,...(b?{n:u.n}:{})};
  const thread=ev.said.length?`<p class="air-odd-me">Bạn (${esc(ev.said[ev.said.length-1].tone.toLowerCase())}): ${esc(ev.said[ev.said.length-1].say.join(' '))}</p>`:'';
  return `<section class="air-odd kind-${esc(ev.kind)}" role="group" aria-labelledby="air-odd-title">
    <div class="air-odd-head">${who}<div class="grow"><small>${esc(KIND[ev.kind]||'')} · ${esc(ev.who)}</small><h3 id="air-odd-title">${ev.npc?esc(ev.emoji)+' ':''}${esc(ev.title)}</h3></div>${ev.round>1?`<span class="air-round">${ev.round}/${ev.rounds}</span>`:''}</div>
    ${thread}<p class="air-odd-line">${esc(ev.line)}</p>${ev.cue?`<p class="air-odd-cue">${esc(ev.cue)}</p>`:''}
    <div class="air-odd-row"><small>Giọng</small><div class="air-segs">${seg(ev.tones,u.tone,'oddTone')}</div></div>
    <div class="air-odd-row"><small>Nói</small><div class="air-words">${words}</div></div>${count}
    ${ev.channels.length>1?`<div class="air-odd-row"><small>Báo</small><div class="air-segs">${seg(ev.channels,u.to,'oddTo')}</div></div>`:''}
    <div class="air-odd-go">${x.cmd(ready?'💬 Nói':'Chọn giọng và ý muốn nói',cfg.odd,payload,'primary big air-odd-send',!ready)}</div></section>`;
}
/** Ask the office for rest days: how many, why, and whether the union carries the request. Once a day. */
export function restCard(x,cfg){
  const o=odd(x);
  if(o.rest_today)return '<p class="small muted air-rest-done">📝 Hôm nay đã xin nghỉ rồi.</p>';
  const u=x.ui.rest||(x.ui.rest={n:1,say:[],to:'self'});
  const words=(o.rest_words||[]).map(w=>car(x,esc(w.label),'restSay',{v:w.id},`air-word${u.say.includes(w.id)?' on':''}`,` aria-pressed="${u.say.includes(w.id)}"`)).join('');
  const seg=[['self','Gửi điều phái'],['company','Nhờ công đoàn']].map(([id,l])=>car(x,l,'restTo',{v:id},`air-seg${u.to===id?' on':''}`,` aria-pressed="${u.to===id}"`)).join('');
  const days=[1,2].map(n=>car(x,`${n} ngày`,'restN',{v:n},`air-seg${u.n===n?' on':''}`,` aria-pressed="${u.n===n}"`)).join('');
  return `<details class="air-rest"${o.tired?' open':''}><summary>🛌 Xin nghỉ bù${o.tired?' · đang mệt':''}</summary>
    <div class="air-odd-row"><small>Xin</small><div class="air-segs">${days}</div></div>
    <div class="air-odd-row"><small>Vì</small><div class="air-words">${words}</div></div>
    <div class="air-odd-row"><small>Gửi</small><div class="air-segs">${seg}</div></div>
    ${x.cmd('📝 Gửi đơn',cfg.rest,{n:u.n,say:u.say,to:u.to},'primary air-rest-send',!u.say.length)}</details>`;
}
/** Stood down for the day: nothing to fly, one way on. */
export function groundCard(x){
  const cd=odd(x).conduct||{};
  if(!cd.ground)return '';
  return `<section class="air-ground" role="status"><h3>⚖️ ${cd.demoted?'Bị cách chức, tạm đình chỉ bay hôm nay':'Tạm đình chỉ bay hôm nay'}</h3><p class="small">Mai lên phòng an toàn trình bày. Hôm nay tan ca sớm.</p>${x.button('Tan ca','end',{},'primary')}</section>`;
}
/** The guide step while someone waits for an answer (or the day is grounded). */
export function oddStep(x){
  const o=odd(x);
  if(o.ev)return {ok:null,label:`Trả lời: ${o.ev.title}`,go:{sel:'.air-odd',label:'💬 Trả lời'},pulse:''};
  if(o.conduct?.ground)return {ok:null,label:'Tạm đình chỉ bay: tan ca',go:{sel:'.air-ground',label:'⚖️ Tan ca'},pulse:''};
  return null;
}
/** Taps inside the cards above (the module's actions spread these in). */
export const ACTIONS={
  async oddTone(d,el,x){x.ui.odd.tone=d.v;x.render();},
  async oddTo(d,el,x){x.ui.odd.to=d.v;x.render();},
  async oddSay(d,el,x){const u=x.ui.odd,i=u.say.indexOf(d.v);if(i>=0)u.say.splice(i,1);else{u.say.push(d.v);if(u.say.length>2)u.say.shift();}x.render();},
  async oddN(d,el,x){const b=odd(x).ev?.bargain;if(!b)return;x.ui.odd.n=Math.max(0,Math.min(b.ask,(x.ui.odd.n||0)+Number(d.v)));x.render();},
  async restSay(d,el,x){const u=x.ui.rest,i=u.say.indexOf(d.v);if(i>=0)u.say.splice(i,1);else{u.say.push(d.v);if(u.say.length>2)u.say.shift();}x.render();},
  async restTo(d,el,x){x.ui.rest.to=d.v;x.render();},
  async restN(d,el,x){x.ui.rest.n=Number(d.v);x.render();},
};
