import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {createLeisurePresence,publicActivity} from '../public/js/isometric/leisure-presence.js';

const pose=(fields={})=>({kind:'fishing',x:84,y:180,direction:'ne',phase:'walk',action:null,moving:false,...fields});
const peer=(pid,activity)=>({pid,name:pid,lk:{top:'ao_quen'},g:'female',fc:'',x:6,y:6,direction:'se',...(activity?{activity}:{})});
function harness(){
  let now=1000,id=0;const listeners=new Map(),timers=new Map(),events=new Map(),sent=[],drawn=[];
  const leisure=createLeisurePresence();
  const socket={state:'open',flags:{town:true},on(t,fn){listeners.set(t,fn);return()=>listeners.delete(t);},send(frame){sent.push(frame);return this.state==='open';}};
  const target={addEventListener(t,fn){events.set(t,fn);},removeEventListener(t){events.delete(t);}};
  const document={visibilityState:'visible',...target};
  const world={at:{x:6,y:6,direction:'se'},getPresence(){return this.at;},setRemotePlayers(peers){drawn.push(peers);}};
  const source=readFileSync(new URL('../public/js/isometric-town.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
  const context=vm.createContext({live:socket,leisurePresence:leisure,publicActivity,lookOf:()=>({}),setInterval(fn){timers.set(++id,fn);return id;},clearInterval(i){timers.delete(i);},Date:{now:()=>now}});
  vm.runInContext(source+'\nglobalThis.factory=createTownPresence;',context);
  const bridge=context.factory({world,api:{state:{}}},{transport:socket,leisure,document,events:target,now:()=>now,status:()=>{}}).start();
  return {bridge,leisure,socket,sent,drawn,document,world,emit:(t,f)=>listeners.get(t)?.(f),
    join(people=[]){this.emit('town_room',{map:'iso-town-v1',room:'r',me:'me',people});},
    tick(ms=280){now+=ms;for(const fn of timers.values())fn();}};
}

test('public sample strips private state and serializes only allowed action kind',()=>{
  assert.deepEqual(publicActivity(pose({x:84.1234,action:{kind:'cast',at:5,duration:700,from:[1,2]},round:{id:'secret'},stats:{fish:999},rewards:99})),pose({x:84.12,action:'cast'}));
  for(const value of [pose({x:NaN}),pose({y:201}),pose({direction:'up'}),pose({kind:'work'}),pose({kind:['fishing']}),pose({phase:'boat'}),pose({action:'reward'})])assert.equal(publicActivity(value),null);
});

test('activity bridge is a local channel with matching subscriptions and idempotent publishing',()=>{
  const bridge=createLeisurePresence(),changes=[],seen=[];
  const off=bridge.observeLocal(sample=>changes.push(sample));
  assert.equal(bridge.publish(pose()),true);assert.equal(bridge.publish(pose()),true);
  assert.equal(changes.length,1);assert.deepEqual(bridge.current,pose());
  const unsubscribe=bridge.subscribe('fishing',peers=>seen.push(peers));
  bridge.updatePeers([peer('fisher',pose()),peer('swimmer',pose({kind:'pool'})),peer('walker')]);
  assert.equal(seen.at(-1).length,1);assert.equal(seen.at(-1)[0].pid,'fisher');
  bridge.clear();assert.equal(bridge.current,null);assert.equal(changes.length,2);
  bridge.updatePeers([]);assert.equal(seen.at(-1).length,0);
  off();unsubscribe();bridge.publish(pose());assert.equal(changes.length,2);
});

test('shared transport keeps all peers for leisure but removes outdoor people from town drawing',()=>{
  const h=harness(),seen=[];h.leisure.subscribe('fishing',peers=>seen.push(peers));
  h.join([peer('walker'),peer('fisher',pose()),peer('swimmer',pose({kind:'pool'}))]);
  assert.equal(h.drawn.at(-1).length,1);assert.equal(h.drawn.at(-1)[0].pid,'walker');
  assert.equal(seen.at(-1).length,1);assert.equal(seen.at(-1)[0].pid,'fisher');
  h.emit('town',{room:'r',ev:[{k:'mv',pid:'walker',x:6,y:6,activity:pose()}]});
  assert.equal(h.drawn.at(-1).length,0);assert.equal(seen.at(-1).length,2);
  h.emit('town',{room:'r',ev:[{k:'mv',pid:'fisher',x:6,y:6,activity:null}]});
  assert.equal(h.drawn.at(-1)[0].pid,'fisher');assert.equal(seen.at(-1).length,1);
  h.emit('town',{room:'r',ev:[{k:'out',pid:'walker'}]});assert.equal(seen.at(-1).length,0);
});

test('local activity shares the town update throttle, deduplicates and clears on close',()=>{
  const h=harness();h.join();h.leisure.publish(pose({round:{id:'private'},action:{kind:'cast',at:1}}));
  assert.equal(h.sent.length,1);h.tick();assert.equal(h.sent.at(-1).t,'town_mv');
  assert.equal(h.sent.at(-1).activity.action,'cast');assert.equal(JSON.stringify(h.sent).includes('private'),false);
  const n=h.sent.length;h.leisure.publish(pose({action:'cast'}));h.tick();assert.equal(h.sent.length,n);
  h.world.at.y=6.1;h.leisure.publish(pose({x:85}));const moved=h.sent.length;
  h.leisure.publish(pose({x:86}));h.tick(20);assert.equal(h.sent.length,moved);
  h.tick(270);assert.equal(h.sent.at(-1).activity.x,86);assert.equal(h.sent.at(-1).y,6.1);
  h.leisure.clear();h.tick();assert.equal(h.sent.at(-1).activity,null);
});

test('outdoor overlay can retain the town anchor and reconnect with current pose',()=>{
  const h=harness();h.join();h.leisure.publish(pose());h.world.at=null;h.tick();
  assert.equal(h.sent.at(-1).t,'town_mv');assert.equal(h.sent.at(-1).x,6);
  h.socket.state='down';h.emit('down',{});h.socket.state='open';h.emit('welcome',{});
  assert.equal(h.sent.at(-1).t,'town_in');assert.equal(h.sent.at(-1).activity.kind,'fishing');
  h.leisure.clear();assert.equal(h.sent.at(-1).t,'town_out');
});

test('closing and reopening before the send interval still publishes an explicit activity exit',()=>{
  const h=harness();h.join();h.leisure.publish(pose({kind:'boat',phase:'boat',x:270,y:50}));h.tick();
  h.leisure.clear();h.leisure.publish(pose({kind:'boat'}));h.tick();
  assert.equal(h.sent.at(-1).activity,null,'clear cannot be coalesced away by a new session');
  h.tick();assert.equal(h.sent.at(-1).activity.x,84);assert.equal(h.sent.at(-1).activity.phase,'walk');
});

test('hidden tabs, disconnect and takeover clear activity subscribers',()=>{
  const h=harness(),seen=[];h.leisure.subscribe('fishing',peers=>seen.push(peers));h.join([peer('p',pose())]);
  h.document.visibilityState='hidden';h.bridge.sync();assert.equal(seen.at(-1).length,0);
  h.document.visibilityState='visible';h.bridge.sync();h.join([peer('p',pose())]);
  h.emit('down',{});assert.equal(seen.at(-1).length,0);
  h.emit('welcome',{});h.join([peer('p',pose())]);h.emit('town_left',{why:'other'});assert.equal(seen.at(-1).length,0);
  const n=h.sent.length;h.leisure.publish(pose());h.tick(2000);assert.equal(h.sent.length,n);
});
