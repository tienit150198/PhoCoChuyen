/** Dịch vụ Thuế & Tiền lương Minh Bạch — the payroll desk inside the shared office desktop (office_kit.js):
 *  📥 Hộp thư (việc chị Hồng giao, khiếu nại lương), 📂 Hồ sơ (bảng lương nháp soát từng người, hoặc
 *  tờ khai làm từng bước với giấy tờ gốc và máy tính bàn), 📋 Quy định (quy định kỳ lương + sổ tay luật),
 *  and a sticky bar with the next step and the main action. */
import {statusStrip,taskMails,dayMails,inboxPane,rulesList,desk,bar,switchTab,keepBarAboveFooter,fold,idleDesk,dueOf,openTasks,planCard,mateCards,trackFold,careSummary,foldToggle,
  coachOf,goto,gotoAction,guideOf,shut,shutWork,shutBar,summaryCard} from './office_kit.js';
import {pending,stepLine} from '../v4/guide.js';

const BOSS='Chị Hồng';
const fmtN=n=>String(Math.trunc(Number(n)));   // whole numbers as the player types them: 12400, never 12.400 (owner, 01/10)
/** A payroll page with thousands dots dropped from its text (12.400 xu → 12400 xu), never inside attributes.
 *  The task's own texts keep their form on the server: they are part of the facts the server validates. */
const plain=html=>String(html).replace(/>([^<]+)</g,(m,t)=>'>'+t.replace(/(\d)\.(?=\d{3}(?!\d))/g,'$1')+'<');
const lab=(list,id)=>list?.find(o=>o.id===id)?.label??id;
const state=(x,t)=>x.ui[t.id]??={paper:0,sel:{},multi:{},order:{}};
const fid=(t,...p)=>['tp',t.id,...p].join('-').replace(/[^a-zA-Z0-9_-]/g,'_');
const NUMERIC=/^[−-]?[\d.]+( xu)?$/;

/** The toast of a wrong check from a server without `toast`: “✗ Chưa khớp 1/2 ô.” (+ the lunch note, if any). */
function shortMiss(st,r){
  const n=st.kind==='fields'?st.fields.length:0,b=Array.isArray(r.bad)?r.bad.length:0,lunch=String(r.message||'').match(/🍜[^.]*\./)?.[0];
  return `✗ Chưa khớp${n?` ${n-b}/${n} ô`:''}.${lunch?' '+lunch:''}`;
}

/** Integer typed by a person: "12.400", "12 400", "-900" → 12400 / -900; anything else → null. */
function parseIntVN(raw){
  const s=String(raw??'').trim().replace(/−/g,'-').replace(/[\s.,_]/g,'').replace(/xu$/i,'');
  return /^-?\d{1,10}$/.test(s)?Number(s):null;
}

/** Tiny calculator (no eval: CSP-safe). + − × ÷ ( ) and postfix %. "12.400" = twelve thousand four hundred. */
function calc(src){
  const s=String(src).replace(/\s+/g,'').replace(/[×x*]/gi,'*').replace(/[÷:]/g,'/').replace(/−/g,'-');
  let i=0;
  const num=()=>{const m=/^\d+(?:[.,]\d+)*/.exec(s.slice(i));if(!m)throw new Error('số');i+=m[0].length;
    const t=m[0];if(/^[1-9]\d{0,2}(\.\d{3})+$/.test(t))return Number(t.replace(/\./g,''));
    const parts=t.split(/[.,]/);if(parts.length>2)throw new Error('số');return Number(parts.join('.'));};
  const factor=()=>{
    if(s[i]==='-'){i++;return -factor();}
    if(s[i]==='+'){i++;return factor();}
    let v;
    if(s[i]==='('){i++;v=expr();if(s[i]!==')')throw new Error(')');i++;}else v=num();
    while(s[i]==='%'){i++;v/=100;}
    return v;
  };
  const term=()=>{let v=factor();while(s[i]==='*'||s[i]==='/'){const op=s[i++],r=factor();v=op==='*'?v*r:v/r;}return v;};
  const expr=()=>{let v=term();while(s[i]==='+'||s[i]==='-'){const op=s[i++],r=term();v=op==='+'?v+r:v-r;}return v;};
  if(!s||s.length>120)throw new Error('trống');
  const v=expr();if(i!==s.length||!Number.isFinite(v))throw new Error('lỗi');
  return v;
}

function paperView(p,x){
  const body=p.kind==='table'
    ?`<div class="tp-scroll" tabindex="0" aria-label="${x.esc(p.title)}"><table class="tp-table"><thead><tr>${p.head.map(h=>`<th scope="col">${x.esc(h)}</th>`).join('')}</tr></thead><tbody>${p.rows.map(r=>`<tr>${r.map(v=>`<td class="${NUMERIC.test(String(v))?'num':''}">${x.esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`
    :`<dl class="tp-kv">${p.rows.map(([k,v])=>`<dt>${x.esc(k)}</dt><dd class="${NUMERIC.test(String(v))?'num':''}">${x.esc(v)}</dd>`).join('')}</dl>`;
  return `<article class="tp-paper"><h4>${x.esc(p.title)}</h4>${body}${p.note?`<p class="tp-paper-note">✎ ${x.esc(p.note)}</p>`:''}</article>`;
}
/** Paper tabs (one paper at a time). */
function paperTabs(t,x,label){
  const u=state(x,t),idx=Math.min(u.paper,t.papers.length-1);
  return {idx,html:`<div class="tp-tabs" role="toolbar" aria-label="${x.esc(label)}">${t.papers.map((q,i)=>`<button type="button" class="tp-tab ${i===idx?'on':''}" data-action="car:paper" data-task="${x.esc(t.id)}" data-i="${i}" aria-pressed="${i===idx}"><span aria-hidden="true">📄</span> ${x.esc(q.title)}</button>`).join('')}</div>`};
}

function solvedText(st,x){
  const a=st.answer;
  switch(st.kind){
    case'choice':return x.esc(lab(st.options,a));
    case'multi':return (a||[]).map(v=>x.esc(lab(st.options,v))).join(' · ');
    case'number':return `<b class="num">${fmtN(a)}</b>`;
    case'order':return (a||[]).map((v,i)=>`${i+1}. ${x.esc(lab(st.items,v))}`).join('<br>');
    case'match':return Object.entries(a||{}).map(([l,r])=>`${x.esc(lab(st.left,l))} → <b>${x.esc(lab(st.right,r))}</b>`).join('<br>');
    case'fields':return `<table class="tp-cells">${Object.entries(a||{}).map(([k,v])=>{const f=st.fields.find(q=>q.id===k);return `<tr><th scope="row">${x.esc(f?.label||k)}</th><td class="num">${f?.options?x.esc(lab(f.options,v)):fmtN(v)}</td></tr>`;}).join('')}</table>`;
  }
  return '';
}

/** One line under each box of a form: where its number comes from and the formula, in words (never the number).
 *  Keyed by form:step, then the field id ('' for a one-number step). Same rules as 📘 Sổ tay quy định. */
const HOW={
  'payslip:gross':{day_rate:'Lương giờ (Hợp đồng) × 8 giờ.',leave:'Số ngày nghỉ KHÔNG lương (Bảng chấm công) × Lương 1 ngày. Nghỉ phép năm không trừ.',
    ot:'Mỗi dòng tăng ca: số giờ × Lương giờ × hệ số đã xếp ở bước 1, rồi cộng lại.',gross:'Lương cơ bản − Trừ nghỉ không lương + 3 phụ cấp trong Hợp đồng + Tiền tăng ca.'},
  'payslip:ins':{bhxh:'Lương đóng bảo hiểm (Hợp đồng) × 8%, làm tròn xuống.',bhyt:'Lương đóng bảo hiểm × 1,5% (× 15 ÷ 1000), làm tròn xuống.',bhtn:'Lương đóng bảo hiểm × 1%, làm tròn xuống.'},
  'payslip:tax':{taxable:'Tổng thu nhập − ăn trưa (miễn tối đa 700) − 3 khoản bảo hiểm − 5000 bản thân − 2000 × người phụ thuộc ĐÃ đăng ký.',
    pit:'Áp biểu lũy tiến tháng (📋 Quy định · Thuế TNCN) lên Thu nhập tính thuế, làm tròn xuống.'},
  'payslip:net':{'':'Tổng thu nhập − 3 khoản bảo hiểm − Thuế TNCN (số của các bước trên).'},
  'transfer:total':{'':'Tổng thực lĩnh trên Bảng lương ĐÃ DUYỆT — không lấy tổng file nháp.'},
  'vat:vat':{output:'Cộng cột “Thuế GTGT” của mọi hóa đơn bán ra.',input:'Cộng cột “Thuế GTGT” của hóa đơn mua vào, bỏ các tờ đã loại ở bước 1.'},
  'vat:payable':{'':'Thuế đầu ra − thuế đầu vào được khấu trừ (bước trước).'},
  'calendar:late':{'':'Số tiền thuế × 3 × số ngày trễ ÷ 10000 (0,03% mỗi ngày), làm tròn xuống.'},
  'question:diff':{'':'Dòng “Thực lĩnh” phiếu tháng 8 − dòng “Thực lĩnh” phiếu tháng 9.'},
  'yearend:calc':{deduct:'12 × 5000 bản thân + 2000 × số tháng có người phụ thuộc (giấy “Người phụ thuộc đã đăng ký”).',
    taxable:'Thu nhập chịu thuế của MỌI nơi − bảo hiểm bắt buộc − Tổng giảm trừ.',due:'Áp biểu lũy tiến NĂM (mốc tháng × 12) lên Thu nhập tính thuế cả năm, làm tròn xuống.',
    balance:'Thuế phải nộp cả năm − thuế đã khấu trừ ở mọi nơi; âm là được hoàn.'},
};
/** One box of a calculation as a small card (owner, 02/10: the two-column table was a wall on a phone): the label on
 *  top, its 📐 formula folded under it (check() opens it on a box that did not match), the box full width. After a wrong check
 *  the boxes off say “chưa khớp” in red and the others “khớp” in green, until the next check. `key` is '' for a
 *  one-number step. */
function field(t,st,x,{key,label,options,miss}){
  const id=key?fid(t,st.id,key):fid(t,st.id),bad=!!miss?.bad?.includes(key),ok=!!miss&&!bad&&st.kind==='fields';
  const how=HOW[`${t.form}:${st.id}`]?.[key],mark=bad?' aria-invalid="true"':'';
  const box=options?`<select class="${bad?'tp-bad':''}" id="${id}" data-preserve${mark}><option value="">Chọn…</option>${options.map(o=>`<option value="${x.esc(o.id)}">${x.esc(o.label)}</option>`).join('')}</select>`
    :`<input class="input tp-num${bad?' tp-bad':''}" id="${id}" data-preserve type="text" inputmode="numeric" autocomplete="off" placeholder="0"${mark}>`;
  return `<div class="tp-field${bad?' bad':ok?' ok':''}"><div class="tp-field-top"><label for="${id}">${x.esc(label)}</label>${bad?'<span class="tp-ftag bad">✗ chưa khớp</span>':ok?'<span class="tp-ftag ok">✓ khớp</span>':''}</div>
    ${how?`<details class="tp-how" id="${id}-how"><summary>📐 Cách tính</summary><p>${x.esc(how)}</p></details>`:''}${box}</div>`;
}

function inputView(st,t,x){
  const u=state(x,t),sid=x.esc(st.id),tid=x.esc(t.id),miss=u.miss?.[st.id];
  switch(st.kind){
    case'choice':return `<div class="tp-choices">${st.options.map(o=>`<button type="button" class="tp-choice ${u.sel[st.id]===o.id?'on':''}" data-action="car:pick" data-task="${tid}" data-step="${sid}" data-v="${x.esc(o.id)}" aria-pressed="${u.sel[st.id]===o.id}"><span class="tp-box radio" aria-hidden="true">${u.sel[st.id]===o.id?'●':''}</span>${x.esc(o.label)}</button>`).join('')}</div>`;
    case'multi':{const on=u.multi[st.id]||[];return `<div class="tp-choices">${st.options.map(o=>`<button type="button" class="tp-choice check ${on.includes(o.id)?'on':''}" data-action="car:toggle" data-task="${tid}" data-step="${sid}" data-v="${x.esc(o.id)}" aria-pressed="${on.includes(o.id)}"><span class="tp-box" aria-hidden="true">${on.includes(o.id)?'✓':''}</span>${x.esc(o.label)}</button>`).join('')}</div>`;}
    case'number':return `<div class="tp-fields">${field(t,st,x,{key:'',label:'Đáp số (xu)',miss})}</div>`;
    case'fields':return `<div class="tp-fields">${st.fields.map(f=>field(t,st,x,{key:f.id,label:f.label,options:f.options,miss})).join('')}</div>`;
    case'match':return `<div class="tp-match">${st.left.map(l=>`<label class="tp-cell-row"><span>${x.esc(l.label)}</span><select id="${fid(t,st.id,l.id)}" data-preserve><option value="">Chọn…</option>${st.right.map(r=>`<option value="${x.esc(r.id)}">${x.esc(r.label)}</option>`).join('')}</select></label>`).join('')}</div>`;
    case'order':{
      const picked=u.order[st.id]||[],rest=st.items.filter(o=>!picked.includes(o.id));
      return `<ol class="tp-order">${picked.map((id,i)=>`<li><span class="tp-no">${i+1}</span><span class="grow">${x.esc(lab(st.items,id))}</span><button type="button" class="btn small ghost" data-action="car:unpick" data-task="${tid}" data-step="${sid}" data-i="${i}" aria-label="Bỏ bước ${i+1}">✕</button></li>`).join('')||'<li class="tp-order-empty">Chạm các việc bên dưới theo đúng thứ tự.</li>'}</ol>
        <div class="tp-choices">${rest.map(o=>`<button type="button" class="tp-choice" data-action="car:opick" data-task="${tid}" data-step="${sid}" data-v="${x.esc(o.id)}">＋ ${x.esc(o.label)}</button>`).join('')}</div>`;
    }
  }
  return '<p class="ok-note">Bước này chưa có giao diện.</p>';
}

/** What the last checks said, as one card under the step (the toast only says “chưa khớp”): which boxes are off,
 *  the newest hint, the deeper ones the server worked on the player's own numbers (`deep`, optional), older hints
 *  greyed. The server unlocks one hint per wrong check (procedures.public); after a reload only those stay. */
function resultCard(cur,miss,tries,x){
  const hints=(cur.hints||[]).slice(0,tries).filter(Boolean).reverse(),deep=miss?.deep||[];
  if(!miss?.where&&!hints.length&&!deep.length)return '';
  const li=(icon,s,cls='')=>`<li${cls?` class="${cls}"`:''}><span aria-hidden="true">${icon}</span><span>${x.esc(s)}</span></li>`;
  return `<div class="tp-result${miss?' miss':''}" role="status">${miss?.where?`<p class="tp-result-head">✗ ${x.esc(miss.where)}</p>`:''}
    <ul class="tp-tips">${hints.slice(0,1).map(s=>li('💡',s)).join('')}${deep.map(s=>li('🔎',s,'deep')).join('')}${hints.slice(1).map(s=>li('💡',s,'old')).join('')}</ul></div>`;
}

/** The worksheet: the current step big, done steps folded away. */
function worksheet(t,x){
  const p=t.progress||{at:0,total:0,attempts:{}},steps=t.steps||[],cur=steps[p.at];
  const solved=steps.filter(s=>s.state==='solved'),last=solved[solved.length-1];
  const done=solved.length?fold(`✓ ${solved.length} bước đã xong <small>xem lại</small>`,`<ol class="tp-steps">${solved.map(st=>`<li class="tp-step solved"><div class="tp-step-head"><span class="tp-no" aria-hidden="true">✓</span><b>${x.esc(st.title)}</b></div><div class="tp-answer">${solvedText(st,x)}</div>${st.explain?`<p class="tp-explain">${x.esc(st.explain)}</p>`:''}${st.work?.length?`<ol class="tp-ex-work">${st.work.map(w=>`<li>${x.esc(w)}</li>`).join('')}</ol>`:''}</li>`).join('')}</ol>`):'';
  let body='';
  if(cur&&cur.state==='current'){
    const tries=p.attempts[cur.id]||0,hint=resultCard(cur,state(x,t).miss?.[cur.id],tries,x);
    body=`<article class="tp-work" data-step-card="${x.esc(t.id)}:${x.esc(cur.id)}"><header class="tp-work-head"><span class="tp-no" aria-hidden="true">${p.at+1}</span><div class="grow"><small>Bước ${p.at+1}/${p.total}${p.total-p.at-1?` · còn ${p.total-p.at-1} bước sau`:''}${tries>1?` · ${tries} lần kiểm`:''}</small><h3>${x.esc(cur.title)}</h3></div>${cur.tag==='ethic'?'<span class="ok-tag warn">🔒 bảo mật & quy trình</span>':''}</header>
      <p class="tp-prompt">${x.esc(cur.prompt)}</p>${inputView(cur,t,x)}${hint}</article>`;
  }else if(!t.filed)body=`<article class="tp-work done"><header class="tp-work-head"><span class="tp-no" aria-hidden="true">📤</span><div class="grow"><small>Bước cuối</small><h3>Nộp / bàn giao hồ sơ</h3></div></header></article>`;
  const pct=p.total?Math.round(p.at/p.total*100):0;
  return `<section class="tp-sheet"><h3 class="ok-h">🧮 Bảng tính hồ sơ <small>${p.at}/${p.total} bước</small></h3>
    <div class="tp-progress" role="progressbar" aria-label="Tiến độ hồ sơ" aria-valuemin="0" aria-valuemax="${p.total}" aria-valuenow="${p.at}"><i style="width:${pct}%"></i></div>
    ${last&&cur&&last.explain?`<p class="tp-lastok">✓ <b>${x.esc(last.title)}</b> — ${x.esc(last.explain)}</p>`:''}${body}${done}</section>`;
}

/** The desk calculator, folded to one line unless the step asks for numbers or it has results on its tape. */
function calculator(x,cur){
  const hist=x.ui.calc||[],open=x.ui.okFold?.calc??(hist.length>0||['number','fields'].includes(cur?.kind));
  return `<details class="ok-fold tp-calc"${open?' open':''}><summary data-action="car:fold" data-fold="calc">🧮 Máy tính bàn${hist.length?` <small>${hist.length} phép tính</small>`:''}</summary><div class="ok-fold-body">
    <div class="tp-calc-row"><input class="input" id="tp-calc" data-preserve type="text" inputmode="decimal" autocomplete="off" placeholder="vd: 12400 × 8%" aria-label="Phép tính">${x.button('=','car:calc',{},'primary')}</div>
    <ul class="tp-tape">${hist.map(h=>`<li><span>${x.esc(h.expr)}</span><b>${x.esc(h.out)}</b></li>`).join('')||'<li class="tp-tape-help">Dấu chấm là phân cách hàng nghìn; % hiểu là chia 100. Kết quả làm tròn xuống ghi kèm.</li>'}</ul></div></details>`;
}

/** Law notes (lương, bảo hiểm, thuế, hạn nộp) as one fold per group. */
function lawBook(x){
  const gs=x.cc.rules||[];if(!gs.length)return '';
  return `<section class="tp-law"><h3 class="ok-h">📘 Sổ tay quy định</h3>${gs.map(g=>fold(`${x.esc(g.emoji)} ${x.esc(g.group)}`,`<ul class="tp-law-list">${g.lines.map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul>`)).join('')}</section>`;
}
const todayRules=x=>rulesList(x,x.room.data?.today?.rules||[],`Quy định kỳ lương tháng ${x.room.data?.today?.month??''}`);

/** Claims after payday: messages from staff, answered right in the inbox. */
function claimMails(x){
  const cl=x.room.data?.claims||[],ch=x.cc.claim_choices||[];
  return cl.map(c=>({avatar:'<span class="ok-emoji">📨</span>',from:x.esc(c.name),role:'Khiếu nại lương',tone:'bad',
    subject:`Thiếu ${fmtN(c.amount)} xu`,
    body:`<p>${x.esc(c.why)}</p><div class="tp-claim-acts">${ch.map((o,i)=>x.cmd(x.esc(o.label),'tp_claim',{claim:c.id,choice:o.id},i===0?'primary small':'ghost small')).join('')}</div><p class="ok-note">Chưa xử lý tới cuối ngày là ${BOSS} mất tin tưởng.</p>`}));
}

/* ---------------------------------------------------------------- the payroll grid */
const RES={ok:['✓','Chuẩn'],bad:['✗','Có lỗi']};
const gsel=x=>(x.ui.gsel??={});
function rowOf(t,x){const rows=t.rows||[],id=gsel(x)[t.id];return rows.find(r=>r.id===id)||rows.find(r=>!r.reviewed)||rows[0];}
const nameOf=r=>(r.cells||[]).find(c=>c.z==='name')?.v||r.id;
/** Rows of a source paper about one person (all rows when `who` is empty). Tables match the name column;
 * the message list keeps that person's own messages plus the general notes. */
function refRows(p,who){
  if(!who)return p.rows;
  if(p.kind==='table')return p.rows.filter(r=>r[0]===who);
  const last=who.split(' ').pop();
  return p.rows.filter(([k])=>!/^Tin nhắn · /.test(k)||k==='Tin nhắn · '+last);
}
function refList(p,x,who=''){
  const rows=refRows(p,who);
  if(!rows.length)return `<p class="tp-ref-none">Không có dòng nào của <b>${x.esc(who)}</b> trong “${x.esc(p.title)}”.</p>${p.note?`<p class="tp-paper-note">✎ ${x.esc(p.note)}</p>`:''}`;
  if(p.kind!=='table')return `<dl class="tp-kv">${rows.map(([k,v])=>`<dt>${x.esc(k)}</dt><dd>${x.esc(v)}</dd>`).join('')}</dl>`;
  const flag=v=>/Nghỉ việc|chưa duyệt/.test(v)?'bad':'';
  return `<ul class="tp-ref">${rows.map(r=>`<li><b>${x.esc(r[0])}</b>${r.slice(1).map((v,i)=>`<span class="${flag(String(v))}"><small>${x.esc(p.head[i+1]||'')}</small> ${x.esc(v)}</span>`).join('')}</li>`).join('')}</ul>${p.note?`<p class="tp-paper-note">✎ ${x.esc(p.note)}</p>`:''}`;
}
/* ---------------------------------------------------------------- after payday: every cell explained (feedback #71)
 * The server sends, for a paid grid, each cell's state (hit · miss · extra · ok · moot), its right value, the working and
 * the papers / rule cards it comes from. Wrong cells get a coloured outline and a badge in the sheet itself; a tap on any
 * cell opens its working. */
const CELL_STATE={hit:['good','✓ Bắt đúng lỗi'],miss:['bad','✗ Bỏ sót — ô này sai'],extra:['warn','✗ Đánh dấu nhầm — ô này đúng'],ok:['','✓ Ô này đúng'],moot:['','Không tính']};
const BADGE={hit:'✓ bắt đúng',miss:'✗ sót',extra:'✗ nhầm'};
const gcell=x=>(x.ui.gcell??={});
const exId=(t,r,z)=>fid(t,'ex',r.id,z);
/** One cell's explanation: what the draft says, the right value, the working and its source. */
function cellExplain(t,r,z,x,picked=false){
  const e=r.explain?.[z];if(!e)return '';
  const c=(r.cells||[]).find(q=>q.z===z)||{},[tone,said]=CELL_STATE[e.s]||CELL_STATE.ok;
  const vals=`<p class="tp-ex-vals"><span>Bảng nháp: <b>${x.esc(c.v??'')}</b></span>${e.want!=null?`<span>Đúng: <b>${x.esc(e.want)}</b></span>`:''}</p>`;
  return `<div class="tp-ex s-${x.esc(e.s)}${picked?' picked':''}" id="${exId(t,r,z)}"><p class="tp-ex-head"><b>${x.esc(c.k||z)}</b> <span class="ok-tag ${tone}">${said}</span></p>${vals}
    <ol class="tp-ex-work">${(e.steps||[]).map(s=>`<li>${x.esc(s)}</li>`).join('')}</ol>${e.src?.length?`<p class="tp-ex-src">📎 Căn cứ: ${e.src.map(s=>`<span>${x.esc(s)}</span>`).join(' · ')}</p>`:''}</div>`;
}
/** A paid row: every cell tappable, wrong ones outlined and badged, their working listed under the row. */
function paidRow(t,r,x){
  const sel=gcell(x)[t.id],pick=sel?.row===r.id?sel.z:null,ex=r.explain||{};
  const cell=c=>{const s=ex[c.z]?.s||'ok',b=BADGE[s];
    return `<button type="button" class="tp-cell s-${s}${c.z==='name'?' name':''}${pick===c.z?' picked':''}" data-action="car:gcell" data-task="${x.esc(t.id)}" data-row="${x.esc(r.id)}" data-cell="${x.esc(c.z)}" aria-pressed="${pick===c.z}" aria-controls="${exId(t,r,c.z)}"><span class="k">${x.esc(c.k)}</span><span class="v">${x.esc(c.v)}</span>${b?`<span class="tp-badge ${s}">${b}</span>`:''}</button>`;};
  const bad=(r.cells||[]).filter(c=>['miss','extra','hit'].includes(ex[c.z]?.s)).map(c=>c.z);
  const more=pick&&!bad.includes(pick)?cellExplain(t,r,pick,x,true):'';
  const ok=r.result?.ok,[ic,label]=RES[ok?'ok':'bad'];
  const sum=[r.result?.missed?.length?`sót ${r.result.missed.length} ô`:'',r.result?.extra?.length?`đánh dấu nhầm ${r.result.extra.length} ô`:''].filter(Boolean).join(' · ');
  return `<div class="tp-cells-grid">${(r.cells||[]).map(cell).join('')}</div>
    <div class="tp-verdict ${ok?'ok':'bad'}" role="status"><b>${ic} ${label}${sum?` · ${sum}`:''}</b>${bad.length?'':'<p>Dòng này không có lỗi và bạn không đánh dấu nhầm ô nào.</p>'}</div>
    ${bad.map(z=>cellExplain(t,r,z,x,pick===z)).join('')}${more}<p class="tp-ex-tip">👆 Chạm vào ô bất kỳ để xem cách tính.</p>`;
}
function rowCard(t,r,x){
  const live=!r.reviewed&&!t.filed,flags=new Set(r.flags||[]),truth=new Set(r.truth?.z||[]),max=x.cc.max_flags||3;
  if(r.result&&r.explain)return `<section class="tp-person"><header><span class="tp-avatar" aria-hidden="true">${x.esc(nameOf(r).split(' ').pop().slice(0,1))}</span><b>${x.esc(nameOf(r))}</b><small>Dòng ${x.esc(r.id.slice(1))}</small></header>${paidRow(t,r,x)}</section>`;
  const cell=c=>{
    const cls=`${flags.has(c.z)?' flagged':''}${truth.has(c.z)?' truth':''}${c.z==='name'?' name':''}`;
    const inner=`<span class="k">${x.esc(c.k)}</span><span class="v">${x.esc(c.v)}</span>`;
    return live?`<button type="button" class="tp-cell${cls}" data-action="car:flag" data-task="${x.esc(t.id)}" data-row="${x.esc(r.id)}" data-cell="${x.esc(c.z)}" aria-pressed="${flags.has(c.z)}">${inner}</button>`:`<div class="tp-cell${cls}">${inner}</div>`;
  };
  let foot='';
  if(r.result){
    const ok=r.result.ok,[ic,label]=RES[ok?'ok':'bad'];
    foot=`<div class="tp-verdict ${ok?'ok':'bad'}" role="status"><b>${ic} ${label}</b>${(r.truth?.why||[]).map(w=>`<p>${x.esc(w)}</p>`).join('')}${r.result.missed.length?`<p>Sót: ${r.result.missed.map(z=>x.esc(cellName(r,z))).join(', ')}</p>`:''}${r.result.extra.length?`<p>Đánh dấu nhầm: ${r.result.extra.map(z=>x.esc(cellName(r,z))).join(', ')}</p>`:''}${ok&&!(r.truth?.why||[]).length?'<p>Dòng này đúng từ đầu.</p>':''}</div>`;
  }else if(r.reviewed){
    foot=`<p class="tp-done">✓ Đã soát${flags.size?` · ${flags.size} ô cần sửa`:' · không thấy sai'}</p>`;
  }else{
    // First payroll: why each glowing cell is wrong, next to the cells (the header hint stays one short line).
    const co=coachOf(x,t)?.rows?.[r.id],why=co?.z?co.z.filter(z=>!flags.has(z)).map(z=>`<p class="tp-hint">💡 Ô “${x.esc(cellName(r,z))}” sai: ${x.esc(co.why?.[co.z.indexOf(z)]||'đối chiếu hồ sơ gốc')}</p>`).join(''):'';
    foot=`${why}${r.tip?`<p class="tp-hint">💡 ${x.esc(r.tip)}</p>`:''}<div class="tp-row-tools"><small>${flags.size?`🚩 ${flags.size}/${max} ô nghi sai`:'Chạm vào ô sai để đánh dấu'}</small>${r.hinted?'':x.cmd('💡 Gợi ý','tp_hint',{task:t.id,row:r.id},'ghost small')}</div>`;
  }
  return `<section class="tp-person"${r.reviewed||t.filed?'':` data-step-card="${x.esc(t.id)}:${x.esc(r.id)}"`}><header><span class="tp-avatar" aria-hidden="true">${x.esc(nameOf(r).split(' ').pop().slice(0,1))}</span><b>${x.esc(nameOf(r))}</b><small>Dòng ${x.esc(r.id.slice(1))}</small></header>
    <div class="tp-cells-grid">${(r.cells||[]).map(cell).join('')}</div>${foot}</section>`;
}
/** A paid grid: rows with something to look at are open; rows right from the start fold to one line. */
function gridReview(t,x){
  const g=t.grid||{},open=((x.ui.rvRow??={})[t.id]??={}),sel=gcell(x)[t.id];
  const missed=t.rows.reduce((n,r)=>n+(r.result?.missed?.length||0),0),extra=t.rows.reduce((n,r)=>n+(r.result?.extra?.length||0),0);
  const rich=t.rows.some(r=>r.explain);
  const rows=t.rows.map(r=>{
    const res=r.result||{},bad=!res.ok,show=bad||open[r.id]||sel?.row===r.id;
    const head=`<b>${res.ok?'✓':'✗'} ${x.esc(nameOf(r))}</b><small>Dòng ${x.esc(r.id.slice(1))}</small>`;
    if(!rich||!r.explain){   // a grid the server could not regenerate: the reasons as before, with the cells named
      const why=r.truth?.why||[],notes=[];
      if(res.missed?.length)notes.push(`sót: ${res.missed.map(z=>cellName(r,z)).join(', ')}`);
      if(res.extra?.length)notes.push(`đánh dấu nhầm: ${res.extra.map(z=>cellName(r,z)).join(', ')}`);
      return `<li class="tp-rv-row ${res.ok?'ok':'bad'}"><div class="tp-rv-head">${head}</div>${why.length?`<span>${why.map(w=>x.esc(w)).join(' · ')}</span>`:'<span>Dòng này đúng từ đầu.</span>'}${notes.length?`<small>${x.esc(notes.join(' · '))}</small>`:''}</li>`;
    }
    const toggle=bad?'':x.button(show?'Thu gọn':'Xem từng ô','car:rvrow',{task:t.id,row:r.id},'ghost small');
    return `<li class="tp-rv-row ${res.ok?'ok':'bad'}"><div class="tp-rv-head">${head}${toggle}</div>${show?paidRow(t,r,x):r.truth?.z?.length?`<span>✓ Bạn bắt đúng lỗi: ${x.esc(r.truth.z.map(z=>cellName(r,z)).join(', '))}</span>`:'<span>Đúng từ đầu, bạn không đánh dấu nhầm ô nào.</span>'}</li>`;
  }).join('');
  const sum=missed||extra?`Sót ${missed} lỗi · đánh dấu nhầm ${extra} ô.${rich?' Viền đỏ: ô sai bạn bỏ sót. Viền cam: ô đúng bạn đánh dấu nhầm. Cách tính nằm ngay dưới mỗi dòng.':''}`:'Bắt đủ mọi lỗi, không giữ lương oan ô nào.';
  return `<h3 class="ok-h">💸 ${x.esc(t.title)} · ${Number(g.ok)||0}/${Number(g.total)||t.rows.length} dòng chuẩn</h3><p class="tp-rv-sum">${x.esc(sum)}</p><ul class="tp-rv">${rows}</ul>`;
}
/** A finished form: each step with the answer that matched, how many checks it took, the explanation and the working. */
function formReview(t,x){
  const p=t.progress||{attempts:{}};
  const li=(t.steps||[]).map(st=>{
    const miss=Math.max(0,(Number(p.attempts?.[st.id])||1)-1);
    return `<li class="tp-step solved${miss?' retried':''}"><div class="tp-step-head"><span class="tp-no" aria-hidden="true">${miss?'!':'✓'}</span><b>${x.esc(st.title)}</b>${miss?`<span class="ok-tag warn">${miss} lần chưa khớp</span>`:'<span class="ok-tag good">khớp ngay</span>'}</div>
      <div class="tp-answer">${solvedText(st,x)}</div>${st.explain?`<p class="tp-explain">${x.esc(st.explain)}</p>`:''}${st.work?.length?`<ol class="tp-ex-work">${st.work.map(w=>`<li>${x.esc(w)}</li>`).join('')}</ol>`:''}</li>`;
  }).join('');
  return `<h3 class="ok-h">📄 ${x.esc(t.title)} <small>${t.mistakes?`${t.mistakes} lần chưa khớp`:'khớp hết ngay lần đầu'}</small></h3><ol class="tp-steps">${li}</ol>`;
}
/** Finished dossiers still in the save (yesterday and today), newest first. */
const doneTasks=x=>(x.room.tasks||[]).filter(v=>v.status==='completed'&&v.known&&(v.form==='grid'?v.rows?.length:v.steps?.length)).sort((a,b)=>(b.completed_turn||0)-(a.completed_turn||0));
/** The review of the dossier that just closed (or the one picked), and the list to revisit the others. */
function gridRecap(x){
  const done=doneTasks(x);if(!done.length)return '';
  const want=x.ui.tpReview??x.ui.okLast,t=done.find(v=>v.id===want);
  const bad=v=>v.form==='grid'?(v.grid?.ok??0)<(v.grid?.total??0):v.mistakes>0;
  const chips=done.filter(v=>v.id!==t?.id).map(v=>x.button(`${bad(v)?'✗':'✓'} ${x.esc(v.title)} <small>· ngày ${Number(v.day)||''}</small>`,'car:review',{task:v.id},`tp-qchip ${bad(v)?'bad':'ok'}`)).join('');
  const body=t?(t.form==='grid'?gridReview(t,x):formReview(t,x)):'';
  const list=chips?fold(`🗂️ Xem lại hồ sơ đã làm <small>${done.length-(t?1:0)} hồ sơ · cách tính từng ô</small>`,`<div class="tp-rv-pick" role="toolbar" aria-label="Hồ sơ đã làm">${chips}</div>`,!t||(x.ui.okFold?.tpdone??false),'tp-rv-list','tpdone'):'';
  // data-idle-open: a review the player picked stays open on the done screen across re-renders (app.js jobView).
  return `<section class="tp-recap" aria-label="Xem lại hồ sơ"${x.ui.tpReview&&t?' data-idle-open':''}>${body}${list}</section>`;
}
/** The pay period's own rule cards next to the papers (a grid carried past a period change keeps its own rules). */
function periodRules(t,x){
  const p=t.period;if(!p?.rules?.length)return '';
  const today=x.room.data?.today?.month,other=today!=null&&today!==p.month;
  const body=`${other?`<p class="tp-hint">⚠️ Bảng này thuộc kỳ lương tháng ${x.esc(p.month)}: soát theo quy định của kỳ đó, không phải kỳ tháng ${x.esc(today)}.</p>`:''}${rulesList(x,p.rules,`Quy định kỳ lương tháng ${p.month}`)}`;
  return fold(`📋 Quy định kỳ này <small>${p.rules.length} thẻ · mức sàn bảo hiểm, ngày lễ, tạm ứng…</small>`,body,other||(x.ui.okFold?.prules??false),'tp-prules','prules');
}
function gridDoc(t,x){
  const rows=t.rows||[],r=rowOf(t,x),g=t.grid||{};
  const chips=rows.map(v=>{
    const st=v.result?(v.result.ok?'✓':'✗'):v.reviewed?'•':'';
    return x.button(`<span>${x.esc(nameOf(v).split(' ').pop())}</span>${st?`<i>${st}</i>`:''}${(v.flags||[]).length&&!v.result?'<i>🚩</i>':''}`,'car:gpick',{task:t.id,row:v.id},`tp-qchip ${v.id===r?.id?'active':''} ${v.result?(v.result.ok?'ok':'bad'):v.reviewed?'done':''}`);
  }).join('');
  const {idx,html}=paperTabs(t,x,'Hồ sơ gốc');
  const u=state(x,t),who=r&&!t.filed?nameOf(r):'',only=who&&!u.allRef?who:'',p=t.papers[idx];
  const toggle=who?x.button(only?`Xem cả ${p.rows.length} dòng`:`Chỉ xem ${x.esc(who.split(' ').pop())}`,'car:refall',{task:t.id},'ghost small tp-refall'):'';
  const count=t.filed?`<small class="tp-grid-sum">💸 Đã chuyển · ${g.ok}/${g.total} dòng chuẩn</small>`:`<small>${g.reviewed||0}/${g.total||rows.length} đã soát</small>`;
  return `<nav class="tp-queue" aria-label="Bảng lương nháp"><span class="tp-qlabel">👥 Bảng lương</span>${chips}${count}</nav>
    ${r?rowCard(t,r,x):''}
    <section class="tp-tray"><h3 class="ok-h">🗃️ Hồ sơ gốc để đối chiếu${only?` <small>· dòng của ${x.esc(only)}</small>`:''}</h3>${html}<article class="tp-paper"><h4>${x.esc(p.title)}</h4>${refList(p,x,only)}${toggle?`<p class="tp-refbar">${toggle}</p>`:''}</article>${t.filed?'':periodRules(t,x)}</section>`;
}
function gridBar(t,x,gd){
  const r=rowOf(t,x),g=t.grid||{};
  if(!t.filed&&g.reviewed===g.total)return bar(x,t,`Đã soát đủ ${g.total} người.`,gd.cta);
  if(!r||t.filed)return bar(x,t,'Bảng lương đã chuyển.');
  if(r.reviewed)return bar(x,t,`${x.esc(nameOf(r))}: đã soát`,gd.cta);
  const n=(r.flags||[]).length;
  return bar(x,t,`👤 ${x.esc(nameOf(r))}${n?` · 🚩 ${n}`:''}`,gd.cta);
}
const cellSel=(r,z)=>`.tp-cell[data-row="${r.id}"][data-cell="${z}"]`;
const cellName=(r,z)=>(r.cells||[]).find(c=>c.z===z)?.k||z;
/* One person at a time. The first payroll (coach) lights each wrong cell, then “Xong dòng”. */
function gridSteps(t,x){
  const rows=t.rows||[],r=rowOf(t,x),g=t.grid||{};
  if(t.filed||!r||g.reviewed===g.total)return [];
  const who=nameOf(r);
  if(r.reviewed){
    const next=rows.find(v=>!v.reviewed);
    return next?[{ok:null,label:`Soát tiếp: ${nameOf(next)}`,go:{act:'car:gpick',data:{task:t.id,row:next.id},label:'Người tiếp theo ›'}}]:[];
  }
  const flags=r.flags||[],co=coachOf(x,t)?.rows?.[r.id],want=co?.z,out=[];
  if(want){
    const flag=(z,label)=>({cmd:'tp_flag',payload:{task:t.id,row:r.id,cell:z},label});
    for(const z of flags.filter(v=>!want.includes(v))){const go=flag(z,`↩️ Bỏ dấu ô “${x.esc(cellName(r,z))}”`);out.push({ok:false,label:`${who}: ô “${cellName(r,z)}” đúng — bỏ dấu`,go,hintGo:go,pulse:cellSel(r,z)});}
    want.forEach(z=>{if(!flags.includes(z)){const go=flag(z,`🚩 ${x.esc(who.split(' ').pop())}: đánh dấu ô “${x.esc(cellName(r,z))}”`);out.push({ok:null,label:`${who}: ô “${cellName(r,z)}” sai`,go,hintGo:go,pulse:cellSel(r,z)});}});
  }
  const n=flags.length;
  out.push({ok:null,label:want?`${who}: xong dòng`:`${who}: so từng ô rồi xong dòng`,go:{cmd:'tp_row',payload:{task:t.id,row:r.id},label:n?`✓ Xong dòng · ${n} ô cần sửa`:'✓ Xong dòng · không thấy sai'},
    ...(want?{}:{hintGo:goto(x,t,'.tp-person')})});
  return out;
}

/* ---------------------------------------------------------------- a form (tờ khai) done step by step */
function formDoc(t,x){
  const {idx,html}=paperTabs(t,x,'Giấy tờ');
  return `${worksheet(t,x)}<section class="tp-tray"><h3 class="ok-h">🗃️ Giấy tờ khách gửi <small>${t.papers.length} tờ</small></h3>${html}${paperView(t.papers[idx],x)}</section>${calculator(x,(t.steps||[])[(t.progress||{}).at||0])}`;
}
function formBar(t,x,gd){
  const p=t.progress||{},cur=(t.steps||[])[p.at];
  if(cur&&cur.state==='current')return bar(x,t,'',gd.cta);
  if(!t.filed)return bar(x,t,'Hồ sơ đã khớp hết — nộp cho khách.',gd.cta);
  return bar(x,t,'Đã nộp hồ sơ.');
}
/* A form step by step. The first dossier (coach) lights the right choice / the next item, or fills the cells. */
function formSteps(t,x){
  const p=t.progress||{},cur=(t.steps||[])[p.at];
  if(!cur||cur.state!=='current')return [];
  const u=state(x,t),co=coachOf(x,t),key=co&&co.step===cur.id?co.key:undefined;
  const label=`Bước ${p.at+1}/${p.total}: ${cur.title}`,check={act:'car:check',data:{task:t.id,step:cur.id,kind:cur.kind},label:'✔ Kiểm tra'};
  const lit=(sel,go)=>[{ok:null,label,go,pulse:sel}];
  if(key===undefined)return [{ok:null,label,go:check,hintGo:goto(x,t,'.tp-work')}];
  const opt=v=>`.tp-choice[data-step="${cur.id}"][data-v="${v}"]`;
  const d={task:t.id,step:cur.id},name=(list,v)=>x.esc(lab(list,v));
  if(cur.kind==='choice'&&u.sel[cur.id]!==key)return lit(opt(key),{act:'car:pick',data:{...d,v:key},label:`👉 ${name(cur.options,key)}`});
  if(cur.kind==='multi'){
    const on=u.multi[cur.id]||[],v=on.find(q=>!key.includes(q))??key.find(q=>!on.includes(q));
    if(v!==undefined)return lit(opt(v),{act:'car:toggle',data:{...d,v},label:`${on.includes(v)?'↩️ Bỏ chọn':'☑️ Chọn'} “${name(cur.options,v)}”`});
  }
  if(cur.kind==='order'){
    const picked=u.order[cur.id]||[],bad=picked.findIndex((v,i)=>v!==key[i]);
    if(bad>=0)return lit(`.tp-order button[data-action="car:unpick"][data-i="${bad}"]`,{act:'car:unpick',data:{...d,i:bad},label:`↩️ Bỏ “${name(cur.items,picked[bad])}”`});
    if(picked.length<key.length)return lit(`.tp-choice[data-action="car:opick"][data-v="${key[picked.length]}"]`,{act:'car:opick',data:{...d,v:key[picked.length]},label:`＋ ${name(cur.items,key[picked.length])}`});
  }
  if(['number','fields','match'].includes(cur.kind)&&!u.coached?.[cur.id])
    return [{ok:null,label,go:{act:'car:coach',data:{task:t.id,step:cur.id},label:'✍️ Điền theo giấy tờ'}}];
  return [{ok:null,label,go:check}];
}
/** {steps, final} for the header hint and the bottom button. */
function guideFor(t,x){
  const grid=t.form==='grid';
  if(!t.known)return {steps:[{ok:null,label:grid?'Nhận bảng lương nháp':'Nhận hồ sơ, đọc yêu cầu',go:{cmd:'ask',payload:{task:t.id},label:grid?'📥 Nhận bảng lương nháp':'📥 Nhận hồ sơ & đọc yêu cầu'}}]};
  if(grid){
    const g=t.grid||{};
    return {steps:gridSteps(t,x),final:!t.filed&&g.reviewed===g.total?{label:`💸 Chuyển lương ${g.total} người`,go:{cmd:'tp_pay',payload:{task:t.id},confirm:'Chuyển lương theo bảng đã soát? Ô đánh dấu sẽ được sửa trước khi chuyển; ô sót thì chuyển nguyên như bảng nháp.'}}:null};
  }
  const steps=formSteps(t,x);
  return {steps,final:!steps.length&&!t.filed?{label:'📤 Nộp / bàn giao hồ sơ',go:{cmd:'tp_file',payload:{task:t.id},confirm:'Nộp hồ sơ này? Sau khi nộp không sửa được nữa; thưởng hồ sơ phụ thuộc số lần chưa khớp và hạn nộp.'}}:null};
}

/* ---------------------------------------------------------------- care: the filing calendar, colleagues, the track */
const FILE_TAG={filed:['✓ Đã nộp','filed'],late_filed:['Nộp muộn','late_filed'],boss:['Chị Hồng nộp thay','boss'],late:['Quá hạn','late'],due:['Hạn hôm nay','due'],locked:['Chưa mở','locked']};
function filingPlan(x){
  const p=x.room.data?.care?.plan;if(!p||p.kind!=='filings')return '';
  const rows=p.items.map(f=>{const [label,tone]=FILE_TAG[f.state]||[f.rel,'todo'];
    const note=[`${f.who} · hạn ${f.date} (${f.rel})`,f.state==='late'||f.fee?`đã chịu ${f.fee} xu chậm nộp`:'',f.why].filter(Boolean).join(' · ');
    const act=f.can&&x.room.open?x.confirmCmd(`📨 Nộp · ${f.minutes} phút`,'tp_declare',{filing:f.id},`Ký số và nộp “${f.name}” cho ${f.who}? Mất ${f.minutes} phút.`,'primary small'):'';
    return {emoji:f.emoji,title:f.name,note,tag:{label,tone},act,tone:f.state==='late'?'bad':f.state==='due'?'warn':''};});
  return planCard(x,{title:`📆 ${p.title}`,sub:`${p.done}/${p.total} đã nộp`,rows,
    foot:`Quá hạn mỗi ngày ${p.fee} xu tiền chậm nộp (Minh Bạch chịu thay khách). Ngày ${x.esc(p.payday)}: trả lương cả xưởng.`});
}
const care=(x,t)=>({plan:filingPlan(x),people:mateCards(x,{prefix:'tp_',t}),track:trackFold(x,{prefix:'tp_',career:'tax_payroll'})});
const careBadge=x=>{const c=x.room.data?.care;return (c?.asked?1:0)+((c?.plan?.items)||[]).filter(f=>f.can&&(f.state==='due'||f.state==='late')).length;};

/* ---------------------------------------------------------------- the office desktop */
const strip=(x,t)=>statusStrip(x,t,{boss:BOSS,op:'tp_overtime'});
/** Office shut: every tp_ command takes office time (claims: only “pay now”); car:check / car:flag send one. */
const SHUT={prefix:'tp_',acts:['check','flag'],free:(op,tag)=>op==='tp_claim'&&!tag.includes('pay_now')};
function currentMail(t,x){
  const label=x.cc.labels?.[t.form]||'Hồ sơ',due=dueOf(t,x),left=typeof t.due_turn==='number'?t.due_turn-(x.room.turn||0):null;
  const chips=[`<span class="ok-tag">${x.esc(label)}</span>`,
    !due&&left!==null&&t.known?`<span class="ok-tag ${left<0?'bad':left<8?'warn':''}">${left>=0?`⏳ Hạn nội bộ: còn ${left} lượt`:'⌛ Quá hạn nội bộ'}</span>`:'',
    t.bonus&&t.form!=='grid'?`<span class="ok-tag good">🎁 Thưởng ${x.money(t.pay??t.bonus)}</span>`:'',
    t.mistakes?`<span class="ok-tag bad">✗ ${t.mistakes} lần chưa khớp</span>`:''].join('');
  const help=!t.known&&t.form==='grid'?'<p class="ok-note">Sót lỗi thì người lao động nhận sai lương — hôm sau sẽ có khiếu nại.</p>':'';
  return `<p class="ok-quote">“${x.esc(t.opening)}”</p>${t.brief?`<p class="ok-brief">🎯 ${x.esc(t.brief)}</p>`:''}<div class="ok-chips">${chips}</div>${help}`;
}
function nextText(t){
  if(t.form==='grid'){
    if(!t.known)return 'Nhận bảng lương nháp';
    const left=(t.rows||[]).filter(r=>!r.reviewed).length;
    return left?`Soát bảng lương: còn ${left}/${(t.rows||[]).length} người`:'Chuyển lương trước giờ hạn';
  }
  if(!t.known)return 'Nhận hồ sơ, đọc yêu cầu';
  const p=t.progress;
  if(p&&p.at<p.total)return `Bước ${p.at+1}/${p.total}: ${t.steps[p.at].title}`;
  return 'Nộp / bàn giao hồ sơ';
}

export default {
  id:'tax_payroll',
  css:true,
  next(t,x){
    if(x&&t.gen&&shut(x))return `Văn phòng đóng cửa lúc ${x.room.data.office.limit_time} — khép ca`;
    try{const n=x&&pending(guideFor(t,x).steps);if(n)return stepLine(n);}catch{/* the fixed lines below */}
    return nextText(t);
  },
  job(t,x){
    const grid=t.form==='grid',claims=(x.room.data?.claims||[]).length,fresh=(x.room.data?.today?.rules||[]).filter(r=>r.new).length;
    x.ui.lastGrid=grid?t.id:null;x.ui.tpReview=null;   // the review after this dossier closes shows this one
    const unread=openTasks(x).filter(v=>!v.known).length+claims+careBadge(x);
    const tabs=[{id:'inbox',icon:'📥',label:'Hộp thư',badge:unread||'',tone:claims?'bad':''},{id:'doc',icon:'📂',label:'Hồ sơ'},{id:'rules',icon:'📋',label:'Quy định',badge:fresh||'',tone:'warn'}];
    const inbox=inboxPane(x,{tasks:taskMails(x,t,currentMail(t,x)),other:[...claimMails(x),...dayMails(x,{boss:BOSS,key:`${t.id}:${t.known?1:0}`})],...care(x,t)});
    const rules=todayRules(x)+lawBook(x);
    const gd=guideFor(t,x),g=guideOf(x,t,gd.steps,gd.final);
    if(!t.known)return plain(desk(x,t,{cls:'tp',tabs,strip:strip(x,t),hint:g.hint,panes:{inbox:shutWork(x,inbox,SHUT),rules,
      doc:`<p class="ok-empty"><span aria-hidden="true">✉️</span><b>${x.esc(t.title)}</b><span>${grid?'Bảng lương nháp còn nằm trên bàn chị Hồng.':'Hồ sơ còn trong phong bì.'}</span></p>`},
      bar:bar(x,t,'',g.cta,true)}));
    // Office shut (a timed dossier): its work is drawn disabled, the hint steps aside and the bar closes the day.
    const off=shut(x)&&Boolean(t.gen),hint=off?'':g.hint,work=html=>shutWork(x,html,SHUT),doc=html=>off?work(html):html;
    if(grid)return plain(desk(x,t,{cls:'tp',tabs,strip:strip(x,t),hint,panes:{inbox:work(inbox),rules,doc:doc(gridDoc(t,x))},bar:off?shutBar(x,t):gridBar(t,x,g)}));
    return plain(desk(x,t,{cls:'tp',tabs,strip:strip(x,t),hint,panes:{inbox:work(inbox),rules,doc:doc(formDoc(t,x))},bar:off?shutBar(x,t):formBar(t,x,g)}));
  },
  idle(x){
    const d=x.room.data||{};if(!d.office)return '';
    return plain(shutWork(x,idleDesk(x,{cls:'tp',strip:strip(x,null),recap:gridRecap(x),tasks:taskMails(x,null),other:[...claimMails(x),...dayMails(x,{boss:BOSS})],rules:todayRules(x),...care(x,null)}),SHUT));
  },
  summary(data,x){
    if(!data||typeof data!=='object')return '';
    const o=data.office||{},rows=[];
    const row=(k,v)=>rows.push(`<div class="kv-row"><span>${x.esc(k)}</span><b>${x.esc(v)}</b></div>`);
    if(data.mod?.name)row('Hôm nay',`${data.mod.emoji||''} ${data.mod.name}`);
    if(data.grids)row('Bảng lương đã chuyển',`${data.grids} (${data.clean||0} bảng sạch lỗi)`);
    if(data.claims_new)row('Người sẽ khiếu nại sáng mai',String(data.claims_new));
    if(data.claims_ignored)row('Khiếu nại bị bỏ quên',String(data.claims_ignored));
    if(o.late)row('Việc nộp trễ hạn',String(o.late));
    if(o.fines)row('Bị trừ tiền',`${o.fines} xu`);
    if(o.overtime)row('Tăng ca','Có (mai vào muộn 30 phút)');
    if(o.carried)row('Việc dở để sáng mai',`${o.carried} (hạn 10:00)`);
    const ch=Number(o.trust_change)||0;
    const trust=o.trust_label?`<p class="tp-sum-trust">👩‍💼 Chị Hồng: <b>${x.esc(o.trust_label)}</b> (${o.trust}/100${ch?`, ${ch>0?'+':''}${ch} hôm nay`:''})</p>`:'';
    const insp=data.inspect?`<p class="tp-sum-audit ${data.inspect.ok?'ok':'bad'}">${data.inspect.ok?'🏅':'🔍'} ${x.esc(data.inspect.text||'')}</p>`:'';
    for(const f of Array.isArray(data.filings)?data.filings:[])row(f.boss?'Chị Hồng nộp thay':'Tờ khai quá hạn',`${f.name}${f.fee?` · −${f.fee} xu chậm nộp`:''}`);
    const life=careSummary(data.care,x);
    if(!rows.length&&!trust&&!insp&&!life)return '';
    return summaryCard(x,data,{cls:'tp-sum',title:'🧮 Bàn lương hôm nay',brief:data.grids?`${data.grids} bảng lương đã chuyển`:'',
      extra:[data.claims_new?`🙋 <b>${Number(data.claims_new)} người</b> sẽ tới khiếu nại sáng mai`:''],
      body:`${insp}${trust}${rows.length?`<div class="kv">${rows.join('')}</div>`:''}${life?`<h4 class="section-title">🧭 Đời sống văn phòng</h4><div class="kv">${life}</div>`:''}`});
  },
  tick(root){keepBarAboveFooter(root);},
  actions:{
    tab:switchTab,
    fold:foldToggle,
    goto:gotoAction,
    /** First dossier: type the key into the step's cells (inputs keep their typed value across renders). */
    coach(d,el,x){
      const t=x.room.tasks.find(q=>q.id===d.task),st=t?.steps?.find(s=>s.id===d.step),co=t&&x.room.data?.coach?.[t.id];
      if(!st||co?.step!==st.id)return;
      const put=(id,v)=>{const i=document.getElementById(id);if(i)i.value=String(v);};
      if(st.kind==='number')put(fid(t,st.id),co.key);
      else for(const [k,v] of Object.entries(co.key||{}))put(fid(t,st.id,k),v);
      (state(x,t).coached??={})[st.id]=true;x.render();
    },
    gpick(d,el,x){gsel(x)[d.task]=d.row;x.render();document.querySelector('.career-job.tp .tp-queue')?.scrollIntoView({block:'nearest'});},
    /** A paid grid: tap a cell → its working opens under the row (tap again to close an extra one). */
    gcell(d,el,x){
      const g=gcell(x),cur=g[d.task];
      g[d.task]=cur&&cur.row===d.row&&cur.z===d.cell?null:{row:d.row,z:d.cell};
      x.render();
      const box=document.getElementById(fid({id:d.task},'ex',d.row,d.cell));
      if(box&&g[d.task])box.scrollIntoView({block:'nearest'});
    },
    rvrow(d,el,x){const o=((x.ui.rvRow??={})[d.task]??={});o[d.row]=!o[d.row];if(!o[d.row]&&gcell(x)[d.task]?.row===d.row)gcell(x)[d.task]=null;x.render();},
    review(d,el,x){x.ui.tpReview=d.task;x.render();document.querySelector('.career-job.tp .tp-recap')?.scrollIntoView({block:'start'});},
    async flag(d,el,x){
      const on=el.getAttribute('aria-pressed')==='true';
      el.classList.toggle('flagged',!on);el.setAttribute('aria-pressed',String(!on));
      const r=await x.send('tp_flag',{task:d.task,row:d.row,cell:d.cell});
      if(!r){el.classList.toggle('flagged',on);el.setAttribute('aria-pressed',String(on));}
    },
    paper(d,el,x){const u=x.ui[d.task];if(u){u.paper=Number(d.i)||0;x.render();}},
    refall(d,el,x){const u=x.ui[d.task];if(u){u.allRef=!u.allRef;x.render();}},
    pick(d,el,x){const u=x.ui[d.task];if(u){u.sel[d.step]=d.v;x.render();}},
    toggle(d,el,x){const u=x.ui[d.task];if(!u)return;const a=u.multi[d.step]||[];u.multi[d.step]=a.includes(d.v)?a.filter(v=>v!==d.v):[...a,d.v];x.render();},
    opick(d,el,x){const u=x.ui[d.task];if(!u)return;const a=u.order[d.step]||[];if(!a.includes(d.v))u.order[d.step]=[...a,d.v];x.render();},
    unpick(d,el,x){const u=x.ui[d.task];if(!u)return;const a=[...(u.order[d.step]||[])];a.splice(Number(d.i),1);u.order[d.step]=a;x.render();},
    calc(d,el,x){
      const input=document.getElementById('tp-calc');const expr=(input?.value||'').trim();if(!expr)return;
      let out;try{const v=calc(expr);out=Number.isInteger(v)?fmtN(v):`${v.toLocaleString('vi-VN',{maximumFractionDigits:4,useGrouping:false})} (↓ ${fmtN(Math.floor(v))})`;}catch{out='Phép tính chưa hợp lệ';}
      x.ui.calc=[{expr,out},...(x.ui.calc||[])].slice(0,5);x.render();
    },
    async check(d,el,x){
      const t=x.room.tasks.find(q=>q.id===d.task);if(!t?.steps)return;
      const st=t.steps.find(s=>s.id===d.step),u=state(x,t);if(!st)return;
      const val=id=>document.getElementById(id)?.value??'';
      let answer=null,bad=null;   // bad: the first empty or malformed box, named in the toast and focused
      if(st.kind==='choice')answer=u.sel[st.id]||null;
      else if(st.kind==='multi')answer=(u.multi[st.id]||[]).length?[...u.multi[st.id]]:null;
      else if(st.kind==='order')answer=(u.order[st.id]||[]).length===st.items.length?[...u.order[st.id]]:null;
      else if(st.kind==='number'){answer=parseIntVN(val(fid(t,st.id)));if(answer===null)bad={id:fid(t,st.id),label:'Đáp số',empty:!val(fid(t,st.id)).trim()};}
      else if(st.kind==='match'){answer={};for(const l of st.left){const v=val(fid(t,st.id,l.id));if(!v){answer=null;break;}answer[l.id]=v;}}
      else if(st.kind==='fields'){answer={};for(const f of st.fields){const raw=val(fid(t,st.id,f.id));const v=f.options?raw:parseIntVN(raw);if(v===null||v===''){answer=null;bad={id:fid(t,st.id,f.id),label:f.label,empty:!String(raw).trim(),select:!!f.options};break;}answer[f.id]=v;}}
      if(answer===null&&bad){   // say which box, and take the player there (it is often off screen on a phone)
        x.toast(bad.select?`Chọn “${bad.label}” trước nhé.`:bad.empty?`Còn trống ô “${bad.label}”. Không có thì ghi 0 nhé.`:`Ô “${bad.label}” chỉ ghi số, vd 14250.`,true);
        const box=document.getElementById(bad.id);if(box){box.classList.add('tp-bad');box.addEventListener('input',()=>box.classList.remove('tp-bad'),{once:true});box.scrollIntoView({block:'center'});box.focus({preventScroll:true});}
        return;}
      if(answer===null){x.toast(st.kind==='choice'?'Chạm chọn một đáp án trước nhé.':st.kind==='multi'?'Chạm chọn ít nhất một ô trước nhé.':st.kind==='order'?'Chạm đủ các việc theo thứ tự trước nhé.':st.kind==='match'?'Chọn đủ từng dòng trước nhé.':'Điền đủ các ô số trước khi kiểm tra nhé.',true);return;}
      const r=await x.send('tp_submit',{task:t.id,step:st.id,answer},{quiet:true});
      if(!r)return;
      // A wrong check names the boxes that do not match (never their values); they stay marked until the next check.
      // A one-number step has no box names in the reply: its only box ('') is the one off. The toast stays one short
      // line (`toast`, or the same line built here for an older server); the details go to the card under the step.
      const wrong=r.correct===false;
      x.toast(wrong?(r.toast||shortMiss(st,r)):r.message,wrong?true:r.celebrate?'good':false);
      (u.miss??={})[st.id]=wrong?{bad:st.kind==='number'?['']:Array.isArray(r.bad)?r.bad:[],where:String(r.where||''),
        deep:Array.isArray(r.deep)?r.deep.filter(s=>typeof s==='string'):[]}:null;
      x.render();
      if(!wrong)return;
      document.querySelectorAll('.career-job.tp .tp-field.bad details.tp-how').forEach(d=>{d.open=true;});   // once: the player may fold it again
      document.querySelector('.career-job.tp .tp-result')?.scrollIntoView({block:'center'});
    },
  },
};
