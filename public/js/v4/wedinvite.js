/** 💌 Thiệp mời cưới cả phố (game/wed_invite.py, live/wedinvite.py).
 *
 * Two parts in one lazy module:
 * - the card every other player sees once: a centred modal like "Có gì mới" (whatsnew.js) and the 🎁 gift card
 *   (gift.js): the couple's names, their own words, the party's time when there is one, "Chúc mừng 🎉", "Đi dự tiệc"
 *   and "Đóng". app.js asks GET /api/wedinvite after the game is up and when the live service says a new card is out
 *   (`wedinvite`), and loads this module only when a card is due. Opening a card POSTs /api/wedinvite/seen (it never
 *   comes back, on any device); "Chúc mừng" sends the same with cheer. It waits for a break point
 *   (v4/break-gate.js) like the other cards that open by themselves; same modal rules (focus kept inside, Esc closes,
 *   a backdrop tap does nothing, a tap in the first moment is ignored, reduced motion respected).
 * - the sheet that sends one: "💌 Gửi thiệp mời cưới cả phố" (Khu phố, Hôn nhân's party card): the couple's names,
 *   a text box with ideas, a live preview of the card, the price on the button and the payment sheet (payment.js:
 *   wallet first, or the bank account / card). POST /api/wedinvite/send with a request id kept until it lands, so a
 *   retried tap never pays twice. Every rule and number lives on the server; the sheet only shows them.
 * Names and the text come from players: always escaped. */
import {icon,escapeHTML as esc} from '../icons.js';
import {quiet as firstCustomers} from './onboard.js';
import {why,want,turn} from './break-gate.js';
import {confirmPurchase} from './payment.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const rid=()=>globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
const nowS=()=>Date.now()/1000;
const post=(api,url,body,retry=false)=>api.json(url,{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify(body),retry});

let E=null,cssReady=null;
function loadCss(){
  if(cssReady)return cssReady;
  if(document.querySelector('link[data-wi-css]'))return cssReady=Promise.resolve();
  const href=globalThis.__mnlBoot?.asset?.('/css/wedinvite.css')||'/css/wedinvite.css';
  const l=document.createElement('link');l.rel='stylesheet';l.href=href;l.dataset.wiCss='1';
  cssReady=new Promise(done=>{l.onload=l.onerror=()=>done();setTimeout(done,4000);});
  document.head.append(l);
  return cssReady;
}

/* ================================================================ the card (everyone else) */
const Q={queue:[],seen:new Set(),dlg:null,timer:0,calm:0,openedAt:0,back:null,fetching:null};

/** The card's markup; `preview`: inside the sending sheet (no ids, nothing to press). */
export function cardHTML(c,{preview=false}={}){
  const p=c.party,live=p&&nowS()>=p.at-300&&nowS()<p.end;
  const kicker=p?'Thiệp mời cưới':'Thông báo cưới';
  const when=p?`<p class="wi-when"><span>🎉 ${live?'Tiệc cưới đang diễn ra!':'Tiệc cưới lúc'}</span><b>${esc(p.at_label)}</b><small>Khu phố › Lịch cưới</small></p>`
    :`<p class="wi-when"><span aria-hidden="true">💍</span> Hai bạn đã nên duyên, chung vui cùng phố nhé!</p>`;
  const id=preview?'':' id="wiTitle"',tid=preview?'':' id="wiText"';
  const go=p?`<button type="button" class="btn cream big full" data-wi="go"${preview?' tabindex="-1"':''}>${live?'🎊 Vào dự ngay':'📅 Xem lịch cưới'}</button>`:'';
  return `<div class="wi-top"><span class="wi-hy" aria-hidden="true">囍</span><span class="wi-env" aria-hidden="true">💌</span>`+
    `<p class="wi-kicker">${kicker}</p><h2 class="wi-names"${id}><span>${esc(c.a)}</span><span class="wi-amp" aria-hidden="true">💞</span><span class="sr-only"> và </span><span>${esc(c.b)}</span></h2></div>`+
    `<blockquote class="wi-text"${tid}>${esc(c.text)}</blockquote>${when}`+
    `<div class="wi-foot"><button type="button" class="btn primary big full" data-wi="cheer"${preview?' tabindex="-1"':''}>Chúc mừng 🎉</button>${go}`+
    `<button type="button" class="btn ghost full" data-wi="close"${preview?' tabindex="-1"':''}>Đóng</button></div>`;
}

function blocker(doc=document){
  const s=E?.api?.state;if(!s)return 'loading';
  if(s.journey?.story&&!s.journey.intro)return 'intro';
  if(firstCustomers(s))return 'first-customers';
  if(doc.hidden)return 'hidden';
  if(doc.getElementById('tutLayer')?.isConnected)return 'tour';
  for(const d of doc.querySelectorAll('dialog[open]')){
    if(d===Q.dlg)continue;
    if(String(d.id||'').startsWith('tut'))return 'tour';
  }
  return why(Q.dlg,{strict:false},doc)||(turn('wedinvite')?'':'turn');
}

function build(){
  if(Q.dlg)return Q.dlg;
  const d=document.createElement('dialog');d.id='wiDialog';d.className='wi-dialog';
  d.setAttribute('aria-modal','true');d.setAttribute('aria-labelledby','wiTitle');d.setAttribute('aria-describedby','wiText');
  d.innerHTML='<div class="wi-card"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    const b=e.target.closest('button[data-wi]');if(!b||!d.contains(b))return;
    if(performance.now()-Q.openedAt<450){e.preventDefault();return;}   // a tap already on its way when the card popped up
    done(b.dataset.wi);
  });
  d.addEventListener('cancel',e=>{e.preventDefault();done('close');});   // Esc
  d.addEventListener('keydown',e=>{
    if(e.key!=='Tab')return;
    const f=[...d.querySelectorAll('button')];if(!f.length)return;
    const first=f[0],last=f[f.length-1],at=document.activeElement;
    if(e.shiftKey&&(at===first||!d.contains(at))){e.preventDefault();last.focus();}
    else if(!e.shiftKey&&(at===last||!d.contains(at))){e.preventDefault();first.focus();}
  });
  Q.dlg=d;return d;
}

async function show(){
  const c=Q.queue[0];if(!c)return;
  await loadCss();
  build();Q.back??=document.activeElement;
  Q.dlg.querySelector('.wi-card').innerHTML=cardHTML(c);
  if(!Q.dlg.open)Q.dlg.showModal();
  Q.openedAt=performance.now();
  Q.dlg.tabIndex=-1;Q.dlg.focus({preventScroll:true});
  // Shown: never again, on any device (retried; if it still fails it simply comes back on the next load).
  if(E?.api)post(E.api,'/api/wedinvite/seen',{id:c.id},true).catch(e=>console.warn('wedinvite seen:',e));
}

function done(what){
  const c=Q.queue.shift();if(!c)return;
  const api=E?.api;
  if(what==='cheer'&&api){
    post(api,'/api/wedinvite/seen',{id:c.id,cheer:true},true).catch(e=>console.warn('wedinvite cheer:',e));
    E.toast?.(`Đã gửi lời chúc mừng tới ${c.a} & ${c.b} 🎉`,'good');
  }
  if(what==='go'&&c.party){
    finish();
    const live=nowS()>=c.party.at-300&&nowS()<c.party.end;
    (live?import('./walk.js').then(m=>m.openWalk(E,{wedding:c.party.id})):import('./wedding.js').then(m=>m.openWeddings(E))).catch(e=>console.warn('wedinvite go:',e));
    return;
  }
  if(Q.queue.length){show();return;}
  finish();
}
function finish(){
  stop();want('wedinvite',Boolean(Q.queue.length));
  if(Q.dlg?.open)Q.dlg.close();
  if(Q.back?.isConnected&&typeof Q.back.focus==='function')Q.back.focus({preventScroll:true});
  Q.back=null;
  if(Q.queue.length)watch();
}

function check(){
  if(!Q.queue.length){stop();want('wedinvite',false);return;}
  if(Q.dlg?.open)return;
  if(blocker()){Q.calm=0;return;}   // two calm checks in a row (about a second): never between two sheets
  if(++Q.calm<2)return;
  stop();show();
}
function stop(){clearInterval(Q.timer);Q.timer=0;}
function watch(){if(Q.timer)return;want('wedinvite');Q.calm=0;Q.timer=setInterval(check,700);}

/** Cards from GET /api/wedinvite (app.js passes the first answer; the live frame asks again here). */
export function showCards(env,items){
  try{
    E=env||E;
    const fresh=(items||[]).filter(c=>c&&Number.isInteger(c.id)&&typeof c.text==='string'&&!Q.seen.has(c.id));
    for(const c of fresh){Q.seen.add(c.id);Q.queue.push(c);}
    Q.queue.sort((x,y)=>x.id-y.id);
    if(Q.queue.length){loadCss();if(!Q.dlg?.open)watch();}
  }catch(error){console.error('wedinvite:',error);}   // never in the way of the game
}
/** The live service says a new card is out: ask a little later (spread over a few seconds, not every page at once). */
export function onWedInvite(env){
  E=env||E;
  if(Q.fetching)return;
  Q.fetching=setTimeout(()=>{
    E.api.json('/api/wedinvite').then(d=>showCards(E,d?.items)).catch(()=>{}).finally(()=>{Q.fetching=null;});
  },400+Math.random()*6000);
}

/* ================================================================ the sending sheet (the couple) */
const C={dlg:null,me:null,text:'',rid:rid(),busy:false,flash:null,loading:false,err:''};

function sheet(){
  if(C.dlg)return C.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium wi-sheet';d.setAttribute('aria-labelledby','wi-title');
  d.innerHTML='<div class="wi-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-wic]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onSheet(el.dataset.wic,el.dataset);
  });
  d.addEventListener('input',e=>{if(e.target.name==='witext'){C.text=e.target.value;paint();}});
  d.addEventListener('close',()=>{C.flash=null;});
  C.dlg=d;return d;
}

/** Khu phố › "Thiệp mời cưới", Hôn nhân's party card. */
export async function openWedInvite(env){
  E=env;
  const s=document.getElementById('sheet');if(s?.open)env.closeSheet();
  await loadCss();
  const d=sheet();
  if(!d.open){d.showModal();d.scrollTop=0;}
  C.flash=null;render();load();
}
export async function wedInviteAction(action,data,el,env){
  if(action!=='wedInvite')return false;
  await openWedInvite(env);return true;
}

async function load(){
  C.loading=true;C.err='';render();
  try{C.me=await E.api.json('/api/wedinvite/me');}
  catch(e){C.err=e.status===404?'Máy chủ chưa có thiệp mời cưới. Tải lại trang sau ít phút nhé.':(e.message||'Chưa tải được. Thử lại nhé.');}
  finally{C.loading=false;render();}
}

const wallet=()=>Number(E?.api?.state?.journey?.wallet||0);
function preview(){
  const m=C.me||{},n=m.names||{a:'Bạn',b:'Người ấy'};
  const text=C.text.trim()||'Lời mời của bạn sẽ hiện ở đây…';
  return `<div class="wi-card wi-mini" aria-hidden="true">${cardHTML({a:n.a,b:n.b,text,party:m.party?{...m.party,end:m.party.at+600}:null},{preview:true})}</div>`;
}
function page(){
  const head=`<header class="sheet-head wi-head"><span class="wi-logo" aria-hidden="true">💌</span><div class="grow"><h2 id="wi-title">Gửi thiệp mời cưới cả phố</h2><p class="wi-sub">Cả phố thấy thiệp, mỗi người một lần.</p></div>`+
    `<button class="icon-btn" type="button" data-wic="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  const flash=C.flash?`<p class="wi-flash ${C.flash.kind}" role="status">${esc(C.flash.text)}</p>`:'';
  if(C.loading&&!C.me)return head+`<div class="sheet-body wi-body"><p class="wi-empty">⏳ Đang mở…</p></div>`;
  if(C.err)return head+`<div class="sheet-body wi-body"><p class="wi-flash bad">${esc(C.err)}</p><button type="button" class="btn" data-wic="retry">Thử lại</button></div>`;
  const m=C.me||{},n=m.names;
  const sent=m.sent?`<section class="wi-sent"><h3>💌 Thiệp bạn đã gửi</h3><blockquote>${esc(m.sent.text)}</blockquote>`+
    `<p>${m.sent.status==='deleted'?'Thiệp này đã được gỡ.':`🎉 <b>${fmt(m.sent.cheers)}</b> lời chúc mừng từ cả phố`}</p></section>`:'';
  if(!m.can){
    const more=!n?`<button type="button" class="btn" data-wic="marriage">💍 Mở Hôn nhân</button>`:'';
    return head+`<div class="sheet-body wi-body">${flash}<p class="wi-why">${esc(m.why||'Chưa gửi được thiệp lúc này.')}</p>${more}${sent}</div>`;
  }
  const party=m.party?`<p class="wi-line">🎉 Tiệc cưới lúc <b>${esc(m.party.at_label)}</b>: thiệp có nút <b>Xem lịch cưới</b> để mọi người tới dự.</p>`
    :`<p class="wi-line">💍 Chưa hẹn giờ tiệc nên thiệp là <b>thông báo cưới</b>. <button type="button" class="wi-link" data-wic="marriage">Hẹn giờ tiệc</button> trước nếu muốn mời mọi người tới dự.</p>`;
  const ideas=(m.presets||[]).map((t,i)=>`<button type="button" class="wi-idea" data-wic="idea" data-i="${i}">${esc(t)}</button>`).join('');
  const len=C.text.trim().length,price=Number(m.price||10000);
  return head+`<div class="sheet-body wi-body">${flash}
    <p class="wi-couple"><span>${esc(n.a)}</span> <span aria-hidden="true">💞</span> <span>${esc(n.b)}</span></p>${party}
    <label class="wi-label" for="wi-text">Lời mời của hai bạn</label>
    <textarea id="wi-text" name="witext" class="input wi-input" rows="4" maxlength="${Number(m.max)||200}" placeholder="Ví dụ: Tụi mình cưới rồi nè! Cả phố ghé chung vui nha 💕">${esc(C.text)}</textarea>
    <p class="wi-count" data-wi-count>${len}/${Number(m.max)||200}</p>
    <details class="wi-ideas"${C.text?'':' open'}><summary>Gợi ý lời mời</summary><div class="wi-idea-list">${ideas}</div></details>
    <h3 class="wi-label">Xem trước</h3><div class="wi-preview" data-wi-preview>${preview()}</div>
    ${sent}</div>
    <footer class="wi-bar"><small class="wi-why-s" data-wi-why>${esc(hint(len,price))}</small>
      <button type="button" class="btn primary big full" data-wic="send"${C.busy||hint(len,price)?' disabled':''}>💌 Gửi thiệp · ${fmt(price)} xu</button></footer>`;
}
function hint(len,price){
  const m=C.me||{};
  if(len<(Number(m.min)||10))return `Viết ít nhất ${Number(m.min)||10} ký tự nhé.`;
  const b=E?.api?.state?.journey?.bank;
  if(wallet()<price&&!(b?.open&&Number(b.balance)>=price)&&!(Number(b?.card?.available)>=price))return `Cần ${fmt(price)} xu trong ví hoặc tài khoản.`;
  return '';
}
function render(){
  if(!C.dlg)return;
  const y=C.dlg.querySelector('.wi-body')?.scrollTop;
  C.dlg.querySelector('.wi-root').innerHTML=page();
  if(y)C.dlg.querySelector('.wi-body').scrollTop=y;
  C.dlg.setAttribute('aria-busy',String(C.busy));
}
/** Typing: the counter, the preview and the button only (the text box keeps its caret). */
function paint(){
  const d=C.dlg;if(!d)return;
  const len=C.text.trim().length,m=C.me||{},price=Number(m.price||10000),h=hint(len,price);
  const cnt=d.querySelector('[data-wi-count]');if(cnt)cnt.textContent=`${len}/${Number(m.max)||200}`;
  const pv=d.querySelector('[data-wi-preview]');if(pv)pv.innerHTML=preview();
  const w=d.querySelector('[data-wi-why]');if(w)w.textContent=h;
  const b=d.querySelector('[data-wic="send"]');if(b)b.disabled=C.busy||Boolean(h);
}

async function onSheet(op,data){
  if(op==='close'){C.dlg.close();return;}
  if(op==='retry'){load();return;}
  if(op==='marriage'){C.dlg.close();E.act('marriage',{tab:'home'});return;}
  if(op==='idea'){const t=C.me?.presets?.[Number(data.i)];if(t){C.text=t;render();C.dlg.querySelector('#wi-text')?.focus({preventScroll:true});}return;}
  if(op!=='send'||C.busy)return;
  const m=C.me,n=m?.names,price=Number(m?.price||10000);
  if(!m?.can||!n)return;
  const how=await confirmPurchase(E,{title:'Gửi thiệp mời cả phố?',message:`Thiệp của ${n.a} & ${n.b} sẽ hiện cho mọi người trong phố, mỗi người một lần.`,
    label:`Gửi · ${fmt(price)} xu`,cost:price,noJoint:true});
  if(!how)return;
  C.busy=true;C.flash=null;render();
  try{
    const d=await post(E.api,'/api/wedinvite/send',{text:C.text,rid:C.rid,pay:how},true);
    if(d.state&&typeof d.revision==='number')E.api.accept({state:d.state,revision:d.revision});
    C.rid=rid();C.text='';
    C.flash={text:d.message||'Đã gửi thiệp 💌',kind:'good'};
    E.toast?.(d.message||'Đã gửi thiệp 💌','good');
    C.me=await E.api.json('/api/wedinvite/me').catch(()=>C.me);
  }catch(e){C.flash={text:e.message||'Chưa gửi được. Thử lại nhé.',kind:'bad'};}
  finally{C.busy=false;render();}
}
