/** 🎤 Phòng trà Mây Chiều: hear what the room wants, name the set, settle the guests' awkward demands, then one step of
 * the turn at a time (warm up in order, pick the song from the tea room's songbook, the sound check, the minutes left, a
 * request slip, an incident on stage, the encore) and read the dedication to the right table. The server grades each
 * step (game/careers/singer.py); a wrong one stays open to fix and lowers the set's quality. */
import {data,person,askCard,introCard,deskCard,kitActions,kitInput,notesPage} from './street_kit.js';
import {current,stepsOf,stepCard,rulesList,statsCard,slipActions,stepsArt} from './slip_kit.js';
import {clean,withArt} from '../ui-kit.js';

const wrap=body=>`<div class="career-job sk slip singer">${body}</div>`;
const STATS={noun:'lượt',money:'bonus',moneyLabel:'thưởng',master:[90,30],title:'Hành trình ở Mây Chiều'};

const notebook=x=>`<details class="sl-notebook"><summary>📒 Sổ tay Phòng trà Mây Chiều</summary>${rulesList(x)}</details>`;
const top=x=>`${introCard(x,'cs_intro','🎤')}${deskCard(x,'cs_desk','Chuyện ở phòng trà')}`;
const tail=x=>statsCard(x,STATS);

/** The stage lighting up: one piece per step of the turn (solid: done, ringed: now, grey: still to do). */
const PIECE={phong:'🪑',khach:'💬',khoi_dong:'🫁',bai:'🎼',chinh:'🎚️',con_lai:'⏱️',giay:'📝',xu_ly:'🛠️',encore:'👏',ban:'💐'};
/** The song slip on the mic stand: the table, and the set once it is settled (not before: that is the first step). */
function setCard(t,x){
  const n=t.needs||{},known=t.at>0;
  return `<article class="sl-ticket">${withArt(`<small>Bàn ${x.esc(n.table)} · ${x.esc(n.guest)}</small>
    <h3><span aria-hidden="true">${known?x.esc(n.emoji):'🎤'}</span> ${x.esc(known?n.set_name:'Khán phòng đang chờ')}</h3>
    ${known?`<p class="small">Lời chúc tặng ${x.esc(n.to)} · thưởng tối đa ${x.fmt(n.bonus||0)} xu.</p>`:'<p class="small">Chưa chốt kiểu hát: nhìn khán phòng rồi chốt.</p>'}`,
    stepsArt(t,{kind:'stage',icons:PIECE,head:'🎤',label:'Sân khấu'}))}</article>`;
}

function slip(t,x){
  const st=current(t);
  if(!st)return `<p class="sl-finished" role="status">✓ Hết lượt · chất lượng ${x.esc(t.quality)}% · thưởng ${x.fmt(t.paid||0)} xu.</p>`;
  return stepCard(x,st,{at:t.at,total:stepsOf(t).length,quality:t.quality??100,cmd:'cs_step',payload:{task:t.id},key:`${t.id}-${st.id}`});
}

export default {
  id:'singer',css:true,
  next(t,x){return x.esc(!t.known?'Nghe khách muốn nghe gì':current(t)?.title||'Đã hết lượt');},
  job(t,x){
    if(!data(x).intro||x.ui.intro)return wrap(introCard(x,'cs_intro','🎤'));
    if(!t.known)return wrap(top(x)+askCard(x,t,'Nghe khách muốn nghe gì')+tail(x)+notebook(x));
    return wrap(top(x)+person(x,t,`<p class="small">${x.esc(t.opening)}</p>`)+setCard(t,x)+slip(t,x)+
      (t.lines?.length?`<p class="sl-last" role="status">${x.esc(t.lines.at(-1))}</p>`:'')+notebook(x)+tail(x));
  },
  // Compact layout: the notebook folds; the full layout keeps it open.
  idle(x){return wrap(top(x)+tail(x)+(clean()?notebook(x):`<h3 class="sl-rules-h">📒 Sổ tay Phòng trà Mây Chiều</h3>${rulesList(x)}`));},
  input(el,x){return kitInput(el,x);},
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'slip singer',eyebrow:'Phòng trà Mây Chiều',title:'Sổ tay phòng trà',body:rulesList(x)}):'';},
  actions:{...kitActions,...slipActions},
  dock:[['car:notes','book','Sổ tay phòng trà','Khởi động, sổ hợp âm, thử âm, giờ lượt hát, sự cố'],['car:intro','question','Giới thiệu nghề','Hát cho người ngồi trước mặt mình']],
};
