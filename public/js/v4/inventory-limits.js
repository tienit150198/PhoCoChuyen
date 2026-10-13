const fmt=n=>Number(n).toLocaleString('vi-VN');

export function inventoryLimits(inv){
  const u=inv.order_upgrade;
  return `<section class="card" aria-label="Sức chứa và hạn mức nhập"><div class="row spread wrap"><span>Sức chứa: <b>${fmt(inv.capacity)}</b>/loại</span><span>Nhập mỗi dòng: <b>${fmt(inv.line_cap||80)}</b></span></div>${u?`<div class="row spread wrap space-top"><small class="muted">Hạn mức bậc ${u.tier}/${u.max_tier} · sức chứa nâng riêng</small>${u.next_limit?`<button type="button" class="btn ghost small" data-action="v4OrderUpgrade">Nâng lên ${fmt(u.next_limit)} · ${fmt(u.next_price)} xu</button>`:'<small class="tag green">Đã mở tối đa</small>'}</div>`:''}</section>`;
}

// Only ten trays are mounted per line. Indices stay identical on every page, so
// paging never counts goods or loses the player's tally. Empty slots show shortages.
export function cratePage(o,requested=0){
  const n=Math.max(0,Number(o.count_hint)||0),qty=Math.max(n,Number(o.qty)||0);
  const sizes=Array.from({length:Math.ceil(qty/10)},(_,t)=>Math.min(10,qty-t*10));
  const holes=sizes.map(()=>new Set());let h=0;
  for(const ch of o.id)h=(h*31+ch.charCodeAt(0))>>>0;
  let miss=qty-n,guard=0;
  // Keep the existing small-crate scatter; finish deterministically if a large
  // shortage exhausts the random attempts, rather than inventing extra goods.
  while(miss>0&&guard++<1000){h=(Math.imul(h,1103515245)+12345)>>>0;const t=(h>>>8)%sizes.length,slot=(h>>>16)%sizes[t];if(!holes[t].has(slot)){holes[t].add(slot);miss--;}}
  for(let t=0;miss>0&&t<sizes.length;t++)for(let s=0;miss>0&&s<sizes[t];s++)if(!holes[t].has(s)){holes[t].add(s);miss--;}
  const pages=Math.max(1,Math.ceil(sizes.length/10)),page=Math.max(0,Math.min(pages-1,Math.floor(Number(requested)||0)));
  let k=0;const trays=[];
  for(let t=0;t<sizes.length;t++){
    if(t<page*10||t>=(page+1)*10){k+=sizes[t]-holes[t].size;continue;}
    const from=k,cells=Array.from({length:sizes[t]},(_,s)=>holes[t].has(s)?null:k++);
    trays.push({number:t+1,from,to:k,cells});
  }
  return {page,pages,trays};
}
