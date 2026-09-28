/** Kế toán tập đoàn · Sông Hồng Group — bàn hợp nhất (plugin client module).
 *  Group chart (mẹ – con, tỷ lệ sở hữu, đồng tiền), document tray (gói báo cáo, sổ đối chiếu nội bộ,
 *  email, bảng tính hợp nhất), procedure steps with hands-on widgets (bút toán loại trừ Nợ/Có tự cân,
 *  ghép tỷ giá, sắp xếp lịch khóa sổ) and the quarter's consolidation journal on the side.
 *  No inline handlers: every button goes through data-command / data-action="car:*". */
const P='ga_';
const num=v=>Number(v||0).toLocaleString('vi-VN');
const dkey=(t,st)=>`${t.id}:${st.id}`;
const drafts=x=>(x.ui.drafts??={});
const views=x=>(x.ui.view??={});
const currentStep=t=>(t.proc||[]).find(s=>s.state==='current');
const acct=(x,id)=>(x.cc.accounts||[]).find(a=>a.id===id)?.name||id;
const btn=(x,label,action,data={},style='',disabled=false)=>x.button(label,action,data,style).replace('<button ',`<button ${disabled?'disabled ':''}`);

/* ---------------------------------------------------------------- documents */
function tableDoc(d,x){
  const head=`<tr>${d.cols.map(c=>`<th>${x.esc(c)}</th>`).join('')}</tr>`;
  const body=(d.rows||[]).map(r=>`<tr>${r.map(v=>`<td>${x.esc(v)}</td>`).join('')}</tr>`).join('');
  const foot=(d.foot||[]).map(r=>`<tr>${r.map(v=>`<td>${x.esc(v)}</td>`).join('')}</tr>`).join('');
  return `<div class="ga-scroll"><table class="ga-table ${d.wide?'wide':''}"><thead>${head}</thead><tbody>${body}</tbody>${foot?`<tfoot>${foot}</tfoot>`:''}</table></div>${d.note?`<p class="ga-small">${x.esc(d.note)}</p>`:''}`;
}
function docBody(d,x){
  if(d.type==='table')return tableDoc(d,x);
  if(d.type==='kv')return `<dl class="ga-kv">${(d.rows||[]).map(([k,v])=>`<dt>${x.esc(k)}</dt><dd>${x.esc(v)}</dd>`).join('')}</dl>`;
  if(d.type==='cash')return `<div class="ga-cash"><table class="ga-table"><thead><tr><th>Mệnh giá</th><th>Số tờ</th></tr></thead><tbody>${(d.denoms||[]).map(([k,v])=>`<tr><td>💵 ${x.esc(k)}</td><td class="num">${num(v)}</td></tr>`).join('')}</tbody></table><p class="ga-small">Tự nhân mệnh giá × số tờ để ra tổng tiền thực đếm.</p></div>`;
  if(d.type==='email')return `<div class="ga-mail"><p><b>Từ:</b> ${x.esc(d.sender||'')}</p><p><b>Chủ đề:</b> ${x.esc(d.subject||'')}</p><p>${x.esc(d.text||'')}</p></div>`;
  return `<p class="ga-paper">${x.esc(d.text||'')}</p>`;
}
function docsPanel(t,x){
  const st=currentStep(t),need=new Set(st?.docs||[]);
  const opened=t.docs.filter(d=>!d.closed);
  let sel=views(x)[t.id];
  if(!opened.some(d=>d.id===sel))sel=opened[0]?.id;
  const tabs=t.docs.map(d=>{
    const label=`<span class="ga-doc-ico">${d.closed?'📁':'📄'}</span><span class="grow">${x.esc(d.title)}<small>${x.esc(d.source)}</small></span>${d.closed&&need.has(d.id)?'<em class="ga-need">cần mở</em>':''}`;
    return d.closed?btn(x,label,'car:open',{task:t.id,doc:d.id},'ga-tab closed'):btn(x,label,'car:view',{task:t.id,doc:d.id},`ga-tab ${d.id===sel?'active':''}`);
  }).join('');
  const doc=opened.find(d=>d.id===sel);
  return `<section class="ga-docs"><h4 class="ga-sec">📂 Tài liệu trong hồ sơ <small>${opened.length}/${t.docs.length} đã mở</small></h4>
    <div class="ga-tabs">${tabs}</div>
    ${doc?`<article class="ga-viewer" aria-live="polite"><header><b>${x.esc(doc.title)}</b><small>Nguồn: ${x.esc(doc.source)}</small></header>${docBody(doc,x)}</article>`:'<p class="ga-empty">Mở một tài liệu để xem. Chỉ kết luận từ số liệu có nguồn.</p>'}
  </section>`;
}

/* ---------------------------------------------------------------- step widgets */
function summary(st,x){
  const a=st.answer;
  if(a==null)return '';
  const lab=(list,id)=>(list||[]).find(o=>o.id===id)?.label||id;
  if(st.kind==='choice')return x.esc(lab(st.options,a));
  if(st.kind==='multi')return a.map(id=>x.esc(lab(st.options,id))).join(' · ');
  if(st.kind==='number')return `${num(a)} ${x.esc(st.unit||'')}`;
  if(st.kind==='order')return a.map(id=>x.esc(lab(st.items,id))).join(' → ');
  if(st.kind==='match')return Object.entries(a).map(([l,r])=>`${x.esc(lab(st.left,l))} → <b>${x.esc(lab(st.right,r))}</b>`).join('<br>');
  if(st.kind==='fields')return (st.fields||[]).map(f=>`${x.esc(f.label)}: <b>${f.options?x.esc(lab(f.options,a[f.id])):num(a[f.id])}</b>`).join(' · ');
  if(st.kind==='entry')return (Array.isArray(a)?a:[]).map(r=>`Nợ ${x.esc(r.debit)} / Có ${x.esc(r.credit)}: <b>${num(r.amount)}</b>`).join('<br>');
  return '';
}
function acctOptions(x,st,selected){
  return `<option value="">— tài khoản —</option>`+(st.accounts||[]).map(a=>`<option value="${x.esc(a.id)}" ${a.id===selected?'selected':''}>${x.esc(a.name)}</option>`).join('');
}
function voucher(t,st,x){
  const k=dkey(t,st),d=drafts(x)[k]??={debit:[{account:'',amount:''}],credit:[{account:'',amount:''}]};
  const row=(side,r,i)=>`<div class="ga-vrow" data-side="${side}"><select class="ga-acct" aria-label="Tài khoản ${side==='debit'?'Nợ':'Có'}">${acctOptions(x,st,r.account)}</select><input class="ga-amt" type="number" inputmode="numeric" min="1" step="1" placeholder="số tiền" value="${x.esc(r.amount)}" aria-label="Số tiền">${btn(x,'✕','car:delrow',{key:k,side,i},'ga-del ghost',d[side].length<=1)}</div>`;
  const side=(id,label)=>`<div class="ga-vside ${id}"><h5>${label}</h5>${d[id].map((r,i)=>row(id,r,i)).join('')}${btn(x,`＋ Dòng ${label}`,'car:addrow',{key:k,side:id},'ghost small ga-add',d[id].length>=6)}</div>`;
  return `<div class="ga-voucher" data-entry="${x.esc(k)}">
    <div class="ga-vhead"><b>BÚT TOÁN HỢP NHẤT</b><small>${x.esc(t.title)}</small></div>
    <div class="ga-vcols">${side('debit','Nợ')}${side('credit','Có')}</div>
    <div class="ga-vfoot"><span>Tổng Nợ <b data-sum="debit">0</b></span><span>Tổng Có <b data-sum="credit">0</b></span><span class="ga-bal" data-bal>—</span></div>
    ${btn(x,'✂️ Ghi bút toán hợp nhất','car:entry',{task:t.id,step:st.id},'primary full')}
  </div>`;
}
function widget(t,st,x){
  const k=dkey(t,st),dr=drafts(x);
  if(st.kind==='choice')return `<div class="ga-options">${(st.options||[]).map(o=>x.cmd(x.esc(o.label),P+'step',{task:t.id,step:st.id,answer:o.id},'ga-opt')).join('')}</div>`;
  if(st.kind==='multi'){
    const sel=dr[k]||[];
    return `<div class="ga-checks" data-multi="${x.esc(k)}">${(st.options||[]).map(o=>`<label class="ga-check"><input type="checkbox" value="${x.esc(o.id)}" ${sel.includes(o.id)?'checked':''}><span>${x.esc(o.label)}</span></label>`).join('')}</div>${btn(x,'✔ Xác nhận lựa chọn','car:multi',{task:t.id,step:st.id},'primary full')}`;
  }
  if(st.kind==='number')return `<div class="ga-numrow"><input class="ga-input" type="number" inputmode="numeric" step="1" data-num="${x.esc(k)}" value="${x.esc(dr[k]??'')}" aria-label="${x.esc(st.title)}"><span class="ga-unit">${x.esc(st.unit||'')}</span>${btn(x,'Xác nhận','car:num',{task:t.id,step:st.id},'primary')}</div>`;
  if(st.kind==='order'){
    const ids=dr[k]??=(st.items||[]).map(i=>i.id);
    const item=id=>(st.items||[]).find(i=>i.id===id)?.label||id;
    return `<ol class="ga-order">${ids.map((id,i)=>`<li><span class="ga-ord-n">${i+1}</span><span class="grow">${x.esc(item(id))}</span>${btn(x,'↑','car:move',{key:k,i,dir:-1},'ghost ga-mv',i===0)}${btn(x,'↓','car:move',{key:k,i,dir:1},'ghost ga-mv',i===ids.length-1)}</li>`).join('')}</ol>${btn(x,'✔ Chốt thứ tự','car:order',{task:t.id,step:st.id},'primary full')}`;
  }
  if(st.kind==='match'){
    const cur=dr[k]||{};
    return `<div class="ga-match" data-match="${x.esc(k)}">${(st.left||[]).map(l=>`<label class="ga-mrow"><span>${x.esc(l.label)}</span><select data-left="${x.esc(l.id)}"><option value="">— chọn —</option>${(st.right||[]).map(r=>`<option value="${x.esc(r.id)}" ${cur[l.id]===r.id?'selected':''}>${x.esc(r.label)}</option>`).join('')}</select></label>`).join('')}</div>${btn(x,'✔ Xác nhận ghép','car:match',{task:t.id,step:st.id},'primary full')}`;
  }
  if(st.kind==='fields'){
    const cur=dr[k]||{};
    return `<div class="ga-fields" data-fields="${x.esc(k)}">${(st.fields||[]).map(f=>`<label class="ga-mrow"><span>${x.esc(f.label)}</span>${f.options?`<select data-field="${x.esc(f.id)}"><option value="">— chọn —</option>${f.options.map(o=>`<option value="${x.esc(o.id)}" ${cur[f.id]===o.id?'selected':''}>${x.esc(o.label)}</option>`).join('')}</select>`:`<span class="ga-numrow"><input class="ga-input" type="number" inputmode="numeric" step="1" data-field="${x.esc(f.id)}" value="${x.esc(cur[f.id]??'')}"><span class="ga-unit">${x.esc(f.unit||'')}</span></span>`}</label>`).join('')}</div>${btn(x,'✔ Xác nhận số liệu','car:fields',{task:t.id,step:st.id},'primary full')}`;
  }
  if(st.kind==='entry')return voucher(t,st,x);
  return '';
}
function stepsPanel(t,x){
  const ps=t.proc_state||{},rows=(t.proc||[]).map((st,i)=>{
    if(st.state==='locked')return `<li class="ga-step locked"><span class="ga-dot">🔒</span><b>${i+1}. ${x.esc(st.title)}</b></li>`;
    if(st.state==='solved')return `<li class="ga-step solved"><span class="ga-dot">✓</span><div class="grow"><b>${i+1}. ${x.esc(st.title)}</b><p class="ga-ans">${summary(st,x)}</p>${st.explain?`<p class="ga-explain">${x.esc(st.explain)}</p>`:''}</div></li>`;
    const tries=(ps.attempts||{})[st.id]||0;
    const missing=(st.docs||[]).filter(id=>t.docs.find(d=>d.id===id)?.closed);
    return `<li class="ga-step current"><span class="ga-dot">${i+1}</span><div class="grow"><b>${x.esc(st.title)}</b><p class="ga-prompt">${x.esc(st.prompt||'')}</p>
      ${missing.length?`<p class="ga-warn">📁 Mở trước: ${missing.map(id=>x.esc(t.docs.find(d=>d.id===id).title)).join(', ')}</p>`:''}
      ${st.tip?`<p class="ga-tip">💡 ${x.esc(st.tip)}</p>`:''}
      ${widget(t,st,x)}
      <div class="ga-stepfoot">${tries?`<small class="ga-small">Đã thử ${tries} lần</small>`:'<span></span>'}${st.tip?'':x.cmd('💡 Xin gợi ý',P+'hint',{task:t.id},'ghost small')}</div></div></li>`;
  }).join('');
  return `<section class="ga-proc"><h4 class="ga-sec">🧾 Quy trình <small>${(ps.solved||[]).length}/${ps.total||0} bước</small></h4><ol class="ga-steps">${rows}</ol>${handover(t,x)}</section>`;
}
function handover(t,x){
  if(!t.handover_options)return '';
  const sel=x.ui.note?.[t.id]||'specific';
  return `<div class="ga-handover"><h5>📝 Ghi chú bàn giao</h5>${t.handover_options.map(o=>`<label class="ga-check"><input type="radio" name="ga-note-${x.esc(t.id)}" value="${x.esc(o.id)}" ${o.id===sel?'checked':''}><span>${x.esc(o.label)}</span></label>`).join('')}
    ${btn(x,'📤 Nộp hồ sơ','car:submit',{task:t.id},'primary full big')}</div>`;
}

/* ---------------------------------------------------------------- side: group chart & consolidation journal */
function groupChart(x){
  const ents=x.cc.entities||[],parent=ents.find(e=>e.own==null),subs=ents.filter(e=>e.own!=null);
  if(!parent)return '';
  return `<section class="ga-card"><h4 class="ga-sec">🏢 Cơ cấu tập đoàn</h4><div class="ga-org">
    <div class="ga-node parent"><span>${x.esc(parent.emoji)}</span><b>${x.esc(parent.short)}</b><small>${x.esc(parent.name)}</small></div>
    <ul class="ga-subs">${subs.map(e=>`<li class="ga-node ${e.own<100?'nci':''} ${e.cur!=='xu'?'fx':''}"><span>${x.esc(e.emoji)}</span><b>${x.esc(e.short)}</b><small>${e.own}%${e.own<100?` · CĐKKS ${100-e.own}%`:''}${e.cur!=='xu'?` · báo cáo bằng ${x.esc(e.cur)}`:''}</small></li>`).join('')}</ul></div></section>`;
}
function ledgerPanel(x){
  const d=x.room.data||{},led=d.elim||{},ids=Object.keys(led).sort();
  const dr=ids.reduce((s,k)=>s+Math.max(0,led[k]),0),cr=ids.reduce((s,k)=>s+Math.max(0,-led[k]),0);
  const rows=ids.map(k=>`<tr><td><b>${x.esc(k)}</b> <small>${x.esc(acct(x,k).replace(/^\d+ · /,''))}</small></td><td class="num">${led[k]>0?num(led[k]):''}</td><td class="num">${led[k]<0?num(-led[k]):''}</td></tr>`).join('');
  const last=(d.entries||[]).slice(-3).reverse().map(e=>`<li><b>${x.esc(e.title)}</b><small>${e.lines.map(([a,b,m])=>`Nợ ${x.esc(a)}/Có ${x.esc(b)} ${num(m)}`).join(' · ')}</small></li>`).join('');
  const ms=(x.cc.milestones||[]).map(m=>`<li class="${(d.milestones||[]).includes(m.id)?'done':''}">${(d.milestones||[]).includes(m.id)?'✓':'○'} ${x.esc(m.name)}</li>`).join('');
  return `<aside class="ga-side">
    <section class="ga-card"><h4 class="ga-sec">🗓️ ${x.esc(d.period?.label||'Kỳ khóa sổ quý')}</h4><ul class="ga-ms">${ms}</ul></section>
    ${groupChart(x)}
    <section class="ga-card"><h4 class="ga-sec">✂️ Sổ bút toán hợp nhất <span class="ga-badge ${dr===cr?'ok':'bad'}">${dr===cr?'Nợ = Có':'Lệch'}</span></h4>
      ${ids.length?`<div class="ga-scroll"><table class="ga-table tb"><thead><tr><th>TK</th><th>Nợ</th><th>Có</th></tr></thead><tbody>${rows}</tbody><tfoot><tr><td>Tổng</td><td class="num">${num(dr)}</td><td class="num">${num(cr)}</td></tr></tfoot></table></div>`:'<p class="ga-empty">Quý này chưa có bút toán loại trừ. Bút toán hợp nhất chỉ nằm ở cấp tập đoàn — không ghi vào sổ công ty con — và làm lại mỗi quý.</p>'}
    </section>
    ${last?`<section class="ga-card"><h4 class="ga-sec">📒 Bút toán gần đây</h4><ul class="ga-journal">${last}</ul></section>`:''}
  </aside>`;
}

/* ---------------------------------------------------------------- DOM → draft sync (no input hook: tick + actions) */
function readEntry(box){
  const out={debit:[],credit:[]};
  box.querySelectorAll('.ga-vrow').forEach(r=>out[r.dataset.side].push({account:r.querySelector('select').value,amount:r.querySelector('input').value}));
  return out;
}
function sync(root,x){
  const dr=drafts(x);
  root.querySelectorAll('[data-multi]').forEach(b=>{dr[b.dataset.multi]=[...b.querySelectorAll('input:checked')].map(i=>i.value);});
  root.querySelectorAll('[data-num]').forEach(i=>{dr[i.dataset.num]=i.value;});
  root.querySelectorAll('[data-match]').forEach(b=>{const o={};b.querySelectorAll('select').forEach(s=>{if(s.value)o[s.dataset.left]=s.value;});dr[b.dataset.match]=o;});
  root.querySelectorAll('[data-fields]').forEach(b=>{const o={};b.querySelectorAll('[data-field]').forEach(s=>{o[s.dataset.field]=s.value;});dr[b.dataset.fields]=o;});
  root.querySelectorAll('[data-entry]').forEach(b=>{dr[b.dataset.entry]=readEntry(b);});
  root.querySelectorAll('input[type=radio][name^="ga-note-"]:checked').forEach(r=>{(x.ui.note??={})[r.name.slice(8)]=r.value;});
}
const rootOf=el=>el.closest('.career-job')||document;
const intOf=v=>{const s=String(v??'').trim();return /^-?\d+$/.test(s)?Number(s):null;};
function stepOf(x,data){
  const t=(x.room.tasks||[]).find(v=>v.id===data.task);
  return [t,t&&(t.proc||[]).find(s=>s.id===data.step)];
}
const send=(x,t,st,answer)=>x.send(P+'step',{task:t.id,step:st.id,answer});

/* ---------------------------------------------------------------- office: clock, deadline, trust, luck of the day */
const hhmm=m=>`${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`;
const span=m=>m>=60?`${Math.floor(m/60)} giờ${m%60?` ${m%60} phút`:''}`:`${m} phút`;
function dueOf(t,x){
  if(typeof t?.due!=='number')return null;
  const o=x.room.data?.office||{},clock=Number(o.clock)||480,day=x.room.day;
  const overdue=day>(t.due_day??day)||clock>t.due,left=t.due-clock;
  return {time:hhmm(t.due),overdue,soon:!overdue&&left<=45,left:Math.max(0,left)};
}
function officeBar(t,x){
  const d=x.room.data||{},o=d.office;if(!o)return '';
  const mod=d.today?.mod,due=t&&t.status!=='completed'?dueOf(t,x):null,trust=Math.max(0,Math.min(100,Number(o.trust)||0));
  const pay=mod?.id==='crunch'?18:12,ask=`Ở lại tới 20:00? Được trả ${pay} xu, mai vào muộn 30 phút vì mệt.`;
  const chip=due?`<span class="ga-chip ${due.overdue?'bad':due.soon?'warn':''}">⏰ Hạn ${x.esc(due.time)} · ${due.overdue?'đã trễ':'còn '+span(due.left)}</span>`:'';
  let alert='';
  if(o.locked)alert=`<p class="ga-alert bad">🔒 20:00 — văn phòng khóa cửa. Khép ngày, mai làm tiếp; việc dở được giữ nguyên.</p>`;
  else if(o.closed)alert=`<div class="ga-alert warn"><span>🌇 17:30 — hết giờ hành chính.</span>${x.confirmCmd(`🌙 Ở lại tăng ca (+${pay} xu)`,'ga_overtime',{},ask,'small')}</div>`;
  else if(o.can_overtime)alert=`<div class="ga-alert"><span>Sắp hết giờ. Còn việc dở?</span>${x.confirmCmd(`🌙 Đăng ký tăng ca (+${pay} xu)`,'ga_overtime',{},ask,'ghost small')}</div>`;
  return `<section class="ga-office" aria-label="Giờ làm việc hôm nay">
    <div class="ga-obar"><span class="ga-clock"><b>🕗 ${x.esc(o.time)}</b><small>${o.overtime?'tăng ca tới 20:00':o.lunch?'nghỉ trưa 12:00':'tan sở 17:30'}</small></span>${chip}
      <span class="ga-trust" title="Chị Mai Anh tin bạn ${trust}/100"><small>Chị Mai Anh: ${x.esc(o.trust_label||'')}</small><span class="bar ${trust<35?'low':trust>=75?'high':''}"><i style="width:${trust}%"></i></span></span></div>
    ${mod&&mod.id!=='normal'?`<p class="ga-mod"><b>${x.esc(mod.emoji)} ${x.esc(mod.name)}</b> ${x.esc(mod.text)}</p>`:''}
    ${o.tired?'<p class="ga-small">😮‍💨 Hôm qua tăng ca nên sáng nay vào muộn 30 phút.</p>':''}
    ${alert}</section>`;
}
function rulesBox(x){
  const rs=x.room.data?.today?.rules||[];if(!rs.length)return '';
  const fresh=rs.filter(r=>r.new).length;
  return `<section class="ga-rulebox" aria-label="Quy định đối chiếu"><h4 class="ga-sec">📋 Quy định đối chiếu ${fresh?`<span class="ga-new">${fresh} mới</span>`:''}</h4>
    <div class="ga-rules-row">${rs.map(r=>`<article class="ga-rule ${r.new?'new':''}"><b>${x.esc(r.emoji)} ${x.esc(r.title)}${r.new?' <em>MỚI</em>':''}</b><p>${x.esc(r.text)}</p></article>`).join('')}</div></section>`;
}
function fxCard(x,hot){
  const f=x.room.data?.today?.fx;if(!f)return '';
  const arrow=f.delta>0?`▲${f.delta}`:f.delta<0?`▼${-f.delta}`:'=';
  return `<section class="ga-fx ${hot?'hot':''}" aria-label="Bảng tỷ giá hôm nay"><span class="ga-fx-big">💱 <b>${num(f.closing)}</b><small>xu/NM cuối kỳ</small></span>
    <span class="ga-fx-move ${f.delta>0?'up':f.delta<0?'down':''}">${arrow} <small>so với hôm qua (${num(f.prev)})</small></span>
    <small class="ga-fx-rest">Bình quân ${num(f.average)} · lịch sử ${num(f.hist)}</small></section>`;
}

/* ---------------------------------------------------------------- the intercompany matching board */
const msel=(x,t)=>((x.ui.msel??={})[t.id]??={a:null,b:null});
const money=(l)=>`${l.kind==='pay'?'−':''}${num(l.amount)}`;
function waiting(t,x){return typeof t.wait==='number'&&(Number(x.room.data?.office?.clock)||480)<t.wait;}
function lineCard(t,l,x,sel){
  const st=l.state,tags=Object.fromEntries((t.tags||[]).map(g=>[g.id,g]));
  const badge=!st?'':st.k==='pair'?`<span class="ga-lbadge pair">🔗 ${st.no||''}${st.cause==='fx'?' · 💱':st.cause==='typo'?' · ⌨️':''}</span>`
    :`<span class="ga-lbadge tag">${x.esc(tags[st.tag]?.emoji||'•')} ${x.esc(tags[st.tag]?.label||st.tag)}</span>`;
  const inner=`<span class="ga-lrow"><b class="ga-ref">${x.esc(l.ref)}</b><b class="ga-lamt">${money(l)}</b></span><span class="ga-ltext">${x.esc(l.date)} · ${x.esc(l.text)}</span>${badge}`;
  if(st)return `<li class="ga-line done ${st.k}">${inner}</li>`;
  const on=sel[l.side]===l.id;
  return `<li>${btn(x,inner,'car:msel',{task:t.id,line:l.id,side:l.side},`ga-line ${on?'on':''} ${l.hinted?'hinted':''}`).replace('<button ',`<button aria-pressed="${on}" `)}</li>`;
}
function actionBar(t,x,sel){
  const L=Object.fromEntries((t.lines||[]).map(l=>[l.id,l])),a=L[sel.a],b=L[sel.b];
  const clear=btn(x,'✕','car:mclear',{task:t.id},'ghost ga-x').replace('<button ','<button aria-label="Bỏ chọn" ');
  if(a&&b){
    if(a.amount===b.amount)return `<div class="ga-abar" role="group" aria-label="Ghép cặp"><span class="grow ga-apick"><b>${x.esc(a.ref)}</b> ↔ <b>${x.esc(b.ref)}</b> · cùng ${num(a.amount)} xu</span>${clear}
      ${x.cmd(`🔗 Ghép cặp này`,'ga_pair',{task:t.id,a:a.id,b:b.id},'primary full')}</div>`;
    return `<div class="ga-abar" role="group" aria-label="Ghép cặp lệch tiền"><span class="grow ga-apick"><b>${x.esc(a.ref)}</b> ↔ <b>${x.esc(b.ref)}</b> · lệch ${num(Math.abs(a.amount-b.amount))} xu — vì sao?</span>${clear}
      <div class="ga-chips">${(t.causes||[]).map(c=>x.cmd(`${x.esc(c.emoji)} ${x.esc(c.label)}`,'ga_pair',{task:t.id,a:a.id,b:b.id,cause:c.id},'ga-chipbtn')).join('')}</div></div>`;
  }
  const one=a||b;if(!one)return '';
  const tip=one.tip?`<p class="ga-tip">💡 ${x.esc(one.tip)}</p>`:'';
  return `<div class="ga-abar" role="group" aria-label="Dòng chỉ có một bên"><span class="grow ga-apick"><b>${x.esc(one.ref)}</b> · ${money(one)} xu — chạm dòng ${one.side==='a'?'bên mua':'bên bán'} để ghép, hoặc chọn lý do:</span>${clear}
    ${tip}<div class="ga-chips">${(t.tags||[]).map(g=>x.cmd(`${x.esc(g.emoji)} ${x.esc(g.label)}`,'ga_tag',{task:t.id,line:one.id,tag:g.id},'ga-chipbtn')).join('')}
    ${one.hinted?'':x.cmd('💡 Gợi ý','ga_hint',{task:t.id,line:one.id},'ghost small')}</div></div>`;
}
function meterBox(t,x){
  const m=t.meter||{},n=t.names||{},pct=m.total?Math.round(100*m.resolved/m.total):0;
  const gap=Math.abs(Number(m.gap)||0);
  const status=m.ready?`<b class="ga-ok">✓ Hai sổ khớp: ${num(m.agreed)} xu</b>`:`Còn lệch chưa có lý do: <b class="${gap?'ga-bad':''}">${num(gap)} xu</b> · ${m.resolved}/${m.total} dòng`;
  return `<section class="ga-meter" aria-live="polite"><div class="ga-mrow2"><span>Phải thu theo ${x.esc(n.a||'')} <b>${num(m.ra)}</b></span><span>Phải trả theo ${x.esc(n.b||'')} <b>${num(m.rb)}</b></span></div>
    <div class="ga-mbar"><i style="width:${pct}%"></i></div><p>${status}</p></section>`;
}
function boardView(t,x){
  const sel=msel(x,t),L=Object.fromEntries((t.lines||[]).map(l=>[l.id,l]));
  for(const s of ['a','b'])if(sel[s]&&(!L[sel[s]]||L[sel[s]].state))sel[s]=null;
  const n=t.names||{},m=t.meter||{},hot=n.fx||x.room.data?.today?.mod?.id==='fx_swing';
  const evid=(t.docs||[]).length?`<section class="ga-evid"><h4 class="ga-sec">🔎 Bằng chứng <small>${t.docs.length} tờ</small></h4><ul>${t.docs.map(d=>`<li><b>${x.esc(d.title)}</b><small>${x.esc(d.source)}</small><p>${x.esc(d.text||'')}</p></li>`).join('')}</ul></section>`:'';
  if(waiting(t,x))return `<div class="ga-board"><div class="ga-board-main"><section class="ga-wait"><p class="ga-wait-big">⏳ Gói báo cáo hẹn <b>${x.esc(hhmm(t.wait))}</b> mới về</p>
      <p class="ga-small">Làm hồ sơ khác trước — đồng hồ chỉ chạy khi bạn làm việc. Hoặc gọi giục cho kịp hạn.</p>
      ${x.cmd('📞 Gọi giục anh Phong (10 phút)','ga_chase',{task:t.id},'primary full')}</section></div><div class="ga-board-side">${rulesBox(x)}</div></div>`;
  const col=(side,title)=>`<section class="ga-col" aria-label="${x.esc(title)}"><h4 class="ga-colh">${side==='a'?'📤':'📥'} ${x.esc(title)}</h4><ul class="ga-lines">${(t.lines||[]).filter(l=>l.side===side).map(l=>lineCard(t,l,x,sel)).join('')}</ul></section>`;
  const bar=m.ready&&t.status!=='completed'?`<div class="ga-abar ready">${x.confirmCmd(`✂️ Loại trừ ${num(m.agreed)} xu`,'ga_submit',{task:t.id},`Chốt đối chiếu và ghi bút toán loại trừ Nợ 331 / Có 131: ${num(m.agreed)} xu?`,'primary full big')}</div>`:actionBar(t,x,sel);
  const guide=!sel.a&&!sel.b&&!m.ready?'<p class="ga-guide">Chạm một dòng bên bán và dòng cùng chứng từ bên mua để <b>ghép</b>. Dòng chỉ có một bên: chạm rồi chọn <b>lý do</b>.</p>':'';
  return `<div class="ga-board"><div class="ga-board-main">${meterBox(t,x)}${guide}
      <div class="ga-cols">${col('a','Sổ phải thu · '+(n.a||''))}${col('b','Sổ phải trả · '+(n.b||''))}</div>${bar}</div>
    <div class="ga-board-side">${fxCard(x,hot)}${evid}${rulesBox(x)}</div></div>`;
}
function boardRecap(x){
  const t=(x.room.tasks||[]).find(v=>v.id===x.ui.lastBoard);
  if(!t||t.status!=='completed'||!t.lines)return '';
  const n=t.names||{},m=t.meter||{};
  const note=(t.lines||[]).filter(l=>l.state&&(l.state.k==='tag'||(l.state.cause&&l.side==='a')));
  return `<section class="ga-recap" role="status"><h4>🔁 Đối chiếu vừa chốt · ${x.esc(n.a||'')} ↔ ${x.esc(n.b||'')}</h4>
    <p>Loại trừ <b>${num(m.agreed)} xu</b> (Nợ 331 / Có 131)${t.mistakes?` · ${t.mistakes} lần sửa sai`:' · không sửa lần nào'}.</p>
    ${note.length?`<ul>${note.map(l=>`<li>${x.esc(l.why||'')}</li>`).join('')}</ul>`:''}</section>`;
}

export default {
  id:'group_accounting',
  css:true,
  next(t,x){
    if(!t.known)return t.variant==='match'?'Nhận hai sổ đối chiếu':'Nhận hồ sơ từ người giao việc';
    if(t.variant==='match'){
      const m=t.meter||{};
      if(x&&waiting(t,x))return 'Chờ gói báo cáo về, hoặc gọi giục';
      if(t.status==='completed')return 'Đã loại trừ';
      return m.ready?'Hai sổ đã khớp — bấm “Loại trừ”':`Ghép và tìm lý do: còn ${(m.total||0)-(m.resolved||0)} dòng`;
    }
    const st=(t.proc||[]).find(s=>s.state==='current');
    if(st){
      const miss=(st.docs||[]).filter(id=>(t.docs||[]).find(d=>d.id===id)?.closed);
      return miss.length?'Mở tài liệu cần thiết trước khi làm bước này':`Bước ${(t.proc_state?.at||0)+1}/${t.proc_state?.total||0}: ${st.title}`;
    }
    return t.handover?'Đã nộp hồ sơ':'Chọn ghi chú bàn giao và nộp hồ sơ';
  },
  job(t,x){
    const who=x.npc(t.npc),k=t.kind_info||{},timed=typeof t.due==='number',board=t.variant==='match',bar=officeBar(t,x);
    x.ui.lastBoard=board?t.id:null;
    const head=t.known&&timed?`<article class="ga-head compact"><div class="ga-who">${x.portrait(who,40)}<div class="grow"><small class="ga-small">${x.esc(k.emoji||'🧾')} ${x.esc(k.name||'Hồ sơ hợp nhất')} · ${x.esc(who.display_name)}</small><p class="ga-quote">“${x.esc(t.opening)}”</p></div></div></article>`
      :`<article class="ga-head"><div class="ga-who">${x.portrait(who,52)}<div class="grow"><span class="ga-kind">${x.esc(k.emoji||'🧾')} ${x.esc(k.name||'Hồ sơ hợp nhất')}</span><h3>${x.esc(t.title)}</h3><p class="ga-quote">“${x.esc(t.opening)}”</p><small class="ga-small">${x.esc(who.display_name)}${who.role?' · '+x.esc(who.role):''}</small></div></div>
      ${timed?'':`<div class="patience" title="Kiên nhẫn của người giao việc"><div class="bar ${t.patience<50?'low':''}"><i style="width:${Number(t.patience)||0}%"></i></div><small>${Number(t.patience)||0}%</small></div>`}</article>`;
    if(!t.known)return `<div class="career-job ga">${bar}${head}<div class="ga-card">${x.cmd(board?'📥 Nhận hai sổ đối chiếu':'📥 Nhận hồ sơ','ask',{task:t.id},'primary full big')}<p class="ga-small">${board?'Ghép từng dòng sổ bên bán với sổ bên mua, tìm lý do cho dòng chỉ có một bên, khớp hết thì loại trừ. Mỗi lần ghép sai tốn 20 phút soát lại.':'Nhận hồ sơ để xem đề bài, chứng từ và các bước cần làm.'}</p></div>${board?rulesBox(x):ledgerPanel(x)}</div>`;
    if(board)return `<div class="career-job ga">${bar}${head}${boardView(t,x)}</div>`;
    return `<div class="career-job ga">${bar}${head}<p class="ga-brief">🎯 ${x.esc(t.brief||'')}</p>
      <div class="ga-bench"><div class="ga-main">${docsPanel(t,x)}${stepsPanel(t,x)}</div>${ledgerPanel(x)}</div></div>`;
  },
  idle(x){
    const d=x.room.data||{};if(!d.office)return '';
    return `<div class="career-job ga">${boardRecap(x)}${officeBar(null,x)}${rulesBox(x)}</div>`;
  },
  summary(data,x){
    if(!data||typeof data!=='object')return '';
    const o=data.office||{},rows=[],MS=Object.fromEntries((x.cc.milestones||[]).map(m=>[m.id,m.name]));
    const row=(k,v)=>rows.push(`<div class="kv-row"><span>${x.esc(k)}</span><b>${x.esc(v)}</b></div>`);
    if(data.mod?.name)row('Hôm nay',`${data.mod.emoji||''} ${data.mod.name}`);
    if(data.boards)row('Bàn đối chiếu đã chốt',String(data.boards));
    if(data.dossiers)row('Hồ sơ hoàn tất',String(data.dossiers));
    if(data.slips)row('Lần sửa sai',String(data.slips));
    if(data.posted)row('Bút toán loại trừ đã ghi',String(data.posted));
    if(o.late)row('Việc nộp trễ hạn',String(o.late));
    if(o.fines)row('Bị trừ tiền',`${o.fines} xu`);
    if(o.overtime)row('Tăng ca','Có (mai vào muộn 30 phút)');
    if(o.carried)row('Việc dở để sáng mai',`${o.carried} (hạn 10:00)`);
    if(Array.isArray(data.milestones)&&data.milestones.length)row('Mốc quý đã xong',data.milestones.map(m=>MS[m]||m).join(', '));
    if(typeof data.quarter_done==='number')row('Khép quý',`${data.quarter_done}/${(x.cc.milestones||[]).length||6} mốc`);
    const ch=Number(o.trust_change)||0;
    const trust=o.trust_label?`<p class="ga-sum-trust">👩‍💼 Chị Mai Anh: <b>${x.esc(o.trust_label)}</b> (${o.trust}/100${ch?`, ${ch>0?'+':''}${ch} hôm nay`:''})</p>`:'';
    const note=r=>r&&typeof r==='object'?`<p class="ga-sum-note ${r.ok?'ok':'bad'}">${r.ok?'🏅':'🔍'} ${x.esc(r.text||'')}</p>`:'';
    if(!rows.length&&!trust&&!data.audit&&!data.board)return '';
    return `<article class="card space-top ga-sum"><h4 class="section-title">🏢 Bàn hợp nhất hôm nay</h4>${note(data.audit)}${note(data.board)}${trust}${rows.length?`<div class="kv">${rows.join('')}</div>`:''}</article>`;
  },
  tick(root,x){
    sync(root,x);
    root.querySelectorAll('[data-entry]').forEach(b=>{
      const e=readEntry(b),sum=side=>e[side].reduce((s,r)=>s+(intOf(r.amount)>0?intOf(r.amount):0),0);
      const d=sum('debit'),c=sum('credit');
      b.querySelector('[data-sum="debit"]').textContent=num(d);
      b.querySelector('[data-sum="credit"]').textContent=num(c);
      const bal=b.querySelector('[data-bal]');
      bal.textContent=!d&&!c?'Chưa nhập số':d===c?'✓ Cân':`Lệch ${num(Math.abs(d-c))}`;
      bal.className='ga-bal '+(!d&&!c?'':d===c?'ok':'bad');
    });
  },
  actions:{
    msel(d,el,x){const t=(x.room.tasks||[]).find(v=>v.id===d.task);if(!t)return;const s=msel(x,t);s[d.side]=s[d.side]===d.line?null:d.line;x.render();},
    mclear(d,el,x){const t=(x.room.tasks||[]).find(v=>v.id===d.task);if(!t)return;const s=msel(x,t);s.a=s.b=null;x.render();},
    async open(data,el,x){views(x)[data.task]=data.doc;await x.send(P+'open',{task:data.task,doc:data.doc});},
    view(data,el,x){sync(rootOf(el),x);views(x)[data.task]=data.doc;x.render();},
    async multi(data,el,x){
      sync(rootOf(el),x);const [t,st]=stepOf(x,data);if(!st)return;
      const ans=drafts(x)[dkey(t,st)]||[];
      if(!ans.length){x.toast('Chọn ít nhất một ô.',true);return;}
      await send(x,t,st,ans);
    },
    async num(data,el,x){
      sync(rootOf(el),x);const [t,st]=stepOf(x,data);if(!st)return;
      const v=intOf(drafts(x)[dkey(t,st)]);
      if(v===null){x.toast('Nhập một số nguyên (không dấu chấm, không chữ).',true);return;}
      await send(x,t,st,v);
    },
    move(data,el,x){
      sync(rootOf(el),x);const list=drafts(x)[data.key];if(!list)return;
      const i=Number(data.i),j=i+Number(data.dir);if(j<0||j>=list.length)return;
      [list[i],list[j]]=[list[j],list[i]];x.render();
    },
    async order(data,el,x){const [t,st]=stepOf(x,data);if(!st)return;await send(x,t,st,drafts(x)[dkey(t,st)]||st.items.map(i=>i.id));},
    async match(data,el,x){
      sync(rootOf(el),x);const [t,st]=stepOf(x,data);if(!st)return;
      const ans=drafts(x)[dkey(t,st)]||{};
      if(Object.keys(ans).length<st.left.length){x.toast('Ghép đủ tất cả các dòng trước khi xác nhận.',true);return;}
      await send(x,t,st,ans);
    },
    async fields(data,el,x){
      sync(rootOf(el),x);const [t,st]=stepOf(x,data);if(!st)return;
      const raw=drafts(x)[dkey(t,st)]||{},ans={};
      for(const f of st.fields){
        if(f.options){if(!raw[f.id]){x.toast(`Chọn “${f.label}”.`,true);return;}ans[f.id]=raw[f.id];}
        else{const v=intOf(raw[f.id]);if(v===null){x.toast(`Ô “${f.label}” cần một số nguyên.`,true);return;}ans[f.id]=v;}
      }
      await send(x,t,st,ans);
    },
    addrow(data,el,x){sync(rootOf(el),x);const d=drafts(x)[data.key];if(d&&d[data.side].length<6){d[data.side].push({account:'',amount:''});x.render();}},
    delrow(data,el,x){sync(rootOf(el),x);const d=drafts(x)[data.key];if(d&&d[data.side].length>1){d[data.side].splice(Number(data.i),1);x.render();}},
    async entry(data,el,x){
      sync(rootOf(el),x);const [t,st]=stepOf(x,data);if(!st)return;
      const d=drafts(x)[dkey(t,st)],ans={debit:[],credit:[]};
      for(const side of ['debit','credit'])for(const r of d[side]){
        const a=intOf(r.amount);
        if(!r.account&&!String(r.amount||'').trim())continue;
        if(!r.account||!(a>0)){x.toast('Mỗi dòng cần chọn tài khoản và nhập số tiền nguyên dương.',true);return;}
        ans[side].push({account:r.account,amount:a});
      }
      if(!ans.debit.length||!ans.credit.length){x.toast('Phiếu cần ít nhất một dòng Nợ và một dòng Có.',true);return;}
      const sd=ans.debit.reduce((s,r)=>s+r.amount,0),sc=ans.credit.reduce((s,r)=>s+r.amount,0);
      if(sd!==sc){x.toast(`Chưa cân: Tổng Nợ ${num(sd)} ≠ Tổng Có ${num(sc)}.`,true);return;}
      await send(x,t,st,ans);
    },
    async submit(data,el,x){
      sync(rootOf(el),x);
      const note=x.ui.note?.[data.task]||'specific';
      if(!await x.ask('Nộp hồ sơ','Nộp hồ sơ kèm ghi chú bàn giao đã chọn? Người giao việc sẽ nhận xét ngay.','Nộp'))return;
      await x.send(P+'submit',{task:data.task,note,confirm:true});
    },
  },
};
