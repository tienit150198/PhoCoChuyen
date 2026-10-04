import assert from 'node:assert/strict';
import {bindRoomCode} from '../public/js/v4/booth-input.js';
class Box extends EventTarget { value=''; }
const box=new Box();let joined=0;bindRoomCode(box,()=>joined++);
const event=(type,values={})=>{const e=new Event(type,{cancelable:true});Object.assign(e,values);box.dispatchEvent(e);};
box.value='ar2k';event('input');assert.equal(box.value,'AR2K');
event('compositionstart');box.value='Ả';event('input',{isComposing:true});assert.equal(box.value,'Ả');
event('keydown',{key:'Enter',isComposing:true});assert.equal(joined,0);
box.value='ar2k';event('compositionend');assert.equal(box.value,'AR2K');
event('keydown',{key:'Enter',isComposing:false});assert.equal(joined,1);
console.log('Room code: R, composition text and IME Enter passed');
