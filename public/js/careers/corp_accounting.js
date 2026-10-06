/** Kế toán doanh nghiệp · Công ty CP Mây Tre Xanh — bàn kế toán (plugin client module).
 *  An office desktop (office_kit.js): 📥 Hộp thư (việc chị Hạnh và đồng nghiệp giao, tin trong ngày),
 *  📂 Hồ sơ (một chứng từ một lúc: khay đóng dấu DUYỆT/TRẢ LẠI/TRÌNH SẾP, hoặc hồ sơ nhiều bước với
 *  phiếu kế toán Nợ/Có tự cân), 📋 Quy định (quy định tháng + sổ tra cứu), 📒 Sổ sách (cân đối thử)
 *  and a sticky bar with the next step and the main action.
 *  No inline handlers: every button goes through data-command / data-action="car:*". */
import {statusStrip,taskMails,dayMails,inboxPane,rulesList,desk,bar,switchTab,keepBarAboveFooter,fold,idleDesk,openTasks,planCard,mateCards,trackFold,careSummary,foldToggle,
  coachOf,goto,gotoAction,guideOf,procSteps,coachFill,shut,shutWork,shutBar,summaryCard,note,envelope,deskHelp} from './office_kit.js';
import {clean} from '../ui-kit.js';
import {pending,stepLine} from '../v4/guide.js';
import {amountAttrs,amountNote,amountNoteHTML,amountOf} from '../v4/amount-parse.js';

const P='ca_';
const BOSS='Chị Hạnh';
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
  if(d.type==='cash')return `<div class="ca-cash"><table class="ca-table"><thead><tr><th>Mệnh giá</th><th>Số tờ</th></tr></thead><tbody>${(d.denoms||[]).map(([k,v])=>`<tr><td>💵 ${x.esc(k)}</td><td class="num">${num(v)}</td></tr>`).join('')}</tbody></table></div>`;
  if(d.type==='email')return `<div class="ca-mail"><p><b>Từ:</b> ${x.esc(d.sender||'')}</p><p><b>Chủ đề:</b> ${x.esc(d.subject||'')}</p><p>${x.esc(d.text||'')}</p></div>`;
  return `<p class="ca-paper">${x.esc(d.text||'')}</p>`;
}
/** The dossier's papers: a strip of folder tabs, one paper open at a time. */
function docsPanel(t,x){
  const st=currentStep(t),need=new Set(st?.docs||[]);
  const opened=t.docs.filter(d=>!d.closed);
  let sel=views(x)[t.id];
  if(!opened.some(d=>d.id===sel))sel=opened[0]?.id;
  const tabs=t.docs.map(d=>{
    // Clean layout: a paper still closed that this step needs keeps its "❗"; the source line goes (it is in the viewer).
    const label=`<span class="ca-doc-ico" aria-hidden="true">${d.closed?'📁':'📄'}</span><span class="grow">${x.esc(d.title)}${d.closed?(need.has(d.id)?(clean()?' <small>❗</small>':'<small>Cần mở cho bước này</small>'):''):clean()?'':`<small>${x.esc(d.source)}</small>`}</span>`;
    return d.closed?btn(x,label,'car:open',{task:t.id,doc:d.id},`ca-tab closed ${need.has(d.id)?'need':''}`):btn(x,label,'car:view',{task:t.id,doc:d.id},`ca-tab ${d.id===sel?'active':''}`);
  }).join('');
  const doc=opened.find(d=>d.id===sel);
  let flags=null;
  if(doc?.type==='invoice'&&st?.kind==='multi'&&(st.options||[]).some(o=>INVOICE_FLAGS.includes(o.id))){
    const k=dkey(t,st);flags={key:k,sel:drafts(x)[k]||[]};
  }
  return `<section class="ca-docs"><h3 class="ok-h">📄 ${clean()?'':'Chứng từ '}<small>${opened.length}/${t.docs.length}${clean()?'':' đã mở'}</small></h3>
    <div class="ca-tabs" role="toolbar" aria-label="Chứng từ trong hồ sơ">${tabs}</div>
    ${doc?`<article class="ca-viewer" aria-live="polite"><header><b>${x.esc(doc.title)}</b><small>${clean()?'':'Nguồn: '}${x.esc(doc.source)}</small></header>${docBody(doc,x,flags)}</article>`:'<p class="ok-empty"><span aria-hidden="true">📁</span><span>Mở một chứng từ để xem.</span></p>'}
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
  const row=(side,r,i)=>`<div class="ca-vrow" data-side="${side}" data-amt-box><select class="ca-acct" aria-label="Tài khoản ${side==='debit'?'Nợ':'Có'}">${acctOptions(x,st,r.account)}</select><input class="ca-amt${unread(r.amount,'xu')}" ${amountAttrs('xu')} placeholder="số tiền" value="${x.esc(r.amount)}" aria-label="Số tiền">${btn(x,'✕','car:delrow',{key:k,side,i},'ca-del ghost',d[side].length<=1)}${amountNoteHTML(r.amount,'xu')}</div>`;
  const side=(id,label)=>`<div class="ca-vside ${id}"><h4>${label}</h4>${d[id].map((r,i)=>row(id,r,i)).join('')}${btn(x,`＋ Dòng ${label}`,'car:addrow',{key:k,side:id},'ghost small ca-add',d[id].length>=6)}</div>`;
  return `<div class="ca-voucher" data-entry="${x.esc(k)}">
    <div class="ca-vhead"><b>PHIẾU KẾ TOÁN</b><small>${x.esc(t.title)}</small></div>
    <div class="ca-vcols">${side('debit','Nợ')}${side('credit','Có')}</div>
    <div class="ca-vfoot"><span>Tổng Nợ <b data-sum="debit">0</b></span><span>Tổng Có <b data-sum="credit">0</b></span><span class="ca-bal" data-bal>—</span></div>
  </div>`;
}
/** One line under each box of a calculation: where its number comes from and the formula, in words (never the number).
 *  Keyed by variant:step, then the field id ('' for a one-number step, '*' for every box of the step). */
const HOW={
  'invoice_out:calc':{base:'Số lượng THỰC GIAO (Biên bản giao nhận) × Đơn giá chưa thuế (Đơn đặt hàng).',vat:'Tiền hàng chưa thuế × 10%.',total:'Tiền hàng chưa thuế + Thuế GTGT.'},
  'bank_rec:adjusted':{'':'Số dư cuối kỳ theo Sổ tiền gửi, cộng tiền vào / trừ tiền ra của các khoản cần ghi bổ sung.'},
  'ageing:balance':{'':'Cộng cột “Còn phải thu” của mọi hóa đơn chưa thu đủ (Sổ chi tiết công nợ 131).'},
  'petty_cash:count':{'':'Bảng kiểm đếm: mỗi dòng mệnh giá × số tờ, rồi cộng lại.'},
  'petty_cash:book':{'':'Sổ quỹ: tồn quỹ đầu ngày + các phiếu thu − các phiếu chi.'},
  'depreciation:monthly':{'*':'Nguyên giá ÷ (số năm × 12), theo Sổ tài sản cố định. Mới dùng trong tháng hoặc đã khấu hao hết thì ghi 0.'},
  'depreciation:nbv':{'':'Nguyên giá − hao mòn lũy kế − khấu hao tháng này (Sổ tài sản cố định).'},
  'inventory_count:diff':{'*':'Thực đếm (Biên bản kiểm kê) − Tồn theo sổ (Thẻ kho). Thiếu ghi số âm, khớp ghi 0.'},
  'inventory_count:value':{'':'Số lượng thiếu (bước trước) × Đơn giá vốn trên Thẻ kho.'},
  'month_close:vat_pay':{'':'Thuế đầu ra (TK 3331) − thuế đầu vào được khấu trừ (TK 133), trên bảng số dư.'},
  'trial_balance:diff':{'':'Tổng cột Dư Nợ và tổng cột Dư Có của bảng cân đối thử: lấy tổng lớn trừ tổng nhỏ.'},
  'trial_balance:is':{rev:'Số dư TK 511 trên Sổ cái.',gross:'Doanh thu thuần − Giá vốn (TK 632).',pbt:'Lợi nhuận gộp − chi phí bán hàng (641) − chi phí quản lý (642), theo số đã sửa.'},
};
const how=(t,st,id,x)=>{const h=HOW[`${t.variant}:${st.id}`],s=h?.[id]??h?.['*'];return s?note(`📐 ${x.esc(s)}`,`Cách tính: ${st.title}`):'';};
/** Boxes the last wrong check named (server `bad`; '' = a one-number step), outlined until the next check. */
const missOf=(x,t,st)=>new Set(x.ui.miss?.[dkey(t,st)]||[]);
function widget(t,st,x){
  const k=dkey(t,st),dr=drafts(x);
  if(st.kind==='choice')return `<div class="ca-options">${(st.options||[]).map(o=>x.cmd(x.esc(o.label),P+'step',{task:t.id,step:st.id,answer:o.id},'ca-opt').replace('<button ',`<button data-opt="${x.esc(o.id)}" `)).join('')}</div>`;
  if(st.kind==='multi'){
    const sel=dr[k]||[];
    return `<div class="ca-checks" data-multi="${x.esc(k)}">${(st.options||[]).map(o=>`<label class="ca-check"><input type="checkbox" value="${x.esc(o.id)}" ${sel.includes(o.id)?'checked':''}><span>${x.esc(o.label)}</span></label>`).join('')}</div>`;
  }
  if(st.kind==='number'){const bad=missOf(x,t,st).has('');
    return `<div class="ca-numrow" data-amt-box>${bad?'<span class="ca-bad" aria-hidden="true">✗</span>':''}<input class="ca-input${unread(dr[k],st.unit)}" ${amountAttrs(st.unit||'')} placeholder="${HINT}" data-num="${x.esc(k)}" value="${x.esc(dr[k]??'')}" aria-label="${x.esc(st.title)}"${bad?' aria-invalid="true"':''}><span class="ca-unit">${x.esc(st.unit||'')}</span>${amountNoteHTML(dr[k],st.unit||'')}</div>${how(t,st,'',x)}`;}
  if(st.kind==='order'){
    const ids=dr[k]??=(st.items||[]).map(i=>i.id);
    const item=id=>(st.items||[]).find(i=>i.id===id)?.label||id;
    return `<ol class="ca-order">${ids.map((id,i)=>`<li><span class="ca-ord-n">${i+1}</span><span class="grow">${x.esc(item(id))}</span>${btn(x,'↑','car:move',{key:k,i,dir:-1},'ghost ca-mv',i===0)}${btn(x,'↓','car:move',{key:k,i,dir:1},'ghost ca-mv',i===ids.length-1)}</li>`).join('')}</ol>`;
  }
  if(st.kind==='match'){
    const cur=dr[k]||{};
    return `<div class="ca-match" data-match="${x.esc(k)}">${(st.left||[]).map(l=>`<label class="ca-mrow"><span>${x.esc(l.label)}</span><select data-left="${x.esc(l.id)}"><option value="">— chọn —</option>${(st.right||[]).map(r=>`<option value="${x.esc(r.id)}" ${cur[l.id]===r.id?'selected':''}>${x.esc(r.label)}</option>`).join('')}</select></label>`).join('')}</div>`;
  }
  if(st.kind==='fields'){
    const cur=dr[k]||{},bad=missOf(x,t,st);
    return `<div class="ca-fields" data-fields="${x.esc(k)}">${(st.fields||[]).map(f=>`<label class="ca-mrow"><span${bad.has(f.id)?' class="ca-bad"':''}>${bad.has(f.id)?'✗ ':''}${x.esc(f.label)}</span>${f.options?`<select data-field="${x.esc(f.id)}"><option value="">— chọn —</option>${f.options.map(o=>`<option value="${x.esc(o.id)}" ${cur[f.id]===o.id?'selected':''}>${x.esc(o.label)}</option>`).join('')}</select>`:`<span class="ca-numrow" data-amt-box><input class="ca-input${unread(cur[f.id],f.unit)}" ${amountAttrs(f.unit||'')} data-field="${x.esc(f.id)}" value="${x.esc(cur[f.id]??'')}"${bad.has(f.id)?' aria-invalid="true"':''}><span class="ca-unit">${x.esc(f.unit||'')}</span>${amountNoteHTML(cur[f.id],f.unit||'')}</span>`}</label>${how(t,st,f.id,x)}`).join('')}</div>`;
  }
  if(st.kind==='entry')return voucher(t,st,x);
  return '';
}
/** Confirm label + action of each step kind (office_kit.procSteps puts it on the bottom button; choices answer on tap). */
const CONFIRM={multi:['✔ Xác nhận lựa chọn','car:multi'],number:['✔ Xác nhận','car:num'],order:['✔ Chốt thứ tự','car:order'],
  match:['✔ Xác nhận ghép','car:match'],fields:['✔ Xác nhận số liệu','car:fields'],entry:['✍️ Ghi bút toán','car:entry']};
/** The work sheet: the current step big, done steps folded away. */
function stepCard(t,x){
  const ps=t.proc_state||{},steps=t.proc||[],cur=steps.find(s=>s.state==='current');
  const solved=steps.filter(s=>s.state==='solved'),locked=steps.filter(s=>s.state==='locked').length,total=ps.total||steps.length;
  const last=solved[solved.length-1];
  const done=solved.length?fold(clean()?`✓ ${solved.length}`:`✓ ${solved.length} bước đã xong <small>xem lại</small>`,`<ol class="ca-steps">${solved.map(st=>`<li class="ca-step solved"><span class="ca-dot" aria-hidden="true">✓</span><div class="grow"><b>${steps.indexOf(st)+1}. ${x.esc(st.title)}</b><p class="ca-ans">${summary(st,x)}</p>${st.explain?`<p class="ca-explain">${x.esc(st.explain)}</p>`:''}</div></li>`).join('')}</ol>`):'';
  let body;
  if(cur){
    const i=steps.indexOf(cur),tries=(ps.attempts||{})[cur.id]||0;
    const missing=(cur.docs||[]).filter(id=>t.docs.find(d=>d.id===id)?.closed);
    body=`<article class="ca-work" data-step-card="${x.esc(t.id)}:${x.esc(cur.id)}"><header class="ca-work-head"><span class="ca-dot" aria-hidden="true">${i+1}</span><div class="grow"><small>${clean()?`${i+1}/${total}`:`Bước ${i+1}/${total}${locked?` · còn ${locked} bước sau`:''}`}</small><h3>${x.esc(cur.title)}</h3></div></header>
      <p class="ca-prompt">${x.esc(cur.prompt||'')}</p>
      ${missing.length?`<p class="ca-warn">📁 ${clean()?'':'Mở trước: '}${missing.map(id=>x.esc(t.docs.find(d=>d.id===id).title)).join(', ')}</p>`:''}
      ${cur.tip?`<p class="ca-tip">💡 ${x.esc(cur.tip)}</p>`:''}
      ${widget(t,cur,x)}
      <div class="ca-stepfoot">${tries?`<small>${clean()?`↻ ${tries}`:`Đã thử ${tries} lần`}</small>`:'<span></span>'}${cur.tip?'':x.cmd(clean()?'💡 Gợi ý':'💡 Xin gợi ý',P+'hint',{task:t.id},'ghost small')}</div></article>`;
  }else body=handover(t,x);
  const pct=total?Math.round(solved.length/total*100):0;
  return `<section class="ca-proc">${clean()?'':`<h3 class="ok-h">🧾 Quy trình <small>${solved.length}/${total} bước</small></h3>`}
    <div class="ca-prog" role="progressbar" aria-label="Tiến độ hồ sơ" aria-valuemin="0" aria-valuemax="${total}" aria-valuenow="${solved.length}"><i style="width:${pct}%"></i></div>
    ${last&&cur&&last.explain?(clean()?`<p class="ca-lastok">✓ <b>${x.esc(last.title)}</b>${note(x.esc(last.explain),last.title,'','span')}</p>`:`<p class="ca-lastok">✓ <b>${x.esc(last.title)}</b> — ${x.esc(last.explain)}</p>`):''}${body}${done}</section>`;
}
function handover(t,x){
  if(!t.handover_options)return '';
  const sel=x.ui.note?.[t.id]||'specific';
  return `<article class="ca-work ca-handover"><header class="ca-work-head"><span class="ca-dot" aria-hidden="true">📝</span><div class="grow"><small>Bước cuối</small><h3>Ghi chú bàn giao</h3></div></header>
    ${t.handover_options.map(o=>`<label class="ca-check"><input type="radio" name="ca-note-${x.esc(t.id)}" value="${x.esc(o.id)}" ${o.id===sel?'checked':''}><span>${x.esc(o.label)}</span></label>`).join('')}</article>`;
}

/* ---------------------------------------------------------------- 📒 books: period, trial balance, journal */
function booksPane(x){
  const d=x.room.data||{},led=d.ledger||{},ids=Object.keys(led).sort();
  const dr=ids.reduce((s,k)=>s+Math.max(0,led[k]),0),cr=ids.reduce((s,k)=>s+Math.max(0,-led[k]),0);
  const rows=ids.map(k=>`<tr><td><b>${x.esc(k)}</b> <small>${x.esc(acct(x,k).replace(/^\d+ · /,''))}</small></td><td class="num">${led[k]>0?num(led[k]):''}</td><td class="num">${led[k]<0?num(-led[k]):''}</td></tr>`).join('');
  const last=(d.entries||[]).slice(-3).reverse().map(e=>`<li><b>${x.esc(e.title)}</b><small>${e.lines.map(([a,b,m])=>`Nợ ${x.esc(a)}/Có ${x.esc(b)} ${num(m)}`).join(' · ')}</small></li>`).join('');
  const ms=(x.cc.milestones||[]).map(m=>`<li class="${(d.milestones||[]).includes(m.id)?'done':''}">${(d.milestones||[]).includes(m.id)?'✓':'○'} ${x.esc(m.name)}</li>`).join('');
  return `<section class="ca-book"><h3 class="ok-h">📅 ${x.esc(d.period?.label||'Kỳ kế toán')} <small>${x.esc(d.period?.date||'')}</small></h3><ul class="ca-ms">${ms}</ul></section>
    <section class="ca-book"><h3 class="ok-h">⚖️ Cân đối thử <span class="ok-tag ${dr===cr?'good':'bad'}">${dr===cr?'Cân':'Lệch'}</span></h3>
      ${ids.length?`<div class="ca-scroll"><table class="ca-table tb"><thead><tr><th>TK</th><th>Dư Nợ</th><th>Dư Có</th></tr></thead><tbody>${rows}</tbody><tfoot><tr><td>Tổng</td><td class="num">${num(dr)}</td><td class="num">${num(cr)}</td></tr></tfoot></table></div>`:'<p class="ok-note">Chưa có bút toán nào trong kỳ.</p>'}
    </section>
    ${last?`<section class="ca-book"><h3 class="ok-h">📒 Nhật ký chung gần đây</h3><ul class="ca-journal">${last}</ul></section>`:''}`;
}

/* ---------------------------------------------------------------- the document desk (khay chứng từ) */
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
  const memo=`<div class="ca-from"><span class="ca-doc-ico" aria-hidden="true">${DOC_ICON[c.doc]||'📄'}</span><div class="grow"><small>Bộ ${i+1}/${cs.length} · ${x.esc(c.who||'')}</small><p>“${x.esc(c.quote||'')}”</p></div></div>`;
  if(c.stamp){
    const [ic,label]=RES[c.result]||['•',''];
    return `<section class="ca-case done">${memo}${paperView(t,c,x)}
      <div class="ca-verdict ${x.esc(c.result||'')}" role="status"><b>${ic} ${label}</b><span>Dấu của bạn: ${VLAB[c.stamp]}${c.result!=='ok'?` · Cần: ${VLAB[c.truth?.v]||''}`:''}</span><p>${x.esc(c.truth?.why||'')}</p></div></section>`;
  }
  return `<section class="ca-case" data-step-card="${x.esc(t.id)}:${x.esc(c.id)}">${memo}${paperView(t,c,x)}${c.tip?`<p class="ca-tip">💡 ${x.esc(c.tip)}</p>`:''}
    <div class="ca-tools"><small>${n?(clean()?`⭕ ${n}/${max}`:`⭕ Đã khoanh ${n}/${max} chỗ`):clean()?`⭕ 0/${max}`:'Chạm vào ô trên giấy để khoanh chỗ nghi sai'}</small>${c.hinted?'':x.cmd('💡 Gợi ý','ca_hint',{task:t.id,case:c.id},'ghost small')}</div></section>`;
}
function deskDoc(t,x){
  const cs=t.cases||[],c=caseOf(t,x),tray=t.tray||{};
  const chips=cs.map((v,i)=>{
    const st=v.stamp?(RES[v.result]||['•'])[0]:'';
    return btn(x,`<b>${i+1}</b><span aria-hidden="true">${DOC_ICON[v.doc]||'📄'}</span>${st?`<i>${st}</i>`:''}`,'car:pick',{task:t.id,case:v.id},`ca-qchip ${v.id===c?.id?'active':''} ${v.stamp?'stamped '+(v.result||''):''}`)
      .replace('<button ',`<button aria-label="Bộ ${i+1}${v.stamp?' · đã đóng dấu':''}" `);
  }).join('');
  return `<nav class="ca-queue" aria-label="Khay chứng từ"><span class="ca-qlabel">🗂️${clean()?'':' Khay'}</span>${chips}<small>${tray.stamped||0}/${tray.total||cs.length}${clean()?'':' đã đóng dấu'}</small></nav>
    ${c?caseCard(t,c,x):''}`;
}
function deskBar(t,x,g){
  const cs=t.cases||[],c=caseOf(t,x),tray=t.tray||{},i=cs.indexOf(c);
  if(tray.ready&&t.status!=='completed')return bar(x,t,clean()?`✓ ${tray.total}/${tray.total}`:`Đã đóng dấu đủ ${tray.total} bộ.`,g);
  if(!c)return bar(x,t,'Khay đang trống.');
  if(c.stamp){const [ic,label]=RES[c.result]||['•',''];return bar(x,t,`${clean()?'':'Bộ '}${i+1}: ${ic} ${label}`,g);}
  const n=(c.circles||[]).length;
  const stamps=['approve','escalate','reject'].map(v=>btn(x,`<span>${VLAB[v]}</span>`,'car:stamp',{task:t.id,case:c.id,verdict:v},`ca-sbtn ${v}`)).join('');
  // The three stamps are the choice: a full-width row of the bar (ui-bar top), readable on a phone.
  return bar(x,t,`🗂️ ${clean()?'':'Bộ '}${i+1}/${cs.length}${n?` · ⭕ ${n}`:''}`,'',false,{top:`<div class="ca-stampbar" role="group" aria-label="Đóng dấu">${stamps}</div>`});
}
/** What a zone on the paper is called (“MST”, “Số tiền”…), for the first tray's hint. */
function zoneName(c,z){
  const p=c.paper||{},row=[...(p.rows||[]),...(p.foot||[])].find(r=>r.z===z);
  return row?row.k:p.table?.z===z?'bảng hàng hóa':z==='note'?'giấy kẹp kèm':'chỗ sai';
}
/* The tray, one set at a time. The first tray (coach) lights the zone to circle and the right stamp. */
function deskSteps(t,x){
  const cs=t.cases||[],c=caseOf(t,x);
  if(!c||(t.tray||{}).ready)return [];
  if(c.stamp){
    const next=cs.find(v=>!v.stamp);
    return next?[{ok:null,label:`Sang bộ ${cs.indexOf(next)+1}/${cs.length}`,go:{act:'car:pick',data:{task:t.id,case:next.id},label:'Bộ tiếp theo ›'}}]:[];
  }
  const i=cs.indexOf(c)+1,k=coachOf(x,t)?.cases?.[c.id],circ=c.circles||[],out=[];
  if(!k)return [{ok:null,label:`Bộ ${i}/${cs.length}: soi giấy, khoanh chỗ sai rồi đóng dấu`,go:goto(x,t,'.ca-case:not(.done) .ca-sheet')}];
  if(k.v!=='approve'&&!k.z.some(z=>circ.includes(z))){
    const z=k.z.find(v=>(c.zones||[]).includes(v))||k.z[0],sel=`.ca-pz[data-case="${c.id}"][data-zone="${z}"]`;
    // First tray: the glowing zone is also what the bottom button (or the hint) circles.
    out.push({ok:null,label:`Bộ ${i}: ô “${zoneName(c,z)}” có vấn đề — khoanh lại`,go:{cmd:'ca_circle',payload:{task:t.id,case:c.id,zone:z},label:`⭕ Khoanh ô “${x.esc(zoneName(c,z))}”`},pulse:sel});
  }
  out.push({ok:null,label:`Bộ ${i}: đóng dấu ${VLAB[k.v]}`,go:{act:'car:stamp',data:{task:t.id,case:c.id,verdict:k.v},label:`🖋️ Đóng dấu ${VLAB[k.v]}`},pulse:`.ca-sbtn.${k.v}`});
  return out;
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
  const tabs=docs.map(d=>d.closed?btn(x,`<span class="ca-doc-ico" aria-hidden="true">📁</span><span class="grow">${x.esc(d.title)}<small>Mở · ${lag?12:6} phút</small></span>`,'car:open',{task:t.id,doc:d.id},'ca-tab closed'):btn(x,`<span class="ca-doc-ico" aria-hidden="true">📖</span><span class="grow">${x.esc(d.title)}${d.id===sel?'<small>Đang xem</small>':''}</span>`,'car:view',{task:t.id,doc:d.id===sel?'':d.id},`ca-tab ${d.id===sel?'active':''}`)).join('');
  return `<section class="ca-binder"><h3 class="ok-h">📚 Sổ tra cứu <small>${opened.length}/${docs.length} đã mở</small></h3><div class="ca-tabs">${tabs}</div>
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
  return `<section class="ca-recap" role="status"><h3 class="ok-h">🗂️ Khay vừa chốt · ${ok}/${cs.length} bộ chuẩn</h3><ul>${li}</ul></section>`;
}

/* ---------------------------------------------------------------- care: the month-end close plan, colleagues, the track */
const CLOSE_TAG={done:['✓ Kịp mốc','done'],late_done:['Xong · trễ mốc','late_done'],late:['Trễ mốc','late'],due:['Hạn hôm nay','due']};
function closePlan(x){
  const p=x.room.data?.care?.plan;if(!p||p.kind!=='close')return '';
  const rows=p.items.map(i=>{const [label,tone]=CLOSE_TAG[i.state]||[i.rel,'todo'];
    return {emoji:i.emoji,title:i.name,note:`${i.how} · mốc ${i.date}`,tag:{label,tone},tone:i.state==='late'?'bad':i.state==='due'?'warn':''};});
  return planCard(x,{title:`📅 ${p.title}`,sub:`${p.done}/${p.total} mốc`,rows,foot:`Đủ 5 mốc kịp hạn: thưởng ${p.bonus} xu và chị Hạnh ghi nhận. Thiếu hồ sơ nào thì bấm “＋ Nhận thêm việc”.`});
}
const care=(x,t)=>({plan:closePlan(x),people:mateCards(x,{prefix:P,t}),track:trackFold(x,{prefix:P,career:'corp_accounting'})});
const careBadge=x=>x.room.data?.care?.asked?1:0;

/* ---------------------------------------------------------------- the office desktop */
const strip=(x,t)=>statusStrip(x,t,{boss:BOSS,op:'ca_overtime',help:deskHelp(x,{key:'ok-corp_accounting',title:'🗂️ Bàn kế toán',boss:BOSS})});
/** Office shut: every ca_ command takes office time; these car: actions send one. */
const SHUT={prefix:'ca_',acts:['open','multi','num','order','match','fields','entry','submit','stamp','circle']};
const todayRules=x=>rulesList(x,x.room.data?.today?.rules||[],'Quy định đang áp dụng');
function currentMail(t,x){
  const timed=typeof t.due==='number',k=t.kind_info||{};
  const chips=[
    `<span class="ok-tag">${x.esc(k.emoji||'🧾')} ${x.esc(k.name||'Hồ sơ kế toán')}</span>`,
    !timed?`<span class="ok-tag ${t.patience<50?'warn':''}">Kiên nhẫn ${Number(t.patience)||0}%</span>`:'',
  ].join('');
  const help=!t.known&&t.variant==='desk'?note('Duyệt nhầm là bị trừ tiền.','Khay chứng từ'):'';
  return `<p class="ok-quote">“${x.esc(t.opening)}”</p>${t.brief?`<p class="ok-brief">🎯 ${x.esc(t.brief)}</p>`:''}<div class="ok-chips">${chips}</div>${help}`;
}
function nextText(t){
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
}
function dossierBar(t,x,g){
  if(currentStep(t))return bar(x,t,'',g);
  if(t.handover_options)return bar(x,t,clean()?'':'Chọn ghi chú bàn giao rồi nộp.',g);
  return bar(x,t,x.esc(nextText(t)));
}
/** {steps, final} for the header hint and the bottom button. */
function guideFor(t,x){
  const isDesk=t.variant==='desk';
  if(!t.known)return {steps:[{ok:null,label:isDesk?'Nhận khay chứng từ':'Nhận hồ sơ',go:{cmd:'ask',payload:{task:t.id},label:isDesk?(clean()?'📥 Nhận khay':'📥 Nhận khay chứng từ'):'📥 Nhận hồ sơ'}}]};
  if(isDesk){
    const tray=t.tray||{};
    return {steps:deskSteps(t,x),final:tray.ready&&t.status!=='completed'?{label:`📤 Chốt khay · ${tray.ok}/${tray.total} chuẩn`,go:{cmd:'ca_submit',payload:{task:t.id},confirm:'Chốt khay và báo kết quả cho chị Hạnh?'}}:null};
  }
  const steps=procSteps(x,t,{pre:'ca',confirm:CONFIRM});
  return {steps,final:!steps.length&&t.handover_options?{label:'📤 Nộp hồ sơ',go:{act:'car:submit',data:{task:t.id}}}:null};
}

export default {
  id:'corp_accounting',
  css:true,
  next(t,x){
    if(x&&t.known&&shut(x))return `Văn phòng đóng cửa lúc ${x.room.data.office.limit_time} — khép ca`;
    try{const n=x&&pending(guideFor(t,x).steps);if(n)return stepLine(n);}catch{/* the fixed lines below */}
    return nextText(t);
  },
  job(t,x){
    const isDesk=t.variant==='desk',rules=x.room.data?.today?.rules||[],fresh=rules.filter(r=>r.new).length;
    x.ui.lastTray=isDesk?t.id:null;
    const tabs=[{id:'inbox',icon:'📥',label:'Hộp thư',badge:openTasks(x).filter(v=>!v.known).length+careBadge(x)||''},
      {id:'doc',icon:'📂',label:'Hồ sơ'},{id:'rules',icon:'📋',label:'Quy định',badge:fresh||'',tone:'warn'},
      ...(isDesk?[]:[{id:'books',icon:'📒',label:'Sổ sách'}])];
    const inbox=inboxPane(x,{tasks:taskMails(x,t,currentMail(t,x)),other:dayMails(x,{boss:BOSS,key:`${t.id}:${t.known?1:0}`}),...care(x,t)});
    const gd=guideFor(t,x),g=guideOf(x,t,gd.steps,gd.final);
    if(!t.known){
      return desk(x,t,{cls:'ca',tabs,strip:strip(x,t),hint:g.hint,panes:{inbox,
        doc:envelope(x,t,{empty:isDesk?'Khay chứng từ còn nằm trên bàn chị Hạnh.':'Hồ sơ còn trong phong bì.',extra:isDesk?note('Duyệt nhầm là bị trừ tiền.','Khay chứng từ'):''}),
        rules:todayRules(x),books:booksPane(x)},
        bar:bar(x,t,'',g,true)});
    }
    // Office shut: the work is drawn disabled, the hint steps aside and the bar closes the day.
    const off=shut(x),hint=off?'':g.hint,work=html=>shutWork(x,html,SHUT);
    if(isDesk)return desk(x,t,{cls:'ca',tabs,strip:strip(x,t),hint,panes:{inbox:work(inbox),doc:work(deskDoc(t,x)),rules:work(todayRules(x)+binder(t,x))},bar:off?shutBar(x,t):deskBar(t,x,g)});
    return desk(x,t,{cls:'ca',tabs,strip:strip(x,t),hint,panes:{inbox:work(inbox),doc:work(stepCard(t,x)+docsPanel(t,x)),rules:todayRules(x)||'<p class="ok-note">Hôm nay chưa có quy định mới.</p>',books:booksPane(x)},bar:off?shutBar(x,t):dossierBar(t,x,g)});
  },
  idle(x){
    const d=x.room.data||{};if(!d.office)return '';
    return shutWork(x,idleDesk(x,{cls:'ca',strip:strip(x,null),recap:trayRecap(x),tasks:taskMails(x,null),other:dayMails(x,{boss:BOSS}),rules:todayRules(x),...care(x,null)}),SHUT);
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
    const cl=data.close;
    if(cl?.missed?.length)row('Trễ mốc khóa sổ',cl.missed.join(', '));
    if(cl?.month_end)row('Khóa sổ tháng',`${cl.on_time}/${cl.total} mốc kịp hạn${cl.bonus?` · thưởng +${cl.bonus} xu`:''}${cl.left?.length?` · còn thiếu: ${cl.left.join(', ')}`:''}`);
    const life=careSummary(data.care,x);
    if(!rows.length&&!trust&&!audit&&!life)return '';
    return summaryCard(x,data,{cls:'ca-sum',title:'🗂️ Bàn kế toán hôm nay',brief:data.dossiers?`${data.dossiers} hồ sơ hoàn tất`:desk.stamped?`${desk.stamped} chứng từ đã đóng dấu`:'',
      body:`${audit}${trust}${rows.length?`<div class="kv">${rows.join('')}</div>`:''}${life?`<h4 class="section-title">🧭 Đời sống văn phòng</h4><div class="kv">${life}</div>`:''}`});
  },
  tick(root,x){
    keepBarAboveFooter(root);
    sync(root,x);
    root.querySelectorAll('[data-entry]').forEach(b=>{
      const e=readEntry(b),sum=side=>e[side].reduce((s,r)=>{const a=amountOf(r.amount,'xu');return s+(a>0?a:0);},0);
      const d=sum('debit'),c=sum('credit');
      b.querySelector('[data-sum="debit"]').textContent=num(d);
      b.querySelector('[data-sum="credit"]').textContent=num(c);
      const bal=b.querySelector('[data-bal]');
      bal.textContent=!d&&!c?'Chưa nhập số':d===c?'✓ Cân':`Lệch ${num(Math.abs(d-c))}`;
      bal.className='ca-bal '+(!d&&!c?'':d===c?'ok':'bad');
    });
  },
  actions:{
    tab:switchTab,
    fold:foldToggle,
    goto:gotoAction,
    coach:coachFill,
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
      const v=amountOf(drafts(x)[dkey(t,st)],st.unit||'');
      if(v===null){x.toast('Chưa hiểu số đã ghi. Ghi số nguyên, vd 1.500.000, -200 hoặc 6+4.',true);return;}
      await send(x,t,st,v);
    },
    move(data,el,x){
      sync(rootOf(el),x);const list=drafts(x)[data.key];if(!list)return;
      const i=Number(data.i),j=i+Number(data.dir);if(j<0||j>=list.length)return;
      [list[i],list[j]]=[list[j],list[i]];(x.ui.moved??={})[data.key]=true;x.render();
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
        else{const v=amountOf(raw[f.id],f.unit||'');if(v===null){x.toast(`Ô “${f.label}” cần một số nguyên.`,true);return;}ans[f.id]=v;}
      }
      await send(x,t,st,ans);
    },
    addrow(data,el,x){sync(rootOf(el),x);const d=drafts(x)[data.key];if(d&&d[data.side].length<6){d[data.side].push({account:'',amount:''});x.render();}},
    delrow(data,el,x){sync(rootOf(el),x);const d=drafts(x)[data.key];if(d&&d[data.side].length>1){d[data.side].splice(Number(data.i),1);x.render();}},
    async entry(data,el,x){
      sync(rootOf(el),x);const [t,st]=stepOf(x,data);if(!st)return;
      const d=drafts(x)[dkey(t,st)],ans={debit:[],credit:[]};
      for(const side of ['debit','credit'])for(const r of d[side]){
        const a=amountOf(r.amount,'xu');
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
function rootOf(el){return el.closest('.career-job')||document;}
/** A money box that cannot be read yet is outlined (amount-parse.js); the note under it says why. */
const unread=(v,unit)=>amountNote(v,unit||'').bad?' amt-unread':'';
const HINT='ví dụ: 6+4, -200, 1.500.000';
function stepOf(x,data){
  const t=(x.room.tasks||[]).find(v=>v.id===data.task);
  return [t,t&&(t.proc||[]).find(s=>s.id===data.step)];
}
/** A step check. A wrong one names the boxes that are off (never their values): marked until the next check. */
async function send(x,t,st,answer){
  const r=await x.send(P+'step',{task:t.id,step:st.id,answer});
  if(r){(x.ui.miss??={})[dkey(t,st)]=r.correct===false?(st.kind==='number'?['']:Array.isArray(r.bad)?r.bad:[]):null;if(r.correct===false)x.render();}
  return r;
}
