import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync(new URL('../public/js/v4/fair.js',import.meta.url),'utf8');
const slice=(start,end)=>source.slice(source.indexOf(start),source.indexOf(end,source.indexOf(start)));

test('an inactive stall never blocks state refresh for the visible stall',()=>{
 const S={tab:'home',busy:false,bc:{phase:'shake'},xd:{phase:'shake'},oaq:{anim:{}},ring:{taps:[100],result:null,finishing:true}};
 const context=vm.createContext({S,KN:{busy:()=>true},XS:{busy:()=>true},PB:{busy:()=>true}});
 const animating=vm.runInContext(slice('const animating=','async function send')+';animating',context);
 assert.equal(animating(),false,'leaving unfinished games must release unrelated live updates');
 for(const tab of ['bc','xd','dt','xs','pb','oaq','ring']){S.tab=tab;assert.equal(animating(),true,tab+' still protects its visible animation');}
 S.tab='ring';S.ring.finishing=false;assert.equal(animating(),false,'a partial ring round can receive state updates while preserving live DOM');
 S.tab='home';S.busy=true;assert.equal(animating(),true,'a pending shared command retains its lock');
});

function oaqFixture({latency=0}={}){
 let now=0,id=0;const timers=new Map(),renders=[],sounds=[];
 const o={stage:'play',lv:'de',b:Array(12).fill(5),q:[1,1],cap:[0,0,0,0],ply:0};
 const S={tab:'oaq',busy:false,tick:0,oaq:{sel:1,fast:false,anim:null},dlg:{open:true},env:{api:{refresh:async()=>{}}}};
 const end={stage:'won',me:55,opp:15,prize:15},fair={oaq:o};
 const context=vm.createContext({S,F:()=>fair,R:()=>({}),OPP:{de:{lost:['won']}},pick:a=>a?.[0]||'',document:{hidden:false},reduce:()=>false,
  setTimeout:(fn,ms)=>{timers.set(++id,{fn,at:now+ms});return id;},render:()=>renders.push({at:now,open:S.dlg.open,tab:S.tab}),sfx:type=>sounds.push({type,at:now}),
  send:()=>new Promise(resolve=>{const finish=()=>{fair.oaq={...o,stage:'won',b:Array(12).fill(0)};resolve({fair:{trace:Array.from({length:40},(_,i)=>['drop',i%12]),end}});};if(latency)timers.set(++id,{fn:finish,at:now+latency});else finish();}),
  pauseLoto:()=>{},ltMusic:()=>{},stopRing:()=>{},KN:null,PB:null,clearInterval:()=>{}});
 const ui=vm.runInContext(slice('const wait=ms=>','/* ---- 💍 Ném vòng cổ chai ---- */')+';({oaqMove,playTrace})',context);
 const closeBody=source.match(/d\.addEventListener\('close',\(\)=>\{([^\n]+)\}\);/)[1];
 const close=vm.runInContext('()=>{S.dlg.open=false;'+closeBody+'}',context);
 const flush=async()=>{for(let i=0;i<8;i++)await Promise.resolve();};
 const advance=async target=>{await flush();for(let i=0;i<100;i++){const entry=[...timers.entries()].sort((a,b)=>a[1].at-b[1].at)[0];if(!entry||entry[1].at>target){now=target;await flush();return;}timers.delete(entry[0]);now=entry[1].at;entry[1].fn();await flush();}throw Error('timer loop');};
 return {S,fair,end,ui,close,advance,renders,sounds,document:context.document};
}

for(const leave of ['close','tab','document'])test(`ô ăn quan fast-forwards authoritative state when ${leave} hides its trace`,async()=>{
 const f=oaqFixture(),move=f.ui.oaqMove(1);await f.advance(50);const before=f.renders.length,sounds=f.sounds.length;
 if(leave==='close')f.close();else if(leave==='tab')f.S.tab='home';else f.document.hidden=true;
 await f.advance(5000);await move;
 assert.equal(f.S.busy,false);assert.equal(f.S.oaq.anim,null);assert.equal(f.S.oaq.end.prize,15);assert.equal(f.fair.oaq.stage,'won');
 assert.equal(f.sounds.length,sounds,'hidden stones and result do not play sounds');
 assert.ok(f.renders.length-before<2,'a hidden trace does not repeatedly rebuild the fair');
});

test('closing then reopening during a wait never resumes the old stone replay',async()=>{
 const f=oaqFixture(),move=f.ui.oaqMove(1);await f.advance(50);f.close();f.S.dlg.open=true;
 const renders=f.renders.length,sounds=f.sounds.length;await f.advance(5000);await move;
 assert.equal(f.renders.length-renders,1,'one final authoritative board render after reopening');assert.equal(f.sounds.length,sounds);assert.equal(f.S.oaq.end.prize,15);
});

test('visible ô ăn quan keeps its normal stone pacing and one terminal result',async()=>{
 const f=oaqFixture(),move=f.ui.oaqMove(1);await f.advance(4599);assert.equal(f.S.busy,true);await f.advance(4600);await move;
 assert.equal(f.sounds.filter(s=>s.type==='stone').length,40);assert.equal(f.sounds.filter(s=>s.type==='kinh').length,1);assert.equal(f.S.oaq.end.prize,15);assert.equal(f.S.busy,false);
});

test('closing and reopening before an ô ăn quan answer skips the cancelled replay',async()=>{
 const f=oaqFixture({latency:1000}),move=f.ui.oaqMove(1);await f.advance(50);f.close();f.S.dlg.open=true;
 await f.advance(999);assert.equal(f.S.busy,true);await f.advance(1000);await move;
 assert.equal(f.S.busy,false);assert.equal(f.S.oaq.end.prize,15);assert.equal(f.sounds.length,0);assert.equal(f.renders.length,2);
});
