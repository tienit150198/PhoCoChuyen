/** ⌨️ Redraw an own-dialog sheet without taking the field the player is typing in away (owner 21/10: "gõ text ở phát
 * lì xì thì bị tắt rồi scroll"). Sheets like 🧧 Lì xì, 🚗 Garage, 🐾 Thú cưng write their whole root with innerHTML on
 * background events (a lì xì grabbed anywhere in town, a state whose wallet moved, a live frame): the focused <input>
 * was thrown away mid-word, so the phone keyboard closed and the page scrolled back.
 * paint(root, html, body) writes the markup as before when nobody is typing in `root`; while a field inside it has
 * focus, it patches the markup in place instead (home-morph.js: same nodes, the focused field keeps its node, value,
 * caret and keyboard), and if the field still had to be replaced (the screen changed shape) it is focused again with
 * its text and caret. `body` (a selector): the scrolling part, whose scroll is put back when it was written anew.
 * Pure DOM, no state (tests/sheet_paint.mjs). */
import {morph} from './home-morph.js';

const FIELD='input:not([type=button]):not([type=checkbox]):not([type=radio]):not([type=range]):not([type=hidden]):not([type=submit]):not([type=file]),textarea,select,[contenteditable="true"]';

/** The text field inside `root` that has focus (null: nobody is typing there). */
export function typingIn(root,doc=globalThis.document){
  const a=doc?.activeElement;
  return a&&a!==doc.body&&root?.contains?.(a)&&a.matches?.(FIELD)?a:null;
}
const keyOf=a=>a.id?`#${cssEsc(a.id)}`:a.getAttribute?.('name')?`${a.nodeName.toLowerCase()}[name="${cssEsc(a.getAttribute('name'))}"]`:null;
const cssEsc=s=>globalThis.CSS?.escape?CSS.escape(s):String(s).replace(/["\\]/g,'\\$&');

export function paint(root,html,body=null,doc=globalThis.document){
  if(!root)return false;
  const was=body?root.querySelector(body):null,y=was?was.scrollTop:0;
  const a=typingIn(root,doc);
  if(a&&root.firstChild){
    const key=keyOf(a),value=a.value,start=a.selectionStart,end=a.selectionEnd;
    morph(root,html);
    if(doc.activeElement!==a&&key){   // replaced after all: the same field again, as the player left it
      const el=root.querySelector(key);
      if(el){if(el.value!==value)el.value=value;el.focus({preventScroll:true});try{if(start!=null)el.setSelectionRange(start,end);}catch{/* number inputs */}}
    }
  }else root.innerHTML=html;
  if(y){const now=root.querySelector(body);if(now&&now!==was&&now.scrollTop!==y)now.scrollTop=y;}
  return Boolean(a);
}
