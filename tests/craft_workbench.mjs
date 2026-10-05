import assert from 'node:assert/strict';
import {RECIPES,SIZES,pathFor,sampledPath,traceStart,tracePoint,traceKeyboard,newDraft,stepComplete,nextStep,craftWork,draftKey,restoreDraft,reconcileDraft,saveDraft,submitCraft} from '../public/js/v4/craft-gestures.js';
import {craftedArt} from '../public/js/v4/craft-art.js';

const memory=new Map(),storage={setItem:(k,v)=>memory.set(k,v),getItem:k=>memory.get(k),removeItem:k=>memory.delete(k)};
const d=newDraft({kind:'teddy',color:'rose',pattern:'flower'});
assert.equal(nextStep(d),false,'Cannot skip measurement');
assert.equal(craftWork(d),null,'Cannot submit an unfinished object');
d.measure=[24,30];assert.equal(nextStep(d),true);
for(const step of ['cut','sew']){
 const path=sampledPath(pathFor(d));let trace=traceStart(path);
 trace=tracePoint(trace,path,path[0]);const before=trace.count;
 trace=tracePoint(trace,path,path.at(-1));assert.ok(trace.count<path.length,'Teleport cannot finish a path');
 trace=traceStart(path);
 for(const p of path)trace=tracePoint(trace,path,p);
 assert.equal(trace.count,path.length,`Pointer ${step} completes with continuous intermediate points`);
 // A keyboard user follows each successive next point; no special finish shortcut.
 let keyboard=tracePoint(traceStart(path),path,path[0]);
 for(let i=0;i<3000&&keyboard.count<path.length;i++){
  const target=path[keyboard.count],dx=target[0]-keyboard.cursor[0],dy=target[1]-keyboard.cursor[1];
  keyboard=traceKeyboard(keyboard,path,Math.abs(dx)>Math.abs(dy)?dx>0?'ArrowRight':'ArrowLeft':dy>0?'ArrowDown':'ArrowUp');
 }
 assert.equal(keyboard.count,path.length,`Keyboard ${step} can complete actual tracing`);
 d.trace[step]=trace;assert.equal(nextStep(d),true);
 assert.ok(before>0);
}
assert.equal(nextStep(d),false,'Stuffing requires all four zones');d.stuffed=[0,1,2,3];assert.equal(nextStep(d),true);
d.marks=[[.5,.52]];assert.equal(stepComplete(d),false,'Finish requires face and bow');d.face=[0,1,2,3];assert.equal(stepComplete(d),true);
assert.deepEqual(craftWork(d),{v:1,steps:RECIPES.teddy,size:[24,30],marks:[[.5,.52]]});
const alice=draftKey('alice','teddy'),bob=draftKey('bob','teddy');assert.notEqual(alice,bob);assert.equal(draftKey(null,'teddy'),null);
assert.equal(saveDraft(storage,alice,d),true);assert.equal(storage.getItem(bob),undefined);assert.deepEqual(restoreDraft(storage.getItem(alice),d).marks,d.marks);
const colored=JSON.stringify({...d,color:'mint',pattern:'stars'});
assert.equal(reconcileDraft(colored,{kind:'teddy',color:'rose',pattern:'plain'}).color,'mint','Reload defaults preserve saved material');
assert.equal(reconcileDraft(colored,{kind:'teddy',color:'rose',pattern:'plain'}).pattern,'stars','Reload defaults preserve saved pattern');
const recolored=reconcileDraft(colored,{kind:'teddy',color:'sky',pattern:'plain',materialChanges:{color:true}});
assert.equal(recolored.color,'sky','Explicit selection changes material');assert.equal(recolored.pattern,'stars');assert.equal(recolored.step,d.step);assert.deepEqual(recolored.marks,d.marks);
assert.equal(restoreDraft('{oops',d),null);assert.equal(restoreDraft(JSON.stringify({...d,step:3,done:[]}),d),null);
assert.equal(saveDraft({setItem(){throw Error('blocked');}},alice,d),false,'Storage denied does not crash');
await submitCraft({cmd:async()=>null},d,'cash',{storage,key:alice});assert.ok(storage.getItem(alice),'Failure retains draft');
await assert.rejects(()=>submitCraft({cmd:async()=>{throw Error('offline');}},d,'cash',{storage,key:alice}));assert.ok(storage.getItem(alice),'Disconnect retains draft');
let sent;await submitCraft({cmd:async(action,payload)=>{sent=[action,payload];return {ok:true};}},d,'cash',{storage,key:alice});assert.equal(storage.getItem(alice),undefined);assert.equal(sent[0],'jr_out_craft');assert.deepEqual(sent[1].work,craftWork(d));
for(const kind of ['pot','bracelet','card']){
 const draft=newDraft({kind});
 for(const step of RECIPES[kind]){if(pathFor(draft)){const path=sampledPath(pathFor(draft));draft.trace[step]=path.reduce((t,p)=>tracePoint(t,path,p),traceStart(path));}else if(step==='beads')draft.placed=[0,1,2,3,4,5,6,7];else draft.marks=[[.4,.6]];assert.ok(nextStep(draft),`${kind}/${step} completes`);}
 assert.deepEqual(craftWork(draft).size,SIZES[kind]);assert.match(craftedArt({...draft,work:craftWork(draft)},[{id:'rose',hex:'#de829d'}]),/<svg/);
}
console.log('Craft workbench: measured dimensions, continuous traces, keyboard paths, no skipped steps, draft isolation, disconnected save and shared artwork passed.');
