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
import {buyPayment,askBuy} from './payment.js';
import {lookOf,figureSVG,portrait,pairIcon,myPairs,wingIcon,wingOfState,WING_TIERS,WING_TIER_COLOR} from './look.js';
import {kinds,kindOf,adopt,refreshCharms,pairRows,waiting,relOf,SHOP_NAME} from './charms.js';
import {wdStatus,wdItem,wdThumb} from './wardrobe.js';
import {lazy,skeleton} from '../lazy.js';
import {townServiceAvailable} from '../isometric/town-utilities.js';   // 🏠 which other shops this save has (the menu's gates)
// 🐾 the pet shelves (v4/pets.js), loaded the first time that group opens
const PT=lazy(()=>import('./pets.js'),{css:['/css/pets.css']});
// 🛍️ the shop's sheet (one row of tabs, a grid of cards, the detail sheet): v4/shop-shelves.js; its commands stay here
import {shopAction,wingsReady,focusDetail} from './shop-shelves.js';
export {accShopView} from './shop-shelves.js';

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
const inCart=(st,id)=>(st.cart||[]).includes(id);
const cartLook=(api,st)=>Object.fromEntries(cartOf(api,st).map(it=>[it.slot,it.id]));

/* ---- 👕 Trang phục: the racks (game/wardrobe.py slots) ---- */
const CL=['top','bottom','shoes','hair'];
const CL_EMOJI={top:'👕',bottom:'👖',shoes:'👟',hair:'💇'};

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
/** For 🛍️ Cửa hàng's sheet (v4/shop-shelves.js). */
export {S,PT,PET,W,btn,attrs,fmt,busy,qtyRow,cartBar,cartToggle,inCart,cartLook,CL,CL_EMOJI,WC,wingsOf,ownWings,styleOf,wName,badge,wingTile,sortWings,wingReveal,wingTable,wq,moreList,petTabs};

/* ---- 🏠 Nhà & xe: the other things bought in the game, each in its own screen (a card that opens it) ---- */
const MORE=[['garage','🚗','Xe & phương tiện','Xe máy, ô tô, du thuyền, máy bay riêng, biển số.'],['gadgets','📱','Điện thoại & đồ công nghệ','Điện thoại, máy ảnh, đồng hồ…'],
  ['jrEnterHome','🛋️','Đồ trong nhà','Nội thất, trang trí, sửa chữa nhà.'],['spendStyle','🎨','Phong cách','Màu tên của bạn trong tuần.'],
  ['lux','💎','Mua sắm cao cấp','Du lịch, đồ sưu tầm, dinh thự, tiệc…'],['auction','🔨','Nhà đấu giá','Đồ độc bản, biển số đẹp.']];
const moreList=api=>MORE.filter(([a])=>townServiceAvailable(a,api.state,api.content,{}));
/* ---- the sheet ---- */
function head(api,eyebrow,title){
  return `<header class="sheet-head jr-head"><button type="button" class="btn ghost small jr-back" data-action="jrView" data-view="home" aria-label="Quay lại">${icon('back',18)}</button><div class="grow"><span class="eyebrow">${eyebrow}</span><h2>${title}</h2></div></header>`;
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
  busy=true;env.renderSheet();
  try{
    const d=await api.json(`/api/marriage/${op}`,{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify(body)});
    adopt(api,d,()=>env.renderMain?.());
    if(d?.message)toast(d.message,'good');
    return d;
  }catch(e){toast(e.message||'Chưa làm được. Thử lại nhé.',true);return null;}
  finally{busy=false;env.renderSheet();}
}

/** A purchase done (owner 23/10 "gọn"): a short toast of what came; ⚒️ Đi cường hóa when it can now be ghép. */
const got=(env,text,forge='')=>env.toast(text,'good',forge&&env.act?{action:{label:'⚒️ Đi cường hóa',run:()=>env.act('jrForge',{tab:forge})}}:{});

export async function accShopAction(action,data,el,env){
  const {api,ui,cmd,renderSheet,confirmAction}=env,st=S(ui),c=W(api);
  if(!c)return false;
  if(await shopAction(action,data,el,env))return true;   // tabs, filters, the detail sheet (v4/shop-shelves.js)
  switch(action){
    case'jrAsForgeTab':st.ftab=forgeTabs(api).includes(data.tab)?data.tab:'wing';renderSheet(false);return true;
    // 👕 Quần áo (game/wardrobe.py jr_wd_buy / jr_wd_wear, as in Tủ đồ)
    case'jrAsClSlot':st.cslot=CL.includes(data.slot)?data.slot:'top';renderSheet();return true;
    case'jrAsClTry':{const it=data.item&&wdItem(api,data.item);
      if(st.multi&&it&&CL.includes(it.slot)&&wdStatus(api,it)?.buy){cartToggle(st,it.id);st.cdraft=inCart(st,it.id)?it.id:null;renderSheet();return true;}
      st.cdraft=it&&CL.includes(it.slot)&&st.cdraft!==it.id?it.id:null;renderSheet();if(st.cdraft)focusDetail();return true;}
    case'jrAsClBuy':{const it=wdItem(api,data.item),stt=it&&wdStatus(api,it);if(!stt?.buy||busy)return true;
      const how=await buyPayment(env,{title:`Mua ${it.name}?`,message:`Giá ${fmt(stt.price)} xu${stt.price<it.price?` (giá nhân viên ${c.shop_name}, giá gốc ${fmt(it.price)} xu)`:''}. Mua xong mặc luôn, đổi màu trong Tủ đồ.`,label:`Mua · ${fmt(stt.price)} xu`,cost:stt.price});
      if(!how)return true;
      busy=true;renderSheet();const ok=await cmd('jr_wd_buy',{item:it.id,wear:true,pay:how},{quiet:true});busy=false;if(ok){st.cdraft=null;got(env,`👕 +1 ${it.name} · đã mặc`);}
      renderSheet();return true;}
    case'jrAsClOn':{const it=wdItem(api,data.item);if(!it||!CL.includes(it.slot)||wdStatus(api,it)||busy)return true;
      busy=true;const ok=await cmd('jr_wd_wear',{look:{[it.slot]:it.id}});busy=false;if(ok)st.cdraft=null;renderSheet();return true;}
    case'jrAsTry':{const it=wdItem(api,data.item);if(!it||it.slot!=='acc')return true;
      if(st.multi&&wdStatus(api,it)?.buy){cartToggle(st,it.id);st.draft=inCart(st,it.id)?it.id:null;renderSheet();return true;}
      st.draft=st.draft===it.id?null:it.id;renderSheet();if(st.draft)focusDetail();return true;}
    // 🧺 several pieces at once (jr_wd_buy items: one price, all or none)
    case'jrAsMulti':if(data.off||st.multi){st.multi=false;st.cart=[];}else{st.multi=true;st.cart=[];}renderSheet();return true;
    case'jrAsBuyMany':{const xs=cartOf(api,st);if(!xs.length||busy)return true;
      const sum=xs.reduce((a,it)=>a+wdStatus(api,it).price,0),slots=xs.map(it=>it.slot),wear=new Set(slots).size===slots.length;
      const how=await buyPayment(env,{title:`Mua ${xs.length} món?`,message:`${xs.map(it=>`${it.name} (${fmt(wdStatus(api,it).price)} xu)`).join(', ')}. Tổng ${fmt(sum)} xu, trả một lần, mua đủ cả hoặc không món nào. ${wear?'Mua xong mặc luôn.':'Mua xong cất vào tủ (có món cùng chỗ).'}`,label:`Mua ${xs.length} món · ${fmt(sum)} xu`,cost:sum});
      if(!how)return true;
      busy=true;renderSheet();const ok=await cmd('jr_wd_buy',{items:xs.map(it=>it.id),wear,pay:how},{quiet:true});busy=false;
      if(ok){st.cart=[];st.multi=false;st.draft=null;st.cdraft=null;got(env,`🧺 +${xs.length} món: ${xs.map(it=>it.name).join(', ')}`);}renderSheet();return true;}
    case'jrAsPairQty':{const n=Math.max(1,Math.min(Number(data.n)||1,10));(st.pq??={})[data.kind]=n;renderSheet();return true;}
    case'jrAsWingQty':{const n=Math.max(1,Math.min(Number(data.n)||1,WC(api)?.qty_max||1));(st.wq??={})[data.k]=n;renderSheet();return true;}
    case'jrAsBuy':{const it=wdItem(api,data.item),stt=it&&wdStatus(api,it);if(!stt?.buy||busy)return true;
      const how=await buyPayment(env,{title:`Mua ${it.name}?`,message:`Giá ${fmt(stt.price)} xu${stt.price<it.price?` (giá nhân viên ${c.shop_name}, giá gốc ${fmt(it.price)} xu)`:''}. Mua xong đeo luôn, đổi màu trong Tủ đồ.`,label:`Mua · ${fmt(stt.price)} xu`,cost:stt.price});
      if(!how)return true;
      busy=true;renderSheet();const ok=await cmd('jr_wd_buy',{item:it.id,wear:true,pay:how},{quiet:true});busy=false;if(ok){st.draft=null;got(env,`🎀 +1 ${it.name} · đã đeo`);}
      renderSheet();return true;}
    case'jrAsWearAcc':{const it=wdItem(api,data.item);if(!it||wdStatus(api,it))return true;
      if(await cmd('jr_wd_wear',{look:{acc:it.id}}))st.draft=null;renderSheet();return true;}
    case'jrAsPairBuy':{const k=kindOf(api,data.kind);if(!k||busy)return true;
      const who=st.to&&api.charmView?.friends?.find(f=>f.code===st.to)?.name;
      const v=api.charmView,room=v?Math.max(1,(v.box_max||10)-v.box.length-v.sent.length):1,q=Math.max(1,Math.min(st.pq?.[k.id]||1,room)),sum=k.price*q;
      const how=await buyPayment(env,{title:`Mua cặp ${k.name}${q>1?` ×${q}`:''}?`,message:`${k.item}, hai chiếc một cặp. ${q>1?`${q} cặp × ${fmt(k.price)} xu = ${fmt(sum)} xu, trả một lần, mua đủ cả hoặc không cặp nào.`:`Giá ${fmt(k.price)} xu.`} ${who?`Bạn giữ một chiếc, chiếc còn lại gửi tới ${who}${q>1?', các cặp kia nằm trong hộp quà':''}.`:'Bạn giữ một chiếc, tặng chiếc còn lại cho một người bạn.'}`,label:`Mua · ${fmt(sum)} xu`,cost:sum});
      if(!how)return true;
      const to=st.to&&api.charmView?.friends?.find(f=>f.code===st.to);
      // one request id per purchase: a retry pays nothing (game/friend_charms.py _buy)
      const done=await post(env,'charm_buy',{kind:k.id,pay:how,rid:rid(),...(q>1?{qty:q}:{}),...(to?{code:to.code}:{})});
      if(done){if(to)st.to='';if(st.pq)delete st.pq[k.id];st.psel=null;}renderSheet();return true;}
    case'jrAsTo':st.to=typeof data.code==='string'?data.code:'';renderSheet();return true;
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
    case'jrAsWingTry':st.wtry=data.k&&WC(api)?.styles?.some(x=>x.id===data.k)?(st.wtry===data.k?null:data.k):null;st.reveal=null;renderSheet();if(st.wtry)focusDetail();return true;
    case'jrAsWingReveal':st.reveal=null;renderSheet();return true;
    case'jrAsWingBuy':{const x=styleOf(api,data.k),c2=WC(api);if(!x||busy||!c2)return true;
      const q=wq(st,x.id,Math.max(1,Math.min(c2.qty_max||1,c2.own_max-ownWings(api).length))),sum=x.price*q;
      if(askBuy(api.state.journey,sum)&&!await confirmAction(`Mua ${x.name}${q>1?` ×${q}`:''}?`,`${q>1?`${q} đôi × ${fmt(x.price)} xu = ${fmt(sum)} xu, trả một lần, mua đủ cả hoặc không đôi nào. Mỗi đôi`:`Giá ${fmt(x.price)} xu. Mở hộp`} ra hạng D hoặc C ngẫu nhiên, ghép ba đôi ở ⚒️ Cường hóa để lên hạng.`,`🪽 Mua · ${fmt(sum)} xu`,{cost:sum}))return true;
      // the request id (game/wings.py RQ_KEEP): a retry answers the same wings and pays nothing
      busy=true;renderSheet();const r=await cmd('jr_pet_wing_buy',{style:x.id,...(q>1?{qty:q}:{}),rid:rid().replace(/[^A-Za-z0-9_.:-]/g,'').slice(0,64),confirm:true},{quiet:true});busy=false;
      // the detail stays open on this style with the reveal; ⚒️ when three of a tier can go up now (owner 23/10)
      if(r?.wings?.length){st.reveal=r.wings.map(w=>({k:w.k,r:w.r}));st.wtry=x.id;if(st.wq)delete st.wq[x.id];got(env,`🪽 +${r.wings.length} ${x.name}`,wingsReady(api)&&'wing');}renderSheet();return true;}
    case'jrAsWingWear':if(busy)return true;busy=true;await cmd('jr_pet_wing_wear',{id:data.id||null});busy=false;renderSheet();return true;
    case'jrAsWingDrop':{const x=wingsOf(api)?.own?.find(o=>o.id===data.id);if(!x||busy)return true;
      if(!await confirmAction(`Bỏ ${wName(api,x)}?`,'Đôi cánh này sẽ mất hẳn, không lấy lại được.','Bỏ cánh'))return true;
      busy=true;await cmd('jr_pet_wing_drop',{id:x.id,confirm:true});busy=false;st.wfz=st.wfz.filter(id=>id!==x.id);renderSheet();return true;}
    case'jrAsWingPick':{if(!data.id){st.wfz=[];renderSheet();return true;}
      const i=st.wfz.indexOf(data.id);if(i>=0)st.wfz.splice(i,1);else if(st.wfz.length<3)st.wfz.push(data.id);else st.wfz=[...st.wfz.slice(0,2),data.id];renderSheet();return true;}
    case'jrAsWingQuick':case'jrAsWingFuse':{if(busy||!WC(api))return true;
      const own=ownWings(api),xs=action==='jrAsWingQuick'?wingQuick(api):st.wfz.map(id=>own.find(x=>x.id===id)).filter(Boolean);if(xs?.length!==3)return true;
      if(action==='jrAsWingQuick'){st.wfz=xs.map(x=>x.id);renderSheet();}   // ⚡ the pick shows in the panel too
      const f=wingFuseOf(api,xs),[m,a,b]=xs,top=WING_TIERS.length-1;if(m.r>=top)return true;
      const what=`Dùng: ${wName(api,m)} (cánh chính, giữ kiểu${m.id===wingsOf(api)?.on?', đang đeo':''}), ${wName(api,a)}, ${wName(api,b)}.`;
      if(!await confirmAction(action==='jrAsWingQuick'?'⚡ Cường hóa nhanh cánh?':'Ghép ba đôi cánh?',`${what} Thành công: ${styleOf(api,m.k)?.name||'Cánh'} ${f.to>m.r?'lên':'giữ'} hạng ${tierName(f.to)}, hai đôi kia dùng hết. Trượt: ${f.lose?'⚠️ hai đôi kia sẽ mất':'ba đôi vẫn còn'}. Phí ${fmt(f.fee)} xu, thành hay trượt đều mất phí.`,`🧬 Ghép · ${fmt(f.fee)} xu`,{cost:f.fee}))return true;
      busy=true;const r=await cmd('jr_pet_wing_fuse',{wings:xs.map(x=>x.id),main:m.id,confirm:true});busy=false;
      if(r?.fuse){const lost=r.fuse.lost||[];st.wfz=r.fuse.ok?[]:st.wfz.filter(id=>!lost.includes(id));if(r.fuse.ok){const mm=ownWings(api).find(x=>x.id===r.fuse.main);if(mm)st.reveal=[{k:mm.k,r:mm.r}];}}
      renderSheet();return true;}
  }
  return false;
}
