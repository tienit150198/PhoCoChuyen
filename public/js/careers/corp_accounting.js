/** Kế toán doanh nghiệp · Công ty Mây Tre Xanh — bàn kế toán (plugin client module).
 *  Document tray (hóa đơn soi được lỗi, sao kê, sổ quỹ…), procedure steps with hands-on widgets
 *  (phiếu kế toán Nợ/Có tự cân, bảng khớp, sắp xếp), and the running trial balance on the side.
 *  No inline handlers: every button goes through data-command / data-action="car:*". */
const P='ca_';
const num=v=>Number(v||0).toLocaleString('vi-VN');
const dkey=(t,st)=>`${t.id}:${st.id}`;
const drafts=x=>(x.ui.drafts??={});
const views=x=>(x.ui.view??={});
const currentStep=t=>(t.proc||[]).find(s=>s.state==='current');
const acct=(x,id)=>(x.cc.accounts||[]).find(a=>a.id===id)?.name||id;
const btn=(x,label,action,data={},style='',disabled=false)=>x.button(label,action,data,style).replace('<button ',`<button ${disabled?'disabled ':''}`);
const INVOICE_FLAGS=['mst','buyer','qty','vat','total','sign'];

/* ---------------------------------------------------------------- documents */
function invoiceDoc(d,x,flags){
  const zone=(id,inner,cls='')=>flags?`<button type="button" class="ca-zone ${cls} ${flags.sel.includes(id)?'flagged':''}" data-action="car:flag" data-flag="${id}" data-key="${x.esc(flags.key)}" aria-pressed="${flags.sel.includes(id)}">${inner}</button>`:`<div class="ca-zone ${cls}">${inner}</div>`;
  const lines=(d.lines||[]).map(([item,unit,qty,price,amount],i)=>`<tr><td>${i+1}</td><td>${x.esc(item)}</td><td>${x.esc(unit)}</td><td class="num">${zone('qty',num(qty),'inline')}</td><td class="num">${num(price)}</td><td class="num">${num(amount)}</td></tr>`).join('');
  return `<div class="ca-invoice">
    <header><b>HÓA ĐƠN GIÁ TRỊ GIA TĂNG</b><small>(Bản thể hiện của hóa đơn điện tử)</small>
      <div class="ca-inv-no"><span>Ký hiệu <b>${x.esc(d.symbol)}</b></span><span>Số <b>${x.esc(d.number)}</b></span><span>Ngày <b>${x.esc(d.date)}</b></span></div></header>
    ${zone('mst',`<span class="lbl">Đơn vị bán</span><b>${x.esc(d.seller.name)}</b><span>MST: <b class="mono">${x.esc(d.seller.mst)}</b></span><small>${x.esc(d.seller.addr)}</small>`,'party')}
    ${zone('buyer',`<span class="lbl">Đơn vị mua</span><b>${x.esc(d.buyer.name)}</b><span>MST: <b class="mono">${x.esc(d.buyer.mst)}</b></span><small>${x.esc(d.buyer.addr)}</small>`,'party')}
    <div class="ca-scroll"><table class="ca-table"><thead><tr><th>STT</th><th>Hàng hóa, dịch vụ</th><th>ĐVT</th><th>SL</th><th>Đơn giá</th><th>Thành tiền</th></tr></thead><tbody>${lines}</tbody></table></div>
    <div class="ca-inv-sum">
      <div><span>Cộng tiền hàng</span><b>${num(d.base)}</b></div>
      ${zone('vat',`<span>Thuế suất GTGT ${x.esc(d.rate)}% · Tiền thuế</span><b>${num(d.vat)}</b>`,'row')}
      ${zone('total',`<span>Tổng cộng thanh toán</span><b>${num(d.total)}</b>`,'row strong')}
    </div>
    ${zone('sign',d.signed?`<span class="ca-stamp">✔ Đã ký số</span><small>Ký bởi: ${x.esc(d.signer)}</small>`:`<span class="ca-stamp missing">Chưa có chữ ký số</span><small>Chữ ký người bán: —</small>`,'sign')}
    ${flags?'<p class="ca-small">Chạm vào ô nghi có lỗi để đánh dấu (chạm lại để bỏ).</p>':''}
  </div>`;
}
function tableDoc(d,x){
  const head=`<tr>${d.cols.map(c=>`<th>${x.esc(c)}</th>`).join('')}</tr>`;
  const body=(d.rows||[]).map(r=>`<tr>${r.map(v=>`<td>${x.esc(v)}</td>`).join('')}</tr>`).join('');
  const foot=(d.foot||[]).map(r=>`<tr>${r.map(v=>`<td>${x.esc(v)}</td>`).join('')}</tr>`).join('');
  return `<div class="ca-scroll"><table class="ca-table ${d.wide?'wide':''}"><thead>${head}</thead><tbody>${body}</tbody>${foot?`<tfoot>${foot}</tfoot>`:''}</table></div>${d.note?`<p class="ca-small">${x.esc(d.note)}</p>`:''}`;
}
function docBody(d,x,flags){
  if(d.type==='invoice')return invoiceDoc(d,x,flags);
  if(d.type==='table')return tableDoc(d,x);
  if(d.type==='kv')return `<dl class="ca-kv">${(d.rows||[]).map(([k,v])=>`<dt>${x.esc(k)}</dt><dd>${x.esc(v)}</dd>`).join('')}</dl>`;
  if(d.type==='cash')return `<div class="ca-cash"><table class="ca-table"><thead><tr><th>Mệnh giá</th><th>Số tờ</th></tr></thead><tbody>${(d.denoms||[]).map(([k,v])=>`<tr><td>💵 ${x.esc(k)}</td><td class="num">${num(v)}</td></tr>`).join('')}</tbody></table><p class="ca-small">Tự nhân mệnh giá × số tờ để ra tổng tiền thực đếm.</p></div>`;
  if(d.type==='email')return `<div class="ca-mail"><p><b>Từ:</b> ${x.esc(d.sender||'')}</p><p><b>Chủ đề:</b> ${x.esc(d.subject||'')}</p><p>${x.esc(d.text||'')}</p></div>`;
  return `<p class="ca-paper">${x.esc(d.text||'')}</p>`;
}
function docsPanel(t,x){
  const st=currentStep(t),need=new Set(st?.docs||[]);
  const opened=t.docs.filter(d=>!d.closed);
  let sel=views(x)[t.id];
  if(!opened.some(d=>d.id===sel))sel=opened[0]?.id;
  const tabs=t.docs.map(d=>{
    const label=`<span class="ca-doc-ico">${d.closed?'📁':'📄'}</span><span class="grow">${x.esc(d.title)}<small>${x.esc(d.source)}</small></span>${d.closed&&need.has(d.id)?'<em class="ca-need">cần mở</em>':''}`;
    return d.closed?btn(x,label,'car:open',{task:t.id,doc:d.id},'ca-tab closed'):btn(x,label,'car:view',{task:t.id,doc:d.id},`ca-tab ${d.id===sel?'active':''}`);
  }).join('');
  const doc=opened.find(d=>d.id===sel);
  let flags=null;
  if(doc?.type==='invoice'&&st?.kind==='multi'&&(st.options||[]).some(o=>INVOICE_FLAGS.includes(o.id))){
    const k=dkey(t,st);flags={key:k,sel:drafts(x)[k]||[]};
  }
  return `<section class="ca-docs"><h4 class="ca-sec">📂 Chứng từ trong hồ sơ <small>${opened.length}/${t.docs.length} đã mở</small></h4>
    <div class="ca-tabs">${tabs}</div>
    ${doc?`<article class="ca-viewer" aria-live="polite"><header><b>${x.esc(doc.title)}</b><small>Nguồn: ${x.esc(doc.source)}</small></header>${docBody(doc,x,flags)}</article>`:'<p class="ca-empty">Mở một chứng từ để xem. Chứng từ gốc là căn cứ duy nhất để ghi sổ.</p>'}
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
  const row=(side,r,i)=>`<div class="ca-vrow" data-side="${side}"><select class="ca-acct" aria-label="Tài khoản ${side==='debit'?'Nợ':'Có'}">${acctOptions(x,st,r.account)}</select><input class="ca-amt" type="number" inputmode="numeric" min="1" step="1" placeholder="số tiền" value="${x.esc(r.amount)}" aria-label="Số tiền">${btn(x,'✕','car:delrow',{key:k,side,i},'ca-del ghost',d[side].length<=1)}</div>`;
  const side=(id,label)=>`<div class="ca-vside ${id}"><h5>${label}</h5>${d[id].map((r,i)=>row(id,r,i)).join('')}${btn(x,`＋ Dòng ${label}`,'car:addrow',{key:k,side:id},'ghost small ca-add',d[id].length>=6)}</div>`;
  return `<div class="ca-voucher" data-entry="${x.esc(k)}">
    <div class="ca-vhead"><b>PHIẾU KẾ TOÁN</b><small>${x.esc(t.title)}</small></div>
    <div class="ca-vcols">${side('debit','Nợ')}${side('credit','Có')}</div>
    <div class="ca-vfoot"><span>Tổng Nợ <b data-sum="debit">0</b></span><span>Tổng Có <b data-sum="credit">0</b></span><span class="ca-bal" data-bal>—</span></div>
    ${btn(x,'✍️ Ghi bút toán','car:entry',{task:t.id,step:st.id},'primary full')}
  </div>`;
}
function widget(t,st,x){
  const k=dkey(t,st),dr=drafts(x);
  if(st.kind==='choice')return `<div class="ca-options">${(st.options||[]).map(o=>x.cmd(x.esc(o.label),P+'step',{task:t.id,step:st.id,answer:o.id},'ca-opt')).join('')}</div>`;
  if(st.kind==='multi'){
    const sel=dr[k]||[];
    return `<div class="ca-checks" data-multi="${x.esc(k)}">${(st.options||[]).map(o=>`<label class="ca-check"><input type="checkbox" value="${x.esc(o.id)}" ${sel.includes(o.id)?'checked':''}><span>${x.esc(o.label)}</span></label>`).join('')}</div>${btn(x,'✔ Xác nhận lựa chọn','car:multi',{task:t.id,step:st.id},'primary full')}`;
  }
  if(st.kind==='number')return `<div class="ca-numrow"><input class="ca-input" type="number" inputmode="numeric" step="1" data-num="${x.esc(k)}" value="${x.esc(dr[k]??'')}" aria-label="${x.esc(st.title)}"><span class="ca-unit">${x.esc(st.unit||'')}</span>${btn(x,'Xác nhận','car:num',{task:t.id,step:st.id},'primary')}</div>`;
  if(st.kind==='order'){
    const ids=dr[k]??=(st.items||[]).map(i=>i.id);
    const item=id=>(st.items||[]).find(i=>i.id===id)?.label||id;
    return `<ol class="ca-order">${ids.map((id,i)=>`<li><span class="ca-ord-n">${i+1}</span><span class="grow">${x.esc(item(id))}</span>${btn(x,'↑','car:move',{key:k,i,dir:-1},'ghost ca-mv',i===0)}${btn(x,'↓','car:move',{key:k,i,dir:1},'ghost ca-mv',i===ids.length-1)}</li>`).join('')}</ol>${btn(x,'✔ Chốt thứ tự','car:order',{task:t.id,step:st.id},'primary full')}`;
  }
  if(st.kind==='match'){
    const cur=dr[k]||{};
    return `<div class="ca-match" data-match="${x.esc(k)}">${(st.left||[]).map(l=>`<label class="ca-mrow"><span>${x.esc(l.label)}</span><select data-left="${x.esc(l.id)}"><option value="">— chọn —</option>${(st.right||[]).map(r=>`<option value="${x.esc(r.id)}" ${cur[l.id]===r.id?'selected':''}>${x.esc(r.label)}</option>`).join('')}</select></label>`).join('')}</div>${btn(x,'✔ Xác nhận ghép','car:match',{task:t.id,step:st.id},'primary full')}`;
  }
  if(st.kind==='fields'){
    const cur=dr[k]||{};
    return `<div class="ca-fields" data-fields="${x.esc(k)}">${(st.fields||[]).map(f=>`<label class="ca-mrow"><span>${x.esc(f.label)}</span>${f.options?`<select data-field="${x.esc(f.id)}"><option value="">— chọn —</option>${f.options.map(o=>`<option value="${x.esc(o.id)}" ${cur[f.id]===o.id?'selected':''}>${x.esc(o.label)}</option>`).join('')}</select>`:`<span class="ca-numrow"><input class="ca-input" type="number" inputmode="numeric" step="1" data-field="${x.esc(f.id)}" value="${x.esc(cur[f.id]??'')}"><span class="ca-unit">${x.esc(f.unit||'')}</span></span>`}</label>`).join('')}</div>${btn(x,'✔ Xác nhận số liệu','car:fields',{task:t.id,step:st.id},'primary full')}`;
  }
  if(st.kind==='entry')return voucher(t,st,x);
  return '';
}
function stepsPanel(t,x){
  const ps=t.proc_state||{},rows=(t.proc||[]).map((st,i)=>{
    if(st.state==='locked')return `<li class="ca-step locked"><span class="ca-dot">🔒</span><b>${i+1}. ${x.esc(st.title)}</b></li>`;
    if(st.state==='solved')return `<li class="ca-step solved"><span class="ca-dot">✓</span><div class="grow"><b>${i+1}. ${x.esc(st.title)}</b><p class="ca-ans">${summary(st,x)}</p>${st.explain?`<p class="ca-explain">${x.esc(st.explain)}</p>`:''}</div></li>`;
    const tries=(ps.attempts||{})[st.id]||0;
    const missing=(st.docs||[]).filter(id=>t.docs.find(d=>d.id===id)?.closed);
    return `<li class="ca-step current"><span class="ca-dot">${i+1}</span><div class="grow"><b>${x.esc(st.title)}</b><p class="ca-prompt">${x.esc(st.prompt||'')}</p>
      ${missing.length?`<p class="ca-warn">📁 Mở trước: ${missing.map(id=>x.esc(t.docs.find(d=>d.id===id).title)).join(', ')}</p>`:''}
      ${st.tip?`<p class="ca-tip">💡 ${x.esc(st.tip)}</p>`:''}
      ${widget(t,st,x)}
      <div class="ca-stepfoot">${tries?`<small class="ca-small">Đã thử ${tries} lần</small>`:'<span></span>'}${st.tip?'':x.cmd('💡 Xin gợi ý',P+'hint',{task:t.id},'ghost small')}</div></div></li>`;
  }).join('');
  return `<section class="ca-proc"><h4 class="ca-sec">🧾 Quy trình <small>${(ps.solved||[]).length}/${ps.total||0} bước</small></h4><ol class="ca-steps">${rows}</ol>${handover(t,x)}</section>`;
}
function handover(t,x){
  if(!t.handover_options)return '';
  const sel=x.ui.note?.[t.id]||'specific';
  return `<div class="ca-handover"><h5>📝 Ghi chú bàn giao</h5>${t.handover_options.map(o=>`<label class="ca-check"><input type="radio" name="ca-note-${x.esc(t.id)}" value="${x.esc(o.id)}" ${o.id===sel?'checked':''}><span>${x.esc(o.label)}</span></label>`).join('')}
    ${btn(x,'📤 Nộp hồ sơ','car:submit',{task:t.id},'primary full big')}</div>`;
}

/* ---------------------------------------------------------------- side: ledger & trial balance */
function ledgerPanel(x){
  const d=x.room.data||{},led=d.ledger||{},ids=Object.keys(led).sort();
  const dr=ids.reduce((s,k)=>s+Math.max(0,led[k]),0),cr=ids.reduce((s,k)=>s+Math.max(0,-led[k]),0);
  const rows=ids.map(k=>`<tr><td><b>${x.esc(k)}</b> <small>${x.esc(acct(x,k).replace(/^\d+ · /,''))}</small></td><td class="num">${led[k]>0?num(led[k]):''}</td><td class="num">${led[k]<0?num(-led[k]):''}</td></tr>`).join('');
  const last=(d.entries||[]).slice(-3).reverse().map(e=>`<li><b>${x.esc(e.title)}</b><small>${e.lines.map(([a,b,m])=>`Nợ ${x.esc(a)}/Có ${x.esc(b)} ${num(m)}`).join(' · ')}</small></li>`).join('');
  const ms=(x.cc.milestones||[]).map(m=>`<li class="${(d.milestones||[]).includes(m.id)?'done':''}">${(d.milestones||[]).includes(m.id)?'✓':'○'} ${x.esc(m.name)}</li>`).join('');
  return `<aside class="ca-side">
    <section class="ca-card"><h4 class="ca-sec">📅 ${x.esc(d.period?.label||'Kỳ kế toán')} <small>${x.esc(d.period?.date||'')}</small></h4><ul class="ca-ms">${ms}</ul></section>
    <section class="ca-card"><h4 class="ca-sec">⚖️ Cân đối thử <span class="ca-badge ${dr===cr?'ok':'bad'}">${dr===cr?'Cân':'Lệch'}</span></h4>
      ${ids.length?`<div class="ca-scroll"><table class="ca-table tb"><thead><tr><th>TK</th><th>Dư Nợ</th><th>Dư Có</th></tr></thead><tbody>${rows}</tbody><tfoot><tr><td>Tổng</td><td class="num">${num(dr)}</td><td class="num">${num(cr)}</td></tr></tfoot></table></div>`:'<p class="ca-empty">Chưa có bút toán nào trong kỳ. Mỗi bút toán đúng sẽ được ghi vào sổ cái của bạn.</p>'}
    </section>
    ${last?`<section class="ca-card"><h4 class="ca-sec">📒 Nhật ký chung gần đây</h4><ul class="ca-journal">${last}</ul></section>`:''}
  </aside>`;
}

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
  const crunch=mod?.id==='crunch';
  const dueChip=due?`<span class="ca-chip ${due.overdue?'bad':due.soon?'warn':''}">⏰ Hạn ${x.esc(due.time)} · ${due.overdue?'đã trễ':'còn '+span(due.left)}</span>`:'';
  let alert='';
  if(o.locked)alert=`<p class="ca-alert bad">🔒 20:00 — văn phòng khóa cửa. Khép ngày, mai làm tiếp; việc dở được giữ nguyên.</p>`;
  else if(o.closed)alert=`<div class="ca-alert warn"><span>🌇 17:30 — hết giờ hành chính.</span>${x.confirmCmd(`🌙 Ở lại tăng ca (+${crunch?18:12} xu)`,'ca_overtime',{},`Ở lại tới 20:00? Được trả ${crunch?18:12} xu, mai vào muộn 30 phút vì mệt.`,'small')}</div>`;
  else if(o.can_overtime)alert=`<div class="ca-alert"><span>Sắp hết giờ. Còn việc dở?</span>${x.confirmCmd(`🌙 Đăng ký tăng ca (+${crunch?18:12} xu)`,'ca_overtime',{},`Ở lại tới 20:00? Được trả ${crunch?18:12} xu, mai vào muộn 30 phút vì mệt.`,'ghost small')}</div>`;
  return `<section class="ca-office" aria-label="Giờ làm việc hôm nay">
    <div class="ca-obar">
      <span class="ca-clock"><b>🕗 ${x.esc(o.time)}</b><small>${o.overtime?'tăng ca tới 20:00':o.lunch?'nghỉ trưa 12:00':'tan sở 17:30'}</small></span>
      ${dueChip}
      <span class="ca-trust" title="Chị Hạnh tin bạn ${trust}/100"><small>Chị Hạnh: ${x.esc(o.trust_label||'')}</small><span class="bar ${trust<35?'low':trust>=75?'high':''}"><i style="width:${trust}%"></i></span></span>
    </div>
    ${mod&&mod.id!=='normal'?`<p class="ca-mod"><b>${x.esc(mod.emoji)} ${x.esc(mod.name)}</b> ${x.esc(mod.text)}</p>`:''}
    ${o.tired?'<p class="ca-small">😮‍💨 Hôm qua tăng ca nên sáng nay vào muộn 30 phút.</p>':''}
    ${alert}
  </section>`;
}
function rulesBox(x){
  const rs=x.room.data?.today?.rules||[];if(!rs.length)return '';
  const fresh=rs.filter(r=>r.new).length;
  return `<section class="ca-rulebox" aria-label="Quy định đang áp dụng"><h4 class="ca-sec">📋 Quy định đang áp dụng ${fresh?`<span class="ca-new">${fresh} mới</span>`:''}</h4>
    <div class="ca-rules-row">${rs.map(r=>`<article class="ca-rule ${r.new?'new':''}"><b>${x.esc(r.emoji)} ${x.esc(r.title)}${r.new?' <em>MỚI</em>':''}</b><p>${x.esc(r.text)}</p></article>`).join('')}</div></section>`;
}

/* ---------------------------------------------------------------- the document desk */
const VLAB={approve:'DUYỆT',escalate:'TRÌNH SẾP',reject:'TRẢ LẠI'};
const RES={ok:['✓','Chuẩn'],reason:['⚠️','Đúng dấu, sai căn cứ'],wrong:['✗','Sai dấu']};
const DOC_ICON={invoice:'🧾',payreq:'📝',voucher:'💵',email:'📧'};
const br=(x,v)=>String(v??'').split('\n').map(s=>x.esc(s)).join('<br>');
const sels=x=>(x.ui.sel??={});
function caseOf(t,x){
  const cs=t.cases||[],id=sels(x)[t.id];
  return cs.find(c=>c.id===id)||cs.find(c=>!c.stamp)||cs[0];
}
function paperView(t,c,x){
  const p=c.paper||{},live=!c.stamp,circ=new Set(c.circles||[]),truth=new Set(c.truth&&c.truth.v!=='approve'?c.truth.z:[]);
  const zone=(z,inner,cls='')=>{
    if(!z)return `<div class="ca-pz fixed ${cls}">${inner}</div>`;
    const mark=`${circ.has(z)?' circled':''}${truth.has(z)?' truth':''}`;
    return live?`<button type="button" class="ca-pz ${cls}${mark}" data-action="car:circle" data-task="${x.esc(t.id)}" data-case="${x.esc(c.id)}" data-zone="${x.esc(z)}" aria-pressed="${circ.has(z)}">${inner}</button>`:`<div class="ca-pz ${cls}${mark}">${inner}</div>`;
  };
  const kv=r=>zone(r.z,`<span class="k">${x.esc(r.k)}</span><span class="v">${br(x,r.v)}</span>`,r.strong?'strong':'');
  const tb=p.table?zone(p.table.z,`<div class="ca-scroll"><table class="ca-table"><thead><tr>${p.table.cols.map(h=>`<th>${x.esc(h)}</th>`).join('')}</tr></thead><tbody>${p.table.rows.map(r=>`<tr>${r.map((v,i)=>`<td class="${i&&/^[\d.]+$/.test(v)?'num':''}">${x.esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`,'table'):'';
  const stamp=c.stamp?`<div class="ca-stampmark ${c.stamp} ${x.ui.fresh===c.id?'fresh':''}" aria-hidden="true">${VLAB[c.stamp]}</div>`:'';
  return `<article class="ca-sheet ${x.esc(p.kind||'')}"><header><b>${x.esc(p.title||'')}</b>${p.sub?`<small>${x.esc(p.sub)}</small>`:''}</header>
    <div class="ca-prows">${(p.rows||[]).map(kv).join('')}</div>${tb}
    ${(p.foot||[]).length?`<div class="ca-pfoot">${p.foot.map(kv).join('')}</div>`:''}
    ${p.note?zone(p.note.z||'note',`<span class="k">📎 Giấy kẹp kèm</span><span class="v">${br(x,p.note.text)}</span>`,'clip'):''}
    ${stamp}</article>`;
}
function caseCard(t,c,x){
  const cs=t.cases||[],i=cs.indexOf(c),n=(c.circles||[]).length,max=x.cc.max_circles||3;
  const from=`<div class="ca-from"><span class="ca-doc-ico">${DOC_ICON[c.doc]||'📄'}</span><div class="grow"><small>Bộ ${i+1}/${cs.length} · ${x.esc(c.who||'')}</small><p>“${x.esc(c.quote||'')}”</p></div></div>`;
  if(c.stamp){
    const [ic,label]=RES[c.result]||['•',''],next=cs.find(v=>!v.stamp);
    return `<section class="ca-case done">${from}${paperView(t,c,x)}
      <div class="ca-verdict ${x.esc(c.result||'')}" role="status"><b>${ic} ${label}</b><span>Dấu của bạn: ${VLAB[c.stamp]}${c.result!=='ok'?` · Cần: ${VLAB[c.truth?.v]||''}`:''}</span><p>${x.esc(c.truth?.why||'')}</p></div>
      ${next?btn(x,`Bộ tiếp theo ›`,'car:pick',{task:t.id,case:next.id},'primary full big'):''}</section>`;
  }
  const hint=c.tip?`<p class="ca-tip">💡 ${x.esc(c.tip)}</p>`:'';
  return `<section class="ca-case">${from}${paperView(t,c,x)}${hint}
    <div class="ca-tools"><small>${n?`⭕ Đã khoanh ${n}/${max} chỗ`:'Chạm vào ô trên giấy để khoanh chỗ nghi sai'}</small>${c.hinted?'':x.cmd('💡 Gợi ý','ca_hint',{task:t.id,case:c.id},'ghost small')}</div>
    <div class="ca-stampbar" role="group" aria-label="Đóng dấu">
      ${['approve','escalate','reject'].map(v=>btn(x,`<span>${VLAB[v]}</span>`,'car:stamp',{task:t.id,case:c.id,verdict:v},`ca-sbtn ${v}`)).join('')}
    </div></section>`;
}
/** Reference tables as scannable cards: first column is the name, the rest are labelled facts. */
function refList(d,x){
  if(d.type!=='table')return docBody(d,x,null);
  const flag=v=>/Ngừng|khóa|Không/.test(v)?'bad':'';
  return `<ul class="ca-ref">${(d.rows||[]).map(r=>`<li><b>${x.esc(r[0])}</b>${r.slice(1).map((v,i)=>`<span class="${flag(v)}"><small>${x.esc(d.cols[i+1]||'')}</small> ${x.esc(v)}</span>`).join('')}</li>`).join('')}</ul>`;
}
function binder(t,x){
  const docs=t.docs||[],opened=docs.filter(d=>!d.closed);
  let sel=views(x)[t.id];if(!opened.some(d=>d.id===sel))sel=null;
  const doc=opened.find(d=>d.id===sel);
  const lag=x.room.data?.today?.mod?.id==='lag';
  const tabs=docs.map(d=>d.closed?btn(x,`<span class="ca-doc-ico">📁</span><span class="grow">${x.esc(d.title)}<small>Mở · ${lag?12:6} phút</small></span>`,'car:open',{task:t.id,doc:d.id},'ca-tab closed'):btn(x,`<span class="ca-doc-ico">📖</span><span class="grow">${x.esc(d.title)}<small>${d.id===sel?'Đang xem · chạm để gấp':'Chạm để xem'}</small></span>`,'car:view',{task:t.id,doc:d.id===sel?'':d.id},`ca-tab ${d.id===sel?'active':''}`)).join('');
  return `<section class="ca-binder"><h4 class="ca-sec">📚 Sổ tra cứu <small>${opened.length}/${docs.length} đã mở</small></h4><div class="ca-tabs">${tabs}</div>
    ${doc?`<article class="ca-viewer"><header><b>${x.esc(doc.title)}</b><small>Nguồn: ${x.esc(doc.source)}</small></header>${refList(doc,x)}</article>`:''}</section>`;
}
function trayRecap(x){
  const t=(x.room.tasks||[]).find(v=>v.id===x.ui.lastTray);
  if(!t||t.status!=='completed'||!t.cases)return '';
  const cs=t.cases,ok=cs.filter(c=>c.result==='ok').length;
  const li=cs.map((c,i)=>{
    const [ic,label]=RES[c.result]||['•',''];
    return `<li class="${x.esc(c.result||'')}"><b>${ic} Bộ ${i+1} · ${x.esc(label)}</b><span>Dấu của bạn: ${VLAB[c.stamp]||'—'}${c.result!=='ok'?` · Cần: ${VLAB[c.truth?.v]||''}`:''}</span>${c.result!=='ok'&&c.truth?.why?`<small>${x.esc(c.truth.why)}</small>`:''}</li>`;
  }).join('');
  return `<section class="ca-recap" role="status"><h4>🗂️ Khay vừa chốt · ${ok}/${cs.length} bộ chuẩn</h4><ul>${li}</ul></section>`;
}
function deskView(t,x){
  const cs=t.cases||[],c=caseOf(t,x),desk=t.tray||{};
  const chips=cs.map((v,i)=>{
    const st=v.stamp?(RES[v.result]||['•'])[0]:'';
    return btn(x,`<b>${i+1}</b><span>${DOC_ICON[v.doc]||'📄'}</span>${st?`<i>${st}</i>`:''}`,'car:pick',{task:t.id,case:v.id},`ca-qchip ${v.id===c?.id?'active':''} ${v.stamp?'stamped '+(v.result||''):''}`);
  }).join('');
  const ready=desk.ready&&t.status!=='completed';
  const foot=ready?`<div class="ca-ready">${x.confirmCmd(`📤 Chốt khay · ${desk.ok}/${desk.total} chuẩn`,'ca_submit',{task:t.id},'Chốt khay và báo kết quả cho chị Hạnh?','primary full big')}</div>`:'';
  return `<div class="ca-desk">
    <div class="ca-desk-main"><nav class="ca-queue" aria-label="Khay chứng từ">${chips}<small>${desk.stamped||0}/${desk.total||cs.length} đã đóng dấu</small></nav>
      ${foot}${c?caseCard(t,c,x):''}</div>
    <div class="ca-desk-side">${rulesBox(x)}${binder(t,x)}</div>
  </div>`;
}

/* ---------------------------------------------------------------- DOM → draft sync (no input hook: tick + actions) */
function readEntry(box){
  const out={debit:[],credit:[]};
  box.querySelectorAll('.ca-vrow').forEach(r=>out[r.dataset.side].push({account:r.querySelector('select').value,amount:r.querySelector('input').value}));
  return out;
}
function sync(root,x){
  const dr=drafts(x);
  root.querySelectorAll('[data-multi]').forEach(b=>{dr[b.dataset.multi]=[...b.querySelectorAll('input:checked')].map(i=>i.value);});
  root.querySelectorAll('[data-num]').forEach(i=>{dr[i.dataset.num]=i.value;});
  root.querySelectorAll('[data-match]').forEach(b=>{const o={};b.querySelectorAll('select').forEach(s=>{if(s.value)o[s.dataset.left]=s.value;});dr[b.dataset.match]=o;});
  root.querySelectorAll('[data-fields]').forEach(b=>{const o={};b.querySelectorAll('[data-field]').forEach(s=>{o[s.dataset.field]=s.value;});dr[b.dataset.fields]=o;});
  root.querySelectorAll('[data-entry]').forEach(b=>{dr[b.dataset.entry]=readEntry(b);});
  root.querySelectorAll('input[type=radio][name^="ca-note-"]:checked').forEach(r=>{(x.ui.note??={})[r.name.slice(8)]=r.value;});
}
const rootOf=el=>el.closest('.career-job')||document;
const intOf=v=>{const s=String(v??'').trim();return /^-?\d+$/.test(s)?Number(s):null;};
function stepOf(x,data){
  const t=(x.room.tasks||[]).find(v=>v.id===data.task);
  return [t,t&&(t.proc||[]).find(s=>s.id===data.step)];
}
const send=(x,t,st,answer)=>x.send(P+'step',{task:t.id,step:st.id,answer});

export default {
  id:'corp_accounting',
  css:true,
  next(t){
    if(t.variant==='desk'){
      if(!t.known)return 'Nhận khay chứng từ';
      const left=(t.cases||[]).filter(c=>!c.stamp).length;
      return left?`Soi và đóng dấu: còn ${left}/${(t.cases||[]).length} bộ`:'Chốt khay, báo kết quả';
    }
    if(!t.known)return 'Nhận hồ sơ từ người giao việc';
    const st=(t.proc||[]).find(s=>s.state==='current');
    if(st){
      const miss=(st.docs||[]).filter(id=>(t.docs||[]).find(d=>d.id===id)?.closed);
      return miss.length?'Mở chứng từ gốc trước khi làm bước này':`Bước ${(t.proc_state?.at||0)+1}/${t.proc_state?.total||0}: ${st.title}`;
    }
    return t.handover?'Đã nộp hồ sơ':'Chọn ghi chú bàn giao và nộp hồ sơ';
  },
  job(t,x){
    const who=x.npc(t.npc),k=t.kind_info||{};
    const timed=typeof t.due==='number';
    const head=t.known&&timed?`<article class="ca-head compact"><div class="ca-who">${x.portrait(who,40)}<div class="grow"><small class="ca-small">${x.esc(k.emoji||'🧾')} ${x.esc(who.display_name)}${who.role?' · '+x.esc(who.role):''}</small><p class="ca-quote">“${x.esc(t.opening)}”</p></div></div></article>`
      :`<article class="ca-head"><div class="ca-who">${x.portrait(who,52)}<div class="grow"><span class="ca-kind">${x.esc(k.emoji||'🧾')} ${x.esc(k.name||'Hồ sơ kế toán')}</span><h3>${x.esc(t.title)}</h3><p class="ca-quote">“${x.esc(t.opening)}”</p><small class="ca-small">${x.esc(who.display_name)}${who.role?' · '+x.esc(who.role):''}</small></div></div>
      ${timed?'':`<div class="patience" title="Kiên nhẫn của người giao việc"><div class="bar ${t.patience<50?'low':''}"><i style="width:${Number(t.patience)||0}%"></i></div><small>${Number(t.patience)||0}%</small></div>`}</article>`;
    const desk=t.variant==='desk',bar=officeBar(t,x);
    x.ui.lastTray=desk?t.id:null;
    if(!t.known)return `<div class="career-job ca">${bar}${head}<div class="ca-card">${x.cmd(desk?'📥 Nhận khay chứng từ':'📥 Nhận hồ sơ','ask',{task:t.id},'primary full big')}<p class="ca-small">${desk?'Soi từng bộ theo quy định hôm nay rồi đóng dấu. Duyệt nhầm là bị trừ tiền.':'Nhận hồ sơ để xem đề bài, chứng từ và các bước cần làm.'}</p></div>${desk?rulesBox(x):ledgerPanel(x)}</div>`;
    if(desk)return `<div class="career-job ca">${bar}${head}${deskView(t,x)}</div>`;
    return `<div class="career-job ca">${bar}${head}<p class="ca-brief">🎯 ${x.esc(t.brief||'')}</p>
      <div class="ca-bench"><div class="ca-main">${docsPanel(t,x)}${stepsPanel(t,x)}</div>${ledgerPanel(x)}</div></div>`;
  },
  idle(x){
    const d=x.room.data||{};if(!d.office)return '';
    return `<div class="career-job ca">${trayRecap(x)}${officeBar(null,x)}${rulesBox(x)}</div>`;
  },
  summary(data,x){
    if(!data||typeof data!=='object')return '';
    const o=data.office||{},desk=data.desk||{},rows=[];
    const row=(k,v)=>rows.push(`<div class="kv-row"><span>${x.esc(k)}</span><b>${x.esc(v)}</b></div>`);
    if(data.mod?.name)row('Hôm nay',`${data.mod.emoji||''} ${data.mod.name}`);
    if(desk.stamped)row('Chứng từ đã đóng dấu',`${desk.ok}/${desk.stamped} chuẩn${desk.slips?` · ${desk.slips} duyệt nhầm`:''}`);
    if(data.dossiers)row('Hồ sơ hoàn tất',String(data.dossiers));
    if(data.posted)row('Bút toán đã ghi',String(data.posted));
    if(o.late)row('Việc nộp trễ hạn',String(o.late));
    if(o.fines)row('Bị trừ tiền',`${o.fines} xu`);
    if(o.overtime)row('Tăng ca','Có (mai vào muộn 30 phút)');
    if(o.carried)row('Việc dở để sáng mai',`${o.carried} (hạn 10:00)`);
    if(Array.isArray(data.milestones)&&data.milestones.length)row('Mốc tháng đã xong',data.milestones.join(', '));
    const ch=Number(o.trust_change)||0;
    const trust=o.trust_label?`<p class="ca-sum-trust">👩‍💼 Chị Hạnh: <b>${x.esc(o.trust_label)}</b> (${o.trust}/100${ch?`, ${ch>0?'+':''}${ch} hôm nay`:''})</p>`:'';
    const audit=data.audit?`<p class="ca-sum-audit ${data.audit.ok?'ok':'bad'}">${data.audit.ok?'🏅':'🔍'} ${x.esc(data.audit.text||'')}</p>`:'';
    if(!rows.length&&!trust&&!audit)return '';
    return `<article class="card space-top ca-sum"><h4 class="section-title">🗂️ Bàn kế toán hôm nay</h4>${audit}${trust}${rows.length?`<div class="kv">${rows.join('')}</div>`:''}</article>`;
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
      bal.className='ca-bal '+(!d&&!c?'':d===c?'ok':'bad');
    });
  },
  actions:{
    async open(data,el,x){views(x)[data.task]=data.doc;await x.send(P+'open',{task:data.task,doc:data.doc});},
    view(data,el,x){sync(rootOf(el),x);views(x)[data.task]=data.doc;x.render();},
    pick(data,el,x){sels(x)[data.task]=data.case;x.ui.fresh=null;x.render();document.querySelector('.career-job.ca .ca-queue')?.scrollIntoView({block:'nearest'});},
    async circle(data,el,x){
      const on=el.getAttribute('aria-pressed')==='true';
      el.classList.toggle('circled',!on);el.setAttribute('aria-pressed',String(!on));
      const r=await x.send(P+'circle',{task:data.task,case:data.case,zone:data.zone});
      if(!r){el.classList.toggle('circled',on);el.setAttribute('aria-pressed',String(on));}
    },
    async stamp(data,el,x){
      const t=(x.room.tasks||[]).find(v=>v.id===data.task),c=(t?.cases||[]).find(v=>v.id===data.case);
      if(!c)return;
      if(data.verdict!=='approve'&&!(c.circles||[]).length){x.toast(`Khoanh ít nhất một chỗ làm căn cứ trước khi ${data.verdict==='reject'?'trả lại':'trình sếp'}.`,true);return;}
      sels(x)[data.task]=data.case;
      const r=await x.send(P+'stamp',{task:data.task,case:data.case,verdict:data.verdict});
      if(r){x.ui.fresh=data.case;x.render();}
    },
    flag(data,el,x){
      const root=rootOf(el),box=root.querySelector(`[data-multi="${CSS.escape(data.key)}"]`);
      const input=box?.querySelector(`input[value="${CSS.escape(data.flag)}"]`);
      if(!input){x.toast('Ô này không có trong danh sách lỗi của bước hiện tại.',true);return;}
      input.checked=!input.checked;
      if(input.checked){const none=box.querySelector('input[value="none"]');if(none)none.checked=false;}
      el.classList.toggle('flagged',input.checked);el.setAttribute('aria-pressed',String(input.checked));
      sync(root,x);
    },
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
