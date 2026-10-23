/** ⚒️ Cường hóa v2 (owner-approved 23/10: "gọn và dễ dùng như các game khác"; jrView 'forge', action jrForge {tab}).
 * One layout for every kind (🪽 Cánh, 🧬 Thú, 👗 Đồ thú, 🧰 Linh kiện):
 * - the kind tabs on top (⚡ where ⚡ Cường hóa nhanh finds something), the player's pieces of that kind as a grid of
 *   tiles, each with its rank colour (D grey … SSS red, HT / 🌟 gold), a red ⚡ dot when it can go up now, 🔒 when locked;
 * - a tap opens the upgrade panel: the piece big, rank → next rank, what changes (% thu nhập, sức thú, chỉ số), the
 *   ingredients auto-filled as slots (tap a slot to swap), the fee, the short ⚠️ loss rule from S, and two buttons:
 *   "Cường hóa" (the one-shot command: jr_pet_wing_fuse, jr_pet_fuse, jr_pet_wfuse, jr_pet_gear_up / _fuse) and
 *   "Cường hóa tối đa" (the kind's ⚡ command up to the top rank, `pin` this piece: game/forge_locks.py), its budget as
 *   before (Tiêu tối đa: − N + with Vòng đầu / ×2 / ×5);
 * - ⚡ Ghép tất cả: every kind's ⚡ command in turn (one question unless ☑️ Không hỏi lại), one combined result card;
 * - 🔒 Khóa (jr_pet_lock): a locked piece is never an ingredient (the server skips it everywhere);
 * - ☑️ Không hỏi lại (v4/no-ask.js), 🕶️ Ẩn tên (settings forgeAnon, game/forge_news.py), ⏩ Bỏ qua hiệu ứng
 *   (localStorage 'mnl.forgeFast': no result animation, no wait).
 * Every rule, fee and roll stays on the server; the plans here mirror game/wings.py sets, game/pet_tiers.py fuse_sets /
 * gear_step and game/pet_wardrobe.py triples (locks and pin included) only to show what will happen. No odds (owner
 * 19/10 "đừng show tỷ lệ ra"). Short words on screen (owner 23/10 "không cần giải thích nhiều"). A redraw keeps the
 * scroll (env.renderSheet(), a tab change too). Styles: /css/forge.css. */
import {icon,escapeHTML as esc} from '../icons.js';
import {shortNum} from './wealth.js';
import {wingIcon} from './look.js';
import {petPicture,lookup} from './pet-art.js';
import {qtyBox,QTY,afterTap} from '../qty-input.js';
import {noAsk,setNoAsk} from './no-ask.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
/** Big xu never wrap on a phone: 1.234.567 → 1,23tr (the exact number in the title). */
const xu=n=>Number(n)>=1e5?shortNum(n):fmt(n);

/* ---- ⏩ Bỏ qua hiệu ứng: this device's choice (localStorage, try/catch; no storage: the effects play) ---- */
export const FAST_KEY='mnl.forgeFast';
export function fastFx(){try{return globalThis.localStorage?.getItem(FAST_KEY)==='1';}catch{return false;}}
export function setFastFx(on){try{if(on)globalThis.localStorage?.setItem(FAST_KEY,'1');else globalThis.localStorage?.removeItem(FAST_KEY);}catch{/* it keeps the effects */}}
/* ---- 🎯 Ghép tới: how high ⚡ goes, this device's choice (owner 23/10 after SS pets lost in one tap: "mặc định là để ghép tới
 * bậc S thôi còn mọi người tự chỉnh lên tiếp các mức trên"). S by default: no ⚡ fusion then risks the two others. ---- */
export const TOP_KEY='mnl.forgeTop',AUTO_TOPS=[4,5,6,7];
export function autoTop(){try{const n=Number(globalThis.localStorage?.getItem(TOP_KEY));return AUTO_TOPS.includes(n)?n:4;}catch{return 4;}}
export function setAutoTop(n){try{if(AUTO_TOPS.includes(n)&&n!==4)globalThis.localStorage?.setItem(TOP_KEY,String(n));else globalThis.localStorage?.removeItem(TOP_KEY);}catch{/* S */}}
/** How long the ⚒️ hammer shows before a result (no wait with ⏩ or reduced motion). */
export const FX={wait:650};
const calm=()=>{try{return !!globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;}catch{return false;}};
const pause=()=>fastFx()||calm()||!FX.wait?Promise.resolve():new Promise(r=>setTimeout(r,FX.wait));

/* ---- ranks ---- */
export const TIERS=['D','C','B','A','S','SS','SSS','HT'];
export const TIER_COLOR=['#8d939a','#3f9f5b','#3d82e6','#9256e8','#e8820f','#e0408d','#e0353b','#d9a400'];
const tierChip=(r,cls='')=>`<i class="fv-tier${cls?' '+cls:''}" style="--tc:${TIER_COLOR[r]||TIER_COLOR[0]}">${TIERS[r]??''}</i>`;
const tierName=r=>r===7?'Huyền thoại':`hạng ${TIERS[r]}`;

/* ---- the save and the catalogues ---- */
const J=api=>api.state?.journey||{};
const WC=api=>api.content?.journey?.wardrobe?.wings||null;
const PC=api=>api.content?.journey?.pets||null;
const TT=api=>PC(api)?.tiers||null;
const WD=api=>PC(api)?.wardrobe||null;
const lockSet=api=>new Set(J(api).forge_locks||[]);
/** What a payment can draw on (the wallet, then the account; nothing while the wallet is in debt). */
const funds=api=>{const j=J(api),w=Number(j.wallet)||0;return w<0?0:w+(j.bank?.open?Math.max(0,Number(j.bank.balance)||0):0);};
const LOSE=api=>TT(api)?.limits?.lose_from??WC(api)?.lose_from??4;
/** v4/pets.js fxOf: the rank aura, the coat effect, 🌟 on a legendary that kept its breed, the clothes' ranks. */
const fxOf=(api,p)=>p?{r:p.r||0,x:p.fx??p.x??'',lg:!!p.legend&&(PC(api)?.breeds||[]).find(b=>b.id===p.b)?.fuse!=='legend',wr:p.wr||null,o:p.wo||0,st:p.wst||''}:{};
function petArt(api,p,size,pose='sit'){
  const L=p&&lookup(PC(api),p.b,p.c);if(!L)return `<span class="fv-emo" aria-hidden="true">🐾</span>`;
  return petPicture(L.breed,L.coat,pose,p.w||{},size,'pet-svg',fxOf(api,p));
}

/** The kinds: [tab id (jrForge {tab}), emoji, label, kind]. */
const KINDS=[['wing','🪽','Cánh','wing'],['plab','🧬','Thú','pet'],['pward','👗','Đồ thú','ward'],['pgear','🧰','Linh kiện','gear']];
/* Whole sentences per kind (the English pack matches whole texts: public/js/v4/i18n.js). */
const NEED={wing:n=>`Thiếu ${n} đôi`,pet:n=>`Thiếu ${n} bé`,ward:n=>`Thiếu ${n} món`,gear:n=>`Thiếu ${n} món`};
const LOSS={wing:'⚠️ Trượt mất 2 đôi phụ',pet:'⚠️ Trượt mất 2 bé phụ',ward:'',gear:'⚠️ Trượt mất 2 món phụ'};
const LOST={wing:n=>`Mất ${n} đôi phụ`,pet:n=>`Mất ${n} bé phụ`,ward:n=>`Mất ${n} món phụ`,gear:n=>`Mất ${n} món phụ`};
const NONE={wing:'Chưa có đôi cánh nào.',pet:'Chưa có bé nào.',ward:'Chưa có đồ thú nào.',gear:'Chưa có linh kiện nào.'};
/** The kinds this save has: wings with a character, the pets' with pets on the server (story mode). */
export function forgeTabs(api){
  const j=J(api),pc=PC(api),pets=!!(j.story&&j.pets&&pc);
  return KINDS.filter(([id])=>id==='wing'?!!(WC(api)&&j.gender):!pets?false:id==='pward'?!!pc.wardrobe:!!pc.tiers).map(x=>x[0]);
}
const kindOf=tab=>KINDS.find(x=>x[0]===tab)?.[3]||'wing';

/* ---- the pieces of each kind, one shape: {id, kind, r (7 = HT / 🌟), name, …} ---- */
function wings(api){
  const w=J(api).wings,c=WC(api);if(!w||!c)return [];
  return w.own.map(x=>({id:x.id,kind:'wing',r:x.r,k:x.k,name:c.styles?.find(s=>s.id===x.k)?.name||'Cánh',worn:x.id===w.on,price:c.styles?.find(s=>s.id===x.k)?.price||0,raw:x}));
}
function pets(api){
  const v=J(api).pets;if(!v||!TT(api))return [];
  const all=[...(v.pets||[]).map(p=>({...p,at:'home'})),...(v.petx?.ken||[]).map(p=>({...p,at:'ken'})),...(v.farm||[]).map(p=>({...p,at:'farm'}))];
  return all.map(p=>({id:p.id,kind:'pet',r:p.legend?7:(p.r||0),name:p.n,b:p.b,at:p.at,walk:p.id===v.walk,sad:p.at==='home'&&p.mood==='buon',
    pw:Number(p.pw)||0,legend:!!p.legend,dogcat:(PC(api)?.breeds||[]).find(b=>b.id===p.b)?.kind||'',raw:p}));
}
function wardStacks(api){
  const W=WD(api),its=J(api).pets?.petw?.it||[],L=lockSet(api),m=new Map();if(!W)return [];
  for(const i of its){const it=W.items?.find(q=>q.id===i.k);if(!it)continue;const key=`${i.k}|${i.r}`;
    let g=m.get(key);if(!g){g={id:key,kind:'ward',r:i.r,k:i.k,name:it.name,emoji:it.emoji,it,pieces:[]};m.set(key,g);}
    g.pieces.push({id:i.id,on:i.on||null,locked:L.has(i.id)});}
  return [...m.values()];
}
function gears(api){
  const t=TT(api);if(!t)return [];
  return (J(api).pets?.petx?.gear||[]).map(g=>({id:g.id,kind:'gear',r:g.r,lv:g.lv,s:g.s,m:g.m,name:g.name,emoji:g.emoji,on:g.on||null,value:g.value,up_fee:g.up_fee,raw:g}));
}
const itemsOf=(api,kind)=>kind==='wing'?wings(api):kind==='pet'?pets(api):kind==='ward'?wardStacks(api):gears(api);

/* ---- what the server's ⚡ finds (the same picks; locks and pin included) ---- */
const seq=x=>Number(String(x.id).slice(1))||0;
/** game/wings.py sets: [{r, set [main, a, b], t}] the lowest tier first. */
export function wingSets(api,scope='all',top=7,pin=null){
  const all=wings(api),w=J(api).wings,locks=lockSet(api),pinned=pin&&all.find(x=>x.id===pin);
  const cap=pinned?Math.min(top,7,pinned.r<7?pinned.r+1:0):Math.min(top,7);
  const keep=new Set([...locks,...[pin,w?.on].filter(Boolean)]),g=new Map();
  for(const x of all)if((scope==='all'||x.k===scope)&&x.r<cap){if(!g.has(x.r))g.set(x.r,[]);g.get(x.r).push(x);}
  const out=[];
  for(const [r,xs] of [...g].sort((a,b)=>a[0]-b[0])){
    const free=xs.filter(x=>!keep.has(x.id)),t=Math.min(Math.floor(free.length/2),Math.floor(xs.length/3));if(t<1)continue;
    const main=xs.find(x=>x.id===pin)||xs.find(x=>x.id===w?.on)||[...xs].sort((a,b)=>(keep.has(b.id)-keep.has(a.id))||(b.price-a.price)||(seq(a)-seq(b)))[0];
    const rest=free.filter(x=>x!==main).sort((a,b)=>(a.price-b.price)||(seq(a)-seq(b)));
    out.push({r,set:[main,rest[0],rest[1]],t});
  }
  return out;
}
/** game/pet_tiers.py fuse_sets. */
export function petSets(api,scope='all',top=7,pin=null){
  const all=pets(api),walk=J(api).pets?.walk,locks=lockSet(api),pinned=pin&&all.find(p=>p.id===pin);
  const cap=pinned?(pinned.legend?-1:pinned.r):7,keep=new Set([...locks,...[pin,walk].filter(Boolean)]),g=new Map();
  for(const p of all){if(p.legend||p.sad||!p.dogcat||(scope!=='all'&&p.dogcat!==scope)||p.r+1>top||p.r>cap)continue;if(!g.has(p.r))g.set(p.r,[]);g.get(p.r).push(p);}
  const out=[];
  for(const [r,xs] of [...g].sort((a,b)=>a[0]-b[0])){
    const free=xs.filter(p=>!keep.has(p.id)),t=Math.min(Math.floor(free.length/2),Math.floor(xs.length/3));if(t<1)continue;
    const main=xs.find(p=>p.id===pin)||xs.find(p=>p.id===walk)||[...xs].sort((a,b)=>(keep.has(b.id)-keep.has(a.id))||(b.pw-a.pw)||(a.id<b.id?1:-1))[0];
    const rest=free.filter(p=>p!==main).sort((a,b)=>((a.at==='home')-(b.at==='home'))||(a.pw-b.pw)||(a.id<b.id?-1:1));
    out.push({r,set:[main,rest[0],rest[1]],t});
  }
  return out;
}
/** game/pet_wardrobe.py triples (worn ones kept, locked ones never): [{k, r, t}]. */
export function wardSets(api,scope='all',top=6){
  const order=(WD(api)?.items||[]).map(i=>i.id),out=[];
  for(const g of wardStacks(api)){if((scope!=='all'&&g.k!==scope)||g.r>=Math.min(top,6))continue;
    const n=g.pieces.filter(p=>!p.on&&!p.locked).length;if(n>=3)out.push({k:g.k,r:g.r,t:Math.floor(n/3)});}
  return out.sort((a,b)=>a.r-b.r||order.indexOf(a.k)-order.indexOf(b.k));
}
/** game/pet_tiers.py gear_step, as a plan: {sets [{g main, r}], worn [g] (+1s), est one round, min the first fee}. */
export function gearPlan(api,scope='all',top=6,pin=null){
  const t=TT(api);if(!t)return {sets:[],worn:[],n:0,est:0,min:0};
  const L=t.gear.lv_max,order=t.gear.slots.map(s=>s.id),locks=lockSet(api),all=gears(api),pinned=pin&&all.find(g=>g.id===pin);
  const bag=all.filter(g=>(scope==='all'||g.s===scope)&&(!pinned||(g.s===pinned.s&&g.r<=pinned.r)));
  const keep=g=>!!g.on||locks.has(g.id)||g.id===pin;
  const up=(r,lv)=>t.gear.up_fee[r]*(lv+1),toMax=g=>{let a=0;for(let lv=g.lv;lv<L;lv++)a+=up(g.r,lv);return a;};
  const m=new Map();for(const g of bag){if(g.r>=Math.min(top,6))continue;const key=`${g.r}|${order.indexOf(g.s)}`;if(!m.has(key))m.set(key,[]);m.get(key).push(g);}
  const sets=[];
  for(const [,gs] of [...m].sort((a,b)=>a[1][0].r-b[1][0].r||order.indexOf(a[1][0].s)-order.indexOf(b[1][0].s))){
    const main=[...gs].sort((a,b)=>((b.id===pin)-(a.id===pin))||(!!b.on-!!a.on)||(keep(b)-keep(a))||b.lv-a.lv||seq(a)-seq(b))[0];
    if(gs.filter(g=>g!==main&&!keep(g)).length<2)continue;
    sets.push({g:main,r:main.r,cost:toMax(main)+t.gear.fuse_fee[main.r],first:main.lv<L?up(main.r,main.lv):t.gear.fuse_fee[main.r]});
  }
  const worn=sets.length?[]:bag.filter(g=>(g.on||g.id===pin)&&g.lv<L).sort((a,b)=>((a.id!==pin)-(b.id!==pin))||b.r-a.r||b.lv-a.lv||seq(a)-seq(b));
  return {sets,worn,n:sets.length+worn.length,est:sets.reduce((a,x)=>a+x.cost,0)+worn.reduce((a,g)=>a+toMax(g),0),
    min:sets.length?sets[0].first:worn.length?up(worn[0].r,worn[0].lv):0};
}
/** {n, est the first round's fees, min the first fee} of a kind's ⚡ (scope, pin). */
export function planOf(api,kind,scope='all',pin=null,top=autoTop()){
  if(kind==='gear')return gearPlan(api,scope,Math.min(top,6),pin);
  const fee=kind==='wing'?r=>Number(WC(api)?.fee?.[r])||0:kind==='pet'?r=>Number(TT(api)?.ranks?.[r]?.fee)||0:r=>Number(WD(api)?.fee?.[r])||0;
  const sets=kind==='wing'?wingSets(api,scope,top,pin):kind==='pet'?petSets(api,scope,top,pin):wardSets(api,scope,6);   // 👗 never loses: all the way
  return {sets,n:sets.reduce((a,x)=>a+x.t,0),est:sets.reduce((a,x)=>a+x.t*fee(x.r),0),min:sets.length?fee(sets[0].r):0};
}
const autoMax=(api,kind)=>kind==='wing'?WC(api)?.auto_max:kind==='ward'?WD(api)?.auto_max:kind==='gear'?TT(api)?.limits?.gear_auto_max:TT(api)?.limits?.auto_max;

/* ---- one piece: can it go up now, with what ---- */
/** The ingredients that may join piece x by hand, best first (the server's order for its ⚡). */
function mates(api,x){
  const L=lockSet(api);
  if(x.kind==='wing'){const on=J(api).wings?.on;
    return wings(api).filter(y=>y.id!==x.id&&y.r===x.r&&y.id!==on&&!L.has(y.id)).sort((a,b)=>(a.price-b.price)||(seq(a)-seq(b)));}
  if(x.kind==='pet'){const walk=J(api).pets?.walk;
    return pets(api).filter(q=>q.id!==x.id&&q.r===x.r&&!q.legend&&!q.sad&&q.id!==walk&&!L.has(q.id)).sort((a,b)=>((a.at==='home')-(b.at==='home'))||(a.pw-b.pw));}
  if(x.kind==='gear')return gears(api).filter(g=>g.id!==x.id&&g.s===x.s&&g.r===x.r&&!g.on&&!L.has(g.id)).sort((a,b)=>a.lv-b.lv||seq(a)-seq(b));
  return [];
}
/** What a tap of "Cường hóa" does for x: {mode fuse | up | max | none, fee, to (rank), need (ingredients missing), lose, why}. */
function stepOf(api,x){
  const t=TT(api),c=WC(api),W=WD(api),L=lockSet(api);
  if(x.kind==='wing'){if(x.r>=7)return {mode:'max'};const m=mates(api,x);return {mode:'fuse',fee:c.fee[x.r],to:x.r+1,need:Math.max(0,2-m.length),lose:x.r>=LOSE(api)};}
  if(x.kind==='pet'){if(x.legend)return {mode:'max'};if(x.sad)return {mode:'none',why:'Bé đang buồn'};const m=mates(api,x);
    return {mode:'fuse',fee:t.ranks[x.r].fee,to:x.r+1,need:Math.max(0,2-m.length),lose:x.r>=LOSE(api)};}
  if(x.kind==='ward'){if(x.r>=6)return {mode:'max'};const free=x.pieces.filter(p=>!L.has(p.id)).length;
    return {mode:'fuse',fee:W.fee[x.r],to:x.r+1,need:Math.max(0,3-free),lose:false};}
  const lv=t.gear.lv_max;
  if(x.lv<lv)return {mode:'up',fee:x.up_fee,to:x.r,lv:x.lv+1,need:0,lose:false};
  if(x.r>=6)return {mode:'max'};
  const m=mates(api,x);return {mode:'fuse',fee:t.gear.fuse_fee[x.r],to:x.r+1,need:Math.max(0,2-m.length),lose:x.r>=LOSE(api)};
}
const canUp=(api,x)=>{const s=stepOf(api,x);return (s.mode==='fuse'||s.mode==='up')&&!s.need&&funds(api)>=s.fee;};
/** The narrowest ⚡ scope holding x, and its pin: "Cường hóa tối đa". */
const maxOf=x=>x.kind==='wing'?{scope:'all',pin:x.id}:x.kind==='pet'?{scope:'all',pin:x.id}:x.kind==='ward'?{scope:x.k,pin:null}:{scope:x.s,pin:x.id};

/* ---- the screen ---- */
const S=ui=>ui.fg??={sel:null,picks:{},slot:-1,bud:{},res:null,allx:1};
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,action,data={},cls='',dis=false,extra='')=>`<button type="button" class="btn ${cls}" data-action="${action}"${attrs(data)}${dis?' disabled':''}${extra}>${label}</button>`;
let busy=false,running='';

function artOf(api,x,size){
  if(x.kind==='wing')return wingIcon(x.raw||{k:x.k,r:x.r},size);
  if(x.kind==='pet')return petArt(api,x.raw||x,size);
  if(x.kind==='ward'&&size>=96){const p=(J(api).pets?.pets||[]).find(q=>q.id===J(api).pets?.walk)||(J(api).pets?.pets||[])[0];
    if(p&&x.it){const w={...(p.w||{}),[x.it.slot]:x.k},f=fxOf(api,p);f.wr={...(f.wr||{}),[x.it.slot]:x.r};
      const L=lookup(PC(api),p.b,p.c);if(L)return petPicture(L.breed,L.coat,x.it.slot==='bed'?'sleep':'sit',w,size,'pet-svg',f);}}
  return `<span class="fv-emo" style="--s:${size}px" aria-hidden="true">${esc(x.emoji||'✨')}</span>`;
}
function tileSub(api,x){
  if(x.kind==='wing')return x.worn?'👕':'';
  if(x.kind==='pet')return x.walk?'🦮':x.at==='ken'?'🏠':x.at==='farm'?'🌾':x.sad?'🥺':'';
  if(x.kind==='ward')return `×${x.pieces.length}${x.pieces.some(p=>p.on)?' 🐾':''}`;
  return `${x.lv?`+${x.lv}`:'+0'}${x.on?' 🐾':''}`;
}
const isLocked=(api,x)=>x.kind==='ward'?x.pieces.some(p=>p.locked):lockSet(api).has(x.id);
function tile(api,st,x){
  const on=st.sel===x.id,up=canUp(api,x),lk=isLocked(api,x),sub=tileSub(api,x);
  const label=`${x.name}, ${tierName(x.r)}${up?', lên hạng được':''}${lk?', đã khóa':''}`;
  return `<li><button type="button" class="fv-tile${on?' on':''}" style="--tc:${TIER_COLOR[x.r]}" data-action="jrFgSel" data-id="${esc(x.id)}" aria-pressed="${on}" aria-label="${esc(label)}">
    <span class="fv-art">${artOf(api,x,52)}</span>${tierChip(x.r)}${up?'<i class="fv-dot" aria-hidden="true">⚡</i>':''}${lk?'<i class="fv-lk" aria-hidden="true">🔒</i>':''}
    <small class="fv-nm" data-no-translate>${esc(x.name)}</small>${sub?`<small class="fv-sub">${esc(sub)}</small>`:''}</button></li>`;
}
const sortItems=(api,xs)=>[...xs].sort((a,b)=>b.r-a.r||(canUp(api,b)-canUp(api,a))||String(a.name).localeCompare(String(b.name),'vi')||seq(a)-seq(b));

/** The ingredients picked for x: the player's swaps where still valid, else the best ones. */
function picksOf(api,st,x){
  const m=mates(api,x),mine=(st.picks[x.id]||[]).filter(id=>m.some(y=>y.id===id));
  const out=[...new Set(mine)].slice(0,2);for(const y of m){if(out.length>=2)break;if(!out.includes(y.id))out.push(y.id);}
  return out.map(id=>m.find(y=>y.id===id));
}
function slots(api,st,x,step){
  if(step.mode!=='fuse')return '';
  if(x.kind==='ward'){const L=lockSet(api),use=x.pieces.filter(p=>!L.has(p.id)).sort((a,b)=>!!a.on-!!b.on).slice(0,3);
    return `<div class="fv-slots" role="group" aria-label="Nguyên liệu ${use.length}/3"><span class="fv-cnt">${use.length}/3</span>${[0,1,2].map(i=>use[i]
      ?`<span class="fv-slot">${artOf(api,x,40)}${tierChip(x.r,'sm')}${use[i].on?'<small class="fv-sub">🐾</small>':''}</span>`
      :`<span class="fv-slot empty" aria-label="Thiếu">＋</span>`).join('')}</div>`;}
  const ps=picksOf(api,st,x),m=mates(api,x),n=1+ps.length;
  const side=(y,i)=>y?`<button type="button" class="fv-slot pick${st.slot===i?' open':''}" data-action="jrFgSlot" data-i="${i}" aria-expanded="${st.slot===i}" aria-label="${esc(`Nguyên liệu ${i+1}: ${y.name}. Đổi`)}">${artOf(api,y,40)}${tierChip(y.r,'sm')}<small class="fv-sub">⇄</small></button>`
    :`<span class="fv-slot empty" aria-label="Thiếu">＋</span>`;
  const list=st.slot>=0&&m.length>2?`<ul class="fv-cands" aria-label="Chọn nguyên liệu">${m.map(y=>{const cur=ps[st.slot]?.id===y.id,other=ps.some((z,j)=>j!==st.slot&&z?.id===y.id);
    return `<li><button type="button" class="fv-cand${cur?' on':''}" data-action="jrFgPick" data-i="${st.slot}" data-id="${esc(y.id)}" aria-pressed="${cur}"${other?' disabled':''} aria-label="${esc(`${y.name} ${tierName(y.r)}`)}">${artOf(api,y,36)}<small data-no-translate>${esc(y.name)}</small></button></li>`;}).join('')}</ul>`:'';
  return `<div class="fv-slots" role="group" aria-label="Nguyên liệu ${n}/3"><span class="fv-cnt">${n}/3</span><span class="fv-slot main">${artOf(api,x,40)}${tierChip(x.r,'sm')}<small class="fv-sub">👑</small></span>${side(ps[0],0)}${side(ps[1],1)}</div>${list}`;
}
/** What changes: % thu nhập, 💪 lực chiến thú, chỉ số. */
function gains(api,x,step){
  const row=(e,a,b)=>`<li><span aria-hidden="true">${e}</span> <b>${a}</b> → <b class="up">${b}</b></li>`;
  if(x.kind==='wing'){const c=WC(api);return row('💰',`+${c.earn[x.r]}%`,`+${c.earn[step.to]}%`)+row('💪',`+${c.battle[x.r]}%`,`+${c.battle[step.to]}%`);}
  if(x.kind==='pet'){const R=TT(api).ranks;return step.to>6?row('💰',`+${R[6].profit}%`,'🌟'):row('💰',`+${R[x.r].profit}%`,`+${R[step.to].profit}%`);}
  if(x.kind==='ward'){const W=WD(api);return x.it?.slot==='bed'?'':row('💰',`+${W.bonus[x.r]}%`,`+${W.bonus[step.to]}%`);}
  const t=TT(api),st=t.stats.find(s=>s.id===t.gear.slots.find(z=>z.id===x.s)?.stat),bonus=t.gear.models?.[x.s]?.[x.m]?.bonus||0;
  const val=(r,lv)=>t.gear.base[r]+Math.floor(t.gear.base[r]*lv/10)+bonus;
  return step.mode==='up'?row(st?.emoji||'✨',`+${x.value}`,`+${val(x.r,step.lv)}`):row(st?.emoji||'✨',`+${x.value}`,`+${val(step.to,0)}`);
}
function budgetOf(api,st,x,pl){
  if(!pl.n)return 0;const cap=Math.max(pl.min,funds(api));
  return Math.max(pl.min,Math.min(st.bud[x.id]||pl.est,cap));
}
function panel(api,st,x){
  const step=stepOf(api,x),lk=isLocked(api,x),allLk=x.kind==='ward'?x.pieces.every(p=>p.locked):lk;
  const head=`<div class="fv-ph"><h3 id="fv-ptitle" tabindex="-1" data-no-translate>${esc(x.name)}</h3>
    <button type="button" class="btn ghost small fv-lock${lk?' on':''}" data-action="jrFgLock" data-id="${esc(x.id)}" aria-pressed="${allLk}">${allLk?'🔓 Mở khóa':'🔒 Khóa'}${x.kind==='ward'&&lk&&!allLk?` <small>${x.pieces.filter(p=>p.locked).length}/${x.pieces.length}</small>`:''}</button>
    <button type="button" class="btn ghost small fv-x" data-action="jrFgSel" data-id="" aria-label="Đóng">${icon('x',18)}</button></div>`;
  const big=`<div class="fv-big" style="--tc:${TIER_COLOR[x.r]}">${artOf(api,x,112)}</div>`;
  if(step.mode==='max')return `<section class="jr-card fv-panel" id="fv-panel" aria-labelledby="fv-ptitle">${head}${big}<p class="fv-ladder">${tierChip(x.r,'big')} <span>Cao nhất rồi</span></p></section>`;
  if(step.mode==='none')return `<section class="jr-card fv-panel" id="fv-panel" aria-labelledby="fv-ptitle">${head}${big}<p class="fv-ladder">${tierChip(x.r,'big')}</p><p class="fv-warn">${esc(step.why)}</p></section>`;
  const ladder=step.mode==='up'?`<p class="fv-ladder">${tierChip(x.r,'big')} <b>+${x.lv}</b> <span aria-hidden="true">→</span> <b class="up">+${step.lv}</b></p>`
    :`<p class="fv-ladder" aria-label="${esc(`${tierName(x.r)} lên ${tierName(step.to)}`)}">${tierChip(x.r,'big')} <span aria-hidden="true">→</span> ${tierChip(step.to,'big')}</p>`;
  const short=funds(api)<step.fee,ready=!step.need&&!short;
  const one=btn(running===x.id+':one'?'⚒️ …':'Cường hóa','jrFgOne',{id:x.id},'primary fv-go',busy||!ready);
  // ⚡ Cường hóa tối đa: the kind's ⚡, pinned on this piece (game/forge_locks.py), the budget as before
  const mo=maxOf(x),pl=planOf(api,x.kind,mo.scope,mo.pin),b=budgetOf(api,st,x,pl),cap=Math.max(pl.min,funds(api));
  const quick=[];for(const [n,l] of [[pl.est,'Vòng đầu'],[pl.est*2,'×2'],[pl.est*5,'×5']]){const v=Math.max(pl.min,Math.min(n,cap));if(!quick.some(q=>q[0]===v))quick.push([v,l]);}
  const nb=(m,l,dis,on='')=>`<button type="button" class="fv-qb${on}" data-action="jrFgBud"${attrs({id:x.id,n:m})}${dis?' disabled':''}${l.length<3?` aria-label="${m<b?'Bớt':'Thêm'}"`:''}>${l}</button>`;
  const maxBox=pl.n&&autoMax(api,x.kind)?`<div class="fv-max">${btn(running===x.id+':max'?'⚒️ …':'⚡ Cường hóa tối đa','jrFgMax',{id:x.id},'fv-go2',busy||funds(api)<pl.min)}
      <div class="fv-bud" role="group" aria-label="Tiêu tối đa"><span class="fv-step">${nb(b-pl.min,'−',b-pl.min<pl.min)}${qtyBox({value:b,min:pl.min,max:cap,money:true,label:'Tiêu tối đa',go:`data-action="jrFgBud" data-id="${esc(x.id)}" data-n="${QTY}"`})}${nb(b+pl.min,'+',b+pl.min>cap)}</span>
      <span class="fv-qchips">${quick.map(([n,l])=>nb(n,l,false,n===b?' on':'')).join('')}</span></div></div>`:'';
  const why=step.need?`<p class="fv-need">${NEED[x.kind](step.need)}</p>`:short?`<p class="fv-need">Thiếu ${xu(step.fee-funds(api))} xu</p>`:'';
  return `<section class="jr-card fv-panel" id="fv-panel" aria-labelledby="fv-ptitle">${head}
    <div class="fv-top">${big}<div class="fv-info">${ladder}<ul class="fv-gain">${gains(api,x,step)}</ul></div></div>
    ${slots(api,st,x,step)}
    <p class="fv-fee">Phí <b title="${fmt(step.fee)} xu">${xu(step.fee)} xu</b></p>
    ${step.lose&&LOSS[x.kind]?`<p class="fv-warn">${LOSS[x.kind]}</p>`:''}${why}
    <div class="fv-acts">${one}${maxBox}</div></section>`;
}

/* ---- results: one card for a fusion, a ⚡ run or Ghép tất cả ---- */
function madeOf(api,kind,a){
  if(kind==='wing')return (a.made||[]).map(x=>({kind,r:x.r,name:WC(api)?.styles?.find(s=>s.id===x.k)?.name||'Cánh',raw:x}));
  if(kind==='pet')return (a.made||[]).map(x=>{const p=pets(api).find(q=>q.id===x.id);return {kind,r:x.legend?7:x.r,name:x.n,raw:p?.raw||{b:x.b,c:0,r:x.r}};});
  if(kind==='ward')return (a.made||[]).map(x=>{const it=WD(api)?.items?.find(q=>q.id===x.k);return {kind,r:x.r,name:it?.name||'',emoji:it?.emoji};});
  return (a.made||[]).map(g=>({kind,r:g.r,name:`${g.name}${g.lv?` +${g.lv}`:''}`,emoji:g.emoji}));
}
function resultCard(api,res){
  const best=[...res.made].sort((a,b)=>b.r-a.r)[0],anim=res.fx?' fv-pop':'';
  const list=res.made.slice(0,12).map(x=>`<li style="--tc:${TIER_COLOR[x.r]}">${artOf(api,x,40)}${tierChip(x.r,'sm')}</li>`).join('')+(res.made.length>12?`<li class="more">+${res.made.length-12}</li>`:'');
  return `<section class="jr-card fv-res${anim}${res.ok?' win':''}" role="status" aria-live="polite" aria-label="Kết quả cường hóa">
    <div class="fv-rh"><h3>${res.ok?'🎉 Thành công':'💨 Trượt'}</h3>${btn(icon('x',18),'jrFgRes',{},'ghost small',false,' aria-label="Ẩn kết quả"')}</div>
    ${best?`<div class="fv-rbest${res.fx?' fv-shine':''}" style="--tc:${TIER_COLOR[best.r]}">${artOf(api,best,88)}${tierChip(best.r,'big')}<b data-no-translate>${esc(best.name)}</b></div>`:''}
    <div class="fv-stats"><div><b>${res.n}</b><small>lượt</small></div><div class="good"><b>${res.okN}</b><small>thành công</small></div><div><b>${res.n-res.okN}</b><small>trượt</small></div><div><b title="${fmt(res.spent)} xu">${shortNum(res.spent)}</b><small>xu đã tiêu</small></div></div>
    ${res.made.length?`<ul class="fv-made" aria-label="Lên hạng">${list}</ul>`:''}${res.lost?`<p class="fv-warn">${(LOST[res.kind]||LOST.gear)(res.lost)}</p>`:''}</section>`;
}

/* ---- ✨ a thần thú offer (a fusion to S+; ⚡ stops on it): answered here too (jr_pet_morph) ---- */
function myth(api){
  const o=J(api).pets?.petw?.mo,p=o&&pets(api).find(q=>q.id===o.p);if(!p)return '';
  const b=(PC(api)?.breeds||[]).find(x=>x.id===o.b);
  return `<section class="jr-card fv-myth" aria-label="Thần thú"><h3>✨ Thần thú</h3><div class="fv-myth-row">${petArt(api,p.raw,72)}<span aria-hidden="true">➜</span>${petArt(api,{...p.raw,b:o.b,c:o.c},72,'happy')}</div>
    <p class="fv-center"><b data-no-translate>${esc(p.name)}</b> → <b>${esc(b?.name||'')}</b></p>
    <div class="fv-acts two">${btn('💛 Giữ','jrFgMorph',{take:'0'},'ghost',busy)}${btn('✨ Đổi','jrFgMorph',{take:'1'},'primary',busy)}</div></section>`;
}

/* ---- the view ---- */
function head(){
  return `<header class="sheet-head jr-head"><button type="button" class="btn ghost small jr-back" data-action="jrView" data-view="home" aria-label="Quay lại">${icon('back',18)}</button><div class="grow"><span class="eyebrow">NÂNG CẤP</span><h2>⚒️ Cường hóa</h2></div></header>`;
}
const pref=(key,on,label,title='')=>`<label class="fv-pref"${title?` title="${esc(title)}"`:''}><input type="checkbox" data-fv-pref="${key}"${on?' checked':''}><span>${label}</span></label>`;
/** ⚡ Ghép tất cả: what each kind's ⚡ would do now (scope all), the budgets at ×allx. */
function allPlan(api,st){
  const out=[];let left=funds(api);
  for(const tab of forgeTabs(api)){const kind=kindOf(tab);if(!autoMax(api,kind))continue;const pl=planOf(api,kind);if(!pl.n)continue;
    const b=Math.max(pl.min,Math.min(pl.est*(st.allx||1),Math.max(pl.min,left)));out.push({tab,kind,b,pl});}
  return out;
}
export function forgeView(env){
  const {api,ui}=env,st=S(ui),as=ui.as??={},ok=forgeTabs(api);bind(env);
  if(!ok.length)return head()+`<div class="sheet-body jr-body fv"><p class="muted">Chưa có gì để cường hóa.</p></div>`;
  if(!ok.includes(as.ftab))as.ftab=ok[0];
  const kind=kindOf(as.ftab),items=sortItems(api,itemsOf(api,kind));
  if(st.sel&&!items.some(x=>x.id===st.sel))st.sel=null;
  const tabs=KINDS.filter(x=>ok.includes(x[0])).map(([id,e,label,k])=>{const on=id===as.ftab,n=itemsOf(api,k).length,go=!!autoMax(api,k)&&planOf(api,k).n>0;
    return `<button type="button" role="tab" id="fv-t-${id}" class="fv-kind${on?' on':''}" aria-selected="${on}" aria-controls="fv-pane" data-action="jrFgTab" data-tab="${id}"><span aria-hidden="true">${e}</span><b>${label}</b><small>${n}</small>${go?'<i class="fv-ready" aria-label="Cường hóa nhanh được">⚡</i>':''}</button>`;}).join('');
  const plan=allPlan(api,st),sum=plan.reduce((a,x)=>a+x.b,0);
  const all=`<div class="fv-all">${btn(running==='all'?`⚒️ ${st.allAt||''}`:'⚡ Ghép tất cả','jrFgAll',{},'primary fv-allgo',busy||!plan.length)}
    <span class="fv-allx" role="group" aria-label="Tiêu tối đa">${[1,2,5].map(m=>`<button type="button" class="fv-qb${(st.allx||1)===m?' on':''}" data-action="jrFgAllX" data-x="${m}" aria-pressed="${(st.allx||1)===m}">×${m}</button>`).join('')}</span>
    <small class="fv-allsum">${plan.length?`≤ <b title="${fmt(sum)} xu">${shortNum(sum)}</b> xu`:'—'}</small>
    <span class="fv-allx fv-top" role="group" aria-label="Ghép tới hạng"><small>Ghép tới</small>${AUTO_TOPS.map(n=>`<button type="button" class="fv-qb${autoTop()===n?' on':''}" data-action="jrFgTop" data-top="${n}" aria-pressed="${autoTop()===n}">${TIERS[n]}</button>`).join('')}</span></div>`;
  const sel=st.sel&&items.find(x=>x.id===st.sel);
  const grid=items.length?`<ul class="fv-grid" aria-label="${esc(KINDS.find(x=>x[0]===as.ftab)[2])}">${items.map(x=>tile(api,st,x)).join('')}</ul>`
    :`<div class="fv-empty"><p>${NONE[kind]}</p>${btn('🛍️ Cửa hàng','jrAccShop',{tab:{wing:'wing',pet:'pbuy',ward:'pwear',gear:'pgear'}[kind]},'small')}</div>`;
  return head()+`<div class="sheet-body jr-body fv${sel?' has-sel':''}">
    <div class="fv-prefs">${pref('noask',noAsk(),'Không hỏi lại')}${pref('anon',!!api.state?.settings?.forgeAnon,'Ẩn tên','Lên hạng SS+: báo cả phố không kèm tên')}${pref('fast',fastFx(),'Bỏ qua hiệu ứng')}</div>
    ${all}${st.res?resultCard(api,st.res):''}${myth(api)}
    <nav class="fv-kinds" role="tablist" aria-label="Loại đồ">${tabs}</nav>
    <div class="fv-main" id="fv-pane" role="tabpanel" aria-labelledby="fv-t-${as.ftab}">${sel?panel(api,st,sel):''}${grid}</div>
  </div>`;
}

/* ---- the clicks ---- */
let bound=null;
function bind(env){
  if(bound||typeof document==='undefined'){bound=env;return;}
  bound=env;
  document.addEventListener('change',e=>{
    const el=e.target?.closest?.('#sheet [data-fv-pref]');if(!el||!bound)return;const on=!!el.checked,k=el.dataset.fvPref;
    if(k==='noask'){setNoAsk(on);bound.renderSheet();}
    else if(k==='fast'){setFastFx(on);bound.renderSheet();}
    else if(k==='anon')anon(bound,on);
  });
}
async function anon(env,on){
  if(busy||!!env.api.state?.settings?.forgeAnon===on)return;
  busy=true;try{await env.cmd('settings',{forgeAnon:on},{quiet:true});}finally{busy=false;}env.renderSheet();
}
const rid=()=>(globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`).replace(/[^A-Za-z0-9_.:-]/g,'').slice(0,64);
/** The ⚡ command of a kind: [action, payload]. */
function autoCmd(kind,scope,pin,budget,top=autoTop()){
  if(kind==='wing')return ['jr_pet_wing_fuse_auto',{budget,top,scope,...(pin?{pin}:{}),rid:rid(),confirm:true}];
  if(kind==='pet')return ['jr_pet_fuse_auto',{budget,top,scope,...(pin?{pin}:{}),confirm:true}];
  if(kind==='ward')return ['jr_pet_wfuse_auto',{budget,max_rank:6,scope,confirm:true}];
  return ['jr_pet_gear_auto',{budget,top:Math.min(top,6),scope,...(pin?{pin}:{}),confirm:true}];
}
const ask=(env,title,msg,label,cost)=>noAsk()?Promise.resolve(true):env.confirmAction(title,msg,label,cost?{cost}:undefined);
const focusPanel=()=>{if(typeof document==='undefined')return;const p=document.getElementById?.('fv-panel');if(!p)return;
  const r=p.getBoundingClientRect?.(),h=globalThis.innerHeight||800;if(r&&(r.top<0||r.top>h*.6))p.scrollIntoView?.({block:'start',behavior:fastFx()||calm()?'auto':'smooth'});
  document.getElementById('fv-ptitle')?.focus?.({preventScroll:true});};

async function runOne(env,st,x){
  const {api}=env,step=stepOf(api,x);if(busy||step.need||!(step.mode==='fuse'||step.mode==='up'))return;
  const ps=x.kind==='ward'||step.mode==='up'?[]:picksOf(api,st,x);

  const what=step.mode==='up'?`+${x.lv} → +${step.lv}`:`${TIERS[x.r]} → ${TIERS[step.to]}`;
  if(!await ask(env,`⚒️ Cường hóa ${what}?`,step.lose&&LOSS[x.kind]?`Phí ${fmt(step.fee)} xu. ${LOSS[x.kind]}.`:`Phí ${fmt(step.fee)} xu.`,`Cường hóa · ${xu(step.fee)} xu`,step.fee))return;
  const [action,payload]=x.kind==='wing'?['jr_pet_wing_fuse',{wings:[x.id,...ps.map(y=>y.id)],main:x.id,confirm:true}]
    :x.kind==='pet'?['jr_pet_fuse',{pets:[x.id,...ps.map(y=>y.id)],main:x.id,confirm:true}]
    :x.kind==='ward'?['jr_pet_wfuse',{k:x.k,r:x.r,confirm:true}]
    :step.mode==='up'?['jr_pet_gear_up',{gear:x.id,confirm:true}]:['jr_pet_gear_fuse',{gears:[x.id,...ps.map(y=>y.id)],confirm:true}];
  busy=true;running=x.id+':one';env.renderSheet();
  let r=null;try{r=await env.cmd(action,payload,{quiet:true});if(r)await pause();}finally{busy=false;running='';}
  if(r){
    const ok=x.kind==='wing'||x.kind==='pet'?!!r.fuse?.ok:!!r.ok,lost=(r.fuse?.lost||r.lost||[]).length;
    const after=ok?itemsOf(api,x.kind).find(y=>x.kind==='ward'?y.pieces.some(p=>p.id===r.item):y.id===(r.fuse?.pet||r.fuse?.main||r.gear||x.id)):null;
    st.res={kind:x.kind,ok,n:1,okN:ok?1:0,spent:step.fee,made:after?[{...after}]:[],lost,fx:!fastFx()};
    if(after)st.sel=after.id;delete st.picks[x.id];st.slot=-1;
  }
  env.renderSheet();
}
async function runMax(env,st,x){
  const {api}=env,mo=maxOf(x),pl=planOf(api,x.kind,mo.scope,mo.pin);if(busy||!pl.n||funds(api)<pl.min)return;
  const b=budgetOf(api,st,x,pl),lose=x.r>=LOSE(api)&&x.kind!=='ward';   // with the pin nothing above its rank
  if(!await ask(env,'⚡ Cường hóa tối đa?',lose?`Tiêu tối đa ${fmt(b)} xu. ⚠️ Từ S trượt mất món phụ. 🔒 Món khóa không bị dùng.`:`Tiêu tối đa ${fmt(b)} xu. 🔒 Món khóa không bị dùng.`,`⚡ Tối đa · ${xu(b)} xu`,Math.min(b,funds(api))))return;
  const [action,payload]=autoCmd(x.kind,mo.scope,mo.pin,b);
  busy=true;running=x.id+':max';env.renderSheet();
  let r=null;try{r=await env.cmd(action,payload,{quiet:true});if(r?.auto)await pause();}finally{busy=false;running='';}
  if(r?.auto){const a=r.auto;st.res={kind:x.kind,ok:a.ok>0,n:a.n,okN:a.ok,spent:a.spent,made:madeOf(api,x.kind,a),fx:!fastFx()};delete st.bud[x.id];}
  env.renderSheet();
}
async function runAll(env,st){
  const {api}=env,plan=allPlan(api,st);if(busy||!plan.length)return;
  const sum=plan.reduce((a,x)=>a+x.b,0),emo=plan.map(p=>KINDS.find(z=>z[0]===p.tab)[1]).join(' ');
  const lose=plan.some(p=>p.pl.sets?.some?.(s=>s.r>=LOSE(api))||p.pl.sets?.some?.(s=>s.g&&s.r>=LOSE(api)));
  if(!await ask(env,'⚡ Ghép tất cả?',lose?`Ghép ${emo}. Tiêu tối đa ${fmt(sum)} xu. ⚠️ Từ S trượt mất món phụ. 🔒 Món khóa không bị dùng.`:`Ghép ${emo}. Tiêu tối đa ${fmt(sum)} xu. 🔒 Món khóa không bị dùng.`,`⚡ Ghép · ≤ ${xu(sum)} xu`,Math.min(sum,funds(api))))return;
  busy=true;running='all';const res={kind:'all',ok:false,n:0,okN:0,spent:0,made:[],fx:!fastFx()};
  try{
    for(let i=0;i<plan.length;i++){
      const p=plan[i],pl=planOf(api,p.kind);if(!pl.n)continue;   // an earlier run may have used the money
      const b=Math.max(pl.min,Math.min(p.b,funds(api)));if(funds(api)<pl.min)continue;
      st.allAt=`${i+1}/${plan.length}`;env.renderSheet();
      const [action,payload]=autoCmd(p.kind,'all',null,b);
      const r=await env.cmd(action,payload,{quiet:true});
      if(r?.auto){const a=r.auto;res.n+=a.n;res.okN+=a.ok;res.spent+=a.spent;res.made.push(...madeOf(api,p.kind,a));}
    }
    if(res.n)await pause();
  }finally{busy=false;running='';st.allAt='';}
  res.ok=res.okN>0;if(res.n)st.res=res;
  env.renderSheet();
}

export async function forgeAction(action,data,el,env){
  const {api,ui}=env,st=S(ui),as=ui.as??={};
  const find=id=>itemsOf(api,kindOf(as.ftab)).find(x=>x.id===id);
  switch(action){
    case'jrFgTab':if(forgeTabs(api).includes(data.tab)){as.ftab=data.tab;st.sel=null;st.slot=-1;}env.renderSheet();return true;   // the tabs stay under the finger
    case'jrFgSel':{const x=data.id&&find(data.id);st.sel=x&&st.sel!==x.id?x.id:null;st.slot=-1;env.renderSheet();if(st.sel)focusPanel();return true;}
    case'jrFgSlot':{const i=Number(data.i);st.slot=st.slot===i?-1:(i===0||i===1?i:-1);env.renderSheet();return true;}
    case'jrFgPick':{const x=st.sel&&find(st.sel),i=Number(data.i);if(!x||!(i===0||i===1))return true;
      const ps=picksOf(api,st,x).map(y=>y?.id);ps[i]=data.id;st.picks[x.id]=ps;st.slot=-1;env.renderSheet();return true;}
    case'jrFgBud':{if(data.id)st.bud[data.id]=Math.max(1,Number(data.n)||0);afterTap(()=>env.renderSheet());return true;}
    case'jrFgAllX':st.allx=[1,2,5].includes(Number(data.x))?Number(data.x):1;env.renderSheet();return true;
    case'jrFgTop':setAutoTop(Number(data.top));env.renderSheet();return true;
    case'jrFgRes':st.res=null;env.renderSheet();return true;
    case'jrFgOne':{const x=find(data.id);if(x)await runOne(env,st,x);return true;}
    case'jrFgMax':{const x=find(data.id);if(x)await runMax(env,st,x);return true;}
    case'jrFgAll':await runAll(env,st);return true;
    case'jrFgLock':{const x=find(data.id);if(!x||busy)return true;
      const ids=x.kind==='ward'?x.pieces.map(p=>p.id):[x.id],on=x.kind==='ward'?!x.pieces.every(p=>p.locked):!lockSet(api).has(x.id);
      busy=true;try{await env.cmd('jr_pet_lock',{ids,on},{quiet:true});}finally{busy=false;}env.renderSheet();return true;}
    case'jrFgMorph':{if(busy)return true;busy=true;try{await env.cmd('jr_pet_morph',{take:data.take==='1'});}finally{busy=false;}env.renderSheet();return true;}
  }
  return false;
}
