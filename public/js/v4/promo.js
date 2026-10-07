/** 🎖️ Thăng tiến and 🧑‍💼 Ca quản lý (game/promotion.py → room().promo). Loaded lazily by app.js (L.promo).
 *
 * Two sheets, each one icon, one short line and one obvious button; the explanations sit behind "Xem thêm".
 *   promo    the ladder (title · good days · bar), the review when one is due (two questions, then the pay ask),
 *            and the way into a manager shift from step 3;
 *   manager  the board: tap a job, tap a teammate; check what comes back (✅ / ↩️); settle a small crisis;
 *            close the shift. Every step is a server command (pm_*); the board here only remembers which job
 *            is picked (ui.pmPick).
 *   office   🏢 Phòng điều hành (game/promotion_office.py, from the executive step of a long ladder): the day's figures, then
 *            three tabs: 📥 việc cần quyết, 🗓️ điều phối (tap a slot, tap a person), 👥 nhân sự (tap a person, pick a decision).
 *            Shown in the 'manager' sheet while ui.pmOffice is set. */
import {icon,escapeHTML as esc} from '../icons.js';
import {T} from './terms.js';
import {orgView,inspView} from './org.js';   // 🎖️ a career on an org ladder (game/org.py)

const KIND={khach:['🗣️','Khách'],tay:['🔧','Tay nghề'],so:['📋','Giấy tờ'],gap:['⚡','Việc gấp']};
const mood=n=>n>=80?'😊':n>=60?'🙂':n>=40?'😐':'😟';
const head=(title,sub='',eyebrow='')=>`<header class="sheet-head"><div class="grow">${eyebrow?`<span class="eyebrow">${eyebrow}</span>`:''}<h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
const cmd=(label,command,payload={},style='',disabled=false)=>`<button type="button" class="btn ${style}" data-command="${command}" data-payload="${esc(JSON.stringify(payload))}"${disabled?' disabled':''}>${label}</button>`;
const act=(label,action,data={},style='',disabled=false)=>`<button type="button" class="btn ${style}" data-action="${action}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${disabled?' disabled':''}>${label}</button>`;
const bar=(a,b)=>`<div class="bar pm-bar" role="progressbar" aria-valuemin="0" aria-valuemax="${b}" aria-valuenow="${a}"><i style="width:${b?Math.min(100,Math.round(100*a/b)):0}%"></i></div>`;
const room=env=>env.api.state.careers[env.api.state.current];
const GOLD='#d9b45a',NAVY='#1f2d4d';
const starPts=(cx,cy,r)=>Array.from({length:10},(_,i)=>{const a=Math.PI/5*i-Math.PI/2,rr=i%2?r*.45:r;return `${(cx+rr*Math.cos(a)).toFixed(1)},${(cy+rr*Math.sin(a)).toFixed(1)}`;}).join(' ');
/** A pilot's shoulder board (F#193): g gold stripes, s stars, w a gold wreath around the stars. */
export function insignia(x,w=96){
  if(!x)return '';
  if(x.big)return bigStar(x,w);
  const bars=Array.from({length:x.g},(_,i)=>`<rect x="${84-i*8}" y="7" width="5" height="22" rx="1" fill="${GOLD}"/>`).join('');
  const stars=Array.from({length:x.s},(_,i)=>`<polygon points="${starPts(26+i*12,18,5.5)}" fill="${GOLD}"/>`).join('');
  const wreath=x.w?`<path d="M18 27 Q30 35 52 27" fill="none" stroke="${GOLD}" stroke-width="1.6"/><path d="M18 9 Q16 18 18 27 M52 9 Q54 18 52 27" fill="none" stroke="${GOLD}" stroke-width="1.2" stroke-dasharray="2 2"/>`:'';
  return `<svg class="pm-ins" viewBox="0 0 100 36" width="${w}" height="${Math.round(w*.36)}" role="img" aria-label="${esc(x.label||'')}"><rect x="1" y="3" width="97" height="30" rx="7" fill="${NAVY}"/><circle cx="9" cy="18" r="3.6" fill="${GOLD}"/>${wreath}${stars}${bars}</svg>`;
}
/** Phó Tổng Giám đốc (F#207): one big star on a swept bird's wing, aviation style, on the same navy board. */
function bigStar(x,w){
  const wing=x.wing?`<path d="M69 14 C57 6 37 2.5 15 5 Q18.5 9.5 23 13 Q25 10.8 27.5 10.2 Q29.5 14.5 33.5 18 Q35.5 14.6 38 14 Q40.5 18.5 44.5 22 Q46.5 18 49 17.4 Q51.5 21 55.5 24 Q57.8 20.6 60.5 20.4 Q63.5 23.4 68.5 24 Z" fill="${GOLD}"/>`
    +`<path d="M67 15.6 C56 9.6 41 7 25 7.6 M27.5 10.2 C38 10.2 50 12.6 62 17.6" fill="none" stroke="${NAVY}" stroke-width=".8" opacity=".55"/>`:'';
  return `<svg class="pm-ins" viewBox="0 0 100 36" width="${w}" height="${Math.round(w*.36)}" role="img" aria-label="${esc(x.label||'')}"><rect x="1" y="3" width="97" height="30" rx="7" fill="${NAVY}"/><circle cx="9" cy="18" r="3.6" fill="${GOLD}"/>${wing}<polygon points="${starPts(79,18.5,12.5)}" fill="${GOLD}" stroke="${NAVY}" stroke-width=".8"/></svg>`;
}
const badge=p=>p.insignia?`<span class="pm-badge pm-badge-ins">${insignia(p.insignia,112)}<small>${esc(p.insignia.label)}</small></span>`:`<span class="pm-badge" aria-hidden="true">${p.badge||'🎖️'}</span>`;
const place=env=>env.api.content.catalogue?.find(x=>x.id===env.api.state.current)?.short||'';

/** F#206: what a "ngày điều hành tốt" is (game/promotion_office.py close: score, GOOD_SCORE). */
const OFFICE_RULE=`<li>🏢 Ngày điều hành tốt: trong ca, tự xếp ít nhất 1 việc ở 🗓️ Điều phối, rồi khép ngày với điểm điều hành từ 60/100.</li><li>Điểm = ½ tỷ lệ đúng giờ + 0,3 × tinh thần + 20, trừ 6 mỗi phàn nàn và 2 mỗi % vượt quỹ lương. Việc bỏ trống, việc cần quyết để tới cuối ngày đều thêm phàn nàn.</li><li>🔁 Xoay ca: ai đã làm 2 ngày liền thì sáng hôm sau dễ 🥱 mệt (1 phần 2), và hôm đó làm dễ trễ hơn hẳn. Đừng để ai làm ngày thứ 3 liền, cho nghỉ 1 ngày là hết mệt.</li><li>Số ngày điều hành tốt đếm lại từ 0 sau mỗi lần lên bậc.</li>`;
/** F#212: "đã làm N ngày liền" on a person (duty = days in a row worked before today; TIRED_AT costs). */
const tiredAt=of=>of.tired_at||2;
const rowTag=(of,m)=>!m.duty||m.rest?'':m.duty>=tiredAt(of)?`<i class="bad">🥱 ${m.duty} ngày liền · nên nghỉ</i>`:`<i>🔁 ${m.duty} ngày liền</i>`;
/** The steps behind "Xem thêm": what each step gives. */
function more(p,career){
  const emp=p.track==='emp',pcts=(p.pcts||[]).map(x=>x+'%').join(' → ');
  const rows=(p.log||[]).map(x=>`<li>✓ Ngày ${x.d}: bậc ${x.to}</li>`).join('');
  const ladder=p.ladder?`<ol class="pm-path">${p.ladder.map((t,i)=>`<li class="${i<p.rank?'on':''}">${p.insignias?insignia(p.insignias[i],46):''}<span>${esc(t)}</span></li>`).join('')}</ol>`:'';
  return `<details class="pm-more"><summary>Xem thêm</summary>${ladder}<ul class="pm-rules">
    <li>Ngày tốt: ca thường xong từ 2 việc, đánh giá trong ngày từ ★3.5 nếu có. Nghề văn phòng theo kết quả “ngày chắc tay”; ca quản lý đạt chất lượng từ 60%.</li>
    <li>${emp?'Mỗi bậc: tăng lương ':`Mỗi bậc: ${esc(T(career,'tip').toLowerCase())} `}${pcts}.</li>
    <li>Bậc 3: mở 🧑‍💼 Ca quản lý${p.track==='own'?' (nhân viên + phụ việc thời vụ)':''}.</li>
    ${p.office_from?`<li>Bậc ${p.office_from} (${esc(p.office_title)}): mở 🏢 phòng điều hành: điều phối, quản lý nhân sự, xử lý việc khó.</li>${OFFICE_RULE}`:''}
    <li>Không bao giờ bị giáng chức. Ngày chưa tốt không cộng ngày tốt và vẫn tính vào tỷ lệ ngày làm.</li>${rows}</ul></details>`;
}

/** The review: one question at a time, then (employees) the pay ask. */
function review(p){
  const d=p.due,dots=`<span class="pm-dots">${Array.from({length:d.of},(_,i)=>`<i class="${i<d.n?'on':''}"></i>`).join('')}</span>`;
  const top=`<p class="pm-eyebrow">${d.who==='Phòng sếp'?'🏢 Phòng sếp':'🏮 Hội buôn phố'} ${dots}</p><h3 class="pm-title">Xét lên ${esc(d.title)}</h3>`;
  if(d.q)return `<article class="pm-card pm-review">${top}<p class="pm-q">${esc(d.q.text)}</p><div class="pm-opts">${d.q.options.map(o=>act(esc(o.label),'pmAnswer',{question:d.q.id,option:o.id},'pm-opt')).join('')}</div>
    <details class="pm-more"><summary>?</summary><p class="small muted">Mỗi câu có cách tốt nhất, cách tạm được và cách sếp chưa ưng (0 điểm). Có câu 0 điểm là hẹn xét lại sau 3 ngày làm. Chọn cách đúng quy trình, có trách nhiệm nhất.</p></details></article>`;
  if(d.ask)return `<article class="pm-card pm-review">${top}<p class="pm-q">💰 Lương mới: <b>${d.pay[0]} → ${d.pay[1]} xu/ngày</b></p><div class="pm-opts">${d.ask.map((a,i)=>act(esc(a.label),'pmAsk',{ask:a.id},i===0?'primary':'pm-opt')).join('')}</div>
    <details class="pm-more"><summary>?</summary><p class="small muted">Xin hợp lý, xin cao: được thêm khi cả hai câu đều trả lời tốt nhất. “Xin cao” mà có câu mới tạm được thì sếp hẹn 3 ngày làm nữa. Chưa chắc thì chọn “Xin hợp lý”.</p></details></article>`;
  return '';
}

/** #11: why the last review did not pass and when the next one is. The answers' scores come back with the
 * command (game/promotion.py _later, `review`) and live in ui.pmLast for this session; after a reload only the rule. */
function lastReview(env,wait){
  const L=env.ui?.pmLast?.career===env.api.state.current?env.ui.pmLast:null;
  const when=`<p class="small">⏳ Chỉ đếm ngày có làm việc. Làm thêm <b>${wait}</b> ngày là sếp hẹn xét lại ở đầu ca kế tiếp.</p>`;
  if(!L)return `<div class="pm-last">${when}<p class="small muted">💡 Lần xét trước chưa qua: có câu bị chấm 0 điểm, hoặc chọn “Xin cao” khi chưa trả lời tốt nhất cả hai câu. Lần sau chọn cách đúng quy trình nhất rồi “Xin hợp lý”.</p></div>`;
  const mark=s=>s===2?'✅':s===1?'🟡':'❌';
  return `<div class="pm-last"><p class="pm-eyebrow">📋 Lần xét vừa rồi</p><ul class="pm-rules">${L.rows.map(r=>`<li class="${r.score?'':'bad'}">${mark(r.score)} ${esc(r.q)}<small class="pm-hint">Bạn chọn “${esc(r.a)}” · ${esc(r.word)}</small></li>`).join('')}${L.why==='high'?`<li class="bad">❌ Xin cao<small class="pm-hint">Chỉ được khi cả hai câu đều tốt nhất. Lần sau chọn “Xin hợp lý”.</small></li>`:''}</ul>${when}</div>`;
}
export function promoView(env){
  const c=room(env),p=c.promo;
  if(!p)return head('🎖️ Thăng tiến')+`<div class="sheet-body"><p class="muted">Có việc làm rồi mới tính chuyện lên chức nhé.</p></div>`;
  if(p.org)return orgView(env,head,act,cmd,esc(place(env)).toUpperCase());
  if(p.due)return head('🎖️ Thăng tiến','',esc(place(env)).toUpperCase())+`<div class="sheet-body">${review(p)}</div>`;
  const n=p.next,sh=p.shift;
  const line=n?`${n.good}/${n.need} ngày tốt → ${esc(n.title)}`:'Bậc cao nhất rồi!';
  const lock=(n?.requirements?.length?`<ul class="pm-rules">${n.requirements.map(r=>`<li>${r.met?'✓':'🔒'} ${esc(r.label)}${r.id==='office'&&r.need?`${bar(r.got,r.need)}<small class="pm-hint">Ngày tốt khi: tự xếp ít nhất 1 việc ở 🗓️ Điều phối và cuối ngày điểm điều hành từ 60/100.</small>`:''}</li>`).join('')}</ul>`
    :[n?.why,n?.wait?`Hẹn xét lại sau ${n.wait} ngày làm`:null].filter(Boolean).map(s=>`<p class="pm-lock">🔒 ${esc(s)}</p>`).join(''))+(n?.wait?lastReview(env,n.wait):'');
  const work=p.rank>=3?'Bạn có thể mở ca quản lý: giao việc cho đội, kiểm tra kết quả và xử lý chuyện trong ca. Mỗi ngày vẫn có thể chọn tự làm ở quầy.'
    :'Công việc ở quầy vẫn như trước. Từ bậc 3, bạn có thêm ca quản lý để giao việc cho đội và kiểm tra kết quả.';
  const benefit=p.track==='emp'?`Thăng chức tăng lương${p.pct?` · hiện tại +${p.pct}%`:''}.`:`Thăng tiến tăng tiền boa từ khách quen${p.pct?` · hiện tại +${p.pct}%`:''}.`;
  let main;
  const of=p.office,todo=of?.inbox?.length||0;
  const office=of?act(`🏢 ${esc(of.name)}${todo?` · ${todo} việc cần quyết`:''}`,'pmOffice',{},`${c.open&&of.live&&!sh?'primary':''} big full`):'';
  if(c.open&&sh)main=act('🧑‍💼 Bảng quản lý','pmBoard',{},'primary big full');
  else if(p.mgr&&!c.open)main=act(`🧑‍💼 Mở ca quản lý · ${p.team} người`,'pmStart',{},'primary big full');
  else main=act('Về quầy','close',{},'primary big full');
  const step=`<span class="pm-step">${Array.from({length:p.top},(_,i)=>`<i class="${i<p.rank?'on':''}"></i>`).join('')}</span>`;
  if(office&&c.open&&of.live&&!sh)main=office+act('Về quầy','close',{},'ghost full');
  else if(office)main=office+main;
  return head('🎖️ Thăng tiến','',esc(place(env)).toUpperCase())+`<div class="sheet-body"><article class="pm-card pm-ladder">${badge(p)}<h3 class="pm-title">${esc(p.title)}</h3>${step}${n?bar(n.good,n.need):''}<p class="pm-line">${line}</p><p class="small">💰 ${benefit}</p><p class="small muted">${work}</p>${lock}${main}${more(p,env.api.state.current)}</article></div>`;
}

/* ------------------------------------------------------------------ 🏢 Phòng điều hành */
const FACE=n=>n>=75?'😊':n>=55?'🙂':n>=35?'😐':n>=20?'😟':'😣';
const pctBar=(n,cls='')=>`<span class="of-meter ${cls}" aria-hidden="true"><i style="width:${Math.max(0,Math.min(100,n))}%"></i></span>`;
function officeKpi(of){
  const k=of.kpi,l=of.labels,over=k.cost>k.budget;
  const tile=(v,label,cls='')=>`<span class="${cls}"><b>${v}</b><small>${esc(label)}</small></span>`;
  return `<div class="of-kpi">${tile(k.ontime+'%','⏱️ '+l[0],k.ontime<60?'bad':'')}${tile(k.compl,'📣 '+l[1],k.compl>6?'bad':'')}${tile(FACE(k.morale)+' '+k.morale,l[2],k.morale<45?'bad':'')}${tile(Math.round(100*k.cost/k.budget)+'%','💰 '+l[3],over?'bad':'')}</div>`;
}
function officeInbox(of){
  if(!of.inbox.length)return `<p class="of-empty">✅ Không còn việc nào chờ quyết hôm nay.</p>`;
  return of.inbox.map(x=>`<article class="pm-card of-ask"><p class="pm-eyebrow">${x.emoji} ${esc(x.title)}</p><p class="pm-q">${esc(x.text)}</p><div class="pm-opts">${x.options.map(o=>cmd(esc(o.label),'pm_of_inbox',{item:x.i,option:o.id},'pm-opt')).join('')}</div></article>`).join('')
    +`<p class="small muted">Để đó tới cuối ngày thì phương án tệ nhất sẽ xảy ra.</p>`;
}
const BAR={off:'🚫 đình chỉ',rest:'😴 phải nghỉ',lv:'🎓 chưa đủ bậc'};
function why(of,slot,m){
  const b=slot.bar?.[m.i];if(b)return BAR[b]||'🔒';
  if(of.slots.some(x=>x.who===m.i&&x.i!==slot.i))return '📌 đã có việc';
  return '';
}
function officePlan(of,ui){
  const pick=Number.isInteger(ui.pmOfSlot)?ui.pmOfSlot:null;
  const rows=of.slots.map(s=>{
    const who=s.who!=null?of.staff[s.who]:null,open=pick===s.i;
    const tag=who?`<span class="of-who">${FACE(who.mood)} ${esc(who.n)}</span>`:`<span class="of-who none">${open?'👇 Chọn người':'Chưa xếp'}</span>`;
    let list='';
    if(open){
      const cands=of.staff.filter(m=>m.r===s.role).map(m=>{const w=why(of,s,m);return {m,w};}).sort((a,b)=>(a.w?1:0)-(b.w?1:0)||b.m.sk-a.m.sk);
      list=`<div class="of-cands">${cands.map(({m,w})=>`<button type="button" class="of-cand" data-action="pmOfMate" data-slot="${s.i}" data-i="${m.i}"${w?' disabled':''}><b>${esc(m.n)}</b><small>${esc(m.t)} · tay nghề ${m.sk}${m.iss?' · ⚠️':''}${m.duty&&!m.rest?` · ${m.duty>=tiredAt(of)?'🥱 ':''}${m.duty} ngày liền`:''}</small><span>${w||FACE(m.mood)}</span></button>`).join('')}
        ${who?cmd('✕ Bỏ xếp','pm_of_plan',{slot:s.i,mate:null},'small ghost'):''}</div>`;
    }
    return `<li class="of-slot${open?' open':''}${who?' set':''}"><button type="button" class="of-slot-btn" data-action="pmOfSlot" data-i="${s.i}" aria-expanded="${open}"><span class="of-slot-t"><b>${esc(s.t)}</b><small>${esc(s.sub)}${s.need?` · cần từ ${esc(s.need)}`:''}</small></span>${tag}</button>${list}</li>`;
  }).join('');
  return `<ul class="of-slots">${rows}</ul><details class="pm-more"><summary>Xem thêm</summary><ul class="pm-rules">${OFFICE_RULE}<li>Người làm ${of.duty_max} ngày liền phải nghỉ một ngày (quy định). Ai được nghỉ thì tinh thần lên.</li><li>Tay nghề cao, tinh thần tốt: dễ đúng giờ. Đang có chuyện chưa xử lý (⚠️) thì dễ trễ.</li><li>Ô bỏ trống: trợ lý xếp tạm lúc khép ngày, kém hơn và không có thưởng điều hành. Không ai làm được thì ${esc(of.unit)} đó bị hủy.</li></ul></details>`;
}
function officeStaff(of,ui){
  const open=Number.isInteger(ui.pmOfWho)?ui.pmOfWho:null;
  return `<p class="of-left">🗳️ Còn <b>${of.left}</b> lượt quyết nhân sự hôm nay · mỗi người một quyết định/ngày</p><ul class="of-staff">${of.staff.map(m=>{
    const tags=[m.iss?`<i class="bad">${esc(m.iss)}</i>`:'',m.mk?`<i>${esc(m.mk)}</i>`:'',m.off?'<i class="bad">🚫 Đình chỉ</i>':'',m.rest?'<i>😴 Phải nghỉ</i>':'',rowTag(of,m),m.acted?'<i>✓ Đã quyết hôm nay</i>':''].join('');
    let body='';
    if(open===m.i){
      const off=(a)=>m.acted||!of.left||(a==='promote'&&m.top)||(a==='demote'&&m.low)||(a==='raise'&&m.pay>=7)||(a==='cut'&&m.pay<=1);
      body=`<div class="of-person"><p class="small">${m.hint?`📝 ${esc(m.hint)}`:'🔒 Chưa rõ tính cách: nói chuyện riêng để hiểu.'}</p>
        <p class="of-line"><span>Tay nghề</span>${pctBar(m.sk)}<b>${m.sk}</b></p><p class="of-line"><span>Tinh thần</span>${pctBar(m.mood,m.mood<35?'low':'')}<b>${m.mood}</b></p><p class="small muted">Bậc lương ${m.pay}/7${m.duty?` · làm ${m.duty} ngày liền`:''}</p>
        <div class="of-acts">${of.acts.map(a=>cmd(`${a.icon} ${esc(a.label)}`,'pm_of_hr',{mate:m.i,act:a.id},'small',off(a.id))).join('')}</div></div>`;
    }
    return `<li class="of-row${open===m.i?' open':''}"><button type="button" class="of-row-btn" data-action="pmOfWho" data-i="${m.i}" aria-expanded="${open===m.i}"><span class="of-face" aria-hidden="true">${FACE(m.mood)}</span><span class="of-name"><b>${esc(m.n)}</b><small>${esc(m.t)}</small></span><span class="of-tags">${tags}</span></button>${body}</li>`;
  }).join('')}</ul><details class="pm-more"><summary>Xem thêm</summary><ul class="pm-rules"><li>Mỗi người có tính cách riêng: cùng một quyết định, người này cảm ơn, người kia tự ái.</li><li>Có lý do (đang có lỗi, đã nhắc từ trước, làm tốt thật) thì quyết định có tác dụng. Không có lý do thì người đó buồn và cả phòng để ý.</li><li>Mệt không phải là lỗi: cho nghỉ, đừng phạt.</li><li>Thăng chức, tăng lương làm quỹ lương tăng. Bị dồn quá thì người ta nghỉ việc.</li></ul></details>`;
}
/** F#206: does today count as a good office day? Progress n/need and what the close will score. */
function officeToday(of,p,empty){
  const r=p.next?.requirements?.find(x=>x.id==='office'&&x.need);
  const ok=(on,text)=>`<li class="${on?'on':''}">${on?'✓':'○'} ${text}</li>`;
  const k=of.kpi,over=k.cost>k.budget,tired=new Set(of.slots.map(x=>x.who).filter(w=>w!=null&&(of.staff[w]?.duty||0)>=tiredAt(of))).size;
  const rows=[typeof of.me==='boolean'?ok(of.me,'Tự xếp ít nhất 1 việc ở 🗓️ Điều phối'):'',
    ok(!of.inbox.length,of.inbox.length?`Còn ${of.inbox.length} việc cần quyết (để tới cuối ngày là thêm phàn nàn)`:'Đã quyết hết 📥 việc'),
    ok(!empty,empty?`${empty} ${esc(of.unit)} chưa xếp người`:'Đã xếp đủ người'),
    ok(!tired,tired?`${tired} người đã làm ${tiredAt(of)}+ ngày liền đang được xếp (dễ trễ): xoay ca`:'Xoay ca: không ai làm ngày thứ 3 liền'),
    ok(!over,over?'Quỹ lương đang vượt (trừ 2 điểm mỗi %)':'Quỹ lương trong mức')].join('');
  return `<details class="of-today"${of.me===false&&!p.org?' open':''}><summary><b>🎯 ${r?`Ngày điều hành tốt: ${r.got}/${r.need}`:'Hôm nay tính ngày tốt?'}</b><span>${r?bar(r.got,r.need):''}</span></summary><ul>${rows}</ul><p class="small muted">Cuối ngày, điểm điều hành từ ${of.good_score||60}/100 là tính 1 ngày tốt. Điểm và cách tính hiện ở tổng kết ngày.</p></details>`;
}
export function officeView(env){
  const c=room(env),p=c.promo,of=p?.office,ui=env.ui;
  if(!of)return head('🏢 Phòng điều hành')+`<div class="sheet-body"><p class="muted">Phòng điều hành mở từ bậc lãnh đạo.</p></div>`;
  const eyebrow=esc(place(env)).toUpperCase();
  if(of.wait||!of.live)return head(`🏢 ${esc(of.name)}`,'',eyebrow)+`<div class="sheet-body">${of.kpi?officeKpi(of):''}<p class="of-empty">${of.wait?'Phòng mở từ ca sau. Mở ca là có việc ngay.':'Phòng điều hành làm việc trong ca. Mở ca để điều phối và quyết việc.'}</p>${act('Về quầy','close',{},'primary big full')}</div>`;
  const insp=p.org?.insp?[['insp','🔎 Kiểm tra']]:[];   // 🎖️ Trợ lý BGĐ: kiểm tra điều lệnh (game/org.py)
  const tabs=[...insp,['inbox',`📥 Việc${of.inbox.length?` (${of.inbox.length})`:''}`],['plan','🗓️ Điều phối'],['staff','👥 Nhân sự']];
  const tab=tabs.some(t=>t[0]===ui.pmOfTab)?ui.pmOfTab:insp.length&&!p.org.insp.sent?'insp':(of.inbox.length?'inbox':of.slots.some(s=>s.who==null)?'plan':'staff');
  const empty=of.slots.filter(s=>s.who==null).length;
  const line=of.inbox.length?`${of.inbox.length} việc chờ quyết`:empty?`${empty} ${of.unit} chưa xếp người`:'Bảng hôm nay đã xếp đủ';
  const bar=`<div class="of-tabs" role="tablist">${tabs.map(([id,label])=>`<button type="button" role="tab" class="of-tab${tab===id?' on':''}" aria-selected="${tab===id}" data-action="pmOfTab" data-tab="${id}">${label}</button>`).join('')}</div>`;
  const body=tab==='insp'?inspView(p.org,cmd):tab==='inbox'?officeInbox(of):tab==='plan'?officePlan(of,ui):officeStaff(of,ui);
  const log=of.log?.length?`<details class="pm-more"><summary>Nhật ký</summary><ul class="pm-rules">${of.log.slice().reverse().map(x=>`<li>${esc(x)}</li>`).join('')}</ul></details>`:'';
  const foot=`<footer class="sheet-foot"><p>🗳️ ${of.left} lượt quyết · thưởng tối đa ${of.cap} xu</p>${act('Xong','close',{},'primary')}</footer>`;
  return head(`🏢 ${esc(of.name)}`,line,eyebrow)+`<div class="sheet-body of-board">${officeKpi(of)}${officeToday(of,p,empty)}${bar}<div class="of-body" role="tabpanel">${body}</div>${log}</div>`+foot;
}

/** The manager's board. */
export function managerView(env){
  const c=room(env),p=c.promo,sh=p?.shift,ui=env.ui;
  if(ui.pmOffice&&p?.office)return officeView(env);
  if(!sh)return head('🧑‍💼 Ca quản lý')+`<div class="sheet-body"><p class="muted">Chưa có ca quản lý nào đang mở.</p></div>`;
  const eyebrow=esc(place(env)).toUpperCase();
  if(sh.closed){
    const own=p.track==='own';
    return head('🧑‍💼 Chốt ca','',eyebrow)+`<div class="sheet-body"><article class="pm-card pm-done"><span class="pm-badge" aria-hidden="true">${sh.quality>=60?'🎉':'🙂'}</span>
      <div class="pm-stats"><span><b>${sh.good}/${sh.size}</b><small>việc tốt</small></span><span><b>${sh.quality}%</b><small>chất lượng</small></span><span><b>${mood(sh.mood)}</b><small>tinh thần đội</small></span></div>
      <p class="pm-pay">+${sh.bonus} xu ${own?esc(T(env.api.state.current,'income'))+' đội':'thưởng quản lý'}${sh.wage?` · −${sh.wage} xu phụ việc`:''}</p>${act('Khép ngày','end',{},'primary big full')}</article></div>`;
  }
  const pick=Number.isInteger(ui.pmPick)&&sh.tasks[ui.pmPick]?.st==='q'?ui.pmPick:null,esc_=sh.esc,busy=!!esc_;
  const team=`<div class="pm-team" role="group" aria-label="Đội">${sh.team.map(m=>{
    const can=pick!=null&&!m.busy&&!m.off&&!busy,fit=pick!=null?(m.s===sh.tasks[pick].kind?' fit':m.w===sh.tasks[pick].kind?' weak':''):'';
    return `<button type="button" class="pm-mate${m.busy?' busy':''}${m.off?' off':''}${fit}" data-action="pmMate" data-i="${m.i}"${can?'':' disabled'}><span class="pm-face" aria-hidden="true">${m.off?'🏠':m.busy?'⏳':mood(m.mood)}</span><b>${esc(m.name)}</b><span class="pm-sw"><i class="s" title="Giỏi: ${KIND[m.s][1]}">${KIND[m.s][0]}</i><i class="w" title="Yếu: ${KIND[m.w][1]}">${KIND[m.w][0]}</i></span></button>`;}).join('')}</div>`;
  const row=t=>{
    const k=KIND[t.kind],who=t.who!=null?sh.team[t.who]?.name:'';
    let right='';
    if(t.st==='q')right=pick===t.i?'<span class="pm-tag sel">👆 Chọn người</span>':'';
    else if(t.st==='w')right=`<span class="pm-tag">⏳ ${esc(who)}</span>`;
    else if(t.st==='d')right=`<span class="pm-check">${cmd('✅','pm_check',{task:t.i,ok:true},'small',busy)}${cmd('↩️','pm_check',{task:t.i,ok:false},'small ghost',busy)}</span>`;
    else right=`<span class="pm-tag ${t.st==='ok'?'good':''}">${t.st==='ok'?'✅':'☑️'}</span>`;
    const body=`<span class="pm-kind" aria-hidden="true">${k[0]}</span><span class="pm-job"><b>${esc(t.t)}</b>${t.st==='d'?`<small class="pm-res${t.bad?' bad':''}">${esc(t.res)} · ${esc(who)}</small>`:t.k?`<small>${esc(t.k)}</small>`:''}</span>`;
    return t.st==='q'?`<li class="pm-row${pick===t.i?' picked':''}"><button type="button" class="pm-pick" data-action="pmPick" data-i="${t.i}"${busy?' disabled':''}>${body}</button>${right}</li>`:`<li class="pm-row st-${t.st}">${body}${right}</li>`;
  };
  const order={d:0,q:1,w:2,ok:3,meh:3},jobs=[...sh.tasks].sort((a,b)=>order[a.st]-order[b.st]||a.i-b.i);
  const crisis=busy?`<article class="pm-card pm-esc" role="alertdialog" aria-label="Gỡ rối"><p class="pm-q">${esc(esc_.text)}</p><div class="pm-opts">${esc_.options.map(o=>cmd(esc(o.label),'pm_fix',{option:o.id},'pm-opt')).join('')}</div></article>`:'';
  const left=sh.tasks.filter(t=>t.st==='q'||t.st==='w'||t.st==='d').length,working=sh.tasks.some(t=>t.st==='w');
  const line=busy?'Gỡ rối trước đã':pick!=null?'Chọn người làm việc này':sh.tasks.some(t=>t.st==='d')?'Kiểm việc: ✅ hay ↩️':left?'Chạm một việc để giao':'Xong hết rồi!';
  const foot=`<footer class="sheet-foot"><p>⭐ ${sh.pts}</p><div class="row wrap">${cmd('⏳ Chờ','pm_wait',{},'ghost',busy||!working)}${cmd('Chốt ca','pm_close',{},left?'ghost':'primary',busy)}</div></footer>`;
  return head('🧑‍💼 Ca quản lý',line,eyebrow)+`<div class="sheet-body pm-board">${crisis}${team}<ul class="pm-jobs">${jobs.map(row).join('')}</ul>
    <details class="pm-more"><summary>Xem thêm</summary><ul class="pm-rules"><li>Giao đúng sở trường (ô xanh): nhanh và ít lỗi.</li><li>Việc trả về có ⚠️: bấm ↩️ để làm lại, được thêm điểm.</li><li>Việc ổn mà trả về: mất thời gian, đội buồn.</li><li>Thưởng = 2 xu × điểm ⭐ (có trần).</li></ul></details></div>`+foot;
}

/** The day summary's line (summaryView). */
export function promoSummary(p,career){
  const bits=[];
  if(p.manager)bits.push(`🧑‍💼 Ca quản lý: ${p.manager.good}/${p.manager.size} việc tốt · +${p.manager.bonus} xu`);
  if(p.tip)bits.push(`🎖️ ${esc(T(career,'tip'))} +${p.tip} xu`);
  if(p.org)bits.push(...p.org.map(esc));   // 🎖️ cấp bậc (game/org.py): warnings, evaluation, a step, a course
  if(p.office){bits.push(...(p.office.lines||[]).map(esc));if(p.office.bonus)bits.push(`🏢 Thưởng điều hành +${p.office.bonus} xu`);}
  if(p.line)bits.push(esc(p.line));
  else if(p.next){
    bits.push(`🎖️ ${p.good?'Ngày tốt!':'Hôm nay chưa đạt ngày tốt.'} ${p.next.good}/${p.next.need} → ${esc(p.next.title)}`);
    const blockers=p.next.requirements?.filter(r=>!r.met)||[];
    if(blockers.length)bits.push(...blockers.map(r=>`🔒 ${esc(r.label)}`));
    else if(!p.next.requirements){
      if(p.next.why)bits.push(`🔒 ${esc(p.next.why)}`);
      if(p.next.wait)bits.push(`Hẹn xét lại sau ${p.next.wait} ngày làm`);
    }
  }
  return bits.length?`<div class="notice ${p.line?'success':''}">${icon('star',17)}<div>${bits.map(b=>`<p>${b}</p>`).join('')}${p.line||p.next?`<button type="button" class="btn small" data-action="promo">🎖️ Xem</button>`:''}</div></div>`:'';
}

export async function promoAction(action,data,el,env){
  const {ui,cmd:send,openSheet,toast,renderSheet}=env;
  if(action==='promo'){openSheet('promo');return true;}
  if(action==='pmAnswer'||action==='pmAsk'){   // the review: the generic command, plus the reason when it is put off (#11)
    const r=await send(action==='pmAnswer'?'pm_answer':'pm_ask',action==='pmAnswer'?{question:data.question,option:data.option}:{ask:data.ask});
    if(r?.later&&r.review)ui.pmLast={...r.review,career:env.api.state.current};else if(r?.celebrate)ui.pmLast=null;
    renderSheet();return true;
  }
  if(action==='pmBoard'){ui.pmPick=null;ui.pmOffice=false;openSheet('manager');return true;}
  if(action==='pmStart'){const r=await send('start_day',{manager:true});if(r){ui.pmPick=null;ui.pmOffice=false;ui.task=null;openSheet('manager');}return true;}
  if(action==='pmOffice'){ui.pmOffice=true;ui.pmOfSlot=null;ui.pmOfWho=null;ui.pmOfTab=null;openSheet('manager');return true;}
  if(action==='pmOfTab'){ui.pmOfTab=data.tab;ui.pmOfSlot=null;ui.pmOfWho=null;renderSheet();return true;}
  if(action==='pmOfSlot'){const i=Number(data.i);ui.pmOfSlot=ui.pmOfSlot===i?null:i;ui.pmOfTab='plan';renderSheet();return true;}
  if(action==='pmOfWho'){const i=Number(data.i);ui.pmOfWho=ui.pmOfWho===i?null:i;ui.pmOfTab='staff';renderSheet();return true;}
  if(action==='pmOfMate'){const slot=Number(data.slot);if(await send('pm_of_plan',{slot,mate:Number(data.i)}))ui.pmOfSlot=null;renderSheet();return true;}
  if(action==='pmPick'){const i=Number(data.i);ui.pmPick=ui.pmPick===i?null:i;renderSheet();return true;}
  if(action==='pmMate'){
    if(!Number.isInteger(ui.pmPick)){toast('Chạm một việc trước nhé.','hint');return true;}
    const task=ui.pmPick;ui.pmPick=null;
    if(!await send('pm_assign',{task,mate:Number(data.i)}))ui.pmPick=task;
    renderSheet();return true;
  }
  return false;
}
