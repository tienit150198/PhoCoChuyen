/** 🧩 Ghép ba Phố Mây (game/tile_match.py is the authority). A triple-match game in its own dialog, opened from Khu phố
 * and the town map ("tileMatch"). Phone first (390 × 844, 360 × 780; landscape puts the tray beside the board), few
 * words, one main button, the rules behind "?".
 *
 * The page plays the level locally with the same rules as the server (class Game below mirrors tile_match.Game,
 * and rng() is the same mulberry32, so a 🔀 shuffle lands the same on both sides). When the board is cleared it sends
 * every tap and booster (`jr_tile_end {lv, moves}`); the server rebuilds the level from its seed, replays them and
 * checks the time. Boosters are granted one at a time by the server first (`jr_tile_boost`: free today, or xu).
 *
 * Drawing: one element per tile, positioned by transform; a move only changes where a tile belongs and the CSS
 * transition flies it (board → tray, tray → hold, undo back). Three of a kind pop; a quick run of triples is a combo. */
import {escapeHTML as esc} from '../icons.js';
import {actBar,helpBtn} from '../ui-kit.js';
import {stylesheet} from '../lazy.js';

const ICE=1,KEY=2,LOCK=4,HOLD=3,SLOT_MAX=1;
const MOVE={undo:-1,shuffle:-2,push:-3,slot:-4},BOOST_OF={'-1':'undo','-2':'shuffle','-3':'push','-4':'slot'};
const BOOSTS=[['undo','↩','Hoàn tác'],['shuffle','🔀','Xáo'],['push','⇪','Đẩy ra'],['slot','➕','Thêm ô']];
const MIN_TAP_MS=250,MIN_LEVEL_MS=20000;
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const T={dlg:null,env:null,view:'home',level:null,g:null,lv:0,moves:[],t0:0,busy:false,flash:null,combo:0,lastClear:-9,
  result:null,cache:new Map(),els:new Map(),lay:null,ro:null,sending:false,why:null};

/* ---------------------------------------------------------------- rules (mirror of game/tile_match.py) */
/** mulberry32, bit for bit tile_match.Rng. */
export function rng(seed){
  let a=seed>>>0;
  const next=()=>{a=(a+0x6D2B79F5)>>>0;let t=Math.imul(a^(a>>>15),1|a);t=(t+Math.imul(t^(t>>>7),61|t))^t;return (t^(t>>>14))>>>0;};
  return {next,below:n=>n>0?next()%n:0};
}
export const shuffleSeed=(seed,n)=>(seed^(Math.imul(0x9E3779B1,n+1)>>>0))>>>0;
export class Game{
  constructor(lv){
    this.lv=lv;this.n=lv.tiles.length;this.kind=lv.tiles.map(t=>t[3]);this.ice=lv.tiles.map(t=>t[4]&ICE?1:0);
    this.where=Array(this.n).fill('b');this.block=lv.b.map(b=>b.length);this.under=Array.from({length:this.n},()=>[]);
    lv.b.forEach((b,i)=>b.forEach(j=>this.under[j].push(i)));
    this.tray=[];this.hold=[];this.cap=lv.cap;this.undoStack=[];this.shuffles=0;this.slots=0;this.gone=0;this.taps=0;this.lost=false;
    this.used={undo:0,shuffle:0,push:0,slot:0};
  }
  get won(){return this.gone===this.n;}
  get over(){return this.lost||this.won;}
  open(t){return this.where[t]==='h'||(this.where[t]==='b'&&this.block[t]===0);}
  toTray(t){
    const k=this.kind[t];let at=this.tray.length;
    for(let i=this.tray.length-1;i>=0;i--)if(this.kind[this.tray[i]]===k){at=i+1;break;}
    this.tray.splice(at,0,t);this.where[t]='t';
    const same=this.tray.filter(x=>this.kind[x]===k);
    if(same.length===3){for(const x of same){this.tray.splice(this.tray.indexOf(x),1);this.where[x]='g';}this.gone+=3;this.undoStack=[];return same;}
    if(this.tray.length>=this.cap)this.lost=true;
    return null;
  }
  tap(t){
    if(this.over||!Number.isInteger(t)||t<0||t>=this.n||!this.open(t))throw new Error('tap');
    this.taps++;
    if(this.where[t]==='b'&&this.ice[t]){this.ice[t]--;return 'ice';}
    if(this.where[t]==='h'){const i=this.hold.indexOf(t);this.hold.splice(i,1);this.undoStack.push([t,i]);}
    else{for(const d of this.under[t])this.block[d]--;this.undoStack.push([t,null]);}
    return this.toTray(t)||'tray';
  }
  canUndo(){return !this.over&&this.undoStack.length>0;}
  undo(){
    if(!this.canUndo())throw new Error('undo');
    const [t,i]=this.undoStack.pop();this.tray.splice(this.tray.indexOf(t),1);
    if(i===null){this.where[t]='b';for(const d of this.under[t])this.block[d]++;}else{this.hold.splice(i,0,t);this.where[t]='h';}
    this.used.undo++;
  }
  boardIds(){const out=[];for(let t=0;t<this.n;t++)if(this.where[t]==='b')out.push(t);return out;}
  canShuffle(){return !this.over&&this.boardIds().length>=2;}
  shuffle(){
    if(!this.canShuffle())throw new Error('shuffle');
    const ids=this.boardIds(),kinds=ids.map(t=>this.kind[t]),r=rng(shuffleSeed(this.lv.seed,this.shuffles));
    for(let i=kinds.length-1;i>0;i--){const j=r.below(i+1);[kinds[i],kinds[j]]=[kinds[j],kinds[i]];}
    ids.forEach((t,i)=>{this.kind[t]=kinds[i];});this.shuffles++;this.used.shuffle++;
  }
  canPush(){return !this.over&&this.tray.length>0&&this.hold.length===0;}
  push(){if(!this.canPush())throw new Error('push');const out=this.tray.slice(0,HOLD);this.tray=this.tray.slice(HOLD);for(const t of out)this.where[t]='h';this.hold=out;this.undoStack=[];this.used.push++;}
  canSlot(){return !this.over&&this.slots<SLOT_MAX;}
  slot(){if(!this.canSlot())throw new Error('slot');this.slots++;this.cap++;this.used.slot++;}
  move(m){if(m>=0)return this.tap(m);const b=BOOST_OF[m];if(!b)throw new Error('move');this[b]();return b;}
}

/* ---------------------------------------------------------------- state from the server */
const S=()=>T.env?.api?.state?.journey?.tile||{lv:0,max:100,pm:0,pct:'0',n:0,cap:15,free:{},price:{}};
const wallet=()=>T.env?.api?.state?.journey?.wallet??0;
const sound=()=>T.env?.sound||null;
function priceOf(kind){const st=S(),paid=(st.cur?.p||{})[kind]||0;return (st.price?.[kind]||0)*(2**paid);}
function freeOf(kind){return (S().free||{})[kind]||0;}
async function loadLevel(lv){
  if(T.cache.has(lv))return T.cache.get(lv);
  const r=await fetch(`/api/tile/level?lv=${lv}`,{credentials:'same-origin'});
  if(!r.ok)throw new Error('Chưa tải được màn chơi.');
  const data=await r.json();
  if(T.cache.size>=12)T.cache.delete(T.cache.keys().next().value);   // bounded: a dozen levels at most
  T.cache.set(lv,data);return data;
}

/* ---------------------------------------------------------------- the dialog */
function dialog(){
  if(T.dlg)return T.dlg;
  const d=document.createElement('dialog');d.className='sheet v4-sheet narrow tm-sheet';d.setAttribute('aria-labelledby','tm-title');
  d.innerHTML='<div class="tm-root"></div>';document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){close();return;}
    const tile=e.target.closest('.tm-tile');
    if(tile&&d.contains(tile)){e.preventDefault();if(e.detail===0)tapTile(Number(tile.dataset.id));return;}   // Enter / Space on a focused tile
    const el=e.target.closest('[data-tm]');if(!el||!d.contains(el))return;e.preventDefault();
    if(el.getAttribute('aria-disabled')==='true'){why(el.dataset.why);return;}
    act(el.dataset.tm,el.dataset);
  });
  d.addEventListener('pointerdown',e=>{const el=e.target.closest('.tm-tile');if(!el||!d.contains(el))return;e.preventDefault();tapTile(Number(el.dataset.id));});
  d.addEventListener('cancel',e=>{e.preventDefault();close();});
  d.addEventListener('close',()=>{T.ro?.disconnect();T.ro=null;});
  T.dlg=d;return d;
}
async function close(){
  if(T.view==='play'&&T.g&&!T.g.over&&T.moves.length){
    if(!(await T.env.confirmAction?.('Rời màn?','Ván này chưa xong sẽ không được tính.','Rời màn')))return;
  }
  if(T.view==='play'&&T.g&&!T.g.won)quit();
  T.view='home';T.dlg?.close();
}
function quit(){T.env.api.command('jr_tile_quit',{}).catch(()=>{});}

/** The menu entry, the town map's door, "Có gì mới". */
export async function openTileMatch(env){
  T.env=env;await stylesheet('/css/tile-match.css');
  const d=dialog();if(!d.open)d.showModal();
  if(T.view!=='play')T.view='home';
  paint();
}
export async function tileMatchAction(action,data,el,env){if(action!=='tileMatch')return false;await openTileMatch(env);return true;}

async function act(a,ds){
  switch(a){
    case'close':await close();break;
    case'play':await start(Number(ds.lv)||nextLevel());break;
    case'again':await start(T.lv);break;
    case'next':await start(Math.min(100,T.lv+1));break;
    case'home':if(T.view==='play'&&T.g&&!T.g.over)quit();T.view='home';T.result=null;paint();break;
    case'boost':await boost(ds.k);break;
  }
}
const nextLevel=()=>Math.min(100,S().lv+1);
function why(text){if(!text)return;T.why=text;paintWhy();clearTimeout(T.whyT);T.whyT=setTimeout(()=>{T.why=null;paintWhy();},4000);sound()?.error?.();}
function paintWhy(){const el=T.dlg?.querySelector('.tm-why');if(el){el.textContent=T.why?`⚠ ${T.why}`:'';el.hidden=!T.why;}}

/* ---------------------------------------------------------------- start, boosters, end */
async function start(lv){
  if(T.busy)return;T.busy=true;T.flash=null;
  try{
    const [,level]=await Promise.all([T.env.api.command('jr_tile_start',{lv}),loadLevel(lv)]);
    T.lv=lv;T.level=level;T.g=new Game(level);T.moves=[];T.t0=Date.now();T.combo=0;T.lastClear=-9;T.result=null;T.view='play';T.sending=false;
    T.els=new Map();
  }catch(e){T.flash=e.message||'Chưa mở được màn.';T.view='home';}
  T.busy=false;paint();
}
async function boost(kind){
  const g=T.g;if(!g||g.over||T.busy)return;
  const can={undo:g.canUndo(),shuffle:g.canShuffle(),push:g.canPush(),slot:g.canSlot()}[kind];
  if(!can){why(boostWhy(kind));return;}
  const cost=freeOf(kind)>0?0:priceOf(kind);
  if(cost>wallet()){why(`Ví chưa đủ ${fmt(cost)} xu.`);return;}
  T.busy=true;paintBoosts();
  try{
    await T.env.api.command('jr_tile_boost',{kind,lv:T.lv});
    g.move(MOVE[kind]);T.moves.push(MOVE[kind]);
    if(kind==='shuffle')shuffleFx();
    sound()?.click?.();
  }catch(e){why(e.message||'Chưa dùng được.');}
  T.busy=false;layout();paintBoosts();
}
function boostWhy(kind){
  const g=T.g;
  if(kind==='undo')return 'Chưa có ô nào để hoàn tác.';
  if(kind==='push')return g.hold.length?'Đưa các ô đang chờ về khay trước.':'Khay đang trống.';
  if(kind==='slot')return 'Mỗi màn thêm 1 ô thôi.';
  return 'Còn quá ít ô để xáo.';
}
function tapTile(t){
  const g=T.g;if(T.view!=='play'||!g||g.over||T.busy)return;
  if(!g.open(t)){const el=T.els.get(t);el?.classList.remove('tm-nope');void el?.offsetWidth;el?.classList.add('tm-nope');return;}
  let r;try{r=g.tap(t);}catch{return;}
  T.moves.push(t);
  const s=sound();
  if(r==='ice'){T.els.get(t)?.classList.add('tm-crack');s?.tone?.(1200,.05,.03);layout();paintBoosts();return;}
  if(Array.isArray(r)){
    const n=T.moves.length;T.combo=n-T.lastClear<=4?T.combo+1:1;T.lastClear=n;
    popFx(r);
    if(s){const base=523.25*Math.pow(1.122,Math.min(6,T.combo-1));[1,1.26,1.5].forEach((m,i)=>s.tone?.(base*m,.22,.04,i*.07));}
    try{navigator.vibrate?.(12);}catch{/* not on every phone */}
  }else if(s?.pop)s.pop();else s?.click?.();
  layout();paintBoosts();
  if(g.won)setTimeout(win,420);
  else if(g.lost)setTimeout(lose,380);
}
async function win(){
  if(T.sending)return;T.sending=true;
  const g=T.g,lv=T.lv,spent=Date.now()-T.t0,wait=Math.max(MIN_LEVEL_MS,MIN_TAP_MS*g.taps)+400-spent;
  T.result={win:true,lv,taps:g.taps,ms:spent,pending:true};T.view='done';paint();
  sound()?.success?.();
  if(wait>0)await new Promise(r=>setTimeout(r,wait));   // the server counts a level's least plausible time: wait it out quietly
  try{
    const r=await T.env.api.command('jr_tile_end',{lv,moves:T.moves});
    T.result={win:!!r.win,first:!!r.first,lv,taps:g.taps,ms:spent,pct:r.tile?.pct};
  }catch(e){T.result={win:false,lv,error:e.message||'Chưa ghi nhận được.'};}
  T.sending=false;if(T.view==='done')paint();
}
function lose(){
  sound()?.error?.();quit();
  T.result={win:false,lv:T.lv,full:true};T.view='done';paint();
}

/* ---------------------------------------------------------------- views */
function head(){
  const st=S();
  return `<header class="tm-head">
    <h2 id="tm-title">${T.view==='home'?'Ghép ba Phố Mây':`Màn ${T.lv}`}</h2>
    <span class="tm-badge" title="Tiền kiếm từ làm việc và kinh doanh">🧩 Phúc lợi +${esc(st.pct||'0')}%</span>
    ${helpBtn('tile-match','🧩 Ghép ba Phố Mây',[
      {title:'Cách chơi',open:true,body:'<ul><li>Chạm ô sáng để đưa xuống khay. Ô bị ô khác đè (dù một phần) thì mờ, chưa chạm được.</li><li>Ba ô giống nhau trong khay sẽ biến mất. Dọn sạch bàn là qua màn; khay đầy 7 ô là thua.</li><li>Chồng úp: chỉ ô trên cùng mở. 🔒 mở khi đã lấy ô 🔑. 🧊 chạm hai lần.</li></ul>'},
      {title:'Trợ giúp',body:`<ul><li>↩ Hoàn tác ô vừa đưa xuống · 🔀 Xáo các ô còn trên bàn · ⇪ Đẩy 3 ô đầu khay lên hàng chờ · ➕ Thêm 1 ô khay cho màn này.</li><li>Mỗi ngày có vài lượt miễn phí; sau đó trả xu, giá gấp đôi mỗi lần dùng trong cùng màn.</li></ul>`},
      {title:'Phúc lợi',body:`<ul><li>Mỗi màn MỚI qua lần đầu: +0,2% tiền kiếm từ làm việc và kinh doanh (lương, tiền làm, nhân viên, quầy, hợp đồng). Tối đa +20% ở màn 100.</li><li>Không áp dụng cho lãi ngân hàng, đầu tư, chợ đen, quà, chuyển khoản.</li><li>Mỗi ngày tính tối đa ${st.cap||15} màn mới. Chơi lại màn cũ cho vui thoải mái.</li></ul>`}],{cls:'tm-q'})}
    <button type="button" class="tm-x" data-tm="close" aria-label="Đóng">✕</button></header>`;
}
function homeView(){
  const st=S(),lv=nextLevel(),capped=st.lv<100&&st.n>=st.cap,done=st.lv>=100;
  const cleared=Array.from({length:st.lv},(_,i)=>i+1).reverse();
  const replay=cleared.length?`<details class="tm-replay"><summary>Chơi lại · ${st.lv} màn</summary><div class="tm-grid">${cleared.map(n=>`<button type="button" class="tm-lvbtn" data-tm="play" data-lv="${n}">${n}</button>`).join('')}</div></details>`:'';
  const main=done?`<button type="button" class="btn primary big" data-tm="play" data-lv="100">🏆 Chơi lại màn 100</button>`
    :`<button type="button" class="btn primary big" data-tm="play" data-lv="${lv}"${capped?` aria-disabled="true" data-why="Hôm nay đã qua ${st.cap} màn mới. Mai chơi tiếp nhé!"`:''}${T.busy?' disabled':''}>▶ Chơi màn ${lv}</button>`;
  return `<div class="tm-lobby">${T.flash?`<p class="tm-flash">${esc(T.flash)}</p>`:''}
    <div class="tm-hero"><div class="tm-hero-tiles" aria-hidden="true"><i>💄</i><i>🍜</i><i>🐶</i></div>
      <p class="tm-lv"><b>${done?'🏆 100/100':`Màn ${lv}`}</b><span>${st.lv}/100</span></p>
      <div class="tm-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${st.lv}"><i style="width:${st.lv}%"></i></div>
      <p class="tm-today">📅 Hôm nay ${st.n}/${st.cap} màn mới</p></div>
    ${replay}
    <p class="tm-why" role="status" hidden></p></div>
    ${actBar({main,cls:'tm-bar'})}`;
}
function boostBtn([k,emo,name]){
  const g=T.g,free=freeOf(k),cost=priceOf(k);
  const can={undo:g?.canUndo(),shuffle:g?.canShuffle(),push:g?.canPush(),slot:g?.canSlot()}[k];
  const tag=free>0?`<em class="tm-free">${free}</em>`:`<em class="tm-cost">${fmt(cost)}</em>`;
  return `<button type="button" class="tm-boost" data-tm="boost" data-k="${k}"${can?'':' aria-disabled="true" data-why="'+esc(g?boostWhy(k):'')+'"'} aria-label="${name}${free>0?`, còn ${free} lượt miễn phí`:`, ${fmt(cost)} xu`}"><span aria-hidden="true">${emo}</span><small>${name}</small>${tag}</button>`;
}
function playView(){
  return `<div class="tm-play"><div class="tm-stage"><div class="tm-board"></div><div class="tm-holdrow" aria-label="Hàng chờ"></div><div class="tm-tray" aria-label="Khay"></div><div class="tm-fx" aria-hidden="true"></div></div>
    <p class="tm-why" role="status" hidden></p>
    <div class="tm-boosts">${BOOSTS.map(boostBtn).join('')}</div></div>`;
}
function doneView(){
  const r=T.result||{},st=S();
  const clock=r.ms?`${Math.floor(r.ms/60000)}:${String(Math.floor(r.ms/1000)%60).padStart(2,'0')}`:'';
  if(r.win){
    const last=r.lv>=100;
    return `<div class="tm-done win"><div class="tm-burst" aria-hidden="true">${['✨','🎉','⭐'].map((c,i)=>`<i style="--i:${i}">${c}</i>`).join('')}</div>
      <h3>🎉 Qua màn ${r.lv}!</h3>
      ${r.first?`<p class="tm-gain">🧩 Phúc lợi +${esc(r.pct||st.pct)}%</p>`:r.pending?'<p class="tm-sub">Đang ghi nhận…</p>':''}
      <p class="tm-stats">👆 ${r.taps} · ⏱ ${clock}</p></div>
      ${actBar({next:'<button type="button" class="btn" data-tm="home">Sảnh</button>',
        main:`<button type="button" class="btn primary big" data-tm="${last?'home':'next'}"${r.pending?' disabled':''}>${last?'🏆 Xong 100 màn':`Màn ${Math.min(100,r.lv+1)} ▶`}</button>`,cls:'tm-bar'})}`;
  }
  return `<div class="tm-done lose"><h3>${r.full?'😵 Khay đầy rồi!':'Chưa ghi nhận'}</h3>
    <p class="tm-sub">${esc(r.error||'Thử lại, để ý ô bị đè nhé.')}</p></div>
    ${actBar({next:'<button type="button" class="btn" data-tm="home">Sảnh</button>',main:`<button type="button" class="btn primary big" data-tm="again">↻ Chơi lại màn ${r.lv}</button>`,cls:'tm-bar'})}`;
}
function paint(){
  const root=T.dlg?.querySelector('.tm-root');if(!root)return;
  root.className=`tm-root tm-${T.view}`;
  if(T.view==='play'){
    root.innerHTML=head()+playView();
    T.els=new Map();
    T.ro?.disconnect();
    if(typeof ResizeObserver==='function'){T.ro=new ResizeObserver(()=>layout());T.ro.observe(root.querySelector('.tm-stage'));}
    layout();return;
  }
  T.ro?.disconnect();T.ro=null;
  root.innerHTML=head()+`<div class="tm-body">${T.view==='done'?doneView():homeView()}</div>`;
  paintWhy();
}
function paintBoosts(){const el=T.dlg?.querySelector('.tm-boosts');if(el)el.innerHTML=BOOSTS.map(boostBtn).join('');}

/* ---------------------------------------------------------------- the board: geometry and tiles */
/** Where everything sits for the stage's size: board tile size s, tray/hold tile size ts and the rows' origins. */
/** The level's own extent in half tiles (a small early level fills the stage instead of a 7 × 8 frame). */
function extent(lv){
  if(lv._box)return lv._box;
  let x0=Infinity,y0=Infinity,x1=-Infinity,y1=-Infinity;
  for(const [x,y] of lv.tiles){x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x+2);y1=Math.max(y1,y+2);}
  return (lv._box={x0,y0,cols:(x1-x0)/2,rows:(y1-y0)/2});
}
const MAX_TILE=64;
function geometry(W,H,lv,cap){
  const {x0,y0,cols,rows}=extent(lv),pad=6,side=W>H*1.25&&W>=560;
  if(side){
    const panel=Math.min(W*0.42,440),bw=W-panel-pad*3,s=Math.floor(Math.min(MAX_TILE,bw/cols,(H-pad*2)/rows));
    const ts=Math.floor(Math.min(56,(panel-pad*2)/(cap+.4))),ox=pad+Math.floor((bw-s*cols)/2)-x0*s/2,oy=pad+Math.floor((H-pad*2-s*rows)/2)-y0*s/2;
    const px=W-panel-pad+Math.floor((panel-ts*cap)/2),ty=Math.floor(H/2)+8;
    return {s,ts,ox,oy,tray:{x:px,y:ty},hold:{x:px+Math.floor((cap-HOLD)*ts/2),y:ty-ts-14},side};
  }
  const ts=Math.floor(Math.min(56,(W-pad*2)/(cap+.3))),trayH=ts+14,holdH=Math.round(ts*.9)+8;
  const bh=H-trayH-holdH-pad*2,s=Math.floor(Math.min(MAX_TILE,(W-pad*2)/cols,bh/rows));
  const ox=Math.floor((W-s*cols)/2)-x0*s/2,oy=pad+Math.max(0,Math.floor((bh-s*rows)/2))-y0*s/2;
  const tx=Math.floor((W-ts*cap)/2),ty=H-trayH+7;
  return {s,ts,ox,oy,tray:{x:tx,y:ty},hold:{x:Math.floor((W-ts*HOLD)/2),y:ty-holdH},side};
}
function tileEl(t){
  let el=T.els.get(t);if(el)return el;
  const f=T.level.tiles[t][4];
  el=document.createElement('button');el.type='button';el.className='tm-tile';el.dataset.id=String(t);
  if(f&ICE)el.classList.add('tm-ice');if(f&LOCK)el.classList.add('tm-lock');if(f&KEY)el.classList.add('tm-key');
  el.innerHTML='<span class="tm-face"></span>';
  T.dlg.querySelector('.tm-board').append(el);T.els.set(t,el);return el;
}
function stackOf(t){const st=T.level.stacks||[];for(const s of st){const i=s.ids.indexOf(t);if(i>=0)return {s,i};}return null;}
function layout(){
  const stage=T.dlg?.querySelector('.tm-stage');const g=T.g,lv=T.level;if(!stage||!g||!lv)return;
  const W=stage.clientWidth,H=stage.clientHeight;if(!W||!H)return;
  const geo=geometry(W,H,lv,g.cap);T.lay=geo;
  stage.style.setProperty('--s',`${geo.s}px`);stage.style.setProperty('--ts',`${geo.ts}px`);
  const tray=stage.querySelector('.tm-tray');
  tray.style.cssText=`left:${geo.tray.x-4}px;top:${geo.tray.y-4}px;width:${geo.ts*g.cap+8}px;height:${geo.ts+8}px`;
  tray.innerHTML=Array.from({length:g.cap},()=>'<i></i>').join('');
  const hold=stage.querySelector('.tm-holdrow');
  hold.style.cssText=`left:${geo.hold.x-4}px;top:${geo.hold.y-4}px;width:${geo.ts*HOLD+8}px;height:${geo.ts+8}px`;hold.classList.toggle('on',g.hold.length>0);
  const s=geo.s;
  for(let t=0;t<g.n;t++){
    const el=tileEl(t),[x,y,z]=lv.tiles[t],w=g.where[t];
    let px,py,size=s,zi;
    if(w==='g'){if(!el.classList.contains('tm-pop'))el.classList.add('tm-gone');continue;}
    el.classList.remove('tm-gone');
    if(w==='t'){const i=g.tray.indexOf(t);px=geo.tray.x+i*geo.ts;py=geo.tray.y;size=geo.ts;zi=1000+i;}
    else if(w==='h'){const i=g.hold.indexOf(t);px=geo.hold.x+i*geo.ts;py=geo.hold.y;size=geo.ts;zi=900+i;}
    else{
      const st=stackOf(t);
      px=geo.ox+x*s/2;py=geo.oy+y*s/2;zi=z*10+5;
      if(st&&st.i>0){const dir=x>=lv.w/2-1?-1:1,k=Math.min(st.i,10);px+=dir*k*Math.max(3,Math.round(s*.09));zi=50-k;}
    }
    const covered=w==='b'&&g.block[t]>0,stacked=w==='b'&&stackOf(t)?.i>0;
    el.classList.toggle('tm-off',covered&&!stacked);el.classList.toggle('tm-back',stacked);
    el.classList.toggle('tm-iced',w==='b'&&g.ice[t]>0);
    el.classList.toggle('tm-small',w!=='b');
    el.style.zIndex=String(zi);el.style.width=el.style.height=`${size-2}px`;
    el.style.transform=`translate(${px+1}px,${py+1}px)`;
    const face=el.firstChild,icon=stacked?'':lv.icons[g.kind[t]]||'?';
    if(face.textContent!==icon)face.textContent=icon;
    el.setAttribute('aria-label',stacked?'Ô úp':covered?`${icon} bị đè`:icon);
    el.tabIndex=g.open(t)?0:-1;
  }
}
function popFx(ids){
  const fx=T.dlg?.querySelector('.tm-fx');
  for(const t of ids){const el=T.els.get(t);if(!el)continue;el.classList.add('tm-pop');setTimeout(()=>{el.classList.remove('tm-pop');el.classList.add('tm-gone');},360);}
  if(fx&&T.lay){
    const g=T.lay,x=g.tray.x+g.ts*1.5,y=g.tray.y;
    const b=document.createElement('b');b.className='tm-combo';b.style.left=`${x}px`;b.style.top=`${y-10}px`;
    b.textContent=T.combo>1?`Combo ×${T.combo}!`:'✨';fx.append(b);setTimeout(()=>b.remove(),900);
  }
}
function shuffleFx(){const b=T.dlg?.querySelector('.tm-board');if(!b)return;b.classList.remove('tm-shuffling');void b.offsetWidth;b.classList.add('tm-shuffling');}
