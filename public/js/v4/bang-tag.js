/** ⚔️ Bang tags and my bang's worn items (game/bang.py, live/bangs.py). Small and loaded with the app.
 *  bg {n, e, c, r, k?, b?}: what the live service sends beside a name (chat messages, map and street walkers, cards) and
 *  what the game's profile page carries (profile.bang): the bang's name, emoji, colour id, the role, 👑 (this week's
 *  strongest bang), 🎖️ the badge worn. Colours and roles mirror game/bang_content.py (tests/test_bang.py compares them).
 *  My own bang comes from GET /api/bang/me (loadMine): the uniform drawn on my character (withBang: the bang's top in its
 *  colour, only while I am in that bang), the flag in my home (flagSVG), the boat paint (boatPaint). No DOM work here
 *  beyond one small stylesheet. */
import {escapeHTML as esc} from '../icons.js';
import {setLookOver} from './look.js';

// id: [hex, ink (readable text), wardrobe colour id (look.tint), garage paint id]
export const COLORS={do:['#d2453d','#a3271f','do','do'],vang:['#e0b43f','#8a6410','vang','vang'],mint:['#5cbf9a','#23795a','mint','xanh_la'],navy:['#3a4e7c','#2a3a63','navy','navy'],lavender:['#9d86c9','#6a4fa3','lavender','tim'],hong:['#ef9bb8','#b0456d','hong','hong'],dao:['#f0955a','#a8541c','dao','cam'],den:['#3a3436','#2a2527','den','den'],trang:['#f3f0e8','#6d665a','trang','trang'],bac:['#b8bec6','#5e6670','bac','bac']};
export const ROLES={chu:'Bang chủ',pho:'Phó bang',lao:'Trưởng lão',tinh:'Tinh anh',tv:'Thành viên'};
export const SHORT={chu:'Chủ',pho:'Phó',lao:'Lão',tinh:'Tinh',tv:''};
export const UNIFORM_TOP={polo:'ao_polo',hoodie:'ao_hoodie',aodai:'ao_dai'};
const BITS={ao:1,huy:2,co:4,thuyen:8};
const color=c=>COLORS[c]||COLORS.do;
const clean=bg=>bg&&typeof bg==='object'&&typeof bg.n==='string'&&bg.n?bg:null;

/** "👑 🐉 Rồng Đỏ · Phó bang" (the role left out for a plain member when `short`). */
export function tagLine(bg,short=false){
  bg=clean(bg);if(!bg)return '';
  const role=short?SHORT[bg.r]||'':ROLES[bg.r]||'';
  return `${bg.k?'👑 ':''}${bg.e||'⚔️'} ${bg.n.slice(0,24)}${role?' · '+role:''}`;
}
export const tagInk=bg=>clean(bg)?color(bg.c)[1]:'';
export const tagHex=bg=>clean(bg)?color(bg.c)[0]:'';
/** The badge before a name (🎖️ Huy hiệu bang worn): the bang's emoji, or ''. */
export const badge=bg=>clean(bg)&&bg.b?(bg.e||'⚔️'):'';

let css=false;
function ensureCss(){
  if(css||typeof document==='undefined')return;css=true;
  const s=document.createElement('style');s.dataset.bgCss='';
  s.textContent=`.bg-chip{display:inline-flex;align-items:center;gap:3px;margin-left:4px;padding:0 7px;border-radius:999px;font-style:normal;font-size:.76em;font-weight:700;line-height:1.55;white-space:nowrap;background:#fff7ec;background:color-mix(in srgb,var(--bgc) 16%,#fff);color:var(--bgi);border:1px solid var(--bgc);border:1px solid color-mix(in srgb,var(--bgc) 45%,transparent);vertical-align:middle;max-width:100%;overflow:hidden;text-overflow:ellipsis}
html[data-theme="dem"] .bg-chip{background:#2b2622;background:color-mix(in srgb,var(--bgc) 28%,#1d1a18);color:#f4ece4}
.bg-badge{margin-right:2px}
.dc-roomwrap-3d{position:relative}.bg-flag3d{position:absolute;top:10px;left:12px;z-index:3;pointer-events:none;filter:drop-shadow(0 2px 2px rgba(60,40,20,.35))}`;
  document.head.append(s);
}
/** A small chip with the bang and role, or ''. */
export function chip(bg,short=true){
  bg=clean(bg);if(!bg)return '';ensureCss();const [hex,ink]=color(bg.c);
  return `<em class="bg-chip" style="--bgc:${hex};--bgi:${ink}" title="${esc(tagLine(bg))}" data-no-translate>${esc(tagLine(bg,short))}</em>`;
}
export const badgeHTML=bg=>badge(bg)?`<span class="bg-badge" aria-label="Huy hiệu bang">${esc(badge(bg))}</span>`:'';

/* ---- my bang (GET /api/bang/me) ---- */
const M={mine:null,at:0,pending:null,listeners:new Set()};
export const myBang=()=>M.mine;
export function onMine(fn){M.listeners.add(fn);return ()=>M.listeners.delete(fn);}
export function setMine(mine){
  const before=JSON.stringify(M.mine);M.mine=mine&&typeof mine==='object'&&mine.bang?mine:null;M.at=Date.now();
  setLookOver(wears('ao')?L=>withBang(L):null);   // my character wears the uniform wherever it is drawn (look.js figure)
  if(JSON.stringify(M.mine)!==before)for(const fn of [...M.listeners]){try{fn(M.mine);}catch(e){console.warn('bang:',e);}}
}
/** My membership, at most every 5 minutes unless forced. Never throws. */
export async function loadMine(api,{force=false}={}){
  if(!api?.json)return M.mine;
  if(!force&&M.at&&Date.now()-M.at<300_000)return M.mine;
  if(M.pending)return M.pending;
  M.pending=(async()=>{try{const d=await api.json('/api/bang/me');setMine(d?.mine||null);}catch{/* the last one */}finally{M.pending=null;}return M.mine;})();
  return M.pending;
}
const wears=(item,m=M.mine)=>Boolean(m&&(Number(m.wear)&BITS[item]));
/** The look others see: with the bang uniform in the bang's colour while I wear it (the saved wardrobe is untouched). */
export function withBang(look,m=M.mine){
  if(!look||!wears('ao',m))return look;
  const top=UNIFORM_TOP[m.uniform]||UNIFORM_TOP.polo,c=color(m.color?.id||'do');
  return {...look,top,uniform:false,tint:{...(look.tint||{}),[top]:c[2]}};   // uniform:false: the bang's, not the work uniform
}
/** 🚩 The bang's flag on my wall (v4/reno.js), or ''. */
export function flagSVG(x,y,m=M.mine){
  if(!wears('co',m))return '';
  const [hex,ink]=color(m.color?.id||'do');
  return `<g class="bg-flag" transform="translate(${x} ${y})" aria-label="Cờ bang ${esc(m.name||'')}" role="img"><rect x="-2" y="0" width="4" height="74" rx="2" fill="#8a6a4a"/><circle cx="0" cy="-2" r="4" fill="#e0b43f"/>`
    +`<path d="M2 4h46l-9 13l9 13H2z" fill="${hex}" stroke="${ink}" stroke-width="1.5"/><text x="21" y="22" text-anchor="middle" font-size="14">${esc(m.emoji||'⚔️')}</text></g>`;
}
/** 🚩 The flag pinned in a corner of my 3D room view (v4/reno.js), or ''. */
export function flagBadge(m=M.mine){
  const g=flagSVG(6,8,m);if(!g)return '';ensureCss();
  return `<svg class="bg-flag3d" width="58" height="84" viewBox="0 0 60 88" aria-hidden="true">${g}</svg>`;
}
/** ⛵ The paint of a boat I ride (v4/ride.js wire): the bang's while its boat paint is on, else the vehicle's. */
export function boatPaint(paint,kind,m=M.mine){
  return kind==='boat'&&wears('thuyen',m)?color(m.color?.id||'do')[3]:paint;
}
