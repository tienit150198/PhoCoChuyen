/** Original warm counter UI. No reference website code/assets are reused. */
import {icon,portrait,itemArt,escapeHTML as esc} from './icons.js';
import {skeleton} from './lazy.js';
import {lowItems,restockBar} from './v4/restock.js';
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const b=(label,action,payload={},cls='')=>`<button type="button" class="btn ${cls}" data-action="${action}" ${Object.entries(payload).map(([k,v])=>`data-${k}="${esc(v)}"`).join(' ')}>${label}</button>`;
const doB=(label,op,payload={},cls='',confirm='')=>b(label,'expDo',{op,payload:JSON.stringify(payload),confirm},cls);
const note=(s,cls='')=>`<div class="life-note ${cls}">${s}</div>`;
const em=(s,cls='')=>`<span class="em ${cls}" aria-hidden="true">${s}</span>`;
/* Tiết học / Chuyến đi (v4/teach-tour.js, ~60 KB + teach.css) load only for a teacher or a tour guide:
 * app.js imports it with those careers' assets; until it is in, the workbench shows a skeleton. */
let TT=null,ttLoad=null;
export function teachTour(){
 ttLoad??=import('./v4/teach-tour.js').then(m=>{TT=m;document.dispatchEvent(new CustomEvent('mnl:lazy'));return m;},e=>{ttLoad=null;throw e;});
 return ttLoad;
}
const tt=()=>{if(!TT)teachTour().catch(e=>console.warn('teach-tour:',e));return TT;};
export function nextStep(t){
 const v2=(t?.room||t?.trip)?tt()?.v2Stage(t):null;if(v2)return v2;
 const maps={teacher:{plan:'Soạn nhịp tiết học',attendance:'Điểm danh theo ghế',teach:'Giúp từng bạn hiểu bài',grade:'Phản hồi phiếu cuối tiết',ready:'Khép tiết & lưu tiến bộ'},tour_guide:{plan:'Chọn lộ trình hợp đoàn',gather:'Kiểm người & khởi hành',stop:'Kể chuyện · chụp ảnh · kiểm đoàn',ready:'Gửi bưu thiếp & khép chuyến'},milk_tea:{order:'Chọn trà, topping và chỉnh vị'}};
 return maps[t?.career]?.[t.stage]||'Một công việc nhỏ đang chờ';
}
/* ------------------------------------------------------------ life sheets
 * Chuẩn bị · Bảng giá · Trò nhỏ · Hộ chiếu · Khu phố share one shell: a sticky
 * top (back, shop name, close) with the tab bar, then cards (styles: css/lifesheets.css). */
const TABS=[['prepare','🧺','Chuẩn bị'],['prices','🏷️','Bảng giá'],['workshop','🧩','Trò nhỏ'],['passport','🌟','Hộ chiếu'],['town','🗺️','Khu phố'],['phone','💬','Chuyện phố']];
const KIND_EM={sort:'🧺',pairs:'🃏',sequence:'🔢',match:'🔗'};
const tile=(s,cls='')=>`<span class="lx-tile ${cls}" aria-hidden="true">${s}</span>`;
const h3=s=>`<h3 class="lx-h">${s}</h3>`;
export function lifeNav(view){return `<nav class="lx-nav" aria-label="Các góc trải nghiệm">${TABS.map(([id,emoji,label])=>`<button type="button" class="lx-tab${view===id?' active':''}" data-action="${id}"${view===id?' aria-current="page"':''}>${em(emoji)}<span>${label}</span></button>`).join('')}</nav>`;}
export function guestRibbon(t,c,content){
 const person=content.npcs.find(n=>n.id===t.npc);const patience=c.life.mode==='calm'?100:(t.patience??100);
 let words=t.opening;
 if(t.career==='milk_tea'&&t.needs){const lookup=id=>content.experiences.ingredients.find(i=>i.id===id)?.name||id,n=t.needs;words=`Cho mình ${lookup(n.base)} size ${n.size}${n.flavor?', vị '+lookup(n.flavor):''}, ${n.toppings.map(lookup).join(', ')}, ${n.sugar}% đường và ${{none:'không đá',little:'ít đá',normal:'đá bình thường'}[n.ice]} nhé!`;}
 return `<section class="guest-ribbon"><div class="guest-portrait">${portrait(person||{display_name:'Bạn'},94)}<small>${esc(person?.display_name||'Bạn')}</small></div><div class="order-bubble"><p>${esc(words)}</p><div class="patience"><span>${t.career==='teacher'?'NHỊP LỚP':t.career==='tour_guide'?'NHỊP ĐOÀN':'KIÊN NHẪN'}</span><div><i style="width:${patience}%"></i></div><small>${patience}%</small></div>${!t.known?doB('💬 Hỏi rõ yêu cầu','ask',{task:t.id},'small primary'):''}${b('Trò chuyện','chat',{npc:t.npc,task:t.id},'small ghost')}</div></section>`;
}
/** The day the player sees (life day in the story; game/days.py): set by experienceView. */
let STATE=null;
const dayNo=c=>STATE?.journey?.story&&Number.isInteger(STATE.journey.life_day)?STATE.journey.life_day:c.day;
function shell(view,c,meta,body,foot=''){
 return `<div class="lx-top"><header class="sheet-head lx-head"><button type="button" class="btn ghost small icon-btn lx-back" data-action="home" aria-label="Quay lại hành trình">${icon('back',18)}</button><div class="grow"><span class="eyebrow">Ngày ${dayNo(c)} · ${esc(meta.short||'')}</span><h2>${esc(c.life.shop_name||meta.place)}</h2></div><button type="button" class="btn ghost small icon-btn" data-action="close" aria-label="Đóng">${icon('x',20)}</button></header>${lifeNav(view)}</div><div class="life-content lx lx-${view}">${body}</div>${foot}`;
}
/** Story mode: a place that is not open yet shows a lock card instead of its sheets. */
function lockedView(cid,c,content,meta,state){
 const J=state.journey,n=(content.journey?.unlock_chapter||{})[cid],hint=n===J.chapter+1?'Sắp mở':'Còn ở phía trước';
 return `<div class="lx-top"><header class="sheet-head lx-head"><div class="grow"><span class="eyebrow">${esc(meta.short||'')}</span><h2>${esc(meta.place||'')}</h2></div><button type="button" class="btn ghost small icon-btn" data-action="close" aria-label="Đóng">${icon('x',20)}</button></header></div><div class="life-content lx"><section class="lx-card lx-locked">${tile('🔒','big')}<b>Chưa mở</b><small>${hint}${n?` · Chương ${n}`:''}</small>${b(icon('back',16)+' Hành trình','home',{},'primary')}</section></div>`;
}
// How each daily goal counts (feedback #69, 02/10): shown under the reward until it is claimed.
const GOAL_HINTS={serve:'Mở cửa rồi làm xong việc trong ca',play:'Chơi ở tab Trò nhỏ',talk:'Bấm 💬 ở một công việc, hoặc Người quen → Trò chuyện, với 2 người khác nhau (chat Cả phố không tính)'};
function goalList(c){
 if(!c.life.goals.length)return '';
 return `<ul class="lx-goals">${c.life.goals.map(g=>{const ready=g.current>=g.goal;
  return `<li class="${g.claimed?'claimed':ready?'ready':''}"><span class="lx-check" aria-hidden="true">${g.claimed||ready?icon('check',14):''}</span><div class="grow"><b>${esc(g.title)}</b><small>Thưởng ${g.reward} xu · +10 XP</small>${!g.claimed&&!ready&&GOAL_HINTS[g.id]?`<small class="lx-goal-hint">${GOAL_HINTS[g.id]}</small>`:''}</div><div class="lx-goal-end">${g.claimed?'<span class="done-mark">✓ Đã nhận</span>':ready?doB('Nhận quà','life_goal',{goal:g.id},'small primary'):`<b>${Math.min(g.current,g.goal)}/${g.goal}</b>`}</div></li>`;}).join('')}</ul>`;
}
function goalCard(c){return c.life.goals.length?`<section class="lx-card">${h3('🌞 Nhiệm vụ hôm nay')}${goalList(c)}<p class="lx-goal-note">Đóng ca là tính lại từ đầu, nhớ bấm Nhận quà trước khi đóng ca.</p></section>`:'';}
/** The few working steps of a career without a price list. */
function craftSteps(cid){
 return cid==='teacher'?['🌱 Lớp học Mầm Nắng',['🖼️ Ví dụ','🧩 Luyện tập','💡 Cùng hiểu']]:cid==='pharmacy'?['🧰 Cẩn thận từng chút',['📋 Nhận phiếu','🔎 Đọc mã lô','🧰 Kiểm khay','🤝 Bàn giao']]:cid==='accounting'?['📒 Mỗi số có một nguồn',['📂 Mở nguồn','🧩 Ghép phiếu','🔎 Tìm sai lệch','📒 Giải thích']]:cid==='customer_care'?['🎧 Nghe thật, làm tới nơi',['💬 Lắng nghe','🔎 Kiểm chứng','🤝 Phối hợp','✅ Theo dõi']]:['',[]];
}
function ingredientArt(ing){
 const bottle=ing.group==='flavor';return `<svg class="ingredient-art" viewBox="0 0 90 108" aria-hidden="true"><ellipse cx="45" cy="101" rx="32" ry="5" fill="#c6ab8540"/>${bottle?`<path d="M29 27V14H60V27L65 42V93Q65 98 59 98H29Q23 98 23 92V42Z" fill="#fffcf2" stroke="#74563f" stroke-width="2.4"/><rect x="28" y="61" width="33" height="31" rx="3" fill="${ing.color}"/><path d="M31 17V8H58M43 8V2H73V7H50" fill="none" stroke="#655348" stroke-width="5" stroke-linecap="round"/>`:`<path d="M15 27H75L72 94Q72 99 64 99H25Q18 99 18 92Z" fill="${ing.color}" stroke="#806046" stroke-width="2.4"/><rect x="11" y="21" width="68" height="12" rx="6" fill="#efe1c2" stroke="#806046" stroke-width="2.4"/><path d="M25 21V17Q45 5 65 17V21" fill="#e7d4b3" stroke="#806046" stroke-width="2.4"/>`}<rect x="24" y="44" width="43" height="35" rx="8" fill="#fff5dd" stroke="#baa07c" stroke-width="1.4"/><text x="45" y="68" text-anchor="middle" font-size="22">${ing.emoji}</text></svg>`;
}
function prepView(cid,c,content,meta){
 const ingredients=content.experiences.ingredients,w=c.life.weather||{},mode=c.life.mode!=='normal'?(content.experiences.modes.find(m=>m.id===c.life.mode)||{}):null;
 const xp=Math.max(0,Math.min(100,Math.round((c.xp_in_level||0)/90*100)));
 const level=`<section class="lx-card lx-level"><div class="grow"><div class="lx-level-row"><b>🌟 Cấp ${c.level}</b><small>${c.xp_in_level}/90 XP</small></div><div class="lx-bar" role="progressbar" aria-label="Kinh nghiệm" aria-valuemin="0" aria-valuemax="90" aria-valuenow="${c.xp_in_level||0}"><i style="width:${xp}%"></i></div></div>${b('✏️ Đổi tên','expRename',{},'small ghost')}</section>`;
 const today=`<section class="lx-card lx-today">${h3('Hôm nay')}<div class="lx-weather">${tile(w.emoji||'🌤️','big')}<div class="grow"><b>${esc(w.name||'')}</b>${mode?` <span class="tag ${c.life.mode==='festival'?'amber':'blue'}">${c.life.mode==='festival'?'🎏':'☁️'} ${esc(mode.name||'')}</span>`:''}<p>${esc(w.description||'')}</p><small>Dự kiến ${c.life.forecast} lượt đầu ca · có thể nhận thêm</small></div></div></section>`;
 let stock;
 if(cid==='milk_tea')stock=`<section class="lx-card lx-wide">${h3('🧺 Chuẩn bị từng mẻ nhỏ')}<div class="prep-ingredients">${ingredients.map(i=>{const lots=c.life.pantry.filter(l=>l.item===i.id&&l.qty>0&&l.expires>=c.day),exp=Math.min(...lots.map(l=>l.expires));return `<article>${ingredientArt(i)}<div><strong>${i.name}</strong><small>${i.cost} xu/phần · giữ ${i.life} ngày</small><span class="tag ${exp===c.day?'amber':'green'}">Còn ${c.life.stock[i.id]} ${lots.length?'· hết ngày '+exp:''}</span></div>${doB('+5','tea_prepare',{item:i.id,qty:5,confirm:true},'primary small',`Chuẩn bị 5 phần ${i.name}: ${i.cost*5} xu.`)}</article>`;}).join('')}</div></section>`;
 else {const link=(e,label,action)=>b(tile(e)+`<span class="grow">${label}</span>`+icon('chevron',16),action,{},'lx-link');
  stock=`<section class="lx-card">${h3('Trước giờ mở cửa')}<div class="lx-links">${link('🧺',cid==='mother_baby'||cid==='pharmacy'?'Kiểm kho & nhập hàng':'Xem công việc được giữ','warehouse')}${link('👥','Xếp ca nhân viên','staff')}${link('🪴','Trang trí góc của mình','decor')}${link('💌','Đọc chuyện đang chờ','passport')}</div></section>`;}
 const grid=`<div class="lx-grid">${today}${goalCard(c)}</div>${stock}`;
 // Stocked shops: one line before opening when shelves are empty or low, with the way to restock.
 const short=cid!=='milk_tea'&&c.inventory?restockBar(c,lowItems(c,content,cid),{urgent:false}):'';
 return shell('prepare',c,meta,(short?`<section class="lx-card lx-restock">${short}</section>`:'')+level+grid,`<footer class="life-sticky">${b(c.open?'Về quầy · tiếp tục chơi':'Mở cửa ngày '+dayNo(c),c.open?'close':'start',{},'primary jumbo')}</footer>`);
}
/** life_price's trial band (game/experiences.py): round(base×75%)–round(base×125%), Python rounding (half to even). */
const pyRound=v=>{const f=Math.floor(v),d=v-f;return d>0.5||(d===0.5&&f%2)?f+1:f;};
const band=base=>[pyRound(base*.75),pyRound(base*1.25)];
function priceRow(i,value,lo,hi,open,art=''){
 // The band sits under the name, and "Lưu giá" waits for the shop to close like the input (life_price refuses both).
 return `<li class="lx-price">${art||tile(i.emoji||'🏷️')}<label class="grow" for="price-${i.id}">${esc(i.name)}<small class="lx-band">Giá ${lo}–${hi} xu</small></label><span class="lx-price-in"><input class="input" type="number" inputmode="numeric" id="price-${i.id}" min="${lo}" max="${hi}" value="${value}" data-preserve aria-label="Giá ${esc(i.name)}, từ ${lo} đến ${hi} xu" ${open?'disabled':''}><small>xu</small></span>${b('Lưu giá','expPrice',{item:i.id},'small').replace('<button ',open?'<button disabled ':'<button ')}</li>`;
}
function priceView(cid,c,content,meta){
 const ing=content.experiences.ingredients,fixed=(list,add)=>`<ul class="lx-rows">${list.map(i=>`<li>${tile(i.emoji||'•')}<span class="grow">${esc(i.name)}</span><b>${add}</b></li>`).join('')}</ul>`;
 let body;
 if(cid==='milk_tea'){
  const bases=ing.filter(x=>x.group==='base').map(i=>({...i,price:{milk:30,black:25,matcha:35}[i.id]||30}));
  body=`<section class="lx-card">${h3('🧋 Menu hôm nay')}<p class="lx-hint">Đổi giá trong khoảng 75%–125% giá gốc trước khi mở ca${c.open?' (đang mở ca: đóng ca rồi đổi)':''}.</p><ul class="lx-prices">${bases.map(i=>priceRow(i,c.life.prices[i.id]||i.price,...band(i.price),c.open)).join('')}</ul></section>
   <div class="lx-grid"><section class="lx-card">${h3('Hương vị')}${fixed(ing.filter(i=>i.group==='flavor'),'+6 xu')}</section><section class="lx-card">${h3('Topping')}${fixed(ing.filter(i=>i.group==='topping'),'+5 xu')}<p class="lx-hint">Size L +7 xu · 0 / 30 / 50 / 100% đường</p></section></div>`;
 }else if(cid==='mother_baby'){
  body=`<section class="lx-card">${h3('🎁 Những món nhỏ xinh')}<p class="lx-hint">Đổi giá trong khoảng 75%–125% giá gốc trước khi mở ca${c.open?' (đang mở ca: đóng ca rồi đổi)':''}.</p><ul class="lx-prices">${content.products.map(i=>priceRow(i,c.life.prices[i.id]||i.price,...band(i.price),c.open,`<span class="lx-tile art" aria-hidden="true">${itemArt(i.icon,40,i.color)}</span>`)).join('')}</ul></section>`;
 }else if(cid==='tour_guide'){
  body=`<section class="lx-card">${h3('🧭 Chuyến đi hôm nay')}<ul class="lx-rows">${content.experiences.places.filter(i=>i.id!=='gate').map(p=>`<li>${tile(p.emoji)}<span class="grow">${esc(p.name)}</span><small>${p.minutes}′</small><b>${p.fee} xu</b></li>`).join('')}</ul><p class="lx-hint">Nghề này nhận thù lao theo công việc.</p></section>`;
 }else{
  const [title,steps]=craftSteps(cid);
  body=`<section class="lx-card lx-empty">${tile('🏷️','big')}<p>${c.inventory?'Giá tính ngay trong từng việc.':'Nghề này nhận thù lao theo công việc.'}</p>${c.inventory?b(icon('box',16)+' Kho','inventory',{},'ghost'):''}</section>${title?`<section class="lx-card">${h3(title)}<ol class="lx-steps">${steps.map(s=>`<li>${s}</li>`).join('')}</ol></section>`:''}`;
 }
 return shell('prices',c,meta,body);
}
function activityBoard(a,spec,ui){
 let inner='';
 if(a.status==='completed')inner=`<div class="mini-result lx-result">${em('🎉')}<h2>Một lượt thật vui!</h2><p>${a.score} điểm cá nhân · ${a.reward?'+ '+a.reward+' xu':'Lượt luyện tập / đã nhận quà hôm nay'}</p><small>${a.moves} thao tác · ${a.mistakes} lần thử chưa khớp</small>${b('Lưu kỷ niệm vào hộ chiếu','passport',{},'primary')}</div>`;
 else if(a.kind==='pairs')inner=`<p class="lx-hint">Lật hai thẻ để tìm cặp.</p><div class="memory-grid">${a.cards.map(v=>doB(v.value?esc(v.value):'✦','life_activity_flip',{card:v.id},`memory-card ${v.value?'flipped':''} ${a.matched.includes(v.id)?'matched':''}`)).join('')}</div>`;
 else if(a.kind==='sequence')inner=`<div class="sequence-tray">${a.sequence.length?a.sequence.map((id,i)=>`<span><b>${i+1}</b> ${esc(a.cards.find(v=>v.id===id).label)}</span>`).join(''):'Đặt bước đầu tiên vào đây…'}</div><div class="lx-cards">${a.cards.filter(v=>!a.sequence.includes(v.id)).map(v=>doB(esc(v.label),'life_activity_step',{card:v.id},'paper-tile')).join('')}</div><div class="lx-actions">${doB('↶ Hoàn tác','life_activity_undo',{},'ghost')}${doB('Kiểm nhịp công việc','life_activity_check',{},'primary')}</div>`;
 else {const isSort=a.kind==='sort';inner=`<p class="lx-hint">Bấm một thẻ rồi chọn ${isSort?'ngăn':'nhãn tương ứng'}.</p><div class="match-layout"><div class="match-source">${a.cards.map(v=>a.assignments[v.id]?`<div class="paper-tile matched">✓ ${esc(v.label)}</div>`:`<button class="paper-tile ${ui.activityCard===v.id?'selected':''}" draggable="true" data-drag-card="${v.id}" data-action="expCard" data-card="${v.id}">${esc(v.label)}</button>`).join('')}</div><div class="match-target">${(isSort?a.bins.map(v=>({id:v,label:v})):a.right).map(v=>`<button class="match-bin" data-drop-target="${esc(v.id)}" data-action="expTarget" data-target="${esc(v.id)}"><strong>${isSort?'🧺':'🔖'} ${esc(v.label)}</strong>${v.hint?`<small>${esc(v.hint)}</small>`:''}<span>${Object.values(a.assignments).filter(t=>t===v.id).length} thẻ đã ghép</span></button>`).join('')}</div></div>`;}
 const [name]=String(spec?.title||'Trò nhỏ').split(' · ');
 return `<section class="lx-card lx-play" id="activity-board"><div class="lx-play-head">${tile(KIND_EM[a.kind]||spec?.emoji||'🧩')}<h3 class="grow">${esc(name)}</h3><span class="tag ${a.practice?'':'green'}">${a.practice?'Diễn tập':'Chơi thường'}</span></div>${inner}</section>`;
}
function workshopView(cid,c,content,meta,ui){
 const specs=content.experiences.activities.filter(a=>a.career===cid),a=c.life.activity,spec=a&&specs.find(v=>v.id===a.spec);
 const theme=String(specs[0]?.title||'').split(' · ')[1]||'';
 const cards=specs.map(sp=>{const [name]=sp.title.split(' · '),got=c.life.activity_rewards.includes(sp.id),on=a&&a.spec===sp.id&&a.status!=='completed';
  return `<article class="lx-card lx-game${on?' on':''}"><div class="lx-game-head">${tile(KIND_EM[sp.type]||sp.emoji)}<div class="grow"><h4>${esc(name)}</h4><p>${esc(sp.description)}</p></div></div><div class="lx-chips"><span class="chip">🏆 Kỷ lục riêng: ${c.life.activity_best[sp.id]||'—'}</span><span class="chip${got?' done':''}">${got?'✓ ':'🎁 '}Quà ${got?'đã nhận hôm nay':'12 xu + 10 XP'}</span></div><div class="lx-actions">${doB('Chơi ngay','life_activity_start',{spec:sp.id,replace:true},'primary small')}${doB('Luyện không thưởng','life_activity_start',{spec:sp.id,practice:true,replace:true},'ghost small')}</div></article>`;}).join('');
 return shell('workshop',c,meta,`${a?activityBoard(a,spec,ui):''}${theme?`<h3 class="lx-sec">${esc(specs[0].emoji)} ${esc(theme)}</h3>`:''}<div class="lx-games">${cards}</div>`);
}
function passportView(cid,c,content,meta){
 const stories=content.experiences.stories.filter(x=>x.career===cid),x=c.life,served=c.metrics.served||0,badges=x.badges_view||[];
 const owned=badges.filter(v=>v.claimed).length,closed=stories.filter(st=>x.chapters[st.id]?.completed).length;
 const stats=`<div class="lx-stats"><div><b>${owned}/${badges.length}</b><small>Huy hiệu</small></div><div><b>${closed}/${stories.length}</b><small>Chuyện</small></div><div><b>${x.stickers.length}</b><small>Thiệp</small></div></div>`;
 const story=st=>{const ch=x.chapters[st.id]||{step:0,completed:false},open=served>=st.goal,beat=st.beats[Math.min(2,ch.step)],wait=ch.step===1&&served<=ch.baseline;
  return `<article class="lx-card lx-story${ch.completed?' done':!open?' locked':''}"><div class="lx-story-top"><small>CHƯƠNG ${stories.indexOf(st)+1} · ${ch.step}/3 NHỊP</small>${!open&&!ch.completed?'':`<span class="lx-dots" aria-hidden="true">${[0,1,2].map(i=>`<i class="${i<ch.step||ch.completed?'on':''}"></i>`).join('')}</span>`}</div><h4>${!open&&!ch.completed?'🔒 ':''}${esc(st.title)}</h4><p>${ch.completed?'Đã lưu một kỷ niệm có nguồn vào hộ chiếu.':!open?'Mở sau '+st.goal+' công việc đã hoàn thành.':esc(beat.text)}</p>${ch.completed?'<span class="tag green">✓ Đã khép chuyện</span>':!open?'':`<div class="lx-actions">${wait?b('Làm tiếp một công việc','queue',{},'small primary'):beat.choices.map(a=>doB(esc(a.label),'life_chapter',{story:st.id,choice:a.id},'small')).join('')}</div>`}</article>`;};
 const badge=v=>{const ready=!v.claimed&&v.current>=v.goal,pct=Math.min(100,Math.round(Math.min(v.current,v.goal)/Math.max(1,v.goal)*100));
  return `<article class="lx-badge${v.claimed?' owned':ready?' ready':''}"><span class="lx-medal" aria-hidden="true">${v.emoji}</span><h4>${esc(v.title)}</h4>${v.claimed?'<small class="lx-got">✓ Đã nhận</small>':ready?doB('Nhận','life_badge',{badge:v.id},'primary small'):`<small>${Math.min(v.current,v.goal)}/${v.goal}</small>${v.current>0?`<i class="lx-mini" aria-hidden="true"><i style="width:${pct}%"></i></i>`:''}`}</article>`;};
 const stickers=x.stickers.length?`<div class="lx-postcards">${x.stickers.map(v=>`<article class="lx-postcard"><span aria-hidden="true">${v.emoji}</span><b>${esc(v.title)}</b><small>Ngày ${v.day}</small></article>`).join('')}</div>`:`<p class="lx-none">🎟️ Chưa có thiệp.</p>`;
 return shell('passport',c,meta,`${stats}${goalCard(c)}<h3 class="lx-sec">💌 Những chuyện đang viết tiếp</h3><div class="lx-stories">${stories.map(story).join('')}</div><h3 class="lx-sec">🌟 Huy hiệu của riêng mình</h3><div class="lx-badges">${badges.map(badge).join('')}</div><h3 class="lx-sec">🎟️ Hộp thiệp kỷ niệm · ${x.stickers.length}</h3>${stickers}`);
}
function townView(cid,c,content,meta,ui){
 const visit=content.experiences.town.find(p=>p.id===ui.townPlace),kind={library:'sequence',garden:'pairs',studio:'match',market:'sort'}[visit?.id],spec=content.experiences.activities.find(v=>v.career===cid&&v.type===kind);
 const visitCard=visit?`<article class="lx-card lx-visit"><div class="lx-play-head">${tile(visit.emoji)}<div class="grow"><h3>${esc(visit.name)}</h3><p>${esc(visit.description)}</p></div></div><div class="lx-actions">${spec?doB('Thử '+spec.title,'life_activity_start',{spec:spec.id,replace:true},'primary'):b('Chuẩn bị ngày hội','prepare',{},'primary')}${b(visit.id==='studio'?'Trang trí góc của mình':'Đọc lời nhắn khu phố',visit.id==='studio'?'decor':'phone',{},'ghost')}</div></article>`:'';
 const dm=c.life.day_metrics,row=(n,goal,label)=>`<li class="${n>=goal?'claimed':''}"><span class="lx-check" aria-hidden="true">${n>=goal?icon('check',14):''}</span><span class="grow">${Math.min(n,goal)}/${goal} ${label}</span></li>`;
 const fest=`<section class="lx-card lx-fest"><div class="lx-play-head">${tile('🎏')}<div class="grow"><h3>Ngày hội của khu phố</h3><p>Chuẩn bị một góc nghề của mình: làm xong 3 việc và 1 trò nhỏ trong ca Ngày hội.</p></div></div><ul class="lx-goals">${row(dm.served||0,3,'việc')}${row(dm.activities||0,1,'trò nhỏ')}</ul><div class="lx-actions">${c.life.festival&&!c.life.festival_claimed?doB('Mở góc ngày hội','life_festival',{},'primary'):c.life.festival_claimed?'<span class="tag green">✓ Đã tổ chức</span>':b('Chọn Ngày hội ở Chuẩn bị','prepare',{},'ghost')}</div></section>`;
 return shell('town',c,meta,`<div class="town-map lx-map"><div class="map-river"></div><div class="map-road"></div><span class="map-cloud cloud-one">☁️</span><span class="map-cloud cloud-two">☁️</span>${content.experiences.town.map(p=>`<button class="town-pin ${c.life.visits.includes(p.id)?'visited':''} ${ui.townPlace===p.id?'selected':''}" style="left:${p.x}%;top:${p.y}%" data-action="expVisit" data-place="${p.id}">${em(p.emoji)}<strong>${p.name}</strong><small>${c.life.visits.includes(p.id)?'✓ Đã ghé':'Chạm để ghé'}</small></button>`).join('')}</div>${visitCard}${fest}`);
}
export function experienceView(view,cid,c,content,meta,ui,state){
 STATE=state||STATE;const J=state?.journey;
 if(J?.story&&!(J.unlocked||[]).includes(cid))return lockedView(cid,c,content,meta,state);
 if(view==='prepare')return prepView(cid,c,content,meta);
 if(view==='prices')return priceView(cid,c,content,meta);
 if(view==='workshop')return workshopView(cid,c,content,meta,ui);
 if(view==='passport')return passportView(cid,c,content,meta);
 if(view==='town')return townView(cid,c,content,meta,ui);
 return '';
}
function studentCard(st,body,extra=''){return `<article class="student-card ${extra}"><div class="student-name"><span class="student-face">${['Minh','Bảo'].includes(st.name)?'👦':'👧'}</span><div><h3>${st.name}</h3><small>Học sinh</small></div></div>${body}</article>`;}
function lessonSketch(lesson){
 const drawings={
  'Cộng những điều nhỏ':'<span>⭐ ⭐ ⭐</span><b>+</b><span>⭐ ⭐ ⭐ ⭐</span>',
  'Chia đều giỏ bút':'<span>✏️ ✏️ ✏️ ✏️</span><span>✏️ ✏️ ✏️ ✏️</span><span>✏️ ✏️ ✏️ ✏️</span>',
  'Nhìn nhịp hoa văn':'<span>🌸</span><span>🌿</span><span>🌸</span><span>🌿</span><span>?</span>',
  'Đọc lời nhắn nhỏ':'<span>💌 An để sách ở kệ xanh.</span>',
  'Những chiếc lá giấy':'<span>🍃 🍃 🍃 🍃 🍃</span><b>+</b><span>🍃 🍃 🍃</span>',
  'Hình nào khác nhóm?':'<span>●</span><span>■</span><span>●</span><span>●</span>',
  'Lịch trực thư viện':'<span>Thứ hai · Minh</span><span>Thứ ba · Vy</span>',
  'Đo bằng khối gỗ':'<span>▰ ▰ ▰ ▰</span><span>▰ ▰ ▰ ▰ ▰ ▰</span>'
 };
 return `<div class="lesson-sketch" aria-label="Minh họa đúng với đề bài">${drawings[lesson.title]||''}</div>`;
}
function teacherJob(t,c,content,ui){
 const lesson=t.lesson;let body='';const present=t.students.filter(s=>s.present);
 if(t.stage==='plan'){
  ui.lessonSequence??=[];body=`<h3>Soạn ba nhịp cho tiết học</h3><p class="muted">Bắt đầu bằng ví dụ, cho lớp luyện tập, rồi kiểm xem các bạn đã hiểu gì.</p><div class="sequence-tray">${ui.lessonSequence.map((k,i)=>`<span>${i+1}. ${content.experiences.lesson_steps.find(x=>x.id===k).name}</span>`).join('')||'Chọn bước đầu tiên…'}</div><div class="tile-grid">${content.experiences.lesson_steps.filter(v=>!ui.lessonSequence.includes(v.id)).map(v=>b(em(v.emoji)+v.name,'lessonStep',{step:v.id},'paper-tile')).join('')}</div><div class="row wrap space-top">${b('↶ Soạn lại','lessonReset',{},'ghost')}${b('Chốt giáo án → Điểm danh','lessonPlan',{task:t.id},'primary')}</div>`;
 }else if(t.stage==='attendance')body=`<h3>Ai đang có mặt trong lớp?</h3><div class="student-grid">${t.students.map(st=>studentCard(st,`<p>${st.present?'🪑 Đang ngồi ở ghế':'✉️ Có thông báo nghỉ'}</p>${st.id in t.attendance?'<span class="tag green">✓ Đã ghi nhận</span>':`<div class="row wrap">${doB('Có mặt','lesson_attendance',{task:t.id,student:st.id,present:true},'small')}${doB('Vắng có thông báo','lesson_attendance',{task:t.id,student:st.id,present:false},'small ghost')}</div>`}`)).join('')}</div>`;
 else if(t.stage==='teach')body=`<h3>Mỗi bạn thử bằng một cách</h3><div class="student-grid">${present.map(st=>studentCard(st,`<p>“${esc(st.need)}”</p>${t.taught[st.id]?'<span class="tag green">✓ Đã hướng dẫn</span>':`<div class="method-stack">${content.experiences.methods.map(m=>doB(m.emoji+' '+m.name,'lesson_teach',{task:t.id,student:st.id,method:m.id},'small')).join('')}</div>`}`)).join('')}</div>`;
 else if(t.stage==='grade')body=`<div class="source-note"><strong>Gợi ý từ ví dụ trên bảng</strong><p>${esc(lesson.fact)}</p></div><h3>Phản hồi riêng từng phiếu</h3><div class="student-grid">${present.map(st=>studentCard(st,`<p class="student-answer">Bạn trả lời: <strong>${esc(st.submission)}</strong></p>${st.id in t.grades?'<span class="tag green">✓ Đã phản hồi</span>':`<div class="row wrap">${doB('Đã đúng · nói rõ vì sao','lesson_grade',{task:t.id,student:st.id,correct:true,feedback:'specific'},'small')}${doB('Cần thử lại · gợi ý riêng','lesson_grade',{task:t.id,student:st.id,correct:false,feedback:'retry'},'small ghost')}</div>`}`)).join('')}</div>`;
 else body=`<div class="mini-result">${em('🌱')}<h2>Một điều mới đã được hiểu</h2><p>${present.length} bạn có mặt · ${Object.keys(t.grades).length} phiếu được phản hồi</p>${doB('Khép tiết & nhận 65 xu','lesson_complete',{task:t.id,confirm:true},'primary jumbo','Khép tiết và lưu phản hồi. Thù lao chỉ nhận một lần.')}</div>`;
 return `<div class="lesson-room"><div class="chalkboard lesson-board"><span>${esc(lesson.topic)} · TIẾT ${t.day}</span><h2>${esc(lesson.title)}</h2><p>${esc(lesson.prompt)}</p>${lessonSketch(lesson)}</div><nav class="lesson-progress">${[['plan','Soạn'],['attendance','Điểm danh'],['teach','Dạy'],['grade','Phản hồi'],['ready','Khép tiết']].map(([k,l])=>`<span class="${t.stage===k?'current':''}">${l}</span>`).join('')}</nav><div class="work-paper">${body}</div></div>`;
}
function routeMap(t,content,route,interactive=true){
 const places=content.experiences.places,points=['gate',...route].map(id=>places.find(p=>p.id===id)).filter(Boolean);
 return `<div class="route-map"><div class="map-river"></div><svg viewBox="0 0 100 100" preserveAspectRatio="none" class="route-lines" aria-hidden="true"><polyline points="${points.map(p=>p.x+','+p.y).join(' ')}" fill="none" stroke="#c2825b" stroke-width="1.2" stroke-dasharray="2 1"/></svg>${places.map(p=>`<button class="route-pin ${route.includes(p.id)?'selected':''} ${t.route[t.at]===p.id?'at':''}" style="left:${p.x}%;top:${p.y}%" ${interactive&&p.id!=='gate'?`data-action="tourRoute" data-place="${p.id}"`:'disabled'}>${em(p.emoji)}<strong>${p.name}</strong><small>${p.id==='gate'?'Xuất phát':`${p.minutes}′ · ${p.fee} xu`}</small></button>`).join('')}</div>`;
}
function guideJob(t,c,content,ui){
 const places=content.experiences.places,lookup=id=>places.find(v=>v.id===id);let body='';
 if(t.stage==='plan'){
  ui.tourRoute??=[];const route=ui.tourRoute;body=`<div class="trip-brief"><h3>Đoàn muốn đi đâu?</h3><p>${t.required.map(id=>lookup(id).name).join(' + ')} · cần Hiên Trà nghỉ chân</p><div class="row wrap"><span class="tag">${t.weather==='rain'?'🌦️ Mưa · lối bờ đóng':'☀️ Đi theo nhịp vừa'}</span><span class="tag">≤ ${t.limit} phút</span><span class="tag">Vé ≤ ${t.budget} xu</span></div></div>${routeMap(t,content,route)}<div class="route-itinerary">${route.map((id,i)=>`<span>${i+1}. ${lookup(id).name}</span>`).join('')||'Chạm các điểm trên bản đồ để tạo tuyến…'}</div><div class="row wrap spread space-top"><span>${route.reduce((s,id)=>s+lookup(id).minutes+5,0)} phút · ${route.reduce((s,id)=>s+lookup(id).fee,0)} xu vé</span>${b('↶ Chọn lại','tourReset',{},'ghost')}${b('Chốt hành trình','tourPlan',{task:t.id},'primary')}</div>`;
 }else if(t.stage==='ready')body=`<div class="mini-result">${em('🧭')}<h2>Cùng đi, cùng trở về</h2><p>${t.stamps.length} điểm · ${t.visitors.length} người · bộ bưu thiếp trong Hộ chiếu</p>${doB('Khép chuyến & nhận 90 xu','tour_complete',{task:t.id,confirm:true},'primary jumbo','Xác nhận đã đi đủ tuyến và gửi kỷ niệm cho đoàn.')}</div>`;
 else {
  const here=t.stage==='stop'?lookup(t.route[t.at]):lookup('gate');const absent=t.at===1&&t.day%2===0&&!t.located;
  const count=`<section class="headcount"><h3>👥 Kiểm đoàn · ${t.counted.length}/${t.visitors.length}</h3><div class="visitor-grid">${t.visitors.map(v=>`<button class="visitor ${t.counted.includes(v.id)?'checked':''}" data-action="expDo" data-op="tour_count" data-payload="${esc(JSON.stringify({task:t.id,visitor:v.id}))}" ${t.counted.includes(v.id)?'disabled':''}><span>${v.id==='binh'?'👨‍🦳':v.id==='truc'?'👩':'🧑'}</span><strong>${v.name}</strong><small>${t.counted.includes(v.id)?'✓ Đã có mặt':absent&&v.id==='nam'?'Đang ở quầy thông tin':'Có mặt ở điểm hẹn'}</small></button>`).join('')}</div>${absent?note('Nam nhắn đang hỏi tại quầy thông tin. Giữ đoàn ở điểm hẹn và nhờ điều phối đi cùng bạn ấy. '+doB('Liên hệ quầy thông tin','tour_locate',{task:t.id,location:'info'},'small primary')):''}</section>`;
  body=`<div class="location-heading"><span>${here.emoji}</span><div><small>${t.stage==='gather'?'ĐIỂM HẸN':'ĐIỂM '+(t.at+1)+' / '+t.route.length}</small><h2>${here.name}</h2></div></div>${count}`;
  if(t.stage==='gather')body+=doB('Khởi hành · '+t.plan_cost+' xu vé','tour_depart',{task:t.id,confirm:true},'primary jumbo','Dùng '+t.plan_cost+' xu cho vé tham quan; chỉ thu một lần cho chuyến.');
  else {const target=content.experiences.photo_objects.find(o=>o.id===here.target);body+=`<div class="tour-station-grid"><div class="source-note"><h3>📖 Bảng chuyện của điểm đến</h3><p>${esc(here.fact)}</p><strong>${esc(here.question)}</strong><div class="row wrap space-top">${t.quiz_done?'<span class="tag green">✓ Đã kể đúng chi tiết</span>':here.answers.map(a=>doB(esc(a),'tour_tell',{task:t.id,answer:a},'small')).join('')}</div></div><div class="photo-mission"><h3>📸 Phiếu ảnh: ${target.name}</h3><p>Chạm đúng chủ thể trong khung cảnh nhỏ.</p><div class="photo-finder">${content.experiences.photo_objects.map((o,i)=>`<button style="left:${[18,50,80,26,68,47][i]}%;top:${[24,19,34,72,76,52][i]}%" data-action="expDo" data-op="tour_photo" data-payload="${esc(JSON.stringify({task:t.id,object:o.id}))}" aria-label="Chụp ${o.name}">${o.emoji}</button>`).join('')}<i class="viewfinder"></i></div>${t.photo_done?'<span class="tag green">✓ Đã chụp đúng chủ thể</span>':''}</div></div>${doB(t.at===t.route.length-1?'Gửi ảnh · trở về bến':'Lưu bưu thiếp · tới điểm tiếp','tour_next',{task:t.id},'primary jumbo')}`;}
 }
 return `<div class="guide-workbench">${body}</div>`;
}
function cupArt(cup,ingredients){
 const base=ingredients.find(v=>cup.items.includes(v.id)&&v.group==='base'),flavor=ingredients.find(v=>cup.items.includes(v.id)&&v.group==='flavor'),topping=ingredients.filter(v=>cup.items.includes(v.id)&&v.group==='topping');
 return `<svg class="big-cup" viewBox="0 0 200 235" aria-label="Ly bạn đang pha"><defs><clipPath id="cupClip"><path d="M43 43H157L145 209Q144 218 132 218H69Q56 218 56 209Z"/></clipPath></defs><ellipse cx="100" cy="224" rx="62" ry="7" fill="#7f654326"/><path d="M43 43H157L145 209Q144 218 132 218H69Q56 218 56 209Z" fill="#ffffffa6" stroke="#896649" stroke-width="3"/><g clip-path="url(#cupClip)">${base?`<rect x="44" y="${cup.size==='L'?53:83}" width="116" height="175" fill="${base.color}"/>`:''}${flavor?`<rect x="44" y="167" width="116" height="50" fill="${flavor.color}"/>`:''}${topping.map((top,k)=>top.id==='foam'?'<ellipse cx="100" cy="84" rx="57" ry="12" fill="#fff4df"/>':Array.from({length:11},(_,i)=>`<circle cx="${62+(i%5)*18}" cy="${207-Math.floor(i/5)*15-k*20}" r="6" fill="${top.color}"/>`).join('')).join('')}${cup.ice!=='none'?'<rect x="61" y="88" width="22" height="22" rx="6" fill="#fff9d45c" transform="rotate(10 72 99)"/><rect x="117" y="110" width="21" height="21" rx="5" fill="#ffffff55"/>':''}</g><rect x="38" y="36" width="124" height="10" rx="5" fill="${cup.sealed?'#eab0bc':'#f9f0da'}" stroke="#896649" stroke-width="2.4"/>${cup.sealed?'<path d="M103 37L117 2" stroke="#e5839d" stroke-width="10"/>':''}<ellipse cx="100" cy="140" rx="27" ry="24" fill="#fff0d5" stroke="#ae8160" stroke-width="1.6"/><circle cx="92" cy="138" r="2.5" fill="#674d3a"/><circle cx="108" cy="138" r="2.5" fill="#674d3a"/><path d="M95 146Q100 151 105 146" fill="none" stroke="#674d3a" stroke-width="2"/><circle cx="85" cy="145" r="4" fill="#edb0b3"/><circle cx="115" cy="145" r="4" fill="#edb0b3"/></svg>`;
}
function teaJob(t,c,content){
 const ingredients=content.experiences.ingredients,cup=t.cup,n=t.needs;
 return `<div class="tea-counter"><div class="tea-working"><div class="cup-stage">${cupArt(cup,ingredients)}<div class="cup-label">${cup.items.length?cup.items.map(k=>ingredients.find(i=>i.id===k).name).join(' · '):'Ly mới đang chờ một chút trà'}</div><span class="tag">${cup.size} · ${cup.sugar}% đường · ${{none:'không đá',little:'ít đá',normal:'đá thường'}[cup.ice]}</span>${cup.checked?'<span class="tag green">✓ Đúng yêu cầu</span>':''}</div><div class="tea-controls"><h3>Chỉnh theo vị khách thích</h3><div class="tea-option"><label>Cỡ ly<select class="input" id="tea-size" ${cup.sealed?'disabled':''}>${['M','L'].map(v=>`<option ${v===cup.size?'selected':''}>${v}</option>`).join('')}</select></label><label>Đường<select class="input" id="tea-sugar" ${cup.sealed?'disabled':''}>${[0,30,50,100].map(v=>`<option value="${v}" ${v===cup.sugar?'selected':''}>${v}%</option>`).join('')}</select></label><label>Đá<select class="input" id="tea-ice" ${cup.sealed?'disabled':''}>${[['none','Không đá'],['little','Ít đá'],['normal','Bình thường']].map(([v,l])=>`<option value="${v}" ${v===cup.ice?'selected':''}>${l}</option>`).join('')}</select></label></div>${b('Lưu cỡ · đường · đá','teaConfig',{task:t.id},'cream full')}<div class="tea-step-actions">${doB('✓ Kiểm ly','tea_check',{task:t.id},'primary')}${doB('Đóng nắp','tea_seal',{task:t.id},'cream')}${doB('Làm lại ly','tea_discard',{task:t.id,confirm:true},'ghost','Bỏ ly đang làm. Nguyên liệu đã dùng không hoàn kho.')}</div>${doB('Trao khách · '+fmt(t.quoted_price||0)+' xu','tea_serve',{task:t.id,confirm:true},'primary jumbo','Giao ly đã kiểm và đóng nắp; thu đúng giá đã chốt.')}</div></div>${['base','flavor','topping'].map((group,i)=>`<section class="ingredient-shelf"><h3>${['🫖 Trà nền','🍑 Hương vị','🟤 Topping'][i]}</h3><div class="ingredient-row">${ingredients.filter(v=>v.group===group).map(v=>`<button class="ingredient ${cup.items.includes(v.id)?'chosen':''}" data-action="expDo" data-op="tea_add" data-payload="${esc(JSON.stringify({task:t.id,item:v.id}))}" ${!t.known||cup.sealed||cup.items.includes(v.id)||c.life.stock[v.id]===0?'disabled':''}>${ingredientArt(v)}<strong>${v.name}</strong><small>${cup.items.includes(v.id)?'✓ Trong ly':'Còn '+c.life.stock[v.id]}</small></button>`).join('')}</div></section>`).join('')}<div class="row wrap space-top">${b('🧺 Chuẩn bị thêm nguyên liệu','prepare',{},'ghost')}${b('🏷️ Xem menu','prices',{},'ghost')}</div></div>`;
}
export function extendedJob(t,c,content,ui,state){
 if(t.career==='teacher'&&t.room)return tt()?TT.lessonV2(t,c,content,ui,state):skeleton();
 if(t.career==='tour_guide'&&t.trip)return tt()?TT.tripV2(t,c,content,ui):skeleton();
 const body=t.career==='teacher'?teacherJob(t,c,content,ui):t.career==='tour_guide'?guideJob(t,c,content,ui):teaJob(t,c,content);
 return guestRibbon(t,c,content)+body;
}
export function experienceSummary(c){
 const x=c.shift_summary?.experiences;if(!x)return '';
 return `<section class="cozy-summary"><h3>🌙 Những điều mang về hôm nay</h3><div class="summary-mini-grid"><div><strong>${x.perfect}</strong><small>Việc làm chính xác</small></div><div><strong>${x.activities}</strong><small>Trò nhỏ đã xong</small></div><div><strong>${x.tips}</strong><small>Tip vào két</small></div></div><div class="receipt-row"><span>Tip đội nhận trực tiếp (không qua két)</span><b>${x.staff_tips} xu</b></div><div class="receipt-row"><span>Giá trị nguyên liệu đã dùng</span><b>${x.consumed_cost} xu</b></div><div class="receipt-row"><span>Hao hụt ghi nhận (không trừ lại)</span><b>${x.waste_value} xu</b></div>${b('Xem hộ chiếu & kỷ niệm','passport',{},'ghost full')}</section>`;
}
