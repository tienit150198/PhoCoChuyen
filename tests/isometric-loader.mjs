import assert from 'node:assert/strict';
import test from 'node:test';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

function harness(){
  const timers=new Map(),calls=[],instances=[];let seq=0;
  const note={classList:{add(){}},setAttribute(){},remove(){calls.push('remove');},querySelector(){return {addEventListener(){}};}};
  const source=readFileSync(new URL('../public/js/iso-boot.js',import.meta.url),'utf8')
    .replace(/^import .*\r?\n/gm,'').replace(/^export \{.*\};\r?\n/gm,'').replace(/^export /gm,'')
    .replace("import('./isometric/phaser-world.js')",'Promise.resolve({PhaserWorld:FakeWorld})');
  const context=vm.createContext({Promise,console:{warn(){}},location:{reload(){}},
    FakeWorld:class {constructor(){this.ready=new Promise((resolve,reject)=>{this.resolve=resolve;this.reject=reject;});instances.push(this);}destroy(){calls.push('destroy');}},
    document:{getElementById:id=>id==='stage'?{append(){}}:{},createElement:()=>note},
    attachGuide:()=>calls.push('guide'),attachTreasure:()=>calls.push('treasure'),requestAnimationFrame:fn=>fn(),
    setTimeout:(fn,ms)=>{timers.set(++seq,{fn,ms});return seq;},clearTimeout:id=>timers.delete(id)});
  vm.runInContext(source+'\nup=true;globalThis.startWorld=start;',context);
  context.startWorld({env:()=>({}),world:{adopt:()=>calls.push('adopt')},interact(){},renderMain:()=>calls.push('render')});
  const run=ms=>{const entry=[...timers].find(([,t])=>t.ms===ms);assert.ok(entry);timers.delete(entry[0]);entry[1].fn();};
  return {calls,instances,note,run,timers};
}
const flush=async()=>{for(let i=0;i<10;i++)await Promise.resolve();};

test('loader keeps its message and proxy until the scene is ready',async()=>{
  const h=harness();h.run(0);await flush();
  assert.equal(h.instances.length,1);assert.deepEqual(h.calls,[]);
  h.instances[0].resolve();await flush();
  assert.deepEqual(h.calls,['adopt','render','guide','treasure','remove']);assert.equal(h.timers.size,0);
});
test('failed scene is disposed and retried instead of hiding the loading message',async()=>{
  const h=harness();h.run(0);await flush();h.instances[0].reject(new Error('scene failed'));await flush();
  assert.deepEqual(h.calls,['destroy']);h.run(1500);await flush();
  h.instances[1].resolve();await flush();assert.deepEqual(h.calls,['destroy','adopt','render','guide','treasure','remove']);
});
test('a scene that never boots times out with a recoverable retry',async()=>{
  const h=harness();h.run(0);await flush();h.run(20000);await flush();
  assert.deepEqual(h.calls,['destroy']);assert.ok([...h.timers.values()].some(t=>t.ms===1500));
});
