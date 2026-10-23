/** 🛍️ Cửa hàng (owner 23/10: "với bán đồ này đưa ra 1 cái gọi là shop riêng đi, xong thú cưng hay người gì trong đó cả",
 * "cửa hàng hoặc shop đều là 1 đó nhé, mua gì nằm đó hết cho dễ"): one place to buy, its own entry in the menu (app.js,
 * beside the hubs) and in the new map's Tiện ích (isometric-shell.js). Three groups of shelves: 👤 Cho bạn (🎀 Phụ kiện,
 * 🤝 Phụ kiện đôi, 🪽 Cánh, 👕 Trang phục), 🐾 Thú cưng (🐶 Mua bé, 👗 Đồ cho bé, 🪽 Cánh cho bé, 🎾 Đồ chơi, 🧰 Linh kiện:
 * v4/pets.js petEmbedHTML draws its own shelves here, same picks and jr_pet_* commands; its dialog keeps selling too) and
 * 🏠 Nhà & xe (cards to the screens that sell the rest: garage, gadgets, home, lux…). 👕 Trang phục: the wardrobe's pieces
 * with a price, tried on the mirror and bought with jr_wd_buy; Tủ đồ (v4/wardrobe.js) is for wearing, its buy buttons
 * open this shelf.
 * ⚒️ Cường hóa (forgeView, jrView 'forge', owner 23/10): every ghép / nâng hạng in one place (🪽 ghép cánh, 🧬 ghép thú,
 * 👗 ghép đồ thú, 🧰 cường hóa & lên hạng linh kiện), each with ⚡ Cường hóa nhanh (owner 23/10: "cường hóa nhanh sẽ tự
 * ghép mà cường hóa chứ sao lại cường hóa từng lần", "nó giống ghép tự động của áo quần ấy"): a card like 🤖 Ghép tự động
 * of the pets' clothes (which ones, up to which rank, the most to spend), one question saying what a miss may lose, ONE
 * command that fuses again and again on the server (🪽 jr_pet_wing_fuse_auto here, the pets' in v4/pets.js autoCard),
 * then its summary; Tự chọn stays below. A redraw keeps the scroll (env.renderSheet(), owner 23/10: no jump).
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
 *   every tile, what it adds (tiền kiếm được, 💪 lực chiến thú) under the mirror. */
import {icon,escapeHTML as esc} from '../icons.js';
import {shortNum} from './wealth.js';
import {buyPayment,askBuy} from './payment.js';
import {lookOf,figureSVG,portrait,pairIcon,myPairs,wingIcon,wingOfState,WING_TIERS,WING_TIER_COLOR} from './look.js';
import {kinds,kindOf,adopt,refreshCharms,pairRows,waiting,relOf,SHOP_NAME} from './charms.js';
import {wdStatus,wdItem,wdThumb} from './wardrobe.js';
import {lazy,skeleton} from '../lazy.js';
import {qtyBox,QTY,afterTap} from '../qty-input.js';
import {noAsk,setNoAsk} from './no-ask.js';   // ☑️ Không hỏi lại (this device, shared with 🛍️'s buy buttons)
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
  return `<ul class="wg-perks"><li>💰 +${c.earn[r]}% tiền kiếm được khi làm việc</li><li>💪 +${c.battle[r]}% lực chiến thú cưng</li></ul>`;}
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
/** ⚡ What jr_pet_wing_fuse_auto finds now, as game/wings.py `sets` sees it: for each style × tier with three wings (of
 * `scope`'s style, or any) whose result is at most `top`, the lowest tier first, then the styles' order: {r, k, set [main,
 * a, b], t sets}. One style a set (owner 23/10: "ghép nhanh thì ghép gì nhận đó thôi k ghép nhanh mấy dòng khác nhé").
 * The main one is the wing worn when it is among them, else the oldest; the two others the oldest, never the wing worn. */
export function wingSets(api,scope='all',top=WING_TIERS.length-1){
  const w=wingsOf(api),T=WING_TIERS.length-1,seq=x=>Number(String(x.id).slice(1))||0,g=new Map(),order=(WC(api)?.styles||[]).map(s=>s.id);
  for(const x of ownWings(api)){if((scope==='all'||x.k===scope)&&x.r<Math.min(top,T)){const key=`${x.r}|${x.k}`;if(!g.has(key))g.set(key,[]);g.get(key).push(x);}}
  const ix=k=>{const i=order.indexOf(k);return i<0?order.length:i;};
  return [...g.values()].filter(xs=>xs.length>=3).sort((a,b)=>a[0].r-b[0].r||ix(a[0].k)-ix(b[0].k)).map(xs=>{
    const main=xs.find(x=>x.id===w?.on)||[...xs].sort((a,b)=>seq(a)-seq(b))[0];
    const rest=xs.filter(x=>x!==main).sort((a,b)=>seq(a)-seq(b));
    return {r:xs[0].r,k:xs[0].k,set:[main,rest[0],rest[1]],t:Math.floor(xs.length/3)};});
}
/** {sets, n sets now, est the first round's fees, min the first fee}. */
export function wingPlan(api,scope='all',top=WING_TIERS.length-1){
  const c=WC(api),sets=wingSets(api,scope,top),fee=r=>Number(c?.fee?.[r])||0;
  return {sets,n:sets.reduce((a,x)=>a+x.t,0),est:sets.reduce((a,x)=>a+x.t*fee(x.r),0),min:sets.length?fee(sets[0].r):0};
}
const wAuto=st=>({scope:st.wascope||'all',top:st.watop||WING_TIERS.length-1});
/** The most to spend: the first round's fees until one is picked, within [the first fee, the money at hand]. */
function wingBudget(api,st,pl){
  if(!pl.n)return 0;const cap=Math.max(pl.min,funds(api));
  return Math.max(pl.min,Math.min(st.wabud||pl.est,cap));
}
const opt=(v,l,on)=>`<option value="${esc(v)}"${on?' selected':''}>${esc(l)}</option>`;
/** ⚡ Cường hóa nhanh for wings: the pickers, what it finds, the budget, the button (one question, one command). */
function wingAuto(env,st){
  const {api}=env,c=WC(api),{scope,top}=wAuto(st),T=WING_TIERS.length-1,max=c.auto_max||50;
  const all=wingPlan(api,'all',top),pl=wingPlan(api,scope,top),b=wingBudget(api,st,pl);
  const per=new Map();for(const x of ownWings(api))per.set(x.k,0);for(const st2 of [...per.keys()])per.set(st2,wingPlan(api,st2,top).n);
  const scopes=opt('all',`Tất cả kiểu (${all.n})`,scope==='all')+(c.styles||[]).filter(x=>per.has(x.id)).map(x=>opt(x.id,`${x.emoji} ${x.name} (${per.get(x.id)})`,scope===x.id)).join('');
  const ranks=WING_TIERS.slice(1).map((r,i)=>opt(i+1,i+1===T?'🌟 Huyền thoại':r,top===i+1)).join('');
  const fields=`<div class="fg-afields"><label class="fg-afield"><span>Kiểu cánh</span><select data-as-sel="wascope" aria-label="Kiểu cánh để ghép">${scopes}</select></label>`
    +`<label class="fg-afield"><span>Ghép tới hạng</span><select data-as-sel="watop" aria-label="Ghép tới hạng">${ranks}</select></label></div>`;
  let body;
  if(!pl.n)body=`<p class="small muted">${top<T&&wingPlan(api,scope).n?`Đã tới hạng ${esc(tierName(top))}: chọn hạng cao hơn để ghép tiếp.`:'Cần ba đôi cùng kiểu, cùng hạng để lên hạng.'}</p>`;
  else{
    const cap=Math.max(pl.min,funds(api)),step=pl.min,lose=top>(c.lose_from??4);
    const quick=[];for(const [n,l] of [[pl.est,'Vòng đầu'],[pl.est*2,'×2'],[pl.est*5,'×5']]){const v=Math.max(pl.min,Math.min(n,cap));if(!quick.some(q=>q[0]===v))quick.push([v,l]);}
    const nb=(m,label,dis,on='')=>`<button type="button" class="as-qty-b${on}" data-action="jrAsWingBud"${attrs({n:m})}${dis?' disabled':''}${label.length<3?` aria-label="${m<b?'Bớt ngân sách':'Thêm ngân sách'}"`:''}>${label}</button>`;
    const tags=pl.sets.map(x=>`<span class="fg-aset">${esc(styleOf(api,x.k)?.emoji||'')}${badge(x.r)} → ${badge(Math.min(x.r+1,T))}${x.t>1?`<small>×${x.t}</small>`:''}</span>`).join('');
    const short=funds(api)<pl.min||(Number(api.state.journey?.wallet)||0)<0;
    body=`<div class="fg-astats"><div><b>${pl.n}</b><small>bộ ba ghép được ngay</small></div><div><b>${fmt(pl.est)}</b><small>xu phí vòng đầu</small></div></div>`
      +`<div class="fg-asets">${tags}</div>`
      +`<div class="as-qty fg-abud" role="group" aria-label="Tiêu tối đa"><span class="fg-abud-l">Tiêu tối đa</span><span class="as-qty-step">${nb(b-step,'−',b-step<pl.min)}`
      +qtyBox({value:b,min:pl.min,max:cap,money:true,label:'Số xu tiêu tối đa',go:`data-action="jrAsWingBud" data-n="${QTY}"`})
      +`${nb(b+step,'+',b+step>cap)}</span><span class="as-qty-chips">${quick.map(([n,l])=>nb(n,l,false,n===b?' on':'')).join('')}</span>`
      +`<small class="as-qty-sum">Dừng trước khi vượt <b>${fmt(b)} xu</b> · trả một lần</small></div>`
      +(lose?`<p class="fg-awarn">⚠️ Từ hạng S trở lên: trượt thì mất hai đôi phụ, cánh chính ở lại.</p>`:'')
      +(short?`<p class="fg-awarn">Chưa đủ xu cho lượt ghép đầu (${fmt(pl.min)} xu).</p>`:'')
      +btn(`⚡ Cường hóa nhanh · tiêu tối đa ${fmt(b)} xu`,'jrAsWingAuto',{},'primary fg-ago',busy||short);
  }
  return `<section class="jr-card fg-quick fg-auto" aria-label="Cường hóa nhanh"><h3>⚡ Cường hóa nhanh</h3>
    ${fields}${body}</section>`;
}
/** The last ⚡ run's summary (game/wings.py _auto `auto`): turns, successes, misses, xu spent, wings used, why it stopped,
 * the wings that went up (the best one shown big). */
function wingResult(api,a){
  const c=WC(api),stop={done:'Hết bộ ba để ghép.',top:'Đã tới hạng đặt.',budget:'Dừng vì chạm số xu đã đặt.',money:'Dừng vì hết tiền.',
    cap:`Đủ ${c?.auto_max||50} lượt một lần, bấm tiếp nếu muốn.`}[a.stop]||'';
  const made=[...(a.made||[])].sort((x,y)=>y.r-x.r),best=made[0];
  return `<section class="jr-card fg-ares" aria-live="polite" aria-label="Kết quả cường hóa nhanh"><div class="fg-ares-h"><h3>⚡ Kết quả cường hóa nhanh</h3>${btn('✕','jrAsWingRes',{},'ghost small')}</div>
    ${best?`<div class="fg-ares-best">${wingIcon(best,96,wName(api,best))}${badge(best.r)}<b>${esc(wName(api,best))}</b></div>`:''}
    <div class="fg-astats four"><div><b>${a.n}</b><small>lượt ghép</small></div><div class="good"><b>${a.ok}</b><small>thành công</small></div><div><b>${a.n-a.ok}</b><small>trượt</small></div><div><b title="${fmt(a.spent)} xu">${shortNum(a.spent)}</b><small>xu đã tiêu</small></div></div>
    <p class="small muted fg-center">Dùng hết ${a.used} đôi · ${esc(stop)}${a.left?` Còn ${a.left} bộ ba.`:''}</p>
    ${made.length?`<h4>✨ Cánh lên hạng</h4><ul class="fg-amade">${made.map(x=>`<li style="--wt:${WING_TIER_COLOR[x.r]}">${wingIcon(x,48)}${badge(x.r)}<small>${esc(styleOf(api,x.k)?.name||'Cánh')}</small></li>`).join('')}</ul>`
      :`<p class="small muted fg-center">💨 Lần này chưa lên hạng đôi nào${a.used?'':', các đôi vẫn còn nguyên'}.</p>`}</section>`;
}
const wingTile=(api,w,x,pick=-1,forge=false)=>{const on=x.id===w.on;
  return `<li class="wg-tile${on?' on':''}${pick>=0?' picked':''}" style="--wt:${WING_TIER_COLOR[x.r]}">${forge?`<button type="button" class="wg-pick" data-action="jrAsWingPick" data-id="${esc(x.id)}" aria-pressed="${pick>=0}" aria-label="${esc(wName(api,x))}${pick===0?', cánh chính':''}${on?', đang đeo':''}">`:`<span class="wg-pick">`}${wingIcon(x,64)}${badge(x.r)}${pick>=0?`<i class="wg-num" aria-hidden="true">${pick+1}</i>`:''}${forge?'</button>':'</span>'}
    <small>${esc(styleOf(api,x.k)?.name||'Cánh')}${forge&&on?' · đang đeo':''}</small>${forge?'':`<span class="as-row-btns">${on?btn('Cất','jrAsWingWear',{id:''},'ghost small',busy):btn('Đeo','jrAsWingWear',{id:x.id},'small',busy)}${btn('Bỏ','jrAsWingDrop',{id:x.id},'ghost small',busy)}</span>`}</li>`;};
const sortWings=own=>[...own].sort((a,b)=>b.r-a.r||String(a.k).localeCompare(b.k));
const wingReveal=(api,st)=>st.reveal?.length?`<section class="jr-card wg-reveal" aria-live="polite"><h3>🎉 ${st.reveal.length>1?'Mở hộp cánh':'Cánh mới'}</h3><div class="wg-reveal-row">${st.reveal.map((x,i)=>`<span class="wg-reveal-item" style="--i:${i}">${wingIcon(x,72,wName(api,x))}${badge(x.r)}</span>`).join('')}</div>${btn('Tuyệt!','jrAsWingReveal',{},'primary small')}</section>`:'';
const wingTable=c=>`<details class="jr-card wg-table"><summary>📈 Hạng cánh được gì</summary><table><thead><tr><th>Hạng</th><th>Tiền kiếm được</th><th>Lực chiến thú</th></tr></thead><tbody>${c.earn.map((e,r)=>`<tr><td>${badge(r)}</td><td>+${e}%</td><td>+${c.battle[r]}%</td></tr>`).join('')}</tbody></table></details><p class="wd-note as-foot">${btn('🏆 Xếp hạng cánh','rank',{board:'wings'},'ghost small')}</p>`;   // 🪽 the Cánh board (game/wing_lb.py)
/** ⚒️ Cường hóa's 🪽 shelf: ⚡ Cường hóa nhanh, the wings to pick, the fusion picked, what each tier gives. */
function wingForge(env,st){
  const {api}=env,c=WC(api);if(!c)return `<p class="muted">Cánh đang về hàng, lát nữa quay lại nhé.</p>`;
  const w=wingsOf(api)||{},own=ownWings(api);
  st.wfz=(st.wfz||[]).filter(id=>own.some(x=>x.id===id));   // ui.as may come from jrAccShop (v4/journey.js) without it
  if(!own.length)return `${wingReveal(api,st)}<section class="jr-card fg-empty"><h3>🪽 Chưa có đôi cánh nào</h3><p class="small">Mua cánh ở Cửa hàng (ra hạng D hoặc C), có ba đôi là ghép lên hạng được.</p>${btn('🛍️ Mua cánh','jrAccShop',{tab:'wing'},'primary small')}</section>${wingTable(c)}`;
  const quick=(st.wres?wingResult(api,st.wres):'')+wingAuto(env,st);
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
  out.wing={line:own.length?`${own.length} đôi · ${byTier.map(([r,k])=>`${tierName(r)}×${k}`).join(' ')}`:'Chưa có đôi nào',quick:wingPlan(api).n>0};
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
  bindPickers(env);
  const top=head(api,'NÂNG CẤP','⚒️ Cường hóa');
  if(!ok.length)return top+`<div class="sheet-body jr-body"><p class="muted">Chưa có gì để cường hóa. Có cánh hay thú cưng rồi quay lại nhé.</p></div>`;
  if(!ok.includes(st.ftab))st.ftab=ok[0];
  const n=forgeCounts(env),tabs=FORGE.filter(x=>ok.includes(x[0])).map(([id,e,label])=>{const k=n[id];
    return `<button type="button" role="tab" class="fg-kind${st.ftab===id?' active':''}" aria-selected="${st.ftab===id}" data-action="jrAsForgeTab" data-tab="${id}"><span class="fg-kind-e" aria-hidden="true">${e}</span><b>${label}</b><small>${k?esc(k.line):'…'}</small>${k?.quick?'<i class="fg-ready" title="Cường hóa nhanh được">⚡</i>':''}</button>`;}).join('');
  const part=FORGE.find(x=>x[0]===st.ftab)[3];
  const body=part?(PT.use()?.petEmbedHTML(env,part)||skeleton()):wingForge(env,st);
  return top+`<div class="sheet-body jr-body wd as fg">
    <div class="fg-prefs">${noAskRow()}${fzAnonRow(api)}</div>
    <nav class="fg-kinds" role="tablist" aria-label="Đồ ghép được của bạn">${tabs}</nav>
    ${body}
  </div>`;
}

/** 📣 Báo cả phố khi lên SS+ (game/forge_news.py): 🕶️ Ẩn tên (the `settings` command, forgeAnon). Short labels only (owner 23/10 "không cần giải thích nhiều"). */
function fzAnonRow(api){
  return `<label class="fg-noask" title="Báo cả phố khi lên hạng SS+ mà không hiện tên bạn"><input type="checkbox" data-as-fzanon ${api.state?.settings?.forgeAnon?'checked':''}><span>Ẩn tên</span></label>`;
}

/** ☑️ Không hỏi lại: Cường hóa, ⚡ Cường hóa nhanh and the ghép buttons act at once (v4/no-ask.js); always in sight. */
function noAskRow(){
  return `<label class="fg-noask"><input type="checkbox" data-as-noask ${noAsk()?'checked':''}><span>Không hỏi lại</span></label>`;
}

async function fzAnon(env,on){
  if(busy||!!env.api.state.settings?.forgeAnon===on)return;
  busy=true;try{await env.cmd('settings',{forgeAnon:on},{quiet:true});}finally{busy=false;}env.renderSheet();
}

/** ⚡ The wings' pickers (data-as-sel): a change sets the value and drops a picked budget back to the estimate; the sheet
 * redraws where the player is. One listener for the page, the latest env. */
let pickEnv=null;
function bindPickers(env){
  if(pickEnv||typeof document==='undefined'){pickEnv=env;return;}
  pickEnv=env;
  document.addEventListener('change',e=>{
    const na=e.target?.closest?.('#sheet [data-as-noask]');if(na&&pickEnv){setNoAsk(!!na.checked);pickEnv.renderSheet();return;}
    const an=e.target?.closest?.('#sheet [data-as-fzanon]');if(an&&pickEnv){fzAnon(pickEnv,!!an.checked);return;}
    const el=e.target?.closest?.('#sheet [data-as-sel]');if(!el||!pickEnv)return;const st=S(pickEnv.ui);
    if(el.dataset.asSel==='wascope')st.wascope=el.value||'all';
    else if(el.dataset.asSel==='watop')st.watop=Math.max(1,Math.min(WING_TIERS.length-1,Number(el.value)||WING_TIERS.length-1));else return;
    st.wabud=0;pickEnv.renderSheet();});
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
    // ⚡ Cường hóa nhanh (game/wings.py jr_pet_wing_fuse_auto): the budget, the summary, the run
    case'jrAsWingBud':st.wabud=Math.max(1,Number(data.n)||0);afterTap(()=>renderSheet());return true;
    case'jrAsWingRes':st.wres=null;renderSheet();return true;
    case'jrAsWingAuto':{const c2=WC(api);if(busy||!c2)return true;
      const {scope,top}=wAuto(st),pl=wingPlan(api,scope,top),b=wingBudget(api,st,pl),T=WING_TIERS.length-1;if(!pl.n||funds(api)<pl.min)return true;
      const lose=top>(c2.lose_from??4),sn=scope==='all'?'Mọi kiểu cánh':`Chỉ ${styleOf(api,scope)?.name||'kiểu này'}`;
      const msg=`${sn}, ba đôi cùng hạng, hạng thấp trước, tới hạng ${top===T?'🌟 Huyền thoại':tierName(top)}. Thành công: cánh chính lên hạng, giữ kiểu; hai đôi kia dùng hết. Trượt: ${lose?'dưới hạng S ba đôi vẫn còn; ⚠️ từ hạng S trở lên mất hai đôi phụ, cánh chính ở lại':'ba đôi vẫn còn'}, mất phí lượt đó. Cánh đang đeo luôn là cánh chính, không bao giờ bị dùng mất. Tiêu tối đa ${fmt(b)} xu, tối đa ${c2.auto_max||50} lượt, trả một lần: ví trước, thiếu thì lấy từ tài khoản.`;
      if(!noAsk()&&!await confirmAction('⚡ Cường hóa nhanh cánh?',msg,`⚡ Cường hóa · tối đa ${fmt(b)} xu`,{cost:Math.min(b,funds(api))}))return true;
      // the request id (game/wings.py rq): a retry answers the run it made and pays nothing
      busy=true;renderSheet();const r=await cmd('jr_pet_wing_fuse_auto',{budget:b,top,scope,rid:rid().replace(/[^A-Za-z0-9_.:-]/g,'').slice(0,64),confirm:true});busy=false;
      if(r?.auto){st.wres=r.auto;st.wabud=0;st.wfz=[];if(scope!=='all'&&!wingPlan(api,scope,top).n&&!ownWings(api).some(x=>x.k===scope))st.wascope='all';}
      renderSheet();return true;}
    case'jrAsWingFuse':{if(busy||!WC(api))return true;
      const own=ownWings(api),xs=st.wfz.map(id=>own.find(x=>x.id===id)).filter(Boolean);if(xs?.length!==3)return true;
      const f=wingFuseOf(api,xs),[m,a,b]=xs,top=WING_TIERS.length-1;if(m.r>=top)return true;
      const what=`Dùng: ${wName(api,m)} (cánh chính, giữ kiểu${m.id===wingsOf(api)?.on?', đang đeo':''}), ${wName(api,a)}, ${wName(api,b)}.`;
      if(!noAsk()&&!await confirmAction('Ghép ba đôi cánh?',`${what} Thành công: ${styleOf(api,m.k)?.name||'Cánh'} ${f.to>m.r?'lên':'giữ'} hạng ${tierName(f.to)}, hai đôi kia dùng hết. Trượt: ${f.lose?'⚠️ hai đôi kia sẽ mất':'ba đôi vẫn còn'}. Phí ${fmt(f.fee)} xu, thành hay trượt đều mất phí.`,`🧬 Ghép · ${fmt(f.fee)} xu`,{cost:f.fee}))return true;
      busy=true;const r=await cmd('jr_pet_wing_fuse',{wings:xs.map(x=>x.id),main:m.id,confirm:true});busy=false;
      if(r?.fuse){const lost=r.fuse.lost||[];st.wfz=r.fuse.ok?[]:st.wfz.filter(id=>!lost.includes(id));if(r.fuse.ok){const mm=ownWings(api).find(x=>x.id===r.fuse.main);if(mm)st.reveal=[{k:mm.k,r:mm.r}];}}
      renderSheet();return true;}
  }
  return false;
}
