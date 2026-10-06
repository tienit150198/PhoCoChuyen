import assert from 'node:assert/strict';
import {bindRoomCode,codeKeys} from '../public/js/v4/booth-input.js';
class Box extends EventTarget { value=''; }
const box=new Box();let joined=0;bindRoomCode(box,()=>joined++);
const event=(type,values={})=>{const e=new Event(type,{cancelable:true});Object.assign(e,values);box.dispatchEvent(e);};
box.value='ar2k';event('input');assert.equal(box.value,'AR2K');
event('compositionstart');box.value='Ả';event('input',{isComposing:true});assert.equal(box.value,'Ả');
event('keydown',{key:'Enter',isComposing:true});assert.equal(joined,0);
box.value='ar2k';event('compositionend');assert.equal(box.value,'AR2K');
event('keydown',{key:'Enter',isComposing:false});assert.equal(joined,1);
// Telex turned code letters into accents ("không gõ được chữ R"): each mark goes back to its key.
box.value='Ả2K';event('input');assert.equal(box.value,'AR2K','A then R in Telex is Ả');
for(const [typed,code] of [['ả2k','AR2K'],['Á7','AS7'],['À9','AF9'],['Ã3','AX3'],['Ạ4','AJ4'],['Ă2','AW2'],['Đ5','DD5'],['Â6','AA6'],['Ấ','AAS'],['Ư2','W2'],['Ê2K','EE2K'],['ab-c d','ABCD'],['ẢẢẢ','ARAR']])
  assert.equal(codeKeys(typed),code,typed);
console.log('Room code: R, Telex marks, composition text and IME Enter passed');
