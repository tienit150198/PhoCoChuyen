/** Nhân viên cứu hộ hồ bơi — the high chair at Hồ bơi Sóng Xanh (server: game/careers/lifeguard.py).
 * Opening the pool (checks one by one, the water log typed by hand, fix or report each fault, open or hold the
 * gate), the scan on a clock (five zones in a minute; a zone's card offers the whistle and the alarm, never which
 * one is right), the rescue (backup, reach / throw / go with the tube, breathing, care), the gate, the children's
 * class (swim test, wristbands, today's topics, the head count), first aid, and thunder (out, shelter, count,
 * wait, answer the manager, reopen). The awkward people of the pool answer through the air crew's encounter card
 * (air_kit.js oddCard); the end-of-shift log is written from what really happened.
 * The server decides everything; hints show the next step, never which way a decision should go. */
import {stepRows,nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {data,cc,act,pane,introCard,deskCard,dayBar,person,askCard,bottom,kitActions,tip,clean} from './street_kit.js';
import {oddCard,restCard,record,ACTIONS as oddActions} from './air_kit.js';

const ODD_CFG={odd:'hb_odd',rest:'hb_rest',kinds:{charm:'Lời mời khó từ chối',harass:'Quấy rối',demand:'Yêu cầu oái oăm',corner:'Làm tắt',bargain:'Mặc cả với hồ'},
  rest_to:[['self','Gửi anh Hải'],['company','Nhờ công đoàn']]};
const pay=t=>({task:t.id});
const PAIR=(x,group,k)=>((cc(x)[group]||{})[k])||['•',k];
/** A command button that also carries the moment of the tap (the scan's clock: careers.js tapStamp). */
const tapCmd=(x,label,command,payload,cls='')=>`<button type="button" class="btn ${cls}" data-command="${command}" data-tap-stop="${command}" data-payload="${x.esc(JSON.stringify(payload))}">${label}</button>`;

/* ------------------------------------------------------------ shared pieces */
function learnNote(x){
  const l=data(x).learn;if(!l?.on)return '';
  if(clean())return `<p class="hb-learn" aria-label="Anh Hải kèm: việc ${Math.min(l.n+1,l.of)}/${l.of}">🛟 ${Math.min(l.n+1,l.of)}/${l.of}</p>${tip(`Anh Hải ngồi cạnh kèm bạn: việc ${Math.min(l.n+1,l.of)}/${l.of}. Sai gì anh nhắc trước.`,'Học nghề','p')}`;
  return `<p class="hb-learn">🛟 Anh Hải ngồi cạnh kèm bạn: việc ${Math.min(l.n+1,l.of)}/${l.of}. Sai gì anh nhắc trước.</p>`;
}
function groundCard(x){
  const cd=data(x).odd?.conduct||{};if(!cd.ground)return '';
  return `<section class="hb-ground" role="status"><h3>⚖️ ${cd.demoted?'Bị hạ bậc, tạm đình chỉ trực hôm nay':'Tạm đình chỉ trực ghế hôm nay'}</h3><p class="small">Mai lên trung tâm trình bày. Hôm nay tan ca sớm.</p>${x.button('Tan ca','end',{},'primary')}</section>`;
}
function poolStep(x){
  const o=data(x).odd||{};
  if(o.ev)return {ok:null,label:`Trả lời: ${o.ev.title}`,go:{sel:'.air-odd',label:'💬 Trả lời'},pulse:''};
  if(o.conduct?.ground)return {ok:null,label:'Tạm đình chỉ trực: tan ca',go:{sel:'.hb-ground',label:'⚖️ Tan ca'},pulse:''};
  return null;
}
/** A choice; on the clean layout its explanation (`sub`) is in the "?" sheet. */
const opt=(x,label,sub,command,payload,cls='')=>x.cmd(`<span class="sk-opt-label">${label}</span>${sub?(clean()?tip(x.esc(sub),label.replace(/^\S+\s/,'')):`<small>${x.esc(sub)}</small>`):''}`,command,payload,`sk-opt ${cls}`);

/* ------------------------------------------------------------ opening the pool */
/** Clean layout: each check in a word or two (the full name stays in aria-label), the report channels short. */
const LG_WORD={clear:'Nước',strip:'Que thử',drain:'Nắp hút',tube:'Phao ống',ring:'Phao tròn',kit:'Sơ cứu',signs:'Biển',phone:'Điện thoại'};
const CHAN_WORD={book:'Ghi sổ trực',tech:'Báo kỹ thuật',boss:'Gọi quản lý ngay'};
const checkWord=r=>clean()&&LG_WORD[r.id]||r.label;
/** The water card's ranges as numbers ("Clo: từ 1 tới 3 trên bảng mẫu" → "1–3"), '' when it does not read so. */
const rangeOf=s=>{const m=String(s||'').match(/từ\s+([\d,]+)\s+tới\s+([\d,]+)/);return m?`${m[1]}–${m[2]}`:'';};
function openClean(t,x){
  const n=t.needs||{},rows=n.checks||[],chan=cc(x).channels||{};
  // Checked fine or not yet: a tile. A fault: its own row with what was found (the cue), the fix and whom to tell.
  const tiles=rows.filter(r=>r.state!=='fault').map(r=>{const name=x.esc(r.label);
    if(!r.state)return x.cmd(`<span class="tile-emoji">${x.esc(r.emoji)}</span><b>${x.esc(checkWord(r))}</b>`,'hb_check',{task:t.id,what:r.id},'tile sk-tile hb-tile').replace('<button ',`<button aria-label="Kiểm ${name.toLowerCase()}" `);
    return `<div class="sk-tile hb-tile done" aria-label="${name}: ổn"><span class="tile-emoji">✅</span><b>${x.esc(checkWord(r))}</b>${tip(x.esc(r.text||''),r.label)}</div>`;}).join('');
  const faults=rows.filter(r=>r.state==='fault').map(r=>{
    const fix=r.fix?(r.fixed?`<span class="tag green">🔧 ${x.esc(r.fix)}</span>`:x.cmd(`🔧 ${x.esc(r.fix)}`,'hb_fix',{task:t.id,what:r.id},'small hb-fix')):'';
    const rep=r.rep?`<span class="tag blue">${x.esc(PAIR(x,'channels',r.rep)[0])} Đã báo: ${x.esc(CHAN_WORD[r.rep]||PAIR(x,'channels',r.rep)[1])}</span>`
      :`<div class="hb-chans" role="group" aria-label="Báo cho ai">${Object.entries(chan).map(([k,[e,l]])=>x.cmd(`${x.esc(e)} ${x.esc(CHAN_WORD[k]||l)}`,'hb_rep',{task:t.id,what:r.id,to:k},'ghost small').replace('<button ',`<button aria-label="${x.esc(l)}" `)).join('')}</div>`;
    return `<li class="seen fault">⚠️ <b>${x.esc(r.label)}:</b> ${x.esc(r.text)}<div class="hb-row">${fix}</div>${rep}</li>`;}).join('');
  const done=rows.filter(r=>r.state).length,all=done===rows.length;
  const decide=pane(x,`gate-${t.id}`,'🚪 <b>Mở cổng?</b>',`<div class="sk-opts">${opt(x,'🔓 Mở cổng đón khách','mọi thứ đã an toàn','hb_open',{task:t.id,decision:'open'})}${opt(x,'⏳ Hoãn mở, chờ kỹ thuật','khách chờ ngoài cổng','hb_open',{task:t.id,decision:'delay'})}</div>`,all);
  return `<section class="card hb-open"><h4 aria-label="Danh sách mở hồ">🧪 <small class="muted">${done}/${rows.length}</small></h4><div class="tile-grid hb-tiles">${tiles}</div>${faults?`<ul class="hb-checklist">${faults}</ul>`:''}</section>${n.strip?logForm(t,x):''}
    <section class="card hb-decide">${decide}</section>`;
}
function openPanel(t,x){
  if(clean())return openClean(t,x);
  const n=t.needs||{},rows=n.checks||[],chan=cc(x).channels||{};
  const items=rows.map(r=>{
    if(!r.state)return `<li>${x.cmd(`${x.esc(r.emoji)} ${x.esc(r.label)}`,'hb_check',{task:t.id,what:r.id},'ghost hb-check')}</li>`;
    if(r.state==='ok')return `<li class="seen">✅ <b>${x.esc(r.label)}:</b> ${x.esc(r.text)}</li>`;
    const fix=r.fix?(r.fixed?`<span class="tag green">🔧 ${x.esc(r.fix)}</span>`:x.cmd(`🔧 ${x.esc(r.fix)}`,'hb_fix',{task:t.id,what:r.id},'small hb-fix')):'';
    const rep=r.rep?`<span class="tag blue">${x.esc(PAIR(x,'channels',r.rep)[0])} Đã báo: ${x.esc(PAIR(x,'channels',r.rep)[1])}</span>`
      :`<div class="hb-chans" role="group" aria-label="Báo cho ai">${Object.entries(chan).map(([k,[e,l]])=>x.cmd(`${x.esc(e)} ${x.esc(l)}`,'hb_rep',{task:t.id,what:r.id,to:k},'ghost small')).join('')}</div>`;
    return `<li class="seen fault">⚠️ <b>${x.esc(r.label)}:</b> ${x.esc(r.text)}<div class="hb-row">${fix}</div>${rep}</li>`;
  }).join('');
  const card=pane(x,'water-card','📏 Bảng mẫu Sóng Xanh',`<ul class="hb-card"><li>🧪 ${x.esc((n.card||{}).cl||'')}</li><li>🧪 ${x.esc((n.card||{}).ph||'')}</li></ul><p class="small muted">Luật của trò chơi: ngoài bảng mẫu là chưa mở hồ, báo kỹ thuật.</p>`,false,'hb-cardpane');
  return `<section class="card hb-open"><h4>🧪 Danh sách mở hồ</h4><ul class="hb-checklist">${items}</ul></section>${n.strip?logForm(t,x):''}${card}
    <section class="card hb-decide"><h4>🚪 Mở cổng?</h4><div class="sk-opts">${opt(x,'🔓 Mở cổng đón khách','mọi thứ đã an toàn','hb_open',{task:t.id,decision:'open'})}${opt(x,'⏳ Hoãn mở, chờ kỹ thuật xử lý','khách chờ ngoài cổng','hb_open',{task:t.id,decision:'delay'})}</div></section>`;
}
function logForm(t,x){
  const n=t.needs||{},st=n.strip;
  const strip=`<div class="hb-strip" aria-label="Que thử"><span class="hb-pad cl" style="--v:${Math.min(1,(parseFloat(String(st.cl).replace(',','.'))||0)/5)}"></span><span class="hb-pad ph" style="--v:${Math.min(1,Math.max(0,((parseFloat(String(st.ph).replace(',','.'))||7)-6.8)/1.6))}"></span><b>Clo ${x.esc(st.cl)}${clean()&&rangeOf(n.card?.cl)?` <small>(${x.esc(rangeOf(n.card.cl))})</small>`:''} · pH ${x.esc(st.ph)}${clean()&&rangeOf(n.card?.ph)?` <small>(${x.esc(rangeOf(n.card.ph))})</small>`:''}</b></div>`;
  if(n.log)return `<section class="card hb-log"><h4>📒 Sổ nước hôm nay</h4>${strip}<p class="tag green">Đã ghi: Clo ${x.esc(n.log.cl)} · pH ${x.esc(n.log.ph)}</p></section>`;
  const typed=(x.ui.log??={})[t.id]||{};
  const f=(k,label)=>`<label class="hb-field"><span>${label}</span><input name="${k}" inputmode="decimal" autocomplete="off" maxlength="8" value="${x.esc(typed[k]||'')}" data-hb-log="${k}"></label>`;
  return `<form class="card hb-log" data-hb-form="log"><h4>📒 Ghi sổ nước</h4>${strip}${clean()?tip('Gõ đúng số trên que thử. Ngoài bảng mẫu (số trong ngoặc) là chưa mở hồ, báo kỹ thuật.','Sổ nước','p'):'<p class="small muted">Gõ đúng số trên que thử.</p>'}<div class="hb-fields">${f('cl','🧪 Clo')}${f('ph','🧪 pH')}</div><button type="submit" class="btn primary full">📒 Ghi sổ nước</button></form>`;
}
function openSteps(t,x){
  const n=t.needs||{},rows=n.checks||[],next=rows.find(r=>!r.state);
  const steps=[{ok:!next||null,label:'Kiểm từng món',note:`${rows.filter(r=>r.state).length}/${rows.length}`,go:next?{cmd:'hb_check',payload:{task:t.id,what:next.id},label:`${x.esc(next.emoji)} Kiểm ${x.esc(checkWord(next).toLowerCase())}`}:null}];
  if(n.strip)steps.push({ok:n.log?true:null,label:'Ghi số que thử vào sổ nước',go:{sel:'.hb-log',label:'📒 Ghi sổ nước'},pulse:''});
  for(const r of rows.filter(r=>r.state==='fault')){
    if(r.fix)steps.push({ok:r.fixed||null,label:`Tự xử lý: ${r.label}`,go:{cmd:'hb_fix',payload:{task:t.id,what:r.id},label:`🔧 ${x.esc(r.fix)}`}});
    steps.push({ok:r.rep?true:null,label:`Báo lại: ${r.label}`,go:{sel:'.hb-chans',label:'📣 Chọn người cần báo'},pulse:''});
  }
  steps.push({ok:null,label:'Mở cổng hay hoãn',go:{sel:clean()?'.hb-decide .sk-pane-sum':'.hb-decide',label:'🚪 Quyết mở cổng'},pulse:''});
  return steps;
}

/* ------------------------------------------------------------ the scan */
function clockBar(t,x){
  const n=t.needs||{};if(n.sweep==null)return '';
  const done=(n.zones||[]).every(z=>z.text!=null);
  return `<div class="hb-clock${done?' done':''}" data-hb-start="${x.esc(n.sweep)}" data-hb-limit="${x.esc(n.limit||60)}" role="timer"><i></i><b>${done?'Đã quét đủ năm khu':'⏱️ Vòng quét'}</b><small class="hb-secs"></small></div>`;
}
function watchPanel(t,x){
  const n=t.needs||{},zones=n.zones||[];
  if(n.sweep==null)return `<section class="card hb-start"><h4>👀 Vòng quét</h4>${clean()?`<p>⏱️ 5 khu · ${x.esc(cc(x).sweep_s||60)}″ · 🆘 Đuối nước: im lặng, người dựng đứng, đầu ngửa</p>`:`<p>Nhìn đủ năm khu trong ${x.esc(cc(x).sweep_s||60)} giây. Người đuối nước thường im lặng: người dựng đứng, đầu ngửa ra sau, không tiến lên được.</p>`}${tapCmd(x,'👀 BẮT ĐẦU VÒNG QUÉT','hb_scan',pay(t),'primary big full hb-go')}</section>`;
  const sel=x.ui.zone?.[t.id];
  const tiles=zones.map(z=>{
    const mark=n.alarm===z.id?'🚨':z.whistle?'📣':z.text!=null?'👁️':'';
    if(z.text==null)return tapCmd(x,`<span class="tile-emoji">${x.esc(z.emoji)}</span><b>${x.esc(z.name)}</b>${clean()?'':'<small>chạm để nhìn</small>'}`,'hb_look',{task:t.id,zone:z.id},'tile sk-tile hb-zone');
    return act(x,`<span class="tile-emoji">${x.esc(z.emoji)}</span><b>${x.esc(z.name)}</b><small>${mark} đã nhìn</small>`,'zone',{task:t.id,zone:z.id},`tile sk-tile hb-zone seen${sel===z.id?' on':''}`,` aria-pressed="${sel===z.id}"`);
  }).join('');
  return `${clockBar(t,x)}<div class="tile-grid hb-zones">${tiles}</div>${zoneCard(t,x,sel)}${n.alarm?rescueCard(t,x):''}`;
}
function zoneCard(t,x,id){
  const n=t.needs||{},z=(n.zones||[]).find(r=>r.id===id&&r.text!=null);
  if(!z)return clean()?tip('Chạm một khu đã nhìn để thổi còi hoặc báo động.','Vòng quét','p'):'<p class="small muted hb-tip">Chạm một khu đã nhìn để thổi còi hoặc báo động.</p>';
  const rules=cc(x).rules||{};
  const wh=z.whistle?`<p class="tag blue">📣 Đã nhắc: ${x.esc((rules[z.whistle]||['',''])[1])}</p>`
    :pane(x,`wh-${t.id}-${z.id}`,'📣 Thổi còi nhắc…',`<div class="hb-rules">${Object.entries(rules).map(([k,[e,l]])=>x.cmd(`${x.esc(e)} ${x.esc(l)}`,'hb_whistle',{task:t.id,zone:z.id,rule:k},'ghost small hb-rule')).join('')}</div>`,false,'hb-whpane');
  const alarm=n.alarm?'':n.false===z.id?'<p class="tag amber">Báo động nhầm khu này rồi.</p>':tapCmd(x,'🚨 Còi dài: có người đang chìm!','hb_alarm',{task:t.id,zone:z.id},'danger full hb-alarm');
  return `<section class="card hb-zonecard"><h4>${x.esc(z.emoji)} ${x.esc(z.name)}</h4><p>${x.esc(z.text)}</p>${clean()?tip('Ổn thì để yên, quét tiếp.',z.name,'p'):'<p class="small muted">Ổn thì để yên, quét tiếp.</p>'}${wh}${alarm}</section>`;
}
function rescueCard(t,x){
  const r=(t.needs||{}).rescue||{},m=cc(x).methods||{},care=cc(x).care||{};
  const help=r.help?`<p class="tag ${r.help==='team'?'green':'amber'}">${r.help==='team'?'📣 Đã gọi hỗ trợ':'🤐 Tự làm một mình'}</p>`
    :`<div class="sk-opts">${opt(x,'📣 Ba hồi còi: anh Hải trông hồ, gọi 115','','hb_backup',{task:t.id,how:'team'})}${opt(x,'🤐 Tự làm, khỏi phiền ai','','hb_backup',{task:t.id,how:'alone'})}</div>`;
  const how=r.method?`<p class="tag green">${x.esc((m[r.method]||['', ''])[0])} ${x.esc((m[r.method]||['', ''])[1])}</p>`
    :`<div class="sk-opts">${Object.entries(m).map(([k,[e,l,sub]])=>(r.fails||[]).includes(k)?`<p class="small muted">✗ ${x.esc(l)}: không tới.</p>`:opt(x,`${x.esc(e)} ${x.esc(l)}`,sub,'hb_method',{task:t.id,method:k})).join('')}</div>`;
  const look=!r.method?'':r.assess?`<p class="hb-assess">🩺 ${x.esc(r.assess)}</p>`:x.cmd('🩺 Gọi to, vỗ vai, nhìn ngực mười giây','hb_assess',pay(t),'ghost full');
  const aid=!r.method?'':r.care?`<p class="tag green">${x.esc((care[r.care]||['', ''])[0])} ${x.esc((care[r.care]||['', ''])[1])}</p>`
    :`<div class="sk-opts">${Object.entries(care).map(([k,[e,l]])=>opt(x,`${x.esc(e)} ${x.esc(l)}`,'','hb_care',{task:t.id,care:k})).join('')}</div>`;
  return `<section class="sk-event tense hb-rescue" role="group"><div class="sk-ev-head"><span aria-hidden="true">🚨</span><div><small>Có người gặp nạn</small><h3>Cứu người</h3></div></div>
    <h4>1. Gọi hỗ trợ</h4>${help}<h4>2. Đưa người vào bờ</h4>${how}${r.method?`<h4>3. Xem tỉnh, thở</h4>${look}<h4>4. Sơ cứu</h4>${aid}`:''}</section>`;
}
function watchSteps(t,x){
  const n=t.needs||{},zones=n.zones||[];
  if(n.sweep==null)return [{ok:null,label:'Bắt đầu vòng quét',go:{cmd:'hb_scan',payload:pay(t),label:'👀 Bắt đầu vòng quét'}}];
  const next=zones.find(z=>z.text==null);
  const rows=[{ok:!next||null,label:'Nhìn đủ năm khu',note:`${zones.filter(z=>z.text!=null).length}/${zones.length}`,go:next?{cmd:'hb_look',payload:{task:t.id,zone:next.id},label:`${x.esc(next.emoji)} Nhìn ${x.esc(next.name.split('·')[0].trim().toLowerCase())}`}:null}];
  rows.push({ok:!next||null,label:'Nhắc ai vi phạm, báo động nếu có người chìm',go:{sel:'.hb-zones',label:'📣 Xem lại từng khu'},pulse:''});
  if(n.alarm){
    const r=n.rescue||{};
    rows.push({ok:r.help?true:null,label:'Gọi hỗ trợ',go:{sel:'.hb-rescue',label:'📣 Gọi hỗ trợ'},pulse:''});
    rows.push({ok:r.method?true:null,label:'Đưa người vào bờ',go:{sel:'.hb-rescue',label:'🛟 Chọn cách cứu'},pulse:''});
    rows.push({ok:r.assess?true:null,label:'Xem tỉnh, thở',go:r.method?{cmd:'hb_assess',payload:pay(t),label:'🩺 Xem tỉnh, thở'}:null});
    rows.push({ok:r.care?true:null,label:'Sơ cứu',go:{sel:'.hb-rescue',label:'❤️ Chọn cách sơ cứu'},pulse:''});
  }
  return rows;
}

/* ------------------------------------------------------------ the gate */
function gatePanel(t,x){
  const q=(t.needs||{}).queue||[],vs=cc(x).verdicts||{};
  return `<div class="hb-queue">${q.map((p,i)=>{
    const btn=(what,label)=>p[what]?`<p class="hb-q"><span aria-hidden="true">${what==='ask'?'👂':'👀'}</span> ${x.esc(p[what])}</p>`:x.cmd(label,'hb_gq',{task:t.id,i,what},'ghost small');
    const seg=Object.entries(vs).map(([k,[e,l]])=>x.cmd(`${e} ${x.esc(l)}`,'hb_verdict',{task:t.id,i,verdict:k},`hb-verdict${p.verdict===k?' on':''}`)).join('');
    return `<article class="card hb-person${p.verdict?' got':''}"><div class="row"><span class="hb-av" aria-hidden="true">${x.esc(p.emoji)}</span><div class="grow"><b>${x.esc(p.who)}</b>${p.best?`<p class="small">Đúng ra: ${x.esc((vs[p.best]||['',''])[0])} ${x.esc((vs[p.best]||['',''])[1])}</p>`:''}</div></div>
      <div class="hb-qs">${btn('look','👀 Nhìn')}${btn('ask','👂 Hỏi')}</div><div class="hb-verdicts" role="group" aria-label="Cho vào thế nào">${seg}</div></article>`;}).join('')}</div>`;
}
function gateSteps(t,x){
  return ((t.needs||{}).queue||[]).map((p,i)=>({ok:p.verdict?true:null,label:`Quyết: ${p.who}`,go:{sel:`.hb-person:nth-child(${i+1})`,label:`🎫 ${x.esc(p.who)}`},pulse:''}));
}

/* ------------------------------------------------------------ the children's class */
function lessonPanel(t,x){
  const n=t.needs||{},bands=cc(x).bands||{},topics=cc(x).topics||{},order=cc(x).band_order||Object.keys(bands);
  const sheet=n.sheet?'':x.cmd('📋 Xem sổ đón phụ huynh','hb_sheet',pay(t),'ghost full');
  const kids=(n.kids||[]).map(k=>{
    const seg=order.map(b=>x.cmd(`${x.esc(bands[b][0])} ${x.esc(bands[b][1].split(':')[0])}`,'hb_band',{task:t.id,kid:k.id,band:b},`hb-band b-${b}${k.band===b?' on':''}`)).join('');
    const away=k.away?(k.called?'<p class="tag green">📞 Mẹ đã quay lại</p>':x.cmd('📞 Gọi số trong sổ đón','hb_call',{task:t.id,kid:k.id},'small')):'';
    return `<article class="card hb-kid"><div class="row"><span class="hb-av" aria-hidden="true">${x.esc(k.emoji)}</span><div class="grow"><b>${x.esc(k.name)}</b> <small>${x.esc(k.age)} tuổi</small><p class="small">${x.esc(k.claim)}</p></div></div>
      ${k.test?`<p class="hb-q">🏊 ${x.esc(k.test)}</p>`:x.cmd('🏊 Bơi thử ở làn sát thành','hb_test',{task:t.id,kid:k.id},'ghost small')}${away}<div class="hb-bands" role="group" aria-label="Vòng tay">${seg}</div></article>`;}).join('');
  const plan=(n.topics||[]).map(k=>`${(topics[k]||['',''])[0]} ${(topics[k]||['',k])[1]}`).join(' · ');
  const tbtn=Object.entries(topics).map(([k,[e,l]])=>(n.taught||[]).includes(k)?`<span class="tag green">✓ ${x.esc(l)}</span>`:x.cmd(`${x.esc(e)} ${x.esc(l)}`,'hb_teach',{task:t.id,topic:k},'ghost small hb-topic')).join('');
  return `${sheet}<div class="hb-kids">${kids}</div><section class="card hb-teach"><h4>📚 Giáo án hôm nay</h4><p class="small">${x.esc(plan)}</p><div class="hb-topics">${tbtn}</div></section>
    <section class="card hb-countcard">${n.counted?'<p class="tag green">🔢 Đã điểm danh lúc lên bờ</p>':x.cmd('🔢 Điểm danh lúc lên bờ','hb_count',pay(t),'ghost full')}</section>`;
}
function lessonSteps(t,x){
  const n=t.needs||{},kids=n.kids||[],rows=[{ok:n.sheet||null,label:'Xem sổ đón',go:{cmd:'hb_sheet',payload:pay(t),label:'📋 Xem sổ đón'}}];
  const untested=kids.find(k=>!k.test);
  rows.push({ok:!untested||null,label:'Bơi thử từng bé',note:`${kids.filter(k=>k.test).length}/${kids.length}`,go:untested?{cmd:'hb_test',payload:{task:t.id,kid:untested.id},label:`🏊 ${x.esc(untested.name)} bơi thử`}:null});
  rows.push({ok:kids.every(k=>k.band)||null,label:'Phát vòng tay',go:{sel:'.hb-kids',label:'🟢 Phát vòng tay'},pulse:''});
  rows.push({ok:(n.topics||[]).every(k=>(n.taught||[]).includes(k))||null,label:'Dạy theo giáo án',go:{sel:'.hb-teach',label:'📚 Dạy theo giáo án'},pulse:''});
  rows.push({ok:n.counted||null,label:'Điểm danh lúc lên bờ',go:{cmd:'hb_count',payload:pay(t),label:'🔢 Điểm danh'}});
  return rows;
}

/* ------------------------------------------------------------ first aid */
function aidPanel(t,x){
  const n=t.needs||{};
  const top=`<div class="hb-row">${n.ask?'':x.cmd('👂 Hỏi chuyện gì xảy ra','hb_aidask',pay(t),'ghost small')}${t.washed?'<span class="tag green">🧤 Đã đeo găng</span>':x.cmd('🧤 Đeo găng tay','hb_gloves',pay(t),'small hb-gloves')}</div>`;
  const opts=(n.options||[]).map(o=>x.cmd(`<span class="sk-opt-label">${x.esc(o.label)}</span>`,'hb_aid',{task:t.id,choice:o.id},'sk-opt')).join('');
  return `<section class="sk-event hb-aid"><div class="sk-ev-head"><span aria-hidden="true">🩹</span><div><small>${x.esc(n.who||'')}</small><h3>${x.esc(n.detail||'')}</h3></div></div>
    ${n.ask?`<p class="hb-q">👂 ${x.esc(n.ask)}</p>`:''}${top}<div class="sk-opts">${opts}</div></section>`;
}
function aidSteps(t,x){
  const n=t.needs||{};
  return [{ok:n.ask?true:null,label:'Hỏi chuyện',go:{cmd:'hb_aidask',payload:pay(t),label:'👂 Hỏi chuyện'}},
    {ok:t.washed||null,label:'Đeo găng tay',go:{cmd:'hb_gloves',payload:pay(t),label:'🧤 Đeo găng'}},
    {ok:null,label:'Chọn cách sơ cứu',go:{sel:'.hb-aid .sk-opts',label:'🩹 Chọn cách sơ cứu'},pulse:''}];
}

/* ------------------------------------------------------------ thunder */
function stormPanel(t,x){
  const n=t.needs||{},sh=cc(x).shelters||{},rp=cc(x).replies||{};
  const ev=(n.events||[]).map(e=>`<li class="${e.thunder?'th':''} k-${x.esc(e.kind)}"><span class="hb-at">${x.esc(e.at)}</span><span>${e.thunder?'⚡ ':''}${x.esc(e.text)}</span></li>`).join('');
  const wait=cc(x).wait_after||30;
  const status=clean()?`<p class="hb-now" aria-label="Giờ ${x.esc(n.now||'')}${n.last_thunder?`, sấm cuối ${x.esc(n.last_thunder)}, chờ ${wait} phút`:', chưa nghe sấm'}">🕒 <b>${x.esc(n.now||'')}</b>${n.last_thunder?` · ⚡ <b>${x.esc(n.last_thunder)}</b> +${wait}′`:` · ⚡ chưa · +${wait}′`}</p>`
    :`<p class="hb-now">🕒 Giờ: <b>${x.esc(n.now||'')}</b>${n.last_thunder?` · ⚡ Sấm cuối: <b>${x.esc(n.last_thunder)}</b>`:' · chưa nghe sấm'}</p>`;
  const rule=clean()?tip(`Nghe sấm hoặc thấy chớp: tất cả lên bờ, vào nơi có mái kiên cố, đếm người. ${x.esc(wait)} phút sau tiếng sấm cuối mới xuống lại.`,'📏 Nội quy dông sét','p'):pane(x,'storm-rule','📏 Nội quy dông sét',`<p class="small">Nghe sấm hoặc thấy chớp: tất cả lên bờ, vào nơi có mái kiên cố, đếm người. ${x.esc(cc(x).wait_after||30)} phút sau tiếng sấm cuối mới xuống lại.</p>`,false,'hb-rulepane');
  const acts=[];
  if(!n.sky)acts.push(x.cmd('📻 Nghe bản tin thời tiết','hb_sky',pay(t),'ghost small'));
  if(n.shelter&&!n.counted)acts.push(x.cmd('🔢 Đếm người','hb_count',pay(t),'small'));
  if(n.more)acts.push(x.cmd('⏱️ Chờ, xem trời','hb_wait',pay(t),'small hb-wait'));
  const out=n.shelter?`<p class="tag green">${x.esc((sh[n.shelter]||['',''])[0])} Đã lên bờ: ${x.esc((sh[n.shelter]||['',''])[1])}</p>`
    :`<section class="card hb-shelter"><h4>📣 Cho tất cả lên bờ, trú ở…</h4><div class="sk-opts">${Object.entries(sh).map(([k,[e,l]])=>opt(x,`${x.esc(e)} ${x.esc(l)}`,'','hb_shelter',{task:t.id,where:k})).join('')}</div></section>`;
  const push=n.push?`<section class="sk-event tense hb-push"><div class="sk-ev-head"><span aria-hidden="true">💬</span><div><small>Có người hỏi</small><h3>${x.esc((n.events||[]).slice(-1)[0]?.text||'')}</h3></div></div><div class="sk-opts">${Object.entries(rp).map(([k,[e,l]])=>opt(x,`${x.esc(e)} ${x.esc(l)}`,'','hb_reply',{task:t.id,say:k})).join('')}</div></section>`:'';
  return `<section class="card hb-storm"><h4>⛈️ Dông chiều</h4><ul class="hb-timeline">${ev}</ul>${status}${rule}</section>${push}${out}<div class="hb-row">${acts.join('')}</div>`;
}
function stormSteps(t,x){
  const n=t.needs||{};
  return [{ok:n.shelter?true:null,label:'Có sấm: cho lên bờ, vào nơi trú',go:{sel:'.hb-shelter',label:'📣 Cho lên bờ'},pulse:''},
    {ok:n.counted||null,label:'Đếm người',go:n.shelter?{cmd:'hb_count',payload:pay(t),label:'🔢 Đếm người'}:null},
    {ok:null,label:'Chờ đủ rồi mở lại',go:n.more?{cmd:'hb_wait',payload:pay(t),label:'⏱️ Chờ, xem trời'}:null}];
}

/* ------------------------------------------------------------ the end-of-shift log */
function reportCard(x){
  const td=data(x).today||{},rows=td.facts||[];
  if(!rows.length)return '';
  if(td.report)return `<p class="tag ${td.report==='ok'?'green':td.report==='miss'?'amber':'danger'} hb-report-done">📒 ${td.report==='ok'?'Đã ghi sổ trực.':td.report==='miss'?'Đã ghi sổ trực (còn thiếu).':'Sổ trực có dòng ghi khống.'}</p>`;
  const pick=(x.ui.report??={})[td.day]||[];
  const lines=rows.map(r=>act(x,`<span>${pick.includes(r.id)?'☑️':'⬜'}</span> ${x.esc(r.text)}`,'reportPick',{id:r.id,day:td.day},`hb-line${pick.includes(r.id)?' on':''}`,` aria-pressed="${pick.includes(r.id)}"`)).join('');
  return pane(x,`report-${td.day}`,`📒 Ghi sổ trực ca · ${rows.length} dòng`,`<p class="small muted">Chọn những gì thật sự đã xảy ra, đủ để ca sau nắm.</p><div class="hb-lines">${lines}</div>${x.cmd('📒 Ghi vào sổ trực','hb_report',{lines:pick},'primary full',!pick.length)}`,true,'hb-report');
}

/* ------------------------------------------------------------ the guide */
const STEPS={open:openSteps,watch:watchSteps,gate:gateSteps,lesson:lessonSteps,aid:aidSteps,storm:stormSteps};
function finalOf(t,x,steps){
  const n=t.needs||{};
  if(t.kind==='watch')return n.sweep==null?null:{label:'✅ KẾT THÚC VÒNG QUÉT',go:finalGo(steps,'hb_round',pay(t)),ready:!n.alarm||!!(n.rescue||{}).care,why:'đưa người vào bờ, sơ cứu'};
  if(t.kind==='gate'){const all=((n.queue||[]).length)&&(n.queue||[]).every(p=>p.verdict);return {label:'🎫 XONG LƯỢT CỔNG',go:all?finalGo(steps,'hb_gate',pay(t)):null,ready:!!all,why:'quyết cho cả ba người'};}
  if(t.kind==='lesson'){const all=(n.kids||[]).every(k=>k.band);return {label:'🏫 TAN LỚP',go:all?finalGo(steps,'hb_lesson',pay(t)):null,ready:all,why:'phát vòng tay cho cả ba bé'};}
  if(t.kind==='storm')return {label:'🔓 MỞ LẠI HỒ',go:finalGo(steps.filter(s=>s.label!=='Chờ đủ rồi mở lại'),'hb_reopen',pay(t)),ready:true,can:t.can?.hb_reopen};
  return null;
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở hồ',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  const o=poolStep(x);if(o)return {steps:[o],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'hb_intro',payload:{},label:'🛟 Vào ca thôi!'}}],final:null};
  if(t.kind!=='open'&&!t.known)return {steps:[{ok:null,label:'Tới chỗ đó',go:{cmd:'ask',payload:pay(t),label:ASK[t.kind]||'👋 Tới xem'}}],final:null,pulse:'.sk-ask'};
  const steps=(STEPS[t.kind]||(()=>[]))(t,x);
  return {steps,final:finalOf(t,x,steps)};
}
const ASK={watch:'🪜 Lên ghế cao',gate:'🎫 Ra cổng',lesson:'🏫 Ra khu cạn đón lớp',aid:'🩹 Mang hộp sơ cứu tới',storm:'🌩️ Nhìn trời'};
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});
function top(x){return `${introCard(x,'hb_intro','🛟')}${deskCard(x,'hb_desk','Chuyện ở hồ')}${oddCard(x,ODD_CFG)}${groundCard(x)}`;}
const PANEL={open:openPanel,watch:watchPanel,gate:gatePanel,lesson:lessonPanel,aid:aidPanel,storm:stormPanel};

export default {
  id:'lifeguard',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='open'?'Mở hồ':!t.known?'Tới chỗ đó':'Làm tiếp';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x),head=top(x);
    if(d.desk?.ev||d.odd?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk hb">${hint}${head}${bottom(x,g)}</div>`;
    let main,side='';
    if(t.kind!=='open'&&!t.known)main=askCard(x,t,ASK[t.kind]||'👋 Tới xem');
    else{
      main=(['open','storm','watch'].includes(t.kind)?'':person(x,t))+(PANEL[t.kind]||(()=>''))(t,x);
      side=stepRows(x,g.steps,'Các bước',{chip:true});
    }
    return `<div class="career-job sk hb">${hint}${head}${learnNote(x)}${dayBar(x)}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x),head=top(x);
    if(d.desk?.ev||d.odd?.ev||!d.intro||x.ui.intro){
      const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện ở hồ',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}
        :d.odd?.ev?{steps:[poolStep(x)],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'hb_intro',payload:{},label:'🛟 Vào ca thôi!'}}],final:null};
      return `<div class="career-job sk hb">${hintFor(g,x)}${head}${bottom(x,g)}</div>`;
    }
    const td=d.today||{};
    const tiles=[[td.tasks||0,'việc'],[td.whistles||0,'lần thổi còi'],[td.rescues||0,'người được cứu'],[td.gate||0,'người soát ở cổng']];
    return `<div class="career-job sk hb">${head}${dayBar(x)}<section class="card hb-today"><h4>🛟 Ca hôm nay</h4><div class="hb-tiles">${tiles.map(([v,l])=>`<div><b>${x.esc(v)}</b><small>${x.esc(l)}</small></div>`).join('')}</div></section>
      ${reportCard(x)}<section class="card hb-record"><h4>📁 Hồ sơ của bạn</h4>${record(x)}${restCard(x,ODD_CFG)}</section></div>`;
  },
  input(el,x){
    const k=el.dataset?.hbLog;if(!k)return false;
    const tid=x.room.active_task;
    ((x.ui.log??={})[tid]??={})[k]=el.value;
    return true;
  },
  async submit(form,x){
    if(form.dataset.hbForm!=='log')return false;
    const t=(x.room.tasks||[]).find(r=>r.id===x.room.active_task);if(!t)return true;
    const cl=(form.elements.cl?.value||'').trim(),ph=(form.elements.ph?.value||'').trim();
    if(!cl||!ph){x.toast('Điền đủ hai ô rồi ghi sổ nhé.');return true;}
    await x.send('hb_log',{task:t.id,cl,ph});
    return true;
  },
  tick(root,x){
    keepBarAboveFooter(root);
    const el=root.querySelector('.hb-clock');if(!el||el.classList.contains('done'))return;
    const start=Number(el.dataset.hbStart),limit=Number(el.dataset.hbLimit)||60,now=typeof x?.now==='function'?x.now():Date.now()/1000;
    const s=Math.max(0,now-start),bar=el.querySelector('i'),out=el.querySelector('.hb-secs');
    if(bar)bar.style.width=`${Math.min(100,s/limit*100).toFixed(1)}%`;
    el.classList.toggle('late',s>limit);
    if(out)out.textContent=s>limit?`quá ${Math.floor(s-limit)} giây`:`còn ${Math.max(0,Math.ceil(limit-s))} giây`;
  },
  actions:{...kitActions,...oddActions,
    async zone(d,el,x){(x.ui.zone??={})[d.task]=d.zone;x.render();},
    async reportPick(d,el,x){const b=((x.ui.report??={})[d.day]??=[]);const i=b.indexOf(d.id);if(i>=0)b.splice(i,1);else b.push(d.id);x.render();},
  },
};
