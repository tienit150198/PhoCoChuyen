import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../public/js/app.js',import.meta.url),'utf8');
const start=source.indexOf("{const d=$('#sheet'),HANDLE=");
const end=source.indexOf("$('#sheet').addEventListener('close'",start);
assert.ok(start>0&&end>start);
function fixture(){
  const events={},pending=[],globalEvents={},docEvents={};
  const sheet={open:true,scrollTop:0,style:{},closed:0,captured:null,addEventListener(n,f){events[n]=f;},dispatchEvent(){this.closed++;},setPointerCapture(id){this.captured=id;},hasPointerCapture(id){return this.captured===id;},releasePointerCapture(){this.captured=null;}};
  vm.runInNewContext(source.slice(start,end),{$:()=>sheet,layout:()=> 'phone',setTimeout:f=>{pending.push(f);return pending.length;},clearTimeout:id=>{pending[id-1]=()=>{};},Event:class{},window:{addEventListener(n,f){globalEvents[n]=f;}},document:{hidden:true,addEventListener(n,f){docEvents[n]=f;}}});
  const head={getBoundingClientRect:()=>({top:20})};
  const target={closest:selector=>selector.startsWith('.sheet-head')?head:null};
  const event=(y,t=0,pointerId=1)=>({target,pointerType:'touch',clientY:y,timeStamp:t,pointerId,isPrimary:pointerId===1});
  return {sheet,events,pending,event,globalEvents,docEvents};
}
{
  const {sheet,events,pending,event}=fixture();
  events.pointerdown(event(90));events.pointermove(event(240,20));events.pointerup(event(240,40));
  pending.forEach(f=>f());assert.equal(sheet.closed,0,'scrolling the header body must not dismiss');
}
{
  const {sheet,events,pending,event}=fixture();
  events.pointerdown(event(25));events.pointermove(event(150,20));events.pointercancel(event(150,30));
  pending.forEach(f=>f());assert.equal(sheet.closed,0,'native pan cancellation must not dismiss');
  assert.equal(sheet.style.transform,'');
}
{
  const {sheet,events,pending,event}=fixture();
  events.pointerdown(event(25));events.pointermove(event(150,20));events.pointerup(event(150,200));
  pending.forEach(f=>f());assert.equal(sheet.closed,1,'an intentional handle drag still dismisses');
}
{
  const {sheet,events,event}=fixture();events.pointerdown(event(25));
  assert.equal(sheet.captured,1,'the handle owns its pointer until release outside the sheet');
  events.pointermove(event(160));events.lostpointercapture?.(event(160));
  assert.equal(sheet.style.transform,'','lost capture must restore the sheet instead of leaving only backdrop');
}
{
  const {sheet,events,event,globalEvents}=fixture();events.pointerdown(event(25));events.pointermove(event(160));
  globalEvents.blur?.();assert.equal(sheet.style.transform,'','losing window focus clears partial drag');
}
{
  const {sheet,events,pending,event}=fixture();events.pointerdown(event(25));events.pointermove(event(160));events.pointerup(event(160,200));
  sheet.resetGesture?.();pending.forEach(f=>f());
  assert.equal(sheet.closed,0,'opening a new view cancels dismissal scheduled by the old view');
  assert.equal(sheet.style.transform,'');
  assert.match(source,/function openSheet\(view,data=\{\}\)\{\$\('#sheet'\)\.resetGesture\?\.\(\)/,'real openSheet resets stale motion before rendering');
}
{
  const {sheet,events,pending,event}=fixture();events.pointerdown(event(25));events.pointermove(event(160,20,2));events.pointerup(event(160,200,2));pending.forEach(f=>f());
  assert.equal(sheet.closed,0,'another finger cannot dismiss the first finger handle gesture');
}
console.log('Sheet gestures: scroll, cancel, dismissal, lost capture, focus, reopen and multi-touch pass.');
