/** 🎖️ Cấp bậc & chức vụ (game/org.py → room().promo.org), shown in the promo sheet (v4/promo.js) for a career on an
 * org ladder. Phone first, few words: the shoulder board, grade · post, ⚠️ n/3, ★ and Liêm chính, one bar to the next
 * step and one main button; the warnings' history, the requirements and the whole ladder sit behind "Xem thêm".
 *   orgView(env, head, act, cmd)   the sheet (the interview or course exam in place when one is due)
 *   warnChip(org)                  "⚠️ 2/3" for the morning strip and the shift header
 *   inspView(of, org, cmd)         🔎 kiểm tra điều lệnh, the Trợ lý BGĐ's tab in the office */
import {escapeHTML as esc} from '../icons.js';
import {boardSVG,badgeSVG} from './insignia.js';

const bar=(a,b)=>`<div class="bar pm-bar" role="progressbar" aria-valuemin="0" aria-valuemax="${b}" aria-valuenow="${a}"><i style="width:${b?Math.min(100,Math.round(100*a/b)):0}%"></i></div>`;
const st=n=>n==null?'—':(n/10).toFixed(1);
export const warnChip=o=>o?`<span class="og-warn${o.warns.length?' on':''}" title="Cảnh cáo">⚠️ ${o.warns.length}/${o.warn_max}</span>`:'';

function due(o,act){
  const d=o.due,dots=`<span class="pm-dots">${Array.from({length:d.of},(_,i)=>`<i class="${i<d.n?'on':''}"></i>`).join('')}</span>`;
  const top=`<p class="pm-eyebrow">${d.k==='course'?'📚 Bài kiểm tra cuối khóa':'🏛️ Ban chỉ huy'} ${dots}</p><h3 class="pm-title">${esc(d.title)}</h3>`;
  if(!d.q)return '';
  return `<article class="pm-card pm-review">${top}<p class="pm-q">${esc(d.q.text)}</p><div class="pm-opts">${d.q.options.map(x=>act(esc(x.label),'pmAnswer',{question:d.q.id,option:x.id},'pm-opt')).join('')}</div>
    <details class="pm-more"><summary>?</summary><p class="small muted">Câu 0 điểm: hẹn xét lại sau 3 ngày làm.</p></details></article>`;
}
/** What still holds the next step back, on the card itself (not only under "Xem thêm": feedback #251, a full bar with a
 * 🔒 hidden below read as "everything met"). The bar already counts the days; a suspension is the card's line. */
function missing(n){
  const left=(n?.requirements||[]).filter(r=>!r.met&&r.id!=='days'&&r.id!=='susp');
  if(!n)return '';
  if(!left.length)return n.good>=n.need?`<p class="small og-todo">✅ Đủ điều kiện: cuối ca Ban chỉ huy xét.</p>`:'';
  return `<ul class="pm-rules og-todo">${left.slice(0,3).map(r=>`<li class="bad">🔒 ${esc(r.label)}</li>`).join('')}</ul>`;
}
function rows(list){return `<ul class="pm-rules">${(list||[]).map(r=>`<li>${r.met?'✓':'🔒'} ${esc(r.label)}</li>`).join('')}</ul>`;}
function more(o,cmd){
  const warns=o.warns.length?`<p class="pm-eyebrow">⚠️ Cảnh cáo đang có</p><ul class="pm-rules">${o.warns.map(w=>`<li class="bad">⚠️ ${esc(w.why)}<small class="pm-hint">📖 ${esc(w.how)}</small></li>`).join('')}</ul>
    <p class="small muted">🧽 ${Math.min(o.clean,o.decay)}/${o.decay} ngày làm không vi phạm → xóa hết cảnh cáo. Có vi phạm mới thì đếm lại từ 0. Lần thứ 4: hạ 1 bậc hàm.</p>`:'';
  const hist=o.wlog.length?`<p class="pm-eyebrow">📜 Lịch sử</p><ul class="pm-rules">${o.wlog.map(w=>`<li>${esc(w.k)}${w.why?` · ${esc(w.why)}`:''}<small class="pm-hint">Ngày ${w.d}</small></li>`).join('')}</ul>`:'';
  const ng=o.next_grade?`<p class="pm-eyebrow">⭐ Lên ${esc(o.next_grade.name)}</p>${rows(o.next_grade.rows)}`:'';
  const np=o.next_post?`<p class="pm-eyebrow">🪑 Bổ nhiệm ${esc(o.next_post.short)}</p>${rows(o.next_post.rows)}`:'';
  const aims=o.aims.length>1?`<div class="row wrap og-aims">${o.aims.map(a=>cmd(`🧭 ${esc(a.short)}`,'pm_org_aim',{post:a.id},`small ${a.id===o.aim?'primary':'ghost'}`,a.id===o.aim)).join('')}</div>`:'';
  const ladder=`<ol class="og-ladder">${o.ladder.map(g=>`<li class="${g.on?'on':''}">${boardSVG(g.ins,44)}<span>${esc(g.name)}</span></li>`).join('')}</ol>`;
  const mark=o.mark.on?`<p class="small bad">💵 Dấu liêm chính${o.mark.self?' (đã tự giác)':''}: không bổ nhiệm Trợ lý BGĐ, Phó Giám đốc, không lên Đại tá.</p>`:'';
  return `<details class="pm-more"><summary>Xem thêm</summary>${warns}${ng}${np}${aims}${mark}${hist}${ladder}
    <ul class="pm-rules"><li>Vi phạm quy trình: cảnh cáo. ${o.decay||10} ngày làm không vi phạm: xóa hết. Lần 4: hạ 1 bậc hàm.</li><li>Nhận phong bì: hạ bậc ngay, ghi dấu liêm chính mãi mãi.</li><li>${esc(o.boss)}: không bổ nhiệm người chơi.</li></ul></details>`;
}
export function orgView(env,head,act,cmd,place){
  const c=env.api.state.careers[env.api.state.current],p=c.promo,o=p.org;
  if(o.due)return head('🎖️ Cấp bậc','',place)+`<div class="sheet-body">${due(o,act)}</div>`;
  const n=p.next,of=p.office,todo=of?.inbox?.length||0;
  const line=o.susp?`⛔ Tạm đình chỉ: còn ${o.susp} ngày`:n?`${n.good}/${n.need} ngày → ${esc(n.title)}`:'Cao nhất rồi!';
  const own=o.own?cmd('🙇 Tự giác nộp lại phong bì','pm_org_own',{},'primary big full'):'';
  const office=of?act(`🏢 ${esc(of.name)}${todo?` · ${todo}`:''}`,'pmOffice',{},`${own?'':'primary '}big full`):'';
  const main=own||office||act('Về ca','close',{},'primary big full');
  return head('🎖️ Cấp bậc','',place)+`<div class="sheet-body"><article class="pm-card og-card">
    <div class="og-top">${badgeSVG(34)}${boardSVG(o.grade.ins,120,o.grade.name)}</div>
    <h3 class="pm-title">${esc(o.grade.name)}</h3><p class="og-post">${esc(o.post.short)}</p>
    <p class="og-stats">${warnChip(o)}<span>★ ${st(o.stars)}</span><span>🛡️ ${o.liem}</span>${o.mark.on?'<span class="bad">💵</span>':''}</p>
    ${n&&!o.susp?bar(n.good,n.need):''}<p class="pm-line">${line}</p>${o.susp?'':missing(n)}${main}${own&&office?office:''}${more(o,cmd)}</article></div>`;
}

/* ------------------------------------------------------------------ 🔎 kiểm tra điều lệnh (Trợ lý BGĐ) */
export function inspView(o,cmd){
  const ins=o?.insp;if(!ins)return `<p class="of-empty">Mở ca để kiểm tra.</p>`;
  const picked=ins.units.filter(u=>u.on).length;
  if(picked<2)return `<p class="of-left">📋 Chọn 2 đơn vị (${picked}/2)</p><div class="og-units">${ins.units.map(u=>cmd(`${esc(u.name)}${u.hot?' · 📣 nhiều phản ánh':''}`,'pm_of_insp',{op:'pick',unit:u.i},`${u.on?'primary':'ghost'} full`,u.on)).join('')}</div>`;
  const todo=ins.rows.findIndex(r=>!r.gr||r.arts.some(a=>a.m==null));   // one member open at a time (few words on screen)
  const rowsHTML=ins.rows.map((r,i)=>`<details class="pm-card og-member"${i===todo?' open':''}><summary><b>${esc(r.n)}</b> <small>${esc(r.unit)} · ${r.arts.filter(a=>a.m!=null).length}/3${r.gr?' ✓':''}</small></summary><ul class="og-arts">${r.arts.map((a,k)=>`<li><span><b>${a.e} ${esc(a.name)}</b><small>${esc(a.text)}</small></span>
      <span class="og-mark">${ins.sent?`${a.m===a.truth?'✅':'❌'}`:cmd('Đạt','pm_of_insp',{op:'mark',row:r.i,a:k,v:false},`small ${a.m===false?'primary':'ghost'}`)+cmd('Vi phạm','pm_of_insp',{op:'mark',row:r.i,a:k,v:true},`small ${a.m===true?'primary':'ghost'}`)}</span></li>`).join('')}</ul>
      ${ins.sent?'':`<div class="row wrap og-grades">${ins.grades.map(g=>cmd(esc(g.label.replace(' nhiệm vụ','')),'pm_of_insp',{op:'grade',row:r.i,g:g.id},`small ${r.gr===g.id?'primary':'ghost'}`)).join('')}</div>`}</details>`).join('');
  const ready=ins.rows.every(r=>r.gr&&r.arts.every(a=>a.m!=null));
  return rowsHTML+(ins.sent?`<p class="of-empty">📤 Đã trình PGĐ · đúng ${ins.score}%</p>`:cmd('📤 Trình PGĐ','pm_of_insp',{op:'send'},`${ready?'primary':'ghost'} big full`,!ready));
}
