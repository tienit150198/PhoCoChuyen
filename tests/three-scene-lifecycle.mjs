import assert from 'node:assert/strict';
import {test,after} from 'node:test';
import {build} from 'esbuild';
import * as THREE from 'three';

// Keep production geometry, materials, raycasting and scene code. Only the browser
// and WebGL device boundary is replaced; no graphics driver is needed in Node.
class Surface extends EventTarget {
  isConnected=true;clientWidth=800;clientHeight=520;style={};
  setAttribute(){}focus(){}setPointerCapture(){}
  append(child){child.parentNode=this;this.child=child;}
  remove(){this.parentNode=null;}
  closest(){return this.dialog;}
  getBoundingClientRect(){return {left:0,top:0,width:800,height:520};}
}
class Renderer {
  constructor(){this.domElement=new Surface();this.shadowMap={};this.info={memory:{geometries:0,textures:0}};this.renderLists={dispose(){}};Renderer.last=this;this.frames=0;}
  setPixelRatio(){}setClearColor(){}setSize(){}
  render(scene,camera){this.scene=scene;this.camera=camera;scene.updateMatrixWorld(true);camera.updateMatrixWorld(true);this.frames++;}
  dispose(){this.disposed=true;}forceContextLoss(){this.lost=true;}
}
class Controls extends THREE.EventDispatcher {
  constructor(camera){super();this.camera=camera;this.target=new THREE.Vector3();Controls.last=this;}
  update(){this.camera.lookAt(this.target);this.dispatchEvent({type:'change'});}
  dispose(){this.disposed=true;}
}
const originals=new Map(),keep=(key,value)=>{if(!originals.has(key))originals.set(key,globalThis[key]);globalThis[key]=value;};
keep('__sceneThree',{...THREE,WebGLRenderer:Renderer});keep('__sceneControls',Controls);
const compiled=await build({entryPoints:['client/home3d/scene.js'],bundle:true,write:false,format:'esm',platform:'node',logLevel:'silent',plugins:[{
  name:'scene-browser-boundary',setup(b){
    b.onResolve({filter:/^three$/},()=>({path:'three',namespace:'boundary'}));
    b.onResolve({filter:/^three\/addons\/controls\/OrbitControls.js$/},()=>({path:'controls',namespace:'boundary'}));
    b.onLoad({filter:/.*/,namespace:'boundary'},a=>({contents:a.path==='three'?`export const {${Object.keys(THREE).join(',')}}=globalThis.__sceneThree;`:'export const OrbitControls=globalThis.__sceneControls;',loader:'js'}));
  }
}]});
const {createHomeScene,createDistrictScene,districtHomes}=await import('data:text/javascript;base64,'+Buffer.from(compiled.outputFiles[0].text).toString('base64'));
after(()=>{for(const [key,value]of originals){if(value===undefined)delete globalThis[key];else globalThis[key]=value;}});
test('the lazy production entry exports both scenes and the public district directory',()=>{
  assert.equal(typeof createHomeScene,'function');assert.equal(typeof createDistrictScene,'function');assert.equal(typeof districtHomes,'function');
  assert.equal(districtHomes('rent',{journey:{homes:{homes:[{id:'room',group:'rent',name:'Phòng trọ'}]}}},{},null)[0].status,'model');
});
function browser(){
  const doc=new Surface(),host=new Surface(),dialog={open:true},dialogs=[dialog],frames=new Map(),timers=new Map(),observers=[];let id=0,time=100;
  host.dialog=dialog;doc.body=new Surface();doc.hidden=false;doc.visibilityState='visible';doc.querySelectorAll=()=>dialogs;doc.createElement=()=>new Surface();
  class Observer {constructor(fn){this.fn=fn;this.active=false;observers.push(this);}observe(){this.active=true;}disconnect(){this.active=false;}}
  class ModalObserver extends Observer {kind='mutation';}
  keep('window',new Surface());keep('document',doc);keep('devicePixelRatio',1);keep('ResizeObserver',Observer);keep('MutationObserver',ModalObserver);keep('IntersectionObserver',undefined);
  keep('requestAnimationFrame',fn=>{frames.set(++id,fn);return id;});keep('cancelAnimationFrame',n=>frames.delete(n));
  keep('setInterval',fn=>{timers.set(++id,fn);return id;});keep('clearInterval',n=>timers.delete(n));
  return {doc,host,frames,timers,observers,cover(){dialogs.push({open:true});this.mutate();},uncover(){dialogs.pop();this.mutate();},mutate(){for(const o of observers)if(o.active&&o.kind==='mutation')o.fn([]);},frame(){time+=40;const work=[...frames.values()];frames.clear();for(const fn of work)fn(time);}};
}
test('a covered district pauses all frames and resumes after uncover without stale movement',()=>{
  const b=browser(),moves=[],scene=createDistrictScene(b.host,{onMove:p=>moves.push(p)}),renderer=Renderer.last;
  try{
    b.frame();scene.setInput(1,0);b.frame();const at=scene.getPosition();
    b.cover();const before=renderer.frames;b.frame();assert.equal(renderer.frames,before,'covered NPC scene must stop rendering');
    assert.equal(b.frames.size,0);scene.setPeople([{pid:'p',activity:{x:1,y:1}}]);assert.equal(b.frames.size,0,'network updates cannot restart a covered scene');
    b.uncover();assert.ok(b.frames.size>0,'uncover must restart without a pointer or resize');b.frame();
    assert.deepEqual(scene.getPosition(),at,'covered joystick input is cleared');assert.ok(renderer.frames>before);
  }finally{scene.dispose();}
  assert.equal(b.frames.size,0);assert.equal(b.observers.filter(o=>o.active).length,0);b.mutate();assert.equal(b.frames.size,0);assert.ok(renderer.disposed&&renderer.lost);
});

test('authored district houses survive batching with bounded draws, real home metadata and cover transparency',()=>{
  const b=browser(),homes=Array.from({length:8},(_,i)=>({id:'home-'+i,kindId:i?'tro_moi':'ky_tuc_xa'})),scene=createDistrictScene(b.host,{group:'rent',homes});
  try{
    b.frame();const renderer=Renderer.last,houses=renderer.scene.children.filter(o=>o.userData.architecture);
    assert.equal(houses.length,8);assert.equal(new Set(houses.map(h=>h.userData.architecture.id)).size,8);
    for(const [i,h]of houses.entries()){
      assert.ok(h.children.length>=4&&h.children.length<=18,'many architectural details batch into a bounded set of paints');
      assert.ok(h.children.every(m=>m.isMesh&&m.userData.home===homes[i]),'every clickable batch belongs to the actual home');
      assert.ok(h.children.reduce((n,m)=>n+m.geometry.attributes.position.count,0)>1000,'batching keeps detailed real geometry');
    }
    Controls.last.camera.position.set(-13.2,1.5,-34);Controls.last.update();b.frame();
    const covered=houses.filter(h=>h.children.some(m=>m.material.opacity===.35));assert.ok(covered.length,'a house between camera and player still fades to .35');
    assert.ok(covered.every(h=>h.children.every(m=>m.material.opacity===.35&&!m.material.depthWrite)),'all parts of a covering house fade together');
    Controls.last.camera.position.set(0,20,20);Controls.last.update();b.frame();assert.ok(houses.every(h=>h.children.every(m=>m.material.opacity===1)));
  }finally{scene.dispose();}
});
test('animated district customers reuse house occlusion until the player or camera moves',()=>{
  const b=browser(),scene=createDistrictScene(b.host),raycast=THREE.Mesh.prototype.raycast;let casts=0;
  THREE.Mesh.prototype.raycast=function(...args){casts++;return raycast.apply(this,args);};
  try{
    b.frame();const initial=casts;assert.ok(initial>0,'initial cover must inspect the actual house geometry');
    for(let i=0;i<120;i++)b.frame();
    assert.equal(casts,initial,'stationary player/camera must not repeat house raycasts for NPC animation');
    assert.equal(Renderer.last.frames,121,'all visible NPC animation frames are retained');
    Controls.last.camera.position.x+=2;Controls.last.update();b.frame();assert.ok(casts>initial,'orbit updates house cover immediately');
    const orbited=casts;scene.setInput(1,0);b.frame();assert.ok(casts>orbited,'walking recalculates the real line of sight');
  }finally{THREE.Mesh.prototype.raycast=raycast;scene.dispose();}
});
test('the initial district cover uses the houses placed in world coordinates',()=>{
  const b=browser(),scene=createDistrictScene(b.host);
  try{
    Controls.last.camera.position.set(-13.2,1.5,-34);Controls.last.update();
    b.frame();const renderer=Renderer.last,houses=renderer.scene.children.filter(o=>o.userData.architecture),at=scene.getPosition();
    const delta=new THREE.Vector3(at.x,1.1,at.y).sub(renderer.camera.position),distance=delta.length();
    const ray=new THREE.Raycaster(renderer.camera.position,delta.normalize(),0,distance-.1);
    const covered=new Set(ray.intersectObjects(houses,true).map(h=>h.object.parent));
    for(const house of houses)assert.ok(house.children.every(o=>o.material.opacity===(covered.has(house)?.35:1)),'first-frame house fade must match its final world position');
  }finally{scene.dispose();}
});
const room={id:'living',name:'Phòng khách',cols:7,frows:4,wrows:2,out:false,fix:[]};
const data=(color='#b36c6c')=>({scope:'mine',room,parts:{},items:[{id:'chair',it:{id:'ghe_dau',cat:'table',spot:'floor',w:1,h:1},q:{r:'living',x:40,y:25},color}],edit:true});
test('a home redraw deferred behind a modal resumes even when every resident is still',()=>{
  const b=browser(),scene=createHomeScene(b.host);
  try{
    scene.update(data());b.frame();const renderer=Renderer.last,before=renderer.frames;
    b.cover();scene.update(data('#cc9977'));b.frame();assert.equal(renderer.frames,before);
    b.uncover();assert.ok(b.frames.size>0,'closing the covering modal wakes a stationary home');b.frame();assert.ok(renderer.frames>before);
  }finally{scene.dispose();}
  assert.equal(b.observers.filter(o=>o.active).length,0);
});
test('changing paint repeatedly releases unused materials while retaining shared geometry',()=>{
  const b=browser(),scene=createHomeScene(b.host),disposed=new Set(),initialGeometries=new Set();
  try{
    scene.update(data());b.frame();const renderer=Renderer.last,firstMaterials=new Set();
    renderer.scene.traverse(o=>{if(o.isMesh){initialGeometries.add(o.geometry);firstMaterials.add(o.material);o.material.addEventListener('dispose',()=>disposed.add(o.material));}});
    const oldPaint=[...firstMaterials].find(m=>m.color?.getHexString()==='b36c6c');assert.ok(oldPaint);
    for(let i=0;i<12;i++){scene.update(data('#'+(0x805020+i*1000).toString(16)));b.frame();}
    assert.ok(disposed.has(oldPaint),'old furniture paint must be disposed during updates, not only on close');
    const currentGeometries=new Set();renderer.scene.traverse(o=>{if(o.isMesh)currentGeometries.add(o.geometry);});assert.deepEqual(currentGeometries,initialGeometries,'room rebuilds reuse the same primitive geometry');
  }finally{scene.dispose();}
  assert.equal(b.frames.size,0);assert.equal(b.timers.size,0);
});
test('orbiting behind interior walls fades their attached trim and restores them independently',()=>{
  const b=browser(),selected=[],scene=createHomeScene(b.host,{select:id=>selected.push(id)});
  try{
    scene.update(data());b.frame();const renderer=Renderer.last,controls=Controls.last;
    const back=renderer.scene.getObjectByName('back-wall'),side=renderer.scene.getObjectByName('side-wall'),floor=renderer.scene.getObjectByName('floor');
    controls.camera.position.set(0,4,-12);controls.update();b.frame();assert.equal(back.material.opacity,.35);assert.equal(back.material.depthWrite,false);assert.equal(side.material.opacity,1);assert.equal(floor.material.opacity,1);
    const wallParts=[];renderer.scene.traverse(o=>{if(o.userData.wall==='back')wallParts.push(o);});assert.ok(wallParts.length>1,'trim follows its wall');assert.ok(wallParts.every(o=>o.material.opacity===.35));
    let chair;renderer.scene.traverse(o=>{if(o.userData.uid==='chair')chair=o;});
    const top=chair.children.reduce((a,o)=>o.position.y>a.position.y?o:a),target=top.getWorldPosition(new THREE.Vector3()).project(renderer.camera);
    for(const type of ['pointerdown','pointerup']){const event=new Event(type);Object.assign(event,{button:0,isPrimary:true,pointerId:1,pointerType:'mouse',clientX:(target.x+1)*400,clientY:(1-target.y)*260});renderer.domElement.dispatchEvent(event);}
    assert.deepEqual(selected,['chair'],'faded walls do not intercept furniture selection');
    controls.camera.position.set(12,9,12);controls.update();b.frame();assert.ok(wallParts.every(o=>o.material.opacity===1));assert.equal(back.material.depthWrite,true);
  }finally{scene.dispose();}
});
