/** ☕ Chỗ tiêu xu (game/spend.py): đi quán, spa, Rạp Mây, 🙏 công đức Chùa Gió Lành, 🎨 phong cách tuần. Story mode.
 * Every rule and price lives on the server; this file renders api.state.journey.spend with the static lists
 * (content.journey.spend), sends `jr_spend_*` and reads the weekly board (GET /api/congduc). Its own dialog, opened with
 * data-action="spend" (data-tab) or spendQuan / spendSpa / spendRap / spendChua / spendStyle (menu, town map doors).
 * Phone first, few words: emoji tabs, one pick per screen, one main button in the bottom bar with the price on it.
 * Styles: /css/spend.css. */
import {icon,escapeHTML as esc} from '../icons.js';
import {nameAttrs,frameAttrs,titleChip} from './style-tag.js';

const TABS=[['quan','☕','Đi quán'],['spa','💆','Spa'],['rap','🎬','Rạp Mây'],['chua','🙏','Công đức'],['style','🎨','Phong cách']];
export const ACTIONS={spend:'',spendQuan:'quan',spendSpa:'spa',spendRap:'rap',spendChua:'chua',spendStyle:'style'};
const KINDS=[['color','🌈','Màu tên'],['frame','🖼️','Khung hồ sơ'],['title','🏷️','Danh hiệu']];
const S={dlg:null,env:null,tab:'quan',shop:'',pick:{},kind:'color',amount:20,wish:'',anon:null,board:null,boardAt:0,busy:false,flash:null,listening:false};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const J=()=>S.env?.api?.state?.journey||{};
const V=()=>J().spend;
const CAT=()=>S.env?.api?.content?.journey?.spend||null;
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');

let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=link('/css/spend.css','sd-css');

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium sd-sheet';d.setAttribute('aria-labelledby','sd-title');
  d.innerHTML='<div class="sd-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-sd]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.sd,el.dataset);
  });
  d.addEventListener('change',e=>{
    const t=e.target;
    if(t.name==='wish'){S.wish=t.value;}
    else if(t.name==='anon'){S.anon=t.checked;}
    else if(t.name==='amount'){const n=Math.floor(Number(t.value));if(Number.isFinite(n))S.amount=Math.max(CAT()?.give?.min||5,Math.min(CAT()?.give?.max||1e6,n));render();}
  });
  d.addEventListener('close',()=>{S.flash=null;});
  S.dlg=d;return d;
}
export async function openSpend(env,tab){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';env.api.addEventListener('state',()=>{const key=JSON.stringify([J().wallet,J().spend,J().bank?.balance]);if(key===seen)return;seen=key;if(S.dlg?.open&&!S.busy)render();});
  }
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();
  if(TABS.some(t=>t[0]===tab))S.tab=tab;
  S.flash=null;
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
  if(S.tab==='chua')loadBoard();
}
export async function spendAction(action,data,el,env){
  if(!(action in ACTIONS))return false;
  await openSpend(env,ACTIONS[action]||data?.tab);return true;
}

async function loadBoard(force=false){
  if(!force&&S.board&&Date.now()-S.boardAt<15000)return;
  S.boardAt=Date.now();
  try{S.board=await S.env.api.json('/api/congduc');}catch{S.board=S.board||{error:true};}
  if(S.dlg?.open&&S.tab==='chua')render();
}
async function send(action,payload={}){
  const {api}=S.env;S.busy=true;render();
  try{
    const r=await api.command(action,payload);
    S.flash={text:[r.message,...(r.effects||[]).filter(Boolean).map(x=>`💬 ${x}`)].filter(Boolean).join(' '),kind:'good'};
    return r;
  }catch(e){S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;render();}
}

/* ---- picks ---- */
const shopOf=()=>{const c=CAT();if(!c)return null;return c.shops.find(x=>x.id===S.shop)||c.shops[0];};
function pickOf(tab){
  const c=CAT();if(!c)return null;
  if(tab==='quan'){const sh=shopOf();return sh.items.find(x=>x.id===S.pick.quan)||sh.items[0];}
  if(tab==='spa')return c.spa.find(x=>x.id===S.pick.spa)||c.spa[0];
  if(tab==='style'){const list=styleList();return list.find(x=>x.id===S.pick.style)||list[0];}
  return null;
}
const styleList=()=>{const c=CAT();return S.kind==='color'?c.colors:S.kind==='frame'?c.frames:c.titles;};
const daysLeft=until=>Math.max(0,Math.ceil((until-Date.now()/1000)/86400));
const guest=()=>!S.env?.api?.account?.username;   // a guest's gift is always Ẩn danh on the board (game/spend.py _name)
const anonNow=()=>guest()||(S.anon??(S.amount<(CAT()?.give?.anon_under||50)));
/** Money reasons live here (game/spend.py public stays small): T0 from the wallet only, the rest wallet then bank. */
const cash=()=>Number(J().wallet)||0;
const ready=()=>cash()<0?0:cash()+(Number(J().bank?.balance)||0);
const cashWhy=price=>cash()>=price?'':'Chưa đủ xu';
const readyWhy=price=>cash()<0?'Ví đang nợ':ready()>=price?'':`Còn thiếu ${fmt(price-ready())} xu`;

/** The bottom bar's one button: [label, op, why (disabled reason)]. */
function main(v){
  const c=CAT(),it=pickOf(S.tab);
  switch(S.tab){
    case'quan':return [`Gọi · ${fmt(it.price)} xu`,'eat',(v.full||[]).includes(it.id)?(it.full?'Bụng no rồi':'Đang tỉnh rồi'):cashWhy(it.price)];
    case'spa':return [`Làm · ${fmt(it.price)} xu`,'spa',cashWhy(it.price)];
    case'rap':return v.seen?['Tuần này xem rồi','film','✓']:[`Mua vé · ${fmt(c.film_price)} xu`,'film',cashWhy(c.film_price)];
    case'chua':return [`Công đức · ${fmt(S.amount)} xu`,'give',readyWhy(S.amount)];
    case'style':{const until=v.own?.[it.id],worn=v.wear?.[S.kind]===it.id;
      if(until&&!worn)return ['Dùng','wear',''];
      return [`${until?'Gia hạn':'Mua 7 ngày'} · ${fmt(it.price)} xu`,'style',v.lock?.[it.id]||readyWhy(it.price)];}
  }
  return ['','',''];
}

async function onClick(op,data){
  const v=V()||{};
  switch(op){
    case'close':S.dlg.close();return;
    case'tab':S.tab=data.tab;S.flash=null;render();S.dlg.querySelector('.sd-body')?.scrollTo?.(0,0);if(S.tab==='chua')loadBoard();return;
    case'shop':S.shop=data.id;S.pick.quan=null;render();return;
    case'pick':S.pick[S.tab]=data.id;render();return;
    case'kind':S.kind=data.kind;S.pick.style=null;render();return;
    case'amount':S.amount=Number(data.n)||S.amount;render();return;
    case'players':S.dlg.close();S.env.act?.('social');return;   // 🏪 real players' places: Phố nghề (v4/social.js)
    case'unwear':send('jr_spend_wear',{kind:S.kind,id:null});return;
    case'go':{
      const [,what]=main(v),it=pickOf(S.tab);
      if(what==='eat'){const sh=shopOf();await send('jr_spend_eat',{shop:sh.id,item:it.id});}
      else if(what==='spa')await send('jr_spend_spa',{item:it.id});
      else if(what==='film')await send('jr_spend_film',{});
      else if(what==='give'){const r=await send('jr_spend_give',{amount:S.amount,wish:S.wish,anon:anonNow(),confirm:true});if(r)loadBoard(true);}
      else if(what==='style')await send('jr_spend_style',{id:it.id,confirm:true});
      else if(what==='wear')await send('jr_spend_wear',{kind:S.kind,id:it.id});
      return;}
  }
}

/* ---- rendering ---- */
function render(){
  if(!S.dlg)return;
  const body=S.dlg.querySelector('.sd-body'),y=body?.scrollTop;
  S.dlg.querySelector('.sd-root').innerHTML=page();
  if(y)S.dlg.querySelector('.sd-body').scrollTop=y;
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
function page(){
  const v=V(),c=CAT(),t=TABS.find(x=>x[0]===S.tab)||TABS[0];
  const head=`<header class="sheet-head sd-head"><span class="sd-logo" aria-hidden="true">${t[1]}</span><div class="grow"><h2 id="sd-title">${esc(t[2])}</h2></div>
    <span class="sd-wallet" title="Ví">👛 ${fmt(Math.max(0,J().wallet||0))}</span><button class="icon-btn" type="button" data-sd="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  if(!v||!c)return head+`<div class="sheet-body sd-body"><p class="sd-empty">⏳</p></div>`;   // an older server
  if(!v.story)return head+`<div class="sheet-body sd-body"><p class="sd-empty">Chỉ có trong hành trình.</p></div>`;
  const tabs=`<nav class="sd-tabs" role="tablist" aria-label="Chỗ tiêu xu">${TABS.map(([id,e,l])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" aria-label="${esc(l)}" title="${esc(l)}" class="${S.tab===id?'on':''}" data-sd="tab" data-tab="${id}">${e}</button>`).join('')}</nav>`;
  const inner=S.tab==='quan'?quan(v,c):S.tab==='spa'?spa(v,c):S.tab==='rap'?rap(v,c):S.tab==='chua'?chua(v,c):style(v,c);
  const [label,,why]=main(v);
  const bar=`<footer class="sd-bar">${why&&why!=='✓'?`<small class="sd-why">${esc(why)}</small>`:''}<button type="button" class="btn primary big sd-main" data-sd="go"${S.busy||why?' disabled':''}>${esc(label)}</button></footer>`;
  const flash=`<p class="sd-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  return head+tabs+`<div class="sheet-body sd-body">${flash}${inner}</div>`+bar;
}
const fx=(full,wake,spirit)=>[full?`🍚+${full}`:'',wake?`⚡+${wake}`:'',spirit?`😊+${spirit}`:''].filter(Boolean).map(x=>`<i>${x}</i>`).join('');
function row(it,on,extra=''){
  return `<button type="button" class="sd-item${on?' on':''}" data-sd="pick" data-id="${esc(it.id)}" aria-pressed="${on}"><span class="sd-ico" aria-hidden="true">${esc(it.emoji)}</span><b>${esc(it.name)}</b><span class="sd-fx">${extra}</span><em>${fmt(it.price)}</em></button>`;
}
function quan(v,c){
  const sh=shopOf(),it=pickOf('quan'),n=v.stamps?.[sh.id]||0,k=v.stickers?.[sh.id]||0,first=!(v.today||[]).includes('cafe');
  const chips=`<div class="sd-chips">${c.shops.map(x=>`<button type="button" class="sd-chip${x.id===sh.id?' on':''}" data-sd="shop" data-id="${esc(x.id)}" aria-label="${esc(x.name)}" title="${esc(x.name)}" aria-pressed="${x.id===sh.id}">${esc(x.emoji)}</button>`).join('')}</div>`;
  const dots=Array.from({length:c.stamp_card},(_,i)=>`<i class="${i<n?'on':''}"></i>`).join('');
  const card=`<section class="sd-card"><h3>${esc(sh.emoji)} ${esc(sh.name)}</h3><p class="sd-stamps" aria-label="Thẻ tích điểm ${n}/${c.stamp_card}">${dots}${k?`<span class="sd-sticker" title="Nhãn dán">🏷️×${k}</span>`:''}</p>
    <div class="sd-list">${sh.items.map(x=>row(x,x.id===it.id,fx(x.full,x.wake,first?(x.price>=28?2:1):0))).join('')}</div></section>`;
  return chips+card+`<button type="button" class="sd-link" data-sd="players">🏪 Quán người chơi</button>`;
}
function spa(v,c){
  const it=pickOf('spa'),first=!(v.today||[]).includes('spa');
  return `<section class="sd-card"><h3>💆 ${esc(c.spa_name)}</h3><div class="sd-list">${c.spa.map(x=>row(x,x.id===it.id,fx(0,x.wake,first?c.spa_spirit:0))).join('')}</div></section>`;
}
function rap(v,c){
  const f=c.films.find(x=>x.id===v.film)||c.films[0],stubs=Number(v.stubs)||0;
  return `<section class="sd-card sd-film"><div class="sd-poster" aria-hidden="true">${esc(f.emoji)}</div><h3>${esc(f.name)}</h3>
    <p class="sd-fx">${v.seen?'<i>✓</i>':fx(0,0,c.film_spirit)}${stubs?`<i title="Cuống vé">🎟️×${stubs}</i>`:''}</p></section>`;
}
function chua(v,c){
  const g=c.give,b=S.board;
  const amounts=`<div class="sd-chips sd-amounts">${g.presets.map(n=>`<button type="button" class="sd-chip${S.amount===n?' on':''}" data-sd="amount" data-n="${n}" aria-pressed="${S.amount===n}">${fmt(n)}</button>`).join('')}
    <label class="sd-num"><span class="sr-only">Số xu</span><input type="number" name="amount" inputmode="numeric" min="${g.min}" max="${g.max}" step="1" value="${S.amount}"></label></div>`;
  const wish=`<label class="sd-select"><span class="sr-only">Lời cầu</span><select name="wish"><option value="">🙏 …</option>${g.wishes.map(w=>`<option value="${esc(w.id)}"${S.wish===w.id?' selected':''}>${esc(w.text)}</option>`).join('')}</select></label>`;
  const anon=guest()?'':`<label class="sd-toggle"><input type="checkbox" name="anon"${anonNow()?' checked':''}><span>Ẩn danh</span></label>`;
  let board='<p class="sd-empty">⏳</p>';
  if(b&&!b.error){
    const rows=(b.top||[]).slice(0,5).map((r,i)=>`<li class="${r.me?'me':''}"><span>${i+1}</span><b data-no-translate>${esc(r.name)}</b><em>${fmt(r.xu)}</em></li>`).join('');
    board=`<h4>📜 Bảng tuần · ${fmt(b.xu)} xu</h4>${rows?`<ol class="sd-board">${rows}</ol>`:''}${b.mine?`<p class="sd-mine">Bạn: ${fmt(b.mine)} xu</p>`:''}`;
  }else if(b?.error)board='';
  return `<section class="sd-card"><h3>🛕 Chùa Gió Lành</h3>${amounts}<div class="sd-row">${wish}${anon}</div></section><section class="sd-card">${board}</section>`;
}
function style(v,c){
  const it=pickOf('style'),api=S.env.api,name=api.state?.name||'Bạn',now=Date.now()/1000;
  const kinds=`<div class="sd-chips sd-kinds">${KINDS.map(([k,e,l])=>`<button type="button" class="sd-chip${S.kind===k?' on':''}" data-sd="kind" data-kind="${k}" aria-label="${esc(l)}" title="${esc(l)}" aria-pressed="${S.kind===k}">${e}</button>`).join('')}</div>`;
  // the preview: what is worn, with the picked item tried on
  const st={...(v.st||{})};st[S.kind==='color'?'c':S.kind==='frame'?'f':'t']=it.id;
  const fr=frameAttrs(api,st);
  const preview=`<div class="sd-preview"><span class="sd-av${fr.cls}"${fr.attrs} aria-hidden="true">🙂</span><b${nameAttrs(api,st,'sd-pname')} data-no-translate>${esc(name)}</b>${titleChip(api,st)}</div>`;
  const tiles=styleList().map(x=>{
    const until=v.own?.[x.id],left=until&&until>now?daysLeft(until):0,worn=v.wear?.[S.kind]===x.id&&left,lock=(v.lock?.[x.id]||'').includes('để mở');
    const art=S.kind==='color'?`<span${nameAttrs(api,{c:x.id},'sd-swatch')}>Aa</span>`:S.kind==='frame'?`<span class="sd-ring${frameAttrs(api,{f:x.id}).cls}"${frameAttrs(api,{f:x.id}).attrs}></span>`:`<span class="sd-tchip">${esc(x.emoji)} ${esc(x.name)}</span>`;
    return `<button type="button" class="sd-tile${x.id===it.id?' on':''}${worn?' worn':''}" data-sd="pick" data-id="${esc(x.id)}" aria-pressed="${x.id===it.id}" aria-label="${esc(x.name)}" title="${esc(x.name)}">${art}<small>${lock?'🔒':left?`${worn?'✓ ':''}${left} ngày`:fmt(x.price)}</small></button>`;
  }).join('');
  const off=v.wear?.[S.kind]&&v.own?.[v.wear[S.kind]]>now?`<button type="button" class="sd-link" data-sd="unwear">Cất</button>`:'';
  return kinds+`<section class="sd-card">${preview}<div class="sd-tiles sd-${S.kind}">${tiles}</div>${off}</section>`;
}
