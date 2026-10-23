/** One explicit source per purchase; changing it here never changes the saved bank preference. */
import {personalPayment,paymentText,paymentMoney} from './money.js';
import {noAsk} from './no-ask.js';
export function paymentChoices(J,cost,joint=null,{noJoint=false,noCredit=false,extraSources=[]}={}){
  const b=J?.bank,c=b?.card;
  const option=(id,label,balance,exists=true,why='')=>({id,label,balance:Number(balance)||0,ok:exists&&!why&&(!(cost>0)||Number(balance)>=cost),why:why||(!exists?'Chưa có nguồn tiền này.':cost>0&&Number(balance)<cost?'Chưa đủ số dư.':''),text:paymentText(id)});
  return [...extraSources.map(x=>({...x,ok:x.balance>=cost,text:x.text||''})),
    option('cash','Tiền lương / ví',J?.wallet,true),
    option('account','Chuyển khoản từ tài khoản ngân hàng',b?.balance,!!b?.open),
    ...(!noCredit?[option('card','Thẻ tín dụng',c?.available,!!c,c?.locked||'')]:[]),
    ...(!noJoint?[option('joint','Quỹ chung vợ chồng',joint?.balance||0,!!joint)]:[])];
}
export async function confirmPurchase(env,{title,message='',label='Thanh toán',cost,noJoint=false,noCredit=false,extraSources=[],defaultMethod}={}){
  const J=env.api.state.journey;
  let joint=null;
  if(!noJoint&&env.api.json)try{joint=(await env.api.json('/api/marriage'))?.home?.fund||null;}catch{/* options explain unavailable joint funds */}
  const options=paymentChoices(J,cost,joint,{noJoint,noCredit,extraSources});
  const pref=defaultMethod||J?.bank?.pref||'auto';
  let selected=options.find(x=>x.id===pref)?.id;
  if(!selected&&pref==='joint')selected=options.find(x=>['cash','card'].includes(x.id)&&x.ok)?.id;
  if(!selected){const auto=personalPayment(J,cost,noJoint);selected=options.find(x=>x.id===auto&&x.ok)?.id;}
  selected||=options.find(x=>x.ok)?.id||'';
  const result=await env.confirmAction(title,message,label,{...paymentMoney(selected,cost),payment:{options,selected,cost}});
  const chosen=result===true?selected:result;
  return options.some(x=>x.id===chosen&&x.ok)?chosen:null;
}
/** 🛍️ Cửa hàng (owner 23/10 "gọn và dễ dùng như các game khác"): a purchase asks first only when it is big for this
 * player, at least BIG_BUY_SHARE of what they can pay with (wallet + bank account); a smaller one goes straight through
 * and a toast says what came. One rule for every shelf (v4/shop-shelves.js, the pets' shop in v4/pets.js). */
export const BIG_BUY_SHARE=0.2;
export const spendable=J=>Math.max(0,Number(J?.wallet)||0)+(J?.bank?.open?Math.max(0,Number(J.bank.balance)||0):0);
export const bigBuy=(J,cost)=>!(cost>0)?false:cost>=spendable(J)*BIG_BUY_SHARE;
/** ☑️ Không hỏi lại (v4/no-ask.js, the same 'mnl.noAsk' tick as ⚒️ Cường hóa): a ticked box skips the question of any size. */
export {noAsk,setNoAsk,NO_ASK_KEY} from './no-ask.js';
/** Ask before this purchase? Not when the box is ticked; else only a big one. */
export const askBuy=(J,cost)=>!noAsk()&&bigBuy(J,cost);
/** The source to pay a small purchase (or any, with ☑️ Không hỏi lại) with, as confirmPurchase would pick it (no joint fund: that one always asks);
 * a big one, or one no source covers, asks with confirmPurchase (which says why). */
export async function buyPayment(env,opts){
  const J=env.api.state.journey,cost=opts.cost;
  if(!askBuy(J,cost)&&!opts.always){
    const options=paymentChoices(J,cost,null,{noJoint:true,noCredit:opts.noCredit}),pref=J?.bank?.pref||'auto';
    const pick=options.find(x=>x.id===pref&&x.ok)?.id||options.find(x=>x.id===personalPayment(J,cost,true)&&x.ok)?.id||'';
    if(pick)return pick;
    if(noAsk())return 'cash';   // ☑️ no question at all: the server says what is missing
  }
  return confirmPurchase(env,opts);
}
