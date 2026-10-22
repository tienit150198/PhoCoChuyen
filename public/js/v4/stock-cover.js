/** 📦 Thiếu tiền nhập hàng (owner 22/10, feedback #481 "nhập hàng khi ví không đủ tiền được không"): when the shop's own
 * money cannot pay a restock, the confirm offers how to pay the rest instead of a dead end: the wallet then the account,
 * a credit-card swipe, or a vay nhập hàng (game/bank_plus.py). Every rule and number is the server's: this file reads
 * state.journey.bank.plus (cover, rules) and returns the choice, which the command carries as `cover` (📦 Kho:
 * inv_order, inv_order_cart, order_stock) or as `wallet` / `credit` (🏪 Quầy: jr_quay_restock). */
const fmt=n=>Number(n||0).toLocaleString('vi-VN');

/** The options of the confirm's "Nguồn thanh toán" list for a shortfall of `short` xu, or null when there is nothing to
 * offer (not the story, or a workplace you are hired at: its fund is the employer's). */
export function coverOptions(state,short,{career=null,wallet=true}={}){
  const j=state?.journey;
  if(!j?.story||!(short>0))return null;
  if(career&&j.places?.[career]?.employed)return null;
  const b=j.bank?.open?j.bank:null,cv=b?.plus?.cover,R=b?.plus?.rules||{};
  const cash=Number(j.wallet)||0,have=Math.max(0,cash)+(b?Number(b.balance)||0:0),out=[];
  if(wallet)out.push({id:'wallet',label:'Ví rồi tài khoản',balance:have,ok:cash>=0&&have>=short,
    why:cash<0?'Ví đang nợ.':'Ví và tài khoản chưa đủ.',text:`Lấy ${fmt(short)} xu từ ví, thiếu mới lấy tài khoản.`});
  const none='Mở tài khoản ở Ngân hàng Phố trước nhé.';
  out.push({id:'card',label:'Quẹt thẻ tín dụng',balance:cv?.card?.available||0,ok:Boolean(cv?.card?.ok)&&cv.card.available>=short,
    why:!cv?none:cv.card.why||'Hạn mức thẻ còn lại chưa đủ.',text:`Quẹt thẻ ${fmt(short)} xu, trả khi có sao kê. Trả hết trước hạn thì không mất lãi.`});
  const fee=Math.max(1,Math.ceil(short*(Number(R.stock_bp)||0)/10000));
  out.push({id:'loan',label:'Vay nhập hàng',balance:cv?.loan?.room||0,ok:Boolean(cv?.loan?.ok)&&cv.loan.room>=short,
    why:!cv?none:cv.loan.ok?'Hạn mức vay nhập hàng còn lại chưa đủ.':cv.loan.why||'Ngân hàng chưa cho vay.',
    text:`Vay ${fmt(short)} xu, sau ${R.stock_days||7} ngày trả ${fmt(short+fee)} xu. Tới hạn ngân hàng tự trích tài khoản, rồi tiền của tiệm này, rồi ví.`});
  return out;
}

/** One confirm with the payment list: resolves to 'wallet' | 'card' | 'loan', or null (backed out / nothing to offer). */
export async function askCover(confirmAction,state,{title,msg,label,short,career=null,wallet=true}){
  const options=coverOptions(state,short,{career,wallet});
  if(!options)return null;
  const selected=(options.find(o=>o.ok)||options[0]).id;
  const v=await confirmAction(title,`${msg} Tiền của tiệm còn thiếu ${fmt(short)} xu: chọn cách bù phần này.`,label,{payment:{options,selected,cost:short}});
  return options.some(o=>o.id===v)?v:null;
}
