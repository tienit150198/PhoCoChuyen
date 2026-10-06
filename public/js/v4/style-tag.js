/** 🎨 Status of the week (game/spend.py): a name colour, a profile frame and a title, as `st` {c?, f?, t?} of catalogue
 * ids. The live service sends it beside a name (live/styles.py: chat messages, walkers, cards), the player's own comes
 * from api.state.journey.spend.st and other players' cards from shop.style (game/social.py). Unknown ids show nothing.
 * Colours have a light and a dark value (both ≥ 4.5:1, tests/test_spend.py); the theme picks one in CSS. */
import {escapeHTML as esc} from '../icons.js';

const HEX=/^#[0-9a-f]{6}$/i;
const cat=api=>api?.content?.journey?.spend||null;
let ready=false;
/** One small global stylesheet, added on first use (no file to load). */
function ensureCss(){
  if(ready||typeof document==='undefined')return;ready=true;
  const s=document.createElement('style');s.dataset.stCss='';
  s.textContent=`.st-nm{color:var(--stl)!important}html[data-theme="dem"] .st-nm{color:var(--std)!important}
.st-nm.st-grad{background:linear-gradient(90deg,var(--stg1),var(--stg2));-webkit-background-clip:text;background-clip:text;color:transparent!important}
html[data-theme="dem"] .st-nm.st-grad{background:linear-gradient(90deg,var(--stgd1),var(--stgd2));-webkit-background-clip:text;background-clip:text}
.st-fr{box-shadow:0 0 0 2px var(--str),0 0 0 4px rgba(255,255,255,.55)!important;position:relative}
.st-fr[data-st-badge]::after{content:attr(data-st-badge);position:absolute;right:-6px;bottom:-6px;font-size:12px;line-height:1}
.st-ti{display:inline-block;margin-left:4px;padding:0 6px;border-radius:999px;font-style:normal;font-size:.78em;font-weight:700;background:var(--surface-2,#f6ecdf);color:var(--ink-2,#5a4436)}`;
  document.head.append(s);
}
export function item(api,id){const c=cat(api);if(!c||typeof id!=='string')return null;return c.colors.find(x=>x.id===id)||c.frames.find(x=>x.id===id)||c.titles.find(x=>x.id===id)||null;}
/** Attributes for a name: ` class="st-nm…" style="…"` (with a leading space), or '' when no colour is worn. */
export function nameAttrs(api,st,cls=''){
  const c=item(api,st?.c);if(!c||!HEX.test(c.light)||!HEX.test(c.dark))return cls?` class="${cls}"`:'';ensureCss();
  const g=Array.isArray(c.grad)&&c.grad.every(x=>HEX.test(x))?`;--stg1:${c.grad[0]};--stg2:${c.grad[1]};--stgd1:${(c.grad_dark||c.grad)[0]};--stgd2:${(c.grad_dark||c.grad)[1]}`:'';
  return ` class="${cls?cls+' ':''}st-nm${g?' st-grad':''}" style="--stl:${c.light};--std:${c.dark}${g}"`;
}
/** Attributes for an avatar or a card: ` st-fr` to append to its class list, and the style with the ring colour. */
export function frameAttrs(api,st){
  const f=item(api,st?.f);if(!f||!HEX.test(f.ring))return {cls:'',attrs:''};ensureCss();
  return {cls:' st-fr',attrs:` style="--str:${f.ring}" data-st-badge="${esc(f.emoji)}"`};
}
/** A small chip with the bought title ("☕ Tín đồ cà phê"), or ''. */
export function titleChip(api,st){const t=item(api,st?.t);if(!t)return '';ensureCss();return `<em class="st-ti">${esc(t.emoji)} ${esc(t.name)}</em>`;}
/** For a canvas: the name's fill (a colour, or two stops for a gradient) and the ring, on this theme. */
export function paint(api,st,dark){
  const c=item(api,st?.c),f=item(api,st?.f);
  const grad=c&&Array.isArray(c.grad)?(dark?(c.grad_dark||c.grad):c.grad):null;
  return {color:c?(dark?c.dark:c.light):null,grad:grad&&grad.every(x=>HEX.test(x))?grad:null,ring:f&&HEX.test(f.ring)?f.ring:null,badge:f?.emoji||''};
}
