/** Homestay Mây Đà Lạt — front desk, 7-day room calendar, app-order inbox, housekeeping workbench,
 *  lost-and-found calls and the surprises that walk in at the counter. */
const PAN_SCALE=24;   // seconds shown on the frying-pan bar
const AIR_SCALE=120;  // seconds shown on the window-airing bar
import {reqList} from '../ui-kit.js';
import {stepRows,nextHint,stepCta,finalGo,pending,firstTime,todoAttrs,todoArrow,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {cashPanel,changeStep,changePayload,tray,tillActions} from './till.js';
import {restockGo} from '../v4/restock.js';
import {tomorrowCard} from './tomorrow_kit.js';
const JOB_ICON={checkin:'🔑',checkout:'🧾',breakfast:'🍳',booking:'📅',recommend:'🗺️',claim:'📞'};
const STATUS={clean:['Sạch','green'],dirty:['Cần dọn','amber'],occupied:['Có khách','blue'],maintenance:['Bảo trì','danger']};
const CELL={occ:'🛏️',book:'📌',maint:'🔧',free:''};
const MOOD_EMOJI={'Rất vui':'😊','Vui vẻ':'🙂','Tạm ổn':'😐','Không vui':'😟'};
const EGG_LABEL={raw:'sống',runny:'lòng đào',well:'chín kỹ',burnt:'cháy'};
const CLAIM_CHOICES=[['give','🎁 Giao đồ cho người gọi','Giao món đồ cho người đang gọi? Nếu không phải chủ đồ, nhà phải chịu trách nhiệm.'],
  ['channel','🧾 Nhắn người đặt phòng xác nhận trước','Nhắn qua kênh đặt phòng để người đặt xác nhận rồi mới gửi đồ?'],
  ['deny','🙅 Từ chối giao đồ','Từ chối giao đồ cho người gọi này?']];

const roomInfo=(x,id)=>x.cc.rooms.find(r=>r.id===id)||{id,name:id,emoji:'🚪',cap:0,beds:'',unlock:1};
const itemInfo=(x,id)=>(x.content.inventory?.items?.homestay||[]).find(i=>i.id===id)||{name:id,emoji:'•'};
const counted=(x,adults,kids)=>adults+(kids||[]).filter(k=>k>=x.cc.kid_free_age).length;
const price=(x,key,base)=>x.room.life?.prices?.[key]??base;
const rateInfo=(x,id)=>(x.cc.rates||[]).find(r=>r.id===id)||{id,name:'Giá niêm yết',short:'giá gốc',pct:100,emoji:'🏷️'};
const deskOpen=x=>!!x.room.data?.desk?.ev;
const airOf=x=>x.room.data?.air||x.cc.air||{damp:15,cold:90};
const cmdAttr=(x,command,payload)=>`data-command="${x.esc(command)}" data-payload="${x.esc(JSON.stringify(payload))}"`;
/* Supplies a step takes, by the server's own count (room.inventory.stock = what need()/take() see). */
/** What the shelf lacks for `need` ({item: qty}): [{id, need, have}], [] when enough. */
const lacks=(x,need)=>Object.entries(need).filter(([k,q])=>q>0&&x.stock(k)<q).map(([id,q])=>({id,need:q,have:x.stock(id)}));
/** The step the shelf cannot supply becomes the way to supply it: "📦 Nhập mì ly · thiếu 2" (an arrived crate is
 * opened first, an order on the way shows when it comes). A guide `go`; lackBtn is the same tap as a button. */
function lackGo(x,short){
  const g=restockGo(x.room,short,{task:x.room.active_task||null}),s=short[0],name=x.esc(itemInfo(x,s.id).name.toLowerCase());
  return {...g,label:g.full||g.coming?g.label:g.ready?`📦 Mở thùng ${name} lên kệ`:`📦 Nhập ${name} · thiếu ${s.need-s.have}`};
}
const goAttrs=(x,g)=>`data-action="${x.esc(g.act)}"${Object.entries(g.data||{}).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}`;
const lackBtn=(x,short,style='small primary')=>{const g=lackGo(x,short);return x.button(g.label,g.act,g.data||{},style+' hs-lack');};
/** What one housekeeping step takes (homestay.py _clean): its own supplies, the minibar's instant noodles on the
 * amenity step, and a second bath kit when the amenities go in before the bathroom is scrubbed (one gets wet). */
const hkNeed=(room,s)=>{const use={...(s.use||{})};if(s.id==='amenity'){if(room.mini)use.noodles=room.mini;if(room.hk&&!(room.hk.done||[]).includes('bath'))use.soap_kit=2;}return use;};
const carBtn=(x,label,action,data={},cls='',extra='')=>`<button type="button" class="${cls}" data-action="car:${action}"${Object.entries(data).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}${extra}>${label}</button>`;
/* A section whose open/closed state survives re-renders (x.ui.open[key]); `def` is the state before the player touches it. */
function panel(x,key,head,body,def=false,cls=''){
  const open=(x.ui.open||{})[key]??def;
  return `<section class="hs-panel ${cls} ${open?'open':''}">${carBtn(x,`<span class="grow">${head}</span><i aria-hidden="true">${open?'▴':'▾'}</i>`,'fold',{key,open:open?'1':''},'hs-panel-head',` aria-expanded="${open}"`)}${open?`<div class="hs-panel-body">${body}</div>`:''}</section>`;
}

function checklist(x,rows){
  // A row may carry a 4th item, a guide.js `go`: an open row then jumps to (or does) its step.
  return `<ul class="checklist">${rows.map(([ok,label,note,go])=>{const s={ok,go};return `<li class="${ok===true?'ok':ok===false?'bad':''}${todoAttrs(s)?' gd-todo':''}"${todoAttrs(s)}><span>${ok===true?'✓':ok===false?'✗':'○'}</span>${x.esc(label)}${note?`<small>${x.esc(note)}</small>`:''}${todoArrow(s)}</li>`;}).join('')}</ul>`;
}
function selection(x,t){
  if(x.ui.selTask!==t.id){x.ui.selTask=t.id;x.ui.sel=[];}
  return x.ui.sel;
}
function step(n,title,done,body){
  return `<section class="hs-step-card ${done?'done':''}"><h4 class="section-title"><span class="hs-num">${done?'✓':n}</span>${title}</h4>${body}</section>`;
}
/* A run of step cards, phone-short: only the step in hand is open. A finished card is one line that
 * unfolds on tap (x.ui.open); with `seq` the cards after the current one are one muted line each
 * (their controls only work once the earlier steps are done). cards: [{n,title,done,body,keep}],
 * keep = stays open when done (its result is needed by the step in hand). */
function stepRun(x,cards,{seq=false}={}){
  const list=cards.filter(Boolean),cur=list.findIndex(c=>!c.done);
  return list.map((c,i)=>{
    if(c.done&&!c.keep){
      const key='st'+i,open=!!(x.ui.open||{})[key];
      return `<section class="hs-step-card done folded">${carBtn(x,`<span class="hs-num">✓</span><span class="grow">${c.title}</span><i aria-hidden="true">${open?'▴':'▾'}</i>`,'fold',{key,open:open?'1':''},'hs-step-head',` aria-expanded="${open}"`)}${open?`<div class="hs-step-body">${c.body}</div>`:''}</section>`;
    }
    if(seq&&cur>=0&&i>cur)return `<section class="hs-step-card later" aria-disabled="true"><h4 class="section-title"><span class="hs-num">${c.n}</span>${c.title}</h4></section>`;
    return step(c.n,c.title,c.done,c.body);
  }).join('');
}
function bar(kind,start,zones,scale){
  return `<div class="hs-timer ${kind}" data-hs-timer="${kind}" data-start="${start||''}">
    <div class="hs-track">${zones.map(([cls,a,b])=>`<i class="zone ${cls}" style="left:${a/scale*100}%;width:${(b-a)/scale*100}%"></i>`).join('')}<b class="fill"></b></div>
    <small class="hs-timer-label">${start?'…':kind==='pan'?'Chảo đang trống':'Cửa sổ đang đóng'}</small></div>`;
}
const bubble=(x,who,text)=>`<div class="hs-bubble"><b>${x.esc(who)}</b> “${x.esc(text)}”</div>`;

/* ---------------------------------------------------------------- the one step that matters now (only it gets the primary colour) */
function focus(t,x){
  if(!t.known)return 'ask';
  const n=t.needs;
  if(t.job==='checkin'){const ci=t.ci;if(!ci.verified)return '';if(!ci.ids)return 'ids';if(!ci.counted)return 'count';if(!ci.extra)return '';if(!ci.rooms.length)return 'assign';if(n.cold&&!ci.heater)return 'heater';return 'welcome';}
  if(t.job==='checkout'){if(!t.checked)return 'inspect';if(t.check?.lost&&!t.returned)return 'return';return 'settle';}
  if(t.job==='breakfast'){
    const tr=t.tray,want=t.eggs_fix||n.eggs||{};
    if(tr.pan)return 'plate';
    if(tr.eggs.includes('raw'))return 'toss';
    if(tr.eggs.length<(want.runny||0)+(want.well||0))return 'egg';
    return ['bread','milk','coffee'].some(k=>(tr[k]||0)<(n[k]||0))?'':'serve';
  }
  if(t.job==='booking')return t.hold.length?'book':'hold';
  if(t.job==='claim')return '';
  return 'advise';
}
const st=(t,x,key,alt='ghost')=>focus(t,x)===key?'primary':alt;

/* ---------------------------------------------------------------- the day, the counter */
function todayChip(x){
  const d=x.room.data||{},m=d.mod;if(!m)return '';
  const rv=d.rating_view,tr=rv?.trend||0;
  const spark=rv?.days?.length>2?`<span class="hs-spark" aria-hidden="true">${rv.days.map(([day,v])=>`<i style="height:${Math.max(12,(v-10)/40*100)}%" title="Ngày ${day}: ${(v/10).toFixed(1)}"></i>`).join('')}</span>`:'';
  const score=d.score!=null?`<span class="hs-score" title="Điểm trung bình trên app đặt phòng">${spark}⭐ ${Number(d.score).toFixed(1)} trên app${tr?` <small class="${tr>0?'hs-up':'hs-down'}">${tr>0?'↑':'↓'}${Math.abs(tr).toFixed(1)}</small>`:''}${rv?.featured?' <small class="hs-up">· nổi bật</small>':''}</span>`:'';
  return `<p class="hs-today"><span aria-hidden="true">${x.esc(m.emoji)}</span> <b>Hôm nay: ${x.esc(m.title)}</b> <small>${x.esc(m.text)}</small>${score}</p>`;
}
function todayLine(x){
  const d=x.room.data||{},m=d.mod;if(!m)return '';
  const open=!!(x.ui.open||{}).today,rv=d.rating_view,tr=rv?.trend||0;
  const score=d.score!=null?`<span class="hs-score">⭐ ${Number(d.score).toFixed(1)}${tr?` <small class="${tr>0?'hs-up':'hs-down'}">${tr>0?'↑':'↓'}${Math.abs(tr).toFixed(1)}</small>`:''}</span>`:'';
  return `<div class="hs-todayline ${open?'open':''}">${carBtn(x,`<span aria-hidden="true">${x.esc(m.emoji)}</span> <b class="grow">Hôm nay: ${x.esc(m.title)}</b>${score}<i aria-hidden="true">${open?'▴':'▾'}</i>`,'fold',{key:'today',open:open?'1':''},'hs-step-head',` aria-expanded="${open}"`)}${open?todayChip(x):''}</div>`;
}
function deskCard(x){
  const ev=x.room.data?.desk?.ev;if(!ev)return '';
  const who=x.npc(ev.npc);
  const opts=ev.options.map(o=>`<button type="button" class="btn ghost hs-opt" ${cmdAttr(x,'hs_desk',{option:o.id})} ${o.cost>x.room.money?'disabled':''}><b>${x.esc(o.label)}</b>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}</button>`).join('');
  return `<section class="hs-desk ${x.esc(ev.tone||'')}" role="alert" aria-live="assertive"><div class="hs-desk-head"><span class="hs-desk-emoji" aria-hidden="true">${x.esc(ev.emoji)}</span><div class="grow"><small>CHUYỆN Ở QUẦY</small><h3>${x.esc(ev.title)}</h3></div>${x.portrait(who,40)}</div>
    <p>${x.esc(ev.text)}</p><div class="hs-opts">${opts}</div></section>`;
}
function lastDesk(x){const l=x.room.data?.desk?.last;if(!l||l.day!==x.room.day)return '';return `<p class="hs-last ${l.good===true?'good':l.good===false?'bad':''}" aria-live="polite"><span aria-hidden="true">${x.esc(l.emoji)}</span> <b>${x.esc(l.title)}:</b> ${x.esc(l.outcome)}</p>`;}
function foot(x){
  const d=x.room.data||{},busy=deskOpen(x);
  return `<p class="row wrap hs-foot">${x.cmd(d.safe_today?'✅ Đã ký sổ an toàn hôm nay':'🧯 Kiểm tra an toàn & ký sổ','hs_safety',{},'ghost small',!!d.safe_today||busy)}${x.button('📦 Kho & nhập hàng','inventory',{},'ghost small')}</p>`;
}
function rules(x){return `<details class="hs-rules fold gd-rules"><summary>📜 Quy tắc</summary><ul>${(x.cc.rules||[]).map(r=>`<li>${x.esc(r)}</li>`).join('')}</ul></details>`;}

/* ---------------------------------------------------------------- app orders (OTA inbox) */
const pendingOrders=x=>(x.room.data?.ota||[]).filter(o=>o.status==='new');
const DONE=['completed','cancelled','referred'];
function waiting(x,skip=''){
  const list=(x.room.tasks||[]).filter(t=>t.job==='checkin'&&t.id!==skip&&!DONE.includes(t.status)&&!(t.ci?.rooms||[]).length);
  if(!list.length)return '';
  const who=list.map(t=>`${x.esc(x.npc(t.npc)?.display_name||'Khách')}${t.needs?` (${counted(x,t.needs.adults,t.needs.kids)} người × ${t.needs.nights} đêm)`:''}`).join(', ');
  return `<p class="hs-warn">🧳 Còn khách chờ nhận phòng hôm nay: ${who}. Chừa phòng cho họ trước khi nhận đơn mới.</p>`;
}
function roomFree(x,rid,start,nights,skip){
  const d=x.room.data||{},r=roomInfo(x,rid),room=d.rooms?.[rid];
  if(r.unlock>(d.level||1))return 'phòng chưa mở';
  if(room?.status==='maintenance')return 'phòng đang bảo trì';
  const row=d.grid?.[rid]||[];
  for(let k=0;k<nights;k++){const cell=row[start+k-d.today];if(cell&&cell.kind!=='free')return `đã có khách đêm ${start+k}`;}
  const other=pendingOrders(x).find(o=>o.id!==skip&&o.room===rid&&o.start<start+nights&&start<o.start+o.nights);
  if(other)return `trùng đơn ${other.ota} của ${other.name}`;
  return '';
}
// Mirrors the server's _blocked(): why a room cannot be held for [start, start+nights) — '' when it can.
function holdBlock(x,rid,start,nights){
  const d=x.room.data||{},r=roomInfo(x,rid),room=d.rooms?.[rid]||{};
  if(r.unlock>(d.level||1))return `${r.name} chưa mở`;
  if(room.status==='maintenance')return `${r.name} đang bảo trì`;
  if(room.status==='occupied'&&(room.until>start||(room.task&&start<=d.today)))return `${r.name} còn khách ở tới ngày ${room.until}`;
  const b=(d.bookings||[]).find(b=>b.rooms.includes(rid)&&b.start<start+nights&&start<b.start+b.nights);
  return b?`${r.name} đã có khách đặt từ ngày ${b.start}`:'';
}
function otaRow(x,o){
  const r=roomInfo(x,o.room),clash=roomFree(x,o.room,o.start,o.nights,o.id),end=o.start+o.nights-1;
  const pick=(x.ui.ota||{})[o.id]||[],cap=pick.reduce((a,id)=>a+roomInfo(x,id).cap,0),busy=deskOpen(x);
  const chips=x.cc.rooms.filter(v=>v.unlock<=(x.room.data?.level||1)).map(v=>{
    const why=roomFree(x,v.id,o.start,o.nights,o.id),on=pick.includes(v.id);
    return `<button type="button" class="hs-chip ${on?'on':''}" data-action="car:ota" data-order="${x.esc(o.id)}" data-room="${x.esc(v.id)}" aria-pressed="${on}" ${why?'disabled':''} title="${x.esc(why||v.cap+' người')}">${v.emoji} ${x.esc(v.name)}<small>${why?'✗':v.cap+'👤'}</small></button>`;
  }).join('');
  const actions=clash?`<p class="small">Xếp sang phòng trống đủ ${o.guests} chỗ (tối đa 2 phòng):</p><div class="hs-chips">${chips}</div>
      <div class="row wrap">${x.cmd(`🔁 Xếp vào ${pick.map(id=>x.esc(roomInfo(x,id).name)).join(' + ')||'…'}${pick.length?` (${cap} chỗ)`:''}`,'hs_sync',{order:o.id,rooms:pick},'ghost small',!pick.length||cap<o.guests||busy)}
      ${x.confirmCmd(`🏡 Nhờ Nhà Gỗ Cô Ba (−${x.cc.walk_fee||15} xu)`,'hs_walk',{order:o.id},`Chuyển ${o.name} sang Nhà Gỗ Cô Ba? Nhà trả ${x.cc.walk_fee||15} xu chênh lệch và taxi.`,'ghost small',busy)}</div>`
    :annivHint(x,o)?`<div class="row wrap">${x.cmd(`✅ Đồng bộ vào ${x.esc(r.name)}`,'hs_sync',{order:o.id,rooms:[o.room]},'ghost small',busy)}</div>
      <p class="small">Hoặc xếp sang phòng khác đủ ${o.guests} chỗ:</p><div class="hs-chips">${chips}</div>
      <div class="row wrap">${x.cmd(`🔁 Xếp vào ${pick.map(id=>x.esc(roomInfo(x,id).name)).join(' + ')||'…'}${pick.length?` (${cap} chỗ)`:''}`,'hs_sync',{order:o.id,rooms:pick},'ghost small',!pick.length||cap<o.guests||busy)}</div>`
    :`<div class="row wrap">${x.cmd(`✅ Đồng bộ vào ${x.esc(r.name)}`,'hs_sync',{order:o.id,rooms:[o.room]},'ghost small',busy)}</div>`;
  return `<li class="hs-ota-row ${clash?'clash':''}"><div class="row spread"><b>${x.esc(o.ota)} · ${x.esc(o.name)}</b><span class="tag ${clash?'danger':'green'}">${clash?'⚠️ Trùng':'Trống'}</span></div>
    <small>${r.emoji} ${x.esc(r.name)} · đêm ${o.start}${o.nights>1?'–'+end:''} · ${o.guests} khách · app chuyển ${x.money(o.net)} (đã trừ ${x.cc.commission||15}%)</small>
    ${clash?`<p class="hs-warn">⚠️ ${x.esc(clash)} — app đã bán trùng.</p>`:''}${annivHint(x,o)}${actions}</li>`;
}
/* Room 3 is the couple's every year: warn before an app order takes their nights (they have not called yet). */
function annivHint(x,o){
  const d=x.room.data||{},a=d.anniv||{},nights=2;
  if(a.booked||!a.next||o.room!==x.cc.anniv_room||d.today<a.call-2)return '';
  if(!(o.start<a.next+nights&&a.next<o.start+o.nights))return '';
  return `<p class="small hs-anniv-hint">🗝️ Đêm ${a.next}–${a.next+nights-1} ${x.esc(x.cc.anniv_name||'Cô Diệp & Chú Khang')} hay xin phòng số 3 — có thể xếp khách app sang phòng khác.</p>`;
}
function otaPanel(x,open=false){
  const list=pendingOrders(x);
  if(!list.length)return '';
  const clashes=list.filter(o=>roomFree(x,o.room,o.start,o.nights,o.id)).length;
  return `<details class="hs-ota" ${open||clashes?'open':''}><summary>📥 Hộp đơn OTA · ${list.length} chờ đồng bộ${clashes?` · <b class="hs-bad">${clashes} trùng phòng</b>`:''}</summary>
    ${waiting(x)}<ul class="hs-ota-list">${list.map(o=>otaRow(x,o)).join('')}</ul></details>`;
}

/* ---------------------------------------------------------------- calendar */
function calendar(x,{range=null,picked=[],selectable=false,task=''}={}){
  const d=x.room.data||{};if(!d.grid)return '';
  const days=Array.from({length:x.cc.horizon||7},(_,k)=>d.today+k);
  const inRange=day=>range&&day>=range[0]&&day<range[0]+range[1];
  const wanted={};
  for(const o of pendingOrders(x))for(let k=0;k<o.nights;k++)(wanted[o.room+':'+(o.start+k)]=wanted[o.room+':'+(o.start+k)]||[]).push(o.name);
  const head=`<div class="hs-row head"><span class="hs-rname">Phòng</span>${days.map(day=>`<span class="hs-day ${inRange(day)?'want':''}">${day===d.today?'Nay':'N'+day}</span>`).join('')}</div>`;
  const rows=x.cc.rooms.map(r=>{
    const locked=r.unlock>d.level,room=d.rooms[r.id];
    const on=picked.includes(r.id),tick=on?'<b class="hs-tick" aria-hidden="true">✓</b>':'';
    const label=`<span class="hs-rname"><span class="hs-rn">${tick}${r.emoji} ${x.esc(r.name)}</span><small>số ${r.no} · ${r.cap}👤${r.stairs?' · 🪜':''}${locked?' · 🔒':''}</small></span>`;
    const cells=(d.grid[r.id]||[]).map(c=>{
      const ota=wanted[r.id+':'+c.day],clash=ota&&(c.kind!=='free'||ota.length>1);
      const label=(c.label||'Trống')+(ota?` · đơn OTA chờ: ${ota.join(', ')}`:'');
      return `<span class="hs-cell ${c.kind} ${inRange(c.day)?'want':''} ${ota?'ota':''} ${clash?'clash':''}" title="${x.esc(label)}" aria-label="Ngày ${c.day}: ${x.esc(label)}">${c.anniv?'🗝️':CELL[c.kind]||''}${ota?'<i aria-hidden="true">📥</i>':''}</span>`;
    }).join('');
    // Picking a room on a phone: the whole row (name and nights) is one big tap target.
    if(selectable&&!locked)return `<button type="button" class="hs-row hs-pick ${on?'picked':''} st-${x.esc(room?.status||'')}" data-action="car:sel" data-task="${x.esc(task)}" data-room="${x.esc(r.id)}" aria-pressed="${on}">${label}${cells}</button>`;
    return `<div class="hs-row ${on?'picked':''} ${locked?'locked':''} st-${x.esc(room?.status||'')}">${label}${cells}</div>`;
  }).join('');
  return `<div class="hs-cal-wrap"><div class="hs-cal">${head}${rows}</div></div>
    <p class="hs-legend small muted">🛏️ có khách · 📌 đã đặt · 🗝️ cô chú phòng số 3 · 📥 đơn OTA chưa đồng bộ · 🔧 bảo trì · 🪜 phải leo cầu thang${range?' · cột tô màu = đêm khách hỏi':''}</p>`;
}

/* ---------------------------------------------------------------- housekeeping */
function housekeeping(x){
  const d=x.room.data||{};if(!d.rooms)return '';
  const busy=deskOpen(x);
  const cards=x.cc.rooms.map(r=>{
    const room=d.rooms[r.id],locked=r.unlock>d.level,[label,kind]=STATUS[room.status]||['?',''],st=d.stays?.[r.id];
    let body='';
    if(room.status==='occupied')body=st?stayCard(x,r,room,st):`<small>${x.esc(room.guest||'Khách')} · trả phòng ngày ${room.until}</small>`;
    else if(room.status==='clean')body=`<small class="hs-stars" aria-label="Điểm buồng phòng ${room.q}/5">${'★'.repeat(room.q)}${'☆'.repeat(Math.max(0,5-room.q))}</small>`;
    else if(room.status==='maintenance'){
      // The note of a locked room already ends with “mở ở cấp N”: show the lock once, on its own line.
      const note=String(room.note||'Đang sửa').replace(/\s*[—-]\s*mở ở cấp \d+\s*$/,'');
      body=`<small>${x.esc(note)}</small>${locked?`<small class="hs-lock">🔒 Mở ở cấp ${r.unlock}</small>`:x.confirmCmd('🔧 Gọi thợ','hs_repair',{room:r.id},'Gọi thợ sửa phòng này? Tiền công trả ngay, sau đó phòng cần dọn lại.','ghost small',busy)}`;
    }
    else body=x.button(room.hk?'🧹 Dọn tiếp':'🧹 Dọn phòng','car:hk',{room:r.id},'small ghost');
    return `<article class="hs-roomcard ${x.esc(room.status)} ${x.ui.hk===r.id?'active':''}"><div class="row spread"><b>${r.emoji} ${x.esc(r.name)} <span class="hs-door">số ${r.no}</span></b><span class="tag ${kind}">${label}</span></div><small class="muted">${r.cap} người · ${x.esc(r.beds)}</small>${locked?'':upkeep(x,r,room)}${body}</article>`;
  }).join('');
  const rid=x.ui.hk,room=rid&&d.rooms[rid];
  const lost=(d.lost||[]).filter(l=>l.status==='kept');
  return `<div class="hs-rooms">${cards}</div>${room&&room.status==='dirty'?turnover(x,rid,room):''}
    ${lost.length?`<details class="hs-lost"><summary>🗃️ Tủ đồ thất lạc (${lost.length})</summary><ul>${lost.map(l=>`<li>${x.esc(l.item)} · phòng ${x.esc(roomInfo(x,l.room).name)} · ngày ${l.day}</li>`).join('')}</ul><small class="muted">Chỉ giao cho người đặt phòng, hoặc người được họ xác nhận qua kênh đặt phòng.</small></details>`:''}`;
}
function turnover(x,rid,room){
  const r=roomInfo(x,rid),done=room.hk?.done||[],air=airOf(x),busy=deskOpen(x);
  const middle=x.cc.hk_steps.filter(s=>s.id!=='strip'&&s.id!=='ready').every(s=>done.includes(s.id));
  const steps=x.cc.hk_steps.map((s,i)=>{
    const ok=done.includes(s.id),free=s.id==='ready',wait=(s.id!=='strip'&&!room.hk)||(s.id==='ready'&&!middle);
    const use=Object.entries(s.use||{}).map(([k,q])=>`${q} ${itemInfo(x,k).name.toLowerCase()}`);
    if(s.id==='amenity'&&room.mini)use.push(`${room.mini} mì ly bù minibar`);
    // Short of a supply: the step says what is missing and a tap opens the stock room for it (the server would refuse).
    const short=ok?[]:lacks(x,hkNeed(room,s)),g=short.length?lackGo(x,short):null;
    return `<button type="button" class="hs-hkstep ${ok?'done':''}${g?' short':''}" ${g?goAttrs(x,g):cmdAttr(x,'hs_clean',{room:rid,step:s.id})} ${ok||(!g&&wait)||(busy&&!free)?'disabled':''}><span class="n">${ok?'✓':i+1}</span><span class="e">${g?'📦':s.emoji}</span><span class="grow">${x.esc(s.name)}${g?`<small class="hs-lack-line">${g.label}</small>`:use.length?`<small>−${x.esc(use.join(', '))}</small>`:''}</span></button>`;
  }).join('');
  return `<div class="hs-turnover card"><div class="row spread"><h4>🧹 Dọn phòng ${r.emoji} ${x.esc(r.name)}</h4>${x.button('Đóng','car:hk',{room:rid},'ghost small')}</div>
    <p class="small muted">🪟 ${air.damp}–${air.cold} giây${air.damp>(x.cc.air?.damp||15)?' · 🌧️ mưa ẩm':''}</p>
    ${bar('air',room.hk?.start,[['damp',0,air.damp],['fresh',air.damp,air.cold],['cold',air.cold,AIR_SCALE]],AIR_SCALE)}
    <div class="hs-hksteps">${steps}</div></div>`;
}
/* ---------------------------------------------------------------- care loop: upkeep, guests who stay, garden & wood, guest book */
const wearTone=w=>w>=80?'good':w>=50?'ok':w>=25?'warn':'bad';
function upkeep(x,r,room){
  const w=room.wear??100,busy=deskOpen(x),empty=['clean','dirty'].includes(room.status)&&!room.hk&&!room.task;
  const deep=empty&&w<80?x.confirmCmd(`🧽 Tổng vệ sinh (−${x.cc.deep_cost||3} xu)`,'hs_deep',{room:r.id},`Tổng vệ sinh phòng ${r.name}: giặt rèm, lau gầm giường, xịt chống ẩm${r.id==='ho'?', lau lan can gỗ và tưới hoa ban công':''}? Độ tươm tất về 100%.`,w<(x.cc.wear_low||50)?'small':'ghost small',busy):'';
  const snag=room.snag?`<div class="hs-snag"><span>🔧 ${x.esc(room.snag)}</span>${x.confirmCmd(`Sửa (−${x.cc.fix_cost||4} xu)`,'hs_fix',{room:r.id},`Mua đồ sửa: ${room.snag.toLowerCase()}?`,'ghost small',busy||room.status==='maintenance')}</div>`:'';
  return `<div class="hs-wear ${wearTone(w)}" title="Độ tươm tất: mỗi đêm có khách giảm dần, tổng vệ sinh để phục hồi"><div class="bar"><i style="width:${w}%"></i></div><small>Tươm tất ${w}% · ${x.esc(room.wear_word||'')}</small></div>${snag}${deep?`<div class="row wrap">${deep}</div>`:''}`;
}
function stayCard(x,r,room,st){
  const d=x.room.data,today=d.today,busy=deskOpen(x);
  const head=`<div class="hs-stay-head"><span class="hs-mood" aria-hidden="true">${MOOD_EMOJI[st.word]||'🙂'}</span><span class="grow"><b>${x.esc(st.guest)}</b><small>${x.esc(st.word)} · trả phòng ngày ${room.until}${st.regular?' · khách quen':''}</small></span></div>`;
  const moodBar=`<div class="hs-moodbar"><i style="width:${st.mood}%"></i></div>`;
  if(st.rolled!==today){
    const why=room.task?'Đang làm thủ tục trả phòng.':room.until<=today?'Trả phòng hôm nay.':'Mới nhận phòng — từ mai mới cần chăm.';
    return `<div class="hs-stay">${head}${moodBar}<small class="muted">${why}</small>${stayLog(x,r,st)}</div>`;
  }
  const rows=[],btns=[];
  const tidyDone=st.tidy!=null;
  rows.push({ok:st.tidy==='tidy'||st.tidy==='door'?true:st.tidy==='intrude'||st.tidy==='basket'?false:null,icon:st.dnd?'🚪':'🧺',label:st.dnd?'Để khăn ở cửa':'Dọn phòng giữa kỳ',
    note:{intrude:'đã vào phòng dù có biển',basket:'chỉ để khăn, phòng chưa dọn'}[st.tidy]||(st.dnd?'2 khăn tắm, không gõ cửa':'2 khăn tắm')});
  const towels=lacks(x,{towel:2});
  if(!tidyDone)btns.push(x.cmd('🧺 Vào dọn phòng','hs_stay',{room:r.id,do:'tidy'},st.dnd?'ghost small':'small',busy||towels.length>0),x.cmd('🚪 Để khăn ở cửa','hs_stay',{room:r.id,do:'door'},st.dnd?'small':'ghost small',busy||towels.length>0),towels.length?lackBtn(x,towels):'');
  if(st.cold){
    rows.push({ok:st.warmed?true:null,icon:'🔥',label:'Sưởi đêm lạnh',note:st.warmed?(st.warmed==='wood'?'lò củi + chăn dày':'máy sưởi gas + chăn dày'):'1 bó củi hoặc 1 bình gas',tone:st.warmed?'':'danger'});
    if(!st.warmed)btns.push(x.cmd(`🪵 Nhóm lò củi (${d.wood||0})`,'hs_stay',{room:r.id,do:'warm',how:'wood'},'small',busy||!d.wood),x.cmd(`🔥 Máy sưởi gas (${x.stock('heater_gas')})`,'hs_stay',{room:r.id,do:'warm',how:'gas'},'ghost small',busy||!x.stock('heater_gas')));
  }
  let ask='';
  if(st.ask){
    const a=(x.cc.asks||[]).find(v=>v.id===st.ask)||{emoji:'💬',label:st.ask};
    rows.push({ok:st.asked==='ok'?true:st.asked==='bad'?false:null,icon:a.emoji,label:a.label,note:st.asked==='bad'?'gợi ý chưa hợp':''});
    if(!st.asked){
      if(st.ask==='trip'){
        const want=new Set(st.want||[]),avoid=new Set(st.avoid||[]);
        const opts=(st.opts||[]).map(id=>{const p=x.cc.places.find(v=>v.id===id)||{name:id,emoji:'📍',tags:[]};
          return `<button type="button" class="hs-trip-opt" ${cmdAttr(x,'hs_stay',{room:r.id,do:'ask',place:id})} ${busy?'disabled':''}><b>${p.emoji} ${x.esc(p.name)}</b><span class="hs-tags">${p.tags.map(tag=>`<i class="${avoid.has(tag)?'bad':want.has(tag)?'good':''}">${x.esc(x.cc.tag_names[tag]||tag)}</i>`).join('')}</span></button>`;}).join('');
        ask=`${bubble(x,'Khách:',st.say||'')}<div class="hs-trip">${opts}</div>`;
      }else{
        const use=Object.entries(a.use||{}).map(([k,q])=>`${q} ${itemInfo(x,k).name.toLowerCase()}`).join(', ');
        const short=lacks(x,a.use||{});
        ask=`${bubble(x,'Khách:',st.say||'')}<div class="row wrap">${x.cmd(`${a.emoji} ${x.esc(a.act||a.label)}${use?` (${x.esc(use)})`:''}`,'hs_stay',{room:r.id,do:'ask'},'small',busy||short.length>0)}${short.length?lackBtn(x,short):''}</div>`;
      }
    }
  }
  const sign=st.dnd?'<p class="hs-dnd">🚪 Cửa treo biển <b>“Xin đừng làm phiền”</b></p>':'';
  return `<div class="hs-stay">${head}${moodBar}${sign}${reqList(rows,x.esc,'Việc chăm khách phòng '+r.name)}${btns.length?`<div class="row wrap hs-stay-btns">${btns.join('')}</div>`:''}${ask}${stayLog(x,r,st)}</div>`;
}
function stayLog(x,r,st){
  if(!(st.log||[]).length)return '';
  const key='log-'+r.id;
  return panel(x,key,'📓 Nhật ký mấy ngày ở',`<ul class="hs-log">${st.log.map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul>`,false,'hs-mini');
}
function careList(x,open){
  const rows=x.room.data?.care||[];if(!rows.length)return '';
  const done=rows.filter(r=>r.ok===true).length,next=rows.find(r=>r.ok!==true);
  const head=`📋 Việc chăm hôm nay <b>${done}/${rows.length}</b>${next?`<small>Tiếp: ${x.esc(next.label)}</small>`:'<small>Xong hết rồi.</small>'}`;
  return panel(x,'care',head,reqList(rows.map(r=>({ok:r.ok,icon:r.icon,label:r.label,note:r.note||'',tone:r.tone||''})),x.esc,'Việc chăm hôm nay'),open&&!!next,'hs-care');
}
function gardenCard(x){
  const d=x.room.data||{};if(d.garden==null)return '';
  const g=d.garden,bloom=x.cc.garden_bloom||70,wilt=x.cc.garden_wilt||35,busy=deskOpen(x);
  const gw=g>=bloom?'🌸 nở rộ — khách ở tiếp vui hơn':g>=wilt?'🌿 cần tưới sớm':'🥀 đang héo — khách ở tiếp phàn nàn';
  const tm=d.tomorrow||{},cold=['cold','rain'].includes(tm.id);
  const staying=Object.entries(d.rooms||{}).filter(([id,r])=>r.status==='occupied'&&r.until>d.today+1).length;
  const tip=cold?`Mai ${x.esc(tm.emoji||'')} ${x.esc((tm.title||'').toLowerCase())}: ${staying} phòng có khách ở tiếp${staying?` — cần ${staying} bó củi hoặc ${staying} bình gas.`:'.'}`:`Mai ${x.esc(tm.emoji||'')} ${x.esc((tm.title||'').toLowerCase())}: không cần sưởi thêm.`;
  const full=(d.wood||0)+(d.wood_order||0)+(x.cc.wood_pack||5)>(x.cc.wood_max||30)||(d.wood_order||0)>=2*(x.cc.wood_pack||5);
  return `<section class="hs-garden">
    <div class="hs-gline"><span class="hs-gicon" aria-hidden="true">🌸</span><span class="grow"><b>Vườn cẩm tú cầu</b><small>${g}% · ${gw}</small><span class="hs-gbar ${g>=bloom?'good':g>=wilt?'ok':'bad'}"><i style="width:${g}%"></i></span></span>${x.cmd('💧 Tưới, tỉa','hs_garden',{},g<50?'small':'ghost small',busy||g>=100)}</div>
    <div class="hs-gline"><span class="hs-gicon" aria-hidden="true">🪵</span><span class="grow"><b>Củi khô: ${d.wood||0} bó</b><small>${d.wood_order?`+${d.wood_order} bó Chú Tư chở tới sáng mai · `:''}${tip}</small></span>${x.confirmCmd(`🪵 Đặt ${x.cc.wood_pack||5} bó (−${x.cc.wood_cost||6} xu)`,'hs_wood',{},`Đặt ${x.cc.wood_pack||5} bó củi của Chú Tư? Củi chở tới sáng mai — đêm nay chỉ dùng được củi đang có hoặc gas.`,cold&&(d.wood||0)+(d.wood_order||0)<staying?'small':'ghost small',busy||full)}</div></section>`;
}
function bookPanel(x,open=false){
  const d=x.room.data||{},book=d.book||[],a=d.anniv||{};
  const roomName=id=>id?roomInfo(x,id).name:'—';
  const pages=(a.pages||[]).map(p=>`<li>Năm thứ ${p.year} · ngày ${p.day} · ${p.room?x.esc(roomName(p.room)):'không có phòng'}${p.stars?` · ${'★'.repeat(p.stars)}`:''}</li>`).join('');
  const when=a.here?`Cô chú đang ở phòng ${x.esc(roomName(a.here))}.`:a.booked?`Đã đặt phòng ${x.esc(roomName(a.booked.room))} từ ngày ${a.booked.start} (năm thứ ${a.booked.year}).`:`Cô chú thường gọi đặt vào ngày ${a.call}.`;
  const three=`<article class="hs-anniv"><span class="hs-anniv-key" aria-hidden="true">🗝️</span><div class="grow"><b>Phòng số 3 · ${x.esc(x.cc.anniv_name||'Cô Diệp & Chú Khang')}</b><small>Năm nào cũng xin phòng Đồi Thông, cửa sổ nhìn đồi thông. ${when}</small>${pages?`<ul class="hs-pages">${pages}</ul>`:''}</div></article>`;
  const rows=book.map(b=>{const who=x.npc(b.npc);
    return `<li class="hs-guest">${x.portrait(who,36)}<div class="grow"><b>${x.esc(b.name)}</b><small>${b.visits} lần ở · lần cuối ngày ${b.last}${b.fav?` · thích ${x.esc(roomName(b.fav))}`:''}${b.stars?` · ${'★'.repeat(b.stars)}`:''}</small>
      ${b.notes.length?`<ul class="hs-notes">${b.notes.map(n=>`<li><span aria-hidden="true">${x.esc(n.emoji)}</span> ${x.esc(n.text)}</li>`).join('')}</ul>`:''}${b.more?`<small class="muted">Ở thêm ${b.more} lần nữa để biết thêm.</small>`:''}</div></li>`;}).join('');
  const body=`${three}${rows?`<ul class="hs-book">${rows}</ul>`:'<p class="small muted">Khách ở xong sẽ được ghi vào sổ; lần sau họ quay lại, sổ nhắc bạn điều họ thích.</p>'}`;
  if(open)return `<section class="hs-bookp"><h4 class="section-title">📖 Sổ lưu bút · ${book.length} khách quen</h4>${body}</section>`;
  return panel(x,'book',`📖 Sổ lưu bút · ${book.length} khách quen`,body,false,'hs-bookp');
}
function regularCard(t,x){
  const b=(x.room.data?.book||[]).find(v=>v.npc===t.npc);if(!b||!b.visits)return '';
  const fav=b.fav?roomInfo(x,b.fav):null;
  return `<div class="hs-regular"><b>📖 Khách quen · ${b.visits} lần ở${fav?` · thích ${fav.emoji} ${x.esc(fav.name)}`:''}</b>${b.notes.map(n=>`<small>${x.esc(n.emoji)} ${x.esc(n.text)}</small>`).join('')}</div>`;
}

/* While a surprise waits at the counter: only the pan and rooms being aired can still be finished. */
function running(t,x,pan=true){
  const d=x.room.data||{},parts=[];
  if(pan&&t&&t.known&&t.job==='breakfast'&&t.tray.pan){
    const w=x.cc.egg||{raw:5,runny:11,well:18};
    parts.push(`<div class="hs-pan">${bar('pan',t.tray.pan,[['raw',0,w.raw],['runny',w.raw,w.runny],['well',w.runny,w.well],['burnt',w.well,PAN_SCALE]],PAN_SCALE)}${x.cmd('🥄 Nhấc trứng ra đĩa','hs_plate',{task:t.id},'primary')}</div>`);
  }
  const air=airOf(x);
  for(const r of x.cc.rooms){
    const room=d.rooms?.[r.id];
    if(room?.status!=='dirty'||!room.hk)continue;
    const middle=x.cc.hk_steps.filter(s=>s.id!=='strip'&&s.id!=='ready').every(s=>room.hk.done.includes(s.id));
    parts.push(`<div class="hs-pan"><b>${r.emoji} ${x.esc(r.name)} đang mở cửa sổ</b>${bar('air',room.hk.start,[['damp',0,air.damp],['fresh',air.damp,air.cold],['cold',air.cold,AIR_SCALE]],AIR_SCALE)}
      ${middle?x.cmd('✅ Kiểm lại & báo phòng sạch','hs_clean',{room:r.id,step:'ready'},parts.length?'ghost':'primary'):'<small class="muted">Quyết xong chuyện ở quầy rồi dọn tiếp.</small>'}</div>`);
  }
  return parts.length?`<section class="hs-step-card hs-running"><h4 class="section-title">⏱️ Đang dở tay</h4>${parts.join('')}</section>`:'';
}

/* ---------------------------------------------------------------- jobs */
function checkinJob(t,x){
  const n=t.needs,ci=t.ci,d=x.room.data,sel=selection(x,t);
  const booked=counted(x,n.adults,n.kids),arr=t.arrived?counted(x,t.arrived.adults,t.arrived.kids):null,extra=arr!==null?arr-booked:0;
  const staying=ci.extra==='refuse'?booked:(arr??booked);
  const list=n.list.map(e=>`<button type="button" class="hs-entry ${ci.verified&&e.code===n.code&&e.start===t.day?'ok':''}" data-entry="${x.esc(e.id)}" ${cmdAttr(x,'hs_verify',{task:t.id,entry:e.id})} ${ci.verified?'disabled':''}>
      <b>${x.esc(e.id)}</b><span class="grow">${x.esc(e.name)} · <code>${x.esc(e.code)}</code><small>nhận ngày ${e.start}${e.start===d.today?' (hôm nay)':''} · ${e.nights} đêm · ${e.guests} khách</small></span></button>`).join('');
  let proof='';
  if(n.proof==='bank'){
    const res={ok:['green','🏦 Sao kê đã có khoản cọc — đối chiếu xong.'],missing:['danger','🏦 Sao kê KHÔNG có khoản cọc: chuyển nhầm số tài khoản. Thu đủ tại quầy.']}[t.bank];
    proof=`<div class="hs-proof"><p class="small">💸 Cọc ${x.money(n.paid)} chuyển khoản qua ${x.esc(n.platform)} — khách đưa <b>ảnh chụp màn hình</b>.</p>${res?`<p class="tag ${res[0]}">${res[1]}</p>`:x.cmd('🏦 Mở app ngân hàng đối chiếu','hs_bank',{task:t.id},'ghost small')}</div>`;
  }
  const s1=({n:1,title:'Khớp đặt phòng trên app',done:ci.verified&&(n.proof!=='bank'||!!t.bank),body:`<p class="small">🔎 <b>${x.esc(n.code)}</b> · <b>${x.esc(n.name)}</b> · hôm nay</p><div class="stack hs-entries">${list}</div>${proof}`});
  const idText={ok:'Người lớn đều có giấy tờ tùy thân.',app:'Khách dùng ứng dụng định danh điện tử thay thẻ giấy — hợp lệ.'}[t.id_status]||'';
  const s2=({n:2,title:'Giấy tờ & khai báo lưu trú',done:!!ci.ids,body:ci.ids?`<p class="small">🪪 ${x.esc(idText)} Đã khai báo lưu trú. <b>Không</b> ghi hay chụp số giấy tờ.</p>`:
    `<div class="row wrap">${x.cmd('👀 Xem giấy tờ & khai báo','hs_ids',{task:t.id,mode:'look'},st(t,x,'ids'),!ci.verified)}${x.cmd('📸 Chụp lưu giấy tờ vào máy','hs_ids',{task:t.id,mode:'photo'},'ghost small',!ci.verified)}</div><p class="small muted">🔒 Chỉ xem, không lưu.</p>`});
  let s3body;
  if(!ci.counted)s3body=x.cmd('🧮 Đếm khách đang đứng ở quầy','hs_count',{task:t.id},st(t,x,'count'),!ci.verified);
  else{
    const kids=t.arrived.kids.length?`, ${t.arrived.kids.length} bé (${t.arrived.kids.join(', ')} tuổi)`:'';
    s3body=`<p class="small">👥 Có mặt ${t.arrived.adults} người lớn${x.esc(kids)} → <b>${arr} người tính chỗ</b> (đặt ${booked}).${t.arrived.kids.length?` <span class="muted">Bé dưới ${x.cc.kid_free_age} tuổi ngủ chung không tính.</span>`:''}</p>`;
    if(extra>0)s3body+=ci.extra&&ci.extra!=='none'?`<p class="tag ${ci.extra==='surcharge'?'green':'amber'}">${ci.extra==='surcharge'?`Phụ thu ${x.cc.extra_guest} xu/người/đêm + nệm phụ`:'Chỉ nhận đúng số người đã đặt'}</p>`:
      `<div class="notice amber">Dư ${extra} người so với đặt phòng.</div><div class="row wrap hs-extra">${x.cmd(`➕ Phụ thu ${x.cc.extra_guest} xu/người/đêm`,'hs_extra',{task:t.id,choice:'surcharge'},'ghost small')}${x.cmd('🙅 Chỉ nhận đúng số đã đặt','hs_extra',{task:t.id,choice:'refuse'},'ghost small')}</div>`;
  }
  const s3={n:3,title:'Đếm khách',done:!!(ci.counted&&ci.extra),body:s3body};
  const busyOf=id=>(d.grid?.[id]||[]).slice(0,n.nights).some(c=>c.kind!=='free')||!['clean','dirty'].includes(d.rooms[id].status);
  const dirtyOf=id=>d.rooms[id].status==='dirty';
  const fav=(d.book||[]).find(b=>b.npc===t.npc)?.fav;
  const tiles=x.cc.rooms.map(r=>{
    const room=d.rooms[r.id],locked=r.unlock>d.level;
    const busy=busyOf(r.id);
    const on=sel.includes(r.id)||(!sel.length&&ci.rooms.includes(r.id));
    return `<button type="button" class="tile ${on?'selected':''} ${locked?'locked':''} ${busy?'empty':''}" data-action="car:sel" data-task="${x.esc(t.id)}" data-room="${x.esc(r.id)}" aria-pressed="${on}" ${locked||(busy&&!on)?'disabled':''}><span class="tile-emoji">${r.emoji}</span><b>${x.esc(r.name)}</b>${fav===r.id?'<small class="hs-fav">⭐ phòng quen</small>':''}<small>${locked?'🔒 cấp '+r.unlock:busy?x.esc(STATUS[room.status]?.[0]||'')+(room.status==='clean'?' · vướng lịch':''):room.status==='dirty'?`🧹 Cần dọn · ${r.cap} người`:r.cap+' người'}</small></button>`;
  }).join('');
  const pick=sel.length?sel:ci.rooms,cap=pick.reduce((a,id)=>a+roomInfo(x,id).cap,0),stale=pick.filter(id=>!ci.rooms.includes(id)&&busyOf(id));
  const given=ci.rooms.length>0&&(!sel.length||(sel.length===ci.rooms.length&&sel.every(id=>ci.rooms.includes(id))));
  const caps=x.cc.rooms.filter(r=>r.unlock<=d.level&&!busyOf(r.id)).map(r=>r.cap).sort((a,b)=>b-a);
  const full=ci.counted&&ci.extra&&!ci.rooms.length&&(caps[0]||0)+(caps[1]||0)<staying;
  const fee=(x.cc.walk_fee||15)+(t.bank==='missing'?0:n.paid);
  const walk=full?`<div class="notice amber space-top">Hết phòng trống ${n.nights} đêm cho ${staying} người.</div>
    <div class="row wrap">${x.confirmCmd(`🏡 Chuyển sang Nhà Gỗ Cô Ba (−${fee} xu)`,'hs_relocate',{task:t.id},`Chỉ chọn khi không còn phòng nào dọn kịp hay sắp trả. Xin lỗi ${n.name}, hoàn cọc và trả ${x.cc.walk_fee||15} xu chênh lệch + taxi?`,'ghost small')}</div>`:'';
  const s4=({n:4,title:n.size>staying?`Giao phòng (${n.nights} đêm, cần chỗ cho ${staying} người, khách đặt phòng ${n.size} người)`:`Giao phòng (${n.nights} đêm, cần chỗ cho ${staying} người)`,done:given,body:`<div class="tile-grid hs-tiles">${tiles}</div>
    <div class="row wrap space-top">${x.cmd(`🗝️ Giao ${pick.length?pick.map(id=>x.esc(roomInfo(x,id).name)).join(' + '):'phòng'} (${cap} chỗ)`,'hs_assign',{task:t.id,rooms:pick},st(t,x,'assign'),!(ci.counted&&ci.extra)||!pick.length||given||stale.length>0||(!given&&cap<staying))}</div>${stale.length?`<p class="small hs-warn">${x.esc(stale.map(id=>roomInfo(x,id).name).join(', '))} chưa sạch hoặc chưa trống — bỏ chọn, dọn xong rồi giao.</p>`:''}${!given&&pick.length&&cap<staying&&!stale.length?`<p class="small hs-warn">Mới đủ ${cap}/${staying} chỗ — chọn thêm một phòng (tối đa 2).</p>`:''}${pick.some(dirtyOf)?`<p class="small hs-warn">🧹 ${x.esc(pick.filter(dirtyOf).map(id=>roomInfo(x,id).name).join(', '))} chưa dọn — khách vào là thấy ngay. Dọn xong rồi hẵng trao chìa khóa.</p>`:''}${walk}`});
  const s5=n.cold?{n:5,title:'Máy sưởi đêm lạnh',done:!!ci.heater,body:ci.heater?'<p class="small">🔥 Đã lắp gas, thử lửa, mở hé cửa thông gió.</p>':x.cmd(`🔥 Lắp gas máy sưởi (${x.stock('heater_gas')} bình)`,'hs_heater',{task:t.id},st(t,x,'heater',''),!ci.rooms.length||!x.stock('heater_gas'))}:null;
  return stepRun(x,[s1,s2,s3,s4,s5],{seq:true});
}
function checkinSide(t,x){
  const n=t.needs,ci=t.ci,booked=counted(x,n.adults,n.kids),arr=t.arrived?counted(x,t.arrived.adults,t.arrived.kids):booked;
  const extra=ci.extra==='surcharge'?Math.max(0,arr-booked):0;
  const credit=t.bank==='missing'?0:n.paid;
  const due=n.rate*n.nights-credit+x.cc.extra_guest*extra*n.nights;
  const paidLabel=n.proof==='bank'?(t.bank==='ok'?'Cọc đã về tài khoản ✓':t.bank==='missing'?'Cọc chưa về (chuyển nhầm)':'Cọc theo ảnh chụp (chưa đối chiếu)'):`Đã trả trước (${x.esc(n.platform)})`;
  const rows=[[ci.verified||null,'Khớp mã & ngày',''],[ci.ids||null,'Xem giấy tờ, không lưu số',''],[ci.counted?true:null,'Đếm khách',ci.counted?`${arr}/${booked} người`:''],
    [ci.rooms.length?true:null,'Phòng sạch, trống đủ đêm',ci.rooms.map(id=>roomInfo(x,id).name).join(' + ')]];
  if(n.proof==='bank')rows.splice(1,0,[t.bank?true:null,'Đối chiếu cọc trên app ngân hàng',t.bank==='missing'?'khoản cọc chưa từng về':'']);
  if(n.cold)rows.push([ci.heater||null,'Máy sưởi (trời lạnh)','']);
  return `<div class="hs-receipt"><h4>🧾 Phiếu thu nhận phòng</h4>
    <div class="kv"><span>${n.nights} đêm × ${n.rate} xu</span><b>${x.money(n.rate*n.nights)}</b></div>
    ${n.paid?`<div class="kv"><span>${paidLabel}</span><b>−${x.money(credit)}</b></div>`:''}
    ${extra?`<div class="kv"><span>Phụ thu ${extra} người × ${n.nights} đêm</span><b>${x.money(x.cc.extra_guest*extra*n.nights)}</b></div>`:''}
    <div class="kv total"><span>Thu tại quầy</span><b>${x.money(due)}</b></div></div>
    ${stepRows(x,checkinSteps(t,x),'Việc nhận phòng')}`;
}

function checkoutJob(t,x){
  const n=t.needs,c=t.check,r=t.room?roomInfo(x,t.room):null,pkg=n.package;
  const free=t.truth_hint?.free_water??pkg?.water_free??x.cc.free_water;
  const where=r?`${r.emoji} Phòng ${x.esc(r.name)}`:'Phòng khách (ca đêm xếp)';
  let s1;
  if(!t.checked)s1={n:1,title:'Kiểm phòng trước khi tính tiền',done:false,body:`<p class="small">${where} · ${n.nights} đêm</p>${x.cmd('🔍 Báo buồng phòng kiểm','hs_inspect',{task:t.id},st(t,x,'inspect'))}`};
  else s1={n:1,title:'Kết quả kiểm phòng',done:true,keep:true,body:`<div class="hs-minibar">
      <span>💧 ${c.water} chai <small>(${free} chai tặng)</small></span><span>🍜 ${c.noodles} ly mì</span><span>🍪 ${c.snack} gói bánh</span><span>☕ ${c.coffee} gói <small>(miễn phí)</small></span></div>
      <p class="small">${c.damage?`🏺 Hư hỏng: <b>${x.esc(c.damage)}</b>`:'✅ Không có hư hỏng.'}</p>
      ${c.lost?`<div class="notice ${t.returned?'green':'amber'}">🎒 Khách để quên: <b>${x.esc(c.lost)}</b> ${t.returned?'— đã trả tận tay.':x.cmd('Trả đồ cho khách','hs_return',{task:t.id},'small '+st(t,x,'return'))}</div>`:''}`};
  const row=l=>{const q=t.bill[l.id]||0;
    return `<div class="hs-line ${q?'on':''}"><span class="e">${l.emoji}</span><span class="grow">${x.esc(l.name)}<small>${l.price} xu/${x.esc(l.unit)}</small></span>
      ${x.cmd('−','hs_line',{task:t.id,line:l.id,delta:-1},'ghost small hs-qbtn',!t.checked||!q)}<b class="q">${q}</b>${x.cmd('+','hs_line',{task:t.id,line:l.id,delta:1},'ghost small hs-qbtn',!t.checked||q>=9)}</div>`;};
  // Lines already on the bill show; the empty ones wait under one "+ thêm dòng" line.
  const used=x.cc.bill_lines.filter(l=>t.bill[l.id]),rest=x.cc.bill_lines.filter(l=>!t.bill[l.id]),more=!!(x.ui.open||{}).lines;
  const lines=used.map(row).join('')+(rest.length?`<div class="hs-lines-more ${more?'open':''}">${carBtn(x,`<span class="grow">＋ Thêm dòng (${rest.map(l=>l.emoji).join(' ')})</span><i aria-hidden="true">${more?'▴':'▾'}</i>`,'fold',{key:'lines',open:more?'1':''},'hs-step-head',` aria-expanded="${more}"`)}${more?rest.map(row).join(''):''}</div>`:'');
  const banner=pkg?`<div class="hs-package">🎁 <b>${x.esc(pkg.name)}</b>: ${x.esc(pkg.text)}.</div>`:'';
  const s2={n:2,title:'Lập hóa đơn từng dòng',done:false,body:`${banner}<p class="small muted">💧 tính từ chai thứ ${free+1}${n.laundry?` · 👕 ${n.laundry} túi`:''}${n.late?' · 🕑 trả muộn':''}</p>${lines}`};
  return stepRun(x,[s1,s2],{seq:true});
}
function checkoutSide(t,x){
  const rows=x.cc.bill_lines.filter(l=>t.bill[l.id]).map(l=>`<div class="kv"><span>${l.emoji} ${x.esc(l.name)} × ${t.bill[l.id]}</span><b>${x.money(l.price*t.bill[l.id])}</b></div>`).join('');
  const total=x.cc.bill_lines.reduce((a,l)=>a+l.price*(t.bill[l.id]||0),0);
  const pay=!t.checked||!total?'':t.pay==='cash'?cashPanel(x,t.id,t.cash):'<p class="small hs-pay">📱 Khách chuyển khoản khi nhận hóa đơn.</p>';
  return `<div class="hs-receipt"><h4>🧾 Hóa đơn trả phòng</h4>${rows||'<p class="small muted">Chưa có dòng nào. Tiền phòng đã thu khi nhận phòng.</p>'}<div class="kv total"><span>Tổng</span><b>${x.money(total)}</b></div></div>
    ${pay}${stepRows(x,checkoutSteps(t,x),'Việc trả phòng')}${t.disputes?`<p class="small hs-warn">Khách đã chỉ ra hóa đơn sai ${t.disputes} lần.</p>`:''}`;
}

function breakfastJob(t,x){
  const n=t.needs,tray=t.tray,w=x.cc.egg||{raw:5,runny:11,well:18};
  const ask=t.gen?(t.diet?bubble(x,'Khách:',t.diet_say||''):`<div class="row wrap">${x.cmd('💬 Hỏi dị ứng, ăn kiêng','hs_diet',{task:t.id},'ghost small')}</div>`):'';
  const pan=`<div class="hs-pan">${bar('pan',tray.pan,[['raw',0,w.raw],['runny',w.raw,w.runny],['well',w.runny,w.well],['burnt',w.well,PAN_SCALE]],PAN_SCALE)}
    <div class="row wrap">${tray.pan?x.cmd('🥄 Nhấc trứng ra đĩa','hs_plate',{task:t.id},st(t,x,'plate')):x.cmd(`🍳 Đập trứng vào chảo (${x.stock('egg')})`,'hs_egg',{task:t.id},st(t,x,'egg',''),!x.stock('egg')||tray.eggs.length>=6)}</div>
    <p class="small muted">⏱️ ${w.raw}–${w.runny}s lòng đào · ${w.runny}–${w.well}s chín kỹ · >${w.well}s cháy</p></div>`;
  const tiles=[['bread','🥖','Bánh mì nướng','hs_bread',6],['milk','🥛','Sữa tươi ấm','hs_milk',4],['coffee','☕','Cà phê','hs_coffee',4]].map(([k,e,l,cmd,cap])=>{
    const q=x.stock(k),have=tray[k],want=n[k];
    return `<button type="button" class="tile ${!q?'empty':''} ${want?'wanted':''}" ${cmdAttr(x,cmd,{task:t.id})} ${!q||have>=cap?'disabled':''}><span class="tile-emoji">${e}</span><b>${l}</b><small>kho ${q}</small>${have?`<em class="tile-count">×${have}</em>`:''}</button>`;}).join('');
  return (ask?step('💬','Hỏi trước khi nấu',!!t.diet,ask):'')+step(1,'Chảo trứng',false,pan)+step(2,'Bánh mì & đồ uống',false,`<div class="tile-grid hs-tiles">${tiles}</div>`);
}
function breakfastSide(t,x){
  const n=t.needs,tray=t.tray;
  const eggs=tray.eggs.map(e=>`<span class="hs-egg ${e}" title="${EGG_LABEL[e]}">🍳<small>${EGG_LABEL[e]}</small></span>`).join('');
  return `<div class="hs-tray"><h4>🍽️ Khay ${x.esc(n.where.toLowerCase())} · ${n.people} người</h4><div class="hs-eggs">${eggs||'<small class="muted">Chưa có trứng</small>'}</div>
    <p class="small">${'🥖'.repeat(tray.bread)}${'🥛'.repeat(tray.milk)}${'☕'.repeat(tray.coffee)}</p></div>${stepRows(x,breakfastSteps(t,x),'Khay ăn sáng')}${n.allergy==='egg'||t.eggs_fix?'<p class="small hs-warn">⚠️ Một người dị ứng trứng: không thêm trứng.</p>':''}
    <div class="stack">${x.confirmCmd('🗑️ Dọn khay làm lại','hs_toss',{task:t.id},'Bỏ khay này? Nguyên liệu đã dùng ghi vào hao hụt.',st(t,x,'toss','danger')+' small',!(tray.eggs.length||tray.bread||tray.milk||tray.coffee||tray.pan))}</div>`;
}

function localRate(x,t){x.ui.rate=x.ui.rate||{};return t.hold.length?(t.rate||'std'):(x.ui.rate[t.id]||'std');}
function bookingJob(t,x){
  const n=t.needs,d=x.room.data,sel=selection(x,t),need=counted(x,n.adults,n.kids);
  const held=t.hold.length,rate=t.gen?localRate(x,t):'std',pct=rateInfo(x,rate).pct;
  const pick=held?t.hold:sel;
  const cap=pick.reduce((a,id)=>a+roomInfo(x,id).cap,0);
  const total=Math.ceil(pick.reduce((a,id)=>a+price(x,id,0),0)*n.nights*pct/100);
  const stale=n.start<d.today;
  let body=calendar(x,{range:[n.start,n.nights],picked:pick,selectable:!held,task:t.id})+(held?'':waiting(x));
  body+=`<p class="small">👆 Chọn: <b>${pick.map(id=>x.esc(roomInfo(x,id).name)).join(' + ')||'—'}</b> · ${cap}/${need} chỗ · ~${x.money(total)}</p>`;
  const clash=held?[]:sel.map(id=>holdBlock(x,id,n.start,n.nights)).filter(Boolean);
  const short=!held&&sel.length&&cap<need?`Mới đủ ${cap}/${need} chỗ — chọn thêm hoặc đổi phòng rộng hơn.`:'';
  if(!held)body+=`<div class="row wrap">${x.cmd('📌 Giữ phòng trên lịch','hs_hold',t.gen?{task:t.id,rooms:sel,rate}:{task:t.id,rooms:sel},st(t,x,'hold'),!sel.length||stale||clash.length>0||!!short)}${sel.length?x.button('Bỏ chọn','car:clear',{},'ghost small'):''}</div>${clash.length||short?`<p class="small hs-warn">${x.esc([...clash.map(v=>v+' trong những đêm này.'),short].filter(Boolean).join(' '))}</p>`:''}`;
  else body+=`<div class="card hs-quote"><div class="kv"><span>${t.hold.map(id=>x.esc(roomInfo(x,id).name)).join(' + ')} × ${n.nights} đêm${t.gen?` · ${x.esc(rateInfo(x,rate).name.toLowerCase())}`:''}</span><b>${x.money(t.quote.total)}</b></div><div class="kv total"><span>Cọc ${x.cc.deposit_pct}% giữ phòng</span><b>${x.money(t.quote.deposit)}</b></div>${x.cmd('Bỏ giữ, chọn lại','hs_release',{task:t.id},'ghost small')}</div>`;
  let price2='';
  if(t.gen){
    const chips=(x.cc.rates||[]).map(r=>{const on=r.id===rate;
      return held?`<button type="button" class="hs-chip ${on?'on':''}" ${cmdAttr(x,'hs_rate',{task:t.id,rate:r.id})} aria-pressed="${on}" ${on?'disabled':''}>${r.emoji} ${x.esc(r.name)}<small>${x.esc(r.short)}</small></button>`
        :`<button type="button" class="hs-chip ${on?'on':''}" data-action="car:rate" data-task="${x.esc(t.id)}" data-rate="${x.esc(r.id)}" aria-pressed="${on}">${r.emoji} ${x.esc(r.name)}<small>${x.esc(r.short)}</small></button>`;}).join('');
    const said=t.budget_say?bubble(x,'Khách:',t.budget_say):x.cmd('💬 Hỏi khách ngân sách','hs_budget',{task:t.id},'ghost small');
    price2=step(2,'Báo giá theo mùa',false,`<div class="hs-chips hs-rates" role="group" aria-label="Mức giá">${chips}</div>${t.haggles?`<p class="hs-warn">Khách đã chê giá ${t.haggles} lần — báo lại mức khác.</p>`:''}<div class="space-top">${said}</div>`);
  }
  return step(1,`Lịch phòng · đêm ${n.start}${n.nights>1?'–'+(n.start+n.nights-1):''}`,held,body)+price2;
}
function bookingSide(t,x){
  const n=t.needs,need=counted(x,n.adults,n.kids),pick=t.hold.length?t.hold:selection(x,t);
  const cap=pick.reduce((a,id)=>a+roomInfo(x,id).cap,0);
  const stairs=pick.some(id=>roomInfo(x,id).stairs);
  const rows=[[pick.length?cap>=need:null,`Đủ chỗ cho ${need} người`,n.kids.length?`bé dưới ${x.cc.kid_free_age} tuổi không tính`:''],
    [t.hold.length?true:null,'Trống mọi đêm (không trùng lịch)',''],
    ...(!n.stairs_ok?[[pick.length?!stairs:null,'Không phải leo cầu thang','khách đã dặn']]:[]),
    ...(n.prefer.length?[[pick.length?pick.some(id=>n.prefer.includes(id)):null,'Phòng khách thích',n.prefer.map(id=>roomInfo(x,id).name).join(' / ')]]:[])];
  const stale=n.start<x.room.data.today;
  return `<div class="hs-receipt"><h4>📅 Yêu cầu đặt phòng</h4><div class="kv"><span>Nhận phòng</span><b>ngày ${n.start}</b></div><div class="kv"><span>Số đêm</span><b>${n.nights}</b></div>
    <div class="kv"><span>Khách</span><b>${n.adults} lớn${n.kids.length?` + ${n.kids.length} bé`:''}</b></div><div class="kv"><span>Kênh</span><b>${x.esc(n.channel)}</b></div>
    ${t.gen?`<div class="kv"><span>Mức giá</span><b>${x.esc(rateInfo(x,localRate(x,t)).name)}</b></div>`:''}</div>
    ${stale?'<div class="notice amber">Ngày khách hỏi đã qua. Báo lại lịch sự thôi.</div>':''}${checklist(x,t.hold.length?rows:rows.map(r=>[...r,{sel:'.hs-cal'}]))}
    <div class="stack">${x.confirmCmd('🙏 Báo hết phòng, giới thiệu Nhà Gỗ Cô Ba','hs_decline',{task:t.id},'Báo khách không còn phòng phù hợp và giới thiệu homestay hàng xóm?','ghost small')}</div>`;
}

function recommendJob(t,x){
  const n=t.needs,ans=t.answers||{};
  const avoid=new Set([...n.avoid,...Object.values(ans).flatMap(a=>a.avoid)]),wants=new Set([...n.wants,...Object.values(ans).flatMap(a=>a.want)]);
  const probes=x.cc.probes.map(p=>ans[p.id]?`<p class="hs-ans"><b>${p.emoji} ${x.esc(p.label)}</b> ${x.esc(ans[p.id].answer)}</p>`:
    x.cmd(`${p.emoji} ${x.esc(p.label)}`,'hs_probe',{task:t.id,q:p.id},'ghost small')).join('');
  const places=x.cc.places.map(p=>{
    const on=t.picks.includes(p.id),clash=p.tags.filter(tag=>avoid.has(tag));
    return `<button type="button" class="hs-place ${on?'selected':''} ${clash.length?'clash':''}" ${cmdAttr(x,'hs_pick',{task:t.id,place:p.id})} aria-pressed="${on}">
      <span class="tile-emoji">${p.emoji}</span><b>${x.esc(p.name)}</b><small class="hs-blurb" title="${x.esc(p.blurb)}">${x.esc(p.blurb)}</small>
      <span class="hs-tags">${p.tags.map(tag=>`<i class="${avoid.has(tag)?'bad':wants.has(tag)?'good':''}">${x.esc(x.cc.tag_names[tag]||tag)}</i>`).join('')}</span></button>`;}).join('');
  const asked=Object.keys(ans).length;
  return stepRun(x,[{n:1,title:`Hỏi thêm cho chắc · ${asked}/${x.cc.probes.length}`,done:asked>=x.cc.probes.length,body:`<div class="hs-probes">${probes}</div>`},
    {n:2,title:`Chọn ${n.count}–3 nơi`,done:false,body:`<div class="hs-places">${places}</div>`}]);
}
function recommendSide(t,x){
  const n=t.needs,ans=t.answers||{};
  const avoid=[...new Set([...n.avoid,...Object.values(ans).flatMap(a=>a.avoid)])],wants=[...new Set([...n.wants,...Object.values(ans).flatMap(a=>a.want)])];
  const tagsOf=id=>x.cc.places.find(p=>p.id===id)?.tags||[];
  const rows=wants.map(w=>[t.picks.length?t.picks.some(id=>tagsOf(id).includes(w)):null,'Có nơi '+(x.cc.tag_names[w]||w),'']).concat(avoid.map(a=>[t.picks.length?!t.picks.some(id=>tagsOf(id).includes(a)):null,'Tránh: '+(x.cc.tag_names[a]||a),'']));
  return `<div class="hs-receipt"><h4>🗺️ Lịch trình vẽ tay</h4>${t.picks.map((id,i)=>{const p=x.cc.places.find(v=>v.id===id);return `<div class="kv"><span>${i+1}. ${p.emoji} ${x.esc(p.name)}</span></div>`;}).join('')||'<p class="small muted">Chưa chọn nơi nào.</p>'}</div>
    ${stepRows(x,recommendSteps(t,x),'Việc gợi ý')}${checklist(x,rows.map(r=>[...r,{sel:'.hs-places'}]))}`;
}

function claimJob(t,x){
  const n=t.needs,e=n.entry,r=roomInfo(x,e.room),ans=t.answers||{};
  const log=`<div class="hs-lostcard"><span class="hs-lost-emoji" aria-hidden="true">${x.esc(e.emoji)}</span><div class="grow"><b>${x.esc(e.item)}</b><small>${x.esc(e.detail)}</small>
    <ul class="hs-facts"><li>🚪 Tìm thấy ở <b>${x.esc(r.name)}</b></li><li>📅 Khách trả phòng <b>ngày ${e.day}</b></li><li>🧾 Đặt phòng: <b>${x.esc(e.booker)}</b></li></ul></div></div>`;
  const qs=(x.cc.claim_qs||[]).map(q=>ans[q.id]?`<div class="hs-bubble"><b>${q.emoji} ${x.esc(q.label)}</b> “${x.esc(ans[q.id])}”</div>`
    :x.cmd(`${q.emoji} ${x.esc(q.label)}`,'hs_quiz',{task:t.id,q:q.id},'ghost small')).join('');
  return step(1,'Sổ đồ thất lạc ghi',true,log)+step(2,'Hỏi người gọi để xác minh',Object.keys(ans).length>=2,`<div class="stack hs-claim-q">${qs}</div>`);
}
function claimSide(t,x){
  const asked=Object.keys(t.answers||{}).length;
  const btns=CLAIM_CHOICES.map(([id,label,q])=>x.confirmCmd(label,'hs_claim',{task:t.id,choice:id},q,'ghost full')).join('');
  return `<div class="hs-receipt"><h4>📞 Cuộc gọi hỏi đồ</h4><p class="small">“${x.esc(t.needs.note)}”</p><div class="kv"><span>Đã hỏi</span><b>${asked}/${(x.cc.claim_qs||[]).length} câu</b></div></div>
    <div class="stack hs-claim-pick">${btns}</div>`;
}

/* ---------------------------------------------------------------- next steps (guide.js)
 * Every job lists what is left as steps; the header hint, the tappable rows and the bottom
 * button all come from them. Mechanical steps (read, count, add a line) are one tap on every
 * task; judgement calls (the right booking row, the room, extra guests, the place, the caller)
 * do the right thing on the very first task and point at the choices after that. */
const capOf=(x,ids)=>ids.reduce((a,id)=>a+roomInfo(x,id).cap,0);
const inv=(x,item,what)=>({act:'inventory',label:`📦 Hết ${x.esc(what)}: mở Kho nhập thêm`});
/* The best 1–2 rooms for `need` people among those `ok` accepts: one room, no stairs, clean, not smaller than booked, the favourite. */
function bestRooms(x,ok,need,{size=0,prefer=[],stairs=true}={}){
  const d=x.room.data||{},ids=x.cc.rooms.filter(r=>r.unlock<=(d.level||1)&&ok(r.id)&&(stairs||!r.stairs)).map(r=>r.id);
  const combos=[];ids.forEach((a,i)=>{combos.push([a]);ids.slice(i+1).forEach(b=>combos.push([a,b]));});
  const cost=c=>{const cap=capOf(x,c);
    return (c.length-1)*100+(c.some(id=>d.rooms?.[id]?.status==='dirty')?60:0)+(cap<size?40:0)+(c.some(id=>roomInfo(x,id).stairs)?8:0)-(c.some(id=>prefer.includes(id))?20:0)+cap;};
  return combos.filter(c=>capOf(x,c)>=need).sort((a,b)=>cost(a)-cost(b))[0]||null;
}
/* Turnover of one dirty room, in the house order; the last step waits for the airing window (tick). */
function hkSteps(x,rid){
  const room=x.room.data?.rooms?.[rid];if(!room||room.status!=='dirty')return [];
  const r=roomInfo(x,rid),done=room.hk?.done||[];
  return x.cc.hk_steps.map(s=>{
    const short=lacks(x,hkNeed(room,s));
    return {ok:done.includes(s.id)||null,label:`Dọn ${r.name}: ${s.name}`,go:short.length&&!done.includes(s.id)?lackGo(x,short):{cmd:'hs_clean',payload:{room:rid,step:s.id},label:`${s.emoji} ${x.esc(s.name)} · ${x.esc(r.name)}`}};
  });
}
function checkinSteps(t,x){
  const n=t.needs,ci=t.ci,d=x.room.data,id=t.id,first=firstTime(x),rows=[];
  const right=n.list.find(e=>e.code===n.code&&e.name===n.name&&e.start===d.today);
  rows.push({ok:ci.verified||null,label:`Khớp mã ${n.code} trên app`,go:first&&right?{cmd:'hs_verify',payload:{task:id,entry:right.id},label:`🔎 Chọn dòng ${right.id} · ${x.esc(n.code)} · hôm nay`}:{sel:'.hs-entries'},
    pulse:first&&right?`.hs-entry[data-entry="${right.id}"]`:''});
  if(t.gen&&n.proof==='bank')rows.push({ok:t.bank?true:null,label:'Đối chiếu cọc trên app ngân hàng',go:{cmd:'hs_bank',payload:{task:id},label:'🏦 Mở app ngân hàng đối chiếu'}});
  rows.push({ok:ci.ids||null,label:'Xem giấy tờ, khai báo lưu trú',go:ci.verified?{cmd:'hs_ids',payload:{task:id,mode:'look'},label:'👀 Xem giấy tờ & khai báo'}:null});
  rows.push({ok:ci.counted||null,label:'Đếm khách ở quầy',go:ci.verified?{cmd:'hs_count',payload:{task:id},label:'🧮 Đếm khách ở quầy'}:null});
  if(!ci.counted)return rows;
  const booked=counted(x,n.adults,n.kids),arr=counted(x,t.arrived.adults,t.arrived.kids);
  const busy=rid=>(d.grid?.[rid]||[]).slice(0,n.nights).some(c=>c.kind!=='free')||!['clean','dirty'].includes(d.rooms[rid]?.status);
  if(!ci.extra){
    const fits=bestRooms(x,rid=>!busy(rid)&&d.rooms[rid].status==='clean',arr),pick=fits?'surcharge':'refuse';
    rows.push({ok:null,label:`Dư ${arr-booked} người: phụ thu hay chỉ nhận đúng số đặt`,go:first?{cmd:'hs_extra',payload:{task:id,choice:pick},label:pick==='surcharge'?`➕ Phụ thu ${x.cc.extra_guest} xu/người/đêm (còn phòng rộng)`:'🙅 Chỉ nhận đúng số đã đặt (hết phòng rộng)'}:{sel:'.hs-extra'}});
    return rows;
  }
  const staying=ci.extra==='refuse'?booked:arr,sel=selection(x,t);
  if(!ci.rooms.length){
    const valid=sel.length&&!sel.some(busy)&&capOf(x,sel)>=staying;
    const best=bestRooms(x,rid=>!busy(rid),staying,{size:n.size,prefer:[(d.book||[]).find(b=>b.npc===t.npc)?.fav].filter(Boolean)});
    const plan=valid?sel:best;
    if(!plan){
      rows.push({ok:null,label:'Hết phòng trống đủ đêm',go:{cmd:'hs_relocate',payload:{task:id},confirm:`Không còn phòng nào dọn kịp hay sắp trả? Xin lỗi ${n.name}, chuyển sang Nhà Gỗ Cô Ba?`,label:'🏡 Chuyển sang Nhà Gỗ Cô Ba'}});
      return rows;
    }
    if(valid||first)for(const rid of plan)rows.push(...hkSteps(x,rid));
    const names=plan.map(rid=>roomInfo(x,rid).name).join(' + ');
    const why=sel.length&&!valid?(sel.some(busy)?'phòng đã chọn chưa trống đủ đêm':`mới đủ ${capOf(x,sel)}/${staying} chỗ, chọn thêm (tối đa 2)`):'';
    const taken=sel.find(busy);
    rows.push({ok:null,label:`Giao phòng sạch, đủ ${staying} chỗ`,note:why,go:valid||first?{cmd:'hs_assign',payload:{task:id,rooms:plan},label:`🗝️ Giao ${x.esc(names)} (${capOf(x,plan)} chỗ)`}
      :taken?{act:'car:sel',data:{task:id,room:taken},label:`↺ Bỏ chọn ${x.esc(roomInfo(x,taken).name)}, chọn phòng khác`}:{sel:'.hs-tiles',label:'👉 Chọn phòng sạch, trống đủ đêm'}});
  }else rows.push({ok:true,label:`Giao ${ci.rooms.map(rid=>roomInfo(x,rid).name).join(' + ')}`});
  if(n.cold)rows.push({ok:ci.heater||null,label:'Lắp gas máy sưởi (đêm lạnh)',go:!ci.rooms.length?null:x.stock('heater_gas')?{cmd:'hs_heater',payload:{task:id},label:'🔥 Lắp gas máy sưởi'}:inv(x,'heater_gas','gas máy sưởi')});
  return rows;
}
const checkinDue=(t,x)=>{const n=t.needs,ci=t.ci,booked=counted(x,n.adults,n.kids),arr=t.arrived?counted(x,t.arrived.adults,t.arrived.kids):booked;
  return n.rate*n.nights-(t.bank==='missing'?0:n.paid)+x.cc.extra_guest*(ci.extra==='surcharge'?Math.max(0,arr-booked):0)*n.nights;};
const checkinFinal=(t,x,steps)=>{const ci=t.ci;
  return {label:'🔑 Trao chìa khóa & thu tiền',go:finalGo(steps,'hs_welcome',{task:t.id},{question:`Thu ${checkinDue(t,x)} xu.`,confirm:true}),ready:!!(ci.verified&&ci.ids&&ci.counted&&ci.extra&&ci.rooms.length),why:'giao phòng trước'};};

function billTruth(t,x){
  const n=t.needs,c=t.check||{},pkg=n.package||{},free=new Set(pkg.free||[]),wf=t.truth_hint?.free_water??pkg.water_free??x.cc.free_water;
  return {water:free.has('water')?0:Math.max(0,(c.water||0)-wf),noodles:free.has('noodles')?0:c.noodles||0,snack:free.has('snack')?0:c.snack||0,
    laundry:free.has('laundry')?0:n.laundry||0,late:n.late?1:0,damage:c.damage?1:0};
}
function checkoutSteps(t,x){
  const id=t.id,rows=[{ok:t.checked||null,label:'Kiểm phòng trước khi tính tiền',go:{cmd:'hs_inspect',payload:{task:id},label:'🔍 Báo buồng phòng kiểm'}}];
  if(!t.checked)return rows;
  const lost=t.check?.lost;
  if(lost)rows.push({ok:t.returned||null,label:`Trả ${lost} khách để quên`,go:{cmd:'hs_return',payload:{task:id},label:`🎒 Trả ${x.esc(lost)} cho khách`}});
  const truth=billTruth(t,x);
  for(const l of x.cc.bill_lines){
    const want=truth[l.id]||0,have=t.bill[l.id]||0;if(!want&&!have)continue;
    rows.push({ok:have===want?true:have>want?false:null,label:`${l.emoji} ${l.name}: ${want} ${l.unit}`,note:have!==want?`${have}/${want}`:'',
      go:have===want?null:{cmd:'hs_line',payload:{task:id,line:l.id,delta:have<want?1:-1},label:`${have<want?'➕ Thêm':'➖ Bớt'} 1 ${x.esc(l.unit)} · ${x.esc(l.name)}`}});
  }
  // Cash guests: count the change once the bill is right (the notes follow the bill total).
  const change=t.pay==='cash'?changeStep(x,id,t.cash):null;
  if(change)rows.push(change);
  return rows;
}
const checkoutFinal=(t,x,steps)=>{const total=x.cc.bill_lines.reduce((a,l)=>a+l.price*(t.bill[l.id]||0),0);
  const cash=t.pay==='cash'&&total?t.cash:null,given=cash?tray(x,t.id,cash).reduce((a,v)=>a+v,0):0;
  return {label:cash&&cash.due>0?`🧾 In hóa đơn, thu ${x.money(total)} · thối ${x.money(given)}`:`🧾 In hóa đơn & thu ${x.money(total)}`,
    go:finalGo(steps,'hs_settle',{task:t.id,...changePayload(x,t.id,cash)},{question:cash&&cash.due>0?`Thu ${total} xu, đưa khách ${given} xu tiền thối. Khách sẽ đọc từng dòng.`:`Thu ${total} xu, khách sẽ đọc từng dòng.`,confirm:true}),ready:!!t.checked,why:'kiểm phòng trước'};};

const eggNext=t=>{const want=t.eggs_fix||t.needs.eggs||{},got=t.tray.eggs.filter(e=>e==='runny').length;return got<(want.runny||0)?'runny':'well';};
function breakfastSteps(t,x){
  const n=t.needs,tray=t.tray,id=t.id,want=t.eggs_fix||n.eggs||{},w=x.cc.egg||{raw:5,runny:11,well:18},rows=[];
  if(t.gen)rows.push({ok:t.diet||null,label:'Hỏi dị ứng, ăn kiêng trước khi nấu',go:{cmd:'hs_diet',payload:{task:id},label:'💬 Hỏi dị ứng, ăn kiêng'}});
  const got={runny:tray.eggs.filter(e=>e==='runny').length,well:tray.eggs.filter(e=>e==='well').length};
  if(tray.eggs.some(e=>e==='raw'||e==='burnt')||got.runny>(want.runny||0)||got.well>(want.well||0))
    rows.push({ok:false,label:'Trứng hỏng hoặc dư: dọn khay làm lại',go:{cmd:'hs_toss',payload:{task:id},confirm:'Bỏ khay này? Nguyên liệu đã dùng ghi vào hao hụt.',label:'🗑️ Dọn khay làm lại'}});
  const plate=k=>({cmd:'hs_plate',payload:{task:id},label:`🥄 Nhấc trứng ra lúc ${EGG_LABEL[k]} (${k==='runny'?w.raw:w.runny}–${k==='runny'?w.runny:w.well} giây)`});
  let pan=!!tray.pan;
  for(const k of ['runny','well']){
    if(!want[k]&&!got[k])continue;
    const open=got[k]<(want[k]||0);
    const go=!open?null:pan?plate(k):tray.pan?null:x.stock('egg')?{cmd:'hs_egg',payload:{task:id},label:`🍳 Đập 1 trứng vào chảo (${EGG_LABEL[k]})`}:inv(x,'egg','trứng');
    if(open&&pan)pan=false;
    rows.push({ok:got[k]?got[k]===want[k]:null,label:`${want[k]||0} trứng ${EGG_LABEL[k]}`,note:`${got[k]}/${want[k]||0}`,go});
  }
  if(pan)rows.push({ok:null,label:'Nhấc trứng ra khỏi chảo',go:plate(eggNext(t))});
  for(const [k,l,cmd] of [['bread','bánh mì','hs_bread'],['milk','sữa','hs_milk'],['coffee','cà phê','hs_coffee']]){
    if(!n[k]&&!tray[k])continue;
    rows.push({ok:tray[k]?tray[k]===n[k]:null,label:`${n[k]} ${l}`,note:`${tray[k]}/${n[k]}`,go:tray[k]<n[k]?(x.stock(k)?{cmd,payload:{task:id},label:`➕ Thêm 1 ${l}`}:inv(x,k,l)):null});
  }
  return rows;
}
const breakfastFinal=(t,x,steps)=>{const tray=t.tray;
  return {label:`✅ Mang ra cho khách · ${x.money(t.quoted_price||0)}`,go:finalGo(steps,'hs_serve',{task:t.id},{question:'Khách ăn và đánh giá đúng những gì trên khay.',confirm:true}),
    ready:!tray.pan&&!!(tray.bread||tray.eggs.length)&&!tray.eggs.includes('raw'),why:'làm khay trước'};};

function bookingSteps(t,x){
  const n=t.needs,d=x.room.data,id=t.id,first=firstTime(x),need=counted(x,n.adults,n.kids),rows=[];
  if(n.start<d.today)return rows;
  if(t.gen)rows.push({ok:t.asked_budget||null,label:'Hỏi khách ngân sách',go:{cmd:'hs_budget',payload:{task:id},label:'💬 Hỏi khách ngân sách'}});
  if(!t.hold.length){
    const sel=selection(x,t),valid=sel.length&&capOf(x,sel)>=need&&!sel.some(rid=>holdBlock(x,rid,n.start,n.nights));
    const best=bestRooms(x,rid=>!holdBlock(x,rid,n.start,n.nights),need,{size:need,prefer:n.prefer,stairs:n.stairs_ok});
    const plan=valid?sel:first?best:null,rate=d.mod?.id==='low'?'low':'std';
    if(!best&&!valid){rows.push({ok:null,label:'Không còn phòng hợp những đêm này'});return rows;}
    const payload=t.gen?{task:id,rooms:plan||[],rate:valid?localRate(x,t):rate}:{task:id,rooms:plan||[]};
    const why=sel.length&&!valid?(sel.map(rid=>holdBlock(x,rid,n.start,n.nights)).find(Boolean)||`mới đủ ${capOf(x,sel)}/${need} chỗ, chọn thêm (tối đa 2)`):'';
    const taken=sel.find(rid=>holdBlock(x,rid,n.start,n.nights));
    rows.push({ok:null,label:`Giữ phòng trống mọi đêm, đủ ${need} chỗ`,note:why,go:plan?{cmd:'hs_hold',payload,label:`📌 Giữ ${x.esc(plan.map(rid=>roomInfo(x,rid).name).join(' + '))} trên lịch`}
      :taken?{act:'car:sel',data:{task:id,room:taken},label:`↺ Bỏ chọn ${x.esc(roomInfo(x,taken).name)} (đã có khách), chọn phòng khác`}:{sel:'.hs-cal',label:'👉 Chạm tên phòng trên lịch để chọn'}});
    return rows;
  }
  rows.push({ok:true,label:`Đã giữ ${t.hold.map(rid=>roomInfo(x,rid).name).join(' + ')}`});
  if(t.gen&&t.haggles){
    const said=(x.ui.hag??={})[id];
    if(!said||said.n!==t.haggles)x.ui.hag[id]={n:t.haggles,rate:t.rate};
    const was=x.ui.hag[id].rate,lower=(x.cc.rates||[])[Math.max(0,(x.cc.rates||[]).findIndex(r=>r.id===was)-1)];
    if(t.rate===was)rows.push({ok:null,label:'Khách chê giá: báo mức thấp hơn',go:first&&lower&&lower.id!==was?{cmd:'hs_rate',payload:{task:id,rate:lower.id},label:`${lower.emoji} Báo ${x.esc(lower.name.toLowerCase())}`}:{sel:'.hs-rates'}});
  }
  return rows;
}
const bookingFinal=(t,x,steps)=>{
  const n=t.needs,stale=n.start<x.room.data.today;
  if(stale||(!t.hold.length&&steps.some(s=>s.ok===null&&!s.go&&/Không còn phòng/.test(s.label))))
    return {label:'🙏 Báo hết phòng, giới thiệu Nhà Gỗ Cô Ba',go:{cmd:'hs_decline',payload:{task:t.id},confirm:'Báo khách không còn phòng phù hợp và giới thiệu homestay hàng xóm?'},ready:true};
  return {label:`💰 Nhận cọc${t.quote?' '+x.money(t.quote.deposit):''} & gửi xác nhận`,go:finalGo(steps,'hs_book',{task:t.id},{question:'Tin xác nhận kèm nội quy sẽ gửi cho khách.',confirm:true}),ready:!!t.hold.length,why:'giữ phòng trước'};
};

function recommendSteps(t,x){
  const n=t.needs,ans=t.answers||{},id=t.id,first=firstTime(x),rows=[];
  const q=x.cc.probes.find(p=>!ans[p.id]);
  rows.push({ok:q?null:true,label:'Hỏi khách cho chắc',note:`${Object.keys(ans).length}/${x.cc.probes.length}`,go:q?{cmd:'hs_probe',payload:{task:id,q:q.id},label:`${q.emoji} Hỏi: ${x.esc(q.label)}`}:null});
  if(q&&Object.keys(ans).length<3)return rows;
  const avoid=new Set([...n.avoid,...Object.values(ans).flatMap(a=>a.avoid)]),wants=new Set([...n.wants,...Object.values(ans).flatMap(a=>a.want)]);
  const place=pid=>x.cc.places.find(p=>p.id===pid)||{id:pid,name:pid,tags:[]};
  const clash=pid=>place(pid).tags.some(tag=>avoid.has(tag));
  for(const pid of t.picks.filter(clash))rows.push({ok:false,label:`${place(pid).name} vướng điều khách cần tránh`,go:{cmd:'hs_pick',payload:{task:id,place:pid},label:`✕ Bỏ ${x.esc(place(pid).name)}`}});
  const good=t.picks.filter(pid=>!clash(pid)).length;
  if(good<n.count){
    const best=x.cc.places.filter(p=>!t.picks.includes(p.id)&&!clash(p.id)).sort((a,b)=>b.tags.filter(g=>wants.has(g)).length-a.tags.filter(g=>wants.has(g)).length)[0];
    rows.push({ok:null,label:`Chọn ${n.count} nơi hợp khách`,note:`${good}/${n.count}`,go:first&&best&&t.picks.length<3?{cmd:'hs_pick',payload:{task:id,place:best.id},label:`${best.emoji} Chọn ${x.esc(best.name)}`}:{sel:'.hs-places',label:'👉 Chọn nơi hợp khách (thẻ xanh, không thẻ đỏ)'}});
  }else rows.push({ok:true,label:`Đã chọn ${good} nơi`});
  return rows;
}
const recommendFinal=(t,x,steps)=>({label:'✉️ Gửi lịch trình cho khách',go:finalGo(steps,'hs_advise',{task:t.id},{question:'Khách sẽ đi đúng những nơi bạn gợi ý.',confirm:true}),ready:t.picks.length>=t.needs.count,why:`chọn ít nhất ${t.needs.count} nơi`});

function claimSteps(t,x){
  const ans=t.answers||{},id=t.id,qs=x.cc.claim_qs||[],q=qs.find(v=>!ans[v.id]),rows=[];
  rows.push({ok:q?null:true,label:'Hỏi người gọi để xác minh',note:`${Object.keys(ans).length}/${qs.length}`,go:q?{cmd:'hs_quiz',payload:{task:id,q:q.id},label:`${q.emoji} Hỏi: ${x.esc(q.label)}`}:null});
  const safe=CLAIM_CHOICES.find(c=>c[0]==='channel');
  if(!q)rows.push({ok:null,label:'Quyết định giao đồ',go:firstTime(x)?{cmd:'hs_claim',payload:{task:id,choice:safe[0]},confirm:safe[2],label:safe[1]}:{sel:'.hs-claim-pick',label:'👉 So câu trả lời với sổ rồi quyết định'}});
  return rows;
}
const claimFinal=()=>({label:'📞 Quyết định giao đồ',go:{sel:'.hs-claim-pick'},ready:false});

const GUIDES={checkin:[checkinSteps,checkinFinal],checkout:[checkoutSteps,checkoutFinal],breakfast:[breakfastSteps,breakfastFinal],booking:[bookingSteps,bookingFinal],recommend:[recommendSteps,recommendFinal],claim:[claimSteps,claimFinal]};
/** {steps, final, pulse} for the task on screen. */
function taskGuide(t,x){
  if(x.room.data?.desk?.ev){
    const steps=[];
    if(t?.known&&t.job==='breakfast'&&t.tray.pan)steps.push({ok:null,label:'Nhấc trứng khỏi chảo',go:{cmd:'hs_plate',payload:{task:t.id},label:'🥄 Nhấc trứng ra đĩa'}});
    steps.push({ok:null,label:'Quyết chuyện ở quầy',go:{sel:'.hs-opts',label:'👉 Chọn cách xử lý chuyện ở quầy'}});
    return {steps,final:{label:'Quyết chuyện ở quầy',go:{sel:'.hs-opts'},ready:false}};
  }
  if(!t.known)return {steps:[{ok:null,label:t.job==='claim'?'Nghe máy':'Nghe khách nói',go:{cmd:'ask',payload:{task:t.id},label:t.job==='claim'?'📞 Nghe máy':'👂 Nghe khách'}}],pulse:'.hs-ask'};
  const [make,fin]=GUIDES[t.job]||[()=>[],()=>({label:'',go:null,ready:false})];
  const steps=make(t,x),final=fin(t,x,steps);
  const first=pending(steps);
  return {steps,final,pulse:firstTime(x)&&first?.pulse||''};
}
function hintFor(g,x){
  const f=g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/<[^>]*>/g,'').replace(/^[^\p{L}]+/u,''),go:g.final.go}:null;
  // Only steps with no way to do them are left: the hint offers the finish, like the bottom button.
  const steps=f&&!pending(g.steps)?.go?g.steps.filter(s=>s.ok===true||s.go):g.steps;
  return nextHint(x,steps,{final:f,pulse:g.pulse});
}
const bottomBar=(g,x)=>g.final?`<div class="hs-bar">${stepCta(x,g.steps,g.final)}</div>`:'';

/* Between guests: the chores that cost the house if forgotten (app orders, rooms for tonight's arrivals, guests who stay on). */
function idleSteps(x){
  const d=x.room.data||{},rows=[],busy=deskOpen(x);
  if(busy)return [{ok:null,label:'Quyết chuyện ở quầy',go:{sel:'.hs-opts',label:'👉 Chọn cách xử lý chuyện ở quầy'}}];
  for(const o of pendingOrders(x)){
    const clash=roomFree(x,o.room,o.start,o.nights,o.id),pick=(x.ui.ota||{})[o.id]||[];
    const fits=pick.length&&capOf(x,pick)>=o.guests&&pick.every(id=>!roomFree(x,id,o.start,o.nights,o.id));
    const names=ids=>x.esc(ids.map(id=>roomInfo(x,id).name).join(' + '));
    rows.push({ok:null,label:`Đồng bộ đơn ${o.ota} của ${o.name}`,note:clash&&pick.length&&!fits?`mới đủ ${capOf(x,pick)}/${o.guests} chỗ`:'',
      go:!clash?{cmd:'hs_sync',payload:{order:o.id,rooms:[o.room]},label:`📥 Đồng bộ đơn ${x.esc(o.name)} vào ${names([o.room])}`}
        :fits?{cmd:'hs_sync',payload:{order:o.id,rooms:pick},label:`🔁 Xếp ${x.esc(o.name)} vào ${names(pick)}`}
        :{sel:'.hs-ota-row.clash .hs-chips',label:`📥 Đơn ${x.esc(o.name)} trùng phòng: chạm phòng trống đủ ${o.guests} chỗ`}});
  }
  const tonight=new Set((d.bookings||[]).filter(b=>b.start<=d.today&&b.start+b.nights>d.today).flatMap(b=>b.rooms));
  for(const rid of tonight)if(d.rooms?.[rid]?.status==='dirty')rows.push(...hkSteps(x,rid).map(s=>({...s,label:s.label+' (khách tới tối nay)'})));
  for(const [rid,st] of Object.entries(d.stays||{})){
    if(st.rolled!==d.today)continue;
    const r=roomInfo(x,rid);
    if(st.tidy==null)rows.push({ok:null,label:`${r.name}: ${st.dnd?'để khăn ở cửa (biển đừng làm phiền)':'dọn phòng giữa kỳ'}`,go:lacks(x,{towel:2}).length?lackGo(x,lacks(x,{towel:2})):{cmd:'hs_stay',payload:{room:rid,do:st.dnd?'door':'tidy'},label:st.dnd?`🚪 Để khăn ở cửa ${x.esc(r.name)}`:`🧺 Vào dọn ${x.esc(r.name)}`}});
    if(st.cold&&!st.warmed&&(d.wood||x.stock('heater_gas')))rows.push({ok:null,label:`${r.name}: sưởi đêm lạnh`,go:{cmd:'hs_stay',payload:{room:rid,do:'warm',how:d.wood?'wood':'gas'},label:d.wood?`🪵 Nhóm lò củi ${x.esc(r.name)}`:`🔥 Máy sưởi gas ${x.esc(r.name)}`}});
    if(st.ask&&!st.asked){
      const a=(x.cc.asks||[]).find(v=>v.id===st.ask)||{emoji:'💬',label:st.ask,use:{}};
      // The trip choices sit on the rooms tab: the step opens that tab first, then points at them.
      if(st.ask==='trip'){const label=`🗺️ Gợi ý nơi đi cho khách ${x.esc(r.name)}`;rows.push({ok:null,label:`${r.name}: ${a.label.toLowerCase()}`,go:(x.ui.hsTab||'cal')==='rooms'?{sel:'.hs-trip',label}:{act:'car:tab',data:{tab:'rooms'},label}});}
      else rows.push({ok:null,label:`${r.name}: ${a.label.toLowerCase()}`,go:lacks(x,a.use||{}).length?lackGo(x,lacks(x,a.use||{})):{cmd:'hs_stay',payload:{room:rid,do:'ask'},label:`${a.emoji} ${x.esc(a.act||a.label)} · ${x.esc(r.name)}`}});
    }
  }
  return rows;
}

/* Buttons that must wait for real seconds (egg in the pan, windows airing): greyed with a countdown until the window opens. */
function waitFor(x,el){
  let p;try{p=JSON.parse(el.dataset.payload||'{}');}catch{return null;}
  if(el.dataset.command==='hs_plate'){
    const t=(x.room.tasks||[]).find(v=>v.id===p.task),pan=t?.tray?.pan;if(!pan)return null;
    const w=x.cc.egg||{raw:5,runny:11,well:18};return eggNext(t)==='runny'?[pan,w.raw,'trứng lòng đào']:[pan,w.runny,'trứng chín kỹ'];
  }
  if(el.dataset.command==='hs_clean'&&p.step==='ready'){const hk=x.room.data?.rooms?.[p.room]?.hk;return hk?.start?[hk.start,airOf(x).damp,'phòng hết mùi ẩm']:null;}
  return null;
}
function holdUntilReady(root,x){
  const box=root.closest('dialog')||root;
  box.querySelectorAll('.gd-cta[data-command],.gd-hint[data-command]').forEach(el=>{
    const w=waitFor(x,el);if(!w)return;
    const left=w[1]-(x.now()-w[0]),label=el.querySelector('b')||el;
    if(el.dataset.hsLabel==null)el.dataset.hsLabel=label.innerHTML;
    const wait=`⏳ Chờ ${Math.ceil(left)} giây cho ${w[2]}…`;
    if(left>0){el.disabled=true;if(label.textContent!==wait)label.textContent=wait;}
    else if(el.disabled){el.disabled=false;label.innerHTML=el.dataset.hsLabel;}
  });
}

/* Scroll targets stay clear of the sticky sheet header and the sticky next-step bar (phones). */
function keepClear(root){
  const d=root.closest('dialog'),head=d?.querySelector('.sheet-head'),bar=root.querySelector('.hs-bar');
  const h=head&&getComputedStyle(head).position==='sticky'?head.offsetHeight:0;
  const b=bar&&getComputedStyle(bar).position==='sticky'?bar.offsetHeight:0;
  if(root.dataset.hsClear!==h+':'+b){root.dataset.hsClear=h+':'+b;root.style.setProperty('--hs-head',h+'px');root.style.setProperty('--hs-barh',b+'px');}
}
/* When a step is finished, bring the next step's card into view (once per change, never while the player just scrolls). */
function followStep(root,x){
  const cards=[...root.querySelectorAll('.wb-main>.hs-step-card')],cur=cards.find(c=>!c.classList.contains('done'));
  const key=`${x.room.active_task||''}:${cards.indexOf(cur)}`;
  const was=x.ui.hsFollow;x.ui.hsFollow=key;
  if(!cur||was==null||was===key||was.split(':')[0]!==key.split(':')[0])return;
  cur.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
}

const JOBS={checkin:[checkinJob,checkinSide],checkout:[checkoutJob,checkoutSide],breakfast:[breakfastJob,breakfastSide],booking:[bookingJob,bookingSide],recommend:[recommendJob,recommendSide],claim:[claimJob,claimSide]};

function board(x,t){
  return `<h4 class="section-title">🗓️ Lịch phòng 7 ngày</h4>${t&&t.job==='booking'&&t.known?'<p class="small muted">Lịch ở ngay bước 1 phía trên.</p>':calendar(x)}
    ${otaPanel(x)}${careList(x,false)}
    <h4 class="section-title">🧹 Buồng phòng</h4>${housekeeping(x)}${gardenCard(x)}${bookPanel(x)}`;
}
const IDLE_TABS=[['cal','🗓️ Lịch'],['rooms','🧹 Buồng'],['garden','🌸 Vườn'],['book','📖 Sổ']];
const caller=size=>`<span class="hs-caller" style="width:${size}px;height:${size}px" aria-hidden="true">📞</span>`;
function ticketCard(t,x,size=48){
  const who=x.npc(t.npc),anon=t.job==='claim';
  const pill=`<span class="tag blue">${JOB_ICON[t.job]||''} ${x.esc(x.cc.jobs?.[t.job]||t.job)}</span>`;
  const line=t.job==='recommend'?t.needs.request:t.job==='checkout'?t.needs.claim:t.job==='claim'?t.needs.note:t.needs.note||t.opening;
  return `<article class="card ticket hs-tk"><div class="hs-tk-head">${anon?caller(32):x.portrait(who,32)}<h3>${anon?'Người gọi':x.esc(who.display_name)}</h3><div class="patience" title="Kiên nhẫn"><div class="bar ${t.patience<50?'low':''}"><i style="width:${t.patience}%"></i></div><small>${t.patience}%</small></div>${pill}</div>
      <p class="small">${x.esc(line)}</p>${regularCard(t,x)}</article>`;
}

export default {
  id:'homestay',
  css:true,
  next(t,x){
    try{const n=x&&pending(taskGuide(t,x).steps);if(n)return x.esc(stepLine(n));}catch{/* fall back to the fixed lines */}
    if(x?.room?.data?.desk?.ev)return 'Có chuyện ở quầy cần quyết';
    if(!t.known)return t.job==='claim'?'Nghe cuộc gọi':'Nghe khách nói';
    const n=t.needs;
    if(t.job==='checkin'){const ci=t.ci;if(!ci.verified)return 'Khớp mã đặt phòng';if(!ci.ids)return 'Xem giấy tờ, khai báo lưu trú';if(!ci.counted)return 'Đếm khách';if(!ci.extra)return 'Quyết định người đi thêm';if(!ci.rooms.length)return 'Giao phòng sạch, trống đủ đêm';if(n.cold&&!ci.heater)return 'Lắp gas máy sưởi';return 'Trao chìa khóa & thu tiền';}
    if(t.job==='checkout'){if(!t.checked)return 'Kiểm phòng trước khi tính';if(t.check?.lost&&!t.returned)return 'Trả đồ khách bỏ quên';return 'Lập hóa đơn từng dòng';}
    if(t.job==='breakfast'){if(t.tray.pan)return 'Nhấc trứng đúng giây';return 'Chiên trứng, bánh mì, đồ uống';}
    if(t.job==='booking')return t.hold.length?(t.haggles?'Báo lại mức giá khác':'Nhận cọc & gửi xác nhận'):'Chọn phòng trống mọi đêm';
    if(t.job==='claim')return Object.keys(t.answers||{}).length<2?'Hỏi người gọi để xác minh':'Quyết định giao đồ';
    return t.picks.length>=n.count?'Gửi lịch trình':'Hỏi thêm rồi chọn nơi';
  },
  idle(x){
    const d=x.room.data||{},steps=idleSteps(x),todo=pending(steps)?.go;
    const hint=todo?nextHint(x,steps,{}):'',bar=todo?`<div class="hs-bar">${stepCta(x,steps,{label:'',go:null,ready:false})}</div>`:'';
    const stats=`<div class="row wrap hs-stats">${d.synced?x.pill(`📥 ${d.synced} đơn OTA đã đồng bộ`,'green'):''}${d.claims_ok?x.pill(`🎁 ${d.claims_ok} món đồ về đúng chủ`,'green'):''}${d.ota_walked?x.pill(`🏡 ${d.ota_walked} khách phải chuyển nhà hàng xóm`,'amber'):''}${d.claims_bad?x.pill(`⚠️ ${d.claims_bad} lần giao nhầm đồ`,'amber'):''}${d.lost_deposit?x.pill(`💸 mất ${d.lost_deposit} xu cọc ảo`,'amber'):''}</div>`;
    const tab=x.ui.hsTab||'cal';
    const tabs=`<div class="hs-tabs" role="tablist" aria-label="Khu trong nhà">${IDLE_TABS.map(([id,label])=>carBtn(x,label,'tab',{tab:id},`hs-tab ${tab===id?'on':''}`,` role="tab" aria-selected="${tab===id}"`)).join('')}</div>`;
    const pane=tab==='rooms'?`${housekeeping(x)}`:tab==='garden'?gardenCard(x):tab==='book'?bookPanel(x,true):calendar(x);
    return `<div class="career-job hs hs-idle">${hint}${deskCard(x)}${lastDesk(x)}${todayChip(x)}${stats}${careList(x,true)}${otaPanel(x,true)}${running(null,x)}
      ${tabs}<section class="hs-tabpane" role="tabpanel">${pane}</section>${foot(x)}${rules(x)}${bar}</div>`;
  },
  job(t,x){
    const desk=deskCard(x),who=x.npc(t.npc),g=taskGuide(t,x),hint=hintFor(g,x);
    // The calendar and the rooms are shared state: folded under the task so the task comes first.
    const more=`<section class="hs-board">${panel(x,'board','🗓️ Lịch phòng, buồng phòng, vườn & sổ',board(x,t),false,'hs-boardp')}${foot(x)}${rules(x)}</section>`;
    if(!t.known){
      const pill=`<span class="tag blue">${JOB_ICON[t.job]||''} ${x.esc(x.cc.jobs?.[t.job]||t.job)}</span>`;
      const anon=t.job==='claim';
      return `<div class="career-job hs">${hint}${desk}${desk?running(t,x):lastDesk(x)}${todayLine(x)}<article class="card ticket"><div class="row">${anon?caller(56):x.portrait(who,56)}<div class="grow"><div class="row spread"><h3>${anon?'Có cuộc gọi':x.esc(who.display_name)}</h3>${pill}</div><p>“${x.esc(t.opening)}”</p>${anon?'':regularCard(t,x)}</div></div>${x.cmd(t.job==='claim'?'📞 Nghe máy':'👂 Nghe khách','ask',{task:t.id},desk?'ghost full':'primary full gd-cta hs-ask',!!desk)}</article>${desk?bottomBar(g,x):more}</div>`;
    }
    if(desk)return `<div class="career-job hs">${hint}${desk}${running(t,x)}${ticketCard(t,x)}${bottomBar(g,x)}</div>`;
    const [main,side]=JOBS[t.job]||[()=>'',()=>''];
    // The steps and the receipt first; the one next-step button rides at the bottom of the sheet.
    return `<div class="career-job hs">${hint}${lastDesk(x)}${todayLine(x)}${ticketCard(t,x)}${running(t,x,false)}<div class="workbench"><section class="wb-main">${main(t,x)}</section><aside class="wb-side">${side(t,x)}</aside></div>
      ${more}${bottomBar(g,x)}</div>`;
  },
  tick(root,x){keepBarAboveFooter(root);keepClear(root);holdUntilReady(root,x);followStep(root,x);},
  // The egg pan and the open windows (v4/careers.js): the bars glide on the compositor, the words change five times a
  // second. "Nhấc trứng" / "báo phòng sạch" hold them where they were when the finger came down (tapStop).
  meters(root,x){
    const w=x.cc.egg||{raw:5,runny:11,well:18},air=airOf(x);
    root.querySelectorAll('[data-hs-timer]').forEach(el=>{
      const start=Number(el.dataset.start);if(!start)return;
      const s=Math.max(0,x.now()-start),pan=el.dataset.hsTimer==='pan',scale=pan?PAN_SCALE:AIR_SCALE;
      x.slide(el.querySelector('.fill'),s/scale*100,100/scale,true);
      {const l=el.querySelector('.hs-timer-label'),text=s.toFixed(1)+' giây · '+(pan?(s<w.raw?'lòng trắng còn sống':s<=w.runny?'LÒNG ĐÀO — nhấc nếu khách thích':s<=w.well?'CHÍN KỸ':'cháy mất rồi!'):(s<air.damp?'phòng còn mùi ẩm':s<=air.cold?'thoáng mát, thơm gỗ thông':'phòng lạnh dần'));if(l.textContent!==text)l.textContent=text;}   // the meters run every frame: write only a change
      el.classList.toggle('ready',pan?(s>=w.raw&&s<=w.well):(s>=air.damp&&s<=air.cold));
      el.classList.toggle('over',pan?s>w.well:s>air.cold);
    });
  },
  tapStop:(op,p)=>op==='hs_plate'||(op==='hs_clean'&&p.step==='ready'),
  actions:{
    ...tillActions,
    async sel(data,el,x){
      const t=(x.room.tasks||[]).find(v=>v.id===data.task);if(!t)return;
      const sel=selection(x,t),id=data.room,on=sel.includes(id),drop=!on&&sel.length>=2?sel[0]:null;
      x.ui.sel=on?sel.filter(v=>v!==id):[...sel,id].slice(-2);
      x.render();
      const name=roomInfo(x,id).name,seats=t.job==='booking'&&t.needs?` · ${capOf(x,x.ui.sel)}/${counted(x,t.needs.adults,t.needs.kids)} chỗ`:'';
      x.toast(on?`Đã bỏ chọn ${name}${seats}.`:drop?`Tối đa 2 phòng: bỏ ${roomInfo(x,drop).name}, chọn ${name}${seats}.`:`Đã chọn ${name}${seats}.`,'hint');
    },
    async clear(data,el,x){x.ui.sel=[];x.render();},
    async tab(data,el,x){x.ui.hsTab=IDLE_TABS.some(([id])=>id===data.tab)?data.tab:'cal';x.render();},
    async hk(data,el,x){x.ui.hk=x.ui.hk===data.room?null:data.room;x.render();},
    async fold(data,el,x){if(!/^[a-z][a-z0-9-]{0,20}$/.test(data.key||''))return;x.ui.open=x.ui.open||{};x.ui.open[data.key]=!data.open;x.render();},
    async rate(data,el,x){
      if(!(x.cc.rates||[]).some(r=>r.id===data.rate))return;
      x.ui.rate=x.ui.rate||{};x.ui.rate[data.task]=data.rate;x.render();
    },
    async ota(data,el,x){
      x.ui.ota=x.ui.ota||{};
      const cur=x.ui.ota[data.order]||[],id=data.room;
      x.ui.ota[data.order]=cur.includes(id)?cur.filter(v=>v!==id):[...cur,id].slice(-2);
      x.render();
    },
  },
  dock:[['inventory','box','Kho','Khăn, ga, bữa sáng']],
  // Day summary: "🌅 Ngày mai" (who checks in tomorrow evening, rooms still dirty, the forecast, the shelf) first.
  summary(data,x){
    const d=x.room.data||{},day=d.today??x.room.day,dirty=Array.isArray(data?.dirty)?data.dirty:[];
    const come=(d.bookings||[]).filter(b=>b.start===day).map(b=>`${x.esc(b.name)} (${b.rooms.map(r=>x.esc(roomInfo(x,r).name)).join(', ')})`);
    const plan=[come.length?`🛏️ Tối mai nhận phòng: <b>${come.slice(0,3).join(' · ')}</b>${come.length>3?` · +${come.length-3}`:''}`:'',
      dirty.length?`🧹 Phòng cần dọn: <b>${x.esc(dirty.join(', '))}</b>`:''];
    return tomorrowCard(x,data,{lift:/chờ đồng bộ|chưa ký sổ kiểm tra an toàn|^Dự báo ngày mai/,plan,title:'🏡 Sổ nhà hôm nay',
      labels:{arrived:'Khách nhận phòng',walked:'Khách phải chuyển chỗ',moved:'Khách đổi phòng'}});
  },
};
