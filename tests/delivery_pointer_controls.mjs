import assert from 'node:assert/strict';
import * as controls from '../public/js/careers/delivery_controls.js';
assert.equal(typeof controls.holdPointer,'function');
class Element {
  events={};captured=new Set();
  addEventListener(name,fn){this.events[name]=fn;}
  setPointerCapture(id){this.captured.add(id);}
  hasPointerCapture(id){return this.captured.has(id);}
  releasePointerCapture(id){this.captured.delete(id);this.fire('lostpointercapture',id);}
  fire(name,id,x=0,y=0){this.events[name]?.({pointerId:id,clientX:x,clientY:y,button:0,preventDefault(){}});}
}
const stick=new Element(),events=[];
let enabled=true;
const reset=controls.holdPointer(stick,{enabled:()=>enabled,
  start:()=>events.push('start'),move:(e,origin)=>events.push([e.clientX-origin.x,e.clientY-origin.y]),end:()=>events.push('end')});
stick.fire('pointerdown',7,70,90);
assert.deepEqual(events,['start'],'touch begins neutrally even away from centre');
stick.fire('pointerdown',8,20,20);stick.fire('pointermove',8,40,40);stick.fire('pointerup',8);
assert.deepEqual(events,['start'],'another finger cannot steal or release the stick');
stick.fire('pointermove',7,85,60);assert.deepEqual(events.at(-1),[15,-30]);
stick.fire('pointercancel',7);assert.equal(events.at(-1),'end');assert.equal(stick.captured.size,0);
stick.fire('pointerdown',9);reset();assert.equal(events.filter(x=>x==='end').length,2,'blur reset releases capture exactly once');
stick.fire('pointermove',9,90,90);assert.equal(events.at(-1),'end','no stale input after reset');
stick.fire('pointerdown',10);stick.fire('lostpointercapture',10);assert.equal(events.at(-1),'end');
enabled=false;const before=events.length;stick.fire('pointerdown',11);assert.equal(events.length,before);
console.log('courier pointer ownership, neutral origin, cancellation, capture loss and external reset passed');
