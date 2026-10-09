/** "Tất cả" (feedback #290, 09/10: "thêm nút Tất cả khi chọn hết nhân viên quầy hay tiệm, nâng cấp thiết bị ở quầy").
 * Pure plans for the one-tap versions of per-item actions, plus a runner that sends the SAME per-item server commands
 * one by one (game/quay.py jr_quay_buy / jr_quay_hire, game/operations.py ops_shift). The server checks each step
 * exactly like a single tap; the client total is only the confirm text. The runner stops at the first refusal
 * (no money, a slot taken meanwhile) and the caller says how many were done. No DOM here: tests/select_all.mjs loads it. */

/** Equipment a counter still lacks, cheapest first so the money there is covers the most items.
 * `have` = what the server's _have() counts (wallet ≥ 0 + bank account). `fit` = the prefix that money pays. */
export function buyAllPlan(catalog,owned,place,have){
  const own=new Set(owned||[]);
  const todo=(catalog||[]).filter(it=>!own.has(it.id)&&Number.isFinite(Number(it.price?.[place])))
    .map(it=>({id:it.id,name:it.name,emoji:it.emoji||'',price:Number(it.price[place])}))
    .sort((a,b)=>a.price-b.price);
  let left=Math.max(0,Number(have)||0);const fit=[];
  for(const it of todo){if(it.price>left)break;fit.push(it);left-=it.price;}
  const sum=list=>list.reduce((n,it)=>n+it.price,0);
  return {todo,total:sum(todo),fit,fitTotal:sum(fit)};
}

/** Wallet money the counter's purchases may use (game/quay.py _have): cash never below 0, plus an open bank account. */
export function quayHave(journey){
  const j=journey||{},bank=j.bank;
  return Math.max(0,Number(j.wallet)||0)+(bank&&bank.open&&Number.isFinite(Number(bank.balance))?Math.max(0,Number(bank.balance)):0);
}

/** Job seekers to hire into the free places of a counter, in list order, each at the wage on their row
 * (the player's typed wage, else what they ask). */
export function hireAllPlan(cands,staffCount,slots,wageOf=c=>c.ask){
  const free=Math.max(0,(Number(slots)||1)-(Number(staffCount)||0));
  return (cands||[]).slice(0,free).map(c=>({id:c.id,name:c.name,wage:Number(wageOf(c))||c.ask}));
}

/** Hired workers whose shift is not already `on` (Sổ tiệm › Nhân viên). */
export function shiftAllPlan(staff,on){
  return (staff||[]).filter(e=>e.status==='hired'&&!!e.on_shift!==!!on);
}

/** Send `steps` one at a time. `run(step)` resolves truthy when the server took it; falsy or a throw stops the rest.
 * Returns {done, total, error} (error: the thrown value, if any). Never runs two steps at once. */
export async function runAll(steps,run){
  const list=[...(steps||[])];let done=0,error=null;
  for(const step of list){
    let ok=false;
    try{ok=await run(step);}catch(e){error=e;}
    if(!ok)break;
    done++;
  }
  return {done,total:list.length,error};
}

