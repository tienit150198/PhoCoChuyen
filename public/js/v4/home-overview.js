/** 🗺️ Tổng quan nhà: the whole house at a glance (owner 23/10 "nhìn được tổng quan cái nhà nữa").
 * A cutaway of every floor (the plans: content.journey.homelife.plans, game/home_overview.py), the garden, the pool
 * and the garage under it; each room shows its pieces and Ấm cúng (state journey.homelife.ov.rooms) and who is in it.
 * A tap on a room of the place you live in hands over to the interior on that room (reno.js openReno(env,'room:<id>')).
 * Below: who is home, 🧹 Việc nhà hôm nay (jr_chore_do, game/home_chores.py), the rooms floor by floor.
 * The other homes you own show their plan only (furniture lives where you live). Phone first (390px): the stage pans
 * (native scroll) and zooms (− / +). Styles: /css/bank.css + /css/house.css + /css/homelife.css. */
import {icon,escapeHTML as esc} from '../icons.js';
import {myPortrait} from './look.js';

const S={dlg:null,env:null,kind:'',zoom:1,busy:false,flash:null,listening:false,fam:null,guests:[],famAt:0};
const J=()=>S.env?.api?.state?.journey||{};
const HL=()=>J().homelife||null;
const CAT=()=>S.env?.api?.content?.journey?.homelife||{plans:{},chores:{acts:[]}};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,op,data={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-ho="${op}"${attrs(data)}${S.busy?' disabled':''}${extra}>${label}</button>`;
export const ZOOM_MIN=.7, ZOOM_MAX=1.8, ZOOM_STEP=1.25;

/* ---- the cutaway's geometry (pure: tests/home_overview.mjs) ---- */
/** The house drawn for a screen `width` px wide, phone first: the roof, then each floor from the top (its label, its
 * rooms in rows that wrap at the width, each row stretched to fill it, widths by the rooms' columns; the balcony /
 * terrace and, on the ground floor, the garden and the pool after the rooms), the ground, then the garage under it.
 * `zoom` makes the rooms bigger (fewer a row) or smaller. {w, h, rooms, floors, roof, ground, garage}. */
export function layoutPlan(plan,{width=360,zoom=1}={}){
  const z=Math.max(ZOOM_MIN,Math.min(ZOOM_MAX,zoom)),u=11*z,H=Math.round(58*z),gap=4,pad=8,label=16;
  const bw=Math.max(160,Math.round(width)-pad*2),apt=plan?.group==='apartment';
  const floors=[...(plan?.floors||[])].sort((a,b)=>b.fl-a.fl);
  const order={in:0,deck:1,garden:2};
  const flow=list=>{
    const rows=[];let cur=[],used=0;
    for(const r of list){const nat=Math.min(bw,Math.max(3,r.cols)*u*(r.zone==='in'?1:.85));
      if(cur.length&&used+gap+nat>bw){rows.push(cur);cur=[];used=0;}cur.push([r,nat]);used+=(cur.length>1?gap:0)+nat;}
    if(cur.length)rows.push(cur);
    return rows.map(row=>{const tot=row.reduce((a,[,n])=>a+n,0),free=bw-gap*(row.length-1);let x=pad;
      return row.map(([r,n],i)=>{const w=i===row.length-1?pad+bw-x:Math.floor(n/tot*free);const o={r,x,w};x+=w+gap;return o;});});
  };
  const roofH=apt?22:Math.round(34*z),top=floors[0],roofed=Boolean(top&&top.rooms.some(r=>r.zone==='in'));
  let y=pad;const roof={x:pad,y,w:bw,h:roofH,on:apt||roofed};
  if(roof.on)y+=roofH;
  const rooms=[],rows=[];
  for(const f of floors){
    const fy=y;y+=label;
    for(const row of flow([...f.rooms].sort((a,b)=>(order[a.zone]??0)-(order[b.zone]??0)))){
      for(const {r,x,w} of row)rooms.push({...r,fl:f.fl,x,y,w,h:H});y+=H+gap;}
    rows.push({fl:f.fl,name:f.name,y:fy,h:y-fy});
    y+=2;
  }
  const ground=y;y+=6;
  const g=plan?.garage||{};let garage=null;
  if(g.slots>0){garage={x:pad,y,w:bw,h:Math.round(H*.95),style:g.style};y+=garage.h;}
  return {w:Math.round(width),h:Math.round(y+pad),rooms,floors:rows,roof,ground,garage};
}

/** Where each person stands (cosmetic): you in the living room, a child in the small bedroom, pets in the garden… */
const PREFS={me:['living','studio','attic','tro','bunk'],spouse:['kitchen','living','studio'],child:['bed2','living','bed','studio'],
  pet:['yard','pavilion','pool','balcony','terrace','living','studio','attic','tro','bunk'],guest:['suite','living','study','studio']};
export function placePeople(plan,people){
  const all=(plan?.floors||[]).flatMap(f=>f.rooms),ids=new Set(all.map(r=>r.id)),types=new Map(all.map(r=>[r.type,r.id]));
  const first=all.find(r=>r.zone==='in')?.id||all[0]?.id||'';let pets=0;
  return people.map(p=>{let prefs=PREFS[p.k]||PREFS.guest;if(p.k==='pet'&&pets++%2)prefs=['living',...prefs];
    const hit=prefs.find(t=>types.has(t)||ids.has(t));return {...p,room:hit?(types.get(hit)||hit):first};});
}

/* ---- styles on first use ---- */
let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
export const ensureCss=()=>cssReady??=Promise.all([link('/css/bank.css','bk-css'),link('/css/house.css','hs-css'),link('/css/homelife.css','hl-css')]);

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium bk-sheet hs-sheet ho-sheet';d.setAttribute('aria-labelledby','ho-title');
  d.innerHTML='<div class="ho-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-ho]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.ho,el.dataset);
  });
  d.addEventListener('close',()=>{S.flash=null;});
  S.dlg=d;return d;
}
export async function openOverview(env,kind){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';env.api.addEventListener('state',()=>{const key=JSON.stringify([J().homelife,J().deco?.cozy?.total,J().garage?.cars?.length]);if(key===seen)return;seen=key;if(S.dlg?.open&&!S.busy)render();});
  }
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();
  const homes=HL()?.ov?.homes||[];
  S.kind=kind&&CAT().plans[kind]?kind:(HL()?.ov?.kind||homes[0]?.kind||'');
  S.flash=null;
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();loadFamily();
}
export async function overviewAction(action,data,el,env){
  if(action!=='homeOverview')return false;
  await openOverview(env,data?.kind);return true;
}

/** The spouse at home and friends staying or visiting (the pages Nhà của bạn already reads). */
async function loadFamily(){
  if(Date.now()-S.famAt<15000)return;S.famAt=Date.now();
  const [m,g]=await Promise.all([S.env.api.json('/api/marriage').catch(()=>null),S.env.api.json('/api/home-guests').catch(()=>null)]);
  S.fam=m?{together:Boolean(m.family?.together),partner:m.couple?.status==='married'?m.couple?.partner?.name||'':''}:null;
  S.guests=(g?.active||[]).filter(x=>x.mine&&(x.kind==='stay'||x.kind==='visit')).slice(0,6).map(x=>({k:'guest',n:x.name||'Bạn',e:x.kind==='stay'?'🧳':'👋',stay:x.kind==='stay'}));
  if(S.dlg?.open&&!S.busy)render();
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
    case'home':S.kind=data.kind;S.flash=null;render();return;
    case'zoom':S.zoom=Math.max(ZOOM_MIN,Math.min(ZOOM_MAX,Number(data.d)>0?S.zoom*ZOOM_STEP:S.zoom/ZOOM_STEP));render();return;
    case'room':{
      if(!isHere()){S.flash={text:'Bạn đang không ở căn này. Dọn về đây để vào từng phòng nhé.',kind:'warn'};render();return;}
      if(!data.room)return;
      S.dlg.close();(await import('./reno.js')).openReno(S.env,'room:'+data.room);return;}
    case'chore':send('jr_chore_do',{act:data.act});return;
    case'garage':S.dlg.close();(await import('./villa-garage.js')).openVillaGarage(S.env);return;
    case'house':S.dlg.close();(await import('./house.js')).openHouse(S.env);return;
    case'pets':S.dlg.close();S.env.openSheet('home',{jrView:'household'});return;
  }
}

const isHere=()=>Boolean(S.kind&&S.kind===HL()?.ov?.kind);
/** The stage's width: the sheet's, less the card's padding. */
const stageWidth=()=>Math.max(240,Math.min(720,S.sw||(S.dlg?.querySelector('.ho-root')?.clientWidth||360)-34));

/* ---- rendering ---- */
function render(){
  if(!S.dlg)return;
  const root=S.dlg.querySelector('.ho-root');
  const scroller=root.querySelector('.ho-scroll'),left=scroller?.scrollLeft,top=scroller?.scrollTop,bodyTop=root.querySelector('.ho-body')?.scrollTop;
  root.innerHTML=page();
  const sc=root.querySelector('.ho-scroll');
  if(sc&&left!=null){sc.scrollLeft=left;sc.scrollTop=top;}else if(sc){sc.scrollLeft=Math.max(0,(sc.scrollWidth-sc.clientWidth)/2);}
  const body=root.querySelector('.ho-body');if(body&&bodyTop)body.scrollTop=bodyTop;
  S.dlg.setAttribute('aria-busy',String(S.busy));
  const w=sc?.clientWidth;if(w&&Math.abs(w-(S.sw||0))>1&&!S.measuring){S.sw=w;S.measuring=true;try{render();}finally{S.measuring=false;}}   // the stage is drawn for the width it really has
}
function head(plan){
  return `<header class="sheet-head bk-head hs-head"><span class="hs-logo" aria-hidden="true">🗺️</span>
    <div class="grow"><span class="eyebrow">TỔNG QUAN NHÀ</span><h2 id="ho-title">${esc(plan?.name||'Nhà của bạn')}</h2><p>${isHere()?'Nơi bạn đang ở':'Nhà của bạn · đang để trống'}</p></div>
    <button class="icon-btn" type="button" data-ho="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
}
const flash=()=>`<p class="bk-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
function page(){
  const j=J();
  if(!j.story)return head(null)+`<div class="sheet-body bk ho-body"><section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🏠</div><h3>Chỉ có trong chế độ hành trình</h3></section></div>`;
  const plan=CAT().plans[S.kind];
  if(!plan)return head(null)+`<div class="sheet-body bk ho-body"><section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🏠</div><h3>Chưa xem được căn này</h3><p>Tải lại trang để có bản mới nhé.</p>${btn('🏠 Nhà của bạn','house',{},'primary')}</section></div>`;
  return head(plan)+`<div class="sheet-body bk ho-body">${flash()}${homesRow()}${summary(plan)}${stage(plan)}${whoCard(plan)}${isHere()?choresCard():''}${roomList(plan)}
    <div class="bk-actions">${btn(plan.garage?.style==='ham'?'🚘 Hầm để xe':'🛵 Chỗ để xe','garage',{},'cream')}${btn('🏠 Nhà của bạn','house',{},'cream')}</div></div>`;
}
function homesRow(){
  const homes=HL()?.ov?.homes||[];if(homes.length<2)return '';
  return `<div class="ho-homes" role="tablist" aria-label="Chọn căn nhà">${homes.map(h=>{const p=CAT().plans[h.kind];if(!p)return '';
    return `<button type="button" role="tab" class="ho-home${h.kind===S.kind?' on':''}" aria-selected="${h.kind===S.kind}" data-ho="home" data-kind="${esc(h.kind)}"><span aria-hidden="true">${p.emoji}</span>${esc(p.name)}${h.live?' <small>· đang ở</small>':''}</button>`;}).join('')}</div>`;
}
const stats=()=>isHere()?HL()?.ov?.rooms||{}:{};
function summary(plan){
  const rooms=plan.floors.reduce((n,f)=>n+f.rooms.length,0),st=stats(),pieces=Object.values(st).reduce((n,x)=>n+(x[0]||0),0);
  const cozy=isHere()?J().deco?.cozy?.total:null;
  return `<p class="hs-chips ho-sum"><span>🏢 ${plan.floors.length>1?`${plan.floors.length} tầng`:'1 tầng'}</span><span>🚪 ${rooms} phòng</span>${isHere()?`<span>🪑 ${fmt(pieces)} món</span>`:''}${cozy!=null?`<span>🪴 Ấm cúng ${fmt(cozy)}</span>`:''}${plan.has?.pool?'<span>🏊 Hồ bơi</span>':''}${plan.has?.garden?'<span>🌳 Sân vườn</span>':''}<span>🅿️ ${plan.garage?.slots||0} chỗ xe</span></p>`;
}
function people(plan){
  if(!isHere())return [];
  const ov=HL()?.ov||{},list=[...(ov.who||[])];
  const spouse=S.fam?.partner&&(S.fam.together||ov.where==='shared');
  if(spouse)list.splice(1,0,{k:'spouse',n:S.fam.partner,e:'💞'});
  return placePeople(plan,[...list,...(S.guests||[])]);
}
function face(p,size=22){
  if(p.k==='me'){const st=S.env?.api?.state;try{return `<span class="ho-face me">${myPortrait(st,size,'Bạn')}</span>`;}catch{return `<span class="ho-face me">🙂</span>`;}}
  return `<span class="ho-face" title="${esc(p.n||'')}">${esc(p.e||'🙂')}</span>`;
}
function roomHTML(r,st,ppl){
  const [n,cz]=st[r.id]||[0,0],here=ppl.filter(p=>p.room===r.id);
  const small=r.w<64;
  const label=`${r.name}${isHere()?`: ${n} món, ấm cúng ${cz}`:''}${here.length?`, có ${here.map(p=>p.k==='me'?'bạn':p.n).join(', ')}`:''}`;
  return `<button type="button" class="ho-room z-${esc(r.zone)} t-${esc(r.type)}" data-ho="room" data-room="${esc(r.id)}" style="left:${r.x}px;top:${r.y}px;width:${r.w}px;height:${r.h}px" aria-label="${esc(label)}">
    <span class="ho-rname"><span aria-hidden="true">${r.emoji}</span>${small?'':` ${esc(r.name)}`}</span>
    ${isHere()&&(n||cz)?`<span class="ho-badge" aria-hidden="true">🪑${n}${cz?` · 🪴${cz}`:''}</span>`:''}
    ${here.length?`<span class="ho-people" aria-hidden="true">${here.map(p=>face(p)).join('')}</span>`:''}</button>`;
}
function garageHTML(plan,G){
  if(!G)return '';
  const hx=HL()?.hamxe,cars=J().garage?.cars||[],V=S.env?.api?.content?.journey?.garage?.vehicles||[];
  const parked=isHere()&&hx?hx.park:[],slots=Math.max(1,plan.garage?.slots||1);
  const bay=i=>{const id=parked[i],it=id&&V.find(v=>v.id===id),c=id&&cars.find(x=>x.id===id);return `<span class="ho-bay${it?' full':''}">${it?`<i style="--gr-paint:${esc(paintHex(c?.color||it.paint))}">${it.emoji}</i>`:''}</span>`;};
  const n=Math.min(slots,12);
  return `<button type="button" class="ho-garage s-${esc(G.style)}" data-ho="garage" style="left:${G.x}px;top:${G.y}px;width:${G.w}px;height:${G.h}px" aria-label="${esc(`${plan.garage.name}: ${parked.length}/${slots} chỗ có xe. Mở chỗ để xe`)}">
    <span class="ho-rname"><span aria-hidden="true">${G.style==='ham'?'🚘':'🅿️'}</span> ${esc(plan.garage.name)}</span><span class="ho-bays" aria-hidden="true">${Array.from({length:n},(_,i)=>bay(i)).join('')}</span></button>`;
}
const paintHex=id=>(S.env?.api?.content?.journey?.garage?.paints||[]).find(p=>p.id===id)?.hex||'#c9c3b8';
function stage(plan){
  const z=S.zoom,L=layoutPlan(plan,{width:stageWidth(),zoom:z}),st=stats(),ppl=people(plan),apt=plan.group==='apartment';
  const floors=L.floors.map(f=>`<span class="ho-flabel" style="top:${f.y}px">${esc(f.name)}</span><span class="ho-slab" style="left:${L.roof.x}px;top:${f.y+f.h-2}px;width:${L.roof.w}px"></span>`).join('');
  const roof=!L.roof.on?'':apt?`<span class="ho-apt" style="left:${L.roof.x}px;top:${L.roof.y}px;width:${L.roof.w}px;height:${L.roof.h}px" aria-hidden="true">🏢 Tầng trên</span>`
    :`<span class="ho-roof" style="left:${L.roof.x}px;top:${L.roof.y}px;width:${L.roof.w}px;height:${L.roof.h}px" aria-hidden="true"></span>`;
  const ground=`<span class="ho-ground" style="top:${L.ground}px"></span>`;
  const hint=isHere()?'Chạm một phòng để vào phòng đó.':'Căn này đang để trống: xem sơ đồ, dọn về ở để bày trí.';
  return `<section class="bk-card ho-card"><div class="ho-tools"><small>${hint}</small><span class="ho-zoom" role="group" aria-label="Thu phóng">${btn('−','zoom',{d:-1},'ghost small',' aria-label="Thu nhỏ sơ đồ"')}<b>${Math.round(z*100)}%</b>${btn('+','zoom',{d:1},'ghost small',' aria-label="Phóng to sơ đồ"')}</span></div>
    <div class="ho-scroll" tabindex="0" aria-label="Sơ đồ ${esc(plan.name)}"><div class="ho-stage g-${esc(plan.group)}" style="width:${L.w}px;height:${L.h}px;--z:${z}">
      <span class="ho-sky" style="height:${L.ground}px"></span>${roof}${ground}${floors}${garageHTML(plan,L.garage)}${L.rooms.map(r=>roomHTML(r,st,ppl)).join('')}</div></div></section>`;
}
function whoCard(plan){
  const ppl=people(plan);if(!ppl.length)return '';
  const rooms=new Map(plan.floors.flatMap(f=>f.rooms).map(r=>[r.id,r]));
  const name=p=>p.k==='me'?'Bạn':p.n;
  const pets=ppl.some(p=>p.k==='pet'||p.k==='child');
  return `<section class="bk-card"><h3>🏡 Ai đang ở nhà</h3><ul class="ho-who">${ppl.map(p=>{const r=rooms.get(p.room);
    return `<li>${face(p,28)}<span><b>${esc(name(p))}</b><small>${r?`${r.emoji} ${esc(r.name)}`:''}${p.k==='guest'?(p.stay?' · ở cùng':' · ghé chơi'):''}</small></span></li>`;}).join('')}</ul>
    ${pets?btn('🍼 Chăm sóc gia đình','pets',{},'ghost small'):''}</section>`;
}
function choresCard(){
  // state {done:[ids], no?:{id:code}, paid?, streak?}; names, the WHY texts and the rules: the catalogue (game/home_chores.py)
  const C=HL()?.chores,K=CAT().chores||{};if(!C||!K.acts)return '';
  const done=C.done||[],no=C.no||{},at=K.bonus_at||3,prog=Math.min(done.length,at);
  const rows=K.acts.map(x=>{const d=done.includes(x.id),why=!d&&no[x.id]?(K.why?.[no[x.id]]||'—'):'';
    return btn(`<span aria-hidden="true">${x.emoji}</span><span class="ho-ctext">${esc(x.name)}${why?`<small>${esc(why)}</small>`:''}</span>${d?'<b class="ho-done" aria-label="Đã làm">✓</b>':''}`,'chore',{act:x.id},`ho-chore${d?' done':''}`,d||why?' disabled':'');}).join('');
  return `<section class="bk-card ho-chores"><h3>🧹 Việc nhà hôm nay</h3>
    <div class="ho-prog" role="progressbar" aria-valuemin="0" aria-valuemax="${at}" aria-valuenow="${prog}" aria-label="Việc nhà hôm nay"><i style="width:${Math.round(prog/at*100)}%"></i></div>
    <p class="bk-hint">${C.paid?`✅ Nhà gọn gàng: đã nhận +${fmt(K.bonus)} xu hôm nay.`:`Làm ${at} việc: +${fmt(K.bonus)} xu. Mỗi ngày ${K.spirit_max||2} việc đầu +1 tinh thần.`}${C.streak>1?` 🔥 ${C.streak} ngày liền (ngày thứ ${K.every}: +${fmt(K.streak_xu)} xu).`:''}</p>
    <div class="ho-chore-grid">${rows}</div></section>`;
}
function roomList(plan){
  const st=stats();
  return `<details class="bk-card ho-list"><summary><b>📋 Từng phòng</b><small>${plan.floors.reduce((n,f)=>n+f.rooms.length,0)} phòng</small></summary>${plan.floors.map(f=>`<h4>${esc(f.name)}</h4><ul>${f.rooms.map(r=>{const [n,cz]=st[r.id]||[0,0];
    return `<li><button type="button" class="ho-row" data-ho="room" data-room="${esc(r.id)}"><span aria-hidden="true">${r.emoji}</span><span class="grow">${esc(r.name)}</span>${isHere()?`<small>🪑 ${n} · 🪴 ${cz}</small>`:''}<i aria-hidden="true">›</i></button></li>`;}).join('')}</ul>`).join('')}</details>`;
}
