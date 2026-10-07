/** Điều dưỡng khoa Nội — a day shift at Bệnh viện phường Lá Sen (server: game/careers/nurse.py).
 * The handover book, vital signs (measure, chart by typing, the alarm card, report to the doctor), the medication
 * round (identity, allergy band, tray label, blood sugar, give or hold), call bells, triage at reception (Thẻ màu
 * Lá Sen), getting someone ready for a procedure (consent, fasting, jewellery) and going home (paper, cannula,
 * teaching, teach-back). The awkward people of the ward answer through the air crew's encounter card (air_kit.js
 * oddCard); the end-of-shift handover notes are written from what really happened.
 * The server decides everything; hints show the next step, never which way a decision should go. */
import {stepRows,nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {data,cc,act,tile,pane,introCard,deskCard,dayBar,person,askCard,bottom,kitActions,tip,clean} from './street_kit.js';
import {oddCard,restCard,record,ACTIONS as oddActions} from './air_kit.js';

const PATIENT=['vitals','med','bell','proc','discharge'];
const ODD_CFG={odd:'dd_odd',rest:'dd_rest',kinds:{charm:'Lời mời khó từ chối',harass:'Quấy rối',demand:'Yêu cầu oái oăm',corner:'Làm tắt',bargain:'Mặc cả với khoa'},
  rest_to:[['self','Gửi chị Hoa'],['company','Nhờ công đoàn']]};
const SIGN=(x,k)=>(cc(x).signs||{})[k]||{name:k,emoji:'•',unit:''};
const COLOR=(x,k)=>(cc(x).colors||{})[k]||['⚪',k,''];
const HOLD=(x,k)=>(cc(x).hold||{})[k]||k;
const pay=t=>({task:t.id});
/** The alarm card's limit as numbers ("từ 38,0 trở lên hoặc 35,5 trở xuống" → "≥38,0 · ≤35,5"); '' when it does not
 * read as numbers alone (then the card stays in its pane). Clean layout: shown on each sign's tile. */
export function limitOf(s){
  const out=String(s||'').replace(/^số trên\s+/,'').replace(/từ\s+([\d,]+)\s+trở lên/g,'≥$1').replace(/([\d,]+)\s+trở xuống/g,'≤$1')
    .replace(/trên\s+([\d,]+)/g,'>$1').replace(/dưới\s+([\d,]+)/g,'<$1').replace(/\s+hoặc\s+/g,' · ').trim();
  return /\p{L}/u.test(out)?'':out;
}
/** "Giường 3 · Trần Thị Tư" → "🛏️3 · Tư" (clean layout; the full name stays in aria-label). */
export const bedShort=name=>{const [b,n]=String(name||'').split('·').map(s=>s.trim());const no=(b||'').replace(/\D/g,'');return no&&n?`🛏️${no} · ${n.split(/\s+/).pop()}`:name;};

/* ------------------------------------------------------------ shared bedside pieces */
function patientCard(t,x){
  if(!t.known)return askCard(x,t,t.kind==='bell'?'🏃 Tới giường xem':'👋 Tới giường, chào người bệnh');
  const n=t.needs||{};
  const tags=[`<span class="tag blue">G${x.esc(n.bed)}</span>`,n.fall?'<span class="tag amber">⚠️ Nguy cơ té ngã</span>':''].join('');
  return person(x,t,`<p class="dd-dx">${x.esc(n.dx||'')}</p>`,`<span class="dd-tags">${tags}</span>`);
}
function handsRow(t,x){
  return t.washed?`<span class="tag green" aria-label="Đã sát khuẩn tay">🧴 ${clean()?'✓':'Đã sát khuẩn tay'}</span>`:x.cmd('🧴 Sát khuẩn tay','dd_wash',pay(t),'dd-wash');
}
function idPanel(t,x){
  const me=(t.needs||{}).me;
  if(me){
    const shown=me.name?`<b>${x.esc(me.name)}</b> · ${x.esc(me.dob)}<br><small>Vòng tay ${x.esc(me.band)} · ${x.esc(me.name)} · ${x.esc(me.dob)}</small>`:`<b>${x.esc(me.said||'')}</b><br><small>Chưa có họ tên, ngày sinh để đối chiếu.</small>`;
    return `<section class="card dd-id"><h4>🪪 Người bệnh</h4><p class="dd-me">${shown}</p></section>`;
  }
  const o=(how,label,sub)=>x.cmd(`<span class="sk-opt-label">${label}</span>${clean()?tip(sub,label.replace(/^\S+\s/,'')):`<small>${sub}</small>`}`,'dd_id',{task:t.id,how},'sk-opt');
  const opts=[o('open','🗣️ Mời tự nói họ tên, ngày sinh','rồi đối chiếu vòng tay'),o('name',`❓ “${x.esc(x.npc(t.npc).display_name)} phải không ạ?”`,'hỏi có hay không'),o('bed','🔢 Xem số giường','nhanh')];
  const k=[...t.id].reduce((n,ch)=>n+ch.charCodeAt(0),0)%3;   // the order turns with the task: the right way is not always on top
  return `<section class="card dd-id"><h4>🪪 Xác định người bệnh</h4><div class="sk-opts">${[...opts.slice(k),...opts.slice(0,k)].join('')}</div></section>`;
}
function bedside(t,x){return `<div class="dd-bedside">${handsRow(t,x)}</div>${idPanel(t,x)}`;}
function learnNote(x){
  const l=data(x).learn;if(!l?.on)return '';
  if(clean())return `<p class="dd-learn" aria-label="Chị Hoa kèm: việc ${Math.min(l.n+1,l.of)}/${l.of}">👩‍⚕️ ${Math.min(l.n+1,l.of)}/${l.of}</p>${tip(`Chị Hoa đứng cạnh kèm bạn: việc ${Math.min(l.n+1,l.of)}/${l.of}. Sai gì chị nhắc trước.`,'Học nghề','p')}`;
  return `<p class="dd-learn">👩‍⚕️ Chị Hoa đứng cạnh kèm bạn: việc ${Math.min(l.n+1,l.of)}/${l.of}. Sai gì chị nhắc trước.</p>`;
}
function groundCard(x){
  const cd=data(x).odd?.conduct||{};if(!cd.ground)return '';
  return `<section class="dd-ground" role="status"><h3>⚖️ ${cd.demoted?'Bị hạ bậc, tạm đình chỉ trực hôm nay':'Tạm đình chỉ trực hôm nay'}</h3><p class="small">Mai lên phòng Điều dưỡng trình bày. Hôm nay tan ca sớm.</p>${x.button('Tan ca','end',{},'primary')}</section>`;
}
/** Someone waiting for an answer (air_kit oddCard), or stood down for the day. */
function wardStep(x){
  const o=data(x).odd||{};
  if(o.ev)return {ok:null,label:`Trả lời: ${o.ev.title}`,go:{sel:'.air-odd',label:'💬 Trả lời'},pulse:''};
  if(o.conduct?.ground)return {ok:null,label:'Tạm đình chỉ trực: tan ca',go:{sel:'.dd-ground',label:'⚖️ Tan ca'},pulse:''};
  return null;
}
function holdPane(t,x,reasons,open=false){
  const rows=reasons.map(k=>x.cmd(`<span class="sk-opt-label">✋ ${x.esc(HOLD(x,k))}</span>`,'dd_hold',{task:t.id,reason:k},'sk-opt')).join('');
  return pane(x,`hold-${t.id}`,'✋ Giữ lại, báo bác sĩ…',`<div class="sk-opts">${rows}</div>`,open,'dd-hold');
}

/* ------------------------------------------------------------ the handover */
function shiftPanel(t,x){
  const notes=(t.needs||{}).notes||[],first=x.ui.first?.[t.id],c=clean();
  // Clean layout: an unread bed is "🛏️3 · Tư"; a read one keeps its diagnosis and the night's note (they decide who goes first).
  const rows=notes.map(n=>`<li class="${n.text?'read':''}">${n.text?`<b>${x.esc(n.name)}</b><small>${x.esc(n.dx)}</small><p>${x.esc(n.text)}</p>`
    :x.cmd(`<b>${x.esc(c?bedShort(n.name):n.name)}</b><small>📋${c?'':' Đọc ghi chú ca đêm'}</small>`,'dd_read',{task:t.id,bed:n.bed},'dd-note').replace('<button ',`<button aria-label="Đọc ghi chú ca đêm: ${x.esc(n.name)}" `)}</li>`).join('');
  const pick=notes.map(n=>act(x,`G${x.esc(n.name.split('·')[0].replace(/\D/g,''))}`,'pickFirst',{task:t.id,bed:n.bed},`dd-bedpick${first===n.bed?' on':''}`,` aria-pressed="${first===n.bed}"`)).join('');
  if(c)return `<section class="card dd-shift"><h4>📋 Sổ giao ca</h4><ul class="dd-notes">${rows}</ul></section>
    <section class="card dd-first">${pane(x,`first-${t.id}`,'🚶 <b>Giường xem trước</b>',`<div class="dd-picks">${pick}</div>`,!notes.some(n=>!n.text)||!!first)}</section>`;
  return `<section class="card dd-shift"><h4>📋 Sổ giao ca đêm qua</h4><ul class="dd-notes">${rows}</ul></section>
    <section class="card dd-first"><h4>🚶 Giường xem trước</h4><div class="dd-picks">${pick}</div></section>`;
}
function shiftSteps(t,x){
  const notes=(t.needs||{}).notes||[],next=notes.find(n=>!n.text),first=x.ui.first?.[t.id];
  return [{ok:!next||null,label:'Đọc ghi chú từng giường',note:`${notes.filter(n=>n.text).length}/${notes.length}`,go:next?{cmd:'dd_read',payload:{task:t.id,bed:next.bed},label:`📋 Đọc giường ${x.esc(next.name.split('·')[0].replace(/\D/g,''))}`}:null},
    {ok:first?true:null,label:'Chọn giường xem trước',go:{sel:'.dd-first',label:'🚶 Chọn giường xem trước'},pulse:''}];
}

/* ------------------------------------------------------------ vital signs */
function vitalsPanel(t,x){
  const n=t.needs||{},ids=cc(x).sign_ids||[],vals=n.vals||{},first=n.first||{},lim=k=>clean()?limitOf(SIGN(x,k).card):'';
  const tiles=ids.map(k=>{const s=SIGN(x,k),v=vals[k];
    if(v!=null){const again=first[k]!==v||(t.seen||[]).includes(`${k}2`),inner=`<span class="tile-emoji">${x.esc(s.emoji)}</span><b>${x.esc(v)}</b><small>${lim(k)?`${x.esc(s.unit)} · 🚨 ${x.esc(lim(k))}`:`${x.esc(s.name)} · ${x.esc(s.unit)}`}</small>${again?'<small class="dd-again">đã đo lại</small>':t.chart==null?'<small class="dd-again">🔁 đo lại</small>':''}`;
      const cls=`dd-sign done${(n.flags||[]).includes(k)?' bad':''}`;
      return t.chart==null&&!again?tile(x,'dd_recheck',{task:t.id,sign:k},inner,cls):`<div class="sk-tile ${cls}">${inner}</div>`;}
    return tile(x,'dd_measure',{task:t.id,sign:k},`<span class="tile-emoji">${x.esc(s.emoji)}</span><b>${x.esc(s.name)}</b>${lim(k)?`<small class="dd-lim">🚨 ${x.esc(lim(k))}</small>`:`<small>${k==='pain'?'hỏi điểm đau':'đo'}</small>`}`,'dd-sign');}).join('');
  // Clean layout: the alarm card's limits sit on each tile as numbers (they decide whether to call the doctor); its
  // sentence goes to the "?" sheet. A limit that does not read as numbers keeps the card on screen.
  const body=`<ul class="dd-card">${ids.map(k=>`<li>${x.esc(SIGN(x,k).emoji)} <b>${x.esc(SIGN(x,k).name)}</b> ${x.esc(SIGN(x,k).card)}</li>`).join('')}</ul>`;
  const card=clean()&&ids.every(k=>lim(k))?tip(x.esc(`${ids.map(k=>`${SIGN(x,k).name} ${SIGN(x,k).card}`).join('; ')}. Ngoài thẻ là báo bác sĩ (luật của trò chơi).`),'🚨 Thẻ báo động Lá Sen','p')
    :pane(x,'alarm-card','🚨 Thẻ báo động Lá Sen',`${body}<p class="small muted">Luật của trò chơi: ngoài thẻ là báo bác sĩ.</p>`,false,'dd-alarm');
  return `<section class="card dd-vitals"><h4>🩺 ${clean()?'Sinh tồn':'Đo dấu hiệu sinh tồn'}</h4><p class="small muted">${x.esc(n.look||'')}</p><div class="tile-grid dd-signs">${tiles}</div>${card}</section>${chartForm(t,x)}${callPanel(t,x)}`;
}
function chartForm(t,x){
  const ids=cc(x).sign_ids||[],n=t.needs||{},all=ids.every(k=>(n.vals||{})[k]!=null);
  if(t.chart){
    return `<section class="card dd-chart"><h4>📝 Phiếu theo dõi</h4><ul class="dd-chart-done">${ids.map(k=>`<li>${x.esc(SIGN(x,k).emoji)} ${x.esc(SIGN(x,k).name)}: <b>${x.esc(t.chart[k])}</b></li>`).join('')}</ul></section>`;
  }
  if(!all)return '';
  const typed=(x.ui.chart??={})[t.id]||{};
  const rows=ids.map(k=>`<label class="dd-field"><span>${x.esc(SIGN(x,k).emoji)} ${x.esc(SIGN(x,k).name)}</span><input name="${x.esc(k)}" inputmode="decimal" autocomplete="off" maxlength="12" value="${x.esc(typed[k]||'')}" data-dd-chart="${x.esc(k)}" placeholder="${k==='bp'?'120/80':''}"><small>${x.esc(SIGN(x,k).unit)}</small></label>`).join('');
  return `<form class="card dd-chart" data-dd-form="chart"><h4>📝 Ghi phiếu theo dõi</h4>${clean()?tip('Gõ đúng số vừa đo.','Phiếu theo dõi','p'):'<p class="small muted">Gõ đúng số vừa đo.</p>'}<div class="dd-fields">${rows}</div><button type="submit" class="btn primary full">📝 Ghi phiếu</button></form>`;
}
function callPanel(t,x){
  if(t.called?.length)return `<p class="tag green dd-called">📞 Đã báo bác sĩ: ${t.called.map(k=>x.esc(SIGN(x,k).name.toLowerCase())).join(', ')}</p>`;
  const n=t.needs||{},have=(cc(x).sign_ids||[]).filter(k=>(n.vals||{})[k]!=null);
  if(!have.length)return '';
  const pick=(x.ui.call??={})[t.id]||[];
  const chips=have.map(k=>act(x,`${x.esc(SIGN(x,k).emoji)} ${x.esc(SIGN(x,k).name)} ${x.esc(n.vals[k])}`,'callPick',{task:t.id,sign:k},`dd-chip${pick.includes(k)?' on':''}`,` aria-pressed="${pick.includes(k)}"`)).join('');
  return pane(x,`call-${t.id}`,'📞 Báo bác sĩ Khang…',`<p class="small muted">Chọn chỉ số muốn báo.</p><div class="dd-chips">${chips}</div>${x.cmd('📞 Gọi bác sĩ','dd_call',{task:t.id,signs:pick},'primary full dd-call',!pick.length)}`,false,'dd-callbox');
}
function vitalsSteps(t,x){
  const ids=cc(x).sign_ids||[],n=t.needs||{},rows=[];
  rows.push({ok:t.washed||null,label:'Sát khuẩn tay',go:{cmd:'dd_wash',payload:pay(t),label:'🧴 Sát khuẩn tay'}});
  rows.push({ok:n.me?true:null,label:'Xác định người bệnh',go:{sel:'.dd-id',label:'🪪 Xác định người bệnh'},pulse:''});
  const next=ids.find(k=>(n.vals||{})[k]==null);
  rows.push({ok:!next||null,label:'Đo đủ năm chỉ số',note:`${ids.length-ids.filter(k=>(n.vals||{})[k]==null).length}/${ids.length}`,
    go:next?{cmd:'dd_measure',payload:{task:t.id,sign:next},label:`${x.esc(SIGN(x,next).emoji)} Đo ${x.esc(SIGN(x,next).name.toLowerCase())}`}:null});
  rows.push({ok:t.chart?true:null,label:'Ghi phiếu theo dõi',go:{sel:'.dd-chart',label:'📝 Ghi phiếu theo dõi'},pulse:''});
  rows.push({ok:t.called?.length?true:null,label:'So thẻ báo động, báo bác sĩ nếu cần',go:{sel:clean()&&ids.every(k=>limitOf(SIGN(x,k).card))?'.dd-signs':'.dd-alarm',label:'🚨 So với thẻ báo động'},pulse:''});
  return rows;
}

/* ------------------------------------------------------------ medication */
function medPanel(t,x){
  const n=t.needs||{},o=n.order||{},refused=n.refuse;
  const order=`<section class="card dd-order"><h4>📄 Phiếu y lệnh</h4><dl class="kv"><dt>Người bệnh</dt><dd><b>${x.esc(o.name)}</b> · ${x.esc(o.dob)} · giường ${x.esc(o.bed)}</dd>
    <dt>Thuốc</dt><dd><b>${x.esc(o.drug)}</b></dd><dt>Đường dùng</dt><dd>${x.esc(o.route)}</dd><dt>Giờ</dt><dd>${x.esc(o.time)}</dd></dl>${o.rule?`<p class="dd-rule">📌 ${x.esc(o.rule)}</p>`:''}
    ${n.board?`<p class="dd-board">🪧 Biển đầu giường: <b>${x.esc(n.board)}</b></p>`:''}</section>`;
  const chk=(what,label,seen,shown)=>seen?`<li class="seen">${shown}</li>`:`<li>${x.cmd(label,'dd_check',{task:t.id,what},'ghost dd-check')}</li>`;
  const checks=`<section class="card dd-checks"><h4>🔍 Đối chiếu</h4><ul class="dd-checklist">
    ${chk('allergy','🔴 Xem vòng dị ứng',n.allergy!=null,n.allergy?`🔴 <b>${x.esc(n.allergy)}</b>`:'⚪ Không có vòng dị ứng')}
    ${chk('label','🏷️ Đọc nhãn khay khoa dược',n.tray!=null,`🏷️ Nhãn khay: <b>${x.esc(n.tray)}</b>`)}
    ${o.rule?chk('sugar','🩸 Đo đường huyết',n.sugar!=null,n.sugar==='low'?'🩸 Máy báo <b>THẤP</b>':'🩸 Trong ngưỡng'):''}</ul></section>`;
  const decide=refused?`<section class="sk-event tense dd-refuse"><div class="sk-ev-head"><span aria-hidden="true">🙅</span><div><small>Người bệnh từ chối</small><h3>${x.esc(refused)}</h3></div></div>
      <div class="sk-opts">${t.said==='refused'?x.cmd('<span class="sk-opt-label">🗣️ Hỏi vì sao, giải thích</span>','dd_explain',pay(t),'sk-opt'):''}
      ${x.cmd('<span class="sk-opt-label">😤 Ép uống cho xong</span><small>“không uống là nặng thêm đó”</small>','dd_push',pay(t),'sk-opt')}
      ${x.cmd(`<span class="sk-opt-label">✋ ${x.esc(HOLD(x,'refuse'))}, báo bác sĩ</span>`,'dd_hold',{task:t.id,reason:'refuse'},'sk-opt')}</div></section>`
    :`<section class="card dd-decide"><h4>⚖️ Quyết định</h4><div class="sk-opts">${x.cmd(`<span class="sk-opt-label">💊 Thực hiện y lệnh</span>${clean()?tip('cho thuốc, ký phiếu','Thực hiện y lệnh'):'<small>cho thuốc, ký phiếu</small>'}`,'dd_give',pay(t),'sk-opt dd-give')}</div>${holdPane(t,x,cc(x).med_hold||[])}</section>`;
  return order+checks+decide;
}
function medSteps(t,x){
  const n=t.needs||{},rows=[];
  rows.push({ok:t.washed||null,label:'Sát khuẩn tay',go:{cmd:'dd_wash',payload:pay(t),label:'🧴 Sát khuẩn tay'}});
  rows.push({ok:n.me?true:null,label:'Xác định người bệnh',go:{sel:'.dd-id',label:'🪪 Xác định người bệnh'},pulse:''});
  rows.push({ok:n.allergy!=null||null,label:'Xem vòng dị ứng',go:{cmd:'dd_check',payload:{task:t.id,what:'allergy'},label:'🔴 Xem vòng dị ứng'}});
  rows.push({ok:n.tray!=null||null,label:'Đọc nhãn khay',go:{cmd:'dd_check',payload:{task:t.id,what:'label'},label:'🏷️ Đọc nhãn khay'}});
  if(n.order?.rule)rows.push({ok:n.sugar!=null||null,label:'Đo đường huyết',go:{cmd:'dd_check',payload:{task:t.id,what:'sugar'},label:'🩸 Đo đường huyết'}});
  rows.push({ok:null,label:'Cho thuốc hoặc giữ lại',go:{sel:n.refuse?'.dd-refuse':'.dd-decide',label:'⚖️ Quyết định'},pulse:''});
  return rows;
}

/* ------------------------------------------------------------ call bells */
function bellPanel(t,x){
  const n=t.needs||{};
  const opts=(n.options||[]).map(o=>x.cmd(`<span class="sk-opt-label">${x.esc(o.label)}</span>`,'dd_bell',{task:t.id,choice:o.id},'sk-opt')).join('');
  return `<section class="sk-event dd-bell"><div class="sk-ev-head"><span aria-hidden="true">🔔</span><div><small>Giường ${x.esc(n.bed)}</small><h3>${x.esc(n.detail||'')}</h3></div></div><div class="sk-opts">${opts}</div></section>`;
}

/* ------------------------------------------------------------ triage */
function triagePanel(t,x){
  const q=(t.needs||{}).queue||[],order=cc(x).color_order||[];
  const cards=q.map((p,i)=>{const got=(t.colors||{})[String(i)];
    const btn=(what,label)=>p[what]?`<p class="dd-q"><span aria-hidden="true">${what==='ask'?'👂':'🩺'}</span> ${x.esc(p[what])}</p>`:x.cmd(label,'dd_tq',{task:t.id,i,what},'ghost small');
    const seg=order.map(c=>{const [e,name]=COLOR(x,c);return x.cmd(`${e} ${x.esc(name)}`,'dd_color',{task:t.id,i,color:c},`dd-color c-${c}${got===c?' on':''}`);}).join('');
    return `<article class="card dd-arrival${got?` got c-${got}`:''}"><div class="row"><span class="dd-av" aria-hidden="true">${x.esc(p.emoji)}</span><div class="grow"><b>${x.esc(p.who)}</b><p class="small">${x.esc(p.text)}</p></div></div>
      <div class="dd-qs">${btn('ask','👂 Hỏi')}${btn('quick','🩺 Đo nhanh')}</div><div class="dd-colors" role="group" aria-label="Thẻ màu">${seg}</div></article>`;}).join('');
  const scale=pane(x,'tri-scale','🚦 Thẻ màu Lá Sen',`<ul class="dd-card">${order.map(c=>{const [e,name,when]=COLOR(x,c);return `<li>${e} <b>${x.esc(name)}</b> · ${x.esc(when)}</li>`;}).join('')}</ul><p class="small muted">Xếp theo dấu hiệu, không theo tiếng la. Luật của trò chơi.</p>`,false,'dd-scale');
  return `${scale}<div class="dd-queue">${cards}</div>`;
}
function triageSteps(t,x){
  const q=(t.needs||{}).queue||[];
  return q.map((p,i)=>({ok:(t.colors||{})[String(i)]?true:null,label:`Thẻ màu: ${p.who}`,go:{sel:`.dd-arrival:nth-child(${i+1})`,label:`🚦 ${x.esc(p.who)}`},pulse:''}));
}

/* ------------------------------------------------------------ procedures */
function procPanel(t,x){
  const n=t.needs||{},ch=n.checks||{},checks=cc(x).proc_checks||{};
  const rows=Object.entries(checks).map(([k,[e,label]])=>ch[k]!=null?`<li class="seen">${x.esc(e)} <b>${x.esc(label)}:</b> ${x.esc(ch[k])}</li>`:`<li>${x.cmd(`${x.esc(e)} ${x.esc(label)}`,'dd_check',{task:t.id,what:k},'ghost dd-check')}</li>`).join('');
  const extra=[];
  const st=n.state||{};
  if(st.jewel&&!n.jewel_off)extra.push(x.cmd('<span class="sk-opt-label">💍 Tháo trang sức, giao người nhà</span>','dd_jewel',pay(t),'sk-opt'));
  if((st.consent==='unsigned'||st.consent==='withdrawn')&&!n.signed){
    if(!t.called?.length)extra.push(x.cmd('<span class="sk-opt-label">📞 Mời bác sĩ tới giải thích</span>','dd_call',{task:t.id,reason:'consent'},'sk-opt'));
    if(!n.explained)extra.push(x.cmd('<span class="sk-opt-label">🗣️ Hỏi điều người bệnh lo, giải thích</span>','dd_explain',pay(t),'sk-opt'));
    if(st.consent==='withdrawn'&&t.said!=='pushed')extra.push(x.cmd('<span class="sk-opt-label">😤 Thuyết phục ép cho xong</span><small>“không mổ là tay lệch luôn đó”</small>','dd_push',pay(t),'sk-opt'));
  }
  return `<section class="card dd-proc"><h4>🛏️ ${x.esc(n.proc||'')} · ${x.esc(n.time||'')}</h4><ul class="dd-checklist">${rows}</ul>${n.signed?'<p class="tag green">📝 Đã ký giấy cam đoan sau khi bác sĩ giải thích</p>':''}${n.jewel_off?'<p class="tag green">💍 Đã tháo trang sức</p>':''}</section>
    ${extra.length?`<div class="sk-opts dd-extra">${extra.join('')}</div>`:''}<section class="card dd-decide"><h4>⚖️ Quyết định</h4>${holdPane(t,x,cc(x).proc_hold||[])}</section>`;
}
function procSteps(t,x){
  const n=t.needs||{},ch=n.checks||{},rows=[];
  rows.push({ok:t.washed||null,label:'Sát khuẩn tay',go:{cmd:'dd_wash',payload:pay(t),label:'🧴 Sát khuẩn tay'}});
  rows.push({ok:n.me?true:null,label:'Xác định người bệnh',go:{sel:'.dd-id',label:'🪪 Xác định người bệnh'},pulse:''});
  for(const [k,[e,label]] of Object.entries(cc(x).proc_checks||{}))rows.push({ok:ch[k]!=null||null,label,go:{cmd:'dd_check',payload:{task:t.id,what:k},label:`${x.esc(e)} ${x.esc(label)}`}});
  return rows;
}

/* ------------------------------------------------------------ going home */
function dischargePanel(t,x){
  const n=t.needs||{},ch=n.checks||{},teach=cc(x).teach||{};
  const C=(k,label)=>ch[k]!=null?`<li class="seen">${x.esc(ch[k])}</li>`:`<li>${x.cmd(label,'dd_check',{task:t.id,what:k},'ghost dd-check')}</li>`;
  const extra=[];
  const st=n.state||{};
  if(st.paper==='unsigned'&&!n.signed&&!t.called?.length)extra.push(x.cmd('📞 Mời bác sĩ khám lại, ký giấy','dd_call',{task:t.id,reason:'paper'},'small'));
  if(st.cannula===true&&!n.cannula_off)extra.push(x.cmd('🩹 Rút kim luồn','dd_cannula',pay(t),'small'));
  const topics=Object.entries(teach).map(([k,[e,label]])=>(t.teach||[]).includes(k)?`<span class="tag green">✓ ${x.esc(label)}</span>`:x.cmd(`${x.esc(e)} ${x.esc(label)}`,'dd_teach',{task:t.id,topic:k},'ghost small dd-topic')).join('');
  return `${n.rush?`<p class="dd-rush">⏱️ ${x.esc(n.rush)}</p>`:''}<section class="card dd-papers"><h4>📄 Thủ tục</h4><ul class="dd-checklist">${C('paper','📄 Xem giấy ra viện')}${C('bhyt','💳 Xem thẻ BHYT')}${C('cannula','🩹 Xem kim luồn')}</ul>
    ${n.signed?'<p class="tag green">📄 Bác sĩ đã ký giấy ra viện</p>':''}${n.cannula_off?'<p class="tag green">🩹 Đã rút kim luồn</p>':''}${extra.length?`<div class="dd-row">${extra.join('')}</div>`:''}</section>
    <section class="card dd-teach"><h4>🗣️ Dặn dò</h4><div class="dd-topics">${topics}</div>${n.teachback?'<p class="tag green">🔁 Người bệnh đã nhắc lại</p>':x.cmd('🔁 Nhờ người bệnh nhắc lại','dd_teachback',pay(t),'small',!(t.teach||[]).length)}</section>`;
}
function dischargeSteps(t,x){
  const n=t.needs||{},ch=n.checks||{},rows=[];
  rows.push({ok:t.washed||null,label:'Sát khuẩn tay',go:{cmd:'dd_wash',payload:pay(t),label:'🧴 Sát khuẩn tay'}});
  rows.push({ok:n.me?true:null,label:'Xác định người bệnh',go:{sel:'.dd-id',label:'🪪 Xác định người bệnh'},pulse:''});
  for(const [k,label] of [['paper','📄 Xem giấy ra viện'],['bhyt','💳 Xem thẻ BHYT'],['cannula','🩹 Xem kim luồn']])rows.push({ok:ch[k]!=null||null,label:label.slice(2).trim(),go:{cmd:'dd_check',payload:{task:t.id,what:k},label}});
  rows.push({ok:(t.teach||[]).length?true:null,label:'Dặn dò',go:{sel:'.dd-teach',label:'🗣️ Dặn dò'},pulse:''});
  rows.push({ok:n.teachback||null,label:'Nhờ nhắc lại',go:{cmd:'dd_teachback',payload:pay(t),label:'🔁 Nhờ người bệnh nhắc lại'}});
  return rows;
}

/* ------------------------------------------------------------ the end-of-shift handover */
function reportCard(x){
  const td=data(x).today||{},rows=td.facts||[];
  if(!rows.length)return '';
  if(td.report)return `<p class="tag ${td.report==='ok'?'green':td.report==='miss'?'amber':'danger'} dd-report-done">📒 ${td.report==='ok'?'Đã viết sổ giao ca.':td.report==='miss'?'Đã viết sổ giao ca (còn thiếu).':'Sổ giao ca có dòng ghi khống.'}</p>`;
  const pick=(x.ui.report??={})[td.day]||[];
  const lines=rows.map(r=>act(x,`<span>${pick.includes(r.id)?'☑️':'⬜'}</span> ${x.esc(r.text)}`,'reportPick',{id:r.id,day:td.day},`dd-line${pick.includes(r.id)?' on':''}`,` aria-pressed="${pick.includes(r.id)}"`)).join('');
  return pane(x,`report-${td.day}`,`📒 Viết sổ giao ca · ${rows.length} dòng`,`<p class="small muted">Chọn những gì thật sự đã xảy ra, đủ để ca đêm theo dõi.</p><div class="dd-lines">${lines}</div>${x.cmd('📒 Ghi vào sổ giao ca','dd_report',{lines:pick},'primary full',!pick.length)}`,true,'dd-report');
}

/* ------------------------------------------------------------ the guide */
function bellSteps(t,x){
  return [{ok:t.washed||null,label:'Sát khuẩn tay',go:{cmd:'dd_wash',payload:pay(t),label:'🧴 Sát khuẩn tay'}},
    {ok:null,label:'Trả lời chuông',go:{sel:'.dd-bell',label:'🔔 Chọn cách trả lời'},pulse:''}];
}
function stepsOf(t,x){
  return ({shift:shiftSteps,vitals:vitalsSteps,med:medSteps,proc:procSteps,discharge:dischargeSteps,triage:triageSteps,bell:bellSteps}[t.kind]||(()=>[]))(t,x);
}
function finalOf(t,x,steps){
  const n=t.needs||{};
  if(t.kind==='shift'){const f=x.ui.first?.[t.id];return {label:'📋 NHẬN CA',go:f?finalGo(steps,'dd_round',{task:t.id,first:f}):null,ready:!!f,why:'chọn giường xem trước'};}
  if(t.kind==='vitals')return t.chart?{label:'✅ XONG LƯỢT ĐO',go:finalGo(steps,'dd_done',pay(t)),ready:true}:null;
  if(t.kind==='triage'){const all=((n.queue||[]).length)&&(n.queue||[]).every((_,i)=>(t.colors||{})[String(i)]);return {label:'🚦 GỬI VÀO KHÁM',go:all?finalGo(steps,'dd_triage',pay(t)):null,ready:!!all,why:'phát thẻ màu cho cả ba người'};}
  if(t.kind==='proc')return {label:'🛏️ CHUYỂN ĐI THỦ THUẬT',go:finalGo(steps,'dd_send',pay(t)),ready:true,can:t.can?.dd_send};
  if(t.kind==='discharge')return {label:'🏠 CHO VỀ',go:finalGo(steps,'dd_discharge',pay(t)),ready:true};
  return null;
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện trong khoa',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  const o=wardStep(x);if(o)return {steps:[o],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'dd_intro',payload:{},label:'🏥 Vào ca thôi!'}}],final:null};
  if(t.kind!=='shift'&&!t.known)return {steps:[{ok:null,label:t.kind==='triage'?'Nghe cô Mỹ':'Tới giường',go:{cmd:'ask',payload:pay(t),label:t.kind==='triage'?'👂 Nghe cô Mỹ':'👋 Tới giường'}}],final:null,pulse:'.sk-ask'};
  const steps=stepsOf(t,x);
  return {steps,final:finalOf(t,x,steps)};
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});
function top(x){return `${introCard(x,'dd_intro','🏥')}${deskCard(x,'dd_desk','Chuyện trong khoa')}${oddCard(x,ODD_CFG)}${groundCard(x)}`;}

export default {
  id:'nurse',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='shift'?'Đọc sổ giao ca':!t.known?'Tới giường':'Làm tiếp';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x),head=top(x);
    if(d.desk?.ev||d.odd?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk dd">${hint}${head}${bottom(x,g)}</div>`;
    let main='',side='';
    const learn=learnNote(x);
    if(t.kind==='shift'){main=shiftPanel(t,x);side=stepRows(x,g.steps,'Nhận ca',{chip:true});}
    else if(t.kind==='triage'){main=t.known?triagePanel(t,x):askCard(x,t,'👂 Nghe cô Mỹ');side=t.known?stepRows(x,g.steps,'Quầy tiếp đón',{chip:true}):'';}
    else if(!t.known)main=patientCard(t,x);
    else{
      const body={vitals:vitalsPanel,med:medPanel,bell:bellPanel,proc:procPanel,discharge:dischargePanel}[t.kind](t,x);
      main=`${patientCard(t,x)}${t.kind==='bell'?`<div class="dd-bedside">${handsRow(t,x)}</div>`:bedside(t,x)}${body}`;
      side=t.kind==='bell'?'':stepRows(x,g.steps,'Các bước',{chip:true});
    }
    return `<div class="career-job sk dd">${hint}${head}${learn}${dayBar(x)}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x),head=top(x);
    if(d.desk?.ev||d.odd?.ev||!d.intro||x.ui.intro){
      const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện trong khoa',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}
        :d.odd?.ev?{steps:[wardStep(x)],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'dd_intro',payload:{},label:'🏥 Vào ca thôi!'}}],final:null};
      return `<div class="career-job sk dd">${hintFor(g,x)}${head}${bottom(x,g)}</div>`;
    }
    const td=d.today||{};
    const tiles=[[td.tasks||0,'việc'],[td.calls||0,'lần báo bác sĩ'],[td.held||0,'lần giữ lại'],[td.triaged||0,'người phân loại']];
    return `<div class="career-job sk dd">${head}${dayBar(x)}<section class="card dd-today"><h4>🏥 Ca hôm nay</h4><div class="dd-tiles">${tiles.map(([v,l])=>`<div><b>${x.esc(v)}</b><small>${x.esc(l)}</small></div>`).join('')}</div></section>
      ${reportCard(x)}<section class="card dd-record"><h4>📁 Hồ sơ của bạn</h4>${record(x)}${restCard(x,ODD_CFG)}</section></div>`;
  },
  input(el,x){
    const k=el.dataset?.ddChart;if(!k)return false;
    const form=el.closest('form');const tid=x.room.active_task;
    ((x.ui.chart??={})[tid]??={})[k]=el.value;
    if(form)form.dataset.dirty='1';
    return true;
  },
  async submit(form,x){
    if(form.dataset.ddForm!=='chart')return false;
    const t=(x.room.tasks||[]).find(r=>r.id===x.room.active_task);if(!t)return true;
    const vals={};for(const k of cc(x).sign_ids||[])vals[k]=(form.elements[k]?.value||'').trim();
    if(Object.values(vals).some(v=>!v)){x.toast('Điền đủ năm ô rồi ghi phiếu nhé.');return true;}
    await x.send('dd_chart',{task:t.id,vals});
    return true;
  },
  tick(root){keepBarAboveFooter(root);},
  actions:{...kitActions,...oddActions,
    async pickFirst(d,el,x){(x.ui.first??={})[d.task]=d.bed;x.render();},
    async callPick(d,el,x){const b=((x.ui.call??={})[d.task]??=[]);const i=b.indexOf(d.sign);if(i>=0)b.splice(i,1);else b.push(d.sign);x.render();},
    async reportPick(d,el,x){const b=((x.ui.report??={})[d.day]??=[]);const i=b.indexOf(d.id);if(i>=0)b.splice(i,1);else b.push(d.id);x.render();},
  },
};
