// Owner 07/10 ("mấy cái con số nhập hàng, mua vàng,.. đang phải bấm cộng mệt quá, cho nhập số nhé"): the shared typed box
// between − and + (public/js/qty-input.js). Typing, clamping, an empty box, a pasted "1.000", Enter and leaving the box,
// on a small stand-in DOM (no dependencies).
import assert from 'node:assert/strict';
import test from 'node:test';
import {QTY,digits,clampQty,fmtQty,qtyVal,qtyBox,commit,installQty} from '../public/js/qty-input.js';

/* ---- a tiny DOM: enough for the box's listeners ---- */
const unq=s=>s.replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
const attrsOf=html=>{const m=/^<(\w+)([^>]*)>/.exec(html.trim()),a=new Map();for(const x of m[2].matchAll(/([\w-]+)(?:="([^"]*)")?/g))a.set(x[1],unq(x[2]??''));return [m[1].toUpperCase(),a];};
class El{
  constructor(doc,tag,attrs=new Map()){this.ownerDocument=doc;this.nodeName=tag;this.a=attrs;this.parentElement=null;this.kids=[];this.value=attrs.get('value')??'';this.hidden=false;this.clicks=0;}
  getAttribute(k){return this.a.has(k)?this.a.get(k):null;}
  setAttribute(k,v){this.a.set(k,String(v));}
  removeAttribute(k){this.a.delete(k);}
  hasAttribute(k){return this.a.has(k);}
  get dataset(){const d={};for(const [k,v] of this.a)if(k.startsWith('data-'))d[k.slice(5).replace(/-(\w)/g,(_,c)=>c.toUpperCase())]=v;return d;}
  get textContent(){return this.a.get('_text')||'';}
  get form(){return null;}
  closest(sel){
    if(sel==='input[data-qty]')return this.nodeName==='INPUT'&&this.hasAttribute('data-qty')?this:null;
    if(sel==='button')return this.nodeName==='BUTTON'?this:null;
    return null;
  }
  querySelector(sel){return sel.includes('data-qty-sent')?this.kids.find(k=>k.nodeName==='INPUT'&&k.hasAttribute('data-qty')&&k.hasAttribute('data-qty-sent'))||null:null;}
  appendChild(k){k.parentElement=this;this.kids.push(k);return k;}
  remove(){const p=this.parentElement;if(p)p.kids=p.kids.filter(k=>k!==this);this.parentElement=null;}
  dispatchEvent(ev){return this.ownerDocument.fire(ev.type,this,ev);}
  click(){this.clicks++;this.ownerDocument.fire('click',this,{type:'click'});}
  select(){this.sel=[0,this.value.length];}
  setSelectionRange(a,b){this.sel=[a,b];}
  focus(){const d=this.ownerDocument;d.activeElement=this;d.fire('focusin',this,{type:'focusin'});}
  blur(){const d=this.ownerDocument;if(d.activeElement!==this)return;d.activeElement=d.body;if(this.value!==this._atFocus)d.fire('change',this,{type:'change'});d.fire('focusout',this,{type:'focusout'});}
}
class Doc{
  constructor(){this.on={};this.body=new El(this,'BODY');this.activeElement=this.body;this.documentElement=this.body;this.clicked=[];}
  addEventListener(t,f,capture){(this.on[t]??=[]).push({f,capture:!!capture});}
  fire(type,target,ev={}){
    const e={type,target,key:ev.key,isComposing:false,stopped:false,prevented:false,preventDefault(){this.prevented=true;},stopImmediatePropagation(){this.stopped=true;}};
    const list=this.on[type]||[];
    for(const l of [...list.filter(x=>x.capture),...list.filter(x=>!x.capture)]){if(e.stopped)break;l.f(e);}
    if(type==='click'&&!e.stopped&&target.nodeName==='BUTTON')this.clicked.push(target);
    if(type==='focusin')target._atFocus=target.value;
    return !e.prevented;
  }
  createElement(tag){
    const doc=this;
    if(tag!=='template')return new El(doc,tag.toUpperCase());
    return {content:{firstElementChild:null},set innerHTML(h){const [t,a]=attrsOf(h);this.content.firstElementChild=new El(doc,t,a);}};
  }
}
globalThis.Event=class{constructor(type,o={}){this.type=type;this.bubbles=!!o.bubbles;}};
/** A box drawn by qtyBox, put in a stepper row. */
function mount(doc,opts){
  const [tag,a]=attrsOf(qtyBox(opts));const el=new El(doc,tag,a);
  const row=new El(doc,'DIV');row.appendChild(el);doc.body.appendChild(row);
  return el;
}
const type=(doc,el,text)=>{el.value=text;doc.fire('input',el,{type:'input'});};
const key=(doc,el,k)=>doc.fire('keydown',el,{type:'keydown',key:k});

test('digits, clamp, format: a paste of "1.000" is 1000; empty, 0 or nonsense is the minimum; never NaN',()=>{
  assert.equal(digits('1.000'),'1000');
  assert.equal(digits(' 12 phân'),'12');
  assert.equal(digits('-5'),'5');
  assert.equal(digits('007'),'7');
  assert.equal(clampQty('1.000',1,30),30);
  assert.equal(clampQty('1.000',1,5000),1000);
  assert.equal(clampQty('',1,30),1);
  assert.equal(clampQty('0',1,30),1);
  assert.equal(clampQty('0',0,999),0);
  assert.equal(clampQty('abc',2,9),2);
  assert.equal(clampQty('12',5,100,5),10,'guests go by 5');
  assert.equal(clampQty('13',5,100,5),15);
  assert.equal(clampQty('999999999999',5,100,5),100);
  assert.equal(clampQty(NaN,1,10),1);
  assert.ok(Number.isInteger(clampQty(undefined,undefined,undefined)));
  assert.equal(fmtQty(1500,true),(1500).toLocaleString('vi-VN'));
  assert.equal(fmtQty(1500),'1500');
  assert.equal(qtyVal({value:'1.500'}),1500);
  assert.equal(qtyVal({value:''}),0);
});

test('the box: a numeric phone keypad, no autofill, the stepper limits, a money box shows separators',()=>{
  const h=qtyBox({value:12,min:1,max:30,label:'Số lượng'});
  for(const part of ['inputmode="numeric"','pattern="[0-9]*"','autocomplete="off"','type="text"','data-min="1"','data-max="30"','min="1"','max="30"','value="12"','aria-label="Số lượng"'])
    assert.ok(h.includes(part),part);
  const m=qtyBox({value:1500,min:1,max:1e6,money:true});
  assert.ok(m.includes(`value="${(1500).toLocaleString('vi-VN')}"`)&&m.includes('data-qty-was="1500"'),m);
  const g=qtyBox({value:3,min:0,max:999,go:`data-command="ops_keep" data-payload="${JSON.stringify({item:'cup',qty:QTY}).replace(/"/g,'&quot;')}"`});
  assert.ok(g.includes('data-qty-go='),'a stepper box carries its tap');
});

test('typing keeps digits only; Enter clamps and does what a tap does with the typed number',()=>{
  const doc=new Doc();installQty(doc);
  const el=mount(doc,{value:3,min:0,max:999,go:`data-command="ops_keep" data-payload="${JSON.stringify({item:'cup',qty:QTY}).replace(/"/g,'&quot;')}"`});
  el.focus();
  assert.deepEqual(el.sel,[0,1],'the whole number is selected on focus, so typing replaces it');
  type(doc,el,'1a2');
  assert.equal(el.value,'12','letters never get in');
  assert.equal(doc.clicked.length,0,'nothing goes out while typing');
  key(doc,el,'Enter');
  assert.equal(doc.clicked.length,1);
  assert.deepEqual(JSON.parse(doc.clicked[0].getAttribute('data-payload')),{item:'cup',qty:12});
  assert.equal(doc.clicked[0].hidden,true);
  assert.equal(doc.clicked[0].parentElement,null,'the stand-in button is gone again');
  assert.equal(el.value,'12');
  assert.equal(doc.activeElement,doc.body,'Enter closes the keypad');
  assert.equal(doc.clicked.length,1,'leaving after Enter does not send it twice');
});

test('over the max is the max; an empty box is the minimum; the same number is not sent again',()=>{
  const doc=new Doc();installQty(doc);
  const el=mount(doc,{value:5,min:1,max:30,go:'data-action="v4Qty" data-set="987654321"'});
  el.focus();type(doc,el,'250');
  assert.equal(el.value,'250','over the max is allowed while typing');
  el.blur();
  assert.equal(el.value,'30','leaving clamps to the max');
  assert.equal(doc.clicked.at(-1).getAttribute('data-set'),'30');
  const n=doc.clicked.length;
  el.focus();type(doc,el,'');el.blur();
  assert.equal(el.value,'1','empty → the minimum');
  assert.equal(doc.clicked.at(-1).getAttribute('data-set'),'1');
  assert.equal(doc.clicked.length,n+1);
  const other=mount(doc,{value:7,min:1,max:30,go:'data-action="v4Qty" data-set="987654321"'});
  other.focus();type(doc,other,'7');other.blur();
  assert.equal(doc.clicked.length,n+1,'the number it already had: no tap');
  other.focus();type(doc,other,'0');other.blur();
  assert.equal(other.value,'1');
  assert.ok(!Number.isNaN(Number(doc.clicked.at(-1).getAttribute('data-set'))));
});

test('a field box (the screen reads it): Enter clamps and tells the screen with an input event, like a tap',()=>{
  const doc=new Doc();installQty(doc);
  const seen=[];doc.addEventListener('input',e=>seen.push(e.target.value));
  const el=mount(doc,{value:4,min:1,max:6});
  el.focus();type(doc,el,'1.000');
  assert.equal(el.value,'1000','"1.000" pasted: a thousand, no dot');
  key(doc,el,'Enter');
  assert.equal(el.value,'6');
  assert.equal(seen.at(-1),'6','the totals hear the clamped number');
  assert.equal(doc.clicked.length,0,'a field box sends nothing by itself');
  el.focus();type(doc,el,'');el.blur();
  assert.equal(el.value,'1');assert.equal(seen.at(-1),'1');
});

test('a money box: raw digits while typing, separators once left; a paste of "1.000" is a thousand',()=>{
  const doc=new Doc();installQty(doc);
  const el=mount(doc,{value:1500,min:1,max:1e6,money:true,go:'data-qy="step" data-set="987654321"'});
  assert.equal(el.value,(1500).toLocaleString('vi-VN'));
  el.focus();
  assert.equal(el.value,'1500','digits while typing');
  type(doc,el,'2.000');
  assert.equal(el.value,'2000');
  el.blur();
  assert.equal(el.value,(2000).toLocaleString('vi-VN'));
  assert.equal(doc.clicked.at(-1).getAttribute('data-set'),'2000');
  assert.equal(commit(el,true),2000,'what the box holds, read back through the separators');
});

test('live: a page-only number follows every keystroke (gold price on the buy button), clamped',()=>{
  const doc=new Doc();installQty(doc);
  const el=mount(doc,{value:10,min:1,max:100000,live:true,go:'data-action="ivGoldQty" data-n="987654321"'});
  el.focus();type(doc,el,'5');type(doc,el,'55');
  assert.deepEqual(doc.clicked.map(b=>b.getAttribute('data-n')),['5','55']);
  el.blur();
  assert.equal(doc.clicked.length,2,'leaving with the number already out: nothing more');
});

test('a − / + tapped right after a typed number went out steps from the typed number, not the old one',()=>{
  const doc=new Doc();installQty(doc);
  const el=mount(doc,{value:3,min:0,max:999,go:'data-command="ops_keep" data-payload="{&quot;qty&quot;:987654321}"'});
  const plus=new El(doc,'BUTTON',new Map([['data-command','ops_keep'],['data-payload','{"qty":4}'],['_text','+']]));
  el.parentElement.appendChild(plus);
  el.focus();type(doc,el,'20');el.blur();
  assert.equal(JSON.parse(doc.clicked.at(-1).getAttribute('data-payload')).qty,20);
  doc.fire('click',plus,{type:'click'});
  assert.equal(JSON.parse(doc.clicked.at(-1).getAttribute('data-payload')).qty,21,'20 + 1, not the drawn 3 + 1');
  assert.ok(!doc.clicked.includes(plus),'the stale + is not sent');
});
