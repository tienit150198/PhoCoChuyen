/** 🏪 Quầy của bạn, F#295/#296 (homestay, 09/10): "sao chép mua hàng như lần gần nhất", "tự trừ từ tài khoản của mình
 * mà không cần góp vốn", "nhiều quầy (>10) nên có cách quản lý trực quan… quản lý chung, hay cùng loại tiệm với nhau".
 * Pure plans for quay.js (no DOM; tests/quay_manage.mjs loads this file). Every amount here is only the confirm text:
 * the server (game/quay_business.py jr_quay_restock with `wallet`, game/quay.py jr_quay_till / jr_quay_pause) checks
 * each step again, exactly like a single tap.
 *   againPlan   🔁 the counter's last order (business.again) at today's cost, trimmed to the room left in the stock room;
 *   shortOf     👛 what the till and the fund lack for a total (paid from the wallet, then the account, by the server);
 *   groupStalls 📋 the counters by trade, the biggest group first;
 *   stallLine   📋 one compact line per counter: status, stock low, cash, staff on the floor;
 *   againAll / tillAll / openAll   the bulk steps for a group (or every counter). */

export const STOCK_MAX=20000;   // game/quay_business.py STOCK_MAX
const n=v=>Math.max(0,Math.floor(Number(v)||0));

/** {items, count, total, trimmed} for the last order of `st` (null: none, or nothing fits). `trimmed`: some portions
 * did not fit in the stock room and were left out (the server caps the room at STOCK_MAX portions). */
export function againPlan(st){
  const b=st?.business,last=b?.again||[];if(!last.length)return null;
  const rows=b.stock||[];let room=Math.max(0,STOCK_MAX-n(b.stock_total));let total=0,count=0,trimmed=false;const items={};
  for(const {id,qty} of last){
    const row=rows.find(r=>r.id===id);if(!row){trimmed=true;continue;}
    const q=Math.min(n(qty),room);if(q<n(qty))trimmed=true;if(!q)continue;
    items[id]=q;count+=q;room-=q;total+=q*n(row.cost);
  }
  return count?{items,count,total,trimmed}:null;
}

/** Xu the counter lacks for `total` (its till + fund pay first). */
export const shortOf=(st,total)=>Math.max(0,n(total)-n(st?.till)-n(st?.fund));

/** [{trade, stalls}] in the order of the trades' first counter, the biggest group first. */
export function groupStalls(stalls){
  const by=new Map();
  for(const st of stalls||[]){if(!by.has(st.trade))by.set(st.trade,[]);by.get(st.trade).push(st);}
  return [...by.entries()].map(([trade,list])=>({trade,stalls:list})).sort((a,b)=>b.stalls.length-a.stalls.length);
}

/** The few facts the overview shows for one counter. `low`: out of stock, or about to be (under 2 hours of sales). */
export function stallLine(st){
  const b=st?.business||null,hours=b?.income?.stock_hours;
  const status=b?.status||(st?.closed?'paused':'running');
  const low=!!b&&(status==='out_of_stock'||n(b.stock_total)===0||(hours!=null&&Number(hours)<2));
  return {status,low,paused:!!(b?.paused),cash:n(st?.till)+n(st?.fund),till:n(st?.till),stock:n(b?.stock_total),staff:(st?.staff||[]).length};
}

/** 🔁 for every counter with a last order: the steps (jr_quay_restock payloads) the money there pays, in list order.
 * `have` = wallet ≥ 0 + bank account (select-all.js quayHave): each counter's shortfall comes out of it in turn. */
export function againAll(stalls,have){
  let left=n(have),total=0,short=0;const steps=[],skip=[];
  for(const st of stalls||[]){
    const plan=againPlan(st);if(!plan)continue;
    const miss=shortOf(st,plan.total);
    if(miss>left){skip.push(st);continue;}
    left-=miss;total+=plan.total;short+=miss;
    steps.push({stall:st.id,items:plan.items,...(miss?{wallet:true}:{})});
  }
  return {steps,total,short,skip};
}

/** 💰 Thu két: the counters whose till holds something. */
export function tillAll(stalls){
  const list=(stalls||[]).filter(st=>n(st.till)>0);
  return {steps:list.map(st=>({stall:st.id})),total:list.reduce((a,st)=>a+n(st.till),0)};
}

/** ▶️ Mở bán: the counters their owner paused (staff sell again; unpaid costs or checks still keep a counter shut). */
export function openAll(stalls){
  return {steps:(stalls||[]).filter(st=>st?.business?.paused&&!st.due).map(st=>({stall:st.id,on:false}))};
}
