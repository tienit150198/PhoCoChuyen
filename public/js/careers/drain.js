/** Thông cống chú Hai — drain and sewer cleaning callouts (server: game/careers/drain.py).
 * The morning packing (the appointment book, five tools on the bike), a callout: find the cause by
 * asking, looking, running water or the camera, quote from the price list before touching anything,
 * the right tool (or a stopgap), the manhole safety drill, test, clean up, advice and the cash.
 * The awkward people (0.9.16): a price you name yourself (the customer decides), the homeowner grumbling
 * over your shoulder, the "while you're here" extra job, no cash (deposit or trust), the debt book, and
 * customers coming back for the difference after a chặt chém.
 * The server decides everything; one tap sends one command. */
import {stepRows,nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {planBox,stockLines,figures} from './plan_kit.js';
import {cashPanel,changeStep,changePayload,tillActions} from './till.js';
import {data,cc,lower,tile,pane,introCard,deskCard,dayBar,person,askCard,bottom,kitActions,amountBox,kitInput,choiceCard,debtBook,troubleLast,tip,clean,headChip} from './street_kit.js';

const toolOf=(x,k)=>(cc(x).tools||[]).find(t=>t.id===k)||{id:k,name:k,emoji:'🔧',note:''};
const placeOf=(x,k)=>(cc(x).places||{})[k]||{name:k,emoji:'🕳️',price:0};
const causeName=(x,k)=>((cc(x).causes||{})[k]||{}).name||k;
const JOBS=['call','manhole','emergency','recall'];
const GEAR_EMOJI={gang_tay:'🧤',khau_trang:'😷',ung:'🥾',kinh:'🥽'};
const HOW_EMOJI={hoi:'👂',nhin:'🔦',xa:'💧',camera:'📹'};

/* ------------------------------------------------------------ the bike and the gear */
function bikeCard(x,compact=false){
  const d=data(x),bike=d.bike||[],slots=d.slots||5;
  const on=bike.map(k=>{const t=toolOf(x,k);return `<span class="cg-slot on" title="${x.esc(t.name)}"><span aria-hidden="true">${x.esc(t.emoji)}</span><small>${x.esc(t.name)}</small></span>`;}).join('');
  const empty=Array.from({length:Math.max(0,slots-bike.length)},()=>'<span class="cg-slot" aria-hidden="true"></span>').join('');
  const gear=Object.entries(cc(x).gear||{}).map(([k,l])=>`<span class="cg-gear ${(d.gear||[]).includes(k)?'on':''}" title="${x.esc(l)}">${GEAR_EMOJI[k]||'•'}</span>`).join('');
  return `<section class="card cg-bike ${compact?'compact':''}"><div class="cg-bike-head"><h4>🛵 Trên xe ${bike.length}/${slots}</h4><span class="cg-gears" aria-label="Đồ bảo hộ">${gear}</span></div><div class="cg-slots">${on}${empty}</div></section>`;
}
function gearRow(x){
  const d=data(x);
  // Clean layout: the icon alone (the name is its label for readers and its tooltip).
  return `<div class="cg-gear-row">${Object.entries(cc(x).gear||{}).map(([k,l])=>x.cmd(clean()?`${GEAR_EMOJI[k]||''}`:`${GEAR_EMOJI[k]||''} ${x.esc(l)}`,'cg_gear',{item:k},(d.gear||[]).includes(k)?'small cg-on':'small ghost').replace('<button ',`<button aria-label="${x.esc(l)}" title="${x.esc(l)}" `)).join('')}</div>`;
}

/* ------------------------------------------------------------ packing in the morning */
/** A tool's name in a word or two on the clean layout (the full name is the tile's label for readers). */
const SHORT={pit_tong:'Pít-tông',lo_xo:'Dây 5m',may_lo_xo:'Máy 15m',may_phun:'Phun áp',camera:'Camera',moc:'Móc',gau:'Gầu bùn',do_khi:'Đo khí'};
/** An appointment as one line: the place's icon and the job without the place's own words ("🚿 tiệm tóc"); the
 * place and the client are its label, the whole book opens from the "📒" chip. */
function bookLine(x,b){
  const p=placeOf(x,b.place),lead=String(p.name||'').split(/\s+/).slice(0,2).join(' ').toLowerCase(),txt=String(b.text||'');
  const rest=txt.toLowerCase().startsWith(lead)&&lead?txt.slice(lead.length).trim():txt;
  return `<li title="${x.esc(`${b.who} · ${p.name} · ${txt}`)}" aria-label="${x.esc(`${b.who}: ${txt}`)}"><span aria-hidden="true">${x.esc(p.emoji)}</span> ${x.esc(rest||txt)}</li>`;
}
const shortOf=tl=>clean()&&SHORT[tl.id]||tl.name;
function setupPanel(t,x){
  const d=data(x),n=t.needs||{},bike=d.bike||[],slots=d.slots||5;
  const book=(n.book||[]).map(b=>{const p=placeOf(x,b.place);return `<li><span aria-hidden="true">${x.esc(p.emoji)}</span><div><b>${x.esc(b.who)}</b><small>${x.esc(p.name)} · ${x.esc(b.text)}</small></div></li>`;}).join('');
  const tools=(cc(x).tools||[]).map(tl=>{const on=bike.includes(tl.id);
    return tile(x,'cg_pack',{tool:tl.id},`<span class="tile-emoji">${x.esc(tl.emoji)}</span><b title="${x.esc(tl.name)}">${x.esc(shortOf(tl))}</b>${tip(x.esc(tl.note),tl.name)}`,on?'selected':'',!on&&bike.length>=slots).replace('<button ',`<button aria-label="${x.esc(tl.name)}" `);}).join('');
  // Clean layout: the appointment book is a header chip ("📒 3 hẹn"), its card opens over the bench.
  const lines=clean()?`<ul class="cg-booklines" aria-label="Sổ hẹn hôm nay">${(n.book||[]).map(b=>bookLine(x,b)).join('')}</ul>`:'';
  return `${headChip('📒',`${(n.book||[]).length} hẹn`,'.cg-book',{label:'Sổ hẹn hôm nay',flow:true})}${lines}<section class="card cg-book ui-chipped"><h4>📒 Sổ hẹn hôm nay</h4><ul class="cg-booklist">${book}</ul>${tip(x.esc(n.note||''),'','p')}</section>
    <section class="card cg-pack"><h4>🧰${clean()?'':' Xếp lên xe'} <small class="muted">${bike.length}/${slots}</small></h4><div class="tile-grid cg-tools">${tools}</div>
    <h4 class="section-title">🦺${clean()?'':' Đồ bảo hộ'}</h4>${gearRow(x)}</section>`;
}
// What chú Hai would load for each kind of place in the book (a first guess: the clue on site decides).
const PLACE_TOOLS={bon_rua:['may_phun','lo_xo'],lavabo:['lo_xo'],thoat_san:['lo_xo'],bon_cau:['pit_tong','may_lo_xo'],ong_chinh:['may_lo_xo','camera'],ho_ga:['gau','do_khi'],mai:['moc']};
function packPlan(t,x){
  const want=[...new Set([...(t.needs?.book||[]).flatMap(b=>PLACE_TOOLS[b.place]||[]),'camera','moc','pit_tong'])];
  return want.slice(0,data(x).slots||5);
}
function setupSteps(t,x){
  const d=data(x),bike=d.bike||[],rows=[],plan=packPlan(t,x),next=plan.find(k=>!bike.includes(k));
  const full=bike.length>=(d.slots||5),tl=next&&toolOf(x,next);
  // Yesterday's tools are still on the bike: take off one today's book does not need, to make room.
  const spare=full&&next?bike.find(k=>!plan.includes(k)):null,sp=spare&&toolOf(x,spare);
  rows.push({ok:!next||(full&&!spare)?true:null,label:'Xếp đồ nghề theo sổ hẹn',note:`${bike.length}/${d.slots||5}`,
    go:next&&!full?{cmd:'cg_pack',payload:{tool:next},label:clean()?`${x.esc(tl.emoji)} Xếp ${x.esc(lower(shortOf(tl)))}`:`${x.esc(tl.emoji)} Xếp ${x.esc(lower(tl.name))} lên xe`}
      :spare?{cmd:'cg_pack',payload:{tool:spare},label:clean()?`${x.esc(sp.emoji)} Cất ${x.esc(lower(shortOf(sp)))}`:`${x.esc(sp.emoji)} Cất ${x.esc(lower(sp.name))} lại tiệm`}:null});
  rows.push({ok:(d.gear||[]).includes('gang_tay')?true:null,label:'Đeo găng tay',go:{cmd:'cg_gear',payload:{item:'gang_tay'},label:'🧤 Đeo găng tay'}});
  return rows;
}

/* ------------------------------------------------------------ a callout */
function ticket(t,x){
  if(!t.known)return askCard(x,t,'👂 Nghe khách kể');
  const n=t.needs||{},p=placeOf(x,n.place);
  const tag=t.kind==='manhole'?'<span class="tag amber">⚫ Hố ga · phường trả</span>':t.kind==='emergency'?'<span class="tag danger">🌙 Gọi đêm</span>':t.kind==='recall'?'<span class="tag blue">🔁 Gọi lại</span>':'';
  return person(x,t,`<p class="cg-place">${x.esc(p.emoji)} ${x.esc(p.name)}${n.old?' · <em>ống gang cũ</em>':''}</p><p class="muted small">“${x.esc(t.opening)}”</p>`,tag);
}
function pipe(t,x){
  // The pipe from the drain to the street: the blockage shows once it is found, the water once it flows.
  const c=t.cleared,known=t.camera||t.diag;
  return `<div class="cg-pipe ${c==='full'?'flow':c==='temp'?'slow':''}" aria-hidden="true"><span class="cg-drain">${x.esc(placeOf(x,t.needs?.place).emoji)}</span><span class="cg-tube"><i class="cg-water"></i>${c==='full'?'':`<b class="cg-clog">${known?'🟫':'❓'}</b>`}</span><span class="cg-out">🕳️</span></div>`;
}
function checkPanel(t,x){
  const n=t.needs||{},clues=n.clues||{},bike=data(x).bike||[];
  const rows=['hoi','nhin','xa','camera'].map(h=>{const text=h==='camera'?t.camera:clues[h],label=(cc(x).hows||{})[h]||h;
    if(text)return `<li class="seen"><span aria-hidden="true">${HOW_EMOJI[h]}</span><div><b>${x.esc(label)}</b><small>${x.esc(text)}</small></div></li>`;
    const dis=h==='camera'&&!bike.includes('camera');
    return `<li>${x.cmd(`${HOW_EMOJI[h]} ${x.esc(label)}${dis?' <small>(không mang theo)</small>':''}`,'cg_check',{task:t.id,how:h},'ghost cg-how',dis)}</li>`;}).join('');
  const causes=Object.entries(cc(x).causes||{}).map(([k,v])=>`<button type="button" class="cg-cause ${t.diag===k?'on':''}" data-command="cg_diag" data-payload="${x.esc(JSON.stringify({task:t.id,cause:k}))}"${t.checked?.length?'':' disabled'}>${x.esc(v.name)}</button>`).join('');
  const open=!t.diag||t.cleared==='fail';
  return `<section class="card cg-check"><h4>🔍 Tìm bệnh</h4>${pipe(t,x)}<ul class="cg-clues">${rows}</ul>
    ${pane(x,`cause-${t.id}-${t.diag||''}-${t.cleared||''}`,t.diag?`📝 Nghi: <b>${x.esc(causeName(x,t.diag))}</b>`:'📝 Ghi nguyên nhân',`<div class="cg-causes">${causes}</div>`,open,'cg-diag')}</section>`;
}
function quotePanel(t,x){
  const pr=t.prices||{},p=placeOf(x,t.needs?.place),night=t.kind==='emergency';
  const q=(lv,label,sub)=>x.cmd(`<span class="sk-opt-label">${label} · ${x.fmt(pr[lv]||0)} xu</span><small>${sub}</small>`,'cg_quote',{task:t.id,level:lv},`sk-opt cg-q-${lv}`);
  const rows=[q('list','🧾 Theo bảng giá',night?'đã gồm phụ phí gọi đêm, nói rõ trước':`${p.name} · ${causeName(x,t.diag)}`),q('high','💰 Nói thách','gấp gần đôi bảng giá'),q('low','🙂 Làm rẻ lấy lòng','tiệm chịu lỗ')];
  if(t.kind==='recall')rows.push(q('warranty','🔁 Bảo hành, không lấy tiền','khi lỗi là của tiệm'));
  const open=t.quote==null||t.cleared==='fail'||(t.quoted_for&&t.quoted_for!==t.diag),ctr=t.bid?.counter;
  const own=open?pane(x,`own-${t.id}`,'✍️ Tự báo giá',`${ctr?`<p class="cg-counter">🗣️ Khách trả <b>${x.fmt(ctr)} xu</b>${x.cmd(`Chốt ${x.fmt(ctr)} xu`,'cg_price',{task:t.id,price:ctr},'small primary')}</p>`:''}
    ${amountBox(x,`price-${t.id}`,ctr||pr.list||10,{min:0,max:500,label:'Giá bạn báo',send:'🧾 Báo giá này',cmd:'cg_price',payload:{task:t.id}})}<p class="small muted">Báo cao thì có người trả, có người cãi, có người đi rêu rao khắp ngõ.</p>`,!!ctr,'cg-own'):'';
  return `<section class="card cg-quote"><h4>🧾 ${t.quote!=null?`Đã báo ${x.fmt(t.quote)} xu`:'Báo giá trước khi làm'}</h4>${open?`<div class="sk-opts">${rows.join('')}</div>${own}`:''}</section>`;
}
function safetyPanel(t,x){
  if(t.kind!=='manhole')return '';
  const done=new Set(t.safety||[]),lab=cc(x).safety||{};
  const rows=['rao','khi','quat','canh'].map(k=>`<li class="${done.has(k)?'ok':''}">${done.has(k)?`<span>✓</span>${x.esc(lab[k]||k)}`:x.cmd(x.esc(lab[k]||k),'cg_safety',{task:t.id,step:k},'ghost small cg-safe')}</li>`).join('');
  return `<section class="card cg-safety"><h4>⚠️ An toàn hố ga</h4><ol class="cg-safelist">${rows}</ol></section>`;
}
function workPanel(t,x){
  const bike=data(x).bike||[],all=cc(x).tools||[];
  const use=all.filter(tl=>!['camera','do_khi'].includes(tl.id)).map(tl=>{const on=bike.includes(tl.id),used=(t.tools||[]).includes(tl.id);
    return tile(x,'cg_work',{task:t.id,tool:tl.id},`<span class="tile-emoji">${x.esc(tl.emoji)}</span><b>${x.esc(tl.name)}</b><small>${on?(used?'đã thử':'trên xe'):'để ở tiệm'}</small>`,`${used?'used':''} ${on?'':'away'}`,!on);}).join('');
  const away=all.filter(tl=>!bike.includes(tl.id)).map(tl=>x.cmd(`${x.esc(tl.emoji)} ${x.esc(tl.name)}`,'cg_fetch',{tool:tl.id,drop:bike[0]},'small ghost')).join('');
  const extra=`<div class="cg-extra">${x.cmd('🔧 Thay ống xi-phông','cg_part',{task:t.id},'small',t.part)}${x.confirmCmd('🧪 Đổ bột thông cống','cg_chem',{task:t.id},'Đổ hóa chất xút vào ống? Cần găng tay, kính; ống cũ dễ hỏng.','small ghost')}</div>`;
  return `<section class="card cg-work"><h4>🧰 Thông</h4>${gearRow(x)}<div class="tile-grid cg-use">${use}</div>${extra}${away?pane(x,`fetch-${t.id}`,'🛵 Về tiệm lấy đồ nghề khác',`<p class="small muted">Khách phải chờ thêm. Xe đầy thì để lại món đầu tiên.</p><div class="cg-away">${away}</div>`,false,'cg-fetch'):''}</section>`;
}
function finishPanel(t,x){
  const b=(k,label,cmd,done)=>done?`<span class="tag green">✓ ${label}</span>`:x.cmd(label,cmd,{task:t.id},'');
  return `<section class="card cg-finish"><h4>${t.cleared==='full'?'✅ Đã thông':'🟡 Thông tạm'}</h4>${pipe(t,x)}
    <div class="cg-row">${b('test','💧 Xả nước thử','cg_test',t.tested)}${b('clean','🧽 Dọn sạch chỗ làm','cg_clean',t.cleaned)}${b('advise','🗣️ Dặn khách','cg_advise',t.advised)}</div></section>`;
}

/* ------------------------------------------------------------ the awkward people (0.9.16) */
function twistCard(t,x){
  const tw=t.twist;if(!tw||tw.state!=='on')return '';
  const o=(choice,label,sub,cmd,extra={})=>({cmd,payload:{task:t.id,choice,...extra},label,sub});
  if(tw.kind==='watch')return choiceCard(x,'cg-watch','🗯️','Chủ nhà đứng sau lưng lèm bèm',tw.line,[
    o('bear','😮‍💨 Nhịn, làm tiếp','lèm bèm kệ lèm bèm','cg_watch'),o('answer','🗣️ Đáp lại cho ra lẽ','có người nghe, có người nổi khùng','cg_watch'),
    o('away','🙏 Mời ra ngoài chờ','cho mình tập trung','cg_watch'),o('refuse','🎒 Từ chối làm tiếp','không lấy đồng nào','cg_watch')]);
  if(tw.kind==='extra')return choiceCard(x,'cg-extra','🙏','Khách nhờ “tiện tay”',tw.line,[
    o('free','🤲 Làm luôn, không lấy tiền','khách vui','cg_extra'),o('refuse','🙅 Việc khác tính riêng','khách có thể dỗi','cg_extra')],
    `${tw.counter?`<p class="small">🗣️ Khách trả <b>${x.fmt(tw.counter)} xu</b></p>`:''}${amountBox(x,`extra-${t.id}`,tw.counter||cc(x).extra_fair||12,{label:'Hoặc báo giá việc phụ',send:'🧾 Báo giá việc phụ',cmd:'cg_extra',payload:{task:t.id,choice:'charge'}})}`);
  if(tw.kind==='nocash')return choiceCard(x,'cg-nocash','💸','Khách không có tiền mặt',tw.line,[
    o('wait','🏧 Đợi khách đi rút tiền','khách sốt ruột','cg_nocash'),o('trust','📒 Tin khách, ghi nợ','có người trả, có người quên luôn','cg_nocash')],
    amountBox(x,`dep-${t.id}`,Math.max(1,Math.floor((t.quote||10)/2)),{label:'Hoặc xin trả trước',send:'💵 Xin trả trước',cmd:'cg_nocash',payload:{task:t.id,choice:'deposit'},field:'amount'}));
  return '';
}
function troubleCard(x){
  const ev=data(x).trouble?.ev;if(!ev||ev.kind!=='comeback')return '';
  const f=ev.facts,o=(choice,label,sub)=>({cmd:'cg_trouble',payload:{choice},label,sub});
  return choiceCard(x,'sk-trouble','🔁',`${f.who} quay lại cùng ông Lộc`,`“Hỏi ra rẻ hơn ${f.extra} xu, trả lại tiền chênh đi!”`,[
    o('refund',`💵 Trả lại ${f.extra} xu`,'nhận sai'),o('explain','🗣️ Giải thích','hên xui'),o('refuse','🙅 Không trả','cả ngõ sẽ biết')],
    amountBox(x,`cb-${ev.id}`,Math.max(1,Math.floor(f.extra/2)),{max:f.extra,label:'Hoặc trả bớt',send:'💵 Trả bớt',cmd:'cg_trouble',payload:{choice:'part'},field:'amount'}));
}
/* ------------------------------------------------------------ the guide */
function jobSteps(t,x){
  const d=data(x),rows=[],bike=d.bike||[];
  if(!d.out)return [{ok:null,label:'Xếp đồ nghề, lên đường trước',go:null}];
  const clues=t.needs?.clues||{},seen=['hoi','nhin','xa'].filter(h=>clues[h]).length+(t.camera?1:0);
  if(!t.diag||t.cleared==='fail'){
    const next=['hoi','nhin','xa','camera'].find(h=>!(h==='camera'?t.camera:clues[h])&&(h!=='camera'||bike.includes('camera')));
    if(seen<2&&next)rows.push({ok:null,label:'Tìm hiểu bệnh',note:`${seen} manh mối`,go:{cmd:'cg_check',payload:{task:t.id,how:next},label:`${HOW_EMOJI[next]} ${x.esc((cc(x).hows||{})[next]||next)}`}});
    else if(t.cleared==='fail'&&next)rows.push({ok:null,label:'Chưa đúng bệnh: tìm thêm',go:{cmd:'cg_check',payload:{task:t.id,how:next},label:`${HOW_EMOJI[next]} ${x.esc((cc(x).hows||{})[next]||next)}`}});
    rows.push({ok:t.diag&&t.cleared!=='fail'?true:null,label:'Ghi nguyên nhân',go:{sel:'.cg-diag',label:'📝 Chọn nguyên nhân'},pulse:''});
    return rows;
  }
  if(t.quote==null)return [{ok:null,label:'Báo giá trước khi làm',go:{sel:'.cg-quote .sk-opts',label:'🧾 Báo giá cho khách'},pulse:''}];
  if(t.quoted_for&&t.quoted_for!==t.diag)rows.push({ok:null,label:'Bệnh khác lúc báo giá: báo lại',go:{sel:'.cg-quote .sk-opts',label:'🧾 Báo lại giá'},pulse:''});
  const noMeter=t.kind==='manhole'&&!bike.includes('do_khi')&&!['khi','quat'].every(k=>(t.safety||[]).includes(k));
  if(noMeter){const m=toolOf(x,'do_khi');rows.push({ok:null,label:`Thiếu ${lower(m.name)}`,go:{cmd:'cg_fetch',payload:{tool:'do_khi',drop:bike.find(k=>!['gau','do_khi'].includes(k))||bike[0]},label:`🛵 Về tiệm lấy ${x.esc(lower(m.name))}`}});}
  if(t.kind==='manhole')for(const k of ['rao','khi','quat','canh'])if(!(t.safety||[]).includes(k)&&!(noMeter&&(k==='khi'||k==='quat')))rows.push({ok:null,label:(cc(x).safety||{})[k]||k,go:{cmd:'cg_safety',payload:{task:t.id,step:k},label:`⚠️ ${x.esc((cc(x).safety||{})[k]||k)}`}});
  if(!(d.gear||[]).includes('gang_tay'))rows.push({ok:null,label:'Đeo găng tay',go:{cmd:'cg_gear',payload:{item:'gang_tay'},label:'🧤 Đeo găng tay'}});
  if(t.kind==='manhole')for(const k of ['ung','khau_trang'])if(!(d.gear||[]).includes(k))rows.push({ok:null,label:(cc(x).gear||{})[k]||k,go:{cmd:'cg_gear',payload:{item:k},label:`${GEAR_EMOJI[k]} ${x.esc((cc(x).gear||{})[k]||k)}`}});
  if(!t.cleared||t.cleared==='fail'){rows.push({ok:null,label:'Thông bằng đồ nghề hợp bệnh',go:{sel:'.cg-use',label:'🧰 Chọn đồ nghề để thông'},pulse:''});return rows;}
  rows.push({ok:t.tested||null,label:'Xả nước thử',go:{cmd:'cg_test',payload:{task:t.id},label:'💧 Xả nước thử'}});
  rows.push({ok:t.cleaned||null,label:'Dọn sạch chỗ làm',go:{cmd:'cg_clean',payload:{task:t.id},label:'🧽 Dọn sạch chỗ làm'}});
  rows.push({ok:t.advised||null,label:'Dặn khách giữ ống thông',go:{cmd:'cg_advise',payload:{task:t.id},label:'🗣️ Dặn khách'}});
  return rows;
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện giữa đường',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(d.trouble?.ev)return {steps:[{ok:null,label:'Khách cũ quay lại',go:{sel:'.sk-trouble',label:'👉 Giải quyết với khách'},pulse:''}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'cg_intro',payload:{},label:'🧰 Vào việc thôi!'}}],final:null};
  if(t.twist?.state==='on')return {steps:[{ok:null,label:'Khách đang nói với bạn',go:{sel:'.sk-twist',label:'👉 Trả lời khách'},pulse:''}],final:null};
  if(t.kind==='setup'){const steps=setupSteps(t,x);return {steps,final:{label:'🛵 LÊN ĐƯỜNG',go:finalGo(steps,'cg_setout',{task:t.id}),ready:(d.bike||[]).length>0,why:'xếp ít nhất một món đồ nghề'}};}
  if(!t.known)return {steps:[{ok:null,label:'Nghe khách kể',go:{cmd:'ask',payload:{task:t.id},label:'👂 Nghe khách kể'}}],final:null,pulse:'.sk-ask'};
  if(t.stage==='pay'){const s=changeStep(x,t.id,t.cash),steps=s?[s]:[];return {steps,final:{label:'💵 ĐƯA TIỀN THỐI',go:finalGo(steps,'cg_pay',{task:t.id,...changePayload(x,t.id,t.cash)}),ready:true}};}
  const steps=jobSteps(t,x),done=t.cleared==='full'||t.cleared==='temp';
  return {steps,final:done?{label:t.kind==='manhole'?'🏦 BÁO PHƯỜNG NGHIỆM THU':'💵 TÍNH TIỀN',go:finalGo(steps,'cg_bill',{task:t.id}),ready:true}:null};
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});

export default {
  id:'drain',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='setup'?'Đọc sổ hẹn, xếp đồ nghề':!t.known?'Nghe khách kể':'Tìm bệnh, báo giá, thông';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    const top=`${introCard(x,'cg_intro','🧰')}${deskCard(x,'cg_desk','Chuyện giữa đường')}${troubleCard(x)}${troubleLast(x)}`;
    if(d.desk?.ev||d.trouble?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk cg">${hint}${top}${bottom(x,g)}</div>`;
    let main='',side='';
    if(t.twist?.state==='on'){const head=`${ticket(t,x)}`;return `<div class="career-job sk cg">${hint}${top}${head}${twistCard(t,x)}${bottom(x,g)}</div>`;}
    if(t.kind==='setup'){main=setupPanel(t,x);side=stepRows(x,g.steps,'Chuẩn bị',{chip:true});}
    else if(!t.known)main='';
    else if(t.stage==='pay')main=cashPanel(x,t.id,t.cash);
    else if(t.cleared==='full'||t.cleared==='temp')main=finishPanel(t,x);
    else{
      main=(!t.diag||t.cleared==='fail'?checkPanel(t,x):'')+(t.diag?quotePanel(t,x):'')+(t.quote!=null?safetyPanel(t,x)+workPanel(t,x):'');
      side=stepRows(x,g.steps,'Việc ở nhà khách',{chip:true});
    }
    const head=t.kind==='setup'?dayBar(x):`${ticket(t,x)}${dayBar(x)}`;
    return `<div class="career-job sk cg">${hint}${top}${head}<div class="workbench"><section class="wb-main">${main}${t.kind!=='setup'?bikeCard(x,true):''}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x),top=`${introCard(x,'cg_intro','🧰')}${deskCard(x,'cg_desk','Chuyện giữa đường')}${troubleCard(x)}${troubleLast(x)}`;
    if(d.trouble?.ev){const g={steps:[{ok:null,label:'Khách cũ quay lại',go:{sel:'.sk-trouble',label:'👉 Giải quyết với khách'},pulse:''}],final:null};return `<div class="career-job sk cg">${hintFor(g,x)}${top}${bottom(x,g)}</div>`;}
    if(d.desk?.ev||!d.intro||x.ui.intro){const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện giữa đường',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'cg_intro',payload:{},label:'🧰 Vào việc thôi!'}}],final:null};
      return `<div class="career-job sk cg">${hintFor(g,x)}${top}${bottom(x,g)}</div>`;}
    return `<div class="career-job sk cg">${top}${dayBar(x)}${bikeCard(x)}${debtBook(x,d.debts,'cg_chase')}</div>`;
  },
  input(el,x){return kitInput(el,x);},
  tick(root){keepBarAboveFooter(root);},
  // Day summary: "Ngày mai" first (parts and gloves in the store, who still owes, the morning's book), one way to
  // the store, the day's figures folded.
  summary(sum,x){
    if(!sum||sum.jobs==null)return '';
    const owe=(data(x).debts||[]).filter(d=>d.state==='open'),due=owe.reduce((n,d)=>n+(Number(d.owed)||0)-(Number(d.paid)||0),0);
    const plan=[...stockLines(x),owe.length?`📒 Còn ${owe.length} người nợ · ${x.fmt(due)} xu`:'',
      typeof sum.note==='string'&&sum.note?`<span aria-hidden="true">🧰</span> ${x.esc(sum.note)}`:''];
    const rows=[['Việc đã làm',sum.jobs],['Thông tận gốc',sum.cleared],['Thông tạm',sum.temp],['Tiền công (xu)',sum.earned],['Nói thách (xu)',sum.overcharged]];
    return planBox(x,{lines:plan,go:['📦 Mở kho vật tư','inventory'],more:[`🛵 Hôm nay · ${sum.jobs} việc · ${sum.earned||0} xu`,figures(x,rows,Array.isArray(sum.lines)?sum.lines:[])]});
  },
  actions:{...tillActions,...kitActions},
  dock:[['inventory','box','Kho vật tư','Ống xi-phông, găng tay…']],
};
