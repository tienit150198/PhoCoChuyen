import assert from 'node:assert/strict';
import test from 'node:test';

// Drive the public module with a small DOM and fake clock; no server or real timers.
async function fixture(t,{incoming=[],outgoing=[]}={}){
 const saved={document:globalThis.document,MutationObserver:globalThis.MutationObserver,setTimeout:globalThis.setTimeout,clearTimeout:globalThis.clearTimeout,now:Date.now};
 let now=1000000,id=0;const timers=new Map(),observers=[];
 class Element{
  constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.listeners=new Map();this.open=false;this.scrollTop=0;this.classList={toggle(){}};}
  append(child){if(child.parentElement)child.parentElement.children=child.parentElement.children.filter(x=>x!==child);this.children.push(child);child.parentElement=this;}
  before(child){const parent=this.parentElement;if(child.parentElement)child.parentElement.children=child.parentElement.children.filter(x=>x!==child);parent.children.splice(parent.children.indexOf(this),0,child);child.parentElement=parent;}
  remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(x=>x!==this);this.parentElement=null;}
  set innerHTML(value){this.html=value;for(const child of this.children)child.parentElement=null;this.children=[];}
  get innerHTML(){return this.html||'';}
  setAttribute(){}
  addEventListener(type,fn){const list=this.listeners.get(type)||[];list.push(fn);this.listeners.set(type,list);}
  removeEventListener(type,fn){this.listeners.set(type,(this.listeners.get(type)||[]).filter(x=>x!==fn));}
  emit(type,data={}){for(const fn of [...(this.listeners.get(type)||[])])fn(data);}
  querySelector(){return null;}
  showModal(){this.open=true;}
  close(){this.open=false;this.emit('close');}
 }
 const body=new Element('body'),side=new Element(),hud=new Element(),sheet=new Element('dialog'),html=new Element('html');html.dataset.layout='desktop';side.append(hud);body.append(side);body.append(sheet);
 const doc=new Element();Object.assign(doc,{body,head:new Element('head'),documentElement:html,hidden:false,activeElement:null,createElement:tag=>new Element(tag),getElementById:key=>({side,taskHUD:hud,sheet})[key]||null,querySelector:sel=>sel.startsWith('link')?{sheet:true}:null});
 globalThis.document=doc;globalThis.MutationObserver=class{constructor(fn){this.fn=fn;observers.push(this);}observe(){}disconnect(){}};
 globalThis.setTimeout=(fn,delay)=>{timers.set(++id,{fn,at:now+delay});return id;};globalThis.clearTimeout=key=>timers.delete(key);Date.now=()=>now;
 t.after(()=>{Object.assign(globalThis,{document:saved.document,MutationObserver:saved.MutationObserver,setTimeout:saved.setTimeout,clearTimeout:saved.clearTimeout});Date.now=saved.now;});
 const requests=[];let refreshes=0;
 const api=new Element();Object.assign(api,{account:{username:'owner'},state:{current:'tea'},json:async url=>{requests.push(url);return url.includes('/orders')?{incoming,outgoing}:{places:[{id:'career:owner:tea',kind:'career',target:'tea',name:'Tea'}]};},refresh:async()=>{refreshes++;}});
 const env={api,live:()=>null};const mod=await import(`../public/js/v4/workplace-visit.js?owner-test=${Math.random()}`);
 const flush=async()=>{for(let n=0;n<15;n++)await Promise.resolve();};
 const advance=async ms=>{const end=now+ms;while(true){const next=[...timers].sort((a,b)=>a[1].at-b[1].at)[0];if(!next||next[1].at>end)break;now=next[1].at;timers.delete(next[0]);await next[1].fn();await flush();}now=end;};
 mod.workVisitsBoot(env);await flush();
 return {mod,env,doc,body,side,hud,sheet,html,requests,flush,advance,refreshes:()=>refreshes,orders:()=>requests.filter(x=>x.includes('/orders')).length,places:()=>requests.filter(x=>x.includes('scope=mine')).length,mutate:()=>observers.forEach(o=>o.fn()),box:()=>[body,side,hud,sheet].flatMap(x=>x.children).find(x=>x.className==='wv-owner')};
}

test('owner control follows in-flow work surfaces across desktop, phone and career dialog',async t=>{
 const f=await fixture(t);const box=f.box();assert.equal(box.parentElement,f.side,'desktop owner belongs in the sidebar');
 f.html.dataset.layout='phone';f.mutate();const stack=f.hud.parentElement;assert.notEqual(stack,f.side,'compact HUD has a shared positioned container');assert.equal(box.parentElement,stack,'phone owner is in a dedicated row below task HUD');assert.deepEqual(stack.children,[f.hud,box]);
 f.hud.innerHTML='new task cards';f.mutate();assert.equal(box.parentElement,stack,'task rerender leaves presence row intact');
 f.sheet.open=true;f.mutate();assert.equal(box.parentElement,f.sheet,'open career sheet includes presence in normal flow');
 f.sheet.open=false;f.mutate();assert.equal(box.parentElement,stack);
 f.html.dataset.layout='desktop';f.mutate();assert.equal(box.parentElement,f.side);assert.equal(f.hud.parentElement,f.side,'desktop returns the untouched task HUD to the sidebar');
});
test('empty inbox polls every 30 seconds and unchanged workplaces every two minutes',async t=>{
 const f=await fixture(t);assert.equal(f.orders(),1);assert.equal(f.places(),1);
 await f.advance(25000);assert.equal(f.orders(),1,'idle users do not poll every five seconds');
 await f.advance(5000);assert.equal(f.orders(),2);
 await f.advance(90000);assert.equal(f.orders(),5);assert.equal(f.places(),2);
});
test('active incoming and outgoing services stay responsive without duplicate settlement refresh',async t=>{
 const f=await fixture(t,{incoming:[{id:'one',status:'accepted',price:10}]});await f.advance(10000);
 assert.equal(f.orders(),3);assert.equal(f.refreshes(),1);
});
test('buyer awaiting service also uses fast polling',async t=>{
 const f=await fixture(t,{outgoing:[{id:'two',status:'accepted',price:10}]});await f.advance(10000);assert.equal(f.orders(),3);
});
test('visitor inbox owns polling while open and resumes owner on close',async t=>{
 const f=await fixture(t);await f.mod.openWorkplaceVisit(f.env,{inbox:true});assert.equal(f.orders(),2);
 await f.advance(10000);assert.equal(f.orders(),4,'only the dialog polls while visiting');
 const dialog=f.body.children.find(x=>x.className==='wv-dialog');dialog.close();await f.flush();assert.equal(f.orders(),5,'close reconciles orders once');
});
test('hidden tabs and signed-out users do not request owner data',async t=>{
 const f=await fixture(t);f.doc.hidden=true;f.mod.workVisitsOwnerFocus(f.env);await f.flush();await f.advance(60000);assert.equal(f.requests.length,2);
 f.doc.hidden=false;f.env.api.account=null;await f.advance(60000);assert.equal(f.requests.length,2);
});
test('changing workplace bypasses the slow discovery interval',async t=>{
 const f=await fixture(t);f.env.api.state.current='nail';f.env.api.emit('state');await f.advance(5000);assert.equal(f.places(),2);
});
test('slow workplace discovery does not overlap refreshes or start orders after opening visitor inbox',async t=>{
 const f=await fixture(t),json=f.env.api.json;let release,discoveries=0;
 f.env.api.json=url=>url.includes('scope=mine')?(discoveries++,new Promise(resolve=>release=resolve)):json(url);
 f.mod.workVisitsOwnerFocus(f.env);f.mod.workVisitsOwnerFocus(f.env);await f.flush();assert.equal(discoveries,1);
 await f.mod.openWorkplaceVisit(f.env,{inbox:true});assert.equal(f.orders(),2);
 release({places:[]});await f.flush();assert.equal(f.orders(),2,'owner does not start another orders request after modal takes over');
});
test('failed order polling backs off and retries without request bursts',async t=>{
 const f=await fixture(t);let attempts=0;const json=f.env.api.json;
 f.env.api.json=async url=>{if(url.includes('/orders')){attempts++;throw Error('offline');}return json(url);};
 await f.advance(30000);assert.equal(attempts,1);
 await f.advance(25000);assert.equal(attempts,1);await f.advance(5000);assert.equal(attempts,2);
});
