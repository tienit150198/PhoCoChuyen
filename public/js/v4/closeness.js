/** 👥 Người quen: điểm thân quen with each neighbour and customer (server: game/closeness.py,
 * state.closeness = closeness.public()). The list (Hàng xóm | Khách quen) with tier, progress and the
 * likes revealed so far; a profile card per person (💬 Trò chuyện, 🎁 Tặng quà, recent history); the
 * inbox (gifts to thank, invites to answer, words of care) and the gift bag.
 * Render-only: every number and every word comes from the server. Commands: qn_chat, qn_gift,
 * qn_thank, qn_invite, qn_use. Actions: qnOpen, qnBack, qnTab, qnChat, qnPick, qnGift, qnThank,
 * qnInvite, qnUse. Loaded by app.js for the 'people' sheet.
 * 💛 Thân thiết (state.closeness.gw, game/goodwill.py): what being close is worth (the perk ladder, 🔒 ??? rows until
 * reached), today's 📝 việc nhờ, 🎂 birthdays, 🤝 referrals, weekly favours (qn_favour), the ✨ badge (qn_gw_seen) and
 * the first-time guide card (game/coach/people.py → tutorial/coach-content.js "features", note id gw1). */
import {icon,portrait,escapeHTML as esc} from '../icons.js';
import {asset} from '../assets.js';
import {notesSeen,markNoteSeen} from '../tutorial/store.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,action,data={},style='',extra='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}${extra}>${label}</button>`;
const signed=n=>n>0?`+${n}`:n<0?`−${Math.abs(n)}`:'±0';

let cssReady=null;
function ensureCss(){
  if(cssReady)return cssReady;
  cssReady=new Promise(done=>{
    if(document.querySelector('link[data-qn-css]')){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=asset('/css/closeness.css');l.dataset.qnCss='';
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
  return cssReady;
}

const dataOf=api=>api.state?.closeness||null;
const personOf=(api,id)=>dataOf(api)?.people?.find(p=>p.id===id)||null;
const npcOf=(api,id)=>api.content?.npcs?.find(n=>n.id===id);

function face(api,p,size=52){
  if(p.cast||!npcOf(api,p.id))return `<span class="qn-face" style="--s:${size}px" aria-hidden="true">${esc(p.emoji||'🙂')}</span>`;
  return `<span class="qn-face pic" style="--s:${size}px" aria-hidden="true">${portrait(npcOf(api,p.id),size)}</span>`;
}
/** Share of the way from this tier's floor to the next one (a full bar at Như người nhà). */
function pct(p){return p.next==null?100:Math.max(4,Math.round((p.score-p.floor)/(p.next-p.floor)*100));}
function bar(p){
  return `<div class="qn-bar t${p.tier}" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${p.score}" aria-label="Điểm thân quen ${p.score} trên 100"><i style="width:${pct(p)}%"></i></div>`;
}
const chip=p=>`<span class="qn-tier t${p.tier}"><span aria-hidden="true">${p.tier_emoji}</span> ${esc(p.tier_name)}</span>`;
function likes(p,full=false){
  const out=p.likes.map(x=>`<span class="qn-like" title="${esc(x.label)}"><span aria-hidden="true">${x.emoji}</span>${full?` ${esc(x.label)}`:''}</span>`);
  if(full)out.push(...p.dislikes.map(x=>`<span class="qn-like no"><span aria-hidden="true">${x.emoji}</span> Không thích: ${esc(x.label)}</span>`));
  if(full&&p.hidden)out.push(`<span class="qn-like unknown">❓ Còn ${p.hidden} điều chưa biết</span>`);
  return out.join('');
}

/* ------------------------------------------------------------------ 💛 thân thiết (game/goodwill.py) */
const GW_NOTE='gw1';
let gwSteps=null,gwLoading=null;
function loadGuide(env){
  if(gwSteps||gwLoading)return;
  gwLoading=import('../tutorial/coach-content.js').then(m=>{gwSteps=m.default?.features?.goodwill?.steps||[];env.renderSheet?.(false);}).catch(()=>{gwSteps=[];});
}
/** The first-time card: a few words on why being close matters, "Tiếp" between them, remembered in notesSeen. */
function guideCard(env,d){
  const {ui,api}=env;
  if(!d.gw?.on||ui.gwGuideDone||notesSeen(api).has(GW_NOTE))return '';
  if(!gwSteps){loadGuide(env);return '';}
  if(!gwSteps.length)return '';
  const i=Math.min(ui.gwStep|0,gwSteps.length-1),st=gwSteps[i],last=i===gwSteps.length-1;
  return `<section class="qn-guide" aria-label="Thân thiết với mọi người"><div class="qn-guide-top"><b>🧭 Thân thiết với mọi người</b><small class="muted">${i+1}/${gwSteps.length}</small></div>
    <p><span aria-hidden="true">${esc(st.e)}</span> <span>${esc(st.t)}</span></p>
    <div class="qn-in-act">${btn('Bỏ qua','gwGuide',{go:'end'},'ghost small')}${btn(last?'Xong 🎉':'Tiếp','gwGuide',{go:last?'end':'next'},'primary small')}</div></section>`;
}
/** Today's việc nhờ, birthdays, a referral on its way, the street titles. */
function gwToday(d){
  const g=d.gw;if(!g?.on)return '';
  const rows=[];
  if(g.errand){
    const e=g.errand;
    rows.push(`<li class="qn-in errand${e.done?' done':''}"><p>📝 ${esc(e.text)}</p><div class="qn-in-act"><span class="tag">${e.emoji} ${esc(e.what)}</span>${e.done?'<span class="muted small">✅ Đã giúp xong</span>':btn(`🎁 Mang tới ${esc(e.who_name)}`,'qnErrand',{who:e.who},'primary small')}</div></li>`);
  }
  if(g.bdays?.length)rows.push(`<li class="qn-in bday"><p>🎂 Hôm nay sinh nhật ${g.bdays.map(n=>`<b>${esc(n)}</b>`).join(', ')}. Tặng quà hôm nay được quý gấp đôi.</p></li>`);
  if(g.ref)rows.push(`<li class="qn-in ref"><p>🤝 ${fmt(g.ref.n)} khách sộp sắp ghé ${esc(g.ref.place)}${g.ref.by?` (${esc(g.ref.by)} giới thiệu)`:''}: mỗi khách trả thêm ${fmt(g.ref.pct)}%.</p></li>`);
  const titles=g.titles?.length?`<div class="qn-titles">${g.titles.map(t=>`<span class="qn-title"><span aria-hidden="true">${t.emoji}</span> ${esc(t.name)}</span>`).join('')}</div>`:'';
  if(!rows.length&&!titles)return '';
  return `<section class="qn-sec" aria-label="Thân thiết hôm nay"><h3>💛 Thân thiết hôm nay</h3>${titles}${rows.length?`<ul class="qn-inbox">${rows.join('')}</ul>`:''}</section>`;
}
/** Small marks on a row: what this person adds to your pay, a birthday, a favour ready, today's request. */
function gwMarks(d,p){
  const g=p.gw;if(!d.gw?.on||!g)return '';
  const out=[];
  if(g.pct>0)out.push(`<span class="qn-perk" title="Phục vụ xong trả thêm ${g.pct}%">💼 +${g.pct}%</span>`);
  if(g.bday_today)out.push('<span aria-label="Hôm nay sinh nhật">🎂</span>');
  if(g.fav&&!g.fav.left)out.push(`<span aria-label="Có việc muốn giúp bạn">${g.fav.emoji}</span>`);
  if(d.gw.errand&&!d.gw.errand.done&&d.gw.errand.who===p.id)out.push('<span aria-label="Đang nhờ bạn một việc">📝</span>');
  return out.join(' ');
}
/** The perk ladder of one person: what is open, what comes next, and 🔒 ??? for what nobody has told you yet. */
function perkSec(d,p){
  const g=d.gw;if(!g?.on||!p.gw)return '';
  const rows=p.cast?[...g.common.filter(r=>r.id==='likes'),...(p.gw.ladder||[])]:g.common;
  const tname=t=>d.tiers[t-1]?.name||'';
  const li=r=>{
    const secret=r.name==='???',on=!secret&&(r.open!=null?r.open:p.tier>=r.tier);
    return `<li class="qn-perk-row${on?' on':''}${secret?' secret':''}"><span class="qn-perk-ico" aria-hidden="true">${r.emoji}</span><span class="grow"><b>${esc(r.name)}</b>${r.words?`<small>${esc(r.words)}</small>`:''}</span><span class="qn-tier t${on?r.tier:1}">${on?'✓ Đã có':secret&&p.tier>=r.tier?'🤫 Còn bí mật':`Từ ${esc(tname(r.tier))}`}</span></li>`;
  };
  const lines=[];
  if(!p.cast&&p.tier>=3)lines.push(`💼 Đang trả thêm <b>${fmt(p.gw.pct)}%</b> mỗi lần bạn phục vụ xong.`);
  if(!p.cast&&p.tier>=3)lines.push(p.gw.keep?'💬 Tuần này đã hỏi thăm: đã tính thêm 2%.':'💬 Hỏi thăm hoặc tặng quà trong tuần để được thêm 2%.');
  if(p.id==='ba_tam'&&g.rent_pct)lines.push(`🏠 Tiền phòng đang được bớt <b>${fmt(g.rent_pct)}%</b> (khi còn ở gác nhà bà).`);
  if(p.id==='co_ba'&&g.shop_pct)lines.push(`🛒 Quà mua ngoài phố đang rẻ hơn <b>${fmt(g.shop_pct)}%</b>.`);
  lines.push(p.gw.bday?`🎂 Sinh nhật: <b>${esc(p.gw.bday)}</b>${p.gw.bday_today?' · hôm nay!':''}`:'🎂 Sinh nhật: ??? (thân hơn mới biết)');
  return `<section class="qn-sec" aria-label="Thân thiết được gì"><h3>💛 Thân thiết được gì</h3>${lines.map(x=>`<p class="small">${x}</p>`).join('')}<ul class="qn-perks">${rows.map(li).join('')}</ul></section>`;
}
function favBtn(p){
  const f=p.gw?.fav;if(!f)return '';
  return f.left?`<p class="small muted qn-note">${esc(f.label)}: ${fmt(f.left)} ngày nữa.</p>`:`<div class="qn-fav">${btn(esc(f.label),'qnFavour',{who:p.id},'secondary big')}</div>`;
}

/** "💛 Thân thiết · 64/100" for chat headers and reviews (an alias of a cast member reads the cast). */
export function tierLabel(api,id){
  const d=dataOf(api);if(!d)return '';
  const p=personOf(api,(d.alias||{})[id]||id);
  return p?`${p.tier_emoji} ${esc(p.tier_name)} · ${p.score}/100`:'🙂 Người lạ';
}

/* ------------------------------------------------------------------ inbox */
function inboxRow(r){
  const who=`<b>${esc(r.who_name)}</b>`;
  if(r.kind==='invite'){
    if(r.state!=='new')return '';
    // Hạn trả lời on the one day counter: an invite is open until the end of its `until` day.
    const left=(r.until??r.day)-(r.today??r.day),due=`Trả lời trước khi hết Ngày ${r.until??r.day}${left<=0?' (hôm nay)':left===1?' (ngày mai)':` (còn ${left} ngày)`}.`;
    return `<li class="qn-in invite"><p>${who} · ${esc(r.text)}</p><p class="small muted">📅 ${due}</p><div class="qn-in-act">${btn(`🎉 Đi dự · ${fmt(r.cost)} xu`,'qnInvite',{id:r.id,choice:'go'},'primary')}${btn('💌 Gửi lời chúc','qnInvite',{id:r.id,choice:'wish'},'ghost')}</div></li>`;
  }
  if(r.kind==='gift'||r.kind==='envelope'){
    const what=r.kind==='envelope'?`🧧 +${fmt(r.amount)} xu`:r.item_view?`${r.item_view.emoji} ${esc(r.item_view.name)}`:'';
    return `<li class="qn-in gift${r.state==='new'?'':' done'}"><p>${esc(r.text)}</p><div class="qn-in-act"><span class="tag green">${what}</span>${r.state==='new'?btn('🙏 Cảm ơn','qnThank',{id:r.id},'primary small'):'<span class="muted small">Đã nhận</span>'}</div></li>`;
  }
  return `<li class="qn-in ${r.kind}"><p>${r.kind==='warn'?'⚠️ ':''}${esc(r.text)}</p></li>`;
}
function inbox(d){
  const cost=d.invite_cost;
  const rows=d.inbox.filter(r=>r.state==='new'||d.day-r.day<=1).slice(0,5).map(r=>inboxRow({...r,cost,today:d.day})).filter(Boolean);
  if(!rows.length)return '';
  return `<section class="qn-sec" aria-label="Lời nhắn và quà"><h3>💌 Lời nhắn và quà${d.pending?` <em class="badge">${d.pending}</em>`:''}</h3><ul class="qn-inbox">${rows.join('')}</ul></section>`;
}

/* ------------------------------------------------------------------ list */
function row(api,p,d){
  const today=[p.talked?'💬':'',p.gifted?'🎁':''].filter(Boolean).join(' ');
  const marks=gwMarks(d,p);
  return `<li><button type="button" class="qn-row" data-action="qnOpen" data-who="${esc(p.id)}">${face(api,p,48)}
    <span class="qn-row-main"><span class="qn-row-top"><b>${esc(p.name)}</b>${chip(p)}</span>
    <small class="muted">${esc(p.role)}${p.cast?'':` · ${esc(p.place)}`}</small>${bar(p)}
    <span class="qn-row-foot">${p.likes.length?`<span class="qn-likes" aria-label="Thích: ${esc(p.likes.map(x=>x.label).join(', '))}">${likes(p)}</span>`:'<span class="muted small">Chưa rõ sở thích</span>'}${marks||today?`<span class="qn-today">${marks}${today?` <span aria-label="Hôm nay đã hỏi thăm">${today}</span>`:''}</span>`:''}</span></span>
    ${icon('chevron',16)}</button></li>`;
}
function bagSec(d){
  if(!d.bag.length)return '';
  return `<section class="qn-sec" aria-label="Túi quà"><h3>🎒 Túi quà</h3><p class="muted small">Quà người quen tặng. Tặng lại ai đó, hoặc tự thưởng cho mình.</p><ul class="qn-bag">${d.bag.map(b=>`<li><span aria-hidden="true">${b.emoji}</span><span class="grow">${esc(b.name)} <small class="muted">×${b.qty}</small></span>${btn('Dùng','qnUse',{item:b.id},'ghost small')}</li>`).join('')}</ul></section>`;
}
const HOW=`<ul class="qn-how">
  <li>💬 Trò chuyện lần đầu trong ngày: +1 tới +3. Nói nặng lời: −3.</li>
  <li>🎁 Tặng quà (mỗi người một món mỗi ngày): đúng món họ thích +6, món thường +3, món họ không ưa −2.</li>
  <li>🙏 Cảm ơn khi được tặng: +2. Để quá hai ngày không cảm ơn: −1.</li>
  <li>🎉 Được mời mà tới dự: +5, gửi lời chúc: +1, im lặng: −3.</li>
  <li>⭐ Phục vụ khách quen: 5★ +2, 3★ −1, 2★ −3, 1★ −5. Thối thiếu tiền: −3.</li>
  <li>🍃 Lâu không gặp (hơn 14 ngày) thì nhạt dần, rất chậm.</li>
  <li>💛 Càng thân, người ta càng hay hỏi thăm, tặng quà, báo tin trước, dễ bỏ qua lỗi nhỏ, hay bo thêm và tới dự ngày vui của bạn.</li></ul>`;
const HOW_GW=`<ul class="qn-how">
  <li>💼 Khách từ Người quen trở lên: phục vụ xong họ trả thêm 2%, Thân thiết 4%, Như người nhà 6%. Hỏi thăm trong tuần: thêm 2%.</li>
  <li>🏘️ Hàng xóm thân: bớt tiền phòng, bớt giá quà, mỗi tuần giúp bạn một việc.</li>
  <li>📝 Giúp người ta việc nhờ trong ngày: +3. 🎂 Tặng quà đúng ngày sinh nhật: điểm nhân đôi.</li>
  <li>🔒 Có những điều chỉ người thân mới được biết.</li></ul>`;

function listView(env,d){
  const {ui}=env,tab=ui.qnTab==='work'?'work':'home';
  const home=d.people.filter(p=>p.cast),work=d.people.filter(p=>!p.cast);
  const shown=tab==='home'?home:work;
  const tabBtn=(id,label,n)=>`<button type="button" role="tab" aria-selected="${tab===id}" class="${tab===id?'active':''}" data-action="qnTab" data-tab="${id}">${label} <small>${n}</small></button>`;
  const list=shown.length?`<ul class="qn-list">${shown.map(p=>row(env.api,p,d)).join('')}</ul>`
    :`<div class="empty">${icon('people',30)}<h3>Chưa có khách quen</h3><p class="muted small">Làm việc cho ai đó vài lần là họ nhớ mặt bạn.</p></div>`;
  return `<div class="sheet-body qn">${guideCard(env,d)}${gwToday(d)}${inbox(d)}
    <div class="segmented qn-tabs" role="tablist" aria-label="Nhóm người quen">${tabBtn('home','🏘️ Hàng xóm',home.length)}${tabBtn('work','🛍️ Khách quen',work.length)}</div>
    ${list}${bagSec(d)}
    <details class="qn-fold"><summary>Điểm thân quen tính thế nào?</summary><div class="qn-tiers">${d.tiers.map(t=>`<span class="qn-tier t${t.tier}">${t.emoji} ${esc(t.name)} <small>từ ${t.low}</small></span>`).join('')}</div>${HOW}${d.gw?.on?HOW_GW:''}</details></div>`;
}

/* ------------------------------------------------------------------ profile */
function giftPicker(env,d,p){
  if(p.gifted)return `<p class="notice">${icon('check',16)} Hôm nay đã tặng ${esc(p.name)} rồi. Mai hãy tặng tiếp nhé.</p>`;
  const kidNo=['beer','coffee','betel','cash'];
  const errand=d.gw?.errand&&!d.gw.errand.done&&d.gw.errand.who===p.id?d.gw.errand:null;
  const item=g=>{
    const kid=p.kid&&g.tags.some(t=>kidNo.includes(t));
    const poor=g.src!=='bag'&&(!d.fund_ok||g.price>d.fund);
    const off=kid||poor;
    const want=errand&&g.tags.includes(errand.tag)?' · 📝 đúng việc nhờ':'';
    const was=g.was&&g.was!==g.price?`<s>${fmt(g.was)}</s> `:'';
    const cost=(g.src==='bag'?`Trong túi ×${g.qty}`:g.src==='stall'?`${fmt(g.price)} xu · của tiệm mình`:`${was}${fmt(g.price)} xu${g.secret?' · 🤫 hàng riêng cô Ba':''}`)+want;
    return `<li><button type="button" class="qn-gift" data-action="qnGift" data-who="${esc(p.id)}" data-gift="${esc(g.id)}" data-src="${g.src}"${off?' disabled':''}><span class="qn-gift-emoji" aria-hidden="true">${g.emoji}</span><span class="grow"><b>${esc(g.name)}</b><small>${kid?'Không hợp với trẻ nhỏ':cost}</small></span></button></li>`;
  };
  const gifts=[...d.bag,...d.gifts];
  return `<section class="qn-sec qn-picker" aria-label="Chọn quà"><h3>🎁 Chọn một món quà</h3><p class="muted small">${d.fund_ok?`Tiền mua quà lấy từ quỹ nơi bạn đang làm (còn ${fmt(d.fund)} xu).`:'Mở một nơi làm việc để có tiền mua quà. Quà trong túi thì tặng được ngay.'}</p><ul class="qn-gifts">${gifts.map(item).join('')}</ul></section>`;
}
function profileView(env,d,p){
  const {ui,api}=env,line=ui.qnLine?.[p.id];
  const next=p.next==null?'Thân như người nhà rồi.':`Còn ${p.next-p.score} điểm nữa tới “${esc(d.tiers[p.tier].name)}”.`;
  const here=!p.cast&&p.career&&p.career===api.state.current;
  const talk=here?btn('💬 Trò chuyện','chat',{npc:p.id},'primary big'):btn(p.cast?'💬 Trò chuyện':'💬 Nhắn hỏi thăm','qnChat',{who:p.id},'primary big');
  const hist=p.history.length?`<ul class="qn-hist">${p.history.map(h=>`<li><span class="qn-d ${h.d>0?'up':h.d<0?'down':''}">${h.d?signed(h.d):'🎁'}</span><span class="grow">${esc(h.text)}</span><small class="muted">Ngày ${fmt(h.day)}</small></li>`).join('')}</ul>`:'<p class="muted small">Chưa có kỷ niệm nào. Hỏi thăm một câu là bắt đầu.</p>';
  return `<div class="sheet-body qn qn-profile">
    ${btn(icon('chevron',15)+' Tất cả người quen','qnBack',{},'ghost small qn-back')}
    <article class="qn-card">${face(api,p,84)}<div class="qn-card-main"><h3>${esc(p.name)}</h3><p class="muted">${esc(p.role)}${p.cast?'':` · ${esc(p.place)}`}</p>
      <div class="qn-card-tier">${chip(p)}<span class="qn-score">${p.score}<small>/100</small></span></div>${bar(p)}<p class="small muted">${next}</p></div></article>
    ${line?`<div class="qn-say"><span aria-hidden="true">${p.cast?esc(p.emoji):'💬'}</span><p>${line.q?`“${esc(line.t)}”`:esc(line.t)}</p></div>`:''}
    <div class="qn-actions">${talk}${btn(`🎁 Tặng quà`,'qnPick',{who:p.id},`${ui.qnPick===p.id?'secondary':'ghost'} big`,` aria-expanded="${ui.qnPick===p.id}"`)}</div>
    ${p.talked?'<p class="small muted qn-note">💬 Hôm nay đã hỏi thăm rồi.</p>':''}
    ${favBtn(p)}
    ${d.gw?.errand&&!d.gw.errand.done&&d.gw.errand.who===p.id?`<p class="notice qn-errand-note">📝 ${esc(d.gw.errand.text)}</p>`:''}
    ${ui.qnPick===p.id?giftPicker(env,d,p):''}
    ${p.gw?.story?`<section class="qn-sec qn-story" aria-label="Chuyện riêng"><h3>📖 Chuyện riêng</h3><p>${esc(p.gw.story)}</p></section>`:''}
    ${perkSec(d,p)}
    <section class="qn-sec" aria-label="Sở thích"><h3>💡 Sở thích</h3><div class="qn-likes full">${likes(p,true)||'<span class="muted small">Chưa biết gì. Thân hơn hoặc tặng thử một món là biết.</span>'}</div></section>
    <section class="qn-sec" aria-label="Gần đây"><h3>🗓️ Gần đây</h3>${hist}</section></div>`;
}

export function closenessView(env){
  const {api,ui}=env;ensureCss();
  const d=dataOf(api);
  const head=(sub)=>`<header class="sheet-head"><div class="grow"><span class="eyebrow">KHU PHỐ</span><h2>👥 Người quen</h2><p>${sub}</p></div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  if(!d)return head('Đang tải…')+`<div class="sheet-body"><p class="muted">Chưa có dữ liệu người quen.</p></div>`;
  const p=ui.qnWho&&personOf(api,ui.qnWho);
  if(d.gw?.fresh&&!(ui.gwSeenAt>Date.now()-15000)){ui.gwSeenAt=Date.now();setTimeout(()=>env.cmd?.('qn_gw_seen',{},{quiet:true}),0);}
  if(p)return head('Càng thân, người ta càng thương mình.')+profileView(env,d,p);
  return head('Càng thân, hàng xóm càng hay hỏi thăm, tặng quà và tới dự ngày vui của bạn.')+listView(env,d);
}
/** Badge for the menu: gifts to thank and invites to answer. */
export function closenessBadge(api){const d=dataOf(api);return (d?.pending||0)+(d?.gw?.fresh||0);}

export async function closenessAction(action,data,el,env){
  const {ui,cmd,renderSheet}=env;
  switch(action){
    case'qnOpen':ui.qnWho=data.who;ui.qnPick=null;renderSheet(false);return true;
    case'qnBack':ui.qnWho=null;ui.qnPick=null;renderSheet(false);return true;
    case'qnTab':ui.qnTab=data.tab==='work'?'work':'home';renderSheet();return true;
    case'qnPick':ui.qnPick=ui.qnPick===data.who?null:data.who;renderSheet();return true;
    case'qnChat':{const r=await cmd('qn_chat',{who:data.who},{quiet:true});if(r){(ui.qnLine??={})[data.who]={t:r.line,q:true};renderSheet();}return true;}
    case'qnGift':{const r=await cmd('qn_gift',{who:data.who,gift:data.gift,src:data.src});if(r){ui.qnPick=null;(ui.qnLine??={})[data.who]={t:r.message,q:false};renderSheet();}return true;}
    case'qnThank':await cmd('qn_thank',{id:data.id});renderSheet();return true;
    case'qnInvite':await cmd('qn_invite',{id:data.id,choice:data.choice});renderSheet();return true;
    case'qnUse':await cmd('qn_use',{item:data.item});renderSheet();return true;
    case'qnFavour':{const r=await cmd('qn_favour',{who:data.who});if(r){(ui.qnLine??={})[data.who]={t:r.message,q:false};renderSheet();}return true;}
    case'qnErrand':ui.qnWho=data.who;ui.qnPick=data.who;renderSheet(false);return true;
    case'gwGuide':if(data.go==='next'){ui.gwStep=(ui.gwStep|0)+1;}else{ui.gwGuideDone=true;markNoteSeen(env,GW_NOTE);}renderSheet(false);return true;
  }
  return false;
}
