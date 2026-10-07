/** Front-end orchestration. Economic rules live on the Python server, not in chat. */
import {GameAPI} from './api.js';
import {sellerVisitStrip,customerTaskBanner,visitCustomer,customerPortrait} from './v4/workplace-visit-ui.js';
import {equipmentView,staffRefresh,staffRefreshPaused,scrollGuard} from './v4/work-equipment.js';
import {suppressMediaGesture} from './v4/media-gestures.js';
for(const event of ['contextmenu','dragstart','dblclick'])document.addEventListener(event,suppressMediaGesture);
import {BobaWorld} from './boba-world.js';
import {wordsFor,kindOf} from './scenes/index.js';
import {termsSource,T} from './v4/terms.js';
// Scene kinds load on demand: the current career's before the first frame, another career's before switching
// to it (careerAssets below), so no career flashes the storefront and startup isn't waiting on all of them.
import {nextStep,lifeNav,guestRibbon,experienceView,extendedJob,experienceSummary,teachTour} from './experience-ui.js';
import {icon,portrait,itemArt,escapeHTML as esc} from './icons.js';
import {fillToast,toastHead} from './toast-lines.js';
import {reqList,fold,clean as uiClean,few,actBar,tip as uiTip,helpBtn,withWhy,headChip} from './ui-kit.js';
import {olderRows,olderButton,loadOlder,syncOlder} from './archive.js';
import {Sound} from './audio.js';
import {soundsBoot} from './v4/sounds.js';
import {dayclockBoot,clockChip,clockAria,clockCard,clockSummary,closingNote,clockStep} from './v4/dayclock.js';  // giờ trong ngày
import {careerSubmit,careerInput,loadCareerModules,careerUI,hasCareerUI,setCareerData,careerContext,startTicker,tickNow,careerSwitchButton,CSS_KIT} from './v4/careers.js';
import {applyGuide,guideAction,nextHint,stepCta,plainText,firstTime,barParts} from './v4/guide.js';
import {inventoryView,feedbackView,situationView,jobView as jobAppView,v4Action,v4Submit,v4Input} from './v4/views.js';
import {moneyBoot,confirmMoney,confirmShort,dialogBalances,isSpend,priceIn} from './v4/money.js';  // 💰 Ví / Quỹ tiệm in sight while spending
import {quickOpen,firstDay} from './v4/onboard.js';  // a brand-new player's first minutes
import {hudMoney,hudChipsHTML,wealthHTML,loadJoint,jointBalance,wealthAction} from './v4/wealth.js';  // 💰 Tiền của bạn (top bar chips + sheet)
import {emojiOf,townOn} from './v4/journey.js';
import {lowItems,crates} from './v4/restock.js';  // the bar's Kho badge
import {setLanguage,t as i18nT} from './v4/i18n.js';
import {shell} from './v4/shell.js';
import {accountSubmit,accountNudge,accountAction,accountBoot} from './v4/account.js';
import {registerWorker,listenWorker} from './v4/push.js';
import {homeView as homeV4,futureView as futureV4,journeyBoot,journeyAction,journeySubmit} from './v4/home.js';
import {procedureSubmit,procedureAction} from './v4/procedure.js';
import {abandonGate,abandonAfter,abandonSummary} from './v4/abandon.js';
import {lifeSummary} from './v4/life.js';
import {lunchStrip,snackStrip,snackDue,eveningBody,needsAction} from './v4/needs.js';  // 🍚 No bụng · 😴 Tỉnh táo: lunch, the evening
import {boardView,boardAction,boardSubmit,boardBoot,boardUnread} from './v4/board.js';
import {lazy,skeleton,idle as whenIdle,prefetch} from './lazy.js';
/* Features that load on first use (lazy.js), not with the page: a sheet's code comes when it first opens
 * (a skeleton shows meanwhile), and the small always-on parts (badges, notices, polls) in idle time once the
 * game is on screen. A module that arrives re-renders the screen through the 'mnl:lazy' event (below). */
const L={
  pnl:lazy(()=>import('./v4/pnl.js'),{css:['/css/pnl.css']}),  // Kết quả kinh doanh (end of day)
  ops:lazy(()=>import('./operations-ui.js')),  // Sổ tiệm
  tips:lazy(()=>import('./v4/tips.js')),  // tip hên xui
  settings:lazy(()=>import('./v4/settings.js')),  // Cài đặt (+ the Xếp hạng privacy row)
  social:lazy(()=>import('./v4/social.js')),  // Phố nghề
  classroom:lazy(()=>import('./v4/classroom.js')),  // Lớp học
  accountingSchool:lazy(()=>import('./v4/accounting-school.js'),{css:['/css/accounting-school.css']}),
  desk:lazy(()=>import('./desk.js')),  // office dossiers
  inc:lazy(()=>import('./v4/incidents.js')),  // Chuyện đời
  chat:lazy(()=>import('./v4/ai-chat.js')),  // AI characters
  happen:lazy(()=>import('./v4/happenings.js')),  // happenings in the scene
  fb:lazy(()=>import('./v4/feedback.js'),{css:['/css/feedback.css','/css/admin-stats.css']}),  // Góp ý (+ admin stats)
  rank:lazy(()=>import('./v4/leaderboard.js')),  // Xếp hạng
  people:lazy(()=>import('./v4/closeness.js')),  // 👥 Người quen: điểm thân quen
  tut:lazy(()=>import('./tutorial/index.js')),  // first-run tour, guide, announcements
  live:lazy(()=>import('./v4/live.js')),  // 💬 Chat: the live socket, the chat button + badge (the dialog is v4/chat.js)
  tm:lazy(()=>import('./careers/tomorrow_kit.js'),{css:['/css/careers/tomorrow_kit.css']}),  // 🌅 Ngày mai in the pharmacy's day summary
  promo:lazy(()=>import('./v4/promo.js'),{css:['/css/promo.css']}),  // 🎖️ Thăng tiến, 🧑‍💼 Ca quản lý (game/promotion.py)
};
const TUT_OPEN=new Set(['help','tutGuide','tutReplay']);  // tutorial actions whose buttons other modules render
const PROMO_OPEN=new Set(['promo','pmBoard','pmStart','pmPick','pmMate','pmOffice']);  // 🎖️ v4/promo.js
/** A sheet whose code is not in yet: its header (with the close button) and a skeleton. */
const lazyView=(h,fn)=>h.use()?fn(h.m):header('')+`<div class="sheet-body">${skeleton()}</div>`;
/** A sheet that reads the catalogue's `more` part (api.more(): job postings, the shop book, situations, story texts):
 * a skeleton until it is in (it loads right after the first frame; the 'mnl:lazy' event re-renders). */
const moreView=fn=>{if(api.hasMore())return fn();api.more().catch(e=>console.warn('content:',e));return header('')+`<div class="sheet-body">${skeleton()}</div>`;};
/** The module behind an action that opens it; the tapped control shows as pending while the code loads. */
async function viaLazy(h,el){if(h.m)return h.m;el?.classList?.add('is-pending');try{return await h.get();}finally{el?.classList?.remove('is-pending');}}

const $=s=>document.querySelector(s), api=new GameAPI(), sound=new Sound();
const ended=t=>['completed','referred','cancelled'].includes(t.status);
/** The stock room opened from the scene or the dock: no restock filter left over (views.js v4Restock). */
const INV_PLAIN={invFocus:null,invNeed:null,invReturn:null,orderRush:false};
/** First day at a place, its three jobs done: closing the day is the next step (and the chapter goal). */
const wrapUp=c=>Boolean(c?.open&&c.day===1&&c.day_completed>=3&&!c.tasks.some(x=>!ended(x)));
/** Why "Đón thêm khách" would be refused now (game/engine.py more_gate; null: a customer comes in): closing time,
 * today's customers all dealt, or 4 already in hand. The dock and the work sheets then offer the real next step. */
const moreGate=c=>c?.open&&c.more_gate||null;
/** The next customer, or when none can come in: the work in hand, else closing the day. */
function moreWay(c,label,style='primary'){
  const g=moreGate(c);if(!g)return commandButton(label,'more_work',{},style);
  const left=c.tasks.filter(x=>!ended(x)).length;
  if(left)return button(`${g.why==='full'?'Làm tiếp việc đang chờ':'Làm nốt việc dở'} · ${left} `+icon('arrow',14),'nextJob',{},style);
  return button(icon('exit',16)+' Khép ca · xem tổng kết','end',{},style+' gd-pulse');
}
/** Shift closed: every control whose command needs it open (game/engine.py "Mở ca trước khi xử lý công việc nhé")
 * is drawn disabled, and the work sheet's "Mở ca" bar is the one way on (it opens the shift in place). */
const SHUT_WORK=/^(shop_|ac_|cs_|ph_|cl_|desk_|more_work$)/;
function shutWork(html){
  const c=room();if(!c||c.open||!api.state?.current)return html;
  const g=meta().shift_gate,needs=op=>SHUT_WORK.test(op)||Boolean(g&&op.startsWith(g.prefix)&&!g.free.includes(op));
  return html.replace(/<button\b([^>]*?)\sdata-(command|op)="([^"]*)"([^>]*)>/g,(m,a,k,op,b)=>needs(op)&&!/\sdisabled\b/.test(a+b)?`<button${a} data-${k}="${op}"${b} disabled>`:m);
}
/** Work sheets pay from the workplace fund (game/engine.py money: "Chưa đủ xu…"). A command button that spends a
 * named price (its label starts with a spending word, or it carries data-cost) the fund cannot cover is drawn
 * disabled with "thiếu N xu", like the 0.9.16 bakery's "thiếu 1 bơ lạt". */
const FUND_VIEWS=new Set(['job','inventory','warehouse','prepare','prices','workshop','decor','operations','queue','situation','event']);
function shortWork(html){
  const c=room();if(!c||!FUND_VIEWS.has(ui.view)||!api.state?.current)return html;
  return html.replace(/<button\b([^>]*\sdata-(?:command|op)="[^"]*"[^>]*)>([\s\S]*?)<\/button>/g,(m,a,label)=>{
    if(/\sdisabled\b/.test(a)||/\sdata-pocket="(?!fund)/.test(a))return m;
    const text=label.replace(/<[^>]*>/g,' ').replace(/&[a-z#0-9]+;/gi,' ').replace(/\s+/g,' ').trim(),told=Number((a.match(/\sdata-cost="(\d+)"/)||[])[1]);
    const cost=told||(isSpend(text)&&!/khoảng/.test(text)?priceIn(text):null);
    return cost>c.money?`<button${a} disabled>${label}<small class="mn-miss"> · thiếu ${fmt(cost-c.money)} xu</small></button>`:m;
  });
}
const closedBar=()=>notice(`<b>Ca đang nghỉ</b> · mở ca để làm tiếp. ${button(icon('sun',14)+' Mở ca','startHere',{},'primary small')}`,'amber','sun');
const ui={opsTab:'staff',staffId:null,lessonSequence:[],tourRoute:[],activityCard:null,view:null,tab:'',task:null,npc:null,jobTab:'shelf',journalTab:'quests',libraryQuery:'',docs:new Set(),transactions:new Set(),drafts:{},ai:{},suggestions:{},busy:false,paused:false};
const world=new BobaWorld($('#world'),interact);
soundsBoot({api,world,sound});  // character voices, detail sounds, bank speaker
api.addEventListener('result',e=>{if(e.detail?.result?.card_swipe)import('./v4/bank.js').then(m=>m.swipeSound(api)).catch(()=>{});});  // 🏦 quẹt thẻ: ting ting
dayclockBoot();  // giờ trong ngày: HUD clock, closing prompt, the scene's light
/* 💰 Where the money chip shows and which pockets (v4/money.js): work sheets spend the workplace's fund
 * (and may touch the wallet), the job board ("Đi cửa sau"), the journey pages, the bank and marriage spend
 * the wallet. Everything else (reviews, chat, settings…) shows no chip. */
const MONEY_FUND=new Set(['job','inventory','warehouse','prepare','prices','decor','workshop','town','operations','social','people','incident','event','situation','classroom','feedback']);  // feedback: a reply may offer the customer something back
function moneyScope(d){
  if(!d?.open||!api.state)return null;
  if(d.id==='sheet'){const v=ui.view,cid=api.state.current;
    if(MONEY_FUND.has(v)&&cid&&api.state.careers[cid])return {fund:cid};
    return v==='jobapp'||v==='home'?{fund:null}:null;}
  // The bank and 🏠 Nhà của bạn (a .bk-sheet too): wallet + bank account, and the couple's Quỹ chung when the
  // house sheet has loaded one (data-joint, v4/house.js): a house is paid from all three.
  if(d.matches('.bk-sheet'))return {fund:null,account:true,...(d.dataset.joint!=null&&d.dataset.joint!==''?{joint:Number(d.dataset.joint)}:{})};
  return d.matches('.mr-sheet')?{fund:null}:null;
}
termsSource(()=>api.content?.catalogue);  // each career's words for the shared screens (v4/terms.js)
moneyBoot({api,scope:moneyScope,till:cid=>wordsFor(cid).till,phone:()=>document.documentElement.dataset.layout==='phone'});
// Before a workplace is chosen the server picks one that is open (state.focus) and sends its full view.
const career=()=>api.state?.current||api.state?.focus||'mother_baby';
const room=()=>api.state?.careers[career()];
const meta=()=>api.content?.catalogue.find(c=>c.id===career())||{};
/** Careers whose review follow-up is their own passport sheet, not the server's review_followup event. */
const REVIEW_PASSPORT=['teacher','tour_guide','milk_tea'];
const npc=id=>api.content?.npcs.find(n=>n.id===id)||{display_name:api.state?.name||'Bạn',role:'Bạn',personality:''};
const product=id=>api.content.products.find(p=>p.id===id)||api.content.lots.find(p=>p.id===id)||{name:id,price:0,icon:'box',color:'cream'};
const activeTask=()=>room()?.tasks.find(t=>t.id===(ui.task||room().active_task))||room()?.tasks.find(t=>!ended(t));
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const LEGACY=['mother_baby','pharmacy','accounting','customer_care','teacher','tour_guide','milk_tea'];
const plugin=()=>!LEGACY.includes(career());
const env=()=>({api,ui,cmd,confirmAction,toast,renderSheet,renderMain,openSheet,closeSheet,world,act:(action,data={})=>handleAction(action,data,null),live:()=>L.live.m?.live||null});  // live: 🗺️ the town's Đi dạo sign (v4/town-walk.js)
/** The one day counter the player sees: the life day in the story, the workplace's own day elsewhere (game/days.py). */
const dayNo=c=>api.state?.journey?.story&&Number.isInteger(api.state.journey.life_day)?api.state.journey.life_day:c?.day;
const needsJob=()=>room()?.job?.required&&room().job.status!=='hired';
const attrs=obj=>Object.entries(obj).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const button=(label,action,data={},style='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}>${label}</button>`;
const commandButton=(label,command,payload={},style='',disabled=false)=>`<button type="button" class="btn ${style}" data-command="${command}" data-payload="${esc(JSON.stringify(payload))}"${disabled?' disabled':''}>${label}</button>`;
const pill=(label,kind='')=>`<span class="tag ${kind}">${label}</span>`;
const empty=(title,text='',ico='leaf')=>`<div class="empty">${icon(ico,32)}<h3>${title}</h3>${text?`<p class="muted small">${text}</p>`:''}</div>`;
/** Office-type careers talk about files and trays, not customers. */
const deskWork=()=>(meta()?.category||{accounting:'office'}[career()])==='office';
const notice=(text,kind='',ico='leaf')=>`<div class="notice ${kind}">${icon(ico,17)}<div>${text}</div></div>`;
/** kind: true/'error' (red, longer), 'good' (success after a celebrated action), 'hint' (short helper line
 * with a 💡, auto-dismiss) or plain. Same text is never stacked twice. Career desks reach it as env.toast(text,'hint'). */
/* Long enough to read (owner: toasts were too quick): a floor per kind plus reading time
 * (~15 characters a second), capped. Toasts never take taps (.toasts is pointer-events:none). */
const toastLife=(message,cls)=>Math.min(8000,Math.max(cls==='error'?4500:cls==='hint'?3000:3200,1200+String(message).length*45));   // owner 03/10: shorter, and a tap closes it
/* A toast says a few words (toast-lines.js toastHead: ≤8, an error its first sentence; owner 03/10 "chữ ít thôi"):
 * a note with more to it shows a small ▾, and a first tap opens the whole text (a second tap closes it).
 * The text is put into English first (when that is on), so the few words are cut from the shown language. */
function toast(message,kind=false){if(!message)return;const box=$('#toasts'),cls=kind===true||kind==='error'?'error':kind==='good'?'good':kind==='hint'?'hint':'';
  const said=String(i18nT(String(message))),{head,more}=toastHead(said,{error:cls==='error'});let life=toastLife(head,cls);
  const mount=$('#confirmDialog').open?$('#confirmDialog'):$('#sheet').open?$('#sheet'):document.body;mount.append(box);
  if(mount.id==='sheet')requestAnimationFrame(headMeasure);   // the header may have moved (a centred sheet changing height)
  const leave=el=>{clearTimeout(el._t);el._t=setTimeout(()=>{el.classList.add('leaving');setTimeout(()=>el.remove(),320);},life);};
  const same=[...box.children].find(x=>x.dataset.msg===message&&!x.classList.contains('leaving'));
  if(same){same.classList.remove('bump');void same.offsetWidth;same.classList.add('bump');leave(same);return;}
  if(cls==='hint'&&box.querySelector('.toast.error:not(.leaving)'))return;
  const el=document.createElement('div');el.className=`toast ${cls}`.trim();el.dataset.msg=message;
  const fill=text=>{fillToast(el,text);if(cls==='hint'){const face=document.createElement('span');face.className='hint-face';face.setAttribute('aria-hidden','true');face.textContent='💡';el.prepend(face);}};
  fill(head);
  if(more){el.classList.add('has-more');el.insertAdjacentHTML('beforeend','<i class="toast-more" aria-hidden="true">▾</i>');}
  el.title=more?said:'Bấm để tắt';
  el.addEventListener('click',()=>{
    if(more&&!el.classList.contains('open')){el.classList.add('open');el.classList.remove('has-more');fill(said);life=toastLife(said,cls);leave(el);return;}
    clearTimeout(el._t);el.classList.add('leaving');setTimeout(()=>el.remove(),320);});   // owner 03/10: tap to close, so it stops covering the screen
  box.append(el);leave(el);
  // Calm screen: one toast at a time, the newest wins.
  while(box.children.length>1)box.firstElementChild.remove();}
function download(data,name,type='application/json'){const blob=new Blob([data],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);}
let pmWant=null;   // 🧑‍💼 "Mở ca quản lý" waiting behind the accountant's entry check: the check's start_day keeps it
async function cmd(action,payload={},options={}){
  if(action==='start_day'&&!payload?.acct_check&&acctDue(options.career||career())){pmWant=payload?.manager?options.career||career():null;acctCheck(options.career||career());return null;}
  const pm=action==='start_day'&&payload?.acct_check&&pmWant===(options.career||career());
  if(pm)payload={...payload,manager:true};
  try{const r=await api.command(action,payload,options.career||career());if(pm){pmWant=null;ui.pmPick=null;ui.task=null;setTimeout(()=>openSheet('manager'),0);}if(!options.quiet)toast(r.message,r.correct===false?'error':r.celebrate?'good':false);if(r.celebrate){sound.success();world.celebrate();}else sound.click();for(const note of new Set(r.effects||[]))toast(note);if(r.clock)setTimeout(()=>toast(r.clock.text),1400);if(r.needs_say)setTimeout(()=>world.say(r.needs_say),700);if(r.quay)quayFlush();return r;}
  catch(error){if(error.quiet)return null;
    if(error.data?.code==='acct_check'&&!payload?.acct_check){acctCheck(options.career||career());return null;}   // 💼 kế toán: the entry check first (v4/accounting-school.js)
    // A command aimed at another workplace while work is in progress here (engine: ab.check with no confirm): ask once
    // with the real numbers, switch with the player's confirm, then send the command again. Never a silent loop.
    if(error.data?.code==='abandon_confirm'&&action!=='select_career'&&!options.abandonRetry){const target=options.career||career();const sw=await switchCareer(target);if(!sw)return null;abandonAfter(sw);return cmd(action,payload,{...options,career:target,abandonRetry:true});}
    toast(error.status?error.message:'Mất kết nối. Việc đã xác nhận vẫn được giữ, thử lại sau một chút nhé.',true);sound.error();return null;}  // quiet: a tap the save moved under twice (api.js), the screen already shows why
}
/** 💼 A certified accountant's shift opens with the knowledge check (game/accounting_jobs.py): state.accounting_school.jobs. */
const acctDue=cid=>!!api.state?.accounting_school?.jobs?.places?.[cid]?.[2]&&!api.state.careers?.[cid]?.open;
async function acctCheck(cid){const m=await viaLazy(L.accountingSchool);if(await m.accountingCheckOpen(env(),cid))openSheet('accountingSchool');}
// A page behind the server's release (update.js FIRM) reloads onto it at the next navigation, when nothing is lost.
function closeSheet(){if($('#sheet').open)$('#sheet').close();ui.view=null;ui.ai={};world.paused=ui.paused;api.updates.navigated();}
function openSheet(view,data={}){if(api.updates.navigated())return;$('#sheet').resetGesture?.();if(view!=='job'&&view!=='chat'){ui.task=null;}Object.assign(ui,data);ui.view=view;renderSheet(false);if(!$('#sheet').open){const d=$('#sheet');d.showModal();d.scrollTop=0;d.tabIndex=-1;d.focus({preventScroll:true});}}
/** "?" of a work screen before the tutorial module has loaded (same markup as tutorial/guide.js helpButton;
 * a tap loads it: TUT_OPEN). Every career's work screen carries it, in the header, next to "Đóng". */
const helpQ=cid=>`<button type="button" class="icon-btn tut-help" data-action="tutGuide" data-career="${esc(cid||'')}" data-tab="work" aria-label="Hướng dẫn nghề này">?</button>`;
function header(title,subtitle='',eyebrow='MỘT NGÀY LÀM NGHỀ',extra=''){const kit=[].concat(CSS_KIT[career()]||[]),short=ui.view==='job'&&uiClean()&&(kit.includes('street_kit')||kit.includes('office_kit')||['tra_da','pet_shop','customer_care','accounting','pharmacy','milk_tea','cafe_bakery','restaurant','florist','mother_baby','clothing','grocery','pet_care'].includes(career()))?esc(few(plainText(title),4)):'';return `<header class="sheet-head"><div class="grow"><span class="eyebrow">${eyebrow}</span><h2 title="${esc(plainText(title))}"${short?` aria-label="${esc(plainText(title))}"`:''}>${short||title}</h2>${subtitle?`<p>${subtitle}</p>`:''}</div>${extra}${ui.view==='job'?(L.tut.m?.guideHelp(career())||helpQ(career())):''}<button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;}
function footer(left='',right=''){return `<footer class="sheet-foot"><p>${left}</p><div class="row wrap">${right}</div></footer>`;}
/** ⋯ in a work sheet's header: the rarely used ways out ("Để lát nữa", "Xem các việc khác") that used to take a
 * whole footer row under the career's action bar. data-auto: every re-render shuts it again. */
function headMenu(items){return `<details class="head-more" data-auto><summary class="icon-btn" aria-label="Thêm lựa chọn" title="Thêm lựa chọn"><span aria-hidden="true">⋯</span></summary><div class="head-menu">${items}</div></details>`;}
document.addEventListener('click',e=>{for(const d of document.querySelectorAll('details.head-more[open]'))if(!d.contains(e.target)||e.target.closest?.('.head-menu [data-action],.head-menu [data-command]'))d.open=false;},true);
function setPaused(value){ui.paused=value;world.paused=value;$('#pauseOverlay').hidden=!value;renderMain();if(value)sound.stopMusic();else sound.configure(api.state.settings);}
function draft(t){return ui.drafts[t.id]??={paper:t.pack?.paper||'cream',ribbon:t.pack?.ribbon||'gold',card:t.pack?.card||'Gửi bạn một ngày dịu dàng.',checks:[]};}
function taskNext(t){if(!t)return'Chọn một việc nhỏ để bắt đầu';if(!room().open)return'Mở ngày để tiếp tục';if(t.desk)return L.desk.use()?.deskNext(t,api)||'…';if(careerUI(t.career))return careerUI(t.career).next(t,careerContext(env()));if(['teacher','tour_guide','milk_tea'].includes(t.career))return nextStep(t);if(!t.known&&['mother_baby','pharmacy'].includes(career()))return'Hỏi nhu cầu / đọc mục tiêu';if(career()==='mother_baby'){if(!Object.keys(t.basket).length)return'Lấy hàng trên kệ';if(t.needs.gift&&!t.pack)return'Tới bàn gói quà';if(!t.checked)return'Kiểm giỏ trước khi giao';return'Thanh toán & bàn giao';}if(career()==='pharmacy'){if(t.needs.referral)return'Chuyển cô Thu';if(!Object.keys(t.basket).length)return'Đọc nhãn và lấy đúng mã';return t.checked?'Bàn giao phiếu':'Kiểm mã · lượng · lô';}if(career()==='accounting')return !t.inspected.length?'Mở bản gốc để kiểm':'Ghép chứng từ & giao dịch';return !t.identity?'Xác minh yêu cầu':t.status==='executing'?'Chờ kết quả phối hợp':t.status==='awaiting_confirmation'?'Kiểm kết quả đã về':t.status==='resolved'?'Hoàn tất và đóng vụ':'Kiểm chứng trước khi đề xuất';}
/* ---- Shell (v0.6): HUD, navigation and task cards. Render-only; every number comes from the server state. ---- */
const EXT=['teacher','tour_guide','milk_tea'];
const layout=()=>document.documentElement.dataset.layout;
/** Update markup only when it changed, and then only the nodes that changed (morph): keeps focus, scroll
 * and running animations. */
function setHTML(el,html){if(el&&el._html!==html){if(el._html===undefined)el.innerHTML=html;else morph(el,html);el._html=html;}}
/* Morph: patch a region to match new markup instead of replacing it. Unchanged nodes keep their identity,
 * so a re-render after every command no longer replays entry animations, re-decodes images, drops focus or
 * jumps the scroll. Nodes are matched by position + tag (+ id); a mismatch is replaced like innerHTML would.
 * Form fields follow the new markup unless the player is in them (focused) or they are data-preserve;
 * <details> keep the player's open/closed state, except <details data-auto>: there the render's `open`
 * attribute wins (a fold the career opens for the current step and shuts after it). English mode: text the
 * i18n layer already translated from the same Vietnamese source is left alone. */
const morphTpl=document.createElement('template');
const sheetScroll=scrollGuard();   // the open sheet's scroll: redraws wait for a fling, inner lists keep their place
const morphSame=(cur,src)=>cur===src||cur===i18nT(src);
function morph(el,html){morphTpl.innerHTML=html;morphKids(el,morphTpl.content);morphTpl.innerHTML='';}
function morphKids(from,to){
  // Runtime-owned views keep their canvas and focus during state refreshes.
  if(from.nodeType===1&&to.nodeType===1&&from.hasAttribute('data-morph-static')&&to.hasAttribute('data-morph-static'))return;
  let a=from.firstChild,b=to.firstChild;
  while(b){
    if(a?.nodeType===1&&a.hasAttribute('data-morph-keep')){a=a.nextSibling;continue;}   // a line another module put in the page (tutorial/tips.js inline hint)
    const nb=b.nextSibling;
    if(a&&a.nodeType===b.nodeType&&a.nodeName===b.nodeName&&(a.nodeType!==1||a.id===b.id)){morphNode(a,b);a=a.nextSibling;}
    else if(a){const na=a.nextSibling;from.replaceChild(b,a);a=na;}
    else from.appendChild(b);
    b=nb;
  }
  while(a){const na=a.nextSibling;a.remove();a=na;}
}
function morphNode(a,b){
  if(a.nodeType!==1){if(!morphSame(a.nodeValue,b.nodeValue))a.nodeValue=b.nodeValue;return;}
  const tag=a.nodeName,skipOpen=tag==='DETAILS'&&!b.hasAttribute('data-auto');
  if(skipOpen)a._mk=b.hasAttribute('open');   // what the markup asks for, used when the fold is new here
  for(const at of b.attributes){if(skipOpen&&at.name==='open')continue;const cur=a.getAttribute(at.name);if(cur===null||!morphSame(cur,at.value)){if(at.namespaceURI)a.setAttributeNS(at.namespaceURI,at.name,at.value);else a.setAttribute(at.name,at.value);}}
  for(let i=a.attributes.length-1;i>=0;i--){const n=a.attributes[i].name;if(!(skipOpen&&n==='open')&&!b.hasAttribute(n))a.removeAttribute(n);}
  morphKids(a,b);
  if(tag==='INPUT'||tag==='TEXTAREA'||tag==='SELECT'){
    if(a.hasAttribute('data-preserve')||a===document.activeElement||a.type==='file')return;
    if(tag==='SELECT'){for(let i=0;i<b.options.length;i++)if(a.options[i]&&a.options[i].selected!==b.options[i].selected)a.options[i].selected=b.options[i].selected;}
    else{if(a.value!==b.value)a.value=b.value;if(a.checked!==b.checked)a.checked=b.checked;}
  }
}
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
  else list=[['queue','folder','Sổ việc','Chọn một vụ'],['workbench',m.icon,id==='accounting'?'Đối chiếu':'Xử lý','Bàn làm việc'],id==='accounting'?['warehouse','book','Tủ hồ sơ','Sổ khách tháng']:['warehouse','clipboard','Theo dõi','Vụ nhiều ngày'],['decor','plant','Góc của bạn','Nâng cấp']];
  if(id==='teacher')list.unshift(['classroom','calendar','Kế hoạch lớp','Tiết học & sự kiện']);
  return list;
}
function navItems(c){
  const items=[['home','grid','Đổi nghề'],['prepare','coffee','Chuẩn bị'],['feedback','star','Đánh giá',lowOpen(c)],['phone','phone','Chuyện phố',feedUnread(c)?'dot':0],['situation','flag','Tình huống',openSituation(c)?'dot':0],['incident','shield','Chuyện đời',L.inc.m?.incidentBadge(c)||0]];
  items.splice(4,0,['nhom','chat','Nhóm phố',boardUnread(api)],['social','globe','Phố nghề',api.social?.unread||0]);  // Nhóm Cư Dân Phố (v4/board.js), Phố nghề (v4/social.js)
  if(c.job?.required)items.push(['jobapp','briefcase','Việc làm',needsJob()?'dot':0]);
  items.push(['operations','store',wordsFor(career()).books,c.ops?.alerts?.length?'dot':0]);
  if(!EXT.includes(career()))items.push(['journal','book','Sổ tay']);
  items.push(['people','people','Người quen',L.people.m?.closenessBadge(api)||0],['album','camera','Kỷ niệm'],['workshop','sparkle','Trò nhỏ'],['passport','award','Hộ chiếu'],['jrTown','compass','Bản đồ phố'],['rank','award','Xếp hạng']);  // 🗺️ Bản đồ phố: the walkable town (v4/town-walk.js; the old Khu phố map is its 🎏 Quảng trường); Bảng xếp hạng (v4/leaderboard.js)
  items.push(['jrWardrobe','shirt','Tủ đồ']);  // 👗 Tủ đồ (v4/wardrobe.js, opened by journey.js)
  {const chat=L.live.m?.liveNav();if(chat)items.push(chat);}  // 💬 Chat (v4/live.js): only while the live service has it on
  {const lv=L.live.m?.live;if(lv?.flags.street&&lv.welcomed)items.push(['liveWalk','map','Đi dạo']);}  // 🚶 Đi dạo (v4/walk.js): only while the live service has it on
  {const date=L.live.m?.dateNav();if(date)items.push(date);}  // 💕 Góc hẹn hò (v4/dating.js): only while the live service has dates on
  {const lv=L.live.m?.live;if(lv?.flags.wedding&&lv.welcomed)items.push(['liveWed','heart','Lịch cưới']);}  // 💍 Lịch cưới (v4/wedding.js): live weddings, while on
  {const lv=L.live.m?.live;if(lv?.flags.kara&&lv.welcomed)items.push(['liveKara','music','Phòng hát']);}  // 🎤 Phòng hát (v4/karaoke.js): only while the live service has it on (LIVE_KARAOKE)
  items.push(['friends','user','Bạn bè',api.friendAlerts||0],['marriage','heart','Hôn nhân',api.marriageAlerts||0]);  // Bạn bè + Hôn nhân (v4/marriage.js, own dialog; badges from v4/ticker.js)
  items.push(['money','bag','Tiền của bạn']);  // 💰 the money sheet (v4/wealth.js), also behind the HUD money chips
  {const bk=api.state?.journey?.bank;items.push(['bank','coin','Ngân hàng',bk?.unread||(bk?.overdue?'dot':0)]);}  // 🏦 Ngân hàng Phố (v4/bank.js, own dialog)
  if(api.state?.journey?.story)items.push(['house','home','Nhà của bạn',api.state.journey.home?.own?.loan?.overdue?'dot':0]);  // 🏠 Nhà của bạn (v4/house.js, own dialog)
  if(api.state?.journey?.story&&api.state.journey.garage)items.push(['garage','bike','Xe & phương tiện']);  // 🚗 (v4/garage.js, own dialog): only once the server has it
  if(api.state?.journey?.story&&api.state.journey.gadgets)items.push(['gadgets','phone','Điện thoại & đồ công nghệ']);  // 📱 (v4/gadgets.js, own dialog): only once the server has it
  if(api.state?.journey?.story&&api.state.journey.pets)items.push(['pets','paw','Thú cưng']);  // 🐾 v4/pets.js (own dialog): only once the server has it
  if(api.state?.journey?.story&&api.state.journey.spend)items.push(['spend','coffee','Đi chơi'],['spendStyle','sparkle','Phong cách']);  // ☕🙏 quán, spa, rạp, công đức; 🎨 màu tên tuần (v4/spend.js, own dialog): only once the server has it
  if(api.state?.rui)items.push(['rui','shield','Bảo hiểm',api.state.rui.card||api.state.rui.warn?'dot':0]);  // 🛡️ Rủi ro & bảo hiểm (v4/rui.js): only once the server has it
  if(api.state?.journey?.story)items.push(['jrInvest','coin','Đầu tư']);
  if(api.state?.journey?.story&&api.content?.journey?.quay)items.push(['quay','store','Quầy của bạn',quayBadge()]);  // 🏪 (v4/quay.js, own dialog): only once the server has it
  if(api.state?.fair?.show)items.push(['fair','flag','Hội chợ',api.state.fair.open&&!api.state.fair.played?'dot':0]);  // 🏮 Hội chợ dân gian (v4/fair.js, own dialog): only around the fair's days
  // A career with its own shell (the air crew: no Sổ tiệm, a flight log instead) reshapes the list; others keep it.
  const result=careerUI(career())?.nav?.(items,careerContext(env()))||items;
  if(!result.some(x=>x[0]==='accountingSchool'))result.push(['accountingSchool','calculator','Học kế toán']);  // 📒 Học kế toán (v4/accounting-school.js): every career, after a career's own reshaping
  if(api.state?.journey?.story&&!result.some(x=>x[0]==='jrInvest'))result.push(['jrInvest','coin','Đầu tư']);
  return result;
}
/** 🏪 A dot when a counter needs its owner: a thief, rent to pay, closed waiting, or a till to collect soon. */
function quayBadge(){const q=api.state?.journey?.quay;if(api.quayInvites>0)return api.quayInvites;return q?.shift||(q?.stalls||[]).some(st=>(st.case&&!st.case.rep)||st.due||st.closed||(st.left<=1&&st.till>0))?'dot':0;}   // 💼 a friend's shift invitation: its count
/** 💼 A hired shift's day just closed (game/quay.py on_shift): settle it now (game/quay_hire.py flush; every load does too). */
async function quayFlush(){try{const d=await api.post('/api/quay/flush',{});if(d?.state&&typeof d.revision==='number')api.accept({state:d.state,revision:d.revision});}catch{/* the next load settles it */}}
const badgeHTML=b=>b==='dot'?'<i class="dot" aria-hidden="true"></i>':b?`<em class="badge">${b}</em>`:'';
/** One line under the look-alike Khu phố entries, so each says what it is (owner D5: names stay, lines added). */
const RAIL_NOTE={home:'Hành trình · mục tiêu của bạn',jrTown:'Dạo phố, vào nơi làm',social:'Ghé tiệm người chơi khác',nhom:'Tin nhắn hàng xóm',phone:'Khách khen, chê, kể chuyện'};
const railItem=([a,i,label,badge],extra='',hide='')=>`<button type="button" class="rail-item${a==='social'?' top-social':''}${extra} ${ui.view===a?'active':''}" data-action="${a}"${ui.view===a?' aria-current="page"':''}${hide}>${icon(i,21)}<span>${label}</span>${RAIL_NOTE[a]?`<small class="rail-note">${RAIL_NOTE[a]}</small>`:''}${badgeHTML(badge)}</button>`;
/** The work pages, always in sight (rail on desktop/tablet, top of "Thêm" on the phone), in this order. Any
 * entry that is in no group below (a career's own page) joins them, so nothing a career adds is lost. */
const RAIL_MAIN=['liveChat','home','prepare','operations','jrInvest','prices','feedback','jobapp','accountingSchool'];   // 💬 Chat first, one tap (owner, 01/10)
/** Học kế toán is a work page for the office accountants; everyone else finds it under "Của mình". */
const ACC_CAREERS=['accounting','corp_accounting','tax_payroll','group_accounting'];
const railMain=x=>!RAIL_GROUPED.has(x[0])||(x[0]==='accountingSchool'&&ACC_CAREERS.includes(career()));
/** The rest sit in small hubs, one tap further: [id, icon, label, entries]. The hub carries its entries' badges. */
const RAIL_GROUPS=[
  ['pho','building','Khu phố',['fair','spend','pets','liveWalk','liveWed','liveKara','nhom','phone','social','jrTown','rank']],
  ['ban','people','Quan hệ',['liveDate','people','friends','marriage']],
  ['tien','coin','Ngân hàng & nhà',['money','bank','house','garage','gadgets','rui','quay']],
  ['chuyen','note','Chuyện của bạn',['situation','incident']],
  ['minh','gift','Của mình',['jrWardrobe','spendStyle','album','passport','workshop','journal','accountingSchool']],
];
/** ☕ v4/spend.js (game/spend.py): the menu entries and the town map's doors (each opens its tab). */
const SPEND_OPEN=new Set(['spend','spendQuan','spendSpa','spendRap','spendChua','spendStyle']);
const RAIL_GROUPED=new Set(RAIL_GROUPS.flatMap(g=>g[3]));
/** Numbers add up; a dot alone stays a dot. */
function groupBadge(items){
  let n=0,dot=false;for(const x of items){const b=x[3];if(!b)continue;if(Number.isFinite(Number(b)))n+=Number(b);else dot=true;}
  return n||(dot?'dot':0);
}
/** "Kho" on the bar: a number of items running low (stock + on the way), or 📦 when a crate is in to count.
 * Milk tea keeps its own counter (data.boba): what is out and not ordered yet. 0: nothing to say. */
function stockBadge(c){
  if(c.inventory){if(crates(c.inventory).ready.length)return '📦';return lowItems(c,api.content,career()).length;}
  const b=c.data?.boba;if(!b)return 0;
  const ordered=id=>(b.orders||[]).some(o=>o.item===id);
  return (b.stations||[]).filter(s=>s.unlocked&&s.on!==false&&s.stock===0&&!ordered(s.id)).length+['M','L'].filter(z=>b.cups&&b.cups[z]===0&&!ordered('cup_'+z)).length;
}
/** Phone bar (owner, 03/10: "Nông trại của bà"): the same five places in every career, always in sight:
 * (1) customers / work list, (2) the bench, (3) Kho, (4) Sổ tiệm, (5) Thêm. A career without a stock room or
 * a shop book gets its next own scene action there (Tủ hồ sơ, Kế hoạch lớp…), else Chuẩn bị.
 * Entries are [action, icon, label, badge, full name]; tablet/desktop keep every scene action. */
function dockItems(c=room()){
  const all=sceneActions();if(layout()!=='phone')return all.map(([a,i,l])=>[a,i,l,0,l]);
  const nav=navItems(c),out=[],has=a=>out.some(x=>x[0]===a);
  // A long name keeps its first half on the bar ("Sân chùa & chánh điện" → "Sân chùa"); the full one is its aria-label.
  const short=l=>l.length>14&&l.includes(' & ')?l.split(' & ')[0]:l;
  const add=(x,badge=0,label)=>{if(x&&!has(x[0]))out.push([x[0],x[1],label||short(x[2]),badge,x[2]]);return !!x;};
  // A career's own 'car:' entries (Bảng nội quy, Sổ tay nhà) open a pane inside its work sheet, so from the
  // scene they show nothing: those stay in Thêm, and the slot goes to Chuẩn bị.
  const own=()=>all.find(x=>!has(x[0])&&x[0]!=='decor'&&!x[0].startsWith('car:'));
  const prep=()=>nav.find(x=>x[0]==='prepare'&&!has('prepare'));
  add(all.find(x=>x[0]==='queue')||all[0]);
  add(all.find(x=>x[0]==='workbench'));
  // Kho: the career's stock room ("Kho kem", "Kho hàng" → "Kho"; "Vật tư", "Tủ hồ sơ" keep their name);
  // milk tea's lives in Chuẩn bị (the 'warehouse' action opens it on that tab).
  const kho=all.find(x=>['inventory','warehouse'].includes(x[0]))||(career()==='milk_tea'?['warehouse','box','Kho']:null);
  if(kho)add(kho,stockBadge(c),/^Kho(\s|$)/.test(kho[2])?'Kho':'');
  else add(own()||prep());
  // Sổ tiệm (the career's own word: Sổ chùa…), or the air crew's Sổ bay (careerUI().nav turns it into 'prices').
  const ops=nav.find(x=>x[0]==='operations'),book=nav.find(x=>x[0]==='prices');
  if(ops)add(ops,ops[3],wordsFor(career()).books||ops[2]);else add(book||own()||prep(),book?.[3]||0);
  return out;
}
/** Desktop/tablet: the work pages, the hubs (each opens in place under its button) and a footer (Hỏi nhanh, Góp ý,
 * Cài đặt; the career guides open from the "?" of each work screen and Cài đặt).
 * Phone ("Thêm" sheet): the scene actions the dock has no room for, the same entries in a grid; a hub fills
 * the sheet with a back button. Every entry is always in the markup (hidden when folded) so deep links
 * ("Thử ngay" in Có gì mới) and sweeps still find it by data-action. */
function railHTML(c){
  const phone=layout()==='phone',shown=dockItems(c),onBar=x=>phone&&shown.some(y=>y[0]===x[0]),extra=phone?sceneActions().filter(x=>!onBar(x)):[];
  const nav=navItems(c),order=x=>{const i=RAIL_MAIN.indexOf(x[0]);return i<0?RAIL_MAIN.length:i;};
  const main=nav.filter(railMain).sort((a,b)=>order(a)-order(b));
  const groups=RAIL_GROUPS.map(([g,ic,label,ids])=>[g,ic,label,ids.map(id=>nav.find(x=>x[0]===id)).filter(x=>x&&!railMain(x))]).filter(g=>g[3].length);
  const open=groups.some(g=>g[0]===ui.railGroup)?ui.railGroup:null,hide=phone&&open?' hidden':'';
  const title=t=>phone?`<p class="rail-title"${hide}>${esc(t)}</p>`:'';
  const mini=(a,i,l,d='')=>`<button type="button" class="rail-mini${ui.view===a?' active':''}" data-action="${a}"${d} aria-label="${l}" title="${l}">${icon(i,19)}<span>${l}</span></button>`;
  return (extra.length?title(wordsFor(career()).rail_in)+extra.map(([a,i,l])=>railItem([a,i,l],'',hide)).join(''):'')+
    // The phone's "Thêm" does not repeat the bar: those entries stay in the markup, hidden (deep links, sweeps).
    title('Công việc')+main.map(x=>railItem(x,'',onBar(x)?' hidden':hide)).join('')+title('Đời sống')+
    groups.map(([g,ic,label,items])=>{const on=open===g,cur=items.some(x=>x[0]===ui.view);
      return `<button type="button" class="rail-item rail-group${cur?' active':''}" data-action="v4Group" data-group="${g}" data-menu-stay aria-expanded="${on}"${hide}>${icon(ic,21)}<span>${label}</span>${badgeHTML(groupBadge(items))}<i class="rail-caret" aria-hidden="true">${icon('chevron',12)}</i></button>`+
        `<div class="rail-sub" data-group="${g}" role="group" aria-label="${label}"${on?'':' hidden'}><div class="rail-sub-head"><button type="button" class="icon-btn rail-back" data-action="v4Group" data-group="" data-menu-stay aria-label="Quay lại">${icon('back',20)}</button><b>${label}</b></div>${items.map(x=>railItem(x)).join('')}</div>`;}).join('')+
    `<div class="rail-foot"${hide}>${mini('tutGuide','question','Hỏi nhanh',' data-topic="quick"')}${mini('gopy','chat','Góp ý')}${mini('settings','settings','Cài đặt')}</div>`;   // ❓ Hỏi nhanh (tutorial/guide.js)
}
/** Open or fold a hub (data-group="" folds). Phone: the sheet scrolls back to the top and focus follows. */
function railGroup(g,focus=true){
  const was=ui.railGroup;ui.railGroup=g&&was!==g?g:null;const rail=$('#rail');setHTML(rail,railHTML(room()));
  if(layout()!=='phone'||!focus)return;
  rail.scrollTop=0;
  rail.querySelector(ui.railGroup?'.rail-sub:not([hidden]) .rail-back':`.rail-group[data-group="${CSS.escape(was||'')}"]`)?.focus({preventScroll:true});
}
function dockHTML(c){
  const phone=layout()==='phone',low=lowOpen(c),items=dockItems(c);
  const more=phone&&navItems(c).some(x=>x[3]&&!items.some(y=>y[0]===x[0]));
  return items.map(([a,i,l,b,full])=>`<button type="button" class="dock-btn${a==='workbench'?' main':''}${phone&&l.length>14?' long':''}" data-action="${a}"${full!==l?` aria-label="${esc(full)}" title="${esc(full)}"`:''}>${icon(i,22)}<span>${l}</span>${badgeHTML(a==='feedback'&&low?low:b)}</button>`).join('')+
    (phone?`<button type="button" class="dock-btn dock-more" data-action="v4Menu" aria-label="${esc(wordsFor(career()).more_aria)}" aria-expanded="${document.documentElement.classList.contains('menu-open')}">${icon('menu',22)}<span>Thêm</span>${more?'<i class="dot" aria-hidden="true"></i>':''}</button>`:'');
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
/** Something new behind the status sheet: a life story waiting (Phố nghề / Nhóm phố messages: the dot on Thêm). */
const statusDot=()=>Boolean(api.state.life?.pending);
function hudHTML(c,m){
  // 💰 Two labelled chips (v4/wealth.js): this workplace's fund and the wallet; either opens "Tiền của bạn".
  const money=hudChipsHTML(hudMoney(api.state,career()),{phone:layout()==='phone',short:shortMoney});
  return `<button type="button" class="cozy-day hud-day" data-action="status" aria-haspopup="dialog" aria-label="Ngày ${dayNo(c)}. ${esc(clockAria(c.day_clock))}"><strong>Ngày ${dayNo(c)}</strong>${clockChip(c.day_clock)}${icon('chevron',12)}${statusDot()?'<i class="dot" aria-hidden="true"></i>':''}</button>`+
    `<div class="cozy-till hud-money" role="group" aria-label="Tiền của bạn">${money}</div>`;
}
/** "Cần để ý": things waiting besides the task in hand (event, incident, low reviews, shop alerts…). */
function hudNotes(c){
  const notes=[],x=openSituation(c),cl=c.classroom,low=lowOpen(c),alert=c.ops?.alerts?.[0];
  if(c.event)notes.push(['event',{},c.event.practice?'play':'flag',c.event.practice?'Diễn tập':'Chuyện ở góc phố',c.event.stage==='resolved'?'Đã có kết quả · xem lại':c.event.title]);
  if(x)notes.push(['situation',{},'flag',x.tone==='tense'?'Chuyện căng':'Chuyện đời thường',x.title]);
  const incNote=L.inc.m?.incidentNote(c);if(incNote)notes.unshift(incNote);
  if(cl&&c.open){const ev=cl.active||cl.offers.find(o=>o.kind==='event');if(ev)notes.push(['classroom',{},'book',cl.active?'Đang làm dở':'Lịch lớp · '+cl.month,`${ev.emoji} ${ev.title}`]);}
  if(low)notes.push(['feedback',{filter:'open'},'star','Đánh giá',`${low} đánh giá ≤3★ chờ bạn trả lời`]);
  if(alert)notes.push(['opsTab',{tab:alert.tab},'store',wordsFor(career()).books,alert.text]);
  return notes;
}
const noteRows=notes=>notes.map(([a,d,i,k,txt])=>`<button type="button" class="hud-note" data-action="${a}"${attrs(d)}><span class="hud-note-ico">${icon(i,16)}</span><span class="grow"><small>${esc(k)}</small><b>${esc(txt)}</b></span>${icon('chevron',14)}</button>`).join('');
/** The status sheet: what the top bar used to carry, one tap away. */
function statusView(){
  const c=room(),m=meta(),J=api.state.journey,L=api.state.life,w=c.life?.weather,clk=hudClock(c),reviews=c.feed.filter(p=>p.stars).length,left=c.tasks.filter(t=>!ended(t)).length;
  const mode=c.life?.mode&&c.life.mode!=='normal'?api.content.experiences?.modes?.find(x=>x.id===c.life.mode):null;
  const tile=(action,ico,value,label,data={},badge=0)=>`<${action?'button type="button"':'div'} class="st-tile${value?'':' st-link'}"${action?` data-action="${action}"`:''}${attrs(data)}><span class="st-ico" aria-hidden="true">${ico}</span>${value?`<b>${value}</b>`:''}<small>${label}</small>${badge?`<em class="badge">${badge}</em>`:''}</${action?'button':'div'}>`;
  const tiles=[
    c.open?tile('stPause',icon(ui.paused?'play':'pause',18),clk||(ui.paused?'▶':'⏸'),ui.paused?'Tiếp tục':'Tạm dừng'):'',
    tile('queue',icon('clipboard',18),String(left),c.open?'việc đang chờ':'Đang nghỉ'),
    tile('feedback','<span class="st-star">★</span>',c.rating?Number(c.rating).toFixed(1):'—',`${reviews} ${esc(wordsFor(career()).rating)}`),
    w?tile('',esc(w.emoji),esc(w.name),mode?esc(mode.name):'Hôm nay'):'',
    J?tile('money','👛',J.debt?`−${shortMoney(J.debt)}`:shortMoney(J.wallet),'Ví của bạn'):'',
    L?.enabled?tile('stView',esc(L.mood?.emoji||'🙂'),`${L.spirit|0}/100`,'Tinh thần',{view:'life'},L.pending?'!':0):'',
    api.state.needs?.enabled?tile('stView','🍚',`${api.state.needs.full.value|0}/100`,'No bụng',{view:'life'}):'',
    api.state.needs?.enabled?tile('stView','😴',`${api.state.needs.wake.value|0}/100`,'Tỉnh táo',{view:'life'}):'',
  ].join('');
  const notes=hudNotes(c);
  return header(`Ngày ${dayNo(c)}`,'',esc(c.life.shop_name||m.place))+`<div class="sheet-body st-body">${clockCard(c.day_clock)}${notes.length?`<div class="st-notes">${noteRows(notes)}</div>`:''}<div class="st-grid">${tiles}</div>`+
    (c.shift_summary&&!c.open?button('Xem ngày vừa qua','summary',{},'ghost small full'):'')+`</div>`;
}
/** 🎖️ One line on the morning card: the title and the good days towards the next step (a tap opens Thăng tiến),
 * the review when one waits, and 🧑‍💼 from step 3. Nothing for a brand-new place. */
function promoStrip(c){
  const p=c.promo;if(!p||!(p.rank||p.due||p.next?.good||p.mgr))return '';
  if(p.due)return `<button type="button" class="pm-strip due" data-action="promo"><span aria-hidden="true">🎖️</span><b>${p.due.who==='Phòng sếp'?'Sếp hẹn gặp bạn':p.due.who==='Ban chỉ huy'?'Ban chỉ huy hẹn gặp':'Hội buôn phố ghé thăm'}</b><small>${esc(p.due.title)}</small></button>`;
  const n=p.next,w=n?Math.round(100*n.good/Math.max(1,n.need)):100;
  return `<div class="pm-strip-row"><button type="button" class="pm-strip" data-action="promo"><span aria-hidden="true">🎖️</span><b>${esc(p.title)}</b>${p.org?`<small class="og-warn${p.org.warns.length?' on':''}">⚠️ ${p.org.warns.length}/${p.org.warn_max}</small>`:''}${n?`<small>${n.good}/${n.need}</small><span class="bar"><i style="width:${w}%"></i></span>`:''}</button>${p.mgr?'<button type="button" class="pm-strip mgr" data-action="promo" aria-label="Ca quản lý">🧑‍💼</button>':''}</div>`;
}
function taskCards(c){
  const t=c.tasks.find(x=>x.id===c.active_task&&!ended(x))||c.tasks.find(x=>!ended(x)),W=wordsFor(career()),desk=deskWork(),notes=hudNotes(c);
  const bell=notes.length?`<button type="button" class="hud-alerts" data-action="status" aria-label="Cần để ý · ${notes.length}">${icon('bell',17)}<b>${notes.length}</b></button>`:'';
  // First task at this place (no one served yet): the one way on glows (guide.js pulse), like the work screens.
  const first=c.metrics?.served>0?'':' gd-pulse';
  let main;
  if(needsJob())main=`<article class="note-card calm-card">${button('Xin việc '+icon('chevron',13),'jobapp',{},'primary big grow gd-pulse')}${bell}</article>`;
  else if(!c.open)main=`<article class="note-card calm-card">${button(icon('sun',16)+' Chuẩn bị ngày mới'+(c.day_clock?` · mở ${esc(c.day_clock.open_time)}`:''),'prepare',{},'primary big grow'+first)}${eveningDue()?'<button type="button" class="icon-btn hud-sum nd-moon-btn" data-action="evening" aria-label="Buổi tối: ăn gì, ngủ mấy giờ"><span aria-hidden="true">🌙</span></button>':''}${c.shift_summary?`<button type="button" class="icon-btn hud-sum" data-action="summary" aria-label="Xem ngày vừa qua">${icon('clipboard',18)}</button>`:''}${bell}</article>`;
  // The one line is the work screen's "Bước tiếp theo" (career modules' next() = guide.stepLine of the next
  // step, plain text); "Làm tiếp" opens the work screen, whose bottom button (stepCta) does that step.
  else if(t)main=`<article class="note-card calm-card task-card">${closingNote(c.day_clock,true,moreGate(c))}<button type="button" class="calm-what" data-action="job" data-task="${esc(t.id)}" title="${esc(t.title)}"><span class="npc-mini">${customerPortrait(visitCustomer(t,npc(t.npc)),34)}</span><b>${esc(plainText(taskNext(t)))}</b></button>${bell}${button('Làm tiếp '+icon('arrow',14),'job',{task:t.id},'primary'+first)}</article>`;
  // Day one, its three jobs done: closing the day is the next step (and the chapter goal).
  // Closing time with nobody in hand: close the day (the summary follows).
  // So is a day whose customers are all dealt, or whose next customer would arrive at closing time (more_gate).
  else if(moreGate(c)||c.day_clock?.is_open&&c.day_clock.level==='closing')main=`<article class="note-card calm-card">${closingNote(c.day_clock,false,moreGate(c))}${button(icon('exit',16)+' Khép ca · xem tổng kết','end',{},'primary big grow gd-pulse')}${bell}</article>`;
  else if(wrapUp(c))main=`<article class="note-card calm-card">${button('Khép ca hôm nay','end',{},'primary big grow gd-pulse')}${moreGate(c)?'':`<button type="button" class="icon-btn hud-sum" data-command="more_work" data-payload="{}" aria-label="${desk?'Nhận thêm một việc':esc(W.more_btn)}">${icon('plus',18)}</button>`}${bell}</article>`;
  else main=`<article class="note-card calm-card">${commandButton(desk?'Nhận thêm một việc':esc(W.more_btn),'more_work',{},'primary big grow')}<button type="button" class="icon-btn hud-sum" data-action="end" aria-label="Khép ca hôm nay">${icon('exit',18)}</button>${bell}</article>`;
  // A career with its own home card (the air crew's boarding pass) draws it; hiring keeps the shared "Xin việc".
  // 🧑‍💼 A manager shift's day: the board is the one way on (closed: the day's close).
  const mg=c.open&&!needsJob()?c.promo?.shift:null;
  const own=needsJob()||mg?'':careerUI(career())?.hudCard?.(c,t,careerContext(env()),{bell,first,wrap:wrapUp(c),note:closingNote(c.day_clock,!!t,moreGate(c))});if(own)main=own;
  if(mg)main=`<article class="note-card calm-card">${mg.closed?button(icon('exit',16)+' Khép ca · xem tổng kết','end',{},'primary big grow gd-pulse'):button('🧑‍💼 Bảng quản lý','pmBoard',{},'primary big grow')}${bell}</article>`;
  // 🎖️ The morning card carries the ladder (title · good days) or the review waiting (game/promotion.py).
  const ps=!c.open&&!needsJob()?promoStrip(c):'';
  if(ps)main=main.replace(/^<article class="/,'<article class="pm-has-strip ').replace(/^(<article[^>]*>)/,'$1'+ps);

  // 🍱 Lunch (v4/needs.js): a strip at the top of the card, from 11:30 on the shop clock; one tap, never a modal.
  // 🍢 Ăn thêm: the same strip when hungry or sleepy outside lunch (paid; the Đời thường sheet always has it).
  const lunch=c.open&&!needsJob()?lunchStrip(api.state.needs,api.state.journey?.wallet|0)||(snackDue(api.state.needs)?snackStrip(api.state.needs):''):'';
  if(lunch)main=main.replace(/^<article class="/,'<article class="nd-has-lunch ').replace(/^(<article[^>]*>)/,'$1'+lunch);
  // Desktop has a side column for the list; phone and tablet keep it behind the bell (status sheet).
  const list=notes.length&&layout()==='desktop'?`<article class="note-card hud-notes"><span class="eyebrow">Cần để ý · ${notes.length}</span>${noteRows(notes)}</article>`:'';
  return main+sellerVisitStrip(c)+list;
}
/** When the next step of the task in hand changes while the player is in the scene, draw the eye to the card once. */
function stepHint(c){
  const t=c.open&&!needsJob()?c.tasks.find(x=>x.id===c.active_task&&!ended(x)):null;
  const key=t?`${career()}|${t.id}|${taskNext(t)}`:'';
  if(ui.hintKey===undefined){ui.hintKey=key;return;}
  if(key===ui.hintKey||$('#sheet').open||$('#confirmDialog').open||ui.paused)return;
  // The task card already shows the step: a new step of the same task gives the card a brief pulse (no toast).
  const same=t&&ui.hintKey.startsWith(`${career()}|${t.id}|`);ui.hintKey=key;const card=$('#taskHUD .task-card');if(same&&card)replay(card,['pulse']);
}
/** Coin pop / star bump when the server says money or rating changed. */
function hudFeedback(c){
  const prev=ui.hudPrev,dc=c.day_clock,clk=dc?{day:c.day,minute:dc.minute,is_open:dc.is_open}:null,wallet=api.state?.journey?.wallet;ui.hudPrev={career:career(),money:c.money,rating:c.rating,clk,wallet};
  if(!prev||prev.career!==career())return;
  // "+20 phút": how long that action took on the shop clock, floating under the clock.
  const step=clockStep(prev.clk,clk),chip=step&&$('#topbar .dc-chip');
  if(chip)requestAnimationFrame(()=>{if(!chip.isConnected)return;const r=chip.getBoundingClientRect(),pop=document.createElement('span');pop.className='coin-pop dc-pop up';pop.setAttribute('aria-hidden','true');
    pop.textContent=`+${step} phút`;pop.style.left=`${Math.round(r.left+r.width/2)}px`;pop.style.top=`${Math.round(r.bottom-2)}px`;document.body.append(pop);setTimeout(()=>pop.remove(),1500);});
  const d=c.money-prev.money,till=$('#topbar .hud-fund')||$('#topbar .cozy-till');
  if(wallet!=null&&prev.wallet!=null&&wallet!==prev.wallet){const w=$('#topbar .hud-wallet');if(w)replay(w,['bump']);}
  // Layout is read and animations restarted in the next frames, not mid-render (no forced synchronous layout).
  if(d&&till){
    requestAnimationFrame(()=>{
      if(!till.isConnected)return;const r=till.getBoundingClientRect(),pop=document.createElement('span');
      pop.className=`coin-pop ${d>0?'up':'down'}`;pop.setAttribute('aria-hidden','true');pop.textContent=`${d>0?'+':'−'}${fmt(Math.abs(d))} xu`;
      pop.style.left=`${Math.round(r.left+r.width/2)}px`;pop.style.top=`${Math.round(r.bottom-6)}px`;document.body.append(pop);setTimeout(()=>pop.remove(),1500);
    });
    replay(till,['bump']);
  }
  if(c.rating&&prev.rating!==c.rating){const down=prev.rating&&c.rating<prev.rating,day=$('#topbar .hud-day');
    if(day)requestAnimationFrame(()=>{if(!day.isConnected)return;const r=day.getBoundingClientRect(),pop=document.createElement('span');pop.className=`coin-pop rate ${down?'down':'up'}`;pop.setAttribute('aria-hidden','true');
      pop.textContent=`★ ${Number(c.rating).toFixed(1)}`;pop.style.left=`${Math.round(r.left+r.width/2)}px`;pop.style.top=`${Math.round(r.bottom-6)}px`;document.body.append(pop);setTimeout(()=>pop.remove(),1500);});}
}
/** Restart a CSS animation class without forcing layout: off now, back on two frames later. */
function replay(el,add,off=add){el.classList.remove(...off);requestAnimationFrame(()=>requestAnimationFrame(()=>el.isConnected&&el.classList.add(...add)));}
let mainDeferred=false;
function renderMain(){
  if(!api.state||!api.content)return;
  // The fair owns its visible HUD. Rebuilding the obscured workplace also marks its
  // canvas dirty, competing with the last throw/result frame on mobile devices.
  if(document.querySelector('dialog.fh-sheet[open]')){mainDeferred=true;return;}
  mainDeferred=false;const c=room(),m=meta();
  document.body.classList.toggle('reduce-motion',api.state.settings.reduceMotion);document.body.classList.toggle('large-text',api.state.settings.largeText);shell.career(m);
  setHTML($('#topbar'),hudHTML(c,m));
  setHTML($('#rail'),railHTML(c));
  setHTML($('#sceneHeading'),`${shell.mark(m)}<div class="scene-title"><h1>${esc(c.life.shop_name||m.place)}</h1></div>${careerSwitchButton()}`);
  setHTML($('#sceneBadge'),'');  // open/closed, weather and mode: status sheet (tap the day)
  setHTML($('#taskHUD'),taskCards(c));
  setHTML($('#dock'),dockHTML(c));
  setHTML($('#sceneHint'),c.day<=1&&layout()!=='phone'?`${icon('move',12)} Chạm sàn để đi · Chạm đồ vật để làm · WASD / mũi tên · E tương tác`:'');
  $('#ambientCaption').textContent='';$('#saveState').classList.toggle('offline',!api.connected);
  setHTML($('#saveState'),api.connected?`<i class="saved-dot"></i>Đã lưu`:`<i class="saved-dot"></i>Mất kết nối <button type="button" class="linkish" data-action="reconnect">Thử lại</button>`);
  hudFeedback(c);stepHint(c);
  sound.configure(api.state.settings);world.update(api.state,api.content);
}
document.addEventListener('close',()=>{if(mainDeferred)renderMain();},true);
/* Toasts (and the update pill) sit just under the open sheet's sticky header: never over its title and buttons,
 * nor over the career's action bar at the bottom. The header's bottom edge is kept in --sheet-head-b, read in a
 * ResizeObserver callback (after layout: no forced layout) and once the opening animation has ended. */
const headWatch={el:null,b:-1,ro:typeof ResizeObserver==='function'?new ResizeObserver(()=>headMeasure()):null};
function headMeasure(){
  const h=headWatch.el;if(!h?.isConnected||!$('#sheet').open)return;
  const b=Math.max(0,Math.round(h.getBoundingClientRect().bottom));
  if(b!==headWatch.b){headWatch.b=b;document.documentElement.style.setProperty('--sheet-head-b',b+'px');}
}
function watchHead(dialog){
  const h=dialog.querySelector('#sheetContent>.sheet-head');if(!headWatch.ro||h===headWatch.el)return;
  if(headWatch.el)headWatch.ro.unobserve(headWatch.el);headWatch.el=h;
  if(h)headWatch.ro.observe(h);else{headWatch.b=-1;document.documentElement.style.removeProperty('--sheet-head-b');}
}
if(headWatch.ro){headWatch.ro.observe($('#sheet'));$('#sheet').addEventListener('animationend',e=>{if(e.target===$('#sheet'))headMeasure();});}
function renderSheet(preserve=true){
  if(!ui.view)return;const dialog=$('#sheet');
  // Class names are collected off-DOM and written once, only when they differ (no style invalidation per render).
  let html;const cls=document.createElement('i');cls.className='sheet';
  {const dialog=cls;switch(ui.view){
    case'home':dialog.classList.add('home');if(townOn(env()))dialog.classList.add('tw-sheet');html=homeView();break;  // 🗺️ the town: one fixed height (css/town.css)
    case'future':html=futureView();break;
    case'job':dialog.classList.add('cozy-job');html=jobView();break;
    case'prepare':case'prices':case'workshop':case'passport':case'town':dialog.classList.add('cozy-sheet',ui.view==='prepare'?'prep-sheet':'life-sheet');html=careerUI(career())?.page?.(ui.view,careerContext(env()))||(ui.view==='passport'?moreView:f=>f())(()=>experienceView(ui.view,career(),room(),api.content,meta(),ui,api.state));break;
    case'carPage':dialog.classList.add('medium');html=careerUI(career())?.page?.(ui.carPage,careerContext(env()))||'';if(!html){ui.view='job';html=jobView();dialog.classList.replace('medium','cozy-job');}break;  // a career's own entry opened outside its work sheet (Bảng nội quy, Sổ tay nhà)
    case'queue':dialog.classList.add('medium');html=queueView();break;
    case'chat':dialog.classList.add('medium');html=chatView();break;
    case'phone':dialog.classList.add('medium');html=phoneView();break;
    case'event':dialog.classList.add('medium');html=eventView();break;
    case'journal':dialog.classList.add('medium');html=journalView();break;
    case'people':dialog.classList.add('medium','v4-sheet','qn-sheet');html=lazyView(L.people,m=>m.closenessView(env()));break;
    case'decor':html=decorView();break;
    case'warehouse':dialog.classList.add('medium');html=warehouseView();break;
    case'album':dialog.classList.add('medium');html=albumView();if(api.state.marriage?.spouse)queueMicrotask(()=>import('./v4/wedding.js').then(m=>m.fillAlbum(env())).catch(()=>{}));break;  // 💍 the couple's party photos
    case'settings':dialog.classList.add('medium','v4-sheet','drawer');html=lazyView(L.settings,m=>m.settingsView(env()));break;
    case'social':dialog.classList.add('wide','v4-sheet');html=lazyView(L.social,m=>m.socialView(env()));break;
    case'gopy':dialog.classList.add('medium','v4-sheet','fb-dialog');html=lazyView(L.fb,m=>m.feedbackPageView(env()));break;
    case'nhom':dialog.classList.add('medium','v4-sheet','bd-sheet');html=boardView(env());break;
    case'rank':dialog.classList.add('medium','v4-sheet','lb-sheet');html=lazyView(L.rank,m=>m.leaderboardView(env()));break;
    case'summary':dialog.classList.add('narrow','cozy-summary');html=summaryView();break;
    case'evening':dialog.classList.add('narrow','nd-sheet');html=eveningView();break;  // 🌙 Buổi tối (v4/needs.js)
    case'help':dialog.classList.add('medium');html=helpView();break;
    case'status':dialog.classList.add('narrow','status-sheet');html=statusView();break;
    case'money':dialog.classList.add('medium','v4-sheet','wl-sheet');html=wealthView();break;
    case'inventory':dialog.classList.add('medium','v4-sheet');html=inventoryView(env());break;
    case'feedback':dialog.classList.add('v4-sheet','wide');html=feedbackView(env());break;
    case'situation':dialog.classList.add('medium','v4-sheet');html=moreView(()=>situationView(env()));break;
    case'incident':dialog.classList.add('medium','v4-sheet','inc-sheet');html=lazyView(L.inc,m=>m.incidentView(env()));break;
    case'jobapp':dialog.classList.add('medium','v4-sheet');html=moreView(()=>jobAppView(env()));break;
    case'classroom':dialog.classList.add('wide','v4-sheet');html=lazyView(L.classroom,m=>m.classroomView(env()));break;
    case'accountingSchool':dialog.classList.add('wide','v4-sheet','as-sheet');html=lazyView(L.accountingSchool,m=>m.accountingSchoolView(env()));break;
    case'operations':dialog.classList.add('operations');html=moreView(()=>lazyView(L.ops,m=>m.operationsView(career(),room(),api.content.operations,ui,api.state)));break;
    case'promo':dialog.classList.add('narrow','v4-sheet','pm-sheet');html=lazyView(L.promo,m=>m.promoView(env()));break;  // 🎖️
    case'manager':dialog.classList.add('medium','v4-sheet','pm-sheet');html=lazyView(L.promo,m=>m.managerView(env()));break;  // 🧑‍💼
    default:html=header('Một khoảng thảnh thơi')+`<div class="sheet-body">${empty('Cửa sổ chưa mở','Quay lại cảnh để tiếp tục nhé.')}</div>`;
  }}
  html=shortWork(shutWork(html));
  if(dialog.className!==cls.className)dialog.className=cls.className;
  // A fresh view is written whole; a re-render of the same view is morphed (or skipped when unchanged).
  const box=$('#sheetContent');
  // ui.freshSheet (repaintSheet): same view, but written whole once so the engine lays the text out anew.
  const fresh=ui.freshSheet;ui.freshSheet=false;
  const changed=!preserve||fresh||box._html!==html;
  // Same markup as on screen: nothing to write, so nothing to save and restore either (reading scrollTop there
  // forced a layout on every command).
  if(!changed){applyGuide(dialog);return;}
  // Folds keep the player's open/closed state, matched by id, then data-fold, then their summary text (numbers
  // ignored, so "Kho · 3 món" is still the same fold); a fold not on screen before opens as its markup says.
  // <details data-auto> follow the markup instead and are left out.
  const folds=()=>[...dialog.querySelectorAll('details:not([data-auto])')];
  const foldKey=el=>el.id?'#'+el.id:el.dataset.fold?'@'+el.dataset.fold:'~'+(el.querySelector(':scope>summary')?.textContent||'').replace(/[\d\s]+/g,' ').trim().slice(0,80);
  const foldKeys=list=>{const n={};return list.map(el=>{const k=foldKey(el);n[k]=(n[k]||0)+1;return k+'|'+n[k];});};
  const openedDetails=preserve?(list=>new Map(foldKeys(list).map((k,i)=>[k,list[i].open])))(folds()):null,scroll=preserve?dialog.scrollTop:0,active=document.activeElement,selection=active?.selectionStart;
  const fkey=el=>el.id||(el.name&&el.form?`${el.form.dataset.socForm||el.form.id||''}|${el.form.dataset.pid||el.form.dataset.post||el.form.dataset.id||''}|${el.name}`:null);
  const fields={};if(preserve)dialog.querySelectorAll('[data-preserve]').forEach(el=>{const k=fkey(el);if(k)fields[k]={value:el.value,checked:el.checked};});const focusKey=preserve&&active&&dialog.contains(active)?fkey(active):null;
  sheetScroll.watch(dialog);if(!preserve)sheetScroll.reset();
  if(!preserve||fresh||box._html===undefined)box.innerHTML=html;else if(changed)morph(box,html);
  box._html=html;
  tickNow(env());document.dispatchEvent(new Event('sheetrender'));
  applyGuide(dialog);watchHead(dialog);
  if(preserve){const now=folds(),keys=foldKeys(now);now.forEach((el,i)=>{const want=openedDetails.has(keys[i])?openedDetails.get(keys[i]):(el._mk??el.open);if(el.open!==want)el.open=want;el._mk=undefined;});dialog.querySelectorAll('[data-preserve]').forEach(el=>{const data=fields[fkey(el)];if(data){el.value=data.value;if(el.type==='checkbox')el.checked=data.checked;}});if(dialog.scrollTop!==scroll)dialog.scrollTop=scroll;sheetScroll.restore(dialog);if(focusKey){const el=[...dialog.querySelectorAll('[data-preserve],input,textarea,select')].find(x=>fkey(x)===focusKey);el?.focus({preventScroll:true});try{el?.setSelectionRange(selection,selection);}catch{/* not a text input */}}}
  if(!preserve)dialog.scrollTop=0;
  if(ui.view==='chat'){$('#messages')?.scrollTo(0,$('#messages').scrollHeight);}
}

function homeView(){return homeV4(env());}
const placeOf=cid=>{const m=api.content?.catalogue.find(x=>x.id===cid)||{id:cid};return {name:m.place||m.short||cid,emoji:emojiOf(m)};};
function wealthView(){return wealthHTML(api.state,{joint:jointBalance(),current:career(),place:placeOf,head:(t,sub)=>header(t,'',sub||'NGÂN HÀNG & NHÀ')});}
function futureView(){if(api.state.journey)return futureV4(env());return header('Cả một khu phố phía trước','Những nghề sẽ mở sau','DANH MỤC 19 NGHỀ')+`<div class="sheet-body"><div class="future-grid">${api.content.catalogue.filter(c=>!api.state.careers[c.id]).map(c=>`<article class="future-card">${pill(icon('lock',11)+' Mở sau')}<h3>${esc(c.title||c.name)}</h3><p>${esc(c.core_loop||c.focus||c.summary||c.unique_mechanic||'Một trải nghiệm nghề mới, có cơ chế và câu chuyện riêng.')}</p></article>`).join('')}</div></div>`+footer('',button('Về các nghề đang mở','home',{},'primary'));}
function queueView(){const own=careerUI(career())?.board?.(careerContext(env()));if(own)return own;const c=room(),tasks=c.tasks.filter(t=>!ended(t)),lead=(tasks.find(t=>t.id===c.active_task)||tasks[0])?.id;return header('Việc đang chờ','','SỔ VIỆC · '+esc(meta().place))+`<div class="sheet-body">${!c.open?notice('Ca đang nghỉ. '+button('Bắt đầu ngày','start',{},'small primary'),'amber','sun'):''}<div class="queue-grid">${tasks.map(t=>`<article class="queue-card ${t.id===c.active_task?'active':''}"><div class="row">${customerPortrait(visitCustomer(t,npc(t.npc)),44)}<div class="grow"><h3>${esc(t.title)}</h3>${String(t.title||'').includes(npc(t.npc).display_name)?'':`<small class="muted">${esc(npc(t.npc).display_name)}</small>`}</div>${t.deferred?pill('Đã hẹn','amber'):''}</div><p>${esc(t.opening)}</p><div class="row spread">${pill(taskNext(t),'green')}${button('Làm tiếp '+icon('arrow',13),'job',{task:t.id},t.id===lead?'small primary':'small')}</div></article>`).join('')||empty('Hết việc rồi!','','coffee')}</div></div>`+(c.open?footer(`${c.day_completed} việc đã xong hôm nay`,(moreGate(c)?'':commandButton(icon('plus',14)+' Nhận thêm việc','more_work',{},tasks.length?'ghost':'primary'))+button('Khép ca','end',{},moreGate(c)&&!tasks.length?'primary':'ghost')):'');}
function customerAside(t){const n=npc(t.npc),c=room();let needs='';if(t.needs){if(career()==='mother_baby'){const p=product(t.needs.product),paper=api.content.papers.find(p=>p.id===t.needs.paper);needs=`<strong>${t.needs.qty} × ${esc(p.name)}</strong><br>Ngân sách: ${fmt(t.needs.budget)} xu<br>${t.needs.gift?'Gói giấy '+esc(paper.name):'Không cần gói quà'}`;}}
  return `<aside class="work-aside ${t.known?'known':''} ${!Object.keys(t.basket||{}).length?'empty-tray':''}">${t.known?`<div class="needs"><h4>${icon('clipboard',15)} Điều đã xác nhận</h4><p>${needs||'Đã hiểu mục tiêu.'}</p></div>`:''}${career()==='mother_baby'?basketView(t):''}</aside>`;
}
/** Mother & baby basket (the pharmacy tray lives in pharmacyJob). */
function basketView(t){const lines=Object.entries(t.basket||{});return `<div class="row spread space-top"><h4>Giỏ đang giữ</h4>${pill(Object.values(t.basket||{}).reduce((a,b)=>a+b,0)+' món')}</div><div class="basket">${lines.map(([id,qty])=>{const p=product(id);return `<div class="basket-line">${itemArt(p.icon||'box',40,p.color)}<div><strong>${esc(p.name)}</strong><small>${esc(fmt(room().life.prices[p.id]||p.price)+' xu')} × ${qty}</small></div><button class="icon-btn" aria-label="Bỏ một ${esc(p.name)}" data-command="basket_remove" data-payload="${esc(JSON.stringify({task:t.id,item:id}))}">${icon('minus',14)}</button></div>`;}).join('')||'<div class="empty-basket">Khay còn trống.</div>'}</div><div class="receipt-total"><span>Tiền hàng</span><span>${fmt(lines.reduce((sum,[id,q])=>sum+(room().life.prices[id]||product(id).price)*q,0))} xu</span></div>`;}
function jobView(){
  let t=activeTask();const c=room(),mod=careerUI(career());
  // Counter careers (module.autoNext) go straight to the next waiting customer after a hand-over.
  if(t&&ended(t)&&mod?.autoNext){const n=c.tasks.find(x=>x.id===c.active_task&&!ended(x))||c.tasks.find(x=>!ended(x));if(n){t=n;ui.task=n.id;}}
  // Plugins may show a between-orders panel (settle cash, refuel, field work…).
  const idle=mod?.idle&&(!t||ended(t))?`<div class="career-idle space-top">${mod.idle(careerContext(env()))}</div>`:'';
  if(!t){
    // Between customers there is always one clear way on: the next customer (unless the career's own panel offers it).
    const more=wrapUp(c)?button('Khép ca hôm nay','end',{},'primary gd-pulse'):c.open&&(moreGate(c)||!idle.includes('data-command="more_work"'))?moreWay(c,icon('plus',14)+' '+(deskWork()?'Nhận thêm một việc':esc(wordsFor(career()).next_btn))):'';
    return header(deskWork()?'Bàn làm việc đang trống':esc(wordsFor(career()).none_waiting),c.open?'':'Ca đang nghỉ.')+`<div class="sheet-body">${c.open?'':closedBar()}${idle||empty('Làm điều mình thích một chút','','coffee')}<div class="row wrap space-top">${more}${button(esc(wordsFor(career()).queue_btn),'queue',{},more||idle.includes('more_work')?'ghost':'primary')}${mod?.noDecor?'':button('Chăm chút không gian','decor',{},'ghost')}</div></div>`;
  }
  if(ended(t)){
    // Task done: the thank-you and one clear way on, named for what is really next (nobody waiting: take one
    // more / close the day, never "Công việc tiếp theo"). The career's between-orders panel folds into one line
    // under it (drawn in full it made this screen 2–4 screens deep); it opens by itself when a surprise at the
    // counter needs a decision first (kit.desk_block) or the career marks its panel data-idle-open.
    const way=c.tasks.some(x=>!ended(x))?button('Công việc tiếp theo','nextJob',{},'primary'):wrapUp(c)?button('Khép ca hôm nay','end',{},'primary gd-pulse'):c.open?moreWay(c,deskWork()?'Nhận thêm một việc':esc(wordsFor(career()).more_btn)):'';
    const ways=`${c.open?'':closedBar()}<div class="row wrap space-top done-ways" style="justify-content:center">${way}${button('Đọc lời nhắn','phone',{},'ghost small')}${c.event?button('Chuyện vừa xảy ra','event',{},'cream small'):''}</div>`;
    const open=Boolean(c.data?.desk?.ev)||/data-idle-open|class="fk-event"/.test(idle)||ui.idleOpen===t.id;
    const fold=idle?`<details class="idle-fold space-top" data-auto data-idle-task="${esc(t.id)}"${open?' open':''}><summary>${icon('clipboard',16)}<b>${deskWork()?'Bàn làm việc':'Việc giữa ca'}</b></summary>${idle}</details>`:'';
    if(t.desk)return header('Hồ sơ đã đóng dấu',esc(t.title),'KẾT QUẢ HỒ SƠ')+`<div class="sheet-body">${L.desk.use()?L.desk.m.deskDone(t,env()):skeleton()}${ways}${fold}</div>`;
    return header('Một việc đã được làm tới nơi',t.title,'THÀNH QUẢ HÔM NAY')+`<div class="sheet-body center done-body"><div class="celebration">${icon('sparkle',55)}</div><h2>Cảm ơn bạn đã giúp!</h2>${ways}${fold}</div>`;
  }
  ui.task=t.id;let inner;
  if(careerUI(career()))inner=careerUI(career()).job(t,careerContext(env()));else if(['teacher','tour_guide','milk_tea'].includes(career()))inner=extendedJob(t,c,api.content,ui,api.state);else if(t.desk)inner=L.desk.use()?L.desk.m.deskJob(t,env()):skeleton();else if(career()==='mother_baby')inner=motherBabyJob(t);else if(career()==='pharmacy')inner=pharmacyJob(t);else if(career()==='accounting')inner=accountingJob(t);
  // A workplace with its own workbench whose code or data part did not come (a weak network): a skeleton while it is
  // asked for again (ensureCareerUI), never the customer-care view, which read its task as a ticket and threw.
  else if(CAREER_MODULES.includes(career())){ensureCareerUI();inner=skeleton();}else inner=supportJob(t);
  return header(esc(t.title),taskNext(t),esc(meta().work).toUpperCase()+' · NGÀY '+t.day,headMenu(commandButton('Để lát nữa','defer',{task:t.id},'ghost')+button('Xem các việc khác','queue',{},'ghost')))+`<div class="sheet-body">${!c.open?closedBar():''}${['teacher','tour_guide','milk_tea'].includes(career())||plugin()||t.desk||careerUI(career())?'':guestRibbon(t,c,api.content)}${customerTaskBanner(t)}${inner}</div>`;
}
/* The done screen's "Việc giữa ca" fold remembers that the player opened it (for this task): its data-auto
 * markup is redrawn on every render, so the state lives here. */
document.addEventListener('toggle',e=>{const d=e.target;if(d?.matches?.('details.idle-fold'))ui.idleOpen=d.open?d.dataset.idleTask:ui.idleOpen===d.dataset.idleTask?null:ui.idleOpen;},true);
function motherBabyJob(t){const d=draft(t),tab=ui.jobTab;const step=`<nav class="step-strip" aria-label="Bước phục vụ">${[['shelf','Kệ hàng'],['pack','Gói quà'],['checkout','Thu ngân']].map(([id,l],i)=>`<button data-action="jobTab" data-tab="${id}" class="${tab===id?'active':''}"><span>${i+1}</span>${l}</button>`).join('')}</nav>`;
  let main='';if(tab==='pack'){
    const paper=api.content.papers.find(p=>p.id===d.paper),ribbon=api.content.ribbons.find(r=>r.id===d.ribbon);
    main=`<h3>Một món quà được chăm chút</h3><div class="wrap-layout"><div class="gift-preview"><div class="gift-box" style="--paper-color:${paper.color};--ribbon-color:${ribbon.color}"><div class="gift-bow"></div></div></div><div><label class="field">Giấy gói</label><div class="swatches">${api.content.papers.map(p=>`<button class="swatch ${p.id===d.paper?'selected':''}" data-action="paper" data-value="${p.id}"><i style="background:${p.color}"></i>${p.name}</button>`).join('')}</div><label class="field">Chiếc nơ</label><div class="swatches">${api.content.ribbons.map(r=>`<button class="swatch ${r.id===d.ribbon?'selected':''}" data-action="ribbon" data-value="${r.id}"><i style="background:${r.color}"></i>${r.name}</button>`).join('')}</div><label class="field">Lời chúc<input class="input" id="gift-card" maxlength="100" data-draft="card" value="${esc(d.card)}"></label></div></div><div class="row wrap space-top">${button(icon('gift',16)+' Gói món quà này','pack',{},'primary')}${button('Sang thu ngân '+icon('arrow',14),'jobTab',{tab:'checkout'},'ghost')}</div><p class="small-note space-top">Vật liệu gói: 5 xu khi giao hàng. Đổi mẫu trước khi giao không mất phí.</p>${t.pack?notice('Đã lưu mẫu gói '+esc(api.content.papers.find(p=>p.id===t.pack.paper).name)+'.'):''}`;
  }else if(tab==='checkout'){
    const total=Object.entries(t.basket).reduce((sum,[id,q])=>sum+(room().life.prices[id]||product(id).price)*q,0);main=`<h3>Mọi điều nhỏ đều đúng chứ?</h3><div class="verify-list"><div class="row spread"><span>Tiền hàng theo giỏ</span><strong>${fmt(total)} xu</strong></div><div class="row spread"><span>Mẫu gói đang chọn</span><strong>${t.pack?esc(api.content.papers.find(p=>p.id===t.pack.paper).name):'Chưa gói'}</strong></div><div class="row spread"><span>Vật liệu gói</span><strong>${t.pack?'5':'0'} xu</strong></div></div>${t.checked?notice('Giỏ đã được đối chiếu.'):notice('Chưa kiểm xong.','amber','clipboard')}<div class="row wrap space-top">${commandButton(icon('check',15)+' Kiểm đơn','shop_check',{task:t.id},'ghost')}${button(icon('bag',15)+' Thanh toán & giao','deliverMB',{},'primary')}</div>${room().upgrades.includes('workbench')&&t.known?notice('Bàn kiểm hai bước: so '+t.needs.qty+' món mã '+esc(t.needs.product)+' với giỏ; sau đó xem màu giấy khách đã chọn.','blue','search'):''}`;
  }else main=`<div class="row spread"><div><h3>Chọn một món thật hợp</h3></div>${pill('8 món nhỏ')}</div><div class="product-grid">${api.content.products.map(p=>`<article class="product-card"><div class="art">${itemArt(p.icon,78,p.color)}</div><div class="product-info"><h4>${esc(p.name)}</h4><div class="row spread"><span class="price">${p.price} xu</span><span class="stock">Còn ${room().available[p.id]}</span></div>${commandButton(icon('plus',12)+' Thêm vào giỏ','shop_pick',{task:t.id,item:p.id},'small',!t.known||room().available[p.id]<1||!room().open)}</div></article>`).join('')}</div><div class="row space-top">${button('Tới bàn gói '+icon('arrow',14),'jobTab',{tab:'pack'},'primary')}${button('Không gói · thu ngân','jobTab',{tab:'checkout'},'ghost')}</div>`;
  return `<div class="work-layout"><div class="work-main">${step}${main}</div>${customerAside(t)}</div>`;
}
/* ---- Desk work screens: pharmacy counter, bookkeeping board, support desk (classic tasks).
   Render + client UI state only (ui.docs, ui.transactions, ui.phFilter, ui.jobTab, draft checks);
   the server checks every command again. Styles: css/desks.css, scoped under .career-job.dw. ---- */
const pct=v=>Math.max(0,Math.min(100,Math.round(Number(v)||0)));
const dwState=(label,tone='')=>`<span class="dw-state${tone?' '+tone:''}">${label}</span>`;
/** Who is waiting: portrait, name, one context line, patience and a chat button (replaces the guest ribbon).
 * Clean layout (pharmacy, accounting; UI wave 5): `sub` may be '', `quote:false` sends the opening to "?" (ui-kit tip),
 * `extra` sits before the chat button (an in-flow chip row, the "?"). Defaults draw it as before (the support desk). */
function dwWho(t,sub,{quote=true,extra=''}={}){
  const n=npc(t.npc),p=room().life?.mode==='calm'?100:pct(t.patience??100);
  return `<header class="dw-who">${portrait(n,48)}<div class="dw-who-name"><strong>${esc(n.display_name)}</strong>${sub?`<small>${sub}</small>`:''}`+
    `<div class="dw-pat${p<50?' low':p<75?' mid':''}" role="meter" aria-label="Kiên nhẫn" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${p}"><i><b style="width:${p}%"></b></i><small>${uiClean()?'':'Kiên nhẫn '}${p}%</small></div></div>${extra}`+
    `<button type="button" class="btn ghost icon-btn dw-talk" data-action="chat" data-npc="${esc(t.npc)}" data-task="${esc(t.id)}" aria-label="Trò chuyện với ${esc(n.display_name)}">${icon('chat',20)}</button></header>`+
    (quote?`<p class="dw-quote">${esc(t.opening)}</p>`:uiTip(esc(t.opening),`${esc(n.display_name)} nói`,'p'));
}
/** The desks' "?" on the clean layout: what the screen folded away (tips), then how the desk works. */
const DESK_HOW={pharmacy:['Hỏi lại phiếu để biết mã và số lượng.','Chọn mã trong bộ lọc, đọc nhãn: chỉ lô hợp lệ, không tạm giữ, mới được xuất. Màu hộp không cho biết lô có được xuất.','Lấy đúng lượng, tự kiểm mã · số lượng · lô, rồi kiểm khay.','Bàn giao; hoặc chuyển cô Thu khi phiếu ngoài phạm vi (liều dùng, triệu chứng, hộp thay thế).'],
  accounting:['Mở từng bản gốc, đọc mã tham chiếu (HD).','Bản sao cùng nguồn: loại trùng. Số lệch gốc: sửa theo bản gốc.','Chọn chứng từ và giao dịch cùng mã HD, tổng bằng nhau: ghép nhóm (nhiều-một hoặc một-nhiều).','Mọi thẻ đã ghép hoặc loại trùng: kiểm & bàn giao (thù lao 70 xu).']};
const deskQ=id=>helpBtn('desk-'+id,id==='pharmacy'?'💊 Quầy thuốc':'📒 Bàn đối chiếu',[{title:'Cách làm',body:`<ol>${DESK_HOW[id].map(s=>`<li>${esc(s)}</li>`).join('')}</ol>`}],{tips:true,cls:'dw-q'});
/** Sticky bar above the sheet footer: what is going on + at most one main action. */
const dwBar=(text,btns='')=>`<div class="dw-bar"><div class="dw-bar-text" aria-live="polite">${text}</div>${btns?`<div class="dw-bar-btns">${btns}</div>`:''}</div>`;

const LOT_STATE={unread:['Chưa đọc',''],available:['Hợp lệ','green'],held:['Tạm giữ','amber'],expired:['Hết hiệu lực','danger'],pull:['Có hộp cần rút','amber']};
/** Pharmacy slip, step by step (guide.js): ask, read the labels, take valid boxes, self-check, hand over.
 * The first slip's bottom button does each step; from the next one on, the steps that are the player's own
 * (reading the labels, choosing a valid lot, the self-check) only point at where to tap (👆, guide.js). */
function pharmacySteps(t){
  const c=room(),n=t.known?t.needs:null,first=firstTime({room:c});
  if(!t.known)return [{ok:null,label:'Hỏi rõ phiếu',go:{cmd:'ask',payload:{task:t.id},label:'💬 Hỏi rõ phiếu'}}];
  if(n.referral)return [{ok:null,label:'Yêu cầu ngoài phiếu: chuyển cô Thu',go:{act:'referPH',label:'Chuyển cô Thu →'}}];
  const care=careData(),pull=id=>(care?.batches||[]).some(b=>b.lot===id&&b.flag);
  const lots=api.content.lots.filter(l=>l.product===n.product),tray=Object.entries(t.basket||{}),count=tray.reduce((a,[,q])=>a+q,0);
  const valid=id=>{const l=api.content.lots.find(x=>x.id===id);return !!l&&l.product===n.product&&t.inspected.includes(id)&&l.status==='available'&&!c.held_lots.includes(id)&&!pull(id);};
  const unread=lots.filter(l=>!t.inspected.includes(l.id)),bad=tray.find(([id])=>!valid(id));
  const good=lots.find(l=>valid(l.id)&&(c.available?.[l.id]??0)>(t.basket?.[l.id]||0));
  const rows=[{ok:!unread.length||null,label:`Đọc nhãn các lô ${n.product}`,note:`${lots.length-unread.length}/${lots.length}`,go:!unread[0]?null:first?{cmd:'ph_inspect',payload:{task:t.id,lot:unread[0].id},label:`👁️ Đọc nhãn lô ${esc(unread[0].id)}`}:{sel:'.dw-lotgroup.want .dw-lot.unread',label:'👁️ Đọc nhãn từng lô'}}];
  if(bad)rows.push({ok:false,label:`Bỏ hộp ${bad[0]} ra khỏi khay`,go:first?{cmd:'basket_remove',payload:{task:t.id,item:bad[0]},label:`➖ Bỏ một hộp ${esc(bad[0])}`}:{sel:'.dw-traylist',label:'➖ Bỏ hộp không xuất được'}});
  rows.push({ok:!bad&&count===n.qty||null,label:`Lấy đủ ${n.qty} hộp ${n.product} từ lô hợp lệ`,note:`${count}/${n.qty}`,
    go:count>n.qty&&tray[0]?(first?{cmd:'basket_remove',payload:{task:t.id,item:tray[0][0]},label:`➖ Bỏ bớt một hộp`}:{sel:'.dw-traylist',label:'➖ Bỏ bớt một hộp'})
      :count<n.qty&&good?(first?{cmd:'ph_pick',payload:{task:t.id,item:good.id},label:`➕ Lấy 1 hộp lô ${esc(good.id)}`}:{sel:'.dw-lotgroup.want .dw-lotlist',label:'➕ Lấy hộp từ lô hợp lệ'})
      :count<n.qty&&!unread.length?(first?{act:'referPH',label:'Không lô nào xuất được: chuyển cô Thu'}:{sel:'.dw-refer',label:'Không lô nào xuất được: chuyển cô Thu'}):null});
  const d=draft(t).checks;
  rows.push({ok:['code','quantity','lot'].every(k=>d.includes(k))||t.checked||null,label:'Tự kiểm khay: mã, số lượng, lô',go:first?{act:'phTickAll',label:'☑️ Đã so mã, số lượng, lô'}:{sel:'.dw-checks',label:'☑️ Tự so mã, số lượng, lô'}});
  rows.push({ok:t.checked||null,label:'Kiểm khay',go:{act:'verifyPH',label:'✓ Kiểm khay'}});
  return rows;
}
/** ph_check as the server would answer it: its own pre-check (can.ph_check, game/desk_can.py ph_ready) first, then the
 * three ticks the page sends, in the command's order. True when the check would go. */
function phCan(t){
  const s=t.can?.ph_check;if(s&&s!==true)return s;
  const d=draft(t).checks;
  return ['code','quantity','lot'].every(k=>d.includes(k))?true:{why:'Cần xác nhận đủ mã, số lượng và trạng thái lô.',fix:{sel:'.dw-checks',label:'☑️ Tự kiểm khay'}};
}
/** The pharmacy counter on the clean layout (UI wave 5, docs/UI_KIT.md). Kept in sight: the customer's words until the
 * slip is read, the slip's code × count, every lot's state (Hợp lệ / Tạm giữ / Hết hiệu lực / Cần rút), its stock and
 * use-by day, the tray against the slip. To "?": the rules (only valid lots, the colour says nothing), the opening once
 * the slip is read, the refer hint. The counter's to-dos fold into one chip by the customer. One main button. */
function pharmacyClean(t){
  const c=room(),d=draft(t),n=t.known?t.needs:null,refer=!!n?.referral,want=n&&!refer?n.product:'',f=ui.phFilter==='all'?'':(ui.phFilter||want);
  const lotOf=id=>api.content.lots.find(l=>l.id===id),tray=Object.entries(t.basket||{}),count=tray.reduce((a,[,q])=>a+q,0);
  const codes=[...new Set(tray.map(([id])=>lotOf(id)?.product||id))],name=id=>api.content.ph_products.find(p=>p.id===id)?.name||'';
  const care=careData(),pull=id=>(care?.batches||[]).some(b=>b.lot===id&&b.flag),use=id=>(care?.batches||[]).find(b=>b.lot===id&&!b.flag);
  const state=l=>!t.inspected.includes(l.id)?'unread':c.held_lots.includes(l.id)?'held':l.status==='available'&&pull(l.id)?'pull':l.status;
  const aria=(html,label)=>html.replace('<button ',`<button aria-label="${esc(label)}" `);
  // The counter's to-dos (the fridge log, regulars due, a shelf to pull): one chip, the first one's icon and its time.
  const alerts=care?.alerts||[],first=String(alerts[0]||''),time=(first.match(/\d{1,2}:\d{2}/)||[])[0]||'';
  const chip=alerts.length?`<span class="ui-chiprow dw-chiprow">${headChip([...first][0]||'⚠️',time||String(alerts.length),'.dw-ph .cb-strip',{label:alerts.join(' · '),flow:true})}</span>`:'';
  const today=alerts.length?`<section class="cb-strip ui-chipped" aria-label="Việc quầy hôm nay"><ul>${alerts.map(a=>`<li>${esc(a)}</li>`).join('')}</ul>${openBoard('Kho & sổ quầy',alerts.some(a=>a.startsWith('💊')||a.startsWith('📞'))?'regulars':'lots')}</section>`:'';
  const who=dwWho(t,'',{quote:!t.known,extra:chip+deskQ('pharmacy')});
  const slip=!t.known?'':refer?`<section class="dw-slip refer" aria-label="Phiếu lấy hàng: ngoài phạm vi"><p class="dw-slip-miss">📋 Ngoài phiếu</p>${uiTip('Yêu cầu nằm ngoài phiếu. Không lấy hộp thay thế: chuyển cô Thu.','📋 Phiếu','p')}</section>`
    :`<section class="dw-slip dw-slip-c" aria-label="${esc(`Phiếu: mã ${n.product} ${name(n.product)}, ${n.qty} hộp`)}"><b class="dw-slip-code" title="${esc(name(n.product))}">📋 ${esc(n.product)}</b><b class="dw-slip-qty">× ${n.qty}</b>${uiTip('Chỉ lô hợp lệ, không tạm giữ.','📋 Phiếu','p')}</section>`;
  const lotRow=l=>{const s=state(l),[label,tone]=s==='pull'?['Cần rút','amber']:LOT_STATE[s]||LOT_STATE.expired,left=c.available?.[l.id];
    const meta=s==='unread'?'':`<small aria-label="${esc(`Còn ${fmt(left)} hộp`)}">📦 ${fmt(left)}${s==='available'&&use(l.id)?` · HSD ${use(l.id).exp}`:''}</small>`;
    const act=s==='unread'?aria(commandButton(icon('eye',15)+' Đọc','ph_inspect',{task:t.id,lot:l.id},'ghost'),'Đọc nhãn '+l.id)
      :s==='available'?(!(left>0)?button('📦 Nhập','warehouse',{},'small ghost'):aria(commandButton(icon('plus',15)+' 1','ph_pick',{task:t.id,item:l.id},'',!c.open),'Lấy 1 hộp '+l.id))
      :s==='pull'?openBoard('Sổ lô','lots'):'';
    return `<li class="dw-lot ${s}">${itemArt('box',36,l.color)}<div class="dw-lot-id"><b>${esc(l.id)}</b>${s==='unread'?'':dwState(label,tone)}${meta}</div><div class="dw-lot-act">${act}</div></li>`;};
  const lots=t.known&&!refer?`<section class="dw-sec dw-lots" aria-label="Kệ lô hàng"><div class="dw-sec-head"><label class="dw-filter"><select id="ph-filter" aria-label="Xem mã hộp" data-action-change="ph-filter"><option value="all">Tất cả</option>${api.content.ph_products.map(p=>`<option value="${p.id}"${f===p.id?' selected':''}>${p.id}${p.id===want?' 📋':''}</option>`).join('')}</select></label>${uiTip('Màu hộp không cho biết lô có được xuất.','Kệ lô hàng')}</div>`+
    api.content.ph_products.filter(p=>!f||p.id===f).map(p=>`<div class="dw-lotgroup${p.id===want?' want':''}">${f?'':`<h4><b>${p.id}</b> ${esc(p.name)}</h4>`}<ul class="dw-lotlist">${api.content.lots.filter(l=>l.product===p.id).map(lotRow).join('')}</ul></div>`).join('')+`</section>`:'';
  // The self-check: three ticks in one row (the slip and the tray it compares sit right above); the full sentence and
  // the pair it compares are the label for screen readers.
  const ticks=n&&!refer?[['code','Mã',`Mã hộp khớp phiếu: phiếu ${want}, khay ${codes.join(', ')||'trống'}`],['quantity','Số lượng',`Số lượng đúng phiếu: phiếu ${n.qty}, khay ${count}`],['lot','Lô',`Lô đã đọc nhãn, được xuất: ${tray.map(([id])=>id).join(', ')||'trống'}`]]:[];
  const trayBox=count&&!refer?`<section class="dw-sec dw-tray" aria-label="Khay"><div class="dw-sec-head"><h3>🧺 Khay</h3><span class="dw-count${count===n.qty?' ok':''}">${count}/${n.qty}</span></div>`+
    `<ul class="dw-traylist">${tray.map(([id,q])=>{const l=lotOf(id);return `<li>${itemArt('box',32,l?.color)}<span><b>${esc(id)} × ${q}</b></span><button type="button" class="btn ghost icon-btn" aria-label="Bỏ một hộp ${esc(id)}" data-command="basket_remove" data-payload="${esc(JSON.stringify({task:t.id,item:id}))}">${icon('minus',16)}</button></li>`;}).join('')}</ul>`+
    (t.checked?'<p class="dw-ok">✓ Đã kiểm</p>':`<div class="dw-checks dw-checks-c" role="group" aria-label="Tự kiểm khay">${ticks.map(([k,l,full])=>`<label class="dw-tick" aria-label="${esc(full)}"><input type="checkbox" data-phcheck="${k}"${d.checks.includes(k)?' checked':''}><span><b>${l}</b></span></label>`).join('')}</div>`)+`</section>`:'';
  const referBox=t.known&&!refer?`<section class="dw-refer" aria-label="Chuyển người phụ trách">${uiTip('Hỏi liều dùng, triệu chứng hay hộp thay thế: chuyển cô Thu, không tự đoán.','Chuyển cô Thu','p')}${aria(button('↪️ Cô Thu','referPH',{},'ghost'),'Chuyển cô Thu')}</section>`:'';
  const steps=pharmacySteps(t).map(s=>s.go?.act==='phTickAll'?{...s,go:{...s.go,label:'☑️ Đã so đủ 3'}}:s),hint=nextHint({room:c},steps,{final:t.checked?{label:'Bàn giao phiếu',go:{act:'deliverPH'}}:null});
  let {next,main}=barParts({room:c},steps,{label:'Bàn giao '+icon('arrow',15),go:{act:'deliverPH'},ready:!!t.checked});
  if(/data-action="verifyPH"/.test(main))main=withWhy(main,phCan(t));
  const note=want?`<span class="ui-note" aria-label="${esc(`Khay ${count} trên ${n.qty} hộp`)}">🧺 ${count}/${n.qty}</span>`:'';
  return `<div class="career-job dw dw-ph">${hint}${who}${today}<div class="dw-ph-grid">${slip}${lots}${trayBox}${referBox}</div>${actBar({next:next||note,main,cls:'dw-bar'})}</div>`;
}
function pharmacyJob(t){
  if(uiClean())return pharmacyClean(t);
  const c=room(),d=draft(t),n=t.known?t.needs:null,refer=!!n?.referral,want=n&&!refer?n.product:'',f=ui.phFilter==='all'?'':(ui.phFilter||want);
  const lotOf=id=>api.content.lots.find(l=>l.id===id),tray=Object.entries(t.basket||{}),count=tray.reduce((a,[,q])=>a+q,0);
  const codes=[...new Set(tray.map(([id])=>lotOf(id)?.product||id))],name=id=>api.content.ph_products.find(p=>p.id===id)?.name||'';
  const care=careData(),pull=id=>(care?.batches||[]).some(b=>b.lot===id&&b.flag),use=id=>(care?.batches||[]).find(b=>b.lot===id&&!b.flag);
  const state=l=>!t.inspected.includes(l.id)?'unread':c.held_lots.includes(l.id)?'held':l.status==='available'&&pull(l.id)?'pull':l.status;
  const slip=!t.known?`<section class="dw-slip unknown" aria-label="Phiếu lấy hàng"><span class="dw-eyebrow">📋 Phiếu lấy hàng</span><p class="dw-slip-miss">Phiếu chưa đủ thông tin.</p>${commandButton('💬 Hỏi rõ phiếu','ask',{task:t.id},'primary')}</section>`
    :refer?`<section class="dw-slip refer" aria-label="Phiếu lấy hàng"><span class="dw-eyebrow">📋 Phiếu lấy hàng</span><p class="dw-slip-miss">Yêu cầu nằm ngoài phiếu.</p><p class="dw-hint">Không lấy hộp thay thế.</p>${button('Chuyển cô Thu '+icon('arrow',15),'referPH',{},'primary')}</section>`
    :`<section class="dw-slip" aria-label="Phiếu lấy hàng"><span class="dw-eyebrow">📋 Phiếu lấy hàng</span><dl class="dw-slip-grid"><div><dt>Mã hộp</dt><dd>${esc(n.product)}<small>${esc(name(n.product))}</small></dd></div><div><dt>Số lượng</dt><dd>${n.qty} hộp</dd></div><div class="wide"><dt>Ghi chú</dt><dd>Chỉ lô hợp lệ, không tạm giữ.</dd></div></dl></section>`;
  const lotRow=l=>{const s=state(l),[label,tone]=LOT_STATE[s]||LOT_STATE.expired;
    return `<li class="dw-lot ${s}">${itemArt('box',36,l.color)}<div class="dw-lot-id"><b>${esc(l.id)}</b>${dwState(label,tone)}${s!=='unread'?`<small>Còn ${fmt(c.available?.[l.id])} hộp${s==='available'&&use(l.id)?` · HSD ngày ${use(l.id).exp}`:''}</small>`:''}</div><div class="dw-lot-act">${s==='unread'?commandButton(icon('eye',15)+' Đọc nhãn','ph_inspect',{task:t.id,lot:l.id},'ghost'):s==='available'?(!(c.available?.[l.id]>0)&&t.known&&!refer?button('📦 Hết · nhập hàng','warehouse',{},'small ghost'):commandButton(icon('plus',15)+' Lấy 1','ph_pick',{task:t.id,item:l.id},'',!t.known||refer||!c.open)):s==='pull'?openBoard('Sổ lô','lots'):''}</div></li>`;};
  const lots=`<section class="dw-sec dw-lots" aria-label="Kệ lô hàng"><div class="dw-sec-head"><h3>Kệ lô hàng</h3><label class="dw-filter"><span>Xem mã</span><select id="ph-filter" aria-label="Chọn mã hộp" data-action-change="ph-filter"><option value="all">Tất cả mã</option>${api.content.ph_products.map(p=>`<option value="${p.id}"${f===p.id?' selected':''}>${p.id}${p.id===want?' · trên phiếu':''}</option>`).join('')}</select></label></div><p class="dw-hint">Màu hộp không cho biết lô có được xuất.</p>`+
    api.content.ph_products.filter(p=>!f||p.id===f).map(p=>`<div class="dw-lotgroup${p.id===want?' want':''}"><h4><b>${p.id}</b> ${esc(p.name)}${p.id===want?dwState('Mã trên phiếu','blue'):''}</h4><ul class="dw-lotlist">${api.content.lots.filter(l=>l.product===p.id).map(lotRow).join('')}</ul></div>`).join('')+`</section>`;
  const facts={code:`Phiếu ${want||'—'} · khay ${codes.join(', ')||'—'}`,quantity:`Phiếu ${n&&!refer?n.qty:'—'} · khay ${count}`,lot:tray.length?'Khay: '+tray.map(([id])=>id).join(', '):'Khay chưa có lô'};
  const trayBox=`<section class="dw-sec dw-tray" aria-label="Khay kiểm hai bước"><div class="dw-sec-head"><h3>Khay đang giữ</h3><span class="dw-count${want&&count===n.qty?' ok':''}">${count}${want?'/'+n.qty:''} hộp</span></div>`+
    (tray.length?`<ul class="dw-traylist">${tray.map(([id,q])=>{const l=lotOf(id);return `<li>${itemArt('box',32,l?.color)}<span><b>${esc(id)} × ${q}</b><small>${esc(l?.name||'')}</small></span><button type="button" class="btn ghost icon-btn" aria-label="Bỏ một hộp ${esc(id)}" data-command="basket_remove" data-payload="${esc(JSON.stringify({task:t.id,item:id}))}">${icon('minus',16)}</button></li>`;}).join('')}</ul>`:`<p class="dw-empty">Khay còn trống.</p>`)+
    `<h4 class="dw-step-title">Bước 1 · Tự kiểm khay</h4><div class="dw-checks">${[['code','Mã hộp khớp phiếu'],['quantity','Số lượng đúng phiếu'],['lot','Lô đã đọc nhãn, được xuất']].map(([k,l])=>`<label class="dw-tick"><input type="checkbox" data-phcheck="${k}"${d.checks.includes(k)?' checked':''}><span><b>${l}</b><small>${esc(facts[k])}</small></span></label>`).join('')}</div>`+
    `${withWhy(button(icon('check',16)+' Kiểm khay','verifyPH',{},t.checked?'ghost':want&&count===n.qty?'primary':''),t.checked||phCan(t))}${t.checked?'<p class="dw-ok">✓ Đã kiểm đủ ba bước.</p>':''}`+
    `<h4 class="dw-step-title">Bước 2 · Bàn giao</h4><button type="button" class="btn ${t.checked?'primary':''}" data-action="deliverPH"${t.checked?'':' disabled'}>Bàn giao phiếu ${icon('arrow',15)}</button></section>`;
  const referBox=t.known&&!refer?`<section class="dw-refer" aria-label="Chuyển người phụ trách"><div><b>Phiếu có điều ngoài phạm vi?</b><p class="dw-hint">Hỏi liều dùng, triệu chứng hay hộp thay thế: chuyển cô Thu, không tự đoán.</p></div>${button('Chuyển cô Thu','referPH',{},'ghost')}</section>`:'';
  const barText=!t.known?'Hỏi rõ phiếu trước khi lấy hàng.':`Phiếu <b>${esc(want)} × ${n.qty}</b> · Khay <b>${count}/${n.qty}</b>${t.checked?' · đã kiểm':count<n.qty?' · lấy thêm':count>n.qty?' · thừa hộp':' · tự kiểm khay'}`;
  // A slip that must be referred has nothing to pick: only the slip and its one action.
  const today=care?.alerts?.length?`<section class="cb-strip" aria-label="Việc quầy hôm nay"><ul>${care.alerts.map(a=>`<li>${esc(a)}</li>`).join('')}</ul>${openBoard('Kho & sổ quầy',care.alerts.some(a=>a.startsWith('💊')||a.startsWith('📞'))?'regulars':'lots')}</section>`:'';
  const steps=pharmacySteps(t),hint=nextHint({room:c},steps,{final:t.checked?{label:'Bàn giao phiếu',go:{act:'deliverPH'}}:null});
  if(refer)return `<div class="career-job dw dw-ph">${hint}${dwWho(t,'Phiếu đã rõ')}${slip}${today}</div>`;
  return `<div class="career-job dw dw-ph">${hint}${dwWho(t,t.known?'Phiếu đã rõ':'Phiếu chưa rõ')}${today}<div class="dw-ph-grid">${slip}${lots}${trayBox}${referBox}</div>${dwBar(barText,stepCta({room:c},steps,{label:'Bàn giao '+icon('arrow',15),go:{act:'deliverPH'},ready:!!t.checked},{style:'primary'}))}</div>`;
}

/** Bookkeeping board, step by step (guide.js): open every original, fix what differs, get the
 * missing source, then match documents and transactions that carry the same HD code. */
function acGroup(t){
  const inG=(k,id)=>t.groups.some(g=>g[k].includes(id)),free=d=>!t.removed.includes(d.id)&&!inG('docs',d.id)&&!d.missing;
  const tx=t.transactions.find(x=>!inG('transactions',x.id));if(!tx)return null;
  const key=x=>[...x.refs].sort().join('|'),txs=t.transactions.filter(x=>!inG('transactions',x.id)&&key(x)===key(tx));
  const docs=t.docs.filter(d=>free(d)&&tx.refs.includes(d.ref)),want=txs.reduce((s,x)=>s+x.amount,0),have=docs.reduce((s,d)=>s+d.amount,0);
  // Same code, same amount, counted twice: the later card is the copy.
  const twin=have!==want?docs.find((d,i)=>docs.some((e,j)=>j<i&&e.ref===d.ref&&e.amount===d.amount)):null;
  return {tx,txs,docs,twin,refs:tx.refs};
}
function accountingSteps(t){
  const inG=(k,id)=>t.groups.some(g=>g[k].includes(id));
  const unread=t.docs.filter(d=>!t.inspected.includes(d.id)&&!d.missing&&!t.removed.includes(d.id)&&!inG('docs',d.id));
  const off=t.docs.find(d=>t.inspected.includes(d.id)&&d.original!==undefined&&d.original!==d.amount&&!t.removed.includes(d.id)&&!inG('docs',d.id));
  const miss=t.docs.find(d=>d.missing);
  const rows=[{ok:!unread.length||null,label:'Mở bản gốc từng chứng từ',note:`${t.docs.length-unread.length}/${t.docs.length}`,go:unread[0]?{cmd:'ac_inspect',payload:{task:t.id,doc:unread[0].id},label:`👁️ Mở gốc ${esc(unread[0].id)}`}:null}];
  if(off)rows.push({ok:false,label:`Sửa ${off.id} theo bản gốc`,go:{cmd:'ac_correct',payload:{task:t.id,doc:off.id},label:`✏️ Sửa ${esc(off.id)} theo gốc`}});
  if(miss)rows.push({ok:null,label:'Xin nguồn cho phiếu còn thiếu',go:!t.source_requested?{cmd:'ac_request_source',payload:{task:t.id},label:'📨 Xin nguồn bổ sung'}:(!t.source_at||sameDay(t.source_at))?{cmd:'advance',label:'⏳ Chờ thêm 20 phút'}:null});
  const g=acGroup(t);
  if(g){
    const picked=g.docs.length&&g.docs.every(d=>ui.docs.has(d.id))&&ui.docs.size===g.docs.length&&g.txs.every(x=>ui.transactions.has(x.id))&&ui.transactions.size===g.txs.length;
    rows.push(g.twin?{ok:null,label:`${g.twin.id} trùng với một phiếu khác`,go:{cmd:'ac_duplicate',payload:{task:t.id,doc:g.twin.id},label:`🗂️ Đánh dấu ${esc(g.twin.id)} là bản trùng`}}
      :{ok:null,label:`Ghép các thẻ mã ${g.refs.join(' + ')}`,go:picked?{act:'match',label:'🔗 Ghép nhóm'}:{act:'acPick',data:{tx:g.tx.id},label:`👉 Chọn các thẻ mã ${esc(g.refs.join(' + '))}`}});
  }
  return rows;
}
/** “Đánh dấu trùng” as engine ac_duplicate checks it: only a copy (its source names the original, shown once read)
 * whose original is read too; otherwise drawn disabled with the reason. */
function dupButton(t,d){
  if(d.duplicate_of&&t.inspected.includes(d.duplicate_of))return commandButton('Đánh dấu trùng','ac_duplicate',{task:t.id,doc:d.id},'ghost');
  return d.duplicate_of?commandButton('Mở cả hai bản gốc trước','ac_duplicate',{task:t.id,doc:d.id},'ghost',true)
    :commandButton('Đánh dấu trùng','ac_duplicate',{task:t.id,doc:d.id},'ghost',true).replace('<button ','<button title="Chỉ bản sao cùng nguồn mới loại trùng" ');
}
/** Why engine ac_match would refuse the picked cards before even adding them up ('' when it would not). */
function matchBlock(t,ds){
  return ds.some(d=>!t.inspected.includes(d.id))?'Đọc đủ bản gốc trước':ds.some(d=>d.missing)?'Thẻ thiếu nguồn chưa ghép được':ds.some(d=>d.duplicate_of)?'Loại bản trùng trước'
    :ds.some(d=>d.original!==undefined&&d.original!==d.amount)?'Sửa theo gốc trước':'';
}
/** ac_match as the server would answer the picked cards, in its order (game/desk_can.py ac_match_rules): the pick's
 * shape, then each card's own state (the server's can.ac_match, one entry per card that cannot go yet), then the sums
 * and the HD codes. True when the group would go. */
function acMatchCan(t,selD,selT){
  if(!selD.length||!selT.length)return {why:'Chọn phiếu và giao dịch để ghép.',fix:{act:'jobTab',data:{tab:selD.length?'acTx':'acDocs'},label:selD.length?'Chọn giao dịch →':'← Chọn chứng từ'}};
  if(selD.length>1&&selT.length>1)return {why:'Ghép theo từng quan hệ nhiều-một hoặc một-nhiều, không gộp cả hồ sơ.',fix:{act:'clearSelection',label:'Bỏ chọn'}};
  const cards=t.can?.ac_match||{},bad=selD.find(d=>cards[d.id]);if(bad)return cards[bad.id];
  const a=selD.reduce((s,d)=>s+d.amount,0),b=selT.reduce((s,x)=>s+x.amount,0);
  if(a!==b)return {why:`Tổng phiếu ${a} xu chưa khớp giao dịch ${b} xu. Thử kiểm phần còn thiếu nhé.`};
  const r1=new Set(selD.map(d=>d.ref)),r2=new Set(selT.flatMap(x=>x.refs));
  if(r1.size!==r2.size||[...r1].some(r=>!r2.has(r)))return {why:'Tổng giống nhau nhưng tham chiếu nguồn chưa khớp. Kiểm mã hóa đơn nhé.'};
  return true;
}
/** The bookkeeping board on the clean layout (UI wave 5, docs/UI_KIT.md). Kept on every card: its code, amount and HD
 * code; once read, what it is (✓, Lệch gốc + the original amount, Bản sao + the card it copies, Thiếu nguồn, hoàn);
 * a transaction's codes. To "?": the opening (the same ask on every file), the transactions' notes, the hand-over
 * checklist and the work bench's rule. The sums of the picked cards and the one main button sit in the shared bar. */
/** The bar's step labels in a few words (clean layout): the card it acts on stays named. */
function acShort(s){
  const g=s.go;if(!g)return s;
  const doc=g.payload?.doc?esc(g.payload.doc):'';
  if(g.cmd==='ac_duplicate')return {...s,go:{...g,label:`🗂️ Loại trùng ${doc}`}};
  if(g.cmd==='ac_correct')return {...s,go:{...g,label:`✏️ Sửa ${doc}`}};
  if(g.act==='acPick')return {...s,go:{...g,label:String(g.label).replace('👉 Chọn các thẻ mã','👉 Chọn')}};
  return s;
}
function accountingClean(t){
  const inG=(k,id)=>t.groups.some(g=>g[k].includes(id)),sum=a=>a.reduce((s,x)=>s+x.amount,0);
  const selD=t.docs.filter(d=>ui.docs.has(d.id)),selT=t.transactions.filter(x=>ui.transactions.has(x.id)),ds=sum(selD),ts=sum(selT);
  const read=t.docs.filter(d=>t.inspected.includes(d.id)).length,settled=t.docs.filter(d=>t.removed.includes(d.id)||inG('docs',d.id)).length;
  const txDone=t.transactions.filter(x=>inG('transactions',x.id)).length,allDone=settled===t.docs.length&&txDone===t.transactions.length;
  const tab=ui.jobTab==='acTx'?'tx':'docs',can=t.can||{};
  const aria=(html,label)=>html.replace('<button ',`<button aria-label="${esc(label)}" `);
  const pick=(action,id,on,off,mark)=>`<button type="button" class="dw-pick${on?' on':''}" data-action="${action}" data-id="${esc(id)}" aria-pressed="${on}" aria-label="Chọn ${esc(id)}"${off?' disabled':''}>${on?icon('check',20):mark||''}</button>`;
  const docCard=d=>{
    const seen=t.inspected.includes(d.id),used=inG('docs',d.id),removed=t.removed.includes(d.id),sel=ui.docs.has(d.id),off=seen&&d.original!==undefined&&d.original!==d.amount,copy=seen&&d.duplicate_of;
    const [label,tone]=removed||used?['','']:d.missing?['Thiếu nguồn','amber']:!seen?['','']:off?['Lệch gốc','danger']:copy?[`Bản sao ${esc(d.duplicate_of)}`,'amber']:['✓','blue'];
    const both=copy&&t.inspected.includes(d.duplicate_of);
    const act=removed||used||d.missing?'':!seen?aria(commandButton(icon('eye',15)+' Mở','ac_inspect',{task:t.id,doc:d.id},'ghost'),'Mở bản gốc '+d.id)
      :off?aria(commandButton('✏️ Sửa','ac_correct',{task:t.id,doc:d.id},'ghost'),'Sửa theo gốc '+d.id)
      :copy?withWhy(aria(commandButton('🗂️ Loại trùng','ac_duplicate',{task:t.id,doc:d.id},'ghost'),'Đánh dấu trùng '+d.id),both||{why:'Cần đối chiếu cả hai bản có cùng nguồn; thẻ này chưa được chứng minh là bản sao.',fix:{cmd:'ac_inspect',payload:{task:t.id,doc:d.duplicate_of},label:'👁️ Mở gốc '+d.duplicate_of}}):'';
    const src=seen?`${off?`<small class="dw-orig">gốc ${fmt(d.original)}</small>`:''}${uiTip(`${esc(d.source)} · số gốc ${fmt(d.original)} xu`,esc(d.id))}`:'';
    return `<li class="dw-card${sel?' selected':''}${used||removed?' settled':''}">${pick('selectDoc',d.id,sel,used||removed,used?icon('link',18):removed?icon('minus',18):'')}<div class="dw-card-main"><div class="dw-line"><b class="dw-code">${esc(d.id)}</b><span class="dw-amt" aria-label="${esc(`${fmt(d.amount)} xu`)}">${fmt(d.amount)}</span><span class="dw-sub">${esc(d.ref)}${d.kind==='hoàn'?' · hoàn':''}</span>${label?dwState(label,tone):''}${src}${act}</div></div></li>`;};
  const txCard=x=>{const used=inG('transactions',x.id),sel=ui.transactions.has(x.id);
    return `<li class="dw-card tx${sel?' selected':''}${used?' settled':''}">${pick('selectTx',x.id,sel,used,used?icon('link',18):'')}<div class="dw-card-main"><div class="dw-line"><b class="dw-code">${esc(x.id)}</b><span class="dw-amt" aria-label="${esc(`${fmt(x.amount)} xu`)}">${fmt(x.amount)}</span><span class="dw-sub">${esc(x.refs.join(' + '))}</span></div>${uiTip(esc(x.note),esc(x.id))}</div></li>`;};
  // Tabs: the open tab keeps its word; both keep their count.
  const tabs=`<div class="dw-tabs" role="tablist" aria-label="Bàn đối chiếu">${[['docs','acDocs','📂','Chứng từ',t.docs.length-settled,selD.length],['tx','acTx','🔗','Giao dịch',t.transactions.length-txDone,selT.length]].map(([k,val,e,l,left,picked])=>`<button type="button" role="tab" aria-selected="${tab===k}" aria-label="${esc(`${l}: ${picked?`đã chọn ${picked}`:left?`còn ${left}`:'xong'}`)}" class="dw-tab${tab===k?' on':''}" data-action="jobTab" data-tab="${val}"><span><span aria-hidden="true">${e}</span>${tab===k?' '+l:''}</span><em>${picked?`✓ ${picked}`:left?left:'✓'}</em></button>`).join('')}</div>`;
  const board=`<div class="dw-board show-${tab}"><section class="dw-col docs" aria-label="Chứng từ"><h3 class="dw-col-title">📂 Chứng từ</h3><ul class="dw-cards">${t.docs.map(docCard).join('')}</ul></section><section class="dw-col tx" aria-label="Giao dịch"><h3 class="dw-col-title">🔗 Giao dịch</h3><ul class="dw-cards">${t.transactions.map(txCard).join('')}</ul></section></div>`;
  // A missing source: the promised time stays in sight; asking for it and waiting are the bar's steps.
  const later=t.source_at&&!sameDay(t.source_at);
  const missing=t.docs.some(d=>d.missing)?`<div class="dw-alert" role="status"><b>⏳ Thiếu nguồn</b>${t.source_requested&&t.source_at?`<span aria-label="${esc(`Người gửi hẹn gửi lúc ${hm(t.source_at)}${later?' sáng mai':' hôm nay'}`)}">📨 ${hm(t.source_at)}${later?' mai':''}</span>`:''}${later?button('Việc khác','queue',{},'ghost'):''}</div>`:'';
  const groups=t.groups.length?`<ul class="dw-groups" aria-label="Nhóm đã ghép: ${t.groups.length}">${t.groups.map((g,i)=>`<li><span><b>${esc(g.docs.join(' + '))} ↔ ${esc(g.transactions.join(' + '))}</b><small aria-label="${esc(`Khớp ${fmt(g.total)} xu`)}">= ${fmt(g.total)}</small></span>${commandButton('Tháo','ac_unmatch',{task:t.id,index:i},'ghost')}</li>`).join('')}</ul>`:'';
  const notes=`${uiTip('Thù lao 70 xu. Bàn giao khi mọi chứng từ đã ghép hoặc loại trùng và mọi giao dịch đã có nguồn.','Bàn giao hồ sơ','p')}${room().upgrades.includes('workbench')?uiTip('Bàn kiểm: tìm phiếu có cùng mã tham chiếu; không tính một nguồn hai lần. Kiểm tổng và tập mã đều phải khớp.','Bàn kiểm','p'):''}`;
  const both=selD.length&&selT.length,finish={label:icon('check',16)+' Bàn giao',go:{act:'completeAC'},ready:allDone,can:can.ac_complete};
  let next='',main='';
  if(selD.length||selT.length){
    next=`<span class="dw-sums" role="status"><span aria-label="${esc(`Chứng từ đã chọn: ${selD.length}, tổng ${ds} xu`)}">📂 <b>${fmt(ds)}</b></span><i class="${both?ds===ts?'ok':'bad':''}" aria-hidden="true">${both?ds===ts?'=':'≠':'⇄'}</i><span aria-label="${esc(`Giao dịch đã chọn: ${selT.length}, tổng ${ts} xu`)}">🔗 <b>${fmt(ts)}</b></span></span><button type="button" class="btn ghost icon-btn" data-action="clearSelection" aria-label="Bỏ chọn">${icon('x',18)}</button>`;
    main=both?withWhy(button(icon('link',16)+' Ghép nhóm','match',{},'primary big'),acMatchCan(t,selD,selT))
      :button(selD.length?'Chọn giao dịch →':'← Chọn chứng từ','jobTab',{tab:selD.length?'acTx':'acDocs'},'primary big');
  }else{
    ({next,main}=barParts({room:room()},allDone?[]:accountingSteps(t).map(acShort),finish));
    if(!next)next=`<span class="ui-note" aria-label="${esc(`Đã xử lý ${settled} trên ${t.docs.length} chứng từ`)}">📂 ${settled}/${t.docs.length}</span>`;
  }
  const hint=nextHint({room:room()},accountingSteps(t),{final:allDone?{label:'Kiểm & bàn giao hồ sơ',go:{act:'completeAC'}}:null,cta:false});
  return `<div class="career-job dw dw-ac">${hint}${dwWho(t,'',{quote:false,extra:deskQ('accounting')})}${missing}${tabs}${board}${groups}${notes}${actBar({next,main,cls:'dw-bar'})}</div>`;
}
function accountingJob(t){
  if(uiClean())return accountingClean(t);
  const inG=(k,id)=>t.groups.some(g=>g[k].includes(id)),sum=a=>a.reduce((s,x)=>s+x.amount,0);
  const selD=t.docs.filter(d=>ui.docs.has(d.id)),selT=t.transactions.filter(x=>ui.transactions.has(x.id)),ds=sum(selD),ts=sum(selT);
  const read=t.docs.filter(d=>t.inspected.includes(d.id)).length,settled=t.docs.filter(d=>t.removed.includes(d.id)||inG('docs',d.id)).length;
  const txDone=t.transactions.filter(x=>inG('transactions',x.id)).length,allDone=settled===t.docs.length&&txDone===t.transactions.length;
  const tab=ui.jobTab==='acTx'?'tx':'docs';
  const pick=(action,id,on,off,mark)=>`<button type="button" class="dw-pick${on?' on':''}" data-action="${action}" data-id="${esc(id)}" aria-pressed="${on}" aria-label="Chọn ${esc(id)}"${off?' disabled':''}>${on?icon('check',20):mark||''}</button>`;
  const docCard=d=>{
    const seen=t.inspected.includes(d.id),used=inG('docs',d.id),removed=t.removed.includes(d.id),sel=ui.docs.has(d.id),off=seen&&d.original!==undefined&&d.original!==d.amount;
    const [label,tone]=removed?['Đã loại trùng','']:used?['Đã ghép','green']:d.missing?['Thiếu nguồn','amber']:!seen?['Chưa đọc gốc','']:off?['Lệch gốc','danger']:['Đã đọc','blue'];
    const act=removed||used||d.missing?'':!seen?commandButton(icon('eye',15)+' Mở gốc','ac_inspect',{task:t.id,doc:d.id},'ghost'):off?commandButton('Sửa theo gốc','ac_correct',{task:t.id,doc:d.id},'ghost'):dupButton(t,d);
    const src=seen?`<p>${esc(d.source)}</p><p>Số gốc: <b>${fmt(d.original)} xu</b>${off?` · đang ghi ${fmt(d.amount)} xu`:''}</p>`:d.missing?'<p>Nguồn chưa được gửi. Xin người gửi bổ sung.</p>':'<p>Chưa mở.</p>';
    return `<li class="dw-card${sel?' selected':''}${used||removed?' settled':''}">${pick('selectDoc',d.id,sel,used||removed,used?icon('link',18):removed?icon('minus',18):'')}<div class="dw-card-main"><div class="dw-line"><b class="dw-code">${esc(d.id)}</b><span class="dw-amt">${fmt(d.amount)} xu</span>${dwState(label,tone)}</div><div class="dw-row2">${fold(`<b class="dw-sub">${esc(d.ref)}</b>${d.kind==='hoàn'?' · khoản hoàn':''}`,src)}${act}</div></div></li>`;};
  const txCard=x=>{const used=inG('transactions',x.id),sel=ui.transactions.has(x.id);
    return `<li class="dw-card tx${sel?' selected':''}${used?' settled':''}">${pick('selectTx',x.id,sel,used,used?icon('link',18):'')}<div class="dw-card-main"><div class="dw-line"><b class="dw-code">${esc(x.id)}</b><span class="dw-amt">${fmt(x.amount)} xu</span>${used?dwState('Đã ghép','green'):''}</div><div class="dw-sub">${esc(x.refs.join(' + '))}</div><p class="dw-note">${esc(x.note)}</p></div></li>`;};
  const tabs=`<div class="dw-tabs" role="tablist" aria-label="Bàn đối chiếu">${[['docs','acDocs','📂','Chứng từ',t.docs.length-settled,selD.length],['tx','acTx','🔗','Giao dịch',t.transactions.length-txDone,selT.length]].map(([k,val,e,l,left,picked])=>`<button type="button" role="tab" aria-selected="${tab===k}" class="dw-tab${tab===k?' on':''}" data-action="jobTab" data-tab="${val}"><span><span aria-hidden="true">${e}</span> ${l}</span><em>${picked?`đã chọn ${picked}`:left?`còn ${left}`:'xong ✓'}</em></button>`).join('')}</div>`;
  const board=`<div class="dw-board show-${tab}"><section class="dw-col docs" aria-label="Chứng từ"><h3 class="dw-col-title">📂 Chứng từ</h3><ul class="dw-cards">${t.docs.map(docCard).join('')}</ul></section><section class="dw-col tx" aria-label="Giao dịch"><h3 class="dw-col-title">🔗 Giao dịch</h3><ul class="dw-cards">${t.transactions.map(txCard).join('')}</ul></section></div>`;
  const missing=t.docs.some(d=>d.missing)?`<div class="dw-alert"><div><b>Một phiếu còn thiếu nguồn.</b><p>${t.source_requested?(t.source_at?`Người gửi hẹn gửi lúc ${hm(t.source_at)}${sameDay(t.source_at)?' hôm nay':' sáng mai'}.`:'Đã xin bổ sung.'):'Không ghép thẻ thiếu nguồn.'}</p></div>${t.source_requested?(!t.source_at||sameDay(t.source_at)?commandButton('⏳ Chờ thêm 20 phút','advance',{},'ghost'):button('Việc khác','queue',{},'ghost')):commandButton('Xin nguồn bổ sung','ac_request_source',{task:t.id},'primary')}</div>`:'';
  const groups=t.groups.length?`<section class="dw-sec" aria-label="Nhóm đã ghép"><h3>Nhóm đã ghép · ${t.groups.length}</h3><ul class="dw-groups">${t.groups.map((g,i)=>`<li><span><b>${esc(g.docs.join(' + '))} ↔ ${esc(g.transactions.join(' + '))}</b><small>Khớp ${fmt(g.total)} xu</small></span>${commandButton('Tháo','ac_unmatch',{task:t.id,index:i},'ghost')}</li>`).join('')}</ul></section>`:'';
  const hand=`<section class="dw-sec dw-handover" aria-label="Bàn giao hồ sơ"><h3>Bàn giao hồ sơ</h3>${reqList([
      {ok:read===t.docs.length||null,icon:'👁️',label:'Mở đủ bản gốc',value:`${read}/${t.docs.length}`},
      {ok:settled===t.docs.length||null,icon:'📂',label:'Mỗi chứng từ đã ghép hoặc loại trùng',value:`${settled}/${t.docs.length}`},
      {ok:txDone===t.transactions.length||null,icon:'🔗',label:'Mỗi giao dịch đã có nguồn',value:`${txDone}/${t.transactions.length}`}],esc,'Điều kiện bàn giao')}`+
    `<p class="dw-hint">Thù lao 70 xu.</p><div class="dw-acts">${t.groups.length?button(icon('check',16)+' Kiểm & bàn giao hồ sơ','completeAC',{},allDone?'primary':''):`<button type="button" class="btn" disabled>${icon('check',16)} Kiểm & bàn giao hồ sơ</button>`}${button('Hỏi người gửi','chat',{npc:t.npc,task:t.id},'ghost')}${careData()?openBoard('📚 Tủ hồ sơ khách'):''}</div>`+
    `${room().upgrades.includes('workbench')?notice('Bàn kiểm: tìm phiếu có cùng mã tham chiếu; không tính một nguồn hai lần. Kiểm tổng và tập mã đều phải khớp.','blue','search'):''}</section>`;
  const both=selD.length&&selT.length;
  const bar=allDone?dwBar('<b>Đã ghép đủ.</b> Kiểm lại rồi bàn giao.',button(icon('check',16)+' Bàn giao','completeAC',{},'primary'))
    :selD.length||selT.length?dwBar(`<span class="dw-sums"><span><small>Chứng từ · ${selD.length}</small><b>${fmt(ds)}</b></span><i class="${both?ds===ts?'ok':'bad':''}" aria-label="${both?ds===ts?'bằng nhau':'chưa bằng':'so với'}">${both?ds===ts?'=':'≠':'⇄'}</i><span><small>Giao dịch · ${selT.length}</small><b>${fmt(ts)}</b></span></span>`,
      `<button type="button" class="btn ghost icon-btn" data-action="clearSelection" aria-label="Bỏ chọn">${icon('x',18)}</button>`+(both?(matchBlock(t,selD)?`<button type="button" class="btn primary" disabled>${icon('link',16)} ${esc(matchBlock(t,selD))}</button>`:withWhy(button(icon('link',16)+' Ghép nhóm','match',{},'primary'),acMatchCan(t,selD,selT)))
        :button(selD.length?'Chọn giao dịch →':'← Chọn chứng từ','jobTab',{tab:selD.length?'acTx':'acDocs'},'primary dw-swap')+`<button type="button" class="btn dw-wide-only" disabled>${icon('link',16)} Ghép nhóm</button>`))
    :dwBar(read<t.docs.length?'Mở bản gốc, rồi chọn chứng từ và giao dịch cùng mã HD.':'Chọn chứng từ và giao dịch cùng mã HD.');
  const steps=accountingSteps(t),hint=nextHint({room:room()},steps,{final:allDone?{label:'Kiểm & bàn giao hồ sơ',go:{act:'completeAC'}}:null,cta:false});
  return `<div class="career-job dw dw-ac">${hint}${dwWho(t,'Gửi hồ sơ đối chiếu')}${missing}${tabs}${board}${groups}${hand}${bar}</div>`;
}

// Each option says WHEN it fits (game/engine.py CS_SOL_WHEN), so the evidence decides the pick, not trial and error.
const solutions=[['reship','Gửi bù món thiếu','box','Khi kiện giao thiếu món'],['trace','Đối soát giao nhận','search','Khi kiện chậm, kẹt hay báo giao mà chưa tới'],['exchange','Đổi đúng món','refresh','Khi khách nhận sai mã, sai màu (không phải thiếu món)'],['refund','Thực hiện hoàn','coin','Khi hồ sơ có yêu cầu hoàn hợp lệ'],['guide','Hướng dẫn khách','book','Khi đơn không lỗi, khách cần cách làm']];
const CS_STEPS=['Xác minh','Chứng cứ','Phương án','Thực hiện','Kiểm kết quả','Đóng vụ'];
const CS_CHANNELS=['💬 Tin nhắn','📞 Gọi điện','✉️ Thư điện tử'];
/** Where a support case stands (0–5), from server fields only. */
function csStep(t){if(!t.identity)return 0;if(t.evidence.some(e=>e.text==null))return 1;return {proposed:3,executing:3,awaiting_confirmation:4,resolved:5}[t.status]??2;}
/** Support case, one move at a time (the "Việc bây giờ" card already holds the action). */
function supportSteps(t){
  const step=csStep(t),e=t.evidence.find(e=>e.text==null),read=t.evidence.filter(e=>e.text!=null).length,now='.dw-now .btn.primary';
  const one=(label,go)=>[{ok:null,label,go,pulse:now}];
  if(t.status==='handed_over')return one('Chờ chị Mai phản hồi',{cmd:'advance',label:'⏳ Chờ thêm 20 phút'});
  if(step===0)return one('Xác minh người yêu cầu',{cmd:'cs_identity',payload:{task:t.id},label:'🔐 Xác minh mã đơn'});
  if(step===1&&e)return [{ok:null,label:'Mở chứng cứ',note:`${read}/${t.evidence.length}`,go:{cmd:'cs_evidence',payload:{task:t.id,evidence:e.id},label:`📂 Mở: ${esc(e.title)}`},pulse:now}];
  // The evidence names the fix (thiếu món → gửi bù …); only a first case gets the right card lit.
  const fix={missing:'reship',delivered:'trace',delay:'trace',wrong:'exchange',refund:'refund',guide:'guide'}[t.variant];
  // The hint points at the whole group of options (never at the first one, which reads as "pick this"); on the
  // first (coached) case it proposes the fix the evidence names, as office_kit does on a first dossier.
  const coach=fix&&!(room()?.metrics?.served>0)?solutions.find(x=>x[0]===fix):null;
  if(step===2)return [{ok:null,label:'Chọn một phương án có căn cứ',go:coach?{cmd:'cs_propose',payload:{task:t.id,solution:fix},label:`👉 ${coach[1]}`}:{sel:'.dw-now .dw-choices'},pulse:fix?`.dw-now .dw-choice[data-payload*='"solution":"${fix}"']`:''}];
  if(t.status==='proposed')return one('Gửi việc cho đầu mối',{act:'executeCS',label:'Gửi việc cho đầu mối →'});
  if(t.status==='executing')return one('Chờ kết quả từ đầu mối',t.ready_at==null||sameDay(t.ready_at)?{cmd:'advance',label:'⏳ Chờ thêm 20 phút'}:{act:'queue',label:'Xem các việc khác'});
  if(step===4)return one('Kiểm kết quả đã về',{cmd:'cs_confirm',payload:{task:t.id},label:'🔍 Kiểm kết quả'});
  return one('Hoàn tất & đóng vụ',{act:'closeCS',label:'✓ Hoàn tất & đóng vụ'});
}
function supportJob(t){
  const step=csStep(t),read=t.evidence.filter(e=>e.text!=null).length,sol=solutions.find(x=>x[0]===t.proposal);
  const channel=CS_CHANNELS[[...String(t.id)].reduce((a,ch)=>a+ch.charCodeAt(0),0)%CS_CHANNELS.length],cl=uiClean();
  const tracker=`<ol class="dw-steps" aria-label="Tiến trình vụ">${CS_STEPS.map((s,i)=>`<li class="${i<step?'done':i===step?'now':''}"${i===step?' aria-current="step"':''}${cl?` aria-label="${s}" title="${s}"`:''}><span class="dw-dot" aria-hidden="true">${i<step?'✓':i+1}</span>${cl?'':`<span class="dw-step-label">${s}</span>`}</li>`).join('')}</ol>`;  // (the current step is the lit one in the tracker; the "Bước x/6" line under it repeated it)
  const canPropose=t.identity&&read===t.evidence.length&&['new','understood','proposed'].includes(t.status);
  const choices=`<div class="dw-choices" role="group" aria-label="Phương án">${solutions.map(([id,l,i,h])=>`<button type="button" class="dw-choice${t.proposal===id?' selected':''}" data-command="cs_propose" data-payload="${esc(JSON.stringify({task:t.id,solution:id}))}" aria-pressed="${t.proposal===id}"${canPropose?'':' disabled'}>${icon(i,22)}<span><b>${l}</b><small>${h}</small></span></button>`).join('')}</div>`;
  // The eyebrow names the lit part of the tracker (its labels are hidden on a phone); one line says what to do there.
  // Clean layout (docs/UI_KIT.md): the lit tracker names the step; the card keeps its title (the explanation goes to the
  // "?"), and a single action button moves to the shared bar at the bottom (one main button). Choices stay in the card.
  let main='';
  // `keep`: the text is a fact (a promised time, the call-before-noon rule), not an explanation: it stays in sight.
  // `card`: the title itself says something the bar does not (the plan picked); otherwise a card whose only action
  // moved to the bar goes (its title just repeats the button).
  const now=(title,text,action,extra='',{keep=false,card=false}={})=>{
    if(cl&&/^\s*<button\b/.test(action)&&(action.match(/<button\b/g)||[]).length===1){main=action.replace(/\sfull(?=[\s"])/,'');action='';if(!extra&&!keep&&!card)return text?uiTip(text,title,'p'):'';}
    return `<section class="dw-now" aria-label="Việc bây giờ">${cl?'':`<span class="dw-eyebrow">Bước ${step+1}/${CS_STEPS.length} · ${CS_STEPS[step]}</span>`}<h3>${title}</h3>${text?(cl&&!keep?uiTip(text,title,'p'):`<p>${text}</p>`):''}${extra}${action}</section>`;};
  const key=t.evidence.find(e=>e.id===t.basis&&e.text!=null);  // 📌 the source line that names the fix (server sends it once every source is read)
  let card;
  const waitNow=t.ready_at==null||sameDay(t.ready_at);
  if(t.status==='handed_over')card=now('Chờ chị Mai phản hồi',t.eta?`Chị Mai hẹn phản hồi ${esc(t.eta.toLowerCase())}.`:'',commandButton('⏳ Chờ thêm 20 phút','advance',{},'primary full'),'',{keep:true});
  else if(step===0)card=now('Xác minh người yêu cầu','Khớp mã đơn khách đưa thì mới được xem hồ sơ.',commandButton('🔐 Xác minh mã đơn','cs_identity',{task:t.id},'primary full',!room().open));
  else if(step===1){const e=t.evidence.find(e=>e.text==null);card=now(`Mở chứng cứ · ${read}/${t.evidence.length}`,'Đọc đủ các nguồn: một dòng trong đó chỉ cách xử lý.',commandButton(icon('folder',16)+' Mở: '+esc(e.title),'cs_evidence',{task:t.id,evidence:e.id},'primary full'));}
  else if(step===2)card=now('Chọn phương án khớp căn cứ','',choices,key?`<blockquote class="dw-basis"><b>📌 ${esc(key.title)}</b>“${esc(key.text)}”</blockquote>`:'');
  else if(t.status==='proposed')card=now(`Phương án: ${sol?.[1]||''}`,'Mới là đề xuất: gửi việc thì đầu mối mới làm.',button('Gửi việc cho đầu mối '+icon('arrow',15),'executeCS',{},'primary full'),'',{card:true});
  else if(t.status==='executing')card=now(`Đang chờ ${esc(t.wait_label||'đầu mối')}: ${sol?.[1]||''}`,`Dự kiến có kết quả: <b>${esc(t.eta||'')}</b>.${waitNow?'':' Vụ mở qua đêm: mỗi sáng gọi cập nhật cho khách trước 12:00.'}`,waitNow?commandButton('⏳ Chờ thêm 20 phút','advance',{},'primary full'):button('Xem các việc khác','queue',{},'primary full'),'',{keep:true});
  else if(step===4)card=now('Kết quả đã về','Đầu mối báo xong: kiểm với khách trước khi đóng.',commandButton(icon('search',16)+' Kiểm kết quả','cs_confirm',{task:t.id},'primary full'));
  else card=now('Kết quả đã kiểm chứng','Khách đã xác nhận: đóng vụ, nhận 65 xu.',button(icon('check',16)+' Hoàn tất & đóng vụ','closeCS',{},'primary full'));
  const change=t.status==='proposed'?`<section class="dw-sec dw-change" aria-label="Đổi phương án"><h3>Đổi phương án?</h3>${choices}</section>`:'';
  const handover=t.identity&&t.status==='understood'&&!t.handed_over?`<section class="dw-alt">${(h=>cl?uiTip(h,'Bàn giao cùng chị Mai','p'):`<p class="dw-hint">${h}</p>`)(`Chưa chắc hướng xử lý? Bàn giao cho chị Mai kèm nguồn đã đọc${t.inspected.length<2?' (cần đọc ít nhất 2 nguồn)':''}.`)}${commandButton('Bàn giao cùng chị Mai','cs_handover',{task:t.id},'ghost',t.inspected.length<2)}</section>`:'';
  const evidence=`<section class="dw-sec" aria-label="Chứng cứ"><div class="dw-sec-head"><h3>Chứng cứ</h3><span class="dw-count${read===t.evidence.length?' ok':''}">${read}/${t.evidence.length}</span></div>${cl&&!t.identity?'':`<ul class="dw-evlist">${t.evidence.map(e=>{const open=e.text!=null;
    return `<li class="dw-ev${open?' done':''}${key===e?' key':''}"><span class="dw-mark" role="img" aria-label="${open?'Đã mở':'Chưa mở'}">${open?'✓':''}</span><div><b>${esc(e.title)}${key===e?' <em class="dw-key">📌 Căn cứ</em>':''}</b>${open?`<p>${esc(e.text)}</p>`:t.identity||cl?'':'<small>Xác minh để mở</small>'}</div>${!open&&t.identity?commandButton('Mở','cs_evidence',{task:t.id,evidence:e.id},'ghost'):''}</li>`;}).join('')}</ul>`}</section>`;
  const notes=`${room().upgrades.includes('workbench')&&!cl?notice('Bàn kiểm hai bước: so yêu cầu của khách với chứng cứ đóng gói/giao nhận, không coi một trạng thái đơn lẻ là kết luận.','blue','search'):''}`;
  const log=t.timeline.length?fold(cl?`📒 ${t.timeline.length}`:`Nhật ký vụ · ${t.timeline.length} dòng`,`<ol class="dw-log">${t.timeline.map(line=>`<li>${esc(line)}</li>`).join('')}</ol>`):'';
  const sub=cl?`${channel.split(' ')[0]}${t.value?` · ${fmt(t.value)} xu`:''}${t.days_open?` · 📅 ${t.days_open+1}`:''}`:`${channel}${t.value?` · đơn ${fmt(t.value)} xu`:''}${t.days_open?` · ngày thứ ${t.days_open+1}`:''}`;
  const timers=[t.sla_label?dwState(`⏳ Phản hồi đầu: còn ${esc(t.sla_label)}`,'amber'):'',t.sla==='late'?dwState('Trễ hạn phản hồi đầu','danger'):'',t.upd_label?dwState(`📞 Gọi cập nhật: ${esc(t.upd_label)}`,t.upd?.done?'green':t.upd?.late?'danger':'amber'):''].join('');
  const seen=careData()?.people?.find(p=>p.npc===t.npc),past=seen?.last?.filter(x=>!x.title||x.title!==t.title||x.day!==t.day)||[];
  const history=seen&&past.length?`<section class="cb-history" aria-label="Thẻ khách"><h3>🗂️ ${esc(seen.name)} đã gọi ${seen.n} lần</h3><ul class="cb-past">${past.slice().reverse().map(x=>`<li>Ngày ${x.day}: ${esc(x.title)} · ${esc(x.note)}${x.stars?` · ${x.stars}★`:''}</li>`).join('')}</ul></section>`:'';
  return `<div class="career-job dw dw-cs">${nextHint({room:room()},supportSteps(t),{cta:false})}${dwWho(t,sub)}${timers?`<div class="cs-timers">${timers}</div>`:''}${cl?`<div class="cs-track">${tracker}${helpBtn('cs-desk','🎧 Bàn chăm sóc khách',[{title:'Sáu bước của một vụ',body:`<ol>${CS_STEPS.map(s=>`<li>${esc(s)}</li>`).join('')}</ol>`},{title:'Phương án',body:`<ul>${solutions.map(([,l,,h])=>`<li><b>${esc(l)}</b>: ${esc(h)}</li>`).join('')}</ul>`}],{tips:true,cls:'cs-q'})}</div>`:tracker}<div class="dw-cs-grid"><div class="dw-cs-work">${card}${change}${handover}${csCallPanel(t)}</div><div class="dw-cs-facts">${history}${evidence}${notes}${log}</div></div>${main?actBar({main,cls:'cs-bar'}):''}</div>`;  // the follow-up board: dock "Theo dõi"
}
function chatView(){
  const id=ui.npc||activeTask()?.npc||api.content.npcs.find(n=>n.career_id===career()).id,n=npc(id),c=room();ui.npc=id;
  const messages=c.chats[id]||[],memories=c.memories.filter(m=>m.npc===id),t=c.tasks.find(t=>t.npc===id&&!ended(t)),relation=c.relationships[id]||0;
  const rel=L.people.use()?.tierLabel(api,id)||(relation>=40?'Thân thiết':relation>5?'Bạn quen':relation?'Đã từng giúp nhau':'Lần đầu gặp');
  const quick=[['Bạn cần gì hôm nay?','Bạn cần gì hôm nay?'],['Nhớ lần trước không?','Bạn nhớ lần trước mình giúp gì không?'],['Hôm nay thế nào?','Hôm nay bạn thấy thế nào?']];
  return `<header class="sheet-head chat-head"><span class="chat-avatar">${portrait(n,48)}</span><div class="grow"><span class="eyebrow">${esc(n.role||'Trò chuyện')}</span><h2>${esc(n.display_name)}</h2><p>${rel}${memories.length?` · ${memories.length} kỷ niệm chung`:''}</p></div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`+
    `<div class="sheet-body chat-body">${t?`<div class="chat-task"><span class="grow">${icon('flag',14)} ${esc(t.title)}</span>${t.known?'':commandButton('Hỏi rõ nhu cầu','ask',{task:t.id},'small ghost')}${button('Mở việc '+icon('arrow',13),'job',{task:t.id},'small primary')}</div>`:''}${L.chat.use()?L.chat.m.chatMessages(env(),{npc:id,name:n.display_name,messages,opening:t?.opening}):skeleton()}`+
    `<details class="chat-about"><summary>Về ${esc(n.display_name)}</summary>${n.personality?`<p class="small">${esc(n.personality)}</p>`:''}<div class="progress" aria-hidden="true"><i style="width:${Math.min(100,Math.max(4,relation))}%"></i></div>${memories.slice(-3).reverse().map(m=>`<div class="memory">${esc(m.text)}${m.day?`<br><small class="muted">Ngày ${m.day}</small>`:''}</div>`).join('')}${messages.length?button('Xóa tin nhắn','clearChat',{},'small ghost space-top'):''}</details></div>`+
    (L.chat.m?L.chat.m.chatFooter(env(),{npc:id,name:n.display_name,quick,suggestions:ui.suggestions[id]}):'');
}
/** Posts older than the feed kept in the save (read only). */
function olderPosts(c){return olderRows(career(),'feed').map(p=>`<article class="post older"><div class="row"><div class="grow"><span class="author">${esc(p.author||'')}</span><div class="post-meta">Ngày ${Number(p.day)||''}</div></div>${p.kind==='review'?pill('Đánh giá','amber'):''}</div><div class="post-text">${p.stars?`<div class="stars" aria-label="${p.stars} trên 5 sao">${'★'.repeat(p.stars)}${'☆'.repeat(5-p.stars)}</div>`:''}${esc(p.text||'')}</div>${(p.comments||[]).map(co=>`<div class="comment"><strong>${esc(co.author||'')}</strong><p>${esc(co.text||'')}</p></div>`).join('')}</article>`).join('')+olderButton(career(),'feed',c.feed.length,c.feed.length>=100);}
function phoneView(){const c=room(),reviews=c.feed.filter(p=>p.stars).length;markFeedSeen();
  const followup=meta().review_followup||REVIEW_PASSPORT.includes(career());   // where the server takes review_followup (game/content.py REVIEW_FOLLOWUP)
  const posts=c.feed.map(p=>`<article class="post" id="${p.id}"><div class="row">${p.npc==='player'?`<span class="avatar-small">${esc([...String(p.author||'')][0]||'')}</span>`:portrait(npc(p.npc),42)}<div class="grow"><div class="ck-meta"><span class="author">${esc(p.author)}</span><small>Ngày ${p.day}</small></div>${p.stars?`<div class="stars ck-stars" aria-label="${p.stars} trên 5 sao">${'★'.repeat(p.stars)}${'☆'.repeat(5-p.stars)}</div>`:p.npc==='player'||p.kind==='review'?`<div class="post-meta">${p.npc==='player'?'Bài của bạn':'Đánh giá'}</div>`:''}</div></div><div class="post-text">${esc(p.text)}</div>`+
    `<div class="post-actions">${commandButton(icon('heart',14)+' '+(p.liked?'Đã thích':'Thích'),'feed_like',{post:p.id},'small'+(p.liked?' liked':''))}${p.feedback?button(icon('chat',14)+' Trả lời đánh giá','fbGo',{post:p.id},'small'):''}${p.kind==='review'&&followup?button(icon('flag',14)+' Trao đổi tình huống','reviewFollowup',{post:p.id},'small'):''}${p.comments.length?`<small class="muted">${p.comments.length} lời nhắn</small>`:''}${p.feedback?'':`<details class="reply-more"><summary>${icon('chat',14)} Trả lời</summary><form class="reply-form" data-reply-post="${p.id}"><input class="input" id="reply-${p.id}" data-preserve maxlength="500" required placeholder="Trả lời ${esc(p.author)}…" aria-label="Trả lời ${esc(p.author)}"><button type="submit" class="btn primary" aria-label="Gửi trả lời">${icon('send',15)}</button></form></details>`}</div>`+
    `${p.comments.map((co,index)=>`<div class="comment ck-box ${co.npc==='player'?'ck-owner owner-reply':'ck-quiet'}"><strong>${esc(co.author)}${co.npc==='player'?' '+pill('Bạn'):''}</strong><p>${esc(co.text)}</p>${co.npc==='player'?button('Sửa','expReplyEdit',{post:p.id,index},'small ghost'):''}</div>`).join('')}</article>`).join('');
  return header('Chuyện phố','','BẢNG TIN KHU PHỐ')+`<div class="sheet-body feed-v6"><form id="postForm" class="feed-composer"><span class="avatar-small" aria-hidden="true">${esc([...String(api.state.name||'')][0]||'')}</span><textarea id="post-text" data-preserve rows="2" maxlength="500" required placeholder="Hôm nay tiệm có chuyện gì? Kể hàng xóm nghe…" aria-label="Nội dung bài viết"></textarea><button class="btn primary" type="submit">${icon('send',15)} Đăng</button></form>`+
    `${reviews?`<button type="button" class="feed-rating" data-action="feedback"><b>★ ${c.rating}</b><span>${reviews} đánh giá của khách</span><span class="grow"></span><span class="feed-rating-go">Xem tất cả ${icon('chevron',13)}</span></button>`:''}${posts||empty('Bảng tin còn yên ắng','','mail')}${olderPosts(c)}</div>`+footer('',commandButton(icon('refresh',14)+' Xem lời nhắn mới','advance',{},'ghost'));}
function eventView(){const e=room().event;if(!e)return header('Hôm nay vẫn thật bình thường')+`<div class="sheet-body">${empty('Chưa có chuyện cần xử lý','','coffee')}${button('Xem 24 tình huống của nghề','library',{},'primary space-top')}</div>`;
 const n=npc(e.npc),opt=e.options.find(o=>o.id===e.chosen);return header(esc(e.title),e.practice?'Diễn tập · không ảnh hưởng tiền, đánh giá hay quan hệ.':'',e.practice?'DIỄN TẬP':'CHUYỆN ĐỜI THƯỜNG')+`<div class="sheet-body"><div class="event-hero">${portrait(n,64)}<div><span class="eyebrow">${esc(n.display_name)}</span><p>${esc(e.opening)}</p></div></div><div class="event-evidence">${e.evidence.map(ev=>`<article class="evidence-card"><span class="eyebrow">${esc(ev.source)}</span><h4>${icon(ev.text?'check':'eye',16)} ${esc(ev.title)}</h4>${ev.text?`<p>${esc(ev.text)}</p>`:commandButton('Kiểm dữ kiện này','event_read',{evidence:ev.id},'ghost small')}</article>`).join('')}</div><h3 class="space-top">Bạn muốn xử lý như thế nào?</h3><div class="choice-grid">${e.options.map(o=>`<button class="choice ${e.chosen===o.id?'selected':''}" data-command="event_choose" data-payload="${esc(JSON.stringify({choice:o.id}))}" ${e.read.length<2||!['noticed','investigating','proposed'].includes(e.stage)?'disabled':''}><strong>${esc(o.label)}</strong><small>${o.cost?o.cost+' xu từ quỹ nghề':'Không tốn xu'}</small></button>`).join('')}</div>${e.stage==='proposed'?`<div class="execution"><h4>Đề nghị đã rõ</h4><p class="small">${esc(opt.response)}</p>${button('Xác nhận phương án','confirmEvent',{},'primary')}</div>`:e.stage==='executing'?`<div class="execution"><h4>Thực hiện điều đã thống nhất</h4>${opt.steps.map((s,i)=>`<div class="step-item"><span class="step-circle ${i<e.step?'done':''}">${i<e.step?icon('check',13):i+1}</span>${esc(s)}</div>`).join('')}${button(icon('play',14)+' '+esc(opt.steps[e.step]),'eventStep',{},'primary full space-top')}</div>`:e.stage==='resolved'?`<div class="execution"><h3>${icon('check',20)} Chuyện đã có kết quả</h3><p class="small">Đã thực hiện: <strong>${esc(opt.label)}</strong>.</p>${commandButton('Cất câu chuyện','event_dismiss',{},'primary')}</div>`:(e.read.length<2?notice('Xem ít nhất hai dữ kiện rồi mới chọn cách xử lý nhé.','','search'):'')}</div>`+footer('',e.practice?commandButton('Cất diễn tập','event_dismiss',{},'ghost small'):button('Quay lại quầy','close',{},'ghost small'));
}
function peopleView(){const c=room();return header('Bạn quen','','KHU PHỐ')+`<div class="sheet-body"><div class="npc-grid">${api.content.npcs.filter(n=>n.career_id===career()).map(n=>`<article class="npc-card">${portrait(n,72)}<h3>${esc(n.display_name)}</h3>${pill(esc(n.role))}<p>${esc(n.personality)}</p><div class="small muted">${c.memories.filter(m=>m.npc===n.id).length} ký ức · ${c.relationships[n.id]||0} lần gắn kết</div>${button(icon('chat',14)+' Trò chuyện','chat',{npc:n.id},'small primary full')}</article>`).join('')}</div></div>`;}
function journalView(){const c=room(),tab=ui.journalTab;let inner='';
  if(tab==='quests')inner=c.quest_progress.map(progress=>{const q=api.content.quests.find(q=>q.id===progress.id);return `<article class="quest-card"><div class="row spread"><div><span class="eyebrow">CÂU CHUYỆN · ${q.id}</span><h3>${esc(q.title)}</h3></div>${icon(progress.claimed?'award':'book',26)}</div><p>${esc(q.story)}</p>${progress.steps.map(s=>`<div class="quest-step ${s.done?'done':''}"><span class="step-circle ${s.done?'done':''}">${s.done?icon('check',12):icon('flag',12)}</span><span class="grow">${esc(s.title)}</span><span class="small">${Math.min(s.current,s.goal)} / ${s.goal}</span></div>`).join('')}<div class="row spread space-top">${pill(`Kỷ niệm + ${q.reward} xu`,'amber')}${commandButton(progress.claimed?'Đã lưu kỷ niệm':'Nhận kỷ niệm','quest_claim',{quest:q.id},'small primary',!progress.ready||progress.claimed)}</div></article>`;}).join('');
  else if(tab==='history'){const row=l=>`<div class="history-row"><small>Ngày ${l.day}<br>Nhịp ${l.turn}</small><div class="grow">${esc(l.text)}</div>${icon(({money:'coin',event:'flag',day:'sun',match:'link',correction:'check',fact:'chat',upgrade:'plant',keepsake:'award'})[l.kind]||'note',15)}</div>`,shown=Math.min(80,c.journal.length);
    inner=(c.journal.slice().reverse().slice(0,80).map(row).join('')+olderRows(career(),'journal').map(row).join('')+olderButton(career(),'journal',shown,c.journal.length>shown||c.journal.length>=100))||empty('Một cuốn sổ còn mới');}
  else if(tab==='memories')inner=c.memories.slice().reverse().map(m=>`<div class="memory"><strong>${esc(npc(m.npc).display_name)}</strong><p>${esc(m.text)}</p>${m.day?`<small class="muted">Ngày ${m.day}</small>`:''}</div>`).join('')||empty('Chưa có ký ức chung','','people');
  else {const q=ui.libraryQuery.toLocaleLowerCase('vi-VN'),items=api.content.event_catalogue.filter(e=>e.career===career()&&(`${e.id} ${e.title}`.toLocaleLowerCase('vi-VN').includes(q)));inner=`<input class="input" id="library-search" data-preserve placeholder="Tìm: review, clip, quên ví, mất hàng…" value="${esc(ui.libraryQuery)}" aria-label="Tìm tình huống"><div class="event-library space-top">${items.map(e=>`<article class="library-item"><small class="muted">Diễn tập</small><h4>${esc(e.title)}</h4>${button('Thử tình huống '+icon('arrow',13),'practice',{event:e.id},'small ghost')}</article>`).join('')||empty('Chưa có tình huống khớp')}</div>`;}
  return header('Sổ tay','','SỔ TAY')+`<div class="sheet-body"><nav class="pill-tabs">${[['quests','Câu chuyện'],['history','Nhật ký'],['memories','Ký ức'],['library','24 tình huống']].map(([id,label])=>`<button data-action="journalTab" data-tab="${id}" class="${tab===id?'active':''}">${label}</button>`).join('')}</nav>${inner}</div>`;
}
function decorView(){const c=room(),spots={window:'Bên cửa sổ',corner:'Góc phòng',front:'Gần cửa',center:'Giữa phòng',wall:'Trên tường'};return header('Trang trí & nâng cấp','','GÓC CỦA BẠN',pill(icon('coin',13)+' '+fmt(c.money)+' xu','amber'))+`<div class="sheet-body">${equipmentView(c,career(),api.content.upgrades)}<div class="row spread space-top"><div><h3>Chọn sắc cho căn phòng</h3><p class="muted small">Đổi màu tường không tốn xu.</p></div>${icon('plant',25)}</div><div class="theme-options">${[['boba','Trà sữa'],['warm','Ấm áp'],['sage','Xanh dịu'],['lavender','Tím mây']].map(([id,l])=>commandButton(`${(c.theme||'boba')===id?icon('check',13):icon('sun',13)} ${l}`,'theme',{theme:id},'small '+((c.theme||'boba')===id?'primary':'ghost'))).join('')}</div><div class="upgrade-grid">${api.content.upgrades.filter(u=>u.kind!=='equipment'&&(!u.careers||u.careers.includes(career()))).map(u=>{const owned=c.upgrades.includes(u.id);return `<article class="upgrade-card"><div class="row spread"><span class="upgrade-icon">${icon(u.icon,31)}</span>${pill(owned?'ĐÃ CÓ':u.min_level>c.level?'CẤP '+u.min_level:u.price+' XU',owned?'green':'')}</div><h3>${esc(u.name)}</h3><p>${esc(u.description)}</p>${owned?(u.kind==='decor'?`<select aria-label="Vị trí ${esc(u.name)}" data-decor-item="${u.id}">${Object.entries(spots).filter(([s])=>u.id==='poster'?s==='wall':s!=='wall').map(([id,label])=>`<option value="${id}"${c.decor[u.id]?.spot===id?' selected':''}>${label}</option>`).join('')}</select>`:u.id==='assistant'?commandButton('Nhờ hỗ trợ hôm nay','assistant_help',{},'small',c.assistant_day===c.day):pill('Đang dùng trong nghề','green')):u.min_level>c.level?`<button type="button" class="btn ghost full" disabled>🔒 Mở ở cấp ${u.min_level} (đang cấp ${c.level})</button>`:c.money<u.price?`<button type="button" class="btn ghost full" disabled>Thiếu ${fmt(u.price-c.money)} xu</button>`:button(icon('plus',14)+' Đặt trong phòng','buyUpgrade',{item:u.id},'primary full')}</article>`;}).join('')}</div></div>`+footer('',button('Xem căn phòng','close',{},'primary'));}
/* ---- Many days at the original desks + the stock room (warehouseView): legacy parcels on the
   shop clock (mother_baby, pharmacy), the pharmacy's lot book · fridge log · regulars, the
   bookkeeping client files and the support follow-up board, plus the support call panel.
   Server-authoritative: data-wh-* and data-cs-* are handled by the two listeners below.
   Spec: docs/superpowers/specs/2026-09-29-desk-careers-care-ai-design.md · css/desks.css. ---- */
const hm=a=>{const m=((Number(a)||0)%1440+1440)%1440;return `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`;};
const careData=()=>room()?.data?.care||null;
const sameDay=a=>Number.isFinite(a)&&Math.floor(a/1440)===room()?.day;
const hearts=(n,max=5)=>`<span class="cb-hearts" role="img" aria-label="Tin cậy ${n}/${max}">${'♥'.repeat(n)}<i>${'♥'.repeat(Math.max(0,max-n))}</i></span>`;
const confirmBtn=(label,op,payload,confirm,style='',disabled=false)=>`<button type="button" class="btn ${style}" data-action="v4Cmd"${attrs({op,payload:JSON.stringify(payload),confirm})}${disabled?' disabled':''}>${label}</button>`;
const openBoard=(label,tab='',style='ghost')=>`<button type="button" class="btn ${style}" data-wh-open="${esc(tab)}">${label}</button>`;
const aiVoices=()=>!!(api.ai?.configured&&api.state?.settings?.aiConsent);
const priceWord=f=>f<1?`rẻ hơn ×${String(f).replace('.',',')}`:f>1?`đắt hơn ×${String(f).replace('.',',')}`:'giá niêm yết';
const FLAG_LABEL={expired:['Quá hạn','danger'],recalled:['Thu hồi','danger'],warm:['Hỏng lạnh','danger']};

function warehouseView(){
  const id=career();
  if(id==='accounting')return clientBoard();
  if(id==='customer_care')return followBoard();
  if(!['mother_baby','pharmacy'].includes(id))return queueView();
  const c=room(),ph=id==='pharmacy',care=ph?careData():null,cap=Math.max(c.ops.property.details.stock_cap,c.upgrades.includes('shelf')?24:12);
  const tab=ph&&['lots','regulars'].includes(ui.whTab)?ui.whTab:'stock';
  const bad=care?.batches?.filter(b=>b.flag).length||0,here=care?.regulars?.filter(r=>r.state==='here'||r.state==='call').length||0;
  const tabs=ph?`<div class="dw-tabs wh-tabs" role="tablist" aria-label="Kho & sổ quầy">${[['stock','📦','Kho',''],['lots','🧊','Sổ lô',bad?`${bad} cần rút`:''],['regulars','💊','Khách quen',here?`${here} cần làm`:'']].map(([k,e,l,n])=>`<button type="button" role="tab" aria-selected="${tab===k}" class="dw-tab${tab===k?' on':''}" data-wh-tab="${k}"><span><span aria-hidden="true">${e}</span> ${l}</span><em>${n||'&nbsp;'}</em></button>`).join('')}</div>`:'';
  const body=tab==='lots'?phLotBook():tab==='regulars'?phRegulars():stockDesk(cap);
  return header(ph?'Kho & sổ quầy':'Kho nhỏ sau tiệm',esc(c.stock_desk?.clock?.label||''),'KHO HÀNG · SỨC CHỨA '+cap+' / MÃ')+`<div class="sheet-body wh">${tabs}${body}</div>`+footer('',c.open?commandButton('⏳ Chờ thêm 20 phút','advance',{},'ghost small'):'');
}
const SHIP_CAP=8,MERGE_CAP=12;
/** Deliveries on the way (game/engine.py stock_vans): the lines of one merged order share a van. */
const stockVans=c=>new Set(c.shipments.filter(s=>s.status==='in_transit').map(s=>s.placed!=null?`${s.supplier}|${s.placed}|${s.lo}|${s.hi}`:s.id)).size;
function stockDesk(cap){
  const c=room(),id=career(),mb=id==='mother_baby',desk=c.stock_desk||{},care=mb?null:careData(),list=mb?api.content.products:api.content.lots.filter(l=>l.status==='available');
  const waiting=c.shipments.filter(s=>s.status!=='received'),arrived=waiting.filter(s=>s.ready_now),onWay=k=>waiting.filter(s=>s.item===k).reduce((n,s)=>n+s.qty,0),low=list.filter(p=>c.stock[p.id]+onWay(p.id)<=2);
  // order_stock takes at most SHIP_CAP deliveries on the way (game/engine.py): past that, receive one first.
  const vansFull=stockVans(c)>=SHIP_CAP,picks=ui.whPick?.[id]||{};
  const sups=desk.suppliers||[],picked=ui.whSup?.[id],supId=sups.some(s=>s.id===picked)?picked:(desk.default||sups[0]?.id),sup=sups.find(s=>s.id===supId);
  const next=waiting.filter(s=>!s.ready_now).sort((a,b)=>(a.left_min??0)-(b.left_min??0))[0];
  const chip=(n,label,kind)=>n?`<span class="inv-chip ${kind}"><b>${n}</b> ${label}</span>`:'';
  const strip=`<section class="inv-status" aria-label="Tình trạng kho"><div class="inv-chips">${chip(arrived.length,'kiện đã tới · đếm ở dưới','accent')}${chip(waiting.length-arrived.length,'kiện đang giao','info')}${chip(low.length,'mã sắp hết','warn')}${vansFull?`<span class="inv-chip warn">🚚 Đủ ${SHIP_CAP} kiện đang giao: nhận bớt rồi đặt tiếp</span>`:''}${!waiting.length&&!low.length?`<span class="inv-calm">${icon('check',14)} Kho ổn.</span>`:''}</div>`+
    `${!arrived.length&&next?`<div class="inv-cta"><p class="wh-next">Kiện sớm nhất: <b>${esc(next.eta_label||'')}</b>${next.left_label?` · ${esc(next.left_label)}`:''}</p>${c.open&&sameDay(next.arrives_day*1440)?commandButton('⏳ Chờ thêm 20 phút','advance',{},'primary'):''}</div>`:''}</section>`;
  const parcel=s=>{const p=product(s.item);return s.ready_now?`<article class="card inv-crate-card open"><div class="row spread"><strong>${esc(p.name)}</strong>${pill('ĐÃ TỚI','green')}</div><div class="inv-slip"><span>Phiếu giao ghi</span><b>${s.qty} món</b></div><ul class="inv-crate" aria-label="Trong kiện">${Array.from({length:s.actual||0},()=>`<li>${itemArt(p.icon||'box',32,p.color)}</li>`).join('')}</ul><form class="inv-receive" data-receive="${esc(s.id)}"><label for="count-${esc(s.id)}">Bạn đếm được</label><input id="count-${esc(s.id)}" class="input" type="number" min="1" max="12" inputmode="numeric" required placeholder="0" style="width:88px"><button class="btn primary" type="submit">${icon('check',15)} Kiểm & nhập kho</button></form></article>`
    :`<article class="card order-row wh-parcel"><div class="row spread"><div class="grow"><strong>${esc(p.name)} · ${s.qty} món</strong><small class="muted block">${esc(s.supplier_emoji||'🚚')} ${esc(s.supplier_name||'')} · đã trả ${fmt(s.cost)} xu</small></div>${pill('ĐANG GIAO','amber')}</div><p class="wh-eta">Dự kiến nhận: <b>${esc(s.eta_label||'')}</b>${s.left_label?` · ${esc(s.left_label)}`:''}</p><span class="wh-prog" aria-hidden="true"><i style="width:${Math.round((s.progress||0)*100)}%"></i></span>${s.late_note?`<p class="wh-late">⚠️ ${esc(s.late_note)}</p>`:''}</article>`;};
  const pick=sups.length?`<details class="wh-sups wh-sups-fold" data-fold="wh-sups"><summary><span class="wh-sups-k">Nhập từ</span><b>${sup?`<span aria-hidden="true">${esc(sup.emoji||'🚚')}</span> ${esc(sup.name)}`:''}</b><small>${esc(sup?.quote?.label||sup?.window||'')}</small></summary><div class="wh-sup-list" role="radiogroup" aria-label="Chọn nhà cung cấp">${sups.map(s=>`<button type="button" role="radio" aria-checked="${s.id===supId}" class="wh-sup${s.id===supId?' on':''}" data-wh-sup="${esc(s.id)}"><span class="wh-sup-name"><span aria-hidden="true">${esc(s.emoji||'🚚')}</span> ${esc(s.name)}</span><b>${esc(s.quote?.label||s.window||'')}</b><small>${esc(priceWord(s.factor))} · ${esc(s.window||'')}</small></button>`).join('')}</div>${sup?.note?`<p class="dw-hint">${esc(sup.note)}</p>`:''}</details>`:'';
  const row=p=>{const q=c.stock[p.id],on=onWay(p.id),held=q-c.available[p.id],room_=Math.max(0,cap-q-on),max=Math.min(6,room_),state=q===0?'out':q+on<=2?'low':'';
    // The bill sits on the order button and follows the number ("Đặt 3 · 108 xu", whBill), priced as whOrder charges.
    const qty=Math.min(Math.max(1,max),state?Math.min(4,Math.max(1,max)):1),can=!!(max&&c.open&&!vansFull),cost=Math.max(1,Math.ceil(p.cost*qty*(sup?.factor??1)));
    const lots=care?.batches?.filter(b=>b.lot===p.id)||[],first=lots.find(b=>!b.flag),flagged=lots.filter(b=>b.flag).reduce((n,b)=>n+b.qty,0);
    return `<div class="inventory-row inv-row ${state}">${itemArt(p.icon||'box',45,p.color)}<div class="grow"><h4>${esc(p.name)}${mb?'':` · ${esc(p.id)}`}</h4><small><b class="inv-big">${q}</b>/${cap} trên kệ${on?` · <span class="inv-flag info">+${on} đang giao</span>`:''}${held?` · đang giữ ${held}`:''} · ${fmt(p.cost)} xu/món</small>${!mb&&(first||flagged)?`<small class="block">${first?`HSD gần nhất: ngày ${first.exp}`:''}${flagged?` · <b class="wh-bad">${flagged} hộp cần rút</b>`:''}</small>`:''}<span class="inv-bar" aria-hidden="true"><i style="width:${Math.round(q/cap*100)}%"></i><i class="on" style="width:${Math.round(on/cap*100)}%"></i></span></div>`+
      `<span class="inv-row-act">${whQty(p,max,qty)}${can?`<label class="wh-pick"><input type="checkbox" data-wh-pick="${esc(p.id)}"${picks[p.id]?' checked':''}> Gộp</label>`:''}<button type="button" class="btn small${state&&max&&!vansFull?' primary':''}" data-wh-order="${esc(p.id)}"${can?` data-cost="${p.cost}" data-factor="${sup?.factor??1}" data-money="${c.money}"`:''}${can&&cost<=c.money?'':' disabled'}>${!max?'Kệ đầy':vansFull?`Đủ ${SHIP_CAP} kiện`:!c.open?(mb?'Mở tiệm trước':'Mở quầy trước'):whLabel(qty,cost,c.money)}</button>${!mb?(c.held_lots.includes(p.id)?commandButton('Cô Thu kiểm lại','ph_release',{lot:p.id},'small primary'):commandButton('Tạm giữ','ph_quarantine',{lot:p.id},'small ghost')):''}</span></div>`;};
  // Đơn gộp (F#194): tick “Gộp” on several rows, then one order, one payment, one van (engine order_stock `lines`).
  const n=list.filter(p=>picks[p.id]).length;
  const merge=c.open?`<div class="wh-merge"><button type="button" class="btn small${n?' primary':''}" data-wh-merge="1"${n&&!vansFull?'':' disabled'}>🛒 Đặt đơn gộp · <span data-wh-merge-n>${n}</span> mã</button><small class="muted">Tick “Gộp” ở các mã cần nhập, chỉnh số rồi đặt một lần: một chuyến xe, trả một lần (tối đa ${MERGE_CAP} mã).</small></div>`:'';
  return strip+(waiting.length?`<h3>Kiện hàng</h3>${arrived.map(parcel).join('')}${waiting.filter(s=>!s.ready_now).map(parcel).join('')}<div class="divider"></div>`:'')+pick+merge+`<h3>Hàng trên kệ</h3>${list.map(row).join('')}`;
}
/** A "Gộp" box was ticked: remember it and update the merged-order button without redrawing the rows. */
function whPick(box){
  const id=career(),picks=(ui.whPick??={})[id]??={};
  if(box.checked)picks[box.dataset.whPick]=true;else delete picks[box.dataset.whPick];
  const n=document.querySelectorAll('[data-wh-pick]:checked').length,b=document.querySelector('[data-wh-merge]');
  if(b){b.querySelector('[data-wh-merge-n]').textContent=String(n);b.disabled=!n||stockVans(room())>=SHIP_CAP;b.classList.toggle('primary',!!n);}
}
async function whMerge(){
  const c=room(),id=career(),desk=c.stock_desk||{},sups=desk.suppliers||[],picked=ui.whSup?.[id],supId=sups.some(s=>s.id===picked)?picked:(desk.default||sups[0]?.id),sup=sups.find(s=>s.id===supId)||{factor:1,name:'nhà cung cấp',quote:{}};
  const items=[...document.querySelectorAll('[data-wh-pick]:checked')].map(b=>b.dataset.whPick);
  if(!items.length){toast('Tick “Gộp” ở ít nhất một mã nhé.',true);return;}
  if(items.length>MERGE_CAP){toast(`Một đơn gộp tối đa ${MERGE_CAP} mã.`,true);return;}
  const lines=[];
  for(const item of items){const qty=Number(document.getElementById('qty-'+item)?.value);if(!Number.isInteger(qty)||qty<1||qty>6){toast('Mỗi mã từ 1 đến 6 món.',true);return;}lines.push({item,qty});}
  const cost=lines.reduce((n,l)=>n+Math.max(1,Math.ceil(product(l.item).cost*l.qty*sup.factor)),0);
  const what=lines.map(l=>`${l.qty} × ${product(l.item).name}`).join(', ');
  if(cost>c.money){toast(`Quỹ còn ${fmt(c.money)} xu, đơn gộp cần ${fmt(cost)} xu.`,true);return;}
  if(await confirmAction(`Đặt đơn gộp ${lines.length} mã?`,`${what} từ ${sup.name}: trả ${fmt(cost)} xu một lần. Dự kiến nhận: ${sup.quote?.eta_label||sup.window||''}, cả đơn một chuyến. Hàng chỉ cộng kho sau khi bạn đếm nhận từng kiện.`,'Đặt đơn gộp')&&await cmd('order_stock',{lines,supplier:supId}))(ui.whPick??={})[id]={};
}
/** Quantity with − / + (44 px) around the number for a stock-desk row; disabled when the shelf is full. */
const whQty=(p,max,qty)=>`<span class="wh-qty"><button type="button" class="btn ghost" data-wh-step="-1" aria-label="Bớt một"${max>1?'':' disabled'}>−</button><input class="input" type="number" id="qty-${p.id}" min="1" max="${Math.max(1,max)}" value="${qty}" inputmode="numeric" aria-label="Số nhập ${esc(p.name)}"${max?'':' disabled'}><button type="button" class="btn ghost" data-wh-step="1" aria-label="Thêm một"${max>1?'':' disabled'}>+</button></span>`;
const whLabel=(q,cost,money)=>cost>money?`Thiếu ${fmt(cost-money)} xu`:`Đặt ${q} · ${fmt(cost)} xu`;
/** The order button of a stock-desk row as the number changes: what the parcel costs, or the shortfall (disabled). */
function whBill(input){
  const b=input?.closest('.inv-row')?.querySelector('[data-wh-order][data-cost]');if(!b)return;
  const q=Math.max(1,Math.min(Number(input.max)||1,Math.floor(Number(input.value))||1)),cost=Math.max(1,Math.ceil(Number(b.dataset.cost)*q*Number(b.dataset.factor))),money=Number(b.dataset.money)||0;
  b.disabled=cost>money;b.textContent=whLabel(q,cost,money);
}
async function whOrder(item){
  const c=room(),id=career(),desk=c.stock_desk||{},sups=desk.suppliers||[],picked=ui.whSup?.[id],supId=sups.some(s=>s.id===picked)?picked:(desk.default||sups[0]?.id),sup=sups.find(s=>s.id===supId)||{factor:1,name:'nhà cung cấp',quote:{}};
  const qty=Number(document.getElementById('qty-'+item)?.value);
  if(!Number.isInteger(qty)||qty<1||qty>6){toast('Mỗi lần đặt từ 1 đến 6 món.',true);return;}
  const p=product(item),cost=Math.max(1,Math.ceil(p.cost*qty*sup.factor));
  if(await confirmAction('Đặt một kiện hàng?',`${qty} × ${p.name} từ ${sup.name}: trả ${fmt(cost)} xu ngay. Dự kiến nhận: ${sup.quote?.eta_label||sup.window||''}. Chỉ cộng kho sau khi kiện tới và bạn đếm nhận.`,'Đặt hàng'))await cmd('order_stock',{item,qty,supplier:supId});
}
function phLotBook(){
  const care=careData();if(!care)return empty('Sổ lô mở khi quầy mở ca','','box');
  const slot=s=>{const r=s.row;
    if(!r)return `<li class="wh-slot"><div class="grow"><b>${esc(s.label)}</b><small>${s.can_log?'Chưa ghi':'Ghi '+esc(s.hint)}</small></div>${commandButton('🌡️ Ghi nhiệt độ','ph_fridge_log',{slot:s.id},s.can_log?'primary':'ghost',!s.can_log)}</li>`;
    const out=!!r.cause,fix=out&&!r.fix;
    return `<li class="wh-slot${out?(fix?' warn':r.ok?' ok':' bad'):' ok'}"><div class="grow"><b>${esc(s.label)} · ${esc(r.at)}</b><small>${out?esc(r.clue||''):'Trong khoảng 2–8°C'}</small>${out&&r.fix?`<small>${r.ok?'✓ Đã xử lý':'✗ Xử lý chưa đúng: hộp lạnh phải rút'}</small>`:''}</div><b class="wh-temp">${esc(r.temp_label)}</b>`+
      (fix?`<div class="wh-fix">${commandButton('🚪 Đóng kín cửa, đo lại','ph_fridge_fix',{slot:s.id,fix:'door'},'ghost')}${confirmBtn('🔌 Tủ dự phòng · gọi thợ','ph_fridge_fix',{slot:s.id,fix:'move'},'Chuyển hộp lạnh sang tủ dự phòng và gọi thợ điện: 15 xu.','ghost')}</div>`:'')+`</li>`;};
  const lots=[...new Set(care.batches.map(b=>b.lot))];
  const batch=b=>{const [label,tone]=FLAG_LABEL[b.flag]||[b.days_left<=0?'Hết hạn sau hôm nay':b.days_left<=2?`Còn ${b.days_left} ngày`:`Còn ${b.days_left} ngày`,b.days_left<=2?'amber':'green'];
    return `<li class="wh-batch${b.flag?' bad':''}"><div class="grow"><b>${esc(b.id)} × ${b.qty}</b><small>HSD ngày ${b.exp}${b.recalled?` · ${esc(b.recalled)}`:''}</small></div>${dwState(label,tone)}${b.flag?commandButton('Rút khỏi kệ','ph_lot_pull',{batch:b.id},'small primary',!room().open):''}</li>`;};
  const notices=care.notices?.length?`<ul class="cb-alerts">${care.notices.map(n=>`<li>📢 Ngày ${n.day}: ${esc(n.text)}</li>`).join('')}</ul>`:'';
  return `${notices}<section class="card wh-fridge" aria-label="Sổ nhiệt độ tủ mát"><div class="dw-sec-head"><h3>🧊 Tủ mát · 2–8°C</h3><span class="dw-count${care.fridge_score>=85?' ok':''}">Sổ 7 ngày ${care.fridge_score}%</span></div><ul class="wh-slots">${care.fridge.slots.map(slot).join('')}</ul></section>`+
    `<section class="dw-sec" aria-label="Sổ lô"><div class="dw-sec-head"><h3>Sổ lô · hạn dùng</h3>${care.waste?`<span class="dw-count">Hao hụt ${fmt(care.waste)} xu</span>`:''}</div><p class="dw-hint">Hộp quá hạn, bị thu hồi hay hỏng lạnh còn trên kệ thì cả mã đó không xuất được.</p>${lots.map(l=>`<div class="dw-lotgroup"><h4><b>${esc(l)}</b> ${esc(product(l).name||'')}</h4><ul class="wh-batches">${care.batches.filter(b=>b.lot===l).map(batch).join('')}</ul></div>`).join('')||'<p class="dw-empty">Kệ trống.</p>'}</section>`;
}
function phRegulars(){
  const care=careData();if(!care)return empty('Sổ khách quen mở khi quầy mở ca','','people');
  const card=r=>{const n=r.npc?npc(r.npc):null,short=r.shelf<r.qty;
    const face=n?portrait(n,44):`<span class="cb-emoji" aria-hidden="true">${esc(r.emoji)}</span>`;
    const chip={here:dwState('Đang ở quầy','green'),call:dwState('Tới lịch gọi nhắc','amber'),called:dwState(`Đã nhắc · ngày ${r.due}`,'blue'),later:dwState(`Hẹn ngày ${r.due}`)}[r.state];
    const dots=r.hist.map(([d,k])=>`<i class="cb-dot ${k}" title="Ngày ${d}: ${{ok:'đúng hẹn',late:'tới trễ',missed:'lỡ đợt'}[k]}"></i>`).join('');
    const act=r.state==='here'?confirmBtn(`Giao ${r.qty} × ${esc(r.lot)} · +30 xu`,'ph_care_hand',{who:r.id},`Giao ${r.qty} × ${r.lot} cho ${r.name} theo phiếu lặp lại?`,'primary',!!r.block||short||!room().open)
      :r.state==='call'?commandButton('📞 Gọi nhắc lấy thuốc','ph_care_call',{who:r.id},'primary',!room().open):'';
    const warn=r.state==='here'&&(r.block||short)?`<p class="wh-bad">${esc(r.block||`Kệ còn ${r.shelf} hộp, cần ${r.qty}: đặt chuyến phân phối.`)}</p><div class="dw-acts">${r.block?`<button type="button" class="btn ghost" data-wh-tab="lots">🧊 Mở sổ lô</button>`:`<button type="button" class="btn ghost" data-wh-tab="stock">📦 Đặt hàng</button>`}</div>`:'';
    return `<article class="card cb-card"><div class="cb-head">${face}<div class="grow"><strong>${esc(r.name)}</strong><small>${esc(r.note)}</small></div>${chip}</div><div class="cb-meta"><span>${esc(r.lot)} × ${r.qty} · mỗi ${r.every} ngày</span><span>Kệ có ${r.shelf}</span>${hearts(r.trust)}${dots?`<span class="cb-dots" aria-label="Các đợt gần đây">${dots}</span>`:''}</div>${warn}${act?`<div class="dw-acts">${act}</div>`:''}</article>`;};
  return `<p class="dw-hint">Gọi nhắc từ hôm trước ngày hẹn thì khách ghé đúng ngày; không nhắc, khách tới trễ một ngày. Quá hạn là lỡ đợt.</p>${care.regulars.map(card).join('')}`;
}
function clientBoard(){
  const care=careData(),head=header('Tủ hồ sơ khách',care?`Một tháng sổ = ${care.month} ngày · khóa sổ trong 3 ngày`:'','SỔ SÁCH KHÁCH NHỎ');
  if(!care)return head+`<div class="sheet-body cb">${empty('Tủ hồ sơ mở khi bắt đầu ca','','book')}</div>`;
  const open=room().open;
  const card=cl=>{const b=cl.book,face=cl.npc?portrait(npc(cl.npc),44):`<span class="cb-emoji" aria-hidden="true">${esc(cl.emoji)}</span>`;let body='';
    if(!b)body=`<p class="dw-hint">Sổ tháng sau tới ngày ${cl.next_arrive}.</p>`;
    else{const st=b.late?dwState('Trễ hạn','danger'):!b.opened?dwState('Chờ mở','amber'):b.gap?dwState('Thiếu phiếu','amber'):dwState('Đang soát','blue');
      const due=`Hạn khóa ngày ${b.due}${b.days_left>0?` · còn ${b.days_left} ngày`:b.days_left===0?' · hôm nay':' · đã quá hạn'}`;
      if(!b.opened)body=`<div class="cb-row">${st}<span>${due}</span></div><div class="dw-acts">${commandButton(`📂 Mở hộp sổ tháng ${b.m+1}`,'ac_book_open',{client:cl.id},'primary',!open)}</div>`;
      else{const checks=`<div class="cb-checks" role="group" aria-label="Các bước soát">${b.checks_all.map(k=>{const n=b.found[k.id];return k.done?`<div class="cb-check done"><span aria-hidden="true">${k.emoji}</span><span><b>${esc(k.label)}</b><small>${n?`${n} chỗ sai · đã sửa`:'Không có sai sót'}</small></span></div>`
            :`<button type="button" class="cb-check${k.hint?' hint':''}" data-command="ac_book_check" data-payload="${esc(JSON.stringify({client:cl.id,check:k.id}))}"${open?'':' disabled'}><span aria-hidden="true">${k.emoji}</span><span><b>${esc(k.label)}</b><small>${k.hint?'⭐ Hồ sơ ghi: nên soát':'Chưa soát'}</small></span></button>`;}).join('')}</div>`;
        const chase=b.missing&&!b.source?(b.chase===0?commandButton(`📎 Xin khách gửi ${b.missing} phiếu thiếu`,'ac_book_chase',{client:cl.id},'ghost',!open):b.can_follow?commandButton('📞 Gọi nhắc lại','ac_book_chase',{client:cl.id},'primary',!open):`<p class="dw-hint">Khách hẹn gửi ngày ${b.promise}.</p>`):'';
        const close=b.gap?confirmBtn('Khóa kèm ghi chú thiếu','ac_book_close',{client:cl.id,note:'missing_note'},`Khóa sổ ${cl.name} tháng ${b.m+1} kèm ghi chú thiếu ${b.missing} phiếu? Thù lao 75%.`,'ghost',!open)
          :confirmBtn(`🔒 Khóa sổ tháng ${b.m+1}`,'ac_book_close',{client:cl.id,note:'full'},`Khóa sổ ${cl.name} tháng ${b.m+1}? Lỗi ở bước chưa soát sẽ bị trừ thù lao.`,'primary',!open);
        body=`<div class="cb-row">${st}<span>${due}</span></div><p class="cb-facts">${b.receipts} phiếu${b.missing?` · sao kê thiếu ${b.missing} phiếu${b.source?' (đã nhận)':''}`:' · đủ phiếu'}</p>${checks}<div class="dw-acts">${chase}${close}</div>`;}}
    const habits=cl.known.length?`<ul class="cb-habits">${cl.known.map(h=>`<li>📌 ${esc(h.text)}</li>`).join('')}</ul>`:'';
    const more=cl.unknown?`<small class="cb-more">Còn ${cl.unknown} thói quen chưa biết.</small>`:'';
    const past=cl.months.length?fold(`Các tháng trước · ${cl.months.length}`,`<ul class="cb-past">${cl.months.map(m=>`<li>Tháng ${m.m+1}: ${esc(care.grades[m.closed.grade]||'')} · ${fmt(m.closed.fee)} xu</li>`).join('')}</ul>`):'';
    return `<article class="card cb-card"><div class="cb-head">${face}<div class="grow"><strong>${esc(cl.name)}</strong><small>${esc(cl.owner)} · ${fmt(cl.fee)} xu/tháng</small></div>${hearts(cl.trust)}</div>${habits}${more}${body}${past}</article>`;};
  const alerts=care.alerts?.length?`<ul class="cb-alerts">${care.alerts.map(a=>`<li>${esc(a)}</li>`).join('')}</ul>`:'';
  return head+`<div class="sheet-body cb">${alerts}${care.clients.map(card).join('')}</div>`+footer('',button('Sổ việc','queue',{},'ghost small'));
}
const CS_STATUS={new:'Chờ xác minh',understood:'Đang kiểm hồ sơ',proposed:'Đã có phương án',awaiting_confirmation:'Có kết quả · cần kiểm',resolved:'Chờ đóng vụ',handed_over:'Chị Mai đang xem'};
function followBoard(){
  const care=careData(),head=header('Bảng theo dõi',esc(care?.clock?.label||''),'VỤ NHIỀU NGÀY');
  if(!care)return head+`<div class="sheet-body cb">${empty('Bảng theo dõi mở khi bắt đầu ca','','clipboard')}</div>`;
  const h=care.handover&&care.handover.day===room().day?care.handover:null;
  const hand=h?`<section class="card cb-hand${h.read?' read':''}" aria-label="Bàn giao"><h3>🗂️ Bàn giao từ ca hôm qua</h3>${h.night.length?`<ul class="cb-alerts">${h.night.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:''}<ul class="cb-list">${h.rows.map(r=>`<li><span class="grow"><b>${esc(r.name)}</b> · ${esc(r.title)}<small>${esc(r.next)}${r.eta?` · dự kiến ${esc(r.eta)}`:''}</small></span>${button('Mở','job',{task:r.task},'ghost small')}</li>`).join('')}</ul>${h.read?'<p class="dw-ok">✓ Đã đọc bàn giao</p>':commandButton('Đã đọc bàn giao','cs_handover_read',{},'primary')}</section>`:'';
  const alerts=care.alerts?.length?`<ul class="cb-alerts">${care.alerts.map(a=>`<li>${esc(a)}</li>`).join('')}</ul>`:'';
  const caseRow=r=>{const st=r.desk?'Hồ sơ bàn giấy tờ':r.status==='executing'?`Chờ ${r.wait_label||'đầu mối'}${r.eta?` · ${r.eta}`:''}`:CS_STATUS[r.status]||'';
    const chips=[r.days_open?dwState(`Ngày thứ ${r.days_open+1}`):'',r.sla_label?dwState(`⏳ Phản hồi đầu: còn ${esc(r.sla_label)}`,'amber'):'',r.upd_label?dwState(`📞 Cập nhật: ${esc(r.upd_label)}`,r.upd_label==='đã gọi'?'green':r.upd_label==='trễ hẹn'?'danger':'amber'):'',r.repeat?dwState(`Gọi lần ${r.repeat+1}`,'blue'):''].join('');
    return `<li class="cb-case${r.late?' late':''}"><div class="grow"><span><b>${esc(r.name)}</b> · ${esc(r.title)}</span><small>${esc(st)}${r.tone_label?` · khách ${esc(r.tone_label)}`:''}</small>${chips?`<span class="cb-chips">${chips}</span>`:''}</div>${button('Mở vụ','job',{task:r.task},'small')}</li>`;};
  const cases=`<section class="dw-sec" aria-label="Vụ đang mở"><div class="dw-sec-head"><h3>Vụ đang mở</h3><span class="dw-count">${care.board.length}</span></div>${care.board.length?`<ul class="cb-cases">${care.board.map(caseRow).join('')}</ul>`:'<p class="dw-empty">Không còn vụ nào mở.</p>'}</section>`;
  const trend=care.trend?.length?`<section class="card cb-trend" aria-label="Mức hài lòng"><h3>Mức hài lòng 7 ngày</h3><ol class="cb-bars" aria-label="Theo ngày">${care.trend.map(x=>`<li aria-label="Ngày ${x.day}: ${(x.avg10/10).toFixed(1).replace('.',',')} sao"><span class="cb-bar"><i style="height:${Math.max(6,Math.round((x.avg10-10)/40*100))}%"></i></span><b>${(x.avg10/10).toFixed(1).replace('.',',')}</b><small>N${x.day}</small></li>`).join('')}</ol></section>`:'';
  const people=care.people?.length?`<section class="dw-sec" aria-label="Thẻ khách"><h3>Thẻ khách quen của trạm</h3>${care.people.slice(0,6).map(personCard).join('')}</section>`:'';
  return head+`<div class="sheet-body cb">${hand}${alerts}${cases}${trend}${people}</div>`+footer('',room().open?commandButton('⏳ Chờ thêm 20 phút','advance',{},'ghost small'):'');
}
function personCard(p){
  const n=npc(p.npc);
  return `<article class="card cb-card cb-person"><div class="cb-head">${portrait(n,40)}<div class="grow"><strong>${esc(p.name||n.display_name)}</strong><small>${p.n} vụ đã xử lý${p.open?` · ${p.open} vụ đang mở`:''}</small></div></div>${p.last?.length?`<ul class="cb-past">${p.last.slice().reverse().map(x=>`<li>Ngày ${x.day}: ${esc(x.title)} · ${esc(x.note)}${x.stars?` · ${x.stars}★`:''}</li>`).join('')}</ul>`:''}</article>`;
}
/* Support call: the customer answers in character (AI when allowed, scripted otherwise);
   tone, SLA and satisfaction are decided by the server rules only. */
let csCallPending=null;
function csCallPanel(t){
  if(!t.identity||ended(t))return '';
  const n=npc(t.npc),wait=csCallPending?.task===t.id,left=t.call_left??0;
  const lines=(t.call||[]).map(m=>m.who==='player'?`<div class="bubble user"><div>${esc(m.text)}</div></div>`
    :`<div class="bubble npc${m.mode==='ai'?' ai':''}">${m.mode==='ai'?`<span class="ai-badge" title="${esc('Lời gốc: '+(m.canonical||''))}" aria-label="Câu trả lời do AI viết">AI</span>`:''}<div>${esc(m.text)}</div></div>`).join('');
  const pending=wait?`<div class="bubble user pending"><div>${esc(csCallPending.text)}</div></div><div class="bubble npc typing" role="status" aria-label="${esc(n.display_name)} đang trả lời…"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span></div>`:'';
  const tone={vui:'green',binh:'blue',lo:'amber',buc:'danger'}[t.tone]||'';
  const chips=(t.picks||[]).map(p=>`<button type="button" class="btn ghost small" data-cs-pick="${esc(p.id)}" data-task="${esc(t.id)}"${wait||!left||!room().open?' disabled':''}>${esc(p.label)}</button>`).join('');
  const folded=uiClean()&&!lines&&!pending;   // clean layout: a call not started yet is one line ("📞 Gọi Lan · Khách lo lắng ›")
  return `<section class="dw-sec cs-call" aria-label="Cuộc gọi với ${esc(n.display_name)}">${folded?'<details class="cs-call-fold"><summary class="dw-sec-head">':'<div class="dw-sec-head">'}<h3>📞 Gọi ${esc(n.display_name)}</h3>${dwState('Khách '+esc(t.tone_label||''),tone)}${folded?'</summary>':'</div>'}`+
    `${lines||pending?`<div class="chat-messages cs-call-log" role="log" aria-live="polite"><div class="cs-call-rows">${lines}${pending}</div></div>`:uiClean()?uiTip('Báo tình trạng thật, xin lỗi khi khách phải chờ, hỏi thêm khi cần. Lời nói không tự hoàn tiền hay đổi phương án.','📞 Cuộc gọi','p'):'<p class="dw-hint">Báo tình trạng thật, xin lỗi khi khách phải chờ, hỏi thêm khi cần. Lời nói không tự hoàn tiền hay đổi phương án.</p>'}`+
    `<div class="quick-replies">${chips}</div><form class="chat-form cs-call-form" data-cs-call="${esc(t.id)}"><textarea id="cs-say-${esc(t.id)}" name="say" data-preserve rows="1" maxlength="200" required placeholder="Nói với ${esc(n.display_name)}…" aria-label="Lời nói với ${esc(n.display_name)}"></textarea><button type="submit" class="btn primary" aria-label="Nói"${wait||!left||!room().open?' disabled':''}>${icon('send',17)}<span>Nói</span></button></form>`+
    `<p class="cs-call-meta">${aiVoices()?`${icon('sparkle',13)} Khách trả lời bằng AI · đừng gõ thông tin thật · còn ${left} lượt nói hôm nay`:uiClean()?`<span aria-label="Còn ${left} lượt nói hôm nay">💬 ${left}</span>`:`Khách trả lời theo kịch bản · còn ${left} lượt nói hôm nay`}</p>${folded?'</details>':''}</section>`;
}
async function csCallSend(task,body){
  if(csCallPending||ui.busy)return;
  const t=room()?.tasks.find(x=>x.id===task);if(!t)return;
  csCallPending={task,text:body.text||(t.picks||[]).find(p=>p.id===body.pick)?.label||''};renderSheet();
  const run=()=>api.post('/api/ai/support_call',{career:'customer_care',task,...body,request_id:globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`,expected_revision:api.revision},20000);
  const post=()=>{const job=api.queue.then(run,run);api.queue=job.catch(()=>{});return job;};
  try{
    let data;
    try{data=await post();}catch(error){if(error.status===409&&error.data?.state){api.accept(error.data);data=await post();}else throw error;}
    api.accept(data);const r=data.result||{};
    if(r.kept)toast(r.kept,'good');else if(r.tone_moved)toast(`${npc(t.npc).display_name} ${r.tone_moved==='dịu hơn'?'dịu giọng hơn':'căng hơn'}.`,r.tone_moved==='dịu hơn'?'good':'hint');
    for(const note of new Set(r.effects||[]))toast(note);
  }catch(error){
    if(!error.status)await cmd('cs_call',{task,...body},{quiet:true}); // AI route unreachable: the scripted line
    else toast(error.message||'Chưa gọi được.',true);
  }finally{csCallPending=null;renderSheet();}
}
document.addEventListener('click',async e=>{
  const el=e.target.closest?.('[data-wh-tab],[data-wh-sup],[data-wh-order],[data-wh-open],[data-wh-step],[data-wh-pick],[data-wh-merge],[data-cs-pick]');if(!el||el.disabled||ui.busy)return;
  if(el.dataset.whPick)whPick(el);
  else if(el.dataset.whMerge)await whMerge();
  else if(el.dataset.whStep){const input=el.parentElement.querySelector('input');if(input){input.value=String(Math.max(1,Math.min(Number(input.max)||1,(Math.floor(Number(input.value))||1)+Number(el.dataset.whStep))));whBill(input);}}
  else if(el.dataset.whTab){ui.whTab=el.dataset.whTab;renderSheet(false);}
  else if(el.dataset.whSup){(ui.whSup??={})[career()]=el.dataset.whSup;renderSheet();}
  else if(el.dataset.whOrder)await whOrder(el.dataset.whOrder);
  else if(el.dataset.whOpen!==undefined){ui.whTab=el.dataset.whOpen||ui.whTab;openSheet('warehouse');}
  else if(el.dataset.csPick)await csCallSend(el.dataset.task,{pick:el.dataset.csPick});
});
document.addEventListener('submit',async e=>{
  const f=e.target;if(!(f instanceof HTMLFormElement)||!f.dataset.csCall)return;e.preventDefault();
  const input=f.querySelector('textarea'),text=input?.value.trim();if(!text)return;input.value='';await csCallSend(f.dataset.csCall,{text});
});
function albumView(){const c=room();return header('Kỷ niệm','Giữ 6 ảnh gần nhất.','ALBUM')+`<div class="sheet-body"><div class="row spread"><span></span>${button(icon('camera',16)+' Chụp góc hiện tại','photo',{},'primary')}</div><div class="album-grid space-top">${c.album.map(p=>`<article class="polaroid"><img src="${esc(p.image)}" alt="${esc(p.title)}" loading="lazy"><p>${esc(p.title)}</p><div class="row spread"><small>Ngày ${p.day} · ${esc(meta().place)}</small>${button(icon('download',13),'downloadPhoto',{id:p.id},'ghost small')}</div></article>`).join('')||empty('Một album chưa có ảnh','','camera')}</div>${c.quests_claimed.length?`<h3 class="space-top">Kỷ vật câu chuyện</h3>${c.quests_claimed.map(id=>`<div class="memory">${icon('award',17)} ${esc(api.content.quests.find(q=>q.id===id).keepsake)}</div>`).join('')}`:''}${api.state.marriage?.spouse?'<div data-wed-album></div>':''}</div>`;
}
const CLOSE_LABELS={markdown_sold:'Bánh giảm giá đã bán',markdown_income:'Thu từ bánh giảm giá (xu)',discarded:'Món phải bỏ',wilted:'Cành hoa héo',wilted_value:'Giá trị hoa héo (xu)',sales:'Doanh thu quầy (xu)',ledger_total:'Tổng sổ ghi nợ (xu)',repaired:'Máy đã sửa xong',returned:'Máy trả lại khách',hazards:'Lỗi an toàn',expired_units:'Nông sản quá hạn',eggs_tomorrow:'Trứng còn trong ổ',hungry_hens:'Gà chưa được cho ăn',ripe_tomorrow:'Luống chín ngày mai',delivered:'Đơn đã giao',failed:'Giao thất bại',refused:'Đơn đã từ chối nhận',km:'Quãng đường (ô phố)',fees:'Phí giao (xu)',fuel:'Xăng còn (%)',settled_at_close:'COD tự nộp cuối ca (xu)',food_cancelled:'Đơn đồ ăn bị hủy',arrived:'Khách nhận phòng',walked:'Khách phải chuyển chỗ',moved:'Khách đổi phòng',dirty:'Phòng cần dọn',staying:'Bé đang ở lại',free:'Chuồng trống',posted:'Bút toán đã ghi',dossiers:'Hồ sơ hoàn tất',milestones:'Mốc kỳ kế toán',balanced:'Sổ cân đối'};
/** Career-specific part of the day summary: module.summary(data,x) or a generic list. */
function careerCloseSummary(){
  const data=room().shift_summary?.career??room().shift_summary?.experiences?.counter;if(!data||typeof data!=='object')return '';
  const mod=careerUI(career());
  if(mod?.summary){try{return mod.summary(data,careerContext(env()))||'';}catch(error){console.error(error);}}
  // The pharmacy: "🌅 Ngày mai" first (regulars due, calls to make, boxes to pull, the shelf; one way to Kho & sổ
  // quầy), the day's figures folded under it (careers/tomorrow_kit.js; the plain book below until it is in).
  if(career()==='pharmacy'&&L.tm.use()){
    try{const c=room(),alerts=(careData()?.alerts||[]).filter(a=>typeof a==='string').map(esc),shelf=L.tm.m.shelfLines(c,api.content.lots.filter(l=>l.status==='available'));
      return L.tm.m.tomorrowCard(careerContext(env()),data,{plan:alerts,shelf,kho:'warehouse',go:alerts.length&&!shelf.length?{label:'📦 Mở Kho & sổ quầy',action:'warehouse'}:null,labels:CLOSE_LABELS});}
    catch(error){console.error(error);}
  }
  const show=v=>typeof v==='boolean'?(v?'Có':'Không'):Array.isArray(v)?v.map(x=>typeof x==='object'?(x.name||x.title||x.label||''):x).filter(Boolean).join(', '):typeof v==='number'?fmt(v):String(v);
  const rows=Object.entries(data).filter(([k,v])=>CLOSE_LABELS[k]&&!(v===0||v===false&&k!=='balanced'||Array.isArray(v)&&!v.length)).map(([k,v])=>`<div class="kv-row"><span>${esc(CLOSE_LABELS[k])}</span><b>${esc(show(v))}</b></div>`).join('');
  const lines=[...(Array.isArray(data.lines)?data.lines:[]),...(typeof data.note==='string'&&data.note?[data.note]:[])].filter(x=>typeof x==='string');
  if(!rows&&!lines.length)return '';
  return `<article class="card space-top"><h4 class="section-title">${icon('clipboard',15)} Sổ nghề hôm nay</h4>${rows?`<div class="kv">${rows}</div>`:''}${lines.length?`<ul class="small">${lines.map(l=>`<li>${esc(l)}</li>`).join('')}</ul>`:''}</article>`;
}
/** End of day: headline, three big numbers, what needs you, then the details. One primary CTA in the foot. */
function summaryView(){
  const c=room(),s=c.shift_summary,m=meta(),eve=!c.open&&eveningDue();
  const next=c.open?button('Về quầy','close',{},'primary big'):eve?button('🌙 Ăn tối, đi ngủ','evening',{},'primary big'):button(icon('play',15)+' Bắt đầu ngày '+dayNo(c),'start',{},'primary big');
  if(!s)return header('Mình khép ca nhé?','','TỔNG KẾT NGÀY')+`<div class="sheet-body">${empty('Chưa có ngày nào khép lại','','sun')}</div>`+footer('',next);
  const rv=s.reviews||{},job=s.job||null,ops=s.operations,net=Number(s.net)||0,own=careerUI(career())?.daySummary?.(s,careerContext(env()))||null;
  const pagoda=career()==='pagoda';   // visitors' impressions at the pagoda (game/pagoda_voice.py)
  const stat=(cls,big,label,sub='')=>`<div class="sum-stat ${cls}"><strong>${big}</strong><small>${label}</small>${sub?`<em${sub.startsWith('<span')?' class="ck-chips"':''}>${sub}</em>`:''}</div>`;
  const stats=`<div class="sum-stats">${stat(net>=0?'good':'bad',`${net>=0?'+':'−'}${fmt(Math.abs(net))}<span> xu</span>`,'Thay đổi trong ca',`<span class="ck-delta up">thu ${fmt(s.income)}</span><span class="ck-delta down">chi ${fmt(s.cost)}</span>`)}${stat('',`${s.completed}`,'Việc đã xong',s.carried?`${s.carried} việc để mai`:'')}${stat('star',rv.count?`★ ${rv.average}`:'—',rv.count?`${rv.count} ${pagoda?'cảm nhận':'đánh giá'} mới`:pagoda?'Chưa có cảm nhận mới':'Chưa có đánh giá mới')}</div>`;
  const notes=[];
  if(job?.boss)notes.push(`<article class="sum-boss"><span class="eyebrow">Một cuộc gặp may mắn</span><h3>${esc(job.boss.org)} · ${esc(job.boss.title)}</h3><p>${esc(job.boss.text)}</p>${button(icon('mail',15)+' Xem thư mời','bossOffer',{career:job.boss.career},'primary small')}</article>`);
  if(s.incidents&&L.inc.use())notes.push(L.inc.m.incidentSummary(s.incidents));
  if(s.happen&&L.happen.use())notes.push(L.happen.m.happenSummary(s.happen));
  if(s.abandon)notes.push(abandonSummary(s.abandon));
  if(s.promo&&L.promo.use())notes.push(L.promo.m.promoSummary(s.promo,career()));  // 🎖️ a good day, the review booked, the manager shift
  if(s.life)notes.push(lifeSummary(s.life));
  if(s.experiences?.tip_day?.count&&L.tips.use())notes.push(L.tips.m.tipSummary(s.experiences.tip_day));
  const jr=s.journey;
  // The wallet after the day, its moves as chips (owner 03/10 "chữ ít thôi": the title names the life day, the clock card the hour);
  // the 🔥 x3 day's bonus (summary.journey.x3, only when above 0) is a chip of its own.
  if(jr&&(jr.living||jr.upkeep||jr.salary||jr.x3))notes.push(notice(`<b>Ví còn ${fmt(jr.wallet)} xu</b><p class="ck-chips"><span class="ck-delta down">Phòng & cơm −${fmt(jr.living)}</span>${jr.upkeep?`<span class="ck-delta down">Nơi làm khác −${fmt(jr.upkeep)}</span>`:''}${jr.salary?`<span class="ck-delta up">Lương +${fmt(jr.salary)}</span>`:''}${jr.x3?`<span class="ck-delta up">🔥 x3 +${fmt(jr.x3)}</span>`:''}${jr.gift?`<span class="ck-delta up">🎁 Quà +${fmt(jr.gift)}</span>`:''}</p>${jr.wallet<0?'<p>Ví đang nợ: trả hết nợ thì câu chuyện mới đi tiếp.</p>':''}`,jr.wallet<0?'amber':'','bag'));
  if(job?.salary)notes.push(notice(`<b>Lương hôm nay +${fmt(job.salary)} xu</b>${job.result==='official'?'<p>Hết thử việc: bạn đã được ký hợp đồng chính thức! 🎉</p>':job.result==='extended'?'<p>Thử việc được gia hạn thêm 2 ngày. Cố lên nhé!</p>':job.probation?'<p>Đang thử việc: nhận 85% lương.</p>':''}`,'success','briefcase'));
  if(rv.open||(rv.count&&rv.weakest&&rv.average<4.5))notes.push(notice(pagoda?`${rv.count&&rv.weakest&&rv.average<4.5?`Khách thập phương nhắc nhiều nhất về <b>${esc(rv.weakest)}</b>.`:''}${rv.open?` ${rv.open} cảm nhận chờ hồi đáp.`:''}<br>${button('Xem cảm nhận','feedback',{filter:rv.open?'open':'all'},'small')}`:`${rv.count&&rv.weakest&&rv.average<4.5?`Khách góp ý nhiều nhất về <b>${esc(rv.weakest)}</b>.`:''}${rv.open?` ${rv.open} đánh giá chờ trả lời.`:''}<br>${button('Xem đánh giá','feedback',{filter:rv.open?'open':'all'},'small')}`,'amber','star'));
  if(ops?.unpaid)notes.push(notice(`<b>${esc(wordsFor(career()).books)}: còn ${fmt(ops.unpaid)} xu cần trả</b><p class="ck-chips">${ops.wages?`<span class="ck-delta flat">Lương ${fmt(ops.wages)}</span>`:''}${ops.utilities?`<span class="ck-delta flat">điện nước ${fmt(ops.utilities)}</span>`:''}${ops.rent_accrued?`<span class="ck-delta flat">thuê ${fmt(ops.rent_accrued)} xu</span>`:''}${ops.period?'<span class="ck-delta warn">vừa kết kỳ thuế</span>':''}</p>${button('Mở sổ thu chi','finance',{},'small')}`,'','mail'));
  // 🧾 A tax period closed today (operations.py on_close): the calculation, not just a bill (players asked "5k xu thuế ở đâu ra?").
  if(ops?.period){const p=ops.period;notes.push(notice(`<b>🧾 Kết kỳ thuế ngày ${fmt(p.start)}–${fmt(p.end)}</b><p>${esc(T(career(),'revenue'))} cả kỳ ${fmt(p.revenue)} xu × ${fmt(p.rate)}% = <b>${fmt(p.tax)} xu thuế</b> (làm tròn lên). Mặt bằng cả kỳ ${fmt(p.rent)} xu. Hai khoản nằm trong ${esc(wordsFor(career()).books)} → Thu chi, hạn đóng ngày ${fmt(p.end+2)}.</p>${button('Mở sổ thu chi','finance',{},'small')}`,'amber','mail'));}
  // Hired staff (operations.py on_close): what each one did today, or why not (no shift, paused by an open incident),
  // and what their finished jobs earned the shop (staff_bonus, one cash-book row; absent from older servers).
  const team=ops?.staff||[],held=team.some(t=>t.paused);
  if(team.length)notes.push(notice(`<b>Đội hôm nay</b><p>${team.map(t=>`<b>${esc(t.name)}</b> ${[t.shift?`<span>${fmt(t.jobs)} việc</span>`:t.paused?'':'<span>không vào ca</span>',t.paused?'<span>tạm dừng vì còn sự cố đang mở</span>':''].filter(Boolean).join(', ')}`).join(' · ')}${ops.staff_bonus?` · <b>+${fmt(ops.staff_bonus)} xu thưởng</b>`:''}</p>${held?button('Xem nhân viên','staff',{},'small'):''}`,held?'amber':'','people'));
  const details=`<details class="sum-more space-top"><summary>Chi tiết cả ngày</summary>${experienceSummary(c)}<div class="kv"><div class="kv-row"><span>Xu thu vào</span><b>+${fmt(s.income)}</b></div><div class="kv-row"><span>Xu đã chi trong ca</span><b>−${fmt(s.cost)}</b></div><div class="kv-row"><span>Chuyện đã xử lý</span><b>${s.events}</b></div></div></details>`;
  // A career with its own day page (the air crew's flight log) replaces the headline and the big numbers; the notes stay shared.
  return header(own?.title||`Ngày ${s.journey?.life_day??s.day} đã khép lại`,esc(c.life.shop_name||m.place),own?.eyebrow||'TỔNG KẾT NGÀY')+`<div class="sheet-body summary-v6">${own?own.top:`<div class="sum-hero"><span class="sum-sun" aria-hidden="true">${icon('sun',34)}</span><p>${esc(s.headline||'Một ngày nữa đã có chuyện để nhớ.')}</p></div>${stats}${clockSummary(s)}${pnlFold(s)}`}${notes.length?`<div class="stack space-top">${notes.join('')}</div>`:''}${careerCloseSummary()}${accountNudge(env())}${details}</div>`+footer('',button('Đọc lời nhắn','phone',{},'ghost')+next);
}
/** 🌙 The evening between closing the day and the next morning (game/needs.py): what to eat, when to sleep. */
const eveningDue=()=>Boolean(api.state?.needs?.evening&&!api.state.needs.evening.chosen);
function eveningView(){
  const N=api.state.needs,E=N?.evening,c=room();
  const start=c&&!c.open?button(icon('sun',15)+' Bắt đầu ngày '+dayNo(c),'start',{},'primary big'):button('Về quầy','close',{},'primary big');
  if(!E)return header('Buổi tối','','BUỔI TỐI')+`<div class="sheet-body">${empty('Chưa tới buổi tối','Khép ca xong rồi chọn bữa tối và giờ đi ngủ nhé.','sun')}</div>`+footer('',start);
  return header(E.chosen?'Một ngày đã xong':'Tối nay thế nào?',E.finish?`Khép ca lúc ${esc(E.finish)} · Ngày sống ${E.life_day-1}`:'','BUỔI TỐI')+eveningBody(N,ui.eve,{start,wallet:api.state.journey?.wallet|0});
}
/** The day's profit/loss card (v4/pnl.js) folded to one line, "✓ Lãi/lỗ hôm nay: +N xu": the numbers above already
 * say how the day went; the full statement is one tap away. */
function pnlFold(s){
  if(!L.pnl.use())return '';const c=room(),card=L.pnl.m.pnlCard(env());if(!card)return '';
  let p=null;try{p=L.pnl.m.pnlOf(c,s.day);}catch{p=null;}
  const net=Number(p?.net)||0,office=p?.salaryOnly||(c.job?.required&&!p?.revenue);
  return `<details class="sum-pnl" data-fold="sum-pnl"><summary><span>✓ ${office?'Kết quả ngày làm':'Lãi/lỗ hôm nay'}</span><b class="${net>0?'good':net<0?'bad':''}">${net>0?'+':net<0?'−':''}${fmt(Math.abs(net))} xu</b></summary>${card}</details>`;
}
function helpView(){const guides={teacher:['Soạn ba bước: ví dụ → thử theo nhóm → câu hỏi cuối tiết.','Điểm danh đúng ghế có mặt; hỗ trợ theo nhu cầu từng bạn.','Đọc câu trả lời, đánh dấu đúng/chưa đúng và chọn phản hồi.','Khép tiết khi mọi bạn có mặt đã được hỗ trợ.'],tour_guide:['Chọn tuyến có đủ điểm đoàn thích và một nơi nghỉ.','Kiểm đủ khách; xác nhận vé trước khi đi.','Mỗi điểm: đọc chuyện, trả lời câu hỏi, tìm chi tiết chụp ảnh.','Kiểm lại đoàn trước khi đi tiếp, rồi gửi bưu thiếp.'],milk_tea:['Hỏi món khách gọi.','Chọn trà, vị và topping; chỉnh size, đường, đá.','Kiểm công thức trước khi dán nắp.','Giao ly, đọc review; chuẩn bị mẻ mới và theo dõi hạn dùng.'],mother_baby:['Hỏi khách cần gì.','Chọn đúng món và số lượng từ kệ.','Gói theo màu được yêu cầu, hoặc bỏ qua khi khách không cần.','Kiểm đơn ở Thu ngân, xác nhận giao.'],pharmacy:['Hỏi lại phiếu để biết mã và số lượng.','Chọn mã trong bộ lọc, đọc nhãn lô A hợp lệ.','Lấy đúng lượng, đánh dấu ba bước rồi kiểm khay.','Bàn giao hoặc chuyển cô Thu nếu ngoài phạm vi.'],accounting:['Mở từng bản gốc, đọc mã tham chiếu.','Loại bản trùng có căn cứ hoặc sửa số từ nguồn gốc.','Chọn phiếu và giao dịch tương ứng, ghép từng nhóm.','Khi mọi nguồn đều được ghép, kiểm và bàn giao.'],customer_care:['Xác minh mã đơn của khách.','Mở cả ba chứng cứ, không kết luận từ một nguồn.','Chọn phương án, xác nhận gửi việc tới đầu mối.','Qua hai nhịp, kiểm kết quả và đóng vụ.']};
  const m=meta(),steps=guides[career()]||[`${m.work||'Khách'}: chọn một việc đang chờ.`,`${m.station||'Bàn làm việc'}: tự tay làm từng bước rồi bàn giao.`,'Đánh giá: đọc lời khách và trả lời thật lòng.','Khép ca khi xong việc. Mai lại là một ngày mới.'];
  return header('Cách chơi',esc(m.place||''),'HƯỚNG DẪN')+`<div class="sheet-body"><div class="help-grid"><section class="card"><h3>${esc(m.short||m.name||'')}</h3><ol class="help-steps">${steps.map(s=>`<li>${esc(s)}</li>`).join('')}</ol>${button('Làm việc ngay '+icon('arrow',14),'job',{},'primary')}</section><section class="card"><h3>Chạm vào cảnh</h3><ul class="help-list"><li>Chạm sàn để đi, chạm người hoặc đồ vật để làm.</li><li>Bàn phím: WASD hoặc mũi tên để đi, E để dùng đồ gần nhất.</li></ul></section></div><h3 class="section-title">Muốn đổi nhịp?</h3><div class="chip-row">${button(icon('sparkle',15)+' Trò nhỏ','workshop',{},'ghost small')}${button(icon('award',15)+' Hộ chiếu','passport',{},'ghost small')}${button(icon('flag',15)+' Tình huống','situation',{},'ghost small')}${EXT.includes(career())?'':button(icon('book',15)+' Sổ tay','journal',{},'ghost small')}${button(icon('grid',15)+' Hành trình','home',{},'ghost small')}${button(icon('settings',15)+' Cài đặt','settings',{},'ghost small')}</div></div>`;}


/* Interaction controller. Native dialogs keep keyboard focus inside a workbench. */
let confirmResolve=null;
/** `money` (optional): {cost, pocket:'wallet'|'fund'} of a payment, for the "còn thiếu" line; without it a
 * confirm that talks money still shows the balances of the sheet under it (v4/money.js confirmMoney). */
function confirmAction(title,message,label='Xác nhận',money=null,opts=null){
  const under=[...document.querySelectorAll('dialog[open]')].filter(d=>d.id!=='confirmDialog').pop(),b=dialogBalances(under);
  // Not enough in the fund for an exact price: the server would refuse ("Chưa đủ xu"), so the button says so instead.
  const short=confirmShort(b,[title,message,label],money),yes=short?.sure?`<button type="button" class="btn primary" data-action="confirmYes" disabled>Thiếu ${fmt(short.miss)} xu</button>`:button(esc(label),'confirmYes',{},'primary');
  $('#confirmContent').innerHTML=`<span class="eyebrow">MỘT BƯỚC XÁC NHẬN</span><h2>${esc(title)}</h2>${message?`<p class="muted">${esc(message)}</p>`:''}${confirmMoney(b,[title,message,label],money)}<div class="row">${button('Để mình xem lại','confirmNo',{},'ghost')}${yes}</div>`;
  if(money?.payment){
    const {options,selected,cost}=money.payment;
    $('#confirmContent').querySelectorAll('.mn-confirm,.mn-short').forEach(x=>x.remove());
    const choices=document.createElement('div');choices.className='space-bottom';
    choices.innerHTML=`<label for="confirmPay">Nguồn thanh toán</label><select id="confirmPay" class="input">${options.map(x=>`<option value="${esc(x.id)}"${x.id===selected?' selected':''}>${esc(x.label)} · ${fmt(x.balance)} xu${x.ok?'':' · '+esc(x.why||'Chưa đủ số dư.')}</option>`).join('')}</select><p id="confirmPayHint" class="muted"></p><small class="muted">Lựa chọn chỉ áp dụng cho lần này. Đổi mặc định trong Ngân hàng.</small>`;
    $('#confirmContent').querySelector('.row').before(choices);
    const select=choices.querySelector('select'),yesButton=$('#confirmContent').querySelector('[data-action="confirmYes"]')||$('#confirmContent').querySelector('button.primary');
    const sync=()=>{const x=options.find(o=>o.id===select.value);yesButton.disabled=!x?.ok;yesButton.textContent=x?.ok?label:`Thiếu ${fmt(Math.max(0,cost-(x?.balance||0)))} xu`;choices.querySelector('#confirmPayHint').textContent=x?.ok?x.text:x?.why||'Chọn nguồn thanh toán.';};
    select.addEventListener('change',sync);sync();
  }
  $('#confirmDialog').showModal();
  // A second tap of a double tap must not land on "Đồng ý" (Xin nghỉ việc): the button wakes up a moment later.
  if(opts?.arm>0){const yesButton=$('#confirmContent').querySelector('[data-action="confirmYes"]');if(yesButton&&!yesButton.disabled){yesButton.disabled=true;setTimeout(()=>{if(yesButton.isConnected)yesButton.disabled=false;},opts.arm);}}
  return new Promise(resolve=>{confirmResolve=resolve;});
}
function inputPrompt(title,value,maxLength=100){
  $('#confirmContent').innerHTML=`<span class="eyebrow">GÓC CỦA BẠN</span><h2>${esc(title)}</h2><textarea class="input" id="cozy-prompt" maxlength="${maxLength}" rows="3">${esc(value)}</textarea><div class="row space-top">${button('Để sau','confirmNo',{},'ghost')}${button('Lưu','confirmYes',{},'primary')}</div>`;
  $('#confirmDialog').showModal();$('#cozy-prompt').focus();return new Promise(resolve=>{confirmResolve=ok=>resolve(ok?$('#cozy-prompt').value:null);});
}
function finishConfirm(value){const choice=$('#confirmPay');if(value&&choice)value=choice.value;$('#confirmDialog').close();confirmResolve?.(value);confirmResolve=null;document.body.append($('#toasts'));}
$('#confirmDialog').addEventListener('cancel',e=>{e.preventDefault();finishConfirm(false);});
$('#sheet').addEventListener('cancel',e=>{e.preventDefault();if(api.state?.current)closeSheet();});
/* Phone bottom sheets show a grab handle: dragging the sheet head down now really closes the sheet (it
 * used to do nothing). Only transform moves while dragging; past 90 px or a quick flick it slides away and
 * closes through the same 'cancel' path as Escape (so sheets that may not close yet stay put). */
{const d=$('#sheet'),HANDLE='.sheet-head,.home-top';let y0=0,t0=0,dy=0,pointer=null,timer=0;
  const release=()=>{const id=pointer;pointer=null;if(id!==null&&d.hasPointerCapture?.(id))d.releasePointerCapture(id);};
  const reset=()=>{clearTimeout(timer);timer=0;release();dy=0;d.style.transition='';d.style.transform='';};
  d.resetGesture=reset;
  d.addEventListener('pointerdown',e=>{const head=e.target.closest?.(HANDLE);if(layout()!=='phone'||e.pointerType==='mouse'||e.isPrimary===false||pointer!==null||d.scrollTop>2||!head||e.clientY-head.getBoundingClientRect().top>22||e.target.closest('button,a,input,select,textarea,summary,label'))return;reset();pointer=e.pointerId;y0=e.clientY;t0=e.timeStamp;dy=0;try{d.setPointerCapture(pointer);}catch{/* pointer already cancelled by native scrolling */reset();}});
  d.addEventListener('pointermove',e=>{if(pointer===null||e.pointerId!==pointer)return;dy=Math.max(0,e.clientY-y0);d.style.transition='none';d.style.transform=dy?`translateY(${dy}px)`:'';},{passive:true});
  const end=e=>{if(pointer===null||e.pointerId!==pointer)return;release();const flick=dy>40&&dy/Math.max(1,e.timeStamp-t0)>.5;d.style.transition='transform .2s ease-out';
    if(dy>90||flick){d.style.transform='translateY(100%)';timer=setTimeout(()=>{reset();if(d.open)d.dispatchEvent(new Event('cancel',{cancelable:true}));},190);}
    else{d.style.transform='';timer=setTimeout(reset,220);}};
  d.addEventListener('pointerup',end);
  d.addEventListener('pointercancel',e=>{if(e.pointerId===pointer)reset();});
  d.addEventListener('lostpointercapture',e=>{if(e.pointerId===pointer)reset();});
  d.addEventListener('close',()=>{if(!d.open)reset();});
  window.addEventListener('blur',reset);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)reset();});}
$('#sheet').addEventListener('close',()=>{document.body.append($('#toasts'));
  // The close event is async: the sheet may already be reopened with another view.
  if($('#sheet').open)return;
  if(ui.view){ui.view=null;ui.ai={};world.paused=ui.paused;}
  // Rail/dock highlight follows the open sheet.
  if(api.state&&api.state.current)renderMain();});
/** The career's how-to line in the scene's speech bubble, a few words of it (the bubble holds three short lines). */
const greeting=()=>toastHead(String(i18nT(String(meta().greeting||'')))).head;
async function start(){if(needsJob()){openSheet('jobapp');return;}const r=await cmd('start_day');if(r){ui.task=null;closeSheet();world.say(greeting());}}
/** Bỏ dở việc: the server's own gates (locked place, certificate, profile) answer first, with no payload; only its
 * "abandon_confirm" refusal opens the "Vẫn đi" dialog, built from a fresh state. Any other refusal refreshes the state
 * too, so a stale preview can never bring the dialog back in a loop. Resolves the switch result or null. */
async function switchCareer(id){
  let r;
  try{r=await api.command('select_career',{},id);}
  catch(error){
    if(error.quiet)return null;
    if(error.data?.code!=='abandon_confirm'){await api.refresh().catch(()=>{});toast(error.status?error.message:'Mất kết nối. Việc đã xác nhận vẫn được giữ, thử lại sau một chút nhé.',true);sound.error();return null;}
    await api.refresh().catch(()=>{});
    const pass=await abandonGate(api,id);
    if(!pass)return null;   // "Ở lại làm nốt"
    if(!pass.confirm){toast('Việc đang làm vừa thay đổi. Bấm chuyển lần nữa để xem lại nhé.');return null;}   // never confirm unseen
    try{r=await api.command('select_career',pass,id);}
    catch(again){if(again.quiet)return null;await api.refresh().catch(()=>{});toast(again.status?again.message:'Mất kết nối. Thử lại sau một chút nhé.',true);sound.error();return null;}
  }
  sound.click();for(const note of new Set(r.effects||[]))toast(note);
  return r;
}
async function selectCareer(id){
  ui.task=null;ui.docs.clear();ui.transactions.clear();ui.ai={};ui.phFilter='';ui.jobTab='shelf';
  await careerAssets(id);  // its workbench, stylesheet and scene first: the new place never renders half-styled
  const r=await switchCareer(id);if(!r){closeSheet();setPaused(false);return;}if(r.hired)toast(r.message,'good');
  closeSheet();world.say(greeting());setPaused(false);if(needsJob())openSheet('jobapp');else if(quickOpen(api.state,id))await openFirstDay();else if(!room().open)openSheet('prepare');
  abandonAfter(r);
}
/** A brand-new player's first workplace (v4/onboard.js quickOpen): day 1 opens at once, straight into the first
 * customer. The "Chuẩn bị" sheet stays one tap away (rail/dock) and comes back from day 2. */
async function openFirstDay(){
  const r=await cmd('start_day',{},{quiet:true});if(!r){openSheet('prepare');return;}
  ui.task=null;world.say(greeting());
  const t=room().tasks.find(x=>x.id===room().active_task&&!ended(x))||room().tasks.find(x=>!ended(x));
  if(t)openJob(t.id);else closeSheet();
}
async function openJob(id,tab){
  const target=id||room().active_task||room().tasks.find(t=>!ended(t))?.id;
  if(target!==ui.task){ui.docs.clear();ui.transactions.clear();ui.phFilter='';ui.lessonSequence=[];ui.tourRoute=[];}
  ui.task=target;ui.jobTab=tab||(ui.jobTab||'shelf');
  const t=target&&room().tasks.find(x=>x.id===target),select=t&&!ended(t)&&target!==room().active_task;
  // The workbench opens at once; the selection is confirmed in the background (commands are queued in
  // order, so a step sent meanwhile still lands after it). On failure fall back to the server's task.
  openSheet('job',{task:target,jobTab:tab||ui.jobTab});
  if(select){const r=await cmd('task_select',{task:target},{quiet:true});if(!r&&ui.view==='job'&&ui.task===target){ui.task=room().active_task||null;renderSheet(false);}}
}
function interact(id){sound.unlock();sound.click();if(ui.paused)return;
  {const alt=careerUI(career())?.spots?.[id];if(alt){openSheet(alt);return;}}  // a career's own place for a scene spot (air crew: no Sổ tiệm)
  if(id.startsWith('staff:')){ui.staffId=id.slice(6);openSheet('operations',{opsTab:'staff'});return;}
  if(id.startsWith('ops:')){openSheet('operations',{opsTab:id.slice(4)});return;}
  if(id==='officer'){openSheet('operations',{opsTab:'security'});return;}if(id.startsWith('npc:')){openSheet('chat',{npc:id.slice(4),task:null});return;}
  if(id==='event'){openSheet('event');return;}
  if(id==='pet'){world.pet();return;}
  if(id==='assistant'){cmd('assistant_help');return;}
  if(id==='door'){if(room().open)handleAction('end',{});else openSheet('prepare');return;}
  if(id==='board'){openSheet('phone');return;}
  if(id==='warehouse'){openSheet(career()==='milk_tea'?'prepare':['mother_baby','pharmacy','accounting','customer_care'].includes(career())?'warehouse':room().inventory?'inventory':'queue',INV_PLAIN);return;}
  if(['shelf','workbench','counter','evidence'].includes(id)){const tab=career()==='mother_baby'?(id==='workbench'?'pack':id==='counter'?'checkout':'shelf'):'shelf';openJob(null,tab);return;}
}
async function talk(text){if(!ui.npc||!text.trim())return;const id=ui.npc;const r=await (await L.chat.get()).aiTalk(env(),id,text);if(!r)return;ui.suggestions[id]=r.suggestions||[];world.say(r.reply,id);renderSheet();}
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
      if(data.confirm){if(!await confirmAction(wordsFor(career()).confirm_title,data.confirm,'Đồng ý thực hiện'))break;payload.confirm=true;}
      const r=await cmd(data.op,payload);
      if(r){if(data.op==='ops_hire')ui.staffId=payload.candidate;if(data.op==='ops_case_demo')ui.opsTab='security';if(data.op==='ops_incident_demo')ui.opsTab='staff';renderSheet();}
      break;
    }
    case'prepare':case'prices':case'workshop':case'passport':case'town':openSheet(action);break;
    case'expDo':{const p=JSON.parse(data.payload||'{}');
      if(data.op==='life_activity_start'&&room().life.activity?.status==='playing'&&!await confirmAction('Đổi trò nhỏ?','Tiến trình trò nhỏ đang làm sẽ được thay bằng ván mới.','Đổi trò'))break;
      if(data.confirm&&!await confirmAction('Xác nhận thao tác',data.confirm,'Đồng ý'))break;
      if(data.confirm)p.confirm=true;const r=await cmd(data.op,p);if(r){ui.activityCard=null;if(data.op==='life_activity_start'&&ui.view==='town')openSheet('workshop');else renderSheet();}break;}
    case'expRename':{const value=await inputPrompt('Đặt tên góc của bạn',room().life.shop_name||meta().place,36);if(value!==null)await cmd('life_rename',{name:value});break;}
    case'expPrice':{const el=document.getElementById('price-'+data.item),v=Number(el?.value),lo=Number(el?.min),hi=Number(el?.max);
      // The band is on the row (experience-ui priceRow): say it here instead of sending a price life_price refuses.
      if(!el||!Number.isInteger(v)||(lo&&v<lo)||(hi&&v>hi)){toast(lo&&hi?`Giá từ ${lo} đến ${hi} xu (75%–125% giá gốc).`:'Nhập giá bằng số nhé.',true);break;}
      await cmd('life_price',{item:data.item,price:v});break;}
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
    case'home':openSheet('home',{homeMode:null});break;  // 🗺️ the setting's choice again (Bản đồ phố / Danh sách)
    case'accountingSchool':if(await (await viaLazy(L.accountingSchool,el)).accountingSchoolOpen(env()))openSheet('accountingSchool');break;
    case'v4Group':railGroup(data.group||'');break;
    // "Thêm" opens on its first page, not inside the hub left open last time.
    case'v4Menu':if(ui.railGroup&&layout()==='phone')railGroup(null,false);await shell.action(action,data,el,env());break;
    case'future':openSheet('future');break;
    case'choose':await selectCareer(data.career);break;
    case'bossOffer':if(data.career&&api.state.careers[data.career])await selectCareer(data.career);break;
    case'start':await start();break;
    case'startHere':if(needsJob()){openSheet('jobapp');break;}if(await cmd('start_day'))renderSheet();break;  // the work sheet's "Mở ca": stay on it
    case'pause':setPaused(!ui.paused);break;
    case'resume':setPaused(false);break;
    case'sound':await cmd('settings',{sound:!api.state.settings.sound},{quiet:true});break;
    case'people':case'phone':case'queue':case'decor':case'settings':case'album':case'summary':case'event':case'status':openSheet(action);break;
    case'evening':ui.eve=null;openSheet('evening');break;  // 🌙 v4/needs.js
    case'stPause':closeSheet();setPaused(!ui.paused);break;
    case'stView':openSheet('home',{jrView:data.view});break;
    case'money':openSheet('money');loadJoint(env());break;
    case'wlDraw':await wealthAction(action,data,el,{...env(),placeName:cid=>placeOf(cid).name});break;
    case'journal':if(['teacher','tour_guide','milk_tea'].includes(career()))openSheet('passport');else openSheet('journal',{journalTab:'quests'});break;
    case'library':if(['teacher','tour_guide','milk_tea'].includes(career()))openSheet('workshop');else openSheet('journal',{journalTab:'library'});break;
    case'journalTab':ui.journalTab=data.tab;renderSheet(false);break;
    case'loadOlder':{const p=loadOlder(api,data.career,data.kind,data.shown);renderSheet();try{await p;}catch(e){toast(e.message,true);}renderSheet();break;}
    case'warehouse':openSheet(career()==='milk_tea'?'prepare':['mother_baby','pharmacy','accounting','customer_care'].includes(career())?'warehouse':room().inventory?'inventory':'queue',INV_PLAIN);break;
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
    case'phTickAll':{const t=activeTask();draft(t).checks=['code','quantity','lot'];renderSheet();break;}
    case'verifyPH':{const t=activeTask(),selected=draft(t).checks;await cmd('ph_check',{task:t.id,checks:['code','quantity','lot'].filter(k=>selected.includes(k))});break;}
    case'deliverPH':{const t=activeTask();if(await confirmAction('Bàn giao phiếu?','Hoàn tất nhận 40 xu thù lao.'))await cmd('ph_deliver',{task:t.id});break;}
    case'referPH':{const t=activeTask();if(await confirmAction('Chuyển cô Thu kiểm tiếp?','Hàng đang giữ được trả về kệ. Người phụ trách nhận việc; bạn nhận 25 xu thù lao chuyển đúng phạm vi.','Chuyển phiếu'))await cmd('ph_refer',{task:t.id});break;}
    case'selectDoc':ui.docs.has(data.id)?ui.docs.delete(data.id):ui.docs.add(data.id);renderSheet();break;
    case'selectTx':ui.transactions.has(data.id)?ui.transactions.delete(data.id):ui.transactions.add(data.id);renderSheet();break;
    case'acPick':{const t=activeTask(),g=t&&acGroup(t);if(g){ui.docs=new Set(g.docs.map(d=>d.id));ui.transactions=new Set(g.txs.map(x=>x.id));}renderSheet();break;}
    case'clearSelection':ui.docs.clear();ui.transactions.clear();renderSheet();break;
    case'match':{const r=await cmd('ac_match',{task:activeTask().id,docs:[...ui.docs],transactions:[...ui.transactions]});if(r){ui.docs.clear();ui.transactions.clear();renderSheet();}break;}
    case'completeAC':if(await confirmAction('Bàn giao bản đối chiếu?','Mọi thẻ phải được xử lý trước khi nhận thù lao.','Kiểm & bàn giao'))await cmd('ac_complete',{task:activeTask().id,explanation:'source_report'});break;
    case'executeCS':if(await confirmAction('Gửi việc tới đầu mối?','Kho, bên vận chuyển hay kế toán có thể mất vài giờ tới vài ngày. Vụ vẫn mở tới khi bạn kiểm kết quả.','Gửi việc'))await cmd('cs_execute',{task:activeTask().id});break;
    case'closeCS':if(await confirmAction('Đóng vụ đã có kết quả?','','Đóng vụ'))await cmd('cs_close',{task:activeTask().id});break;
    case'end':if(!room().open){openSheet('summary');break;}if(await confirmAction(wordsFor(career()).end_title,wordsFor(career()).end_text,'Khép ca')){const r=await cmd('end_day',{carry_event:true});if(r){ui.task=null;openSheet('summary');world.say('Hẹn gặp lại vào một ngày dịu dàng.');}}break;
    case'buyUpgrade':{const u=api.content.upgrades.find(x=>x.id===data.item);if(await confirmAction((u.kind==='equipment'?'Lắp ':'Đặt ')+u.name.toLowerCase()+'?',`Dùng ${u.price} xu của nghề này. ${u.description}`,u.kind==='equipment'?'Mua & lắp':'Mua & đặt'))await cmd('buy_upgrade',{item:data.item});break;}
    case'restock':{const quantity=Number(document.getElementById('qty-'+data.item)?.value);if(!Number.isInteger(quantity)||quantity<1||quantity>6){toast('Mỗi lần đặt từ 1 đến 6 món.',true);break;}const p=product(data.item);if(await confirmAction('Đặt một kiện hàng?',`${quantity} × ${p.name}, tổng ${quantity*p.cost} xu. Chỉ cộng kho sau khi kiện tới và bạn kiểm nhận.`, 'Đặt hàng'))await cmd('order_stock',{item:data.item,qty:quantity});break;}
    case'confirmEvent':{const e=room().event,o=e.options.find(o=>o.id===e.chosen);if(await confirmAction('Xác nhận cách xử lý?',`${o.label}. ${e.practice?'Diễn tập không trừ xu.':o.cost?'Chi '+o.cost+' xu từ quỹ nghề.':'Không tốn xu.'}`, 'Bắt đầu thực hiện'))await cmd('event_confirm');break;}
    case'eventStep':{const r=await cmd('event_step');if(r){world.say(r.message);world.go(room().event.station,()=>{});}break;}
    case'practice':{const e=room().event;if(e&&e.stage!=='resolved'){if(e.practice){if(!(await confirmAction('Chuyển tình huống diễn tập?','Diễn tập hiện tại được cất lại, không thay đổi tiền hoặc quan hệ.','Chuyển tình huống')))break;await cmd('event_dismiss',{}, {quiet:true});}else{toast('Bạn đang có một chuyện thật trong ca. Hoàn thành trước rồi mở diễn tập nhé.',true);openSheet('event');break;}}const r=await cmd('event_start',{event:data.event});if(r)openSheet('event');break;}
    case'reviewFollowup':{if(REVIEW_PASSPORT.includes(career())){openSheet('passport');break;}const r=await cmd('review_followup',{post:data.post});if(r)openSheet('event');break;}
    case'photo':{closeSheet();await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));const image=world.snapshot();const r=await cmd('photo',{image,title:meta().place+' · Ngày '+dayNo(room())});if(r)openSheet('album');break;}
    case'downloadPhoto':{const p=room().album.find(x=>x.id===data.id);if(p){const a=document.createElement('a');a.href=p.image;a.download=`goc-pho-ngay-${p.day}.${/^data:image\/(png|jpeg)/.exec(p.image)?.[1]?.replace('jpeg','jpg')||'webp'}`;a.click();}break;}
    case'saveAI':await cmd('settings',{aiConsent:$('#ai-consent').checked});break;
    case'export':try{const data=await api.exportSave();download(JSON.stringify(data,null,2),'mot-ngay-lam-nghe-save.json');toast('Đã xuất bản lưu riêng của bạn.');}catch(e){toast(e.message,true);}break;
    case'import':$('#import-file').click();break;
    case'resetCareer':if(await confirmAction('Xóa tiến trình riêng nghề này?','Tiền, đồ, công việc, hội thoại và album của nghề đang chọn sẽ được đặt lại. Các nghề khác giữ nguyên. Nên xuất bản lưu trước.','Xóa & bắt đầu lại')){const r=await cmd('reset_career',{confirm:'BAT DAU LAI'});if(r){ui.task=null;closeSheet();await start();}}break;
    default:{
      if((L.tut.m||TUT_OPEN.has(action))&&await (await viaLazy(L.tut,el)).tutorialAction(action,data,el,env()))break;
      if(action.startsWith('desk:')&&await (await viaLazy(L.desk,el)).deskAction(action,data,el,env()))break;
      if(await boardAction(action,data,el,env()))break;
      if((L.rank.m||action==='rank')&&await (await viaLazy(L.rank,el)).leaderboardAction(action,data,el,env()))break;
      if((L.promo.m||PROMO_OPEN.has(action))&&await (await viaLazy(L.promo,el)).promoAction(action,data,el,env()))break;  // 🎖️🧑‍💼

      if(action==='liveChat'){(await viaLazy(L.live,el)).openChat(data);break;}  // 💬 Chat (v4/chat.js)
      if(action==='liveWalk'){const w=await import('./v4/walk.js');L.live.m?.benchSpot(w.walk);await w.openWalk(env(),data);break;}  // 🚶 Đi dạo (v4/walk.js): its own dialog; 💕 its benches are the dating bench
      if(action==='liveDate'){(await viaLazy(L.live,el)).openDate(data);break;}  // 💕 Góc hẹn hò (v4/dating.js)
      if(action==='liveWed'){await (await import('./v4/wedding.js')).openWeddings(env());break;}  // 💍 Lịch cưới (v4/wedding.js): its own dialog
      if(action==='liveKara'){await (await import('./v4/karaoke.js')).openKaraoke(env(),data);break;}  // 🎤 Phòng hát (v4/karaoke.js): its own dialog
      if(action==='marriage'||action==='friends'){await (await import('./v4/marriage.js')).marriageAction(action,data,el,env());break;}  // Hôn nhân, Bạn bè: lazy
      if(action==='bank'){await (await import('./v4/bank.js')).bankAction(action,data,el,env());break;}  // 🏦 Ngân hàng Phố: lazy
      if(action==='house'){await (await import('./v4/house.js')).houseAction(action,data,el,env());break;}  // 🏠 Nhà của bạn: lazy
      if(action==='garage'){await (await import('./v4/garage.js')).garageAction(action,data,el,env());break;}  // 🚗 Xe & phương tiện: lazy
      if(action==='pets'){await (await import('./v4/pets.js')).petsAction(action,data,el,env());break;}  // 🐾 Nuôi thú cưng: lazy
      if(action==='gadgets'){await (await import('./v4/gadgets.js')).gadgetsAction(action,data,el,env());break;}  // 📱 Cửa hàng điện thoại: lazy
      if(SPEND_OPEN.has(action)){await (await import('./v4/spend.js')).spendAction(action,data,el,env());break;}  // ☕ Đi quán, spa, rạp, 🙏 công đức, 🎨 phong cách: lazy
      if(action==='vang'){ui.ivMarket='gold';await journeyAction('jrInvest',data,el,env());break;}
      if(action==='rui'){await (await import('./v4/rui.js')).ruiAction(action,data,el,env());break;}
      if(action==='homeGuests'){await (await import('./v4/home-guests.js')).openHomeGuests(env(),data);break;}
      if(action==='workVisit'){await (await import('./v4/workplace-visit.js')).openWorkplaceVisit(env(),data);break;}
      if(action==='workVisitServe'){if(data.kind==='quay'){await (await import('./v4/quay.js')).quayAction('quay',{visitor:data.order},el,env());break;}if(data.career&&data.career!==career()){await selectCareer(data.career);if(career()!==data.career)break;}await openJob(data.task);break;}
      if(action==='quay'){await (await import('./v4/quay.js')).quayAction(action,data,el,env());break;}  // 🏪 Quầy của bạn: lazy
      if(action==='fair'){await (await import('./v4/fair.js')).fairAction(action,data,el,env());break;}  // 🏮 Hội chợ dân gian: lazy
      if(L.people.m&&await L.people.m.closenessAction(action,data,el,env()))break;
      if(await needsAction(action,data,el,env()))break;  // 🍚😴 nd…
      if(await journeyAction(action,data,el,env()))break;
      if((L.inc.m||action==='incident'||action==='incLog')&&await (await viaLazy(L.inc,el)).incidentAction(action,data,el,env()))break;
      if(guideAction(action,data,el))break;
      if(await v4Action(action,data,el,env()))break;
      if(action.startsWith('car:')){const mod=careerUI(career()),fn=mod?.actions?.[action.slice(4)];if(fn){
        // A career's own entry (dock: Bảng nội quy, Sổ tay nhà, Giới thiệu nghề) tapped on the scene, the bar or Thêm,
        // where its work sheet is not on screen: its own page when it has one, else the work sheet with the pane open.
        if(!el?.closest?.('.career-job')&&(mod.dock||[]).some(d=>d[0]===action)){
          if(mod.page?.(action,careerContext(env()))){openSheet('carPage',{carPage:action});break;}
          if(!($('#sheet').open&&ui.view==='job'))await openJob(null);
        }
        await fn(data,el,careerContext(env()));break;}}
      if(L.settings.m?await L.settings.m.settingsAction(action,data,el,env()):await accountAction(action,data,el,env()))break;
      if((L.social.m||action==='social')&&await (await viaLazy(L.social,el)).socialAction(action,data,el,env()))break;
      if((L.fb.m||action==='gopy')&&await (await viaLazy(L.fb,el)).feedbackAction(action,data,el,env()))break;
      if(procedureAction(action,data,el,env()))break;
      if(/^as[A-Z]/.test(action)&&await (await viaLazy(L.accountingSchool,el)).accountingSchoolAction(action,data,el,env()))break;
      if(action==='classroom'){openSheet('classroom');break;}
      if(await shell.action(action,data,el,env()))break;
      toast('Chưa có tương tác này.',true);
    }
  }
}
/* Taps answer at once: the pressed control dims before the server replies. A tap that lands while
   a command is on the wire is kept (the last one only) and replayed on the re-rendered control with
   the same attributes, instead of being dropped ("phải bấm mấy lần mới vô"). */
let heldTap=null,flightTap=null;
const tapKey=el=>el.dataset.command?`[data-command="${CSS.escape(el.dataset.command)}"][data-payload="${CSS.escape(el.dataset.payload||'')}"]`
  :`[data-action="${CSS.escape(el.dataset.action)}"]`+Object.entries(el.dataset).filter(([k])=>k!=='action').map(([k,v])=>`[data-${k.replace(/[A-Z]/g,m=>'-'+m.toLowerCase())}="${CSS.escape(v)}"]`).join('');
function pressed(el){el.classList.add('is-pressed');setTimeout(()=>el.classList.remove('is-pressed'),700);}
/** A tap held while a command is on the wire shows it is waiting (aria-busy; CSS adds a small spinner after
 * 400 ms), so a slow server does not feel like a dead button. No extra request: it is replayed as before. */
let heldEl=null;
function holdMark(el){heldEl?.classList.remove('is-held');heldEl?.removeAttribute('aria-busy');heldEl=el||null;if(el){el.classList.add('is-held');el.setAttribute('aria-busy','true');}}
function replayHeld(){
  holdMark(null);
  const key=heldTap;heldTap=null;if(!key)return;
  const el=[...document.querySelectorAll(key)].find(x=>!x.disabled&&x.offsetParent!==null);
  el?.click();
}
document.addEventListener('click',async e=>{
  const el=e.target.closest?.('[data-action],[data-command]');if(!el||el.disabled)return;sound.unlock();sound.configure(api.state?.settings||{sound:true,music:false});
  pressed(el);
  // Additional input while a mutation is on the wire waits for it; retries carry an idempotency key.
  // A second tap on the control already on the wire is a double tap, not a new wish.
  // data-quick (a milk tea pick): the workbench shows it at once and queues its command itself (api.command keeps
  // the order), so quick picks in a row are not held behind each other.
  if(ui.busy&&!['close','confirmNo','confirmYes'].includes(el.dataset.action)&&!el.hasAttribute('data-quick')){try{const k=tapKey(el);heldTap=k===flightTap?null:k;}catch{heldTap=null;}holdMark(heldTap?el:null);return;}
  try{flightTap=tapKey(el);}catch{flightTap=null;}
  // "Đón thêm khách" drawn before the gate closed (a career panel, an older render): no press into a sure refusal.
  if(el.dataset.command==='more_work'&&moreGate(room())){const g=moreGate(room());toast(g.why==='full'?'Đang có đủ việc: làm tiếp việc đang chờ nhé.':g.why==='cap'?'Hôm nay đủ khách rồi: làm nốt rồi khép ca nhé.':'Sắp đóng cửa: không đón thêm khách. Làm nốt rồi khép ca nhé.','hint');if(room().tasks.some(x=>!ended(x))){ui.task=null;await openJob(null,'shelf');}else{renderMain();renderSheet();}return;}
  if(el.dataset.command){const action=el.dataset.command,payload=JSON.parse(el.dataset.payload||'{}');const result=await cmd(action,payload);if(result){if(action==='defer'){ui.task=null;openSheet('queue');}if(action==='event_dismiss'){openSheet('journal',{journalTab:'library'});}if(action==='more_work'){ui.task=null;await openJob(null,'shelf');}if(action==='ask'){world.say(result.message,activeTask()?.npc);}}}
  else{try{await handleAction(el.dataset.action,el.dataset,el);}catch(error){console.error(error);toast('Thao tác chưa hoàn tất. '+error.message,true);}}
});
document.addEventListener('dragstart',e=>{const el=e.target.closest?.('[data-drag-card]');if(el){ui.activityCard=el.dataset.dragCard;e.dataTransfer.setData('text/plain',ui.activityCard);}});
document.addEventListener('dragover',e=>{if(e.target.closest?.('[data-drop-target]'))e.preventDefault();});
document.addEventListener('drop',async e=>{const el=e.target.closest?.('[data-drop-target]');if(!el||ui.busy)return;e.preventDefault();const card=e.dataTransfer.getData('text/plain');if(!card)return;await cmd('life_activity_assign',{card,target:el.dataset.dropTarget});ui.activityCard=null;renderSheet();});
document.addEventListener('submit',async e=>{
  const f=e.target;if(!(f instanceof HTMLFormElement))return;e.preventDefault();sound.unlock();if(ui.busy)return;
  if(await careerSubmit(f,env()))return;
  if(await journeySubmit(f,env()))return;
  if(await boardSubmit(f,env()))return;
  if(await v4Submit(f,env()))return;
  if(await accountSubmit(f,env()))return;
  if(L.accountingSchool.m&&await L.accountingSchool.m.accountingSchoolSubmit(f,env()))return;
  if(L.social.m&&await L.social.m.socialSubmit(f,env()))return;
  if(L.fb.m&&await L.fb.m.feedbackSubmit(f,env()))return;
  if(await procedureSubmit(f,env()))return;
  if(await shell.submit(f,env()))return;
  if(f.id==='staffTalkForm'){const input=$('#staff-message'),text=input.value.trim();if(!text)return;input.value='';await cmd('ops_staff_talk',{employee:f.dataset.employee,text},{quiet:true});}
  else if(f.id==='chatForm'){const input=$('#chat-input'),text=input.value.trim();if(!text||L.chat.m?.chatBusy(ui.npc))return;input.value='';const count=$('#chat-count');if(count)count.textContent='0/200';await talk(text);}
  else if(f.id==='postForm'){const input=$('#post-text'),text=input.value.trim();if(!text)return;input.value='';await cmd('feed_post',{text});}
  else if(f.dataset.replyPost){const input=f.querySelector('input'),text=input.value.trim();if(!text)return;input.value='';await cmd('feed_reply',{post:f.dataset.replyPost,text});}
  else if(f.dataset.receive){const count=Number(f.querySelector('input').value);await cmd('receive_stock',{shipment:f.dataset.receive,count});}
  else if(f.id==='settingsForm'){await cmd('settings',{name:$('#player-name').value});}
});
document.addEventListener('input',e=>{
  if(L.accountingSchool.m?.accountingSchoolInput(e.target,env()))return;
  if(careerInput(e.target,env(),'input'))return;
  if(v4Input(e.target,env()))return;
  if(L.settings.m?.settingsInput(e.target))return;
  if(L.fb.m?.feedbackInput(e.target,env()))return;
  if(e.target.dataset.draft&&activeTask())draft(activeTask())[e.target.dataset.draft]=e.target.value;
  if(e.target.id==='library-search'){ui.libraryQuery=e.target.value;renderSheet();}
  if(e.target.closest?.('.wh-qty'))whBill(e.target);
});
document.addEventListener('change',async e=>{
  const el=e.target;
  if(L.accountingSchool.m?.accountingSchoolInput(el,env()))return;
  if(careerInput(el,env(),'change'))return;
  if(L.settings.m&&await L.settings.m.settingsChange(el,env()))return;
  if(el.dataset.staffRole)await cmd('ops_assign',{employee:el.dataset.staffRole,role:el.value});
  if(el.dataset.staffSchedule)await cmd('ops_schedule',{employee:el.dataset.staffSchedule,schedule:el.value});
  if(el.dataset.phcheck){const checks=draft(activeTask()).checks;draft(activeTask()).checks=el.checked?[...new Set([...checks,el.dataset.phcheck])]:checks.filter(k=>k!==el.dataset.phcheck);}
  if(el.dataset.actionChange==='ph-filter'){ui.phFilter=el.value;renderSheet(false);}
  if(el.dataset.decorItem)await cmd('decor_move',{item:el.dataset.decorItem,spot:el.value});
  if(el.id==='import-file'&&el.files[0]){const file=el.files[0];try{if(file.size>14500000)throw new Error('Bản lưu quá lớn.');const save=JSON.parse(await file.text());if(await confirmAction('Khôi phục bản lưu này?','Các nghề của phiên hiện tại sẽ được thay thế bằng dữ liệu trong tệp. Hãy xuất bản hiện tại trước nếu cần.','Khôi phục')){const r=await cmd('import_save',{save});if(r){ui.task=null;ui.docs.clear();ui.transactions.clear();closeSheet();if(!api.state.current)openSheet('home');}}}catch(error){toast('Không nhập được: '+error.message,true);}}
});
window.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('#sheet').open&&!$('#confirmDialog').open&&api.state?.current){setPaused(!ui.paused);}});
// Back in the tab: re-sync, unless the state is fresh anyway (every focus used to refetch and re-render all).
window.addEventListener('focus',()=>{if(api.state&&!ui.busy&&!(ui.view==='home'&&ui.jrView==='invest')&&Date.now()-(api.syncedAt||0)>15000)api.refresh().catch(()=>{});});
const stopStaffRefresh=staffRefresh({state:()=>api.state,refresh:()=>api.refresh(),busy:()=>staffRefreshPaused(ui,!!document.querySelector('dialog.qy-sheet[open]'),!!document.querySelector('dialog.fh-sheet[open]'))||sheetScroll.busy(),lastSync:()=>api.syncedAt||0});
window.addEventListener('pagehide',event=>{if(!event.persisted)stopStaffRefresh();});
let responsiveTimer;
window.addEventListener('resize',()=>{clearTimeout(responsiveTimer);responsiveTimer=setTimeout(()=>{if(api.state&&api.content)renderMain();},140);});
// Badges set outside a render (v4/ticker.js, v4/marriage.js): redraw the rail so its hubs carry them too.
document.addEventListener('mnl:badges',()=>{if(api.state&&api.content&&!$('#app').hidden){setHTML($('#rail'),railHTML(room()));setHTML($('#dock'),dockHTML(room()));}});
window.addEventListener('layoutchange',()=>{world.resize();if(api.state&&api.content)renderMain();});
/* A workbench showing picks ahead of the server (milk tea: module.settling) skips drawing its sheet for an answer that
 * another queued answer follows: the sheet shows those picks already, and the last answer draws it. */
const settling=()=>{if(ui.view!=='job')return false;try{return !!careerUI(career())?.settling?.(careerContext(env()));}catch{return false;}};
// While the player scrolls the open sheet, its redraw waits for the scroll to settle (work-equipment.js scrollGuard).
api.addEventListener('state',()=>{syncOlder(api.revision);ensureCareerUI();renderMain();if(ui.view&&!settling()){if(sheetScroll.busy())sheetScroll.later(()=>{if(ui.view&&!settling())renderSheet();});else renderSheet();}shell.update(env());});
api.addEventListener('busy',e=>{ui.busy=e.detail;document.body.classList.toggle('busy',ui.busy);$('#saveState')?.setAttribute('aria-busy',String(ui.busy));if(!ui.busy&&heldTap)setTimeout(replayHeld,60);else if(!ui.busy)holdMark(null);});
/* "Game mất chữ": an iPhone tab left open across a deploy came back with every card of the work sheet
 * blank (containers, portrait and button shapes drawn, no words) while the DOM still held the text.
 * - Coming back to such a tab reloads it onto the new release when nothing would be lost (update.js
 *   autoReload asks idle()); otherwise the pill stays, as before.
 * - Coming back without a new release, a page restored from the back/forward cache, or a web font that
 *   finished loading late: the open sheet is written whole once (not morphed), so its text is laid out
 *   and painted again. Never while the player is typing. */
const TYPING='input:not([type=button]):not([type=checkbox]):not([type=radio]):not([type=range]):not([type=hidden]),textarea,select,[contenteditable="true"]';
function typing(){
  const a=document.activeElement;if(a&&a!==document.body&&a.matches?.(TYPING))return true;
  return [...document.querySelectorAll('dialog[open] input,dialog[open] textarea')].some(e=>e.matches(TYPING)&&e.value&&e.value!==e.defaultValue);
}
api.updates.idle=()=>!ui.busy&&!(api.writing>0)&&!document.querySelector('#confirmDialog[open]')&&!typing();
function repaintSheet(){if(ui.view&&$('#sheet')?.open&&!typing()){ui.freshSheet=true;renderSheet();}}
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')repaintSheet();});
window.addEventListener('pageshow',e=>{if(e.persisted)repaintSheet();});
// Fonts arrive in several batches at boot: one rewrite after the last of them, not one per batch.
let fontsLate=0;document.fonts?.addEventListener?.('loadingdone',()=>{clearTimeout(fontsLate);fontsLate=setTimeout(repaintSheet,150);});
/* Tap feedback. A control that starts a server request within 400 ms of its tap is marked at once
 * (.is-pending + aria-busy; CSS dims it and adds a spinner after 150 ms) until the requests settle; a
 * re-render drops the mark too. A second tap on a pending control is swallowed (no double submit).
 * The mark goes only once EVERY request is answered, so a control that keeps its own busy state (off while its
 * request is out, e.g. the wedding's 🧧 send) opts out with data-own-busy: otherwise, re-enabled while another
 * request was still out (the minute money), it looked ready but its next tap was swallowed without a word. */
const tap={el:null,at:0,pending:new Set()};
document.addEventListener('touchstart',()=>{},{passive:true});  // iOS Safari shows :active only with a touch listener
document.addEventListener('click',e=>{
  const el=e.target.closest?.('button,[data-action],[data-command]');
  if(el?.classList.contains('is-pending')){e.preventDefault();e.stopImmediatePropagation();return;}
  tap.el=el&&!el.disabled&&!el.hasAttribute('data-own-busy')?el:null;tap.at=performance.now();
},true);
document.addEventListener('submit',e=>{tap.el=e.submitter||e.target.querySelector?.('button:not([type=button])')||null;tap.at=performance.now();},true);
// A command waiting in the queue counts as on its way (api.js 'queued': behind an AI write that holds the queue up to
// AI_WAIT, its request starts seconds after the tap); the mark stays until no request and no command is left.
const markTap=()=>{const el=tap.el;if(el?.isConnected&&performance.now()-tap.at<400&&!tap.pending.has(el)){el.classList.add('is-pending');el.setAttribute('aria-busy','true');tap.pending.add(el);}};
const unmarkTaps=()=>{if(api.inflight>0||api.waiting>0)return;for(const el of tap.pending){el.classList.remove('is-pending');el.removeAttribute('aria-busy');}tap.pending.clear();};
api.addEventListener('net',e=>{if(e.detail>0)markTap();else unmarkTaps();});
api.addEventListener('queued',markTap);
api.addEventListener('busy',e=>{if(!e.detail)unmarkTaps();});
/* Career workbenches and scene kinds load on demand (startup: the current one; selectCareer: the next one).
 * Anything else that switches careers is covered by ensureCareerUI (re-renders once the module is in). */
const CAREER_MODULES=[];
// Its part of the catalogue (api.careerContent: a plugin workplace's data) comes with its workbench.
const careerAssets=(id,waitCss=true)=>Promise.all([CAREER_MODULES.includes(id)&&!hasCareerUI(id)?loadCareerModules([id],waitCss):null,api.careerContent(id),import(`./scenes/${kindOf(id)}.js`).catch(()=>{}),id==='teacher'||id==='tour_guide'?teachTour(api).catch(()=>{}):null]);
setCareerData(id=>api.hasCareerContent(id));  // careerUI(id) waits for the workplace's data part too
/* The current workplace's workbench and data part, when they are not in (a switch, or a start-up whose fetch failed
 * on a weak network: the game opens anyway). Failed again: asked for once more after 2, 4, 8 … 30 s, not on every
 * render. Both loaders settle without throwing. */
const workbench={busy:null,id:null,tries:0,timer:0};
function ensureCareerUI(){
  const id=api.state?.current;
  if(!id||(hasCareerUI(id)&&api.hasCareerContent(id))||!CAREER_MODULES.includes(id)||workbench.busy===id||(workbench.timer&&workbench.id===id))return;
  workbench.busy=id;Promise.all([hasCareerUI(id)?null:loadCareerModules([id],true),api.careerContent(id)]).then(()=>{
    workbench.busy=null;
    if(hasCareerUI(id)&&api.hasCareerContent(id)){if(workbench.id===id)workbench.tries=0;}
    else{if(workbench.id!==id){workbench.id=id;workbench.tries=0;}workbench.timer=setTimeout(()=>{workbench.timer=0;ensureCareerUI();},Math.min(30000,2000*2**workbench.tries++));}
    if(api.state?.current===id){renderMain();if(ui.view)renderSheet();}
  });
}
api.addEventListener('offline',()=>renderMain());
// While the always-on features load one by one after start-up (lazyBoot), only a module the screen is waiting
// for re-renders it; the rest get one re-render at the end (seven full re-renders there used to land on the
// player's first taps).
let lazyFrame=0,lazyBoot=false;
document.addEventListener('mnl:lazy',e=>{if(lazyFrame||(lazyBoot&&e.detail?.wanted===false))return;lazyFrame=requestAnimationFrame(()=>{lazyFrame=0;if(!api.state||$('#app').hidden)return;renderMain();if(ui.view)renderSheet(!$('#sheetContent .mnl-skel'));});});
window.addEventListener('online',()=>{if(api.state)api.refresh().then(()=>renderMain()).catch(()=>{});});
window.addEventListener('error',e=>{console.error('Game UI:',e.error||e.message);});
try{
  await api.init();
  // Only the current workplace's workbench (+ its stylesheet and scene) gates the first frame; the others load
  // when the player switches to them (startup used to wait on ~45 requests for every career and scene).
  CAREER_MODULES.push(...Object.keys(api.content.careers||{}),'milk_tea','mother_baby');
  // Its stylesheet only styles the workbench: wait for it only when a sheet opens right away (day closed).
  await Promise.all([careerAssets(career(),Boolean(api.state.current&&(!room()?.open||needsJob()))),setLanguage(api.state.settings.lang)]);
  import('./v4/home-guests.js').then(m=>m.homeGuestsBoot(env())).catch(e=>console.warn('homeGuests:',e));
  import('./v4/workplace-visit.js').then(m=>m.workVisitsBoot(env())).catch(e=>console.warn('workVisits:',e));
  shell.boot(env());journeyBoot(env());boardBoot(env());startTicker(()=>env());$('#loading').hidden=true;$('#app').hidden=false;world.resize();renderMain();
  const oauthReturned=accountBoot(env());
  ensureCareerUI();  // its workbench failed to come above (the game opens anyway): ask again in the background
  try{performance.mark('mnl-first-frame');}catch{/* no User Timing */}   // "time to first game frame" (telemetry.js load beacon)
  import('./telemetry.js').then(m=>m.telemetryBoot({api,ui})).catch(e=>console.warn('telemetry:',e));  // Giữ chân: leave/error/load beacons
  // 💬 The live socket (chat button, friends): first idle moment after the first frame, not last of the queue below
  // (it came ~6 s late, and after a sign-in sheet even later); its greyed button shows until the welcome.
  whenIdle(()=>L.live.get().then(m=>m.liveBoot(env())).catch(e=>console.warn('live:',e)),800);
  // The rest of the catalogue (api.more), now that the first frame is out: it never competed with it on the wire.
  api.more().catch(e=>console.warn('content:',e));
  // Always-on features (badges, notices, polls, tips) load once the game is on screen, not before it.
  // Góp ý and admin stats (and their stylesheets) load when that page first opens (L.fb).
  // One per idle slot, so a tap never waits behind all of them compiling at once. A player who has not been
  // through the tour yet gets the tutorial at once (its welcome card is the first thing they should see).
  const tutBoot=[L.tut,m=>m.tutorialBoot(env())];
  let tutNow=false;try{tutNow=localStorage.getItem('mnl.tut.done')!=='1'&&api.state.settings?.tutorialDone!==true;}catch{}
  const bootSteps=[...(tutNow?[]:[tutBoot]),[L.inc,m=>m.incidentBoot(env())],[L.chat,m=>m.aiNoticeBoot(env())],[L.happen,m=>m.happenBoot(env())],
    [L.people,()=>{}],[L.social,m=>m.startSocialPoll(env())],[L.tips,m=>m.tipsBoot({api,sound})]];
  const bootNext=i=>{
    if(i>=bootSteps.length){lazyBoot=false;document.dispatchEvent(new CustomEvent('mnl:lazy',{detail:{wanted:true}}));return;}
    const [h,fn]=bootSteps[i];h.get().then(fn).catch(e=>console.warn('lazy boot:',e)).finally(()=>whenIdle(()=>bootNext(i+1),600));
  };
  // Places the player has worked at: their workbench and scene into the HTTP cache, at the lowest priority,
  // long after start-up (the next switch then opens without a network wait).
  whenIdle(()=>{const has=u=>(globalThis.__mnlBoot?.asset?.(u)||u)!==u;
    const played=Object.entries(api.state.careers||{}).filter(([id,c])=>id!==career()&&c&&(c.day>1||c.metrics?.served>0)).map(([id])=>id).slice(0,2);
    prefetch(played.flatMap(id=>[`/js/careers/${id}.js`,`/css/careers/${id}.css`,`/js/scenes/${kindOf(id)}.js`]).filter(has));},12000);
  (window.requestIdleCallback||setTimeout)(()=>{if(api.state.settings.sound!==false)sound.prepare();},{timeout:3000});
  registerWorker();
  const openSocial=tab=>{ui.socTab=tab||'street';ui.socShop=null;L.social.get().then(m=>{m.invalidate(ui);openSheet('social');}).catch(()=>{});};
  listenWorker(url=>{const q=new URL(url,location.origin).searchParams;if(q.get('social'))openSocial(q.get('social'));});
  if(!oauthReturned){
    const deep=new URLSearchParams(location.search);
    if(deep.get('social')){history.replaceState(null,'','/');openSocial(deep.get('social'));}
    else if(!api.state.current)openSheet('home');else{if(!room().open)openSheet(room().shift_summary?'summary':'prepare');}
  }
  // Callback feedback gets the first screen. Start automatic cards only after the player closes it;
  // a queued close event from a sheet already reopened is not a dismissal.
  const bootAutomatic=()=>{
    if(tutNow)tutBoot[0].get().then(tutBoot[1]).catch(e=>console.warn('lazy boot:',e));
    lazyBoot=true;whenIdle(()=>bootNext(0),1500);
    import('./v4/whatsnew.js').then(m=>m.whatsNewBoot(env())).catch(e=>console.warn('whatsnew:',e));  // "Có gì mới": lazy, off the first load
    import('./v4/x3week.js').then(m=>m.x3Boot(env())).catch(e=>console.warn('x3week:',e));  // 🔥 Nghề x3 trong tuần (game/x3_week.py)
    if(api.state?.rui)import('./v4/rui.js').then(m=>m.ruiBoot(env())).catch(e=>console.warn('rui:',e));  // 🛡️ a warning or a card at a calm moment (game/rui.py)
    if(api.gifts?.length)import('./v4/gift.js').then(m=>m.giftBoot(env())).catch(e=>console.warn('gift:',e));  // 🎁 Quà từ Phố Có Chuyện: only for a save with a gift
    if(api.xfers?.length)import('./v4/bank-xfer.js').then(m=>m.showIncoming(env(),api.xfers)).catch(e=>console.warn('xfer:',e));  // 💸 what friends sent (credited on load)
    if(firstDay(api.state))import('./v4/onboard-fx.js').then(m=>m.onboardBoot(env())).catch(e=>console.warn('onboard:',e));  // a new player's first day only
  };
  if(oauthReturned){
    const sheet=$('#sheet'),resumeBoot=()=>{if(sheet.open)return;sheet.removeEventListener('close',resumeBoot);bootAutomatic();};
    sheet.addEventListener('close',resumeBoot);
  }else bootAutomatic();
  import('./v4/ticker.js').then(m=>m.tickerBoot(()=>env())).catch(e=>console.warn('ticker:',e));  // Bảng tin cả phố (tin cưới): lazy
}catch(error){$('#loading').innerHTML=`<div class="loading-leaf">${icon('leaf',45)}</div><h1>Khu phố đang đợi mở cửa</h1><p>Chưa kết nối được. Kiểm tra mạng rồi thử lại nhé.</p><button class="btn primary big" id="reload-btn">Thử kết nối lại</button>`;console.warn(error);$('#reload-btn').onclick=()=>location.reload();}
