import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {createLeisurePresence,publicActivity} from '../public/js/isometric/leisure-presence.js';

function harness({state='open',flag=true,mode='town'}={}){
  const source=readFileSync(new URL('../public/js/isometric-town.js',import.meta.url),'utf8')
    .replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
  let now=1000,id=0;const timers=new Map(),listeners=new Map(),events=new Map(),sent=[],drawn=[];
  const live={state,flags:{town:flag},on(t,fn){listeners.set(t,fn);return()=>listeners.delete(t);},send(f){if(this.state!=='open')return false;sent.push(f);return true;}};
  const eventTarget={addEventListener(t,fn){events.set(t,fn);},removeEventListener(t){events.delete(t);}};
  const doc={visibilityState:'visible',...eventTarget};
  const world={mode,getPresence(){return this.mode==='town'?{x:6,y:6,direction:1,name:'Spoof',task:'private'}:null;},setRemotePlayers(p){drawn.push(p);}};
  const env={world,api:{state:{private:'secret',journey:{gender:'female'}}}};
  const context=vm.createContext({live,leisurePresence:createLeisurePresence(),publicActivity,lookOf:()=>({top:'ao_quen'}),console,document:doc,window:eventTarget,
    setInterval:(fn)=>{timers.set(++id,fn);return id;},clearInterval:i=>timers.delete(i),
    setTimeout:(fn)=>{timers.set(++id,fn);return id;},clearTimeout:i=>timers.delete(i),Date:{now:()=>now}});
  vm.runInContext(source+'\nglobalThis.factory=createTownPresence;',context);
  const bridge=context.factory(()=>env,{transport:live,document:doc,events:eventTarget,now:()=>now,status:()=>{}});
  bridge.start();
  return {bridge,live,world,sent,drawn,doc,emit:(t,f)=>listeners.get(t)?.(f),
    mode(m){world.mode=m;events.get('mnl:iso-mode')?.({detail:{mode:m}});},
    tick(ms=280){now+=ms;for(const fn of [...timers.values()])fn();}};
}
test('join sends only public look and canonical ground coordinates',()=>{
  const h=harness();assert.equal(h.sent[0].t,'town_in');assert.equal(h.sent[0].map,'iso-town-v1');
  assert.deepEqual(Object.keys(h.sent[0]).sort(),['cid','direction','g','look','map','t','x','y']);
  assert.equal(JSON.stringify(h.sent).includes('private'),false);assert.equal(JSON.stringify(h.sent).includes('Spoof'),false);
});
test('only real snapshot peers and diffs reach the renderer',()=>{
  const h=harness();h.emit('town_room',{map:'iso-town-v1',room:'iso-town-v1:1',me:'me',people:[{pid:'peer',name:'Lan',lk:{top:'ao_quen'},x:6,y:7,direction:1}]});
  assert.equal(h.drawn.at(-1)[0].pid,'peer');assert.equal(h.drawn.at(-1)[0].look.top,'ao_quen');
  h.emit('town',{room:'iso-town-v1:1',ev:[{k:'mv',pid:'peer',x:6,y:8,direction:-1},{k:'in',pid:'me',name:'Self',x:6,y:6}]});
  assert.equal(h.drawn.at(-1).length,1);assert.equal(h.drawn.at(-1)[0].y,8);
  h.emit('town',{room:'iso-town-v1:1',ev:[{k:'out',pid:'peer'}]});assert.equal(h.drawn.at(-1).length,0);
});
test('work and hidden tabs leave, visible town rejoins',()=>{
  const h=harness();h.emit('town_room',{map:'iso-town-v1',room:'r',me:'me',people:[]});
  h.mode('work');assert.equal(h.sent.at(-1).t,'town_out');assert.equal(h.drawn.at(-1).length,0);
  h.mode('town');assert.equal(h.sent.at(-1).t,'town_in');
  h.doc.visibilityState='hidden';h.bridge.sync();assert.equal(h.sent.at(-1).t,'town_out');
  h.doc.visibilityState='visible';h.bridge.sync();assert.equal(h.sent.at(-1).t,'town_in');
});
test('moves are throttled and do not keep sending unchanged positions',()=>{
  const h=harness();h.emit('town_room',{map:'iso-town-v1',room:'r',me:'me',people:[]});
  h.world.getPresence=()=>({x:6,y:7,direction:1});h.tick();assert.equal(h.sent.at(-1).t,'town_mv');
  const n=h.sent.length;h.tick();assert.equal(h.sent.length,n);
  h.world.getPresence=()=>({x:6,y:7.1,direction:1});h.tick(20);assert.equal(h.sent.length,n+1);
  h.world.getPresence=()=>({x:6,y:7.2,direction:1});h.tick(20);assert.equal(h.sent.length,n+1);
  h.tick(280);assert.equal(h.sent.length,n+2);
});
test('disabled feature, disconnect and second-tab takeover clear real peers',()=>{
  const off=harness({flag:false});assert.equal(off.sent.length,0);
  const h=harness();h.emit('town_room',{map:'iso-town-v1',room:'r',me:'me',people:[{pid:'p',name:'Lan',x:6,y:8}]});
  h.live.state='down';h.emit('down',{});assert.equal(h.drawn.at(-1).length,0);
  h.live.state='open';h.emit('welcome',{flags:{town:true}});assert.equal(h.sent.at(-1).t,'town_in');
  h.emit('town_left',{why:'other'});const n=h.sent.length;h.tick(2000);assert.equal(h.sent.length,n);
});
test('late room after entering work is immediately left',()=>{
  const h=harness();h.mode('work');const n=h.sent.length;
  h.emit('town_room',{map:'iso-town-v1',room:'r',me:'me',people:[{pid:'p',x:6,y:8}]});
  assert.equal(h.sent.length,n+1);assert.equal(h.sent.at(-1).t,'town_out');assert.equal(h.drawn.at(-1).length,0);
});
