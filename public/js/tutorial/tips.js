/** In-context tips for a brand-new player: the tutorial happens while playing. One short bubble points at the
 * control that matters right now; it never dims the screen, never asks for "Tiếp", and goes away when the
 * player does the thing (or after a few seconds for a look-here tip). "×" turns the remaining tips off.
 * The full coach-mark tour (tour.js) stays in Cài đặt → Xem hướng dẫn → "Xem lại hướng dẫn".
 *
 * Progress survives a reload (localStorage mnl.tut.tips); the end marks the tutorial done like the tour
 * (store.js markTourDone: settings.tutorialDone follows the account). Markup only: no game rule here. */
import {markTourDone,featuresSeen,markFeature} from './store.js';
import {coachOn} from './coach.js';
import {t as tr} from '../v4/i18n.js';

const KEY='mnl.tut.tips';
const get=()=>{try{return localStorage.getItem(KEY);}catch{return null;}};
const set=v=>{try{if(v==null)localStorage.removeItem(KEY);else localStorage.setItem(KEY,v);}catch{/* storage blocked */}};
export const tipsSaved=()=>get()!=null;

let E=null,run=null,bubble=null,timer=0,seen=false;
const $=(s,root=document)=>root.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const S=()=>E?.api?.state;
const room=()=>{const s=S();return s?.careers?.[s?.current];};
const view=()=>$('#sheet')?.open?E?.ui?.view:null;
/** Visible, enabled, on screen. */
function vis(el){
  if(!el||!el.isConnected||el.disabled)return null;
  const r=el.getBoundingClientRect();
  if(r.width<2||r.height<2||r.bottom<0||r.top>innerHeight)return null;
  const cs=getComputedStyle(el);return cs.visibility==='hidden'||cs.display==='none'?null:el;
}
const first=(sel,root=document)=>[...root.querySelectorAll(sel)].find(vis)||null;
/** The top-most open dialog (the bubble lives in the browser's top layer with it). */
const topDialog=()=>{const d=[...document.querySelectorAll('dialog[open]')];return d[d.length-1]||null;};
const calmStage=()=>!topDialog()&&!document.documentElement.classList.contains('menu-open');

/* ------------------------------------------------------------------ the tips */
/** `when`: the moment is here; `find`: the control to point at; `done`: the player did it;
 * `ttl`: a look-here tip leaves by itself after that many ms on screen; `cls` 'slim': a compact line that
 * sits beside the bottom bar and keeps off the customer card and the buttons (see placeBubble). */
const TIPS=[
  {id:'work',emoji:'👆',cls:'slim',text:'Bấm nút sáng để làm từng bước cho khách.',
    when:()=>view()==='job'&&!!room()?.open,
    find:()=>{const s=$('#sheet[open]');return s&&(first('.gd-cta',s)||first('.gd-pulse',s)||first('.sheet-body .btn.primary',s));},
    done:()=>run.acted||(room()?.metrics?.served|0)>0},
  {id:'close',emoji:'🌙',text:'Hết khách rồi: khép ca, xem tổng kết.',
    when:()=>!!room()?.open,
    find:()=>first('#sheet[open] .btn[data-action="end"]')||first('#taskHUD .btn[data-action="end"]'),
    done:()=>view()==='summary'||!room()?.open},
  {id:'journey',emoji:'🧭',ttl:9000,   // day 2: the rest of the street (on a phone it sits behind "Thêm")
    text:()=>first('#isoHUD .iso-nav [data-action="isoCareers"]')?'Công việc: tìm và đổi nơi làm.':first('#rail [data-action="jrPick"]')?'Đổi nghề: tìm và chọn nơi làm khác.':'Thêm → Đổi nghề: tìm và chọn nơi làm khác.',
    when:()=>calmStage()&&(S()?.journey?.life_day|0)>=2,
    find:()=>first('#isoHUD .iso-nav [data-action="isoCareers"]')||first('#rail [data-action="jrPick"]')||first('#dock [data-action="v4Menu"]'),
    done:()=>!calmStage()},   // opened Hành trình, the menu or anything else: it has done its job
];

/* ------------------------------------------------------------------ bubble */
/** A small bubble with an arrow, above or under the control; `onClose` for "×". `cls` 'inline': a line in the page's own
 * flow right under the control (no ring, no arrow), so it covers nothing; it moves with the page. */
export function showBubble({id,emoji,text,el,onClose,cls=''}){
  hideBubble();
  const host=topDialog()||document.body;
  bubble=document.createElement('div');bubble.className=`tut-layer tips ${cls}`.trim();bubble.dataset.tip=id;
  bubble.innerHTML=`<div class="tut-spot" aria-hidden="true"></div><div class="tut-bubble" role="status" aria-live="polite"><i class="tut-arrow" aria-hidden="true"></i>`+
    `<div class="tut-row"><span class="tut-emoji" aria-hidden="true">${esc(emoji)}</span><p class="tut-text">${esc(text)}</p>`+
    `<button type="button" class="tip-x" aria-label="Tắt gợi ý">×</button></div></div>`;
  bubble.querySelector('.tip-x').addEventListener('click',e=>{e.preventDefault();e.stopPropagation();const f=onClose;hideBubble();f?.();});
  // Inline: kept in place when the page redraws itself (app.js morph skips data-morph-keep).
  if(/\binline\b/.test(cls)){bubble.dataset.morphKeep='1';el.after(bubble);}else host.append(bubble);
  bubble._el=el;placeBubble();
  return bubble;
}
export function hideBubble(){bubble?.remove();bubble=null;}
export const bubbleUp=()=>!!bubble?.isConnected;
/** What a slim bubble keeps off: the buttons, tabs and the customer / order card of the screen it is on. */
const AVOID='button,[role="tab"],.gd-ctas,[class*="customer"],[class*="ticket"],[class*="guest"]';
const overlap=(a,b)=>Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));
/** Follow the control (a sheet scrolls, the layout changes); hide while it is off screen. A slim bubble
 * stands beside the bottom bar the control sits in, on the side (above or under) where it covers the least
 * of the customer card and the buttons, and never the control itself. */
export function placeBubble(){
  if(!bubble)return;
  if(bubble.classList.contains('inline')){bubble.hidden=false;return;}   // in the flow: nothing to place
  const el=bubble._el,r=vis(el)?el.getBoundingClientRect():null;
  const b=bubble.querySelector('.tut-bubble'),arrow=bubble.querySelector('.tut-arrow'),spot=bubble.querySelector('.tut-spot');
  bubble.hidden=!r;if(!r)return;
  const pad=5;Object.assign(spot.style,{left:r.left-pad+'px',top:r.top-pad+'px',width:r.width+2*pad+'px',height:r.height+2*pad+'px'});
  const W=innerWidth,H=innerHeight,m=12,bw=Math.min(320,W-2*m),bh=b.offsetHeight||64;
  b.style.width=bw+'px';
  const left=Math.round(Math.min(W-bw-m,Math.max(m,r.left+r.width/2-bw/2)));
  const clamp=t=>Math.round(Math.max(m,Math.min(H-bh-m,t)));
  let up,top;
  if(bubble.classList.contains('slim')){
    const bar=el.closest('.gd-ctas'),a=(bar&&vis(bar)?bar:el).getBoundingClientRect();
    const root=bubble.parentElement||document.body;
    const keep=[...root.querySelectorAll(AVOID)].filter(x=>x!==el&&!x.contains(el)&&!b.contains(x)&&vis(x)).map(x=>x.getBoundingClientRect());
    const cost=t=>{const box={left,right:left+bw,top:t,bottom:t+bh};
      return keep.reduce((s,q)=>s+overlap(box,q),0)+4*overlap(box,r)+(t<m||t+bh>H-m?1e6:0);};
    const upT=a.top-10-bh,downT=a.bottom+10;
    up=cost(upT)<cost(downT);
    top=clamp(up?upT:downT);
  }else{
    const above=r.top-14-bh>=m,below=r.bottom+14+bh<=H-m;
    up=r.top>H*0.5?above:!below&&above;   // controls low on the screen get the bubble above them
    top=clamp(up?r.top-pad-12-bh:r.bottom+pad+12);
  }
  b.style.left=left+'px';b.style.top=top+'px';
  arrow.dataset.side=up?'bottom':'top';arrow.hidden=false;
  arrow.style.left=Math.round(Math.min(bw-22,Math.max(10,r.left+r.width/2-left-8)))+'px';
}

/* ------------------------------------------------------------------ flow */
function tick(){
  if(!run)return;
  const tip=TIPS[run.i];
  if(!tip){finish();return;}
  if(coachOn()){if(bubbleUp())hideBubble();return;}   // 🧭 the workplace coach says the same, step by step: one voice at a time
  if(run.shown&&(tip.done()||(tip.ttl&&performance.now()-run.shown>tip.ttl))){next();return;}
  if(!tip.when()){if(bubbleUp()&&bubble.dataset.tip===tip.id)hideBubble();return;}
  const el=tip.find(),top=topDialog();
  // Not there, or under a newer dialog (a confirm, a scene): wait out of sight.
  if(!el||top&&!top.contains(el)){if(bubbleUp())bubble.hidden=true;return;}
  if(!bubbleUp()||bubble.dataset.tip!==tip.id||bubble._el!==el||bubble.parentElement!==(top||document.body)){
    showBubble({id:tip.id,emoji:tip.emoji,text:typeof tip.text==='function'?tip.text():tip.text,el,cls:tip.cls,onClose:()=>stopTips('off')});
  }else placeBubble();
  run.shown||=performance.now();
}
function next(){
  hideBubble();run.i++;run.shown=0;run.acted=false;
  if(run.i>=TIPS.length){finish();return;}
  set(TIPS[run.i].id);
}
function finish(){stopTips('done');}
export function stopTips(reason){
  if(!run)return;
  run=null;clearInterval(timer);timer=0;hideBubble();set(null);markTourDone(E);
  if(reason==='off')E?.toast?.('Đã tắt gợi ý. Hướng dẫn ở Cài đặt 📘','hint');
}
export const tipsRunning=()=>!!run;

/** Start (or pick up after a reload) the tips of a brand-new player. */
export function startTips(env){
  E=env;watch();
  const at=TIPS.findIndex(t=>t.id===get());
  run={i:Math.max(0,at),shown:0,acted:false};set(TIPS[run.i].id);
  clearInterval(timer);timer=setInterval(tick,400);tick();
}

/** One-time wiring: a command answered after a tap on the work screen = the player did a step. */
function watch(){
  if(seen)return;seen=true;
  let clicked=false;
  document.addEventListener('click',e=>{
    const el=e.target.closest?.('[data-action],[data-command]');
    clicked=!!(el&&$('#sheet[open]')?.contains(el)&&E?.ui?.view==='job'&&!['close','jobTab','chat'].includes(el.dataset.action));
  },true);
  E?.api?.addEventListener('state',e=>{if(run&&clicked&&e.detail?.result){run.acted=true;clicked=false;}});
  const again=()=>{if(bubbleUp())placeBubble();};
  addEventListener('resize',again);addEventListener('layoutchange',again);addEventListener('scroll',again,true);
}

/* ------------------------------------------------------------------ hints */
/* Help at the moment of need: the first time a new player meets one of the questions players really ask
 * (feedback), one small bubble on the right control. Each shows once (settings.notesSeen, like the
 * announcements), "×" puts it away. Saves named with the onboarding only (v4/onboard.js markedNew), after
 * the first 3 customers, never while a tip is up. */
const HINTS=[
  // On the journey home a floating bubble covered the character card: this one is a line under the heading (inline),
  // and stays while the page is open (taking it away would move the workplaces under the player's finger).
  {id:'h-job',emoji:'🔁',text:'Đổi nghề: khép ca ở nơi đang làm, rồi chọn nơi khác ở đây.',ttl:Infinity,cls:'inline',
    when:()=>view()==='home'&&!!S()?.journey?.intro&&Object.values(S()?.careers||{}).some(c=>c?.started),
    find:()=>first('#sheet[open] .jr-places .jr-sec-head'),
    done:()=>view()!=='home'},
  {id:'h-money',emoji:'👛',text:'Tiền của bạn: bấm 🏪 Quỹ hoặc 👛 Ví để xem hết.',ttl:8000,
    when:()=>calmStage()&&(room()?.metrics?.served|0)>0,
    find:()=>first('#topbar .hud-fund')||first('#topbar .hud-wallet'),
    done:()=>view()==='money'},
  {id:'h-clock',emoji:'🕗',text:'Giờ trong game ở đây. Tới giờ đóng cửa thì khép ca.',ttl:8000,
    when:()=>!!room()?.open&&['soon60','soon30','closing'].includes(room()?.day_clock?.level),
    find:()=>first('#sheet[open] .dc-chip')||first('#sheet[open] [data-testid="clock"]')||first('#sheet[open] .mt-hud .mt-chip')||(calmStage()&&(first('#topbar .dc-chip')||first('#topbar .hud-day')))},
  {id:'h-door',emoji:'🚪',text:'Xong việc? Bấm đây (hoặc đi ra cửa) để khép ca.',ttl:9000,
    when:()=>calmStage()&&!!room()?.open,
    find:()=>first('#taskHUD .calm-end[data-action="end"]')||first('#taskHUD .icon-btn[data-action="end"]'),
    done:()=>view()==='summary'},
];
/* First use of the town's player services, for every save (they came after most players' first days): the first
 * time one of these sheets is open, one short bubble on the control to start with, like the hints above. Once each
 * (store.js markFeature: one packed "fh-" id in notesSeen), never over the tips, the tour or a running coach. The
 * 🧭 coach itself is per workplace (a shift to open and close): these sheets are not workplaces. */
const SVC='dialog.svc-sheet:not(.ws-sheet)[open]',FAM='dialog.mr-sheet[open]',PHOTO='dialog.pt-sheet[open]',WED='dialog.ws-sheet[open]',FAIR='dialog.tf-sheet[open]';
const FEATS=[
  {id:'svc',emoji:'🛎️',dlg:SVC,text:'Chạm một người để xem giá rồi đặt. Xu được giữ tới khi bạn xác nhận.',
    find:()=>first(`${SVC} .svc-list .svc-card`)},
  {id:'svc-mine',emoji:'🧰',dlg:SVC,text:'Bật công tắc để người khác đặt dịch vụ của bạn.',
    find:()=>first(`${SVC} .svc-switch`)},
  {id:'birth',emoji:'👶',dlg:FAM,text:'Chọn Sinh con hay Nhận nuôi, đặt tên bé, rồi gửi lời mời.',
    find:()=>first(`${FAM} #mr-family-children .mr-seg`)},
  {id:'birth-room',emoji:'🏡',dlg:FAM,text:'Đặt tên, giá phòng sinh rồi lưu: các cặp sẽ đặt phòng của bạn.',
    find:()=>first(`${FAM} #mr-family-room h3`)},
  {id:'photo',emoji:'📸',dlg:PHOTO,text:'Chọn gói, phông, giá rồi bấm Đặt chụp. Xu giữ tới khi có ảnh.',
    find:()=>first(`${PHOTO} .pt-pkgs`)},
  {id:'studio',emoji:'📷',dlg:PHOTO,text:'Khách đặt hiện ở đây: Nhận đơn rồi bấm Chụp.',
    find:()=>first(`${PHOTO} .pt-order .btn.primary`)},
  {id:'wed',emoji:'💒',dlg:WED,text:'Mỗi dịch vụ: chọn một người làm, chọn yêu cầu rồi đặt.',
    find:()=>first(`${WED} .ws-providers .svc-card`)},
  {id:'wed-work',emoji:'🧰',dlg:WED,text:'Bật dịch vụ cưới để cô dâu chú rể tìm thấy bạn.',
    find:()=>first(`${WED} .ws-switch`)},
  {id:'fair',emoji:'🎪',dlg:FAIR,text:'Đặt ở một gian để được giá hội chợ. Xem diễn để lấy tem.',
    find:()=>first(`${FAIR} .tf-grid > *`)},
  {id:'booth',emoji:'🧑‍🔧',dlg:FAIR,text:'Chọn nghề, mức giảm, rồi bấm Dựng gian.',
    find:()=>first(`${FAIR} .tf-setup .tf-careers`)},
];
// It goes at the player's first tap (it may sit over other controls of the sheet), when the sheet closes, or after 9 s.
for(const f of FEATS){f.ttl=9000;f.feat=true;f.done=()=>!document.querySelector(f.dlg)||H.tap>H.since;}
let H=null;
export function hintsBoot(env,{markedNew,quiet,notesSeen,markSeen}){
  if(H)return;E=E||env;watch();
  H={now:null,since:0,tap:0};
  document.addEventListener('pointerdown',()=>{if(H.now)H.tap=performance.now();},true);
  const tick=()=>{
    const s=env.api.state;if(!s)return;
    const fresh=markedNew(s);
    if(run){if(H.now)H.now=null;return;}                  // the tips go first
    if(H.now){
      const h=HINTS.find(x=>x.id===H.now)||FEATS.find(x=>x.id===H.now);
      // These sheets redraw themselves: the bubble follows the control drawn again in its place.
      if(h.feat&&bubble?.dataset.tip===h.id&&!bubble._el?.isConnected){const el=h.find();if(el)bubble._el=el;}
      // An inline line the page dropped while redrawing itself goes back under its heading.
      if(h.cls==='inline'&&bubble?.dataset.tip===h.id&&!bubble.isConnected&&!h.done?.()){const el=bubble._el?.isConnected?bubble._el:h.find();if(el){el.after(bubble);bubble._el=el;}}
      const gone=!bubbleUp()||bubble.dataset.tip!==h.id;
      if(gone||h.done?.()||performance.now()-H.since>h.ttl){if(!gone)hideBubble();H.now=null;return;}
      const top=topDialog(),el=bubble._el;
      if(h.cls==='inline')return;   // it scrolls with the page: hiding it off screen would only move the page
      if(!vis(el)||top&&!top.contains(el))bubble.hidden=true;else placeBubble();
      return;
    }
    if(document.getElementById('tutLayer')?.isConnected)return;
    // The coach's chip (or a coach run waiting out of sight under these sheets) does not hold the services' hints back.
    const coachUp=coachOn(),coachShown=!!document.querySelector('#coachLayer:not([hidden])');
    if(fresh&&!quiet(s)&&!coachUp){
      const seen=notesSeen(env.api);
      for(const h of HINTS){
        if(seen.has(h.id)||!h.when())continue;
        const el=h.find(),top=topDialog();if(!el||top&&!top.contains(el))continue;
        showBubble({id:h.id,emoji:h.emoji,text:h.text,el,cls:`hint ${h.cls||''}`.trim()});
        H.now=h.id;H.since=performance.now();markSeen(env,h.id);   // shown = seen: it never comes back
        return;
      }
    }
    if(coachShown)return;
    const done=featuresSeen(env.api);
    for(const h of FEATS){
      if(done.has(h.id))continue;
      const el=h.find(),top=topDialog();if(!el||top&&!top.contains(el))continue;
      showBubble({id:h.id,emoji:h.emoji,text:tr(h.text),el,cls:'hint'});
      H.now=h.id;H.since=performance.now();markFeature(env,h.id);
      return;
    }
  };
  setInterval(tick,600);
}
