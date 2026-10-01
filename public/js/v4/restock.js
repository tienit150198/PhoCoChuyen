/** "📦 Nhập hàng": one shortcut from any work screen of a stocked workplace back to a full shelf.
 *
 * Players asked "xếp hàng mới lên kệ như nào?": goods only reach the shelf after an order arrives
 * and its crate is opened and counted in the stock room (views.js inventoryView). So wherever a
 * shelf is short, the work screen shows one short line and one button, and that button always
 * does the next useful thing for the missing items:
 *   a crate has arrived      → "📦 Mở thùng lên kệ (N)", straight to that crate;
 *   an order is on the way   → "🚚 Hàng đang về · còn ~20 phút", the order list (wait there);
 *   nothing ordered yet      → "📦 Nhập hàng", the stock room filtered to those items, order form open.
 * The go objects plug into guide.js steps ({act, data, label}); v4Restock (views.js) handles them.
 * Pure string builders: `room` is the career state the client has (room.inventory is inventory.public). */
import {escapeHTML as esc} from '../icons.js';

/** Low stock, as the stock room counts it: what is on the shelf plus what is on the way. */
export const lowLine=cap=>Math.max(2,Math.floor((Number(cap)||0)*.08));

/** "Sữa hộp Mây Trắng" → "Sữa hộp": the words before the brand (capitalised words after the first). */
export function shortName(name){
  const words=String(name||'').split(/\s+/).filter(Boolean),out=[];
  for(const w of words){if(out.length&&w[0]!==w[0].toLowerCase())break;out.push(w);}
  return out.join(' ')||String(name||'');
}

/** In-transit orders for `items` (every item when empty): arrived ones and the ones still coming, soonest first. */
export function crates(inv,items=[]){
  const want=o=>!items.length||items.includes(o.item);
  const open=(inv?.orders||[]).filter(o=>o&&o.status==='in_transit'&&want(o));
  return {ready:open.filter(o=>o.ready_now),coming:open.filter(o=>!o.ready_now).sort((a,b)=>(a.left_min??1e9)-(b.left_min??1e9))};
}

/** Deliveries on the way and the most game/inventory.py inv_order allows at once (TRANSIT_CAP; lines of a
 * merged order share a `group`: one van; and at most TRANSIT_LINES lines in all). {n, cap, full}. */
export function vans(inv){
  const on=(inv?.orders||[]).filter(o=>o&&o.status==='in_transit'),n=new Set(on.map(o=>o.group||o.id)).size,cap=Number(inv?.transit_cap)||8;
  return {n,cap,full:n>=cap||on.length>=(Number(inv?.transit_lines)||1e9)};
}
/** "🚚 7/8 đơn đang về" once the order book is nearly full ('' before that). */
export const vansLine=inv=>{const v=vans(inv);return v.n>=v.cap-2?`🚚 ${v.n}/${v.cap} đơn đang về`:'';};
/** The order book is full (inv_order would refuse): the one next action instead of ordering. A crate at
 * the door → open it; otherwise when the next one comes (the order list). null while there is room. */
export function fullGo(inv,task=null){
  const v=vans(inv);if(!v.full)return null;
  const {ready,coming}=crates(inv);
  if(ready.length)return {act:'v4InvOpen',data:{order:ready[0].id},label:`📦 Mở thùng đã tới (${ready.length}) · đủ ${v.cap} đơn`,ready:ready.length,full:true};
  const o=coming[0];
  return {act:'v4Restock',data:{items:'',task:task||'',wait:'1'},label:`🚚 Đủ ${v.cap} đơn đang về${o?.left_label?` · ${esc(o.left_label)}`:''}`,coming:true,full:true};
}

/** The guide step `go` that brings `items` back: {act:'v4Restock', data, label}. `task`: the work
 * screen to come back to once the goods are on the shelf. `urgent`: a customer is waiting (the order
 * form starts on the express courier). */
export function restockGo(room,items=[],{task=null,urgent=true}={}){
  // Items: ids, or {id, need} (the count the job needs, so the stock room knows when it is enough).
  const list=(items||[]).filter(Boolean).map(v=>typeof v==='object'?{id:v.id,need:Number(v.target??v.need)||0}:{id:String(v),need:0});
  const ids=[...new Set(list.map(v=>v.id))];
  const inv=room?.inventory;
  if(!inv)return {act:'warehouse',label:'📦 Nhập hàng'};
  const want=id=>Math.max(0,...list.filter(v=>v.id===id).map(v=>v.need));
  const {ready,coming}=crates(inv,ids),data={items:ids.map(id=>want(id)?`${id}:${want(id)}`:id).join(','),task:task||''};
  if(ready.length)return {act:'v4Restock',data:{...data,order:ready[0].id},label:`📦 Mở thùng lên kệ (${ready.length})`,ready:ready.length};
  if(coming.length){const o=coming[0];return {act:'v4Restock',data:{...data,wait:'1'},label:`🚚 Hàng đang về${o.left_label?` · ${esc(o.left_label)}`:''}`,coming:true};}
  return fullGo(inv,task)||{act:'v4Restock',data:{...data,urgent:urgent?'1':''},label:'📦 Nhập hàng'};
}

const attrs=data=>Object.entries(data||{}).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
/** The same tap as a button. */
export function restockButton(room,items,opts={},cls='small'){
  const go=restockGo(room,items,opts);
  return `<button type="button" class="btn ${cls} rs-btn${go.ready?' ready':''}" data-action="${go.act}"${attrs(go.data)}>${go.label}</button>`;
}

/** Items of this workplace by id (content.inventory.items[career]). */
export function stockItems(content,career){
  return Object.fromEntries((content?.inventory?.items?.[career]||[]).map(i=>[i.id,i]));
}

/** What is short for this job: `need` = {item: qty wanted}; `avail(id)` = what can still be taken
 * (defaults to the shelf count). Returns [{id, name, emoji, have, need}] (restockGo takes these as items). */
export function shortOf(room,content,career,need,avail){
  const by=stockItems(content,career),stock=room?.inventory?.stock||{},locked=room?.inventory?.locked||[];
  const have=avail||(id=>Number(stock[id])||0);
  return Object.entries(need||{}).filter(([id,q])=>by[id]&&!locked.includes(id)&&q>0&&have(id)<q)
    // target: what the shelf must hold for this job (what is already promised to other bills stays put).
    .map(([id,q])=>({id,name:by[id].name,emoji:by[id].emoji||'📦',have:Math.max(0,have(id)),need:q,target:(Number(stock[id])||0)+q-Math.max(0,have(id))}));
}

/** One short line and the button: "⚠️ Kệ hết: 🥛 Sữa hộp, 🥖 Bánh mì ổ   [📦 Nhập hàng]".
 * `short` from shortOf(); '' when nothing is short. */
export function restockBar(room,short,opts={}){
  if(!short?.length||!room?.inventory)return '';
  const out=short.every(s=>s.have<=0),names=short.slice(0,3).map(s=>`<span class="rs-item"><span aria-hidden="true">${esc(s.emoji)}</span> ${esc(shortName(s.name))}</span>`).join(', ')+(short.length>3?` +${short.length-3}`:'');
  return `<div class="rs-bar" role="status"><p class="rs-line"><b>⚠️ ${out?'Kệ hết':'Kệ sắp hết'}:</b> ${names}</p>${restockButton(room,short,opts,'small primary')}</div>`;
}

/** Items at or under the low line (stock + on the way), for the day's preparation. */
export function lowItems(room,content,career){
  const inv=room?.inventory;if(!inv)return [];
  const cap=Number(inv.capacity)||40,line=lowLine(cap),on=inv.arriving||{},locked=inv.locked||[];
  return (content?.inventory?.items?.[career]||[]).filter(i=>!locked.includes(i.id)&&(Number(inv.stock?.[i.id])||0)+(Number(on[i.id])||0)<=line)
    .map(i=>({id:i.id,name:i.name,emoji:i.emoji||'📦',have:Number(inv.stock?.[i.id])||0,need:line+1}))
    .sort((a,b)=>a.have-b.have);
}

/** A step inside a career's own checklist when one supply ran out: `what` names it in plain words.
 * "📦 Hết ly giấy: nhập hàng" / "📦 Mở thùng ly giấy lên kệ" / "🚚 Ly giấy đang về · còn ~20 phút". */
export function restockFor(x,ids,what,{task}={}){
  const room=x?.room,g=restockGo(room,[].concat(ids||[]).filter(Boolean),{task:task??room?.active_task??null});
  const w=esc(what||''),left=g.coming?crates(room?.inventory,[].concat(ids||[])).coming[0]?.left_label:'';
  const label=g.full?g.label:g.ready?`📦 Mở thùng ${w} lên kệ`:g.coming?`🚚 ${w.charAt(0).toUpperCase()+w.slice(1)} đang về${left?` · ${esc(left)}`:''}`:`📦 Hết ${w}: nhập hàng`;
  return {...g,label};
}

/** Price of one order line from a supplier card (game/inventory.py line_price + ship_fee): `full` the
 * listed price, `pct` the wholesale tier reached, `cost` the goods, `ship` the fee when this line ships
 * alone, `total` what a single order costs. Older servers send no terms: no tier, no fee. */
export function orderQuote(it,qty,sup){
  const q=Math.max(1,Number(qty)||1),f=Number(sup?.factor)||1;
  const pct=Math.max(0,...(sup?.bulk||[]).filter(([n])=>q>=n).map(([,p])=>p));
  const full=Math.max(1,Math.ceil(it.cost*q*f)),off=pct?Math.max(1,Math.floor((full*pct+50)/100)):0,cost=Math.max(1,full-off);
  const ship=cost>=(Number(sup?.free_from)||0)?0:(Number(sup?.ship)||0);
  const tier=[...(sup?.bulk||[])].sort((a,b)=>a[0]-b[0]).find(([n])=>q<n)||null;
  return {full,pct,cost,ship,total:cost+ship,tier};
}
