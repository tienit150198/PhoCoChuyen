import assert from 'node:assert/strict';
import * as telemetry from '../public/js/telemetry.js';

assert.equal(typeof telemetry.createClientPerformance,'function','sampled client performance collection must be available');
const {createClientPerformance}=telemetry;
const phase=(api,detail)=>api.dispatchEvent(Object.assign(new Event('clientperf'),{detail}));
function observers(types=['longtask','event']){
  const instances=[];
  class Observer{
    static supportedEntryTypes=types;
    constructor(callback){this.callback=callback;this.records=[];this.disconnected=false;instances.push(this);}
    observe(options){this.options=options;}
    disconnect(){this.disconnected=true;}
    takeRecords(){return this.records.splice(0);}
    emit(entries){this.callback({getEntries:()=>entries});}
  }
  return {Observer,instances};
}

{ // The other 90% of pages incur no observer, event listener or API timing work.
  const api=new EventTarget(),{Observer,instances}=observers();
  let listens=0;api.addEventListener=()=>listens++;
  const perf=createClientPerformance(api,{random:()=>.1,Observer});
  assert.equal(api.perfEnabled,false);
  assert.equal(listens,0);assert.equal(instances.length,0);assert.equal(perf.take(),null);
}
{ // Fixed numeric fields only: never retain a response, route, target or player-entered text.
  const api=new EventTarget(),{Observer,instances}=observers();
  const perf=createClientPerformance(api,{random:()=>.099,Observer});
  assert.equal(api.perfEnabled,true);
  phase(api,{parse:1.4,apply:4,render:8,text:'private',route:'/secret?q=private'});
  phase(api,{parse:2.8,apply:-3,render:Infinity});
  phase(api,{parse:'5',apply:null,render:NaN});
  assert.deepEqual(perf.take(),{parse:{n:2,total:4,max:3},apply:{n:1,total:4,max:4},render:{n:1,total:8,max:8}});
  assert.equal(perf.take(),null,'each beacon drains only new samples');
  perf.stop();assert.equal(api.perfEnabled,false);
  assert.ok(instances.every(x=>x.disconnected));
  phase(api,{parse:99});assert.equal(perf.take(),null);
}
{ // One slow interaction can have multiple event entries: keep its longest duration only.
  const api=new EventTarget(),{Observer,instances}=observers();
  const perf=createClientPerformance(api,{random:()=>0,Observer});
  const long=instances.find(x=>x.options.type==='longtask'),event=instances.find(x=>x.options.type==='event');
  assert.deepEqual(long.options,{type:'longtask',buffered:true});
  assert.deepEqual(event.options,{type:'event',buffered:true,durationThreshold:40});
  const entry=(duration,interactionId)=>({duration,interactionId,get target(){throw Error('must not inspect target');},get name(){throw Error('must not inspect name');}});
  long.emit([entry(65),entry(110),entry(NaN),entry(-1)]);
  event.emit([entry(56,1),entry(80,1),entry(48,2),entry(40,0),entry(8,3)]);
  event.records.push(entry(96,2));
  assert.deepEqual(perf.take(),{longtask:{n:2,total:175,max:110},interaction:{n:2,total:176,max:96}});
  event.emit([entry(120,2),entry(64,4)]);
  assert.deepEqual(perf.take(),{interaction:{n:1,total:64,max:64}},'an interaction already sent is not counted twice');
  perf.stop();
}
{ // A long-lived tab has bounded sample work, values and payload, including after a drain.
  const api=new EventTarget(),{Observer,instances}=observers();
  const perf=createClientPerformance(api,{random:()=>0,Observer});
  const long=instances.find(x=>x.options.type==='longtask'),event=instances.find(x=>x.options.type==='event');
  for(let i=0;i<500;i++)phase(api,{parse:70000,apply:2,render:3});
  long.emit(Array.from({length:500},()=>({duration:70000})));
  event.emit(Array.from({length:500},(_,i)=>({duration:40,interactionId:i+1})));
  const values=perf.take();
  assert.deepEqual(values.parse,{n:200,total:12000000,max:60000});
  assert.equal(values.apply.n,200);assert.equal(values.render.n,200);
  assert.equal(values.longtask.n,200);assert.equal(values.interaction.n,200);
  assert.equal(api.perfEnabled,false);assert.ok(instances.every(x=>x.disconnected));
  assert.ok(JSON.stringify(values).length<600);
  phase(api,{parse:1});long.emit([{duration:100}]);event.emit([{duration:40,interactionId:9999}]);
  assert.equal(perf.take(),null,'sample caps apply to the entire page, not just one beacon');
}
{ // Unsupported/partially supported browser performance APIs must never break gameplay.
  for(const Observer of [null,class {static supportedEntryTypes=['longtask','event'];constructor(){throw Error('unsupported');}},class {static supportedEntryTypes=[];}]){
    const api=new EventTarget(),perf=createClientPerformance(api,{random:()=>0,Observer});
    phase(api,{apply:3});assert.deepEqual(perf.take(),{apply:{n:1,total:3,max:3}});perf.stop();
  }
}
{ // Entries without an interaction ID still consume the native observer's work budget.
  const api=new EventTarget(),{Observer,instances}=observers(['event']);
  const perf=createClientPerformance(api,{random:()=>0,Observer});
  instances[0].emit(Array.from({length:250},()=>({duration:80,interactionId:0})));
  assert.equal(instances[0].disconnected,true);
  assert.equal(perf.take(),null);perf.stop();
}

{ // Integration: performance is sent only by the existing load/leave beacons.
  const sent=[],timers=[],win=new EventTarget(),doc=new EventTarget(),{Observer,instances}=observers();
  for(const k of ['addEventListener','removeEventListener','dispatchEvent'])globalThis[k]=win[k].bind(win);
  globalThis.window=globalThis;
  Object.assign(doc,{readyState:'complete',visibilityState:'visible',referrer:'',getElementById:()=>null,querySelector:()=>null,querySelectorAll:()=>[]});
  globalThis.document=doc;
  globalThis.location={origin:'https://example.com',href:'https://example.com/',search:''};
  const storage=()=>({getItem:()=>null,setItem(){}});globalThis.localStorage=storage();globalThis.sessionStorage=storage();
  Object.defineProperty(globalThis,'navigator',{value:{sendBeacon:(url,data)=>{sent.push(JSON.parse(data));return true;}},configurable:true});
  Object.defineProperty(globalThis,'performance',{value:{now:()=>1000,getEntriesByType:()=>[],getEntriesByName:()=>[]},configurable:true});
  globalThis.PerformanceObserver=Observer;
  Math.random=()=>0;globalThis.setTimeout=(fn,ms)=>{timers.push({fn,ms});return timers.length;};globalThis.clearTimeout=()=>{};
  const api=new EventTarget();telemetry.telemetryBoot({api,ui:{view:'job'}});
  phase(api,{parse:12});assert.equal(sent.length,0);
  assert.deepEqual(timers.map(x=>x.ms),[1500],'performance collection adds no timer');
  timers[0].fn();assert.deepEqual(sent[0].load.perf,{parse:{n:1,total:12,max:12}});
  phase(api,{apply:7,render:19});
  win.dispatchEvent(new Event('pagehide'));
  assert.equal(sent.length,2);assert.deepEqual(sent[1].leave.perf,{apply:{n:1,total:7,max:7},render:{n:1,total:19,max:19}});
  assert.ok(instances.every(x=>x.disconnected),'page exit releases observers');
  assert.equal(api.perfEnabled,false);
}
console.log('client_performance.mjs: bounded sampled phases, long tasks, interactions and beacon integration OK');
