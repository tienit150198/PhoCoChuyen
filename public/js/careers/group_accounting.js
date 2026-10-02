/** Kế toán tập đoàn · Sông Hồng Group — bàn hợp nhất inside the shared office desktop (office_kit.js):
 *  📥 Hộp thư (việc chị Mai Anh và các công ty con gửi), 📂 Hồ sơ (bàn đối chiếu hai sổ nội bộ, hoặc
 *  hồ sơ hợp nhất nhiều bước: bút toán loại trừ Nợ/Có tự cân, ghép tỷ giá, lịch khóa sổ),
 *  📋 Quy định (quy định đối chiếu + tỷ giá), 📒 Sổ sách (cơ cấu tập đoàn, sổ bút toán hợp nhất)
 *  and a sticky bar with the next step and the main action.
 *  No inline handlers: every button goes through data-command / data-action="car:*". */
import {statusStrip,taskMails,dayMails,inboxPane,rulesList,desk,bar,switchTab,keepBarAboveFooter,fold,idleDesk,openTasks,hhmm,planCard,mateCards,trackFold,careSummary,foldToggle,
  coachOf,goto,gotoAction,guideOf,procSteps,coachFill,shut,shutWork,shutBar} from './office_kit.js';
import {pending,stepLine} from '../v4/guide.js';

const P='ga_';
const BOSS='Chị Mai Anh';
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
  if(d.type==='cash')return `<div class="ga-cash"><table class="ga-table"><thead><tr><th>Mệnh giá</th><th>Số tờ</th></tr></thead><tbody>${(d.denoms||[]).map(([k,v])=>`<tr><td>💵 ${x.esc(k)}</td><td class="num">${num(v)}</td></tr>`).join('')}</tbody></table></div>`;
  if(d.type==='email')return `<div class="ga-mail"><p><b>Từ:</b> ${x.esc(d.sender||'')}</p><p><b>Chủ đề:</b> ${x.esc(d.subject||'')}</p><p>${x.esc(d.text||'')}</p></div>`;
  return `<p class="ga-paper">${x.esc(d.text||'')}</p>`;
}
/** The dossier's papers: folder tabs, one paper open at a time. */
function docsPanel(t,x){
  const st=currentStep(t),need=new Set(st?.docs||[]);
  const opened=t.docs.filter(d=>!d.closed);
  let sel=views(x)[t.id];
  if(!opened.some(d=>d.id===sel))sel=opened[0]?.id;
  const tabs=t.docs.map(d=>{
    const label=`<span class="ga-doc-ico" aria-hidden="true">${d.closed?'📁':'📄'}</span><span class="grow">${x.esc(d.title)}${d.closed?(need.has(d.id)?'<small>Cần mở cho bước này</small>':''):`<small>${x.esc(d.source)}</small>`}</span>`;
    return d.closed?btn(x,label,'car:open',{task:t.id,doc:d.id},`ga-tab closed ${need.has(d.id)?'need':''}`):btn(x,label,'car:view',{task:t.id,doc:d.id},`ga-tab ${d.id===sel?'active':''}`);
  }).join('');
  const doc=opened.find(d=>d.id===sel);
  return `<section class="ga-docs"><h3 class="ok-h">📄 Tài liệu <small>${opened.length}/${t.docs.length} đã mở</small></h3>
    <div class="ga-tabs" role="toolbar" aria-label="Tài liệu trong hồ sơ">${tabs}</div>
    ${doc?`<article class="ga-viewer" aria-live="polite"><header><b>${x.esc(doc.title)}</b><small>Nguồn: ${x.esc(doc.source)}</small></header>${docBody(doc,x)}</article>`:'<p class="ok-empty"><span aria-hidden="true">📁</span><span>Mở một tài liệu để xem.</span></p>'}
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
  const side=(id,label)=>`<div class="ga-vside ${id}"><h4>${label}</h4>${d[id].map((r,i)=>row(id,r,i)).join('')}${btn(x,`＋ Dòng ${label}`,'car:addrow',{key:k,side:id},'ghost small ga-add',d[id].length>=6)}</div>`;
  return `<div class="ga-voucher" data-entry="${x.esc(k)}">
    <div class="ga-vhead"><b>BÚT TOÁN HỢP NHẤT</b><small>${x.esc(t.title)}</small></div>
    <div class="ga-vcols">${side('debit','Nợ')}${side('credit','Có')}</div>
    <div class="ga-vfoot"><span>Tổng Nợ <b data-sum="debit">0</b></span><span>Tổng Có <b data-sum="credit">0</b></span><span class="ga-bal" data-bal>—</span></div>
  </div>`;
}
/** One line under each box of a calculation: where its number comes from and the formula, in words (never the number).
 *  Keyed by variant:step, then the field id ('' for a one-number step, '*' for every box of the step). */
const HOW={
  'ic_rec:diff':{'':'Số dư trên Sổ phải thu − số dư trên Sổ phải trả.'},
  'ic_rec:agreed':{'':'Số dư của bên KHÔNG phải điều chỉnh (theo nguyên nhân ở bước trước).'},
  'elim_upi:upi':{'':'Hàng nội bộ CÒN TỒN cuối kỳ (giá nội bộ) × tỷ suất lãi gộp; phần đã bán ra ngoài không tính.'},
  'elim_div:parent':{'':'Tổng cổ tức (Nghị quyết) × tỷ lệ sở hữu của công ty mẹ (Cơ cấu sở hữu).'},
  'elim_div:nci':{'':'Tổng cổ tức − phần của công ty mẹ.'},
  'fx_translate:tr':{'*':'Số NM trên Bảng cân đối thử × tỷ giá đã chọn ở bước trước (Tỷ giá tập đoàn duyệt).'},
  'fx_translate:diff':{'':'Tài sản − nợ phải trả (đã quy đổi) − vốn góp × tỷ giá lịch sử − (doanh thu − chi phí đã quy đổi). Có thể âm.'},
  'worksheet:cons':{'*':'Cộng ngang số của ba công ty trên dòng đó, rồi cộng cột loại trừ (số âm).'},
  'worksheet:ta':{'':'Cộng tổng tài sản ba công ty − các khoản loại trừ phía tài sản (phải thu nội bộ, khoản đầu tư).'},
  'nci:nci_profit':{'':'Lợi nhuận sau thuế của SH Logistics × tỷ lệ của cổ đông ngoài (Cơ cấu sở hữu).'},
  'nci:parent_profit':{'':'Lợi nhuận hợp nhất (Kết quả hợp nhất) − phần của cổ đông không kiểm soát.'},
  'nci:nci_close':{'':'30% vốn chủ đầu năm + phần lãi của cổ đông không kiểm soát − 30% cổ tức đã chia.'},
  'pbc:mat':{'':'5% × lợi nhuận trước thuế (giấy Mức trọng yếu).'},
  'variance:var':{'*':'Thực tế − Ngân sách trên cùng dòng, giữ nguyên dấu (âm nếu thực tế nhỏ hơn).'},
};
const how=(t,st,id,x)=>{const h=HOW[`${t.variant}:${st.id}`],s=h?.[id]??h?.['*'];return s?`<p class="ok-note">📐 ${x.esc(s)}</p>`:'';};
/** Boxes the last wrong check named (server `bad`; '' = a one-number step), outlined until the next check. */
const missOf=(x,t,st)=>new Set(x.ui.miss?.[dkey(t,st)]||[]);
function widget(t,st,x){
  const k=dkey(t,st),dr=drafts(x);
  if(st.kind==='choice')return `<div class="ga-options">${(st.options||[]).map(o=>x.cmd(x.esc(o.label),P+'step',{task:t.id,step:st.id,answer:o.id},'ga-opt').replace('<button ',`<button data-opt="${x.esc(o.id)}" `)).join('')}</div>`;
  if(st.kind==='multi'){
    const sel=dr[k]||[];
    return `<div class="ga-checks" data-multi="${x.esc(k)}">${(st.options||[]).map(o=>`<label class="ga-check"><input type="checkbox" value="${x.esc(o.id)}" ${sel.includes(o.id)?'checked':''}><span>${x.esc(o.label)}</span></label>`).join('')}</div>`;
  }
  if(st.kind==='number'){const bad=missOf(x,t,st).has('');
    return `<div class="ga-numrow">${bad?'<span class="ga-bad" aria-hidden="true">✗</span>':''}<input class="ga-input" type="number" inputmode="numeric" step="1" data-num="${x.esc(k)}" value="${x.esc(dr[k]??'')}" aria-label="${x.esc(st.title)}"${bad?' aria-invalid="true"':''}><span class="ga-unit">${x.esc(st.unit||'')}</span></div>${how(t,st,'',x)}`;}
  if(st.kind==='order'){
    const ids=dr[k]??=(st.items||[]).map(i=>i.id);
    const item=id=>(st.items||[]).find(i=>i.id===id)?.label||id;
    return `<ol class="ga-order">${ids.map((id,i)=>`<li><span class="ga-ord-n">${i+1}</span><span class="grow">${x.esc(item(id))}</span>${btn(x,'↑','car:move',{key:k,i,dir:-1},'ghost ga-mv',i===0)}${btn(x,'↓','car:move',{key:k,i,dir:1},'ghost ga-mv',i===ids.length-1)}</li>`).join('')}</ol>`;
  }
  if(st.kind==='match'){
    const cur=dr[k]||{};
    return `<div class="ga-match" data-match="${x.esc(k)}">${(st.left||[]).map(l=>`<label class="ga-mrow"><span>${x.esc(l.label)}</span><select data-left="${x.esc(l.id)}"><option value="">— chọn —</option>${(st.right||[]).map(r=>`<option value="${x.esc(r.id)}" ${cur[l.id]===r.id?'selected':''}>${x.esc(r.label)}</option>`).join('')}</select></label>`).join('')}</div>`;
  }
  if(st.kind==='fields'){
    const cur=dr[k]||{},bad=missOf(x,t,st);
    return `<div class="ga-fields" data-fields="${x.esc(k)}">${(st.fields||[]).map(f=>`<label class="ga-mrow"><span${bad.has(f.id)?' class="ga-bad"':''}>${bad.has(f.id)?'✗ ':''}${x.esc(f.label)}</span>${f.options?`<select data-field="${x.esc(f.id)}"><option value="">— chọn —</option>${f.options.map(o=>`<option value="${x.esc(o.id)}" ${cur[f.id]===o.id?'selected':''}>${x.esc(o.label)}</option>`).join('')}</select>`:`<span class="ga-numrow"><input class="ga-input" type="number" inputmode="numeric" step="1" data-field="${x.esc(f.id)}" value="${x.esc(cur[f.id]??'')}"${bad.has(f.id)?' aria-invalid="true"':''}><span class="ga-unit">${x.esc(f.unit||'')}</span></span>`}</label>${how(t,st,f.id,x)}`).join('')}</div>`;
  }
  if(st.kind==='entry')return voucher(t,st,x);
  return '';
}
/** Confirm label + action of each step kind (office_kit.procSteps puts it on the bottom button; choices answer on tap). */
const CONFIRM={multi:['✔ Xác nhận lựa chọn','car:multi'],number:['✔ Xác nhận','car:num'],order:['✔ Chốt thứ tự','car:order'],
  match:['✔ Xác nhận ghép','car:match'],fields:['✔ Xác nhận số liệu','car:fields'],entry:['✂️ Ghi bút toán hợp nhất','car:entry']};
/** The work sheet: the current step big, done steps folded away. */
function stepCard(t,x){
  const ps=t.proc_state||{},steps=t.proc||[],cur=steps.find(s=>s.state==='current');
  const solved=steps.filter(s=>s.state==='solved'),locked=steps.filter(s=>s.state==='locked').length,total=ps.total||steps.length;
  const last=solved[solved.length-1];
  const done=solved.length?fold(`✓ ${solved.length} bước đã xong <small>xem lại</small>`,`<ol class="ga-steps">${solved.map(st=>`<li class="ga-step solved"><span class="ga-dot" aria-hidden="true">✓</span><div class="grow"><b>${steps.indexOf(st)+1}. ${x.esc(st.title)}</b><p class="ga-ans">${summary(st,x)}</p>${st.explain?`<p class="ga-explain">${x.esc(st.explain)}</p>`:''}</div></li>`).join('')}</ol>`):'';
  let body;
  if(cur){
    const i=steps.indexOf(cur),tries=(ps.attempts||{})[cur.id]||0;
    const missing=(cur.docs||[]).filter(id=>t.docs.find(d=>d.id===id)?.closed);
    body=`<article class="ga-work" data-step-card="${x.esc(t.id)}:${x.esc(cur.id)}"><header class="ga-work-head"><span class="ga-dot" aria-hidden="true">${i+1}</span><div class="grow"><small>Bước ${i+1}/${total}${locked?` · còn ${locked} bước sau`:''}</small><h3>${x.esc(cur.title)}</h3></div></header>
      <p class="ga-prompt">${x.esc(cur.prompt||'')}</p>
      ${missing.length?`<p class="ga-warn">📁 Mở trước: ${missing.map(id=>x.esc(t.docs.find(d=>d.id===id).title)).join(', ')}</p>`:''}
      ${cur.tip?`<p class="ga-tip">💡 ${x.esc(cur.tip)}</p>`:''}
      ${widget(t,cur,x)}
      <div class="ga-stepfoot">${tries?`<small>Đã thử ${tries} lần</small>`:'<span></span>'}${cur.tip?'':x.cmd('💡 Xin gợi ý',P+'hint',{task:t.id},'ghost small')}</div></article>`;
  }else body=handover(t,x);
  const pct=total?Math.round(solved.length/total*100):0;
  return `<section class="ga-proc"><h3 class="ok-h">🧾 Quy trình <small>${solved.length}/${total} bước</small></h3>
    <div class="ga-prog" role="progressbar" aria-label="Tiến độ hồ sơ" aria-valuemin="0" aria-valuemax="${total}" aria-valuenow="${solved.length}"><i style="width:${pct}%"></i></div>
    ${last&&cur&&last.explain?`<p class="ga-lastok">✓ <b>${x.esc(last.title)}</b> — ${x.esc(last.explain)}</p>`:''}${body}${done}</section>`;
}
function handover(t,x){
  if(!t.handover_options)return '';
  const sel=x.ui.note?.[t.id]||'specific';
  return `<article class="ga-work ga-handover"><header class="ga-work-head"><span class="ga-dot" aria-hidden="true">📝</span><div class="grow"><small>Bước cuối</small><h3>Ghi chú bàn giao</h3></div></header>    ${t.handover_options.map(o=>`<label class="ga-check"><input type="radio" name="ga-note-${x.esc(t.id)}" value="${x.esc(o.id)}" ${o.id===sel?'checked':''}><span>${x.esc(o.label)}</span></label>`).join('')}</article>`;
}

/* ---------------------------------------------------------------- side: group chart & consolidation journal */
function groupChart(x){
  const ents=x.cc.entities||[],parent=ents.find(e=>e.own==null),subs=ents.filter(e=>e.own!=null);
  if(!parent)return '';
  return `<section class="ga-book"><h3 class="ok-h">🏢 Cơ cấu tập đoàn</h3><div class="ga-org">
    <div class="ga-node parent"><span aria-hidden="true">${x.esc(parent.emoji)}</span><b>${x.esc(parent.short)}</b><small>${x.esc(parent.name)}</small></div>
    <ul class="ga-subs">${subs.map(e=>`<li class="ga-node ${e.own<100?'nci':''} ${e.cur!=='xu'?'fx':''}"><span aria-hidden="true">${x.esc(e.emoji)}</span><b>${x.esc(e.short)}</b><small>${e.own}%${e.own<100?` · CĐKKS ${100-e.own}%`:''}${e.cur!=='xu'?` · báo cáo bằng ${x.esc(e.cur)}`:''}</small></li>`).join('')}</ul></div></section>`;
}
/** 📒 Sổ sách: the quarter's milestones, the group chart, the consolidation journal. */
function booksPane(x){
  const d=x.room.data||{},led=d.elim||{},ids=Object.keys(led).sort();
  const dr=ids.reduce((s,k)=>s+Math.max(0,led[k]),0),cr=ids.reduce((s,k)=>s+Math.max(0,-led[k]),0);
  const rows=ids.map(k=>`<tr><td><b>${x.esc(k)}</b> <small>${x.esc(acct(x,k).replace(/^\d+ · /,''))}</small></td><td class="num">${led[k]>0?num(led[k]):''}</td><td class="num">${led[k]<0?num(-led[k]):''}</td></tr>`).join('');
  const last=(d.entries||[]).slice(-3).reverse().map(e=>`<li><b>${x.esc(e.title)}</b><small>${e.lines.map(([a,b,m])=>`Nợ ${x.esc(a)}/Có ${x.esc(b)} ${num(m)}`).join(' · ')}</small></li>`).join('');
  const ms=(x.cc.milestones||[]).map(m=>`<li class="${(d.milestones||[]).includes(m.id)?'done':''}">${(d.milestones||[]).includes(m.id)?'✓':'○'} ${x.esc(m.name)}</li>`).join('');
  return `<section class="ga-book"><h3 class="ok-h">🗓️ ${x.esc(d.period?.label||'Kỳ khóa sổ quý')}</h3><ul class="ga-ms">${ms}</ul></section>
    ${groupChart(x)}
    <section class="ga-book"><h3 class="ok-h">✂️ Sổ bút toán hợp nhất <span class="ok-tag ${dr===cr?'good':'bad'}">${dr===cr?'Nợ = Có':'Lệch'}</span></h3>
      ${ids.length?`<div class="ga-scroll"><table class="ga-table tb"><thead><tr><th>TK</th><th>Nợ</th><th>Có</th></tr></thead><tbody>${rows}</tbody><tfoot><tr><td>Tổng</td><td class="num">${num(dr)}</td><td class="num">${num(cr)}</td></tr></tfoot></table></div>`:'<p class="ok-note">Quý này chưa có bút toán loại trừ.</p>'}
    </section>
    ${last?`<section class="ga-book"><h3 class="ok-h">📒 Bút toán gần đây</h3><ul class="ga-journal">${last}</ul></section>`:''}`;
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
/** A step check. A wrong one names the boxes that are off (never their values): marked until the next check. */
async function send(x,t,st,answer){
  const r=await x.send(P+'step',{task:t.id,step:st.id,answer});
  if(r){(x.ui.miss??={})[dkey(t,st)]=r.correct===false?(st.kind==='number'?['']:Array.isArray(r.bad)?r.bad:[]):null;if(r.correct===false)x.render();}
  return r;
}

function fxCard(x,hot){
  const f=x.room.data?.today?.fx;if(!f)return '';
  const arrow=f.delta>0?`▲${f.delta}`:f.delta<0?`▼${-f.delta}`:'=';
  return `<section class="ga-fx ${hot?'hot':''}" aria-label="Bảng tỷ giá hôm nay"><span class="ga-fx-big"><span aria-hidden="true">💱</span> <b>${num(f.closing)}</b><small>xu/NM cuối kỳ</small></span>
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
function meterBox(t,x){
  const m=t.meter||{},n=t.names||{},pct=m.total?Math.round(100*m.resolved/m.total):0;
  const gap=Math.abs(Number(m.gap)||0);
  const status=m.ready?`<b class="ga-ok">✓ Hai sổ khớp: ${num(m.agreed)} xu</b>`:`Còn lệch chưa có lý do: <b class="${gap?'ga-bad':''}">${num(gap)} xu</b> · ${m.resolved}/${m.total} dòng`;
  return `<section class="ga-meter" aria-live="polite"><div class="ga-mrow2"><span>Phải thu theo ${x.esc(n.a||'')} <b>${num(m.ra)}</b></span><span>Phải trả theo ${x.esc(n.b||'')} <b>${num(m.rb)}</b></span></div>
    <div class="ga-mbar"><i style="width:${pct}%"></i></div><p>${status}</p></section>`;
}
function evidence(t,x){
  const docs=t.docs||[];if(!docs.length)return '';
  return fold(`🔎 Bằng chứng <small>${docs.length} tờ</small>`,`<ul class="ga-evid">${docs.map(d=>`<li><b>${x.esc(d.title)}</b><small>${x.esc(d.source)}</small><p>${x.esc(d.text||'')}</p></li>`).join('')}</ul>`,false,'ga-evid-fold');
}
function boardDoc(t,x){
  const sel=msel(x,t),L=Object.fromEntries((t.lines||[]).map(l=>[l.id,l]));
  for(const s of ['a','b'])if(sel[s]&&(!L[sel[s]]||L[sel[s]].state))sel[s]=null;
  const n=t.names||{},hot=n.fx||x.room.data?.today?.mod?.id==='fx_swing';
  if(waiting(t,x))return `<section class="ga-wait"><p class="ga-wait-big"><span aria-hidden="true">⏳</span> Gói báo cáo hẹn <b>${x.esc(hhmm(t.wait))}</b> mới về</p>
      <p class="ok-note">Làm hồ sơ khác trước — đồng hồ chỉ chạy khi bạn làm việc.</p></section>${evidence(t,x)}`;
  const col=(side,title)=>`<section class="ga-col" aria-label="${x.esc(title)}"><h3 class="ga-colh"><span aria-hidden="true">${side==='a'?'📤':'📥'}</span> ${x.esc(title)}</h3><ul class="ga-lines">${(t.lines||[]).filter(l=>l.side===side).map(l=>lineCard(t,l,x,sel)).join('')}</ul></section>`;
  return `${meterBox(t,x)}${hot?fxCard(x,true):''}
    <div class="ga-cols">${col('a','Sổ phải thu · '+(n.a||''))}${col('b','Sổ phải trả · '+(n.b||''))}</div>${evidence(t,x)}`;
}
function boardBar(t,x,g){
  const m=t.meter||{},sel=msel(x,t),L=Object.fromEntries((t.lines||[]).map(l=>[l.id,l])),a=L[sel.a],b=L[sel.b];
  if(waiting(t,x))return bar(x,t,`Chờ gói báo cáo về lúc ${hhmm(t.wait)}`,g.cta);
  if(m.ready&&t.status!=='completed')return bar(x,t,`Hai sổ đã khớp: ${num(m.agreed)} xu.`,g.cta);
  const clear=btn(x,'✕ Bỏ chọn','car:mclear',{task:t.id},'ghost ga-x');
  if(a&&b){
    if(a.amount===b.amount)return bar(x,t,`<b>${x.esc(a.ref)}</b> ↔ <b>${x.esc(b.ref)}</b> · cùng ${num(a.amount)} xu`,clear+x.cmd('🔗 Ghép cặp này','ga_pair',{task:t.id,a:a.id,b:b.id},'primary ga-dopair'));
    return bar(x,t,`<b>${x.esc(a.ref)}</b> ↔ <b>${x.esc(b.ref)}</b> · lệch ${num(Math.abs(a.amount-b.amount))} xu — vì sao?`,
      (t.causes||[]).map(c=>x.cmd(`${x.esc(c.emoji)} ${x.esc(c.label)}`,'ga_pair',{task:t.id,a:a.id,b:b.id,cause:c.id},`ga-chipbtn ga-cause-${x.esc(c.id)}`)).join('')+clear);
  }
  const one=a||b;
  if(one)return bar(x,t,`<b>${x.esc(one.ref)}</b> · ${money(one)} xu — chạm dòng ${one.side==='a'?'bên mua':'bên bán'} để ghép, hoặc chọn lý do:${one.tip?`<span class="ga-bartip">💡 ${x.esc(one.tip)}</span>`:''}`,
    (t.tags||[]).map(g=>x.cmd(`${x.esc(g.emoji)} ${x.esc(g.label)}`,'ga_tag',{task:t.id,line:one.id,tag:g.id},`ga-chipbtn ga-tag-${x.esc(g.id)}`)).join('')
    +(one.hinted?'':x.cmd('💡 Gợi ý','ga_hint',{task:t.id,line:one.id},'ghost'))+clear);
  return bar(x,t,`🔗 Còn ${(m.total||0)-(m.resolved||0)} dòng`,g.cta);
}
/* The matching board. The first board (coach) walks line by line: light the line, its partner (or the reason),
 * then the pair / cause button. Later boards just point at the two ledgers. */
function boardSteps(t,x){
  const m=t.meter||{};
  if(waiting(t,x))return [{ok:null,label:`Chờ gói báo cáo về lúc ${hhmm(t.wait)} — hoặc gọi giục`,go:{cmd:'ga_chase',payload:{task:t.id},label:'📞 Gọi giục anh Phong (10 phút)'}}];
  if(m.ready||t.status==='completed')return [];
  const sel=msel(x,t),L=Object.fromEntries((t.lines||[]).map(l=>[l.id,l])),a=L[sel.a]&&!L[sel.a].state?L[sel.a]:null,b=L[sel.b]&&!L[sel.b].state?L[sel.b]:null;
  const left=(m.total||0)-(m.resolved||0),co=coachOf(x,t)?.lines;
  const line=id=>`.ga-line[data-line="${id}"]`,step=(label,sel,go)=>({ok:null,label,go:go||goto(x,t,sel),pulse:sel});
  // First board: the glowing line is also what the bottom button (or the hint) picks.
  const pick=(l,label)=>step(label,line(l.id),{act:'car:msel',data:{task:t.id,line:l.id,side:l.side},label:`👆 Chọn ${x.esc(l.ref)}`});
  if(!co)return [{ok:null,label:`Còn ${left} dòng: ghép hai dòng cùng chứng từ, dòng lẻ chọn lý do`,go:goto(x,t,'.ga-cols','👆 Chạm một dòng để bắt đầu')}];
  const open=(t.lines||[]).filter(l=>!l.state&&co[l.id]);
  const one=a||b,cur=one||open.find(l=>l.side==='a')||open[0];
  if(!cur)return [];
  const k=co[cur.id]||{};
  if(k.tag){
    if(!one||one.id!==cur.id)return [pick(cur,`${cur.ref}: dòng lẻ — chọn dòng rồi chọn lý do`)];
    if(a&&b)return [{ok:null,label:'Bỏ chọn dòng thừa',go:{act:'car:mclear',data:{task:t.id},label:'✕ Bỏ chọn'}}];
    const tg=(t.tags||[]).find(g=>g.id===k.tag);
    return [step(`${cur.ref}: lý do “${tg?.label||k.tag}”`,`.ga-tag-${k.tag}`,{cmd:'ga_tag',payload:{task:t.id,line:cur.id,tag:k.tag},label:`${tg?.emoji||''} ${x.esc(tg?.label||k.tag)}`})];
  }
  const mate=L[k.mate];
  if(!mate||mate.state)return [{ok:null,label:`Ghép ${cur.ref} với dòng cùng chứng từ bên kia`,go:goto(x,t,'.ga-cols')}];
  const [pa,pb]=cur.side==='a'?[cur,mate]:[mate,cur];
  const wrong=(a&&a.id!==pa.id)||(b&&b.id!==pb.id);
  if(wrong)return [{ok:null,label:'Chọn nhầm dòng — bỏ chọn rồi làm lại',go:{act:'car:mclear',data:{task:t.id},label:'✕ Bỏ chọn'}}];
  if(!a)return [pick(pa,`Chọn ${pa.ref} (sổ bên bán)`)];
  if(!b)return [pick(pb,`Chọn ${pb.ref} (sổ bên mua) — cùng chứng từ`)];
  if(pa.amount===pb.amount)return [step(`Ghép ${pa.ref} ↔ ${pb.ref}`,'.ga-dopair',{cmd:'ga_pair',payload:{task:t.id,a:pa.id,b:pb.id},label:'🔗 Ghép cặp này'})];
  const c=(t.causes||[]).find(v=>v.id===k.cause);
  return [step(`Lệch ${num(Math.abs(pa.amount-pb.amount))} xu: ${c?.label||''}`,`.ga-cause-${k.cause}`,{cmd:'ga_pair',payload:{task:t.id,a:pa.id,b:pb.id,cause:k.cause},label:`${c?.emoji||''} ${x.esc(c?.label||'')}`})];
}
function boardRecap(x){
  const t=(x.room.tasks||[]).find(v=>v.id===x.ui.lastBoard);
  if(!t||t.status!=='completed'||!t.lines)return '';
  const n=t.names||{},m=t.meter||{};
  const note=(t.lines||[]).filter(l=>l.state&&(l.state.k==='tag'||(l.state.cause&&l.side==='a')));
  return `<section class="ga-recap" role="status"><h3 class="ok-h">🔁 Đối chiếu vừa chốt · ${x.esc(n.a||'')} ↔ ${x.esc(n.b||'')}</h3>
    <p>Loại trừ <b>${num(m.agreed)} xu</b> (Nợ 331 / Có 131)${t.mistakes?` · ${t.mistakes} lần sửa sai`:' · không sửa lần nào'}.</p>
    ${note.length?`<ul>${note.map(l=>`<li>${x.esc(l.why||'')}</li>`).join('')}</ul>`:''}</section>`;
}

/* ---------------------------------------------------------------- the office desktop */
/* ---------------------------------------------------------------- care: reporting packs, audit questions, colleagues, the track */
const PACK_TAG={wait:['Chưa tới hạn','wait'],late:['Trễ hạn','late'],in:['Đã về · chưa soát','in'],fixing:['Đang sửa','fixing'],ok:['✓ Đã soát','ok']};
function packPlan(x){
  const p=x.room.data?.care?.plan;if(!p||p.kind!=='packs')return '';
  const rows=p.items.map(i=>{const [label,tone]=PACK_TAG[i.state]||[i.state,''];
    const note=i.state==='fixing'?`${i.contact} gửi lại bản sửa ${i.back}`:i.promised?`${i.contact} hứa gửi sớm`:i.state==='wait'?`${i.contact} · hạn ${p.due}`:i.contact;
    const act=!x.room.open?'':i.can_review?x.cmd(`🔎 Soát gói · ${p.review} phút`,'ga_review',{sub:i.sub},'primary small'):i.can_nudge?x.cmd(`📞 Gọi giục · ${p.nudge} phút`,'ga_nudge',{sub:i.sub},'ghost small'):'';
    // A pack that came in only needs you (the card opens by itself) once the filing day has come.
    const now=p.due_rel==='Hôm nay'||p.due_rel==='Đã qua';
    return {emoji:i.emoji,title:i.short,note,tag:{label,tone},act,tone:i.state==='late'?'bad':i.state==='in'&&now?'warn':''};});
  const qs=(p.queries||[]).map(q=>({emoji:'❓',title:q.text,note:`Chị Thảo · trả lời trước hết ${q.date} (${q.rel})${q.minutes>10?' · gói chưa soát nên lâu hơn':''}`,
    tag:{label:q.rel,tone:q.rel==='Hôm nay'?'due':''},act:x.room.open?x.cmd(`✉️ Trả lời · ${q.minutes} phút`,'ga_answer',{query:q.id},'primary small'):'',tone:q.rel==='Hôm nay'?'warn':''}));
  return planCard(x,{title:`📦 ${p.title}`,sub:`${p.done}/${p.total} đã soát`,rows,
      foot:`Hạn nộp gói: ${x.esc(p.due)} (${x.esc(p.due_rel)}). Soát đủ 4 gói trước ngày chốt quý: thưởng ${p.bonus} xu. Gói trễ mà chưa gọi giục lần nào thì chị Mai Anh không vui.`})
    +planCard(x,{title:'❓ Câu hỏi kiểm toán',sub:`${qs.length} câu chờ`,rows:qs,key:'plan2',foot:'Trả lời trong 2 ngày. Gói đã soát thì có sẵn giấy làm việc.'});
}
const care=(x,t)=>({plan:packPlan(x),people:mateCards(x,{prefix:P,t}),track:trackFold(x,{prefix:P,career:'group_accounting'})});
const careBadge=x=>{const p=x.room.data?.care?.plan;return (x.room.data?.care?.asked?1:0)+((p?.items)||[]).filter(i=>i.can_review).length+((p?.queries)||[]).length;};

const strip=(x,t)=>statusStrip(x,t,{boss:BOSS,op:'ga_overtime'});
/** Office shut: every ga_ command takes office time; these car: actions send one. */
const SHUT={prefix:'ga_',acts:['open','multi','num','order','match','fields','entry','submit']};
const todayRules=x=>rulesList(x,x.room.data?.today?.rules||[],'Quy định đối chiếu');
function currentMail(t,x){
  const timed=typeof t.due==='number',k=t.kind_info||{};
  const chips=[`<span class="ok-tag">${x.esc(k.emoji||'🧾')} ${x.esc(k.name||'Hồ sơ hợp nhất')}</span>`,
    !timed?`<span class="ok-tag ${t.patience<50?'warn':''}">Kiên nhẫn ${Number(t.patience)||0}%</span>`:''].join('');
  const help=!t.known&&t.variant==='match'?'<p class="ok-note">Mỗi lần ghép sai tốn 20 phút soát lại.</p>':'';
  return `<p class="ok-quote">“${x.esc(t.opening)}”</p>${t.brief?`<p class="ok-brief">🎯 ${x.esc(t.brief)}</p>`:''}<div class="ok-chips">${chips}</div>${help}`;
}
function dossierBar(t,x,g){
  if(currentStep(t))return bar(x,t,'',g.cta);
  if(t.handover_options)return bar(x,t,'Chọn ghi chú bàn giao rồi nộp.',g.cta);
  return bar(x,t,'Đã nộp hồ sơ.');
}
/** {steps, final} for the header hint and the bottom button. */
function guideFor(t,x){
  const board=t.variant==='match';
  if(!t.known)return {steps:[{ok:null,label:board?'Nhận hai sổ đối chiếu':'Nhận hồ sơ',go:{cmd:'ask',payload:{task:t.id},label:board?'📥 Nhận hai sổ đối chiếu':'📥 Nhận hồ sơ'}}]};
  if(board){
    const m=t.meter||{};
    return {steps:boardSteps(t,x),final:m.ready&&t.status!=='completed'?{label:`✂️ Loại trừ ${num(m.agreed)} xu`,go:{cmd:'ga_submit',payload:{task:t.id},confirm:`Chốt đối chiếu và ghi bút toán loại trừ Nợ 331 / Có 131: ${num(m.agreed)} xu?`}}:null};
  }
  const steps=procSteps(x,t,{pre:'ga',confirm:CONFIRM});
  return {steps,final:!steps.length&&t.handover_options?{label:'📤 Nộp hồ sơ',go:{act:'car:submit',data:{task:t.id}}}:null};
}

export default {
  id:'group_accounting',
  css:true,
  next(t,x){
    if(x&&t.known&&shut(x))return `Văn phòng đóng cửa lúc ${x.room.data.office.limit_time} — khép ca`;
    try{const n=x&&pending(guideFor(t,x).steps);if(n)return stepLine(n);}catch{/* the fixed lines below */}
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
    const board=t.variant==='match',fresh=(x.room.data?.today?.rules||[]).filter(r=>r.new).length;
    x.ui.lastBoard=board?t.id:null;
    const tabs=[{id:'inbox',icon:'📥',label:'Hộp thư',badge:openTasks(x).filter(v=>!v.known).length+careBadge(x)||''},
      {id:'doc',icon:'📂',label:'Hồ sơ'},{id:'rules',icon:'📋',label:'Quy định',badge:fresh||'',tone:'warn'},{id:'books',icon:'📒',label:'Sổ sách'}];
    const inbox=inboxPane(x,{tasks:taskMails(x,t,currentMail(t,x)),other:dayMails(x,{boss:BOSS,key:`${t.id}:${t.known?1:0}`}),...care(x,t)});
    const rules=todayRules(x)+fxCard(x,false);
    const gd=guideFor(t,x),g=guideOf(x,t,gd.steps,gd.final);
    if(!t.known)return desk(x,t,{cls:'ga',tabs,strip:strip(x,t),hint:g.hint,panes:{inbox,rules,books:booksPane(x),
      doc:`<p class="ok-empty"><span aria-hidden="true">✉️</span><b>${x.esc(t.title)}</b><span>${board?'Hai sổ đối chiếu còn nằm trong hộp thư của công ty con.':'Hồ sơ còn trong phong bì.'}</span></p>`},
      bar:bar(x,t,'',g.cta,true)});
    // Office shut: the work is drawn disabled, the hint steps aside and the bar closes the day.
    const off=shut(x),hint=off?'':g.hint,work=html=>shutWork(x,html,SHUT);
    if(board){
      // Picking lines and choosing why stay in the bar; the guide's button covers the rest (waiting, ready, nothing picked).
      const sel=msel(x,t),picked=!waiting(t,x)&&!(t.meter||{}).ready&&(sel.a||sel.b);
      return desk(x,t,{cls:'ga',tabs,strip:strip(x,t),hint,panes:{inbox:work(inbox),rules,books:booksPane(x),doc:work(boardDoc(t,x))},bar:off?shutBar(x,t):boardBar(t,x,picked?{cta:''}:g)});
    }
    return desk(x,t,{cls:'ga',tabs,strip:strip(x,t),hint,panes:{inbox:work(inbox),rules,books:booksPane(x),doc:work(stepCard(t,x)+docsPanel(t,x))},bar:off?shutBar(x,t):dossierBar(t,x,g)});
  },
  idle(x){
    const d=x.room.data||{};if(!d.office)return '';
    return shutWork(x,idleDesk(x,{cls:'ga',strip:strip(x,null),recap:boardRecap(x),tasks:taskMails(x,null),other:dayMails(x,{boss:BOSS}),rules:todayRules(x),...care(x,null)}),SHUT);
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
    if(data.queries_late)row('Câu hỏi kiểm toán trả lời chậm',String(data.queries_late));
    if(data.packs)row('Gói báo cáo quý',`${data.packs.ok}/${data.packs.total} đã soát${data.packs.bonus?` · thưởng +${data.packs.bonus} xu`:''}${data.packs.silent?.length?` · chưa gọi giục: ${data.packs.silent.join(', ')}`:''}`);
    const life=careSummary(data.care,x);
    if(!rows.length&&!trust&&!data.audit&&!data.board&&!life)return '';
    return `<article class="card space-top ga-sum"><h4 class="section-title">🏢 Bàn hợp nhất hôm nay</h4>${note(data.audit)}${note(data.board)}${trust}${rows.length?`<div class="kv">${rows.join('')}</div>`:''}${life?`<h4 class="section-title">🧭 Đời sống văn phòng</h4><div class="kv">${life}</div>`:''}</article>`;
  },
  tick(root,x){
    keepBarAboveFooter(root);
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
    tab:switchTab,
    fold:foldToggle,
    goto:gotoAction,
    coach:coachFill,
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
