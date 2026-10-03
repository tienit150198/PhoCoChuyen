/** Nông Trại Đồi Gió — six plots, a hen house, the cold room and the packing
 *  table. Field state is persistent and turn-based; everything is recomputed
 *  on the server, the client only shows it. */
import {reqList} from '../ui-kit.js';
import {stepRows,nextHint,stepCta,finalGo,pending,firstTime,stepLine,goAttrs,bareLabel} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {planBox,stockLines,figures} from './plan_kit.js';
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
const data=x=>x.room.data||{plots:[],cold:[],coop:{},diary:[]};
const packed=(t,crop)=>sum((t.crate||[]).filter(e=>e.crop===crop).map(e=>e.qty));
/* Wholesale prices come in tenths of a xu. */
const xu=v=>(Number(v||0)/10).toLocaleString('vi-VN',{maximumFractionDigits:1});
const estimate=(row,grade,qty,slip)=>{let t=0;const base=grade==='A'?row.a:row.b;for(let i=0;i<qty;i++)t+=Math.max(1,Math.floor(base*Math.max(50,100-10*Math.floor((row.sold+i)/slip))/100));return Math.max(1,Math.floor((t+5)/10));};

/* ------------------------------------------------------------ weather + order */
/* The weather as one tappable line (today · tomorrow · season); the tip, the 3-day outlook, the plan
 * and the season detail unfold under it. Warnings (no water, bees) always stay in view. */
function weatherBar(x){
  const d=data(x),w=d.weather||{},f=d.forecast||{},se=d.season,out=d.outlook||[],open=!!x.ui.wxOpen;
  const flags=[d.nopump?'<span class="fa-flag bad">🚱 Trạm bơm cúp nước: chỉ tưới từng luống</span>':'',d.bees?'<span class="fa-flag">🐝 Ong đang ở cạnh vườn: đừng phun thuốc hóa học</span>':''].join('');
  const season=se?`<div class="fa-season"><span class="fa-sky" aria-hidden="true">${x.esc(se.emoji)}</span><div class="grow"><b>${x.esc(se.name)} · ngày ${se.day}/${se.days}</b>${se.good?.length?`<small>được mùa: ${x.esc(se.good.join(', '))}</small>`:''}</div>${se.day===se.days?`<span class="fa-flag">Mai: ${x.esc(se.next.emoji)} ${x.esc(se.next.name)}</span>`:''}</div>`:'';
  const strip=out.length?`<ol class="fa-outlook" aria-label="Dự báo ba ngày tới">${out.map((o,i)=>`<li class="${o.id}"><small>${i===0?'Mai':i===1?'Ngày kia':'Ngày '+o.day}</small><span aria-hidden="true">${x.esc(o.emoji)}</span><b>${x.esc(o.name)}</b><small class="fa-night">${o.night>0?'đêm ẩm +'+o.night:'đêm khô '+o.night}%</small>${o.season?`<em>${x.esc(o.season_emoji)} ${x.esc(o.season)}</em>`:''}</li>`).join('')}</ol>`
    :`<div class="fa-forecast"><small>Mai</small><span aria-hidden="true">${x.esc(f.emoji||'')}</span><small>${x.esc(f.name||'')}</small></div>`;
  const tmr=out[0]||f;
  const head=`<span class="fa-wchip"><span aria-hidden="true">${x.esc(w.emoji||'🌤️')}</span> <b>${x.esc(w.name||'')}</b></span>${tmr&&tmr.name?`<span class="fa-wchip" title="${x.esc(tmr.name)}">Mai ${x.esc(tmr.emoji||'')}</span>`:''}${se?`<span class="fa-wchip" title="${x.esc(se.name)}">${x.esc(se.emoji)} ${se.day}/${se.days}</span>`:''}${d.plan?'<span class="fa-wchip fa-wplan" aria-hidden="true">🗓️</span>':''}`;
  return `<div class="fa-weather ${open?'open':''}">${carBtn(x,head,'wx',{},'fa-whead ghost',` aria-expanded="${open}" aria-label="Thời tiết hôm nay: ${x.esc(w.name||'')}"`)}
    ${open?`<div class="fa-wbody card"><p class="fa-wtip"><b>Hôm nay: ${x.esc(w.name||'')}</b> · ${x.esc(w.tip||'')}</p>${strip}${d.plan?`<p class="fa-plan">🗓️ ${x.esc(d.plan)}</p>`:''}${season}</div>`:''}${flags?`<div class="fa-flags">${flags}</div>`:''}</div>`;
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
    return `<section class="fa-event ${ev.tone==='tense'?'tense':''}" role="group" aria-labelledby="fa-ev-title"><div class="fa-ev-head"><span class="fa-ev-emoji" aria-hidden="true">${x.esc(ev.emoji)}</span><div><small>Chuyện bất ngờ ở trại</small><h3 id="fa-ev-title">${x.esc(ev.title)}</h3></div></div>
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
  if(!t.known)return `<article class="card ticket"><div class="row">${x.portrait(who,56)}<div class="grow"><h3>${x.esc(who.display_name)}</h3><p>${x.esc(t.opening)}</p></div></div>${x.cmd('📞 Nhận đơn hàng','ask',{task:t.id},'primary full gd-cta fa-ask')}</article>`;
  // Compact once the order is known: who · patience · price, what, the order type in short; the full
  // type, the price rules and the customer's words unfold from it (the sheet header carries the title).
  const n=t.needs,open=!!x.ui.orderOpen;
  const kind=n.kind==='contract'?'<span class="tag blue">🍽️ Hợp đồng · loại A · thùng carton</span>':'<span class="tag amber">🧺 Khách chợ · A/B · túi giấy</span>';
  const short=`${n.kind==='contract'?'<span class="tag blue">🍽️ Hợp đồng · A · carton</span>':'<span class="tag amber">🧺 Chợ · A/B · túi giấy</span>'}${n.organic?'<span class="tag green">🌿 Hữu cơ + QR</span>':''}`;
  return `<article class="card ticket fa-ticket"><div class="fa-t-row">${x.portrait(who,40)}<div class="grow">
    <div class="fa-t-head"><b>${x.esc(who.display_name)}</b><span class="patience" title="Kiên nhẫn"><span class="bar ${t.patience<50?'low':''}"><i style="width:${t.patience}%"></i></span><small>${t.patience}%</small></span><b class="price">${x.money(t.quoted_price||0)}</b></div>
    <p class="fa-order-items">${Object.entries(n.items).map(([k,q])=>{const p=produce(x,k),pr=data(x).prices?.[k];return `<span class="fa-chip">${p.emoji} ${q} ${x.esc(p.unit)} ${x.esc(p.name.toLowerCase())}${pr!=null?` × ${pr} xu`:''}</span>`;}).join('')}</p></div></div>
    ${carBtn(x,`<span class="fa-t-kind">${short}</span>`,'order',{},'fa-t-more ghost',` aria-expanded="${open}" aria-label="Điều kiện đơn hàng"`)}
    ${open?`<div class="fa-t-body"><p class="row wrap">${kind}${n.organic?'<span class="tag green">🌿 Bắt buộc hữu cơ + QR</span>':''}</p><p class="small muted">Loại B tính ${x.cc.b_percent||70}% giá${n.kind==='market'||n.organic?` · nhãn hữu cơ thật: ×${x.cc.organic_percent||130}%`:''} · hàng giao dư không tính tiền.</p>
    <p class="muted small">“${x.esc(n.note)}”</p></div>`:''}</article>`;
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
/* Phân bón lá thúc: bought from the HTX right at the bed, sprayed in 10% doses. The server sends up to three
 * amounts with their price and the harvest day they would give, or why the bed cannot take one now. */
function thucBlock(p,x){
  const t=p.thuc;if(!t||!Array.isArray(t.options))return '';
  const btn=o=>x.confirmCmd(`<b>−${o.pct}%</b> <small>${o.cost} xu</small>${o.eta!=null?` <small>chín ${DAYS(o.eta)}</small>`:''}`,'fa_boost',{plot:p.id,pct:o.pct},
    `Mua ${o.pct/t.step} liều phân bón lá thúc (${o.cost} xu) phun luống ${p.id}? Thời gian lớn rút thêm ${o.pct}%, đất màu −${o.pct/t.step*t.soil}.`,'small ghost fa-thuc-dose',!o.ok);
  const why=t.why||t.options.find(o=>!o.ok)?.why;
  return `<div class="fa-thuc"><p class="small"><b>🧴 Phân bón lá thúc</b> <small class="muted">đạm cá, hữu cơ · đã thúc ${t.pct}/${t.max}%</small></p>
    <p class="small muted">Mỗi liều rút ${t.step}% thời gian lớn, tốn ${t.soil} đất màu. Tối đa ${t.max}% mỗi vụ.</p>
    ${t.options.length?`<div class="fa-actions">${t.options.map(btn).join('')}</div>`:''}${why?`<p class="small fa-why">${x.esc(why)}</p>`:''}</div>`;
}
/* The seed choice of an empty bed (the workbench's open bed, and the bed you stand at in 🚶 Tự đi). */
function seedTiles(p,x,cls=''){
  const st=(x.room.inventory||{}).stock||{},level=x.room.level||1,rot=p.rotation||{};
  return `<div class="tile-grid fa-seeds${cls?' '+cls:''}">${x.cc.crops.map(c=>{const locked=c.unlock>level,q=st[c.seed]||0,r=rot[c.id];
        const tag=r==='rotate'?'<em class="fa-rot good">luân canh +màu</em>':r==='same'?'<em class="fa-rot bad">trùng vụ trước</em>':'';
        return tile(x,'fa_plant',{plot:p.id,crop:c.id},`<span class="tile-emoji">${c.emoji}</span><b>${x.esc(c.name)}</b><small>${locked?'🔒 cấp '+c.unlock:q+' '+x.esc(supply(x,c.seed).unit)}</small>${tag}`,`${locked?'locked':''} ${!q?'empty':''}`,locked||!q);}).join('')}</div>`;
}
/* What the harvest button asks first. */
function harvestAsk(p,x){
  const th=x.cc.thresholds;
  return p.safe_in?`⛔ Luống này còn ${p.safe_in} nhịp cách ly sau khi dùng hóa chất. Thu bây giờ thì cả lô phải hủy, không được bán. Vẫn thu?`
    :p.growth<th.ripe?'Cây còn non: thu bây giờ được ít và chỉ đạt loại B. Vẫn thu?':p.growth>=th.over?'Cây đã quá lứa: chỉ đạt loại B. Thu hoạch?':'Thu hoạch luống này vào kho mát?';
}
function plotPanel(p,x){
  if(!p)return '';
  const th=x.cc.thresholds,m=x.cc.moisture,inv=x.room.inventory||{stock:{}},st=inv.stock||{};
  if(!p.crop){
    const prev=p.prev?produce(x,p.prev):null;
    return `<div class="card fa-panel"><h4>${x.esc(p.id)} · Luống trống</h4>
      <dl class="kv"><dt>Đất màu</dt><dd>${p.soil}/100 ${p.soil<soilLow(x)?'<b class="fa-bad">bạc màu</b>':''}<small class="muted"> · để trống qua đêm +${x.cc.soil?.rest??8}</small></dd><dt>Độ ẩm · cỏ</dt><dd>${p.moisture}% · ${p.weeds}/3</dd><dt>Vụ trước</dt><dd>${prev?`${prev.emoji} ${x.esc(prev.name)}`:'chưa rõ'}</dd></dl>      ${seedTiles(p,x)}
      <div class="fa-actions space-top">${x.cmd(p.compost?'🟫 Đã bón lót compost':`🟫 Bón lót compost (${st.compost||0}) · +${x.cc.soil?.add?.compost??20} màu`,'fa_fertilize',{plot:p.id,kind:'compost'},'small ghost',p.compost||!st.compost)}</div></div>`;
  }
  const c=produce(x,p.crop);
  const left=when(p);
  const budget=p.cap?Math.min(100,Math.round((p.grown||0)/p.cap*100)):0;
  const scouted=p.scouted_ago==null?'chưa thăm':p.scouted_ago===0?'vừa thăm':`thăm ${p.scouted_ago} nhịp trước`;
  const canHarvest=p.growth>=th.young&&p.growth<th.rotten;
  const harvestQ=harvestAsk(p,x);
  return `<div class="card fa-panel"><div class="row spread"><h4>${x.esc(p.id)} · ${c.emoji} ${x.esc(c.name)}</h4><span class="tag ${p.organic?'green':'amber'}">${p.organic?'🌿 Hữu cơ':'🧪 Đã dùng hóa chất'}</span></div>
    <dl class="kv"><dt>Độ lớn</dt><dd>${p.growth} · ${x.esc(left)}</dd><dt>Ngày của vụ</dt><dd>ngày ${p.day_no}</dd>
      <dt>Sức lớn hôm nay</dt><dd><span class="fa-budget"><span class="fa-meter budget"><i style="width:${budget}%"></i></span><small>${p.grown||0}/${p.cap}${(p.grown||0)>=p.cap?' · đủ, chờ qua đêm':''}</small></span></dd>
      <dt>Đất màu</dt><dd>${p.soil}/100 ${p.soil<soilLow(x)?'<b class="fa-bad">bạc màu: cây lớn chậm</b>':''}<small class="muted"> · mỗi đêm cây ăn ${c.feed||0}</small></dd>
      <dt>Độ ẩm</dt><dd>${p.moisture}% <small class="muted">(lý tưởng ${m.low}–${m.high}%)</small></dd>
      <dt>Cỏ dại</dt><dd>${p.weeds}/3</dd><dt>Sâu</dt><dd>${p.scouted_ago==null?'?':p.seen+'/3'} · ${x.esc(scouted)}${p.seen>=2?' · <b class="fa-bad">đêm nay lan sang luống bên</b>':''}</dd>
      <dt>Phân đã bón</dt><dd>${[p.compost?'compost':'',p.npk?'NPK':'',p.thuc?.pct?`thúc −${p.thuc.pct}%`:''].filter(Boolean).join(' + ')||'chưa'}</dd><dt>Cách ly</dt><dd>${p.safe_in?`<b class="fa-bad">còn ${p.safe_in} nhịp</b>`:'an toàn'}</dd></dl>
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
    </div>${thucBlock(p,x)}
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
  // The plots come first; the care list and the valve share one line under them, then the open bed,
  // the diary and the meter legend.
  return `<div class="fa-plots" role="group" aria-label="Sáu luống rau">${d.plots.map(p=>plotCard(p,x)).join('')}</div>
    <div class="fa-fieldtop">${careFold(x)}${x.cmd(d.nopump?'🚱 Van tưới mất nước':'🚿 Mở van tưới cả vườn','fa_water',{plot:'all'},'small ghost fa-valve',d.nopump||!d.plots.some(p=>p.crop))}</div>
    ${plotPanel(sel,x)}
    <details class="fa-diary space-top"><summary>📓 Nhật ký canh tác (QR truy xuất)</summary><ul>${diary.map(r=>`<li><b>Ngày ${r.day} · ${x.esc(r.plot)}</b> ${x.esc(r.text)}</li>`).join('')||'<li class="muted">Chưa có ghi chép.</li>'}</ul></details>
    <div class="fa-legend small muted"><span><i class="lg young"></i>non</span><span><i class="lg ripe"></i>đúng lứa</span><span><i class="lg over"></i>quá lứa</span><span><i class="lg water"></i>độ ẩm (vạch = lý tưởng)</span><span><i class="lg soil"></i>đất màu</span></div>`;
}

/* ------------------------------------------------------------ coop */
function coopTab(x){
  const d=data(x),coop=d.coop||{},st=(x.room.inventory||{}).stock||{},mood=coop.mood??80,ok=coop.mood_ok??60;
  const face=mood>=ok?'😊 vui, đẻ đều':mood>=35?'😐 hơi mệt':'😟 ủ rũ';
  return `<div class="card fa-coop"><div class="fa-hens ${mood<35?'sad':''}">${Array.from({length:coop.hens||0},(_,i)=>`<span style="--i:${i}">🐔</span>`).join('')}</div>
    <div class="fa-nest">${Array.from({length:Math.min(24,coop.nest||0)},(_,i)=>`<span class="${i<(coop.stale||0)?'stale':''}">🥚</span>`).join('')||'<small class="muted">Ổ trống</small>'}</div>
    <div class="fa-mood"><div class="row spread"><b>Tinh thần đàn · ${x.esc(face)}</b><small>${mood}/100</small></div><span class="fa-meter mood ${mood<ok?'low':''}" style="--lo:${ok}%"><i style="width:${mood}%"></i></span>
      <small class="muted">Mai đẻ khoảng ${coop.lay_pct??100}% đàn${d.fed_today?'':' (chưa ăn: chỉ nửa đàn)'}.</small></div>
    <dl class="kv"><dt>Đàn gà</dt><dd>${coop.hens||0} mái</dd><dt>Trứng trong ổ</dt><dd>${coop.nest||0}${coop.stale?` · ${coop.stale} quả từ hôm qua`:''}</dd><dt>Hôm nay</dt><dd>${d.fed_today?'✓ đã cho ăn':'<b class="fa-bad">chưa cho ăn</b>'} · ${coop.cleaned_today?'✓ chuồng sạch':'<b class="fa-bad">chưa dọn chuồng</b>'}</dd><dt>Cám trong kho</dt><dd>${st.feed||0} bao</dd></dl>
    <p class="muted small">🥚 qua đêm → loại B</p>
    <div class="row wrap">${x.cmd('🌾 Cho gà ăn & thay nước','fa_feed',{},'primary',d.fed_today||!st.feed)}${x.cmd('🧹 Dọn chuồng','fa_clean',{},'',!!coop.cleaned_today)}${x.cmd('🧺 Nhặt trứng','fa_collect',{},'',!coop.nest)}
      ${(coop.hens||0)<(x.cc.hens||10)?x.confirmCmd(`🐔 Mua gà mái đẻ · ${x.cc.hen_cost} xu`,'fa_hen',{},`Mua một gà mái đẻ giá ${x.cc.hen_cost} xu?`,'ghost small',(Number(x.room.money)||0)<x.cc.hen_cost):''}</div></div>`;
}

/* ------------------------------------------------------------ cold room + crate */
function coldTab(t,x){
  const d=data(x),order=t&&t.known?t.needs:null;
  const lots=[...(d.cold||[])].sort((a,b)=>a.crop.localeCompare(b.crop)||a.expires-b.expires);
  return `<div class="row spread wrap"><p class="muted small grow">❄️ ${d.cold_units||0}/${x.cc.cold_cap}</p>${x.button('📦 Kho vật tư','inventory',{},'ghost small')}</div>
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
    }).join('')||'<p class="muted">Kho mát trống.</p>'}</div>`;
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
      ${left?(lots.length?`<div class="row wrap">${lots.map(l=>{const n=Math.min(left,l.qty);return x.cmd(`Góp ${n} từ lô ${x.esc(l.id)} · +${n*pl.price} xu`,'fa_pledge',{lot:l.id,qty:n},'small primary');}).join('')}</div>`:`<p class="notice amber small">Kho mát chưa có ${x.esc(p.name.toLowerCase())} loại A.</p>`):''}</section>`;
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
    <p class="muted small">Giá sỉ loại A (xu) · bán thêm ${slip} → −10%</p>
    <ul class="fa-board">${board}</ul>
    ${rp?`<p class="fa-rumour">🗣️ Anh Tuấn rỉ tai: “Mai ${x.esc(rp.name.toLowerCase())} ${ru.up?'lên giá':'rớt giá'} đó.”</p>`:''}</section>
    <section class="fa-sell"><h4 class="section-title">Bán sỉ từ kho mát</h4>${sell||'<p class="muted small">Kho mát chưa có lô nào bán được.</p>'}</section>`;
}
const labelTiles=(t,x,cls='')=>{
  const label=(id,e,title,sub)=>tile(x,'fa_label',{task:t.id,label:id},`<span class="tile-emoji">${e}</span><b>${title}</b><small>${sub}</small>`,t.label===id?'selected':'');
  return `<div class="tile-grid fa-labels ${cls}" role="group" aria-label="Nhãn">${label('plain','🏷️','Nhãn thường','tên trại · ngày thu')}${label('organic','🌿','Nhãn hữu cơ','QR nhật ký canh tác')}</div>`;
};
/* The label is the step: its two choices ride in the bottom bar, right over the button. */
const labelStep=(t,x,g)=>t.known&&pending(g.steps)?.key==='label';
function crateSide(t,x,g){
  if(!t.known)return `<div class="card"><p class="small">Nhận đơn để mở bàn đóng thùng.</p></div>`;
  const n=t.needs,crate=t.crate||[],steps=g.steps||[],open=!!x.ui.stepsOpen,done=steps.filter(s=>s.ok===true).length;
  return `<div class="fa-crate card"><h4>${n.kind==='contract'?'📦 Thùng carton':'🛍️ Túi giấy'} cho ${x.esc(x.npc(t.npc).display_name)}</h4>
    <div class="fa-crate-box">${crate.map(e=>{const p=produce(x,e.crop);return `<div class="fa-crate-line"><span>${p.emoji} ${e.qty} ${x.esc(p.unit)} · ${x.esc(e.grade)}${e.organic?' 🌿':''}</span><small>lô ${x.esc(e.lot)}</small><button type="button" class="icon-btn" aria-label="Trả lô ${x.esc(e.lot)} về kho" data-command="fa_unpack" data-payload="${x.esc(JSON.stringify({task:t.id,lot:e.lot}))}">↩︎</button></div>`;}).join('')||'<small class="muted">Thùng trống — xếp hàng từ Kho mát.</small>'}</div>
    ${labelStep(t,x,g)?'':`<h4 class="section-title">Nhãn</h4>${labelTiles(t,x)}`}
    <section class="fa-care fa-steps ${open?'open':''}">${carBtn(x,`<span class="fa-care-title">📋 Việc của đơn <b>${done}/${steps.length}</b></span>`,'steps',{},'fa-care-head ghost',` aria-expanded="${open}"`)}${open?stepRows(x,steps,'Việc của đơn'):''}</section></div>`;
}

/* ------------------------------------------------------------ next steps (guide.js)
 * An order is: produce in the cold room (harvest a ripe bed, look after a bed that ripens
 * today, collect eggs) → packed in the crate → an honest label → delivered. Farm work is
 * one tap on every order; the label is a judgement call: the right one on the first order,
 * after that the step points at the two labels. */
const inv=(x,what)=>({act:'inventory',label:`📦 Hết ${x.esc(what)}: mở Kho nhập thêm`});
const harvestGo=(x,p,c)=>({cmd:'fa_harvest',payload:{plot:p.id},confirm:p.growth<x.cc.thresholds.ripe?`${c.name} còn non: thu bây giờ chỉ đạt loại B. Vẫn thu?`:`Thu hoạch ${c.name.toLowerCase()} luống ${p.id} vào kho mát?`,
  label:`🧺 Thu hoạch ${x.esc(c.name.toLowerCase())} luống ${x.esc(p.id)}`});
/* How to get `need` more units of crop k today: a lot to pack, eggs to collect, a bed to harvest or to look after. */
function sourceStep(t,x,k,need){
  const d=data(x),n=t.needs,c=produce(x,k),th=x.cc.thresholds,m=x.cc.moisture,contract=n.kind==='contract';
  const fits=l=>l.crop===k&&l.left>=0&&!l.unsafe&&(!n.organic||l.organic);
  const lots=(d.cold||[]).filter(fits).sort((a,b)=>(a.grade>b.grade)-(a.grade<b.grade)||a.left-b.left);
  const A=lots.find(l=>l.grade==='A'),any=lots[0];
  const pack=l=>{const q=Math.min(need,l.qty);return {cmd:'fa_pack',payload:{task:t.id,lot:l.id,qty:q},label:`📦 Xếp ${q} ${x.esc(c.unit)} ${x.esc(c.name.toLowerCase())} loại ${l.grade} vào thùng`};};
  if(A||(any&&!contract))return {go:pack(A||any)};
  if(k==='egg'){
    const nest=d.coop?.nest||0;
    if(nest)return {go:{cmd:'fa_collect',payload:{},label:`🧺 Nhặt ${nest} trứng trong ổ`}};
    return any?{go:pack(any)}:{note:'gà đẻ thêm qua đêm'};
  }
  const beds=(d.plots||[]).filter(p=>p.crop===k&&!p.safe_in&&(!n.organic||p.organic)&&p.growth<th.rotten).sort((a,b)=>b.growth-a.growth);
  const ripe=beds.find(p=>p.growth>=th.ripe);
  if(ripe)return {plot:ripe.id,go:harvestGo(x,ripe,c)};
  const st=(x.room.inventory||{}).stock||{};
  for(const p of beds){
    const room=(p.cap||0)-(p.grown||0),today=p.eta===0||p.growth+room>=th.ripe;
    const boost=!today&&!p.compost&&(st.compost||0)>0&&p.growth+5+room+4>=th.ripe;
    if(!today&&!boost)continue;
    const tag=`${p.id}: ${p.growth}/${th.ripe}`;
    if(p.weeds)return {plot:p.id,note:tag,go:{cmd:'fa_weed',payload:{plot:p.id},label:`🌾 Nhổ cỏ luống ${x.esc(p.id)} cho ${x.esc(c.name.toLowerCase())} mau lớn`}};
    if(boost)return {plot:p.id,note:tag,go:{cmd:'fa_fertilize',payload:{plot:p.id,kind:'compost'},label:`🟫 Bón compost luống ${x.esc(p.id)}: chín kịp hôm nay`}};
    if(p.moisture<m.low)return {plot:p.id,note:tag,go:{cmd:'fa_water',payload:{plot:p.id},label:`💧 Tưới luống ${x.esc(p.id)} (${p.moisture}%)`}};
    return {plot:p.id,go:{cmd:'advance',payload:{},label:`⏳ Chờ ${x.esc(c.name.toLowerCase())} luống ${x.esc(p.id)} chín · ${p.growth}/${th.ripe}`}};
  }
  if(any)return {go:pack(any)};
  const young=beds.find(p=>p.growth>=th.young);
  if(young&&!contract)return {plot:young.id,go:harvestGo(x,young,c)};
  const soon=beds.find(p=>p.eta!=null);
  return {note:soon?`${soon.id} chín ${DAYS(soon.eta)}`:'chưa có luống nào trồng'};
}
function orderSteps(t,x){
  const d=data(x),n=t.needs,id=t.id,rows=[],crate=t.crate||[];
  for(const e of crate){
    if(e.unsafe)rows.push({ok:false,label:`Lô ${e.lot} chưa hết cách ly thuốc`,go:{cmd:'fa_unpack',payload:{task:id,lot:e.lot},label:`↩︎ Bỏ lô ${x.esc(e.lot)} ra khỏi thùng`}});
    else if(n.organic&&!e.organic)rows.push({ok:false,label:`Lô ${e.lot} không hữu cơ`,go:{cmd:'fa_unpack',payload:{task:id,lot:e.lot},label:`↩︎ Bỏ lô ${x.esc(e.lot)} (không hữu cơ)`}});
  }
  for(const [k,q] of Object.entries(n.items)){
    const c=produce(x,k),have=packed(t,k),label=`${q} ${c.unit} ${c.name.toLowerCase()}${n.kind==='contract'?' loại A':''}`;
    const b=sum(crate.filter(e=>e.crop===k&&e.grade==='B').map(e=>e.qty)),note=b?`A ${have-b} · B ${b} / ${q}`:`${have}/${q}`;
    if(have>=q){rows.push({ok:!(n.kind==='contract'&&b),label,note});continue;}
    const s=sourceStep(t,x,k,q-have);
    rows.push({ok:null,label,note:s.note||note,go:s.go,plot:s.plot});
  }
  if(crate.length){
    // Honest = no organic label over a lot that is not organic, and the organic label when the contract asks for it.
    const all=crate.every(e=>e.organic),right=n.organic||all?'organic':'plain',name={organic:'🌿 Nhãn hữu cơ + QR',plain:'🏷️ Nhãn thường'};
    const fine=t.label&&!(t.label==='organic'&&!all)&&!(n.organic&&t.label!=='organic');
    rows.push({key:'label',ok:t.label?!!fine:null,label:'Dán nhãn đúng sự thật',note:t.label&&!fine?(n.organic&&t.label!=='organic'?'hợp đồng cần nhãn hữu cơ':'có lô không hữu cơ'):'',
      go:fine?null:firstTime(x)?{cmd:'fa_label',payload:{task:id,label:right},label:`${name[right]}`}:{sel:'.fa-labels',label:'🏷️ Chọn nhãn: hữu cơ chỉ khi mọi lô đều hữu cơ'}});
    const st=(x.room.inventory||{}).stock||{},eggs=packed(t,'egg'),veg=crate.some(e=>e.crop!=='egg');
    const pack={};if(n.kind==='contract')pack.carton=1;else if(veg)pack.bag=1;if(eggs)pack.egg_tray=Math.ceil(eggs/10);
    for(const [k,q] of Object.entries(pack))if((st[k]||0)<q)rows.push({ok:false,label:`${supply(x,k).name} ×${q}`,note:`kho còn ${st[k]||0}`,go:inv(x,supply(x,k).name.toLowerCase())});
  }
  return rows;
}
const deliverFinal=(t,x,steps)=>({label:'🚚 GIAO HÀNG',go:finalGo(steps,'fa_deliver',{task:t.id},{question:'Khách sẽ kiểm số lượng, loại hàng và quét QR trên nhãn.',confirm:true}),
  ready:!!((t.crate||[]).length&&t.label),why:(t.crate||[]).length?'dán nhãn trước':'xếp hàng vào thùng trước'});
function taskGuide(t,x){
  if(data(x).desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở trại',go:{sel:'.fa-opts',label:'👉 Chọn cách xử lý chuyện ở trại'}}],final:{label:'Quyết chuyện ở trại',go:{sel:'.fa-opts'},ready:false}};
  if(!t.known)return {steps:[{ok:null,label:'Nghe khách đặt hàng',go:{cmd:'ask',payload:{task:t.id},label:'📞 Nhận đơn hàng'}}],pulse:'.fa-ask'};
  const steps=orderSteps(t,x);
  return {steps,final:deliverFinal(t,x,steps)};
}
function hintFor(g,x){
  const f=g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null;
  // Only steps with no way to do them today are left: the hint offers the finish, like the bottom button.
  const steps=f&&!pending(g.steps)?.go?g.steps.filter(s=>s.ok===true||s.go):g.steps;
  return nextHint(x,steps,{final:f,pulse:g.pulse});
}
/* The bottom bar: what the crate holds (icons and numbers) over the one next-step button. */
function bottomBar(t,x,g){
  if(!g.final)return '';
  // When the next step works a bed, that bed's numbers ride along, so the result of each tap shows next to the button.
  const bed=(data(x).plots||[]).find(p=>p.id===pending(g.steps)?.plot),th=x.cc.thresholds,m=x.cc.moisture;
  const plot=bed?`<span class="fa-bed">${x.esc(bed.id)} ${bed.crop?produce(x,bed.crop).emoji:''} ${bed.growth}/${th.ripe} · 💧${bed.moisture}%${bed.moisture<m.low?'↓':''}${bed.weeds?` · 🌾${bed.weeds}`:''}</span>`:'';
  const strip=t.known?`<div class="fa-strip" aria-label="Thùng hàng">${Object.entries(t.needs.items).map(([k,q])=>{const h=packed(t,k);return `<span class="${h>=q?'ok':''}">${produce(x,k).emoji} ${h}/${q}</span>`;}).join('')}<span class="${t.label?'ok':''}">${t.label==='organic'?'🌿':'🏷️'} ${t.label?'✓':'—'}</span>${plot}</div>`:'';
  return `<div class="fa-bar">${strip}${labelStep(t,x,g)?labelTiles(t,x,'fa-bar-labels'):''}${stepCta(x,g.steps,g.final)}</div>`;
}
/* Between orders: the daily chores that cost tomorrow's harvest or eggs when forgotten. */
function idleSteps(x){
  const d=data(x),st=(x.room.inventory||{}).stock||{},coop=d.coop||{},m=x.cc.moisture,rows=[];
  if(d.desk?.ev)return [{ok:null,label:'Quyết chuyện ở trại',go:{sel:'.fa-opts',label:'👉 Chọn cách xử lý chuyện ở trại'}}];
  if(!d.fed_today&&st.feed)rows.push({ok:null,label:'Cho gà ăn & thay nước',go:{cmd:'fa_feed',payload:{},label:'🌾 Cho gà ăn & thay nước'}});
  if(!coop.cleaned_today)rows.push({ok:null,label:'Dọn chuồng gà',go:{cmd:'fa_clean',payload:{},label:'🧹 Dọn chuồng gà'}});
  if(coop.nest)rows.push({ok:null,label:`Nhặt ${coop.nest} trứng`,go:{cmd:'fa_collect',payload:{},label:`🧺 Nhặt ${coop.nest} trứng trong ổ`}});
  const planted=(d.plots||[]).filter(p=>p.crop),dry=planted.filter(p=>p.moisture<m.low);
  // Several dry beds and none close to waterlogged: one turn of the valve waters them all.
  const valve=!d.nopump&&dry.length>=2&&planted.every(p=>p.moisture+(x.cc.water?.all||22)<=m.wet);
  if(valve)rows.push({ok:null,label:`Tưới ${dry.map(p=>p.id).join(', ')}`,go:{cmd:'fa_water',payload:{plot:'all'},label:`🚿 Mở van tưới cả vườn (${dry.length} luống khô)`}});
  const pl=d.pledge;
  if(pl&&pl.done<pl.qty){
    const lot=(d.cold||[]).find(l=>l.crop===pl.crop&&l.grade==='A'&&!l.unsafe&&l.left>=0);
    if(lot){const q=Math.min(pl.qty-pl.done,lot.qty);rows.push({ok:null,label:'Góp hàng cho HTX',go:{cmd:'fa_pledge',payload:{lot:lot.id,qty:q},label:`🤝 Góp ${q} ${x.esc(produce(x,pl.crop).unit)} ${x.esc(produce(x,pl.crop).name.toLowerCase())} cho HTX`}});}
  }
  // An empty bed with seeds in the store: open it so the seed choice is right there.
  const empty=(d.plots||[]).find(p=>!p.crop),seeds=(x.cc.crops||[]).some(c=>c.unlock<=(x.room.level||1)&&(st[c.seed]||0)>0);
  if(empty&&seeds)rows.push({ok:null,label:`Gieo luống trống ${empty.id}`,go:x.ui.plot===empty.id&&(x.ui.tab||'field')==='field'?{sel:'.fa-seeds',label:`🌱 Chọn hạt gieo luống ${x.esc(empty.id)}`}:{act:'car:open',data:{plot:empty.id},label:`🌱 Gieo luống trống ${x.esc(empty.id)}`}});
  for(const p of planted){
    if(p.moisture<m.low&&!valve)rows.push({ok:null,label:`Tưới luống ${p.id}`,go:{cmd:'fa_water',payload:{plot:p.id},label:`💧 Tưới luống ${x.esc(p.id)} (${p.moisture}%)`}});
    else if(p.weeds>=2)rows.push({ok:null,label:`Nhổ cỏ luống ${p.id}`,go:{cmd:'fa_weed',payload:{plot:p.id},label:`🌾 Nhổ cỏ luống ${x.esc(p.id)}`}});
  }
  return rows;
}

/* ------------------------------------------------------------ 🚶 Tự đi
 * The farm as a place to walk in (careers/farm_walk.js draws it, loaded on first use): the beds, the coop, the
 * cold room and the packing table, the trader's truck, the scooter. Same steps and the same commands as the
 * workbench: a step whose place is elsewhere becomes "📍 go there" (the walk takes about a second), the place you
 * stand at shows its own buttons, and the delivery is a ride on the scooter that ends with the same `fa_deliver`.
 * "⏩ Bấm nhanh" is the workbench above, unchanged. The choice (and the camera) is kept on this device. */
const PREF='mnl.farm.walk';
const prefs=()=>{try{return JSON.parse(localStorage.getItem(PREF)||'{}')||{};}catch{return {};}};
const setPref=o=>{try{localStorage.setItem(PREF,JSON.stringify({...prefs(),...o}));}catch{/* storage off: this visit only */}};
const walking=x=>!x.ui.fvOff&&prefs().mode!=='tap';
let walkMod=null;
const walkLoad=()=>walkMod??=import('./farm_walk.js').catch(error=>{console.error(error);return null;});
const PLACE={tank:'Bồn nước',coop:'Chuồng gà',shed:'Nhà kho',pack:'Bàn đóng hàng',bike:'Xe máy',truck:'Xe anh Tuấn',board:'Bảng thời tiết'};
const placeName=id=>/^P[1-6]$/.test(id||'')?`Luống ${id}`:PLACE[id]||'';
/* Where a step is done. */
const BED=new Set(['fa_water','fa_drain','fa_weed','fa_scout','fa_fertilize','fa_spray','fa_boost','fa_harvest','fa_clear','fa_plant']);
const AT={fa_feed:'coop',fa_clean:'coop',fa_collect:'coop',fa_hen:'coop',fa_pack:'pack',fa_unpack:'pack',fa_label:'pack',fa_discard:'pack',fa_pledge:'truck',fa_sell:'truck',fa_deliver:'bike'};
function spotOf(go,x){
  if(!go)return null;
  if(go.cmd)return BED.has(go.cmd)?(go.payload?.plot==='all'?'tank':go.payload?.plot||null):AT[go.cmd]||null;
  if(go.act==='car:open')return go.data?.plot||null;
  if(go.act==='inventory')return 'shed';
  if(go.sel==='.fa-seeds')return x.ui.plot||null;
  if(go.sel==='.fa-labels')return 'pack';
  return null;
}
function walkGo(go,x){
  const at=spotOf(go,x);
  if(!at)return go;
  if(at!==x.ui.fvNear)return {act:'car:fvgo',data:{to:at},label:`📍 ${x.esc(bareLabel(go.label||''))}`};
  // At the empty bed the seeds are right under the stage.
  if(go.act==='car:open')return {sel:'.fa-seeds',label:`🌱 Chọn hạt gieo luống ${x.esc(at)}`};
  return go;
}
const walkSteps=(steps,x)=>(steps||[]).map(s=>s&&s.ok!==true&&s.go?{...s,go:walkGo(s.go,x)}:s);
/* The finish: walk to the scooter, then ride. A finish asked early keeps the workbench's question. */
function walkFinal(t,x,g){
  const f=g.final;if(!f||f.go?.cmd!=='fa_deliver')return f;
  if(x.ui.fvNear!=='bike')return {...f,label:'🛵 Ra xe chở hàng',go:{act:'car:fvgo',data:{to:'bike'},label:'🛵 Ra xe chở hàng'}};
  return {...f,label:'🛵 Chở hàng đi giao',go:{act:'car:fvride',data:{task:t.id,ask:f.go.confirm||''},label:'🛵 Chở hàng đi giao'}};
}
/* Who waits at the end of the road (by farm_npc_0N), and how they look. */
const BUYER={1:['HTX rau Đồi Gió',{hair:'#5a5250',top:'#7f9a5c',hat:true}],2:['Nhà hàng Bếp Mây',{hair:'#2f2420',top:'#ffffff'}],3:['Sạp cô Hai',{hair:'#3a2c26',top:'#d98a7a'}],
  4:['Vựa anh Tuấn',{hair:'#3c2f28',top:'#8fb3cf',hat:true}],5:['Nhà bé Mít',{hair:'#3a2a22',top:'#f2c84b'}],6:['Lò bánh flan Bà Năm',{hair:'#d8d4cf',top:'#b89ad0'}],7:['Quán chay Lá Xanh',{hair:'#2f2622',top:'#7fae63'}]};
const sameGo=(a,b)=>!!(a&&b)&&(a.cmd||a.act)===(b.cmd||b.act)&&JSON.stringify(a.payload||a.data||{})===JSON.stringify(b.payload||b.data||{});
/* The buttons of the place you stand at (only the ones that do something now). */
function placeActs(at,t,x,g){
  const d=data(x),st=(x.room.inventory||{}).stock||{},coop=d.coop||{},th=x.cc.thresholds,out=[];
  const add=(label,go,cls='')=>out.push({...go,label,cls});
  const more=(label,what)=>add(label,{act:'car:fvmore',data:{more:what}},'ghost');
  if(/^P[1-6]$/.test(at||'')){
    const p=d.plots.find(q=>q.id===at);if(!p)return out;
    if(!p.crop){if(!p.compost&&st.compost)add('🟫 Bón lót',{cmd:'fa_fertilize',payload:{plot:p.id,kind:'compost'}},'ghost');return out;}
    if(p.stage==='rotten')add('🧹 Dọn luống',{cmd:'fa_clear',payload:{plot:p.id},confirm:'Nhổ bỏ toàn bộ cây trên luống này?'});
    else{
      if(p.growth>=th.young&&p.growth<th.rotten)add('🧺 Thu hoạch',{cmd:'fa_harvest',payload:{plot:p.id},confirm:harvestAsk(p,x)});
      add('💧 Tưới',{cmd:'fa_water',payload:{plot:p.id}});
      if(p.weeds)add('🌾 Nhổ cỏ',{cmd:'fa_weed',payload:{plot:p.id}});
      add('🔍 Thăm sâu',{cmd:'fa_scout',payload:{plot:p.id}},'ghost');
    }
    more('🟫 Bón & phun','bed');
  }else if(at==='tank'){
    if(!d.nopump&&d.plots.some(p=>p.crop))add('🚿 Mở van tưới cả vườn',{cmd:'fa_water',payload:{plot:'all'}});
  }else if(at==='coop'){
    if(!d.fed_today&&st.feed)add('🌾 Cho gà ăn',{cmd:'fa_feed',payload:{}});
    if(!coop.cleaned_today)add('🧹 Dọn chuồng',{cmd:'fa_clean',payload:{}});
    if(coop.nest)add(`🧺 Nhặt ${coop.nest} trứng`,{cmd:'fa_collect',payload:{}});
    more('🐔 Xem đàn gà','coop');
  }else if(at==='pack')more(t?'❄️ Kho mát & thùng hàng':'❄️ Kho mát','pack');
  else if(at==='truck')more('📈 Bán sỉ cho anh Tuấn','market');
  else if(at==='shed')add('📦 Kho vật tư',{act:'inventory'});
  else if(at==='board')more('🌤️ Xem dự báo','sky');
  else if(at==='bike'&&t?.known&&(t.crate||[]).length){const f=walkFinal(t,x,g);if(f?.go)add(f.label,f.go);}
  return out;
}
function placeLine(at,x){
  if(!at)return '';
  const p=/^P[1-6]$/.test(at)?data(x).plots.find(q=>q.id===at):null,c=p?.crop?produce(x,p.crop):null;
  return `<p class="fv-at"><b>📍 ${x.esc(placeName(at))}</b>${c?` · ${c.emoji} ${x.esc(c.name)} <small>${x.esc(when(p))}</small>`:p?' · <small>🌱 chọn hạt để gieo</small>':''}</p>`;
}
function orderChip(t,x){
  if(!t)return '';
  const who=x.npc(t.npc);
  if(!t.known)return `<div class="fv-chip">${x.portrait(who,32)}<span class="fv-chip-who"><b>${x.esc(who.display_name)}</b><small>📞 đang gọi đặt hàng</small></span></div>`;
  const items=Object.entries(t.needs.items).map(([k,q])=>{const h=packed(t,k);return `<span class="${h>=q?'ok':''}">${produce(x,k).emoji} ${h}/${q}</span>`;}).join('');
  return `<button type="button" class="fv-chip" data-action="car:fvmore" data-more="order" aria-label="Đơn của ${x.esc(who.display_name)}">${x.portrait(who,32)}<span class="fv-chip-who"><b>${x.esc(who.display_name)}</b><span class="patience"><span class="bar ${t.patience<50?'low':''}"><i style="width:${t.patience}%"></i></span></span></span>
    <span class="fa-strip">${items}<span class="${t.label?'ok':''}">${t.label==='organic'?'🌿':'🏷️'} ${t.label?'✓':'—'}</span></span><b class="price">${x.money(t.quoted_price||0)}</b></button>`;
}
function drawer(t,x,g){
  const what=x.ui.fvMore;if(!what)return '';
  const d=data(x),p=d.plots.find(q=>q.id===x.ui.fvNear);let body='',title='';
  if(what==='bed'&&p){title=placeName(p.id);body=plotPanel(p,x);}
  else if(what==='coop'){title='🐔 Chuồng gà';body=coopTab(x);}
  else if(what==='pack'){title='❄️ Kho mát';body=coldTab(t,x)+(t?crateSide(t,x,g):'');}
  else if(what==='market'){title='📈 Chợ đầu mối';body=marketTab(x);}
  else if(what==='sky'){title='🌤️ Thời tiết';const was=x.ui.wxOpen;x.ui.wxOpen=true;body=weatherBar(x);x.ui.wxOpen=was;}
  else if(what==='order'&&t){title='🧾 Đơn hàng';const was=x.ui.orderOpen;x.ui.orderOpen=true;body=orderTicket(t,x);x.ui.orderOpen=was;}
  if(!body)return '';
  return `<section class="fv-drawer" role="dialog" aria-label="${x.esc(plainTitle(title))}"><div class="fv-drawer-head"><b>${title}</b>${carBtn(x,'✕','fvmore',{more:''},'ghost small fv-x',' aria-label="Đóng"')}</div>${body}</section>`;
}
const plainTitle=s=>String(s).replace(/<[^>]*>/g,'');
const seg=(x,label,items)=>`<div class="fv-seg" role="group" aria-label="${label}">${items.map(([text,action,dat,on])=>carBtn(x,text,action,dat,on?'on':'',` aria-pressed="${on}"`)).join('')}</div>`;
const modeSeg=(x,walk)=>seg(x,'Cách chơi',[['🚶 Tự đi','fvmode',{mode:'walk'},walk],['⏩ Bấm nhanh','fvmode',{mode:'tap'},!walk]]);
const camSeg=x=>seg(x,'Góc nhìn',[['👁️ Thứ nhất','fvcam',{cam:'fp'},x.ui.fvCam!=='tp'],['Thứ ba','fvcam',{cam:'tp'},x.ui.fvCam==='tp']]);
/** The walk view: the stage first (re-renders keep it), the order, the overlay switches, the place's buttons and
 * the next-step button under it. `t` null: between orders. */
function walkView(t,x,g,idle=false){
  x.ui.fvCam??=prefs().cam==='tp'?'tp':'fp';
  x.ui.fvTask=t?.id||null;
  const steps=walkSteps(g.steps,x),final=(t&&walkFinal(t,x,g))||{label:'',go:null,ready:false},at=x.ui.fvNear||null;
  const next=pending(g.steps);
  x.ui.fvTarget=spotOf(next?.go,x)||(t&&!next&&g.final?.ready!==false&&g.final?.go?'bike':null);
  const ride=x.ui.fvRide;
  const hint=ride?'':t?hintFor({steps,final},x):pending(steps)?.go?nextHint(x,steps,{}):'';
  let acts;
  if(ride)acts=`<p class="fv-at"><b>🛵 ${x.esc(ride.place||'')}</b></p><button type="button" class="btn primary big grow gd-cta fv-honk" data-action="car:fvhonk" data-fd-wait=".fv-arrived">📯 Bóp còi</button>`;
  else{
    const cta=t||pending(steps)?.go?stepCta(x,steps,final):'',ctaGo=pending(steps)?.go;
    const own=placeActs(at,t,x,g).filter(o=>!sameGo(o,ctaGo)&&!(o.act==='car:fvride'&&cta.includes('car:fvride')));
    const p=/^P[1-6]$/.test(at||'')?data(x).plots.find(q=>q.id===at):null;
    const seeds=p&&!p.crop?seedTiles(p,x,'fv-seeds'):'';
    const labels=at==='pack'&&t&&labelStep(t,x,g)?labelTiles(t,x,'fa-bar-labels'):'';
    acts=`${placeLine(at,x)}${seeds}${labels}${own.length?`<div class="fv-btns">${own.map(o=>`<button type="button" class="btn small fv-btn ${o.cls}"${goAttrs(o)}>${o.label}</button>`).join('')}</div>`:''}${cta}`;
  }
  const top=ride?'':`<div class="fv-top">${camSeg(x)}${modeSeg(x,true)}</div>`;
  return `<div class="career-job fa fa-walk"${idle?' data-idle-open':''}><div class="fv-host" id="fvHost"><i hidden></i></div>${hint}${top}${ride?'':drawer(t,x,g)}
    ${deskCard(x)}<div class="fa-bar fv-acts">${orderChip(t,x)}${acts}</div></div>`;
}
/* What the engine tells the workbench. */
const HOOKS={
  near(x,id){x.ui.fvNear=id||null;if(/^P[1-6]$/.test(id||''))x.ui.plot=id;if(x.ui.fvMore&&!['order','sky'].includes(x.ui.fvMore))x.ui.fvMore=null;x.render();},
  ride(x,info){x.ui.fvRide=info||null;x.ui.fvMore=null;x.render();},
  deliver:(x,task)=>x.send('fa_deliver',{task,confirm:true}),
  slow(x){setPref({mode:'tap'});x.toast('Máy hơi chậm nên vườn chuyển sang Bấm nhanh. Muốn đi lại thì chạm 🚶 Tự đi.');x.render();},
  broken(x){x.ui.fvOff=true;x.render();},
  hint(){if(prefs().hint)return false;setPref({hint:1});return true;},
};

export default {
  id:ID,
  css:true,
  next(t,x){
    try{const n=x&&pending(taskGuide(t,x).steps);if(n)return x.esc(stepLine(n));}catch{/* fall back to the fixed lines */}
    if(!t.known)return 'Nghe khách đặt hàng';
    const missing=Object.entries(t.needs.items).filter(([k,q])=>packed(t,k)<q);
    if(missing.length)return 'Thu hoạch, rồi xếp hàng vào thùng';
    if(!t.label)return 'Dán nhãn trung thực';
    return 'Giao hàng cho khách';
  },
  job(t,x){
    const g=taskGuide(t,x),hint=hintFor(g,x);
    if(data(x).desk?.ev)return `<div class="career-job fa">${hint}${deskCard(x)}${weatherBar(x)}${bottomBar(t,x,g)}</div>`;
    if(walking(x))return walkView(t,x,g);
    const tab=x.ui.tab||'field';
    const main=tab==='coop'?coopTab(x):tab==='cold'?coldTab(t,x):tab==='market'?marketTab(x):fieldTab(x);
    // The order first; the weather and the farm's tabs below it. The bar keeps the next step in reach.
    return `<div class="career-job fa">${hint}${x.ui.fvOff?'':modeSeg(x,false)}${deskCard(x)}${orderTicket(t,x)}${weatherBar(x)}${tabs(x)}
      <div class="workbench"><section class="wb-main">${main}</section><aside class="wb-side">${crateSide(t,x,g)}</aside></div>${bottomBar(t,x,g)}</div>`;
  },
  idle(x){
    const steps=idleSteps(x),todo=pending(steps)?.go;
    const hint=todo?nextHint(x,steps,{}):'',bar=todo?`<div class="fa-bar">${stepCta(x,steps,{label:'',go:null,ready:false})}</div>`:'';
    if(data(x).desk?.ev)return `<div class="career-job fa">${hint}${deskCard(x)}${weatherBar(x)}${bar}</div>`;
    if(walking(x))return walkView(null,x,{steps},true);
    const tab=x.ui.tab||'field';
    const main=tab==='coop'?coopTab(x):tab==='cold'?coldTab(null,x):tab==='market'?marketTab(x):fieldTab(x);
    return `<div class="career-job fa">${hint}${x.ui.fvOff?'':modeSeg(x,false)}${weatherBar(x)}${deskCard(x)}${tabs(x)}
      <div class="workbench single"><section class="wb-main">${main}</section></div>${bar}</div>`;
  },
  // The next-step bar rides above the sheet's own sticky footer.
  // 🚶 Tự đi: the stage goes into #fvHost (again after a render that replaced the host) and keeps drawing.
  tick(root,x){
    keepBarAboveFooter(root);
    const host=root.querySelector(':scope>#fvHost');
    if(!host)return;
    walkLoad().then(m=>{
      if(!m){x.ui.fvOff=true;x.render();return;}
      if(!host.isConnected)return;
      // A ride the page no longer has (reloaded engine, another order now): back to the farm.
      if(x.ui.fvRide&&(!m.riding()||m.riding()!==x.ui.fvTask)){if(m.riding())m.cancelRide();x.ui.fvRide=null;x.render();return;}
      m.mount(host,x,HOOKS);
    });
  },
  // Day summary: "Ngày mai" first (the weather, beds to pick, eggs, the night's pests and soil, supplies), one way
  // to the supplies, the day's figures folded.
  summary(sum,x){
    if(!sum||typeof sum!=='object'||sum.eggs_tomorrow==null)return '';
    const lines=(Array.isArray(sum.lines)?sum.lines:[]).filter(l=>typeof l==='string');
    const night=lines.filter(l=>/^(🐛|🟫|🐔)/u.test(l)||l.includes(' Mai sang '));
    const sky=typeof sum.note==='string'&&sum.note.startsWith('Mai trời')?sum.note.split('. ')[0].replace(/\.$/,''):'';
    const ripe=Array.isArray(sum.ripe_tomorrow)?sum.ripe_tomorrow:[];
    const plan=[sky?`🌤️ ${x.esc(sky)}`:'',
      ripe.length?`<span>🧺 Luống chín:</span> <b>${x.esc(ripe.join(', '))}</b>`:'',
      sum.eggs_tomorrow?`🥚 Sáng mai có ${sum.eggs_tomorrow} trứng trong ổ`:'',
      sum.hungry_hens&&!night.some(l=>l.startsWith('🐔'))?'🐔 Hôm nay gà chưa được ăn: mai đẻ ít':'',
      ...night.map(l=>x.esc(l)),...stockLines(x)];
    const rows=[['Bán sỉ ở chợ đầu mối (xu)',sum.market_income],['Nông sản quá hạn',sum.expired_units],['Tinh thần đàn gà',sum.hen_mood!=null?`${sum.hen_mood}/100`:'']];
    return planBox(x,{lines:plan,go:['📦 Mở kho vật tư','inventory'],
      more:[sum.market_income?`🌱 Nông trại hôm nay · +${sum.market_income} xu chợ`:'🌱 Nông trại hôm nay',figures(x,rows,lines.filter(l=>!night.includes(l)))]});
  },
  actions:{
    async tab(data,el,x){x.ui.tab=['field','coop','cold','market'].includes(data.tab)?data.tab:'field';x.render();},
    async plot(data,el,x){x.ui.plot=x.ui.plot===data.plot?null:data.plot;x.render();},
    // A next step that works a bed: show the field with that bed open (never toggles it shut).
    async open(data,el,x){if(!/^P[1-6]$/.test(data.plot||''))return;x.ui.tab='field';x.ui.plot=data.plot;x.render();},
    async seen(data,el,x){x.ui.seen=data.key;x.render();},
    async care(data,el,x){x.ui.careOpen=!x.ui.careOpen;x.render();},
    async wx(data,el,x){x.ui.wxOpen=!x.ui.wxOpen;x.render();},
    async order(data,el,x){x.ui.orderOpen=!x.ui.orderOpen;x.render();},
    async steps(data,el,x){x.ui.stepsOpen=!x.ui.stepsOpen;x.render();},
    // 🚶 Tự đi
    async fvgo(d,el,x){const m=await walkLoad();x.ui.fvMore=null;m?.go(d.to);},
    async fvride(d,el,x){
      const t=(x.room.tasks||[]).find(q=>q.id===d.task);if(!t||!t.known)return;
      if(d.ask&&!await x.ask('Xác nhận',d.ask,'Đồng ý'))return;
      const m=await walkLoad();if(!m)return;
      const [sign,look]=BUYER[Number(String(t.npc).slice(-2))]||[x.npc(t.npc).display_name,{hair:'#3a2c26',top:'#8fb3cf'}];
      m.ride({task:t.id,place:sign,sign,look:{skin:'#e9c3a0',...look}});
    },
    async fvhonk(d,el,x){(await walkLoad())?.honk();},
    async fvcam(d,el,x){const cam=d.cam==='tp'?'tp':'fp';x.ui.fvCam=cam;setPref({cam});(await walkLoad())?.camera(cam);x.render();},
    async fvmode(d,el,x){const mode=d.mode==='tap'?'tap':'walk';setPref({mode});x.ui.fvMore=null;x.render();},
    async fvmore(d,el,x){x.ui.fvMore=d.more&&x.ui.fvMore!==d.more?d.more:null;x.render();},
  },
  dock:[['inventory','box','Kho vật tư','Hạt giống, phân, bao bì']],
};
