/** Front-end orchestration. Economic rules live on the Python server, not in chat. */
import {GameAPI} from './api.js';
import {BobaWorld} from './boba-world.js';
import {wordsFor,loadAllScenes} from './scenes/index.js';
loadAllScenes(); // warm the scene kinds so no career flashes the storefront
import {operationsView} from './operations-ui.js';
import {nextStep,lifeNav,guestRibbon,experienceView,extendedJob,experienceSummary} from './experience-ui.js';
import {icon,portrait,itemArt,escapeHTML as esc} from './icons.js';
import {reqList,fold} from './ui-kit.js';
import {Sound} from './audio.js';
import {careerSubmit,careerInput,loadCareerModules,careerUI,careerContext,startTicker} from './v4/careers.js';
import {inventoryView,feedbackView,situationView,jobView as jobAppView,v4Action,v4Submit,v4Input} from './v4/views.js';
import {setLanguage} from './v4/i18n.js';
import {shell} from './v4/shell.js';
import {settingsView as settingsV4,settingsAction,settingsChange,settingsInput} from './v4/settings.js';
import {accountSubmit,accountNudge} from './v4/account.js';
import {socialView,socialAction,socialSubmit,invalidate as socialInvalidate,startSocialPoll} from './v4/social.js';
import {registerWorker,listenWorker} from './v4/push.js';
import {classroomView} from './v4/classroom.js';
import {homeView as homeV4,futureView as futureV4,journeyBoot,journeyAction,journeySubmit} from './v4/home.js';
import {procedureSubmit,procedureAction} from './v4/procedure.js';
import {deskJob,deskDone,deskNext,deskAction} from './desk.js';
import {incidentView,incidentSummary,incidentNote,incidentBadge,incidentAction,incidentBoot} from './v4/incidents.js';
import {happenBoot,happenSummary} from './v4/happenings.js';

const $=s=>document.querySelector(s), api=new GameAPI(), sound=new Sound();
const ended=t=>['completed','referred','cancelled'].includes(t.status);
const ui={opsTab:'staff',staffId:null,lessonSequence:[],tourRoute:[],activityCard:null,view:null,tab:'',task:null,npc:null,jobTab:'shelf',journalTab:'quests',libraryQuery:'',docs:new Set(),transactions:new Set(),drafts:{},ai:{},suggestions:{},busy:false,paused:false};
const world=new BobaWorld($('#world'),interact);
const career=()=>api.state?.current||'mother_baby';
const room=()=>api.state?.careers[career()];
const meta=()=>api.content?.catalogue.find(c=>c.id===career())||{};
const npc=id=>api.content?.npcs.find(n=>n.id===id)||{display_name:api.state?.name||'Bạn',role:'Bạn',personality:''};
const product=id=>api.content.products.find(p=>p.id===id)||api.content.lots.find(p=>p.id===id)||{name:id,price:0,icon:'box',color:'cream'};
const activeTask=()=>room()?.tasks.find(t=>t.id===(ui.task||room().active_task))||room()?.tasks.find(t=>!ended(t));
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const LEGACY=['mother_baby','pharmacy','accounting','customer_care','teacher','tour_guide','milk_tea'];
const plugin=()=>!LEGACY.includes(career());
const env=()=>({api,ui,cmd,confirmAction,toast,renderSheet,openSheet,closeSheet,world});
const needsJob=()=>room()?.job?.required&&room().job.status!=='hired';
const attrs=obj=>Object.entries(obj).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const button=(label,action,data={},style='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}>${label}</button>`;
const commandButton=(label,command,payload={},style='',disabled=false)=>`<button type="button" class="btn ${style}" data-command="${command}" data-payload="${esc(JSON.stringify(payload))}"${disabled?' disabled':''}>${label}</button>`;
const pill=(label,kind='')=>`<span class="tag ${kind}">${label}</span>`;
const empty=(title,text,ico='leaf')=>`<div class="empty">${icon(ico,32)}<h3>${title}</h3><p class="muted small">${text}</p></div>`;
/** Office-type careers talk about files and trays, not customers. */
const deskWork=()=>(meta()?.category||{accounting:'office'}[career()])==='office';
const notice=(text,kind='',ico='leaf')=>`<div class="notice ${kind}">${icon(ico,17)}<div>${text}</div></div>`;
/** kind: true/'error' (red, longer), 'good' (success after a celebrated action), 'hint' (short helper line
 * with a 💡, auto-dismiss) or plain. Same text is never stacked twice. Career desks reach it as env.toast(text,'hint'). */
function toast(message,kind=false){if(!message)return;const box=$('#toasts'),cls=kind===true||kind==='error'?'error':kind==='good'?'good':kind==='hint'?'hint':'',life=cls==='error'?5500:cls==='hint'?3200:3600;
  const mount=$('#confirmDialog').open?$('#confirmDialog'):$('#sheet').open?$('#sheet'):document.body;mount.append(box);
  const leave=el=>{clearTimeout(el._t);el._t=setTimeout(()=>{el.classList.add('leaving');setTimeout(()=>el.remove(),320);},life);};
  const same=[...box.children].find(x=>x.dataset.msg===message&&!x.classList.contains('leaving'));
  if(same){same.classList.remove('bump');void same.offsetWidth;same.classList.add('bump');leave(same);return;}
  const el=document.createElement('div');el.className=`toast ${cls}`.trim();el.dataset.msg=message;el.textContent=message;
  if(cls==='hint'){const face=document.createElement('span');face.className='hint-face';face.setAttribute('aria-hidden','true');face.textContent='💡';el.prepend(face);}
  box.append(el);leave(el);
  const cap=document.documentElement.dataset.layout==='phone'?2:3;while(box.children.length>cap)box.firstElementChild.remove();}
function download(data,name,type='application/json'){const blob=new Blob([data],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);}
async function cmd(action,payload={},options={}){
  try{const r=await api.command(action,payload,options.career||career());if(!options.quiet)toast(r.message,r.correct===false?'error':r.celebrate?'good':false);if(r.celebrate){sound.success();world.celebrate();}else sound.click();for(const note of new Set(r.effects||[]))toast(note);return r;}
  catch(error){toast(error.status?error.message:'Mất kết nối. Việc đã xác nhận vẫn được giữ, thử lại sau một chút nhé.',true);sound.error();return null;}
}
function closeSheet(){if($('#sheet').open)$('#sheet').close();ui.view=null;ui.ai={};world.paused=ui.paused;}
function openSheet(view,data={}){if(view!=='job'&&view!=='chat'){ui.task=null;}Object.assign(ui,data);ui.view=view;renderSheet(false);if(!$('#sheet').open){const d=$('#sheet');d.showModal();d.scrollTop=0;d.tabIndex=-1;d.focus({preventScroll:true});}}
function header(title,subtitle='',eyebrow='MỘT NGÀY LÀM NGHỀ',extra=''){return `<header class="sheet-head"><div class="grow"><span class="eyebrow">${eyebrow}</span><h2>${title}</h2>${subtitle?`<p>${subtitle}</p>`:''}</div>${extra}<button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;}
function footer(left='',right=''){return `<footer class="sheet-foot"><p>${left}</p><div class="row wrap">${right}</div></footer>`;}
function setPaused(value){ui.paused=value;world.paused=value;$('#pauseOverlay').hidden=!value;renderMain();if(value)sound.stopMusic();else sound.configure(api.state.settings);}
function draft(t){return ui.drafts[t.id]??={paper:t.pack?.paper||'cream',ribbon:t.pack?.ribbon||'gold',card:t.pack?.card||'Gửi bạn một ngày dịu dàng.',checks:[]};}
function taskNext(t){if(!t)return'Chọn một việc nhỏ để bắt đầu';if(!room().open)return'Mở ngày để tiếp tục';if(t.desk)return deskNext(t,api);if(careerUI(t.career))return careerUI(t.career).next(t,careerContext(env()));if(['teacher','tour_guide','milk_tea'].includes(t.career))return nextStep(t);if(!t.known&&['mother_baby','pharmacy'].includes(career()))return'Hỏi nhu cầu / đọc mục tiêu';if(career()==='mother_baby'){if(!Object.keys(t.basket).length)return'Lấy hàng trên kệ';if(t.needs.gift&&!t.pack)return'Tới bàn gói quà';if(!t.checked)return'Kiểm giỏ trước khi giao';return'Thanh toán & bàn giao';}if(career()==='pharmacy'){if(t.needs.referral)return'Chuyển cô Thu';if(!Object.keys(t.basket).length)return'Đọc nhãn và lấy đúng mã';return t.checked?'Bàn giao phiếu':'Kiểm mã · lượng · lô';}if(career()==='accounting')return !t.inspected.length?'Mở bản gốc để kiểm':'Ghép chứng từ & giao dịch';return !t.identity?'Xác minh yêu cầu':t.status==='executing'?'Chờ kết quả phối hợp':t.status==='awaiting_confirmation'?'Kiểm kết quả đã về':t.status==='resolved'?'Hoàn tất và đóng vụ':'Kiểm chứng trước khi đề xuất';}
/* ---- Shell (v0.6): HUD, navigation and task cards. Render-only; every number comes from the server state. ---- */
const EXT=['teacher','tour_guide','milk_tea'];
const layout=()=>document.documentElement.dataset.layout;
/** Replace markup only when it changed: keeps focus, scroll and running animations. */
function setHTML(el,html){if(el&&el._html!==html){el.innerHTML=html;el._html=html;}}
const lowOpen=c=>(c.feed||[]).filter(p=>p.feedback&&p.feedback.status==='open'&&p.stars<=3).length;
const openSituation=c=>c.situation&&c.situation.stage!=='resolved'&&!c.situation.practice?c.situation:null;
function feedUnread(c){
  const key='mnl.seenFeed.'+career();ui.seenFeed??={};
  if(!(career() in ui.seenFeed)){try{ui.seenFeed[career()]=localStorage.getItem(key)||'';}catch{ui.seenFeed[career()]='';}}
  return Boolean(c.feed?.[0])&&c.feed[0].id!==ui.seenFeed[career()];
}
function markFeedSeen(){const id=room()?.feed?.[0]?.id;if(!id)return;(ui.seenFeed??={})[career()]=id;try{localStorage.setItem('mnl.seenFeed.'+career(),id);}catch{/* storage blocked */}}
/** Hands-on actions of the current career (the dock). Shell pages live in the rail / "Thêm" menu. */
function sceneActions(){
  const id=career(),m=meta();let list;
  if(['mother_baby','pharmacy'].includes(id))list=[['queue','people','Khách ghé','Chọn lượt'],['shelf','shelf','Kệ hàng','Lấy đúng món'],['workbench',id==='pharmacy'?'check':'gift',id==='pharmacy'?'Kiểm phiếu':'Gói quà','Tự tay làm'],['counter','clipboard','Bàn giao','Kiểm & chốt'],['warehouse','box','Kho hàng','Nhập & nhận'],['decor','plant','Trang trí','Góc của bạn']];
  else if(EXT.includes(id))list=[['queue','people',id==='teacher'?'Tiết học':id==='tour_guide'?'Đoàn khách':'Khách ghé','Chọn lượt'],['workbench',m.icon,id==='teacher'?'Vào lớp':id==='tour_guide'?'Dẫn đoàn':'Pha chế','Tự tay làm']];
  else if(plugin())list=[['queue','people',m.work||'Khách','Chọn lượt'],['workbench',m.icon||'sparkle',m.station||'Làm việc','Tự tay làm'],...(careerUI(id)?.dock||[])];
  else list=[['queue','folder','Sổ việc','Chọn một vụ'],['workbench',m.icon,id==='accounting'?'Đối chiếu':'Xử lý','Bàn làm việc'],['evidence','search','Chứng cứ','Kiểm dữ kiện'],['decor','plant','Góc của bạn','Nâng cấp']];
  if(id==='teacher')list.unshift(['classroom','calendar','Kế hoạch lớp','Tiết học & sự kiện']);
  return list;
}
function navItems(c){
  const items=[['home','grid','Hành trình'],['prepare','coffee','Chuẩn bị'],['feedback','star','Đánh giá',lowOpen(c)],['phone','phone','Chuyện phố',feedUnread(c)?'dot':0],['situation','flag','Tình huống',openSituation(c)?'dot':0],['incident','shield','Chuyện đời',incidentBadge(c)]];
  if(c.job?.required)items.push(['jobapp','briefcase','Việc làm',needsJob()?'dot':0]);
  items.push(['operations','store','Sổ tiệm',c.ops?.alerts?.length?'dot':0]);
  if(!EXT.includes(career()))items.push(['journal','book','Sổ tay']);
  items.push(['people','people','Bạn quen'],['album','camera','Kỷ niệm'],['workshop','sparkle','Trò nhỏ'],['passport','award','Hộ chiếu'],['town','compass','Khu phố']);
  return items;
}
const railItem=([a,i,label,badge])=>`<button type="button" class="rail-item ${ui.view===a?'active':''}" data-action="${a}"${ui.view===a?' aria-current="page"':''}>${icon(i,21)}<span>${label}</span>${badge==='dot'?'<i class="dot" aria-hidden="true"></i>':badge?`<em class="badge">${badge}</em>`:''}</button>`;
function railHTML(c){
  const extra=layout()==='phone'?sceneActions().slice(4):[];
  return (extra.length?`<p class="rail-title">Trong tiệm</p>${extra.map(([a,i,l])=>railItem([a,i,l])).join('')}<p class="rail-title">Sổ & khu phố</p>`:'')+navItems(c).map(railItem).join('')+`<button type="button" class="rail-item rail-bottom" data-action="help">${icon('question',21)}<span>Cách chơi</span></button>`;
}
function dockHTML(c){
  const phone=layout()==='phone',low=lowOpen(c);let items=sceneActions();
  if(phone){items=items.slice(0,4);for(const f of [['feedback','star','Đánh giá','Khách nói gì'],['prepare','coffee','Chuẩn bị','Trước mỗi ca']])if(items.length<4&&!items.some(x=>x[0]===f[0]))items.push(f);}
  const more=phone&&navItems(c).some(x=>x[3]&&!items.some(y=>y[0]===x[0]));
  return items.map(([a,i,l,sub])=>`<button type="button" class="dock-btn${a==='workbench'?' main':''}" data-action="${a}">${icon(i,22)}<span>${l}${sub?`<small>${sub}</small>`:''}</span>${a==='feedback'&&low?`<em class="badge">${low}</em>`:''}</button>`).join('')+
    (phone?`<button type="button" class="dock-btn dock-more" data-action="v4Menu" aria-label="Thêm: sổ tiệm, sổ tay, khu phố" aria-expanded="${document.documentElement.classList.contains('menu-open')}">${icon('menu',22)}<span>Thêm</span>${more?'<i class="dot" aria-hidden="true"></i>':''}</button>`:'');
}
/** Shop clock when the career keeps one: module `clock(room)` hook, the boba counter or the office desk. */
function hudClock(c){
  if(!c.open)return '';
  try{const v=careerUI(career())?.clock?.(c);if(v)return String(v);}catch{/* the hook is optional */}
  const b=c.data?.boba?.clock,o=c.data?.office?.clock;
  if(typeof b==='string')return b;
  if(Number.isFinite(o))return `${String(Math.floor(o/60)%24).padStart(2,'0')}:${String(Math.round(o)%60).padStart(2,'0')}`;
  return '';
}
/** Phone HUD keeps big sums short so nothing is cut at 390px: 125.400 → 125,4k, 3.373.500 → 3,37tr. */
const shortMoney=n=>Math.abs(n)>=999950?`${(n/1e6).toLocaleString('vi-VN',{maximumFractionDigits:2})}tr`:Math.abs(n)>=1e5?`${(n/1e3).toLocaleString('vi-VN',{maximumFractionDigits:1})}k`:fmt(n);
function hudHTML(c,m){
  const reviews=c.feed.filter(p=>p.stars).length,left=c.tasks.filter(t=>!ended(t)).length,w=c.life?.weather,clk=hudClock(c);
  const sub=!c.open?'Chưa mở cửa':left?`Còn ${left} việc`:'Hết việc rồi';
  const money=layout()==='phone'?shortMoney(c.money):fmt(c.money);
  return `<button type="button" class="icon-btn day-control" data-action="${c.open?'pause':'prepare'}" aria-label="${c.open?(ui.paused?'Tiếp tục':'Tạm dừng'):'Chuẩn bị ngày mới'}">${icon(c.open?(ui.paused?'play':'pause'):'sun',24)}</button>`+
    `<button type="button" class="cozy-day" data-action="prepare"><strong>Ngày ${c.day}</strong><small>${w?`<span class="hud-weather" title="${esc(w.name||'')}">${esc(w.emoji)}</span> `:''}${clk?`<span class="hud-clock">${esc(clk)}</span><span class="hud-sub"> · ${sub}</span>`:sub}</small></button>`+
    `<button type="button" class="cozy-till" data-action="finance" aria-label="${esc(wordsFor(career()).till)}: ${fmt(c.money)} xu"><small>${esc(c.life.shop_name||m.place)}</small><strong data-testid="money"${money.length>=6?' class="long"':''}>${money}<span> xu</span></strong></button>`+
    `<button type="button" class="cozy-rating" data-action="feedback" aria-label="${c.rating?`Đánh giá ${c.rating} sao, ${reviews} lượt`:'Chưa có đánh giá'}"><b class="rating-num">${c.rating?Number(c.rating).toFixed(1):'—'}</b><small>${reviews} ${esc(wordsFor(career()).rating)}</small></button>`+
    `<button type="button" class="icon-btn top-social" data-action="social" aria-label="Phố nghề">${icon('store',20)}${api.social?.unread?`<em class="badge">${api.social.unread}</em>`:''}</button><button type="button" class="icon-btn top-settings" data-action="settings" aria-label="Cài đặt">${icon('settings',20)}</button>`;
}
function taskCards(c){
  const t=c.tasks.find(x=>x.id===c.active_task&&!ended(x))||c.tasks.find(x=>!ended(x)),left=c.tasks.filter(x=>!ended(x)).length;
  let main;
  if(needsJob())main=`<article class="note-card"><span class="eyebrow">Việc làm</span><h3>Nơi này cần tuyển bạn trước đã</h3><p>Gửi CV, phỏng vấn, nhận thư mời rồi đi làm.</p>${button('Xin việc '+icon('chevron',13),'jobapp',{},'primary full')}</article>`;
  else if(!c.open)main=`<article class="note-card"><span class="eyebrow">Ngày ${c.day}</span><h3>${c.shift_summary?'Sẵn sàng cho ngày mới?':'Khách sắp ghé rồi.'}</h3><p>Chuẩn bị một chút rồi mở cửa nhé.</p>${button(icon('sun',14)+' Chuẩn bị ngày mới','prepare',{},'primary full')}${c.shift_summary?button('Xem ngày vừa qua','summary',{},'ghost small full'):''}</article>`;
  else if(t)main=`<article class="note-card task-card"><span class="eyebrow">Việc trước mắt</span><div class="row"><span class="npc-mini">${portrait(npc(t.npc),35)}</span><div class="grow"><h3>${esc(t.title)}</h3><small class="muted npc-mini">${esc(npc(t.npc).display_name)}</small></div></div>${t.known?'':`<p class="hud-quote">“${esc(t.opening)}”</p>`}<div class="task-step">${icon('flag',13)} ${esc(taskNext(t))}</div>${button('Làm tiếp '+icon('arrow',14),'job',{task:t.id},'primary full')}<div class="hud-extra small muted">${left} việc đang chờ · ${c.day_completed} việc đã xong</div></article>`;
  else main=`<article class="note-card"><span class="eyebrow">Quầy đang rảnh</span><h3>${deskWork()?'Hết việc trong khay rồi!':'Hết khách rồi!'}</h3><p>${deskWork()?'Nhận thêm việc hoặc khép ca hôm nay.':'Đón thêm khách hoặc khép ca hôm nay.'}</p>${commandButton(deskWork()?'Nhận thêm một việc':'Đón thêm một khách','more_work',{},'primary full')}${button('Khép ca hôm nay','end',{},'ghost small full')}</article>`;
  const notes=[],x=openSituation(c),cl=c.classroom,low=lowOpen(c),alert=c.ops?.alerts?.[0];
  if(c.event)notes.push(['event',{},c.event.practice?'play':'flag',c.event.practice?'Diễn tập':'Chuyện ở góc phố',c.event.stage==='resolved'?'Đã có kết quả · xem lại':c.event.title]);
  if(x)notes.push(['situation',{},'flag',x.tone==='tense'?'Chuyện căng':'Chuyện đời thường',x.title]);
  const incNote=incidentNote(c);if(incNote)notes.unshift(incNote);
  if(cl&&c.open){const ev=cl.active||cl.offers.find(o=>o.kind==='event');if(ev)notes.push(['classroom',{},'book',cl.active?'Đang làm dở':'Lịch lớp · '+cl.month,`${ev.emoji} ${ev.title}`]);}
  if(low)notes.push(['feedback',{filter:'open'},'star','Đánh giá',`${low} đánh giá ≤3★ chờ bạn trả lời`]);
  if(alert)notes.push(['opsTab',{tab:alert.tab},'store','Sổ tiệm',alert.text]);
  const list=notes.length?`<article class="note-card hud-notes"><span class="eyebrow">Cần để ý · ${notes.length}</span>${notes.map(([a,d,i,k,txt])=>`<button type="button" class="hud-note" data-action="${a}"${attrs(d)}><span class="hud-note-ico">${icon(i,16)}</span><span class="grow"><small>${esc(k)}</small><b>${esc(txt)}</b></span>${icon('chevron',14)}</button>`).join('')}</article>`:'';
  return main+list;
}
/** Helper hint: when the next step of the task in hand changes while the player is in the scene, say it once. */
function stepHint(c){
  const t=c.open&&!needsJob()?c.tasks.find(x=>x.id===c.active_task&&!ended(x)):null;
  const key=t?`${career()}|${t.id}|${taskNext(t)}`:'';
  if(ui.hintKey===undefined){ui.hintKey=key;return;}
  if(key===ui.hintKey||$('#sheet').open||$('#confirmDialog').open||ui.paused)return;
  ui.hintKey=key;if(t)toast(taskNext(t),'hint');
}
/** Coin pop / star bump when the server says money or rating changed. */
function hudFeedback(c){
  const prev=ui.hudPrev;ui.hudPrev={career:career(),money:c.money,rating:c.rating};
  if(!prev||prev.career!==career())return;
  const d=c.money-prev.money,till=$('#topbar .cozy-till');
  if(d&&till){
    const r=till.getBoundingClientRect(),pop=document.createElement('span');
    pop.className=`coin-pop ${d>0?'up':'down'}`;pop.setAttribute('aria-hidden','true');pop.textContent=`${d>0?'+':'−'}${fmt(Math.abs(d))} xu`;
    pop.style.left=`${Math.round(r.left+r.width/2)}px`;pop.style.top=`${Math.round(r.bottom-6)}px`;document.body.append(pop);setTimeout(()=>pop.remove(),1500);
    till.classList.remove('bump');void till.offsetWidth;till.classList.add('bump');
  }
  if(c.rating&&prev.rating!==c.rating){const el=$('#topbar .cozy-rating');if(el){el.classList.remove('bump','down');void el.offsetWidth;el.classList.add('bump');if(prev.rating&&c.rating<prev.rating)el.classList.add('down');}}
}
function renderMain(){
  if(!api.state||!api.content)return;const c=room(),m=meta();
  document.body.classList.toggle('reduce-motion',api.state.settings.reduceMotion);document.body.classList.toggle('large-text',api.state.settings.largeText);document.documentElement.style.setProperty('--career',m.color||'#c44b30');
  setHTML($('#topbar'),hudHTML(c,m));
  setHTML($('#rail'),railHTML(c));
  setHTML($('#sceneHeading'),`<span class="eyebrow">${esc(m.map_label)}</span><h1>${esc(c.life.shop_name||m.place)}</h1><p>${esc(m.tagline)}</p>`);
  const w=c.life?.weather,mode=c.life?.mode&&c.life.mode!=='normal'?api.content.experiences?.modes?.find(x=>x.id===c.life.mode):null;
  setHTML($('#sceneBadge'),pill(c.open?'Đang mở cửa':'Đang nghỉ',c.open?'green':'')+(w?pill(`${esc(w.emoji)} ${esc(w.name)}`):'')+(mode?pill(esc(mode.name),c.life.mode==='festival'?'amber':'blue'):''));
  setHTML($('#taskHUD'),taskCards(c));
  setHTML($('#dock'),dockHTML(c));
  setHTML($('#sceneHint'),`${icon('move',12)} Chạm sàn để đi · Chạm đồ vật để làm · ${layout()!=='phone'?'WASD / mũi tên · E tương tác':'Các nút phía dưới cũng thao tác được'}`);
  $('#ambientCaption').textContent='“'+m.caption+'”';$('#saveState').classList.toggle('offline',!api.connected);
  setHTML($('#saveState'),api.connected?`<i class="saved-dot"></i>Đã lưu`:`<i class="saved-dot"></i>Mất kết nối <button type="button" class="linkish" data-action="reconnect">Thử lại</button>`);
  hudFeedback(c);stepHint(c);
  sound.configure(api.state.settings);world.update(api.state,api.content);
}
function renderSheet(preserve=true){
  if(!ui.view)return;const dialog=$('#sheet'),openedDetails=[...dialog.querySelectorAll('details')].map(el=>el.open),scroll=dialog.scrollTop,active=document.activeElement,focusId=active?.id,selection=active?.selectionStart;
  const fkey=el=>el.id||(el.name&&el.form?`${el.form.dataset.socForm||el.form.id||''}|${el.form.dataset.pid||el.form.dataset.post||el.form.dataset.id||''}|${el.name}`:null);
  const fields={};if(preserve)dialog.querySelectorAll('[data-preserve]').forEach(el=>{const k=fkey(el);if(k)fields[k]={value:el.value,checked:el.checked};});const focusKey=active&&dialog.contains(active)?fkey(active):null;
  let html;dialog.className='sheet';
  switch(ui.view){
    case'home':dialog.classList.add('home');html=homeView();break;
    case'future':html=futureView();break;
    case'job':dialog.classList.add('cozy-job');html=jobView();break;
    case'prepare':case'prices':case'workshop':case'passport':case'town':dialog.classList.add('cozy-sheet',ui.view==='prepare'?'prep-sheet':'life-sheet');html=careerUI(career())?.page?.(ui.view,careerContext(env()))||experienceView(ui.view,career(),room(),api.content,meta(),ui);break;
    case'queue':dialog.classList.add('medium');html=queueView();break;
    case'chat':dialog.classList.add('medium');html=chatView();break;
    case'phone':dialog.classList.add('medium');html=phoneView();break;
    case'event':dialog.classList.add('medium');html=eventView();break;
    case'journal':dialog.classList.add('medium');html=journalView();break;
    case'people':dialog.classList.add('medium');html=peopleView();break;
    case'decor':html=decorView();break;
    case'warehouse':dialog.classList.add('medium');html=warehouseView();break;
    case'album':dialog.classList.add('medium');html=albumView();break;
    case'settings':dialog.classList.add('medium','v4-sheet','drawer');html=settingsV4(env());break;
    case'social':dialog.classList.add('wide','v4-sheet');html=socialView(env());break;
    case'summary':dialog.classList.add('narrow','cozy-summary');html=summaryView();break;
    case'help':dialog.classList.add('medium');html=helpView();break;
    case'inventory':dialog.classList.add('medium','v4-sheet');html=inventoryView(env());break;
    case'feedback':dialog.classList.add('v4-sheet','wide');html=feedbackView(env());break;
    case'situation':dialog.classList.add('medium','v4-sheet');html=situationView(env());break;
    case'incident':dialog.classList.add('medium','v4-sheet','inc-sheet');html=incidentView(env());break;
    case'jobapp':dialog.classList.add('medium','v4-sheet');html=jobAppView(env());break;
    case'classroom':dialog.classList.add('wide','v4-sheet');html=classroomView(env());break;
    case'operations':dialog.classList.add('operations');html=operationsView(career(),room(),api.content.operations,ui,api.state);break;
    default:html=header('Một khoảng thảnh thơi')+`<div class="sheet-body">${empty('Cửa sổ chưa mở','Quay lại cảnh để tiếp tục nhé.')}</div>`;
  }
  $('#sheetContent').innerHTML=html;
  if(preserve){dialog.querySelectorAll('details').forEach((el,i)=>{el.open=openedDetails[i]||false;});dialog.querySelectorAll('[data-preserve]').forEach(el=>{const data=fields[fkey(el)];if(data){el.value=data.value;if(el.type==='checkbox')el.checked=data.checked;}});dialog.scrollTop=scroll;if(focusKey){const el=[...dialog.querySelectorAll('[data-preserve],input,textarea,select')].find(x=>fkey(x)===focusKey);el?.focus({preventScroll:true});try{el?.setSelectionRange(selection,selection);}catch{/* not a text input */}}}
  if(!preserve)dialog.scrollTop=0;
  if(ui.view==='chat'){$('#messages')?.scrollTo(0,$('#messages').scrollHeight);}
}

function homeView(){return homeV4(env());}
function futureView(){if(api.state.journey)return futureV4(env());return header('Cả một khu phố phía trước','Những nghề sẽ mở sau','DANH MỤC 19 NGHỀ')+`<div class="sheet-body"><div class="future-grid">${api.content.catalogue.filter(c=>!api.state.careers[c.id]).map(c=>`<article class="future-card">${pill(icon('lock',11)+' Mở sau')}<h3>${esc(c.title||c.name)}</h3><p>${esc(c.core_loop||c.focus||c.summary||c.unique_mechanic||'Một trải nghiệm nghề mới, có cơ chế và câu chuyện riêng.')}</p></article>`).join('')}</div></div>`+footer('',button('Về các nghề đang mở','home',{},'primary'));}
function queueView(){const c=room(),tasks=c.tasks.filter(t=>!ended(t));return header('Việc đang chờ',c.open?'Chọn một việc để làm tiếp.':'Mở ca để làm tiếp những việc đã giữ lại.','SỔ VIỆC · '+esc(meta().place))+`<div class="sheet-body">${!c.open?notice('Ca đang nghỉ. Mọi việc vẫn được giữ nguyên.<br>'+button('Bắt đầu ngày','start',{},'small primary'),'amber','sun'):''}<div class="queue-grid">${tasks.map(t=>`<article class="queue-card ${t.id===c.active_task?'active':''}"><div class="row">${portrait(npc(t.npc),44)}<div class="grow"><h3>${esc(t.title)}</h3><small class="muted">${esc(npc(t.npc).display_name)}</small></div>${t.deferred?pill('Đã hẹn','amber'):''}</div><p>${esc(t.opening)}</p><div class="row spread">${pill(taskNext(t),'green')}${button('Làm tiếp '+icon('arrow',13),'job',{task:t.id},'small primary')}</div></article>`).join('')||empty('Hết việc rồi!','Đón thêm khách hoặc khép ca hôm nay nhé.','coffee')}</div></div>`+(c.open?footer(`${c.day_completed} việc đã xong hôm nay`,commandButton(icon('plus',14)+' Nhận thêm việc','more_work',{},tasks.length?'ghost':'primary',tasks.length>=4)+button('Khép ca','end',{},'ghost')):'');}
function customerAside(t){const n=npc(t.npc),c=room();let needs='';if(t.needs){if(career()==='mother_baby'){const p=product(t.needs.product),paper=api.content.papers.find(p=>p.id===t.needs.paper);needs=`<strong>${t.needs.qty} × ${esc(p.name)}</strong><br>Ngân sách: ${fmt(t.needs.budget)} xu<br>${t.needs.gift?'Gói giấy '+esc(paper.name):'Không cần gói quà'}`;}}
  return `<aside class="work-aside ${t.known?'known':''} ${!Object.keys(t.basket||{}).length?'empty-tray':''}">${t.known?`<div class="needs"><h4>${icon('clipboard',15)} Điều đã xác nhận</h4><p>${needs||'Đã hiểu mục tiêu. Xem nguồn trước khi quyết định.'}</p></div>`:`<p class="small muted">Bấm “Hỏi rõ yêu cầu” ở khung trên để biết khách cần gì.</p>`}${career()==='mother_baby'?basketView(t):''}</aside>`;
}
/** Mother & baby basket (the pharmacy tray lives in pharmacyJob). */
function basketView(t){const lines=Object.entries(t.basket||{});return `<div class="row spread space-top"><h4>Giỏ đang giữ</h4>${pill(Object.values(t.basket||{}).reduce((a,b)=>a+b,0)+' món')}</div><div class="basket">${lines.map(([id,qty])=>{const p=product(id);return `<div class="basket-line">${itemArt(p.icon||'box',40,p.color)}<div><strong>${esc(p.name)}</strong><small>${esc(fmt(room().life.prices[p.id]||p.price)+' xu')} × ${qty}</small></div><button class="icon-btn" aria-label="Bỏ một ${esc(p.name)}" data-command="basket_remove" data-payload="${esc(JSON.stringify({task:t.id,item:id}))}">${icon('minus',14)}</button></div>`;}).join('')||'<div class="empty-basket">Khay còn trống.<br>Chọn món từ kệ hàng.</div>'}</div><div class="receipt-total"><span>Tiền hàng</span><span>${fmt(lines.reduce((sum,[id,q])=>sum+(room().life.prices[id]||product(id).price)*q,0))} xu</span></div>`;}
function jobView(){
  let t=activeTask();const c=room(),mod=careerUI(career());
  // Counter careers (module.autoNext) go straight to the next waiting customer after a hand-over.
  if(t&&ended(t)&&mod?.autoNext){const n=c.tasks.find(x=>x.id===c.active_task&&!ended(x))||c.tasks.find(x=>!ended(x));if(n){t=n;ui.task=n.id;}}
  // Plugins may show a between-orders panel (settle cash, refuel, field work…).
  const idle=mod?.idle&&(!t||ended(t))?`<div class="career-idle space-top">${mod.idle(careerContext(env()))}</div>`:'';
  if(!t){
    // Between customers there is always one clear way on: the next customer (unless the career's own panel offers it).
    const more=c.open&&!idle.includes('data-command="more_work"')?commandButton(icon('plus',14)+(deskWork()?' Nhận thêm một việc':' Đón khách tiếp theo'),'more_work',{},'primary'):'';
    return header(deskWork()?'Bàn làm việc đang trống':'Chưa có khách nào đang chờ',c.open?'Việc đã nhận đều xong. Nhận lượt tiếp theo khi bạn sẵn sàng.':'Ca đang nghỉ.')+`<div class="sheet-body">${idle||empty('Làm điều mình thích một chút','Bạn có thể đọc review, trang trí hoặc nhận thêm việc.','coffee')}<div class="row wrap space-top">${more}${button('Xem sổ việc','queue',{},more||idle.includes('more_work')?'ghost':'primary')}${button('Chăm chút không gian','decor',{},'ghost')}</div></div>`;
  }
  if(ended(t)&&t.desk)return header('Hồ sơ đã đóng dấu',esc(t.title),'KẾT QUẢ HỒ SƠ')+`<div class="sheet-body">${deskDone(t,env())}<div class="row wrap space-top" style="justify-content:center">${button('Công việc tiếp theo','nextJob',{},'primary')}${button('Đọc lời nhắn','phone',{},'ghost')}${c.event?button('Chuyện vừa xảy ra','event',{},'cream'):''}</div>${idle}</div>`;
  if(ended(t))return header('Một việc đã được làm tới nơi',t.title,'THÀNH QUẢ HÔM NAY')+`<div class="sheet-body center"><div class="celebration">${icon('sparkle',55)}</div><h2>Cảm ơn bạn đã giúp!</h2><p class="muted">${deskWork()?'Hồ sơ đã chuyển đi. Một lời nhắn đang đợi trên Chuyện phố.':'Khách đã nhận kết quả. Một lời nhắn đang đợi trên Chuyện phố.'}</p><div class="row wrap" style="justify-content:center">${c.tasks.some(x=>!ended(x))?button('Công việc tiếp theo','nextJob',{},'primary'):c.open?commandButton(deskWork()?'Nhận thêm một việc':'Đón thêm một khách','more_work',{},'primary'):''}${button('Đọc lời nhắn','phone',{},'ghost')}${c.event?button('Chuyện vừa xảy ra','event',{},'cream'):''}</div>${idle}</div>`;
  ui.task=t.id;let inner;
  if(careerUI(career()))inner=careerUI(career()).job(t,careerContext(env()));else if(['teacher','tour_guide','milk_tea'].includes(career()))inner=extendedJob(t,c,api.content,ui,api.state);else if(t.desk)inner=deskJob(t,env());else if(career()==='mother_baby')inner=motherBabyJob(t);else if(career()==='pharmacy')inner=pharmacyJob(t);else if(career()==='accounting')inner=accountingJob(t);else inner=supportJob(t);
  return header(esc(t.title),taskNext(t),esc(meta().work).toUpperCase()+' · NGÀY '+t.day)+`<div class="sheet-body">${!c.open?notice('Ca đang nghỉ. Mở ngày để làm tiếp. '+button('Bắt đầu ngày','start',{},'primary small'),'amber'):''}${['teacher','tour_guide','milk_tea'].includes(career())||plugin()||t.desk||careerUI(career())?'':guestRibbon(t,c,api.content)}${inner}</div>`+footer('Bạn có thể giữ việc và quay lại, không mất đồ đã chọn.',commandButton('Để lát nữa','defer',{task:t.id},'ghost small')+button('Xem các việc khác','queue',{},'small'));
}
function motherBabyJob(t){const d=draft(t),tab=ui.jobTab;const step=`<nav class="step-strip" aria-label="Bước phục vụ">${[['shelf','Kệ hàng'],['pack','Gói quà'],['checkout','Thu ngân']].map(([id,l],i)=>`<button data-action="jobTab" data-tab="${id}" class="${tab===id?'active':''}"><span>${i+1}</span>${l}</button>`).join('')}</nav>`;
  let main='';if(tab==='pack'){
    const paper=api.content.papers.find(p=>p.id===d.paper),ribbon=api.content.ribbons.find(r=>r.id===d.ribbon);
    main=`<h3>Một món quà được chăm chút</h3><p class="muted small">Chọn giấy theo điều khách thích. Nơ và lời chúc là nét riêng của bạn.</p><div class="wrap-layout"><div class="gift-preview"><div class="gift-box" style="--paper-color:${paper.color};--ribbon-color:${ribbon.color}"><div class="gift-bow"></div></div></div><div><label class="field">Giấy gói</label><div class="swatches">${api.content.papers.map(p=>`<button class="swatch ${p.id===d.paper?'selected':''}" data-action="paper" data-value="${p.id}"><i style="background:${p.color}"></i>${p.name}</button>`).join('')}</div><label class="field">Chiếc nơ</label><div class="swatches">${api.content.ribbons.map(r=>`<button class="swatch ${r.id===d.ribbon?'selected':''}" data-action="ribbon" data-value="${r.id}"><i style="background:${r.color}"></i>${r.name}</button>`).join('')}</div><label class="field">Lời chúc<input class="input" id="gift-card" maxlength="100" data-draft="card" value="${esc(d.card)}"></label></div></div><div class="row wrap space-top">${button(icon('gift',16)+' Gói món quà này','pack',{},'primary')}${button('Sang thu ngân '+icon('arrow',14),'jobTab',{tab:'checkout'},'ghost')}</div><p class="small-note space-top">Vật liệu gói: 5 xu khi giao hàng. Đổi mẫu trước khi giao không mất phí.</p>${t.pack?notice('Đã lưu mẫu gói '+esc(api.content.papers.find(p=>p.id===t.pack.paper).name)+'. Có thể đổi trước khi bàn giao.'):''}`;
  }else if(tab==='checkout'){
    const total=Object.entries(t.basket).reduce((sum,[id,q])=>sum+(room().life.prices[id]||product(id).price)*q,0);main=`<h3>Mọi điều nhỏ đều đúng chứ?</h3><p class="muted small">Kiểm lại hàng, ngân sách và mẫu gói trước khi trao cho khách.</p><div class="verify-list"><div class="row spread"><span>Tiền hàng theo giỏ</span><strong>${fmt(total)} xu</strong></div><div class="row spread"><span>Mẫu gói đang chọn</span><strong>${t.pack?esc(api.content.papers.find(p=>p.id===t.pack.paper).name):'Chưa gói'}</strong></div><div class="row spread"><span>Vật liệu gói</span><strong>${t.pack?'5':'0'} xu</strong></div></div>${t.checked?notice('Giỏ đã được đối chiếu. Bàn giao sẽ xuất kho và ghi doanh thu đúng một lần.'):notice('Chưa kiểm xong. Có thể sửa lựa chọn mà không mất tiền.','amber','clipboard')}<div class="row wrap space-top">${commandButton(icon('check',15)+' Kiểm đơn','shop_check',{task:t.id},'ghost')}${button(icon('bag',15)+' Thanh toán & giao','deliverMB',{},'primary')}</div>${room().upgrades.includes('workbench')&&t.known?notice('Bàn kiểm hai bước: so '+t.needs.qty+' món mã '+esc(t.needs.product)+' với giỏ; sau đó xem màu giấy khách đã chọn.','blue','search'):''}`;
  }else main=`<div class="row spread"><div><h3>Chọn một món thật hợp</h3><p class="muted small">Hàng được giữ riêng cho đơn này khi đưa vào giỏ.</p></div>${pill('8 món nhỏ')}</div><div class="product-grid">${api.content.products.map(p=>`<article class="product-card"><div class="art">${itemArt(p.icon,78,p.color)}</div><div class="product-info"><h4>${esc(p.name)}</h4><div class="row spread"><span class="price">${p.price} xu</span><span class="stock">Còn ${room().available[p.id]}</span></div>${commandButton(icon('plus',12)+' Thêm vào giỏ','shop_pick',{task:t.id,item:p.id},'small',!t.known||room().available[p.id]<1||!room().open)}</div></article>`).join('')}</div><div class="row space-top">${button('Tới bàn gói '+icon('arrow',14),'jobTab',{tab:'pack'},'primary')}${button('Không gói · thu ngân','jobTab',{tab:'checkout'},'ghost')}</div>`;
  return `<div class="work-layout"><div class="work-main">${step}${main}</div>${customerAside(t)}</div>`;
}
/* ---- Desk work screens: pharmacy counter, bookkeeping board, support desk (classic tasks).
   Render + client UI state only (ui.docs, ui.transactions, ui.phFilter, ui.jobTab, draft checks);
   the server checks every command again. Styles: css/desks.css, scoped under .career-job.dw. ---- */
const pct=v=>Math.max(0,Math.min(100,Math.round(Number(v)||0)));
const dwState=(label,tone='')=>`<span class="dw-state${tone?' '+tone:''}">${label}</span>`;
/** Who is waiting: portrait, name, one context line, patience and a chat button (replaces the guest ribbon). */
function dwWho(t,sub){
  const n=npc(t.npc),p=room().life?.mode==='calm'?100:pct(t.patience??100);
  return `<header class="dw-who">${portrait(n,48)}<div class="dw-who-name"><strong>${esc(n.display_name)}</strong><small>${sub}</small>`+
    `<div class="dw-pat${p<50?' low':p<75?' mid':''}" role="meter" aria-label="Kiên nhẫn" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${p}"><i><b style="width:${p}%"></b></i><small>Kiên nhẫn ${p}%</small></div></div>`+
    `<button type="button" class="btn ghost icon-btn dw-talk" data-action="chat" data-npc="${esc(t.npc)}" data-task="${esc(t.id)}" aria-label="Trò chuyện với ${esc(n.display_name)}">${icon('chat',20)}</button></header>`+
    `<p class="dw-quote">${esc(t.opening)}</p>`;
}
/** Sticky bar above the sheet footer: what is going on + at most one main action. */
const dwBar=(text,btns='')=>`<div class="dw-bar"><div class="dw-bar-text" aria-live="polite">${text}</div>${btns?`<div class="dw-bar-btns">${btns}</div>`:''}</div>`;

const LOT_STATE={unread:['Chưa đọc',''],available:['Hợp lệ','green'],held:['Tạm giữ','amber'],expired:['Hết hiệu lực','danger']};
function pharmacyJob(t){
  const c=room(),d=draft(t),n=t.known?t.needs:null,refer=!!n?.referral,want=n&&!refer?n.product:'',f=ui.phFilter==='all'?'':(ui.phFilter||want);
  const lotOf=id=>api.content.lots.find(l=>l.id===id),tray=Object.entries(t.basket||{}),count=tray.reduce((a,[,q])=>a+q,0);
  const codes=[...new Set(tray.map(([id])=>lotOf(id)?.product||id))],name=id=>api.content.ph_products.find(p=>p.id===id)?.name||'';
  const state=l=>!t.inspected.includes(l.id)?'unread':c.held_lots.includes(l.id)?'held':l.status;
  const slip=!t.known?`<section class="dw-slip unknown" aria-label="Phiếu lấy hàng"><span class="dw-eyebrow">📋 Phiếu lấy hàng</span><p class="dw-slip-miss">Phiếu chưa đủ thông tin.</p><p class="dw-hint">Hỏi lại khách trước khi lấy hàng. Không đoán theo màu hộp.</p>${commandButton('💬 Hỏi rõ phiếu','ask',{task:t.id},'primary')}</section>`
    :refer?`<section class="dw-slip refer" aria-label="Phiếu lấy hàng"><span class="dw-eyebrow">📋 Phiếu lấy hàng</span><p class="dw-slip-miss">Yêu cầu nằm ngoài phiếu.</p><p class="dw-hint">Không lấy hộp thay thế. Chuyển cô Thu kiểm tiếp.</p>${button('Chuyển cô Thu '+icon('arrow',15),'referPH',{},'primary')}</section>`
    :`<section class="dw-slip" aria-label="Phiếu lấy hàng"><span class="dw-eyebrow">📋 Phiếu lấy hàng</span><dl class="dw-slip-grid"><div><dt>Mã hộp</dt><dd>${esc(n.product)}<small>${esc(name(n.product))}</small></dd></div><div><dt>Số lượng</dt><dd>${n.qty} hộp</dd></div><div class="wide"><dt>Ghi chú</dt><dd>Chỉ lô hợp lệ, không tạm giữ.</dd></div></dl></section>`;
  const lotRow=l=>{const s=state(l),[label,tone]=LOT_STATE[s]||LOT_STATE.expired;
    return `<li class="dw-lot ${s}">${itemArt('box',36,l.color)}<div class="dw-lot-id"><b>${esc(l.id)}</b>${dwState(label,tone)}${s!=='unread'?`<small>Còn ${fmt(c.available?.[l.id])} hộp</small>`:''}</div><div class="dw-lot-act">${s==='unread'?commandButton(icon('eye',15)+' Đọc nhãn','ph_inspect',{task:t.id,lot:l.id},'ghost'):s==='available'?commandButton(icon('plus',15)+' Lấy 1','ph_pick',{task:t.id,item:l.id},'',!t.known||refer||!c.open):''}</div></li>`;};
  const lots=`<section class="dw-sec dw-lots" aria-label="Kệ lô hàng"><div class="dw-sec-head"><h3>Kệ lô hàng</h3><label class="dw-filter"><span>Xem mã</span><select id="ph-filter" aria-label="Chọn mã hộp" data-action-change="ph-filter"><option value="all">Tất cả mã</option>${api.content.ph_products.map(p=>`<option value="${p.id}"${f===p.id?' selected':''}>${p.id}${p.id===want?' · trên phiếu':''}</option>`).join('')}</select></label></div><p class="dw-hint">Đọc nhãn từng lô. Màu hộp không cho biết lô có được xuất.</p>`+
    api.content.ph_products.filter(p=>!f||p.id===f).map(p=>`<div class="dw-lotgroup${p.id===want?' want':''}"><h4><b>${p.id}</b> ${esc(p.name)}${p.id===want?dwState('Mã trên phiếu','blue'):''}</h4><ul class="dw-lotlist">${api.content.lots.filter(l=>l.product===p.id).map(lotRow).join('')}</ul></div>`).join('')+`</section>`;
  const facts={code:`Phiếu ${want||'—'} · khay ${codes.join(', ')||'—'}`,quantity:`Phiếu ${n&&!refer?n.qty:'—'} · khay ${count}`,lot:tray.length?'Khay: '+tray.map(([id])=>id).join(', '):'Khay chưa có lô'};
  const trayBox=`<section class="dw-sec dw-tray" aria-label="Khay kiểm hai bước"><div class="dw-sec-head"><h3>Khay đang giữ</h3><span class="dw-count${want&&count===n.qty?' ok':''}">${count}${want?'/'+n.qty:''} hộp</span></div>`+
    (tray.length?`<ul class="dw-traylist">${tray.map(([id,q])=>{const l=lotOf(id);return `<li>${itemArt('box',32,l?.color)}<span><b>${esc(id)} × ${q}</b><small>${esc(l?.name||'')}</small></span><button type="button" class="btn ghost icon-btn" aria-label="Bỏ một hộp ${esc(id)}" data-command="basket_remove" data-payload="${esc(JSON.stringify({task:t.id,item:id}))}">${icon('minus',16)}</button></li>`;}).join('')}</ul>`:`<p class="dw-empty">Khay trống. Lấy hộp từ lô hợp lệ.</p>`)+
    `<h4 class="dw-step-title">Bước 1 · Tự kiểm khay</h4><div class="dw-checks">${[['code','Mã hộp khớp phiếu'],['quantity','Số lượng đúng phiếu'],['lot','Lô đã đọc nhãn, được xuất']].map(([k,l])=>`<label class="dw-tick"><input type="checkbox" data-phcheck="${k}"${d.checks.includes(k)?' checked':''}><span><b>${l}</b><small>${esc(facts[k])}</small></span></label>`).join('')}</div>`+
    `${button(icon('check',16)+' Kiểm khay','verifyPH',{},t.checked?'ghost':want&&count===n.qty?'primary':'')}${t.checked?'<p class="dw-ok">✓ Đã kiểm đủ ba bước.</p>':''}`+
    `<h4 class="dw-step-title">Bước 2 · Bàn giao</h4><button type="button" class="btn ${t.checked?'primary':''}" data-action="deliverPH"${t.checked?'':' disabled'}>Bàn giao phiếu ${icon('arrow',15)}</button>${t.checked?'':'<p class="dw-hint">Mở khi bước 1 đã khớp.</p>'}</section>`;
  const referBox=t.known&&!refer?`<section class="dw-refer" aria-label="Chuyển người phụ trách"><div><b>Phiếu có điều ngoài phạm vi?</b><p class="dw-hint">Hỏi liều dùng, triệu chứng hay hộp thay thế: chuyển cô Thu, không tự đoán.</p></div>${button('Chuyển cô Thu','referPH',{},'ghost')}</section>`:'';
  const barText=!t.known?'Hỏi rõ phiếu trước khi lấy hàng.':`Phiếu <b>${esc(want)} × ${n.qty}</b> · Khay <b>${count}/${n.qty}</b>${t.checked?' · đã kiểm':count<n.qty?' · lấy thêm':count>n.qty?' · thừa hộp':' · tự kiểm khay'}`;
  // A slip that must be referred has nothing to pick: only the slip and its one action.
  if(refer)return `<div class="career-job dw dw-ph">${dwWho(t,'Phiếu đã rõ')}${slip}</div>`;
  return `<div class="career-job dw dw-ph">${dwWho(t,t.known?'Phiếu đã rõ':'Phiếu chưa rõ')}<div class="dw-ph-grid">${slip}${lots}${trayBox}${referBox}</div>${dwBar(barText,t.checked?button('Bàn giao '+icon('arrow',15),'deliverPH',{},'primary'):'')}</div>`;
}

function accountingJob(t){
  const inG=(k,id)=>t.groups.some(g=>g[k].includes(id)),sum=a=>a.reduce((s,x)=>s+x.amount,0);
  const selD=t.docs.filter(d=>ui.docs.has(d.id)),selT=t.transactions.filter(x=>ui.transactions.has(x.id)),ds=sum(selD),ts=sum(selT);
  const read=t.docs.filter(d=>t.inspected.includes(d.id)).length,settled=t.docs.filter(d=>t.removed.includes(d.id)||inG('docs',d.id)).length;
  const txDone=t.transactions.filter(x=>inG('transactions',x.id)).length,allDone=settled===t.docs.length&&txDone===t.transactions.length;
  const tab=ui.jobTab==='acTx'?'tx':'docs';
  const pick=(action,id,on,off,mark)=>`<button type="button" class="dw-pick${on?' on':''}" data-action="${action}" data-id="${esc(id)}" aria-pressed="${on}" aria-label="Chọn ${esc(id)}"${off?' disabled':''}>${on?icon('check',20):mark||''}</button>`;
  const docCard=d=>{
    const seen=t.inspected.includes(d.id),used=inG('docs',d.id),removed=t.removed.includes(d.id),sel=ui.docs.has(d.id),off=seen&&d.original!==undefined&&d.original!==d.amount;
    const [label,tone]=removed?['Đã loại trùng','']:used?['Đã ghép','green']:d.missing?['Thiếu nguồn','amber']:!seen?['Chưa đọc gốc','']:off?['Lệch gốc','danger']:['Đã đọc','blue'];
    const act=removed||used||d.missing?'':!seen?commandButton(icon('eye',15)+' Mở gốc','ac_inspect',{task:t.id,doc:d.id},'ghost'):off?commandButton('Sửa theo gốc','ac_correct',{task:t.id,doc:d.id},'ghost'):commandButton('Đánh dấu trùng','ac_duplicate',{task:t.id,doc:d.id},'ghost');
    const src=seen?`<p>${esc(d.source)}</p><p>Số gốc: <b>${fmt(d.original)} xu</b>${off?` · đang ghi ${fmt(d.amount)} xu`:''}</p>`:d.missing?'<p>Nguồn chưa được gửi. Xin người gửi bổ sung.</p>':'<p>Chưa mở. Bấm “Mở gốc” để đọc.</p>';
    return `<li class="dw-card${sel?' selected':''}${used||removed?' settled':''}">${pick('selectDoc',d.id,sel,used||removed,used?icon('link',18):removed?icon('minus',18):'')}<div class="dw-card-main"><div class="dw-line"><b class="dw-code">${esc(d.id)}</b><span class="dw-amt">${fmt(d.amount)} xu</span>${dwState(label,tone)}</div><div class="dw-row2">${fold(`<b class="dw-sub">${esc(d.ref)}</b>${d.kind==='hoàn'?' · khoản hoàn':''}`,src)}${act}</div></div></li>`;};
  const txCard=x=>{const used=inG('transactions',x.id),sel=ui.transactions.has(x.id);
    return `<li class="dw-card tx${sel?' selected':''}${used?' settled':''}">${pick('selectTx',x.id,sel,used,used?icon('link',18):'')}<div class="dw-card-main"><div class="dw-line"><b class="dw-code">${esc(x.id)}</b><span class="dw-amt">${fmt(x.amount)} xu</span>${used?dwState('Đã ghép','green'):''}</div><div class="dw-sub">${esc(x.refs.join(' + '))}</div><p class="dw-note">${esc(x.note)}</p></div></li>`;};
  const tabs=`<div class="dw-tabs" role="tablist" aria-label="Bàn đối chiếu">${[['docs','acDocs','📂','Chứng từ',t.docs.length-settled,selD.length],['tx','acTx','🔗','Giao dịch',t.transactions.length-txDone,selT.length]].map(([k,val,e,l,left,picked])=>`<button type="button" role="tab" aria-selected="${tab===k}" class="dw-tab${tab===k?' on':''}" data-action="jobTab" data-tab="${val}"><span><span aria-hidden="true">${e}</span> ${l}</span><em>${picked?`đã chọn ${picked}`:left?`còn ${left}`:'xong ✓'}</em></button>`).join('')}</div>`;
  const board=`<div class="dw-board show-${tab}"><section class="dw-col docs" aria-label="Chứng từ"><h3 class="dw-col-title">📂 Chứng từ</h3><ul class="dw-cards">${t.docs.map(docCard).join('')}</ul></section><section class="dw-col tx" aria-label="Giao dịch"><h3 class="dw-col-title">🔗 Giao dịch</h3><ul class="dw-cards">${t.transactions.map(txCard).join('')}</ul></section></div>`;
  const missing=t.docs.some(d=>d.missing)?`<div class="dw-alert"><div><b>Một phiếu còn thiếu nguồn.</b><p>${t.source_requested?'Đã xin bổ sung. Nguồn về sau hai nhịp.':'Không ghép thẻ thiếu nguồn. Xin người gửi bổ sung.'}</p></div>${t.source_requested?commandButton('Nhận phản hồi','advance',{},'ghost'):commandButton('Xin nguồn bổ sung','ac_request_source',{task:t.id},'primary')}</div>`:'';
  const groups=t.groups.length?`<section class="dw-sec" aria-label="Nhóm đã ghép"><h3>Nhóm đã ghép · ${t.groups.length}</h3><ul class="dw-groups">${t.groups.map((g,i)=>`<li><span><b>${esc(g.docs.join(' + '))} ↔ ${esc(g.transactions.join(' + '))}</b><small>Khớp ${fmt(g.total)} xu</small></span>${commandButton('Tháo','ac_unmatch',{task:t.id,index:i},'ghost')}</li>`).join('')}</ul></section>`:'';
  const hand=`<section class="dw-sec dw-handover" aria-label="Bàn giao hồ sơ"><h3>Bàn giao hồ sơ</h3>${reqList([
      {ok:read===t.docs.length||null,icon:'👁️',label:'Mở đủ bản gốc',value:`${read}/${t.docs.length}`},
      {ok:settled===t.docs.length||null,icon:'📂',label:'Mỗi chứng từ đã ghép hoặc loại trùng',value:`${settled}/${t.docs.length}`},
      {ok:txDone===t.transactions.length||null,icon:'🔗',label:'Mỗi giao dịch đã có nguồn',value:`${txDone}/${t.transactions.length}`}],esc,'Điều kiện bàn giao')}`+
    `<p class="dw-hint">Bản bàn giao giữ nhóm, nguồn và lý do điều chỉnh. Thù lao 70 xu.</p><div class="dw-acts">${t.groups.length?button(icon('check',16)+' Kiểm & bàn giao hồ sơ','completeAC',{},allDone?'primary':''):`<button type="button" class="btn" disabled>${icon('check',16)} Kiểm & bàn giao hồ sơ</button>`}${button('Hỏi người gửi','chat',{npc:t.npc,task:t.id},'ghost')}</div>`+
    `${room().upgrades.includes('workbench')?notice('Bàn kiểm: tìm phiếu có cùng mã tham chiếu; không tính một nguồn hai lần. Kiểm tổng và tập mã đều phải khớp.','blue','search'):''}</section>`;
  const both=selD.length&&selT.length;
  const bar=allDone?dwBar('<b>Đã ghép đủ.</b> Kiểm lại rồi bàn giao.',button(icon('check',16)+' Bàn giao','completeAC',{},'primary'))
    :selD.length||selT.length?dwBar(`<span class="dw-sums"><span><small>Chứng từ · ${selD.length}</small><b>${fmt(ds)}</b></span><i class="${both?ds===ts?'ok':'bad':''}" aria-label="${both?ds===ts?'bằng nhau':'chưa bằng':'so với'}">${both?ds===ts?'=':'≠':'⇄'}</i><span><small>Giao dịch · ${selT.length}</small><b>${fmt(ts)}</b></span></span>`,
      `<button type="button" class="btn ghost icon-btn" data-action="clearSelection" aria-label="Bỏ chọn">${icon('x',18)}</button>`+(both?button(icon('link',16)+' Ghép nhóm','match',{},'primary')
        :button(selD.length?'Chọn giao dịch →':'← Chọn chứng từ','jobTab',{tab:selD.length?'acTx':'acDocs'},'primary dw-swap')+`<button type="button" class="btn dw-wide-only" disabled>${icon('link',16)} Ghép nhóm</button>`))
    :dwBar(read<t.docs.length?'Mở bản gốc, rồi chọn chứng từ và giao dịch cùng mã HD.':'Chọn chứng từ và giao dịch cùng mã HD.');
  return `<div class="career-job dw dw-ac">${dwWho(t,'Gửi hồ sơ đối chiếu')}${missing}${tabs}${board}${groups}${hand}${bar}</div>`;
}

const solutions=[['reship','Gửi bù món thiếu','box','Gửi phần còn thiếu của đơn'],['trace','Đối soát giao nhận','search','Nhờ đầu mối kiểm chặng giao'],['exchange','Đổi đúng món','refresh','Tạo yêu cầu đổi đúng mã'],['refund','Thực hiện hoàn','coin','Hoàn từ quỹ công ty'],['guide','Hướng dẫn khách','book','Chỉ khách tự làm từng bước']];
const CS_STEPS=['Xác minh','Chứng cứ','Phương án','Thực hiện','Kiểm kết quả','Đóng vụ'];
const CS_CHANNELS=['💬 Tin nhắn','📞 Gọi điện','✉️ Thư điện tử'];
/** Where a support case stands (0–5), from server fields only. */
function csStep(t){if(!t.identity)return 0;if(t.evidence.some(e=>e.text==null))return 1;return {proposed:3,executing:3,awaiting_confirmation:4,resolved:5}[t.status]??2;}
function supportJob(t){
  const step=csStep(t),read=t.evidence.filter(e=>e.text!=null).length,sol=solutions.find(x=>x[0]===t.proposal);
  const channel=CS_CHANNELS[[...String(t.id)].reduce((a,ch)=>a+ch.charCodeAt(0),0)%CS_CHANNELS.length];
  const tracker=`<ol class="dw-steps" aria-label="Tiến trình vụ">${CS_STEPS.map((s,i)=>`<li class="${i<step?'done':i===step?'now':''}"${i===step?' aria-current="step"':''}><span class="dw-dot" aria-hidden="true">${i<step?'✓':i+1}</span><span class="dw-step-label">${s}</span></li>`).join('')}</ol><p class="dw-step-now">Bước ${step+1}/6 · <b>${CS_STEPS[step]}</b></p>`;
  const canPropose=t.identity&&read===t.evidence.length&&['new','understood','proposed'].includes(t.status);
  const choices=`<div class="dw-choices" role="group" aria-label="Phương án">${solutions.map(([id,l,i,h])=>`<button type="button" class="dw-choice${t.proposal===id?' selected':''}" data-command="cs_propose" data-payload="${esc(JSON.stringify({task:t.id,solution:id}))}" aria-pressed="${t.proposal===id}"${canPropose?'':' disabled'}>${icon(i,22)}<span><b>${l}</b><small>${h}</small></span></button>`).join('')}</div>`;
  const now=(title,text,action)=>`<section class="dw-now" aria-label="Việc bây giờ"><span class="dw-eyebrow">Việc bây giờ</span><h3>${title}</h3><p>${text}</p>${action}</section>`;
  let card;
  if(t.status==='handed_over')card=now('Chờ chị Mai phản hồi','Hồ sơ đã bàn giao kèm nguồn. Phản hồi về sau hai nhịp.',commandButton('Nhận phản hồi bàn giao','advance',{},'primary full'));
  else if(step===0)card=now('Xác minh người yêu cầu','Xin mã đơn và đối chiếu trước khi mở hồ sơ.',commandButton('🔐 Xác minh mã đơn','cs_identity',{task:t.id},'primary full',!room().open));
  else if(step===1){const e=t.evidence.find(e=>e.text==null);card=now(`Mở chứng cứ · ${read}/${t.evidence.length}`,'Đọc đủ các nguồn. Một trạng thái đơn lẻ chưa phải kết luận.',commandButton(icon('folder',16)+' Mở: '+esc(e.title),'cs_evidence',{task:t.id,evidence:e.id},'primary full'));}
  else if(step===2)card=now('Chọn một phương án có căn cứ','Đối chiếu các nguồn rồi chọn. Hệ thống kiểm điều kiện trước khi nhận.',choices);
  else if(t.status==='proposed')card=now(`Phương án: ${sol?.[1]||''}`,'Mới là đề nghị. Gửi việc cho đầu mối để bắt đầu.',button('Gửi việc cho đầu mối '+icon('arrow',15),'executeCS',{},'primary full'));
  else if(t.status==='executing')card=now(`Đang thực hiện: ${sol?.[1]||''}`,'Đầu mối đã nhận việc. Kết quả về sau hai nhịp.',commandButton('Xem phản hồi phối hợp','advance',{},'primary full'));
  else if(step===4)card=now('Kết quả đã về','Kiểm xác nhận với khách trước khi đóng.',commandButton(icon('search',16)+' Kiểm kết quả','cs_confirm',{task:t.id},'primary full'));
  else card=now('Kết quả đã kiểm chứng','Có thể đóng vụ. Khách sẽ đánh giá theo vụ thật.',button(icon('check',16)+' Hoàn tất & đóng vụ','closeCS',{},'primary full'));
  const change=t.status==='proposed'?`<section class="dw-sec dw-change" aria-label="Đổi phương án"><h3>Đổi phương án?</h3>${choices}</section>`:'';
  const handover=t.identity&&t.status==='understood'&&!t.handed_over?`<section class="dw-alt"><p class="dw-hint">Chưa chắc hướng xử lý? Bàn giao cho chị Mai kèm nguồn đã đọc${t.inspected.length<2?' (cần đọc ít nhất 2 nguồn)':''}.</p>${commandButton('Bàn giao cùng chị Mai','cs_handover',{task:t.id},'ghost',t.inspected.length<2)}</section>`:'';
  const evidence=`<section class="dw-sec" aria-label="Chứng cứ"><div class="dw-sec-head"><h3>Chứng cứ</h3><span class="dw-count${read===t.evidence.length?' ok':''}">${read}/${t.evidence.length}</span></div><ul class="dw-evlist">${t.evidence.map(e=>{const open=e.text!=null;
    return `<li class="dw-ev${open?' done':''}"><span class="dw-mark" role="img" aria-label="${open?'Đã mở':'Chưa mở'}">${open?'✓':''}</span><div><b>${esc(e.title)}</b>${open?`<p>${esc(e.text)}</p>`:t.identity?'':'<small>Xác minh để mở</small>'}</div>${!open&&t.identity?commandButton('Mở','cs_evidence',{task:t.id,evidence:e.id},'ghost'):''}</li>`;}).join('')}</ul></section>`;
  const notes=`<p class="dw-hint">🛡️ Tiền hoàn đi từ quỹ công ty, không trừ ví bạn. Chỉ đóng vụ khi kết quả đã kiểm chứng.</p>${room().upgrades.includes('workbench')?notice('Bàn kiểm hai bước: so yêu cầu của khách với chứng cứ đóng gói/giao nhận, không coi một trạng thái đơn lẻ là kết luận.','blue','search'):''}`;
  const log=t.timeline.length?fold(`Nhật ký vụ · ${t.timeline.length} dòng`,`<ol class="dw-log">${t.timeline.map(line=>`<li>${esc(line)}</li>`).join('')}</ol>`):'';
  const sub=`${channel}${t.value?` · đơn ${fmt(t.value)} xu`:''}`;
  return `<div class="career-job dw dw-cs">${dwWho(t,sub)}${tracker}<div class="dw-cs-grid"><div class="dw-cs-work">${card}${change}${handover}</div><div class="dw-cs-facts">${evidence}${notes}${log}</div></div></div>`;
}
function chatView(){
  const id=ui.npc||activeTask()?.npc||api.content.npcs.find(n=>n.career_id===career()).id,n=npc(id),c=room();ui.npc=id;
  const messages=c.chats[id]||[],memories=c.memories.filter(m=>m.npc===id),t=c.tasks.find(t=>t.npc===id&&!ended(t)),relation=c.relationships[id]||0,ai=ui.ai[id];
  const rel=relation>=40?'Thân thiết':relation>5?'Bạn quen':relation?'Đã từng giúp nhau':'Lần đầu gặp';
  const bubbles=messages.length?messages.map((m,i)=>`<div class="bubble ${m.role==='user'?'user':'npc'}">${m.role==='npc'&&ai&&i===messages.length-1&&ai.mode==='ai'?pill('AI'):''}<div>${esc(ai&&i===messages.length-1&&ai.mode==='ai'?ai.text:m.text)}</div></div>`).join(''):`<div class="bubble npc"><div>${esc(t?.opening||'Chào bạn! Hôm nay mình trò chuyện một chút nhé?')}</div></div>`;
  const quick=[['Bạn cần gì hôm nay?','Bạn cần gì hôm nay?'],['Nhớ lần trước không?','Bạn nhớ lần trước mình giúp gì không?'],['Hôm nay thế nào?','Hôm nay bạn thấy thế nào?']];
  return `<header class="sheet-head chat-head"><span class="chat-avatar">${portrait(n,48)}</span><div class="grow"><span class="eyebrow">${esc(n.role||'Trò chuyện')}</span><h2>${esc(n.display_name)}</h2><p>${rel}${memories.length?` · ${memories.length} kỷ niệm chung`:''}</p></div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`+
    `<div class="sheet-body chat-body">${t?`<div class="chat-task"><span class="grow">${icon('flag',14)} ${esc(t.title)}</span>${t.known?'':commandButton('Hỏi rõ nhu cầu','ask',{task:t.id},'small ghost')}${button('Mở việc '+icon('arrow',13),'job',{task:t.id},'small primary')}</div>`:''}<div id="messages" class="chat-messages" role="log" aria-live="polite">${bubbles}</div>`+
    `<details class="chat-about"><summary>Về ${esc(n.display_name)}</summary>${n.personality?`<p class="small">${esc(n.personality)}</p>`:''}<div class="progress" aria-hidden="true"><i style="width:${Math.min(100,Math.max(4,relation))}%"></i></div>${memories.slice(-3).reverse().map(m=>`<div class="memory">${esc(m.text)}${m.day?`<br><small class="muted">Ngày ${m.day}</small>`:''}</div>`).join('')}${messages.length?button('Xóa tin nhắn','clearChat',{},'small ghost space-top'):''}</details></div>`+
    `<footer class="sheet-foot chat-foot"><div class="quick-replies">${quick.map(([l,text])=>button(l,'quickChat',{text},'ghost small')).join('')}</div><form id="chatForm" class="chat-form"><textarea id="chat-input" data-preserve rows="1" placeholder="Nói gì đó với ${esc(n.display_name)}…" maxlength="500" required aria-label="Tin nhắn tới ${esc(n.display_name)}"></textarea><button type="submit" class="btn primary" aria-label="Gửi">${icon('send',17)}<span>Gửi</span></button></form>${api.ai.configured&&api.state.settings.aiConsent?'<small class="chat-mode">AI có thể diễn đạt lại câu trả lời.</small>':''}</footer>`;
}
function phoneView(){const c=room(),reviews=c.feed.filter(p=>p.stars).length;markFeedSeen();
  const posts=c.feed.map(p=>`<article class="post" id="${p.id}"><div class="row">${p.npc==='player'?`<span class="avatar-small">${esc(p.author.slice(0,1))}</span>`:portrait(npc(p.npc),42)}<div class="grow"><span class="author">${esc(p.author)}</span><div class="post-meta">Ngày ${p.day}${p.npc==='player'?' · Bài của bạn':''}</div></div>${p.kind==='review'?pill('Đánh giá','amber'):''}</div><div class="post-text">${p.stars?`<div class="stars" aria-label="${p.stars} trên 5 sao">${'★'.repeat(p.stars)}${'☆'.repeat(5-p.stars)}</div>`:''}${esc(p.text)}</div>`+
    `<div class="post-actions">${commandButton(icon('heart',14)+' '+(p.liked?'Đã thích':'Thích'),'feed_like',{post:p.id},'small'+(p.liked?' liked':''))}${p.feedback?button(icon('chat',14)+' Trả lời đánh giá','fbGo',{post:p.id},'small'):''}${p.kind==='review'?button(icon('flag',14)+' Trao đổi tình huống','reviewFollowup',{post:p.id},'small'):''}${p.comments.length?`<small class="muted">${p.comments.length} lời nhắn</small>`:''}</div>`+
    `${p.comments.map((co,index)=>`<div class="comment ${co.npc==='player'?'owner-reply':''}"><strong>${esc(co.author)}${co.npc==='player'?' '+pill('Bạn'):''}</strong><p>${esc(co.text)}</p>${co.npc==='player'?button('Sửa','expReplyEdit',{post:p.id,index},'small ghost'):''}</div>`).join('')}`+
    `${p.feedback?'':`<details class="reply-more"><summary>${icon('chat',14)} Trả lời</summary><form class="reply-form" data-reply-post="${p.id}"><input class="input" id="reply-${p.id}" data-preserve maxlength="500" required placeholder="Trả lời ${esc(p.author)}…" aria-label="Trả lời ${esc(p.author)}"><button type="submit" class="btn primary" aria-label="Gửi trả lời">${icon('send',15)}</button></form></details>`}</article>`).join('');
  return header('Chuyện phố','Lời nhắn và đánh giá quanh tiệm.','BẢNG TIN KHU PHỐ')+`<div class="sheet-body feed-v6"><form id="postForm" class="feed-composer"><span class="avatar-small" aria-hidden="true">${esc(api.state.name.slice(0,1))}</span><textarea id="post-text" data-preserve rows="2" maxlength="500" required placeholder="Hôm nay tiệm có chuyện gì? Kể hàng xóm nghe…" aria-label="Nội dung bài viết"></textarea><button class="btn primary" type="submit">${icon('send',15)} Đăng</button></form>`+
    `${reviews?`<button type="button" class="feed-rating" data-action="feedback"><b>★ ${c.rating}</b><span>${reviews} đánh giá của khách</span><span class="grow"></span><span class="feed-rating-go">Xem tất cả ${icon('chevron',13)}</span></button>`:''}${posts||empty('Bảng tin còn yên ắng','Phục vụ vị khách đầu tiên hoặc đăng một lời chào nhé.','mail')}</div>`+footer('',commandButton(icon('refresh',14)+' Xem lời nhắn mới','advance',{},'ghost'));}
function eventView(){const e=room().event;if(!e)return header('Hôm nay vẫn thật bình thường','Bạn có thể thử một câu chuyện trong Sổ tay.')+`<div class="sheet-body">${empty('Chưa có chuyện cần xử lý','Hoàn thành một công việc để gặp một chuyện trong ngày, hoặc diễn tập bất kỳ tình huống nào.','coffee')}${button('Xem 24 tình huống của nghề','library',{},'primary space-top')}</div>`;
 const n=npc(e.npc),opt=e.options.find(o=>o.id===e.chosen);return header(esc(e.title),e.practice?'Diễn tập · không ảnh hưởng tiền, đánh giá hay quan hệ.':'Một chuyện vừa xảy ra trong ca. Kiểm dữ kiện trước khi kết luận.',e.practice?'DIỄN TẬP':'CHUYỆN ĐỜI THƯỜNG')+`<div class="sheet-body"><div class="event-hero">${portrait(n,64)}<div><span class="eyebrow">${esc(n.display_name)}</span><p>${esc(e.opening)}</p></div></div><div class="event-evidence">${e.evidence.map(ev=>`<article class="evidence-card"><span class="eyebrow">${esc(ev.source)}</span><h4>${icon(ev.text?'check':'eye',16)} ${esc(ev.title)}</h4>${ev.text?`<p>${esc(ev.text)}</p>`:commandButton('Kiểm dữ kiện này','event_read',{evidence:ev.id},'ghost small')}</article>`).join('')}</div><h3 class="space-top">Bạn muốn xử lý như thế nào?</h3><div class="choice-grid">${e.options.map(o=>`<button class="choice ${e.chosen===o.id?'selected':''}" data-command="event_choose" data-payload="${esc(JSON.stringify({choice:o.id}))}" ${e.read.length<2||!['noticed','investigating','proposed'].includes(e.stage)?'disabled':''}><strong>${esc(o.label)}</strong><small>${o.cost?o.cost+' xu từ quỹ nghề':'Không tốn xu'}${e.practice?' · chỉ diễn tập':''}</small></button>`).join('')}</div>${e.stage==='proposed'?`<div class="execution"><h4>Đề nghị đã rõ</h4><p class="small">${esc(opt.response)}</p>${button('Xác nhận phương án','confirmEvent',{},'primary')}</div>`:e.stage==='executing'?`<div class="execution"><h4>Thực hiện điều đã thống nhất</h4>${opt.steps.map((s,i)=>`<div class="step-item"><span class="step-circle ${i<e.step?'done':''}">${i<e.step?icon('check',13):i+1}</span>${esc(s)}</div>`).join('')}${button(icon('play',14)+' '+esc(opt.steps[e.step]),'eventStep',{},'primary full space-top')}</div>`:e.stage==='resolved'?`<div class="execution"><h3>${icon('check',20)} Chuyện đã có kết quả</h3><p class="small">Đã thực hiện: <strong>${esc(opt.label)}</strong>.</p><p class="small-note">${e.practice?'Đây là diễn tập, tiền và quan hệ vẫn giữ nguyên.':'Mọi người sẽ nhớ chuyện này. Ngày mai có thể có lời nhắn nối tiếp.'}</p>${commandButton('Cất câu chuyện','event_dismiss',{},'primary')}</div>`:(e.read.length<2?notice('Xem ít nhất hai dữ kiện rồi mới chọn cách xử lý nhé.','','search'):'')}</div>`+footer('',e.practice?commandButton('Cất diễn tập','event_dismiss',{},'ghost small'):button('Quay lại quầy','close',{},'ghost small'));
}
function peopleView(){const c=room();return header('Bạn quen','Những người bạn gặp quanh tiệm.','KHU PHỐ')+`<div class="sheet-body"><div class="npc-grid">${api.content.npcs.filter(n=>n.career_id===career()).map(n=>`<article class="npc-card">${portrait(n,72)}<h3>${esc(n.display_name)}</h3>${pill(esc(n.role))}<p>${esc(n.personality)}</p><div class="small muted">${c.memories.filter(m=>m.npc===n.id).length} ký ức · ${c.relationships[n.id]||0} lần gắn kết</div>${button(icon('chat',14)+' Trò chuyện','chat',{npc:n.id},'small primary full')}</article>`).join('')}</div></div>`;}
function journalView(){const c=room(),tab=ui.journalTab;let inner='';
  if(tab==='quests')inner=c.quest_progress.map(progress=>{const q=api.content.quests.find(q=>q.id===progress.id);return `<article class="quest-card"><div class="row spread"><div><span class="eyebrow">CÂU CHUYỆN · ${q.id}</span><h3>${esc(q.title)}</h3></div>${icon(progress.claimed?'award':'book',26)}</div><p>${esc(q.story)}</p>${progress.steps.map(s=>`<div class="quest-step ${s.done?'done':''}"><span class="step-circle ${s.done?'done':''}">${s.done?icon('check',12):icon('flag',12)}</span><span class="grow">${esc(s.title)}</span><span class="small">${Math.min(s.current,s.goal)} / ${s.goal}</span></div>`).join('')}<div class="row spread space-top">${pill(`Kỷ niệm + ${q.reward} xu`,'amber')}${commandButton(progress.claimed?'Đã lưu kỷ niệm':'Nhận kỷ niệm','quest_claim',{quest:q.id},'small primary',!progress.ready||progress.claimed)}</div></article>`;}).join('');
  else if(tab==='history')inner=c.journal.slice().reverse().slice(0,80).map(l=>`<div class="history-row"><small>Ngày ${l.day}<br>Nhịp ${l.turn}</small><div class="grow">${esc(l.text)}</div>${icon(({money:'coin',event:'flag',day:'sun',match:'link',correction:'check',fact:'chat',upgrade:'plant',keepsake:'award'})[l.kind]||'note',15)}</div>`).join('')||empty('Một cuốn sổ còn mới','Những gì bạn thực hiện sẽ được ghi lại ở đây.');
  else if(tab==='memories')inner=c.memories.slice().reverse().map(m=>`<div class="memory"><strong>${esc(npc(m.npc).display_name)}</strong><p>${esc(m.text)}</p>${m.day?`<small class="muted">Ngày ${m.day}</small>`:''}</div>`).join('')||empty('Chưa có ký ức chung','Hoàn thành một việc hoặc một chuyện trong ca để tạo ký ức thật.','people');
  else {const q=ui.libraryQuery.toLocaleLowerCase('vi-VN'),items=api.content.event_catalogue.filter(e=>e.career===career()&&(`${e.id} ${e.title}`.toLocaleLowerCase('vi-VN').includes(q)));inner=notice('Thử bất kỳ tình huống nào. Diễn tập không tính tiền, không đổi quan hệ.','blue','flag')+`<input class="input space-top" id="library-search" data-preserve placeholder="Tìm: review, clip, quên ví, mất hàng…" value="${esc(ui.libraryQuery)}" aria-label="Tìm tình huống"><div class="event-library space-top">${items.map(e=>`<article class="library-item"><small class="muted">Diễn tập</small><h4>${esc(e.title)}</h4>${button('Thử tình huống '+icon('arrow',13),'practice',{event:e.id},'small ghost')}</article>`).join('')||empty('Chưa có tình huống khớp','Thử từ khóa ngắn hơn.')}</div>`;}
  return header('Sổ tay','Câu chuyện, nhật ký và ký ức của tiệm.','SỔ TAY')+`<div class="sheet-body"><nav class="pill-tabs">${[['quests','Câu chuyện'],['history','Nhật ký'],['memories','Ký ức'],['library','24 tình huống']].map(([id,label])=>`<button data-action="journalTab" data-tab="${id}" class="${tab===id?'active':''}">${label}</button>`).join('')}</nav>${inner}</div>`;
}
function decorView(){const c=room(),spots={window:'Bên cửa sổ',corner:'Góc phòng',front:'Gần cửa',center:'Giữa phòng',wall:'Trên tường'};return header('Trang trí & nâng cấp','Đồ mới xuất hiện ngay trong cảnh.','GÓC CỦA BẠN',pill(icon('coin',13)+' '+fmt(c.money)+' xu','amber'))+`<div class="sheet-body"><div class="row spread"><div><h3>Chọn sắc cho căn phòng</h3><p class="muted small">Đổi màu tường không tốn xu.</p></div>${icon('plant',25)}</div><div class="theme-options">${[['boba','Trà sữa'],['warm','Ấm áp'],['sage','Xanh dịu'],['lavender','Tím mây']].map(([id,l])=>commandButton(`${(c.theme||'boba')===id?icon('check',13):icon('sun',13)} ${l}`,'theme',{theme:id},'small '+((c.theme||'boba')===id?'primary':'ghost'))).join('')}</div><div class="upgrade-grid">${api.content.upgrades.filter(u=>!u.careers||u.careers.includes(career())).map(u=>{const owned=c.upgrades.includes(u.id);return `<article class="upgrade-card"><div class="row spread"><span class="upgrade-icon">${icon(u.icon,31)}</span>${pill(owned?'ĐÃ CÓ':u.min_level>c.level?'CẤP '+u.min_level:u.price+' XU',owned?'green':'')}</div><h3>${esc(u.name)}</h3><p>${esc(u.description)}</p>${owned?(u.kind==='decor'?`<select aria-label="Vị trí ${esc(u.name)}" data-decor-item="${u.id}">${Object.entries(spots).filter(([s])=>u.id==='poster'?s==='wall':s!=='wall').map(([id,label])=>`<option value="${id}"${c.decor[u.id]?.spot===id?' selected':''}>${label}</option>`).join('')}</select>`:u.id==='assistant'?commandButton('Nhờ hỗ trợ hôm nay','assistant_help',{},'small',c.assistant_day===c.day):pill('Đang dùng trong nghề','green')):u.min_level>c.level?`<button type="button" class="btn ghost full" disabled>🔒 Mở ở cấp ${u.min_level} (đang cấp ${c.level})</button>`:button(icon('plus',14)+' Đặt trong phòng','buyUpgrade',{item:u.id},'primary full')}</article>`;}).join('')}</div></div>`+footer('Kệ mở rộng tăng sức chứa. Đồ trang trí có thể chuyển vị trí.',button('Xem căn phòng','close',{},'primary'));}
function warehouseView(){const c=room();if(!['mother_baby','pharmacy'].includes(career()))return queueView();const mb=career()==='mother_baby',list=mb?api.content.products:api.content.lots.filter(l=>l.status==='available'),cap=Math.max(c.ops.property.details.stock_cap,c.upgrades.includes('shelf')?24:12);
 // Stock bins with counts, parcels on the way and ONE next step; the server stays authoritative.
 const waiting=c.shipments.filter(s=>s.status!=='received'),arrived=waiting.filter(s=>s.ready_now),onWay=id=>waiting.filter(s=>s.item===id).reduce((n,s)=>n+s.qty,0),low=list.filter(p=>c.stock[p.id]+onWay(p.id)<=2);
 const chip=(n,label,kind)=>n?`<span class="inv-chip ${kind}"><b>${n}</b> ${label}</span>`:'';
 const strip=`<section class="inv-status" aria-label="Tình trạng kho"><div class="inv-chips">${chip(arrived.length,'kiện đã tới · đếm ở dưới','accent')}${chip(waiting.length-arrived.length,'kiện đang giao','info')}${chip(low.length,'mã sắp hết','warn')}${!waiting.length&&!low.length?`<span class="inv-calm">${icon('check',14)} Kho ổn. Đặt thêm khi một mã còn ít.</span>`:''}</div>${!arrived.length&&waiting.length?`<div class="inv-cta">${commandButton(icon('clock',15)+' Chờ một nhịp cho kiện tới','advance',{},'primary')}</div>`:''}</section>`;
 const parcel=s=>{const p=product(s.item);return s.ready_now?`<article class="card inv-crate-card open"><div class="row spread"><strong>${esc(p.name)}</strong>${pill('ĐÃ TỚI','green')}</div><div class="inv-slip"><span>Phiếu giao ghi</span><b>${s.qty} món</b></div><ul class="inv-crate" aria-label="Trong kiện">${Array.from({length:s.actual},()=>`<li>${itemArt(p.icon||'box',32,p.color)}</li>`).join('')}</ul><form class="inv-receive" data-receive="${s.id}"><label for="count-${s.id}">Bạn đếm được</label><input id="count-${s.id}" class="input" type="number" min="1" max="12" inputmode="numeric" required placeholder="0" style="width:88px"><button class="btn primary" type="submit">${icon('check',15)} Kiểm & nhập kho</button></form></article>`:`<article class="card order-row"><div class="row spread"><div><strong>${esc(p.name)} · ${s.qty} món</strong><small class="muted block">Đã trả ${fmt(s.cost)} xu · tới sau khoảng hai nhịp</small></div>${pill('ĐANG GIAO','amber')}</div></article>`;};
 const row=p=>{const q=c.stock[p.id],on=onWay(p.id),held=q-c.available[p.id],room=Math.max(0,cap-q-on),max=Math.min(6,room),state=q===0?'out':q+on<=2?'low':'';
  return `<div class="inventory-row inv-row ${state}">${itemArt(p.icon||'box',45,p.color)}<div class="grow"><h4>${esc(p.name)}</h4><small><b class="inv-big">${q}</b>/${cap} trên kệ${on?` · <span class="inv-flag info">+${on} đang giao</span>`:''}${held?` · đang giữ ${held}`:''} · ${fmt(p.cost)} xu/món${!mb?` · ${esc(p.id)}`:''}</small><span class="inv-bar" aria-hidden="true"><i style="width:${Math.round(q/cap*100)}%"></i><i class="on" style="width:${Math.round(on/cap*100)}%"></i></span></div>`+
   `<span class="inv-row-act"><input class="input" type="number" id="qty-${p.id}" min="1" max="${Math.max(1,max)}" value="${Math.min(Math.max(1,max),state?Math.min(4,Math.max(1,max)):1)}" aria-label="Số nhập ${esc(p.name)}" style="width:72px"${max?'':' disabled'}>${button(max?'Đặt nhập':'Kệ đầy','restock',{item:p.id},'small'+(state&&max?' primary':''))}${!mb?(c.held_lots.includes(p.id)?commandButton('Cô Thu kiểm lại','ph_release',{lot:p.id},'small primary'):commandButton('Tạm giữ','ph_quarantine',{lot:p.id},'small ghost')):''}</span></div>`;};
 return header('Kho nhỏ sau tiệm','Đặt hàng chưa cộng kho. Kiểm đúng số hộp khi kiện tới.','KHO HÀNG · SỨC CHỨA '+cap+' / MÃ')+`<div class="sheet-body">${strip}${waiting.length?`<h3>Kiện hàng</h3>${arrived.map(parcel).join('')}${waiting.filter(s=>!s.ready_now).map(parcel).join('')}<div class="divider"></div>`:''}<h3>Hàng trên kệ</h3>${list.map(row).join('')}</div>`+footer('Tồn được giữ riêng cho từng đơn, không bán cùng một món hai lần.',commandButton('Chờ một nhịp','advance',{},'ghost small'));
}
function albumView(){const c=room();return header('Kỷ niệm','Chụp lại góc tiệm bạn đã chăm chút. Giữ 6 ảnh gần nhất.','ALBUM')+`<div class="sheet-body"><div class="row spread"><span></span>${button(icon('camera',16)+' Chụp góc hiện tại','photo',{},'primary')}</div><div class="album-grid space-top">${c.album.map(p=>`<article class="polaroid"><img src="${esc(p.image)}" alt="${esc(p.title)}" loading="lazy"><p>${esc(p.title)}</p><div class="row spread"><small>Ngày ${p.day} · ${esc(meta().place)}</small>${button(icon('download',13),'downloadPhoto',{id:p.id},'ghost small')}</div></article>`).join('')||empty('Một album chưa có ảnh','Đặt một chậu cây hoặc giữ lại căn phòng đầu tiên của bạn.','camera')}</div>${c.quests_claimed.length?`<h3 class="space-top">Kỷ vật câu chuyện</h3>${c.quests_claimed.map(id=>`<div class="memory">${icon('award',17)} ${esc(api.content.quests.find(q=>q.id===id).keepsake)}</div>`).join('')}`:''}</div>`;
}
const CLOSE_LABELS={markdown_sold:'Bánh giảm giá đã bán',markdown_income:'Thu từ bánh giảm giá (xu)',discarded:'Món phải bỏ',wilted:'Cành hoa héo',wilted_value:'Giá trị hoa héo (xu)',sales:'Doanh thu quầy (xu)',ledger_total:'Tổng sổ ghi nợ (xu)',repaired:'Máy đã sửa xong',returned:'Máy trả lại khách',hazards:'Lỗi an toàn',expired_units:'Nông sản quá hạn',eggs_tomorrow:'Trứng còn trong ổ',hungry_hens:'Gà chưa được cho ăn',ripe_tomorrow:'Luống chín ngày mai',delivered:'Đơn đã giao',failed:'Giao thất bại',refused:'Đơn đã từ chối nhận',km:'Quãng đường (ô phố)',fees:'Phí giao (xu)',fuel:'Xăng còn (%)',settled_at_close:'COD tự nộp cuối ca (xu)',food_cancelled:'Đơn đồ ăn bị hủy',arrived:'Khách nhận phòng',walked:'Khách phải chuyển chỗ',moved:'Khách đổi phòng',dirty:'Phòng cần dọn',staying:'Bé đang ở lại',free:'Chuồng trống',posted:'Bút toán đã ghi',dossiers:'Hồ sơ hoàn tất',milestones:'Mốc kỳ kế toán',balanced:'Sổ cân đối'};
/** Career-specific part of the day summary: module.summary(data,x) or a generic list. */
function careerCloseSummary(){
  const data=room().shift_summary?.career??room().shift_summary?.experiences?.counter;if(!data||typeof data!=='object')return '';
  const mod=careerUI(career());
  if(mod?.summary){try{return mod.summary(data,careerContext(env()))||'';}catch(error){console.error(error);}}
  const show=v=>typeof v==='boolean'?(v?'Có':'Không'):Array.isArray(v)?v.map(x=>typeof x==='object'?(x.name||x.title||x.label||''):x).filter(Boolean).join(', '):typeof v==='number'?fmt(v):String(v);
  const rows=Object.entries(data).filter(([k,v])=>CLOSE_LABELS[k]&&!(v===0||v===false&&k!=='balanced'||Array.isArray(v)&&!v.length)).map(([k,v])=>`<div class="kv-row"><span>${esc(CLOSE_LABELS[k])}</span><b>${esc(show(v))}</b></div>`).join('');
  const lines=[...(Array.isArray(data.lines)?data.lines:[]),...(typeof data.note==='string'&&data.note?[data.note]:[])].filter(x=>typeof x==='string');
  if(!rows&&!lines.length)return '';
  return `<article class="card space-top"><h4 class="section-title">${icon('clipboard',15)} Sổ nghề hôm nay</h4>${rows?`<div class="kv">${rows}</div>`:''}${lines.length?`<ul class="small">${lines.map(l=>`<li>${esc(l)}</li>`).join('')}</ul>`:''}</article>`;
}
/** End of day: headline, three big numbers, what needs you, then the details. One primary CTA in the foot. */
function summaryView(){
  const c=room(),s=c.shift_summary,m=meta(),next=c.open?button('Về quầy','close',{},'primary big'):button(icon('play',15)+' Bắt đầu ngày '+c.day,'start',{},'primary big');
  if(!s)return header('Mình khép ca nhé?','Việc chưa xong được giữ nguyên để làm tiếp.','TỔNG KẾT NGÀY')+`<div class="sheet-body">${empty('Chưa có ngày nào khép lại','Làm vài việc nhỏ rồi quay lại đây nhé.','sun')}</div>`+footer('',next);
  const rv=s.reviews||{},job=s.job||null,ops=s.operations,net=Number(s.net)||0;
  const stat=(cls,big,label,sub='')=>`<div class="sum-stat ${cls}"><strong>${big}</strong><small>${label}</small>${sub?`<em>${sub}</em>`:''}</div>`;
  const stats=`<div class="sum-stats">${stat(net>=0?'good':'bad',`${net>=0?'+':'−'}${fmt(Math.abs(net))}<span> xu</span>`,'Thay đổi trong ca',`thu ${fmt(s.income)} · chi ${fmt(s.cost)}`)}${stat('',`${s.completed}`,'Việc đã xong',s.carried?`${s.carried} việc để mai`:'')}${stat('star',rv.count?`★ ${rv.average}`:'—',rv.count?`${rv.count} đánh giá mới`:'Chưa có đánh giá mới')}</div>`;
  const notes=[];
  if(job?.boss)notes.push(`<article class="sum-boss"><span class="eyebrow">Một cuộc gặp may mắn</span><h3>${esc(job.boss.org)} · ${esc(job.boss.title)}</h3><p>${esc(job.boss.text)}</p>${button(icon('mail',15)+' Xem thư mời','bossOffer',{career:job.boss.career},'primary small')}</article>`);
  if(s.incidents)notes.push(incidentSummary(s.incidents));
  if(s.happen)notes.push(happenSummary(s.happen));
  const jr=s.journey;
  if(jr&&(jr.living||jr.upkeep||jr.salary))notes.push(notice(`<b>Ngày sống thứ ${jr.life_day}</b><p>Tiền phòng và cơm nước: −${fmt(jr.living)} xu.</p>${jr.upkeep?`<p>Duy trì các nơi làm khác: −${fmt(jr.upkeep)} xu.</p>`:''}${jr.salary?`<p>Lương về ví: +${fmt(jr.salary)} xu.</p>`:''}<p>Ví của bạn còn <b>${fmt(jr.wallet)} xu</b>.</p>${jr.wallet<0?'<p>Ví đang nợ: trả hết nợ thì câu chuyện mới đi tiếp.</p>':''}`,jr.wallet<0?'amber':'','home'));
  if(job?.salary)notes.push(notice(`<b>Lương hôm nay +${fmt(job.salary)} xu</b>${job.result==='official'?'<p>Hết thử việc: bạn đã được ký hợp đồng chính thức! 🎉</p>':job.result==='extended'?'<p>Thử việc được gia hạn thêm 2 ngày. Cố lên nhé!</p>':job.probation?'<p>Đang thử việc: nhận 85% lương.</p>':''}`,'success','briefcase'));
  if(rv.open||(rv.count&&rv.weakest&&rv.average<4.5))notes.push(notice(`${rv.count&&rv.weakest&&rv.average<4.5?`Khách góp ý nhiều nhất về <b>${esc(rv.weakest)}</b>.`:''}${rv.open?` Còn ${rv.open} đánh giá chờ bạn trả lời.`:''}<br>${button('Xem đánh giá','feedback',{filter:rv.open?'open':'all'},'small')}`,'amber','star'));
  if(ops?.unpaid)notes.push(notice(`<b>Sổ tiệm: còn ${fmt(ops.unpaid)} xu cần trả</b><p>Lương ${fmt(ops.wages)} · điện nước ${fmt(ops.utilities)} · thuê ${fmt(ops.rent_accrued)} xu${ops.period?' · vừa kết kỳ thuế':''}</p>${button('Mở sổ thu chi','finance',{},'small')}`,'','mail'));
  const details=`<details class="sum-more space-top"><summary>Chi tiết cả ngày</summary>${experienceSummary(c)}<div class="kv"><div class="kv-row"><span>Xu thu vào</span><b>+${fmt(s.income)}</b></div><div class="kv-row"><span>Xu đã chi trong ca</span><b>−${fmt(s.cost)}</b></div><div class="kv-row"><span>Chuyện đã xử lý</span><b>${s.events}</b></div></div></details>`;
  return header(`Ngày ${s.day} đã khép lại`,esc(c.life.shop_name||m.place),'TỔNG KẾT NGÀY')+`<div class="sheet-body summary-v6"><div class="sum-hero"><span class="sum-sun" aria-hidden="true">${icon('sun',34)}</span><p>${esc(s.headline||'Một ngày nữa đã có chuyện để nhớ.')}</p></div>${stats}${notes.length?`<div class="stack space-top">${notes.join('')}</div>`:''}${careerCloseSummary()}${accountNudge(env())}${details}</div>`+footer('',button('Đọc lời nhắn','phone',{},'ghost')+next);
}
function helpView(){const guides={teacher:['Soạn ba bước: ví dụ → thử theo nhóm → câu hỏi cuối tiết.','Điểm danh đúng ghế có mặt; hỗ trợ theo nhu cầu từng bạn.','Đọc câu trả lời, đánh dấu đúng/chưa đúng và chọn phản hồi.','Khép tiết khi mọi bạn có mặt đã được hỗ trợ.'],tour_guide:['Chọn tuyến có đủ điểm đoàn thích và một nơi nghỉ.','Kiểm đủ khách; xác nhận vé trước khi đi.','Mỗi điểm: đọc chuyện, trả lời câu hỏi, tìm chi tiết chụp ảnh.','Kiểm lại đoàn trước khi đi tiếp, rồi gửi bưu thiếp.'],milk_tea:['Hỏi món khách gọi.','Chọn trà, vị và topping; chỉnh size, đường, đá.','Kiểm công thức trước khi dán nắp.','Giao ly, đọc review; chuẩn bị mẻ mới và theo dõi hạn dùng.'],mother_baby:['Hỏi khách cần gì.','Chọn đúng món và số lượng từ kệ.','Gói theo màu được yêu cầu, hoặc bỏ qua khi khách không cần.','Kiểm đơn ở Thu ngân, xác nhận giao.'],pharmacy:['Hỏi lại phiếu để biết mã và số lượng.','Chọn mã trong bộ lọc, đọc nhãn lô A hợp lệ.','Lấy đúng lượng, đánh dấu ba bước rồi kiểm khay.','Bàn giao hoặc chuyển cô Thu nếu ngoài phạm vi.'],accounting:['Mở từng bản gốc, đọc mã tham chiếu.','Loại bản trùng có căn cứ hoặc sửa số từ nguồn gốc.','Chọn phiếu và giao dịch tương ứng, ghép từng nhóm.','Khi mọi nguồn đều được ghép, kiểm và bàn giao.'],customer_care:['Xác minh mã đơn của khách.','Mở cả ba chứng cứ, không kết luận từ một nguồn.','Chọn phương án, xác nhận gửi việc tới đầu mối.','Qua hai nhịp, kiểm kết quả và đóng vụ.']};
  const m=meta(),steps=guides[career()]||[`${m.work||'Khách'}: chọn một việc đang chờ.`,`${m.station||'Bàn làm việc'}: tự tay làm từng bước rồi bàn giao.`,'Đánh giá: đọc lời khách và trả lời thật lòng.','Khép ca khi xong việc. Mai lại là một ngày mới.'];
  return header('Cách chơi',esc(m.place||''),'HƯỚNG DẪN')+`<div class="sheet-body"><div class="help-grid"><section class="card"><h3>${esc(m.short||m.name||'')}</h3><ol class="help-steps">${steps.map(s=>`<li>${esc(s)}</li>`).join('')}</ol>${button('Làm việc ngay '+icon('arrow',14),'job',{},'primary')}</section><section class="card"><h3>Chạm vào cảnh</h3><ul class="help-list"><li>Chạm sàn để đi, chạm người hoặc đồ vật để làm.</li><li>Các nút ở thanh dưới làm được y như vậy.</li><li>Bàn phím: WASD hoặc mũi tên để đi, E để dùng đồ gần nhất.</li><li>Tạm dừng hay đóng trình duyệt đều không mất việc đã làm.</li></ul></section></div><h3 class="section-title">Muốn đổi nhịp?</h3><div class="chip-row">${button(icon('sparkle',15)+' Trò nhỏ','workshop',{},'ghost small')}${button(icon('award',15)+' Hộ chiếu','passport',{},'ghost small')}${button(icon('flag',15)+' Tình huống','situation',{},'ghost small')}${EXT.includes(career())?'':button(icon('book',15)+' Sổ tay','journal',{},'ghost small')}${button(icon('grid',15)+' Hành trình','home',{},'ghost small')}${button(icon('settings',15)+' Cài đặt','settings',{},'ghost small')}</div></div>`;}


/* Interaction controller. Native dialogs keep keyboard focus inside a workbench. */
let confirmResolve=null;
function confirmAction(title,message,label='Xác nhận'){
  $('#confirmContent').innerHTML=`<span class="eyebrow">MỘT BƯỚC XÁC NHẬN</span><h2>${esc(title)}</h2><p class="muted">${esc(message)}</p><div class="row">${button('Để mình xem lại','confirmNo',{},'ghost')}${button(esc(label),'confirmYes',{},'primary')}</div>`;
  $('#confirmDialog').showModal();return new Promise(resolve=>{confirmResolve=resolve;});
}
function inputPrompt(title,value,maxLength=100){
  $('#confirmContent').innerHTML=`<span class="eyebrow">GÓC CỦA BẠN</span><h2>${esc(title)}</h2><textarea class="input" id="cozy-prompt" maxlength="${maxLength}" rows="3">${esc(value)}</textarea><div class="row space-top">${button('Để sau','confirmNo',{},'ghost')}${button('Lưu','confirmYes',{},'primary')}</div>`;
  $('#confirmDialog').showModal();$('#cozy-prompt').focus();return new Promise(resolve=>{confirmResolve=ok=>resolve(ok?$('#cozy-prompt').value:null);});
}
function finishConfirm(value){$('#confirmDialog').close();confirmResolve?.(value);confirmResolve=null;document.body.append($('#toasts'));}
$('#confirmDialog').addEventListener('cancel',e=>{e.preventDefault();finishConfirm(false);});
$('#sheet').addEventListener('cancel',e=>{e.preventDefault();if(api.state?.current)closeSheet();});
$('#sheet').addEventListener('close',()=>{document.body.append($('#toasts'));
  // The close event is async: the sheet may already be reopened with another view.
  if($('#sheet').open)return;
  if(ui.view){ui.view=null;ui.ai={};world.paused=ui.paused;}
  // Rail/dock highlight follows the open sheet.
  if(api.state&&api.state.current)renderMain();});
async function start(){if(needsJob()){openSheet('jobapp');return;}const r=await cmd('start_day');if(r){ui.task=null;closeSheet();world.say(meta().greeting);}}
async function selectCareer(id){
  ui.task=null;ui.docs.clear();ui.transactions.clear();ui.ai={};ui.phFilter='';ui.jobTab='shelf';
  const r=await cmd('select_career',{}, {career:id,quiet:true});if(!r)return;
  closeSheet();world.say(meta().greeting);setPaused(false);if(needsJob())openSheet('jobapp');else if(!room().open)openSheet('prepare');
}
async function openJob(id,tab){
  const target=id||room().active_task||room().tasks.find(t=>!ended(t))?.id;
  if(target!==ui.task){ui.docs.clear();ui.transactions.clear();ui.phFilter='';ui.lessonSequence=[];ui.tourRoute=[];}
  ui.task=target;ui.jobTab=tab||(ui.jobTab||'shelf');
  if(target){const t=room().tasks.find(t=>t.id===target);if(t&&!ended(t)&&target!==room().active_task)await cmd('task_select',{task:target},{quiet:true});}
  openSheet('job',{task:target,jobTab:tab||ui.jobTab});
}
function interact(id){sound.unlock();sound.click();if(ui.paused)return;
  if(id.startsWith('staff:')){ui.staffId=id.slice(6);openSheet('operations',{opsTab:'staff'});return;}
  if(id.startsWith('ops:')){openSheet('operations',{opsTab:id.slice(4)});return;}
  if(id==='officer'){openSheet('operations',{opsTab:'security'});return;}if(id.startsWith('npc:')){openSheet('chat',{npc:id.slice(4),task:null});return;}
  if(id==='event'){openSheet('event');return;}
  if(id==='pet'){world.pet();return;}
  if(id==='assistant'){cmd('assistant_help');return;}
  if(id==='door'){if(room().open)handleAction('end',{});else openSheet('prepare');return;}
  if(id==='board'){openSheet('phone');return;}
  if(id==='warehouse'){openSheet(career()==='milk_tea'?'prepare':['mother_baby','pharmacy'].includes(career())?'warehouse':room().inventory?'inventory':'queue');return;}
  if(['shelf','workbench','counter','evidence'].includes(id)){const tab=career()==='mother_baby'?(id==='workbench'?'pack':id==='counter'?'checkout':'shelf'):'shelf';openJob(null,tab);return;}
}
async function talk(text){if(!ui.npc||!text.trim())return;const id=ui.npc;delete ui.ai[id];const r=await cmd('talk',{npc:id,text},{quiet:true});if(!r)return;ui.suggestions[id]=r.suggestions||[];world.say(r.reply,id);renderSheet();if(api.state.settings.aiConsent&&api.ai.configured){const answer=await api.aiReply(id);if(answer.mode==='ai'){ui.ai[id]=answer;if(ui.view==='chat'&&ui.npc===id)renderSheet();}}}
async function handleAction(action,data,el){
  switch(action){
    case'close':closeSheet();break;
    case'confirmNo':finishConfirm(false);break;
    case'confirmYes':finishConfirm(true);break;
    case'staff':case'finance':case'security':case'property':openSheet('operations',{opsTab:action});break;
    case'operations':openSheet('operations',{opsTab:room().ops?.alerts?.[0]?.tab||ui.opsTab||'staff'});break;
    case'reconnect':try{await api.refresh();toast('Đã kết nối lại.','good');}catch{toast('Vẫn chưa kết nối được. Thử lại sau một chút nhé.',true);}renderMain();break;
    case'opsTab':openSheet('operations',{opsTab:data.tab});break;
    case'staffChat':ui.staffId=data.employee;openSheet('operations',{opsTab:'staff'});setTimeout(()=>$('#staff-message')?.focus(),0);break;
    case'opsDo':{
      const payload=JSON.parse(data.payload||'{}');
      if(data.confirm){if(!await confirmAction('Xác nhận việc của tiệm',data.confirm,'Đồng ý thực hiện'))break;payload.confirm=true;}
      const r=await cmd(data.op,payload);
      if(r){if(data.op==='ops_hire')ui.staffId=payload.candidate;if(data.op==='ops_case_demo')ui.opsTab='security';if(data.op==='ops_incident_demo')ui.opsTab='staff';renderSheet();}
      break;
    }
    case'prepare':case'prices':case'workshop':case'passport':case'town':openSheet(action);break;
    case'expDo':{const p=JSON.parse(data.payload||'{}');
      if(data.op==='life_activity_start'&&room().life.activity?.status==='playing'&&!await confirmAction('Đổi trò nhỏ?','Tiến trình trò nhỏ đang làm sẽ được thay bằng ván mới. Công việc ở quầy được giữ nguyên.','Đổi trò'))break;
      if(data.confirm&&!await confirmAction('Xác nhận thao tác',data.confirm,'Đồng ý'))break;
      if(data.confirm)p.confirm=true;const r=await cmd(data.op,p);if(r){ui.activityCard=null;if(data.op==='life_activity_start'&&ui.view==='town')openSheet('workshop');else renderSheet();}break;}
    case'expRename':{const value=await inputPrompt('Đặt tên góc của bạn',room().life.shop_name||meta().place,36);if(value!==null)await cmd('life_rename',{name:value});break;}
    case'expPrice':await cmd('life_price',{item:data.item,price:Number(document.getElementById('price-'+data.item).value)});break;
    case'expReplyEdit':{const co=room().feed.find(p=>p.id===data.post)?.comments[Number(data.index)];if(!co)break;const text=await inputPrompt('Sửa phản hồi của mình',co.text,500);if(text!==null)await cmd('life_reply_edit',{post:data.post,index:Number(data.index),text});break;}
    case'expCard':ui.activityCard=data.card;renderSheet();break;
    case'expTarget':if(!ui.activityCard){toast('Chọn một thẻ trước nhé.');break;}await cmd('life_activity_assign',{card:ui.activityCard,target:data.target});ui.activityCard=null;renderSheet();break;
    case'lessonStep':if(!ui.lessonSequence.includes(data.step))ui.lessonSequence.push(data.step);renderSheet();break;
    case'lessonReset':ui.lessonSequence=[];renderSheet();break;
    case'lessonPlan':await cmd('lesson_plan',{task:activeTask().id,steps:ui.lessonSequence});break;
    case'tourRoute':ui.tourRoute=ui.tourRoute.includes(data.place)?ui.tourRoute.filter(p=>p!==data.place):[...ui.tourRoute,data.place];renderSheet();break;
    case'tourReset':ui.tourRoute=[];renderSheet();break;
    case'tourPlan':await cmd('tour_plan',{task:activeTask().id,route:ui.tourRoute});break;
    case'teaConfig':await cmd('tea_config',{task:activeTask().id,size:$('#tea-size').value,sugar:Number($('#tea-sugar').value),ice:$('#tea-ice').value});break;
    case'expVisit':ui.townPlace=data.place;await cmd('life_town',{place:data.place});renderSheet();break;
    case'home':openSheet('home');break;
    case'future':openSheet('future');break;
    case'choose':await selectCareer(data.career);break;
    case'bossOffer':if(data.career&&api.state.careers[data.career])await selectCareer(data.career);break;
    case'start':await start();break;
    case'pause':setPaused(!ui.paused);break;
    case'resume':setPaused(false);break;
    case'sound':await cmd('settings',{sound:!api.state.settings.sound},{quiet:true});break;
    case'help':case'people':case'phone':case'queue':case'decor':case'settings':case'album':case'summary':case'event':openSheet(action);break;
    case'journal':if(['teacher','tour_guide','milk_tea'].includes(career()))openSheet('passport');else openSheet('journal',{journalTab:'quests'});break;
    case'library':if(['teacher','tour_guide','milk_tea'].includes(career()))openSheet('workshop');else openSheet('journal',{journalTab:'library'});break;
    case'journalTab':ui.journalTab=data.tab;renderSheet(false);break;
    case'warehouse':openSheet(career()==='milk_tea'?'prepare':['mother_baby','pharmacy'].includes(career())?'warehouse':room().inventory?'inventory':'queue');break;
    case'job':await openJob(data.task);break;
    case'nextJob':ui.task=null;await openJob(null,'shelf');break;
    case'shelf':await openJob(null,'shelf');break;
    case'workbench':await openJob(null,career()==='mother_baby'?'pack':'shelf');break;
    case'counter':await openJob(null,career()==='mother_baby'?'checkout':'shelf');break;
    case'evidence':await openJob(null,'shelf');break;
    case'jobTab':ui.jobTab=data.tab;renderSheet(false);break;
    case'chat':openSheet('chat',{npc:data.npc||activeTask()?.npc,task:data.task||null});break;
    case'quickChat':await talk(data.text);break;
    case'clearChat':if(await confirmAction('Xóa các tin nhắn này?','Ký ức về việc đã làm vẫn giữ trong Sổ tay. Chỉ xóa phần hội thoại tự do.','Xóa lịch sử'))await cmd('chat_clear',{npc:ui.npc});break;
    case'paper':draft(activeTask()).paper=data.value;renderSheet(false);break;
    case'ribbon':draft(activeTask()).ribbon=data.value;renderSheet(false);break;
    case'pack':{const t=activeTask(),d=draft(t);const r=await cmd('shop_pack',{task:t.id,paper:d.paper,ribbon:d.ribbon,card:d.card});if(r)world.say('Một món quà được gói bằng cả sự chăm chút.');break;}
    case'deliverMB':{const t=activeTask();if(!t.checked){toast('Kiểm đơn trước khi xác nhận thanh toán nhé.',true);break;}const total=Object.entries(t.basket).reduce((s,[id,q])=>s+(room().life.prices[id]||product(id).price)*q,0);if(await confirmAction('Trao món quà cho khách?',`Thu ${total} xu tiền hàng${t.pack?', trừ 5 xu vật liệu gói':''} và xuất đúng số hàng đang giữ.`, 'Thanh toán & giao'))await cmd('shop_deliver',{task:t.id});break;}
    case'verifyPH':{const t=activeTask(),selected=draft(t).checks;await cmd('ph_check',{task:t.id,checks:['code','quantity','lot'].filter(k=>selected.includes(k))});break;}
    case'deliverPH':{const t=activeTask();if(await confirmAction('Bàn giao phiếu?','Phiếu sẽ được kiểm lại đúng mã, số lượng và lô. Hoàn tất nhận 40 xu thù lao.'))await cmd('ph_deliver',{task:t.id});break;}
    case'referPH':{const t=activeTask();if(await confirmAction('Chuyển cô Thu kiểm tiếp?','Hàng đang giữ được trả về kệ. Người phụ trách nhận việc; bạn nhận 25 xu thù lao chuyển đúng phạm vi.','Chuyển phiếu'))await cmd('ph_refer',{task:t.id});break;}
    case'selectDoc':ui.docs.has(data.id)?ui.docs.delete(data.id):ui.docs.add(data.id);renderSheet();break;
    case'selectTx':ui.transactions.has(data.id)?ui.transactions.delete(data.id):ui.transactions.add(data.id);renderSheet();break;
    case'clearSelection':ui.docs.clear();ui.transactions.clear();renderSheet();break;
    case'match':{const r=await cmd('ac_match',{task:activeTask().id,docs:[...ui.docs],transactions:[...ui.transactions]});if(r){ui.docs.clear();ui.transactions.clear();renderSheet();}break;}
    case'completeAC':if(await confirmAction('Bàn giao bản đối chiếu?','Bản bàn giao giữ các nhóm, nguồn và lý do điều chỉnh. Mọi thẻ phải được xử lý trước khi nhận thù lao.','Kiểm & bàn giao'))await cmd('ac_complete',{task:activeTask().id,explanation:'source_report'});break;
    case'executeCS':if(await confirmAction('Gửi việc tới đầu mối?','Đây là lệnh thực hiện, chưa phải kết quả. Sau hai nhịp hãy quay lại kiểm xác nhận.','Gửi việc'))await cmd('cs_execute',{task:activeTask().id});break;
    case'closeCS':if(await confirmAction('Đóng vụ đã có kết quả?','Hệ thống chỉ cho đóng nếu kết quả đã được xác minh. Khách sẽ để lại review theo vụ thực tế.','Đóng vụ'))await cmd('cs_close',{task:activeTask().id});break;
    case'end':if(!room().open){openSheet('summary');break;}if(await confirmAction('Khép ca hôm nay?','Việc còn dở được giữ cho ngày mai. Lương, điện nước và tiền thuê ghi vào sổ tiệm để bạn trả sau.','Khép ca')){const r=await cmd('end_day',{carry_event:true});if(r){ui.task=null;openSheet('summary');world.say('Hẹn gặp lại vào một ngày dịu dàng.');}}break;
    case'buyUpgrade':{const u=api.content.upgrades.find(x=>x.id===data.item);if(await confirmAction('Đặt '+u.name.toLowerCase()+'?',`Dùng ${u.price} xu của nghề này. ${u.description}`,'Mua & đặt'))await cmd('buy_upgrade',{item:data.item});break;}
    case'restock':{const quantity=Number(document.getElementById('qty-'+data.item)?.value);if(!Number.isInteger(quantity)||quantity<1||quantity>6){toast('Mỗi lần đặt từ 1 đến 6 món.',true);break;}const p=product(data.item);if(await confirmAction('Đặt một kiện hàng?',`${quantity} × ${p.name}, tổng ${quantity*p.cost} xu. Chỉ cộng kho sau khi kiện tới và bạn kiểm nhận.`, 'Đặt hàng'))await cmd('order_stock',{item:data.item,qty:quantity});break;}
    case'confirmEvent':{const e=room().event,o=e.options.find(o=>o.id===e.chosen);if(await confirmAction('Xác nhận cách xử lý?',`${o.label}. ${e.practice?'Diễn tập không trừ xu.':o.cost?'Chi '+o.cost+' xu từ quỹ nghề.':'Không tốn xu.'} Sau đó thực hiện các bước.`, 'Bắt đầu thực hiện'))await cmd('event_confirm');break;}
    case'eventStep':{const r=await cmd('event_step');if(r){world.say(r.message);world.go(room().event.station,()=>{});}break;}
    case'practice':{const e=room().event;if(e&&e.stage!=='resolved'){if(e.practice){if(!(await confirmAction('Chuyển tình huống diễn tập?','Diễn tập hiện tại được cất lại, không thay đổi tiền hoặc quan hệ.','Chuyển tình huống')))break;await cmd('event_dismiss',{}, {quiet:true});}else{toast('Bạn đang có một chuyện thật trong ca. Hoàn thành trước rồi mở diễn tập nhé.',true);openSheet('event');break;}}const r=await cmd('event_start',{event:data.event});if(r)openSheet('event');break;}
    case'reviewFollowup':{if(['teacher','tour_guide','milk_tea'].includes(career())){openSheet('passport');break;}const r=await cmd('review_followup',{post:data.post});if(r)openSheet('event');break;}
    case'photo':{closeSheet();await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));const image=world.snapshot();const r=await cmd('photo',{image,title:meta().place+' · Ngày '+room().day});if(r)openSheet('album');break;}
    case'downloadPhoto':{const p=room().album.find(x=>x.id===data.id);if(p){const a=document.createElement('a');a.href=p.image;a.download=`goc-pho-ngay-${p.day}.webp`;a.click();}break;}
    case'saveAI':await cmd('settings',{aiConsent:$('#ai-consent').checked});break;
    case'export':try{const data=await api.exportSave();download(JSON.stringify(data,null,2),'mot-ngay-lam-nghe-save.json');toast('Đã xuất bản lưu riêng của bạn.');}catch(e){toast(e.message,true);}break;
    case'import':$('#import-file').click();break;
    case'resetCareer':if(await confirmAction('Xóa tiến trình riêng nghề này?','Tiền, đồ, công việc, hội thoại và album của nghề đang chọn sẽ được đặt lại. Các nghề khác giữ nguyên. Nên xuất bản lưu trước.','Xóa & bắt đầu lại')){const r=await cmd('reset_career',{confirm:'BAT DAU LAI'});if(r){ui.task=null;closeSheet();await start();}}break;
    default:{
      if(await deskAction(action,data,el,env()))break;
      if(await journeyAction(action,data,el,env()))break;
      if(await incidentAction(action,data,el,env()))break;
      if(await v4Action(action,data,el,env()))break;
      if(action.startsWith('car:')){const mod=careerUI(career()),fn=mod?.actions?.[action.slice(4)];if(fn){await fn(data,el,careerContext(env()));break;}}
      if(await settingsAction(action,data,el,env()))break;
      if(await socialAction(action,data,el,env()))break;
      if(procedureAction(action,data,el,env()))break;
      if(action==='classroom'){openSheet('classroom');break;}
      if(await shell.action(action,data,el,env()))break;
      toast('Chưa có tương tác này.',true);
    }
  }
}
document.addEventListener('click',async e=>{
  const el=e.target.closest('[data-action],[data-command]');if(!el||el.disabled)return;sound.unlock();sound.configure(api.state?.settings||{sound:true,music:false});
  // Ignore additional input while a mutation is on the wire; retries carry an idempotency key.
  if(ui.busy&&!['close','confirmNo','confirmYes'].includes(el.dataset.action))return;
  if(el.dataset.command){const action=el.dataset.command,payload=JSON.parse(el.dataset.payload||'{}');const result=await cmd(action,payload);if(result){if(action==='defer'){ui.task=null;openSheet('queue');}if(action==='event_dismiss'){openSheet('journal',{journalTab:'library'});}if(action==='more_work'){ui.task=null;await openJob(null,'shelf');}if(action==='ask'){world.say(result.message,activeTask()?.npc);}}}
  else{try{await handleAction(el.dataset.action,el.dataset,el);}catch(error){console.error(error);toast('Thao tác chưa hoàn tất. '+error.message,true);}}
});
document.addEventListener('dragstart',e=>{const el=e.target.closest('[data-drag-card]');if(el){ui.activityCard=el.dataset.dragCard;e.dataTransfer.setData('text/plain',ui.activityCard);}});
document.addEventListener('dragover',e=>{if(e.target.closest('[data-drop-target]'))e.preventDefault();});
document.addEventListener('drop',async e=>{const el=e.target.closest('[data-drop-target]');if(!el||ui.busy)return;e.preventDefault();const card=e.dataTransfer.getData('text/plain');if(!card)return;await cmd('life_activity_assign',{card,target:el.dataset.dropTarget});ui.activityCard=null;renderSheet();});
document.addEventListener('submit',async e=>{
  const f=e.target;if(!(f instanceof HTMLFormElement))return;e.preventDefault();sound.unlock();if(ui.busy)return;
  if(await careerSubmit(f,env()))return;
  if(await journeySubmit(f,env()))return;
  if(await v4Submit(f,env()))return;
  if(await accountSubmit(f,env()))return;
  if(await socialSubmit(f,env()))return;
  if(await procedureSubmit(f,env()))return;
  if(await shell.submit(f,env()))return;
  if(f.id==='staffTalkForm'){const input=$('#staff-message'),text=input.value.trim();if(!text)return;input.value='';await cmd('ops_staff_talk',{employee:f.dataset.employee,text},{quiet:true});}
  else if(f.id==='chatForm'){const input=$('#chat-input'),text=input.value.trim();if(!text)return;input.value='';await talk(text);}
  else if(f.id==='postForm'){const input=$('#post-text'),text=input.value.trim();if(!text)return;input.value='';await cmd('feed_post',{text});}
  else if(f.dataset.replyPost){const input=f.querySelector('input'),text=input.value.trim();if(!text)return;input.value='';await cmd('feed_reply',{post:f.dataset.replyPost,text});}
  else if(f.dataset.receive){const count=Number(f.querySelector('input').value);await cmd('receive_stock',{shipment:f.dataset.receive,count});}
  else if(f.id==='settingsForm'){await cmd('settings',{name:$('#player-name').value});}
});
document.addEventListener('input',e=>{
  if(careerInput(e.target,env(),'input'))return;
  if(v4Input(e.target,env()))return;
  if(settingsInput(e.target))return;
  if(e.target.dataset.draft&&activeTask())draft(activeTask())[e.target.dataset.draft]=e.target.value;
  if(e.target.id==='library-search'){ui.libraryQuery=e.target.value;renderSheet();}
});
document.addEventListener('change',async e=>{
  const el=e.target;
  if(careerInput(el,env(),'change'))return;
  if(await settingsChange(el,env()))return;
  if(el.dataset.staffRole)await cmd('ops_assign',{employee:el.dataset.staffRole,role:el.value});
  if(el.dataset.staffSchedule)await cmd('ops_schedule',{employee:el.dataset.staffSchedule,schedule:el.value});
  if(el.dataset.phcheck){const checks=draft(activeTask()).checks;draft(activeTask()).checks=el.checked?[...new Set([...checks,el.dataset.phcheck])]:checks.filter(k=>k!==el.dataset.phcheck);}
  if(el.dataset.actionChange==='ph-filter'){ui.phFilter=el.value;renderSheet(false);}
  if(el.dataset.decorItem)await cmd('decor_move',{item:el.dataset.decorItem,spot:el.value});
  if(el.id==='import-file'&&el.files[0]){const file=el.files[0];try{if(file.size>14500000)throw new Error('Bản lưu quá lớn.');const save=JSON.parse(await file.text());if(await confirmAction('Khôi phục bản lưu này?','Các nghề của phiên hiện tại sẽ được thay thế bằng dữ liệu trong tệp. Hãy xuất bản hiện tại trước nếu cần.','Khôi phục')){const r=await cmd('import_save',{save});if(r){ui.task=null;ui.docs.clear();ui.transactions.clear();closeSheet();if(!api.state.current)openSheet('home');}}}catch(error){toast('Không nhập được: '+error.message,true);}}
});
window.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('#sheet').open&&!$('#confirmDialog').open&&api.state?.current){setPaused(!ui.paused);}});
window.addEventListener('focus',()=>{if(api.state&&!ui.busy)api.refresh().catch(()=>{});});
let responsiveTimer;
window.addEventListener('resize',()=>{clearTimeout(responsiveTimer);responsiveTimer=setTimeout(()=>{if(api.state&&api.content)renderMain();},140);});
window.addEventListener('layoutchange',()=>{world.resize();if(api.state&&api.content)renderMain();});
api.addEventListener('state',()=>{renderMain();if(ui.view)renderSheet();shell.update(env());});
api.addEventListener('busy',e=>{ui.busy=e.detail;document.body.classList.toggle('busy',ui.busy);$('#saveState')?.setAttribute('aria-busy',String(ui.busy));});
api.addEventListener('offline',()=>renderMain());
window.addEventListener('online',()=>{if(api.state)api.refresh().then(()=>renderMain()).catch(()=>{});});
window.addEventListener('error',e=>{console.error('Game UI:',e.error||e.message);});
try{
  await api.init();await loadCareerModules([...Object.keys(api.content.careers||{}),'milk_tea','mother_baby']);await setLanguage(api.state.settings.lang);shell.boot(env());journeyBoot(env());incidentBoot(env());happenBoot(env());startTicker(()=>env());$('#loading').hidden=true;$('#app').hidden=false;world.resize();renderMain();
  registerWorker();startSocialPoll(env());
  const openSocial=tab=>{ui.socTab=tab||'street';ui.socShop=null;socialInvalidate(ui);openSheet('social');};
  listenWorker(url=>{const q=new URL(url,location.origin).searchParams;if(q.get('social'))openSocial(q.get('social'));});
  const deep=new URLSearchParams(location.search);
  if(deep.get('social')){history.replaceState(null,'','/');openSocial(deep.get('social'));}
  else if(!api.state.current)openSheet('home');else{world.say('Chào bạn trở lại. Mọi việc đã xác nhận vẫn ở đây.');if(!room().open)openSheet(room().shift_summary?'summary':'prepare');}
}catch(error){$('#loading').innerHTML=`<div class="loading-leaf">${icon('leaf',45)}</div><h1>Khu phố đang đợi mở cửa</h1><p>Chưa kết nối được. Kiểm tra mạng rồi thử lại nhé.</p><button class="btn primary big" id="reload-btn">Thử kết nối lại</button>`;console.warn(error);$('#reload-btn').onclick=()=>location.reload();}
