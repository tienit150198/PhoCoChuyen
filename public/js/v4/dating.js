/** 💕 Góc hẹn hò: the dating bench and the 5-minute café date (the rules, the clock and the matcher are the live
 * service's: live/dating.py; this file only draws). Its own dialog, opened from the menu entry, the heart in the
 * chat, the "💕" pill on the scene while waiting or on a date, and (phase 2) a bench spot in the street scene
 * (attachBench). A match opens the dialog by itself.
 * No guide, no tips (owner, 01/10): icons, short labels, one line where a line is needed. Player text is always
 * escaped and marked data-no-translate. */
import {icon,escapeHTML as esc} from '../icons.js';
import {live} from './live.js';
import {stylesheet} from '../lazy.js';

const S={dlg:null,env:null,bound:false,bench:{state:'idle',n:0,waited:0,at:0,pref:'any'},pref:pref0(),date:null,at:0,end:null,
  msgs:[],want:null,menu:false,report:false,confirm:null,flash:'',flashTimer:0,tick:0,pill:null,spots:new Set(),busy:false};
const PREFS=[['m','👦','Bạn nam'],['f','👧','Bạn nữ'],['any','✨','Ai cũng được']];
const REASONS=[['rude','Thô tục'],['spam','Spam'],['scam','Lừa đảo'],['private','Lộ thông tin'],['other','Khác']];
const LINES={nope:'Hôm nay chưa hợp, phố còn đông người mà!',left:'Bạn đã rời buổi hẹn.',gone:'Bạn ấy có việc phải đi trước rồi. Phố còn đông người mà!'};
const rid=()=>Math.random().toString(36).slice(2,10);
function pref0(){try{const v=localStorage.getItem('mnl.datePref');return ['m','f','any'].includes(v)?v:'any';}catch{return 'any';}}
const savePref=v=>{S.pref=v;try{localStorage.setItem('mnl.datePref',v);}catch{/* private mode */}};
const myG=()=>({male:'m',female:'f'})[S.env?.api?.state?.journey?.gender]||null;
const left=()=>S.date?Math.max(0,S.date.left-(Date.now()-S.at)/1000):0;
const mmss=s=>`${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`;
const av=(a,cls='')=>`<span class="dt-av ${cls}" aria-hidden="true">${esc(a||'🌸')}</span>`;
const peer=()=>S.date?.peer||S.end?.peer||{};
const pname=()=>`<b data-no-translate>${esc(peer().name||'Bạn ấy')}</b>`;

/* ---- the dialog ------------------------------------------------------------------------------------------ */
function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium dt-sheet';d.setAttribute('aria-label','Góc hẹn hò');
  d.innerHTML=`<div class="dt-root"><header class="dt-head"></header><div class="dt-net" hidden>${icon('refresh',14)} Đang kết nối lại…</div>
    <div class="dt-body"></div><div class="dt-flash" role="status" aria-live="polite" hidden></div>
    <div class="dt-quick" hidden></div>
    <form class="dt-compose" hidden><input type="text" maxlength="200" enterkeyhint="send" autocomplete="off" aria-label="Tin nhắn" placeholder="Nói gì đó…">
    <button type="submit" class="dt-send" aria-label="Gửi">${icon('send',19)}</button></form></div>`;
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-dt]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onAct(el.dataset.dt,el.dataset);
  });
  d.addEventListener('keydown',e=>{if(e.key==='Escape')e.stopPropagation();});   // closes this only, never pauses the game
  d.addEventListener('close',()=>{S.menu=false;S.report=false;S.confirm=null;S.end=null;clearInterval(S.tick);pill();});   // the end card is seen once
  d.querySelector('.dt-compose').addEventListener('submit',e=>{e.preventDefault();say(d.querySelector('.dt-compose input').value);});
  S.dlg=d;return d;
}

/** Menu entry, chat heart, the scene pill, a street bench: open on whatever is going on (bench, date, end). */
export async function openDate(env,data={}){
  S.env=env;bind();await stylesheet('/css/dating.css');
  const d=dialog();
  if(!d.open){d.showModal();}
  if(live.state==='open'&&!S.date)live.send({t:'queue',op:'peek'});
  if(data.sit&&!S.date&&S.bench.state!=='wait')sit(data.spot);
  render();clock();
}

/* ---- live frames ----------------------------------------------------------------------------------------- */
function bind(){
  if(S.bound)return;S.bound=true;
  // Escape closes this dialog only: focus may sit on <body> after a redraw, where the game's own Escape (pause) would see it
  window.addEventListener('keydown',e=>{if(e.key==='Escape'&&S.dlg?.open)e.stopPropagation();},true);
  live.on('welcome',f=>{welcome(f);paint();});
  live.on('down',()=>paint());
  live.on('bench',f=>{S.bench={...f,at:Date.now()};if(f.state==='wait')S.end=null;paint();});
  live.on('date',f=>{
    const first=!S.date||S.date.id!==f.id;
    if(f.step==='end'){S.end=f;S.date=null;S.msgs=[];S.menu=false;S.report=false;S.confirm=null;S.bench={state:'idle',n:S.bench.n,waited:0,at:Date.now()};
      if(f.how==='match'&&navigator.vibrate)try{navigator.vibrate([30,60,30]);}catch{/* not allowed */}
      paint();return;}
    take(f);
    if(first){S.msgs=[];S.want=null;S.end=null;if(!S.dlg?.open&&S.env)openDate(S.env);}   // a match: the dialog comes up by itself
    paint();
  });
  live.on('msg',f=>{
    if(!S.date||f.ch!=='date:'+S.date.id)return;
    if(!S.msgs.some(m=>m.id===f.id)){S.msgs.push(f);if(S.msgs.length>120)S.msgs.shift();}
    paint(true);
  });
  live.on('reported',f=>{if(f.date){S.report=false;S.menu=false;flash('Đã báo cáo. Cảm ơn bạn!');paint();}});
  live.on('error',f=>{
    if(!S.dlg?.open)return;
    if(['queue','answer','heart','date_say','date_leave','date_block','date_report'].includes(f.ref)||String(f.ref||'').startsWith('dt')){
      if(f.code==='no_date'&&S.date){S.date=null;}
      flash(f.msg||'Không gửi được.');paint();
    }
  });
}
function welcome(f){
  if(f.date)take(f.date);
  else if(S.date){S.end={step:'end',how:'gone',peer:S.date.peer,id:S.date.id,same:S.date.same,of:S.date.of};S.date=null;}   // the service restarted: that date is gone
  S.bench=f.bench?{...f.bench,at:Date.now()}:{state:'idle',n:S.bench.n,waited:0,at:Date.now()};
}
function take(f){S.date=f;S.at=Date.now();if(f.step!=='menu')S.want=null;}

/* ---- actions --------------------------------------------------------------------------------------------- */
function sit(spot){
  if(live.state!=='open'){flash('Mất kết nối, thử lại sau nhé.');return;}
  live.send({t:'queue',op:'sit',pref:S.pref,g:myG(),...(spot?{spot}:{})});
  S.bench={...S.bench,state:'wait',waited:0,at:Date.now(),pref:S.pref};S.end=null;
}
function say(text){
  text=String(text||'').trim();if(!text||!S.date||live.state!=='open')return;
  if(live.send({t:'date_say',date:S.date.id,text,cid:'dt'+rid()})){const i=S.dlg.querySelector('.dt-compose input');i.value='';}
}
function onAct(act,d){
  const D=S.date;
  switch(act){
    case'close':S.dlg.close();return;
    case'pref':savePref(d.v);if(S.bench.state==='wait')sit();break;
    case'sit':sit();break;
    case'stand':live.send({t:'queue',op:'stand'});S.bench={...S.bench,state:'idle'};break;
    case'again':S.end=null;sit();break;
    case'pick':if(!D||D.mine!=null||D.shown)return;D.mine=Number(d.i);live.send({t:'answer',date:D.id,step:'card',i:D.i,pick:Number(d.i)});break;
    case'want':if(!D||D.give)return;S.want=d.id;break;
    case'give':if(!D||D.give||!S.want)return;D.want=S.want;D.give=d.id;live.send({t:'answer',date:D.id,step:'menu',want:S.want,give:d.id});break;
    case'unwant':S.want=null;break;
    case'quick':say(d.text);return;
    case'chatDone':if(D){D.done=true;live.send({t:'answer',date:D.id,step:'chat'});}break;
    case'vote':if(!D||D.mine)return;D.mine=d.v;live.send({t:'heart',date:D.id,v:d.v});break;
    case'menu':S.menu=!S.menu;S.report=Boolean(S.end);S.confirm=null;break;
    case'report':S.report=true;break;
    case'reason':{const id=D?.id||S.end?.id;if(id)live.send({t:'date_report',date:id,reason:d.r});break;}
    case'block':if(S.confirm!=='block'){S.confirm='block';break;}if(D)live.send({t:'date_block',date:D.id});S.menu=false;S.confirm=null;break;
    case'leave':if(S.confirm!=='leave'){S.confirm='leave';break;}if(D)live.send({t:'date_leave',date:D.id});S.menu=false;S.confirm=null;break;
    case'dm':S.dlg.close();import('./live.js').then(m=>m.openChat({ch:dmId(d.pid)}));return;
    case'retry':live.reconnect();break;
  }
  render();
}
const dmId=pid=>{const [a,b]=[live.me?.pid,pid].sort();return `dm:${a}:${b}`;};

/* ---- drawing --------------------------------------------------------------------------------------------- */
function flash(text){S.flash=text;clearTimeout(S.flashTimer);S.flashTimer=setTimeout(()=>{S.flash='';const f=S.dlg?.querySelector('.dt-flash');if(f)f.hidden=true;},3500);}
function paint(toBottom=false){pill();spots();if(S.dlg?.open){render(toBottom);clock();}}

function head(){
  const x=`<button type="button" class="icon-btn" data-dt="close" aria-label="Đóng">${icon('x',20)}</button>`;
  const D=S.date;
  if(!D)return `<span class="dt-logo" aria-hidden="true">${icon('heart',18)}</span><h2 class="grow">Góc hẹn hò</h2>${x}`;
  const p=D.peer||{};
  return `${av(p.av,'md')}<div class="grow dt-who"><h2 data-no-translate>${esc(p.name||'Bạn ấy')}</h2><small>${steps(D)}</small></div>`+
    `<span class="dt-clock" aria-label="Còn lại"><b>${mmss(left())}</b></span>`+
    `<button type="button" class="icon-btn" data-dt="menu" aria-label="Thêm" aria-expanded="${S.menu}">${icon('menu',19)}</button>${x}`;
}
function steps(D){
  const order=['hello','card','menu','chat','vote'],at=order.indexOf(D.step);
  return `<span class="dt-steps" aria-hidden="true">${order.slice(1).map((s,k)=>`<i class="${k+1<at?'done':k+1===at?'on':''}"></i>`).join('')}</span>`+
    (D.cards?.length?` Hợp nhau ${D.same}/${D.of}`:'');
}

function safety(){
  if(!S.menu)return '';
  if(S.report)return `<div class="dt-menu" role="menu"><p>Báo cáo vì…</p><div class="dt-chips">${REASONS.map(([k,l])=>`<button type="button" class="dt-chip" data-dt="reason" data-r="${k}">${l}</button>`).join('')}</div></div>`;
  return `<div class="dt-menu" role="menu"><button type="button" class="dt-mi" data-dt="report">${icon('flag',16)} Báo cáo</button>`+
    `<button type="button" class="dt-mi warn" data-dt="block">${icon('shield',16)} ${S.confirm==='block'?'Chặn thật?':'Chặn'}</button>`+
    `<button type="button" class="dt-mi" data-dt="leave">${icon('exit',16)} ${S.confirm==='leave'?'Rời thật?':'Rời buổi hẹn'}</button></div>`;
}

function bench(){
  const B=S.bench,wait=B.state==='wait';
  const prefs=`<div class="dt-prefs" role="radiogroup" aria-label="Muốn gặp">${PREFS.map(([v,e,l])=>`<button type="button" role="radio" aria-checked="${S.pref===v}" class="dt-pref${S.pref===v?' on':''}" data-dt="pref" data-v="${v}"><span aria-hidden="true">${e}</span>${l}</button>`).join('')}</div>`;
  if(wait){
    const secs=(B.waited||0)+(Date.now()-(B.at||Date.now()))/1000;
    return `<div class="dt-bench wait"><div class="dt-scene" aria-hidden="true"><span class="dt-seat">🪑</span><span class="dt-cup">☕</span><span class="dt-dots"><i></i><i></i><i></i></span></div>`+
      `<p class="dt-big" role="timer" aria-live="off"><b class="dt-wait">${mmss(secs)}</b></p><p class="dt-line">Đang tìm người hợp gu…</p>${prefs}`+
      `<button type="button" class="btn ghost full" data-dt="stand">Đứng dậy</button></div>`;
  }
  const g=myG();
  return `<div class="dt-bench"><div class="dt-scene" aria-hidden="true"><span class="dt-seat">🪑</span><span class="dt-cup">☕</span><span class="dt-heart">💕</span></div>`+
    `<p class="dt-line"><b>Hẹn 5 phút ở quán cà phê</b></p>${prefs}`+
    `<button type="button" class="btn primary full dt-go" data-dt="sit"${live.state!=='open'?' disabled':''}>${icon('chair',18)} Ngồi chờ</button>`+
    (B.n?`<p class="dt-n">${icon('people',14)} ${B.n} người đang chờ</p>`:'')+(g?'':`<p class="dt-n">Chọn Nam/Nữ cho nhân vật để người khác tìm thấy bạn.</p>`)+`</div>`;
}

function endView(){
  const E=S.end,p=E.peer||{},sum=`<p class="dt-sum">Hợp nhau ${E.same||0}/${E.of||3}${E.hits!=null?` · Gọi trúng món ${E.hits}/2`:''}</p>`;
  if(E.how==='match'){
    const chips=[E.spirit?`<span class="dt-tag good">+${E.spirit} tinh thần</span>`:'',E.friends?`<span class="dt-tag">Đã là bạn bè</span>`:''].join('');
    return `<div class="dt-end match"><div class="dt-pair" aria-hidden="true">${av(live.me?.av,'lg')}<span class="dt-beat">💕</span>${av(p.av,'lg')}</div>`+
      `<h3>Đang tìm hiểu 💕</h3><p class="dt-line">${pname()} cũng thả tim!</p>${chips?`<div class="dt-tags">${chips}</div>`:''}${sum}`+
      `<div class="dt-actions">${E.friends?`<button type="button" class="btn primary" data-dt="dm" data-pid="${esc(p.pid||'')}">${icon('chat',16)} Nhắn tin</button>`:''}<button type="button" class="btn ghost" data-dt="again">Ngồi ghế tiếp</button></div></div>`;
  }
  return `<div class="dt-end"><div class="dt-leaf" aria-hidden="true">🍃</div><p class="dt-line">${esc(LINES[E.how]||LINES.nope)}</p>${E.how==='nope'?sum:''}`+
    `<div class="dt-actions"><button type="button" class="btn primary" data-dt="again">${icon('chair',16)} Ngồi ghế tiếp</button><button type="button" class="btn ghost" data-dt="close">Đóng</button></div></div>`+
    (E.how!=='left'?`<button type="button" class="dt-report-link" data-dt="menu">${icon('flag',13)} Báo cáo</button>`:'');
}

function cardView(D){
  const shown=D.shown,their=shown?D.cards[D.i]?.them:null,mine=D.mine;
  const opts=D.opts.map((o,k)=>{
    const me=mine===k,th=shown&&their===k;
    return `<button type="button" class="dt-opt${me?' me':''}${th?' them':''}${mine!=null&&!me&&!th?' dim':''}" data-dt="pick" data-i="${k}"${mine!=null||shown?' aria-disabled="true"':''}>`+
      `<span>${esc(o)}</span>${me||th?`<span class="dt-who-picked">${me?av(live.me?.av,'xs'):''}${th?av(D.peer?.av,'xs'):''}</span>`:''}</button>`;
  }).join('');
  const verdict=shown?(mine!=null&&mine===their?'<p class="dt-verdict good">Hợp nhau! 💞</p>':their==null?'<p class="dt-verdict">Bạn ấy chưa kịp chọn 😴</p>':'<p class="dt-verdict">Khác gu 😆</p>'):
    mine!=null?`<p class="dt-wait-line">${D.peer_done?`${icon('check',14)} ${pname()} chọn rồi`:`Chờ ${pname()}…`}</p>`:'';
  return `<p class="dt-kicker">Câu ${D.i+1}/${D.of}</p><h3 class="dt-q">${esc(D.q)}</h3><div class="dt-opts">${opts}</div>${verdict}`;
}

function menuView(D){
  const item=m=>`${esc(m.emo)} ${esc(m.name)}`;
  if(D.shown&&D.order){
    const o=D.order,hitMe=o.they_gave&&o.i_want&&o.they_gave.id===o.i_want.id,hitThem=o.i_gave&&o.they_want&&o.i_gave.id===o.they_want.id;
    const row=(who,got,want,hit)=>`<div class="dt-order${hit?' hit':''}"><p class="dt-o-who">${who}</p><p class="dt-o-got">${got?item(got):'—'}</p><p class="dt-o-res">${hit?'Trúng phóc! 🎯':want?`thèm ${item(want)} cơ 😅`:'chưa kịp gọi'}</p></div>`;
    return `<p class="dt-kicker">Chọn món cho nhau</p>${row(`${pname()} gọi cho bạn`,o.they_gave,o.i_want,hitMe)}${row(`Bạn gọi cho ${pname()}`,o.i_gave,o.they_want,hitThem)}`;
  }
  if(D.give)return `<p class="dt-kicker">Chọn món cho nhau</p><div class="dt-done-pick"><span class="dt-emo">${esc(D.menu.find(m=>m.id===D.give)?.emo||'🍽️')}</span><p>${D.peer_done?`${icon('check',14)} ${pname()} gọi xong rồi`:`Chờ ${pname()} gọi món…`}</p></div>`;
  const giving=Boolean(S.want),act=giving?'give':'want';
  const grid=D.menu.map(m=>`<button type="button" class="dt-dish${S.want===m.id&&!giving?' on':''}" data-dt="${act}" data-id="${esc(m.id)}"><span class="dt-emo">${esc(m.emo)}</span><span>${esc(m.name)}</span></button>`).join('');
  return `<p class="dt-kicker">Chọn món cho nhau · ${giving?'2':'1'}/2</p><h3 class="dt-q">${giving?`Gọi gì cho ${pname()}?`:'Bạn đang thèm món gì?'}</h3>`+
    (giving?`<button type="button" class="dt-back" data-dt="unwant">${icon('chevron',14,'dt-back-ico')} Bạn thèm: ${esc(D.menu.find(m=>m.id===S.want)?.emo||'')}</button>`:'')+`<div class="dt-menu-grid">${grid}</div>`;
}

function chatView(D){
  const mine=live.me?.pid;
  const list=S.msgs.map(m=>`<div class="dt-msg${m.pid===mine?' mine':''}"><span class="dt-bub" data-no-translate>${esc(m.text).replace(/\n/g,'<br>')}</span></div>`).join('');
  return `<div class="dt-chat">${list||`<p class="dt-empty">${icon('chat',22)} Một phút trò chuyện. Mở lời đi!</p>`}</div>`+
    `<button type="button" class="dt-done" data-dt="chatDone"${D.done?' disabled':''}>${D.done?`${icon('check',14)} Chờ bạn ấy…`:'Xong, chọn thôi'}</button>`;
}

function voteView(D){
  if(D.mine)return `<div class="dt-vote-wait"><span class="dt-emo big">${D.mine==='heart'?'❤️':'👋'}</span><p class="dt-line">Đã chọn. Chờ chút…</p></div>`;
  return `<h3 class="dt-q center">Hẹn ${pname()} lần nữa?</h3><p class="dt-line">Chỉ bạn thấy lựa chọn của mình.</p>`+
    `<div class="dt-votes"><button type="button" class="dt-vote heart" data-dt="vote" data-v="heart"><span class="dt-emo big">❤️</span>Hẹn tiếp</button>`+
    `<button type="button" class="dt-vote" data-dt="vote" data-v="wave"><span class="dt-emo big">👋</span>Chào nhé</button></div>`;
}

function body(){
  if(!live.welcomed)return `<div class="dt-end"><p class="dt-line">${icon('refresh',18)} Đang kết nối…</p></div>`;
  const D=S.date;
  if(!D)return S.end?safety()+endView():bench();
  let main='';
  if(D.step==='hello')main=`<div class="dt-hello"><div class="dt-pair" aria-hidden="true">${av(live.me?.av,'lg')}<span class="dt-table">☕</span>${av(D.peer?.av,'lg')}</div><h3>Gặp ${pname()}!</h3><p class="dt-line">5 phút ở quán cà phê phố</p></div>`;
  else if(D.step==='card')main=cardView(D);
  else if(D.step==='menu')main=menuView(D);
  else if(D.step==='chat')main=chatView(D);
  else if(D.step==='vote')main=voteView(D);
  return safety()+`<div class="dt-step" data-step="${D.step}">${main}</div>`;
}

function render(toBottom=false){
  const d=S.dlg;if(!d)return;
  d.querySelector('.dt-head').innerHTML=head();
  d.querySelector('.dt-net').hidden=!(live.welcomed&&live.state!=='open');
  const b=d.querySelector('.dt-body'),atBottom=b.scrollHeight-b.scrollTop-b.clientHeight<60;
  b.innerHTML=body();b.dataset.step=S.date?.step||(S.end?'end':S.bench.state);
  if(S.date?.step==='chat'&&(toBottom||atBottom)){const c=b.querySelector('.dt-chat');if(c)c.scrollTop=c.scrollHeight;b.scrollTop=b.scrollHeight;}
  const chat=S.date?.step==='chat',form=d.querySelector('.dt-compose'),q=d.querySelector('.dt-quick');
  form.hidden=!chat;q.hidden=!chat;
  if(chat&&!q.childElementCount)q.innerHTML=(S.date.quick||[]).map(t=>`<button type="button" class="dt-chip" data-dt="quick" data-text="${esc(t)}">${esc(t)}</button>`).join('');
  if(!chat)q.innerHTML='';
  const f=d.querySelector('.dt-flash');f.hidden=!S.flash;f.textContent=S.flash;
}

/** The clocks (header countdown, waiting timer) without redrawing anything else. */
function clock(){
  clearInterval(S.tick);
  if(!S.dlg?.open)return;
  S.tick=setInterval(()=>{
    if(!S.dlg?.open){clearInterval(S.tick);return;}
    const c=S.dlg.querySelector('.dt-clock b');if(c){const s=left();c.textContent=mmss(s);c.parentElement.classList.toggle('low',s<=10);}
    const w=S.dlg.querySelector('.dt-wait');if(w&&S.bench.state==='wait')w.textContent=mmss((S.bench.waited||0)+(Date.now()-S.bench.at)/1000);
  },250);
}

/* ---- the pill on the scene: waiting or on a date while the dialog is closed --------------------------------- */
function pill(){
  const on=Boolean(live.flags.dating)&&live.welcomed&&!S.dlg?.open&&(S.bench.state==='wait'||Boolean(S.date));
  if(on&&!S.pill){
    S.pill=document.createElement('button');S.pill.type='button';S.pill.className='dt-pill';
    S.pill.addEventListener('click',()=>S.env&&openDate(S.env));
    (document.getElementById('stage')||document.body).append(S.pill);
  }
  if(!S.pill)return;
  S.pill.hidden=!on;
  if(on){S.pill.innerHTML=S.date?`💕 <b data-no-translate>${esc(S.date.peer?.name||'')}</b>`:`🪑 Đang chờ`;S.pill.setAttribute('aria-label',S.date?'Quay lại buổi hẹn':'Góc hẹn hò: đang chờ');}
}

/* ---- phase 2: a bench spot in the street scene ------------------------------------------------------------- */
/** The street scene (live-stroll) hands its "Góc hẹn hò" bench spot here: host = {el: an HTMLElement drawn over the
 * bench, place: 'boho' | 'chodem' | …}. The spot shows the bench state (💕, ⏳ while I wait, the date's peer) and a tap
 * opens the date corner and sits down at once with the last preference (spot `street:<place>`).
 * Returns {update(), destroy()}; the scene calls destroy() when it leaves the place. */
export function attachBench(env,host){
  S.env=env;bind();stylesheet('/css/dating.css');
  const el=host?.el;if(!el)return {update(){},destroy(){}};
  const spot={host,el,click:()=>openDate(env,{sit:S.bench.state!=='wait'&&!S.date,spot:host.place?`street:${String(host.place).toLowerCase().replace(/[^a-z0-9_-]/g,'').slice(0,30)}`:''})};
  el.classList.add('dt-spot');el.setAttribute('role','button');el.tabIndex=0;
  el.addEventListener('click',spot.click);
  spot.key=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();spot.click();}};el.addEventListener('keydown',spot.key);
  S.spots.add(spot);spots();
  return {update:spots,destroy(){S.spots.delete(spot);el.removeEventListener('click',spot.click);el.removeEventListener('keydown',spot.key);el.classList.remove('dt-spot');}};
}
function spots(){
  for(const s of S.spots){
    const on=Boolean(live.flags.dating)&&live.welcomed;
    s.el.hidden=!on;
    s.el.innerHTML=`<span aria-hidden="true">${S.date?'💕':S.bench.state==='wait'?'⏳':'🪑'}</span><small>${S.date?esc(S.date.peer?.name||''):S.bench.state==='wait'?'Đang chờ':'Hẹn hò?'}</small>`;
    s.el.setAttribute('aria-label',S.date?'Quay lại buổi hẹn':'Góc hẹn hò');
  }
}

/** For live.js: a welcome that says I am waiting or on a date (a reload in the middle of one) loads this module;
 * it takes that welcome, draws the pill and opens the date. */
export function datingBoot(env,w){
  S.env=env;bind();
  if(w){welcome(w);if(S.date){openDate(env);return;}}
  stylesheet('/css/dating.css').then(()=>paint());
}
