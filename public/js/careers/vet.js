/** 🩺 Phòng khám Thú y Cỏ May: listen to the owner, settle the case, settle their awkward demands, then one step of the
 * case at a time (weigh, take the temperature, work out the dose, the procedure in order, what to tell the owner), and
 * hand the right pet back. The server grades each step (game/careers/vet.py); a wrong one stays open to fix and lowers
 * the case's quality. Other players' pets (🩺 Khám, 💉 Tiêm, game/vet_service.py) are seen in the "Bé của người chơi" card. */
import {data,person,askCard,introCard,deskCard,kitActions,kitInput,notesPage} from './street_kit.js';
import {current,stepsOf,stepCard,rulesList,statsCard,ordersCard,inboxTick,slipActions} from './slip_kit.js';
import {clean} from '../ui-kit.js';

const wrap=body=>`<div class="career-job sk slip vet">${body}</div>`;
const ORDERS={id:'vet',svcCmd:'ty_svc',attrs:'data-coach="vet-orders"',title:'Bé của người chơi',emoji:'🐾',noun:'Bé',
  empty:'Chưa có bé nào. Người chơi đặt 🩺 Khám hoặc 💉 Tiêm cho thú cưng ở 🛎️ Phố dịch vụ; nhận đơn rồi khám ở đây.',
  done:'🩺 Khám xong. Bấm Giao để trả bé cho chủ.'};
const STATS={noun:'ca',money:'bonus',moneyLabel:'thưởng',master:[90,30],title:'Hành trình ở Cỏ May'};

const notebook=x=>`<details class="sl-notebook"><summary>📒 Sổ tay phòng khám Cỏ May</summary>${rulesList(x)}</details>`;
const top=x=>`${introCard(x,'ty_intro','🩺')}${deskCard(x,'ty_desk','Chuyện ở phòng khám')}`;
const tail=x=>ordersCard(x,ORDERS)+statsCard(x,STATS);
const KIND={dog:'🐶',cat:'🐱'};

/** The case card: the pet, and the case once it is settled (not before: that is the first step). */
function caseCard(t,x){
  const n=t.needs||{},known=t.at>0;
  return `<article class="sl-ticket"><small>Chuồng ${x.esc(n.cage)} · ${x.esc(n.collar)}</small>
    <h3><span aria-hidden="true">${known?x.esc(n.emoji):KIND[n.pet_kind]||'🐾'}</span> ${x.esc(known?n.case_name:`Bé ${n.pet}`)}</h3>
    ${known?`<p class="small">Bé ${x.esc(n.pet)} · ${x.esc(n.what)}</p>`:`<p class="small">${x.esc(n.what)} · chưa chốt bệnh: nghe chủ kể, khám rồi chốt.</p>`}</article>`;
}

function slip(t,x){
  const st=current(t);
  if(!st)return `<p class="sl-finished" role="status">✓ Đã trả bé · chất lượng ${x.esc(t.quality)}% · thưởng ${x.fmt(t.paid||0)} xu.</p>`;
  return stepCard(x,st,{at:t.at,total:stepsOf(t).length,quality:t.quality??100,cmd:'ty_step',payload:{task:t.id},key:`${t.id}-${st.id}`});
}

export default {
  id:'vet',css:true,
  next(t,x){return x.esc(!t.known?'Nghe chủ kể bệnh':current(t)?.title||'Đã trả bé');},
  job(t,x){
    if(!data(x).intro||x.ui.intro)return wrap(introCard(x,'ty_intro','🩺'));
    if(!t.known)return wrap(top(x)+askCard(x,t,'Nghe chủ kể bệnh')+tail(x)+notebook(x));
    return wrap(top(x)+person(x,t,`<p class="small">${x.esc(t.opening)}</p>`)+caseCard(t,x)+slip(t,x)+
      (t.lines?.length?`<p class="sl-last" role="status">${x.esc(t.lines.at(-1))}</p>`:'')+notebook(x)+tail(x));
  },
  // Compact layout: the notebook folds; the full layout keeps it open.
  idle(x){return wrap(top(x)+tail(x)+(clean()?notebook(x):`<h3 class="sl-rules-h">📒 Sổ tay phòng khám Cỏ May</h3>${rulesList(x)}`));},
  input(el,x){return kitInput(el,x);},
  meters(root,x){inboxTick(root,x);},
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'slip vet',eyebrow:'Phòng khám Thú y Cỏ May',title:'Sổ tay phòng khám',body:rulesList(x)}):'';},
  actions:{...kitActions,...slipActions},
  dock:[['car:notes','book','Sổ tay phòng khám','Cân bé, thân nhiệt, liều theo cân, dịch truyền, nhịn ăn trước mổ'],['car:intro','question','Giới thiệu nghề','Cân trước, tính liều sau, nói thật với chủ']],
};
