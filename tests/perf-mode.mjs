// Unit test of public/js/perf-mode.js (⚡ light mode for slow devices) and the classic World's use of it.
// node tests/perf-mode.mjs; exits non-zero on failure. Each case imports a fresh copy (query string) with its own globals.
import assert from 'node:assert/strict';

let n=0;
async function fresh({search='',saved=null,memory}={}){
  const store=new Map(saved?[['mnl.perf',JSON.stringify(saved)]]:[]);
  globalThis.localStorage={getItem:k=>store.get(k)??null,setItem:(k,v)=>store.set(k,String(v))};
  globalThis.document={documentElement:{dataset:{}}};
  Object.defineProperty(globalThis,'location',{value:{search},configurable:true,writable:true});
  Object.defineProperty(globalThis,'navigator',{value:memory===undefined?{}:{deviceMemory:memory},configurable:true,writable:true});
  const m=await import(`../public/js/perf-mode.js?case=${++n}`);
  return {m,store,root:globalThis.document.documentElement};
}

{ // a fast device: off, nothing on <html>
  const {m,root}=await fresh({memory:8});
  assert.equal(m.lowEnd(),false);assert.equal(root.dataset.perf,undefined);
}
{ // measured slow: on, tells the scenes once, remembered for the next start
  const {m,store,root}=await fresh();
  let calls=0;const off=m.onLowEnd(()=>calls++);
  m.markLowEnd('classic');m.markLowEnd('iso');
  assert.equal(m.lowEnd(),true);assert.equal(calls,1);assert.equal(root.dataset.perf,'low');assert.equal(m.lowReason(),'classic');
  assert.equal(JSON.parse(store.get('mnl.perf')).low,true);off();
}
{ // remembered for 7 days, then measured again
  const {m}=await fresh({saved:{low:true,at:Date.now()-864e5,why:'iso'}});
  assert.equal(m.lowEnd(),true);assert.equal(m.lowReason(),'iso');
  const old=await fresh({saved:{low:true,at:Date.now()-8*864e5}});
  assert.equal(old.m.lowEnd(),false);
}
{ // ≤ 2 GB phones start light; ?perf= overrides both ways
  assert.equal((await fresh({memory:2})).m.lowEnd(),true);
  assert.equal((await fresh({memory:2,search:'?perf=full'})).m.lowEnd(),false);
  assert.equal((await fresh({memory:8,search:'?x=1&perf=low'})).m.lowEnd(),true);
}
{ // storage blocked: still works for the page
  globalThis.localStorage={getItem(){throw new Error('blocked');},setItem(){throw new Error('blocked');}};
  globalThis.document={documentElement:{dataset:{}}};globalThis.location.search='';globalThis.navigator={};
  const m=await import(`../public/js/perf-mode.js?case=${++n}`);
  assert.equal(m.lowEnd(),false);m.markLowEnd('classic');assert.equal(m.lowEnd(),true);
}
console.log('perf-mode ok');
