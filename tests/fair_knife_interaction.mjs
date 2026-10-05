import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../public/js/v4/fair-knife.js',import.meta.url),'utf8').replace(/export /g,'');
function fixture({taps=[0,120],elapsed=1000,latency=1000,lost=false,refused=false,need=3,response=null}={}){
 let now=0,id=0;
 const timers=new Map(),frames=new Map(),sounds=[],requests=[],renders=[],events={};
 const paint={gradients:0,bitmaps:0};
 const context2d=new Proxy({createLinearGradient(){paint.gradients++;return {addColorStop(){}};},createRadialGradient(){paint.gradients++;return {addColorStop(){}};},drawImage(){paint.bitmaps++;}}, {get:(o,key)=>o[key]??(()=>{})});
 const canvas=()=>({width:300,height:360,isConnected:true,getContext:()=>context2d,getBoundingClientRect:()=>({width:300}),addEventListener(){}});
 const cv=canvas(),document={hidden:false,documentElement:{dataset:{}},createElement:canvas,addEventListener:(name,fn)=>{events[name]=fn;}};
 const later=(fn,ms)=>{timers.set(++id,{fn,at:now+ms});return id;};
 const board={chance:true,need,pre:[],th0:0,segs:[[60000,240,0]]};
 const k={fly:80,gap:10,impact:90,min_tap:120,level_ms:60000,levels:10,stakes:[2,5],ladder:[11,12,16,21,28,36,46,60,78,100],
  run:{stage:'play',id:'round-1',lv:1,el:elapsed,tp:taps,stake:5,prize:0,win:6,board}};
 const S={tab:'dt',dlg:{open:true,querySelector:()=>cv},env:{api:{refresh:async()=>{}}}};
 const context=vm.createContext({performance:{now:()=>now},document,ResizeObserver:class{observe(){}},
  setTimeout:later,clearTimeout:i=>timers.delete(i),requestAnimationFrame:fn=>{frames.set(++id,fn);return id;},cancelAnimationFrame:i=>frames.delete(i)});
 const {setup}=vm.runInContext(source+'\n;({setup})',context);
 const ui=setup({S,F:()=>({knife:k,now:0,wallet:100,open:true}),serverNow:()=>0,reduce:()=>false,pick:a=>a[0],
  btn:(title,op,data,cls,attrs)=>`<button data-fh="${op}"${attrs||''}>${title}</button>`,say:()=>'',xu:String,esc:String,
  render:()=>renders.push({at:now,level:S.kn.L,last:S.kn.last}),sfx:type=>sounds.push({type,at:now}),
  send:(name,payload)=>{requests.push({name,payload,at:now});return new Promise(resolve=>later(()=>{
   if(refused){resolve(null);return;}
   if(response){k.run=response.fair.run;resolve(response);return;}
   const run={stage:lost?'lost':'choice',lv:1,stake:5,prize:lost?0:6,win:7,chance:true};k.run=run;
   resolve({fair:{lost,cleared:!lost,lv:1,stuck:Array.from({length:need-(lost?1:0)},(_,i)=>360*i/need),run}});
  },latency));}});
 const flush=async()=>{for(let i=0;i<16;i++)await Promise.resolve();};
 const advance=async target=>{
  assert.ok(target>=now);await flush();
  for(let count=0;count<100;count++){
   const entry=[...timers.entries()].sort((a,b)=>a[1].at-b[1].at)[0];
   if(!entry||entry[1].at>target){now=target;await flush();return;}
   const [key,timer]=entry;timers.delete(key);now=timer.at;timer.fn();await flush();
  }
  throw new Error('Timer loop did not settle');
 };
 const frame=()=>{const entries=[...frames.entries()];frames.clear();for(const [,fn] of entries)fn(now);};
 const replace=()=>{k.run={...k.run,id:'round-2',lv:2,stage:'play',el:0,tp:[],board};S.kn.L=null;ui.view();return S.kn.L;};
 return {S,k,ui,paint,sounds,requests,renders,frames,advance,frame,replace,document,events,throw:()=>ui.click('knthrow',{})};
}

test('a delayed chance result never confirms the last knife before the server',async()=>{
 const f=fixture({lost:true});f.throw();await f.advance(500);
 assert.equal(f.S.kn.L.over,'pending');
 assert.equal(f.S.kn.L.stuck.length,2,'only the first two knives are confirmed while the final one is pending');
 assert.equal(f.sounds.filter(s=>s.type==='mark').length,0,'the last knife must not sound like a hit before a later loss');
 await f.advance(1700);assert.equal(f.S.kn.last.kind,'lost');
 assert.equal(f.sounds.filter(s=>s.type==='mark').length,0);
});

test('leaving the stall during a flight suppresses its delayed sound',async()=>{
 const f=fixture({taps:[]});f.throw();f.S.tab='home';f.ui.stop();await f.advance(100);
 assert.equal(f.sounds.filter(s=>s.type==='mark').length,0);
});

test('backgrounding during the last flight does not play result sounds',async()=>{
 const f=fixture({latency:200,lost:true});f.throw();f.document.hidden=true;f.events.visibilitychange();await f.advance(1000);
 assert.equal(f.sounds.filter(s=>s.type==='mark'||s.type==='lose').length,0);
 assert.equal(f.S.kn.last.kind,'lost','the authoritative answer still settles while hidden');
});

test('an expired old board cannot submit taps after it has been replaced',async()=>{
 const f=fixture({elapsed:60001});f.ui.mount();f.frame();const replacement=f.replace();await f.advance(500);
 assert.equal(f.requests.length,0,'the delayed timeout must not submit the old level');
 assert.equal(f.S.kn.L,replacement);assert.equal(f.S.kn.last,null);
});

test('an expired old board cannot overwrite a replacement after refreshing',async()=>{
 const f=fixture({elapsed:60001,taps:[]});f.ui.mount();f.frame();await f.advance(500);
 const replacement=f.replace();await f.advance(5000);
 assert.equal(f.S.kn.L,replacement,'the previous timeout must not clear the next board');
 assert.equal(f.S.kn.last,null,'the previous timeout must not turn the new run into a loss');
});

test('an expiry refresh that finds a cleared level does not invent a loss',async()=>{
 const f=fixture({elapsed:60001,taps:[]});f.S.env.api.refresh=async()=>{f.k.run={stage:'choice',lv:1,stake:5,prize:6,win:7,chance:true};};
 f.ui.mount();f.frame();await f.advance(5000);
 assert.equal(f.S.kn.last,null);assert.equal(f.S.kn.L,null);
 assert.equal(f.sounds.filter(s=>s.type==='lose').length,0);assert.match(f.ui.view(),/Qua màn 1!/);
});

test('an expiry with an unavailable refresh keeps the level recoverable without inventing a loss',async()=>{
 const f=fixture({elapsed:60001,taps:[]});f.S.env.api.refresh=async()=>{throw new Error('offline');};
 f.ui.mount();f.frame();const level=f.S.kn.L;await f.advance(5000);
 assert.equal(f.S.kn.L,level);assert.equal(level.over,'retry');assert.equal(f.S.kn.last,null);
 f.S.env.api.refresh=async()=>{f.k.run={stage:'lost',lv:1,stake:5,gone:0,chance:true};};
 f.ui.click('knretry',{});await f.advance(5000);
 assert.equal(f.requests.length,0,'a no-tap expiry only reads its outcome');assert.equal(f.S.kn.L,null);
 assert.match(f.ui.view(),/Thua ở màn 1/);
});

test('timeout submissions include their original board id',async()=>{
 const f=fixture({elapsed:60001});f.ui.mount();f.frame();await f.advance(400);
 assert.equal(f.requests[0].payload.id,'round-1');
});

test('steady board frames reuse blade artwork instead of rebuilding gradients',()=>{
 const f=fixture();f.ui.mount();f.frame();const first=f.paint.gradients;
 f.frame();f.frame();
 assert.equal(f.paint.gradients,first,'blade, wood, and background artwork are reused at the same scale');
 assert.ok(f.paint.bitmaps>0);
});

test('rapid taps still respect the server interval and submit a single complete level',async()=>{
 const f=fixture({taps:[],need:3});f.throw();f.throw();await f.advance(119);f.throw();await f.advance(120);f.throw();await f.advance(240);f.throw();f.throw();
 assert.equal(f.requests.length,1);assert.equal(f.requests[0].name,'fair_kn_throw');
 assert.equal(f.requests[0].payload.id,'round-1','throws are bound to their board across server revision retries');
 assert.deepEqual(Array.from(f.requests[0].payload.taps),[1000,1120,1240]);
});

test('a failed final response retains the submitted taps for an explicit retry',async()=>{
 const f=fixture({refused:true,latency:200});f.throw();const level=f.S.kn.L;await f.advance(200);
 assert.equal(f.S.kn.L,level,'a failed response must not reset the board to its pre-submit count');
 assert.equal(level.over,'retry');assert.equal(f.ui.busy(),false);
 assert.match(f.ui.view(),/data-fh="knretry"/);
 await f.advance(2000);assert.equal(f.requests.length,1,'no mutation retries run without user input');
});

test('retry refreshes first and never resubmits a result that already reached the server',async()=>{
 const f=fixture({refused:true,latency:200});f.throw();await f.advance(200);let refreshes=0;
 f.S.env.api.refresh=async()=>{refreshes++;f.k.run={stage:'choice',lv:1,stake:5,prize:6,win:7,chance:true};};
 f.ui.click('knretry',{});f.ui.click('knretry',{});await f.advance(200);
 assert.equal(refreshes,1);assert.equal(f.requests.length,1);
 assert.equal(f.S.kn.L,null);assert.match(f.ui.view(),/Qua màn 1!/);
 assert.doesNotMatch(f.S.kn.say,/Chưa nhận được kết quả/,'the recovered result must replace the stale waiting message');
 assert.equal(f.S.kn.rest.length,3,'a recovered clear shows every confirmed knife');
});

test('retry cannot replay taps into a new run with the same level number',async()=>{
 const f=fixture({refused:true,latency:200});f.throw();await f.advance(200);
 f.S.env.api.refresh=async()=>{f.k.run={...f.k.run,id:'a-different-round',tp:[]};};
 f.ui.click('knretry',{});await f.advance(200);
 assert.equal(f.requests.length,1);f.ui.view();assert.equal(f.S.kn.L.id,'a-different-round');
 assert.equal(f.S.kn.L.taps.length,0);
});

test('retry resubmits identical taps once only when a refreshed matching run is still playing',async()=>{
 const f=fixture({refused:true,latency:200});f.throw();await f.advance(200);let refreshes=0;
 f.S.env.api.refresh=async()=>{refreshes++;};
 f.ui.click('knretry',{});f.ui.click('knretry',{});await f.advance(400);
 assert.equal(refreshes,1);assert.equal(f.requests.length,2);
 assert.deepEqual(f.requests[1].payload,f.requests[0].payload);
 assert.equal(f.requests[1].payload.id,'round-1');
 assert.equal(f.S.kn.L.over,'retry');assert.equal(f.ui.busy(),false);
});

test('retry preserves the board and sends nothing if the state refresh also fails',async()=>{
 const f=fixture({refused:true,latency:200});f.throw();const level=f.S.kn.L;await f.advance(200);
 f.S.env.api.refresh=async()=>{throw new Error('offline');};
 f.ui.click('knretry',{});await f.advance(200);
 assert.equal(f.requests.length,1);assert.equal(f.S.kn.L,level);assert.equal(f.ui.busy(),false);
});

for(const action of ['start','next'])test(`closing during ${action} keeps the accepted board without sound or repaint`,async()=>{
 const response={fair:{}},f=fixture({response,latency:200});
 response.fair.run={...f.k.run,id:'accepted-board',lv:action==='next'?2:1,tp:[],el:0};
 f.k.run=action==='start'?null:{...f.k.run,stage:'choice'};
 f.ui.click('kn'+action,{});const renders=f.renders.length;f.S.dlg.open=false;f.ui.stop();
 await f.advance(200);
 assert.equal(f.k.run.id,'accepted-board');assert.equal(f.S.kn.L.id,'accepted-board');assert.equal(f.ui.busy(),false);
 assert.equal(f.sounds.filter(s=>s.type==='open').length,0);
 assert.equal(f.renders.length,renders,'a closed dialog must not repaint after the response');
});

test('closing during stop retains payment without sound or repaint',async()=>{
 const response={fair:{stopped:true,prize:6,run:{stage:'done',lv:1,stake:5,paid:6}}},f=fixture({response,latency:200});
 f.k.run={...f.k.run,stage:'choice',prize:6};
 f.ui.click('knstop',{});const renders=f.renders.length;f.S.dlg.open=false;f.ui.stop();await f.advance(200);
 assert.equal(f.k.run.stage,'done');assert.equal(f.S.kn.last.kind,'paid');assert.equal(f.S.kn.last.paid,6);assert.equal(f.ui.busy(),false);
 assert.equal(f.sounds.filter(s=>s.type==='win').length,0);
 assert.equal(f.renders.length,renders,'a closed dialog must not repaint after payment');
});
