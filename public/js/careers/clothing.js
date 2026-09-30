/** Tiệm Áo Chỉ Mây — a small neighbourhood clothes shop (server: game/careers/clothing.py).
 *  The rack (item → colour → size, with the count left on each size), the fitting room queue,
 *  alterations at Bà Tư's machine, returns by the house policy, sale tags, Zalo/Facebook
 *  parcels, the mannequin, and a real till (./till.js). Intro card "Giới thiệu nghề" on first open. */
import {keepBarAboveFooter} from './food_kit.js';
import {reqList,fold} from '../ui-kit.js';
import {stepRows,nextHint,stepCta,finalGo,pending,stepLine} from '../v4/guide.js';
import {restockButton} from '../v4/restock.js';
import {cashPanel,changeStep,changePayload,tray,tillActions} from './till.js';
import * as SF from './stage_fold.js';
import {reqPin,nextLine,pinTop,asmActions,finalStep} from './asm_kit.js';
const ID='clothing';
const FREE=['hat','belt','socks'];
const data=x=>x.room.data||{};
const catalogue=x=>x.content.inventory?.items?.[ID]||[];
const item=(x,id)=>catalogue(x).find(i=>i.id===id)||{id,name:id,emoji:'👚',unit:'cái'};
const price=(x,id)=>(data(x).prices||{})[id]??x.cc.base_prices?.[id]??0;
const sizes=(x,id)=>x.cc.sizes?.[id]||['F'];
const colours=(x,id)=>x.cc.colours?.[id]||[];
const swatch=(x,c)=>x.cc.swatch?.[c]||'#ccc';
const onRack=(x,id,s)=>(data(x).grid?.[id]?.[s])||0;
/** What can still be taken for a new pick: on the rack minus what open bills and parcels hold. */
const free=(x,id,s)=>Math.max(0,onRack(x,id,s)-((data(x).held||{})[`${id}:${s}`]||0));
const npcId=i=>`${ID}_npc_${String(i+1).padStart(2,'0')}`;
const sum=a=>(a||[]).reduce((s,v)=>s+Number(v||0),0);
const KIND_ICON={fit:'📏',outfit:'👗',alter:'✂️',room:'🚪',return:'🔁',sale:'🏷️',online:'📦',display:'🧍‍♀️'};
const sizeLabel=s=>s==='F'?'Free size':s;
const dot=(x,c)=>`<i class="ao-dot" style="background:${x.esc(swatch(x,c))}" aria-hidden="true"></i>`;
const pieceLabel=(x,p)=>`${item(x,p.item).emoji} ${item(x,p.item).name}${p.size&&p.size!=='F'?` · size ${p.size}`:''} · ${p.colour}`;
const carBtn=(x,label,action,d={},cls='')=>`<button type="button" class="btn ${cls}" data-action="car:${action}"${Object.entries(d).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}>${label}</button>`;

/* ------------------------------------------------------------ intro card */
function introCard(x,closable=true){
  const i=x.cc.intro;if(!i)return '';
  const list=rows=>`<ul class="ao-ilist">${rows.map(([e,t])=>`<li><span aria-hidden="true">${x.esc(e)}</span>${x.esc(t)}</li>`).join('')}</ul>`;
  return `<section class="card ao-intro" aria-label="Giới thiệu nghề"><div class="ao-intro-head"><span class="ao-intro-icon" aria-hidden="true">🧵</span><div><small>Giới thiệu nghề</small><h3>${x.esc(i.title)}</h3></div></div>
    <p class="ao-story">${x.esc(i.story)}</p>
    <h4>🧺 Công việc gồm…</h4>${list(i.does)}
    <h4>⚡ Bạn sẽ gặp…</h4>${list(i.meets)}
    <h4>🌟 Được sao khi…</h4>${list(i.stars)}
    ${closable?x.cmd('🪡 Vào ca thôi!','ao_intro',{seen:true},'primary full ao-intro-go'):''}</section>`;
}
const showIntro=x=>!data(x).intro||x.ui.intro;
const introFold=x=>`<details class="ao-intro-fold"><summary>🧵 Giới thiệu nghề <small>· công việc, người bạn gặp, khi nào được sao</small></summary>${introCard(x)}</details>`;

/* ------------------------------------------------------------ small cards */
function todayStrip(x){
  const t=data(x).today;if(!t)return '';
  const sale=data(x).sale_today;
  return `<div class="ao-today"><span aria-hidden="true">${x.esc(t.emoji)}</span><p><b>Ngày ${t.day} · ${x.esc(t.name)}</b><small>${x.esc(t.text)}</small></p>${sale?`<span class="tag amber">🏷️ Đang sale</span>`:''}</div>`;
}
function bookLine(x,t){
  const idx=Number(String(t.npc).slice(-2))-1,row=(data(x).book||{})[String(idx)];
  if(!row)return '';
  const parts=[row.top?`áo ${row.top}`:'',row.waist?`quần ${row.waist}`:'',(row.kid||[]).length?`bé ${row.kid.join(', ')}`:''].filter(Boolean);
  return parts.length?`<p class="ao-book small">📒 Sổ size khách quen: <b>${x.esc(parts.join(' · '))}</b></p>`:'';
}
function ticket(t,x){
  const w=x.npc(t.npc),kind=x.cc.kinds?.[t.kind]||t.kind;
  const said=t.kind==='fit'?t.needs.lines.map(l=>l.say).join(' '):t.kind==='outfit'?t.needs.note:t.opening;
  return `<article class="card ticket ao-ticket"><div class="row">${x.portrait(w,52)}<div class="grow"><div class="row spread wrap"><h3>${x.esc(w.display_name)}</h3><span class="tag">${KIND_ICON[t.kind]||''} ${x.esc(kind)}</span></div>
    <p class="ao-said">“${x.esc(said)}”</p>${bookLine(x,t)}
    <div class="patience" title="Kiên nhẫn"><div class="bar ${t.patience<50?'low':''}"><i style="width:${t.patience}%"></i></div><small>${t.patience}%</small></div></div></div></article>`;
}

/* ------------------------------------------------------------ the rack (pick / pack / dress) */
const pickOf=(x,t)=>{const p=x.ui.pick;return p&&p.task===t.id?p:{task:t.id,item:null,colour:null};};
/** What the order still needs from the rack: item → the colour asked ('' when any colour goes). */
function needOf(t,x){
  const out=new Map(),add=(i,c)=>{if(!out.has(i))out.set(i,c||'');};
  if(!t.known)return out;
  if(t.kind==='fit'&&t.stage==='pick'){const m=lineMatches(t);t.needs.lines.forEach((l,k)=>{if(m[k]<0)add(l.item,l.colour);});}
  else if(t.kind==='online'&&!t.parcel.sealed){const m=packMatch(t);t.needs.lines.forEach((l,k)=>{if(m[k]<0)add(l.item,l.colour);});}
  else if(t.kind==='room'&&t.stage==='pick'){const b=t.needs.buy;if(!t.picks.some(p=>p.item===b.item&&p.colour===b.colour))add(b.item,b.colour);}
  else if(t.kind==='outfit'&&t.stage==='pick'){
    const o=x.cc.occasions?.[t.needs.occasion]||{},have=new Set(t.picks.map(p=>p.item));
    if(!isSet(t,x))for(const m of o.mains||[])if(m.some(i=>have.has(i))||!have.size)for(const i of m)if(!have.has(i))add(i);
    for(const i of o.need||[])if(!have.has(i))add(i);
  }
  return out;
}
function rack(t,x,mode='pick',want=''){
  const p=pickOf(x,t),cmd=mode==='pack'?'ao_pack':'ao_pick',need=mode==='dress'?new Map():needOf(t,x);
  // What the customer asked for leads the rack ("Khách cần"), and a tap on it picks the colour they said.
  const list=[...catalogue(x)].sort((a,b)=>need.has(b.id)-need.has(a.id));
  const chips=list.map(it=>{const left=sizes(x,it.id).reduce((s,z)=>s+free(x,it.id,z),0),w=need.has(it.id);
    return `<button type="button" class="ao-chip g-${x.esc(x.cc.groups?.[it.id]||'')}${p.item===it.id?' on':''}${w?' want':''}" data-action="car:item" data-task="${x.esc(t.id)}" data-item="${x.esc(it.id)}"${w&&need.get(it.id)?` data-colour="${x.esc(need.get(it.id))}"`:''} aria-pressed="${p.item===it.id}">${w?'<i class="asm-need">Khách cần</i>':''}<span aria-hidden="true">${x.esc(it.emoji)}</span><b>${x.esc(it.name)}</b><small>${mode==='dress'?'':`còn ${left} · `}${x.fmt(price(x,it.id))} xu</small></button>`;}).join('');
  let body=`<p class="small muted ao-lab">${mode==='dress'?'Chạm một món để chọn màu.':'Chạm một món để chọn màu và size.'}</p>`;
  if(p.item){
    const it=item(x,p.item),said=need.get(p.item)||'';
    const cols=[...colours(x,p.item)].sort((a,b)=>(b===said)-(a===said));
    const sw=cols.map(c=>mode==='dress'
      ?`<button type="button" class="ao-swatch" data-command="ao_dress" data-payload="${x.esc(JSON.stringify({task:t.id,item:p.item,colour:c}))}">${dot(x,c)}<span>${x.esc(c)}</span></button>`
      :`<button type="button" class="ao-swatch${p.colour===c?' on':''}${c===said?' want':''}" data-action="car:colour" data-task="${x.esc(t.id)}" data-colour="${x.esc(c)}" aria-pressed="${p.colour===c}">${dot(x,c)}<span>${x.esc(c)}${c===said?' <small>· khách dặn</small>':''}</span></button>`).join('');
    const sz=mode==='dress'?'':sizes(x,p.item).map(s=>{const n=free(x,p.item,s),off=!p.colour||n<=0;
      return `<button type="button" class="ao-size${n<=0?' out':''}" data-command="${cmd}" data-payload="${x.esc(JSON.stringify({task:t.id,item:p.item,size:s,colour:p.colour}))}"${off?' disabled':''} aria-label="${x.esc(`${it.name} size ${s}, còn ${n}`)}"><b>${x.esc(sizeLabel(s))}</b><small>${n<=0?'hết':`còn ${n}`}</small></button>`;}).join('');
    const empty=sizes(x,p.item).some(s=>onRack(x,p.item,s)<=0);
    body=`<div class="ao-sel"><span class="ao-sel-emoji" aria-hidden="true">${x.esc(it.emoji)}</span><b>${x.esc(it.name)}</b><span class="muted">${x.fmt(price(x,p.item))} xu</span></div>
      <p class="ao-lab">${mode==='dress'?'Chạm màu để mặc lên ma-nơ-canh':'1 · Màu'}</p><div class="ao-swatches">${sw}</div>
      ${mode==='dress'?'':`<p class="ao-lab">2 · Size <small>${p.colour?'(số nhỏ = còn trên giá)':'— chọn màu trước'}</small></p><div class="ao-sizes">${sz}</div>`}
      ${empty&&mode!=='dress'?`<div class="ao-restock">${restockButton(x.room,[{id:p.item,need:4}],{task:t.id},'small ghost')}</div>`:''}`;
  }
  const title=mode==='pack'?'📦 Lấy đồ trên giá bỏ vào gói':mode==='dress'?'🧍‍♀️ Chọn đồ cho ma-nơ-canh':'👚 Giá treo';
  return `<section class="card ao-rack"${want?` data-want="${x.esc(want)}"`:''}><h4>${title}</h4><div class="ao-chips" role="group" aria-label="Các món trong tiệm">${chips}</div>${body}</section>`;
}
function sizeChart(x){
  const rows=(x.cc.top_chart||[]).map(([s,h1,h2,w1,w2])=>`<tr><th>${s}</th><td>${h1}–${h2} cm</td><td>${w1}–${w2} kg</td></tr>`).join('');
  const jeans=Object.entries(x.cc.jeans_waist||{}).map(([s,w])=>`<span class="ao-kv"><b>${s}</b> eo ${w}</span>`).join('');
  const kids=Object.entries(x.cc.kids_age||{}).map(([s,[a,b]])=>`<span class="ao-kv"><b>${s}</b> ${a}–${b} tuổi</span>`).join('');
  return fold('📐 Bảng size của tiệm',`<table class="ao-chart"><thead><tr><th>Size</th><th>Cao</th><th>Nặng</th></tr></thead><tbody>${rows}</tbody></table>
    <p class="small">👖 Quần jean theo vòng eo (cm):</p><div class="ao-kvs">${jeans}</div>
    <p class="small">🧒 Đồ trẻ em theo tuổi:</p><div class="ao-kvs">${kids}</div>
    <p class="small ao-tipline">💡 Sơ mi của tiệm may ôm: khách mặc size nào ở shop khác thì lấy <b>lớn hơn một size</b>.</p>`);
}
function picked(t,x){
  if(!t.picks.length)return '<p class="small muted ao-empty">Quầy còn trống.</p>';
  const canTry=t.stage==='pick';
  return `<ul class="ao-picked">${t.picks.map((p,i)=>{const tried=t.tried[i];
    const tag=tried==='ok'?'<span class="tag green">✓ vừa</span>':tried==='small'?'<span class="tag danger">chật</span>':tried==='big'?'<span class="tag danger">rộng</span>':'';
    return `<li>${dot(x,p.colour)}<span class="grow">${x.esc(pieceLabel(x,p))}<small>${x.fmt(price(x,p.item))} xu</small></span>${tag}
      ${canTry&&!FREE.includes(p.item)&&tried==null?x.cmd('🚪 Mời thử','ao_try',{task:t.id,index:i},'small ghost'):''}
      ${canTry?`<button type="button" class="btn small ghost ao-x" data-command="ao_unpick" data-payload="${x.esc(JSON.stringify({task:t.id,index:i}))}" aria-label="Treo lại ${x.esc(item(x,p.item).name)}">✕</button>`:''}</li>`;}).join('')}</ul>`;
}
function receipt(t,x){
  const b=t.bill;if(!b)return '';
  const card=`<div class="card ao-receipt"><h4>🧾 Hóa đơn</h4><ul>${b.lines.map(l=>`<li><span class="grow">${x.esc(l.label)}${l.size&&l.size!=='F'?` · ${x.esc(l.size)}`:''}${l.colour?` · ${x.esc(l.colour)}`:''}</span><b>${x.fmt(l.amount)}</b></li>`).join('')}</ul>
    ${b.off?`<p class="ao-rline"><span>Cộng</span><b>${x.fmt(b.sub)}</b></p><p class="ao-rline"><span>Bớt</span><b>−${x.fmt(b.off)}</b></p>`:''}
    <p class="ao-rline total"><span>Tổng</span><b>${x.money(b.total)}</b></p></div>`;
  // At the till the bill is one line (the change panel repeats the total); a tap opens it.
  return SF.part(x,t.id,new Set(),'bill','🧾 Hóa đơn',card,{done:true,sum:`${b.lines.length} dòng${b.off?` · bớt ${x.fmt(b.off)}`:''} · tổng ${x.money(b.total)}`});
}
/** The counter list: open while picking, one line once the bill is closed. */
function counter(t,x,title){
  const card=`<section class="card ao-counter"><h4>${title}</h4>${picked(t,x)}</section>`;
  if(t.stage!=='pay')return card;
  return SF.part(x,t.id,new Set(),'counter',title,card,{done:true,sum:t.picks.map(p=>x.esc(item(x,p.item).name)).join(', ')||'quầy trống'});
}
function haggleBox(t,x){
  if(t.haggle!=='ask')return '';
  const b=t.bill,h=x.cc.haggle||{small:5,big:20};
  return `<div class="card ao-haggle"><p><b>${x.esc(x.npc(t.npc).display_name)}</b> đòi bớt giá. Chị Vy dặn: khách quen bớt tối đa ${h.small}%.</p>
    <div class="ao-3">${x.cmd('🙂 Giữ giá','ao_haggle',{task:t.id,answer:'hold'},'ghost')}${x.cmd(`🤏 Bớt ${h.small}% (−${Math.floor(b.sub*h.small/100)})`,'ao_haggle',{task:t.id,answer:'small'},'ghost')}${x.cmd(`💸 Bớt ${h.big}%`,'ao_haggle',{task:t.id,answer:'big'},'ghost')}</div></div>`;
}
function payBlock(t,x){
  if(t.stage!=='pay')return '';
  return `${receipt(t,x)}${haggleBox(t,x)}${t.cash?cashPanel(x,t.id,t.cash):''}
    <div class="row wrap">${x.cmd('↩︎ Mở lại bill','ao_unbill',{task:t.id},'small ghost')}</div>`;
}
/** Steps for the bill and the till (stage pay). */
function paySteps(t,x){
  const rows=[];
  if(t.haggle==='ask')rows.push({ok:null,label:'Trả lời khách chuyện bớt giá',go:{sel:'.ao-haggle'}});
  const ch=t.cash?changeStep(x,t.id,t.cash):null;if(ch)rows.push(ch);
  return rows;
}
function payFinal(t,x,steps){
  const cash=t.cash,given=cash?sum(tray(x,t.id,cash)):0,total=t.bill?.total||0;
  return {label:cash&&cash.due>0?`🛍️ Giao đồ · thối ${x.money(given)}`:`🛍️ Giao đồ · thu ${x.money(total)}`,
    go:finalGo(steps,'ao_pay',{task:t.id,...changePayload(x,t.id,cash)},{question:`Thu ${total} xu${cash&&cash.due>0?`, thối ${given} xu`:''}.`,confirm:true}),
    ready:t.haggle!=='ask'&&!!cash,why:'trả lời chuyện bớt giá'};
}
const billFinal=(t,x,ready)=>({label:'🧾 Chốt bill',go:{cmd:'ao_bill',payload:{task:t.id}},ready,why:'lấy đồ ra quầy'});

/* ------------------------------------------------------------ fit */
function lineMatches(t){
  const used=new Set();
  return t.needs.lines.map(l=>{const i=t.picks.findIndex((p,j)=>!used.has(j)&&p.item===l.item&&p.colour===l.colour);if(i>=0)used.add(i);return i;});
}
/** True when the rack already shows this line's item and colour, so the next move is a size. */
const onRackPick=(x,t,l)=>{const p=pickOf(x,t);return p.item===l.item&&p.colour===l.colour;};
function fitSteps(t,x){
  if(t.stage==='pay')return paySteps(t,x);
  const m=lineMatches(t),rows=t.needs.lines.map((l,k)=>{const i=m[k],it=item(x,l.item),tried=i>=0?t.tried[i]:null;
    if(i>=0&&(tried==='small'||tried==='big'))return {ok:false,label:`${it.emoji} ${it.name} ${tried==='small'?'chật':'rộng'}: đổi size`,go:{cmd:'ao_unpick',payload:{task:t.id,index:i},label:`↩︎ Treo lại size ${t.picks[i].size}`}};
    // The customer named their size ("Mình mặc size M"): another size on the counter is flagged at once.
    if(i>=0&&l.told&&tried!=='ok'&&t.picks[i].size!==l.told)return {ok:false,label:`${it.emoji} ${it.name}: khách nói size ${l.told}`,go:{cmd:'ao_unpick',payload:{task:t.id,index:i},label:`↩︎ Treo lại size ${t.picks[i].size}`}};
    return {ok:i>=0?true:null,label:`${it.emoji} ${it.name} · màu ${l.colour}`,note:i>=0?`đã lấy size ${t.picks[i].size}`:l.say.split('. ').slice(1).join('. '),
      go:i>=0?null:onRackPick(x,t,l)?{sel:'.ao-sizes',label:'👉 Chọn size trên giá treo'}:{act:'car:item',data:{task:t.id,item:l.item,colour:l.colour},label:`👉 Lấy ${x.esc(it.name.toLowerCase())} màu ${x.esc(l.colour)}`}};});
  const extra=t.picks.length-m.filter(i=>i>=0).length;
  if(extra>0)rows.push({ok:false,label:'Trên quầy có món khách không hỏi',go:{sel:'.ao-picked'}});
  return rows;
}
function fitJob(t,x){
  const shelf=t.stage==='pick'?`${rack(t,x)}${sizeChart(x)}`:'';
  // Every asked line is on the counter: the counter (and any extra item to put back) comes before the rack.
  if(t.picks.length&&lineMatches(t).every(i=>i>=0))return `${counter(t,x,'🛍️ Trên quầy')}${shelf}${payBlock(t,x)}`;
  return `${shelf}${counter(t,x,'🛍️ Trên quầy')}${payBlock(t,x)}`;
}

/* ------------------------------------------------------------ outfit */
function isSet(t,x){
  const items=t.picks.map(p=>p.item),grp=x.cc.groups||{};
  return items.some(i=>grp[i]==='one')||(items.some(i=>grp[i]==='top')&&items.some(i=>grp[i]==='bottom'));
}
const outfitWrong=(t,x)=>{const n=t.needs;return t.picks.find(p=>p.item==='jeans'?p.size!==n.waist:!FREE.includes(p.item)&&p.item!=='kids'&&sizes(x,p.item).includes(n.top)&&p.size!==n.top);};
function outfitSteps(t,x){
  if(t.stage==='pay')return paySteps(t,x);
  const n=t.needs,items=t.picks.map(p=>p.item),grp=x.cc.groups||{};
  const set=isSet(t,x);
  const total=sum(t.picks.map(p=>price(x,p.item)));
  const wrongSize=outfitWrong(t,x);
  // One action at a time: first a top or a one-piece for the occasion, then trousers to go with the top.
  const top=items.some(i=>grp[i]==='top'),one=items.some(i=>grp[i]==='one');
  const pick=set?{ok:true,label:'Một bộ hoàn chỉnh: váy/áo dài, hoặc áo + quần'}
    :top?{ok:null,label:'Chọn quần hợp với áo',note:'một bộ: áo + quần',go:{sel:'.ao-rack .ao-chip.g-bottom',label:'👖 Chọn quần hợp với áo'},pulse:''}
    :{ok:null,label:'Chọn áo hoặc váy hợp dịp',note:'một bộ: váy/áo dài, hoặc áo + quần',go:{sel:'.ao-rack .ao-chip.g-one,.ao-rack .ao-chip.g-top',label:'👗 Chọn áo hoặc váy hợp dịp'},pulse:''};
  return [
    pick,
    {ok:!t.picks.length?null:wrongSize?false:true,label:`Đúng size khách nói: áo ${n.top}, quần ${n.waist}`,note:wrongSize?`${item(x,wrongSize.item).name} đang size ${wrongSize.size}`:'',go:wrongSize?{cmd:'ao_unpick',payload:{task:t.id,index:t.picks.indexOf(wrongSize)},label:'↩︎ Treo lại món sai size'}:null},
    {ok:!t.picks.length?null:total<=n.budget?true:false,label:`Trong ngân sách ${n.budget} xu`,note:`đang ${total} xu`},
  ];
}
function outfitJob(t,x){
  const o=x.cc.occasions?.[t.needs.occasion]||{},total=sum(t.picks.map(p=>price(x,p.item))),pct=Math.min(100,total/t.needs.budget*100);
  const items=t.picks.map(p=>p.item),grp=x.cc.groups||{},top=items.some(i=>grp[i]==='top'),set=items.some(i=>grp[i]==='one')||(top&&items.some(i=>grp[i]==='bottom'));
  // One row: the occasion and the budget bar; under it what the occasion needs (the shop checks it at the
  // counter), open while picking, folded after (data-auto: the render decides).
  return `<section class="card ao-occasion compact"><div class="row"><span class="ao-big" aria-hidden="true">${x.esc(o.emoji||'👗')}</span><div class="grow"><h4>${x.esc(o.name||'')}</h4>
    <div class="ao-budget"><small>Ngân sách</small><div class="bar ${total>t.needs.budget?'low':''}"><i style="width:${pct}%"></i></div><b class="${total>t.needs.budget?'bad':''}">${x.fmt(total)}/${x.fmt(t.needs.budget)}</b></div></div></div>
    ${(o.tips||[]).length?`<details class="ao-tipfold" data-auto${t.stage==='pick'?' open':''}><summary>💡 Dịp này cần</summary><ul class="small ao-tips">${o.tips.map(v=>`<li>${x.esc(v)}</li>`).join('')}</ul></details>`:''}</section>
    ${t.stage==='pick'?rack(t,x,'pick',set?'':top?'bottom':'top'):''}${counter(t,x,'🛍️ Bộ đồ đang phối')}${payBlock(t,x)}`;
}

/* ------------------------------------------------------------ alterations */
function alterSteps(t,x){
  const a=t.alt,id=t.id;
  if(t.stage==='pay')return paySteps(t,x);
  const rows=[{ok:a.measured||null,label:'Đo trên người khách',go:a.measured?null:{cmd:'ao_measure',payload:{task:id},label:'📏 Đo cho khách'}}];
  if(!a.measured)return rows;
  if(t.stage==='measure')rows.push({ok:null,label:'Tự may hoặc gửi Bà Tư',go:{sel:'.ao-choice'}});
  if(t.stage==='sew')rows.push({ok:null,label:'Đạp máy, dừng đúng vạch xanh',go:a.start?{cmd:'ao_sew_stop',payload:{task:id},label:'✋ Dừng máy!'}:{cmd:'ao_sew_start',payload:{task:id},label:'🧵 Đạp máy may'}});
  if(t.stage==='wait'){const left=Math.max(0,(t.ready_turn||0)-(x.room.turn||0));
    rows.push({ok:null,label:'Nhận đồ Bà Tư may xong',note:left>0?`Bà Tư còn may, làm việc khác chút (${left} nhịp)`:'',go:left>0?null:{cmd:'ao_alter_collect',payload:{task:id},label:'👵 Nhận đồ từ Bà Tư'}});}
  return rows;
}
function alterJob(t,x){
  const a=t.alt,n=t.needs,g=item(x,n.garment),id=t.id,job=n.job==='hem'?'Lai quần':'Bóp eo';
  const cm=Math.max(1,Math.min(10,Number((x.ui.cm||{})[id]??a.cm??3)));
  let body='';
  if(!a.measured)body=`<p class="small">Mời khách mặc thử để đo và ghim kim trước.</p>`;
  else if(t.stage==='measure')body=`<p class="ao-measure">📏 Số đo: <b>${a.cm} cm</b> cần ${n.job==='hem'?'cắt lên':'bóp vào'}</p>
    <div class="ao-choice"><div class="card ao-opt"><h5>✂️ Tự may</h5><p class="small">Chọn số cm rồi ngồi vào máy. Công trọn ${n.fee} xu, nhưng lỡ tay là khách buồn.</p>
      <div class="ao-step" role="group" aria-label="Số cm"><button type="button" class="btn ghost" data-action="car:cm" data-task="${x.esc(id)}" data-d="-1" aria-label="Bớt 1 cm">−</button><b>${cm} cm</b><button type="button" class="btn ghost" data-action="car:cm" data-task="${x.esc(id)}" data-d="1" aria-label="Thêm 1 cm">+</button></div>
      ${x.cmd(`✂️ Phấn ${cm} cm & ngồi máy`,'ao_alter_self',{task:id,cm},'primary full')}</div>
    <div class="card ao-opt"><h5>👵 Gửi Bà Tư</h5><p class="small">Chắc tay, đẹp đường may. Chờ một lát, bà lấy ${x.cc.tailor_share||40}% tiền công.</p>${x.cmd('👵 Mang sang gian bên','ao_alter_send',{task:id},'ghost full')}</div></div>`;
  else if(t.stage==='sew'){const z=t.sew?.zone||[.7,.92];
    body=`<p class="small">Phấn ${a.cut} cm. Kim chạy dọc đường may — dừng máy khi kim nằm trong vạch xanh.</p>
      <div class="ao-sew" data-ao-sew="1" data-start="${a.start||0}" data-sec="${t.sew?.seconds||4}" data-lo="${z[0]}" data-hi="${z[1]}"><div class="ao-seam"><i class="ao-zone" style="left:${z[0]*100}%;width:${(z[1]-z[0])*100}%"></i><i class="ao-needle" style="left:0%"></i></div><small class="ao-sew-label">${a.start?'Máy đang chạy…':'Sẵn sàng'}</small></div>
      ${a.start?x.cmd('✋ Dừng máy!','ao_sew_stop',{task:id},'primary big full ao-stop'):x.cmd('🧵 Đạp máy may','ao_sew_start',{task:id},'primary big full')}`;}
  else if(t.stage==='wait')body=`<p class="small">👵 Bà Tư đang may ở gian bên…</p>`;
  else if(t.stage==='ready')body=`<p class="small ao-ok">✓ Đã ${job.toLowerCase()} xong${a.seam==='crooked'?' (đường may hơi xiên)':''}. Tính tiền công cho khách.</p>`;
  return `<section class="card ao-alter"><h4>✂️ ${job} · ${x.esc(g.name)}</h4><p class="small muted">${x.esc(n.note)} Công ${n.fee} xu.</p>${body}</section>${payBlock(t,x)}`;
}

/* ------------------------------------------------------------ fitting room */
function roomSteps(t,x){
  const r=t.room,id=t.id,q=t.needs.queue;
  if(t.stage==='pay')return paySteps(t,x);
  if(t.stage==='room'){
    const i=r.i,k=String(i),who=x.npc(npcId(q[i].npc));
    const rows=q.map((c,j)=>j<i?{ok:!['lost','accused'].includes(r.res[String(j)])?true:false,label:`${x.npc(npcId(c.npc)).display_name} xong lượt thử`}:null).filter(Boolean);
    if(!(k in r.tags)&&!(k in r.outs))rows.push({ok:null,label:`Đếm đồ ${who.display_name} cầm vào, đưa thẻ số`,go:{sel:'.ao-tags'}});
    else if(!(k in r.outs))rows.push({ok:null,label:`${who.display_name} thử xong: đếm lại đồ`,go:{cmd:'ao_room_out',payload:{task:id},label:'🚪 Khách bước ra, đếm lại'}});
    else if(!r.checked.includes(i))rows.push({ok:null,label:'Thiếu món: kiểm phòng thử trước',go:{cmd:'ao_room_check',payload:{task:id},label:'🔍 Kiểm phòng thử'}});
    else rows.push({ok:null,label:'Phòng trống: hỏi khéo khách',go:{cmd:'ao_room_ask',payload:{task:id},label:'🙏 Hỏi khéo khách'}});
    return rows;
  }
  const b=t.needs.buy,has=t.picks.some(p=>p.item===b.item&&p.size===b.size&&p.colour===b.colour);
  return [{ok:true,label:'Phòng thử đã vãn'},{ok:has||null,label:`Lấy ${item(x,b.item).name.toLowerCase()} size ${b.size} màu ${b.colour}`,
    go:has?null:{cmd:'ao_pick',payload:{task:id,item:b.item,size:b.size,colour:b.colour},label:`👚 Lấy ${x.esc(item(x,b.item).name.toLowerCase())} size ${x.esc(b.size)}`}}];
}
const RES={ok:['green','✓ đủ đồ'],found:['green','✓ đồ để quên trên móc'],returned:['green','✓ khách trả lại'],lost:['danger','mất một món'],accused:['danger','nghi oan khách']};
function roomJob(t,x){
  const r=t.room,q=t.needs.queue,id=t.id;
  const cards=q.map((c,j)=>{const w=x.npc(npcId(c.npc)),k=String(j),cur=t.stage==='room'&&j===r.i,res=r.res[k];
    const hangers=`<span class="ao-hangers" aria-label="Cầm ${c.items} món">${'👚'.repeat(c.items)}</span>`;
    let act='';
    if(cur&&!(k in r.tags)&&!(k in r.outs))act=`<p class="ao-lab">Đưa thẻ số — khách cầm vào mấy món?</p><div class="ao-tags">${[1,2,3,4,5,6].map(n=>x.cmd(String(n),'ao_room_tag',{task:id,count:n},'ghost ao-tag')).join('')}</div>
      <button type="button" class="gd-alt" data-command="ao_room_out" data-payload="${x.esc(JSON.stringify({task:id}))}">hoặc cho vào luôn, khỏi thẻ</button>`;
    else if(cur&&!(k in r.outs))act=`<p class="small">🏷️ Thẻ số <b>${r.tags[k]}</b> · đang thử đồ…</p>${x.cmd('🚪 Khách bước ra, đếm lại','ao_room_out',{task:id},'primary full')}`;
    else if(cur)act=`<p class="small bad">Trả ${r.outs[k]} món, thẻ ghi ${r.tags[k]??'?'}.</p><div class="ao-3">${r.checked.includes(j)?'':x.cmd('🔍 Kiểm phòng','ao_room_check',{task:id},'primary')}${x.cmd('🙏 Hỏi khéo','ao_room_ask',{task:id},r.checked.includes(j)?'primary':'ghost')}${x.cmd('👋 Để khách đi','ao_room_let',{task:id},'ghost')}</div>`;
    const tag=res?`<span class="tag ${RES[res][0]}">${RES[res][1]}</span>`:cur?'<span class="tag amber">Đang tới lượt</span>':j>r.i?'<span class="tag">Đang chờ</span>':'';
    return `<article class="ao-guest${cur?' cur':''}">${x.portrait(w,40)}<div class="grow"><div class="row spread wrap"><b>${x.esc(w.display_name)}</b>${tag}</div>${hangers}${act}</div></article>`;}).join('');
  const buyCard=`<section class="card ao-counter"><h4>🛍️ ${x.esc(x.npc(t.npc).display_name)} mua</h4><p class="ao-said">“${x.esc(t.needs.buy.say)}”</p>${picked(t,x)}</section>`;
  const buy=t.stage!=='room'?`${t.stage==='pay'?SF.part(x,t.id,new Set(),'counter',`🛍️ ${x.esc(x.npc(t.npc).display_name)} mua`,buyCard,{done:true,sum:t.picks.map(p=>x.esc(item(x,p.item).name)).join(', ')}):buyCard}${t.stage==='pick'?rack(t,x):''}${payBlock(t,x)}`:'';
  return `<section class="card ao-room"><h4>🚪 Phòng thử <small class="muted">(rèm ${t.stage==='room'?'đang kéo':'mở'})</small></h4><div class="ao-queue">${cards}</div></section>${buy}`;
}

/* ------------------------------------------------------------ returns */
const FACT_LABEL={tag:['🏷️','Xem tem mác'],receipt:['🧾','Xem hóa đơn'],wear:['🔍','Xem tình trạng đồ']};
function returnSteps(t,x){
  return [...Object.entries(FACT_LABEL).map(([k,[e,l]])=>({ok:t.ret.seen.includes(k)||null,label:l,go:t.ret.seen.includes(k)?null:{cmd:'ao_inspect',payload:{task:t.id,what:k},label:`${e} ${l}`}})),
    {ok:null,label:'Đối chiếu chính sách rồi quyết',go:{sel:'.ao-decide'}}];
}
function returnJob(t,x){
  const n=t.needs,it=item(x,n.item),id=t.id,ns=(x.ui.ns||{})[id]||n.new_size||n.size,tone=(x.ui.tone||{})[id]||'calm';
  const facts=Object.entries(FACT_LABEL).map(([k,[e,l]])=>t.ret.seen.includes(k)?`<li class="ao-fact"><span aria-hidden="true">${e}</span><p>${x.esc(t.facts?.[k]||'')}</p></li>`
    :`<li class="ao-fact todo">${x.cmd(`${e} ${l}`,'ao_inspect',{task:id,what:k},'ghost full')}</li>`).join('');
  const sizesRow=sizes(x,n.item).map(s=>`<button type="button" class="ao-size sm${s===ns?' on':''}" data-action="car:ns" data-task="${x.esc(id)}" data-size="${x.esc(s)}" aria-pressed="${s===ns}"${free(x,n.item,s)<=0?' disabled':''}><b>${x.esc(sizeLabel(s))}</b><small>còn ${free(x,n.item,s)}</small></button>`).join('');
  return `<section class="card ao-return"><h4>🔁 ${x.esc(it.emoji)} ${x.esc(it.name)} · size ${x.esc(n.size)} · ${x.esc(n.colour)}</h4>
    <p class="small">Mua ${n.days_ago} ngày trước · ${x.fmt(n.price)} xu · khách muốn <b>${n.want==='exchange'?`đổi sang size ${x.esc(n.new_size||'')}`:'trả lấy tiền'}</b></p>
    <ul class="ao-facts">${facts}</ul>
    ${fold('📋 Chính sách đổi trả',`<ul class="small ao-tips">${(x.cc.policy||[]).map(v=>`<li>${x.esc(v)}</li>`).join('')}</ul>`,true)}</section>
    <section class="card ao-decide"><h4>Quyết định</h4>
      <p class="ao-lab">Đổi hàng · size mới</p><div class="ao-sizes">${sizesRow}</div>
      ${x.confirmCmd(`🔁 Đổi sang size ${x.esc(ns)}`,'ao_return_do',{task:id,choice:'exchange',new_size:ns,confirm:true},`Đổi cho khách sang size ${ns}?`,'ghost full')}
      ${x.confirmCmd(`💵 Hoàn ${x.fmt(n.price)} xu`,'ao_return_do',{task:id,choice:'refund',confirm:true},`Hoàn ${n.price} xu cho khách?`,'ghost full')}
      <p class="ao-lab">Từ chối · cách nói</p><div class="ao-2">${['calm','blunt'].map(v=>`<button type="button" class="btn small ${tone===v?'primary':'ghost'}" data-action="car:tone" data-task="${x.esc(id)}" data-tone="${v}" aria-pressed="${tone===v}">${v==='calm'?'🙂 Nhẹ nhàng, chỉ bảng':'😤 Nói thẳng'}</button>`).join('')}</div>
      ${x.confirmCmd('🙅 Từ chối đổi trả','ao_return_do',{task:id,choice:'refuse',tone,confirm:true},'Từ chối đổi trả cho khách?','ghost full')}</section>`;
}

/* ------------------------------------------------------------ sale tags */
function saleSteps(t,x){
  return t.needs.lines.map((l,i)=>({ok:String(i) in t.sale.tags||null,label:`Tem ${item(x,l.item).name}: giảm ${l.pct}%`,go:String(i) in t.sale.tags?null:{sel:`.ao-sale-line[data-line="${i}"]`}}));
}
function saleJob(t,x){
  const rows=t.needs.lines.map((l,i)=>{const it=item(x,l.item),base=t.sale.base?.[l.item]??price(x,l.item),got=t.sale.tags[String(i)];
    return `<div class="ao-sale-line" data-line="${i}"><div class="row spread"><b>${x.esc(it.emoji)} ${x.esc(it.name)}</b><span class="tag amber">−${l.pct}%</span></div>
      <p class="small muted">Giá gốc ${x.fmt(base)} xu · ${x.fmt(base)} × ${100-l.pct}% = ?</p>
      <div class="ao-4">${(t.sale.options[i]||[]).map(v=>`<button type="button" class="btn ${got===v?'primary':'ghost'}" data-command="ao_tag" data-payload="${x.esc(JSON.stringify({task:t.id,line:i,price:v}))}" aria-pressed="${got===v}">${x.fmt(v)}</button>`).join('')}</div></div>`;}).join('');
  return `<section class="card ao-sale"><h4>🏷️ Máy in tem sale</h4><p class="small">Làm tròn xuống. Tem thấp tiệm lỗ, tem cao khách phàn nàn.</p>${rows}</section>`;
}

/* ------------------------------------------------------------ online orders */
function packMatch(t){
  const used=new Set();
  return t.needs.lines.map(l=>{const i=t.parcel.items.findIndex((p,j)=>!used.has(j)&&p.item===l.item&&p.size===l.size&&p.colour===l.colour);if(i>=0)used.add(i);return i;});
}
function onlineSteps(t,x){
  const pc=t.parcel,m=packMatch(t),id=t.id;
  const rows=t.needs.lines.map((l,k)=>({ok:m[k]>=0||null,label:`${item(x,l.item).emoji} ${item(x,l.item).name} · size ${l.size} · ${l.colour}`,
    go:m[k]>=0?null:free(x,l.item,l.size)>0?{cmd:'ao_pack',payload:{task:id,item:l.item,size:l.size,colour:l.colour},label:`📦 Bỏ ${x.esc(item(x,l.item).name.toLowerCase())} size ${x.esc(l.size)} vào gói`}:onRackPick(x,t,l)?{sel:'.ao-rack',label:'👉 Nhập thêm hàng ở giá treo'}:{act:'car:item',data:{task:id,item:l.item,colour:l.colour},label:'👉 Xem giá treo'}}));
  const extra=pc.items.length-m.filter(i=>i>=0).length;
  if(extra>0)rows.push({ok:false,label:'Gói có món không đúng đơn',go:{sel:'.ao-parcel'}});
  rows.push({ok:pc.label?true:null,label:'In phiếu giao',go:pc.label||!pc.items.length?null:{cmd:'ao_label',payload:{task:id},label:'🖨️ In phiếu giao'}});
  rows.push({ok:pc.sealed||null,label:'Dán băng keo',go:pc.sealed||!pc.label?null:{cmd:'ao_seal',payload:{task:id},label:'📦 Dán băng keo'}});
  return rows;
}
function onlineJob(t,x){
  const n=t.needs,pc=t.parcel,id=t.id,app=n.channel==='zalo'?['💬','Zalo','zalo']:['📘','Facebook','fb'];
  const chat=`<div class="ao-chat ${app[2]}"><small>${app[0]} ${app[1]} · ${x.esc(x.npc(t.npc).display_name)}</small><p>${x.esc(t.opening)}</p><ul>${n.lines.map(l=>`<li>${dot(x,l.colour)}${x.esc(item(x,l.item).name)} · size <b>${x.esc(l.size)}</b> · ${x.esc(l.colour)}</li>`).join('')}</ul><p class="small">${x.esc(n.note)}</p></div>`;
  const items=pc.items.length?`<ul class="ao-picked">${pc.items.map((p,i)=>`<li>${dot(x,p.colour)}<span class="grow">${x.esc(pieceLabel(x,p))}</span>${pc.sealed?'':`<button type="button" class="btn small ghost ao-x" data-command="ao_unpack" data-payload="${x.esc(JSON.stringify({task:id,index:i}))}" aria-label="Lấy ra">✕</button>`}</li>`).join('')}</ul>`:'<p class="small muted ao-empty">Gói còn trống.</p>';
  const label=pc.label?`<div class="ao-label"><b>📮 ${x.esc(x.npc(t.npc).display_name)}</b><small>${x.esc(n.address)}</small><span>${pc.label.cod?`Thu hộ ${x.money(pc.label.cod)}`:'Đã thanh toán'}</span></div>`:'';
  return `<section class="card ao-online">${chat}</section>${pc.sealed?'':rack(t,x,'pack')}<section class="card ao-parcel"><h4>📦 Gói hàng ${pc.sealed?'<span class="tag green">đã dán</span>':''}</h4>${items}${label}
    <div class="row wrap">${pc.items.length&&!pc.sealed?x.cmd(pc.label?'🖨️ In lại phiếu':'🖨️ In phiếu giao','ao_label',{task:id},'small ghost'):''}${pc.label&&!pc.sealed?x.cmd('📦 Dán băng keo','ao_seal',{task:id},'small ghost'):''}</div></section>`;
}
const onlineFinal=(t,x,steps)=>({label:'🛵 Giao cho shipper',go:finalGo(steps,'ao_ship',{task:t.id},{question:'Shipper chạy luôn, không mở gói ra được nữa.',confirm:true}),ready:!!t.parcel.label,why:'in phiếu giao'});

/* ------------------------------------------------------------ mannequin */
function displaySteps(t,x){
  const dp=t.disp,id=t.id;
  const rows=[{ok:dp.pieces.length?true:null,label:'Mặc đồ hợp chủ đề lên ma-nơ-canh',go:dp.pieces.length?null:{sel:'.ao-rack'}}];
  dp.pieces.forEach((p,i)=>rows.push({ok:dp.steamed.includes(i)||null,label:`Hấp phẳng ${item(x,p.item).name.toLowerCase()}`,go:dp.steamed.includes(i)?null:{cmd:'ao_steam',payload:{task:id,index:i},label:`♨️ Hấp ${x.esc(item(x,p.item).name.toLowerCase())}`}}));
  return rows;
}
function mannequin(x,pieces,steamed=[],t=null){
  const body=pieces.length?pieces.map((p,i)=>`<li>${dot(x,p.colour)}<span class="grow">${x.esc(item(x,p.item).emoji)} ${x.esc(item(x,p.item).name)} · ${x.esc(p.colour)}</span>${steamed.includes(i)?'<span class="tag green">phẳng</span>':'<span class="tag amber">nhăn</span>'}
    ${t?`${steamed.includes(i)?'':x.cmd('♨️ Hấp','ao_steam',{task:t.id,index:i},'small ghost')}<button type="button" class="btn small ghost ao-x" data-command="ao_undress" data-payload="${x.esc(JSON.stringify({task:t.id,index:i}))}" aria-label="Cởi ra">✕</button>`:''}</li>`).join(''):'<li class="muted small">Ma-nơ-canh đang trống.</li>';
  return `<div class="ao-manq"><span class="ao-manq-fig" aria-hidden="true">🧍‍♀️</span><ul class="ao-picked">${body}</ul></div>`;
}
function displayJob(t,x){
  const o=x.cc.occasions?.[t.needs.theme]||{};
  return `<section class="card ao-occasion"><div class="row"><span class="ao-big" aria-hidden="true">${x.esc(o.emoji||'🧍‍♀️')}</span><div class="grow"><h4>Chủ đề: ${x.esc(o.name||'')}</h4><ul class="small ao-tips">${(o.tips||[]).map(v=>`<li>${x.esc(v)}</li>`).join('')}</ul></div></div></section>
    <section class="card ao-display"><h4>🧍‍♀️ Ma-nơ-canh cạnh cửa</h4>${mannequin(x,t.disp.pieces,t.disp.steamed,t)}</section>${rack(t,x,'dress')}`;
}
const displayFinal=(t,x,steps)=>({label:'✨ Trưng bày',go:finalGo(steps,'ao_display_done',{task:t.id},{question:'Khách đi ngang sẽ ngắm bộ này mấy ngày tới.',confirm:true}),ready:t.disp.pieces.length>0,why:'mặc đồ lên ma-nơ-canh'});
const saleFinal=(t,x,steps)=>({label:'🏷️ Treo tem sale',go:finalGo(steps,'ao_sale_done',{task:t.id},{question:'Tem sẽ được dùng ở quầy cả ngày hôm nay.',confirm:true}),ready:Object.keys(t.sale.tags).length===t.needs.lines.length,why:'in đủ tem'});

/* ------------------------------------------------------------ the order, pinned */
/** What the customer asked for, pinned under the header while picking (asm_kit): one chip per thing
 * the order needs, from the order's own fields (item, colour, the size clue they gave, the occasion's
 * rules, the budget), with a live ✓ / ✗. A chip still to find opens that item on the rack in the
 * colour asked. Return, sale, alteration and mannequin jobs keep their own panels. */
function pin(t,x,next){
  if(!t.known||t.stage==='done')return '';
  const id=t.id,chips=[],it=i=>item(x,i),live=t.stage==='pick'||t.kind==='online'&&!t.parcel.sealed;
  const find=(i,c)=>live?`data-action="car:item" data-task="${x.esc(id)}" data-item="${x.esc(i)}"${c?` data-colour="${x.esc(c)}"`:''}`:'';
  const clue=l=>l.ask||l.say.split('. ').slice(1).join('. ').replace(/\.$/,'');
  if(t.kind==='fit'){
    const m=lineMatches(t);
    t.needs.lines.forEach((l,k)=>{const i=m[k],tried=i>=0?t.tried[i]:null,off=i>=0&&l.told&&tried!=='ok'&&t.picks[i].size!==l.told,bad=tried==='small'||tried==='big'||off;
      chips.push({ok:i<0?null:!bad,icon:it(l.item).emoji,title:l.say,act:i<0?find(l.item,l.colour):'',
        text:`${it(l.item).name} · ${l.colour} · ${i<0?clue(l):`size ${t.picks[i].size}${off?` · khách nói ${l.told}`:bad?(tried==='small'?' chật':' rộng'):tried==='ok'?' vừa':''}`}`});});
    const extra=t.picks.length-m.filter(i=>i>=0).length;
    if(extra>0)chips.push({ok:false,icon:'➖',text:`${extra} món khách không hỏi`});
  }else if(t.kind==='outfit'){
    const n=t.needs,o=x.cc.occasions?.[n.occasion]||{},have=new Set(t.picks.map(p=>p.item)),any=t.picks.length>0;
    const total=sum(t.picks.map(p=>price(x,p.item))),wrong=outfitWrong(t,x);
    chips.push({info:true,ok:null,icon:o.emoji||'👗',text:o.name||''});
    chips.push({ok:isSet(t,x)||null,icon:'👗',text:'Một bộ: váy/áo dài, hoặc áo + quần'});
    chips.push({ok:!any?null:!wrong,icon:'📏',text:`Áo ${n.top} · quần ${n.waist}${wrong?` · ${it(wrong.item).name} đang ${wrong.size}`:''}`});
    for(const i of o.need||[])chips.push({ok:have.has(i)||null,icon:it(i).emoji,text:it(i).name,act:have.has(i)?'':find(i)});
    if((o.bad||[]).length)chips.push({info:true,ok:null,icon:'🚫',text:`Tránh màu ${o.bad.join(', ')}`});
    chips.push({ok:!any?null:total<=n.budget,icon:'💰',text:`Tối đa ${x.fmt(n.budget)} xu · đang ${x.fmt(total)}`});
  }else if(t.kind==='online'){
    const m=packMatch(t),n=t.needs;
    n.lines.forEach((l,k)=>chips.push({ok:m[k]>=0||null,icon:it(l.item).emoji,text:`${it(l.item).name} · size ${l.size} · ${l.colour}`,act:m[k]>=0?'':find(l.item,l.colour)}));
    const extra=t.parcel.items.length-m.filter(i=>i>=0).length;
    if(extra>0)chips.push({ok:false,icon:'➖',text:`${extra} món không đúng đơn`});
    chips.push({info:true,ok:null,icon:n.pay==='cod'?'💵':'✅',text:n.pay==='cod'?'Thu hộ khi giao':'Đã chuyển khoản'});
  }else if(t.kind==='room'&&t.stage!=='room'){
    const b=t.needs.buy,has=t.picks.some(p=>p.item===b.item&&p.size===b.size&&p.colour===b.colour);
    chips.push({ok:has||null,icon:it(b.item).emoji,text:`${it(b.item).name} · size ${b.size} · ${b.colour}`,act:has?'':find(b.item,b.colour)});
  }else return '';
  if(t.stage==='pay'&&!chips.some(c=>c.ok===false))return '';   // at the till the bill says it all
  const who=x.npc(t.npc);
  return reqPin(x,{sub:x.esc(who.display_name),chips,key:id,next});
}

/* ------------------------------------------------------------ the guide */
const STEPS={fit:fitSteps,outfit:outfitSteps,alter:alterSteps,room:roomSteps,return:returnSteps,sale:saleSteps,online:onlineSteps,display:displaySteps};
const ASK={fit:'Nghe khách tả size',outfit:'Hỏi khách đi dịp gì',alter:'Xem đồ cần sửa',room:'Ra trông phòng thử',return:'Nghe khách đổi trả',sale:'Nghe chị Vy dặn',online:'Mở tin nhắn đặt hàng',display:'Nghe chị Vy dặn'};
function taskGuide(t,x){
  if(!t.known)return {steps:[{ok:null,label:ASK[t.kind]||'Nghe khách',go:{cmd:'ask',payload:{task:t.id},label:'👂 '+(ASK[t.kind]||'Nghe khách')}}],final:null};
  const steps=(STEPS[t.kind]||(()=>[]))(t,x);
  let final=null;
  if(t.stage==='pay')final=payFinal(t,x,steps);
  else if(['fit','outfit'].includes(t.kind)||(t.kind==='room'&&t.stage==='pick'))final=billFinal(t,x,t.picks.length>0);
  else if(t.kind==='alter'&&t.stage==='ready')final=billFinal(t,x,true);
  else if(t.kind==='online')final=onlineFinal(t,x,steps);
  else if(t.kind==='display')final=displayFinal(t,x,steps);
  else if(t.kind==='sale')final=saleFinal(t,x,steps);
  return {steps,final};
}
function hintFor(g,x){
  const f=g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/<[^>]*>/g,'').replace(/^[^\p{L}]+/u,''),go:g.final.go}:null;
  const steps=f&&!pending(g.steps)?.go?g.steps.filter(s=>s.ok===true||s.go):g.steps;
  return nextHint(x,steps,{final:f});
}
const bottomBar=(g,x)=>g.final?`<div class="ao-bar">${nextLine(x,pending(g.steps),g.final.ready!==false?'đủ rồi, bấm nút dưới':'')}${stepCta(x,g.steps,g.final)}</div>`:'';

/* ------------------------------------------------------------ between customers */
function swapCards(x){
  const rows=data(x).swaps_due||[];if(!rows.length)return '';
  return `<section class="card ao-swaps"><h4>🔁 Khách quay lại đổi size</h4>${rows.map(s=>`<article class="ao-swap">${x.portrait(x.npc(s.npc),40)}<div class="grow"><b>${x.esc(s.name)}</b>
    <p class="small">${x.esc(item(x,s.item).name)} ${x.esc(s.colour)}: lấy size ${x.esc(s.wrong)} về mặc không vừa, cần size <b>${x.esc(s.right)}</b>.</p>
    <div class="ao-2">${x.cmd(`🔁 Đổi size ${x.esc(s.right)}`,'ao_swap',{id:s.id,mode:'swap'},'primary',!s.can_swap)}${x.confirmCmd(`💵 Hoàn ${x.fmt(s.price)} xu`,'ao_swap',{id:s.id,mode:'refund'},`Hoàn ${s.price} xu cho khách?`,'ghost')}</div>
    ${s.can_swap?'':`<p class="small bad">Giá treo hết size ${x.esc(s.right)}.</p>${restockButton(x.room,[{id:s.item,need:3}],{},'small ghost')}`}</div></article>`).join('')}</section>`;
}
function lookCard(x){
  const l=data(x).look_view;if(!l)return '';
  const stages=(x.cc.looks||[]).map((v,i)=>`<i class="${i<=l.stage?'on':''}" title="${x.esc(v.name)}"></i>`).join('');
  return `<section class="card ao-look"><div class="row spread wrap"><h4>🪡 ${x.esc(l.name)}</h4><div class="ao-pips" aria-label="Tiệm đang ở giai đoạn ${l.stage+1}/${(x.cc.looks||[]).length}">${stages}</div></div>
    <p class="small">${x.esc(l.text)}</p>${l.next?`<p class="small muted">Phục vụ thêm ${l.next.left} khách → ${x.esc(l.next.name)}</p>`:''}
    ${carBtn(x,'ℹ️ Giới thiệu nghề','intro',{},'small ghost')}</section>`;
}
function careCard(x){
  const rows=data(x).care||[];if(!rows.length)return '';
  return `<section class="card ao-care"><h4>📋 Việc chăm tiệm</h4>${reqList(rows.map(r=>({ok:r.ok,icon:r.icon,label:r.label})),x.esc,'Việc chăm tiệm')}</section>`;
}
function gridCard(x){
  const inv=x.room.inventory||{},cap=inv.capacity||30,on=inv.arriving||{};
  const rows=catalogue(x).map(it=>{const total=sizes(x,it.id).reduce((s,z)=>s+onRack(x,it.id,z),0),out=sizes(x,it.id).some(z=>onRack(x,it.id,z)<=0);
    return `<li class="ao-grow${out?' short':''}"><span class="ao-gname"><span aria-hidden="true">${x.esc(it.emoji)}</span>${x.esc(it.name)}<small>${total}/${cap}${on[it.id]?` · 🚚 +${on[it.id]}`:''}</small></span>
      <span class="ao-gsizes">${sizes(x,it.id).map(z=>`<span class="ao-gs${onRack(x,it.id,z)<=0?' out':onRack(x,it.id,z)<=1?' low':''}"><b>${x.esc(z==='F'?'F':z)}</b>${onRack(x,it.id,z)}</span>`).join('')}</span>
      ${out?restockButton(x.room,[{id:it.id,need:6}],{},'small ghost'):''}</li>`;}).join('');
  return `<section class="card ao-grid"><h4>👚 Giá treo theo size</h4><ul>${rows}</ul><p class="small muted">Hàng nhập về tự chia size bán chạy trước (M, L…).</p></section>`;
}
function bookCard(x){
  const rows=data(x).book_view||[];
  const body=rows.length?`<ul class="ao-bookl">${rows.map(r=>`<li>${x.portrait(x.npc(r.npc),32)}<span class="grow"><b>${x.esc(r.name)}</b><small>${[r.top?`áo ${r.top}`:'',r.waist?`quần ${r.waist}`:'',(r.kid||[]).length?`bé ${r.kid.join(', ')}`:''].filter(Boolean).map(x.esc).join(' · ')}</small></span><small>${r.visits} lần</small></li>`).join('')}</ul>`
    :'<p class="small muted">Bán vừa size cho khách quen, tiệm sẽ nhớ size của họ ở đây.</p>';
  return `<section class="card ao-bookc"><h4>📒 Sổ size khách quen</h4>${body}</section>`;
}
function windowCard(x){
  const d=data(x).display_view;if(!d)return '';
  return `<section class="card ao-display"><div class="row spread wrap"><h4>🧍‍♀️ Ma-nơ-canh</h4><span class="tag ${d.fresh?'green':'amber'}">${d.fresh?'★'.repeat(d.score)+' đang hút khách':'đã cũ, nên thay'}</span></div>${mannequin(x,d.pieces,d.pieces.map((_,i)=>i))}</section>`;
}

export default {
  id:ID,
  css:true,
  next(t,x){
    try{const n=x&&pending(taskGuide(t,x).steps);if(n)return x.esc(stepLine(n));}catch{/* fall back below */}
    if(!t.known)return ASK[t.kind]||'Nghe khách';
    return t.stage==='pay'?'Thối tiền và giao đồ':'Làm tiếp việc đang dở';
  },
  job(t,x){
    const g=taskGuide(t,x);
    // On a task the intro is one line (open it to read, "Vào ca thôi!" inside marks it read); ❔ in the dock opens it.
    const intro=x.ui.intro?introCard(x,!data(x).intro):!data(x).intro?introFold(x):'';
    if(t.known)SF.opened(x,t.id);
    if(!t.known){
      const w=x.npc(t.npc),kind=x.cc.kinds?.[t.kind]||t.kind;
      return `<div class="career-job ao">${hintFor(g,x)}${intro}${todayStrip(x)}<article class="card ticket ao-ticket"><div class="row">${x.portrait(w,56)}<div class="grow"><div class="row spread wrap"><h3>${x.esc(w.display_name)}</h3><span class="tag">${KIND_ICON[t.kind]||''} ${x.esc(kind)}</span></div><p class="small"><b>${x.esc(t.title)}</b></p><p>“${x.esc(t.opening)}”</p></div></div>
        ${x.cmd('👂 '+(ASK[t.kind]||'Nghe khách'),'ask',{task:t.id},'primary full gd-cta')}</article>${swapCards(x)}</div>`;
    }
    const body={fit:fitJob,outfit:outfitJob,alter:alterJob,room:roomJob,return:returnJob,sale:saleJob,online:onlineJob,display:displayJob}[t.kind]||(()=>'');
    // The checklist sits under the work (the bottom bar and the header already show the next step).
    const k=g.steps.filter(s=>s&&s.ok!==true).length;
    const list=g.steps.length?`<details class="card ao-steps"><summary>📝 Việc cần làm <small>· ${k?`còn ${k}`:'xong hết'}/${g.steps.length}</small></summary>${stepRows(x,g.steps)}</details>`:'';
    return `<div class="career-job ao">${hintFor(g,x)}${intro}${ticket(t,x)}${pin(t,x,pending(g.steps)||finalStep(g.final))}${body(t,x)}${list}${bottomBar(g,x)}</div>`;
  },
  idle(x){
    const tab=x.ui.tab||'rack';
    const tabs=`<div class="ao-tabs" role="tablist">${[['rack','👚 Giá treo'],['book','📒 Khách quen'],['window','🧍‍♀️ Cửa kính']].map(([k,l])=>`<button type="button" role="tab" class="btn small ${tab===k?'primary':'ghost'}" data-action="car:tab" data-tab="${k}" aria-selected="${tab===k}">${l}</button>`).join('')}</div>`;
    const body=tab==='book'?bookCard(x):tab==='window'?(windowCard(x)||'<p class="small muted card">Chưa trưng bộ nào. Chị Vy sẽ nhờ bạn thay đồ ma-nơ-canh.</p>'):gridCard(x);
    // After the first customer the unread intro is one line here too (it never blocks the shop).
    const served=(x.room.metrics?.served||0)>0&&!x.ui.intro;
    return `<div class="career-job ao ao-idle">${showIntro(x)?(served?introFold(x):introCard(x,true)):''}${todayStrip(x)}${swapCards(x)}${careCard(x)}${lookCard(x)}${tabs}${body}</div>`;
  },
  actions:{
    ...tillActions,
    ...SF.foldActions,
    ...asmActions,
    // A tap on what the order asks for comes with its colour: straight on to the sizes.
    async item(d,el,x){x.ui.pick={task:d.task,item:d.item,colour:d.colour||null};x.render();
      requestAnimationFrame(()=>document.querySelector(`.career-job.ao ${d.colour?'.ao-sizes':'.ao-swatches'}`)?.scrollIntoView({block:'center',behavior:'smooth'}));},
    async colour(d,el,x){const p=x.ui.pick;if(p&&p.task===d.task){p.colour=d.colour;x.render();}},
    async cm(d,el,x){const t=(x.room.tasks||[]).find(v=>v.id===d.task);if(!t)return;const m=(x.ui.cm??={});m[d.task]=Math.max(1,Math.min(10,Number(m[d.task]??t.alt?.cm??3)+Number(d.d)));x.render();},
    async ns(d,el,x){(x.ui.ns??={})[d.task]=d.size;x.render();},
    async tone(d,el,x){(x.ui.tone??={})[d.task]=d.tone==='blunt'?'blunt':'calm';x.render();},
    async tab(d,el,x){x.ui.tab=['rack','book','window'].includes(d.tab)?d.tab:'rack';x.render();},
    async intro(d,el,x){
      x.ui.intro=!x.ui.intro||!document.querySelector('dialog[open] .career-job.ao');
      if(document.querySelector('dialog[open] .career-job.ao'))x.render();
      else document.querySelector('#dock [data-action="workbench"],[data-action="workbench"]')?.click();
    },
  },
  tick(root,x){
    keepBarAboveFooter(root);
    pinTop(root);
    root.querySelectorAll('[data-ao-sew]').forEach(el=>{
      const start=Number(el.dataset.start);if(!start)return;
      const sec=Number(el.dataset.sec)||4,lo=Number(el.dataset.lo),hi=Number(el.dataset.hi),p=Math.max(0,(x.now()-start)/sec);
      const n=el.querySelector('.ao-needle');if(n)n.style.left=Math.min(100,p*100)+'%';
      el.classList.toggle('ready',p>=lo&&p<=hi);el.classList.toggle('over',p>hi);
      const l=el.querySelector('.ao-sew-label');if(l)l.textContent=p<lo?'Kim đang chạy… chưa tới vạch':p<=hi?'TRONG VẠCH — dừng ngay!':'Lố vạch rồi!';
    });
  },
  dock:[['inventory','box','Kho','Nhập hàng'],['car:intro','question','Giới thiệu nghề','Công việc & sao']],
};
