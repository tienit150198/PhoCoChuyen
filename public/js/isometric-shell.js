/** Small DOM controls over the town. All gameplay still goes through the app's existing actions. */
import {escapeHTML as esc} from './icons.js';
import {uiIcon as icon} from './isometric/ui-icons.js';
import {hudMoney,shortNum} from './v4/wealth.js';
import {myPortrait} from './v4/look.js';

const ENDED=new Set(['completed','referred','cancelled']);
const fmt=n=>Number(n).toLocaleString('vi-VN');
let getEnvironment=null;
let listening=false;
let rendered='';
let chatLive=null;

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
  const chatStatus=chatOff?'Tạm nghỉ':chatOnline?'Cả phố · Bạn bè':
    connection&&!connection.url?'Chưa khả dụng':
    social.state==='connecting'?'Đang kết nối':
    social.state==='down'?'Mất kết nối':social.state==='off'?'Không khả dụng':'Chưa kết nối';
  return {current,mode:sceneMode,name:state.name||'Bạn',day,place,careerName:meta.name||place,
    sceneTitle:sceneMode==='work'?place:'Đảo Hoàng Sa',money:hudMoney(state,current),
    task,taskCount:tasks.length,needsJob,open:Boolean(room?.open),
    missionAction:!current?'isoCareers':needsJob?'isoApply':!room.open?'isoPrepare':task?'isoMission':'isoQueue',
    chatUnread:Math.max(0,Number(social.unread?.())||0),chatOnline,chatOff,chatStatus,
    menuOpen:false};
}

const control=(label,action,ico,cls='',extra='')=>`<button type="button" class="${cls}" data-action="${action}"${extra}>${icon(ico,22)}<span>${label}</span></button>`;

function moneyChip(label,value,kind){
  if(value==null)return '';
  const amount=value<0?'−'+shortNum(-value):shortNum(value);
  const full=`${value<0?'đang nợ ':''}${fmt(Math.abs(value))} xu`;
  return `<button type="button" class="iso-money iso-${kind}${value<0?' is-debt':''}" data-action="money" aria-label="${label}: ${full}. Xem tiền của bạn" title="${label}: ${full}"><span class="iso-money-mark">${icon(kind==='wallet'?'bag':'store',18)}</span><span><small>${label}</small><b data-testid="iso-${kind}">${amount}</b></span></button>`;
}

/** Server text is escaped here; portrait art comes from the existing saved wardrobe. */
export function isometricHUDHTML(model,state={}){
  const m=model;
  const missionTitle=!m.current?'Hôm nay, thử làm nghề gì?':m.needsJob?`Xin việc tại ${m.place}`:!m.open?'Ca làm đang nghỉ':m.task?.title||'Bạn đã làm hết việc đang chờ';
  const missionLabel=!m.current?'Chọn nghề':m.needsJob?'Xem tuyển dụng':!m.open?'Chuẩn bị ca':m.task?'Làm tiếp':'Mở sổ việc';
  const missionMeta=m.current&&m.open&&!m.needsJob?`${m.taskCount} việc đang chờ`:!m.current?'Chọn nghề hôm nay':m.needsJob?'Tuyển dụng':'Ca làm của bạn';
  const missionAria=`${missionLabel}: ${missionTitle}`;
  const nav=[['isoTown','map','Phố'],['isoCareers','briefcase','Công việc'],['isoAvatar','user','Nhân vật'],['isoBag','bag','Túi đồ'],['isoMore','menu','Thêm']];
  const active=m.activeTab||(m.mode==='work'?'isoCareers':'isoTown');
  return `<header class="iso-top" aria-label="Bạn và tiền của bạn">
    <button type="button" class="iso-profile" data-action="isoAvatar" aria-label="Nhân vật của ${esc(m.name)}. Mở tủ đồ"><span class="iso-portrait">${myPortrait(state,42,'Nhân vật của bạn')}</span><span class="iso-profile-copy"><b>${esc(m.name)}</b><small>${m.day!=null?`Ngày ${fmt(m.day)}`:'Phố Có Chuyện'}</small></span></button>
    <div class="iso-pockets">${moneyChip('Ví',m.money.wallet,'wallet')}${moneyChip('Quỹ',m.money.fund,'fund')}</div>
    ${control('Cài đặt','settings','settings','iso-round iso-settings',' aria-label="Cài đặt" title="Cài đặt"')}
  </header>
  <nav class="iso-quick" aria-label="Lối tắt">
    ${control('Sổ việc','isoQueue','clipboard','iso-quick-button',' aria-label="Sổ việc đang chờ"')}
    ${control('Người quen','people','people','iso-quick-button',' aria-label="Người quen trong phố"')}
    ${m.current?control('Hôm nay','status','clock','iso-quick-button',' aria-label="Hôm nay: giờ, tình trạng và chuyện cần để ý"'):''}
    ${m.mode==='town'?`<details class="iso-outings"><summary class="iso-quick-button">${icon('fish',22)}<span>Thư giãn</span></summary><div class="iso-outings-menu" role="group" aria-label="Hoạt động ngoài trời"><b>Ra ngoài chơi</b>${[['fishing','fish','Câu cá'],['boat','boat','Chèo thuyền'],['pool','pool','Bơi']].map(([kind,ico,label])=>control(label,'isoLeisure',ico,'iso-outing-button',` data-kind="${kind}" aria-label="${label}: mở địa điểm ngoài trời"`)).join('')}</div></details>`:''}
  </nav>
  <button type="button" class="iso-mission" data-action="${m.missionAction}" aria-label="${esc(missionAria)}"><span class="iso-mission-heading">${icon('note',18)}<small>${esc(missionMeta)}</small></span><b>${esc(missionTitle)}</b><span class="iso-mission-next">${esc(missionLabel)} ${icon('arrow',16)}</span></button>
  <div class="iso-camera" role="group" aria-label="Góc nhìn Đảo Hoàng Sa">
    ${control('Phóng to','isoZoomIn','plus','iso-round',' aria-label="Phóng to cảnh" title="Phóng to"')}
    ${control('Thu nhỏ','isoZoomOut','minus','iso-round',' aria-label="Thu nhỏ cảnh" title="Thu nhỏ"')}
    ${control('Về giữa','isoRecenter','compass','iso-round',' aria-label="Đưa góc nhìn về nhân vật" title="Về giữa"')}
    ${control('Toàn đảo','isoOverview','overview','iso-round iso-overview',' aria-label="Xem toàn đảo" title="Xem toàn đảo"')}
  </div>
  <button type="button" class="iso-chat${m.chatOnline?'':' is-offline'}" data-action="isoChat" aria-label="Trò chuyện${m.chatUnread?` · ${m.chatUnread} tin chưa đọc`:''}" aria-haspopup="dialog" aria-controls="townChat"><span class="iso-chat-mark">${icon('chats',26)}</span><span class="iso-chat-copy"><b>Trò chuyện</b><small>${esc(m.chatStatus)}</small></span><em class="iso-chat-unread"${m.chatUnread?'':' hidden'}>${m.chatUnread>99?'99+':m.chatUnread||''}</em></button>
  <p class="iso-key-hint"><kbd>W A S D</kbd> / <kbd>↑ ↓ ← →</kbd> di chuyển · Chạm đường để đi</p>
  <div class="iso-scene"><span class="iso-scene-symbol">${icon(m.mode==='work'?'store':'leaf',24)}</span><span class="iso-scene-copy"><small>${esc(m.mode==='work'?m.careerName:'Phố Có Chuyện')}</small><b>${esc(m.sceneTitle)}</b></span><button type="button" class="iso-scene-go" data-action="${m.mode==='work'?'isoTown':m.current?'isoWork':'isoCareers'}" aria-label="${esc(m.mode==='work'?'Ra Đảo Hoàng Sa':m.current?`Vào làm tại ${m.place}`:'Chọn một nghề trên đảo')}">${m.mode==='work'?'Ra đảo':m.current?'Vào làm':'Chọn nghề'}${icon('arrow',17)}</button></div>
  <nav class="iso-nav" aria-label="Điều hướng chính">${nav.map(([action,ico,label])=>control(label,action,ico,`iso-tab${action===active?' is-active':''}`,action==='isoMore'?` aria-controls="rail" aria-expanded="${m.menuOpen}"`:action===active?' aria-current="page"':'')).join('')}</nav>`;
}

function syncMenu(){
  const root=document.documentElement;
  const open=root.classList.contains('menu-open');
  const button=document.querySelector('#isoHUD [data-action="isoMore"]');
  button?.setAttribute('aria-expanded',String(open));
  button?.classList.toggle('is-active',open);
  if(!open&&document.getElementById('rail')?.contains(document.activeElement))button?.focus({preventScroll:true});
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
    window.addEventListener('mnl:iso-mode',()=>updateIsometricShell(getEnvironment?.()));
    window.addEventListener('layoutchange',()=>updateIsometricShell(getEnvironment?.()));
    // Subscribe to the same live data as the real inbox; the entry itself is always discoverable.
    import('./v4/live.js').then(({live,liveBoot})=>{
      // The entry is already visible; do not wait for the app's deferred feature boot.
      liveBoot(getEnvironment?.());
      chatLive=live;
      for(const event of ['connection','welcome','down','state','msg','read','quiet','cleared','blocked','chan'])live.on(event,()=>updateIsometricShell(getEnvironment?.()));
      updateIsometricShell(getEnvironment?.());
    }).catch(()=>{});
    // The existing shell closes its More menu on outside click/Escape, without a server change.
    new MutationObserver(syncMenu).observe(root,{attributes:true,attributeFilter:['class']});
    window.addEventListener('pointerdown',event=>{
      const outing=document.querySelector('#isoHUD .iso-outings[open]');
      if(outing&&!outing.contains(event.target))outing.open=false;
    });
    window.addEventListener('keydown',event=>{
      const outing=document.querySelector('#isoHUD .iso-outings[open]');
      if(event.key==='Escape'&&outing){outing.open=false;outing.querySelector('summary')?.focus({preventScroll:true});}
    });
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
  if(!state.current&&(state.journey?.intro||state.journey?.story===false)&&env.ui?.view==='home'&&env.ui.jrView==='home'){
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
  root.dataset.sceneMode=model.mode;
  hud.dataset.sceneMode=model.mode;
  model.menuOpen=root.classList.contains('menu-open');
  if(env.ui?.view&&document.getElementById('sheet')?.open)model.activeTab=env.ui.isoTab;
  const html=isometricHUDHTML(model,env.api.state);
  if(html!==rendered){
    const active=document.activeElement;
    const action=hud.contains(active)?active?.dataset?.action:null;
    const outingOpen=hud.querySelector('.iso-outings')?.open;
    hud.innerHTML=html;
    rendered=html;
    if(outingOpen&&model.mode==='town')hud.querySelector('.iso-outings')?.setAttribute('open','');
    if(action)hud.querySelector(`[data-action="${action}"]`)?.focus({preventScroll:true});
  }
  syncMenu();
}

function changeMode(mode,env){
  env.ui&&(env.ui.isoTab=null);
  env.closeSheet();
  env.world?.setMode?.(mode);
  updateIsometricShell(env);
}

/** Return false for normal app actions; no money/task/choose commands originate in this shell. */
export async function isometricAction(action,data={},el=null,env){
  if(!action?.startsWith('iso')||!env)return false;
  const model=isometricHUDModel(env.api?.state,env.api?.content,env.world?.mode);
  const act=(name,payload={})=>env.act(name,payload);
  switch(action){
    case'isoTown':changeMode('town',env);break;
    case'isoWork':
      if(!model.current){env.openSheet('home',{homeMode:'list',jrView:'home'});break;}
      changeMode('work',env);break;
    case'isoCareers':env.ui&&(env.ui.isoTab='isoCareers');env.openSheet('home',{homeMode:'list',jrView:'home'});break;
    case'isoAvatar':env.ui&&(env.ui.isoTab='isoAvatar');env.openSheet('home',{jrView:'wardrobe'});break;
    case'isoBag':env.ui&&(env.ui.isoTab='isoBag');if(model.current)await act('warehouse');else env.openSheet('home',{homeMode:'list',jrView:'home'});break;
    case'isoChat':await act('liveChat');break;
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
    case'isoApply':changeMode('work',env);await act('jobapp');break;
    case'isoQueue':if(model.current)await act('queue');else env.openSheet('home',{homeMode:'list',jrView:'home'});break;
    case'isoZoomIn':env.world?.zoomBy?.(1.15);break;
    case'isoZoomOut':env.world?.zoomBy?.(1/1.15);break;
    case'isoRecenter':env.world?.recenter?.();break;
    case'isoOverview':env.world?.overviewIsland?.();break;
    case'isoLeisure':
      if(!['fishing','boat','pool'].includes(data.kind))return false;
      {const outing=el?.closest?.('.iso-outings');if(outing){outing.open=false;outing.querySelector('summary')?.focus({preventScroll:true});}}
      await act('leisurePlace',{kind:data.kind});break;
    default:return false;
  }
  updateIsometricShell(env);
  return true;
}
