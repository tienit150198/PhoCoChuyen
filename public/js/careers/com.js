/** Cơm tấm Dì Bảy — a rice stall at the mouth of the market (server: game/careers/com.py).
 * The morning (two pots with the right water line, the bowl of nước mắm tasted and fixed, the charcoal
 * lit, the trays laid in the glass case), the grill (sườn turned once, each side 8–16 s, lifted to the
 * warming rack), every plate (đĩa or hộp, rice by the ladle from the right pot, dishes from the case and
 * the rack, a fried egg, mỡ hành, nước mắm poured / on the side / soy sauce, soup) and the shared till.
 * The server decides everything; one tap sends one command. */
import {stepRows,nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {cashPanel,changeStep,changePayload,tillActions} from './till.js';
import {data,cc,lower,tile,introCard,deskCard,dayBar,person,askCard,bottom,kitActions,tip,clean,few} from './street_kit.js';

const DISH=(x,k)=>(cc(x).dishes||{})[k]||{name:k,short:k,emoji:'🍽️',src:'tray'};
const RICE=(x,k)=>(cc(x).rice||{})[k]||{name:k,short:k,emoji:'🍚'};
const VS=(x,k)=>(cc(x).vessels||{})[k]||{name:k,emoji:'🍽️'};
const VA=(x,n)=>(cc(x).va_word||{})[n]||`${n} vá`;
const SIDE=x=>cc(x).side_ok||[8,16];
const BURN=x=>Number(cc(x).side_burn||24);
const stock=(x,k)=>Number(data(x).stock?.[k]||0);
const sorted=a=>[...a].sort().join(',');
const MAM_WORD={ruoi:'rưới nước mắm',rieng:'nước mắm để riêng',tuong:'nước tương'};
const FIX_FOR={man:'nuoc',lat:'mam',ngot:'chanh',chua:'duong'};
const FIRST_TRAYS=['bi','cha','thit_kho','rau','ca_kho','dau_hu'];
const lineText=(x,ln)=>`${RICE(x,ln.r).name}${ln.va===2?'':`, ${VA(x,ln.va)}`} · ${ln.it.map(k=>DISH(x,k).short).join(', ')}${ln.mo?'':' · không hành mỡ'} · ${MAM_WORD[ln.mam]||'không nước mắm'}${ln.canh?' · có canh':''}`;
const wantVessel=t=>t.needs?.togo?'hop':'dia';
// Nước mắm on a plate: a box always on the side (unless soy sauce), a plate as the customer said.
const wantMam=(t,ln)=>ln.mam==='tuong'?'tuong':wantVessel(t)==='hop'?'rieng':ln.mam;

/* ------------------------------------------------------------ pairing plates with the order (as the server does) */
function plan(t){
  const lines=t.needs?.lines||[],plates=t.plates||[],used=new Set(),pairs=new Map();
  lines.forEach((ln,li)=>{
    const want=sorted(ln.it),pi=plates.findIndex((p,i)=>!used.has(i)&&sorted(p.it)===want);
    if(pi>=0){used.add(pi);pairs.set(li,pi);}
  });
  // The plate being made: the last one, not paired yet, still fitting an open line.
  const last=plates.length-1,lp=plates[last];let active=-1;
  if(lp&&!used.has(last)){
    active=lines.findIndex((ln,li)=>{if(pairs.has(li))return false;const need=[...ln.it];
      return lp.it.every(k=>{const i=need.indexOf(k);if(i<0)return false;need.splice(i,1);return true;});});
  }
  return {pairs,used,active,last};
}
const potReady=(x,r)=>{const p=data(x).pots?.[r];return !!p&&p.va>0&&x.now()>=Number(p.at);};
const goodPiece=x=>(data(x).rack||[]).findIndex(pc=>pc.q==='ok');

/* ------------------------------------------------------------ the grill */
function grillPhase(x){
  const b=data(x).grill?.b;if(!b)return null;
  const from=b.flip!=null?Number(b.flip):Number(b.start),s=Math.max(0,x.now()-from);
  return {b,from,s,side:b.flip!=null?2:1};
}
const sideWord=(x,s)=>{const [lo,hi]=SIDE(x);return s<lo?'còn hồng…':s<=hi?'VÀNG ĐỀU — ĐƯỢC RỒI!':s<=BURN(x)?'xém cạnh rồi…':'cháy khét!';};
function grillBar(x){
  const d=data(x),g=d.grill||{},ph=grillPhase(x),[lo,hi]=SIDE(x),max=BURN(x)+6;
  if(!g.lit)return '';
  const zones=`<i class="ct-z raw" style="width:${lo/max*100}%"></i><i class="ct-z ok" style="width:${(hi-lo)/max*100}%"></i><i class="ct-z xem" style="width:${(BURN(x)-hi)/max*100}%"></i><i class="ct-z khet"></i>`;
  if(!ph)return '';
  return `<div class="ct-gauge" data-ct-from="${ph.from}" data-max="${max}"><div class="ct-track">${zones}<span class="ct-needle"></span></div><small class="ct-gauge-label">${ph.s.toFixed(1)} giây · ${x.esc(sideWord(x,ph.s))}</small></div>`;
}
function grillCard(x,t){
  const d=data(x),g=d.grill||{},rack=d.rack||[],ph=grillPhase(x),open=d.shop?.open;
  if(!g.lit)return `<section class="card ct-grill"><h4>🔥 Bếp than</h4><p class="small muted">Bếp chưa nhóm.</p>${x.cmd('🔥 Nhóm bếp than','com_fire',{},'primary')}</section>`;
  let body='';
  if(ph){
    const [lo,hi]=SIDE(x);
    body=`<p class="small"><b>${ph.b.n} miếng sườn trên vỉ</b> · ${ph.side===1?'mặt thứ nhất':'đã trở, mặt thứ hai'} · vàng đều trong ${lo}–${hi} giây</p>${grillBar(x)}
      <div class="ct-row">${ph.side===1?x.cmd('🔄 Trở mặt','com_flip',{},'primary ct-stop'):''}${x.cmd('🍖 Gắp ra khay','com_lift',{},ph.side===2?'primary ct-stop':'ghost ct-stop')}</div>`;
  }else{
    const room=Number(cc(x).rack_max||8)-rack.length,n=Math.min(Number(cc(x).batch_max||4),room,stock(x,'suon'));
    body=`<p class="small muted">Vỉ trống · kho còn ${stock(x,'suon')} miếng sườn ướp</p><div class="ct-row" role="group" aria-label="Đặt sườn lên vỉ">${[1,2,3,4].map(k=>x.cmd(`🍖 ${k} miếng`,'com_grill',{n:k},'small',k>n)).join('')}</div>${n<1?`<small class="muted">${!stock(x,'suon')?'Hết sườn: nhập ở Kho':'Khay giữ ấm đầy'}</small>`:''}`;
  }
  const chips=rack.map((pc,i)=>{const bad=pc.q!=='ok',label=`🍖 <small>${x.esc((cc(x).grill_note||{})[pc.q]||pc.q)}</small>`;
    const pick=t&&t.known&&t.stage==='prep'&&(t.plates||[]).length&&open?x.cmd(label,'com_pick',{task:t.id,item:'suon',i,plate:(t.plates||[]).length-1},`small ct-pc q-${pc.q}`):`<span class="ct-pc q-${x.esc(pc.q)}">${label}</span>`;
    return `<li>${pick}${bad?x.confirmCmd('🗑️','com_toss',{i},'Bỏ miếng sườn này?','small ghost ct-toss'):''}</li>`;}).join('');
  return `<section class="card ct-grill"><h4>🔥 Bếp than · vỉ sườn</h4>${body}<h4 class="section-title">Khay giữ ấm <small>${rack.length}/${cc(x).rack_max||8}</small></h4>${chips?`<ul class="ct-rack">${chips}</ul>`:'<p class="small muted">Chưa có miếng nào.</p>'}</section>`;
}

/* ------------------------------------------------------------ the pots, the case */
function potLine(x,r){
  const p=data(x).pots?.[r]||{},R=RICE(x,r);
  if(!p.va)return `<span class="ct-pot empty"><span aria-hidden="true">${x.esc(R.emoji)}</span><b>${x.esc(R.name)}</b><small>hết cơm</small></span>`;
  const left=Math.ceil(Number(p.at)-x.now());
  const q=left>0?`<small data-ct-pot="${Number(p.at)}">chín sau ${left}s</small>`:p.q!=='ok'?`<small class="ct-bad">${x.esc((cc(x).rice_note||{})[p.q]||p.q)}</small>`:'<small>dẻo thơm</small>';
  return `<span class="ct-pot ${left>0?'cooking':''}"><span aria-hidden="true">${x.esc(R.emoji)}</span><b>${x.esc(R.name)}</b><span class="sk-meter"><i style="width:${p.va/Number(cc(x).pot_va||14)*100}%"></i></span><small>${p.va} vá</small>${q}</span>`;
}
function stallBar(x){
  const d=data(x),m=d.mam||{};
  return `<div class="ct-stall" role="group" aria-label="Xe cơm">${potLine(x,'tam')}${potLine(x,'trang')}<span class="ct-pot"><span aria-hidden="true">🫙</span><b>Nước mắm</b><small>${m.tasted?(m.q==='ok'?'vừa miệng':'chưa vừa'):'chưa nếm'}</small></span></div>`;
}
function caseTiles(x,t,pi){
  const tr=data(x).trays||{},want=new Set();
  const ln=(t.needs?.lines||[])[plan(t).active];(ln?.it||[]).forEach(k=>want.add(k));
  return (cc(x).trays||FIRST_TRAYS).map(k=>{const D=DISH(x,k),n=Number(tr[k]?.n||0);
    return tile(x,'com_pick',{task:t.id,item:k,plate:pi},`<span class="tile-emoji">${x.esc(D.emoji)}</span><b>${x.esc(D.name)}</b><small>${n?`còn ${n} phần`:'khay trống'}</small>`,want.has(k)?'want':'',!n);}).join('');
}

/* ------------------------------------------------------------ the order and the counter */
function ticket(t,x){
  if(!t.known)return askCard(x,t,'👂 Hỏi khách gọi gì');
  const n=t.needs||{},{pairs}=plan(t);
  const chips=(n.lines||[]).map((ln,li)=>`<span class="ct-chip ${pairs.has(li)?'ok':''}">${x.esc(VS(x,wantVessel(t)).emoji)} ${x.esc(lineText(x,ln))}</span>`).join('');
  const tags=[n.togo?'<span class="tag">🥡 Mang về</span>':'',n.chay?'<span class="tag green">📿 Ăn chay</span>':'',n.check?'<span class="tag amber">👀 Liếc dĩa kỹ</span>':''].join('');
  return person(x,t,`<p class="ct-chips">${chips}</p>${n.note?`<p class="muted small">${x.esc(n.note)}</p>`:''}`,tags?`<span class="ct-tags">${tags}</span>`:'');
}
function plateCard(x,t,p,i,now){
  const items=p.it.map(k=>`<span class="ct-it">${x.esc(DISH(x,k).emoji)} ${x.esc(DISH(x,k).short)}</span>`).join('');
  const bits=[p.r?`${x.esc(RICE(x,p.r==='mix'?'tam':p.r).emoji)} ${p.va} vá${p.r==='mix'?' (lẫn hai nồi)':''}`:'chưa xới cơm',p.mo?'🌿 mỡ hành':'',p.mam?`🫙 ${MAM_WORD[p.mam]}`:'',p.canh?'🥣 canh':''].filter(Boolean).join(' · ');
  const warn=(p.x||[]).length?`<small class="ct-bad">⚠️ ${(p.x||[]).map(q=>x.esc((cc(x).grill_note||{})[q]||(cc(x).rice_note||{})[q]||q)).join(', ')}</small>`:'';
  return `<li class="ct-plate ${now?'now':''}"><span class="ct-v" aria-hidden="true">${x.esc(VS(x,p.v).emoji)}</span><span class="ct-plate-body"><b>${x.esc(VS(x,p.v).name)}</b><small>${bits}</small><span class="ct-its">${items}</span>${warn}</span></li>`;
}
function counter(t,x){
  const plates=t.plates||[],full=plates.length>=Number(cc(x).plates_max||6);
  const row=plates.map((p,i)=>plateCard(x,t,p,i,i===plates.length-1)).join('');
  const take=['dia','hop'].map(v=>x.cmd(`${x.esc(VS(x,v).emoji)} Lấy ${v==='dia'?'dĩa':'hộp'}`,'com_plate',{task:t.id,v},`small ${v===wantVessel(t)?'':'ghost'}`,full||(v==='hop'&&!stock(x,'hop')))).join('');
  const drop=plates.length?x.confirmCmd('🗑️ Làm lại dĩa này','com_drop',{task:t.id},'Bỏ dĩa đang làm, làm lại cái khác?','small ghost'):'';
  return `<section class="card ct-counter"><h4>🍽️ Trên quầy</h4>${row?`<ul class="ct-plates">${row}</ul>`:'<p class="small muted">Chưa có dĩa nào.</p>'}<div class="ct-row">${take}</div><div class="sk-go-end">${drop}</div></section>`;
}
function platePanel(t,x){
  const plates=t.plates||[];if(!plates.length)return '';
  const pi=plates.length-1,p=plates[pi],box=p.v==='hop';
  const rice=['tam','trang'].map(r=>{const R=RICE(x,r),pot=data(x).pots?.[r]||{};
    return x.cmd(`${x.esc(R.emoji)} Xới 1 vá ${x.esc(R.short)}`,'com_rice',{task:t.id,r,plate:pi},'com-rice',!pot.va||p.va>=Number(cc(x).va_max||4));}).join('');
  const eggs=[['dao','Ốp la lòng đào'],['chin','Ốp la chín kỹ']].map(([h,l])=>x.cmd(`🍳 ${l}`,'com_egg',{task:t.id,how:h,plate:pi},'small ghost',!stock(x,'trung'))).join('');
  const mams=Object.entries(cc(x).mam||{}).map(([k,l])=>x.cmd(x.esc(l),'com_mam',{task:t.id,m:k,plate:pi},`small ${p.mam===k?'primary':'ghost'}`,false)).join('');
  return `<section class="card ct-make"><h4>${x.esc(VS(x,p.v).emoji)} ${box?'Hộp':'Dĩa'} đang làm · ${p.va} vá cơm</h4>
    <h4 class="section-title">Xới cơm</h4><div class="ct-row">${rice}</div>
    <h4 class="section-title">Tủ kính</h4><div class="tile-grid ct-case">${caseTiles(x,t,pi)}</div>
    <h4 class="section-title">Chảo trứng</h4><div class="ct-row">${eggs}<small class="muted">${stock(x,'trung')} quả</small></div>
    <h4 class="section-title">Chan, rưới</h4><div class="ct-row">${x.cmd('🌿 Mỡ hành','com_mo',{task:t.id,plate:pi,on:!p.mo},`small ${p.mo?'primary':'ghost'}`)}${x.cmd(box?'🥣 Bịch canh':'🥣 Chén canh','com_canh',{task:t.id,plate:pi,on:!p.canh},`small ${p.canh?'primary':'ghost'}`)}</div>
    <div class="ct-row">${mams}${p.mam?x.cmd('Không nước mắm','com_mam',{task:t.id,m:'none',plate:pi},'small ghost'):''}</div></section>`;
}

/* ------------------------------------------------------------ the morning */
const WSHORT={lung:'½',mot:'1',ruoi:'1½'};
function setupPanel(t,x){
  const d=data(x),m=d.mam||{},g=d.grill||{};
  const pot=r=>{const R=RICE(x,r),p=d.pots?.[r]||{};
    if(p.va)return `<div class="ct-cook"><b>${x.esc(R.emoji)} ${x.esc(R.name)}</b>${potLine(x,r)}</div>`;
    // Clean layout: the water depth as a number of knuckles (½ · 1 · 1½); the question is in the "?" sheet.
    return `<div class="ct-cook"><b>${x.esc(R.emoji)} ${x.esc(R.name)}${clean()?'':': đổ nước tới đâu?'}</b><div class="ct-row">${Object.entries(cc(x).water||{}).map(([k,l])=>x.cmd(clean()?WSHORT[k]||x.esc(l):x.esc(l),'com_cook',{r,water:k},'small ghost',!stock(x,R.item||(r==='tam'?'gao_tam':'gao'))).replace('<button ',`<button aria-label="${x.esc(l)}" `)).join('')}</div></div>`;};
  const fix=m.tasted?`<p class="small">🥄 Nước mắm ${x.esc((cc(x).taste||{})[m.q]||'')}</p><div class="ct-row">${Object.entries(cc(x).fix||{}).map(([k,l])=>x.cmd(x.esc(l),'com_fix',{add:k},'small ghost')).join('')}</div>`:x.cmd('🥄 Nếm nước mắm','com_taste',{},'primary');
  // Clean layout: each dish in two words unless two dishes would then read the same (then in full).
  const keys=cc(x).trays||FIRST_TRAYS,two=keys.map(k=>few(DISH(x,k).name,2,true)),dup=new Set(two.filter((v,i)=>two.indexOf(v)!==i));
  const dishName=(k,i)=>clean()&&!dup.has(two[i])?two[i]:DISH(x,k).name;
  const trays=keys.map((k,i)=>{const D=DISH(x,k),n=Number(d.trays?.[k]?.n||0);
    return tile(x,'com_tray',{item:k},`<span class="tile-emoji">${x.esc(D.emoji)}</span><b>${x.esc(dishName(k,i))}</b><small>${clean()?`${n||'–'} · 📦 ${stock(x,k)}`:`${n?`${n} phần`:'chưa bày'} · kho ${stock(x,k)}`}</small>`,n?'selected':'',!stock(x,k)||n+Number((cc(x).tray_n||{})[k]||8)>Number(cc(x).tray_max||16));}).join('');
  if(clean())return `<section class="card ct-setup"><h4 aria-label="Đổ nước mấy đốt ngón tay? Gạo tấm hút ít nước hơn gạo trắng.">💧 Mấy đốt? Tấm ít hơn</h4>${tip('Đổ nước tới đâu (đốt ngón tay)? Gạo tấm hút ít nước hơn gạo trắng.','Hai nồi cơm','p')}${pot('tam')}${pot('trang')}
    <div class="ct-row ct-morning">${m.tasted?fix:x.cmd('🥄 Nếm','com_taste',{},'primary').replace('<button ','<button aria-label="Nếm chén nước mắm pha tối qua" ')}${g.lit?'<span class="tag green">✓ Than hồng</span>':x.cmd('🔥 Nhóm','com_fire',{},'primary').replace('<button ','<button aria-label="Nhóm bếp than" ')}</div>
    <h4 class="section-title" aria-label="Bày khay">🍱</h4>${tip('Đồ nấu không để qua đêm: bày vừa đủ bán.','Bày khay lên tủ kính','p')}<div class="tile-grid ct-case">${trays}</div>
    ${tip(x.esc(t.needs?.note||''),'','p')}</section>`;
  return `<section class="card ct-setup"><h4>🍚 Hai nồi cơm</h4><p class="small muted">Gạo tấm hút ít nước hơn gạo trắng.</p>${pot('tam')}${pot('trang')}
    <h4 class="section-title">🫙 Chén nước mắm pha tối qua</h4>${fix}
    <h4 class="section-title">🔥 Bếp than</h4>${g.lit?'<span class="tag green">✓ Than hồng đều</span>':x.cmd('🔥 Nhóm bếp than','com_fire',{},'primary')}
    <h4 class="section-title">🍱 Bày khay lên tủ kính</h4><p class="small muted">Đồ nấu không để qua đêm: bày vừa đủ bán.</p><div class="tile-grid ct-case">${trays}</div>
    <p class="small muted">${x.esc(t.needs?.note||'')}</p></section>`;
}
function setupSteps(t,x){
  const d=data(x),m=d.mam||{},rows=[],water=cc(x).water||{};
  for(const r of ['tam','trang']){const R=RICE(x,r),w=R.water||(r==='tam'?'lung':'mot'),p=d.pots?.[r]||{};
    rows.push({ok:p.va?true:null,label:`Nấu nồi ${lower(R.name)}`,go:{cmd:'com_cook',payload:{r,water:w},label:clean()?`${R.emoji} Nấu ${WSHORT[w]||''}`:`${R.emoji} ${water[w]||'Nấu'}`}});}
  if(!m.tasted)rows.push({ok:null,label:'Nếm chén nước mắm',go:{cmd:'com_taste',payload:{},label:'🥄 Nếm nước mắm'}});
  else if(m.q!=='ok'){const k=FIX_FOR[m.q];rows.push({ok:false,label:'Chỉnh nước mắm cho vừa',note:(cc(x).taste||{})[m.q]||'',go:{cmd:'com_fix',payload:{add:k},label:`🫙 ${(cc(x).fix||{})[k]||'Chỉnh'}`}});}
  else rows.push({ok:true,label:'Nước mắm vừa miệng'});
  rows.push({ok:d.grill?.lit?true:null,label:'Nhóm bếp than',go:{cmd:'com_fire',payload:{},label:'🔥 Nhóm bếp than'}});
  const laid=FIRST_TRAYS.filter(k=>Number(d.trays?.[k]?.n||0)>0),next=FIRST_TRAYS.find(k=>!laid.includes(k)&&stock(x,k)>0);
  rows.push({ok:laid.length>=2?true:null,label:'Bày khay lên tủ kính',note:`${laid.length} khay · bày vừa đủ`,go:laid.length<2&&next?{cmd:'com_tray',payload:{item:next},label:`${DISH(x,next).emoji} Bày khay ${lower(DISH(x,next).short)}`}:null});
  return rows;
}

/* ------------------------------------------------------------ the guide */
function grillStep(x){
  const d=data(x),ph=grillPhase(x),[lo]=SIDE(x);
  if(!d.grill?.lit)return {ok:null,label:'Nhóm bếp than',go:{cmd:'com_fire',payload:{},label:'🔥 Nhóm bếp than'}};
  if(!ph)return stock(x,'suon')?{ok:null,label:'Nướng sườn',note:'trên khay hết miếng ngon',go:{cmd:'com_grill',payload:{n:Math.min(4,stock(x,'suon'))},label:'🍖 Đặt sườn lên vỉ'}}
    :{ok:null,label:'Hết sườn ướp',note:'nhập ở Kho hoặc nói thật với khách',go:{act:'warehouse',label:'🧺 Nhập ở Kho'},out:true};
  if(ph.s<lo)return {ok:null,label:ph.side===1?'Chờ mặt dưới vàng rồi trở':'Chờ mặt kia vàng rồi gắp',note:`${Math.ceil(lo-ph.s)} giây nữa`,go:null};
  return ph.side===1?{ok:null,label:'Trở mặt sườn',go:{cmd:'com_flip',payload:{},label:'🔄 Trở mặt'}}:{ok:null,label:'Gắp sườn ra khay',go:{cmd:'com_lift',payload:{},label:'🍖 Gắp ra khay'}};
}
function lineSteps(t,x,ln,pi,rows){
  const p=t.plates[pi];
  if(p.va<ln.va){const R=RICE(x,ln.r),ready=potReady(x,ln.r);
    rows.push({ok:null,label:`Xới ${lower(R.name)}: ${VA(x,ln.va)}`,note:`${p.va}/${ln.va} vá${ready?'':' · nồi chưa sẵn'}`,go:ready?{cmd:'com_rice',payload:{task:t.id,r:ln.r,plate:pi},label:`${R.emoji} Xới 1 vá ${R.short}`}:null});return;}
  const need=[...ln.it];p.it.forEach(k=>{const i=need.indexOf(k);if(i>=0)need.splice(i,1);});
  if(need.length){const k=need[0],D=DISH(x,k);
    if(k==='suon'){const i=goodPiece(x);rows.push(i>=0?{ok:null,label:'Gắp miếng sườn vàng đều',go:{cmd:'com_pick',payload:{task:t.id,item:'suon',i,plate:pi},label:'🍖 Gắp sườn'}}:grillStep(x));}
    else if(D.src==='pan')rows.push(stock(x,'trung')?{ok:null,label:D.name,go:{cmd:'com_egg',payload:{task:t.id,how:k==='trung_dao'?'dao':'chin',plate:pi},label:`🍳 ${D.name}`}}
      :{ok:null,label:D.name,note:'hết trứng: nhập ở Kho hoặc nói thật với khách',go:{act:'warehouse',label:'🧺 Nhập ở Kho'},out:true});
    else{const n=Number(data(x).trays?.[k]?.n||0);
      rows.push(n?{ok:null,label:`Gắp ${lower(D.name)}`,go:{cmd:'com_pick',payload:{task:t.id,item:k,plate:pi},label:`${D.emoji} Gắp ${D.short}`}}
        :stock(x,k)?{ok:null,label:`Gắp ${lower(D.name)}`,note:'khay trống',go:{cmd:'com_tray',payload:{item:k},label:`${D.emoji} Bày khay ${D.short}`}}
        :{ok:null,label:`Hết ${lower(D.name)}`,note:'nhập ở Kho hoặc nói thật với khách',go:{act:'warehouse',label:'🧺 Nhập ở Kho'},out:true});}
    return;
  }
  const mo=ln.mo&&!ln.chay;
  if(mo!==!!p.mo){rows.push({ok:false,label:mo?'Chan mỡ hành':'Khách không ăn mỡ hành',go:{cmd:'com_mo',payload:{task:t.id,plate:pi,on:mo},label:mo?'🌿 Mỡ hành':'Bỏ mỡ hành'}});return;}
  const m=wantMam(t,ln);
  if(p.mam!==m){rows.push({ok:null,label:MAM_WORD[m],go:{cmd:'com_mam',payload:{task:t.id,m,plate:pi},label:`🫙 ${(cc(x).mam||{})[m]||MAM_WORD[m]}`}});return;}
  if(ln.canh!==!!p.canh){rows.push({ok:false,label:ln.canh?'Múc canh':'Khách không lấy canh',go:{cmd:'com_canh',payload:{task:t.id,plate:pi,on:ln.canh},label:ln.canh?'🥣 Múc canh':'Bỏ canh'}});return;}
  rows.push({ok:true,label:lineText(x,ln)});
}
function orderSteps(t,x){
  const d=data(x),lines=t.needs?.lines||[],plates=t.plates||[],{pairs,active,last}=plan(t),rows=[];
  if(!d.shop?.open)rows.push({ok:null,label:'Mở quán xong mới bán',go:null});
  const lp=plates[last];
  if(lp&&lp.v!==wantVessel(t))rows.push({ok:false,label:wantVessel(t)==='hop'?'Khách mua mang về: lấy hộp':'Khách ngồi ăn: lấy dĩa',go:{cmd:'com_drop',payload:{task:t.id},label:'🗑️ Làm lại'}});
  lines.forEach((ln,li)=>{
    if(pairs.has(li))return lineSteps(t,x,ln,pairs.get(li),rows);
    if(li===active)return lineSteps(t,x,ln,last,rows);
    const v=wantVessel(t);
    rows.push({ok:null,label:lineText(x,ln),go:active>=0?null:{cmd:'com_plate',payload:{task:t.id,v},label:`${VS(x,v).emoji} Lấy ${v==='dia'?'dĩa':'hộp'}`},note:active>=0?'làm sau':''});
  });
  if(lp&&active<0&&!pairs.size&&!rows.some(r=>r.ok===false))rows.push({ok:false,label:'Dĩa này không đúng món khách gọi',go:{cmd:'com_drop',payload:{task:t.id},label:'🗑️ Làm lại dĩa này'}});
  return rows;
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở quán',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'com_intro',payload:{},label:'🍚 Vào việc thôi!'}}],final:null};
  if(t.kind==='setup'){const steps=setupSteps(t,x);return {steps,final:{label:'🍚 MỞ QUÁN',go:finalGo(steps,'com_open',{task:t.id}),ready:true}};}
  if(!t.known)return {steps:[{ok:null,label:'Hỏi khách',go:{cmd:'ask',payload:{task:t.id},label:'👂 Hỏi khách gọi gì'}}],final:null,pulse:'.sk-ask'};
  if(t.stage==='pay'){const s=changeStep(x,t.id,t.cash),steps=s?[s]:[];return {steps,final:{label:'💵 ĐƯA TIỀN THỐI',go:finalGo(steps,'com_pay',{task:t.id,...changePayload(x,t.id,t.cash)}),ready:true}};}
  const steps=orderSteps(t,x);
  // Out of a dish, with nothing in the stock room: say so (the plates already made are thrown out).
  const out=(t.needs?.lines||[]).some(ln=>ln.it.some(k=>{const D=DISH(x,k);return D.src==='tray'?!Number(d.trays?.[k]?.n||0)&&!stock(x,k):D.src==='pan'?!stock(x,'trung'):goodPiece(x)<0&&!stock(x,'suon')&&!d.grill?.b;}));
  if(out)return {steps,final:{label:'🙏 Nói thật: quán hết món này',go:{cmd:'com_decline',payload:{task:t.id},confirm:(t.plates||[]).length?'Dĩa đang làm phải bỏ. Nói thật với khách là quán hết món?':''},ready:true}};
  const wait=pending(steps);   // a pot still cooking, a side still pink: the button waits with the reason
  return {steps,final:{label:'🍚 ĐƯA CƠM',go:finalGo(steps,'com_serve',{task:t.id}),ready:!!(t.plates||[]).length&&!(wait&&!wait.go),why:'làm dĩa cơm trước đã',
    can:wait&&!wait.go?undefined:t.can?.com_serve}};   // the server's pre-check (com.py _plate_rules)
}
/** When the guide changes by itself (a pot done, a side ready to turn): the workbench redraws then. */
function wakeAt(x){
  const d=data(x),now=x.now(),at=[];
  for(const p of Object.values(d.pots||{}))if(p.va>0&&Number(p.at)>now)at.push(Number(p.at));
  const ph=grillPhase(x);if(ph&&ph.from+SIDE(x)[0]>now)at.push(ph.from+SIDE(x)[0]);
  return at.length?Math.min(...at)+0.2:0;
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});

/* ------------------------------------------------------------ idle: the stall between customers */
function caseView(x){
  const tr=data(x).trays||{};
  const rows=(cc(x).trays||FIRST_TRAYS).map(k=>{const D=DISH(x,k),n=Number(tr[k]?.n||0);
    return `<li><span aria-hidden="true">${x.esc(D.emoji)}</span><b>${x.esc(D.name)}</b><span class="sk-meter ${n&&n<3?'warn':''}"><i style="width:${n/Number(cc(x).tray_max||16)*100}%"></i></span><small>${n?`${n} phần`:'khay trống'} · kho ${stock(x,k)}</small>${!n||n<3?x.cmd('＋ Bày','com_tray',{item:k},'small ghost',!stock(x,k)):''}</li>`;}).join('');
  return `<section class="card ct-shop"><h4>🍱 Tủ kính</h4><ul class="ct-trays">${rows}</ul><p class="small muted">🍖 ${stock(x,'suon')} miếng sườn ướp · 🥚 ${stock(x,'trung')} trứng · 🥡 ${stock(x,'hop')} hộp</p></section>`;
}
function potsCard(x){
  const d=data(x),empty=['tam','trang'].filter(r=>!d.pots?.[r]?.va);
  if(!empty.length||!d.shop?.open)return '';
  return `<section class="card ct-refill"><h4>🍚 Nồi hết cơm</h4>${empty.map(r=>{const R=RICE(x,r);return `<div class="ct-cook"><b>${x.esc(R.name)}: đổ nước tới đâu?</b><div class="ct-row">${Object.entries(cc(x).water||{}).map(([k,l])=>x.cmd(x.esc(l),'com_cook',{r,water:k},'small ghost',!stock(x,R.item))).join('')}</div></div>`;}).join('')}</section>`;
}

export default {
  id:'com',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='setup'?'Nấu cơm, mở quán':!t.known?'Hỏi khách gọi gì':'Xới cơm cho khách';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    const top=`${introCard(x,'com_intro','🍚')}${deskCard(x,'com_desk','Chuyện ở quán')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk ct">${hint}${top}${bottom(x,g)}</div>`;
    let main='',side='';
    if(t.kind==='setup'){main=setupPanel(t,x);side=stepRows(x,g.steps,'Việc mở quán',{chip:true});}
    else if(!t.known)main='';
    else if(t.stage==='pay')main=cashPanel(x,t.id,t.cash);
    else{const fire=!!data(x).grill?.b;   // a batch on the grill comes first: its bar is what to watch
      main=fire?`${grillCard(x,t)}${counter(t,x)}${platePanel(t,x)}${potsCard(x)}`:`${counter(t,x)}${platePanel(t,x)}${grillCard(x,t)}${potsCard(x)}`;side=stepRows(x,g.steps,'Cơm của khách',{chip:true});}
    const head=t.kind==='setup'?dayBar(x):`${ticket(t,x)}${dayBar(x)}${stallBar(x)}`;
    return `<div class="career-job sk ct" data-ct-wake="${wakeAt(x)}">${hint}${top}${head}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x),top=`${introCard(x,'com_intro','🍚')}${deskCard(x,'com_desk','Chuyện ở quán')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro){const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện ở quán',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'com_intro',payload:{},label:'🍚 Vào việc thôi!'}}],final:null};
      return `<div class="career-job sk ct">${hintFor(g,x)}${top}${bottom(x,g)}</div>`;}
    return `<div class="career-job sk ct" data-ct-wake="${wakeAt(x)}">${top}${dayBar(x)}${stallBar(x)}${grillCard(x,null)}${potsCard(x)}${caseView(x)}</div>`;
  },
  tick(root,x){
    keepBarAboveFooter(root);
    const w=root.matches?.('[data-ct-wake]')?root:root.querySelector('[data-ct-wake]'),at=Number(w?.dataset.ctWake||0);
    if(at&&x.now()>=at){w.dataset.ctWake='0';x.render();return;}
    root.querySelectorAll('[data-ct-pot]').forEach(el=>{const left=Math.ceil(Number(el.dataset.ctPot)-x.now()),s=left>0?`chín sau ${left}s`:'chín rồi';if(el.textContent!==s)el.textContent=s;});
  },
  // The grill (v4/careers.js): the needle glides on the compositor, the words change five times a second.
  // "Trở mặt" / "Gắp ra" hold it where it stood when the finger came down (tapStop).
  meters(root,x){
    root.querySelectorAll('[data-ct-from]').forEach(el=>{
      const from=Number(el.dataset.ctFrom),max=Number(el.dataset.max)||30,s=Math.max(0,x.now()-from),[lo,hi]=SIDE(x);
      x.slide(el.querySelector('.ct-needle'),s/max*100,100/max);
      const l=el.querySelector('.ct-gauge-label'),text=`${s.toFixed(1)} giây · ${sideWord(x,s)}`;
      if(l&&l.textContent!==text)l.textContent=text;
      el.classList.toggle('ready',s>=lo&&s<=hi);el.classList.toggle('over',s>BURN(x));
    });
  },
  tapStop:op=>op==='com_flip'||op==='com_lift',
  summary(data,x){
    if(!data||data.plates==null)return '';
    const tm=data.tomorrow,D=k=>DISH(x,k);
    // "Ngày mai" first: what was thrown out at closing, what runs low, then one way to Kho.
    const lines=[(data.dumped||[]).length||data.rice_left?`🗑️ Bỏ cuối ngày: ${(data.dumped||[]).map(r=>`<b>${r.n}</b> phần ${x.esc(D(r.id).short)}`).concat(data.rice_left?[`<b>${data.rice_left}</b> vá cơm`]:[]).join(' · ')}: mai bày khay vừa đủ`:'',
      (data.low||[]).length?`📦 Sắp hết: ${data.low.slice(0,4).map(r=>`${x.esc(r.name)} <b>${r.n}</b>`).join(' · ')}${data.low.length>4?` · +${data.low.length-4}`:''}`:'',
      data.raw?`🍖 ${data.raw} lần sườn chưa chín tới tay khách: mỗi mặt đủ ${SIDE(x)[0]} giây`:''].filter(Boolean);
    const plan=`<section class="ct-plan" aria-label="Ngày mai"><h4 class="section-title">🌅 Ngày mai</h4>${tm?`<p class="ct-tomorrow"><span aria-hidden="true">${x.esc(tm.emoji)}</span> <b>Mai: ${x.esc(tm.label)}</b><small>${x.esc(tm.hint)}</small></p>`:''}${lines.length?`<ul class="ct-plan-list">${lines.map(l=>`<li>${l}</li>`).join('')}</ul>`:''}${x.button('🧺 Mở Kho','warehouse',{},'primary small ct-plan-go')}</section>`;
    const row=(l,v)=>`<div class="kv-row"><span>${l}</span><b>${v}</b></div>`;
    const kv=`<div class="kv">${row('Dĩa, hộp đã bán',data.plates)}${row('Khách',data.customers)}${data.over?row('Vá cơm xới dư',data.over):''}${data.waste?row('Đồ bỏ cuối ngày',`${data.waste} xu`):''}</div>`;
    return `<article class="card space-top ct-sum">${plan}<details class="ct-sum-more"><summary>🍚 Quán cơm hôm nay · ${data.plates} dĩa</summary>${kv}</details></article>`;
  },
  actions:{...tillActions,...kitActions},
  dock:[['inventory','box','Kho quán cơm','Nhập gạo, sườn, trứng, đồ kho, hộp…']],
};
