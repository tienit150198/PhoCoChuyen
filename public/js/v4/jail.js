/** 🚔 Trại tạm giữ (game/jail.py): the player's own screen while they serve a few in-game days.
 *
 * Its own dialog (like the Chợ đen's), opened by itself when api.state.jail appears (app.js calls sync() on every
 * state) and with data-action="jail"; closing it leaves a small chip ("🚔 Trại · còn N ngày") that opens it again.
 * Owner 09/10 "vô tù có map, di chuyển này kia được nữa đi chứ đừng mỗi cái hình": the screen is the camp itself, a
 * place to walk (./jail-map.js, scenes/jail-place.js). Each công ích task is done at its own corner (🧹 the yard's
 * cây bàng, 🍚 the căng tin's counter, 📚 the library shelf…): walk up, its panel opens over the camp with the small
 * tap/drag game. The bunk ends the jail day ("🌙 Hết một ngày trong trại", jail_end: the life day moves on without
 * work), the phòng thăm gặp asks the friends for bail (POST /api/marriage/jail_ask: every friend gets a request, a
 * friend pays), the cán bộ trực has the days, the rules and the ways out to the chats, the Cổng trại the countdown.
 * The chips under the camp go to each place (the keyboard's and a screen reader's way). A browser that cannot draw
 * the camp (no canvas / ResizeObserver) gets the card page as before. Every rule and number is the server's: the
 * tasks' layouts come in the state (pz), the answers are checked there (jail_task_done), the day's end waits for
 * `ready`. No odds anywhere. While jailed the page asks for the state now and then (a friend's bail lands on the
 * server). Styles: /css/jail.css. */
import {icon,escapeHTML as esc} from '../icons.js';
import {setup as mapSetup,canMap} from './jail-map.js';
import {PLACES,TASK_SPOT,TASK_ICON} from '../scenes/jail-place.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const S={env:null,dlg:null,chip:null,id:null,game:null,busy:false,flash:null,skew:0,tick:0,poll:0,sure:false,map:null,mapOn:false,panel:null};
const J=()=>S.env?.api?.state?.jail||null;
const nowMs=()=>Date.now()+S.skew;
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,op,data={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-jl="${op}"${attrs(data)}${extra}>${label}</button>`;
const mmss=s=>{s=Math.max(0,Math.ceil(s));return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;};
const reduce=()=>document.documentElement.classList.contains('reduce-motion')||matchMedia('(prefers-reduced-motion: reduce)').matches;

let cssReady=null;
const ensureCss=()=>cssReady??=new Promise(done=>{
  if(document.querySelector('link[data-jl-css]')){done();return;}
  const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.('/css/jail.css')||'/css/jail.css';l.setAttribute('data-jl-css','');
  l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
});

/* ---- the dialog and the chip ---- */
function dialog(){
  if(S.dlg)return S.dlg;
  S.mapOn=canMap();
  const d=document.createElement('dialog');
  d.className=S.mapOn?'sheet v4-sheet jl-sheet jl-map':'sheet v4-sheet medium jl-sheet';d.setAttribute('aria-labelledby','jl-title');
  d.innerHTML=S.mapOn?`<div class="jl-root"><div class="jl-headslot"></div><div class="jl-stage"><div class="jl-panel" role="region" aria-live="polite" hidden></div></div>
    <nav class="jl-here" aria-label="Các chỗ trong trại"></nav></div>`:'<div class="jl-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    const el=e.target.closest('[data-jl]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.jl,el.dataset,el);
  });
  d.addEventListener('pointerdown',paintDown);
  d.addEventListener('pointermove',paintMove);
  d.addEventListener('close',()=>{clearInterval(S.tick);S.tick=0;S.flash=null;S.map?.off();chip();});
  S.dlg=d;
  if(S.mapOn)S.map=mapSetup({J,state:()=>({api:S.env?.api,skew:S.skew}),panelBox:()=>d.querySelector('.jl-panel'),
    arrive:s=>{S.panel=s.id;S.sure=false;if(!S.game||S.panel!=='task:'+S.game.task)S.flash=null;render();d.querySelector('.jl-panel')?.scrollTo?.(0,0);},
    leave:()=>{if(S.panel){S.panel=null;S.sure=false;render();}}});
  return d;
}
function chip(){
  const j=J(),show=!!j&&!S.dlg?.open;
  if(!show){S.chip?.remove();S.chip=null;return;}
  if(!S.chip){const b=document.createElement('button');b.type='button';b.className='jl-chip';b.addEventListener('click',()=>openJail(S.env));document.body.append(b);S.chip=b;}
  const t=`🚔 Trại tạm giữ · còn ${j.left} ngày`;if(S.chip.textContent!==t)S.chip.textContent=t;
}
export async function openJail(env){
  S.env=env;
  const j=J();if(!j)return;
  if(typeof j.now==='number')S.skew=j.now*1000-Date.now();
  await ensureCss();
  const d=dialog();
  for(const x of document.querySelectorAll('dialog[open]'))if(x!==d&&!String(x.id||'').startsWith('tut'))try{x.close();}catch{/* already closing */}
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();chip();
  if(S.mapOn)S.map.mount(d.querySelector('.jl-stage'));
  clearInterval(S.tick);S.tick=setInterval(tick,1000);
}
/** Every state (app.js): open on a new sentence, redraw, say goodbye when it is over. */
export function sync(env){
  S.env=env;
  const j=J();
  if(j){
    if(typeof j.now==='number')S.skew=j.now*1000-Date.now();
    if(S.id!==j.id){S.id=j.id;S.game=null;S.panel=null;if(!document.querySelector('dialog.fh-sheet[open]'))openJail(env);}   // the Chợ đen's arrest card goes first; its button opens the camp
    else if(S.dlg?.open&&!S.busy)render();
    if(S.game&&!j.tasks.some(t=>t.id===S.game.task&&!t.done))S.game=null;
    S.map?.redraw();
    chip();poll(true);
    return;
  }
  if(S.id){S.id=null;S.game=null;S.panel=null;poll(false);if(S.dlg?.open)S.dlg.close();chip();env.toast?.('🎉 Bạn đã ra khỏi trại tạm giữ. Về nhà thôi!','good');}
}
/** A friend's bail happens on the server: look again now and then while inside. */
function poll(on){
  if(!on){clearInterval(S.poll);S.poll=0;return;}
  if(S.poll)return;
  S.poll=setInterval(()=>{if(document.hidden||S.busy||!J())return;S.env.api.refresh().catch(()=>{/* the next one */});},40000);
}
function tick(){
  if(!S.dlg?.open)return;
  const j=J();if(!j)return;
  S.dlg.querySelectorAll('[data-jl-count]').forEach(el=>{
    const k=el.dataset.jlCount,left=((k==='day'?j.ready:k==='ask'?j.ask_next:(S.game?.ready||0))*1000-nowMs())/1000;
    if(left<=0){if(el.dataset.done!=='1'){el.dataset.done='1';render();S.map?.redraw();}return;}
    el.textContent=mmss(left);
  });
}

/* ---- the page ---- */
function render(){
  if(!S.dlg)return;
  if(S.mapOn){renderMap();return;}
  const root=S.dlg.querySelector('.jl-root'),y=S.dlg.scrollTop;
  root.innerHTML=page();
  S.dlg.scrollTop=y;
}
const flash=()=>`<p class="jl-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
function head(j){
  const done=j?j.tasks.filter(t=>t.done).length:0,all=j?j.tasks.length:0;
  const sub=j?`<p class="jl-sub"><b>Còn ${j.left} ngày</b> · <span>Ngày ${j.day} trong trại</span> · <span>Công ích ${done}/${all}</span></p>`:'';
  return `<header class="jl-head"><span class="jl-badge" aria-hidden="true">🚔</span><div class="grow"><span class="eyebrow">${esc(j?.why_text||'Trại tạm giữ')}</span><h2 id="jl-title">Trại tạm giữ phường</h2>${S.mapOn?sub:''}</div>
    <button class="icon-btn" type="button" data-jl="close" aria-label="Thu nhỏ">${icon('x',21)}</button></header>`;
}
function page(){
  const j=J();
  if(!j)return head(null)+`<div class="sheet-body jl-body"><p>Bạn không ở trại tạm giữ.</p>${btn('Đóng','close',{},'primary full')}</div>`;
  if(S.game)return head(j)+`<div class="sheet-body jl-body">${flash()}${gameView(j)}</div>`;
  return head(j)+`<div class="sheet-body jl-body">${scene(j)}${flash()}${tasks(j)}${actions(j)}${rules()}</div>`;
}
/* ---- the camp (map mode): the header, the chips to each place, the panel of the place the player stands at ---- */
function renderMap(){
  const j=J(),d=S.dlg;
  const hs=d.querySelector('.jl-headslot'),h=head(j);if(hs.dataset.k!==h){hs.dataset.k=h;hs.innerHTML=h;}
  const here=d.querySelector('.jl-here'),hh=j?chips(j):'';if(here.dataset.k!==hh){here.dataset.k=hh;here.innerHTML=hh;}
  const box=d.querySelector('.jl-panel'),ph=j&&S.panel?panelHTML(j,S.panel):'';
  if(!ph){box.hidden=true;box.innerHTML='';box.dataset.k='';return;}
  if(box.dataset.k!==ph){box.dataset.k=ph;box.innerHTML=ph;}
  box.hidden=false;
}
function chips(j){
  const go=(id,label,cls='')=>`<button type="button" class="jl-spot${cls}" data-jl="spot" data-id="${esc(id)}">${label}</button>`;
  return j.tasks.map(t=>go('task:'+t.id,`<span aria-hidden="true">${t.emoji}</span> ${esc(t.name)}${t.done?' <i aria-label="đã xong">✓</i>':''}`,t.done?' done':' task')).join('')
    +go('bunk','<span aria-hidden="true">🌙</span> Giường · hết ngày')+go('visit','<span aria-hidden="true">🤝</span> Thăm gặp')
    +go('guard','<span aria-hidden="true">👮</span> Cán bộ trực')+go('gate','<span aria-hidden="true">🚪</span> Cổng trại');
}
const top=(emoji,title,sub='')=>`<div class="jl-p-head"><span class="jl-p-emoji" aria-hidden="true">${emoji}</span><div class="grow"><b>${esc(title)}</b>${sub?`<small>${sub}</small>`:''}</div>
  <button type="button" class="icon-btn small" data-jl="shut" aria-label="Đóng">${icon('x',16)}</button></div>`;
function dots(j){return `<span class="jl-dots" aria-hidden="true">${Array.from({length:j.days},(_,i)=>`<i class="${i<j.days-j.left?'on':''}"></i>`).join('')}</span>`;}
function panelHTML(j,id){
  if(id.startsWith('task:')){
    const task=id.slice(5),t=j.tasks.find(x=>x.id===task),place=PLACES[TASK_SPOT[task]];
    if(S.game&&S.game.task===task&&t&&!t.done)return flash()+gameView(j);
    if(!t)return top(place?.icon||TASK_ICON[task]||'📍',place?.name||'')+`<p>Hôm nay chỗ này không có việc công ích của bạn. Việc hôm nay:</p>
      <div class="jl-chips">${j.tasks.map(x=>`<button type="button" class="jl-pick${x.done?' done':''}" data-jl="spot" data-id="task:${esc(x.id)}">${x.emoji} ${esc(x.name)}${x.done?' ✓':''}</button>`).join('')}</div>`;
    return top(t.emoji,t.name,esc(place?.name||''))+flash()+`<p>${esc(t.hint)}</p>`
      +(t.done?'<p class="jl-done">✓ Việc này xong rồi. Đi làm việc khác nhé.</p>':`<div class="jl-p-acts">${btn(S.game?.task===task?'Làm tiếp':'Bắt tay vào làm','start',{task},'primary',S.busy?' disabled':'')}</div>`);
  }
  if(id==='bunk'){
    const done=j.tasks.filter(t=>t.done).length,all=done===j.tasks.length;
    const note=j.left<=1?'Còn một ngày: hết ngày là được về.':all?`Đủ ${j.tasks.length} việc rồi: hết ngày này được tính hai ngày.`:`Công ích hôm nay ${done}/${j.tasks.length}. Làm đủ thì hết ngày được tính hai ngày.`;
    return top('🌙','Giường trong buồng',`Ngày ${j.day} trong trại`)+flash()+`<p class="jl-note">${note}</p>${endButton(j)}
      <p class="jl-why">Hết ngày: qua một ngày sống, không đi làm. Tiền phòng vẫn tính, cơm trại miễn phí.</p>`;
  }
  if(id==='visit')return top('🤝','Phòng thăm gặp')+flash()+`<p>Gọi cho bạn bè qua ô kính. Bạn bè bảo lãnh thì trả ${xu(j.bail)} từ ví của họ, bạn được về ngay.</p>${askButton(j)}`;
  if(id==='guard')return top('👮','Bàn cán bộ trực',`${esc(j.why_text)} · án ${j.days} ngày`)+flash()
    +`<p class="jl-left"><b>Còn ${j.left} ngày</b> ${dots(j)}</p>${tasks(j)}${rules()}`;
  if(id==='gate'){const done=j.tasks.filter(t=>t.done).length;
    return top('🚪','Cổng trại',`Còn ${j.left} ngày`)+`<p class="jl-left"><b>Còn ${j.left} ngày nữa là ra cổng</b> ${dots(j)}</p>
      <ul class="jl-ways"><li><span aria-hidden="true">🧹</span> Làm đủ ${j.tasks.length} việc công ích trong ngày (${done}/${j.tasks.length}): hết ngày được tính hai ngày.</li>
        <li><span aria-hidden="true">🤝</span> Bạn bè bảo lãnh ${xu(j.bail)}: về ngay.</li></ul>
      <div class="jl-p-acts">${btn('🌙 Về giường hết ngày','spot',{id:'bunk'},'cream small')}${btn('🤝 Ra phòng thăm gặp','spot',{id:'visit'},'cream small')}</div>`;}
  return '';
}
function endButton(j){
  const wait=(j.ready*1000-nowMs())/1000;
  return wait>0?btn(`🌙 Hết ngày sau <span data-jl-count="day">${mmss(wait)}</span>`,'end',{},'cream big full',' disabled')
    :btn(S.sure?'🌙 Chắc chưa? Hết ngày nhé':'🌙 Hết một ngày trong trại','end',{},'primary big full',S.busy?' disabled':'');
}
function askButton(j){
  const ask=j.ask_next?(j.ask_next*1000-nowMs())/1000:0;
  return ask>0?btn(`🤝 Đã nhờ bạn bè · nhờ lại sau <span data-jl-count="ask">${mmss(ask)}</span>`,'ask',{},'ghost full',' disabled')
    :btn(`🤝 Nhờ bạn bảo lãnh`,'ask',{},'primary full',S.busy?' disabled':'');
}
function scene(j){
  return `<section class="jl-scene" aria-label="Phòng giam và sân trại"><div class="jl-cell"><div class="jl-window" aria-hidden="true"><span class="jl-sun"></span></div>
      <div class="jl-bars" aria-hidden="true"></div><div class="jl-bunk" aria-hidden="true"><span>🛏️</span></div><div class="jl-me" aria-hidden="true">🧑</div></div>
    <div class="jl-yard" aria-hidden="true"><span class="jl-tree">🌳</span><span class="jl-flag">🚩</span><span class="jl-guard">👮</span><span class="jl-broom">🧹</span></div>
    <div class="jl-days" role="status"><b>Còn ${j.left} ngày</b><small>Ngày ${j.day} trong trại · án ${j.days} ngày</small>${dots(j)}</div></section>`;
}
function tasks(j){
  const done=j.tasks.filter(t=>t.done).length,all=done===j.tasks.length,n=j.tasks.length;
  const doIt=t=>S.mapOn?btn('Đi làm','spot',{id:'task:'+t.id},'primary small'):btn('Làm','start',{task:t.id},'primary small',S.busy?' disabled':'');
  const rows=j.tasks.map(t=>`<li class="jl-task${t.done?' done':''}"><span class="jl-ic" aria-hidden="true">${t.emoji}</span><span class="grow"><b>${esc(t.name)}</b><small>${esc(t.hint)}</small></span>
      ${t.done?'<span class="tag green">Xong ✓</span>':doIt(t)}</li>`).join('');
  const note=j.left<=1?'Còn một ngày: hết ngày là được về.':all?`Đủ ${n} việc rồi: hết ngày này được tính hai ngày.`:`Làm đủ ${n} việc công ích hôm nay: hết ngày được tính hai ngày.`;
  return `<section class="jl-card"><h3>🧹 Công ích hôm nay <small>${done}/${n}</small></h3><ul class="jl-tasks">${rows}</ul><p class="jl-note">${note}</p></section>`;
}
function actions(j){
  return `<section class="jl-card jl-go">${endButton(j)}<p class="jl-why">Hết ngày: qua một ngày sống, không đi làm. Tiền phòng vẫn tính, cơm trại miễn phí.</p>
    ${askButton(j)}<p class="jl-why">Bạn bè bảo lãnh thì trả ${xu(j.bail)} từ ví của họ, bạn được về ngay.</p></section>`;
}
function rules(){
  return `<section class="jl-card jl-rules"><h3>📋 Nội quy trại</h3><ul>
      <li><span aria-hidden="true">✅</span> Trong trại chỉ được nhắn tin và làm công ích.</li>
      <li><span aria-hidden="true">🚫</span> Việc khác (đi làm, chợ đen, mua sắm, ngân hàng, đi chơi…) chờ ra trại rồi làm.</li></ul>
    <div class="jl-links">${btn('💬 Nhắn tin','go',{to:'liveChat'},'ghost small')}${btn('👥 Bạn bè','go',{to:'friends'},'ghost small')}${btn('⚙️ Cài đặt','go',{to:'settings'},'ghost small')}</div></section>`;
}


/* ---- the công ích games: tap and drag, the answer checked by the server ---- */
const TITLE={sweep:'🧹 Quét sân trại',plant:'🌱 Trồng cây ven đường',rice:'🍚 Phụ bếp chia cơm',paint:'🎨 Sơn lại tường',books:'📚 Xếp sách thư viện trại'};
const BOOK_COLORS=['#c0533a','#3a7bc0','#3aa060','#c09a3a','#8a4ac0','#c03a7b','#3aa6a6','#c06a3a','#5a6ac0'];
/* 👕 the clothes and their pegs (game/jail.py COLORS, CLOTHES) */
const COLOR={do:['#e04a3a','đỏ'],cam:['#f08a2a','cam'],vang:['#f2c230','vàng'],la:['#4caf50','xanh lá'],duong:['#3a7bd5','xanh dương'],
  tim:['#8a4ac0','tím'],hong:['#f06aa0','hồng'],nau:['#8a5a32','nâu']};
const CLOTH={ao:['👕','Áo'],quan:['👖','Quần'],khan:['🧣','Khăn'],vo:['🧦','Vớ'],mu:['🧢','Mũ'],ao_khoac:['🧥','Áo khoác'],yem:['🎽','Áo ba lỗ']};
/* 🗑️ the trash and its bins (game/jail.py TRASH, BINS) */
const TRASH={bao_cu:['📰','Báo cũ','giay'],hop_giay:['📦','Hộp giấy','giay'],vo_cu:['📓','Vở cũ','giay'],ly_giay:['☕','Ly giấy','giay'],
  thung_carton:['🗃️','Thùng các-tông','giay'],chai_nhua:['🧴','Chai nhựa','nhua'],tui_ni_long:['🛍️','Túi ni lông','nhua'],hop_xop:['🍱','Hộp xốp','nhua'],
  ong_hut:['🥤','Ống hút nhựa','nhua'],nap_chai:['🔘','Nắp chai','nhua'],vo_chuoi:['🍌','Vỏ chuối','huu_co'],xuong_ca:['🐟','Xương cá','huu_co'],
  la_kho:['🍂','Lá khô','huu_co'],com_thua:['🍚','Cơm thừa','huu_co'],vo_trung:['🥚','Vỏ trứng','huu_co']};
const BIN={giay:['📄','Giấy'],nhua:['♻️','Nhựa'],huu_co:['🌿','Hữu cơ']};
const FEED={thoc:['🌾','Thóc'],ngo:['🌽','Ngô'],rau:['🥬','Rau']};
const STOCK={xa_phong:['🧼','Xà phòng'],khan:['🧣','Khăn'],ban_chai:['🪥','Bàn chải'],chen:['🥣','Chén'],dep:['🩴','Dép'],giay_ve_sinh:['🧻','Giấy vệ sinh']};
const FOLD={trai:['⬅️','Gập mép trái'],phai:['➡️','Gập mép phải'],tren:['⬆️','Gập mép trên'],duoi:['⬇️','Gập mép dưới']};
/* Step games: the tools in order, the art of each stage (🌱 plant, 🍜 dishes) */
const STEPS={
  plant:{n:'holes',tools:[['dig','⛏️','Đào hố'],['seed','🌰','Gieo hạt'],['water','💧','Tưới nước']],art:['🟫','🕳️','🌰','🌱'],
    label:(i,s)=>`Hố ${i+1}: ${s}`,stage:['chưa đào','đã đào','đã gieo hạt','đã tưới, cây lên rồi'],
    say:{dig:'Đào hố trước đã nha.',seed:'Hố đào rồi, gieo hạt đi.',water:'Gieo rồi, giờ tưới nước.'}},
  dishes:{n:'bowls',tools:[['scrape','🥄','Cạo thức ăn'],['soap','🧼','Rửa xà phòng'],['rinse','🚿','Tráng nước'],['rack','🧺','Úp lên giá']],
    art:['🍜','🥣','🫧','💧','✨'],label:(i,s)=>`Chén ${i+1}: ${s}`,stage:['còn thức ăn','đã cạo','đã rửa xà phòng','đã tráng','sạch, úp lên giá rồi'],
    say:{scrape:'Cạo sạch thức ăn thừa trước đã.',soap:'Cạo rồi, giờ rửa xà phòng.',rinse:'Còn xà phòng, tráng nước đi.',rack:'Tráng rồi, úp lên giá cho ráo.'}},
};
function fresh(task,pz,ready){
  const g={task,pz,ready,err:'',sel:null};
  if(task==='sweep')g.hp=Object.fromEntries(pz.piles.map(c=>[c,3]));
  if(STEPS[task]){g.tool=STEPS[task].tools[0][0];g.holes=Array.from({length:pz[STEPS[task].n]},()=>[]);}
  if(task==='rice')g.scoops=pz.want.map(()=>0);
  if(task==='paint')g.painted=[];
  if(task==='books')g.order=[];
  if(task==='laundry')g.hang=pz.items.map(()=>null);
  if(task==='mop')g.wipes=pz.dirt.map(()=>0);
  if(task==='trash')g.bins=pz.items.map(()=>null);
  if(task==='veg')g.picked=[];
  if(task==='chicken'){g.tool=Object.keys(FEED)[0];g.fed=pz.want.map(()=>null);}
  if(task==='fix')g.hits=pz.nails.map(()=>0);
  if(task==='ledger')g.counts=Object.fromEntries(pz.kinds.map(k=>[k,0]));
  if(task==='fold'){g.folds=pz.cards.map(()=>[]);g.at=0;}
  return g;
}
function finished(g){
  const pz=g.pz;
  if(g.task==='sweep')return Object.values(g.hp).every(n=>n<=0);
  if(STEPS[g.task])return g.holes.every(h=>h.length===STEPS[g.task].tools.length);
  if(g.task==='rice')return g.scoops.every((n,i)=>n===pz.want[i]);
  if(g.task==='paint')return pz.dirty.every(c=>g.painted.includes(c));
  if(g.task==='books')return g.order.length===pz.nums.length;
  if(g.task==='laundry')return g.hang.every(x=>x!==null);
  if(g.task==='mop')return g.wipes.every((n,i)=>n===pz.dirt[i]);
  if(g.task==='trash')return g.bins.every(Boolean);
  if(g.task==='veg')return pz.yellow.every(i=>g.picked.includes(i));
  if(g.task==='chicken')return g.fed.every(Boolean);
  if(g.task==='fix')return g.hits.every((n,i)=>n===pz.nails[i]);
  if(g.task==='ledger')return pz.kinds.every(k=>g.counts[k]>0);
  if(g.task==='fold')return g.folds.every((f,i)=>f.length===pz.cards[i].length);
  return false;
}
function answer(g){
  if(g.task==='sweep')return {swept:Object.keys(g.hp).map(Number)};
  if(STEPS[g.task])return {steps:g.holes};
  if(g.task==='rice')return {scoops:g.scoops};
  if(g.task==='paint')return {cells:g.painted.filter(c=>g.pz.dirty.includes(c))};
  if(g.task==='laundry')return {hang:g.hang};
  if(g.task==='mop')return {wipes:g.wipes};
  if(g.task==='trash')return {bins:g.bins};
  if(g.task==='veg')return {picked:g.picked};
  if(g.task==='chicken')return {fed:g.fed};
  if(g.task==='fix')return {hits:g.hits};
  if(g.task==='ledger')return {counts:g.counts};
  if(g.task==='fold')return {folds:g.folds};
  return {order:g.order};
}
/** 📒 the ledger is counted by eye: a wrong count is said here, before the cán bộ sees it. */
function precheck(g){
  if(g.task!=='ledger')return '';
  const off=g.pz.kinds.filter(k=>g.counts[k]!==g.pz.pile.filter(x=>x===k).length);
  return off.length?`Có ${off.length} loại đếm chưa khớp, đếm lại trên kệ nha.`:'';
}
function gameView(j){
  const g=S.game,t=j.tasks.find(x=>x.id===g.task)||{};
  const ok=finished(g),wait=(g.ready*1000-nowMs())/1000;
  const go=!ok?btn('Xong','done',{},'primary big full',' disabled'):wait>0?btn(`Cán bộ đang kiểm tra… <span data-jl-count="task">${mmss(wait)}</span>`,'done',{},'cream big full',' disabled')
    :btn('✅ Báo cán bộ: xong rồi','done',{},'primary big full',S.busy?' disabled':'');
  const title=TITLE[g.task]||`${t.emoji||''} ${esc(t.name||'')}`;
  return `<section class="jl-card jl-game jl-${g.task}"><div class="jl-game-head"><h3>${title}</h3>${btn('‹ Để sau','back',{},'ghost small')}</div>
    <p class="jl-note">${esc(t.hint||'')}</p>${board(g)}${g.err?`<p class="jl-err" role="alert">${esc(g.err)}</p>`:''}${go}</section>`;
}
const tap=(op,data,label,inner,cls='',extra='')=>`<button type="button" class="${cls}" data-jl="${op}"${attrs(data)} aria-label="${esc(label)}"${extra}>${inner}</button>`;
function toolbar(list,cur,op='tool'){
  return `<div class="jl-tools" role="group" aria-label="Dụng cụ">${list.map(([id,e,l])=>`<button type="button" class="jl-tool${cur===id?' on':''}" data-jl="${op}" data-t="${id}" aria-pressed="${cur===id}"><span aria-hidden="true">${e}</span>${l}</button>`).join('')}</div>`;
}
function board(g){
  const pz=g.pz;
  if(g.task==='sweep')return `<div class="jl-yardgrid">${Array.from({length:pz.cells||12},(_,c)=>{const hp=g.hp[c];
      if(hp===undefined)return '<span class="jl-plot clean" aria-hidden="true"></span>';
      return hp>0?`<button type="button" class="jl-plot leaf hp${hp}" data-jl="sweep" data-c="${c}" aria-label="Đống lá, còn ${hp} lần quét">🍂</button>`
        :'<span class="jl-plot clean done" aria-label="Đã quét sạch">✨</span>';}).join('')}</div>`;
  if(STEPS[g.task]){
    const st=STEPS[g.task],art=h=>st.art[h.length];
    return toolbar(st.tools,g.tool)+`<div class="jl-road jl-${g.task}-row">${g.holes.map((h,i)=>tap('hole',{i},st.label(i,st.stage[h.length]),art(h),`jl-hole s${h.length}${h.length===st.tools.length?' full':''}`)).join('')}</div>`;
  }
  if(g.task==='rice')return `<div class="jl-trays">${pz.want.map((w,i)=>{const n=g.scoops[i];
      return `<div class="jl-tray${n===w?' ok':n>w?' over':''}"><small>Khay ${i+1} · cần <b>${w}</b> muỗng</small><button type="button" class="jl-plate" data-jl="scoop" data-i="${i}" aria-label="Thêm một muỗng cơm vào khay ${i+1}">${'🍚'.repeat(n)||'🍽️'}</button>
        <button type="button" class="jl-less" data-jl="less" data-i="${i}" aria-label="Bớt một muỗng ở khay ${i+1}"${n?'':' disabled'}>− bớt</button></div>`;}).join('')}</div>`;
  if(g.task==='paint')return `<div class="jl-wall" data-jl-wall="1">${Array.from({length:pz.cells},(_,c)=>{const dirty=pz.dirty.includes(c),on=g.painted.includes(c);
      return `<button type="button" class="jl-tile${dirty?on?' painted':' dirty':' clean'}" data-jl="paint" data-c="${c}" aria-label="${dirty?on?'Đã sơn':'Ô tường bẩn':'Ô tường sạch'}">${dirty&&!on?'〰️':''}</button>`;}).join('')}</div><p class="jl-why">Giữ ngón tay và kéo qua các ô để sơn nhanh.</p>`;
  if(g.task==='laundry'){
    const pegs=pz.pegs.map((c,p)=>{const i=g.hang.indexOf(p),it=i>=0?pz.items[i]:null;
      return tap('peg',{p},it?`Kẹp màu ${COLOR[c]?.[1]||c}, đã phơi ${CLOTH[it.k]?.[1]||''}`:`Kẹp màu ${COLOR[c]?.[1]||c}`,`<i style="--pg:${COLOR[c]?.[0]||'#999'}"></i>${it?`<span style="--cl:${COLOR[it.c]?.[0]}">${CLOTH[it.k]?.[0]||'👕'}</span>`:''}`,`jl-peg${it?' hung':''}`);}).join('');
    const basket=pz.items.map((it,i)=>g.hang[i]!==null?'':tap('cloth',{i},`Đồ giặt: ${CLOTH[it.k]?.[1]||''}, màu ${COLOR[it.c]?.[1]||''}`,
      `<span style="--cl:${COLOR[it.c]?.[0]}">${CLOTH[it.k]?.[0]||'👕'}</span>`,`jl-cloth${g.sel===i?' on':''}`,` aria-pressed="${g.sel===i}"`)).join('');
    return `<div class="jl-line" role="group" aria-label="Dây phơi">${pegs}</div><p class="jl-shelf-l">${g.sel!==null?'Rổ đồ giặt · giờ chọn kẹp cùng màu':'Rổ đồ giặt · chạm một món'}</p><div class="jl-basket">${basket||'<small>Phơi hết rồi</small>'}</div>`;
  }
  if(g.task==='mop')return `<div class="jl-floor">${pz.dirt.map((d,i)=>{const left=d-g.wipes[i];
      return d?tap('mop',{i},left>0?`Ô sàn bẩn, còn ${left} lần lau`:'Ô sàn đã sạch',left>0?'〰️'.repeat(left):'✨',`jl-tile2 d${Math.max(0,left)}`)
        :'<span class="jl-tile2 d0" aria-hidden="true"></span>';}).join('')}</div>`;
  if(g.task==='trash'){
    const items=pz.items.map((x,i)=>g.bins[i]?'':tap('junk',{i},TRASH[x]?.[1]||x,`<span aria-hidden="true">${TRASH[x]?.[0]||'❔'}</span><small>${esc(TRASH[x]?.[1]||x)}</small>`,`jl-junk${g.sel===i?' on':''}`,` aria-pressed="${g.sel===i}"`)).join('');
    const bins=Object.entries(BIN).map(([b,[e,l]])=>tap('bin',{b},`Thùng ${l}: ${g.bins.filter(x=>x===b).length} món`,`<span aria-hidden="true">${e}</span>${l}<small>${g.bins.filter(x=>x===b).length}</small>`,`jl-bin b-${b}`)).join('');
    return `<div class="jl-junks">${items||'<small>Phân loại xong rồi</small>'}</div><div class="jl-bins">${bins}</div>`;
  }
  if(g.task==='veg')return `<div class="jl-leaves">${Array.from({length:pz.leaves},(_,i)=>{const y=pz.yellow.includes(i),gone=g.picked.includes(i);
      return gone?'<span class="jl-leaf gone" aria-hidden="true"></span>':tap('leaf',{i},y?'Lá vàng':'Lá xanh',y?'🍂':'🌿',`jl-leaf${y?' yellow':''}`);}).join('')}</div>`;
  if(g.task==='chicken'){
    const tools=Object.entries(FEED).map(([id,[e,l]])=>[id,e,l]);
    return toolbar(tools,g.tool)+`<div class="jl-coop">${pz.want.map((w,i)=>{const f=g.fed[i];
      return tap('hen',{i},f?`Gà ${i+1}: đã ăn ${FEED[f]?.[1]||''}`:`Gà ${i+1} đang thèm ${FEED[w]?.[1]||''}`,`<span class="jl-think" aria-hidden="true">${f?'❤️':FEED[w]?.[0]||'❔'}</span><span aria-hidden="true">🐔</span>`,`jl-hen${f?' fed':''}`);}).join('')}</div>`;
  }
  if(g.task==='fix')return `<div class="jl-nails">${pz.nails.map((n,i)=>{const left=n-g.hits[i];
      return tap('nail',{i},left>0?`Đinh ${i+1}: còn nhô ${left} nấc`:`Đinh ${i+1}: đã vô hết`,`<span class="jl-nail-up" aria-hidden="true">${'▮'.repeat(Math.max(0,left))}</span><span aria-hidden="true">${left>0?'🔩':'✅'}</span>`,`jl-nail${left>0?'':' in'}`);}).join('')}</div>`;
  if(g.task==='ledger')return `<p class="jl-shelf-l">Kệ kho</p><div class="jl-stock" aria-label="Kệ kho: ${pz.pile.length} món">${pz.pile.map(k=>`<span aria-hidden="true">${STOCK[k]?.[0]||'📦'}</span>`).join('')}</div>
    <p class="jl-shelf-l">Sổ kiểm kho</p><div class="jl-count">${pz.kinds.map(k=>`<div class="jl-count-row"><span aria-hidden="true">${STOCK[k]?.[0]||''}</span><b>${esc(STOCK[k]?.[1]||k)}</b>
      ${tap('cnt',{k,d:-1},`Bớt một ${STOCK[k]?.[1]||k}`,'−','jl-step',g.counts[k]?'':' disabled')}<output>${g.counts[k]}</output>${tap('cnt',{k,d:1},`Thêm một ${STOCK[k]?.[1]||k}`,'+','jl-step')}</div>`).join('')}</div>`;
  if(g.task==='fold'){
    const i=Math.min(g.at,pz.cards.length-1),card=pz.cards[i],did=g.folds[i];
    const steps=card.map((f,k)=>`<li class="${k<did.length?'ok':k===did.length?'now':''}"><span aria-hidden="true">${FOLD[f]?.[0]||''}</span>${esc(FOLD[f]?.[1]||f)}</li>`).join('');
    return `<p class="jl-shelf-l">Tấm chăn ${i+1}/${pz.cards.length} · thẻ hướng dẫn</p><ol class="jl-card-steps">${steps}</ol>
      <div class="jl-blanket" style="--f:${did.length}" aria-hidden="true">🟦</div>${toolbar(Object.entries(FOLD).map(([id,[e,l]])=>[id,e,l]),null,'fold')}
      <p class="jl-why">Đã gấp xong ${g.folds.filter((f,k)=>f.length===pz.cards[k].length).length}/${pz.cards.length} tấm.</p>`;
  }
  const shelf=pz.nums.map((n,i)=>g.order.includes(i)?'<span class="jl-book gone" aria-hidden="true"></span>'
    :`<button type="button" class="jl-book" style="--bk:${BOOK_COLORS[i%BOOK_COLORS.length]}" data-jl="book" data-i="${i}" aria-label="Sách số ${n}"><b>${n}</b></button>`).join('');
  const sorted=g.order.map(i=>`<span class="jl-book small" style="--bk:${BOOK_COLORS[i%BOOK_COLORS.length]}"><b>${pz.nums[i]}</b></span>`).join('');
  return `<p class="jl-shelf-l">Kệ chưa xếp</p><div class="jl-shelf">${shelf}</div><p class="jl-shelf-l">Kệ đã xếp (nhỏ → lớn)</p><div class="jl-shelf done">${sorted||'<small>Chưa có cuốn nào</small>'}</div>`;
}
function shake(el){if(!el||reduce())return;el.classList.remove('jl-shake');void el.offsetWidth;el.classList.add('jl-shake');}
/** One move of a game, on the game's own state only (no page): '' when it went, else what to say and what to shake
 * ([text, selector]); a move that is fine but worth a word (an over-full tray) says it too. Node tests drive it
 * (tests/jail_games.mjs). */
export function step(g,op,data){
  const pz=g.pz,i=Number(data.i),no=(text,sel)=>[text,sel];
  if(op==='sweep'){const c=Number(data.c);if(g.hp[c]>0)g.hp[c]--;}
  else if(op==='tool')g.tool=data.t;
  else if(op==='hole'){const st=STEPS[g.task],h=g.holes[i],next=st?.tools[h?.length]?.[0];
    if(!next)return '';
    if(g.tool!==next)return no(st.say[next],`[data-jl="hole"][data-i="${i}"]`);
    h.push(next);}
  else if(op==='scoop'){g.scoops[i]=Math.min(5,g.scoops[i]+1);if(g.scoops[i]>pz.want[i])return [`Khay ${i+1} dư cơm rồi, bớt lại cho đúng phần nha.`,null];}
  else if(op==='less'){g.scoops[i]=Math.max(0,g.scoops[i]-1);}
  else if(op==='paint')paintOn(g,Number(data.c));
  else if(op==='book'){const left=pz.nums.map((n,k)=>[n,k]).filter(([,k])=>!g.order.includes(k)).sort((a,b)=>a[0]-b[0]);
    if(left[0]?.[1]!==i)return no('Chưa đúng thứ tự: tìm cuốn số nhỏ nhất còn lại.',`[data-jl="book"][data-i="${i}"]`);
    g.order.push(i);}
  else if(op==='cloth')g.sel=g.sel===i?null:i;
  else if(op==='peg'){const p=Number(data.p);
    if(g.sel===null)return no('Chọn một món trong rổ trước đã nha.','.jl-basket');
    if(g.hang.includes(p))return no('Kẹp này có đồ rồi.',`[data-jl="peg"][data-p="${p}"]`);
    if(pz.pegs[p]!==pz.items[g.sel].c)return no(`Món này màu ${COLOR[pz.items[g.sel].c]?.[1]||''}, tìm kẹp cùng màu nha.`,`[data-jl="peg"][data-p="${p}"]`);
    g.hang[g.sel]=p;g.sel=null;}
  else if(op==='mop'){if(g.wipes[i]>=pz.dirt[i])return no('Ô này sạch rồi, lau dư phí nước nha.',`[data-jl="mop"][data-i="${i}"]`);g.wipes[i]++;}
  else if(op==='junk')g.sel=g.sel===i?null:i;
  else if(op==='bin'){
    if(g.sel===null)return no('Chạm một món rác trước, rồi chọn thùng.','.jl-junks');
    const it=TRASH[pz.items[g.sel]];
    if(it&&it[2]!==data.b)return no(`Thùng ${BIN[data.b]?.[1]||''} không nhận ${it[1]} đâu, nghĩ lại nha.`,`[data-jl="bin"][data-b="${data.b}"]`);
    g.bins[g.sel]=data.b;g.sel=null;}
  else if(op==='leaf'){if(!pz.yellow.includes(i))return no('Lá xanh còn ăn được, giữ lại nha.',`[data-jl="leaf"][data-i="${i}"]`);if(!g.picked.includes(i))g.picked.push(i);}
  else if(op==='hen'){if(g.fed[i])return '';
    if(pz.want[i]!==g.tool)return no(`Gà ${i+1} đang thèm ${FEED[pz.want[i]]?.[1]||''}, chọn đúng món nha.`,`[data-jl="hen"][data-i="${i}"]`);
    g.fed[i]=g.tool;}
  else if(op==='nail'){if(g.hits[i]>=pz.nails[i])return no('Đinh vô hết rồi, gõ nữa là cong đinh đó!',`[data-jl="nail"][data-i="${i}"]`);g.hits[i]++;}
  else if(op==='cnt'){const k=data.k;if(k in g.counts)g.counts[k]=Math.max(0,Math.min(30,g.counts[k]+Number(data.d)));}
  else if(op==='fold'){const at=Math.min(g.at,pz.cards.length-1),did=g.folds[at],want=pz.cards[at][did.length];
    if(!want)return '';
    if(data.t!==want)return no(`Thẻ ghi bước tiếp theo là “${FOLD[want]?.[1]||want}”.`,'.jl-blanket');
    did.push(data.t);if(did.length===pz.cards[at].length&&g.at<pz.cards.length-1)g.at++;}
  return '';
}
function play(op,data){
  const g=S.game;if(!g)return;
  const r=step(g,op,data);g.err=r?r[0]:'';render();
  if(r&&r[1])shake(S.dlg.querySelector(r[1]));
}
/** The games' pure parts, for the node tests. */
export const games={fresh,finished,answer,precheck,step,TRASH,FEED,STOCK,FOLD,COLOR,STEPS};
/* 🎨 the wall paints under a dragged finger too */
let painting=false;
function paintOn(g,c){if(!g||g.task!=='paint'||g.painted.includes(c)||!g.pz.dirty.includes(c))return false;g.painted.push(c);return true;}
function paintCell(c){return paintOn(S.game,c);}
function paintDown(e){if(!S.game||S.game.task!=='paint'||!e.target.closest?.('[data-jl-wall]'))return;painting=true;
  const up=()=>{painting=false;removeEventListener('pointerup',up);removeEventListener('pointercancel',up);};addEventListener('pointerup',up);addEventListener('pointercancel',up);}
function paintMove(e){
  if(!painting)return;
  const el=document.elementFromPoint(e.clientX,e.clientY)?.closest?.('[data-jl="paint"]');
  if(el&&paintCell(Number(el.dataset.c))){el.classList.remove('dirty');el.classList.add('painted');el.textContent='';if(finished(S.game))render();}
}

/* ---- server calls ---- */
async function command(action,payload){
  S.busy=true;render();
  try{return await S.env.api.command(action,payload);}
  catch(e){S.flash={text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};if(S.game)S.game.err=e.message||'';return null;}
  finally{S.busy=false;}
}
async function start(task){
  S.flash=null;
  const r=await command('jail_task_start',{task});
  if(r?.jail?.pz){S.game=fresh(task,r.jail.pz,r.jail.ready);if(S.mapOn)S.panel='task:'+task;}
  render();if(S.game){S.dlg.scrollTop=0;S.dlg.querySelector('.jl-panel')?.scrollTo?.(0,0);}
}
async function done(){
  const g=S.game;if(!g||!finished(g))return;
  const why=precheck(g);if(why){g.err=why;render();shake(S.dlg.querySelector('.jl-count'));return;}
  const r=await command('jail_task_done',{task:g.task,ans:answer(g)});
  if(r?.jail?.ok){S.game=null;S.flash={text:r.message||'Xong việc rồi.',kind:'good'};S.map?.redraw();}
  render();
}
async function endDay(){
  if(!S.sure){S.sure=true;render();setTimeout(()=>{if(S.sure){S.sure=false;render();}},4000);return;}
  S.sure=false;S.flash=null;
  const j=J();const r=await command('jail_end',{day:j?.day});
  if(r){S.flash={text:[r.message,...(r.effects||[])].filter(Boolean).join(' '),kind:'good'};}
  if(J())render();
}
async function askBail(){
  const {api}=S.env;S.busy=true;S.flash=null;render();
  try{
    const d=await api.json('/api/marriage/jail_ask',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify({})});
    if(d.state&&typeof d.revision==='number')api.accept({state:d.state,revision:d.revision});
    S.flash={text:d.message||'Đã nhờ bạn bè.',kind:'good'};
  }catch(e){S.flash={text:e.message||'Chưa nhờ được. Thử lại nhé.',kind:'bad'};}
  finally{S.busy=false;render();}
}
function onClick(op,data,el){
  if(S.busy&&op!=='close'&&op!=='shut')return;
  switch(op){
    case'close':S.dlg.close();return;
    case'start':start(data.task);return;
    case'back':S.game=null;render();return;
    case'done':done();return;
    case'end':endDay();return;
    case'ask':askBail();return;
    case'go':S.dlg.close();S.env.act?.(data.to);return;
    case'spot':if(S.map)S.map.go(data.id);else{S.panel=data.id;render();}return;   // walk there; its panel opens on arrival
    case'shut':S.panel=null;S.sure=false;S.map?.clearAt();render();return;
    default:play(op,data);
  }
}
