/** Dịch vụ Thuế & Tiền lương Minh Bạch — paper tray, step-by-step worksheet and a desk calculator. */
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
    case'choice':return `<div class="tp-choices">${st.options.map(o=>`<button type="button" class="tp-choice ${u.sel[st.id]===o.id?'on':''}" data-action="car:pick" data-task="${tid}" data-step="${sid}" data-v="${x.esc(o.id)}" aria-pressed="${u.sel[st.id]===o.id}">${x.esc(o.label)}</button>`).join('')}</div>`;
    case'multi':{const on=u.multi[st.id]||[];return `<div class="tp-choices">${st.options.map(o=>`<button type="button" class="tp-choice check ${on.includes(o.id)?'on':''}" data-action="car:toggle" data-task="${tid}" data-step="${sid}" data-v="${x.esc(o.id)}" aria-pressed="${on.includes(o.id)}"><span class="tp-box" aria-hidden="true">${on.includes(o.id)?'✓':''}</span>${x.esc(o.label)}</button>`).join('')}</div>`;}
    case'number':return `<label class="tp-cell-row"><span>Đáp số (xu)</span><input class="input tp-num" id="${fid(t,st.id)}" data-preserve type="text" inputmode="numeric" autocomplete="off" placeholder="0"></label>`;
    case'fields':return `<table class="tp-cells edit"><tbody>${st.fields.map(f=>`<tr><th scope="row"><label for="${fid(t,st.id,f.id)}">${x.esc(f.label)}</label></th><td>${f.options?`<select id="${fid(t,st.id,f.id)}" data-preserve><option value="">Chọn…</option>${f.options.map(o=>`<option value="${x.esc(o.id)}">${x.esc(o.label)}</option>`).join('')}</select>`:`<input class="input tp-num" id="${fid(t,st.id,f.id)}" data-preserve type="text" inputmode="numeric" autocomplete="off" placeholder="0">`}</td></tr>`).join('')}</tbody></table>`;
    case'match':return `<div class="tp-match">${st.left.map(l=>`<label class="tp-cell-row"><span>${x.esc(l.label)}</span><select id="${fid(t,st.id,l.id)}" data-preserve><option value="">Chọn…</option>${st.right.map(r=>`<option value="${x.esc(r.id)}">${x.esc(r.label)}</option>`).join('')}</select></label>`).join('')}</div>`;
    case'order':{
      const picked=u.order[st.id]||[],rest=st.items.filter(o=>!picked.includes(o.id));
      return `<ol class="tp-order">${picked.map((id,i)=>`<li><span class="tp-no">${i+1}</span><span class="grow">${x.esc(lab(st.items,id))}</span><button type="button" class="btn small ghost" data-action="car:unpick" data-task="${tid}" data-step="${sid}" data-i="${i}" aria-label="Bỏ bước ${i+1}">✕</button></li>`).join('')||'<li class="muted small">Chạm các việc bên dưới theo đúng thứ tự.</li>'}</ol>
        <div class="tp-choices">${rest.map(o=>`<button type="button" class="tp-choice" data-action="car:opick" data-task="${tid}" data-step="${sid}" data-v="${x.esc(o.id)}">＋ ${x.esc(o.label)}</button>`).join('')}</div>`;
    }
  }
  return '<p class="muted">Bước này chưa có giao diện.</p>';
}

function sheet(t,x){
  return `<ol class="tp-steps">${t.steps.map((st,i)=>{
    const head=`<div class="tp-step-head"><span class="tp-no">${st.state==='solved'?'✓':i+1}</span><b>${x.esc(st.title)}</b>${st.tag==='ethic'?x.pill('🔒 bảo mật & quy trình'):''}${t.progress.attempts[st.id]>1&&st.state!=='locked'?`<small class="muted">${t.progress.attempts[st.id]} lần kiểm</small>`:''}</div>`;
    if(st.state==='solved')return `<li class="tp-step solved">${head}<div class="tp-answer">${solvedText(st,x)}</div>${st.explain?`<p class="tp-explain">${x.esc(st.explain)}</p>`:''}</li>`;
    if(st.state==='locked')return `<li class="tp-step locked">${head}</li>`;
    const hint=(t.progress.attempts[st.id]||0)>0?`<p class="tp-hint">💡 ${x.esc(st.hints[Math.min(st.hints.length,t.progress.attempts[st.id])-1])}</p>`:'';
    return `<li class="tp-step current">${head}<p>${x.esc(st.prompt)}</p>${inputView(st,t,x)}${hint}
      <div class="row wrap space-top">${x.button('✔ Kiểm tra','car:check',{task:t.id,step:st.id,kind:st.kind},'primary')}</div></li>`;
  }).join('')}</ol>`;
}

function calculator(x){
  const hist=x.ui.calc||[];
  return `<section class="tp-calc" aria-label="Máy tính bàn"><h4>🧮 Máy tính bàn</h4>
    <div class="tp-calc-row"><input class="input" id="tp-calc" data-preserve type="text" inputmode="decimal" autocomplete="off" placeholder="vd: 12.400 × 8%" aria-label="Phép tính">${x.button('=','car:calc',{},'primary')}</div>
    <ul class="tp-tape">${hist.map(h=>`<li><span>${x.esc(h.expr)}</span><b>${x.esc(h.out)}</b></li>`).join('')||'<li class="muted small">Dấu chấm là phân cách hàng nghìn; % hiểu là chia 100. Kết quả làm tròn xuống ghi kèm.</li>'}</ul></section>`;
}

function rules(x){
  return `<details class="tp-rules"><summary>📘 Quy định: lương, bảo hiểm, thuế, hạn nộp</summary>${(x.cc.rules||[]).map(g=>`<h5>${x.esc(g.emoji+' '+g.group)}</h5><ul>${g.lines.map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul>`).join('')}</details>`;
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
function dueChip(t,x){
  const due=t&&t.status!=='completed'?dueOf(t,x):null;
  return due?`<span class="tp-chip ${due.overdue?'bad':due.soon?'warn':''}">⏰ Hạn ${x.esc(due.time)} · ${due.overdue?'đã trễ':'còn '+span(due.left)}</span>`:'';
}
function officeBar(t,x){
  const d=x.room.data||{},o=d.office;if(!o)return '';
  const mod=d.today?.mod,trust=Math.max(0,Math.min(100,Number(o.trust)||0)),pay=mod?.id==='crunch'?18:12;
  const ask=`Ở lại tới 20:00? Được trả ${pay} xu, mai vào muộn 30 phút vì mệt.`;
  let alert='';
  if(o.locked)alert=`<p class="tp-alert bad">🔒 20:00 — văn phòng khóa cửa. Khép ngày, mai làm tiếp; việc dở được giữ nguyên.</p>`;
  else if(o.closed)alert=`<div class="tp-alert warn"><span>🌇 17:30 — hết giờ hành chính.</span>${x.confirmCmd(`🌙 Ở lại tăng ca (+${pay} xu)`,'tp_overtime',{},ask,'small')}</div>`;
  else if(o.can_overtime)alert=`<div class="tp-alert"><span>Sắp hết giờ. Còn việc dở?</span>${x.confirmCmd(`🌙 Đăng ký tăng ca (+${pay} xu)`,'tp_overtime',{},ask,'ghost small')}</div>`;
  return `<section class="tp-office" aria-label="Giờ làm việc hôm nay">
    <div class="tp-obar"><span class="tp-clock"><b>🕗 ${x.esc(o.time)}</b><small>${o.overtime?'tăng ca tới 20:00':o.lunch?'nghỉ trưa 12:00':'tan sở 17:30'}</small></span>
      ${dueChip(t,x)}
      <span class="tp-trust" title="Chị Hồng tin bạn ${trust}/100"><small>Chị Hồng: ${x.esc(o.trust_label||'')}</small><span class="bar ${trust<35?'low':trust>=75?'high':''}"><i style="width:${trust}%"></i></span></span></div>
    ${mod&&mod.id!=='normal'?`<p class="tp-mod"><b>${x.esc(mod.emoji)} ${x.esc(mod.name)}</b> ${x.esc(mod.text)}</p>`:''}
    ${o.tired?'<p class="small muted">😮‍💨 Hôm qua tăng ca nên sáng nay vào muộn 30 phút.</p>':''}
    ${alert}</section>`;
}
function rulesBox(x){
  const rs=x.room.data?.today?.rules||[];if(!rs.length)return '';
  const fresh=rs.filter(r=>r.new).length;
  return `<section class="tp-rulebox" aria-label="Quy định kỳ lương này"><h4>📋 Quy định kỳ lương tháng ${x.esc(x.room.data?.today?.month??'')} ${fresh?`<span class="tp-new">${fresh} mới</span>`:''}</h4>
    <div class="tp-rules-row">${rs.map(r=>`<article class="tp-rule ${r.new?'new':''}"><b>${x.esc(r.emoji)} ${x.esc(r.title)}${r.new?' <em>MỚI</em>':''}</b><p>${x.esc(r.text)}</p></article>`).join('')}</div></section>`;
}
function claimsBox(x){
  const cl=x.room.data?.claims||[];if(!cl.length)return '';
  const ch=x.cc.claim_choices||[];
  return `<section class="tp-claims" aria-label="Khiếu nại lương"><h4>📨 Khiếu nại sau ngày trả lương <span class="tp-new">${cl.length}</span></h4>
    ${cl.map(c=>`<article class="tp-claim"><div><b>${x.esc(c.name)}</b> · thiếu <b class="num">${fmtN(c.amount)} xu</b><p>${x.esc(c.why)}</p></div>
      <div class="tp-claim-acts">${ch.map((o,i)=>x.cmd(x.esc(o.label),'tp_claim',{claim:c.id,choice:o.id},i===0?'primary small':'ghost small')).join('')}</div></article>`).join('')}
    <p class="small muted">Khiếu nại chưa xử lý tới cuối ngày làm chị Hồng mất tin tưởng.</p></section>`;
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
    foot=`<div class="tp-verdict ${ok?'ok':'bad'}" role="status"><b>${ic} ${label}</b>${(r.truth?.why||[]).map(w=>`<p>${x.esc(w)}</p>`).join('')}${r.result.missed.length?`<p class="small">Sót: ${r.result.missed.length} ô</p>`:''}${r.result.extra.length?`<p class="small">Đánh dấu nhầm: ${r.result.extra.length} ô</p>`:''}${ok&&!(r.truth?.why||[]).length?'<p>Dòng này đúng từ đầu.</p>':''}</div>`;
  }else if(r.reviewed){
    const next=(t.rows||[]).find(v=>!v.reviewed);
    foot=`<p class="tp-done">✓ Đã soát${flags.size?` · ${flags.size} ô cần sửa`:' · không thấy sai'}</p>${next?x.button('Người tiếp theo ›','car:gpick',{task:t.id,row:next.id},'primary full'):''}`;
  }else{
    foot=`${r.tip?`<p class="tp-hint">💡 ${x.esc(r.tip)}</p>`:''}<div class="tp-row-tools"><small>${flags.size?`🚩 ${flags.size}/${max} ô nghi sai`:'Chạm vào ô sai để đánh dấu'}</small>${r.hinted?'':x.cmd('💡 Gợi ý','tp_hint',{task:t.id,row:r.id},'ghost small')}</div>
      ${x.cmd(flags.size?`✓ Xong dòng · ${flags.size} ô cần sửa`:'✓ Xong dòng · không thấy sai','tp_row',{task:t.id,row:r.id},'primary full')}`;
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
  return `<section class="tp-recap" role="status"><h4>💸 Bảng lương vừa chuyển · ${Number(g.ok)||0}/${Number(g.total)||t.rows.length} dòng chuẩn</h4><ul>${li}</ul></section>`;
}
function gridView(t,x){
  const rows=t.rows||[],r=rowOf(t,x),g=t.grid||{};
  const chips=rows.map(v=>{
    const st=v.result?(v.result.ok?'✓':'✗'):v.reviewed?'•':'';
    return x.button(`<span>${x.esc(nameOf(v).split(' ').pop())}</span>${st?`<i>${st}</i>`:''}${(v.flags||[]).length&&!v.result?'<i>🚩</i>':''}`,'car:gpick',{task:t.id,row:v.id},`tp-qchip ${v.id===r?.id?'active':''} ${v.result?(v.result.ok?'ok':'bad'):v.reviewed?'done':''}`);
  }).join('');
  const u=state(x,t),idx=Math.min(u.paper,t.papers.length-1);
  const tabs=t.papers.map((q,i)=>`<button type="button" class="tp-tab ${i===idx?'on':''}" data-action="car:paper" data-task="${x.esc(t.id)}" data-i="${i}" aria-pressed="${i===idx}">📄 ${x.esc(q.title)}</button>`).join('');
  const ready=!t.filed&&g.reviewed===g.total;
  const pay=ready?`<div class="tp-pay">${x.confirmCmd(`💸 Chuyển lương ${g.total} người`,'tp_pay',{task:t.id},'Chuyển lương theo bảng đã soát? Ô đánh dấu sẽ được sửa trước khi chuyển; ô sót thì chuyển nguyên như bảng nháp.','primary full big')}</div>`:'';
  const summary=t.filed?`<p class="tp-grid-sum">💸 Đã chuyển lương · ${g.ok}/${g.total} dòng chuẩn</p>`:`<small class="muted">${g.reviewed||0}/${g.total||rows.length} đã soát</small>`;
  return `<div class="tp-grid-desk">
    <div class="tp-grid-main"><nav class="tp-queue" aria-label="Bảng lương nháp">${chips}${summary}</nav>${pay}${r?rowCard(t,r,x):''}</div>
    <div class="tp-grid-side">${rulesBox(x)}<section class="tp-tray"><div class="tp-tabs" role="toolbar" aria-label="Hồ sơ gốc">${tabs}</div>
      <article class="tp-paper"><h4>${x.esc(t.papers[idx].title)}</h4>${refList(t.papers[idx],x)}</article></section></div>
  </div>`;
}

export default {
  id:'tax_payroll',
  css:true,
  next(t){
    if(t.form==='grid'){
      if(!t.known)return 'Nhận bảng lương nháp';
      const left=(t.rows||[]).filter(r=>!r.reviewed).length;
      return left?`Soát bảng lương: còn ${left}/${(t.rows||[]).length} người`:'Chuyển lương trước giờ hạn';
    }
    if(!t.known)return 'Nhận hồ sơ, đọc yêu cầu';
    const p=t.progress;
    if(p&&p.at<p.total)return `Bước ${p.at+1}/${p.total}: ${t.steps[p.at].title}`;
    return 'Nộp / bàn giao hồ sơ';
  },
  job(t,x){
    const who=x.npc(t.npc),label=x.cc.labels?.[t.form]||'Hồ sơ',bar=officeBar(t,x),grid=t.form==='grid';
    x.ui.lastGrid=grid?t.id:null;
    if(!t.known){
      return `<div class="career-job tp">${bar}${claimsBox(x)}<article class="tp-ticket"><div class="row">${x.portrait(who,56)}<div class="grow"><span class="tp-form">${x.esc(label)}</span><h3>${x.esc(who.display_name)}</h3><p>“${x.esc(t.opening)}”</p></div></div>${x.cmd(grid?'📥 Nhận bảng lương nháp':'📥 Nhận hồ sơ & đọc yêu cầu','ask',{task:t.id},'primary full')}${grid?'<p class="small muted">Soát từng ô với hồ sơ gốc. Sót lỗi thì người lao động nhận sai lương — hôm sau sẽ có khiếu nại.</p>':''}</article>${grid?rulesBox(x):''}</div>`;
    }
    if(grid)return `<div class="career-job tp">${bar}${claimsBox(x)}<article class="tp-ticket compact"><div class="row">${x.portrait(who,40)}<div class="grow"><small class="muted">${x.esc(label)} · ${x.esc(who.display_name)}</small><p>“${x.esc(t.opening)}”</p></div></div></article>${gridView(t,x)}</div>`;
    const u=state(x,t),p=t.progress,left=t.due_turn-(x.room.turn||0);
    const idx=Math.min(u.paper,t.papers.length-1);
    const tabs=t.papers.map((q,i)=>`<button type="button" class="tp-tab ${i===idx?'on':''}" data-action="car:paper" data-task="${x.esc(t.id)}" data-i="${i}" aria-pressed="${i===idx}">📄 ${x.esc(q.title)}</button>`).join('');
    const done=p.at>=p.total;
    const timed=typeof t.due==='number';
    const due=left>=0?`⏳ Hạn nội bộ: còn ${left} lượt thao tác`:'⌛ Đã quá hạn nội bộ — nộp vẫn được nhưng không có thưởng';
    return `<div class="career-job tp">${bar}${claimsBox(x)}
      <article class="tp-ticket"><div class="row">${x.portrait(who,48)}<div class="grow">
        <div class="row spread wrap"><span class="tp-form">${x.esc(label)}</span>${x.pill(`🎁 thưởng ${x.money(t.bonus)}`)}</div>
        <h3>${x.esc(t.title)}</h3><p class="small">${x.esc(t.brief)}</p>
        <div class="row wrap">${timed?dueChip(t,x):`<span class="tp-due ${left<8?'warn':''} ${left<0?'bad':''}">${due}</span>`}${t.mistakes?x.pill(`✗ ${t.mistakes} lần chưa khớp`,'bad'):''}</div>
        <div class="tp-progress" role="progressbar" aria-valuemin="0" aria-valuemax="${p.total}" aria-valuenow="${p.at}"><i style="width:${p.at/p.total*100}%"></i></div>
      </div></div></article>
      <div class="tp-desk">
        <section class="tp-tray"><div class="tp-tabs" role="toolbar" aria-label="Giấy tờ">${tabs}</div>${paperView(t.papers[idx],x)}${calculator(x)}</section>
        <section class="tp-work"><h4 class="section-title">Bảng tính hồ sơ</h4>${sheet(t,x)}
          ${done&&!t.filed?`<div class="tp-file">${x.confirmCmd('📤 Nộp / bàn giao hồ sơ','tp_file',{task:t.id,confirm:true},'Nộp hồ sơ này? Sau khi nộp không sửa được nữa; thưởng hồ sơ phụ thuộc số lần chưa khớp và hạn nộp.','primary full')}</div>`:''}</section>
        <aside class="tp-tools">${rules(x)}</aside>
      </div></div>`;
  },
  idle(x){
    const d=x.room.data||{};if(!d.office)return '';
    return `<div class="career-job tp">${gridRecap(x)}${officeBar(null,x)}${claimsBox(x)}${rulesBox(x)}</div>`;
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
  actions:{
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
