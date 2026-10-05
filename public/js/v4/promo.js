/** 🎖️ Thăng tiến and 🧑‍💼 Ca quản lý (game/promotion.py → room().promo). Loaded lazily by app.js (L.promo).
 *
 * Two sheets, each one icon, one short line and one obvious button; the explanations sit behind "Xem thêm".
 *   promo    the ladder (title · good days · bar), the review when one is due (two questions, then the pay ask),
 *            and the way into a manager shift from step 3;
 *   manager  the board: tap a job, tap a teammate; check what comes back (✅ / ↩️); settle a small crisis;
 *            close the shift. Every step is a server command (pm_*); the board here only remembers which job
 *            is picked (ui.pmPick). */
import {icon,escapeHTML as esc} from '../icons.js';

const KIND={khach:['🗣️','Khách'],tay:['🔧','Tay nghề'],so:['📋','Giấy tờ'],gap:['⚡','Việc gấp']};
const mood=n=>n>=80?'😊':n>=60?'🙂':n>=40?'😐':'😟';
const head=(title,sub='',eyebrow='')=>`<header class="sheet-head"><div class="grow">${eyebrow?`<span class="eyebrow">${eyebrow}</span>`:''}<h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
const cmd=(label,command,payload={},style='',disabled=false)=>`<button type="button" class="btn ${style}" data-command="${command}" data-payload="${esc(JSON.stringify(payload))}"${disabled?' disabled':''}>${label}</button>`;
const act=(label,action,data={},style='',disabled=false)=>`<button type="button" class="btn ${style}" data-action="${action}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${disabled?' disabled':''}>${label}</button>`;
const bar=(a,b)=>`<div class="bar pm-bar" role="progressbar" aria-valuemin="0" aria-valuemax="${b}" aria-valuenow="${a}"><i style="width:${b?Math.min(100,Math.round(100*a/b)):0}%"></i></div>`;
const room=env=>env.api.state.careers[env.api.state.current];
const place=env=>env.api.content.catalogue?.find(x=>x.id===env.api.state.current)?.short||'';

/** The steps behind "Xem thêm": what each step gives. */
function more(p){
  const emp=p.track==='emp';
  const rows=(p.log||[]).map(x=>`<li>✓ Ngày ${x.d}: bậc ${x.to}</li>`).join('');
  return `<details class="pm-more"><summary>Xem thêm</summary><ul class="pm-rules">
    <li>Ngày tốt: ca thường xong từ 2 việc, đánh giá trong ngày từ ★3.5 nếu có. Nghề văn phòng theo kết quả “ngày chắc tay”; ca quản lý đạt chất lượng từ 60%.</li>
    <li>${emp?'Mỗi bậc: tăng lương 8% → 16% → 25% → 35%.':'Mỗi bậc: khách quen boa thêm 3% → 6% → 9% → 12%.'}</li>
    <li>Bậc 3: mở 🧑‍💼 Ca quản lý${p.track==='own'?' (nhân viên + phụ việc thời vụ)':''}.</li>
    <li>Không bao giờ bị giáng chức. Ngày chưa tốt không cộng ngày tốt và vẫn tính vào tỷ lệ ngày làm.</li>${rows}</ul></details>`;
}

/** The review: one question at a time, then (employees) the pay ask. */
function review(p){
  const d=p.due,dots=`<span class="pm-dots">${Array.from({length:d.of},(_,i)=>`<i class="${i<d.n?'on':''}"></i>`).join('')}</span>`;
  const top=`<p class="pm-eyebrow">${d.who==='Phòng sếp'?'🏢 Phòng sếp':'🏮 Hội buôn phố'} ${dots}</p><h3 class="pm-title">Xét lên ${esc(d.title)}</h3>`;
  if(d.q)return `<article class="pm-card pm-review">${top}<p class="pm-q">${esc(d.q.text)}</p><div class="pm-opts">${d.q.options.map(o=>cmd(esc(o.label),'pm_answer',{question:d.q.id,option:o.id},'pm-opt')).join('')}</div></article>`;
  if(d.ask)return `<article class="pm-card pm-review">${top}<p class="pm-q">💰 Lương mới: <b>${d.pay[0]} → ${d.pay[1]} xu/ngày</b></p><div class="pm-opts">${d.ask.map((a,i)=>cmd(esc(a.label),'pm_ask',{ask:a.id},i===0?'primary':'pm-opt')).join('')}</div>
    <details class="pm-more"><summary>?</summary><p class="small muted">Xin hợp lý, xin cao: được thêm khi trả lời thật tốt. Xin cao mà chưa tốt thì hẹn quý sau.</p></details></article>`;
  return '';
}

export function promoView(env){
  const c=room(env),p=c.promo;
  if(!p)return head('🎖️ Thăng tiến')+`<div class="sheet-body"><p class="muted">Có việc làm rồi mới tính chuyện lên chức nhé.</p></div>`;
  if(p.due)return head('🎖️ Thăng tiến','',esc(place(env)).toUpperCase())+`<div class="sheet-body">${review(p)}</div>`;
  const n=p.next,sh=p.shift;
  const line=n?`${n.good}/${n.need} ngày tốt → ${esc(n.title)}`:'Bậc cao nhất rồi!';
  const lock=n?.requirements?.length?`<ul class="pm-rules">${n.requirements.map(r=>`<li>${r.met?'✓':'🔒'} ${esc(r.label)}</li>`).join('')}</ul>`
    :[n?.why,n?.wait?`Hẹn xét lại sau ${n.wait} ngày làm`:null].filter(Boolean).map(s=>`<p class="pm-lock">🔒 ${esc(s)}</p>`).join('');
  const work=p.rank>=3?'Bạn có thể mở ca quản lý: giao việc cho đội, kiểm tra kết quả và xử lý chuyện trong ca. Mỗi ngày vẫn có thể chọn tự làm ở quầy.'
    :'Công việc ở quầy vẫn như trước. Từ bậc 3, bạn có thêm ca quản lý để giao việc cho đội và kiểm tra kết quả.';
  const benefit=p.track==='emp'?`Thăng chức tăng lương${p.pct?` · hiện tại +${p.pct}%`:''}.`:`Thăng tiến tăng tiền boa từ khách quen${p.pct?` · hiện tại +${p.pct}%`:''}.`;
  let main;
  if(c.open&&sh)main=act('🧑‍💼 Bảng quản lý','pmBoard',{},'primary big full');
  else if(p.mgr&&!c.open)main=act(`🧑‍💼 Mở ca quản lý · ${p.team} người`,'pmStart',{},'primary big full');
  else main=act('Về quầy','close',{},'primary big full');
  const step=`<span class="pm-step">${Array.from({length:p.top},(_,i)=>`<i class="${i<p.rank?'on':''}"></i>`).join('')}</span>`;
  return head('🎖️ Thăng tiến','',esc(place(env)).toUpperCase())+`<div class="sheet-body"><article class="pm-card pm-ladder"><span class="pm-badge" aria-hidden="true">🎖️</span><h3 class="pm-title">${esc(p.title)}</h3>${step}${n?bar(n.good,n.need):''}<p class="pm-line">${line}</p><p class="small">💰 ${benefit}</p><p class="small muted">${work}</p>${lock}${main}${more(p)}</article></div>`;
}

/** The manager's board. */
export function managerView(env){
  const c=room(env),p=c.promo,sh=p?.shift,ui=env.ui;
  if(!sh)return head('🧑‍💼 Ca quản lý')+`<div class="sheet-body"><p class="muted">Chưa có ca quản lý nào đang mở.</p></div>`;
  const eyebrow=esc(place(env)).toUpperCase();
  if(sh.closed){
    const own=p.track==='own';
    return head('🧑‍💼 Chốt ca','',eyebrow)+`<div class="sheet-body"><article class="pm-card pm-done"><span class="pm-badge" aria-hidden="true">${sh.quality>=60?'🎉':'🙂'}</span>
      <div class="pm-stats"><span><b>${sh.good}/${sh.size}</b><small>việc tốt</small></span><span><b>${sh.quality}%</b><small>chất lượng</small></span><span><b>${mood(sh.mood)}</b><small>tinh thần đội</small></span></div>
      <p class="pm-pay">+${sh.bonus} xu ${own?'doanh thu đội':'thưởng quản lý'}${sh.wage?` · −${sh.wage} xu phụ việc`:''}</p>${act('Khép ngày','end',{},'primary big full')}</article></div>`;
  }
  const pick=Number.isInteger(ui.pmPick)&&sh.tasks[ui.pmPick]?.st==='q'?ui.pmPick:null,esc_=sh.esc,busy=!!esc_;
  const team=`<div class="pm-team" role="group" aria-label="Đội">${sh.team.map(m=>{
    const can=pick!=null&&!m.busy&&!m.off&&!busy,fit=pick!=null?(m.s===sh.tasks[pick].kind?' fit':m.w===sh.tasks[pick].kind?' weak':''):'';
    return `<button type="button" class="pm-mate${m.busy?' busy':''}${m.off?' off':''}${fit}" data-action="pmMate" data-i="${m.i}"${can?'':' disabled'}><span class="pm-face" aria-hidden="true">${m.off?'🏠':m.busy?'⏳':mood(m.mood)}</span><b>${esc(m.name)}</b><span class="pm-sw"><i class="s" title="Giỏi: ${KIND[m.s][1]}">${KIND[m.s][0]}</i><i class="w" title="Yếu: ${KIND[m.w][1]}">${KIND[m.w][0]}</i></span></button>`;}).join('')}</div>`;
  const row=t=>{
    const k=KIND[t.kind],who=t.who!=null?sh.team[t.who]?.name:'';
    let right='';
    if(t.st==='q')right=pick===t.i?'<span class="pm-tag sel">👆 Chọn người</span>':'';
    else if(t.st==='w')right=`<span class="pm-tag">⏳ ${esc(who)}</span>`;
    else if(t.st==='d')right=`<span class="pm-check">${cmd('✅','pm_check',{task:t.i,ok:true},'small',busy)}${cmd('↩️','pm_check',{task:t.i,ok:false},'small ghost',busy)}</span>`;
    else right=`<span class="pm-tag ${t.st==='ok'?'good':''}">${t.st==='ok'?'✅':'☑️'}</span>`;
    const body=`<span class="pm-kind" aria-hidden="true">${k[0]}</span><span class="pm-job"><b>${esc(t.t)}</b>${t.st==='d'?`<small class="pm-res${t.bad?' bad':''}">${esc(t.res)} · ${esc(who)}</small>`:t.k?`<small>${esc(t.k)}</small>`:''}</span>`;
    return t.st==='q'?`<li class="pm-row${pick===t.i?' picked':''}"><button type="button" class="pm-pick" data-action="pmPick" data-i="${t.i}"${busy?' disabled':''}>${body}</button>${right}</li>`:`<li class="pm-row st-${t.st}">${body}${right}</li>`;
  };
  const order={d:0,q:1,w:2,ok:3,meh:3},jobs=[...sh.tasks].sort((a,b)=>order[a.st]-order[b.st]||a.i-b.i);
  const crisis=busy?`<article class="pm-card pm-esc" role="alertdialog" aria-label="Gỡ rối"><p class="pm-q">${esc(esc_.text)}</p><div class="pm-opts">${esc_.options.map(o=>cmd(esc(o.label),'pm_fix',{option:o.id},'pm-opt')).join('')}</div></article>`:'';
  const left=sh.tasks.filter(t=>t.st==='q'||t.st==='w'||t.st==='d').length,working=sh.tasks.some(t=>t.st==='w');
  const line=busy?'Gỡ rối trước đã':pick!=null?'Chọn người làm việc này':sh.tasks.some(t=>t.st==='d')?'Kiểm việc: ✅ hay ↩️':left?'Chạm một việc để giao':'Xong hết rồi!';
  const foot=`<footer class="sheet-foot"><p>⭐ ${sh.pts}</p><div class="row wrap">${cmd('⏳ Chờ','pm_wait',{},'ghost',busy||!working)}${cmd('Chốt ca','pm_close',{},left?'ghost':'primary',busy)}</div></footer>`;
  return head('🧑‍💼 Ca quản lý',line,eyebrow)+`<div class="sheet-body pm-board">${crisis}${team}<ul class="pm-jobs">${jobs.map(row).join('')}</ul>
    <details class="pm-more"><summary>Xem thêm</summary><ul class="pm-rules"><li>Giao đúng sở trường (ô xanh): nhanh và ít lỗi.</li><li>Việc trả về có ⚠️: bấm ↩️ để làm lại, được thêm điểm.</li><li>Việc ổn mà trả về: mất thời gian, đội buồn.</li><li>Thưởng = 2 xu × điểm ⭐ (có trần).</li></ul></details></div>`+foot;
}

/** The day summary's line (summaryView). */
export function promoSummary(p){
  const bits=[];
  if(p.manager)bits.push(`🧑‍💼 Ca quản lý: ${p.manager.good}/${p.manager.size} việc tốt · +${p.manager.bonus} xu`);
  if(p.tip)bits.push(`🎖️ Khách quen boa thêm +${p.tip} xu`);
  if(p.line)bits.push(esc(p.line));
  else if(p.next){
    bits.push(`🎖️ ${p.good?'Ngày tốt!':'Hôm nay chưa đạt ngày tốt.'} ${p.next.good}/${p.next.need} → ${esc(p.next.title)}`);
    const blockers=p.next.requirements?.filter(r=>!r.met)||[];
    if(blockers.length)bits.push(...blockers.map(r=>`🔒 ${esc(r.label)}`));
    else if(!p.next.requirements){
      if(p.next.why)bits.push(`🔒 ${esc(p.next.why)}`);
      if(p.next.wait)bits.push(`Hẹn xét lại sau ${p.next.wait} ngày làm`);
    }
  }
  return bits.length?`<div class="notice ${p.line?'success':''}">${icon('star',17)}<div>${bits.map(b=>`<p>${b}</p>`).join('')}${p.line||p.next?`<button type="button" class="btn small" data-action="promo">🎖️ Xem</button>`:''}</div></div>`:'';
}

export async function promoAction(action,data,el,env){
  const {ui,cmd:send,openSheet,toast,renderSheet}=env;
  if(action==='promo'){openSheet('promo');return true;}
  if(action==='pmBoard'){ui.pmPick=null;openSheet('manager');return true;}
  if(action==='pmStart'){const r=await send('start_day',{manager:true});if(r){ui.pmPick=null;ui.task=null;openSheet('manager');}return true;}
  if(action==='pmPick'){const i=Number(data.i);ui.pmPick=ui.pmPick===i?null:i;renderSheet();return true;}
  if(action==='pmMate'){
    if(!Number.isInteger(ui.pmPick)){toast('Chạm một việc trước nhé.','hint');return true;}
    const task=ui.pmPick;ui.pmPick=null;
    if(!await send('pm_assign',{task,mate:Number(data.i)}))ui.pmPick=task;
    renderSheet();return true;
  }
  return false;
}
