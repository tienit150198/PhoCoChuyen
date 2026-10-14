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
  if(!cards.length)return '<p class="cv-card-empty">Chưa có lời chúc nào.</p>';
  return `<div class="cv-saved"><ol class="cv-card-list">${cards.slice().reverse().map(c=>`<li class="cv-card"><b>${cardText(c,choices)}</b><small>Ngày ${c.day|0}</small></li>`).join('')}</ol></div>`;
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
  return `<div class="cv-card-tabs" role="group" aria-label="Chọn bảng lời chúc"><span class="cv-seg">${[['mine','Của tôi'],['public','Bảng chung']].map(([id,label])=>`<button type="button" class="cv-seg-b${board.tab===id?' on':''}" data-cv="card-tab" data-id="${id}" aria-pressed="${board.tab===id}">${label}</button>`).join('')}</span><button type="button" class="icon-btn small cv-refresh" data-cv="card-refresh" aria-label="Làm mới" title="Làm mới"${board[board.tab].loading?' disabled':''}>↻</button></div>`;
}
export function cardBoardHTML(board,choices,withTabs=true){
  const mine=board.tab==='mine',page=board[board.tab];
  return `<section class="cv-card-board" data-with-tabs="${withTabs}" aria-label="Bảng lời chúc">${withTabs?cardBoardTabs(board):''}
    ${page.error?`<p class="cv-why" role="alert">${esc(page.error)}</p>`:''}${board.busy?'<p class="cv-wait" role="status">Đang cập nhật…</p>':page.loading?'<p class="cv-wait" role="status">Đang tải bảng lời chúc…</p>':''}
    ${!page.rows.length&&!page.loading?`<p class="cv-card-empty">${mine?'Bạn chưa treo lời chúc nào.':'Chưa có lời chúc công khai.'}</p>`:''}
    <ol class="cv-card-list">${page.rows.map(card=>`<li class="cv-card${card.public===true?' is-public':''}" data-card-id="${esc(card.id)}"><b>${cardText(card,choices)}</b><span class="cv-card-foot"><small>Ngày ${card.day|0} · <span aria-hidden="true">${card.public===true?'🌏':'🔒'}</span> <span class="cv-card-privacy">${card.public===true?'Công khai':'Chỉ mình tôi'}</span></small>${mine?`<button type="button" class="btn ghost small" data-cv="card-toggle" data-id="${esc(card.id)}" data-public="${card.public!==true}"${board.busy?' disabled':''}>${board.busy===card.id?'Đang lưu…':card.public===true?'Thôi chia sẻ':'Chia sẻ'}</button>`:''}</span></li>`).join('')}</ol>
    ${page.before?`<button type="button" class="btn ghost small full" data-cv="card-more"${page.loading?' disabled':''}>Xem thêm</button>`:''}</section>`;
}
/** The card, three small steps: who for → what for (only what fits) → the card itself (optional name and message,
 * who may read it). `draft` = {recipient, blessing, name, message, public}; a blessing that does not fit the
 * recipient keeps the send button disabled. */
export function cardComposer(choices,draft={},ok=true,sharing=false){
  const who=choices.recipients.find(x=>x.id===draft.recipient),valid=who?.blessings.includes(draft.blessing);
  const pick=(kind,w,on,off=false)=>`<button type="button" class="cv-pick${on?' on':''}" data-cv="${kind}" data-id="${esc(w.id)}" aria-pressed="${on}"${off?' disabled':''}>${esc(w.text)}</button>`;
  const dots=n=>`<span class="cv-dots" aria-hidden="true">${[1,2,3].map(i=>`<i${i<=n?' class="on"':''}></i>`).join('')}</span>`;
  if(!who)return `<div class="cv-card-compose">${dots(1)}<h4 class="cv-q">Gửi lời chúc cho ai?</h4><div class="cv-chips grid">${choices.recipients.map(w=>pick('card-recipient',w,false,!ok)).join('')}</div></div>`;
  const back=`<button type="button" class="cv-crumb" data-cv="card-back" aria-label="Quay lại">‹</button>`;
  if(!draft.blessing)return `<div class="cv-card-compose">${dots(2)}<h4 class="cv-q">${back}Mong <b>${esc(who.text)}</b>…</h4><div class="cv-chips">${choices.blessings.filter(w=>who.blessings.includes(w.id)).map(w=>pick('card-blessing',w,false,!ok)).join('')}</div></div>`;
  const blessing=choices.blessings.find(x=>x.id===draft.blessing);
  const tag=`<figure class="cv-tag cv-tag-live" aria-label="Xem trước"><span class="cv-tag-knot" aria-hidden="true"></span><b><span>Con cầu mong</span> <span data-tag="who" data-no-translate>${esc(draft.name||'')}</span><span data-tag="who-default"${draft.name?' hidden':''}>${esc(who.text)}</span> <span>${esc(blessing?.text||'…')}.</span> <span data-tag="msg" data-no-translate>${esc(draft.message||'')}</span></b></figure>`;
  const privacy=sharing?`<div class="cv-privacy" role="group" aria-label="Ai có thể đọc bảng này?"><span class="cv-seg"><button type="button" class="cv-seg-b${draft.public!==true?' on':''}" data-cv="card-public" data-public="false" aria-pressed="${draft.public!==true}">🔒 Chỉ mình tôi</button><button type="button" class="cv-seg-b${draft.public===true?' on':''}" data-cv="card-public" data-public="true" aria-pressed="${draft.public===true}">🌏 Công khai</button></span><button type="button" class="icon-btn small cv-q-btn" data-cv="note" aria-label="Giải thích: ai đọc được" aria-expanded="false">?</button></div>
    <p class="cv-card-note" hidden>Mọi người đọc được tên và lời nhắn khi bạn chọn Công khai. Đổi lại được sau khi treo.</p>`:'';
  return `<div class="cv-card-compose">${dots(3)}<div class="cv-q-row">${back}${tag}</div>
    <div class="cv-fields"><label class="cv-card-field"><span>Tên người nhận</span><input name="card-name" data-card-field="name" maxlength="40" value="${esc(draft.name||'')}" autocomplete="off" placeholder="${esc(who.text)}"></label>
    <label class="cv-card-field"><span>Lời nhắn</span><textarea name="card-message" data-card-field="message" maxlength="140" rows="2" placeholder="Không bắt buộc">${esc(draft.message||'')}</textarea></label></div>
    ${privacy}
    <div class="cv-p-acts"><button type="button" class="btn primary big full" data-cv="card-send"${ok&&valid?'':' disabled'}>📜 Treo bảng lời chúc</button></div></div>`;
}

/** A small pagoda for the entry card and the scene's header (theme tokens only). */
export const pagodaArt=(w=56,cls='cg-art')=>`<svg class="${cls}" viewBox="0 0 64 52" width="${w}" height="${Math.round(w*52/64)}" aria-hidden="true" focusable="false"><circle cx="51" cy="12" r="8" fill="var(--star)" opacity=".35"/><rect x="29" y="4" width="6" height="7" rx="2" fill="var(--star)"/><path d="M8 22Q32 6 56 22Q50 21 46 24H18Q14 21 8 22Z" fill="var(--accent)"/><rect x="18" y="24" width="28" height="8" fill="var(--surface)" stroke="var(--line-strong)"/><path d="M2 35Q32 19 62 35Q55 34 50 37H14Q9 34 2 35Z" fill="var(--accent-strong)"/><rect x="12" y="37" width="40" height="13" fill="var(--surface)" stroke="var(--line-strong)"/><path d="M28 50V44a4 4 0 0 1 8 0v6Z" fill="var(--accent-strong)"/><rect x="16" y="41" width="6" height="5" rx="1" fill="var(--star)" opacity=".7"/><rect x="42" y="41" width="6" height="5" rx="1" fill="var(--star)" opacity=".7"/></svg>`;

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
  const day=`${esc(C.label||'')}${C.feast?' · 🍚 cơm chay':''}${C.unlimited?'':` · ${visitStatus(C)}`}`;
  const list=`<div class="lf-choices grid cg-acts">${acts}</div>${wishes}`;
  const scene=Array.isArray(C.more)&&C.khan&&C.chant;
  return `<h3 class="jr-sub">🛕 Chùa Gió Lành <small>· ${day}</small></h3>
    ${scene?`<button type="button" class="cg-enter" data-action="lfChuaVisit">${pagodaArt(56)}<span class="grow"><b>Vào chùa</b><small>Thắp hương · khấn · treo lời chúc</small></span><span class="cg-go" aria-hidden="true">›</span></button>
    <details class="cg-quick"><summary>Làm nhanh</summary>${list}</details>`:list}`;
}
