/** 🛍️ Cửa hàng, gọn như các game khác (owner 23/10 "gọn và dễ dùng như các game khác"). The shop's sheet (jrView
 * 'accshop'); the commands, the gifting of pairs, the 🧺 cart and the wing reveal stay in v4/acc-shop.js (actions jrAs*).
 * - One row of tabs: 🎀 Phụ kiện · 👕 Trang phục · 🪽 Cánh · 🤝 Đồ đôi · 🐾 Thú cưng (+ 🔗 Nơi mua khác). The pets' shelves
 *   (Mua bé, Đồ cho bé, Cánh cho bé, Đồ chơi, Linh kiện) are chips inside 🐾, not a second row of tabs.
 * - Every shelf the same grid of cards: the art, the name, the price, a border coloured by rarity (RARITY, grey → green →
 *   blue → purple → gold → red: the shop's items have no rarity of their own, so it is the price's place on its shelf)
 *   and a corner badge (Đang dùng / Đã có ×N).
 * - A bar per shelf to filter and sort (Độ hiếm, Giá tăng / giảm, Chưa có), kept in ui.as.f (no localStorage).
 * - A tap opens the detail sheet docked at the bottom of the shop: the try-on on the character, what it gives, the
 *   quantity where buying many makes sense (wings, pairs, the pets' things: − n + ×1 ×5 ×10 Tối đa), the total and ONE
 *   Mua button; wear / equip where the shelf has it. Esc or ✕ closes it, the focus goes back to the card.
 * - A small purchase goes straight through with a toast (payment.js bigBuy); wings that can now be ghép offer
 *   ⚒️ Đi cường hóa (jrForge), in the toast and in the sheet.
 * The pets' cards and their detail come from v4/pets.js (petShopModel): its picks, its main button, its jr_pet_* commands. */
import {icon,escapeHTML as esc} from '../icons.js';
import {lookOf,figureSVG,portrait,pairIcon,myPairs,wingIcon,wingOfState,WING_TIERS} from './look.js';
import {kinds,kindOf,pairRows,waiting,relOf,refreshCharms,SHOP_NAME} from './charms.js';
import {wdStatus,wdItem,wdThumb,arrange} from './wardrobe.js';
import {skeleton} from '../lazy.js';
import {noAsk,setNoAsk} from './no-ask.js';
import {S,PT,PET,W,btn,attrs,fmt,busy,qtyRow,cartBar,cartToggle,inCart,cartLook,CL,CL_EMOJI,WC,wingsOf,ownWings,styleOf,wName,badge,
  wingTile,sortWings,wingReveal,wingTable,wq,moreList,shopTabs,petTabs} from './acc-shop.js';

/** The rarity classes: grey, green, blue, purple, gold, red (acc-shop.css .t0 … .t5). */
export const RARITY=['Thường','Tốt','Hiếm','Quý','Sử thi','Huyền thoại'];
const TOP=[['acc','🎀','Phụ kiện'],['wear','👕','Trang phục'],['wing','🪽','Cánh'],['pair','🤝','Đồ đôi'],['pet','🐾','Thú cưng'],['more','🔗','Nơi mua khác']];
export const isPet=tab=>PET.some(x=>x[0]===tab);
export const partOf=tab=>PET.find(x=>x[0]===tab)?.[3]||'buy';
/** A card's rarity when the shelf gives none: the place of its price among the shelf's prices, spread on the six. */
function byPrice(list){
  const ps=[...new Set(list.map(x=>x.price).filter(p=>p>0))].sort((a,b)=>a-b),n=ps.length,top=RARITY.length-1;
  for(const x of list)if(!Number.isInteger(x.t)){const i=ps.indexOf(x.price);x.t=i<0?0:n<=RARITY.length?i:Math.round(i*top/(n-1));}
  return list;
}
/** A shelf's filters (ui.as.f[key]): r the rarity (-1 all), sort '' | 'asc' | 'desc', miss "Chưa có", g the kind. */
export const F=(st,key)=>(st.f??={})[key]??={r:-1,sort:'',miss:false,g:''};
function shown(list,f){
  const xs=list.filter(x=>(f.r<0||x.t===f.r)&&(!f.miss||!x.own)&&(!f.g||x.g===f.g));
  return f.sort?[...xs].sort((a,b)=>(f.sort==='asc'?1:-1)*(a.price-b.price)):xs;
}

/* ---- the filter bar, a card, the grid, the detail sheet ---- */
const gem=t=>`<i class="as-gem t${t}" aria-hidden="true"></i>`;
const opt=(key,k,v,on,inner)=>`<button type="button" class="as-dd-o${on?' on':''}" data-action="jrAsF"${attrs({key,k,v})} aria-pressed="${on}">${inner}</button>`;
function fbar(key,list,f,groups,extra=''){
  const tiers=[...new Set(list.map(x=>x.t))].sort((a,b)=>a-b);
  const grp=groups?.length>1?`<details class="as-dd"><summary class="as-fb${f.g?' on':''}">Loại: <b>${esc(groups.find(g=>g[0]===f.g)?.[1]||'Tất cả')}</b></summary>
    <div class="as-dd-list">${opt(key,'g','',!f.g,'Tất cả')}${groups.map(([g,l])=>opt(key,'g',g,f.g===g,esc(l))).join('')}</div></details>`:'';
  const rar=tiers.length>1?`<details class="as-dd"><summary class="as-fb${f.r>=0?' on':''}">${gem(f.r<0?'x':f.r)}Độ hiếm: <b>${f.r<0?'Tất cả':RARITY[f.r]}</b></summary>
    <div class="as-dd-list">${opt(key,'r',-1,f.r<0,'Tất cả')}${tiers.map(t=>opt(key,'r',t,f.r===t,`${gem(t)}${RARITY[t]}`)).join('')}</div></details>`:'';
  const next={'':'asc',asc:'desc',desc:''}[f.sort]||'';
  const sort=`<button type="button" class="as-fb${f.sort?' on':''}" data-action="jrAsF"${attrs({key,k:'sort',v:next})} aria-label="${f.sort==='asc'?'Giá đang tăng dần, chạm để giảm dần':f.sort==='desc'?'Giá đang giảm dần, chạm để bỏ sắp xếp':'Sắp xếp theo giá tăng dần'}">${f.sort==='asc'?'Giá ↑':f.sort==='desc'?'Giá ↓':'Giá ↕'}</button>`;
  const miss=`<button type="button" class="as-fb${f.miss?' on':''}" data-action="jrAsF"${attrs({key,k:'miss',v:f.miss?'':'1'})} aria-pressed="${f.miss}">Chưa có</button>`;
  return `<div class="as-fbar" role="toolbar" aria-label="Lọc và sắp xếp">${grp}${rar}${sort}${miss}${extra}</div>`;
}
/** One card: x {id, art, name, price, was (the price before a discount), t, own (count), many (show ×N), on (in use),
 * lock (why not yet), sel, cart, action + data (none: a card to look at only), note (instead of the price)}. */
function card(x){
  const tag=x.action?'button':'div',corner=x.on?'Đang dùng':x.own?(x.many?`Đã có ×${x.own}`:'Đã có'):'';
  const price=x.note??(x.price?`${x.was>x.price?`<s>${fmt(x.was)}</s> `:''}${fmt(x.price)} xu`:'Miễn phí');
  return `<${tag}${x.action?` type="button" data-action="${x.action}"${attrs(x.data||{})} aria-pressed="${!!(x.sel||x.cart)}"`:''} class="as-card t${x.t}${x.sel?' sel':''}${x.cart?' in-cart':''}${x.lock?' locked':''}${x.on?' using':''}" data-key="${esc(x.id)}"${x.lock?` title="${esc(x.lock)}"`:''}>
    <span class="as-card-art" aria-hidden="true">${x.art}</span>${corner?`<span class="as-card-badge${x.on?' on':''}">${corner}</span>`:''}
    <span class="as-card-name">${esc(x.name)}</span><span class="as-card-price">${price}</span><span class="sr-only">${RARITY[x.t]}</span>${x.cart?'<i class="as-incart" aria-label="trong giỏ">🧺</i>':''}</${tag}>`;
}
function grid(key,list,st,{groups,extra='',empty='Quầy này đang hết hàng.'}={}){
  const f=F(st,key);if(f.g&&!groups?.some(g=>g[0]===f.g))f.g='';
  const xs=shown(list,f);
  const body=xs.length?`<div class="as-grid" role="list" aria-label="Hàng bày bán">${xs.map(x=>`<div role="listitem" class="as-cell">${card(x)}</div>`).join('')}</div>`
    :`<div class="as-none"><p>${list.length?'Không có món nào khớp bộ lọc.':esc(empty)}</p>${list.length?btn('Bỏ lọc','jrAsF',{key,k:'reset',v:''},'ghost small'):''}</div>`;
  return fbar(key,list,f,groups,extra)+body;
}
/** The detail sheet, docked at the bottom of the shop (sticky): ✕, the stage, the words, then the buying part. */
function detail({id,t,title,stage,info='',extra='',buy=''}){
  return `<section class="as-detail t${t}" role="dialog" aria-labelledby="as-d-h" tabindex="-1" data-as-detail data-key="${esc(id)}">
    <span class="as-d-grip" aria-hidden="true"></span><button type="button" class="as-d-x" data-action="jrAsClose" aria-label="Đóng">${icon('x',20)}</button>
    <div class="as-d-main"><div class="as-d-stage">${stage}</div><div class="as-d-info"><span class="as-d-tier">${gem(t)}${RARITY[t]}</span><h3 id="as-d-h">${title}</h3>${info}</div></div>
    ${extra}${buy?`<div class="as-d-buy">${buy}${noAskBox()}</div>`:''}</section>`;
}
/** ☑️ Không hỏi lại (owner 23/10, the label only: "không cần giải thích nhiều"): ticked, Mua buys at once with no question of any size (payment.js noAsk, this device). */
const noAskBox=()=>{const on=noAsk();return `<label class="as-noask${on?' on':''}"><input type="checkbox" data-action="jrAsNoAsk"${on?' checked':''}><span>Không hỏi lại</span></label>`;};
const mirror=(api,look,label)=>{const pr=myPairs();return figureSVG(pr&&!look.pr?{...look,pr}:look,api.state.journey.gender,{w:150,h:212,label});};
const staffNote=(api,c,always=false)=>!c.staff_off?'':api.state.careers?.[c.shop]?.started?`<p class="as-d-note good">🏷️ Giá nhân viên ${esc(c.shop_name)}: −${c.staff_off}%</p>`
  :always?`<p class="as-d-note">🏷️ Làm ở ${esc(c.shop_name)}: giảm ${c.staff_off}%</p>`:'';
const multiBtn=st=>btn(st.multi?'✓ Đang chọn nhiều':'🧺 Chọn nhiều','jrAsMulti',{},`as-fb as-multi-b${st.multi?' on':''}`);
/** 👫 owner 24/10: a shelf shows the character's gender and unisex first; this switch shows the other pieces too. */
const othersBtn=(st,hidden)=>!st.gall&&!hidden?'':btn(st.gall?'👫 Hợp với bạn':`👀 Đồ khác (${hidden})`,'jrAsAll',{},`as-fb${st.gall?' on':''}`);
/** The 🧺 cart, docked at the bottom while there is no detail open: what is in it on the character, the sum, one buy. */
function cartDock(api,st){
  const bar=cartBar(api,st);if(!bar)return '';
  const look={...lookOf(api.state),...cartLook(api,st)};
  return `<div class="as-cart-dock"><span class="as-cart-fig" aria-hidden="true">${portrait(look,api.state.journey.gender,56,'')}</span>${bar}</div>`;
}

/* ---- 🎀 Phụ kiện ---- */
function accShelf(env,st){
  const {api}=env,c=W(api),g=api.state.journey.gender,saved=lookOf(api.state);
  const tidy=arrange(api,c.items.filter(x=>x.slot==='acc'&&x.id!=='pk_khong'),{all:st.gall,keep:[saved.acc,st.draft]});
  const list=byPrice(tidy.list.map(it=>{const s=wdStatus(api,it);
    return {id:it.id,art:portrait({...saved,acc:it.id},g,64,''),name:it.name,price:s?.buy?s.price:it.price,was:s?.buy?it.price:0,own:s?0:1,on:saved.acc===it.id,
      lock:s?.lock||'',note:s?.lock?`🔒 ${esc(s.lock)}`:s?undefined:it.price?'Đã có':'Miễn phí',sel:!st.multi&&st.draft===it.id,cart:inCart(st,it.id),action:'jrAsTry',data:{item:it.id}};}));
  const body=`${grid('acc',list,st,{extra:multiBtn(st)+othersBtn(st,tidy.hidden)})}
    <p class="wd-note as-foot">🎀 ${esc(c.acc_shop?.title||'Tiệm phụ kiện')} ${btn('👗 Tủ đồ','jrWardrobe',{},'ghost small')}</p>`;
  const x=!st.multi&&list.find(x=>x.id===st.draft);
  return {body,detail:x?wdDetail(api,st,x,'acc'):cartDock(api,st)};
}
/** 🎀 / 👕 detail: the piece on the character, the price (staff price), buy or wear, 🧺 into the cart. */
function wdDetail(api,st,x,kind){
  const c=W(api),it=wdItem(api,x.id),s=wdStatus(api,it),saved=lookOf(api.state),acc=kind==='acc';
  const stage=mirror(api,{...saved,[it.slot]:it.id},`Nhân vật của bạn ${acc?'đeo':'mặc'} thử ${it.name}`);
  const worn=saved[it.slot]===it.id,lock=s?.lock;
  const state=lock?`<p class="wd-lock">🔒 ${esc(lock)}.</p>`:worn?`<p class="as-d-note good">✓ Đang ${acc?'đeo':'mặc'}</p>`:s?.buy?'':`<p class="as-d-note">Đã có trong tủ đồ.</p>`;
  const info=`${s?.buy?`<p class="as-d-price">${s.price<it.price?`<s>${fmt(it.price)}</s> `:''}<b>${fmt(s.price)} xu</b></p>`:''}${staffNote(api,c,!acc)}${state}
    `;
  const buy=lock?'':s?.buy?`<div class="as-d-btns">${btn(`Mua · ${fmt(s.price)} xu`,acc?'jrAsBuy':'jrAsClBuy',{item:it.id},'primary as-d-go',busy)}${btn(inCart(st,it.id)?'✓ Trong giỏ':'🧺 Cho vào giỏ','jrAsCart',{item:it.id},'ghost')}</div>`
    :worn?'':`<div class="as-d-btns">${acc?btn(`🎀 Đeo ${esc(it.name)}`,'jrAsWearAcc',{item:it.id},'primary as-d-go',busy):btn(`${CL_EMOJI[it.slot]||'✨'} Mặc ${esc(it.name)}`,'jrAsClOn',{item:it.id},'primary as-d-go',busy)}</div>`;
  return detail({id:it.id,t:x.t,title:esc(it.name),stage,info,buy});
}

/* ---- 👕 Trang phục: the wardrobe's pieces with a price (game/wardrobe.py), a rack per slot ---- */
function wearShelf(env,st){
  const {api}=env,c=W(api),g=api.state.journey.gender,saved=lookOf(api.state);
  const slots=c.slots.filter(x=>CL.includes(x.id)).sort((a,b)=>CL.indexOf(a.id)-CL.indexOf(b.id));
  const it=st.cdraft&&wdItem(api,st.cdraft);
  if(!slots.some(x=>x.id===st.cslot))st.cslot=it&&CL.includes(it.slot)?it.slot:slots[0]?.id||'top';   // from Tủ đồ: the piece's own rack
  const chips=slots.map(x=>`<button type="button" class="chip${st.cslot===x.id?' active':''}" aria-pressed="${st.cslot===x.id}" data-action="jrAsClSlot" data-slot="${esc(x.id)}">${CL_EMOJI[x.id]||''} ${esc(x.name)}</button>`).join('');
  const tidy=arrange(api,c.items.filter(x=>x.slot===st.cslot&&x.price),{all:st.gall,keep:[saved[st.cslot],st.cdraft]});
  const list=byPrice(tidy.list.map(x=>{const s=wdStatus(api,x);
    return {id:x.id,art:wdThumb({...saved,[x.slot]:x.id},g,x.slot),name:x.name,price:s?.buy?s.price:x.price,was:s?.buy?x.price:0,own:s?0:1,on:saved[x.slot]===x.id,
      lock:s?.lock||'',note:s?.lock?`🔒 ${esc(s.lock)}`:s?undefined:'Đã có',sel:!st.multi&&st.cdraft===x.id,cart:inCart(st,x.id),action:'jrAsClTry',data:{item:x.id}};}));
  const body=`<div class="as-cats" role="group" aria-label="Loại đồ">${chips}</div>${grid('wear',list,st,{extra:multiBtn(st)+othersBtn(st,tidy.hidden)})}
    <p class="wd-note as-foot">${btn('👗 Tủ đồ','jrWardrobe',{},'ghost small')}</p>`;
  const x=!st.multi&&list.find(x=>x.id===st.cdraft);
  return {body,detail:x?wdDetail(api,st,x,'wear'):cartDock(api,st)};
}

/* ---- 🪽 Cánh: bought and worn here, ghép in ⚒️ Cường hóa ---- */
/** Wings that can go up now: three of one tier below the top (what ⚒️ Cường hóa ghép). */
export function wingsReady(api){
  const top=WING_TIERS.length-1,n=new Map();
  for(const x of ownWings(api))if(x.r<top)n.set(x.r,(n.get(x.r)||0)+1);
  return [...n.values()].some(k=>k>=3);
}
const forgeBtn=(tab,label='⚒️ Đi cường hóa')=>btn(label,'jrForge',{tab},'as-d-forge');
function wingShelf(env,st){
  const {api}=env,c=WC(api);
  if(!c)return {body:`<p class="muted">Cánh đang về hàng, lát nữa quay lại nhé.</p>`,detail:''};
  const w=wingsOf(api)||{},own=ownWings(api),worn=wingOfState(api.state);
  const list=byPrice(c.styles.map(x=>({id:x.id,art:wingIcon({k:x.id,r:0},64),name:x.name,price:x.price,own:own.filter(o=>o.k===x.id).length,many:true,
    on:worn?.k===x.id,sel:st.wtry===x.id,action:'jrAsWingTry',data:{k:x.id}})));
  const forge=own.length>=3?`<p class="jr-card as-for">⚒️ <span class="grow">Ghép cánh lên hạng</span>${btn('⚒️ Cường hóa','jrForge',{tab:'wing'},'small')}</p>`:'';
  const tiles=own.length?`<details class="jr-card wg-own as-own"><summary><b>🪽 Tủ cánh</b> <small class="muted">${own.length}/${c.own_max} · đeo, cất, bỏ</small></summary>
    <ul class="wg-grid">${sortWings(own).map(x=>wingTile(api,w,x)).join('')}</ul></details>`:'';
  const x=list.find(x=>x.id===st.wtry);
  const body=`${x?'':wingReveal(api,st)}${forge}${grid('wing',list,st)}${tiles}${wingTable(c)}`;
  return {body,detail:x?wingDetail(api,st,x):''};
}
function wingDetail(api,st,x){
  const c=WC(api),w=wingsOf(api)||{},own=ownWings(api),style=styleOf(api,x.id),mine=sortWings(own.filter(o=>o.k===x.id));
  const stage=mirror(api,{...lookOf(api.state),wg:{k:x.id,r:mine[0]?.r||0}},`Nhân vật của bạn thử ${style.name}`);
  const cap=Math.max(1,Math.min(c.qty_max||1,c.own_max-own.length)),q=wq(st,x.id,cap),full=own.length>=c.own_max;
  const info=`<p class="as-d-price"><b>${fmt(style.price)} xu</b> / đôi</p><p class="small">${esc(style.desc)}</p><p class="as-d-note">🎲 Ra hạng D hoặc C</p>
    <ul class="as-d-gives"><li>💰 +${c.earn[0]}–${c.earn[1]}% tiền kiếm được khi làm việc</li><li>💪 +${c.battle[0]}–${c.battle[1]}% lực chiến thú cưng</li></ul>`;
  const reveal=st.reveal?.length?wingReveal(api,st).replace('</section>',`${wingsReady(api)?forgeBtn('wing'):''}</section>`):'';
  const have=mine.length?`<details class="as-d-own"${reveal?' open':''}><summary>🪽 Bạn có ${mine.length} đôi ${esc(style.name)}</summary><ul class="wg-grid">${mine.map(o=>wingTile(api,w,o)).join('')}</ul></details>`:'';
  const ready=!reveal&&wingsReady(api)?`<p class="as-d-note">${forgeBtn('wing')}</p>`:'';
  const buy=`${qtyRow(api,'jrAsWingQty',{k:x.id},q,cap,style.price)}${full?`<p class="wd-lock">🪽 Tủ cánh đầy ${c.own_max} đôi</p>`:''}
    <div class="as-d-btns">${btn(`Mua${q>1?` ×${q}`:''} · ${fmt(style.price*q)} xu`,'jrAsWingBuy',{k:x.id},'primary as-d-go',busy||full)}</div>`;
  return detail({id:x.id,t:x.t,title:`${esc(style.emoji)} ${esc(style.name)}`,stage,info:info+ready,extra:reveal+have,buy});
}

/* ---- 🤝 Đồ đôi (phụ kiện đôi): the gifts and pairs on top, the shelf, the pairs worn ---- */
function friendPick(v,st,id){
  const fr=v.friends||[];
  if(!fr.length)return `<p class="muted small">Kết bạn trước rồi tặng nhé.</p>`;
  const opts=fr.map(f=>`<option value="${esc(f.code)}"${f.code===st.to?' selected':''}>${esc(f.name)}</option>`).join('');
  return `<div class="as-give"><label class="sr-only" for="as-to-${esc(id)}">Tặng cho</label><select class="input" id="as-to-${esc(id)}" data-as-to>${st.to&&fr.some(f=>f.code===st.to)?'':'<option value="">Chọn một người bạn…</option>'}${opts}</select>
    ${btn('🎁 Tặng','jrAsGive',{id},'primary small',busy)}</div>`;
}
function pairShelf(env,st){
  const {api}=env,v=api.charmView,ks=kinds(api);
  refreshCharms(env,15000)?.then(x=>{if(x)env.renderSheet();});   // a gift may have come in since
  const toName=st.to&&v?.friends?.find(f=>f.code===st.to)?.name;
  const forWho=toName?`<p class="jr-card as-for">🎁 <span class="grow">Quà cho <b>${esc(toName)}</b></span>${btn('Bỏ chọn','jrAsTo',{code:''},'ghost small')}</p>`:'';
  const have=k=>v?v.pairs.filter(p=>p.kind===k).length+v.box.filter(b=>b.kind===k).length:0;
  const list=byPrice(ks.map(k=>({id:k.id,art:pairIcon(k.id,64),name:k.name,price:k.price,own:have(k.id),many:true,on:!!v?.pairs.some(p=>p.kind===k.id&&p.on),
    sel:st.psel===k.id,action:'jrAsPairPick',data:{kind:k.id}})));
  const x=list.find(x=>x.id===st.psel),shelf=grid('pair',list,st);
  if(!v)return {body:`${forWho}${shelf}<p class="muted small">Đang mở hộp quà…</p>`,detail:x?pairDetail(api,st,x):''};
  const K=id=>kindOf(api,id)||{emoji:'🎁',name:'Phụ kiện'};
  const incoming=v.incoming.length?`<section class="jr-card as-incoming" aria-label="Quà đang chờ bạn"><h3>🎁 Quà đang chờ bạn</h3><ul class="as-list">${v.incoming.map(o=>`<li><span class="as-pair-art">${pairIcon(o.kind,44)}</span>
      <span class="grow"><b>${esc(o.name)}</b><small>tặng bạn một chiếc ${esc(K(o.kind).emoji)} ${esc(K(o.kind).name)}, mỗi người đeo một chiếc</small></span>
      <span class="as-row-btns">${btn('Nhận','jrAsAnswer',{id:o.id,answer:'accept'},'primary small',busy)}${btn('Từ chối','jrAsAnswer',{id:o.id,answer:'decline'},'ghost small',busy)}</span></li>`).join('')}</ul></section>`:'';
  const box=v.box.length?`<section class="jr-card as-box" aria-label="Hộp quà"><h3>🎀 Hộp quà <small class="muted">${v.box.length}/${v.box_max}</small></h3><ul class="as-list">${v.box.map(b=>`<li class="as-box-row"><span class="as-pair-art">${pairIcon(b.kind,44)}</span>
      <span class="grow"><b>${esc(K(b.kind).emoji)} ${esc(K(b.kind).name)}</b>${friendPick(v,st,b.id)}</span>
      ${btn(`Bán lại · ${fmt(b.sell)} xu`,'jrAsSell',{id:b.id},'ghost small',busy)}</li>`).join('')}</ul></section>`:'';
  const sent=v.sent.length?`<section class="jr-card as-sent" aria-label="Đã gửi"><h3>⏳ Chờ bạn nhận</h3><ul class="as-list">${v.sent.map(o=>`<li><span class="as-pair-art">${pairIcon(o.kind,44)}</span>
      <span class="grow"><b>${esc(K(o.kind).emoji)} ${esc(K(o.kind).name)}</b><small>đã gửi tới ${esc(o.name)}</small></span>${btn('Rút lại','jrAsCancel',{id:o.id},'ghost small',busy)}</li>`).join('')}</ul></section>`:'';
  const on=v.pairs.filter(p=>p.on).length;
  const mine=v.pairs.length?`<section class="jr-card as-mine" aria-label="Cặp của bạn"><div class="as-mine-head"><b>🤝 Đang có ${v.pairs.length} cặp</b><small class="muted">đang đeo ${on}</small></div>
      <ul class="as-pairs">${pairRows(api,v.pairs)}</ul>
      <div class="as-mine-foot">${btn('Đeo hết','jrAsWearAll',{on:'1'},'ghost small',busy||on===v.pairs.length)}${btn('Cất hết','jrAsWearAll',{on:'0'},'ghost small',busy||!on)}</div></section>`:'';
  const full=v.can_buy===false?`<p class="wd-lock">🎀 Hộp quà đã đầy ${v.box_max} cặp chưa tặng. Tặng bớt rồi mua thêm nhé.</p>`:'';
  const bonds=(v.bond_in||[]).map(o=>({...o,r:relOf(api,o.label)})).filter(o=>o.r);
  const bondIn=bonds.length?`<section class="jr-card as-incoming" aria-label="Lời mời quan hệ"><h3>💞 Lời mời quan hệ</h3><ul class="as-list">${bonds.map(o=>`<li><span class="as-rel-emoji" aria-hidden="true">${esc(o.r.emoji)}</span>
      <span class="grow"><b>${esc(o.name)}</b><small>muốn hai bạn thành “${esc(o.r.name)}”</small></span>
      <span class="as-row-btns">${btn('Đồng ý','jrAsBondAnswer',{id:o.id,answer:'accept'},'primary small',busy)}${btn('Để sau','jrAsBondAnswer',{id:o.id,answer:'decline'},'ghost small',busy)}</span></li>`).join('')}</ul></section>`:'';
  return {body:`${bondIn}${incoming}${forWho}${box}${full}${shelf}${mine}${sent}`,detail:x?pairDetail(api,st,x):''};
}
function pairDetail(api,st,x){
  const v=api.charmView,k=kindOf(api,x.id),canBuy=!v||v.can_buy!==false;
  const room=v?Math.max(0,(v.box_max||10)-v.box.length-v.sent.length):1,q=Math.max(1,Math.min(st.pq?.[k.id]||1,Math.max(1,room)));
  const fr=v?.friends||[],to=st.to&&fr.find(f=>f.code===st.to);
  const stage=mirror(api,{...lookOf(api.state),pr:{...(myPairs()||{}),[k.id]:1}},`Nhân vật của bạn đeo thử ${k.name}`);
  const info=`<p class="as-d-price"><b>${fmt(k.price)} xu</b> / cặp</p><p class="as-item">${esc(k.item)}</p><p class="small">${esc(k.desc)}</p><p class="as-hint">${esc(k.hint)}</p>`;
  const who=fr.length?`<div class="as-d-who" role="group" aria-label="Tặng ngay cho"><span class="as-d-who-l">🎁 Tặng ngay cho</span><div class="as-d-chips">${btn('Để sau',
    'jrAsTo',{code:''},`chip${to?'':' active'}`)}${fr.map(f=>btn(esc(f.name),'jrAsTo',{code:f.code},`chip${to?.code===f.code?' active':''}`)).join('')}</div></div>`:'';
  const buy=`${who}${qtyRow(api,'jrAsPairQty',{kind:k.id},q,room,k.price)}${canBuy?'':`<p class="wd-lock">🎀 Hộp quà đã đầy ${v.box_max} cặp chưa tặng. Tặng bớt rồi mua thêm nhé.</p>`}
    <div class="as-d-btns">${btn(`${to?'Mua & tặng':'Mua cặp'}${q>1?` ×${q}`:''} · ${fmt(k.price*q)} xu`,'jrAsPairBuy',{kind:k.id},'primary as-d-go',busy||!canBuy)}</div>`;
  return detail({id:k.id,t:x.t,title:`${esc(k.emoji)} ${esc(k.name)}`,stage,info,buy});
}

/* ---- 🐾 Thú cưng: v4/pets.js gives the cards and the picked one's detail (loaded on first sight) ---- */
function petShelf(env,st){
  const {api}=env,m=PT.use(),part=partOf(st.tab);
  const chips=`<div class="as-cats" role="group" aria-label="Hàng cho thú cưng">${petTabs(api).map(([id,e,l])=>`<button type="button" class="chip${st.tab===id?' active':''}" aria-pressed="${st.tab===id}" data-action="jrAsTab" data-tab="${id}"><span aria-hidden="true">${e}</span> ${esc(l)}</button>`).join('')}</div>`;
  if(!m)return {body:chips+skeleton(),detail:''};
  const md=m.petShopModel(env,part);
  if(!md)return {body:chips+'<p class="pt-empty">⏳</p>',detail:''};
  if(md.empty)return {body:chips+`<p class="muted">${esc(md.empty)}</p>`,detail:''};
  const list=byPrice(md.cards.map(x=>({...x,action:x.locked?null:'jrAsPet',data:{id:x.id}})));
  const x=md.detail&&list.find(c=>c.id===md.detail.id);
  const d=x?detail({id:x.id,t:x.t,title:md.detail.title,stage:md.detail.stage,info:md.detail.info+(md.detail.forge?`<p class="as-d-note">${forgeBtn(md.detail.forge)}</p>`:''),
    buy:`<div class="pt-root pt-embed as-ptd" aria-busy="${!!md.busy}">${md.detail.flash}${md.detail.controls}${md.detail.bar}</div>`}):'';
  const lux=md.lux?.length?`<h4 class="as-sub">💎 Dòng sang · 🔀 ghép mới có</h4><div class="as-grid">${md.lux.map(c=>`<div class="as-cell">${card({...c,t:RARITY.length-1})}</div>`).join('')}</div>`:'';
  return {body:`${chips}${md.note||''}${grid(st.tab,list,st,{groups:md.groups})}${lux}`,detail:d};
}

/* ---- 🔗 Nơi mua khác: the screens that sell the rest ---- */
function moreShelf(env){
  const list=moreList(env.api);
  return {body:`<div class="as-shelf">${list.map(([a,e,name,desc])=>`<button type="button" class="jr-card as-kind as-more" data-action="${a}"><span class="as-kind-art" aria-hidden="true">${e}</span><span class="as-kind-text"><b>${esc(name)}</b><small>${esc(desc)}</small></span></button>`).join('')}</div>`,detail:''};
}

/* ---- the sheet ---- */
function head(){
  return `<header class="sheet-head jr-head"><button type="button" class="btn ghost small jr-back" data-action="jrView" data-view="home" aria-label="Quay lại">${icon('back',18)}</button><div class="grow"><span class="eyebrow">MUA SẮM</span><h2>🛍️ ${esc(SHOP_NAME)}</h2></div></header>`;
}
/** The tabs this save has, in the owner's order ([id, emoji, label]; 🐾 stands for the pet shelves). */
function tabsOf(api){
  const ok=shopTabs(api);
  return TOP.filter(([id])=>id==='pet'?ok.some(isPet):ok.includes(id));
}
export function accShopView(env){
  const {api,ui}=env,c=W(api),st=S(ui);bindKeys(env);
  if(!c||!api.state.journey?.gender)return head(api)+`<div class="sheet-body jr-body"><p class="muted">Cửa hàng đang bày hàng, lát nữa quay lại nhé.</p></div>`;
  if(!shopTabs(api).includes(st.tab))st.tab='acc';
  const cur=isPet(st.tab)?'pet':st.tab,n=waiting(api);
  if(cur==='pet')(st.last??={}).pet=st.tab;
  const tabs=tabsOf(api),nav=tabs.length>1?`<nav class="as-tabs" role="tablist" aria-label="Quầy hàng">${tabs.map(([id,e,label])=>{const on=id===cur;
    return `<button type="button" role="tab" class="as-tab${on?' active':''}" aria-selected="${on}" data-action="jrAsTab" data-tab="${id}"><span aria-hidden="true">${e}</span>${label}${id==='pair'&&n?`<i class="as-badge" aria-label="${n} món quà đang chờ">${n}</i>`:''}</button>`;}).join('')}</nav>`:'';
  const {body,detail:d}=cur==='pet'?petShelf(env,st):cur==='more'?moreShelf(env):cur==='wing'?wingShelf(env,st):cur==='wear'?wearShelf(env,st):cur==='pair'?pairShelf(env,st):accShelf(env,st);
  return head(api)+`<div class="sheet-body jr-body wd as as-v2${d?' has-detail':''}">${nav}${body}${d}</div>`;
}

/* ---- the shop's own actions (accShopAction sends them here first) ---- */
const focusSoon=sel=>globalThis.requestAnimationFrame?.(()=>document.querySelector(sel)?.focus?.({preventScroll:true}));
/** Close the detail sheet of the shelf on screen; the focus goes back to its card. */
function close(env,st){
  const cur=isPet(st.tab)?'pet':st.tab;let key='';
  if(cur==='acc'){key=st.draft;st.draft=null;}
  else if(cur==='wear'){key=st.cdraft;st.cdraft=null;}
  else if(cur==='wing'){key=st.wtry;st.wtry=null;st.reveal=null;}
  else if(cur==='pair'){key=st.psel;st.psel=null;}
  else if(cur==='pet'){const m=PT.use();key=m?.petShopModel(env,partOf(st.tab))?.detail?.id||'';m?.petShopPick(env,partOf(st.tab),'');}
  env.renderSheet();if(key&&typeof document!=='undefined')focusSoon(`#sheet .as-card[data-key="${globalThis.CSS?.escape?.(String(key))??key}"]`);
}
export const focusDetail=()=>{if(typeof document!=='undefined')focusSoon('#sheet [data-as-detail]');};
export async function shopAction(action,data,el,env){
  const {api,ui,renderSheet}=env,st=S(ui);
  switch(action){
    case'jrAsTab':{const ok=shopTabs(api);
      if(data.tab==='pet'){const pets=ok.filter(isPet);st.tab=pets.includes(st.last?.pet)?st.last.pet:pets[0]||'acc';}
      else st.tab=ok.includes(data.tab)?data.tab:'acc';
      if(isPet(st.tab))(st.last??={}).pet=st.tab;renderSheet(false);return true;}
    case'jrAsF':{const f=F(st,String(data.key||st.tab));
      if(data.k==='r')f.r=Number(data.v)>=0?Number(data.v):-1;else if(data.k==='sort')f.sort=['asc','desc'].includes(data.v)?data.v:'';
      else if(data.k==='miss')f.miss=!!data.v;else if(data.k==='g')f.g=String(data.v||'');else if(data.k==='reset')Object.assign(f,{r:-1,sort:'',miss:false,g:''});
      renderSheet();return true;}
    case'jrAsClose':close(env,st);return true;
    case'jrAsNoAsk':{const on=el?.type==='checkbox'?el.checked:!noAsk();setNoAsk(on);
      renderSheet();return true;}
    case'jrAsPairPick':st.psel=kindOf(api,data.kind)&&st.psel!==data.kind?data.kind:null;renderSheet();if(st.psel)focusDetail();return true;
    case'jrAsPet':{const m=PT.use();if(!m)return true;const part=partOf(st.tab),cur=m.petShopModel(env,part)?.detail?.id;
      m.petShopPick(env,part,cur===data.id?'':data.id);renderSheet();if(cur!==data.id)focusDetail();return true;}
    case'jrAsCart':{const it=wdItem(api,data.item);if(!it||!wdStatus(api,it)?.buy)return true;
      const was=inCart(st,it.id);cartToggle(st,it.id);
      env.toast(was?`Đã bỏ ${it.name} khỏi giỏ`:inCart(st,it.id)?`🧺 ${it.name} vào giỏ · ${st.cart.length} món`:'Giỏ đầy 12 món rồi','hint');renderSheet();return true;}
  }
  return false;
}
/** Esc closes the detail sheet first (not the whole shop); a tap outside an open filter list closes it. */
let keyEnv=null;
function bindKeys(env){
  keyEnv=env;if(bindKeys.on||typeof document==='undefined'||!document.addEventListener)return;bindKeys.on=true;
  document.addEventListener('keydown',e=>{
    if(e.key!=='Escape'||document.querySelector('#confirmDialog[open]'))return;
    const dd=document.querySelector('#sheet[open] .as-dd[open]'),d=document.querySelector('#sheet[open] [data-as-detail]');if(!dd&&!d)return;
    e.preventDefault();e.stopPropagation();if(dd){dd.open=false;dd.querySelector('summary')?.focus?.();return;}
    if(keyEnv)close(keyEnv,S(keyEnv.ui));
  },true);
  document.addEventListener('click',e=>{for(const dd of document.querySelectorAll('#sheet .as-dd[open]'))if(!dd.contains(e.target))dd.open=false;},true);
}
