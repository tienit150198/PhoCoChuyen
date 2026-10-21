/** 🚗 Đại lý xe Phố Mây: the morning slip first (match the frame numbers, check the new vehicles, post the prices), then
 * one customer at a time: a sale (needs, licence and budget, honest specs, test drive, registration tax and plate, trả góp
 * through Ngân hàng Phố, papers, hand-over), a trade-in, after-sales or an accessory, one server-graded step at a time
 * (game/careers/car_dealer.py). Other players' cars (🚗 Bảo dưỡng ô tô, game/dealer_service.py) are serviced in the
 * "Xe của người chơi" card. A vehicle for the player is bought in 🚗 Xe & phương tiện (game/garage.py), not here. */
import {data,person,askCard,introCard,deskCard,kitActions,kitInput,notesPage} from './street_kit.js';
import {current,stepsOf,stepCard,rulesList,statsCard,ordersCard,inboxTick,slipActions,stepsArt} from './slip_kit.js';
import {clean,withArt} from '../ui-kit.js';

const wrap=body=>`<div class="career-job sk slip car_dealer">${body}</div>`;
const ORDERS={id:'car_dealer',svcCmd:'dx_svc',attrs:'data-coach="car_dealer-orders"',title:'Xe của người chơi',emoji:'🚗',noun:'Xe',
  empty:'Chưa có xe nào. Người chơi đặt 🚗 Bảo dưỡng ô tô ở 🛎️ Phố dịch vụ; nhận đơn rồi làm ở đây.',
  done:'🚗 Bảo dưỡng xong. Bấm Giao để trả xe cho khách.'};
const STATS={noun:'lượt',money:'earned',moneyLabel:'tiền lời',master:[100,30],title:'Hành trình ở đại lý'};

const notebook=x=>`<details class="sl-notebook"><summary>📒 Sổ tay Đại lý Phố Mây</summary>${rulesList(x)}</details>`;
const top=x=>`${introCard(x,'dx_intro','🚗')}${deskCard(x,'dx_desk','Chuyện ở showroom')}`;
const own='<div class="sl-row dx-own"><button type="button" class="btn ghost small" data-action="inventory">📦 Kho xe</button><button type="button" class="btn ghost small" data-action="garage" data-tab="car">🔑 Mua xe cho mình</button></div>';
const tail=x=>ordersCard(x,ORDERS)+statsCard(x,STATS)+own;

const TOOL={so:'🔢',pdi:'🔧',bang:'🏷️',xe:'🚗',khach:'💬',lai:'🛣️',tien:'🧮',gop:'🏦',giay:'📂',giao:'🔑',gia:'💰',bh:'🛡️',bd:'🛠️',pk:'🎁'};
const KIND={open:['🔐','Nhận lô xe, treo bảng giá','Lô xe sáng nay'],ban:['🚗','Bán xe','Hồ sơ bán xe'],thu_cu:['🔁','Thu xe cũ','Phiếu thu xe'],
  hau_mai:['🔧','Hậu mãi','Phiếu dịch vụ'],pk:['🎁','Phụ kiện','Túi phụ kiện']};
/** The deal on the desk: the vehicle once it is chosen (not before: choosing it is a step), the total and the loan. */
function dealCard(t,x){
  const n=t.needs||{},[emoji,what,label]=KIND[t.kind]||KIND.ban;
  let head=`${emoji} ${what}`,line='';
  if(t.kind==='ban'&&n.model_name){
    head=`${n.emoji||emoji} ${n.model_name}`;
    line=`Giá niêm yết ${x.fmt(n.price)} xu (đã gồm VAT) · trước bạ và biển số nộp hộ${n.loan?' · khách hỏi trả góp':''}`;
  }else if(t.kind==='ban')line='Nghe nhu cầu, bằng lái, ngân sách rồi chọn đúng xe.';
  else if(t.kind==='thu_cu')line=`${n.used||''} · đã dùng ${n.years||0} năm`;
  else if(t.kind==='pk')line=n.item_name?`${n.emoji||''} ${n.item_name}`:'Nghe khách cần gì rồi lấy đúng món.';
  else if(t.kind==='hau_mai')line='Bảo hành đúng chính sách, bảo dưỡng đúng thứ tự.';
  else line='Đầu ngày: chưa đón khách khi chưa xong phiếu này.';
  return `<article class="sl-ticket${t.kind==='open'?' dx-open':''}">${withArt(`<small>${x.esc(what)}</small><h3>${x.esc(head)}</h3><p class="small">${x.esc(line)}</p>`,
    stepsArt(t,{kind:t.kind==='pk'?'bag':t.kind==='open'?'bench':'paper',icons:TOOL,head:emoji,label}))}</article>`;
}

function slip(t,x){
  const st=current(t);
  if(!st)return `<p class="sl-finished" role="status">✓ Xong phiếu · chất lượng ${x.esc(t.quality)}%${t.paid?` · ${x.fmt(t.paid)} xu`:''}.</p>`;
  const out=(t.kind==='ban'||t.kind==='pk')&&t.at===0?`<div class="sl-row">${x.cmd('Hết hàng, hẹn khách','dx_out',{task:t.id},'ghost small')}</div>`:'';
  return stepCard(x,st,{at:t.at,total:stepsOf(t).length,quality:t.quality??100,cmd:'dx_step',payload:{task:t.id},key:`${t.id}-${st.id}`})+out;
}

export default {
  id:'car_dealer',css:true,
  next(t,x){return x.esc(!t.known?'Nghe khách cần gì':current(t)?.title||'Xong phiếu');},
  job(t,x){
    if(!data(x).intro||x.ui.intro)return wrap(introCard(x,'dx_intro','🚗'));
    if(!t.known)return wrap(top(x)+askCard(x,t,'Nghe khách cần gì')+tail(x)+notebook(x));
    const who=t.kind==='open'?'':person(x,t,`<p class="small">${x.esc(t.opening)}</p>`);
    return wrap(top(x)+who+dealCard(t,x)+slip(t,x)+
      (t.lines?.length?`<p class="sl-last" role="status">${x.esc(t.lines.at(-1))}</p>`:'')+notebook(x)+tail(x));
  },
  // Compact layout: the notebook folds; the full layout keeps it open.
  idle(x){return wrap(top(x)+tail(x)+(clean()?notebook(x):`<h3 class="sl-rules-h">📒 Sổ tay Đại lý Phố Mây</h3>${rulesList(x)}`));},
  input(el,x){return kitInput(el,x);},
  meters(root,x){inboxTick(root,x);},
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'slip car_dealer',eyebrow:'Đại lý xe Phố Mây',title:'Sổ tay của đại lý',body:rulesList(x)}):'';},
  actions:{...kitActions,...slipActions},
  dock:[['inventory','box','Kho xe','Nhập xe, phụ kiện'],['car:notes','book','Sổ tay của đại lý','Trước bạ, biển số, trả góp, xe cũ, bảo hành'],['car:intro','question','Giới thiệu nghề','Nghe nhu cầu trước, tư vấn sau']],
};
