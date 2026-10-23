/** 🛒 The selling counter shared by 🍱 Căn tin trường học (canteen.js) and ✏️ Tiệm văn phòng phẩm (stationery.js): the
 * whole shop on one screen, like a selling game (owner 22/10: "UI như kiểu của trà sữa, show hết ra người ta chọn").
 * The customer's bubble (or "Đang chờ khách…"), every shelf in a grid with its stock, the tray (khay / giỏ) with − / +
 * per line and the running bill, Giao, the counter log, the queue and the reviews. Every tap is a server command
 * (game/careers/counterkit.py grades the hand-over); the page only shows what is on the shelf minus what is already in
 * the tray. Layout lives in public/css/careers/counter_kit.css (on street_kit.css for the intro and surprise cards). */
import {data,cc,speaker,introCard,deskCard,kitActions,notesPage,stockOf,DONE} from './street_kit.js';

const TRAY_MAX=60;   // counterkit.TRAY_MAX
const pay=(x,o)=>x.esc(JSON.stringify(o));
const btnCmd=(x,cls,command,payload,inner,{disabled=false,label='',attrs=''}={})=>
  `<button type="button" class="${cls}" data-command="${command}" data-payload="${pay(x,payload)}"${label?` aria-label="${x.esc(label)}"`:''}${attrs}${disabled?' disabled':''}>${inner}</button>`;
const openTasks=x=>(x.room.tasks||[]).filter(t=>!DONE.includes(t.status));
const goods=x=>{const m={};for(const s of cc(x).shelves||[])for(const i of s.items||[])m[i.id]=i;return m;};

/** What the tray takes off the shelves (a service takes its material): counterkit.materials. */
function used(g,tray){
  const out={};
  for(const [k,q] of Object.entries(tray||{})){const i=g[k];const src=i?.service?i.uses:k;if(src)out[src]=(out[src]||0)+q;}
  return out;
}
/** Left on the shelf for this good (a service: its material), after what the tray already holds. */
const leftOf=(x,g,tray,i)=>{const src=i.service?i.uses:i.id;if(!src)return null;return Math.max(0,stockOf(x,src)-(used(g,tray)[src]||0));};

/* ---------------------------------------------------------------- the top: intro, surprise, the day */
const top=(x,o)=>`${introCard(x,o.prefix+'intro',o.icon)}${deskCard(x,o.prefix+'desk',o.deskWhere)}`;

function dayLine(x){
  const d=data(x),m=d.mod||{},td=d.today||{};
  const today=td.day===x.room.day&&td.jobs?`<span class="ck-today">📊 ${x.esc(td.jobs)} lượt · lời ${x.fmt(td.earned)} xu</span>`:'';
  if(!m.label&&!today)return '';
  return `<div class="ck-mod"${m.hint?` title="${x.esc(m.hint)}"`:''}><span class="ck-mod-emo" aria-hidden="true">${x.esc(m.emoji||'🌤️')}</span><div class="ck-mod-text"><b>${x.esc(m.label||'')}</b>${m.hint?`<small>${x.esc(m.hint)}</small>`:''}</div>${today}</div>`;
}

/* ---------------------------------------------------------------- the queue */
function bellOf(x,t){const b=data(x).bells;const v=b&&t.id in b?b[t.id]:t.bell_left;return v==null?null:Number(v);}
function queue(x,active,o){
  const tasks=openTasks(x);
  const chips=tasks.map(t=>{
    const who=speaker(x,t),on=!!active&&t.id===active.id,p=Math.max(0,Math.min(100,t.patience??100)),bell=bellOf(x,t);
    const label=`${who.display_name} · kiên nhẫn ${p}%${bell!=null?` · trống đánh sau ${bell} nhịp`:''}`;
    return btnCmd(x,`ck-guest${on?' on':''}${p<50?' low':''}`,'task_select',{task:t.id},
      `${x.portrait(who,34)}${bell!=null?`<em class="ck-guest-bell${bell<=5?' hurry':''}" aria-hidden="true">🥁${x.esc(bell)}</em>`:''}<i class="ck-pat" aria-hidden="true"><b style="width:${p}%"></b></i><small aria-hidden="true">${x.esc(who.display_name)}</small>`,
      {label,attrs:on?' aria-current="true"':''});
  }).join('');
  const learning=(x.room.metrics?.served||0)<2;
  const more=x.room.open&&!x.room.more_gate&&!learning&&tasks.length>0&&tasks.length<4
    ?btnCmd(x,'ck-guest ck-guest-more','more_work',{},`<span aria-hidden="true">＋</span><small>${x.esc(o.moreLabel)}</small>`,{label:o.moreLabel}):'';
  if(!chips&&!more)return '';
  return `<nav class="ck-queue" aria-label="Hàng chờ">${chips}${more}</nav>`;
}

/* ---------------------------------------------------------------- the customer's bubble */
/** What the customer says, without the "Tên:" the opening may start with. */
function sayOf(x,t){
  const name=String(speaker(x,t).display_name||'');let say=String(t.opening||'');
  return name&&say.startsWith(name+':')?say.slice(name.length+1).trim():say;
}
function chipList(x,t,o){
  const n=t.needs||{},d=data(x),tags=cc(x).tags||{},out=[];
  if(t.phase&&cc(x).phases?.[t.phase])out.push(['phase',cc(x).phases[t.phase]]);
  const bell=bellOf(x,t);
  if(bell!=null)out.push([`bell${bell<=5?' hurry':''}`,bell>0?`🥁 còn ${bell} nhịp`:'🥁 Trống sắp đánh!']);
  if(n.budget!=null)out.push(['budget',`💰 ${x.fmt(n.budget)} xu`]);
  for(const a of n.avoid||[])out.push(['avoid',`🚫 ${tags[a]||a}`]);
  if(n.trays)out.push(['trays',`🍱 ${n.trays} phần${n.cls?` · lớp ${n.cls}`:''}`]);
  if(n.grade)out.push(['grade',`🎒 Lớp ${n.grade}`]);
  if(n.cover)out.push(['cover','📔 Bọc, dán nhãn']);
  if(n.sets&&n.pages)out.push(['photo',`🖨️ ${n.sets} bộ × ${n.pages} trang`]);
  if(n.sample&&o.sample)out.push([d.sampled?'sampled':'sample',d.sampled?'🧪 Đã lưu mẫu':'🧪 Chưa lưu mẫu']);
  return out;
}
function chips(x,t,o){
  const out=chipList(x,t,o);
  return out.length?`<div class="ck-tags">${out.map(([k,s])=>`<span class="ck-tag ${k}">${x.esc(s)}</span>`).join('')}</div>`:'';
}
function bubble(x,t,o){
  if(!t){
    const more=x.room.open?(x.room.more_gate?'':x.cmd(`🔔 ${x.esc(o.callNext)}`,'more_work',{},'primary small ck-call')):`<small class="ck-closed">${x.esc(o.closedLine)}</small>`;
    return `<section class="ck-bubble ck-wait" aria-live="polite"><span class="ck-wait-emo" aria-hidden="true">${x.esc(o.icon)}</span><div class="ck-say"><p><b>Đang chờ khách…</b></p><small>${x.esc(o.waitLine)}</small></div>${more}</section>`;
  }
  const who=speaker(x,t),name=String(who.display_name||''),say=sayOf(x,t);
  const p=Math.max(0,Math.min(100,t.patience??100));
  return `<section class="ck-bubble" aria-label="${x.esc(name)}"><div class="ck-cust">${x.portrait(who,52)}<div class="ck-cust-name"><b>${x.esc(name)}</b>${who.role?`<small>${x.esc(who.role)}</small>`:''}</div></div>
    <div class="ck-say"><p>${x.esc(say)}</p>${t.known?chips(x,t,o):''}
    <div class="ck-pat-row" title="Kiên nhẫn"><i class="ck-pat${p<50?' low':''}" aria-hidden="true"><b style="width:${p}%"></b></i><small><span class="sr-only">Kiên nhẫn </span>${p}%</small></div>
    ${t.known?'':x.cmd('👂 Hỏi khách cần gì','ask',{task:t.id},'primary full ck-ask')}</div></section>`;
}

/* ---------------------------------------------------------------- the shelves */
function tileOf(x,o,t,g,i,tray,ready,big){
  const q=tray[i.id]||0,left=leftOf(x,g,tray,i),src=i.service?g[i.uses]:null,total=Object.values(tray).reduce((s,v)=>s+v,0);
  const out=left!=null&&left<=0,full=total>=TRAY_MAX,can=ready&&!out&&!full;
  // Spoken label in ' · ' pieces (each one has its English: v4/i18n.js translates segment by segment).
  const stockWord=left==null?'':src?` · ${src.name}: còn ${left}`:` · còn ${left}`;
  const label=`${i.name} · ${i.price} xu/${i.unit}${stockWord}${q?` · trong ${o.tray.toLowerCase()} ${q}`:''}${out?' · hết hàng':''}`;
  const inner=`<span class="ck-emo" aria-hidden="true">${x.esc(i.emoji)}</span><b class="ck-name">${x.esc(i.name)}</b><span class="ck-price">${x.esc(i.price)} xu</span>`+
    (left!=null?`<em class="ck-count${out?' zero':left<=3?' low':''}" aria-hidden="true">${src?`${x.esc(src.emoji)}`:''}${x.esc(left)}</em>`:'')+
    (q?`<i class="ck-inq" aria-hidden="true">×${x.esc(q)}</i>`:'');
  const tile=btnCmd(x,`ck-tile${q?' on':''}${out?' zero':''}${i.service?' svc':''}`,o.prefix+'add',{task:t?.id||'',item:i.id},inner,{disabled:!can,label});
  const n5=Math.min(5,left??5,TRAY_MAX-total);
  const plus=(i.service||(big&&q>0))&&can&&n5>1?btnCmd(x,'ck-plus5',o.prefix+'add',{task:t.id,item:i.id,qty:n5},`+${n5}`,{label:`+${n5} · ${i.name}`}):'';
  return `<div class="ck-cell">${tile}${plus}</div>`;
}
function shelves(x,t,o){
  const g=goods(x),tray=t?.tray||{},d=data(x);
  const ready=!!t&&t.known&&t.stage!=='done'&&!d.desk?.ev;
  const big=!!t?.needs&&(t.needs.lines||[]).reduce((s,l)=>s+(l.qty||0),0)>=8;
  const why=!t?'Chưa có khách: tới lượt khách rồi mới lấy hàng.':!t.known?'Hỏi khách cần gì trước, rồi chạm món để lấy.':d.desk?.ev?'Quyết chuyện ở trên trước đã.':'';
  return `<section class="ck-shelves" aria-label="Kệ hàng"><div class="ck-shelves-head"><h3>${x.esc(o.shelvesTitle)}</h3><button type="button" class="btn ghost small" data-action="inventory">📦 Kho</button></div>
    ${why?`<p class="ck-why">${x.esc(why)}</p>`:''}
    ${(cc(x).shelves||[]).map(s=>`<section class="ck-shelf" data-shelf="${x.esc(s.id)}"><h4>${x.esc(s.title)}</h4><div class="ck-grid">${(s.items||[]).map(i=>tileOf(x,o,t,g,i,tray,ready,big)).join('')}</div></section>`).join('')}</section>`;
}

/* ---------------------------------------------------------------- the tray */
function tray(x,t,o){
  const g=goods(x),tr=t?.tray||{},rows=Object.entries(tr),n=rows.reduce((s,[,q])=>s+q,0),work=!!t&&t.known&&t.stage!=='done';
  const bill=t?.bill??rows.reduce((s,[k,q])=>s+(g[k]?.price||0)*q,0),budget=t?.needs?.budget;
  const over=budget!=null&&bill>budget;
  const lines=rows.map(([k,q])=>{
    const i=g[k]||{id:k,name:k,emoji:'•',price:0,unit:''},left=leftOf(x,g,tr,i);
    return `<li class="ck-tline"><span class="ck-emo" aria-hidden="true">${x.esc(i.emoji)}</span><span class="ck-tname">${x.esc(i.name)}<small>${x.esc(i.price)} xu × ${x.esc(q)}</small></span>
      <span class="ck-qty">${btnCmd(x,'ck-step',o.prefix+'remove',{task:t.id,item:k},'−',{disabled:!work,label:`−1 · ${i.name}`})}<b>${x.esc(q)}</b>${btnCmd(x,'ck-step',o.prefix+'add',{task:t.id,item:k},'+',{disabled:!work||(left!=null&&left<=0)||n>=TRAY_MAX,label:`+1 · ${i.name}`})}</span>
      <span class="ck-sub">${x.fmt((i.price||0)*q)} xu</span></li>`;
  }).join('');
  const empty=`<p class="ck-tray-empty">${x.esc(t?.known?o.trayEmpty:t?'Hỏi khách cần gì trước đã.':`${o.tray} đang trống.`)}</p>`;
  return `<section class="ck-tray" aria-label="${x.esc(o.tray)}"><div class="ck-tray-head"><h3>${x.esc(o.trayIcon)} ${x.esc(o.tray)}${n?` <small>${n} món</small>`:''}</h3>${n&&work?x.cmd(`🧹 Dọn ${o.tray.toLowerCase()}`,o.prefix+'clear',{task:t.id},'ghost small ck-clear'):''}</div>
    ${rows.length?`<ul class="ck-tlines">${lines}</ul>`:empty}
    <div class="ck-bill${over?' over':''}" role="status"><span>Tổng tiền</span><b>${x.fmt(bill)} xu</b>${budget!=null?`<small>${over?`lố ${x.fmt(bill-budget)} xu so với ${x.fmt(budget)} xu khách có`:`khách có ${x.fmt(budget)} xu`}</small>`:''}</div></section>`;
}

/** The counter log: the last words at the counter (what is missing, what the customer said). */
function log(x,t){
  const l=(t?.lines||[]).slice(-3);if(!l.length)return '';
  return `<ul class="ck-log" aria-live="polite">${l.map((s,i)=>`<li${i===l.length-1?' class="last"':''}>${x.esc(s)}</li>`).join('')}</ul>`;
}

/** The sticky bar: the bill, 🧪 Lưu mẫu for a lunch order (canteen), Giao. */
function bar(x,t,o){
  if(!t)return '';
  const d=data(x),n=Object.values(t.tray||{}).reduce((s,q)=>s+q,0),work=t.known&&t.stage!=='done';
  const sample=o.sample&&(t.phase==='trua'||t.needs?.sample)
    ?(d.sampled?'<button type="button" class="btn ghost ck-sample done" disabled>✓ Đã lưu mẫu</button>':x.cmd('🧪 Lưu mẫu',o.prefix+'sample',{},'cream ck-sample')):'';
  const label=typeof o.serve==='function'?o.serve(t):o.serve;
  return `<div class="ck-bar"><div class="ck-bar-bill"><small>${n} món</small><b>${x.fmt(t.bill??0)} xu</b></div>${sample}${x.cmd(`✅ ${x.esc(label)}`,o.prefix+'serve',{task:t.id},'primary ck-serve',!work||!n||!!d.desk?.ev)}</div>`;
}

/* ---------------------------------------------------------------- reviews, notes */
function reviews(x){
  const posts=(x.room.feed||[]).filter(p=>p&&p.stars),avg=x.room.rating;
  const list=posts.slice(0,3).map(p=>`<article class="ck-rev-item"><div class="ck-rev-top"><b>${x.esc(p.author||'Khách')}</b><span class="ck-stars" aria-label="${x.esc(p.stars)} sao">${'★'.repeat(p.stars)}${'☆'.repeat(Math.max(0,5-p.stars))}</span></div><p>${x.esc(p.text||'')}</p>${p.day!=null?`<small>Ngày ${x.esc(p.day)}</small>`:''}</article>`).join('');
  return `<section class="ck-rev" aria-label="Đánh giá"><div class="ck-rev-head"><h3>⭐ Đánh giá</h3><span class="ck-rate"><b>${x.esc(avg||'—')}</b><small>${posts.length} lượt</small></span></div>
    ${list||'<p class="ck-why">Chưa có đánh giá nào. Bán đúng, giao kịp là có lời khen.</p>'}${posts.length?x.button('Đọc & trả lời đánh giá','feedback',{},'ghost small'):''}</section>`;
}
const rulesList=x=>`<ol class="ck-rules">${(cc(x).rules||[]).map(r=>`<li>${x.esc(r)}</li>`).join('')}</ol>`;
/** The price board: every good with its list price (the notes page). */
const priceBoard=x=>(cc(x).shelves||[]).map(s=>`<h4 class="ck-board-h">${x.esc(s.title)}</h4><ul class="ck-board">${(s.items||[]).map(i=>`<li><span aria-hidden="true">${x.esc(i.emoji)}</span><span class="ck-board-name">${x.esc(i.name)}</span><b>${x.esc(i.price)} xu/${x.esc(i.unit)}</b></li>`).join('')}</ul>`).join('');
const notebook=(x,o)=>`<details class="ck-notes"><summary>📒 ${x.esc(o.notesTitle)}</summary>${rulesList(x)}</details>`;

/* ---------------------------------------------------------------- the station */
function station(x,t,o){
  return `${dayLine(x)}${queue(x,t,o)}<div class="ck-main"><div class="ck-side">${bubble(x,t,o)}${tray(x,t,o)}${log(x,t)}</div>${shelves(x,t,o)}</div>${bar(x,t,o)}${reviews(x)}${notebook(x,o)}`;
}

/* ---------------------------------------------------------------- screen readers (player #497, blind, 23/10)
 * Vào việc, Hỏi khách and Giao take their own button off the page (or turn it off): the focus fell to <body>, a
 * screen reader went quiet and lost its place, and the next customer came in without a word. tick() says what
 * changed in a hidden live line (data-morph-static: renders leave its words alone) and puts the focus back on the
 * next step. Nothing changes on screen. */
const LIVE='<p class="sr-only ck-live" aria-live="polite" aria-atomic="true" data-morph-static></p>';
const NEXT=['.sk-event .sk-opt:not([disabled])','.ck-ask','.ck-call','.ck-tile:not([disabled])','.ck-serve:not([disabled])','.ck-guest','button:not([disabled])'];
/** The words for what changed since the last tick ('' = nothing new): the last customer's outcome, a new customer,
 * what they asked for, what is wrong with the tray, a surprise at the counter. */
function news(x,o,root,s){
  const tasks=x.room.tasks||[],tid=root.dataset.ckTask||'',t=tasks.find(k=>k.id===tid),ev=data(x).desk?.ev,intro=!!root.querySelector('.sk-intro');
  const key=intro?'intro':`${tid}|${t?.known?1:0}|${(t?.lines||[]).length}|${ev?.title||''}`;
  if(key===s.key)return '';
  const was={...s};Object.assign(s,{key,tid,known:!!t?.known,lines:(t?.lines||[]).length,ev:ev?.title||'',at:1});
  if(!was.at||intro)return '';   // the first look (the reader reads the screen itself) or the intro card
  const out=[],who=k=>String(speaker(x,k).display_name||'');
  if(was.tid&&was.tid!==tid){const p=tasks.find(k=>k.id===was.tid);const l=p&&DONE.includes(p.status)&&(p.lines||[]).at(-1);if(l)out.push(l);}
  if(ev&&ev.title!==was.ev)out.push(`${ev.title}. ${ev.text||''}`);
  if(!t)out.push(x.room.open?`Đang chờ khách. ${o.waitLine}`:o.closedLine);
  else if(t.id!==was.tid||was.key==='intro')out.push(`${who(t)}: ${sayOf(x,t)}`);
  else if(t.known&&!was.known)out.push(`${who(t)}: ${sayOf(x,t)}`,...chipList(x,t,o).map(([,c])=>c));
  else if((t.lines||[]).length>was.lines)out.push(t.lines.at(-1));
  return out.filter(Boolean).join(' · ');
}
function tick(root,x,o){
  const s=x.ui.ckSr??={},live=root.querySelector('.ck-live'),said=news(x,o,root,s);
  if(said&&live){live.textContent='';clearTimeout(s.t);s.t=setTimeout(()=>{if(live.isConnected)live.textContent=said;},150);}   // after the focus move, so it is not cut off
  const a=document.activeElement,lost=!a||a===document.body||!a.isConnected||a.disabled&&root.contains(a);
  if(!lost){s.had=root.contains(a);return;}
  if(!s.had)return;
  s.had=false;
  for(const q of NEXT){
    const el=[...root.querySelectorAll(q)].find(e=>e.offsetParent!==null);if(!el)continue;
    el.focus({preventScroll:true});s.had=document.activeElement===el;
    // A keyboard player sees it (after the render puts the sheet's scroll back); a tap scrolls nothing.
    requestAnimationFrame(()=>{if(document.activeElement===el&&el.matches(':focus-visible'))el.scrollIntoView({block:'nearest'});});
    return;
  }
}

/** The career module for a counter shop. `o`: id, prefix (ct_ / vp_), icon, the tray's name (Khay / Giỏ) and its
 * icon, the serve label (or a function of the task), the waiting lines, the notes and the dock. */
export function counterKit(o){
  o={deskWhere:'Chuyện ở quầy',shelvesTitle:'🛒 Quầy hàng',moreLabel:'Đón khách',callNext:'Mời khách tiếp theo',
    closedLine:'Quầy chưa mở: bắt đầu ngày để đón khách.',waitLine:'Khách tới là thấy ngay ở đây.',
    trayEmpty:'Chạm món trên kệ để lấy cho khách.',sample:false,...o};
  const wrap=(x,body,t)=>`<div class="career-job sk ck-counter ${o.id}" data-ck-task="${x.esc(t?.id||'')}">${LIVE}${body}</div>`;
  return {
    id:o.id,css:true,autoNext:true,
    next(t,x){
      if(!t.known)return x.esc('Hỏi khách cần gì');
      if(o.sample&&t.phase==='trua'&&!data(x).sampled)return x.esc('Lưu mẫu thức ăn trưa');
      return x.esc(Object.keys(t.tray||{}).length?(typeof o.serve==='function'?o.serve(t):o.serve):'Chạm món trên kệ');
    },
    job(t,x){
      if(!data(x).intro||x.ui.intro)return wrap(x,introCard(x,o.prefix+'intro',o.icon),t);
      return wrap(x,top(x,o)+station(x,t,o),t);
    },
    idle(x){return wrap(x,top(x,o)+station(x,null,o));},
    tick(root,x){tick(root,x,o);},
    page(view,x){return view==='car:notes'?notesPage(x,{cls:`ck-counter ${o.id}`,eyebrow:o.place,title:x.esc(o.notesTitle),body:rulesList(x)+priceBoard(x)}):'';},
    actions:{...kitActions},
    dock:o.dock,
  };
}
