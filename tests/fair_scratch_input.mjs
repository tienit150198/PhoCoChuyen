import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../public/js/v4/fair-scratch.js',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'').replace(/export /g,'');
function fixture(){
 const handlers={},stats={rects:0,writes:0};let text='0%';
 const pct={get textContent(){return text;},set textContent(v){text=v;stats.writes++;}};
 const noop=()=>{},context=new Proxy({createLinearGradient:()=>({addColorStop:noop})},{get:(o,k)=>o[k]||noop});
 const cv={getBoundingClientRect(){stats.rects++;return {left:0,top:0,width:300,height:240};},getContext:()=>context,addEventListener:(k,v)=>handlers[k]=v,setPointerCapture:noop};
 const S={dlg:{open:true,querySelector:s=>s==='.fh-xs-cv'?cv:s==='.fh-xs-pct'?pct:null}};
 const ui=new Function('tr',source+';return setup;')(s=>s)({S,F:()=>({scratch:{}}),render:noop,sfx:noop,pick:a=>a[0],reduce:()=>true});
 S.xs.t={id:1,prize:0};ui.mount();stats.rects=stats.writes=0;
 const event=(id,x,y=40)=>({pointerId:id,clientX:x,clientY:y,button:0,preventDefault:noop});
 return {S,ui,handlers,stats,event};
}
test('scratch batches coalesced samples into one layout read and one progress write without dropping points',()=>{
 const f=fixture();f.handlers.pointerdown(f.event(1,20));f.stats.rects=f.stats.writes=0;
 f.handlers.pointermove({...f.event(1,90),getCoalescedEvents:()=>[30,40,50,60,70,80,90].map(x=>f.event(1,x))});
 assert.equal(f.S.xs.strokes[0].length,8,'all input samples remain available for replay');
 assert.equal(f.stats.rects,1,'one geometry read per dispatched event');
 assert.equal(f.stats.writes,1,'only the final coverage percentage is written');
});
test('second finger cannot replace or end the captured scratch gesture',()=>{
 const f=fixture();f.handlers.pointerdown(f.event(1,20));f.handlers.pointerdown(f.event(2,200));
 f.handlers.pointermove(f.event(2,240));f.handlers.pointerup(f.event(2,240));f.handlers.pointermove(f.event(1,40));
 assert.deepEqual(f.S.xs.strokes,[[[20/300,40/240],[40/300,40/240]]]);
 f.handlers.pointerup(f.event(1,40));f.handlers.pointermove(f.event(1,50));assert.equal(f.S.xs.strokes[0].length,2);
});
