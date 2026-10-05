import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../public/js/v4/fair-knife.js',import.meta.url),'utf8').replace(/export /g,'');
function fixture({need=11,lost=false,latency=1000}={}){
 let now=0,id=0,paint=[];
 const timers=new Map(),frames=new Map();
 function canvas(root=false){
  let matrix=[1,0,0,1,0,0],stack=[];
  const cv={width:300,height:360,isConnected:true,getBoundingClientRect:()=>({width:300}),addEventListener(){}};
  const ctx=new Proxy({globalAlpha:1,
   save(){stack.push({matrix:[...matrix],alpha:this.globalAlpha});},
   restore(){const prev=stack.pop();matrix=prev.matrix;this.globalAlpha=prev.alpha;},
   setTransform(...values){matrix=values;},
   translate(x,y){const [a,b,c,d,e,f]=matrix;matrix=[a,b,c,d,a*x+c*y+e,b*x+d*y+f];},
   rotate(angle){const [a,b,c,d,e,f]=matrix,co=Math.cos(angle),si=Math.sin(angle);matrix=[a*co+c*si,b*co+d*si,-a*si+c*co,-b*si+d*co,e,f];},
   createLinearGradient:()=>({addColorStop(){}}),createRadialGradient:()=>({addColorStop(){}}),
   drawImage(image){if(root&&image.width===22&&image.height===72)paint.push({x:matrix[4],y:matrix[5],angle:Math.atan2(matrix[1],matrix[0])+Math.PI/2,alpha:this.globalAlpha});}
  },{get:(obj,key)=>obj[key]??(()=>{})});
  cv.getContext=()=>ctx;return cv;
 }
 const cv=canvas(true),later=(fn,ms)=>{timers.set(++id,{fn,at:now+ms});return id;};
 const board={chance:true,need,pre:[],th0:0,segs:[[64000,240,0]]};
 const k={fly:80,gap:10,impact:90,min_tap:120,level_ms:60000,run:{stage:'play',id:'physical-board',lv:1,el:1000,tp:[],stake:5,board}};
 const S={tab:'dt',dlg:{open:true,querySelector:s=>s==='.fh-kn-cv'?cv:null}};
 const context=vm.createContext({performance:{now:()=>now},document:{hidden:false,documentElement:{dataset:{}},createElement:()=>canvas(),addEventListener(){}},
  ResizeObserver:class{observe(){}},setTimeout:later,clearTimeout:i=>timers.delete(i),requestAnimationFrame:fn=>{frames.set(++id,fn);return id;},cancelAnimationFrame:i=>frames.delete(i)});
 const {setup,angleAt,lands}=vm.runInContext(source+'\n;({setup,angleAt,lands})',context);
 const ui=setup({S,F:()=>({knife:k,now:0}),serverNow:()=>0,reduce:()=>false,pick:a=>a[0],render(){},sfx(){},
  send:()=>new Promise(resolve=>later(()=>{k.run={stage:lost?'lost':'choice',lv:1,stake:5};resolve({fair:{lost,cleared:!lost,lv:1,stuck:Array.from({length:need-(lost?1:0)},(_,i)=>360*i/need),run:k.run}});},latency))});
 const flush=async()=>{for(let i=0;i<16;i++)await Promise.resolve();};
 const advance=async target=>{await flush();for(let count=0;count<100;count++){const entry=[...timers].sort((a,b)=>a[1].at-b[1].at)[0];if(!entry||entry[1].at>target){now=target;await flush();return;}const [key,timer]=entry;timers.delete(key);now=timer.at;timer.fn();await flush();}throw Error('timer did not settle');};
 const frame=()=>{paint=[];const callbacks=[...frames.values()];frames.clear();for(const fn of callbacks)fn(now);return paint;};
 const physical=at=>{const angle=(lands(board,k,1000)+angleAt(board,1000+at))*Math.PI/180;return {x:150+68*Math.cos(angle),y:150+68*Math.sin(angle),angle};};
 ui.mount();return {S,ui,k,board,advance,frame,physical,throw:()=>ui.click('knthrow',{})};
}
const distance=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
const angleDistance=(a,b)=>Math.abs(Math.atan2(Math.sin(a.angle-b.angle),Math.cos(a.angle-b.angle)));

test('a chance knife reaches its displayed stuck position continuously at impact',async()=>{
 const f=fixture();f.throw();await f.advance(79);const flying=f.frame()[0];await f.advance(80);const stuck=f.frame()[0];
 assert.ok(distance(flying,stuck)<2,`79→80 ms tip jump is ${distance(flying,stuck).toFixed(1)} px: ${JSON.stringify({flying,stuck})}`);
 assert.ok(distance(stuck,f.physical(80))<.01,'the blade sticks at the actual flight impact angle');
});

test('the pending last chance knife rotates from its real impact position while awaiting the server',async()=>{
 const f=fixture({need:1});f.throw();await f.advance(280);const pending=f.frame()[0];
 assert.ok(distance(pending,f.physical(280))<.01,`pending blade leaves its physical slot: ${JSON.stringify({pending,expected:f.physical(280)})}`);
 assert.ok(angleDistance(pending,f.physical(280))<.001,'the pending blade stays aligned with its physical slot');
 assert.equal(pending.alpha,.45);assert.equal(f.S.kn.L.over,'pending');
});

test('a delayed authoritative clear confirms the same physical slot without adopting server display angles',async()=>{
 const f=fixture({need:1});f.throw();await f.advance(1000);const confirmed=f.frame()[0];
 assert.ok(distance(confirmed,f.physical(1000))<.01,`confirmed blade jumps to server placeholder: ${JSON.stringify({confirmed,expected:f.physical(1000)})}`);
 assert.equal(confirmed.alpha,1);assert.equal(f.S.kn.L.over,'clear');
});

test('a delayed authoritative loss bounces from the pending blade position',async()=>{
 const f=fixture({need:1,lost:true});f.throw();await f.advance(1000);const bounce=f.frame()[0];
 assert.ok(distance(bounce,f.physical(1000))<.01,`bounce starts at the wrong location: ${JSON.stringify({bounce,expected:f.physical(1000)})}`);
 assert.ok(angleDistance(bounce,f.physical(1000))<.001,'the bounce inherits the pending blade orientation');
 assert.equal(f.S.kn.L.over,'lost');assert.equal(f.S.kn.L.stuck.length,0);
});

test('the result board continues from the terminal board orientation',async()=>{
 const f=fixture({need:1});f.throw();await f.advance(1649);const terminal=f.frame()[0];await f.advance(1650);const rest=f.frame()[0];
 assert.equal(f.S.kn.L,null);assert.ok(distance(terminal,rest)<.01,`terminal→rest blade jumps ${distance(terminal,rest).toFixed(1)} px`);
});
