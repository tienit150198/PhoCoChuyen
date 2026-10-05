import assert from 'node:assert/strict';
import test from 'node:test';
import {judge, setup} from '../public/js/v4/fair-knife.js';

test('chance knives keep physical angles even when every impact overlaps an existing blade',()=>{
 const b={chance:true,need:7,pre:[90],th0:0,segs:[[60000,0,0]]};
 const result=judge(b,{impact:90,fly:80,gap:10},[0,120,240,360,480,600,720]);
 assert.equal(result.hit,-1);
 assert.equal(result.stuck.length,7);
 assert.deepEqual(result.stuck,Array(7).fill(90),'a stationary board keeps every impact at 90 degrees without predicting a loss');
});

test('legacy skill board still judges collisions',()=>{
 const b={need:7,pre:[90],th0:0,segs:[[60000,0,0]]};
 assert.equal(judge(b,{impact:90,fly:80,gap:10},[0]).hit,0);
});

test('chance UI waits for a server loss without celebrating locally',async()=>{
 const sounds=[],requests=[];
 let now=1000;
 const originals={performance:globalThis.performance,requestAnimationFrame:globalThis.requestAnimationFrame,
   cancelAnimationFrame:globalThis.cancelAnimationFrame,setTimeout:globalThis.setTimeout};
 globalThis.performance={now:()=>now};
 globalThis.requestAnimationFrame=()=>1;
 globalThis.cancelAnimationFrame=()=>{};
 globalThis.setTimeout=fn=>{queueMicrotask(fn);return 1;};
 try{
  let resolve;
  const pending=new Promise(r=>{resolve=r;});
  const run={stage:'play',id:'one',lv:1,el:0,tp:[],board:{chance:true,need:2,pre:[],th0:0,segs:[[60000,0,0]]}};
  const k={run,fly:80,gap:10,impact:90,min_tap:120,level_ms:60000};
  const state={tab:'dt',dlg:{open:true}};
  const ui=setup({S:state,F:()=>({knife:k,now:1}),serverNow:()=>1000,render:()=>{},sfx:s=>sounds.push(s),
   pick:a=>a[0],send:(name,payload)=>{requests.push({name,payload});return pending;}});
  ui.click('knthrow',{});now+=200;ui.click('knthrow',{});
  await new Promise(r=>queueMicrotask(r));
  assert.equal(requests.length,1);
  assert.ok(!sounds.includes('cap'));
  resolve({fair:{lost:true,lv:1,stuck:[0],run:{stake:5,gone:0}}});
  await new Promise(r=>originals.setTimeout(r,0));
  assert.ok(!sounds.includes('cap'));
  assert.equal(state.kn.last.kind,'lost');
 }finally{Object.assign(globalThis,originals);}
});
