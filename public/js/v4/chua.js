/** 🛕 Đi chùa: the quiet acts at chùa Gió Lành, a section of the "Đời thường" sheet (state.chua = chua.public()).
 * Free, a few a day; every rule lives in game/chua.py. Buttons use data-action="lfChua" (life.js lifeAction).
 * An older server sends no `chua`: the section is simply not drawn.
 * 1.4.8: "Vào chùa" opens the walkable pagoda (./chua-visit.js, loaded on the tap); the buttons below it stay as the
 * quick way. A server without the scene's fields (`more`, `khan`, `chant`) gets no way in, only the buttons. */
import {escapeHTML as esc} from '../icons.js';

function gain(a){
  const out=[];
  if(a.spirit)out.push(`<span class="up">tinh thần +${a.spirit}</span>`);
  if(a.wake)out.push(`<span class="up">tỉnh táo +${a.wake}</span>`);
  if(a.full)out.push(`<span class="up">no bụng +${a.full}</span>`);
  return out.join(' · ')||'Không tốn xu';
}
function actButton(a){
  const why=a.done?'Hôm nay làm rồi':a.why;
  return `<button type="button" class="lf-choice has-emoji cg-act" data-action="lfChua" data-act="${esc(a.id)}"${a.ok?'':' disabled'}><span class="lf-ch-emoji" aria-hidden="true">${a.emoji}</span><span class="lf-ch-text"><b>${esc(a.name)}</b><small>${gain(a)}</small>${why?`<em>${esc(why)}</em>`:''}</span></button>`;
}
/** The section, or '' when the server has none (an older build, or outside the story). */
export function chuaSection(C){
  if(!C?.enabled||!Array.isArray(C.acts))return '';
  const wishAct=C.acts.find(a=>a.id==='nguyen');
  const acts=C.acts.filter(a=>a.id!=='nguyen').map(actButton).join('');
  const wishes=wishAct?`<div class="cg-wish"><p class="small"><span aria-hidden="true">${wishAct.emoji}</span> <b>${esc(wishAct.name)}</b> <small class="muted">· tinh thần +${wishAct.spirit}${!wishAct.ok?` · ${esc(wishAct.done?'Hôm nay làm rồi':wishAct.why)}`:''}</small></p><div class="cg-wishes">${(C.wishes||[]).map(w=>`<button type="button" class="btn cream small" data-action="lfChua" data-act="nguyen" data-wish="${esc(w.id)}"${wishAct.ok?'':' disabled'}>${esc(w.text)}</button>`).join('')}</div></div>`:'';
  const day=`${esc(C.label||'')}${C.feast?' · chùa có cơm chay':''}`;
  const list=`<div class="lf-choices grid cg-acts">${acts}</div>${wishes}`;
  const scene=Array.isArray(C.more)&&C.khan&&C.chant;
  return `<h3 class="jr-sub">🛕 Đi chùa Gió Lành <small>· ${day} · còn ${C.left|0}/${C.daily|0} việc hôm nay</small></h3>
    ${scene?`<button type="button" class="cg-enter" data-action="lfChuaVisit"><span class="cg-enter-ico" aria-hidden="true">🛕</span><span class="grow"><b>Vào chùa</b><small>Đi dạo sân chùa, vào chánh điện khấn, tụng kinh cùng thầy</small></span><span aria-hidden="true">›</span></button>
    <details class="cg-quick"><summary>Làm nhanh, không cần vào chùa</summary>${list}</details>`:list}`;
}
