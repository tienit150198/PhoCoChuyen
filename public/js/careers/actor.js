/** 🎬 Hãng phim Bến Mây: read the script page, name the scene, settle the set's awkward demands, then one step of the
 * scene at a time (the lines in order, the mark, the continuity photo, the director's note, the takes left, the stunt's
 * safety order; or the premiere's speech, a reporter's question and what may be posted) and hang the costume on the right
 * hook. The server grades each step (game/careers/actor.py); a wrong one stays open to fix and lowers the scene's quality. */
import {data,person,askCard,introCard,deskCard,kitActions,kitInput,notesPage} from './street_kit.js';
import {current,stepsOf,stepCard,rulesList,statsCard,slipActions,stepsArt} from './slip_kit.js';
import {clean,withArt} from '../ui-kit.js';

const wrap=body=>`<div class="career-job sk slip actor">${body}</div>`;
const STATS={noun:'cảnh',money:'bonus',moneyLabel:'thưởng',master:[90,30],title:'Hành trình ở Bến Mây'};

const notebook=x=>`<details class="sl-notebook"><summary>📒 Sổ tay Hãng phim Bến Mây</summary>${rulesList(x)}</details>`;
const top=x=>`${introCard(x,'dn_intro','🎬')}${deskCard(x,'dn_desk','Chuyện ở trường quay')}`;
const tail=x=>statsCard(x,STATS);

/** The clapperboard filling up: one piece per step of the scene (solid: done, ringed: now, grey: still to do). */
const PIECE={kich_ban:'📜',doan:'💬',thoai:'🗣️',vi_tri:'❌',noi_canh:'📸',chi_dao:'🎬',luot:'🔁',an_toan:'🥋',tra_loi:'🎤',dang:'📋',moc:'👗'};
/** The call sheet: the role, and the scene once it is settled (not before: that is the first step). */
function sceneCard(t,x){
  const n=t.needs||{},known=t.at>0;
  return `<article class="sl-ticket">${withArt(`<small>Phim “Ngõ Nhỏ Có Nắng” · ${x.esc(n.role)}</small>
    <h3><span aria-hidden="true">${known?x.esc(n.emoji):'📜'}</span> ${x.esc(known?n.scene_name:'Trang kịch bản mới')}</h3>
    ${known?`<p class="small">Trang phục treo móc ${x.esc(n.hook)} · thưởng tối đa ${x.fmt(n.bonus||0)} xu.</p>`:'<p class="small">Chưa chốt cảnh: đọc trang kịch bản rồi chốt.</p>'}`,
    stepsArt(t,{kind:'clapper',icons:PIECE,head:'🎬',label:'Bảng clap'}))}</article>`;
}

function slip(t,x){
  const st=current(t);
  if(!st)return `<p class="sl-finished" role="status">✓ Cắt! Đạt · chất lượng ${x.esc(t.quality)}% · thưởng ${x.fmt(t.paid||0)} xu.</p>`;
  return stepCard(x,st,{at:t.at,total:stepsOf(t).length,quality:t.quality??100,cmd:'dn_step',payload:{task:t.id},key:`${t.id}-${st.id}`});
}

export default {
  id:'actor',css:true,
  next(t,x){return x.esc(!t.known?'Đọc trang kịch bản':current(t)?.title||'Đã quay xong');},
  job(t,x){
    if(!data(x).intro||x.ui.intro)return wrap(introCard(x,'dn_intro','🎬'));
    if(!t.known)return wrap(top(x)+askCard(x,t,'Đọc trang kịch bản')+tail(x)+notebook(x));
    return wrap(top(x)+person(x,t,`<p class="small">${x.esc(t.opening)}</p>`)+sceneCard(t,x)+slip(t,x)+
      (t.lines?.length?`<p class="sl-last" role="status">${x.esc(t.lines.at(-1))}</p>`:'')+notebook(x)+tail(x));
  },
  // Compact layout: the notebook folds; the full layout keeps it open.
  idle(x){return wrap(top(x)+tail(x)+(clean()?notebook(x):`<h3 class="sl-rules-h">📒 Sổ tay Hãng phim Bến Mây</h3>${rulesList(x)}`));},
  input(el,x){return kitInput(el,x);},
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'slip actor',eyebrow:'Hãng phim Bến Mây',title:'Sổ tay trường quay',body:rulesList(x)}):'';},
  actions:{...kitActions,...slipActions},
  dock:[['car:notes','book','Sổ tay trường quay','Thoại, dấu đứng, nối cảnh, lượt quay, cảnh hành động an toàn'],['car:intro','question','Giới thiệu nghề','Diễn ít thôi, sống nhiều vào']],
};
