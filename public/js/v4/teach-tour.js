/** Teacher "Tiết học" and tour guide "Chuyến đi" (v2 layer of the legacy
 * careers). The server keeps every rule; this module only renders the
 * projection in t.room / t.trip. Phone first: one stage at a time, one
 * primary button per stage, small cards instead of long text. */
import {escapeHTML as esc,portrait} from '../icons.js';
import {t as tr,language} from './i18n.js';

if(typeof document!=='undefined'&&!document.querySelector('link[data-teach-css]')){
  const l=document.createElement('link');l.rel='stylesheet';l.href='/css/teach.css';l.dataset.teachCss='1';document.head.append(l);
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
const local=(label,action,data,cls,disabled=false,aria='')=>`<button type="button" class="${cls}" data-action="${action}" ${Object.entries(data).map(([k,v])=>`data-${k}="${esc(v)}"`).join(' ')}${disabled?' disabled':''}${aria?` aria-label="${esc(aria)}"`:''}>${label}</button>`;
const em=s=>`<span aria-hidden="true">${s}</span>`;
const signed=n=>n>0?'+'+n:String(n);
function meter(label,value){
  const v=Math.max(0,Math.min(100,value??100)),tone=v>=80?'good':v>=55?'warn':'bad';
  return `<div class="tt-meter ${tone}" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${v}" aria-label="${esc(label)}"><span>${esc(label)}</span><i><b style="width:${v}%"></b></i><strong>${v}%</strong></div>`;
}
function stepper(items,current){
  const at=items.findIndex(x=>x[0]===current);
  return `<ol class="tt-steps" aria-label="Các bước">${items.map(([id,label],i)=>`<li class="${i<at?'done':i===at?'now':''}"${i===at?' aria-current="step"':''}><i aria-hidden="true">${i<at?'✓':i+1}</i><span>${esc(label)}</span></li>`).join('')}</ol>`;
}
function eventCard(ev,op,task,extra=()=>''){
  if(ev.chosen){
    const mood=ev.mood??ev.focus??0;
    return `<article class="tt-event done ${ev.mistake?'oops':''}"><header>${em(ev.emoji)}<b>${esc(ev.title)}</b></header><p class="tt-outcome">${esc(ev.outcome)}</p><div class="tt-chips">${mood?`<span class="tag ${mood>0?'green':'amber'}">${mood>0?'😊':'😕'} ${signed(mood)}</span>`:''}${(ev.trust||[]).map(x=>`<span class="tag ${x.delta>0?'green':'amber'}">${x.delta>0?'💛':'💔'} ${esc(x.name)} ${signed(x.delta)}</span>`).join('')}${ev.minutes?`<span class="tag">⏱ +${ev.minutes}′</span>`:''}${ev.mistake?'<span class="tag danger">Chưa ổn</span>':''}</div></article>`;
  }
  return `<article class="tt-event" aria-live="polite"><header>${em(ev.emoji)}<b>${esc(ev.title)}</b></header><p>${esc(ev.text)}</p><div class="tt-options">${ev.options.map(o=>act(`<span>${esc(o.label)}</span>${o.cost?`<small>−${o.cost} xu quỹ đoàn</small>`:''}`,op,{task,event:ev.id,option:o.id},'tt-option')).join('')}</div>${extra(ev)}</article>`;
}

/* ------------------------------------------------------------ teacher */
const LESSON_STEPS=[['roll','Điểm danh'],['plan','Soạn'],['teach','Dạy'],['check','Phiếu'],['ready','Khép']];
const STYLE_ICON={look:'🖼️',hands:'🧩',talk:'💬',short:'⏱️'};
const ROLE={open:'Mở đầu',core:'Hoạt động chính',check:'Kiểm tra'};
const ENERGY={calm:['🧘','Nhẹ nhàng'],move:['🏃','Vận động'],game:['🎲','Trò chơi']};

function kidStyle(c,id){return (c.classroom?.notebook||[]).find(k=>k.id===id)?.style||null;}

function rollStage(t,R){
  const seated=R.kids.filter(k=>k.status==='here'),odd=R.kids.filter(k=>k.status!=='here'),todo=seated.filter(k=>!k.done);
  const card=k=>`<article class="tt-kid ${k.done?'ok':''} st-${k.status}"><div class="tt-kid-top"><span class="tt-face" aria-hidden="true">${k.emoji}</span><div><b>${esc(k.name)}</b><small>${k.mark_emoji} ${esc(k.clue)}</small></div></div>${k.done?`<span class="tag green">✓ ${esc(k.options.find(o=>o.id===k.done)?.label||'')}</span>`:`<div class="tt-options">${k.options.map(o=>act(esc(o.label),'lesson_roll',{task:t.id,kid:k.id,choice:o.id},'tt-option small')).join('')}</div>`}</article>`;
  return `<h3 class="tt-h">🪑 Điểm danh đầu giờ</h3>${odd.length?`<p class="tt-tip">Đọc kỹ từng trường hợp trước khi ghi.</p><div class="tt-kids">${odd.map(card).join('')}</div>`:''}
  <ul class="tt-seated" aria-label="Các bạn đang ngồi ở chỗ">${seated.map(k=>`<li class="${k.done?'ok':''}"><span aria-hidden="true">${k.emoji}</span>${esc(k.name)}${k.done?' ✓':''}</li>`).join('')}</ul>
  ${todo.length?`<div class="tt-cta">${act(`✓ Có mặt · ${todo.length} bạn đang ngồi`,'lesson_roll',{task:t.id,kid:'all'},'primary jumbo')}</div>`:''}`;
}

function planStage(t,c,R,ui){
  ui.lessonSequence??=[];const seq=ui.lessonSequence.filter(id=>R.hand.some(x=>x.id===id)).slice(0,3);
  const cards=seq.map(id=>R.hand.find(x=>x.id===id)),mins=cards.reduce((s,x)=>s+x.minutes,0);
  const reach=new Set(cards.flatMap(x=>x.styles));
  const present=R.kids.filter(k=>['here','late'].includes(k.status));
  const kid=k=>{const st=kidStyle(c,k.id);return `<li><span aria-hidden="true">${k.emoji}</span><b>${esc(k.name)}</b><small>${st?`${STYLE_ICON[st]}${reach.has(st)?' ✓':''}`:`❓ ${esc(k.trait)}`}</small></li>`;};
  const slot=i=>{const x=cards[i];return `<li class="${x?'filled':''}"><i>${i+1}</i>${x?`<span>${x.emoji} ${esc(x.name)}</span><small>${x.minutes}′</small>`:`<span class="muted">${['Mở đầu','Hoạt động chính','Kiểm tra cuối tiết'][i]}</span>`}</li>`;};
  const hand=R.hand.map(x=>{const n=seq.indexOf(x.id);return local(`<span class="tt-card-top">${em(x.emoji)}<b>${esc(x.name)}</b>${n>=0?`<i class="tt-badge">${n+1}</i>`:''}</span><span class="tt-card-meta"><span>${ENERGY[x.energy][0]} ${esc(ENERGY[x.energy][1])}</span><span>⏱ ${x.minutes}′</span></span><span class="tt-card-meta"><span>${x.styles.map(s=>STYLE_ICON[s]).join(' ')}</span><span class="tt-role r-${x.role}">${esc(ROLE[x.role])}</span></span>`,'lessonStep',{step:x.id},'tt-card'+(n>=0?' picked':''),n>=0||seq.length>=3);}).join('');
  const over=mins>R.limit,short=seq.length===3&&mins<R.min,core=cards.some(x=>x.role==='core'),ready=seq.length===3&&!over&&!short&&core;
  const why=over?'Quá giờ tiết học':short?`Mới ${mins} phút, cần ít nhất ${R.min}`:seq.length===3&&!core?'Thiếu hoạt động chính':'Chốt giáo án →';
  return `<h3 class="tt-h">📋 Soạn ba hoạt động</h3><p class="tt-tip">${esc(R.cond.emoji)} ${esc(R.cond.tip)} Tiết ${R.min}–${R.limit} phút, có một hoạt động chính, phủ đủ cách học của các bạn và kết thúc bằng kiểm tra.</p>
  <ul class="tt-present" aria-label="Cách học của các bạn có mặt">${present.map(kid).join('')}</ul>
  <ol class="tt-tray">${[0,1,2].map(slot).join('')}</ol>
  <div class="tt-sum ${over||short?'bad':''}"><span>⏱ ${mins}/${R.limit} phút</span><span>${['look','hands','talk','short'].map(s=>`<b class="${reach.has(s)?'on':''}" title="${esc({look:'Học bằng mắt',hands:'Học bằng tay',talk:'Học bằng lời',short:'Từng bước ngắn'}[s])}">${STYLE_ICON[s]}</b>`).join('')}</span></div>
  <div class="tt-hand">${hand}</div>
  <div class="tt-cta row">${local('↶ Chọn lại','lessonReset',{},'btn ghost',!seq.length)}${local(esc(why),'lessonPlan',{},'btn primary jumbo',!ready)}</div>`;
}

function teachStage(t,R,content){
  const phase=R.plan.map((id,i)=>{const x=R.hand.find(h=>h.id===id);return `<li class="${i<R.phase?'done':i===R.phase?'now':''}">${em(x.emoji)}<span>${esc(x.name)}</span></li>`;}).join('');
  const events=R.events.map(ev=>eventCard(ev,'lesson_call',t.id)).join('');
  const lost=R.lost.map(k=>`<article class="tt-kid ${k.helped?'ok':''}"><div class="tt-kid-top"><span class="tt-face" aria-hidden="true">${k.emoji}</span><div><b>${esc(k.name)}</b><small>${esc(k.helped?'Đã hiểu bài 🌱':k.away?'Đang không ở trong lớp':k.clue)}</small></div></div>${k.helped||k.away?'':`<div class="tt-methods" role="group" aria-label="Cách giúp ${esc(k.name)}">${R.methods.map(m=>act(`${em(m.emoji)}<small>${esc(m.name)}</small>`,'lesson_help',{task:t.id,kid:k.id,method:m.id},'tt-method',{aria:m.name})).join('')}</div>`}</article>`).join('');
  const pending=R.pending.length>0,last=R.phase>=2;
  return `<ol class="tt-phases">${phase}</ol>${events}${R.lost.length?`<h3 class="tt-h">🙋 Ai đang chưa theo kịp?</h3><div class="tt-kids">${lost}</div>`:`<p class="tt-tip">Cả lớp đang theo kịp bài. 🌟</p>`}
  <div class="tt-cta">${act(pending?'Xử lý chuyện trong lớp trước':last?'Thu phiếu cuối tiết →':`Sang hoạt động ${R.phase+2} →`,'lesson_next',{task:t.id},'primary jumbo',{disabled:pending})}</div>`;
}

function checkStage(t,R){
  const card=x=>`<article class="tt-ticket ${x.mark?'ok':''}"><div class="tt-kid-top"><span class="tt-face" aria-hidden="true">${x.emoji}</span><div><b>${esc(x.name)}</b><small>${esc(x.note)}</small></div><strong class="tt-answer">${esc(x.answer)}</strong></div>${x.mark?`<span class="tag green">✓ ${esc(R.marks.find(m=>m.id===x.mark).emoji+' '+R.marks.find(m=>m.id===x.mark).label)}</span>`:`<div class="tt-marks">${R.marks.map(m=>act(`${em(m.emoji)} ${esc(m.label)}`,'lesson_mark',{task:t.id,kid:x.kid,mark:m.id},'tt-option small')).join('')}</div>`}</article>`;
  return `<h3 class="tt-h">🎫 Phiếu cuối tiết</h3><div class="tt-key"><b>Đáp án trên bảng</b><p>${esc(t.lesson.fact)}</p></div><div class="tt-tickets">${R.tickets.map(card).join('')}</div>`;
}

function readyStage(t,R){
  const stars='⭐'.repeat(R.stars)+'☆'.repeat(3-R.stars);
  return `<section class="tt-result" aria-live="polite">${em('🌱')}<h3>Tiết học trọn vẹn</h3><div class="tt-stats"><div><b>${stars}</b><small>Giáo án</small></div><div><b>${R.understood}/${R.of}</b><small>Bạn hiểu bài</small></div><div><b>${t.patience??100}%</b><small>Nhịp lớp</small></div></div>${R.log.length?`<ul class="tt-log">${R.log.map(e=>`<li>${em(e.emoji)} ${esc(e.title)} ${e.mistake?'· <span class="bad-text">chưa ổn</span>':'· ✓'}</li>`).join('')}</ul>`:''}<div class="tt-cta">${act(`Khép tiết · +${R.estimate} xu`,'lesson_complete',{task:t.id,confirm:true},'primary jumbo',{confirm:'Khép tiết và gửi lời nhắn cho phụ huynh. Thù lao chỉ nhận một lần.'})}</div></section>`;
}

export function lessonV2(t,c,content,ui,state){
  const R=titled(t.room,state),person=content.npcs.find(n=>n.id===t.npc);
  let body='';
  if(R.stage==='roll')body=rollStage(t,R);
  else if(R.stage==='plan')body=planStage(t,c,R,ui);
  else if(R.stage==='teach')body=teachStage(t,R,content);
  else if(R.stage==='check')body=checkStage(t,R);
  else body=readyStage(t,R);
  const focus=c.life?.mode==='calm'?100:(t.patience??100);
  return `<div class="tt tt-lesson"><section class="tt-board"><div class="tt-board-top"><span>${esc(t.lesson.topic)} · ${esc(t.title)}</span>${R.tier>1?`<span class="tt-tier">${'★'.repeat(R.tier)}</span>`:''}</div><p>${esc(t.lesson.prompt)}</p><div class="tt-board-foot"><span class="tt-cond">${esc(R.cond.emoji)} ${esc(R.cond.text)}</span></div></section>
  <div class="tt-hud">${meter('NHỊP LỚP',focus)}<button type="button" class="tt-who" data-action="chat" data-npc="${esc(t.npc)}" data-task="${esc(t.id)}" aria-label="Trò chuyện với ${esc(person?.display_name||'')}">${portrait(person||{display_name:'?'},30)}<span>💬</span></button></div>
  ${stepper(LESSON_STEPS,R.stage)}<div class="tt-body">${body}</div></div>`;
}

/* ------------------------------------------------------------ tour guide */
const TRIP_STEPS=[['plan','Lộ trình'],['gather','Điểm hẹn'],['stop','Tham quan'],['ready','Về bến']];
const ANGLE_ICON={history:'📜',fun:'🎈',photo:'📸'};

function tripSummary(T,route){
  const leg=(a,b)=>T.legs[`${a}>${b}`]||0,place=id=>T.places.find(p=>p.id===id);
  let mins=0,prev='gate';for(const id of route){mins+=leg(prev,id)+place(id).minutes;prev=id;}
  const fee=route.reduce((s,id)=>s+place(id).fee,0),tags=new Set(route.flatMap(id=>place(id).tags));
  const happy=T.members.filter(m=>tags.has(m.wish)).length;
  const outdoor=route.filter(id=>!place(id).indoor).length,rest=route.some(id=>place(id).tags.includes('rest'));
  const warn=[];
  if(route.length&&!rest)warn.push('Cần một chỗ nghỉ chân (🪑).');
  if(T.weather.outdoor_max!=null&&outdoor>T.weather.outdoor_max)warn.push(`Nắng gắt: tối đa ${T.weather.outdoor_max} điểm ngoài trời.`);
  if(fee>T.fund)warn.push('Vé vượt quỹ đoàn.');
  if(mins>T.limit)warn.push('Lộ trình quá giờ.');
  if(route.includes('hill')&&T.members.some(m=>m.elder))warn.push('Đồi dốc: người lớn tuổi sẽ mệt.');
  if(route.length&&route.length<3)warn.push('Chọn ít nhất 3 điểm.');
  return {mins,fee,happy,tags,warn,ok:route.length>=3&&route.length<=5&&rest&&fee<=T.fund&&mins<=T.limit&&!(T.weather.outdoor_max!=null&&outdoor>T.weather.outdoor_max)};
}

function tripMap(T,route,here){
  const pts=[T.gate,...route.map(id=>T.places.find(p=>p.id===id))];
  return `<div class="tt-map" role="img" aria-label="Bản đồ lộ trình"><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d="M0 70 C20 62 30 90 50 84 S80 70 100 78" class="tt-river"/><polyline points="${pts.map(p=>p.x+','+p.y).join(' ')}" class="tt-route"/></svg><span class="tt-pin gate" style="left:${T.gate.x}%;top:${T.gate.y}%">${T.gate.emoji}</span>${T.places.map(p=>{const n=route.indexOf(p.id);return `<span class="tt-pin ${p.closed?'closed':''} ${n>=0?'on':''} ${here===p.id?'here':''}" style="left:${p.x}%;top:${p.y}%" title="${esc(p.name)}">${p.emoji}${n>=0?`<i>${n+1}</i>`:''}</span>`;}).join('')}</div>`;
}

function roster(T,mode){
  if(mode==='angle')return `<ul class="tt-fans" aria-label="Đoàn thích nghe kiểu gì">${T.members.map(m=>`<li title="${esc(m.name)}"><span aria-hidden="true">${m.emoji}</span><b>${esc(m.name)}</b><span aria-hidden="true">${ANGLE_ICON[m.angle]}</span></li>`).join('')}</ul><p class="tt-legend">📜 thích chuyện xưa · 🎈 thích trò vui · 📸 thích góc ảnh</p>`;
  return `<ul class="tt-roster">${T.members.map(m=>`<li title="${esc(m.note)}"><span class="tt-face" aria-hidden="true">${m.emoji}</span><div><b>${esc(m.name)}</b><small>${mode==='angle'?`${ANGLE_ICON[m.angle]} ${esc({history:'Thích chuyện xưa',fun:'Thích trò vui',photo:'Thích góc ảnh'}[m.angle])}`:`${T.tags[m.wish].emoji} ${esc(T.tags[m.wish].label)} · ${esc(m.note)}`}</small></div></li>`).join('')}</ul>`;
}

function planTrip(t,T,ui){
  ui.tourRoute??=[];const route=ui.tourRoute.filter(id=>T.places.some(p=>p.id===id&&!p.closed)).slice(0,5),S=tripSummary(T,route);
  const row=p=>{const n=route.indexOf(p.id),full=route.length>=5&&n<0;return local(`<span class="tt-place-emoji" aria-hidden="true">${p.emoji}</span><span class="tt-place-main"><b>${esc(p.name)}</b><small>${p.closed?`🚧 ${esc(p.closed)}`:`${p.tags.map(g=>T.tags[g].emoji).join(' ')} · ${p.indoor?'🏠 trong nhà':'🌤️ ngoài trời'}`}</small></span><span class="tt-place-cost"><b>${p.minutes}′</b><small>${p.fee?p.fee+' xu':'miễn phí'}</small></span>${n>=0?`<i class="tt-badge">${n+1}</i>`:''}`,'tourRoute',{place:p.id},'tt-place'+(n>=0?' picked':''),Boolean(p.closed)||full);};
  return `<h3 class="tt-h">👥 Đoàn hôm nay · ${T.members.length} người</h3>${roster(T,'wish')}
  <h3 class="tt-h">🗺️ Chọn 3–5 điểm theo thứ tự đi</h3><p class="tt-tip">${esc(T.weather.emoji)} ${esc(T.weather.text)} Thứ tự khác nhau thì đường đi dài ngắn khác nhau.</p>
  ${tripMap(T,route)}<div class="tt-places">${T.places.map(row).join('')}</div>
  <div class="tt-sum ${S.warn.length?'bad':''}"><span>⏱ ${S.mins}/${T.limit}′</span><span>🎟 ${S.fee}/${T.fund} xu</span><span>😊 ${S.happy}/${T.members.length}</span></div>${S.warn.length?`<ul class="tt-warn">${S.warn.map(w=>`<li>⚠️ ${esc(w)}</li>`).join('')}</ul>`:''}
  <div class="tt-cta row">${local('↶ Chọn lại','tourReset',{},'btn ghost',!route.length)}${act('Chốt lộ trình →','tour_plan',{task:t.id,route,v:2},'primary jumbo',{disabled:!S.ok})}</div>`;
}

function gatherTrip(t,T){
  const late=T.events.find(e=>!e.chosen),lateWho=late?.who;
  const heads=T.members.map(m=>`<li class="${m.id===lateWho?'missing':''}"><span aria-hidden="true">${m.emoji}</span><small>${m.id===lateWho?'⏰':'✓'}</small></li>`).join('');
  return `<h3 class="tt-h">📍 Điểm hẹn · ${esc(T.gate.name)}</h3><ul class="tt-heads" aria-label="Kiểm đoàn">${heads}</ul>${T.events.map(ev=>eventCard(ev,'tour_call',t.id)).join('')}
  <div class="tt-cta">${act(late?'Đoàn chưa đủ người':`Đủ ${T.members.length}/${T.members.length} người · Xuất phát →`,'tour_depart',{task:t.id},'primary jumbo',{disabled:Boolean(late)})}</div>`;
}

function stopTrip(t,T){
  const H=T.here,pending=T.events.some(e=>!e.chosen),last=T.at===T.route.length-1;
  const tell=H.told?`<blockquote class="tt-quote">${ANGLE_ICON[H.told]} “${esc(H.line)}”</blockquote>`:`<div class="tt-angles" role="group" aria-label="Cách kể ở điểm này">${T.angles.map(a=>act(`${em(a.emoji)}<span>${esc(a.label)}</span>`,'tour_tell',{task:t.id,angle:a.id},'tt-angle')).join('')}</div>`;
  const dots=T.route.map((id,i)=>{const p=T.places.find(x=>x.id===id);return `<li class="${i<T.at?'done':i===T.at?'now':''}">${p.emoji}</li>`;}).join('');
  return `<ol class="tt-dots" aria-label="Lộ trình">${dots}</ol><div class="tt-here"><span aria-hidden="true">${H.emoji}</span><div><small>ĐIỂM ${T.at+1}/${T.route.length}</small><h3>${esc(H.name)}</h3></div></div>
  ${T.events.map(ev=>eventCard(ev,'tour_call',t.id)).join('')}
  <h3 class="tt-h">🎙️ Kể gì cho đoàn nghe?</h3>${H.told?'':roster(T,'angle')}${tell}
  <div class="tt-cta">${act(pending?'Còn chuyện cần xử lý':!H.told?'Kể chuyện trước đã':last?'Đếm đoàn & về bến →':'Đếm đoàn & đi tiếp →','tour_next',{task:t.id},'primary jumbo',{disabled:pending||!H.told})}</div>`;
}

function readyTrip(t,T){
  const stamps=T.stamps.map(id=>T.places.find(p=>p.id===id)?.emoji).join(' ');
  return `<section class="tt-result" aria-live="polite">${em('🧭')}<h3>Cùng đi, cùng về đủ</h3><p class="tt-stamps">${stamps}</p><div class="tt-stats"><div><b>${T.clock}/${T.limit}′</b><small>${T.over?`Trễ ${T.over}′`:'Đúng giờ'}</small></div><div><b>${T.fund_left} xu</b><small>Quỹ còn · thưởng +${T.saving}</small></div><div><b>${t.patience??100}%</b><small>Nhịp đoàn</small></div></div>${T.log.length?`<ul class="tt-log">${T.log.map(e=>`<li>${em(e.emoji)} ${esc(e.title)} ${e.mistake?'· <span class="bad-text">chưa ổn</span>':'· ✓'}</li>`).join('')}</ul>`:''}${T.commission?`<p class="tt-tip">🎁 Đã nhận ${T.commission} xu hoa hồng tiệm lưu niệm.</p>`:''}<div class="tt-cta">${act(`Khép chuyến · +${T.estimate} xu${T.tips_estimate?` · tip ~${T.tips_estimate}`:''}`,'tour_complete',{task:t.id,confirm:true},'primary jumbo',{confirm:'Khép chuyến và gửi lời cảm ơn cho đoàn. Thù lao chỉ nhận một lần.'})}</div></section>`;
}

export function tripV2(t,c,content,ui){
  const T=t.trip,person=content.npcs.find(n=>n.id===t.npc);
  let body='';
  if(T.stage==='plan')body=planTrip(t,T,ui);
  else if(T.stage==='gather')body=gatherTrip(t,T);
  else if(T.stage==='stop')body=stopTrip(t,T);
  else body=readyTrip(t,T);
  const mood=c.life?.mode==='calm'?100:(t.patience??100);
  const clock=T.stage==='plan'?'':`<span class="tag">⏱ ${T.clock}/${T.limit}′</span>`;
  return `<div class="tt tt-trip"><div class="tt-trip-top"><span class="tag">${esc(T.weather.emoji)} ${esc(T.weather.name)}</span><span class="tag">🎟 Quỹ ${T.stage==='plan'?T.fund:T.fund_left} xu</span>${clock}${T.tier>1?`<span class="tt-tier">${'★'.repeat(T.tier)}</span>`:''}</div>
  <div class="tt-hud">${meter('NHỊP ĐOÀN',mood)}<button type="button" class="tt-who" data-action="chat" data-npc="${esc(t.npc)}" data-task="${esc(t.id)}" aria-label="Trò chuyện với ${esc(person?.display_name||'')}">${portrait(person||{display_name:'?'},30)}<span>💬</span></button></div>
  ${stepper(TRIP_STEPS,T.stage)}<div class="tt-body">${body}</div></div>`;
}

export const v2Stage=t=>t?.room?({roll:'Điểm danh đầu giờ',plan:'Soạn ba hoạt động',teach:'Dạy và giúp từng bạn',check:'Phản hồi phiếu cuối tiết',ready:'Khép tiết'}[t.room.stage]):t?.trip?({plan:'Chọn lộ trình hợp đoàn',gather:'Tập trung ở điểm hẹn',stop:'Kể chuyện và giữ đoàn',ready:'Khép chuyến'}[t.trip.stage]):null;
