/** 🛡️ Rủi ro & bảo hiểm (game/rui.py → state.rui) and 💰 Tiệm vàng Kim Phát (game/vang.py → state.vang).
 * - A centred card opens by itself at a calm moment (v4/break-gate.js, after the gift, "Có gì mới" and the x3 week):
 *   a warning with its prevention, or a story card with its choices. One short line, one obvious button, the rest
 *   behind "?". Each card opens by itself once a session; the "Bảo hiểm" page shows it again.
 * - The "Bảo hiểm" page (data-action="rui"): the policies, the gear, what is broken. The "Tiệm vàng" page
 *   (data-action="vang"): today's price, a month's chart, buy and sell by the phân.
 * Every rule and number lives on the server; this file renders and sends jr_rui_* / jr_vang_* commands.
 * Styles: /css/whatsnew.css (the card's shell) + /css/rui.css. app.js loads this module lazily (ruiBoot, ruiAction). */
import {icon,escapeHTML as esc} from '../icons.js';
import {quiet,turn,want} from './break-gate.js';

const S={env:null,pop:null,page:null,view:'',busy:false,flash:null,done:null,timer:0,calm:0,seen:new Set(),qty:10,listening:false};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const R=()=>S.env?.api?.state?.rui||null;
const G=()=>S.env?.api?.state?.vang||null;
const CAT=()=>S.env?.api?.content?.journey?.rui||{policies:[],gear:[],rules:{}};
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const POCKET=['wallet','account'];   // cash first, then the bank account (rui.py, vang.py)

/* ---- styles on first use ---- */
let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=Promise.all([link('/css/whatsnew.css','wn-css'),link('/css/rui.css','rui-css')]);

/* ---- bits ---- */
const head=(emoji,title,sub='',id='ruiTitle')=>`<header class="wn-head"><span class="wn-spark" aria-hidden="true">${emoji}</span><div class="grow"><h2 id="${id}">${esc(title)}</h2>${sub?`<p class="wn-meta">${esc(sub)}</p>`:''}</div><button type="button" class="icon-btn wn-x" data-rui="close" aria-label="Đóng">${icon('x',22)}</button></header>`;
const help=lines=>`<details class="rui-help"><summary aria-label="Giải thích">?</summary><ul>${lines.map(t=>`<li>${esc(t)}</li>`).join('')}</ul></details>`;
function costLine(o){
  const out=[];
  out.push(o.cost?xu(o.cost):'Không tốn xu');
  if(o.spirit)out.push(`tinh thần ${o.spirit}`);
  if(o.note)out.push(o.note);
  return out.map(esc).join(' · ');
}
function optBtn(o,i,op,data){
  const why=o.ok===false?(o.why||'Chưa làm được'):'';
  return `<button type="button" class="rui-opt${i===0?' primary':''}" data-rui="${op}"${attrs(data)}${why||S.busy?' disabled':''}><span class="rui-opt-emoji" aria-hidden="true">${o.emoji||'•'}</span><span class="rui-opt-text"><b>${esc(o.label)}</b><small>${why?esc(why):costLine(o)}</small></span></button>`;
}
const flash=()=>S.flash?`<p class="rui-flash ${S.flash.kind}" role="status">${esc(S.flash.text)}</p>`:'';

/* ---- the card (a warning or an event) ---- */
function popHTML(){
  if(S.done)return head(S.done.emoji,S.done.title)+`<div class="wn-body"><p class="rui-line">${esc(S.done.text)}</p></div><footer class="wn-foot"><button type="button" class="btn primary big full" data-rui="close">Xong</button></footer>`;
  const r=R(),c=r?.card,w=!c&&r?.warn;
  if(c){
    const chips=[];
    if(c.loss)chips.push(`<span class="rui-chip out">${c.kind==='hack'?`−${xu(c.loss)} trong tài khoản`:`−${xu(c.loss)} tiền mặt`}</span>`);
    if(c.cover)chips.push(`<span class="rui-chip good">🛡️ Bảo hiểm trả ${c.cover}%</span>`);
    return head(c.emoji,c.title,c.left?`Chọn trong ${c.left} ngày`:'')+`<div class="wn-body">${flash()}<p class="rui-line">${esc(c.text)}</p>${chips.length?`<p class="rui-chips">${chips.join('')}</p>`:''}`+
      `<div class="rui-opts">${c.opts.map((o,i)=>optBtn(o,i,'choose',{id:c.id,choice:o.id})).join('')}</div>`+
      help(['Chuyện đời ai cũng có lúc gặp.',c.kind==='hack'?'Bảo hiểm hiện tại không bồi thường vụ hack tài khoản.':'Có bảo hiểm thì trả ít hơn.',`Không chọn sau ${CAT().rules.card_days||3} ngày: tự chọn cách nhẹ nhất.`,'Không bao giờ bị nợ vì chuyện này.'])+`</div>`;
  }
  if(w){
    return head(w.emoji,w.title,w.days?`Còn ${w.days} ngày`:'Sắp xảy ra')+`<div class="wn-body">${flash()}<p class="rui-line">${esc(w.text)}</p>`+
      `<div class="rui-opts">${w.opts.map((o,i)=>optBtn(o,i,'prevent',{opt:o.id})).join('')}</div>`+
      help(['Phòng trước thì chuyện không xảy ra.','Ngân hàng tránh mất tiền mặt do móc túi; tài khoản vẫn có rủi ro bị hack.','Khóa phiên lạ khi được cảnh báo để chặn vụ hack, không tốn xu.'])+`</div>`+
      `<footer class="wn-foot"><button type="button" class="btn ghost full" data-rui="close">Để sau</button></footer>`;
  }
  return head('🛡️','Bình yên')+`<div class="wn-body"><p class="rui-line">Không có chuyện gì cả.</p></div><footer class="wn-foot"><button type="button" class="btn primary big full" data-rui="close">Xong</button></footer>`;
}

/* ---- the "Bảo hiểm" page ---- */
function polRow(p){
  const c=CAT().policies.find(x=>x.id===p.id)||{name:p.id,emoji:'🛡️',what:'',cover:80};
  const price=p.company?'Công ty đóng':p.can||p.on?`${xu(p.month)}/tháng · trả ${c.cover}%`:'Chưa có gì để bảo hiểm';
  const wait=p.on&&p.wait?`<em class="rui-wait">Có hiệu lực sau ${p.wait} ngày</em>`:'';
  const btn=p.company?'':p.on?`<button type="button" class="btn ghost small" data-rui="pol" data-id="${p.id}" data-on="0"${S.busy?' disabled':''}>Ngưng</button>`
    :`<button type="button" class="btn primary small" data-rui="pol" data-id="${p.id}" data-on="1"${S.busy||!p.can?' disabled':''}>Mua</button>`;
  return `<li class="rui-row${p.on?' on':''}"><span class="rui-ico" aria-hidden="true">${c.emoji}</span><span class="grow"><b>${esc(c.name)}${p.on?' ✓':''}</b><small>${esc(c.what)}</small><small>${esc(price)}</small>${wait}</span>${btn}</li>`;
}
function gearRow(g,have){
  const btn=have?'<span class="rui-have">✓ Đã có</span>':`<button type="button" class="btn small" data-rui="gear" data-id="${g.id}"${S.busy?' disabled':''}>Mua · ${xu(g.price)}</button>`;
  return `<li class="rui-row${have?' on':''}"><span class="rui-ico" aria-hidden="true">${g.emoji}</span><span class="grow"><b>${esc(g.name)}</b><small>${esc(g.what)}</small></span>${btn}</li>`;
}
function ruiPage(){
  const r=R()||{pol:[],gear:[],broken:[]},rules=CAT().rules||{};
  const now=r.card||r.warn;
  const alert=now?`<button type="button" class="rui-now" data-rui="pop"><span aria-hidden="true">${now.emoji}</span><span class="grow"><b>${esc(now.title)}</b><small>${esc(now.text)}</small></span>${icon('chevron',18)}</button>`:'';
  const calm=r.calm?`<p class="rui-calm">🌱 Phố còn bình yên với người mới. Cứ yên tâm làm việc.</p>`:'';
  const pending=r.hack_pending?`<p class="rui-calm">${esc(r.hack_pending.days?`🚔 Đã trình báo ${r.hack_pending.n} vụ hack. Kết quả gần nhất sau ${r.hack_pending.days} ngày sống.`:'🚔 Tiền hoàn đang chờ: cần tài khoản ngân hàng và số dư dưới mức tối đa để nhận ở ngày sống tiếp theo.')}</p>`:'';
  const broken=(r.broken||[]).length?`<h3 class="rui-h">🔧 Đang hỏng</h3><ul class="rui-list">${r.broken.map(b=>`<li class="rui-row"><span class="rui-ico" aria-hidden="true">${b.kind==='xe'?'🚗':'🏠'}</span><span class="grow"><b>${esc(b.name)}</b></span><button type="button" class="btn primary small" data-rui="fix" data-kind="${b.kind}" data-ref="${esc(b.ref)}"${S.busy?' disabled':''}>Sửa · ${xu(b.cost)}</button></li>`).join('')}</ul>`:'';
  return head('🛡️','Bảo hiểm & rủi ro','Phòng trước, đỡ lo','ruiPageTitle')+`<div class="wn-body">${flash()}${alert}${calm}${pending}${broken}`+
    `<h3 class="rui-h">🛡️ Bảo hiểm</h3><ul class="rui-list">${(r.pol||[]).map(polRow).join('')}</ul>`+
    `<h3 class="rui-h">🔒 Đồ phòng thân</h3><ul class="rui-list">${CAT().gear.map(g=>gearRow(g,(r.gear||[]).includes(g.id))).join('')}</ul>`+
    help(['Chuyện xấu luôn báo trước 1–2 ngày. Phòng trước là tránh được.',`Ví và tài khoản dưới ${fmt(rules.floor||300)} xu: không có chuyện gì.`,
      `Mỗi lần mất tối đa ${rules.event_pct||8}% tiền của bạn, mỗi tháng tối đa ${rules.month_pct||12}%.`,
      `Bảo hiểm mới mua có hiệu lực sau ${rules.wait||3} ngày.`,
      `Bị hack: mất ${rules.hack_pct||8}% tài khoản thanh toán, tối đa ${fmt(rules.hack_max||3000)} xu và chịu giới hạn rủi ro chung.`,
      'Khóa phiên lạ khi được cảnh báo để chặn vụ hack, không tốn xu.','Không bao giờ bị nợ vì rủi ro.'])+`</div>`;
}

/* ---- the gold shop ---- */
function spark(hist){
  if(!hist?.length)return '';
  const w=300,h=64,lo=Math.min(...hist),hi=Math.max(...hist),span=Math.max(1,hi-lo);
  const pts=hist.map((p,i)=>`${(i*w/Math.max(1,hist.length-1)).toFixed(1)},${(h-4-(p-lo)*(h-8)/span).toFixed(1)}`).join(' ');
  const up=hist[hist.length-1]>=hist[0];
  return `<svg class="rui-spark ${up?'up':'down'}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" role="img" aria-label="Giá vàng ${hist.length} ngày: thấp nhất ${fmt(lo)}, cao nhất ${fmt(hi)}"><polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/></svg>`;
}
const amount=n=>n<10?`${n} phân`:n%10?`${fmt(Math.floor(n/10))},${n%10} chỉ`:`${fmt(n/10)} chỉ`;
const costOf=(n,g)=>Math.ceil(n*g.buy/10);
const worthOf=(n,g)=>Math.floor(n*g.sell/10);
function vangPage(){
  const g=G();
  if(!g)return head('💰','Tiệm vàng Kim Phát','','vangTitle')+`<div class="wn-body"><p class="rui-line">Tiệm vàng chưa mở.</p></div>`;
  const ch=g.y?((g.p-g.y)*100/g.y):0,chip=`<span class="rui-chip ${ch>=0?'good':'out'}">${ch>=0?'▲':'▼'} ${Math.abs(ch).toFixed(1).replace('.',',')}%</span>`;
  const q=Math.max(1,Math.min(S.qty,100000)),gain=g.value-g.cost;
  const mine=g.phan?`<div class="rui-mine"><b>Bạn có ${amount(g.phan)}</b><span>Bán ngay được ${xu(g.value)}</span><span class="${gain>=0?'good':'out'}">${gain>=0?'Lãi':'Lỗ'} ${xu(Math.abs(gain))}</span></div>`:'';
  const sellN=Math.min(q,g.phan||0);
  return head('💰','Tiệm vàng Kim Phát','Giá chung cả phố, đổi mỗi ngày','vangTitle')+`<div class="wn-body">${flash()}`+
    `<div class="rui-price"><b>${xu(g.p)}</b><span>/ chỉ</span>${chip}</div>${g.news?`<p class="rui-news">📰 ${esc(g.news)}</p>`:''}${spark(g.hist)}`+
    `<p class="rui-sub">Tiệm bán ${xu(g.buy)} · mua lại ${xu(g.sell)}</p>${mine}`+
    `<div class="rui-qty" role="group" aria-label="Số vàng"><button type="button" class="btn small" data-rui="qty" data-d="-1" aria-label="Bớt">−</button><b>${amount(q)}</b><button type="button" class="btn small" data-rui="qty" data-d="1" aria-label="Thêm">+</button></div>`+
    `<div class="rui-quick">${[[1,'1 phân'],[10,'1 chỉ'],[50,'5 chỉ']].map(([n,l])=>`<button type="button" class="btn ghost small${q===n?' on':''}" data-rui="set" data-n="${n}">${l}</button>`).join('')}</div>`+
    `<div class="rui-trade"><button type="button" class="btn primary big" data-rui="buy"${S.busy?' disabled':''}>Mua · ${xu(costOf(q,g))}</button>`+
    `<button type="button" class="btn big" data-rui="sell"${S.busy||!g.phan?' disabled':''}>Bán · nhận ${xu(worthOf(sellN||q,g))}</button></div>`+
    help(['Mua đắt hơn giá 2,5%, bán rẻ hơn 2,5%.','Giữ lâu vài tuần mới mong có lời.','Giá lên xuống mỗi ngày, có thể lỗ.','1 chỉ = 10 phân.'])+`</div>`;
}

/* ---- dialogs ---- */
function dialog(kind){
  const key=kind==='pop'?'pop':'page';
  if(S[key])return S[key];
  const d=document.createElement('dialog');
  d.id=kind==='pop'?'ruiCard':'ruiPage';d.className=`wn-dialog rui-dialog ${kind==='pop'?'rui-pop':'rui-pagebox'}`;
  d.setAttribute('aria-modal','true');d.setAttribute('aria-labelledby',kind==='pop'?'ruiTitle':'ruiPageTitle');
  d.innerHTML='<div class="wn-card"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    const b=e.target.closest('[data-rui]');if(!b||!d.contains(b)||b.disabled)return;
    e.preventDefault();onClick(d,b.dataset.rui,b.dataset);
  });
  d.addEventListener('cancel',e=>{e.preventDefault();close(d);});
  d.addEventListener('close',()=>{if(d===S.pop)S.done=null;S.flash=null;});
  S[key]=d;return d;
}
function render(){
  if(S.pop?.open)S.pop.querySelector('.wn-card').innerHTML=popHTML();
  if(S.page?.open){
    const body=S.page.querySelector('.wn-body'),top=body?.scrollTop;
    S.page.querySelector('.wn-card').innerHTML=S.view==='vang'?vangPage():ruiPage();
    if(top)S.page.querySelector('.wn-body').scrollTop=top;
    S.page.setAttribute('aria-labelledby',S.view==='vang'?'vangTitle':'ruiPageTitle');
  }
}
function close(d){if(d?.open)d.close();}
function listen(){
  if(S.listening||!S.env?.api)return;S.listening=true;
  let seen='';S.env.api.addEventListener('state',()=>{const s=S.env.api.state,key=JSON.stringify([s?.rui,s?.vang,s?.journey?.wallet]);if(key===seen)return;seen=key;if(!S.busy)render();});
}
async function openPop(){
  await ensureCss();listen();
  const d=dialog('pop');S.done=null;S.flash=null;
  d.querySelector('.wn-card').innerHTML=popHTML();
  if(!d.open)d.showModal();
  d.tabIndex=-1;d.focus({preventScroll:true});
}
export async function openRui(env,view='rui'){
  S.env=env||S.env;S.view=view;S.flash=null;
  const sheet=document.getElementById('sheet');if(sheet?.open)S.env.closeSheet?.();
  await ensureCss();listen();
  const d=dialog('page');
  d.querySelector('.wn-card').innerHTML=view==='vang'?vangPage():ruiPage();
  d.setAttribute('aria-labelledby',view==='vang'?'vangTitle':'ruiPageTitle');
  if(!d.open)d.showModal();
  d.tabIndex=-1;d.focus({preventScroll:true});
}
export async function ruiAction(action,data,el,env){
  if(action!=='rui'&&action!=='vang')return false;
  await openRui(env,action);return true;
}

async function send(command,payload){
  S.busy=true;render();
  try{
    const r=await S.env.api.command(command,payload);
    S.flash={text:[r.message,...(r.effects||[])].filter(Boolean).join(' '),kind:'good'};
    return r;
  }catch(e){S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;render();}
}
const ask=(title,msg,label,money)=>S.env.confirmAction(title,msg,label,money);

async function onClick(d,op,data){
  const g=G();
  switch(op){
    case'close':close(d);return;
    case'pop':openPop();return;
    case'choose':case'prevent':{
      const r=R(),src=op==='choose'?r?.card:r?.warn;if(!src)return;
      const res=await send(op==='choose'?'jr_rui_choose':'jr_rui_prevent',op==='choose'?{id:data.id,choice:data.choice}:{opt:data.opt});
      if(res&&d===S.pop){S.done={emoji:src.emoji,title:src.title,text:S.flash?.text||res.message||''};S.flash=null;render();}
      return;}
    case'pol':send('jr_rui_pol',{id:data.id,on:data.on==='1'});return;
    case'gear':{const it=CAT().gear.find(x=>x.id===data.id);if(!it)return;
      if(await ask(`Mua ${it.name.toLowerCase()}?`,it.what,`Mua · ${xu(it.price)}`,{cost:it.price,pocket:POCKET}))send('jr_rui_gear',{id:it.id});return;}
    case'fix':send('jr_rui_fix',{kind:data.kind,ref:data.ref});return;
    case'qty':{const step=S.qty>=10?10:1;S.qty=Math.max(1,Math.min(100000,S.qty+Number(data.d)*step));render();return;}
    case'set':S.qty=Number(data.n)||10;render();return;
    case'buy':{if(!g)return;const n=S.qty,cost=costOf(n,g);
      if(await ask(`Mua ${amount(n)} vàng?`,`Giá tiệm bán hôm nay ${xu(g.buy)} một chỉ.`,`Mua · ${xu(cost)}`,{cost,pocket:POCKET}))send('jr_vang_buy',{phan:n});return;}
    case'sell':{if(!g?.phan)return;const n=Math.min(S.qty,g.phan),all=n===g.phan;
      if(await ask(`Bán ${amount(n)} vàng?`,`Tiệm mua lại ${xu(g.sell)} một chỉ. Tiền vào ví.`,`Bán · nhận ${xu(worthOf(n,g))}`))send('jr_vang_sell',all?{all:true}:{phan:n});return;}
  }
}

/* ---- by itself, at a calm moment ---- */
function due(){
  const r=R();if(!r)return null;
  if(r.card)return 'c'+r.card.id;
  if(r.warn)return 'w'+[r.warn.kind,r.warn.sub,r.warn.ref].join('|');
  return null;
}
function check(){
  const k=due(),J=S.env?.api?.state?.journey;
  if(!k||S.seen.has(k)||!J?.story||!J.intro){want('rui',false);S.calm=0;return;}
  want('rui');
  if(S.page?.open||!quiet(S.pop)||!turn('rui')){S.calm=0;return;}
  if(++S.calm<2)return;
  S.calm=0;want('rui',false);S.seen.add(k);openPop();
}
/** Called once by app.js after the game is on screen. */
export function ruiBoot(env){
  try{S.env=env;clearInterval(S.timer);S.timer=setInterval(check,1000);}
  catch(error){console.error('rui:',error);}   // never in the way of the game
}
