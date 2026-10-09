// "Tất cả" (feedback #290): the plans behind Lắp tất cả / Thuê tất cả / Cả đội vào ca, and the one-at-a-time runner.
// With `--plan` (or `--render`) it reads {kind, ...} JSON on stdin and prints the plan (tests/test_select_all.py feeds it real states).
import assert from 'node:assert/strict';
import {buyAllPlan,quayHave,hireAllPlan,shiftAllPlan,runAll} from '../public/js/v4/select-all.js';

if(process.argv.includes('--render')){   // Sổ tiệm › Nhân viên from a real public state: {career, state, operations}
  let raw='';for await(const chunk of process.stdin)raw+=chunk;
  const x=JSON.parse(raw),{operationsView}=await import('../public/js/operations-ui.js');
  process.stdout.write(operationsView(x.career,x.state.careers[x.career],x.operations,{opsTab:'staff'},x.state));
  process.exit(0);
}
if(process.argv.includes('--plan')){
  let raw='';for await(const chunk of process.stdin)raw+=chunk;
  const x=JSON.parse(raw);
  const out=x.kind==='buy'?buyAllPlan(x.catalog,x.owned,x.place,quayHave(x.journey))
    :x.kind==='hire'?hireAllPlan(x.cands,x.staff,x.slots)
    :shiftAllPlan(x.staff,x.on).map(e=>e.id);
  process.stdout.write(JSON.stringify(out));
  process.exit(0);
}

const items=[{id:'camera',name:'Camera quầy',price:{sap:140}},{id:'bang',name:'Bảng hiệu',price:{sap:600}},{id:'tu',name:'Tủ mát',price:{sap:700}}];
// Cheapest first; what the money there covers is a prefix; owned items never come back.
let p=buyAllPlan(items,[],'sap',800);
assert.deepEqual(p.todo.map(i=>i.id),['camera','bang','tu']);assert.equal(p.total,1440);
assert.deepEqual(p.fit.map(i=>i.id),['camera','bang']);assert.equal(p.fitTotal,740);
p=buyAllPlan(items,['camera'],'sap',10**6);assert.deepEqual(p.fit.map(i=>i.id),['bang','tu']);assert.equal(p.fitTotal,1300);
assert.equal(buyAllPlan(items,[],'sap',100).fit.length,0,'Not even the cheapest: nothing to send');
assert.equal(buyAllPlan(items,[],'kiot',10**6).todo.length,0,'An unknown price is never guessed');
assert.equal(buyAllPlan(null,null,'sap',1).todo.length,0);
// The money the server counts (game/quay.py _have): wallet never below 0, plus an open account.
assert.equal(quayHave({wallet:300,bank:{open:true,balance:500}}),800);
assert.equal(quayHave({wallet:-50,bank:{open:true,balance:500}}),500);
assert.equal(quayHave({wallet:300,bank:{open:false,balance:500}}),300);
assert.equal(quayHave({}),0);
// Hire: only the free places, in list order, at the row's wage.
const cands=[{id:'a',name:'An',ask:20},{id:'b',name:'Bình',ask:22},{id:'c',name:'Chi',ask:18}];
assert.deepEqual(hireAllPlan(cands,0,3).map(c=>[c.id,c.wage]),[['a',20],['b',22],['c',18]]);
assert.deepEqual(hireAllPlan(cands,1,3).map(c=>c.id),['a','b']);
assert.equal(hireAllPlan(cands,3,3).length,0);
assert.deepEqual(hireAllPlan(cands,0,2,c=>c.id==='a'?30:c.ask).map(c=>c.wage),[30,22],'A typed wage is kept');
// Shift: only hired people not already in that state.
const staff=[{id:'x',status:'hired',on_shift:true},{id:'y',status:'hired',on_shift:false},{id:'z',status:'former',on_shift:false}];
assert.deepEqual(shiftAllPlan(staff,true).map(e=>e.id),['y']);assert.deepEqual(shiftAllPlan(staff,false).map(e=>e.id),['x']);
// Runner: strictly one at a time, stops at the first refusal (falsy or throw), counts what the server took.
let live=0,peak=0;const seen=[];
const slow=async n=>{live++;peak=Math.max(peak,live);await new Promise(r=>setTimeout(r,2));live--;seen.push(n);return n!==3;};
let r=await runAll([1,2,3,4],slow);
assert.deepEqual(r,{done:2,total:4,error:null});assert.deepEqual(seen,[1,2,3]);assert.equal(peak,1,'Never two commands at once');
const boom=new Error('Cần 700 xu.');
r=await runAll(['a','b'],async s=>{if(s==='b')throw boom;return {message:'OK'};});
assert.equal(r.done,1);assert.equal(r.error,boom);
r=await runAll([],async()=>true);assert.deepEqual(r,{done:0,total:0,error:null});
console.log('Select-all: cheapest-first equipment within the money, free places only, shift toggles, one-at-a-time runner that stops at a refusal passed.');
