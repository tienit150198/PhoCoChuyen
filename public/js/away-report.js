/** 🧾 "Lúc bạn vắng" (B4, F#243 / F#247: "đồ trong shop mất hết", "nhập 30 ly giấy … hết ngày lại báo hết"): on the
 * player's return to a workplace or a counter, one compact card says what the staff sold and used meanwhile, and the
 * profit. Nothing new is saved on the server for it: the page keeps, per device, a copy of the business totals from the
 * player's last look (localStorage) and shows the difference. Workplace items come from the server's running totals
 * (workplace_business business_used, so expiry or a theft is never counted as a sale); a counter's from its stock,
 * which only sales lower. A look shorter than GAP after the last one is not an absence. */
import {escapeHTML as esc} from './icons.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const PREFIX='mnl.away.';
const GAP=5*60*1000;      // shorter than this since the last look: not "away"
const CAP=25;             // words in the card's one line on a phone (owner 06/10 "ít chữ hơn")
const mem={};             // key -> {base, end, at, last, seen, told}: this tab's report, frozen at the return
const wrote={};
const hidden=()=>typeof document!=='undefined'&&document.visibilityState==='hidden';
if(typeof document!=='undefined')document.addEventListener('click',e=>{
  const b=e.target?.closest?.('[data-away-seen]');if(!b)return;
  const m=mem[b.dataset.awaySeen];if(m)m.seen=true;
  b.closest('.aw-card')?.remove();
});
function load(key){try{const v=JSON.parse(localStorage.getItem(PREFIX+key)||'null');return v&&typeof v==='object'&&Number.isFinite(v.o)?v:null;}catch{return null;}}
function save(key,snap){try{const s=JSON.stringify(snap);if(wrote[key]===s)return;wrote[key]=s;localStorage.setItem(PREFIX+key,s);}catch{}}
const strip=live=>({o:live.o,n:live.n,r:live.r,k:live.k,u:live.u});

/** Track one business and return its away report (or null). `live`: {o: orders or items sold so far, n: profit so far,
 * r: revenue so far, k: {name: running cost}, u: {item: running count}, names: {item: name}, drop: u is stock (a sale
 * lowers it), busy: the server is still catching up}. Called on every render where the business shows; a render in a
 * hidden tab is no look. A look GAP after this tab's last one (another workplace meanwhile, the phone in a pocket) is a
 * return, measured from the copy saved at that last look. */
export function awayReport(key,live,now=Date.now()){
  if(!live||!Number.isFinite(live.o)||hidden())return null;
  let m=mem[key];
  if(m&&now-m.last>=GAP&&(m.seen||!m.base))m=null;
  if(!m){
    const snap=load(key);
    const away=!!snap&&live.o>snap.o&&now-(snap.t||0)>=GAP;
    m=mem[key]={base:away?snap:null,end:away?live:null,at:now,seen:!away,told:false};
  }else if(m.base&&!m.seen&&m.end?.busy){m.end=live;m.at=now;}   // the offline catch-up is still being written: count it all
  m.last=now;
  save(key,{...strip(live),t:now});
  return m.base&&!m.seen?build(key,m):null;
}
/** The report once: true the first time a fresh report is read (for a toast). */
export function awayFresh(key){const m=mem[key];if(!m||m.seen||!m.base||m.told)return false;m.told=true;return true;}

function build(key,m){
  const a=m.base,b=m.end,names=b.names||{},orders=b.o-a.o;
  let items=null;
  if(a.u&&b.u){
    items=Object.keys({...a.u,...b.u}).map(id=>[names[id]||id,b.drop?(a.u[id]||0)-(b.u[id]||0):(b.u[id]||0)-(a.u[id]||0)])
      .filter(([,q])=>q>0).sort((x,y)=>y[1]-x[1]);
  }
  const costs={};for(const k of Object.keys(b.k||{}))costs[k]=(b.k[k]||0)-((a.k||{})[k]||0);
  return {key,orders,profit:(b.n||0)-(a.n||0),revenue:(b.r||0)-(a.r||0),costs,items,since:a.t||0,now:m.at};
}

const words=s=>s.trim().split(/\s+/).filter(Boolean).length;
const lower=s=>s?s.charAt(0).toLowerCase()+s.slice(1):s;
/** The card's one line: ≤ CAP words, the biggest items first and "+N món" for the rest. */
export function awayLine(rep,unit='đơn'){
  const head=`🧾 Lúc bạn vắng: nhân viên bán ${fmt(rep.orders)} ${unit}`;
  const tail=` · ${rep.profit<0?'lỗ':'lãi'} ${fmt(Math.abs(rep.profit))} xu`;
  const list=[],items=rep.items||[];
  for(let i=0;i<items.length;i++){
    const next=[...list,`${fmt(items[i][1])} ${lower(items[i][0])}`],rest=items.length-next.length;
    if(words(head+', dùng '+next.join(', ')+(rest?`, +${rest} món`:'')+tail)>CAP)break;
    list.push(next[next.length-1]);
  }
  const rest=items.length-list.length;
  const used=list.length?`, dùng ${list.join(', ')}${rest?`, +${rest} món`:''}`:rest?`, dùng ${rest} loại hàng`:'';
  return head+used+tail;
}
export function awayToast(rep,unit='đơn'){return `🧾 Lúc bạn vắng: đội bán ${fmt(rep.orders)} ${unit}`;}   // a toast ≤ 8 words

function span(rep){
  const min=Math.max(1,Math.round((rep.now-rep.since)/60000));
  const d=new Date(rep.since),at=`${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
  return `Từ ${at}${min>=1440?` (${Math.floor(min/1440)} ngày trước)`:''}, khoảng ${min>=60?`${Math.floor(min/60)} giờ${min%60?` ${min%60} phút`:''}`:`${min} phút`}`;
}
/** The card: the line, and a fold with every item, the money and why the stock went down. `lines`: extra
 * [label, text] rows for the fold (each place's own costs); `where`: where the money went. */
export function awayCard(rep,{unit='đơn',lines=[],where='quỹ nghề',extra=''}={}){
  if(!rep)return '';
  const items=(rep.items||[]).map(([name,q])=>`<li><b>${fmt(q)}</b> × ${esc(name)}</li>`).join('');
  const rows=[['Thu',`${fmt(rep.revenue)} xu`],...lines,[rep.profit<0?'Lỗ':'Lãi',`${fmt(Math.abs(rep.profit))} xu`]]
    .map(([k,v])=>`<div><small>${esc(k)}</small><b>${esc(v)}</b></div>`).join('');
  return `${STYLES}<section class="aw-card" data-testid="away-report" role="status"><p class="aw-line">${esc(awayLine(rep,unit))}</p>
    <details class="aw-more"><summary>Xem chi tiết</summary>
      <p class="aw-note">${esc(span(rep))}. Hàng không hết hạn: nhân viên đã bán, tiền vào ${esc(where)}.</p>
      ${items?`<ul class="aw-items">${items}</ul>`:''}<div class="aw-money">${rows}</div>${extra}
    </details><button type="button" class="btn ghost small aw-ok" data-away-seen="${esc(rep.key)}">Đã xem</button></section>`;
}

const STYLES=`<style>.aw-card{display:grid;gap:6px;margin:0 0 12px;padding:10px 12px;border:1px solid var(--line,#e5d9c6);border-radius:14px;background:#fbf4e6;color:#4d3d2c;font-size:.82rem}.aw-line{margin:0;line-height:1.5;font-weight:600}.aw-more summary{min-height:36px;display:flex;align-items:center;cursor:pointer;color:#7c644e}.aw-note{margin:4px 0;line-height:1.5;color:#6c5944}.aw-items{margin:4px 0;padding-left:18px;line-height:1.6}.aw-money{display:grid;grid-template-columns:repeat(auto-fit,minmax(96px,1fr));gap:6px;margin:6px 0}.aw-money>div{display:grid;gap:2px;padding:6px 8px;border-radius:10px;background:#fff8ec}.aw-money small{font-size:.68rem;color:#7c644e}.aw-ok{justify-self:end;min-height:40px}</style>`;

/* ---- the two places ---- */
/** A workplace (game/workplace_business.py public): orders, profit with the 40% bonus, and the items the staff took. */
export function workplaceAway(c,cid,owner='',now=Date.now()){
  const b=c?.ops?.business;if(!b||!(c.ops.staff||[]).some(e=>e.status==='hired'))return null;
  const u={},names={};for(const [id,name,q] of Array.isArray(b.used)?b.used:[]){u[id]=q;names[id]=name;}
  return awayReport(`wp.${owner}.${cid}`,{o:b.served,n:b.net,r:b.revenue,k:{w:b.wages,m:b.materials,g:b.goods,p:b.profit_bonus},u,names,busy:!!b.catching_up},now);
}
export function workplaceAwayCard(rep){
  if(!rep)return '';const k=rep.costs;
  return awayCard(rep,{where:'quỹ nghề',lines:[['Lương, vật tư',`${fmt((k.w||0)+(k.m||0))} xu`],['Giá vốn hàng',`${fmt(k.g)} xu`],['Thưởng 40%',`+${fmt(k.p)} xu`]],
    extra:'<p class="aw-note">Giá vốn đã trả lúc nhập hàng. Muốn đội bán tiếp thì nhập thêm.</p><button type="button" class="btn ghost small" data-action="warehouse">📦 Nhập thêm</button>'});
}
/** A counter (game/quay_business.py public): items sold, profit after every cost, and what left the stock. */
export function stallAway(st,owner='',nameOf=id=>id,now=Date.now()){
  const b=st?.business;if(!b||!(st.staff||[]).length)return null;
  const u={},names={};for(const x of Array.isArray(b.stock)?b.stock:[]){u[x.id]=x.qty;names[x.id]=nameOf(x.id);}
  const spent=Object.values(b.expenses||{}).reduce((a,v)=>a+(Number(v)||0),0);
  return awayReport(`qy.${owner}.${st.id}`,{o:b.sold,n:b.net,r:b.revenue,k:{e:spent},u,names,drop:true},now);
}
export function stallAwayCard(rep){
  return rep?awayCard(rep,{unit:'món',where:'két quầy',lines:[['Chi phí quầy',`${fmt(rep.costs.e)} xu`]]}):'';
}
