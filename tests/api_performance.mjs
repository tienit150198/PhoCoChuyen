import assert from 'node:assert/strict';
import {GameAPI} from '../public/js/api.js';
import {createClientPerformance} from '../public/js/telemetry.js';

let time=0;
Object.defineProperty(globalThis,'performance',{value:{now:()=>time},configurable:true});
function api(){
  const a=new GameAPI(),events=[];a.updates={seen(){}};a.addEventListener('clientperf',e=>events.push(e.detail));
  return {a,events};
}
const reply=(status=200)=>({ok:status<400,status,headers:new Headers()});
{ // Receiving a slow body is not JSON parse time. No body, path, IDs or response fields enter the event.
  const {a,events}=api();a.perfEnabled=true;
  const original=JSON.parse;
  globalThis.fetch=async()=>({...reply(),text:async()=>{time+=950;return '{"secret":"player typed text"}';},json:async()=>({secret:'player typed text'})});
  try{
    JSON.parse=raw=>{time+=7;return original(raw);};
    assert.deepEqual(await a.fetchJSON('/api/example?private=1',{},1000),{secret:'player typed text'});
  }finally{JSON.parse=original;}
  assert.deepEqual(events,[{parse:7}]);
}
{ // Unsampled requests keep the existing Response.json path with no timing calls.
  const {a,events}=api();a.perfEnabled=false;
  const old=performance.now;performance.now=()=>assert.fail('unsampled timing');
  globalThis.fetch=async()=>({...reply(),json:async()=>({ok:true}),text:()=>assert.fail('unsampled text buffering')});
  try{assert.deepEqual(await a.fetchJSON('/api/example',{},1000),{ok:true});}finally{performance.now=old;}
  assert.deepEqual(events,[]);
}
{ // Adoption and all synchronous state listeners are separate measurements.
  const {a,events}=api();a.perfEnabled=true;
  const state={get settings(){time+=3;return {lang:'vi'};}};
  a.addEventListener('state',()=>{assert.equal(a.state,state);time+=11;});
  assert.equal(a.accept({state,revision:1}),true);
  assert.deepEqual(events,[{apply:3,render:11}]);
  assert.equal(a.revision,1);
  const old=performance.now;performance.now=()=>assert.fail('stale state must not be measured');
  try{assert.equal(a.accept({state:{},revision:0},0),false);}finally{performance.now=old;}
  assert.equal(a.state,state);assert.equal(events.length,1);
}
{ // A page can reach its sample cap while waiting for a response body: stop measuring immediately.
  const {a,events}=api();a.perfEnabled=true;
  globalThis.fetch=async()=>({...reply(),text:async()=>{a.perfEnabled=false;return '{}';},json:()=>assert.fail('already chose sampled body path')});
  const old=performance.now;performance.now=()=>assert.fail('measurement disabled while awaiting body');
  try{assert.deepEqual(await a.fetchJSON('/api/example',{},1000),{});}finally{performance.now=old;}
  assert.deepEqual(events,[]);
}
{ // Commands reconstruct deltas before accept; that CPU work belongs in apply, not a lost pre-phase.
  const {a,events}=api();a.perfEnabled=true;
  a.state={};a.json=async()=>({state:{get chunk(){time+=5;return {};}},revision:1,
    delta:{refs:[],keys:[[['chunk'],'12345678']]},result:{message:'ok'}});
  a.addEventListener('state',()=>{time+=9;});
  await a.command('settings',{});
  assert.deepEqual(events,[{apply:5,render:9}]);
}
{ // Sampled 503/invalid JSON retries preserve request bodies and eventually adopt the state once.
  const {a,events}=api(),perf=createClientPerformance(a,{random:()=>0,Observer:null});
  a.delays=[0,0];a.retryWindow=1000;a.holding={hold(){},release(){}};
  let attempt=0;const bodies=[];
  globalThis.fetch=async(_url,options)=>{
    bodies.push(options.body);attempt++;
    return new Response(attempt===1?'<html>503</html>':JSON.stringify({state:{},revision:1,result:{message:'ok'}}),{status:attempt===1?503:200});
  };
  assert.deepEqual(await a.command('settings',{musicVolume:0}),{message:'ok'});
  assert.equal(attempt,2);assert.equal(bodies[0],bodies[1]);assert.equal(a.revision,1);
  assert.equal(events.filter(e=>'apply' in e).length,1);
  const metrics=perf.take();assert.ok(metrics.parse.n>=1);assert.equal(metrics.apply.n,1);assert.equal(metrics.render.n,1);
  assert.ok(!JSON.stringify(metrics).includes('settings'));perf.stop();
}
console.log('api_performance.mjs: isolated sampled parse/apply/render, stale states and retries OK');
