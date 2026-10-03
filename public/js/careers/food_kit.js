/** Shared pieces for the three shop workbenches (restaurant, café-bakery,
 * florist): the "today" strip, the guest queue, the surprise card, a quick
 * result line, the sticky action bar and the end-of-day grade card.
 * Everything here only renders server state and sends commands. */
import {planBox,dayFold} from './tomorrow_kit.js';

const DONE=['completed','cancelled','referred'];
export const openTasks=x=>(x.room.tasks||[]).filter(t=>!DONE.includes(t.status));

/** Luck of the day + served count + streak, as one row of chips: "☀️ Hôm nay: Ngày thường ▸ · ✅ 3 · 🔥 2".
 * The day's hint is one tap away (the chip is a fold; data-auto, so a re-render shuts it again). */
export function dayStrip(x,day,compact=false){
  if(!day?.mod)return '';
  const m=day.mod,streak=x.room.life?.streak||0;
  const hint=!compact&&m.hint?`<small class="fk-day-hint">${x.esc(m.hint)}</small>`:'';
  const chip=`<span aria-hidden="true">${x.esc(m.emoji)}</span><b>Hôm nay: ${x.esc(m.label)}</b>`;
  return `<div class="fk-day chip" role="group" aria-label="Hôm nay">
    ${hint?`<details class="fk-mod" data-auto><summary>${chip}</summary>${hint}</details>`:`<p class="fk-mod">${chip}</p>`}
    <p class="fk-stats"><span title="Đã phục vụ">✅ ${Number(day.served)||0}</span>${streak?`<span class="fk-streak" title="Làm đúng liên tiếp">🔥 ${streak}</span>`:''}${day.walkins?`<span title="Khách vãng lai">🚶 ${day.walkins}</span>`:''}</p>
  </div>`;
}

/** Latest result in one line (screen readers hear it; new ones pop). A new result shows whole; after the next
 * render it keeps to one line, and a tap (focus) shows it whole again. */
export function flash(x,day){
  const f=day?.flash;
  if(!f?.text||(f.kind==='event'&&day.open_event))return '<p class="fk-flash" aria-live="polite"></p>';
  const fresh=x.ui.fkFlash!==f.n;x.ui.fkFlash=f.n;
  return `<p class="fk-flash ${x.esc(f.kind)}${fresh?' new':''}" aria-live="polite" tabindex="0" title="${x.esc(f.text)}">${x.esc(f.text)}</p>`;
}

export function patience(p){
  const v=Math.max(0,Math.min(100,Number(p)||0));
  return `<div class="fk-patience ${v<50?'low':v<75?'mid':''}" role="meter" aria-label="Kiên nhẫn" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${v}"><i style="width:${v}%"></i><small>${v}%</small></div>`;
}

/** Guest chips: tap to switch order; "+" lets one more guest in. */
export function queue(x,active){
  const tasks=openTasks(x);
  const chips=tasks.map(t=>{
    const who=x.npc(t.npc),g=t.guest||{},on=!!active&&t.id===active.id,p=t.patience??100;
    const badge=t.vip==='critic'?'📝':(g.emoji||'🙂');
    const label=`${who.display_name} · ${t.vip==='critic'?'Người viết review':g.label||'Khách'} · kiên nhẫn ${p}%`;
    return `<button type="button" class="fk-guest${on?' on':''}${p<50?' low':''}" data-command="task_select" data-payload="${x.esc(JSON.stringify({task:t.id}))}" aria-label="${x.esc(label)}"${on?' aria-current="true"':''}>
      ${x.portrait(who,34)}<em aria-hidden="true">${badge}</em><i class="fk-pat" aria-hidden="true"><b style="width:${Math.max(0,Math.min(100,p))}%"></b></i><small class="fk-name" aria-hidden="true">${x.esc(who.display_name)}</small></button>`;
  }).join('');
  // While learning the place (first two jobs), no extra guests: one clear order at a time.
  const learning=(x.room.metrics?.served||0)<2;
  const more=x.room.open&&!x.room.more_gate&&!learning&&tasks.length>0&&tasks.length<4?`<button type="button" class="fk-guest fk-more" data-command="more_work" data-payload="{}" aria-label="Đón thêm một khách"><span aria-hidden="true">＋</span><small>Đón khách</small></button>`:'';
  if(!chips&&!more)return '';
  return `<nav class="fk-queue" aria-label="Hàng chờ">${chips}${more}</nav>`;
}

/** The open surprise with its choices (server checks every choice again). */
export function eventCard(x,day,op){
  const e=day?.open_event;if(!e)return '';
  return `<section class="fk-event" aria-labelledby="fk-ev-title">
    <div class="fk-ev-head"><span class="fk-ev-emoji" aria-hidden="true">${x.esc(e.emoji)}</span><div><small>Chuyện bất ngờ · cần bạn quyết</small><h3 id="fk-ev-title">${x.esc(e.title)}</h3></div></div>
    <p>${x.esc(e.text)}</p>
    <div class="fk-ev-choices">${(e.choices||[]).map(c=>`<button type="button" class="fk-choice" data-command="${x.esc(op)}" data-payload="${x.esc(JSON.stringify({event:e.id,choice:c.id}))}"${c.blocked?' disabled':''}><b>${x.esc(c.label)}</b>${c.blocked||c.hint?`<small>${x.esc(c.blocked||c.hint)}</small>`:''}</button>`).join('')}</div>
  </section>`;
}

/** Today's surprises that are already handled (small, for the idle panel). */
export function eventLog(x,day){
  const rows=(day?.events||[]).filter(e=>e.status!=='open');
  if(!rows.length)return '';
  return `<ul class="fk-evlog" aria-label="Chuyện trong ngày">${rows.map(e=>`<li class="${e.good?'good':e.good===false?'bad':''}"><span aria-hidden="true">${x.esc(e.emoji)}</span><span><b>${x.esc(e.title)}</b>${e.note?`<small>${x.esc(e.note)}</small>`:''}</span></li>`).join('')}</ul>`;
}

/** Sticky bottom bar on phones: what's next + the one primary action. */
export function actionBar(next,buttons){
  const cap=String(next).replace(/^\s*(\S)/,(m,c)=>m.replace(c,c.toUpperCase()));
  return `<div class="fk-bar"><p class="fk-next" aria-live="polite">${cap}</p><div class="fk-bar-btns">${buttons}</div></div>`;
}

/** Keeps the sticky bar above the sheet's own footer (called from tick). The footer's height comes from a
 * ResizeObserver (read after layout, for free) instead of offsetHeight on every tick, which forced a full
 * layout each time the DOM had just changed (~15% of a busy session's main thread on a slow phone). */
export function keepBarAboveFooter(root){
  const foot=root.closest('dialog')?.querySelector('.sheet-foot');
  // No footer (work sheets have none now): the bar sits on the sheet's bottom edge, above the phone's home bar.
  if(!foot){setFoot(root,null);return;}
  if(footWatch.el!==foot)watchFoot(foot);
  footWatch.root=root;
  if(footWatch.h!==null)setFoot(root,footWatch.h);
}
const footWatch={el:null,root:null,h:null,ro:null};
function setFoot(root,h){const v=h===null?'env(safe-area-inset-bottom, 0px)':h+'px';if(root.dataset.fkFoot!==v){root.dataset.fkFoot=v;root.style.setProperty('--fk-foot',v);}}
function watchFoot(foot){
  const W=footWatch,measure=()=>getComputedStyle(foot).position==='sticky'?foot.offsetHeight:0;
  W.ro?.disconnect();W.el=foot;W.h=null;
  if(typeof ResizeObserver!=='function'){W.h=measure();return;}
  // The callback runs right after layout: reading the height there costs nothing.
  W.ro=new ResizeObserver(()=>{if(W.el!==foot)return;W.h=measure();if(W.root?.isConnected)setFoot(W.root,W.h);});
  W.ro.observe(foot);
}

export function lockTag(level){return `<span class="fk-lock" aria-label="Mở ở cấp ${level}">🔒 cấp ${level}</span>`;}

/** Between orders: the day, the surprise, the queue and one clear action.
 * `guests` draws the waiting guests (default: the chip queue); `cls` adds the
 * career's own root class so its styles apply. */
export function idlePanel(x,day,op,extra='',guests=null,cls=''){
  const open=openTasks(x);
  return `<div class="career-job food fk-idle${cls?' '+x.esc(cls):''}">${dayStrip(x,day)}${flash(x,day)}${eventCard(x,day,op)}${guests?guests(x):queue(x,null)}${extra}
    ${!day?.open_event&&x.room.open&&!open.length?`<p class="fk-empty">Quầy đang trống. ${x.room.more_gate?x.button('🚪 Khép ca · xem tổng kết','end',{},'primary'):x.cmd('＋ Đón khách mới','more_work',{},'primary')}</p>`:''}
    ${eventLog(x,day)}</div>`;
}

/** End-of-day card (module.summary). `tomorrow:false`: tomorrow's line is in the plan above it (shopSummary). */
export function gradeCard(data,x,{tomorrow=true}={}){
  if(!data||typeof data!=='object')return '';
  const g=data.grade,tm=data.tomorrow;
  const evs=(data.events||[]).map(e=>`<li class="${e.good?'good':e.good===false?'bad':''}">${e.good?'✓':e.good===false?'✗':'•'} ${x.esc(e.note||'')}</li>`).join('');
  const rows=[['Đã phục vụ',data.served],['Làm đúng hết',data.perfect],['Khách vãng lai',data.walkins],['Bán lẻ',data.sales],['Lỡ bán',data.missed],['Tiền thưởng thêm',data.tips?data.tips+' xu':0]]
    .filter(([,v])=>v).map(([k,v])=>`<div class="kv-row"><span>${x.esc(k)}</span><b>${x.esc(String(v))}</b></div>`).join('');
  return `<article class="card space-top fk-grade">
    <div class="fk-grade-head">${g?`<span class="fk-letter g-${x.esc(g.letter)}" aria-label="Hạng ${x.esc(g.letter)}">${x.esc(g.letter)}</span><div><h4>Hạng ngày: ${x.esc(g.letter)} · ${g.score}/100</h4><small>Đúng món ${g.acc}% · nhanh ${g.speed}% · xử lý chuyện ${g.events}%${g.waste?` · hao hụt ${g.waste} xu`:''}</small></div>`:'<div><h4>Hôm nay chưa phục vụ khách nào</h4></div>'}</div>
    ${data.today?`<p class="small">${x.esc(data.today.emoji)} ${x.esc(data.today.label)}</p>`:''}
    ${rows?`<div class="kv">${rows}</div>`:''}
    ${evs?`<ul class="fk-evsum">${evs}</ul>`:''}
    ${(data.lines||[]).map(l=>`<p class="small">🎁 ${x.esc(l)}</p>`).join('')}
    ${tm&&tomorrow?`<p class="fk-tomorrow"><span aria-hidden="true">${x.esc(tm.emoji)}</span> <b>Ngày mai: ${x.esc(tm.label)}</b><small>${x.esc(tm.hint)}</small></p>`:''}
  </article>`;
}

/** The shop's part of the day summary: "🌅 Ngày mai" first (tomorrow's luck, the career's own `lines`, the stock
 * room, one button to Kho), then the grade and the career's `extra` cards folded into one line. */
export function shopSummary(data,x,{lines=[],extra='',emoji='🧾'}={}){
  if(!data||typeof data!=='object')return '';
  const g=data.grade,n=Number(data.served)||0;
  const title=`${emoji} Hôm nay${g?` · hạng ${x.esc(g.letter)}`:''} · ${n} khách`;
  return `<article class="card space-top fk-sum">${planBox(x,{mood:data.tomorrow,lines})}${dayFold(title,gradeCard(data,x,{tomorrow:false})+extra)}</article>`;
}
