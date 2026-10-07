/** Công an phường — a day shift at Công an phường Mây (server: game/careers/police.py).
 * The morning briefing (read the duty book, choose what goes first), the residence desk (an envelope, a "relative up
 * at the district" or a hurry first; then each paper, accept or name the paper to bring), lost and found (count with the
 * finder, ask the claimant, give or keep), mediation (hear each side, propose terms, both sides decide from hidden
 * traits, sign or refer), a lost child (calm, ask, the name tag, announce, verify whoever comes), patrols (look, then a
 * reminder, a report or making it safe), scam talks (the invitation, topics, the audience's questions) and the duty
 * phone (call back, priority card, dispatch). The awkward people of the ward answer through the air crew's encounter
 * card (air_kit.js oddCard); the duty book is written at the end of the shift from what really happened.
 * The server decides everything; hints show the next step, never which way a decision should go. */
import {stepRows,nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {data,cc,act,pane,introCard,deskCard,dayBar,askCard,bottom,kitActions,tip,clean} from './street_kit.js';
import {oddCard,restCard,record,ACTIONS as oddActions} from './air_kit.js';
import {whyAttrs} from '../ui-kit.js';
import {boardSVG} from '../v4/insignia.js';   // 🎖️ cấp hiệu (game/org.py)

const ODD_CFG={odd:'cap_odd',rest:'cap_rest',kinds:{charm:'Lời mời khó từ chối',harass:'Quấy rối',demand:'Yêu cầu oái oăm',corner:'Làm tắt',bargain:'Mặc cả với phường'},
  rest_to:[['self','Gửi anh Định'],['company','Nhờ công đoàn']]};
const pay=t=>({task:t.id});
/** A choice; on the clean layout its explanation (`sub`) is in the "?" sheet. */
const opt=(x,label,sub,cmd,payload,cls='')=>x.cmd(`<span class="sk-opt-label">${label}</span>${sub?(clean()?tip(x.esc(sub),label.replace(/<[^>]+>/g,'')):`<small>${x.esc(sub)}</small>`):''}`,cmd,payload,`sk-opt ${cls}`);
/** The order of choices turns with the task (and the scene): the right way is not always on top. */
const turn=(list,seed)=>{if(!list.length)return list;const k=[...String(seed)].reduce((n,ch)=>n+ch.charCodeAt(0),0)%list.length;return [...list.slice(k),...list.slice(0,k)];};
const seenHas=(t,k)=>(t.seen||[]).includes(k);

/* ------------------------------------------------------------ shared pieces */
function learnNote(x){
  const l=data(x).learn;if(!l?.on)return '';
  if(clean())return `<p class="cap-learn" aria-label="Anh Định kèm: việc ${Math.min(l.n+1,l.of)}/${l.of}">👮 ${Math.min(l.n+1,l.of)}/${l.of}${l.point?' · 👉 có mục gấp':''}</p>${tip(`Anh Định đứng cạnh kèm bạn: việc ${Math.min(l.n+1,l.of)}/${l.of}. Sai gì anh nhắc trước.`,'Học nghề','p')}`;
  return `<p class="cap-learn">👮 Anh Định đứng cạnh kèm bạn: việc ${Math.min(l.n+1,l.of)}/${l.of}. Sai gì anh nhắc trước.${l.point?' Anh chỉ vào một mục trong sổ: “Chuyện này có người đang cần mình ngay.”':''}</p>`;
}
function groundCard(x){
  const cd=data(x).odd?.conduct||{};if(!cd.ground)return '';
  return `<section class="cap-ground" role="status"><h3>⚖️ ${cd.demoted?'Bị hạ bậc, tạm dừng nhiệm vụ hôm nay':'Tạm dừng nhiệm vụ hôm nay'}</h3><p class="small">Mai lên Ban chỉ huy giải trình. Hôm nay tan ca sớm.</p>${x.button('Tan ca','end',{},'primary')}</section>`;
}
function wardStep(x){
  const o=data(x).odd||{};
  if(o.ev)return {ok:null,label:`Trả lời: ${o.ev.title}`,go:{sel:'.air-odd',label:'💬 Trả lời'},pulse:''};
  if(o.conduct?.ground)return {ok:null,label:'Tạm dừng nhiệm vụ: tan ca',go:{sel:'.cap-ground',label:'⚖️ Tan ca'},pulse:''};
  return null;
}
const waitBar=t=>`<div class="patience" title="Kiên nhẫn"><div class="bar ${t.patience<50?'low':''}"><i style="width:${t.patience}%"></i></div><small>${t.patience}%</small></div>`;
/** Who is in front of you: the resident at the desk, or the two neighbours of a dispute (not the colleague who sent them). */
function caseCard(t,x){
  const n=t.needs||{};
  if(t.kind==='desk')return `<article class="card sk-ticket cap-who"><div class="row"><span class="cap-big" aria-hidden="true">${x.esc(n.emoji)}</span><div class="grow"><h3>${x.esc(n.who)}</h3>${clean()?tip(x.esc(n.role),n.who,'p'):`<p class="small muted">${x.esc(n.role)}</p>`}<p class="small">${x.esc(String(t.opening||'').split('): ').slice(1).join('): '))}</p>${waitBar(t)}</div></div></article>`;
  return `<article class="card sk-ticket cap-who"><div class="row"><span class="cap-big" aria-hidden="true">${x.esc(n.emoji)}</span><div class="grow"><h3>${x.esc(n.title)}</h3><p class="small">${x.esc(t.opening)}</p>${waitBar(t)}</div></div></article>`;
}
/* ------------------------------------------------------------ 🎖️ cấp bậc: the rank line, an envelope, owning up */
function rankBar(x){
  const o=x.room.promo?.org;if(!o)return '';
  const own=o.own?x.cmd('🙇 Tự giác nộp lại','pm_org_own',{},'small primary'):'';
  // Clean layout (few words): the board and ⚠️ n/3 only, the name is the board's label; a tap opens the rank card.
  const name=clean()?'':`<b>${x.esc(o.grade.name)}</b>`;
  return `<div class="cap-rank" role="status"><button type="button" class="cap-rank-go" data-action="promo" aria-label="${x.esc(o.title)}">${boardSVG(o.grade.ins,40,o.grade.name)}${name}<span class="og-warn${o.warns.length?' on':''}">⚠️ ${o.warns.length}/${o.warn_max}</span></button>${o.susp?`<span class="bad">⛔ ${o.susp}</span>`:''}${own}</div>`;
}
function beatCard(t,x){
  const b=(data(x).beat?.offers||[]).find(o=>o.t===t.id&&!o.a);if(!b)return '';
  return `<section class="sk-event tense cap-beat" role="alertdialog" aria-label="Phong bì"><div class="sk-ev-head"><span aria-hidden="true">${x.esc(b.emoji)}</span><div><small>${x.esc(b.who)}</small><h3>Phong bì</h3></div></div><p>${x.esc(b.text)}</p>
    <div class="sk-opts">${turn(b.options,t.id).map(o=>opt(x,x.esc(o.label),'','cap_beat',{task:t.id,choice:o.id})).join('')}</div></section>`;
}
const said=(e,who,text)=>`<p class="cap-said"><span aria-hidden="true">${e}</span><span><b>${who}</b> ${text}</span></p>`;

/* ------------------------------------------------------------ the briefing */
/** Clean layout: the duty book's topics in a word or two, and each entry in a few words that keep what decides
 * which job goes first (who needs you, by when). Not listed: in full. */
const BRIEF_WORD={'Cuộc gọi của bà Năm':'Bà Năm','Karaoke tổ 5':'Karaoke','Ví nhặt được ở chợ':'Ví ở chợ','Cổng trường Tiểu học Mây':'Cổng trường'};
const briefName=e=>clean()&&BRIEF_WORD[e.name]||e.name;
const BRIEF_SHORT=[[/cán bộ điều tra/,'Bà Năm bị “cán bộ điều tra” giục chuyển tiền 8:30, gọi lại không nghe'],[/Tổ 3 xin/,'Tổ 3 xin buổi nói chuyện lừa đảo, chưa hẹn ngày'],
  [/tự xử/,'Karaoke tới 0:30, chị Mận dọa “tự xử”; 8:00 hai bên lên phường'],[/tắt lúc 21:45/,'Karaoke tắt 21:45, không ai phản ánh'],
  [/mẹ nhập viện/,'Ví có giấy tờ; chủ ví cần trước 9:00 để mẹ nhập viện'],[/Tủ đồ thất lạc/,'Tủ đồ thất lạc: mũ, dù, chưa ai nhận'],
  [/suýt bị xe máy quẹt/,'Cổng trường tắc, bé lớp 1 suýt bị quẹt; xin người đứng 7:00'],[/đông nhưng thông/,'Cổng trường hôm qua đông nhưng thông']];
const briefText=s=>{if(!clean())return s;const m=BRIEF_SHORT.find(([re])=>re.test(s||''));return m?m[1]:s;};
function briefPanel(t,x){
  const c=clean(),es=t.needs?.entries||[];
  const rows=es.map(e=>`<li class="${e.text?'read':''}">${e.text?`<b>${x.esc(e.emoji)} ${x.esc(briefName(e))}</b><p>${x.esc(briefText(e.text))}</p>${c&&briefText(e.text)!==e.text?tip(x.esc(e.text),e.name,'p'):''}`
    :x.cmd(`<b>${x.esc(e.emoji)} ${x.esc(briefName(e))}</b><small>📖${c?'':' Đọc mục này'}</small>`,'cap_read',{task:t.id,entry:e.id},'cap-note').replace('<button ',`<button aria-label="Đọc mục này: ${x.esc(e.name)}" `)}</li>`).join('');
  const first=x.ui.first?.[t.id];
  const picks=es.map(e=>act(x,`${x.esc(e.emoji)} ${x.esc(briefName(e))}`,'pickFirst',{task:t.id,v:e.id},`cap-pick${first===e.id?' on':''}`,` aria-pressed="${first===e.id}" aria-label="Làm trước: ${x.esc(e.name)}"`)).join('');
  // Clean layout: the choice waits behind one line until the book is read (or a pick is made), then opens by itself.
  if(c)return `<section class="card cap-book"><h4>📒 Sổ trực ban</h4><ul class="cap-notes">${rows}</ul></section>
    <section class="card cap-first">${pane(x,`first-${t.id}`,'🚶 <b>Làm trước</b>',`<div class="cap-picks">${picks}</div>`,!es.some(e=>!e.text)||!!first)}</section>`;
  return `<section class="card cap-book"><h4>📒 Sổ trực ban đêm qua</h4><ul class="cap-notes">${rows}</ul></section>
    <section class="card cap-first"><h4>🚶 Làm trước</h4><div class="cap-picks">${picks}</div></section>`;
}
function briefSteps(t,x){
  const es=t.needs?.entries||[],next=es.find(e=>!e.text),first=x.ui.first?.[t.id];
  return [{ok:!next||null,label:'Đọc từng mục sổ trực ban',note:`${es.filter(e=>e.text).length}/${es.length}`,go:next?{cmd:'cap_read',payload:{task:t.id,entry:next.id},label:`📖 Đọc: ${x.esc(briefName(next))}`}:null},
    {ok:first?true:null,label:'Chọn việc làm trước',go:{sel:'.cap-first',label:'🚶 Chọn việc làm trước'},pulse:data(x).learn?.point?`.cap-pick[data-v="${data(x).learn.point}"]`:''}];
}

/* ------------------------------------------------------------ the residence desk */
function deskPanel(t,x){
  const n=t.needs||{},docs=cc(x).docs||{},pr=n.pressure;
  let out='';
  if(pr&&!pr.answered){
    const opts=turn(pr.options,t.id).map(o=>opt(x,x.esc(o.label),'','cap_press',{task:t.id,choice:o.id})).join('');
    out+=`<section class="sk-event tense cap-press"><div class="sk-ev-head"><span aria-hidden="true">${x.esc(pr.emoji)}</span><div><small>Trước khi xem hồ sơ</small><h3>${x.esc(pr.title)}</h3></div></div><p>${x.esc(pr.text)}</p><div class="sk-opts">${opts}</div></section>`;
  }
  const rows=(n.docs||[]).map(k=>{const [e,label]=docs[k]||['📄',k];const txt=(n.checks||{})[k];
    return txt!=null?`<li class="seen ${n.ok?.[k]?'ok':'bad'}"><b>${x.esc(e)} ${x.esc(label)}</b><span>${x.esc(txt)}</span></li>`
      :`<li>${x.cmd(`${x.esc(e)} ${clean()?x.esc(label):`Xem ${x.esc(label.toLowerCase())}`}`,'cap_doc',{task:t.id,doc:k},'ghost cap-check',!!(pr&&!pr.answered)).replace('<button ',`<button aria-label="Xem ${x.esc(label.toLowerCase())}" `)}</li>`;}).join('');
  out+=`<section class="card cap-docs"><h4>🗂️ ${clean()?'Hồ sơ tạm trú':'Hồ sơ khai báo tạm trú'}</h4><ul class="cap-checklist">${rows}</ul></section>`;
  const back=(n.docs||[]).map(k=>opt(x,`📄 Thiếu, sai: ${x.esc((docs[k]||['',k])[1].toLowerCase())}`,(cc(x).back_line||{})[k]||'','cap_back',{task:t.id,doc:k})).join('');
  const locked=pr&&!pr.answered;
  out+=`<section class="card cap-decide"><h4>⚖️ Quyết định</h4>${locked?'<p class="small muted">Trả lời người khai trước đã.</p>':`<div class="sk-opts">${opt(x,'🗂️ Nhận hồ sơ','đủ giấy, hẹn giờ trả','cap_accept',pay(t),'cap-accept')}</div>${pane(x,`back-${t.id}`,'📄 Hướng dẫn bổ sung…',`<div class="sk-opts">${back}</div>`,false,'cap-back')}`}</section>`;
  return out;
}
function deskSteps(t,x){
  const n=t.needs||{},rows=[],docs=cc(x).docs||{};
  if(n.pressure)rows.push({ok:n.pressure.answered?true:null,label:`Trả lời: ${n.pressure.title}`,go:{sel:'.cap-press',label:`${x.esc(n.pressure.emoji)} Trả lời người khai`},pulse:''});
  for(const k of n.docs||[]){const [e,label]=docs[k]||['📄',k];rows.push({ok:(n.checks||{})[k]!=null||null,label:`Xem ${label.toLowerCase()}`,go:n.pressure&&!n.pressure.answered?null:{cmd:'cap_doc',payload:{task:t.id,doc:k},label:`${x.esc(e)} Xem ${x.esc(label.toLowerCase())}`}});}
  rows.push({ok:null,label:'Nhận hồ sơ hoặc hướng dẫn bổ sung',go:{sel:'.cap-decide',label:'⚖️ Quyết định'},pulse:''});
  return rows;
}

/* ------------------------------------------------------------ lost and found */
function lostPanel(t,x){
  const n=t.needs||{},qs=cc(x).lost_q||{};
  let out=`<section class="card cap-item"><div class="row"><span class="cap-big" aria-hidden="true">${x.esc(n.emoji)}</span><div class="grow"><h4>${x.esc(n.item)}</h4><p class="small muted">${x.esc(n.finder)} nộp · ${x.esc(n.found)}</p></div></div>
    ${n.truth?`<dl class="cap-kv"><dt>Hình dáng</dt><dd>${x.esc(n.truth.color)}</dd><dt>Bên trong</dt><dd>${x.esc(n.truth.inside)}</dd><dt>Nhặt ở</dt><dd>${x.esc(n.truth.where)}</dd></dl><p class="tag green">🧾 Đã ký biên bản${clean()?'':' tiếp nhận'}</p>`
      :x.cmd(clean()?'🧾 Kiểm đếm, ký biên bản':'🧾 Kiểm đếm cùng người nhặt, ký biên bản','cap_count',pay(t),'primary full cap-count')}</section>`;
  if(n.who){
    const asked=n.says||{};
    const chips=Object.entries(qs).map(([k,[e,label]])=>asked[k]!=null?said(x.esc(e),x.esc(label)+':',x.esc(asked[k])):x.cmd(`${x.esc(e)} ${x.esc(label)}`,'cap_lq',{task:t.id,q:k},'ghost small cap-q')).join('');
    out+=`<section class="card cap-claim"><h4>${x.esc(n.who_emoji)} ${x.esc(n.who)} tới xin nhận lại</h4><div class="cap-qs">${chips}</div></section>
      <section class="card cap-decide"><h4>⚖️ Quyết định</h4><div class="sk-opts">${turn([opt(x,'✅ Trả lại, ký nhận','khớp với biên bản','cap_give',pay(t)),opt(x,'🔒 Chưa trả','hẹn mang giấy tờ, chứng minh','cap_keep',pay(t))],t.id).join('')}</div></section>`;
  }
  return out;
}
function lostSteps(t,x){
  const n=t.needs||{},asked=Object.keys(n.says||{}).length;
  return [{ok:n.truth?true:null,label:'Kiểm đếm, ký biên bản',go:{cmd:'cap_count',payload:pay(t),label:'🧾 Kiểm đếm, ký biên bản'}},
    {ok:asked>=2||null,label:'Hỏi người tới nhận (ít nhất hai câu)',note:`${asked}`,go:n.who?{sel:'.cap-claim',label:'❓ Hỏi người tới nhận'}:null,pulse:''},
    {ok:null,label:'Trả lại hoặc chưa trả',go:n.who?{sel:'.cap-decide',label:'⚖️ Quyết định'}:null,pulse:''}];
}

/* ------------------------------------------------------------ mediation */
function termsOf(t,x){
  const n=t.needs||{},cur=(x.ui.terms??={})[t.id]??={};
  for(const tm of n.terms||[])if(cur[tm.id]==null)cur[tm.id]=Math.floor((tm.options.length-1)/2);
  return cur;
}
function disputePanel(t,x){
  const n=t.needs||{},heard=n.heard||{};
  const side=k=>{const s=n[k]||{};return `<article class="card cap-side side-${k}"><div class="row"><span class="cap-big" aria-hidden="true">${x.esc(s.emoji)}</span><div class="grow"><h4>${x.esc(s.name)}</h4><p class="small">${x.esc(s.say)}</p></div></div>
    ${heard[k]?`<p class="cap-heard">👂 ${x.esc(heard[k])}</p>`:x.cmd(`👂 Nghe riêng ${x.esc(s.name)}`,'cap_hear',{task:t.id,side:k},'ghost full cap-hear')}</article>`;};
  let out=`<div class="cap-sides">${side('a')}${side('b')}</div>`;
  const offers=(n.offers||[]).map((o,i)=>`<li><b>Lần ${i+1}:</b> ${(n.terms||[]).map(tm=>x.esc(tm.options[o.terms[tm.id]])).join(' · ')} <span class="tag ${o.a?'green':'danger'}">${x.esc(n.a.name)} ${o.a?'✓':'✗'}</span> <span class="tag ${o.b?'green':'danger'}">${x.esc(n.b.name)} ${o.b?'✓':'✗'}</span></li>`).join('');
  if(offers)out+=`<section class="card cap-offers"><h4>📝 Các lần đề xuất</h4><ul>${offers}</ul></section>`;
  if(n.deal){out+=`<p class="tag green cap-deal">🤝 Hai bên đã đồng ý. Ký biên bản hòa giải.</p>`;return out;}
  const cur=termsOf(t,x);
  const rows=(n.terms||[]).map(tm=>`<div class="cap-term"><small>${x.esc(tm.label)}</small><div class="cap-segs" role="group" aria-label="${x.esc(tm.label)}">${tm.options.map((o,i)=>act(x,x.esc(o),'term',{task:t.id,term:tm.id,v:i},`cap-seg${cur[tm.id]===i?' on':''}`,` aria-pressed="${cur[tm.id]===i}"`)).join('')}</div></div>`).join('');
  const left=n.left??0;
  out+=`<section class="card cap-propose"><h4>🤝 ${clean()?'Đề xuất':'Đề xuất của bạn'} <small class="muted">· còn ${left}${clean()?'':' lần'}</small></h4>${rows}
    ${x.cmd(clean()?'📝 Đề xuất':'📝 Đề xuất với hai bên','cap_offer',{task:t.id,terms:cur},'primary full cap-offer',left<=0)}
    ${pane(x,`dp-more-${t.id}`,'Cách khác…',`<div class="sk-opts">${n.threat?'':opt(x,'😤 Dọa phạt cả hai cho xong','“không chịu thì phạt hết”','cap_threat',pay(t))}${x.confirmCmd('<span class="sk-opt-label">📅 Chuyển tổ hòa giải, hẹn buổi sau</span>','cap_refer',pay(t),'Chuyển tổ hòa giải, hẹn hai nhà buổi sau?','sk-opt')}</div>`,false,'cap-more')}</section>`;
  return out;
}
function disputeSteps(t,x){
  const n=t.needs||{},h=n.heard||{};
  return [{ok:h.a?true:null,label:`Nghe ${n.a?.name||''}`,go:{cmd:'cap_hear',payload:{task:t.id,side:'a'},label:`👂 Nghe ${x.esc(n.a?.name||'')}`}},
    {ok:h.b?true:null,label:`Nghe ${n.b?.name||''}`,go:{cmd:'cap_hear',payload:{task:t.id,side:'b'},label:`👂 Nghe ${x.esc(n.b?.name||'')}`}},
    {ok:n.deal?true:null,label:'Đề xuất để hai bên cùng đồng ý',note:(n.offers||[]).length?`${(n.offers||[]).length}/${cc(x).max_offers||3}`:'',go:n.deal?null:{sel:'.cap-propose',label:'🤝 Đề xuất'},pulse:''}];
}

/* ------------------------------------------------------------ lost children */
function childPanel(t,x){
  const n=t.needs||{},C=cc(x);
  let out=`<section class="card cap-kid"><div class="row"><span class="cap-big" aria-hidden="true">${x.esc(n.emoji)}</span><div class="grow"><h4>${x.esc(n.kid)} · ${x.esc(n.age)}</h4><p class="small muted">${x.esc(n.found)}</p></div></div>
    ${n.calm?`<p class="tag green">🧸 Bé đã bình tĩnh${clean()?'':', đứng yên một chỗ dễ thấy'}</p>`:x.cmd(clean()?'🧸 Ngồi dỗ bé':'🧸 Ngồi xuống dỗ bé, đứng yên một chỗ','cap_calm',pay(t),'primary full cap-calm')}</section>`;
  const asks=n.asks||{};
  const qs=Object.entries(C.kid_q||{}).map(([k,[e,label]])=>asks[k]!=null?said(x.esc(e),'',x.esc(asks[k])):x.cmd(`${x.esc(e)} ${x.esc(label)}`,'cap_kq',{task:t.id,q:k},'ghost small cap-q')).join('');
  out+=`<section class="card cap-ask"><h4>🗣️ Hỏi bé</h4><div class="cap-qs">${qs}</div>${n.tag?`<p class="cap-tag">🎒 ${x.esc(n.tag)}</p>`:x.cmd('🎒 Xem balo, thẻ tên','cap_tag',pay(t),'ghost small cap-tagbtn')}</section>`;
  const ann=Object.entries(C.announce||{}).map(([k,[e,label]])=>(n.announced||[]).includes(k)?`<span class="tag ${k==='post'?'danger':'green'}">${x.esc(e)} ${x.esc(label)}</span>`
    :x.cmd(`<span class="sk-opt-label">${x.esc(e)} ${x.esc(label)}</span>`,'cap_announce',{task:t.id,how:k},'sk-opt',k==='call'&&!n.tag)).join('');
  out+=`<section class="card cap-find"><h4>📢 Tìm người nhà</h4><div class="sk-opts">${ann}</div></section>`;
  if(n.who){
    const says=n.says||{};
    const vs=Object.entries(C.verify||{}).map(([k,[e,label]])=>says[k]!=null?said(x.esc(e),'',x.esc(says[k])):x.cmd(`${x.esc(e)} ${x.esc(label)}`,'cap_verify',{task:t.id,q:k},'ghost small cap-q')).join('');
    out+=`<section class="card cap-claim"><h4>${x.esc(n.who_emoji)} ${x.esc(n.who)} tới đón bé</h4><div class="cap-qs">${vs}</div></section>
      <section class="card cap-decide"><h4>⚖️ Quyết định</h4><div class="sk-opts">${turn([opt(x,'🤝 Giao bé cho người nhà','đã xác minh','cap_handover',pay(t)),opt(x,'🏠 Giữ bé ở phường','gọi bố mẹ xác nhận','cap_hold',pay(t))],t.id).join('')}</div></section>`;
  }
  return out;
}
function childSteps(t,x){
  const n=t.needs||{},v=Object.keys(n.says||{}).length;
  return [{ok:n.calm||null,label:'Dỗ bé, đứng một chỗ',go:{cmd:'cap_calm',payload:pay(t),label:'🧸 Dỗ bé'}},
    {ok:Object.keys(n.asks||{}).length||n.tag?true:null,label:'Hỏi bé, xem thẻ tên',go:{sel:'.cap-ask',label:'🗣️ Hỏi bé'},pulse:''},
    {ok:(n.announced||[]).length?true:null,label:'Tìm người nhà',go:{sel:'.cap-find',label:'📢 Tìm người nhà'},pulse:''},
    {ok:v>=2||null,label:'Xác minh người đón (hai cách)',note:n.who?`${v}`:'',go:n.who?{sel:'.cap-claim',label:'🪪 Xác minh người đón'}:null,pulse:''},
    {ok:null,label:'Giao bé hoặc giữ lại',go:n.who?{sel:'.cap-decide',label:'⚖️ Quyết định'}:null,pulse:''}];
}

/* ------------------------------------------------------------ patrols */
function patrolPanel(t,x){
  const n=t.needs||{};
  const rule=pane(x,'cap-rule','📏 Quy tắc tuần tra phường Mây','<ul class="cap-rule"><li>💬 Lần đầu, chuyện nhỏ: nhắc nhở, hướng dẫn.</li><li>📝 Tái phạm hoặc gây nguy hiểm: lập biên bản.</li><li>🛑 Nguy hiểm trước mắt: làm cho an toàn trước.</li><li>✉️ Phong bì, chiếu bạc: không bao giờ.</li></ul><p class="small muted">Luật của trò chơi.</p>',false,'cap-rulebox');
  const cards=(n.scenes||[]).map((sc,i)=>{
    const done=sc.done,chosen=done?(sc.options||[]).find(o=>o.id===done):null;
    const opts=done?`<p class="cap-out">✔️ ${x.esc(chosen?.label||'')}<br><small>${x.esc(sc.outcome||'')}</small></p>`
      :`<div class="sk-opts">${turn(sc.options||[],t.id+i).map(o=>opt(x,x.esc(o.label),'','cap_act',{task:t.id,i,choice:o.id})).join('')}</div>`;
    return `<article class="card cap-scene${done?' done':''}"><div class="row"><span class="cap-big" aria-hidden="true">${x.esc(sc.emoji)}</span><p class="grow">${x.esc(sc.text)}</p></div>
      ${sc.look?`<p class="cap-look">🔍 ${x.esc(sc.look)}</p>`:done?'':x.cmd('🔍 Xem kỹ, hỏi chuyện','cap_look',{task:t.id,i},'ghost small cap-lookbtn')}${opts}</article>`;}).join('');
  return `<section class="cap-place"><h4>${x.esc(n.emoji)} ${x.esc(n.name)}</h4></section>${rule}<div class="cap-scenes">${cards}</div>`;
}
function patrolSteps(t,x){
  return (t.needs?.scenes||[]).map((sc,i)=>({ok:sc.done?true:null,label:sc.text.length>40?sc.text.slice(0,38)+'…':sc.text,
    go:sc.look?{sel:`.cap-scene:nth-child(${i+1}) .sk-opts`,label:'⚖️ Chọn cách xử lý'}:{cmd:'cap_look',payload:{task:t.id,i},label:`🔍 Xem kỹ chuyện ${i+1}`},pulse:''}));
}

/* ------------------------------------------------------------ scam talks */
function talkPanel(t,x){
  const n=t.needs||{},C=cc(x),chosen=t.topics||[];
  let out=`<section class="card cap-talk"><h4>🎤 ${x.esc(n.where)}</h4><p class="small muted">${x.esc(n.audience)}</p>
    ${n.invite?`<p class="cap-invite">✉️ ${x.esc(n.invite)}</p>`:x.cmd('✉️ Đọc thư mời','cap_invite',pay(t),'ghost full cap-invitebtn')}</section>`;
  if(!n.presented){
    const can=t.can?.cap_topic,why=w=>w?` ${whyAttrs(can).trim()}`:'';
    const chips=Object.entries(C.topics||{}).map(([k,[e,label]])=>{const off=!chosen.includes(k)&&can&&can!==true;
      return x.cmd(`${x.esc(e)} ${x.esc(label)}`,'cap_topic',{task:t.id,topic:k},`cap-topic${chosen.includes(k)?' on':''}${off?' is-why':''}`).replace('<button ',`<button${why(off)} `);}).join('');
    out+=`<section class="card cap-topics"><h4>🗂️ Chọn chủ đề <small class="muted">· ${chosen.length}/${C.topic_max||3}</small></h4><div class="cap-chips">${chips}</div></section>`;
    return out;
  }
  const qs=(n.questions||[]).map(q=>{const a=q.answered,opts=q.options||[];
    return `<article class="card cap-question${a?' done':''}"><p><b>${x.esc(q.who)}:</b> ${x.esc(q.text)}</p>${a?`<p class="cap-out">✔️ ${x.esc((opts.find(o=>o.id===a)||{}).label||'')}</p>`
      :`<div class="sk-opts">${turn(opts,t.id+q.id).map(o=>opt(x,x.esc(o.label),'','cap_answer',{task:t.id,q:q.id,option:o.id})).join('')}</div>`}</article>`;}).join('');
  return out+`<div class="cap-questions">${qs}</div>`;
}
function talkSteps(t,x){
  const n=t.needs||{};
  const rows=[{ok:n.invite?true:null,label:'Đọc thư mời',go:{cmd:'cap_invite',payload:pay(t),label:'✉️ Đọc thư mời'}},
    {ok:n.presented||(t.topics||[]).length?true:null,label:'Chọn chủ đề',go:{sel:'.cap-topics',label:'🗂️ Chọn chủ đề'},pulse:''}];
  for(const q of n.questions||[])rows.push({ok:q.answered?true:null,label:`Trả lời ${q.who}`,go:{sel:'.cap-question:not(.done) .sk-opts',label:`💬 Trả lời ${x.esc(q.who)}`},pulse:''});
  return rows;
}

/* ------------------------------------------------------------ the duty phone */
function callsPanel(t,x){
  const q=t.needs?.queue||[],C=cc(x),order=C.prio_order||[];
  const cards=q.map((c,i)=>{const got=(t.prio||{})[String(i)];
    const seg=order.map(k=>{const [e,name]=(C.prio||{})[k]||['',k];return x.cmd(`${e} ${x.esc(name)}`,'cap_prio',{task:t.id,i,prio:k},`cap-prio p-${k}${got===k?' on':''}`);}).join('');
    return `<article class="card cap-call${got?` got p-${got}`:''}"><div class="row"><span class="cap-big" aria-hidden="true">${x.esc(c.emoji)}</span><div class="grow"><b>${x.esc(c.who)}</b><p class="small">${x.esc(c.text)}</p></div></div>
      ${c.detail?`<p class="cap-look">📞 ${x.esc(c.detail)}</p>`:x.cmd('📞 Gọi lại hỏi rõ','cap_cb',{task:t.id,i},'ghost small cap-cbbtn')}<div class="cap-prios" role="group" aria-label="Mức ưu tiên">${seg}</div></article>`;}).join('');
  const scale=pane(x,'cap-scale','🚨 Thẻ ưu tiên tin báo',`<ul class="cap-rule">${order.map(k=>{const [e,name,when]=(C.prio||{})[k]||['',k,''];return `<li>${e} <b>${x.esc(name)}</b> · ${x.esc(when)}</li>`;}).join('')}</ul><p class="small muted">Ai đang gặp nguy thì đi trước. Luật của trò chơi.</p>`,false,'cap-scalebox');
  return `${scale}<div class="cap-calls">${cards}</div>`;
}
function callsSteps(t,x){
  return (t.needs?.queue||[]).map((c,i)=>({ok:(t.prio||{})[String(i)]?true:null,label:`Xếp: ${c.who}`,go:{sel:`.cap-call:nth-child(${i+1})`,label:`☎️ ${x.esc(c.who)}`},pulse:''}));
}

/* ------------------------------------------------------------ the end-of-shift duty book */
function logCard(x){
  const td=data(x).today||{},rows=td.facts||[];
  if(!rows.length)return '';
  if(td.log)return `<p class="tag ${td.log==='ok'?'green':td.log==='miss'?'amber':'danger'} cap-log-done">📒 ${td.log==='ok'?'Đã ghi sổ trực ban.':td.log==='miss'?'Đã ghi sổ trực ban (còn thiếu).':'Sổ trực ban có dòng ghi khống.'}</p>`;
  const pick=(x.ui.log??={})[td.day]||[];
  const lines=rows.map(r=>act(x,`<span>${pick.includes(r.id)?'☑️':'⬜'}</span> ${x.esc(r.text)}`,'logPick',{id:r.id,day:td.day},`cap-line${pick.includes(r.id)?' on':''}`,` aria-pressed="${pick.includes(r.id)}"`)).join('');
  return pane(x,`log-${td.day}`,`📒 Ghi sổ trực ban · ${rows.length} dòng`,`<p class="small muted">Chọn những gì thật sự đã xảy ra, đủ để ca sau theo dõi.</p><div class="cap-lines">${lines}</div>${x.cmd('📒 Ghi vào sổ trực ban','cap_log',{lines:pick},'primary full',!pick.length)}`,true,'cap-log');
}

/* ------------------------------------------------------------ the guide */
const STEPS={brief:briefSteps,desk:deskSteps,lost:lostSteps,dispute:disputeSteps,child:childSteps,patrol:patrolSteps,talk:talkSteps,calls:callsSteps};
const PANELS={brief:briefPanel,desk:deskPanel,lost:lostPanel,dispute:disputePanel,child:childPanel,patrol:patrolPanel,talk:talkPanel,calls:callsPanel};
function finalOf(t,x,steps){
  const n=t.needs||{};
  if(t.kind==='brief'){const f=x.ui.first?.[t.id];return {label:'📋 GIAO BAN XONG',go:f?finalGo(steps,'cap_first',{task:t.id,first:f}):null,ready:!!f,why:'chọn việc làm trước'};}
  if(t.kind==='dispute'&&n.deal)return {label:'🤝 KÝ BIÊN BẢN HÒA GIẢI',go:{cmd:'cap_sign',payload:pay(t)},ready:true};
  if(t.kind==='patrol'){const all=(n.scenes||[]).length&&(n.scenes||[]).every(s=>s.done);return {label:'🚶 XONG VÒNG TUẦN TRA',go:all?{cmd:'cap_endpatrol',payload:pay(t)}:null,ready:!!all,why:'xử lý đủ ba chuyện'};}
  if(t.kind==='talk'&&!n.presented){const k=(t.topics||[]).length;return {label:'🎤 TRÌNH BÀY',go:k?finalGo(steps,'cap_present',pay(t)):null,ready:!!k,why:'chọn ít nhất một chủ đề'};}
  if(t.kind==='calls'){const all=(n.queue||[]).length&&(n.queue||[]).every((_,i)=>(t.prio||{})[String(i)]);return {label:'🚨 ĐIỀU ĐỘNG',go:all?finalGo(steps,'cap_dispatch',pay(t)):null,ready:!!all,why:'xếp mức ưu tiên cho cả ba cuộc gọi'};}
  return null;
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở phường',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  const o=wardStep(x);if(o)return {steps:[o],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'cap_intro',payload:{},label:'👮 Vào ca thôi!'}}],final:null};
  if(t.kind!=='brief'&&!t.known)return {steps:[{ok:null,label:'Chào hỏi, nghe chuyện',go:{cmd:'ask',payload:pay(t),label:'👋 Chào hỏi, nghe chuyện'}}],final:null,pulse:'.sk-ask'};
  const steps=(STEPS[t.kind]||(()=>[]))(t,x);
  return {steps,final:finalOf(t,x,steps)};
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});
function top(x){return `${introCard(x,'cap_intro','👮')}${deskCard(x,'cap_desk','Chuyện ở phường')}${oddCard(x,ODD_CFG)}${groundCard(x)}`;}
const ASK_LABEL={desk:'👋 Mời ngồi, nhận hồ sơ',lost:'👋 Nhận đồ từ người nhặt',dispute:'👋 Mời hai bên ngồi',child:'🏃 Tới chỗ bé',patrol:'🚶 Bắt đầu tuần tra',talk:'👋 Tới nhà văn hóa',calls:'☎️ Nhấc máy'};

export default {
  id:'police',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='brief'?'Đọc sổ trực ban':!t.known?'Chào hỏi, nghe chuyện':'Làm tiếp';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x),head=top(x);
    if(d.desk?.ev||d.odd?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk cap">${hint}${head}${bottom(x,g)}</div>`;
    let main='',side='';
    if(t.kind!=='brief'&&!t.known)main=askCard(x,t,ASK_LABEL[t.kind]||'👋 Chào hỏi');
    else{
      const body=(PANELS[t.kind]||(()=>''))(t,x);
      main=beatCard(t,x)+(['desk','dispute'].includes(t.kind)?`${caseCard(t,x)}${body}`:body);
      side=stepRows(x,g.steps,t.kind==='brief'?'Giao ban':'Các bước',{chip:true});
    }
    return `<div class="career-job sk cap">${hint}${head}${learnNote(x)}${dayBar(x)}${rankBar(x)}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x),head=top(x);
    if(d.desk?.ev||d.odd?.ev||!d.intro||x.ui.intro){
      const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện ở phường',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}
        :d.odd?.ev?{steps:[wardStep(x)],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'cap_intro',payload:{},label:'👮 Vào ca thôi!'}}],final:null};
      return `<div class="career-job sk cap">${hintFor(g,x)}${head}${bottom(x,g)}</div>`;
    }
    const td=d.today||{};
    const tiles=[[td.tasks||0,'việc'],[td.helped||0,'lần giúp dân'],[td.reminders||0,'lần nhắc nhở'],[td.reports||0,'biên bản']];
    return `<div class="career-job sk cap">${head}${dayBar(x)}${rankBar(x)}<section class="card cap-today"><h4>👮 Ca hôm nay</h4><div class="cap-tiles">${tiles.map(([v,l])=>`<div><b>${x.esc(v)}</b><small>${x.esc(l)}</small></div>`).join('')}</div></section>
      ${logCard(x)}<section class="card cap-record"><h4>📁 Hồ sơ của bạn</h4>${record(x)}${restCard(x,ODD_CFG)}</section></div>`;
  },
  tick(root){keepBarAboveFooter(root);},
  actions:{...kitActions,...oddActions,
    async pickFirst(d,el,x){(x.ui.first??={})[d.task]=d.v;x.render();},
    async term(d,el,x){((x.ui.terms??={})[d.task]??={})[d.term]=Number(d.v);x.render();},
    async logPick(d,el,x){const b=((x.ui.log??={})[d.day]??=[]);const i=b.indexOf(d.id);if(i>=0)b.splice(i,1);else b.push(d.id);x.render();},
  },
};
