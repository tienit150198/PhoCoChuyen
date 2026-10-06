// BACKLOG #12 / chat 06/10: lists and decor rails must not jump while the player scrolls. Checks the two helpers:
// home-morph.js (a home sheet patched in place keeps its rails' nodes, so their scroll) and work-equipment.js
// scrollGuard (a background redraw waits for a fling; a tap alone does not wait; inner lists get their scroll back).
import assert from 'node:assert/strict';
import {kids,railScroll,railRestore} from '../public/js/v4/home-morph.js';
import {scrollGuard} from '../public/js/v4/work-equipment.js';

/* ---- a tiny DOM: enough for the morph (children, attributes, text) ---- */
class N{
  constructor(name,attrs={},kidsList=[],text=null){this.nodeName=name;this.nodeType=name==='#text'?3:1;this.nodeValue=text;this.kids=[];this.parent=null;
    this.attrs=new Map(Object.entries(attrs));this.scrollLeft=0;this.scrollTop=0;for(const k of kidsList)this.appendChild(k);}
  get id(){return this.attrs.get('id')||'';}
  get firstChild(){return this.kids[0]||null;}
  get nextSibling(){const p=this.parent;if(!p)return null;return p.kids[p.kids.indexOf(this)+1]||null;}
  get attributes(){return [...this.attrs].map(([name,value])=>({name,value,namespaceURI:null}));}
  getAttribute(k){return this.attrs.has(k)?this.attrs.get(k):null;}
  hasAttribute(k){return this.attrs.has(k);}
  setAttribute(k,v){this.attrs.set(k,String(v));}
  removeAttribute(k){this.attrs.delete(k);}
  appendChild(n){n.parent?.removeChild(n);n.parent=this;this.kids.push(n);return n;}
  removeChild(n){this.kids.splice(this.kids.indexOf(n),1);n.parent=null;return n;}
  replaceChild(n,old){n.parent?.removeChild(n);const i=this.kids.indexOf(old);this.kids[i]=n;n.parent=this;old.parent=null;return old;}
  querySelectorAll(sel){const m=sel.match(/^\[(.+)\]$/),out=[];const walk=x=>{for(const k of x.kids){if(k.nodeType===1&&k.hasAttribute(m[1]))out.push(k);walk(k);}};walk(this);return out;}
}
const T=s=>new N('#text',{},[],s);
const card=(k,extra={})=>new N('BUTTON',{class:'dc-buycard','data-k':k,...extra},[T(k)]);
const page=(cards,{money='💰 10 xu',room='r1',open=false}={})=>new N('DIV',{},[
  new N('P',{class:'bk-flash'},[T(money)]),
  new N('svg',{'data-whole':'',class:'dc-room','data-room':room},[new N('g',{},[T(room)])]),
  new N('DETAILS',{class:'dc-why',...(open?{open:''}:{})},[new N('SUMMARY',{},[T('Điểm tính thế nào?')])]),
  new N('DIV',{class:'dc-scroll'},[new N('DIV',{class:'dc-strip','data-dc-rail':'items'},cards.map(k=>card(k)))])]);

// 1. A redraw where only the money changed keeps the rail node: its scrollLeft (and a fling) survive.
const root=new N('DIV');kids(root,page(['a','b','c','d']));
const rail=root.querySelectorAll('[data-dc-rail]')[0],svg=root.kids[1],why=root.kids[2];
rail.scrollLeft=420;why.setAttribute('open','');   // the player scrolled the drawer and opened the fold
const saved=railScroll(root);
kids(root,page(['a','b','c','d'],{money:'💰 99 xu'}));
assert.equal(root.querySelectorAll('[data-dc-rail]')[0],rail,'the rail is the same node after a redraw');
assert.equal(rail.scrollLeft,420,'its scroll is untouched');
assert.equal(root.kids[0].kids[0].nodeValue,'💰 99 xu','what changed is patched');
assert.notEqual(root.kids[1],svg,'the room drawing (data-whole) is written anew, as before');
assert.ok(root.kids[2].hasAttribute('open'),'a fold the player opened stays open');
railRestore(root,saved);assert.equal(rail.scrollLeft,420,'restoring a kept rail never writes its scroll (a smooth scroll goes on)');

// 2. Only the cards change (a purchase): the rail node stays, its cards are re-rendered.
kids(root,page(['a','b','c','d','e']));
assert.equal(root.querySelectorAll('[data-dc-rail]')[0],rail);
assert.deepEqual(rail.kids.map(c=>c.getAttribute('data-k')),['a','b','c','d','e']);
assert.equal(rail.scrollLeft,420);

// 3. Switching drawer tab / category starts the strip from its first card; the rooms rail keeps its place.
const saved2=railScroll(root);railRestore(root,saved2,k=>k!=='rooms');assert.equal(rail.scrollLeft,0,'a reset key starts over');

// 4. A rail that had to be written anew (another rail took its place) gets its old position back.
const r2=new N('DIV');kids(r2,new N('DIV',{},[new N('DIV',{'data-dc-rail':'cats'},[card('x')])]));
const cats=r2.querySelectorAll('[data-dc-rail]')[0];cats.scrollLeft=77;const s2=railScroll(r2);
kids(r2,new N('DIV',{},[new N('DIV',{'data-dc-rail':'items'},[card('y')]),new N('DIV',{'data-dc-rail':'cats'},[card('x')])]));
const cats2=r2.querySelectorAll('[data-dc-rail]').find(x=>x.getAttribute('data-dc-rail')==='cats');
assert.notEqual(r2.querySelectorAll('[data-dc-rail]')[0],cats,'a rail is never morphed into another rail');
railRestore(r2,s2);assert.equal(cats2.scrollLeft,77,'a rail written anew gets its scroll back');

/* ---- scrollGuard: fake clock, timers and an event target ---- */
let clock=0;const timers=new Map();let tid=0;
const g=scrollGuard({quiet:350,now:()=>clock,setT:(f,ms)=>{timers.set(++tid,{f,at:clock+ms});return tid;},clearT:t=>timers.delete(t)});
const run=ms=>{clock+=ms;for(const [id,t] of [...timers])if(t.at<=clock){timers.delete(id);t.f();}};
const handlers={};const sheet={addEventListener:(t,f)=>{(handlers[t]??=[]).push(f);},querySelectorAll:()=>[]};
const fire=(t,e={})=>(handlers[t]||[]).forEach(f=>f(e));
g.watch(sheet);g.watch(sheet);
assert.equal(handlers.scroll.length,1,'watching twice adds one set of listeners');
let renders=0;const redraw=()=>renders++;
// a tap (finger down and up, no scroll) holds nothing up
fire('touchstart',{touches:[1]});fire('touchend',{touches:[]});
assert.equal(g.busy(),false,'a tap alone is not scrolling');
g.later(redraw);assert.equal(renders,1,'idle: the redraw runs at once');
// a fling: the redraw waits while scroll events come, then runs once
fire('touchstart',{touches:[1]});fire('scroll',{target:sheet});
g.later(redraw);g.later(redraw);assert.equal(renders,1,'finger down: waits');
fire('touchend',{touches:[]});
for(let i=0;i<10;i++){run(16);fire('scroll',{target:sheet});}   // momentum
assert.equal(renders,1,'still flinging: waits');
run(400);assert.equal(renders,2,'settled: one redraw, the newest');
run(2000);assert.equal(renders,2,'and only once');
assert.equal(g.busy(),false);
// a wheel turn on a desktop counts as scrolling too
fire('wheel');assert.equal(g.busy(),true);run(400);assert.equal(g.busy(),false);

// restore(): an inner list the player scrolled, written anew by a morph mismatch, gets its scroll back
const list1={nodeType:1,id:'',tagName:'DIV',classList:['fb-detail'],scrollTop:300,scrollLeft:0,isConnected:true};
const host={addEventListener:(t,f)=>{(handlers2[t]??=[]).push(f);},querySelectorAll:sel=>sel==='div.fb-detail'?[cur]:[]};
const handlers2={};let cur=list1;
const g2=scrollGuard({now:()=>clock,setT:()=>0,clearT:()=>{}});g2.watch(host);
(handlers2.scroll||[]).forEach(f=>f({target:list1}));
list1.isConnected=false;const list2={...list1,scrollTop:0,isConnected:true};cur=list2;
g2.restore(host);assert.equal(list2.scrollTop,300,'the new list node scrolls back to where the player was');
list2.scrollTop=120;(handlers2.scroll||[]).forEach(f=>f({target:list2}));g2.restore(host);assert.equal(list2.scrollTop,120,'a kept node is left alone');
g2.reset();list2.isConnected=false;const list3={...list1,scrollTop:0,isConnected:true};cur=list3;g2.restore(host);assert.equal(list3.scrollTop,0,'a new view starts at the top');

console.log('Home scroll: morph keeps rails, folds and focus; rails restore/reset; scroll guard defers redraws and restores inner lists');
