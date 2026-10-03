/** Tổ trông trẻ Mèo Con — a day babysitting one child (server: game/careers/babysitter.py).
 * The day is a schedule of blocks, one at a time: taking the child from the parent (wash hands, read the note, a
 * greeting that suits the child, the bag), a snack or lunch that suits the child's age and allergy, play that suits
 * the mood, a sweep of the room for hazards, the nap (routine, the right comfort toy, a pat on the slow breath out:
 * a stop tap, tapStop + kit.tap_now), small moments (crying, a scraped knee, a tantrum) and the handover with an
 * honest day log. The server decides everything; one tap sends one command. */
import {stepRows,nextHint,finalGo,pending,stepLine,firstTime} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {data,cc,lower,tile,introCard,deskCard,dayBar,bottom,kitActions,meter,notesPage} from './street_kit.js';

const KIND={arrive:['👋','Nhận bé'],snack:['🍎','Bữa phụ'],meal:['🍚','Bữa trưa'],play:['🧸','Giờ chơi'],safety:['🔌','Soát nhà'],
  nap:['😴','Ngủ trưa'],moment:['💛','Chuyện nhỏ'],handover:['📝','Bàn giao']};
const need=t=>t.needs||{};
const fam=x=>data(x).fam||{};
const kidName=x=>`bé ${fam(x).kid||''}`.trim();
const FOOD=(x,k)=>(cc(x).foods||{})[k]||{name:k,emoji:'🍽️',group:'snack',al:[],prep:null,hard:false};
const ACT=(x,k)=>(cc(x).acts||{})[k]||{name:k,emoji:'🧸',fits:[],small:false,screen:false};
const HAZ=(x,k)=>(cc(x).haz||{})[k]||{emoji:'❔',name:k,fix:''};
const LOVEY=(x,k)=>(cc(x).loveys||{})[k]||['🧸',k];
const BAGI=(x,k)=>k==='lovey'?LOVEY(x,fam(x).lovey):(cc(x).bag||{})[k]||['🎒',k];
const ALG=(x,k)=>(cc(x).allergens||{})[k]||k;
const PREP=(x,k)=>(cc(x).prep||{})[k]||['✂️',k];
const needsPrep=(x,k)=>{const p=FOOD(x,k).prep;return p==='cool'||p==='bone'||(p==='cut'&&!!fam(x).young);};
const slotOf=t=>Number(String(t.id).split('-').pop());
/** The one button that sends this command with this payload (what a pointer arrow lands on). */
const ctl=(cmd,payload)=>`[data-command="${cmd}"][data-payload='${JSON.stringify(payload)}']`;
const pressed=(html,on)=>html.replace('<button ',`<button aria-pressed="${on}" `);

/* ------------------------------------------------------------ the child and the day */
function noteChips(x){
  const f=fam(x),td=data(x).today||{};
  if(!td.note)return '<p class="small muted bm-note-hide">📝 Giấy dặn chưa đọc</p>';
  const chip=(s,cls='')=>`<span class="bm-chip ${cls}">${s}</span>`;
  return `<p class="bm-chips">${chip(f.allergy?`⚠️ Dị ứng ${x.esc(ALG(x,f.allergy))}`:'✅ Không dị ứng','warn')}${chip(`😴 Ngủ ${x.esc(f.nap||'')}`)}${chip(`${x.esc(LOVEY(x,f.lovey)[0])} ${x.esc(LOVEY(x,f.lovey)[1])}`)}${chip(f.screen?`📺 ${f.screen} phút, sau ngủ trưa`:'📺 Không màn hình')}</p>`;
}
function kidCard(t,x){
  const f=fam(x),who=x.npc(t.npc),tm=(cc(x).tempers||{})[f.temper]||['🙂',''];
  return `<article class="card bm-kid"><div class="row">${x.portrait(who,44)}<div class="grow"><h3>👶 Bé ${x.esc(f.kid||'')} <small class="muted">· ${x.esc(f.age||'')} · ${x.esc(tm[0])} ${x.esc(tm[1])}</small></h3>
    <p class="small bm-open">${x.esc(t.opening||'')}</p>${noteChips(x)}</div></div></article>`;
}
/** The day as a row of chips: what is done, what is now, what is next. */
function planRow(t,x){
  const plan=data(x).plan||[],now=slotOf(t);
  return `<ol class="bm-plan" aria-label="Lịch trong ngày">${plan.map((p,i)=>{const k=KIND[p.kind]||['•',p.kind];
    return `<li class="${i<now?'done':i===now?'now':''}"><span aria-hidden="true">${i<now?'✓':k[0]}</span><b>${x.esc(p.time)}</b><small>${x.esc(k[1])}</small></li>`;}).join('')}</ol>`;
}
function learnLine(x){
  const l=data(x).learn;if(!l?.on)return '';
  return `<p class="bm-learn" aria-label="Học nghề">📞 Học nghề · ngày ${Math.min(l.n+1,l.of)}/${l.of} · <b>${x.esc(l.title||'')}</b></p>`;
}

/* ------------------------------------------------------------ the blocks */
function arrivePanel(t,x){
  const st=t.st||{},n=need(t);
  const chores=`<div class="tile-grid bm-chores">${tile(x,'bm_wash',{task:t.id},'<span class="tile-emoji">🧼</span><b>Rửa tay</b>',st.wash?'selected':'')}
    ${tile(x,'bm_note',{task:t.id},'<span class="tile-emoji">📝</span><b>Đọc giấy dặn</b>',st.note?'selected':'')}
    ${tile(x,'bm_bag',{task:t.id},'<span class="tile-emoji">🎒</span><b>Mở túi đồ</b>',st.bag?'selected':'')}</div>`;
  const greets=Object.entries(cc(x).greets||{}).map(([k,[e,l]])=>tile(x,'bm_greet',{task:t.id,greet:k},`<span class="tile-emoji">${x.esc(e)}</span><b>${x.esc(l)}</b>`,st.greet===k?'selected':'',st.greet!=null)).join('');
  const have=(n.bag||[]).filter(k=>k!==n.missing);
  const bag=st.bag?`<h4 class="section-title">🎒 Trong túi</h4><p class="bm-bagin">${have.map(k=>`<span>${x.esc(BAGI(x,k)[0])} ${x.esc(BAGI(x,k)[1])}</span>`).join('')}${st.ask?`<span class="got">${x.esc(BAGI(x,st.ask)[0])} ${x.esc(BAGI(x,st.ask)[1])}</span>`:''}</p>
    <h4 class="section-title">🙋 Túi của ${x.esc(kidName(x))} cần có <small class="muted">chạm món còn thiếu để hỏi</small></h4>
    <div class="tile-grid bm-need">${(n.bag||[]).map(k=>tile(x,'bm_ask',{task:t.id,item:k},`<span class="tile-emoji">${x.esc(BAGI(x,k)[0])}</span><b>${x.esc(BAGI(x,k)[1])}</b>`,st.ask===k?'selected':'',!!st.ask)).join('')}</div>`:'';
  return `<section class="card bm-arrive"><h4>👋 Đón ${x.esc(kidName(x))}</h4>${chores}
    <h4 class="section-title">🙂 Chào bé</h4><div class="tile-grid bm-greets">${greets}</div>${bag}</section>`;
}
function foodPanel(t,x){
  const st=t.st||{},n=need(t),plate=st.plate||[],full=plate.length>=(n.groups||[]).length+1;
  const tags=k=>{const v=FOOD(x,k),bits=[];if(v.al?.length)bits.push(`có ${v.al.map(a=>ALG(x,a)).join(', ')}`);if(v.hard)bits.push('cứng, hạt nhỏ');return bits.join(' · ');};
  const menu=(n.menu||[]).map(k=>{const v=FOOD(x,k),on=plate.includes(k),tg=tags(k);
    return pressed(tile(x,'bm_food',{task:t.id,food:k},`<span class="tile-emoji">${x.esc(v.emoji)}</span><b>${x.esc(v.name)}</b><small>${x.esc((cc(x).groups||{})[v.group]||'')}</small>${tg?`<small class="bm-al">${x.esc(tg)}</small>`:''}`,on?'selected':'',!on&&full),on);}).join('');
  const dish=plate.map(k=>{const v=FOOD(x,k),p=v.prep,done=(st.prep||[]).includes(k);
    return `<li><span>${x.esc(v.emoji)} ${x.esc(v.name)}</span>${p?(done?`<span class="tag green">✓ ${x.esc(PREP(x,p)[1])}</span>`:x.cmd(`${x.esc(PREP(x,p)[0])} ${x.esc(PREP(x,p)[1])}`,'bm_prep',{task:t.id,food:k},'small bm-prep')):''}</li>`;}).join('');
  const groups=(n.groups||[]).map(g=>`${x.esc((cc(x).groups||{})[g]||g)}`).join(' + ');
  return `<section class="card bm-food"><h4>🍽️ Bàn bếp <small class="muted">${groups}</small></h4><div class="tile-grid bm-menu">${menu}</div>
    <h4 class="section-title">🥣 Đĩa của bé</h4>${plate.length?`<ul class="bm-plate">${dish}</ul>`:'<p class="small muted">Chạm món trên bàn bếp để lấy ra đĩa.</p>'}
    <div class="sk-row">${x.cmd(st.kidwash?'✓ Đã rửa tay bé':'🧼 Rửa tay cho bé','bm_kidwash',{task:t.id},`bm-kidwash ${st.kidwash?'ghost':''}`,!!st.kidwash)}${x.cmd(st.seat?'✓ Bé ngồi ghế':'🪑 Cho bé ngồi ghế ăn','bm_seat',{task:t.id},`bm-seat ${st.seat?'ghost':''}`,!!st.seat)}</div></section>`;
}
function playPanel(t,x){
  const st=t.st||{},n=need(t),mood=(cc(x).moods||{})[n.mood]||['🙂',''],np=Number(cc(x).play_beats||3);
  const acts=(n.acts||[]).map(k=>{const a=ACT(x,k),tg=[a.small?'mảnh nhỏ':'',a.screen?'màn hình':''].filter(Boolean).join(' · ');
    return tile(x,'bm_play',{task:t.id,act:k},`<span class="tile-emoji">${x.esc(a.emoji)}</span><b>${x.esc(a.name)}</b>${tg?`<small>${x.esc(tg)}</small>`:''}`,st.act===k?'selected':'',!!st.act);}).join('');
  let beat='';
  if(st.act&&st.beat<np){
    const b=(cc(x).beats||{})[n.beats?.[st.beat]]||{line:'',opts:[]},order=n.order?.[st.beat]||[0,1,2];
    beat=`<div class="bm-beat"><p class="bm-say">💬 ${x.esc(b.line)}</p><div class="sk-opts">${order.map(i=>b.opts[i]).filter(Boolean).map(o=>x.cmd(`<span class="sk-opt-label">${x.esc(o[1])}</span>`,'bm_beat',{task:t.id,opt:o[0]},'sk-opt')).join('')}</div></div>`;
  }
  const tidy=st.act&&st.beat>=np&&!ACT(x,st.act).screen?`<div class="sk-row">${x.cmd(st.tidy?'✓ Đã dọn đồ chơi':'🧺 Cùng bé dọn đồ chơi','bm_tidy',{task:t.id},`bm-tidy ${st.tidy?'ghost':''}`,!!st.tidy)}</div>`:'';
  return `<section class="card bm-play"><p class="bm-mood"><span aria-hidden="true">${x.esc(mood[0])}</span> ${x.esc(mood[1])}</p>
    ${st.act?`<p class="small">Bé vui ${meter(st.joy||0,100,'bm-joy')}<b>${Number(st.joy||0)}%</b></p>`:''}
    <h4 class="section-title">🧸 Kệ đồ chơi</h4><div class="tile-grid bm-acts">${acts}</div>${beat}${tidy}</section>`;
}
function safetyPanel(t,x){
  const st=t.st||{},n=need(t),fixed=st.fixed||[],wrong=st.wrong||[];
  const room=(n.items||[]).map(k=>{const h=HAZ(x,k),f=fixed.includes(k),w=wrong.includes(k);
    return tile(x,'bm_check',{task:t.id,item:k},`<span class="tile-emoji">${f?'✅':x.esc(h.emoji)}</span><b>${x.esc(h.name)}</b>${f?`<small>${x.esc(h.fix)}</small>`:w?'<small>an toàn</small>':''}`,f?'selected':w?'bm-ok':'',f||w);}).join('');
  return `<section class="card bm-safety"><h4>🔌 ${x.esc((cc(x).homes||{})[n.home]||'Phòng khách')} <small class="muted">đã xử lý ${fixed.length} chỗ</small></h4>
    <p class="small muted">Ngồi ngang tầm bé: chạm vào chỗ dễ nguy hiểm.</p><div class="tile-grid bm-room">${room}</div></section>`;
}
function napPanel(t,x){
  const st=t.st||{},n=need(t),b=t.breath||{cycle:4,lo:.5,hi:.85,need:3},steps=cc(x).nap_steps||{};
  const step=k=>x.cmd(`${st[k]?'✓':x.esc((steps[k]||['•'])[0])} ${x.esc((steps[k]||['',k])[1])}`,'bm_nap',{task:t.id,step:k},`bm-step ${st[k]?'ghost':''}`,!!st[k]);
  const loveys=(n.loveys||[]).map(k=>tile(x,'bm_lovey',{task:t.id,item:k},`<span class="tile-emoji">${x.esc(LOVEY(x,k)[0])}</span><b>${x.esc(LOVEY(x,k)[1])}</b>`,st.lovey===k?'selected':'',!!st.lovey)).join('');
  const lo=(b.lo*100).toFixed(1),w=((b.hi-b.lo)*100).toFixed(1),asleep=Number(st.good||0)>=b.need;
  const gauge=st.pat!=null&&!asleep?`<div class="bm-breath" data-bm-pat="${Number(st.pat)}" data-cycle="${b.cycle}" data-lo="${b.lo}" data-hi="${b.hi}">
      <p class="bm-breath-say"><span class="bm-face" aria-hidden="true">😪</span> <b data-bm-say>…</b></p>
      <div class="bm-track" aria-hidden="true"><i class="bm-zone" style="left:${lo}%;width:${w}%"></i><span class="bm-needle"><i></i></span></div>
      ${x.cmd('🤲 Vỗ nhẹ','bm_pat',{task:t.id},'primary big bm-pat').replace('<button ','<button data-fd-wait=".bm-breath.ready" ')}</div>`:'';
  return `<section class="card bm-nap"><h4>😴 Phòng ngủ <small class="muted">${asleep?'bé ngủ say':`ngủ ${Number(st.good||0)}/${b.need}`}</small></h4>
    <div class="sk-row">${step('potty')}${step('dark')}${step('song')}</div>
    <h4 class="section-title">🧸 Đồ ôm của ${x.esc(kidName(x))}</h4><div class="tile-grid bm-loveys">${loveys}</div>${gauge}
    ${st.pat==null?'<p class="small muted">Tắt đèn, đưa đúng đồ ôm, bé nằm yên rồi mới vỗ.</p>':''}</section>`;
}
function momentPanel(t,x){
  const st=t.st||{},n=need(t),mv=(cc(x).moves||{})[n.mk]||{},used=st.used||[];
  const moves=(n.moves||[]).map(k=>{const m=mv[k]||['•',k];return tile(x,'bm_care',{task:t.id,move:k},`<span class="tile-emoji">${x.esc(m[0])}</span><b>${x.esc(m[1])}</b>`,used.includes(k)?'selected':'',used.includes(k)||st.calm>=100);}).join('');
  return `<section class="card bm-moment"><h4>💛 ${x.esc(((cc(x).moment_title||{})[n.mk])||'')}</h4>
    <p class="small">Bé bình tĩnh ${meter(st.calm||0,100,'bm-calm')}<b>${Number(st.calm||0)}%</b></p><div class="tile-grid bm-moves">${moves}</div></section>`;
}
function handoverPanel(t,x){
  const d=data(x),st=t.st||{},ticks=st.ticks||[],pay=d.pay;
  const lines=(d.log||[]).map(l=>{const on=ticks.includes(l.id);
    return `<li>${pressed(x.cmd(`<span aria-hidden="true">${on?'✍️':'○'}</span> ${x.esc(l.text)}`,'bm_log',{task:t.id,line:l.id},`bm-line ${on?'on':''}`),on)}</li>`;}).join('');
  const money=pay?`<p class="small bm-pay">💵 Công ${pay.rate} xu${pay.loyal?` · khách quen +${pay.loyal}`:''}${pay.bonus?` · chăm kỹ +${pay.bonus}`:''} · chăm kỹ ${pay.care}%</p>`:'';
  return `<section class="card bm-hand"><h4>📝 Nhật ký trong ngày <small class="muted">chỉ ghi chuyện có thật</small></h4><ul class="bm-log">${lines}</ul>${money}</section>`;
}
const PANEL={arrive:arrivePanel,snack:foodPanel,meal:foodPanel,play:playPanel,safety:safetyPanel,nap:napPanel,moment:momentPanel,handover:handoverPanel};

/* ------------------------------------------------------------ the guide */
function stepsOf(t,x){
  const st=t.st||{},n=need(t),f=fam(x),first=firstTime(x)&&t.kind==='arrive';
  // The first block ever: the button does the step; later: it only points at the control.
  const go=(cmd,payload,label,sel)=>first?{cmd,payload,label}:{sel:sel||ctl(cmd,payload),label};
  const id=t.id,rows=[];
  if(t.kind==='arrive'){
    const right=((cc(x).tempers||{})[f.temper]||[])[2];
    rows.push({ok:st.wash||null,label:'Rửa tay',go:go('bm_wash',{task:id},'🧼 Rửa tay')});
    rows.push({ok:st.note||null,label:'Đọc giấy dặn',go:go('bm_note',{task:id},'📝 Đọc giấy dặn')});
    rows.push({ok:st.greet?true:null,label:'Chào bé hợp tính',go:first&&right?{cmd:'bm_greet',payload:{task:id,greet:right},label:`${x.esc((cc(x).greets||{})[right]?.[0]||'')} Chào bé`}:{sel:'.bm-greets',label:'👉 Chọn cách chào bé'}});
    rows.push({ok:st.bag||null,label:'Mở túi đồ',go:go('bm_bag',{task:id},'🎒 Mở túi đồ')});
    if(st.bag)rows.push({ok:st.ask?true:null,label:'Hỏi món còn thiếu',go:first&&n.missing?{cmd:'bm_ask',payload:{task:id,item:n.missing},label:`🙋 Hỏi xin ${x.esc(lower(BAGI(x,n.missing)[1]))}`}:{sel:'.bm-need',label:'👉 Hỏi món còn thiếu'}});
    return {steps:rows,final:{label:'👶 NHẬN BÉ',go:finalGo(rows,'bm_take',{task:id}),ready:true}};
  }
  if(t.kind==='snack'||t.kind==='meal'){
    const plate=st.plate||[];
    for(const g of n.groups||[])rows.push({ok:plate.some(k=>FOOD(x,k).group===g)||null,label:(cc(x).groups||{})[g]||g,go:{sel:'.bm-menu',label:`👉 Chọn ${x.esc(lower((cc(x).groups||{})[g]||g))}`}});
    for(const k of plate)if(needsPrep(x,k)&&!(st.prep||[]).includes(k))rows.push({ok:null,label:`${PREP(x,FOOD(x,k).prep)[1]} ${lower(FOOD(x,k).name)}`,go:{sel:ctl('bm_prep',{task:id,food:k}),label:`${x.esc(PREP(x,FOOD(x,k).prep)[0])} ${x.esc(PREP(x,FOOD(x,k).prep)[1])}`}});
    rows.push({ok:st.kidwash||null,label:'Rửa tay cho bé',go:{sel:'.bm-kidwash',label:'🧼 Rửa tay cho bé'}});
    rows.push({ok:st.seat||null,label:'Cho bé ngồi ghế ăn',go:{sel:'.bm-seat',label:'🪑 Cho bé ngồi ghế'}});
    return {steps:rows,final:{label:'🍽️ DỌN CHO BÉ ĂN',go:finalGo(rows,'bm_serve',{task:id}),ready:plate.length>0,why:'chọn món cho bé'}};
  }
  if(t.kind==='play'){
    const np=Number(cc(x).play_beats||3);
    rows.push({ok:st.act?true:null,label:'Chọn trò hợp tâm trạng bé',go:{sel:'.bm-acts',label:'👉 Chọn trò chơi'}});
    if(st.act&&st.beat<np)rows.push({ok:null,label:'Chơi cùng bé',note:`${st.beat}/${np}`,go:{sel:'.bm-beat',label:'👉 Trả lời bé'}});
    if(st.act&&st.beat>=np&&!ACT(x,st.act).screen)rows.push({ok:st.tidy||null,label:'Cùng bé dọn đồ chơi',go:{sel:'.bm-tidy',label:'🧺 Dọn đồ chơi'}});
    return {steps:rows,final:{label:'✅ CHƠI XONG',go:finalGo(rows,'bm_play_done',{task:id}),ready:!!st.act&&st.beat>=np,why:'chơi với bé thêm chút nữa'}};
  }
  if(t.kind==='safety'){
    const seen=(st.fixed||[]).length+(st.wrong||[]).length;
    rows.push({ok:seen?true:null,label:'Chạm chỗ dễ nguy hiểm',note:`đã xử lý ${(st.fixed||[]).length}`,go:{sel:'.bm-room',label:'👉 Soát phòng'}});
    return {steps:rows,final:{label:'🛡️ CHO BÉ RA CHƠI',go:finalGo(rows,'bm_safe_done',{task:id}),ready:true}};
  }
  if(t.kind==='nap'){
    const b=t.breath||{need:3},good=Number(st.good||0);
    rows.push({ok:st.potty||null,label:'Cho bé đi vệ sinh',go:{sel:ctl('bm_nap',{task:id,step:'potty'}),label:'🚽 Đi vệ sinh'}});
    rows.push({ok:st.dark||null,label:'Kéo rèm, tắt đèn',go:{sel:ctl('bm_nap',{task:id,step:'dark'}),label:'🌙 Kéo rèm'}});
    rows.push({ok:st.lovey?true:null,label:'Đúng đồ ôm của bé',go:{sel:'.bm-loveys',label:'👉 Chọn đồ ôm'}});
    rows.push({ok:st.song||null,label:'Hát ru',go:{sel:ctl('bm_nap',{task:id,step:'song'}),label:'🎵 Hát ru'}});
    rows.push({ok:good>=b.need||null,label:'Vỗ nhẹ lúc bé thở ra',note:`${good}/${b.need}`,go:st.pat!=null?{sel:'.bm-pat',label:'🤲 Vỗ lúc bé thở ra'}:null});
    return {steps:rows,final:{label:'😴 BÉ NGỦ RỒI',go:finalGo(rows,'bm_nap_done',{task:id}),ready:good>=b.need,why:'vỗ cho bé ngủ say'}};
  }
  if(t.kind==='moment'){
    rows.push({ok:st.calm>=100||null,label:'Dỗ bé tới khi bé ổn',note:`${Number(st.calm||0)}%`,go:{sel:'.bm-moves',label:'👉 Chọn cách dỗ'}});
    return {steps:rows,final:{label:'💛 BÉ ỔN RỒI',go:finalGo(rows,'bm_moment_done',{task:id}),ready:st.calm>=100,why:'dỗ bé thêm'}};
  }
  rows.push({ok:(st.ticks||[]).length?true:null,label:'Ghi nhật ký thật',go:{sel:'.bm-log',label:'👉 Ghi nhật ký'}});
  return {steps:rows,final:{label:'👋 BÀN GIAO BÉ',go:finalGo(rows,'bm_hand',{task:id}),ready:true}};
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở nhà bé',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'bm_intro',payload:{},label:'👶 Vào việc thôi!'}}],final:null};
  return stepsOf(t,x);
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null});

/* ------------------------------------------------------------ the parents' notes (dock page) and the families */
function notes(x){
  const d=data(x),f=fam(x),fams=d.fams||{};
  const known=Object.entries(fams).map(([k,v])=>`<li>👪 ${x.esc(k===f.id?`Bé ${f.kid}`:k)} · ${Number(v.visits)} ngày · ${'💛'.repeat(Number(v.trust)||0)||'mới quen'}</li>`).join('');
  return `<section class="card bm-notes"><h4>📝 Giấy dặn hôm nay · bé ${x.esc(f.kid||'')} (${x.esc(f.age||'')})</h4>${noteChips(x)}
    <p class="small muted">Bố mẹ: ${x.esc(f.parent||'')}</p>${known?`<h4 class="section-title">Các gia đình</h4><ul class="small bm-fams">${known}</ul>`:''}</section>`;
}
const wrap=inner=>`<div class="career-job sk bm">${inner}</div>`;
const top=x=>`${introCard(x,'bm_intro','👶')}${deskCard(x,'bm_desk','Chuyện ở nhà bé')}`;
function gate(x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở nhà bé',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'bm_intro',payload:{},label:'👶 Vào việc thôi!'}}],final:null};
}

export default {
  id:'babysitter',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed line below */}
    return (KIND[t.kind]||['','Trông bé'])[1];
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    if(d.desk?.ev||!d.intro||x.ui.intro)return wrap(`${hint}${top(x)}${bottom(x,g)}`);
    const panel=(PANEL[t.kind]||handoverPanel)(t,x);
    const side=stepRows(x,g.steps,'Việc của bước này');
    return wrap(`${hint}${top(x)}${learnLine(x)}${kidCard(t,x)}${planRow(t,x)}<div class="workbench"><section class="wb-main">${panel}</section><aside class="wb-side">${side}</aside></div>${dayBar(x)}${bottom(x,g)}`);
  },
  idle(x){
    const d=data(x);
    if(d.desk?.ev||!d.intro||x.ui.intro){const g=gate(x);return wrap(`${hintFor(g,x)}${top(x)}${bottom(x,g)}`);}
    return wrap(`${top(x)}${dayBar(x)}${notes(x)}`);
  },
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'bm',eyebrow:'Tổ trông trẻ Mèo Con',title:'📝 Giấy dặn của bố mẹ',body:notes(x)}):'';},
  // The nap's breath bar glides on the compositor (ctx.slide); the words and the ready cue follow it.
  meters(root,x){
    const box=root.querySelector('[data-bm-pat]');if(!box)return;
    const cyc=Number(box.dataset.cycle)||4,lo=Number(box.dataset.lo),hi=Number(box.dataset.hi);
    const el=x.now()-Number(box.dataset.bmPat),ph=((el%cyc)+cyc)%cyc/cyc;
    x.slide(box.querySelector('.bm-needle'),ph*100,100/cyc);
    const ready=ph>=lo&&ph<=hi,say=ph<.5?'Bé hít vào…':ready?'Bé thở ra chậm: vỗ nhẹ!':'Đợi nhịp thở sau…';
    const line=box.querySelector('[data-bm-say]');if(line&&line.textContent!==say)line.textContent=say;
    const face=box.querySelector('.bm-face'),fe=ready?'😌':'😪';if(face&&face.textContent!==fe)face.textContent=fe;
    box.classList.toggle('ready',ready);
  },
  tapStop:op=>op==='bm_pat',
  tick(root){keepBarAboveFooter(root);},
  summary(sum,x){
    if(!sum||sum.care==null||sum.kid==null)return '';
    const tm=sum.tomorrow,row=(l,v)=>`<div class="kv-row"><span>${l}</span><b>${v}</b></div>`;
    const plan=`<section class="bm-tomorrow" aria-label="Ngày mai"><h4 class="section-title">🌅 Ngày mai</h4>${tm?`<p><span aria-hidden="true">${x.esc(tm.emoji)}</span> <b>${x.esc(tm.label)}</b> <small class="muted">${x.esc(tm.hint)}</small></p>`:''}${sum.note?`<p class="small">${x.esc(sum.note)}</p>`:''}</section>`;
    const kv=`<div class="kv">${row('Việc trong ngày',sum.blocks)}${row('Chăm kỹ',`${sum.care}%`)}${row('Bàn giao',sum.handed?'✓':'—')}</div>${(sum.lines||[]).length?`<ul class="small">${sum.lines.map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul>`:''}`;
    return `<article class="card space-top bm-sum">${plan}<details class="bm-sum-more"><summary>👶 Bé ${x.esc(sum.kid)} hôm nay · chăm kỹ ${sum.care}%</summary>${kv}</details></article>`;
  },
  actions:{...kitActions,async notes(d,el,x){x.render();setTimeout(()=>document.querySelector('.bm-kid')?.scrollIntoView({block:'center'}),0);}},
  dock:[['car:notes','book','Giấy dặn của bố mẹ','Dị ứng, giờ ngủ, đồ ôm'],['car:intro','question','Giới thiệu nghề','Công việc & sao']],
};
