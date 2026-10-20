/** 🏝️ Đảo riêng (game/island.py, game/island_trips.py): buy a private island, go out alone or take friends on your
 * yacht or plane (as many as it has seats), answer a friend's invitation. Story mode. Every rule, price and seat count
 * lives on the server: this renders api.state.journey.island with the static list (content.journey.island) and the
 * trips (GET /api/island), sends `jr_island_buy` / `jr_island_sell` and POST /api/island/<op>. Being on the island is
 * v4/island-scene.js (both interfaces). Opened with data-action="island" (data-tab) and islandInvites; the invitation
 * card comes from the live socket (island_ping, welcome isl_inv). Styles: /css/spend.css + /css/island.css.
 * 🏗️ Xây (game/island_build.py): the plots of an island on a small map, build / upgrade / phá dỡ (jr_isle_build,
 * jr_isle_up, jr_isle_raze; api.state.journey.islb). 🌍 Ghé đảo: invitations, then the islands open to everyone (GET
 * /api/island?public=1, POST visit / leave); the owner opens or closes theirs (POST public). No time limit since 19/10.
 * 🏡 20/10: the house styles (public/js/house-art.js) in a phone-first picker: 🏠 Nhà ở / 🎡 Vui chơi, the tiers, cards with
 * a drawn preview; the chosen one big, its three levels and colours (`look` of jr_isle_build), 🎨 sơn lại (jr_isle_paint). */
import {icon,escapeHTML as esc} from '../icons.js';
import {layout,PLOT_W} from '../island-layout.js';
import {HOUSES,splitKind,previewHouse} from '../house-art.js';

const ALL_TABS=[['buy','🏝️','Mua đảo'],['go','🛥️','Ra đảo'],['build','🏗️','Xây'],['inv','🌍','Ghé đảo']];
// 🛑 MNL_ISLAND_BUILD_OFF (content.journey.island.build_off): the 🏗️ Xây tab hides; buildings already there still show
const tabsOn=()=>ALL_TABS.filter(t=>t[0]!=='build'||!CAT()?.build_off);
export const ACTIONS={island:'',islandInvites:'inv',islandBuild:'build',islandOpen:'inv'};
const S={dlg:null,env:null,tab:'buy',pick:'',isle:'',ride:'',sel:new Set(),list:null,listAt:0,skew:0,busy:false,flash:null,listening:false,seq:0,plot:-1,kind:'',
  cat:'home',tier:0,look:0,pv:1,paint:-1};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const J=()=>S.env?.api?.state?.journey||{};
const V=()=>J().island||null;
const CAT=()=>S.env?.api?.content?.journey?.island||null;
const ownIds=()=>Object.keys(V()?.own||{});
/** The server's clock (GET /api/island `now`) minus this device's: a trip's hour is the server's. */
const serverNow=()=>Date.now()/1000+S.skew;
const minutes=(t,now=serverNow())=>Math.max(0,Math.ceil((Number(t?.ends)-now)/60));
/** ⏳ "còn 5 phút" before 19/10, ♾️ since (a trip has no time limit; an older trip keeps its hour). */
const timeLeft=t=>t?.unlimited?'♾️ không giới hạn':`⏳ còn ${minutes(t)} phút`;
/* ---- 🏗️ the buildings (api.state.journey.islb, content.journey.island.build) ---- */
const BC=()=>CAT()?.build||null;
const BL=()=>J().islb||null;
/** A stored kind ('pho_hoi_an__2': a style in its third colour) → its catalogue entry. */
const KIND=k=>{const id=splitKind(String(k||''))[0];return (BC()?.buildings||[]).find(b=>b.id===id)||null;};
const lookOf=k=>splitKind(String(k||''))[1]||0;
const hoursLeft=s=>{const m=Math.max(1,Math.ceil(s/60)),h=Math.floor(m/60);return h?`${h}g${m%60?` ${m%60}p`:''}`:`${m}p`;};
const stars=n=>'⭐'.repeat(Math.max(0,n));
const plotsOf=iid=>BL()?.p?.[iid]||{};
const lvlNow=(e,now=serverNow())=>e.b&&e.t<=now?e.b:e.l;
const busyNow=(e,now=serverNow())=>Boolean(e.b)&&e.t>now;
const heard=data=>{if(Number.isFinite(data?.now))S.skew=data.now-Date.now()/1000;return data;};

let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=Promise.all([link('/css/spend.css','sd-css'),link('/css/island.css','isl-css')]);

/* ---- money (game/lux.py ready_why: the wallet, then the bank account; never with the wallet in debt) ---- */
const cash=()=>Number(J().wallet)||0;
const ready=()=>cash()<0?0:cash()+(Number(J().bank?.balance)||0);
export const readyWhy=(price,wallet,bank)=>wallet<0?'Ví đang nợ':(wallet+bank)>=price?'':`Còn thiếu ${fmt(price-wallet-bank)} xu`;

/* ---- the server ---- */
async function load(force=false){
  if(!force&&S.list&&Date.now()-S.listAt<4000&&(S.tab!=='inv'||S.list.open))return;
  const seq=++S.seq;
  try{const data=heard(await S.env.api.json(`/api/island?friends=1${S.tab==='inv'?'&public=1':''}`));if(seq!==S.seq)return;S.list=data;S.listAt=Date.now();}
  catch(e){if(seq===S.seq&&!S.list)S.flash={text:e.message||'Chưa tải được chuyến đi. Thử lại nhé.',kind:'bad'};}
  if(S.dlg?.open)render();
}
async function post(op,body){
  const api=S.env.api;
  const data=await api.json(`/api/island/${op}`,{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify(body)});
  S.list=heard(data);S.listAt=Date.now();S.seq++;return data;
}
async function run(fn,ok){
  S.busy=true;render();
  try{const r=await fn();if(ok)S.flash={text:typeof ok==='function'?ok(r):ok,kind:'good'};return r;}
  catch(e){S.flash={text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;render();}
}
async function command(action,payload){
  return run(async()=>{const r=await S.env.api.command(action,payload);S.flash={text:[r.message,...(r.effects||[]).filter(Boolean)].filter(Boolean).join(' '),kind:r.refused?'bad':'good'};return r;});
}

/* ---- the dialog ---- */
function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium sd-sheet isl-sheet';d.setAttribute('aria-labelledby','isl-title');
  d.innerHTML='<div class="sd-root"></div>';document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-is]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.is,el.dataset);
  });
  d.addEventListener('change',e=>{const t=e.target;if(t.name==='friend'){t.checked?S.sel.add(t.value):S.sel.delete(t.value);render();}});
  d.addEventListener('close',()=>{S.flash=null;});
  S.dlg=d;return d;
}
export async function openIsland(env,tab){
  S.env=env;
  if(!S.listening){
    S.listening=true;let seen='';
    env.api.addEventListener('state',()=>{const key=JSON.stringify([J().wallet,J().island,J().islb,J().bank?.balance]);if(key===seen)return;seen=key;if(S.dlg?.open&&!S.busy)render();});
  }
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();
  if(tabsOn().some(t=>t[0]===tab))S.tab=tab;
  else if(!tab)S.tab=ownIds().length?'go':'buy';
  S.flash=null;
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();load(true);
}
export async function islandAction(action,data,el,env){
  if(!(action in ACTIONS))return false;
  await openIsland(env,ACTIONS[action]||data?.tab);return true;
}
/** 🏗️ From the island itself (the owner taps a plot or 🏗️): the build tab of that island, that plot. */
export async function openBuild(env,iid,plot=-1){
  S.isle=iid;if(plot>=0){S.plot=plot;S.kind='';}
  await openIsland(env,'build');
}

function render(){
  if(!S.dlg)return;
  const y=S.dlg.querySelector('.sd-body')?.scrollTop;
  S.dlg.querySelector('.sd-root').innerHTML=page();
  for(const cv of S.dlg.querySelectorAll('canvas[data-house]'))previewHouse(cv,cv.dataset.house,Number(cv.dataset.lv)||1,Number(cv.dataset.look)||0);
  if(y)S.dlg.querySelector('.sd-body').scrollTop=y;
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
const chip=(op,id,label,on,title='')=>`<button type="button" class="sd-chip${on?' on':''}" data-is="${op}" data-id="${esc(id)}" aria-pressed="${on}"${title?` aria-label="${esc(title)}" title="${esc(title)}"`:''}>${label}</button>`;
const row=(op,id,ico,name,right,on,extra='')=>`<button type="button" class="sd-item${on?' on':''}" data-is="${op}" data-id="${esc(id)}" aria-pressed="${on}"><span class="sd-ico" aria-hidden="true">${ico}</span><b>${esc(name)}</b><span class="sd-fx">${extra}</span><em>${right}</em></button>`;
const invCount=()=>(S.list?.invites||[]).length;

function page(){
  const TABS=tabsOn(),t=TABS.find(x=>x[0]===S.tab)||TABS[0],c=CAT();
  if(S.tab!==t[0])S.tab=t[0];
  const head=`<header class="sheet-head sd-head"><span class="sd-logo" aria-hidden="true">${t[1]}</span><div class="grow"><h2 id="isl-title">${esc(t[2])}</h2></div>
    <span class="sd-wallet" title="Ví">👛 ${fmt(Math.max(0,J().wallet||0))}</span><button class="icon-btn" type="button" data-is="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  if(!c)return head+`<div class="sheet-body sd-body"><p class="sd-empty">⏳</p></div>`;
  if(!J().story)return head+`<div class="sheet-body sd-body"><p class="sd-empty">Chỉ có trong hành trình.</p></div>`;
  const tabs=`<nav class="sd-tabs isl-tabs" role="tablist" aria-label="Đảo riêng">${TABS.map(([id,e,l])=>{const n=id==='inv'?invCount():0;
    return `<button type="button" role="tab" aria-selected="${S.tab===id}" class="${S.tab===id?'on':''}" data-is="tab" data-tab="${id}"><span aria-hidden="true">${e}</span>${esc(l)}${n?` <i class="isl-badge" aria-label="${n} lời mời">${n}</i>`:''}</button>`;}).join('')}</nav>`;
  const inner={buy,go,build,inv}[S.tab](c);
  const [label,,why]=main(c);
  const bar=label?`<footer class="sd-bar">${why.trim()?`<small class="sd-why">${esc(why)}</small>`:''}<button type="button" class="btn primary big sd-main" data-is="go"${S.busy||why?' disabled':''}>${esc(label)}</button></footer>`:'';
  const flash=`<p class="sd-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  return head+tabs+`<div class="sheet-body sd-body">${flash}${inner}</div>`+bar;
}
const island=c=>c.islands.find(x=>x.id===S.pick)||c.islands.find(x=>!V()?.own?.[x.id])||c.islands[0];
const myIsle=c=>{const ids=ownIds();return c.islands.find(x=>x.id===S.isle&&ids.includes(x.id))||c.islands.find(x=>ids.includes(x.id))||null;};
const rides=()=>V()?.rides||[];
const ride=()=>rides().find(r=>r.id===S.ride)||null;
/** Where it lands on this island: a plane on an island with no strip comes down on the pad. */
const landsAt=(c,arrive,look)=>arrive==='plane'&&layout(look).pad.kind!=='strip'?'Bãi đáp':c.arrive[arrive]||'';
const vehicleLine=t=>t.vehicle?(String(t.vehicle.name||'').startsWith(t.vehicle.emoji)?t.vehicle.name:`${t.vehicle.emoji} ${t.vehicle.name}`):'🚤 Xuồng của đảo';

/** The bottom bar's one button: [label, op, why it is off]. */
function main(c){
  const v=V(),trip=S.list?.trip;
  if(S.tab==='buy'){
    const i=island(c);
    if(v?.own?.[i.id])return ['🛥️ Ra đảo này','goto',''];
    return [`Mua · ${fmt(i.price)} xu`,'buy',readyWhy(i.price,cash(),Number(J().bank?.balance)||0)];
  }
  if(S.tab==='build'){
    const i=myIsle(c),bc=BC();if(!i||!bc)return ['🏝️ Xem các hòn đảo','shop',''];
    const plots=plotsOf(i.id),e=plots[S.plot],now=serverNow(),money=(n)=>readyWhy(n,cash(),Number(J().bank?.balance)||0);
    const wait=crewWait(plots),crews=wait?`Cả ${bc.crews} đội thợ đang bận, rảnh sau ${hoursLeft(wait)}`:'';
    if(!e){const shown=visible(bc),k=KIND(S.kind)||shown.find(x=>!buildWhy(c,i,x,plots))||shown[0];if(!k)return ['Chưa xây được','',' '];
      S.kind=k.id;const why=buildWhy(c,i,k,plots)||crews||money(k.levels[0].price);return [`${k.emoji} Xây · ${fmt(k.levels[0].price)} xu`,'build',why];}
    if(busyNow(e,now))return [`⏳ Xong sau ${hoursLeft(e.t-now)}`,'',' '];
    const k=KIND(e.k),lv=lvlNow(e,now),next=k?.levels[lv];
    if(!next)return ['🏝️ Ra đảo ngắm','goto',''];
    return [`Nâng cấp ${stars(lv+1)} · ${fmt(next.price)} xu`,'up',crews||money(next.price)];
  }
  if(S.tab==='go'){
    if(trip)return ['🏝️ Lên đảo','enter',''];
    const i=myIsle(c);if(!i)return ['🏝️ Xem các hòn đảo','shop',''];
    return [ride()?`${ride().emoji} Ra đảo cùng bạn bè`:'🚤 Ra đảo một mình','start',''];
  }
  return ['','',''];
}

function buy(c){
  const v=V(),i=island(c),own=v?.own?.[i.id];
  const chips=`<div class="sd-chips">${c.islands.map(x=>chip('pick',x.id,`${x.emoji}${v?.own?.[x.id]?'✓':''}`,x.id===i.id,x.name)).join('')}</div>`;
  const facts=[`💰 ${fmt(i.price)} xu`,`🧾 Phí giữ đảo ${fmt(i.month)} xu/tháng`,`↩️ Bán lại ${fmt(i.sell)} xu`];
  const owned=own?`<p class="isl-own">✓ Đảo của bạn${v.due?` · phí tháng này đang tính ${fmt(v.due)} xu`:''}</p><button type="button" class="sd-link" data-is="sell" data-id="${esc(i.id)}">Bán đảo · ${fmt(own.sell)} xu</button>`:'';
  return chips+`<section class="sd-card isl-card isl-${esc(i.look)}"><div class="isl-poster" aria-hidden="true">${i.emoji}</div><h3>${esc(i.name)}</h3><p class="lx-sub">📍 ${esc(i.where)}</p><p>${esc(i.desc)}</p>
    <ul class="isl-facts">${facts.map(f=>`<li>${esc(f)}</li>`).join('')}</ul>${owned}
    <p class="lx-sub">Phí giữ đảo trả mỗi ${c.month_days} ngày, từ ví rồi tới tài khoản. ${c.unlimited?'Ở đảo bao lâu tùy thích.':`Mỗi chuyến chơi ${c.minutes} phút.`}</p></section>`;
}

function go(c){
  const trip=S.list?.trip;
  if(!S.list)return `<p class="sd-empty">⏳</p>`;
  if(trip)return tripCard(c,trip);
  const i=myIsle(c);
  if(!i)return `<section class="sd-card"><p class="sd-empty">Bạn chưa có đảo nào. Chọn một hòn ở thẻ 🏝️ Mua đảo nhé.</p></section>`;
  const ids=ownIds(),chips=ids.length>1?`<div class="sd-chips">${c.islands.filter(x=>ids.includes(x.id)).map(x=>chip('isle',x.id,x.emoji,x.id===i.id,x.name)).join('')}</div>`:'';
  const list=[row('ride','','🚤','Đi một mình','1 người',!ride(),`<i>${esc(c.arrive.solo||'')}</i>`),
    ...rides().map(r=>row('ride',r.id,r.emoji,r.name,`${r.seats} chỗ`,ride()?.id===r.id,`<i>${esc(landsAt(c,r.arrive,i.look))}</i>`))].join('');
  const none=rides().length?'':`<p class="lx-sub">Muốn rủ bạn bè? Mua du thuyền, trực thăng hay phi cơ (Mua sắm, Garage), mỗi loại chở được số người khác nhau.</p>`;
  return chips+`<section class="sd-card"><h3>${i.emoji} ${esc(i.name)}</h3><h4>Đi bằng gì?</h4><div class="sd-list">${list}</div>${none}
    <p class="lx-sub">${c.unlimited?'Ở bao lâu tùy thích.':`Chuyến chơi kéo dài ${c.minutes} phút.`} Bạn mời bạn bè sau khi ra đảo.</p></section>`;
}
function tripCard(c,t){
  const left=minutes(t),solo=t.kind==='solo'||t.seats<=1,guests=t.guests||[],free=t.seats-t.aboard;
  void left;
  const head=`<h3>${esc(t.island.emoji)} ${esc(t.island.name)}</h3><p class="lx-sub">${esc(vehicleLine(t))} · 👥 ${t.aboard+(t.visitors||0)}/${t.cap||t.seats} người · ${timeLeft(t)}</p>`;
  const vis=t.visitor_list||[];
  const pub=`<div class="isl-pub${t.public?' on':''}"><div><b>🌍 ${t.public?'Đang mở cửa cho mọi người':'Mở cửa cho mọi người'}</b><small>${t.public?`${vis.length} khách đang ghé`:`Tối đa ${CAT()?.public_cap||40} người`}</small></div>
    <button type="button" class="btn${t.public?' ghost':' primary'}" data-is="public" aria-pressed="${Boolean(t.public)}">${t.public?'Đóng cửa':'Mở cửa'}</button></div>
    ${vis.length?`<ul class="isl-guests">${vis.map(g=>`<li><span>${esc(g.name)}</span><small>🌍 Khách</small><button type="button" class="sd-link" data-is="remove" data-code="${esc(g.code)}">Mời về</button></li>`).join('')}</ul>`:''}`;
  const gl=guests.length?`<h4>Khách trên chuyến</h4><ul class="isl-guests">${guests.map(g=>`<li><span>${esc(g.name)}</span><small>${g.status==='aboard'?'🛥️ Đã lên':'💌 Chờ trả lời'}</small><button type="button" class="sd-link" data-is="remove" data-code="${esc(g.code)}">${g.status==='aboard'?'Mời xuống':'Hủy lời mời'}</button></li>`).join('')}</ul>`:'';
  let invite='';
  if(!solo){
    const asked=new Set(guests.map(g=>g.code)),friends=(S.list?.friends||[]).filter(f=>!asked.has(f.code));
    const boxes=friends.length?`<div class="isl-friends">${friends.map(f=>`<label class="isl-friend"><input type="checkbox" name="friend" value="${esc(f.code)}"${S.sel.has(f.code)?' checked':''}> ${esc(f.name)}</label>`).join('')}</div>
      <button type="button" class="btn" data-is="invite"${S.sel.size&&!S.busy?'':' disabled'}>💌 Mời ${S.sel.size||''} bạn</button>`
      :`<p class="lx-sub">${(S.list?.friends||[]).length?'Đã mời hết bạn bè.':'Chưa có bạn bè để mời. Kết bạn ở mục Bạn bè nhé.'}</p>`;
    invite=`<h4>Mời bạn bè</h4><p class="lx-sub">Còn ${Math.max(0,free)} chỗ trống.</p><p class="lx-sub">Bạn nào đồng ý trước thì lên trước, hết chỗ thì thôi.</p>${boxes}`;
  }else invite=`<p class="lx-sub">Đi một mình nên không chở thêm ai. Lần sau chọn du thuyền hoặc phi cơ để rủ bạn bè.</p>`;
  return `<section class="sd-card">${head}${pub}${gl}${invite}<button type="button" class="sd-link isl-end" data-is="end">Kết thúc chuyến chơi</button></section>`;
}
function inv(){
  if(!S.list)return `<p class="sd-empty">⏳</p>`;
  const invites=S.list.invites||[],aboard=S.list.aboard||[],visiting=S.list.visiting||[],open=S.list.open;
  const card=(t,on)=>{const full=t.aboard>=t.seats;
    return `<section class="sd-card isl-invite"><h3>${esc(t.island.emoji)} ${esc(t.island.name)}</h3><p class="lx-sub">👤 ${esc(t.owner.name)} · ${esc(vehicleLine(t))}</p>
    <p class="lx-sub">👥 ${t.aboard}/${t.seats} người · ${timeLeft(t)}</p>
    <div class="isl-actions">${on?`<button type="button" class="btn primary" data-is="enter" data-trip="${esc(t.id)}">🏝️ Lên đảo</button><button type="button" class="btn ghost" data-is="leave" data-trip="${esc(t.id)}">Rời chuyến</button>`
      :`<button type="button" class="btn primary" data-is="accept" data-trip="${esc(t.id)}"${full?' disabled':''}>${full?'Hết chỗ rồi':'Đồng ý'}</button><button type="button" class="btn ghost" data-is="decline" data-trip="${esc(t.id)}">Từ chối</button>`}</div></section>`;};
  const visit=t=>`<section class="sd-card isl-invite isl-visit"><h3>🌍 ${esc(t.island.emoji)} ${esc(t.island.name)}</h3><p class="lx-sub">👤 ${esc(t.owner.name)} · 👥 ${t.aboard+(t.visitors||0)}/${t.cap} người</p>
    <div class="isl-actions"><button type="button" class="btn primary" data-is="enter" data-trip="${esc(t.id)}" data-visit="1">🏝️ Vào lại</button><button type="button" class="btn ghost" data-is="leave" data-trip="${esc(t.id)}">Rời đảo</button></div></section>`;
  const mine=new Set(visiting.map(t=>t.id));
  const row=t=>{const n=t.people??(t.aboard+(t.visitors||0)),full=n>=t.cap,built=(t.builds||[]).length;
    return `<li class="isl-open"><span class="isl-open-ico isl-${esc(t.island.look)}" aria-hidden="true">${esc(t.island.emoji)}</span><div><b>${esc(t.island.name)}</b><small>👤 ${esc(t.owner.name)} · 👥 ${n}/${t.cap}${built?` · 🏗️ ${built}`:''}${t.score?` · ✨ ${t.score}`:''}</small></div>
      <button type="button" class="btn${full?' ghost':' primary'}" data-is="visit" data-trip="${esc(t.id)}"${full&&!mine.has(t.id)?' disabled':''}>${mine.has(t.id)?'Vào lại':full?'Đông quá':'Ghé chơi'}</button></li>`;};
  const pub=open===undefined?`<p class="sd-empty">⏳</p>`:open.length?`<ul class="isl-opens">${open.map(row).join('')}</ul>`:`<p class="lx-sub">Chưa đảo nào mở cửa. Chủ đảo bật 🌍 Mở cửa ở thẻ 🛥️ Ra đảo.</p>`;
  return aboard.map(t=>card(t,true)).join('')+invites.map(t=>card(t,false)).join('')+visiting.map(visit).join('')
    +`<section class="sd-card"><h3>🌍 Đảo đang mở cửa</h3>${pub}</section>`;
}

/* ---- 🏗️ Xây: the plots of one island on a small map, then the chosen plot ---- */
/** The part of the island the plots cover (a margin around them), so the squares are big enough to tap. */
function plotBox(spots,L){
  const v=L.villa,xs=[...spots.map(p=>p[0]),v.x-v.w/2,v.x+v.w/2],ys=[...spots.map(p=>p[1]),v.y-v.h/2,v.y+v.h/2],pad=PLOT_W*.9;
  let x0=Math.min(...xs)-pad,x1=Math.max(...xs)+pad,y0=Math.min(...ys)-pad,y1=Math.max(...ys)+pad;
  const want=1.25;   // not taller than wide, not much wider than 16:10
  if((x1-x0)/(y1-y0)<want){const d=(want*(y1-y0)-(x1-x0))/2;x0-=d;x1+=d;}
  if((x1-x0)/(y1-y0)>1.7){const d=((x1-x0)/1.7-(y1-y0))/2;y0-=d;y1+=d;}
  return {x:x0,y:y0,w:x1-x0,h:y1-y0};
}
/** The island under the plots, as on both interfaces' maps (public/js/island-layout.js): sea, sand, grass, the villa, the pier. */
function miniMap(look,box){
  const L=layout(look),cx=L.shore.reduce((a,p)=>a+p[0],0)/L.shore.length,cy=L.shore.reduce((a,p)=>a+p[1],0)/L.shore.length;
  const inset=by=>L.shore.map(([x,y])=>{const d=Math.hypot(x-cx,y-cy)||1,k=Math.max(0,1-by/d);return `${(cx+(x-cx)*k).toFixed(4)},${(cy+(y-cy)*k).toFixed(4)}`;}).join(' ');
  const r=(o,fill)=>`<rect x="${o.x-o.w/2}" y="${o.y-o.h/2}" width="${o.w}" height="${o.h}" fill="${fill}"/>`;
  const v=L.villa;
  return `<svg class="isl-mini" viewBox="${box.x} ${box.y} ${box.w} ${box.h}" preserveAspectRatio="none" aria-hidden="true">
    <rect x="-1" y="-1" width="3" height="3" fill="${L.sea}"/><polygon points="${inset(-.012)}" fill="#ffffff80"/><polygon points="${inset(0)}" fill="${L.sand}"/><polygon points="${inset(L.sandWidth)}" fill="${L.grass}"/>
    ${r(L.dock,'#b5844f')}${(L.walk||[]).map(w=>r(w,'#b5844f')).join('')}${r({x:v.x,y:v.y,w:v.w,h:v.h},v.roof)}
    ${L.palms.map(([x,y])=>`<circle cx="${x}" cy="${y}" r=".012" fill="#3f8a3e"/>`).join('')}</svg>`;
}
function buildWhy(c,i,kind,plots){
  const bc=BC(),pl=bc.plots[i.id]?.[S.plot],now=serverNow();
  if(kind.coast&&!pl?.[2])return 'Cần ô sát biển ⚓';
  if(kind.big&&i.price<bc.big_from)return 'Chỉ đảo lớn';
  if(kind.max&&Object.values(plots).filter(e=>splitKind(String(e.k))[0]===kind.id).length>=kind.max)return `Mỗi đảo ${kind.max}`;
  void now;return '';
}
/** Both crews at work: how long until one is free (seconds), else 0. */
function crewWait(plots){
  const now=serverNow(),busy=Object.values(plots).filter(e=>busyNow(e,now));
  return busy.length>=(BC()?.crews||2)?Math.min(...busy.map(e=>e.t-now)):0;
}
function build(c){
  const bc=BC();if(!bc)return `<p class="sd-empty">⏳</p>`;
  const i=myIsle(c);
  if(!i)return `<section class="sd-card"><p class="sd-empty">Mua một hòn đảo rồi xây nhà, hồ bơi, công viên… trên đó nhé.</p></section>`;
  const ids=ownIds(),chips=ids.length>1?`<div class="sd-chips">${c.islands.filter(x=>ids.includes(x.id)).map(x=>chip('isle',x.id,x.emoji,x.id===i.id,x.name)).join('')}</div>`:'';
  const plots=plotsOf(i.id),spots=bc.plots[i.id]||[],now=serverNow();
  if(S.plot<0||S.plot>=spots.length){const free=spots.findIndex((_,n)=>!plots[n]);S.plot=free>=0?free:0;}
  const busy=Object.values(plots).filter(e=>busyNow(e,now)).length,box=plotBox(spots,layout(i.look));
  const tiles=spots.map(([x,y,coast],n)=>{const e=plots[n],k=e&&KIND(e.k),lv=e?lvlNow(e,now):0,work=e&&busyNow(e,now);
    const face=!e?(coast?'⚓':'＋'):work?'🏗️':k?.emoji||'❔',sub=!e?'':work?hoursLeft(e.t-now).split(' ')[0]:String(lv);
    const label=!e?`Ô ${n+1} trống${coast?', sát biển':''}`:`Ô ${n+1}: ${k?.name||''}${work?', đang xây':`, cấp ${lv}`}`;
    return `<button type="button" class="isl-plot${e?' built':''}${work?' work':''}${n===S.plot?' on':''}" style="left:${((x-box.x)/box.w*100).toFixed(2)}%;top:${((y-box.y)/box.h*100).toFixed(2)}%;width:${(PLOT_W*.94/box.w*100).toFixed(2)}%;height:${(PLOT_W*.94/box.h*100).toFixed(2)}%" data-is="plot" data-id="${n}" aria-pressed="${n===S.plot}" aria-label="${esc(label)}"><span>${face}</span>${sub?`<small>${esc(sub)}</small>`:''}</button>`;}).join('');
  const map=`<div class="isl-map" style="aspect-ratio:${(box.w/box.h).toFixed(3)}" role="group" aria-label="Ô đất trên ${esc(i.name)}">${miniMap(i.look,box)}${tiles}</div>
    <p class="lx-sub isl-crews">👷 ${busy}/${bc.crews} đội thợ đang làm · ${Object.keys(plots).length}/${spots.length} ô đã dùng</p>`;
  const e=plots[S.plot],pl=spots[S.plot]||[0,0,0];
  let detail;
  if(!e){
    const shown=visible(bc);
    if(!KIND(S.kind)||!shown.some(k=>k.id===S.kind)){const k=shown.find(x=>!buildWhy(c,i,x,plots))||shown[0];S.kind=k?.id||'';S.look=0;S.pv=1;}
    const sel=KIND(S.kind);
    const cats=`<div class="sd-chips isl-cats">${chip('cat','home','🏠 Nhà ở',S.cat==='home')}${chip('cat','fun','🎡 Vui chơi',S.cat==='fun')}</div>`;
    const tiers=S.cat==='home'&&bc.tiers?.length?`<div class="sd-chips isl-tiers">${chip('tier','0','Tất cả',!S.tier)}${bc.tiers.map(([n,l])=>chip('tier',String(n),esc(l),S.tier===n)).join('')}</div>`:'';
    const cards=shown.map(k=>{const why=buildWhy(c,i,k,plots),[l1]=k.levels,on=S.kind===k.id;
      return `<button type="button" class="isl-hcard${on?' on':''}${why?' off':''}" data-is="kind" data-id="${esc(k.id)}" aria-pressed="${on}"${why?' aria-disabled="true"':''}>${thumb(k,1,on?S.look:0)}<b>${esc(k.name)}</b><small>${fmt(l1.price)} xu</small>${why?`<i class="isl-why">${esc(why)}</i>`:k.tier?`<i class="isl-tier">${'◆'.repeat(k.tier)}</i>`:''}</button>`;}).join('');
    detail=`<h3>Ô ${S.plot+1}${pl[2]?' · ⚓ sát biển':''}</h3>${cats}${tiers}${sel?showcase(sel,S.pv,S.look,null):''}<div class="isl-hgrid">${cards}</div>`;
  }else{
    const k=KIND(e.k),lv=lvlNow(e,now),work=busyNow(e,now),look=lookOf(e.k);
    if(S.kind!==k?.id){S.kind=k?.id||'';S.pv=Math.max(1,lv);S.paint=-1;}
    detail=`<h3>${k?.emoji||''} ${esc(k?.name||'')} ${stars(lv)}</h3>${k?showcase(k,S.pv,S.paint>=0?S.paint:look,{look,lv}):''}
      ${work?`<p class="lx-sub">🏗️ Đang xây cấp ${e.b} · còn ${hoursLeft(e.t-now)}</p>`:''}
      <button type="button" class="sd-link" data-is="raze">${work&&!lv?'Hủy xây':'Phá bỏ'} · nhận lại ${fmt(e.back)} xu</button>`;
  }
  return chips+`<section class="sd-card isl-build">${map}</section><section class="sd-card">${detail}</section>
    <p class="lx-sub">Công trình không kiếm tiền: chỉ để ở, để chơi và khoe với bạn bè. Phá bỏ nhận lại ${bc.salvage_pct}%.</p>`;
}

/** The buildings of the chosen group (🏠 homes of a tier, 🎡 the rest), homes cheapest first. */
function visible(bc){
  const all=bc.buildings||[];
  if(S.cat!=='home')return all.filter(k=>k.cat!=='home');
  return all.filter(k=>k.cat==='home'&&(!S.tier||(k.tier||1)===S.tier)).sort((a,b)=>a.levels[0].price-b.levels[0].price);
}
/** A drawn house (house-art.js) or, for the first buildings, their icon. */
const thumb=(k,lv,look,cls='isl-thumb')=>HOUSES[k.id]?`<canvas class="${cls}" data-house="${esc(k.id)}" data-lv="${lv}" data-look="${look}" aria-hidden="true"></canvas>`
  :`<span class="${cls} isl-thumb-e" aria-hidden="true">${k.emoji}</span>`;
/** The chosen building big: its levels (⭐ preview), its colours, what each level adds. `own`: a built one ({look, lv}). */
function showcase(k,pv,look,own){
  const art=HOUSES[k.id],lv=Math.max(1,Math.min(3,pv)),pals=art?.pals||[];
  const levels=`<div class="isl-lvls" role="group" aria-label="Xem trước cấp">${k.levels.map((l,n)=>`<button type="button" class="isl-lv${n+1===lv?' on':''}" data-is="pv" data-id="${n+1}" aria-pressed="${n+1===lv}" aria-label="Cấp ${n+1}">⭐${n+1}</button>`).join('')}</div>`;
  const sw=k.looks?.length>1&&pals.length?`<div class="isl-looks" role="group" aria-label="Màu">${k.looks.map((name,n)=>{const p=pals[n]||pals[0],on=n===look;
    return `<button type="button" class="isl-look${on?' on':''}" data-is="look" data-id="${n}" aria-pressed="${on}" title="${esc(name)}" aria-label="${esc(name)}"><i style="background:linear-gradient(135deg,${p.roof} 50%,${p.wall} 50%)"></i></button>`;}).join('')}<small>${esc(k.looks[look]||'')}</small></div>`:'';
  const paint=own&&k.looks?.length>1&&look!==own.look?`<button type="button" class="btn isl-paint" data-is="paint" data-id="${look}"${S.busy?' disabled':''}>🎨 Sơn màu ${esc(k.looks[look])} · ${fmt(k.paint)} xu</button>`:'';
  const lines=`<ul class="isl-lvl-lines">${k.levels.map((l,n)=>`<li class="${n+1===lv?'on':''}"><b>${stars(n+1)}</b> ${esc(l.text)}<small>${own?'':`${fmt(l.price)} xu · `}⏱️ ${l.hours}g</small></li>`).join('')}</ul>`;
  const note=[k.big?'👑 Chỉ đảo lớn':'',k.max?`Mỗi đảo ${k.max}`:'',k.coast?'⚓ Ô sát biển':''].filter(Boolean).join(' · ');
  return `<div class="isl-show">${thumb(k,lv,look,'isl-big')}<div class="isl-show-txt"><p>${esc(k.desc||'')}</p>${note?`<p class="lx-sub">${esc(note)}</p>`:''}${levels}${sw}${paint}</div>${lines}</div>`;
}

/* ---- taps ---- */
async function onClick(op,data){
  const c=CAT();
  switch(op){
    case'close':S.dlg.close();return;
    case'tab':S.tab=data.tab;S.flash=null;render();S.dlg.querySelector('.sd-body')?.scrollTo?.(0,0);load();return;
    case'pick':S.pick=data.id;render();return;
    case'isle':S.isle=data.id;S.plot=-1;S.kind='';render();return;
    case'plot':S.plot=Number(data.id);S.kind='';S.look=0;S.pv=1;S.paint=-1;S.flash=null;render();return;
    case'kind':if(S.kind!==data.id){S.kind=data.id;S.look=0;S.pv=1;}render();return;
    case'cat':S.cat=data.id;S.tier=0;S.kind='';render();return;
    case'tier':S.tier=Number(data.id)||0;S.kind='';render();return;
    case'pv':S.pv=Number(data.id)||1;render();return;
    case'look':{const i=myIsle(c),e=i&&plotsOf(i.id)[S.plot],n=Number(data.id)||0;if(e)S.paint=n;else S.look=n;render();return;}
    case'paint':{
      const i=myIsle(c),e=i&&plotsOf(i.id)[S.plot],k=e&&KIND(e.k),n=Number(data.id)||0;if(!k||!k.looks?.[n])return;
      if(!await S.env.confirmAction(`Sơn ${k.name} màu ${k.looks[n]}?`,`${fmt(k.paint)} xu, trả từ ví rồi tới tài khoản. Sơn xong ngay, cấp nhà giữ nguyên.`,'Sơn lại'))return;
      const r=await command('jr_isle_paint',{island:i.id,plot:S.plot,look:n,confirm:true});if(r&&!r.refused){S.paint=-1;render();}return;}
    case'raze':{
      const i=myIsle(c),e=i&&plotsOf(i.id)[S.plot],k=e&&KIND(e.k);if(!e)return;
      if(!await S.env.confirmAction(`Phá ${k?.name||'công trình'}?`,`Nhận lại ${fmt(e.back)} xu (${BC().salvage_pct}% tiền đã xây). Ô đất trống lại.`,'Phá bỏ'))return;
      await command('jr_isle_raze',{island:i.id,plot:S.plot,confirm:true});return;}
    case'public':{const t=S.list?.trip;if(!t)return;
      if(t.public&&!await S.env.confirmAction('Đóng cửa đảo?','Khách đang ghé sẽ về phố. Bạn bè đi cùng vẫn ở lại.','Đóng cửa'))return;
      await run(()=>post('public',{trip:t.id,open:!t.public}),t.public?'Đã đóng cửa đảo.':'Đảo đã mở cửa. Ai cũng ghé được ở thẻ 🌍 Ghé đảo.');return;}
    case'visit':{const r=await run(()=>post('visit',{trip:data.trip}));if(r){const t=(r.visiting||[]).find(x=>x.id===data.trip)||(r.aboard||[]).find(x=>x.id===data.trip);if(t)enter(t);}return;}
    case'ride':S.ride=data.id||'';render();return;
    case'sell':{
      const i=c.islands.find(x=>x.id===data.id),own=V()?.own?.[data.id];if(!i||!own)return;
      if(!await S.env.confirmAction(`Bán ${i.name}?`,`Bạn nhận lại ${fmt(own.sell)} xu vào ví (${c.sell_pct}% giá mua). Chuyến chơi đang mở ở đảo này sẽ kết thúc.`,'Bán đảo'))return;
      await command('jr_island_sell',{id:i.id,confirm:true});load(true);return;}
    case'invite':{
      const t=S.list?.trip;if(!t||!S.sel.size)return;const codes=[...S.sel];
      const r=await run(()=>post('invite',{trip:t.id,codes}),x=>{const n=Number(x?.done?.sent)||0,k=Number(x?.done?.skipped)||0;return n?`Đã gửi ${n} lời mời${k?` (${k} bạn không mời được)`:''}. Chờ bạn bè đồng ý nhé.`:'Các bạn này đã được mời rồi.';});
      if(r)S.sel.clear();render();return;}
    case'remove':{const t=S.list?.trip;if(!t)return;await run(()=>post('remove',{trip:t.id,code:data.code}),'Đã cập nhật danh sách khách.');return;}
    case'end':{const t=S.list?.trip;if(!t)return;
      if(!await S.env.confirmAction('Kết thúc chuyến ra đảo?','Mọi người trên đảo sẽ về phố. Bạn có thể ra đảo lại bất cứ lúc nào.','Kết thúc'))return;
      await run(()=>post('end',{trip:t.id}),'Chuyến chơi đã kết thúc. Mọi người đã về phố.');return;}
    case'accept':{const r=await run(()=>post('answer',{trip:data.trip,answer:'accept'}),'Đã nhận lời. Lên đảo thôi!');if(r){const t=(r.aboard||[]).find(x=>x.id===data.trip);if(t)enter(t);}return;}
    case'decline':await run(()=>post('answer',{trip:data.trip,answer:'decline'}),'Đã từ chối lời mời.');return;
    case'leave':await run(()=>post('leave',{trip:data.trip}),'Bạn đã rời chuyến này.');return;
    case'enter':{const t=data.trip?[...(S.list?.aboard||[]),...(S.list?.visiting||[])].find(x=>x.id===data.trip):S.list?.trip;if(t)enter(t);return;}
    case'go':{
      const [,what]=main(c);
      if(what==='goto'){S.isle=S.tab==='build'?(myIsle(c)?.id||''):island(c).id;S.tab='go';S.flash=null;render();load();}
      else if(what==='build'||what==='up'){
        const i=myIsle(c),bc=BC();if(!i||!bc)return;const e=plotsOf(i.id)[S.plot];
        if(what==='build'){const k=KIND(S.kind);if(!k)return;const [l1]=k.levels;
          if(!await S.env.confirmAction(`Xây ${k.name}?`,`${fmt(l1.price)} xu, trả từ ví rồi tới tài khoản. Xong sau ${l1.hours} giờ, trong lúc đó có giàn giáo.`,'Xây'))return;
          const look=k.looks?.length>1&&S.look>0&&S.look<k.looks.length?S.look:0;
          await command('jr_isle_build',{island:i.id,plot:S.plot,kind:k.id,...(look?{look}:{}),confirm:true});}
        else if(e){const k=KIND(e.k),lv=lvlNow(e),next=k?.levels[lv];if(!next)return;
          if(!await S.env.confirmAction(`Nâng ${k.name} lên cấp ${lv+1}?`,`${fmt(next.price)} xu. Xong sau ${next.hours} giờ.`,'Nâng cấp'))return;
          await command('jr_isle_up',{island:i.id,plot:S.plot,confirm:true});}
      }
      else if(what==='shop'){S.tab='buy';render();}
      else if(what==='enter'){if(S.list?.trip)enter(S.list.trip);}
      else if(what==='buy'){
        const i=island(c);
        if(!await S.env.confirmAction(`Mua ${i.name}?`,`Giá ${fmt(i.price)} xu, trả từ ví rồi tới tài khoản ngân hàng. Phí giữ đảo ${fmt(i.month)} xu mỗi ${c.month_days} ngày.`,'Mua đảo'))return;
        const r=await command('jr_island_buy',{id:i.id,confirm:true});if(r&&!r.refused){S.isle=i.id;}
      }else if(what==='start'){
        const i=myIsle(c);if(!i)return;
        const r=await run(()=>post('start',{island:i.id,vehicle:ride()?.id||''}),ride()?'Đã ra đảo. Giờ mời bạn bè cùng chơi nhé.':'');
        if(r?.trip&&!ride())enter(r.trip);
      }
      return;}
  }
}
/** Onto the island: close this dialog, open the scene; coming back reopens nothing (the town is where you are). A visitor
 * (🌍 an island open to everyone) leaves it when going back to town. */
async function enter(t){
  const env=S.env;S.dlg?.close();S.sel.clear();
  const {openIslandScene}=await import('./island-scene.js');
  const end=async()=>{
    if(!await env.confirmAction('Kết thúc chuyến ra đảo?','Mọi người trên đảo sẽ về phố. Bạn có thể ra đảo lại bất cứ lúc nào.','Kết thúc'))return false;
    await post('end',{trip:t.id});return true;};
  const reload=async()=>{const d=heard(await env.api.json(`/api/island${t.visit?'?public=1':''}`));S.list=d;S.listAt=Date.now();
    return [d.trip,...(d.aboard||[]),...(d.visiting||[]),...(d.open||[])].find(x=>x&&x.id===t.id)||null;};
  const use=async plot=>{   // 🏗️ a leisure building: a little tinh thần, a few times a day (the server checks the island)
    const cap=BC()?.use_max||0;if(!cap||(Number(BL()?.used)||0)>=cap)return '';
    try{const r=await env.api.command('jr_isle_use',{trip:t.id,plot});return r?.refused?'':(r?.message||'');}catch{return '';}};
  const build=plot=>openBuild(env,t.island.id,plot);
  const actions=t.mine?{end,reload,use,build}:{reload,use};
  openIslandScene(env,{...t,ends:t.ends-S.skew},{actions,skew:S.skew,onClose:()=>{if(t.visit)post('leave',{trip:t.id}).catch(()=>{});}});
}

/* ---- the invitation card (live/island.py island_ping, welcome isl_inv) ---- */
let card=null,cardTimer=0;
function showCard(env,html,onOpen){
  card?.remove();clearTimeout(cardTimer);
  const el=document.createElement('div');el.className='isl-ping';el.setAttribute('role','status');el.setAttribute('aria-live','polite');
  el.innerHTML=`<span class="isl-ping-ico" aria-hidden="true">💌</span><p>${html}</p><div><button type="button" class="btn primary small" data-ping="open">Xem lời mời</button><button type="button" class="btn ghost small" data-ping="later">Để sau</button></div>`;
  el.addEventListener('click',e=>{const b=e.target.closest('[data-ping]');if(!b)return;el.remove();card=null;clearTimeout(cardTimer);if(b.dataset.ping==='open')onOpen();});
  ([...document.querySelectorAll('dialog[open]')].pop()||document.body).append(el);card=el;   // over the top dialog, or it would sit under it
  cardTimer=setTimeout(()=>{el.remove();if(card===el)card=null;},20000);
}
export async function onIslandPing(env,f){
  S.env??=env;
  if(S.dlg?.open)load(true);
  if(f?.why!=='invite')return;
  await ensureCss();
  let t=null;
  try{const data=heard(await env.api.json('/api/island'));t=(data.invites||[]).find(x=>x.id===f.trip)||null;}catch{/* the card still says something */}
  const text=t?esc(`${t.owner.name} mời bạn ra ${t.island.name} bằng ${vehicleLine(t)}. Còn ${Math.max(0,t.seats-t.aboard)} chỗ.`):'Bạn có lời mời ra đảo.';
  showCard(env,text,()=>openIsland(env,'inv'));
}
export async function onIslandWelcome(env,n){
  if(!(n>0)||onIslandWelcome.shown)return;onIslandWelcome.shown=true;
  await ensureCss();
  showCard(env,`Bạn có ${Number(n)} lời mời ra đảo.`,()=>openIsland(env,'inv'));
}
