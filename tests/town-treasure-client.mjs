import assert from 'node:assert/strict';
import test from 'node:test';
import {createTreasureController} from '../public/js/isometric/treasure.js';
function harness(){
  const listeners=new Map(),sent=[],drawn=[],notices=[],writes=[],timers=new Map();let time=1000000,id=0;
  const doc={hidden:false,addEventListener(){},removeEventListener(){}};
  const socket={state:'open',flags:{treasure:true,town:true},on(t,f){listeners.set(t,f);return()=>listeners.delete(t);},send(f){sent.push(f);return true;}};
  const world={mode:'town',getPresence:()=>({x:4,y:5,direction:'se'}),setTreasure:v=>drawn.push(v)};
  const api={queue:Promise.resolve(),accepted:1,json:()=>new Promise(()=>{}),post:async(u,b)=>{writes.push([u,b]);return {state:{},revision:2,result:{message:'Nhặt được 10.000 xu'}};},retrying:async send=>send(),refresh:async()=>{api.refreshed=true;},accept:d=>api.saved=d};
  const c=createTreasureController(()=>({world,api,toast:t=>notices.push(t)}),{socket,document:doc,now:()=>time,setInterval:f=>{timers.set(++id,f);return id;},clearInterval:i=>timers.delete(i),setTimeout:f=>{timers.set(++id,f);return id;},clearTimeout:i=>timers.delete(i),uuid:()=> 'request-00001'});
  const wave={enabled:true,server_time:1000,wave:{id:'w1',expires_at:1600,reward:10000,notice:'Rương đã xuất hiện!'},chests:[{id:'c1',map_id:'iso-town-v1',x:4,y:5,claimed:false}]};
  return {c,api,socket,world,doc,sent,drawn,notices,writes,timers,wave,emit:(t,f)=>listeners.get(t)?.(f),advance:ms=>time+=ms};
}
test('bounded public snapshots, single wave notice, expiry and disabled cleanup',()=>{
  const h=harness();h.c.start();h.c.receive(h.wave);h.c.receive(h.wave);
  assert.equal(h.drawn.at(-1).length,1);assert.equal(h.notices.length,1);
  h.advance(600001);h.c.tick();assert.deepEqual(h.drawn.at(-1),[]);
  h.c.receive({...h.wave,enabled:false});assert.deepEqual(h.drawn.at(-1),[]);h.c.stop();assert.equal(h.timers.size,0);
});
test('collection publishes position and uses a server proof, never optimistic coins',async()=>{
  const h=harness();h.c.start();h.c.receive(h.wave);
  const claim=h.c.claim('c1');await Promise.resolve();assert.equal(h.sent.at(-2).t,'town_mv');assert.equal(h.sent.at(-1).t,'town_treasure_prepare');assert.equal(h.writes.length,0);
  h.emit('town_treasure_ready',{cid:'wrong',chest_id:'c1',proof:'ignore'});assert.equal(h.writes.length,0);
  h.emit('town_treasure_ready',{cid:h.sent.at(-1).cid,chest_id:'c1',proof:'signed',expires_at:1005});await claim;
  assert.equal(h.writes.length,1);assert.equal(h.writes[0][1].proof,'signed');assert.equal(h.api.saved.revision,2);h.c.stop();
});
test('distant, claimed and off-map treasure cannot start a claim; hidden stops requests',async()=>{
  const h=harness();h.c.start();h.c.receive({...h.wave,chests:[{...h.wave.chests[0],x:99}]});await h.c.claim('c1');assert.equal(h.sent.length,0);
  h.c.receive({...h.wave,chests:[{...h.wave.chests[0],claimed:true}]});assert.deepEqual(h.drawn.at(-1),[]);
  h.c.receive(h.wave);h.world.mode='work';await h.c.claim('c1');assert.equal(h.sent.length,0);h.c.stop();
});
test('disconnect rejects pending proof and clears stale chests',async()=>{
  const h=harness();h.c.start();h.c.receive(h.wave);const p=h.c.claim('c1');await Promise.resolve();h.emit('down',{});await p;
  assert.deepEqual(h.drawn.at(-1),[]);assert.equal(h.writes.length,0);h.c.stop();
});
test('proof is acquired after queued commands, using the current position',async()=>{
  const h=harness();let release;h.api.queue=new Promise(r=>{release=r;});h.c.start();h.c.receive(h.wave);
  const p=h.c.claim('c1');await Promise.resolve();assert.equal(h.sent.length,0);
  h.advance(6000);h.world.getPresence=()=>({x:4.2,y:5,direction:'ne'});release();await Promise.resolve();
  assert.equal(h.sent.at(-2).x,4.2);h.emit('town_treasure_ready',{cid:h.sent.at(-1).cid,chest_id:'c1',proof:'fresh'});await p;
  assert.equal(h.writes[0][1].proof,'fresh');h.c.stop();
});
test('late snapshots cannot revive claimed chests or roll back a newer wave',async()=>{
  const h=harness();h.c.start();await Promise.resolve();h.c.receive(h.wave);
  h.c.receive({...h.wave,server_time:1002,chests:[{...h.wave.chests[0],claimed:true}]});h.c.receive({...h.wave,server_time:1001});
  assert.equal(h.drawn.at(-1).length,0);
  h.c.receive({...h.wave,server_time:1003});assert.equal(h.drawn.at(-1).length,0);
  h.c.stop();
});
test('lost claim responses retry the same request and reconcile an uncertain wallet',async()=>{
  const h=harness();h.c.start();await Promise.resolve();h.c.receive(h.wave);let attempts=0;
  h.api.post=async(u,b)=>{h.writes.push([u,b]);if(!attempts++)throw new Error('connection lost');return {state:{coins:10000},revision:2};};
  h.api.retrying=async send=>{try{return await send();}catch{return send();}};
  const p=h.c.claim('c1');await Promise.resolve();h.emit('town_treasure_ready',{cid:h.sent.at(-1).cid,chest_id:'c1',proof:'stable'});await p;
  assert.equal(h.writes.length,2);assert.deepEqual(h.writes[0],h.writes[1]);assert.equal(h.api.saved.state.coins,10000);
  h.c.stop();
  const fail=harness();fail.c.start();await Promise.resolve();fail.c.receive(fail.wave);fail.api.post=async()=>{throw new Error('network');};
  const lost=fail.c.claim('c1');await Promise.resolve();fail.emit('town_treasure_ready',{cid:fail.sent.at(-1).cid,chest_id:'c1',proof:'unknown'});await lost;
  assert.equal(fail.api.refreshed,true);fail.c.stop();
});
