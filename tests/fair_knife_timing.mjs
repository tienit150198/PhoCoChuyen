import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../public/js/v4/fair-knife.js',import.meta.url),'utf8').replace(/export /g,'');
function fixture({latency=0,lost=false,chance=true,refused=false}={}){
 let now=0,id=0;
 const timers=new Map(),frames=new Map(),sounds=[],requests=[],renders=[];
 const later=(fn,ms)=>{timers.set(++id,{fn,at:now+ms});return id;};
 const board={chance,need:8,pre:[],th0:0,segs:[[60000,60,0]]};
 if(lost&&!chance)board.pre=[(90-60*2.08+360)%360];
 const k={fly:80,gap:6,impact:90,min_tap:120,level_ms:60000,
  run:{stage:'play',id:'level-1',lv:1,el:2000,tp:[0,120,240,360,480,600,720],board}};
 const S={tab:'dt',dlg:{open:true}};
 const context=vm.createContext({performance:{now:()=>now},document:{hidden:false,addEventListener:()=>{}},
  setTimeout:later,clearTimeout:i=>timers.delete(i),requestAnimationFrame:fn=>{frames.set(++id,fn);return id;},cancelAnimationFrame:i=>frames.delete(i)});
 const {setup}=vm.runInContext(source+'\n;({setup})',context);
 const ui=setup({S,F:()=>({knife:k,now:0}),serverNow:()=>0,reduce:()=>false,pick:a=>a[0],
  render:()=>renders.push({at:now,level:S.kn.L,last:S.kn.last}),sfx:type=>sounds.push({type,at:now}),
  send:(name,payload)=>{requests.push({name,payload,at:now});return new Promise(resolve=>later(()=>{
   if(refused){resolve(null);return;}
   const run={stage:lost?'lost':'choice',lv:1,stake:5};k.run=run;
   resolve({fair:{lost,cleared:!lost,lv:1,stuck:[0,45,90,135,180,225,270,315],run}});
  },latency));}});
 const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
 const advance=async target=>{
  assert.ok(target>=now);
  await flush();
  for(let count=0;count<100;count++){
   const entry=[...timers.entries()].sort((a,b)=>a[1].at-b[1].at)[0];
   if(!entry||entry[1].at>target){now=target;await flush();return;}
   const [key,timer]=entry;timers.delete(key);now=timer.at;timer.fn();await flush();
  }
  throw new Error('Timer loop did not settle');
 };
 return {S,k,ui,sounds,requests,renders,frames,advance,throw:()=>ui.click('knthrow',{}),terminal:()=>sounds.filter(s=>s.type==='cap'||s.type==='lose')};
}

for(const latency of [0,200,1000])for(const lost of [false,true]){
 test(`chance ${lost?'loss':'clear'} with ${latency}ms response waits for flight and one terminal animation`,async()=>{
  const f=fixture({latency,lost}),terminalAt=Math.max(80,latency),resultAt=terminalAt+(lost?700:650);
  f.throw();assert.equal(f.requests.length,1);assert.equal(f.requests[0].name,'fair_kn_throw');
  assert.equal(f.requests[0].payload.taps.at(-1),2000,'the final tap uses the original level clock');
  await f.advance(terminalAt-1);
  assert.equal(f.terminal().length,0,'no local prediction before both server answer and last knife impact');
  assert.equal(f.S.kn.L.over,'pending');assert.equal(f.ui.busy(),true);
  await f.advance(terminalAt);
  assert.deepEqual(f.terminal(),[{type:lost?'lose':'cap',at:terminalAt}],'terminal animation starts immediately when flight and answer are ready');
  await f.advance(resultAt-1);
  assert.equal(f.ui.busy(),true,'terminal animation keeps the result controls blocked');assert.equal(f.S.kn.last,null);
  await f.advance(resultAt);
  assert.equal(f.S.kn.L,null,'one terminal animation is sufficient');assert.equal(f.ui.busy(),false);
  assert.equal(f.renders.at(-1).at,resultAt);
  assert.equal(f.S.kn.last?.kind,lost?'lost':undefined);
 });
}

for(const lost of [false,true])test(`legacy skill ${lost?'loss':'clear'} retains its original flight and animation wait`,async()=>{
 const f=fixture({chance:false,lost}),resultAt=80+(lost?700:650);
 f.throw();await f.advance(resultAt-1);assert.equal(f.ui.busy(),true);
 await f.advance(resultAt);assert.equal(f.ui.busy(),false);assert.equal(f.renders.at(-1).at,resultAt);
 assert.equal(f.requests.length,1);
});

test('a refused chance throw releases busy state and retains taps for explicit recovery',async()=>{
 const f=fixture({latency:200,refused:true});f.throw();await f.advance(200);
 assert.equal(f.S.kn.L.over,'retry');assert.equal(f.S.kn.L.taps.length,8);assert.equal(f.ui.busy(),false);
 assert.equal(f.S.kn.last,null);assert.equal(f.terminal().length,0);
});

test('closing the dialog before the answer settles without scheduling hidden terminal animation',async()=>{
 const f=fixture({latency:200,lost:true});f.throw();await f.advance(20);
 f.S.dlg.open=false;f.ui.stop();const rendered=f.renders.length;
 await f.advance(1000);
 assert.equal(f.terminal().length,0,'a closed dialog does not play result sounds');
 assert.equal(f.frames.size,0,'a closed dialog does not restart animation frames');
 assert.equal(f.renders.length,rendered,'a closed dialog does not repaint');
 assert.equal(f.ui.busy(),false,'the server answer still settles the pending level');
 assert.equal(f.S.kn.last.kind,'lost');
});

for(const replaceAt of [20,100])test(`a replaced level ignores stale result completion at ${replaceAt}ms`,async()=>{
 const f=fixture({latency:80,lost:true});f.throw();await f.advance(replaceAt);
 const replacement={id:'level-2',b:f.S.kn.L.b,over:null,done:false,taps:[],stuck:[]};
 f.S.kn.L=replacement;const rendered=f.renders.length,terminal=f.terminal().length;
 await f.advance(2000);
 assert.equal(f.S.kn.L,replacement,'a delayed old answer never clears the new level');
 assert.equal(f.S.kn.last,null);assert.equal(f.renders.length,rendered);assert.equal(f.terminal().length,terminal);
});
