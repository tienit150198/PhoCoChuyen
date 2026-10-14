import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {createSharedIslandSession} from '../public/js/shared-island.js';
import {createTreasureController} from '../public/js/isometric/treasure.js';
import {createLeisurePresence,publicActivity} from '../public/js/isometric/leisure-presence.js';

const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
function harness({load,ready=Promise.resolve(),paused=false}={}){
  const calls=[],api=new EventTarget(),view={canvas:{},open:()=>calls.push('open'),destroy:()=>calls.push('view.destroy'),ready:()=>calls.push('ready'),status(){},notice:text=>calls.push(['notice',text]),onClose(fn){this.close=fn;},onCamera(fn){this.camera=fn;}};
  api.state={settings:{newInterface:false},current:'mother_baby',journey:{wallet:300}};api.content={catalogue:[]};
  const main={paused,wake:()=>calls.push('main.wake')},env={api,world:main,closeSheet:()=>calls.push('closeSheet'),toast:text=>calls.push(['toast',text]),act:action=>calls.push(action)};
  let world,peerEnv,treasureEnv,interact;
  class World {constructor(_canvas,callback){world=this;interact=callback;this.ready=ready;this.mode='town';}
    update(state,content){calls.push(['update',state,content]);} resize(){calls.push('resize');} destroy(){calls.push('world.destroy');}
    recenter(){calls.push('recenter');} zoomBy(v){calls.push(['zoom',v]);} setMovementInput(x,y){calls.push(['move',x,y]);}}
  const runtime={World,createPresence(getEnv,options){peerEnv=getEnv;calls.push('presence.create');return {start(){calls.push('presence.start');return this;},stop(){calls.push('presence.stop');},sync(){calls.push('presence.sync');}};},
    createTreasure(getEnv){treasureEnv=getEnv;calls.push('treasure.create');return {start(){calls.push('treasure.start');return this;},stop(){calls.push('treasure.stop');},claim:id=>calls.push(['claim',id])};},
    attachInput(v,w){assert.equal(v,view);assert.equal(w,world);return {destroy:()=>calls.push('input.destroy')};}};
  const session=createSharedIslandSession(env,{view,loadRuntime:()=>load||Promise.resolve(runtime),onClose:()=>calls.push('closed')});
  return {session,calls,env,view,runtime,get world(){return world;},get peerEnv(){return peerEnv?.();},get treasureEnv(){return treasureEnv?.();},interact:id=>interact(id)};
}
await test('classic opens the same island protocols, updates fresh state, and restores the paused workplace',async()=>{
  const h=harness(),start=h.session.start();assert.equal(h.env.world.paused,true);await start;
  assert.equal(h.peerEnv.world,h.world);assert.equal(h.treasureEnv.world,h.world);assert.equal(h.peerEnv.api,h.env.api);
  assert.deepEqual(h.env.api.state.settings,{newInterface:false});assert.equal(h.env.api.state.current,'mother_baby');
  h.interact('treasure:shared-oldest-id');assert.deepEqual(h.calls.at(-1),['claim','shared-oldest-id']);
  h.interact('career:pharmacy');assert.equal(h.calls.filter(c=>Array.isArray(c)&&c[0]==='claim').length,1);
  h.view.camera('in');assert.deepEqual(h.calls.at(-1),['zoom',1.25]);h.view.camera('me');assert.equal(h.calls.at(-1),'recenter');
  h.env.api.state={...h.env.api.state,journey:{wallet:10300}};h.env.api.dispatchEvent(new Event('state'));
  assert.ok(h.calls.some(c=>Array.isArray(c)&&c[0]==='update'&&c[1].journey.wallet===10300));
  h.session.close();h.session.close();assert.equal(h.env.world.paused,false);
  for(const event of ['presence.stop','treasure.stop','world.destroy','input.destroy','view.destroy','closed'])assert.equal(h.calls.filter(c=>c===event).length,1,event+' exactly once');
  const count=h.calls.length;h.env.api.dispatchEvent(new Event('state'));assert.equal(h.calls.length,count,'state listener removed');
  assert.equal(h.env.api.state.settings.newInterface,false);
});
await test('closing while the engine downloads cannot mount a late world',async()=>{
  const pending=deferred(),h=harness({load:pending.promise,paused:true}),start=h.session.start();h.session.close();pending.resolve(h.runtime);await start;
  assert.equal(h.world,undefined);assert.equal(h.env.world.paused,true);assert.ok(!h.calls.includes('presence.start'));
});
await test('closing during scene boot releases the engine immediately and starts no controllers',async()=>{
  const pending=deferred(),h=harness({ready:pending.promise}),start=h.session.start();await Promise.resolve();h.session.close();await start;
  pending.resolve();assert.equal(h.calls.filter(c=>c==='world.destroy').length,1);assert.ok(!h.calls.includes('presence.start'));assert.equal(h.env.world.paused,false);
});
await test('load failure and a later jail state leave no island listeners or paused classic game',async()=>{
  const failed=harness({load:Promise.reject(new Error('load failed'))});await failed.session.start();assert.equal(failed.env.world.paused,false);assert.ok(failed.calls.includes('closed'));
  const h=harness();await h.session.start();h.env.api.state={...h.env.api.state,jail:{id:'camp'}};h.env.api.dispatchEvent(new Event('state'));assert.equal(h.env.world.paused,false);assert.ok(h.calls.includes('world.destroy'));
});
await test('classic entry routes load shared island lazily and do not save a renderer preference',()=>{
  const app=readFileSync('public/js/app.js','utf8'),town=readFileSync('public/js/v4/town-walk.js','utf8'),source=readFileSync('public/js/shared-island.js','utf8');
  assert.match(app,/\['sharedIsland','map','Ra đảo nhặt rương'\]/);assert.match(app,/import\('\.\/shared-island\.js'\)/);
  assert.match(town,/data-action="sharedIsland"/);assert.match(source,/createTownPresence/);assert.match(source,/createTreasureController/);
  assert.doesNotMatch(source,/saveInterface|newInterface\s*[:=]\s*true|location\.reload/);
});
await test('classic island uses the real shared room and server-proof chest claim without optimistic currency',async()=>{
  const h=harness(),listeners=new Map(),sent=[],writes=[],timers=new Map();let serial=0;
  const socket={state:'open',flags:{town:true,treasure:true},on(name,fn){if(!listeners.has(name))listeners.set(name,new Set());listeners.get(name).add(fn);return()=>listeners.get(name)?.delete(fn);},send(frame){sent.push(frame);return true;}};
  const emit=(name,value)=>{for(const fn of [...(listeners.get(name)||[])])fn(value);};
  const doc=new EventTarget();Object.assign(doc,{visibilityState:'visible',hidden:false});const events=new EventTarget();
  const clock={setInterval:fn=>{timers.set(++serial,fn);return serial;},clearInterval:id=>timers.delete(id),setTimeout:fn=>{timers.set(++serial,fn);return serial;},clearTimeout:id=>timers.delete(id)};
  const source=readFileSync('public/js/isometric-town.js','utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
  const context=vm.createContext({live:socket,leisurePresence:createLeisurePresence(),publicActivity,lookOf:()=>({top:'ao_so_mi'}),console,document:doc,window:events,...clock,Date:{now:()=>1000000}});
  vm.runInContext(source+'\nglobalThis.factory=createTownPresence;',context);
  Object.assign(h.env.api,{live:{url:'/live'},queue:Promise.resolve(),accepted:1,json:()=>new Promise(()=>{}),retrying:async send=>send(),refresh:async()=>{},
    post:async(url,body)=>{writes.push({url,body});return {state:{...h.env.api.state,journey:{wallet:10300}},revision:2,result:{message:'Bạn nhận được 10.000 xu!'}};},
    accept(result){this.state=result.state;this.dispatchEvent(new Event('state'));}});
  const Base=h.runtime.World;
  h.runtime.World=class extends Base {getPresence(){return this.at||{x:4,y:5,direction:'se'};} correctPresence(at){this.at={...at,direction:'se'};} setRemotePlayers(peers){this.peers=peers;} setTreasure(chests){this.chests=chests;}};
  h.runtime.createPresence=(getEnv,options)=>context.factory(getEnv,{...options,transport:socket,document:doc,events,now:()=>1000000});
  h.runtime.createTreasure=getEnv=>createTreasureController(getEnv,{socket,document:doc,now:()=>1000000,...clock,uuid:()=> 'shared-classic-claim'});
  await h.session.start();assert.equal(sent[0].t,'town_in');assert.equal(sent[0].map,'iso-town-v1');
  emit('town_room',{cid:sent[0].cid,map:'iso-town-v1',room:'island-room',me:'me',x:4,y:5,people:[{pid:'new-interface-peer',name:'Lan',x:4.3,y:5,direction:'sw'}]});
  assert.equal(h.world.peers[0].pid,'new-interface-peer','classic sees the same real island peers');
  emit('town_treasure',{enabled:true,server_time:1000,wave:{id:'wave-1',starts_at:900,next_at:1500},chests:[{id:'same-server-chest',map_id:'iso-town-v1',x:4,y:5,count:3,claimed:false}]});
  assert.equal(h.world.chests[0].count,3);h.interact('treasure:same-server-chest');await Promise.resolve();await Promise.resolve();
  assert.equal(sent.at(-1).t,'town_treasure_prepare');assert.equal(sent.at(-1).chest_id,'same-server-chest');assert.equal(writes.length,0);assert.equal(h.env.api.state.journey.wallet,300);
  emit('town_treasure_ready',{cid:sent.at(-1).cid,chest_id:'same-server-chest',proof:'server-proof'});await h.env.api.queue;
  assert.equal(writes.length,1);assert.equal(writes[0].url,'/api/town/treasure/claim');assert.equal(writes[0].body.proof,'server-proof');assert.equal(h.env.api.state.journey.wallet,10300);assert.equal(h.env.api.state.settings.newInterface,false);
  h.session.close();assert.equal(sent.at(-1).t,'town_out');assert.equal(timers.size,0);assert.ok([...listeners.values()].every(set=>set.size===0),'closing removes both protocols subscriptions');
});

await test('F#381: a screen-reader list names every chest nearest first and its button walks there and picks it',async()=>{
  const h=harness(),rows=[];let pick;
  Object.assign(h.view,{chests:r=>rows.push(r),onChest:fn=>{pick=fn;}});
  const Base=h.runtime.World,gone=[];
  h.runtime.World=class extends Base {
    constructor(...args){super(...args);this.hotspots=[{id:'career:x',x:0,y:0},{id:'treasure:far',x:14,y:5},{id:'treasure:near',x:6,y:5}];this.treasure=[{id:'far',x:14,y:5},{id:'near',x:6,y:5,count:3}];}
    getPresence(){return {x:4,y:5,direction:'se'};}
    go(id,cb){h.calls.push(['go',id]);cb();}};
  await h.session.start();
  assert.deepEqual(rows.at(-1),[{id:'near',count:3,steps:2},{id:'far',count:1,steps:10}],'only chests, nearest first, stacked count kept');
  pick('near');assert.deepEqual(h.calls.slice(-3),[['notice','Đang đi tới rương, khoảng 2 bước…'],['go','treasure:near'],['claim','near']]);
  h.world.hotspots=h.world.hotspots.filter(x=>x.id!=='treasure:near');pick('near');
  assert.deepEqual(h.calls.at(-1),['notice','Rương này đã được nhặt. Danh sách đã cập nhật.']);assert.deepEqual(rows.at(-1).map(r=>r.id),['far']);
  h.session.close();const n=rows.length;await new Promise(r=>setTimeout(r,1100));assert.equal(rows.length,n,'the list timer stops on close');
});
await test('F#381: older views and worlds without the list keep working',async()=>{
  const h=harness();await h.session.start();h.interact('treasure:a');assert.deepEqual(h.calls.at(-1),['claim','a']);h.session.close();
});
