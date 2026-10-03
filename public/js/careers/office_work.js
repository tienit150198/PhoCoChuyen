/** Hands-on desks of Công ty CP Cánh Diều (hr_admin, secretary, it_helpdesk) inside the shared office
 * desktop (office_kit.js): 📥 Hộp thư · 📂 Hồ sơ · 📋 Quy định and the sticky bar. One dossier is one piece
 * of real desk work (game/careers/office_work.py), drawn here by its kind:
 *   sort   one card at a time, tap the tray it goes in;
 *   mark   a draft or a sheet: tap a word or a cell, pick the right wording (or the reason it is wrong);
 *   slots  a rooms × hours board: pick a meeting, tap a free cell;
 *   fields what a caller said or a label shows, typed into a form;
 *   seq    tap the steps you will do, in order (↑ ↓ to move, ✕ to drop);
 *   case   look into it, then answer.
 * The server keeps the clock and the score: every move is a command. Only the open card, the word being
 * fixed, the meeting being placed and the step list being built live in x.ui. */
import {statusStrip,taskMails,dayMails,inboxPane,rulesList,desk,bar,switchTab,keepBarAboveFooter,fold,idleDesk,openTasks,mateCards,trackFold,careSummary,foldToggle,
  goto,gotoAction,guideOf,summaryCard} from './office_kit.js';
import {pending,stepLine} from '../v4/guide.js';

const DONE=['completed','cancelled','referred'];
const u=(x,t)=>x.ui[t.id]??={card:null,seg:null,item:null,order:null};
const W=t=>t.work||{};
/** Openings here often carry who speaks (“Chị Huyền gửi file: “…””): quote only the ones that are plain speech. */
const quoted=(x,text)=>/[“”]/.test(text||'')?x.esc(text):`“${x.esc(text)}”`;
const mails=(x,t,body)=>taskMails(x,t,body).map(m=>{const v=m.preview&&openTasks(x).find(o=>m.act?.includes(`data-task="${x.esc(o.id)}"`));
  return v?{...m,preview:quoted(x,v.opening)}:m;});
const optsOf=(w,sg)=>sg.opts||w.opts||[];
const fid=(t,f)=>['ow',t.id,f].join('-').replace(/[^a-zA-Z0-9_-]/g,'_');
const cut=(s,n)=>{s=String(s||'');return s.length>n?s.slice(0,n-1)+'…':s;};
const segsOf=w=>(w.blocks||[]).flatMap(b=>b.k==='table'?b.rows.flatMap(r=>r.filter(c=>c&&typeof c==='object'&&c.id)):(b.segs||[]).filter(s=>s.id));

/* ---------------------------------------------------------------- shared bits */
function deskCard(x,c){
  const dk=x.room.data?.desk;if(!dk)return '';
  const ev=dk.ev;
  if(ev){
    const opts=ev.options.map(o=>{
      const poor=o.cost>(Number(x.room.money)||0);
      const inner=`<span class="ow-opt-label">${x.esc(o.label)}</span>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}${o.cost?`<em>−${x.fmt(o.cost)} xu${poor?' · chưa đủ tiền':''}</em>`:''}`;
      return o.cost?x.confirmCmd(inner,c.p+'desk',{option:o.id},`Cách này tốn ${x.fmt(o.cost)} xu. Đồng ý?`,'ow-opt',poor):x.cmd(inner,c.p+'desk',{option:o.id},'ow-opt');
    }).join('');
    return `<section class="ow-event ${ev.tone==='tense'?'tense':''}" role="group" aria-labelledby="ow-ev-title" data-step-card="ev:${x.esc(ev.id)}"><div class="ow-ev-head"><span aria-hidden="true">${x.esc(ev.emoji)}</span><div><small>Chuyện bất ngờ ở văn phòng</small><h3 id="ow-ev-title">${x.esc(ev.title)}</h3></div></div>
      <p>${x.esc(ev.text)}</p><div class="ow-opts">${opts}</div></section>`;
  }
  const last=dk.last,key=last?`${last.script}-${last.choice}-${last.day}-${(dk.log||[]).length}`:'';
  if(last&&last.day===x.room.day&&x.ui.seen!==key)
    return `<div class="ow-last ${last.good===true?'good':last.good===false?'bad':''}" role="status"><span aria-hidden="true">${x.esc(last.emoji||'💬')}</span><p><b>${x.esc(last.title||'')}</b> · ${x.esc(last.outcome||'')}</p>${x.button('✕','car:seen',{key},'ghost small ow-x')}</div>`;
  return '';
}

function papersView(t,x){
  const ps=t.papers||[];if(!ps.length)return '';
  const items=ps.map((p,i)=>{
    const key=`owp-${t.id}-${p.id}`,open=x.ui.okFold?.[key]??i===0;
    return fold(`${x.esc(p.emoji||'📄')} ${x.esc(p.title)}`,`<ul class="ow-lines">${(p.lines||[]).map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul>`,open,'ow-paper',key);
  }).join('');
  return `<section class="ow-papers"><h3 class="ok-h">🗃️ Giấy tờ kèm theo <small>${ps.length} tờ · chạm để mở</small></h3>${items}</section>`;
}

function twistBanner(t,x){
  const tw=W(t).twist;if(!tw)return '';
  return `<p class="ow-twist" role="status"><b>📞 Vừa đổi:</b> ${x.esc(tw.note)}</p>`;
}

function hintBox(t,x,c){
  if(t.filed)return '';
  const tips=(t.tips||[]).map(s=>`<li>💡 ${x.esc(s)}</li>`).join(''),left=Number(t.hints_left)||0,hs=x.cc.helpers||[c.boss];
  const who=hs[(Number(x.room.day)||0)%hs.length];
  const btn=x.cmd(left?`💡 Hỏi ${x.esc(who)} · còn ${left} lần`:'💡 Hết lượt hỏi',c.p+'hint',{task:t.id},'ghost small',!left);
  return `<section class="ow-help">${tips?`<ul class="ow-tips">${tips}</ul>`:''}<div class="ow-help-row">${btn}<small>Mỗi lần hỏi mất 10 phút và bớt ${Number(x.cc.hint_cut)||3} xu thưởng.</small></div></section>`;
}

function resultView(t,x){
  const r=t.result;if(!r)return '';
  const lines=(r.lines||[]).map(l=>`<li class="${l.ok?'ok':'bad'}"><b aria-hidden="true">${l.ok?'✓':'✗'}</b><span>${x.esc(l.text)}</span></li>`).join('');
  const clean=!(r.errors||[]).length;
  return `<section class="ow-result ${clean?'ok':'bad'}" role="status"><h3 class="ok-h">📤 ${x.esc(cut(t.title,60))} · ${Number(r.ok)||0}/${Number(r.total)||0} đúng${t.late?' <span class="ok-tag warn">Trễ hạn</span>':''}</h3>
    ${clean?'<p class="ow-clean">Không sai chỗ nào. Gọn!</p>':''}<ul class="ow-res">${lines}</ul></section>`;
}

/* ---------------------------------------------------------------- sort: one card at a time, tap its tray */
function sortDoc(t,x){
  const w=W(t),ans=t.ans||{},s=u(x,t),bins=w.bins||[],items=w.items||[],tw=w.twist?.item;
  const cur=items.find(i=>i.id===s.card)||(tw&&!(tw in ans)&&items.find(i=>i.id===tw))||items.find(i=>!(i.id in ans))||items[0];if(!cur)return '';
  const binOf=id=>bins.find(b=>b.id===id),done=items.filter(i=>i.id in ans).length;
  const chips=items.map((it,i)=>{const b=binOf(ans[it.id]),on=it.id===cur.id;
    return `<button type="button" class="ow-chip${on?' on':''}${b?' done':''}${it.id===tw?' tw':''}" data-action="car:card" data-task="${x.esc(t.id)}" data-card="${x.esc(it.id)}" aria-pressed="${on}" aria-label="${x.esc(`Thẻ ${i+1}: ${it.title}${b?` · ${b.label}`:' · chưa xếp'}`)}"><span>${i+1}</span>${b?`<i aria-hidden="true">${x.esc(b.emoji)}</i>`:''}</button>`;}).join('');
  const counts=bins.map(b=>`<span class="ow-bincount"><span aria-hidden="true">${x.esc(b.emoji)}</span> ${x.esc(b.label)} <b>${items.filter(i=>ans[i.id]===b.id).length}</b></span>`).join('');
  const lines=(cur.lines||[]).map(l=>`<li>${x.esc(l)}</li>`).join('');
  const btns=bins.map(b=>{const on=ans[cur.id]===b.id;
    return `<button type="button" class="btn ow-bin${on?' on':''}" data-action="car:put" data-task="${x.esc(t.id)}" data-item="${x.esc(cur.id)}" data-bin="${on?'':x.esc(b.id)}" aria-pressed="${on}"><span aria-hidden="true">${x.esc(b.emoji)}</span> ${x.esc(b.label)}${on?' ✓':''}</button>`;}).join('');
  return `<section class="ow-sort"><h3 class="ok-h">🗂️ Xếp vào khay <small>${done}/${items.length} thẻ đã xếp</small></h3>
    <nav class="ow-chips" aria-label="Các thẻ">${chips}</nav>
    <article class="ow-card${cur.id===tw?' tw':''}" data-step-card="${x.esc(t.id)}:${x.esc(cur.id)}"><header><b>${x.esc(cur.title)}</b>${cur.sub?`<small>${x.esc(cur.sub)}</small>`:''}${cur.id===tw?'<span class="ok-tag warn">Vừa đổi</span>':''}</header>
      ${lines?`<ul class="ow-lines">${lines}</ul>`:''}${cur.note?`<p class="ow-note">${x.esc(cur.note)}</p>`:''}
      <div class="ow-bins" role="group" aria-label="Xếp thẻ này vào khay">${btns}</div></article>
    <div class="ow-counts">${counts}</div></section>`;
}

/* ---------------------------------------------------------------- mark: tap a word or a cell, pick the right one */
function markDoc(t,x){
  const w=W(t),ans=t.ans||{},s=u(x,t),tw=w.twist?.seg;
  // A sheet cell shows what is written in it (times, ✓/—) until you mark it; then the reason you chose.
  const shown=sg=>{const o=optsOf(w,sg),i=sg.id in ans?ans[sg.id]:sg.keep;return w.opts&&!(sg.id in ans)?sg.t:o[i]??sg.t;};
  const segBtn=sg=>{const ch=sg.id in ans,on=s.seg===sg.id;
    return `<button type="button" class="ow-seg${ch?' fixed':''}${on?' on':''}${sg.id===tw?' tw':''}" data-action="car:seg" data-task="${x.esc(t.id)}" data-seg="${x.esc(sg.id)}" aria-pressed="${on}" aria-label="${x.esc(`${shown(sg)}${ch?` (đã sửa từ “${sg.t}”)`:''} · chạm để sửa`)}">${ch?`<s>${x.esc(sg.t)}</s> `:''}${x.esc(shown(sg))}</button>`;};
  const picker=sg=>{
    const o=optsOf(w,sg),cur=sg.id in ans?ans[sg.id]:sg.keep;
    return `<div class="ow-picker" data-step-card="${x.esc(t.id)}:${x.esc(sg.id)}"><p><b>“${x.esc(sg.t)}”</b> ${w.opts?'— ô này đúng chưa?':'— sửa thành:'}</p><div class="ow-choices">${o.map((v,i)=>
      `<button type="button" class="ow-choice${i===cur?' on':''}" data-action="car:mark" data-task="${x.esc(t.id)}" data-seg="${x.esc(sg.id)}" data-opt="${i}" aria-pressed="${i===cur}"><span class="ow-box" aria-hidden="true">${i===cur?'●':''}</span>${x.esc(v)}${i===sg.keep&&!w.opts?' <small>(giữ nguyên)</small>':''}</button>`).join('')}</div>
      ${x.button('Đóng','car:segx',{task:t.id},'ghost small')}</div>`;};
  const sel=segsOf(w).find(sg=>sg.id===s.seg);
  const blocks=(w.blocks||[]).map(b=>{
    let html,has=false;
    if(b.k==='table'){
      const rows=b.rows.map(r=>`<tr>${r.map((c,i)=>{
        if(c&&typeof c==='object'&&c.id){if(c.id===s.seg)has=true;return `<td>${segBtn(c)}</td>`;}
        const v=c&&typeof c==='object'?c.t:c;return i===0?`<th scope="row">${x.esc(v)}</th>`:`<td>${x.esc(v)}</td>`;}).join('')}</tr>`).join('');
      html=`<div class="ow-scroll" tabindex="0" aria-label="Bảng cần soát"><table class="ow-sheet"><thead><tr>${b.head.map(h=>`<th scope="col">${x.esc(h)}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`;
    }else{
      const inner=(b.segs||[]).map(sg=>{if(sg.id){if(sg.id===s.seg)has=true;return segBtn(sg);}return x.esc(sg.t);}).join('');
      html=b.k==='h'?`<h4 class="ow-doc-h">${inner}</h4>`:`<p class="ow-doc-p">${inner}</p>`;
    }
    return html+(has&&sel?picker(sel):'');
  }).join('');
  const fixed=Object.keys(ans).length;
  return `<section class="ow-mark"><h3 class="ok-h">🔍 Soát từng chỗ <small>${fixed?`đã sửa ${fixed} chỗ`:'chạm vào chỗ sai để sửa'}</small></h3>
    <article class="ow-doc${w.opts?' ow-doc-table':''}">${blocks}</article>
    ${w.opts?`<p class="ok-note">Chạm một ô, chọn lý do nếu ô đó sai. Ô đúng thì để nguyên.</p>`:`<p class="ok-note">Chữ gạch chân chấm là chỗ chạm được. Chỗ đúng thì để nguyên.</p>`}</section>`;
}

/* ---------------------------------------------------------------- slots: rooms × hours */
function slotsDoc(t,x){
  const w=W(t),ans=t.ans||{},s=u(x,t),cols=w.cols||[],rows=w.rows||[],items=w.items||[],rules=w.rules||[],tags=w.tags||{};
  const at={};for(const [k,v] of Object.entries(ans))at[v]=k;
  const taken={};for(const r of rules)if(r.kind==='taken')taken[`${r.col}|${r.row}`]=r;
  const busy={};for(const r of rules)if(r.kind==='busy')for(const h of r.rows)(busy[h]??=[]).push(r.who);
  const sel=items.find(i=>i.id===s.item)||items.find(i=>!(i.id in ans));
  const rowL=id=>rows.find(r=>r.id===id)?.label||id,colL=id=>cols.find(c=>c.id===id)?.label||id;
  const where=it=>{const v=ans[it.id];if(!v)return '';const [c,r]=v.split('|');return `${rowL(r)} · ${colL(c)}`;};
  const chips=items.map(it=>{const on=sel?.id===it.id,p=where(it);
    return `<button type="button" class="ow-item${on?' on':''}${p?' done':''}" data-action="car:item" data-task="${x.esc(t.id)}" data-item="${x.esc(it.id)}" aria-pressed="${on}">
      <b>${x.esc(it.title)}</b><small>👥 ${Number(it.size)||1}${(it.who||[]).length?` · ${x.esc(it.who.join(', '))}`:''}${(it.needs||[]).map(n=>` · cần ${x.esc(tags[n]||n)}`).join('')}</small>${p?`<em>📍 ${x.esc(p)}</em>`:'<em class="todo">Chưa xếp</em>'}</button>`;}).join('');
  const head=cols.map(c=>`<th scope="col"><b>${x.esc(c.label)}</b><small>👥 ${Number(c.cap)||0}${(c.tags||[]).map(g=>` · ${x.esc(tags[g]||g)}`).join('')}</small></th>`).join('');
  const body=rows.map(r=>`<tr><th scope="row"><b>${x.esc(r.label)}</b>${busy[r.id]?`<small class="ow-busy">🚫 ${x.esc(busy[r.id].join(', '))}</small>`:''}</th>${cols.map(c=>{
    const key=`${c.id}|${r.id}`,iid=at[key],it=items.find(i=>i.id===iid),tk=taken[key];
    if(it)return `<td><button type="button" class="ow-cell full${sel?.id===it.id?' on':''}" data-action="car:item" data-task="${x.esc(t.id)}" data-item="${x.esc(it.id)}" aria-label="${x.esc(`${r.label} · ${c.label}: ${it.title}`)}">${x.esc(cut(it.title,28))}</button></td>`;
    const lock=tk?`<span class="ow-taken">🔒 ${x.esc(cut(tk.text,26))}</span>`:'';
    if(!sel)return `<td>${lock||'<span class="ow-free">—</span>'}</td>`;
    return `<td><button type="button" class="ow-cell${tk?' taken':''}" data-action="car:place" data-task="${x.esc(t.id)}" data-item="${x.esc(sel.id)}" data-cell="${x.esc(key)}" aria-label="${x.esc(`Xếp “${sel.title}” vào ${c.label} lúc ${r.label}`)}">${lock||'＋'}</button></td>`;
  }).join('')}</tr>`).join('');
  const rl=rules.map(r=>`<li class="${r.new?'new':''}">${r.new?'<em class="ok-newtag">MỚI</em> ':''}${x.esc(r.kind==='busy'?`${r.who}: ${r.text} lúc ${r.rows.map(rowL).join(', ')}`:r.text)}</li>`).join('');
  const off=sel&&ans[sel.id]?`<p class="ow-unplace">${x.button(`↩️ Gỡ “${x.esc(cut(sel.title,30))}” khỏi lịch`,'car:unplace',{task:t.id,item:sel.id},'ghost small')}</p>`:'';
  return `<section class="ow-slots"><h3 class="ok-h">🗓️ Bảng lịch <small>${Object.keys(ans).length}/${items.length} đã xếp</small></h3>
    ${rl?`<ul class="ow-rules" aria-label="Điều cần nhớ khi xếp">${rl}</ul>`:''}
    <div class="ow-items" role="group" aria-label="Việc cần xếp">${chips}</div>
    ${sel?`<p class="ow-pickhint" data-step-card="${x.esc(t.id)}:${x.esc(sel.id)}">👆 Đang xếp: <b>${x.esc(sel.title)}</b> — chạm một ô trống trên bảng.</p>`:''}
    <div class="ow-scroll" tabindex="0" aria-label="Bảng phòng và giờ"><table class="ow-grid"><thead><tr><th scope="col">Giờ</th>${head}</tr></thead><tbody>${body}</tbody></table></div>${off}</section>`;
}

/* ---------------------------------------------------------------- fields: a call or a label, typed into a form */
/* Dates and times on a numeric keypad (feedback 02/10: phones' number pad has no "/" or ":"): typing digits puts the
 * separators in by itself (05032027 → 05/03/2027, 1430 → 14:30); a date also has 📅, the phone's own calendar. */
const isoOf=v=>{const m=/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(String(v||'').trim());return m?`${m[3]}-${m[2].padStart(2,'0')}-${m[1].padStart(2,'0')}`:'';};
function fmtDigits(kind,raw){
  const d=raw.replace(/\D+/g,'');
  if(kind==='date'){const a=d.slice(0,2),b=d.slice(2,4),y=d.slice(4,8);return a+(d.length>2?'/'+b:'')+(d.length>4?'/'+y:'');}
  return d.length>=4?d.slice(0,2)+':'+d.slice(2,4):d;   // only once the four digits are in (930 stays 930: 9:30 on the server)
}
let fmtBound=false;
function bindFormat(){
  if(fmtBound||typeof document==='undefined')return;fmtBound=true;
  document.addEventListener('input',e=>{
    const el=e.target;if(!(el instanceof HTMLInputElement))return;
    const kind=el.dataset.owFmt;
    if(kind){
      if(e.inputType&&e.inputType.startsWith('delete'))return;   // let backspace remove a "/" or ":" freely
      if(/[^\d/:\s.\-h]/i.test(el.value))return;                 // something else typed by hand: leave it
      if(!/^[\d]+$/.test(el.value.replace(/[/:]/g,'')))return;     // separators typed by hand ("5/3/2027"): leave it
      const v=fmtDigits(kind,el.value);if(v!==el.value){el.value=v;try{el.setSelectionRange(v.length,v.length);}catch{/* not a text box */}}
      return;
    }
    if(el.dataset.owCal!==undefined)fromCalendar(el);
  });
  document.addEventListener('change',e=>{const el=e.target;if(el instanceof HTMLInputElement&&el.dataset.owCal!==undefined)fromCalendar(el);});
}
function fromCalendar(el){
  const m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(el.value);const box=document.getElementById(el.dataset.owCal);
  if(!m||!box)return;box.value=`${m[3]}/${m[2]}/${m[1]}`;box.dispatchEvent(new Event('change',{bubbles:true}));
}

function fieldsDoc(t,x){
  const w=W(t),ans=t.ans||{},tw=w.twist?.field;
  const script=(w.script||[]).map(l=>`<li class="ow-say${l.new?' new':''}"><b>${x.esc(l.who)}</b><p>${x.esc(l.text)}</p></li>`).join('');
  const box=f=>{const id=fid(t,f.id),v=ans[f.id]??'';
    const input=f.kind==='pick'
      ?`<select id="${id}" data-preserve><option value="">Chọn…</option>${(f.opts||[]).map(o=>`<option value="${x.esc(o.id)}"${o.id===v?' selected':''}>${x.esc(o.label)}</option>`).join('')}</select>`
      :`<input class="input" id="${id}" data-preserve type="text" autocomplete="off" maxlength="80" value="${x.esc(v)}"${f.kind==='digits'?' inputmode="numeric"':f.kind==='time'?' inputmode="numeric" placeholder="vd 14:30" data-ow-fmt="time"':f.kind==='date'?' inputmode="numeric" placeholder="vd 05/03/2027" data-ow-fmt="date"':''}>`
        +(f.kind==='date'?`<span class="ow-cal" title="Chọn trên lịch">📅<input type="date" class="ow-cal-in" data-ow-cal="${id}" aria-label="Chọn ngày trên lịch" value="${x.esc(isoOf(v))}"></span>`:'');
    return `<label class="ow-field${f.id===tw?' tw':''}${f.kind==='date'?' date':''}" for="${id}"><span>${x.esc(f.label)}${f.id===tw?' <span class="ok-tag warn">Vừa đổi</span>':''}</span>${f.kind==='date'?`<span class="ow-datebox">${input}</span>`:input}</label>`;};
  return `<section class="ow-fields"><h3 class="ok-h">📝 Ghi lại cho đủ <small>${(w.fields||[]).length} ô</small></h3>
    ${script?`<ol class="ow-script" aria-label="Lời người ta nói">${script}</ol>`:''}
    <form class="ow-form" data-step-card="${x.esc(t.id)}:form" onsubmit="return false">${(w.fields||[]).map(box).join('')}</form></section>`;
}

/* ---------------------------------------------------------------- seq: pick the steps, in order */
const orderOf=(x,t)=>{const s=u(x,t);if(!s.order)s.order=[...(t.ans?.order||[])];return s.order;};
function seqDoc(t,x){
  const w=W(t),pool=w.pool||[],order=orderOf(x,t),tw=w.twist?.step,lab=id=>pool.find(p=>p.id===id)?.label||id;
  const li=order.map((id,i)=>`<li class="${id===tw?'tw':''}"><span class="ow-no">${i+1}</span><span class="grow">${x.esc(lab(id))}</span>
    ${x.button('↑','car:up',{task:t.id,i},'ghost small ow-mv',i===0)}${x.button('↓','car:down',{task:t.id,i},'ghost small ow-mv',i===order.length-1)}${x.button('✕','car:del',{task:t.id,i},'ghost small ow-mv')}</li>`).join('');
  const rest=pool.filter(p=>!order.includes(p.id)).map(p=>`<button type="button" class="ow-choice${p.id===tw?' tw':''}" data-action="car:add" data-task="${x.esc(t.id)}" data-step="${x.esc(p.id)}">＋ ${x.esc(p.label)}${p.id===tw?' <span class="ok-tag warn">Vừa đổi</span>':''}</button>`).join('');
  return `<section class="ow-seq"><h3 class="ok-h">🧭 Các bước sẽ làm <small>${order.length} bước</small></h3>
    <ol class="ow-order" data-step-card="${x.esc(t.id)}:order">${li||'<li class="ow-empty">Chạm các bước bên dưới theo thứ tự sẽ làm. Bước có hại thì bỏ qua.</li>'}</ol>
    ${rest?`<h4 class="ok-h2">Có thể làm</h4><div class="ow-choices ow-pool">${rest}</div>`:''}</section>`;
}

/* ---------------------------------------------------------------- case: look into it, then answer */
function caseDoc(t,x,c){
  const w=W(t),read=new Set(t.ans?.read||[]),cost=Number(x.cc.cost?.read)||8;
  const facts=(w.facts||[]).map(f=>read.has(f.id)
    ?`<li class="ow-fact read"><b>🔎 ${x.esc(f.title)}</b>${f.source?` <small>· ${x.esc(f.source)}</small>`:''}<p>${x.esc(f.text||'')}</p></li>`
    :`<li class="ow-fact">${x.cmd(`🔍 ${x.esc(f.title)} <small>· ${cost} phút</small>`,c.p+'read',{task:t.id,fact:f.id},'ow-ask')}</li>`).join('');
  const title=id=>(w.facts||[]).find(f=>f.id===id)?.title||id;
  const opts=(w.options||[]).map(o=>{const miss=(o.requires||[]).filter(r=>!read.has(r));
    return `<li>${x.confirmCmd(x.esc(o.label),c.p+'reply',{task:t.id,option:o.id},'Trả lời theo cách này? Chọn rồi không đổi được.','ow-answer',!!miss.length)}${miss.length?`<small class="ow-need">Cần tìm hiểu trước: ${x.esc(miss.map(title).join(', ').toLowerCase())}</small>`:''}</li>`;}).join('');
  return `<section class="ow-case"><h3 class="ok-h">🔎 Tìm hiểu <small>${read.size}/${(w.facts||[]).length} chuyện</small></h3>
    <ul class="ow-facts">${facts}</ul>
    <h3 class="ok-h">💬 Trả lời thế nào?</h3><ul class="ow-answers" data-step-card="${x.esc(t.id)}:answer">${opts}</ul></section>`;
}

const VIEW={sort:sortDoc,mark:markDoc,slots:slotsDoc,fields:fieldsDoc,seq:seqDoc,case:caseDoc};

/* ---------------------------------------------------------------- next step, bottom button */
function guideFor(t,x,c){
  const ev=x.room.data?.desk?.ev;
  if(ev)return {steps:[{ok:null,label:ev.title,go:goto(x,t,'.ow-event','👇 Quyết chuyện này trước')}],final:null};
  if(!t.known)return {steps:[{ok:null,label:'Nhận hồ sơ, đọc yêu cầu',go:{cmd:'ask',payload:{task:t.id},label:'📥 Nhận hồ sơ & đọc yêu cầu'}}],final:null};
  if(t.filed)return {steps:[],final:null};
  const w=W(t),ans=t.ans||{},kind=w.type,ask=`Nộp cho ${c.boss}? Nộp rồi không sửa được nữa.`;
  const file={label:'📤 Nộp hồ sơ',go:{cmd:c.p+'file',payload:{task:t.id},confirm:ask},ready:!t.ready};
  const steps=[];
  if(kind==='sort'){
    const left=(w.items||[]).filter(i=>!(i.id in ans));
    if(left.length)steps.push({ok:null,label:`Xếp thẻ “${cut(left[0].title,30)}”`,go:goto(x,t,'.ow-card','👇 Chọn khay cho thẻ này')});
    return {steps,final:file};
  }
  if(kind==='mark'){
    steps.push({ok:Object.keys(ans).length?true:null,label:'Soát từng chỗ, sửa chỗ sai',go:goto(x,t,'.ow-doc','👇 Chạm chỗ sai để sửa')});
    return {steps,final:file};
  }
  if(kind==='slots'){
    const left=(w.items||[]).filter(i=>!(i.id in ans));
    if(left.length)steps.push({ok:null,label:`Xếp “${cut(left[0].title,30)}”`,go:goto(x,t,'.ow-grid','👇 Chạm một ô trống trên bảng')});
    return {steps,final:file};
  }
  if(kind==='fields')return {steps,final:{label:'📤 Nộp lời nhắn',go:{act:'car:hand',data:{task:t.id}}}};
  if(kind==='seq'){
    if(!orderOf(x,t).length)steps.push({ok:null,label:'Chọn các bước sẽ làm, theo thứ tự',go:goto(x,t,'.ow-pool','👇 Chạm các bước theo thứ tự')});
    return {steps,final:{label:'📤 Chốt các bước',go:{act:'car:hand',data:{task:t.id}}}};
  }
  if(kind==='case'){
    const read=new Set(t.ans?.read||[]),f=(w.facts||[]).find(v=>!read.has(v.id));
    if(f)steps.push({ok:null,label:`Tìm hiểu: ${f.title}`,go:{cmd:c.p+'read',payload:{task:t.id,fact:f.id},label:`🔍 ${x.esc(f.title)}`}});
    else steps.push({ok:null,label:'Chọn cách trả lời',go:goto(x,t,'.ow-answers','👇 Chọn cách trả lời')});
    return {steps,final:null};
  }
  return {steps,final:file};
}

/* ---------------------------------------------------------------- the office desktop */
function currentMail(t,x){
  const form=(x.cc.forms||[]).find(f=>f.id===t.form);
  const chips=[form?`<span class="ok-tag">${x.esc(form.label)}</span>`:'',t.bonus?`<span class="ok-tag good">🎁 Thưởng tới ${x.money(t.bonus)}</span>`:'',
    W(t).twist?'<span class="ok-tag warn">📞 Có thay đổi</span>':''].join('');
  return `<p class="ok-quote">${quoted(x,t.opening)}</p>${t.brief?`<p class="ok-brief">🎯 ${x.esc(t.brief)}</p>`:''}<div class="ok-chips">${chips}</div>`;
}
function lastFiled(x){
  const t=(x.room.tasks||[]).find(v=>v.id===x.ui.okLast);
  return t&&t.filed&&DONE.includes(t.status)?resultView(t,x):'';
}

/** A career module for one Cánh Diều desk. c = {id, p (command prefix), boss, cls, title (rules pane), sum (summary title)}. */
export function officeWork(c){
  bindFormat();
  const strip=(x,t)=>statusStrip(x,t,{boss:c.boss,op:c.p+'overtime'});
  const care=(x,t)=>({people:mateCards(x,{prefix:c.p,t}),track:trackFold(x,{prefix:c.p,career:c.id})});
  const rules=x=>rulesList(x,x.room.data?.today?.rules||[],c.title);
  const send=async(x,cmd,payload)=>x.send(c.p+cmd,payload);
  const taskOf=(x,id)=>(x.room.tasks||[]).find(v=>v.id===id);
  return {
    id:c.id,
    css:true,
    next(t,x){
      try{const n=x&&pending(guideFor(t,x,c).steps);if(n)return stepLine(n);}catch{/* the line below */}
      return t.known?'Làm hồ sơ rồi nộp':'Nhận hồ sơ, đọc yêu cầu';
    },
    job(t,x){
      const unread=openTasks(x).filter(v=>!v.known).length+(x.room.data?.care?.asked?1:0);
      const tabs=[{id:'inbox',icon:'📥',label:'Hộp thư',badge:unread||''},{id:'doc',icon:'📂',label:'Hồ sơ'},{id:'rules',icon:'📋',label:'Quy định'}];
      const inbox=inboxPane(x,{tasks:mails(x,t,currentMail(t,x)),other:dayMails(x,{boss:c.boss,key:`${t.id}:${t.known?1:0}`}),...care(x,t)});
      const gd=guideFor(t,x,c),g=guideOf(x,t,gd.steps,gd.final);
      const ev=deskCard(x,c);
      if(!t.known)return desk(x,t,{cls:`ow ${c.cls}`,tabs,strip:strip(x,t),hint:g.hint,panes:{inbox,rules:rules(x),
        doc:`${ev}<p class="ok-empty"><span aria-hidden="true">✉️</span><b>${x.esc(t.title)}</b><span>Hồ sơ còn trong phong bì.</span></p>`},bar:bar(x,t,'',g.cta,true)});
      const view=VIEW[W(t).type];
      const doc=`${ev}${twistBanner(t,x)}${t.filed?resultView(t,x):view?view(t,x,c):''}${hintBox(t,x,c)}${papersView(t,x)}`;
      const nx=t.filed?'Đã nộp hồ sơ.':t.ready&&W(t).type!=='mark'?t.ready:'';
      return desk(x,t,{cls:`ow ${c.cls}`,tabs,strip:strip(x,t),hint:g.hint,panes:{inbox,rules:rules(x),doc},bar:bar(x,t,x.esc(nx),g.cta)});
    },
    idle(x){
      const d=x.room.data||{};if(!d.office)return '';
      return idleDesk(x,{cls:`ow ${c.cls}`,strip:strip(x,null),recap:deskCard(x,c)+lastFiled(x),tasks:mails(x,null),other:dayMails(x,{boss:c.boss}),rules:rules(x),...care(x,null)});
    },
    summary(data,x){
      if(!data||typeof data!=='object')return '';
      const o=data.office||{},rows=[];
      const row=(k,v)=>rows.push(`<div class="kv-row"><span>${x.esc(k)}</span><b>${x.esc(v)}</b></div>`);
      if(data.mod?.name)row('Hôm nay',`${data.mod.emoji||''} ${data.mod.name}`);
      if(data.filed)row('Hồ sơ đã nộp',`${data.filed} (${data.clean||0} hồ sơ không sai chỗ nào)`);
      if(data.errors)row('Chỗ sai trong ngày',String(data.errors));
      if(o.late)row('Việc nộp trễ hạn',String(o.late));
      if(o.fines)row('Bị trừ tiền',`${o.fines} xu`);
      if(o.overtime)row('Tăng ca','Có (mai vào muộn 30 phút)');
      if(o.carried)row('Việc dở để sáng mai',`${o.carried} (hạn 10:00)`);
      const ch=Number(o.trust_change)||0;
      const trust=o.trust_label?`<p class="ow-sum-trust">👩‍💼 ${x.esc(c.boss)}: <b>${x.esc(o.trust_label)}</b> (${o.trust}/100${ch?`, ${ch>0?'+':''}${ch} hôm nay`:''})</p>`:'';
      const insp=data.inspect?`<p class="ow-sum-audit ${data.inspect.ok?'ok':'bad'}">${data.inspect.ok?'🏅':'🔍'} ${x.esc(data.inspect.text||'')}</p>`:'';
      const dk=typeof data.desk==='string'?`<p class="ow-sum-desk">💬 ${x.esc(data.desk)}</p>`:'';
      const life=careSummary(data.care,x);
      if(!rows.length&&!trust&&!insp&&!life&&!dk)return '';
      return summaryCard(x,data,{cls:'ow-sum',title:x.esc(c.sum),brief:data.filed?`${data.filed} hồ sơ đã nộp`:'',
        body:`${insp}${trust}${dk}${rows.length?`<div class="kv">${rows.join('')}</div>`:''}${life?`<h4 class="section-title">🧭 Đời sống văn phòng</h4><div class="kv">${life}</div>`:''}`});
    },
    tick(root){keepBarAboveFooter(root);},
    actions:{
      tab:switchTab,
      fold:foldToggle,
      goto:gotoAction,
      seen(d,el,x){x.ui.seen=d.key;x.render();},
      card(d,el,x){const t=taskOf(x,d.task);if(!t)return;u(x,t).card=d.card;x.render();},
      async put(d,el,x){const t=taskOf(x,d.task);if(!t)return;u(x,t).card=null;await send(x,'put',{task:d.task,item:d.item,bin:d.bin||null});},
      seg(d,el,x){const t=taskOf(x,d.task);if(!t)return;const s=u(x,t);s.seg=s.seg===d.seg?null:d.seg;x.render();},
      segx(d,el,x){const t=taskOf(x,d.task);if(!t)return;u(x,t).seg=null;x.render();},
      async mark(d,el,x){
        const t=taskOf(x,d.task);if(!t)return;const s=u(x,t),sg=segsOf(W(t)).find(v=>v.id===d.seg),opt=Number(d.opt);s.seg=null;
        if(!sg||(opt===sg.keep&&!(sg.id in (t.ans||{})))||t.ans?.[sg.id]===opt){x.render();return;}
        await send(x,'mark',{task:d.task,seg:d.seg,opt});
      },
      item(d,el,x){const t=taskOf(x,d.task);if(!t)return;u(x,t).item=d.item;x.render();},
      async place(d,el,x){const t=taskOf(x,d.task);if(!t)return;u(x,t).item=null;await send(x,'place',{task:d.task,item:d.item,cell:d.cell});},
      async unplace(d,el,x){await send(x,'place',{task:d.task,item:d.item,cell:null});},
      add(d,el,x){const t=taskOf(x,d.task);if(!t)return;const o=orderOf(x,t);if(!o.includes(d.step))o.push(d.step);x.render();},
      del(d,el,x){const t=taskOf(x,d.task);if(!t)return;orderOf(x,t).splice(Number(d.i),1);x.render();},
      up(d,el,x){const t=taskOf(x,d.task);if(!t)return;const o=orderOf(x,t),i=Number(d.i);if(i>0)[o[i-1],o[i]]=[o[i],o[i-1]];x.render();},
      down(d,el,x){const t=taskOf(x,d.task);if(!t)return;const o=orderOf(x,t),i=Number(d.i);if(i<o.length-1)[o[i+1],o[i]]=[o[i],o[i+1]];x.render();},
      async hand(d,el,x){
        const t=taskOf(x,d.task);if(!t?.work)return;const w=W(t);
        if(w.type==='fields'){
          const fields={};
          for(const f of w.fields||[]){
            const box=document.getElementById(fid(t,f.id)),v=String(box?.value??'').trim();
            if(!v){x.toast(`Còn trống ô “${f.label}”.`,true);if(box){box.scrollIntoView({block:'center'});box.focus({preventScroll:true});}return;}
            fields[f.id]=v;
          }
          if(!await x.ask('Nộp lời nhắn',`Gửi cho ${c.boss}? Nộp rồi không sửa được nữa.`,'Nộp'))return;
          await send(x,'file',{task:t.id,fields,confirm:true});
          return;
        }
        const order=orderOf(x,t);
        if(!order.length){x.toast('Chạm chọn ít nhất một bước trước nhé.',true);return;}
        if(!await x.ask('Chốt các bước',`Làm theo ${order.length} bước này? Chốt rồi không sửa được nữa.`,'Chốt'))return;
        await send(x,'file',{task:t.id,order:[...order],confirm:true});
      },
    },
  };
}
