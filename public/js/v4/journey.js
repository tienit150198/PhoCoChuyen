/** Hành trình: one person, one small neighbourhood. The journey home (character,
 * chapter, workplaces), its sheets (titles, wallet, profile), the first-run
 * intro and the story scenes. Markup only: every rule lives in
 * game/journey.py. Buttons use data-action="jr…" (journeyAction) or the app's
 * `choose`/`close`; forms use data-jr-form (journeySubmit). */
import {icon,escapeHTML as esc} from '../icons.js';
import {accountChip} from './account.js';
import {storiesBoot,storiesCard,storiesAction,maybeStory} from './stories.js';
import {investView,investEntry,investAction} from './invest.js';
import {boardEntry} from './board.js';
import {lifeView,lifeEntry,lifeCard,lifeAction,lifeBoot} from './life.js';

export const EMOJI={restaurant:'🍜',cafe_bakery:'🥐',grocery:'🛒',repair:'🔧',homestay:'🏡',corp_accounting:'🧮',tax_payroll:'🧾',group_accounting:'🏢',
  mother_baby:'🎁',pharmacy:'💊',accounting:'📒',customer_care:'🎧',teacher:'🍎',tour_guide:'🧭',milk_tea:'🧋',florist:'💐',salon:'💇',
  pet_care:'🐾',farm:'🌾',delivery:'🛵'};
const CATS={food:'Ăn uống',shop:'Buôn bán',service:'Dịch vụ',office:'Văn phòng',outdoor:'Ngoài trời'};
const LEGACY_CAT={mother_baby:'shop',pharmacy:'shop',accounting:'office',customer_care:'office',teacher:'service',tour_guide:'outdoor',milk_tea:'food'};
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

/** Warm little portrait of the player, drawn inline (no external art). */
export function avatar(gender,size=56){
  const f=gender==='female',m=gender==='male',hair='#5b4436',skin='#f5cfae',shirt=f?'#e39a8a':m?'#78a3b6':'#c3ab83';
  const label=f?'Nhân vật nữ':m?'Nhân vật nam':'Nhân vật của bạn';
  const front=m?`<path d="M20 37Q18 13 40 12Q62 13 60 37Q56 25 45 22Q35 30 20 37Z" fill="${hair}"/>`
    :f?`<path d="M21 38Q21 15 40 15Q59 15 59 38Q52 25 41 22Q31 26 21 38Z" fill="${hair}"/>`
    :`<path d="M20 36Q20 15 40 14Q60 15 60 36Q52 25 40 24Q28 25 20 36Z" fill="${hair}"/>`;
  return `<svg class="jr-av" width="${size}" height="${size}" viewBox="0 0 80 80" role="img" aria-label="${label}"><rect width="80" height="80" rx="26" fill="#f4e4cf"/>`+
    (f?`<circle cx="40" cy="12" r="9" fill="${hair}"/><path d="M18 44C12 10 68 10 62 44L64 68H16Z" fill="${hair}"/>`:'')+
    `<path d="M12 80c2-23 54-23 56 0" fill="${shirt}"/><rect x="34" y="50" width="12" height="12" rx="5" fill="#e6b692"/><ellipse cx="40" cy="38" rx="19" ry="21" fill="${skin}"/>${front}`+
    `<ellipse cx="33" cy="40" rx="2.8" ry="3.4" fill="#4b3936"/><ellipse cx="47" cy="40" rx="2.8" ry="3.4" fill="#4b3936"/><circle cx="32.3" cy="38.8" r="1" fill="#fff"/><circle cx="46.3" cy="38.8" r="1" fill="#fff"/>`+
    `<ellipse cx="28" cy="46" rx="3.6" ry="2.2" fill="#e08f86" opacity=".55"/><ellipse cx="52" cy="46" rx="3.6" ry="2.2" fill="#e08f86" opacity=".55"/><path d="M36 48q4 4 8 0" fill="none" stroke="#a46e5e" stroke-width="1.8" stroke-linecap="round"/></svg>`;
}

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
  if(J.story&&!J.intro)return introView(env);
  if(ui.jrView==='titles')return titlesView(env);
  if(ui.jrView==='wallet')return walletView(env);
  if(ui.jrView==='invest')return investView(env);
  if(ui.jrView==='life')return lifeView(env);
  if(ui.jrView==='profile')return profileView(env);
  return homeMain(env);
}

function meCard(env){
  const {api}=env,J=api.state.journey,C=api.content.journey,mat=J.maturity;
  const span=mat.next?Math.max(1,mat.next-mat.floor):1,pct=mat.next?Math.min(100,Math.round((mat.xp-mat.floor)*100/span)):100;
  const eq=J.equipped_title;
  const skills=(C.skills||[]).map(sk=>{const v=J.skills.find(x=>x.id===sk.id)||{level:0};return `<li class="jr-skill ${v.level?'':'zero'}" title="${esc(sk.name)}"><span aria-hidden="true">${sk.emoji}</span><b>${esc(SKILL_SHORT[sk.id]||sk.name)}</b><i class="jr-pips" aria-label="Mức ${v.level}">${'●'.repeat(v.level)}${'○'.repeat(Math.max(0,6-v.level))}</i></li>`;}).join('');
  const wallet=J.story?`<button type="button" class="jr-stat ${J.debt?'bad':''}" data-action="jrView" data-view="wallet"><small>Ví của bạn</small><b>${J.debt?`Nợ ${fmt(J.debt)} xu`:`${fmt(J.wallet)} xu`}</b></button>`:'';
  return `<section class="jr-card jr-me" aria-label="Nhân vật của bạn">
    <div class="jr-me-top"><button type="button" class="jr-avatar" data-action="jrView" data-view="profile" aria-label="Sửa tên và nhân vật">${avatar(J.gender,68)}</button>
      <div class="jr-me-text"><h2>${esc(api.state.name)}</h2>
        ${J.story?`<button type="button" class="jr-title-chip ${eq?'':'empty'}" data-action="jrView" data-view="titles">${eq?`<span aria-hidden="true">${eq.emoji}</span> ${esc(eq.name)}`:'Chọn danh hiệu để đeo'}</button>`:''}
        <div class="jr-level"><div class="jr-level-row"><b>Trưởng thành cấp ${mat.level}</b><small>${esc(mat.name)}</small></div><div class="jr-bar" role="progressbar" aria-label="Kinh nghiệm trưởng thành" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><i style="width:${pct}%"></i></div></div></div></div>
    ${J.story?`<div class="jr-stats">${wallet}<div class="jr-stat"><small>Ngày sống</small><b>${fmt(J.life_day)}</b></div><button type="button" class="jr-stat" data-action="jrView" data-view="titles"><small>Danh hiệu</small><b>${J.titles.length}</b></button></div>`:''}
    <details class="jr-skills-box"><summary>Kỹ năng</summary><ul class="jr-skills">${skills}</ul></details>
  </section>`;
}

function chapterCard(env){
  const {api}=env,J=api.state.journey,C=api.content.journey,g=J.gender;
  const sid=J.suggested,sm=sid?meta(api,sid):null,room=sid?api.state.careers[sid]:null;
  const place=sm?(sm.place||sm.short):'';
  const job=room?.job||{};
  const label=!room?'':job.required&&job.status!=='hired'?(job.status==='offer'?`Xem thư mời ở ${place}`:`Xin việc ở ${place}`):room.started?`Tiếp tục ở ${place}`:`Thử làm ở ${place}`;
  const cta=sid?`<button type="button" class="btn primary big full jr-cta" data-action="choose" data-career="${esc(sid)}"><span aria-hidden="true">${emojiOf(sm)}</span> ${esc(label)} ${icon('arrow',16)}</button>`:'';
  if(J.finale){
    const last=C.chapters[C.chapters.length-1];
    return `<section class="jr-card jr-chapter finale"><div class="jr-ch-art" aria-hidden="true">🏮</div><span class="eyebrow">HÀNH TRÌNH TIẾP DIỄN</span><h2>Người của khu phố</h2><p class="muted">Khu phố đã là nhà. Mỗi ngày vẫn còn những việc nhỏ đáng làm.</p>${say(last.outro[0],g)}${cta}</section>`;
  }
  const ch=C.chapters.find(x=>x.n===J.chapter);if(!ch)return '';
  const goals=J.goals.map(x=>`<li class="${x.done?'done':''}"><span class="jr-check" aria-hidden="true">${x.done?icon('check',14):''}</span><span class="grow">${esc(x.text)}</span><b>${fmt(Math.min(x.cur,x.goal))}/${fmt(x.goal)}</b></li>`).join('');
  const done=J.goals.filter(x=>x.done).length;
  const paused=J.progress_paused?`<div class="notice jr-debt">${icon('coin',17)}<div>Ví đang nợ ${fmt(J.debt)} xu nên câu chuyện tạm dừng. Rút tiền lời từ một nơi làm việc để trả là đi tiếp được.</div></div>${btn('Mở ví của bạn','jrView',{view:'wallet'},'ghost small')}`:'';
  return `<section class="jr-card jr-chapter"><div class="jr-ch-top"><div class="jr-ch-art" aria-hidden="true">${ch.art}</div><div class="grow"><span class="eyebrow">Chương ${ch.n}/${C.chapters.length}</span><h2>${esc(ch.title)}</h2><p class="muted">${esc(ch.tagline)}</p></div></div>
    ${say(ch.intro[ch.intro.length-1],g,'compact')}
    <button type="button" class="jr-link" data-action="jrStory" data-n="${ch.n}">${icon('book',14)} Nghe lại câu chuyện</button>
    <h3 class="jr-goals-title">Việc cần làm <small>${done}/${J.goals.length}</small></h3><ul class="jr-goals">${goals}</ul>${paused}${cta}</section>`;
}

function placeCard(env,cid){
  const {api}=env,J=api.state.journey,m=meta(api,cid),c=api.state.careers[cid],p=J.places[cid];
  const job=c.job||{},tags=[];
  if(cid===api.state.current&&c.started)tags.push(tag('Đang làm','blue'));
  if(c.started)tags.push(tag(`Ngày ${c.day} · Cấp ${c.level||1}`,'green'));
  if(p?.paused)tags.push(tag('Tạm đóng','amber'));
  if(job.status==='offer')tags.push(tag('💌 Có thư mời','blue'));
  else if(job.required&&job.status!=='hired')tags.push(tag(icon('briefcase',12)+' Cần xin việc','amber'));
  if(!c.started&&J.story&&(api.content.journey.unlock_chapter||{})[cid]===J.chapter)tags.push(tag('Mới mở','green'));
  let money='';
  if(p&&J.story)money=p.employed?`<p class="jr-fund">Làm thuê · lương về ví</p>`:`<p class="jr-fund">Quỹ ${fmt(p.fund)} xu · ${p.paused?'không tốn phí duy trì':`duy trì ${fmt(p.upkeep)} xu/ngày`}</p>`;
  const action=p?.paused?btn('Mở lại','jrReopen',{career:cid},'cream small'):
    btn(`${c.started?'Tiếp tục':job.required&&job.status!=='hired'?'Xin việc':'Bắt đầu'} ${icon('arrow',13)}`,'choose',{career:cid},c.started?'primary small':'cream small');
  return `<article class="jr-place ${p?.paused?'paused':''} ${cid===api.state.current?'current':''}" style="--career:${colour(m.color)}"><span class="jr-place-emoji" aria-hidden="true">${emojiOf(m)}</span>
    <div class="jr-place-text"><span class="eyebrow">${esc(CATS[catOf(m)]||'')}</span><h3>${esc(m.place||m.short)}</h3><small>${esc(m.short||'')}</small><div class="jr-tags">${tags.join('')}</div>${money}</div>${action}</article>`;
}

function lockedTile(env,cid){
  const {api}=env,J=api.state.journey,m=meta(api,cid),n=(api.content.journey.unlock_chapter||{})[cid];
  const hint=n===J.chapter+1?'Sắp mở':'Còn ở phía trước';
  return `<article class="jr-locked" aria-label="Nơi làm việc chưa mở"><span class="jr-place-emoji silhouette" aria-hidden="true">${emojiOf(m)}</span><b>🔒 Chưa mở</b><small>${esc(CATS[catOf(m)]||'')}<br>${hint}</small></article>`;
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
  return `<section class="jr-places" aria-label="Nơi làm việc"><div class="jr-sec-head"><h2>Nơi làm việc</h2><small>${open.length}/${all.length} nơi đã mở</small></div>${chips}
    <div class="jr-grid">${shown.map(id=>placeCard(env,id)).join('')}</div>
    ${locked.length?`<h3 class="jr-sub">Còn ở phía trước</h3><div class="jr-locked-grid">${soon.map(id=>lockedTile(env,id)).join('')}${rest}</div>`:''}</section>`;
}

function homeMain(env){
  const {api}=env,J=api.state.journey;
  const top=`<header class="jr-top"><div class="grow"><span class="eyebrow">${J.story?`Khu phố nhỏ · Ngày sống ${fmt(J.life_day)}`:'Khu phố nhỏ · mọi nơi đều mở'}</span><h1>Hành trình của bạn</h1></div>${accountChip(env)}${api.state.current?btn(icon('x',20),'close',{},'ghost small jr-close','aria-label="Đóng"'):''}</header>`;
  return `<div class="jr-home">${top}<div class="jr-columns"><div class="jr-col">${meCard(env)}${lifeCard(env)}${boardEntry(env)}${J.story?chapterCard(env):''}${storiesCard(env)}</div><div class="jr-col wide">${placesSection(env)}</div></div></div>`;
}

/* ------------------------------------------------------------------ intro */
function introView(env){
  const {api,ui}=env,J=api.state.journey,C=api.content.journey,ch=C.chapters[0];
  const step=J.gender&&ui.jrStep!=='who'?'job':ui.jrStep||'arrive';
  if(step==='arrive'){
    return `<div class="jr-intro"><div class="jr-street" aria-hidden="true"><span>🏠</span><span>🏪</span><span>🌳</span><span>🧋</span><span>🏮</span><span>🛵</span></div>
      <span class="eyebrow">Ngày đầu tiên</span><h1>Một khu phố nhỏ, một căn gác thuê</h1>
      <p class="jr-lead">Bạn vừa chuyển tới đây với một chiếc ba lô. Chưa quen ai, chưa có nghề gì trong tay, chỉ có thật nhiều tò mò.</p>
      <div class="jr-lines">${ch.intro.slice(0,2).map(l=>say(l,J.gender)).join('')}</div>
      <button type="button" class="btn primary big full" data-action="jrStep" data-step="who">Chào khu phố ${icon('arrow',16)}</button>
      ${api.account?'':`<button type="button" class="jr-link acct-intro-link" data-action="v4AccountOpen" data-mode="login">${icon('user',14)} Đã có tài khoản? Đăng nhập</button>`}</div>`;
  }
  if(step==='who')return `<div class="jr-intro">${whoForm(env,'Bạn là ai?','Hàng xóm sẽ gọi bạn thế nào?','Đây là mình')}</div>`;
  const ids=ch.unlocks.filter(id=>api.state.careers[id]);
  return `<div class="jr-intro"><span class="eyebrow">Việc đầu tiên</span><h1>Bắt đầu từ đâu nhỉ?</h1>
    <div class="jr-lines">${say(ch.intro[2],J.gender)}</div>
    <div class="jr-first-jobs">${ids.map(id=>{const m=meta(api,id);return `<button type="button" class="jr-job" data-action="choose" data-career="${esc(id)}" style="--career:${colour(m.color)}"><span class="jr-job-emoji" aria-hidden="true">${emojiOf(m)}</span><b>${esc(m.place||m.short)}</b><small>${esc(m.tagline||m.short||'')}</small><span class="jr-job-go">Làm thử ${icon('arrow',14)}</span></button>`;}).join('')}</div>
    <button type="button" class="jr-link" data-action="jrStep" data-step="who">${icon('back',14)} Sửa tên hoặc nhân vật</button></div>`;
}

function whoForm(env,title,sub,cta){
  const {api,ui}=env,J=api.state.journey,pick=ui.jrGender||J.gender||'';
  const card=(g,label)=>`<button type="button" class="jr-gender ${pick===g?'active':''}" data-action="jrGender" data-gender="${g}" aria-pressed="${pick===g}">${avatar(g,96)}<b>${label}</b></button>`;
  return (title?`<span class="eyebrow">Nhân vật</span><h1>${title}</h1><p class="jr-lead">${sub}</p>`:'')+`
    <form class="jr-who" data-jr-form="profile"><div class="jr-genders" role="group" aria-label="Giới tính">${card('male','Nam')}${card('female','Nữ')}</div>
    <label class="jr-name"><span>Tên của bạn</span><input id="jr-name" name="name" maxlength="24" autocomplete="nickname" required value="${esc(api.state.name)}" data-preserve></label>
    <button type="submit" class="btn primary big full" ${pick?'':'disabled'}>${cta} ${icon('arrow',16)}</button></form>`;
}

function profileView(env){
  return head('Nhân vật của bạn','',{back:true})+`<div class="sheet-body jr-body jr-profile">${whoForm(env,'','','Lưu lại')}</div>`;
}

/* ------------------------------------------------------------------ titles */
function titlesView(env){
  const {api}=env,J=api.state.journey,C=api.content.journey,have=new Map(J.titles);
  const cats=C.cats.map(cat=>{
    const rows=C.titles.filter(t=>t.cat===cat.id);if(!rows.length)return '';
    const tiles=rows.map(t=>{
      const day=have.get(t.id);
      if(day!==undefined){
        const info=t.secret?J.secret[t.id]:t,on=J.equipped===t.id;
        return `<button type="button" class="jr-title earned ${on?'on':''}" data-action="jrEquip" data-title="${on?'':esc(t.id)}" aria-pressed="${on}"><span class="jr-title-emoji" aria-hidden="true">${info.emoji}</span><b>${esc(info.name)}</b><small>${esc(info.desc)}</small><em>${on?'Đang đeo':`Ngày sống ${fmt(day)} · Đeo`}</em></button>`;
      }
      if(t.secret)return `<div class="jr-title secret"><span class="jr-title-emoji" aria-hidden="true">❔</span><b>???</b><small>Bí mật. Cứ sống ở phố rồi sẽ biết.</small></div>`;
      return `<div class="jr-title"><span class="jr-title-emoji" aria-hidden="true">${t.emoji}</span><b>${esc(t.name)}</b><small>${esc(t.desc)}</small></div>`;
    }).join('');
    const got=rows.filter(t=>have.has(t.id)).length;
    return `<section class="jr-title-cat"><h3>${esc(cat.name)} <small>${got}/${rows.length}</small></h3><div class="jr-title-grid">${tiles}</div></section>`;
  }).join('');
  return head('Danh hiệu',`Đã có ${J.titles.length}/${C.titles.length}.`,{back:true})+`<div class="sheet-body jr-body">${cats}</div>`;
}

/* ------------------------------------------------------------------ wallet */
function walletView(env){
  const {api}=env,J=api.state.journey,C=api.content.journey;
  if(!J.story)return head('Ví của bạn','',{back:true})+`<div class="sheet-body jr-body"><p class="muted">Ví và quỹ nơi làm việc có trong hành trình.</p></div>`;
  const places=Object.entries(J.places).map(([cid,p])=>{
    const m=meta(api,cid),c=api.state.careers[cid];
    const draw=p.withdraw_max>0?`<form class="jr-move" data-jr-form="withdraw" data-career="${esc(cid)}"><label><span>Rút về ví</span><input type="number" name="amount" inputmode="numeric" min="1" max="${p.withdraw_max}" value="${Math.min(p.withdraw_max,50)}" id="jr-draw-${esc(cid)}" data-preserve></label><button type="submit" class="btn primary small">Rút</button>${btn('Tối đa','jrMax',{input:'jr-draw-'+cid,value:p.withdraw_max},'ghost small')}</form>`
      :`<p class="muted small">Quỹ cần giữ ${fmt(C.reserve)} xu và đủ tiền hóa đơn chưa trả${p.unpaid?` (${fmt(p.unpaid)} xu)`:''}, nên chưa rút được.</p>`;
    const invest=J.wallet>0?`<form class="jr-move" data-jr-form="invest" data-career="${esc(cid)}"><label><span>Góp vốn</span><input type="number" name="amount" inputmode="numeric" min="1" max="${J.wallet}" value="${Math.min(J.wallet,20)}" id="jr-invest-${esc(cid)}" data-preserve></label><button type="submit" class="btn cream small">Góp</button></form>`:'';
    const pause=p.employed?'':p.paused?btn(`Mở lại · ${fmt(C.reopen_fee)} xu`,'jrReopen',{career:cid},'cream small'):btn('Tạm đóng','jrPause',{career:cid},'ghost small',c.open?' disabled title="Khép ca trước"':'');
    return `<details class="jr-fundrow ${p.paused?'paused':''}"><summary><span class="jr-place-emoji" aria-hidden="true">${emojiOf(m)}</span><span class="grow"><b>${esc(m.place||m.short)}</b><small>${p.employed?'Làm thuê · lương về ví':p.paused?'Tạm đóng · không tốn phí duy trì':`Duy trì ${fmt(p.upkeep)} xu/ngày khi vắng chủ`}</small></span><b class="jr-amt">${fmt(p.fund)} xu</b></summary>
      <div class="jr-fund-actions">${draw}${invest}<div class="row wrap">${pause}</div></div></details>`;
  }).join('')||`<p class="muted">Chưa có nơi làm việc nào. Bắt đầu ở một tiệm trong hẻm nhé.</p>`;
  const kinds={living:'🏠',upkeep:'💡',draw:'👛',invest:'📈',salary:'💵',reopen:'🔑',incident:'⚖️',life:'🌿'};
  const hist=J.history.map(h=>`<li><span aria-hidden="true">${kinds[h.kind]||'•'}</span><span class="grow">${esc(h.label)}<small>Ngày sống ${fmt(h.day)}</small></span><b class="${h.amount<0?'out':'in'}">${h.amount<0?'−':'+'}${fmt(Math.abs(h.amount))} xu</b></li>`).join('')||`<li class="muted">Chưa có khoản nào.</li>`;
  const L=J.living;
  return head('Ví của bạn','',{back:true})+`<div class="sheet-body jr-body">
    <section class="jr-card jr-purse ${J.debt?'bad':''}" aria-live="polite"><small>${J.debt?'Đang nợ tiền phòng':'Số dư'}</small><strong>${J.debt?`${fmt(J.debt)} xu`:`${fmt(J.wallet)} xu`}</strong>
      <p>Mỗi ngày sống: tiền phòng ${fmt(L.rent)} xu và cơm nước ${fmt(L.meals)} xu.</p>
      ${J.debt?`<p class="jr-debt-note">Khi ví còn nợ, câu chuyện tạm dừng. Rút tiền lời về ví để trả nhé.</p>`:''}</section>
    ${investEntry(env)}${lifeEntry(env)}
    <h3 class="jr-sub">Quỹ các nơi làm việc</h3><div class="jr-funds">${places}</div>
    <h3 class="jr-sub">Sổ ví gần đây</h3><ul class="jr-history">${hist}</ul></div>`;
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

function whoScene(){
  return `<div class="jr-scene-card">${whoForm(E,'Trước khi đi tiếp…','Khu phố muốn biết thêm một chút về bạn.','Lưu và tiếp tục')}</div>`;
}

function storyScene(n){
  const {api}=E,J=api.state.journey,ch=api.content.journey.chapters.find(x=>x.n===n);if(!ch)return '';
  return `<div class="jr-scene-card"><div class="jr-ch-art big" aria-hidden="true">${ch.art}</div><span class="eyebrow">Chương ${ch.n}</span><h2 id="jrSceneTitle">${esc(ch.title)}</h2><div class="jr-lines">${ch.intro.map(l=>say(l,J.gender)).join('')}</div>${btn('Đã hiểu','jrSceneClose',{},'primary big full')}</div>`;
}

let asked=false;
function maybeScene(){
  if(!E?.api.state?.journey||!E.api.content?.journey)return;
  const J=E.api.state.journey,d=document.getElementById('jrScene');
  if(d?.open||document.getElementById('stScene')?.open||J.story&&!J.intro)return;
  if(!J.story){maybeStory();return;}
  if(document.getElementById('confirmDialog')?.open){setTimeout(maybeScene,400);return;}
  const ch=J.news.find(n=>n.kind==='chapter');
  if(ch){openScene(chapterScene(Number(ch.ref)),[ch.id]);return;}
  const ts=J.news.filter(n=>n.kind==='titles');
  if(ts.length){const ids=[...new Set(ts.flatMap(n=>n.items))];const html=titleScene(ids);if(html){openScene(html,ts.map(n=>n.id));return;}
    E.cmd('jr_seen',{ids:ts.map(n=>n.id)},{quiet:true});return;}
  if(!J.gender&&!asked){asked=true;openScene(whoScene());return;}
  maybeStory();   // truyện nghề: a workplace beat, after the journey's own scenes
}

/* ------------------------------------------------------------------ HUD */
/** Phone chip keeps the wallet short (1.000.000 → 1tr) so it never runs into the scene's title card. */
const shortXu=n=>Math.abs(n)>=999950?`${(n/1e6).toLocaleString('vi-VN',{maximumFractionDigits:2})}tr`:Math.abs(n)>=1e5?`${(n/1e3).toLocaleString('vi-VN',{maximumFractionDigits:1})}k`:fmt(n);
let hudWatch=null;
function hud(){
  if(!E?.api.state?.journey)return;
  let el=document.getElementById('jrHud');
  const stage=document.getElementById('stage');
  if(!el&&stage){el=document.createElement('button');el.type='button';el.id='jrHud';el.className='jr-hud';el.dataset.action='home';stage.appendChild(el);}
  if(!el)return;
  const J=E.api.state.journey;
  el.hidden=!J.story||!E.api.state.current;
  if(el.hidden)return;
  const eq=J.equipped_title;
  el.setAttribute('aria-label','Mở hành trình của bạn');
  el.innerHTML=`${avatar(J.gender,34)}<span class="jr-hud-text"><b>${E.api.state.life?.pending?'<i class="lf-dot" aria-hidden="true"></i>':''}${esc(E.api.state.name)}</b><small>${eq?`${eq.emoji} ${esc(eq.name)}`:`Cấp ${J.maturity.level} · ${esc(J.maturity.name)}`}</small></span><span class="jr-hud-wallet ${J.debt?'bad':''}"><span class="jr-hud-long">${J.debt?`Nợ ${fmt(J.debt)} xu`:`👛 ${fmt(J.wallet)} xu`}</span><span class="jr-hud-short">${J.debt?`Nợ ${shortXu(J.debt)}`:`👛 ${shortXu(J.wallet)}`}</span></span>`;
  // The title card leaves exactly the chip's width free (CSS var), whatever the layout or wallet length.
  if(!hudWatch&&typeof ResizeObserver!=='undefined'){hudWatch=new ResizeObserver(()=>{el.parentElement?.style.setProperty('--jr-hud-w',`${Math.ceil(el.offsetWidth)}px`);});hudWatch.observe(el);}
}

/* ------------------------------------------------------------------ wiring */
export function journeyBoot(env){
  E=env;sceneDialog();storiesBoot(env);lifeBoot(env);
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
  E=E||env;
  if(action.startsWith('jrArc'))return storiesAction(action,data,el,env);
  const {ui,cmd,renderSheet,confirmAction,api}=env;
  switch(action){
    case'jrView':ui.jrView=data.view||'home';renderSheet(false);document.getElementById('sheet')?.scrollTo?.(0,0);return true;
    case'jrStep':ui.jrStep=data.step;renderSheet(false);return true;
    case'jrGender':{ui.jrGender=data.gender;const scene=document.getElementById('jrScene');
      if(scene?.open){const name=scene.querySelector('[name="name"]')?.value;openScene(whoScene(),sceneQueue||[]);const input=scene.querySelector('[name="name"]');if(input&&name!=null)input.value=name;}
      else renderSheet();return true;}
    case'jrEquip':{const r=await cmd('jr_equip',{title:data.title||null});
      // Inside a scene the toast sits behind the dialog: say it on the button.
      if(r&&el?.closest('#jrScene')){el.textContent='✓ Đang đeo';el.disabled=true;}
      if(r&&ui.view==='home')renderSheet();return true;}
    case'jrMax':{const input=document.getElementById(data.input);if(input)input.value=data.value;return true;}
    case'jrPause':{const place=placeOf(api,data.career);
      if(await confirmAction(`Tạm đóng ${place}?`,`Khi tạm đóng, nơi này không tốn phí duy trì và chưa làm việc được. Mở lại tốn ${api.content.journey.reopen_fee} xu.`,'Tạm đóng'))await cmd('jr_pause',{career:data.career,confirm:true});return true;}
    case'jrReopen':{const place=placeOf(api,data.career);
      if(await confirmAction(`Mở lại ${place}?`,`Phí mở lại ${api.content.journey.reopen_fee} xu, trả từ quỹ của nơi này (nếu quỹ thiếu thì trả từ ví).`,'Mở lại'))await cmd('jr_reopen',{career:data.career,confirm:true});return true;}
    case'jrStory':openScene(storyScene(Number(data.n)));return true;
    case'jrSceneNext':{const n=Number(data.n);openScene(chapterScene(n,1),sceneQueue||[]);return true;}
    case'jrSceneClose':await closeScene();return true;
    case'jrHome':ui.jrView='home';env.openSheet('home');return true;
  }
  return false;
}

export async function journeySubmit(f,env){
  const kind=f.dataset.jrForm;if(!kind)return false;
  const {ui,cmd,renderSheet,api}=env;
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
  const eq=state?.journey?.equipped_title;return eq?`${eq.emoji} ${eq.name}`:'';
}
