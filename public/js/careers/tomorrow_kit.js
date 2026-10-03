/** "🌅 Ngày mai" at the top of a stocked shop's part of the day summary (owner, 03/10, as milk tea has it):
 * what ran out or runs low, what must be used up tomorrow, what is on the way, the career's own lines
 * (pots to reheat, fruit still green…), and one button to Kho. The day's own figures go in a fold under it.
 * Every line comes from a field that is there (an older server leaves one out: the line goes too).
 * Pure string builders; the small stylesheet (public/css/careers/tomorrow_kit.css) is added on first use. */
import {lowItems,crates,shortName} from '../v4/restock.js';
import {asset} from '../assets.js';

function boot(){
  if(typeof document==='undefined'||document.querySelector('link[data-tk-css]'))return;
  const l=document.createElement('link');l.rel='stylesheet';l.href=asset('/css/careers/tomorrow_kit.css');l.dataset.tkCss='1';document.head.append(l);
}

const names=(x,list,n=3)=>list.slice(0,n).map(i=>`${x.esc(i.emoji||'📦')} ${x.esc(shortName(i.name))}${i.have!=null?` <b>${i.have}</b>`:''}`).join(' · ')+(list.length>n?` · +${list.length-n}`:'');

/** The stock room's lines for tomorrow (room.inventory as the client has it, after closing). */
export function stockLines(x){
  const room=x.room,inv=room?.inventory;if(!inv)return [];
  const cid=x.state?.current,items=Object.fromEntries((x.content?.inventory?.items?.[cid]||[]).map(i=>[i.id,i]));
  const low=lowItems(room,x.content,cid),out=low.filter(i=>i.have<=0),few=low.filter(i=>i.have>0);
  const soon=Object.entries(inv.expiring||{}).filter(([id,q])=>q>0&&items[id]&&!(inv.locked||[]).includes(id)).map(([id,q])=>({...items[id],have:q}));
  const {ready,coming}=crates(inv),kinds=list=>[...new Set(list.map(o=>o.item))].map(id=>items[id]).filter(Boolean);
  return [
    out.length?`❌ Hết: ${names(x,out.map(i=>({...i,have:null})))}`:'',
    few.length?`📦 Sắp hết: ${names(x,few)}`:'',
    soon.length?`⏳ Dùng hết trong ngày mai: ${names(x,soon)}`:'',
    ready.length?`📦 ${ready.length} kiện đã tới, chờ đếm nhận`:'',
    coming.length?`🚚 Đang về ${coming.length} kiện: ${names(x,kinds(coming).map(i=>({...i,have:null})))}`:'',
  ].filter(Boolean);
}

/** The block: `mood` {emoji, label, hint} (tomorrow's luck), `lines` (markup, the career's own first),
 * `go` the button (default: 📦 Mở Kho). Shows "Kho đủ hàng" when the stock room has nothing to say. */
export function planBox(x,{mood=null,lines=[],go=null}={}){
  boot();
  const stock=stockLines(x),own=(lines||[]).filter(Boolean);
  const calm=x.room?.inventory&&!stock.length?['✓ Kho đủ hàng cho ngày mai']:[];
  const all=[...own,...stock,...calm];
  const btn=go===false?'':go||x.button('📦 Mở Kho','inventory',{},'primary small tk-go');
  return `<section class="tk-plan" aria-label="Ngày mai"><h4 class="section-title">🌅 Ngày mai</h4>
    ${mood?.label?`<p class="tk-mood"><span aria-hidden="true">${x.esc(mood.emoji||'🌤️')}</span> <b>${x.esc(mood.label)}</b>${mood.hint?`<small>${x.esc(mood.hint)}</small>`:''}</p>`:''}
    ${all.length?`<ul class="tk-list">${all.map(l=>`<li>${l}</li>`).join('')}</ul>`:''}${btn}</section>`;
}

/** The day's own figures, folded under the plan: `title` is the one line it shows shut. */
export const dayFold=(title,inner)=>inner?`<details class="tk-more"><summary>${title}</summary>${inner}</details>`:'';

/** Lines about tomorrow ("Sáng mai…", "📅 Ngày mai: …", "Mai nhớ…") for the plan, the rest for the fold: [mai, rest]. */
export function splitMai(lines){
  const mai=/(^|[^\p{L}])mai([^\p{L}]|$)/iu,all=(lines||[]).filter(l=>typeof l==='string'&&l);
  return [all.filter(l=>mai.test(l)),all.filter(l=>!mai.test(l))];
}

/** A shop whose day ends in lines from the server (the street stalls, the pet shop): "🌅 Ngày mai" with the lines about
 * tomorrow, the career's own `plan` lines and the stock room; the rest of the day's lines folded as "Sổ nghề hôm nay".
 * `note:false`: the server's note is already in `plan`. */
export function linesSummary(data,x,{plan=[],note=true,title='📒 Sổ nghề hôm nay'}={}){
  if(!data||typeof data!=='object')return '';
  const [mai,rest]=splitMai([...(Array.isArray(data.lines)?data.lines:[]),...(note&&typeof data.note==='string'?[data.note]:[])]);
  const fold=rest.length?`<ul class="small tk-lines">${rest.map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul>`:'';
  return `<article class="card space-top tk-sum">${planBox(x,{lines:[...plan,...mai.map(l=>x.esc(l))]})}${dayFold(title,fold)}</article>`;
}
