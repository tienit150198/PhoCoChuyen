// Owner 22/10 ("nhiều người than k hiển thị bàn phím của game đó, nên nhập này kia k đc"): a tap on a typing field
// focuses it inside the touch and never blurs it (public/js/typing-tap.js); whole-number fields take a pasted
// "1.000.000" and leave out a typed separator. On a small stand-in DOM (no dependencies).
import assert from 'node:assert/strict';
import test from 'node:test';
import {typingTarget,tapFocus,wholeNumber,pastedWhole,typedWhole,installTyping,typingNow} from '../public/js/typing-tap.js';

globalThis.Event??=class{constructor(type,o={}){this.type=type;this.bubbles=!!o.bubbles;}};

/* ---- a tiny DOM ---- */
class El{
  constructor(tag,{type='',step=null,parent=null,typing=false,control=null,own=false}={}){
    Object.assign(this,{tagName:tag,type,step,parentElement:parent,typing,control,own,value:'',disabled:false,readOnly:false,log:[]});
  }
  getAttribute(k){return k==='step'?this.step:null;}
  matches(){return this.typing;}
  closest(sel){
    for(let e=this;e;e=e.parentElement){
      if(sel.startsWith('input:not')&&e.typing)return e;
      if(sel==='label'&&e.tagName==='LABEL')return e;
      if(sel.startsWith('button')&&e.own)return e;
    }
    return null;
  }
  focus(o){this.log.push(['focus',o]);this.doc.activeElement=this;}
  blur(){this.log.push(['blur']);this.doc.activeElement=null;}
  dispatchEvent(e){this.log.push(['event',e.type]);return true;}
}
function doc(){
  const L={},d={activeElement:null,documentElement:{classList:{on:new Set(),contains(c){return this.on.has(c);}}},
    addEventListener(t,f){(L[t]??=[]).push(f);},
    fire(t,e){for(const f of L[t]||[])f(e);return e;},
    el(tag,o){const e=new El(tag,o);e.doc=d;return e;}};
  return d;
}
const touch=(x,y)=>({touches:[{clientX:x,clientY:y}]});
const tapOn=(d,target,{dx=0}={})=>{d.fire('touchstart',{...touch(10,10),target});if(dx)d.fire('touchmove',{...touch(10+dx,10),target});d.fire('touchend',{touches:[],target});};

test('the field a touch means: the field itself (a label focuses its field by its own click)', () => {
  const d=doc(),input=d.el('INPUT',{type:'number',typing:true}),label=d.el('LABEL'),span=d.el('SPAN',{parent:label});
  label.control=input;
  assert.equal(typingTarget(input),input);
  assert.equal(typingTarget(d.el('SPAN',{parent:input})),input);
  assert.equal(typingTarget(span),null);
  assert.equal(typingTarget(d.el('DIV')),null);
  assert.equal(typingTarget(null),null);
});

test('when a touch focuses: not moved, not disabled / read-only, not already typing with its keyboard', () => {
  const d=doc(),f=d.el('INPUT',{typing:true});
  assert.equal(tapFocus(f,{active:null}),true);
  assert.equal(tapFocus(f,{active:f,kbOpen:false}),true);   // focused by script, no keyboard: focus again in the touch
  assert.equal(tapFocus(f,{active:f,kbOpen:true}),false);   // the caret / Dán bubble is the browser's
  assert.equal(tapFocus(f,{active:null,moved:true}),false);
  f.disabled=true;assert.equal(tapFocus(f,{}),false);f.disabled=false;f.readOnly=true;assert.equal(tapFocus(f,{}),false);
  assert.equal(tapFocus(null,{}),false);
});

test('a tap focuses inside the touch; a focused field is focused again, never blurred (2.5.2.4 blur() + focus())', () => {
  const d=doc();installTyping(d);
  const f=d.el('INPUT',{type:'text',typing:true});
  tapOn(d,f);
  assert.equal(d.activeElement,f);
  assert.deepEqual(f.log,[['focus',undefined]]);   // a first focus may scroll the field into view
  f.log=[];tapOn(d,f);
  assert.deepEqual(f.log,[['focus',{preventScroll:true}]]);
  d.documentElement.classList.on.add('kb-open');f.log=[];tapOn(d,f);
  assert.deepEqual(f.log,[]);   // keyboard up: nothing
  const g=d.el('TEXTAREA',{typing:true});tapOn(d,g,{dx:30});
  assert.deepEqual(g.log,[]);   // a finger that slid was scrolling the sheet
  tapOn(d,g,{dx:4});
  assert.deepEqual(g.log,[['focus',undefined]]);
  d.fire('touchend',{touches:[],target:f});   // no touchstart seen (a second finger lifted): left alone
  assert.ok(!f.log.some(x=>x[0]==='blur'));
});

test('whole-number fields: <input type=number> without a decimal step', () => {
  const d=doc();
  assert.equal(wholeNumber(d.el('INPUT',{type:'number'})),true);
  assert.equal(wholeNumber(d.el('INPUT',{type:'number',step:'10'})),true);
  assert.equal(wholeNumber(d.el('INPUT',{type:'number',step:'0.1'})),false);
  assert.equal(wholeNumber(d.el('INPUT',{type:'number',step:'any'})),false);
  assert.equal(wholeNumber(d.el('INPUT',{type:'text'})),false);
  assert.equal(wholeNumber(null),false);
});

test('a paste keeps its digits; a typed separator is left out', () => {
  assert.equal(pastedWhole('1.000.000'),'1000000');
  assert.equal(pastedWhole(' 50.000 xu '),'50000');
  assert.equal(pastedWhole('1,000'),'1000');
  assert.equal(pastedWhole('1200'),null);   // digits only: the browser's own paste
  assert.equal(pastedWhole('xin chào'),null);
  assert.equal(typedWhole('50','.'),'50');
  assert.equal(typedWhole('50',','),'50');
  assert.equal(typedWhole('','50.000'),'50000');
  assert.equal(typedWhole('5','0'),null);
});

test('the listeners: paste "1.000.000" into the bank amount, type "5" "0" "." "0"', () => {
  const d=doc();installTyping(d);
  const amt=d.el('INPUT',{type:'number',typing:true});
  let prevented=0;
  const paste=text=>d.fire('paste',{target:amt,clipboardData:{getData:()=>text},preventDefault(){prevented++;}});
  paste('1.000.000');
  assert.equal(amt.value,'1000000');assert.equal(prevented,1);
  assert.deepEqual(amt.log.at(-1),['event','input']);   // the screen's own input listener reads it (bank-xfer.js)
  paste('2500');assert.equal(prevented,1);   // plain digits: the browser pastes
  amt.value='50';
  const key=data=>d.fire('beforeinput',{target:amt,inputType:'insertText',data,preventDefault(){prevented++;}});
  key('.');assert.equal(amt.value,'50');assert.equal(prevented,2);
  key('0');assert.equal(prevented,2);   // a digit: typed as usual
  const dec=d.el('INPUT',{type:'number',step:'0.5',typing:true});
  d.fire('paste',{target:dec,clipboardData:{getData:()=>'1.5'},preventDefault(){prevented++;}});
  assert.equal(prevented,2);   // a decimal field keeps its point
});

test('typingNow: a text field has focus (auto-opening cards wait: break-gate.js, journey.js, life.js)', () => {
  const body={matches:()=>false},field={matches:()=>true},button={matches:()=>false};
  assert.equal(typingNow({body,activeElement:field}),true);
  assert.equal(typingNow({body,activeElement:button}),false);
  assert.equal(typingNow({body,activeElement:body}),false);
  assert.equal(typingNow({body,activeElement:null}),false);
  assert.equal(typingNow(null),false);
});
