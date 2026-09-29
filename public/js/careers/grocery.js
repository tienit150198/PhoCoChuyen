/** Tạp Hoá Cô Ba — checkout counter (scanner, scale, promo board, change tray,
 *  bank app, ghi-sổ ledger), shelf rotation, rush-hour queue, bulk orders,
 *  the stock & price-tag board (Mây Mart flyer) and surprises at the shop.
 *  Care loop: today's care checklist, tomorrow's forecast, real shelf rotation,
 *  trust / lean days / repayment plans in the credit book, weekly regular lists. */
import {keepBarAboveFooter} from './food_kit.js';
import {reqList,fold} from '../ui-kit.js';
const ID='grocery';
const catalogue=x=>x.content.inventory?.items?.[ID]||[];
const item=(x,id)=>catalogue(x).find(i=>i.id===id)||{id,name:id,emoji:'•',unit:''};
const price=(x,id)=>(x.room.data?.prices||{})[id]??x.cc.base_prices?.[id]??0;
const unitPrice=(t,x,id)=>t.haggle&&t.haggle.state==='match'&&t.haggle.item===id?t.haggle.theirs:price(x,id);
const sum=a=>a.reduce((s,v)=>s+v,0);
const weighedAmount=(p,g)=>Math.floor((g*p+500)/1000);
const methodOf=t=>t.needs.pay==='credit'&&t.pay.declined?'cash':t.needs.pay;
const METHOD={cash:['💵','Tiền mặt'],transfer:['📱','Chuyển khoản'],credit:['📒','Xin ghi sổ']};
const tile=(x,command,payload,inner,cls='',disabled=false)=>`<button type="button" class="tile ${cls}" data-command="${command}" data-payload="${x.esc(JSON.stringify(payload))}"${disabled?' disabled':''}>${inner}</button>`;
const carBtn=(x,label,action,data={},cls='')=>`<button type="button" class="btn ${cls}" data-action="car:${action}"${Object.entries(data).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}>${label}</button>`;
const checklist=(x,rows)=>`<ul class="checklist">${rows.map(([ok,label,note])=>`<li class="${ok===true?'ok':ok===false?'bad':''}"><span>${ok===true?'✓':ok===false?'✗':'○'}</span>${x.esc(label)}${note?`<small>${x.esc(note)}</small>`:''}</li>`).join('')}</ul>`;
const stockUnit=(x,id)=>id in (x.cc.weighed||{})?(id==='rice'?'kg':'lạng'):item(x,id).unit;
const priceUnit=(x,id)=>id in (x.cc.weighed||{})?'kg':item(x,id).unit;
const who=(x,idx)=>x.npc(`${ID}_npc_${String(idx+1).padStart(2,'0')}`);

function discount(p,qty,unit){
  if(p.kind==='bundle')return Math.floor(qty/p.every)*p.free*unit;
  if(p.kind==='step')return Math.floor(qty/p.every)*p.off;
  return qty*p.off;
}
function cartTotal(t,x){
  let s=0;
  for(const [k,q] of Object.entries(t.scanned||{}))s+=unitPrice(t,x,k)*q;
  for(const w of Object.values(t.weighed||{}))s+=weighedAmount(price(x,w.plu),w.grams);
  for(const id of t.promos||[]){const p=x.cc.promos.find(v=>v.id===id);if(p)s-=discount(p,t.scanned[p.item]||0,unitPrice(t,x,p.item));}
  return Math.max(0,s);
}
function wantUnits(t){
  const units={};
  for(const l of t.needs.lines)if(!l.weighed)units[l.item]=(units[l.item]||0)+l.qty;
  return units;
}
const hasBeer=t=>t.needs.lines.some(l=>l.item==='beer');
const minor=t=>t.age!=null&&t.age<18;
const dropped=(t,id)=>t.haggle&&t.haggle.state==='dropped'&&t.haggle.item===id;
const rivalOf=x=>Object.fromEntries((x.room.data?.today_view?.rival||[]).map(r=>[r.item,r.theirs]));

/* ------------------------------------------------------------ today + surprises */
function todayStrip(x){
  const tv=x.room.data?.today_view;if(!tv)return '';
  const chips=(tv.rival||[]).map(r=>{const it=item(x,r.item),hi=r.ours>r.theirs;
    return `<span class="gr-flyer ${hi?'hi':'ok'}"><span aria-hidden="true">${it.emoji}</span><span>${x.esc(it.name)}</span><b>${x.fmt(r.theirs)}</b><small>${hi?`tiệm ${x.fmt(r.ours)}`:'tiệm ngang giá'}</small></span>`;}).join('');
  return `<section class="gr-today" aria-label="Hôm nay ở tiệm"><div class="gr-mood"><span class="gr-mood-emoji" aria-hidden="true">${tv.mod.emoji}</span><div><b>Hôm nay: ${x.esc(tv.mod.name)}</b><small>${x.esc(tv.mod.text)}</small></div></div>
    ${chips?`<div class="gr-flyers"><small class="gr-flyer-head">📣 Tờ rơi Mây Mart${tv.calm?' · khách quen hôm nay không so giá':''}</small>${chips}</div>`:''}</section>`;
}
function deskCard(x){
  const desk=x.room.data?.desk;if(!desk)return '';
  const ev=desk.ev;
  if(ev){
    const opts=ev.options.map(o=>{
      const poor=o.cost>(Number(x.room.money)||0);
      const inner=`<span class="gr-opt-label">${x.esc(o.label)}</span>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}${o.cost?`<em class="gr-cost">−${x.fmt(o.cost)} xu${poor?' · ví chưa đủ':''}</em>`:''}`;
      return o.cost?x.confirmCmd(inner,'gr_decide',{option:o.id},`Lựa chọn này tốn ${x.fmt(o.cost)} xu. Đồng ý?`,'gr-opt',poor):x.cmd(inner,'gr_decide',{option:o.id},'gr-opt');
    }).join('');
    return `<section class="gr-event ${ev.tone==='tense'?'tense':''}" role="group" aria-labelledby="gr-ev-title"><div class="gr-ev-head"><span class="gr-ev-emoji" aria-hidden="true">${ev.emoji}</span><div><small>Chuyện bất ngờ · quyết xong rồi làm tiếp</small><h3 id="gr-ev-title">${x.esc(ev.title)}</h3></div></div>
      <p>${x.esc(ev.text)}</p><div class="gr-opts">${opts}</div></section>`;
  }
  const last=desk.last,key=last?`${last.script}-${last.choice}-${last.day}`:'';
  if(last&&last.day===x.room.day&&x.ui.seenLast!==key){
    return `<div class="gr-last ${last.good===true?'good':last.good===false?'bad':''}" role="status"><span aria-hidden="true">${last.emoji}</span><p><b>${x.esc(last.title)}</b> · ${x.esc(last.outcome)}</p>${carBtn(x,'✕','seen',{key},'ghost small gr-x')}</div>`;
  }
  return '';
}

/* ------------------------------------------------------------ header */
function ticket(t,x){
  const w=x.npc(t.npc),n=t.needs,[e,m]=METHOD[n.pay]||['🧾',''];
  const tag=t.kind==='checkout'?`<span class="tag blue">${e} ${x.esc(m)}</span>`:t.kind==='rush'?'<span class="tag amber">⏱️ Giờ cao điểm</span>':t.kind==='bulk'?'<span class="tag green">📦 Đơn sỉ</span>':'<span class="tag amber">🗂️ Việc kệ</span>';
  const say=t.kind==='checkout'?(n.note||t.opening):t.kind==='bulk'?(n.note||t.opening):t.opening;
  return `<article class="card ticket gr-ticket"><div class="row">${x.portrait(w,44)}<div class="grow">
    <div class="row spread"><h3>${x.esc(w.display_name)}</h3>${tag}</div>
    <p class="small"><b>${x.esc(t.title)}</b></p><p class="muted small">“${x.esc(say)}”</p>
    ${t.kind==='rush'?'':`<div class="patience" title="Kiên nhẫn"><div class="bar ${t.patience<50?'low':''}"><i style="width:${t.patience}%"></i></div><small>${t.patience}%</small></div>`}</div></div></article>`;
}
function alerts(x){
  const inv=x.room.inventory||{},exp=Object.values(inv.expiring||{}).filter(v=>v>0).length;
  const low=catalogue(x).filter(i=>!(inv.locked||[]).includes(i.id)&&(inv.stock?.[i.id]??0)<=3).length;
  return exp+low;
}
function tabs(x,idle=false){
  const tab=curTab(x,idle),d=x.room.data||{};
  const owed=sum((d.ledger_view||[]).map(r=>r.balance)),n=alerts(x)+(d.rotation||[]).length;
  const due=(d.lists_view||[]).filter(l=>l.when==='today'&&l.items.some(i=>i.packed<i.qty)).length;
  const worry=(d.ledger_view||[]).some(r=>r.hard||r.risk||r.overdue);
  const b=(label,id,aria)=>`<button type="button" role="tab" aria-selected="${tab===id}" class="btn small ${tab===id?'primary':'ghost'}" data-action="car:tab" data-tab="${id}"${aria?` aria-label="${x.esc(aria)}"`:''}>${label}</button>`;
  return `<div class="gr-tabs ${idle?'three':''}" role="tablist">${idle?'':b('🛒 Quầy','counter')}${b(`🏷️ Kho${n?` <span class="gr-badge">${n}</span>`:''}`,'stock',n?`Kho & giá, ${n} việc cần xem`:'Kho & giá')}${b(`📒 Sổ nợ${worry?' <span class="gr-badge">!</span>':owed?` <span class="gr-badge soft">${x.fmt(owed)}</span>`:''}`,'ledger',`Sổ nợ, hàng xóm đang nợ ${owed} xu`)}${b(`🧺 Giỏ quen${due?` <span class="gr-badge">${due}</span>`:''}`,'lists',due?`Giỏ quen, ${due} giỏ cần soạn hôm nay`:'Giỏ quen')}</div>`;
}
const curTab=(x,idle)=>{const t=x.ui.tab||(idle?'stock':'counter');return idle&&t==='counter'?'stock':t;};
function billbar(x,total,cta,note=''){
  return `<div class="gr-billbar">${total!=null?`<div class="gr-billsum"><small>${x.esc(note||'Tổng bill')}</small><b>${x.money(total)}</b></div>`:''}${cta}</div>`;
}

/* ------------------------------------------------------------ checkout · basket */
function counterBasket(t,x){
  const n=t.needs,rv=rivalOf(x);
  return `<div class="gr-basket">${n.lines.map((l,i)=>{
    const it=item(x,l.item);
    if(l.weighed){
      const w=t.weighed[String(i)];
      return `<div class="gr-line weighed ${w?'done':''}"><span class="gr-emoji">${it.emoji}</span><div class="grow"><b>${x.esc(it.name)}</b><small>${l.container?'🧺 để trong rổ nhựa của khách':'🛍️ túi của tiệm'} · cân ký · ${x.fmt(price(x,l.item))} xu/kg</small></div>
        ${t.stage==='basket'?carBtn(x,w?'⚖️ Cân lại':'⚖️ Đặt lên cân','scale',{line:i,task:t.id},w?'ghost small':'small'):''}</div>`;
    }
    const have=t.scanned[l.item]||0,blocked=l.item==='beer'&&minor(t),gone=dropped(t,l.item);
    const flyer=rv[l.item]!=null&&!gone?` · <span class="gr-mini-flyer">Mây Mart ${x.fmt(rv[l.item])}</span>`:'';
    const inv=x.room.inventory||{stock:{}},avail=Math.max(0,(inv.stock?.[l.item]||0)-(x.room.data?.held?.[l.item]||0));
    const short=t.stage==='basket'&&!blocked&&!gone&&have<l.qty&&avail<l.qty-have;
    const want=Math.max(1,Math.min(l.qty-have,avail));
    return `<div class="gr-line ${have>=l.qty?'done':''} ${blocked||gone?'blocked':''}"><span class="gr-emoji">${it.emoji}</span><div class="grow"><b>${x.esc(it.name)}</b><small>${l.qty} ${x.esc(it.unit)} · ${x.fmt(unitPrice(t,x,l.item))} xu${l.item==='beer'?' · 🔞 18+':''}${flyer}</small>${short?`<small class="gr-short">Kệ chỉ còn ${avail} — nhập gấp ở “Kho & giá” hoặc bán phần đang có.</small>`:''}</div>
      ${t.stage==='basket'&&!blocked&&!gone?x.cmd(`Quét ×${want}`,'gr_scan',{task:t.id,item:l.item,qty:want},'small',have>=l.qty||!avail):''}${short&&!avail?carBtn(x,'🏷️ Kho','tab',{tab:'stock'},'small ghost'):''}${blocked?'<span class="tag danger">Không bán</span>':''}${gone?'<span class="tag danger">Khách bỏ</span>':''}</div>`;
  }).join('')}</div>`;
}
function haggleCard(t,x){
  const h=t.haggle;if(!h||h.state!=='ask')return '';
  const it=item(x,h.item),w=x.npc(t.npc);
  return `<div class="gr-haggle" role="group" aria-label="Khách trả giá"><div class="row">${x.portrait(w,36)}<p class="grow"><b>${x.esc(w.display_name)}</b> chìa tờ rơi: Mây Mart bán ${x.esc(it.name.toLowerCase())} <b>${x.fmt(h.theirs)} xu</b>, tiệm đang để <b>${x.fmt(h.ours)} xu</b>.</p></div>
    <div class="gr-haggle-btns">${x.cmd(`🤝 Bớt còn ${x.fmt(h.theirs)} xu`,'gr_haggle',{task:t.id,answer:'match'},'primary')}${x.cmd(`✋ Giữ giá ${x.fmt(h.ours)} xu`,'gr_haggle',{task:t.id,answer:'hold'},'ghost')}</div>
    <small class="muted">Bớt thì mỏng lời; giữ giá thì có người vẫn mua, có người bỏ sang Mây Mart.</small></div>`;
}
function scalePanel(t,x){
  const i=Number(x.ui.scale);
  const l=t.needs.lines[i];
  if(!(x.ui.scaleFor===t.id&&l&&l.weighed))return '';
  const tare=x.ui.tare===true,it=item(x,l.item);
  return `<div class="gr-scale card"><div class="row spread"><h4>⚖️ Cân điện tử · ${it.emoji} ${x.esc(it.name)}</h4>${carBtn(x,'✕','scale',{line:-1,task:t.id},'ghost small')}</div>
    <div class="gr-scale-screen"><span>${l.container?'Rổ nhựa của khách đang nằm trên bàn cân':'Túi nilon mỏng của tiệm'}</span><b>${tare?'TARE ▸ 0 g':'—'}</b></div>
    <div class="row wrap">${carBtn(x,tare?'✓ Đã trừ bì (tare)':'Trừ bì (tare)','tare',{},tare?'primary small':'ghost small')}<small class="muted">Rồi bấm đúng mã PLU của món đang nằm trên cân.</small></div>
    <div class="tile-grid gr-plu">${Object.keys(x.cc.weighed||{}).map(k=>{const p=item(x,k);return tile(x,'gr_weigh',{task:t.id,line:i,plu:k,tare},`<span class="tile-emoji">${p.emoji}</span><b>${x.esc(p.name)}</b><small>PLU · ${x.fmt(price(x,k))} xu/kg</small>`);}).join('')}</div></div>`;
}
function shelfTiles(t,x){
  const inv=x.room.inventory||{stock:{},locked:[]},held=x.room.data?.held||{};
  return `<div class="tile-grid gr-shelf-tiles">${catalogue(x).filter(i=>!(i.id in (x.cc.weighed||{}))).map(i=>{
    const mine=t.scanned[i.id]||0,q=Math.max(0,(inv.stock?.[i.id]||0)-(held[i.id]||0)+mine),locked=(inv.locked||[]).includes(i.id);
    return tile(x,'gr_scan',{task:t.id,item:i.id,qty:1},`<span class="tile-emoji">${i.emoji}</span><b>${x.esc(i.name)}</b><small>${locked?'🔒 cấp '+(i.unlock||1):`còn ${q-mine} ${x.esc(i.unit)}`}${i.age?' · 🔞':''}</small>${mine?`<em class="tile-count">×${mine}</em>`:''}`,
      `${locked?'locked':''} ${q-mine<=0?'empty':''}`,locked||q-mine<=0||t.stage!=='basket'||dropped(t,i.id));
  }).join('')}</div>`;
}
function promoBoard(t,x){
  return `<div class="gr-promos">${x.cc.promos.map(p=>{
    const on=t.promos.includes(p.id),it=item(x,p.item),ok=discount(p,t.scanned[p.item]||0,unitPrice(t,x,p.item))>0;
    return `<div class="gr-promo ${on?'on':''}"><span>${it.emoji}</span><small class="grow">${x.esc(p.label)}</small>${on?'<span class="tag green">Đã áp</span>':x.cmd('Áp','gr_promo',{task:t.id,promo:p.id},'small ghost',t.stage!=='basket'||!ok)}</div>`;
  }).join('')}</div>`;
}
function receipt(t,x){
  const rows=[];
  for(const [k,q] of Object.entries(t.scanned)){const it=item(x,k),u=unitPrice(t,x,k);rows.push(`<div class="gr-rline"><span>${it.emoji} ${x.esc(it.name)} ×${q}${u!==price(x,k)?' <small>(giá Mây Mart)</small>':''}</span><b>${x.fmt(u*q)}</b>${t.stage==='basket'?`<button type="button" class="icon-btn gr-void" aria-label="Xóa ${x.esc(it.name)}" data-command="gr_void" data-payload="${x.esc(JSON.stringify({task:t.id,item:k}))}">✕</button>`:''}</div>`);}
  for(const [i,w] of Object.entries(t.weighed)){const it=item(x,w.plu);rows.push(`<div class="gr-rline"><span>${it.emoji} ${x.esc(it.name)} ${x.fmt(w.grams)} g${w.tare?' (đã trừ bì)':''}</span><b>${x.fmt(weighedAmount(price(x,w.plu),w.grams))}</b>${t.stage==='basket'?`<button type="button" class="icon-btn gr-void" aria-label="Xóa dòng cân" data-command="gr_void" data-payload="${x.esc(JSON.stringify({task:t.id,line:Number(i)}))}">✕</button>`:''}</div>`);}
  for(const id of t.promos){const p=x.cc.promos.find(v=>v.id===id);if(p)rows.push(`<div class="gr-rline promo"><span>🏷️ ${x.esc(p.label)}</span><b>−${x.fmt(discount(p,t.scanned[p.item]||0,unitPrice(t,x,p.item)))}</b></div>`);}
  const total=t.total??cartTotal(t,x);
  return `<div class="gr-receipt" aria-label="Hóa đơn"><div class="gr-receipt-head">TẠP HOÁ CÔ BA<br><small>Hẻm 7 · Phường Mây · ${t.stage==='basket'?'đang tính':'đã chốt'}</small></div>
    ${rows.join('')||'<p class="muted small">Chưa có món nào. Quét hoặc cân hàng.</p>'}
    <div class="gr-rtotal"><span>TỔNG</span><b>${x.money(total)}</b></div></div>`;
}
function basketChecklist(t,x){
  const want=wantUnits(t),rows=[];
  for(const [k,q] of Object.entries(want)){
    const have=t.scanned[k]||0,it=item(x,k);
    if(k==='beer'&&minor(t))rows.push([!have,`${it.name}: không bán cho khách dưới 18`,'']);
    else if(dropped(t,k))rows.push([!have,`${it.name}: khách bỏ, sang Mây Mart mua`,'']);
    else rows.push([have?have===q:null,`${q} ${it.unit} ${it.name}`,have?`${have}/${q}`:'']);
  }
  t.needs.lines.forEach((l,i)=>{if(!l.weighed)return;const w=t.weighed[String(i)],it=item(x,l.item);
    rows.push([w?w.plu===l.item&&(!l.container||w.tare):null,`Cân ${it.name.toLowerCase()}${l.container?' (trừ bì rổ)':''}`,w?`${w.grams} g · mã ${item(x,w.plu).name}`:'']);});
  for(const k of Object.keys(t.scanned))if(!want[k])rows.push([false,`${item(x,k).name} (khách không mua)`,'']);
  for(const p of x.cc.promos){if(discount(p,t.scanned[p.item]||0,unitPrice(t,x,p.item))>0)rows.push([t.promos.includes(p.id),`Khuyến mãi: ${p.label}`,'']);}
  if(hasBeer(t))rows.push([t.age==null?null:true,'Kiểm tuổi khách mua bia',t.age==null?'':t.age+' tuổi']);
  if(t.haggle&&t.haggle.state==='ask')rows.push([null,'Trả lời khách chuyện giá Mây Mart','']);
  return checklist(x,rows);
}

/* ------------------------------------------------------------ checkout · payment */
function money(x,v){return `<span class="gr-money ${v>=10?'note':'coin'} d${v}">${x.fmt(v)}</span>`;}
function cashPanel(t,x){
  const pay=t.pay,tender=sum(pay.tender),due=tender-t.total,given=sum(pay.change);
  const check=pay.note_check;
  return `<div class="gr-pay card"><h4>💵 Khách đưa</h4><div class="gr-tender">${pay.tender.map(v=>money(x,v)).join('')}<b>= ${x.money(tender)}</b></div>
    <div class="row wrap">${x.cmd('🔦 Soi & sờ tiền','gr_check_note',{task:t.id},'small ghost',pay.checked)}
      ${check==='fake'?x.cmd('🙏 Nhờ khách đổi tờ khác','gr_reject_note',{task:t.id},'small danger'):''}
      ${check==='real'?'<span class="tag green">Tiền thật</span>':check==='fake'?'<span class="tag danger">Nghi tiền giả!</span>':''}</div>
    <h4 class="space-top">Khay thối tiền</h4>
    <div class="gr-due"><span>Cần thối</span><b>${x.money(Math.max(0,due))}</b><span>Đang đặt</span><b class="${given===due?'ok':given>due?'over':''}">${x.money(given)}</b></div>
    <div class="bar gr-due-bar"><i style="width:${due>0?Math.min(100,given/due*100):100}%"></i></div>
    <div class="gr-tray">${pay.change.map(v=>money(x,v)).join('')||'<small class="muted">Khay trống</small>'}</div>
    <div class="gr-denoms">${x.cc.denoms.map(v=>`<button type="button" class="gr-denom ${v>=10?'note':'coin'}" data-command="gr_change" data-payload="${x.esc(JSON.stringify({task:t.id,denom:v}))}" aria-label="Thêm ${v} xu">${x.fmt(v)}</button>`).join('')}</div>
    <div class="row wrap">${x.cmd('↩︎ Bớt tờ cuối','gr_change_undo',{task:t.id},'small ghost',!pay.change.length)}${x.cmd('Cất hết','gr_change_undo',{task:t.id,all:true},'small ghost',!pay.change.length)}</div></div>`;
}
function transferPanel(t,x){
  const pay=t.pay,sc=pay.screen||{};
  const bank=pay.bank;
  return `<div class="gr-pay card"><div class="gr-phones">
    <div class="gr-phone customer"><small>Điện thoại của khách</small><b class="gr-phone-ok">✔ ${x.esc(sc.status==='success'?'Chuyển tiền thành công':'Đang xử lý')}</b><span class="gr-phone-amt">${x.money(sc.amount||0)}</span><small>Tới: ${x.esc(sc.to||'')}</small><small>ND: ${x.esc(sc.memo||'')}</small></div>
    <div class="gr-phone shop"><small>App ngân hàng của tiệm</small>${!pay.verified?'<span class="muted small">Chưa kiểm</span>':bank?`<b>+${x.money(bank)}</b><small>${bank>=t.total?'Khớp hóa đơn ✓':'Thiếu '+x.money(t.total-bank)}</small>`:'<span class="small">Chưa thấy tiền về…</span>'}</div></div>
    <p class="muted small">Ảnh màn hình của khách có thể sai hoặc chưa về. Chỉ tin loa báo/app ngân hàng của tiệm.</p>
    <div class="row wrap">${x.cmd(pay.verified?'🔄 Kiểm lại app':'🔔 Kiểm loa/app ngân hàng','gr_verify',{task:t.id},'small ghost')}
    ${pay.verified&&bank>0&&bank<t.total&&!pay.fixed?x.cmd('🙏 Nhờ khách chuyển bù','gr_transfer_fix',{task:t.id},'small'):''}</div></div>`;
}
function creditPanel(t,x){
  const row=(x.room.data?.ledger_view||[]).find(r=>r.npc===t.npc);
  if(!row)return `<div class="gr-pay card"><p>Khách này chưa có trang trong sổ.</p>${x.cmd('Nhận tiền mặt thay vì ghi sổ','gr_decline_credit',{task:t.id},'small')}</div>`;
  const after=row.balance+t.total,pct=Math.min(100,after/row.limit*100);
  const days=row.balance&&row.since?x.room.day-Math.max(1,row.since):0;
  return `<div class="gr-pay card gr-book"><h4>📒 Sổ ghi nợ · ${x.esc(row.name)}</h4>
    <dl class="kv"><dt>Hạn mức</dt><dd>${x.money(row.limit)}</dd><dt>Đang nợ</dt><dd>${x.money(row.balance)}${row.balance?` · từ ${days} ngày trước`:''}</dd>
    <dt>Nếu ghi thêm</dt><dd><b>${x.money(after)}</b></dd><dt>Nợ quá hạn</dt><dd>${row.overdue?'<span class="tag danger">Có</span>':'Không'}</dd></dl>
    <div class="bar ${after>row.limit?'low':''}"><i style="width:${pct}%"></i></div><small class="muted">Quy định: ${x.esc((x.cc.credit_rules||[]).join(' '))}</small>
    <div class="row wrap space-top">${x.cmd('🙏 Từ chối khéo, nhận tiền mặt','gr_decline_credit',{task:t.id},'small ghost')}</div></div>`;
}
function payCta(t,x){
  const m=methodOf(t);
  const label=m==='credit'?'📒 GHI SỔ & GIAO HÀNG':'✅ THU TIỀN & GIAO HÀNG';
  const q=m==='cash'?'Giao hàng và tiền thối cho khách? Khách sẽ đếm lại tiền thối.':m==='transfer'?'Cho khách mang hàng về? Chỉ nên giao khi app ngân hàng của tiệm đã báo đủ tiền.':'Ghi khoản này vào sổ nợ và giao hàng?';
  return x.confirmCmd(label,'gr_pay',{task:t.id},q,'primary big grow');
}

function checkoutJob(t,x){
  if(t.stage==='done'){const r=t.result||{};return `<div class="workbench"><section class="wb-main"><div class="card"><h4>✅ Đã xong</h4><p>${x.esc(METHOD[r.method]?.[1]||'')} · ${x.money(r.total||0)}${r.loss?` · thất thoát ${x.money(r.loss)}`:''}</p></div></section><aside class="wb-side">${receipt(t,x)}</aside></div>`;}
  const basket=t.stage==='basket';
  const m=methodOf(t);
  const main=basket?`${haggleCard(t,x)}<h4 class="section-title">1 · Giỏ hàng trên quầy</h4>${counterBasket(t,x)}${scalePanel(t,x)}
      ${hasBeer(t)?`<div class="notice amber row spread"><span>🔞 Giỏ có bia: hỏi giấy tờ trước khi bán.</span>${x.cmd('🪪 Kiểm tuổi','gr_id',{task:t.id},'small',t.age!=null)}</div>`:''}
      <h4 class="section-title">2 · Kệ hàng (quét thêm từng món)</h4>${shelfTiles(t,x)}
      <h4 class="section-title">3 · Bảng khuyến mãi tuần này</h4>${promoBoard(t,x)}`
    :`<h4 class="section-title">Thanh toán · ${x.esc(METHOD[m][1])}</h4>${m==='cash'?cashPanel(t,x):m==='transfer'?transferPanel(t,x):creditPanel(t,x)}`;
  const side=`${receipt(t,x)}${basket?basketChecklist(t,x):''}`;
  const empty=!Object.keys(t.scanned).length&&!Object.keys(t.weighed).length;
  const cta=basket?x.cmd('🧾 CHỐT BILL','gr_total',{task:t.id},'primary big grow',empty||t.haggle?.state==='ask'):payCta(t,x);
  return `<div class="workbench"><section class="wb-main">${main}</section><aside class="wb-side">${side}</aside></div>${billbar(x,t.total??cartTotal(t,x),cta,basket?'Đang tính':'Tổng bill')}`;
}

/* ------------------------------------------------------------ rush hour */
function rushJob(t,x){
  const r=t.rush,queue=t.needs.queue,o=r.offer,turn=x.room.turn,dl=t.deadlines||[];
  const done=Object.fromEntries((r.log||[]).map(v=>[v.i,v.status]));
  const row=queue.map((q,i)=>{const w=who(x,q.npc),st=done[i],left=dl[i]!=null?dl[i]-turn:null;
    const cls=st==='served'?'served':st?'gone':i===r.i?'now':left!=null&&left<=1?'hurry':'';
    const badge=st==='served'?'✓':st==='left'?'🚶':st==='empty'?'∅':i===r.i?'▶':left!=null?`${Math.max(0,left)}`:'…';
    return `<li class="gr-qp ${cls}" title="${x.esc(w.display_name)}">${x.portrait(w,34)}<b aria-label="${st==='served'?'đã xong':st?'đã về':left!=null?`còn ${Math.max(0,left)} nhịp`:''}">${badge}</b></li>`;}).join('');
  const head=`<div class="gr-queue"><small>Hàng chờ · số trên đầu là nhịp còn chờ được</small><ol>${row}</ol></div>`;
  if(r.i>=queue.length||!o)return `${head}<div class="card"><p>Hàng chờ đã vãn.</p></div>`;
  const q=queue[r.i],w=who(x,q.npc),beer=q.items.some(([id])=>id==='beer'),aged=r.ages?.[String(r.i)];
  const lines=q.items.map(([id,qty])=>{const it=item(x,id),u=o.units[id]||0,cut=u<qty;
    return `<div class="gr-line ${cut?'blocked':''}"><span class="gr-emoji">${it.emoji}</span><div class="grow"><b>${x.esc(it.name)}</b><small>${qty} ${x.esc(it.unit)} × ${x.fmt(price(x,id))} xu${cut?(id==='beer'&&aged!=null&&aged<18?' · không bán (dưới 18)':` · kệ chỉ còn ${u}`):''}</small></div></div>`;}).join('');
  const left=dl[r.i]!=null?dl[r.i]-turn:null;
  let act;
  if(!Object.keys(o.units||{}).length&&o.charged==null)act=`<div class="notice amber">Kệ đã hết món khách này cần.</div>${x.cmd('🙏 Xin lỗi, mời khách sau','gr_rush_total',{task:t.id,total:o.totals[0]},'primary full')}`;
  else if(o.charged==null)act=`${beer&&aged==null?`<div class="notice amber row spread"><span>🔞 Có bia: hỏi giấy tờ trước khi bán.</span>${x.cmd('🪪 Kiểm tuổi','gr_rush_id',{task:t.id},'small primary')}</div>`:''}<h4 class="section-title">Máy tính tiền · chọn tổng tiền</h4><div class="gr-choices">${o.totals.map(v=>x.cmd(`${x.fmt(v)} xu`,'gr_rush_total',{task:t.id,total:v},'gr-choice')).join('')}</div>`;
  else act=`<h4 class="section-title">Khách đưa ${o.tender.map(v=>money(x,v)).join(' ')} · thu ${x.money(o.charged)}</h4><p class="small">Thối lại bao nhiêu?</p><div class="gr-choices">${(o.changes||[]).map(v=>x.cmd(`${x.fmt(v)} xu`,'gr_rush_change',{task:t.id,change:v},'gr-choice')).join('')}</div>`;
  return `${head}<article class="card gr-rush-now"><div class="row">${x.portrait(w,48)}<div class="grow"><div class="row spread"><h3>${x.esc(w.display_name)}</h3>${left!=null?`<span class="tag ${left<=1?'danger':'amber'}">⏳ còn ${Math.max(0,left)} nhịp</span>`:''}</div><p class="small">“${x.esc(q.note)}”</p></div></div>
    <div class="gr-basket">${lines}</div>${act}</article>
    <p class="muted small">Đã thu ${x.money(r.cash)} · ${r.served} khách xong${r.left?` · ${r.left} khách bỏ về`:''}. Không cần khuyến mãi ở giờ cao điểm.</p>`;
}

/* ------------------------------------------------------------ bulk orders */
function bulkJob(t,x){
  const b=t.bulk,n=t.needs,inv=x.room.inventory||{stock:{}},held=x.room.data?.held||{};
  const list=sum(n.lines.map(l=>price(x,l.item)*l.qty));
  const shortOf=l=>Math.max(0,l.qty-Math.max(0,(inv.stock?.[l.item]||0)-(held[l.item]||0)));
  const rows=n.lines.map(l=>{const it=item(x,l.item),s=shortOf(l);
    return `<div class="gr-line ${s?'':'done'}"><span class="gr-emoji">${it.emoji}</span><div class="grow"><b>${x.esc(it.name)} × ${l.qty}</b><small>${x.fmt(price(x,l.item))} xu/${x.esc(priceUnit(x,l.item))} · kho còn ${inv.stock?.[l.item]||0}${s?` · <b class="bad">thiếu ${s}</b>`:' ✓'}</small></div>
      ${b.stage==='deliver'&&s?x.confirmCmd(`⚡ Nhập ${Math.min(30,s)}`,'inv_order',{item:l.item,qty:Math.min(30,s),supplier:'express'},`Nhập hỏa tốc ${Math.min(30,s)} ${it.unit} ${it.name} · khoảng ${x.fmt(Math.ceil(it.cost*Math.min(30,s)*1.35))} xu? Hỏa tốc 30–60 phút, nhớ mở thùng đếm ở Kho & giá.`,'small ghost'):''}</div>`;}).join('');
  let body='',cta='';
  if(b.stage==='quote'){
    const last=b.offers.length?b.offers[b.offers.length-1]:-1;
    body=`<h4 class="section-title">Báo giá sỉ · giá lẻ ${x.money(list)}</h4><p class="small muted">Bớt nhiều thì dễ chốt nhưng mỏng lời. Khách chỉ nghe báo giá tối đa 2 lần${b.offers.length?' — còn 1 lần':''}.</p>
      <div class="gr-choices">${(x.cc.bulk_offers||[0,5,10,15]).filter(v=>v>last).map(v=>x.cmd(`${v?`Bớt ${v}%`:'Giá lẻ'} · ${x.fmt(Math.floor(list*(100-v)/100))} xu`,'gr_bulk_quote',{task:t.id,off:v},'gr-choice')).join('')}</div>`;
  }else if(b.stage==='deliver'){
    const short=n.lines.some(l=>shortOf(l)>0);
    body=`<div class="notice ${short?'amber':'green'}">Đã chốt ${x.money(b.price)} · nhận cọc ${x.money(b.deposit)}. ${short?'Kho còn thiếu hàng: nhập thêm rồi mở thùng đếm ở “Kho & giá”.':'Kho đủ hàng, soạn và giao được rồi!'} Giao trước khi đóng ca, không thì phải hoàn cọc.</div>
      ${short?x.confirmCmd('Giao phần đang có','gr_bulk_deliver',{task:t.id,partial:true},'Giao thiếu hàng: chỉ thu phần đã giao và khách sẽ không vui. Giao luôn?','ghost small'):''}`;
    cta=x.confirmCmd('🚚 SOẠN HÀNG & GIAO','gr_bulk_deliver',{task:t.id},`Soạn đủ hàng và giao, thu nốt ${x.fmt(b.price-b.deposit)} xu?`,'primary big grow',short);
  }
  return `<div class="card gr-bulk"><div class="gr-basket">${rows}</div>${body}</div>${cta?billbar(x,b.price,cta,'Giá đã chốt'):''}`;
}

/* ------------------------------------------------------------ shelf */
function planned(t,x){
  const set=[...t.shelf.order,...t.shelf.cart];
  const cur=x.ui.orderFor===t.id?(x.ui.order||[]):null;
  if(!cur||cur.length!==set.length||!cur.every(v=>set.includes(v))){x.ui.order=set.slice();x.ui.orderFor=t.id;}
  return x.ui.order;
}
function lotCard(t,l,x,pos){
  const sh=t.shelf,day=x.room.day,left=l.exp==null?null:l.exp-day,on=sh.order.includes(l.id);
  const cls=left==null?'unknown':left<0?'expired':left===0?'today':left<=2?'near':'fresh';
  const text=left==null?'HSD: chưa đọc':left<0?`HSD ${l.exp} · QUÁ HẠN`:left===0?`HSD ${l.exp} · hết hạn hôm nay`:`HSD ngày ${l.exp} · còn ${left} ngày`;
  const it=item(x,t.needs.item);
  return `<div class="gr-lot ${cls} ${l.new?'new':''}"><div class="gr-lot-art">${Array.from({length:Math.min(6,l.qty)},()=>it.emoji).join('')}${l.marked?'<em class="gr-sticker">−30%</em>':''}</div>
    <b>${l.new?'Thùng mới':'Lô '+x.esc(l.id)} · ${l.qty} ${x.esc(it.unit)}</b><small>${x.esc(text)}</small>
    <div class="row wrap">${left==null?x.cmd('🔍 Đọc hạn','gr_check',{task:t.id,lot:l.id},'small'):''}
      ${on&&left!=null?x.cmd('🗑️ Rút','gr_pull',{task:t.id,lot:l.id},'small ghost'):''}
      ${left!=null&&!l.marked?x.cmd('🏷️ −30%','gr_mark',{task:t.id,lot:l.id},'small ghost'):''}
      ${pos!=null?`${carBtn(x,'◀','move',{lot:l.id,dir:-1},'small ghost')}${carBtn(x,'▶','move',{lot:l.id,dir:1},'small ghost')}`:''}</div></div>`;
}
function shelfJob(t,x){
  const sh=t.shelf,lots=Object.fromEntries(t.lots.map(l=>[l.id,l])),it=item(x,t.needs.item),p=price(x,t.needs.item);
  const plan=planned(t,x);
  const all=[...sh.order,...sh.cart].map(id=>lots[id]);
  const day=x.room.day,left=l=>l.exp==null?null:l.exp-day;
  const known=all.every(l=>l.exp!=null);
  const exps=plan.map(id=>lots[id].exp);
  const sorted=known&&exps.every((v,i)=>!i||exps[i-1]<=v);
  const rows=[
    [known?true:null,'Đọc hạn tất cả các lô',`${all.filter(l=>l.exp!=null).length}/${all.length}`],
    [known?!sh.order.some(id=>left(lots[id])<=0):null,'Không còn lô hết hạn trên kệ',''],
    [known?all.filter(l=>left(l)>=1&&left(l)<=2).every(l=>l.marked):null,`Dán tem giảm ${x.cc.markdown}% cho lô còn 1–2 ngày`,''],
    [known?sorted:null,'Hạn gần ở trước, hàng mới ở sau (FIFO)',''],
    [sh.tag===p,'Tem giá khớp bảng giá',`${sh.tag} / ${p} xu`],
    [sh.placed&&!sh.cart.length?true:null,'Đã xếp thùng mới lên kệ',''],
  ];
  const main=`<h4 class="section-title">1 · Kệ ${x.esc(it.name)} (mặt kệ → trong cùng)</h4>
    <div class="gr-shelf">${plan.map((id,i)=>lotCard(t,lots[id],x,i)).join('')}</div>
    ${sh.pulled.length?`<p class="muted small">Đã rút khỏi kệ: ${sh.pulled.map(v=>x.esc(v)).join(', ')}</p>`:''}
    <div class="row wrap space-top">${x.cmd('📐 Xếp kệ theo thứ tự này','gr_place',{task:t.id,order:plan},'primary')}${carBtn(x,'Sắp theo hạn đã đọc','autosort',{},'ghost small')}</div>
    <h4 class="section-title">2 · Tem giá</h4><div class="gr-tag row"><div class="gr-pricetag"><small>${x.esc(it.name)}</small><b>${x.fmt(sh.tag)} xu</b><small>/${x.esc(it.unit)}</small></div>
    <div class="grow"><p class="small">Bảng giá hiện hành: <b>${x.money(p)}</b></p>${x.cmd('🖨️ In lại tem giá','gr_retag',{task:t.id},'small ghost',sh.retagged||sh.tag===p)}</div></div>
    <ul class="muted small gr-policy">${(x.cc.policy||[]).map(v=>`<li>${x.esc(v)}</li>`).join('')}</ul>`;
  const cta=x.confirmCmd('✅ BÁO CÔ BA ĐÃ XẾP XONG','gr_shelf_done',{task:t.id},'Cô Ba sẽ đi một vòng kiểm hạn, tem và thứ tự kệ. Báo xong nhé?','primary big grow',!sh.placed||sh.cart.length>0);
  return `<div class="workbench"><section class="wb-main">${main}</section><aside class="wb-side">${checklist(x,rows)}</aside></div>${billbar(x,null,cta)}`;
}

/* ------------------------------------------------------------ stock & price tags */
function supplierPick(x){
  const sups=x.content.inventory?.suppliers||[],cur=x.ui.sup||'partner';
  const short={market:'Chợ đầu mối',partner:'Nhà phân phối',express:'Hỏa tốc'};
  return `<div class="gr-sups" role="radiogroup" aria-label="Nhập từ">${sups.map(s=>`<button type="button" role="radio" aria-checked="${s.id===cur}" class="gr-sup ${s.id===cur?'on':''}" data-action="car:sup" data-sup="${s.id}" title="${x.esc(s.name)}"><b>${x.esc(s.emoji)} ${x.esc(short[s.id]||s.name)}</b><small>${x.esc(s.quote?.label||s.window||(s.lead===0?'có ngay':''))} · ${s.factor<1?'rẻ':s.factor>1?'đắt':'giá gốc'}${s.short>=15?' · hay thiếu':''}</small></button>`).join('')}</div>`;
}
function incoming(x){
  const inv=x.room.inventory||{},orders=(inv.orders||[]).filter(o=>o.status==='in_transit'||(o.status==='received'&&o.actual<o.qty&&!o.claimed&&o.day===x.room.day));
  if(!orders.length)return '';
  return `<div class="gr-incoming"><h4>🚚 Hàng đang về</h4>${orders.map(o=>{const it=item(x,o.item);
    if(o.status==='received')return `<div class="gr-inrow"><span>${it.emoji} ${x.esc(it.name)}: nhận ${o.actual}/${o.qty}</span>${x.cmd('📝 Báo thiếu','inv_claim',{order:o.id},'small ghost')}</div>`;
    return `<div class="gr-inrow"><span>${it.emoji} ${x.esc(it.name)} × ${o.qty}</span>${o.ready_now?x.button('📦 Mở thùng & đếm','v4InvOpen',{order:o.id},'small primary'):`<small class="muted">đang trên đường…</small>`}</div>`;}).join('')}</div>`;
}
function stockView(x){
  const inv=x.room.inventory||{stock:{},expiring:{},locked:[],orders:[]},d=x.room.data||{},rv=rivalOf(x);
  const cap=inv.capacity||60,sups=x.content.inventory?.suppliers||[],sup=sups.find(s=>s.id===(x.ui.sup||'partner'))||{factor:1,lead:1,name:''};
  const qty=Number(x.ui.qty)||10,cleared=d.cleared||[];
  const rot=new Set((d.rotation||[]).map(r=>r.item)),short=Object.fromEntries((d.forecast?.needs||[]).filter(r=>r.short).map(r=>[r.item,r]));
  const rows=catalogue(x).map(it=>{
    const locked=(inv.locked||[]).includes(it.id),q=inv.stock?.[it.id]??0,exp=inv.expiring?.[it.id]||0,near=d.near?.[it.id]||0,held=d.held?.[it.id]||0;
    const p=price(x,it.id),[lo,hi]=d.price_range?.[it.id]||[p,p],step=Math.max(1,Math.round((x.cc.base_prices?.[it.id]||p)*0.05));
    const transit=(inv.orders||[]).filter(o=>o.item===it.id&&o.status==='in_transit').reduce((s,o)=>s+o.qty,0);
    const room=cap-q-transit,n=Math.min(qty,room,30),cost=Math.max(1,Math.ceil(it.cost*n*sup.factor));
    const theirs=rv[it.id];
    if(locked)return `<div class="gr-srow locked"><span class="gr-emoji">${it.emoji}</span><div class="gr-sinfo"><b>${x.esc(it.name)}</b><small>🔒 mở ở cấp ${it.unlock||1}</small></div></div>`;
    return `<div class="gr-srow ${q<=3?'low':''} ${exp?'exp':''}"><span class="gr-emoji">${it.emoji}</span>
      <div class="gr-sinfo"><b>${x.esc(it.name)}</b><div class="gr-sbar" aria-hidden="true"><i style="width:${Math.min(100,q/cap*100)}%"></i></div>
        <small>Còn <b>${q}</b> ${x.esc(stockUnit(x,it.id))}${held?` · ${held} đang giữ trên bill`:''}${transit?` · 🚚 ${transit} đang về`:''}</small>
        ${exp?`<small class="bad">⚠ ${exp} hết hạn hôm nay</small>`:''}${near?`<small class="warn">⏳ ${near} HSD ngày mai — nên xả giá</small>`:''}${rot.has(it.id)?'<small class="warn">🔄 kệ chưa xoay</small>':''}${short[it.id]?`<small class="warn">📅 mai cần ~${short[it.id].want}, thiếu ${short[it.id].short}</small>`:''}</div>
      <div class="gr-sprice"><div class="gr-tagbox">${x.cmd('−','gr_tag',{item:it.id,price:p-step},'small ghost gr-step',p-step<lo)}<span class="gr-ptag" aria-label="Giá ${p} xu">${x.fmt(p)}<small>/${x.esc(priceUnit(x,it.id))}</small></span>${x.cmd('+','gr_tag',{item:it.id,price:p+step},'small ghost gr-step',p+step>hi)}</div>
        ${theirs!=null?`<small class="${p>theirs?'bad':'ok'}">Mây Mart ${x.fmt(theirs)}</small>`:''}</div>
      <div class="gr-sact">${exp?x.confirmCmd('🗑️ Rút hàng hết hạn','gr_pull_today',{item:it.id},`Rút ${exp} ${stockUnit(x,it.id)} ${it.name} hết hạn hôm nay khỏi kệ? Ghi vào hao hụt.`,'small danger'):''}
        ${near&&!exp&&!cleared.includes(it.id)?x.cmd(`🏷️ Xả ${near>12?12:near} món −${100-(x.cc.clear_percent||70)}%`,'gr_clear',{item:it.id},'small ghost'):''}
        ${n>0?x.confirmCmd(`📦 Nhập ${n} · ${x.fmt(cost)} xu`,'inv_order',{item:it.id,qty:n,supplier:sup.id||'partner'},`Nhập ${n} ${stockUnit(x,it.id)} ${it.name} từ ${sup.name} · ${x.fmt(cost)} xu? ${`Dự kiến nhận: ${sup.quote?.eta_label||sup.window||'sớm'}.`}, mở thùng đếm rồi mới lên kệ.`,'small ghost'):'<small class="muted">Kho đầy</small>'}</div></div>`;
  }).join('');
  return `<div class="card gr-stock"><div class="row spread"><h4>🏷️ Kho & giá</h4><small class="muted">Sức chứa ${cap} mỗi loại</small></div>
    ${rotationNotes(x)}${incoming(x)}
    <div class="gr-orderbar"><small>Nhập từ</small>${supplierPick(x)}<div class="gr-qty" role="radiogroup" aria-label="Số lượng mỗi lần nhập">${[5,10,20,30].map(v=>`<button type="button" role="radio" aria-checked="${v===qty}" class="btn small ${v===qty?'primary':'ghost'}" data-action="car:qty" data-qty="${v}">${v}</button>`).join('')}</div></div>
    <div class="gr-stock-list">${rows}</div>
    <ul class="muted small gr-policy">${(x.cc.stock_rules||[]).map(v=>`<li>${x.esc(v)}</li>`).join('')}</ul></div>`;
}

/* ------------------------------------------------------------ ledger */
function ledgerRow(x,r){
  const pct=r.limit_now?Math.min(100,r.balance/r.limit_now*100):100,stars='★'.repeat(r.trust)+'☆'.repeat(5-r.trust);
  const tags=[r.hard?`<span class="tag amber">🙁 Đang kẹt tiền</span>`:'',r.plan?`<span class="tag blue">📅 Trả góp ${x.fmt(r.plan.each)} xu × ${r.plan.left} · kỳ tới ngày ${r.plan.next}</span>`:'',
    r.overdue&&!r.plan?`<span class="tag danger">Quá hạn ${r.age} ngày</span>`:'',r.risk?'<span class="tag danger">Sắp mất trắng</span>':'',!r.can_credit&&!r.plan&&r.trust<=0?'<span class="tag danger">Ngưng ghi sổ</span>':''].join('');
  const acts=r.balance?(r.plan?'':`${x.cmd(r.reminded_today?'Đã nhắc':'💬 Nhắc nợ','gr_remind',{npc:r.npc},'small ghost',r.reminded_today)}
      ${[2,3].map(n=>x.cmd(`🤝 Giãn ${n} kỳ`,'gr_plan',{npc:r.npc,parts:n},r.hard?'small primary':'small ghost')).join('')}`):'';
  return `<article class="gr-lrow ${r.overdue?'overdue':''} ${r.hard?'hard':''}"><div class="gr-lhead"><div class="grow"><b>${x.esc(r.name)}</b><small>${x.esc(r.role)}</small></div>
      <div class="gr-trust" aria-label="Lòng tin ${r.trust}/5: ${x.esc(r.trust_name)}"><span aria-hidden="true">${stars}</span><small>${x.esc(r.trust_name)}</small></div></div>
    <div class="gr-lnum"><b>${x.money(r.balance)}</b><small>/ hạn mức ${x.fmt(r.limit_now)}${r.balance?` · ${r.age} ngày`:''}</small></div>
    <div class="bar ${r.balance>r.limit_now*0.8?'low':''}" aria-hidden="true"><i style="width:${pct}%"></i></div>
    ${tags?`<div class="gr-ltags">${tags}</div>`:''}${r.hard?`<p class="small gr-hard">“${x.esc(r.hard)}” — ${r.plan?'lịch trả góp vẫn chạy, cứ để người ta trả theo kỳ.':'đừng nhắc nợ lúc này, giãn nợ thì vẫn trả được.'}</p>`:''}
    ${r.written?`<p class="small muted">Đã gạch sổ (mất trắng) ${x.fmt(r.written)} xu.</p>`:''}${acts?`<div class="gr-lacts">${acts}</div>`:''}</article>`;
}
function ledgerView(x){
  const d=x.room.data||{},rows=d.ledger_view||[];
  return `<div class="card gr-ledger"><h4>📒 Sổ ghi nợ hàng xóm</h4><p class="muted small">Lòng tin quyết định hạn mức. Nhắc nợ nhẹ nhàng, riêng tư, mỗi ngày tối đa một lần. Nợ quá ${x.cc.overdue_days} ngày thì chưa ghi thêm.</p>
    ${rows.map(r=>ledgerRow(x,r)).join('')}
    ${fold('Luật sổ nợ có tình',`<ul class="small gr-policy">${[...(x.cc.credit_rules||[]),...(x.cc.care_rules||[]).slice(0,3)].map(v=>`<li>${x.esc(v)}</li>`).join('')}</ul>`)}
    <p class="small space-top">Đã thu nợ: ${x.money(d.repaid||0)}${d.stats?.bad_debt?` · mất trắng: ${x.money(d.stats.bad_debt)}`:''} · Doanh thu quầy hôm nay: ${x.money(d.day_sales||0)}</p></div>`;
}

/* ------------------------------------------------------------ care loop */
function foldBox(x,key,summary,body,auto=false,cls=''){
  const open=x.ui.open?.[key]??auto;
  return `<details class="fold gr-fold ${cls}"${open?' open':''}><summary data-action="car:fold" data-key="${x.esc(key)}">${summary}</summary><div class="fold-body">${body}</div></details>`;
}
const CARE_MARK={true:['ok','✓','xong'],false:['bad','!','cần làm ngay'],null:['','○','chưa làm']};
function careAct(x,r){
  const d=r.do;if(!d)return '';
  if(d.tab)return carBtn(x,'Xem','tab',{tab:d.tab},'small ghost');
  if(d.cmd==='gr_pull_today')return x.confirmCmd('🗑️ Rút','gr_pull_today',{item:d.item},'Rút hàng hết hạn hôm nay khỏi kệ? Giá trị được ghi vào hao hụt.','small danger');
  if(d.cmd==='gr_rotate')return x.cmd('🔄 Xoay','gr_rotate',{item:d.item},'small');
  if(d.cmd==='gr_pack')return x.cmd('🧺 Soạn','gr_pack',{npc:d.npc},'small');
  if(d.cmd==='gr_remind')return x.cmd('💬 Nhắc','gr_remind',{npc:d.npc},'small ghost');
  return '';
}
/* reqList rows with one action button each (same markup and styles as ui-kit reqList). */
function careList(x,rows,label){
  return `<ul class="req-list gr-care" aria-label="${x.esc(label)}">${rows.map(r=>{const [cls,mark,said]=CARE_MARK[r.ok===true?'true':r.ok===false?'false':'null'];
    return `<li class="req-row ${cls}${r.tone?' tone-'+x.esc(r.tone):''}"><span class="req-mark" aria-label="${said}">${mark}</span><span class="req-icon" aria-hidden="true">${x.esc(r.icon||'')}</span><span class="req-label">${x.esc(r.label)}${r.note?`<small>${x.esc(r.note)}</small>`:''}</span>${careAct(x,r)}</li>`;}).join('')}</ul>`;
}
function careCard(x){
  const rows=x.room.data?.care||[];
  const todo=rows.filter(r=>r.ok!==true).length,urgent=rows.some(r=>r.ok===false);
  const summary=`📋 Việc chăm hôm nay · ${todo?`<b class="${urgent?'bad':''}">${todo} việc</b>`:'đã gọn'}`;
  const body=rows.length?careList(x,rows,'Việc chăm hôm nay'):'<p class="small muted">Kệ đúng hạn, sổ nợ yên ổn, không có giỏ quen nào phải soạn. Tiệm gọn gàng!</p>';
  return `<section class="gr-carebox">${foldBox(x,'care',summary,body,todo>0)}</section>`;
}
function forecastBody(x,f){
  const need=reqList(f.needs.map(r=>{const it=item(x,r.item);return {ok:r.short?null:true,icon:it.emoji,label:it.name,
    note:r.short?`thiếu khoảng ${r.short} ${stockUnit(x,r.item)} — nhập hôm nay cho kịp`:'',value:`${r.have}/~${r.want}`,tone:r.short?'warn':''};}),x.esc,'Hàng cần cho ngày mai');
  const lists=f.lists.length?`<p class="small">🧺 Giỏ quen ghé lấy: <b>${f.lists.map(l=>x.esc(l.name)).join(', ')}</b></p>`:'';
  const pay=f.pay.length?`<p class="small">💰 Dự kiến trả nợ: ${f.pay.map(p=>`${x.esc(p.name)} ${x.fmt(p.amount)} xu${p.how==='plan'?' (trả góp)':''}`).join(' · ')}</p>`:'';
  return `<p class="small"><b>${x.esc(f.mod.emoji)} ${x.esc(f.mod.name)}</b> — ${x.esc(f.mod.text)}</p>
    <p class="small muted">Ngày kia: ${x.esc(f.after.emoji)} ${x.esc(f.after.name)}</p>${lists}${pay}
    ${f.needs.length?`<p class="gr-sub">Hàng cho mấy lượt khách đầu ngày mai <small>(còn dùng được / cần)</small></p>${need}`:''}
    <p class="small gr-tip">💡 ${x.esc(f.tip)}</p>`;
}
function forecastCard(x){
  const f=x.room.data?.forecast;if(!f)return '';
  const summary=`📅 Ngày mai: ${x.esc(f.mod.emoji)} ${x.esc(f.mod.name)}${f.short?` · <b class="warn">thiếu ${f.short} món</b>`:''}${f.lists.length?` · 🧺 ${f.lists.length}`:''}`;
  return `<section class="gr-forecast">${foldBox(x,'forecast',summary,forecastBody(x,f))}</section>`;
}
function rotationNotes(x){
  const rows=x.room.data?.rotation||[];if(!rows.length)return '';
  return `<div class="gr-rotations">${rows.map(r=>{const it=item(x,r.item);
    return `<div class="notice amber gr-rot"><span aria-hidden="true">🔄</span><p class="grow"><b>Kệ ${x.esc(it.name)} chưa xoay</b><small>Hàng mới (HSD ngày ${r.front}) nằm trước ${r.back_qty} ${x.esc(stockUnit(x,r.item))} HSD ngày ${r.back}: khách lấy hàng mới, lô cũ sẽ hết hạn trên kệ.</small></p>${x.cmd('🔄 Xoay kệ','gr_rotate',{item:r.item},'small')}</div>`;}).join('')}</div>`;
}
const hearts=n=>'♥'.repeat(n)+'♡'.repeat(Math.max(0,5-n));
function listCard(x,l){
  const w=x.npc(l.npc),today=l.when==='today',inv=x.room.inventory||{stock:{}};
  const rows=l.items.map(i=>{const it=item(x,i.item),have=inv.stock?.[i.item]??0;
    return today?{ok:i.packed>=i.qty?true:null,icon:it.emoji,label:`${i.qty} ${stockUnit(x,i.item)} ${it.name}`,value:`${i.packed}/${i.qty}`,note:i.packed<i.qty&&have<i.qty-i.packed?`kho còn ${have}`:''}
      :{ok:have>=i.qty?true:null,icon:it.emoji,label:`${i.qty} ${stockUnit(x,i.item)} ${it.name}`,value:`kho ${have}`,tone:have<i.qty?'warn':''};});
  const full=l.items.every(i=>i.packed>=i.qty),pay={cash:'💵 tiền mặt',transfer:'📱 chuyển khoản',credit:'📒 ghi sổ'}[l.pay]||'';
  return `<article class="card gr-list ${today?'today':''}"><div class="row">${x.portrait(w,40)}<div class="grow"><div class="row spread wrap"><h4>${x.esc(l.name)}</h4><span class="tag ${today?(full?'green':'amber'):'blue'}">${today?(full?'Đã soạn · chờ khách':'Hôm nay · ghé lúc đóng ca'):'Ngày mai'}</span></div>
    <p class="small muted">“${x.esc(l.say)}”</p></div></div>
    ${reqList(rows,x.esc,'Danh sách giỏ quen')}
    ${l.stale?`<p class="small bad">⚠ ${l.stale} món trong giỏ hết hạn hôm nay — khách sẽ không vui.</p>`:''}
    <div class="row spread wrap space-top"><small class="muted">Khoảng ${x.fmt(l.value)} xu · ${pay}</small>${today&&!full?x.cmd('🧺 Soạn giỏ','gr_pack',{npc:l.npc},'small primary'):today?'':'<small class="muted">Nhập đủ hàng hôm nay, mai soạn.</small>'}</div></article>`;
}
function listsView(x){
  const d=x.room.data||{},ls=d.lists_view||[],regs=Object.values(d.lists||{});
  const book=regs.map(r=>`<li><b>${x.esc(r.name||'')}</b><span class="gr-hearts" aria-label="Thân tình ${r.bond}/5">${hearts(r.bond)}</span><small>${x.esc(r.bond_name||'')} · lấy giỏ: ${r.next===x.room.day?'hôm nay':r.next===x.room.day+1?'ngày mai':'ngày '+r.next}${r.bond>=(x.cc.bond_calm||4)?' · không so giá Mây Mart':''}</small></li>`).join('');
  return `<div class="gr-lists"><p class="small muted">Khách quen đặt giỏ hàng tuần: xem trước một ngày để nhập hàng, soạn trong ngày, khách ghé lấy lúc đóng ca.</p>
    ${ls.length?ls.map(l=>listCard(x,l)).join(''):'<div class="card"><p class="small">Hôm nay và ngày mai không có giỏ quen nào.</p></div>'}
    <section class="card gr-bonds"><h4>💛 Khách quen</h4><ul>${book}</ul>${fold('Thân tình để làm gì?',`<p class="small">Giỏ đủ món, tươi: +1. Không soạn hoặc soạn phải hàng hết hạn: −1. Từ “${x.esc((x.cc.bond_names||[])[3]||'')}” khách gửi thêm tiền bồi dưỡng; từ “${x.esc((x.cc.bond_names||[])[x.cc.bond_calm||4]||'')}” khách không mang tờ rơi Mây Mart ra so giá nữa.</p>`)}</section></div>`;
}

function tabBody(x,work,idle=false){
  const tab=curTab(x,idle);
  if(tab==='lists')return listsView(x);
  if(tab==='ledger')return ledgerView(x);
  if(tab==='stock')return stockView(x);
  return work();
}

export default {
  id:ID,
  css:true,
  next(t){
    if(!t.known)return t.kind==='shelf'?'Nghe Cô Ba dặn việc kệ':t.kind==='rush'?'Mời hàng chờ vào':t.kind==='bulk'?'Nghe khách đặt đơn sỉ':'Mời khách đặt giỏ lên quầy';
    if(t.kind==='shelf'){
      const sh=t.shelf;
      if(!sh.placed||sh.cart.length)return 'Đọc hạn, rút/dán tem rồi xếp kệ';
      return 'Kiểm tem giá rồi báo xong';
    }
    if(t.kind==='rush')return 'Tính nhanh, thối đúng cho từng khách';
    if(t.kind==='bulk')return t.bulk.stage==='quote'?'Báo giá sỉ cho khách':'Đủ hàng thì soạn & giao';
    if(t.stage==='basket'){
      if(t.haggle?.state==='ask')return 'Trả lời khách chuyện giá';
      if(hasBeer(t)&&t.age==null)return 'Kiểm tuổi khách mua bia';
      return 'Quét, cân, áp khuyến mãi rồi chốt bill';
    }
    const m=methodOf(t);
    return m==='cash'?'Soi tiền và thối đúng':m==='transfer'?'Kiểm app ngân hàng của tiệm':'Xem sổ nợ rồi quyết định';
  },
  job(t,x){
    const w=x.npc(t.npc),top=`${todayStrip(x)}${deskCard(x)}`;
    if(x.room.data?.desk?.ev)return `<div class="career-job gr">${top}<p class="small muted" role="note">Khách và kệ hàng chờ một chút: quyết xong chuyện này rồi làm tiếp nhé.</p></div>`;
    if(!t.known){
      const label=t.kind==='shelf'?'📋 Nhận việc':t.kind==='rush'?'⏱️ Mở quầy cho hàng chờ':t.kind==='bulk'?'📦 Nghe đơn sỉ':'🛒 Mời khách đặt hàng lên quầy';
      return `<div class="career-job gr">${top}<article class="card ticket"><div class="row">${x.portrait(w,56)}<div class="grow"><h3>${x.esc(w.display_name)}</h3><p class="small"><b>${x.esc(t.title)}</b></p><p>“${x.esc(t.opening)}”</p></div></div>
        ${x.cmd(label,'ask',{task:t.id},'primary full')}</article>${careCard(x)}${forecastCard(x)}${tabs(x)}${(x.ui.tab||'counter')!=='counter'?tabBody(x,()=>''):''}</div>`;
    }
    const work=()=>t.kind==='shelf'?shelfJob(t,x):t.kind==='rush'?rushJob(t,x):t.kind==='bulk'?bulkJob(t,x):checkoutJob(t,x);
    const tab=curTab(x,false),side=tab==='counter'?'':`${careCard(x)}${tab==='stock'?forecastCard(x):''}`;
    return `<div class="career-job gr">${top}${ticket(t,x)}${tabs(x)}${side}${tabBody(x,work)}</div>`;
  },
  idle(x){
    if(x.room.data?.desk?.ev)return `<div class="career-job gr">${todayStrip(x)}${deskCard(x)}</div>`;
    return `<div class="career-job gr">${todayStrip(x)}${deskCard(x)}<p class="small muted">Giữa hai lượt khách: chăm kệ, soạn giỏ quen, xem sổ nợ và chuẩn bị cho ngày mai.</p>
      ${careCard(x)}${forecastCard(x)}${tabs(x,true)}${tabBody(x,()=>'',true)}</div>`;
  },
  actions:{
    async tab(data,el,x){x.ui.tab=['ledger','stock','lists'].includes(data.tab)?data.tab:'counter';x.render();},
    // Remember a fold's state across re-renders (the click lands before the browser toggles it).
    async fold(data,el,x){(x.ui.open??={})[data.key]=!el.closest('details')?.open;},
    async sup(data,el,x){x.ui.sup=data.sup;x.render();},
    async qty(data,el,x){x.ui.qty=Number(data.qty)||10;x.render();},
    async seen(data,el,x){x.ui.seenLast=data.key;x.render();},
    async scale(data,el,x){const i=Number(data.line);x.ui.scale=i>=0?i:null;x.ui.scaleFor=i>=0?data.task:null;x.ui.tare=false;x.render();},
    async tare(data,el,x){x.ui.tare=!x.ui.tare;x.render();},
    async move(data,el,x){
      const o=x.ui.order||[],i=o.indexOf(data.lot),j=i+Number(data.dir);
      if(i<0||j<0||j>=o.length)return;
      [o[i],o[j]]=[o[j],o[i]];x.render();
    },
    async autosort(data,el,x){
      const t=x.room.tasks.find(v=>v.id===x.ui.orderFor);if(!t)return;
      const exp=Object.fromEntries(t.lots.map(l=>[l.id,l.exp]));
      if((x.ui.order||[]).some(id=>exp[id]==null)){x.toast('Đọc hạn tất cả các lô trước đã nhé.');return;}
      x.ui.order.sort((a,b)=>exp[a]-exp[b]);x.render();
    },
  },
  // The sticky bill bar rides above the sheet's own sticky footer.
  tick(root){keepBarAboveFooter(root);},
  dock:[['inventory','box','Kho','Nhập & đếm hàng']],
};
