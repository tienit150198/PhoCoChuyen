/** "🌅 Ngày mai" at the top of a career's part of the day summary (owner, 03/10, as milk tea has it): what ran out
 * or runs low on the shelf, what expires tomorrow, crates at the door, orders on the way, the career's own lines
 * (pots to reheat, fruit still green, who is booked for tomorrow…), and ONE button to the page that deals with it.
 * The day's own figures go in a fold under it ("Sổ nghề hôm nay").
 * Built only from what the client already has (the stock room the page holds, the summary the server sent, the
 * career's own data): a missing field drops its line (an older server leaves one out), it never shows a wrong number.
 * Two ways in, one look:
 * - planBox / dayFold / linesSummary: the stocked shops (food_kit's restaurant, café-bakery, florist; the street
 *   stalls and the pet shop, whose day ends in lines from the server);
 * - tomorrowCard (+ shelfLines for the two older shops' room.stock): the service careers' summary(data, x) hook
 *   (pet care, salon, nail, clothing, repair, homestay, mother & baby) and app.js for the pharmacy.
 * Pure string builders; the one stylesheet (public/css/careers/tomorrow_kit.css) is added on first use. */
import {lowItems,crates,shortName} from '../v4/restock.js';
import {stylesheet} from '../lazy.js';

const CSS='/css/careers/tomorrow_kit.css';
let cssIn=false;
function boot(){
  if(cssIn||typeof document==='undefined')return;cssIn=true;
  stylesheet(CSS);  // the same <link> app.js's lazy loader adds (one per page)
}

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const fmt=n=>Number(n||0).toLocaleString('vi-VN');

/** "a · b · c · +2" for at most `n` names. */
const few=(list,n=3)=>list.slice(0,n).join(' · ')+(list.length>n?` · +${list.length-n}`:'');

/** Shelf lines from the stock room of a plugin career (room.inventory = inventory.public, as the client has it after
 * closing): what is out, what runs low (shelf plus what is on the way under the stock room's low line), goods that
 * expire tomorrow, crates at the door, orders on the way. [] when the career keeps no stock room. */
export function stockLines(x){
  const room=x?.room,inv=room?.inventory;if(!inv?.stock)return [];
  const cid=x.state?.current||x.state?.focus,byId=Object.fromEntries((x.content?.inventory?.items?.[cid]||[]).map(i=>[i.id,i]));
  const name=i=>`${esc(i.emoji||'📦')} ${esc(shortName(i.name))}`;
  const low=lowItems(room,x.content,cid),out=low.filter(i=>i.have<=0),thin=low.filter(i=>i.have>0);
  // Lots that expire today are thrown out at closing, so what is left in expiring_soon goes tomorrow.
  const old=Object.entries(inv.expiring_soon||{}).filter(([id,q])=>q>0&&byId[id]&&!(inv.locked||[]).includes(id)).map(([id,q])=>`${name(byId[id])} <b>${q}</b>`);
  const {ready,coming}=crates(inv);
  return [
    out.length?`📦 Hết hàng: ${few(out.map(name))}`:'',
    thin.length?`📉 Sắp hết: ${few(thin.map(i=>`${name(i)} <b>${i.have}</b>`))}`:'',
    old.length?`⏳ Hết hạn trong ngày mai: ${few(old)}`:'',
    ready.length?`📬 <b>${ready.length}</b> thùng đã tới, chưa mở lên kệ`:'',
    coming.length?`🚚 Đang về <b>${coming.length}</b> đơn${coming[0].eta_label?` · sớm nhất ${esc(coming[0].eta_label)}`:''}`:'',
  ].filter(Boolean);
}

/** The same for the two older shops (mother & baby, pharmacy): room.stock, room.shipments and the product
 * list (`list`: [{id, name}]); low = 2 or fewer on the shelf and on the way, as the stock desk counts. */
export function shelfLines(room,list){
  if(!room?.stock||!Array.isArray(list))return [];
  const ships=(room.shipments||[]).filter(s=>s.status!=='received'),ready=ships.filter(s=>s.ready_now),onWay=id=>ships.filter(s=>s.item===id).reduce((n,s)=>n+(Number(s.qty)||0),0);
  const name=p=>esc(p.name||p.id);
  const out=list.filter(p=>(Number(room.stock[p.id])||0)<=0&&!onWay(p.id)),thin=list.filter(p=>{const q=Number(room.stock[p.id])||0;return q>0&&q+onWay(p.id)<=2;});
  const next=ships.filter(s=>!s.ready_now).sort((a,b)=>(a.left_min??1e9)-(b.left_min??1e9))[0];
  return [
    out.length?`📦 Hết hàng: ${few(out.map(name))}`:'',
    thin.length?`📉 Sắp hết: ${few(thin.map(p=>`${name(p)} <b>${Number(room.stock[p.id])||0}</b>`))}`:'',
    ready.length?`📬 <b>${ready.length}</b> kiện đã tới, chưa đếm nhận`:'',
    ships.length>ready.length?`🚚 Đang về <b>${ships.length-ready.length}</b> kiện${next?.eta_label?` · sớm nhất ${esc(next.eta_label)}`:''}`:'',
  ].filter(Boolean);
}

/** The block: `mood` {emoji, label, hint} (tomorrow's luck), `lines` (markup, the career's own first),
 * `go` the button (default: 📦 Mở Kho; false: none). Shows "Kho đủ hàng" when the stock room has nothing to say. */
export function planBox(x,{mood=null,lines=[],go=null}={}){
  boot();
  const stock=stockLines(x),own=(lines||[]).filter(Boolean);
  const calm=x.room?.inventory&&!stock.length?['✓ Kho đủ hàng cho ngày mai']:[];
  const all=[...own,...stock,...calm];
  const btn=go===false?'':go||x.button('📦 Mở Kho','inventory',{},'primary small tk-go');
  return `<section class="tk-plan" aria-label="Ngày mai"><h4 class="section-title">🌅 Ngày mai</h4>
    ${mood?.label?`<p class="tk-mood"><span aria-hidden="true">${esc(mood.emoji||'🌤️')}</span> <b>${esc(mood.label)}</b>${mood.hint?`<small>${esc(mood.hint)}</small>`:''}</p>`:''}
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
  const fold=rest.length?`<ul class="small tk-lines">${rest.map(l=>`<li>${esc(l)}</li>`).join('')}</ul>`:'';
  return `<article class="card space-top tk-sum">${planBox(x,{lines:[...plan,...mai.map(esc)]})}${dayFold(title,fold)}</article>`;
}

/** The day's figures as the shared "Sổ nghề hôm nay" shows them: labelled values, then the server's lines. */
function dayBook(data,labels,keep){
  const show=v=>typeof v==='boolean'?(v?'Có':'Không'):Array.isArray(v)?v.map(x=>typeof x==='object'?(x?.name||x?.title||x?.label||''):x).filter(Boolean).join(', '):typeof v==='number'?fmt(v):String(v);
  const rows=Object.entries(labels||{}).filter(([k])=>data[k]!=null&&!(data[k]===0||data[k]===false||Array.isArray(data[k])&&!data[k].length))
    .map(([k,l])=>`<div class="kv-row"><span>${esc(l)}</span><b>${esc(show(data[k]))}</b></div>`).join('');
  return `${rows?`<div class="kv">${rows}</div>`:''}${keep.length?`<ul class="small tk-lines">${keep.map(l=>`<li>${esc(l)}</li>`).join('')}</ul>`:''}`;
}

/** The career's block in the day summary: "🌅 Ngày mai" first, then the day folded.
 * - data: what the career's on_close sent ({lines, note, …});
 * - lift: the server lines about tomorrow (a RegExp) that move up into "Ngày mai" (the forecast, a booking…);
 * - plan: the career's own lines for tomorrow (markup, escaped by the caller), before the shelf lines;
 * - shelf: the shelf lines (stockLines / shelfLines), go: the one button ({label, action, data}); without one,
 *   a shelf that needs something gets "📦 Mở Kho" (the bar's Kho slot: `kho` its action, `khoLabel` its words);
 * - title / labels / more: the fold's summary line, the labelled values it lists, extra markup after them. */
export function tomorrowCard(x,data,{lift=null,plan=[],shelf=null,go=null,kho='inventory',khoLabel='📦 Mở Kho',title='📋 Sổ nghề hôm nay',labels={},more='',calm='✓ Kệ đủ hàng, chưa có gì phải lo cho ngày mai.'}={}){
  boot();
  const d=data&&typeof data==='object'?data:{};
  const lines=[...(Array.isArray(d.lines)?d.lines:[]),...(typeof d.note==='string'&&d.note?[d.note]:[])].filter(l=>typeof l==='string'&&l);
  const up=lift?lines.filter(l=>lift.test(l)):[],keep=lines.filter(l=>!up.includes(l));
  const stock=shelf??stockLines(x);
  const list=[...plan.filter(Boolean),...up.map(esc),...stock];
  const button=go||(stock.length?{label:khoLabel,action:kho,data:{}}:null);
  const btn=button?`<button type="button" class="btn primary small tk-go" data-action="${esc(button.action)}"${Object.entries(button.data||{}).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}>${button.label}</button>`:'';
  const book=dayBook(d,labels,keep)+more;
  return `<article class="card space-top tk-sum"><section class="tk-plan" aria-label="Ngày mai"><h4 class="section-title">🌅 Ngày mai</h4>`+
    `<ul class="tk-list">${list.length?list.map(l=>`<li>${l}</li>`).join(''):`<li class="tk-calm">${esc(calm)}</li>`}</ul>${btn}</section>`+
    `${book?dayFold(title,book):''}</article>`;
}
