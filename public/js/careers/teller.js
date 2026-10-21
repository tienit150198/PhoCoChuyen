/** 🏦 Quầy số 3, Ngân hàng Phố: the float count at opening, one customer at a time (five steps: nhận yêu cầu → kiểm tra
 * thông tin → xử lý tiền → xác nhận → giao biên nhận), the handover at closing. The cash tray totals itself: drag a note
 * (or tap it) into the tray, take one out with −, confirm when the total matches. Before standing alone: three short
 * lessons, the practical exam (three parts), then two shifts with chị Hạnh beside you. The server grades every step.
 * The counter's money is the bank's (nghìn đồng), never the player's xu or own bank account. */
import {data,cc,person,askCard,introCard,deskCard,kitActions,amountBox,kitInput,notesPage,act,dayBar} from './street_kit.js';
import {clean,tip} from '../ui-kit.js';
import {stepsArt} from './slip_kit.js';

const wrap=body=>`<div class="career-job sk teller">${body}</div>`;
const DENOMS=['500','200','100','50','20','10'];
const TRAY_MAX=300;
const stepsOf=t=>t.needs?.steps||[];
const current=t=>stepsOf(t)[t.at];
/** 2350 (nghìn đồng) → "2.350.000đ" */
export const vnd=k=>`${String(Math.round(Number(k)||0)*1000).replace(/\B(?=(\d{3})+(?!\d))/g,'.')}đ`;
const trayOf=(x,key)=>(x.ui.tray??={})[key]??={};
export const trayTotal=tray=>Object.entries(tray||{}).reduce((s,[d,n])=>s+Number(d)*(Number(n)||0),0);
const trayClean=tray=>Object.fromEntries(DENOMS.filter(d=>tray[d]>0).map(d=>[d,tray[d]]));
const busyTask=x=>(x.room.tasks||[]).some(t=>t.status==='in_progress'&&(t.at||0)>0);

/* ---------------------------------------------------------------- drag a note into the tray (touch and mouse) */
let live=null,drag=null,swallow=false;
if(globalThis.document?.addEventListener){
  const D=globalThis.document;
  D.addEventListener('pointerdown',e=>{
    const n=e.target?.closest?.('.teller [data-tl-note]');if(!n||!live)return;
    drag={d:n.dataset.tlNote,key:n.dataset.key,x0:e.clientX,y0:e.clientY,moved:false,ghost:null};
  },true);
  D.addEventListener('pointermove',e=>{
    if(!drag)return;
    if(!drag.moved&&Math.hypot(e.clientX-drag.x0,e.clientY-drag.y0)<8)return;
    drag.moved=true;
    if(!drag.ghost){const g=D.createElement('div');g.className=`tl-ghost n${drag.d}`;g.textContent=drag.d;g.setAttribute('aria-hidden','true');D.body.appendChild(g);drag.ghost=g;}
    drag.ghost.style.transform=`translate(${e.clientX-30}px,${e.clientY-20}px)`;
    const over=D.elementFromPoint(e.clientX,e.clientY)?.closest?.('[data-tl-tray]');
    for(const el of D.querySelectorAll('[data-tl-tray].hot'))if(el!==over)el.classList.remove('hot');
    over?.classList.add('hot');
    if(e.cancelable)e.preventDefault();
  },{capture:true,passive:false});
  const end=e=>{
    if(!drag)return;const d=drag;drag=null;d.ghost?.remove();
    for(const el of D.querySelectorAll('[data-tl-tray].hot'))el.classList.remove('hot');
    if(!d.moved||!live)return;
    swallow=true;setTimeout(()=>{swallow=false;},400);   // the click that follows a drag is not a tap
    const over=e.type==='pointerup'&&D.elementFromPoint(e.clientX,e.clientY)?.closest?.('[data-tl-tray]');
    if(over&&over.dataset.tlTray===d.key){const t=trayOf(live,d.key);t[d.d]=Math.min(TRAY_MAX,(t[d.d]||0)+1);live.render();}
  };
  D.addEventListener('pointerup',end,true);
  D.addEventListener('pointercancel',end,true);
  D.addEventListener('click',e=>{if(swallow&&e.target?.closest?.('[data-tl-note]')){e.preventDefault();e.stopImmediatePropagation();swallow=false;}},true);
}

/* ---------------------------------------------------------------- one step, whatever its type */
function trayStep(st,x,cmd,payload,key){
  const tray=trayOf(x,key),target=Number(st.target)||0,total=trayTotal(tray);
  const pal=(st.palette||DENOMS).map(d=>`<button type="button" class="tl-note n${d}" data-action="car:trayAdd" data-key="${x.esc(key)}" data-d="${d}" data-tl-note="${d}" aria-label="Thêm một tờ ${d} nghìn"><b>${d}</b><small>nghìn</small></button>`).join('');
  const rows=DENOMS.filter(d=>tray[d]>0).map(d=>`<li class="tl-stack"><span class="tl-chip n${d}"><b>${d}</b> × ${tray[d]}</span>
    <span class="tl-stack-btns">${act(x,'−','trayAdd',{key,d,n:-1},'ghost small',` aria-label="Bớt một tờ ${d} nghìn"`)}${act(x,'+10','trayAdd',{key,d,n:10},'ghost small',` aria-label="Thêm một cọc tờ ${d} nghìn"`)}</span></li>`).join('');
  const state=total===target?'ok':total>target?'over':'under';
  const diff=total===target?'✓ Khớp phiếu':total>target?`Thừa ${vnd(total-target)}`:`Còn thiếu ${vnd(target-total)}`;
  const send=x.cmd('✅ Xác nhận khay tiền',cmd,{...payload,step:st.id,value:trayClean(tray)},'primary tl-tray-send',total!==target);
  return `<div class="tl-trayw">
    <div class="tl-palette" role="group" aria-label="Tờ tiền trong két">${pal}</div>
    <div class="tl-tray ${state}" data-tl-tray="${x.esc(key)}" aria-live="polite">
      <div class="tl-total"><span>Khay</span><b>${vnd(total)}</b><span class="tl-need">cần ${vnd(target)}</span></div>
      <p class="tl-diff ${state}">${diff}<span class="tl-machine" title="Máy đếm tiền">🖨️ ${Object.values(tray).reduce((a,b)=>a+b,0)} tờ</span></p>
      ${rows?`<ul class="tl-stacks">${rows}</ul>`:`<p class="tl-empty">${clean()?'Chạm hoặc kéo tờ tiền vào khay.':'Kéo tờ tiền vào khay, hoặc chạm vào tờ tiền. Bấm +10 để thêm một cọc.'}</p>`}
    </div>
    <div class="tl-row">${act(x,'Làm lại','trayClear',{key},'ghost')}${send}</div></div>`;
}

function pickStep(st,x,cmd,payload,key){
  const sel=(x.ui.pick??={})[key];
  const cards=(st.options||[]).map(o=>`<button type="button" class="tl-card${sel===o.id?' on':''}" data-action="car:pick" data-key="${x.esc(key)}" data-id="${x.esc(o.id)}" aria-pressed="${sel===o.id}">
    <span class="tl-face" aria-hidden="true">${x.esc(o.face||'🙂')}</span><b>${x.esc(o.name||o.label)}</b><small>${x.esc(o.detail||'')}</small><small class="tl-tail">TK ${x.esc(o.tail||'')}</small></button>`).join('');
  return `<div class="tl-cards" role="group" aria-label="Danh sách người nhận">${cards}</div>
    <div class="tl-row">${x.cmd('✅ Chọn người này',cmd,{...payload,step:st.id,value:sel||''},'primary tl-pick-send',!sel)}</div>`;
}

function multiStep(st,x,cmd,payload,key){
  const seq=((x.ui.multi??={})[key]||[]).filter(v=>(st.options||[]).some(o=>o.id===v));
  const opts=(st.options||[]).map(o=>{const on=seq.includes(o.id);
    return act(x,`<i class="tl-tick" aria-hidden="true">${on?'✓':''}</i><span>${x.esc(o.label)}</span>`,'multi',{key,id:o.id},`tl-pick${on?' on':''}`,` aria-pressed="${on}"`);}).join('');
  return `${tip('Chạm để chọn hoặc bỏ chọn từng dòng.','','p','small')}<div class="tl-picks">${opts}</div>
    <div class="tl-row">${act(x,'Làm lại','multiClear',{key},'ghost')}${x.cmd('✅ Xác nhận lựa chọn',cmd,{...payload,step:st.id,value:[...seq].sort()},'primary tl-multi-send')}</div>`;
}

function choiceStep(st,x,cmd,payload){
  return `<div class="tl-options">${(st.options||[]).map(o=>x.cmd(x.esc(o.label),cmd,{...payload,step:st.id,value:o.id},'tl-option')).join('')}</div>`;
}

function numberStep(st,x,cmd,payload,key){
  return amountBox(x,`tl-${key}`,0,{min:0,max:10000000,label:'Số ghi vào phiếu',send:'Ghi vào phiếu',cmd,payload:{...payload,step:st.id},field:'value',unit:st.unit||''});
}

/** A step's own list (the float's envelopes, the receipts in the tray) as chips. */
const rowsOf=(st,x)=>st.rows?.length?`<ul class="tl-rows">${st.rows.map(r=>`<li>${x.esc(r)}</li>`).join('')}</ul>`:'';

function stepBody(st,x,cmd,payload,key){
  if(st.type==='tray')return trayStep(st,x,cmd,payload,key);
  if(st.type==='pick')return pickStep(st,x,cmd,payload,key);
  if(st.type==='multi')return multiStep(st,x,cmd,payload,key);
  if(st.type==='number')return numberStep(st,x,cmd,payload,key);
  return choiceStep(st,x,cmd,payload);
}

/* ---------------------------------------------------------------- the customer's papers */
function slipCard(t,x){
  const n=t.needs||{},j=t.job_info?.id;
  if(j==='withdraw'&&n.slip){
    const s=n.slip,c=n.card||{};
    return `<section class="tl-papers" aria-label="Phiếu và giấy tờ">
      <article class="tl-slip"><small>PHIẾU RÚT TIỀN</small><b>${x.esc(s.name)}</b><span class="tl-amt">${x.esc(s.amount_text)}</span>
        ${s.words?`<span class="tl-words">${x.esc(s.words)}</span>`:''}<span class="tl-sign">${s.signed?'✍️ Đã ký':'✍️ …………'}</span></article>
      <article class="tl-idcard"><small>CCCD</small>${c.note?`<span class="tl-face" aria-hidden="true">${x.esc(c.face||'🙂')}</span>`:`<span class="tl-idphoto" aria-hidden="true">${x.portrait(x.npc(t.npc),40)}</span>`}<b>${x.esc(c.name||'')}</b><span>Số ${x.esc(c.no||'')}</span>${c.note?`<em>${x.esc(c.note)}</em>`:''}</article>
      ${s.by?`<p class="tl-note-line">${x.esc(s.by)}</p>`:''}</section>`;
  }
  if(j==='change'&&n.brought){
    const notes=Object.entries(n.brought).sort((a,b)=>Number(b[0])-Number(a[0])).map(([d,k])=>`<span class="tl-chip n${x.esc(d)}"><b>${x.esc(d)}</b> × ${x.esc(k)}</span>`).join('');
    return `<section class="tl-papers"><p class="tl-say">${x.esc(n.ask)}</p><div class="tl-chips" aria-label="Tiền khách đưa">${notes}</div></section>`;
  }
  if(j==='transfer'&&n.ask)return `<section class="tl-papers"><p class="tl-say">${x.esc(n.ask)}</p><p class="tl-photo"><span aria-hidden="true">📱</span> Ảnh trên điện thoại khách: <b class="tl-face">${x.esc(n.photo)}</b></p></section>`;
  if(j==='savings'&&n.arc!==undefined){
    const pct=Math.max(0,Math.min(100,Math.round(100*(n.saved||0)/(n.goal||1))));
    return `<section class="tl-papers tl-arcbox"><p><span aria-hidden="true">${x.esc(n.emoji||'🍵')}</span> <b>Xe trà mới của bà Lựu</b> · ${vnd(n.saved)} / ${vnd(n.goal)}</p><div class="bar"><i style="width:${pct}%"></i></div></section>`;
  }
  if(j==='savings'&&n.goal)return `<section class="tl-papers"><p><span aria-hidden="true">${x.esc(n.emoji)}</span> Mục tiêu: <b>${x.esc(n.goal_text)}</b></p><ul class="tl-facts"><li>Cần ${vnd(n.goal)}</li><li>Đã có ${vnd(n.saved)}</li><li>${x.esc(n.months)} tháng</li></ul></section>`;
  if(j==='atm'&&n.cassettes){
    return `<section class="tl-papers tl-atm" aria-label="Màn hình ATM"><small>🏧 MÀN HÌNH ATM · đầy ${x.esc(n.cap)} tờ / hộp</small><div class="tl-cass">${n.cassettes.map(c=>{
      const pct=Math.round(100*c.left/(n.cap||1));
      return `<div class="tl-cas"><b>Khe ${x.esc(c.id)}</b><span class="tl-chip n${x.esc(c.denom)}">${x.esc(c.denom)}</span><div class="bar ${c.left<n.low?'low':''}"><i style="width:${pct}%"></i></div><small>${x.esc(c.left)} tờ</small></div>`;}).join('')}</div></section>`;
  }
  return '';
}

function stepCard(t,x){
  const st=current(t),steps=stepsOf(t);
  if(!st)return `<p class="tl-finished" role="status">✓ Xong · chất lượng ${x.esc(t.quality)}% · thưởng ${x.fmt(t.paid||0)} xu.</p>`;
  if(data(x).shift?.close?.done)return '<p class="tl-finished" role="status">Đã bàn giao quỹ cuối ca. Khách còn lại để ca sau.</p>';
  return `<section class="card tl-step" aria-labelledby="tl-step-title">
    <p class="tl-step-count" role="status">Bước ${t.at+1}/${steps.length} · chất lượng ${x.esc(t.quality??100)}%</p>
    <progress value="${t.at}" max="${steps.length}" aria-label="Tiến trình giao dịch"></progress>
    <h3 id="tl-step-title">${x.esc(st.title)}</h3><p class="tl-evidence">${x.esc(st.evidence)}</p>${rowsOf(st,x)}
    ${stepBody(st,x,'tl_step',{task:t.id},`${t.id}:${st.id}`)}</section>`;
}

/* ---------------------------------------------------------------- opening float, closing handover */
/** 💼 The float count: on top, before any customer. */
function openCard(x){
  const d=data(x),sh=d.shift||{};
  if(!x.room.open||!sh.open||d.stage==='learn'||sh.open.done)return '';
  const st=sh.open.step;
  return `<section class="card tl-shift" aria-label="Nhận quỹ đầu ca"><h4>💼 Đầu ca · ${x.esc(st.title)}</h4><p class="tl-evidence">${x.esc(st.evidence)}</p>${rowsOf(st,x)}
    ${stepBody(st,x,'tl_shift',{part:'open'},`open:${st.id}`)}</section>`;
}
/** 🧾 The handover: below the customers, folded while some are still waiting. */
function closeCard(x){
  const d=data(x),sh=d.shift||{};
  if(!x.room.open||!sh.open?.done||d.stage==='learn')return '';
  if(sh.close.done)return '<p class="tl-finished small">✓ Đã nhận quỹ đầu ca · ✓ Đã bàn giao cuối ca.</p>';
  if(busyTask(x))return '';
  const st=sh.close.step,left=(x.room.tasks||[]).some(t=>!['completed','referred','cancelled'].includes(t.status));
  return `<details class="card tl-close"${!left||sh.close.at>0?' open':''}><summary>🧾 Cuối ca: bàn giao quỹ (${sh.close.at}/${sh.close.total})</summary>
    <h4>${x.esc(st.title)}</h4><p class="tl-evidence">${x.esc(st.evidence)}</p>${rowsOf(st,x)}${stepBody(st,x,'tl_shift',{part:'close'},`close:${st.id}`)}</details>`;
}
const shiftCard=x=>openCard(x)+closeCard(x);

/* ---------------------------------------------------------------- học việc, thi thực hành, bảng tên */
function learnCard(x){
  const d=data(x),ls=d.lessons||[],next=ls.find(l=>!l.done);
  if(d.stage!=='learn'||!next)return '';
  const done=ls.filter(l=>l.done).map(l=>`<li>✓ ${x.esc(l.title)}</li>`).join('');
  return `<section class="card tl-learn" aria-label="Học việc"><small>🎓 Học việc với chị Hạnh · ${ls.filter(l=>l.done).length}/${ls.length}</small>
    <h3><span aria-hidden="true">${x.esc(next.emoji)}</span> ${x.esc(next.title)}</h3><p>${x.esc(next.text)}</p><p class="tl-ask"><b>${x.esc(next.ask)}</b></p>
    <div class="tl-options">${next.options.map(o=>x.cmd(x.esc(o.label),'tl_learn',{lesson:next.id,answer:o.id},'tl-option tl-lesson-opt')).join('')}</div>
    ${done?`<ul class="tl-done">${done}</ul>`:''}</section>`;
}

function examCard(x){
  const d=data(x);if(d.stage!=='exam')return '';
  const ev=d.exam_view;
  if(ev){
    const st=ev.step;
    return `<section class="card tl-exam" aria-label="Thi thực hành"><div class="tl-exam-head"><small>📝 Thi thực hành · phần ${ev.at+1}/${ev.total}</small>
      <b class="tl-timer" data-started="${x.esc(ev.started)}">⏱️ 0:00</b>${x.cmd('💡 Gợi ý','tl_exam_hint',{},'ghost small tl-hint')}</div>
      <h3>${x.esc(st.title)}</h3><p class="tl-evidence">${x.esc(st.evidence)}</p>${tip('Mỗi phần làm một lần. Xin gợi ý thì mất 🎯.','','p','small')}
      ${stepBody(st,x,'tl_exam',{},`exam:${st.id}`)}</section>`;
  }
  if(d.exam_retry)return `<section class="card tl-exam"><h3>📝 Thi thực hành</h3><p>Hôm nay thi rồi, mai thi lại với đề khác. Khách hôm nay: bấm 👀 Xem chị Hạnh làm để học thêm.</p></section>`;
  return `<section class="card tl-exam"><h3>📝 Thi thực hành</h3><p>Ba phần: đếm và đổi tiền · xác nhận người nhận khi có hai người trùng tên · xử lý chỗ bất thường.</p>
    ${tip(`Qua cả ba phần là nhận bảng tên. Xong trong ${cc(x).exam_fast||150} giây được ⚡, không xin gợi ý được 🎯.`,'','p','small')}
    ${x.cmd('📝 Bắt đầu thi thực hành','tl_exam',{start:true},'primary full tl-exam-go',busyTask(x))}</section>`;
}

function badgeCard(x){
  const d=data(x),b=d.badge,p=d.progress||{};if(!b)return '';
  const name=x.state?.name||'Bạn';
  const extra=(b.fast?'<span title="Thi nhanh">⚡</span>':'')+(b.clean?'<span title="Không cần gợi ý">🎯</span>':'');
  const sub=d.stage==='training'?`Tập sự · ca kèm ${d.training||0}/${p.training||2}`:x.esc(p.title||'Giao dịch viên');
  return `<div class="tl-badge" role="status"><span class="tl-badge-pin" aria-hidden="true">🪪</span><div class="grow"><b>${x.esc(name)}</b><small>Quầy số 3 · ${sub}</small></div>${extra}</div>`;
}

/* ---------------------------------------------------------------- nhánh nghề, xét lên chức, sổ ghi nhận, xe trà */
function reviewCard(x){
  const d=data(x),rv=d.review_view;
  if(rv){const st=rv.step;
    return `<section class="card tl-review" aria-label="Thi lên chức"><small>📝 Thi lên ${x.esc(rv.title)} · phần ${rv.at+1}/${rv.total}</small>
      <h3>${x.esc(st.title)}</h3><p class="tl-evidence">${x.esc(st.evidence)}</p>${stepBody(st,x,'tl_review',{},`review:${st.id}`)}</section>`;}
  if(d.review_ready){const b=(d.progress?.branches||[]).find(r=>r.id===d.branch);
    return `<section class="card tl-review"><h3>📝 Đủ điều kiện thi lên ${x.esc(b?.next?.title||'')}</h3>${x.cmd('📝 Thi lên chức','tl_review',{start:true},'primary full tl-review-go',busyTask(x))}</section>`;}
  return '';
}

function arcCard(x){
  const a=data(x).arc_view;if(!a?.done||a.cup)return '';
  return `<section class="card tl-cart" role="status"><p class="tl-cart-art" aria-hidden="true">🌳🍵☺️</p><h3>Xe trà mới của bà Lựu đã ra phố!</h3>
    <p>Chiếc xe trà inox đứng dưới gốc bàng đầu phố. Bà vẫy bạn qua.</p>${x.cmd('🍵 Nhận ly trà đầu tiên','tl_seen',{},'primary full')}</section>`;
}

function progress(x){
  const d=data(x),p=d.progress||{},st=d.stats||{},rec=d.record||{},a=d.arc_view||{};
  const branches=(p.branches||[]).map(b=>{
    const on=b.id===d.branch,next=b.next;
    const ladder=b.ladder.map((t,i)=>`<li class="${!b.open?'':i<b.rank?'past':i===b.rank?'now':''}">${x.esc(t)}</li>`).join('');
    const need=next?`<small>${Math.min(b.prog,next.need)}/${next.need} ${b.id==='quan_ly'?'lần bàn giao khớp':'việc đạt'}${next.exam?' · có bài xét':''} → ${x.esc(next.title)}</small>`:'<small>Bậc cao nhất của nhánh.</small>';
    const pick=d.stage==='teller'&&!on&&b.open?x.cmd('Theo nhánh này','tl_branch',{branch:b.id},'small ghost'):on?'<span class="tag green">Đang theo</span>':b.open?'':'<small class="muted">Cần Trưởng quầy</small>';
    return `<li class="tl-branch${on?' on':''}"><div class="row spread"><b>${x.esc(b.emoji)} ${x.esc(b.label)}</b>${pick}</div><ol class="tl-ladder">${ladder}</ol>${need}</li>`;}).join('');
  const recs=(cc(x).record||[]).map(r=>`<li><span>${x.esc(r.label)}</span><b>${x.esc(rec[r.id]||0)}</b></li>`).join('');
  const arc=a.total?`<p class="small">🍵 Xe trà của bà Lựu: ${a.done?'đã ra phố':`chặng ${a.stage+1}/${a.total} · ${vnd(a.saved)} / ${vnd(a.goal)}`}</p>`:'';
  return `<details class="tl-progress"><summary>${x.esc(p.title||'')} · ${st.good||0} việc đạt · ${st.active_days||0} ngày</summary>
    ${d.stage==='teller'?`<ul class="tl-branches">${branches}</ul>`:`<p class="small">${x.esc(p.stage_label||'')}: qua thi thực hành và ${p.training||2} ca kèm rồi mới chọn nhánh nghề.</p>`}
    <h4>📒 Sổ ghi nhận</h4><ul class="tl-record">${recs}</ul>${arc}
    <ul class="tl-miles">${(p.milestones||[]).map(m=>`<li><b>${m.achieved?'✓ ':''}${x.esc(m.label)}</b><small>${Math.min(st.good||0,m.jobs)}/${m.jobs} việc · ${Math.min(st.active_days||0,m.days)}/${m.days} ngày</small></li>`).join('')}</ul></details>`;
}

const notebook=x=>`<ul class="tl-rules">${(cc(x).notebook||[]).map(n=>`<li>${x.esc(n)}</li>`).join('')}</ul>`;
const notesFold=x=>`<details class="tl-notebook"><summary>📘 Sổ tay quầy giao dịch</summary>${notebook(x)}</details>`;
const top=x=>`${introCard(x,'tl_intro','🏦')}${deskCard(x,'tl_desk','Chuyện ở quầy')}`;
const onboarding=x=>`${learnCard(x)}${examCard(x)}${badgeCard(x)}${reviewCard(x)}${arcCard(x)}`;

/** The transaction filling up beside the customer (owner 21/10, like the milk-tea cup): one piece per step. */
const DESK={tray:'💵',count:'💵',bundle:'💵',fill:'💵',cash:'💵',money:'💵',receipt:'🧾',check:'🪪',who:'🪪',person:'🪪',confirm:'✍️',
  readback:'✍️',sign:'✍️',next:'🛎️',collect:'📥',advise:'💬',left:'🧮',lost:'🔍',short:'⚠️',settle:'🤝',journal:'📒',low:'🔻',
  seal:'🔒',slot:'🏧',safety:'🔐',clean:'🧹',pending:'📋',power:'🔌',roster:'📋',issue:'⚠️'};
function customer(t,x){
  const d=data(x);
  if(!t.known)return askCard(x,t,'Nhận yêu cầu')+(['learn','exam'].includes(d.stage)?shadowBtn(t,x):'');
  if(['learn','exam'].includes(d.stage))
    return person(x,t,`<p class="small">${x.esc(t.opening)}</p>`)+slipCard(t,x)+`<p class="tl-note-line">${d.stage==='learn'?'Học xong ba bài với chị Hạnh rồi mới đứng quầy.':'Chưa qua thi thực hành: đứng cạnh xem chị Hạnh làm.'}</p>`+shadowBtn(t,x);
  return person(x,t,`<p class="small">${x.esc(t.opening)}</p>`,'',stepsArt(t,{kind:'cash',icons:DESK,head:'🧾',label:'Giao dịch'}))+slipCard(t,x)+stepCard(t,x)+
    (t.lines?.length?`<p class="tl-last" role="status">${x.esc(t.lines.at(-1))}</p>`:'');
}
const shadowBtn=(t,x)=>(t.at||0)>0?'':`<div class="tl-row">${x.cmd('👀 Xem chị Hạnh làm','tl_shadow',{task:t.id},'tl-shadow')}</div>`;

export default {
  id:'teller',css:true,
  next(t,x){const d=data(x);
    if(d.stage==='learn')return 'Học việc với chị Hạnh';
    if(d.stage==='exam')return d.exam_view?'Làm bài thi thực hành':'Thi thực hành';
    if(!d.shift?.open?.done)return 'Nhận quỹ đầu ca';
    return x.esc(!t.known?'Nhận yêu cầu':current(t)?.title||'Đã xong');},
  job(t,x){
    live=x;
    const d=data(x);
    if(!d.intro||x.ui.intro)return wrap(introCard(x,'tl_intro','🏦'));
    const serve=!(d.stage==='learn'||(d.stage==='exam'&&d.exam_view)||(d.stage!=='exam'&&!d.shift?.open?.done&&x.room.open));
    return wrap(top(x)+dayBar(x)+onboarding(x)+openCard(x)+(serve?customer(t,x):'')+closeCard(x)+progress(x)+notesFold(x));
  },
  idle(x){live=x;if(!data(x).intro||x.ui.intro)return wrap(introCard(x,'tl_intro','🏦'));return wrap(top(x)+dayBar(x)+onboarding(x)+shiftCard(x)+progress(x)+(clean()?notesFold(x):notebook(x)));},
  tick(root,x){
    live=x;
    const el=root?.querySelector?.('.tl-timer');
    if(el){const s=Math.max(0,Math.floor((x.now?.()??Date.now()/1000)-Number(el.dataset.started||0)));el.textContent=`⏱️ ${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;}
  },
  input(el,x){return kitInput(el,x);},
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'teller',eyebrow:'Phòng giao dịch Bến Chợ',title:'Sổ tay quầy giao dịch',body:notebook(x)}):'';},
  actions:{...kitActions,
    async trayAdd(d,el,x){
      const t=trayOf(x,d.key),n=Number(d.n||1);
      t[d.d]=Math.max(0,Math.min(TRAY_MAX,(t[d.d]||0)+n));if(!t[d.d])delete t[d.d];x.render();
    },
    async trayClear(d,el,x){(x.ui.tray??={})[d.key]={};x.render();},
    async pick(d,el,x){(x.ui.pick??={})[d.key]=d.id;x.render();},
    async multi(d,el,x){const all=x.ui.multi??={},seq=all[d.key]||[];all[d.key]=seq.includes(d.id)?seq.filter(v=>v!==d.id):[...seq,d.id];x.render();},
    async multiClear(d,el,x){(x.ui.multi??={})[d.key]=[];x.render();},
    async amtSend(d,el,x){
      // Zero can be typed; the server grades the number.
      const raw=x.ui.amt?.[d.key],value=Number(raw===undefined||raw===''?d.def:raw);
      if(!Number.isInteger(value)||value<0||value>10000000){x.toast?.('Nhập số nguyên từ 0 trở lên.');return;}
      await x.send(d.cmd,{...JSON.parse(d.extra||'{}'),[d.field]:value});
    },
  },
  dock:[['car:notes','book','Sổ tay quầy giao dịch','Năm bước, khay tiền, chuyển tiền, ATM, bàn giao'],['car:intro','question','Giới thiệu nghề','Quầy số 3 xin chào!']],
};
