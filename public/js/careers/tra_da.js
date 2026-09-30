/** Trà đá gốc bàng — bà Lựu's sidewalk iced-tea stall (server: game/careers/tra_da.py).
 * Stations (thermos, ice box, glasses and basin, stools), the customer on the
 * stool (pour, snacks, serve, cash or the tab book), the tab settlement with
 * chú Tường, the timed "trật tự đô thị" sweep, surprises, the stall's own story
 * and what it can buy to grow. Everything is decided on the server; the client
 * only shows it and sends one command per tap. */
import {stepRows,nextHint,stepCta,finalGo,pending,firstTime,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {cashPanel,changeStep,changePayload,tillActions} from './till.js';
const DONE=['completed','cancelled','referred'];
const data=x=>x.room.data||{};
const cc=x=>x.cc||{};
const stock=(x,k)=>Number(x.room.inventory?.stock?.[k]||0);
const drinkOf=(x,k)=>(cc(x).drinks||[]).find(d=>d.id===k)||{id:k,name:k,emoji:'🥤',uses:[]};
const snackOf=(x,k)=>(cc(x).snacks||[]).find(d=>d.id===k)||{id:k,name:k,emoji:'•',unit:''};
const lower=s=>s?s[0].toLowerCase()+s.slice(1):'';
const count=(tray,k)=>(tray||[]).filter(g=>g.d===k).length;
const price=(x,k)=>Number(x.room.life?.prices?.[k]??cc(x).prices?.[k]??0);
const carBtn=(x,label,action,d={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-action="car:${action}"${Object.entries(d).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}${extra}>${label}</button>`;
const tile=(x,command,payload,inner,cls='',disabled=false)=>`<button type="button" class="tile td-tile ${cls}" data-command="${command}" data-payload="${x.esc(JSON.stringify(payload))}"${disabled?' disabled':''}>${inner}</button>`;
const bar=(v,max,cls='')=>`<span class="td-meter ${cls}"><i style="width:${Math.max(0,Math.min(100,v/Math.max(1,max)*100)).toFixed(1)}%"></i></span>`;
const inv=(x,what)=>({act:'inventory',label:`📦 Hết ${x.esc(what)}: mở kho nhập thêm`});
/** One line that a tap opens; remembered per key in x.ui.pane. The body is drawn only while open. */
function pane(x,key,summary,body,auto=false,cls=''){
  const open=(x.ui.pane??={})[key]??auto;
  return `<div class="td-pane ${cls}${open?' open':''}"><button type="button" class="td-pane-sum" data-action="car:pane" data-key="${x.esc(key)}" data-open="${open?1:0}" aria-expanded="${open}">${summary}</button>${open?`<div class="td-pane-body">${body}</div>`:''}</div>`;
}

/* ------------------------------------------------------------ cards on top */
function introCard(x,force=false){
  const d=data(x),i=cc(x).intro;if(!i||(d.intro&&!force))return '';
  const list=(title,rows)=>`<section><h4>${x.esc(title)}</h4><ul class="td-icons">${rows.map(([e,s])=>`<li><span aria-hidden="true">${x.esc(e)}</span>${x.esc(s)}</li>`).join('')}</ul></section>`;
  const go=d.intro?carBtn(x,'Đã hiểu','introClose',{},'primary full'):x.cmd('🍵 Vào việc thôi!','td_intro',{},'primary full td-intro-go');
  return `<article class="td-intro card" role="dialog" aria-labelledby="td-intro-title"><h3 id="td-intro-title">🌳 ${x.esc(i.title)}</h3><p>${x.esc(i.lead)}</p>
    <div class="td-intro-grid">${list('Công việc gồm…',i.work)}${list('Bạn sẽ gặp…',i.meet)}${list('Được khen khi…',i.stars)}</div>${go}</article>`;
}
function sweepCard(x){
  const sw=data(x).sweep;if(!sw||sw.stage!=='coming')return '';
  const left=Math.max(0,Math.ceil(sw.start+sw.limit-x.now())),stools=sw.left,umb=sw.umbrella&&!sw.folded;
  return `<section class="td-sweep" role="alert" aria-live="assertive"><div class="td-sweep-head"><span aria-hidden="true">🚨</span><div><small>Trật tự đô thị đang tới</small><h3>Dẹp ghế, gấp ô ngay!</h3></div><b class="td-clock" data-td-sweep="${sw.start+sw.limit}">${left}s</b></div>
    <p>Xe của phường dừng đầu phố. Kịp xếp chồng ghế sát gốc cây và gấp ô thì không sao; để ghế ngoài vỉa hè là bị phạt, thu ghế.</p>
    <div class="td-sweep-btns">${x.cmd(`🪑 Xếp chồng ghế <small>còn ${stools}</small>`,'td_pack',{what:'stools'},'primary big',!stools)}${sw.umbrella?x.cmd(`⛱️ ${umb?'Gấp ô':'Đã gấp ô'}`,'td_pack',{what:'umbrella'},'big',!umb):''}</div></section>`;
}
function deskCard(x){
  const desk=data(x).desk;if(!desk)return '';
  const ev=desk.ev;
  if(ev){
    const opts=ev.options.map(o=>{
      const poor=o.cost>(Number(x.room.money)||0);
      const inner=`<span class="td-opt-label">${x.esc(o.label)}</span>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}${o.cost?`<em>−${x.fmt(o.cost)} xu${poor?' · chưa đủ tiền':''}</em>`:''}`;
      return x.cmd(inner,'td_desk',{option:o.id},'td-opt',poor);
    }).join('');
    return `<section class="td-event ${ev.tone==='tense'?'tense':''}" role="group" aria-labelledby="td-ev-title"><div class="td-ev-head"><span aria-hidden="true">${x.esc(ev.emoji)}</span><div><small>Chuyện ở quán</small><h3 id="td-ev-title">${x.esc(ev.title)}</h3></div></div>
      <p>${x.esc(ev.text)}</p><div class="td-opts">${opts}</div></section>`;
  }
  const last=desk.last,key=last?`${last.script}-${last.choice}-${last.day}-${(desk.log||[]).length}`:'';
  if(last&&last.day===x.room.day&&x.ui.seen!==key)
    return `<div class="td-last ${last.good===true?'good':last.good===false?'bad':''}" role="status"><span aria-hidden="true">${x.esc(last.emoji)}</span><p><b>${x.esc(last.title)}</b> · ${x.esc(last.outcome)}</p>${carBtn(x,'✕','seen',{key},'ghost small td-x',' aria-label="Đã đọc"')}</div>`;
  return '';
}
function arcCard(x){
  const due=data(x).arc?.due;if(!due)return '';
  return `<article class="td-arc card"><small>Chuyện của quán</small><h3>${x.esc(due.emoji)} ${x.esc(due.title)}</h3>${due.text.map(s=>`<p>${x.esc(s)}</p>`).join('')}${x.cmd('Ghi nhớ','td_arc',{},'small primary td-arc-go')}</article>`;
}
function dayBar(x){
  const d=data(x),m=d.mod||{},st=d.stall||{},spot=(cc(x).spots||{})[st.spot];
  const sum=`<span class="td-sky" aria-hidden="true">${x.esc(m.emoji||'🌤️')}</span><b>${x.esc(m.label||'')}${spot?` · ${x.esc(spot.emoji)} ${x.esc(spot.name)}`:''}</b>`;
  return `<div class="td-day">${m.hint?pane(x,`day-${x.room.day}`,sum,`<small>${x.esc(m.hint)}</small>`,false,'grow'):`<div class="grow td-day-line">${sum}</div>`}
    ${carBtn(x,'❔','intro',{},'ghost small td-help',' aria-label="Giới thiệu nghề"')}</div>`;
}

/* ------------------------------------------------------------ stations */
const STATION_OF={td_brew:'tea',td_topup:'tea',td_dump_tea:'tea',td_crush:'ice',td_wash:'cups',td_basin:'cups',td_unpack:'stools'};
function stations(x,steps=null,key='idle'){
  const d=data(x),th=d.thermos||{},ice=d.ice||{},g=d.glasses||{},st=d.stall||{},c=cc(x),che=stock(x,'che');
  const tea=th.tea?`${th.tea}/${th.max} cốc · ${th.strength>=c.weak?'đậm vừa':th.strength>=c.watery?'hơi nhạt':'nhạt như nước'}${th.stale?' · <b class="td-bad">đã ôi</b>':''}`:'Bình trống';
  const brew=[1,2,3].map(n=>x.cmd(`🍃 ${n} nắm<small>${n===1?'nhạt':n===2?'vừa':'đậm'}</small>`,'td_brew',{leaves:n},`small td-leaf ${n===2?'primary':'ghost'}`,che<n)).join('');
  const rate=ice.rate>=8?'tan rất nhanh':ice.rate>=5?'tan nhanh':'tan chậm';
  const card={};
  card.tea=`<div class="td-st card"><h4>🫖 Bình chè</h4>${bar(th.tea||0,th.max||12,th.stale||th.strength<c.weak?'warn':'')}<small>${tea}</small>
      <div class="td-row">${brew}</div><div class="td-row">${x.cmd('🫖 Châm nước','td_topup',{},'small ghost',!th.tea||th.tea>=th.max)}${x.confirmCmd('🚰 Đổ bỏ','td_dump_tea',{},'Đổ bỏ chè đang có trong bình?','small ghost',!th.tea)}</div><small class="muted">Chè khô: ${che} nắm</small></div>`;
  card.ice=`<div class="td-st card"><h4>🧊 Thùng đá</h4>${bar(ice.portions||0,ice.max||24,(ice.portions||0)<4?'warn':'')}<small>${ice.portions||0}/${ice.max} phần · ${rate}</small>
      <div class="td-row">${x.cmd(`🔨 Đập 1 cây đá <small>còn ${ice.blocks||0} cây</small>`,'td_crush',{},'small',!st.box||!ice.blocks||(ice.portions||0)>(ice.max-ice.block))}</div></div>`;
  card.cups=`<div class="td-st card"><h4>🥛 Cốc & chậu</h4><small>Sạch ${g.clean||0} · bẩn ${g.dirty||0}${g.grimy?` · <b class="td-bad">nhờn ${g.grimy}</b>`:''}</small>${bar(d.basin||0,d.basin_max||12,(d.basin||0)>=(d.basin_max||12)?'bad':'')}<small>Nước chậu ${d.basin>=d.basin_max?'đục ngầu':d.basin>d.basin_max/2?'hơi đục':'còn trong'}</small>
      <div class="td-row">${x.cmd('🧽 Rửa cốc','td_wash',{},'small',!(g.dirty||g.grimy))}${x.cmd('🪣 Thay nước','td_basin',{},'small ghost',!d.basin)}</div></div>`;
  card.stools=`<div class="td-st card"><h4>🪑 Ghế · ô</h4><small>${st.packed?'<b class="td-bad">Đang dẹp</b>':`${st.stools||0}/${d.owned?.stools||0} ghế bày`} · ô ${st.umbrella?'đang dựng':'gấp'}</small>
      <div class="td-row">${st.packed?x.cmd('🪑 Bày lại quán','td_unpack',{},'small primary'):''}</div></div>`;
  const keys=['tea','ice','cups','stools'];
  if(!steps)return `<section class="td-stations" aria-label="Quầy trà">${keys.map(k=>card[k]).join('')}</section>`;
  const cur=STATION_OF[pending(steps)?.go?.cmd]||'';
  const low={tea:!th.tea||th.stale||th.strength<c.weak,ice:(ice.portions||0)<4,cups:!g.clean||(d.basin||0)>=(d.basin_max||12),stools:!!st.packed};
  const open=keys.filter(k=>k===cur||(st.open&&low[k]));
  const rest=keys.filter(k=>!open.includes(k));
  const sum=`🧰 chè ${th.tea||0}/${th.max||12} · đá ${ice.portions||0}/${ice.max||24} · cốc ${g.clean||0} · ghế ${st.stools||0}/${d.owned?.stools||0}`;
  return `<section class="td-stations" aria-label="Quầy trà">${open.map(k=>card[k]).join('')}</section>${rest.length?pane(x,`st-${key}-${cur}`,sum,`<div class="td-stations">${rest.map(k=>card[k]).join('')}</div>`,false,'td-st-more'):''}`;
}

/* ------------------------------------------------------------ setup */
function setupPanel(t,x){
  const d=data(x),st=d.stall||{},n=t.needs||{},spots=cc(x).spots||{},owned=d.owned||{};
  const spotTiles=Object.entries(spots).map(([k,s])=>tile(x,'td_spot',{spot:k},`<span class="tile-emoji">${x.esc(s.emoji)}</span><b>${x.esc(s.name)}</b><small>${x.esc(s.note)}</small>`,`${st.spot===k?'selected':''} ${s.legal?'':'danger'}`)).join('');
  const cap=st.spot?spots[st.spot].cap:8,max=Math.min(owned.stools||4,12);
  const stools=Array.from({length:Math.max(0,max-1)},(_,i)=>i+2).map(k=>tile(x,'td_stools',{n:k},`<b>${k}</b><small>ghế</small>`,`td-num ${st.stools===k?'selected':''} ${k>cap?'over':''}`,!st.spot)).join('');
  const here=spots[st.spot],good=st.stools>=cc(x).stools_min&&st.stools<=cap;
  const spotSec=here?pane(x,`spot-${t.id}`,`✓ ${x.esc(here.emoji)} Chỗ bày: ${x.esc(here.name)}${here.legal?'':' ⚠️'}`,`<div class="tile-grid td-spots">${spotTiles}</div>`,false,`td-done${here.legal?'':' warn'}`)
    :`<h4>🌳 Chọn chỗ bày quán</h4><div class="tile-grid td-spots">${spotTiles}</div>`;
  const stoolSec=!st.spot?'':st.stools&&good?pane(x,`stools-${t.id}`,`✓ 🪑 ${st.stools} ghế · chỗ này vừa ${cap} ghế`,`<div class="td-stools">${stools}</div>`,false,'td-done')
    :`<h4 class="section-title">🪑 Bày ghế <small class="muted">chỗ này vừa ${cap} ghế</small></h4><div class="td-stools">${stools}</div>`;
  return `<div class="card td-setup">${spotSec}${stoolSec}
    <div class="td-row space-top">${x.cmd(st.umbrella?'⛱️ Gấp ô':'⛱️ Dựng ô','td_umbrella',{up:!st.umbrella},st.umbrella?'ghost':'')}${x.cmd(st.box?'🧊 Thùng đá đã đặt':'🧊 Đặt thùng đá chỗ râm','td_box',{},'',!st.spot||st.box)}</div>
    <p class="small muted">${x.esc(n.note||'')}</p></div>`;
}
function setupSteps(t,x){
  const d=data(x),st=d.stall||{},n=t.needs||{},spots=cc(x).spots||{},th=d.thermos||{},ice=d.ice||{},c=cc(x),rows=[],owned=d.owned||{};
  const want=spots[n.spot]||{};
  rows.push({ok:st.spot?st.spot===n.spot:null,label:`Bày ở ${lower(want.name||'')}`,note:st.spot&&st.spot!==n.spot?'bà Lựu dặn chỗ khác':'',go:{cmd:'td_spot',payload:{spot:n.spot},label:`${x.esc(want.emoji||'')} Bày ở ${x.esc(lower(want.name||''))}`}});
  const cap=want.cap||8,good=st.stools>=c.stools_min&&st.stools<=(spots[st.spot]||want).cap,k=Math.min(owned.stools||4,cap);
  rows.push({ok:st.stools?good:null,label:'Bày ghế nhựa',note:st.stools?`${st.stools} ghế`:'',go:st.spot?{cmd:'td_stools',payload:{n:k},label:`🪑 Bày ${k} ghế`}:null});
  if(n.umbrella)rows.push({ok:st.umbrella||st.spot==='hien'?true:null,label:'Dựng ô che nắng',go:{cmd:'td_umbrella',payload:{up:true},label:'⛱️ Dựng ô'}});
  rows.push({ok:st.box?true:null,label:'Đặt thùng đá chỗ râm',go:st.spot?{cmd:'td_box',payload:{},label:'🧊 Đặt thùng đá'}:null});
  const brewOk=th.tea>0&&th.strength>=c.weak;
  rows.push({ok:th.tea?brewOk:null,label:'Pha một bình chè đậm vừa',note:th.tea&&!brewOk?'chè nhạt: pha lại':'',go:stock(x,'che')>=2?{cmd:'td_brew',payload:{leaves:2},label:'🍵 Pha bình chè (2 nắm)'}:inv(x,'chè')});
  rows.push({ok:ice.portions>0?true:null,label:'Đập một cây đá vào thùng',go:!st.box?null:ice.blocks?{cmd:'td_crush',payload:{},label:'🔨 Đập một cây đá'}:inv(x,'đá cây')});
  return rows;
}

/* ------------------------------------------------------------ a customer */
function ticket(t,x){
  const who=x.npc(t.npc);
  if(!t.known)return `<article class="card td-ticket"><div class="row">${x.portrait(who,56)}<div class="grow"><h3>${x.esc(who.display_name)}</h3><p>${x.esc(t.opening)}</p></div></div>${x.cmd('👂 Hỏi khách gọi gì','ask',{task:t.id},'primary full td-ask')}</article>`;
  const n=t.needs||{};
  const chips=[...Object.entries(n.drinks||{}).map(([k,q])=>{const dr=drinkOf(x,k),h=count(t.tray,k);return `<span class="td-chip ${h>=q?'ok':''}">${x.esc(dr.emoji)} ${h}/${q} ${x.esc(lower(dr.name))} <small>${price(x,k)} xu</small></span>`;}),
    ...Object.entries(n.snacks||{}).map(([k,q])=>{const s=snackOf(x,k),h=(t.snacks||{})[k]||0,kid=n.kid&&k==='thuoc_la';return `<span class="td-chip ${kid?'no':h>=q?'ok':''}">${x.esc(s.emoji)} ${kid?'':`${h}/`}${q} ${x.esc(s.unit)} ${x.esc(lower(s.name))}${kid?' <small>trẻ con hỏi mua</small>':` <small>${price(x,k)} xu</small>`}</span>`;})].join('');
  const match=t.kind==='match'&&t.start_turn!=null?Math.max(0,(cc(x).match_turns||8)-((x.room.turn||0)-t.start_turn)):null;
  return `<article class="card td-ticket"><div class="row">${x.portrait(who,48)}<div class="grow"><div class="row spread"><h3>${x.esc(who.display_name)}</h3>${n.pay==='tab'?'<span class="tag amber">📒 Ghi sổ</span>':'<span class="tag green">💵 Tiền mặt</span>'}</div>
    <p class="small"><b>${x.esc(t.title)}</b> · ${n.seats>1?`${n.seats} người ngồi`:'1 người'}</p><p class="td-chips">${chips}</p><p class="muted small">“${x.esc(n.note||'')}”</p>
    ${match!=null?`<p class="notice ${match<=2?'amber':''} small">⚽ Còn khoảng ${match} lượt nữa là hết hiệp một.</p>`:''}
    <div class="patience" title="Kiên nhẫn"><div class="bar ${t.patience<50?'low':''}"><i style="width:${t.patience}%"></i></div><small>${t.patience}%</small></div></div></div></article>`;
}
function pourPanel(t,x){
  const n=t.needs||{},d=data(x),th=d.thermos||{},g=d.glasses||{};
  const pour=(cc(x).drinks||[]).map(dr=>{const miss=(dr.uses||[]).find(k=>!stock(x,k)),dis=!th.tea||!(g.clean||g.grimy)||!!miss;
    return tile(x,'td_pour',{task:t.id,drink:dr.id},`<span class="tile-emoji">${x.esc(dr.emoji)}</span><b>${x.esc(dr.name)}</b><small>${miss?'hết '+(miss==='sau'?'sấu':'chanh'):price(x,dr.id)+' xu'}</small>`,dr.id in (n.drinks||{})?'want':'',dis);}).join('');
  const snacks=(cc(x).snacks||[]).map(s=>{const q=stock(x,s.id);return tile(x,'td_snack',{task:t.id,item:s.id},`<span class="tile-emoji">${x.esc(s.emoji)}</span><b>${x.esc(s.name)}</b><small>${q?`còn ${q}`:'hết'}</small>`,s.id in (n.snacks||{})&&!(n.kid&&s.id==='thuoc_la')?'want':'',!q);}).join('');
  const tray=(t.tray||[]).map((gl,i)=>{const dr=drinkOf(x,gl.d);return `<button type="button" class="td-glass ${gl.grimy||gl.stale||(gl.s<cc(x).weak)?'warn':''}" data-command="td_takeback" data-payload="${x.esc(JSON.stringify({task:t.id,index:i}))}" aria-label="Đổ bỏ cốc ${x.esc(dr.name)}"><span aria-hidden="true">${x.esc(dr.emoji)}</span><small>${x.esc(dr.name)}${dr.cold?(gl.ice?' · có đá':' · <b>không đá</b>'):''}</small><i aria-hidden="true">↩︎</i></button>`;}).join('');
  const sn=Object.entries(t.snacks||{}).map(([k,q])=>{const s=snackOf(x,k);return `<button type="button" class="td-glass" data-command="td_takeback" data-payload="${x.esc(JSON.stringify({task:t.id,item:k}))}" aria-label="Cất lại ${x.esc(s.name)}"><span aria-hidden="true">${x.esc(s.emoji)}</span><small>${q} ${x.esc(s.unit)}</small><i aria-hidden="true">↩︎</i></button>`;}).join('');
  return `<div class="card td-pour"><h4>🥤 Rót trà</h4><div class="tile-grid td-drinks">${pour}</div>
    <h4 class="section-title">🌻 Đồ ăn vặt</h4><div class="tile-grid td-snacks">${snacks}</div>
    ${n.kid?`<div class="td-row space-top">${x.cmd(t.refused?'🙅 Đã từ chối bán thuốc':'🙅 Không bán thuốc lá cho trẻ con','td_refuse',{task:t.id},t.refused?'ghost':'danger',t.refused)}</div>`:''}
    <h4 class="section-title">🍽️ Khay mang ra</h4><div class="td-tray">${tray+sn||'<small class="muted">Khay còn trống.</small>'}</div></div>`;
}
function bookPanel(t,x){
  const v=x.ui.book?.[t.id]??'';
  return `<div class="card td-bookw"><h4>📒 Ghi sổ cho ${x.esc(x.npc(t.npc).display_name)}</h4><p class="small">Hóa đơn: <b>${x.money(t.owe||0)}</b>. Ghi đúng số vào sổ, bà Lựu dò sổ mỗi tối.</p>
    <div class="td-row"><label class="td-amt"><span>Số tiền ghi sổ (xu)</span><input type="number" inputmode="numeric" min="1" max="500" value="${x.esc(v)}" data-td-book="${x.esc(t.id)}"></label>${carBtn(x,'✍️ Ghi vào sổ','book',{task:t.id},'primary')}</div></div>`;
}
const need=(t,k)=>(t.needs?.drinks||{})[k]||0;
function customerSteps(t,x){
  const d=data(x),n=t.needs||{},th=d.thermos||{},ice=d.ice||{},g=d.glasses||{},st=d.stall||{},c=cc(x),rows=[],id=t.id;
  if(!st.open)rows.push({ok:null,label:'Dọn hàng xong mới bán',go:null});
  if(st.packed)rows.push({ok:null,label:'Bày lại quán',go:{cmd:'td_unpack',payload:{},label:'🪑 Bày lại ghế, dựng ô'}});
  // Extra glasses first: pour the right ones, then hand over.
  (t.tray||[]).forEach((gl,i)=>{if(count(t.tray.slice(0,i+1),gl.d)>need(t,gl.d))rows.push({ok:false,label:`Cốc ${lower(drinkOf(x,gl.d).name)} khách không gọi`,go:{cmd:'td_takeback',payload:{task:id,index:i},label:`↩︎ Đổ bỏ cốc ${x.esc(lower(drinkOf(x,gl.d).name))}`}});});
  for(const [k,q] of Object.entries(n.drinks||{})){
    const have=count(t.tray,k),dr=drinkOf(x,k);
    if(have>=q){rows.push({ok:true,label:`${q} ${lower(dr.name)}`});continue;}
    let go={cmd:'td_pour',payload:{task:id,drink:k},label:`${x.esc(dr.emoji)} Rót ${x.esc(lower(dr.name))} (${have+1}/${q})`},note=`${have}/${q}`;
    const miss=(dr.uses||[]).find(u=>!stock(x,u));
    if(!th.tea||th.stale||th.strength<c.weak)go=stock(x,'che')>=2?{cmd:'td_brew',payload:{leaves:2},label:th.tea?'🍵 Chè nhạt/ôi: pha bình mới':'🍵 Hết chè: pha bình mới'}:inv(x,'chè');
    else if(!(g.clean))go=d.basin>=d.basin_max?{cmd:'td_basin',payload:{},label:'🪣 Nước chậu đục: thay nước'}:(g.dirty||g.grimy)?{cmd:'td_wash',payload:{},label:'🧽 Hết cốc sạch: rửa cốc'}:go;
    else if(dr.cold&&!ice.portions)go=ice.blocks?{cmd:'td_crush',payload:{},label:'🔨 Hết đá: đập thêm một cây'}:inv(x,'đá cây');
    else if(miss){go=null;note=`hết ${miss==='sau'?'sấu':'chanh'}`;}
    rows.push({ok:null,label:`${q} ${lower(dr.name)}`,note,go});
  }
  for(const [k,q] of Object.entries(n.snacks||{})){
    const s=snackOf(x,k),have=(t.snacks||{})[k]||0;
    if(n.kid&&k==='thuoc_la'){
      if(have)rows.push({ok:false,label:'Trẻ con không được mua thuốc lá',go:{cmd:'td_takeback',payload:{task:id,item:k},label:'↩︎ Cất lại thuốc lá'}});
      rows.push({ok:t.refused?true:null,label:'Nói khéo: không bán thuốc cho trẻ con',go:{cmd:'td_refuse',payload:{task:id},label:'🙅 Từ chối bán thuốc lá'}});
      continue;
    }
    rows.push(have>=q?{ok:true,label:`${q} ${s.unit} ${lower(s.name)}`}:{ok:null,label:`${q} ${s.unit} ${lower(s.name)}`,note:`${have}/${q}`,go:stock(x,k)?{cmd:'td_snack',payload:{task:id,item:k},label:`${x.esc(s.emoji)} Lấy ${x.esc(lower(s.name))} (${have+1}/${q})`}:inv(x,lower(s.name))});
  }
  for(const [k] of Object.entries(t.snacks||{}))if(!(k in (n.snacks||{})))rows.push({ok:false,label:`${snackOf(x,k).name}: khách không gọi`,go:{cmd:'td_takeback',payload:{task:id,item:k},label:`↩︎ Cất lại ${x.esc(lower(snackOf(x,k).name))}`}});
  if(n.seats>(st.stools||0))rows.push({ok:null,label:`Đủ ${n.seats} ghế cho khách`,note:`đang bày ${st.stools||0}`,go:(d.owned?.stools||0)>=n.seats?{cmd:'td_stools',payload:{n:Math.min(d.owned.stools,Math.max(n.seats,st.stools||0))},label:`🪑 Bày thêm ghế (${n.seats})`}:null});
  return rows;
}

/* ------------------------------------------------------------ the tab settlement */
function settlePanel(t,x){
  const b=t.bill;
  if(!b||t.stage==='prep')return `<div class="card td-settle"><h4>📒 Sổ của chú Tường</h4><p class="small">Chú hỏi hết bao nhiêu. Mở sổ, đọc từng dòng cho chú nghe.</p></div>`;
  const dp=t.dispute||{},lines=b.lines.map(l=>`<li class="${dp.line===l.id&&t.stage==='dispute'?'hot':''}"><span>Ngày ${l.day}</span><span class="grow">${x.esc(l.what)}</span><b>${x.fmt(l.amount)} xu</b></li>`).join('');
  let ask='';
  if(t.stage==='dispute'){
    const l=b.lines.find(r=>r.id===dp.line);
    ask=`<div class="td-dispute"><p><b>Chú Tường hỏi lại dòng ngày ${l?.day}:</b> ${x.esc(l?.what||'')} · ${x.fmt(l?.amount||0)} xu. Tự tính lại theo giá quán rồi chọn:</p>
      <div class="td-opts">${x.cmd('📒 Cho chú xem dòng sổ','td_dispute',{task:t.id,choice:'show'},'td-opt')}${x.cmd('✏️ Ghi nhầm: sửa lại cho đúng','td_dispute',{task:t.id,choice:'fix'},'td-opt')}${x.cmd('🤝 Thôi, bỏ dòng này cho chú','td_dispute',{task:t.id,choice:'drop'},'td-opt')}${x.cmd('😤 Cãi: sổ ghi thế thì trả thế','td_dispute',{task:t.id,choice:'argue'},'td-opt')}</div></div>`;
  }
  return `<div class="card td-settle"><h4>📒 Sổ của chú Tường</h4><ul class="td-book">${lines||'<li class="muted">Sổ trắng.</li>'}</ul><p class="row spread"><span>Cộng</span><b>${x.money(b.total)}</b></p>${ask}</div>`;
}

/* ------------------------------------------------------------ guide */
function guide(t,x){
  const d=data(x);
  if(d.sweep?.stage==='coming')return {steps:[{ok:null,label:'Dẹp ghế, gấp ô trước khi xe tới',go:{sel:'.td-sweep',label:'🚨 Dẹp quán ngay!'}}],final:null};
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở quán',go:{sel:'.td-opts',label:'👉 Chọn cách xử lý chuyện ở quán'}}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'td_intro',payload:{},label:'🍵 Vào việc thôi!'}}],final:null};
  if(t.kind==='setup'){const steps=setupSteps(t,x);return {steps,final:{label:'☀️ MỞ HÀNG',go:finalGo(steps,'td_open',{task:t.id}),ready:!!(d.stall?.spot&&d.stall?.box&&(d.stall?.stools||0)>=cc(x).stools_min),why:'chọn chỗ, bày ghế, đặt thùng đá'}};}
  if(!t.known)return {steps:[{ok:null,label:'Hỏi khách gọi gì',go:{cmd:'ask',payload:{task:t.id},label:'👂 Hỏi khách gọi gì'}}],final:null,pulse:'.td-ask'};
  if(t.kind==='settle'){
    if(t.stage==='prep')return {steps:[{ok:null,label:'Đọc sổ cho chú Tường',go:{cmd:'td_bill',payload:{task:t.id},label:'📒 Mở sổ, đọc cho chú'}}],final:null};
    if(t.stage==='dispute')return {steps:[{ok:null,label:'Xem lại dòng chú hỏi',go:{sel:'.td-dispute',label:'📒 Xem lại dòng chú hỏi'},pulse:''}],final:null};
    if(!t.cash)return {steps:[],final:{label:'🤝 Xong sổ',go:{cmd:'td_settle_free',payload:{task:t.id}},ready:true}};
  }
  if(t.stage==='pay'){
    const s=changeStep(x,t.id,t.cash),steps=s?[s]:[];
    return {steps,final:{label:'💵 ĐƯA TIỀN THỐI',go:finalGo(steps,'td_pay',{task:t.id,...changePayload(x,t.id,t.cash)}),ready:true}};
  }
  if(t.stage==='book'){
    const v=Number(x.ui.book?.[t.id]||0);
    return {steps:[{ok:v?true:null,label:`Ghi ${t.owe} xu vào sổ`,note:v?`đang ghi ${v}`:'',go:v?null:{sel:'[data-td-book]',label:'✍️ Điền số tiền vào sổ'}}],final:{label:'✍️ GHI VÀO SỔ',go:{cmd:'td_book',payload:{task:t.id,amount:v||t.owe}},ready:true}};
  }
  const steps=customerSteps(t,x);
  const has=(t.tray||[]).length||Object.keys(t.snacks||{}).length||t.refused;
  return {steps,final:{label:t.needs?.pay==='tab'?'🥤 ĐƯA TRÀ · GHI SỔ':'🥤 ĐƯA TRÀ · TÍNH TIỀN',go:finalGo(steps,'td_serve',{task:t.id}),ready:!!has,why:'rót trà cho khách trước'}};
}
function hintFor(g,x){
  const f=g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null;
  return nextHint(x,g.steps,{final:f,pulse:g.pulse});
}
function bottom(t,x,g){
  if(!g.final)return g.steps.length?`<div class="td-bar">${stepCta(x,g.steps,{label:'',go:null,ready:false})}</div>`:'';
  return `<div class="td-bar">${stepCta(x,g.steps,g.final)}</div>`;
}

/* ------------------------------------------------------------ idle: the book, growth, ice */
function tabFold(x){
  const tab=data(x).tab||{lines:[],owed:0};
  return `<details class="td-fold card"><summary>📒 Sổ ghi nợ · ${x.money(tab.owed||0)}</summary><ul class="td-book">${tab.lines.map(l=>`<li><span>Ngày ${l.day}</span><span class="grow">${x.esc(l.what)}</span><b>${x.fmt(l.amount)} xu</b></li>`).join('')||'<li class="muted">Sổ trắng, chưa ai nợ.</li>'}</ul></details>`;
}
function growFold(x){
  const d=data(x),o=d.owned||{},money=Number(x.room.money)||0,c=cc(x);
  const done={stools:(o.stools||0)+2>(c.stools_max||12),glasses:(o.glasses||0)+4>24,umbrella:(o.umbrella||1)>=2,banner:!!o.banner};
  const rows=(c.growth||[]).map(gr=>`<li><span aria-hidden="true">${x.esc(gr.emoji)}</span><div class="grow"><b>${x.esc(gr.name)}</b><small>${x.esc(gr.note)}</small></div>${done[gr.id]?'<span class="tag green">✓ Có rồi</span>':x.confirmCmd(`${gr.cost} xu`,'td_buy',{item:gr.id},`Mua ${lower(gr.name)} hết ${gr.cost} xu nhé?`,'small',money<gr.cost)}</li>`).join('');
  const plan=d.ice_plan??3,pm=c.ice_plan_max||6;
  return `<details class="td-fold card"><summary>🌱 Sắm sửa cho quán · ${o.stools||0} ghế · ô ${o.umbrella>=2?'to':'cũ'}${o.banner?' · có biển':''}</summary><ul class="td-grow">${rows}</ul>
    <h4 class="section-title">🧊 Dặn anh Tuấn xe đá (4 xu/cây, giao mỗi sáng)</h4><div class="td-row">${x.cmd('−','td_ice_plan',{n:Math.max(0,plan-1)},'small ghost td-step',plan<=0)}<b class="td-plan">${plan} cây/sáng</b>${x.cmd('+','td_ice_plan',{n:Math.min(pm,plan+1)},'small ghost td-step',plan>=pm)}</div></details>`;
}
function idleSteps(x){
  const d=data(x),g=d.glasses||{},ice=d.ice||{},th=d.thermos||{},st=d.stall||{},c=cc(x),rows=[];
  if(d.sweep?.stage==='coming')return [{ok:null,label:'Dẹp quán trước khi xe tới',go:{sel:'.td-sweep',label:'🚨 Dẹp quán ngay!'}}];
  if(d.desk?.ev)return [{ok:null,label:'Quyết chuyện ở quán',go:{sel:'.td-opts',label:'👉 Chọn cách xử lý chuyện ở quán'}}];
  if(!d.intro)return [{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'td_intro',payload:{},label:'🍵 Vào việc thôi!'}}];
  if(!st.open)return rows;
  if(st.packed)rows.push({ok:null,label:'Bày lại quán',go:{cmd:'td_unpack',payload:{},label:'🪑 Bày lại ghế, dựng ô'}});
  if(d.basin>=d.basin_max)rows.push({ok:null,label:'Thay nước chậu rửa',go:{cmd:'td_basin',payload:{},label:'🪣 Thay nước chậu'}});
  else if((g.dirty||0)+(g.grimy||0)>=4)rows.push({ok:null,label:'Rửa cốc bẩn',go:{cmd:'td_wash',payload:{},label:'🧽 Rửa cốc'}});
  if(ice.portions<4&&ice.blocks&&st.box)rows.push({ok:null,label:'Đập thêm đá',go:{cmd:'td_crush',payload:{},label:'🔨 Đập một cây đá'}});
  if((!th.tea||th.stale||th.strength<c.weak)&&stock(x,'che')>=2)rows.push({ok:null,label:'Pha bình chè mới',go:{cmd:'td_brew',payload:{leaves:2},label:'🍵 Pha bình chè mới'}});
  return rows;
}

export default {
  id:'tra_da',
  css:true,
  next(t,x){
    try{const n=x&&pending(guide(t,x).steps);if(n)return x.esc(stepLine(n));const g=guide(t,x);if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    if(t.kind==='setup')return 'Dọn hàng, pha chè, đập đá';
    if(!t.known)return 'Hỏi khách gọi gì';
    return t.kind==='settle'?'Đọc sổ, thu tiền':'Rót trà, đưa cho khách';
  },
  job(t,x){
    const g=guide(t,x),hint=hintFor(g,x),d=data(x);
    const top=`${introCard(x,!!x.ui.intro)}${sweepCard(x)}${deskCard(x)}`;
    if(d.sweep?.stage==='coming'||d.desk?.ev||!d.intro||x.ui.intro)return `<div class="career-job td">${hint}${top}${bottom(t,x,g)}</div>`;
    let main='',side='';
    if(t.kind==='setup'){main=setupPanel(t,x);side=stepRows(x,g.steps,'Việc dọn hàng');}
    else if(t.kind==='settle'){main=settlePanel(t,x)+(t.stage==='pay'&&t.cash?cashPanel(x,t.id,t.cash,{title:'💵 Chú Tường trả tiền'}):'');}
    else if(!t.known){main='';}
    else if(t.stage==='pay'){main=cashPanel(x,t.id,t.cash);}
    else if(t.stage==='book'){main=bookPanel(t,x);}
    else{main=pourPanel(t,x);side=stepRows(x,g.steps,'Việc của khách');}
    const head=t.kind==='setup'?`${arcCard(x)}${dayBar(x)}`:`${ticket(t,x)}${dayBar(x)}`;
    return `<div class="career-job td">${hint}${top}${head}
      <div class="workbench"><section class="wb-main">${main}${stations(x,g.steps,t.id)}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(t,x,g)}</div>`;
  },
  idle(x){
    const d=data(x),steps=idleSteps(x),todo=pending(steps)?.go,hint=todo?nextHint(x,steps,{}):'';
    const top=`${introCard(x,!!x.ui.intro)}${sweepCard(x)}${deskCard(x)}`;
    const bar=todo?`<div class="td-bar">${stepCta(x,steps,{label:'',go:null,ready:false})}</div>`:'';
    if(d.sweep?.stage==='coming'||d.desk?.ev||!d.intro||x.ui.intro)return `<div class="career-job td">${hint}${top}${bar}</div>`;
    return `<div class="career-job td">${hint}${top}${arcCard(x)}${dayBar(x)}${stations(x,steps,'idle')}${tabFold(x)}${growFold(x)}${bar}</div>`;
  },
  input(el,x){
    const id=el.dataset?.tdBook;if(!id)return false;
    (x.ui.book??={})[id]=Math.max(0,Math.min(500,Math.floor(Number(el.value)||0)))||'';
    return true;
  },
  tick(root,x){
    keepBarAboveFooter(root);
    const clock=root.querySelector('[data-td-sweep]');
    if(clock){
      const end=Number(clock.dataset.tdSweep),left=Math.max(0,Math.ceil(end-x.now()));
      const s=`${left}s`;if(clock.textContent!==s)clock.textContent=s;clock.classList.toggle('late',left<=5);
      if(left<=0&&x.ui.sweepSent!==end){x.ui.sweepSent=end;x.send('td_sweep_end',{});}
    }
  },
  actions:{
    ...tillActions,
    async seen(d,el,x){x.ui.seen=d.key;x.render();},
    async pane(d,el,x){(x.ui.pane??={})[d.key]=d.open!=='1';x.render();},
    async intro(d,el,x){x.ui.intro=true;x.render();},
    async introClose(d,el,x){x.ui.intro=false;x.render();},
    async book(d,el,x){
      const v=Number(x.ui.book?.[d.task]||0);
      if(!v){x.toast?.('Điền số tiền ghi sổ trước nhé.');root(el)?.querySelector('[data-td-book]')?.focus();return;}
      await x.send('td_book',{task:d.task,amount:v});
    },
  },
  dock:[['inventory','box','Kho chè & đồ vặt','Chè, chanh, hướng dương, thuốc lẻ']],
};
const root=el=>el?.closest?.('.career-job');
