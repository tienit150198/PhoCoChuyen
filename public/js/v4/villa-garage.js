/** 🚘 Hầm để xe: your vehicles parked at home (owner 23/10 "biệt thự ok thêm hầm để xe"; F#271 hầm xe biệt thự sân vườn).
 * game/villa_garage.py says where you park (a villa's underground garage with 4–12 bays, a yard, an apartment block's
 * basement, the lot down the alley) and which vehicle stands in which bay (journey.homelife.hamxe, derived from
 * journey.garage: nothing to migrate). Tap a vehicle: its card, 🛣️ a ride out (jr_garage_trip), 🫧 a wash
 * (jr_hamxe_wash), ⭐ ride this one (jr_garage_ride), 🔧 paint & plates (v4/garage.js). "Xếp chỗ đỗ" picks the
 * vehicles that take the bays (jr_hamxe_park). Boats moor at the berth or the marina, planes at the helipad or the
 * airport. Styles: /css/bank.css + /css/house.css + /css/homelife.css. */
import {icon,escapeHTML as esc} from '../icons.js';
import {ensureCss} from './home-overview.js';

const S={dlg:null,env:null,sel:'',sort:null,busy:false,flash:null,listening:false};
const J=()=>S.env?.api?.state?.journey||{};
const HX=()=>J().homelife?.hamxe||null;
const GC=()=>S.env?.api?.content?.journey?.garage||{vehicles:[],paints:[],groups:[]};
const item=id=>GC().vehicles.find(v=>v.id===id);
const car=id=>(J().garage?.cars||[]).find(c=>c.id===id);
const paint=id=>GC().paints.find(p=>p.id===id)||{hex:'#c9c3b8',name:''};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const lname=s=>String(s||'').slice(0,1).toLowerCase()+String(s||'').slice(1);
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,op,data={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-vg="${op}"${attrs(data)}${S.busy?' disabled':''}${extra}>${label}</button>`;

/** The bays' labels: "B1-01" in a villa's hầm, "Ô 1" elsewhere. */
export const bayName=(style,i)=>style==='ham'?`B1-${String(i+1).padStart(2,'0')}`:`Ô ${i+1}`;

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium bk-sheet hs-sheet vg-sheet';d.setAttribute('aria-labelledby','vg-title');
  d.innerHTML='<div class="vg-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-vg]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.vg,el.dataset);
  });
  d.addEventListener('close',()=>{S.flash=null;S.sort=null;S.sel='';});
  S.dlg=d;return d;
}
export async function openVillaGarage(env){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';env.api.addEventListener('state',()=>{const key=JSON.stringify([HX(),J().garage,J().wallet]);if(key===seen)return;seen=key;if(S.dlg?.open&&!S.busy)render();});
  }
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();S.sel='';S.sort=null;S.flash=null;
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
}
export async function villaGarageAction(action,data,el,env){
  if(action!=='villaGarage')return false;
  await openVillaGarage(env);return true;
}

async function send(action,payload={}){
  if(S.busy)return null;S.busy=true;render();
  try{const r=await S.env.api.command(action,payload);S.flash={text:[r.message,...(r.effects||[])].filter(Boolean).join(' '),kind:'good'};return r;}
  catch(e){S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;render();}
}
async function onClick(op,data){
  switch(op){
    case'close':S.dlg.close();return;
    case'pick':S.sel=S.sel===data.id?'':data.id;S.flash=null;render();S.dlg.querySelector('.vg-card')?.scrollIntoView?.({block:'nearest',behavior:'smooth'});return;
    case'trip':send('jr_garage_trip',{id:data.id});return;
    case'wash':send('jr_hamxe_wash',{id:data.id});return;
    case'ride':send('jr_garage_ride',{id:data.id});return;
    case'shop':S.dlg.close();(await import('./garage.js')).openGarage(S.env,data.tab||'mine');return;
    case'overview':S.dlg.close();(await import('./home-overview.js')).openOverview(S.env);return;
    case'sort':S.sort=[...(HX()?.park||[])];S.sel='';S.flash=null;render();return;
    case'sortOff':S.sort=null;render();return;
    case'toggle':{if(!S.sort)return;const i=S.sort.indexOf(data.id);if(i>=0)S.sort.splice(i,1);else if(S.sort.length<(HX()?.slots||1))S.sort.push(data.id);
      else{S.flash={text:`Chỉ có ${HX()?.slots||1} chỗ đỗ. Bỏ bớt một xe trước nhé.`,kind:'warn'};}render();return;}
    case'save':{const r=await send('jr_hamxe_park',{ids:S.sort||[]});if(r){S.sort=null;render();}return;}
    case'auto':{const r=await send('jr_hamxe_park',{ids:[]});if(r){S.sort=null;render();}return;}
  }
}

/* ---- rendering ---- */
function render(){
  if(!S.dlg)return;
  const root=S.dlg.querySelector('.vg-root'),top=root.querySelector('.vg-body')?.scrollTop;
  root.innerHTML=page();
  const b=root.querySelector('.vg-body');if(b&&top)b.scrollTop=top;
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
function head(h){
  const ham=h?.style==='ham';
  return `<header class="sheet-head bk-head hs-head"><span class="hs-logo vg-logo" aria-hidden="true">${ham?'🚘':'🅿️'}</span>
    <div class="grow"><span class="eyebrow">${ham?'HẦM ĐỂ XE':'CHỖ ĐỂ XE'}</span><h2 id="vg-title">${esc(h?.name||'Chỗ để xe')}</h2><p>${h?`${h.park.length}/${h.slots} chỗ có xe`:''}</p></div>
    <button class="icon-btn" type="button" data-vg="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
}
const flash=()=>`<p class="bk-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
function tile(id,size=''){
  const it=item(id),c=car(id);if(!it)return '';
  const p=paint(c?.color||it.paint),washed=(HX()?.wash||[]).includes(id),ride=J().garage?.ride===id;
  return `<span class="vg-car ${size}${washed?' shine':''}${c?.broken!=null?' broken':''}" style="--gr-paint:${esc(p.hex)}"><span class="vg-emoji">${it.emoji}</span>${c?.plate||c?.uq?.t?`<span class="vg-plate${c?.uq?' uq':''}">${esc(c?.uq?.t||c.plate)}</span>`:''}${ride?'<span class="vg-star" title="Đang đi">⭐</span>':''}${washed?'<span class="vg-sparkle" aria-hidden="true">✨</span>':''}</span>`;
}
function page(){
  const j=J(),h=HX();
  if(!j.story||!h)return head(null)+`<div class="sheet-body bk vg-body"><section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🚘</div><h3>Chỉ có trong chế độ hành trình</h3></section></div>`;
  const all=(j.garage?.cars||[]).length;
  if(!all)return head(h)+`<div class="sheet-body bk vg-body">${flash()}${garageArt(h)}<section class="bk-card bk-center"><h3>Chưa có xe nào</h3><p>Mua một chiếc ở Cửa hàng xe, xe sẽ về đỗ ở đây.</p>${btn('🛵 Cửa hàng xe','shop',{tab:'bike'},'primary')}</section></div>`;
  return head(h)+`<div class="sheet-body bk vg-body">${flash()}${S.sort?sortView(h):garageArt(h)+card(h)+others(h)}
    <div class="bk-actions">${S.sort?'':btn('🔀 Xếp chỗ đỗ','sort',{},'cream')}${btn('🗺️ Tổng quan nhà','overview',{},'cream')}${btn('🔧 Nhà xe','shop',{tab:'mine'},'cream')}</div></div>`;
}
/** The garage drawn: the ramp, the lights, the bays two by two with their numbers and lines. */
function garageArt(h){
  const bays=Array.from({length:h.slots},(_,i)=>{const id=h.park[i],it=id&&item(id);
    return `<li class="vg-bay${it?' full':''}${S.sel&&S.sel===id?' on':''}">${it?`<button type="button" class="vg-bay-btn" data-vg="pick" data-id="${esc(id)}" aria-pressed="${S.sel===id}" aria-label="${esc(`${it.name}, ${bayName(h.style,i)}`)}">${tile(id)}<span class="vg-bay-no">${bayName(h.style,i)}</span></button>`
      :`<span class="vg-empty"><span class="vg-bay-no">${bayName(h.style,i)}</span>Trống</span>`}</li>`;}).join('');
  const washed=(h.wash||[]).length;
  return `<section class="vg-ham s-${esc(h.style)}" aria-label="${esc(h.name)}"><div class="vg-lights" aria-hidden="true"><i></i><i></i><i></i></div>
    <div class="vg-ramp" aria-hidden="true">${h.style==='ham'?'⬆ Lối lên sân':h.style==='chung'?'⬆ Lối lên sảnh':'⬆ Ra đường'}</div>
    <ul class="vg-bays">${bays}</ul>
    <p class="vg-note">${washed?`🫧 Hôm nay đã rửa ${washed} xe.`:`🫧 Rửa xe đầu tiên trong ngày: +${S.env?.api?.content?.journey?.homelife?.wash_spirit||1} tinh thần.`}</p></section>`;
}
function card(h){
  const id=S.sel,it=item(id),c=car(id);
  if(!it||!c)return `<p class="bk-hint vg-tap">Chạm một chiếc xe để xem, rửa hoặc đi một vòng.</p>`;
  const washed=(h.wash||[]).includes(id),ride=J().garage?.ride===id;
  const tripLabel=`🛣️ ${esc(it.trip||'Đi một vòng')}${it.fuel?` · ${fmt(it.fuel)} xu xăng`:''}`;
  return `<section class="bk-card vg-card"><div class="hs-home-top">${tile(id,'big')}<div class="grow"><small>${esc(paint(c.color).name||'')}${c.plate?` · biển “${esc(c.plate)}”`:''}</small><h3>${esc(it.name)}</h3>
    <p class="hs-chips"><span>📅 Mua ngày ${fmt(c.day)}</span>${c.upkeep?`<span>🧾 ${fmt(c.upkeep)} xu/tháng</span>`:''}${c.uq?`<span>🔨 +${c.uq.pct}% mỗi ca</span>`:''}${ride?'<span>⭐ Đang đi</span>':''}${washed?'<span>✨ Sạch bóng</span>':''}${c.broken!=null?'<span>🛠️ Đang hỏng</span>':''}</p></div></div>
    <p>${esc(it.desc||'')}</p>
    <div class="bk-actions">${btn(tripLabel,'trip',{id},'primary',c.trip_why?` disabled title="${esc(c.trip_why)}"`:'')}${btn(washed?'✨ Đã rửa hôm nay':'🫧 Rửa xe','wash',{id},'ghost',washed?' disabled':'')}${ride?'':btn('⭐ Đi chiếc này','ride',{id},'ghost')}</div>
    ${c.trip_why?`<p class="bk-hint">${esc(c.trip_why)}</p>`:''}</section>`;
}
function others(h){
  const row=(title,list)=>list.length?`<section class="bk-card vg-others"><h3>${title}</h3><ul class="vg-row">${list.map(([id,where])=>{const it=item(id);if(!it)return '';
    return `<li><button type="button" class="vg-mini${S.sel===id?' on':''}" data-vg="pick" data-id="${esc(id)}" aria-label="${esc(it.name)}">${tile(id,'small')}<span><b>${esc(it.name)}</b>${where?`<small>${esc(where)}</small>`:''}</span></button></li>`;}).join('')}</ul></section>`:'';
  const out=(h.out||[]).map(id=>[id,h.style==='ham'?'Đỗ ngoài sân':'Gửi bãi ngoài']);
  return row('🅿️ Ngoài chỗ đỗ',out)+row('⛵ Ở bến',h.water||[])+row('✈️ Ở sân bay',h.air||[]);
}
function sortView(h){
  const road=[...(h.park||[]),...(h.out||[])];
  const list=road.map(id=>{const it=item(id);if(!it)return '';const i=S.sort.indexOf(id);
    return `<li><button type="button" class="vg-mini${i>=0?' on':''}" data-vg="toggle" data-id="${esc(id)}" aria-pressed="${i>=0}">${tile(id,'small')}<span><b>${esc(it.name)}</b><small>${i>=0?`${bayName(h.style,i)}`:'Chưa xếp'}</small></span></button></li>`;}).join('');
  return `<section class="bk-card"><h3>🔀 Xếp chỗ đỗ</h3><p class="bk-hint">Chọn tối đa ${h.slots} xe theo thứ tự muốn đỗ. Xe còn lại đỗ ngoài. Chỉ xe máy và ô tô vào ${esc(lname(h.name))}.</p>
    <ul class="vg-row">${list}</ul><div class="bk-actions">${btn(`Lưu (${S.sort.length}/${h.slots})`,'save',{},'primary')}${btn('Để tự xếp','auto',{},'ghost')}${btn('Hủy','sortOff',{},'ghost')}</div></section>`;
}
