/** 🛍️ Mua sắm (game/lux.py, game/estates.py): du lịch nước ngoài, bộ sưu tập, dinh thự, phi cơ, tiệc, khóa học,
 * 🎆 Mạnh Thường Quân. Story mode. Every rule and price lives on the server; this file renders api.state.journey.lux
 * with the static lists (content.journey.lux), sends `jr_lux_*` and reads the weekly board (GET /api/mtq).
 * Its own dialog, opened with data-action="lux" (data-tab) or luxTrip / luxSuu / luxNha / luxBay / luxTiec / luxHoc /
 * luxMtq (menu, town map doors). Phone first, few words: emoji tabs and chips, one pick per screen, one main button in
 * the bottom bar with the price on it; the visa's paperwork rules sit behind "?". Styles: /css/spend.css + /css/lux.css. */
import {icon,escapeHTML as esc} from '../icons.js';
import {withWhy,whyTap} from '../ui-kit.js';
// Typed numbers in the − N + steppers (owner 07/10: "cho nhập số nhé").
import {qtyBox,QTY,afterTap} from '../qty-input.js';

const TABS=[['trip','✈️','Du lịch'],['suu','💎','Sưu tập'],['nha','🏰','Dinh thự'],['bay','🛫','Phi cơ & du thuyền'],['tiec','🎉','Mở tiệc'],['hoc','🎓','Khóa học'],['mtq','🎆','Mạnh Thường Quân']];
export const ACTIONS={lux:'',luxTrip:'trip',luxSuu:'suu',luxNha:'nha',luxBay:'bay',luxTiec:'tiec',luxHoc:'hoc',luxMtq:'mtq'};
const S={dlg:null,env:null,tab:'trip',country:'',cls:'pho_thong',docs:{},iv:null,answers:[],souv:'',set:'',piece:'',estate:'',fly:'',
  pkind:'sinh_nhat',tier:'binh_dan',guests:20,course:'',give:'phao_hoa',size:'nho',slot:0,msg:'me',amount:10000,anon:false,
  board:null,boardAt:0,busy:false,flash:null,listening:false};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const J=()=>S.env?.api?.state?.journey||{};
const V=()=>J().lux;
const CAT=()=>S.env?.api?.content?.journey?.lux||null;
const day=()=>Number(J().life_day)||1;

let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=Promise.all([link('/css/spend.css','sd-css'),link('/css/lux.css','lx-css')]);

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium sd-sheet lx-sheet';d.setAttribute('aria-labelledby','lx-title');
  d.innerHTML='<div class="sd-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-lx]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();if(el.dataset.why){whyTap(el);return;}   // dimmed with a reason (docs/UI_KIT.md): say why, send nothing
    onClick(el.dataset.lx,el.dataset);
  });
  d.addEventListener('change',e=>{
    const t=e.target;
    if(t.name==='msg')S.msg=t.value;
    else if(t.name==='anon')S.anon=t.checked;
    else if(t.name==='amount'){const g=give('thu_vien'),n=Math.floor(Number(t.value));if(Number.isFinite(n))S.amount=Math.max(g.min,Math.min(g.max,n));render();}
  });
  d.addEventListener('close',()=>{S.flash=null;S.iv=null;});
  S.dlg=d;return d;
}
export async function openLux(env,tab){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';env.api.addEventListener('state',()=>{const key=JSON.stringify([J().wallet,J().lux,J().bank?.balance]);if(key===seen)return;seen=key;if(S.dlg?.open&&!S.busy)render();});
  }
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();
  if(TABS.some(t=>t[0]===tab))S.tab=tab;
  S.flash=null;S.iv=null;
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
  if(S.tab==='mtq')loadBoard();
}
export async function luxAction(action,data,el,env){
  if(!(action in ACTIONS))return false;
  await openLux(env,ACTIONS[action]||data?.tab);return true;
}
async function loadBoard(force=false){
  if(!force&&S.board&&Date.now()-S.boardAt<15000)return;
  S.boardAt=Date.now();
  try{S.board=await S.env.api.json('/api/mtq');}catch{S.board=S.board||{error:true};}
  if(S.dlg?.open&&S.tab==='mtq')render();
}
async function send(action,payload={}){
  const {api}=S.env;S.busy=true;render();
  try{
    const r=await api.command(action,payload);
    S.flash={text:[r.message,...(r.effects||[]).filter(Boolean).map(x=>`💬 ${x}`)].filter(Boolean).join(' '),kind:r.refused?'bad':'good'};
    return r;
  }catch(e){S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;render();}
}

/* ---- the catalogue ---- */
const country=()=>{const c=CAT().countries;return c.find(x=>x.id===S.country)||c[0];};
const pieceSet=()=>{const c=CAT().sets;return c.find(x=>x.id===S.set)||c[0];};
const piece=()=>{const st=pieceSet();return st.items.find(x=>x.id===S.piece)||st.items[0];};
const estate=()=>{const c=CAT().estates;return c.find(x=>x.id===(S.estate||V()?.live))||c[0];};   // the villa you live in first
const fly=()=>{const c=CAT().assets;return c.find(x=>x.id===S.fly)||c[0];};
const course=()=>{const c=CAT().courses;return c.find(x=>x.id===S.course)||c[0];};
const give=id=>CAT().gives.find(x=>x.id===(id||S.give))||CAT().gives[0];
const tier=()=>CAT().party_tiers.find(x=>x.id===S.tier)||CAT().party_tiers[0];
const pkind=()=>CAT().party_kinds.find(x=>x.id===S.pkind)||CAT().party_kinds[0];
const own=id=>(V()?.own||{})[id];
const today=()=>V()?.today||[];
const month=(price,bp)=>Math.round(price*bp/10000);

/* ---- money reasons (game/lux.py ready_why: the wallet, then the bank account; never with the wallet in debt) ---- */
const cash=()=>Number(J().wallet)||0;
const ready=()=>cash()<0?0:cash()+(Number(J().bank?.balance)||0);
const readyWhy=price=>cash()<0?'Ví đang nợ':ready()>=price?'':`Còn thiếu ${fmt(price-ready())} xu`;
const can=why=>why?{why}:true;   // a side button (📷, 🛡️) dimmed but tappable: game/lux.py refuses the same

/** Visa paperwork: the docs this country wants, the interview questions of the next application. */
function docsOf(c){const k=c.id;S.docs[k]??=new Set();return S.docs[k];}
const asks=c=>c.interview?(V()?.ask||[]):[];
const answered=c=>asks(c).length===S.answers.filter(a=>a!=null).length&&S.answers.length===asks(c).length;
const visaLeft=c=>(V()?.visa||{})[c.id]||0;
const tripPrice=(c,cls)=>c.trip*(CAT().classes.find(x=>x.id===cls)?.mult||1);
const insurePrice=c=>Math.floor(c.trip*CAT().insure_pct/100);
const souvOpen=c=>today().includes(`in_${c.id}`);

/** The bottom bar's one button: [label, op, why (disabled reason)]. */
function main(v){
  switch(S.tab){
    case'trip':{const c=country();
      if(visaLeft(c)){
        if(souvOpen(c)&&S.souv){const it=CAT().souvenirs[c.id].find(x=>x.id===S.souv);return [`Mua quà · ${fmt(it.price)} xu`,'souv',readyWhy(it.price)];}
        const p=tripPrice(c,S.cls);return today().includes('trip')?['Mai bay tiếp','trip','Hôm nay đã đi']:[`Bay · ${fmt(p)} xu`,'trip',readyWhy(p)];}
      if(asks(c).length&&!answered(c))return [S.iv==null?'🗣️ Phỏng vấn':'Trả lời câu hỏi','iv',S.iv==null?'':'Chọn một câu trả lời'];
      return [`Nộp hồ sơ · ${fmt(c.visa)} xu`,'visa',docsOf(c).size?readyWhy(c.visa):'Chọn giấy tờ'];}
    case'suu':{const it=piece(),o=own(it.id);
      if(o)return pieceSet().id===CAT().wine?['🍾 Khui chai','open','']:[`Bán · ${fmt(o.sell)} xu`,'sell',''];
      return [`Mua · ${fmt(it.price)} xu`,'buy',readyWhy(it.price)];}
    case'nha':{const e=estate(),o=own(e.id);
      if(!o)return [`Mua · ${fmt(e.price)} xu`,'buy',readyWhy(e.price)];
      return V()?.live===e.id?['🏠 Vào nhà','enter','']:['Dọn về ở','live',''];}
    case'bay':{const a=fly(),o=own(a.id);
      if(!o)return [`Mua · ${fmt(a.price)} xu`,'buy',readyWhy(a.price)];
      return today().includes('use')?['Mai đi tiếp','use','Hôm nay đi rồi']:[`${a.verb} · ${fmt(a.use)} xu`,'use',readyWhy(a.use)];}
    case'tiec':{const k=pkind(),p=tier().base+tier().guest*S.guests;
      if(today().includes('party'))return ['Mai mở tiếp','party','Hôm nay mở tiệc rồi'];
      return [`Mở tiệc · ${fmt(p)} xu`,'party',readyWhy(p)];}
    case'hoc':{const c=course(),n=(V()?.course||{})[c.id];
      if(n==null)return [`Đăng ký · ${fmt(c.price)} xu`,'course',readyWhy(c.price)];
      if(n>=c.lessons)return ['✓ Tốt nghiệp','study','✓'];
      return today().includes(`st_${c.id}`)?['Mai học tiếp','study','Hôm nay học rồi']:[`Học buổi ${n+1}`,'study',''];}
    case'mtq':{const g=give(),price=g.sizes?.length?g.sizes.find(z=>z.id===S.size)?.price||g.sizes[0].price:g.min?S.amount:g.price;
      const wait=g.id==='phao_hoa'?Number(S.board?.fw_wait)||0:0;
      if(wait)return [`Đợi ${Math.ceil(wait/60)} phút`,'give','Trời đang có pháo hoa'];
      if(g.slots&&!S.slot)return ['Chọn một chỗ','give','Chọn số'];
      return [`Tài trợ · ${fmt(price)} xu`,'give',readyWhy(price)];}
  }
  return ['','',''];
}

async function onClick(op,data){
  const v=V()||{};
  switch(op){
    case'close':S.dlg.close();return;
    case'tab':S.tab=data.tab;S.flash=null;S.iv=null;render();S.dlg.querySelector('.sd-body')?.scrollTo?.(0,0);if(S.tab==='mtq')loadBoard();return;
    case'country':S.country=data.id;S.iv=null;S.answers=[];S.souv='';render();return;
    case'cls':S.cls=data.id;render();return;
    case'doc':{const set=docsOf(country());set.has(data.id)?set.delete(data.id):set.add(data.id);render();return;}
    case'answer':{S.answers[S.iv]=Number(data.n);S.iv=S.iv+1<asks(country()).length?S.iv+1:null;render();return;}
    case'photo':await send('jr_lux_photo',{});return;
    case'insure':await send('jr_lux_insure',{country:country().id});return;
    case'souv':S.souv=S.souv===data.id?'':data.id;render();return;
    case'set':S.set=data.id;S.piece='';render();return;
    case'piece':S.piece=data.id;render();return;
    case'estate':S.estate=data.id;render();return;
    case'fly':S.fly=data.id;render();return;
    case'pkind':S.pkind=data.id;render();return;
    case'tier':S.tier=data.id;render();return;
    case'guests':{const g=CAT().guests;S.guests=Math.max(g.min,Math.min(g.max,S.guests+Number(data.d)*g.step));render();return;}
    case'guestsSet':{const g=CAT().guests;const n=Math.floor(Number(data.n))||g.min;S.guests=Math.max(g.min,Math.min(g.max,g.min+Math.round((n-g.min)/g.step)*g.step));afterTap(render);return;}   // typed
    case'course':S.course=data.id;render();return;
    case'give':S.give=data.id;S.slot=0;render();return;
    case'size':S.size=data.id;render();return;
    case'slot':S.slot=Number(data.n);render();return;
    case'amount':S.amount=Number(data.n)||S.amount;render();return;
    case'sell':{const id=data.id;await send('jr_lux_sell',{id,confirm:true});return;}
    case'leave':await send('jr_lux_live',{id:null});return;
    case'go':{
      const [,what]=main(v);
      if(what==='trip')await send('jr_lux_trip',{country:country().id,cls:S.cls,confirm:true});
      else if(what==='souv')await send('jr_lux_souv',{id:S.souv});
      else if(what==='iv'){S.iv=0;S.answers=[];render();}
      else if(what==='visa'){const c=country(),r=await send('jr_lux_visa',{country:c.id,docs:[...docsOf(c)],answers:asks(c).map((_,i)=>S.answers[i]??0),confirm:true});if(r){S.answers=[];S.iv=null;}}
      else if(what==='buy'){const id=S.tab==='suu'?piece().id:S.tab==='nha'?estate().id:fly().id;await send('jr_lux_buy',{id,confirm:true});}
      else if(what==='sell')await send('jr_lux_sell',{id:piece().id,confirm:true});
      else if(what==='open')await send('jr_lux_open',{id:piece().id,confirm:true});
      else if(what==='live')await send('jr_lux_live',{id:estate().id});
      else if(what==='enter'){S.dlg.close();(await import('./reno.js')).openReno(S.env,'decor');}
      else if(what==='use')await send('jr_lux_use',{id:fly().id});
      else if(what==='party')await send('jr_lux_party',{kind:S.pkind,tier:S.tier,guests:S.guests,confirm:true});
      else if(what==='course')await send('jr_lux_course',{id:course().id,confirm:true});
      else if(what==='study')await send('jr_lux_study',{id:course().id});
      else if(what==='give'){const g=give(),p={kind:g.id,anon:S.anon,confirm:true};
        if(g.sizes?.length)p.size=S.size;if(g.slots){p.slot=S.slot;p.msg=S.msg;}if(g.min)p.amount=S.amount;
        const r=await send('jr_lux_give',p);if(r){S.slot=0;loadBoard(true);}}
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
const chip=(op,id,label,on,title='')=>`<button type="button" class="sd-chip${on?' on':''}" data-lx="${op}" data-id="${esc(id)}" aria-pressed="${on}"${title?` aria-label="${esc(title)}" title="${esc(title)}"`:''}>${label}</button>`;
const row=(op,id,ico,name,right,on,extra='')=>`<button type="button" class="sd-item${on?' on':''}" data-lx="${op}" data-id="${esc(id)}" aria-pressed="${on}"><span class="sd-ico" aria-hidden="true">${ico}</span><b>${esc(name)}</b><span class="sd-fx">${extra}</span><em>${right}</em></button>`;
const help=lines=>`<details class="lx-help"><summary aria-label="Hướng dẫn">?</summary><ul>${lines.map(l=>`<li>${esc(l)}</li>`).join('')}</ul></details>`;

function page(){
  const v=V(),c=CAT(),t=TABS.find(x=>x[0]===S.tab)||TABS[0];
  const head=`<header class="sheet-head sd-head"><span class="sd-logo" aria-hidden="true">${t[1]}</span><div class="grow"><h2 id="lx-title">${esc(t[2])}</h2></div>
    <span class="sd-wallet" title="Ví">👛 ${fmt(Math.max(0,J().wallet||0))}</span><button class="icon-btn" type="button" data-lx="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  if(!v||!c)return head+`<div class="sheet-body sd-body"><p class="sd-empty">⏳</p></div>`;
  if(!v.story)return head+`<div class="sheet-body sd-body"><p class="sd-empty">Chỉ có trong hành trình.</p></div>`;
  const tabs=`<nav class="sd-tabs lx-tabs" role="tablist" aria-label="Mua sắm">${TABS.map(([id,e,l])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" aria-label="${esc(l)}" title="${esc(l)}" class="${S.tab===id?'on':''}" data-lx="tab" data-tab="${id}">${e}</button>`).join('')}</nav>`;
  const inner={trip,suu,nha,bay,tiec,hoc,mtq}[S.tab](v,c);
  const [label,,why]=main(v);
  const bar=`<footer class="sd-bar">${why&&why!=='✓'?`<small class="sd-why">${esc(why)}</small>`:''}<button type="button" class="btn primary big sd-main" data-lx="go"${S.busy||why?' disabled':''}>${esc(label)}</button></footer>`;
  const flash=`<p class="sd-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  return head+tabs+`<div class="sheet-body sd-body">${flash}${inner}</div>`+bar;
}

function trip(v,c){
  const co=country(),left=visaLeft(co),n=(v.trips||{})[co.id]||0;
  const chips=`<div class="sd-chips">${c.countries.map(x=>chip('country',x.id,x.flag,x.id===co.id,x.name)).join('')}</div>`;
  const head=`<h3>${co.flag} ${esc(co.name)}</h3><p class="lx-sub">🛂 ${left?`còn ${left} ngày`:'chưa có visa'}${n?` · 📕×${n}`:''}</p>`;
  if(left){
    const cls=c.classes.map(x=>row('cls',x.id,x.emoji,x.name,fmt(tripPrice(co,x.id)),x.id===S.cls)).join('');
    const sv=souvOpen(co)?`<h4>🎁 Quà</h4><div class="sd-list">${c.souvenirs[co.id].map(x=>row('souv',x.id,x.emoji,x.name,fmt(x.price),x.id===S.souv,(v.souv||{})[x.id]?`<i>×${v.souv[x.id]}</i>`:'')).join('')}</div>`:'';
    return chips+`<section class="sd-card">${head}${souvOpen(co)?sv:`<div class="sd-list">${cls}</div>`}</section>`;
  }
  if(S.iv!=null&&asks(co).length){
    const q=c.interview[asks(co)[S.iv]];
    return chips+`<section class="sd-card">${head}<h4>🗣️ ${esc(q.q)}</h4><div class="sd-list">${q.a.map((a,i)=>`<button type="button" class="sd-item" data-lx="answer" data-n="${i}"><b>${esc(a)}</b></button>`).join('')}</div></section>`;
  }
  const set=docsOf(co),photoOld=!v.photo||day()-v.photo>=c.photo.days;
  const docs=c.docs.map(d=>`<button type="button" class="sd-chip lx-doc${set.has(d.id)?' on':''}" data-lx="doc" data-id="${d.id}" aria-pressed="${set.has(d.id)}">${d.emoji} ${esc(d.name)}</button>`).join('');
  const tools=[photoOld?withWhy(`<button type="button" class="sd-link" data-lx="photo">📷 Chụp ảnh · ${c.photo.price}</button>`,can(cash()<c.photo.price?'Ví chưa đủ':'')):'',   // the photo is paid from the wallet only
    co.docs.includes('bao_hiem')&&v.ins!==co.id?withWhy(`<button type="button" class="sd-link" data-lx="insure">🛡️ Bảo hiểm · ${fmt(insurePrice(co))}</button>`,can(readyWhy(insurePrice(co)))):''].join('');
  const rules=help([`Lãnh sự cần: ${co.docs.map(d=>c.docs.find(x=>x.id===d).name).join(', ')}.`,
    `Ảnh thẻ chụp chưa quá ${c.photo.days} ngày.`, `Sao kê: tài khoản ngân hàng có ít nhất ${fmt(co.bank*co.trip)} xu.`,
    `Xác nhận việc: đã đi làm ít nhất ${c.work_days} ngày.`, co.interview?'Phỏng vấn: trả lời thật, có vé khứ hồi.':'',
    'Thiếu hay sai một giấy là bị trả hồ sơ, phí không hoàn.'].filter(Boolean));
  return chips+`<section class="sd-card">${head}<div class="sd-chips lx-docs">${docs}</div>${tools?`<div class="lx-tools">${tools}</div>`:''}${rules}</section>`;
}
const stars=n=>'★'.repeat(n);
function suu(v,c){
  const st=pieceSet(),it=piece(),o=own(it.id);
  const chips=`<div class="sd-chips">${c.sets.map(x=>chip('set',x.id,x.emoji,x.id===st.id,x.name)).join('')}</div>`;
  const list=st.items.map(x=>row('piece',x.id,own(x.id)?'✓':st.emoji,x.name,fmt(x.price),x.id===it.id,`<i>${stars(x.rare)}</i>`)).join('');
  const care=it.price>=c.insure_from?`<p class="lx-sub">🧾 ${fmt(month(it.price,c.insure_bp))}/tháng</p>`:'';
  const extra=o&&st.id===c.wine?`<button type="button" class="sd-link" data-lx="sell" data-id="${esc(it.id)}">Bán · ${fmt(o.sell)}</button>`:'';
  return chips+`<section class="sd-card"><h3>${st.emoji} ${esc(st.name)}</h3><div class="sd-list">${list}</div>${care}${extra}</section>`;
}
function nha(v,c){
  const e=estate(),o=own(e.id),types=c.types||{};
  const chips=`<div class="sd-chips">${c.estates.map(x=>chip('estate',x.id,x.emoji,x.id===e.id,x.name)).join('')}</div>`;
  const rooms=[...new Set(e.rooms.map(r=>r.t))].map(t=>types[t]?.emoji||({living:'🛋️',bed:'🛏️',bed2:'🧸',kitchen:'🍲',yard:'🌳'})[t]||'').join('');
  const links=o?[V().live===e.id?`<button type="button" class="sd-link" data-lx="leave">Về nhà cũ</button>`:'',`<button type="button" class="sd-link" data-lx="sell" data-id="${esc(e.id)}">Bán · ${fmt(o.sell)}</button>`].join(''):'';
  return chips+`<section class="sd-card lx-estate lx-${esc(e.theme)}"><h3>${e.emoji} ${esc(e.name)}</h3><p class="lx-sub">📍 ${esc(e.where)}</p><p class="lx-sub">${V().live===e.id?'🏠 Đang ở · ':''}🏢 ${e.floors} tầng · ${e.rooms.length} phòng</p>
    <p class="lx-rooms" aria-label="Các phòng">${rooms}</p><p class="lx-sub">🧾 ${fmt(month(e.price,e.bp))}/tháng</p>${links}</section>`;
}
function bay(v,c){
  const a=fly(),o=own(a.id);
  const chips=`<div class="sd-chips">${c.assets.map(x=>chip('fly',x.id,x.emoji,x.id===a.id,x.name)).join('')}</div>`;
  return chips+`<section class="sd-card"><div class="sd-poster" aria-hidden="true">${a.emoji}</div><h3>${esc(a.name)}</h3><p class="lx-sub">🧾 ${fmt(month(a.price,a.bp))}/tháng</p>
    ${o?`<button type="button" class="sd-link" data-lx="sell" data-id="${esc(a.id)}">Bán · ${fmt(o.sell)}</button>`:''}</section>`;
}
function tiec(v,c){
  const g=c.guests;
  const kinds=`<div class="sd-chips">${c.party_kinds.map(x=>chip('pkind',x.id,x.emoji,x.id===S.pkind,x.name)).join('')}</div>`;
  const tiers=c.party_tiers.map(x=>row('tier',x.id,x.emoji,x.name,fmt(x.base+x.guest*S.guests),x.id===S.tier)).join('');
  const step=`<div class="lx-step"><button type="button" class="sd-chip" data-lx="guests" data-d="-1" aria-label="Bớt khách"${S.guests<=g.min?' disabled':''}>−</button><label class="lx-typed"><span aria-hidden="true">👥</span>${qtyBox({value:S.guests,min:g.min,max:g.max,step:g.step,label:'Số khách',go:`data-lx="guestsSet" data-n="${QTY}"`})}</label><button type="button" class="sd-chip" data-lx="guests" data-d="1" aria-label="Thêm khách"${S.guests>=g.max?' disabled':''}>+</button></div>`;
  return kinds+`<section class="sd-card"><h3>${pkind().emoji} ${esc(pkind().name)}</h3><div class="sd-list">${tiers}</div>${step}</section>`;
}
function hoc(v,c){
  const co=course(),n=(v.course||{})[co.id];
  const chips=`<div class="sd-chips">${c.courses.map(x=>chip('course',x.id,`${x.emoji}${(v.course||{})[x.id]>=x.lessons?'✓':''}`,x.id===co.id,x.name)).join('')}</div>`;
  const dots=Array.from({length:co.lessons},(_,i)=>`<i class="${n!=null&&i<n?'on':''}"></i>`).join('');
  return chips+`<section class="sd-card"><h3>${co.emoji} ${esc(co.name)}</h3><p class="sd-stamps" aria-label="Buổi ${n||0}/${co.lessons}">${dots}</p></section>`;
}
function mtq(v,c){
  const g=give(),b=S.board&&!S.board.error?S.board:null;
  const kinds=`<div class="sd-chips">${c.gives.map(x=>chip('give',x.id,x.emoji,x.id===g.id,x.name)).join('')}</div>`;
  let body='';
  if(g.sizes?.length)body=`<div class="sd-list">${g.sizes.map(z=>row('size',z.id,'🎆',z.name,fmt(z.price),z.id===S.size)).join('')}</div>`;
  else if(g.slots){const taken=new Set((b?.plaques||[]).filter(p=>p.k===g.id).map(p=>p.s));
    body=`<div class="lx-slots">${Array.from({length:g.slots},(_,i)=>i+1).map(n=>`<button type="button" class="sd-chip${S.slot===n?' on':''}" data-lx="slot" data-n="${n}"${taken.has(n)?' disabled':''} aria-pressed="${S.slot===n}">${n}</button>`).join('')}</div>
      <label class="sd-select"><span class="sr-only">Lời khắc</span><select name="msg">${c.dedications.map(d=>`<option value="${esc(d.id)}"${S.msg===d.id?' selected':''}>${esc(d.text)}</option>`).join('')}</select></label>`;}
  else if(g.week){const who=b?.banners?.[g.id];body=`<p class="lx-sub">${who?`🏆 <b data-no-translate>${esc(who)}</b>`:'🏆 —'}</p>`;}
  else body=`<div class="sd-chips sd-amounts">${g.presets.map(n=>chip('amount',n,fmt(n),S.amount===n).replace('data-id','data-n')).join('')}</div><p class="lx-sub">📚 ${fmt(b?.library?.xu||0)}</p>`;
  const anon=`<label class="sd-toggle"><input type="checkbox" name="anon"${S.anon?' checked':''}><span>Ẩn danh</span></label>`;
  const top=b?(b.top||[]).slice(0,3).map((r,i)=>`<li class="${r.me?'me':''}"><span>${i+1}</span><b data-no-translate>${esc(r.name)}</b><em>${fmt(r.xu)}</em></li>`).join(''):'';
  return kinds+`<section class="sd-card"><h3>${g.emoji} ${esc(g.name)}</h3>${body}${anon}</section>${top?`<section class="sd-card"><ol class="sd-board">${top}</ol></section>`:''}`;
}
