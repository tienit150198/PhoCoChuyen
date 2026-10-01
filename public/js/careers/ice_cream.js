/** Tiệm kem Góc Phượng — cô Hiền's ice-cream corner by the school gate (server: game/careers/ice_cream.py).
 * The morning (thermometer, the knob back to 4, a tub that froze again, the scoop well), the freezer lid,
 * scooping by weight on the counter scale (press light / even / full, scrape or top up 10 g), cups, cones,
 * coconut shells, a take-away box weighed by the 100 g, sticks from the drawer, toppings and allergies,
 * the melt clock, the birthday tray, and cash through the shared till.
 * The server decides everything; one tap sends one command. */
import {stepRows,nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {cashPanel,changeStep,changePayload,tillActions} from './till.js';
import {data,cc,lower,tile,act,pane,introCard,deskCard,dayBar,person,askCard,bottom,kitActions} from './street_kit.js';

const FL=(x,k)=>(cc(x).flavours||[]).find(f=>f.id===k)||{id:k,name:k,short:k,emoji:'🍨'};
const VS=(x,k)=>(cc(x).vessels||{})[k]||{name:k,emoji:'🥤',max:2,item:null};
const TP=(x,k)=>(cc(x).toppings||{})[k]||{name:k,emoji:'✨'};
const GOOD=x=>cc(x).good||[60,70];
const ADJ=x=>Number(cc(x).adj||10);
const ADJ_MAX=x=>Number(cc(x).adj_max||3);
const stock=(x,k)=>Number(data(x).stock?.[k]||0);
const tubG=(x,k)=>Number(data(x).tubs?.[k]?.g||0);
const press=x=>x.ui.press||'vua';
const sorted=a=>[...a].sort().join(',');
const grams=cup=>(cup.sc||[]).reduce((s,v)=>s+v.g,0);
const lineText=(x,ln)=>{
  if(ln.v==='que')return '🍡 Kem que đậu xanh';
  if(ln.v==='hop')return `📦 Hộp ${FL(x,ln.f[0]).short} ${ln.g} g`;
  return `${VS(x,ln.v).emoji} ${VS(x,ln.v).name}: ${ln.f.map(f=>FL(x,f).short).join(' + ')}${ln.top?.length?` · ${ln.top.map(k=>lower(TP(x,k).name)).join(' / ')}`:''}`;
};

/* ------------------------------------------------------------ pairing cups with the order (as the server does) */
function plan(t){
  const lines=t.needs?.lines||[],cups=t.cups||[],used=new Set(),pairs=new Map();
  lines.forEach((ln,li)=>{
    const want=sorted(ln.f);
    let ci=cups.findIndex((c,i)=>!used.has(i)&&c.v===ln.v&&sorted(c.sc.map(s=>s.f))===want);
    if(ci<0&&ln.v==='hop')ci=cups.findIndex((c,i)=>!used.has(i)&&c.v==='hop'&&c.sc.length&&c.sc.every(s=>s.f===ln.f[0]));
    if(ci>=0){used.add(ci);pairs.set(li,ci);}
  });
  // The cup being made: the last one on the counter, when it is not paired yet and still fits a line.
  const last=cups.length-1,lc=cups[last];
  let active=-1;
  if(lc&&!used.has(last)){
    active=lines.findIndex((ln,li)=>!pairs.has(li)&&ln.v===lc.v&&(ln.v==='hop'?lc.sc.every(s=>s.f===ln.f[0]):(()=>{const need=[...ln.f];return lc.sc.every(s=>{const i=need.indexOf(s.f);if(i<0)return false;need.splice(i,1);return true;});})()));
  }
  return {pairs,used,active,last};
}

/* ------------------------------------------------------------ the freezer strip and the melt clock */
function fzBar(x){
  const d=data(x),fz=d.fz||{},w=d.well||{},feel=fz.feel||'ok';
  const word={ok:'lạnh vừa',soft:'kem mềm',mushy:'kem nhão!',hard:'cứng đá'}[feel]||'';
  const lid=fz.lid?x.cmd('🧊 Đậy nắp tủ','kem_lid',{open:false},'small km-lid open'):x.cmd('Mở nắp','kem_lid',{open:true},'small ghost km-lid');
  return `<div class="km-fz feel-${x.esc(feel)}" role="group" aria-label="Tủ kem"><span class="km-temp"><span aria-hidden="true">🌡️</span><b>${Number(fz.temp)} °C</b><small>${x.esc(word)}</small></span>
    ${lid}<span class="km-well ${w.dirty?'dirty':''}"><span aria-hidden="true">💧</span><small>${w.dirty?'nước đục':'nước trong'}</small>${w.dirty&&d.shop?.open?x.cmd('Thay nước','kem_well',{},'small'):''}</span></div>`;
}
function meltBar(t,x){
  const m=t.melt;if(!m||m.end!=null||t.stage!=='prep')return '';
  const end=Number(m.start)+Number(m.limit),left=Math.ceil(end-x.now());
  return `<div class="km-melt ${left<=0?'late':left<=10?'soon':''}" role="timer" aria-live="off"><span aria-hidden="true">⏱️</span><span>Kem bắt đầu chảy sau</span><b data-km-melt="${end}">${left>0?`${left}s`:'đang chảy!'}</b></div>`;
}

/* ------------------------------------------------------------ the order and the counter */
function ticket(t,x){
  if(!t.known)return askCard(x,t,'👂 Hỏi khách gọi gì');
  const n=t.needs||{},{pairs}=plan(t);
  const chips=(n.lines||[]).map((ln,li)=>`<span class="km-chip ${pairs.has(li)?'ok':''}">${x.esc(lineText(x,ln))}</span>`).join('');
  const tags=[n.allergy?`<span class="tag red">⚠️ Dị ứng ${x.esc(cc(x).allergens?.[n.allergy]||n.allergy)}</span>`:'',n.check?'<span class="tag amber">👀 Nhìn cân kỹ</span>':'',n.coins?'<span class="tag">🪙 Trả xu lẻ</span>':''].join('');
  return person(x,t,`<p class="km-chips">${chips}</p>${n.note?`<p class="muted small">“${x.esc(n.note)}”</p>`:''}`,tags?`<span class="km-tags">${tags}</span>`:'');
}
function scaleRead(t,x){
  const cups=t.cups||[],cup=cups[cups.length-1];if(!cup)return '';
  if(cup.v==='hop'){
    const g=grams(cup),shown=g+(t.tare?0:Number(cc(x).box_tare||25)),ln=(t.needs?.lines||[]).find(l=>l.v==='hop');
    return `<div class="km-scale"><span class="km-lcd"><b>${shown}</b><small>g</small></span><div class="km-scale-side">${t.tare?'<span class="tag green">✓ Đã trừ bì hộp</span>':x.cmd('⚖️ Trừ bì hộp','kem_tare',{task:t.id},'small km-tare',grams(cup)>0)}
      ${ln?`<small>Khách lấy ${ln.g} g</small>`:''}${adjButtons(t,x,cup)}</div></div>`;
  }
  const sc=cup.sc[cup.sc.length-1];if(!sc)return `<div class="km-scale"><span class="km-lcd"><b>0</b><small>g</small></span><div class="km-scale-side"><small>Múc một viên lên cân</small></div></div>`;
  const [lo,hi]=GOOD(x),cls=sc.g<lo?'low':sc.g>hi?'high':'good';
  return `<div class="km-scale"><span class="km-lcd ${cls}"><b>${sc.g}</b><small>g</small></span><div class="km-scale-side"><small>Viên vừa múc · chuẩn ${lo}–${hi} g</small>${adjButtons(t,x,cup)}</div></div>`;
}
function adjButtons(t,x,cup){
  const sc=cup.sc[cup.sc.length-1];if(!sc)return '';
  const left=ADJ_MAX(x)-sc.a,dis=left<=0;
  return `<div class="km-adj">${x.cmd(`➖ Gạt bớt ${ADJ(x)} g`,'kem_adjust',{task:t.id,delta:-1},'small',dis)}${x.cmd(`➕ Múc thêm ${ADJ(x)} g`,'kem_adjust',{task:t.id,delta:1},'small',dis)}${dis?'<small class="muted">Viên này chỉnh đủ rồi</small>':''}</div>`;
}
function counter(t,x){
  const cups=t.cups||[],{used}=plan(t);
  const row=cups.map((c,i)=>{const v=VS(x,c.v);
    const sc=c.sc.map(s=>`<span class="km-sc ${s.g<GOOD(x)[0]?'low':s.g>GOOD(x)[1]?'high':''} ${s.x?.some(f=>f!=='hm')?'bad':''} ${s.x?.includes('hm')?'hm':''}">${x.esc(FL(x,s.f).emoji)}<small>${s.g}g</small></span>`).join('');
    return `<li class="km-cup ${i===cups.length-1?'now':''} ${used.has(i)?'done':''}"><span class="km-v" aria-hidden="true">${x.esc(v.emoji)}</span><span class="km-cup-body"><b>${x.esc(v.name)}</b><span class="km-scs">${sc}</span>${c.top?`<small>${x.esc(TP(x,c.top).emoji)} ${x.esc(TP(x,c.top).name)}</small>`:''}</span></li>`;}).join('');
  const drop=cups.length?x.confirmCmd('🗑️ Bỏ ly đang làm','kem_drop',{task:t.id},'Bỏ ly đang làm, làm lại cái khác?','small ghost'):'';
  return `<section class="card km-counter"><h4>🍨 Trên quầy</h4>${row?`<ul class="km-cups">${row}</ul>`:'<p class="small muted">Chưa có gì. Chọn ly, ốc quế hay trái dừa.</p>'}${scaleRead(t,x)}<div class="sk-go-end">${drop}</div></section>`;
}
function vesselRow(t,x){
  const want=new Set((t.needs?.lines||[]).map(l=>l.v));
  const v=(k)=>{const s=VS(x,k),n=s.item?stock(x,s.item):null,out=n===0;
    const cmd=k==='que'?'kem_que':'kem_vessel',payload=k==='que'?{task:t.id}:{task:t.id,v:k};
    return tile(x,cmd,payload,`<span class="tile-emoji">${x.esc(s.emoji)}</span><b>${x.esc(s.name)}</b><small>${n==null?(k==='hop'?'theo gam':'không giới hạn'):`còn ${n}`}</small>`,want.has(k)?'want':'',out||(k==='que'&&t.kind!=='serve'));};
  return `<section class="card km-vessels"><h4>Đựng bằng gì</h4><div class="tile-grid km-vgrid">${['ly','oc','dua_trai','hop','que'].map(v).join('')}</div></section>`;
}
function scoopPanel(t,x){
  const p=press(x),lab=cc(x).press_label||{};
  const presses=Object.keys(cc(x).press||{nhe:1,vua:1,day:1}).map(k=>act(x,x.esc(lab[k]||k),'press',{p:k},`small ${p===k?'primary':'ghost'}`,` aria-pressed="${p===k}"`)).join('');
  const want=new Set((t.needs?.lines||[]).flatMap(l=>l.f));
  const fl=(cc(x).flavours||[]).map(f=>{const g=tubG(x,f.id),n=stock(x,f.id),h=homeReady(x,f.id),rf=data(x).refrozen===f.id;
    return tile(x,'kem_scoop',{task:t.id,f:f.id,press:p},`<span class="tile-emoji">${x.esc(f.emoji)}</span><b>${x.esc(f.name)}</b><small>${g?`hộp đang múc ${g} g`:h?`${h} hộp nhà làm`:n?`${n} hộp mới`:'hết'}${rf?' · ⚠️ đông đá':''}</small>`,want.has(f.id)?'want':'',!g&&!n&&!h);}).join('');
  return `<section class="card km-scoop"><h4>🥄 Múc kem</h4><div class="km-press" role="group" aria-label="Múc tay">${presses}</div><div class="tile-grid km-fgrid">${fl}</div></section>`;
}
function topRow(t,x){
  const cups=t.cups||[],cup=cups[cups.length-1];if(!cup||['que','hop'].includes(cup.v))return '';
  const tops=Object.entries(cc(x).toppings||{}).map(([k,v])=>x.cmd(`${x.esc(v.emoji)} ${x.esc(v.name)}`,'kem_top',{task:t.id,top:k},`small ${cup.top===k?'primary':'ghost'}`)).join('');
  return `<section class="card km-tops"><h4>✨ Topping cho ${x.esc(lower(VS(x,cup.v).name))} đang làm</h4><div class="km-toprow">${tops}${cup.top?x.cmd('Bỏ topping','kem_top',{task:t.id,top:'none'},'small ghost'):''}</div></section>`;
}
function packPanel(t,x){
  if(t.kind!=='tray')return '';
  const packs=Object.entries(cc(x).packs||{}).map(([k,v])=>tile(x,'kem_pack',{task:t.id,pack:k},`<span class="tile-emoji">${{xop:'📦',tui:'🛍️',da_kho:'🌫️'}[k]||'📦'}</span><b>${x.esc(v)}</b>`,t.pack===k?'selected':'')).join('');
  return `<section class="card km-pack"><h4>🎂 Mang lên lớp 2A (mười phút)</h4><div class="tile-grid">${packs}</div></section>`;
}

/* ------------------------------------------------------------ the morning */
function setupPanel(t,x){
  const d=data(x),fz=d.fz||{},sh=d.shop||{},kt=cc(x).knob_t||{};
  const knobs=[1,2,3,4,5,6].map(k=>tile(x,'kem_knob',{knob:k},`<b>Số ${k}</b><small>${kt[k]??''} °C</small>`,`${fz.knob===k?'selected':''} ${k===cc(x).knob_ok?'want':''}`)).join('');
  const thermo=fz.read?`<div class="km-thermo feel-${x.esc(fz.feel||'ok')}"><b>${Number(fz.temp)} °C</b><small>nút đang số ${fz.knob} · về ${fz.goal} °C</small></div>`:x.cmd('🌡️ Xem nhiệt kế tủ','kem_thermo',{},'primary');
  const tubs=!sh.checked?x.cmd('🔍 Soi các hộp kem','kem_check',{},'primary'):d.refrozen?`<p class="small km-bad">🧊 Hộp ${x.esc(lower(FL(x,d.refrozen).name))} đông đá lại.</p>${x.cmd('🗑️ Bỏ hộp kem hỏng','kem_discard',{},'primary')}`:'<span class="tag green">✓ Hộp kem nào cũng mịn</span>';
  const well=d.well?.fresh?'<span class="tag green">✓ Nước ngâm muỗng mới thay</span>':x.cmd('💧 Thay nước ngâm muỗng','kem_well',{},'primary');
  return `<section class="card km-setup"><h4>Nhiệt kế tủ kem</h4>${thermo}<h4 class="section-title">Nút vặn tủ</h4><div class="tile-grid km-knobs">${knobs}</div>
    <h4 class="section-title">Hộp kem trong tủ</h4>${tubs}<h4 class="section-title">Khay ngâm muỗng</h4>${well}<p class="small muted">${x.esc(t.needs?.note||'')}</p></section>`;
}
function setupSteps(t,x){
  const d=data(x),fz=d.fz||{},sh=d.shop||{},ok=cc(x).knob_ok||4,rows=[];
  rows.push({ok:fz.read?true:null,label:'Xem nhiệt kế tủ',go:{cmd:'kem_thermo',payload:{},label:'🌡️ Xem nhiệt kế tủ'}});
  rows.push({ok:fz.knob===ok?true:null,label:`Vặn nút tủ về số ${ok}`,note:fz.knob!==ok&&fz.read?`đang số ${fz.knob}`:'',go:{cmd:'kem_knob',payload:{knob:ok},label:`🎛️ Vặn nút về số ${ok}`}});
  rows.push({ok:sh.checked?(d.refrozen?false:true):null,label:'Soi các hộp kem',note:d.refrozen?'có hộp đông đá lại':'',go:sh.checked&&d.refrozen?{cmd:'kem_discard',payload:{},label:'🗑️ Bỏ hộp kem hỏng'}:{cmd:'kem_check',payload:{},label:'🔍 Soi các hộp kem'}});
  rows.push({ok:d.well?.fresh?true:null,label:'Thay nước ngâm muỗng',go:{cmd:'kem_well',payload:{},label:'💧 Thay nước ngâm muỗng'}});
  return rows;
}

/* ------------------------------------------------------------ học nghề: the first customers with cô Hiền */
function learnCard(x){
  const l=data(x).learn;if(!l?.on)return '';
  return `<section class="card km-learn" aria-label="Học nghề"><span class="eyebrow">👩‍🍳 Học nghề với cô Hiền · khách ${Math.min(l.n+1,l.of)}/${l.of}</span><b>${x.esc(l.title||'')}</b><p class="small">${x.esc(l.text||'')}</p><p class="small muted">Cô đứng cạnh: lỡ sai chỗ nào, cô nhắc trước khi đưa kem cho khách.</p></section>`;
}

/* ------------------------------------------------------------ kem nhà làm: a house batch */
const RC=(x,k)=>(cc(x).recipes||{})[k];
const homeReady=(x,f)=>(data(x).home||[]).filter(h=>h.f===f&&h.ready).length;
function recipeOpen(x,k){
  const r=RC(x,k);if(!r?.cert)return true;
  const J=x.state?.journey;
  if(J?.story)return J.certificates?.[cc(x).cert_id]?.earned_day!=null;
  return Number(x.room.day||0)>=Number(cc(x).cert_free_day||5);
}
const QTAG={ok:'<span class="tag green">✓ mịn thơm</span>',soft:'<span class="tag amber">mềm, mau chảy</span>',icy:'<span class="tag amber">dăm đá</span>',grainy:'<span class="tag red">lợn cợn</span>'};
function homeList(x){
  const home=data(x).home||[];if(!home.length)return '';
  return `<ul class="km-home">${home.map((h,i)=>{const r=RC(x,h.f)||{};
    return `<li><span aria-hidden="true">${x.esc(r.emoji||'🏠')}</span><b>${x.esc(r.name||h.f)}</b>${QTAG[h.q]||''}<small>${h.ready?'bán được':'đang đông, mai bán'}</small>${h.q!=='ok'?x.confirmCmd('🗑️ Bỏ','kem_mk_toss',{i},'Bỏ hộp kem nhà làm không đạt này?','small ghost'):''}</li>`;}).join('')}</ul>`;
}
function recipeCard(x,r,b){
  const lo=(cc(x).cook_ok||[76,88]),cool=cc(x).cool_ok||10;
  const how={steam:`Hấp khoai ${r.steam} lượt cho chín bở`,measure:'Đong đúng sổ',cook:`Nấu lửa vừa, khuấy tới khi sánh (${lo[0]}–${lo[1]} °C). Đừng để sôi`,
    cool:`Ngâm thau nước đá, nguội dưới ${cool} °C`,blend:`Xay ${r.blend} lượt cho mịn`,churn:`Máy đánh kem ${r.churn[0]}–${r.churn[1]} phút`,freeze:'Đổ hộp, dán nhãn ngày, đông qua đêm'};
  return `<div class="km-card"><p class="small"><b>📒 Sổ cô Hiền · ${x.esc(r.name)}</b><br>${x.esc(r.note)}</p><ul class="km-ings">${r.ings.map(i=>`<li><span>${x.esc(i.name)}</span><b>${x.esc(i.card)}</b>${b?.ing?.[i.id]!=null?`<small>đã đong ${b.ing[i.id]} ${x.esc(i.unit)}</small>`:''}</li>`).join('')}</ul>
    <ol class="km-steps">${r.steps.map((s,i)=>`<li class="${b&&i<b.at?'done':b&&i===b.at?'now':''}"><b>${x.esc((cc(x).step_label||{})[s]||s)}</b><small>${x.esc(how[s]||'')}</small></li>`).join('')}</ol></div>`;
}
function batchStep(x,r,b){
  if(b.burnt)return `<p class="notice small km-bad">🔥 Khét đáy nồi rồi. Mẻ này không bán được.</p>${x.cmd('🗑️ Đổ bỏ mẻ này','kem_mk_bin',{},'primary')}`;
  const next=(label,dis=false)=>x.cmd(label,'kem_mk_next',{},'primary',dis);
  const temp=`<div class="km-pot"><span class="km-lcd ${b.temp>=Number(cc(x).boil_at||89)?'high':''}"><b>${b.temp}</b><small>°C</small></span></div>`;
  switch(b.step){
    case 'steam':return `<p class="small">♨️ Đã hấp ${b.n} lượt.</p><div class="km-row">${x.cmd('♨️ Hấp thêm một lượt','kem_mk_steam',{},'')}${next('Khoai chín, nghiền mịn →',!b.n)}</div>`;
    case 'measure':{const rows=r.ings.map(i=>`<div class="km-meas"><span>${x.esc(i.name)}</span><div class="km-row">${i.opts.map(o=>x.cmd(`${o} ${x.esc(i.unit)}`,'kem_mk_add',{ing:i.id,amt:o},`small ${b.ing[i.id]===o?'primary':'ghost'}`)).join('')}</div></div>`).join('');
      return `<p class="small muted">Sổ ghi bằng lon, ly, muỗng; vạch trên ca và cân ghi ml, gam.</p>${rows}<div class="km-row">${next('Đổ hết vào nồi →',r.ings.some(i=>b.ing[i.id]==null))}</div>`;}
    case 'cook':return `${temp}<div class="km-row">${x.cmd('🔥 Lửa nhỏ, khuấy','kem_mk_heat',{fire:'nho'},'')}${x.cmd('🔥🔥 Lửa lớn','kem_mk_heat',{fire:'lon'},'')}${next('Tắt bếp →',!b.n)}</div>`;
    case 'cool':return `${temp}<div class="km-row">${x.cmd('🧊 Ngâm thau đá, khuấy','kem_mk_cool',{},'')}${next('Nhấc nồi ra →')}</div>`;
    case 'blend':return `<p class="small">🌀 Đã xay ${b.n} lượt.</p><div class="km-row">${x.cmd('🌀 Xay một lượt','kem_mk_blend',{},'')}${next('Xay xong →',!b.n)}</div>`;
    case 'churn':return `<p class="small">⚙️ Hẹn giờ máy đánh kem:</p><div class="km-row">${(cc(x).churn_min||[]).map(m=>x.cmd(`${m} phút`,'kem_mk_churn',{min:m},'small ghost')).join('')}</div>`;
    case 'freeze':return `<div class="km-row">${x.cmd('🏠 Đổ hộp, cho vào tủ','kem_mk_freeze',{},'primary')}</div>`;
  }
  return '';
}
function batchPanel(x){
  const d=data(x),b=d.batch,home=homeList(x);
  if(b){const r=RC(x,b.f);if(!r)return '';
    return `<section class="card km-batch"><h4>🏠 Kem nhà làm · ${x.esc(r.name)} <small>bước ${b.at+1}/${b.of}</small></h4>${recipeCard(x,r,b)}${batchStep(x,r,b)}
      <div class="sk-go-end">${b.burnt?'':x.confirmCmd('🗑️ Đổ bỏ mẻ','kem_mk_bin',{},'Đổ bỏ mẻ kem đang làm? Tiền nguyên liệu không lấy lại được.','small ghost')}</div></section>`;}
  const full=(d.home||[]).length>=Number(cc(x).home_max||3);
  const tiles=Object.entries(cc(x).recipes||{}).map(([k,r])=>{const open=recipeOpen(x,k);
    const why=open?`${r.cost} xu nguyên liệu`:(x.state?.journey?.story?'🎓 Cần Chứng chỉ làm kem':`mở từ ngày ${cc(x).cert_free_day||5}`);
    return tile(x,'kem_mk_start',{f:k},`<span class="tile-emoji">${x.esc(r.emoji)}</span><b>${x.esc(r.name)}</b><small>${x.esc(why)}</small>`,'',!open||d.made_today||full);}).join('');
  const lead=d.made_today?'Hôm nay máy đánh kem đã chạy một mẻ. Mai làm tiếp nhé.':full?'Tủ đã đủ hộp kem nhà làm, bán bớt rồi nấu thêm.':
    `Mỗi ngày một mẻ. Đông qua đêm, mai bán: viên kem nhà làm khách trả thêm ${cc(x).home_plus||1} xu.`;
  return pane(x,'kmBatch',`<span>🏠 Kem nhà làm</span><small>${(d.home||[]).length?`${(d.home||[]).length} hộp trong tủ`:'tự nấu một mẻ'}</small>`,
    `<p class="small muted">${x.esc(lead)}</p><div class="tile-grid km-rgrid">${tiles}</div>${home}`,false,'km-batch');
}

/* ------------------------------------------------------------ the guide */
function orderSteps(t,x){
  const d=data(x),n=t.needs||{},lines=n.lines||[],cups=t.cups||[],{pairs,active,last}=plan(t),rows=[];
  if(!d.shop?.open)rows.push({ok:null,label:'Mở tiệm xong mới bán',go:null});
  if(d.well?.dirty)rows.push({ok:null,label:'Nước ngâm muỗng đục rồi',go:{cmd:'kem_well',payload:{},label:'💧 Thay nước ngâm muỗng'}});
  const lc=cups[last],sc=lc?.sc?.[lc.sc.length-1],[lo,hi]=GOOD(x);
  let scooping=false;
  // The scoop just made, on the scale: a top-up or a scrape while it can still be fixed (paired cup or not).
  if(lc&&lc.v!=='hop'&&sc&&sc.a<ADJ_MAX(x)&&(sc.g<lo||sc.g>hi)){scooping=true;
    rows.push({ok:false,label:sc.g<lo?'Viên kem nhỏ quá':'Viên kem to quá',note:`${sc.g} g`,
      go:{cmd:'kem_adjust',payload:{task:t.id,delta:sc.g<lo?1:-1},label:sc.g<lo?`➕ Múc thêm ${ADJ(x)} g`:`➖ Gạt bớt ${ADJ(x)} g`}});}
  // The cup in the making: its next scoop, or the box filled to weight.
  if(active>=0){
    const ln=lines[active];
    if(ln.v==='hop'){
      const g=grams(lc),a=sc?.a??ADJ_MAX(x);
      if(!t.tare&&!g)rows.push({ok:null,label:'Trừ bì hộp trên cân',go:{cmd:'kem_tare',payload:{task:t.id},label:'⚖️ Trừ bì hộp'}});
      if(g<ln.g*0.95){scooping=true;const rest=ln.g-g;
        if(d.fz?.lid&&!(rest<=ADJ(x)+2&&a<ADJ_MAX(x)))rows.push({ok:null,label:'Đậy nắp giữa hai muỗng',note:'để mở là tủ ấm nhanh',go:{cmd:'kem_lid',payload:{open:false},label:'🧊 Đậy nắp tủ'}});
        else rows.push({ok:null,label:`Múc cho đủ ${ln.g} g`,note:`đang ${g} g`,go:rest<=ADJ(x)+2&&a<ADJ_MAX(x)?{cmd:'kem_adjust',payload:{task:t.id,delta:1},label:`➕ Múc thêm ${ADJ(x)} g`}
          :{cmd:'kem_scoop',payload:{task:t.id,f:ln.f[0],press:rest<56?'nhe':press(x)},label:`${x.esc(FL(x,ln.f[0]).emoji)} Múc kem ${x.esc(FL(x,ln.f[0]).short)}`}});}
      else if(g>ln.g*1.12&&a<ADJ_MAX(x))rows.push({ok:false,label:'Hộp nặng quá',note:`${g} g`,go:{cmd:'kem_adjust',payload:{task:t.id,delta:-1},label:`➖ Gạt bớt ${ADJ(x)} g`}});
    }else{
      const need=[...ln.f];lc.sc.forEach(s=>{const i=need.indexOf(s.f);if(i>=0)need.splice(i,1);});
      if(need.length){scooping=true;const f=FL(x,need[0]);
        rows.push({ok:null,label:`Múc viên ${f.short}`,note:`${lc.sc.length}/${ln.f.length} viên`,go:tubG(x,f.id)||stock(x,f.id)||homeReady(x,f.id)?{cmd:'kem_scoop',payload:{task:t.id,f:f.id,press:press(x)},label:`${x.esc(f.emoji)} Múc viên ${x.esc(f.short)}`}:null});}
    }
  }
  if(!scooping&&d.fz?.lid)rows.push({ok:false,label:'Nắp tủ đang mở',go:{cmd:'kem_lid',payload:{open:false},label:'🧊 Đậy nắp tủ'}});
  lines.forEach((ln,li)=>{
    if(pairs.has(li)){
      const ci=pairs.get(li),cup=cups[ci];
      if(ln.top?.length&&!ln.top.includes(cup.top)){const k=ln.top.find(v=>v!==n.allergy)||ln.top[0];
        rows.push({ok:null,label:`Rắc ${lower(TP(x,k).name)}`,go:{cmd:'kem_top',payload:{task:t.id,top:k,cup:ci},label:`${x.esc(TP(x,k).emoji)} Rắc ${x.esc(lower(TP(x,k).name))}`}});}
      else if(!ln.top?.length&&cup.top)rows.push({ok:false,label:'Khách không gọi topping',go:{cmd:'kem_top',payload:{task:t.id,top:'none',cup:ci},label:'Bỏ topping'}});
      else rows.push({ok:true,label:lineText(x,ln)});
      return;
    }
    if(li===active){rows.push({ok:null,label:lineText(x,ln),note:'đang làm'});return;}
    const v=VS(x,ln.v),out=v.item&&!stock(x,v.item);
    const missing=ln.f.find(f=>!tubG(x,f)&&!stock(x,f)&&!homeReady(x,f));
    const go=active>=0||out||missing?null:ln.v==='que'?{cmd:'kem_que',payload:{task:t.id},label:'🍡 Lấy kem que'}:{cmd:'kem_vessel',payload:{task:t.id,v:ln.v},label:`${x.esc(v.emoji)} Lấy ${x.esc(lower(v.name))}`};
    rows.push({ok:null,label:lineText(x,ln),note:out?`hết ${lower(v.name)}`:missing?`hết ${FL(x,missing).short}`:'',go});
  });
  if(t.kind==='tray'&&pairs.size===lines.length&&t.pack!=='xop')rows.push({ok:t.pack?false:null,label:'Xếp khay mang lên lớp',go:{cmd:'kem_pack',payload:{task:t.id,pack:'xop'},label:'📦 Xếp thùng xốp + đá gel'}});
  return rows;
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở tiệm',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'kem_intro',payload:{},label:'🍨 Vào việc thôi!'}}],final:null};
  if(t.kind==='setup'){const steps=setupSteps(t,x);return {steps,final:{label:'🍨 MỞ TIỆM',go:finalGo(steps,'kem_open',{task:t.id}),ready:true}};}
  if(!t.known)return {steps:[{ok:null,label:'Hỏi khách',go:{cmd:'ask',payload:{task:t.id},label:'👂 Hỏi khách gọi gì'}}],final:null,pulse:'.sk-ask'};
  if(t.stage==='pay'){const s=changeStep(x,t.id,t.cash),steps=s?[s]:[];return {steps,final:{label:'💵 ĐƯA TIỀN THỐI',go:finalGo(steps,'kem_pay',{task:t.id,...changePayload(x,t.id,t.cash)}),ready:true}};}
  const steps=orderSteps(t,x),stuck=steps.some(s=>s.ok===null&&!s.go&&/^hết /.test(s.note||''))&&!(t.cups||[]).length;
  if(stuck)return {steps,final:{label:'🙏 Nói thật: tiệm hết món này',go:{cmd:'kem_decline',payload:{task:t.id}},ready:true}};
  return {steps,final:{label:'🍨 ĐƯA KEM',go:finalGo(steps,'kem_serve',{task:t.id}),ready:!!(t.cups||[]).length,why:'làm món trước đã'}};
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});

/* ------------------------------------------------------------ idle: the shop between customers */
function shopView(x){
  const d=data(x),tubs=(cc(x).flavours||[]).map(f=>{const g=tubG(x,f.id),n=stock(x,f.id),full=Number(cc(x).tub_g||1200);
    return `<li><span aria-hidden="true">${x.esc(f.emoji)}</span><b>${x.esc(f.name)}</b><span class="sk-meter ${g&&g<full/5?'warn':''}"><i style="width:${Math.round(g/full*100)}%"></i></span><small>${g?`${g} g`:'chưa mở'} · ${n} hộp mới${homeReady(x,f.id)?` · ${homeReady(x,f.id)} nhà làm`:''}</small></li>`;}).join('');
  return `<section class="card km-shop"><h4>🧊 Trong tủ kem</h4><ul class="km-tubs">${tubs}</ul><p class="small muted">🍡 ${stock(x,'que')} cây kem que · 🍦 ${stock(x,'oc')} ốc quế · 🥥 ${stock(x,'trai_dua')} trái dừa</p></section>`;
}

export default {
  id:'ice_cream',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='setup'?'Xem tủ kem, mở tiệm':!t.known?'Hỏi khách gọi gì':'Múc kem cho khách';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    const top=`${introCard(x,'kem_intro','🍨')}${deskCard(x,'kem_desk','Chuyện ở tiệm')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk km">${hint}${top}${bottom(x,g)}</div>`;
    let main='',side='';
    if(t.kind==='setup'){main=`${setupPanel(t,x)}${batchPanel(x)}`;side=stepRows(x,g.steps,'Việc mở tiệm');}
    else if(!t.known)main='';
    else if(t.stage==='pay')main=`${t.needs?.coins&&!t.cash?.gap?'<p class="notice small">🪙 Bé đổ cả nắm xu lẻ ra quầy: đếm từng đồng rồi thối lại.</p>':''}${cashPanel(x,t.id,t.cash)}`;
    else{main=`${meltBar(t,x)}${counter(t,x)}${scoopPanel(t,x)}${topRow(t,x)}${packPanel(t,x)}${vesselRow(t,x)}`;side=stepRows(x,g.steps,'Món của khách');}
    const head=t.kind==='setup'?dayBar(x):`${learnCard(x)}${ticket(t,x)}${dayBar(x)}${fzBar(x)}`;
    return `<div class="career-job sk km">${hint}${top}${head}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x),top=`${introCard(x,'kem_intro','🍨')}${deskCard(x,'kem_desk','Chuyện ở tiệm')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro){const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện ở tiệm',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'kem_intro',payload:{},label:'🍨 Vào việc thôi!'}}],final:null};
      return `<div class="career-job sk km">${hintFor(g,x)}${top}${bottom(x,g)}</div>`;}
    return `<div class="career-job sk km">${top}${dayBar(x)}${fzBar(x)}${batchPanel(x)}${shopView(x)}</div>`;
  },
  tick(root,x){
    keepBarAboveFooter(root);
    const el=root.querySelector('[data-km-melt]');
    if(el){const left=Math.ceil(Number(el.dataset.kmMelt)-x.now()),s=left>0?`${left}s`:'đang chảy!';
      if(el.textContent!==s)el.textContent=s;const bar=el.closest('.km-melt');bar?.classList.toggle('soon',left>0&&left<=10);bar?.classList.toggle('late',left<=0);}
  },
  actions:{...tillActions,...kitActions,
    async press(d,el,x){x.ui.press=d.p;x.render();},
  },
  dock:[['inventory','box','Kho kem','Nhập hộp kem, ốc quế, kem que…']],
};
