/** ♿ Screen readers in the own-dialog sheets (feedback #519, a blind player: "chọn vô mục du lịch thì chỗ làm hộ chiếu
 * tôi không thể vô được"). Sheets like ✈️ Du lịch and 🛍️ Mua sắm redraw their whole root on every tap and on
 * background states: the button the player had just pressed was thrown away, focus fell to <body>, and TalkBack /
 * VoiceOver / NVDA lost their place (often back to the top of the page, outside the dialog).
 *
 *  - keep(dlg, root, write): runs `write` (the redraw); the control that had focus, or was tapped a moment ago (a
 *    phone's screen reader activates a button without focusing it), is found again in the new markup by its data-* /
 *    name / role attributes and focused (no scroll). When it is gone (the screen changed), focus goes to the screen's
 *    heading: [data-focus-here], else the dialog's h2, so the reader starts reading the new screen.
 *  - home(root): that heading, focused (on open).
 *  - say(dlg, text): one live region per dialog, outside the redrawn root (a region written anew with its text
 *    already in it is not read out), so results ("Đã cấp visa…", "Còn thiếu 200 xu") are announced.
 * Pure DOM, no state of its own beyond a property on the dialog (tests/sheet_focus.mjs). */

const RECENT_MS=2500;
const KEEP=new Set(['name','role','type']);
/** What identifies a control across a redraw: its tag and data-* (+ name, role) attributes; plain text otherwise. */
export function sigOf(el){
  if(!el?.attributes)return '';
  const a=[...el.attributes].filter(x=>(x.name.startsWith('data-')&&x.name!=='data-why')||KEEP.has(x.name)).map(x=>`${x.name}=${x.value}`).sort().join('&');
  return `${el.tagName}|${a||'#'+String(el.textContent||'').trim().slice(0,40)}`;
}
const CONTROL='button,a[href],summary,input,select,textarea,[tabindex]';
function find(root,sig,nth){
  let same=[];
  try{same=[...root.querySelectorAll(CONTROL)].filter(x=>sigOf(x)===sig);}catch{return null;}
  return same[nth]||same[0]||null;
}
function where(root,el){
  const sig=sigOf(el);let nth=0;
  try{nth=[...root.querySelectorAll(CONTROL)].filter(x=>sigOf(x)===sig).indexOf(el);}catch{nth=0;}
  return {sig,nth:Math.max(0,nth)};
}
/** Remember the control last tapped inside `root` and the last one focused (once per dialog). */
function track(dlg){
  if(!dlg||dlg.__sfTrack||!dlg.addEventListener)return;
  dlg.__sfTrack=true;guard(dlg.ownerDocument);
  dlg.addEventListener('click',e=>{
    const el=e.target?.closest?.(CONTROL);if(!el||el===dlg)return;
    dlg.__sfTap={el,at:Date.now()};
  },true);
  dlg.addEventListener('focusin',e=>{const el=e.target;if(el&&el!==dlg&&el.matches?.(CONTROL))dlg.__sfLast=where(dlg,el);});
}
/** Focus back into `dlg` (the control focused last, else the heading). */
export function restore(dlg,doc=globalThis.document){
  const spot=dlg?.__sfLast,el=spot?find(dlg,spot.sig,spot.nth):null;
  if(el&&el.getClientRects?.().length!==0){try{el.focus({preventScroll:true});}catch{/* gone */}if(doc?.activeElement===el)return el;}
  return home(dlg?.querySelector?.('.sd-root')||dlg,doc);
}
/** Once per page: a popup over a sheet (a new title, a chapter…) closes after the sheet was redrawn under it, so the
 * browser has nothing to give focus back to and it lands on <body>: it goes back into the sheet on top instead. */
function guard(doc){
  if(!doc||doc.__sfGuard||!doc.addEventListener)return;
  doc.__sfGuard=true;
  doc.addEventListener('close',()=>setTimeout(()=>{
    const a=doc.activeElement;if(a&&a!==doc.body&&a!==doc.documentElement)return;
    const top=[...doc.querySelectorAll('dialog[open]')].pop();
    if(top?.__sfTrack)restore(top,doc);
  },0),true);
}
export function home(root,doc=globalThis.document){
  const h=root?.querySelector?.('[data-focus-here]')||root?.querySelector?.('h2');
  if(!h)return null;
  if(!h.hasAttribute('tabindex'))h.setAttribute('tabindex','-1');
  try{h.focus({preventScroll:true});}catch{/* detached */}
  return doc?.activeElement===h?h:null;
}
export function keep(dlg,root,write,doc=globalThis.document){
  track(dlg);
  const a=doc?.activeElement,tap=dlg?.__sfTap,loose=!a||a===doc.body||a===dlg;
  let from=null,spot=null;
  if(a&&a!==doc.body&&root?.contains?.(a))from=a;
  else if(tap&&Date.now()-tap.at<RECENT_MS&&root?.contains?.(tap.el)&&loose)from=tap.el;
  if(from)spot=where(root,from);
  else if(dlg?.__sfWait&&loose)spot=dlg.__sfWait;   // a control that was disabled while a command ran
  if(dlg)dlg.__sfWait=null;
  write();
  if(!spot||!dlg?.open)return;
  if(from?.isConnected&&root.contains(from))return;   // patched in place (the same node): nothing moved
  const el=find(root,spot.sig,spot.nth);
  if(from&&dlg.__sfTap?.el===from)dlg.__sfTap={el:el||null,at:dlg.__sfTap.at};
  if(el?.disabled){dlg.__sfWait=spot;return;}   // busy: it comes back on the next redraw (a disabled control takes no focus)
  if(el&&el.getClientRects?.().length!==0){try{el.focus({preventScroll:true});}catch{/* gone */}if(doc.activeElement===el)return;}
  home(root,doc);
}
export function say(dlg,text){
  if(!dlg)return;
  let r=dlg.querySelector?.(':scope>.sf-live');
  if(!r){r=dlg.ownerDocument.createElement('p');r.className='sr-only sf-live';r.setAttribute('role','status');r.setAttribute('aria-live','polite');r.setAttribute('aria-atomic','true');dlg.append(r);}
  text=String(text||'');
  if(r.textContent===text){r.textContent='';if(text)setTimeout(()=>{r.textContent=text;},60);return;}   // the same words again: read again
  r.textContent=text;
}
