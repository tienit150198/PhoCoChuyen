/** Tổ thu gom phường Mây — the evening rubbish round (server: game/careers/garbage.py).
 * The start of the shift (gear, the cart), a lane of houses with their bags (what shows from outside,
 * open the odd ones, pull hazards into the red box, wrap broken glass, the right compartment, a kind
 * reminder), the three-compartment cart and the collection point, and residents' complaints.
 * The awkward people (0.9.16): hidden razors and needles, heaps dumped at the lane's end, residents who
 * will not sort (refuse the bag: your call), vandals and an overflowing point at night, and the monthly
 * fee: you name the amount and the tone, each household decides.
 * The server decides everything; one tap sends one command. */
import {stepRows,nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {data,cc,lower,stockOf,tile,meter,pane,introCard,deskCard,dayBar,person,askCard,bottom,kitActions,amountBox,kitInput,choiceCard,troubleLast} from './street_kit.js';

const W=(x,k)=>(cc(x).waste||{})[k]||{name:k,emoji:'🗑️',bin:'con_lai',sharp:false};
const BINS=['huu_co','tai_che','con_lai'];
const binName=(x,b)=>(cc(x).bin_label||{})[b]||b;
const binEmoji=(x,b)=>(cc(x).bin_emoji||{})[b]||'•';
const hm=m=>`${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`;
const NEAT=['Túi buộc gọn, đúng màu.','Túi cột chặt, khô ráo.','Túi nhẹ, buộc kỹ.'];
const odd=b=>!NEAT.includes(b.clue);
const stopsOf=t=>t.needs?.stops||[];
const allBags=t=>stopsOf(t).flatMap((s,si)=>s.bags.map(b=>({...b,si})));
const hazardsLeft=b=>(b.items||[]).filter(i=>['pin','bong_den','binh_xit','kim_tiem','dao_lam'].includes(i)&&!(b.pulled||[]).includes(i));
const misSorted=(x,b)=>b.items&&b.items.some(i=>W(x,i).bin!==({xanh:'huu_co',vang:'tai_che',den:'con_lai'})[b.color]);

/* ------------------------------------------------------------ the cart */
function cartCard(x,compact=false){
  const d=data(x),cap=d.cap||cc(x).cart||{},cart=d.cart||{};
  const cells=BINS.map(b=>{const n=cart[b]?.n||0,m=cap[b]||8;return `<div class="rc-bin rc-${b}"><span>${binEmoji(x,b)} ${x.esc(binName(x,b))}</span>${meter(n,m,n>=m?'bad':n>=m-2?'warn':'')}<small>${n}/${m}</small></div>`;}).join('');
  const haz=(d.haz||[]).length,full=BINS.some(b=>(cart[b]?.n||0)>=(cap[b]||8));
  const load=BINS.reduce((s,b)=>s+(cart[b]?.n||0),0)+haz;
  const dump=d.shift&&load?x.cmd(`🚛 Ra điểm tập kết đổ xe${full?' (ngăn đầy)':''}`,'rac_dump',{},full?'primary':'ghost small'):'';
  return `<section class="card rc-cart ${compact?'compact':''}" aria-label="Xe đẩy"><div class="rc-cart-head"><h4>🛒 Xe đẩy</h4><span class="rc-haz">🔴 ${haz}/${d.haz_max||8}</span></div><div class="rc-bins">${cells}</div>${dump}</section>`;
}

/* ------------------------------------------------------------ the lane */
function laneStrip(t,x){
  const at=t.at||0,started=t.stage!=='prep';
  const houses=stopsOf(t).map((s,i)=>{const n=s.bags.length,done=s.bags.filter(b=>b.loaded||b.refused).length;
    return `<li class="${i===at&&started?'here':''} ${done===n?'done':''}"><span class="rc-house" aria-hidden="true">${done===n?'✅':'🏠'}</span><small>${x.esc(s.house)}</small><b>${done}/${n}</b>${i===at&&started?'<i class="rc-me" aria-hidden="true">🛒</i>':''}</li>`;}).join('');
  const n=t.needs||{};
  return `<section class="rc-lane" aria-label="Ngõ"><div class="rc-lane-head"><b>${x.esc(n.name||'')}</b><span class="tag ${t.late?'danger':'green'}">⏰ tới ${hm(n.until||0)}</span></div><ol class="rc-houses">${houses}</ol></section>`;
}
function bagCard(t,x,b){
  const colour={xanh:'Túi xanh',vang:'Túi vàng',den:'Túi đen'}[b.color];
  if(b.refused)return `<div class="rc-bag rc-${b.color} loaded"><span class="rc-sack" aria-hidden="true"></span><div class="grow"><b>${colour}</b><small>🏷️ dán phiếu, chưa thu</small></div></div>`;
  if(b.loaded)return `<div class="rc-bag rc-${b.color} loaded"><span class="rc-sack" aria-hidden="true"></span><div class="grow"><b>${colour}</b><small>${binEmoji(x,b.loaded)} đã vào ngăn ${x.esc(lower(binName(x,b.loaded)))}</small></div></div>`;
  const items=b.open?`<ul class="rc-items">${(b.items||[]).map(i=>{const w=W(x,i),haz=w.bin==='nguy_hai',out=(b.pulled||[]).includes(i);
    return `<li class="${haz?'haz':''} ${out?'out':''}"><span aria-hidden="true">${x.esc(w.emoji)}</span>${x.esc(w.name)}${haz&&!out?x.cmd('🔴 Tách ra','rac_pull',{task:t.id,bag:b.id,item:i},'small danger'):out?' <small>✓ hộp đỏ</small>':''}${i==='kinh_vo'?(b.wrapped?' <small>✓ đã bọc</small>':x.cmd('🧷 Bọc','rac_wrap',{task:t.id,bag:b.id},'small')):''}</li>`;}).join('')}</ul>`
    :`<p class="rc-clue">${x.esc(b.clue)}</p>`;
  const bins=BINS.map(k=>x.cmd(`${binEmoji(x,k)} ${x.esc(binName(x,k))}`,'rac_load',{task:t.id,bag:b.id,bin:k},`rc-to rc-${k}`)).join('');
  return `<div class="rc-bag rc-${b.color}" data-bag="${x.esc(b.id)}"><div class="rc-bag-head"><span class="rc-sack" aria-hidden="true"></span><div class="grow"><b>${colour}</b>${b.open?'':`<small>${odd(b)?'⚠️ trông lạ':'trông bình thường'}</small>`}</div>${b.open?'':x.cmd('👀 Mở túi','rac_peek',{task:t.id,bag:b.id},'small rc-peek')}</div>
    ${items}<div class="rc-tos">${bins}</div>${b.open&&misSorted(x,b)?x.cmd('🏷️ Chưa phân loại: dán phiếu, không thu','rac_refuse',{task:t.id,bag:b.id},'small ghost rc-refuse'):''}</div>`;
}
function stopPanel(t,x){
  const si=t.at||0,s=stopsOf(t)[si];if(!s)return '';
  const noted=(t.noted||[]).includes(si),messy=s.bags.some(b=>b.open&&misSorted(x,b));
  const note=noted?'<span class="tag green">📝 Đã nhắc nhà này</span>':x.cmd('📝 Nhắc nhà này phân loại','rac_note',{task:t.id,stop:si},messy?'':'ghost small');
  return `<section class="card rc-stop"><h4>🏠 ${x.esc(s.house)}</h4>${s.bags.map(b=>bagCard(t,x,b)).join('')}<div class="rc-note">${note}</div></section>`;
}
function ticket(t,x){
  if(!t.known)return askCard(x,t,t.kind==='complaint'?'👂 Nghe cư dân kể':'👂 Nghe chị Hạnh dặn');
  return person(x,t,t.kind==='complaint'?`<p class="small muted">“${x.esc(t.opening)}”</p>`:'');
}
function casePanel(t,x){
  const k=t.case||{facts:[],options:[]},read=new Set(t.read||[]);
  const facts=k.facts.map(f=>`<li>${f.text?`<b>${x.esc(f.title)}</b><span>${x.esc(f.text)}</span>`:x.cmd(`🔍 ${x.esc(f.title)}`,'rac_read',{task:t.id,fact:f.id},'small ghost')}</li>`).join('');
  const opts=k.options.map(o=>{const miss=o.requires.filter(r=>!read.has(r));const title=miss.map(r=>k.facts.find(f=>f.id===r)?.title||r).join(', ');
    return x.cmd(`<span class="sk-opt-label">${x.esc(o.label)}</span>${miss.length?`<small>cần xem: ${x.esc(lower(title))}</small>`:''}`,'rac_reply',{task:t.id,option:o.id},'sk-opt',miss.length>0);}).join('');
  return `<section class="card rc-case"><h4>🔍 Tìm hiểu</h4><ul class="rc-facts">${facts}</ul><h4 class="section-title">💬 Trả lời</h4><div class="sk-opts">${opts}</div></section>`;
}

/* ------------------------------------------------------------ set-up */
function setupPanel(t,x){
  const d=data(x),n=t.needs||{},gear=cc(x).gear||{},used=cc(x).used||[];
  const tiles=Object.entries(gear).map(([k,label])=>{const on=(d.gear||[]).includes(k),q=used.includes(k)?stockOf(x,k):null;
    return tile(x,'rac_gear',{item:k},`<span class="tile-emoji">${{gang_tay:'🧤',khau_trang:'😷',ao:'🦺',ung:'🥾'}[k]||'•'}</span><b>${x.esc(label)}</b><small>${on?'✓ đã mặc':q!==null?`còn ${q}`:'mặc vào'}</small>`,`${on?'selected':''} ${(n.gear||[]).includes(k)?'want':''}`,q===0&&!on);}).join('');
  return `<section class="card rc-setup"><h4>🦺 Đồ bảo hộ</h4><div class="tile-grid rc-gear">${tiles}</div>
    <div class="rc-row">${d.cart_ok?'<span class="tag green">✓ Xe đã kiểm</span>':x.cmd('🛒 Kiểm xe đẩy','rac_cart',{},'')}</div><p class="small muted">${x.esc(n.note||'')}</p></section>`;
}
function setupSteps(t,x){
  const d=data(x),n=t.needs||{},gear=cc(x).gear||{},rows=[];
  for(const k of n.gear||[]){const on=(d.gear||[]).includes(k),out=(cc(x).used||[]).includes(k)&&!stockOf(x,k);
    rows.push({ok:on?true:null,label:gear[k]||k,note:out&&!on?'hết trong kho':'',go:on?null:out?{act:'inventory',label:`📦 Hết ${x.esc(lower(gear[k]||k))}: mở kho`}:{cmd:'rac_gear',payload:{item:k},label:`${{gang_tay:'🧤',khau_trang:'😷',ao:'🦺',ung:'🥾'}[k]||''} ${x.esc(gear[k]||k)}`}});}
  rows.push({ok:d.cart_ok?true:null,label:'Kiểm xe đẩy',go:{cmd:'rac_cart',payload:{},label:'🛒 Kiểm xe đẩy'}});
  return rows;
}

/* ------------------------------------------------------------ the guide */
function roundSteps(t,x){
  const d=data(x),rows=[],si=t.at||0,s=stopsOf(t)[si],cap=d.cap||{},cart=d.cart||{};
  if(!d.shift)return [{ok:null,label:'Vào ca trước đã',go:null}];
  if(t.stage==='prep')return [{ok:null,label:'Đẩy xe vào ngõ',go:{cmd:'rac_go',payload:{task:t.id},label:'🛒 Đẩy xe vào ngõ'}}];
  if(t.late&&!t.swept)rows.push({ok:null,label:'Quét rác bị bới tung',go:{cmd:'rac_sweep',payload:{task:t.id},label:'🧹 Quét dọn'}});
  for(const b of s?.bags||[]){
    if(b.refused){rows.push({ok:true,label:'Túi dán phiếu, chưa thu'});continue;}
    if(b.loaded){rows.push({ok:true,label:`${{xanh:'Túi xanh',vang:'Túi vàng',den:'Túi đen'}[b.color]} → ${lower(binName(x,b.loaded))}`});continue;}
    if(!b.open&&odd(b)){rows.push({ok:null,label:'Túi trông lạ: mở ra xem',note:b.clue,go:{cmd:'rac_peek',payload:{task:t.id,bag:b.id},label:'👀 Mở túi trông lạ'}});continue;}
    const h=hazardsLeft(b)[0];
    if(h){rows.push({ok:null,label:`Tách ${lower(W(x,h).name)} ra hộp đỏ`,go:{cmd:'rac_pull',payload:{task:t.id,bag:b.id,item:h},label:`🔴 Tách ${x.esc(lower(W(x,h).name))}`}});continue;}
    if(b.open&&(b.items||[]).includes('kinh_vo')&&!b.wrapped){rows.push({ok:null,label:'Bọc mảnh kính vỡ',go:{cmd:'rac_wrap',payload:{task:t.id,bag:b.id},label:'🧷 Bọc mảnh kính'}});continue;}
    const full=BINS.filter(k=>(cart[k]?.n||0)>=(cap[k]||8));
    if(full.length)rows.push({ok:null,label:`Ngăn ${full.map(k=>lower(binName(x,k))).join(', ')} đầy`,go:{cmd:'rac_dump',payload:{},label:'🚛 Ra điểm tập kết đổ xe'}});
    rows.push({ok:null,label:'Bỏ túi vào đúng ngăn',go:{sel:`[data-bag="${b.id}"] .rc-tos`,label:'👉 Chọn ngăn cho túi'},pulse:''});
  }
  if(s&&s.bags.some(b=>b.open&&misSorted(x,b))&&!(t.noted||[]).includes(si))rows.push({ok:null,label:'Nhắc nhà này phân loại',go:{cmd:'rac_note',payload:{task:t.id,stop:si},label:'📝 Nhắc nhà này phân loại'}});
  if(s&&s.bags.every(b=>b.loaded||b.refused)&&si<stopsOf(t).length-1)rows.push({ok:null,label:'Tới nhà sau',go:{cmd:'rac_next',payload:{task:t.id},label:`🛒 Tới ${x.esc(stopsOf(t)[si+1].house)}`}});
  return rows;
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện giữa đường',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(d.trouble?.ev)return {steps:[{ok:null,label:'Có chuyện ở ngõ',go:{sel:'.sk-trouble',label:'👉 Xử lý ngay'},pulse:''}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'rac_intro',payload:{},label:'🛒 Vào việc thôi!'}}],final:null};
  if(t.twist?.state==='on')return {steps:[{ok:null,label:'Có chuyện ở ngõ',go:{sel:'.sk-twist',label:'👉 Xử lý ngay'},pulse:''}],final:null};
  if(t.kind==='setup'){const steps=setupSteps(t,x);return {steps,final:{label:'🦺 VÀO CA',go:finalGo(steps,'rac_open',{task:t.id}),ready:true}};}
  if(!t.known)return {steps:[{ok:null,label:'Nghe dặn',go:{cmd:'ask',payload:{task:t.id},label:t.kind==='complaint'?'👂 Nghe cư dân kể':'👂 Nghe chị Hạnh dặn'}}],final:null,pulse:'.sk-ask'};
  if(t.kind==='complaint'){
    const k=t.case||{facts:[]},f=k.facts.find(ff=>!ff.text);
    return {steps:[{ok:f?null:true,label:'Tìm hiểu cho rõ',go:f?{cmd:'rac_read',payload:{task:t.id,fact:f.id},label:`🔍 ${x.esc(f.title)}`}:null},{ok:null,label:'Trả lời cư dân',go:{sel:'.rc-case .sk-opts',label:'💬 Chọn cách trả lời'},pulse:''}],final:null};
  }
  const steps=roundSteps(t,x),last=(t.at||0)===stopsOf(t).length-1;
  return {steps,final:t.stage==='round'&&last?{label:'✅ XONG NGÕ',go:finalGo(steps,'rac_finish',{task:t.id}),ready:true}:null};
}
function twistCard(t,x){
  const tw=t.twist;if(!tw||tw.state!=='on')return '';
  const o=(cmd,choice,label,sub)=>({cmd,payload:{task:t.id,choice},label,sub});
  if(tw.kind==='sharp'){const w=W(x,tw.item);
    return choiceCard(x,'rc-hurt','🩸',`Bị ${lower(w.name)} đâm`,'Túi trông bình thường mà có đồ sắc giấu bên trong.',[
      o('rac_hurt','clean','🩹 Tự rửa, sát trùng, băng lại','nhanh, đỡ tốn'),o('rac_hurt','clinic','🏥 Ra trạm y tế','8 xu, khách chờ'),o('rac_hurt','ignore','😬 Kệ, làm tiếp','dễ nhiễm trùng')]);}
  if(tw.kind==='pile')return choiceCard(x,'rc-pile','🗑️',`Đống rác đổ trộm · khoảng ${tw.bags} bao`,tw.line,[
    o('rac_pile','trips','🛒🛒 Đi hai chuyến','mỏi, ngõ sau chờ'),o('rac_pile','truck','🛻 Gọi xe ba gác','10 xu'),o('rac_pile','report','📸 Chụp ảnh báo phường','để lại qua đêm'),o('rac_pile','cram','🧱 Nhồi chặt cho hết','dễ bung xe')]);
  if(tw.kind==='grump')return choiceCard(x,'rc-grump','😤','Chủ nhà ra chặn xe',tw.line,[
    o('rac_grump','explain','🗣️ Giải thích nhẹ nhàng','hên xui'),o('rac_grump','refuse','🏷️ Dán phiếu, không thu túi chưa phân loại','đúng quy định, dễ bị chửi'),
    o('rac_grump','take','🤷 Lấy luôn cho xong',''),o('rac_grump','report','📞 Gọi bác Tâm tổ trưởng','mất thời gian')]);
  return '';
}
function troubleCard(x){
  const tb=data(x).trouble||{},ev=tb.ev;if(!ev)return '';
  const o=(choice,label,sub)=>({cmd:'rac_trouble',payload:{choice},label,sub});
  if(ev.kind==='vandal')return choiceCard(x,'sk-trouble','🛵','Quậy phá lúc nửa đêm',tb.text||'',[
    o('talk','🗣️ Nói chuyện đàng hoàng','hên xui'),o('photo','📸 Chụp ảnh làm bằng chứng',''),o('police','🚓 Gọi công an phường','mất thời gian'),o('ignore','🤐 Lờ đi','')]);
  return choiceCard(x,'sk-trouble','🚛','Điểm tập kết tràn',tb.text||'',[
    o('wait','⏳ Đứng đợi xe ép','lâu'),o('tidy','🧹 Xếp gọn, quét, rắc vôi',''),o('call','📞 Gọi chú Sáu','hên xui'),o('leave','🚶 Bỏ về','')]);
}
function feeBook(x){
  const f=data(x).fees;if(!f||!(f.rows||[]).length)return '';
  const open=f.rows.filter(r=>r.state==='open'),pick=x.ui.feeRow;
  const rows=f.rows.map(r=>{const left=r.due-r.paid,today=r.on===x.room.day,st={paid:'✅ đã đóng',refused:'🚪 không đóng',waived:'🤝 miễn'}[r.state];
    const head=`<div class="row spread"><b>${x.esc(r.house)}</b><span class="tag ${r.state==='open'?'amber':'green'}">${st||`${x.fmt(left)} xu`}</span></div>`;
    if(r.state!=='open')return `<li class="rc-fee ${r.state}">${head}${r.last?`<small class="muted">${x.esc(r.last)}</small>`:''}</li>`;
    const said=r.last?`<p class="small">${x.esc(r.last)}</p>`:'';
    if(today)return `<li class="rc-fee">${head}${said}${r.counter?`<div class="sk-row">${x.cmd(`🤝 Chốt ${x.fmt(r.counter)} xu`,'rac_fee',{row:r.id,tone:'soft',amount:r.counter},'small')}</div>`:'<small class="muted">Hôm nay gõ cửa rồi, mai thu tiếp.</small>'}</li>`;
    if(pick!==r.id)return `<li class="rc-fee">${head}<div class="row spread"><small class="muted">${x.esc(r.lane)}</small><button type="button" class="btn small" data-action="car:feeRow" data-row="${x.esc(r.id)}">🧾 Gõ cửa thu</button></div>${said}</li>`;
    return `<li class="rc-fee on">${head}<small class="muted">${x.esc(r.lane)}</small>${said}${amountBox(x,`fee-${r.id}`,left,{max:left,label:'Thu bao nhiêu',send:'🧾 Thu, nói nhẹ',cmd:'rac_fee',payload:{row:r.id,tone:'soft'},field:'amount'})}
      <div class="sk-row">${act2(x,'📜 Nhắc quy định',{row:r.id,tone:'strict',key:`fee-${r.id}`,def:left})}${x.confirmCmd('🤝 Miễn tháng này','rac_fee',{row:r.id,waive:true},`Miễn phí cho ${r.house}?`,'small ghost')}</div></li>`;}).join('');
  return pane(x,'fees',`🧾 Thu phí vệ sinh · còn ${open.length} hộ`,`<ul class="sk-debts">${rows}</ul>`,open.length>0,'rc-fees');
}
const act2=(x,label,d)=>`<button type="button" class="btn small" data-action="car:feeStrict"${Object.entries(d).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}>${label}</button>`;
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});

export default {
  id:'garbage',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='setup'?'Đồ bảo hộ, kiểm xe':t.kind==='complaint'?'Nghe cư dân phản ánh':'Gom rác từng nhà';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    const top=`${introCard(x,'rac_intro','🛒')}${deskCard(x,'rac_desk','Chuyện giữa đường')}${troubleCard(x)}${troubleLast(x)}`;
    if(d.desk?.ev||d.trouble?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk rc">${hint}${top}${bottom(x,g)}</div>`;
    let main='',side='';
    if(t.twist?.state==='on')return `<div class="career-job sk rc">${hint}${top}${ticket(t,x)}${twistCard(t,x)}${bottom(x,g)}</div>`;
    const clock=d.clock!=null?` · ${hm(d.clock)}`:'';
    if(t.kind==='setup'){main=setupPanel(t,x);side=stepRows(x,g.steps,'Vào ca');}
    else if(!t.known)main='';
    else if(t.kind==='complaint')main=casePanel(t,x);
    else{main=laneStrip(t,x)+(t.stage==='round'?stopPanel(t,x):'')+cartCard(x,true);side=t.stage==='round'?stepRows(x,g.steps,'Việc ở nhà này'):'';}
    const head=t.kind==='setup'?dayBar(x,clock):`${ticket(t,x)}${dayBar(x,clock)}`;
    return `<div class="career-job sk rc">${hint}${top}${head}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x),top=`${introCard(x,'rac_intro','🛒')}${deskCard(x,'rac_desk','Chuyện giữa đường')}${troubleCard(x)}${troubleLast(x)}`;
    if(d.trouble?.ev){const g={steps:[{ok:null,label:'Có chuyện ở ngõ',go:{sel:'.sk-trouble',label:'👉 Xử lý ngay'},pulse:''}],final:null};return `<div class="career-job sk rc">${hintFor(g,x)}${top}${bottom(x,g)}</div>`;}
    if(d.desk?.ev||!d.intro||x.ui.intro){const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện giữa đường',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'rac_intro',payload:{},label:'🛒 Vào việc thôi!'}}],final:null};
      return `<div class="career-job sk rc">${hintFor(g,x)}${top}${bottom(x,g)}</div>`;}
    return `<div class="career-job sk rc">${top}${dayBar(x,d.clock!=null?` · ${hm(d.clock)}`:'')}${cartCard(x)}${d.shift?feeBook(x):''}</div>`;
  },
  input(el,x){return kitInput(el,x);},
  tick(root){keepBarAboveFooter(root);},
  actions:{...kitActions,
    async feeRow(d,el,x){x.ui.feeRow=x.ui.feeRow===d.row?null:d.row;x.render();},
    async feeStrict(d,el,x){const b=x.ui.amt??={},v=Number(b[d.key]===undefined||b[d.key]===''?d.def:b[d.key]);
      await x.send('rac_fee',{row:d.row,tone:'strict',amount:Math.max(1,Math.min(Number(d.def),Math.floor(v)||Number(d.def)))});}},
  dock:[['inventory','box','Kho đồ bảo hộ','Găng tay, khẩu trang, bao']],
};
