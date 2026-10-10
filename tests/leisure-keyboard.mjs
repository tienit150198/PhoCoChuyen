import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import * as geometry from '../public/js/pixel/place-geometry.js';
import {createMovementController} from '../public/js/isometric-movement.js';
import {createLeisureActors} from '../public/js/isometric/leisure-actors.js';
import {createLeisurePresence} from '../public/js/isometric/leisure-presence.js';

const source=readFileSync(new URL('../public/js/pixel/places.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export \{.*\} from .*\r?\n/gm,'').replace(/^export /gm,'');

// Exercise the production dialog's registered listeners and actual simulation.
// DOM nodes, raster rendering and scheduling are deterministic boundary services.
function fixture(kind='boat',next=0){
 const doc=Object.assign(new EventTarget(),{hidden:false,activeElement:null,body:{append(){}}});
 const raster=[];
 const context2d=new Proxy({}, {get:(_,name)=>(...args)=>{raster.push({name,args});},set:()=>true});
 class Element extends EventTarget{
  constructor(tag='div'){super();this.tagName=tag.toUpperCase();this.style={};this.dataset={};this.isConnected=true;}
  setAttribute(){}getBoundingClientRect(){return {width:640,height:400,left:0,top:0};}getContext(){return context2d;}
  focus(){doc.activeElement=this;}closest(selector){return selector==='button'&&this.tagName==='BUTTON'?this:null;}
  showModal(){this.open=true;}close(){this.open=false;this.dispatchEvent(new Event('close'));}remove(){this.isConnected=false;}
  setPointerCapture(){}releasePointerCapture(){}
 }
 const selectors=['canvas','[data-status]','[data-play]','[data-leave]','[data-record]','[data-stick]','[data-knob]','[data-close]'];
 const elements=Object.fromEntries(selectors.map(selector=>[selector,new Element(['[data-play]','[data-leave]','[data-close]'].includes(selector)?'button':selector==='canvas'?'canvas':'div')]));
 const dialog=new Element('dialog');dialog.querySelector=selector=>elements[selector];doc.createElement=()=>dialog;
 const calls=[],frames=new Map();let id=0;
 const context=vm.createContext({console,Math,Date,Set,Map,...geometry,createMovementController,createLeisureActors,
  leisurePresence:createLeisurePresence(),document:doc,window:Object.assign(new EventTarget(),{innerWidth:640,innerHeight:400,devicePixelRatio:1}),
  getComputedStyle:()=>({fontFamily:'sans-serif'}),performance:{now:()=>1000},requestAnimationFrame:fn=>{frames.set(++id,fn);return id;},cancelAnimationFrame:id=>frames.delete(id),
  lookOf:()=>({}),getCharacterStamp:()=>({canvas:{}}),drawRowboat(){},drawSwimmer(){}});
 vm.runInContext(source+'\nglobalThis.open=openPixelPlace;',context);
 const backdrop={};
 const scene=context.open(kind,{api:{state:{journey:{}},command:async(name,payload)=>{calls.push({name,payload});return {message:'Saved',leisure:{boat_laps:1}};}},leisureArt:{background:()=>backdrop,character:()=>({canvas:{}})}});
 const g=geometry.placeGeometry(kind);Object.assign(scene.play.state,{phase:kind,x:g.entry[0],y:g.entry[1],next,moving:true,round:{id:'fixture',entry:g.entry,checkpoints:[[144,62],[260,70],[252,142],g.entry]}});scene.play.reset();
 return {scene,calls,elements,raster,frames,backdrop,flush(){const pending=[...frames];frames.clear();pending.forEach(([,fn])=>fn(1040));},space(selector,repeat=false){
  const target=elements[selector];target.focus();const event=new Event('keydown',{cancelable:true});Object.assign(event,{key:' ',repeat});Object.defineProperty(event,'target',{value:target});dialog.dispatchEvent(event);return event;
 },click(selector){elements[selector].dispatchEvent(new Event('click'));}};
}

for(const kind of ['boat','pool'])for(const next of [0,4])test(`Space on ${kind} physical exit at ${next} legacy checkpoints preserves native activation`,async()=>{
 const h=fixture(kind,next),exit=kind==='boat'?'[data-play]':'[data-leave]';
 try{
  for(const repeat of [false,true])assert.equal(h.space(exit,repeat).defaultPrevented,false,'button Space must not be swallowed by the scene shortcut');
  assert.equal(h.scene.play.state.phase,kind);assert.deepEqual(h.calls,[],'Space keydown never invokes finish');
  h.click(exit);await Promise.resolve();
  assert.equal(h.scene.play.state.phase,'walk','normal click listener exits physically at the entry');assert.equal(h.scene.play.state.round,null);assert.deepEqual(h.calls,[],'exit awards no achievement');
 }finally{h.scene.destroy();}
});

test('each outdoor repaint clears old actors before drawing the backdrop',()=>{
 const h=fixture();
 try{
  h.flush();
  const images=h.raster.map((call,i)=>call.name==='drawImage'&&call.args[0]===h.backdrop?i:-1).filter(i=>i>=0);
  assert.ok(images.length>=2,'initial and input-reset frames both render');
  let previous=-1;
  for(const i of images){
   assert.ok(h.raster.slice(previous+1,i).some(call=>call.name==='clearRect'&&call.args[2]===h.elements.canvas.width&&call.args[3]===h.elements.canvas.height),'transparent or restored backdrops cannot retain earlier character/fish frames');
   previous=i;
  }
 }finally{h.scene.destroy();}
});

test('restoring a lost canvas wakes a fresh scene frame even while idle',()=>{
 const h=fixture();
 try{h.flush();assert.equal(h.frames.size,0);h.elements.canvas.dispatchEvent(new Event('contextrestored'));assert.equal(h.frames.size,1);}
 finally{h.scene.destroy();}
});

test('Space on the main and close buttons defers to their own click listeners',async()=>{
 const h=fixture('pool',4);
 try{
  assert.equal(h.space('[data-play]').defaultPrevented,false);assert.deepEqual(h.calls,[]);
  h.click('[data-play]');await Promise.resolve();assert.deepEqual(h.calls.map(c=>c.name),['jr_leisure_finish']);
  assert.equal(h.space('[data-close]').defaultPrevented,false);assert.equal(h.scene.dialog.open,true);
  h.click('[data-close]');assert.equal(h.scene.dialog.open,false);assert.equal(h.calls.length,1,'closing cannot invoke another interaction');
 }finally{h.scene.destroy();}
});

for(const selector of ['canvas','[data-stick]'])test(`Space on ${selector} retains the scene interaction shortcut`,async()=>{
 const h=fixture('pool',4);
 try{
  assert.equal(h.space(selector).defaultPrevented,true);await Promise.resolve();
  assert.deepEqual(h.calls.map(c=>c.name),['jr_leisure_finish']);
 }finally{h.scene.destroy();}
});


test('boat HUD hides lap records and has one freely available physical exit action',async()=>{
 const h=fixture('boat',0);
 try{
  assert.equal(h.elements['[data-record]'].hidden,true);
  assert.equal(h.elements['[data-leave]'].hidden,true);
  assert.equal(h.elements['[data-play]'].disabled,false);
  assert.equal(h.elements['[data-play]'].textContent,'Lên bờ');
  h.click('[data-play]');await Promise.resolve();assert.equal(h.scene.play.state.phase,'walk');assert.deepEqual(h.calls,[]);
 }finally{h.scene.destroy();}
});
