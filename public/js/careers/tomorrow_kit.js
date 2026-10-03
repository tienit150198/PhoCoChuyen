/** "🌅 Ngày mai" at the top of a career's block in the day summary (as milk tea does): what ran out or runs
 * low on the shelf, crates waiting at the door, orders on the way, what is booked for tomorrow, then ONE
 * button to the page that deals with it; the day's own figures fold underneath ("Sổ nghề hôm nay").
 * Built only from what the client already has (the stock room the page holds, the summary the server sent,
 * the career's own data): a missing field drops its line, it never shows a wrong number.
 * Used by the service careers' summary(data, x) hook (pet care, salon, nail, clothing, repair, homestay,
 * mother & baby) and by app.js for the pharmacy. Styles: public/css/tomorrow.css (injected on first use). */
import {lowItems,crates,shortName} from '../v4/restock.js';
import {asset} from '../assets.js';

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const fmt=n=>Number(n||0).toLocaleString('vi-VN');

let cssIn=false;
function css(){
  if(cssIn||typeof document==='undefined')return;cssIn=true;
  if(document.querySelector('link[data-tm-css]'))return;
  const l=document.createElement('link');l.rel='stylesheet';l.href=asset('/css/tomorrow.css');l.dataset.tmCss='1';document.head.append(l);
}

/** "a · b · c · +2" for at most `n` names. */
const few=(list,n=3)=>list.slice(0,n).join(' · ')+(list.length>n?` · +${list.length-n}`:'');

/** Shelf lines from the stock room of a plugin career (room.inventory = inventory.public): what is out, what runs
 * low (shelf plus what is on the way under the stock room's low line), crates at the door, orders on the way,
 * goods that expire tomorrow. [] when the career keeps no stock room. */
export function stockLines(x){
  const room=x?.room,inv=room?.inventory;if(!inv?.stock)return [];
  const low=lowItems(room,x.content,x.state?.current),name=i=>`${esc(i.emoji)} ${esc(shortName(i.name))}`;
  const out=low.filter(i=>i.have<=0),thin=low.filter(i=>i.have>0);
  const {ready,coming}=crates(inv);
  const items=x.content?.inventory?.items?.[x.state?.current]||[],byId=Object.fromEntries(items.map(i=>[i.id,i]));
  const old=Object.entries(inv.expiring_soon||{}).filter(([id,q])=>q>0&&byId[id]).map(([id,q])=>`${name(byId[id])} <b>${q}</b>`);
  return [
    out.length?`📦 Hết hàng: ${few(out.map(name))}`:'',
    thin.length?`📉 Sắp hết: ${few(thin.map(i=>`${name(i)} <b>${i.have}</b>`))}`:'',
    ready.length?`📬 <b>${ready.length}</b> thùng đã tới, chưa mở lên kệ`:'',
    coming.length?`🚚 Đang về <b>${coming.length}</b> đơn${coming[0].eta_label?` · sớm nhất ${esc(coming[0].eta_label)}`:''}`:'',
    old.length?`⏳ Hết hạn trong ngày mai: ${few(old)}`:'',
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

/** The day's figures as the shared "Sổ nghề hôm nay" shows them: labelled values, then the server's lines. */
function dayBook(data,labels,keep){
  const show=v=>typeof v==='boolean'?(v?'Có':'Không'):Array.isArray(v)?v.map(x=>typeof x==='object'?(x?.name||x?.title||x?.label||''):x).filter(Boolean).join(', '):typeof v==='number'?fmt(v):String(v);
  const rows=Object.entries(labels||{}).filter(([k])=>data[k]!=null&&!(data[k]===0||data[k]===false||Array.isArray(data[k])&&!data[k].length))
    .map(([k,l])=>`<div class="kv-row"><span>${esc(l)}</span><b>${esc(show(data[k]))}</b></div>`).join('');
  return `${rows?`<div class="kv">${rows}</div>`:''}${keep.length?`<ul class="small tm-lines">${keep.map(l=>`<li>${esc(l)}</li>`).join('')}</ul>`:''}`;
}

/** The career's block in the day summary: "🌅 Ngày mai" first, then the day folded.
 * - data: what the career's on_close sent ({lines, note, …});
 * - lift: the server lines about tomorrow (a RegExp) that move up into "Ngày mai" (the forecast, a booking…);
 * - plan: the career's own lines for tomorrow (markup, escaped by the caller), before the shelf lines;
 * - shelf: the shelf lines (stockLines / shelfLines), go: the one button ({label, action, data}); without one,
 *   a shelf that needs something gets "📦 Mở Kho" (the bar's Kho slot: `kho` its action, `khoLabel` its words);
 * - title / labels / more: the fold's summary line, the labelled values it lists, extra markup after them. */
export function tomorrowCard(x,data,{lift=null,plan=[],shelf=null,go=null,kho='inventory',khoLabel='📦 Mở Kho',title='📋 Sổ nghề hôm nay',labels={},more='',calm='✓ Kệ đủ hàng, chưa có gì phải lo cho ngày mai.'}={}){
  css();
  const d=data&&typeof data==='object'?data:{};
  const lines=[...(Array.isArray(d.lines)?d.lines:[]),...(typeof d.note==='string'&&d.note?[d.note]:[])].filter(l=>typeof l==='string'&&l);
  const up=lift?lines.filter(l=>lift.test(l)):[],keep=lines.filter(l=>!up.includes(l));
  const stock=shelf??stockLines(x);
  const list=[...plan.filter(Boolean),...up.map(esc),...stock];
  const button=go||(stock.length?{label:khoLabel,action:kho,data:{}}:null);
  const btn=button?`<button type="button" class="btn primary small tm-go" data-action="${esc(button.action)}"${Object.entries(button.data||{}).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}>${button.label}</button>`:'';
  const book=dayBook(d,labels,keep)+more;
  return `<article class="card space-top tm-sum"><section class="tm-plan" aria-label="Ngày mai"><h4 class="section-title">🌅 Ngày mai</h4>`+
    `<ul class="tm-list">${list.length?list.map(l=>`<li>${l}</li>`).join(''):`<li class="tm-calm">${esc(calm)}</li>`}</ul>${btn}</section>`+
    `${book?`<details class="tm-more"><summary>${title}</summary>${book}</details>`:''}</article>`;
}
