/** 🛍️ Cửa hàng (owner 23/10: "với bán đồ này đưa ra 1 cái gọi là shop riêng đi, xong thú cưng hay người gì trong đó cả",
 * "cửa hàng hoặc shop đều là 1 đó nhé, mua gì nằm đó hết cho dễ"): one place to buy, its own entry in the menu (app.js,
 * beside the hubs) and in the new map's Tiện ích (isometric-shell.js). Three groups of shelves: 👤 Cho bạn (🎀 Phụ kiện,
 * 🤝 Phụ kiện đôi, 🪽 Cánh, 👕 Trang phục), 🐾 Thú cưng (🐶 Mua bé, 👗 Đồ cho bé, 🪽 Cánh cho bé, 🎾 Đồ chơi, 🧰 Linh kiện:
 * v4/pets.js petEmbedHTML draws its own shelves here, same picks and jr_pet_* commands; its dialog keeps selling too) and
 * 🏠 Nhà & xe (cards to the screens that sell the rest: garage, gadgets, home, lux…). 👕 Trang phục: the wardrobe's pieces
 * with a price, tried on the mirror and bought with jr_wd_buy; Tủ đồ (v4/wardrobe.js) is for wearing, its buy buttons
 * open this shelf.
 * ⚒️ Cường hóa (forgeView, jrView 'forge', owner 23/10): every ghép / nâng hạng in one place (🪽 ghép cánh, 🧬 ghép thú,
 * 👗 ghép đồ thú, 🧰 cường hóa & lên hạng linh kiện), each with ⚡ Cường hóa nhanh: a valid set picked on the client, the
 * usual question with what is used and the fee, one enhancement with the existing command.
 * 🛍️ Tiệm phụ kiện Hạt Cườm (owner 22/10: "chuyển chỗ mua linh kiện từ avatar ra 1 nơi khác"): accessories are bought
 * here now, no longer in the wardrobe, which keeps trying on, colours and wearing (v4/wardrobe.js). Opened from the town
 * (Mua sắm, isometric/town-utilities.js), the menu (app.js) and the wardrobe (journey.js: jrView 'accshop', actions jrAs*).
 * Two shelves:
 * - 🎀 Phụ kiện: the wardrobe's accessories (game/wardrobe.py, slot acc), tried on the mirror, bought with jr_wd_buy as
 *   before (so every earlier purchase stays where it was) and worn with jr_wd_wear.
 * - 🤝 Phụ kiện đôi (góp ý #484): Chí cốt, Bạn thân, Tri kỉ, bought as a pair (charm_buy), one piece given to a friend
 *   (charm_offer), who accepts or declines; the box, the offers sent and received, every pair with its own switch (no
 *   limit on how many are worn). Rules on the server (game/friend_charms.py); data and the shared rows: v4/charms.js.
 *   💞 Under "Đang có", the relationship with that friend (charm_bond / charm_bond_answer / charm_bond_off): asked by one,
 *   shown once both agree; the asks waiting for this player on top.
 * - 🪽 Cánh (game/wings.py, owner 22/10): a style bought rolls hạng D or C on the server (jr_pet_wing_buy with a request id:
 *   a retry answers the same wings), shown in a small reveal; one worn at a time (jr_pet_wing_wear). Three wings ghép like
 *   the pets in ⚒️ Cường hóa (jr_pet_wing_fuse, the first one picked is the main one and keeps its style). The tier's badge and colour on
 *   every tile, what it adds (tiền kiếm được, sức thú khi đấu) under the mirror. */
import {icon,escapeHTML as esc} from '../icons.js';
import {confirmPurchase} from './payment.js';
import {lookOf,figureSVG,portrait,pairIcon,myPairs,wingIcon,wingOfState,WING_TIERS,WING_TIER_COLOR} from './look.js';
import {kinds,kindOf,adopt,refreshCharms,pairRows,waiting,relOf,SHOP_NAME} from './charms.js';
import {wdStatus,wdItem,wdThumb} from './wardrobe.js';
import {lazy,skeleton} from '../lazy.js';
import {townServiceAvailable} from '../isometric/town-utilities.js';   // 🏠 which other shops this save has (the menu's gates)
// 🐾 the pet shelves (v4/pets.js), loaded the first time that group opens
const PT=lazy(()=>import('./pets.js'),{css:['/css/pets.css']});

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const W=api=>api.content.journey?.wardrobe;
const S=ui=>ui.as??={tab:'acc',draft:null,to:'',wfz:[],reveal:null,wtry:null};
/** The shelves: 👤 for the character, 🐾 for the pets, 🏠 the others ([id, emoji, label, the pets.js shelf]). */
const ME=[['acc','🎀','Phụ kiện'],['pair','🤝','Phụ kiện đôi'],['wing','🪽','Cánh'],['wear','👕','Trang phục']];
const PET=[['pbuy','🐶','Mua bé','buy'],['pwear','👗','Đồ cho bé','wear'],['pwing','🪽','Cánh cho bé','wing'],['ptoy','🎾','Đồ chơi','toy'],['pgear','🧰','Linh kiện','gear']];
/** The pet shelves this save has: pets on the server and the story mode (game/pets.py), the wardrobe and gear when sent. */
function petTabs(api){
  const J=api.state.journey,c=api.content.journey?.pets;if(!J?.story||!J.pets||!c)return [];
  return PET.filter(([id])=>id==='pwear'||id==='pwing'?!!c.wardrobe:id==='pgear'?!!c.tiers:true);
}
const meTabs=c=>ME.filter(([id])=>id!=='wing'||c.wings);
/** Every shelf id open to this save (journey.js jrAccShop checks a `tab` against it). */
export const shopTabs=api=>{const c=W(api);return c?[...meTabs(c),...petTabs(api)].map(x=>x[0]).concat(moreList(api).length?['more']:[]):[];};
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,action,data={},style='',dis=false)=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}${dis?' disabled':''}>${label}</button>`;
const rid=()=>globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
let busy=false;
/** What a purchase can draw on (wallet + the bank account): the "Tối đa" of a quantity; the server checks it again. */
const funds=api=>{const J=api.state.journey||{},b=J.bank;return Math.max(0,Number(J.wallet)||0)+(b?.open?Math.max(0,Number(b.balance)||0):0);};
/** 🛍️ owner 23/10 "mua thì cho mua nhiều cái 1 lần": − N + with ×1 ×5 ×10 and "Tối đa" (the server's limit, the room, the
 * money), the sum; one confirm, one command (the server takes all or none). Nothing when only one fits. */
function qtyRow(api,action,data,q,cap,price){
  if(cap<=1)return '';
  const most=Math.max(1,Math.min(cap,price>0?Math.floor(funds(api)/price)||1:cap)),n=Math.max(1,Math.min(q,cap));
  const quick=[1,5,10].filter(x=>x<cap&&x!==most);
  const b=(m,label,dis,extra='')=>`<button type="button" class="as-qty-b${extra}" data-action="${action}"${attrs({...data,n:m})}${dis?' disabled':''}${label.length<3?` aria-label="${m<n?'Bớt một':'Thêm một'}"`:''}>${label}</button>`;
  return `<div class="as-qty" role="group" aria-label="Số lượng mua"><span class="as-qty-step">${b(n-1,'−',n<=1)}<b class="as-qty-n" aria-live="polite">${n}</b>${b(n+1,'+',n>=cap)}</span>
    <span class="as-qty-chips">${quick.map(x=>b(x,`×${x}`,false,x===n?' on':'')).join('')}${b(most,`Tối đa ×${most}`,false,most===n?' on':'')}</span>
    <small class="as-qty-sum">${n} × ${fmt(price)} = <b>${fmt(price*n)} xu</b></small></div>`;
}
const cartToggle=(st,id)=>{const c=st.cart??=[],i=c.indexOf(id);if(i>=0)c.splice(i,1);else if(c.length<12)c.push(id);};   // game/wardrobe.py BUY_MANY_MAX
/** 🧺 Several pieces at once (🎀 and 👕: each piece is owned once, so "many" is many pieces): the cart, its sum, one buy. */
const cartOf=(api,st)=>(st.cart||[]).map(id=>wdItem(api,id)).filter(it=>it&&wdStatus(api,it)?.buy);
function cartBar(api,st){
  const xs=cartOf(api,st);if(!st.multi&&!xs.length)return '';
  const sum=xs.reduce((a,it)=>a+wdStatus(api,it).price,0);
  return `<section class="jr-card as-cart" aria-live="polite"><div class="as-cart-head"><b>🧺 Giỏ · ${xs.length} món</b><span>${fmt(sum)} xu</span></div>
    <p class="small muted">${xs.length?xs.map(it=>esc(it.name)).join(', '):'Chạm các món muốn mua, ở cả 🎀 Phụ kiện và 👕 Trang phục, rồi mua một lần.'}</p>
    <div class="as-row-btns">${btn(`🛍️ Mua cả giỏ · ${fmt(sum)} xu`,'jrAsBuyMany',{},'primary small',busy||!xs.length)}${btn(xs.length?'Bỏ giỏ':'Thôi','jrAsMulti',{off:'1'},'ghost small')}</div></section>`;
}
const multiChip=st=>`<div class="as-chips as-multi">${btn(st.multi?'✓ Đang chọn nhiều món':'🧺 Chọn nhiều món, mua một lần','jrAsMulti',{},`chip${st.multi?' active':''}`)}</div>`;
const inCart=(st,id)=>(st.cart||[]).includes(id);
const cartLook=(api,st)=>Object.fromEntries(cartOf(api,st).map(it=>[it.slot,it.id]));

/* ---- 🎀 Phụ kiện ---- */
function accTile(api,st,it,saved,look,g){
  const worn=saved.acc===it.id,on=look.acc===it.id,stt=wdStatus(api,it);
  const tag=worn?'<small class="wd-tag worn">Đang đeo</small>'
    :stt?.lock?`<small class="wd-tag lock">🔒 ${esc(stt.lock)}</small>`
    :stt?.buy?`<small class="wd-tag price">${stt.price<it.price?`<s>${fmt(it.price)}</s> `:''}${fmt(stt.price)} xu</small>`
    :`<small class="wd-tag">${it.price?'Đã có':it.need?'Đã mở':'Miễn phí'}</small>`;
  const cart=inCart(st,it.id);
  return `<button type="button" class="wd-item${on?' on':''}${cart?' in-cart':''}${stt?.lock?' locked':''}" data-action="jrAsTry" data-item="${esc(it.id)}" aria-pressed="${st.multi?cart:on}">
    <span class="wd-thumb" aria-hidden="true">${portrait({...look,acc:it.id},g,64,'')}</span><b>${esc(it.name)}</b>${tag}${cart?'<i class="as-incart" aria-label="trong giỏ">🧺</i>':''}</button>`;
}
function accActions(api,st,saved,look){
  if(!st.draft||st.draft===saved.acc)return `<p class="wd-hint">👇 Chạm một món để đeo thử trước gương.</p>`;
  const it=wdItem(api,st.draft),stt=it&&wdStatus(api,it);if(!it)return '';
  const main=stt?.lock?`<p class="wd-lock">🔒 ${esc(it.name)}: ${esc(stt.lock.charAt(0).toLowerCase()+stt.lock.slice(1))}.</p>`
    :stt?.buy?btn(`Mua ${esc(it.name)} · ${fmt(stt.price)} xu`,'jrAsBuy',{item:it.id},'primary full',busy)
    :btn(`🎀 Đeo ${esc(it.name)}`,'jrAsWearAcc',{item:it.id},'primary full',busy);
  return main+btn('Bỏ thử','jrAsReset',{},'ghost small full');
}
function accShelf(env,st){
  const {api}=env,c=W(api),g=api.state.journey.gender,saved=lookOf(api.state),look={...saved,...(st.draft?{acc:st.draft}:{})};
  const pr=myPairs(),mirror=figureSVG(pr?{...look,pr}:look,g,{w:150,h:212,label:'Nhân vật của bạn đang đeo thử'});
  const items=c.items.filter(x=>x.slot==='acc'&&x.id!=='pk_khong');
  const staff=c.staff_off&&api.state.careers?.[c.shop]?.started?`<p class="wd-note good">🏷️ Giá nhân viên ${esc(c.shop_name)}: −${c.staff_off}%</p>`:'';
  return `<section class="jr-card wd-stage">
      <div class="wd-mirror">${mirror}</div>
      <div class="wd-side"><h3>${esc(api.state.name)}</h3>${staff}<div class="wd-actions" aria-live="polite">${accActions(api,st,saved,look)}</div></div>
    </section>
    ${multiChip(st)}${cartBar(api,st)}
    <div class="wd-grid">${items.map(it=>accTile(api,st,it,saved,look,g)).join('')}</div>
    <p class="wd-note as-foot">🎀 ${esc(c.acc_shop?.title||'Tiệm phụ kiện')} · 🎨 Đổi màu, phối với áo quần: ${btn('👗 Tủ đồ','jrWardrobe',{},'ghost small')}</p>`;
}

/* ---- 👕 Trang phục: the wardrobe's pieces with a price (game/wardrobe.py), one tried on at a time ---- */
const CL=['top','bottom','shoes','hair'];
const CL_EMOJI={top:'👕',bottom:'👖',shoes:'👟',hair:'💇'};
function clActions(api,st,saved){
  const it=st.cdraft&&wdItem(api,st.cdraft);
  if(!it||saved[it.slot]===it.id)return `<p class="wd-hint">👇 Chạm một món để mặc thử trước gương.</p>`;
  const stt=wdStatus(api,it);
  const main=stt?.lock?`<p class="wd-lock">🔒 ${esc(it.name)}: ${esc(stt.lock.charAt(0).toLowerCase()+stt.lock.slice(1))}.</p>`
    :stt?.buy?btn(`Mua ${esc(it.name)} · ${fmt(stt.price)} xu`,'jrAsClBuy',{item:it.id},'primary full',busy)
    :btn(`${CL_EMOJI[it.slot]||'✨'} Mặc ${esc(it.name)}`,'jrAsClOn',{item:it.id},'primary full',busy);
  return main+btn('Bỏ thử','jrAsClTry',{item:''},'ghost small full');
}
function wearShelf(env,st){
  const {api}=env,c=W(api),g=api.state.journey.gender,saved=lookOf(api.state);
  const slots=c.slots.filter(x=>CL.includes(x.id)).sort((a,b)=>CL.indexOf(a.id)-CL.indexOf(b.id));
  const it=st.cdraft&&wdItem(api,st.cdraft);
  if(!slots.some(x=>x.id===st.cslot))st.cslot=it&&CL.includes(it.slot)?it.slot:slots[0]?.id||'top';   // from Tủ đồ: the piece's own rack
  const look={...saved,...(st.multi?cartLook(api,st):{}),...(it?{[it.slot]:it.id}:{})},pr=myPairs();   // 🧺 the cart on the mirror: a whole outfit
  const mirror=figureSVG(pr?{...look,pr}:look,g,{w:150,h:212,label:'Nhân vật của bạn đang mặc thử'});
  const staff=c.staff_off?api.state.careers?.[c.shop]?.started?`<p class="wd-note good">🏷️ Giá nhân viên ${esc(c.shop_name)}: −${c.staff_off}%</p>`:`<p class="wd-note">🏷️ Làm ở ${esc(c.shop_name)}: giảm ${c.staff_off}%</p>`:'';
  const chips=slots.map(x=>`<button type="button" class="chip${st.cslot===x.id?' active':''}" aria-pressed="${st.cslot===x.id}" data-action="jrAsClSlot" data-slot="${esc(x.id)}">${CL_EMOJI[x.id]||''} ${esc(x.name)}</button>`).join('');
  const tile=x=>{const on=look[x.slot]===x.id,worn=saved[x.slot]===x.id,stt=wdStatus(api,x);
    const tag=worn?'<small class="wd-tag worn">Đang mặc</small>':stt?.lock?`<small class="wd-tag lock">🔒 ${esc(stt.lock)}</small>`
      :stt?.buy?`<small class="wd-tag price">${stt.price<x.price?`<s>${fmt(x.price)}</s> `:''}${fmt(stt.price)} xu</small>`:'<small class="wd-tag">Đã có</small>';
    const cart=inCart(st,x.id);
    return `<button type="button" class="wd-item${on?' on':''}${cart?' in-cart':''}${stt?.lock?' locked':''}" data-action="jrAsClTry" data-item="${esc(x.id)}" aria-pressed="${st.multi?cart:on}">
      <span class="wd-thumb" aria-hidden="true">${wdThumb({...saved,[x.slot]:x.id},g,x.slot)}</span><b>${esc(x.name)}</b>${tag}${cart?'<i class="as-incart" aria-label="trong giỏ">🧺</i>':''}</button>`;};
  const items=c.items.filter(x=>x.slot===st.cslot&&x.price);
  return `<section class="jr-card wd-stage">
      <div class="wd-mirror">${mirror}</div>
      <div class="wd-side"><h3>${esc(api.state.name)}</h3>${staff}<div class="wd-actions" aria-live="polite">${clActions(api,st,saved)}</div></div>
    </section>
    <div class="as-chips" role="group" aria-label="Loại đồ">${chips}</div>
    ${multiChip(st)}${cartBar(api,st)}
    <div class="wd-grid">${items.map(tile).join('')||'<p class="muted">Quầy này đang hết hàng.</p>'}</div>
    <p class="wd-note as-foot">🎨 Đổi màu, phối cả bộ: ${btn('👗 Tủ đồ','jrWardrobe',{},'ghost small')}</p>`;
}

/* ---- 🐾 Thú cưng: v4/pets.js draws the shelf (its picks, its main button), loaded on first sight ---- */
function petShelf(env,st){
  const m=PT.use(),part=PET.find(x=>x[0]===st.tab)?.[3]||'buy';
  return m?m.petEmbedHTML(env,part):skeleton();
}

/* ---- 🤝 Phụ kiện đôi ---- */
function friendPick(v,st,id){
  const fr=v.friends||[];
  if(!fr.length)return `<p class="muted small">Kết bạn trước rồi tặng nhé.</p>`;
  const opts=fr.map(f=>`<option value="${esc(f.code)}"${f.code===st.to?' selected':''}>${esc(f.name)}</option>`).join('');
  return `<div class="as-give"><label class="sr-only" for="as-to-${esc(id)}">Tặng cho</label><select class="input" id="as-to-${esc(id)}" data-as-to>${st.to&&fr.some(f=>f.code===st.to)?'':'<option value="">Chọn một người bạn…</option>'}${opts}</select>
    ${btn('🎁 Tặng','jrAsGive',{id},'primary small',busy)}</div>`;
}
function pairShelf(env,st){
  const {api}=env,v=api.charmView,list=kinds(api);
  refreshCharms(env,15000)?.then(x=>{if(x)env.renderSheet(false);});   // a gift may have come in since
  const canBuy=!v||v.can_buy!==false,toName=st.to&&v?.friends?.find(f=>f.code===st.to)?.name;
  const room=v?Math.max(0,(v.box_max||10)-v.box.length-v.sent.length):1,pq=st.pq||{};
  const forWho=toName?`<p class="jr-card as-for">🎁 <span class="grow">Đang chọn quà cho <b>${esc(toName)}</b>: mua xong là gửi luôn.</span>${btn('Bỏ chọn','jrAsTo',{code:''},'ghost small')}</p>`:'';
  const cat=list.map(k=>`<article class="jr-card as-kind as-${esc(k.id)}">
      <span class="as-kind-art">${pairIcon(k.id,84,`Cặp ${k.name}`)}</span>
      <div class="as-kind-text"><h3>${esc(k.emoji)} ${esc(k.name)}</h3><p class="as-item">${esc(k.item)}</p><p class="small">${esc(k.desc)}</p><p class="as-hint">${esc(k.hint)}</p>
      ${qtyRow(api,'jrAsPairQty',{kind:k.id},pq[k.id]||1,room,k.price)}
      ${btn(`${toName?'Mua & tặng':'Mua cặp'}${(pq[k.id]||1)>1&&room>1?` ×${Math.min(pq[k.id],room)} · ${fmt(k.price*Math.min(pq[k.id],room))}`:` · ${fmt(k.price)}`} xu`,'jrAsPairBuy',{kind:k.id},'primary small',busy||!canBuy)}</div></article>`).join('');
  if(!v)return `<div class="as-shelf">${cat}</div><p class="muted small">Đang mở hộp quà…</p>`;
  const K=id=>kindOf(api,id)||{emoji:'🎁',name:'Phụ kiện'};
  const incoming=v.incoming.length?`<section class="jr-card as-incoming" aria-label="Quà đang chờ bạn"><h3>🎁 Quà đang chờ bạn</h3><ul class="as-list">${v.incoming.map(o=>`<li><span class="as-pair-art">${pairIcon(o.kind,44)}</span>
      <span class="grow"><b>${esc(o.name)}</b><small>tặng bạn một chiếc ${esc(K(o.kind).emoji)} ${esc(K(o.kind).name)}, mỗi người đeo một chiếc</small></span>
      <span class="as-row-btns">${btn('Nhận','jrAsAnswer',{id:o.id,answer:'accept'},'primary small',busy)}${btn('Từ chối','jrAsAnswer',{id:o.id,answer:'decline'},'ghost small',busy)}</span></li>`).join('')}</ul></section>`:'';
  const box=v.box.length?`<section class="jr-card as-box" aria-label="Hộp quà"><h3>🎀 Hộp quà <small class="muted">${v.box.length}/${v.box_max}</small></h3><p class="muted small">Tặng một chiếc cho bạn bè, cặp này thành của hai người.</p><ul class="as-list">${v.box.map(b=>`<li class="as-box-row"><span class="as-pair-art">${pairIcon(b.kind,44)}</span>
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
  return `${bondIn}${incoming}${forWho}${mine}${box}${sent}${full}<div class="as-shelf">${cat}</div>`;
}

/* ---- 🪽 Cánh: bought and worn here; ghép in ⚒️ Cường hóa (forgeView) ---- */
const WC=api=>api.content.journey?.wardrobe?.wings;
const wingsOf=api=>api.state.journey?.wings||null;
const ownWings=api=>{const w=wingsOf(api);return Array.isArray(w?.own)?w.own:[];};
const tierName=r=>WING_TIERS[r]||'D';
const badge=r=>`<i class="wg-tier${r===WING_TIERS.length-1?' top':''}" style="--wt:${WING_TIER_COLOR[r]||WING_TIER_COLOR[0]}" title="Hạng ${esc(tierName(r))}">${r===WING_TIERS.length-1?'🌟 HT':esc(tierName(r))}</i>`;   // 🌟 Huyền thoại: short on the badge
const styleOf=(api,k)=>WC(api)?.styles?.find(x=>x.id===k)||null;
const wName=(api,x)=>`${styleOf(api,x.k)?.name||'Cánh'} ${tierName(x.r)}`;
function wingPerks(api,r){const c=WC(api);if(!c)return '';
  return `<ul class="wg-perks"><li>💰 +${c.earn[r]}% tiền kiếm được khi làm việc</li><li>⚔️ +${c.battle[r]}% máu và sức đánh cho thú khi đấu</li></ul>`;}
/** What three wings give (game/wings.py fuse): the main one goes to `to`, the fee is the lowest tier's, from tier S a miss
 * loses the two others. */
function wingFuseOf(api,xs){
  const c=WC(api),low=Math.min(...xs.map(x=>x.r)),m=xs[0],top=WING_TIERS.length-1;
  return {m,low,to:low===top-1?top:Math.max(m.r,low+1),fee:c.fee[Math.min(low,c.fee.length-1)],lose:low>=c.lose_from};
}
function fusePanel(api,st,own){
  const xs=st.wfz.map(id=>own.find(x=>x.id===id)).filter(Boolean);
  if(!xs.length)return own.length>=3?`<p class="wd-hint">🧬 Hoặc tự chọn ba đôi: đôi chọn đầu tiên là cánh chính, giữ nguyên kiểu.</p>`:'';
  const {m,to,fee,lose}=wingFuseOf(api,xs),top=WING_TIERS.length-1;
  const why=xs.length<3?`Chọn thêm ${3-xs.length} đôi nữa.`:m.r>=top?'Cánh chính đã là huyền thoại.':'';
  return `<section class="jr-card wg-fuse" aria-live="polite"><div class="wg-fuse-row">${xs.map((x,i)=>`<span class="wg-fuse-slot${i?'':' main'}">${wingIcon(x,48)}${badge(x.r)}</span>`).join('<b aria-hidden="true">+</b>')}</div>
    <p class="small">${why?esc(why):`Thành công: <b>${esc(styleOf(api,m.k)?.name||'Cánh')}</b> ${to>m.r?'lên':'giữ'} hạng <b>${esc(tierName(to))}</b>${to>m.r?'':' (ghép ba đôi cùng hạng mới lên được)'}, hai đôi kia dùng hết. Trượt: ${lose?'⚠️ hai đôi kia sẽ mất, cánh chính ở lại':'ba đôi vẫn còn'}, mất phí.`}</p>
    <div class="as-row-btns">${btn(`🧬 Ghép · ${fmt(fee)} xu`,'jrAsWingFuse',{},'primary small',busy||!!why)}${btn('Bỏ chọn','jrAsWingPick',{id:''},'ghost small')}</div></section>`;
}
/** ⚡ Cường hóa nhanh for wings (owner 23/10): three wings of the highest tier that has three (below Huyền thoại); the
 * main one is the wing worn when it is among them, else the dearest style; the two others never the one worn. */
export function wingQuick(api){
  const w=wingsOf(api),own=ownWings(api),top=WING_TIERS.length-1,price=x=>styleOf(api,x.k)?.price||0;
  for(let r=top-1;r>=0;r--){
    const g=own.filter(x=>x.r===r);if(g.length<3)continue;
    const main=g.find(x=>x.id===w?.on)||[...g].sort((a,b)=>price(b)-price(a))[0];
    const rest=g.filter(x=>x!==main).sort((a,b)=>(a.id===w?.on)-(b.id===w?.on)||price(a)-price(b));
    return [main,rest[0],rest[1]];
  }
  return null;
}
const wingTile=(api,w,x,pick=-1,forge=false)=>{const on=x.id===w.on;
  return `<li class="wg-tile${on?' on':''}${pick>=0?' picked':''}" style="--wt:${WING_TIER_COLOR[x.r]}">${forge?`<button type="button" class="wg-pick" data-action="jrAsWingPick" data-id="${esc(x.id)}" aria-pressed="${pick>=0}" aria-label="${esc(wName(api,x))}${pick===0?', cánh chính':''}${on?', đang đeo':''}">`:`<span class="wg-pick">`}${wingIcon(x,64)}${badge(x.r)}${pick>=0?`<i class="wg-num" aria-hidden="true">${pick+1}</i>`:''}${forge?'</button>':'</span>'}
    <small>${esc(styleOf(api,x.k)?.name||'Cánh')}${forge&&on?' · đang đeo':''}</small>${forge?'':`<span class="as-row-btns">${on?btn('Cất','jrAsWingWear',{id:''},'ghost small',busy):btn('Đeo','jrAsWingWear',{id:x.id},'small',busy)}${btn('Bỏ','jrAsWingDrop',{id:x.id},'ghost small',busy)}</span>`}</li>`;};
const sortWings=own=>[...own].sort((a,b)=>b.r-a.r||String(a.k).localeCompare(b.k));
const wingReveal=(api,st)=>st.reveal?.length?`<section class="jr-card wg-reveal" aria-live="polite"><h3>🎉 ${st.reveal.length>1?'Mở hộp cánh':'Cánh mới'}</h3><div class="wg-reveal-row">${st.reveal.map((x,i)=>`<span class="wg-reveal-item" style="--i:${i}">${wingIcon(x,72,wName(api,x))}${badge(x.r)}</span>`).join('')}</div>${btn('Tuyệt!','jrAsWingReveal',{},'primary small')}</section>`:'';
const wingTable=c=>`<details class="jr-card wg-table"><summary>📈 Hạng cánh được gì</summary><table><thead><tr><th>Hạng</th><th>Tiền kiếm được</th><th>Thú khi đấu</th></tr></thead><tbody>${c.earn.map((e,r)=>`<tr><td>${badge(r)}</td><td>+${e}%</td><td>+${c.battle[r]}%</td></tr>`).join('')}</tbody></table></details>`;
function wingShelf(env,st){
  const {api}=env,c=WC(api);
  if(!c)return `<p class="muted">Cánh đang về hàng, lát nữa quay lại nhé.</p>`;
  const w=wingsOf(api)||{},own=ownWings(api),worn=wingOfState(api.state),g=api.state.journey.gender;
  const show=st.wtry?{k:st.wtry,r:0}:worn,look=lookOf(api.state),pr=myPairs();
  const mirror=figureSVG({...look,...(pr?{pr}:{}),...(show?{wg:show}:{})},g,{w:150,h:212,label:show?'Nhân vật của bạn với đôi cánh':'Nhân vật của bạn'});
  const wx=worn&&own.find(x=>x.id===w.on);
  const side=st.wtry?`<h3>${esc(styleOf(api,st.wtry)?.name||'')}</h3><p class="small">Đang thử trước gương. Mua xong mới biết ra hạng D hay C nhé.</p>${btn('Bỏ thử','jrAsWingTry',{k:''},'ghost small')}`
    :wx?`<h3>${esc(wName(api,wx))} ${badge(wx.r)}</h3>${wingPerks(api,wx.r)}${w.got?`<p class="small muted">Hôm nay cánh đã thêm ${fmt(w.got)} xu.</p>`:''}`
    :`<h3>Chưa đeo cánh</h3><p class="small">Mỗi đôi mua về ra hạng D hoặc C, ghép ba đôi ở ⚒️ Cường hóa để lên hạng. Hạng càng cao càng đẹp và càng được nhiều.</p>`;
  const cap=Math.max(1,Math.min(c.qty_max||1,c.own_max-own.length));
  const forge=own.length>=3?`<p class="jr-card as-for">⚒️ <span class="grow">Ghép ba đôi để lên hạng${wingQuick(api)?', có thể ghép ngay':''}.</span>${btn('⚒️ Cường hóa','jrForge',{tab:'wing'},'small')}</p>`:'';
  const tiles=own.length?`<section class="jr-card wg-own"><div class="as-mine-head"><b>🪽 Tủ cánh</b><small class="muted">${own.length}/${c.own_max}</small></div>
    <ul class="wg-grid">${sortWings(own).map(x=>wingTile(api,w,x)).join('')}</ul></section>`:'';
  const shelf=c.styles.map(x=>`<article class="jr-card as-kind wg-style"><button type="button" class="as-kind-art" data-action="jrAsWingTry" data-k="${esc(x.id)}" aria-label="Thử ${esc(x.name)} trước gương">${wingIcon({k:x.id,r:0},84)}</button>
      <div class="as-kind-text"><h3>${esc(x.emoji)} ${esc(x.name)}</h3><p class="small">${esc(x.desc)}</p><p class="as-hint">Ra hạng D hoặc C ngẫu nhiên</p>
      ${qtyRow(api,'jrAsWingQty',{k:x.id},wq(st,x.id,cap),cap,x.price)}
      ${btn(`Mua${wq(st,x.id,cap)>1?` ×${wq(st,x.id,cap)}`:''} · ${fmt(x.price*wq(st,x.id,cap))} xu`,'jrAsWingBuy',{k:x.id},'primary small',busy||own.length>=c.own_max)}</div></article>`).join('');
  return `${wingReveal(api,st)}<section class="jr-card wd-stage"><div class="wd-mirror">${mirror}</div><div class="wd-side">${side}</div></section>${forge}${tiles}<div class="as-shelf">${shelf}</div>${wingTable(c)}`;
}
/** ⚒️ Cường hóa's 🪽 shelf: ⚡ Cường hóa nhanh, the wings to pick, the fusion picked, what each tier gives. */
function wingForge(env,st){
  const {api}=env,c=WC(api);if(!c)return `<p class="muted">Cánh đang về hàng, lát nữa quay lại nhé.</p>`;
  const w=wingsOf(api)||{},own=ownWings(api);
  st.wfz=(st.wfz||[]).filter(id=>own.some(x=>x.id===id));   // ui.as may come from jrAccShop (v4/journey.js) without it
  if(!own.length)return `${wingReveal(api,st)}<section class="jr-card fg-empty"><h3>🪽 Chưa có đôi cánh nào</h3><p class="small">Mua cánh ở Cửa hàng (ra hạng D hoặc C), có ba đôi là ghép lên hạng được.</p>${btn('🛍️ Mua cánh','jrAccShop',{tab:'wing'},'primary small')}</section>${wingTable(c)}`;
  const q=wingQuick(api),f=q&&wingFuseOf(api,q);
  const quick=`<section class="jr-card fg-quick">${btn('⚡ Cường hóa nhanh','jrAsWingQuick',{},'primary',busy||!q)}<small>${q?`👑 ${esc(wName(api,q[0]))} + ${esc(wName(api,q[1]))} + ${esc(wName(api,q[2]))} → hạng ${esc(tierName(f.to))} · ${fmt(f.fee)} xu`:'Cần ba đôi cùng hạng để lên hạng.'}</small></section>`;
  // owner 23/10 "hiện tại khó ghép quá": the wings by tier, how many, and whether that tier can go up now
  const top=WING_TIERS.length-1,tiers=[...new Set(own.map(x=>x.r))].sort((a,b)=>b-a);
  const groups=tiers.map(r=>{const g=sortWings(own.filter(x=>x.r===r)),n=g.length;
    const can=r>=top?'cao nhất rồi':n>=3?`ghép được ${Math.floor(n/3)} lần`:`thiếu ${3-n} đôi để ghép`;
    return `<div class="wg-group"><p class="wg-group-head">${badge(r)} <b>Hạng ${esc(tierName(r))}</b> · ${n} đôi <small class="muted">· ${can}</small></p>
      <ul class="wg-grid">${g.map(x=>wingTile(api,w,x,st.wfz.indexOf(x.id),true)).join('')}</ul></div>`;}).join('');
  return `${wingReveal(api,st)}${quick}${fusePanel(api,st,own)}<section class="jr-card wg-own"><div class="as-mine-head"><b>🪽 Tự chọn ba đôi</b><small class="muted">${own.length}/${c.own_max}</small></div>
    ${groups}</section>
    <p class="wd-note as-foot">🛍️ Thêm cánh: ${btn('Cửa hàng','jrAccShop',{tab:'wing'},'ghost small')}</p>${wingTable(c)}`;
}

const wq=(st,k,cap)=>Math.max(1,Math.min(st.wq?.[k]||1,cap));

/* ---- 🏠 Nhà & xe: the other things bought in the game, each in its own screen (a card that opens it) ---- */
const MORE=[['garage','🚗','Xe & phương tiện','Xe máy, ô tô, du thuyền, máy bay riêng, biển số.'],['gadgets','📱','Điện thoại & đồ công nghệ','Điện thoại, máy ảnh, đồng hồ…'],
  ['jrEnterHome','🛋️','Đồ trong nhà','Nội thất, trang trí, sửa chữa nhà.'],['spendStyle','🎨','Phong cách','Màu tên của bạn trong tuần.'],
  ['lux','💎','Mua sắm cao cấp','Du lịch, đồ sưu tầm, dinh thự, tiệc…'],['auction','🔨','Nhà đấu giá','Đồ độc bản, biển số đẹp.']];
const moreList=api=>MORE.filter(([a])=>townServiceAvailable(a,api.state,api.content,{}));
function moreShelf(env){
  const list=moreList(env.api);
  return `<p class="wd-note">Những món này có quầy riêng: chạm để tới đó.</p><div class="as-shelf">${list.map(([a,e,name,desc])=>`<button type="button" class="jr-card as-kind as-more" data-action="${a}"><span class="as-kind-art" aria-hidden="true">${e}</span><span class="as-kind-text"><b>${esc(name)}</b><small>${esc(desc)}</small></span></button>`).join('')}</div>`;
}

/* ---- the sheet ---- */
const GROUPS=[['me','👤','Cho bạn'],['pet','🐾','Thú cưng'],['more','🏠','Nhà & xe']];
const groupOf=tab=>PET.some(x=>x[0]===tab)?'pet':tab==='more'?'more':'me';
function head(api,eyebrow,title){
  return `<header class="sheet-head jr-head"><button type="button" class="btn ghost small jr-back" data-action="jrView" data-view="home" aria-label="Quay lại">${icon('back',18)}</button><div class="grow"><span class="eyebrow">${eyebrow}</span><h2>${title}</h2></div></header>`;
}
export function accShopView(env){
  const {api,ui}=env,c=W(api),st=S(ui);
  const top=head(api,'MUA SẮM',`🛍️ ${SHOP_NAME}`);
  if(!c||!api.state.journey?.gender)return top+`<div class="sheet-body jr-body"><p class="muted">Cửa hàng đang bày hàng, lát nữa quay lại nhé.</p></div>`;
  const by={me:meTabs(c),pet:petTabs(api),more:moreList(api).length?[['more','🔗','Nơi mua khác']]:[]},all=[...by.me,...by.pet,...by.more];
  if(!all.some(x=>x[0]===st.tab))st.tab='acc';
  const cur=groupOf(st.tab),n=waiting(api),shown=GROUPS.filter(([g])=>by[g].length);
  const groups=shown.length>1?`<nav class="as-groups" role="tablist" aria-label="Nhóm hàng" style="--n:${shown.length}">${shown.map(([g,e,label])=>{const on=g===cur;
    return `<button type="button" role="tab" class="as-group${on?' active':''}" aria-selected="${on}" data-action="jrAsGroup" data-group="${g}"><span aria-hidden="true">${e}</span>${label}${g==='me'&&n&&!on?`<i class="as-badge" aria-label="${n} món quà đang chờ">${n}</i>`:''}</button>`;}).join('')}</nav>`:'';
  const tabs=by[cur].length>1?`<nav class="wd-tabs" role="tablist" aria-label="Quầy hàng">${by[cur].map(([id,e,label])=>`<button type="button" role="tab" class="wd-tab${st.tab===id?' active':''}" aria-selected="${st.tab===id}" data-action="jrAsTab" data-tab="${id}"><span aria-hidden="true">${e}</span>${label}${id==='pair'&&n?`<i class="as-badge" aria-label="${n} món quà đang chờ">${n}</i>`:''}</button>`).join('')}</nav>`:'';
  const body=cur==='pet'?petShelf(env,st):cur==='more'?moreShelf(env):st.tab==='acc'?accShelf(env,st):st.tab==='wing'?wingShelf(env,st):st.tab==='wear'?wearShelf(env,st):pairShelf(env,st);
  return top+`<div class="sheet-body jr-body wd as">
    ${groups}${tabs}
    ${body}
  </div>`;
}

/* ---- ⚒️ Cường hóa (owner 23/10): every "ghép / nâng hạng" of the game in one place, each with ⚡ Cường hóa nhanh. The
 * 🐾 shelves are v4/pets.js (lab, ward, gear bag) drawn here; the pets' dialog keeps its own tabs too. ---- */
const FORGE=[['wing','🪽','Cánh'],['plab','🧬','Ghép thú','lab'],['pward','👗','Đồ thú cưng','ward'],['pgear','🧰','Linh kiện thú','gearup']];
export function forgeTabs(api){
  const c=W(api),J=api.state.journey,pc=api.content.journey?.pets,pets=!!(J?.story&&J.pets&&pc);
  return FORGE.filter(([id])=>id==='wing'?!!(c?.wings&&J?.gender):!pets?false:id==='pward'?!!pc.wardrobe:!!pc.tiers).map(x=>x[0]);
}
/** What the player owns to ghép, by kind: a short line each, and whether ⚡ finds a set (the pets' from v4/pets.js). */
function forgeCounts(env){
  const {api}=env,own=ownWings(api),out={};
  const byTier=[...own.reduce((m,x)=>m.set(x.r,(m.get(x.r)||0)+1),new Map())].sort((a,b)=>b[0]-a[0]);
  out.wing={line:own.length?`${own.length} đôi · ${byTier.map(([r,k])=>`${tierName(r)}×${k}`).join(' ')}`:'Chưa có đôi nào',quick:!!wingQuick(api)};
  const pc=forgeTabs(api).some(t=>t[0]==='p')&&PT.use()?.petForgeCounts?.(env);
  if(pc){
    out.plab={line:pc.lab.n?`${pc.lab.n} bé · ${pc.lab.ranks.map(([r,k])=>`${r}×${k}`).join(' ')}`:'Chưa có bé nào',quick:pc.lab.quick};
    out.pward={line:pc.ward.n?`${pc.ward.n} món · ${pc.ward.sets} bộ ghép được`:'Chưa có món nào',quick:pc.ward.quick};
    out.pgear={line:pc.gear.n?`${pc.gear.n} món · ${pc.gear.up} lên hạng được`:'Chưa có món nào',quick:pc.gear.quick};
  }
  return out;
}
export function forgeView(env){
  const {api,ui}=env,st=S(ui),ok=forgeTabs(api);
  const top=head(api,'NÂNG CẤP','⚒️ Cường hóa');
  if(!ok.length)return top+`<div class="sheet-body jr-body"><p class="muted">Chưa có gì để cường hóa. Có cánh hay thú cưng rồi quay lại nhé.</p></div>`;
  if(!ok.includes(st.ftab))st.ftab=ok[0];
  const n=forgeCounts(env),tabs=FORGE.filter(x=>ok.includes(x[0])).map(([id,e,label])=>{const k=n[id];
    return `<button type="button" role="tab" class="fg-kind${st.ftab===id?' active':''}" aria-selected="${st.ftab===id}" data-action="jrAsForgeTab" data-tab="${id}"><span class="fg-kind-e" aria-hidden="true">${e}</span><b>${label}</b><small>${k?esc(k.line):'…'}</small>${k?.quick?'<i class="fg-ready" title="Cường hóa nhanh được">⚡</i>':''}</button>`;}).join('');
  const part=FORGE.find(x=>x[0]===st.ftab)[3];
  const body=part?(PT.use()?.petEmbedHTML(env,part)||skeleton()):wingForge(env,st);
  return top+`<div class="sheet-body jr-body wd as fg">
    <p class="wd-note fg-intro">⚡ Cường hóa nhanh tự chọn bộ hợp lệ, hỏi lại đúng món dùng và phí trước khi làm.</p>
    <nav class="fg-kinds" role="tablist" aria-label="Đồ ghép được của bạn">${tabs}</nav>
    ${body}
  </div>`;
}

async function post(env,op,body){
  const {api,toast}=env;
  busy=true;env.renderSheet(false);
  try{
    const d=await api.json(`/api/marriage/${op}`,{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify(body)});
    adopt(api,d,()=>env.renderMain?.());
    if(d?.message)toast(d.message,'good');
    return d;
  }catch(e){toast(e.message||'Chưa làm được. Thử lại nhé.',true);return null;}
  finally{busy=false;env.renderSheet(false);}
}

export async function accShopAction(action,data,el,env){
  const {api,ui,cmd,renderSheet,confirmAction}=env,st=S(ui),c=W(api);
  if(!c)return false;
  switch(action){
    case'jrAsTab':st.tab=shopTabs(api).includes(data.tab)?data.tab:'acc';(st.last??={})[groupOf(st.tab)]=st.tab;renderSheet(false);return true;
    case'jrAsGroup':{const ok=shopTabs(api),g=GROUPS.some(x=>x[0]===data.group)?data.group:'me',last=st.last?.[g],list=ok.filter(id=>groupOf(id)===g);
      st.tab=list.includes(last)?last:list[0]||'acc';renderSheet(false);return true;}
    case'jrAsForgeTab':st.ftab=forgeTabs(api).includes(data.tab)?data.tab:'wing';renderSheet(false);return true;
    // 👕 Quần áo (game/wardrobe.py jr_wd_buy / jr_wd_wear, as in Tủ đồ)
    case'jrAsClSlot':st.cslot=CL.includes(data.slot)?data.slot:'top';renderSheet(false);return true;
    case'jrAsClTry':{const it=data.item&&wdItem(api,data.item);
      if(st.multi&&it&&CL.includes(it.slot)&&wdStatus(api,it)?.buy){cartToggle(st,it.id);st.cdraft=inCart(st,it.id)?it.id:null;renderSheet(false);return true;}
      st.cdraft=it&&CL.includes(it.slot)&&st.cdraft!==it.id?it.id:null;renderSheet(false);return true;}
    case'jrAsClBuy':{const it=wdItem(api,data.item),stt=it&&wdStatus(api,it);if(!stt?.buy||busy)return true;
      const how=await confirmPurchase(env,{title:`Mua ${it.name}?`,message:`Giá ${fmt(stt.price)} xu${stt.price<it.price?` (giá nhân viên ${c.shop_name}, giá gốc ${fmt(it.price)} xu)`:''}. Mua xong mặc luôn, đổi màu trong Tủ đồ.`,label:`Mua · ${fmt(stt.price)} xu`,cost:stt.price});
      if(!how)return true;
      busy=true;const ok=await cmd('jr_wd_buy',{item:it.id,wear:true,pay:how});busy=false;if(ok)st.cdraft=null;
      renderSheet(false);return true;}
    case'jrAsClOn':{const it=wdItem(api,data.item);if(!it||!CL.includes(it.slot)||wdStatus(api,it)||busy)return true;
      busy=true;const ok=await cmd('jr_wd_wear',{look:{[it.slot]:it.id}});busy=false;if(ok)st.cdraft=null;renderSheet(false);return true;}
    case'jrAsTry':{const it=wdItem(api,data.item);if(!it||it.slot!=='acc')return true;
      if(st.multi&&wdStatus(api,it)?.buy){cartToggle(st,it.id);st.draft=inCart(st,it.id)?it.id:null;renderSheet(false);return true;}
      st.draft=st.draft===it.id?null:it.id;renderSheet(false);return true;}
    // 🧺 several pieces at once (jr_wd_buy items: one price, all or none)
    case'jrAsMulti':if(data.off||st.multi){st.multi=false;st.cart=[];}else{st.multi=true;st.cart=[];}renderSheet(false);return true;
    case'jrAsBuyMany':{const xs=cartOf(api,st);if(!xs.length||busy)return true;
      const sum=xs.reduce((a,it)=>a+wdStatus(api,it).price,0),slots=xs.map(it=>it.slot),wear=new Set(slots).size===slots.length;
      const how=await confirmPurchase(env,{title:`Mua ${xs.length} món?`,message:`${xs.map(it=>`${it.name} (${fmt(wdStatus(api,it).price)} xu)`).join(', ')}. Tổng ${fmt(sum)} xu, trả một lần, mua đủ cả hoặc không món nào. ${wear?'Mua xong mặc luôn.':'Mua xong cất vào tủ (có món cùng chỗ).'}`,label:`Mua ${xs.length} món · ${fmt(sum)} xu`,cost:sum});
      if(!how)return true;
      busy=true;const ok=await cmd('jr_wd_buy',{items:xs.map(it=>it.id),wear,pay:how});busy=false;
      if(ok){st.cart=[];st.multi=false;st.draft=null;st.cdraft=null;}renderSheet(false);return true;}
    case'jrAsPairQty':{const n=Math.max(1,Math.min(Number(data.n)||1,10));(st.pq??={})[data.kind]=n;renderSheet(false);return true;}
    case'jrAsWingQty':{const n=Math.max(1,Math.min(Number(data.n)||1,WC(api)?.qty_max||1));(st.wq??={})[data.k]=n;renderSheet(false);return true;}
    case'jrAsReset':st.draft=null;renderSheet(false);return true;
    case'jrAsBuy':{const it=wdItem(api,data.item),stt=it&&wdStatus(api,it);if(!stt?.buy||busy)return true;
      const how=await confirmPurchase(env,{title:`Mua ${it.name}?`,message:`Giá ${fmt(stt.price)} xu${stt.price<it.price?` (giá nhân viên ${c.shop_name}, giá gốc ${fmt(it.price)} xu)`:''}. Mua xong đeo luôn, đổi màu trong Tủ đồ.`,label:`Mua · ${fmt(stt.price)} xu`,cost:stt.price});
      if(!how)return true;
      if(await cmd('jr_wd_buy',{item:it.id,wear:true,pay:how}))st.draft=null;
      renderSheet(false);return true;}
    case'jrAsWearAcc':{const it=wdItem(api,data.item);if(!it||wdStatus(api,it))return true;
      if(await cmd('jr_wd_wear',{look:{acc:it.id}}))st.draft=null;renderSheet(false);return true;}
    case'jrAsPairBuy':{const k=kindOf(api,data.kind);if(!k||busy)return true;
      const who=st.to&&api.charmView?.friends?.find(f=>f.code===st.to)?.name;
      const v=api.charmView,room=v?Math.max(1,(v.box_max||10)-v.box.length-v.sent.length):1,q=Math.max(1,Math.min(st.pq?.[k.id]||1,room)),sum=k.price*q;
      const how=await confirmPurchase(env,{title:`Mua cặp ${k.name}${q>1?` ×${q}`:''}?`,message:`${k.item}, hai chiếc một cặp. ${q>1?`${q} cặp × ${fmt(k.price)} xu = ${fmt(sum)} xu, trả một lần, mua đủ cả hoặc không cặp nào.`:`Giá ${fmt(k.price)} xu.`} ${who?`Bạn giữ một chiếc, chiếc còn lại gửi tới ${who}${q>1?', các cặp kia nằm trong hộp quà':''}.`:'Bạn giữ một chiếc, tặng chiếc còn lại cho một người bạn.'}`,label:`Mua · ${fmt(sum)} xu`,cost:sum});
      if(!how)return true;
      const to=st.to&&api.charmView?.friends?.find(f=>f.code===st.to);
      // one request id per purchase: a retry pays nothing (game/friend_charms.py _buy)
      const done=await post(env,'charm_buy',{kind:k.id,pay:how,rid:rid(),...(q>1?{qty:q}:{}),...(to?{code:to.code}:{})});
      if(done){if(to)st.to='';if(st.pq)delete st.pq[k.id];}renderSheet(false);return true;}
    case'jrAsTo':st.to=typeof data.code==='string'?data.code:'';renderSheet(false);return true;
    case'jrAsGive':{const sel=document.getElementById(`as-to-${data.id}`),code=sel?.value||st.to;
      if(!code){env.toast('Chọn một người bạn để tặng nhé.','hint');sel?.focus?.();return true;}
      st.to=code;await post(env,'charm_offer',{id:data.id,code});return true;}
    case'jrAsAnswer':{if(data.answer==='decline'&&!await confirmAction('Từ chối món quà?','Món quà sẽ trở về hộp quà của bạn ấy.','Từ chối'))return true;
      await post(env,'charm_respond',{id:data.id,answer:data.answer==='accept'?'accept':'decline'});return true;}
    case'jrAsCancel':await post(env,'charm_cancel',{id:data.id});return true;
    case'jrAsSell':{const b=api.charmView?.box?.find(x=>x.id===data.id),k=b&&kindOf(api,b.kind);if(!b)return true;
      if(!await confirmAction(`Bán lại cặp ${k?.name||''}?`,`Tiệm mua lại ${fmt(b.sell)} xu.`,`Bán · ${fmt(b.sell)} xu`))return true;
      await post(env,'charm_sell',{id:b.id,rid:rid()});return true;}
    case'jrAsWear':{const on=el?.type==='checkbox'?el.checked:!api.charmView?.pairs?.find(p=>p.id===data.id)?.on;
      await post(env,'charm_wear',{id:data.id,on});return true;}
    case'jrAsWearAll':await post(env,'charm_wear',{all:true,on:data.on==='1'});return true;
    // 💞 the relationship with a friend (game/friend_charms.py)
    case'jrAsBond':{const r=relOf(api,data.label);if(!r||busy)return true;await post(env,'charm_bond',{id:data.id,label:r.id});return true;}
    case'jrAsBondAnswer':await post(env,'charm_bond_answer',{id:data.id,answer:data.answer==='accept'?'accept':'decline'});return true;
    case'jrAsBondOff':{if(!await confirmAction('Về lại bạn bè?','Quan hệ đang đặt sẽ bỏ, hai bạn vẫn là bạn bè và vẫn giữ phụ kiện đôi.','Về bạn bè'))return true;
      await post(env,'charm_bond_off',{id:data.id});return true;}
    // 🪽 Cánh (game/wings.py)
    case'jrAsWingTry':st.wtry=data.k&&WC(api)?.styles?.some(x=>x.id===data.k)?(st.wtry===data.k?null:data.k):null;renderSheet(false);return true;
    case'jrAsWingReveal':st.reveal=null;renderSheet(false);return true;
    case'jrAsWingBuy':{const x=styleOf(api,data.k),c2=WC(api);if(!x||busy||!c2)return true;
      const q=wq(st,x.id,Math.max(1,Math.min(c2.qty_max||1,c2.own_max-ownWings(api).length))),sum=x.price*q;
      if(!await confirmAction(`Mua ${x.name}${q>1?` ×${q}`:''}?`,`${q>1?`${q} đôi × ${fmt(x.price)} xu = ${fmt(sum)} xu, trả một lần, mua đủ cả hoặc không đôi nào. Mỗi đôi`:`Giá ${fmt(x.price)} xu. Mở hộp`} ra hạng D hoặc C ngẫu nhiên, ghép ba đôi ở ⚒️ Cường hóa để lên hạng.`,`🪽 Mua · ${fmt(sum)} xu`,{cost:sum}))return true;
      // the request id (game/wings.py RQ_KEEP): a retry answers the same wings and pays nothing
      busy=true;const r=await cmd('jr_pet_wing_buy',{style:x.id,...(q>1?{qty:q}:{}),rid:rid().replace(/[^A-Za-z0-9_.:-]/g,'').slice(0,64),confirm:true});busy=false;
      if(r?.wings?.length){st.reveal=r.wings.map(w=>({k:w.k,r:w.r}));st.wtry=null;if(st.wq)delete st.wq[x.id];}renderSheet(false);return true;}
    case'jrAsWingWear':if(busy)return true;busy=true;await cmd('jr_pet_wing_wear',{id:data.id||null});busy=false;renderSheet(false);return true;
    case'jrAsWingDrop':{const x=wingsOf(api)?.own?.find(o=>o.id===data.id);if(!x||busy)return true;
      if(!await confirmAction(`Bỏ ${wName(api,x)}?`,'Đôi cánh này sẽ mất hẳn, không lấy lại được.','Bỏ cánh'))return true;
      busy=true;await cmd('jr_pet_wing_drop',{id:x.id,confirm:true});busy=false;st.wfz=st.wfz.filter(id=>id!==x.id);renderSheet(false);return true;}
    case'jrAsWingPick':{if(!data.id){st.wfz=[];renderSheet(false);return true;}
      const i=st.wfz.indexOf(data.id);if(i>=0)st.wfz.splice(i,1);else if(st.wfz.length<3)st.wfz.push(data.id);else st.wfz=[...st.wfz.slice(0,2),data.id];renderSheet(false);return true;}
    case'jrAsWingQuick':case'jrAsWingFuse':{if(busy||!WC(api))return true;
      const own=ownWings(api),xs=action==='jrAsWingQuick'?wingQuick(api):st.wfz.map(id=>own.find(x=>x.id===id)).filter(Boolean);if(xs?.length!==3)return true;
      if(action==='jrAsWingQuick'){st.wfz=xs.map(x=>x.id);renderSheet(false);}   // ⚡ the pick shows in the panel too
      const f=wingFuseOf(api,xs),[m,a,b]=xs,top=WING_TIERS.length-1;if(m.r>=top)return true;
      const what=`Dùng: ${wName(api,m)} (cánh chính, giữ kiểu${m.id===wingsOf(api)?.on?', đang đeo':''}), ${wName(api,a)}, ${wName(api,b)}.`;
      if(!await confirmAction(action==='jrAsWingQuick'?'⚡ Cường hóa nhanh cánh?':'Ghép ba đôi cánh?',`${what} Thành công: ${styleOf(api,m.k)?.name||'Cánh'} ${f.to>m.r?'lên':'giữ'} hạng ${tierName(f.to)}, hai đôi kia dùng hết. Trượt: ${f.lose?'⚠️ hai đôi kia sẽ mất':'ba đôi vẫn còn'}. Phí ${fmt(f.fee)} xu, thành hay trượt đều mất phí.`,`🧬 Ghép · ${fmt(f.fee)} xu`,{cost:f.fee}))return true;
      busy=true;const r=await cmd('jr_pet_wing_fuse',{wings:xs.map(x=>x.id),main:m.id,confirm:true});busy=false;
      if(r?.fuse){const lost=r.fuse.lost||[];st.wfz=r.fuse.ok?[]:st.wfz.filter(id=>!lost.includes(id));if(r.fuse.ok){const mm=ownWings(api).find(x=>x.id===r.fuse.main);if(mm)st.reveal=[{k:mm.k,r:mm.r}];}}
      renderSheet(false);return true;}
  }
  return false;
}
