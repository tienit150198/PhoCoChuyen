/** ♿ Feedback #428 (a blind player: "trò nhặt rương cũng không chơi được và cả lụm bao lì xì nữa"): in the 2.5D town,
 * town chests could only be picked by walking the map, and lì xì only by catching falling envelopes. Like the classic
 * island's list (shared-island.js, F#381), Tiện ích → "Rương & lì xì" opens a small panel (not a modal: the town keeps
 * running while the character walks):
 *  - every chest on the street as a row, nearest first, with "Đi tới và nhặt": the character walks the same route as a
 *    tap on the chest and picks it through the same claim (isometric/treasure.js: it must stand by the chest, the server
 *    checks the proof and the distance as before; nothing is skipped);
 *  - every lì xì that can still be grabbed, with "Giật" (POST /api/lixi/grab, the server draws the amount as always).
 * Results are read out by the panel's live region (and the game's toasts). Esc or ✕ closes it. */
import {escapeHTML as esc} from './icons.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');

/** The chests the town shows (its 'treasure:' hotspots, walkable ones only), nearest first. Pure. */
export function chestRows(world){
  const at=world?.getPresence?.(),counts=new Map((world?.treasure||[]).map(c=>[c.id,c.count||1]));
  return (world?.hotspots||[]).filter(h=>typeof h?.id==='string'&&h.id.startsWith('treasure:')&&Number.isFinite(h.x)&&Number.isFinite(h.y))
    .map(h=>({id:h.id.slice(9),count:counts.get(h.id.slice(9))||1,steps:at?Math.max(0,Math.round(Math.hypot(h.x-at.x,h.y-at.y))):null}))
    .sort((a,b)=>(a.steps??0)-(b.steps??0)||a.id.localeCompare(b.id));
}
export const where=r=>(r.count>1?`${r.count} rương chồng · `:'')+(r.steps==null?'trên phố':r.steps<=1?'ngay cạnh bạn':`cách khoảng ${r.steps} bước`);
/** A lì xì row's words: who, how much, what is left. */
export const lixiLabel=p=>`${p.name||'Một người hàng xóm'} phát ${fmt(p.total)} xu · còn ${p.left}/${p.n} bao`;

const CSS=`.iso-pick{position:fixed;z-index:60;left:max(10px,env(safe-area-inset-left));right:max(10px,env(safe-area-inset-right));top:calc(env(safe-area-inset-top,0px) + 70px);
  max-width:420px;margin:0 auto;max-height:min(60vh,520px);overflow:auto;box-sizing:border-box;padding:10px 12px 12px;border-radius:16px;
  background:var(--surface,#fffaf0);color:var(--ink,#3d2c22);box-shadow:0 10px 30px rgba(60,30,10,.28);border:1px solid var(--line,#e6d6bd);font-size:15px}
.iso-pick header{display:flex;align-items:center;gap:8px}
.iso-pick h2{flex:1;margin:0;font-size:1.05rem}
.iso-pick h3{margin:10px 0 4px;font-size:.92rem}
.iso-pick ul{list-style:none;margin:0;padding:0}
.iso-pick li{display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--line,#eee2cf)}
.iso-pick li>span{flex:1;min-width:0;overflow-wrap:anywhere}
.iso-pick button{min-height:44px;border-radius:12px;border:1px solid var(--line,#e0cfb4);background:var(--accent,#c9533a);color:#fff;font-weight:800;padding:6px 12px;cursor:pointer}
.iso-pick .iso-pick-x{background:transparent;color:inherit;min-width:44px;font-size:1.1rem}
.iso-pick p{margin:4px 0;color:var(--ink-2,#6b5646);font-size:.88rem}
.iso-pick :focus-visible{outline:3px solid #2a6fdb;outline-offset:2px}`;

let view=null;
export function closePickups(){view?.close();}
/** Open (or focus) the panel. `env`: the app env (api, world, toast); `deps` for tests. */
export async function openPickups(env,deps={}){
  if(view){view.focus();return view;}
  const doc=deps.document||globalThis.document;
  const lixi=deps.lixi||await import('./v4/lixi-cards.js').catch(()=>null);
  if(!doc.querySelector('style[data-iso-pick]')){const s=doc.createElement('style');s.dataset.isoPick='';s.textContent=CSS;doc.head.append(s);}
  const prev=doc.activeElement,el=doc.createElement('section');
  el.className='iso-pick';el.setAttribute('role','region');el.setAttribute('aria-labelledby','isoPickTitle');
  el.innerHTML=`<header><h2 id="isoPickTitle" tabindex="-1">Rương & lì xì</h2><button type="button" class="iso-pick-x" data-pick="close" aria-label="Đóng danh sách">✕</button></header>
    <p class="iso-pick-note" role="status" aria-live="polite"></p>
    <h3 id="isoPickChests">📦 Rương trên phố</h3><p data-pick-empty="chests"></p><ul data-pick-list="chests" aria-labelledby="isoPickChests"></ul>
    <h3 id="isoPickLixi">🧧 Lì xì đang phát</h3><p data-pick-empty="lixi"></p><ul data-pick-list="lixi" aria-labelledby="isoPickLixi"></ul>`;
  doc.body.append(el);
  const note=el.querySelector('.iso-pick-note'),chests=el.querySelector('[data-pick-list="chests"]'),packets=el.querySelector('[data-pick-list="lixi"]');
  const say=text=>{note.textContent=String(text||'');};
  const getWorld=deps.world||(await import('./isometric-treasure.js').catch(()=>null))?.townWorld;
  const world=()=>getWorld?.()||env.world;   // the real world: its onInteract is the one isometric-treasure.js wraps
  let shown='',shownLx='',timer=0,off=null;
  const keepFocus=(list,attr,fill)=>{   // rebuild a list; the focused row's button survives by its id
    const a=doc.activeElement,had=list.contains(a)?a.getAttribute(attr):null;fill();
    if(had){const again=[...list.querySelectorAll(`[${attr}]`)].find(b=>b.getAttribute(attr)===had);(again||el.querySelector('h2')).focus({preventScroll:true});}
  };
  function drawChests(){
    const w=world(),rows=w?.mode==='town'?chestRows(w):[],ids=rows.map(r=>r.id).join('|');
    el.querySelector('[data-pick-empty="chests"]').textContent=w?.mode!=='town'?'Ra phố để thấy rương.':rows.length?`${rows.length} rương · gần nhất ở đầu danh sách.`:'Chưa có rương. Rương ra theo đợt; danh sách tự cập nhật.';
    if(ids!==shown){shown=ids;keepFocus(chests,'data-pick-chest',()=>{chests.innerHTML=rows.map((r,i)=>`<li data-row="${esc(r.id)}"><span>Rương ${i+1} · <span data-where>${esc(where(r))}</span></span><button type="button" data-pick-chest="${esc(r.id)}" aria-label="Đi tới và nhặt rương ${i+1}">Đi tới và nhặt</button></li>`).join('');});}
    else for(const r of rows){const n=[...chests.querySelectorAll('[data-row]')].find(li=>li.dataset.row===r.id)?.querySelector('[data-where]');if(n&&n.textContent!==where(r))n.textContent=where(r);}
  }
  function drawLixi(){
    const rows=lixi?lixi.ranked().filter(lixi.grabbable):[],ids=rows.map(p=>`${p.id}:${p.left}`).join('|');
    el.querySelector('[data-pick-empty="lixi"]').textContent=!lixi?'':rows.length?`${rows.length} bao đang chờ.`:'Chưa có lì xì để giật.';
    if(ids===shownLx)return;shownLx=ids;
    keepFocus(packets,'data-pick-lixi',()=>{packets.innerHTML=rows.map(p=>`<li><span data-no-translate>${esc(lixiLabel(p))}</span><button type="button" data-pick-lixi="${esc(p.id)}" aria-label="${esc(`Giật lì xì của ${p.name||'một người hàng xóm'}`)}">Giật</button></li>`).join('');});
  }
  function walkTo(id){
    const w=world(),hid='treasure:'+id;
    if(!w||w.mode!=='town'){say('Ra phố trước để đi nhặt rương nhé.');return;}
    if(!(w.hotspots||[]).some(h=>h.id===hid)){say('Rương này đã được nhặt. Danh sách đã cập nhật.');drawChests();return;}
    const row=chestRows(w).find(r=>r.id===id);
    say(row?.steps>1?`Đang đi tới rương, khoảng ${row.steps} bước…`:'Đang nhặt rương…');
    // the same route and the same claim as a tap on the chest (isometric-treasure.js wraps onInteract)
    w.go(hid,()=>w.onInteract?.(hid));
  }
  async function grab(id){
    say('Đang giật lì xì…');
    try{const m=deps.grab?{grab:deps.grab}:await import('./v4/lixi.js');await m.grab(id,null,{say});}
    catch(e){say(e?.message||'Chưa giật được. Thử lại nhé.');}
    drawLixi();
  }
  const onClick=e=>{const b=e.target.closest?.('button');if(!b||!el.contains(b))return;
    if(b.dataset.pick==='close')close();else if(b.dataset.pickChest)walkTo(b.dataset.pickChest);else if(b.dataset.pickLixi)void grab(b.dataset.pickLixi);};
  const onKey=e=>{if((e.key==='Escape'||e.key==='Esc')&&el.contains(doc.activeElement)){e.preventDefault();e.stopPropagation();close();}};
  el.addEventListener('click',onClick);el.addEventListener('keydown',onKey);
  function close(){
    if(!view)return;view=null;clearInterval(timer);off?.();el.remove();
    if(prev?.isConnected&&prev!==doc.body)prev.focus?.({preventScroll:true});
  }
  drawChests();drawLixi();
  timer=setInterval(()=>{if(!el.isConnected){close();return;}drawChests();drawLixi();},1000);
  if(lixi){off=lixi.onChange?.(drawLixi)||null;lixi.refresh?.(env.api,0);}
  view={el,close,focus:()=>el.querySelector('h2').focus({preventScroll:true}),say,drawChests,drawLixi};
  view.focus();
  return view;
}
