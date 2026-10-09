/** Hành trình: one person, one small neighbourhood. The journey home (character,
 * chapter, workplaces), its sheets (titles, wallet, profile), the first-run
 * intro and the story scenes. Markup only: every rule lives in
 * game/journey.py. Buttons use data-action="jr…" (journeyAction) or the app's
 * `choose`/`close`; forms use data-jr-form (journeySubmit). */
import {icon,escapeHTML as esc} from '../icons.js';
import {marketTag} from '../market-ui.js';
import {olderRows,olderButton} from '../archive.js';
import {accountChip} from './account.js';
import {storiesBoot,storiesCard,storiesAction,maybeStory} from './stories.js';
import {investView,investEntry,investAction,investBoot} from './invest.js';
import {boardEntry} from './board.js';
import {abandonTrust} from './abandon.js';
import {certsView,certsEntry,certBadges,certTitles,certAction,certPlaceLine,certBadge} from './certificates.js';
import {lifeView,lifeEntry,lifeCard,lifeAction,lifeBoot} from './life.js';
import {householdView,householdAction,householdSubmit} from './household.js';
import {outingsView,outingsAction} from './outings.js';
import {courierView,courierAction} from './courier.js';
import {portrait,lookOf} from './look.js';
import {lazy,skeleton} from '../lazy.js';
import {FIRST_JOB,quiet,firstDay} from './onboard.js';
import {highlight} from './guide.js';
import {acctPlace,acctTag,acctTags} from './acct-jobs.js';   // 💼 kế toán: exam first, ×3/×5 (game/accounting_jobs.py)
import {fundMoveHTML} from './wealth.js';   // 💼 Rút / góp vốn with a typed amount (F#259)
// The town map's compact goal card on the clean layout (docs/UI_KIT.md, wave 5): ui-kit.js clean(), guarded for tests.
const clean=()=>typeof document!=='undefined'&&!!document.documentElement?.hasAttribute?.('data-clean');
// 👗 Tủ đồ (v4/wardrobe.js): the sheet loads the first time it opens.
const WD=lazy(()=>import('./wardrobe.js'),{css:['/css/wardrobe.css']});
// 🙂 Ảnh đại diện khi chat (v4/avatar.js): likewise.
const AV=lazy(()=>import('./avatar.js'),{css:['/css/avatar.css']});
// 🗺️ Bản đồ phố (v4/town-walk.js): the home as a town to walk, loaded the first time it shows.
const TW=lazy(()=>import('./town-walk.js'),{css:['/css/town.css']});

/* 🗺️ Màn hình chính: "Bản đồ phố" (the default) or "Danh sách" (this list), a per-device choice in Cài đặt, kept like
 * the layout choice (localStorage). ui.homeMode: the other one opened for now ("📋 Danh sách" on the town, "🗺️ Bản đồ
 * phố" on the list or the menu); the "Hành trình" entry clears it. A browser without canvas keeps the list. */
const HOME_KEY='mnl.home';
export const homePref=()=>{try{return localStorage.getItem(HOME_KEY)==='list'?'list':'town';}catch{return 'town';}};
export function setHomePref(v){try{localStorage.setItem(HOME_KEY,v==='list'?'list':'town');}catch{/* storage blocked */}}
let canvasOK=null;
export function townOK(){
  if(canvasOK===null){try{canvasOK=!!document.createElement('canvas').getContext('2d')&&typeof ResizeObserver==='function';}catch{canvasOK=false;}}
  return canvasOK;
}
const townWanted=ui=>townOK()&&(ui.homeMode||homePref())==='town';
/** Does the home sheet show the town now? (app.js gives the sheet its fixed height then) */
export function townOn(env){
  const {api,ui}=env,J=api.state?.journey;
  if(!J||!api.content?.journey||!townWanted(ui)||(ui.jrView&&ui.jrView!=='home'))return false;
  return !(J.story&&!J.intro&&!J.gender);   // a brand-new player picks a look and a name first
}
/** What the town needs from here (the list's own helpers, so both say the same). */
const TOWN_HELP={emojiOf:m=>emojiOf(m),catOf:m=>catOf(m),get CATS(){return CATS;},FIRST_JOB,acctPlace:(api,cid)=>acctPlace(api,cid),chapterCard,certBadge:api=>certBadge(api)};
function townPage(env){
  const m=TW.use();
  return m?m.townHTML(env,TOWN_HELP):`<div class="tw-home"><header class="tw-top home-top"><div class="tw-title"><h2>Khu phố</h2></div><button type="button" class="tw-chip tw-list" data-action="jrList">📋 Danh sách</button></header>${skeleton()}</div>`;
}

export const EMOJI={restaurant:'🍜',cafe_bakery:'🥐',grocery:'🛒',repair:'🔧',homestay:'🏡',corp_accounting:'🧮',tax_payroll:'🧾',group_accounting:'🏢',hr_admin:'🗂️',secretary:'📅',it_helpdesk:'🖥️',
  mother_baby:'🎁',pharmacy:'💊',accounting:'📒',customer_care:'🎧',teacher:'🍎',tour_guide:'🧭',milk_tea:'🧋',florist:'💐',salon:'💇',
  pet_care:'🐾',farm:'🌾',delivery:'🛵',clothing:'👕',pet_shop:'🐠',tra_da:'🧊',ice_cream:'🍨',com:'🍚',nail:'💅',pagoda:'🛕',pho:'🍜',photobooth:'📸',giupviec:'🧹',naucom:'🍲',babysitter:'👶',library:'📚',oil:'🛢️',railway:'🚦',nurse:'🏥',lighthouse:'🗼',rescue:'📞',lifeguard:'🛟',police:'👮',zpop:'💿'};
const CATS={food:'Ăn uống',shop:'Buôn bán',service:'Dịch vụ',office:'Văn phòng',outdoor:'Ngoài trời'};
const LEGACY_CAT={mother_baby:'shop',pharmacy:'shop',accounting:'office',customer_care:'office',teacher:'service',tour_guide:'outdoor',milk_tea:'food'};
// The workplaces counted by game/journey.py OFFICE, rather than every office-category career.
const CHAPTER_OFFICE=['corp_accounting','tax_payroll','group_accounting','hr_admin','secretary','it_helpdesk'];
const SKILL_SHORT={careful:'Cẩn thận',communication:'Giao tiếp',patience:'Kiên nhẫn',numbers:'Con số',teamwork:'Làm nhóm',creative:'Sáng tạo',tech:'Máy tính',calm:'Bình tĩnh',learning:'Ham học'};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const colour=v=>/^#[0-9a-f]{3,8}$/i.test(v||'')?v:'#c44b30';
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,action,data={},style='',extra='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}${extra}>${label}</button>`;
const tag=(label,kind='')=>`<span class="tag ${kind}">${label}</span>`;
export const catOf=m=>m.category||LEGACY_CAT[m.id]||'service';
export const emojiOf=m=>EMOJI[m.id]||m.emoji||'✨';

let E=null;           // the app env captured at boot (api, ui, cmd, openSheet…)
let sceneQueue=null;  // news ids shown in the open scene

const meta=(api,cid)=>api.content.catalogue.find(m=>m.id===cid)||{id:cid,short:cid,place:cid};
const placeOf=(api,cid)=>{const m=meta(api,cid);return m.place||m.short||cid;};
const lineText=(l,gender)=>typeof l.text==='string'?l.text:(l.text[gender]||l.text.none);

/** Warm little portrait of the player, drawn inline (no external art). `look`: the outfit from the
 * wardrobe (v4/look.js lookOf); left out, the gender's everyday look. */
export function avatar(gender,size=56,look=null){return portrait(look,gender,size);}

function say(l,gender,cls=''){
  return `<div class="jr-line ${cls}"><span class="jr-face" aria-hidden="true">${l.emoji}</span><div class="jr-bubble"><b>${esc(l.name)}</b><p>${esc(lineText(l,gender))}</p></div></div>`;
}
function head(title,sub,{back=false,close=false,eyebrow='HÀNH TRÌNH'}={}){
  return `<header class="sheet-head jr-head">${back?`<button type="button" class="btn ghost small jr-back" data-action="jrView" data-view="home" aria-label="Quay lại hành trình">${icon('back',18)}</button>`:''}<div class="grow"><span class="eyebrow">${eyebrow}</span><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div>${close?btn(icon('x',20),'close',{},'ghost small','aria-label="Đóng"'):''}</header>`;
}

/* ------------------------------------------------------------------ home */
export function journeyHome(env){
  const {api,ui}=env,J=api.state.journey;
  if(!J||!api.content.journey)return `<div class="jr-home"><p class="muted">Khu phố đang thức dậy…</p></div>`;
  if(townOn(env))return townPage(env);
  if(J.story&&!J.intro)return introView(env);
  if(ui.jrView==='titles')return titlesView(env);
  if(ui.jrView==='wallet')return walletView(env);
  if(ui.jrView==='invest')return investView(env);
  if(ui.jrView==='life')return lifeView(env);
  if(ui.jrView==='household')return householdView(env);
  if(ui.jrView==='outings')return outingsView(env);
  if(ui.jrView==='courier')return courierView(env);
  if(ui.jrView==='profile')return profileView(env);
  if(ui.jrView==='certs')return certsView(env);
  if(ui.jrView==='wardrobe'){const m=WD.use();return m?m.wardrobeView(env):head('Tủ đồ','',{back:true})+skeleton();}
  if(ui.jrView==='avatar'){const m=AV.use();return m?m.avatarView(env):head('Ảnh đại diện','',{back:true})+skeleton();}
  return homeMain(env);
}

// Hôn nhân (v4/marriage.js): the spouse and the relationship status under the name.
/* 🏷️ Đang đeo (game/journey.py WEAR_MAX): game titles and certificates worn at once; a save from an older server
 * only has `equipped_title`. 🏅 The weekly leaderboard title held now (api.lbTitles, game/lb_titles.py) shows first. */
export const wornOf=J=>Array.isArray(J?.worn)?J.worn:J?.equipped_title?[{...J.equipped_title,kind:'title'}]:[];
const wearMax=J=>J?.wear_max||3;
function wornChips(api,J){
  const worn=wornOf(J),rank=(api.lbTitles||[])[0];
  const chip=(w,cls='')=>`<button type="button" class="jr-title-chip ${cls}" data-action="jrView" data-view="titles"><span aria-hidden="true">${esc(w.emoji)}</span> ${esc(w.name)}</button>`;
  const top=rank?`<button type="button" class="jr-title-chip rank" data-action="rank" data-board="${esc(rank.board)}" title="${esc(rank.label)} tuần này"><span aria-hidden="true">${esc(rank.emoji)}</span> ${esc(rank.name)}</button>`:'';
  return `<div class="jr-worn">${top}${worn.map(w=>chip(w)).join('')||`<button type="button" class="jr-title-chip empty" data-action="jrView" data-view="titles">Chọn danh hiệu để đeo</button>`}</div>`;
}
const spouseChip=api=>{const sp=api.state.marriage?.spouse;return sp?`<button type="button" class="jr-title-chip" data-action="marriage" data-tab="family"><span aria-hidden="true">${sp.status==='married'?'💍':'💞'}</span> ${sp.status==='married'?'Đã kết hôn':'Đã đính hôn'} · ${esc(sp.name)}</button>`:'';};
/* 🚗 The vehicle the player rides (game/garage.py), next to Thay đồ; it opens the garage (v4/garage.js). */
/* 📱 The phone in use (game/gadgets.py), next to the vehicle; it opens the phone shop (v4/gadgets.js). */
const phoneChip=api=>{const g=api.state.journey.gadgets,h=g?.hand,p=g?.perks||[],rim=p.includes('skin')&&/^#[0-9a-f]{6}$/i.test(h?.color||'')?(p.includes('gold')?'#d4af37':h.color):'';return h?.name?`<button type="button" class="jr-title-chip" data-action="gadgets"${rim?` style="box-shadow:inset 0 0 0 2px ${rim}"`:''}><span aria-hidden="true">${esc(h.emoji||'📱')}</span> ${esc(h.name)}</button>`:'';};
const rideChip=api=>{const g=api.state.journey.garage,c=g?.ride&&g.cars?.find(x=>x.id===g.ride),it=c&&(api.content.journey?.garage?.vehicles||[]).find(v=>v.id===c.id);
  return it?`<button type="button" class="jr-title-chip" data-action="garage"><span aria-hidden="true">${it.emoji}</span> ${esc(it.name)}</button>`:'';};
function meCard(env){
  const {api}=env,J=api.state.journey,C=api.content.journey,mat=J.maturity;
  const span=mat.next?Math.max(1,mat.next-mat.floor):1,pct=mat.next?Math.min(100,Math.round((mat.xp-mat.floor)*100/span)):100;
  const skills=(C.skills||[]).map(sk=>{const v=J.skills.find(x=>x.id===sk.id)||{level:0};return `<li class="jr-skill ${v.level?'':'zero'}" title="${esc(sk.name)}"><span aria-hidden="true">${sk.emoji}</span><b>${esc(SKILL_SHORT[sk.id]||sk.name)}</b><i class="jr-pips" aria-label="Mức ${v.level}">${'●'.repeat(v.level)}${'○'.repeat(Math.max(0,6-v.level))}</i></li>`;}).join('');
  // 💰 The wallet stat opens "Tiền của bạn" (v4/wealth.js): every pocket in one place, Sổ ví one tap further.
  const wallet=J.story?`<button type="button" class="jr-stat ${J.debt?'bad':''}" data-action="money"><small>Ví của bạn</small><b>${J.debt?`Nợ ${fmt(J.debt)} xu`:`${fmt(J.wallet)} xu`}</b></button>`:'';
  return `<section class="jr-card jr-me" aria-label="Nhân vật của bạn">
    <div class="jr-me-top"><button type="button" class="jr-avatar" data-action="jrView" data-view="profile" aria-label="Sửa tên và nhân vật">${avatar(J.gender,68,lookOf(api.state))}</button>
      <div class="jr-me-text"><h2>${esc(api.state.name)}</h2>${spouseChip(api)}
        ${J.story?wornChips(api,J)+'<p class="muted small jr-chat-hint">💬 Danh hiệu tự hiện cạnh tên trong chat. Chạm để đổi cái đang đeo.</p>':''}
        <button type="button" class="jr-title-chip jr-wd-chip" data-action="jrWardrobe"><span aria-hidden="true">👗</span> Thay đồ</button>${rideChip(api)}${phoneChip(api)}
        <div class="jr-level"><div class="jr-level-row"><b>Trưởng thành cấp ${mat.level}</b><small>${esc(mat.name)}</small></div><div class="jr-bar" role="progressbar" aria-label="Kinh nghiệm trưởng thành" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><i style="width:${pct}%"></i></div></div></div></div>
    ${J.story?`<div class="jr-stats">${wallet}<div class="jr-stat"><small>Ngày sống</small><b>${fmt(J.life_day)}</b></div><button type="button" class="jr-stat" data-action="jrView" data-view="titles"><small>Danh hiệu</small><b>${J.titles.length}</b></button></div>`:''}
    ${certBadges(env)}
    <details class="jr-skills-box"><summary>Kỹ năng</summary><ul class="jr-skills">${skills}</ul></details>
  </section>`;
}

/** Only offer direct entry to an unlocked, open place whose certificate requirements are met. */
function availablePlaces(api){
  const J=api.state.journey;
  return (J.story?J.unlocked:Object.keys(api.state.careers)).filter(id=>api.state.careers[id]&&!J.places[id]?.paused&&acctPlace(api,id)?.ok!==false);
}
function goalLink(env,goal,{primary=false}={}){
  const {api}=env,J=api.state.journey,open=availablePlaces(api);
  const work=open.includes(api.state.current)?api.state.current:open.includes(J.suggested)?J.suggested:open[0];
  const go=(id,label)=>id?btn(label,'choose',{career:id},`${primary?'primary':'cream'} small jr-goal-cta`):btn('Xem nơi làm việc','jrPlaces',{},'cream small jr-goal-cta');
  switch(goal.id){
    case'places':return btn('Chọn một nơi khác','jrPlaces',{},'cream small jr-goal-cta');
    case'draw':return btn('Xem quỹ để rút lời','jrView',{view:'wallet'},'cream small jr-goal-cta');
    case'clean':return `<small class="jr-goal-hint">Giữ ví không nợ qua các ngày sống liên tiếp.</small>${btn('Kiểm tra ví','jrView',{view:'wallet'},'cream small jr-goal-cta')}`;
    case'titles':return btn('Xem cách nhận danh hiệu','jrView',{view:'titles'},'cream small jr-goal-cta');
    case'office_hired':case'office_days':{
      const office=open.filter(id=>CHAPTER_OFFICE.includes(id)&&api.state.careers[id].job?.required);
      const hired=office.find(id=>api.state.careers[id].job.status==='hired');
      return go(hired||office[0],hired?'Tới văn phòng làm việc':'Xem việc văn phòng');
    }
    case'level':return go(open.filter(id=>api.state.careers[id].started).sort((a,b)=>(api.state.careers[b].level||1)-(api.state.careers[a].level||1))[0]||work,'Tiếp tục lên cấp nghề');
    case'days':return go(work,'Tới nơi làm để khép ngày');
    case'tasks':return go(work,'Tới nơi làm nhận việc');
    case'mature':return go(work,'Làm việc để trưởng thành');
    default:return '';
  }
}

/** The recommendation stays beside its reason and uses the existing workplace entry flow. */
function resumeCard(env,{reasonOnly=false,slim=false}={}){
  const {api}=env,J=api.state.journey,sid=J.suggested,room=sid?api.state.careers[sid]:null;if(!room||!availablePlaces(api).includes(sid))return '';
  const sm=meta(api,sid),place=sm.place||sm.short,job=room.job||{};
  const label=job.required&&job.status!=='hired'?(job.status==='offer'?`Xem thư mời ở ${place}`:`Xin việc ở ${place}`):room.started?`Tiếp tục ở ${place}`:`Thử làm ở ${place}`;
  const pending=(J.goals||[]).filter(x=>!x.done);
  const reason=pending.some(x=>x.id==='places')&&!room.metrics?.served?'Thử một nơi mới để tiến tới mục tiêu làm ở nhiều nơi.'
    :pending.some(x=>x.id.startsWith('office_'))&&CHAPTER_OFFICE.includes(sid)?'Mục tiêu chương này cần kinh nghiệm làm việc văn phòng.'
    :room.started?'Tiếp tục công việc ở nơi bạn đã bắt đầu.':'Một nơi đã mở để bạn bắt đầu làm việc.';
  return `<div class="jr-recommend">${slim?'':`<p class="jr-recommend-reason">${esc(reason)}</p>`}${reasonOnly?'':`<button type="button" class="btn primary big full jr-cta jr-resume" data-action="choose" data-career="${esc(sid)}"><span aria-hidden="true">${emojiOf(sm)}</span> ${esc(label)} ${icon('arrow',16)}</button>`}</div>`;
}

export function chapterCard(env,{compact=false}={}){
  const {api}=env,J=api.state.journey,C=api.content.journey,g=J.gender;
  if(J.finale){
    const last=C.chapters[C.chapters.length-1];
    return `<section class="jr-card jr-chapter finale"><div class="jr-ch-art" aria-hidden="true">🏮</div><span class="eyebrow">HÀNH TRÌNH TIẾP DIỄN</span><h2>Người của khu phố</h2><p class="muted">Khu phố đã là nhà. Mỗi ngày vẫn còn những việc nhỏ đáng làm.</p>${say(last.outro[0],g)}</section>`;
  }
  const ch=C.chapters.find(x=>x.n===J.chapter);if(!ch)return '';
  const pending=J.goals.filter(x=>!x.done),first=pending[0];
  // Receiving work comes before closing the first day; retain the full chapter's authored order in the list.
  const next=first?.id==='days'?pending.find(x=>x.id==='tasks')||first:first;
  const expanded=compact&&env.ui.jrGoalsExpanded;
  const shown=compact&&!expanded?(next?[next]:[]):J.goals;
  const goals=shown.map(x=>`<li class="${x.done?'done':''}" data-goal="${esc(x.id)}"><span class="jr-check" aria-hidden="true">${x.done?icon('check',14):''}</span><div class="grow"><span>${esc(x.text)}</span>${x.done?'':goalLink(env,x,{primary:compact&&!expanded})}</div><b>${fmt(Math.min(x.cur,x.goal))}/${fmt(x.goal)}</b></li>`).join('');
  const directWork=compact&&goals.includes('data-action="choose"');
  const done=J.goals.filter(x=>x.done).length;
  // Clean layout, town map (compact): the goal and its button only; the reason line (why this place) is left out and the
  // "Việc cần làm" heading becomes the count beside the chapter. The full card on the journey page is unchanged.
  const slim=compact&&clean();
  const recommendation=slim&&directWork?'':directWork?(goals.includes(`data-career="${esc(J.suggested)}"`)?resumeCard(env,{reasonOnly:true}):''):resumeCard(env,{slim});
  const paused=J.progress_paused?`<div class="notice jr-debt">${icon('coin',17)}<div>Ví đang nợ ${fmt(J.debt)} xu nên câu chuyện tạm dừng. Rút tiền lời từ một nơi làm việc để trả là đi tiếp được.</div></div>${btn('Mở ví của bạn','jrView',{view:'wallet'},'ghost small')}`:'';
  return `<section class="jr-card jr-chapter"><div class="jr-ch-top"><div class="jr-ch-art" aria-hidden="true">${ch.art}</div><div class="grow"><span class="eyebrow">Chương ${ch.n}/${C.chapters.length}${slim?` · <span aria-label="${esc(`Việc cần làm ${done}/${J.goals.length}`)}">📋 ${done}/${J.goals.length}</span>`:''}</span><h2>${esc(ch.title)}</h2>${compact?'':`<p class="muted">${esc(ch.tagline)}</p>`}</div></div>
    ${slim?'':`<h3 class="jr-goals-title">Việc cần làm <small>${done}/${J.goals.length}</small></h3>`}<ul class="jr-goals">${goals}</ul>${paused}${recommendation}
    ${compact?btn(slim?(expanded?'▴':'▾'):expanded?'Thu gọn mục tiêu':'Xem tất cả mục tiêu','jrGoals',{},'ghost small',` aria-expanded="${!!expanded}"${slim?` aria-label="${expanded?'Thu gọn mục tiêu':'Xem tất cả mục tiêu'}"`:''}`):`${say(ch.intro[ch.intro.length-1],g,'compact')}<button type="button" class="jr-link" data-action="jrStory" data-n="${ch.n}">${icon('book',14)} Nghe lại câu chuyện</button>`}</section>`;
}

function placeCard(env,cid){
  const {api}=env,J=api.state.journey,m=meta(api,cid),c=api.state.careers[cid],p=J.places[cid];
  const job=c.job||{},tags=[],aj=acctPlace(api,cid);
  if(cid===api.state.current&&c.started)tags.push(tag('Đang làm','blue'));
  if(c.started)tags.push(tag(`Ngày ${c.day} · Cấp ${c.level||1}`,'green'));
  if(p?.paused)tags.push(tag('Tạm đóng','amber'));
  if(job.status==='offer')tags.push(tag('💌 Có thư mời','blue'));
  else if(job.required&&job.status!=='hired')tags.push(tag(icon('briefcase',12)+' Cần xin việc','amber'));
  if(!c.started&&J.story&&(api.content.journey.unlock_chapter||{})[cid]===J.chapter)tags.push(tag('Mới mở','green'));
  if(api.state.x3?.today?.includes(cid))tags.push(tag(`🔥 Lời x${api.state.x3.x} hôm nay`,'amber'));   // game/x3_week.py
  {const mk=marketTag(api.state,cid);if(mk)tags.push(tag(esc(mk[0]),mk[1]));}   // 📈 staff profit ×market, 🔥 nghề hot hôm nay (game/staff_market.py)
  if(acctTag(aj))tags.push(tag(acctTag(aj),'amber'));
  let money='';
  if(p&&J.story)money=p.employed?`<p class="jr-fund">Làm thuê · lương về ví${abandonTrust(api,cid)}</p>${btn('💵 Xem lương trong Sổ ví','jrView',{view:'wallet'},'ghost small')}`:`<p class="jr-fund">Quỹ ${fmt(p.fund)} xu · ${p.paused?'tạm đóng, mở lại miễn phí':'vắng chủ không tốn phí'}</p>`;
  if(aj&&!aj.ok)money=`<p class="jr-fund">🔒 ${esc(aj.why)}</p>`;
  const action=aj&&!aj.ok?btn(`Đi học ${icon('arrow',13)}`,'accountingSchool',{},'cream small'):p?.paused?btn('Mở lại','jrReopen',{career:cid},'cream small'):
    btn(`${c.started?'Tiếp tục':job.required&&job.status!=='hired'?'Xin việc':'Bắt đầu'} ${icon('arrow',13)}`,'choose',{career:cid},c.started?'primary small':'cream small');
  return `<article class="jr-place ${p?.paused?'paused':''} ${cid===api.state.current?'current':''}" style="--career:${colour(m.color)}"><span class="jr-place-emoji" aria-hidden="true">${emojiOf(m)}</span>
    <div class="jr-place-text"><span class="eyebrow">${esc(CATS[catOf(m)]||'')}</span><h3>${esc(m.place||m.short)}</h3><small>${esc(m.short||'')}</small><div class="jr-tags">${acctTags(aj,tags,tag).join('')}</div>${money}${J.story?certPlaceLine(env,cid):''}</div>${action}</article>`;
}

function lockedTile(env,cid){
  const {api}=env,J=api.state.journey,m=meta(api,cid),n=(api.content.journey.unlock_chapter||{})[cid];
  // One word per tile: the section is already "Còn ở phía trước"; the next chapter's places say "Sắp mở".
  return `<article class="jr-locked" aria-label="Nơi làm việc chưa mở"><span class="jr-place-emoji silhouette" aria-hidden="true">${emojiOf(m)}</span><b>🔒${n===J.chapter+1?' Sắp mở':''}</b><small><span class="jr-locked-cat">${esc(CATS[catOf(m)]||'')}</span></small></article>`;
}

/** 🔥 Today's x3 careers (game/x3_week.py); the week's list opens from here (v4/x3week.js). */
function x3Banner(env){
  const x=env.api.state.x3;if(!x?.today?.length)return '';
  // The places the player has, by name; the others as a count (owner 03/10: "chữ ít thôi"). The card opens the week.
  const open=new Set(env.api.state.journey?.unlocked||[]),mine=x.today.filter(id=>open.has(id)),rest=x.today.length-mine.length;
  const names=mine.map(id=>{const m=meta(env.api,id);return `${emojiOf(m)} ${m.short||id}`;}).join(' · ')+(rest?`${mine.length?' · ':''}+${rest} nghề khác`:'');
  return `<button type="button" class="jr-x3" data-action="x3Week"><span class="jr-x3-ico" aria-hidden="true">🔥</span><span class="grow"><b>Hôm nay lời x${x.x}</b><small>${esc(names)}</small><em>Cả tuần ›</em></span></button>`;
}

function placesSection(env){
  const {api}=env,J=api.state.journey,all=api.content.catalogue.map(m=>m.id).filter(id=>api.state.careers[id]);
  const order=id=>(api.content.journey.unlock_chapter||{})[id]||9;
  const open=all.filter(id=>J.unlocked.includes(id)).sort((a,b)=>{
    const A=api.state.careers[a],B=api.state.careers[b];
    return (b===api.state.current)-(a===api.state.current)||(B.started-A.started)||order(a)-order(b);
  });
  const locked=all.filter(id=>!J.unlocked.includes(id)).sort((a,b)=>order(a)-order(b));
  // Many open places (sandbox, late chapters): the old category chips come back.
  let shown=open,chips='';
  if(open.length>6){
    const started=open.filter(id=>api.state.careers[id].started),cats=Object.keys(CATS).filter(k=>open.some(id=>catOf(meta(api,id))===k));
    let cat=env.ui.homeCat||'all';
    if(cat==='mine'&&!started.length||cat!=='all'&&cat!=='mine'&&!cats.includes(cat))cat='all';
    shown=cat==='all'?open:cat==='mine'?started:open.filter(id=>catOf(meta(api,id))===cat);
    const chip=(id,text,n)=>`<button type="button" class="chip ${cat===id?'active':''}" data-action="homeCat" data-cat="${id}" aria-pressed="${cat===id}">${text} <em>${n}</em></button>`;
    chips=`<nav class="home-filters jr-filters" aria-label="Nhóm nơi làm việc">${chip('all','Tất cả',open.length)}${started.length?chip('mine','Đã làm',started.length):''}${cats.map(k=>chip(k,CATS[k],open.filter(id=>catOf(meta(api,id))===k).length)).join('')}</nav>`;
  }
  // The next chapter's places show as silhouettes; the rest stay one quiet tile.
  const soon=locked.filter(id=>order(id)===J.chapter+1),later=locked.length-soon.length;
  const rest=later?`<article class="jr-locked more" aria-label="Những nơi còn ở phía trước"><span class="jr-place-emoji silhouette" aria-hidden="true">🏙️</span><b>+${later} nơi nữa</b><small>Còn ở phía trước</small></article>`:'';
  return `<section class="jr-places" tabindex="-1" aria-label="Nơi làm việc"><div class="jr-sec-head"><h2>Nơi làm việc</h2><small>${open.length}/${all.length} nơi đã mở</small></div>${x3Banner(env)}${chips}
    <div class="jr-grid">${shown.map(id=>placeCard(env,id)).join('')}</div>
    ${locked.length?`<h3 class="jr-sub">Còn ở phía trước</h3><div class="jr-locked-grid">${soon.map(id=>lockedTile(env,id)).join('')}${rest}</div>`:''}</section>`;
}

function homeMain(env){
  const {api}=env,J=api.state.journey;
  const town=townOK()?btn('🗺️ Bản đồ phố','jrTown',{},'cream small jr-town'):'';
  const top=`<header class="jr-top"><div class="grow"><span class="eyebrow">${J.story?`Khu phố nhỏ · Ngày sống ${fmt(J.life_day)}`:'Khu phố nhỏ · mọi nơi đều mở'}</span><h1>Hành trình của bạn</h1></div>${town}${accountChip(env)}${api.state.current?btn(icon('x',20),'close',{},'ghost small jr-close','aria-label="Đóng"'):''}</header>`;
  // 🎓 F#267: Thi chứng chỉ sits in the first column, right under the goals (it was last in the third, under the places).
  const more=`${J.story?fairCard(env):''}${lifeCard(env)}${boardEntry(env)}${abroadEntry(env)}${storiesCard(env)}`;
  return `<div class="jr-home">${top}<div class="jr-columns"><div class="jr-col jr-lead">${J.story?chapterCard(env):''}${!J.story||J.finale?resumeCard(env):''}${certsEntry(env)}${meCard(env)}${J.story?houseCard(env):''}</div><div class="jr-col wide">${placesSection(env)}</div><div class="jr-col jr-more">${more}</div></div></div>`;
}

/* ✈️ Du học, 🌏 Làm việc ở nước ngoài (v4/abroad.js, game/abroad.py): one line, under 🎓 Thi chứng chỉ (its styles). */
function abroadEntry(env){
  const {api}=env,J=api.state.journey,A=J?.abroad,K=api.content.journey?.abroad;if(!J?.story||!A||!K)return '';
  const w=A.work,d=w&&K.dests.find(x=>x.id===w.to),st=A.study,sd=st&&K.dests.find(x=>x.id===st.p);
  const line=d?`${d.flag} Đang làm ở ${d.city} · ngày ${w.n}/${w.need}`:sd?`${sd.flag} Đang học ở ${sd.city} · buổi ${st.n}/${st.of}${st.lesson?' · hôm nay chưa học':''}`
    :A.deg.length?`🎓 ${A.deg.length} bằng du học · lương làm thuê +${A.deg_pct}%`:'Học ở nước ngoài, hay sang chi nhánh làm lương cao';
  return `<button type="button" class="jr-card ct-entry" data-action="abroad" data-tab="${w?'work':'study'}"><span class="ct-entry-icon" aria-hidden="true">✈️</span><span class="grow"><b>Du học & đi làm nước ngoài</b><small>${esc(line)}</small></span>${st?.lesson?'<span class="tag green">Vào học</span>':''}${icon('arrow',16)}</button>`;
}

/* 🏮 Hội chợ dân gian (v4/fair.js, own dialog; game/fair.py): a small banner while the fair is open or about to open. */
function fairCard(env){
  const f=env.api.state.fair;if(!f?.show||f.over)return '';
  const m=Math.max(0,Math.floor(((f.open?f.closes:f.opens)-f.now)/60));   // from the server's clock when the state came
  const span=m>=1440?`${Math.floor(m/1440)} ngày ${Math.floor(m%1440/60)} giờ`:m>=60?`${Math.floor(m/60)} giờ ${m%60} phút`:`${Math.max(1,m)} phút`;
  const when=f.open?(f.forever?'':` · còn ${span}`):` · mở sau ${span}`;   // owner 09/10: no end (forever), no countdown
  return `<section class="jr-card jr-fair" aria-label="Chợ đen"><button type="button" class="jr-fair-row" data-action="fair"><span class="jr-fair-lantern" aria-hidden="true">🕶️</span>
    <span class="grow"><b>${f.open?'Chợ đen đang mở':'Chợ đen sắp mở'}</b><small><span class="jr-fair-games">🪨 Ô ăn quan · 💍 Ném vòng kiếm xu · 🦀 Bầu cua · 🎱 Lô tô</span>${when}</small></span><span class="btn primary small" aria-hidden="true">${f.open?'Vào hội':'Xem'}</span></button></section>`;
}

/* 🏠 Nhà của bạn (v4/house.js, own dialog): where you live, what it costs, the way to your own home. */
function houseCard(env){
  const H=env.api.state.journey.home;if(!H)return '';
  const mine=[H.own,...(Array.isArray(H.props)?H.props:[])].filter(Boolean),late=mine.find(x=>x.loan?.overdue);   // 🏘️ several homes
  const p=H.place||{},c=p.cost||{},L=late?.loan||H.own?.loan;
  const bed=p.kind==='ky_tuc_xa';   // 🛏️ Ký túc xá Hẻm 7 (housing.DORM): a bed in a shared room
  const sub=p.where_id==='estate'?'Dinh thự của bạn':p.where_id==='own'?'Nhà của bạn':p.where_id==='shared'?`Nhà chung với ${esc(p.with||'')}`:bed?'Ở ghép ký túc xá':p.where_id==='rent'?'Phòng thuê':'Thuê theo ngày';
  const cost=['own','shared','estate'].includes(p.where_id)?`Điện nước ${fmt(c.rent)} xu/ngày`:`${bed?'Tiền giường':'Tiền phòng'} ${fmt(c.rent)} xu/ngày`;
  const cat=env.api.content.journey?.homes||{groups:[],homes:[]},live=new Map((H.market||[]).map(r=>[r.id,r]));
  const homes=cat.homes.filter(c=>c.kind==='own'&&live.has(c.id)).map(c=>({...c,...live.get(c.id)})).sort((x,y)=>x.price-y.price),sc=H.offer?.score,can=homes.filter(m=>!(m.missing>0)&&(sc==null||sc>=(m.score||0)||!(m.missing_all>0))).pop(),next=homes.find(m=>m.missing>0);
  const tone=(cat.groups.find(g=>g.id===p.group)||{}).color;
  const hint=L?(L.overdue?`⏰ Trả góp nhà đang chậm ${fmt(L.overdue)} xu`:`Đã trả ${L.paid_rows}/${L.rows.length} kỳ vay mua nhà`)
    :H.own?'Nhà không còn nợ 🔑':mine.length?`🔑 Bạn có ${mine.length} căn nhà`:can?`${can.emoji} Đủ tiền trả trước ${esc(can.name)} rồi đó!`:next?`${next.emoji} ${esc(next.name)}: còn thiếu ${fmt(next.missing)} xu để trả trước`:'';
  return `<section class="jr-card jr-house" aria-label="Nơi bạn ở"><button type="button" class="jr-house-row" data-action="house"><span class="jr-house-emoji" aria-hidden="true"${tone?` style="--hs-tone:${esc(tone)}"`:''}>${p.emoji||'🏚️'}</span>
    <span class="grow"><small>${sub} · ${cost}</small><b>${esc(p.name||'')}</b><em>${hint}</em></span><span class="btn cream small" aria-hidden="true">🏠 Nhà của bạn</span></button><div class="jr-actions">${btn('🚪 Vào nhà','jrEnterHome',{},'primary')}${btn('🏡 Nhà & Gia đình','marriage',{tab:'family'},'cream')}${btn('Mời bạn về nhà','homeGuests',{},'cream')}${btn('👶 Con chung','marriage',{tab:'family',section:'children'},'cream')}${btn('🛵 Sổ shipper','jrView',{view:'courier'},'ghost small')}</div></section>`;
}

/* ------------------------------------------------------------------ intro */
/** A brand-new player's one screen: who you are and where you start, then straight into the first customer
 * (app.js quickOpen). The recommended first workplace is picked already; one tap picks another. */
const jobLabel=m=>{const s=String(m.short||m.place||'').replace(/^(Tiệm|Quán)\s+/,'');return s.charAt(0).toUpperCase()+s.slice(1);};
function introView(env){
  const {api,ui}=env,J=api.state.journey,C=api.content.journey,ch=C.chapters[0];
  const ids=ch.unlocks.filter(id=>api.state.careers[id]);
  const rec=ids.includes(FIRST_JOB)?FIRST_JOB:ids[0],job=ids.includes(ui.jrJob)?ui.jrJob:rec;
  const pick=ui.jrGender||J.gender||'',town=townWanted(ui);   // 🗺️ the town is the way in: no job to pick here
  const card=(g,label)=>`<button type="button" class="jr-gender ${pick===g?'active':''}" data-action="jrGender" data-gender="${g}" aria-pressed="${pick===g}">${avatar(g,64)}<b>${label}</b></button>`;
  const chip=id=>{const m=meta(api,id),on=id===job;
    return `<button type="button" class="onb-job ${on?'active':''} ${id===rec?'rec':''}" data-action="jrJob" data-career="${esc(id)}" aria-pressed="${on}" style="--career:${colour(m.color)}"><span aria-hidden="true">${emojiOf(m)}</span>${esc(jobLabel(m))}${id===rec?'<small>hợp người mới</small>':''}</button>`;};
  return `<div class="jr-intro onb-intro"><div class="jr-street" aria-hidden="true"><span>🏠</span><span>🏪</span><span>🌳</span><span>🧋</span><span>🏮</span><span>🛵</span></div>
    <h1>Chào bạn mới! 👋</h1><p class="jr-lead">Một khu phố nhỏ, nhiều nghề để thử.</p>
    <form class="jr-who" data-jr-form="start"><div class="jr-genders" role="group" aria-label="Giới tính">${card('male','Nam')}${card('female','Nữ')}</div>${pick?'':'<p class="onb-need" id="onb-need">👆 Chọn Nam hoặc Nữ để bắt đầu</p>'}
    <label class="jr-name"><span>Tên của bạn</span><input id="jr-name" name="name" maxlength="24" autocomplete="nickname" required value="${esc(api.state.name)}" aria-describedby="jr-name-hint" data-preserve><small class="jr-name-hint" id="jr-name-hint">${NAME_HINT}</small></label>
    ${town?'':`<fieldset class="onb-jobs"><legend>Làm ở đâu trước?</legend><div class="onb-job-row">${ids.map(chip).join('')}</div></fieldset>`}
    <button type="submit" class="btn primary big full"${pick?'':' aria-describedby="onb-need"'}>${town?'Vào phố thôi':'Vào làm thôi'} ${icon('arrow',16)}</button></form>
    ${!town&&J.gender&&townOK()?`<button type="button" class="jr-link" data-action="jrTown">🗺️ Bản đồ phố</button>`:''}
    ${api.account?'':`<button type="button" class="jr-link acct-intro-link" data-action="v4AccountOpen" data-mode="login">${icon('user',14)} Đã có tài khoản? Đăng nhập</button>`}</div>`;
}

/** The display-name rule (game/social.py name_problem), said before the server has to refuse it. */
const NAME_HINT='Chữ, số, khoảng trắng và tối đa 2 emoji';
function whoForm(env,title,sub,cta){
  const {api,ui}=env,J=api.state.journey,pick=ui.jrGender||J.gender||'';
  const card=(g,label)=>`<button type="button" class="jr-gender ${pick===g?'active':''}" data-action="jrGender" data-gender="${g}" aria-pressed="${pick===g}">${avatar(g,96)}<b>${label}</b></button>`;
  return (title?`<span class="eyebrow">Nhân vật</span><h1>${title}</h1><p class="jr-lead">${sub}</p>`:'')+`
    <form class="jr-who" data-jr-form="profile"><div class="jr-genders" role="group" aria-label="Giới tính">${card('male','Nam')}${card('female','Nữ')}</div>
    <label class="jr-name"><span>Tên của bạn</span><input id="jr-name" name="name" maxlength="24" autocomplete="nickname" required value="${esc(api.state.name)}" aria-describedby="jr-name-hint" data-preserve><small class="jr-name-hint" id="jr-name-hint">${NAME_HINT}</small></label>
    <button type="submit" class="btn primary big full" ${pick?'':'disabled'}>${cta} ${icon('arrow',16)}</button></form>`;
}

function profileView(env){
  const {api}=env,J=api.state.journey;
  const wd=J.gender?`<button type="button" class="jr-card jr-wd-entry" data-action="jrWardrobe">${avatar(J.gender,52,lookOf(api.state))}<span class="grow"><b>Tủ đồ</b><small>Đổi kiểu tóc, áo quần, giày và phụ kiện.</small></span>${icon('arrow',16)}</button>`:'';
  const av=`<button type="button" class="jr-card jr-wd-entry" data-action="jrAvatar"><span class="jr-av-emoji" aria-hidden="true">🙂</span><span class="grow"><b>Ảnh đại diện</b><small>Gương mặt hiện cạnh tin nhắn chat, mặc đồ trong Tủ đồ.</small></span>${icon('arrow',16)}</button>`;
  return head('Nhân vật của bạn','',{back:true})+`<div class="sheet-body jr-body jr-profile">${whoForm(env,'','','Lưu lại')}${wd}${av}</div>`;
}

/* ------------------------------------------------------------------ titles */
function titlesView(env){
  const {api}=env,J=api.state.journey,C=api.content.journey,have=new Map(J.titles);
  const worn=wornOf(J),ids=new Set(worn.map(w=>w.id)),max=wearMax(J),full=worn.length>=max;
  const cats=C.cats.map(cat=>{
    const rows=C.titles.filter(t=>t.cat===cat.id);if(!rows.length)return '';
    const tiles=rows.map(t=>{
      const day=have.get(t.id);
      if(day!==undefined){
        const info=t.secret?J.secret[t.id]:t,on=ids.has(t.id);
        return `<button type="button" class="jr-title earned ${on?'on':''}" data-action="jrWear" data-item="${esc(t.id)}" aria-pressed="${on}"><span class="jr-title-emoji" aria-hidden="true">${info.emoji}</span><b>${esc(info.name)}</b><small>${esc(info.desc)}</small><em>${on?'✓ Đang đeo · chạm để cất':full?`Ngày sống ${fmt(day)} · đã đeo đủ ${max}`:`Ngày sống ${fmt(day)} · Đeo`}</em></button>`;
      }
      if(t.secret)return `<div class="jr-title secret"><span class="jr-title-emoji" aria-hidden="true">❔</span><b>???</b><small>Bí mật. Cứ sống ở phố rồi sẽ biết.</small></div>`;
      return `<div class="jr-title"><span class="jr-title-emoji" aria-hidden="true">${t.emoji}</span><b>${esc(t.name)}</b><small>${esc(t.desc)}</small></div>`;
    }).join('');
    const got=rows.filter(t=>have.has(t.id)).length;
    return `<section class="jr-title-cat"><h3>${esc(cat.name)} <small>${got}/${rows.length}</small></h3><div class="jr-title-grid">${tiles}</div></section>`;
  }).join('');
  // What is worn now, on top: one tap on a chip takes it off. Titles and certificates count together.
  const bar=`<section class="jr-wearing" aria-label="Đang đeo"><h3>Đang đeo <small>${worn.length}/${max}</small></h3><p class="muted small">Chọn tối đa ${max} danh hiệu và chứng chỉ. Cái đầu tiên hiện tên, các cái sau hiện biểu tượng.</p>
    <div class="jr-worn">${worn.map(w=>`<button type="button" class="jr-title-chip on" data-action="jrWear" data-item="${esc(w.id)}" aria-label="Cất ${esc(w.name)}"><span aria-hidden="true">${esc(w.emoji)}</span> ${esc(w.name)} <i aria-hidden="true">✕</i></button>`).join('')||'<span class="muted small">Chưa đeo gì. Chạm một danh hiệu hay chứng chỉ bên dưới để đeo.</span>'}</div></section>`;
  return head('Danh hiệu',`Đã có ${J.titles.length}/${C.titles.length}.`,{back:true})+`<div class="sheet-body jr-body">${bar}${cats}${certTitles(env,ids,full)}</div>`;
}

/* ------------------------------------------------------------------ wallet */
function walletView(env){
  const {api}=env,J=api.state.journey,C=api.content.journey;
  if(!J.story)return head('Ví của bạn','',{back:true})+`<div class="sheet-body jr-body"><p class="muted">Ví và quỹ nơi làm việc có trong hành trình.</p></div>`;
  const places=Object.entries(J.places).map(([cid,p])=>{
    const m=meta(api,cid),c=api.state.careers[cid];
    // 💼 Rút về ví in one tap, Góp vốn beside it with a typed amount (v4/wealth.js, F#259).
    const move=fundMoveHTML(api.state,cid);
    // A place you are away from costs nothing (game/journey.py upkeep()): no "Tạm đóng" to save fees any more; an old pause reopens free.
    const pause=!p.employed&&p.paused?btn('Mở lại','jrReopen',{career:cid},'cream small'):'';
    return `<details class="jr-fundrow ${p.paused?'paused':''}"><summary><span class="jr-place-emoji" aria-hidden="true">${emojiOf(m)}</span><span class="grow"><b>${esc(m.place||m.short)}</b><small>${p.employed?'Làm thuê · lương về ví':p.paused?'Tạm đóng · mở lại miễn phí':'Vắng chủ không tốn phí'}</small></span><b class="jr-amt">${fmt(p.fund)} xu</b></summary>
      <div class="jr-fund-actions">${move}${pause?`<div class="row wrap">${pause}</div>`:''}</div></details>`;
  }).join('')||`<p class="muted">Chưa có nơi làm việc nào. Bắt đầu ở một tiệm trong hẻm nhé.</p>`;
  const kinds={living:'🏠',upkeep:'💡',draw:'👛',invest:'📈',salary:'💵',reopen:'🔑',incident:'⚖️',life:'🌿',study:'📚',backdoor:'🚪',bank:'🏦',home:'🔑',fair:'🏮',karaoke:'🎤'};
  // A label that brings its own emoji ("🎁 Quà từ Phố Có Chuyện") shows it in place of the kind's.
  const lead=h=>/^(\p{Extended_Pictographic}\uFE0F?) /u.exec(h.label||'');
  const row=h=>{const m=lead(h);return `<li><span aria-hidden="true">${m?m[1]:kinds[h.kind]||'•'}</span><span class="grow">${esc(m?h.label.slice(m[0].length):h.label)}<small>Ngày sống ${fmt(h.day)}</small></span><b class="${h.amount<0?'out':'in'}">${h.amount<0?'−':'+'}${fmt(Math.abs(h.amount))} xu</b></li>`;};
  const hist=[...J.history,...olderRows('','wallet')].map(row).join('')||`<li class="muted">Chưa có khoản nào.</li>`;
  const L=J.living;
  return head('Ví của bạn','',{back:true})+`<div class="sheet-body jr-body">
    <section class="jr-card jr-purse ${J.debt?'bad':''}" aria-live="polite"><small>${J.debt?'Đang nợ tiền phòng':'Số dư'}</small><strong>${J.debt?`${fmt(J.debt)} xu`:`${fmt(J.wallet)} xu`}</strong>
      <p>Mỗi ngày sống: ${L.where==='own'||L.where==='shared'?'điện nước nhà':'tiền phòng'} ${fmt(L.rent)} xu và cơm nước ${fmt(L.meals)} xu.</p>
      ${J.home?'<button type="button" class="btn ghost small" data-action="house">🏠 Nhà của bạn</button>':''}
      ${J.debt?`<p class="jr-debt-note">Khi ví còn nợ, câu chuyện tạm dừng. Rút tiền lời về ví để trả nhé.</p>`:''}
      <button type="button" class="btn ghost small" data-action="tutGuide" data-topic="money_withdraw">❔ Rút tiền thế nào?</button></section>
    ${investEntry(env)}${lifeEntry(env)}
    <h3 class="jr-sub">Quỹ các nơi làm việc</h3><div class="jr-funds">${places}</div>
    <h3 class="jr-sub">Sổ ví gần đây</h3><p class="small muted">Lương nhận sau khi kết thúc ngày làm được chuyển về ví và ghi ở dòng 💵 Lương ngày… bên dưới. Bấm Xem cũ hơn để tìm những ngày trước.</p><ul class="jr-history">${hist}</ul>${olderButton('','wallet',J.history.length,J.history.length>=30)}</div>`;
}

/* ------------------------------------------------------------------ future (locked) */
export function journeyFuture(env){
  const {api}=env,J=api.state.journey,ids=api.content.catalogue.map(m=>m.id).filter(id=>api.state.careers[id]&&!J?.unlocked?.includes(id));
  return head('Cả một khu phố phía trước','',{close:true,eyebrow:'KHU PHỐ'})+`<div class="sheet-body jr-body"><div class="jr-locked-grid">${ids.map(id=>lockedTile(env,id)).join('')||'<p class="muted">Mọi nơi trong phố đã mở với bạn.</p>'}</div></div>`;
}

/* ------------------------------------------------------------------ scenes */
function sceneDialog(){
  let d=document.getElementById('jrScene');
  if(!d){d=document.createElement('dialog');d.id='jrScene';d.className='jr-scene';d.setAttribute('aria-labelledby','jrSceneTitle');d.innerHTML='<div class="jr-scene-inner" id="jrSceneBody"></div>';document.body.appendChild(d);
    d.addEventListener('cancel',e=>{e.preventDefault();closeScene();});}
  return d;
}
function confetti(){
  if(document.documentElement.classList.contains('reduce-motion')||E?.api.state?.settings.reduceMotion)return '';
  const bits=['🎉','✨','🌸','🎊','⭐'];
  return `<div class="jr-confetti" aria-hidden="true">${Array.from({length:14},(_,i)=>`<i style="--x:${(i*37)%100}%;--d:${(i%5)*.18}s">${bits[i%bits.length]}</i>`).join('')}</div>`;
}
function openScene(html,ids=[]){
  const d=sceneDialog();sceneQueue=ids;d.querySelector('#jrSceneBody').innerHTML=html;
  if(!d.open)d.showModal();
  d.querySelector('.btn.primary')?.focus();
}
async function closeScene(){
  const d=document.getElementById('jrScene'),ids=sceneQueue||[];sceneQueue=null;
  if(d?.open)d.close();
  if(ids.length&&E)await E.cmd('jr_seen',{ids},{quiet:true});
  setTimeout(maybeScene,120);
}

function chapterScene(n,page=0){
  const {api}=E,J=api.state.journey,C=api.content.journey,ch=C.chapters.find(x=>x.n===n),next=C.chapters.find(x=>x.n===n+1),g=J.gender;
  if(!ch)return '';
  if(page===1&&next){
    return `<div class="jr-scene-card"><div class="jr-ch-art big" aria-hidden="true">${next.art}</div><span class="eyebrow">Chương ${next.n} bắt đầu</span><h2 id="jrSceneTitle">${esc(next.title)}</h2><p class="muted">${esc(next.tagline)}</p>
      <div class="jr-lines">${next.intro.map(l=>say(l,g)).join('')}</div>${btn(`Vào chương ${next.n} ${icon('arrow',15)}`,'jrSceneClose',{},'primary big full')}</div>`;
  }
  const story=C.titles.find(t=>t.id===['st_newcomer','st_familiar','st_skilled','st_trusted','st_office','st_local'][n-1]);
  const opened=(next?.unlocks||[]).filter(id=>api.state.careers[id]);
  const final=!next;
  return `<div class="jr-scene-card celebrate">${confetti()}<div class="jr-ch-art big" aria-hidden="true">${final?'🏮':ch.art}</div><span class="eyebrow">Hoàn thành chương ${ch.n}</span><h2 id="jrSceneTitle">${esc(ch.title)}</h2>
    <div class="jr-lines">${ch.outro.map(l=>say(l,g)).join('')}</div>
    ${story?`<div class="jr-award"><span aria-hidden="true">${story.emoji}</span><div><small>Danh hiệu mới</small><b>${esc(story.name)}</b></div>${btn('Đeo ngay','jrEquip',{title:story.id,keep:'1'},'cream small')}</div>`:''}
    ${opened.length?`<div class="jr-unlocks"><small>Nơi làm việc mới mở</small><div class="jr-unlock-row">${opened.map(id=>{const m=meta(api,id);return `<span class="jr-unlock" style="--career:${colour(m.color)}"><span aria-hidden="true">${emojiOf(m)}</span>${esc(m.place||m.short)}</span>`;}).join('')}</div></div>`:''}
    ${final?`<p class="jr-epilogue">Từ một căn gác lạ, bạn đã có một nơi để gọi là nhà. Hành trình vẫn tiếp tục, theo nhịp của riêng bạn.</p>`:''}
    ${next?btn(`Tiếp tục ${icon('arrow',15)}`,'jrSceneNext',{n:String(n)},'primary big full'):btn('Về hành trình','jrSceneClose',{},'primary big full')}</div>`;
}

function titleScene(ids){
  const {api}=E,J=api.state.journey,C=api.content.journey;
  const rows=ids.map(id=>{const t=C.titles.find(x=>x.id===id);return t?.secret?{id,...J.secret[id]}:t;}).filter(Boolean);
  if(!rows.length)return '';
  const first=rows[0];
  return `<div class="jr-scene-card celebrate small">${confetti()}<span class="eyebrow">${rows.length>1?`${rows.length} danh hiệu mới`:'Danh hiệu mới'}</span><h2 id="jrSceneTitle">${esc(first.name)}</h2>
    <div class="jr-award-list">${rows.slice(0,8).map(t=>`<div class="jr-award"><span aria-hidden="true">${t.emoji}</span><div><b>${esc(t.name)}</b><small>${esc(t.desc||'')}</small></div></div>`).join('')}${rows.length>8?`<p class="muted small">Và ${rows.length-8} danh hiệu khác trong bộ sưu tập.</p>`:''}</div>
    <div class="row wrap jr-scene-actions">${btn('Đeo danh hiệu này','jrEquip',{title:first.id,keep:'1'},'cream')}${btn('Tuyệt!','jrSceneClose',{},'primary')}</div></div>`;
}

function titleToast(ids){
  const C=E.api.content.journey,J=E.api.state.journey;
  const rows=ids.map(id=>{const t=C.titles.find(x=>x.id===id);return t?.secret?{id,...J.secret[id]}:t;}).filter(Boolean);
  if(rows.length)E.toast?.(`${rows[0].emoji} Danh hiệu mới: ${rows[0].name}${rows.length>1?` (+${rows.length-1})`:''}`,'good');
}

function whoScene(){
  return `<div class="jr-scene-card">${whoForm(E,'Trước khi đi tiếp…','Khu phố muốn biết thêm một chút về bạn.','Lưu và tiếp tục')}</div>`;
}

function storyScene(n){
  const {api}=E,J=api.state.journey,ch=api.content.journey.chapters.find(x=>x.n===n);if(!ch)return '';
  return `<div class="jr-scene-card"><div class="jr-ch-art big" aria-hidden="true">${ch.art}</div><span class="eyebrow">Chương ${ch.n}</span><h2 id="jrSceneTitle">${esc(ch.title)}</h2><div class="jr-lines">${ch.intro.map(l=>say(l,J.gender)).join('')}</div>${btn('Đã hiểu','jrSceneClose',{},'primary big full')}</div>`;
}

let asked=false;
const toasted=new Set();   // title news already said as a toast (first day), while jr_seen is on its way
function maybeScene(){
  if(!E?.api.state?.journey||!E.api.content?.journey)return;
  const J=E.api.state.journey,d=document.getElementById('jrScene');
  if(d?.open||document.getElementById('stScene')?.open||J.story&&!J.intro)return;
  if(document.querySelector('dialog.fh-sheet[open]')){setTimeout(maybeScene,1500);return;}   // 🏮 not over a dice roll: after the fair's dialog closes
  if(!J.story){maybeStory();return;}
  if(document.getElementById('confirmDialog')?.open){setTimeout(maybeScene,400);return;}
  const S=E.api.state;
  const ch=J.news.find(n=>n.kind==='chapter');
  if(ch){if(!quiet(S))openScene(chapterScene(Number(ch.ref)),[ch.id]);return;}   // after the first 3 customers
  const ts=J.news.filter(n=>n.kind==='titles');
  if(ts.length){const ids=[...new Set(ts.flatMap(n=>n.items))];
    // The first day: a small toast, no card over the work (the titles stay in Hành trình → Danh hiệu).
    if(firstDay(S)){const fresh=ts.filter(n=>!toasted.has(n.id));if(fresh.length){fresh.forEach(n=>toasted.add(n.id));titleToast(ids);E.cmd('jr_seen',{ids:fresh.map(n=>n.id)},{quiet:true});}return;}
    const html=titleScene(ids);if(html){openScene(html,ts.map(n=>n.id));return;}
    E.cmd('jr_seen',{ids:ts.map(n=>n.id)},{quiet:true});return;}
  if(!J.gender&&!asked){asked=true;openScene(whoScene());return;}
  maybeStory();   // truyện nghề: a workplace beat, after the journey's own scenes
}

/* ------------------------------------------------------------------ HUD */
/** The journey chip (name, title, wallet) left the stage for a calm screen: the same facts are in the
 * status sheet (tap the day) and the journey home. Removes a chip an older build left. */
function hud(){document.getElementById('jrHud')?.remove();}

/* ------------------------------------------------------------------ wiring */
export function journeyBoot(env){
  E=env;sceneDialog();storiesBoot(env);lifeBoot(env);investBoot(env);
  document.addEventListener('sheetrender',()=>{if(TW.m&&E?.ui.view==='home')TW.m.townMount(E,TOWN_HELP);});   // 🗺️ the stage back into its slot
  const sheet=document.getElementById('sheet');
  // The first-run intro cannot be dismissed into an empty scene.
  sheet?.addEventListener('cancel',e=>{const J=E.api.state?.journey;if(E.ui.view==='home'&&J?.story&&!J.intro)e.preventDefault();});
  env.api.addEventListener('state',()=>{hud();setTimeout(maybeScene,60);});
  hud();setTimeout(maybeScene,300);
}

export async function journeyAction(action,data,el,env){
  if(action?.startsWith('iv'))return investAction(action,data,el,env);
  if(action?.startsWith('lf'))return lifeAction(action,data,el,env);
  if(!action?.startsWith('jr'))return false;
  if(action==='jrInvest'){
    const open=env.ui.view==='home'&&document.getElementById('sheet')?.open;
    if(open){env.ui.jrView='invest';env.renderSheet(false);document.getElementById('sheet')?.scrollTo?.(0,0);}
    else env.openSheet('home',{jrView:'invest'});
    return true;
  }
  if(action==='jrEnterHome'){env.closeSheet();await (await import('./reno.js')).openReno(env);return true;}
  if(action.startsWith('jrHh'))return householdAction(action,data,el,env);
  if(action.startsWith('jrOut'))return outingsAction(action,data,el,env);
  if(action.startsWith('jrShip'))return courierAction(action,data,el,env);
  E=E||env;
  if(action.startsWith('jrArc'))return storiesAction(action,data,el,env);
  if(action.startsWith('jrCert'))return certAction(action,data,el,env);
  if(action==='jrWardrobe'){WD.use();const open=env.ui.view==='home'&&document.getElementById('sheet')?.open;
    if(open){env.ui.jrView='wardrobe';env.renderSheet(false);document.getElementById('sheet')?.scrollTo?.(0,0);}else env.openSheet('home',{jrView:'wardrobe'});return true;}
  if(action.startsWith('jrWd'))return (await WD.get()).wardrobeAction(action,data,el,env);
  if(action==='jrAvatar'){AV.use();const open=env.ui.view==='home'&&document.getElementById('sheet')?.open;
    if(open){env.ui.jrView='avatar';env.renderSheet(false);document.getElementById('sheet')?.scrollTo?.(0,0);}else env.openSheet('home',{jrView:'avatar'});return true;}
  if(action.startsWith('jrAv'))return (await AV.get()).avatarAction(action,data,el,env);
  const {ui,cmd,renderSheet,confirmAction,api}=env;
  switch(action){
    case'jrGoals':ui.jrGoalsExpanded=!ui.jrGoalsExpanded;renderSheet(false);return true;
    case'jrPlaces':{ui.homeMode='list';ui.jrView='home';ui.homeCat='all';renderSheet(false);const places=document.querySelector('.jr-places');places?.scrollIntoView?.({block:'start'});places?.focus?.({preventScroll:true});return true;}
    case'jrView':ui.jrView=data.view||'home';renderSheet(false);document.getElementById('sheet')?.scrollTo?.(0,0);return true;
    case'jrStep':ui.jrStep=data.step;renderSheet(false);return true;
    case'jrJob':ui.jrJob=data.career;renderSheet();return true;
    case'jrGender':{ui.jrGender=data.gender;const scene=document.getElementById('jrScene');
      if(scene?.open){const name=scene.querySelector('[name="name"]')?.value;openScene(whoScene(),sceneQueue||[]);const input=scene.querySelector('[name="name"]');if(input&&name!=null)input.value=name;}
      else renderSheet();return true;}
    case'jrWear':{   // toggle one title or certificate in what is worn (the server checks it is yours and the cap)
      const J=api.state.journey,cur=wornOf(J).map(w=>w.id),id=data.item;if(!id)return true;
      if(!cur.includes(id)&&cur.length>=wearMax(J)){env.toast?.(`Đeo tối đa ${wearMax(J)} cái. Chạm một cái đang đeo để cất bớt nhé.`,true);return true;}
      const r=await cmd('jr_equip',{worn:cur.includes(id)?cur.filter(x=>x!==id):[...cur,id]});
      if(r&&ui.view==='home')renderSheet(false);return true;}
    case'jrEquip':{   // "Đeo ngay" on a new title: it goes first, the others stay while they fit
      const J=api.state.journey,id=data.title||null;
      const r=await cmd('jr_equip',Array.isArray(J.worn)?{worn:id?[id,...J.worn.map(w=>w.id).filter(x=>x!==id)].slice(0,wearMax(J)):[]}:{title:id});
      // Inside a scene the toast sits behind the dialog: say it on the button.
      if(r&&el?.closest('#jrScene')){el.textContent='✓ Đang đeo';el.disabled=true;}
      if(r&&ui.view==='home')renderSheet();return true;}
    case'jrMax':{const input=document.getElementById(data.input);if(input)input.value=data.value;return true;}
    case'jrPause':{const place=placeOf(api,data.career);
      if(await confirmAction(`Tạm đóng ${place}?`,'Khi tạm đóng, nơi này chưa làm việc được. Mở lại lúc nào cũng được, không tốn phí.','Tạm đóng'))await cmd('jr_pause',{career:data.career,confirm:true});return true;}
    case'jrReopen':{const place=placeOf(api,data.career);
      if(!await confirmAction(`Mở lại ${place}?`,'Mở lại không tốn phí. Quỹ, hàng và người làm vẫn để nguyên như lúc bạn đi.','Mở lại'))return true;
      const r=await cmd('jr_reopen',{career:data.career,confirm:true});
      if(r&&data.go)await env.act('choose',{career:data.career});   // 🗺️ from a door on the map: reopened, then straight in (feedback #140)
      return true;}
    case'jrStory':openScene(storyScene(Number(data.n)));return true;
    case'jrSceneNext':{const n=Number(data.n);openScene(chapterScene(n,1),sceneQueue||[]);return true;}
    case'jrSceneClose':await closeScene();return true;
    case'jrHome':ui.jrView='home';env.openSheet('home');return true;
    // 🗺️ the town ⇄ the list, for now (the "Hành trình" entry goes back to the setting's choice)
    case'jrList':case'jrTown':{ui.homeMode=action==='jrList'?'list':'town';ui.jrView='home';
      if(ui.view==='home'&&document.getElementById('sheet')?.open){renderSheet(false);document.getElementById('sheet')?.scrollTo?.(0,0);}else env.openSheet('home');return true;}
  }
  return false;
}

export async function journeySubmit(f,env){
  const kind=f.dataset.jrForm;if(!kind)return false;
  if(kind==='hhAdopt'||kind==='hhName')return householdSubmit(f,env);
  const {ui,cmd,renderSheet,api}=env;
  if(kind==='start'){   // the intro's one screen: name + look, then the first workplace (no step in between)
    const name=f.querySelector('[name="name"]')?.value.trim()||'',gender=ui.jrGender||api.state.journey.gender;
    // The button stays tappable before a look is picked (a disabled one gave no answer): say why and show where.
    if(!gender){env.toast?.('Chọn Nam hoặc Nữ trước nhé.',true);highlight(f.querySelector('.jr-genders'));return true;}
    const btn=f.querySelector('[type="submit"]');if(btn)btn.disabled=true;
    const town=townWanted(ui);
    const r=await cmd('jr_profile',{name,gender});
    if(!r){if(btn)btn.disabled=false;return true;}
    ui.jrGender=null;
    if(town){ui.jrJob=null;renderSheet(false);return true;}   // 🗺️ into the town: the lit shops show where to start
    const ids=api.content.journey.chapters[0].unlocks.filter(id=>api.state.careers[id]);
    const job=ids.includes(ui.jrJob)?ui.jrJob:ids.includes(FIRST_JOB)?FIRST_JOB:ids[0];ui.jrJob=null;
    if(job)await env.act('choose',{career:job});
    return true;
  }
  if(kind==='profile'){
    const name=f.querySelector('[name="name"]')?.value.trim()||'',gender=ui.jrGender||api.state.journey.gender;
    if(!gender){env.toast?.('Chọn Nam hoặc Nữ trước nhé.',true);return true;}
    const r=await cmd('jr_profile',{name,gender});
    if(r){ui.jrGender=null;if(document.getElementById('jrScene')?.open)await closeScene();else if(!api.state.journey.intro){ui.jrStep='job';renderSheet(false);}else{ui.jrView='home';renderSheet(false);}}
    return true;
  }
  if(kind==='withdraw'||kind==='invest'){
    const amount=Number(f.querySelector('[name="amount"]')?.value);
    if(!Number.isInteger(amount)||amount<1){env.toast?.('Nhập số xu là số nguyên dương nhé.',true);return true;}
    await cmd(kind==='withdraw'?'jr_withdraw':'jr_invest',{career:f.dataset.career,amount});
    return true;
  }
  return false;
}

/** A small line for the career HUD / profile: "🏠 Hàng xóm mới". */
export function titleLine(state){
  const w=wornOf(state?.journey)[0];return w?`${w.emoji} ${w.name}`:'';
}
