import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../public/js/v4/fair.js',import.meta.url),'utf8');
const body=source.slice(source.indexOf('/* ---- 💍 Ném vòng cổ chai ---- */'),source.indexOf('/* ---- 🦀 Bầu cua ---- */'));
const css=readFileSync(new URL('../public/css/fair.css',import.meta.url),'utf8');

function fixture({hits=[1,1,-1,4,-1],latency=0,refused=false,chance=true}={}){
 let now=0,id=0;
 const timers=new Map(),frames=new Map(),sounds=[],requests=[],renders=[];
 const later=(fn,ms=0)=>{timers.set(++id,{fn,at:now+ms});return id;};
 const layer={children:[],append(el){el.parentNode=this;this.children.push(el);},replaceChildren(){this.children.forEach(el=>{el.parentNode=null;});this.children=[];}};
 const element=()=>({className:'',dataset:{},style:{setProperty(k,v){this[k]=v;}},remove(){if(this.parentNode)this.parentNode.children=this.parentNode.children.filter(el=>el!==this);this.parentNode=null;}});
 const rd={id:'round-1',chance,xs:[10,30,50,70,90],period:2400,phase:.05};
 const S={busy:false,tab:'ring',ring:{round:rd,t0:0,taps:[],hits:[],raf:0,result:null,say:''},dlg:{open:true,querySelector:s=>s==='.fh-fly-layer'?layer:null}};
 const fair={wallet:100,today_xu:{ring:0},ring:rd,rules:{rings:5,ring_tol:4.5,nocap:1,ring_left:999,ring_hit:2,ring_all:5,ring_chance:true}};
 const n=hits.filter(h=>Number.isInteger(h)&&h>=0).length,result={hits,n,prize:n*2+(n===5?5:0)};
 const context=vm.createContext({S,F:()=>fair,R:()=>fair.rules,RINGER:{idle:['idle'],hit:['hit'],miss:['miss']},
  performance:{now:()=>now},setTimeout:later,clearTimeout:i=>timers.delete(i),requestAnimationFrame:fn=>{frames.set(++id,fn);return id;},cancelAnimationFrame:i=>frames.delete(i),
  document:{createElement:element},reduce:()=>false,pick:a=>a[0],sfx:type=>sounds.push({type,at:now}),
  render:()=>renders.push({at:now,wallet:fair.wallet,result:S.ring.result}),say:()=>'',meter:()=>'',esc:s=>s,xu:n=>`${n} xu`,btn:(label,op)=>`<button data-fh="${op}">${label}</button>`,
  send:(name,payload)=>{requests.push({name,payload,at:now});return new Promise(resolve=>later(()=>{
   if(refused){resolve(null);return;}
   if(name==='fair_ring_start'){resolve({fair:{round:{...rd,id:'round-2'}}});return;}
   fair.wallet+=result.prize;fair.today_xu.ring+=result.prize;fair.ring=null;resolve({fair:result});
  },latency));}});
 const ui=vm.runInContext(body+'\n;({ringThrow,finishRing,ringStart,stopRing,ringView})',context);
 const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
 const advance=async target=>{
  assert.ok(target>=now);await flush();
  for(let count=0;count<200;count++){
   const entry=[...timers.entries()].sort((a,b)=>a[1].at-b[1].at)[0];
   if(!entry||entry[1].at>target){now=target;await flush();return;}
   const [key,timer]=entry;timers.delete(key);now=timer.at;timer.fn();await flush();
  }
  throw new Error('Timer loop did not settle');
 };
 const throwAll=async()=>{for(let i=0;i<5;i++){await advance(i*300);ui.ringThrow();}};
 return {S,rd,fair,result,layer,sounds,requests,renders,frames,ui,advance,throwAll};
}

test('an aimed ring remains pending and visible until the server confirms it',async()=>{
 const f=fixture();f.ui.ringThrow();await f.advance(900);
 assert.equal(f.layer.children.length,1,'a waiting ring must not disappear as if it missed');
 assert.equal(f.layer.children[0].className,'fh-fly pending');
 assert.deepEqual(Array.from(f.S.ring.hits),[]);assert.equal(f.S.ring.result,null);
 assert.ok(!f.sounds.some(s=>['win','clink','miss'].includes(s.type)),'no local hit or miss prediction');
 assert.equal(f.requests.length,0,'all five taps are still needed for the unchanged server command');
});

test('pending CSS does not animate a ring through a bottle neck then fade it out',()=>{
 const pending=css.match(/@keyframes fh-ringpending\{[^\n]+/)[0];
 assert.doesNotMatch(pending,/opacity\s*:\s*0/);
 assert.doesNotMatch(pending,/translateY\(70px\)/);
});

test('a pending ring stays a whole hoop instead of turning into broken dashes',()=>{
 const pending=css.match(/\.fh-fly\.pending\{[^}]+/)[0];
 assert.doesNotMatch(pending,/border-style\s*:\s*(?:dashed|dotted)/,'the thrown hoop must keep an unbroken outline while waiting');
 assert.doesNotMatch(pending,/border-color\s*:\s*var\(--muted\)/,'the same thrown hoop must not turn into grey fragments');
});

for(const hits of [[1,1,-1,4,-1],[-1,-1,-1,-1,-1],[0,1,2,3,4]])for(const latency of [0,2000]){
 test(`server hits ${hits} with ${latency}ms latency determine every ring landing`,async()=>{
  const f=fixture({hits,latency});await f.throwAll();
  assert.equal(f.requests.length,1,'the fifth tap submits exactly once');
  assert.deepEqual(Array.from(f.requests[0].payload.taps),[0,300,600,900,1200]);
  if(latency){await f.advance(1200+latency-1);assert.equal(f.S.ring.result,null);assert.equal(f.layer.children.length,5);assert.ok(f.layer.children.every(el=>el.className==='fh-fly pending'));}
  await f.advance(1200+latency);
  assert.deepEqual(Array.from(f.S.ring.result.hits),hits);
  assert.deepEqual(f.layer.children.map(el=>el.className),hits.map(h=>'fh-fly '+(h>=0?'hit':'miss')),'the visual outcome is the server array, including repeated bottles');
  f.layer.children.forEach((el,i)=>{if(hits[i]>=0)assert.equal(el.style.left,`calc(6% + ${f.rd.xs[hits[i]]*.88}%)`);});
  assert.equal(f.fair.wallet,100+f.result.prize,'the client never credits money a second time');
  assert.ok(f.renders.filter(r=>r.wallet>100).every(r=>r.result),'payout and confirmed result appear together');
  await f.advance(5000);
  assert.equal(f.layer.children.length,0,'temporary flights are cleaned up');
  const view=f.ui.ringView();assert.equal((view.match(/fh-bottle ringed/g)||[]).length,new Set(hits.filter(h=>h>=0)).size,'confirmed hits remain around their bottles after the flight');
  assert.equal(f.requests.length,1);assert.equal(f.fair.wallet,100+f.result.prize);
 });
}

test('a refused round removes pending rings without invented hits or money',async()=>{
 const f=fixture({refused:true,latency:300});await f.throwAll();await f.advance(1500);
 assert.equal(f.S.ring.result,null);assert.equal(f.S.ring.round,null);assert.equal(f.layer.children.length,0);
 assert.deepEqual(Array.from(f.S.ring.hits),[]);assert.equal(f.fair.wallet,100);assert.equal(f.S.ring.finishing,false);
 assert.ok(!f.sounds.some(s=>['win','clink','miss'].includes(s.type)));
});

for(const hide of ['close','tab'])test(`${hide} while waiting stores the answer without hidden replay or sound`,async()=>{
 const f=fixture({latency:2000});await f.throwAll();
 if(hide==='close'){f.S.dlg.open=false;f.ui.stopRing();}else f.S.tab='home';
 const rendered=f.renders.length,sounds=f.sounds.length;await f.advance(4000);
 assert.equal(f.S.ring.result.n,3);assert.equal(f.S.ring.finishing,false);
 assert.equal(f.sounds.length,sounds);assert.equal(f.renders.length,rendered);assert.equal(f.frames.size,0);
 assert.equal(f.layer.children.length,0,'hidden pending nodes cannot survive into a later round');
 f.S.dlg.open=true;f.S.tab='ring';assert.match(f.ui.ringView(),/Trúng 3\/5 vòng/);
});

test('a replaced round ignores an old answer and its visual cleanup',async()=>{
 const f=fixture({latency:2000});await f.throwAll();
 const replacement={...f.rd,id:'round-2'};f.S.ring={round:replacement,t0:1200,taps:[],hits:[],raf:0,result:null,say:''};f.layer.replaceChildren();
 const rendered=f.renders.length,sounds=f.sounds.length;await f.advance(4000);
 assert.equal(f.S.ring.round,replacement);assert.equal(f.S.ring.result,null);assert.equal(f.renders.length,rendered);assert.equal(f.sounds.length,sounds);
});

test('starting the next round clears old flights before it can accept another throw',async()=>{
 const f=fixture();await f.throwAll();await f.advance(1200);
 const next=f.ui.ringStart();await f.advance(1200);await next;
 assert.equal(f.S.ring.round.id,'round-2');assert.equal(f.layer.children.length,0);assert.equal(f.S.ring.result,null);
 f.ui.ringThrow();await f.advance(2000);assert.equal(f.layer.children.length,1,'old flight cleanup does not remove a new pending ring');
});

test('returning to the stall can rebuild pending rings from the current taps',async()=>{
 const f=fixture();f.ui.ringThrow();await f.advance(300);f.ui.ringThrow();
 f.layer.replaceChildren();
 assert.equal((f.ui.ringView().match(/class="fh-fly pending"/g)||[]).length,2,'a remounted layer retains the unfinished throws');
});

test('legacy timing rounds also wait for authoritative hits and repeated finish never pays twice',async()=>{
 const f=fixture({chance:false,hits:[-1,-1,-1,-1,-1],latency:300});await f.throwAll();
 f.ui.ringThrow();f.ui.finishRing(f.rd);assert.equal(f.requests.length,1);assert.deepEqual(Array.from(f.S.ring.hits),[]);
 await f.advance(1500);f.ui.finishRing(f.rd);assert.equal(f.requests.length,1);assert.equal(f.S.ring.result.n,0);assert.equal(f.fair.wallet,100);
});

for(const hits of [[1,2,1,2,null],[3,3,3,3,3]])test(`every confirmed hit has its own neck hoop: ${hits}`,async()=>{
 const f=fixture({hits});await f.throwAll();await f.advance(2000);
 const view=f.ui.ringView(),expected=hits.filter(h=>Number.isInteger(h)&&h>=0).length;
 assert.equal((view.match(/class="fh-neck-ring"/g)||[]).length,expected,'duplicate bottle indices must not collapse awarded rings');
 for(const index of new Set(hits.filter(h=>Number.isInteger(h)&&h>=0))){const count=hits.filter(h=>h===index).length;assert.ok(view.includes(`Chai ${index+1}, đã trúng ${count} vòng`),'the bottle also announces its exact ring count');}
});
