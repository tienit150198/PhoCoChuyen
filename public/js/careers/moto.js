/** 🏍️ Tiệm sửa xe Út Lanh: listen to the customer, settle the fault, settle their awkward demands, then one step of the
 * ticket at a time (tyre pressure, oil, plugs, chain, brakes, lights, battery, a flooded bike), and hand the right bike
 * back. The server grades each step (game/careers/moto.py); a wrong one stays open to fix and lowers the ticket's quality.
 * Other players' bikes (🔧 Bảo dưỡng xe máy, game/moto_service.py) are worked in the "Xe của người chơi" card. */
import {data,person,askCard,introCard,deskCard,kitActions,kitInput,notesPage} from './street_kit.js';
import {current,stepsOf,stepCard,rulesList,statsCard,ordersCard,inboxTick,slipActions} from './slip_kit.js';
import {clean} from '../ui-kit.js';

const wrap=body=>`<div class="career-job sk slip moto">${body}</div>`;
const ORDERS={id:'moto',svcCmd:'xm_svc',attrs:'data-coach="moto-orders"',title:'Xe của người chơi',emoji:'🏍️',noun:'Xe',
  empty:'Chưa có xe nào. Người chơi đặt 🔧 Bảo dưỡng xe máy ở 🛎️ Phố dịch vụ; nhận đơn rồi làm ở đây.',
  done:'🔧 Bảo dưỡng xong. Bấm Giao để trả xe cho khách.'};
const STATS={noun:'xe',money:'earned',moneyLabel:'tiền công',master:[100,30],title:'Hành trình ở tiệm'};

const notebook=x=>`<details class="sl-notebook"><summary>📒 Sổ tay tiệm Út Lanh</summary>${rulesList(x)}</details>`;
const top=x=>`${introCard(x,'xm_intro','🏍️')}${deskCard(x,'xm_desk','Chuyện ở tiệm')}`;
const tail=x=>ordersCard(x,ORDERS)+statsCard(x,STATS);

/** The ticket on the handlebar: the bike, and the fault once it is settled (not before: that is the first step). */
function ticketCard(t,x){
  const n=t.needs||{},known=t.at>0;
  return `<article class="sl-ticket"><small>Phiếu ${x.esc(n.tag)} · biển ${x.esc(n.plate)}</small>
    <h3><span aria-hidden="true">${known?x.esc(n.emoji):'🏍️'}</span> ${x.esc(known?n.fault_name:`${n.bike} màu ${n.color}`)}</h3>
    ${known?`<p class="small">${x.esc(n.bike)} màu ${x.esc(n.color)} · phụ tùng tiệm ứng ${x.fmt(n.cost||0)} xu, trừ khi giao xe.</p>`:'<p class="small">Chưa chốt lỗi: nghe khách, nhìn xe rồi chốt.</p>'}</article>`;
}

function slip(t,x){
  const st=current(t);
  if(!st)return `<p class="sl-finished" role="status">✓ Đã giao xe · chất lượng ${x.esc(t.quality)}% · tiền công ${x.fmt(t.paid||0)} xu.</p>`;
  return stepCard(x,st,{at:t.at,total:stepsOf(t).length,quality:t.quality??100,cmd:'xm_step',payload:{task:t.id},key:`${t.id}-${st.id}`});
}

export default {
  id:'moto',css:true,
  next(t,x){return x.esc(!t.known?'Nghe khách tả bệnh xe':current(t)?.title||'Đã giao xe');},
  job(t,x){
    if(!data(x).intro||x.ui.intro)return wrap(introCard(x,'xm_intro','🏍️'));
    if(!t.known)return wrap(top(x)+askCard(x,t,'Nghe khách tả bệnh xe')+tail(x)+notebook(x));
    return wrap(top(x)+person(x,t,`<p class="small">${x.esc(t.opening)}</p>`)+ticketCard(t,x)+slip(t,x)+
      (t.lines?.length?`<p class="sl-last" role="status">${x.esc(t.lines.at(-1))}</p>`:'')+notebook(x)+tail(x));
  },
  // Compact layout: the notebook folds; the full layout keeps it open.
  idle(x){return wrap(top(x)+tail(x)+(clean()?notebook(x):`<h3 class="sl-rules-h">📒 Sổ tay tiệm Út Lanh</h3>${rulesList(x)}`));},
  input(el,x){return kitInput(el,x);},
  meters(root,x){inboxTick(root,x);},
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'slip moto',eyebrow:'Tiệm sửa xe Út Lanh',title:'Sổ tay của tiệm',body:rulesList(x)}):'';},
  actions:{...kitActions,...slipActions},
  dock:[['car:notes','book','Sổ tay của tiệm','Áp suất lốp, nhớt, bugi, sên, phanh, ắc quy, xe ngập'],['car:intro','question','Giới thiệu nghề','Nghe bệnh trước, cầm cờ lê sau']],
};
