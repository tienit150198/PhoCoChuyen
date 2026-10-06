/** One shared action bar for every work screen on a phone (mobile compact layout, WP8).
 *
 * Sixteen careers each pin their own button bar at the bottom of the work sheet (.fk-bar, .dw-bar, .sl-bar,
 * .gr-billbar…), each with its own padding, radius and height (66–101 px on a phone). Instead of rewriting
 * them, the guide (v4/guide.js placeToasts, run after every sheet render and whenever a note arrives) hands the
 * bar it found to syncBar(): the bar gets the shared class `abar` (styled once in css/compact.css on phones),
 * and the sheet learns its height, so the scroll padding matches it (--abar-h) and nothing is left under it
 * once the player scrolls to the end.
 *
 * It also measures the sheet header (--hd-t/--hd-h top and height, --hd-btns the width of its buttons on the
 * right) so a note (toast) can sit inside the header's title row on a phone: never over a control, the order
 * or the action bar.
 *
 * Layout only: no state, no commands. Every write is skipped when the value did not change. */

import {warnBudget} from '../ui-kit.js';

/** The careers' own bars (the guide finds a bar through its .gd-cta; a bar without one is picked by name). */
export const BARS='.ui-bar,.fk-bar,.dw-bar,.tt-bar,.dl-bar,.ao-bar,.tv-bar,.fa-bar,.mb-ctabar,.rp-bar,.pl-bar,.sk-bar,.td-bar,.hs-bar,.ps-bar,.ok-bar,.gr-billbar,.sl-bar,.pc-bar';
const set=(el,k,v)=>{if(el.style.getPropertyValue(k)!==v)el.style.setProperty(k,v);};

/** The width taken by the header's right-hand controls (⋯, ❔, ✕, a tag): everything after the title column. */
function headButtons(head){
  const grow=head.querySelector(':scope>.grow,:scope>div:first-child');
  let left=Infinity;
  for(const el of head.children){
    if(el===grow||el.classList.contains('mn-line'))continue;
    const r=el.getBoundingClientRect();
    if(r.width&&r.left>((grow?.getBoundingClientRect().left)??0))left=Math.min(left,r.left);
  }
  const hr=head.getBoundingClientRect();
  return Number.isFinite(left)?Math.max(0,Math.round(hr.right-left)):0;
}

/** Mark the pinned bar (or forget it) and measure the header. `bar` is the sticky/fixed element that holds the
 * work screen's bottom button, or null. */
export function syncBar(dialog,bar){
  if(!dialog)return;
  if(!bar&&dialog.open)bar=[...dialog.querySelectorAll(BARS)].find(e=>e.getClientRects().length&&!e.closest('details:not([open])'))||null;
  for(const old of dialog.querySelectorAll('.abar'))if(old!==bar)old.classList.remove('abar');
  if(bar&&!bar.classList.contains('abar'))bar.classList.add('abar');
  const h=bar?Math.round(bar.getBoundingClientRect().height):0;
  set(dialog,'--abar-h',`${h}px`);
  dialog.toggleAttribute('data-abar',!!bar);
  if(dialog.open&&dialog.querySelector('.career-job'))warnBudget(dialog);   // dev: the screen's word cap (ui-kit.js)
  const head=dialog.querySelector('#sheetContent .sheet-head,#sheetContent .preparation-topline');
  if(head){
    const r=head.getBoundingClientRect();
    set(dialog,'--hd-t',`${Math.max(0,Math.round(r.top))}px`);
    set(dialog,'--hd-h',`${Math.round(r.height)}px`);
    set(dialog,'--hd-btns',`${headButtons(head)}px`);
  }
}
