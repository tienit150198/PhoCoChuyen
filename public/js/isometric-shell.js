/** Small DOM controls over the town. All gameplay still goes through the app's existing actions. */
import {escapeHTML as esc} from './icons.js';
import {uiIcon as icon} from './isometric/ui-icons.js';
import {hudMoney,shortNum} from './v4/wealth.js';
import {myPortrait} from './v4/look.js';
import {openGuide,goTo,firstJob} from './iso-guide.js';
import {townUtilityGroups,townRideLabel,nextTownRide,townRiding,forgeOpen,townFlyLabel,toggleTownFly} from './isometric/town-utilities.js';

const ENDED=new Set(['completed','referred','cancelled']);
/** v4/onboard.js firstDay (story, first life day), inline: the shell's tests run this file without its imports. */
const firstDay=s=>Boolean(s?.journey?.story&&(Number(s.journey.life_day)||1)<=1);
/** v4/onboard.js quickOpen, inline (same reason): the first workplace's day 1 on the first life day opens at once. */
const quickOpen=(s,cid)=>{
  const c=s?.careers?.[cid];
  if(!firstDay(s)||!c||c.open||Number(c.day)!==1||c.shift_summary)return false;
  return Object.entries(s.careers).every(([id,x])=>id===cid||!x?.started);
};
/** Feedback #432 (mỳ cay, 2.4.52): back from the town with the shift closed, the main button took the player back
 * to the workplace AND opened a new day in the same tap, before any stock was bought. It now only says where it goes:
 * the shop's own word from its name (Quán Mì Cay → "Về quán"), any other shop "Về tiệm", a career that is not a shop
 * its own short place word (game/career_voice.py terms.place: "Về lớp", "Về chùa", "Về khoa"…) or "Về chỗ làm". */
const SHOP_WORDS=['quán','tiệm','sạp','xưởng','salon','chợ'];
function homeLabel(meta,shopName){
  const t=meta?.terms;
  if(t&&t.commerce===false)return t.place&&String(t.place).length<=10?'Về '+t.place:'Về chỗ làm';
  for(const name of [shopName,meta?.place]){
    const word=String(name||'').trim().normalize('NFC').split(/\s+/)[0].toLocaleLowerCase('vi');
    if(SHOP_WORDS.includes(word))return 'Về '+word;
  }
  return t?'Về tiệm':'Về chỗ làm';   // no words yet (catalogue not in): nothing that would name a classroom "tiệm"
}
const fmt=n=>Number(n).toLocaleString('vi-VN');
let getEnvironment=null;
let listening=false;
let rendered='';
let chatLive=null;
let cameraOpen=false;
/** "Giao diện cũ (đơn giản)" (owner 18/10: the 2.5D town was hard to play for some): asked from ☰ Thêm, and once by
 * itself to a newer player who has walked the town for a while without a shift (stuckWatch). */
const CLASSIC={title:'Dùng giao diện cũ cho dễ chơi?',
  text:'Giao diện cũ đơn giản hơn: tiệm và các nút làm việc luôn ở trước mặt. Tiến trình giữ nguyên; đổi lại lúc nào cũng được trong Cài đặt.'};

/** Pure presentation state, including the server's task order and chosen career. */
export function isometricHUDModel(state={},content={},mode='town',social={},connection){
  const current=state.current&&state.careers?.[state.current]?state.current:null;
  const room=current?state.careers[current]:null;
  const meta=content?.catalogue?.find(c=>c.id===current)||{};
  const tasks=Array.isArray(room?.tasks)?room.tasks.filter(t=>t&&!ENDED.has(t.status)):[];
  const task=tasks.find(t=>t.id===room?.active_task)||tasks[0]||null;
  const needsJob=Boolean(room?.job?.required&&room.job.status!=='hired');
  const sceneMode=mode==='work'&&current?'work':'town';
  const storyDay=state.journey?.story!==false&&Number.isInteger(state.journey?.life_day)?state.journey.life_day:null;
  const day=storyDay??(Number.isInteger(room?.day)?room.day:null);
  const place=room?.life?.shop_name||meta.place||meta.name||'Nơi làm việc';
  const chatOff=social.flags?.chat===false;
  const chatOnline=social.state==='open'&&!chatOff;
  const chatStatus=chatOff?'Tạm nghỉ':chatOnline?(social.me?.account===false?'Khách · Chỉ xem':'Cả phố · Bạn bè'):
    connection&&!connection.url?'Chưa khả dụng':
    social.state==='connecting'?'Đang kết nối':
    social.state==='down'?'Mất kết nối':social.state==='off'?'Không khả dụng':'Chưa kết nối';
  // A new neighbour's first day (v4/onboard.js firstDay): no workplace yet → the first one (walked to); every customer
  // served → "Khép ca", not the job book.
  const fresh=firstDay(state),done=Boolean(fresh&&room?.open&&!task&&!needsJob);
  return {current,mode:sceneMode,name:state.name||'Bạn',day,place,careerName:meta.name||place,fresh,done,
    sceneTitle:sceneMode==='work'?place:'Đảo Hoàng Sa',money:hudMoney(state,current),
    task,taskCount:tasks.length,needsJob,open:Boolean(room?.open),
    home:current?homeLabel(meta,room?.life?.shop_name):'',firstOpen:Boolean(current&&quickOpen(state,current)),
    missionAction:!current?'isoCareers':needsJob?'isoApply':!room.open?'isoPrepare':task?'isoMission':done?'isoEnd':'isoQueue',
    chatUnread:Math.max(0,Number(social.unread?.())||0),chatOnline,chatOff,chatStatus,
    fairOpen:Boolean(state.fair?.show),menuOpen:false,cameraOpen:false,shop:Boolean(state.journey?.gender),forge:forgeOpen(state,content),
    utilityGroups:townUtilityGroups(state,content,social),
    ride:sceneMode==='town'?townRideLabel(state,content):'',riding:sceneMode==='town'?townRiding(state,content):null,
    fly:sceneMode==='town'?townFlyLabel(state):''};
}

const control=(label,action,ico,cls='',extra='')=>`<button type="button" class="${cls}" data-action="${action}"${extra}>${icon(ico,22)}<span>${label}</span></button>`;

function moneyChip(label,value,kind){
  if(value==null)return '';
  const amount=value<0?'−'+shortNum(-value):shortNum(value);
  const full=`${value<0?'đang nợ ':''}${fmt(Math.abs(value))} xu`;
  return `<button type="button" class="iso-money iso-${kind}${value<0?' is-debt':''}" data-action="money" aria-label="${label}: ${full}. Xem tiền của bạn" title="${label}: ${full}"><span class="iso-money-mark">${icon(kind==='wallet'?'bag':'store',18)}</span><span><small>${label}</small><b data-testid="iso-${kind}">${amount}</b></span></button>`;
}

/** The town's one main button (owner 18/10: "giao diện mới khiến người ta khó chơi", "chữ nút gọn lại"): the next
 * step in a short word, the workplace under it. Inside a workplace the work bar and the task card take over: none.
 * Shift closed (#432): "Về quán" only walks in; the day opens inside, from the work bar's "Chuẩn bị ngày mới", once
 * the player has bought what they need. The one exception is the first workplace's very first day (quickOpen):
 * nothing to buy yet, so "Mở ca" still opens it in one tap, as arriving at its door does. */
export function goButton(m){
  if(m.mode==='work')return null;
  const sub=m.current?m.place:'';
  const [action,ico,label]=!m.current?['isoCareers','briefcase',m.fresh?'Tới quán':'Chọn nghề']:
    m.needsJob?['isoApply','note','Xin việc']:!m.open?(m.firstOpen?['isoOpen','sun','Mở ca']:['isoWork','store',m.home||'Về tiệm']):m.task?['isoMission','arrow','Làm tiếp']:
    m.done?['isoEnd','clock','Khép ca']:['isoWork','store','Vào làm'];
  const what=m.task?.title?` · ${m.task.title}`:'';
  return {action,icon:ico,label,sub,aria:`${label}${sub?` tại ${sub}`:''}${what}`};
}

/** Server text is escaped here; portrait art comes from the existing saved wardrobe. */
export function isometricHUDHTML(model,state={}){
  const m=model;
  const go=goButton(m);
  const nav=m.mode==='work'?[['isoTown','leaf','Ra đảo'],['isoCareers','briefcase','Công việc'],['isoChat','chats','Trò chuyện'],['isoMore','menu','Thêm']]:
    [['isoCareers','briefcase','Công việc'],['isoChat','chats','Trò chuyện'],['isoMore','menu','Thêm']];
  const active=m.activeTab||(m.mode==='work'?'isoCareers':'isoTown');
  const unread=m.chatUnread>99?'99+':m.chatUnread||'';
  const tab=([action,ico,label])=>action==='isoChat'?
    `<button type="button" class="iso-tab iso-chat-tab${m.chatOnline?'':' is-offline'}" data-action="isoChat" aria-label="Trò chuyện · ${esc(m.chatStatus)}${m.chatUnread?` · ${m.chatUnread} tin chưa đọc`:''}" aria-haspopup="dialog" aria-controls="townChat">${icon(ico,22)}<span>${label}</span><em class="iso-chat-unread"${m.chatUnread?'':' hidden'}>${unread}</em></button>`:
    control(label,action,ico,`iso-tab${action===active?' is-active':''}`,action==='isoMore'?` aria-controls="rail" aria-expanded="${m.menuOpen}"`:action===active?' aria-current="page"':'');
  return `<header class="iso-top" aria-label="Bạn và tiền của bạn">
    <button type="button" class="iso-profile" data-action="isoAvatar" aria-label="Nhân vật của ${esc(m.name)}. Mở tủ đồ"><span class="iso-portrait">${myPortrait(state,42,'Nhân vật của bạn')}</span><span class="iso-profile-copy"><b>${esc(m.name)}</b><small>${m.day!=null?`Ngày ${fmt(m.day)}`:'Phố Có Chuyện'}</small></span></button>
    <div class="iso-pockets">${moneyChip('Ví',m.money.wallet,'wallet')}${moneyChip('Quỹ',m.money.fund,'fund')}</div>
  </header>
  <nav class="iso-quick" aria-label="Lối tắt">
    ${control('Chỉ đường','isoGuide','compass','iso-quick-button iso-guide-button',' aria-label="Chỉ đường: chọn nơi muốn tới, nhân vật tự đi" aria-haspopup="dialog"')}
    <details class="iso-tools"><summary class="iso-quick-button" data-iso-focus="iso-tools" aria-controls="isoToolsOptions">${icon('menu',22)}<span>Tiện ích</span>${m.fairOpen?'<i class="iso-tools-dot" title="Chợ đen đang mở" aria-label="Chợ đen đang mở"></i>':''}</summary>
      <div class="iso-tools-options" id="isoToolsOptions" role="group" aria-label="Tiện ích trong phố">
        <b class="iso-tools-heading">Sổ tay trong phố</b>
        ${control('Sổ việc','isoQueue','clipboard','iso-tool',' aria-label="Sổ việc đang chờ"')}
        ${control('Người quen','people','people','iso-tool',' aria-label="Người quen trong phố"')}
        ${m.current?control('Hôm nay','status','clock','iso-tool',' aria-label="Hôm nay: giờ, tình trạng và chuyện cần để ý"'):''}
        ${m.shop?control('Cửa hàng','jrAccShop','bag','iso-tool iso-shop',' aria-label="Cửa hàng: phụ kiện, trang phục, phụ kiện đôi, cánh, đồ thú cưng, nhà và xe"'):''}
        ${m.forge?control('Cường hóa','jrForge','wrench','iso-tool iso-forge',' aria-label="Cường hóa: ghép cánh, ghép thú, nâng đồ thú cưng"'):''}
        ${control('Túi đồ','isoBag','bag','iso-tool')}
        ${control('Rương & lì xì','isoPickups','gift','iso-tool',' aria-label="Rương và lì xì: danh sách, đi tới và nhặt"')}
        ${m.ride?control(esc(m.ride),'isoRide','bike','iso-tool',` aria-label="${esc(m.ride)}: chạm để đổi xe hoặc đi bộ"`):''}
        ${m.fly?control(esc(m.fly),'isoFly','sparkles','iso-tool iso-fly',` aria-label="${esc(m.fly)}: bay nhanh như đi xe, không lái xe khi bay"`):''}
        ${m.fairOpen?control('Chợ đen','fair','basket','iso-tool iso-fair-button',' aria-label="Chợ đen đang mở"'):''}
        ${control('Cài đặt','settings','settings','iso-tool',' aria-label="Cài đặt"')}
        ${(m.utilityGroups||[]).map(group=>`<details class="iso-outings" data-iso-group="${group.id}"><summary class="iso-tool" data-iso-focus="iso-${group.id}" aria-controls="isoUtility-${group.id}">${icon(group.icon,22)}<span>${group.label}</span>${icon('arrow',16)}</summary><div class="iso-outings-menu" id="isoUtility-${group.id}" role="group" aria-label="${group.label}">${group.items.map(item=>control(item.label,item.action,item.icon,'iso-outing-button',Object.entries({'utility-id':item.id||item.action,...(item.actionData||{})}).map(([k,v])=>" data-"+k+"=\""+esc(v)+"\"").join(''))).join('')}</div></details>`).join('')}
        ${m.mode==='town'?`<details class="iso-outings"><summary class="iso-tool" data-iso-focus="iso-outings">${icon('fish',22)}<span>Thư giãn</span>${icon('arrow',16)}</summary><div class="iso-outings-menu" role="group" aria-label="Hoạt động ngoài trời">${[['fishing','fish','Câu cá'],['boat','boat','Chèo thuyền'],['pool','pool','Bơi']].map(([kind,ico,label])=>control(label,'isoLeisure',ico,'iso-outing-button',` data-kind="${kind}" aria-label="${label}: mở địa điểm ngoài trời"`)).join('')}</div></details>`:''}
      </div>
    </details>
  </nav>
  ${go?`<button type="button" class="iso-go" data-action="${go.action}" aria-label="${esc(go.aria)}">${icon(go.icon,22)}<span><b>${esc(go.label)}</b>${go.sub?`<small>${esc(go.sub)}</small>`:''}</span></button>`:''}
  <div class="iso-camera${m.cameraOpen?' is-open':''}" role="group" aria-label="Góc nhìn Đảo Hoàng Sa">
    ${control('Góc nhìn','isoCamera','overview','iso-camera-toggle',' aria-label="Điều chỉnh góc nhìn" aria-expanded="'+Boolean(m.cameraOpen)+'" aria-controls="isoCameraOptions"')}
    <div class="iso-camera-options" id="isoCameraOptions"${m.cameraOpen?'':' hidden'}>
    ${control('Phóng to','isoZoomIn','plus','iso-round',' aria-label="Phóng to cảnh" title="Phóng to"')}
    ${control('Thu nhỏ','isoZoomOut','minus','iso-round',' aria-label="Thu nhỏ cảnh" title="Thu nhỏ"')}
    ${control('Về giữa','isoRecenter','compass','iso-round',' aria-label="Đưa góc nhìn về nhân vật" title="Về giữa"')}
    ${control('Toàn đảo','isoOverview','overview','iso-round iso-overview',' aria-label="Xem toàn đảo" title="Xem toàn đảo"')}
    </div>
  </div>
  <p class="iso-key-hint"><kbd>W A S D</kbd> / <kbd>↑ ↓ ← →</kbd> di chuyển · Chạm đường để đi</p>
  <nav class="iso-nav${nav.length>3?' is-four':''}" aria-label="Điều hướng chính">${nav.map(tab).join('')}</nav>`;
}

function syncMenu(){
  const root=document.documentElement;
  const open=root.classList.contains('menu-open');
  const button=document.querySelector('#isoHUD [data-action="isoMore"]');
  button?.setAttribute('aria-expanded',String(open));
  button?.classList.toggle('is-active',open);
  if(!open&&document.getElementById('rail')?.contains(document.activeElement))button?.focus({preventScroll:true});
}

function closeCamera(){
  cameraOpen=false;
  if(typeof document==='undefined')return;
  const camera=document.querySelector('#isoHUD .iso-camera');
  camera?.classList.remove('is-open');
  camera?.querySelector('[data-action="isoCamera"]')?.setAttribute('aria-expanded','false');
  const options=camera?.querySelector('.iso-camera-options');
  if(options)options.hidden=true;
  rendered='';
  syncDisclosureLayer();
}

// Safari 15 cannot derive this layer with :has(). Only an open HUD disclosure
// needs to paint above the separate workplace task cards; dialogs retain ownership.
function syncDisclosureLayer(){
  if(typeof document==='undefined')return;
  const hud=document.getElementById('isoHUD');
  if(!hud?.dataset)return;
  const open=!document.querySelector('dialog[open]')&&(cameraOpen||['iso-tools'].some(name=>document.querySelector(`#isoHUD .${name}[open]`)));
  hud.dataset.disclosureOpen=String(Boolean(open));
  document.documentElement?.classList?.toggle?.('iso-disclosure-open',Boolean(open));  // isometric.css hides the guide pill under it (#344)
}

const disclosures=(root,selector)=>root.querySelectorAll?[...root.querySelectorAll(selector)]:[root.querySelector(selector)].filter(Boolean);

function closeDisclosure(name,restoreFocus=false,except=null){
  if(typeof document==='undefined')return;
  const panels=disclosures(document,`#isoHUD .${name}[open]`).filter(details=>details!==except);
  if(!panels.length)return;
  if(name==='iso-tools')closeDisclosure('iso-outings');
  for(const details of panels)details.open=false;
  syncDisclosureLayer();
  if(restoreFocus)panels[0].querySelector('summary')?.focus({preventScroll:true});
}

function closeHUDDisclosures(){
  closeDisclosure('iso-tools');
  if(cameraOpen)closeCamera();
  syncDisclosureLayer();
}

function closeActionDisclosure(el){
  if(el?.closest?.('.iso-tools'))closeDisclosure('iso-tools',true);
}

/** Once per device: a newer player (life days 2–10) who has spent STUCK_MS in the town (tab in view, no dialog over it)
 * without a shift open is asked whether the old interface would suit them better. A shift opened ends the watch. */
const STUCK_MS=5*60e3,STUCK_TICK=15e3,STUCK_KEY='mnl.iso.stuckAsked';
function stuckWatch(){
  if(typeof document==='undefined'||typeof setInterval!=='function')return;
  try{if(localStorage.getItem(STUCK_KEY))return;}catch{return;}
  let spent=0;
  const timer=setInterval(()=>{
    const env=getEnvironment?.(),s=env?.api?.state;if(!s)return;
    const day=Number(s.journey?.life_day)||0;
    if(!s.journey?.story||day>10||Object.values(s.careers||{}).some(c=>c?.open)){clearInterval(timer);return;}
    if(day<2||document.visibilityState!=='visible'||document.querySelector('dialog[open]')||env.world?.mode!=='town')return;
    if((spent+=STUCK_TICK)<STUCK_MS)return;
    clearInterval(timer);
    try{localStorage.setItem(STUCK_KEY,'1');}catch{/* private mode: asked this visit only */}
    import('./interface-mode.js').then(m=>m.askInterface(env,{title:'Thấy khó chơi?',text:'Bấm nút lớn ở giữa màn hình để về chỗ làm, rồi Chuẩn bị ngày mới. Nếu vẫn rối, giao diện cũ đơn giản hơn: tiệm và các nút làm việc luôn ở trước mặt. Tiến trình giữ nguyên.'})).catch(()=>{});
  },STUCK_TICK);
}

/** Called once after the app's real state has loaded. Safe to call again after a recovery. */
export function bootIsometricShell(envGetter){
  getEnvironment=typeof envGetter==='function'?envGetter:()=>envGetter;
  const root=document.documentElement;
  root.dataset.game='isometric';
  document.body.classList.add('isometric-game');
  let hud=document.getElementById('isoHUD');
  if(!hud){
    hud=document.createElement('div');
    hud.id='isoHUD';
    (document.getElementById('stage')||document.getElementById('app'))?.append(hud);
    rendered='';
  }
  if(!listening){
    listening=true;
    window.addEventListener('mnl:iso-mode',()=>{closeHUDDisclosures();updateIsometricShell(getEnvironment?.());});
    window.addEventListener('layoutchange',()=>updateIsometricShell(getEnvironment?.()));
    stuckWatch();
    // Subscribe to the same live data as the real inbox; the entry itself is always discoverable.
    import('./v4/live.js').then(module=>{
      const {live,liveBoot}=module;
      // The entry is already visible; do not wait for the app's deferred feature boot.
      chatLive=live;
      for(const event of ['connection','welcome','down','state','msg','read','quiet','cleared','blocked','chan'])live.on(event,()=>updateIsometricShell(getEnvironment?.()));
      const environment=getEnvironment?.();
      if(environment?.bootLive)environment.bootLive(module);else liveBoot(environment);
      updateIsometricShell(getEnvironment?.());
    }).catch(()=>{});
    // The existing shell closes its More menu on outside click/Escape, without a server change.
    new MutationObserver(syncMenu).observe(root,{attributes:true,attributeFilter:['class']});
    new MutationObserver(records=>{
      if(records.some(record=>record.target.tagName==='DIALOG'&&record.target.open))closeHUDDisclosures();
    }).observe(document.body,{subtree:true,attributes:true,attributeFilter:['open']});
    const dismissOutside=event=>{
      for(const name of ['iso-outings','iso-tools']){
        const details=document.querySelector(`#isoHUD .${name}[open]`);
        if(details&&!details.contains(event.target))closeDisclosure(name);
      }
      // Do not replace the tapped control between pointerdown and click.
      if(cameraOpen&&!event.target.closest?.('.iso-camera'))closeCamera();
    };
    window.addEventListener('pointerdown',dismissOutside);
    window.addEventListener('focusin',dismissOutside);
    window.addEventListener('click',event=>{
      const button=event.target.closest?.('[data-action]');
      if(button)closeActionDisclosure(button);
    },true);
    window.addEventListener('toggle',event=>{
      if(!event.target.matches?.('.iso-tools,.iso-outings'))return;
      if(event.target.open&&event.target.matches('.iso-tools')&&cameraOpen)closeCamera();
      if(event.target.open&&event.target.matches('.iso-outings'))closeDisclosure('iso-outings',false,event.target);
      syncDisclosureLayer();
    },true);
    window.addEventListener('keydown',event=>{
      if(event.key!=='Escape'||document.querySelector('dialog[open]'))return;
      const name=['iso-outings','iso-tools'].find(name=>document.querySelector(`#isoHUD .${name}[open]`));
      if(!name&&!cameraOpen)return;
      // The innermost open disclosure owns Escape before the app's pause shortcut.
      event.preventDefault();event.stopPropagation();
      if(name)closeDisclosure(name,true);
      else if(cameraOpen){closeCamera();document.querySelector('#isoHUD [data-action="isoCamera"]')?.focus({preventScroll:true});}
    },true);
  }
  updateIsometricShell(getEnvironment?.());
}

export function updateIsometricShell(env){
  if(!env?.api?.state||typeof document==='undefined')return;
  const hud=document.getElementById('isoHUD');
  if(!hud)return;
  // The legacy career list omits its close control until a workplace is chosen.
  // The isometric town is already a useful destination in completed/free-play onboarding.
  const state=env.api.state;
  if(!state.current&&(state.journey?.intro||['male','female'].includes(state.journey?.gender)||state.journey?.story===false)&&env.ui?.view==='home'&&env.ui.jrView==='home'){
    const header=document.querySelector('#sheetContent .jr-home > .jr-top');
    if(header&&!header.querySelector('[data-action="close"], [data-iso-close]')){
      const close=document.createElement('button');
      close.type='button';
      close.className='btn ghost small jr-close';
      close.dataset.action='isoTown';
      close.dataset.isoClose='';
      close.setAttribute('aria-label','Đóng danh sách nghề, về Đảo Hoàng Sa');
      close.innerHTML=icon('x',20);
      header.append(close);
    }
  }
  const model=isometricHUDModel(env.api.state,env.api.content,env.world?.mode,chatLive||{},env.api.live||{});
  const root=document.documentElement;
  if(root.dataset.sceneMode!==model.mode)root.dataset.sceneMode=model.mode;   // 23/10 lag: an attribute write, even the same value, wakes the joystick's observer
  if(hud.dataset.sceneMode!==model.mode)hud.dataset.sceneMode=model.mode;
  model.menuOpen=root.classList.contains('menu-open');
  model.cameraOpen=cameraOpen;
  if(env.ui?.view&&document.getElementById('sheet')?.open)model.activeTab=env.ui.isoTab;
  const html=isometricHUDHTML(model,env.api.state);
  if(html!==rendered){
    const active=document.activeElement;
    const action=hud.contains(active)?active?.dataset?.action:null;
    const focusKey=hud.contains(active)?active?.dataset?.isoFocus:null;
    const kind=action==='isoLeisure'?active.dataset.kind:null;
    const utilityId=hud.contains(active)?active?.dataset?.utilityId:null;
    const openDetails=['iso-tools','iso-outings'].flatMap(name=>disclosures(hud,'.'+name)
      .filter(details=>details.open).map(details=>'.'+name+(name==='iso-outings'?(details.dataset?.isoGroup?`[data-iso-group="${details.dataset.isoGroup}"]`:':not([data-iso-group])'):'')));
    hud.innerHTML=html;
    rendered=html;
    for(const selector of openDetails)hud.querySelector(selector)?.setAttribute('open','');
    if(utilityId)hud.querySelector(`[data-utility-id="${utilityId}"]`)?.focus({preventScroll:true});
    else if(action)hud.querySelector(`[data-action="${action}"]${kind?`[data-kind="${kind}"]`:''}`)?.focus({preventScroll:true});
    else if(focusKey)hud.querySelector(`[data-iso-focus="${focusKey}"]`)?.focus({preventScroll:true});
  }
  syncMenu();
  syncDisclosureLayer();
}

function changeMode(mode,env){
  env.ui&&(env.ui.isoTab=null);
  env.closeSheet();
  env.world?.setMode?.(mode);
  updateIsometricShell(env);
}

/** The career picker, fresh each time (v4/career-pick.js reads these ui fields). */
const PICK=Object.freeze({homeMode:'list',jrView:'home'});   // Công việc: the places as before 2.5.5 (owner 23/10 "như màn cũ"), 🔎 Tìm nghề on top
/** Return false for normal app actions; no money/task/choose commands originate in this shell. */
export async function isometricAction(action,data={},el=null,env){
  if(!action?.startsWith('iso')||!env)return false;
  const model=isometricHUDModel(env.api?.state,env.api?.content,env.world?.mode);
  const act=(name,payload={})=>env.act(name,payload);
  switch(action){
    case'isoTown':changeMode('town',env);break;
    case'isoWork':
      if(!model.current&&model.fresh){await firstJob(env);break;}
      if(!model.current){env.openSheet('home',PICK);break;}
      changeMode('work',env);break;
    case'isoCareers':if(!model.current&&model.fresh){await firstJob(env);break;}   // day 1: the first workplace, not the whole journey page
      env.ui&&(env.ui.isoTab='isoCareers');env.openSheet('home',PICK);break;
    case'isoAvatar':env.ui&&(env.ui.isoTab='isoAvatar');env.openSheet('home',{jrView:'wardrobe'});break;
    case'isoRide':{const say=nextTownRide(env.api?.state,env.api?.content);if(env.api?.state&&env.api?.content)env.world?.update?.(env.api.state,env.api.content);updateIsometricShell(env);if(say)env.toast?.(say);break;}
    case'isoFly':{const say=toggleTownFly(env.api?.state,env.api?.content);if(env.api?.state&&env.api?.content)env.world?.update?.(env.api.state,env.api.content);updateIsometricShell(env);if(say)env.toast?.(say);break;}   // 🪽 Bay / Hạ cánh
    case'isoBag':env.ui&&(env.ui.isoTab='isoBag');if(model.current)await act('warehouse');else env.openSheet('home',PICK);break;
    case'isoChat':await act('liveChat');break;
    case'isoGuide':await openGuide(env);break;   // 🧭 iso-guide.js
    case'isoPickups':closeHUDDisclosures();await (await import('./isometric-pickups.js')).openPickups(env);break;   // ♿ #428: chests and lì xì as a list
    case'isoGo':await goTo(String(data.dest||''),env);break;
    case'isoCamera':{const open=!cameraOpen;closeHUDDisclosures();cameraOpen=open;syncDisclosureLayer();break;}
    case'isoMore':
      await act('v4Menu');
      if(typeof document!=='undefined'&&document.documentElement.classList.contains('menu-open')){
        requestAnimationFrame(()=>[...document.querySelectorAll('#rail button')].find(button=>button.getClientRects().length)?.focus({preventScroll:true}));
      }
      break;
    case'isoMission':
      if(!model.current){await act('isoCareers');break;}
      changeMode('work',env);
      if(model.needsJob)await act('jobapp');
      else if(!model.open)await act('prepare');
      else if(model.task)await act('job',{task:model.task.id});
      else await act('queue');
      break;
    case'isoPrepare':changeMode('work',env);await act('prepare');break;
    case'isoOpen':   // "Mở ca" (the first day only, see goButton): into the workplace and the shift opens at once; when it cannot, the prepare sheet says why
      changeMode('work',env);await act('start');
      if(model.current&&!env.api?.state?.careers?.[model.current]?.open&&!(typeof document!=='undefined'&&document.querySelector('dialog[open]')))await act('prepare');
      break;
    case'isoClassic':{const {askInterface}=await import('./interface-mode.js');await askInterface(env,CLASSIC);break;}   // ☰ Thêm → "Giao diện cũ"
    case'isoEnd':changeMode('work',env);await act('end');break;   // first day, every customer served: close the shift (its own confirm)
    case'isoApply':changeMode('work',env);await act('jobapp');break;
    case'isoQueue':if(model.current)await act('queue');else env.openSheet('home',PICK);break;
    case'isoZoomIn':env.world?.zoomBy?.(1.15);break;
    case'isoZoomOut':env.world?.zoomBy?.(1/1.15);break;
    case'isoRecenter':env.world?.recenter?.();break;
    case'isoOverview':env.world?.overviewIsland?.();break;
    case'isoLeisure':
      if(!['fishing','boat','pool'].includes(data.kind))return false;
      closeActionDisclosure(el);
      await act('leisurePlace',{kind:data.kind});break;
    default:return false;
  }
  updateIsometricShell(env);
  return true;
}
