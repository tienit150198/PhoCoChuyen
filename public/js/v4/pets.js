/** 🐾 Nuôi thú cưng (game/pets.py): adopt at Góc nhận nuôi Chân Nhỏ, buy at Tiệm Thú Nhỏ Chú Út, care, dress up,
 * photo booth, and the weekly "Bé cưng của tuần" board (GET /api/pets/board). Story mode.
 * Every rule and price lives on the server; this file renders api.state.journey.pets with the static lists
 * (content.journey.pets), draws with ./pet-art.js and sends `jr_pet_*`. Its own dialog, opened with data-action="pets"
 * (data-tab: home | adopt | shop | board) from the menu and the town map's 🐾 door next to the pet shop.
 * Phone first, few words: emoji tabs, one pick per screen, one main button in the bottom bar with the price on it.
 * Styles: /css/pets.css. */
import {icon,escapeHTML as esc} from '../icons.js';
import {lookOf,figureSVG} from './look.js';
import {petSVG,lookup} from './pet-art.js';

const TABS=[['home','🐾','Bé nhà mình'],['adopt','🏠','Nhận nuôi'],['shop','🛍️','Tiệm thú cưng'],['board','🏆','Bé cưng tuần']];
const NEEDS=[['f','🍚','No'],['j','💛','Vui'],['cl','🫧','Sạch'],['h','❤️','Khỏe']];
const MOOD={vui:'😊',on:'🙂',buon:'🥺'};
const S={dlg:null,env:null,tab:'home',sub:'',pet:'',kind:'dog',breed:'',coat:0,item:'',food:'hat',toy:'',clean:'bath',vet:'kham',slot:'head',
  shelter:-1,nick:'',donate:0,pose:'happy',frame:'nang',board:null,boardAt:0,busy:false,flash:null,listening:false};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const J=()=>S.env?.api?.state?.journey||{};
const V=()=>J().pets;
const CAT=()=>S.env?.api?.content?.journey?.pets||null;
const breedOf=id=>(CAT()?.breeds||[]).find(b=>b.id===id);
const cash=()=>Number(J().wallet)||0;
const ready=()=>cash()<0?0:cash()+(Number(J().bank?.balance)||0);
const readyWhy=price=>!price?'':cash()<0?'Ví đang nợ':ready()>=price?'':`Còn thiếu ${fmt(price-ready())} xu`;
const POCKET=['wallet','account'];

let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=link('/css/pets.css','pt-css');

/** A pet's picture from a save's {b, c, w}. */
export function petPic(cat,p,pose='sit',size=72,acc=null){
  const L=lookup(cat,p?.b,p?.c);if(!L)return `<span class="pt-unknown" aria-hidden="true">🐾</span>`;
  return petSVG(L.breed,L.coat,pose,acc??p.w??{},size);
}
function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium pt-sheet';d.setAttribute('aria-labelledby','pt-title');
  d.innerHTML='<div class="pt-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-pt]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.pt,el.dataset);
  });
  d.addEventListener('input',e=>{if(e.target.name==='nick')S.nick=e.target.value;});
  d.addEventListener('close',()=>{S.flash=null;S.sub='';});
  S.dlg=d;return d;
}
export async function openPets(env,tab){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';env.api.addEventListener('state',()=>{const key=JSON.stringify([J().wallet,J().pets,J().bank?.balance]);if(key===seen)return;seen=key;if(S.dlg?.open&&!S.busy)render();});
  }
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();
  S.tab=TABS.some(t=>t[0]===tab)?tab:(V()?.pets?.length?'home':'adopt');S.sub='';S.flash=null;
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
  if(S.tab==='board')loadBoard();
}
export async function petsAction(action,data,el,env){
  if(action!=='pets')return false;
  await openPets(env,data?.tab);return true;
}

async function loadBoard(force=false){
  if(!force&&S.board&&Date.now()-S.boardAt<15000)return;
  S.boardAt=Date.now();
  try{S.board=await S.env.api.json('/api/pets/board');}catch{S.board=S.board||{error:true};}
  if(S.dlg?.open&&S.tab==='board')render();
}
async function send(action,payload={}){
  const {api}=S.env;S.busy=true;render();
  try{
    const r=await api.command(action,payload);
    S.flash={text:[r.message,...(r.effects||[]).filter(Boolean)].filter(Boolean).join(' '),kind:'good'};
    const f=S.flash;setTimeout(()=>{if(S.flash===f&&!S.busy){S.flash=null;if(S.dlg?.open)render();}},6000);   // good news fades (the bank's way)
    return r;
  }catch(e){S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;render();}
}
const ask=(title,msg,label,cost)=>S.env.confirmAction?S.env.confirmAction(title,msg,label,cost?{cost,pocket:POCKET}:undefined):Promise.resolve(confirm(msg));

/* ---- picks ---- */
const pets=()=>V()?.pets||[];
const cur=()=>pets().find(p=>p.id===S.pet)||pets()[0]||null;
const shelterPick=()=>(V()?.shelter||[]).find(a=>a.i===S.shelter&&!a.taken)||null;
const breedList=()=>(CAT()?.breeds||[]).filter(b=>b.kind===S.kind);
const shopItems=()=>[...(CAT()?.accs||[]),...(CAT()?.toys||[])];
const own=id=>Number(V()?.own?.[id])||0;
const wornBy=id=>pets().filter(p=>Object.values(p.w||{}).includes(id)).length;
const groomPrice=p=>p?.kind==='cat'?CAT().groom.cat:CAT().groom.price;
/** The care a pet needs most: [sub view, emoji, label] (the home screen's main button). */
function nextCare(p){
  const n=p.needs,c=CAT();if(!c)return ['photo','📸','Chụp ảnh'];
  const low=[['feed',n.f,'🍚','Cho ăn'],['play',n.j,'🎾','Chơi'],['clean',n.cl,'🛁','Tắm'],['vet',n.h,'🩺','Khám']].filter(x=>x[1]<60).sort((a,b)=>a[1]-b[1])[0];
  return low?[low[0],low[2],low[3]]:['photo','📸','Chụp ảnh'];
}

/** The bottom bar's one button: [label, op, why]. */
function main(){
  const v=V(),c=CAT(),p=cur();
  if(S.tab==='adopt'){const a=shelterPick();if(!a)return ['Chọn một bé','',' '];
    return [`🏠 Nhận nuôi${S.donate?` · ủng hộ ${fmt(S.donate)} xu`:''}`,'adopt',pets().length>=c.max?'Nhà đủ 3 bé rồi':readyWhy(S.donate)];}
  if(S.tab==='shop'){
    if(S.kind==='do'){const it=shopItems().find(x=>x.id===S.item);if(!it)return ['Chọn một món','',' '];
      return [`Mua · ${fmt(it.price)} xu`,'buy',it.uses===0&&own(it.id)?'Có rồi':readyWhy(it.price)];}
    const b=breedOf(S.breed);if(!b)return ['Chọn một giống','',' '];
    return [`Đón về · ${fmt(b.price)} xu`,'shopbuy',pets().length>=c.max?'Nhà đủ 3 bé rồi':readyWhy(b.price)];
  }
  if(S.tab==='board')return ['🐾 Bé nhà mình','tohome',''];
  if(!p)return ['🏠 Nhận nuôi miễn phí','toadopt',''];
  const full=x=>x>=c.full;
  switch(S.sub){
    case'feed':{const f=c.foods.find(x=>x.id===S.food)||c.foods[0];return [`${f.emoji} Cho ăn${f.price?` · ${fmt(f.price)} xu`:''}`,'feed',full(p.needs.f)?'No căng rồi':readyWhy(f.price)];}
    case'play':{const t=c.toys.find(x=>x.id===S.toy);return [`${t?t.emoji:'🤲'} Chơi`,'play',full(p.needs.j)?'Chơi mệt rồi':''];}
    case'clean':{if(S.clean==='player')return ['🧑‍🔧 Tìm thợ người chơi','groomer',''];
      const pr=S.clean==='spa'?groomPrice(p):c.bath.price;return [`${S.clean==='spa'?'✂️ Spa':'🛁 Tắm'} · ${fmt(pr)} xu`,S.clean,full(p.needs.cl)?'Thơm phức rồi':readyWhy(pr)];}
    case'vet':{const it=S.vet==='kham'?c.vet:c.vaccine,why=S.vet==='kham'?(full(p.needs.h)?'Khỏe re rồi':''):(p.vac?`Còn hạn ${p.vac} ngày`:'');
      return [`${it.emoji} ${S.vet==='kham'?'Khám':'Tiêm'} · ${fmt(it.price)} xu`,'vet',why||readyWhy(it.price)];}
    case'dress':return ['✓ Xong','back',''];
    case'photo':return ['💾 Lưu ảnh','save',''];
    case'more':return ['✓ Đổi tên','rename',S.nick.trim()&&S.nick.trim()!==p.n?'':' '];
  }
  const [sub,e,l]=nextCare(p);return [`${e} ${l}`,'sub:'+sub,''];
}

async function onClick(op,data){
  const c=CAT(),p=cur();
  switch(op){
    case'close':S.dlg.close();return;
    case'tab':S.tab=data.tab;S.sub='';S.flash=null;render();top();if(S.tab==='board')loadBoard();return;
    case'pet':S.pet=data.id;S.sub='';render();return;
    case'sub':S.sub=data.sub;S.flash=null;if(S.sub==='more')S.nick=p?.n||'';render();top();return;
    case'back':S.sub='';render();return;
    case'kind':S.kind=data.kind;S.breed='';S.item='';render();return;
    case'breed':S.breed=data.id;S.coat=0;S.nick=S.nick||'';render();return;
    case'coat':S.coat=Number(data.c)||0;render();return;
    case'item':S.item=data.id;render();return;
    case'shelter':S.shelter=Number(data.i);const a=shelterPick();S.nick=a?.n||'';render();return;
    case'donate':S.donate=Number(data.n)||0;render();return;
    case'food':S.food=data.id;render();return;
    case'toy':S.toy=data.id||'';render();return;
    case'clean':S.clean=data.id;render();return;
    case'vet':S.vet=data.id;render();return;
    case'slot':S.slot=data.slot;render();return;
    case'wear':if(p)send('jr_pet_wear',{pet:p.id,slot:S.slot,id:data.id||null});return;
    case'pose':S.pose=data.id;render();return;
    case'frame':S.frame=data.id;render();return;
    case'walk':if(p)send('jr_pet_walk',{pet:p.id});return;
    case'trick':if(p)send('jr_pet_show',{pet:p.id,trick:data.id});return;
    case'home':if(p&&await ask(`Gửi ${p.n} về quê?`,`${p.n} về quê với bà, có vườn rộng. Đón về lúc nào cũng được.`,'Gửi về quê'))send('jr_pet_home',{pet:p.id,confirm:true});return;
    case'fetch':send('jr_pet_back',{pet:data.id});return;
    case'go':return go();
  }
}
async function go(){
  const [,what,why]=main(),c=CAT(),p=cur();if(why&&why.trim())return;
  if(what.startsWith('sub:')){S.sub=what.slice(4);render();top();return;}
  switch(what){
    case'tohome':S.tab='home';S.sub='';render();return;
    case'toadopt':S.tab='adopt';render();return;
    case'back':S.sub='';render();return;
    case'adopt':{const a=shelterPick();if(!a)return;const nick=(S.nick||a.n).trim();
      const r=await send('jr_pet_adopt',{from:'shelter',i:a.i,nick,donate:S.donate,confirm:true});if(r){S.tab='home';S.pet='';S.donate=0;S.shelter=-1;render();}return;}
    case'shopbuy':{const b=breedOf(S.breed);if(!b)return;const nick=(S.nick||b.name).trim().slice(0,16);
      if(!await ask(`Đón bé ${b.name} về?`,`Trả ${fmt(b.price)} xu một lần. Ví trước, thiếu thì lấy từ tài khoản.`,`Đón về · ${fmt(b.price)} xu`,b.price))return;
      const r=await send('jr_pet_adopt',{from:'shop',breed:b.id,coat:S.coat,nick,confirm:true});if(r){S.tab='home';S.pet='';S.breed='';render();}return;}
    case'buy':{const it=shopItems().find(x=>x.id===S.item);if(!it)return;
      if(it.price>=500&&!await ask(`Mua ${it.name}?`,`Trả ${fmt(it.price)} xu.`,`Mua · ${fmt(it.price)} xu`,it.price))return;
      await send('jr_pet_buy',{id:it.id,confirm:true});return;}
    case'feed':await send('jr_pet_feed',{pet:p.id,food:S.food});return;
    case'play':await send('jr_pet_play',{pet:p.id,...(S.toy?{toy:S.toy}:{})});return;
    case'bath':await send('jr_pet_bath',{pet:p.id});return;
    case'spa':{const pr=groomPrice(p);if(!await ask(`Spa cho ${p.n}?`,`${c.groom.where}: tắm sấy, cắt móng. ${fmt(pr)} xu.`,`Spa · ${fmt(pr)} xu`,pr))return;
      await send('jr_pet_groom',{pet:p.id,confirm:true});return;}
    case'groomer':S.dlg.close();S.env.act?.('workVisit',{career:'pet_care',scope:'public'});return;   // 🧑‍🔧 a real player's Pet Care (game/work_visits.py → pets.groom_by_player)
    case'vet':{const it=S.vet==='kham'?c.vet:c.vaccine;if(!await ask(`${it.name} cho ${p.n}?`,`${c.vet.where}. ${fmt(it.price)} xu.`,`${it.emoji} ${fmt(it.price)} xu`,it.price))return;
      await send('jr_pet_vet',{pet:p.id,what:S.vet,confirm:true});return;}
    case'save':savePhoto();return;
    case'rename':await send('jr_pet_name',{pet:p.id,nick:S.nick.trim()});return;
  }
}

/* ---- rendering ---- */
const top=()=>S.dlg?.querySelector('.pt-body')?.scrollTo?.(0,0);
function render(){
  if(!S.dlg)return;
  const body=S.dlg.querySelector('.pt-body'),y=body?.scrollTop;
  S.dlg.querySelector('.pt-root').innerHTML=page();
  if(y)S.dlg.querySelector('.pt-body').scrollTop=y;
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
function page(){
  const v=V(),c=CAT(),t=TABS.find(x=>x[0]===S.tab)||TABS[0];
  const head=`<header class="sheet-head pt-head">${S.sub?`<button class="icon-btn" type="button" data-pt="back" aria-label="Quay lại">${icon('back',21)}</button>`:`<span class="pt-logo" aria-hidden="true">${t[1]}</span>`}<div class="grow"><h2 id="pt-title">${esc(t[2])}</h2></div>
    <span class="pt-wallet" title="Ví">👛 ${fmt(Math.max(0,J().wallet||0))}</span><button class="icon-btn" type="button" data-pt="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  if(!v||!c)return head+`<div class="sheet-body pt-body"><p class="pt-empty">⏳</p></div>`;   // an older server
  if(!v.story)return head+`<div class="sheet-body pt-body"><p class="pt-empty">Chỉ có trong hành trình.</p></div>`;
  const tabs=S.sub?'':`<nav class="pt-tabs" role="tablist" aria-label="Thú cưng">${TABS.map(([id,e,l])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" aria-label="${esc(l)}" title="${esc(l)}" class="${S.tab===id?'on':''}" data-pt="tab" data-tab="${id}">${e}</button>`).join('')}</nav>`;
  const inner=S.tab==='adopt'?adopt(v,c):S.tab==='shop'?shop(v,c):S.tab==='board'?board(c):home(v,c);
  const [label,,why]=main();
  const w=why&&why.trim();
  const bar=label?`<footer class="pt-bar">${w?`<small class="pt-why">${esc(why)}</small>`:''}<button type="button" class="btn primary big pt-main" data-pt="go"${S.busy||w||why===' '?' disabled':''}>${esc(label)}</button></footer>`:'';
  const flash=`<p class="pt-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  return head+tabs+`<div class="sheet-body pt-body">${flash}${inner}</div>`+bar;
}
const meters=n=>`<div class="pt-needs">${NEEDS.map(([k,e,l])=>`<span class="pt-need${n[k]<CAT().low?' low':''}" title="${l} ${n[k]}" aria-label="${l} ${n[k]}"><i aria-hidden="true">${e}</i><b style="--v:${n[k]}%"></b></span>`).join('')}</div>`;
const chip=(op,data,on,inner,label='')=>`<button type="button" class="pt-chip${on?' on':''}" data-pt="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')} aria-pressed="${on}"${label?` aria-label="${esc(label)}" title="${esc(label)}"`:''}>${inner}</button>`;

function home(v,c){
  const list=pets();
  if(!list.length)return `<section class="pt-card pt-center">${petSVG(breedOf('meo_muop'),breedOf('meo_muop').coats[1],'happy',{},120)}<h3>Chưa có bé nào</h3><p class="pt-muted">Góc Chân Nhỏ có bé chờ nhà mới.</p></section>`+farm(v);
  const p=cur();S.pet=p.id;
  const strip=list.length>1?`<div class="pt-strip">${list.map(x=>`<button type="button" class="pt-mini${x.id===p.id?' on':''}" data-pt="pet" data-id="${esc(x.id)}" aria-label="${esc(x.n)}" title="${esc(x.n)}">${petPic(c,x,'sit',44)}</button>`).join('')}</div>`:'';
  const b=breedOf(p.b);
  if(S.sub)return strip+subView(p,c);
  const pose=p.mood==='vui'?'happy':p.mood==='buon'?'sleep':'sit';
  const acts=[['feed','🍚','Ăn'],['play','🎾','Chơi'],['clean','🛁','Tắm'],['vet','🩺','Khám'],['dress','🎀','Diện'],['photo','📸','Ảnh'],['more','⋯','Thêm']];
  return strip+`<section class="pt-card pt-hero"><div class="pt-stage">${petPic(c,p,pose,150)}</div>
    <h3><span data-no-translate>${esc(p.n)}</span> ${MOOD[p.mood]||''}</h3><p class="pt-muted">${esc(b?.name||'')}${p.pts?` · 🏆${p.pts}`:''}${v.walk===p.id?' · 🦮':''}</p>${meters(p.needs)}</section>
    <div class="pt-acts">${acts.map(([s,e,l])=>`<button type="button" class="pt-act" data-pt="sub" data-sub="${s}"><span aria-hidden="true">${e}</span>${l}</button>`).join('')}</div>`;
}
function farm(v){
  if(!v.farm?.length)return '';
  return `<section class="pt-card"><h4>🏡 Ở quê</h4><div class="pt-strip">${v.farm.map(x=>`<button type="button" class="pt-mini" data-pt="fetch" data-id="${esc(x.id)}" aria-label="Đón ${esc(x.n)}" title="Đón ${esc(x.n)}"${pets().length>=CAT().max?' disabled':''}>${petPic(CAT(),x,'sleep',44,{})}</button>`).join('')}</div></section>`;
}
function subView(p,c){
  const pic=(pose,size=110)=>`<div class="pt-stage sm">${petPic(c,p,pose,size)}</div>`;
  switch(S.sub){
    case'feed':return pic('sit')+meters(p.needs)+`<div class="pt-list">${c.foods.map(f=>row('food',f,S.food===f.id,f.price?fmt(f.price):'0')).join('')}</div>`;
    case'play':{const mine=c.toys.filter(t=>own(t.id)&&(t.kind==='both'||t.kind===p.kind));
      return pic('happy')+meters(p.needs)+`<div class="pt-list">${row('toy',{id:'',emoji:'🤲',name:'Tay không'},!S.toy,'')}${mine.map(t=>row('toy',t,S.toy===t.id,t.uses?`×${own(t.id)}`:'∞')).join('')}</div>`
        +(mine.length?'':`<button type="button" class="pt-link" data-pt="tab" data-tab="shop">🛍️ Mua đồ chơi</button>`);}
    case'clean':return pic('sit')+meters(p.needs)+`<div class="pt-list">${row('clean',{id:'bath',emoji:'🛁',name:c.bath.name},S.clean==='bath',fmt(c.bath.price))}${row('clean',{id:'spa',emoji:'✂️',name:'Spa Mèo Mập'},S.clean==='spa',fmt(groomPrice(p)))}${row('clean',{id:'player',emoji:'🧑‍🔧',name:'Thợ người chơi'},S.clean==='player','')}</div>`;
    case'vet':return pic('sit')+meters(p.needs)+`<div class="pt-list">${row('vet',{id:'kham',emoji:'🩺',name:c.vet.name},S.vet==='kham',fmt(c.vet.price))}${row('vet',{id:'tiem',emoji:'💉',name:c.vaccine.name},S.vet==='tiem',p.vac?`✓${p.vac}`:fmt(c.vaccine.price))}</div>`;
    case'dress':{const slots=c.slots,items=c.accs.filter(a=>a.slot===S.slot&&own(a.id));
      const tiles=items.map(a=>{const on=p.w?.[S.slot]===a.id,free=own(a.id)-wornBy(a.id);return `<button type="button" class="pt-tile${on?' on':''}" data-pt="wear" data-id="${on?'':esc(a.id)}" aria-pressed="${on}" aria-label="${esc(a.name)}" title="${esc(a.name)}"${!on&&free<=0?' disabled':''}><span aria-hidden="true">${esc(a.emoji)}</span></button>`;}).join('');
      return pic(S.slot==='bed'?'sleep':'sit',120)+`<div class="pt-chips">${slots.map(s=>chip('slot',{slot:s.id},S.slot===s.id,s.emoji,s.name)).join('')}</div>`
        +(tiles?`<div class="pt-tiles">${tiles}</div>`:`<button type="button" class="pt-link" data-pt="tab" data-tab="shop">🛍️ Mua đồ diện</button>`);}
    case'photo':{const tr=(c.tricks[p.kind]||[]).filter(t=>p.tr.includes(t.id));
      return `<figure class="pt-photo f-${esc(S.frame)}">${photoSVG(p,c)}</figure><div class="pt-chips">${c.poses.map(x=>chip('pose',{id:x.id},S.pose===x.id,esc(x.name))).join('')}</div>
        <div class="pt-chips">${c.frames.map(f=>chip('frame',{id:f.id},S.frame===f.id,f.emoji,f.name)).join('')}${tr.map(t=>chip('trick',{id:t.id},false,t.emoji,t.name)).join('')}</div>`;}
    case'more':{const v=V(),next=p.next;
      return `<section class="pt-card"><label class="pt-name"><span class="sr-only">Tên bé</span><input name="nick" maxlength="${CAT().name_max}" value="${esc(S.nick)}" autocomplete="off"></label>
        <div class="pt-chips">${chip('walk',{},v.walk===p.id,'🦮','Đi dạo cùng')}${chip('home',{},false,'🏡','Về quê')}</div>
        <p class="pt-muted">${(c.tricks[p.kind]||[]).map(t=>`<span title="${esc(t.name)}" class="${p.tr.includes(t.id)?'':'pt-off'}">${t.emoji}</span>`).join(' ')}${next?` · ${p.x}/${next.at}`:''}</p></section>`+farm(v);}
  }
  return '';
}
function row(op,it,on,right){
  return `<button type="button" class="pt-item${on?' on':''}" data-pt="${op}" data-id="${esc(it.id)}" aria-pressed="${on}"><span class="pt-ico" aria-hidden="true">${esc(it.emoji)}</span><b>${esc(it.name)}</b><em>${esc(right)}</em></button>`;
}
function adopt(v,c){
  const list=v.shelter||[],a=shelterPick();
  const cards=list.map(x=>{const b=breedOf(x.b);return `<button type="button" class="pt-pick${S.shelter===x.i?' on':''}" data-pt="shelter" data-i="${x.i}"${x.taken?' disabled':''} aria-pressed="${S.shelter===x.i}">${petPic(c,{b:x.b,c:x.c},x.taken?'sleep':'sit',84,{})}<b data-no-translate>${esc(x.n)}</b><small>${x.taken?'✓':esc(b?.name||'')}</small></button>`;}).join('');
  const form=a?`<section class="pt-card"><label class="pt-name"><span class="sr-only">Tên bé</span><input name="nick" maxlength="${c.name_max}" value="${esc(S.nick)}" autocomplete="off"></label>
    <h4>💗 Ủng hộ Chân Nhỏ</h4><div class="pt-chips">${c.donate.map(n=>chip('donate',{n},S.donate===n,n?fmt(n):'0')).join('')}</div></section>`:'';
  return `<div class="pt-picks">${cards}</div>`+form;
}
function shop(v,c){
  const kinds=`<div class="pt-chips">${chip('kind',{kind:'dog'},S.kind==='dog','🐶','Chó')}${chip('kind',{kind:'cat'},S.kind==='cat','🐱','Mèo')}${chip('kind',{kind:'do'},S.kind==='do','🎀','Đồ')}</div>`;
  if(S.kind==='do'){
    const tiles=shopItems().map(it=>`<button type="button" class="pt-tile${S.item===it.id?' on':''}" data-pt="item" data-id="${esc(it.id)}" aria-pressed="${S.item===it.id}" aria-label="${esc(it.name)}" title="${esc(it.name)}"><span aria-hidden="true">${esc(it.emoji)}</span><small>${fmt(it.price)}</small></button>`).join('');
    const it=shopItems().find(x=>x.id===S.item);
    return kinds+(it?`<p class="pt-sel">${esc(it.emoji)} <b>${esc(it.name)}</b>${own(it.id)?` · có ${it.uses?`${own(it.id)} lượt`:own(it.id)}`:''}</p>`:'')+`<div class="pt-tiles">${tiles}</div>`;
  }
  const b=breedOf(S.breed);
  if(b){const coat=b.coats[S.coat]||b.coats[0];
    return kinds+`<section class="pt-card pt-center"><div class="pt-stage">${petSVG(b,coat,'happy',{},140)}</div><h3>${esc(b.name)}</h3><p class="pt-muted">✨ ${esc(b.trait)}</p>
      <div class="pt-chips pt-coats">${b.coats.map((k,i)=>chip('coat',{c:i},S.coat===i,`<i style="background:${esc(k.b)};box-shadow:inset -6px 0 0 ${esc(k.m)}"></i>`,k.name)).join('')}</div>
      <label class="pt-name"><span class="sr-only">Tên bé</span><input name="nick" maxlength="${c.name_max}" value="${esc(S.nick)}" placeholder="Tên bé" autocomplete="off"></label></section>
      <button type="button" class="pt-link" data-pt="breed" data-id="">↩︎</button>`;}
  return kinds+`<div class="pt-picks">${breedList().map(x=>`<button type="button" class="pt-pick" data-pt="breed" data-id="${esc(x.id)}">${petSVG(x,x.coats[0],'sit',{},84)}<b>${esc(x.name)}</b><small>${fmt(x.price)}</small></button>`).join('')}</div>`;
}
function board(c){
  const b=S.board;if(!b)return '<p class="pt-empty">⏳</p>';if(b.error)return '<p class="pt-empty">📡</p>';
  if(!b.top?.length)return `<p class="pt-empty">🏆</p>`;
  return `<ol class="pt-board">${b.top.map((r,i)=>`<li class="${r.me?'me':''}"><span>${i+1}</span>${petPic(c,{b:r.b,c:r.c},'sit',48,Object.fromEntries((r.a||[]).map(id=>[(c.accs.find(a=>a.id===id)||{}).slot||'x',id])))}<b data-no-translate>${esc(r.name)}<small>${esc(r.owner)}</small></b><em>${r.pts}</em></li>`).join('')}</ol>`;
}

/* ---- 📸 photo booth: the character beside the pet, in a frame; saved as a PNG on this device only ---- */
const FRAME={nang:['#fff4cf','#ffd27a','🌼'],tim:['#ffe3ea','#f5a9bc','💗'],tet:['#ffe1d6','#e05a4f','🧧'],sao:['#e6ecff','#a9c0f5','⭐']};
function photoSVG(p,c){
  const st=S.env.api.state,L=lookup(c,p.b,p.c),[bg,edge,em]=FRAME[S.frame]||FRAME.nang;
  const me=figureSVG(lookOf(st),st?.journey?.gender,{w:120,h:170}).replace('<svg ','<svg x="14" y="22" ');
  const pet=L?petSVG(L.breed,L.coat,S.pose,p.w||{},120).replace('<svg ','<svg x="118" y="72" '):'';
  return `<svg class="pt-shot" viewBox="0 0 260 220" width="260" height="220" role="img" aria-label="${esc(p.n)}"><rect x="2" y="2" width="256" height="216" rx="18" fill="${bg}" stroke="${edge}" stroke-width="4"/>
    <ellipse cx="130" cy="192" rx="110" ry="12" fill="#000" opacity=".06"/>${me}${pet}<text x="22" y="34" font-size="20">${em}</text><text x="236" y="34" font-size="20" text-anchor="end">${em}</text>
    <text x="130" y="210" font-size="13" font-weight="800" fill="#5b4535" text-anchor="middle">${esc(st?.name||'Bạn')} &amp; ${esc(p.n)}</text></svg>`;
}
async function savePhoto(){
  const p=cur(),c=CAT();if(!p)return;
  const svg=photoSVG(p,c).replace('<svg ','<svg xmlns="http://www.w3.org/2000/svg" ').replace('width="260" height="220"','width="780" height="660"');
  const img=await new Promise(done=>{const i=new Image();i.onload=()=>done(i);i.onerror=()=>done(null);i.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);});
  if(!img){S.flash={text:'Chưa lưu được ảnh.',kind:'bad'};render();return;}
  const cv=document.createElement('canvas');cv.width=780;cv.height=660;cv.getContext('2d').drawImage(img,0,0,780,660);
  const a=document.createElement('a');a.download=`be-cung-${p.n}.png`;a.href=cv.toDataURL('image/png');a.click();
  send('jr_pet_show',{pet:p.id});   // a photo counts as showing off (one point a day)
}
