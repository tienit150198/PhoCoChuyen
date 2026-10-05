import assert from 'node:assert/strict';
import fs from 'node:fs';

const path=new URL('../public/js/isometric-movement.js',import.meta.url);
assert.ok(fs.existsSync(path),'the shared mobile movement control exists');
const {normaliseStick,movementAllowed,createMovementController,bootIsometricMovement}=await import(path);
assert.deepEqual(normaliseStick(0,0,40),{x:0,y:0,knobX:0,knobY:0});
assert.equal(normaliseStick(3,0,40).x,0,'small thumb movements stay inside the dead zone');
const diagonal=normaliseStick(80,80,40);
assert.ok(Math.abs(Math.hypot(diagonal.x,diagonal.y)-1)<1e-10,'diagonal speed is radially clamped');
assert.ok(Math.abs(Math.hypot(diagonal.knobX,diagonal.knobY)-1)<1e-10,'the knob stays inside its circular travel');
assert.equal(normaliseStick(0,-40,40).y,-1,'up remains screen up');
assert.equal(normaliseStick(NaN,Infinity,40).x,0,'invalid input cannot move the player');
assert.equal(movementAllowed({available:true,mode:'town'}),true);
for(const cause of ['hidden','modal','menu','driving','paused','destroyed'])assert.equal(movementAllowed({available:true,mode:'town',[cause]:true}),false,cause+' blocks shared movement');
assert.equal(movementAllowed({available:true,mode:'work'}),true);
assert.equal(movementAllowed({available:true,mode:'unknown'}),false);

const input=[],captures=[],releases=[],visuals=[];
const stick=createMovementController({onInput:(x,y)=>input.push({x,y}),onVisual:value=>visuals.push(value),capturePointer:id=>captures.push(id),releasePointer:id=>releases.push(id)});
const bounds={left:10,top:20,width:100,height:100};
assert.equal(stick.pointerDown({pointerId:7,clientX:60,clientY:70,button:0,isPrimary:true},bounds),true);
stick.pointerMove({pointerId:8,clientX:120,clientY:70});
assert.equal(input.length,0,'a second finger cannot take ownership');
stick.pointerMove({pointerId:7,clientX:120,clientY:70});
assert.deepEqual(input.at(-1),{x:1,y:0});
assert.equal(stick.pointerUp({pointerId:8}),false,'another pointer cannot release the stick');
stick.pointerUp({pointerId:7});
assert.deepEqual(input.at(-1),{x:0,y:0});
assert.deepEqual(captures,[7]);assert.deepEqual(releases,[7]);
assert.equal(visuals.at(-1).active,false);
assert.equal(stick.keyDown({key:'ArrowUp'}),true);
stick.keyDown({key:'d'});
assert.ok(input.at(-1).x>0&&input.at(-1).y<0);
assert.ok(Math.abs(Math.hypot(input.at(-1).x,input.at(-1).y)-1)<1e-10);
stick.keyUp({key:'d'});assert.deepEqual(input.at(-1),{x:0,y:-1});
stick.enable(false);assert.deepEqual(input.at(-1),{x:0,y:0});
assert.equal(stick.keyDown({key:'ArrowUp'}),false,'blocked controls do not resume stale keys');
stick.enable(true);stick.keyDown({key:'s'});stick.reset();assert.deepEqual(input.at(-1),{x:0,y:0});
stick.pointerDown({pointerId:9,clientX:120,clientY:70,button:0},bounds);stick.destroy();
assert.deepEqual(input.at(-1),{x:0,y:0});assert.deepEqual(releases,[7,9]);
assert.equal(stick.pointerDown({pointerId:10,clientX:120,clientY:70,button:0},bounds),false);

// Exercise the actual binding against small event targets, including DOM lifecycle changes.
class Element extends EventTarget {
  children=[];style={};dataset={};hidden=false;className='';attributes={};
  classList={contains:name=>this.className.split(' ').includes(name),toggle:(name,on)=>{this.className=this.className.split(' ').filter(x=>x!==name).concat(on?[name]:[]).join(' ');}};
  append(...nodes){this.children.push(...nodes);nodes.forEach(n=>n.parentNode=this);}
  setAttribute(k,v){this.attributes[k]=v;}
  getBoundingClientRect(){return bounds;}
  setPointerCapture(id){this.captured=id;}
  releasePointerCapture(){this.captured=null;}
  remove(){this.parentNode.children=this.parentNode.children.filter(n=>n!==this);}
}
const root=new Element(),stage=new Element(),doc=new EventTarget(),win=new EventTarget(),media=new EventTarget();
Object.assign(media,{matches:true,addListener:f=>media.addEventListener('change',f),removeListener:f=>media.removeEventListener('change',f)});
Object.assign(doc,{documentElement:root,hidden:false,fullscreenElement:null,createElement:()=>new Element(),getElementById:id=>id==='stage'?stage:null,querySelector:()=>doc.modal||doc.driving||null});
win.matchMedia=()=>media;
let observer;class Observer {constructor(cb){this.callback=cb;observer=this;}observe(){}disconnect(){this.disconnected=true;}trigger(){this.callback();}}
const previous={document:globalThis.document,window:globalThis.window,MutationObserver:globalThis.MutationObserver};
Object.assign(globalThis,{document:doc,window:win,MutationObserver:Observer});
const moves=[],world={mode:'town',setMovementInput:(x,y)=>moves.push({x,y})},env={world};
const ui=bootIsometricMovement(()=>env),base=ui.element.children.find(n=>n.className.includes('iso-stick-base'));
assert.equal(ui.element.parentNode,stage,'the joystick survives HUD innerHTML replacements');
function pointer(type,id=1,x=120,y=70){const e=new Event(type,{cancelable:true});Object.assign(e,{pointerId:id,clientX:x,clientY:y,button:0,isPrimary:true});base.dispatchEvent(e);}
function expectReset(trigger,label){pointer('pointerdown');assert.equal(moves.at(-1).x,1);trigger();assert.deepEqual(moves.at(-1),{x:0,y:0},label);}
expectReset(()=>win.dispatchEvent(new Event('blur')),'blur resets movement');
expectReset(()=>{doc.modal={};observer.trigger();},'opening a dialog resets movement');
assert.equal(ui.element.hidden,true);doc.modal=null;observer.trigger();
expectReset(()=>{root.className='menu-open';observer.trigger();},'opening the menu resets movement');root.className='';observer.trigger();
expectReset(()=>{doc.hidden=true;doc.dispatchEvent(new Event('visibilitychange'));},'hiding the page resets movement');doc.hidden=false;doc.dispatchEvent(new Event('visibilitychange'));
expectReset(()=>{world.mode='work';win.dispatchEvent(new Event('mnl:iso-mode'));},'changing scene resets movement');
assert.equal(ui.element.dataset.mode,'work');
expectReset(()=>{doc.driving={};doc.dispatchEvent(new Event('fullscreenchange'));},'delivery fullscreen retains its own controls');doc.driving=null;doc.dispatchEvent(new Event('fullscreenchange'));
expectReset(()=>pointer('pointercancel'),'cancelled touches reset movement');
expectReset(()=>{media.matches=false;media.dispatchEvent(new Event('change'));},'changing to desktop removes mobile movement');
assert.equal(ui.element.hidden,true);media.matches=true;media.dispatchEvent(new Event('change'));
expectReset(()=>ui.destroy(),'destroying the control resets movement');
assert.equal(stage.children.length,0);assert.equal(observer.disconnected,true);
Object.assign(globalThis,previous);
console.log('isometric movement: radial analogue input, pointer ownership, keyboard fallback and lifecycle resets passed');
