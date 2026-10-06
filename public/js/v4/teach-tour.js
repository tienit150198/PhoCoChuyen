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
import {reqList,actBar,clean,tip,helpBtn,few} from '../ui-kit.js';
/** ui-kit clean() (the "Giao diện gọn" layout), false where there is no page (render tests with a stub document). */
const isClean=()=>{try{return clean();}catch{return false;}};
import {GameAPI,aiQueued} from '../api.js';
import {asset} from '../assets.js';
import {nextHint,stepCta,finalGo,pending,firstTime} from './guide.js';

if(typeof document!=='undefined'){
  if(!document.querySelector('link[data-teach-css]')){
    const l=document.createElement('link');l.rel='stylesheet';l.href=asset('/css/teach.css');l.dataset.teachCss='1';document.head.append(l);
  }
  // The sticky bar sits above the sheet's own sticky footer; measure it after every render.
  let seen='';
  const fit=()=>{
    const r=document.querySelector('dialog[open] .tt');if(!r)return;
    keepBarAboveFooter(r);
    // Keep the current period in view in the timetable strip.
    const on=r.querySelector('.tt-period.on'),wrap=on?.closest('.tt-periods-wrap');
    if(wrap&&wrap.scrollWidth>wrap.clientWidth){const a=on.getBoundingClientRect(),b=wrap.getBoundingClientRect();if(a.left<b.left||a.right>b.right)wrap.scrollLeft+=a.left-b.left-(b.width-a.width)/2;}
    // A new next step: bring its controls into view once (no scrolling up and down to find them).
    const key=r.dataset.focusKey||'';
    if(key&&key!==seen){
      const el=r.dataset.focus&&[...r.querySelectorAll(r.dataset.focus)].find(e=>e.offsetParent!==null);
      if(!el)return;
      seen=key;
      const d=r.closest('dialog'),head=d?.querySelector('.sheet-head')?.getBoundingClientRect().bottom??0;
      const foot=r.querySelector('.tt-bar')?.getBoundingClientRect().top??innerHeight;
      const a=el.getBoundingClientRect();
      // Just under the header: the lower middle of the screen is where messages pop up.
      if(a.top<head||a.bottom>foot){
        let s=el.parentElement;
        while(s&&s!==d&&!(s.scrollHeight>s.clientHeight&&/auto|scroll/.test(getComputedStyle(s).overflowY)))s=s.parentElement;
        // Instant: a re-render right after keeps the sheet's scroll position, a smooth scroll would be cut short.
        (s||document.scrollingElement).scrollBy(0,a.top-head-12);
      }
    }
  };
  const host=document.getElementById('sheetContent');
  if(host&&typeof MutationObserver!=='undefined')new MutationObserver(()=>{fit();requestAnimationFrame(fit);}).observe(host,{childList:true});
  document.addEventListener('sheetrender',()=>{fit();requestAnimationFrame(fit);});  // re-renders are morphed in place (app.js), not always a childList change
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

const act=(label,op,payload,cls='',o={})=>`<button type="button" class="btn ${cls}" data-action="expDo" data-op="${op}" data-payload="${esc(JSON.stringify(payload))}"${o.confirm?` data-confirm="${esc(o.confirm)}"`:''}${o.disabled?' disabled':''}${o.aria?` aria-label="${esc(o.aria)}"`:''}${o.attr||''}>${label}</button>`;
const local=(label,action,data,cls,disabled=false,aria='',pressed=null)=>`<button type="button" class="${cls}" data-action="${action}" ${Object.entries(data).map(([k,v])=>`data-${k}="${esc(v)}"`).join(' ')}${disabled?' disabled':''}${aria?` aria-label="${esc(aria)}"`:''}${pressed===null?'':` aria-pressed="${pressed}"`}>${label}</button>`;
const em=s=>`<span aria-hidden="true">${s}</span>`;
const signed=n=>n>0?'+'+n:String(n);
const ENDED=['completed','cancelled','referred'];

// The sheet is re-rendered after every action: folds remember whether the player opened them.
const ttFolds=new Map();
// A button, not <details>: the host restores <details> by position after a re-render, which would hand one fold's
// state to another when folds come and go. A tap flips the fold in place; the map keeps it for the next render.
if(typeof document!=='undefined')document.addEventListener('click',e=>{const b=e.target?.closest?.('[data-tt-fold]');if(!b)return;
  const on=b.getAttribute('aria-expanded')!=='true',box=b.parentElement;ttFolds.set(b.dataset.ttFold,on);
  b.setAttribute('aria-expanded',String(on));box.classList.toggle('is-open',on);const body=box.querySelector(':scope>.fold-body');if(body)body.hidden=!on;},true);
function ttFold(key,summary,body,open=false,cls='fold tt-fold'){
  const on=ttFolds.has(key)?ttFolds.get(key):open;
  return `<div class="${cls}${on?' is-open':''}" data-tour-fold="${esc(key)}"><button type="button" class="tt-fold-sum" data-tt-fold="${esc(key)}" aria-expanded="${on}">${summary}</button><div class="fold-body"${on?'':' hidden'}>${body}</div></div>`;
}
const wide=()=>typeof matchMedia==='function'&&matchMedia('(min-width:761px)').matches;
function meter(label,value){
  const v=Math.max(0,Math.min(100,value??100)),tone=v>=80?'good':v>=55?'warn':'bad';
  // Clean layout (docs/UI_KIT.md): the meter's name is its aria-label; a small icon stands in for the words.
  return `<div class="tt-meter ${tone}" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${v}" aria-label="${esc(label)}">${isClean()?'<span aria-hidden="true">💗</span>':`<span>${esc(label)}</span>`}<i><b style="width:${v}%"></b></i><strong>${v}%</strong></div>`;
}
function hud(label,value,t,person){
  return `<div class="tt-hud">${meter(label,value)}<button type="button" class="tt-who" data-action="chat" data-npc="${esc(t.npc)}" data-task="${esc(t.id)}" aria-label="Trò chuyện với ${esc(person?.display_name||'')}">${portrait(person||{display_name:'?'},30)}<span aria-hidden="true">💬</span></button></div>`;
}
/** Sticky bottom bar (the shared ui-kit actBar): what to do next on the left, the main button(s) on the right.
 * `top` adds a full-width row above (route totals, the plan slots on a wide sheet). */
function bar(next,buttons='',top=''){
  return actBar({top,next:next?`<p class="tt-next ui-note" aria-live="polite">${next}</p>`:'',main:buttons?`<div class="tt-bar-btns">${buttons}</div>`:'',cls:'tt-bar'});
}
function section(icon,title,body,aside='',cls=''){
  return `<section class="tt-sec ${cls}"><div class="tt-sec-head"><h3>${em(icon)} ${title}</h3>${aside?`<small>${aside}</small>`:''}</div>${body}</section>`;
}
function eventCard(ev,op,task){
  if(ev.chosen){
    // Handled: one line (what happened + the mark); the outcome and the effects unfold from it.
    const mood=ev.mood??ev.focus??0;
    const chips=`<div class="tt-chips">${mood?`<span class="tag ${mood>0?'green':'amber'}">${mood>0?'😊':'😕'} ${signed(mood)}</span>`:''}${(ev.trust||[]).map(x=>`<span class="tag ${x.delta>0?'green':'amber'}">${x.delta>0?'💛':'💔'} ${esc(x.name)} ${signed(x.delta)}</span>`).join('')}${ev.minutes?`<span class="tag">⏱ +${ev.minutes}′</span>`:''}${ev.mistake?'<span class="tag danger">Chưa ổn</span>':''}</div>`;
    return `<div class="tt-event done ${ev.mistake?'oops':''}">${ttFold('ev-'+task+'-'+ev.id,`${em(ev.emoji)} <b>${esc(ev.title)}</b>${ev.mistake?' <b class="bad-text">chưa ổn</b>':' <b class="good-text">✓</b>'}`,`<p class="tt-outcome">${esc(ev.outcome)}</p>${chips}`)}</div>`;
  }
  // Clean layout: the title, what happens and every choice (with its cost) stay; only the "Cần bạn quyết" kicker goes.
  const C=isClean();
  return `<article class="tt-event" aria-live="polite" data-ev="${esc(ev.id)}"><header>${em(ev.emoji)}<div>${C?'':'<small>Cần bạn quyết</small>'}<b>${esc(ev.title)}</b></div></header><p>${esc(ev.text)}</p><div class="tt-options">${ev.options.map(o=>act(`<span>${esc(o.label)}</span>${o.cost?`<small>−${o.cost} xu${C?'':' quỹ đoàn'}</small>`:''}`,op,{task,event:ev.id,option:o.id},'tt-option',{attr:` data-opt="${esc(o.id)}"`})).join('')}</div></article>`;
}
function logList(log){
  return log.length?`<ul class="tt-log">${log.map(e=>`<li>${em(e.emoji)} <span>${esc(e.title)}</span> ${e.mistake?'<b class="bad-text">chưa ổn</b>':'<b class="good-text">✓</b>'}</li>`).join('')}</ul>`:'';
}

/* ------------------------------------------------------------ next step (guide.js)
 * Every stage lists what is left as steps; the same steps drive the header hint, the main
 * button in the sticky bar and (first task in the career) the glow on the control to press.
 * On that first task a decision glows on the fitting choice: the tables below mirror the
 * server's rules (game/teach_lesson.py, game/tour_trip.py). Later tasks only point at the
 * choice area and keep the challenge. */
const ROLL_GOOD={here:'present',sick:'excused',late:'let_in',missing:'report'};
const CLASS_GOOD={phone:'step_out',shy:'boards',copy:'move',push:'talk',accent:'teach',tears:'grow',projector:'draw',bee:'window',sleepy:'ask',toilet:'buddy',candy:'keep',visit:'same',leak:'fix'};
const KID_STYLE={minh:'look',an:'hands',vy:'talk',bao:'short',khoa:'look',linh:'short',tu:'hands',mai:'talk'};
const COND_WANT={fresh:['calm','game','move'],noisy:['calm'],sleepy:['move'],nervous:['game'],hot:['calm','game'],friday:['game','move']};
const TRIP_GOOD={late:'call',lost:'point',coconut:'board',bus:'walk',parade:'watch',commission:'decline',heat:'shade',peanut:'ask',shower:'shelter',flash:'quiet',toilet:'escort',threat:'firm',wallet:'warn',dress:'scarf'};
const BEST_ANGLE={culture:'history',nature:'fun',food:'fun',shop:'fun',photo:'photo',rest:'history'};
const nfc=s=>String(s??'').normalize('NFC');

/** Hint (moved into the sheet header by the host), the bar's main button and where to scroll. */
function guided(x,t,stage,view){
  const steps=view.steps||[],final=view.final||{label:'',go:null,ready:false};
  const fin=final.go&&final.ready!==false?{label:final.hint||final.label.replace(/<[^>]*>/g,'').replace(/[→]/g,'').trim(),go:final.go}:null;
  const n=pending(steps);
  const focus=n?(n.pulse&&firstTime(x)?n.pulse:n.go?.sel||''):'';
  return {hint:nextHint(x,steps,{final:fin}),cta:stepCta(x,steps,final,{style:'primary'}),
    attrs:focus?` data-focus="${esc(focus)}" data-focus-key="${esc(`${t.id}|${stage}|${n.label}`)}"`:''};
}
/** Name the fitting choice only on the first task. */
const glow=(first,sel)=>first&&sel?{pulse:sel}:{};

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
  const C=isClean();
  const cells=list.map((x,i)=>{
    const on=x.id===t.id,done=ENDED.includes(x.status);
    const st=done?'✓ Đã dạy':on?'● Đang dạy':x.room&&x.room.stage!=='roll'?'Dạy dở':'Chưa vào';
    // Clean layout: one number per period (✓ taught); the topic and the state are its aria-label.
    const say=`Tiết ${i+1}: ${x.lesson?.topic||x.title} · ${st}`;
    const inner=C?`<b aria-hidden="true">${done?'✓':i+1}</b>`:`<span><b>Tiết ${i+1}</b> · ${esc(x.lesson?.topic||x.title)}</span><small>${st}</small>`;
    return on||done?`<li class="tt-period ${on?'on':'done'}"${on?' aria-current="true"':''}${C?` role="img" aria-label="${esc(say)}"`:''}>${inner}</li>`:`<li>${local(inner,'job',{task:x.id},'tt-period',false,C?say:`Tiết ${i+1}: ${x.title}`)}</li>`;
  }).join('');
  return `<nav class="tt-periods-wrap" aria-label="Thời khoá biểu hôm nay"><ol class="tt-periods${C?' tt-periods-mini':''}">${cells}</ol></nav>`;
}

/** Clean layout: the rules of a period behind one "?" (with the explanations this screen folded away). */
function lessonHelp(R){
  return helpBtn('teach-lesson','🏫 Tiết học',[
    {title:'Soạn giáo án',body:`<ul><li>⏱ ${R.min}–${R.limit} phút, 3 hoạt động, có ít nhất một hoạt động chính</li><li>⭐ Mở đầu hợp không khí lớp</li><li>⭐ Có đủ cách học của các bạn có mặt</li><li>⭐ Kết thúc bằng thẻ Kiểm tra</li></ul>`},
    {title:'Chấm phiếu',body:'<p>So bài với đáp án: đúng → 🌟 Khen cụ thể · sai hoặc chép nhầm → 🪜 Gợi ý một bước · ghi "Giống hệt phiếu của…" → 🤝 Gặp riêng.</p>'},
  ],{tips:true,cls:'tt-q'});
}
const ROLL_SHORT={excused:'Vắng có phép',present:'Có mặt'};
const ROLE_SHORT={open:'Mở đầu',core:'Chính',check:'Kiểm tra'};
/** An activity card's name in two words on the clean layout (it is scored on its icons: energy, ways of learning,
 * minutes, role; never on the name). The full name stays in title. */
const CARD_SHORT={breath:'Hít thở',dance:'Vận động',riddle:'Câu đố',demo:'Làm mẫu',cards:'Thẻ đồ vật',story:'Kể chuyện',relay:'Tiếp sức',pairs:'Hỏi đáp',poster:'Vẽ sơ đồ',board:'Giơ bảng',ticket:'Phiếu cuối',share:'Nói lại'};
const cname=x=>isClean()&&CARD_SHORT[x.id]?CARD_SHORT[x.id]:x.name;
const MARK_SHORT={praise:'Khen',hint:'Gợi ý',private:'Gặp riêng'};
const METHOD_SHORT={look:'Vẽ hình',hands:'Tự thử',talk:'Kể ví dụ',short:'Chia nhỏ'};

function board(t,R,index){
  const at=LESSON_STEPS.findIndex(x=>x[0]===R.stage);
  const card=id=>R.hand.find(h=>h.id===id);
  const plan=R.plan?.length?`<ol class="tt-flow" aria-label="Giáo án">${R.plan.map((id,i)=>{const x=card(id);if(!x)return '';const st=R.stage==='teach'?(i<R.phase?'done':i===R.phase?'now':''):'done';return `<li class="${st}"${st==='now'?' aria-current="step"':''}>${em(x.emoji)}<span title="${esc(x.name)}">${esc(cname(x))}</span><small>${st==='now'?(isClean()?'▶ ':'▶ Đang dạy · '):''}${x.minutes}′</small></li>`;}).join('')}</ol>`:'';
  const teach=R.stage==='teach',C=isClean();
  // Clean layout: the topic alone (the timetable numbers the period), 📜 for the fold, the class's mood line in "?"
  // (the planner keeps its advice where the opener is chosen), the chalk keeps "1/5"; a "?" with the rules.
  const top=`<span class="tt-board-top"><span>${C?'':`Tiết ${index} · `}${esc(t.lesson.topic)}</span>${R.tier>1?`<span class="tt-tier" aria-label="Độ khó ${R.tier}">${'★'.repeat(R.tier)}</span>`:''}${C?'<small aria-label="Đề bài">📜</small>':`<small>${plan&&!teach?'Đề bài · giáo án':'Đề bài'}</small>`}</span>`;
  const cond=`${esc(R.cond.emoji)} ${esc(R.cond.text)}`;
  return `<section class="tt-board" aria-label="Bảng lớp">
    ${ttFold('board-'+t.id,top,`<p class="tt-prompt">${esc(t.lesson.prompt)}</p>${teach?'':plan}`,false,'tt-board-more')}${teach?plan:''}
    <div class="tt-board-foot">${C?`<span aria-hidden="true">${esc(R.cond.emoji)}</span>${tip(cond,'Không khí lớp','span')}`:`<span>${cond}</span>`}<span class="tt-chalk" role="img" aria-label="Bước ${at+1}/5: ${esc(LESSON_STEPS[at]?.[1]||'')}">${LESSON_STEPS.map((_,i)=>`<i class="${i<at?'done':i===at?'now':''}"></i>`).join('')}<b>${at+1}/5${C?'':` · ${esc(LESSON_STEPS[at]?.[1]||'')}`}</b></span>${C?lessonHelp(R):''}</div>
  </section>`;
}

/** One desk per pupil. The cue changes with the step of the period. */
function seatCue(k,R,c,reach){
  if(R.stage==='roll')return k.done?(ROLL_DONE[`${k.status}:${k.done}`]||['good','✓']):ROLL_WAIT[k.status]||['',''];
  if(!isHere(k))return ['dim','Vắng'];
  // Clean layout: the way a pupil learns as its icon (the same icons as the activity cards); the trait stays.
  if(R.stage==='plan'){const st=kidStyle(c,k.id),C=isClean();return st?[reach.has(st)?'good':'',`${STYLE_ICON[st]}${C?'':' '+STYLE_SHORT[st]}${reach.has(st)?' ✓':''}`]:['',C?'❓':'❓ Chưa rõ'];}
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
  const A=R.stage==='teach'&&R.ask&&['up','quiet'].includes(R.ask.state)?R.ask:null;
  const seats=R.kids.map(k=>{
    const [tone,cue]=seatCue(k,R,c,reach);
    const hint=R.stage==='plan'&&isHere(k)&&!kidStyle(c,k.id)?`<em>${esc(k.trait)}</em>`:'';
    const hand=A&&A.kid===k.id?`<span class="cl-raise${A.state==='quiet'?' quiet':''}" role="img" aria-label="${esc(A.state==='up'?k.name+' đang giơ tay':k.name+' có điều muốn hỏi')}">${A.state==='up'?'🙋 ?':'✏️'}</span>`:'';
    return `<li class="tt-seat ${tone?'tone-'+tone:''}${hand?' cl-asking':''}">${hand}<span class="tt-face" aria-hidden="true">${k.emoji}</span><b>${esc(k.name)}</b><small>${esc(cue)}</small>${hint}</li>`;
  }).join('');
  const C=isClean(),done=R.kids.filter(k=>k.done).length;
  const aside=R.stage==='roll'?`${done}/${R.kids.length} đã ghi`:`${here}/${R.kids.length} có mặt`;
  const room=`<div class="tt-room${R.stage==='plan'?' wide':''}">${C?"":`<p class="tt-front" aria-hidden="true">Bục giảng</p>`}<ul class="tt-seats" aria-label="Chỗ ngồi của các bạn">${seats}</ul></div>`;
  // Roll call and planning read every desk; later the class is a strip of faces that opens into the chart.
  // Clean layout: the roll call folds too (the seated pupils are one tap in the bar; the ones to write down one by
  // one have their own cards above), and the strip says only the count.
  const count=R.stage==='roll'?`${done}/${R.kids.length}`:`${here}/${R.kids.length}`;
  if(R.stage==='plan'||(R.stage==='roll'&&!C))return section('🪑',C?'':'Sơ đồ lớp',room,C?`<span aria-label="${esc(aside)}">${count}</span>`:aside,'tt-class');
  const faces=R.kids.map(k=>{const [tone]=seatCue(k,R,c,reach);return `<i class="${tone?'tone-'+tone:''}" title="${esc(k.name)}">${k.emoji}${A&&A.kid===k.id?'🙋':''}</i>`;}).join('');
  return `<section class="tt-sec tt-class tt-class-fold">${ttFold('seats-'+t.id,C?`${em('🪑')}<span class="tt-faces" aria-hidden="true">${faces}</span><small aria-label="${esc('Sơ đồ lớp: '+aside)}">${count}</small>`:`${em('🪑')} <span>Sơ đồ lớp</span><span class="tt-faces" aria-hidden="true">${faces}</span><small>${aside}</small>`,room)}</section>`;
}

function rollStage(t,c,R,first){
  const odd=R.kids.filter(k=>k.status!=='here'),todo=R.kids.filter(k=>k.status==='here'&&!k.done),left=odd.filter(k=>!k.done);
  // Clean layout: the pupil's name, the clue (a note from home, a late arrival, an empty chair) and every choice stay;
  // "Ghi vắng có phép / Ghi có mặt" lose their "Ghi"; the book's title and count fold into the bar's "📋 n/5".
  const C=isClean(),say=o=>C&&ROLL_SHORT[o.id]&&/^Ghi /.test(o.label)?ROLL_SHORT[o.id]:o.label;
  const card=k=>`<article class="tt-kid st-${k.status}" data-kid="${esc(k.id)}"><div class="tt-kid-top"><span class="tt-face" aria-hidden="true">${k.emoji}</span><div><b>${esc(k.name)}</b><small>${k.mark_emoji} ${esc(k.clue)}</small></div></div><div class="tt-options">${k.options.map(o=>act(esc(say(o)),'lesson_roll',{task:t.id,kid:k.id,choice:o.id},'tt-option',{attr:` data-opt="${esc(o.id)}"`,aria:say(o)===o.label?'':o.label})).join('')}</div></article>`;
  const cases=left.length?C?`<section class="tt-sec tt-roll" aria-label="Sổ điểm danh"><div class="tt-kids">${left.map(card).join('')}</div></section>`:section('📋','Sổ điểm danh',`<div class="tt-kids">${left.map(card).join('')}</div>`,`${left.length} bạn cần ghi riêng`):'';
  const next=`📋 ${R.kids.filter(k=>k.done).length}/${R.kids.length}${left.length&&!C?` · ${left.length} bạn ghi riêng`:''}`;
  const steps=[];
  if(todo.length)steps.push({ok:null,label:`Điểm danh ${todo.length} bạn đang ngồi`,go:{cmd:'lesson_roll',payload:{task:t.id,kid:'all'},label:`✓ Có mặt · ${todo.length} bạn`}});
  for(const k of left){const box=`.tt-kid[data-kid="${k.id}"]`;
    steps.push({ok:null,label:`Ghi điểm danh cho ${k.name}`,go:{sel:box,label:C?`📋 Ghi cho ${esc(k.name)}`:`📋 Ghi điểm danh cho ${esc(k.name)}`},...glow(first,ROLL_GOOD[k.status]&&`${box} [data-opt="${ROLL_GOOD[k.status]}"]`)});}
  // The pupils to write down one by one sit right under the board; the seating chart follows.
  return {body:cases+seating(t,c,R),status:esc(next),steps,final:{label:'Soạn bài →',ready:false}};
}

/** A plan that fits (most stars) from today's hand: what the first period glows on. */
function bestPlan(R){
  const need=R.kids.filter(isHere).map(k=>KID_STYLE[k.id]).filter(Boolean),want=COND_WANT[R.cond.id]||[];
  let best=null,top=-1;
  for(const a of R.hand)for(const b of R.hand)for(const d of R.hand){
    if(a===b||b===d||a===d)continue;
    const p=[a,b,d],mins=p.reduce((s,x)=>s+x.minutes,0);
    if(mins>R.limit||mins<R.min||!p.some(x=>x.role==='core'))continue;
    const reach=new Set(p.flatMap(x=>x.styles));
    // Stars first; among equals the textbook shape: opener, main activity, check.
    const stars=(want.includes(a.energy)?1:0)+(need.every(v=>reach.has(v))?1:0)+(d.role==='check'?1:0);
    const score=stars*10+(a.role==='open'?2:0)+(b.role==='core'?1:0);
    if(score>top){top=score;best=p.map(x=>x.id);}
  }
  return best;
}
function planStage(t,c,R,ui,first){
  ui.lessonSequence??=[];const seq=ui.lessonSequence.filter(id=>R.hand.some(x=>x.id===id)).slice(0,3);
  const cards=seq.map(id=>R.hand.find(x=>x.id===id)),mins=cards.reduce((s,x)=>s+x.minutes,0);
  const reach=new Set(cards.flatMap(x=>x.styles)),C=isClean();
  // Clean layout: every fact a card is scored on stays (energy as its icon, minutes, the ways of learning, the role in
  // one or two words); the words go to aria-labels and the rules to "?".
  const role=r=>C?ROLE_SHORT[r]:ROLE[r],energy=e=>C?`<span aria-label="${esc(ENERGY[e][1])}">${ENERGY[e][0]}</span>`:`${ENERGY[e][0]} ${esc(ENERGY[e][1])}`;
  // An empty slot on the clean layout is its number only (the order rule is in "?"; each card names its role).
  const slot=i=>{const x=cards[i];return `<li class="${x?'filled':''}"${C&&!x?` aria-label="${esc(SLOT_HINT[i])}"`:''}><i>${i+1}</i>${x?`<span><b title="${esc(x.name)}">${em(x.emoji)} ${esc(cname(x))}</b><small>${esc(role(x.role))} · ${energy(x.energy)}</small></span><strong>${x.minutes}′</strong>`:`<span class="muted">${C?'—':esc(SLOT_HINT[i])}</span>`}</li>`;};
  const hand=R.hand.map(x=>{const n=seq.indexOf(x.id);return local(`<span class="tt-card-top">${em(x.emoji)}<b title="${esc(x.name)}">${esc(cname(x))}</b></span><span class="tt-card-meta"><span>${energy(x.energy)}</span><span>⏱ ${x.minutes}′</span></span><span class="tt-card-meta"><span aria-label="${esc(x.styles.map(s=>STYLE_LONG[s]).join(', '))}">${x.styles.map(s=>STYLE_ICON[s]).join(' ')}</span><span class="tt-role r-${x.role}">${esc(role(x.role))}</span></span>${n>=0?`<i class="tt-badge" aria-label="Thứ tự ${n+1}">${n+1}</i>`:''}`,'lessonStep',{step:x.id},'tt-card'+(n>=0?' picked':''),n>=0||seq.length>=3,'',n>=0);}).join('');
  const over=mins>R.limit,short=seq.length===3&&mins<R.min,core=cards.some(x=>x.role==='core'),ready=seq.length===3&&!over&&!short&&core;
  const why=over?'Quá giờ tiết học: bớt một hoạt động dài':short?`Mới ${mins} phút, cần ít nhất ${R.min}`:seq.length===3&&!core?'Thiếu hoạt động chính':seq.length<3?`Chọn thêm ${3-seq.length} hoạt động`:'Giáo án đã đủ. Chốt nhé!';
  const styles=['look','hands','talk','short'].map(s=>`<span class="tt-style ${reach.has(s)?'on':''}"${C?` aria-label="${esc(STYLE_SHORT[s])}${reach.has(s)?' ✓':''}"`:''}>${STYLE_ICON[s]}${C?'':' '+esc(STYLE_SHORT[s])}</span>`).join('');
  // The three slots ride in the sticky bar; on a phone they sit inline above the cards instead (teach.css, F#211:
  // in the bar they took ~145 px over the cards and the bar's own lines piled up).
  const slots=[0,1,2].map(slot).join(''),tray=`<ol class="tt-tray tt-tray-bar" aria-label="Giáo án tiết này">${slots}</ol>`;
  // The class's mood decides the opener: on the clean layout it is "Mở đầu:" and the energies that fit (the same
  // table the server scores, COND want), its sentence in aria-label.
  const want=COND_WANT[R.cond.id];
  const tipLine=C&&want?`<p class="tt-tip" aria-label="${esc(R.cond.tip)}">${esc(R.cond.emoji)} Mở đầu: ${want.map(e=>`<span title="${esc(ENERGY[e][1])}">${ENERGY[e][0]}</span>`).join(' ')}</p>`:`<p class="tt-tip">${esc(R.cond.emoji)} ${esc(R.cond.tip)}</p>`;
  const planner=section('📝',C?'':'Giáo án tiết này',`${tipLine}
    <div class="tt-reach" aria-label="Cách học đã có trong giáo án">${styles}</div>
    ${C?'':`<details class="fold gd-rules"><summary>📜 Quy tắc</summary><ul><li>⏱ ${R.min}–${R.limit} phút</li><li>⭐ Mở đầu hợp không khí lớp</li><li>⭐ Có đủ cách học của các bạn có mặt</li><li>⭐ Kết thúc bằng thẻ Kiểm tra</li></ul></details>`}`,`⏱ ${mins}/${R.limit}′`,'tt-planner');
  const pick=section('🗂️',C?'':'Thẻ hoạt động',`<ol class="tt-tray tt-tray-bar tt-tray-inline" aria-label="Giáo án tiết này">${slots}</ol><div class="tt-hand">${hand}</div>`,C?`≥ ${R.min}′`:'Chạm theo thứ tự');
  const generic=!over&&!short&&(seq.length<3||core);
  const next=`<b class="${over||short?'bad-text':''}">⏱ ${mins}/${R.limit}′ · ${seq.length}/3</b>${C&&generic?'':` · ${esc(why)}`}`;
  const steps=[],best=first?bestPlan(R):null,reset={act:'lessonReset',label:'↶ Soạn lại'};
  if(best&&seq.every((id,i)=>best[i]===id))best.forEach((id,i)=>{const x=R.hand.find(h=>h.id===id);
    steps.push({ok:i<seq.length||null,label:`Thẻ ${i+1}: ${x.name}`,go:{act:'lessonStep',data:{step:id},label:C?`🗂️ ${i+1}: ${esc(cname(x))}`:`🗂️ Chọn thẻ ${i+1}: ${esc(x.name)}`},pulse:`.tt-card[data-step="${id}"]`});});
  else if(best)steps.push({ok:false,label:'Soạn lại cho hợp lớp',go:reset});
  else{
    steps.push({ok:seq.length===3||null,label:'Chọn 3 thẻ hoạt động theo thứ tự',go:{sel:'.tt-hand',label:`🗂️ Chọn thẻ ${Math.min(3,seq.length+1)}/3`}});
    if(seq.length===3&&!ready)steps.push({ok:false,label:why,go:{...reset,label:`↶ Soạn lại · ${esc(why)}`}});
  }
  return {body:pick+planner+seating(t,c,R,reach),status:next,top:tray,extra:seq.length?local('↶','lessonReset',{},'btn ghost',false,'Chọn lại'):'',steps,
    final:{label:'Chốt giáo án →',hint:'Chốt giáo án',go:{act:'lessonPlan'},ready}};
}

function teachStage(t,c,R,first){
  const events=R.events.map(ev=>eventCard(ev,'lesson_call',t.id)).join('');
  const need=R.lost.filter(k=>!k.helped&&!k.away);
  // Clean layout: the pupil's clue stays whole (it says how they learn); each way to help in two words.
  const C=isClean(),mname=m=>C&&METHOD_SHORT[m.id]?METHOD_SHORT[m.id]:m.name;
  const help=k=>`<article class="tt-kid" data-kid="${esc(k.id)}"><div class="tt-kid-top"><span class="tt-face" aria-hidden="true">${k.emoji}</span><div><b>${esc(k.name)}</b><small>${esc(k.clue)}</small></div></div><div class="tt-methods" role="group" aria-label="Cách giúp ${esc(k.name)}">${R.methods.map(m=>act(`${em(m.emoji)}<span>${esc(mname(m))}</span>`,'lesson_help',{task:t.id,kid:k.id,method:m.id},'tt-method',{attr:` data-method="${esc(m.id)}"`,aria:mname(m)===m.name?'':m.name})).join('')}</div></article>`;
  const helpBox=need.length?section('🙋',C?'Cần giúp':'Bạn cần giúp',`<div class="tt-kids">${need.map(help).join('')}</div>`,C?'':`${need.length} bạn`):'';
  const waiting=R.pending.length>0,last=R.phase>=2,A=R.ask,hand=A&&A.state==='up'&&!A.result;
  const next=`▶ ${R.phase+1}/3${need.length?` · 🙋 ${need.length}`:' · 🌟'}`;
  const steps=[];
  for(const ev of R.events.filter(e=>!e.chosen)){const box=`.tt-event[data-ev="${ev.id}"]`;
    steps.push({ok:null,label:`Xử lý: ${ev.title}`,go:{sel:box,label:`${esc(ev.emoji)} Xử lý: ${esc(ev.title)}`},...glow(first,CLASS_GOOD[ev.id]&&`${box} [data-opt="${CLASS_GOOD[ev.id]}"]`)});}
  if(A&&A.state==='quiet')steps.push({ok:null,label:`Lại gần hỏi ${A.name}`,go:{cmd:'lesson_invite',payload:{task:t.id},label:`✏️ Lại gần hỏi ${esc(A.name)}`}});
  if(hand&&A.options?.length&&!classWaiting('ask:'+t.id)){
    // The answer that explains why is the one that helps; the scripted ones differ a lot in length.
    const k=A.options.reduce((b,o,i)=>o.label.length>A.options[b].label.length?i:b,0);
    steps.push({ok:null,label:`Trả lời ${A.name}`,go:{sel:'.cl-ask .cl-chips',label:`🙋 Trả lời ${esc(A.name)}`},...glow(first,`.cl-ask .cl-chip:nth-child(${k+1})`)});
  }
  for(const k of need){const box=`.tt-kid[data-kid="${k.id}"]`;
    steps.push({ok:null,label:`Giúp ${k.name} hiểu bài`,go:{sel:box,label:C?`🙋 Giúp ${esc(k.name)}`:`🙋 Giúp ${esc(k.name)} hiểu bài`},...glow(first,KID_STYLE[k.id]&&`${box} [data-method="${KID_STYLE[k.id]}"]`)});}
  const label=last?'Thu phiếu →':`Sang hoạt động ${R.phase+2} →`;
  const go=finalGo(steps,'lesson_next',{task:t.id},{question:hand?`${A.name} đang giơ tay sẽ hạ tay xuống.`:''});
  return {body:(events?section('💬',C?'':'Chuyện trong lớp',events):'')+askPanel(t,R)+helpBox+seating(t,c,R),status:esc(next),steps,
    final:{label,hint:last?'Thu phiếu cuối tiết':`Sang hoạt động ${R.phase+2}`,go,ready:!waiting}};
}

/** The feedback that fits a ticket: most tickets carry the right answer on a guided first period. */
function rightMark(t,R,x){
  if(nfc(x.note).includes(nfc('Giống hệt')))return 'private';
  const n={};for(const v of R.tickets)n[v.answer]=(n[v.answer]||0)+1;
  const fact=nfc(t.lesson.fact).toLowerCase(),top=Object.keys(n).sort((a,b)=>(n[b]-n[a])||(fact.includes(nfc(b).toLowerCase())-fact.includes(nfc(a).toLowerCase())))[0];
  return String(x.answer)===top?'praise':'hint';
}
function checkStage(t,c,R,first){
  const todo=R.tickets.filter(x=>!x.mark),done=R.tickets.length-todo.length;
  const card=x=>`<article class="tt-ticket" data-kid="${esc(x.kid)}"><div class="tt-kid-top"><span class="tt-face" aria-hidden="true">${x.emoji}</span><div><b>${esc(x.name)}</b><small>${esc(x.note)}</small></div><strong class="tt-answer" aria-label="Bài làm: ${esc(x.answer)}">${esc(x.answer)}</strong></div><div class="tt-marks">${R.marks.map(m=>{const say=isClean()&&MARK_SHORT[m.id]||m.label;return act(`${em(m.emoji)} <span>${esc(say)}</span>`,'lesson_mark',{task:t.id,kid:x.kid,mark:m.id},'tt-option',{attr:` data-mark="${esc(m.id)}"`,aria:say===m.label?'':m.label});}).join('')}</div></article>`;
  // How to grade, in one line (players asked "chấm phiếu sao ạ"): which feedback fits which paper.
  // Clean layout: the answer key and each paper (name, note, answer, the three marks) stay; how to grade is in "?".
  const C=isClean(),howText='So bài với đáp án: đúng → 🌟 Khen cụ thể · sai hoặc chép nhầm → 🪜 Gợi ý một bước · ghi "Giống hệt phiếu của…" → 🤝 Gặp riêng. Chấm hết các phiếu rồi bấm Khép tiết.';
  const how=C?tip(esc(howText),'Chấm phiếu','p'):`<p class="tt-tip">${esc(howText)}</p>`;
  const key=`<div class="tt-key">${C?'<b aria-label="Đáp án đúng">✅</b>':'<b>Đáp án đúng</b>'}<p>${esc(t.lesson.fact)}</p></div>${how}`;
  const steps=todo.map(x=>{const box=`.tt-ticket[data-kid="${x.kid}"]`;
    return {ok:null,label:`Chấm phiếu của ${x.name}`,go:{sel:box,label:C?`🎫 Chấm ${esc(x.name)}`:`🎫 Chấm phiếu của ${esc(x.name)}`},...glow(first,`${box} [data-mark="${rightMark(t,R,x)}"]`)};});
  const rest=todo.slice(1),queue=rest.length?C?`<p class="tt-queue" aria-label="${esc('Phiếu tiếp theo: '+rest.map(x=>x.name).join(', '))}">⏭ ${rest.map(x=>x.emoji).join(' ')}</p>`:`<p class="tt-queue">Phiếu tiếp theo: ${rest.map(x=>`${x.emoji} ${esc(x.name)}`).join(' · ')}</p>`:'';
  return {body:section('🎫',C?'':'Chấm phiếu cuối tiết',`${key}<div class="tt-tickets">${todo.slice(0,1).map(card).join('')}</div>${queue}`,C?'':`${done}/${R.tickets.length} đã chấm`)+seating(t,c,R),
    status:`🎫 ${done}/${R.tickets.length}`,steps,final:{label:'Khép tiết',ready:false}};
}

function readyStage(t,c,R){
  const stars='⭐'.repeat(R.stars)+'☆'.repeat(3-R.stars);
  const res=`<section class="tt-result" aria-live="polite">${em('🌱')}<h3>Tiết học trọn vẹn</h3><div class="tt-stats"><div><b>${stars}</b><small>Giáo án</small></div><div><b>${R.understood}/${R.of}</b><small>Bạn hiểu bài</small></div><div><b>${t.patience??100}%</b><small>Nhịp lớp</small></div></div>${logList(R.log)}</section>`;
  const inbox=c.classroom?.care,mail=inbox?.waiting?`<button type="button" class="btn ghost cl-inbox-link" data-action="classroom" data-cl-tab="par">💌 ${inbox.waiting} phụ huynh đang chờ trả lời · Mở sổ lớp</button>`:'';
  return {body:res+askPanel(t,R)+mail+seating(t,c,R),status:`Gửi lời nhắn phụ huynh · <b>+${R.estimate} xu</b>`,steps:[],
    final:{label:'Khép tiết',hint:'Khép tiết, nhận thù lao',go:finalGo([],'lesson_complete',{task:t.id},{confirm:true})}};
}

export function lessonV2(t,c,content,ui,state){
  const R=titled(t.room,state),person=content.npcs.find(n=>n.id===t.npc),first=firstTime({room:c});
  const periods=(c.tasks||[]).filter(x=>x.career==='teacher'&&(x.day===c.day||!ENDED.includes(x.status)));
  const index=Math.max(1,periods.sort((a,b)=>(a.day-b.day)||String(a.id).localeCompare(String(b.id),undefined,{numeric:true})).findIndex(x=>x.id===t.id)+1);
  const view=R.stage==='roll'?rollStage(t,c,R,first):R.stage==='plan'?planStage(t,c,R,ui,first):R.stage==='teach'?teachStage(t,c,R,first):R.stage==='check'?checkStage(t,c,R,first):readyStage(t,c,R);
  const g=guided({room:c},t,R.stage,view);
  const focus=c.life?.mode==='calm'?100:(t.patience??100);
  return `<div class="tt tt-lesson"${g.attrs}>${g.hint}<div class="tt-toprow">${timetable(t,c)}${hud('Nhịp lớp',focus,t,person)}</div>${board(t,R,index)}<div class="tt-body">${view.body}</div>${bar(view.status,(view.extra||'')+g.cta,view.top||'')}</div>`;
}

/* ------------------------------------------------------------ teacher: AI in class
 * A raised hand during the lesson and the parents' message threads (classroom.js)
 * talk to POST /api/ai/class. The server applies the rules and stores the scripted
 * line first; the AI only rewords it (docs/superpowers/specs/2026-09-29-teacher-care-ai-design.md).
 * This module has no `env`, so it keeps a reference to the app's GameAPI instance
 * (captured when it accepts a state; classroomView also binds it). */
let classApi=null;
try{
  const orig=GameAPI.prototype.accept;
  if(!orig.__classAi){const wrap=function(data){classApi=this;return orig.call(this,data);};wrap.__classAi=true;GameAPI.prototype.accept=wrap;}
}catch{/* no api module (tests) */}
export const bindClassApi=api=>{if(api)classApi=api;};
/** "Kế hoạch lớp" shows one page at a time: data-cl-tab on a button picks it (also on a link that opens the dock). */
export const classTab={now:'today'};
if(typeof document!=='undefined')document.addEventListener('click',e=>{const b=e.target?.closest?.('[data-cl-tab]');if(!b)return;classTab.now=b.dataset.clTab;if(!b.dataset.action)setTimeout(rerender,0);},true);  // after the click: re-rendering now would detach the target and read as a tap outside the sheet
/* A reply's rules go through the command queue (in order with the other taps) with later:true, so the
 * server answers right after the rules. Rewording a line (op 'voice': the question, a parent's message, then
 * the reaction to the answer) changes no rule and takes the model seconds; a question being reworded shows
 * "typing" for VOICE_HOLD at most, then the scripted line and the answers (the AI wording replaces it when it
 * comes). Before 1.5.3 the model's whole wait sat in the queue: the class looked frozen for up to 25 s ("trả lời
 * học sinh mà bị đứng"). Fully off the queue, though, the voice's save write (it bumps the revision) landed
 * under a tap already on its way: 409 revision_conflict on lesson_next / lesson_call / lesson_answer / cl_parent
 * (15 sessions on 06/10), and a tap dropped when it moved again under the retry. So the voice now takes its
 * place in the queue (it goes after the taps before it) and the taps after it wait for it, for VOICE_WAIT at
 * most from when it was sent: a usual model answer lands first, a slow one no longer holds the class. */
export const VOICE_HOLD=2000,VOICE_WAIT=4000;
const clPending={},clVoiced=new Set(),clError={};
export const classAiOn=()=>!!(classApi?.ai?.configured&&classApi?.state?.settings?.aiConsent);
const rerender=()=>classApi?.dispatchEvent(new CustomEvent('state',{detail:{}}));
const clQueued=(api,fn)=>{const job=api.queue.then(fn,fn);api.queue=job.catch(()=>{});return job;};
/** A voice in the queue: it starts after the taps already queued; the taps after it wait until it lands, or
 * VOICE_WAIT after it was sent (a later landing is what the one 409 retry in api.command is for). */
export const clVoiceQueued=(api,fn,wait=VOICE_WAIT)=>aiQueued(api,fn,wait);   // api.js, shared with the reviews' AI writes
const clRid=()=>globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
const held=p=>performance.now()-p.at<VOICE_HOLD;
/** The answers wait: a reply on its way, or a question still being reworded (for VOICE_HOLD at most). */
const blocking=p=>!!p&&(!p.voice||p.hide==='first'&&held(p));
/** "Typing…" shows: a reply on its way, or a line being reworded for VOICE_HOLD at most. */
const typingNow=p=>!!p&&(!p.voice||held(p));
/** A reaction being reworded hides its scripted words for VOICE_HOLD only; after that the scripted line shows
 * and the AI wording replaces it when it comes (a slow model used to keep "typing…" up for up to 25 s). */
const hidingLast=p=>!!p&&p.voice&&p.hide==='last'&&held(p);

export async function classSend(body,key,text,{hide='first'}={}){
  const api=classApi,voice=body.op==='voice',prev=clPending[key];
  // One reply at a time per thread; a reply may go while its line is still being reworded, a voice never cuts in.
  if(!api||prev&&(voice||!prev.voice))return null;
  const mine={text:text||'',voice,hide:voice?hide:null,at:performance.now()};
  clPending[key]=mine;delete clError[key];rerender();
  if(voice)setTimeout(()=>{if(clPending[key]===mine)rerender();},VOICE_HOLD+50);
  const rid=clRid(),since=api.accepted,post=()=>api.post('/api/ai/class',{...body,request_id:rid,expected_revision:api.revision,...voice?{}:{later:true}},25000);
  const send=voice?()=>clVoiceQueued(api,post):()=>clQueued(api,post);
  try{
    let data;
    try{data=await send();}
    catch(error){if(error.status===409&&error.data?.state){api.accept(error.data);data=await send();}else throw error;}
    if(clPending[key]===mine)delete clPending[key];
    // An answer older than a state adopted meanwhile (a tap that landed while the model wrote) is left out.
    if(!api.accept(data,since))rerender();
    // The rules are in (later): now the reaction is reworded (a voice in the queue). An older server voiced it already.
    if(!voice&&data?.reason==='later'&&classAiOn())classSend({kind:body.kind,pupil:body.pupil,...body.task?{task:body.task}:{},op:'voice'},key,'',{hide:'last'});
    return data;
  }catch(error){
    if(clPending[key]===mine)delete clPending[key];
    if(!voice)clError[key]=error.status?(error.message||'Chưa gửi được.'):'Mất kết nối máy chủ. Thử lại nhé.';
    rerender();return null;
  }
}
/** Ask the server once to reword a fresh scripted line (question / parent message) in character. */
export function classVoice(key,body){
  if(!classAiOn()||clVoiced.has(key)||clPending[key])return;
  clVoiced.add(key);setTimeout(()=>classSend({...body,op:'voice'},key,''),30);
}
/** A reply on its way (the step "Trả lời …" then waits). A line being reworded does not hide the step. */
export const classWaiting=key=>{const p=clPending[key];return !!p&&!p.voice;};
/** The question is hidden behind "typing…" while it is reworded (VOICE_HOLD at most). */
export const classVoicing=key=>{const p=clPending[key];return !!p&&p.voice&&p.hide==='first'&&held(p);};

/** Chat bubbles for class lines: the teacher on the right, AI lines carry a badge. */
export function clBubbles(lines,key,{typing='',mine=''}={}){
  const row=l=>{
    const me=l.who==='teacher',ai=l.mode==='ai';
    return `<div class="cl-bub ${me?'me':'them'}${ai?' ai':''}"${me||ai?' data-no-translate':''}>${ai?`<span class="cl-ai" title="${esc('Lời gốc: '+(l.canonical||''))}" aria-label="Câu này do AI viết">AI</span>`:''}<p>${esc(l.text)}</p></div>`;
  };
  const wait=clPending[key],last=lines[lines.length-1];
  // A reaction being reworded: "typing…" stands where its scripted words will be, for VOICE_HOLD at most.
  if(hidingLast(wait)&&last&&last.who!=='teacher'&&last.mode==='scripted')lines=lines.slice(0,-1);
  const pend=typingNow(wait)?`${wait.text?`<div class="cl-bub me pending" data-no-translate><p>${esc(wait.text)}</p></div>`:''}<div class="cl-bub them typing" role="status" aria-label="${esc(typing||'Đang trả lời…')}"><span class="cl-dots" aria-hidden="true"><i></i><i></i><i></i></span></div>`:'';
  return `<div class="cl-thread" role="log" aria-live="polite">${lines.map(row).join('')}${pend}</div>${clError[key]?`<p class="cl-err" role="alert">${esc(clError[key])}</p>`:''}`;
}
/** Scripted answers as full-width choices + a short typed answer (≤ max chars). */
export function clReply(key,body,options,max,placeholder){
  const busy=blocking(clPending[key]),id='cl-in-'+key.replace(/[^a-z0-9]/gi,'-');
  const chips=options.map(o=>`<button type="button" class="cl-chip" data-action="clChip" data-cl="${esc(key)}" data-body="${esc(JSON.stringify({...body,option:o.id}))}" data-label="${esc(o.label)}"${busy?' disabled':''}>${esc(o.label)}</button>`).join('');
  return `<div class="cl-reply"><div class="cl-chips" role="group" aria-label="Câu soạn sẵn">${chips}</div><form class="cl-form" data-cl-form="${esc(key)}" data-body="${esc(JSON.stringify(body))}"><textarea id="${id}" name="text" data-preserve rows="2" maxlength="${max}" required placeholder="${esc(placeholder)}" aria-label="${esc(placeholder)}"></textarea><button type="submit" class="btn primary"${busy?' disabled':''}>Gửi</button></form>${modeLine(`${classAiOn()?'✨ Nhân vật trả lời bằng AI · đừng gõ thông tin thật':'Gõ câu của bạn hoặc chọn một câu ở trên'} · tối đa ${max} ký tự`)}</div>`;
}
/** The reply box's mode line; on the clean layout it is listed in "?" (the AI warning stays: it is not an explanation). */
function modeLine(text){
  return isClean()&&!classAiOn()?tip(esc(text),'Trả lời','small'):`<small class="cl-mode">${esc(text)}</small>`;
}
if(typeof document!=='undefined'){
  document.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-cl]');if(!b)return;
    e.preventDefault();e.stopPropagation();if(b.disabled||!classApi)return;
    b.classList.add('is-pressed');setTimeout(()=>b.classList.remove('is-pressed'),700);
    classSend({...JSON.parse(b.dataset.body||'{}'),op:'reply'},b.dataset.cl,b.dataset.label);
  },true);
  document.addEventListener('submit',e=>{
    const f=e.target;if(!(f instanceof HTMLFormElement)||!f.dataset.clForm||!classApi)return;
    e.preventDefault();e.stopPropagation();
    const ta=f.querySelector('textarea'),text=(ta?.value||'').trim();if(!text||blocking(clPending[f.dataset.clForm]))return;
    ta.value='';classSend({...JSON.parse(f.dataset.body||'{}'),op:'reply',text},f.dataset.clForm,text);
  },true);
  document.addEventListener('keydown',e=>{
    if(e.target?.matches?.('form[data-cl-form] textarea')&&e.key==='Enter'&&!e.shiftKey&&!e.isComposing&&e.keyCode!==229){e.preventDefault();e.target.form?.requestSubmit();}
  });
}

/** The pupil with a raised hand (or a question kept on scrap paper) during the main activity. */
function askPanel(t,R){
  const A=R.ask;if(!A)return '';
  const key='ask:'+t.id,body={kind:'pupil',pupil:A.kid,task:t.id};
  // Clean layout: the pupil's name, the clue, the question and every answer stay; a question already answered folds to
  // one line (who, and how it went) that opens to the thread.
  const C=isClean();
  if(A.state==='quiet')return section('✏️',C?esc(A.name):`${esc(A.name)} có điều muốn hỏi`,`<div class="cl-ask quiet"><p class="tt-tip">${esc(A.clue)}</p><div class="tt-options">${act(esc(A.invite),'lesson_invite',{task:t.id},'tt-option')}</div></div>`,C?'':'Nhút nhát');
  if(A.state==='up'&&A.lines[0]?.mode==='scripted'&&!A.result)classVoice(key,body);
  const voicing=classVoicing(key)&&A.state==='up';
  const lines=voicing?A.lines.slice(1):A.lines;
  const thread=clBubbles(lines,key,{typing:`${A.name} đang hỏi…`});
  const tag={good:['green','💡 Hiểu ra'],ok:['amber','🤔 Còn lăn tăn'],poor:['danger','😶 Ngại hỏi'],ignored:['danger','✋ Hạ tay']}[A.result];
  const foot=A.state==='up'&&!A.result&&A.options?clReply(key,body,A.options,A.max||200,`Trả lời ${A.name}…`):`${A.note?`<p class="tt-tip">${esc(A.note)}</p>`:''}`;
  const head=A.state==='up'?`${A.emoji} ${esc(A.name)} giơ tay`:`${A.emoji} Câu hỏi của ${esc(A.name)}`;
  if(C&&A.state!=='up'&&!typingNow(clPending[key]))return `<section class="tt-sec cl-ask ${A.state}" aria-label="${esc(head)}">${ttFold('ask-'+t.id,`${em('🙋')} <span>${A.emoji} ${esc(A.name)}</span>${tag?` <span class="tag ${tag[0]}">${tag[1]}</span>`:''}`,thread+foot)}</section>`;
  return `<section class="tt-sec cl-ask ${A.state}" aria-label="${esc(head)}"><div class="tt-sec-head"><h3>${em('🙋')} ${head}</h3>${tag?`<span class="tag ${tag[0]}">${tag[1]}</span>`:''}</div>${thread}${foot}</section>`;
}

/* ------------------------------------------------------------ tour guide */
const TRIP_STEPS=[['plan','Lộ trình'],['gather','Điểm hẹn'],['stop','Tham quan'],['ready','Về bến']];
const ANGLE_ICON={history:'📜',fun:'🎈',photo:'📸'};
const ANGLE_LABEL={history:'chuyện xưa',fun:'trò vui',photo:'góc ảnh'};
const CALL_DONE={rest:'nghỉ ở homestay',clinic:'đã đi khám',push:'cố đi cùng đoàn'};

const tourFold=(key,summary,body,open=false)=>ttFold(key,summary,body,open);
/* Clean layout (docs/UI_KIT.md): a place in a word or two beside its emoji; the full name stays in aria-label and
 * title. The route is scored on the tags (shown as their icons), indoors or not, minutes, fee and closures, all kept. */
const PLACE_SHORT={museum:'Gốm',garden:'Vườn',market:'Chợ',river:'Bờ sông',cafe:'Quán trà',temple:'Chùa',craft:'Nón lá',hill:'Đồi',food:'Ăn vặt',gate:'Bến'};
const pname=p=>isClean()&&PLACE_SHORT[p.id]?PLACE_SHORT[p.id]:p.name;
function tourHelp(T){
  return helpBtn('teach-tour','🧭 Dẫn đoàn',[
    {title:'Chốt lộ trình',body:`<ul><li>Chọn 3–5 điểm theo thứ tự đi, có một chỗ nghỉ chân (🪑)</li><li>Vé ≤ quỹ đoàn, tổng giờ đi và tham quan ≤ ${T.limit}′</li><li>Nắng gắt: tối đa 2 điểm ngoài trời · mưa, gió: có điểm đóng cửa</li><li>Mỗi người có một điều mong (biểu tượng cạnh tên): ghé nơi có biểu tượng ấy</li><li>Người lớn tuổi ngại đồi dốc</li></ul>`},
    {title:'Trên đường',body:'<ul><li>Xử lý chuyện của đoàn trước khi đi tiếp</li><li>Kể chuyện hợp số đông (số người thích cạnh mỗi cách kể) và hợp nơi đang đứng</li></ul>'},
  ],{tips:true,cls:'tt-q'});
}
/** The career's record of this leg's group (c.life.tour.group), when the trip is a leg of it. */
function legGroup(T,c){const G=c.life?.tour?.group;return G&&T.group&&G.start===T.group.start?G:null;}
const hardRoute=(T,route,mins)=>route.includes('hill')||mins>100||(T.weather.id==='heat'&&route.filter(id=>!T.places.find(p=>p.id===id)?.indoor).length>1);

function tripSummary(T,route,G=null){
  const leg=(a,b)=>T.legs[`${a}>${b}`]||0,place=id=>T.places.find(p=>p.id===id);
  let mins=0,prev='gate';for(const id of route){mins+=leg(prev,id)+place(id).minutes;prev=id;}
  const fee=route.reduce((s,id)=>s+place(id).fee,0),tags=new Set(route.flatMap(id=>place(id).tags));
  const people=T.members.filter(m=>!m.away),happy=people.filter(m=>tags.has(m.wish)).length;
  const outdoor=route.filter(id=>!place(id).indoor).length,rest=route.some(id=>place(id).tags.includes('rest'));
  const warn=[];
  if(route.length&&route.length<3)warn.push(`Chọn thêm ${3-route.length} điểm (ít nhất 3).`);
  if(route.length&&!rest)warn.push('Cần một chỗ nghỉ chân (🪑).');
  if(T.weather.outdoor_max!=null&&outdoor>T.weather.outdoor_max)warn.push(`Nắng gắt: tối đa ${T.weather.outdoor_max} điểm ngoài trời.`);
  if(fee>T.fund)warn.push('Vé vượt quỹ đoàn.');
  if(mins>T.limit)warn.push('Lộ trình quá giờ.');
  if(route.includes('hill')&&people.some(m=>m.elder))warn.push('Đồi dốc: người lớn tuổi sẽ mệt.');
  const tired=G?G.members.filter(m=>m.energy<50&&!T.members.find(x=>x.id===m.id)?.away):[];
  if(tired.length&&route.length&&hardRoute(T,route,mins))warn.push(`😮‍💨 ${tired.map(m=>m.name).join(', ')} đang mệt: tránh dốc, đi ≤ 100′ (−5 nhịp mỗi người).`);
  return {mins,fee,happy,people:people.length,tags,warn,ok:route.length>=3&&route.length<=5&&rest&&fee<=T.fund&&mins<=T.limit&&!(T.weather.outdoor_max!=null&&outdoor>T.weather.outdoor_max)};
}

/** Map with the numbered stops (the same numbers as the list), done stops ticked and "you are here". */
function tripMap(T,route,at=-1,small=false){
  const pts=[T.gate,...route.map(id=>T.places.find(p=>p.id===id))],walked=at<0?0:at+1;
  const line=list=>list.map(p=>p.x+','+p.y).join(' ');
  const pin=p=>{
    const n=route.indexOf(p.id),done=n>=0&&n<at,here=n>=0&&n===at;
    const label=n>=0?`${n+1}. ${p.name}${done?' (đã qua)':here?' (đang ở đây)':''}`:p.closed?`${p.name} (đóng)`:p.name;
    return `<span class="tt-pin${p.closed?' closed':''}${n>=0?' on':''}${done?' done':''}${here?' here':''}" style="left:${p.x}%;top:${p.y}%" title="${esc(label)}">${em(p.emoji)}${n>=0?`<i aria-hidden="true">${done?'✓':n+1}</i>`:''}</span>`;
  };
  const alt=route.length?`Lộ trình: ${route.map((id,i)=>`${i+1}. ${T.places.find(p=>p.id===id)?.name}`).join(', ')}`:'Chưa chọn điểm nào';
  return `<div class="tt-map${small?' small':''}" role="img" aria-label="${esc('Bản đồ. '+alt)}"><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d="M0 70 C20 62 30 90 50 84 S80 70 100 78" class="tt-river"/><polyline points="${line(pts)}" class="tt-route"/>${walked?`<polyline points="${line(pts.slice(0,walked+1))}" class="tt-walked"/>`:''}</svg><span class="tt-pin gate${at<0&&T.stage!=='plan'?' here':''}" style="left:${T.gate.x}%;top:${T.gate.y}%" title="${esc(T.gate.name)}">${em(T.gate.emoji)}</span>${T.places.map(pin).join('')}</div>`;
}

/** The group: each person's wish (planning) or what they need right now (on the road). */
function memberCue(m,T,route){
  if(m.away)return ['dim','🏠 Nghỉ ở homestay'];
  if(T.stage==='plan'){
    if(m.sick)return ['warn','🤒 Đang ốm'];
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
function energyBar(E){
  return E?`<span class="tt-energy tone-${E.tone||'ok'}" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${E.energy}" aria-label="Sức: ${esc(E.word)}"><i><b style="width:${E.energy}%"></b></i>${esc(E.word)}</span>`:'';
}
function roster(T,route,G=null){
  const full=T.stage==='plan',n=T.present??T.members.length;
  const aside=full?`😊 ${tripSummary(T,route,G).happy}/${n} có điều mong`:T.stage==='gather'?`${T.members.filter(m=>!m.away&&!(T.events||[]).some(e=>e.who===m.id&&!e.chosen)).length}/${n} đã tới`:`${n} người`;
  const li=m=>{
    const [tone,cue]=memberCue(m,T,route),E=G?.members.find(x=>x.id===m.id);
    if(full)return `<li class="${tone?'tone-'+tone:''}"><span class="tt-face" aria-hidden="true">${m.emoji}</span><div><b>${esc(m.name)}</b><small>${esc(cue)}</small>${energyBar(E)}${m.elder&&!E?`<em>${esc(m.note)}</em>`:''}</div></li>`;
    // On the road: one pill per person; only someone who needs care spells it out.
    const short=tone==='warn'||tone==='dim'?cue:T.stage==='stop'?ANGLE_ICON[m.angle]:'✓';
    return `<li class="${tone?'tone-'+tone:''}" title="${esc(cue)}"><span class="tt-face" aria-hidden="true">${m.emoji}</span><b>${esc(m.name)}</b><small${short===cue?'':` aria-label="${esc(cue)}"`}>${esc(short)}</small></li>`;
  };
  // Clean layout: the group's title and count as numbers (👥 1/3 · 😊 2/4); every name and their wish icon stay.
  const C=isClean();
  const title=C?(T.group?`${T.group.leg+1}/${T.group.days}`:''):T.group?`Đoàn ${T.group.days} ngày · ngày ${T.group.leg+1}/${T.group.days}`:'Đoàn hôm nay';
  const aside2=C?aside.replace(/ (có điều mong|đã tới|người)$/,''):aside;
  if(!full)return section('👥',title,`<ul class="tt-group compact">${T.members.map(li).join('')}</ul>`,aside2);
  // Planning: one pill per person with their wish (✓ once the route has it); the full cards unfold.
  const pill=m=>{const [tone,cue]=memberCue(m,T,route),w=T.tags[m.wish];const short=tone==='warn'||tone==='dim'?cue:`${w?.emoji||''}${tone==='good'?' ✓':''}`;
    return `<li class="${tone?'tone-'+tone:''}" title="${esc(cue)}"><span class="tt-face" aria-hidden="true">${m.emoji}</span><b>${esc(m.name)}</b><small aria-label="${esc(cue)}">${esc(short)}</small></li>`;};
  return section('👥',title,`<ul class="tt-group compact">${T.members.map(pill).join('')}</ul>${ttFold('roster-'+T.stage,C?'<span aria-label="Chi tiết từng người">ℹ️ ▾</span>':'Chi tiết từng người',`<ul class="tt-group">${T.members.map(li).join('')}</ul>`)}`,aside2);
}
/** The map, folded on a phone (the numbered list says the same); open beside the list on a wide screen. */
function mapFold(T,route,at=-1,small=false){
  return ttFold('map-'+T.stage,isClean()?`${em('🗺️')} <span aria-label="Bản đồ lộ trình">▾</span>`:`${em('🗺️')} <span>Bản đồ lộ trình</span>`,tripMap(T,route,at,small),wide());
}

function itinerary(T){
  let prev='gate';const C=isClean();
  const rows=T.route.map((id,i)=>{
    const p=T.places.find(x=>x.id===id),leg=T.legs[`${prev}>${id}`]||0;prev=id;
    const st=T.stage==='ready'||(T.stage==='stop'&&i<T.at)?'done':T.stage==='stop'&&i===T.at?'now':'';
    const say=`Đi ${leg}′ · tham quan ${p.minutes}′${p.fee?` · vé ${p.fee} xu`:''}`;
    return `<li class="${st}"${st==='now'?' aria-current="step"':''}><i aria-hidden="true">${st==='done'?'✓':i+1}</i><span><b title="${esc(p.name)}">${em(p.emoji)} ${esc(pname(p))}</b>${C?`<small aria-label="${esc(say)}">🚶${leg}′ · 👀${p.minutes}′${p.fee?` · 🎟${p.fee}`:''}</small>`:`<small>${say}</small>`}</span></li>`;
  }).join('');
  return `<ol class="tt-itin" aria-label="Lịch trình"><li class="gate ${T.stage==='gather'?'now':'done'}"><i aria-hidden="true">${T.gate.emoji}</i><span><b>${esc(pname(T.gate))}</b>${C?'':'<small>Điểm hẹn · xuất phát</small>'}</span></li>${rows}</ol>`;
}

/** Someone in a multi-day group woke up sick: decide before the route. */
const FALLBACK_CARE=[['rest','Cho nghỉ ở homestay, để lại thuốc hạ sốt','1 món trong túi sơ cứu'],['clinic','Đưa ra trạm y tế khám, rồi đi nhẹ cùng đoàn','4 xu tiền khám'],['push','Động viên cố đi cho trọn chuyến','']];
function sickPending(T,G){return Boolean(T.care?.sick?!T.care.call:T.stage==='plan'&&G?.sick&&!G.call&&T.group?.leg===G.leg);}
function sickCard(t,T,G){
  const C=T.care;
  if(C?.sick&&C.call)return `<article class="tt-event done ${C.mistake?'oops':''}"><header>${em(C.emoji||'🤒')}<b>${esc(C.name)} · ${esc(CALL_DONE[C.call]||'')}</b></header><p class="tt-outcome">${esc(C.outcome||'')}</p>${C.mistake?'<div class="tt-chips"><span class="tag danger">Chưa ổn</span></div>':''}</article>`;
  const who=C?.sick?C:G?.sick&&sickPending(T,G)?(()=>{const m=G.members.find(x=>x.id===G.sick);return {name:m?.name||'',emoji:m?.emoji||'🤒',text:`Sáng nay ${m?.name||''} ${G.sick_text}.`,options:FALLBACK_CARE.map(([id,label,note])=>({id,label,note}))};})():null;
  if(!who)return '';
  return `<article class="tt-event tt-sick" aria-live="polite"><header>${em('🤒')}<div>${isClean()?'':'<small>Cần bạn quyết trước khi chốt lộ trình</small>'}<b>${esc(who.text)}</b></div></header><div class="tt-options">${who.options.map(o=>act(`<span>${esc(o.label)}</span>${o.note?`<small>${esc(o.note)}</small>`:''}`,'tour_care',{task:t.id,option:o.id},'tt-option',{attr:` data-opt="${esc(o.id)}"`})).join('')}</div></article>`;
}

/** Việc chăm hôm nay: partners to call, the kit, tomorrow's weather. */
function carePanel(t,T,c){
  const X=c.life?.tour;if(!X)return '';
  const G=X.group?.active?X.group:null,k=X.kit,f=X.forecast,rows=[],btns=[];let todo=0,call=0,lunch=false;
  if(G){
    if(G.night){rows.push({ok:G.called?true:null,icon:'🏡',label:'Báo homestay tối nay',note:G.called?'Cô Hạnh đã dọn chỗ cho đoàn':'Số khách, giờ về, ai ăn kiêng',tone:G.called?'':'warn'});if(!G.called){todo++;call++;btns.push(act('🏡 Báo homestay','tour_partner',{partner:'homestay'},'small'));}}
    rows.push({ok:G.lunch?true:G.departed?false:null,icon:'🍚',label:'Cơm trưa cho đoàn',note:G.lunch?'Dì Năm giữ sẵn bàn':G.departed?'Đoàn đã đi, không kịp đặt':'Đặt trước giờ xuất phát',tone:!G.lunch&&!G.departed?'warn':''});
    if(!G.lunch&&!G.departed){todo++;call++;lunch=true;btns.push(act('🍚 Đặt cơm trưa','tour_partner',{partner:'restaurant'},'small'));}
    if(G.tomorrow){rows.push({ok:G.boat_tomorrow?true:null,icon:'🛶',label:'Đò sớm ngày mai',note:G.boat_tomorrow?'Ông Bảy chờ ở bến lúc 6 giờ':f.boat?`Tùy chọn · nhịp đoàn +8 · ${X.boat_price} xu`:`Mai ${f.name.toLowerCase()}: đò nghỉ`});if(!G.boat_tomorrow&&f.boat)btns.push(act(`🛶 Đặt đò mai · ${X.boat_price} xu`,'tour_partner',{partner:'boat',when:'tomorrow'},'small'));}
    else if(X.boat_same_day&&!G.boat_today&&!G.departed&&T.stage==='plan')btns.push(act(`🛶 Đò sáng nay · ${X.boat_price} xu`,'tour_partner',{partner:'boat',when:'today'},'small'));
  }else if(X.upcoming)rows.push({ok:null,icon:'👥',label:X.upcoming.start===c.day?'Đoàn nhiều ngày tới hôm nay':`Đoàn ${X.upcoming.days} ngày tới vào ngày ${X.upcoming.start}`,note:'Cùng một đoàn, đi nhiều ngày'});
  const low=k.mic<k.mic_use*3&&!k.charging;
  rows.push({ok:k.charging||!low?true:null,icon:'🔋',label:'Pin loa cài áo',value:`${k.mic}%`,note:k.charging?'Đang sạc, sáng mai đầy':low?'Sắp hết: cắm sạc qua đêm':'',tone:k.mic<k.mic_use&&!k.charging?'danger':low?'warn':''});
  if(low)todo++;
  if(!k.charging&&k.mic<=60)btns.push(act('🔋 Cắm sạc loa','tour_kit',{item:'mic'},'small'));
  rows.push({ok:k.aid>=2?true:null,icon:'🩹',label:'Túi sơ cứu',value:`${k.aid}/${k.aid_max}`,note:k.aid<2?'Dầu gió, gói bù nước, thuốc hạ sốt sắp hết':'',tone:k.aid===0?'danger':k.aid<2?'warn':''});
  if(k.aid<2)todo++;
  if(k.aid<k.aid_max&&(k.aid<4||f.id==='heat'))btns.push(act(`🩹 Bổ sung · ${(k.aid_max-k.aid)*k.aid_price} xu`,'tour_kit',{item:'aid'},'small'));
  rows.push({ok:k.flag>=k.flag_worn?true:null,icon:'🚩',label:'Cờ dẫn đoàn',value:`${k.flag}%`,note:k.flag<k.flag_worn?'Bạc màu, khách khó nhìn thấy':'',tone:k.flag<k.flag_worn?'warn':''});
  if(k.flag<k.flag_worn)todo++;
  if(k.flag<60)btns.push(act(`🚩 Khâu cờ · ${k.flag_fix} xu`,'tour_kit',{item:'flag'},'small'));
  const body=reqList(rows,esc,'Việc chăm hôm nay')+(btns.length?`<div class="tt-care-btns">${btns.join('')}</div>`:'')+`<p class="tt-forecast">${em(f.emoji)} <span><b>Ngày mai: ${esc(f.name)}</b> · ${esc(f.tip)}</span></p>`;
  // Clean layout: the fold's line is its icon and the count (the rows inside keep their words).
  const sum=isClean()?`${em('📋')} <span aria-label="${esc(`Việc chăm hôm nay: ${todo?todo+' việc chờ':'ổn'}`)}">${todo?`<b class="tt-count">${todo}</b>`:'<small class="good-text">✓</small>'}</span>`
    :`${em('📋')} <span>Việc chăm hôm nay</span>${todo?`<b class="tt-count">${todo} việc chờ</b>`:'<small class="good-text">✓ Ổn</small>'}`;
  // Open by itself only when a partner call is waiting before the group leaves (and no sick guest comes first).
  return tourFold('care',sum,body,(call>0&&T.stage==='plan'&&!sickPending(T,G?legGroup(T,c):null))||(lunch&&T.stage==='gather'));
}

/** Partners, the place notebook, the booking page and the group's diary. */
function bookPanel(T,c){
  const X=c.life?.tour;if(!X)return '';
  const hearts=n=>`<span class="tt-hearts" aria-label="Bậc ${n}/5">${'♥'.repeat(n)}<i>${'♥'.repeat(5-n)}</i></span>`;
  const partners=`<ul class="tt-partners">${X.partners.map(p=>`<li><span class="tt-face" aria-hidden="true">${p.emoji}</span><div><b>${esc(p.name)}</b><small>${esc(p.who)} · ${esc(p.label)} ${hearts(p.level)}</small><em>${esc(p.perk)}</em></div></li>`).join('')}</ul>`;
  const R=X.rating;
  const rating=R.n?`<div class="tt-rating"><div class="tt-rating-bars" role="img" aria-label="${esc(`${R.n} đánh giá gần nhất: ${R.stars.join(', ')} sao`)}">${R.stars.map(s=>`<i class="s${s}" style="height:${s*20}%"></i>`).join('')}</div><p><b>${R.avg}★</b> · ${R.n} đánh giá gần nhất${R.featured?' <span class="tag green">⭐ Được đề xuất</span>':R.thin?' <span class="tag amber">Ít người đặt</span>':''}</p><small>Từ 5 đánh giá, trung bình ${R.goal}★ trở lên: trang đặt tour đề xuất bạn, thêm một đoàn mỗi sáng.</small></div>`:'<p class="tt-tip">Chưa có đánh giá nào trên trang đặt tour.</p>';
  const know=`<ul class="tt-know">${X.know.map(k=>`<li class="lv${k.level}">${em(k.emoji)}<span>${esc(k.name)}</span><small>${k.level===2?'🗝️ Góc ẩn':k.level===1?`📖 còn ${k.need} → 🗝️`:`${k.n}/${X.know_at?.[0]??4}`}</small></li>`).join('')}</ul>`;
  const G=legGroup(T,c)||X.group;
  const diary=G?.diary?.length?`<h4>📔 Nhật ký đoàn ${G.days} ngày</h4><ol class="tt-diary">${G.diary.map(x=>`<li>${esc(x)}</li>`).join('')}</ol>`:'';
  const opened=X.know.filter(k=>k.level).length;
  return tourFold('book',isClean()?`${em('🤝')}${em('📖')} <span aria-label="Bạn hàng · Sổ tay · Đánh giá">${R.avg?`${R.avg}★`:'▾'}</span>`:`${em('🤝')} <span>Bạn hàng · Sổ tay · Đánh giá</span>${R.avg?`<small>${R.avg}★</small>`:''}`,
    `<h4>🤝 Bạn hàng</h4>${partners}<h4>⭐ Trang đặt tour</h4>${rating}<h4>📖 Sổ tay điểm đến${opened?` · mở ${opened}/${X.know.length}`:''}</h4><p class="tt-tip">Kể hợp đoàn ${X.know_at?.[0]??4} lần ở một điểm để mở chuyện ít ai biết, ${X.know_at?.[1]??10} lần để mở góc ẩn.</p>${know}${diary}`);
}

/** The route the first trip glows on: every wish met if possible, then the fewest warnings,
 * the fewest stops and the shortest walk (the order is the quickest one). */
function bestRoute(T,G){
  const open=T.places.filter(p=>!p.closed).map(p=>p.id),ppl=T.members.filter(m=>!m.away);
  const place=id=>T.places.find(p=>p.id===id),leg=(a,b)=>T.legs[`${a}>${b}`]||0;
  const mins=r=>{let s=0,prev='gate';for(const id of r){s+=leg(prev,id)+place(id).minutes;prev=id;}return s;};
  const perms=a=>a.length<2?[a]:a.flatMap((v,i)=>perms([...a.slice(0,i),...a.slice(i+1)]).map(p=>[v,...p]));
  let best=null,key=null;
  const walk=(start,acc)=>{
    if(acc.length>=3){
      const order=perms(acc).reduce((b,p)=>mins(p)<mins(b)?p:b),S=tripSummary(T,order,G);
      if(S.ok){const tags=new Set(acc.flatMap(id=>place(id).tags)),k=[ppl.filter(m=>tags.has(m.wish)).length,-S.warn.length,-acc.length,-S.mins];
        const i=key?k.findIndex((v,j)=>v!==key[j]):0;
        if(!key||(i>=0&&k[i]>key[i])){key=k;best=order;}}
    }
    if(acc.length===5)return;
    for(let i=start;i<open.length;i++)walk(i+1,[...acc,open[i]]);
  };
  walk(0,[]);
  return best;
}
function planTrip(t,T,ui,c,first){
  const G=legGroup(T,c);
  ui.tourRoute??=[];const route=ui.tourRoute.filter(id=>T.places.some(p=>p.id===id&&!p.closed)).slice(0,5),S=tripSummary(T,route,G);
  // Clean layout: a place is its emoji, a short name, the tags' icons, 🏠 indoors / 🌤 outdoors, the minutes and the
  // fee (🎟 0 = free); a closed one says 🚧 Đóng. The full wording is the row's aria-label.
  const C=isClean();
  const placeSay=p=>`${p.name}: ${p.closed?'đóng, '+p.closed:`${p.tags.map(g=>T.tags[g].label).join(', ')}, ${p.indoor?'trong nhà':'ngoài trời'}, ${p.minutes} phút, ${p.fee?p.fee+' xu':'miễn phí'}`}`;
  const row=p=>{const n=route.indexOf(p.id),full=route.length>=5&&n<0;return local(`${n>=0?`<i class="tt-badge">${n+1}</i>`:'<i class="tt-badge off" aria-hidden="true">＋</i>'}<span class="tt-place-emoji" aria-hidden="true">${p.emoji}</span><span class="tt-place-main"><b>${esc(pname(p))}</b><small>${p.closed?(C?'🚧 Đóng':`🚧 ${esc(p.closed)}`):`${p.tags.map(g=>T.tags[g].emoji).join(' ')} · ${C?(p.indoor?'🏠':'🌤'):p.indoor?'trong nhà':'ngoài trời'}`}</small></span><span class="tt-place-cost"><b>${p.minutes}′</b><small>${C?`🎟${p.fee}`:p.fee?p.fee+' xu':'miễn phí'}</small></span>`,'tourRoute',{place:p.id},'tt-place'+(n>=0?' picked':''),Boolean(p.closed)||full,C?(n>=0?`Bỏ điểm ${n+1}: ${placeSay(p)}`:`Thêm ${placeSay(p)}`):n>=0?`Bỏ điểm ${n+1}: ${p.name}`:`Thêm ${p.name}`,n>=0);};
  const top=`<div class="tt-bar-stats"><span class="${S.mins>T.limit?'bad':''}">⏱ ${S.mins}/${T.limit}′</span><span class="${S.fee>T.fund?'bad':''}">🎟 ${S.fee}/${T.fund}${C?"":" xu"}</span><span>😊 ${S.happy}/${S.people}</span></div>`;
  const sick=sickPending(T,G);
  const next=sick?(C?'🤒 Người ốm trước':'Quyết định cho người ốm trước đã'):!route.length?(C?'Chạm 3–5 điểm':'Chạm 3–5 điểm theo thứ tự đi'):(C&&S.warn[0]?S.warn[0].replace(/\s*\(.*\)\.?$/,''):S.warn[0])||(C?`✓ ${route.length} điểm`:`${route.length} điểm · đủ điều kiện. Chốt nhé!`);
  const card=sickCard(t,T,G);
  // The weather's rule (heat: at most 2 outdoor stops; rain, wind: a place shut) stays; a fine day's line goes to "?".
  const rule=T.weather.outdoor_max!=null||T.places.some(p=>p.closed),wx=`${esc(T.weather.emoji)} ${esc(T.weather.text)}`;
  const places=section('🗺️',C?'':'Chọn điểm theo thứ tự đi',`${C&&!rule?tip(wx,'Thời tiết','p'):`<p class="tt-tip">${wx}</p>`}<div class="tt-split"><div class="tt-places">${T.places.map(row).join('')}</div>${mapFold(T,route)}</div>${S.warn.length>1?`<ul class="tt-warn">${S.warn.map(w=>`<li>⚠️ ${esc(w)}</li>`).join('')}</ul>`:''}`,C?`${route.length}/5`:`${route.length}/5 điểm`);
  const steps=[],reset={act:'tourReset',label:'↶ Chọn lại lộ trình'};
  if(sick)steps.push({ok:null,label:'Quyết cho người ốm trước',go:{sel:'.tt-sick',label:'🤒 Quyết cho người ốm'},...glow(first,'.tt-sick [data-opt="rest"]')});
  const best=first?bestRoute(T,G):null;
  if(best&&route.every((id,i)=>best[i]===id))best.forEach((id,i)=>{const p=T.places.find(x=>x.id===id);
    steps.push({ok:i<route.length||null,label:`Điểm ${i+1}: ${p.name}`,go:{act:'tourRoute',data:{place:id},label:C?`${esc(p.emoji)} Chọn ${esc(pname(p))}`:`${esc(p.emoji)} Chọn điểm ${i+1}: ${esc(p.name)}`},pulse:`.tt-place[data-place="${id}"]`});});
  else if(best)steps.push({ok:false,label:'Chọn lại cho hợp đoàn',go:reset});
  else{
    steps.push({ok:route.length>=3||null,label:'Chạm 3–5 điểm theo thứ tự đi',go:{sel:'.tt-places',label:C?`🗺️ Chọn điểm ${route.length+1}`:`🗺️ Chọn điểm ${route.length+1} (3–5 điểm)`}});
    if(route.length>=3&&!S.ok)steps.push({ok:false,label:S.warn[0]||'Lộ trình chưa hợp',go:{sel:'.tt-places',label:`⚠️ ${esc(S.warn[0]||'Sửa lộ trình')}`}});
  }
  return {first:card?section('🤒',C?'':'Người ốm sáng nay',card):'',body:places+roster(T,route,G),status:esc(next),top,steps,
    extra:route.length?local('↶','tourReset',{},'btn ghost',false,'Chọn lại'):'',
    final:{label:'Chốt lộ trình →',hint:'Chốt lộ trình',go:{cmd:'tour_plan',payload:{task:t.id,route,v:2}},ready:S.ok&&!sick}};
}

function eventSteps(T,first){
  return (T.events||[]).filter(e=>!e.chosen).map(ev=>{const box=`.tt-event[data-ev="${ev.id}"]`;
    return {ok:null,label:`Xử lý: ${ev.title}`,go:{sel:box,label:`${esc(ev.emoji)} Xử lý: ${esc(ev.title)}`},...glow(first,TRIP_GOOD[ev.id]&&`${box} [data-opt="${TRIP_GOOD[ev.id]}"]`)};});
}
/** Free partner calls for a multi-day group (lunch before the group leaves, the homestay for tonight). */
function careSteps(T,c,lunch){
  const X=c.life?.tour,G=X?.group?.active&&legGroup(T,c)?X.group:null,out=[],k=X?.kit;
  if(k&&!k.charging&&k.mic<k.mic_use*3)out.push({ok:null,label:'Cắm sạc loa qua đêm',go:{cmd:'tour_kit',payload:{item:'mic'},label:`🔋 Cắm sạc loa · ${k.mic}%`}});
  if(lunch&&G&&!G.lunch&&!G.departed)out.push({ok:null,label:'Đặt cơm trưa cho đoàn',go:{cmd:'tour_partner',payload:{partner:'restaurant'},label:'🍚 Đặt cơm trưa cho đoàn'}});
  if(G?.night&&!G.called)out.push({ok:null,label:'Báo homestay tối nay',go:{cmd:'tour_partner',payload:{partner:'homestay'},label:'🏡 Báo homestay tối nay'}});
  return out;
}
function gatherTrip(t,T,c,first){
  const G=legGroup(T,c),late=(T.events||[]).find(e=>!e.chosen);
  const events=(T.events||[]).map(ev=>eventCard(ev,'tour_call',t.id)).join('');
  const C=isClean();
  const route=section('🧭',C?'Lộ trình':'Lộ trình đã chốt',`<div class="tt-split">${itinerary(T)}${mapFold(T,T.route)}</div>`,C?'':`${T.route.length} điểm`);
  const n=T.present??T.members.length,sick=T.care?.sick&&T.care.call?section('🤒',C?'':'Người ốm sáng nay',sickCard(t,T,G)):'';
  return {body:(events?section('📍',C?esc(pname(T.gate)):`Điểm hẹn · ${esc(T.gate.name)}`,events):'')+sick+roster(T,T.route,G)+route,
    status:esc(late?(C?'⚠️ Chưa đủ người':'Đoàn chưa đủ người: xử lý trước khi đi'):C?`👥 ${n}/${n}`:`Đủ ${n}/${n} người ở ${T.gate.name}`),steps:[...eventSteps(T,first),...careSteps(T,c,true)],
    final:{label:'Xuất phát →',hint:'Xuất phát',go:{cmd:'tour_depart',payload:{task:t.id}},ready:!late}};
}

function stopTrip(t,T,c,first){
  const H=T.here,pending=(T.events||[]).some(e=>!e.chosen),last=T.at===T.route.length-1,X=c.life?.tour;
  // Clean layout: the place's tags (what the best story suits), each way of telling with how many like it (❤️ n), the
  // events and their choices stay; the notebook's progress line goes to "?".
  const C=isClean();
  const fans=a=>T.members.filter(m=>m.angle===a&&!m.away).length;
  const tell=H.told?(C?`<p class="tt-quote-mini">${ANGLE_ICON[H.told]} ✓</p>${tip(`“${esc(H.line)}”`,'Đã kể','p')}`:`<blockquote class="tt-quote">${ANGLE_ICON[H.told]} “${esc(H.line)}”</blockquote>`):`<div class="tt-angles" role="group" aria-label="Cách kể ở điểm này">${T.angles.map(a=>act(`${em(a.emoji)}<span>${esc(a.label)}</span>${C?`<small aria-label="${fans(a.id)} người thích">❤️ ${fans(a.id)}</small>`:`<small>${fans(a.id)} người thích</small>`}`,'tour_tell',{task:t.id,angle:a.id},'tt-angle',{attr:` data-angle="${esc(a.id)}"`})).join('')}</div>`;
  const K=X?.know?.find(k=>k.id===H.id);
  const bookText=K?(K.level===2?`🗝️ Sổ tay: kể hợp đoàn là dẫn được vào ${esc(K.spot||'góc ẩn')}`:K.level===1?`📖 Sổ tay: có chuyện ít ai biết · kể hay thêm ${K.need} lần để mở góc ẩn`:`📖 Sổ tay: kể hay thêm ${K.need} lần để mở chuyện ít ai biết`):'';
  const book=K?(C?tip(bookText,'Sổ tay','p'):`<p class="tt-note">${bookText}</p>`):'';
  const mic=X?.kit?`<span class="${X.kit.mic<X.kit.mic_use?'bad-text':X.kit.mic<X.kit.mic_use*3?'tt-low':''}">🔋 ${X.kit.mic}%</span>`:'';
  const nextStop=last?null:T.places.find(p=>p.id===T.route[T.at+1]);
  const here=`<div class="tt-here"><span aria-hidden="true">${H.emoji}</span><div><small${C?` aria-label="Điểm ${T.at+1}/${T.route.length} · đang ở đây"`:''}>${C?`📍 ${T.at+1}/${T.route.length}`:`Điểm ${T.at+1}/${T.route.length} · đang ở đây`}</small><h3>${esc(H.name)}</h3><p>${H.tags.map(g=>`${T.tags[g].emoji} ${esc(C?few(T.tags[g].label,2,true):T.tags[g].label)}`).join(' · ')}</p></div></div>`;
  const open=(T.events||[]).filter(e=>!e.chosen).map(ev=>eventCard(ev,'tour_call',t.id)).join(''),past=(T.events||[]).filter(e=>e.chosen).map(ev=>eventCard(ev,'tour_call',t.id)).join('');
  const next=nextStop?`➜ ${nextStop.emoji} ${pname(nextStop)}`:`➜ ${T.gate.emoji} ${pname(T.gate)}`;
  // The angle most of the group enjoys, plus the one that suits the place (as the server scores it).
  const ppl=T.members.filter(m=>!m.away),score=a=>{const f=ppl.filter(m=>m.angle===a).length;return 3*f-(ppl.length-f)+(H.tags.some(g=>BEST_ANGLE[g]===a)?2:0);};
  const angle=T.angles.map(a=>a.id).reduce((b,a)=>score(a)>score(b)?a:b);
  const steps=[...eventSteps(T,first),...careSteps(T,c,false),{ok:H.told?true:null,label:'Kể chuyện cho đoàn nghe',go:{sel:'.tt-angles',label:C?'🎙️ Chọn cách kể':'🎙️ Chọn cách kể chuyện'},...glow(first,`.tt-angle[data-angle="${angle}"]`)}];
  return {body:here+(open?section('⚠️',C?'':'Chuyện trên đường',open):'')+section('🎙️',C?'Kể chuyện':'Kể gì cho đoàn nghe?',tell+book,H.told?(C?'✓':'✓ Đã kể'):mic)+(past?`<div class="tt-past">${past}</div>`:'')+roster(T,T.route,legGroup(T,c))+mapFold(T,T.route,T.at,true),
    status:esc(next),steps,final:{label:last?'Đếm đoàn & về bến →':'Đếm đoàn & đi tiếp →',hint:last?'Đếm đoàn, về bến':'Đếm đoàn, đi tiếp',go:{cmd:'tour_next',payload:{task:t.id}},ready:!pending&&!!H.told}};
}

function readyTrip(t,T){
  const stamps=T.stamps.map(id=>T.places.find(p=>p.id===id)?.emoji).join(' ');
  const res=`<section class="tt-result" aria-live="polite">${em('🧭')}<h3>Cùng đi, cùng về đủ</h3><p class="tt-stamps" aria-label="Tem các điểm đã ghé">${stamps}</p><div class="tt-stats"><div><b>${T.clock}/${T.limit}′</b><small>${T.over?`Trễ ${T.over}′`:'Đúng giờ'}</small></div><div><b>${T.fund_left} xu</b><small>Quỹ còn · thưởng +${T.saving}</small></div><div><b>${t.patience??100}%</b><small>Nhịp đoàn</small></div></div>${logList(T.log)}${T.commission?`<p class="tt-tip">🎁 Đã nhận ${T.commission} xu hoa hồng tiệm lưu niệm.</p>`:''}</section>`;
  return {body:res+section('🧭','Lịch trình',itinerary(T)),status:`Đoàn đã về bến · <b>+${T.estimate} xu</b>${T.tips_estimate?` · tip ~${T.tips_estimate}`:''}`,steps:[],
    final:{label:'Khép chuyến',hint:'Khép chuyến, nhận thù lao',go:finalGo([],'tour_complete',{task:t.id},{confirm:true})}};
}

export function tripV2(t,c,content,ui){
  const T=t.trip,person=content.npcs.find(n=>n.id===t.npc),first=firstTime({room:c});
  const view=T.stage==='plan'?planTrip(t,T,ui,c,first):T.stage==='gather'?gatherTrip(t,T,c,first):T.stage==='stop'?stopTrip(t,T,c,first):readyTrip(t,T);
  const g=guided({room:c},t,T.stage,view);
  const mood=c.life?.mode==='calm'?100:(t.patience??100);
  const at=TRIP_STEPS.findIndex(x=>x[0]===T.stage);
  // Clean layout: the chips are icons and numbers (weather icon, 🎟 fund, ⏱ limit), their words in aria-labels; a "?"
  // holds the route rules and the explanations folded away.
  const C=isClean(),fund=T.stage==='plan'?T.fund:T.fund_left,lim=T.stage==='plan'?'≤ '+T.limit:T.clock+'/'+T.limit;
  const chips=C?`${T.group?`<span class="tag blue" aria-label="Đoàn ${T.group.days} ngày · ngày ${T.group.leg+1}">👥 ${T.group.leg+1}/${T.group.days}</span>`:''}<span class="tag" title="${esc(T.weather.name)}" aria-label="${esc(T.weather.name)}">${esc(T.weather.emoji)}</span><span class="tag" aria-label="Quỹ đoàn ${fund} xu">🎟 ${fund}</span>${T.wallet?`<span class="tag amber" aria-label="Bù ${T.wallet} xu tiền túi">👛 ${T.wallet}</span>`:''}<span class="tag" aria-label="Thời gian ${lim} phút">⏱ ${lim}′</span>${T.tier>1?`<span class="tt-tier" aria-label="Độ khó ${T.tier}">${'★'.repeat(T.tier)}</span>`:''}`
    :`${T.group?`<span class="tag blue">👥 Đoàn ${T.group.days} ngày · ${T.group.leg+1}/${T.group.days}</span>`:''}<span class="tag">${esc(T.weather.emoji)} ${esc(T.weather.name)}</span><span class="tag">🎟 Quỹ ${fund} xu</span>${T.wallet?`<span class="tag amber">👛 Bù ${T.wallet} xu</span>`:''}<span class="tag">⏱ ${lim}′</span>${T.tier>1?`<span class="tt-tier" aria-label="Độ khó ${T.tier}">${'★'.repeat(T.tier)}</span>`:''}`;
  const steps=`<span class="tt-chalk tt-trail-mini" role="img" aria-label="Chặng ${at+1}/4: ${esc(TRIP_STEPS[at]?.[1]||'')}">${TRIP_STEPS.map((_,i)=>`<i class="${i<at?'done':i===at?'now':''}"></i>`).join('')}<b>${at+1}/4${C?'':` · ${esc(TRIP_STEPS[at]?.[1]||'')}`}</b></span>`;
  return `<div class="tt tt-trip"${g.attrs}>${g.hint}<div class="tt-trip-top">${chips}${steps}${hud('Nhịp đoàn',mood,t,person)}${C?tourHelp(T):''}</div><div class="tt-body">${view.first||''}${carePanel(t,T,c)}${view.body}${bookPanel(T,c)}</div>${bar(view.status,(view.extra||'')+g.cta,view.top||'')}</div>`;
}

export const v2Stage=t=>t?.room?({roll:'Điểm danh đầu giờ',plan:'Soạn ba hoạt động',teach:'Dạy và giúp từng bạn',check:'Phản hồi phiếu cuối tiết',ready:'Khép tiết'}[t.room.stage]):t?.trip?({plan:'Chọn lộ trình hợp đoàn',gather:'Tập trung ở điểm hẹn',stop:'Kể chuyện và giữ đoàn',ready:'Khép chuyến'}[t.trip.stage]):null;
