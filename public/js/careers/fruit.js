/** Sạp trái cây Dì Tư — the fruit stall at the mouth of the market (server: game/careers/fruit.py).
 * The morning set-up (cover, scale test, bruised fruit), the ripeness baskets, the spring scale with
 * its basket to zero ("trừ bì"), bargaining, cash through the shared till, a customer bringing fruit
 * back, and the evening sell-off. The awkward people (0.9.16): a price you name in a haggle (the customer
 * decides), "bán đắt" complaints, credit and walk-offs, the debt book, shoplifters and people filming the stall.
 * The server decides everything; one tap sends one command. */
import {stepRows,nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {cashPanel,changeStep,changePayload,tillActions} from './till.js';
import {data,cc,lower,tile,pane,introCard,deskCard,dayBar,person,askCard,bottom,kitActions,amountBox,kitInput,choiceCard,debtBook,troubleLast} from './street_kit.js';
import {linesSummary} from './tomorrow_kit.js';

const fruitOf=(x,k)=>(cc(x).fruits||[]).find(f=>f.id===k)||{id:k,name:k,emoji:'🍑',unit:'trái',g:300,kg:10,stages:['tuoi']};
const stageName=(x,s)=>(cc(x).stages||{})[s]||s;
const cheap=(x,s)=>(cc(x).cheap||['ky','heo']).includes(s);
const priceKg=(x,k)=>Number(x.room.life?.prices?.[k]??fruitOf(x,k).kg);
const kg=g=>{g=Math.round(Number(g)||0);if(g<1000&&g%100===0)return `${g/100} lạng`;return `${(g/1000).toFixed(2).replace(/\.?0+$/,'').replace('.',',')} ký`;};
const baskets=x=>data(x).baskets||{};
const real=t=>(t.bag||[]).reduce((s,b)=>s+b.g,0);
/** What the needle shows: fruit, the basket unless zeroed, and the spring's drift. */
const shown=(x,t)=>real(t)+(t.tare?0:Number(cc(x).basket||150))+Number(data(x).scale?.off||0);
const share=(x,t,g)=>{const r=real(t);return g+Math.trunc((shown(x,t)-r)*g/Math.max(1,r));};
function estimate(x,t){
  const r=real(t);if(!r)return 0;
  const v=(t.bag||[]).reduce((s,b)=>s+b.g*priceKg(x,b.i)*(cheap(x,b.s)?(100-(cc(x).xa_off||40)):100)/100/1000,0);
  return Math.max(1,Math.round(v*shown(x,t)/r));
}
const lineGot=(t,ln)=>(t.bag||[]).filter(b=>b.i===ln.i);
const lineText=(x,ln)=>{const f=fruitOf(x,ln.i);return `${ln.kg?kg(ln.kg):`${ln.n} ${f.unit}`} ${lower(f.name)}`;};

/* ------------------------------------------------------------ the scale */
function dial(x,grams,label=''){
  const deg=-135+Math.max(0,Math.min(2400,grams))/2400*270;
  return `<div class="fr-dial" role="img" aria-label="Cân chỉ ${x.esc(kg(grams))}"><span class="fr-ticks" aria-hidden="true"></span><i class="fr-needle" style="transform:rotate(${deg.toFixed(1)}deg)"></i>
    <span class="fr-read"><b>${kg(grams).replace(/ ký| lạng/,'')}</b><small>${grams<1000&&grams%100===0?'lạng':'ký'}</small></span>${label?`<em>${x.esc(label)}</em>`:''}</div>`;
}
function scaleCard(t,x){
  const bag=(t.bag||[]).map((b,i)=>{const f=fruitOf(x,b.i);return `<button type="button" class="fr-pick ${cheap(x,b.s)?'cheap':''} ${b.b?'bad':''}" data-command="tc_unpick" data-payload="${x.esc(JSON.stringify({task:t.id,index:i}))}" aria-label="Bỏ ra ${x.esc(f.name)}"><span aria-hidden="true">${x.esc(f.emoji)}</span><small>${b.g}g</small></button>`;}).join('');
  const est=estimate(x,t);
  return `<section class="card fr-scale" aria-label="Cân">${dial(x,shown(x,t))}
    <div class="fr-scale-side"><div class="fr-basket">${bag||'<small class="muted">Rổ trống</small>'}</div>
      <div class="fr-scale-row">${t.tare?'<span class="tag green">✓ Đã trừ bì rổ</span>':x.cmd('⚖️ Trừ bì rổ','tc_tare',{task:t.id},'small fr-tare')}${est?`<b class="fr-est">≈ ${x.fmt(est)} xu</b>`:''}</div></div></section>`;
}

/* ------------------------------------------------------------ the baskets */
function fruitRow(t,x,k,want=[]){
  const f=fruitOf(x,k),b=baskets(x)[k]||{},bruised=(data(x).bruise||{})[k];
  const stages=[...new Set(f.stages)].map(s=>{
    const q=Number(b[s]||0);
    return `<button type="button" class="fr-st st-${x.esc(s)} ${want.includes(s)?'want':''}" data-command="tc_pick" data-payload="${x.esc(JSON.stringify({task:t.id,item:k,stage:s}))}"${q?'':' disabled'}><span>${x.esc(stageName(x,s))}</span><b>${q}</b></button>`;
  }).join('');
  return `<div class="fr-row"><div class="fr-fruit"><span aria-hidden="true">${x.esc(f.emoji)}</span><b>${x.esc(f.name)}</b><small>${priceKg(x,k)} xu/ký${bruised?' · <em>có trái dập</em>':''}</small></div><div class="fr-stages">${stages}</div></div>`;
}
function pickPanel(t,x){
  const n=t.needs||{},lines=n.lines||[],mine=new Set(t.kind==='bulk'?(n.bulk||[]):lines.map(l=>l.i));
  const want=k=>t.kind==='bulk'?['ky']:(lines.find(l=>l.i===k)?.want||[]);
  const main=[...mine].map(k=>fruitRow(t,x,k,want(k))).join('');
  const rest=(cc(x).fruits||[]).filter(f=>!mine.has(f.id)).map(f=>fruitRow(t,x,f.id,[])).join('');
  return `<section class="card fr-pickwrap"><h4>🧺 Chọn trái</h4>${main}${rest?pane(x,`rest-${t.id}`,'Trái khác trên sạp',rest,false,'fr-rest'):''}</section>`;
}
function ticket(t,x){
  if(!t.known)return askCard(x,t,'👂 Hỏi khách mua gì');
  const n=t.needs||{};
  let chips='';
  if(t.kind==='bulk'){const got=(t.bag||[]).length;chips=`<span class="fr-chip ${got>=n.min?'ok':''}">🥤 ${got}/${n.min}–${n.max} trái chín kỹ</span>`;}
  else chips=(n.lines||[]).map(ln=>{
    const got=lineGot(t,ln),f=fruitOf(x,ln.i),g=got.reduce((s,b)=>s+b.g,0);
    const done=ln.kg?share(x,t,g)*100>=ln.kg*(cc(x).short||90):got.length>=ln.n;
    const prog=ln.kg?kg(share(x,t,g)):`${got.length}/${ln.n}`;
    return `<span class="fr-chip ${done?'ok':''}">${x.esc(f.emoji)} ${x.esc(lineText(x,ln))} · <i>${ln.want.map(s=>x.esc(lower(stageName(x,s)))).join('/')}</i> <small>${x.esc(prog)}</small></span>`;
  }).join('');
  const tag=n.check?'<span class="tag amber">⚖️ Mang cân riêng</span>':'';
  return person(x,t,`<p class="fr-chips">${chips}</p>${n.note?`<p class="muted small">“${x.esc(n.note)}”</p>`:''}`,tag);
}
function hagglePanel(t,x){
  const mid=Math.floor((t.price+t.offer+1)/2),hasCam=Number(baskets(x).cam?.tuoi||0)+Number(baskets(x).cam?.heo||0)>0;
  const deal=(id,label,sub,dis=false)=>x.cmd(`<span class="sk-opt-label">${label}</span><small>${sub}</small>`,'tc_deal',{task:t.id,deal:id},'sk-opt',dis);
  return `<section class="card fr-haggle"><div class="fr-offer"><span aria-hidden="true">🗣️</span><p>“<b>${x.fmt(t.offer)} xu</b> thôi!”<small>Cân ra ${x.fmt(t.price)} xu</small></p></div>
    <div class="sk-opts fr-deals">${deal('hold','🙂 Giữ giá',`${t.price} xu, nói rõ trái tươi, cân đủ`)}${deal('meet','🤝 Bớt một nửa',`${mid} xu`)}
    ${deal('extra','🍊 Giữ giá, tặng thêm trái cam',hasCam?'mất một trái cam':'hết cam',!hasCam)}${deal('give','✅ Bán theo giá khách',`${t.offer} xu`)}</div>
    ${amountBox(x,`offer-${t.id}-${t.offer}`,mid,{max:Math.max(t.price*2,10),label:'Hoặc tự ra giá',send:'🤝 Chốt giá này',cmd:'tc_offer',payload:{task:t.id}})}</section>`;
}
function creditCard(t,x){
  const tw=t.twist;if(!tw||tw.state!=='on')return '';
  const o=(choice,label,sub)=>({cmd:'tc_credit',payload:{task:t.id,choice},label,sub});
  if(tw.kind==='tab')return choiceCard(x,'fr-credit','📒',`Xin ghi nợ · ${x.fmt(t.price)} xu`,tw.line,[
    o('tab','📒 Ghi nợ hết','có người trả, có người quên luôn'),o('refuse','🙅 Không bán chịu','khách có thể bỏ đi')],
    amountBox(x,`part-${t.id}`,Math.max(1,Math.floor(t.price/2)),{max:t.price,label:'Hoặc xin trả trước',send:'💵 Xin trả trước',cmd:'tc_credit',payload:{task:t.id,choice:'part'},field:'amount'}));
  return choiceCard(x,'fr-credit','🏃',`Khách cầm túi đi · ${x.fmt(t.price)} xu`,tw.line,[
    o('hold','✋ Giữ túi lại, đợi lấy ví','khách ngay thì không sao'),o('trust','🙂 Cho cầm đi, tin khách','hên xui'),o('call','👮 Gọi bảo vệ chợ','bắt oan là mất lòng')]);
}
function troubleCard(x){
  const ev=data(x).trouble?.ev;if(!ev)return '';
  const f=ev.facts,o=(choice,label,sub)=>({cmd:'tc_trouble',payload:{choice},label,sub});
  if(ev.kind==='thief'){const fr=fruitOf(x,f.item);
    return choiceCard(x,'sk-trouble','🥷','Kẻ chôm trái',`${f.who} nhét ${f.qty} ${fr.unit} ${lower(fr.name)} vào túi riêng, lững thững bước đi.`,[
      o('remind','🙂 Nhắc khéo: “Quên tính tiền kìa”','người biết ngượng sẽ trả'),o('guard','👮 Gọi bảo vệ chợ','khách chờ ở sạp'),o('ignore','🤐 Làm ngơ',`mất ${f.value} xu`)],
      amountBox(x,`demand-${ev.id}`,f.value,{max:f.value*3,label:'Hoặc giữ lại, đòi tiền',send:'✋ Đòi tiền',cmd:'tc_trouble',payload:{choice:'demand'},field:'amount'}));}
  return choiceCard(x,'sk-trouble','📱','Bị quay clip “bán đắt”','Một chị khách giơ điện thoại quay sạp: “Trái gì bán đắt vl, chợ mạng rẻ bằng nửa!”',[
    o('scale','⚖️ Mời cân lại, chỉ bảng giá',''),o('taste','🍊 Bổ trái mời nếm','mất một trái cam'),o('argue','😤 Cãi tay đôi','cả chợ nghe'),o('ignore','🤐 Kệ','')]);
}
function returnPanel(t,x){
  const f=fruitOf(x,t.needs?.ret),b=baskets(x)[t.needs?.ret]||{},good=Object.entries(b).some(([s,q])=>q&&!cheap(x,s));
  const opt=(id,label,sub,dis=false)=>x.cmd(`<span class="sk-opt-label">${label}</span>${sub?`<small>${sub}</small>`:''}`,'tc_return',{task:t.id,choice:id},'sk-opt',dis);
  return `<section class="card fr-return"><h4>${x.esc(f.emoji)} Trái ${x.esc(lower(f.name))} mang lại</h4>
    ${t.seen?`<p class="fr-seen">🔍 ${x.esc(t.seen)}</p>`:x.cmd('🔍 Xem trái','tc_look',{task:t.id},'primary fr-look')}
    <div class="sk-opts">${opt('swap','🔁 Đổi trái khác',good?'':'hết trái tốt để đổi',!good)}${opt('refund','💵 Hoàn tiền','')}${opt('explain','🗣️ Giải thích nhẹ nhàng','')}${opt('argue','😤 Cãi lại','')}</div></section>`;
}

/* ------------------------------------------------------------ set-up */
function setupPanel(t,x){
  const d=data(x),st=d.stall||{},n=t.needs||{},sc=d.scale||{},bruise=Object.entries(d.bruise||{}).filter(([,v])=>v);
  const cover=[['du','⛱️','Dựng dù','Che nắng'],['bat','🟦','Căng bạt','Che mưa']].map(([k,e,l,s])=>tile(x,'tc_cover',{cover:k},`<span class="tile-emoji">${e}</span><b>${l}</b><small>${s}</small>`,`${st.cover===k?'selected':''} ${n.cover===k?'want':''}`)).join('');
  const reading=st.tested?1000+Number(sc.off||0):Number(sc.off||0);
  const scaleBtn=!st.tested?x.cmd('⚖️ Đặt quả cân 1 ký','tc_scale_test',{},'primary'):sc.off?x.cmd('🔧 Chỉnh kim về đúng','tc_scale_fix',{},'primary'):'<span class="tag green">✓ Cân chuẩn</span>';
  const rows=bruise.map(([k,v])=>{const f=fruitOf(x,k);return `<li><span aria-hidden="true">${x.esc(f.emoji)}</span><span class="grow">${x.esc(f.name)} <small>${v} trái dập</small></span>${x.cmd('🧺 Lựa ra','tc_sort',{item:k},'small')}</li>`;}).join('');
  return `<section class="card fr-setup"><h4>${st.cover?'✓ ':''}Che sạp</h4><div class="tile-grid fr-cover">${cover}</div>
    <h4 class="section-title">Thử cân</h4><div class="fr-test">${dial(x,reading,st.tested?'quả cân 1 ký':'cân trống')}<div>${scaleBtn}${st.tested&&sc.off?`<p class="small fr-warn">Lệch ${Math.abs(sc.off)} gam</p>`:''}</div></div>
    <h4 class="section-title">Trái dập</h4>${rows?`<ul class="fr-bruise">${rows}</ul>`:'<p class="small muted">✓ Rổ nào cũng sạch.</p>'}
    <p class="small muted">${x.esc(n.note||'')}</p></section>`;
}
function setupSteps(t,x){
  const d=data(x),st=d.stall||{},n=t.needs||{},sc=d.scale||{},rows=[];
  rows.push({ok:st.cover?st.cover===n.cover:null,label:n.cover==='bat'?'Căng bạt che mưa':'Dựng dù che nắng',note:st.cover&&st.cover!==n.cover?'chưa hợp trời':'',go:{cmd:'tc_cover',payload:{cover:n.cover},label:n.cover==='bat'?'🟦 Căng bạt':'⛱️ Dựng dù'}});
  rows.push({ok:st.tested?true:null,label:'Thử cân với quả cân 1 ký',go:{cmd:'tc_scale_test',payload:{},label:'⚖️ Đặt quả cân 1 ký'}});
  if(st.tested&&sc.off)rows.push({ok:null,label:'Chỉnh kim cân về đúng',note:`lệch ${Math.abs(sc.off)} gam`,go:{cmd:'tc_scale_fix',payload:{},label:'🔧 Chỉnh kim cân'}});
  for(const [k,v] of Object.entries(d.bruise||{}))if(v)rows.push({ok:null,label:`Lựa ${fruitOf(x,k).name.toLowerCase()} dập`,go:{cmd:'tc_sort',payload:{item:k},label:`🧺 Lựa ${x.esc(lower(fruitOf(x,k).name))} dập ra`}});
  return rows;
}

/* ------------------------------------------------------------ the guide */
function pickGo(t,x,k,want){
  const b=baskets(x)[k]||{},s=want.find(w=>Number(b[w]||0)>0),f=fruitOf(x,k);
  return s?{cmd:'tc_pick',payload:{task:t.id,item:k,stage:s},label:`${x.esc(f.emoji)} Lấy ${x.esc(lower(f.name))} ${x.esc(lower(stageName(x,s)))}`}:null;
}
function buySteps(t,x){
  const n=t.needs||{},rows=[];
  if(!data(x).stall?.open)rows.push({ok:null,label:'Dọn sạp xong mới bán',go:null});
  rows.push({ok:t.tare?true:null,label:'Trừ bì rổ trên cân',go:{cmd:'tc_tare',payload:{task:t.id},label:'⚖️ Trừ bì rổ'}});
  (t.bag||[]).forEach((b,i)=>{if(b.b)rows.push({ok:false,label:`Trái ${lower(fruitOf(x,b.i).name)} bị dập`,go:{cmd:'tc_unpick',payload:{task:t.id,index:i},label:'↩︎ Bỏ trái dập ra'}});});
  if(t.kind==='bulk'){
    const got=(t.bag||[]).length,k=(n.bulk||[]).find(i=>Number(baskets(x)[i]?.ky||0)>0);
    rows.push(got>=n.min?{ok:true,label:`${got} trái chín kỹ`}:{ok:null,label:`Gom ${n.min}–${n.max} trái chín kỹ`,note:`${got}/${n.min}`,go:k?pickGo(t,x,k,['ky']):null});
    return rows;
  }
  for(const ln of n.lines||[]){
    const got=lineGot(t,ln),g=got.reduce((s,b)=>s+b.g,0),f=fruitOf(x,ln.i);
    const wrong=got.findIndex(b=>!ln.want.includes(b.s));
    if(wrong>=0){const i=(t.bag||[]).indexOf(got[wrong]);rows.push({ok:false,label:`${f.name}: sai độ chín`,go:{cmd:'tc_unpick',payload:{task:t.id,index:i},label:`↩︎ Để lại trái ${x.esc(lower(stageName(x,got[wrong].s)))}`}});continue;}
    const done=ln.kg?share(x,t,g)*100>=ln.kg*(cc(x).short||90):got.length>=ln.n;
    if(done){rows.push({ok:true,label:lineText(x,ln),note:ln.kg?kg(share(x,t,g)):''});continue;}
    const go=pickGo(t,x,ln.i,ln.want);
    rows.push({ok:null,label:lineText(x,ln),note:go?(ln.kg?`đang ${kg(share(x,t,g))}`:`${got.length}/${ln.n}`):'hết trái đúng ý',go});
  }
  return rows;
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở sạp',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(d.trouble?.ev)return {steps:[{ok:null,label:'Có chuyện ở sạp',go:{sel:'.sk-trouble',label:'👉 Xử lý ngay'},pulse:''}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'tc_intro',payload:{},label:'🧺 Vào việc thôi!'}}],final:null};
  if(t.stage==='credit')return {steps:[{ok:null,label:'Khách chưa trả tiền',go:{sel:'.sk-twist',label:'👉 Xử lý khách'},pulse:''}],final:null};
  if(t.kind==='setup'){const steps=setupSteps(t,x);return {steps,final:{label:'☀️ MỞ HÀNG',go:finalGo(steps,'tc_open',{task:t.id}),ready:!!d.stall?.cover,why:'dựng dù hoặc căng bạt'}};}
  if(!t.known)return {steps:[{ok:null,label:'Hỏi khách',go:{cmd:'ask',payload:{task:t.id},label:'👂 Hỏi khách mua gì'}}],final:null,pulse:'.sk-ask'};
  if(t.kind==='return'){
    if(!t.seen)return {steps:[{ok:null,label:'Xem trái khách mang lại',go:{cmd:'tc_look',payload:{task:t.id},label:'🔍 Xem trái'}}],final:null};
    return {steps:[{ok:null,label:'Chọn cách giải quyết',go:{sel:'.fr-return .sk-opts',label:'👉 Chọn cách giải quyết'},pulse:''}],final:null};
  }
  if(t.stage==='haggle')return {steps:[{ok:null,label:'Khách trả giá',go:{sel:'.fr-deals',label:'🤝 Trả lời khách'},pulse:''}],final:null};
  if(t.stage==='pay'){const s=changeStep(x,t.id,t.cash),steps=s?[s]:[];return {steps,final:{label:'💵 ĐƯA TIỀN THỐI',go:finalGo(steps,'tc_pay',{task:t.id,...changePayload(x,t.id,t.cash)}),ready:true}};}
  const steps=buySteps(t,x),stuck=steps.some(s=>s.ok===null&&!s.go&&s.note==='hết trái đúng ý');
  if(stuck&&!(t.bag||[]).length)return {steps,final:{label:'🙏 Nói thật: hết trái đúng ý',go:{cmd:'tc_decline',payload:{task:t.id}},ready:true}};
  return {steps,final:{label:'⚖️ CÂN · TÍNH TIỀN',go:finalGo(steps,'tc_weigh',{task:t.id}),ready:!!(t.bag||[]).length,why:'bỏ trái vào rổ trước'}};
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});

/* ------------------------------------------------------------ idle: the stall between customers */
function stallView(x){
  const d=data(x),b=baskets(x);
  const rows=(cc(x).fruits||[]).map(f=>{const s=b[f.id]||{},parts=[...new Set(f.stages)].filter(k=>s[k]).map(k=>`<span class="fr-mini st-${x.esc(k)}">${x.esc(stageName(x,k))} ${s[k]}</span>`).join('');
    return `<li><span aria-hidden="true">${x.esc(f.emoji)}</span><b>${x.esc(f.name)}</b><span class="fr-minis">${parts||'<small class="muted">hết</small>'}</span></li>`;}).join('');
  const ch=Object.values(b).reduce((s,v)=>s+Object.entries(v).filter(([k])=>cheap(x,k)).reduce((a,[,q])=>a+q,0),0);
  const xa=d.stall?.open&&!d.stall?.xa&&ch?x.cmd(`📣 Rao xả ${ch} trái chín kỹ, héo`,'tc_xa',{},'primary full'):d.stall?.xa?'<p class="small muted">📣 Hôm nay đã rao xả.</p>':'';
  return `<section class="card fr-stall"><h4>🧺 Trên sạp</h4><ul class="fr-list">${rows}</ul>${xa}</section>`;
}

export default {
  id:'fruit',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='setup'?'Dọn sạp, thử cân':!t.known?'Hỏi khách mua gì':'Chọn trái, cân cho khách';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    const top=`${introCard(x,'tc_intro','🧺')}${deskCard(x,'tc_desk','Chuyện ở sạp')}${troubleCard(x)}${troubleLast(x)}`;
    if(d.desk?.ev||d.trouble?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk fr">${hint}${top}${bottom(x,g)}</div>`;
    let main='',side='';
    if(t.stage==='credit')return `<div class="career-job sk fr">${hint}${top}${ticket(t,x)}${creditCard(t,x)}${bottom(x,g)}</div>`;
    if(t.kind==='setup'){main=setupPanel(t,x);side=stepRows(x,g.steps,'Việc dọn sạp');}
    else if(!t.known)main='';
    else if(t.kind==='return')main=returnPanel(t,x);
    else if(t.stage==='haggle')main=scaleCard(t,x)+hagglePanel(t,x);
    else if(t.stage==='pay')main=cashPanel(x,t.id,t.cash);
    else{main=scaleCard(t,x)+pickPanel(t,x);side=stepRows(x,g.steps,'Việc của khách');}
    const head=t.kind==='setup'?dayBar(x):`${ticket(t,x)}${dayBar(x)}`;
    return `<div class="career-job sk fr">${hint}${top}${head}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x),top=`${introCard(x,'tc_intro','🧺')}${deskCard(x,'tc_desk','Chuyện ở sạp')}${troubleCard(x)}${troubleLast(x)}`;
    if(d.trouble?.ev){const g={steps:[{ok:null,label:'Có chuyện ở sạp',go:{sel:'.sk-trouble',label:'👉 Xử lý ngay'},pulse:''}],final:null};return `<div class="career-job sk fr">${hintFor(g,x)}${top}${bottom(x,g)}</div>`;}
    if(d.desk?.ev||!d.intro||x.ui.intro){const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện ở sạp',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'tc_intro',payload:{},label:'🧺 Vào việc thôi!'}}],final:null};
      return `<div class="career-job sk fr">${hintFor(g,x)}${top}${bottom(x,g)}</div>`;}
    return `<div class="career-job sk fr">${top}${dayBar(x)}${stallView(x)}${debtBook(x,d.debts,'tc_chase')}</div>`;
  },
  input(el,x){return kitInput(el,x);},
  tick(root){keepBarAboveFooter(root);},
  actions:{...tillActions,...kitActions},
  // "Ngày mai" first: the lines about tomorrow, the stock room, Kho; the rest of the day folded.
  summary(data,x){return linesSummary(data,x);},
  dock:[['inventory','box','Kho trái cây','Nhập xoài, cam, bưởi…']],
};
