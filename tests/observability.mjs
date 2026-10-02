import assert from 'node:assert/strict';
import {test} from 'node:test';
import {createObservability} from '../public/js/observability.js';

const config={origin:'https://phocochuyen.io.vn',firebase:{apiKey:'public',projectId:'pho-co-chuyen',appId:'1:123:web:abc',measurementId:'G-ABC123'},performance:true};
function setup(extra={}){
  const calls=[],api=new EventTarget();
  api.state={current:'milk_tea',journey:{life_day:1},settings:{lang:'vi'}};
  const context={config,origin:config.origin,consent:'yes',navigator:{},api,ui:{view:'home'},version:'1.3.4',
    load:async()=>({event:(name,params)=>calls.push({name,params}),stop:()=>calls.push({name:'stop'})}),...extra};
  return {calls,api,context,tracker:createObservability(context)};
}
function detail(target,name,data){const event=new Event(name);event.detail=data;target.dispatchEvent(event);}

test('production tracking requires consent and respects DNT/GPC',async()=>{
  for(const extra of [{consent:null},{consent:'no'},{origin:'http://localhost:8765'},{navigator:{doNotTrack:'1'}},{navigator:{globalPrivacyControl:true}}]){
    let loads=0;
    const {tracker,calls}=setup({...extra,load:async()=>{loads++;return {event:()=>calls.push('sent')}}});
    await tracker.start();assert.equal(loads,0);assert.equal(calls.length,0);
  }
});
test('SDK failure is isolated from gameplay',async()=>{
  const {tracker,api,calls}=setup({load:async()=>{throw new Error('blocked by browser')}});
  await assert.doesNotReject(()=>tracker.start());
  detail(api,'result',{action:'start_day',career:'milk_tea',result:{message:'user text'}});
  assert.equal(calls.length,0);
});
test('starts once and emits game events without user data',async()=>{
  const {tracker,api,calls}=setup();await tracker.start();await tracker.start();
  detail(api,'result',{action:'start_day',career:'milk_tea',payload:{name:'SECRET PLAYER'},result:{message:'PRIVATE CHAT'}});
  detail(api,'result',{action:'end_day',career:'milk_tea',result:{coins:99}});
  tracker.error('js','SECRET ERROR');tracker.screen('bank','SECRET USER');
  assert.equal(calls.filter(x=>x.name==='game_ready').length,1);
  assert.equal(calls.filter(x=>x.name==='career_start').length,1);
  assert.equal(calls.filter(x=>x.name==='shift_complete').length,1);
  const serialized=JSON.stringify(calls);
  for(const value of ['SECRET','PRIVATE CHAT','99'])assert.ok(!serialized.includes(value));
});
test('revocation stops collection and removes game listeners',async()=>{
  const {tracker,api,calls}=setup();await tracker.start();tracker.stop();
  const before=calls.length;
  detail(api,'result',{action:'start_day',career:'milk_tea'});tracker.error('api');tracker.screen('bank');
  assert.equal(calls.length,before);assert.equal(calls.at(-1).name,'stop');
});
test('unbounded screens and error strings never reach Google',async()=>{
  const {tracker,calls}=setup();await tracker.start();const before=calls.length;
  tracker.screen('player@example.com');tracker.error('private text');
  assert.equal(calls.length,before);
  tracker.screen('bank');tracker.screen('bank');
  assert.equal(calls.filter(x=>x.name==='screen_view').length,1);
});
test('revocation while the SDK loads never attaches listeners or sends events',async()=>{
  let resolve,stops=0;
  const {tracker,api,calls}=setup({load:()=>new Promise(done=>{resolve=done})});
  const pending=tracker.start();tracker.setConsent('no');
  resolve({event:()=>calls.push('sent'),stop:()=>stops++});await pending;
  detail(api,'result',{action:'start_day',career:'milk_tea'});
  assert.equal(calls.length,0);assert.equal(stops,1);
});
test('unsupported SDK produces no events',async()=>{
  const {tracker,calls}=setup({load:async()=>null});
  await tracker.start();tracker.screen('bank');assert.equal(calls.length,0);
});
