import assert from 'node:assert/strict';
import {priceInteger,cloneMenu,selectDishes,menuPayload,filterDishes,pricePreview,restockQuote,createQuayPoller,focusSnapshot,restoreInputFocus,syncDraftValue} from '../public/js/v4/quay-business-ui.js';
import {rideSVG,turnChoices,pathOf} from '../public/js/v4/quay-ride.js';
const rows=Array.from({length:12},(_,i)=>({id:`dish${i}`,name:i?'Trà sữa '+i:'Đậu đỏ',base:20,cost:8}));
const original={on:['dish0'],p:{dish0:20}},draft=cloneMenu(original);selectDishes(draft,rows);
assert.equal(draft.on.length,12,'Full catalogue can be selected');assert.deepEqual(original,{on:['dish0'],p:{dish0:20}},'Draft does not mutate server state');
draft.p.dish0='500';assert.equal(menuPayload(draft,rows).p.dish0,500,'Typed price is parsed at submit');
draft.p.dish0='';assert.equal(menuPayload(draft,rows),null,'An unfinished number is retained as a draft and blocks saving');
for(const bad of ['0','-1','1.2','1e4','1000001',NaN])assert.equal(priceInteger(bad),null);
assert.equal(priceInteger('1000000'),1000000);assert.equal(filterDishes(rows,'dau do')[0].id,'dish0');assert.equal(filterDishes(rows,'TRA SUA').length,11);
assert.equal(pricePreview(5,8,20).margin,-3);assert.equal(pricePreview(500,8,20).kind,'dear');assert.equal(pricePreview(20,8,20).margin,12);
assert.deepEqual(restockQuote({dish0:'5',dish1:'0'},rows),{items:{dish0:5},count:5,total:40});assert.equal(restockQuote({dish0:'2.5'},rows),null);assert.equal(restockQuote({dish0:20000,dish1:1},rows),null);
// Focus restoration retains the caret and prevents the browser from scrolling the dialog to its top.
const snapshot=focusSnapshot({id:'qy-search-x',value:'tra sua',selectionStart:3,selectionEnd:3});let focused,selection;
restoreInputFocus({querySelector:()=>({focus:opts=>focused=opts,setSelectionRange:(...v)=>selection=v})},snapshot);
assert.deepEqual(focused,{preventScroll:true});assert.deepEqual(selection,[3,3]);
// Slow requests and close/reopen cycles must never create parallel polling loops.
let timers=new Map(),seq=0,calls=0,resolve,visible=true,errors=[];
const poll=createQuayPoller({delay:1,active:()=>visible,refresh:()=>{calls++;return new Promise(r=>resolve=r);},failed:x=>errors.push(x),setTimer:(fn,delay)=>{assert.ok(delay>=5000);timers.set(++seq,fn);return seq;},clearTimer:id=>timers.delete(id)});
const tick=()=>{const [id,fn]=timers.entries().next().value;timers.delete(id);return fn();};
poll.start();poll.start();assert.equal(timers.size,1);const pending=tick();assert.equal(calls,1);assert.equal(timers.size,0);
poll.stop();poll.start();await tick();assert.equal(calls,1,'Reopen waits for the previous in-flight request');resolve();await pending;assert.equal(timers.size,1);
visible=false;await tick();assert.equal(calls,1,'Hidden dialogs do not fetch');poll.stop();assert.equal(timers.size,0,'Closing cancels polling');
assert.deepEqual(turnChoices(['R']).map(x=>x.k),['L','S','R'],'Controls remain relative to the driver');
assert.match(rideSVG(['L','S','R'],[]),/RẼ TRÁI/);assert.match(rideSVG(['L','S','R'],['L']),/ĐI THẲNG/);assert.deepEqual(pathOf(['L']),[[0,0],[0,-40],[-40,-40]]);
console.log('Quay UI: unlimited catalogue selection, typed prices, independent drafts, margin/restock quotes, focus preservation, bounded non-overlapping polling and driver-relative turns passed.');

const editedInput={value:"3"};syncDraftValue(editedInput,"");assert.equal(editedInput.value,"","Successful restock clears the live input property");
let writes=0;const liveInput={get value(){return "25"},set value(v){writes++}};syncDraftValue(liveInput,"25");assert.equal(writes,0,"Polling leaves unchanged edited values and caret intact");
