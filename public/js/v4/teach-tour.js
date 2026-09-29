/** Teacher "Tiết học" and tour guide "Chuyến đi" (v2 layer of the legacy
 * careers). The server keeps every rule; this module only renders the
 * projection in t.room / t.trip. Phone first.
 *
 * Teacher: the day's timetable, the chalkboard (what the class is doing now),
 * a seating chart where every pupil shows their state, then the one thing to
 * do at this step. Tour guide: the route map with numbered stops, the group
 * roster with who needs care, then the stop. Both keep a sticky bar at the
 * bottom with the next step and the main button, always in reach. */
import {escapeHTML as esc,portrait} from '../icons.js';
import {t as tr,language} from './i18n.js';
import {keepBarAboveFooter} from '../careers/food_kit.js';

if(typeof document!=='undefined'){
  if(!document.querySelector('link[data-teach-css]')){
    const l=document.createElement('link');l.rel='stylesheet';l.href='/css/teach.css';l.dataset.teachCss='1';document.head.append(l);
  }
  // The sticky bar sits above the sheet's own sticky footer; measure it after every render.
  const fit=()=>{
    const r=document.querySelector('dialog[open] .tt');if(!r)return;
    keepBarAboveFooter(r);
    // Keep the current period in view in the timetable strip.
    const on=r.querySelector('.tt-period.on'),wrap=on?.closest('.tt-periods-wrap');
    if(wrap&&wrap.scrollWidth>wrap.clientWidth){const a=on.getBoundingClientRect(),b=wrap.getBoundingClientRect();if(a.left<b.left||a.right>b.right)wrap.scrollLeft+=a.left-b.left-(b.width-a.width)/2;}
  };
  const host=document.getElementById('sheetContent');
  if(host&&typeof MutationObserver!=='undefined')new MutationObserver(fit).observe(host,{childList:true});
  addEventListener('resize',fit);addEventListener('layoutchange',fit);
}

/** Replace {Title}/{title} with the player's teacher title (Cô/Thầy). The
 * Vietnamese text is translated first so the English pack still matches. */
export function titled(v,state){
  const g=state?.journey?.gender,en=language()==='en';
  const one=s=>{
    if(typeof s!=='string'||!s.includes('{'))return s;
    const x=tr(s),done=x!==s&&en;
    return x.replaceAll('{Title}',done?'Teacher':g==='male'?'Thầy':'Cô').replaceAll('{title}',done?'teacher':g==='male'?'thầy':'cô');
  };
  const walk=x=>typeof x==='string'?one(x):Array.isArray(x)?x.map(walk):x&&typeof x==='object'?Object.fromEntries(Object.entries(x).map(([k,y])=>[k,walk(y)])):x;
  return walk(v);
}

const act=(label,op,payload,cls='',o={})=>`<button type="button" class="btn ${cls}" data-action="expDo" data-op="${op}" data-payload="${esc(JSON.stringify(payload))}"${o.confirm?` data-confirm="${esc(o.confirm)}"`:''}${o.disabled?' disabled':''}${o.aria?` aria-label="${esc(o.aria)}"`:''}>${label}</button>`;
const local=(label,action,data,cls,disabled=false,aria='',pressed=null)=>`<button type="button" class="${cls}" data-action="${action}" ${Object.entries(data).map(([k,v])=>`data-${k}="${esc(v)}"`).join(' ')}${disabled?' disabled':''}${aria?` aria-label="${esc(aria)}"`:''}${pressed===null?'':` aria-pressed="${pressed}"`}>${label}</button>`;
const em=s=>`<span aria-hidden="true">${s}</span>`;
const signed=n=>n>0?'+'+n:String(n);
const ENDED=['completed','cancelled','referred'];

function meter(label,value){
  const v=Math.max(0,Math.min(100,value??100)),tone=v>=80?'good':v>=55?'warn':'bad';
  return `<div class="tt-meter ${tone}" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${v}" aria-label="${esc(label)}"><span>${esc(label)}</span><i><b style="width:${v}%"></b></i><strong>${v}%</strong></div>`;
}
function hud(label,value,t,person){
  return `<div class="tt-hud">${meter(label,value)}<button type="button" class="tt-who" data-action="chat" data-npc="${esc(t.npc)}" data-task="${esc(t.id)}" aria-label="Trò chuyện với ${esc(person?.display_name||'')}">${portrait(person||{display_name:'?'},30)}<span aria-hidden="true">💬</span></button></div>`;
}
/** Sticky bottom bar: what to do next + the main button(s). `top` adds a row above (route totals). */
function bar(next,buttons='',top=''){
  return `<div class="tt-bar">${top}<div class="tt-bar-row"><p class="tt-next" aria-live="polite">${next}</p>${buttons?`<div class="tt-bar-btns">${buttons}</div>`:''}</div></div>`;
}
function section(icon,title,body,aside='',cls=''){
  return `<section class="tt-sec ${cls}"><div class="tt-sec-head"><h3>${em(icon)} ${title}</h3>${aside?`<small>${aside}</small>`:''}</div>${body}</section>`;
}
function eventCard(ev,op,task){
  if(ev.chosen){
    const mood=ev.mood??ev.focus??0;
    return `<article class="tt-event done ${ev.mistake?'oops':''}"><header>${em(ev.emoji)}<b>${esc(ev.title)}</b></header><p class="tt-outcome">${esc(ev.outcome)}</p><div class="tt-chips">${mood?`<span class="tag ${mood>0?'green':'amber'}">${mood>0?'😊':'😕'} ${signed(mood)}</span>`:''}${(ev.trust||[]).map(x=>`<span class="tag ${x.delta>0?'green':'amber'}">${x.delta>0?'💛':'💔'} ${esc(x.name)} ${signed(x.delta)}</span>`).join('')}${ev.minutes?`<span class="tag">⏱ +${ev.minutes}′</span>`:''}${ev.mistake?'<span class="tag danger">Chưa ổn</span>':''}</div></article>`;
  }
  return `<article class="tt-event" aria-live="polite"><header>${em(ev.emoji)}<div><small>Cần bạn quyết</small><b>${esc(ev.title)}</b></div></header><p>${esc(ev.text)}</p><div class="tt-options">${ev.options.map(o=>act(`<span>${esc(o.label)}</span>${o.cost?`<small>−${o.cost} xu quỹ đoàn</small>`:''}`,op,{task,event:ev.id,option:o.id},'tt-option')).join('')}</div></article>`;
}
function logList(log){
  return log.length?`<ul class="tt-log">${log.map(e=>`<li>${em(e.emoji)} <span>${esc(e.title)}</span> ${e.mistake?'<b class="bad-text">chưa ổn</b>':'<b class="good-text">✓</b>'}</li>`).join('')}</ul>`:'';
}

/* ------------------------------------------------------------ teacher */
const LESSON_STEPS=[['roll','Điểm danh'],['plan','Soạn bài'],['teach','Dạy'],['check','Chấm phiếu'],['ready','Khép tiết']];
const STYLE_ICON={look:'🖼️',hands:'🧩',talk:'💬',short:'⏱️'};
const STYLE_SHORT={look:'Nhìn hình',hands:'Làm thử',talk:'Nghe kể',short:'Từng bước'};
const STYLE_LONG={look:'Học bằng mắt',hands:'Học bằng tay',talk:'Học bằng lời',short:'Từng bước ngắn'};
const ROLE={open:'Mở đầu',core:'Hoạt động chính',check:'Kiểm tra'};
const SLOT_HINT=['Mở đầu: khởi động lớp','Hoạt động chính','Kiểm tra cuối tiết'];
const ENERGY={calm:['🧘','Nhẹ nhàng'],move:['🏃','Vận động'],game:['🎲','Trò chơi']};
const ROLL_WAIT={here:['','🪑 Đang ngồi'],sick:['warn','📩 Xin nghỉ ốm'],late:['warn','🏃 Đến muộn'],missing:['bad','❔ Ghế trống']};
const ROLL_DONE={'here:present':['good','✓ Có mặt'],'sick:excused':['dim','📩 Vắng có phép'],'sick:present':['good','✓ Có mặt'],'late:let_in':['good','✓ Đã vào chỗ'],'late:front':['good','✓ Đã vào chỗ'],'late:outside':['warn','🚪 Đứng ngoài'],'missing:report':['info','📞 Đã báo nhà'],'missing:mark':['dim','Ghi vắng']};
const isHere=k=>k.status==='here'||k.status==='late';

function kidStyle(c,id){return (c.classroom?.notebook||[]).find(k=>k.id===id)?.style||null;}

/** Today's periods; the current one is highlighted, the others open their own lesson. */
function timetable(t,c){
  const list=(c.tasks||[]).filter(x=>x.career==='teacher'&&(x.day===c.day||!ENDED.includes(x.status)));
  if(!list.some(x=>x.id===t.id))list.push(t);
  list.sort((a,b)=>(a.day-b.day)||String(a.id).localeCompare(String(b.id),undefined,{numeric:true}));
  const cells=list.map((x,i)=>{
    const on=x.id===t.id,done=ENDED.includes(x.status);
    const st=done?'✓ Đã dạy':on?'● Đang dạy':x.room&&x.room.stage!=='roll'?'Dạy dở':'Chưa vào';
    const inner=`<span><b>Tiết ${i+1}</b> · ${esc(x.lesson?.topic||x.title)}</span><small>${st}</small>`;
    return on||done?`<li class="tt-period ${on?'on':'done'}"${on?' aria-current="true"':''}>${inner}</li>`:`<li>${local(inner,'job',{task:x.id},'tt-period',false,`Tiết ${i+1}: ${x.title}`)}</li>`;
  }).join('');
  return `<nav class="tt-periods-wrap" aria-label="Thời khoá biểu hôm nay"><ol class="tt-periods">${cells}</ol></nav>`;
}

function board(t,R,index){
  const at=LESSON_STEPS.findIndex(x=>x[0]===R.stage);
  const card=id=>R.hand.find(h=>h.id===id);
  const plan=R.plan?.length?`<ol class="tt-flow" aria-label="Giáo án">${R.plan.map((id,i)=>{const x=card(id);if(!x)return '';const st=R.stage==='teach'?(i<R.phase?'done':i===R.phase?'now':''):'done';return `<li class="${st}"${st==='now'?' aria-current="step"':''}>${em(x.emoji)}<span>${esc(x.name)}</span><small>${st==='now'?'▶ Đang dạy · ':''}${x.minutes}′</small></li>`;}).join('')}</ol>`:'';
  return `<section class="tt-board" aria-label="Bảng lớp">
    <div class="tt-board-top"><span>Tiết ${index} · ${esc(t.lesson.topic)}</span>${R.tier>1?`<span class="tt-tier" aria-label="Độ khó ${R.tier}">${'★'.repeat(R.tier)}</span>`:''}</div>
    <p class="tt-prompt">${esc(t.lesson.prompt)}</p>${plan}
    <div class="tt-board-foot"><span>${esc(R.cond.emoji)} ${esc(R.cond.text)}</span><span class="tt-chalk" role="img" aria-label="Bước ${at+1}/5: ${esc(LESSON_STEPS[at]?.[1]||'')}">${LESSON_STEPS.map((_,i)=>`<i class="${i<at?'done':i===at?'now':''}"></i>`).join('')}<b>${at+1}/5 · ${esc(LESSON_STEPS[at]?.[1]||'')}</b></span></div>
  </section>`;
}

/** One desk per pupil. The cue changes with the step of the period. */
function seatCue(k,R,c,reach){
  if(R.stage==='roll')return k.done?(ROLL_DONE[`${k.status}:${k.done}`]||['good','✓']):ROLL_WAIT[k.status]||['',''];
  if(!isHere(k))return ['dim','Vắng'];
  if(R.stage==='plan'){const st=kidStyle(c,k.id);return st?[reach.has(st)?'good':'',`${STYLE_ICON[st]} ${STYLE_SHORT[st]}${reach.has(st)?' ✓':''}`]:['','❓ Chưa rõ'];}
  const lost=R.lost.find(x=>x.id===k.id),ticket=R.tickets.find(x=>x.kid===k.id);
  if(R.stage==='teach'){
    if(!lost)return ['','🙂 Theo kịp'];
    return lost.away?['dim','🚪 Ra ngoài']:lost.helped?['good','💡 Đã hiểu']:['warn','🙋 Cần giúp'];
  }
  if(!ticket)return ['dim','—'];
  const m=ticket.mark&&R.marks.find(x=>x.id===ticket.mark);
  return m?['good',`${m.emoji} Đã chấm`]:['warn','🎫 Chờ chấm'];
}
function seating(t,c,R,reach=new Set()){
  const here=R.kids.filter(isHere).length;
  const seats=R.kids.map(k=>{
    const [tone,cue]=seatCue(k,R,c,reach);
    const hint=R.stage==='plan'&&isHere(k)&&!kidStyle(c,k.id)?`<em>${esc(k.trait)}</em>`:'';
    return `<li class="tt-seat ${tone?'tone-'+tone:''}"><span class="tt-face" aria-hidden="true">${k.emoji}</span><b>${esc(k.name)}</b><small>${esc(cue)}</small>${hint}</li>`;
  }).join('');
  const aside=R.stage==='roll'?`${R.kids.filter(k=>k.done).length}/${R.kids.length} đã ghi`:`${here}/${R.kids.length} có mặt`;
  return section('🪑','Sơ đồ lớp',`<div class="tt-room${R.stage==='plan'?' wide':''}"><p class="tt-front" aria-hidden="true">Bục giảng</p><ul class="tt-seats" aria-label="Chỗ ngồi của các bạn">${seats}</ul></div>`,aside,'tt-class');
}

function rollStage(t,c,R){
  const odd=R.kids.filter(k=>k.status!=='here'),todo=R.kids.filter(k=>k.status==='here'&&!k.done),left=odd.filter(k=>!k.done);
  const card=k=>`<article class="tt-kid st-${k.status}"><div class="tt-kid-top"><span class="tt-face" aria-hidden="true">${k.emoji}</span><div><b>${esc(k.name)}</b><small>${k.mark_emoji} ${esc(k.clue)}</small></div></div><div class="tt-options">${k.options.map(o=>act(esc(o.label),'lesson_roll',{task:t.id,kid:k.id,choice:o.id},'tt-option')).join('')}</div></article>`;
  const cases=left.length?section('📋','Sổ điểm danh',`<div class="tt-kids">${left.map(card).join('')}</div>`,`${left.length} bạn cần ghi riêng`):'';
  const next=left.length&&!todo.length?`Chọn cách ghi cho ${left.length} bạn ở trên`:todo.length?`${todo.length} bạn đang ngồi ở chỗ${left.length?` · còn ${left.length} bạn ghi riêng`:''}`:'Điểm danh xong';
  return {body:seating(t,c,R)+cases,bar:bar(esc(next),todo.length?act(`✓ Có mặt · ${todo.length} bạn`,'lesson_roll',{task:t.id,kid:'all'},'primary'):'')};
}

function planStage(t,c,R,ui){
  ui.lessonSequence??=[];const seq=ui.lessonSequence.filter(id=>R.hand.some(x=>x.id===id)).slice(0,3);
  const cards=seq.map(id=>R.hand.find(x=>x.id===id)),mins=cards.reduce((s,x)=>s+x.minutes,0);
  const reach=new Set(cards.flatMap(x=>x.styles));
  const slot=i=>{const x=cards[i];return `<li class="${x?'filled':''}"><i>${i+1}</i>${x?`<span><b>${em(x.emoji)} ${esc(x.name)}</b><small>${esc(ROLE[x.role])} · ${ENERGY[x.energy][0]} ${esc(ENERGY[x.energy][1])}</small></span><strong>${x.minutes}′</strong>`:`<span class="muted">${esc(SLOT_HINT[i])}</span>`}</li>`;};
  const hand=R.hand.map(x=>{const n=seq.indexOf(x.id);return local(`<span class="tt-card-top">${em(x.emoji)}<b>${esc(x.name)}</b></span><span class="tt-card-meta"><span>${ENERGY[x.energy][0]} ${esc(ENERGY[x.energy][1])}</span><span>⏱ ${x.minutes}′</span></span><span class="tt-card-meta"><span aria-label="${esc(x.styles.map(s=>STYLE_LONG[s]).join(', '))}">${x.styles.map(s=>STYLE_ICON[s]).join(' ')}</span><span class="tt-role r-${x.role}">${esc(ROLE[x.role])}</span></span>${n>=0?`<i class="tt-badge" aria-label="Thứ tự ${n+1}">${n+1}</i>`:''}`,'lessonStep',{step:x.id},'tt-card'+(n>=0?' picked':''),n>=0||seq.length>=3,'',n>=0);}).join('');
  const over=mins>R.limit,short=seq.length===3&&mins<R.min,core=cards.some(x=>x.role==='core'),ready=seq.length===3&&!over&&!short&&core;
  const why=over?'Quá giờ tiết học: bớt một hoạt động dài':short?`Mới ${mins} phút, cần ít nhất ${R.min}`:seq.length===3&&!core?'Thiếu hoạt động chính':seq.length<3?`Chọn thêm ${3-seq.length} hoạt động`:'Giáo án đã đủ. Chốt nhé!';
  const styles=['look','hands','talk','short'].map(s=>`<span class="tt-style ${reach.has(s)?'on':''}">${STYLE_ICON[s]} ${esc(STYLE_SHORT[s])}</span>`).join('');
  const planner=section('📝','Giáo án tiết này',`<p class="tt-tip">${esc(R.cond.emoji)} ${esc(R.cond.tip)} Tiết ${R.min}–${R.limit} phút, có một hoạt động chính, hợp cách học của các bạn và kết thúc bằng kiểm tra.</p>
    <ol class="tt-tray">${[0,1,2].map(slot).join('')}</ol>
    <div class="tt-reach" aria-label="Cách học đã có trong giáo án">${styles}</div>`,`⏱ ${mins}/${R.limit}′`,'tt-planner');
  const pick=section('🗂️','Thẻ hoạt động',`<div class="tt-hand">${hand}</div>`,'Chạm theo thứ tự');
  const next=`<b class="${over||short?'bad-text':''}">⏱ ${mins}/${R.limit}′ · ${seq.length}/3</b> · ${esc(why)}`;
  return {body:seating(t,c,R,reach)+planner+pick,bar:bar(next,local('↶ Chọn lại','lessonReset',{},'btn ghost',!seq.length)+local('Chốt giáo án →','lessonPlan',{},'btn primary',!ready))};
}

function teachStage(t,c,R){
  const events=R.events.map(ev=>eventCard(ev,'lesson_call',t.id)).join('');
  const need=R.lost.filter(k=>!k.helped&&!k.away);
  const help=k=>`<article class="tt-kid"><div class="tt-kid-top"><span class="tt-face" aria-hidden="true">${k.emoji}</span><div><b>${esc(k.name)}</b><small>${esc(k.clue)}</small></div></div><div class="tt-methods" role="group" aria-label="Cách giúp ${esc(k.name)}">${R.methods.map(m=>act(`${em(m.emoji)}<span>${esc(m.name)}</span>`,'lesson_help',{task:t.id,kid:k.id,method:m.id},'tt-method')).join('')}</div></article>`;
  const helpBox=need.length?section('🙋','Bạn cần giúp',`<div class="tt-kids">${need.map(help).join('')}</div>`,`${need.length} bạn`):'';
  const pending=R.pending.length>0,last=R.phase>=2;
  const next=pending?'Xử lý chuyện trong lớp trước':need.length?`Còn ${need.length} bạn chưa hiểu bài`:'Cả lớp đang theo kịp bài 🌟';
  return {body:(events?section('💬','Chuyện trong lớp',events):'')+seating(t,c,R)+helpBox,bar:bar(esc(next),act(last?'Thu phiếu →':`Sang hoạt động ${R.phase+2} →`,'lesson_next',{task:t.id},'primary',{disabled:pending}))};
}

function checkStage(t,c,R){
  const todo=R.tickets.filter(x=>!x.mark),done=R.tickets.length-todo.length;
  const card=x=>`<article class="tt-ticket"><div class="tt-kid-top"><span class="tt-face" aria-hidden="true">${x.emoji}</span><div><b>${esc(x.name)}</b><small>${esc(x.note)}</small></div><strong class="tt-answer" aria-label="Bài làm: ${esc(x.answer)}">${esc(x.answer)}</strong></div><div class="tt-marks">${R.marks.map(m=>act(`${em(m.emoji)} <span>${esc(m.label)}</span>`,'lesson_mark',{task:t.id,kid:x.kid,mark:m.id},'tt-option')).join('')}</div></article>`;
  const key=`<div class="tt-key"><b>Đáp án đúng</b><p>${esc(t.lesson.fact)}</p></div>`;
  return {body:section('🎫','Chấm phiếu cuối tiết',`${key}<div class="tt-tickets">${todo.map(card).join('')}</div>`,`${done}/${R.tickets.length} đã chấm`)+seating(t,c,R),bar:bar(esc(todo.length?`Còn ${todo.length} phiếu chờ phản hồi`:'Đã chấm hết phiếu'))};
}

function readyStage(t,c,R){
  const stars='⭐'.repeat(R.stars)+'☆'.repeat(3-R.stars);
  const res=`<section class="tt-result" aria-live="polite">${em('🌱')}<h3>Tiết học trọn vẹn</h3><div class="tt-stats"><div><b>${stars}</b><small>Giáo án</small></div><div><b>${R.understood}/${R.of}</b><small>Bạn hiểu bài</small></div><div><b>${t.patience??100}%</b><small>Nhịp lớp</small></div></div>${logList(R.log)}</section>`;
  return {body:res+seating(t,c,R),bar:bar(`Gửi lời nhắn phụ huynh · <b>+${R.estimate} xu</b>`,act('Khép tiết','lesson_complete',{task:t.id,confirm:true},'primary',{confirm:'Khép tiết và gửi lời nhắn cho phụ huynh. Thù lao chỉ nhận một lần.'}))};
}

export function lessonV2(t,c,content,ui,state){
  const R=titled(t.room,state),person=content.npcs.find(n=>n.id===t.npc);
  const periods=(c.tasks||[]).filter(x=>x.career==='teacher'&&(x.day===c.day||!ENDED.includes(x.status)));
  const index=Math.max(1,periods.sort((a,b)=>(a.day-b.day)||String(a.id).localeCompare(String(b.id),undefined,{numeric:true})).findIndex(x=>x.id===t.id)+1);
  const view=R.stage==='roll'?rollStage(t,c,R):R.stage==='plan'?planStage(t,c,R,ui):R.stage==='teach'?teachStage(t,c,R):R.stage==='check'?checkStage(t,c,R):readyStage(t,c,R);
  const focus=c.life?.mode==='calm'?100:(t.patience??100);
  return `<div class="tt tt-lesson">${timetable(t,c)}${board(t,R,index)}${hud('Nhịp lớp',focus,t,person)}<div class="tt-body">${view.body}</div>${view.bar}</div>`;
}

/* ------------------------------------------------------------ tour guide */
const TRIP_STEPS=[['plan','Lộ trình'],['gather','Điểm hẹn'],['stop','Tham quan'],['ready','Về bến']];
const ANGLE_ICON={history:'📜',fun:'🎈',photo:'📸'};
const ANGLE_LABEL={history:'chuyện xưa',fun:'trò vui',photo:'góc ảnh'};

function tripSummary(T,route){
  const leg=(a,b)=>T.legs[`${a}>${b}`]||0,place=id=>T.places.find(p=>p.id===id);
  let mins=0,prev='gate';for(const id of route){mins+=leg(prev,id)+place(id).minutes;prev=id;}
  const fee=route.reduce((s,id)=>s+place(id).fee,0),tags=new Set(route.flatMap(id=>place(id).tags));
  const happy=T.members.filter(m=>tags.has(m.wish)).length;
  const outdoor=route.filter(id=>!place(id).indoor).length,rest=route.some(id=>place(id).tags.includes('rest'));
  const warn=[];
  if(route.length&&route.length<3)warn.push(`Chọn thêm ${3-route.length} điểm (ít nhất 3).`);
  if(route.length&&!rest)warn.push('Cần một chỗ nghỉ chân (🪑).');
  if(T.weather.outdoor_max!=null&&outdoor>T.weather.outdoor_max)warn.push(`Nắng gắt: tối đa ${T.weather.outdoor_max} điểm ngoài trời.`);
  if(fee>T.fund)warn.push('Vé vượt quỹ đoàn.');
  if(mins>T.limit)warn.push('Lộ trình quá giờ.');
  if(route.includes('hill')&&T.members.some(m=>m.elder))warn.push('Đồi dốc: người lớn tuổi sẽ mệt.');
  return {mins,fee,happy,tags,warn,ok:route.length>=3&&route.length<=5&&rest&&fee<=T.fund&&mins<=T.limit&&!(T.weather.outdoor_max!=null&&outdoor>T.weather.outdoor_max)};
}

/** Map with the numbered stops (the same numbers as the list), done stops ticked and "you are here". */
function tripMap(T,route,at=-1,small=false){
  const pts=[T.gate,...route.map(id=>T.places.find(p=>p.id===id))],walked=at<0?0:at+1;
  const line=list=>list.map(p=>p.x+','+p.y).join(' ');
  const pin=p=>{
    const n=route.indexOf(p.id),done=n>=0&&n<at,here=n>=0&&n===at;
    const label=n>=0?`${n+1}. ${p.name}${done?' (đã qua)':here?' (đang ở đây)':''}`:p.closed?`${p.name} (đóng)`:p.name;
    return `<span class="tt-pin${p.closed?' closed':''}${n>=0?' on':''}${done?' done':''}${here?' here':''}" style="left:${p.x}%;top:${p.y}%" title="${esc(label)}">${em(p.emoji)}${n>=0?`<i>${done?'✓':n+1}</i>`:''}</span>`;
  };
  const alt=route.length?`Lộ trình: ${route.map((id,i)=>`${i+1}. ${T.places.find(p=>p.id===id)?.name}`).join(', ')}`:'Chưa chọn điểm nào';
  return `<div class="tt-map${small?' small':''}" role="img" aria-label="${esc('Bản đồ. '+alt)}"><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d="M0 70 C20 62 30 90 50 84 S80 70 100 78" class="tt-river"/><polyline points="${line(pts)}" class="tt-route"/>${walked?`<polyline points="${line(pts.slice(0,walked+1))}" class="tt-walked"/>`:''}</svg><span class="tt-pin gate${at<0&&T.stage!=='plan'?' here':''}" style="left:${T.gate.x}%;top:${T.gate.y}%" title="${esc(T.gate.name)}">${em(T.gate.emoji)}</span>${T.places.map(pin).join('')}</div>`;
}

/** The group: each person's wish (planning) or what they need right now (on the road). */
function memberCue(m,T,route){
  if(T.stage==='plan'){
    if(m.elder&&route.includes('hill'))return ['warn','⛰️ Ngại dốc'];
    const w=T.tags[m.wish],ok=route.some(id=>T.places.find(p=>p.id===id)?.tags.includes(m.wish));
    return [ok?'good':'',`${w.emoji} ${w.label}${ok?' ✓':''}`];
  }
  const ev=(T.events||[]).find(e=>e.who===m.id&&!e.chosen);
  if(ev)return ['warn',`${ev.emoji} ${ev.title}`];
  if(T.stage==='gather')return ['good','✓ Đã tới'];
  if(T.stage==='stop')return ['',`${ANGLE_ICON[m.angle]} Thích ${ANGLE_LABEL[m.angle]}`];
  return ['good','✓ Về đủ'];
}
function roster(T,route){
  const full=T.stage==='plan';
  const aside=full?`😊 ${tripSummary(T,route).happy}/${T.members.length} có điều mong`:T.stage==='gather'?`${T.members.filter(m=>!(T.events||[]).some(e=>e.who===m.id&&!e.chosen)).length}/${T.members.length} đã tới`:`${T.members.length} người`;
  const li=m=>{
    const [tone,cue]=memberCue(m,T,route);
    if(full)return `<li class="${tone?'tone-'+tone:''}"><span class="tt-face" aria-hidden="true">${m.emoji}</span><div><b>${esc(m.name)}</b><small>${esc(cue)}</small>${m.elder?`<em>${esc(m.note)}</em>`:''}</div></li>`;
    // On the road: one pill per person; only someone who needs care spells it out.
    const short=tone==='warn'?cue:T.stage==='stop'?ANGLE_ICON[m.angle]:'✓';
    return `<li class="${tone?'tone-'+tone:''}" title="${esc(cue)}"><span class="tt-face" aria-hidden="true">${m.emoji}</span><b>${esc(m.name)}</b><small${short===cue?'':` aria-label="${esc(cue)}"`}>${esc(short)}</small></li>`;
  };
  return section('👥','Đoàn hôm nay',`<ul class="tt-group${full?'':' compact'}">${T.members.map(li).join('')}</ul>`,aside);
}

function itinerary(T){
  let prev='gate';
  const rows=T.route.map((id,i)=>{
    const p=T.places.find(x=>x.id===id),leg=T.legs[`${prev}>${id}`]||0;prev=id;
    const st=T.stage==='ready'||(T.stage==='stop'&&i<T.at)?'done':T.stage==='stop'&&i===T.at?'now':'';
    return `<li class="${st}"${st==='now'?' aria-current="step"':''}><i aria-hidden="true">${st==='done'?'✓':i+1}</i><span><b>${em(p.emoji)} ${esc(p.name)}</b><small>Đi ${leg}′ · tham quan ${p.minutes}′${p.fee?` · vé ${p.fee} xu`:''}</small></span></li>`;
  }).join('');
  return `<ol class="tt-itin" aria-label="Lịch trình"><li class="gate ${T.stage==='gather'?'now':'done'}"><i aria-hidden="true">${T.gate.emoji}</i><span><b>${esc(T.gate.name)}</b><small>Điểm hẹn · xuất phát</small></span></li>${rows}</ol>`;
}

function planTrip(t,T,ui){
  ui.tourRoute??=[];const route=ui.tourRoute.filter(id=>T.places.some(p=>p.id===id&&!p.closed)).slice(0,5),S=tripSummary(T,route);
  const row=p=>{const n=route.indexOf(p.id),full=route.length>=5&&n<0;return local(`${n>=0?`<i class="tt-badge">${n+1}</i>`:'<i class="tt-badge off" aria-hidden="true">＋</i>'}<span class="tt-place-emoji" aria-hidden="true">${p.emoji}</span><span class="tt-place-main"><b>${esc(p.name)}</b><small>${p.closed?`🚧 ${esc(p.closed)}`:`${p.tags.map(g=>T.tags[g].emoji).join(' ')} · ${p.indoor?'trong nhà':'ngoài trời'}`}</small></span><span class="tt-place-cost"><b>${p.minutes}′</b><small>${p.fee?p.fee+' xu':'miễn phí'}</small></span>`,'tourRoute',{place:p.id},'tt-place'+(n>=0?' picked':''),Boolean(p.closed)||full,n>=0?`Bỏ điểm ${n+1}: ${p.name}`:`Thêm ${p.name}`,n>=0);};
  const top=`<div class="tt-bar-stats"><span class="${S.mins>T.limit?'bad':''}">⏱ ${S.mins}/${T.limit}′</span><span class="${S.fee>T.fund?'bad':''}">🎟 ${S.fee}/${T.fund} xu</span><span>😊 ${S.happy}/${T.members.length}</span></div>`;
  const next=!route.length?'Chạm 3–5 điểm theo thứ tự đi':S.warn[0]||`${route.length} điểm · đủ điều kiện. Chốt nhé!`;
  const places=section('🗺️','Chọn điểm theo thứ tự đi',`<p class="tt-tip">${esc(T.weather.emoji)} ${esc(T.weather.text)}</p><div class="tt-split">${tripMap(T,route)}<div class="tt-places">${T.places.map(row).join('')}</div></div>${S.warn.length>1?`<ul class="tt-warn">${S.warn.map(w=>`<li>⚠️ ${esc(w)}</li>`).join('')}</ul>`:''}`,`${route.length}/5 điểm`);
  return {body:roster(T,route)+places,bar:bar(esc(next),local('↶ Chọn lại','tourReset',{},'btn ghost',!route.length)+act('Chốt lộ trình →','tour_plan',{task:t.id,route,v:2},'primary',{disabled:!S.ok}),top)};
}

function gatherTrip(t,T){
  const late=(T.events||[]).find(e=>!e.chosen);
  const events=(T.events||[]).map(ev=>eventCard(ev,'tour_call',t.id)).join('');
  const route=section('🧭','Lộ trình đã chốt',`<div class="tt-split">${tripMap(T,T.route)}${itinerary(T)}</div>`,`${T.route.length} điểm`);
  return {body:(events?section('📍',`Điểm hẹn · ${esc(T.gate.name)}`,events):'')+roster(T,T.route)+route,
    bar:bar(esc(late?'Đoàn chưa đủ người: xử lý trước khi đi':`Đủ ${T.members.length}/${T.members.length} người ở ${T.gate.name}`),act('Xuất phát →','tour_depart',{task:t.id},'primary',{disabled:Boolean(late)}))};
}

function stopTrip(t,T){
  const H=T.here,pending=(T.events||[]).some(e=>!e.chosen),last=T.at===T.route.length-1;
  const fans=a=>T.members.filter(m=>m.angle===a).length;
  const tell=H.told?`<blockquote class="tt-quote">${ANGLE_ICON[H.told]} “${esc(H.line)}”</blockquote>`:`<div class="tt-angles" role="group" aria-label="Cách kể ở điểm này">${T.angles.map(a=>act(`${em(a.emoji)}<span>${esc(a.label)}</span><small>${fans(a.id)} người thích</small>`,'tour_tell',{task:t.id,angle:a.id},'tt-angle')).join('')}</div>`;
  const nextStop=last?null:T.places.find(p=>p.id===T.route[T.at+1]);
  const here=`<div class="tt-here"><span aria-hidden="true">${H.emoji}</span><div><small>Điểm ${T.at+1}/${T.route.length} · đang ở đây</small><h3>${esc(H.name)}</h3><p>${H.tags.map(g=>`${T.tags[g].emoji} ${esc(T.tags[g].label)}`).join(' · ')}</p></div></div>`;
  const events=(T.events||[]).map(ev=>eventCard(ev,'tour_call',t.id)).join('');
  const next=pending?'Còn chuyện cần xử lý':!H.told?'Kể chuyện cho đoàn trước đã':nextStop?`Tiếp theo: ${nextStop.emoji} ${nextStop.name}`:'Điểm cuối. Đếm đoàn rồi về bến';
  return {body:tripMap(T,T.route,T.at,true)+here+(events?section('⚠️','Chuyện trên đường',events):'')+section('🎙️','Kể gì cho đoàn nghe?',tell,H.told?'✓ Đã kể':'')+roster(T,T.route),
    bar:bar(esc(next),act(last?'Đếm đoàn & về bến →':'Đếm đoàn & đi tiếp →','tour_next',{task:t.id},'primary',{disabled:pending||!H.told}))};
}

function readyTrip(t,T){
  const stamps=T.stamps.map(id=>T.places.find(p=>p.id===id)?.emoji).join(' ');
  const res=`<section class="tt-result" aria-live="polite">${em('🧭')}<h3>Cùng đi, cùng về đủ</h3><p class="tt-stamps" aria-label="Tem các điểm đã ghé">${stamps}</p><div class="tt-stats"><div><b>${T.clock}/${T.limit}′</b><small>${T.over?`Trễ ${T.over}′`:'Đúng giờ'}</small></div><div><b>${T.fund_left} xu</b><small>Quỹ còn · thưởng +${T.saving}</small></div><div><b>${t.patience??100}%</b><small>Nhịp đoàn</small></div></div>${logList(T.log)}${T.commission?`<p class="tt-tip">🎁 Đã nhận ${T.commission} xu hoa hồng tiệm lưu niệm.</p>`:''}</section>`;
  return {body:res+section('🧭','Lịch trình',itinerary(T)),
    bar:bar(`Đoàn đã về bến · <b>+${T.estimate} xu</b>${T.tips_estimate?` · tip ~${T.tips_estimate}`:''}`,act('Khép chuyến','tour_complete',{task:t.id,confirm:true},'primary',{confirm:'Khép chuyến và gửi lời cảm ơn cho đoàn. Thù lao chỉ nhận một lần.'}))};
}

export function tripV2(t,c,content,ui){
  const T=t.trip,person=content.npcs.find(n=>n.id===t.npc);
  const view=T.stage==='plan'?planTrip(t,T,ui):T.stage==='gather'?gatherTrip(t,T):T.stage==='stop'?stopTrip(t,T):readyTrip(t,T);
  const mood=c.life?.mode==='calm'?100:(t.patience??100);
  const at=TRIP_STEPS.findIndex(x=>x[0]===T.stage);
  const chips=`<span class="tag">${esc(T.weather.emoji)} ${esc(T.weather.name)}</span><span class="tag">🎟 Quỹ ${T.stage==='plan'?T.fund:T.fund_left} xu</span>${T.wallet?`<span class="tag amber">👛 Bù ${T.wallet} xu</span>`:''}<span class="tag">⏱ ${T.stage==='plan'?'≤ '+T.limit:T.clock+'/'+T.limit}′</span>${T.tier>1?`<span class="tt-tier" aria-label="Độ khó ${T.tier}">${'★'.repeat(T.tier)}</span>`:''}`;
  const steps=`<ol class="tt-trail" aria-label="Các chặng">${TRIP_STEPS.map(([,l],i)=>`<li class="${i<at?'done':i===at?'now':''}"${i===at?' aria-current="step"':''}><i aria-hidden="true">${i<at?'✓':i+1}</i><span>${esc(l)}</span></li>`).join('')}</ol>`;
  return `<div class="tt tt-trip"><div class="tt-trip-top">${chips}</div>${steps}${hud('Nhịp đoàn',mood,t,person)}<div class="tt-body">${view.body}</div>${view.bar}</div>`;
}

export const v2Stage=t=>t?.room?({roll:'Điểm danh đầu giờ',plan:'Soạn ba hoạt động',teach:'Dạy và giúp từng bạn',check:'Phản hồi phiếu cuối tiết',ready:'Khép tiết'}[t.room.stage]):t?.trip?({plan:'Chọn lộ trình hợp đoàn',gather:'Tập trung ở điểm hẹn',stop:'Kể chuyện và giữ đoàn',ready:'Khép chuyến'}[t.trip.stage]):null;
