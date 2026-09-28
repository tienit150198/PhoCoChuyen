/** Nông Trại Đồi Gió — six plots, a hen house, the cold room and the packing
 *  table. Field state is persistent and turn-based; everything is recomputed
 *  on the server, the client only shows it. */
import {reqList} from '../ui-kit.js';
const ID='farm';
const STAGE={empty:'Luống trống',sprout:'Mới nhú',young:'Đang lớn',almost:'Sắp tới lứa',ripe:'Đúng lứa · thu được',over:'Quá lứa · xơ',rotten:'Hỏng · dọn luống'};
const ART={sprout:'🌱',young:'🌿'};
const DAYS=n=>n===0?'hôm nay':n===1?'mai':n===2?'ngày kia':`${n} ngày nữa`;
/* When will this bed be ready (server estimate with full care: eta/over_in in days, 0 = today). */
function when(p){
  if(!p.crop)return '';
  if(p.stage==='rotten')return 'Hỏng · dọn luống';
  if(p.stage==='over')return 'Quá lứa · chỉ loại B';
  if(p.stage==='ripe')return p.over_in==null?'Đúng lứa · thu được':p.over_in===0?'Đúng lứa · thu ngay hôm nay':`Đúng lứa · giữ được tới ${DAYS(p.over_in)}`;
  return p.eta==null?STAGE[p.stage]:`${STAGE[p.stage]} · chín ${DAYS(p.eta)}`;
}
const catalogue=x=>x.content.inventory?.items?.[ID]||[];
const supply=(x,id)=>catalogue(x).find(i=>i.id===id)||{id,name:id,emoji:'•',unit:''};
const produce=(x,id)=>id==='egg'?x.cc.egg:(x.cc.crops||[]).find(c=>c.id===id)||{id,name:id,emoji:'•',unit:''};
const sum=a=>a.reduce((s,v)=>s+v,0);
const pct=(v,max)=>Math.max(0,Math.min(100,v/max*100)).toFixed(1)+'%';
const tile=(x,command,payload,inner,cls='',disabled=false)=>`<button type="button" class="tile ${cls}" data-command="${command}" data-payload="${x.esc(JSON.stringify(payload))}"${disabled?' disabled':''}>${inner}</button>`;
const carBtn=(x,label,action,data={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-action="car:${action}"${Object.entries(data).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}${extra}>${label}</button>`;
const checklist=(x,rows)=>`<ul class="checklist">${rows.map(([ok,label,note])=>`<li class="${ok===true?'ok':ok===false?'bad':''}"><span>${ok===true?'✓':ok===false?'✗':'○'}</span>${x.esc(label)}${note?`<small>${x.esc(note)}</small>`:''}</li>`).join('')}</ul>`;
const data=x=>x.room.data||{plots:[],cold:[],coop:{},diary:[]};
const packed=(t,crop)=>sum((t.crate||[]).filter(e=>e.crop===crop).map(e=>e.qty));
/* Wholesale prices come in tenths of a xu. */
const xu=v=>(Number(v||0)/10).toLocaleString('vi-VN',{maximumFractionDigits:1});
const estimate=(row,grade,qty,slip)=>{let t=0;const base=grade==='A'?row.a:row.b;for(let i=0;i<qty;i++)t+=Math.max(1,Math.floor(base*Math.max(50,100-10*Math.floor((row.sold+i)/slip))/100));return Math.max(1,Math.floor((t+5)/10));};

/* ------------------------------------------------------------ weather + order */
function weatherBar(x){
  const d=data(x),w=d.weather||{},f=d.forecast||{},se=d.season,out=d.outlook||[];
  const flags=[d.nopump?'<span class="fa-flag bad">🚱 Trạm bơm cúp nước: chỉ tưới từng luống</span>':'',d.bees?'<span class="fa-flag">🐝 Ong đang ở cạnh vườn: đừng phun thuốc hóa học</span>':''].join('');
  const season=se?`<div class="fa-season"><span class="fa-sky" aria-hidden="true">${x.esc(se.emoji)}</span><div class="grow"><b>${x.esc(se.name)} · ngày ${se.day}/${se.days}</b><small>${x.esc(se.text)}</small></div>${se.day===se.days?`<span class="fa-flag">Mai: ${x.esc(se.next.emoji)} ${x.esc(se.next.name)}</span>`:''}</div>`:'';
  const strip=out.length?`<ol class="fa-outlook" aria-label="Dự báo ba ngày tới">${out.map((o,i)=>`<li class="${o.id}"><small>${i===0?'Mai':i===1?'Ngày kia':'Ngày '+o.day}</small><span aria-hidden="true">${x.esc(o.emoji)}</span><b>${x.esc(o.name)}</b><small class="fa-night">${o.night>0?'đêm ẩm +'+o.night:'đêm khô '+o.night}%</small>${o.season?`<em>${x.esc(o.season_emoji)} ${x.esc(o.season)}</em>`:''}</li>`).join('')}</ol>`
    :`<div class="fa-forecast"><small>Mai</small><span aria-hidden="true">${x.esc(f.emoji||'')}</span><small>${x.esc(f.name||'')}</small></div>`;
  return `<div class="fa-weather card"><div class="fa-wrow"><span class="fa-sky" aria-hidden="true">${x.esc(w.emoji||'🌤️')}</span><div class="grow"><b>Hôm nay: ${x.esc(w.name||'')}</b><small>${x.esc(w.tip||'')}</small></div></div>
    ${strip}${d.plan?`<p class="fa-plan">🗓️ ${x.esc(d.plan)}</p>`:''}${season}${flags?`<div class="fa-flags">${flags}</div>`:''}</div>`;
}
function deskCard(x){
  const desk=data(x).desk;if(!desk)return '';
  const ev=desk.ev;
  if(ev){
    const opts=ev.options.map(o=>{
      const poor=o.cost>(Number(x.room.money)||0);
      const inner=`<span class="fa-opt-label">${x.esc(o.label)}</span>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}${o.cost?`<em class="fa-cost">−${x.fmt(o.cost)} xu${poor?' · ví chưa đủ':''}</em>`:''}`;
      return o.cost?x.confirmCmd(inner,'fa_decide',{option:o.id},`Lựa chọn này tốn ${x.fmt(o.cost)} xu. Đồng ý?`,'fa-opt',poor):x.cmd(inner,'fa_decide',{option:o.id},'fa-opt');
    }).join('');
    return `<section class="fa-event ${ev.tone==='tense'?'tense':''}" role="group" aria-labelledby="fa-ev-title"><div class="fa-ev-head"><span class="fa-ev-emoji" aria-hidden="true">${x.esc(ev.emoji)}</span><div><small>Chuyện bất ngờ ở trại · quyết xong rồi làm tiếp</small><h3 id="fa-ev-title">${x.esc(ev.title)}</h3></div></div>
      <p>${x.esc(ev.text)}</p><div class="fa-opts">${opts}</div></section>`;
  }
  const last=desk.last,key=last?`${last.script}-${last.choice}-${last.day}-${(desk.log||[]).length}`:'';
  if(last&&last.day===x.room.day&&x.ui.seen!==key){
    return `<div class="fa-last ${last.good===true?'good':last.good===false?'bad':''}" role="status"><span aria-hidden="true">${x.esc(last.emoji)}</span><p><b>${x.esc(last.title)}</b> · ${x.esc(last.outcome)}</p>${carBtn(x,'✕','seen',{key},'ghost small fa-x',' aria-label="Đã đọc"')}</div>`;
  }
  return '';
}
function orderTicket(t,x){
  const who=x.npc(t.npc);
  if(!t.known)return `<article class="card ticket"><div class="row">${x.portrait(who,56)}<div class="grow"><h3>${x.esc(who.display_name)}</h3><p>${x.esc(t.opening)}</p></div></div>${x.cmd('📞 Nhận đơn hàng','ask',{task:t.id},'primary full')}</article>`;
  const n=t.needs;
  return `<article class="card ticket"><div class="row">${x.portrait(who,48)}<div class="grow">
    <div class="row spread"><h3>${x.esc(who.display_name)}</h3><b class="price">${x.money(t.quoted_price||0)}</b></div>
    <p class="small"><b>${x.esc(t.title)}</b></p>
    <p class="fa-order-items">${Object.entries(n.items).map(([k,q])=>{const p=produce(x,k);return `<span class="fa-chip">${p.emoji} ${q} ${x.esc(p.unit)} ${x.esc(p.name.toLowerCase())}</span>`;}).join('')}</p>
    <p class="row wrap">${n.kind==='contract'?'<span class="tag blue">🍽️ Hợp đồng · loại A · thùng carton</span>':'<span class="tag amber">🧺 Khách chợ · A/B · túi giấy</span>'}${n.organic?'<span class="tag green">🌿 Bắt buộc hữu cơ + QR</span>':''}</p>
    <p class="muted small">“${x.esc(n.note)}”</p>
    <div class="patience" title="Kiên nhẫn"><div class="bar ${t.patience<50?'low':''}"><i style="width:${t.patience}%"></i></div><small>${t.patience}%</small></div></div></div></article>`;
}
function tabs(x){
  const tab=x.ui.tab||'field',d=data(x);
  const ripe=d.plots.filter(p=>p.stage==='ripe').length,pl=d.pledge;
  const b=(id,label,sub,badge='')=>carBtn(x,`<span>${label}</span><small>${sub}</small>${badge}`,'tab',{tab:id},`fa-tab ${tab===id?'primary':'ghost'}`,` role="tab" aria-selected="${tab===id}"`);
  return `<div class="fa-tabs" role="tablist" aria-label="Khu làm việc">${b('field','🌱 Vườn',ripe?`${ripe} luống chín`:'6 luống',ripe?`<b class="fa-badge">${ripe}</b>`:'')}${b('coop','🐔 Chuồng',`${d.coop?.nest||0} trứng · ${d.coop?.hens||0} mái`)}${b('cold','❄️ Kho mát',`${d.cold_units||0}/${x.cc.cold_cap}`)}${b('market','📈 Chợ',pl?`HTX ${pl.done}/${pl.qty}`:`bán sỉ`,pl&&pl.done<pl.qty?'<b class="fa-badge">!</b>':'')}</div>`;
}

/* ------------------------------------------------------------ field */
const soilLow=x=>x.cc.soil?.low??25;
function meters(p,x){
  const th=x.cc.thresholds,m=x.cc.moisture;
  const zones=`--y:${pct(th.young,th.max)};--r:${pct(th.ripe,th.max)};--o:${pct(th.over,th.max)};--x:${pct(th.rotten,th.max)}`;
  return `<span class="fa-meter growth" style="${zones}" title="Độ lớn ${p.growth}"><i style="width:${pct(p.growth,th.max)}"></i></span>
    <span class="fa-meter water ${p.moisture<m.dry?'dry':p.moisture>m.wet?'wet':''}" style="--lo:${m.low}%;--hi:${m.high}%" title="Độ ẩm ${p.moisture}%"><i style="width:${p.moisture}%"></i></span>
    <span class="fa-meter soil ${p.soil<soilLow(x)?'low':''}" style="--lo:${soilLow(x)}%" title="Đất màu ${p.soil}"><i style="width:${Math.max(0,Math.min(100,p.soil||0))}%"></i></span>`;
}
function plotCard(p,x){
  const c=p.crop?produce(x,p.crop):null,sel=x.ui.plot===p.id;
  const art=!c?'🟫':p.stage==='rotten'?'🥀':ART[p.stage]||c.emoji;
  return `<button type="button" class="fa-plot ${p.stage} ${sel?'selected':''}" data-action="car:plot" data-plot="${x.esc(p.id)}" aria-pressed="${sel}">
    <span class="fa-plot-id">${x.esc(p.id)}</span><span class="fa-plot-art">${art}</span>
    <b>${c?x.esc(c.name):'Luống trống'}</b><small>${c?x.esc(when(p)):`Nghỉ đất · màu ${p.soil}`}</small>${meters(p,x)}
    <span class="fa-icons">${c?`<em class="day">ngày ${p.day_no}</em>`:''}${'🌾'.repeat(p.weeds)}${'🐛'.repeat(p.seen||0)}${p.soil<soilLow(x)?'<em class="poor">bạc màu</em>':''}${c&&!p.organic?'<em class="chem">hóa chất</em>':''}${p.safe_in?`<em class="phi">⏳ ${p.safe_in}</em>`:''}</span></button>`;
}
function plotPanel(p,x){
  if(!p)return `<p class="muted small">Chạm vào một luống để xem chi tiết và làm việc.</p>`;
  const th=x.cc.thresholds,m=x.cc.moisture,inv=x.room.inventory||{stock:{}},st=inv.stock||{},level=x.room.level||1;
  if(!p.crop){
    const prev=p.prev?produce(x,p.prev):null,rot=p.rotation||{};
    return `<div class="card fa-panel"><h4>${x.esc(p.id)} · Luống trống</h4>
      <dl class="kv"><dt>Đất màu</dt><dd>${p.soil}/100 ${p.soil<soilLow(x)?'<b class="fa-bad">bạc màu</b>':''}<small class="muted"> · để trống qua đêm +${x.cc.soil?.rest??8}</small></dd><dt>Độ ẩm · cỏ</dt><dd>${p.moisture}% · ${p.weeds}/3</dd><dt>Vụ trước</dt><dd>${prev?`${prev.emoji} ${x.esc(prev.name)}`:'chưa rõ'}</dd></dl>
      <p class="small">Chọn giống để gieo (làm đất sẽ nhổ sạch cỏ). <b>Luân canh</b>: đổi nhóm rau lá ↔ cây trái thì đất thêm màu; trồng lại đúng cây cũ thì sâu bệnh còn trong đất.</p>
      <div class="tile-grid fa-seeds">${x.cc.crops.map(c=>{const locked=c.unlock>level,q=st[c.seed]||0,r=rot[c.id];
        const tag=r==='rotate'?'<em class="fa-rot good">luân canh +màu</em>':r==='same'?'<em class="fa-rot bad">trùng vụ trước</em>':'';
        return tile(x,'fa_plant',{plot:p.id,crop:c.id},`<span class="tile-emoji">${c.emoji}</span><b>${x.esc(c.name)}</b><small>${locked?'🔒 cấp '+c.unlock:q+' '+x.esc(supply(x,c.seed).unit)}</small>${tag}`,`${locked?'locked':''} ${!q?'empty':''}`,locked||!q);}).join('')}</div>
      <div class="fa-actions space-top">${x.cmd(p.compost?'🟫 Đã bón lót compost':`🟫 Bón lót compost (${st.compost||0}) · +${x.cc.soil?.add?.compost??20} màu`,'fa_fertilize',{plot:p.id,kind:'compost'},'small ghost',p.compost||!st.compost)}</div></div>`;
  }
  const c=produce(x,p.crop);
  const left=when(p);
  const budget=p.cap?Math.min(100,Math.round((p.grown||0)/p.cap*100)):0;
  const scouted=p.scouted_ago==null?'chưa thăm':p.scouted_ago===0?'vừa thăm':`thăm ${p.scouted_ago} nhịp trước`;
  const canHarvest=p.growth>=th.young&&p.growth<th.rotten;
  const harvestQ=p.safe_in?`⛔ Luống này còn ${p.safe_in} nhịp cách ly sau khi dùng hóa chất. Thu bây giờ thì cả lô phải hủy, không được bán. Vẫn thu?`
    :p.growth<th.ripe?'Cây còn non: thu bây giờ được ít và chỉ đạt loại B. Vẫn thu?':p.growth>=th.over?'Cây đã quá lứa: chỉ đạt loại B. Thu hoạch?':'Thu hoạch luống này vào kho mát?';
  return `<div class="card fa-panel"><div class="row spread"><h4>${x.esc(p.id)} · ${c.emoji} ${x.esc(c.name)}</h4><span class="tag ${p.organic?'green':'amber'}">${p.organic?'🌿 Hữu cơ':'🧪 Đã dùng hóa chất'}</span></div>
    <dl class="kv"><dt>Độ lớn</dt><dd>${p.growth} · ${x.esc(left)}</dd><dt>Ngày của vụ</dt><dd>ngày ${p.day_no}</dd>
      <dt>Sức lớn hôm nay</dt><dd><span class="fa-budget"><span class="fa-meter budget"><i style="width:${budget}%"></i></span><small>${p.grown||0}/${p.cap}${(p.grown||0)>=p.cap?' · đủ, chờ qua đêm':''}</small></span></dd>
      <dt>Đất màu</dt><dd>${p.soil}/100 ${p.soil<soilLow(x)?'<b class="fa-bad">bạc màu: cây lớn chậm</b>':''}<small class="muted"> · mỗi đêm cây ăn ${c.feed||0}</small></dd>
      <dt>Độ ẩm</dt><dd>${p.moisture}% <small class="muted">(lý tưởng ${m.low}–${m.high}%)</small></dd>
      <dt>Cỏ dại</dt><dd>${p.weeds}/3</dd><dt>Sâu</dt><dd>${p.scouted_ago==null?'?':p.seen+'/3'} · ${x.esc(scouted)}${p.seen>=2?' · <b class="fa-bad">đêm nay lan sang luống bên</b>':''}</dd>
      <dt>Phân đã bón</dt><dd>${[p.compost?'compost':'',p.npk?'NPK':''].filter(Boolean).join(' + ')||'chưa'}</dd><dt>Cách ly</dt><dd>${p.safe_in?`<b class="fa-bad">còn ${p.safe_in} nhịp</b>`:'an toàn'}</dd></dl>
    <div class="fa-actions">
      ${x.cmd('💧 Tưới','fa_water',{plot:p.id},'small')}
      ${x.cmd('⛏️ Khơi rãnh','fa_drain',{plot:p.id},'small ghost',p.moisture<=m.high)}
      ${x.cmd('🌾 Nhổ cỏ','fa_weed',{plot:p.id},'small ghost',!p.weeds)}
      ${x.cmd('🔍 Thăm sâu','fa_scout',{plot:p.id},'small ghost')}
    </div>
    <h4 class="section-title">Bón & phòng trừ</h4>
    <div class="fa-actions">
      ${x.cmd(`🟫 Compost (${st.compost||0})`,'fa_fertilize',{plot:p.id,kind:'compost'},'small',p.compost||!st.compost||p.growth>=th.over)}
      ${x.confirmCmd(`🧪 NPK (${st.npk||0})`,'fa_fertilize',{plot:p.id,kind:'npk'},`Bón NPK giúp cây lớn nhanh, nhưng lô này sẽ KHÔNG còn là hữu cơ và phải cách ly ${x.cc.phi.npk} nhịp trước khi thu. Nhật ký sẽ ghi lại.`,'small ghost',p.npk||!st.npk||p.growth>=th.over)}
      ${x.cmd(`🌿 Neem sinh học (${st.bio_spray||0})`,'fa_spray',{plot:p.id,kind:'bio'},'small',!st.bio_spray)}
      ${x.confirmCmd(`☠️ Thuốc hóa học (${st.chem_spray||0})`,'fa_spray',{plot:p.id,kind:'chem'},`${data(x).bees?`Ong của anh Lâm đang ở cạnh vườn: phun bây giờ ong sẽ chết và phải đền ${x.cc.bee_fine} xu. `:''}Thuốc hóa học diệt sạch sâu nhưng lô mất chuẩn hữu cơ và phải cách ly ${x.cc.phi.chem} nhịp. Đã thăm sâu chưa?`,'small danger',!st.chem_spray)}
    </div>
    <div class="row wrap space-top">${x.confirmCmd('🧺 THU HOẠCH','fa_harvest',{plot:p.id},harvestQ,`primary ${p.safe_in?'danger':''}`,!canHarvest)}
      ${x.confirmCmd('🧹 Nhổ bỏ, ủ phân','fa_clear',{plot:p.id},'Nhổ bỏ toàn bộ cây trên luống này?','ghost small')}</div></div>`;
}
function careFold(x){
  const rows=data(x).care||[];if(!rows.length)return '';
  const done=rows.filter(r=>r.ok===true).length,next=rows.find(r=>r.ok!==true),open=!!x.ui.careOpen;
  const head=`<span class="fa-care-title">📋 Việc chăm hôm nay <b>${done}/${rows.length}</b></span><small>${next?`Tiếp: ${x.esc(next.label)}`:'Xong hết, giỏi quá!'}</small>`;
  return `<section class="fa-care ${open?'open':''}">${carBtn(x,head,'care',{},'fa-care-head ghost',` aria-expanded="${open}"`)}
    ${open?reqList(rows.map(r=>({ok:r.ok,icon:r.icon,label:r.label,note:r.note||'',tone:r.tone||''})),x.esc,'Việc chăm hôm nay'):''}</section>`;
}
function fieldTab(x){
  const d=data(x),sel=d.plots.find(p=>p.id===x.ui.plot);
  const diary=(d.diary||[]).slice(-6).reverse();
  return `${careFold(x)}<div class="row spread"><h4 class="section-title">Sáu luống rau</h4>${x.cmd(d.nopump?'🚱 Van tưới mất nước':'🚿 Mở van tưới cả vườn','fa_water',{plot:'all'},'small ghost',d.nopump||!d.plots.some(p=>p.crop))}</div>
    <div class="fa-plots">${d.plots.map(p=>plotCard(p,x)).join('')}</div>
    <div class="fa-legend small muted"><span><i class="lg young"></i>non</span><span><i class="lg ripe"></i>đúng lứa</span><span><i class="lg over"></i>quá lứa</span><span><i class="lg water"></i>độ ẩm (vạch = lý tưởng)</span><span><i class="lg soil"></i>đất màu</span></div>
    ${plotPanel(sel,x)}
    <details class="fa-diary space-top"><summary>📓 Nhật ký canh tác (QR truy xuất)</summary><ul>${diary.map(r=>`<li><b>Ngày ${r.day} · ${x.esc(r.plot)}</b> ${x.esc(r.text)}</li>`).join('')||'<li class="muted">Chưa có ghi chép.</li>'}</ul></details>`;
}

/* ------------------------------------------------------------ coop */
function coopTab(x){
  const d=data(x),coop=d.coop||{},st=(x.room.inventory||{}).stock||{},mood=coop.mood??80,ok=coop.mood_ok??60;
  const face=mood>=ok?'😊 vui, đẻ đều':mood>=35?'😐 hơi mệt':'😟 ủ rũ';
  return `<div class="card fa-coop"><div class="fa-hens ${mood<35?'sad':''}">${Array.from({length:coop.hens||0},(_,i)=>`<span style="--i:${i}">🐔</span>`).join('')}</div>
    <div class="fa-nest">${Array.from({length:Math.min(24,coop.nest||0)},(_,i)=>`<span class="${i<(coop.stale||0)?'stale':''}">🥚</span>`).join('')||'<small class="muted">Ổ trống</small>'}</div>
    <div class="fa-mood"><div class="row spread"><b>Tinh thần đàn · ${x.esc(face)}</b><small>${mood}/100</small></div><span class="fa-meter mood ${mood<ok?'low':''}" style="--lo:${ok}%"><i style="width:${mood}%"></i></span>
      <small class="muted">Mai đẻ khoảng ${coop.lay_pct??100}% đàn${d.fed_today?'':' (chưa ăn: chỉ nửa đàn)'}. Ăn no +, chuồng sạch +, đói hoặc chuồng bẩn hai ngày −, nắng gắt mà không dọn chuồng −.</small></div>
    <dl class="kv"><dt>Đàn gà</dt><dd>${coop.hens||0} mái</dd><dt>Trứng trong ổ</dt><dd>${coop.nest||0}${coop.stale?` · ${coop.stale} quả từ hôm qua`:''}</dd><dt>Hôm nay</dt><dd>${d.fed_today?'✓ đã cho ăn':'<b class="fa-bad">chưa cho ăn</b>'} · ${coop.cleaned_today?'✓ chuồng sạch':'<b class="fa-bad">chưa dọn chuồng</b>'}</dd><dt>Cám trong kho</dt><dd>${st.feed||0} bao</dd></dl>
    <p class="muted small">Trứng để qua đêm trong ổ chỉ còn loại B. Trứng lau khô, không rửa nước.</p>
    <div class="row wrap">${x.cmd('🌾 Cho gà ăn & thay nước','fa_feed',{},'primary',d.fed_today||!st.feed)}${x.cmd('🧹 Dọn chuồng','fa_clean',{},'',!!coop.cleaned_today)}${x.cmd('🧺 Nhặt trứng','fa_collect',{},'',!coop.nest)}
      ${(coop.hens||0)<(x.cc.hens||10)?x.confirmCmd(`🐔 Mua gà mái đẻ · ${x.cc.hen_cost} xu`,'fa_hen',{},`Mua một gà mái đẻ giá ${x.cc.hen_cost} xu?`,'ghost small',(Number(x.room.money)||0)<x.cc.hen_cost):''}</div></div>`;
}

/* ------------------------------------------------------------ cold room + crate */
function coldTab(t,x){
  const d=data(x),order=t&&t.known?t.needs:null;
  const lots=[...(d.cold||[])].sort((a,b)=>a.crop.localeCompare(b.crop)||a.expires-b.expires);
  return `<div class="row spread wrap"><p class="muted small grow">Kho mát ${d.cold_units||0}/${x.cc.cold_cap} đơn vị. Lô hết hạn tươi bị bỏ khi khép ca. Xếp lô cũ đi trước; hàng dư đem bán sỉ ở tab 📈 Chợ.</p>${x.button('📦 Kho vật tư','inventory',{},'ghost small')}</div>
    <div class="fa-lots">${lots.map(l=>{
      const p=produce(x,l.crop),inOrder=order&&l.crop in order.items;
      const need=inOrder?Math.max(0,order.items[l.crop]-packed(t,l.crop)):0,n=Math.min(need,l.qty);
      const canPack=inOrder&&l.left>=0;
      const pk=(label,qty,cls)=>l.unsafe?x.confirmCmd(label,'fa_pack',{task:t.id,lot:l.id,qty},`Lô ${l.id} chưa hết thời gian cách ly thuốc. Vẫn xếp vào thùng giao khách?`,cls+' danger'):x.cmd(label,'fa_pack',{task:t.id,lot:l.id,qty},cls);
      return `<div class="fa-lot ${l.unsafe?'unsafe':''} ${l.left<=0?'expiring':''}"><span class="fa-lot-art">${p.emoji}</span><div class="grow">
        <b>${x.esc(p.name)} · ${l.qty} ${x.esc(p.unit)}</b>
        <small>Lô ${x.esc(l.id)} · ${x.esc(l.plot)} · thu ngày ${l.day} · ${l.left<=0?'hết hạn hôm nay':'còn '+l.left+' ngày'}</small>
        <span class="row wrap"><span class="tag ${l.grade==='A'?'green':'amber'}">Loại ${x.esc(l.grade)}</span>${l.organic?'<span class="tag green">🌿 hữu cơ</span>':''}${l.unsafe?'<span class="tag danger">⛔ chưa hết cách ly</span>':''}</span></div>
        <div class="fa-lot-btns">${canPack?pk('+1',1,'small'):''}${canPack&&n>1?pk(`+${n}`,n,'small primary'):''}
          ${x.confirmCmd('🗑️','fa_discard',{lot:l.id},`Hủy lô ${l.id} và ghi hao hụt?`,'small ghost')}</div></div>`;
    }).join('')||'<p class="muted">Kho mát trống. Thu hoạch luống chín hoặc nhặt trứng.</p>'}</div>`;
}
function marketTab(x){
  const d=data(x),mk=d.market;if(!mk)return '';
  const slip=mk.slip||4,rowOf=c=>mk.rows.find(r=>r.crop===c);
  const board=mk.rows.map(r=>{const p=produce(x,r.crop),room=r.depth-r.sold;
    const tr=r.index>=125?['up','📈 được giá']:r.index<=80?['down','📉 rớt giá']:['','– ổn định'];
    const fit=r.fit>0?'<small class="fa-fit in">vào mùa</small>':r.fit<0?'<small class="fa-fit off">trái vụ</small>':'';
    return `<li class="${room<=0?'full':''}"><span class="fa-b-name">${p.emoji} ${x.esc(p.name)}${fit}</span><span class="fa-b-price"><b>${xu(r.next_a)}</b><small>B ${xu(Math.max(1,Math.floor(r.b*Math.max(50,100-10*Math.floor(r.sold/slip))/100)))}</small></span><span class="fa-trend ${tr[0]}">${tr[1]}</span><span class="fa-b-depth" role="img" aria-label="Chợ đã nhận ${r.sold}/${r.depth}"><i style="width:${Math.min(100,r.sold/r.depth*100)}%"></i></span></li>`;}).join('');
  const ru=mk.rumour,rp=ru?produce(x,ru.crop):null;
  const pl=d.pledge;let pledge='';
  if(pl){
    const p=produce(x,pl.crop),left=pl.qty-pl.done;
    const lots=(d.cold||[]).filter(l=>l.crop===pl.crop&&l.grade==='A'&&!l.unsafe&&l.left>=0);
    pledge=`<section class="fa-pledge card"><div class="row spread"><h4>🤝 Phần góp HTX</h4><b>${pl.done}/${pl.qty} ${x.esc(p.unit)}</b></div><div class="bar"><i style="width:${pl.done/pl.qty*100}%"></i></div>
      <p class="small">${p.emoji} ${x.esc(p.name)} loại A · giá chốt <b>${pl.price} xu/${x.esc(p.unit)}</b>. ${left?`Còn thiếu ${left}: khép ca mà chưa đủ thì HTX phạt ${x.cc.pledge_fine} xu mỗi ${x.esc(p.unit)}.`:'Đã góp đủ, cảm ơn nông trại!'}</p>
      ${left?(lots.length?`<div class="row wrap">${lots.map(l=>{const n=Math.min(left,l.qty);return x.cmd(`Góp ${n} từ lô ${x.esc(l.id)} · +${n*pl.price} xu`,'fa_pledge',{lot:l.id,qty:n},'small primary');}).join('')}</div>`:`<p class="notice amber small">Kho mát chưa có ${x.esc(p.name.toLowerCase())} loại A. Thu hoạch luống đúng lứa rồi quay lại góp.</p>`):''}</section>`;
  }
  const lots=[...(d.cold||[])].filter(l=>!l.unsafe&&l.left>=0).sort((a,b)=>a.left-b.left||a.crop.localeCompare(b.crop));
  // Produce an accepted order or the HTX still needs: warn before it goes to the wholesale market.
  const wanted={};for(const t of (x.room.tasks||[]).filter(t=>t.career===ID&&t.known&&!['completed','cancelled','referred'].includes(t.status)))for(const k of Object.keys(t.needs.items||{}))wanted[k]=x.npc(t.npc).display_name;
  if(pl&&pl.done<pl.qty)wanted[pl.crop]=wanted[pl.crop]||'HTX';
  const sell=lots.map(l=>{const p=produce(x,l.crop),r=rowOf(l.crop);if(!r)return '';const room=r.depth-r.sold,n=Math.min(room,l.qty),few=Math.min(5,n),need=wanted[l.crop];
    const btn=(q,cls)=>{const est=estimate(r,l.grade,q,slip);return x.confirmCmd(`Bán ${q} · ~${est} xu`,'fa_sell',{lot:l.id,qty:q},`${need?`${need} đang cần ${p.name.toLowerCase()} cho đơn đã nhận. `:''}Bán sỉ ${q} ${p.unit} ${p.name.toLowerCase()} loại ${l.grade} cho chợ đầu mối, được khoảng ${est} xu?`,cls);};
    return `<div class="fa-lot ${l.left<=0?'expiring':''}"><span class="fa-lot-art" aria-hidden="true">${p.emoji}</span><div class="grow"><b>${x.esc(p.name)} · ${l.qty} ${x.esc(p.unit)} · loại ${x.esc(l.grade)}</b><small>Lô ${x.esc(l.id)} · ${l.left<=0?'hết hạn hôm nay':'còn '+l.left+' ngày'}</small>${need?`<span class="tag amber">📦 ${x.esc(need)} đang cần</span>`:''}</div>
      <div class="fa-lot-btns">${n?(few<n?btn(few,'small ghost'):'')+btn(n,need?'small ghost':'small primary'):'<small class="muted">chợ đủ hàng</small>'}</div></div>`;}).join('');
  return `${pledge}<section class="fa-market card"><div class="row spread"><h4>📈 Chợ đầu mối hôm nay</h4>${mk.income?`<span class="tag green">+${x.fmt(mk.income)} xu</span>`:''}</div>
    <p class="muted small">Giá sỉ cho mỗi đơn vị loại A (xu), khoảng ${mk.wholesale}% giá bán lẻ. Mỗi ${slip} đơn vị bán thêm, giá hạ 10%; chợ chỉ nhận có hạn mỗi mặt hàng.</p>
    <ul class="fa-board">${board}</ul>
    ${rp?`<p class="fa-rumour">🗣️ Anh Tuấn rỉ tai: “Mai ${x.esc(rp.name.toLowerCase())} ${ru.up?'lên giá':'rớt giá'} đó.” <small>Tin đồn, không chắc đúng.</small></p>`:''}</section>
    <section class="fa-sell"><h4 class="section-title">Bán sỉ từ kho mát</h4>${sell||'<p class="muted small">Kho mát chưa có lô nào bán được. Thu hoạch luống chín hoặc nhặt trứng.</p>'}</section>`;
}
function crateSide(t,x){
  if(!t.known)return `<div class="card"><p class="small">Nhận đơn để mở bàn đóng thùng. Trong lúc chờ, cứ chăm vườn và gà.</p></div>`;
  const n=t.needs,st=(x.room.inventory||{}).stock||{};
  const crate=t.crate||[];
  const eggs=packed(t,'egg'),veg=crate.some(e=>e.crop!=='egg');
  const pack={};if(n.kind==='contract')pack.carton=1;else if(veg)pack.bag=1;if(eggs)pack.egg_tray=Math.ceil(eggs/10);
  const rows=Object.entries(n.items).map(([k,q])=>{
    const a=sum(crate.filter(e=>e.crop===k&&e.grade==='A').map(e=>e.qty)),b=sum(crate.filter(e=>e.crop===k&&e.grade==='B').map(e=>e.qty)),p=produce(x,k);
    return [a+b?a+b>=q&&!(n.kind==='contract'&&b):null,`${q} ${p.unit} ${p.name.toLowerCase()}${n.kind==='contract'?' loại A':''}`,a+b?`A ${a} · B ${b} / ${q}`:''];
  });
  const notOrganic=crate.filter(e=>!e.organic);
  if(t.label==='organic')rows.push([!notOrganic.length,'Nhãn hữu cơ khớp nhật ký',notOrganic.length?`lô ${notOrganic.map(e=>e.lot).join(', ')} không hữu cơ`:'']);
  if(n.organic)rows.push([t.label?t.label==='organic':null,'Hợp đồng yêu cầu nhãn hữu cơ + QR','']);
  rows.push([t.label?true:null,'Đã dán nhãn','']);
  for(const [k,q] of Object.entries(pack))rows.push([(st[k]||0)>=q,`${supply(x,k).name} ×${q}`,`kho còn ${st[k]||0}`]);
  const label=(id,e,title,sub)=>tile(x,'fa_label',{task:t.id,label:id},`<span class="tile-emoji">${e}</span><b>${title}</b><small>${sub}</small>`,t.label===id?'selected':'');
  return `<div class="fa-crate card"><h4>${n.kind==='contract'?'📦 Thùng carton':'🛍️ Túi giấy'} cho ${x.esc(x.npc(t.npc).display_name)}</h4>
    <div class="fa-crate-box">${crate.map(e=>{const p=produce(x,e.crop);return `<div class="fa-crate-line"><span>${p.emoji} ${e.qty} ${x.esc(p.unit)} · ${x.esc(e.grade)}${e.organic?' 🌿':''}</span><small>lô ${x.esc(e.lot)}</small><button type="button" class="icon-btn" aria-label="Trả lô ${x.esc(e.lot)} về kho" data-command="fa_unpack" data-payload="${x.esc(JSON.stringify({task:t.id,lot:e.lot}))}">↩︎</button></div>`;}).join('')||'<small class="muted">Thùng trống — xếp hàng từ Kho mát.</small>'}</div>
    <h4 class="section-title">Nhãn</h4><div class="tile-grid fa-labels">${label('plain','🏷️','Nhãn thường','tên trại · ngày thu')}${label('organic','🌿','Nhãn hữu cơ','QR nhật ký canh tác')}</div>
    ${checklist(x,rows)}
    ${x.confirmCmd('🚚 GIAO HÀNG','fa_deliver',{task:t.id},'Giao thùng hàng này? Khách sẽ kiểm số lượng, loại hàng và quét QR trên nhãn.','primary big full',!crate.length||!t.label)}</div>`;
}

export default {
  id:ID,
  css:true,
  next(t){
    if(!t.known)return 'Nghe khách đặt hàng';
    const missing=Object.entries(t.needs.items).filter(([k,q])=>packed(t,k)<q);
    if(missing.length)return 'Thu hoạch, rồi xếp hàng vào thùng';
    if(!t.label)return 'Dán nhãn trung thực';
    return 'Giao hàng cho khách';
  },
  job(t,x){
    if(data(x).desk?.ev)return `<div class="career-job fa">${weatherBar(x)}${deskCard(x)}<p class="small muted" role="note">Vườn, chuồng và đơn hàng chờ một chút: quyết xong chuyện này rồi làm tiếp nhé.</p></div>`;
    const tab=x.ui.tab||'field';
    const main=tab==='coop'?coopTab(x):tab==='cold'?coldTab(t,x):tab==='market'?marketTab(x):fieldTab(x);
    return `<div class="career-job fa">${weatherBar(x)}${deskCard(x)}${orderTicket(t,x)}${tabs(x)}
      <div class="workbench"><section class="wb-main">${main}</section><aside class="wb-side">${crateSide(t,x)}</aside></div></div>`;
  },
  idle(x){
    if(data(x).desk?.ev)return `<div class="career-job fa">${weatherBar(x)}${deskCard(x)}</div>`;
    const tab=x.ui.tab||'field';
    const main=tab==='coop'?coopTab(x):tab==='cold'?coldTab(null,x):tab==='market'?marketTab(x):fieldTab(x);
    return `<div class="career-job fa">${weatherBar(x)}${deskCard(x)}<p class="notice small">Chưa có đơn hàng đang chờ: chăm vườn, cho gà ăn, bán sỉ hàng dư — hoặc đón thêm khách.</p>${tabs(x)}
      <div class="workbench single"><section class="wb-main">${main}</section></div></div>`;
  },
  actions:{
    async tab(data,el,x){x.ui.tab=['field','coop','cold','market'].includes(data.tab)?data.tab:'field';x.render();},
    async plot(data,el,x){x.ui.plot=x.ui.plot===data.plot?null:data.plot;x.render();},
    async seen(data,el,x){x.ui.seen=data.key;x.render();},
    async care(data,el,x){x.ui.careOpen=!x.ui.careOpen;x.render();},
  },
  dock:[['inventory','box','Kho vật tư','Hạt giống, phân, bao bì']],
};
