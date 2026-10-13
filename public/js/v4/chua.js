/** 🛕 Đi chùa: the quiet acts at chùa Gió Lành, a section of the "Đời thường" sheet (state.chua = chua.public()).
 * Free, repeatable when the server advertises unlimited; every rule lives in game/chua.py.
 * An older server sends no `chua`: the section is simply not drawn.
 * 1.4.8: "Vào chùa" opens the walkable pagoda (./chua-visit.js, loaded on the tap); the buttons below it stay as the
 * quick way. A server without the scene's fields (`more`, `khan`, `chant`) gets no way in, only the buttons. */
import {escapeHTML as esc} from '../icons.js';
import {olderRows,olderButton} from '../archive.js';
import {t} from './i18n.js';

export const actionDone=(c,a)=>!!a?.done&&!c?.unlimited;
export const actionWhy=(c,a)=>actionDone(c,a)?'Hôm nay làm rồi':a.why;
export const visitStatus=c=>c.unlimited?`Tinh thần ${Math.max(0,Math.min(100,c.spirit|0))}/100 · có thể làm lại`:`còn ${c.left|0}/${c.daily|0} việc hôm nay`;
/** These private cards come only from the current player's server state. Never interpolate user text as HTML. */
export function cardText(card,choices){
  const who=choices?.recipients?.find(x=>x.id===card.recipient),blessing=choices?.blessings?.find(x=>x.id===card.blessing);
  if(card.wish||!who||!blessing)return esc(t(card.text||''));
  const recipient=card.name?`<span data-no-translate>${esc(card.name)}</span>`:`<span>${esc(t(who.text))}</span>`;
  return `<span>${esc(t('Con cầu mong'))}</span> ${recipient} <span>${esc(t(blessing.text))}.</span>${card.message?` <span data-no-translate>${esc(card.message)}</span>`:''}`;
}
/** Split the server-authored receipt around its exact card quote; never translate user-authored words. */
export function cardResult(message,card,choices){
  const quote=`“${card.text}”`,at=message.indexOf(quote);
  if(at<0)return esc(t(message));
  return `<span>${esc(t(message.slice(0,at)))}</span>“${cardText(card,choices)}”<span>${esc(t(message.slice(at+quote.length)))}</span>`;
}
export function savedCards(cards=[],choices){
  if(!cards.length)return '<p class="cv-card-empty">Chưa có bảng lời chúc. Viết bảng đầu tiên cho người thân nhé.</p>';
  return `<details class="cv-saved" open><summary>Bảng lời chúc của bạn (${cards.length})</summary><ol class="cv-card-list">${cards.slice().reverse().map(c=>`<li class="cv-card"><b>${cardText(c,choices)}</b><small>Ngày ${c.day|0}</small></li>`).join('')}</ol></details>`;
}
export function cardHistory(c){
  const cards=c.cards||[];
  return savedCards([...olderRows('','chua.cards').slice().reverse(),...cards],c.card_choices)+olderButton('','chua.cards',cards.length,cards.length>=40).replace('data-action="loadOlder"','data-cv="older-cards"');
}
export function cardComposer(choices,draft={},ok=true){
  const who=choices.recipients.find(x=>x.id===draft.recipient),valid=who?.blessings.includes(draft.blessing);
  return `<div class="cv-card-compose"><h4 class="cv-q">Gửi lời chúc cho ai?</h4><div class="cv-chips">${choices.recipients.map(w=>`<button type="button" class="cv-pick${w.id===draft.recipient?' on':''}" data-cv="card-recipient" data-id="${esc(w.id)}" aria-pressed="${w.id===draft.recipient}">${esc(w.text)}</button>`).join('')}</div>
    <h4 class="cv-q">Mong điều gì?</h4><div class="cv-chips">${choices.blessings.map(w=>`<button type="button" class="cv-pick${w.id===draft.blessing?' on':''}" data-cv="card-blessing" data-id="${esc(w.id)}" aria-pressed="${w.id===draft.blessing}"${who?.blessings.includes(w.id)?'':' disabled'}>${esc(w.text)}</button>`).join('')}</div>
    <label class="cv-card-field">Tên người nhận (không bắt buộc)<input name="card-name" data-card-field="name" maxlength="40" value="${esc(draft.name||'')}" autocomplete="off"></label>
    <label class="cv-card-field">Lời nhắn (không bắt buộc)<textarea name="card-message" data-card-field="message" maxlength="140" rows="2">${esc(draft.message||'')}</textarea></label>
    <p class="cv-card-note">Chỉ bạn đọc được bảng này. Bảng được giữ lại khi quay về; hàng rào hiển thị 40 bảng gần nhất. Chọn Xem cũ hơn để đọc những bảng trước đó.</p>
    <div class="cv-p-acts"><button type="button" class="btn primary" data-cv="card-send"${ok&&valid?'':' disabled'}>📜 Treo bảng lời chúc</button></div></div>`;
}

export const spiritGain=(c,n)=>c?.unlimited?Math.max(0,Math.min(n,100-(c.spirit|0))):n;
function gain(a,c){
  const out=[];
  if(a.spirit)out.push(`<span class="up">tinh thần +${spiritGain(c,a.spirit)}</span>`);
  if(a.wake)out.push(`<span class="up">tỉnh táo +${a.wake}</span>`);
  if(a.full)out.push(`<span class="up">no bụng +${a.full}</span>`);
  return out.join(' · ')||'Không tốn xu';
}
function actButton(a,c){
  const why=actionWhy(c,a);
  return `<button type="button" class="lf-choice has-emoji cg-act" data-action="lfChua" data-act="${esc(a.id)}"${a.ok?'':' disabled'}><span class="lf-ch-emoji" aria-hidden="true">${a.emoji}</span><span class="lf-ch-text"><b>${esc(a.name)}</b><small>${gain(a,c)}</small>${why?`<em>${esc(why)}</em>`:''}</span></button>`;
}
/** The section, or '' when the server has none (an older build, or outside the story). */
export function chuaSection(C){
  if(!C?.enabled||!Array.isArray(C.acts))return '';
  const wishAct=C.acts.find(a=>a.id==='nguyen');
  const acts=C.acts.filter(a=>a.id!=='nguyen').map(a=>actButton(a,C)).join('');
  const wishes=wishAct?`<div class="cg-wish"><p class="small"><span aria-hidden="true">${wishAct.emoji}</span> <b>${esc(wishAct.name)}</b> <small class="muted">· tinh thần +${spiritGain(C,wishAct.spirit)}${!wishAct.ok?` · ${esc(actionWhy(C,wishAct))}`:''}</small></p><div class="cg-wishes">${(C.wishes||[]).map(w=>`<button type="button" class="btn cream small" data-action="lfChua" data-act="nguyen" data-wish="${esc(w.id)}"${wishAct.ok?'':' disabled'}>${esc(w.text)}</button>`).join('')}</div></div>`:'';
  const day=`${esc(C.label||'')}${C.feast?' · chùa có cơm chay':''}`;
  const list=`<div class="lf-choices grid cg-acts">${acts}</div>${wishes}`;
  const scene=Array.isArray(C.more)&&C.khan&&C.chant;
  return `<h3 class="jr-sub">🛕 Đi chùa Gió Lành <small>· ${day} · ${visitStatus(C)}</small></h3>
    ${scene?`<button type="button" class="cg-enter" data-action="lfChuaVisit"><span class="cg-enter-ico" aria-hidden="true">🛕</span><span class="grow"><b>Vào chùa</b><small>Đi dạo sân chùa, vào chánh điện khấn, tụng kinh cùng thầy</small></span><span aria-hidden="true">›</span></button>
    <details class="cg-quick"><summary>Làm nhanh, không cần vào chùa</summary>${list}</details>`:list}`;
}
