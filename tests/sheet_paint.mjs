// Owner 21/10 "gõ text ở phát lì xì thì bị tắt rồi scroll": a background redraw (a lì xì grabbed anywhere in town, a
// state whose wallet moved) wrote the whole sheet with innerHTML and threw the focused <input> away mid-word, so the
// phone keyboard closed and the sheet scrolled. v4/sheet-paint.js paint(): written whole when nobody types, patched in
// place (home-morph.js) while a field inside has focus, the field focused again if it still had to be replaced.
// Also checks that the sheets with a text field and a background redraw go through it.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

/* ---- a tiny DOM: elements, text, attributes, a small HTML parser (enough for the morph and paint) ---- */
const VOID=new Set(['INPUT','BR','IMG','HR','META','LINK']);
class N{
  constructor(name,attrs={},text=null){this.nodeName=name;this.nodeType=name==='#text'?3:name==='#frag'?11:1;this.nodeValue=text;this.kids=[];this.parent=null;
    this.attrs=new Map(Object.entries(attrs));this.scrollTop=0;this._value=null;this.checked=false;this.selectionStart=null;this.selectionEnd=null;}
  get id(){return this.attrs.get('id')||'';}
  get firstChild(){return this.kids[0]||null;}
  get nextSibling(){const p=this.parent;if(!p)return null;return p.kids[p.kids.indexOf(this)+1]||null;}
  get attributes(){return [...this.attrs].map(([name,value])=>({name,value,namespaceURI:null}));}
  get value(){return this._value??this.attrs.get('value')??'';}
  set value(v){this._value=String(v);}
  get type(){return this.attrs.get('type')||'text';}
  getAttribute(k){return this.attrs.has(k)?this.attrs.get(k):null;}
  hasAttribute(k){return this.attrs.has(k);}
  setAttribute(k,v){this.attrs.set(k,String(v));}
  removeAttribute(k){this.attrs.delete(k);}
  appendChild(n){if(n.nodeType===11){for(const k of [...n.kids])this.appendChild(k);return n;}n.parent?.removeChild(n);n.parent=this;this.kids.push(n);return n;}
  removeChild(n){this.kids.splice(this.kids.indexOf(n),1);n.parent=null;blurIfGone(n);return n;}
  replaceChild(n,old){n.parent?.removeChild(n);const i=this.kids.indexOf(old);this.kids[i]=n;n.parent=this;old.parent=null;blurIfGone(old);return old;}
  contains(n){for(let x=n;x;x=x.parent)if(x===this)return true;return false;}
  matches(sel){return sel.split(',').some(s=>{const m=s.trim().match(/^([a-z]+)/i);if(!m||m[1].toUpperCase()!==this.nodeName)return false;
    const nots=[...s.matchAll(/:not\(\[type=(\w+)\]\)/g)].map(x=>x[1]);return !nots.includes(this.type);});}
  all(){const out=[];const walk=x=>{for(const k of x.kids){if(k.nodeType===1){out.push(k);walk(k);}}};walk(this);return out;}
  querySelector(sel){
    let m;
    if((m=sel.match(/^#(.+)$/)))return this.all().find(e=>e.id===m[1])||null;
    if((m=sel.match(/^\.([\w-]+)$/)))return this.all().find(e=>(e.getAttribute('class')||'').split(/\s+/).includes(m[1]))||null;
    if((m=sel.match(/^(\w+)\[name="(.+)"\]$/)))return this.all().find(e=>e.nodeName===m[1].toUpperCase()&&e.getAttribute('name')===m[2])||null;
    throw new Error('selector '+sel);
  }
  focus(){doc.activeElement=this;}
  setSelectionRange(a,b){this.selectionStart=a;this.selectionEnd=b;}
  set innerHTML(html){for(const k of [...this.kids])this.removeChild(k);this.appendChild(parse(html));}
}
function blurIfGone(n){if(doc.activeElement&&n.contains(doc.activeElement))doc.activeElement=doc.body;}
function parse(html){
  const frag=new N('#frag'),stack=[frag];
  for(const [,close,tag,attrs,text] of html.matchAll(/<(\/?)(\w+)([^>]*)>|([^<]+)/g)){
    const top=stack.at(-1);
    if(text!==undefined){top.appendChild(new N('#text',{},text));continue;}
    if(close){stack.pop();continue;}
    const el=new N(tag.toUpperCase(),Object.fromEntries([...attrs.matchAll(/([\w-]+)(?:="([^"]*)")?/g)].map(([,k,v])=>[k,v??''])));
    top.appendChild(el);if(!VOID.has(el.nodeName))stack.push(el);
  }
  return frag;
}
const doc={body:new N('BODY'),activeElement:null,createElement:()=>({set innerHTML(h){this.content=parse(h);},content:new N('#frag')})};
doc.activeElement=doc.body;
globalThis.document=doc;

const {paint,typingIn}=await import('../public/js/v4/sheet-paint.js');

const sheet=({wallet='👛 100',flash='',form=true,extra=''}={})=>`<header class="sd-head"><span class="sd-wallet">${wallet}</span></header>`+
  `<div class="sd-body"><p class="sd-flash">${flash}</p>${extra}`+(form?`<section class="sd-card"><input type="text" name="wtext" value="" maxlength="40"><input type="text" name="total" value="100000"></section>`:'')+'</div>';

// 1. Nobody typing: the sheet is written whole, as before (and its scroll comes back on the new body).
let root=new N('DIV');doc.body.appendChild(root);
paint(root,sheet(),'.sd-body');
let body=root.querySelector('.sd-body');body.scrollTop=300;
assert.equal(paint(root,sheet({wallet:'👛 200'}),'.sd-body'),false,'nobody types: nothing kept');
assert.notEqual(root.querySelector('.sd-body'),body,'written anew');
assert.equal(root.querySelector('.sd-body').scrollTop,300,'the scroll comes back on the new body');

// 2. Typing in Lời riêng: a lì xì grab / a wallet that moved redraws the sheet; the field is the same node, it keeps
//    focus, its text and caret; what changed around it is patched; the body (same node) keeps its own scroll.
const input=root.querySelector('input[name="wtext"]');
input.focus();input.value='Chúc mừng';input.setSelectionRange(9,9);
body=root.querySelector('.sd-body');body.scrollTop=420;
assert.equal(typingIn(root),input);
assert.equal(paint(root,sheet({wallet:'👛 999'}),'.sd-body'),true);
assert.equal(root.querySelector('input[name="wtext"]'),input,'the focused field is the same node (the keyboard stays)');
assert.equal(doc.activeElement,input,'it keeps focus');
assert.equal(input.value,'Chúc mừng','and what was typed');
assert.equal(input.selectionStart,9,'and the caret');
assert.equal(root.querySelector('.sd-body'),body,'the body is the same node');
assert.equal(body.scrollTop,420,'its scroll untouched');
assert.equal(root.querySelector('.sd-wallet').firstChild.nodeValue,'👛 999','the wallet is patched in place');
root.querySelector('input[name="total"]').value='5';   // not focused: follows the markup (the form's own number)
paint(root,sheet({wallet:'👛 1'}),'.sd-body');
assert.equal(root.querySelector('input[name="total"]').value,'100000','a field nobody is in follows the markup');
assert.equal(doc.activeElement,input);

// 3. The screen changed shape above the field (a flash line that is a different tag): the field had to be
//    replaced, so the new one is focused again with the text and caret the player had.
assert.equal(paint(root,sheet({extra:'<div class="lxi-sub">⚠</div>'}),'.sd-body'),true);
const again=root.querySelector('input[name="wtext"]');
assert.equal(doc.activeElement,again,'focus is on the field again');
assert.equal(again.value,'Chúc mừng','with the text');
assert.equal(again.selectionStart,9,'and the caret');

// 4. A field outside the sheet (another dialog) does not change how this sheet is written.
const other=new N('INPUT',{type:'text',name:'q'});doc.body.appendChild(other);other.focus();
const before=root.querySelector('.sd-body');
assert.equal(paint(root,sheet(),'.sd-body'),false);
assert.notEqual(root.querySelector('.sd-body'),before);
assert.equal(doc.activeElement,other);
// a checkbox is not typing
const box=root.querySelector('input[name="total"]');box.setAttribute('type','checkbox');box.focus();
assert.equal(typingIn(root),null);

// 5. The sheets with a text field and a background redraw go through paint() (or their own focus keeper).
const src=f=>readFileSync(new URL(`../public/js/v4/${f}`,import.meta.url),'utf8');
const lixi=src('lixi.js');
assert.match(lixi,/function render\(\)\{\s*if\(!S\.dlg\)return;\s*sheetPaint\(S\.dlg\.querySelector\('\.sd-root'\),page\(\),'\.sd-body'\)/,'lì xì: render goes through paint');
assert.match(lixi,/if\(S\.dlg\?\.open&&S\.view!=='give'\)render\(\);/,'lì xì: a grab elsewhere (lixi_upd) does not redraw the give form');
assert.doesNotMatch(lixi,/addEventListener\?\.\('state',\(\)=>\{if\(S\.dlg\?\.open&&S\.view==='give'&&!S\.busy\)render\(\);\}\)/,'lì xì: not every state redraws the give form');
// the same redraw through paint() in every own-dialog sheet with a field and a background redraw (the 21/10 sweep)
const USES={'lixi.js':"sheetPaint(S.dlg.querySelector('.sd-root'),page(),'.sd-body')",'garage.js':"sheetPaint(S.dlg.querySelector('.gr-root'),page(),'.gr-body')",
  'lux.js':"sheetPaint(S.dlg.querySelector('.sd-root'),page(),'.sd-body')",'spend.js':"sheetPaint(S.dlg.querySelector('.sd-root'),page(),'.sd-body')",
  'pets.js':"sheetPaint(root,html,'.pt-body')",'bank.js':"keepFocus(()=>{sheetPaint(S.dlg.querySelector('.bk-root'),page());})",
  'rui.js':"sheetPaint(S.page.querySelector('.wn-card')",'karaoke.js':'sheetPaint(dyn,K.panel?panelHTML()','chat.js':'if(!messages)sheetPaint(b,html);'};
for(const [f,use] of Object.entries(USES)){
  const s=src(f);
  assert.match(s,/^import \{paint as sheetPaint\} from '\.\/sheet-paint\.js';\r?$/m,`${f}: imports paint as sheetPaint, alone on its line (tests strip import lines)`);
  assert.ok(s.includes(use),`${f}: its redraw goes through paint (${use})`);
  // garage.js has its own paint() (a vehicle's colour): a second binding of the same name would not even load
  assert.doesNotMatch(s,/(?:^|[^.\w])(?:const|let|var|function)\s+sheetPaint\b/m,`${f}: no other sheetPaint`);
}
console.log('sheet_paint: ok');
