/** Dịch vụ Thuế & Tiền lương Minh Bạch — the payroll desk inside the shared office desktop (office_kit.js):
 *  📥 Hộp thư (việc chị Hồng giao, khiếu nại lương), 📂 Hồ sơ (bảng lương nháp soát từng người, hoặc
 *  tờ khai làm từng bước với giấy tờ gốc và máy tính bàn), 📋 Quy định (quy định kỳ lương + sổ tay luật),
 *  and a sticky bar with the next step and the main action. */
import {statusStrip,taskMails,dayMails,inboxPane,rulesList,desk,bar,switchTab,keepBarAboveFooter,fold,idleDesk,dueOf,openTasks} from './office_kit.js';

const BOSS='Chị Hồng';
const fmtN=n=>Number(n).toLocaleString('vi-VN');
const lab=(list,id)=>list?.find(o=>o.id===id)?.label??id;
const state=(x,t)=>x.ui[t.id]??={paper:0,sel:{},multi:{},order:{}};
const fid=(t,...p)=>['tp',t.id,...p].join('-').replace(/[^a-zA-Z0-9_-]/g,'_');
const NUMERIC=/^[−-]?[\d.]+( xu)?$/;

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

function inputView(st,t,x){
  const u=state(x,t),sid=x.esc(st.id),tid=x.esc(t.id);
  switch(st.kind){
    case'choice':return `<div class="tp-choices">${st.options.map(o=>`<button type="button" class="tp-choice ${u.sel[st.id]===o.id?'on':''}" data-action="car:pick" data-task="${tid}" data-step="${sid}" data-v="${x.esc(o.id)}" aria-pressed="${u.sel[st.id]===o.id}"><span class="tp-box radio" aria-hidden="true">${u.sel[st.id]===o.id?'●':''}</span>${x.esc(o.label)}</button>`).join('')}</div>`;
    case'multi':{const on=u.multi[st.id]||[];return `<div class="tp-choices">${st.options.map(o=>`<button type="button" class="tp-choice check ${on.includes(o.id)?'on':''}" data-action="car:toggle" data-task="${tid}" data-step="${sid}" data-v="${x.esc(o.id)}" aria-pressed="${on.includes(o.id)}"><span class="tp-box" aria-hidden="true">${on.includes(o.id)?'✓':''}</span>${x.esc(o.label)}</button>`).join('')}</div>`;}
    case'number':return `<label class="tp-cell-row"><span>Đáp số (xu)</span><input class="input tp-num" id="${fid(t,st.id)}" data-preserve type="text" inputmode="numeric" autocomplete="off" placeholder="0"></label>`;
    case'fields':return `<table class="tp-cells edit"><tbody>${st.fields.map(f=>`<tr><th scope="row"><label for="${fid(t,st.id,f.id)}">${x.esc(f.label)}</label></th><td>${f.options?`<select id="${fid(t,st.id,f.id)}" data-preserve><option value="">Chọn…</option>${f.options.map(o=>`<option value="${x.esc(o.id)}">${x.esc(o.label)}</option>`).join('')}</select>`:`<input class="input tp-num" id="${fid(t,st.id,f.id)}" data-preserve type="text" inputmode="numeric" autocomplete="off" placeholder="0">`}</td></tr>`).join('')}</tbody></table>`;
    case'match':return `<div class="tp-match">${st.left.map(l=>`<label class="tp-cell-row"><span>${x.esc(l.label)}</span><select id="${fid(t,st.id,l.id)}" data-preserve><option value="">Chọn…</option>${st.right.map(r=>`<option value="${x.esc(r.id)}">${x.esc(r.label)}</option>`).join('')}</select></label>`).join('')}</div>`;
    case'order':{
      const picked=u.order[st.id]||[],rest=st.items.filter(o=>!picked.includes(o.id));
      return `<ol class="tp-order">${picked.map((id,i)=>`<li><span class="tp-no">${i+1}</span><span class="grow">${x.esc(lab(st.items,id))}</span><button type="button" class="btn small ghost" data-action="car:unpick" data-task="${tid}" data-step="${sid}" data-i="${i}" aria-label="Bỏ bước ${i+1}">✕</button></li>`).join('')||'<li class="tp-order-empty">Chạm các việc bên dưới theo đúng thứ tự.</li>'}</ol>
        <div class="tp-choices">${rest.map(o=>`<button type="button" class="tp-choice" data-action="car:opick" data-task="${tid}" data-step="${sid}" data-v="${x.esc(o.id)}">＋ ${x.esc(o.label)}</button>`).join('')}</div>`;
    }
  }
  return '<p class="ok-note">Bước này chưa có giao diện.</p>';
}

/** The worksheet: the current step big, done steps folded away. */
function worksheet(t,x){
  const p=t.progress||{at:0,total:0,attempts:{}},steps=t.steps||[],cur=steps[p.at];
  const solved=steps.filter(s=>s.state==='solved'),last=solved[solved.length-1];
  const done=solved.length?fold(`✓ ${solved.length} bước đã xong <small>xem lại</small>`,`<ol class="tp-steps">${solved.map(st=>`<li class="tp-step solved"><div class="tp-step-head"><span class="tp-no" aria-hidden="true">✓</span><b>${x.esc(st.title)}</b></div><div class="tp-answer">${solvedText(st,x)}</div>${st.explain?`<p class="tp-explain">${x.esc(st.explain)}</p>`:''}</li>`).join('')}</ol>`):'';
  let body='';
  if(cur&&cur.state==='current'){
    const tries=p.attempts[cur.id]||0;
    const hint=tries>0?`<p class="tp-hint">💡 ${x.esc(cur.hints[Math.min(cur.hints.length,tries)-1])}</p>`:'';
    body=`<article class="tp-work"><header class="tp-work-head"><span class="tp-no" aria-hidden="true">${p.at+1}</span><div class="grow"><small>Bước ${p.at+1}/${p.total}${p.total-p.at-1?` · còn ${p.total-p.at-1} bước sau`:''}${tries>1?` · ${tries} lần kiểm`:''}</small><h3>${x.esc(cur.title)}</h3></div>${cur.tag==='ethic'?'<span class="ok-tag warn">🔒 bảo mật & quy trình</span>':''}</header>
      <p class="tp-prompt">${x.esc(cur.prompt)}</p>${inputView(cur,t,x)}${hint}</article>`;
  }else if(!t.filed)body=`<article class="tp-work done"><header class="tp-work-head"><span class="tp-no" aria-hidden="true">📤</span><div class="grow"><small>Bước cuối</small><h3>Nộp / bàn giao hồ sơ</h3></div></header></article>`;
  const pct=p.total?Math.round(p.at/p.total*100):0;
  return `<section class="tp-sheet"><h3 class="ok-h">🧮 Bảng tính hồ sơ <small>${p.at}/${p.total} bước</small></h3>
    <div class="tp-progress" role="progressbar" aria-label="Tiến độ hồ sơ" aria-valuemin="0" aria-valuemax="${p.total}" aria-valuenow="${p.at}"><i style="width:${pct}%"></i></div>
    ${last&&cur&&last.explain?`<p class="tp-lastok">✓ <b>${x.esc(last.title)}</b> — ${x.esc(last.explain)}</p>`:''}${body}${done}</section>`;
}

function calculator(x){
  const hist=x.ui.calc||[];
  return `<section class="tp-calc" aria-label="Máy tính bàn"><h3 class="ok-h">🧮 Máy tính bàn</h3>
    <div class="tp-calc-row"><input class="input" id="tp-calc" data-preserve type="text" inputmode="decimal" autocomplete="off" placeholder="vd: 12.400 × 8%" aria-label="Phép tính">${x.button('=','car:calc',{},'primary')}</div>
    <ul class="tp-tape">${hist.map(h=>`<li><span>${x.esc(h.expr)}</span><b>${x.esc(h.out)}</b></li>`).join('')||'<li class="tp-tape-help">Dấu chấm là phân cách hàng nghìn; % hiểu là chia 100. Kết quả làm tròn xuống ghi kèm.</li>'}</ul></section>`;
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
function refList(p,x){
  if(p.kind!=='table')return `<dl class="tp-kv">${p.rows.map(([k,v])=>`<dt>${x.esc(k)}</dt><dd>${x.esc(v)}</dd>`).join('')}</dl>`;
  const flag=v=>/Nghỉ việc|chưa duyệt/.test(v)?'bad':'';
  return `<ul class="tp-ref">${p.rows.map(r=>`<li><b>${x.esc(r[0])}</b>${r.slice(1).map((v,i)=>`<span class="${flag(String(v))}"><small>${x.esc(p.head[i+1]||'')}</small> ${x.esc(v)}</span>`).join('')}</li>`).join('')}</ul>${p.note?`<p class="tp-paper-note">✎ ${x.esc(p.note)}</p>`:''}`;
}
function rowCard(t,r,x){
  const live=!r.reviewed&&!t.filed,flags=new Set(r.flags||[]),truth=new Set(r.truth?.z||[]),max=x.cc.max_flags||3;
  const cell=c=>{
    const cls=`${flags.has(c.z)?' flagged':''}${truth.has(c.z)?' truth':''}${c.z==='name'?' name':''}`;
    const inner=`<span class="k">${x.esc(c.k)}</span><span class="v">${x.esc(c.v)}</span>`;
    return live?`<button type="button" class="tp-cell${cls}" data-action="car:flag" data-task="${x.esc(t.id)}" data-row="${x.esc(r.id)}" data-cell="${x.esc(c.z)}" aria-pressed="${flags.has(c.z)}">${inner}</button>`:`<div class="tp-cell${cls}">${inner}</div>`;
  };
  let foot='';
  if(r.result){
    const ok=r.result.ok,[ic,label]=RES[ok?'ok':'bad'];
    foot=`<div class="tp-verdict ${ok?'ok':'bad'}" role="status"><b>${ic} ${label}</b>${(r.truth?.why||[]).map(w=>`<p>${x.esc(w)}</p>`).join('')}${r.result.missed.length?`<p>Sót: ${r.result.missed.length} ô</p>`:''}${r.result.extra.length?`<p>Đánh dấu nhầm: ${r.result.extra.length} ô</p>`:''}${ok&&!(r.truth?.why||[]).length?'<p>Dòng này đúng từ đầu.</p>':''}</div>`;
  }else if(r.reviewed){
    foot=`<p class="tp-done">✓ Đã soát${flags.size?` · ${flags.size} ô cần sửa`:' · không thấy sai'}</p>`;
  }else{
    foot=`${r.tip?`<p class="tp-hint">💡 ${x.esc(r.tip)}</p>`:''}<div class="tp-row-tools"><small>${flags.size?`🚩 ${flags.size}/${max} ô nghi sai`:'Chạm vào ô sai để đánh dấu'}</small>${r.hinted?'':x.cmd('💡 Gợi ý','tp_hint',{task:t.id,row:r.id},'ghost small')}</div>`;
  }
  return `<section class="tp-person"><header><span class="tp-avatar" aria-hidden="true">${x.esc(nameOf(r).split(' ').pop().slice(0,1))}</span><b>${x.esc(nameOf(r))}</b><small>Dòng ${x.esc(r.id.slice(1))}</small></header>
    <div class="tp-cells-grid">${(r.cells||[]).map(cell).join('')}</div>${foot}</section>`;
}
function gridRecap(x){
  const t=(x.room.tasks||[]).find(v=>v.id===x.ui.lastGrid);
  if(!t||!t.filed||!t.rows)return '';
  const g=t.grid||{};
  const li=t.rows.map(r=>{
    const res=r.result||{},why=r.truth?.why||[],notes=[];
    if(res.missed?.length)notes.push(`sót ${res.missed.length} ô`);
    if(res.extra?.length)notes.push(`đánh dấu nhầm ${res.extra.length} ô`);
    return `<li class="${res.ok?'ok':'bad'}"><b>${res.ok?'✓':'✗'} ${x.esc(nameOf(r))}</b>${why.length?`<span>${why.map(w=>x.esc(w)).join(' · ')}</span>`:'<span>Dòng này đúng từ đầu.</span>'}${notes.length?`<small>${notes.join(' · ')}</small>`:''}</li>`;
  }).join('');
  return `<section class="tp-recap" role="status"><h3 class="ok-h">💸 Bảng lương vừa chuyển · ${Number(g.ok)||0}/${Number(g.total)||t.rows.length} dòng chuẩn</h3><ul>${li}</ul></section>`;
}
function gridDoc(t,x){
  const rows=t.rows||[],r=rowOf(t,x),g=t.grid||{};
  const chips=rows.map(v=>{
    const st=v.result?(v.result.ok?'✓':'✗'):v.reviewed?'•':'';
    return x.button(`<span>${x.esc(nameOf(v).split(' ').pop())}</span>${st?`<i>${st}</i>`:''}${(v.flags||[]).length&&!v.result?'<i>🚩</i>':''}`,'car:gpick',{task:t.id,row:v.id},`tp-qchip ${v.id===r?.id?'active':''} ${v.result?(v.result.ok?'ok':'bad'):v.reviewed?'done':''}`);
  }).join('');
  const {idx,html}=paperTabs(t,x,'Hồ sơ gốc');
  const count=t.filed?`<small class="tp-grid-sum">💸 Đã chuyển · ${g.ok}/${g.total} dòng chuẩn</small>`:`<small>${g.reviewed||0}/${g.total||rows.length} đã soát</small>`;
  return `<nav class="tp-queue" aria-label="Bảng lương nháp"><span class="tp-qlabel">👥 Bảng lương</span>${chips}${count}</nav>
    ${r?rowCard(t,r,x):''}
    <section class="tp-tray"><h3 class="ok-h">🗃️ Hồ sơ gốc để đối chiếu</h3>${html}<article class="tp-paper"><h4>${x.esc(t.papers[idx].title)}</h4>${refList(t.papers[idx],x)}</article></section>`;
}
function gridBar(t,x){
  const rows=t.rows||[],r=rowOf(t,x),g=t.grid||{};
  if(!t.filed&&g.reviewed===g.total)return bar(x,t,`Đã soát đủ ${g.total} người.`,x.confirmCmd(`💸 Chuyển lương ${g.total} người`,'tp_pay',{task:t.id},'Chuyển lương theo bảng đã soát? Ô đánh dấu sẽ được sửa trước khi chuyển; ô sót thì chuyển nguyên như bảng nháp.','primary'));
  if(!r||t.filed)return bar(x,t,'Bảng lương đã chuyển.');
  if(r.reviewed){
    const next=rows.find(v=>!v.reviewed);
    return bar(x,t,`${x.esc(nameOf(r))}: đã soát`,next?x.button('Người tiếp theo ›','car:gpick',{task:t.id,row:next.id},'primary'):'');
  }
  const n=(r.flags||[]).length;
  return bar(x,t,`${x.esc(nameOf(r))} · ${n?`${n} ô nghi sai`:'so từng ô với hồ sơ gốc'}`,x.cmd(n?`✓ Xong dòng · ${n} ô cần sửa`:'✓ Xong dòng · không thấy sai','tp_row',{task:t.id,row:r.id},'primary'));
}

/* ---------------------------------------------------------------- a form (tờ khai) done step by step */
function formDoc(t,x){
  const {idx,html}=paperTabs(t,x,'Giấy tờ');
  return `${worksheet(t,x)}<section class="tp-tray"><h3 class="ok-h">🗃️ Giấy tờ khách gửi <small>${t.papers.length} tờ</small></h3>${html}${paperView(t.papers[idx],x)}</section>${calculator(x)}`;
}
function formBar(t,x){
  const p=t.progress||{},cur=(t.steps||[])[p.at];
  if(cur&&cur.state==='current')return bar(x,t,`Bước ${p.at+1}/${p.total}: ${x.esc(cur.title)}`,x.button('✔ Kiểm tra','car:check',{task:t.id,step:cur.id,kind:cur.kind},'primary'));
  if(!t.filed)return bar(x,t,'Hồ sơ đã khớp hết — nộp cho khách.',x.confirmCmd('📤 Nộp / bàn giao hồ sơ','tp_file',{task:t.id,confirm:true},'Nộp hồ sơ này? Sau khi nộp không sửa được nữa; thưởng hồ sơ phụ thuộc số lần chưa khớp và hạn nộp.','primary'));
  return bar(x,t,'Đã nộp hồ sơ.');
}

/* ---------------------------------------------------------------- the office desktop */
const strip=(x,t)=>statusStrip(x,t,{boss:BOSS,op:'tp_overtime'});
function currentMail(t,x){
  const label=x.cc.labels?.[t.form]||'Hồ sơ',due=dueOf(t,x),left=typeof t.due_turn==='number'?t.due_turn-(x.room.turn||0):null;
  const chips=[`<span class="ok-tag">${x.esc(label)}</span>`,
    !due&&left!==null&&t.known?`<span class="ok-tag ${left<0?'bad':left<8?'warn':''}">${left>=0?`⏳ Hạn nội bộ: còn ${left} lượt`:'⌛ Quá hạn nội bộ'}</span>`:'',
    t.bonus&&t.form!=='grid'?`<span class="ok-tag good">🎁 Thưởng ${x.money(t.bonus)}</span>`:'',
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
  next:nextText,
  job(t,x){
    const grid=t.form==='grid',claims=(x.room.data?.claims||[]).length,fresh=(x.room.data?.today?.rules||[]).filter(r=>r.new).length;
    x.ui.lastGrid=grid?t.id:null;
    const unread=openTasks(x).filter(v=>!v.known).length+claims;
    const tabs=[{id:'inbox',icon:'📥',label:'Hộp thư',badge:unread||'',tone:claims?'bad':''},{id:'doc',icon:'📂',label:'Hồ sơ'},{id:'rules',icon:'📋',label:'Quy định',badge:fresh||'',tone:'warn'}];
    const inbox=inboxPane(x,{tasks:taskMails(x,t,currentMail(t,x)),other:[...claimMails(x),...dayMails(x,{boss:BOSS,key:`${t.id}:${t.known?1:0}`})]});
    const rules=todayRules(x)+lawBook(x);
    if(!t.known)return desk(x,t,{cls:'tp',tabs,strip:strip(x,t),panes:{inbox,rules,
      doc:`<p class="ok-empty"><span aria-hidden="true">✉️</span><b>${x.esc(t.title)}</b><span>${grid?'Bảng lương nháp còn nằm trên bàn chị Hồng.':'Hồ sơ còn trong phong bì.'}</span></p>`},
      bar:bar(x,t,x.esc(nextText(t)),x.cmd(grid?'📥 Nhận bảng lương nháp':'📥 Nhận hồ sơ & đọc yêu cầu','ask',{task:t.id},'primary'),true)});
    if(grid)return desk(x,t,{cls:'tp',tabs,strip:strip(x,t),panes:{inbox,rules,doc:gridDoc(t,x)},bar:gridBar(t,x)});
    return desk(x,t,{cls:'tp',tabs,strip:strip(x,t),panes:{inbox,rules,doc:formDoc(t,x)},bar:formBar(t,x)});
  },
  idle(x){
    const d=x.room.data||{};if(!d.office)return '';
    return idleDesk(x,{cls:'tp',strip:strip(x,null),recap:gridRecap(x),tasks:taskMails(x,null),other:[...claimMails(x),...dayMails(x,{boss:BOSS})],rules:todayRules(x)});
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
    if(!rows.length&&!trust&&!insp)return '';
    return `<article class="card space-top tp-sum"><h4 class="section-title">🧮 Bàn lương hôm nay</h4>${insp}${trust}${rows.length?`<div class="kv">${rows.join('')}</div>`:''}</article>`;
  },
  tick(root){keepBarAboveFooter(root);},
  actions:{
    tab:switchTab,
    gpick(d,el,x){gsel(x)[d.task]=d.row;x.render();document.querySelector('.career-job.tp .tp-queue')?.scrollIntoView({block:'nearest'});},
    async flag(d,el,x){
      const on=el.getAttribute('aria-pressed')==='true';
      el.classList.toggle('flagged',!on);el.setAttribute('aria-pressed',String(!on));
      const r=await x.send('tp_flag',{task:d.task,row:d.row,cell:d.cell});
      if(!r){el.classList.toggle('flagged',on);el.setAttribute('aria-pressed',String(on));}
    },
    paper(d,el,x){const u=x.ui[d.task];if(u){u.paper=Number(d.i)||0;x.render();}},
    pick(d,el,x){const u=x.ui[d.task];if(u){u.sel[d.step]=d.v;x.render();}},
    toggle(d,el,x){const u=x.ui[d.task];if(!u)return;const a=u.multi[d.step]||[];u.multi[d.step]=a.includes(d.v)?a.filter(v=>v!==d.v):[...a,d.v];x.render();},
    opick(d,el,x){const u=x.ui[d.task];if(!u)return;const a=u.order[d.step]||[];if(!a.includes(d.v))u.order[d.step]=[...a,d.v];x.render();},
    unpick(d,el,x){const u=x.ui[d.task];if(!u)return;const a=[...(u.order[d.step]||[])];a.splice(Number(d.i),1);u.order[d.step]=a;x.render();},
    calc(d,el,x){
      const input=document.getElementById('tp-calc');const expr=(input?.value||'').trim();if(!expr)return;
      let out;try{const v=calc(expr);out=Number.isInteger(v)?fmtN(v):`${v.toLocaleString('vi-VN',{maximumFractionDigits:4})} (↓ ${fmtN(Math.floor(v))})`;}catch{out='Phép tính chưa hợp lệ';}
      x.ui.calc=[{expr,out},...(x.ui.calc||[])].slice(0,5);x.render();
    },
    async check(d,el,x){
      const t=x.room.tasks.find(q=>q.id===d.task);if(!t?.steps)return;
      const st=t.steps.find(s=>s.id===d.step),u=state(x,t);if(!st)return;
      const val=id=>document.getElementById(id)?.value??'';
      let answer=null;
      if(st.kind==='choice')answer=u.sel[st.id]||null;
      else if(st.kind==='multi')answer=(u.multi[st.id]||[]).length?[...u.multi[st.id]]:null;
      else if(st.kind==='order')answer=(u.order[st.id]||[]).length===st.items.length?[...u.order[st.id]]:null;
      else if(st.kind==='number')answer=parseIntVN(val(fid(t,st.id)));
      else if(st.kind==='match'){answer={};for(const l of st.left){const v=val(fid(t,st.id,l.id));if(!v){answer=null;break;}answer[l.id]=v;}}
      else if(st.kind==='fields'){answer={};for(const f of st.fields){const raw=val(fid(t,st.id,f.id));const v=f.options?raw:parseIntVN(raw);if(v===null||v===''){answer=null;break;}answer[f.id]=v;}}
      if(answer===null){x.toast('Điền đủ và đúng dạng số nguyên (vd 12.400) trước khi kiểm tra nhé.',true);return;}
      await x.send('tp_submit',{task:t.id,step:st.id,answer});
    },
  },
};
