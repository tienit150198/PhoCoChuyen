/** 🚔 Trại tạm giữ (game/jail.py): the player's own screen while they serve a few in-game days.
 *
 * Its own dialog (like the Chợ đen's), opened by itself when api.state.jail appears (app.js calls sync() on every
 * state) and with data-action="jail"; closing it leaves a small chip ("🚔 Trại · còn N ngày") that opens it again.
 * The cell and the yard, the days left, today's three công ích tasks as small tap/drag games, "🤝 Nhờ bạn bảo lãnh"
 * (POST /api/marriage/jail_ask: every friend gets a request, a friend pays) and "🌙 Hết một ngày trong trại"
 * (jail_end: the life day moves on without work). Every rule and number is the server's: the tasks' layouts come in
 * the state (pz), the answers are checked there (jail_task_done), the day's end waits for `ready`. No odds anywhere.
 * While jailed the page asks for the state now and then (a friend's bail lands on the server). Styles: /css/jail.css. */
import {icon,escapeHTML as esc} from '../icons.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const S={env:null,dlg:null,chip:null,id:null,game:null,busy:false,flash:null,skew:0,tick:0,poll:0,sure:false};
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
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium jl-sheet';d.setAttribute('aria-labelledby','jl-title');
  d.innerHTML='<div class="jl-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    const el=e.target.closest('[data-jl]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.jl,el.dataset,el);
  });
  d.addEventListener('pointerdown',paintDown);
  d.addEventListener('pointermove',paintMove);
  d.addEventListener('close',()=>{clearInterval(S.tick);S.tick=0;S.flash=null;chip();});
  S.dlg=d;return d;
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
  clearInterval(S.tick);S.tick=setInterval(tick,1000);
}
/** Every state (app.js): open on a new sentence, redraw, say goodbye when it is over. */
export function sync(env){
  S.env=env;
  const j=J();
  if(j){
    if(typeof j.now==='number')S.skew=j.now*1000-Date.now();
    if(S.id!==j.id){S.id=j.id;S.game=null;openJail(env);}
    else if(S.dlg?.open&&!S.busy)render();
    if(S.game&&!j.tasks.some(t=>t.id===S.game.task&&!t.done))S.game=null;
    chip();poll(true);
    return;
  }
  if(S.id){S.id=null;S.game=null;poll(false);if(S.dlg?.open)S.dlg.close();chip();env.toast?.('🎉 Bạn đã ra khỏi trại tạm giữ. Về nhà thôi!','good');}
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
    if(left<=0){if(el.dataset.done!=='1'){el.dataset.done='1';render();}return;}
    el.textContent=mmss(left);
  });
}

/* ---- the page ---- */
function render(){
  if(!S.dlg)return;
  const root=S.dlg.querySelector('.jl-root'),y=S.dlg.scrollTop;
  root.innerHTML=page();
  S.dlg.scrollTop=y;
}
const flash=()=>`<p class="jl-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
function head(j){
  return `<header class="jl-head"><span class="jl-badge" aria-hidden="true">🚔</span><div class="grow"><span class="eyebrow">${esc(j?.why_text||'Trại tạm giữ')}</span><h2 id="jl-title">Trại tạm giữ phường</h2></div>
    <button class="icon-btn" type="button" data-jl="close" aria-label="Thu nhỏ">${icon('x',21)}</button></header>`;
}
function page(){
  const j=J();
  if(!j)return head(null)+`<div class="sheet-body jl-body"><p>Bạn không ở trại tạm giữ.</p>${btn('Đóng','close',{},'primary full')}</div>`;
  if(S.game)return head(j)+`<div class="sheet-body jl-body">${flash()}${gameView(j)}</div>`;
  return head(j)+`<div class="sheet-body jl-body">${scene(j)}${flash()}${tasks(j)}${actions(j)}${rules()}</div>`;
}
function scene(j){
  const dots=Array.from({length:j.days},(_,i)=>`<i class="${i<j.days-j.left?'on':''}"></i>`).join('');
  return `<section class="jl-scene" aria-label="Phòng giam và sân trại"><div class="jl-cell"><div class="jl-window" aria-hidden="true"><span class="jl-sun"></span></div>
      <div class="jl-bars" aria-hidden="true"></div><div class="jl-bunk" aria-hidden="true"><span>🛏️</span></div><div class="jl-me" aria-hidden="true">🧑</div></div>
    <div class="jl-yard" aria-hidden="true"><span class="jl-tree">🌳</span><span class="jl-flag">🚩</span><span class="jl-guard">👮</span><span class="jl-broom">🧹</span></div>
    <div class="jl-days" role="status"><b>Còn ${j.left} ngày</b><small>Ngày ${j.day} trong trại · án ${j.days} ngày</small><span class="jl-dots" aria-hidden="true">${dots}</span></div></section>`;
}
function tasks(j){
  const done=j.tasks.filter(t=>t.done).length,all=done===j.tasks.length;
  const rows=j.tasks.map(t=>`<li class="jl-task${t.done?' done':''}"><span class="jl-ic" aria-hidden="true">${t.emoji}</span><span class="grow"><b>${esc(t.name)}</b><small>${esc(t.hint)}</small></span>
      ${t.done?'<span class="tag green">Xong ✓</span>':btn('Làm','start',{task:t.id},'primary small',S.busy?' disabled':'')}</li>`).join('');
  const note=j.left<=1?'Còn một ngày: hết ngày là được về.':all?'Đủ ba việc rồi: hết ngày này được tính hai ngày.':'Làm đủ ba việc công ích hôm nay: hết ngày được tính hai ngày.';
  return `<section class="jl-card"><h3>🧹 Công ích hôm nay <small>${done}/${j.tasks.length}</small></h3><ul class="jl-tasks">${rows}</ul><p class="jl-note">${note}</p></section>`;
}
function actions(j){
  const wait=(j.ready*1000-nowMs())/1000,ask=j.ask_next?(j.ask_next*1000-nowMs())/1000:0;
  const end=wait>0?btn(`🌙 Hết ngày sau <span data-jl-count="day">${mmss(wait)}</span>`,'end',{},'cream big full',' disabled')
    :btn(S.sure?'🌙 Chắc chưa? Hết ngày nhé':'🌙 Hết một ngày trong trại','end',{},'primary big full',S.busy?' disabled':'');
  const bail=ask>0?btn(`🤝 Đã nhờ bạn bè · nhờ lại sau <span data-jl-count="ask">${mmss(ask)}</span>`,'ask',{},'ghost full',' disabled')
    :btn(`🤝 Nhờ bạn bảo lãnh`,'ask',{},'cream full',S.busy?' disabled':'');
  return `<section class="jl-card jl-go">${end}<p class="jl-why">Hết ngày: qua một ngày sống, không đi làm. Tiền phòng vẫn tính, cơm trại miễn phí.</p>
    ${bail}<p class="jl-why">Bạn bè bảo lãnh thì trả ${xu(j.bail)} từ ví của họ, bạn được về ngay.</p></section>`;
}
function rules(){
  return `<section class="jl-card jl-rules"><h3>📋 Nội quy trại</h3><ul>
      <li><span aria-hidden="true">🚫</span> Không đi làm, không vào chợ đen, không mua sắm, không đi chơi xa.</li>
      <li><span aria-hidden="true">✅</span> Vẫn nhắn tin, xem bạn bè, đọc sách, học bài, chỉnh cài đặt và góp ý được.</li></ul>
    <div class="jl-links">${btn('💬 Nhắn tin','go',{to:'liveChat'},'ghost small')}${btn('👥 Bạn bè','go',{to:'friends'},'ghost small')}${btn('⚙️ Cài đặt','go',{to:'settings'},'ghost small')}</div></section>`;
}

/* ---- the công ích games: tap and drag, the answer checked by the server ---- */
const TITLE={sweep:'🧹 Quét sân trại',plant:'🌱 Trồng cây ven đường',rice:'🍚 Phụ bếp chia cơm',paint:'🎨 Sơn lại tường',books:'📚 Xếp sách thư viện trại'};
const BOOK_COLORS=['#c0533a','#3a7bc0','#3aa060','#c09a3a','#8a4ac0','#c03a7b'];
function fresh(task,pz,ready){
  const g={task,pz,ready,err:''};
  if(task==='sweep')g.hp=Object.fromEntries(pz.piles.map(c=>[c,3]));
  if(task==='plant'){g.tool='dig';g.holes=Array.from({length:pz.holes},()=>[]);}
  if(task==='rice')g.scoops=pz.want.map(()=>0);
  if(task==='paint')g.painted=[];
  if(task==='books')g.order=[];
  return g;
}
function finished(g){
  if(g.task==='sweep')return Object.values(g.hp).every(n=>n<=0);
  if(g.task==='plant')return g.holes.every(h=>h.length===3);
  if(g.task==='rice')return g.scoops.every((n,i)=>n===g.pz.want[i]);
  if(g.task==='paint')return g.pz.dirty.every(c=>g.painted.includes(c));
  return g.order.length===g.pz.nums.length;
}
function answer(g){
  if(g.task==='sweep')return {swept:Object.keys(g.hp).map(Number)};
  if(g.task==='plant')return {steps:g.holes};
  if(g.task==='rice')return {scoops:g.scoops};
  if(g.task==='paint')return {cells:g.painted.filter(c=>g.pz.dirty.includes(c))};
  return {order:g.order};
}
function gameView(j){
  const g=S.game,t=j.tasks.find(x=>x.id===g.task)||{};
  const ok=finished(g),wait=(g.ready*1000-nowMs())/1000;
  const go=!ok?btn('Xong','done',{},'primary big full',' disabled'):wait>0?btn(`Cán bộ đang kiểm tra… <span data-jl-count="task">${mmss(wait)}</span>`,'done',{},'cream big full',' disabled')
    :btn('✅ Báo cán bộ: xong rồi','done',{},'primary big full',S.busy?' disabled':'');
  return `<section class="jl-card jl-game jl-${g.task}"><div class="jl-game-head"><h3>${TITLE[g.task]||esc(t.name||'')}</h3>${btn('‹ Để sau','back',{},'ghost small')}</div>
    <p class="jl-note">${esc(t.hint||'')}</p>${board(g)}${g.err?`<p class="jl-err" role="alert">${esc(g.err)}</p>`:''}${go}</section>`;
}
function board(g){
  const pz=g.pz;
  if(g.task==='sweep')return `<div class="jl-yardgrid">${Array.from({length:12},(_,c)=>{const hp=g.hp[c];
      if(hp===undefined)return '<span class="jl-plot clean" aria-hidden="true"></span>';
      return hp>0?`<button type="button" class="jl-plot leaf hp${hp}" data-jl="sweep" data-c="${c}" aria-label="Đống lá, còn ${hp} lần quét">🍂</button>`
        :'<span class="jl-plot clean done" aria-label="Đã quét sạch">✨</span>';}).join('')}</div>`;
  if(g.task==='plant'){
    const tools=[['dig','⛏️','Đào hố'],['seed','🌰','Gieo hạt'],['water','💧','Tưới nước']];
    const art=h=>h.length===0?'🟫':h.length===1?'🕳️':h.length===2?'🌰':'🌱';
    return `<div class="jl-tools" role="group" aria-label="Dụng cụ">${tools.map(([id,e,l])=>`<button type="button" class="jl-tool${g.tool===id?' on':''}" data-jl="tool" data-t="${id}" aria-pressed="${g.tool===id}"><span aria-hidden="true">${e}</span>${l}</button>`).join('')}</div>
      <div class="jl-road">${g.holes.map((h,i)=>`<button type="button" class="jl-hole s${h.length}" data-jl="hole" data-i="${i}" aria-label="Hố ${i+1}: ${['chưa đào','đã đào','đã gieo hạt','đã tưới, cây lên rồi'][h.length]}">${art(h)}</button>`).join('')}</div>`;
  }
  if(g.task==='rice')return `<div class="jl-trays">${pz.want.map((w,i)=>{const n=g.scoops[i];
      return `<div class="jl-tray${n===w?' ok':n>w?' over':''}"><small>Khay ${i+1} · cần <b>${w}</b> muỗng</small><button type="button" class="jl-plate" data-jl="scoop" data-i="${i}" aria-label="Thêm một muỗng cơm vào khay ${i+1}">${'🍚'.repeat(n)||'🍽️'}</button>
        <button type="button" class="jl-less" data-jl="less" data-i="${i}" aria-label="Bớt một muỗng ở khay ${i+1}"${n?'':' disabled'}>− bớt</button></div>`;}).join('')}</div>`;
  if(g.task==='paint')return `<div class="jl-wall" data-jl-wall="1">${Array.from({length:pz.cells},(_,c)=>{const dirty=pz.dirty.includes(c),on=g.painted.includes(c);
      return `<button type="button" class="jl-panel${dirty?on?' painted':' dirty':' clean'}" data-jl="paint" data-c="${c}" aria-label="${dirty?on?'Đã sơn':'Ô tường bẩn':'Ô tường sạch'}">${dirty&&!on?'〰️':''}</button>`;}).join('')}</div><p class="jl-why">Giữ ngón tay và kéo qua các ô để sơn nhanh.</p>`;
  const shelf=pz.nums.map((n,i)=>g.order.includes(i)?'<span class="jl-book gone" aria-hidden="true"></span>'
    :`<button type="button" class="jl-book" style="--bk:${BOOK_COLORS[i%BOOK_COLORS.length]}" data-jl="book" data-i="${i}" aria-label="Sách số ${n}"><b>${n}</b></button>`).join('');
  const sorted=g.order.map(i=>`<span class="jl-book small" style="--bk:${BOOK_COLORS[i%BOOK_COLORS.length]}"><b>${pz.nums[i]}</b></span>`).join('');
  return `<p class="jl-shelf-l">Kệ chưa xếp</p><div class="jl-shelf">${shelf}</div><p class="jl-shelf-l">Kệ đã xếp (nhỏ → lớn)</p><div class="jl-shelf done">${sorted||'<small>Chưa có cuốn nào</small>'}</div>`;
}
function shake(el){if(!el||reduce())return;el.classList.remove('jl-shake');void el.offsetWidth;el.classList.add('jl-shake');}
function play(op,data,el){
  const g=S.game;if(!g)return;g.err='';
  if(op==='sweep'){const c=Number(data.c);if(g.hp[c]>0)g.hp[c]--;}
  else if(op==='tool')g.tool=data.t;
  else if(op==='hole'){const h=g.holes[Number(data.i)],next=['dig','seed','water'][h.length];
    if(!next)return;
    if(g.tool!==next){g.err=next==='dig'?'Đào hố trước đã nha.':next==='seed'?'Hố đào rồi, gieo hạt đi.':'Gieo rồi, giờ tưới nước.';render();shake(S.dlg.querySelector(`[data-jl="hole"][data-i="${data.i}"]`));return;}
    h.push(next);}
  else if(op==='scoop'){const i=Number(data.i);g.scoops[i]=Math.min(5,g.scoops[i]+1);if(g.scoops[i]>g.pz.want[i])g.err=`Khay ${i+1} dư cơm rồi, bớt lại cho đúng phần nha.`;}
  else if(op==='less'){const i=Number(data.i);g.scoops[i]=Math.max(0,g.scoops[i]-1);}
  else if(op==='paint')paintCell(Number(data.c));
  else if(op==='book'){const i=Number(data.i),left=g.pz.nums.map((n,k)=>[n,k]).filter(([,k])=>!g.order.includes(k)).sort((a,b)=>a[0]-b[0]);
    if(left[0]?.[1]!==i){g.err='Chưa đúng thứ tự: tìm cuốn số nhỏ nhất còn lại.';render();shake(S.dlg.querySelector(`[data-jl="book"][data-i="${i}"]`));return;}
    g.order.push(i);}
  render();
}
/* 🎨 the wall paints under a dragged finger too */
let painting=false;
function paintCell(c){const g=S.game;if(!g||g.task!=='paint'||g.painted.includes(c)||!g.pz.dirty.includes(c))return false;g.painted.push(c);return true;}
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
  if(r?.jail?.pz){S.game=fresh(task,r.jail.pz,r.jail.ready);}
  render();if(S.game)S.dlg.scrollTop=0;
}
async function done(){
  const g=S.game;if(!g||!finished(g))return;
  const r=await command('jail_task_done',{task:g.task,ans:answer(g)});
  if(r?.jail?.ok){S.game=null;S.flash={text:r.message||'Xong việc rồi.',kind:'good'};}
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
  if(S.busy&&op!=='close')return;
  switch(op){
    case'close':S.dlg.close();return;
    case'start':start(data.task);return;
    case'back':S.game=null;render();return;
    case'done':done();return;
    case'end':endDay();return;
    case'ask':askBail();return;
    case'go':S.dlg.close();S.env.act?.(data.to);return;
    default:play(op,data,el);
  }
}
