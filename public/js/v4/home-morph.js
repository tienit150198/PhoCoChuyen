/** 🏠 Redraw a home sheet (🏠 Nhà của bạn, 🪴 Bày trí phòng) without throwing its DOM away.
 *
 * Writing the whole sheet with innerHTML on every state event (the wallet ticking while staff work, a spouse moving a
 * piece) reset every inner scroll: the drawer's card rail jumped back to its first card and a fling stopped half way,
 * so the last cards were out of reach (góp ý, chat 06/10). morph() patches the markup in place instead, like app.js
 * does for the work sheet: unchanged nodes keep their identity, so a rail keeps its scrollLeft (and a smooth scroll in
 * flight), a button keeps focus, a <details> the player opened stays open.
 * Nodes are matched by position, tag, id and data-dc-rail (a rail never turns into another rail). A node marked
 * data-whole (the room drawing: its pieces are reordered by the walking figure) is always written anew, as before.
 * Form fields follow the markup unless the player is in them. Pure DOM, no imports (tests/home_morph.mjs). */
let tpl=null;

const key=n=>n.nodeType===1?`${n.nodeName}#${n.id||''}@${n.getAttribute('data-dc-rail')||''}`:n.nodeName;
const whole=n=>n.nodeType===1&&n.hasAttribute('data-whole');

export function morph(el,html){
  tpl??=document.createElement('template');
  tpl.innerHTML=html;
  kids(el,tpl.content);
  tpl.innerHTML='';
}

/** Patch the children of `from` to match those of `to` (exported for tests/home_morph.mjs). */
export function kids(from,to){
  let a=from.firstChild,b=to.firstChild;
  while(b){
    const nb=b.nextSibling;
    if(a&&a.nodeType===b.nodeType&&key(a)===key(b)&&!whole(b)){node(a,b);a=a.nextSibling;}
    else if(a){const na=a.nextSibling;from.replaceChild(b,a);a=na;}
    else from.appendChild(b);
    b=nb;
  }
  while(a){const na=a.nextSibling;from.removeChild(a);a=na;}
}

function node(a,b){
  if(a.nodeType!==1){if(a.nodeValue!==b.nodeValue)a.nodeValue=b.nodeValue;return;}
  const keepOpen=a.nodeName==='DETAILS';   // the player's open/closed fold wins over the markup
  for(const at of [...b.attributes]){
    if(keepOpen&&at.name==='open')continue;
    if(a.getAttribute(at.name)!==at.value){if(at.namespaceURI)a.setAttributeNS(at.namespaceURI,at.name,at.value);else a.setAttribute(at.name,at.value);}
  }
  for(const at of [...a.attributes]){if(!(keepOpen&&at.name==='open')&&!b.hasAttribute(at.name))a.removeAttribute(at.name);}
  kids(a,b);
  const tag=a.nodeName;
  if((tag==='INPUT'||tag==='TEXTAREA'||tag==='SELECT')&&a!==globalThis.document?.activeElement){
    if(tag==='SELECT'){for(let i=0;i<b.options.length;i++)if(a.options[i]&&a.options[i].selected!==b.options[i].selected)a.options[i].selected=b.options[i].selected;}
    else{if(a.value!==b.value)a.value=b.value;if(a.checked!==b.checked)a.checked=b.checked;}
  }
}

/** The horizontal rails under `root` ({key: scrollLeft}), to put back on rails that had to be written anew. */
export function railScroll(root,attr='data-dc-rail'){
  const out=new Map();
  for(const el of root?.querySelectorAll?.(`[${attr}]`)||[])out.set(el.getAttribute(attr),{el,left:el.scrollLeft});
  return out;
}
/** After a redraw: a rail that is the same node kept its scroll (and any smooth scroll in flight: never touched);
 * one written anew gets its old position back; `reset` keys start from their first card. */
export function railRestore(root,saved,reset=()=>false,attr='data-dc-rail'){
  for(const el of root?.querySelectorAll?.(`[${attr}]`)||[]){
    const k=el.getAttribute(attr),was=saved.get(k);
    if(reset(k)){if(el.scrollLeft)el.scrollLeft=0;continue;}
    if(was&&was.el!==el&&el.scrollLeft!==was.left)el.scrollLeft=was.left;
  }
}
