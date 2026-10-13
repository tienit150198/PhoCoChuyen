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
/** Only the authenticated mine endpoint supplies cards eligible for visibility controls. */
export function createCardBoard(api,changed=()=>{}){
  const slot=()=>({rows:[],before:null,loading:false,loaded:false,error:'',request:0});
  const board={tab:'mine',mine:slot(),public:slot(),busy:''};
  board.load=async(scope,more=false)=>{
    if(!['mine','public'].includes(scope))return;
    const page=board[scope];if(more&&(page.loading||!page.before))return;
    const cursor=more?page.before:null,request=++page.request;
    if(!more){page.rows=[];page.before=null;}
    page.loading=true;page.error='';changed(board);
    try{
      const data=await api.json(`/api/chua/cards?scope=${scope}&limit=20${cursor?`&before=${encodeURIComponent(cursor)}`:''}`);
      if(request!==page.request)return;
      const seen=new Set(page.rows.map(row=>row.id));page.rows.push(...data.rows.filter(row=>!seen.has(row.id)));
      page.before=data.before;page.loaded=true;
    }catch(error){if(request===page.request)page.error=error.message||'Chưa tải được bảng lời chúc. Bạn thử lại nhé.';}
    finally{if(request===page.request){page.loading=false;changed(board);}}
  };
  board.setPublic=async(card,value)=>{
    const own=board.mine.rows.find(row=>row.id===card.id);if(!own||board.busy)return false;
    const shown=board.mine.rows.length;
    board.busy=own.id;board.mine.error='';changed(board);
    try{
      const body={id:own.id,public:value===true};if(Number.isInteger(own.position))body.position=own.position;
      await api.post('/api/chua/cards/visibility',body);
      const refreshMine=async()=>{await board.load('mine');while(board.mine.rows.length<shown&&board.mine.before&&!board.mine.error)await board.load('mine',true);};
      await Promise.all([refreshMine(),board.load('public')]);return true;
    }catch(error){board.mine.error=error.message||'Chưa đổi được quyền xem. Bạn thử lại nhé.';return false;}
    finally{board.busy='';changed(board);}
  };
  return board;
}
export function cardBoardTabs(board){
  return `<div class="cv-card-tabs" role="group" aria-label="Chọn bảng lời chúc">${[['mine','Lời chúc của tôi'],['public','Bảng chung']].map(([id,label])=>`<button type="button" class="cv-pick${board.tab===id?' on':''}" data-cv="card-tab" data-id="${id}" aria-pressed="${board.tab===id}">${label}</button>`).join('')}<button type="button" class="btn ghost small" data-cv="card-refresh"${board[board.tab].loading?' disabled':''}>Làm mới</button></div>`;
}
export function cardBoardHTML(board,choices,withTabs=true){
  const mine=board.tab==='mine',page=board[board.tab];
  return `<section class="cv-card-board" data-with-tabs="${withTabs}" aria-label="Bảng lời chúc">${withTabs?cardBoardTabs(board):''}
    <p class="cv-card-note">${mine?'Chỉ bạn có thể đổi quyền xem của những bảng này. Công khai sẽ chia sẻ cả tên và lời nhắn với mọi người.':'Những lời chúc được người viết chọn chia sẻ công khai. Làm mới để xem thay đổi mới nhất.'}</p>
    ${page.error?`<p class="cv-why" role="alert">${esc(page.error)}</p>`:''}${board.busy?'<p class="cv-wait" role="status">Đang cập nhật…</p>':page.loading?'<p class="cv-wait" role="status">Đang tải bảng lời chúc…</p>':''}
    ${!page.rows.length&&!page.loading?`<p class="cv-card-empty">${mine?'Bạn chưa treo bảng lời chúc nào.':'Chưa có lời chúc công khai.'}</p>`:''}
    <ol class="cv-card-list">${page.rows.map(card=>`<li class="cv-card" data-card-id="${esc(card.id)}"><b>${cardText(card,choices)}</b><small>Ngày ${card.day|0} · <span class="cv-card-privacy">${card.public===true?'Công khai':'Chỉ mình tôi'}</span></small>${mine?`<button type="button" class="btn cream small" data-cv="card-toggle" data-id="${esc(card.id)}" data-public="${card.public!==true}"${board.busy?' disabled':''}>${board.busy===card.id?'Đang lưu…':card.public===true?'Chuyển về chỉ mình tôi':'Chia sẻ công khai'}</button>`:''}</li>`).join('')}</ol>
    ${page.before?`<button type="button" class="btn ghost small full" data-cv="card-more"${page.loading?' disabled':''}>Xem thêm lời chúc</button>`:''}</section>`;
}
export function cardComposer(choices,draft={},ok=true,sharing=false){
  const who=choices.recipients.find(x=>x.id===draft.recipient),valid=who?.blessings.includes(draft.blessing);
  return `<div class="cv-card-compose"><h4 class="cv-q">Gửi lời chúc cho ai?</h4><div class="cv-chips">${choices.recipients.map(w=>`<button type="button" class="cv-pick${w.id===draft.recipient?' on':''}" data-cv="card-recipient" data-id="${esc(w.id)}" aria-pressed="${w.id===draft.recipient}">${esc(w.text)}</button>`).join('')}</div>
    <h4 class="cv-q">Mong điều gì?</h4><div class="cv-chips">${choices.blessings.map(w=>`<button type="button" class="cv-pick${w.id===draft.blessing?' on':''}" data-cv="card-blessing" data-id="${esc(w.id)}" aria-pressed="${w.id===draft.blessing}"${who?.blessings.includes(w.id)?'':' disabled'}>${esc(w.text)}</button>`).join('')}</div>
    <label class="cv-card-field">Tên người nhận (không bắt buộc)<input name="card-name" data-card-field="name" maxlength="40" value="${esc(draft.name||'')}" autocomplete="off"></label>
    <label class="cv-card-field">Lời nhắn (không bắt buộc)<textarea name="card-message" data-card-field="message" maxlength="140" rows="2">${esc(draft.message||'')}</textarea></label>
    ${sharing?`<fieldset class="cv-card-visibility"><legend>Ai có thể đọc bảng này?</legend><div class="cv-chips"><button type="button" class="cv-pick${draft.public!==true?' on':''}" data-cv="card-public" data-public="false" aria-pressed="${draft.public!==true}">Chỉ mình tôi</button><button type="button" class="cv-pick${draft.public===true?' on':''}" data-cv="card-public" data-public="true" aria-pressed="${draft.public===true}">Công khai</button></div><p class="cv-card-note">Mọi người có thể đọc tên và lời nhắn khi bạn chọn Công khai. Chỉ mình tôi giữ bảng riêng tư. Bạn có thể đổi lại sau khi treo.</p></fieldset>`:'<p class="cv-card-note">Chỉ bạn đọc được bảng này. Bảng được giữ lại khi quay về; hàng rào hiển thị 40 bảng gần nhất. Chọn Xem cũ hơn để đọc những bảng trước đó.</p>'}
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
