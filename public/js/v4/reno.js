/** 🛠️ Trong nhà: vào xem nhà, sửa nhà, trang trí (story mode, a home you own).
 * Every rule and price lives in game/reno.py; this file draws api.state.journey.reno (one SVG room per tab: the
 * walls, ceiling, floor, light and kitchen as the parts' condition and upgrades make them, the furniture in its
 * slots) and sends `jr_reno_*` commands. Its own dialog, opened from 🏠 Nhà của bạn (v4/house.js); the back
 * button returns there. Styles: /css/bank.css + /css/house.css + /css/reno.css (theme tokens; the room's own
 * colours dim with the scene filter in "Phố đêm"). */
import {icon,escapeHTML as esc} from '../icons.js';

const S={dlg:null,env:null,mode:'look',room:'',pick:null,sel:'',move:'',busy:false,flash:null,listening:false};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const low=s=>String(s||'').slice(0,1).toLowerCase()+String(s||'').slice(1);
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,op,data={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-rn="${op}"${attrs(data)}${S.busy?' disabled':''}${extra}>${label}</button>`;
const V=()=>S.env?.api?.state?.journey?.reno||null;
const C=()=>S.env?.api?.content?.journey?.reno||{parts:[],items:[],steps:[]};
const ITEM=k=>C().items.find(x=>x.id===k);
const PART=id=>C().parts.find(x=>x.id===id)||{};
const POCKET=['account','wallet'];   // reno.py pays like the house: the account first, the rest in cash
const condWord=(c,p)=>c>=85?'Như mới':c>=65?'Còn tốt':c>=45?'Hơi cũ':(PART(p).flaw||'Xuống cấp');
const tone=c=>c>=65?'good':c>=45?'warn':'bad';

/* ---- styles on first use ---- */
let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=Promise.all([link('/css/bank.css','bk-css'),link('/css/house.css','hs-css'),link('/css/reno.css','rn-css')]);

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium bk-sheet rn-sheet';d.setAttribute('aria-labelledby','rn-title');
  d.innerHTML='<div class="rn-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-rn]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.rn,el.dataset);
  });
  d.addEventListener('keydown',e=>{   // the room's slots and furniture are SVG groups: Enter/Space tap them
    if(e.key!=='Enter'&&e.key!==' ')return;const el=e.target.closest?.('g[data-rn]');if(!el)return;
    e.preventDefault();onClick(el.dataset.rn,el.dataset);
  });
  d.addEventListener('close',()=>{S.flash=null;S.pick=null;S.sel='';S.move='';});
  S.dlg=d;return d;
}
export async function openReno(env,mode){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';env.api.addEventListener('state',()=>{const key=JSON.stringify([V(),S.env.api.state?.journey?.wallet]);if(key===seen)return;seen=key;if(S.dlg?.open&&!S.busy)render();});
  }
  await ensureCss();
  const d=dialog();
  S.mode=['look','fix','decor'].includes(mode)?mode:'look';S.pick=null;S.sel='';S.move='';S.flash=null;
  const v=V();if(v&&!v.rooms.some(r=>r.id===S.room))S.room=v.rooms[0]?.id||'';
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
}

async function send(action,payload={}){
  const {api}=S.env;S.busy=true;render();
  try{
    const r=await api.command(action,payload);
    S.flash={text:[r.message,...(r.effects||[]).filter(Boolean)].filter(Boolean).join(' '),kind:'good'};
    return r;
  }catch(e){S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}   // quiet: api.js, a double tap
  finally{S.busy=false;render();}
}
const ask=(title,msg,label,cost)=>S.env.confirmAction(title,msg,label,{cost,pocket:POCKET});
const roomOf=id=>(V()?.rooms||[]).find(r=>r.id===id)||{};
const fitsSlot=(it,room,slot)=>it&&it.rooms.includes(room)&&(slot[0]==='w')===(it.spot==='wall');
const spotWord=slot=>slot[0]==='w'?'trên tường':'dưới sàn';

async function onClick(op,data){
  const v=V();
  switch(op){
    case'close':S.dlg.close();return;
    case'back':S.dlg.close();(await import('./house.js')).openHouse(S.env);return;
    case'mode':S.mode=data.mode;S.pick=null;S.sel='';S.move='';S.flash=null;render();return;
    case'room':S.room=data.room;S.pick=null;S.sel='';render();return;
    case'cancel':S.pick=null;S.sel='';S.move='';render();return;
    case'slot':{
      if(S.mode!=='decor')return;
      if(S.move){const x=[...v.items,...v.kho].find(i=>i.id===S.move),it=ITEM(x?.k);if(!x){S.move='';render();return;}
        if(!fitsSlot(it,data.room,data.slot)){S.flash={text:`${it.name} cần chỗ ${it.spot==='wall'?'trên tường':'dưới sàn'}${it.rooms.includes(data.room)?'':` ở ${it.rooms.map(r=>low(roomName(r))).filter(Boolean).join(', ')}`}.`,kind:'warn'};render();return;}
        const uid=S.move;S.move='';S.sel='';await send('jr_reno_move',{uid,room:data.room,slot:data.slot});return;}
      S.pick={room:data.room,slot:data.slot};S.sel='';render();S.dlg.querySelector('.rn-panel')?.scrollIntoView?.({block:'nearest',behavior:'smooth'});return;}
    case'item':if(S.mode!=='decor'){S.mode='decor';}S.sel=data.uid;S.pick=null;S.move='';render();return;
    case'buy':{const it=ITEM(data.item),p=S.pick;if(!it||!p)return;
      if(await ask(`Mua ${low(it.name)}?`,`Đặt ${spotWord(p.slot)} ở ${low(roomOf(p.room).name)}. Ấm cúng +${it.cozy} nếu nhà chưa có món này.`,`Mua · ${xu(it.price)}`,it.price)){
        const r=await send('jr_reno_buy',{item:it.id,room:p.room,slot:p.slot,confirm:true});if(r){S.pick=null;render();}}return;}
    case'put':{const p=S.pick;if(!p)return;S.pick=null;await send('jr_reno_move',{uid:data.uid,room:p.room,slot:p.slot});return;}
    case'pickup':S.move=data.uid;S.sel='';S.pick=null;S.mode='decor';render();return;
    case'store':S.sel='';await send('jr_reno_store',{uid:data.uid});return;
    case'sell':{const x=[...v.items,...v.kho].find(i=>i.id===data.uid),it=ITEM(x?.k);if(!it)return;
      if(await S.env.confirmAction(`Bán lại ${low(it.name)}?`,`Nhận ${xu(it.sell)} (${C().sell_pct}% giá mua).`,`Bán · ${xu(it.sell)}`)){S.sel='';await send('jr_reno_sell',{uid:x.id,confirm:true});}return;}
    case'fix':{const all=data.part==='all',p=v.parts.find(x=>x.id===data.part),cost=all?v.fix_all:p?.fix;if(!cost)return;
      const what=all?'Sửa cả nhà?':`Sửa ${low(PART(p.id).name)}?`,body=all?v.parts.filter(x=>x.fix).map(x=>`${PART(x.id).name} ${xu(x.fix)}`).join(' · '):`${condWord(p.c,p.id)} (${p.c}%) → như mới.`;
      if(await ask(what,body,`Sửa · ${xu(cost)}`,cost))send('jr_reno_fix',{part:data.part,cost,confirm:true});return;}
    case'up':{const p=v.parts.find(x=>x.id===data.part);if(!p?.up)return;
      if(await ask(`${p.up.name}?`,`${PART(p.id).name} như mới, bền hơn. Ấm cúng +${C().cozy_lv}.`,`Làm · ${xu(p.up.cost)}`,p.up.cost))send('jr_reno_up',{part:p.id,lv:p.up.lv,cost:p.up.cost,confirm:true});return;}
  }
}
const roomName=id=>{const r=(V()?.rooms||[]).find(x=>x.id===id);return r?r.name:'';};

/* ---- rendering ---- */
function render(){
  if(!S.dlg)return;
  const body=S.dlg.querySelector('.rn-body'),top=body?.scrollTop;
  S.dlg.querySelector('.rn-root').innerHTML=page();
  const b2=S.dlg.querySelector('.rn-body');if(b2&&top!=null)b2.scrollTop=top;
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
function head(v){
  const h=v?.home;
  return `<header class="sheet-head bk-head rn-head"><button class="icon-btn" type="button" data-rn="back" aria-label="Về Nhà của bạn">${icon('back',21)}</button>
    <div class="grow"><span class="eyebrow">TRONG NHÀ</span><h2 id="rn-title">${h?`${h.emoji} ${esc(h.name)}`:'Nhà của bạn'}</h2></div>
    <button class="icon-btn" type="button" data-rn="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
}
const flash=()=>`<p class="bk-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
function page(){
  const v=V();
  if(!v)return head(v)+`<div class="sheet-body bk rn-body"><section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🔑</div><h3>Chưa có nhà riêng</h3><p>Mua nhà rồi vào sửa sang, trang trí theo ý mình.</p>${btn('🏠 Nhà của bạn','back',{},'primary')}</section></div>`;
  if(!v.rooms.some(r=>r.id===S.room))S.room=v.rooms[0].id;
  const worn=v.parts.some(p=>p.worn);
  const tabs=[['look','🏠 Xem nhà'],['fix',`🛠️ Sửa nhà${worn?'<i class="dot" aria-hidden="true"></i>':''}`],['decor','🪴 Trang trí']];
  const bar=`<div class="segmented bk-tabs rn-tabs" role="tablist" aria-label="Trong nhà">${tabs.map(([id,l])=>`<button type="button" role="tab" aria-selected="${S.mode===id}" class="${S.mode===id?'active':''}" data-rn="mode" data-mode="${id}">${l}</button>`).join('')}</div>`;
  const panel=S.mode==='fix'?fixPanel(v):S.mode==='decor'?decorPanel(v):lookPanel(v);
  return head(v)+`<div class="sheet-body bk rn-body">${bar}${flash()}<div class="rn-grid"><div class="rn-stage">${roomTabs(v)}${scene(v,roomOf(S.room))}</div><div class="rn-panel">${panel}</div></div></div>`;
}
function roomTabs(v){
  const n=id=>v.items.filter(i=>i.r===id).length;
  return `<div class="rn-rooms" role="tablist" aria-label="Các phòng">${v.rooms.map(r=>`<button type="button" role="tab" aria-selected="${S.room===r.id}" class="rn-room${S.room===r.id?' active':''}" data-rn="room" data-room="${r.id}"><span aria-hidden="true">${r.emoji}</span>${esc(r.name)}${n(r.id)?`<small>${n(r.id)}</small>`:''}</button>`).join('')}</div>`;
}

/* ---- the room (SVG 360×230): back wall or sky, ceiling, light, floor, kitchen counter, then slots and furniture ---- */
const W=360,H=230,FY=150;
function scene(v,rm){
  const P=Object.fromEntries(v.parts.map(p=>[p.id,p])),sev=p=>p.c<45?2:p.c<60?1:0;
  const wall=P.wall,roof=P.roof,floor=P.floor,power=P.power,kit=P.kitchen,g=[];
  const ws=Array.from({length:rm.wall},(_,i)=>({slot:'w'+i,x:Math.round(W*(i+1)/(rm.wall+1)),y:rm.id==='kitchen'?88:76}));
  const fs=Array.from({length:rm.floor},(_,i)=>({slot:'f'+i,x:Math.round(W*(i+.5)/rm.floor),y:190}));
  if(rm.out){
    g.push(`<rect class="rn-sky" width="${W}" height="${FY}"/><circle class="rn-sun" cx="300" cy="40" r="16"/>`,
      `<path class="rn-city" d="M0 ${FY}V96h34v-18h26v30h30V88h22v24h40V80h28v34h36V92h30v20h32V84h26v${FY-84}z"/>`);
    if(rm.id==='balcony')g.push(`<rect class="rn-rail" x="0" y="${FY-34}" width="${W}" height="5"/>`+Array.from({length:19},(_,i)=>`<rect class="rn-rail" x="${i*20+4}" y="${FY-34}" width="3" height="34"/>`).join(''));
    else g.push(`<path class="rn-hedge" d="M0 ${FY}V${FY-22}q15-14 30 0q15-14 30 0q15-14 30 0q15-14 30 0q15-14 30 0q15-14 30 0q15-14 30 0q15-14 30 0q15-14 30 0q15-14 30 0q15-14 30 0q15-14 30 0V${FY}z"/>`);
  }else{
    g.push(`<rect class="rn-wall l${wall.lv}" width="${W}" height="${FY}"/>`);
    if(wall.lv===2)g.push(`<rect width="${W}" height="${FY}" fill="url(#rn-paper)"/><rect class="rn-wainscot" y="${FY-26}" width="${W}" height="26"/>`);
    if(rm.wall===2&&rm.id!=='kitchen')g.push(`<rect class="rn-window" x="150" y="44" width="60" height="62" rx="4"/><path class="rn-frame" d="M150 44h60v62h-60zM180 44v62M150 75h60"/>`);
    if(sev(wall))g.push(`<path class="rn-peel" d="M22 92q10-8 22-2l6 10q-12 10-24 2zM262 52q12-6 20 2l-4 12q-12 2-18-6z"/>`+(sev(wall)>1?`<path class="rn-peel" d="M300 104q14-4 22 6l-6 12q-14 0-18-10zM96 30q8-6 18 0l-4 10q-10 2-14-4z"/><path class="rn-crack" d="M70 20l8 18-6 10 10 16M232 96l-6 14 8 8-4 14"/>`:''));
    g.push(`<rect class="rn-ceil" width="${W}" height="14"/>`);
    if(roof.lv===2)g.push(`<rect class="rn-led" y="13" width="${W}" height="3"/>`);
    if(sev(roof))g.push(`<ellipse class="rn-stain" cx="92" cy="18" rx="${sev(roof)>1?40:26}" ry="${sev(roof)>1?13:9}"/>`+(sev(roof)>1?`<ellipse class="rn-stain" cx="276" cy="16" rx="22" ry="7"/><circle class="rn-drip" cx="96" cy="30" r="3"/><circle class="rn-drip d2" cx="80" cy="30" r="2.5"/>`:''));
    g.push(`<path class="rn-cord" d="M180 14v18"/><circle class="rn-bulb${sev(power)?' dim':''}${power.lv===2?' led':''}" cx="180" cy="38" r="7"/>`);
    if(power.lv>=1)g.push(`<rect class="rn-switch" x="${rm.wall===2?222:16}" y="${FY-50}" width="9" height="13" rx="2"/>`);
  }
  // Floor: tiles (old, new) or wood planks, seen a little from above.
  const fl=rm.out&&rm.id==='yard'?'grass':`l${floor.lv}`;
  g.push(`<rect class="rn-floor ${fl}" y="${FY}" width="${W}" height="${H-FY}"/>`);
  if(fl!=='grass'){
    const lines=[];
    for(let i=0;i<=8;i++){const xb=i*W/8,xt=W/2+(xb-W/2)*.82;if(floor.lv<2||rm.out)lines.push(`M${xt.toFixed(1)} ${FY}L${xb.toFixed(1)} ${H}`);}
    const rows=floor.lv===2&&!rm.out?[164,180,198,218]:[166,188,214];
    rows.forEach(y=>lines.push(`M0 ${y}H${W}`));
    if(floor.lv===2&&!rm.out)[[40,164,180],[150,180,198],[250,164,180],[90,198,218],[300,198,218],[200,150,164]].forEach(([x,a,b])=>lines.push(`M${x} ${a}V${b}`));
    g.push(`<path class="rn-joint ${fl}" d="${lines.join('')}"/>`);
    if(sev(floor)&&!rm.out)g.push(`<path class="rn-crack" d="M60 170l14 6-4 10 12 8M268 200l10-8 12 4"/>`+(sev(floor)>1?`<path class="rn-hole" d="M140 206l26-2 4 14-28 2z"/>`:''));
  }else g.push(`<path class="rn-grass-tuft" d="M30 200l4-8 4 8M120 214l4-8 4 8M220 196l4-8 4 8M320 216l4-8 4 8"/>`);
  if(rm.id==='kitchen')g.push(kitchen(kit,sev(kit)));
  // Slots and furniture.
  const byXY=new Map(v.items.filter(i=>i.r===rm.id).map(i=>[i.x,i]));
  const moving=S.move?ITEM(([...v.items,...v.kho].find(i=>i.id===S.move)||{}).k):null;
  for(const s of [...ws,...fs]){
    const it=byXY.get(s.slot),wallSpot=s.slot[0]==='w';
    if(it){
      const m=ITEM(it.k);if(!m)continue;
      const sel=S.sel===it.id||S.move===it.id,size=wallSpot?36:50;
      g.push(`<g class="rn-item${sel?' sel':''}" data-rn="item" data-uid="${esc(it.id)}" tabindex="0" role="button" aria-label="${esc(m.name)}">`+
        `<circle class="rn-hit" cx="${s.x}" cy="${s.y}" r="${size/2+4}"/>`+
        (wallSpot?'':`<ellipse class="rn-shadow" cx="${s.x}" cy="${s.y+23}" rx="26" ry="5"/>`)+
        (sel?`<circle class="rn-ring" cx="${s.x}" cy="${s.y}" r="${size/2+6}"/>`:'')+
        `<text x="${s.x}" y="${s.y}" font-size="${size}" text-anchor="middle" dominant-baseline="central">${m.emoji}</text></g>`);
    }else if(S.mode==='decor'){
      const ok=!moving||fitsSlot(moving,rm.id,s.slot),on=S.pick&&S.pick.room===rm.id&&S.pick.slot===s.slot;
      if(!ok)continue;
      g.push(`<g class="rn-slot${on?' on':''}${moving?' go':''}" data-rn="slot" data-room="${rm.id}" data-slot="${s.slot}" tabindex="0" role="button" aria-label="Chỗ trống ${spotWord(s.slot)}">`+
        `<circle cx="${s.x}" cy="${s.y}" r="20"/><path d="M${s.x-7} ${s.y}h14M${s.x} ${s.y-7}v14"/></g>`);
    }
  }
  const label=`${rm.name}: ${v.parts.filter(p=>p.worn).map(p=>low(PART(p.id).flaw)).join(', ')||'nhà sạch đẹp'}`;
  return `<svg class="rn-scene${rm.out?' out':''}" viewBox="0 0 ${W} ${H}" role="group" aria-label="${esc(label)}">
    <defs><pattern id="rn-paper" width="24" height="24" patternUnits="userSpaceOnUse"><path class="rn-motif" d="M12 5l2 5 5 2-5 2-2 5-2-5-5-2 5-2z"/></pattern></defs>${g.join('')}</svg>`;
}
function kitchen(k,sev){
  const out=[];
  if(k.lv===2)out.push(`<rect class="rn-cab" x="24" y="20" width="312" height="34" rx="3"/><path class="rn-cab-line" d="M102 20v34M180 20v34M258 20v34"/><path class="rn-hood" d="M210 54h44l8 14h-60z"/>`);
  else if(k.lv===1)out.push(`<rect class="rn-shelf" x="40" y="52" width="110" height="5" rx="2"/>`);
  out.push(`<rect class="rn-counter" x="20" y="112" width="320" height="38"/><rect class="rn-counter-top" x="16" y="106" width="328" height="8" rx="2"/>`,
    `<rect class="rn-sink" x="60" y="106" width="56" height="6" rx="2"/><path class="rn-tap" d="M88 106v-12h10"/>`);
  if(k.lv===0)out.push(`<rect class="rn-stove old" x="214" y="94" width="40" height="12" rx="2"/><circle class="rn-burner" cx="234" cy="94" r="6"/>`);
  else out.push(`<rect class="rn-stove" x="204" y="100" width="62" height="7" rx="2"/><ellipse class="rn-burner" cx="222" cy="100" rx="8" ry="2.5"/><ellipse class="rn-burner" cx="248" cy="100" rx="8" ry="2.5"/>`);
  if(sev)out.push(`<ellipse class="rn-soot" cx="234" cy="${k.lv===2?84:78}" rx="${sev>1?34:22}" ry="${sev>1?20:13}"/>`);
  return out.join('');
}

/* ---- panels ---- */
function cozyCard(v){
  const steps=[...(C().steps||[])].sort((a,b)=>a.min-b.min),next=steps.find(s=>s.min>v.cozy);
  let line;
  if(v.perk&&v.perk_on)line=`<p class="rn-perk on">😊 +${v.perk} tinh thần mỗi sáng</p>`;
  else if(v.perk)line=`<p class="rn-perk">${v.late?`😊 +${v.perk} tinh thần tạm dừng khi trễ hạn trả góp`:`🛠️ Sửa nhà tới ${C().cozy_cond}% để có +${v.perk} tinh thần mỗi sáng`}</p>`;
  else line='';
  const more=next?`<p class="bk-hint">Thêm ${next.min-v.cozy} điểm: +${next.spirit} tinh thần mỗi sáng.</p>`:'';
  return `<section class="bk-card rn-cozy"><div class="rn-cozy-top"><span class="rn-cozy-num" aria-hidden="true">${v.cozy}</span><div class="grow"><small>Ấm cúng</small><b>${v.cozy>=((steps[steps.length-1]||{}).min||99)?'Rất ấm cúng':v.cozy>=((steps[0]||{}).min||99)?'Ấm cúng':'Còn trống trải'}</b></div></div>${line}${more}</section>`;
}
function lookPanel(v){
  const worn=v.parts.filter(p=>p.worn);
  const cond=`<section class="bk-card"><h3>Tình trạng nhà · ${v.cond}%</h3><div class="bk-bar ${tone(v.cond)}" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${v.cond}" aria-label="Tình trạng nhà"><i style="width:${v.cond}%"></i></div>
    ${worn.length?`<ul class="rn-flaws">${worn.map(p=>`<li>${PART(p.id).emoji} ${esc(PART(p.id).flaw)}</li>`).join('')}</ul><div class="bk-actions">${btn(`🛠️ Sửa nhà · ${xu(v.fix_all)}`,'mode',{mode:'fix'},'primary')}</div>`:'<p class="bk-hint">Nhà sạch đẹp.</p>'}</section>`;
  const stuff=`<section class="bk-card"><dl class="hs-facts rn-facts"><div><dt>Đồ đạc</dt><dd>${v.items.length} món${v.kho.length?` · kho ${v.kho.length}`:''}</dd></div><div><dt>Đã chi cho nhà</dt><dd>${xu(v.spent)}</dd></div></dl>
    <div class="bk-actions">${btn('🪴 Trang trí','mode',{mode:'decor'},v.items.length?'ghost':'primary')}</div></section>`;
  return cozyCard(v)+cond+stuff;
}
function fixPanel(v){
  const need=v.parts.filter(p=>p.fix),ready=v.ready;
  const short=n=>n>ready?` disabled`:'';
  const all=need.length>1?`<div class="bk-actions rn-fixall">${btn(`🛠️ Sửa hết · ${xu(v.fix_all)}`,'fix',{part:'all'},'primary',short(v.fix_all))}</div>`:'';
  const rows=v.parts.map(p=>{const m=PART(p.id);
    return `<li class="rn-part ${tone(p.c)}"><div class="rn-part-top"><span class="rn-part-ico" aria-hidden="true">${m.emoji}</span><div class="grow"><b>${esc(m.name)}</b><small>${esc(condWord(p.c,p.id))} · ${p.c}%</small></div><span class="rn-lv" aria-label="Nâng cấp ${p.lv}/2">${'★'.repeat(p.lv)}${'☆'.repeat(2-p.lv)}</span></div>
      <div class="bk-bar ${tone(p.c)}" aria-hidden="true"><i style="width:${p.c}%"></i></div>
      <div class="rn-part-go">${p.fix?btn(`Sửa · ${xu(p.fix)}`,'fix',{part:p.id},'ghost',short(p.fix)):''}${p.up?btn(`⬆ ${esc(p.up.name)} · ${xu(p.up.cost)}`,'up',{part:p.id},'ghost',short(p.up.cost)):'<span class="rn-max">Đã nâng cấp hết</span>'}</div></li>`;}).join('');
  return `<section class="bk-card"><h3>Sửa nhà</h3><p class="bk-hint">Có ${xu(ready)} (tài khoản + ví).</p>${all}<ul class="rn-parts">${rows}</ul></section>`;
}
function itemRow(it,act){
  return `<li class="rn-shop-row"><span class="rn-shop-ico" aria-hidden="true">${it.emoji}</span><div class="grow"><b>${esc(it.name)}</b><small>Ấm cúng +${it.cozy}</small></div>${act}</li>`;
}
function decorPanel(v){
  const ready=v.ready;
  if(S.move){const x=[...v.items,...v.kho].find(i=>i.id===S.move),it=ITEM(x?.k);
    if(it)return `<section class="bk-card rn-pick"><h3>${it.emoji} Đặt ${low(it.name)}</h3><p class="bk-hint">Chọn chỗ trống ${it.spot==='wall'?'trên tường':'dưới sàn'}.</p><div class="bk-actions">${btn('Thôi','cancel',{},'ghost')}</div></section>`+khoCard(v);}
  if(S.sel){const x=v.items.find(i=>i.id===S.sel),it=ITEM(x?.k);
    if(it)return `<section class="bk-card rn-pick"><div class="rn-shop-row big"><span class="rn-shop-ico" aria-hidden="true">${it.emoji}</span><div class="grow"><b>${esc(it.name)}</b><small>${esc(roomName(x.r))} · ấm cúng +${it.cozy}</small></div></div>
      <div class="bk-actions">${btn('↔ Dời chỗ','pickup',{uid:x.id},'primary')}${btn('📦 Cất vào kho','store',{uid:x.id},'ghost')}${btn(`Bán lại · ${xu(it.sell)}`,'sell',{uid:x.id},'ghost danger')}${btn('Xong','cancel',{},'ghost')}</div></section>`;}
  if(S.pick){const p=S.pick,rm=roomOf(p.room),have=new Set(v.items.map(i=>i.k));
    const kho=v.kho.filter(x=>fitsSlot(ITEM(x.k),p.room,p.slot));
    const shop=C().items.filter(it=>fitsSlot(it,p.room,p.slot)).sort((a,b)=>a.price-b.price);
    const khoRows=kho.map(x=>itemRow(ITEM(x.k),btn('Đặt vào đây','put',{uid:x.id},'primary small'))).join('');
    const shopRows=shop.map(it=>`<li class="rn-shop-row${have.has(it.id)?' have':''}"><span class="rn-shop-ico" aria-hidden="true">${it.emoji}</span><div class="grow"><b>${esc(it.name)}</b><small>${have.has(it.id)?'Nhà đã có':`Ấm cúng +${it.cozy}`}</small></div>${btn(it.price>ready?`Thiếu ${xu(it.price-ready)}`:xu(it.price),'buy',{item:it.id},it.price>ready?'ghost small':'cream small',it.price>ready?' disabled':'')}</li>`).join('');
    return `<section class="bk-card rn-pick"><div class="rn-pick-head"><h3>${esc(rm.name)} · ${spotWord(p.slot)}</h3>${btn(icon('x',18),'cancel',{},'ghost small icon-btn','aria-label="Đóng"')}</div>
      ${khoRows?`<h4>📦 Trong kho</h4><ul class="rn-shop">${khoRows}</ul>`:''}<h4>🛒 Mua mới</h4><ul class="rn-shop">${shopRows}</ul></section>`;}
  return cozyCard(v)+khoCard(v);
}
function khoCard(v){
  if(!v.kho.length)return '';
  return `<section class="bk-card"><h3>📦 Kho · ${v.kho.length} món</h3><ul class="rn-shop">${v.kho.map(x=>{const it=ITEM(x.k);
    return itemRow(it,`<span class="rn-row-go">${btn('Đặt','pickup',{uid:x.id},S.move===x.id?'primary small':'ghost small')}${btn(xu(it.sell),'sell',{uid:x.id},'ghost small','aria-label="Bán lại"')}</span>`);}).join('')}</ul></section>`;
}
