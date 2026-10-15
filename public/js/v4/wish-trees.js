/** 🌳 Vườn cây ước nguyện at chùa Gió Lành (game/chua_wish.py). Owner 15/10: everyone walks up to a tree, WRITES their
 * own wish (no picking from a list), hangs it on the tree; there are many trees; everyone can read them, clearly.
 * Opened from the pagoda (./chua-visit.js, the tree in the yard and the "Ước nguyện" step) and from the Đi chùa section
 * of the Đời thường sheet (./chua.js). Its own full-screen dialog, three screens:
 *   garden  the nine trees (a little tree each with the colours of its newest ribbons, how many wishes), "Của tôi";
 *   tree    the tree with its newest ribbons hung on the branches (tap one to read it), the wishes as paper cards
 *           under it (newest first, "Xem thêm" pages by id cursor), one main button: "Viết điều ước";
 *   mine    every wish I hung, on any tree, with its state (taken down, waiting for a look after reports).
 * Writing: a sheet over the tree: the words (TEXT_MAX), the ribbon's colour, "Ẩn tên"; "Treo lên cây" sends the temple's
 * own act (jr_chua_do {act:'nguyen', tree, text, color, anon}: tinh thần like any wish), then the ribbon flies up
 * onto the tree. Reading: a card (the words, who, when, on which tree), ‹ › to the next ribbon, 🙏 Cùng cầu, ⚑ Báo cáo,
 * and "Gỡ xuống" for my own. Player words are always escaped and marked data-no-translate.
 * 📜 Old lời chúc (owner 15/10 about the old "Bảng chung": "đưa vào 1 cái đi, sử dụng chung mà"): the cards their owners
 * shared on the old board hang here, on the tree of their theme (game/chua_wish.py card_tree): paper slips among the
 * ribbons and a list "Lời chúc cũ trên cây" under the wishes (GET ?tree=&old=1), read, 🙏 and ⚑ like a wish; the owner's
 * own says "Thôi chia sẻ". "Của tôi" lists my old cards with their sharing switch (the old board's own routes,
 * /api/chua/cards). Rows are told apart by key (rk): 'w<id>' a wish, 'c<position>' an old card.
 * An older server sends no state.chua.wish_trees: openWishTrees() then answers false and the callers keep the old card.
 * Reduced motion: nothing sways, the ribbon appears in place. */
import {icon,escapeHTML as esc} from '../icons.js';
import {stylesheet} from '../lazy.js';
import {cardText,createCardBoard} from './chua.js';

const COLOR_NAME={do:'Đỏ',vang:'Vàng',hong:'Hồng',xanh:'Xanh lá',tim:'Tím'};
const REASONS=[['rude','Lời lẽ khó nghe'],['spam','Quảng cáo, spam'],['private','Lộ thông tin riêng'],['other','Lý do khác']];
const HERO=24;          // ribbons hung on the big tree (the newest)
const PAGE=24;
// Where a ribbon hangs on the tree (the town map's banyan painting), % of its box: on the canopy, never on the trunk;
// most visible first (the newest wishes go there).
const SLOTS=[[50,22],[38,22],[62,22],[44,41],[56,41],[26,22],[74,22],[32,41],[68,41],[50,3],[14,22],[86,22],[20,41],[80,41],
  [38,3],[62,3],[8,41],[92,41],[20,60],[80,60],[8,60],[92,60],[32,60],[68,60]];
const TREE_IMG='/icons/isometric/tree.webp';
const asset=p=>globalThis.__mnlBoot?.asset?.(p)||p;
const OLD_HERO=4;       // slips of old shared cards always on the big tree when it has them
const S={env:null,dlg:null,view:'garden',data:null,loading:false,error:'',tree:'',list:null,old:null,mine:null,cards:null,reader:null,compose:null,busy:false,parent:null,fresh:''};
const still=()=>Boolean(globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches)||document.documentElement.classList.contains('reduce-motion');
const C=()=>S.env?.api?.state?.chua;
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const treeOf=id=>S.data?.trees?.find(t=>t.id===id)||null;
const slot=()=>({rows:[],before:null,loading:false,loaded:false,error:'',req:0});
const words=s=>`<span data-no-translate>${esc(s)}</span>`;
/** A row's key: a wish 'w12', an old shared card 'c34' (their ids come from two tables). */
const rk=r=>(r.kind==='card'?'c':'w')+r.id;
const isCard=key=>String(key).startsWith('c');
const choices=()=>C()?.card_choices;
const oldCount=n=>`${fmt(n)} lời chúc cũ`;
const who=w=>w.name?words(w.name):'<span>Ẩn danh</span>';
function when(at){
  const d=new Date((at|0)*1000),now=new Date(),mins=Math.round((now-d)/60000);
  if(mins<1)return 'vừa xong';
  if(mins<60)return `${mins} phút trước`;
  const same=d.toDateString()===now.toDateString();
  const hm=`${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
  if(same)return `hôm nay ${hm}`;
  const y=new Date(now);y.setDate(now.getDate()-1);
  if(d.toDateString()===y.toDateString())return `hôm qua ${hm}`;
  return `${d.getDate()}/${d.getMonth()+1}`;
}

/* ---------------------------------------------------------------- the art */
/** The garden's little tree: the same painting as the courtyard's, with its newest ribbons (colours only). */
function miniTree(ribbons=[]){
  return `<span class="wt-mini" aria-hidden="true"><img src="${esc(asset(TREE_IMG))}" alt="" loading="lazy" decoding="async">${ribbons.slice(0,12).map((c,i)=>{const [x,y]=SLOTS[i];return `<i class="wt-c-${esc(c)}" style="left:${x}%;top:${y}%"></i>`;}).join('')}</span>`;
}

/* ---------------------------------------------------------------- dialog */
function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet wt-sheet';d.setAttribute('aria-labelledby','wtTitle');
  d.innerHTML=`<div class="wt-root"><header class="wt-head"><button type="button" class="icon-btn wt-back" data-wt="back" aria-label="Quay lại">${icon('back',20)}</button>
      <div class="grow"><h2 id="wtTitle">Vườn ước nguyện</h2><p class="wt-sub"></p></div>
      <button type="button" class="icon-btn" data-wt="close" aria-label="Đóng">${icon('x',20)}</button></header>
    <div class="wt-body" tabindex="-1"></div><div class="wt-layer" hidden></div></div>`;
  document.body.append(d);
  d.addEventListener('click',e=>{const el=e.target.closest('[data-wt]');if(!el||!d.contains(el)||el.disabled)return;e.preventDefault();act(el.dataset.wt,el.dataset);});
  d.addEventListener('input',e=>{if(e.target.matches?.('[name="wt-text"]')&&S.compose){S.compose.text=e.target.value;liveCompose();}});
  d.addEventListener('change',e=>{if(e.target.matches?.('[name="wt-anon"]')&&S.compose){S.compose.anon=e.target.checked;liveCompose();}});
  d.addEventListener('keydown',e=>{if(e.key==='Escape'&&(S.reader||S.compose)){e.preventDefault();S.reader=null;S.compose=null;layer();}
    if(S.reader&&!S.compose&&(e.key==='ArrowLeft'||e.key==='ArrowRight')&&!e.target.closest?.('textarea,input')){e.preventDefault();step(e.key==='ArrowLeft'?-1:1);}});
  d.addEventListener('close',()=>{const t=document.getElementById('toasts');if(t&&S.parent&&t.parentElement===d)S.parent.append(t);S.reader=null;S.compose=null;S.env?.onClose?.();});
  S.dlg=d;return d;
}
/** Open the garden (or one tree: `opt.tree`). false when this server has no wish trees (an older build). */
export async function openWishTrees(env,opt={}){
  if(!env?.api?.state?.chua?.wish_trees)return false;
  S.env=env;await stylesheet('/css/wish-trees.css');
  const d=dialog();
  S.view='garden';S.reader=null;S.compose=null;S.error='';S.list=null;S.mine=null;S.fresh='';
  const toasts=document.getElementById('toasts');if(toasts&&toasts.parentElement!==d){S.parent=toasts.parentElement;d.append(toasts);}
  if(!d.open)d.showModal();
  render();layer();
  await loadGarden();
  if(opt.tree&&treeOf(opt.tree))openTree(opt.tree);
  return true;
}
/** The garden's data (the trees, their counts and newest ribbons, my wishes left today); the pagoda's grove uses it too. */
export async function fetchTrees(api){S.data=await api.json('/api/chua/trees');return S.data;}
async function loadGarden(){
  S.loading=true;S.error='';if(S.view==='garden')render();
  try{await fetchTrees(S.env.api);}
  catch(e){S.error=e.message||'Chưa tải được vườn ước nguyện. Bạn thử lại nhé.';}
  finally{S.loading=false;render();}
}
async function loadRows(box,url,more=false){
  if(!box||(more&&(box.loading||!box.before)))return;
  const req=++box.req;box.loading=true;box.error='';
  if(!more){box.rows=[];box.before=null;}
  render();
  try{
    const data=await S.env.api.json(`${url}&limit=${PAGE}${more&&box.before?`&before=${box.before}`:''}`);
    if(req!==box.req)return;
    const seen=new Set(box.rows.map(rk));box.rows.push(...data.rows.filter(r=>!seen.has(rk(r))));
    box.before=data.before;box.loaded=true;
  }catch(e){if(req===box.req)box.error=e.message||'Chưa tải được điều ước. Bạn thử lại nhé.';}
  finally{if(req===box.req){box.loading=false;render();}}
}
const treeUrl=()=>`/api/chua/wishes?tree=${encodeURIComponent(S.tree)}`;
const oldUrl=()=>`${treeUrl()}&old=1`;
function openTree(id){
  S.view='tree';S.tree=id;S.list=slot();S.old=slot();S.reader=null;render();S.dlg.querySelector('.wt-body').scrollTop=0;
  return Promise.all([loadRows(S.list,treeUrl()),treeOf(id)?.old?loadRows(S.old,oldUrl()):null]);
}
function openMine(){
  S.view='mine';S.mine=slot();S.reader=null;
  // my old lời chúc and whether each hangs in the garden (the old board's own list: the save and its archive)
  S.cards=C()?.sharing&&(C()?.cards||[]).length?createCardBoard(S.env.api,b=>{if(S.cards===b&&S.view==='mine')render();}):null;
  render();S.cards?.load('mine');
  return loadRows(S.mine,'/api/chua/wishes?mine=1');
}

/* ---------------------------------------------------------------- screens */
function head(){
  const d=S.dlg,t=treeOf(S.tree);
  d.querySelector('.wt-back').hidden=S.view==='garden';
  d.querySelector('#wtTitle').textContent=S.view==='tree'&&t?`${t.emoji} Cây ${t.name}`:S.view==='mine'?'Điều ước của tôi':'Vườn ước nguyện';
  const left=S.data?`Hôm nay còn treo được ${S.data.left}/${S.data.per_day}`:'';
  d.querySelector('.wt-sub').textContent=S.view==='tree'&&t?t.hint:S.view==='mine'?left:'Chùa Gió Lành';
}
function render(){
  if(!S.dlg)return;head();
  const body=S.dlg.querySelector('.wt-body');
  body.dataset.view=S.view;
  body.innerHTML=S.view==='tree'?treeView():S.view==='mine'?mineView():gardenView();
  if(S.fresh&&!(S.view==='tree'&&S.list?.loading))fly();   // the new ribbon flies once the tree has its wishes again
}
function gardenView(){
  const D=S.data;
  if(!D)return S.error?`<p class="wt-why" role="alert">${esc(S.error)}</p><button type="button" class="btn primary" data-wt="reload">Thử lại</button>`:'<p class="wt-wait" role="status">Đang vào vườn…</p>';
  const tiles=D.trees.map(t=>`<li><button type="button" class="wt-tile" data-wt="tree" data-id="${esc(t.id)}">${miniTree(t.ribbons)}
      <span class="wt-tile-name"><span aria-hidden="true">${t.emoji}</span> ${esc(t.name)}</span><small class="wt-tile-hint">${esc(t.hint)}</small>
      <span class="wt-count">${t.count?`${fmt(t.count)} điều ước`:t.old?'':'Chưa có ai treo'}${t.count&&t.old?' · ':''}${t.old?oldCount(t.old):''}</span></button></li>`).join('');
  return `<section class="wt-intro"><p>Viết điều ước của riêng bạn, buộc lên một cây. Ai đi chùa cũng đọc được và cùng cầu cho nhau.</p>
      <div class="wt-intro-row"><span class="wt-left${D.left?'':' none'}">${D.off?'Vườn đang tạm nghỉ treo mới':D.left?`🎐 Hôm nay còn treo được ${D.left}/${D.per_day}`:'Hôm nay bạn treo đủ rồi, mai treo tiếp nhé'}</span>
      <button type="button" class="btn ghost small" data-wt="mine">🎐 Của tôi${D.mine?` (${fmt(D.mine)})`:''}</button></div></section>
    <ul class="wt-grid">${tiles}</ul>
    <p class="wt-foot">${fmt(D.total)} điều ước đang treo trong vườn${D.old?` · ${oldCount(D.old)}`:''}</p>`;
}
function ribbon(w,i){
  const [x,y]=SLOTS[i],old=w.kind==='card';
  return `<button type="button" class="wt-rib ${old?'wt-old':`wt-c-${esc(w.color)}`}${w.mine?' mine':''}${S.fresh&&w.key===S.fresh?' fresh':''}" data-wt="read" data-id="${rk(w)}" style="left:${x}%;top:${y}%;--d:${((i*.37)%2.4).toFixed(2)}s" aria-label="${old?'Đọc lời chúc cũ':'Đọc điều ước'} ${i+1}"><i aria-hidden="true"></i>${w.mine?'<em aria-hidden="true">★</em>':''}</button>`;
}
/** An old shared card: its own words (the fixed parts translate, the names and messages never), signed as an old one. */
const oldText=c=>cardText(c,choices());
function card(w,showTree=false){
  const t=showTree?treeOf(w.tree):null;
  const state=w.status&&w.status!=='live'?`<span class="wt-state">${{down:'Đã gỡ xuống',hidden:'Đang chờ xem xét',removed:'Đã bị ẩn'}[w.status]||''}</span>`:'';
  return `<li><button type="button" class="wt-card wt-c-${esc(w.color)}${w.mine?' mine':''}${S.fresh&&w.key===S.fresh?' fresh':''}" data-wt="read" data-id="${rk(w)}">
    <span class="wt-card-text">${words(w.text)}</span>
    <span class="wt-card-foot"><span class="wt-by">— ${who(w)}${w.mine?' <b class="wt-me">(bạn)</b>':''}</span><span class="wt-when">${t?`${t.emoji} ${esc(t.name)} · `:''}${esc(when(w.at))}</span>${w.prayers?`<span class="wt-pray-n">🙏 ${fmt(w.prayers)}</span>`:''}${state}</span></button></li>`;
}
function oldCard(c){
  return `<li><button type="button" class="wt-card wt-old${c.mine?' mine':''}" data-wt="read" data-id="${rk(c)}">
    <span class="wt-card-text">${oldText(c)}</span>
    <span class="wt-card-foot"><span class="wt-by">📜 Lời chúc cũ${c.mine?' <b class="wt-me">(bạn)</b>':''}</span><span class="wt-when">Ngày ${c.day|0}</span>${c.prayers?`<span class="wt-pray-n">🙏 ${fmt(c.prayers)}</span>`:''}</span></button></li>`;
}
function treeView(){
  const t=treeOf(S.tree),L=S.list,O=S.old||slot();if(!t||!L)return '';
  // the newest wishes, and a few old slips too (more when the tree has room)
  const hero=[...L.rows.slice(0,HERO-Math.min(OLD_HERO,O.rows.length)),...O.rows].slice(0,HERO),more=Math.max(0,t.count-hero.length);
  const can=S.data&&S.data.left>0&&!S.data.off;
  const empty=!L.rows.length&&!L.loading&&!L.error&&!O.rows.length&&!O.loading;
  return `<div class="wt-tree-grid"><section class="wt-hero" aria-label="Cây ${esc(t.name)}">
      <div class="wt-stage"><div class="wt-tree"><img class="wt-tree-img" src="${esc(asset(TREE_IMG))}" alt="" decoding="async"><div class="wt-ribs">${hero.map(ribbon).join('')}</div></div>
        ${empty?'<p class="wt-empty">Cây còn trống. Bạn treo điều ước đầu tiên nhé 🎐</p>':''}
        <span class="wt-plaque"><b><span aria-hidden="true">${t.emoji}</span> Cây ${esc(t.name)}</b><small>${t.count?`${fmt(t.count)} điều ước`:t.old?'':'Chưa có điều ước'}${t.count&&t.old?' · ':''}${t.old?oldCount(t.old):''}</small></span></div>
</section>
    <section class="wt-list" aria-label="Điều ước trên cây">
      <h3 class="wt-h3">Điều ước trên cây${more&&hero.length?` <small>· mới nhất trước</small>`:''}</h3>
      ${L.error?`<p class="wt-why" role="alert">${esc(L.error)}</p>`:''}
      ${L.loading&&!L.rows.length?'<p class="wt-wait" role="status">Đang đọc các dải lụa…</p>':''}
      ${empty?'<p class="wt-none">Chưa có ai treo ở cây này.</p>':''}
      ${!L.rows.length&&!L.loading&&!L.error&&O.rows.length?'<p class="wt-none">Chưa có điều ước mới. Bạn treo điều ước đầu tiên nhé 🎐</p>':''}
      <ol class="wt-cards">${L.rows.map(w=>card(w)).join('')}</ol>
      ${L.before?`<button type="button" class="btn ghost small full" data-wt="more"${L.loading?' disabled':''}>${L.loading?'Đang tải…':'Xem thêm điều ước'}</button>`:''}
      ${O.rows.length||O.error?`<h3 class="wt-h3 wt-old-h">📜 Lời chúc cũ trên cây <small>· người chơi chia sẻ ở bảng chung trước đây</small></h3>
        ${O.error?`<p class="wt-why" role="alert">${esc(O.error)}</p>`:''}
        <ol class="wt-cards">${O.rows.map(oldCard).join('')}</ol>
        ${O.before?`<button type="button" class="btn ghost small full" data-wt="more-old"${O.loading?' disabled':''}>${O.loading?'Đang tải…':'Xem thêm lời chúc cũ'}</button>`:''}`:''}</section>
      <div class="wt-cta"><button type="button" class="btn primary big full" data-wt="write"${can?'':' disabled'}>✍️ Viết điều ước lên cây này</button>
        <small>${!S.data?'':S.data.off?'Vườn đang tạm nghỉ treo mới.':can?`Hôm nay còn treo được ${S.data.left}/${S.data.per_day} · chạm dải lụa để đọc`:'Hôm nay bạn treo đủ rồi, mai treo tiếp nhé · chạm dải lụa để đọc'}</small></div></div>`;
}
function mineView(){
  const M=S.mine;if(!M)return '';
  const empty=!M.rows.length&&!M.loading&&!M.error;
  return `<section class="wt-list wide">
    ${M.error?`<p class="wt-why" role="alert">${esc(M.error)}</p>`:''}
    ${M.loading&&!M.rows.length?'<p class="wt-wait" role="status">Đang tìm điều ước của bạn…</p>':''}
    ${empty?'<p class="wt-none">Bạn chưa treo điều ước nào. Chọn một cây trong vườn và viết điều bạn mong nhé.</p><button type="button" class="btn primary" data-wt="back">🌳 Vào vườn</button>':''}
    <ol class="wt-cards">${M.rows.map(w=>card(w,true)).join('')}</ol>
    ${M.before?`<button type="button" class="btn ghost small full" data-wt="more"${M.loading?' disabled':''}>${M.loading?'Đang tải…':'Xem thêm'}</button>`:''}
    ${myOldCards()}</section>`;
}
/** 📜 My old lời chúc: each says whether it hangs in the garden for everyone, and switches (the old board's routes). */
function myOldCards(){
  const B=S.cards;if(!B)return '';
  const P=B.mine,busy=B.busy;
  const row=c=>{const on=c.public===true,t=on?treeOf(c.tree||''):null;
    return `<li class="wt-card wt-old wt-mycard${on?' on':''}"><span class="wt-card-text">${oldText(c)}</span>
      <span class="wt-card-foot"><span class="wt-when">Ngày ${c.day|0}</span><span class="wt-state">${on?t?`🌳 Đang treo ở cây ${esc(t.name)}`:'🌳 Đang treo trong vườn':'🔒 Chỉ mình tôi'}</span>
        <button type="button" class="btn ghost small wt-share" data-wt="card-share" data-id="${esc(c.id)}" data-public="${!on}"${busy?' disabled':''}>${busy===c.id?'Đang lưu…':on?'Thôi chia sẻ':'Treo vào vườn'}</button></span></li>`;};
  return `<section class="wt-mine-old" aria-label="Lời chúc cũ của tôi"><h3 class="wt-h3">📜 Lời chúc cũ của bạn <small>· “Treo vào vườn” thì ai cũng đọc được, kèm tên và lời nhắn</small></h3>
    ${P.error?`<p class="wt-why" role="alert">${esc(P.error)}</p>`:''}${P.loading&&!P.rows.length?'<p class="wt-wait" role="status">Đang tìm lời chúc cũ…</p>':''}
    <ol class="wt-cards">${P.rows.map(row).join('')}</ol>
    ${P.before?`<button type="button" class="btn ghost small full" data-wt="more-cards"${P.loading?' disabled':''}>${P.loading?'Đang tải…':'Xem thêm'}</button>`:''}</section>`;
}

/* ---------------------------------------------------------------- reader and composer (the layer over a screen) */
const rows=()=>S.view==='mine'?S.mine?.rows||[]:[...(S.list?.rows||[]),...(S.old?.rows||[])];
function layer(){
  const box=S.dlg?.querySelector('.wt-layer');if(!box)return;
  const inner=S.compose?composeHTML():S.reader?readHTML():'';   // a wish gone from the list (reported, taken down) closes
  if(!inner){S.reader=null;box.hidden=true;box.innerHTML='';box.dataset.kind='';return;}
  box.hidden=false;box.dataset.kind=S.compose?'compose':'read';
  box.innerHTML=`<div class="wt-scrim" data-wt="shut"></div>${inner}`;
  const focus=box.querySelector(S.compose?'textarea':'.wt-read');focus?.focus({preventScroll:true});
}
function readHTML(){
  const list=rows(),i=list.findIndex(w=>rk(w)===S.reader.id),w=list[i];
  if(!w)return '';
  const t=treeOf(w.tree),busy=S.busy,key=rk(w),old=w.kind==='card';
  const pray=w.mine?'':`<button type="button" class="btn ${w.prayed?'ghost':'primary'} big" data-wt="pray" data-id="${key}"${w.prayed||busy?' disabled':''}>🙏 ${w.prayed?'Bạn đã cùng cầu':'Cùng cầu'}${w.prayers?` · ${fmt(w.prayers)}`:''}</button>`;
  const tools=w.mine?(w.status==='down'?'':`<button type="button" class="btn ghost small" data-wt="down" data-id="${key}"${busy?' disabled':''}>${old?'Thôi chia sẻ':'Gỡ xuống'}</button>`)
    :`<button type="button" class="btn ghost small wt-flag" data-wt="report-ask" data-id="${key}"${busy?' disabled':''}>${icon('flag',14)} Báo cáo</button>`;
  const ask=S.reader.report?`<div class="wt-report" role="group" aria-label="Lý do báo cáo"><p>${old?'Lời chúc này có vấn đề gì?':'Điều ước này có vấn đề gì?'}</p>${REASONS.map(([id,label])=>`<button type="button" class="btn cream small" data-wt="report" data-id="${key}" data-reason="${id}"${busy?' disabled':''}>${esc(label)}</button>`).join('')}</div>`:'';
  return `<article class="wt-read ${old?'wt-old':`wt-c-${esc(w.color)}`}" tabindex="-1" role="dialog" aria-modal="true" aria-label="${old?'Lời chúc cũ':'Điều ước'}">
    <button type="button" class="icon-btn small wt-x" data-wt="shut" aria-label="Đóng">${icon('x',16)}</button>
    <span class="wt-knot" aria-hidden="true"></span>
    <p class="wt-read-text">${old?oldText(w):words(w.text)}</p>
    <p class="wt-read-by">— ${old?'<span>📜 Lời chúc cũ</span>':who(w)}${w.mine?' <b class="wt-me">(bạn)</b>':''}</p>
    <p class="wt-read-meta">${t?`${t.emoji} Cây ${esc(t.name)} · `:''}${old?`Ngày ${w.day|0} · từ bảng chung cũ`:esc(when(w.at))}${w.mine&&w.prayers?` · 🙏 ${fmt(w.prayers)} người cùng cầu`:''}</p>
    <div class="wt-read-acts">${pray}</div>${ask}
    <div class="wt-read-nav"><button type="button" class="icon-btn" data-wt="prev" aria-label="${old?'Lời chúc trước':'Điều ước trước'}"${i>0?'':' disabled'}>‹</button>
      <span>${i+1}/${list.length}</span>${tools}
      <button type="button" class="icon-btn" data-wt="next" aria-label="${old?'Lời chúc sau':'Điều ước sau'}"${i<list.length-1?'':' disabled'}>›</button></div></article>`;
}
function composeHTML(){
  const t=treeOf(S.tree),c=S.compose,D=S.data,max=D?.max||150,name=String(S.env.api.state?.name||'').trim();
  const sw=(D?.colors||Object.keys(COLOR_NAME)).map(id=>`<button type="button" class="wt-sw wt-c-${esc(id)}${c.color===id?' on':''}" data-wt="color" data-id="${esc(id)}" aria-pressed="${c.color===id}" aria-label="Dải lụa ${esc(COLOR_NAME[id]||id)}"></button>`).join('');
  return `<form class="wt-compose" onsubmit="return false" aria-label="Viết điều ước">
    <div class="wt-c-head"><b>✍️ Điều ước của bạn</b><span class="wt-chip">${t?`${t.emoji} Cây ${esc(t.name)}`:''}</span>
      <button type="button" class="icon-btn small" data-wt="shut" aria-label="Đóng">${icon('x',16)}</button></div>
    <div class="wt-paper wt-c-${esc(c.color)}"><span class="wt-knot" aria-hidden="true"></span>
      <textarea name="wt-text" rows="4" maxlength="${max}" placeholder="Bạn mong điều gì? Ví dụ: Mong mẹ mau khỏe để Tết cả nhà về quê." autocomplete="off" data-no-translate>${esc(c.text)}</textarea>
      <span class="wt-sign">— <span data-sign${c.anon||!name?'':' data-no-translate'}>${c.anon||!name?'Ẩn danh':esc(name)}</span></span></div>
    <div class="wt-c-row"><span class="wt-c-label">Màu dải lụa</span><span class="wt-sws" role="group" aria-label="Màu dải lụa">${sw}</span><span class="wt-counter" aria-live="polite">0/${max}</span></div>
    <label class="wt-anon"><input type="checkbox" name="wt-anon"${c.anon?' checked':''}> <span>Ẩn tên của tôi (hiện “Ẩn danh”)</span></label>
    <button type="button" class="btn primary big full" data-wt="hang" disabled>🎐 Treo lên cây</button>
    <p class="wt-c-note">Ai đi chùa cũng đọc được. Viết lời tử tế, đừng ghi số điện thoại hay địa chỉ nhé.</p></form>`;
}
function liveCompose(){
  const f=S.dlg?.querySelector('.wt-compose');if(!f||!S.compose)return;
  const max=S.data?.max||150,min=S.data?.min||3,n=[...S.compose.text.trim()].length,name=String(S.env.api.state?.name||'').trim();
  f.querySelector('.wt-counter').textContent=`${n}/${max}`;f.querySelector('.wt-counter').classList.toggle('near',n>max-15);
  f.querySelector('[data-wt="hang"]').disabled=S.busy||n<min||n>max;
  const sign=f.querySelector('[data-sign]'),anon=S.compose.anon||!name;sign.toggleAttribute('data-no-translate',!anon);sign.textContent=anon?'Ẩn danh':name;
}
function step(d){
  const list=rows(),i=list.findIndex(w=>rk(w)===S.reader?.id),j=i+d;
  if(i<0||j<0||j>=list.length)return;
  S.reader={id:rk(list[j])};layer();
  if(j<list.length-3)return;
  if(S.view==='mine'){if(S.mine?.before)loadRows(S.mine,'/api/chua/wishes?mine=1',true);}
  else if(S.list?.before)loadRows(S.list,treeUrl(),true);else if(S.old?.before)loadRows(S.old,oldUrl(),true);
}

/* ---------------------------------------------------------------- doing */
async function hang(){
  const c=S.compose,t=S.tree;if(!c||S.busy||!t)return;
  const text=c.text.trim();if([...text].length<(S.data?.min||3))return;
  const btn=S.dlg.querySelector('[data-wt="hang"]'),from=btn?.getBoundingClientRect();
  S.busy=true;if(btn){btn.disabled=true;btn.textContent='Đang treo…';}
  try{
    const r=await S.env.cmd('jr_chua_do',{act:'nguyen',tree:t,text,color:c.color,anon:c.anon},{quiet:true});
    if(!r?.chua_wish){if(btn){btn.textContent='🎐 Treo lên cây';}return;}
    S.compose=null;layer();
    if(S.data){S.data.left=Math.max(0,S.data.left-1);S.data.mine+=1;S.data.total+=1;const tr=treeOf(t);if(tr){tr.count+=1;tr.ribbons=[c.color,...tr.ribbons].slice(0,14);}}
    S.fresh=r.chua_wish.key;S.flyFrom=from;S.flyColor=c.color;
    await loadRows(S.list,treeUrl());
    S.env.toast?.(r.message?.replace(/^\S+\s/,'🎐 ')||'🎐 Đã treo điều ước lên cây.');
  }finally{S.busy=false;liveCompose();}   // a refused wish (limit, words) keeps the draft and the button
}
/** The new ribbon flies from the button up to its branch (then glows a moment). */
function fly(){
  const key=S.fresh;S.fresh='';
  const to=S.dlg.querySelector('.wt-rib.fresh');
  const from=S.flyFrom;S.flyFrom=null;
  if(!to||!from||still()||!to.animate){setTimeout(()=>S.dlg?.querySelectorAll('.fresh').forEach(el=>el.classList.remove('fresh')),2600);return;}
  const r=to.getBoundingClientRect(),f=document.createElement('span');
  f.className=`wt-flyer wt-c-${S.flyColor||'do'}`;f.setAttribute('aria-hidden','true');S.dlg.append(f);
  const x0=from.left+from.width/2,y0=from.top,x1=r.left+r.width/2,y1=r.top+r.height/2;
  to.style.visibility='hidden';
  const a=f.animate([{transform:`translate(${x0}px,${y0}px) scale(1.6) rotate(-8deg)`,opacity:.2},{transform:`translate(${(x0+x1)/2}px,${Math.min(y0,y1)-60}px) scale(1.3) rotate(10deg)`,opacity:1,offset:.55},
    {transform:`translate(${x1}px,${y1}px) scale(1) rotate(0)`,opacity:1}],{duration:950,easing:'cubic-bezier(.3,.7,.2,1)'});
  a.onfinish=()=>{f.remove();to.style.visibility='';setTimeout(()=>S.dlg?.querySelectorAll('.fresh').forEach(el=>el.classList.remove('fresh')),2400);};
  void key;
}
async function wishAct(op,key,reason){
  if(S.busy)return;S.busy=true;layer();
  const card=isCard(key),n=Number(String(key).slice(1));
  try{
    const r=await S.env.api.post('/api/chua/wishes',{op,[card?'card':'id']:n,...reason?{reason}:{}});
    const now=card?r.card:r.wish,tr=treeOf(S.tree);
    for(const box of [S.list,S.old,S.mine]){if(!box)continue;const k=box.rows.findIndex(w=>rk(w)===key);if(k<0)continue;
      if(op==='report'&&box!==S.mine||!now)box.rows.splice(k,1);else box.rows[k]={...box.rows[k],...now};}
    if(op==='report'||op==='down'&&S.view==='tree'){
      if(op==='down'&&!card&&S.list){const k=S.list.rows.findIndex(w=>rk(w)===key);if(k>=0)S.list.rows.splice(k,1);if(tr)tr.count=Math.max(0,tr.count-1);}
      if(op==='down'&&card&&tr)tr.old=Math.max(0,(tr.old|0)-1);
      S.reader=null;}
    else if(S.reader)S.reader={id:key};
    if(r.message)S.env.toast?.(r.message);
    render();
  }catch(e){S.env.toast?.(e.message||'Chưa được, bạn thử lại nhé.',true);}
  finally{S.busy=false;layer();}
}
function act(kind,data){
  switch(kind){
    case'close':S.dlg.close();return;
    case'back':if(S.reader||S.compose){S.reader=null;S.compose=null;layer();return;}if(S.view!=='garden'){S.view='garden';render();loadGarden();}return;
    case'reload':loadGarden();return;
    case'tree':openTree(data.id);return;
    case'mine':openMine();return;
    case'more':{const mine=S.view==='mine';loadRows(mine?S.mine:S.list,mine?'/api/chua/wishes?mine=1':treeUrl(),true);return;}
    case'more-old':loadRows(S.old,oldUrl(),true);return;
    case'more-cards':S.cards?.load('mine',true);return;
    case'card-share':if(S.cards)S.cards.setPublic({id:data.id},data.public==='true').then(ok=>{if(ok)S.data&&fetchTrees(S.env.api).then(()=>render()).catch(()=>{});});return;
    case'read':S.reader={id:String(data.id)};S.compose=null;layer();return;
    case'prev':step(-1);return;
    case'next':step(1);return;
    case'shut':S.reader=null;S.compose=null;layer();return;
    case'write':if(!S.data?.left||S.data.off)return;S.reader=null;S.compose=S.compose||{text:'',color:'do',anon:false};layer();liveCompose();return;
    case'color':if(S.compose){S.compose.color=data.id;const ta=S.dlg.querySelector('[name="wt-text"]');if(ta)S.compose.text=ta.value;layer();liveCompose();}return;
    case'hang':hang().catch(e=>S.env.toast?.(e.message,true));return;
    case'pray':wishAct('pray',data.id);return;
    case'down':wishAct('down',data.id);return;
    case'report-ask':if(S.reader){S.reader={...S.reader,report:!S.reader.report};layer();}return;
    case'report':wishAct('report',data.id,data.reason);return;
  }
}

/* ---- test hooks (scripts/browser_wish_trees.py) ---- */
globalThis.__wish={state:()=>({open:!!S.dlg?.open,view:S.view,tree:S.tree,rows:rows().length,old:S.old?.rows.length||0,reader:S.reader?.id||null,compose:!!S.compose,left:S.data?.left??null,
  cards:S.cards?.mine.rows.map(c=>({id:c.id,public:c.public===true}))||null})};
