/** 🚗 Xe & phương tiện: bicycles, motorbikes, cars, yachts and private planes, bought outright (story mode).
 * Every rule and number lives in game/garage.py; this file renders api.state.journey.garage with the static list
 * (content.journey.garage) and sends `jr_garage_*` commands. Its own dialog (like Nhà của bạn), opened with
 * data-action="garage" from the menu, the profile's ride chip and the house card. The art is the emoji on a tile
 * in the vehicle's paint, with its plate under it. Styles: /css/bank.css + /css/house.css + /css/garage.css.
 * 🔨 16/10: the auction's plates (gold) are attached to a vehicle here (jr_garage_plate); the vehicle ridden with one
 * shows its "+x % lợi nhuận mỗi ca" (game/garage.py bonus_now); the limited editions are listed with their number,
 * never in the shop and never sold back. */
import {icon,escapeHTML as esc} from '../icons.js';
import {paint as sheetPaint} from './sheet-paint.js';

const S={dlg:null,env:null,tab:'',view:'list',pick:null,busy:false,flash:null,listening:false};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,op,data={},cls='',why='')=>`<button type="button" class="btn ${cls}" data-gr="${op}"${attrs(data)}${S.busy||why?' disabled':''}${why?` title="${esc(why)}"`:''}>${label}</button>`;
const J=()=>S.env?.api?.state?.journey||{};
const V=()=>J().garage;
const CAT=()=>S.env?.api?.content?.journey?.garage||{groups:[],vehicles:[],paints:[]};
const item=id=>CAT().vehicles.find(x=>x.id===id);
const paint=id=>CAT().paints.find(x=>x.id===id)||CAT().paints[0]||{hex:'#ccc',name:''};
const group=id=>CAT().groups.find(g=>g.id===id)||{};
const lname=s=>String(s||'').slice(0,1).toLowerCase()+String(s||'').slice(1);
const POCKET=['wallet','account'];   // garage.py takes the wallet first, then the bank account

/* ---- styles on first use ---- */
let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=Promise.all([link('/css/bank.css','bk-css'),link('/css/house.css','hs-css'),link('/css/garage.css','gr-css')]);

/** The vehicle's picture: its emoji on a tile in its paint, the plate under it (the owner's words, escaped). */
export function tileHTML(v,color,plate='',size='',uq=false){
  const p=paint(color||v?.paint);
  return `<span class="gr-tile ${size}${v?.limited?' limited':''}" style="--gr-paint:${esc(p.hex)}" aria-hidden="true"><span class="gr-emoji">${v?.emoji||'🚗'}</span>${plate?`<span class="gr-plate${uq?' uq':''}">${esc(plate)}</span>`:''}</span>`;
}
/** 🔨 A vanity plate won at the auction house (game/auction.py): gold. An older server (no `plates`): its dearest
 * plate showed on the vehicle in use; a newer one says which vehicle carries which plate (car.uq). */
const uqPlate=()=>{if(V()&&'plates' in V())return '';const o=J().uniq?.own||{};const x=Object.values(o).filter(v=>v?.k==='plate').sort((a,b)=>(b.p||0)-(a.p||0))[0];return x?.t||'';};
const KIND_WORD={plate:'Biển số',reg:'Số đăng ký',hull:'Biển tên'};
/** The plates won that fit this vehicle (pedal bikes carry none). */
const fitting=(v,it)=>(v?.plates||[]).filter(p=>(p.fit||[]).includes(it?.group)&&!['xe_dap','xe_dap_dien'].includes(it?.base||it?.id));

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium bk-sheet hs-sheet gr-sheet';d.setAttribute('aria-labelledby','gr-title');
  d.innerHTML='<div class="gr-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-gr]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.gr,el.dataset);
  });
  d.addEventListener('input',e=>{if(e.target.name==='plate'&&S.pick){S.pick.plate=e.target.value;const t=d.querySelector('.gr-preview');if(t)t.innerHTML=tileHTML(item(S.pick.id),S.pick.color,S.pick.plate.trim(),'big');}});
  d.addEventListener('submit',e=>e.preventDefault());
  d.addEventListener('close',()=>{S.flash=null;S.view='list';S.pick=null;});
  S.dlg=d;return d;
}
export async function openGarage(env,tab){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';env.api.addEventListener('state',()=>{const key=JSON.stringify([J().wallet,J().garage,J().bank?.balance]);if(key===seen)return;seen=key;if(S.dlg?.open&&!S.busy)render();});
  }
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();
  S.view='list';S.pick=null;
  S.tab=tab&&(tab==='mine'||group(tab).id)?tab:(V()?.cars?.length?'mine':'bike');
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
}
export async function garageAction(action,data,el,env){
  if(action!=='garage')return false;
  await openGarage(env,data?.tab);return true;
}

async function send(action,payload={}){
  const {api}=S.env;S.busy=true;render();
  try{
    const r=await api.command(action,payload);
    S.flash={text:[r.message,...(r.effects||[]).filter(Boolean)].filter(Boolean).join(' '),kind:'good'};
    return r;
  }catch(e){S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}  // quiet: api.js, the save moved under the tap twice
  finally{S.busy=false;render();S.dlg?.querySelector('.gr-body')?.scrollTo?.(0,0);}
}
const ask=(title,msg,label,money)=>S.env.confirmAction(title,msg,label,money);  // money: {cost,pocket} → "còn thiếu" (v4/money.js)

async function onClick(op,data){
  const v=V()||{};
  switch(op){
    case'close':S.dlg.close();return;
    case'tab':S.tab=data.tab;S.view='list';S.pick=null;S.flash=null;render();S.dlg.querySelector('.gr-body')?.scrollTo?.(0,0);return;
    case'back':S.view='list';S.pick=null;render();return;
    case'look':{const it=item(data.id);if(!it)return;S.view='buy';S.pick={id:it.id,color:it.paint,plate:''};S.flash=null;render();S.dlg.querySelector('.gr-body')?.scrollTo?.(0,0);return;}
    case'edit':{const c=(v.cars||[]).find(x=>x.id===data.id);if(!c)return;S.view='edit';S.pick={id:c.id,color:c.color,plate:c.plate||''};S.flash=null;render();return;}
    case'paint':if(S.pick){S.pick.color=data.color;render();}return;
    case'buy':{const p=S.pick,it=p&&item(p.id);if(!it)return;const plate=(p.plate||'').trim();
      if(await ask(`Mua ${lname(it.name)}?`,`Trả đủ ${xu(it.price)} một lần, không vay. Lấy tiền mặt trong ví trước, thiếu thì lấy từ tài khoản ngân hàng. Màu ${lname(paint(p.color).name)}${plate?`, biển tên “${plate}”`:''}.`,`Mua · ${xu(it.price)}`,{cost:it.price,pocket:POCKET})){
        const r=await send('jr_garage_buy',{id:it.id,color:p.color,...(plate?{plate}:{}),confirm:true});
        if(r){S.view='list';S.pick=null;S.tab='mine';render();}
      }return;}
    case'save':{const p=S.pick;if(!p)return;const r=await send('jr_garage_paint',{id:p.id,color:p.color,plate:(p.plate||'').trim()});if(r){S.view='list';S.pick=null;render();}return;}
    case'ride':send('jr_garage_ride',{id:data.id||null});return;
    case'trip':send('jr_garage_trip',{id:data.id});return;
    case'fix':send('jr_rui_fix',{kind:'xe',ref:data.id});return;  // 🛡️ a vehicle left broken (game/rui.py)
    case'sell':{const c=(v.cars||[]).find(x=>x.id===data.id),it=item(data.id);if(!c||!it)return;
      if(await ask(`Bán ${lname(it.name)}?`,`Mua ${xu(c.paid)}, bán lại được ${xu(c.sell)} (${CAT().sell_pct}% giá đã trả). Tiền vào ví. Bán rồi là không lấy lại được.`,`Bán · nhận ${xu(c.sell)}`))send('jr_garage_sell',{id:c.id,confirm:true});return;}
    case'house':S.dlg.close();(await import('./house.js')).openHouse(S.env);return;
    case'race':S.dlg.close();(await import('./race-track.js')).openRace(S.env,data.tab);return;   // 🏁 Độ xe & đua xe (v4/race-track.js)
    case'plates':S.view='plates';S.pick=data.id?{id:data.id}:null;S.flash=null;render();S.dlg.querySelector('.gr-body')?.scrollTo?.(0,0);return;
    case'attach':{const r=await send('jr_garage_plate',{item:data.item,id:data.id||null});if(r&&S.view==='plates'&&S.pick?.id){S.view='list';S.pick=null;render();}return;}
  }
}

/* ---- rendering ---- */
function render(){
  if(!S.dlg)return;
  sheetPaint(S.dlg.querySelector('.gr-root'),page(),'.gr-body');   // typing a plate while the wallet moves: the keyboard stays
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
function head(){
  const v=V(),ride=v?.cars?.find(c=>c.id===v.ride),it=ride&&item(ride.id);
  const back=S.view!=='list'?`<button class="icon-btn" type="button" data-gr="back" aria-label="Quay lại">${icon('back',21)}</button>`:'<span class="gr-logo" aria-hidden="true">🚗</span>';
  return `<header class="sheet-head bk-head hs-head">${back}
    <div class="grow"><span class="eyebrow">NHÀ XE · NGÀY SỐNG ${fmt(J().life_day)}</span><h2 id="gr-title">Xe &amp; phương tiện</h2><p>${it?`Đang đi: ${it.emoji} ${esc(it.name)}`:'Xe đạp, xe máy, ô tô, du thuyền, máy bay'}</p></div>
    <button class="icon-btn" type="button" data-gr="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
}
const flash=()=>`<p class="bk-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
function page(){
  const v=V();
  const note=(t,p)=>head()+`<div class="sheet-body bk hs-body gr-body"><section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🚗</div><h3>${t}</h3><p>${p}</p></section></div>`;
  if(!v)return note('Nhà xe đang mở cửa','Cửa hàng đang sắp xe ra. Mở lại sau ít phút nhé.');   // an older server: no garage yet
  if(!v.story)return note('Mua xe chỉ có trong chế độ hành trình','Vào hành trình để sắm xe cho nhân vật của bạn.');
  const inner=S.view==='buy'?buyView(v):S.view==='edit'?editView(v):S.view==='plates'?platesView(v):(tabs(v)+(S.tab==='mine'?mineView(v):groupView(v,S.tab)));
  return head()+`<div class="sheet-body bk hs-body gr-body">${flash()}${inner}</div>`;
}
function tabs(v){
  const list=[['mine',`🔑 Nhà xe${v.cars.length?` · ${v.cars.length}`:''}`],...CAT().groups.map(g=>[g.id,`${g.emoji} ${g.name}`])];
  return `<div class="segmented bk-tabs gr-tabs" role="tablist" aria-label="Mục nhà xe">${list.map(([id,l])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" class="${S.tab===id?'active':''}" data-gr="tab" data-tab="${id}">${esc(l)}</button>`).join('')}</div>`;
}

/* fee: xu a tháng (game/upkeep.py: phí giữ xe & bảo dưỡng; undefined from an older server: no chip). */
function perkChips(it,fee=it.upkeep){
  return `<p class="hs-chips"><span>😊 +${it.spirit} tinh thần mỗi chuyến</span><span>${it.fuel?`⛽ ${xu(it.fuel)} mỗi chuyến`:'⛽ Không tốn xăng'}</span><span>🗓️ 1 chuyến/ngày</span>${fee>0?`<span>🧾 Giữ xe & bảo dưỡng ${xu(fee)}/tháng</span>`:''}</p>`;
}

/* 🔑 Your vehicles: ride out (once a day, any vehicle), choose which one you ride, paint, plate, sell. */
function mineView(v){
  const today=v.tripped?'<p class="bk-alert good">Hôm nay đã đi chơi một chuyến. Mai lại đi tiếp nhé.</p>':'';
  if(!v.cars.length){
    const first=CAT().vehicles.filter(x=>x.group==='bike').sort((a,b)=>a.price-b.price)[0];
    return `<section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🅿️</div><h3>Nhà xe còn trống</h3><p>Trả đủ một lần, không vay. Có xe rồi, mỗi ngày đi chơi một chuyến cho tinh thần phơi phới.</p>
      ${first?`<div class="bk-actions">${btn(`${first.emoji} Xem ${lname(first.name)} · ${xu(first.price)}`,'look',{id:first.id},'primary')}</div>`:''}</section>`;
  }
  const cards=v.cars.map(c=>{
    const it=item(c.id);if(!it)return '';
    const on=v.ride===c.id,g=group(it.group),uq=c.uq?.t||(on?uqPlate():''),fits=fitting(v,it);
    const perk=c.uq?.pct?`<p class="gr-perk${on?' on':''}">💰 Biển đẹp: lợi nhuận mỗi ca +${fmt(c.uq.pct)}%${on?'':' khi đi chiếc này'}</p>`:'';
    const plateBtn=fits.length?btn(c.uq?'🔨 Đổi biển':'🔨 Gắn biển','plates',{id:c.id},'ghost'):'';
    return `<li class="hs-home gr-car${on?' mine':''}${c.limited?' limited':''}" style="--hs-tone:${esc(g.color||'')}"><div class="hs-home-top">${uq?tileHTML(it,c.color,uq,'',true):tileHTML(it,c.color,c.plate)}<div class="grow"><b>${esc(it.name)}</b><small>${on?'🛞 Đang đi':c.limited?`🏎️ Bản giới hạn ${esc(it.serial||'')}`:`Mua ngày ${fmt(c.day)}`} · ${esc(paint(c.color).name)}</small></div></div>
      ${perk}${perkChips(it,c.upkeep)}
      ${Number.isInteger(c.broken)?`<div class="bk-actions">${btn(`🔧 Đang hỏng · Sửa ${xu(c.broken)}`,'fix',{id:c.id},'primary')}</div>`:''}
      <div class="bk-actions">${btn(`${esc(it.trip)}${it.fuel?` · ${xu(it.fuel)}`:''}`,'trip',{id:c.id},'primary',c.trip_why||'')}${on?'':btn('Đi chiếc này','ride',{id:c.id},'ghost')}${plateBtn}${btn(c.uq?'🎨 Sơn xe':'🎨 Sơn & biển tên','edit',{id:c.id},'ghost')}</div>
      ${c.trip_why&&!v.tripped?`<p class="bk-hint">${esc(c.trip_why)}</p>`:''}
      ${c.limited?'<p class="gr-sell"><small>Bản giới hạn của Nhà đấu giá · không bán lại</small></p>':`<p class="gr-sell"><small>Bán lại được ${xu(c.sell)}</small>${btn('Bán','sell',{id:c.id},'ghost small danger')}</p>`}</li>`;
  }).join('');
  const off=v.ride?`<div class="bk-actions">${btn('Không khoe xe trên hồ sơ','ride',{},'ghost small')}</div>`:'';
  const U=v.upkeep,day=J().life_day||0;
  const bill=U?.month?`<p class="bk-hint gr-bill">🧾 Phí giữ xe & bảo dưỡng khoảng ${xu(U.month)}/tháng, trừ cùng hóa đơn Ngày ${fmt(U.next)}${U.next===day?' (hôm nay)':` (còn ${fmt(U.next-day)} ngày)`}: tiền mặt trước, thiếu thì lấy từ tài khoản, không bao giờ làm ví âm.</p>`:'';
  return `${today}${bonusCard(v)}${raceCard(v)}<section class="bk-card"><h3>Xe của bạn</h3><p class="bk-hint">Chiếc “đang đi” hiện trên hồ sơ, trước nhà và trong Phố nghề.</p>${bill}<ul class="hs-market">${cards}</ul>${off}</section>${platesCard(v)}`;
}

/* 🏁 Độ xe & đua xe (game/racing.py, v4/race-track.js): a motorbike or a car (never a bicycle, a boat or a plane). */
const RACERS=['xe_so','xe_ga','o_to_mini','o_to_suv','mui_tran','sieu_xe'];
function raceCard(v){
  if(!(v.cars||[]).some(c=>{const it=item(c.id);return RACERS.includes(it?.base||c.id);}))return '';
  return `<section class="bk-card gr-race"><h3>🏁 Độ xe &amp; đua xe</h3><p class="bk-hint">Độ xe của bạn ở Xưởng Tư Pít-tông, chạy tính giờ ở Bến Mây, thách đấu tay đôi và giành danh hiệu tuần.</p>
    <div class="bk-actions">${btn('🔧 Độ xe','race',{tab:'tune'},'primary')}${btn('🏁 Ra đường đua','race',{tab:'trial'},'ghost')}</div></section>`;
}
/* 🔨 Biển đẹp: the bonus of the vehicle ridden now, the plates won and where each one is. */
function bonusCard(v){
  const b=v.bonus,it=b&&item(b.id);if(!b||!it)return '';
  const cap=CAT().plate_pct?.shift_cap;
  return `<p class="bk-alert good gr-bonus">💰 Đang đi ${esc(it.name)} gắn biển <b class="gr-gold" data-no-translate>${esc(b.t)}</b>: lợi nhuận mỗi ca +${fmt(b.pct)}%${cap?` (tối đa ${xu(cap)} một ca)`:''}.</p>`;
}
function platesCard(v){
  const list=v.plates||[];if(!list.length)return '';
  const rows=list.map(p=>{const c=p.on&&(v.cars||[]).find(x=>x.id===p.on),it=c&&item(c.id);
    return `<li class="gr-plate-row"><span class="gr-plate uq" data-no-translate>${esc(p.t)}</span><small>${esc(KIND_WORD[p.k]||'Biển')} · ${it?`trên ${esc(it.name)}`:'đang cất'}</small>${it?btn('Tháo','attach',{item:p.id},'ghost small'):''}</li>`;}).join('');
  return `<section class="bk-card gr-plates"><h3>🔨 Biển đẹp của bạn</h3><p class="bk-hint">${platesHint()}</p><ul class="gr-plate-list">${rows}</ul></section>`;
}
function platesHint(){
  const t=CAT().plate_pct;if(!t?.table)return 'Gắn biển lên xe đang đi để lời thêm mỗi ca.';
  const span=a=>`${Math.min(...a)}–${Math.max(...a)}%`;
  return `Gắn lên chiếc đang đi: lợi nhuận mỗi ca tăng. Xe máy ${span(t.table.bike)}, ô tô ${span(t.table.car)}, du thuyền ${span(t.table.boat)}, máy bay ${span(t.table.plane)}; bản giới hạn +${fmt(t.limited)}%, tối đa ${fmt(t.cap)}%. Chỉ tính một chiếc, khóa lúc mở ca.`;
}
/* Attach a plate to one vehicle: each plate that fits it, where it is now. */
function platesView(v){
  const c=(v.cars||[]).find(x=>x.id===S.pick?.id),it=c&&item(c.id);if(!it){S.view='list';return mineView(v);}
  const rows=fitting(v,it).map(p=>{const here=p.on===c.id,other=p.on&&!here&&item(p.on);
    return `<li class="gr-plate-row"><span class="gr-plate uq" data-no-translate>${esc(p.t)}</span><small>${here?'Đang gắn trên chiếc này':other?`Đang trên ${esc(other.name)}`:'Đang cất'}</small>${here?btn('Tháo','attach',{item:p.id},'ghost small'):btn('Gắn lên','attach',{item:p.id,id:c.id},'primary small')}</li>`;}).join('');
  return `<section class="bk-card"><h3>🔨 Gắn biển · ${esc(it.name)}</h3><div class="gr-preview">${tileHTML(it,c.color,c.uq?.t||c.plate,'big',Boolean(c.uq))}</div>
    <ul class="gr-plate-list">${rows||'<li class="bk-hint">Chưa có biển hợp với chiếc này.</li>'}</ul><p class="bk-hint">${platesHint()}</p>
    <div class="bk-actions">${btn('Quay lại','back',{},'ghost')}</div></section>`;
}

/* One tab of the shop: the listings of a group, cheapest first, "thiếu N xu" when the money is not there yet. */
function groupView(v,gid){
  const g=group(gid),why=new Map(v.market.map(m=>[m.id,m.why])),mine=new Set(v.cars.map(c=>c.id));
  const list=CAT().vehicles.filter(x=>x.group===gid&&!x.limited).sort((a,b)=>a.price-b.price);   // 🏎️ limited ones: the auction only
  const rows=list.map(it=>{
    const owned=mine.has(it.id),w=why.get(it.id);
    const status=owned?'<span class="hs-ok">✓ Đã có trong nhà xe</span>':w?`<span class="hs-miss">${esc(w)}</span>`:'<span class="hs-ok">✓ Đủ tiền mua</span>';
    return `<li class="hs-home${owned?' mine':''}" style="--hs-tone:${esc(g.color||'')}"><div class="hs-home-top">${tileHTML(it,it.paint)}<div class="grow"><b>${esc(it.name)}</b><small>${esc(g.where||'')}</small></div><strong class="hs-price">${xu(it.price)}</strong></div>
      <p>${esc(it.desc)}</p>${perkChips(it)}
      <div class="hs-go">${status}${owned?'':btn('Xem & chọn màu','look',{id:it.id},w?'ghost':'primary')}</div></li>`;
  }).join('');
  return `<section class="bk-card"><h3>${g.emoji||''} ${esc(g.where||g.name||'')}</h3><p class="bk-hint">Trả đủ một lần, không vay. Ví ${xu(v.have.wallet)}${v.have.bank?` · tài khoản ${xu(v.have.balance)}`:''}.</p><ul class="hs-market">${rows}</ul></section>`;
}

function swatches(){
  const lim=Boolean(item(S.pick?.id)?.limited);   // the special paints are the limited editions' own
  return `<div class="gr-swatches" role="radiogroup" aria-label="Màu sơn">${CAT().paints.filter(p=>!p.limited||lim).map(p=>`<button type="button" class="gr-swatch${S.pick?.color===p.id?' on':''}" role="radio" aria-checked="${S.pick?.color===p.id}" style="--gr-paint:${esc(p.hex)}" data-gr="paint" data-color="${esc(p.id)}" title="${esc(p.name)}"${S.busy?' disabled':''}><span class="sr-only">${esc(p.name)}</span></button>`).join('')}</div><p class="bk-hint">Màu: <b>${esc(paint(S.pick?.color).name)}</b>. Đổi màu sau này không tốn xu.</p>`;
}
function plateField(){
  const max=CAT().plate_max||10;
  return `<label class="bk-field"><span>Biển tên (không bắt buộc, tối đa ${max} ký tự)</span><input id="gr-plate" name="plate" maxlength="${max}" autocomplete="off" value="${esc(S.pick?.plate||'')}" placeholder="VD: MÂY 01" data-preserve></label>`;
}
function buyView(v){
  const it=item(S.pick?.id);if(!it){S.view='list';return mineView(v);}
  const w=v.market.find(m=>m.id===it.id)?.why;
  return `<section class="bk-card hs-buy"><div class="hs-home-top"><div class="grow"><small>${esc(group(it.group).where||'')}</small><h3>${esc(it.name)}</h3></div><strong class="hs-price">${xu(it.price)}</strong></div>
    <div class="gr-preview">${tileHTML(it,S.pick.color,(S.pick.plate||'').trim(),'big')}</div>
    <p>${esc(it.desc)}</p>${perkChips(it)}
    ${swatches()}${plateField()}
    <p class="bk-hint">${it.upkeep>0?`Phí giữ xe & bảo dưỡng khoảng ${xu(it.upkeep)}/tháng (5 ngày sống), trừ cùng hóa đơn cuối tháng, không bao giờ làm ví âm. Tiền xăng chỉ trả khi bạn đi chơi.`
      :it.upkeep===0?'Xe đạp không tốn phí giữ xe. Tiền xăng chỉ trả khi bạn đi chơi.':'Tiền xăng chỉ trả khi bạn đi chơi.'}</p>
    ${w?`<p class="bk-alert warn">${esc(w)}</p>`:''}
    <div class="bk-actions">${btn(`Mua · ${xu(it.price)}`,'buy',{},'primary big',w||'')}${btn('Quay lại','back',{},'ghost')}</div></section>`;
}
function editView(v){
  const c=v.cars.find(x=>x.id===S.pick?.id),it=c&&item(c.id);if(!it){S.view='list';return mineView(v);}
  const uq=c.uq?.t;   // 🔨 a gold plate on it: the free "biển tên" waits under it
  return `<section class="bk-card"><h3>🎨 Sơn &amp; biển tên · ${esc(it.name)}</h3>
    <div class="gr-preview">${uq?tileHTML(it,S.pick.color,uq,'big',true):tileHTML(it,S.pick.color,(S.pick.plate||'').trim(),'big')}</div>
    ${swatches()}${uq?'<p class="bk-hint">Đang gắn biển đấu giá. Tháo biển ra thì biển tên tự đặt hiện lại.</p>':''}${plateField()}
    <div class="bk-actions">${btn('Lưu lại','save',{},'primary')}${btn('Quay lại','back',{},'ghost')}</div></section>`;
}
