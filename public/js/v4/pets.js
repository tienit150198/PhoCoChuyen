/** 🐾 Nuôi thú cưng (game/pets.py): adopt at Góc nhận nuôi Chân Nhỏ, buy at Tiệm Thú Nhỏ Chú Út, care, dress up,
 * photo booth, and the weekly "Bé cưng của tuần" board (GET /api/pets/board). Story mode.
 * Every rule and price lives on the server; this file renders api.state.journey.pets with the static lists
 * (content.journey.pets), draws with ./pet-art.js and sends `jr_pet_*`. Its own dialog, opened with data-action="pets"
 * (data-tab: home | adopt | shop | board) from the menu and the town map's 🐾 door next to the pet shop.
 * Phone first, few words: emoji tabs, one pick per screen, one main button in the bottom bar with the price on it.
 * 🏅 Owner 19/10 (game/pet_tiers.py, journey.pets.petx, content tiers): ranks D…SSS, the work-income bonus of the pet
 * walked, 🧬 fusing three pets (tab lab), five stats with training, 🧰 gear (tab gear) and the 💪 lực chiến board.
 * 🛍️ Owner 21/10 "mua bé hoặc mua linh kiện cho chọn số lượng mua nữa nhé, trang phục cũng thế": the pet shop, the gear
 * shop and the wardrobe shop take a quantity (− N + with quick chips, the total on the main button); one command, one
 * charge, `qty` sent only above 1 (an older server, whose content has no qty limits, draws no picker).
 * Styles: /css/pets.css. */
import {icon,escapeHTML as esc} from '../icons.js';
import {shortNum} from './wealth.js';
import {paint as sheetPaint} from './sheet-paint.js';
import {lookOf,figureSVG} from './look.js';
import {petSVG,petPicture,lookup,accOf,fxRef} from './pet-art.js';
import {qtyBox,QTY,afterTap} from '../qty-input.js';
import {noAsk} from './no-ask.js';
import {askBuy} from './payment.js';   // 🛍️ Cửa hàng: a small purchase (or any, ☑️ Không hỏi lại) goes straight through (shopAsk)

// owner 19/10 "chưa thấy chỗ mua cánh, đổi pets dắt đi như nào cũng k biết, làm dễ hiểu hơn": every tab says its name
const TABS=[['home','🐾','Bé nhà mình','Bé nhà'],['shop','🛍️','Tiệm thú cưng','Tiệm'],['ward','👗','Tủ đồ của bé','Tủ đồ'],['lab','🧬','Ghép bé','Ghép'],
  ['gear','🧰','Linh kiện','Linh kiện'],['adopt','🏠','Nhận nuôi','Nhận nuôi'],['board','🏆','Bảng xếp hạng','Xếp hạng']];
const NEEDS=[['f','🍚','No'],['j','💛','Vui'],['cl','🫧','Sạch'],['h','❤️','Khỏe']];
const MOOD={vui:'😊',on:'🙂',buon:'🥺'};
const S={dlg:null,env:null,tab:'home',sub:'',pet:'',kind:'dog',breed:'',coat:0,item:'',food:'hat',toy:'',clean:'bath',vet:'kham',slot:'head',
  shelter:-1,nick:'',donate:0,pose:'happy',frame:'nang',board:null,boardAt:0,busy:false,flash:null,listening:false,
  stat:'spd',gslot:'giay',fz:[],fzMix:false,fzBreed:'',gv:'bag',g:'',gbslot:'giay',gmodel:0,grank:0,bkind:'week',ff:{k:'',r:'',at:''},
  wk:'',wrank:0,wslot:'',wsel:'',wfslot:'',bq:1,wascope:'all',watop:6,wabud:0,wres:null,lascope:'all',latop:4,labud:0,lres:null,gascope:'all',gatop:6,gabud:0,gres:null,
  host:null,part:null};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const J=()=>S.env?.api?.state?.journey||{};
const V=()=>J().pets;
const CAT=()=>S.env?.api?.content?.journey?.pets||null;
const breedOf=id=>(CAT()?.breeds||[]).find(b=>b.id===id);
const cash=()=>Number(J().wallet)||0;
const ready=()=>cash()<0?0:cash()+(Number(J().bank?.balance)||0);
const readyWhy=price=>!price?'':cash()<0?'Ví đang nợ':ready()>=price?'':`Còn thiếu ${fmt(price-ready())} xu`;
const POCKET=['wallet','account'];
/* 🏅 ranks, stats, gear (game/pet_tiers.py): journey.pets.petx and content.journey.pets.tiers; an older server: none */
const X=()=>V()?.petx||null;
const TT=()=>CAT()?.tiers||null;
/** What petSVG draws besides the pet: rank, coat effect, a 🌟 legendary that kept its breed, the ranks of what it wears
 * (wr), its cute aura (wo) and a whole set (wst): game/pet_wardrobe.py pet_extra. */
const fxOf=p=>p?{r:p.r||0,x:p.fx??p.x??'',lg:!!p.legend&&breedOf(p.b)?.fuse!=='legend',wr:p.wr||null,o:p.wo||0,st:p.wst||''}:{};
/* 👗 the wardrobe (game/pet_wardrobe.py): content.journey.pets.wardrobe and journey.pets.petw */
const WARD=()=>CAT()?.wardrobe||null;
const wItem=id=>(WARD()?.items||[]).find(i=>i.id===id)||null;
const myItems=()=>V()?.petw?.it||[];
const RKS=['D','C','B','A','S','SS','SSS'];
const RK=r=>`<span class="pt-rk r${r}">${RKS[r]||''}</span>`;
const slotName=id=>(WARD()?.slots||[]).find(x=>x.id===id)?.name||'';
const wPrice=(it,r)=>it.price*(r?(WARD()?.c_mult||4):1);
const RNAME=r=>TT()?.ranks?.[r]?.rank||'';
/** A pet's rank badge (D grey … SSS rainbow; 🌟 a legendary). */
const rankTag=p=>p&&Number.isInteger(p.r)&&TT()?`<span class="pt-rank r${p.r}${p.legend?' lg':''}" title="Hạng ${esc(RNAME(p.r))} · ${esc(TT().ranks[p.r].name)}">${p.legend?'🌟':''}${esc(RNAME(p.r))}</span>`:'';
const fxName=id=>(TT()?.fx||[]).find(f=>f.id===id);
const lifeDay=()=>Number(J().life_day)||1;

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
export function petPic(cat,p,pose='sit',size=72,acc=null,fx=null){
  const L=lookup(cat,p?.b,p?.c);if(!L)return `<span class="pt-unknown" aria-hidden="true">🐾</span>`;
  return petPicture(L.breed,L.coat,pose,acc??p.w??{},size,'pet-svg',fx??fxOf(p));
}
/** The pet picked (or a default one) trying piece `id` of rank r on. */
function tryOn(id,r=0,size=96){
  const it=wItem(id),p=cur()||{b:'meo_muop',c:1,w:{}};if(!it)return '';
  const w={...(p.w||{}),[it.slot]:id},f=fxOf(p);f.wr={...(f.wr||{}),[it.slot]:r};
  return petPic(CAT(),{...p,w},it.slot==='bed'?'sleep':'sit',size,w,f);
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
  d.addEventListener('input',e=>{if(e.target.name!=='nick')return;S.nick=e.target.value;
    // ✓ Đổi tên is drawn disabled while the name is unchanged: wake it as the player types (#446), no re-render (keeps the caret)
    if(S.sub==='more'){const b=d.querySelector('.pt-main'),p=cur(),v=S.nick.trim();if(b&&p)b.disabled=S.busy||!v||v===p.n;}});
  // ⚡ Cường hóa nhanh's two pickers (which ones, up to which rank): a new pick drops a typed budget back to the estimate
  d.addEventListener('change',e=>{const el=e.target.closest?.('[data-pt-sel]');if(el&&d.contains(el)&&autoPick(el))render();});
  d.addEventListener('close',()=>{S.flash=null;S.sub='';});
  S.dlg=d;return d;
}
export async function openPets(env,tab,kind){
  S.env=env;S.host=null;S.part=null;   // the dialog again, not 🛍️ Cửa hàng / ⚒️ Cường hóa's shelves (petEmbedHTML)
  if(!S.listening){
    S.listening=true;
    let seen='';env.api.addEventListener('state',()=>{if(!S.dlg?.open)return;const key=JSON.stringify([J().wallet,J().pets,J().bank?.balance]);if(key===seen)return;seen=key;if(!S.busy)render();});   // closed: no work per command
  }
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();
  S.tab=TABS.some(t=>t[0]===tab)?tab:(V()?.pets?.length?'home':'adopt');S.sub='';S.flash=null;
  if(kind&&S.tab==='shop'){S.kind=kind;S.wk='';}   // 🪽 Có gì mới → the wings shelf
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
  if(S.tab==='board')loadBoard();
}
export async function petsAction(action,data,el,env){
  if(action!=='pets')return false;
  await openPets(env,data?.tab,data?.kind);return true;
}

async function loadBoard(force=false){
  if(!force&&S.board&&Date.now()-S.boardAt<15000)return;
  S.boardAt=Date.now();
  try{S.board=await S.env.api.json('/api/pets/board'+(S.bkind==='power'?'?kind=power':''));}catch{S.board=S.board||{error:true};}
  if(S.dlg?.open&&S.tab==='board')render();
}
async function send(action,payload={}){
  const {api}=S.env;S.busy=true;render();
  try{
    const r=await api.command(action,payload);
    S.flash={text:[r.message,...(r.effects||[]).filter(Boolean)].filter(Boolean).join(' '),kind:'good'};
    const f=S.flash;setTimeout(()=>{if(S.flash===f&&!S.busy){S.flash=null;if(S.dlg?.open||S.host)render();}},6000);   // good news fades (the bank's way)
    return r;
  }catch(e){S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;render();}
}
const ask=(title,msg,label,cost)=>S.env.confirmAction?S.env.confirmAction(title,msg,label,cost?{cost,pocket:POCKET}:undefined):Promise.resolve(confirm(msg));
// ☑️ Không hỏi lại (⚒️ Cường hóa's tick, v4/no-ask.js): on the sheet's shelves a ghép / cường hóa acts at once
const askForge=(...a)=>S.host&&noAsk()?Promise.resolve(true):ask(...a);

/* ---- picks ---- */
const pets=()=>V()?.pets||[];
const cur=()=>pets().find(p=>p.id===S.pet)||pets()[0]||null;
const shelterPick=()=>(V()?.shelter||[]).find(a=>a.i===S.shelter&&!a.taken)||null;
const breedList=()=>(CAT()?.breeds||[]).filter(b=>b.kind===S.kind&&b.shop!==false);
const shopItems=()=>[...(CAT()?.toys||[])];
const own=id=>Number(V()?.own?.[id])||0;
const wornBy=id=>pets().filter(p=>Object.values(p.w||{}).includes(id)).length;
const groomPrice=p=>p?.kind==='cat'?CAT().groom.cat:CAT().groom.price;
/** Home, kennel or at the grandparents': every pet of this save, with where it is. */
const allPets=()=>[...pets().map(p=>({...p,at:'home'})),...(X()?.ken||[]).map(p=>({...p,at:'ken'})),...(V()?.farm||[]).map(p=>({...p,at:'farm'}))];
const petName=id=>allPets().find(p=>p.id===id)?.n||'';
/** The pet picked on the 📋 list when it is not at home (kennel, grandparents'), or null. */
const away=()=>S.pet&&allPets().find(p=>p.id===S.pet&&p.at!=='home')||null;
/** Home full and the kennel too: no room for a new pet. */
const noRoom=()=>pets().length>=CAT().max&&(!TT()||(X()?.ken||[]).length>=TT().limits.kennel);
const roomWhy=()=>noRoom()?'Nhà và trại nuôi đều đầy':'';
/* 🛍️ How many one purchase takes (owner 21/10): the server's limit (content: pets buy_qty, tiers.limits.gear_qty,
 * wardrobe.qty_max) and the room left; 1 on an older server. The server checks it all again. */
const roomLeft=()=>Math.max(0,CAT().max-pets().length)+(TT()?Math.max(0,TT().limits.kennel-(X()?.ken||[]).length):0);
function qtyCap(){
  if(S.tab==='shop'&&(S.kind==='wear'||S.kind==='wing')){const W=WARD();return W?.qty_max?Math.max(0,Math.min(W.qty_max,(W.limit||150)-myItems().length)):1;}
  if(S.tab==='shop'&&S.kind==='toy'){const it=shopItems().find(x=>x.id===S.item);return it&&it.uses!==0&&CAT()?.item_qty||1;}   // 🎾 owner 23/10: many at once (a kept toy: one)
  if(S.tab==='shop'){const n=CAT()?.buy_qty;return n?Math.min(n,roomLeft()):1;}
  if(S.tab==='gear'){const t=TT(),n=t?.limits?.gear_qty;return n?Math.max(0,Math.min(n,t.limits.gear-(X()?.gear||[]).length)):1;}
  return 1;
}
const bq=()=>Math.max(1,Math.min(S.bq,qtyCap()));
/** The names one purchase of q pets gives (game/pets.py _nth_name): Mây, Mây 2, Mây 3 … */
const nthName=(n,i)=>{if(!i)return n;const tail=` ${i+1}`;return (n.slice(0,16-tail.length).trimEnd()||n.slice(0,1))+tail;};
const nameHint=(n,q)=>q<=3?Array.from({length:q},(_,i)=>nthName(n,i)).join(', '):`${nthName(n,0)}, ${nthName(n,1)} … ${nthName(n,q-1)}`;
const times=q=>q>1?` ×${q}`:'';
/** − N + with ×1 ×3 ×5 ×10 and "Tối đa" (what the room and the money allow), and the sum; nothing when only one fits. */
function qtyPick(price){
  const cap=qtyCap();if(cap<=1)return '';
  const q=bq(),most=Math.max(1,Math.min(cap,price>0?Math.floor(ready()/price):cap));
  const quick=[1,3,5,10].filter(n=>n<cap&&n!==most);
  return `<div class="pt-qty" role="group" aria-label="Số lượng mua"><div class="pt-qty-row"><span class="pt-qty-l">Số lượng</span><span class="pt-qty-step">`
    +`<button type="button" class="pt-qty-b" data-pt="bq" data-n="${q-1}"${q<=1?' disabled':''} aria-label="Bớt một">−</button>`
    +qtyBox({value:q,min:1,max:cap,label:'Số lượng mua',go:`data-pt="bq" data-n="${QTY}"`})
    +`<button type="button" class="pt-qty-b" data-pt="bq" data-n="${q+1}"${q>=cap?' disabled':''} aria-label="Thêm một">+</button></span></div>`
    +`<div class="pt-chips pt-qty-chips">${quick.map(n=>chip('bq',{n},q===n,`×${n}`)).join('')}${chip('bq',{n:most},q===most,`Tối đa ×${most}`)}</div>`
    +`<p class="pt-qty-sum">${q} × ${fmt(price)} xu = <b>${fmt(price*q)} xu</b></p></div>`;
}
/** 🧬 The fusion picked (S.fz, the first is the 👑 main pet that goes up and keeps its breed, owner 19/10): {ps, low,
 * fee, recipe, lose} or null. The odds stay on the server (owner 19/10 "đừng show tỷ lệ ra"). */
function fusion(){
  const t=TT();if(!t)return null;const all=allPets(),ps=S.fz.map(id=>all.find(p=>p.id===id)).filter(Boolean);if(ps.length!==3)return {ps};
  const rk=ps.map(p=>p.legend?6:p.r||0),low=Math.min(...rk),fee=t.ranks[low].fee;
  const ids=ps.map(p=>p.b).sort(),recipe=low<6&&(t.recipes||[]).find(r=>[...r.of].sort().join()===ids.join());
  // owner 19/10 "khi lên thì được chọn giữ bé hiện tại hoặc đổi giống": its own, the two others', a legendary breed
  const kind=breedOf(ps[0].b)?.kind,choices=[...new Set([ps[0].b,...ps.slice(1).map(p=>p.b).filter(b=>breedOf(b)?.fuse!=='legend'||low===6),...(low===6&&t.legend?.[kind]?[t.legend[kind]]:[])])];
  return {ps,low,fee,recipe:recipe||null,choices,lose:low>=(t.limits.lose_from??4),why:low===6&&ps[0].legend?'Bé chính đã là huyền thoại: chọn bé SSS khác làm bé chính':''};
}
/** Why this pet cannot join a fusion now ('' when it can). */
function fuseWhy(p){
  if(p.at==='home'&&p.mood==='buon')return 'Bé đang buồn';
  return '';
}
const gearOf=id=>(X()?.gear||[]).find(g=>g.id===id)||null;
/** Two more gears of the same kind and rank, not worn, to fuse with `g` (the lowest levels first), or null.
 * `g` itself may be worn: it goes up in place (owner 19/10: it must be +10 first, see gearUp). */
function gearMates(g){
  if(!g||g.r>=6)return null;
  const m=(X()?.gear||[]).filter(x=>x.id!==g.id&&!x.on&&x.s===g.s&&x.r===g.r).sort((a,b)=>a.lv-b.lv).slice(0,2);
  return m.length===2?m:null;
}
/** 📈 How `g` goes up a rank: {next, max (at +lv_max), have (free mates, ≤2), ok, lose (a failure loses the two), fee}. */
function gearUp(g){
  const t=TT();if(!t||!g||g.r>=6)return null;
  const have=(X()?.gear||[]).filter(x=>x.id!==g.id&&!x.on&&x.s===g.s&&x.r===g.r).length,max=g.lv>=t.gear.lv_max;
  return {next:RNAME(g.r+1),max,have:Math.min(2,have),ok:max&&have>=2,lose:g.r>=(t.limits.lose_from??4),fee:t.gear.fuse_fee[g.r]};
}
/** 👗 What ⚡ Cường hóa nhanh of the clothes (jr_pet_wfuse_auto) finds now, as game/pet_wardrobe.py triples sees it: three of one piece and
 * rank not worn, the result at most rank `top`. {sets [{k, r, t triples}] lowest rank first, n triples, est the first
 * round's fees (each triple once), min the cheapest fee}. The odds stay on the server. */
function autoPlan(scope=S.wascope,top=S.watop){
  const W=WARD(),m=new Map(),order=(W?.items||[]).map(i=>i.id);
  for(const i of myItems()){if(i.on||i.r>=Math.min(top,6)||(scope!=='all'&&i.k!==scope)||!wItem(i.k))continue;const key=`${i.k}|${i.r}`;m.set(key,(m.get(key)||0)+1);}
  const sets=[...m].filter(([,n])=>n>=3).map(([key,n])=>{const [k,r]=key.split('|');return {k,r:Number(r),t:Math.floor(n/3)};})
    .sort((a,b)=>a.r-b.r||order.indexOf(a.k)-order.indexOf(b.k));
  const fee=r=>Number(W?.fee?.[r])||0;
  return {sets,n:sets.reduce((a,x)=>a+x.t,0),est:sets.reduce((a,x)=>a+x.t*fee(x.r),0),min:sets.length?Math.min(...sets.map(x=>fee(x.r))):0};
}
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
    return [`🏠 Nhận nuôi${S.donate?` · ủng hộ ${fmt(S.donate)} xu`:''}`,'adopt',roomWhy()||readyWhy(S.donate)];}
  if(S.tab==='shop'){
    if(S.kind==='wear'||S.kind==='wing'){const it=wItem(S.wk);if(!it)return ['👆 Chọn một món để xem','',' '];const q=bq(),pr=wPrice(it,S.wrank)*q;
      return [`🛍️ Mua hạng ${RKS[S.wrank]}${times(q)} · ${fmt(pr)} xu`,'wbuy',myItems().length>=(WARD()?.limit||150)?'Tủ đồ đầy rồi':readyWhy(pr)];}
    if(S.kind==='toy'){const it=shopItems().find(x=>x.id===S.item);if(!it)return ['Chọn một món','',' '];
      const q=bq();return [`Mua${times(q)} · ${fmt(it.price*q)} xu`,'buy',it.uses===0&&own(it.id)?'Có rồi':readyWhy(it.price*q)];}
    const b=breedOf(S.breed);if(!b)return ['Chọn một giống','',' '];const q=bq();
    return [`Đón về${times(q)} · ${fmt(b.price*q)} xu`,'shopbuy',roomWhy()||readyWhy(b.price*q)];
  }
  if(S.tab==='lab'){const f=fusion();if(!f)return ['','',''];if(f.ps.length<3)return [`🧬 Chọn ${3-f.ps.length} bé nữa`,'',' '];
    return [`🧬 Ghép · ${fmt(f.fee)} xu`,'fuse',f.why?'Chọn bé chính khác':readyWhy(f.fee)];}
  if(S.tab==='gear'){const t=TT();if(!t)return ['','',''];
    if(S.gv==='buy'){const r=Math.min(S.grank,t.gear.shop.length-1),m=t.gear.models[S.gbslot]?.[S.gmodel],q=bq(),pr=t.gear.shop[r]*(m?.mult||1)*q;return [`🛍️ Mua${times(q)} · ${fmt(pr)} xu`,'gbuy',(X()?.gear||[]).length>=t.limits.gear?'Túi đầy rồi':readyWhy(pr)];}
    const g=gearOf(S.g);if(!g)return ['Chọn một món','',' '];
    if(g.lv<t.gear.lv_max)return [`✨ Cường hóa · ${fmt(g.up_fee)} xu`,'gup',readyWhy(g.up_fee)];
    const u=gearUp(g);   // at +10: the main button ranks it up (owner 19/10)
    return !u?['👑 Đã tối đa','',' ']:u.ok?[`📈 Lên hạng ${u.next} · ${fmt(u.fee)} xu`,'gfuse',readyWhy(u.fee)]:[`📈 Cần thêm ${2-u.have} món hạng ${g.rank}`,'',' '];}
  if(S.tab==='board')return ['🐾 Bé nhà mình','tohome',''];
  if(S.tab==='ward')return ['','',''];
  if(S.sub==='all'||away())return ['','',''];
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
    case'equip':return ['✓ Xong','back',''];
    case'train':{const t=TT();if(!t)return ['✓ Xong','back',''];const i=t.stats.findIndex(s=>s.id===S.stat),st=t.stats[i]||t.stats[0],fee=t.ranks[p.r||0].train;
      return [`${st.emoji} Luyện ${st.name.toLowerCase()} · ${fmt(fee)} xu`,'train',(p.tn?.[i]||0)>=t.limits.train_max?'Đã luyện tối đa':(X()?.today?.train||0)>=t.limits.train_day?'Hôm nay luyện đủ rồi':p.mood==='buon'?'Bé đang buồn':readyWhy(fee)];}
  }
  const [sub,e,l]=nextCare(p);return [`${e} ${l}`,'sub:'+sub,''];
}

async function onClick(op,data){
  const c=CAT(),p=cur();
  switch(op){
    case'close':S.dlg.close();return;
    case'bq':S.bq=Math.max(1,Math.min(Number(data.n)||1,qtyCap()));afterTap(render);return;
    case'tab':S.tab=data.tab;S.sub='';S.flash=null;S.bq=1;if(data.kind){S.kind=data.kind;S.wk='';}if(data.wslot!==undefined)S.wslot=data.wslot;render();top();if(S.tab==='board')loadBoard();return;
    case'wk':S.wk=data.id||'';S.wrank=0;S.bq=1;render();if(S.wk)top();return;
    case'wrank':S.wrank=Number(data.r)||0;render();return;
    case'wslot':S.wslot=data.slot||'';S.wk='';render();return;
    case'wfslot':S.wfslot=data.slot||'';S.wsel='';render();return;
    case'wsel':S.wsel=S.wsel===data.key?'':data.key;render();return;
    case'wput':{const [k,r]=data.key.split('|'),it=wItem(k),mine=myItems().filter(i=>i.k===k&&i.r===Number(r));if(!it||!mine.length)return;
      const one=mine.find(i=>!i.on)||mine.find(i=>i.on!==data.pet)||mine[0];
      send('jr_pet_wwear',{pet:data.pet,slot:it.slot,item:one.on===data.pet?null:one.id});return;}
    case'wwear':{const p=cur();if(!p)return;send('jr_pet_wwear',{pet:p.id,slot:data.slot,item:data.id||null});return;}
    case'wfuse':{const [k,r]=S.wsel.split('|'),it=wItem(k),W=WARD(),rr=Number(r),fee=W.fee[rr];if(!it)return;
      if(!await askForge(`Ghép ba ${it.name} hạng ${RKS[rr]}?`,`Thành công: ra một ${it.name} hạng ${RKS[rr+1]}${rr>=3?' (có khi ra món 💎 dòng sang)':''}. Trượt: ba món vẫn còn, mất phí. Món đang mặc sẽ được tháo ra.`,`🔀 Ghép · ${fmt(fee)} xu`,fee))return;
      const res=await send('jr_pet_wfuse',{k,r:rr,confirm:true});if(res?.ok){const n=myItems().find(i=>i.id===res.item);S.wsel=n?`${n.k}|${n.r}`:'';}else if(res)S.flash={...S.flash,kind:'bad'};render();return;}
    case'abud':{const k=AK[data.kind];if(!k)return;S[k.bud]=Math.max(1,Number(data.n)||0);afterTap(render);return;}
    case'ares':{const k=AK[data.kind];if(k)S[k.res]=null;render();return;}
    case'auto':return runAuto(data.kind);
    case'wdrop':{const [k,r]=S.wsel.split('|'),it=wItem(k);if(!it)return;if(!await ask(`Bỏ một ${it.name}?`,`${it.name} hạng ${RKS[r]} sẽ mất hẳn.`,'🗑️ Bỏ'))return;
      await send('jr_pet_wdrop',{k,r:Number(r),confirm:true});if(!myItems().some(i=>`${i.k}|${i.r}`===S.wsel))S.wsel='';render();return;}
    case'fzbreed':S.fzBreed=data.id||'';render();return;
    case'morph':{const r=await send('jr_pet_morph',{take:data.take==='1'});if(r?.morph){S.pet=r.morph.pet;S.flash={...S.flash,kind:'good win'};}render();return;}
    case'pet':S.pet=data.id;S.sub='';render();return;
    case'pick':S.pet=data.id;S.sub='';render();top();return;
    case'ff':S.ff[data.key]=data.val;render();return;
    case'sub':S.sub=data.sub;S.flash=null;if(S.sub==='more')S.nick=p?.n||'';render();top();return;
    case'back':S.sub='';render();return;
    case'kind':S.kind=data.kind;S.bq=1;S.breed='';S.item='';S.wk='';S.wslot='';render();return;
    case'breed':S.breed=data.id;S.coat=0;S.bq=1;S.nick=S.nick||'';render();return;
    case'coat':S.coat=Number(data.c)||0;render();return;
    case'item':S.item=data.id;S.bq=1;render();return;
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
    case'stat':S.stat=data.id;render();return;
    case'gslot':S.gslot=data.slot;render();return;
    case'gwear':if(p)send('jr_pet_gear_wear',{pet:p.id,slot:S.gslot,gear:data.id||null});return;
    case'fz':{const i=S.fz.indexOf(data.id);if(i>=0)S.fz.splice(i,1);else if(S.fz.length<3)S.fz.push(data.id);S.fzBreed='';render();return;}
    case'fzmain':{const i=S.fz.indexOf(data.id);if(i>0){S.fz.splice(i,1);S.fz.unshift(data.id);}S.fzBreed='';render();return;}
    case'fzmix':S.fzMix=!S.fzMix;render();return;
    case'kennel':{const r=await send('jr_pet_kennel',{pet:data.id,to:data.to,...(data.swap?{swap:data.swap}:{}),...(data.walk?{walk:true}:{})});
      if(r){S.fz=S.fz.filter(id=>id!==data.id);if(data.to==='home'&&S.tab==='home'){S.pet=data.id;render();}}return;}
    case'gv':S.gv=data.v;S.g='';S.bq=1;render();top();return;
    case'gsel':S.g=S.g===data.id?'':data.id;render();return;
    case'gpick':{const l=(X()?.gear||[]).filter(x=>x.s===data.slot&&x.r===Number(data.r)).sort((a,b)=>b.lv-a.lv||(a.on?1:0)-(b.on?1:0));if(l[0]){S.g=l[0].id;render();}return;}
    case'gshop':S.gv='buy';S.gbslot=data.slot;S.grank=Number(data.r)||0;S.gmodel=0;S.g='';S.bq=Number(data.n)||1;   // the mates still missing
      if(S.host){S.part='gear';S.env.act?.('jrAccShop',{tab:'pgear'});return;}   // ⚒️ Cường hóa → 🛍️ Cửa hàng's 🧰 shelf, this pick kept
      render();top();return;
    case'forge':S.dlg?.close?.();S.env?.act?.('jrForge',{tab:data.tab});return;   // ⚒️ Cường hóa, in the journey sheet
    case'gbslot':S.gbslot=data.slot;S.gmodel=0;render();return;
    case'gmodel':S.gmodel=Number(data.m)||0;render();return;
    case'grank':S.grank=Number(data.r)||0;render();return;
    case'stroll':{const r=await send('jr_pet_stroll',{});if(r?.found){S.gv='bag';S.g=r.found;render();}return;}
    case'gfuse':{const g=gearOf(S.g),m=gearMates(g),u=gearUp(g);if(!m||!u?.ok)return;const fee=u.fee;
      if(!await askForge(`Lên hạng ${g.name} ${g.rank} → ${u.next}?`,`Dùng thêm hai món ${g.rank} cùng loại. Thành công: ${g.name} lên hạng ${u.next}, về +0. Trượt: ${u.lose?`mất hai món nguyên liệu, ${g.name} vẫn còn.`:'ba món vẫn còn, chỉ mất phí.'}`,`📈 Lên hạng · ${fmt(fee)} xu`,fee))return;
      const r=await send('jr_pet_gear_fuse',{gears:[g.id,...m.map(x=>x.id)],confirm:true});if(r){if(r.ok===false)S.flash={...S.flash,kind:'bad'};S.g=r.gear||S.g;render();}return;}
    case'gdrop':{const g=gearOf(S.g);if(!g)return;if(!await ask(`Bỏ ${g.name}?`,`${g.name} ${g.rank}${g.lv?` +${g.lv}`:''} sẽ mất hẳn.`,'🗑️ Bỏ'))return;
      const r=await send('jr_pet_gear_drop',{gear:g.id,confirm:true});if(r){S.g='';render();}return;}
    case'bkind':S.bkind=data.k;S.board=null;render();loadBoard(true);return;
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
    case'shopbuy':{const b=breedOf(S.breed);if(!b)return;const nick=(S.nick||b.nick||b.name).trim().slice(0,16),q=bq(),pr=b.price*q;
      if(shopAsk(pr)&&!await ask(q>1?`Đón ${q} bé ${b.name} về?`:`Đón bé ${b.name} về?`,`${q>1?`${q} × ${fmt(b.price)} xu = ${fmt(pr)} xu, trả`:`Trả ${fmt(pr)} xu`} một lần. Ví trước, thiếu thì lấy từ tài khoản.${q>1?` Tên: ${nameHint(nick,q)}.`:''}`,`Đón về${times(q)} · ${fmt(pr)} xu`,pr))return;
      const r=await send('jr_pet_adopt',{from:'shop',breed:b.id,coat:S.coat,nick,...(q>1?{qty:q}:{}),confirm:true});if(r){S.tab='home';S.pet='';S.breed='';S.bq=1;render();}return;}
    case'wbuy':{const it=wItem(S.wk);if(!it)return;const q=bq(),one=wPrice(it,S.wrank),pr=one*q;
      if(shopAsk(pr,pr>=1000)&&!await ask(`Mua ${it.name} hạng ${RKS[S.wrank]}${times(q)}?`,`${q>1?`${q} × ${fmt(one)} xu = ${fmt(pr)} xu, trả một lần`:`Trả ${fmt(pr)} xu`}. Mua xong mặc cho bé ở 👗 Diện hoặc nút "Mặc luôn".`,`🛍️ ${fmt(pr)} xu`,pr))return;
      if(await send('jr_pet_wbuy',{id:it.id,...(S.wrank?{rank:S.wrank}:{}),...(q>1?{qty:q}:{}),confirm:true})){S.bq=1;render();}return;}
    case'buy':{const it=shopItems().find(x=>x.id===S.item);if(!it)return;const q=bq(),pr=it.price*q;
      if(shopAsk(pr,pr>=500||q>1)&&!await ask(`Mua ${it.name}${times(q)}?`,`${q>1?`${q} × ${fmt(it.price)} xu = `:'Trả '}${fmt(pr)} xu, trả một lần.`,`Mua · ${fmt(pr)} xu`,pr))return;
      if(await send('jr_pet_buy',{id:it.id,...(q>1?{qty:q}:{}),confirm:true})){S.bq=1;render();}return;}
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
    case'train':await send('jr_pet_train',{pet:p.id,stat:S.stat});return;
    case'fuse':{const f=fusion();if(!f||f.ps.length!==3||f.why)return;const m=f.ps[0],mix=S.fzMix&&!!f.recipe,two=f.ps.slice(1).map(p=>p.n).join(' và ');
      const to=f.choices.includes(S.fzBreed)?S.fzBreed:m.b,bn=to===m.b?'giữ nguyên giống':`thành giống ${breedOf(to)?.name||''}`;
      const win=f.low===6?`${m.n} thành 🌟 huyền thoại, ${bn}`:`${m.n} lên hạng ${RNAME(f.low+1)}, ${bn}`;
      if(!await askForge('Ghép ba bé?',`Thành công: ${mix?`có thể ra bé giống lai (ba bé về quê với bà), không thì ${win}`:win}; ${two} về quê với bà. Trượt: ${f.lose?`⚠️ ${two} sẽ mất, ${m.n} ở lại`:'ba bé vẫn ở lại'}, mất phí.`,`🧬 Ghép · ${fmt(f.fee)} xu`,f.fee))return;
      const r=await send('jr_pet_fuse',{pets:[...S.fz],main:m.id,...(mix?{mix:true}:{}),...(to!==m.b?{breed:to}:{}),confirm:true});
      if(r?.fuse){if(r.fuse.ok){S.fz=[];S.fzMix=false;S.fzBreed='';if(pets().some(x=>x.id===r.fuse.pet))S.pet=r.fuse.pet;S.flash={...S.flash,kind:'good win'};}
        else{const lost=r.fuse.lost||[];S.fz=S.fz.filter(id=>!lost.includes(id));S.flash={...S.flash,kind:'bad'};}render();}
      return;}
    case'gup':{const g=gearOf(S.g);if(!g)return;
      if(g.up_fee>=1000&&!await askForge(`Cường hóa ${g.name}?`,`Trượt: món đồ vẫn nguyên, mất phí.`,`✨ ${fmt(g.up_fee)} xu`,g.up_fee))return;
      const r=await send('jr_pet_gear_up',{gear:g.id,confirm:true});if(r?.ok===false){S.flash={...S.flash,kind:'bad'};render();}return;}
    case'gbuy':{const t=TT(),r=Math.min(S.grank,t.gear.shop.length-1),m=t.gear.models[S.gbslot]?.[S.gmodel];if(!m)return;const q=bq(),one=t.gear.shop[r]*(m.mult||1),pr=one*q;
      if(shopAsk(pr,pr>=1000)&&!await ask(`Mua ${m.name} hạng ${RNAME(r)}${times(q)}?`,q>1?`${q} × ${fmt(one)} xu = ${fmt(pr)} xu, trả một lần.`:`Trả ${fmt(pr)} xu.`,`🛍️ ${fmt(pr)} xu`,pr))return;
      const res=await send('jr_pet_gear_buy',{slot:S.gbslot,model:S.gmodel,rank:r,...(q>1?{qty:q}:{}),confirm:true});if(res){S.gv='bag';S.g='';S.bq=1;render();}return;}
  }
}

/* ---- rendering ---- */
const top=()=>S.host?document.querySelector('#sheet .pt-embed')?.scrollIntoView?.({block:'start'}):S.dlg?.querySelector('.pt-body')?.scrollTo?.(0,0);
function render(){
  if(S.host){if(document.querySelector('#sheet .pt-embed'))S.env?.renderSheet?.();return;}   // 🛍️ ⚒️ inside the sheet: the sheet redraws where the player is (owner 23/10: no jump to the top)
  if(!S.dlg)return;
  const root=S.dlg.querySelector('.pt-root'),html=page();
  S.dlg.setAttribute('aria-busy',String(S.busy));
  if(root._html===html&&root.firstChild)return;   // 🐢 the same screen (a state that did not change it): nothing rebuilt
  sheetPaint(root,html,'.pt-body');root._html=html;   // typing a pet's name while the wallet moves: the keyboard stays
}
function page(){
  const v=V(),c=CAT(),t=TABS.find(x=>x[0]===S.tab)||TABS[0];
  const head=`<header class="sheet-head pt-head">${S.sub?`<button class="icon-btn" type="button" data-pt="back" aria-label="Quay lại">${icon('back',21)}</button>`:`<span class="pt-logo" aria-hidden="true">${t[1]}</span>`}<div class="grow"><h2 id="pt-title">${esc(t[2])}</h2></div>
    <span class="pt-wallet" title="Ví">👛 ${fmt(Math.max(0,J().wallet||0))}</span><button class="icon-btn" type="button" data-pt="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  if(!v||!c)return head+`<div class="sheet-body pt-body"><p class="pt-empty">⏳</p></div>`;   // an older server
  if(!v.story)return head+`<div class="sheet-body pt-body"><p class="pt-empty">Chỉ có trong hành trình.</p></div>`;
  const tabs=S.sub?'':`<nav class="pt-tabs" role="tablist" aria-label="Thú cưng">${TABS.map(([id,e,l,sh])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" aria-label="${esc(l)}" title="${esc(l)}" class="${S.tab===id?'on':''}" data-pt="tab" data-tab="${id}"><span aria-hidden="true">${e}</span><small>${esc(sh)}</small></button>`).join('')}</nav>`;
  const inner=S.tab==='adopt'?adopt(v,c):S.tab==='shop'?shop(v,c):S.tab==='board'?board(c):S.tab==='lab'?lab(v,c):S.tab==='gear'?gear(v,c):S.tab==='ward'?ward(v,c):home(v,c);
  const [label,,why]=main();
  const w=why&&why.trim();
  const bar=label?`<footer class="pt-bar">${w?`<small class="pt-why">${esc(why)}</small>`:''}<button type="button" class="btn primary big pt-main" data-pt="go"${S.busy||w||why===' '?' disabled':''}>${esc(label)}</button></footer>`:'';
  const flash=`<p class="pt-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  return head+tabs+`<div class="sheet-body pt-body">${flash}${S.sub||S.tab==='board'?'':myth(c)}${inner}</div>`+bar;
}
/* 🛍️ Cửa hàng and ⚒️ Cường hóa (v4/acc-shop.js, owner 23/10 "shop riêng", "cửa hàng hoặc shop đều là 1", "Cường hóa …
 * có cường hóa nhanh"): this dialog's shelves drawn inside the journey sheet, the same views, picks and jr_pet_* commands (S is
 * shared; S.host 'sheet' while they are there: render() redraws the sheet, clicks come in by bindSheet). The dialog keeps
 * every tab. `part`: buy (🐶🐱 a pet) | wear (👗) | wing (🪽) | toy (🎾) | gear (🧰 buy) in the shop; lab (🧬 ghép thú) |
 * ward (👗 ghép đồ) | gearup (🧰 cường hóa, lên hạng) in Cường hóa. */
let bound=false;
function bindSheet(){
  if(bound||typeof document==='undefined')return;bound=true;
  document.addEventListener('click',e=>{
    const el=e.target.closest?.('#sheet .pt-embed [data-pt]');if(!el||el.disabled||!S.host)return;
    e.preventDefault();onClick(el.dataset.pt,el.dataset);
  });
  document.addEventListener('input',e=>{if(S.host&&e.target.name==='nick'&&e.target.closest?.('#sheet .pt-embed'))S.nick=e.target.value;});
  document.addEventListener('change',e=>{const el=e.target.closest?.('#sheet .pt-embed [data-pt-sel]');if(el&&S.host&&autoPick(el))render();});   // ⚡ the pickers
}
const PART={buy:['shop'],wear:['shop','wear'],wing:['shop','wing'],toy:['shop','toy'],gear:['gear','','buy'],lab:['lab'],ward:['ward'],gearup:['gear','','bag']};
export function petEmbedHTML(env,part){
  S.env=env;S.host='sheet';bindSheet();
  const v=V(),c=CAT(),want=PART[part]||PART.buy;
  if(!v||!c)return '<p class="pt-empty">⏳</p>';
  if(!v.story)return '<p class="pt-empty">Chỉ có trong hành trình.</p>';
  if(S.part!==part){S.part=part;S.flash=null;S.wk='';S.wslot='';S.item='';S.breed='';S.g='';S.wsel='';S.fz=[];S.bq=1;S.sub='';}   // another shelf: a fresh pick
  // a purchase may have moved them (go: tab home, gear bag)
  S.tab=want[0];if(part==='buy'&&!['dog','cat'].includes(S.kind))S.kind='dog';else if(want[1])S.kind=want[1];if(want[2])S.gv=want[2];S.sub='';
  if(['wear','wing','ward'].includes(part)?!WARD():['gear','gearup','lab'].includes(part)&&!TT())return '<p class="pt-empty">⏳</p>';
  // no pet yet: what is bought waits in the pet's wardrobe / bag; the way to a pet first (home()'s words)
  const none=part!=='buy'&&!allPets().length?`<section class="pt-card pt-center pt-none"><h3>Chưa có bé nào</h3><p class="pt-muted">Góc Chân Nhỏ có bé chờ nhà mới.${['lab','gearup'].includes(part)?'':' Đồ mua trước được cất sẵn, có bé rồi mặc cho bé.'}</p>
    <div class="pt-chips pt-center"><button type="button" class="pt-chip on" data-action="jrAccShop" data-tab="pbuy">🐶 Mua bé</button><button type="button" class="pt-chip" data-action="pets" data-tab="adopt">🏠 Nhận nuôi</button></div></section>`:'';
  const inner=part==='lab'?lab(v,c):part==='ward'?ward(v,c):part==='gear'||part==='gearup'?gear(v,c):shop(v,c);
  const [label,,why]=main(),w=why&&why.trim();
  const bar=label?`<footer class="pt-bar">${w?`<small class="pt-why">${esc(why)}</small>`:''}<button type="button" class="btn primary big pt-main" data-pt="go"${S.busy||w||why===' '?' disabled':''}>${esc(label)}</button></footer>`:'';
  const flash=`<p class="pt-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  const back=S.sub?`<div class="pt-chips"><button type="button" class="pt-chip" data-pt="back">↩︎ Quay lại</button></div>`:'';   // the dialog's ← is in its own head
  const mo=part==='lab'?myth(c):'';   // ✨ a thần thú offer (a fusion, ⚡ stops on it): answered here too
  return `<div class="pt-root pt-embed" aria-busy="${S.busy}">${flash}${back}${mo}${none}${inner}${bar}</div>`;
}
/** A way out of the sheet's shelf to the other place: 🛍️ Cửa hàng's shelf (tab) in the sheet, this dialog's tab else. */
const shopChip=(tab,kind,label)=>S.host?`<button type="button" class="pt-chip" data-action="jrAccShop" data-tab="${tab}">${label}</button>`:chip('tab',{tab:'shop',kind},false,label);

/* ---- ⚡ Cường hóa nhanh (owner 23/10: "cường hóa nhanh sẽ tự ghép mà cường hóa chứ sao lại cường hóa từng lần", "nó giống
 * ghép tự động của áo quần ấy"): on each ghép shelf one card, like 🤖 Ghép tự động of the clothes: which ones, up to which
 * rank, the most to spend (the first round's estimate until one is picked); one question with what may be lost on a
 * miss, ONE command that runs the single one again and again on the server (👗 jr_pet_wfuse_auto, 🧬 jr_pet_fuse_auto,
 * 🧰 jr_pet_gear_auto: game/pet_wardrobe.py, game/pet_tiers.py), then its summary. Tự chọn stays below. The odds stay
 * on the server (owner 19/10 "đừng show tỷ lệ ra"). ---- */
const AK={ward:{sc:'wascope',top:'watop',bud:'wabud',res:'wres',max:6},lab:{sc:'lascope',top:'latop',bud:'labud',res:'lres',max:7},
  gear:{sc:'gascope',top:'gatop',bud:'gabud',res:'gres',max:6}};
/** A picker changed (data-pt-sel: wascope, watop, lascope …): its value, the budget back to the estimate. */
function autoPick(el){
  const key=el.dataset.ptSel,kind=Object.keys(AK).find(k=>AK[k].sc===key||AK[k].top===key);if(!kind)return false;const k=AK[kind];
  if(key===k.sc)S[key]=el.value||'all';else S[key]=Math.max(1,Math.min(k.max,Number(el.value)||k.max));
  S[k.bud]=0;return true;
}
const idn=x=>Number(String(x.id).slice(1))||0;
/** 🧬 What jr_pet_fuse_auto finds now, as game/pet_tiers.py fuse_sets sees it: three pets of ONE breed and rank (owner
 * 23/10: "ghép nhanh thì ghép gì nhận đó thôi k ghép nhanh mấy dòng khác nhé"; no 🌟 legendary, no sad pet at home, one
 * kind or both) whose result is at most `top` (7: 🌟), the lowest rank first, then the breeds' order. {sets [{r, b, t}], n, est, min}. */
function labPlan(scope=S.lascope,top=S.latop){
  const t=TT();if(!t)return {sets:[],n:0,est:0,min:0};
  const m=new Map(),order=(CAT()?.breeds||[]).map(b=>b.id);
  for(const p of allPets()){const b=breedOf(p.b);if(!b||p.legend||fuseWhy(p)||(scope!=='all'&&b.kind!==scope))continue;const r=p.r||0;if(r+1>top)continue;
    const key=`${r}|${p.b}`;if(!m.has(key))m.set(key,{r,b:p.b,n:0});m.get(key).n++;}
  const sets=[...m.values()].filter(x=>x.n>=3).map(({r,b,n})=>({r,b,t:Math.floor(n/3)})).sort((a,b)=>a.r-b.r||order.indexOf(a.b)-order.indexOf(b.b)),fee=r=>Number(t.ranks[r]?.fee)||0;
  return {sets,n:sets.reduce((a,x)=>a+x.t,0),est:sets.reduce((a,x)=>a+x.t*fee(x.r),0),min:sets.length?fee(sets[0].r):0};
}
/** 🧰 What jr_pet_gear_auto does now, as game/pet_tiers.py gear_step sees it: three of a slot, model and rank (two not
 * worn; one model a set, owner 23/10), the main one (worn first, then the highest level) to +max then a rank up, the
 * lowest rank first (then the slots', then the models' order); with none of those the gear worn below +max.
 * {sets [{g, r}], worn [g], n, est (one round, no misses), min (the first step's fee)}. */
function gearPlan(scope=S.gascope,top=S.gatop){
  const t=TT();if(!t)return {sets:[],worn:[],n:0,est:0,min:0};
  const L=t.gear.lv_max,order=t.gear.slots.map(s=>s.id),bag=(X()?.gear||[]).filter(g=>scope==='all'||g.s===scope);
  const up=(r,lv)=>t.gear.up_fee[r]*(lv+1),toMax=g=>{let a=0;for(let lv=g.lv;lv<L;lv++)a+=up(g.r,lv);return a;};
  const m=new Map();for(const g of bag){if(g.r>=Math.min(top,6))continue;const key=`${g.r}|${g.s}|${g.m|0}`;if(!m.has(key))m.set(key,[]);m.get(key).push(g);}
  const sets=[];
  for(const gs of [...m.values()].sort((a,b)=>a[0].r-b[0].r||order.indexOf(a[0].s)-order.indexOf(b[0].s)||(a[0].m|0)-(b[0].m|0))){
    const main=[...gs].sort((a,b)=>(!!b.on-!!a.on)||b.lv-a.lv||idn(a)-idn(b))[0];
    if(gs.filter(g=>g!==main&&!g.on).length<2)continue;
    sets.push({g:main,r:main.r,cost:toMax(main)+t.gear.fuse_fee[main.r],first:main.lv<L?up(main.r,main.lv):t.gear.fuse_fee[main.r]});
  }
  const worn=sets.length?[]:bag.filter(g=>g.on&&g.lv<L).sort((a,b)=>b.r-a.r||b.lv-a.lv||idn(a)-idn(b));
  return {sets,worn,n:sets.length+worn.length,est:sets.reduce((a,x)=>a+x.cost,0)+worn.reduce((a,g)=>a+toMax(g),0),
    min:sets.length?sets[0].first:worn.length?up(worn[0].r,worn[0].lv):0};
}
const planOf=kind=>kind==='lab'?labPlan():kind==='gear'?gearPlan():autoPlan();
/** The budget picked for `kind` (the estimate until one is picked), within [the first fee, the money at hand]. */
function budgetOf(kind,pl){
  if(!pl.n)return 0;const cap=Math.max(pl.min,ready());
  return Math.max(pl.min,Math.min(S[AK[kind].bud]||pl.est,cap));
}
const autoMax=kind=>kind==='ward'?WARD()?.auto_max:kind==='gear'?TT()?.limits?.gear_auto_max:TT()?.limits?.auto_max;
const loseFrom=()=>TT()?.limits?.lose_from??4;
/** ⚒️ Cường hóa's overview (v4/acc-shop.js forgeView, owner 23/10 "ghép thì đưa vào mục riêng"): what this player owns
 * to ghép, grouped by kind with counts, and whether ⚡ has something to do now. */
export function petForgeCounts(env){
  S.env=env;
  const rk=p=>p.legend?7:p.r||0,ps=allPets(),rank=r=>r===7?'🌟':RNAME(r)||RKS[r];
  const by=xs=>[...xs.reduce((m,r)=>m.set(r,(m.get(r)||0)+1),new Map())].sort((a,b)=>b[0]-a[0]);
  const sets=new Map();for(const i of myItems()){if(i.r>=6||!wItem(i.k))continue;const key=`${i.k}|${i.r}`;sets.set(key,(sets.get(key)||0)+1);}
  const bag=X()?.gear||[],L=TT()?.gear?.lv_max||0;
  return {
    lab:{n:ps.length,ranks:by(ps.map(rk)).map(([r,n])=>[rank(r),n]),quick:!!autoMax('lab')&&labPlan('all',7).n>0},
    ward:{n:myItems().length,sets:[...sets.values()].filter(n=>n>=3).length,quick:!!autoMax('ward')&&autoPlan('all',6).n>0},
    gear:{n:bag.length,up:bag.filter(g=>gearUp(g)?.ok).length,lv:bag.filter(g=>g.lv<L).length,quick:!!autoMax('gear')&&gearPlan('all',6).n>0},
  };
}
/** In the dialog: the way to ⚒️ Cường hóa, where every ghép now lives (the dialog's own stays for those used to it). */
const forgeLink=tab=>S.host?'':`<div class="pt-chips"><button type="button" class="pt-chip on" data-pt="forge" data-tab="${tab}">⚒️ Ghép ở Cường hóa: mọi thứ ghép một chỗ</button></div>`;
const opt=(v,l,on)=>`<option value="${esc(v)}"${on?' selected':''}>${esc(l)}</option>`;
const setTag=(k,r,n)=>{const it=wItem(k);return it?`<span class="pt-aset"><i aria-hidden="true">${esc(it.emoji)}</i>${esc(it.name)} ${RK(r)}${n>1?`<small>×${n}</small>`:''}</span>`:'';};
const rankSet=(r,n,b)=>{const bb=b&&breedOf(b);return `<span class="pt-aset">${bb?`<span>${esc(bb.name)}</span> `:''}${r>=6?'SSS → 🌟':`${RK(r)} → ${RK(r+1)}`}${n>1?`<small>×${n}</small>`:''}</span>`;};
/** What each shelf's card says and picks: {what (the ones the pickers choose), fields, stats, tags, note, lose, none}. */
function autoParts(kind,pl){
  const k=AK[kind],top=S[k.top];
  if(kind==='ward'){
    const all=autoPlan('all',top),per=new Map();for(const x of all.sets)per.set(x.k,(per.get(x.k)||0)+x.t);
    if(S.wascope!=='all'&&!per.has(S.wascope)&&wItem(S.wascope))per.set(S.wascope,0);
    const scope=opt('all',`Tất cả (${all.n})`,S.wascope==='all')+[...per].map(([id,n])=>{const it=wItem(id);return opt(id,`${it.emoji} ${it.name} (${n})`,S.wascope===id);}).join('');
    return {label:'Món',scope,ranks:RKS.slice(1).map((r,i)=>opt(i+1,r,top===i+1)).join(''),unit:'bộ ba ghép được ngay',
      tags:pl.sets.slice(0,8).map(x=>setTag(x.k,x.r,x.t)).join('')+(pl.sets.length>8?`<span class="pt-aset">+${pl.sets.length-8}</span>`:''),
      none:'Chưa có 3 món giống hệt (cùng món, cùng hạng) chưa mặc để ghép.',lose:false};
  }
  if(kind==='lab'){
    const n=sc=>labPlan(sc,top).n,scope=opt('all',`Tất cả (${n('all')})`,S.lascope==='all')+opt('dog',`🐶 Chó (${n('dog')})`,S.lascope==='dog')+opt('cat',`🐱 Mèo (${n('cat')})`,S.lascope==='cat');
    return {label:'Bé',scope,ranks:[1,2,3,4,5,6].map(r=>opt(r,RNAME(r),top===r)).join('')+opt(7,'🌟 Huyền thoại',top===7),unit:'bộ ba bé ghép được ngay',
      tags:pl.sets.slice(0,8).map(x=>rankSet(x.r,x.t,x.b)).join('')+(pl.sets.length>8?`<span class="pt-aset">+${pl.sets.length-8}</span>`:''),
      none:'Chưa có 3 bé cùng giống, cùng hạng (vui vẻ, không phải huyền thoại) để ghép.',lose:top>loseFrom()};
  }
  const t=TT(),L=t.gear.lv_max,cnt=sc=>gearPlan(sc,top).n;
  const scope=opt('all',`Tất cả (${cnt('all')})`,S.gascope==='all')+t.gear.slots.map(s=>opt(s.id,`${s.emoji} ${s.name} (${cnt(s.id)})`,S.gascope===s.id)).join('');
  const gt=(g,to)=>`<span class="pt-aset"><i aria-hidden="true">${esc(g.emoji)}</i>${esc(g.name)} ${RK(g.r)}${g.lv?` +${g.lv}`:''} → ${to}</span>`;
  return {label:'Linh kiện',scope,ranks:[1,2,3,4,5,6].map(r=>opt(r,RNAME(r),top===r)).join(''),unit:pl.sets.length?'món lên hạng được':'món đang gắn cường hóa được',
    tags:pl.sets.slice(0,8).map(x=>gt(x.g,`${RK(x.r+1)}`)).join('')+pl.worn.slice(0,8).map(g=>gt(g,`+${L}`)).join(''),
    none:`Chưa có món nào cường hóa được: cần 3 món cùng mẫu, cùng hạng (2 món chưa gắn), hoặc một món đang gắn chưa tới +${L}.`,lose:top>loseFrom()};
}
/** The ⚡ card of a shelf (and the last run's summary above it). An older server (no auto limits): no card. */
function autoCard(kind){
  const max=autoMax(kind);if(!max)return '';
  const k=AK[kind],pl=planOf(kind),b=budgetOf(kind,pl),o=autoParts(kind,pl);
  const fields=`<div class="pt-afields"><label class="pt-afield"><span>${esc(o.label)}</span><select data-pt-sel="${k.sc}" aria-label="${esc(o.label)} để cường hóa">${o.scope}</select></label>`
    +`<label class="pt-afield"><span>Ghép tới hạng</span><select data-pt-sel="${k.top}" aria-label="Ghép tới hạng">${o.ranks}</select></label></div>`;
  let body;
  if(!pl.n)body=`<p class="pt-muted pt-center">${esc(o.none)}</p>`;
  else{
    const cap=Math.max(pl.min,ready()),step=pl.min,why=readyWhy(pl.min);
    const quick=[];for(const [n,l] of [[pl.est,'Vòng đầu'],[pl.est*2,'×2'],[pl.est*5,'×5']]){const v=Math.max(pl.min,Math.min(n,cap));if(!quick.some(q=>q[0]===v))quick.push([v,l]);}
    body=`<div class="pt-astats"><div><b>${pl.n}</b><small>${esc(o.unit)}</small></div><div><b>${fmt(pl.est)}</b><small>xu ${kind==='gear'?'ước tính một vòng':'phí vòng đầu'}</small></div></div>`
      +(o.tags?`<div class="pt-asets">${o.tags}</div>`:'')
      +`<div class="pt-qty" role="group" aria-label="Tiêu tối đa"><div class="pt-qty-row"><span class="pt-qty-l">Tiêu tối đa</span><span class="pt-qty-step">`
      +`<button type="button" class="pt-qty-b" data-pt="abud" data-kind="${kind}" data-n="${b-step}"${b-step<pl.min?' disabled':''} aria-label="Bớt ngân sách">−</button>`
      +qtyBox({value:b,min:pl.min,max:cap,money:true,label:'Số xu tiêu tối đa',go:`data-pt="abud" data-kind="${kind}" data-n="${QTY}"`})
      +`<button type="button" class="pt-qty-b" data-pt="abud" data-kind="${kind}" data-n="${b+step}"${b+step>cap?' disabled':''} aria-label="Thêm ngân sách">+</button></span></div>`
      +`<div class="pt-chips pt-qty-chips">${quick.map(([n,l])=>chip('abud',{kind,n},b===n,l)).join('')}</div>`
      +`<p class="pt-qty-sum">Dừng trước khi vượt <b>${fmt(b)} xu</b> · trả một lần</p></div>`
      +(o.lose?`<p class="pt-fzwarn">⚠️ Từ hạng S trở lên: trượt thì mất 2 ${kind==='lab'?'bé':'món'} nguyên liệu.</p>`:'')
      +(why?`<small class="pt-why">${esc(why)}</small>`:'')
      +`<button type="button" class="btn primary pt-autogo" data-pt="auto" data-kind="${kind}"${S.busy||why?' disabled':''}>⚡ Cường hóa nhanh · tiêu tối đa ${fmt(b)} xu</button>`;
  }
  const card=`<section class="pt-card pt-auto pt-quick" aria-label="Cường hóa nhanh"><h3>⚡ Cường hóa nhanh</h3>${fields}${body}</section>`;
  return (S[k.res]?autoResult(kind,S[k.res],max):'')+card;
}
/** The last ⚡ run's summary (the server's `auto`): turns, successes, misses, the xu spent, what was used, why it
 * stopped and what went up (the best one shown). */
function autoResult(kind,a,max){
  const stop={done:'Hết bộ ba để ghép.',top:'Đã tới hạng đặt.',budget:'Dừng vì chạm số xu đã đặt.',money:'Dừng vì hết tiền.',
    cap:`Đủ ${max} lượt một lần, bấm tiếp nếu muốn.`,myth:'✨ Có thần thú muốn nhập vào bé: trả lời ở trên rồi ghép tiếp nhé.'}[a.stop]||'';
  let best='',made='',used='';
  if(kind==='ward'){
    const g=new Map();for(const i of a.made||[]){const key=`${i.k}|${i.r}`;const o=g.get(key)||{k:i.k,r:i.r,n:0};o.n++;g.set(key,o);}
    const xs=[...g.values()].sort((x,y)=>y.r-x.r||Number(!!wItem(y.k)?.lux)-Number(!!wItem(x.k)?.lux));
    if(xs[0]&&wItem(xs[0].k))best=`<div class="pt-stage">${tryOn(xs[0].k,xs[0].r,110)}</div>`;
    made=xs.map(x=>setTag(x.k,x.r,x.n)).join('');used=`dùng ${a.used} món${a.lux?` · 💎 ${a.lux} món dòng sang`:''}`;
  }else if(kind==='lab'){
    const c=CAT(),xs=[...(a.made||[])].sort((x,y)=>Number(!!y.legend)-Number(!!x.legend)||y.r-x.r),top=xs[0]&&allPets().find(p=>p.id===xs[0].id);
    if(top)best=`<div class="pt-stage">${petPic(c,top,'happy',110,{})}</div>`;
    made=xs.map(x=>`<span class="pt-aset" data-no-translate>${esc(x.n)} ${x.legend?'🌟':RK(x.r)}</span>`).join('');used=`${a.used} bé nguyên liệu đã dùng`;
  }else{
    const xs=[...(a.made||[])].sort((x,y)=>y.r-x.r||y.lv-x.lv);
    if(xs[0])best=`<p class="pt-gear-big" aria-hidden="true">${esc(xs[0].emoji)}</p>`;
    made=xs.map(g=>`<span class="pt-aset"><i aria-hidden="true">${esc(g.emoji)}</i>${esc(g.name)} ${RK(g.r)}${g.lv?` +${g.lv}`:''}</span>`).join('');
    used=`${a.fuses||0} lần ghép lên hạng · dùng ${a.used} món`;
  }
  return `<section class="pt-card pt-ares" aria-label="Kết quả cường hóa nhanh" aria-live="polite"><div class="pt-ares-h"><h4>⚡ Kết quả cường hóa nhanh</h4>${chip('ares',{kind},false,'✕','Ẩn kết quả')}</div>`
    +best
    +`<div class="pt-astats four"><div><b>${a.n}</b><small>lượt</small></div><div class="good"><b>${a.ok}</b><small>thành công</small></div><div><b>${a.n-a.ok}</b><small>trượt</small></div><div class="lux"><b title="${fmt(a.spent)} xu">${shortNum(a.spent)}</b><small>xu đã tiêu</small></div></div>`
    +`<p class="pt-muted pt-center">${esc(used)}</p><p class="pt-muted pt-center"><span>${esc(stop)}</span>${a.left?` <span>Còn ${a.left} ${kind==='gear'?'bộ lên hạng':'bộ ba'}.</span>`:''}</p>`
    +(made?`<h4>✨ ${kind==='lab'?'Bé lên hạng':kind==='gear'?'Món mạnh lên':'Món mới'}</h4><div class="pt-asets">${made}</div>`:`<p class="pt-muted pt-center">💨 Lần này chưa ${kind==='gear'?'mạnh thêm món nào':'lên hạng'}${kind==='ward'?', các món vẫn còn nguyên':''}.</p>`)
    +`</section>`;
}
/** ⚡ The card's button: one question (the scope, the rank, the most to spend, what a miss loses), one command. */
async function runAuto(kind){
  const k=AK[kind];if(S.busy||!k||!autoMax(kind))return;
  const pl=planOf(kind),b=budgetOf(kind,pl);if(!pl.n||readyWhy(pl.min))return;
  const o=autoParts(kind,pl),top=S[k.top],max=autoMax(kind),pay=`Tiêu tối đa ${fmt(b)} xu, tối đa ${max} lượt, trả một lần: ví trước, thiếu thì lấy từ tài khoản.`;
  let msg,cmd,payload;
  if(kind==='ward'){const sc=S.wascope==='all'?null:wItem(S.wascope);
    msg=`${sc?`Chỉ ${sc.name}`:'Mọi món'}, hạng thấp trước, tới hạng ${RKS[top]}. Trượt thì ba món vẫn còn, mất phí lượt đó. Đồ đang mặc được giữ nguyên. ${pay}`;
    cmd='jr_pet_wfuse_auto';payload={scope:S.wascope,max_rank:top,budget:b,confirm:true};}
  else if(kind==='lab'){const sc={all:'Chó và mèo',dog:'Chỉ chó',cat:'Chỉ mèo'}[S.lascope]||'';
    msg=`${sc}, ba bé cùng hạng, hạng thấp trước, tới ${top>=7?'🌟 huyền thoại':`hạng ${RNAME(top)}`}. Thành công: bé chính lên hạng, giữ giống; hai bé nguyên liệu về quê với bà. Trượt: ${o.lose?'dưới hạng S ba bé vẫn ở lại; ⚠️ từ hạng S trở lên mất hai bé nguyên liệu (không về quê), bé chính ở lại':'ba bé vẫn ở lại'}, mất phí lượt đó. Bé đang dắt không bao giờ là nguyên liệu. ${pay}`;
    cmd='jr_pet_fuse_auto';payload={scope:S.lascope,top,budget:b,confirm:true};}
  else{const L=TT().gear.lv_max;
    msg=`Cường hóa món chính lên +${L} rồi ghép lên hạng, hạng thấp trước, tới hạng ${RNAME(top)}; hết bộ ba thì cường hóa món đang gắn lên +${L}. Cường hóa trượt: món vẫn nguyên, mất phí. Ghép trượt: ${o.lose?'dưới hạng S ba món vẫn còn; ⚠️ từ hạng S trở lên mất 2 món nguyên liệu':'ba món vẫn còn'}, mất phí. Món đang gắn không bao giờ là nguyên liệu. ${pay}`;
    cmd='jr_pet_gear_auto';payload={scope:S.gascope,top,budget:b,confirm:true};}
  if(!await askForge('⚡ Cường hóa nhanh?',msg,`⚡ Cường hóa · tối đa ${fmt(b)} xu`,Math.min(b,ready())))return;
  const r=await send(cmd,payload);
  if(r?.auto){S[k.res]=r.auto;S[k.bud]=0;if(!r.ok)S.flash={...S.flash,kind:'bad'};if(S[k.sc]!=='all'&&!planOf(kind).n)S[k.sc]='all';
    if(kind==='lab'){S.fz=[];S.fzBreed='';S.fzMix=false;}if(kind==='gear')S.g='';render();}
}

const meters=n=>`<div class="pt-needs">${NEEDS.map(([k,e,l])=>`<span class="pt-need${n[k]<CAT().low?' low':''}" title="${l} ${n[k]}" aria-label="${l} ${n[k]}"><i aria-hidden="true">${e}</i><b style="--v:${n[k]}%"></b></span>`).join('')}</div>`;
const chip=(op,data,on,inner,label='')=>`<button type="button" class="pt-chip${on?' on':''}" data-pt="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')} aria-pressed="${on}"${label?` aria-label="${esc(label)}" title="${esc(label)}"`:''}>${inner}</button>`;

/** ✨ A thần thú came with the last fusion to S or more (owner 19/10): the game picked it, the player keeps the pet
 * as it is or lets it turn into that one (jr_pet_morph). */
function myth(c){
  const o=V()?.petw?.mo,p=o&&allPets().find(q=>q.id===o.p);if(!p)return '';
  const bb=breedOf(o.b),nm=esc(bb?.name||''),pn=esc(p.n);
  return `<section class="pt-myth" aria-label="Thần thú xuất hiện"><h4>✨ Thần thú xuất hiện!</h4>
    <p>Một bé <b>${nm}</b> muốn nhập vào <b data-no-translate>${pn}</b>. Đổi thì ${pn} hóa thành ${nm}, vẫn giữ hạng, tên, đồ và linh kiện. Không đổi thì ${nm} bay đi.</p>
    <div class="pt-myth-pics"><figure>${petPic(c,p,'sit',92)}<figcaption>${esc(breedOf(p.b)?.name||'')}</figcaption></figure><span aria-hidden="true">➜</span>
      <figure class="to">${petPic(c,{...p,b:o.b,c:o.c},'happy',92)}<figcaption>✨ ${nm}</figcaption></figure></div>
    <div class="pt-chips pt-center">${chip('morph',{take:'0'},false,`💛 Giữ ${pn} như cũ`)}${chip('morph',{take:'1'},true,`✨ Đổi thành ${nm}`)}</div></section>`;
}
function home(v,c){
  const list=pets(),all=allPets(),lst=all.length>1?`<button type="button" class="pt-mini pt-all" data-pt="sub" data-sub="all" aria-label="Lọc các bé" title="Lọc các bé"><span aria-hidden="true">📋</span><small>${all.length}</small></button>`:'';
  if(S.sub==='all')return roster(v);
  // owner 19/10 "Bé nhà mình sao k hiển thị full các bé": every pet in the strip, home first, then the kennel (🏠)
  const out=away(),sel=out?out.id:(cur()?.id||'');
  const mini=x=>`<button type="button" class="pt-mini${x.id===sel?' on':''}${x.at!=='home'?' away':''}" data-pt="${x.at==='home'?'pet':'pick'}" data-id="${esc(x.id)}" aria-label="${esc(x.n)}" title="${esc(x.n)}${v.walk===x.id?' · đang đi dạo':x.at==='ken'?' · trại nuôi':x.at==='farm'?' · ở quê':''}">${petPic(c,x,'sit',44)}${v.walk===x.id?'<small class="pt-walkdot">🦮</small>':x.at==='ken'?'<small>🏠</small>':x.at==='farm'?'<small>🌾</small>':''}</button>`;
  const strip=all.length>1?`<p class="pt-hint">👆 Chạm một bé để chọn · 🦮 là bé đang đi dạo cùng bạn</p><div class="pt-strip">${all.map(mini).join('')}${lst}</div>`:'';
  if(out)return strip+awayCard(v,out);
  if(!list.length)return `<section class="pt-card pt-center">${petSVG(breedOf('meo_muop'),breedOf('meo_muop').coats[1],'happy',{},120)}<h3>Chưa có bé nào</h3><p class="pt-muted">Góc Chân Nhỏ có bé chờ nhà mới.</p></section>`+strip+farm(v);
  const p=cur();S.pet=p.id;
  const b=breedOf(p.b);
  if(S.sub)return strip+subView(p,c);
  const pose=p.mood==='vui'?'happy':p.mood==='buon'?'sleep':'sit';
  const acts=[['feed','🍚','Ăn'],['play','🎾','Chơi'],['clean','🛁','Tắm'],['vet','🩺','Khám'],['dress','👗','Mặc đồ'],['photo','📸','Ảnh'],...(TT()?[['train','🏋️','Luyện'],['equip','🧰','Linh kiện']]:[]),['more','⋯','Thêm']];
  const fx=fxName(p.fx),walking=v.walk===p.id;
  // 🦮 owner 19/10 "đổi pets dắt đi như nào cũng k biết": one big button on the card, and what it does
  const walk=walking?`<div class="pt-walking"><b>🦮 ${esc(p.n)} đang đi dạo cùng bạn</b><small>Bé theo bạn ra phố${p.pct?` và cộng +${p.pct}% tiền làm việc`:''}.</small><button type="button" class="pt-chip" data-pt="walk">🏡 Cho bé ở nhà</button></div>`
    :`<button type="button" class="btn primary pt-walkbtn" data-pt="walk">🦮 Dắt ${esc(p.n)} đi dạo</button><p class="pt-hint">Bé đi dạo sẽ theo bạn ra phố${p.pct?` và cộng +${p.pct}% tiền làm việc`:''}. Mỗi lần dắt được một bé.</p>`;
  return strip+`<section class="pt-card pt-hero${p.r>=4||p.legend?' pt-shine':''}"><div class="pt-stage">${petPic(c,p,pose,150)}</div>
    <h3>${rankTag(p)} <span data-no-translate>${esc(p.n)}</span> ${MOOD[p.mood]||''}</h3><p class="pt-muted">${esc(b?.name||'')}${fx?` · ${fx.emoji} ${esc(fx.name)}`:''}${Number.isInteger(p.pw)?` · 💪${p.pw}`:''}${p.pts?` · 🏆${p.pts}`:''}</p>${walk}${meters(p.needs)}${bonusLine(v,p)}${wearLine(p)}</section>
    <div class="pt-acts">${acts.map(([s,e,l])=>`<button type="button" class="pt-act" data-pt="sub" data-sub="${s}"><span aria-hidden="true">${e}</span>${l}</button>`).join('')}</div>
    `;   // 21/10: the ⚔️ Đấu trường pet button is gone — the arena is for bang members (⚔️ Bang)   // v4/pet-arena.js (owner 19/10 "thi đua … pet ra tranh đấu")
}
/** 📋 Every pet of this save in one list, filtered by kind, rank and place, best first (owner 19/10 "xem danh sách
 * all các bé trong nhà … lọc theo bậc, theo loại chó/mèo"). A tap opens it: a home pet's card, or awayCard. */
const PLACE={home:'🏡 Ở nhà',ken:'🏠 Trại nuôi',farm:'🌾 Ở quê'};
function roster(v){
  const all=allPets(),f=S.ff,kindOf=p=>breedOf(p.b)?.kind||'',ranks=TT()?.ranks||[];
  const ok=p=>(!f.k||kindOf(p)===f.k)&&(f.r===''||(f.r==='lg'?p.legend:!p.legend&&p.r===Number(f.r)))&&(!f.at||p.at===f.at);
  const rows=all.filter(ok).sort((a,b)=>(b.legend?1:0)-(a.legend?1:0)||(b.r||0)-(a.r||0)||(b.pw||0)-(a.pw||0));
  const fc=(key,val,inner,label='')=>chip('ff',{key,val},String(f[key])===String(val),inner,label);
  const has=pred=>all.some(pred);
  return `<section class="pt-card"><h4>📋 Tất cả các bé · ${rows.length===all.length?all.length:`${rows.length}/${all.length}`}</h4>
    <div class="pt-chips">${fc('k','','Tất cả')}${fc('k','dog','🐶 Chó')}${fc('k','cat','🐱 Mèo')}</div>
    <div class="pt-chips">${fc('r','','Mọi hạng')}${ranks.map((x,i)=>has(p=>!p.legend&&p.r===i)||f.r===String(i)?fc('r',i,`<span class="pt-rk r${i}">${esc(x.rank)}</span>`,`Hạng ${x.rank}`):'').join('')}${has(p=>p.legend)?fc('r','lg','🌟','Huyền thoại'):''}</div>
    <div class="pt-chips">${fc('at','','Mọi nơi')}${Object.entries(PLACE).map(([k,l])=>has(p=>p.at===k)?fc('at',k,l):'').join('')}</div>
    ${rows.length?`<div class="pt-rgrid">${rows.map(p=>`<button type="button" class="pt-rcard${p.id===S.pet?' on':''}" data-pt="pick" data-id="${esc(p.id)}" aria-label="${esc(`${p.n} · ${breedOf(p.b)?.name||''} · ${PLACE[p.at]}`)}">${petPic(CAT(),p,'sit',76)}<b data-no-translate>${esc(p.n)}</b><span>${rankTag(p)} <i aria-hidden="true">${PLACE[p.at].split(' ')[0]}${v.walk===p.id?'🦮':''}</i></span>${Number.isInteger(p.pw)?`<small>💪 ${p.pw}</small>`:''}</button>`).join('')}</div>`:'<p class="pt-muted">Không có bé nào hợp bộ lọc.</p>'}</section>`;
}
/** A pet picked on the list that is not at home: what it is, and one tap to bring it home (trading places when home is
 * full, game/pet_tiers.py jr_pet_kennel `swap`) or to walk it. */
function awayCard(v,p){
  const b=breedOf(p.b),fx=fxName(p.fx),full=pets().length>=CAT().max,walked=v.walk&&pets().find(x=>x.id===v.walk);
  let acts='';
  if(p.at==='ken'){
    acts=full?`<p class="pt-muted">Nhà đủ ${CAT().max} bé: chọn một bé ở nhà đổi chỗ vào trại.</p><div class="pt-strip">${pets().map(x=>`<button type="button" class="pt-mini" data-pt="kennel" data-to="home" data-id="${esc(p.id)}" data-swap="${esc(x.id)}" aria-label="Đổi với ${esc(x.n)}" title="Đổi với ${esc(x.n)}">${petPic(CAT(),x,'sit',44)}<small>🔁</small></button>`).join('')}</div>`
        +(walked?`<div class="pt-chips">${chip('kennel',{to:'home',id:p.id,swap:walked.id,walk:1},false,`🦮 Dắt bé này thay ${esc(walked.n)}`)}</div>`:'')
      :`<div class="pt-chips">${chip('kennel',{to:'home',id:p.id},false,'🏡 Đón về nhà')}${chip('kennel',{to:'home',id:p.id,walk:1},false,'🦮 Đón về và dắt đi dạo')}</div>`;
  }else if(p.at==='farm')acts=`<div class="pt-chips">${chip('fetch',{id:p.id},false,'🏡 Đón về nhà')}</div>${full?`<p class="pt-muted">Nhà đủ ${CAT().max} bé rồi.</p>`:''}`;
  return `<section class="pt-card pt-hero${p.r>=4||p.legend?' pt-shine':''}"><div class="pt-stage">${petPic(CAT(),p,'sit',150)}</div>
    <h3>${rankTag(p)} <span data-no-translate>${esc(p.n)}</span></h3><p class="pt-muted">${esc(b?.name||'')}${fx?` · ${fx.emoji} ${esc(fx.name)}`:''}${Number.isInteger(p.pw)?` · 💪${p.pw}`:''} · ${PLACE[p.at]}</p>
    ${p.pct?`<p class="pt-bonus">💰 +${p.pct}% tiền làm việc khi dắt đi dạo</p>`:''}${acts}
    <button type="button" class="pt-link" data-pt="sub" data-sub="all">📋 Về danh sách</button></section>`;
}
/** 💰 What the pet adds to work income (only the one walked, only when not sad: game/pet_tiers.py bonus_rate). */
/** 👗 What its outfit adds (game/pet_wardrobe.py bonus_bp: on top of the rank's %, same daily cap). */
function wearLine(p){
  if(!WARD()||!p.wb)return '';const set=(WARD().sets||[]).find(x=>x.id===p.wst);
  return `<p class="pt-bonus${''}">👗 Đồ đang mặc: +${p.wb}% tiền làm việc${set?` · ${set.emoji} đủ ${esc(set.name)}`:''}${p.wo?` · ${'💖'.repeat(p.wo)}`:''}</p>`;
}
function bonusLine(v,p){
  if(!TT()||!p.pct)return '';const x=X(),on=v.walk===p.id,got=on&&x?.bonus?.on?x.bonus.got:0;
  const why=!on?' · dắt đi dạo để nhận':p.mood==='buon'?' · bé buồn, tạm ngưng':'';
  return `<p class="pt-bonus${on&&p.mood!=='buon'?' on':''}">💰 +${p.pct}% tiền làm việc · tối đa ${fmt(p.cap)}/ngày${got?` · hôm nay ${fmt(got)}`:''}${why}</p>`;
}
function farm(v){
  if(!v.farm?.length)return '';
  return `<section class="pt-card"><h4>🏡 Ở quê</h4><div class="pt-strip">${v.farm.map(x=>`<button type="button" class="pt-mini" data-pt="fetch" data-id="${esc(x.id)}" aria-label="Đón ${esc(x.n)}" title="Đón ${esc(x.n)}"${pets().length>=CAT().max?' disabled':''}>${petPic(CAT(),x,'sleep',44,{})}</button>`).join('')}</div></section>`;
}
/** 🏠 The kennel (up to 30): back home with one tap. */
function kennel(){
  const ken=X()?.ken||[],t=TT();if(!t||!ken.length)return '';const full=pets().length>=CAT().max;
  return `<section class="pt-card"><h4>🏡 Đón từ trại về nhà</h4><div class="pt-strip">${ken.map(x=>`<button type="button" class="pt-mini" data-pt="kennel" data-to="home" data-id="${esc(x.id)}" aria-label="Đón ${esc(x.n)} về nhà" title="Đón ${esc(x.n)} về nhà"${full?' disabled':''}>${petPic(CAT(),x,'sit',44,{})}${rankTag(x)}</button>`).join('')}</div>${full?'<p class="pt-muted">Nhà đủ 3 bé: đưa một bé vào trại trước.</p>':''}</section>`;
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
    case'dress':{const W=WARD();if(!W)return '';
      const slots=W.slots,mine=myItems().filter(i=>wItem(i.k)?.slot===S.slot),groups=new Map();
      for(const i of mine){const key=`${i.k}|${i.r}`;const g=groups.get(key)||{k:i.k,r:i.r,n:0,on:[]};g.n++;if(i.on)g.on.push(i.on);groups.set(key,g);}
      const worn=myItems().find(i=>i.on===p.id&&wItem(i.k)?.slot===S.slot);
      const rows=[...groups.values()].sort((a,b)=>b.r-a.r).map(g=>{const it=wItem(g.k),on=worn&&worn.k===g.k&&worn.r===g.r,free=g.n-g.on.filter(x=>x!==p.id).length;
        return `<button type="button" class="pt-item${on?' on':''}" data-pt="wwear" data-slot="${S.slot}" data-id="${on?'':esc((mine.find(i=>i.k===g.k&&i.r===g.r&&!i.on)||mine.find(i=>i.k===g.k&&i.r===g.r)).id)}" aria-pressed="${on}"><span class="pt-ico" aria-hidden="true">${esc(it.emoji)}</span><b>${esc(it.name)} ${RK(g.r)}${g.n>1?` <small>×${g.n}</small>`:''}${!on&&free<=0?'<small> · bé khác đang mặc</small>':''}</b><em>${on?'✓ Đang mặc':'Mặc'}</em></button>`;}).join('');
      const kind=S.slot==='back'?'wing':'wear';
      return pic(S.slot==='bed'?'sleep':'sit',130)+wearLine(p)+`<div class="pt-chips">${slots.map(x=>chip('slot',{slot:x.id},S.slot===x.id,`${x.emoji} ${esc(x.name)}`)).join('')}</div>`
        +(rows?`<div class="pt-list">${rows}</div>`:`<p class="pt-muted pt-center">Chưa có ${esc(slotName(S.slot).toLowerCase())} nào.</p>`)
        +`<button type="button" class="pt-link" data-pt="tab" data-tab="shop" data-kind="${kind}" data-wslot="${kind==='wear'?S.slot:''}">${S.slot==='back'?'🪽 Mua cánh':'🛍️ Mua thêm đồ'}</button>`;}
    case'photo':{const tr=(c.tricks[p.kind]||[]).filter(t=>p.tr.includes(t.id));
      return `<figure class="pt-photo f-${esc(S.frame)}">${photoSVG(p,c)}</figure><div class="pt-chips">${c.poses.map(x=>chip('pose',{id:x.id},S.pose===x.id,esc(x.name))).join('')}</div>
        <div class="pt-chips">${c.frames.map(f=>chip('frame',{id:f.id},S.frame===f.id,f.emoji,f.name)).join('')}${tr.map(t=>chip('trick',{id:t.id},false,t.emoji,t.name)).join('')}</div>`;}
    case'train':{const t=TT();if(!t)return '';const x=X();
      return pic('happy')+`<p class="pt-muted pt-center">${rankTag(p)} 💪 Lực chiến <b>${p.pw}</b> · luyện hôm nay ${x?.today?.train||0}/${t.limits.train_day}</p><div class="pt-list">${t.stats.map((s,i)=>
        `<button type="button" class="pt-item pt-stat${S.stat===s.id?' on':''}" data-pt="stat" data-id="${s.id}" aria-pressed="${S.stat===s.id}"><span class="pt-ico" aria-hidden="true">${s.emoji}</span><b>${esc(s.name)}<i class="pt-bar-s"><u style="--v:${Math.min(100,(p.st?.[i]||0)/2)}%"></u></i></b><em>${p.st?.[i]||0}${p.tn?.[i]?` <small>(+${p.tn[i]})</small>`:''}</em></button>`).join('')}</div>`;}
    case'equip':{const t=TT();if(!t)return '';const bag=(X()?.gear||[]).filter(g=>g.s===S.gslot).sort((a,b)=>b.value-a.value);
      const worn=p.g?.[S.gslot]||null;
      return pic('sit')+`<p class="pt-muted pt-center">💪 Lực chiến <b>${p.pw}</b></p><div class="pt-chips">${t.gear.slots.map(s=>{const g=gearOf(p.g?.[s.id]);return chip('gslot',{slot:s.id},S.gslot===s.id,g?`${g.emoji}<small class="pt-rk r${g.r}">${esc(g.rank)}</small>`:`<span class="pt-off">${s.emoji}</span>`,s.name);}).join('')}</div>`
        +(bag.length?`<div class="pt-list">${bag.map(g=>{const on=g.id===worn;return `<button type="button" class="pt-item${on?' on':''}" data-pt="gwear" data-id="${on?'':esc(g.id)}" aria-pressed="${on}"><span class="pt-ico" aria-hidden="true">${g.emoji}</span><b>${esc(g.name)} <span class="pt-rk r${g.r}">${esc(g.rank)}</span>${g.lv?` +${g.lv}`:''}${g.on&&!on?`<small> · 🐾 ${esc(petName(g.on))}</small>`:''}</b><em>+${g.value}</em></button>`;}).join('')}</div>`
          :`<button type="button" class="pt-link" data-pt="tab" data-tab="gear">🧰 Tìm linh kiện</button>`);}
    case'more':{const v=V(),next=p.next;
      return `<section class="pt-card"><label class="pt-name"><span class="sr-only">Tên bé</span><input name="nick" maxlength="${CAT().name_max}" value="${esc(S.nick)}" autocomplete="off"></label>
        <div class="pt-chips">${chip('walk',{},v.walk===p.id,v.walk===p.id?'🦮 Đang đi dạo':'🦮 Dắt đi dạo')}${chip('home',{},false,'🏡 Gửi về quê')}${TT()?chip('kennel',{id:p.id,to:'ken'},false,'🏠 Vào trại nuôi'):''}</div>
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
  return odds()+`<div class="pt-picks">${cards}</div>`+form;
}
/** What a new pet can be: D or C (higher ranks come from 🧬 fusions); no odds (owner 19/10 "đừng show tỷ lệ ra"). */
function odds(){
  const t=TT();if(!t)return '';const kept=pets().length>=CAT().max&&!noRoom();
  return `<p class="pt-odds">🎲 Bé mới về hạng <span class="pt-rk r0">D</span> hoặc <span class="pt-rk r1">C</span> · ghép 🧬 để lên hạng cao${kept?'<br>🏠 Nhà đủ 3 bé: bé mới vào trại nuôi.':''}</p>`;
}
const SHOPK=[['dog','🐶 Chó'],['cat','🐱 Mèo'],['wear','👗 Quần áo'],['wing','🪽 Cánh'],['toy','🎾 Đồ chơi']];
function shop(v,c){
  if(S.kind==='do')S.kind='toy';
  const kinds=S.host&&!['dog','cat'].includes(S.kind)?'':`<div class="pt-chips pt-kinds">${SHOPK.filter(([k])=>S.host?k==='dog'||k==='cat':WARD()||(k!=='wear'&&k!=='wing')).map(([k,l])=>chip('kind',{kind:k},S.kind===k,l)).join('')}</div>`;
  if(S.kind==='wear'||S.kind==='wing')return kinds+wshop();
  if(S.kind==='toy'){
    const tiles=shopItems().map(it=>`<button type="button" class="pt-tile${S.item===it.id?' on':''}" data-pt="item" data-id="${esc(it.id)}" aria-pressed="${S.item===it.id}" aria-label="${esc(it.name)}" title="${esc(it.name)}"><span aria-hidden="true">${esc(it.emoji)}</span><small>${fmt(it.price)}</small></button>`).join('');
    const it=shopItems().find(x=>x.id===S.item);
    return kinds+(it?`<p class="pt-sel">${esc(it.emoji)} <b>${esc(it.name)}</b>${own(it.id)?` · có ${it.uses?`${own(it.id)} lượt`:own(it.id)}`:''}</p>${qtyPick(it.price)}`:'')+`<div class="pt-tiles">${tiles}</div>`;
  }
  const b=breedOf(S.breed);
  if(b){const coat=b.coats[S.coat]||b.coats[0];
    return kinds+`<section class="pt-card pt-center"><div class="pt-stage">${petSVG(b,coat,'happy',{},140)}</div><h3>${esc(b.name)}</h3><p class="pt-muted">✨ ${esc(b.trait)}</p>${b.nick&&b.line?`<p class="pt-muted">${esc(b.line)}</p>`:''}
      <div class="pt-chips pt-coats">${b.coats.map((k,i)=>chip('coat',{c:i},S.coat===i,`<i style="background:${esc(k.b)};box-shadow:inset -6px 0 0 ${esc(k.m)}"></i>`,k.name)).join('')}</div>
      <label class="pt-name"><span class="sr-only">Tên bé</span><input name="nick" maxlength="${c.name_max}" value="${esc(S.nick)}" placeholder="${esc(b.nick||'Tên bé')}" autocomplete="off"></label>
      ${qtyPick(b.price)}${bq()>1?`<p class="pt-muted">Tên các bé: ${esc(nameHint((S.nick||b.nick||b.name).trim().slice(0,16),bq()))}</p>`:''}</section>
      <button type="button" class="pt-link" data-pt="breed" data-id="">↩︎</button>`;}
  return kinds+odds()+`<div class="pt-picks">${breedList().map(x=>`<button type="button" class="pt-pick" data-pt="breed" data-id="${esc(x.id)}">${petPicture(x,x.coats[0],'sit',{},84)}<b>${esc(x.name)}</b><small>${fmt(x.price)}</small></button>`).join('')}</div>`;
}
/** 🛍️ The wardrobe's shop: 👗 clothes (by slot) or 🪽 wings, each card the picked pet trying it on; a tap opens it. */
function wshop(){
  const W=WARD(),wing=S.kind==='wing',inKind=i=>wing?i.slot==='back':i.slot!=='back';
  const slots=W.slots.filter(x=>x.id!=='back');if(wing||!slots.some(x=>x.id===S.wslot))S.wslot=wing?'':S.wslot&&slots.some(x=>x.id===S.wslot)?S.wslot:'';
  const ok=i=>inKind(i)&&(!S.wslot||i.slot===S.wslot);
  const list=W.items.filter(i=>ok(i)&&!i.lux&&i.on_sale!==false).sort((a,b)=>(a.sale?0:1)-(b.sale?0:1)||a.price-b.price);
  const lux=W.items.filter(i=>ok(i)&&i.lux);
  const it=wItem(S.wk),owned=it?myItems().filter(i=>i.k===it.id):[];
  const dd=d=>d?`${d.slice(8,10)}/${d.slice(5,7)}`:'';
  const tag=i=>i.sale?`<i class="pt-season">⏳ đến ${dd(i.sale[1])}</i>`:'';
  let top=`<p class="pt-intro">${wing?'🪽 Đeo cánh cho bé: ra phố bé cũng có cánh. Cánh hạng C trở lên còn cộng thêm % tiền làm việc.':'👗 Mặc đồ cho bé thật xinh. Đồ hạng C trở lên còn cộng thêm % tiền làm việc khi bé đi dạo.'}</p>`;
  if(!wing)top+=`<div class="pt-chips">${chip('wslot',{slot:''},!S.wslot,'Tất cả')}${slots.map(x=>chip('wslot',{slot:x.id},S.wslot===x.id,`${x.emoji} ${esc(x.name)}`)).join('')}</div>`;
  let card='';
  if(it){const set=(W.sets||[]).find(x=>x.id===it.set),p=cur();
    card=`<section class="pt-card pt-center pt-wsel"><div class="pt-stage">${tryOn(it.id,S.wrank,150)}</div><h3>${esc(it.emoji)} ${esc(it.name)} ${tag(it)}</h3><p class="pt-desc">${esc(it.desc)}</p>
      ${set?`<p class="pt-muted">${set.emoji} Một món của <b>${esc(set.name)}</b>. ${esc(set.desc)}</p>`:''}
      <div class="pt-chips pt-center">${[0,1].map(r=>chip('wrank',{r},S.wrank===r,`${RK(r)} ${fmt(wPrice(it,r))} xu`)).join('')}</div>
      ${qtyPick(wPrice(it,S.wrank))}
      <p class="pt-muted">${S.wrank?`Hạng C: +${W.bonus[1]}% tiền làm việc khi bé mặc.`:'Hạng D: để diện cho xinh, chưa cộng tiền.'} Hạng B trở lên: ghép 3 món giống nhau ở 👗 Tủ đồ.</p>
      ${owned.length&&p?`<div class="pt-chips pt-center">${chip('wput',{key:`${it.id}|${Math.max(...owned.map(i=>i.r))}`,pet:p.id},false,`👗 Mặc luôn cho ${esc(p.n)}`)}</div><p class="pt-muted">Bạn có ${owned.length} món này.</p>`:''}
      <button type="button" class="pt-link" data-pt="wk" data-id="">↩︎ Xem món khác</button></section>`;}
  const cardOf=i=>`<button type="button" class="pt-wcard${i.id===S.wk?' on':''}" data-pt="wk" data-id="${esc(i.id)}" aria-pressed="${i.id===S.wk}">${tryOn(i.id,0,72)}<b>${esc(i.emoji)} ${esc(i.name)}</b><small>${fmt(i.price)} xu</small>${tag(i)}</button>`;
  return top+card+`<div class="pt-wgrid">${list.map(cardOf).join('')}</div>`
    +(lux.length?`<h4 class="pt-luxh">💎 Dòng sang: không bán, chỉ ra khi ghép đồ hạng A trở lên</h4><div class="pt-wgrid lux">${lux.map(i=>`<div class="pt-wcard off">${tryOn(i.id,4,72)}<b>${esc(i.emoji)} ${esc(i.name)}</b><small>🔀 Ghép mới có</small></div>`).join('')}</div>`:'');
}

/* ---- 👗 tủ đồ: every piece owned, wear it on a pet, fuse three identical ones, throw one away ---- */
function ward(v,c){
  const W=WARD();if(!W)return '<p class="pt-empty">⏳</p>';
  const its=myItems(),slots=W.slots;
  const help=`<details class="pt-more"><summary>💡 Tủ đồ dùng thế nào?</summary><p class="pt-muted">1. Mua đồ, cánh ở 🛍️ Tiệm (hạng D hoặc C).<br>2. Chọn món bên dưới rồi chạm tên bé để mặc.<br>3. Có 3 món giống hệt (cùng món, cùng hạng) thì 🔀 ghép ra 1 món hạng cao hơn. Từ hạng A có thể ra 💎 dòng sang.<br>4. Mỗi món đang mặc cộng thêm: ${W.ranks.map((r,i)=>`${r} +${W.bonus[i]}%`).join(', ')}; 💎 dòng sang +${W.lux_bonus}%, đủ bộ +${W.set_bonus}% (tối đa +${W.bonus_max}%). Ổ nằm chỉ để ở nhà.</p></details>`;
  if(!its.length)return help+`<p class="pt-empty">👗</p><p class="pt-muted pt-center">Tủ đồ còn trống.</p><div class="pt-chips pt-center">${shopChip('pwear','wear','👗 Mua quần áo')}${shopChip('pwing','wing','🪽 Mua cánh')}</div>`;
  const groups=new Map();
  for(const i of its){const it=wItem(i.k);if(!it)continue;const key=`${i.k}|${i.r}`;const g=groups.get(key)||{key,k:i.k,r:i.r,it,n:0,on:[]};g.n++;if(i.on)g.on.push(i.on);groups.set(key,g);}
  const order=slots.map(x=>x.id),has=new Set([...groups.values()].map(g=>g.it.slot));
  const rows=[...groups.values()].filter(g=>!S.wfslot||g.it.slot===S.wfslot).sort((a,b)=>order.indexOf(a.it.slot)-order.indexOf(b.it.slot)||b.r-a.r||a.it.name.localeCompare(b.it.name));
  const g=groups.get(S.wsel);
  let card='';
  if(g){const pets_=allPets().filter(p=>p.at!=='farm'),fee=W.fee[g.r];
    card=`<section class="pt-card pt-center pt-wsel"><div class="pt-stage">${tryOn(g.k,g.r,140)}</div><h3>${esc(g.it.emoji)} ${esc(g.it.name)} ${RK(g.r)} <small>×${g.n}</small></h3><p class="pt-desc">${esc(g.it.desc)}</p>
      <p class="pt-muted">${g.it.slot==='bed'?'Ổ nằm: chỉ ở nhà, không cộng tiền.':`Đang mặc: +${W.bonus[g.r]+(g.it.lux?W.lux_bonus:0)}% tiền làm việc.`}</p>
      <h4>👆 Chạm tên bé để mặc (chạm lại để tháo)</h4><div class="pt-chips pt-center">${pets_.map(p=>chip('wput',{key:g.key,pet:p.id},g.on.includes(p.id),`${g.on.includes(p.id)?'✓ ':''}${esc(p.n)}`)).join('')}</div>
      <div class="pt-chips pt-center">${g.r<6?chip('wfuse',{},false,g.n>=3?`🔀 Ghép 3 → hạng ${RKS[g.r+1]} · ${fmt(fee)} xu`:`🔀 Cần ${3-g.n} món nữa để ghép`):''}${chip('wdrop',{},false,'🗑️ Bỏ 1 món')}</div></section>`
      .replace(`data-pt="wfuse"`,g.n>=3?'data-pt="wfuse"':'data-pt="wfuse" disabled');}
  const chipsF=`<div class="pt-chips">${chip('wfslot',{slot:''},!S.wfslot,`Tất cả · ${its.length}`)}${slots.filter(x=>has.has(x.id)).map(x=>chip('wfslot',{slot:x.id},S.wfslot===x.id,`${x.emoji} ${esc(x.name)}`)).join('')}</div>`;
  return forgeLink('pward')+help+autoCard('ward')+card+chipsF+`<div class="pt-list">${rows.map(r=>`<button type="button" class="pt-item${r.key===S.wsel?' on':''}" data-pt="wsel" data-key="${esc(r.key)}" aria-pressed="${r.key===S.wsel}"><span class="pt-ico" aria-hidden="true">${esc(r.it.emoji)}</span><b>${esc(r.it.name)} ${RK(r.r)}${r.n>1?` <small>×${r.n}</small>`:''}${r.on.length?`<small> · 🐾 ${r.on.map(id=>esc(petName(id))).join(', ')}</small>`:''}</b><em>${r.n>=3&&r.r<6?'🔀':''}</em></button>`).join('')}</div>`
    +`<div class="pt-chips pt-center">${shopChip('pwear','wear','👗 Mua thêm')}${shopChip('pwing','wing','🪽 Mua cánh')}</div>`;
}

function board(c){
  const kinds=TT()?`<div class="pt-chips">${chip('bkind',{k:'week'},S.bkind!=='power','🏆 Bé cưng tuần')}${chip('bkind',{k:'power'},S.bkind==='power','💪 Lực chiến')}</div>`:'';
  const b=S.board;if(!b)return kinds+'<p class="pt-empty">⏳</p>';if(b.error)return kinds+'<p class="pt-empty">📡</p>';
  if(!b.top?.length)return kinds+`<p class="pt-empty">${S.bkind==='power'?'💪':'🏆'}</p>`;
  const pw=b.kind==='power';
  return kinds+`<ol class="pt-board">${b.top.map((r,i)=>`<li class="${r.me?'me':''}"><span>${i+1}</span>${petPic(c,{b:r.b,c:r.c},'sit',48,accOf(c,r),fxRef(c,r))}<b data-no-translate><span>${pw?rankTag({r:r.r||0,legend:breedOf(r.b)?.fuse==='legend'})+' ':''}${esc(r.name)}</span><small>${esc(r.owner)}</small></b><em>${pw?'💪':''}${r.pts}</em></li>`).join('')}</ol>`;
}

/* ---- 🧬 fusing three pets ---- */
function lab(v,c){
  const t=TT();if(!t)return '<p class="pt-empty">⏳</p>';
  const x=X(),f=fusion(),all=allPets();
  // 👑 the first pet picked is the main one (it goes up and keeps its breed); the two others are the ingredients (owner 19/10)
  const slots=[0,1,2].map(i=>{const p=f.ps[i],tag=i?'🧪 Nguyên liệu':'👑 Bé chính';return `<div class="pt-slotw${i?'':' main'}">${p?`<button type="button" class="pt-slot on" data-pt="fz" data-id="${esc(p.id)}" aria-label="Bỏ chọn ${esc(p.n)}">${petPic(c,p,'sit',64,{})}${rankTag(p)}</button>`:`<span class="pt-slot" aria-hidden="true">＋</span>`}<small>${tag}</small>${p&&i?`<button type="button" class="pt-tomain" data-pt="fzmain" data-id="${esc(p.id)}">👑 Làm bé chính</button>`:''}</div>`;}).join('');
  let info=`<p class="pt-muted pt-center">Chọn 3 bé, chó mèo đều được. Bé chọn đầu là 👑 bé chính: lên hạng, được chọn giữ giống hay đổi giống; hai bé kia là nguyên liệu. Ba bé SSS ghép ra 🌟 huyền thoại. Ghép bao nhiêu lần cũng được.</p>`;
  if(f.ps.length===3){const m=f.ps[0],to=f.low===6?'🌟 Huyền thoại':`hạng <span class="pt-rk r${f.low+1}">${esc(RNAME(f.low+1))}</span>`;
    const mix=f.recipe?`<br>${chip('fzmix',{},S.fzMix,`🧬 Thử ra giống lai <b>${esc(breedOf(f.recipe.to)?.name||'')}</b>`)}${f.recipe.coats?' <small>(cần 3 màu lông khác nhau)</small>':''}${S.fzMix?'<br><small>Ra giống lai thì là bé mới, ba bé về quê với bà.</small>':''}`:'';
    const pick=f.choices.includes(S.fzBreed)?S.fzBreed:m.b;
    const breeds=f.choices.length>1&&!f.why?`<div class="pt-fzbreed"><b>Thành công thì ${esc(m.n)} là giống:</b><div class="pt-chips pt-center">${f.choices.map(id=>{const bb=breedOf(id);return chip('fzbreed',{id:id===m.b?'':id},pick===id,`${petPic(c,{b:id,c:0},'sit',30,{})}<span>${id===m.b?'Giữ ':''}${bb?.fuse==='legend'?'🌟 ':''}${esc(bb?.name||id)}</span>`);}).join('')}</div></div>`:'';
    info=`<p class="pt-fz">⬆️ <b data-no-translate>${esc(m.n)}</b> lên ${to}${x?.boost?' <small>(📺 may mắn hơn)</small>':''} · 💸 ${fmt(f.fee)} xu${mix}</p>`+breeds+
      (f.why?`<p class="pt-fzwarn">${esc(f.why)}</p>`:f.lose?`<p class="pt-fzwarn">⚠️ Từ hạng S trở lên: trượt thì 2 bé nguyên liệu sẽ mất, chỉ còn bé chính.</p>`:'<p class="pt-muted pt-center">Trượt thì ba bé vẫn ở lại, chỉ mất phí.</p>');}
  const group=(at,title)=>{const list=all.filter(p=>p.at===at);if(!list.length)return '';
    return `<h4>${title}</h4><div class="pt-picks sm">${list.map(p=>{const on=S.fz.includes(p.id),why=on?'':fuseWhy(p);
      return `<button type="button" class="pt-pick${on?' on':''}" data-pt="fz" data-id="${esc(p.id)}" aria-pressed="${on}"${why||(!on&&S.fz.length>=3)?' disabled':''}${why?` title="${esc(why)}"`:''}>${petPic(c,p,'sit',64,{})}<b data-no-translate>${esc(p.n)}</b><small>${rankTag(p)}${why?` ${esc(why)}`:''}</small></button>`;}).join('')}</div>`;};
  const table=`<details class="pt-more"><summary>📜 Hạng và tiền thưởng</summary><div class="pt-tbl"><table><thead><tr><th>Hạng</th><th>Thưởng</th><th>Tối đa/ngày</th><th>Phí ghép</th></tr></thead><tbody>${t.ranks.map(r=>`<tr><td><span class="pt-rk r${r.id}">${esc(r.rank)}</span> ${esc(r.name)}</td><td>+${r.profit}%</td><td>${fmt(r.cap)}</td><td>${fmt(r.fee)}</td></tr>`).join('')}</tbody></table></div>
    <p class="pt-muted">SSS thân thiết: ${t.sss_bond.map(s=>`từ ${s.at} điểm thân +${s.pct}% (tối đa ${fmt(s.cap)})`).join(', ')}. Ghép bé hạng cao hơn cùng nhóm thì dễ thành hơn. Ba bé cùng giống có thể ra 🧪 đột biến. Lên SSS được bộ lông ${t.fx.filter(f=>f.id!=='dot_bien').map(f=>f.emoji+' '+esc(f.name)).join(', ')}.</p></details>`;
  const recipes=`<details class="pt-more"><summary>🧬 Công thức giống lai (${t.recipes.length})</summary><ul class="pt-recipes">${t.recipes.map(r=>{const to=breedOf(r.to);return `<li>${petPic(c,{b:r.to,c:0},'sit',40,{})}<span><b>${esc(to?.name||r.to)}</b> <small>từ hạng ${esc(r.floor)}</small><br><small>${r.of.map(id=>esc(breedOf(id)?.name||id)).join(' + ')}</small></span></li>`;}).join('')}
    <li>${petPic(c,{b:t.legend.dog,c:0,r:6},'sit',40,{})}${petPic(c,{b:t.legend.cat,c:0,r:6},'sit',40,{})}<span><b>🌟 Huyền thoại</b><br><small>3 bé SSS · ${fmt(t.ranks[6].fee)} xu · giống nào cũng lên được, giữ giống hoặc đổi sang ${esc(breedOf(t.legend.dog)?.name||'')} / ${esc(breedOf(t.legend.cat)?.name||'')}</small></span></li></ul></details>`;
  const ret=(x?.ret||[]).length?`<details class="pt-more"><summary>👵 Đang nghỉ ở nhà bà (${x.ret.length})</summary><div class="pt-strip wrap">${x.ret.slice().reverse().map(r=>`<span class="pt-mini" title="${esc(r.n)}">${petPic(c,{b:r.b,c:r.c,r:r.r,fx:r.fx},'sleep',44,{})}</span>`).join('')}</div></details>`:'';
  return forgeLink('plab')+autoCard('lab')+`<h4 class="pt-own">🧬 Tự chọn ba bé</h4><section class="pt-card pt-center"><div class="pt-slots">${slots}</div>${info}</section>`+group('home','🐾 Ở nhà')+group('ken',`🏠 Trại nuôi · ${(x?.ken||[]).length}/${t.limits.kennel}`)+group('farm','🌾 Ở quê')+kennel()+table+recipes+ret;
}

/* ---- 🧰 gear: the bag, the shop, strolls that find things ---- */
function gear(v,c){
  const t=TT();if(!t)return '<p class="pt-empty">⏳</p>';
  const x=X(),bag=x?.gear||[],w=x?.today?.stroll||0;
  const top=S.host?(S.gv==='buy'?`<div class="pt-chips"><button type="button" class="pt-chip" data-action="jrForge" data-tab="pgear">🎒 Túi ${bag.length}/${t.limits.gear} · ⚒️ Cường hóa</button></div>`
    :`<div class="pt-chips"><button type="button" class="pt-chip" data-action="jrAccShop" data-tab="pgear">🛍️ Mua linh kiện</button>${chip('stroll',{},false,`🦮 Dạo tìm đồ ${w}/${t.limits.stroll_day}`)}</div>`):`<div class="pt-chips">${chip('gv',{v:'bag'},S.gv!=='buy',`🎒 Túi ${bag.length}/${t.limits.gear}`)}${chip('gv',{v:'buy'},S.gv==='buy','🛍️ Tiệm')}${chip('stroll',{},false,`🦮 Dạo tìm đồ ${w}/${t.limits.stroll_day}`)}</div>`;
  if(S.gv==='buy'){
    const models=t.gear.models[S.gbslot]||[],r=Math.min(S.grank,t.gear.shop.length-1),slot=t.gear.slots.find(s=>s.id===S.gbslot),st=t.stats.find(s=>s.id===slot?.stat);
    return top+`<div class="pt-chips">${t.gear.slots.map(s=>chip('gbslot',{slot:s.id},S.gbslot===s.id,s.emoji,s.name)).join('')}</div>
      <div class="pt-tiles">${models.map((m,i)=>`<button type="button" class="pt-tile${S.gmodel===i?' on':''}${m.vip?' vip':''}" data-pt="gmodel" data-m="${i}" aria-pressed="${S.gmodel===i}" aria-label="${esc(m.name)}" title="${esc(m.name)}"><span aria-hidden="true">${m.emoji}</span><small>${m.vip?'💎 ':''}${esc(m.name)}</small></button>`).join('')}</div>
      <div class="pt-chips">${t.gear.shop.map((p,i)=>chip('grank',{r:i},r===i,`<span class="pt-rk r${i}">${esc(RNAME(i))}</span> ${fmt(p*(models[S.gmodel]?.mult||1))}`)).join('')}</div>
      ${qtyPick(t.gear.shop[r]*(models[S.gmodel]?.mult||1))}
      <p class="pt-muted pt-center">${st?.emoji||''} +${t.gear.base[r]+(models[S.gmodel]?.bonus||0)} ${esc(st?.name?.toLowerCase()||'')}${models[S.gmodel]?.bonus?` (💎 hàng xịn +${models[S.gmodel].bonus})`:''} · cường hóa tới +${t.gear.lv_max} · hạng cao hơn: dạo tìm hoặc ghép 3 món.</p>`;
  }
  if(!bag.length)return top+'<p class="pt-empty">🎒</p><p class="pt-muted pt-center">Dắt bé đi dạo để tìm đồ, hoặc ghé tiệm.</p>';
  const g=gearOf(S.g),u=gearUp(g),L=t.gear.lv_max,slotName=id=>(t.gear.slots.find(x=>x.id===id)||{}).name||'';
  // 📈 the way up (owner 19/10): ✨ +1…+L first, then three of a kind and rank → the next rank, D … SSS
  const steps=u?`<ol class="pt-gsteps"><li class="${u.max?'ok':'now'}">✨ Cường hóa lên +${L} <b>${g.lv}/${L}</b></li><li class="${u.have>=2?'ok':u.max?'now':''}">🎒 Thêm 2 món ${esc(slotName(g.s).toLowerCase())} hạng ${esc(g.rank)} chưa gắn <b>${u.have}/2</b>${u.have<2&&g.r<t.gear.shop.length?` ${chip('gshop',{slot:g.s,r:g.r,n:2-u.have},false,'🛍️ Mua')}`:''}</li><li class="${u.ok?'now':''}">📈 Lên hạng ${esc(u.next)} · ${fmt(u.fee)} xu${u.lose?' · <em>trượt mất 2 món nguyên liệu</em>':' · trượt chỉ mất phí'}</li></ol>`
    :g?'<p class="pt-muted">👑 Hạng SSS là cao nhất.</p>':'';
  const card=g?`<section class="pt-card pt-center"><p class="pt-gear-big" aria-hidden="true">${g.emoji}</p><h3>${esc(g.name)} <span class="pt-rk r${g.r}">${esc(g.rank)}</span>${g.lv?` +${g.lv}`:''}</h3>
    <p class="pt-muted">${(t.stats.find(s=>s.id===g.stat)||{}).emoji||''} +${g.value}${g.on?` · 🐾 ${esc(petName(g.on))}`:''}</p>${steps}
    <div class="pt-chips">${u?.ok?chip('gfuse',{},false,`📈 Lên hạng ${esc(u.next)} · ${fmt(u.fee)}`):''}${chip('gdrop',{},false,'🗑️','Bỏ món này')}</div></section>`:'';
  // the ladder: each slot × rank, how many (⬆ when one at +L has two free mates)
  const R7=[0,1,2,3,4,5,6];
  const ladder=`<div class="pt-gl" role="table" aria-label="Linh kiện theo hạng"><div class="pt-gl-r" role="row"><span role="columnheader"></span>${R7.map(r=>`<span role="columnheader" class="pt-rk r${r}">${esc(RNAME(r))}</span>`).join('')}</div>${t.gear.slots.map(sl=>`<div class="pt-gl-r" role="row"><span role="rowheader" title="${esc(sl.name)}">${sl.emoji}</span>${R7.map(r=>{
    const l=bag.filter(x=>x.s===sl.id&&x.r===r),up=r<6&&l.some(x=>x.lv>=L&&l.filter(y=>y.id!==x.id&&!y.on).length>=2),on=g&&g.s===sl.id&&g.r===r;
    return l.length?`<button type="button" role="cell" class="pt-gl-c${up?' up':''}${on?' on':''}" data-pt="gpick" data-slot="${sl.id}" data-r="${r}" aria-label="${esc(sl.name)} ${esc(RNAME(r))}: ${l.length}${up?' · lên hạng được':''}">${l.length}${up?' <i aria-hidden="true">⬆</i>':''}</button>`:'<span role="cell" class="pt-gl-c off">·</span>';}).join('')}</div>`).join('')}</div>`;
  const how=`<p class="pt-muted pt-center pt-ghow">📈 Lên hạng D → C → B → A → S → SS → SSS: cường hóa một món tới +${L}, rồi ghép với 2 món cùng loại, cùng hạng. Từ hạng S, ghép trượt mất 2 món nguyên liệu.</p>`;
  const order=t.gear.slots.map(s=>s.id),list=bag.slice().sort((a,b)=>order.indexOf(a.s)-order.indexOf(b.s)||b.r-a.r||b.lv-a.lv);
  return top+forgeLink('pgear')+autoCard('gear')+(bag.length?'<h4 class="pt-own">🧰 Tự chọn món</h4>':'')+card+(g?'':how)+ladder+`<div class="pt-list">${list.map(x=>`<button type="button" class="pt-item${x.id===S.g?' on':''}" data-pt="gsel" data-id="${esc(x.id)}" aria-pressed="${x.id===S.g}"><span class="pt-ico" aria-hidden="true">${x.emoji}</span><b>${esc(x.name)} <span class="pt-rk r${x.r}">${esc(x.rank)}</span>${x.lv?` +${x.lv}`:''}${x.on?`<small> · 🐾 ${esc(petName(x.on))}</small>`:''}</b><em>+${x.value}</em></button>`).join('')}</div>`;
}

/* ---- 📸 photo booth: the character beside the pet, in a frame; saved as a PNG on this device only ---- */
const FRAME={nang:['#fff4cf','#ffd27a','🌼'],tim:['#ffe3ea','#f5a9bc','💗'],tet:['#ffe1d6','#e05a4f','🧧'],sao:['#e6ecff','#a9c0f5','⭐']};
function photoSVG(p,c){
  const st=S.env.api.state,L=lookup(c,p.b,p.c),[bg,edge,em]=FRAME[S.frame]||FRAME.nang;
  const me=figureSVG(lookOf(st),st?.journey?.gender,{w:120,h:170}).replace('<svg ','<svg x="14" y="22" ');
  const pet=L?petSVG(L.breed,L.coat,S.pose,p.w||{},120,'pet-svg',fxOf(p)).replace('<svg ','<svg x="118" y="72" '):'';
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

/* ---- 🛍️ Cửa hàng (v4/shop-shelves.js, owner 23/10 "gọn và dễ dùng như các game khác"): the pets' shop as plain cards for
 * the shop's grid (its filters, rarity border and badges) and the picked card's detail, drawn with this dialog's own picks
 * (S.breed, S.wk, S.item, S.gbslot + S.gmodel), its main button (data-pt="go") and jr_pet_* commands. `part`: buy | wear |
 * wing | toy | gear. ---- */
const SHOP_PARTS=new Set(['buy','wear','wing','toy','gear']);
/** Inside the shop a purchase asks first only when it is big for this player and ☑️ Không hỏi lại is not ticked
 * (payment.js askBuy); the dialog keeps its own rule (`old`). */
function shopAsk(pr,old=true){return S.host&&SHOP_PARTS.has(S.part)?askBuy(J(),pr):old;}
function shopPart(env,part){
  S.env=env;S.host='sheet';bindSheet();
  if(S.part!==part){S.part=part;S.flash=null;S.wk='';S.wslot='';S.item='';S.breed='';S.bq=1;S.gopen=false;}   // another shelf: a fresh pick
  S.sub='';
  if(part==='gear'){S.tab='gear';S.gv='buy';}else{S.tab='shop';if(part!=='buy')S.kind=part;else if(!['dog','cat'].includes(S.kind))S.kind='dog';}
}
/** Pick a card of the shop (id '' puts it back): a breed, a piece, a toy, or a gear model 'slot|model'. */
export function petShopPick(env,part,id){
  shopPart(env,part);S.bq=1;S.flash=null;
  if(part==='buy'){const b=id&&breedOf(id);S.breed=b?b.id:'';S.coat=0;if(b)S.kind=b.kind;}
  else if(part==='wear'||part==='wing'){S.wk=id&&wItem(id)?id:'';S.wrank=0;}
  else if(part==='toy')S.item=shopItems().some(x=>x.id===id)?id:'';
  else if(part==='gear'){const [sl,m]=String(id||'').split('|'),ok=!!TT()?.gear?.models?.[sl]?.[Number(m)];S.gopen=ok;if(ok){S.gbslot=sl;S.gmodel=Number(m);S.grank=0;}}
}
/** Three of one rank owned now (what ⚒️ Cường hóa ghép): the shop's detail offers the way there. */
const threeOf=keys=>{const n=new Map();for(const k of keys)n.set(k,(n.get(k)||0)+1);return [...n.values()].some(x=>x>=3);};
const ddmm=x=>x?`${x.slice(8,10)}/${x.slice(5,7)}`:'';
/** {cards [{id, art, name, price, own, many, on, sel, g, note, locked}], groups, lux, note, detail, busy}, null
 * while the catalogue is not there, {empty} outside the story. */
export function petShopModel(env,part){
  shopPart(env,part);
  const v=V(),c=CAT();if(!v||!c)return null;
  if(!v.story)return {cards:[],empty:'Chỉ có trong hành trình.'};
  if(['wear','wing'].includes(part)?!WARD():part==='gear'&&!TT())return null;
  const note=part!=='buy'&&!allPets().length?`<section class="pt-card pt-center pt-none"><h3>Chưa có bé nào</h3>
    <div class="pt-chips pt-center"><button type="button" class="pt-chip on" data-action="jrAccShop" data-tab="pbuy">🐶 Mua bé</button><button type="button" class="pt-chip" data-action="pets" data-tab="adopt">🏠 Nhận nuôi</button></div></section>`:'';
  const out={cards:[],groups:null,lux:null,note,detail:null,busy:S.busy};
  if(part==='buy')shopBreeds(c,out);
  else if(part==='wear'||part==='wing')shopWear(part==='wing',out);
  else if(part==='toy')shopToys(out);
  else if(part==='gear')shopGear(out);
  const d=out.detail;
  if(d){const [label,,why]=main(),w=why&&why.trim();
    d.bar=label?`<footer class="pt-bar">${w?`<small class="pt-why">${esc(why)}</small>`:''}<button type="button" class="btn primary big pt-main" data-pt="go"${S.busy||w||why===' '?' disabled':''}>${esc(label)}</button></footer>`:'';
    d.flash=`<p class="pt-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;}
  return out;
}
function shopBreeds(c,out){
  out.cards=(c.breeds||[]).filter(b=>b.shop!==false&&(b.kind==='dog'||b.kind==='cat')).map(b=>({id:b.id,art:petPicture(b,b.coats[0],'sit',{},72),name:b.name,price:b.price,
    own:allPets().filter(p=>p.b===b.id).length,many:true,sel:S.breed===b.id,g:b.kind}));
  out.groups=[['dog','🐶 Chó'],['cat','🐱 Mèo']];
  const b=breedOf(S.breed);if(!b)return;
  const coat=b.coats[S.coat]||b.coats[0];
  out.detail={id:b.id,title:esc(b.name),stage:petSVG(b,coat,'happy',{},140),
    info:`<p class="as-d-price"><b>${fmt(b.price)} xu</b> / bé</p><p class="small">✨ ${esc(b.trait)}</p>${b.nick&&b.line?`<p class="as-d-note">${esc(b.line)}</p>`:''}<p class="as-d-note">🎲 Hạng D hoặc C</p>`,
    controls:`<div class="pt-chips pt-coats" role="group" aria-label="Màu lông">${b.coats.map((k,i)=>chip('coat',{c:i},S.coat===i,`<i style="background:${esc(k.b)};box-shadow:inset -6px 0 0 ${esc(k.m)}"></i>`,k.name)).join('')}</div>
      <label class="pt-name"><span class="sr-only">Tên bé</span><input name="nick" maxlength="${c.name_max}" value="${esc(S.nick)}" placeholder="${esc(b.nick||'Tên bé')}" autocomplete="off"></label>
      ${qtyPick(b.price)}${bq()>1?`<p class="pt-muted">Tên các bé: ${esc(nameHint((S.nick||b.nick||b.name).trim().slice(0,16),bq()))}</p>`:''}`,
    forge:TT()&&threeOf(allPets().filter(p=>!p.legend).map(p=>p.r||0))?'plab':''};
}
function shopWear(wing,out){
  const W=WARD(),inKind=i=>wing?i.slot==='back':i.slot!=='back',mine=myItems();
  out.cards=W.items.filter(i=>inKind(i)&&!i.lux&&i.on_sale!==false).map(i=>({id:i.id,art:tryOn(i.id,0,72),name:`${i.emoji} ${i.name}`,price:i.price,
    own:mine.filter(x=>x.k===i.id).length,many:true,on:mine.some(x=>x.k===i.id&&x.on),sel:S.wk===i.id,g:i.slot,note:i.sale?`${fmt(i.price)} xu · ⏳ ${ddmm(i.sale[1])}`:undefined}));
  if(!wing)out.groups=W.slots.filter(x=>x.id!=='back').map(x=>[x.id,`${x.emoji} ${x.name}`]);
  out.lux=W.items.filter(i=>inKind(i)&&i.lux).map(i=>({id:i.id,art:tryOn(i.id,4,72),name:`${i.emoji} ${i.name}`,price:0,note:'🔀 Ghép mới có',locked:true,own:mine.filter(x=>x.k===i.id).length,many:true}));
  const it=wItem(S.wk);if(!it||!inKind(it))return;
  const set=(W.sets||[]).find(x=>x.id===it.set),p=cur(),owned=mine.filter(i=>i.k===it.id);
  out.detail={id:it.id,title:`${esc(it.emoji)} ${esc(it.name)}`,stage:tryOn(it.id,S.wrank,150),
    info:`<p class="as-d-price"><b>${fmt(wPrice(it,S.wrank))} xu</b> · hạng ${RKS[S.wrank]}</p><p class="small">${esc(it.desc)}</p>${set?`<p class="pt-muted">${set.emoji} Một món của <b>${esc(set.name)}</b>. ${esc(set.desc)}</p>`:''}
      <ul class="as-d-gives"><li>${S.wrank?`💰 Hạng C: +${W.bonus[1]}% tiền làm việc khi bé mặc`:'🎀 Hạng D: để diện cho xinh, chưa cộng tiền'}</li></ul>${owned.length?`<p class="as-d-note">Bạn có ${owned.length} món này.</p>`:''}`,
    controls:`<div class="pt-chips pt-center" role="group" aria-label="Hạng">${[0,1].map(r=>chip('wrank',{r},S.wrank===r,`${RK(r)} ${fmt(wPrice(it,r))} xu`)).join('')}</div>${qtyPick(wPrice(it,S.wrank))}
      ${owned.length&&p?`<div class="pt-chips pt-center">${chip('wput',{key:`${it.id}|${Math.max(...owned.map(i=>i.r))}`,pet:p.id},false,`👗 Mặc luôn cho ${esc(p.n)}`)}</div>`:''}`,
    forge:threeOf(owned.filter(i=>i.r<6).map(i=>i.r))?'pward':''};
}
function shopToys(out){
  out.cards=shopItems().map(it=>({id:it.id,art:`<span class="as-emoji">${esc(it.emoji)}</span>`,name:it.name,price:it.price,own:own(it.id),many:true,sel:S.item===it.id,
    g:it.kind==='dog'||it.kind==='cat'?it.kind:''}));
  if(out.cards.some(x=>x.g))out.groups=[['dog','🐶 Cho chó'],['cat','🐱 Cho mèo']];
  const it=shopItems().find(x=>x.id===S.item);if(!it)return;
  out.detail={id:it.id,title:`${esc(it.emoji)} ${esc(it.name)}`,stage:`<span class="as-emoji big" aria-hidden="true">${esc(it.emoji)}</span>`,
    info:`<p class="as-d-price"><b>${fmt(it.price)} xu</b></p><ul class="as-d-gives"><li>${it.uses?`🔁 Dùng được ${it.uses} lần`:'♾️ Giữ mãi, chơi bao nhiêu cũng được'}</li></ul>${own(it.id)?`<p class="as-d-note">Đang có ${it.uses?`${own(it.id)} lượt`:own(it.id)}.</p>`:''}`,
    controls:qtyPick(it.price),forge:''};
}
function shopGear(out){
  const t=TT(),bag=X()?.gear||[];
  for(const sl of t.gear.slots)(t.gear.models[sl.id]||[]).forEach((m,i)=>out.cards.push({id:`${sl.id}|${i}`,art:`<span class="as-emoji">${m.emoji}</span>`,name:m.name,
    price:t.gear.shop[0]*(m.mult||1),note:`từ ${fmt(t.gear.shop[0]*(m.mult||1))} xu`,own:bag.filter(x=>x.s===sl.id&&x.name===m.name).length,many:true,
    on:bag.some(x=>x.s===sl.id&&x.name===m.name&&x.on),sel:!!S.gopen&&S.gbslot===sl.id&&S.gmodel===i,g:sl.id}));
  out.groups=t.gear.slots.map(s=>[s.id,`${s.emoji} ${s.name}`]);
  const m=S.gopen&&t.gear.models[S.gbslot]?.[S.gmodel];if(!m)return;
  const r=Math.min(S.grank,t.gear.shop.length-1),slot=t.gear.slots.find(s=>s.id===S.gbslot),stt=t.stats.find(s=>s.id===slot?.stat),one=t.gear.shop[r]*(m.mult||1);
  out.detail={id:`${S.gbslot}|${S.gmodel}`,title:`${m.emoji} ${esc(m.name)}`,stage:`<span class="as-emoji big" aria-hidden="true">${m.emoji}</span>`,
    info:`<p class="as-d-price"><b>${fmt(one)} xu</b> · hạng ${esc(RNAME(r))}</p><ul class="as-d-gives"><li>${stt?.emoji||''} +${t.gear.base[r]+(m.bonus||0)} ${esc(stt?.name?.toLowerCase()||'')}${m.bonus?` (💎 hàng xịn +${m.bonus})`:''}</li></ul>`,
    controls:`<div class="pt-chips pt-center" role="group" aria-label="Hạng">${t.gear.shop.map((p,i)=>chip('grank',{r:i},r===i,`<span class="pt-rk r${i}">${esc(RNAME(i))}</span> ${fmt(p*(m.mult||1))}`)).join('')}</div>${qtyPick(one)}`,
    forge:bag.length?'pgear':''};
}
