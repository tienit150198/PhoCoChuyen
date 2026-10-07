/** 📱 Cửa hàng điện thoại Mây Mobile: phones and small gadgets, bought outright (story mode). Feedback F#205.
 * Every rule and number lives in game/gadgets.py; this file renders api.state.journey.gadgets with the static list
 * (content.journey.gadgets) and sends `jr_gadget_*` commands. Its own dialog (like Xe & phương tiện), opened with
 * data-action="gadgets" from the menu hub, the 🧭 Chỉ đường signpost and the town map's door.
 * The art is drawn in CSS: a phone in its shell colour (a foldable has a hinge, the gold one shines), gear as its
 * emoji on a tile. 📸 Selfie (a perk of the phone in use): the character in a frame of that phone, saved as a PNG.
 * Styles: /css/bank.css + /css/house.css + /css/gadgets.css. */
import {icon,escapeHTML as esc} from '../icons.js';
import {lookOf,figureSVG} from './look.js';

const S={dlg:null,env:null,tab:'',view:'list',pick:null,frame:'',busy:false,flash:null,listening:false};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,op,data={},cls='',why='')=>`<button type="button" class="btn ${cls}" data-gd="${op}"${attrs(data)}${S.busy||why?' disabled':''}${why?` title="${esc(why)}"`:''}>${label}</button>`;
const J=()=>S.env?.api?.state?.journey||{};
const V=()=>J().gadgets;
const CAT=()=>S.env?.api?.content?.journey?.gadgets||{groups:[],items:[],perks:[]};
const item=id=>CAT().items.find(x=>x.id===id);
const perk=id=>CAT().perks.find(p=>p.id===id)||{};
const isPhone=it=>it?.group==='phone';
/** 🔨 A phone number won at the auction house (game/auction.py, journey.uniq.own): shown on the phone in use. */
const uqPhone=()=>{const o=S.env?.api?.state?.journey?.uniq?.own||{};const x=Object.values(o).filter(v=>v?.k==='phone').sort((a,b)=>(b.p||0)-(a.p||0))[0];return x?.t||'';};
const lname=it=>isPhone(it)?it.name:String(it?.name||'').slice(0,1).toLowerCase()+String(it?.name||'').slice(1);
const POCKET=['wallet','account'];   // gadgets.py (garage._take): the wallet first, then the bank account
/** Selfie frames: [id, the perk that opens it, label]. The phone in use decides which are open. */
const FRAMES=[['polaroid','selfie','📸 Polaroid'],['pro','skin','🎞️ Tạp chí'],['duo','duo','🪞 Ảnh đôi'],['gold','gold','✨ Viền vàng']];

/* ---- styles on first use ---- */
let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=Promise.all([link('/css/bank.css','bk-css'),link('/css/house.css','hs-css'),link('/css/gadgets.css','gd-css')]);

/** The picture of an item: a phone in its shell, or gear's emoji on a tile in its colour. size: '' | 'big'. */
export function artHTML(it,size=''){
  if(!it)return `<span class="gd-old ${size}" aria-hidden="true">📞</span>`;
  if(!isPhone(it))return `<span class="gd-tile ${size}" style="--gd-shell:${esc(it.color)}" aria-hidden="true"><span>${it.emoji}</span></span>`;
  return `<span class="gd-phone t${Number(it.tier)||1} ${size}${it.id==='sen_gap'?' fold':''}" style="--gd-shell:${esc(it.color)}" aria-hidden="true"><i class="gd-screen"></i><i class="gd-cam"></i></span>`;
}

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium bk-sheet hs-sheet gd-sheet';d.setAttribute('aria-labelledby','gd-title');
  d.innerHTML='<div class="gd-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-gd]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.gd,el.dataset);
  });
  d.addEventListener('change',e=>{if(e.target.name==='trade'&&S.pick){S.pick.trade=e.target.checked;render();}});
  d.addEventListener('close',()=>{S.flash=null;S.view='list';S.pick=null;});
  S.dlg=d;return d;
}
export async function openGadgets(env,tab){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';env.api.addEventListener('state',()=>{const key=JSON.stringify([J().wallet,J().gadgets,J().bank?.balance]);if(key===seen)return;seen=key;if(S.dlg?.open&&!S.busy)render();});
  }
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();
  S.view=tab==='selfie'?'selfie':'list';S.pick=null;
  S.tab=['mine','phone','gear'].includes(tab)?tab:'mine';   // 🎒 first: the phone in use, or the old one and its upgrade
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
}
export async function gadgetsAction(action,data,el,env){
  if(action!=='gadgets')return false;
  await openGadgets(env,data?.tab);return true;
}

async function send(action,payload={}){
  const {api}=S.env;S.busy=true;render();
  try{
    const r=await api.command(action,payload);
    S.flash={text:[r.message,...(r.effects||[]).filter(Boolean)].filter(Boolean).join(' '),kind:'good'};
    return r;
  }catch(e){S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;render();S.dlg?.querySelector('.gd-body')?.scrollTo?.(0,0);}
}
const ask=(title,msg,label,money)=>S.env.confirmAction(title,msg,label,money);
const top=()=>S.dlg?.querySelector('.gd-body')?.scrollTo?.(0,0);
/** The xu off for the old phone: only on a phone, only while the old one is still yours (gadgets.trade_in). */
const tradeOff=it=>isPhone(it)&&!V()?.old?Math.min(CAT().trade_in||0,it.price-10):0;

async function onClick(op,data){
  const v=V()||{};
  switch(op){
    case'close':S.dlg.close();return;
    case'tab':S.tab=data.tab;S.view='list';S.pick=null;S.flash=null;render();top();return;
    case'back':S.view='list';S.pick=null;render();return;
    case'look':{const it=item(data.id);if(!it)return;S.view='buy';S.pick={id:it.id,trade:true};S.flash=null;render();top();return;}
    case'buy':{const it=item(S.pick?.id);if(!it)return;const off=S.pick.trade?tradeOff(it):0,cost=it.price-off;
      if(await ask(`Mua ${lname(it)}?`,`Trả đủ ${xu(cost)} một lần${off?` (đã bớt ${xu(off)} thu máy cũ)`:''}, không vay. Lấy tiền mặt trong ví trước, thiếu thì lấy từ tài khoản ngân hàng.`,`Mua · ${xu(cost)}`,{cost,pocket:POCKET})){
        const r=await send('jr_gadget_buy',{id:it.id,...(isPhone(it)?{trade:Boolean(off)}:{}),confirm:true});
        if(r){S.view='list';S.pick=null;S.tab='mine';render();}
      }return;}
    case'use':send('jr_gadget_use',{id:data.id||null});return;
    case'sell':{const o=(v.own||[]).find(x=>x.id===data.id),it=item(data.id);if(!o||!it)return;
      if(await ask(`Bán ${lname(it)}?`,`Mua ${xu(o.paid)}, bán lại được ${xu(o.sell)} (${CAT().sell_pct}% giá đã trả). Tiền vào ví. Bán rồi là không lấy lại được.`,`Bán · nhận ${xu(o.sell)}`))send('jr_gadget_sell',{id:o.id,confirm:true});return;}
    case'selfie':S.view='selfie';S.flash=null;render();top();return;
    case'frame':S.frame=data.frame;render();return;
    case'save':saveSelfie();return;
  }
}

/* ---- rendering ---- */
function render(){
  if(!S.dlg)return;
  const body=S.dlg.querySelector('.gd-body'),y=body?.scrollTop;
  S.dlg.querySelector('.gd-root').innerHTML=page();
  if(y)S.dlg.querySelector('.gd-body').scrollTop=y;
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
function head(){
  const v=V(),h=v?.hand&&item(v.hand.id);
  const back=S.view!=='list'?`<button class="icon-btn" type="button" data-gd="back" aria-label="Quay lại">${icon('back',21)}</button>`:'<span class="gd-logo" aria-hidden="true">📱</span>';
  const sub=h?`Đang dùng: ${esc(h.name)}`:v&&!v.old?`Đang dùng: ${esc(CAT().old?.name||'Máy cũ')} · lên đời ở đây`:'Điện thoại, đồng hồ, tai nghe, máy ảnh';
  return `<header class="sheet-head bk-head hs-head">${back}
    <div class="grow"><span class="eyebrow">${esc((CAT().where||'Phố dịch vụ').toUpperCase())} · ${esc(CAT().shop||'Mây Mobile')}</span><h2 id="gd-title">Điện thoại</h2><p>${sub}</p></div>
    <button class="icon-btn" type="button" data-gd="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
}
const flash=()=>`<p class="bk-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
function page(){
  const v=V();
  const note=(t,p)=>head()+`<div class="sheet-body bk hs-body gd-body"><section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">📱</div><h3>${t}</h3><p>${p}</p></section></div>`;
  if(!v)return note('Cửa hàng đang mở cửa','Máy mới đang được bày lên kệ. Mở lại sau ít phút nhé.');   // an older server
  if(!v.story)return note('Chỉ có trong chế độ hành trình','Vào hành trình để sắm điện thoại cho nhân vật của bạn.');
  const inner=S.view==='buy'?buyView(v):S.view==='selfie'?selfieView(v):(tabs(v)+(S.tab==='mine'?mineView(v):groupView(v,S.tab)));
  return head()+`<div class="sheet-body bk hs-body gd-body">${flash()}${inner}</div>`;
}
function tabs(v){
  const list=[['mine',`🎒 Của bạn${v.own.length?` · ${v.own.length}`:''}`],...CAT().groups.map(g=>[g.id,`${g.emoji} ${g.name}`])];
  return `<div class="segmented bk-tabs gd-tabs" role="tablist" aria-label="Mục cửa hàng">${list.map(([id,l])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" class="${S.tab===id?'active':''}" data-gd="tab" data-tab="${id}">${esc(l)}</button>`).join('')}</div>`;
}
/** The perks a phone gives, ✓ the ones it opens (cumulative by tier). */
function perkList(it,compact=false){
  if(!isPhone(it))return `<p class="hs-chips"><span>🙌 Khoe trên hồ sơ</span><span>📸 Nhãn dán ảnh selfie</span></p>`;
  const on=new Set(it.perks||[]);
  if(compact)return `<p class="hs-chips">${(it.perks||[]).map(id=>{const p=perk(id);return `<span>${p.emoji} ${esc(p.name)}</span>`;}).join('')}</p>`;
  return `<ul class="gd-perks">${CAT().perks.map(p=>`<li class="${on.has(p.id)?'on':''}"><span aria-hidden="true">${on.has(p.id)?'✓':'·'}</span><span><b>${p.emoji} ${esc(p.name)}</b><small>${esc(p.desc)}</small></span></li>`).join('')}</ul>`;
}

/* 🎒 What you own: the phone in use (and its perks), selfie, use another phone, sell. */
function mineView(v){
  const h=v.hand&&item(v.hand.id),old=CAT().old||{name:'Máy cũ',desc:''};
  const cheapest=CAT().items.filter(isPhone).sort((a,b)=>a.price-b.price)[0];
  const lead=h?`<section class="bk-card gd-hand" style="--gd-shell:${esc(h.color)}"><div class="gd-hand-top">${artHTML(h,'big')}<div class="grow"><small>Đang dùng</small><h3>${esc(h.name)}</h3>${uqPhone()?`<p class="gd-number" data-no-translate>📱 <b>${esc(uqPhone())}</b></p>`:''}
      ${perkList(h,true)}</div></div>
      <div class="bk-actions">${(v.perks||[]).includes('selfie')?btn('📸 Chụp selfie','selfie',{},'primary'):`<span class="bk-hint">📸 Selfie có khung mở từ ${esc(CAT().items.find(x=>(x.perks||[]).includes('selfie'))?.name||'máy tầm trung')}.</span>`}${btn('Cất máy, không khoe','use',{},'ghost small')}</div></section>`
    :`<section class="bk-card gd-hand gd-oldcard"><div class="gd-hand-top">${artHTML(null,'big')}<div class="grow"><small>${v.old?'Bạn đã đổi máy cũ':'Đang dùng'}</small><h3>${v.old?'Chưa cầm máy nào':esc(old.name)}</h3><p>${v.old?'Chọn một chiếc điện thoại bên dưới để dùng và khoe.':esc(old.desc)}</p></div></div>
      ${!v.old&&cheapest?`<p class="bk-alert good">🔁 Thu cũ đổi mới: mua điện thoại đầu tiên, đưa máy cũ cho tiệm, bớt ${xu(CAT().trade_in)}.</p><div class="bk-actions">${btn(`Lên đời · ${esc(cheapest.name)} ${xu(cheapest.price-tradeOff(cheapest))}`,'look',{id:cheapest.id},'primary')}</div>`:''}</section>`;
  if(!v.own.length)return lead;
  const rows=v.own.map(o=>{
    const it=item(o.id);if(!it)return '';
    const on=v.hand?.id===o.id;
    return `<li class="hs-home gd-item${on?' mine':''}" style="--hs-tone:${esc(it.color)}"><div class="hs-home-top">${artHTML(it)}<div class="grow"><b>${esc(it.name)}</b><small>${on?'✋ Đang dùng':`Mua ngày ${fmt(o.day)}`}</small></div></div>
      <div class="gd-row-actions">${isPhone(it)&&!on?btn('Dùng máy này','use',{id:o.id},'ghost'):''}<span class="gd-sell"><small>Bán lại ${xu(o.sell)}</small>${btn('Bán','sell',{id:o.id},'ghost small danger')}</span></div></li>`;
  }).join('');
  return `${lead}<section class="bk-card"><h3>Đồ của bạn</h3><p class="bk-hint">Máy đang dùng và 3 món đắt nhất hiện trên hồ sơ, cho cả phố cùng xem.</p><ul class="hs-market">${rows}</ul></section>`;
}

/* One tab of the shop: cheapest first, "còn thiếu N xu" when the money is not there yet. */
function groupView(v,gid){
  const mine=new Set(v.own.map(o=>o.id)),list=CAT().items.filter(x=>x.group===gid).sort((a,b)=>a.price-b.price);
  const rows=list.map(it=>{
    const owned=mine.has(it.id),w=v.why?.[it.id],off=tradeOff(it);
    const status=owned?'<span class="hs-ok">✓ Đã có</span>':w?`<span class="hs-miss">${esc(w)}</span>`:'<span class="hs-ok">✓ Đủ tiền mua</span>';
    return `<li class="hs-home${owned?' mine':''}" style="--hs-tone:${esc(it.color)}"><div class="hs-home-top">${artHTML(it)}<div class="grow"><b>${esc(it.name)}</b><small>${isPhone(it)?`Hạng ${'★'.repeat(it.tier)}`:esc(it.brand)}</small></div><strong class="hs-price">${xu(it.price)}${off&&!owned?`<small>−${xu(off)} thu cũ</small>`:''}</strong></div>
      <p>${esc(it.desc)}</p>${perkList(it,true)}
      <div class="hs-go">${status}${owned?'':btn(isPhone(it)?'Xem máy':'Xem món này','look',{id:it.id},w?'ghost':'primary')}</div></li>`;
  }).join('');
  const intro=gid==='phone'?'Máy càng xịn càng mở thêm vài món vui: khung selfie, vỏ máy khoe trên hồ sơ. Không máy nào làm ra tiền, không phí tháng.':'Đồ chơi công nghệ để khoe và làm nhãn dán trong ảnh selfie.';
  return `<section class="bk-card"><p class="bk-hint">${intro} Ví ${xu(v.have.wallet)}${v.have.bank?` · tài khoản ${xu(v.have.balance)}`:''}.</p><ul class="hs-market">${rows}</ul></section>`;
}

function buyView(v){
  const it=item(S.pick?.id);if(!it){S.view='list';return mineView(v);}
  const off=tradeOff(it),use=S.pick.trade&&off,cost=it.price-(use?off:0);
  const w=v.have.debt>0?v.why?.[it.id]||'':cost>v.have.ready?`Còn thiếu ${fmt(cost-v.have.ready)} xu.`:'';   // the server's reason assumes the trade-in
  return `<section class="bk-card hs-buy"><div class="hs-home-top"><div class="grow"><small>${esc(it.brand)} · ${esc(CAT().shop||'')}</small><h3>${esc(it.name)}</h3></div><strong class="hs-price">${xu(it.price)}</strong></div>
    <div class="gd-preview">${artHTML(it,'big')}</div>
    <p>${esc(it.desc)}</p>${perkList(it)}
    ${off?`<label class="bk-toggle gd-trade"><input type="checkbox" name="trade"${S.pick.trade?' checked':''}${S.busy?' disabled':''}><span><b>🔁 Thu cũ đổi mới: bớt ${xu(off)}</b><small>Đưa ${esc((CAT().old?.name||'máy cũ').toLowerCase())} cho tiệm. Bỏ chọn nếu muốn giữ làm kỷ niệm.</small></span></label>`:''}
    <p class="bk-hint">Trả một lần, không phí tháng. Bán lại được ${CAT().sell_pct}% giá đã trả.</p>
    ${w?`<p class="bk-alert warn">${esc(w)}</p>`:''}
    <div class="bk-actions">${btn(`Mua · ${xu(cost)}`,'buy',{},'primary big',w||'')}${btn('Quay lại','back',{},'ghost')}</div></section>`;
}

/* ---- 📸 Selfie ---- */
/** The look with the phone in use in hand (look.held: v4/look.js paintPlayer). */
const held=st=>{const L=lookOf(st),c=st?.journey?.gadgets?.hand?.color;return /^#[0-9a-f]{6}$/i.test(c||'')?{...L,held:c}:L;};
function frames(v){return FRAMES.filter(([,p])=>(v.perks||[]).includes(p));}
function figure(flip=false){
  const st=S.env.api.state,svg=figureSVG(held(st),st?.journey?.gender,{w:150,h:210,label:''});
  return `<span class="gd-fig${flip?' flip':''}">${svg}</span>`;
}
function stickers(v){return v.own.map(o=>item(o.id)).filter(it=>it&&!isPhone(it)).sort((a,b)=>b.price-a.price).slice(0,3).map(it=>it.emoji);}
function selfieView(v){
  const list=frames(v);
  if(!list.length){S.view='list';return mineView(v);}
  if(!list.some(f=>f[0]===S.frame))S.frame=list[list.length-1][0];
  const h=item(v.hand?.id),name=S.env.api.state?.name||'Bạn',day=J().life_day;
  const caption=S.frame==='pro'?`Chụp bằng ${h?.name||''}`:S.frame==='gold'?`${name} · ${h?.name||''}`:`${name} · Ngày ${fmt(day)}`;
  const st=stickers(v).map((e,i)=>`<span class="gd-sticker s${i}">${e}</span>`).join('');
  return `<section class="bk-card gd-selfie-card">
    <div class="segmented gd-frames" role="radiogroup" aria-label="Khung ảnh">${list.map(([id,,l])=>`<button type="button" role="radio" aria-checked="${S.frame===id}" class="${S.frame===id?'active':''}" data-gd="frame" data-frame="${id}">${esc(l)}</button>`).join('')}</div>
    <figure class="gd-selfie f-${S.frame}" style="--gd-shell:${esc(h?.color||'#9d86c9')}"><div class="gd-shot">${figure()}${S.frame==='duo'?figure(true):''}${st}</div><figcaption>${esc(caption)}</figcaption></figure>
    <div class="bk-actions">${btn('💾 Lưu ảnh về máy','save',{},'primary')}${btn('Quay lại','back',{},'ghost')}</div>
    <p class="bk-hint">Ảnh lưu trên máy bạn, không gửi đi đâu. Đăng lên Cả phố hay khoe bạn bè tùy bạn.</p></section>`;
}
/** The selfie as a PNG (the same frame, drawn on a canvas), downloaded or shared. */
async function saveSelfie(){
  const v=V(),h=item(v?.hand?.id);if(!v)return;
  const st=S.env.api.state,W=600,H=760,c=document.createElement('canvas');c.width=W;c.height=H;const x=c.getContext('2d');
  const shell=h?.color||'#9d86c9',gold=S.frame==='gold',dark=S.frame==='pro';
  x.fillStyle=gold?'#d4af37':dark?'#23272e':'#fffaf0';x.fillRect(0,0,W,H);
  if(gold){const g=x.createLinearGradient(0,0,W,H);g.addColorStop(0,'#f6e27a');g.addColorStop(.5,'#c9962c');g.addColorStop(1,'#f3d77a');x.fillStyle=g;x.fillRect(0,0,W,H);}
  const sky=x.createLinearGradient(0,40,0,600);sky.addColorStop(0,dark?'#3b4252':'#ffe3c9');sky.addColorStop(1,dark?'#5c6b7f':shell);
  x.fillStyle=sky;x.beginPath();x.roundRect?x.roundRect(36,36,W-72,560,22):x.rect(36,36,W-72,560);x.fill();
  const svg=figureSVG(held(st),st?.journey?.gender,{w:300,h:420}).replace('<svg ','<svg xmlns="http://www.w3.org/2000/svg" ');
  const img=await new Promise(done=>{const i=new Image();i.onload=()=>done(i);i.onerror=()=>done(null);i.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);});
  if(img){
    if(S.frame==='duo'){x.drawImage(img,40,150,260,364);x.save();x.translate(W-40,0);x.scale(-1,1);x.drawImage(img,0,150,260,364);x.restore();}
    else x.drawImage(img,W/2-150,150,300,420);
  }
  x.font='54px "Apple Color Emoji","Segoe UI Emoji",sans-serif';x.textAlign='center';
  stickers(v).forEach((e,i)=>x.fillText(e,[90,W-90,W-100][i],[110,120,560][i]));
  if(gold){x.fillStyle='#fff7d1';for(let i=0;i<14;i++){const px=50+((i*97)%(W-100)),py=50+((i*61)%520);x.fillText('✦',px,py);}}
  x.fillStyle=dark?'#f3f0e8':gold?'#4a3410':'#5a3d2b';x.font='700 30px "Be Vietnam Pro","Segoe UI",sans-serif';
  const name=st?.name||'Bạn';
  x.fillText(S.frame==='pro'?`Chụp bằng ${h?.name||''}`:`${name} · Ngày ${fmt(J().life_day)}`,W/2,650);
  x.font='600 22px "Be Vietnam Pro","Segoe UI",sans-serif';x.fillText('Phố Có Chuyện',W/2,700);
  const blob=await new Promise(done=>c.toBlob(done,'image/png'));if(!blob){S.flash={text:'Máy chưa lưu được ảnh. Thử lại nhé.',kind:'bad'};render();return;}
  const file=new File([blob],'selfie-pho-co-chuyen.png',{type:'image/png'});
  try{if(navigator.canShare?.({files:[file]})){await navigator.share({files:[file],title:'Selfie Phố Có Chuyện'});return;}}catch{/* cancelled: fall back to a download */}
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=file.name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),4000);
  S.flash={text:'Đã lưu ảnh selfie về máy.',kind:'good'};render();
}
