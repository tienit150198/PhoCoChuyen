/** One explicit source per purchase; changing it here never changes the saved bank preference. */
import {personalPayment,paymentText,paymentMoney} from './money.js';
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
