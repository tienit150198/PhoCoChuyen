import assert from 'node:assert/strict';
import {createSiteBubbles} from '../public/js/v4/site-presence.js';
import {renderVenue,projectVenue} from '../public/js/scenes/venue-place.js';
let now=0,serial=0,wakes=0;const timers=new Map();
const bubbles=createSiteBubbles({now:()=>now,wake:()=>wakes++,setTimer:(fn,ms)=>{const id=++serial;timers.set(id,{fn,at:now+ms});return id;},clearTimer:id=>timers.delete(id)});
bubbles.show('me','hello');assert.equal(bubbles.get()[0].text,'hello');assert.equal(timers.size,1);
now=100;bubbles.show('other','👋');assert.equal(timers.size,1,'only one timer for all speakers');
now=200;bubbles.show('me','new speech');assert.equal(bubbles.get().find(b=>b.pid==='me').text,'new speech');assert.equal(timers.size,1);
now=8100;const first=[...timers.entries()][0];timers.delete(first[0]);first[1].fn();assert.deepEqual(bubbles.get().map(b=>b.pid),['me']);assert.equal(timers.size,1);
now=8200;const second=[...timers.entries()][0];timers.delete(second[0]);second[1].fn();assert.equal(bubbles.get().length,0);assert.equal(timers.size,0);assert.ok(wakes>=5);
bubbles.show('me','left room');bubbles.clear();assert.equal(timers.size,0);assert.equal(bubbles.get().length,0);
bubbles.show('other','left and rejoined');bubbles.retain(new Set(['me']));assert.equal(bubbles.get().length,0);assert.equal(timers.size,0);
// Canvas uses plain text; the supplied live position anchors a bubble every paint.
const text=[],ctx=new Proxy({measureText:t=>({width:String(t).length*6}),fillText:(t,x,y)=>text.push({t,x,y})},{get:(o,k)=>k in o?o[k]:(()=>{})});
const canvas={getContext:()=>ctx},room={width:460,height:360,entry:{x:230,y:325},props:[],stations:[]},state={x:230,y:325};
renderVenue(canvas,room,state,{bubbles:[{x:250,y:300,text:'<hello>'}]});let drawn=text.find(t=>t.t==='<hello>');assert.ok(drawn,'bubble text rendered as literal canvas text');assert.equal(drawn.x,projectVenue({x:250,y:300}).x);
text.length=0;renderVenue(canvas,room,state,{bubbles:[{x:290,y:300,text:'👋'}]});drawn=text.find(t=>t.t==='👋');assert.equal(drawn.x,projectVenue({x:290,y:300}).x,'bubble follows a changed walking position');
text.length=0;renderVenue(canvas,room,state,{bubbles:[{x:250,y:300,text:'speech'},{x:250,y:300,text:'👋'}]});assert.notEqual(text.find(t=>t.t==='speech').y,text.find(t=>t.t==='👋').y,'speakers sharing the entrance have readable stacked bubbles');
console.log('site bubbles: one timer, replace/expiry/cleanup, plain text and live position anchors passed');
