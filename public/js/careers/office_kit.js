/** Shared "office desktop" for the three office careers (corp_accounting,
 * tax_payroll, group_accounting): one status row (clock, the boss's trust, energy,
 * deadline, the five-day calendar as a chip that opens), folder tabs (📥 Hộp thư · 📂 Hồ sơ ·
 * 📋 Quy định · 📒 Sổ sách), an email-like inbox (the dossier on the desk expanded, every other
 * message one line) with the career's plan and colleagues (folded unless something needs you
 * today) and the mentor track, and a sticky bottom bar with the next step and the main
 * action. Phones show one tab at a time; wide sheets put the inbox (or the
 * rules) on the left and the document on the right.
 * Pure string builders plus two client-only helpers (tab switch, bar offset):
 * every game action still goes through the career's own commands. */

import {nextHint,stepCta,pending,goAttrs,firstTime,highlight} from '../v4/guide.js';

const DONE=['completed','cancelled','referred'];
export const openTasks=x=>(x.room.tasks||[]).filter(t=>!DONE.includes(t.status));
export const hhmm=m=>`${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`;
export const span=m=>m>=60?`${Math.floor(m/60)} giờ${m%60?` ${m%60} phút`:''}`:`${m} phút`;
const clamp=v=>Math.max(0,Math.min(100,Number(v)||0));

/** Deadline of a timed dossier against the office clock (null when untimed). */
export function dueOf(t,x){
  if(typeof t?.due!=='number')return null;
  const o=x.room.data?.office||{},clock=Number(o.clock)||480,day=x.room.day;
  const overdue=day>(t.due_day??day)||clock>t.due,left=t.due-clock;
  return {time:hhmm(t.due),overdue,soon:!overdue&&left<=45,left:Math.max(0,left)};
}
/** “2g30”, “45 phút”: the status row's short countdown (dueText says it in full). */
const shortSpan=m=>m>=60?`${Math.floor(m/60)}g${m%60?String(m%60).padStart(2,'0'):''}`:`${m} phút`;
export function dueText(due){return due?`Hạn ${due.time} · ${due.overdue?'đã trễ':'còn '+span(due.left)}`:'';}

/** Status strip: clock, deadline of the open dossier, the boss's trust, the day's luck, overtime. */
export function statusStrip(x,t,{boss,op}){
  const d=x.room.data||{},o=d.office;if(!o)return '';
  const mod=d.today?.mod,due=t&&t.status!=='completed'?dueOf(t,x):null,trust=clamp(o.trust);
  const pay=mod?.id==='crunch'?18:12,ask=`Ở lại tới 20:00? Được trả ${pay} xu, mai vào muộn 30 phút vì mệt.`;
  let alert='';
  if(o.locked)alert=`<p class="ok-alert bad">🔒 20:00 — văn phòng khóa cửa.</p>`;
  else if(o.closed)alert=`<div class="ok-alert warn"><span>🌇 17:30 — hết giờ hành chính.</span>${x.confirmCmd(`🌙 Ở lại tăng ca (+${pay} xu)`,op,{},ask,'small')}</div>`;
  else if(o.can_overtime)alert=`<div class="ok-alert"><span>Sắp hết giờ. Còn việc dở?</span>${x.confirmCmd(`🌙 Đăng ký tăng ca (+${pay} xu)`,op,{},ask,'ghost small')}</div>`;
  const lvl=trust<35?'low':trust>=75?'high':'',en=d.care?.energy;
  const tired=en&&(en.tone==='warn'||en.tone==='bad');
  const energy=en?`<span class="ok-energy ${x.esc(en.tone||'')}" role="img" aria-label="Sức bền ${Number(en.value)||0}/100 · ${x.esc(en.label||'')}">🔋 <b>${Number(en.value)||0}</b>${tired?` · ${x.esc(en.label)}`:''}</span>`:'';
  if(!alert&&en?.low&&!o.locked)alert=`<p class="ok-alert warn">😮‍💨 Sức bền ${Number(en.value)||0}/100 — việc gì cũng chậm hơn một chút, hôm nay không tăng ca được. Về đúng giờ là hồi lại.</p>`;
  // One row: clock · trust · energy · deadline · luck · the five-day calendar as a chip that opens.
  return `<div class="ok-top"><header class="ok-strip" aria-label="Giờ làm việc hôm nay">
    <span class="ok-clock"><b>🕗 ${x.esc(o.time)}</b><small>${o.overtime?'tăng ca tới 20:00':o.lunch?'nghỉ trưa 12:00':'tan sở 17:30'}</small></span>
    <span class="ok-trust" title="${x.esc(boss)}: ${x.esc(o.trust_label||'')}"><small>👩‍💼 <span class="ok-boss">${x.esc(boss)}: </span><b>${x.esc(o.trust_label||'')}</b></small><span class="ok-meter ${lvl}" role="meter" aria-label="${x.esc(boss)} tin bạn" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${trust}"><i style="width:${trust}%"></i></span></span>
    ${energy}
    ${due?`<span class="ok-due ${due.overdue?'bad':due.soon?'warn':''}" title="${x.esc(dueText(due))}" aria-label="${x.esc(dueText(due))}">⏰ ${x.esc(due.time)} · ${due.overdue?'đã trễ':`còn ${x.esc(shortSpan(due.left))}`}</span>`:''}
    ${mod&&mod.id!=='normal'?`<span class="ok-modchip">${x.esc(mod.emoji)} ${x.esc(mod.name)}</span>`:''}
    ${calChip(x)}
  </header>${alert}</div>`;
}

/* ---------------------------------------------------------------- care: calendar, plan, colleagues, track */
const CAL_STATE={done:['✓','Xong'],due:['⏰','Hạn hôm nay'],late:['⚠️','Trễ hạn'],todo:['○','Sắp tới'],info:['•','']};
/** The five-day calendar strip (today first): luck of the day and the career's due items, coloured by state. */
export function calStrip(x){
  const cal=x.room.data?.care?.calendar;if(!cal?.length)return '';
  const cells=cal.map((c,i)=>{
    const items=(c.items||[]).map(it=>{const [mark,said]=CAL_STATE[it.state]||CAL_STATE.info;
      return `<li class="ok-cal-it ${x.esc(it.state||'info')}"><span class="ok-cal-mark" aria-label="${said}">${mark}</span><span class="ok-cal-txt">${x.esc(it.emoji)} ${x.esc(it.text)}</span></li>`;}).join('');
    return `<li class="ok-cal-day${i===0?' today':''}"><span class="ok-cal-head"><b>${x.esc(c.rel)}</b><small>${x.esc(c.date)}</small>${c.mod?`<span class="ok-cal-mod" title="${x.esc(c.mod.name)}" aria-label="${x.esc(c.mod.name)}">${x.esc(c.mod.emoji)}</span>`:''}</span>
      ${items?`<ul class="ok-cal-items">${items}</ul>`:`<span class="ok-cal-free">${c.mod?x.esc(c.mod.name):'Không có hạn'}</span>`}</li>`;
  }).join('');
  return `<ol class="ok-cal" aria-label="Lịch 5 ngày tới">${cells}</ol>`;
}
/** The calendar folded into a chip of the status row: "📅 5 ngày" plus how many items are due or late. */
export function calChip(x){
  const cal=x.room.data?.care?.calendar;if(!cal?.length)return '';
  const items=cal.flatMap(c=>c.items||[]),late=items.filter(i=>i.state==='late').length,due=items.filter(i=>i.state==='due').length;
  const n=late?`<em class="ok-cal-n bad">⚠️ ${late}</em>`:due?`<em class="ok-cal-n warn">⏰ ${due}</em>`:'';
  return `<details class="ok-calfold"${kept(x,'cal',false)?' open':''}><summary data-action="car:fold" data-fold="cal" aria-label="Lịch ${cal.length} ngày tới">📅 ${cal.length} ngày${n}</summary>${calStrip(x)}</details>`;
}

const PLAN_TONE={done:'good',filed:'good',ok:'good',late_done:'warn',late_filed:'warn',boss:'bad',late:'bad',due:'warn',in:'info',fixing:'info',todo:'',wait:'',locked:''};
/** A plan card, folded (open by itself only when a row is due today or late): rows [{emoji, title, note, tag:{label, tone},
 * act (ready HTML), tone}] (strings escaped here, act is HTML). A folded card with something to do says so in its title. */
export function planCard(x,{title,sub='',rows=[],foot='',key='plan'}){
  if(!rows.length)return '';
  const hot=rows.some(r=>r.tone==='bad'||r.tone==='warn'),can=rows.filter(r=>r.act).length;
  const open=kept(x,key,hot);
  if(can&&!hot)sub=`${sub}${sub?' · ':''}${can} việc làm được`;
  const li=rows.map(r=>`<li class="ok-plan-row${r.tone?' tone-'+x.esc(r.tone):''}"><span class="ok-plan-ico" aria-hidden="true">${x.esc(r.emoji||'•')}</span>
    <span class="ok-plan-main"><span class="ok-plan-title"><b>${x.esc(r.title)}</b>${r.tag?` <span class="ok-tag ${x.esc(PLAN_TONE[r.tag.tone]??r.tag.tone??'')}">${x.esc(r.tag.label)}</span>`:''}</span>${r.note?`<small>${x.esc(r.note)}</small>`:''}</span>
    ${r.act?`<span class="ok-plan-act">${r.act}</span>`:''}</li>`).join('');
  return fold(`${x.esc(title)}${sub?` <small>${x.esc(sub)}</small>`:''}`,`<ul class="ok-plan-list">${li}</ul>${foot?`<p class="ok-note">${foot}</p>`:''}`,open,'ok-plan',key);
}
export const planTone=s=>PLAN_TONE[s]??'';

const BOND=['Mới quen','Quen mặt','Quen việc','Thân','Rất thân','Như người nhà'];
const hearts=n=>`<span class="ok-bond" role="img" aria-label="Thân thiết ${n}/5">${'♥'.repeat(n)}<i>${'♡'.repeat(Math.max(0,5-n))}</i></span><small class="ok-bond-name">${BOND[n]||''}</small>`;
/** Colleague cards: bond, favour owed, today's request (help / not today) and "cover me" on a dossier due today. */
export function mateCards(x,{prefix,t=null}){
  const cr=x.room.data?.care;if(!cr?.mates?.length)return '';
  const can=new Set(cr.coverable||[]),open=x.room.open;
  const target=t&&can.has(t.id)?t:openTasks(x).filter(v=>can.has(v.id)).sort((a,b)=>a.due-b.due)[0];
  const cards=cr.mates.map(m=>{
    const av=m.npc?x.portrait(x.npc(m.npc),40):`<span class="ok-emoji">${x.esc(m.emoji)}</span>`;
    const owes=m.owes?`<span class="ok-tag good">Nợ bạn ${m.owes} lần giúp</span>`:'';
    const ask=m.ask?`<div class="ok-ask"><p class="ok-bubble">“${x.esc(m.ask.text)}”</p><div class="ok-btns">${x.cmd(`🤝 Giúp · ${m.ask.minutes} phút`,prefix+'help',{mate:m.id,answer:'yes'},'primary small',!open)}${x.cmd('Để hôm khác',prefix+'help',{mate:m.id,answer:'no'},'ghost small',!open)}</div></div>`:'';
    const cover=m.owes&&target&&open?`<div class="ok-btns">${x.cmd(`🙏 Nhờ đỡ “${x.esc(target.title.length>34?target.title.slice(0,33)+'…':target.title)}” +1 giờ`,prefix+'cover',{mate:m.id,task:target.id},'ghost small')}</div>`:'';
    return `<li class="ok-mate${m.ask?' asking':''}"><span class="ok-av" aria-hidden="true">${av}</span><span class="ok-mate-main"><span class="ok-mate-name"><b>${x.esc(m.name)}</b> <small>${x.esc(m.role)}</small></span><span class="ok-mate-meta">${hearts(Number(m.bond)||0)}${owes}</span></span>${ask}${cover}</li>`;
  }).join('');
  // Folded to one line; it opens by itself while a colleague is asking for help.
  const owed=cr.mates.filter(m=>m.owes).length;
  const sum=`👥 Đồng nghiệp <small>${cr.mates.length} người${owed?` · ${owed} người nợ bạn`:''}</small>${cr.asked?' <span class="ok-tag info">Có người nhờ</span>':''}`;
  return fold(sum,`<ul class="ok-mates">${cards}</ul>
    <p class="ok-note">Giúp thì mất ít phút nhưng người ta nhớ — lúc kẹt hạn, nhờ lại được một lần (+1 giờ). Từ chối không sao cả.</p>`,kept(x,'mates',!!cr.asked),'ok-people','mates');
}

/** The mentor / promotion track, energy and the career story arc, folded. */
export function trackFold(x,{prefix,career}){
  const cr=x.room.data?.care;if(!cr?.track)return '';
  const tr=cr.track,e=cr.energy||{},n=tr.next;
  const days=(tr.days||[]).map(v=>`<li class="${v.ok?'ok':'miss'}" title="${x.esc(v.why)}"><b>${v.ok?'✓':'✗'}</b><small>N${Number(v.day)||0}</small></li>`).join('');
  const ladder=(tr.ranks||[]).map((r,i)=>`<li class="${i<tr.rank?'done':i===tr.rank?'now':''}">${i<tr.rank?'✓':i===tr.rank?'●':'○'} ${x.esc(r)}</li>`).join('');
  const next=n?`Bước tiếp: <b>${x.esc(n.title)}</b> — ${n.left?`còn ${n.left} ngày làm chắc tay`:'đủ ngày chắc tay'}${n.trust?` · ${x.esc(cr.mentor)} tin tưởng từ ${n.trust}${n.trust_ok?' ✓':''}`:''}.`:`${x.esc(cr.mentor)} đã đề cử bạn — quyết định nằm ở truyện nghề.`;
  const perks=(tr.perks||[]).map(p=>`<li class="${p.on?'on':''}">${p.on?'✓':'🔒'} ${x.esc(p.text)}</li>`).join('');
  const arc=(x.state?.stories?.arcs||[]).find(a=>a.career===career);
  const story=arc&&arc.seen?`<div class="ok-story"><b>📖 Truyện nghề: ${x.esc(arc.title)} · ${arc.seen}/${arc.total}</b><ul>${(arc.beats||[]).map(b=>`<li>✓ ${x.esc(b.emoji)} ${x.esc(b.title)}</li>`).join('')}${arc.hint&&!arc.done?`<li class="next">… ${x.esc(arc.hint)}</li>`:''}</ul></div>`:'';
  const pct=Math.max(0,Math.min(100,Number(e.value)||0));
  const brk=e.can_break?x.cmd(`☕ Nghỉ giải lao 15 phút (+${e.gain})`,prefix+'break',{},'ghost small'):'';
  const body=`<div class="ok-track"><p class="ok-note">Ngày làm chắc tay: nộp ít nhất một hồ sơ, không trễ hạn, không sai nặng. Đã có <b>${tr.reliable}</b> ngày${tr.streak>1?` · chuỗi ${tr.streak} ngày`:''}.</p>
      ${days?`<ol class="ok-days" aria-label="7 ngày gần đây">${days}</ol>`:''}
      <ol class="ok-ladder">${ladder}</ol><p class="ok-note">${next}</p><ul class="ok-perks">${perks}</ul>${story}</div>
    <div class="ok-energy-box"><span class="ok-energy-row"><b>🔋 Sức bền ${pct}/100 · ${x.esc(e.label||'')}</b></span><span class="ok-meter ${pct<35?'low':pct>=80?'high':''}" role="meter" aria-label="Sức bền" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><i style="width:${pct}%"></i></span>
      <p class="ok-note">Về đúng giờ +${e.rest} mỗi đêm · tăng ca −${e.ot}. Dưới ${e.line}: làm chậm hơn, không được tăng ca.</p>${brk?`<div class="ok-btns">${brk}</div>`:''}</div>`;
  return fold(`🧭 Lộ trình & sức bền <small>${x.esc(tr.title)} · 🔋 ${pct}</small>`,body,kept(x,'track',false),'ok-trackfold','track');
}

/** Day-close summary rows for the shared care part (energy, reliable day, rank). */
export function careSummary(care,x){
  if(!care||typeof care!=='object')return '';
  const ch=Number(care.energy_change)||0,rows=[];
  const row=(k,v)=>rows.push(`<div class="kv-row"><span>${x.esc(k)}</span><b>${x.esc(v)}</b></div>`);
  row('Sức bền',`🔋 ${care.energy}/100 · ${care.energy_label}${ch?` (${ch>0?'+':''}${ch})`:''}`);
  row('Ngày làm chắc tay',`${care.reliable?'✓':'✗'} ${care.why}${care.streak>1?` · chuỗi ${care.streak}`:''}`);
  row('Lộ trình',care.rank_up?`🎉 ${care.rank_up}`:`${care.rank} · ${care.total} ngày chắc tay`);
  if(care.pay)row('Phụ cấp trách nhiệm',`+${care.pay} xu`);
  return rows.join('');
}

/* ---------------------------------------------------------------- inbox */
const emoji=e=>`<span class="ok-emoji">${e}</span>`;
/** One message. Every field is ready HTML (escape before). `act` makes the row a button. */
export function mail(m){
  const tag=m.tag?`<span class="ok-tag ${m.tag.tone||''}">${m.tag.label}</span>`:'';
  if(m.line&&!m.body){
    // One line: avatar · subject (· sender) · tag/time. A dossier opens on tap; a note unfolds its text.
    const cls=`ok-mail line${m.tone?' tone-'+m.tone:''}${m.unread?' unread':''}`;
    const row=`<span class="ok-av sm" aria-hidden="true">${m.avatar||emoji('✉️')}</span><span class="ok-line-subj">${m.unread?'<i class="ok-dot" aria-label="Chưa đọc"></i>':''}<b>${m.subject}</b>${m.from?` <small>· ${m.from}</small>`:''}</span>${tag||m.time?`<span class="ok-line-meta">${tag}${m.time?`<time>${m.time}</time>`:''}</span>`:''}`;
    if(m.act)return `<li><button type="button" class="${cls}" ${m.act}${m.preview?` title="${m.preview.replace(/"/g,'&quot;')}"`:''}>${row}<span class="ok-go" aria-hidden="true">›</span></button></li>`;
    if(m.preview)return `<li><details class="${cls}"><summary>${row}</summary><p class="ok-line-text">${m.preview}</p></details></li>`;
    return `<li class="${cls}"><div class="ok-line-row">${row}</div></li>`;
  }
  const head=`<span class="ok-av" aria-hidden="true">${m.avatar||emoji('✉️')}</span><span class="ok-mail-main">
      <span class="ok-mail-from"><span class="ok-who"><b>${m.from}</b>${m.role?` <small>${m.role}</small>`:''}</span>${m.time?`<time>${m.time}</time>`:''}</span>
      <span class="ok-mail-subj">${m.unread?'<i class="ok-dot" aria-label="Chưa đọc"></i>':''}${m.subject}${tag?' '+tag:''}</span>
      ${m.preview?`<span class="ok-mail-text">${m.preview}</span>`:''}</span>`;
  const cls=`ok-mail${m.current?' current':''}${m.tone?' tone-'+m.tone:''}${m.unread?' unread':''}`;
  if(m.act)return `<li><button type="button" class="${cls}" ${m.act}>${head}<span class="ok-go" aria-hidden="true">›</span></button></li>`;
  return `<li class="${cls}"><div class="ok-mail-row">${head}</div>${m.body?`<div class="ok-mail-body">${m.body}</div>`:''}</li>`;
}

/** Messages for the open dossiers: the one on the desk first (expanded with `body`), the rest open on tap. */
export function taskMails(x,t,body=''){
  const list=openTasks(x);if(t&&!list.some(v=>v.id===t.id))list.unshift(t);
  list.sort((a,b)=>(b.id===t?.id)-(a.id===t?.id));
  return list.map(v=>{
    const who=x.npc(v.npc),due=dueOf(v,x),cur=v.id===t?.id;
    const tag=cur?{label:'Đang mở',tone:'accent'}:due?.overdue?{label:'Trễ hạn',tone:'bad'}:!v.known?{label:'Mới',tone:'info'}:null;
    return {line:!cur,avatar:x.portrait(who,40),from:x.esc(who.display_name),role:x.esc(who.role||''),time:due&&!cur?`Hạn ${x.esc(due.time)}`:'',
      subject:x.esc(v.title),preview:cur?'':`“${x.esc(v.opening)}”`,unread:!v.known&&!cur,current:cur,tag,
      body:cur?body:'',act:cur?'':`data-action="job" data-task="${x.esc(v.id)}" aria-label="${x.esc(`Mở việc: ${v.title} · ${who.display_name}`)}"`};
  });
}

/** Messages of the day: new rules, the day's luck, fines and late notes from the office log. */
export function dayMails(x,{boss,key}){
  const d=x.room.data||{},o=d.office||{},mod=d.today?.mod,out=[];
  const fresh=(d.today?.rules||[]).filter(r=>r.new);
  if(fresh.length)out.push({avatar:emoji('📋'),from:x.esc(boss),role:'Quy định mới',tone:'warn',
    subject:`${fresh.length} quy định đổi từ hôm nay`,preview:fresh.map(r=>`${x.esc(r.emoji)} ${x.esc(r.title)}`).join(' · '),
    act:key?`data-action="car:tab" data-tab="rules" data-key="${x.esc(key)}"`:''});
  if(mod&&mod.id!=='normal')out.push({avatar:emoji(x.esc(mod.emoji)),from:x.esc(boss),role:'Việc hôm nay',subject:x.esc(mod.name),preview:x.esc(mod.text)});
  if(o.tired)out.push({avatar:emoji('😮‍💨'),from:'Chấm công',subject:'Hôm qua tăng ca nên sáng nay vào muộn 30 phút.'});
  const KIND={fine:['💸','Phòng tài vụ','bad'],late:['⏰','Nhắc hạn','warn'],care:['🧭',x.esc(boss),'']};
  for(const n of [...(o.notes||[])].reverse()){
    if(n.day!==x.room.day||!KIND[n.kind])continue;
    const [e,from,tone]=KIND[n.kind];
    out.push({avatar:emoji(e),from,tone,subject:x.esc(n.text)});
  }
  return out.map(m=>({...m,line:true}));
}

/** The inbox pane: dossiers, then other messages, then "take more work". */
export function inboxPane(x,{tasks=[],other=[],title='Hộp thư đến',plan='',people='',track='',take=true}){
  const open=openTasks(x),more=take&&x.room.open&&!x.room.more_gate&&open.length<4?`<p class="ok-more">${x.cmd('＋ Nhận thêm việc','more_work',{},'ghost')}</p>`:'';
  return `<h3 class="ok-h">📥 ${x.esc(title)} <small>${tasks.length+other.length} thư</small></h3>
    ${tasks.length?`<ul class="ok-mails" aria-label="Việc được giao">${tasks.map(mail).join('')}</ul>`:''}
    ${more}${plan}${people}
    ${other.length?`<h4 class="ok-h2">Tin nhắn trong ngày</h4><ul class="ok-mails" aria-label="Tin nhắn">${other.map(mail).join('')}</ul>`:''}
    ${track}`;
}

/** Today's rules, one line each (the title; the text opens on tap). New ones come first, marked MỚI. */
export function rulesList(x,rules,title){
  if(!rules?.length)return '';
  const card=r=>`<li><details class="ok-rule${r.new?' new':''}"><summary><span class="ok-rule-ico" aria-hidden="true">${x.esc(r.emoji)}</span><b class="ok-rule-title">${x.esc(r.title)}${r.new?' <em class="ok-newtag">MỚI</em>':''}</b></summary><p class="ok-rule-txt">${x.esc(r.text)}</p></details></li>`;
  const fresh=rules.filter(r=>r.new),rest=rules.filter(r=>!r.new);
  return `<section class="ok-rules"><h3 class="ok-h">📋 ${x.esc(title)} <small>${rules.length} quy định · chạm để đọc</small>${fresh.length?` <span class="ok-tag warn">${fresh.length} mới</span>`:''}</h3>
    <ul class="ok-rule-list">${[...fresh,...rest].map(card).join('')}</ul></section>`;
}

/* ---------------------------------------------------------------- the desk frame */
export const tabKey=t=>`${t.id}:${t.known?1:0}`;
const TAB_TONE={warn:'warn',bad:'bad'};

/** tabs: [{id:'inbox'|'doc'|'rules'|'books', icon, label, badge, tone}]; panes: {id: html}. */
export function desk(x,t,{cls,tabs,panes,strip,bar,def,hint=''}){
  x.ui.okLast=t.id;   // the done screen (idleDesk) knows which dossier just closed
  const key=tabKey(t),want=x.ui.okTab?.[key]||def||(t.known?'doc':'inbox');
  const tab=tabs.some(v=>v.id===want)?want:tabs[0].id;
  const nav=tabs.map(v=>`<button type="button" role="tab" class="ok-tab ok-tab-${v.id}" id="ok-tab-${v.id}" data-action="car:tab" data-tab="${v.id}" data-key="${x.esc(key)}" aria-controls="ok-pane-${v.id}" aria-selected="${v.id===tab}">
      <span class="ok-tab-ico" aria-hidden="true">${v.icon}</span><span class="ok-tab-label">${x.esc(v.label)}</span>${v.badge?`<em class="ok-badge ${TAB_TONE[v.tone]||''}">${x.esc(String(v.badge))}</em>`:''}</button>`).join('');
  return `<div class="career-job ok ${cls}" data-ok-tab="${tab}">${hint}${strip}
    <nav class="ok-tabs" role="tablist" aria-label="Bàn làm việc">${nav}</nav>
    ${tabs.map(v=>`<section class="ok-pane ok-pane-${v.id}" id="ok-pane-${v.id}" role="tabpanel" aria-labelledby="ok-tab-${v.id}">${panes[v.id]||''}</section>`).join('')}
    ${bar}</div>`;
}

/** Sticky bottom bar: the next step + the main action. On a phone, from another tab it offers the way back to the document
 * (unless `always`, e.g. "receive the dossier", which works from anywhere). */
const plain=s=>String(s).replace(/<[^>]*>/g,' ').replace(/&[a-z]+;/g,' ').toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();
/** A label that only repeats the single main button ("Nhận khay chứng từ" + "📥 Nhận khay chứng từ") is dropped. */
const echoes=(next,main)=>{
  if(!main||(main.match(/<button\b/g)||[]).length!==1)return false;
  const a=plain(next),b=plain(main);
  return !!b&&(a===b||a.startsWith(b+' '));
};
export function bar(x,t,next,main='',always=false){
  const cap=String(next).replace(/^\s*(\S)/,(m,c)=>m.replace(c,c.toUpperCase()));
  const label=next&&!echoes(next,main)?`<p class="ok-next" aria-live="polite">${cap}</p>`:'';
  const back=main?'primary big grow gd-cta':'ghost';
  return `<div class="ok-bar${always?' always':''}${main?'':' bare'}">${label}
    ${main?`<div class="ok-bar-btns ok-main">${main}</div>`:''}
    <div class="ok-bar-btns ok-back"><button type="button" class="btn ${back}" data-action="car:tab" data-tab="doc" data-key="${x.esc(tabKey(t))}">📂 Về hồ sơ</button></div></div>`;
}

/* ---------------------------------------------------------------- the office is shut (office.need_open: office_closed) */
/** After 17:30 (20:00 with overtime) every piece of work that takes office time is refused. */
export const shut=x=>Boolean(x.room.open&&x.room.data?.office?.closed);
/** While shut, the career's work buttons are drawn disabled: its commands (`prefix…`, except overtime and what
 * `free(op, tag)` lets through) and its client actions that send one (`acts`, e.g. ['check'] for car:check). */
export function shutWork(x,html,{prefix,acts=[],free=()=>false}){
  if(!shut(x))return html;
  return String(html).replace(/<button\b[^>]*>/g,tag=>{
    if(/\sdisabled\b/.test(tag))return tag;
    const op=/\sdata-(?:command|op)="([^"]*)"/.exec(tag)?.[1]||'',act=/\sdata-action="car:([^"]*)"/.exec(tag)?.[1]||'';
    const work=acts.includes(act)||op.startsWith(prefix)&&op!==prefix+'overtime'&&!free(op,tag);
    return work?tag.replace(/>$/,' disabled title="Văn phòng đã đóng cửa">'):tag;
  });
}
/** The bottom bar while shut: why, and the day's close (app.js “end”). Overtime stays in the status strip. */
export function shutBar(x,t){
  const o=x.room.data.office;
  return bar(x,t,`🌇 Văn phòng đóng cửa lúc ${x.esc(o.limit_time||'17:30')} — việc dở được giữ nguyên.`,x.button(`${x.icon('exit',16)} Khép ca · xem tổng kết`,'end',{},'primary big grow'));
}

/* ---------------------------------------------------------------- next step (v4/guide.js) */
/** What the server tells the first dossier's screen (office.coach): null on every later dossier. */
export const coachOf=(x,t)=>firstTime(x)&&x.room.data?.coach?.[t.id]||null;
/** A step that lives on the document: bring the 📂 tab forward, then scroll to `sel` and flash it. */
export const goto=(x,t,sel,label='')=>({act:'car:goto',data:{tab:'doc',key:tabKey(t),sel},...(label?{label}:{})});
export function gotoAction(data,el,x){
  switchTab(data,el,x);
  const root=rootOf(el);if(!root||!data.sel)return;
  requestAnimationFrame(()=>{const all=[...root.querySelectorAll(data.sel)];highlight(all.find(e=>e.offsetParent!==null)||all[0]);});
}
const plainLabel=s=>String(s||'').replace(/<[^>]*>/g,'').replace(/^[^\p{L}\p{N}]+/u,'').trim();
/** The one-line hint (top of the job, pinned in the sheet header) and the bar's main button, from one step list.
 * `final` = {label (HTML), go, ready?}: the finishing action once nothing is left. A step may carry `hintGo`: what the
 * hint does when it should point rather than act (the bottom button still acts). */
export function guideOf(x,t,steps,final=null,{done='',main=''}={}){
  // The hint says the step (the button says the action): drop the button label unless the step points elsewhere.
  const hs=steps.map(s=>s.hintGo?{...s,go:s.hintGo}:s.go?{...s,go:{...s.go,label:''}}:s);
  const hint=nextHint(x,hs,{final:final&&final.ready!==false?{label:plainLabel(final.label),go:final.go}:null,done});
  let cta=main;
  if(!cta){
    if(final)cta=stepCta(x,steps,final,{style:'primary big grow'});
    else{const n=pending(steps);cta=n?.go?`<button type="button" class="btn primary big grow gd-cta"${goAttrs(n.go)}>${n.go.label||`👉 ${x.esc(n.label)}`}</button>`:'';}
  }
  return {hint,cta};
}

/** Steps of a step-by-step dossier (corp & group share the widgets: `pre` = 'ca' | 'ga', `confirm` = {kind: [label, action]}).
 * Papers the step needs are opened first. On a first dossier a choice lights the right option and any other
 * step offers “✍️ Điền theo chứng từ” (coachFill) before its confirm button; later the hint points at the step. */
export function procSteps(x,t,{pre,confirm}){
  const st=(t.proc||[]).find(s=>s.state==='current');if(!st)return [];
  const out=[],co=coachOf(x,t),key=co&&co.step===st.id?co.key:undefined;
  for(const id of st.docs||[]){
    const d=(t.docs||[]).find(v=>v.id===id);
    if(d?.closed)out.push({ok:null,label:`Mở “${d.title}”`,go:{act:'car:open',data:{task:t.id,doc:d.id},label:`📂 Mở “${x.esc(d.title)}”`}});
  }
  const at=(t.proc_state?.at||0)+1,total=t.proc_state?.total||(t.proc||[]).length,label=`Bước ${at}/${total}: ${st.title}`;
  if(st.kind==='choice'){
    if(key===undefined)out.push({ok:null,label,go:goto(x,t,`.${pre}-options`,'👇 Chọn một đáp án')});
    else{
      // First dossier: the right option glows, and the bottom button (or the hint) answers with it.
      const o=(st.options||[]).find(v=>v.id===key),sel=`.${pre}-opt[data-opt="${key}"]`;
      out.push({ok:null,label,go:{cmd:`${pre}_step`,payload:{task:t.id,step:st.id,answer:key},label:`👉 ${x.esc(o?.label||'Chọn đáp án đang sáng')}`},pulse:sel});
    }
    return out;
  }
  const [cl,act]=confirm[st.kind]||['✔ Xác nhận',''],k=`${t.id}:${st.id}`;
  // An order list starts complete: until the player moves an item (or has tried once) the button points at the list.
  if(key===undefined&&st.kind==='order'&&!x.ui.moved?.[k]&&!(t.proc_state?.attempts||{})[st.id]){
    out.push({ok:null,label,go:goto(x,t,`.${pre}-order`,'↕️ Xếp lại bằng ↑ ↓')});
    return out;
  }
  if(key!==undefined&&!x.ui.coached?.[k])
    out.push({ok:null,label,go:{act:'car:coach',data:{task:t.id,step:st.id},label:'✍️ Điền theo chứng từ'}});
  else out.push({ok:null,label,go:{act,data:{task:t.id,step:st.id},label:cl},...(key===undefined?{hintGo:goto(x,t,`.${pre}-work`)}:{})});
  return out;
}
/** car:coach — fills the current step's sheet from the first dossier's key (drafts are `${task}:${step}`), then re-renders. */
export function coachFill(data,el,x){
  const t=(x.room.tasks||[]).find(v=>v.id===data.task),st=(t?.proc||[]).find(s=>s.id===data.step),co=t&&x.room.data?.coach?.[t.id];
  if(!st||co?.step!==st.id)return;
  const k=`${t.id}:${st.id}`,key=co.key,dr=(x.ui.drafts??={});
  if(st.kind==='multi'||st.kind==='order')dr[k]=[...key];
  else if(st.kind==='number')dr[k]=String(key);
  else if(st.kind==='match')dr[k]={...key};
  else if(st.kind==='fields')dr[k]=Object.fromEntries(Object.entries(key).map(([f,v])=>[f,String(v)]));
  else if(st.kind==='entry'){
    const side=i=>{const m=new Map();for(const r of key)m.set(r[i],(m.get(r[i])||0)+Number(r[2]));return [...m].map(([account,amount])=>({account,amount:String(amount)}));};
    dr[k]={debit:side(0),credit:side(1)};
  }
  (x.ui.coached??={})[k]=true;x.render();
}

/** Client-only tab switch (no re-render, so typed numbers and ticks stay). */
const rootOf=el=>el.closest('.career-job.ok')||el.closest('dialog')?.querySelector('.career-job.ok')||document.querySelector('dialog[open] .career-job.ok');
export function switchTab(data,el,x){
  const root=rootOf(el);if(!root||!data.tab)return;
  if(data.key)(x.ui.okTab??={})[data.key]=data.tab;
  root.dataset.okTab=data.tab;
  root.querySelectorAll('.ok-tab').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===data.tab)));
  const nav=root.querySelector('.ok-tabs'),dlg=root.closest('dialog');
  if(nav&&dlg){
    const hb=dlg.querySelector('.sheet-head')?.getBoundingClientRect().bottom||0,top=nav.getBoundingClientRect().top;
    if(top<hb)dlg.scrollTop+=top-hb-8;
  }
  if(el.classList.contains('ok-mail')||el.closest('.ok-bar'))root.querySelector(`#ok-tab-${CSS.escape(data.tab)}`)?.focus({preventScroll:true});
}

/** Keeps the sticky bar above the sheet's own sticky footer (call from tick). It also keeps the work in view:
 * on a first dossier the glowing control once per render; otherwise the card of the step / set / person on the
 * desk ([data-step-card]) once each time it changes. Scrolling only, the DOM is never replaced. */
let followed='';
/* The footer's height comes from a ResizeObserver (read right after layout, for free), as in food_kit: reading
 * getComputedStyle + offsetHeight on every 200 ms tick forced a layout each time the DOM had just changed.
 * No footer (work sheets have none now): the bar sits on the sheet's bottom edge, above the phone's home bar. */
const NO_FOOT='env(safe-area-inset-bottom, 0px)';
const okFoot={el:null,root:null,h:null,ro:null};
function setOkFoot(root,v){if(root.dataset.okFoot!==v){root.dataset.okFoot=v;root.style.setProperty('--ok-foot',v);}}
function watchOkFoot(foot){
  const W=okFoot,measure=()=>getComputedStyle(foot).position==='sticky'?foot.offsetHeight:0;
  W.ro?.disconnect();W.el=foot;W.h=null;
  if(typeof ResizeObserver!=='function'){W.h=measure();return;}
  W.ro=new ResizeObserver(()=>{if(W.el!==foot)return;W.h=measure();if(W.root?.isConnected)setOkFoot(W.root,W.h+'px');});
  W.ro.observe(foot);
}
/** Layout reads for the follow scroll wait for the next frame (the layout the browser does anyway), one pending at a time. */
let followFrame=0;
export function keepBarAboveFooter(root){
  const dlg=root.closest('dialog'),foot=dlg?.querySelector('.sheet-foot');
  if(!foot)setOkFoot(root,NO_FOOT);
  else{if(okFoot.el!==foot)watchOkFoot(foot);okFoot.root=root;if(okFoot.h!==null)setOkFoot(root,okFoot.h+'px');}
  if(root.dataset.okFollow||!dlg||followFrame)return;
  followFrame=requestAnimationFrame(()=>{followFrame=0;if(root.isConnected&&!root.dataset.okFollow)follow(root,dlg);});
}
function follow(root,dlg){
  const smooth=matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth';
  const top=dlg.querySelector('.sheet-head')?.getBoundingClientRect().bottom||0,low=root.querySelector(':scope>.ok-bar')?.getBoundingClientRect().top||innerHeight;
  const el=root.querySelector('.ok-pane .gd-pulse');
  if(el){
    if(el.offsetParent===null)return;
    root.dataset.okFollow='1';
    const r=el.getBoundingClientRect();
    if(r.top<top||r.bottom>low)el.scrollIntoView({block:'center',behavior:smooth});
    return;
  }
  const card=root.querySelector('.ok-pane-doc [data-step-card]');
  if(!card||card.offsetParent===null)return;
  root.dataset.okFollow='1';
  if(card.dataset.stepCard===followed)return;
  followed=card.dataset.stepCard;
  const r=card.getBoundingClientRect();
  if(r.top<top||r.top>top+(low-top)*.45)dlg.scrollBy({top:r.top-top-8,behavior:smooth});
}

/** A folded section (native details; the summary is HTML). */
export function fold(summary,body,open=false,cls='',key=''){
  return `<details class="ok-fold${cls?' '+cls:''}"${open?' open':''}><summary${key?` data-action="car:fold" data-fold="${key}"`:''}>${summary}</summary><div class="ok-fold-body">${body}</div></details>`;
}
/** Remembers a care fold the player opened or closed (read after the native toggle has happened). */
export function foldToggle(data,el,x){const d=el.closest('details');if(d&&data.fold)setTimeout(()=>{(x.ui.okFold??={})[data.fold]=d.open;},0);}
const kept=(x,key,open)=>x.ui.okFold?.[key]??open;

/** Between dossiers: the strip, a recap, the inbox and today's rules. Right after a dossier closes (the
 * “done” screen) only the recap stays open; the rest of the desk folds into one line under it. */
export function idleDesk(x,{cls,strip,recap='',tasks=[],other=[],rules='',plan='',people='',track=''}){
  const last=(x.room.tasks||[]).find(v=>v.id===x.ui.okLast),done=!!last&&DONE.includes(last.status);
  const panes=take=>`<section class="ok-pane ok-pane-inbox">${inboxPane(x,{tasks,other,plan,people,track,take})}</section>${rules?`<section class="ok-pane ok-pane-rules">${rules}</section>`:''}`;
  if(!done)return `<div class="career-job ok ok-idle ${cls}">${strip}${recap}${panes(true)}</div>`;
  const n=tasks.length+other.length,ask=other.filter(m=>m.body).length;
  // The screen's own button takes more work, so the folded inbox leaves its “＋ Nhận thêm việc” out.
  // data-idle-open: the done screen (app.js) shows this recap as it is instead of folding it away.
  return `<div class="career-job ok ok-idle ok-done ${cls}" data-idle-open>${recap}${fold(`📥 Bàn làm việc <small>${n} thư · lịch & quy định</small>${ask?` <span class="ok-tag bad">${ask} cần trả lời</span>`:''}`,`${strip}${panes(false)}`,kept(x,'desk',false),'ok-deskfold','desk')}</div>`;
}
