/** ✈️ Du lịch trải nghiệm (game/travel.py → state.journey.travel, content.journey.travel). Feedback #464: pick a place,
 * book a flight (booking early is cheaper), the airport, the cabin crew, landing, a few spots to visit with a small
 * scene each (a photo, a dish, a light game, a rest), postcards and souvenirs, the flight home, a summary.
 * Its own dialog, opened with data-action="travel" (data-to: a place to show first): the menu, the town's ✈️ Đại lý vé
 * door, 🛍️ Mua sắm's visa tab. Every rule and price is the server's (`jr_trip_*`); the airport steps, the crew's small
 * talk and the spot scenes are drawn here only (a scene's stars are for fun, the server gives the same either way).
 * Phone first (390px): one main button in the bottom bar. Styles: /css/spend.css (sd-*) + /css/travel.css (tv-*). */
import {icon,escapeHTML as esc} from '../icons.js';
import {paint as sheetPaint} from './sheet-paint.js';
import {keep as keepFocus,home as focusHome,say} from './sheet-focus.js';

export const ACTIONS=new Set(['travel']);
const S={dlg:null,env:null,tab:'go',pick:'',ahead:-1,cls:'eco',food:'',drink:'',souv:'',airport:-1,mini:null,card:null,
  stampFx:'',summary:null,crew:null,cancelArm:false,busy:false,flash:null,said:null,listening:false};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const J=()=>S.env?.api?.state?.journey||{};
const T=()=>J().travel||null;
const K=()=>S.env?.api?.content?.journey?.travel||null;
const day=()=>Number(J().life_day)||1;
const dest=id=>K()?.dests.find(d=>d.id===id)||null;
const cash=()=>Number(J().wallet)||0;
const ready=()=>cash()<0?0:cash()+(Number(J().bank?.balance)||0);
const readyWhy=price=>cash()<0?'Ví đang nợ, trả nợ trước nhé':ready()>=price?'':`Còn thiếu ${fmt(price-ready())} xu`;
const dayName=a=>a===0?'Hôm nay':a===1?'Ngày mai':`Ngày ${day()+a}`;
const mins=m=>m>=60?`${Math.floor(m/60)} giờ${m%60?` ${m%60} phút`:''}`:`${m} phút`;
const theme=d=>d?` style="--tv-sky:${esc(d.sky)};--tv-land:${esc(d.land)};--tv-accent:${esc(d.accent)}"`:'';
const skyline=d=>`<span class="tv-skyline" aria-hidden="true">${[...(d?.skyline||'🏙️🏢🌳🏙️')].filter(c=>c.trim()).join('')}</span>`;

let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=Promise.all([link('/css/spend.css','sd-css'),link('/css/travel.css','tv-css')]);

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium sd-sheet tv-sheet';d.setAttribute('aria-labelledby','tv-title');
  d.innerHTML='<div class="sd-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-tv]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();
    if(el.getAttribute('aria-disabled')==='true'){if(!S.busy)say(d,main()[2]||'');return;}   // ♿ #519: focusable with its reason, read out on a tap
    onClick(el.dataset.tv,el.dataset);
  });
  d.addEventListener('close',()=>{stopMini();S.flash=null;S.airport=-1;S.card=null;S.crew=null;S.cancelArm=false;});
  S.dlg=d;return d;
}
export async function openTravel(env,data={}){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';env.api.addEventListener?.('state',()=>{const key=JSON.stringify([J().wallet,J().travel,J().life_day,J().bank?.balance]);if(key===seen)return;seen=key;if(S.dlg?.open&&!S.busy&&!S.mini)render();});
  }
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet?.();
  await ensureCss();
  const d=dialog();
  S.tab=data.tab==='book'?'book':'go';
  if(data.to&&dest(data.to)){S.pick=data.to;S.ahead=-1;}
  S.flash=null;S.summary=null;
  const fresh=!d.open;
  if(fresh){d.showModal();d.scrollTop=0;}
  render();
  if(fresh||data.to)focusHome(d.querySelector('.sd-root'));   // ♿ the screen reader starts on the screen's heading
}
export async function travelAction(action,data,el,env){
  if(!ACTIONS.has(action))return false;
  await openTravel(env,data||{});return true;
}
/** Back to the top of the sheet (the dialog scrolls, and the body on some layouts). */
function top(){if(!S.dlg)return;S.dlg.scrollTop=0;S.dlg.querySelector('.sd-body')?.scrollTo?.(0,0);}
async function send(action,payload={}){
  const {api}=S.env;S.busy=true;render();
  try{
    const r=await api.command(action,payload);
    S.flash={text:[r.message,...(r.effects||[]).filter(Boolean).map(x=>`💬 ${x}`)].filter(Boolean).join(' '),kind:'good'};
    return r;
  }catch(e){S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;render();}
}

/* ---- prices (content.journey.travel.dests[].fares: the server's, per class, by days ahead) ---- */
const fareOf=(d,cls,a)=>Number(d?.fares?.[cls]?.[a])||0;
const cheapest=d=>Math.min(...d.fares.eco);
/** The day picked for a place: the first good-price day unless the player chose one. */
const aheadOf=()=>S.ahead>=0?S.ahead:K().good_ahead;
const visaOk=(d,a)=>!d.visa||Number(T()?.visa?.[d.id]||0)>=day()+a;

/** The bottom bar's one button: [label, op, why (dimmed with this reason), note (a line above it)]. */
function main(){
  const t=T(),k=K();
  if(S.tab==='book')return ['','',''];
  if(S.summary)return ['Xong','closeSummary',''];
  if(t?.trip){const tr=t.trip,d=dest(tr.to);
    if(S.mini||S.card)return ['','',''];
    if(tr.ph==='fly')return ['🛬 Hạ cánh','land',''];
    if(tr.ph==='back')return ['🏠 Hạ cánh về nhà','land',''];
    return [`🛫 Ra sân bay về nhà`,'home',''];}
  if(t?.book){const b=t.book;
    if(S.airport>=0)return S.airport<2?['','','']:['🛫 Lên máy bay','board',''];
    return b.left>0?[`Bay ${dayName(b.left)}`,'airport',`Còn ${b.left} ngày nữa. Khép một ca làm để sang ngày mới.`]:['🧳 Ra sân bay','airport',''];}
  const d=dest(S.pick);if(!d||!k)return ['','',''];
  const a=aheadOf(),p=fareOf(d,S.cls,a);
  if(!visaOk(d,a)){
    const held=Number(T()?.visa?.[d.id]||0);
    // ♿ #519: no visa yet, the main button goes to the visa office (it was a dimmed "Đặt vé" with a small link above)
    if(held<day())return ['🛂 Làm visa','visa','',`Cần visa ${d.visa_name} còn hạn tới ${dayName(a).toLowerCase()}`];
    return [`Đặt vé · ${fmt(p)} xu`,'book',`Visa ${d.visa_name} hết hạn ngày ${held}. Chọn ngày bay sớm hơn`];}
  return [`Đặt vé · ${fmt(p)} xu`,'book',readyWhy(p)];
}

async function onClick(op,data){
  const t=T();
  switch(op){
    case'close':S.dlg.close();return;
    case'tab':S.tab=data.tab;S.flash=null;render();top();return;
    case'pick':S.pick=data.id;S.ahead=-1;S.flash=null;render();top();return;
    case'unpick':S.pick='';S.flash=null;render();top();return;
    case'ahead':S.ahead=Number(data.n);render();return;
    case'cls':S.cls=data.id;render();return;
    case'visa':{const d=dest(data.id||S.pick);S.dlg.close();const m=await import('./lux.js');if(m.openLuxVisa)await m.openLuxVisa(S.env,d?.visa);else await m.luxAction('luxTrip',{},null,S.env);return;}
    case'food':S.food=data.id;render();return;
    case'drink':S.drink=data.id;render();return;
    case'meal':if(S.food&&S.drink)await send('jr_trip_meal',{food:S.food,drink:S.drink});return;
    case'crew':{const c=K().crew.find(x=>x.id===data.id),d=dest(t?.trip?.to);if(!c)return;
      const left=Math.max(5,Math.round((d?.fly||60)*0.4));
      S.crew={ask:c.ask,say:c.say.replace('{m}',String(left))};render();return;}
    case'cancel':if(!S.cancelArm){S.cancelArm=true;render();return;}
      S.cancelArm=false;await send('jr_trip_cancel',{confirm:true});return;
    case'step':S.airport=Math.min(2,S.airport+1);render();return;
    case'skipAirport':S.airport=2;await go('board');return;
    case'spot':startMini(data.id);return;
    case'miniTap':miniTap();return;
    case'miniSkip':await finishMini(0);return;
    case'miniClose':stopMini();render();return;
    case'cardClose':S.card=null;render();return;
    case'souv':S.souv=S.souv===data.id?'':data.id;render();return;
    case'buy':if(S.souv)await send('jr_trip_buy',{id:S.souv});return;
    case'go':await go(main()[1]);return;
  }
}
async function go(what){
  if(what==='visa'){await onClick('visa',{id:S.pick});return;}
  if(what==='closeSummary'){S.summary=null;S.pick='';render();return;}
  if(what==='land'){const r=await send('jr_trip_land',{});
    if(r?.travel?.stamp){S.stampFx=r.travel.stamp;render();setTimeout(()=>{S.stampFx='';if(S.dlg?.open)render();},1600);}
    if(r?.travel?.summary){S.summary=r.travel.summary;render();}
    if(r)top();
    return;}
  if(what==='home'){S.food=S.drink='';S.crew=null;const r=await send('jr_trip_home',{});if(r)top();return;}
  if(what==='airport'){S.airport=0;S.flash=null;render();top();return;}
  if(what==='board'){S.food=S.drink='';S.crew=null;const r=await send('jr_trip_board',{});if(r)S.airport=-1;render();if(r)top();return;}
  if(what==='book'){const d=dest(S.pick);if(!d)return;const r=await send('jr_trip_book',{to:d.id,cls:S.cls,day:day()+aheadOf(),confirm:true});if(r){S.pick='';S.ahead=-1;render();top();}return;}
}

/* ---- the spot scenes (drawn here only) ---- */
let raf=0;
function stopMini(){if(raf)cancelAnimationFrame(raf);raf=0;S.mini=null;}
function startMini(id){
  const tr=T()?.trip,d=dest(tr?.to),sp=d?.spots.find(x=>x.id===id);if(!sp||tr.seen.includes(id))return;
  const why=sp.fee?readyWhy(sp.fee):'';if(why){S.flash={text:why,kind:'bad'};render();return;}
  stopMini();S.mini={id,kind:sp.kind,step:0,pos:0,dir:1,stars:0,t0:performance.now()};render();
  if(sp.kind==='photo'||sp.kind==='play')loop();
  if(sp.kind==='rest')setTimeout(()=>{if(S.mini?.id===id&&S.mini.kind==='rest'){S.mini.step=1;render();}},2400);
}
function loop(){
  const m=S.mini;if(!m)return;
  const el=S.dlg?.querySelector('.tv-mover');
  const t=(performance.now()-m.t0)/1000,speed=m.kind==='photo'?0.55:0.8;
  m.pos=(Math.sin(t*Math.PI*speed)+1)/2;   // 0..1, back and forth
  if(el)el.style.left=`${(m.pos*100).toFixed(1)}%`;
  raf=requestAnimationFrame(loop);
}
function miniTap(){
  const m=S.mini;if(!m)return;
  if(m.kind==='food'){m.step++;if(m.step>=3)finishMini(3);else render();return;}
  if(m.kind==='rest'){finishMini(3);return;}
  const off=Math.abs(m.pos-0.5);   // the frame / the target sits in the middle
  finishMini(off<0.08?3:off<0.2?2:1);
}
async function finishMini(stars){
  const m=S.mini;if(!m)return;const id=m.id;stopMini();
  const r=await send('jr_trip_spot',{id});
  if(r)S.card={id,stars,new:!!r.travel?.new};
  render();if(r)top();
}

/* ---- rendering ---- */
function render(){
  if(!S.dlg)return;
  const pos=S.mini?S.mini.pos:0,root=S.dlg.querySelector('.sd-root');
  keepFocus(S.dlg,root,()=>sheetPaint(root,page(),'.sd-body'));   // ♿ #519: the tapped button (or the new screen's heading) keeps the reader's place
  if(S.flash!==S.said){S.said=S.flash;if(S.flash?.text)say(S.dlg,S.flash.text);}
  const el=S.dlg.querySelector('.tv-mover');if(el)el.style.left=`${(pos*100).toFixed(1)}%`;
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
const chip=(op,id,label,on,extra='')=>`<button type="button" class="sd-chip${on?' on':''}" data-tv="${op}" data-id="${esc(id)}" aria-pressed="${on}"${extra}>${label}</button>`;

export function page(){
  const t=T(),k=K(),tr=t?.trip,d=dest(tr?.to||t?.book?.to||S.pick);
  const title=S.tab==='book'?'Sổ du lịch':tr?(tr.ph==='here'?d?.name||'Du lịch':'Trên máy bay'):t?.book&&S.airport>=0?k?.home||'Sân bay':'Du lịch';
  const head=`<header class="sheet-head sd-head"><span class="sd-logo" aria-hidden="true">${S.tab==='book'?'📕':tr?.ph==='here'?esc(d?.flag||'✈️'):'✈️'}</span><div class="grow"><h2 id="tv-title">${esc(title)}</h2></div>
    <span class="sd-wallet" title="Ví">👛 ${fmt(Math.max(0,cash()))}</span><button class="icon-btn" type="button" data-tv="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  if(!k||!J().story)return head+`<div class="sheet-body sd-body"><p class="sd-empty">${J().story===false?'Chỉ có trong hành trình.':'⏳'}</p></div>`;
  const busyTrip=tr?' tv-dot':t?.book&&t.book.left<=0?' tv-dot':'';
  const tabs=`<nav class="sd-tabs tv-tabs" role="tablist" aria-label="Du lịch">${[['go','✈️','Chuyến đi',busyTrip],['book','📕','Sổ du lịch','']].map(([id,e,l,x])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" class="${S.tab===id?'on':''}${x}" data-tv="tab" data-tab="${id}"><span aria-hidden="true">${e}</span> <small>${l}</small></button>`).join('')}</nav>`;
  const inner=S.tab==='book'?bookView(t,k):S.summary?summaryView(S.summary):tr?(tr.ph==='here'?hereView(tr,d):cabinView(tr,d)):t?.book?ticketView(t.book,dest(t.book.to)):S.pick&&d?detailView(d):listView(t,k);
  const [label,,why,note]=main(),line=why||note||'';
  // ♿ #519: a button that cannot go yet stays focusable (aria-disabled) and names its reason (aria-describedby)
  const off=S.busy||why?' aria-disabled="true"':'';   // busy too: a disabled button would drop the reader's focus
  const bar=label?`<footer class="sd-bar">${line?`<small class="sd-why" id="tv-why">${esc(line)}</small>`:''}<button type="button" class="btn primary big sd-main" data-tv="go"${off}${line?' aria-describedby="tv-why"':''}>${esc(label)}</button></footer>`:'';
  const flash=`<p class="sd-flash ${S.flash?.kind||''}">${S.flash?esc(S.flash.text):''}</p>`;   // read out by the dialog's own live region (sheet-focus.js say)
  const fx=S.stampFx?stampFx(dest(S.stampFx)):'';
  return head+tabs+`<div class="sheet-body sd-body">${flash}${inner}</div>`+bar+fx;
}

/* 🗺️ the places */
function listView(t,k){
  const card=d=>{const n=(t?.stamps||{})[d.id]||0;
    return `<button type="button" class="tv-place" data-tv="pick" data-id="${esc(d.id)}"${theme(d)} aria-label="${esc(`${d.name}, từ ${fmt(cheapest(d))} xu${d.visa?', cần visa':''}${n?`, đã đến ${n} lần`:''}`)}">
      <span class="tv-place-art" aria-hidden="true">${skyline(d)}</span>
      <b>${esc(d.flag)} ${esc(d.name)}</b><small>${esc(d.area)}</small>
      <em>từ ${fmt(cheapest(d))} xu</em>${n?`<i class="tv-been" title="Đã đến ${n} lần">✓${n>1?n:''}</i>`:''}${d.visa?'<i class="tv-visa" title="Cần visa">🛂</i>':''}</button>`;};
  const vn=k.dests.filter(d=>d.kind==='vn'),intl=k.dests.filter(d=>d.kind!=='vn');
  const tip=`<p class="tv-tip">🎫 Đặt trước ${k.good_ahead} ngày là giá tốt nhất. Bay ngay trong ngày thì vé gấp đôi.</p>`;
  return `${tip}<h3 class="tv-h">🇻🇳 Trong nước</h3><div class="tv-places">${vn.map(card).join('')}</div>
    <h3 class="tv-h">🌏 Nước ngoài</h3><div class="tv-places">${intl.map(card).join('')}</div>`;
}
function hero(d,sub=''){
  return `<section class="tv-hero"${theme(d)}><div class="tv-hero-sky" aria-hidden="true"><i class="tv-sun"></i><i class="tv-cloud c1">☁️</i><i class="tv-cloud c2">☁️</i></div>
    ${skyline(d)}<div class="tv-hero-txt"><h3 data-focus-here tabindex="-1">${esc(d.flag)} ${esc(d.name)}</h3><p>${esc(sub||d.tag)}</p></div></section>`;
}
function detailView(d){
  const k=K(),a=aheadOf();
  const days=Array.from({length:k.max_ahead+1},(_,i)=>{const p=fareOf(d,S.cls,i),good=i>=k.good_ahead;
    return `<button type="button" class="tv-day${i===a?' on':''}${good?' good':''}${visaOk(d,i)?'':' novisa'}" data-tv="ahead" data-n="${i}" aria-pressed="${i===a}" aria-label="${esc(`${dayName(i)}, ${fmt(p)} xu${good?', giá tốt':i===0?', vé gấp':''}${visaOk(d,i)?'':', visa chưa tới ngày này'}`)}"><small>${esc(dayName(i))}</small><b>${fmt(p)}</b>${good?'<i>Giá tốt</i>':i===0?'<i>Gấp</i>':''}</button>`;}).join('');
  const cls=k.classes.map(c=>`<button type="button" class="sd-item${c.id===S.cls?' on':''}" data-tv="cls" data-id="${esc(c.id)}" aria-pressed="${c.id===S.cls}"><span class="sd-ico" aria-hidden="true">${c.emoji}</span><b>${esc(c.name)}</b><span class="sd-fx">${c.id==='biz'?'<i>Ghế nằm · món ngon</i>':'<i>Bữa ăn kèm</i>'}</span><em>${fmt(fareOf(d,c.id,a))}</em></button>`).join('');
  const spots=d.spots.map(s=>`<span title="${esc(s.name)}" role="img" aria-label="${esc(s.name)}">${s.emoji}</span>`).join('');
  const visa=d.visa?(visaOk(d,a)?`<p class="tv-ok">🛂 Visa ${esc(d.visa_name)} còn hạn tới ngày bay.</p>`:`<p class="tv-warn">🛂 Cần visa ${esc(d.visa_name)} còn hạn tới ngày bay. <button type="button" class="sd-link tv-inline" data-tv="visa" data-id="${esc(d.id)}" aria-label="${esc(`Làm visa ${d.visa_name}`)}">Làm visa</button></p>`):`<p class="tv-ok">${d.kind==='vn'?'🪪 Bay nội địa, chỉ cần căn cước.':'🛂 Miễn visa, cầm hộ chiếu là đi.'}</p>`;
  return `<button type="button" class="sd-link tv-back" data-tv="unpick">← Chọn nơi khác</button>${hero(d)}
    <section class="sd-card"><p class="tv-meta">🛫 ${esc(K().home)} → ${esc(d.airport)} · ${mins(d.fly)}</p><p class="tv-spots"><span class="sr-only">Điểm tham quan: </span>${spots}</p>${visa}</section>
    <section class="sd-card"><h4>📅 Ngày bay <small class="tv-muted">(vé khứ hồi)</small></h4><div class="tv-days">${days}</div></section>
    <section class="sd-card"><h4>💺 Hạng vé</h4><div class="sd-list">${cls}</div>
    <p class="tv-muted tv-small">Hủy trước ngày bay hoàn ${k.refund_early}%, trong ngày bay hoàn ${k.refund_late}%. Lỡ chuyến: hãng tự hoàn ${k.refund_late}%.</p></section>`;
}

/* 🎫 the ticket and the airport */
function pass(b,d){
  const k=K(),c=k.classes.find(x=>x.id===b.cls);
  return `<article class="tv-pass"${theme(d)}><header><b>✈️ ${esc(k.airline)}</b><span>${esc(c?.emoji||'')} ${esc(c?.name||'')}</span></header>
    <div class="tv-route"><div><small>Từ</small><b>${esc(k.home.replace('Sân bay ',''))}</b></div><span aria-hidden="true">✈</span><div><small>Đến</small><b>${esc(d.flag)} ${esc(d.name)}</b></div></div>
    <dl><div><dt>Chuyến</dt><dd>${esc(b.code)}</dd></div><div><dt>Ngày</dt><dd>${esc(String(b.day))}</dd></div><div><dt>Ghế</dt><dd>${esc(b.seat)}</dd></div><div><dt>Cửa</dt><dd>${esc(String(b.gate))}</dd></div></dl>
    <footer aria-hidden="true">${'▍▌▏▎▍▋▏▌▍▏▋▌▎▍▏▌▋▍▎▌▏▍▋▌'}</footer></article>`;
}
function ticketView(b,d){
  if(!d)return '';
  if(S.airport>=0)return airportView(b,d);
  const left=b.left>0?`<p class="tv-tip">⏳ Còn <b>${b.left}</b> ngày nữa bay. Mỗi lần khép ca và sang ngày sống mới là bớt một ngày.</p>`:'<p class="tv-tip good">🧳 Hôm nay bay! Ra sân bay làm thủ tục thôi.</p>';
  const cancel=`<button type="button" class="sd-link" data-tv="cancel">${S.cancelArm?`Chắc chưa? Hủy vé, nhận lại ${fmt(b.back)} xu`:`Hủy vé · hoàn ${fmt(b.back)} xu`}</button>`;
  return `${pass(b,d)}${left}${cancel}`;
}
const STEPS=[['🧳','Làm thủ tục','Gửi vali, nhận thẻ lên máy bay.'],['🛂','Qua an ninh','Bỏ điện thoại, chìa khóa vào khay.'],['🚪','Ra cửa','Loa gọi chuyến bay của bạn.']];
function airportView(b,d){
  const i=S.airport;
  const row=STEPS.map(([e,n],j)=>`<li class="${j<i?'done':j===i?'on':''}"><span aria-hidden="true">${j<i?'✓':e}</span>${esc(n)}</li>`).join('');
  const [e,n,line]=STEPS[i];
  const say=i===2?`📢 Mời hành khách chuyến ${esc(b.code)} đi ${esc(d.name)} ra cửa số ${esc(String(b.gate))}.`:esc(line);
  return `<section class="tv-airport"${theme(d)}><ol class="tv-steps">${row}</ol>
    <div class="tv-desk"><span class="tv-big tv-bob" aria-hidden="true">${e}</span><h3 data-focus-here tabindex="-1">${esc(n)}</h3><p>${say}</p>
    ${i<2?`<button type="button" class="btn primary" data-tv="step">${esc(n)} ${icon('arrow',14)}</button>`:''}</div>
    ${i>=1?pass(b,d):''}<button type="button" class="sd-link" data-tv="skipAirport">Bỏ qua, lên máy bay luôn</button></section>`;
}

/* 🛫 the cabin */
function cabinView(tr,d){
  const k=K(),back=tr.ph==='back',biz=tr.cls==='biz';
  const menu=kind=>k.meals[kind].filter(m=>biz||m.cls==='eco').map(m=>chip(kind,m.id,`${m.emoji} <small>${esc(m.name)}</small>`,(kind==='food'?S.food:S.drink)===m.id)).join('');
  const meal=tr.meal?`<p class="tv-ok">✅ Đã dùng bữa. Ngả ghế nghỉ một chút nhé.</p>`:
    `<p class="tv-bubble">💁 ${biz?'Chào mừng anh chị lên khoang thương gia! Hôm nay mình dùng gì ạ?':'Xin chào! Mình dùng cơm hay mì ạ? Đồ uống mình chọn luôn nha.'}</p>
    <h4>🍽️ Món</h4><div class="sd-chips tv-menu">${menu('food')}</div><h4>🥤 Uống</h4><div class="sd-chips tv-menu">${menu('drink')}</div>
    <button type="button" class="btn primary" data-tv="meal"${S.food&&S.drink&&!S.busy?'':' disabled'}>Gọi món</button>`;
  const crew=`<div class="sd-chips tv-crew">${k.crew.map(c=>chip('crew',c.id,esc(c.ask),false)).join('')}</div>${S.crew?`<p class="tv-bubble">💁 ${esc(S.crew.say)}</p>`:''}`;
  const from=back?d.name:k.home.replace('Sân bay ',''),to=back?'Nhà':d.name;
  return `<section class="tv-cabin${biz?' biz':''}"${theme(back?null:d)}>
      <div class="tv-window" aria-hidden="true"><i class="tv-cloud c1">☁️</i><i class="tv-cloud c2">☁️</i><i class="tv-cloud c3">☁️</i><span class="tv-wing"></span></div>
      <div class="tv-track" role="img" aria-label="${esc(`${from} → ${to}`)}"><small>${esc(from)}</small><span><i class="tv-plane">✈️</i></span><small>${esc(to)}</small></div>
      <p class="tv-meta">${esc(tr.code)} · ghế ${esc(tr.seat)} · ${mins(d.fly)}</p></section>
    <section class="sd-card">${meal}</section>
    <section class="sd-card"><h4>🛎️ Gọi tiếp viên</h4>${crew}</section>
    <p class="tv-muted tv-small">📢 ${esc(back?k.captain.down:k.captain.up)}</p>`;
}

/* 🗺️ at the place */
function hereView(tr,d){
  const k=K(),t=T(),seen=new Set(tr.seen),cards=new Set(t.cards||[]);
  if(S.mini)return miniView(tr,d);
  if(S.card)return cardView(d,S.card);
  const spots=d.spots.map(s=>{const done=seen.has(s.id),kd=k.kinds[s.kind]||{};
    return `<li class="tv-spot${done?' done':''}"><span class="tv-spot-ico" aria-hidden="true">${s.emoji}</span><div><b>${esc(s.name)}</b><small>${kd.emoji||''} ${esc(kd.verb||'')}${s.fee?` · ${fmt(s.fee)} xu`:' · miễn phí'}${cards.has(s.id)?' · 💌':''}</small></div>
      ${done?'<span class="tv-check" role="img" aria-label="Đã ghé">✓</span>':`<button type="button" class="btn small primary" data-tv="spot" data-id="${esc(s.id)}" aria-label="${esc(`Đi ${s.name}`)}"${S.busy?' disabled':''}>Đi</button>`}</li>`;}).join('');
  const g=S.souv&&d.souv.find(x=>x.id===S.souv);
  const shop=d.souv.map(x=>`<button type="button" class="sd-item${x.id===S.souv?' on':''}" data-tv="souv" data-id="${esc(x.id)}" aria-pressed="${x.id===S.souv}"><span class="sd-ico" aria-hidden="true">${x.emoji}</span><b>${esc(x.name)}</b><span class="sd-fx">${(t.souv||{})[x.id]?`<i>×${t.souv[x.id]}</i>`:''}</span><em>${fmt(x.price)}</em></button>`).join('');
  const buy=g?`<button type="button" class="btn tv-buy" data-tv="buy"${readyWhy(g.price)||S.busy?' disabled':''}>🎁 Mua ${esc(g.name)} · ${fmt(g.price)} xu</button>`:'';
  return `${hero(d,d.greet)}<p class="tv-stats"><span>📍 ${seen.size}/${d.spots.length} điểm</span><span>😊 +${tr.sp}</span><span>💸 ${fmt(tr.xu)} xu</span></p>
    <section class="sd-card"><h4>🗺️ Lịch trình</h4><ol class="tv-spots-list">${spots}</ol></section>
    <section class="sd-card"><h4>🎁 Quà lưu niệm</h4><div class="sd-list">${shop}</div>${buy}</section>`;
}
function miniView(tr,d){
  const m=S.mini,sp=d.spots.find(x=>x.id===m.id),k=K();
  let body='';
  if(m.kind==='photo')body=`<p class="tv-muted">Bấm chụp khi ${esc(sp.name)} vào giữa khung.</p><div class="tv-finder"${theme(d)}><span class="tv-frame" aria-hidden="true"></span><span class="tv-mover tv-big" aria-hidden="true">${sp.emoji}</span></div>
    <button type="button" class="btn primary big" data-tv="miniTap">📸 Chụp</button>`;
  else if(m.kind==='play')body=`<p class="tv-muted">Bấm khi ${sp.emoji} chạy vào ô 🎯 giữa đường.</p><div class="tv-bar-game"${theme(d)}><span class="tv-target" aria-hidden="true">🎯</span><span class="tv-mover tv-big" aria-hidden="true">${sp.emoji}</span></div>
    <button type="button" class="btn primary big" data-tv="miniTap">👆 Bấm!</button>`;
  else if(m.kind==='food')body=`<div class="tv-dish"><span class="tv-big" style="transform:scale(${(1-m.step*0.25).toFixed(2)})" aria-hidden="true">${sp.emoji}</span><p>${['Thơm quá!','Ngon ghê!','Miếng cuối nè!'][m.step]||''}</p></div>
    <button type="button" class="btn primary big" data-tv="miniTap">😋 Ăn một miếng (${m.step}/3)</button>`;
  else body=`<div class="tv-breathe"${theme(d)}><span class="tv-big" aria-hidden="true">${sp.emoji}</span><p>${m.step?'Nhẹ cả người.':'Hít vào… thở ra…'}</p></div>
    <button type="button" class="btn primary big" data-tv="miniTap"${m.step?'':' disabled'}>🌿 Thư giãn xong</button>`;
  return `<section class="sd-card tv-mini"><h3 data-focus-here tabindex="-1">${sp.emoji} ${esc(sp.name)}</h3><p class="tv-muted tv-small">${esc(k.kinds[sp.kind]?.verb||'')}${sp.fee?` · ${fmt(sp.fee)} xu`:''}</p>${body}
    <div class="tv-mini-foot"><button type="button" class="sd-link" data-tv="miniSkip">Bỏ qua trò chơi</button><button type="button" class="sd-link" data-tv="miniClose">Để sau</button></div></section>`;
}
function cardView(d,c){
  const sp=d.spots.find(x=>x.id===c.id);if(!sp)return '';
  return `<article class="tv-postcard"${theme(d)}><div class="tv-postcard-art" aria-hidden="true">${skyline(d)}<span class="tv-big">${sp.emoji}</span></div>
    <div class="tv-postcard-txt"><small>${c.new?'💌 Bưu thiếp mới':'💌 Bưu thiếp'} · ${esc(d.name)}</small><h3 data-focus-here tabindex="-1">${esc(sp.name)}</h3><p>${esc(sp.line)}</p>
    ${c.stars?`<p class="tv-stars" aria-label="${c.stars} sao">${'★'.repeat(c.stars)}${'☆'.repeat(3-c.stars)}</p>`:''}</div>
    <button type="button" class="btn primary" data-tv="cardClose">Tiếp tục ${icon('arrow',14)}</button></article>`;
}
function stampFx(d){return d?`<div class="tv-stampfx" aria-hidden="true"${theme(d)}><span><b>${esc(d.flag)}</b><small>${esc(d.name)}</small><small>Ngày ${day()}</small></span></div>`:'';}
function summaryView(x){
  const d=dest(x.to),k=K();
  return `${hero(d,'Về tới nhà rồi! Chuyến đi thật đáng nhớ.')}<section class="sd-card tv-summary"><h3>🏠 Tổng kết chuyến đi</h3>
    <ul><li><span>📍 Điểm đã ghé</span><b>${x.n}/${d.spots.length}</b></li><li><span>😊 Tinh thần</span><b>+${x.sp}</b></li>
    <li><span>💸 Tiêu ở ${esc(d.name)}</span><b>${fmt(x.xu)} xu</b></li><li><span>💌 Bưu thiếp ${esc(d.name)}</span><b>${x.cards}/${x.of}</b></li></ul>
    <p class="tv-muted tv-small">Xem lại hộ chiếu, bưu thiếp và quà ở 📕 Sổ du lịch.</p></section>`;
}

/* 📕 Sổ du lịch */
function bookView(t,k){
  const stamps=t?.stamps||{},cards=new Set(t?.cards||[]),souv=t?.souv||{};
  const pp=k.dests.map(d=>{const n=stamps[d.id]||0;return n?`<span class="tv-stamp"${theme(d)} title="${esc(d.name)}" role="img" aria-label="${esc(`${d.name}: đã đến ${n} lần`)}"><b>${esc(d.flag)}</b><small>${esc(d.name)}</small>${n>1?`<i>×${n}</i>`:''}</span>`:`<span class="tv-stamp empty" title="Chưa đến" role="img" aria-label="${esc(`${d.name}: chưa đến`)}"><b>?</b><small>${esc(d.name)}</small></span>`;}).join('');
  const been=k.dests.filter(d=>stamps[d.id]).length;
  const pc=k.dests.filter(d=>d.spots.some(s=>cards.has(s.id))).map(d=>`<div class="tv-pc-row"><h4>${esc(d.flag)} ${esc(d.name)} <small class="tv-muted">${d.spots.filter(s=>cards.has(s.id)).length}/${d.spots.length}</small></h4>
    <div class="tv-pcs">${d.spots.map(s=>cards.has(s.id)?`<span class="tv-pc"${theme(d)} title="${esc(s.name)}: ${esc(s.line)}" role="img" aria-label="${esc(`${s.name}: ${s.line}`)}">${s.emoji}<small>${esc(s.name)}</small></span>`:`<span class="tv-pc empty" title="Chưa có" role="img" aria-label="Chưa có">?</span>`).join('')}</div></div>`).join('');
  const gifts=k.dests.flatMap(d=>d.souv.filter(g=>souv[g.id]).map(g=>`<span class="tv-gift" title="${esc(g.name)} · ${esc(d.name)}" role="img" aria-label="${esc(`${g.name} · ${d.name}${souv[g.id]>1?` ×${souv[g.id]}`:''}`)}">${g.emoji}<small>${esc(g.name)}</small>${souv[g.id]>1?`<i>×${souv[g.id]}</i>`:''}</span>`)).join('');
  const log=(t?.log||[]).slice().reverse().map(r=>{const d=dest(r.to);return d?`<li><span>${esc(d.flag)} ${esc(d.name)}</span><small>Ngày ${r.d} · ${r.n} điểm · 😊+${r.sp}</small></li>`:'';}).join('');
  return `<section class="sd-card tv-passport"><h3>📕 Hộ chiếu <small class="tv-muted">${been}/${k.dests.length} nơi · ${t?.trips||0} chuyến</small></h3><div class="tv-stamps">${pp}</div></section>
    <section class="sd-card"><h3>💌 Bưu thiếp</h3>${pc||'<p class="tv-muted">Ghé các điểm tham quan để sưu tầm bưu thiếp.</p>'}</section>
    <section class="sd-card"><h3>🎁 Quà lưu niệm</h3>${gifts?`<div class="tv-gifts">${gifts}</div>`:'<p class="tv-muted">Chưa có món quà nào.</p>'}</section>
    ${log?`<section class="sd-card"><h3>🧳 Chuyến gần đây</h3><ul class="tv-log">${log}</ul></section>`:''}`;
}
/** For tests: the state object (reset between cases). */
export const _S=S;
