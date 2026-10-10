import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {lookOf} from '../public/js/v4/look.js';
import {createLeisurePresence,publicActivity} from '../public/js/isometric/leisure-presence.js';

const source=readFileSync(new URL('../public/js/isometric-town.js',import.meta.url),'utf8')
  .replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
function harness(){
  let now=1000,id=0;const timers=new Map(),listeners=new Map(),events=new Map(),sent=[],drawn=[];
  const socket={state:'open',flags:{town:true,treasure:true},accept:true,
    on(type,fn){listeners.set(type,fn);return()=>listeners.delete(type);},
    send(frame){if(!this.accept||this.state!=='open')return false;sent.push(structuredClone(frame));return true;}};
  const target={addEventListener(type,fn){events.set(type,fn);},removeEventListener(type){events.delete(type);}};
  const doc={visibilityState:'visible',...target},leisure=createLeisurePresence();
  const state={journey:{gender:'female'},wardrobe:{look:{top:'ao_thun_kem'}}};
  const world={at:{x:6,y:6,direction:'se'},getPresence(){return this.at;},setRemotePlayers(peers){drawn.push(structuredClone(peers));}};
  const env={world,api:{state,live:{url:'/live'}}};
  const context=vm.createContext({lookOf,publicActivity,leisurePresence:leisure,live:socket,
    setInterval(fn){timers.set(++id,fn);return id;},clearInterval(key){timers.delete(key);},Date:{now:()=>now}});
  vm.runInContext(source+'\nglobalThis.create=createTownPresence;',context);
  const bridge=context.create(()=>env,{transport:socket,document:doc,events:target,leisure,now:()=>now,status(){}}).start();
  const emit=(type,frame)=>listeners.get(type)?.(frame);
  return {bridge,socket,state,world,doc,leisure,sent,drawn,timers,listeners,emit,
    joined(people=[]){emit('town_room',{map:'iso-town-v1',room:'r',me:'me',people,cid:sent.findLast(f=>f.t==='town_in')?.cid});},
    tick(ms=280){now+=ms;for(const fn of [...timers.values()])fn();}};
}

test('changing an outfit publishes it in the current room without a rejoin or idle traffic',t=>{
  const h=harness();h.joined();h.state.wardrobe.look.top='ao_so_mi';h.tick();
  const update=h.sent.at(-1);
  assert.equal(update.t,'town_mv','appearance refresh must keep the current room and treasure lease');
  assert.equal(update.look.top,'ao_so_mi');assert.equal(update.g,'female');
  assert.deepEqual([update.x,update.y,update.direction],[6,6,'se']);
  assert.equal(h.sent.filter(f=>f.t==='town_in').length,1);assert.equal(h.sent.some(f=>f.t==='town_out'),false);
  const count=h.sent.length;for(let i=0;i<300;i++)h.tick(100);
  assert.equal(h.sent.length,count);t.diagnostic('1 outfit change: 1 movement packet, 0 rejoins; 300 unchanged syncs: 0 packets');
  h.bridge.stop();
});

test('appearance shares the movement throttle, preserves activity and merges into peers',()=>{
  const h=harness();h.joined([{pid:'friend',name:'Lan',lk:{top:'ao_thun_kem'},g:'female',x:6,y:7,direction:'sw'}]);
  const activity={kind:'fishing',x:84,y:180,direction:'ne',phase:'walk',action:null,moving:false};
  h.leisure.publish(activity);h.state.wardrobe.look.top='ao_so_mi';h.world.at={x:6,y:6.1,direction:'ne'};
  h.tick(100);assert.equal(h.sent.length,1);
  h.state.wardrobe.look.top='ao_len';h.state.journey.gender='male';h.tick(180);
  const update=h.sent.at(-1);assert.equal(update.look.top,'ao_len');assert.equal(update.g,'male');
  assert.equal(update.x,6);assert.equal(update.y,6.1);assert.deepEqual(update.activity,activity);
  h.emit('town',{room:'r',ev:[{k:'mv',pid:'friend',x:6,y:7,direction:'sw',lk:update.look,g:update.g}]});
  const peer=h.drawn.at(-1)[0];assert.equal(peer.look.top,'ao_len');assert.equal(peer.gender,'male');assert.equal(peer.name,'Lan');
  h.emit('town',{room:'r',ev:[{k:'mv',pid:'friend',x:6,y:7.1,direction:'sw'}]});
  assert.equal(h.drawn.at(-1)[0].look.top,'ao_len','old movement packets retain the last outfit');
  assert.equal(h.drawn.at(-1)[0].gender,'male');
  h.world.at={x:6,y:6.2,direction:'ne'};h.tick();
  assert.equal(Object.hasOwn(h.sent.at(-1),'look'),false,'unchanged appearances do not repeat on movement');
  h.bridge.stop();
});

test('join races, hidden tabs and reconnect publish the latest outfit and clean up',()=>{
  const h=harness();h.state.wardrobe.look.top='ao_so_mi';h.tick();assert.equal(h.sent.length,1);
  h.joined();h.tick();assert.equal(h.sent.at(-1).look.top,'ao_so_mi');
  h.doc.visibilityState='hidden';h.tick();assert.equal(h.sent.at(-1).t,'town_out');
  h.state.wardrobe.look.top='ao_len';const hidden=h.sent.length;h.tick(2000);assert.equal(h.sent.length,hidden);
  h.doc.visibilityState='visible';h.tick();assert.equal(h.sent.at(-1).t,'town_in');assert.equal(h.sent.at(-1).look.top,'ao_len');h.joined();
  h.socket.state='down';h.emit('down',{});h.state.wardrobe.look.top='ao_thun_kem';const down=h.sent.length;h.tick();assert.equal(h.sent.length,down);
  h.socket.state='open';h.emit('welcome',{});assert.equal(h.sent.at(-1).look.top,'ao_thun_kem');h.joined();
  const resumed=h.sent.length;h.tick();assert.equal(h.sent.length,resumed);
  h.bridge.stop();assert.equal(h.timers.size,0);assert.equal(h.listeners.size,0);
});

test('failed sends retry the outfit and private state never produces appearance traffic',()=>{
  const h=harness();h.joined();h.socket.accept=false;h.state.wardrobe.look.top='ao_so_mi';h.tick();assert.equal(h.sent.length,1);
  h.socket.accept=true;h.tick();assert.equal(h.sent.at(-1).look.top,'ao_so_mi');
  const count=h.sent.length;h.state.journey.wallet=999;h.state.wardrobe.look.private='secret';h.tick();assert.equal(h.sent.length,count);
  assert.equal(JSON.stringify(h.sent).includes('secret'),false);h.bridge.stop();
});

test('a rejected movement carrying an outfit retries it without reopening the room',()=>{
  const h=harness();h.joined();h.state.wardrobe.look.top='ao_so_mi';h.tick();
  const count=h.sent.length;h.emit('error',{ref:'town_mv',code:'speed'});h.tick();
  assert.equal(h.sent.length,count+1);assert.equal(h.sent.at(-1).t,'town_mv');
  assert.equal(h.sent.at(-1).look.top,'ao_so_mi');
  assert.equal(h.sent.filter(f=>f.t==='town_in').length,1);h.bridge.stop();
});
