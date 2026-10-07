/** Tiệm album Mây Pop — chị Thơ's ZPOP album and fan-goods shop on Phố chợ (server: game/careers/zpop.py).
 * The morning (count the limited copies, the limit sign, the demo lightstick, the pre-order deadline), then each
 * customer: their words, the shelves (albums by version, lightsticks and the small things), the counter (the basket,
 * Zchart, the poster tube, fansign entries, POB) and the till. An annoying customer brings a decision card: ask, then
 * answer; the other side decides by itself (a hidden trait on the server). A case (a refund, a fake lightstick, pairing,
 * consignment) is only that card. Groups, albums and goods are fiction (zpop_content.py). The server decides
 * everything; one tap sends one command. */
import {stepRows,nextHint,finalGo,pending,stepLine,firstTime} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {cashPanel,changeStep,changePayload,tillActions} from './till.js';
import {data,cc,act,introCard,deskCard,dayBar,person,askCard,bottom,kitActions,amountBox,kitInput,tip,clean} from './street_kit.js';
import {whyAttrs,withWhy} from '../ui-kit.js';

const TABS=[['album','💿 Album'],['merch','🔨 Phụ kiện'],['desk','🧾 Quầy']];
const OPTS=[['zchart','🧾','Quét Zchart'],['tube','🧻','Ống poster'],['raffle','🎟️','Phiếu fansign'],['pob','🎁','POB']];
const need=t=>t.needs||{};
const skus=x=>cc(x).skus||[];
const SKU=(x,k)=>skus(x).find(s=>s.id===k)||{id:k,name:k,short:k,emoji:'💿',price:0};
const stockOf=(x,k)=>Number(data(x).stock?.[k]??x.room.inventory?.stock?.[k]??0);
const priceOf=(x,k)=>Number(x.room?.life?.prices?.[k]??SKU(x,k).price??0);
const cartN=t=>Object.values(t.cart||{}).reduce((s,v)=>s+Number(v||0),0);
const limited=(x,line)=>(line.any||[]).some(k=>SKU(x,k).limited);
/** What a product says about itself in one tag: the cue a customer's words point at. */
function cue(x,s){
  const c=clean(),lim=data(x).mod?.limit||3;
  if(s.member)return c?'🃏':`🃏 chắc card ${s.tag||s.short}`;
  if(s.nocd)return c?'🚫 CD':'🚫 không CD';
  if(s.limited)return c?`🚫 ≤${lim}`:`🚫 tối đa ${lim}/người`;
  if(s.opened)return c?'':'📭 đã khui';
  if(s.bt)return c?'📶 AA':'📶 Bluetooth · pin AA';
  if(s.pin==='pin_aaa')return c?'🔋 AAA':'🔋 pin AAA';
  if(s.poster)return c?'':'🎲 card ngẫu nhiên';
  return '';
}
/** The tile's name: the version alone on the clean layout (the shelf heading names the album); the full name is the label. */
const nameOf=s=>clean()?(s.tag??s.short):s.short;   // '' for an album with one version: its shelf heading names it
/** A shelf's legend on the clean layout: what the tiles' icons mean (deciding: which version is sure of a card). */
const LEGEND={ps:'🃏 = chắc',gm:'🚫 CD = không đĩa',stick:'📶 Bluetooth'};

/* ------------------------------------------------------------ how far a basket meets an order (mirrors zpop.py ring_slips) */
function lineState(x,t){
  const n=need(t),left={...(t.cart||{})},lim=n.limit,nolimit=!!t.tw?.nolimit;
  return (n.lines||[]).map(line=>{
    let got=0;for(const k of line.any){const take=Math.min(left[k]||0,line.qty-got);left[k]=(left[k]||0)-take;got+=take;}
    let want=line.qty;
    if(n.upto)want=Math.min(want,line.any.reduce((s,k)=>s+stockOf(x,k),0));
    if(lim&&!nolimit&&limited(x,line))want=Math.min(want,lim);
    return {line,got,want,ok:got>=want};
  }).map((r,i,all)=>i===all.length-1?{...r,left}:r);
}
function extras(x,t){
  const rows=lineState(x,t),left=rows.length?rows[rows.length-1].left:{...(t.cart||{})};
  return Object.entries(left).filter(([,q])=>q>0).map(([k])=>k);
}
function overLimit(x,t){
  const lim=need(t).limit;if(!lim||t.tw?.nolimit)return null;
  return Object.entries(t.cart||{}).find(([k,q])=>SKU(x,k).limited&&q>lim)?.[0]||null;
}

/* ------------------------------------------------------------ the customer */
function ticket(t,x){
  if(!t.known)return askCard(x,t,'👂 Hỏi khách cần gì');
  const n=need(t),opt=t.opt||{};
  const chip=(ok,s,label='')=>`<span class="zp-chip ${ok?'ok':''}"${label?` aria-label="${x.esc(label)}"`:''}>${s}</span>`;
  let chips='';
  if(t.kind==='sale'){
    if(n.hidden)chips=`${chip(false,'📝 Bé dặn gì? Xin giấy nhắn')}${n.guess?chip(false,`👉 Cô chỉ: ${x.esc(n.guess)}`):''}`;
    else{
      chips=lineState(x,t).map(r=>chip(r.ok,`${r.line.qty>1&&!/^\d/.test(r.line.label)?`${r.line.qty}× `:''}${x.esc(r.line.label)}${r.want<r.line.qty?` <small>(bán ${r.want})</small>`:''}`)).join('');
      chips+=OPTS.filter(([k])=>n[k]).map(([k,e,l])=>chip(!!opt[k],clean()?`${e} ${l.split(" ").pop()}`:`${e} ${l}`)).join('');
    }
    if((n.lines||[]).some(l=>limited(x,l)))chips+=chip(!overLimit(x,t),`🚫 tối đa ${n.limit}/người`,'Giới hạn bản giới hạn mỗi người');
  }
  const note=n.note?(n.tw==='parent'||!clean()?`<p class="zp-note small">${x.esc(n.note)}</p>`:tip(x.esc(n.note),'Khách dặn thêm','p')):'';
  // Clean layout: the ask's lines are the chips (the customer's own words, shortened); the whole sentence goes to "?".
  const say=n.say||t.opening||'';
  const quote=clean()&&chips&&!n.hidden?tip(x.esc(`“${say}”`),'Khách nói','p'):`<p class="zp-say">“${x.esc(say)}”</p>`;
  return person(x,t,`${quote}${chips?`<p class="zp-chips">${chips}</p>`:''}${note}`);
}

/* ------------------------------------------------------------ the annoying ones: ask, then answer */
function twCard(t,x){
  const w=t.tw;if(!w)return '';
  if(w.done){
    if(!w.out)return '';
    return `<div class="sk-last ${w.q==='good'?'good':w.q==='bad'?'bad':''} zp-tw-done" role="status"><span aria-hidden="true">${x.esc(w.emoji)}</span><p>${x.esc(w.out)}</p></div>`;
  }
  const probes=w.probes.map(p=>p.asked?`<li class="zp-fact"><b>${x.esc(p.label.replace(/^\S+\s/,''))}</b> ${x.esc(p.text||'')}</li>`
    :`<li>${x.cmd(x.esc(p.label),'zp_probe',{task:t.id,probe:p.id},'small ghost zp-probe')}</li>`).join('');
  const answers=w.answers.map(a=>x.cmd(`<span class="sk-opt-label">${x.esc(a.label)}</span>`,'zp_ans',{task:t.id,answer:a.id},'sk-opt zp-ans')).join('');
  return `<section class="sk-event tense zp-tw" role="group" aria-label="${x.esc(w.title)}"><div class="sk-ev-head"><span aria-hidden="true">${x.esc(w.emoji)}</span><div><small>Khách khó</small><h3>${x.esc(w.title)}</h3></div></div>
    ${w.push?`<p class="zp-push">${x.esc(w.push)}</p>`:''}${w.tries?`<p class="small muted">Đã thử ${w.tries} cách, chưa được.</p>`:''}
    ${probes?`<ul class="zp-probes">${probes}</ul>`:''}${answers?`<div class="sk-opts">${answers}</div>`:''}</section>`;
}

/* ------------------------------------------------------------ the shelves */
function tileFor(t,x,s){
  const left=stockOf(x,s.id),inCart=Number(t.cart?.[s.id]||0),free=left-inCart;
  const can=free>0?true:{why:left?`Đã lấy hết ${left} ${s.short} trên kệ.`:`Kệ hết ${s.short}. Nhập thêm ở Kho.`,fix:{act:'inventory',label:'📦 Kho'}};
  const why=whyAttrs(can);
  const tag=cue(x,s);
  return `<button type="button" class="tile sk-tile zp-tile ${inCart?'selected':''}${why?' is-why':''}" data-command="zp_add" data-payload="${x.esc(JSON.stringify({task:t.id,sku:s.id}))}" aria-label="${x.esc(`${s.name} · ${priceOf(x,s.id)} xu · còn ${left}`)}"${why}>
    <span class="tile-emoji" aria-hidden="true">${x.esc(s.emoji)}</span><b>${x.esc(nameOf(s))}</b><small>${priceOf(x,s.id)}${clean()?'':' xu'} · 📦 ${left}</small>${tag?`<em class="zp-cue">${x.esc(tag)}</em>`:''}${inCart?`<span class="zp-badge">${inCart}</span>`:''}</button>`;
}
function albumPanel(t,x){
  const albums=cc(x).albums||{},groups=cc(x).groups||{};
  return Object.entries(albums).map(([aid,a])=>{
    const g=groups[a.group]||{},list=skus(x).filter(s=>s.album===aid&&!s.service);
    const sub=clean()?(LEGEND[aid]||''):`${g.name||''} · ${a.kind}`;
    return `<section class="zp-shelf" data-zp-shelf="${x.esc(aid)}"><h4 class="section-title">${x.esc(a.emoji)} ${x.esc(a.name)} <small class="muted">${x.esc(sub)}</small></h4>
      <div class="tile-grid zp-tiles">${list.map(s=>tileFor(t,x,s)).join('')}</div></section>`;
  }).join('');
}
function merchPanel(t,x){
  const part=(fam,title)=>{const list=skus(x).filter(s=>!s.album&&!s.service&&(fam==='stick'?s.group==='stick':s.group!=='stick'));
    return `<section class="zp-shelf" data-zp-shelf="${fam}"><h4 class="section-title">${title}</h4><div class="tile-grid zp-tiles">${list.map(s=>tileFor(t,x,s)).join('')}</div></section>`;};
  return `${part('stick',clean()?`🔨 Búa hồng <small class="muted">${LEGEND.stick}</small>`:'🔨 Búa hồng (BLANKPINK)')}${part('pk',clean()?'🔋 Phụ kiện':'🔋 Pin · binder · toploader · slogan')}`;
}
function deskPanel(t,x){
  const d=data(x),opt=t.opt||{},n=need(t),cart=Object.entries(t.cart||{});
  const rows=cart.map(([k,q])=>{const s=SKU(x,k);return `<li class="zp-row"><span aria-hidden="true">${x.esc(s.emoji)}</span><b>${x.esc(nameOf(s))}</b><small>× ${q}</small><span class="grow"></span><small>${priceOf(x,k)*q}${clean()?'':' xu'}</small>${x.cmd('−','zp_drop',{task:t.id,sku:k},'small ghost zp-minus').replace('<button ',`<button aria-label="Bớt một ${x.esc(s.short)}" `)}</li>`;}).join('');
  const total=cart.reduce((s,[k,q])=>s+priceOf(x,k)*q,0);
  const opts=OPTS.map(([k,e,l])=>{const on=!!opt[k],can=on?true:d.can?.opt?.[k];
    return withWhy(x.cmd(clean()?`${e} ${l.split(' ').pop()}`:`${e} ${l}`,'zp_opt',{task:t.id,key:k,on:!on},`small zp-opt ${on?'primary':'ghost'}`).replace('<button ',`<button aria-pressed="${on}" `),can);}).join('');
  const odds=d.odds||{},fs=n.raffle||opt.raffle;
  return `<section class="card zp-desk"><h4>🧾 ${clean()?'':'Giỏ hàng '}<small class="muted">${cartN(t)}${clean()?'':' món'} · ${total} xu</small></h4>
    ${rows?`<ul class="zp-cart">${rows}</ul>`:clean()?'':`<p class="small muted">Giỏ trống: chạm hàng trên kệ để lấy.</p>`}
    <div class="zp-opts" role="group" aria-label="Lời dặn ở quầy">${opts}</div>
    ${fs?`<p class="small zp-odds">🎟️ Fansign: ${odds.slots} suất / ~${x.fmt(odds.entries||0)} phiếu · mỗi phiếu ~${x.esc(odds.pct||'')}</p>`:''}
    ${d.zban>=x.room.day?`<p class="notice small">⛔ Zchart khóa quét tới hết ngày ${d.zban}.</p>`:''}</section>`;
}

/* ------------------------------------------------------------ the morning */
function setupPanel(t,x){
  const d=data(x),b=d.shop||{},m=d.mod||{},rule=Number(m.limit||3),limits=cc(x).limits||[1,2,3,5,0];
  const sign=limits.map(v=>x.cmd(v?String(v):'∞','zp_sign',{task:t.id,n:v},`small zp-sign ${b.sign===v?'primary':'ghost'}`).replace('<button ',`<button aria-pressed="${b.sign===v}" aria-label="${v?`Tối đa ${v} bản mỗi người`:'Không giới hạn'}" `)).join('');
  const say2=(full,short)=>clean()?`${short}<span class="sr-only"> ${full}</span>`:full;
  const count=b.counted?`<p class="small">📦 Jewel ${clean()?'':'còn '}<b>${stockOf(x,'ps_jewel')}</b> · POB <b>${Number(d.pob||0)}</b></p>`:x.cmd(say2('📦 Đếm bản giới hạn','📦 Đếm kho'),'zp_count',{task:t.id},'zp-count');
  const demo=!b.demo?x.cmd(say2('🔨 Thử búa trưng bày','🔨 Thử búa'),'zp_demo',{task:t.id},'zp-demo')
    :d.demo_weak&&!b.battery?`<p class="notice small">🔨 Búa nháy yếu: hết pin AAA. ${x.cmd(`🔋 Thay pin AAA <small>📦 ${stockOf(x,'pin_aaa')}</small>`,'zp_battery',{task:t.id},'small zp-battery',!stockOf(x,'pin_aaa'))}</p>`
    :'<span class="tag green">✓ Búa sáng rực</span>';
  const book=d.book||[];
  const chot=m.id==='chot'?`<h4 class="section-title">📒 Sổ đặt trước Jewel</h4><ul class="zp-book">${book.map(r=>`<li><b>${x.esc(r.name)}</b><small>…${x.esc(r.phone)}</small><span>${r.qty} bản</span></li>`).join('')}</ul>
    ${b.closed?'<span class="tag green">✓ Đã chốt với nhà phân phối</span>':amountBox(x,`chot-${t.id}`,0,{min:0,max:60,label:'Chốt bao nhiêu bản?',send:'📒 Chốt đơn',cmd:'zp_close',payload:{task:t.id},field:'qty',unit:'bản'})}`:'';
  return `<section class="card zp-setup">${clean()?'':'<h4>🌅 Mở tiệm</h4>'}${count}
    <h4 class="section-title">🚫 Biển <small>NPP: tối đa <b>${rule}</b>/người</small></h4><div class="segmented zp-signs" role="group" aria-label="Biển giới hạn">${sign}</div>
    ${clean()?'':'<h4 class="section-title">🔨 Búa trưng bày</h4>'}${demo}${chot}${m.id!=='normal'&&t.needs?.note?`<p class="small muted">${x.esc(t.needs.note)}</p>`:''}</section>`;
}
function setupSteps(t,x){
  const d=data(x),b=d.shop||{},m=d.mod||{},rule=Number(m.limit||3),rows=[];
  rows.push({ok:b.counted?true:null,label:'Đếm bản giới hạn',go:{cmd:'zp_count',payload:{task:t.id},label:'📦 Đếm bản giới hạn'}});
  rows.push({ok:b.sign===rule?true:b.sign!=null?false:null,label:`Biển: tối đa ${rule}/người`,go:{sel:'.zp-signs',label:'🚫 Dựng biển giới hạn'}});
  rows.push({ok:b.demo?true:null,label:'Thử búa trưng bày',go:{cmd:'zp_demo',payload:{task:t.id},label:'🔨 Thử búa trưng bày'}});
  if(b.demo&&d.demo_weak)rows.push({ok:b.battery?true:null,label:'Thay pin AAA cho búa',go:stockOf(x,'pin_aaa')?{cmd:'zp_battery',payload:{task:t.id},label:'🔋 Thay pin AAA'}:null});
  if(m.id==='chot')rows.push({ok:b.closed?true:null,label:'Chốt đúng số trong sổ',go:{sel:'.zp-setup .sk-amt',label:'📒 Cộng sổ, chốt đơn'}});
  return rows;
}

/* ------------------------------------------------------------ học nghề */
function learnCard(x){
  const l=data(x).learn;if(!l?.on)return '';
  const k=`${Math.min(l.n+1,l.of)}/${l.of}`;
  if(clean())return `<p class="zp-learn" aria-label="Học nghề, khách ${k}">🎓 ${k}${tip(x.esc(`${l.title||''}: ${l.text||''}`),'Học nghề với chị Thơ')}</p>`;
  return `<p class="zp-learn" aria-label="Học nghề">💿 Học nghề · khách ${k} · <b>${x.esc(l.title||'')}</b> <small>${x.esc(l.text||'')}</small></p>`;
}

/* ------------------------------------------------------------ the guide */
const shelfOf=(x,line)=>{const s=SKU(x,line.any[0]);return s.album?{tab:'album',sel:`[data-zp-shelf="${s.album}"]`}:{tab:'merch',sel:`[data-zp-shelf="${s.group==='stick'?'stick':'pk'}"]`};};
function saleSteps(t,x){
  const n=need(t),opt=t.opt||{},rows=[],d=data(x);
  if(!d.shop?.open)rows.push({ok:null,tab:'desk',label:'Mở tiệm xong mới bán',go:d.can?.open?.fix||null});
  if(t.tw&&!t.tw.done){
    if(t.tw.probe_only){const p=t.tw.probes[0];rows.push({ok:null,label:'Xem bé dặn gì',go:{cmd:'zp_probe',payload:{task:t.id,probe:p.id},label:x.esc(p.label)}});}
    else rows.push({ok:null,label:'Trả lời khách',go:{sel:'.zp-tw',label:'👉 Hỏi rồi trả lời khách'}});
  }
  if(!n.hidden)for(const r of lineState(x,t)){
    const {tab,sel}=shelfOf(x,r.line);
    const where=SKU(x,r.line.any[0]),shelf=where.album?(cc(x).albums||{})[where.album]?.name:where.group==='stick'?'Búa hồng':'Phụ kiện';
    rows.push({ok:r.ok?true:null,tab,label:`${r.want>1?`${r.want}× `:''}${r.line.label}`.replace(/^(\d+)× \1 /,'$1 '),note:`${r.got}/${r.want}`,go:r.ok?null:{sel,label:`👉 ${shelf}`}});
  }
  for(const k of extras(x,t)){const s=SKU(x,k);rows.push({ok:false,tab:'desk',label:`Khách không lấy ${s.short}`,go:{cmd:'zp_drop',payload:{task:t.id,sku:k},label:`↩️ Bỏ ${x.esc(s.short)}`}});}
  const over=overLimit(x,t);
  if(over)rows.push({ok:false,tab:'desk',label:`Quá giới hạn ${n.limit} bản/người`,go:{cmd:'zp_drop',payload:{task:t.id,sku:over},label:`↩️ Bớt một ${x.esc(SKU(x,over).short)}`}});
  for(const [k,e,l] of OPTS)if(n[k])rows.push({ok:opt[k]?true:null,tab:'desk',label:l,go:opt[k]?null:{cmd:'zp_opt',payload:{task:t.id,key:k,on:true},label:`${e} ${l}`}});
  return rows;
}
function tabOf(t,x,steps){
  const own=x.ui.tab;if(own?.id===t.id&&TABS.some(([k])=>k===own.tab))return own.tab;
  const n=pending(steps);return n?.tab||'desk';
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở tiệm',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'zp_intro',payload:{},label:'💿 Vào việc thôi!'}}],final:null};
  if(t.kind==='setup'){const steps=setupSteps(t,x);return {steps,final:{label:'💿 MỞ TIỆM',go:finalGo(steps,'zp_open',{task:t.id}),ready:true}};}
  if(!t.known)return {steps:[{ok:null,label:'Hỏi khách',go:{cmd:'ask',payload:{task:t.id},label:'👂 Hỏi khách cần gì'}}],final:null,pulse:'.sk-ask'};
  if(t.kind==='case'){
    const w=t.tw||{},left=(w.probes||[]).filter(p=>!p.asked);
    const steps=[...left.map(p=>({ok:null,label:p.label.replace(/^\S+\s/,''),go:{cmd:'zp_probe',payload:{task:t.id,probe:p.id},label:x.esc(p.label)}})),
      {ok:w.done?true:null,label:'Chọn cách trả lời',go:{sel:'.zp-tw .sk-opts',label:'👉 Chọn cách trả lời'}}];
    return {steps,final:null,pulse:''};
  }
  if(t.stage==='pay'){const s=changeStep(x,t.id,t.cash),steps=s?[s]:[];return {steps,final:{label:'💵 ĐƯA TIỀN THỐI',go:finalGo(steps,'zp_pay',{task:t.id,...changePayload(x,t.id,t.cash)}),ready:true}};}
  const steps=saleSteps(t,x),tab=tabOf(t,x,steps);
  for(const s of steps)if(s.go?.sel&&s.tab&&s.tab!==tab)s.go={act:'car:tab',data:{tab:s.tab,task:t.id},label:`👉 Sang ${TABS.find(([k])=>k===s.tab)[1]}`};
  const n=need(t),empty=!n.hidden&&(n.lines||[]).some(l=>l.any.reduce((s,k)=>s+stockOf(x,k),0)===0);
  if(empty&&!cartN(t))return {steps,tab,final:{label:'🙏 Nói thật: kệ hết hàng',go:{cmd:'zp_decline',payload:{task:t.id}},ready:true}};
  return {steps,tab,final:{label:'🧾 TÍNH TIỀN',go:finalGo(steps,'zp_ring',{task:t.id}),ready:cartN(t)>0,can:t.can?.zp_ring,why:'lấy hàng vào giỏ trước đã'}};
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse,glow:firstTime(x)});
function tabsRow(t,x,tab,steps){
  return `<div class="zp-tabs" role="tablist">${TABS.map(([k,l])=>{const left=steps.filter(s=>s.tab===k&&s.ok!==true).length;
    const word=clean()&&k!==tab?l.split(' ')[0]:l;
    return act(x,`${x.esc(word)}${left?`<small>${left}</small>`:''}`,'tab',{tab:k,task:t.id},`zp-tab ${k===tab?'on':''}`,` role="tab" aria-selected="${k===tab}" aria-label="${x.esc(l)}"`);}).join('')}</div>`;
}

/* ------------------------------------------------------------ idle: the shop between customers */
function shopView(x){
  const d=data(x),b=d.shop||{},odds=d.odds||{};
  const line=['ps_pink','ps_blank','ps_jewel','bua2'].map(k=>`${SKU(x,k).emoji} ${stockOf(x,k)}`).join(' · ');
  return `<section class="card zp-shop"><h4>💿 Kệ hàng</h4><p class="small">${line} · 🎁 POB ${Number(d.pob||0)}</p>
    <p class="small muted">${b.open?`🚫 Biển: tối đa ${b.sign||'∞'}/người`:'Tiệm chưa mở'} · 🎟️ ${odds.slots||30} suất / ~${x.fmt(odds.entries||0)} phiếu</p></section>`;
}

export default {
  id:'zpop',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='setup'?'Đếm kho, dựng biển, mở tiệm':!t.known?'Hỏi khách cần gì':'Bán album cho khách';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    const top=`${introCard(x,'zp_intro','💿')}${deskCard(x,'zp_desk','Chuyện ở tiệm')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk zp">${hint}${top}${bottom(x,g)}</div>`;
    let main='',side='',tabs='';
    if(t.kind==='setup'){main=setupPanel(t,x);side=stepRows(x,g.steps,'Việc mở tiệm',{chip:true});}
    else if(!t.known||t.kind==='case')main=t.known?twCard(t,x):'';
    else if(t.stage==='pay')main=cashPanel(x,t.id,t.cash);
    else{
      const tab=g.tab||'album';tabs=tabsRow(t,x,tab,g.steps);
      main=tab==='album'?albumPanel(t,x):tab==='merch'?merchPanel(t,x):deskPanel(t,x);
      side=stepRows(x,g.steps,'Việc với khách này',{chip:true});
    }
    // On a plain day the shelves follow the order directly (clean layout): the day line, with its "?", moves under them.
    // A comeback, deadline, cosplay or rain day is a cue and stays on top.
    const plain=clean()&&tabs&&(d.mod?.id||'normal')==='normal';
    const head=t.kind==='setup'?dayBar(x):`${learnCard(x)}${ticket(t,x)}${t.kind==='sale'&&t.known?twCard(t,x):''}${plain?'':dayBar(x)}`;
    const bench=`${tabs}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>`;
    return `<div class="career-job sk zp">${hint}${top}${head}${bench}${plain?dayBar(x):''}${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x),top=`${introCard(x,'zp_intro','💿')}${deskCard(x,'zp_desk','Chuyện ở tiệm')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro){const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện ở tiệm',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'zp_intro',payload:{},label:'💿 Vào việc thôi!'}}],final:null};
      return `<div class="career-job sk zp">${hintFor(g,x)}${top}${bottom(x,g)}</div>`;}
    return `<div class="career-job sk zp">${top}${dayBar(x)}${shopView(x)}</div>`;
  },
  input(el,x){return kitInput(el,x);},
  tick(root){keepBarAboveFooter(root);},
  summary(sum,x){
    if(!sum||sum.units==null)return '';
    const row=(l,v)=>`<div class="kv-row"><span>${l}</span><b>${v}</b></div>`,tm=sum.tomorrow;
    const low=(sum.low||[]).map(k=>x.esc(SKU(x,k).short)).join(' · ');
    const plan=`<section class="zp-plan" aria-label="Ngày mai"><h4 class="section-title">🌅 Ngày mai</h4>${tm?`<p class="zp-tomorrow"><span aria-hidden="true">${x.esc(tm.emoji)}</span> <b>Mai: ${x.esc(tm.label)}</b> <small>${x.esc(tm.hint)}</small></p>`:''}${low?`<p class="small">📦 Sắp hết: ${low}</p>`:''}${x.button('🧺 Mở Kho','warehouse',{},'primary small')}</section>`;
    const kv=`<div class="kv">${row('Lượt khách',sum.customers)}${row('Món đã bán',sum.units)}${row('Phiếu fansign',sum.entries)}${row('Chuyện quay lại',sum.cases)}</div>${(sum.lines||[]).length?`<ul class="small">${sum.lines.map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul>`:''}${sum.note?`<p class="small muted">${x.esc(sum.note)}</p>`:''}`;
    return `<article class="card space-top zp-sum">${plan}<details><summary>💿 Tiệm album hôm nay · ${sum.customers} lượt khách · ${sum.units} món</summary>${kv}</details></article>`;
  },
  actions:{...tillActions,...kitActions,
    async tab(d,el,x){x.ui.tab={id:d.task,tab:d.tab};x.render();},
  },
  dock:[['inventory','box','Kho album','Album, Búa hồng, pin, toploader, ống poster…']],
};
