/** 🚗 Xe & phương tiện: bicycles, motorbikes, cars, yachts and private planes, bought outright (story mode).
 * Every rule and number lives in game/garage.py; this file renders api.state.journey.garage with the static list
 * (content.journey.garage) and sends `jr_garage_*` commands. Its own dialog (like Nhà của bạn), opened with
 * data-action="garage" from the menu, the profile's ride chip and the house card. The art is the emoji on a tile
 * in the vehicle's paint, with its plate under it. Styles: /css/bank.css + /css/house.css + /css/garage.css. */
import {icon,escapeHTML as esc} from '../icons.js';

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
export function tileHTML(v,color,plate='',size=''){
  const p=paint(color||v?.paint);
  return `<span class="gr-tile ${size}" style="--gr-paint:${esc(p.hex)}" aria-hidden="true"><span class="gr-emoji">${v?.emoji||'🚗'}</span>${plate?`<span class="gr-plate">${esc(plate)}</span>`:''}</span>`;
}

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
    case'sell':{const c=(v.cars||[]).find(x=>x.id===data.id),it=item(data.id);if(!c||!it)return;
      if(await ask(`Bán ${lname(it.name)}?`,`Mua ${xu(c.paid)}, bán lại được ${xu(c.sell)} (${CAT().sell_pct}% giá đã trả). Tiền vào ví. Bán rồi là không lấy lại được.`,`Bán · nhận ${xu(c.sell)}`))send('jr_garage_sell',{id:c.id,confirm:true});return;}
    case'house':S.dlg.close();(await import('./house.js')).openHouse(S.env);return;
  }
}

/* ---- rendering ---- */
function render(){
  if(!S.dlg)return;
  const body=S.dlg.querySelector('.gr-body'),top=body?.scrollTop;
  S.dlg.querySelector('.gr-root').innerHTML=page();
  if(top)S.dlg.querySelector('.gr-body').scrollTop=top;
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
  const inner=S.view==='buy'?buyView(v):S.view==='edit'?editView(v):(tabs(v)+(S.tab==='mine'?mineView(v):groupView(v,S.tab)));
  return head()+`<div class="sheet-body bk hs-body gr-body">${flash()}${inner}</div>`;
}
function tabs(v){
  const list=[['mine',`🔑 Nhà xe${v.cars.length?` · ${v.cars.length}`:''}`],...CAT().groups.map(g=>[g.id,`${g.emoji} ${g.name}`])];
  return `<div class="segmented bk-tabs gr-tabs" role="tablist" aria-label="Mục nhà xe">${list.map(([id,l])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" class="${S.tab===id?'active':''}" data-gr="tab" data-tab="${id}">${esc(l)}</button>`).join('')}</div>`;
}

function perkChips(it){
  return `<p class="hs-chips"><span>😊 +${it.spirit} tinh thần mỗi chuyến</span><span>${it.fuel?`⛽ ${xu(it.fuel)} mỗi chuyến`:'⛽ Không tốn xăng'}</span><span>🗓️ 1 chuyến/ngày</span></p>`;
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
    const on=v.ride===c.id,g=group(it.group);
    return `<li class="hs-home gr-car${on?' mine':''}" style="--hs-tone:${esc(g.color||'')}"><div class="hs-home-top">${tileHTML(it,c.color,c.plate)}<div class="grow"><b>${esc(it.name)}</b><small>${on?'🛞 Đang đi':`Mua ngày ${fmt(c.day)}`} · ${esc(paint(c.color).name)}</small></div></div>
      ${perkChips(it)}
      <div class="bk-actions">${btn(`${esc(it.trip)}${it.fuel?` · ${xu(it.fuel)}`:''}`,'trip',{id:c.id},'primary',c.trip_why||'')}${on?'':btn('Đi chiếc này','ride',{id:c.id},'ghost')}${btn('🎨 Sơn & biển tên','edit',{id:c.id},'ghost')}</div>
      ${c.trip_why&&!v.tripped?`<p class="bk-hint">${esc(c.trip_why)}</p>`:''}
      <p class="gr-sell"><small>Bán lại được ${xu(c.sell)}</small>${btn('Bán','sell',{id:c.id},'ghost small danger')}</p></li>`;
  }).join('');
  const off=v.ride?`<div class="bk-actions">${btn('Không khoe xe trên hồ sơ','ride',{},'ghost small')}</div>`:'';
  return `${today}<section class="bk-card"><h3>Xe của bạn</h3><p class="bk-hint">Chiếc “đang đi” hiện trên hồ sơ, trước nhà và trong Phố nghề.</p><ul class="hs-market">${cards}</ul>${off}</section>`;
}

/* One tab of the shop: the listings of a group, cheapest first, "thiếu N xu" when the money is not there yet. */
function groupView(v,gid){
  const g=group(gid),why=new Map(v.market.map(m=>[m.id,m.why])),mine=new Set(v.cars.map(c=>c.id));
  const list=CAT().vehicles.filter(x=>x.group===gid).sort((a,b)=>a.price-b.price);
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
  return `<div class="gr-swatches" role="radiogroup" aria-label="Màu sơn">${CAT().paints.map(p=>`<button type="button" class="gr-swatch${S.pick?.color===p.id?' on':''}" role="radio" aria-checked="${S.pick?.color===p.id}" style="--gr-paint:${esc(p.hex)}" data-gr="paint" data-color="${esc(p.id)}" title="${esc(p.name)}"${S.busy?' disabled':''}><span class="sr-only">${esc(p.name)}</span></button>`).join('')}</div><p class="bk-hint">Màu: <b>${esc(paint(S.pick?.color).name)}</b>. Đổi màu sau này không tốn xu.</p>`;
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
    <p class="bk-hint">Không có phí giữ xe hay bảo dưỡng tự trừ. Tiền xăng chỉ trả khi bạn đi chơi.</p>
    ${w?`<p class="bk-alert warn">${esc(w)}</p>`:''}
    <div class="bk-actions">${btn(`Mua · ${xu(it.price)}`,'buy',{},'primary big',w||'')}${btn('Quay lại','back',{},'ghost')}</div></section>`;
}
function editView(v){
  const c=v.cars.find(x=>x.id===S.pick?.id),it=c&&item(c.id);if(!it){S.view='list';return mineView(v);}
  return `<section class="bk-card"><h3>🎨 Sơn &amp; biển tên · ${esc(it.name)}</h3>
    <div class="gr-preview">${tileHTML(it,S.pick.color,(S.pick.plate||'').trim(),'big')}</div>
    ${swatches()}${plateField()}
    <div class="bk-actions">${btn('Lưu lại','save',{},'primary')}${btn('Quay lại','back',{},'ghost')}</div></section>`;
}
