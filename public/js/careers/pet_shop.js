/** Tiệm Thú Nhỏ Chú Út — the pet shop Nhã runs with the Chân Nhỏ rescue (server: game/careers/pet_shop.py).
 * Seven kinds of work: food advice, tank setup, selling / adopting out an animal, the care round of
 * the shop's own tanks and cages, returns, the lost-pet board and heavy deliveries by shipper. The
 * till is real: the player scans every line, closes the bill and builds the change from notes and
 * coins (till.js). Everything is decided on the server; the client shows it and sends one command
 * per tap. */
import {stepRows,nextHint,stepCta,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {cashPanel,changeStep,changePayload,tillActions} from './till.js';
import * as SF from './stage_fold.js';
import {linesSummary} from './tomorrow_kit.js';

const data=x=>x.room.data||{};
const cc=x=>x.cc||{};
const lower=s=>s?s[0].toLowerCase()+s.slice(1):'';
const price=(x,k)=>Number(x.room.life?.prices?.[k]??cc(x).prices?.[k]??0);
const unit=(x,t,k)=>Number(t.units?.[k]??price(x,k));
const pay=(p)=>JSON.stringify(p);
const cmdAttr=(x,command,payload)=>`data-command="${command}" data-payload="${x.esc(pay(payload))}"`;
const carBtn=(x,label,action,d={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-action="car:${action}"${Object.entries(d).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}${extra}>${label}</button>`;
const tile=(x,command,payload,inner,cls='',disabled=false)=>`<button type="button" class="ps-tile ${cls}" ${cmdAttr(x,command,payload)}${disabled?' disabled':''}>${inner}</button>`;
const have=(x,k)=>k in (cc(x).animals||{})?Number(data(x).animals?.[k]||0):k==='adopt'?1:Number(x.stock(k)||0);
const tillJob=t=>['food','tank','screen','ship'].includes(t.job);
const done=t=>['completed','cancelled','referred'].includes(t.status);
const inv=(x,what)=>({act:'inventory',label:`📦 Hết ${x.esc(what)}: mở Kho nhập thêm`});

/** Name and emoji of anything that can sit on the counter. */
function info(x,t,k){
  const c=cc(x),it=c.items?.[k];
  if(it)return {name:it.name,emoji:it.emoji,unit:it.unit};
  const a=c.animals?.[k];
  if(a){const co=coatOf(x,k,t?.coats?.[k]);return {name:co?`${a.name} ${lower(co.name)}`:a.name,emoji:a.emoji,unit:'con'};}
  if(k==='adopt'){const ad=c.adoptees?.[t?.needs?.pet];return {name:ad?`Nhận nuôi ${ad.name}`:(c.fee_names?.adopt||'Phí nhận nuôi'),emoji:'🏡',unit:'lần'};}
  return {name:c.fee_names?.[k]||k,emoji:'🧾',unit:''};
}

/* ------------------------------------------------------------ colours: coats and the shop's paint */
const coatsOf=(x,k)=>cc(x).coats?.[k]||[];
const coatOf=(x,k,id)=>id?coatsOf(x,k).find(c=>c.id===id):null;
const furOf=(x,a)=>a?(cc(x).fur?.[a.kind]||[]).find(c=>c.id===a.coat):null;
/** A colour dot: solid, or split in two for a patterned coat. */
const swatch=(x,c,cls='')=>c?`<span class="ps-sw ${cls}" style="--a:${x.esc(c.hex)};--b:${x.esc(c.hex2||c.hex)}" aria-hidden="true"></span>`:'';
/** "betta xanh dương" for each colour the customer asked for. */
function wish(x,n){
  return Object.entries(n.coat||{}).map(([k,id])=>{const co=coatOf(x,k,id);return co?`${swatch(x,co)} ${x.esc(lower(cc(x).animals?.[k]?.name||k))} ${x.esc(lower(co.name))}`:'';}).filter(Boolean).join(', ');
}
const wishLine=(x,n)=>{const w=wish(x,n);return w?`<small class="ps-wish">🎨 Khách dặn màu: ${w}</small>`:'';};
/** Colour chips under an animal on the counter: tap one to net that colour (rare colours cost more). */
function coatChips(t,x,k){
  if(!t.cart?.[k])return '';
  const cur=t.coats?.[k],a=cc(x).animals?.[k];
  return `<div class="ps-coats" role="group" aria-label="Màu ${x.esc(lower(a?.name||''))}">${coatsOf(x,k).map(co=>{const on=cur===co.id;
    return `<button type="button" class="ps-coat ${on?'on':''}" aria-pressed="${on}" ${cmdAttr(x,'ps_coat',{task:t.id,kind:k,coat:co.id})}${t.billed?' disabled':''}>${swatch(x,co)}<span>${x.esc(co.name)}</span>${co.extra?`<small>hiếm +${co.extra} xu</small>`:''}</button>`;}).join('')}</div>`;
}
/** Guide rows: one per colour the customer asked for. */
function coatSteps(t,x,where){
  return Object.entries(t.needs?.coat||{}).map(([k,id])=>{const co=coatOf(x,k,id),a=cc(x).animals?.[k],on=t.cart?.[k];
    return {ok:t.coats?.[k]?true:null,label:`Chọn màu khách dặn: ${lower(a?.name||k)} ${lower(co?.name||'')}`,note:t.coats?.[k]?coatOf(x,k,t.coats[k])?.name:'',
      go:{sel:on?'.ps-coats':where,label:`🎨 Chọn ${x.esc(lower(a?.name||''))} ${x.esc(lower(co?.name||''))}`},pulse:''};});
}
function palette(x){return data(x).palette||cc(x).themes?.[0]?.colors||{};}
/** The workbench root carries the shop's paint as CSS variables (sand and water keep their dark-mode values). */
function rootTag(x){
  const p=palette(x);
  return p.main?`<div class="career-job ps" style="--ps-teal:${x.esc(p.main)};--ps-teal-d:${x.esc(p.main_d)};--ps-coral:${x.esc(p.accent)}">`:'<div class="career-job ps">';
}
/** A little shopfront in the chosen paint: awning, sign in its ink, wall tiles, tanks and the door. */
function facade(x,th,ink){
  const k=th.colors||{},v=(n,c)=>`--${n}:${x.esc(c)}`;
  return `<div class="ps-facade" style="${[v('w',k.wall),v('wd',k.wall_d),v('ta',k.tile_a),v('tb',k.tile_b),v('m',k.main),v('md',k.main_d),v('ac',k.accent),v('al',k.accent_l),v('sd',k.sand),v('ink',ink||k.main_d)].join(';')}" aria-hidden="true">
    <div class="ps-f-awn"></div><div class="ps-f-sign"><span>🐾</span><b>TIỆM THÚ NHỎ</b></div>
    <div class="ps-f-wall"><i class="ps-f-tank"></i><i class="ps-f-door"></i><i class="ps-f-tank"></i></div></div>`;
}
function paintCard(x){
  const d=data(x),c=cc(x),themes=c.themes||[],owned=d.themes||['ngoc'],stage=Number(d.stage||0),money=Number(x.room.money||0);
  const pick=themes.find(v=>v.id===x.ui.theme)||themes.find(v=>v.id===d.theme)||themes[0];if(!pick)return '';
  const inks=c.inks||[],inkHex=inks.find(i=>i.id===d.ink)?.hex||'';
  const stName=s=>(c.stages||[])[s]?.name||'';
  const free=v=>owned.includes(v.id)||v.stage<=stage;
  const status=v=>v.id===d.theme?'Đang dùng':owned.includes(v.id)?'Đã mua':v.stage<=stage?'Miễn phí':`${v.cost} xu`;
  const tiles=themes.map(v=>{const k=v.colors,on=v.id===pick.id;
    return carBtn(x,`<span class="ps-pal" aria-hidden="true"><i style="background:${x.esc(k.wall)}"></i><i style="background:${x.esc(k.main)}"></i><i style="background:${x.esc(k.accent)}"></i></span><b>${x.esc(v.emoji)} ${x.esc(v.name)}</b><small>${x.esc(status(v))}</small>`,'theme',{theme:v.id},`ps-theme ${on?'on':''} ${v.id===d.theme?'cur':''}`,` aria-pressed="${on}"`);}).join('');
  const cost=free(pick)?0:pick.cost,cur=pick.id===d.theme;
  const note=cur?'Tiệm đang sơn màu này.':owned.includes(pick.id)?'Màu này tiệm đã mua, sơn lại không mất tiền.':!cost?`Tiệm đã tới “${stName(pick.stage)}”, màu này miễn phí.`
    :`Trả ${cost} xu từ quỹ tiệm${stName(pick.stage)?`, hoặc chờ tiệm tới “${stName(pick.stage)}” là miễn phí`:''}.${cost>money?` Quỹ còn ${money} xu, chưa đủ.`:''}`;
  const go=x.cmd(cur?'✓ Đang dùng màu này':`🎨 Sơn màu ${x.esc(lower(pick.name))} · ${cost?x.money(cost):'miễn phí'}`,'ps_paint',{theme:pick.id},'primary full',cur||cost>money);
  const inkRow=inks.map(i=>{const on=i.id===(d.ink||'auto');
    return `<button type="button" class="ps-ink ${on?'on':''}" aria-pressed="${on}" ${cmdAttr(x,'ps_ink',{ink:i.id})}${on?' disabled':''}><b style="color:${x.esc(i.hex||palette(x).main_d||'')}">Aa</b><span>${x.esc(i.name)}</span></button>`;}).join('');
  return `<section class="card ps-paint"><div class="row spread"><h4>🎨 Sơn lại tiệm</h4>${carBtn(x,'Đóng','paintClose',{},'ghost small')}</div>
    ${facade(x,pick,inkHex)}<div class="ps-themes">${tiles}</div><p class="small muted">${note}</p>${go}
    <h5>✒️ Màu chữ biển hiệu</h5><div class="ps-inks">${inkRow}</div></section>`;
}

/* ------------------------------------------------------------ top cards */
function introCard(x,force=false){
  const d=data(x),i=cc(x).intro;if(!i||(d.intro_seen&&!force))return '';
  const list=(title,rows)=>`<section><h4>${x.esc(title)}</h4><ul class="ps-icons">${rows.map(([e,s])=>`<li><span aria-hidden="true">${x.esc(e)}</span>${x.esc(s)}</li>`).join('')}</ul></section>`;
  const go=d.intro_seen?carBtn(x,'Đã hiểu','introClose',{},'primary full'):x.cmd('🐾 Vào tiệm thôi!','ps_intro',{},'primary full ps-intro-go');
  // Lead line, then the three lists folded (one tap opens them; ❔ on the day bar shows this card again).
  return `<article class="ps-intro card" role="dialog" aria-labelledby="ps-intro-title"><h3 id="ps-intro-title">🐠 ${x.esc(i.title)}</h3><p>${x.esc(i.lead)}</p>
    <details class="ps-intro-more"${force?' open':''}><summary>Xem thêm: công việc, người bạn gặp, khi nào được khen</summary><div class="ps-intro-grid">${list('Công việc gồm…',i.jobs)}${list('Bạn sẽ gặp…',i.meet)}${list('Được khen khi…',i.stars)}</div></details>${go}</article>`;
}
function dayBar(x,compact=false){
  const d=data(x),st=(cc(x).stages||[])[d.stage||0]||{},td=d.today||{};
  const chips=[td.sold?`🧾 ${td.sold} đơn`:'',td.good?`💚 ${td.good} trọn vẹn`:'',td.tips?`🎁 ${td.tips} xu cảm ơn`:'',td.loss?`<b class="ps-bad">💸 hụt ${td.loss} xu</b>`:''].filter(Boolean).join(' · ');
  // On a task: one line (the shop's stage text stays on the idle screen).
  const line=compact?chips:chips||x.esc(st.text||'');
  return `<div class="ps-day ${compact?'compact':''}"><span class="ps-day-ico" aria-hidden="true">🐾</span><div class="grow"><b>${x.esc(d.stage_name||st.name||'')}</b>${line?`<small>${line}</small>`:''}</div>
    ${carBtn(x,'🎨','paint',{},'ghost small ps-help',' aria-label="Sơn lại tiệm"')}${carBtn(x,'❔','intro',{},'ghost small ps-help',' aria-label="Giới thiệu nghề"')}</div>`;
}

/* ------------------------------------------------------------ the customer */
function ticket(t,x,pet=''){
  const who=x.npc(t.npc),c=cc(x),tag=`<span class="tag ps-tag">${x.esc(c.job_emoji?.[t.job]||'')} ${x.esc(c.jobs?.[t.job]||'')}</span>`;
  if(!t.known)return `<article class="card ps-ticket"><div class="row">${x.portrait(who,56)}<div class="grow"><div class="row spread wrap"><h3>${x.esc(who.display_name)}</h3>${tag}</div><p>${x.esc(t.opening)}</p></div></div>${x.cmd(t.job==='ship'?'📞 Nghe máy':'👂 Nghe khách nói','ask',{task:t.id},'primary full ps-ask')}</article>`;
  const n=t.needs||{};
  // The job's title is the sheet title already; the animal / item card sits inside the ticket as one row.
  return `<article class="card ps-ticket"><div class="row">${x.portrait(who,40)}<div class="grow"><div class="row spread wrap"><h3>${x.esc(who.display_name)}</h3>${tag}</div>
    <p class="ps-req">“${x.esc(n.request||t.opening)}”</p>
    <div class="patience" title="Kiên nhẫn"><div class="bar ${t.patience<50?'low':''}"><i style="width:${t.patience}%"></i></div><small>${t.patience}%</small></div></div></div>${pet}</article>`;
}
/** Question chips and the answers heard so far. */
const LATE=['till','cash','ship','cod','sign','kit','hand'];
function askPanel(t,x,title='❓ Hỏi han',now=null){
  const topics=cc(x).topics?.[t.job]||{},asked=t.asked||[],ans=t.answers||{};
  const chips=Object.entries(topics).map(([k,[e,q]])=>asked.includes(k)?'':x.cmd(`${x.esc(e)} ${x.esc(q)}`,'ps_ask',{task:t.id,topic:k},'small ghost ps-q')).join('');
  const heard=asked.map(k=>`<li><span aria-hidden="true">${x.esc(topics[k]?.[0]||'')}</span><div><small>${x.esc(topics[k]?.[1]||'')}</small><p>${x.esc(ans[k]||'')}</p></div></li>`).join('');
  // Past the questions (choosing, packing): the answers stay in view as short lines, the question in the tooltip.
  const brief=now&&now.size>0&&!now.has('ask')&&asked.length>0;
  const list=brief?`<ul class="ps-heard brief">${asked.map(k=>`<li title="${x.esc(topics[k]?.[1]||'')}"><span aria-hidden="true">${x.esc(topics[k]?.[0]||'')}</span><p>${x.esc(ans[k]||'')}</p></li>`).join('')}</ul>`:heard?`<ul class="ps-heard">${heard}</ul>`:'';
  const card=`<section class="card ps-ask-card${brief?' brief':''}"><h4>${title}</h4>${list}${chips?`<div class="ps-chips">${chips}</div>`:''}</section>`;
  // The answers guide the choice right after the questions, so the card stays open until the till.
  const late=now&&(LATE.some(k=>now.has(k))||(!!t.billed&&tillJob(t)));
  return late?SF.part(x,t.id,new Set(),'ask',title,card,{done:asked.length>0,sum:`đã hỏi ${asked.length}/${Object.keys(topics).length}`}):card;
}
/** The animal / item the job is about, as one row inside the ticket. */
function petRow(t,x){
  const c=cc(x),n=t.needs||{},row=(emo,name,sub,cls='')=>`<div class="ps-petcard in ${cls}"><span class="ps-pet" aria-hidden="true">${emo}</span><div><b>${name}</b>${sub}</div></div>`;
  if(t.job==='food')return row(x.esc(n.emoji||'🐾'),x.esc(n.pet||''),`<small>${x.esc(c.species?.[n.species]||'')} · cần ${n.qty||1} ${n.species==='tropical'||n.species==='goldfish'||n.species==='bird'||n.species==='hamster'?'gói':'túi'}</small>`);
  if(t.job==='tank'){const want=Object.entries(n.want||{}).map(([k,q])=>`${q} ${lower(c.animals[k]?.name||k)}`).join(', ');return row('🐠',x.esc(want),`<small>${x.esc(n.room||'')}</small>${wishLine(x,n)}`);}
  if(t.job==='screen'){const adopt=n.kind==='adopt',pet=adopt?c.adoptees?.[n.pet]:c.animals?.[n.pet],fur=adopt?furOf(x,pet):null;
    return row(x.esc(pet?.emoji||'🐾'),`${x.esc(pet?.name||'')}${fur?` ${swatch(x,fur)} <small>lông ${x.esc(lower(fur.name))}</small>`:''}`,`<small>${adopt?`${x.esc(pet?.text||'')} · phí nhận nuôi ${price(x,'adopt')} xu`:`${price(x,n.pet)} xu · tiệm còn ${have(x,n.pet)}`}</small>${adopt?'':wishLine(x,n)}`,adopt?'adopt':'');}
  if(t.job==='ret'){const i=c.items?.[n.item]||{};return row(x.esc(i.emoji||'🔁'),x.esc(i.name||''),`<small>giá ${price(x,n.item)} xu</small>`);}
  if(t.job==='ship')return row('📦',x.esc(n.address||''),`<small>${x.esc(n.request||'')}</small>`);
  return '';
}

/* ------------------------------------------------------------ the till */
function tillPanel(t,x,now=new Set()){
  const keys=[...new Set([...Object.keys(t.cart||{}),...Object.keys(t.bill||{})])],billed=!!t.billed;
  const rows=keys.map(k=>{
    const i=info(x,t,k),want=t.cart?.[k]||0,got=t.bill?.[k]||0,u=unit(x,t,k),st=got===want?'ok':got>want?'over':'';
    const ctl=billed?'':`${got?`<button type="button" class="ps-step" ${cmdAttr(x,'ps_void',{task:t.id,key:k})} aria-label="Bớt một ${x.esc(lower(i.name))}">−</button>`:''}<button type="button" class="ps-step ps-scan" data-key="${x.esc(k)}" ${cmdAttr(x,'ps_scan',{task:t.id,key:k})} aria-label="Quét ${x.esc(lower(i.name))}">📟</button>`;
    return `<li class="${st}"><span class="ps-li-name"><span><span aria-hidden="true">${x.esc(i.emoji)}</span> ${x.esc(i.name)}</span><small>quầy ${want} · ${u} xu/${x.esc(i.unit||'món')}</small></span>
      <span class="ps-li-q">×${got}</span><b class="ps-li-sum">${got*u}</b><span class="ps-li-ctl">${ctl}</span></li>`;
  }).join('');
  const fee=t.job==='ship'&&t.fee?`<li class="fee"><span class="ps-li-name"><span><span aria-hidden="true">🛵</span> Phí ship</span></span><span class="ps-li-q"></span><b class="ps-li-sum">${t.fee}</b><span class="ps-li-ctl"></span></li>`:'';
  const total=Number(t.bill_total||0);
  const can=t.job!=='ship'?(t.cash==null||(t.cash.outcome==null&&!t.cash.asked)):t.work?.cod==null;
  const act=billed?(can?x.cmd('↺ Quét lại','ps_rescan',{task:t.id},'small ghost'):''):x.cmd(`🧾 Chốt hóa đơn · ${x.money(total)}`,'ps_total',{task:t.id},'small ps-close',!total);
  return `<section class="card ps-till"><div class="row spread"><h4>📟 Máy tính tiền</h4>${billed?'<span class="tag green">Đã chốt</span>':''}</div>
    <ul class="ps-receipt">${rows||'<li class="muted"><span class="ps-li-name">Quầy còn trống.</span></li>'}${fee}</ul>
    <div class="ps-total"><span>Cộng hóa đơn${t.job==='ship'&&t.fee?' + ship':''}</span><b>${x.money(total+(t.job==='ship'?Number(t.fee||0):0))}</b></div>
    <div class="ps-row">${act}</div></section>`;
}
/** The till: open while scanning; a line before that and once the bill is closed (the change panel says the total). */
function tillPart(t,x,now){
  const n=Object.values(t.bill||{}).reduce((a,v)=>a+v,0),total=Number(t.bill_total||0)+(t.job==='ship'?Number(t.fee||0):0);
  return SF.part(x,t.id,now,'till','📟 Máy tính tiền',tillPanel(t,x,now),{done:!!t.billed,sum:t.billed?`đã chốt ${x.money(total)}`:n?`đã quét ${n} món · ${x.money(total)}`:'quét từng món trên quầy'});
}
/** Guide rows for the till: scan what is on the counter, void what is not, close the bill, the change. */
function tillSteps(t,x){
  const rows=[],id=t.id;
  if(!t.billed){
    for(const [k,q] of Object.entries(t.cart||{})){
      const got=t.bill?.[k]||0,i=info(x,t,k);
      if(got<q)rows.push({stage:'till',ok:null,label:`Quét ${lower(i.name)} (${got}/${q})`,go:{cmd:'ps_scan',payload:{task:id,key:k},label:`📟 Quét ${x.esc(lower(i.name))} (${got+1}/${q})`}});
      else if(got>q)rows.push({stage:'till',ok:false,label:`${i.name}: quét dư ${got-q}`,go:{cmd:'ps_void',payload:{task:id,key:k},label:`− Bớt một ${x.esc(lower(i.name))}`}});
    }
    for(const [k,got] of Object.entries(t.bill||{}))if(!(k in (t.cart||{})))rows.push({stage:'till',ok:false,label:`${info(x,t,k).name}: không có trên quầy`,go:{cmd:'ps_void',payload:{task:id,key:k},label:`− Bỏ ${x.esc(lower(info(x,t,k).name))} khỏi hóa đơn`}});
    if(Object.keys(t.cart||{}).length)rows.push({stage:'till',ok:null,label:'Chốt hóa đơn',go:{cmd:'ps_total',payload:{task:id},label:`🧾 Chốt hóa đơn · ${t.bill_total||0} xu`}});
    return rows;
  }
  const s=changeStep(x,id,t.cash);if(s)rows.push({...s,stage:'cash'});
  return rows;
}

/* ------------------------------------------------------------ food */
function foodPanel(t,x,now=new Set()){
  const c=cc(x),n=t.needs||{},foods=Object.keys(c.foods||{});
  const groups={};for(const k of foods){const g=c.items[k]?.group||'';(groups[g]??=[]).push(k);}
  const shelf=Object.entries(groups).map(([g,ks])=>`<h5>${x.esc(g)}</h5><div class="ps-grid">${ks.map(k=>{const i=c.items[k],f=c.foods[k],q=x.stock(k),on=t.cart?.[k];
    return tile(x,'ps_food',{task:t.id,item:k},`<span class="ps-bag" aria-hidden="true">${x.esc(i.emoji)}</span><b>${x.esc(i.name)}</b><small>${x.esc(f.label)}</small><em>${price(x,k)} xu · còn ${q}</em>`,`${on?'selected':''} ps-food`,q<(n.qty||1)||t.billed);}).join('')}</div>`).join('');
  const g=t.grab;
  const grab=g?`<section class="card ps-grab"><h4>🧺 Khách lấy trong rổ giảm giá</h4><p>${g.qty} × ${x.esc(c.items[g.item]?.name||'')}</p>
    ${g.label?`<p class="notice amber small">📅 ${x.esc(g.label)}</p>`:''}
    <div class="ps-row">${t.work?.dated?'':x.cmd('📅 Xem hạn từng lon','ps_date',{task:t.id},'small')}${t.work?.swapped?'<span class="tag green">✓ Đã xử lý mấy lon trong rổ</span>':`${x.cmd('🔁 Đổi lon mới trên kệ','ps_swap',{task:t.id},'small ghost',t.billed)}${x.cmd('✋ Bỏ ra khỏi quầy','ps_cart',{task:t.id,key:g.item,qty:0},'small ghost',t.billed)}`}</div></section>`:'';
  const main=Object.keys(t.cart||{}).find(k=>k in (c.foods||{}));
  return `${askPanel(t,x,'❓ Hỏi về bé',now)}${grab?SF.part(x,t.id,now,'grab','🧺 Khách lấy trong rổ giảm giá',grab,{done:!!t.work?.swapped,sum:t.work?.swapped?'đã xử lý':''}):''}
    ${SF.part(x,t.id,now,'shelf','🥣 Kệ thức ăn',`<section class="card ps-shelf"><h4>🥣 Kệ thức ăn <small class="muted">đọc nhãn: loài · tuổi · cỡ · vị</small></h4>${shelf}</section>`,{done:!!main,sum:main?x.esc(info(x,t,main).name):''})}`;
}
function foodSteps(t,x){
  const n=t.needs||{},asked=t.asked||[],rows=[],id=t.id;
  const next=['age','allergy','weight','now'].find(k=>!asked.includes(k)),topics=cc(x).topics?.food||{};
  rows.push({stage:'ask',ok:asked.includes('age')&&asked.includes('allergy')?true:null,label:'Hỏi tuổi, cân nặng, dị ứng của bé',note:`đã hỏi ${asked.length}/4`,go:next?{cmd:'ps_ask',payload:{task:id,topic:next},label:`${topics[next]?.[0]||'❓'} ${x.esc(topics[next]?.[1]||'')}`}:null});
  const main=Object.keys(t.cart||{}).find(k=>k in (cc(x).foods||{}));
  rows.push({stage:'shelf',ok:main?true:null,label:'Chọn bao hạt hợp với bé',note:main?info(x,t,main).name:'',go:{sel:'.ps-shelf',label:'🥣 Đọc nhãn, chọn bao hạt'},pulse:''});
  const g=t.grab;
  if(g){
    rows.push({stage:'grab',ok:t.work?.dated?true:null,label:'Xem hạn mấy lon khách lấy trong rổ',go:{cmd:'ps_date',payload:{task:id},label:'📅 Xem hạn mấy lon trong rổ'}});
    if(t.work?.dated)rows.push({stage:'grab',ok:t.work.swapped?true:null,label:'Xử lý mấy lon trong rổ',go:{sel:'.ps-grab',label:'🧺 Đổi lon mới hoặc bỏ ra'},pulse:''});
  }
  return rows;
}

/* ------------------------------------------------------------ tank */
function tankPanel(t,x,now=new Set()){
  const c=cc(x),n=t.needs||{},load=t.load||{litres:0,size:0},id=t.id,lock=t.billed;
  const want=Object.entries(n.want||{}).map(([k,q])=>`${q} ${lower(c.animals[k]?.name||k)}`).join(', ');
  const tanks=Object.entries(c.tanks||{}).map(([k,l])=>tile(x,'ps_tank',{task:id,size:k},`<span class="ps-glass" aria-hidden="true"><i></i></span><b>${l} lít</b><small>${price(x,k)} xu · còn ${x.stock(k)}</small>`,`ps-tanktile ${t.cart?.[k]?'selected':''}`,!x.stock(k)||lock)).join('');
  const fish=(c.fish||[]).map(k=>{const a=c.animals[k],q=t.cart?.[k]||0;
    const dots=(data(x).coats?.[k]||[]).map(id=>swatch(x,coatOf(x,k,id),'sm')).join('');
    return `<div class="ps-stepper ${q?'on':''}"><span class="ps-st-ico" aria-hidden="true">${x.esc(a.emoji)}</span><div class="grow"><b>${x.esc(a.name)} <span class="ps-dots">${dots}</span></b><small>${x.esc(a.note||'')} · ${a.litres} L/con · ${price(x,k)} xu</small></div>
      <button type="button" class="ps-step" ${cmdAttr(x,'ps_cart',{task:id,key:k,qty:Math.max(0,q-1)})}${!q||lock?' disabled':''} aria-label="Bớt ${x.esc(lower(a.name))}">−</button><b class="ps-q">${q}</b>
      <button type="button" class="ps-step" ${cmdAttr(x,'ps_cart',{task:id,key:k,qty:q+1})}${q>=20||have(x,k)<=q||lock?' disabled':''} aria-label="Thêm ${x.esc(lower(a.name))}">+</button></div>${coatChips(t,x,k)}`;}).join('');
  const gear=['filter','heater','conditioner'].map(k=>{const i=c.items[k],q=t.cart?.[k]||0;
    return tile(x,'ps_cart',{task:id,key:k,qty:q?0:1},`<span class="ps-bag" aria-hidden="true">${x.esc(i.emoji)}</span><b>${x.esc(i.name)}</b><small>${price(x,k)} xu${q?' · ✓ trên quầy':''}</small>`,q?'selected':'',lock||(!q&&!x.stock(k)));}).join('');
  const pct=load.size?Math.min(100,load.litres/load.size*100):0,over=load.size&&load.litres>load.size;
  const tips=Object.entries(c.tips||{}).map(([k,[,s]])=>{const on=(t.work?.advice||[]).includes(k),next=on?(t.work.advice||[]).filter(v=>v!==k):[...(t.work?.advice||[]),k];
    return `<button type="button" class="ps-tip ${on?'on':''}" aria-pressed="${on}" ${cmdAttr(x,'ps_advice',{task:id,tips:next})}><span aria-hidden="true">${on?'☑':'☐'}</span>${x.esc(s)}</button>`;}).join('');
  const cart=t.cart||{},size=Object.keys(c.tanks||{}).find(k=>cart[k]),fishIn=(c.fish||[]).filter(k=>cart[k]),gearIn=['filter','heater','conditioner'].filter(k=>cart[k]),adv=(t.work?.advice||[]).length;
  const P=(key,title,body,done,sum)=>SF.part(x,t.id,now,key,title,body,{done,sum});
  return P('tanks','🫙 Chọn bể',`<section class="card ps-tanks"><h4>🫙 Chọn bể</h4><div class="ps-grid three">${tanks}</div>
      <div class="ps-load ${over?'over':''}"><span>Nước cá cần</span><span class="ps-meter"><i style="width:${pct.toFixed(0)}%"></i></span><b>${load.litres}/${load.size||'?'} L</b></div></section>`,!!size,size?`${c.tanks[size]} lít · nước cá cần ${load.litres}/${load.size||'?'} L`:'')
    +P('fish','🐟 Cá thả bể',`<section class="card ps-fish"><h4>🐟 Cá thả bể</h4>${fish}</section>`,fishIn.length>0,fishIn.map(k=>`${cart[k]} ${x.esc(lower(c.animals[k]?.name||k))}`).join(', '))
    +P('gear','🌀 Đồ cho bể',`<section class="card ps-gear"><h4>🌀 Đồ cho bể</h4><div class="ps-grid three">${gear}</div></section>`,gearIn.length>0,gearIn.map(k=>x.esc(c.items[k]?.name||k)).join(', '))
    +P('tips','🗒️ Dặn khách',`<section class="card ps-tips"><h4>🗒️ Dặn khách</h4><div class="ps-tiplist">${tips}</div></section>`,adv>0,adv?`${adv} lời dặn`:'');
}
function tankSteps(t,x){
  const c=cc(x),rows=[],cart=t.cart||{};
  const size=Object.keys(c.tanks||{}).find(k=>cart[k]);
  rows.push({stage:'tanks',ok:size?true:null,label:'Chọn bể đủ nước cho cả đàn',go:{sel:'.ps-tanks',label:'🫙 Chọn cỡ bể'},pulse:''});
  const fish=(c.fish||[]).some(k=>cart[k]);
  rows.push({stage:'fish',ok:fish?true:null,label:'Chọn cá thả bể (cá hợp nhau)',go:{sel:'.ps-fish',label:'🐟 Chọn cá thả bể'},pulse:''});
  rows.push(...coatSteps(t,x,'.ps-fish').map(r=>({...r,stage:'fish'})));
  rows.push({stage:'gear',ok:['filter','heater','conditioner'].some(k=>cart[k])?true:null,label:'Đồ cho bể: lọc, sưởi, khử clo',go:{sel:'.ps-gear',label:'🌀 Chọn đồ cho bể'},pulse:''});
  rows.push({stage:'tips',ok:(t.work?.advice||[]).length?true:null,label:'Dặn khách cách thả cá, thay nước, cho ăn',go:{sel:'.ps-tips',label:'🗒️ Dặn khách cách chăm'},pulse:''});
  return rows;
}

/* ------------------------------------------------------------ screen: sale or adoption */
function screenPanel(t,x,now=new Set()){
  const c=cc(x),n=t.needs||{},id=t.id,w=t.work||{},adopt=n.kind==='adopt';
  const pet=adopt?c.adoptees?.[n.pet]:c.animals?.[n.pet];
  const fur=adopt?furOf(x,pet):null;
  let body='';
  if(!w.verdict){
    body=`<section class="card ps-verdict"><h4>🤔 Quyết định</h4><p class="small muted">Chưa hợp thì hẹn lại hoặc từ chối nhẹ nhàng. Thú khỏe là trên hết.</p><div class="ps-opts">
      ${x.cmd(`💚 ${x.esc(c.verdicts?.sell||'')}`,'ps_verdict',{task:id,verdict:'sell'},'ps-opt')}
      ${x.confirmCmd(`⏳ ${x.esc(c.verdicts?.later||'')}`,'ps_verdict',{task:id,verdict:'later'},'Hẹn khách quay lại sau? Việc này sẽ khép lại.','ps-opt')}
      ${x.confirmCmd(`🙅 ${x.esc(c.verdicts?.refuse||'')}`,'ps_verdict',{task:id,verdict:'refuse'},'Từ chối nhẹ nhàng và gợi ý cách khác? Việc này sẽ khép lại.','ps-opt')}</div></section>`;
  }else if(adopt){
    const sel=x.ui.sign?.[id]||w.signed||[];
    const checks=Object.entries(c.signs||{}).map(([k,s])=>{const on=sel.includes(k);return carBtn(x,`<span aria-hidden="true">${on?'☑':'☐'}</span>${x.esc(s)}`,'sign',{task:id,key:k},`ps-tip ${on?'on':''}`,` aria-pressed="${on}"${t.billed?' disabled':''}`);}).join('');
    body=SF.part(x,id,now,'sign','📝 Giấy nhận nuôi',`<section class="card ps-sign"><h4>📝 Giấy nhận nuôi với nhóm Chân Nhỏ</h4><div class="ps-tiplist">${checks}</div><div class="ps-row">${carBtn(x,w.signed?.length?'✍️ Ký lại giấy':'✍️ Ký giấy nhận nuôi','signGo',{task:id},'small',t.billed?' disabled':'')}</div></section>`,{done:!!w.signed?.length,sum:w.signed?.length?`đã ký ${w.signed.length} mục`:''})
      +kitPart(t,x,now,['collar','leash','litter','toy','cat_kitten','dog_puppy']);
  }else{
    const k=n.pet,on=t.cart?.[k]||0;
    const co=coatOf(x,k,t.coats?.[k]);
    body=SF.part(x,id,now,'hand','🤲 Giao bé',`<section class="card ps-hand"><h4>🤲 Giao bé</h4><div class="ps-row">${on?`<span class="tag green">✓ ${x.esc(pet?.name||'')} đã trên quầy</span>`:x.cmd(`${x.esc(pet?.emoji||'')} Đặt ${x.esc(lower(pet?.name||''))} lên quầy`,'ps_cart',{task:id,key:k,qty:1},'small',t.billed||!have(x,k))}</div>${on?`<p class="small muted">Vớt bé màu nào?</p>${coatChips(t,x,k)}`:''}</section>`,{done:!!on&&(!n.coat?.[k]||!!t.coats?.[k]),sum:on?`${x.esc(pet?.name||'')} đã trên quầy${co?` · ${x.esc(lower(co.name))}`:''}`:''})
      +kitPart(t,x,now,k==='hamster'?['cage_hamster','hamster_food','bedding','toy','cage_bird']:['cage_bird','bird_seed','toy','cage_hamster','bedding']);
  }
  return `${askPanel(t,x,'❓ Hỏi người muốn nuôi',now)}${body}`;
}
function kitPart(t,x,now,keys){
  const got=keys.filter(k=>t.cart?.[k]);
  return SF.part(x,t.id,now,'kit','🎒 Đồ dùng mang về',kitShelf(t,x,keys),{done:got.length>0,sum:got.map(k=>x.esc(cc(x).items[k]?.name||k)).join(', ')});
}
function kitShelf(t,x,keys){
  const c=cc(x),id=t.id;
  return `<section class="card ps-kit"><h4>🎒 Đồ dùng mang về</h4><div class="ps-grid three">${keys.map(k=>{const i=c.items[k],q=t.cart?.[k]||0;
    return tile(x,'ps_cart',{task:id,key:k,qty:q?0:1},`<span class="ps-bag" aria-hidden="true">${x.esc(i.emoji)}</span><b>${x.esc(i.name)}</b><small>${price(x,k)} xu${q?' · ✓':''}</small>`,q?'selected':'',t.billed||(!q&&!x.stock(k)));}).join('')}</div></section>`;
}
function screenSteps(t,x){
  const n=t.needs||{},w=t.work||{},asked=t.asked||[],rows=[],id=t.id,topics=cc(x).topics?.screen||{};
  const next=Object.keys(topics).find(k=>!asked.includes(k));
  rows.push({stage:'ask',ok:asked.length>=4?true:null,label:'Hỏi han người muốn nuôi',note:`đã hỏi ${asked.length}/${Object.keys(topics).length}`,go:next&&!w.verdict?{cmd:'ps_ask',payload:{task:id,topic:next},label:`${topics[next][0]} ${x.esc(topics[next][1])}`}:null});
  rows.push({stage:'verdict',ok:w.verdict?true:null,label:'Quyết định có giao bé không',go:w.verdict?null:{sel:'.ps-verdict',label:'🤔 Quyết định giao bé hay chưa'},pulse:''});
  if(w.verdict==='sell'){
    if(n.kind==='adopt')rows.push({stage:'sign',ok:(w.signed||[]).length?true:null,label:'Ký giấy nhận nuôi',go:{sel:'.ps-sign',label:'📝 Làm giấy nhận nuôi'},pulse:''});
    else{
      rows.push({stage:'hand',ok:t.cart?.[n.pet]?true:null,label:'Đặt bé lên quầy',go:have(x,n.pet)?{cmd:'ps_cart',payload:{task:id,key:n.pet,qty:1},label:'🤲 Đặt bé lên quầy'}:null});
      rows.push(...coatSteps(t,x,'.ps-hand').map(r=>({...r,stage:'hand'})));
      rows.push({stage:'kit',ok:Object.keys(t.cart||{}).some(k=>k!==n.pet)?true:null,label:'Đồ dùng bé cần ở nhà mới',go:{sel:'.ps-kit',label:'🎒 Chọn đồ dùng mang về'},pulse:''});
    }
  }
  return rows;
}

/* ------------------------------------------------------------ care round */
function penPick(t,x){const pens=t.pens||[];const p=x.ui.pen?.[t.id];return pens.some(q=>q.id===p)?p:pens[0]?.id;}
function carePanel(t,x){
  const c=cc(x),w=t.work||{},id=t.id,sel=penPick(t,x),d=data(x);
  const tabs=(t.pens||[]).map(p=>{const pen=c.pens[p.id],fish=pen.kind==='fish',hp=d.pens?.[p.id]?.health??90;
    const marks=[w.fed?.[p.id]?'🍽️':'',w.cleaned?.[p.id]?'🧽':'',p.temp!=null?`🌡️${p.temp}°`:'',(w.isolated||[]).includes(p.id)?'🚑':''].filter(Boolean).join(' ');
    return `<button type="button" class="ps-pen ${fish?'fish':'cage'} ${p.id===sel?'on':''} ${p.dirty&&!w.cleaned?.[p.id]?'dirty':''}" data-action="car:pen" data-task="${x.esc(id)}" data-pen="${x.esc(p.id)}" aria-pressed="${p.id===sel}">
      <span class="ps-pen-ico" aria-hidden="true">${x.esc(pen.emoji)}</span><b>${x.esc(pen.name)}</b><small>${marks||(p.dirty?'bẩn':'&nbsp;')}</small><i class="ps-hp" style="width:${hp}%"></i></button>`;}).join('');
  const p=(t.pens||[]).find(q=>q.id===sel);let tools='';
  if(p){
    const pen=c.pens[p.id],fish=pen.kind==='fish',pl={task:id,pen:p.id};
    const fed=w.fed?.[p.id],cl=w.cleaned?.[p.id];
    tools=`<section class="card ps-tools"><h4>${x.esc(pen.emoji)} ${x.esc(pen.name)}</h4>
      ${p.sign?`<p class="ps-sign-line">👀 ${x.esc(p.sign)}</p>`:''}${p.temp!=null?`<p class="ps-sign-line">🌡️ Nước ${p.temp}°C</p>`:''}
      <h5>🍽️ Cho ăn</h5><div class="ps-opts row3">${Object.entries(c.portions||{}).map(([k,s])=>x.cmd(`${fed===k?'✓ ':''}${x.esc(s)}`,'ps_feed',{...pl,portion:k},`ps-opt small ${fed===k?'on':''}`,!!fed)).join('')}</div>
      <h5>🧽 Dọn ${fish?'bể':'chuồng'}</h5><div class="ps-opts row2">${Object.entries(c.cleans||{}).map(([k,s])=>x.cmd(`${cl===k?'✓ ':''}${x.esc(s)}`,'ps_clean',{...pl,how:k},`ps-opt small ${cl===k?'on':''}`,!!cl)).join('')}</div>
      <h5>🩺 Kiểm tra</h5><div class="ps-row">${fish?x.cmd('🌡️ Đo nhiệt','ps_temp',pl,'small ghost',(w.read||[]).includes(p.id)):''}${fish?x.cmd('🔥 Bật lại sưởi','ps_heat',pl,'small ghost',(w.heated||[]).includes(p.id)):''}
        ${x.cmd('👀 Soi kỹ từng bé','ps_look',pl,'small ghost',(w.looked||[]).includes(p.id))}${x.confirmCmd('🚑 Cách ly bé ốm','ps_isolate',pl,`Chuyển bé ở ${lower(pen.name)} sang ${fish?'bể':'lồng'} cách ly?`,'small ghost',(w.isolated||[]).includes(p.id))}</div></section>`;
  }
  return `<section class="card ps-pens-card"><h4>🧺 Vòng chăm sáng nay</h4><div class="ps-pens">${tabs}</div></section>${tools}`;
}
function careSteps(t,x){
  const c=cc(x),w=t.work||{},rows=[],pens=t.pens||[],id=t.id,pick=pen=>({act:'car:pen',data:{task:id,pen}});
  const unfed=pens.filter(p=>!w.fed?.[p.id]);
  rows.push({ok:unfed.length?null:true,label:'Cho từng bé ăn đúng khẩu phần',note:`${pens.length-unfed.length}/${pens.length}`,go:unfed.length?{...pick(unfed[0].id),label:`🍽️ Cho ${x.esc(lower(c.pens[unfed[0].id].name))} ăn`}:null,pulse:''});
  const dirty=pens.filter(p=>p.dirty&&!w.cleaned?.[p.id]);
  if(pens.some(p=>p.dirty))rows.push({ok:dirty.length?null:true,label:'Dọn chỗ bẩn',go:dirty.length?{...pick(dirty[0].id),label:`🧽 Dọn ${x.esc(lower(c.pens[dirty[0].id].name))}`}:null,pulse:''});
  const unread=pens.filter(p=>c.pens[p.id].kind==='fish'&&p.temp==null);
  rows.push({ok:unread.length?null:true,label:'Đo nhiệt từng bể cá',go:unread.length?{cmd:'ps_temp',payload:{task:id,pen:unread[0].id},label:`🌡️ Đo nhiệt ${x.esc(lower(c.pens[unread[0].id].name))}`}:null});
  const unseen=pens.filter(p=>!(w.looked||[]).includes(p.id));
  rows.push({ok:unseen.length?null:true,label:'Soi kỹ từng bé',go:unseen.length?{cmd:'ps_look',payload:{task:id,pen:unseen[0].id},label:`👀 Soi ${x.esc(lower(c.pens[unseen[0].id].name))}`}:null});
  for(const p of pens){
    const pen=c.pens[p.id],ok=c.temp_ok?.[pen.water];
    if(p.temp!=null&&ok&&(p.temp<ok[0]||p.temp>ok[1]))rows.push({ok:null,label:`${pen.name}: nước ${p.temp}°C`,go:{...pick(p.id),label:`🌡️ Xem lại ${x.esc(lower(pen.name))}`},pulse:''});
  }
  return rows;
}

/* ------------------------------------------------------------ returns */
function retPanel(t,x,now=new Set()){
  const c=cc(x),n=t.needs||{},i=c.items?.[n.item]||{},id=t.id;
  return `<details class="card ps-policy"><summary>📋 Quy định đổi trả</summary><p>${x.esc(c.policy||'')}</p></details>
    ${askPanel(t,x,'🔍 Kiểm tra món khách mang trả')}
    <section class="card ps-decide"><h4>⚖️ Quyết định</h4><div class="ps-opts">${Object.entries(c.decisions||{}).map(([k,s])=>x.confirmCmd(`${k==='refund'?'💵':k==='exchange'?'🔁':'🙅'} ${x.esc(s)}`,'ps_return',{task:id,decision:k},`${s}? Việc này sẽ khép lại.`,'ps-opt')).join('')}</div></section>`;
}
function retSteps(t,x){
  const asked=t.asked||[],topics=cc(x).topics?.ret||{},next=Object.keys(topics).find(k=>!asked.includes(k));
  return [{ok:asked.length>=3?true:null,label:'Xem hóa đơn, seal, mã lô, hạn, lỗi',note:`đã xem ${asked.length}/${Object.keys(topics).length}`,go:next?{cmd:'ps_ask',payload:{task:t.id,topic:next},label:`${topics[next][0]} ${x.esc(topics[next][1])}`}:null},
    {ok:null,label:'Quyết định theo quy định',go:{sel:'.ps-decide',label:'⚖️ Quyết định đổi trả'},pulse:''}];
}

/* ------------------------------------------------------------ lost-pet board */
function lostPanel(t,x,now=new Set()){
  const c=cc(x),n=t.needs||{},w=t.work||{},id=t.id;
  const sel=x.ui.notice?.[id]||w.notice||[];
  const fields=Object.entries(c.fields||{}).map(([k,[e,s]])=>{const on=sel.includes(k);return carBtn(x,`<span aria-hidden="true">${on?'☑':'☐'}</span>${x.esc(e)} ${x.esc(s)}`,'field',{task:id,key:k},`ps-tip ${on?'on':''}`,` aria-pressed="${on}"${w.pinned?' disabled':''}`);}).join('');
  const paper=(w.notice||[]).length?`<div class="ps-paper"><b>TÌM ${x.esc((n.pet||'').toUpperCase())} ${x.esc(n.emoji||'')}</b><ul>${w.notice.map(k=>`<li>${x.esc(c.fields[k][0])} ${x.esc(c.fields[k][1])}</li>`).join('')}</ul></div>`:'';
  const calls=(t.calls||[]).map(k=>{const st=k.state;
    const btns=st==='sent'||st==='blocked'?`<span class="tag ${st==='sent'?'green':''}">${st==='sent'?'🏃 Đã báo chủ đi gặp':'📵 Đã gác máy'}</span>`:
      `${st?'':x.cmd('🤫 Hỏi dấu riêng','ps_call',{task:id,call:k.id,move:'check'},'small ghost')}${x.confirmCmd('🏃 Báo chủ đi gặp','ps_call',{task:id,call:k.id,move:'send'},'Báo chủ nuôi liên lạc với người này?','small ghost')}${x.confirmCmd('📵 Cảm ơn, gác máy','ps_call',{task:id,call:k.id,move:'block'},'Cảm ơn rồi gác máy?','small ghost')}`;
    return `<li class="ps-call" data-call="${x.esc(k.id)}"><p>📞 ${x.esc(k.text)}</p>${k.check?`<p class="ps-sign-line">${x.esc(k.check)}</p>`:''}<div class="ps-row">${btns}</div></li>`;}).join('');
  return `${askPanel(t,x,'❓ Hỏi chủ nuôi')}
    <section class="card ps-notice"><h4>📝 Tờ tìm thú</h4>${w.pinned?'':`<p class="small muted">Chọn dòng in lên tờ giấy dán ngoài bảng (ai đi ngang cũng đọc được).</p><div class="ps-tiplist">${fields}</div>
      <div class="ps-row">${carBtn(x,(w.notice||[]).length?'✏️ Viết lại tờ':'✏️ Viết tờ tìm thú','noticeGo',{task:id},'small')}${(w.notice||[]).length?x.cmd('📌 Dán lên bảng','ps_pin',{task:id},'small primary'):''}</div>`}${paper}</section>
    ${w.pinned?`<section class="card ps-calls"><h4>☎️ Điện thoại tiệm reo</h4><ul class="ps-calllist">${calls}</ul></section>`:''}`;
}
function lostSteps(t,x){
  const w=t.work||{},asked=t.asked||[],topics=cc(x).topics?.lost||{},id=t.id,rows=[];
  const next=Object.keys(topics).find(k=>!asked.includes(k));
  rows.push({ok:asked.length>=4?true:null,label:'Hỏi chủ nuôi về bé',note:`đã hỏi ${asked.length}/${Object.keys(topics).length}`,go:next&&!w.pinned?{cmd:'ps_ask',payload:{task:id,topic:next},label:`${topics[next][0]} ${x.esc(topics[next][1])}`}:null});
  rows.push({stage:'notice',ok:(w.notice||[]).length?true:null,label:'Viết tờ tìm thú',go:w.pinned?null:{sel:'.ps-notice',label:'📝 Viết tờ tìm thú'},pulse:''});
  if((w.notice||[]).length)rows.push({ok:w.pinned?true:null,label:'Dán tờ lên bảng',go:{cmd:'ps_pin',payload:{task:id},label:'📌 Dán lên bảng'}});
  for(const k of t.calls||[])if(k.state!=='sent'&&k.state!=='blocked'&&!w.found)rows.push({stage:'calls',ok:null,label:'Trả lời một cuộc gọi',go:{sel:`.ps-call[data-call="${k.id}"]`,label:'☎️ Nghe cuộc gọi tới'},pulse:''});
  return rows;
}

/* ------------------------------------------------------------ heavy delivery */
function shipPanel(t,x,now=new Set()){
  const c=cc(x),n=t.needs||{},w=t.work||{},id=t.id,lock=t.billed;
  const order=Object.entries(n.order||{}).map(([k,q])=>{const i=c.items[k],have=t.cart?.[k]||0;
    return `<div class="ps-stepper ${have===q?'on':''}"><span class="ps-st-ico" aria-hidden="true">${x.esc(i.emoji)}</span><div class="grow"><b>${x.esc(i.name)}</b><small>đơn ${q} ${x.esc(i.unit)} · ${(c.kg10?.[k]||0)/10} kg/món · kho còn ${x.stock(k)}</small></div>
      <button type="button" class="ps-step" ${cmdAttr(x,'ps_cart',{task:id,key:k,qty:Math.max(0,have-1)})}${!have||lock?' disabled':''} aria-label="Bớt">−</button><b class="ps-q">${have}</b>
      <button type="button" class="ps-step" ${cmdAttr(x,'ps_cart',{task:id,key:k,qty:have+1})}${have>=20||x.stock(k)<=have||lock?' disabled':''} aria-label="Thêm">+</button></div>`;}).join('');
  const kg=(t.kg10||0)/10,bike=(c.bike_max10||200)/10;
  const ships=Object.entries(c.shippers||{}).map(([k,[e,s]])=>tile(x,'ps_shipper',{task:id,kind:k},`<span class="ps-bag" aria-hidden="true">${x.esc(e)}</span><b>${k==='bike'?'Xe máy':'Xe tải nhỏ'} · ${price(x,'ship_'+k)} xu</b><small>${x.esc(s)}</small>`,w.shipper===k?'selected':'',w.cod!=null)).join('');
  const due=Number(t.bill_total||0)+Number(t.fee||0),v=x.ui.cod?.[id]??'';
  const cod=w.shipper&&t.billed?`<section class="card ps-cod"><h4>💵 Phiếu thu hộ</h4><p class="small">Hóa đơn <b>${t.bill_total||0}</b> + phí ship <b>${t.fee||0}</b> = <b>${due} xu</b> shipper thu của khách.</p>
    ${w.cod!=null?`<p><span class="tag green">✓ Đã ghi thu hộ ${w.cod} xu</span></p>`:`<div class="ps-row"><label class="ps-amt"><span>Số tiền thu hộ (xu)</span><input type="number" inputmode="numeric" min="0" max="5000" value="${x.esc(v)}" data-ps-cod="${x.esc(id)}"></label>${carBtn(x,'✍️ Ghi phiếu','cod',{task:id},'small primary')}</div>`}</section>`:'';
  const packed=Object.entries(n.order||{}).every(([k,q])=>(t.cart?.[k]||0)===q);
  return `${askPanel(t,x,'📞 Gọi lại cho khách',now)}${SF.part(x,id,now,'pack','📦 Đóng hàng',`<section class="card ps-pack"><h4>📦 Đóng hàng · nặng ${kg} kg</h4>${order}</section>`,{done:packed,sum:`nặng ${kg} kg`})}
    ${t.billed?`<section class="card ps-ship"><h4>🛵 Gọi shipper <small class="muted">xe máy tối đa ${bike} kg</small></h4><div class="ps-grid two">${ships}</div></section>`:''}${cod}`;
}
function shipSteps(t,x){
  const n=t.needs||{},w=t.work||{},asked=t.asked||[],id=t.id,rows=[],c=cc(x);
  if(!asked.includes('confirm'))rows.push({stage:'ask',ok:null,label:'Gọi xác nhận địa chỉ',go:{cmd:'ps_ask',payload:{task:id,topic:'confirm'},label:'📍 Gọi xác nhận địa chỉ'}});
  else rows.push({ok:true,label:'Gọi xác nhận địa chỉ'});
  if(!t.billed)for(const [k,q] of Object.entries(n.order||{})){
    const got=t.cart?.[k]||0,i=c.items[k];
    if(got!==q)rows.push({stage:'pack',ok:got>q?false:null,label:`Đóng ${q} ${lower(i.name)}`,note:`${got}/${q}`,go:x.stock(k)>=q?{cmd:'ps_cart',payload:{task:id,key:k,qty:q},label:`📦 Đóng ${q} ${x.esc(lower(i.name))}`}:inv(x,lower(i.name))});
  }
  if(t.billed){
    rows.push({stage:'ship',ok:w.shipper?true:null,label:'Chọn shipper hợp với đơn',go:w.shipper?null:{sel:'.ps-ship',label:'🛵 Chọn shipper'},pulse:''});
    if(w.shipper)rows.push({stage:'cod',ok:w.cod!=null?true:null,label:'Ghi tiền thu hộ',go:w.cod!=null?null:{sel:'[data-ps-cod]',label:'💵 Ghi tiền thu hộ'},pulse:''});
  }
  return rows;
}

/* ------------------------------------------------------------ the guide */
const PANELS={food:foodPanel,tank:tankPanel,screen:screenPanel,care:carePanel,ret:retPanel,lost:lostPanel,ship:shipPanel};
const STEPS={food:foodSteps,tank:tankSteps,screen:screenSteps,care:careSteps,ret:retSteps,lost:lostSteps,ship:shipSteps};
function guide(t,x){
  const d=data(x),id=t.id;
  if(!d.intro_seen)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'ps_intro',payload:{},label:'🐾 Vào tiệm thôi!'}}],final:null};
  if(!t.known)return {steps:[{ok:null,label:'Nghe khách nói',go:{cmd:'ask',payload:{task:id},label:t.job==='ship'?'📞 Nghe máy':'👂 Nghe khách nói'}}],final:null,pulse:'.ps-ask'};
  const steps=STEPS[t.job](t,x);
  if(t.job==='care')return {steps,final:{label:'✅ XONG VÒNG CHĂM',go:finalGo(steps,'ps_care_done',{task:id}),ready:!!(Object.keys(t.work?.fed||{}).length||Object.keys(t.work?.cleaned||{}).length),why:'cho các bé ăn trước'}};
  if(t.job==='ret')return {steps,final:null};
  if(t.job==='lost'){const w=t.work||{},open=(t.calls||[]).some(k=>k.state!=='sent'&&k.state!=='blocked');
    return {steps,final:{label:'📌 XONG VIỆC TÌM THÚ',go:finalGo(steps,'ps_lost_done',{task:id}),ready:!!w.pinned&&(w.found||!open),why:'dán tờ và trả lời hết cuộc gọi'}};}
  if(t.job==='screen'&&t.work?.verdict!=='sell')return {steps,final:null};
  const all=[...steps,...tillSteps(t,x)];
  if(t.job==='ship'){const w=t.work||{};return {steps:all,final:{label:'🛵 GIAO HÀNG',go:finalGo(all,'ps_ship',{task:id}),ready:!!(t.billed&&w.shipper&&w.cod!=null),why:'chốt hóa đơn, chọn shipper, ghi thu hộ'}};}
  return {steps:all,final:{label:'💵 ĐƯA HÀNG · THỐI TIỀN',go:t.cash?finalGo(all,'ps_handover',{task:id,...changePayload(x,id,t.cash)}):null,ready:!!t.cash,why:'chốt hóa đơn trước'}};
}
function hintFor(g,x){
  const f=g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null;
  return nextHint(x,g.steps,{final:f,pulse:g.pulse});
}
function bottom(g,x){
  if(!g.final)return g.steps.length?`<div class="ps-bar">${stepCta(x,g.steps,{label:'',go:null,ready:false})}</div>`:'';
  if(!g.final.go)return `<div class="ps-bar">${stepCta(x,g.steps,{...g.final,go:{sel:'.ps-till'},ready:false})}</div>`;
  return `<div class="ps-bar">${stepCta(x,g.steps,g.final)}</div>`;
}

/* ------------------------------------------------------------ idle: the shop itself */
function pensBoard(x){
  const d=data(x),c=cc(x);
  const rows=Object.entries(c.pens||{}).map(([k,p])=>{const hp=d.pens?.[k]?.health??90,n=k==='corner'?(d.corner||[]).length:Number(d.animals?.[k]||0);
    const dots=k==='corner'?(d.corner||[]).map(a=>swatch(x,furOf(x,c.adoptees?.[a]),'sm')).join(''):(d.coats?.[k]||[]).slice(0,Math.min(n,6)).map(id=>swatch(x,coatOf(x,k,id),'sm')).join('');
    return `<li class="${p.kind}"><span aria-hidden="true">${x.esc(p.emoji)}</span><div class="grow"><b>${x.esc(p.name)}</b><small>${k==='corner'?`${n} bé chờ nhà mới`:`${n} con`} <span class="ps-dots">${dots}</span></small><span class="ps-meter ${hp<50?'low':''}"><i style="width:${hp}%"></i></span></div></li>`;}).join('');
  return `<section class="card ps-board"><h4>🐟 Dãy bể & chuồng</h4><ul class="ps-penlist">${rows}</ul></section>`;
}
function cornerCard(x){
  const d=data(x),c=cc(x),list=(d.corner||[]).map(k=>c.adoptees?.[k]).filter(Boolean);
  if(!(d.stage>=1))return '';
  return `<section class="card ps-corner"><h4>🏡 Góc nhận nuôi · nhóm Chân Nhỏ</h4>${list.length?`<ul class="ps-heard">${list.map(a=>`<li><span aria-hidden="true">${x.esc(a.emoji)}</span><div><b>${x.esc(a.name)} ${swatch(x,furOf(x,a))}</b><p>${x.esc(a.text)}</p></div></li>`).join('')}</ul>`:'<p class="small muted">Các bé đều đã có nhà mới.</p>'}</section>`;
}
function paintRow(x){
  const d=data(x),th=(cc(x).themes||[]).find(v=>v.id===d.theme);if(!th)return '';
  const k=th.colors;
  return `<section class="card ps-paintrow"><span class="ps-pal" aria-hidden="true"><i style="background:${x.esc(k.wall)}"></i><i style="background:${x.esc(k.main)}"></i><i style="background:${x.esc(k.accent)}"></i></span><div class="grow"><b>🎨 Màu sơn của tiệm</b><small>${x.esc(th.name)}</small></div>${carBtn(x,'Đổi màu','paint',{},'small')}</section>`;
}
function notesCard(x){
  const notes=[...(data(x).notes||[])].reverse();
  return `<details class="card ps-notes" ${notes.length?'open':''}><summary>📒 Sổ thú quen · ${notes.length}</summary>${notes.length?`<ul class="ps-heard">${notes.map(n=>`<li><span aria-hidden="true">${x.esc(n.emoji)}</span><div><small>Ngày ${n.day}</small><p>${x.esc(n.text)}</p></div></li>`).join('')}</ul>`:'<p class="small muted">Chuyện của khách quen sẽ được ghi ở đây.</p>'}</details>`;
}
function idleSteps(x){
  const d=data(x);
  if(!d.intro_seen)return [{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'ps_intro',payload:{},label:'🐾 Vào tiệm thôi!'}}];
  return [];
}

export default {
  id:'pet_shop',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=x&&pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    if(!t.known)return t.job==='ship'?'Nghe máy':'Nghe khách nói';
    return ({food:'Hỏi han, chọn bao hạt, tính tiền',tank:'Chọn bể, chọn cá, dặn khách',screen:'Hỏi kỹ rồi mới giao bé',care:'Cho ăn, dọn bể, soi từng bé',ret:'Kiểm tra món trả, quyết định',lost:'Viết tờ tìm thú, lọc cuộc gọi',ship:'Đóng hàng, gọi shipper'})[t.job]||'';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),now=t.known&&!done(t)?SF.reach(x,t.id,g):new Set(),hint=hintFor(g,x);
    const intro=introCard(x,!!x.ui.intro);
    if(!d.intro_seen||x.ui.intro)return `${rootTag(x)}${hint}${intro}${bottom(g,x)}</div>`;
    const paint=x.ui.paint?paintCard(x):'';
    if(!t.known||done(t))return `${rootTag(x)}${hint}${dayBar(x,true)}${paint}${ticket(t,x)}${bottom(g,x)}</div>`;
    const main=PANELS[t.job](t,x,now);
    // The till itself (till.js) is untouched: the bill folds around it, the change panel stays open.
    const tillBox=tillJob(t)&&!(t.job==='screen'&&t.work?.verdict!=='sell')?tillPart(t,x,now)+(t.cash?cashPanel(x,t.id,t.cash,{title:`💵 ${x.esc(x.npc(t.npc).display_name)} trả tiền mặt`}):''):'';
    const k=g.steps.filter(s=>s&&s.ok!==true).length;
    const side=`<details class="ps-todo-fold"><summary>📝 Việc cần làm <small>· ${k?`còn ${k}`:'xong hết'}/${g.steps.length}</small></summary>${stepRows(x,g.steps,'Việc cần làm')}</details>`;
    return `${rootTag(x)}${hint}${dayBar(x,true)}${paint}${ticket(t,x,petRow(t,x))}
      <div class="workbench"><section class="wb-main">${main}${tillBox}</section><aside class="wb-side">${side}</aside></div>${bottom(g,x)}</div>`;
  },
  idle(x){
    const d=data(x),steps=idleSteps(x),todo=pending(steps)?.go,hint=todo?nextHint(x,steps,{}):'';
    const bar=todo?`<div class="ps-bar">${stepCta(x,steps,{label:'',go:null,ready:false})}</div>`:'';
    const intro=introCard(x,!!x.ui.intro);
    if(!d.intro_seen||x.ui.intro)return `${rootTag(x)}${hint}${intro}${bar}</div>`;
    return `${rootTag(x)}${hint}${dayBar(x)}${x.ui.paint?paintCard(x):''}${cornerCard(x)}${pensBoard(x)}${x.ui.paint?'':paintRow(x)}${notesCard(x)}
      <details class="card ps-rules"><summary>📋 Quy định đổi trả</summary><p>${x.esc(cc(x).policy||'')}</p></details>${bar}</div>`;
  },
  input(el,x){
    const id=el.dataset?.psCod;if(!id)return false;
    (x.ui.cod??={})[id]=Math.max(0,Math.min(5000,Math.floor(Number(el.value)||0)));
    return true;
  },
  tick(root){keepBarAboveFooter(root);},
  actions:{
    ...tillActions,
    ...SF.foldActions,
    async intro(d,el,x){x.ui.intro=true;x.render();},
    async introClose(d,el,x){x.ui.intro=false;x.render();},
    async paint(d,el,x){x.ui.paint=true;x.ui.theme=null;x.render();requestAnimationFrame(()=>document.querySelector('.career-job.ps .ps-paint')?.scrollIntoView({block:'nearest',behavior:'smooth'}));},
    async paintClose(d,el,x){x.ui.paint=false;x.ui.theme=null;x.render();},
    async theme(d,el,x){x.ui.theme=d.theme;x.render();},
    async pen(d,el,x){(x.ui.pen??={})[d.task]=d.pen;x.render();requestAnimationFrame(()=>document.querySelector('#sheet[open] .ps-tools')?.scrollIntoView({block:'nearest',behavior:'smooth'}));},
    async sign(d,el,x){const t=x.room.tasks?.find(v=>v.id===d.task);const b=(x.ui.sign??={});const cur=b[d.task]??[...(t?.work?.signed||[])];b[d.task]=cur.includes(d.key)?cur.filter(k=>k!==d.key):[...cur,d.key];x.render();},
    async signGo(d,el,x){const t=x.room.tasks?.find(v=>v.id===d.task);const checks=x.ui.sign?.[d.task]??[...(t?.work?.signed||[])];
      if(!checks.length){x.toast?.('Đánh dấu ít nhất một mục trong giấy nhé.');return;}await x.send('ps_sign',{task:d.task,checks});},
    async field(d,el,x){const t=x.room.tasks?.find(v=>v.id===d.task);const b=(x.ui.notice??={});const cur=b[d.task]??[...(t?.work?.notice||[])];b[d.task]=cur.includes(d.key)?cur.filter(k=>k!==d.key):[...cur,d.key];x.render();},
    async noticeGo(d,el,x){const t=x.room.tasks?.find(v=>v.id===d.task);const fields=x.ui.notice?.[d.task]??[...(t?.work?.notice||[])];
      if(!fields.length){x.toast?.('Chọn ít nhất một dòng cho tờ tìm thú nhé.');return;}await x.send('ps_notice',{task:d.task,fields});},
    async cod(d,el,x){const v=x.ui.cod?.[d.task];
      if(v===undefined||v===''){x.toast?.('Điền số tiền thu hộ trước nhé.');el?.closest?.('.career-job')?.querySelector('[data-ps-cod]')?.focus();return;}
      await x.send('ps_cod',{task:d.task,amount:Number(v)});},
  },
  // "Ngày mai" first: the lines about tomorrow, the stock room, Kho; the rest of the day folded.
  summary(data,x){return linesSummary(data,x);},
  dock:[['inventory','box','Kho','Nhập & đếm hàng']],
};
