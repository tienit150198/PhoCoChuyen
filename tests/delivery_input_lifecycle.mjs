// Exercise the real event/arrival handlers in isolation from Canvas and the DOM.
import assert from 'node:assert/strict';
import fs from 'node:fs';
const src=fs.readFileSync(new URL('../public/js/careers/delivery_drive.js',import.meta.url),'utf8');
const stopsSrc=src.slice(src.indexOf('function stops(dt){'),src.indexOf('/* ---------------------------------------------------------------- light, colours */'));
let arrivals=0;
const S={v:.75,stopDone:true,stopX:14,stopY:78,still:0,sending:false,x:14,y:78,at:'start',
  world:{houses:[],marks:{target:{id:'target',gate:{x:54,y:80}}}},opts:{target:'target',arrive:()=>{arrivals++;}}};
const stops=new Function('S','HW','tr','say',stopsSrc+';return stops;')(S,5,s=>s,()=>{});
for(let i=0;i<3200;i++){S.x+=.75/60;stops(1/60);}
assert.equal(arrivals,0,'moving slowly must not complete a delivery');
S.v=0;for(let i=0;i<120;i++)stops(1/60);
assert.equal(arrivals,1,'creeping to the destination must re-arm parking');
S.v=-2;S.still=.3;stops(1/60);
assert.equal(S.still,0,'reversing is movement, not parking');
const keySrc=src.slice(src.indexOf('const KEYS='),src.indexOf('function panel(name){'));
const state={keys:{}};
const key=new Function('S','live','panel',keySrc+';return key;')(state,()=>true,()=>{});
const event=(type,button)=>({code:'Space',type,preventDefault(){},target:{closest:s=>s==='button:not([data-dd])'&&button?{}:null}});
key(event('keydown',false));key(event('keyup',true));
assert.equal(state.keys.d,false,'releasing over toolbar must release the held brake');
console.log('courier lifecycle: slow arrival, reversing and keyboard focus release passed');
