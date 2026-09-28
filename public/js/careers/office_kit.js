/** Shared "office desktop" for the three office careers (corp_accounting,
 * tax_payroll, group_accounting): a status strip (clock, deadline, the boss's
 * trust), folder tabs (📥 Hộp thư · 📂 Hồ sơ · 📋 Quy định · 📒 Sổ sách), an
 * email-like inbox and a sticky bottom bar with the next step and the main
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
  if(o.locked)alert=`<p class="ok-alert bad">🔒 20:00 — văn phòng khóa cửa. Khép ngày, mai làm tiếp; việc dở được giữ nguyên.</p>`;
  else if(o.closed)alert=`<div class="ok-alert warn"><span>🌇 17:30 — hết giờ hành chính.</span>${x.confirmCmd(`🌙 Ở lại tăng ca (+${pay} xu)`,op,{},ask,'small')}</div>`;
  else if(o.can_overtime)alert=`<div class="ok-alert"><span>Sắp hết giờ. Còn việc dở?</span>${x.confirmCmd(`🌙 Đăng ký tăng ca (+${pay} xu)`,op,{},ask,'ghost small')}</div>`;
  const lvl=trust<35?'low':trust>=75?'high':'';
  return `<div class="ok-top"><header class="ok-strip" aria-label="Giờ làm việc hôm nay">
    <span class="ok-clock"><b>🕗 ${x.esc(o.time)}</b><small>${o.overtime?'tăng ca tới 20:00':o.lunch?'nghỉ trưa 12:00':'tan sở 17:30'}</small></span>
    <span class="ok-trust"><small>👩‍💼 ${x.esc(boss)}: <b>${x.esc(o.trust_label||'')}</b></small><span class="ok-meter ${lvl}" role="meter" aria-label="${x.esc(boss)} tin bạn" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${trust}"><i style="width:${trust}%"></i></span></span>
    ${due?`<span class="ok-due ${due.overdue?'bad':due.soon?'warn':''}">⏰ ${x.esc(dueText(due))}</span>`:''}
    ${mod&&mod.id!=='normal'?`<span class="ok-modchip">${x.esc(mod.emoji)} ${x.esc(mod.name)}</span>`:''}
  </header>${alert}</div>`;
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
  const KIND={fine:['💸','Phòng tài vụ','bad'],late:['⏰','Nhắc hạn','warn']};
  for(const n of [...(o.notes||[])].reverse()){
    if(n.day!==x.room.day||!KIND[n.kind])continue;
    const [e,from,tone]=KIND[n.kind];
    out.push({avatar:emoji(e),from,tone,subject:x.esc(n.text)});
  }
  return out;
}

/** The inbox pane: dossiers, then other messages, then "take more work". */
export function inboxPane(x,{tasks=[],other=[],title='Hộp thư đến'}){
  const open=openTasks(x),more=x.room.open&&open.length<4?`<p class="ok-more">${x.cmd('＋ Nhận thêm việc','more_work',{},'ghost')}</p>`:'';
  return `<h3 class="ok-h">📥 ${x.esc(title)} <small>${tasks.length+other.length} thư</small></h3>
    ${tasks.length?`<ul class="ok-mails" aria-label="Việc được giao">${tasks.map(mail).join('')}</ul>`:''}
    ${other.length?`<h4 class="ok-h2">Tin nhắn trong ngày</h4><ul class="ok-mails" aria-label="Tin nhắn">${other.map(mail).join('')}</ul>`:''}
    ${more}`;
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
export function bar(x,t,next,main='',always=false){
  const cap=String(next).replace(/^\s*(\S)/,(m,c)=>m.replace(c,c.toUpperCase()));
  return `<div class="ok-bar${always?' always':''}${main?'':' bare'}"><p class="ok-next" aria-live="polite">${cap}</p>
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
export function fold(summary,body,open=false,cls=''){
  return `<details class="ok-fold${cls?' '+cls:''}"${open?' open':''}><summary>${summary}</summary><div class="ok-fold-body">${body}</div></details>`;
}

/** Between dossiers: the strip, a recap, the inbox and today's rules. */
export function idleDesk(x,{cls,strip,recap='',tasks=[],other=[],rules=''}){
  return `<div class="career-job ok ok-idle ${cls}">${strip}${recap}<section class="ok-pane ok-pane-inbox">${inboxPane(x,{tasks,other})}</section>${rules?`<section class="ok-pane ok-pane-rules">${rules}</section>`:''}</div>`;
}
