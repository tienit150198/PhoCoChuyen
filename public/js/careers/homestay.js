/** Homestay Mây Đà Lạt — front desk, 7-day room calendar, app-order inbox, housekeeping workbench,
 *  lost-and-found calls and the surprises that walk in at the counter. */
const PAN_SCALE=24;   // seconds shown on the frying-pan bar
const AIR_SCALE=120;  // seconds shown on the window-airing bar
const JOB_ICON={checkin:'🔑',checkout:'🧾',breakfast:'🍳',booking:'📅',recommend:'🗺️',claim:'📞'};
const STATUS={clean:['Sạch','green'],dirty:['Cần dọn','amber'],occupied:['Có khách','blue'],maintenance:['Bảo trì','danger']};
const CELL={occ:'🛏️',book:'📌',maint:'🔧',free:''};
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

function checklist(x,rows){
  return `<ul class="checklist">${rows.map(([ok,label,note])=>`<li class="${ok===true?'ok':ok===false?'bad':''}"><span>${ok===true?'✓':ok===false?'✗':'○'}</span>${x.esc(label)}${note?`<small>${x.esc(note)}</small>`:''}</li>`).join('')}</ul>`;
}
function selection(x,t){
  if(x.ui.selTask!==t.id){x.ui.selTask=t.id;x.ui.sel=[];}
  return x.ui.sel;
}
function step(n,title,done,body){
  return `<section class="hs-step-card ${done?'done':''}"><h4 class="section-title"><span class="hs-num">${done?'✓':n}</span>${title}</h4>${body}</section>`;
}
function bar(kind,start,zones,scale){
  return `<div class="hs-timer ${kind}" data-hs-timer="${kind}" data-start="${start||''}">
    <div class="hs-track">${zones.map(([cls,a,b])=>`<i class="zone ${cls}" style="left:${a/scale*100}%;width:${(b-a)/scale*100}%"></i>`).join('')}<b class="fill" style="width:0%"></b></div>
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
  const score=d.score!=null?`<span class="hs-score" title="Điểm trung bình trên app đặt phòng">⭐ ${Number(d.score).toFixed(1)} trên app</span>`:'';
  return `<p class="hs-today"><span aria-hidden="true">${x.esc(m.emoji)}</span> <b>Hôm nay: ${x.esc(m.title)}</b> <small>${x.esc(m.text)}</small>${score}</p>`;
}
function deskCard(x){
  const ev=x.room.data?.desk?.ev;if(!ev)return '';
  const who=x.npc(ev.npc);
  const opts=ev.options.map(o=>`<button type="button" class="btn ghost hs-opt" ${cmdAttr(x,'hs_desk',{option:o.id})} ${o.cost>x.room.money?'disabled':''}><b>${x.esc(o.label)}</b>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}</button>`).join('');
  return `<section class="hs-desk ${x.esc(ev.tone||'')}" role="alert" aria-live="assertive"><div class="hs-desk-head"><span class="hs-desk-emoji" aria-hidden="true">${x.esc(ev.emoji)}</span><div class="grow"><small>CHUYỆN Ở QUẦY</small><h3>${x.esc(ev.title)}</h3></div>${x.portrait(who,40)}</div>
    <p>${x.esc(ev.text)}</p><div class="hs-opts">${opts}</div><p class="hs-note">Trứng trong chảo, phòng đang mở cửa sổ vẫn xử lý được; việc khác chờ quyết xong chuyện này.</p></section>`;
}
function lastDesk(x){const l=x.room.data?.desk?.last;if(!l||l.day!==x.room.day)return '';return `<p class="hs-last ${l.good===true?'good':l.good===false?'bad':''}" aria-live="polite"><span aria-hidden="true">${x.esc(l.emoji)}</span> <b>${x.esc(l.title)}:</b> ${x.esc(l.outcome)}</p>`;}
function foot(x){
  const d=x.room.data||{},busy=deskOpen(x);
  return `<p class="row wrap hs-foot">${x.cmd(d.safe_today?'✅ Đã ký sổ an toàn hôm nay':'🧯 Kiểm tra an toàn & ký sổ','hs_safety',{},'ghost small',!!d.safe_today||busy)}${x.button('📦 Kho & nhập hàng','inventory',{},'ghost small')}</p>`;
}
function rules(x){return `<details class="hs-rules"><summary>📋 Nội quy nhà Mây</summary><ul>${(x.cc.rules||[]).map(r=>`<li>${x.esc(r)}</li>`).join('')}</ul></details>`;}

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
    :`<div class="row wrap">${x.cmd(`✅ Đồng bộ vào ${x.esc(r.name)}`,'hs_sync',{order:o.id,rooms:[o.room]},'ghost small',busy)}</div>`;
  return `<li class="hs-ota-row ${clash?'clash':''}"><div class="row spread"><b>${x.esc(o.ota)} · ${x.esc(o.name)}</b><span class="tag ${clash?'danger':'green'}">${clash?'⚠️ Trùng':'Trống'}</span></div>
    <small>${r.emoji} ${x.esc(r.name)} · đêm ${o.start}${o.nights>1?'–'+end:''} · ${o.guests} khách · app chuyển ${x.money(o.net)} (đã trừ ${x.cc.commission||15}%)</small>
    ${clash?`<p class="hs-warn">⚠️ ${x.esc(clash)} — app đã bán trùng.</p>`:''}${actions}</li>`;
}
function otaPanel(x,open=false){
  const list=pendingOrders(x);
  if(!list.length)return '';
  const clashes=list.filter(o=>roomFree(x,o.room,o.start,o.nights,o.id)).length;
  return `<details class="hs-ota" ${open||clashes?'open':''}><summary>📥 Hộp đơn OTA · ${list.length} chờ đồng bộ${clashes?` · <b class="hs-bad">${clashes} trùng phòng</b>`:''}</summary>
    <p class="small muted">App bán phòng mà không nhìn lịch nhà. Đồng bộ trước khi khách tới; đơn trùng để tới tối là khách tới nơi không có phòng.</p>
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
    const name=`${r.emoji} ${x.esc(r.name)}<small>${r.cap}👤${r.stairs?' · 🪜':''}${locked?' · 🔒':''}</small>`;
    const label=selectable&&!locked?`<button type="button" class="hs-rname" data-action="car:sel" data-task="${x.esc(task)}" data-room="${x.esc(r.id)}" aria-pressed="${picked.includes(r.id)}">${name}</button>`:`<span class="hs-rname">${name}</span>`;
    const cells=(d.grid[r.id]||[]).map(c=>{
      const ota=wanted[r.id+':'+c.day],clash=ota&&(c.kind!=='free'||ota.length>1);
      const label=(c.label||'Trống')+(ota?` · đơn OTA chờ: ${ota.join(', ')}`:'');
      return `<span class="hs-cell ${c.kind} ${inRange(c.day)?'want':''} ${ota?'ota':''} ${clash?'clash':''}" title="${x.esc(label)}" aria-label="Ngày ${c.day}: ${x.esc(label)}">${CELL[c.kind]||''}${ota?'<i aria-hidden="true">📥</i>':''}</span>`;
    }).join('');
    return `<div class="hs-row ${picked.includes(r.id)?'picked':''} ${locked?'locked':''} st-${x.esc(room?.status||'')}">${label}${cells}</div>`;
  }).join('');
  return `<div class="hs-cal-wrap"><div class="hs-cal">${head}${rows}</div></div>
    <p class="hs-legend small muted">🛏️ có khách · 📌 đã đặt · 📥 đơn OTA chưa đồng bộ · 🔧 bảo trì · 🪜 phải leo cầu thang${range?' · cột tô màu = đêm khách hỏi':''}</p>`;
}

/* ---------------------------------------------------------------- housekeeping */
function housekeeping(x){
  const d=x.room.data||{};if(!d.rooms)return '';
  const cards=x.cc.rooms.map(r=>{
    const room=d.rooms[r.id],locked=r.unlock>d.level,[label,kind]=STATUS[room.status]||['?',''];
    let body='';
    if(room.status==='occupied')body=`<small>${x.esc(room.guest||'Khách')} · trả phòng ngày ${room.until}</small>`;
    else if(room.status==='clean')body=`<small class="hs-stars" aria-label="Điểm buồng phòng ${room.q}/5">${'★'.repeat(room.q)}${'☆'.repeat(Math.max(0,5-room.q))}</small>`;
    else if(room.status==='maintenance')body=`<small>${x.esc(room.note||'Đang sửa')}</small>${locked?(/cấp \d/.test(room.note||'')?'':`<small>🔒 mở ở cấp ${r.unlock}</small>`):x.confirmCmd('🔧 Gọi thợ','hs_repair',{room:r.id},'Gọi thợ sửa phòng này? Tiền công trả ngay, sau đó phòng cần dọn lại.','ghost small',deskOpen(x))}`;
    else body=x.button(room.hk?'🧹 Dọn tiếp':'🧹 Dọn phòng','car:hk',{room:r.id},'small ghost');
    return `<article class="hs-roomcard ${x.esc(room.status)} ${x.ui.hk===r.id?'active':''}"><div class="row spread"><b>${r.emoji} ${x.esc(r.name)}</b><span class="tag ${kind}">${label}</span></div><small class="muted">${r.cap} người · ${x.esc(r.beds)}</small>${body}</article>`;
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
    return `<button type="button" class="hs-hkstep ${ok?'done':''}" ${cmdAttr(x,'hs_clean',{room:rid,step:s.id})} ${ok||wait||(busy&&!free)?'disabled':''}><span class="n">${ok?'✓':i+1}</span><span class="e">${s.emoji}</span><span class="grow">${x.esc(s.name)}${use.length?`<small>−${x.esc(use.join(', '))}</small>`:''}</span></button>`;
  }).join('');
  return `<div class="hs-turnover card"><div class="row spread"><h4>🧹 Dọn phòng ${r.emoji} ${x.esc(r.name)}</h4>${x.button('Đóng','car:hk',{room:rid},'ghost small')}</div>
    <p class="small muted">Đúng thứ tự: tháo ga → phòng tắm → ga mới → khăn & minibar → kiểm → báo sạch. Mở cửa sổ ${air.damp}–${air.cold} giây cho hết mùi ẩm mà phòng không lạnh.${air.damp>(x.cc.air?.damp||15)?' 🌧️ Hôm nay mưa ẩm: mở lâu hơn thường lệ.':''}</p>
    ${bar('air',room.hk?.start,[['damp',0,air.damp],['fresh',air.damp,air.cold],['cold',air.cold,AIR_SCALE]],AIR_SCALE)}
    <div class="hs-hksteps">${steps}</div></div>`;
}
/* While a surprise waits at the counter: only the pan and rooms being aired can still be finished. */
function running(t,x){
  const d=x.room.data||{},parts=[];
  if(t&&t.known&&t.job==='breakfast'&&t.tray.pan){
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
  const list=n.list.map(e=>`<button type="button" class="hs-entry ${ci.verified&&e.code===n.code&&e.start===t.day?'ok':''}" ${cmdAttr(x,'hs_verify',{task:t.id,entry:e.id})} ${ci.verified?'disabled':''}>
      <b>${x.esc(e.id)}</b><span class="grow">${x.esc(e.name)} · <code>${x.esc(e.code)}</code><small>nhận ngày ${e.start}${e.start===d.today?' (hôm nay)':''} · ${e.nights} đêm · ${e.guests} khách</small></span></button>`).join('');
  let proof='';
  if(n.proof==='bank'){
    const res={ok:['green','🏦 Sao kê đã có khoản cọc — đối chiếu xong.'],missing:['danger','🏦 Sao kê KHÔNG có khoản cọc: chuyển nhầm số tài khoản. Thu đủ tại quầy.']}[t.bank];
    proof=`<div class="hs-proof"><p class="small">💸 Cọc ${x.money(n.paid)} chuyển khoản qua ${x.esc(n.platform)} — khách đưa <b>ảnh chụp màn hình</b>.</p>${res?`<p class="tag ${res[0]}">${res[1]}</p>`:x.cmd('🏦 Mở app ngân hàng đối chiếu','hs_bank',{task:t.id},'ghost small')}</div>`;
  }
  const s1=step(1,'Khớp đặt phòng trên app',ci.verified,`<p class="small">Khách đọc mã <b>${x.esc(n.code)}</b>, tên <b>${x.esc(n.name)}</b> (${x.esc(n.platform)}). Chọn đúng dòng — coi chừng tên gần giống, số đảo, sai ngày.</p><div class="stack">${list}</div>${proof}`);
  const idText={ok:'Người lớn đều có giấy tờ tùy thân.',app:'Khách dùng ứng dụng định danh điện tử thay thẻ giấy — hợp lệ.'}[t.id_status]||'';
  const s2=step(2,'Giấy tờ & khai báo lưu trú',ci.ids,ci.ids?`<p class="small">🪪 ${x.esc(idText)} Đã khai báo lưu trú. <b>Không</b> ghi hay chụp số giấy tờ.</p>`:
    `<div class="row wrap">${x.cmd('👀 Xem giấy tờ & khai báo','hs_ids',{task:t.id,mode:'look'},st(t,x,'ids'),!ci.verified)}${x.cmd('📸 Chụp lưu giấy tờ vào máy','hs_ids',{task:t.id,mode:'photo'},'ghost small',!ci.verified)}</div><p class="small muted">🔒 Giấy tờ chỉ để xem và khai báo, trả lại ngay cho khách.</p>`);
  let s3body;
  if(!ci.counted)s3body=x.cmd('🧮 Đếm khách đang đứng ở quầy','hs_count',{task:t.id},st(t,x,'count'),!ci.verified);
  else{
    const kids=t.arrived.kids.length?`, ${t.arrived.kids.length} bé (${t.arrived.kids.join(', ')} tuổi)`:'';
    s3body=`<p class="small">👥 Có mặt ${t.arrived.adults} người lớn${x.esc(kids)} → <b>${arr} người tính chỗ</b> (đặt ${booked}).${t.arrived.kids.length?` <span class="muted">Bé dưới ${x.cc.kid_free_age} tuổi ngủ chung không tính.</span>`:''}</p>`;
    if(extra>0)s3body+=ci.extra&&ci.extra!=='none'?`<p class="tag ${ci.extra==='surcharge'?'green':'amber'}">${ci.extra==='surcharge'?`Phụ thu ${x.cc.extra_guest} xu/người/đêm + nệm phụ`:'Chỉ nhận đúng số người đã đặt'}</p>`:
      `<div class="notice amber">Dư ${extra} người so với đặt phòng.</div><div class="row wrap">${x.cmd(`➕ Phụ thu ${x.cc.extra_guest} xu/người/đêm`,'hs_extra',{task:t.id,choice:'surcharge'},'ghost small')}${x.cmd('🙅 Chỉ nhận đúng số đã đặt','hs_extra',{task:t.id,choice:'refuse'},'ghost small')}</div>`;
  }
  const s3=step(3,'Đếm khách',ci.counted&&ci.extra,s3body);
  const busyOf=id=>(d.grid?.[id]||[]).slice(0,n.nights).some(c=>c.kind!=='free')||!['clean','dirty'].includes(d.rooms[id].status);
  const dirtyOf=id=>d.rooms[id].status==='dirty';
  const tiles=x.cc.rooms.map(r=>{
    const room=d.rooms[r.id],locked=r.unlock>d.level;
    const busy=busyOf(r.id);
    const on=sel.includes(r.id)||(!sel.length&&ci.rooms.includes(r.id));
    return `<button type="button" class="tile ${on?'selected':''} ${locked?'locked':''} ${busy?'empty':''}" data-action="car:sel" data-task="${x.esc(t.id)}" data-room="${x.esc(r.id)}" aria-pressed="${on}" ${locked||(busy&&!on)?'disabled':''}><span class="tile-emoji">${r.emoji}</span><b>${x.esc(r.name)}</b><small>${locked?'🔒 cấp '+r.unlock:busy?x.esc(STATUS[room.status]?.[0]||'')+(room.status==='clean'?' · vướng lịch':''):room.status==='dirty'?`🧹 Cần dọn · ${r.cap} người`:r.cap+' người'}</small></button>`;
  }).join('');
  const pick=sel.length?sel:ci.rooms,cap=pick.reduce((a,id)=>a+roomInfo(x,id).cap,0),stale=pick.filter(id=>!ci.rooms.includes(id)&&busyOf(id));
  const given=ci.rooms.length>0&&(!sel.length||(sel.length===ci.rooms.length&&sel.every(id=>ci.rooms.includes(id))));
  const caps=x.cc.rooms.filter(r=>r.unlock<=d.level&&!busyOf(r.id)).map(r=>r.cap).sort((a,b)=>b-a);
  const full=ci.counted&&ci.extra&&!ci.rooms.length&&(caps[0]||0)+(caps[1]||0)<staying;
  const fee=(x.cc.walk_fee||15)+(t.bank==='missing'?0:n.paid);
  const walk=full?`<div class="notice amber space-top">Chưa phòng nào sạch và trống đủ ${n.nights} đêm cho ${staying} người. Dọn phòng bẩn hoặc làm xong trả phòng trước — nếu vẫn hết thật thì:</div>
    <div class="row wrap">${x.confirmCmd(`🏡 Chuyển sang Nhà Gỗ Cô Ba (−${fee} xu)`,'hs_relocate',{task:t.id},`Chỉ chọn khi không còn phòng nào dọn kịp hay sắp trả. Xin lỗi ${n.name}, hoàn cọc và trả ${x.cc.walk_fee||15} xu chênh lệch + taxi?`,'ghost small')}</div>`:'';
  const s4=step(4,n.size>staying?`Giao phòng (${n.nights} đêm, cần chỗ cho ${staying} người, khách đặt phòng ${n.size} người)`:`Giao phòng (${n.nights} đêm, cần chỗ cho ${staying} người)`,given,`<div class="tile-grid hs-tiles">${tiles}</div>
    <div class="row wrap space-top">${x.cmd(`🗝️ Giao ${pick.length?pick.map(id=>x.esc(roomInfo(x,id).name)).join(' + '):'phòng'} (${cap} chỗ)`,'hs_assign',{task:t.id,rooms:pick},st(t,x,'assign'),!(ci.counted&&ci.extra)||!pick.length||given||stale.length>0||(!given&&cap<staying))}</div>${stale.length?`<p class="small hs-warn">${x.esc(stale.map(id=>roomInfo(x,id).name).join(', '))} chưa sạch hoặc chưa trống — bỏ chọn, dọn xong rồi giao.</p>`:''}${!given&&pick.length&&cap<staying&&!stale.length?`<p class="small hs-warn">Mới đủ ${cap}/${staying} chỗ — chọn thêm một phòng (tối đa 2).</p>`:''}${pick.some(dirtyOf)?`<p class="small hs-warn">🧹 ${x.esc(pick.filter(dirtyOf).map(id=>roomInfo(x,id).name).join(', '))} chưa dọn — khách vào là thấy ngay. Dọn xong rồi hẵng trao chìa khóa.</p>`:''}${walk}`);
  const s5=n.cold?step(5,'Máy sưởi đêm lạnh',ci.heater,ci.heater?'<p class="small">🔥 Đã lắp gas, thử lửa, mở hé cửa thông gió.</p>':x.cmd(`🔥 Lắp gas máy sưởi (${x.stock('heater_gas')} bình)`,'hs_heater',{task:t.id},st(t,x,'heater',''),!ci.rooms.length||!x.stock('heater_gas'))):'';
  return s1+s2+s3+s4+s5;
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
    ${checklist(x,rows)}
    ${x.confirmCmd('🔑 Trao chìa khóa & thu tiền','hs_welcome',{task:t.id},`Trao chìa khóa và thu ${due} xu?`,st(t,x,'welcome')+' big full',!(ci.verified&&ci.ids&&ci.counted&&ci.extra&&ci.rooms.length))}`;
}

function checkoutJob(t,x){
  const n=t.needs,c=t.check,r=t.room?roomInfo(x,t.room):null,pkg=n.package;
  const free=t.truth_hint?.free_water??pkg?.water_free??x.cc.free_water;
  const where=r?`${r.emoji} Phòng ${x.esc(r.name)}`:'Phòng khách (ca đêm xếp)';
  let s1;
  if(!t.checked)s1=step(1,'Kiểm phòng trước khi tính tiền',false,`<p class="small">${where} · ${n.nights} đêm. Kiểm minibar, hư hỏng, đồ bỏ quên trong lúc khách chờ ở quầy.</p>${x.cmd('🔍 Báo buồng phòng kiểm','hs_inspect',{task:t.id},st(t,x,'inspect'))}`);
  else s1=step(1,'Kết quả kiểm phòng',true,`<div class="hs-minibar">
      <span>💧 ${c.water} chai <small>(${free} chai tặng)</small></span><span>🍜 ${c.noodles} ly mì</span><span>🍪 ${c.snack} gói bánh</span><span>☕ ${c.coffee} gói <small>(miễn phí)</small></span></div>
      <p class="small">${c.damage?`🏺 Hư hỏng: <b>${x.esc(c.damage)}</b>`:'✅ Không có hư hỏng.'}</p>
      ${c.lost?`<div class="notice ${t.returned?'green':'amber'}">🎒 Khách để quên: <b>${x.esc(c.lost)}</b> ${t.returned?'— đã trả tận tay.':x.cmd('Trả đồ cho khách','hs_return',{task:t.id},'small '+st(t,x,'return'))}</div>`:''}`);
  const lines=x.cc.bill_lines.map(l=>{const q=t.bill[l.id]||0;
    return `<div class="hs-line ${q?'on':''}"><span class="e">${l.emoji}</span><span class="grow">${x.esc(l.name)}<small>${l.price} xu/${x.esc(l.unit)}</small></span>
      ${x.cmd('−','hs_line',{task:t.id,line:l.id,delta:-1},'ghost small hs-qbtn',!t.checked||!q)}<b class="q">${q}</b>${x.cmd('+','hs_line',{task:t.id,line:l.id,delta:1},'ghost small hs-qbtn',!t.checked||q>=9)}</div>`;}).join('');
  const banner=pkg?`<div class="hs-package">🎁 <b>${x.esc(pkg.name)}</b>: ${x.esc(pkg.text)}.</div>`:'';
  const s2=step(2,'Lập hóa đơn từng dòng',false,`${banner}<p class="small muted">Khách nói: “${x.esc(n.claim)}”${n.laundry?` · Gửi giặt ${n.laundry} túi`:''}${n.late?' · Xin trả phòng sau 12h':''}. Nước: chỉ tính chai thứ ${free+1} trở đi.</p>${lines}`);
  return s1+s2;
}
function checkoutSide(t,x){
  const rows=x.cc.bill_lines.filter(l=>t.bill[l.id]).map(l=>`<div class="kv"><span>${l.emoji} ${x.esc(l.name)} × ${t.bill[l.id]}</span><b>${x.money(l.price*t.bill[l.id])}</b></div>`).join('');
  const total=x.cc.bill_lines.reduce((a,l)=>a+l.price*(t.bill[l.id]||0),0);
  return `<div class="hs-receipt"><h4>🧾 Hóa đơn trả phòng</h4>${rows||'<p class="small muted">Chưa có dòng nào. Tiền phòng đã thu khi nhận phòng.</p>'}<div class="kv total"><span>Tổng</span><b>${x.money(total)}</b></div></div>
    ${checklist(x,[[t.checked||null,'Kiểm phòng',''],...(t.check?.lost?[[t.returned||null,'Trả đồ bỏ quên',t.check.lost]]:[]),[t.disputes?false:null,'Khách đồng ý hóa đơn',t.disputes?`đã phải sửa ${t.disputes} lần`:'']])}
    ${x.confirmCmd('🧾 In hóa đơn & thu tiền','hs_settle',{task:t.id},`Thu ${total} xu theo hóa đơn này? Khách sẽ đọc từng dòng.`,st(t,x,'settle')+' big full',!t.checked)}`;
}

function breakfastJob(t,x){
  const n=t.needs,tray=t.tray,w=x.cc.egg||{raw:5,runny:11,well:18};
  const ask=t.gen?(t.diet?bubble(x,'Khách:',t.diet_say||''):`<div class="row wrap">${x.cmd('💬 Hỏi dị ứng, ăn kiêng','hs_diet',{task:t.id},'ghost small')}</div>`):'';
  const pan=`<div class="hs-pan">${bar('pan',tray.pan,[['raw',0,w.raw],['runny',w.raw,w.runny],['well',w.runny,w.well],['burnt',w.well,PAN_SCALE]],PAN_SCALE)}
    <div class="row wrap">${tray.pan?x.cmd('🥄 Nhấc trứng ra đĩa','hs_plate',{task:t.id},st(t,x,'plate')):x.cmd(`🍳 Đập trứng vào chảo (${x.stock('egg')})`,'hs_egg',{task:t.id},st(t,x,'egg',''),!x.stock('egg')||tray.eggs.length>=6)}</div>
    <p class="small muted">Lòng đào: ${w.raw}–${w.runny} giây · chín kỹ: ${w.runny}–${w.well} giây · sau ${w.well} giây là cháy.</p></div>`;
  const tiles=[['bread','🥖','Bánh mì nướng','hs_bread',6],['milk','🥛','Sữa tươi ấm','hs_milk',4],['coffee','☕','Cà phê','hs_coffee',4]].map(([k,e,l,cmd,cap])=>{
    const q=x.stock(k),have=tray[k],want=n[k];
    return `<button type="button" class="tile ${!q?'empty':''} ${want?'wanted':''}" ${cmdAttr(x,cmd,{task:t.id})} ${!q||have>=cap?'disabled':''}><span class="tile-emoji">${e}</span><b>${l}</b><small>kho ${q}</small>${have?`<em class="tile-count">×${have}</em>`:''}</button>`;}).join('');
  return (ask?step('💬','Hỏi trước khi nấu',!!t.diet,ask):'')+step(1,'Chảo trứng',false,pan)+step(2,'Bánh mì & đồ uống',false,`<div class="tile-grid hs-tiles">${tiles}</div>`);
}
function breakfastSide(t,x){
  const n=t.needs,tray=t.tray,want=t.eggs_fix||n.eggs;
  const eggs=tray.eggs.map(e=>`<span class="hs-egg ${e}" title="${EGG_LABEL[e]}">🍳<small>${EGG_LABEL[e]}</small></span>`).join('');
  const got={runny:tray.eggs.filter(e=>e==='runny').length,well:tray.eggs.filter(e=>e==='well').length};
  const rows=[];
  if(want.runny||got.runny)rows.push([got.runny?got.runny===want.runny:null,`${want.runny} trứng lòng đào`,`${got.runny}/${want.runny}`]);
  if(want.well||got.well)rows.push([got.well?got.well===want.well:null,`${want.well} trứng chín kỹ`,`${got.well}/${want.well}`]);
  for(const [k,l] of [['bread','bánh mì'],['milk','sữa'],['coffee','cà phê']])if(n[k]||tray[k])rows.push([tray[k]?tray[k]===n[k]:null,`${n[k]} ${l}`,`${tray[k]}/${n[k]}`]);
  if(tray.eggs.some(e=>e==='raw'||e==='burnt'))rows.push([false,'Trứng hỏng trên khay','dọn khay làm lại']);
  if(n.allergy==='egg'||t.eggs_fix)rows.push([tray.eggs.length<=want.runny+want.well,'⚠️ Một người dị ứng trứng','không thêm trứng']);
  return `<div class="hs-tray"><h4>🍽️ Khay ${x.esc(n.where.toLowerCase())} · ${n.people} người</h4><div class="hs-eggs">${eggs||'<small class="muted">Chưa có trứng</small>'}</div>
    <p class="small">${'🥖'.repeat(tray.bread)}${'🥛'.repeat(tray.milk)}${'☕'.repeat(tray.coffee)}</p></div>${checklist(x,rows)}
    <div class="stack">${x.confirmCmd(`✅ Mang ra cho khách · ${x.money(t.quoted_price||0)}`,'hs_serve',{task:t.id},'Mang khay này ra? Khách ăn và đánh giá đúng những gì trên khay.',st(t,x,'serve')+' big full',!!tray.pan||!(tray.bread||tray.eggs.length)||tray.eggs.includes('raw'))}
    ${x.confirmCmd('🗑️ Dọn khay làm lại','hs_toss',{task:t.id},'Bỏ khay này? Nguyên liệu đã dùng ghi vào hao hụt.',st(t,x,'toss','danger')+' small',!(tray.eggs.length||tray.bread||tray.milk||tray.coffee||tray.pan))}</div>`;
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
  body+=`<p class="small">Chạm tên phòng để chọn (tối đa 2). Đang chọn: <b>${pick.map(id=>x.esc(roomInfo(x,id).name)).join(' + ')||'—'}</b> · ${cap}/${need} chỗ · ~${x.money(total)}</p>`;
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
    price2=step(2,'Báo giá theo mùa',false,`<div class="hs-chips" role="group" aria-label="Mức giá">${chips}</div>${t.haggles?`<p class="hs-warn">Khách đã chê giá ${t.haggles} lần — báo lại mức khác.</p>`:''}<div class="space-top">${said}</div>`);
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
    ${stale?'<div class="notice amber">Ngày khách hỏi đã qua. Báo lại lịch sự thôi.</div>':''}${checklist(x,rows)}
    <div class="stack">${x.confirmCmd(`💰 Nhận cọc${t.quote?' '+x.money(t.quote.deposit):''} & gửi xác nhận`,'hs_book',{task:t.id},'Nhận cọc và ghi lịch? Tin xác nhận kèm nội quy sẽ gửi cho khách.',st(t,x,'book')+' big full',!t.hold.length||stale)}
    ${x.confirmCmd('🙏 Báo hết phòng, giới thiệu Nhà Gỗ Cô Ba','hs_decline',{task:t.id},'Báo khách không còn phòng phù hợp và giới thiệu homestay hàng xóm?','ghost small')}</div>`;
}

function recommendJob(t,x){
  const n=t.needs,ans=t.answers||{};
  const avoid=new Set([...n.avoid,...Object.values(ans).flatMap(a=>a.avoid)]),wants=new Set([...n.wants,...Object.values(ans).flatMap(a=>a.want)]);
  const probes=x.cc.probes.map(p=>ans[p.id]?`<div class="bubble npc small"><b>${p.emoji} ${x.esc(p.label)}</b><br>${x.esc(ans[p.id].answer)}</div>`:
    x.cmd(`${p.emoji} ${x.esc(p.label)}`,'hs_probe',{task:t.id,q:p.id},'ghost small')).join('');
  const places=x.cc.places.map(p=>{
    const on=t.picks.includes(p.id),clash=p.tags.filter(tag=>avoid.has(tag));
    return `<button type="button" class="hs-place ${on?'selected':''} ${clash.length?'clash':''}" ${cmdAttr(x,'hs_pick',{task:t.id,place:p.id})} aria-pressed="${on}">
      <span class="tile-emoji">${p.emoji}</span><b>${x.esc(p.name)}</b><small>${x.esc(p.blurb)}</small>
      <span class="hs-tags">${p.tags.map(tag=>`<i class="${avoid.has(tag)?'bad':wants.has(tag)?'good':''}">${x.esc(x.cc.tag_names[tag]||tag)}</i>`).join('')}</span></button>`;}).join('');
  return step(1,'Hỏi thêm cho chắc',Object.keys(ans).length>=3,`<div class="row wrap hs-probes">${probes}</div>`)+step(2,`Chọn ${n.count}–3 nơi`,t.picks.length>=n.count,`<div class="hs-places">${places}</div>`);
}
function recommendSide(t,x){
  const n=t.needs,ans=t.answers||{};
  const avoid=[...new Set([...n.avoid,...Object.values(ans).flatMap(a=>a.avoid)])],wants=[...new Set([...n.wants,...Object.values(ans).flatMap(a=>a.want)])];
  const tagsOf=id=>x.cc.places.find(p=>p.id===id)?.tags||[];
  const rows=wants.map(w=>[t.picks.length?t.picks.some(id=>tagsOf(id).includes(w)):null,'Có nơi '+(x.cc.tag_names[w]||w),'']).concat(avoid.map(a=>[t.picks.length?!t.picks.some(id=>tagsOf(id).includes(a)):null,'Tránh: '+(x.cc.tag_names[a]||a),'']));
  return `<div class="hs-receipt"><h4>🗺️ Lịch trình vẽ tay</h4>${t.picks.map((id,i)=>{const p=x.cc.places.find(v=>v.id===id);return `<div class="kv"><span>${i+1}. ${p.emoji} ${x.esc(p.name)}</span></div>`;}).join('')||'<p class="small muted">Chưa chọn nơi nào.</p>'}</div>
    ${checklist(x,rows)}<p class="small muted">Chỉ thấy điều khách đã kể. Hỏi thêm để biết điều cần tránh.</p>
    ${x.confirmCmd('✉️ Gửi lịch trình cho khách','hs_advise',{task:t.id},'Gửi lịch trình này? Khách sẽ đi đúng những nơi bạn gợi ý.',st(t,x,'advise')+' big full',t.picks.length<n.count)}`;
}

function claimJob(t,x){
  const n=t.needs,e=n.entry,r=roomInfo(x,e.room),ans=t.answers||{};
  const log=`<div class="hs-lostcard"><span class="hs-lost-emoji" aria-hidden="true">${x.esc(e.emoji)}</span><div class="grow"><b>${x.esc(e.item)}</b><small>${x.esc(e.detail)}</small>
    <ul class="hs-facts"><li>🚪 Tìm thấy ở <b>${x.esc(r.name)}</b></li><li>📅 Khách trả phòng <b>ngày ${e.day}</b></li><li>🧾 Đặt phòng: <b>${x.esc(e.booker)}</b></li></ul></div></div>`;
  const qs=(x.cc.claim_qs||[]).map(q=>ans[q.id]?`<div class="hs-bubble"><b>${q.emoji} ${x.esc(q.label)}</b> “${x.esc(ans[q.id])}”</div>`
    :x.cmd(`${q.emoji} ${x.esc(q.label)}`,'hs_quiz',{task:t.id,q:q.id},'ghost small')).join('');
  return step(1,'Sổ đồ thất lạc ghi',true,log)+step(2,'Hỏi người gọi để xác minh',Object.keys(ans).length>=2,`<div class="stack hs-claim-q">${qs}</div><p class="small muted">So từng câu với sổ: món đồ, phòng, ngày, tên người đặt. Người khác gọi hộ thì phải có xác nhận của người đặt phòng.</p>`);
}
function claimSide(t,x){
  const asked=Object.keys(t.answers||{}).length;
  const btns=CLAIM_CHOICES.map(([id,label,q])=>x.confirmCmd(label,'hs_claim',{task:t.id,choice:id},q,'ghost full')).join('');
  return `<div class="hs-receipt"><h4>📞 Cuộc gọi hỏi đồ</h4><p class="small">“${x.esc(t.needs.note)}”</p><div class="kv"><span>Đã hỏi</span><b>${asked}/${(x.cc.claim_qs||[]).length} câu</b></div></div>
    <div class="stack">${btns}</div><p class="small muted">Nội quy: chỉ giao cho người đặt phòng hoặc người được họ xác nhận qua kênh đặt phòng.</p>`;
}

const JOBS={checkin:[checkinJob,checkinSide],checkout:[checkoutJob,checkoutSide],breakfast:[breakfastJob,breakfastSide],booking:[bookingJob,bookingSide],recommend:[recommendJob,recommendSide],claim:[claimJob,claimSide]};

function board(x,t){
  return `<h4 class="section-title">🗓️ Lịch phòng 7 ngày</h4>${t&&t.job==='booking'&&t.known?'<p class="small muted">Lịch ở ngay bước 1 phía trên.</p>':calendar(x)}
    ${otaPanel(x)}
    <h4 class="section-title">🧹 Buồng phòng</h4>${housekeeping(x)}`;
}
const caller=size=>`<span class="hs-caller" style="width:${size}px;height:${size}px" aria-hidden="true">📞</span>`;
function ticketCard(t,x,size=48){
  const who=x.npc(t.npc),anon=t.job==='claim';
  const pill=`<span class="tag blue">${JOB_ICON[t.job]||''} ${x.esc(x.cc.jobs?.[t.job]||t.job)}</span>`;
  const line=t.job==='recommend'?t.needs.request:t.job==='checkout'?t.needs.claim:t.job==='claim'?t.needs.note:t.needs.note||t.opening;
  return `<article class="card ticket"><div class="row">${anon?caller(size):x.portrait(who,size)}<div class="grow"><div class="row spread"><h3>${anon?'Người gọi':x.esc(who.display_name)}</h3>${pill}</div>
      <p class="small">${x.esc(line)}</p>
      <div class="patience" title="Kiên nhẫn"><div class="bar ${t.patience<50?'low':''}"><i style="width:${t.patience}%"></i></div><small>${t.patience}%</small></div></div></div></article>`;
}

export default {
  id:'homestay',
  css:true,
  next(t,x){
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
    const d=x.room.data||{};
    const stats=`<div class="row wrap hs-stats">${d.synced?x.pill(`📥 ${d.synced} đơn OTA đã đồng bộ`,'green'):''}${d.claims_ok?x.pill(`🎁 ${d.claims_ok} món đồ về đúng chủ`,'green'):''}${d.ota_walked?x.pill(`🏡 ${d.ota_walked} khách phải chuyển nhà hàng xóm`,'amber'):''}${d.claims_bad?x.pill(`⚠️ ${d.claims_bad} lần giao nhầm đồ`,'amber'):''}${d.lost_deposit?x.pill(`💸 mất ${d.lost_deposit} xu cọc ảo`,'amber'):''}</div>`;
    return `<div class="career-job hs hs-idle">${deskCard(x)}${lastDesk(x)}${todayChip(x)}${stats}${otaPanel(x,true)}${running(null,x)}
      <h4 class="section-title">🗓️ Lịch phòng 7 ngày</h4>${calendar(x)}<h4 class="section-title">🧹 Buồng phòng</h4>${housekeeping(x)}${foot(x)}${rules(x)}</div>`;
  },
  job(t,x){
    const desk=deskCard(x),who=x.npc(t.npc);
    if(!t.known){
      const pill=`<span class="tag blue">${JOB_ICON[t.job]||''} ${x.esc(x.cc.jobs?.[t.job]||t.job)}</span>`;
      const anon=t.job==='claim';
      return `<div class="career-job hs">${desk}${desk?running(t,x):lastDesk(x)}${todayChip(x)}<article class="card ticket"><div class="row">${anon?caller(56):x.portrait(who,56)}<div class="grow"><div class="row spread"><h3>${anon?'Có cuộc gọi':x.esc(who.display_name)}</h3>${pill}</div><p>“${x.esc(t.opening)}”</p></div></div>${x.cmd(t.job==='claim'?'📞 Nghe máy':'👂 Nghe khách','ask',{task:t.id},desk?'ghost full':'primary full',!!desk)}</article>${desk?'':board(x,t)+foot(x)+rules(x)}</div>`;
    }
    if(desk)return `<div class="career-job hs">${desk}${running(t,x)}${ticketCard(t,x)}</div>`;
    const [main,side]=JOBS[t.job]||[()=>'',()=>''];
    // The receipt and its one button sit right after the steps; the shared calendar and rooms come below.
    return `<div class="career-job hs">${lastDesk(x)}${todayChip(x)}${ticketCard(t,x)}<div class="workbench"><section class="wb-main">${main(t,x)}</section><aside class="wb-side">${side(t,x)}</aside></div>
      <section class="hs-board">${board(x,t)}${foot(x)}${rules(x)}</section></div>`;
  },
  tick(root,x){
    const w=x.cc.egg||{raw:5,runny:11,well:18},air=airOf(x);
    root.querySelectorAll('[data-hs-timer]').forEach(el=>{
      const start=Number(el.dataset.start);if(!start)return;
      const s=Math.max(0,x.now()-start),pan=el.dataset.hsTimer==='pan',scale=pan?PAN_SCALE:AIR_SCALE;
      el.querySelector('.fill').style.width=Math.min(100,s/scale*100)+'%';
      el.querySelector('.hs-timer-label').textContent=s.toFixed(1)+' giây · '+(pan?(s<w.raw?'lòng trắng còn sống':s<=w.runny?'LÒNG ĐÀO — nhấc nếu khách thích':s<=w.well?'CHÍN KỸ':'cháy mất rồi!'):(s<air.damp?'phòng còn mùi ẩm':s<=air.cold?'thoáng mát, thơm gỗ thông':'phòng lạnh dần'));
      el.classList.toggle('ready',pan?(s>=w.raw&&s<=w.well):(s>=air.damp&&s<=air.cold));
      el.classList.toggle('over',pan?s>w.well:s>air.cold);
    });
  },
  actions:{
    async sel(data,el,x){
      const t=(x.room.tasks||[]).find(v=>v.id===data.task);if(!t)return;
      const sel=selection(x,t),id=data.room;
      x.ui.sel=sel.includes(id)?sel.filter(v=>v!==id):[...sel,id].slice(-2);
      x.render();
    },
    async clear(data,el,x){x.ui.sel=[];x.render();},
    async hk(data,el,x){x.ui.hk=x.ui.hk===data.room?null:data.room;x.render();},
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
};
