// Execute production scheduling/simulation boundaries without a GPU or browser.
import assert from 'node:assert/strict';
import {test} from 'node:test';
import fs from 'node:fs';
import vm from 'node:vm';

function browser(){
  const frames=new Map(),timers=new Map(),observers=[];let id=0,time=0;
  const element=()=>Object.assign(new EventTarget(),{isConnected:true,hidden:false,style:{setProperty(){}},classList:{toggle(){},remove(){}},setAttribute(){},remove(){this.isConnected=false;},querySelector(){return element();},querySelectorAll:()=>[],getClientRects:()=>[{}]});
  const dialog=element();dialog.open=true;const dialogs=[dialog],stage=element();stage.closest=()=>dialog.open?dialog:null;
  const document=Object.assign(new EventTarget(),{body:element(),hidden:false,querySelectorAll:()=>dialogs,querySelector:()=>dialog.open?{}:null});
  class MutationObserver {constructor(fn){this.fn=fn;observers.push(this);}observe(){this.active=true;}disconnect(){this.active=false;}}
  const b={document,stage,dialog,frames,timers,observers,MutationObserver,performance:{now:()=>time},
    requestAnimationFrame(fn){frames.set(++id,fn);return id;},cancelAnimationFrame(n){frames.delete(n);},
    setTimeout(fn){timers.set(++id,fn);return id;},clearTimeout(n){timers.delete(n);},
    cover(){dialogs.push({...element(),open:true});b.mutate();},uncover(){dialogs.pop();b.mutate();},
    mutate(){for(const o of observers)if(o.active)o.fn([{type:'attributes',attributeName:'open',target:dialog}]);},
    frame(){time+=16;const work=[...frames.values()];frames.clear();for(const fn of work)fn(time);},
    hidden(on){document.hidden=on;document.dispatchEvent(new Event('visibilitychange'));}};
  return b;
}
function engine(name,b,names,override=''){
  const source=fs.readFileSync(new URL('../public/js/careers/'+name,import.meta.url),'utf8').replace(/^import .*;\r?$/gm,'').replace(/^export \{.*;\r?$/gm,'').replace(/^export /gm,'');
  const sandbox={...b,console,window:new EventTarget(),performance:b.performance,needsDrivingFrames:()=>true,needsFarmFrames:w=>!!(w.auto||w.ride||w.keys.size),counters:{draw:0,step:0}};
  const helper=new URL('../public/js/careers/activity_visibility.js',import.meta.url);
  vm.createContext(sandbox);
  if(fs.existsSync(helper))vm.runInContext(fs.readFileSync(helper,'utf8').replace(/^export /gm,''),sandbox);
  vm.runInContext(source+'\n'+override+'\nglobalThis.engine={'+names+'};',sandbox);
  return {...sandbox.engine,counters:sandbox.counters};
}

test('covered delivery stops simulation and RAF without changing its route',()=>{
  const b=browser(),e=engine('delivery_drive.js',b,'S,frame,wake,live,syncVisibility,watchActivityVisibility,park',`ride=()=>counters.step++;moveTraffic=()=>{};draw=()=>counters.draw++;measure=()=>{};`);
  Object.assign(e.S,{el:b.stage,opts:{target:'school'},visible:true,w:800,view:'firstperson',last:0});
  e.S.visibilityCleanup=e.watchActivityVisibility(b.stage,e.syncVisibility);
  e.wake();b.frame();assert.equal(e.counters.step,1);
  b.cover();for(let i=0;i<120;i++)b.frame();
  assert.equal(e.counters.step,1,'a covering dialog must not drive or auto-arrive');
  assert.equal(b.frames.size,0,'covered driving has no RAF work');
  assert.equal(e.S.opts.target,'school');
  e.S.keys.u=true;b.uncover();assert.equal(b.frames.size,1,'uncover wakes the same mounted route');b.frame();assert.equal(e.counters.step,2);
  e.S.visible=false;e.syncVisibility();assert.equal(b.frames.size,0,'scrolled-away driving also stops simulation');assert.equal(e.S.keys.u,undefined);
  e.S.visible=true;e.syncVisibility();assert.equal(b.frames.size,1);
  e.park();assert.equal(b.frames.size,0);assert.equal(b.observers.filter(o=>o.active).length,0);b.mutate();assert.equal(b.frames.size,0);
});

test('covered farm suspends its route and hidden changes wait for a visible paint',()=>{
  const b=browser(),e=engine('farm_walk.js',b,'W,watchVisibility,loop,wake',`step=()=>counters.step++;draw=()=>counters.draw++;perf=()=>{};`);
  Object.assign(e.W,{el:b.stage,w:800,h:500,auto:{to:'P1',path:[{x:1,z:4}]}});
  e.watchVisibility();e.wake();b.frame();assert.equal(e.counters.step,1);
  b.cover();for(let i=0;i<120;i++)b.frame();
  assert.equal(e.counters.step,1,'a covered farm must retain the route without walking it');
  assert.equal(b.frames.size,0);assert.equal(e.W.auto.to,'P1');
  e.W.auto=null;e.wake();assert.equal(b.frames.size,0,'hidden state changes defer painting');
  b.uncover();assert.equal(b.frames.size,1,'closing the covering dialog paints deferred changes');
  b.frame();assert.equal(e.counters.draw,2);assert.equal(b.frames.size,0,'an unchanged garden returns to idle');
  b.dialog.open=false;b.dialog.dispatchEvent(new Event('close'));assert.equal(b.observers.filter(o=>o.active).length,0);
});

test('hidden flight releases RAF and pauses phase time until it becomes visible',()=>{
  const b=browser(),e=engine('pilot_fly.js',b,'F,S,frame,syncVisibility,watchActivityVisibility,close',`lessonTick=()=>{};draw=()=>counters.draw++;autopilot=()=>{};physics=()=>counters.step++;readInput=()=>{};talkTick=()=>{};thrHint=()=>null;tidy=()=>{};measure=()=>{};`);
  Object.assign(e.F,{el:b.stage,host:b.dialog,last:0,phase:'test',keys:new Set(['w'])});
  e.F.visibilityCleanup=e.watchActivityVisibility(b.stage,e.syncVisibility);
  e.frame(16);assert.equal(e.counters.step,1);
  b.hidden(true);for(let i=0;i<120;i++)b.frame();
  assert.equal(b.frames.size,0,'hidden flight must not keep scheduling empty frames');
  const paused=e.F.time;assert.equal(e.counters.step,1);
  b.hidden(false);assert.equal(b.frames.size,1,'visibility resumes a visible flight exactly once');
  e.syncVisibility();assert.equal(b.frames.size,1);b.frame();assert.equal(e.F.time,paused,'first resumed frame cannot catch up hidden time');
  e.close();assert.equal(b.frames.size,0);assert.equal(b.observers.filter(o=>o.active).length,0);b.hidden(true);b.hidden(false);assert.equal(b.frames.size,0);
});

test('activity visibility ignores ordinary scene DOM work and observes covering-dialog removal',()=>{
  const b=browser(),e=engine('delivery_drive.js',b,'activityVisible,watchActivityVisibility');let changes=0;
  const off=e.watchActivityVisibility(b.stage,()=>changes++),observer=b.observers[0];
  observer.fn([{type:'childList',addedNodes:[{nodeType:3},{nodeType:1,matches:()=>false,contains:()=>false,querySelector:()=>null}],removedNodes:[]}]);
  assert.equal(changes,0,'labels and ordinary scene descendants do not request another paint');
  b.cover();assert.equal(e.activityVisible(b.stage),false);assert.equal(changes,1);
  const covering={nodeType:1,matches:selector=>selector==='dialog'};
  observer.fn([{type:'childList',addedNodes:[],removedNodes:[covering]}]);assert.equal(changes,2,'removing a dialog rather than closing it still notifies');
  off();assert.equal(observer.active,false);
});

test('a covering dialog holds flight simulation and releases held controls',()=>{
  const b=browser(),e=engine('pilot_fly.js',b,'F,S,frame,syncVisibility',`lessonTick=()=>{};draw=()=>counters.draw++;autopilot=()=>{};physics=()=>counters.step++;readInput=()=>{};talkTick=()=>{};thrHint=()=>null;tidy=()=>{};measure=()=>{};`);
  Object.assign(e.F,{el:b.stage,host:b.dialog,last:0,phase:'test',keys:new Set(['w'])});
  e.frame(16);b.cover();e.syncVisibility();for(let i=0;i<120;i++)b.frame();
  assert.equal(e.counters.step,1,'covering the cockpit cannot advance or settle a flight');
  assert.equal(e.F.keys.size,0);assert.equal(b.frames.size,0);
  b.uncover();e.syncVisibility();b.frame();assert.equal(e.counters.step,2);
});

test('flight pause releases pointer ownership while retaining the selected throttle',()=>{
  const b=browser(),e=engine('pilot_fly.js',b,'F,S,yokeOn,throttleOn,pauseFlight');
  Object.assign(e.F,{el:b.stage,phase:'test',inputResets:[]});
  const yoke=new EventTarget(),throttle=new EventTarget();throttle.getBoundingClientRect=()=>({top:0,height:200});
  e.yokeOn(yoke);e.throttleOn(throttle);
  const pointer=(target,type,id,x=0,y=0)=>{const event=new Event(type);Object.assign(event,{pointerId:id,clientX:x,clientY:y});target.dispatchEvent(event);};
  pointer(yoke,'pointerdown',1);pointer(yoke,'pointermove',1,20,10);pointer(throttle,'pointerdown',2,0,70);
  const power=e.S.Tt;assert.ok(e.F.input.pad[0]>0);
  e.pauseFlight();assert.equal(e.F.input.pad,null);assert.equal(e.S.Tt,power,'pausing does not change the pilot-selected power');
  pointer(yoke,'pointerdown',3);pointer(yoke,'pointermove',3,-10,-15);assert.ok(e.F.input.pad[0]<0,'a fresh finger can own the yoke after a missing pointerup');
  pointer(throttle,'pointerdown',4,0,40);assert.ok(e.S.Tt>power,'a fresh finger can own the throttle after a missing pointerup');
});
