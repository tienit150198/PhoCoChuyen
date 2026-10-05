import assert from 'node:assert/strict';
import {stageFullscreen} from '../public/js/careers/delivery_fullscreen.js';
function fixture(native=true,reject=false){
 const classes=()=>{const s=new Set();return {toggle(k,on){on?s.add(k):s.delete(k);},contains:k=>s.has(k)};};
 const handlers={},host={classList:classes()},button={textContent:'',setAttribute(){},focus(){}};
 const doc={fullscreenElement:null,addEventListener(k,fn){handlers[k]=fn;},async exitFullscreen(){this.fullscreenElement=null;handlers.fullscreenchange();}};
 const stage={isConnected:true,classList:classes(),closest:()=>host};let resets=0,resizes=0;
 if(native)stage.requestFullscreen=async()=>{if(reject)throw Error('unavailable');doc.fullscreenElement=stage;handlers.fullscreenchange();};
 const controller=stageFullscreen(stage,button,{doc,reset:()=>resets++,resize:()=>resizes++,text:x=>x});
 return {controller,stage,doc,host,button,get resets(){return resets;},get resizes(){return resizes;}};
}
for(const [native,reject] of [[true,false],[false,false],[true,true]]){
 const f=fixture(native,reject);await f.controller.toggle();
 assert(f.controller.active);assert(f.stage.classList.contains('dd-expanded'));assert(f.host.classList.contains('dd-expanded-host'));
 assert.match(f.button.textContent,/Thu nhỏ/);assert(f.resets>0&&f.resizes>0);
 await f.controller.exit();assert(!f.controller.active);assert(!f.host.classList.contains('dd-expanded-host'));assert.equal(f.doc.fullscreenElement,null);
}
const escape=fixture();await escape.controller.toggle();await escape.doc.exitFullscreen();assert(!escape.controller.active,'browser Escape restores normal layout');
const pending=fixture();let resolve;
pending.stage.requestFullscreen=()=>new Promise(r=>{resolve=()=>{pending.doc.fullscreenElement=pending.stage;r();};});
const opening=pending.controller.toggle();await pending.controller.exit();resolve();await opening;
assert.equal(pending.doc.fullscreenElement,null,'closing while request pending must not reopen fullscreen');
assert(!pending.controller.active);
console.log('courier fullscreen: native, fallback, Escape and pending-close lifecycle passed');
