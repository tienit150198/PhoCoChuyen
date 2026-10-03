/** "🌅 Ngày mai" at the top of a career's block in the day summary (owner 03/10, after the milk tea one): a few
 * short lines about tomorrow (what ran out or runs low, what is on its way, the career's own reminders), one
 * button to the page where that is done, then the day's figures folded under one line.
 * Used by the stocked street & outdoor careers (delivery, farm, garbage, drain); each keeps the look in its own
 * stylesheet (.pk-plan, .pk-more). Every line comes from a field that is there: an older server leaves one
 * out, the line goes too. */
import {lowItems,crates,shortName} from '../v4/restock.js';

/** The stock room in a few words: "📦 Hết: 🧊 Túi giữ lạnh" / "📦 Sắp hết: 🫧 Màng xốp 2", crates at the door, orders on
 * the way. Names and numbers sit in their own nodes, so the English page can translate each. */
export function stockLines(x){
  const room=x.room,inv=room?.inventory;if(!inv)return [];
  const low=lowItems(room,x.content,x.state?.current),out=low.filter(i=>i.have<=0),few=low.filter(i=>i.have>0);
  const item=(i,n)=>`<span class="pk-it"><span aria-hidden="true">${x.esc(i.emoji)}</span> ${x.esc(shortName(i.name))}${n?` <b>${i.have}</b>`:''}</span>`;
  const list=(rows,n)=>rows.slice(0,3).map(i=>item(i,n)).join(' · ')+(rows.length>3?` · +${rows.length-3}`:'');
  const {ready,coming}=crates(inv);
  return [out.length?`<span>📦 Hết:</span> ${list(out,false)}`:'',
    few.length?`<span>📦 Sắp hết:</span> ${list(few,true)}`:'',
    ready.length?`📦 ${ready.length} thùng hàng đã tới, chờ mở`:'',
    coming.length?`🚚 Đang về ${coming.length} đơn hàng`:''].filter(Boolean);
}

/** The block: `lines` (markup, already escaped), `go` = [label, action] for the one button, `more` = [summary, body]
 * for the day's figures (folded). '' when there is nothing to say and nothing to fold. */
export function planBox(x,{lines=[],go=null,more=null}={}){
  const rows=lines.filter(Boolean);
  const plan=rows.length?`<section class="pk-plan" aria-label="Ngày mai"><h4 class="section-title">🌅 Ngày mai</h4><ul class="pk-list">${rows.map(l=>`<li>${l}</li>`).join('')}</ul>${go?x.button(go[0],go[1],{},'primary small pk-go'):''}</section>`:'';
  const fold=more&&more[1]?`<details class="pk-more"${rows.length?'':' open'}><summary>${more[0]}</summary>${more[1]}</details>`:'';
  return plan||fold?`<article class="card space-top pk-sum">${plan}${fold}</article>`:'';
}

/** The day's figures as label/value rows, then the server's own lines (the ones not shown above). */
export function figures(x,rows,lines=[]){
  const kv=rows.filter(([,v])=>v!=null&&v!==''&&v!==0&&v!==false).map(([l,v])=>`<div class="kv-row"><span>${x.esc(l)}</span><b>${x.esc(String(v))}</b></div>`).join('');
  const li=lines.filter(l=>typeof l==='string'&&l).map(l=>`<li>${x.esc(l)}</li>`).join('');
  return `${kv?`<div class="kv">${kv}</div>`:''}${li?`<ul class="small pk-lines">${li}</ul>`:''}`;
}
