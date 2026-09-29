/** Shared "office desktop" for the three office careers (corp_accounting,
 * tax_payroll, group_accounting): a status strip (clock, deadline, the boss's
 * trust, energy) with the five-day calendar strip, folder tabs (📥 Hộp thư · 📂 Hồ sơ ·
 * 📋 Quy định · 📒 Sổ sách), an email-like inbox with the career's plan, colleague
 * cards and the mentor track, and a sticky bottom bar with the next step and the main
 * action. Phones show one tab at a time; wide sheets put the inbox (or the
 * rules) on the left and the document on the right.
 * Pure string builders plus two client-only helpers (tab switch, bar offset):
 * every game action still goes through the career's own commands. */

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
  const energy=en?`<span class="ok-energy ${x.esc(en.tone||'')}" role="img" aria-label="Sức bền ${Number(en.value)||0}/100 · ${x.esc(en.label||'')}">🔋 Sức bền <b>${Number(en.value)||0}</b>${tired?` · ${x.esc(en.label)}`:''}</span>`:'';
  if(!alert&&en?.low&&!o.locked)alert=`<p class="ok-alert warn">😮‍💨 Sức bền ${Number(en.value)||0}/100 — việc gì cũng chậm hơn một chút, hôm nay không tăng ca được. Về đúng giờ là hồi lại.</p>`;
  return `<div class="ok-top"><header class="ok-strip" aria-label="Giờ làm việc hôm nay">
    <span class="ok-clock"><b>🕗 ${x.esc(o.time)}</b><small>${o.overtime?'tăng ca tới 20:00':o.lunch?'nghỉ trưa 12:00':'tan sở 17:30'}</small>${energy}</span>
    <span class="ok-trust"><small>👩‍💼 ${x.esc(boss)}: <b>${x.esc(o.trust_label||'')}</b></small><span class="ok-meter ${lvl}" role="meter" aria-label="${x.esc(boss)} tin bạn" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${trust}"><i style="width:${trust}%"></i></span></span>
    ${due?`<span class="ok-due ${due.overdue?'bad':due.soon?'warn':''}">⏰ ${x.esc(dueText(due))}</span>`:''}
    ${mod&&mod.id!=='normal'?`<span class="ok-modchip">${x.esc(mod.emoji)} ${x.esc(mod.name)}</span>`:''}
  </header>${alert}${calStrip(x)}</div>`;
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

const PLAN_TONE={done:'good',filed:'good',ok:'good',late_done:'warn',late_filed:'warn',boss:'bad',late:'bad',due:'warn',in:'info',fixing:'info',todo:'',wait:'',locked:''};
/** A plan card, folded (open by itself when a row needs you today): rows [{emoji, title, note, tag:{label, tone},
 * act (ready HTML), tone}] (strings escaped here, act is HTML). */
export function planCard(x,{title,sub='',rows=[],foot='',key='plan'}){
  if(!rows.length)return '';
  const open=kept(x,key,rows.some(r=>r.act||r.tone==='bad'||r.tone==='warn'));
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
  return `<section class="ok-people"><h4 class="ok-h2">👥 Đồng nghiệp${cr.asked?' <span class="ok-tag info">Có người nhờ</span>':''}</h4><ul class="ok-mates">${cards}</ul>
    <p class="ok-note">Giúp thì mất ít phút nhưng người ta nhớ — lúc kẹt hạn, nhờ lại được một lần (+1 giờ). Từ chối không sao cả.</p></section>`;
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
    return {avatar:x.portrait(who,40),from:x.esc(who.display_name),role:x.esc(who.role||''),time:due&&!cur?`Hạn ${x.esc(due.time)}`:'',
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
  const KIND={fine:['💸','Phòng tài vụ','bad'],late:['⏰','Nhắc hạn','warn'],care:['🧭',boss,'']};
  for(const n of [...(o.notes||[])].reverse()){
    if(n.day!==x.room.day||!KIND[n.kind])continue;
    const [e,from,tone]=KIND[n.kind];
    out.push({avatar:emoji(e),from,tone,subject:x.esc(n.text)});
  }
  return out;
}

/** The inbox pane: dossiers, then other messages, then "take more work". */
export function inboxPane(x,{tasks=[],other=[],title='Hộp thư đến',plan='',people='',track=''}){
  const open=openTasks(x),more=x.room.open&&open.length<4?`<p class="ok-more">${x.cmd('＋ Nhận thêm việc','more_work',{},'ghost')}</p>`:'';
  return `<h3 class="ok-h">📥 ${x.esc(title)} <small>${tasks.length+other.length} thư</small></h3>
    ${tasks.length?`<ul class="ok-mails" aria-label="Việc được giao">${tasks.map(mail).join('')}</ul>`:''}
    ${more}${plan}${people}
    ${other.length?`<h4 class="ok-h2">Tin nhắn trong ngày</h4><ul class="ok-mails" aria-label="Tin nhắn">${other.map(mail).join('')}</ul>`:''}
    ${track}`;
}

/** Today's rule cards (new ones first). */
export function rulesList(x,rules,title){
  if(!rules?.length)return '';
  const fresh=rules.filter(r=>r.new).length,sorted=[...rules].sort((a,b)=>(b.new?1:0)-(a.new?1:0));
  return `<section class="ok-rules"><h3 class="ok-h">📋 ${x.esc(title)}${fresh?` <span class="ok-tag warn">${fresh} mới</span>`:''}</h3>
    <ul class="ok-rule-list">${sorted.map(r=>`<li class="ok-rule${r.new?' new':''}"><span class="ok-rule-ico" aria-hidden="true">${x.esc(r.emoji)}</span><span class="ok-rule-txt"><b>${x.esc(r.title)}${r.new?' <em class="ok-newtag">MỚI</em>':''}</b><span>${x.esc(r.text)}</span></span></li>`).join('')}</ul></section>`;
}

/* ---------------------------------------------------------------- the desk frame */
export const tabKey=t=>`${t.id}:${t.known?1:0}`;
const TAB_TONE={warn:'warn',bad:'bad'};

/** tabs: [{id:'inbox'|'doc'|'rules'|'books', icon, label, badge, tone}]; panes: {id: html}. */
export function desk(x,t,{cls,tabs,panes,strip,bar,def}){
  const key=tabKey(t),want=x.ui.okTab?.[key]||def||(t.known?'doc':'inbox');
  const tab=tabs.some(v=>v.id===want)?want:tabs[0].id;
  const nav=tabs.map(v=>`<button type="button" role="tab" class="ok-tab ok-tab-${v.id}" id="ok-tab-${v.id}" data-action="car:tab" data-tab="${v.id}" data-key="${x.esc(key)}" aria-controls="ok-pane-${v.id}" aria-selected="${v.id===tab}">
      <span class="ok-tab-ico" aria-hidden="true">${v.icon}</span><span class="ok-tab-label">${x.esc(v.label)}</span>${v.badge?`<em class="ok-badge ${TAB_TONE[v.tone]||''}">${x.esc(String(v.badge))}</em>`:''}</button>`).join('');
  return `<div class="career-job ok ${cls}" data-ok-tab="${tab}">${strip}
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
  return `<div class="ok-bar${always?' always':''}${main?'':' bare'}">${label}
    ${main?`<div class="ok-bar-btns ok-main">${main}</div>`:''}
    <div class="ok-bar-btns ok-back"><button type="button" class="btn ghost" data-action="car:tab" data-tab="doc" data-key="${x.esc(tabKey(t))}">📂 Về hồ sơ</button></div></div>`;
}

/** Client-only tab switch (no re-render, so typed numbers and ticks stay). */
export function switchTab(data,el,x){
  const root=el.closest('.career-job.ok');if(!root||!data.tab)return;
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

/** Keeps the sticky bar above the sheet's own sticky footer (call from tick). */
export function keepBarAboveFooter(root){
  const foot=root.closest('dialog')?.querySelector('.sheet-foot');
  const h=foot&&getComputedStyle(foot).position==='sticky'?foot.offsetHeight:0;
  if(root.dataset.okFoot!==String(h)){root.dataset.okFoot=String(h);root.style.setProperty('--ok-foot',h+'px');}
}

/** A folded section (native details; the summary is HTML). */
export function fold(summary,body,open=false,cls='',key=''){
  return `<details class="ok-fold${cls?' '+cls:''}"${open?' open':''}><summary${key?` data-action="car:fold" data-fold="${key}"`:''}>${summary}</summary><div class="ok-fold-body">${body}</div></details>`;
}
/** Remembers a care fold the player opened or closed (read after the native toggle has happened). */
export function foldToggle(data,el,x){const d=el.closest('details');if(d&&data.fold)setTimeout(()=>{(x.ui.okFold??={})[data.fold]=d.open;},0);}
const kept=(x,key,open)=>x.ui.okFold?.[key]??open;

/** Between dossiers: the strip, a recap, the inbox and today's rules. */
export function idleDesk(x,{cls,strip,recap='',tasks=[],other=[],rules='',plan='',people='',track=''}){
  return `<div class="career-job ok ok-idle ${cls}">${strip}${recap}<section class="ok-pane ok-pane-inbox">${inboxPane(x,{tasks,other,plan,people,track})}</section>${rules?`<section class="ok-pane ok-pane-rules">${rules}</section>`:''}</div>`;
}
