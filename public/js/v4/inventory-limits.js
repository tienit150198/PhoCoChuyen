const fmt=n=>Number(n).toLocaleString('vi-VN');

// Two separate paid ladders (feedback #375/#378): shelf room per item, and how much one order line may carry. Each row
// offers its own upgrade, named for what it raises. While one line already fills a whole shelf, a bigger line cannot be
// used: the row says so instead of selling it here (it stays in Thiết bị → Nhập hàng mỗi lần).
export function inventoryLimits(inv){
  const u=inv.order_upgrade,st=inv.storage_upgrade,cap=Number(inv.capacity)||0,line=Number(inv.line_cap)||80;
  const done='<small class="tag green">Đã mở tối đa</small>';
  const storage=st?(st.next_capacity?`<button type="button" class="btn small" data-action="v4StorageUpgrade">Nâng sức chứa lên ${fmt(st.next_capacity)} · ${fmt(st.next_price)} xu</button>`:done):'';
  // A line that already fills the shelf: no upgrade here, and the why is the row's tooltip, not a grey line (#384).
  const full=u&&u.next_limit&&line>=cap&&st?.next_capacity?` title="Một dòng đã nhập đầy kệ ${fmt(cap)}: nâng sức chứa trước."`:'';
  const order=u?(!u.next_limit?done:full?'':`<button type="button" class="btn ghost small" data-action="v4OrderUpgrade">Nâng nhập mỗi dòng lên ${fmt(u.next_limit)} · ${fmt(u.next_price)} xu</button>`):'';
  return `<section class="card" aria-label="Sức chứa và hạn mức nhập"><div class="row spread wrap"><span>Sức chứa: <b>${fmt(cap)}</b>/loại</span>${storage}</div><div class="row spread wrap space-top"><span${full}>Nhập mỗi dòng: <b>${fmt(line)}</b></span>${order}</div></section>`;
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
