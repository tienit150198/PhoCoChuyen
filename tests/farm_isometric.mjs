import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const url=new URL('../public/js/careers/farm_isometric.js',import.meta.url);
assert.ok(fs.existsSync(url),'the cozy farm view has a presentation-only renderer');
const {farmProject,farmUnproject,farmCamera,farmMovement,farmDepth,farmDirection,pickFarmSpot,needsFarmFrames,farmVisualKey,farmObstacleBounds,createFarmRenderer}=await import(url);
assert.deepEqual(farmObstacleBounds,{pen:[-7,15.6,-3.6,19],hay:[11.4,1.3,12.8,2.7]},'solid hen run and hay bale have explicit visible footprints');
const camera={x:0,z:8,scale:20,cx:240,cy:180};
const origin=farmProject(0,0,8,camera);
assert.deepEqual(origin,{x:240,y:180});
assert.deepEqual(farmProject(1,0,8,camera),{x:260,y:190});
assert.deepEqual(farmProject(0,0,9,camera),{x:260,y:170});
assert.deepEqual(farmProject(0,3,8,camera),{x:240,y:120});
for(const [x,z] of [[-5,8],[0,8],[5,8],[-5,12.5],[0,12.5],[5,12.5],[-11,17],[9.5,9],[-5,-2]]){
  const point=farmProject(x,0,z,camera),world=farmUnproject(point.x,point.y,camera);
  assert.ok(Math.abs(world.x-x)<1e-10&&Math.abs(world.z-z)<1e-10,'tap coordinates invert the real farm metre coordinates');
}
for(const [sx,sy] of [[0,-1],[0,1],[-1,0],[1,0],[-1,-1],[1,-1],[-1,1],[1,1]]){
  const move=farmMovement(sx,sy,3.3),point=farmProject(move.x,0,8+move.z,camera);
  assert.ok(Math.abs(Math.hypot(move.x,move.z)-3.3)<1e-10,'diagonal input never increases world speed');
  assert.ok(Math.abs((point.x-origin.x)*sy-(point.y-origin.y)*sx)<1e-8,'all eight controls move in their screen direction');
  assert.ok((point.x-origin.x)*sx+(point.y-origin.y)*sy>0,'movement agrees with the pressed direction');
}
assert.deepEqual(farmMovement(0,0,3.3),{x:0,z:0});
assert.ok(Math.hypot(...Object.values(farmMovement(.2,0,3.3)))<3.3,'analogue input retains its magnitude');
const phone=farmCamera({x:0,z:-3.4,yaw:0},390,440);
assert.ok(phone.scale>=15,'phone crops and the character stay readable');
assert.deepEqual(farmCamera({x:0,z:-3.4,yaw:2},390,440),phone,'turning never rotates or shifts the garden camera');
assert.ok(farmDepth({x:0,z:13})<farmDepth({x:0,z:8}),'northern objects draw behind the foreground');
for(const [yaw,direction] of [[0,'ne'],[Math.PI/2,'se'],[Math.PI,'sw'],[-Math.PI/2,'nw']])assert.equal(farmDirection(yaw),direction);
const beds={P1:[-6.6,7.2,-3.4,8.8],P2:[-1.6,7.2,1.6,8.8],P6:[3.4,11.7,6.6,13.3]};
for(const [id,s] of Object.entries(beds)){
  const point=farmProject((s[0]+s[2])/2,.32,(s[1]+s[3])/2,camera);
  assert.equal(pickFarmSpot(point.x,point.y,camera,beds),id,'tapping a raised bed selects its original interaction target');
}
assert.equal(pickFarmSpot(-500,-500,camera,beds),null);
const resting={keys:new Set(),me:{moving:0},fx:[]};
assert.equal(needsFarmFrames(resting),false,'a resting garden needs no animation frames');
assert.equal(farmVisualKey({room:{data:{clock:1},tasks:[{patience:1}]}}),farmVisualKey({room:{data:{clock:2},tasks:[{patience:2}]}}),'clock and order countdown ticks do not redraw static scenery');
for(const active of [{auto:{}},{ride:{}},{joy:{}},{keys:new Set(['f'])},{fx:[{k:'water'}]},{hint:1},{me:{moving:.2}}])assert.equal(needsFarmFrames({...resting,...active}),true);

let surfaces=0;const sizes=[];
const context=new Proxy({measureText:s=>({width:String(s).length*7}),createLinearGradient:()=>({addColorStop(){}})}, {get:(o,k)=>k in o?o[k]:()=>{},set:(o,k,v)=>(o[k]=v,true)});
const createCanvas=(width,height)=>{surfaces++;sizes.push([width,height]);return {width,height,getContext:()=>context};};
const characters=[];
const renderer=createFarmRenderer({createCanvas,ImageClass:null,preloadCharacters:()=>{},characterStamp:o=>{characters.push(o);return {canvas:{},width:120,height:160};}});
const world={beds:{P1:[-5,8],P2:[0,8],P3:[5,8],P4:[-5,12.5],P5:[0,12.5],P6:[5,12.5]},spots:beds,trees:[{x:-15,z:14,s:1}],posts:[]};
const plot={id:'P1',crop:'tomato',stage:'ripe',growth:100,moisture:60,weeds:0,seen:0};
const data={plots:[plot],coop:{nest:2},weather:{id:'sun'}};
const state={...resting,w:390,h:440,me:{x:0,z:4,yaw:0,moving:0},hens:[],near:null};
const options={data,look:{top:'ao_so_mi'},gender:'female',moisture:{low:40,high:80,dry:25,wet:90},target:'P1'};
renderer.draw(context,state,world,options);
assert.equal(characters.at(-1).gender,'female');
assert.deepEqual(characters.at(-1).look,options.look);
assert.equal(characters.at(-1).direction,'ne');
const built=surfaces;
renderer.draw(context,{...state,me:{...state.me,x:.3}},world,options);
assert.equal(surfaces,built,'walking reuses the static floor, buildings and planted bed art');
assert.equal(characters.length,1,'a static character direction reuses its wardrobe stamp');
renderer.draw(context,state,world,{...options,data:{...data,plots:[{...plot,stage:'sprout',growth:1}]}});
assert.ok(surfaces>built,'a server growth-stage change redraws the planted bed');
for(let i=0;i<110;i++)renderer.draw(context,{...state,w:390+i},world,{...options,data:{...data,plots:[{...plot,moisture:i}]}});
assert.ok(renderer.stats().stamps<=96,'bed and scenery texture cache stays bounded');
assert.ok(renderer.stats().groundChunks<=24,'floor chunk cache stays bounded');
for(const width of [1160,1280,2560]){
  const desktop=createFarmRenderer({createCanvas,ImageClass:null,preloadCharacters:()=>{},characterStamp:()=>({canvas:{},width:120,height:160})});
  desktop.draw(context,{...state,w:width,h:640},world,options);const count=desktop.stats().groundBuilds;
  desktop.draw(context,{...state,w:width,h:640,me:{...state.me,x:.15}},world,options);
  assert.equal(desktop.stats().groundBuilds,count,`${width}px desktop movement reuses every visible floor chunk`);
  assert.ok(desktop.stats().groundChunks<=24,'desktop and ultrawide floor memory stays bounded');
}
assert.ok(sizes.every(([w,h])=>w*h<1000000),'the farm never caches an unbounded whole-world bitmap');
assert.equal(JSON.stringify(data),JSON.stringify({plots:[plot],coop:{nest:2},weather:{id:'sun'}}),'drawing does not mutate authoritative farm data');
const requested=[];let redraws=0;
class DelayedImage {naturalWidth=768;naturalHeight=795;set src(value){this.url=value;requested.push(this);}}
globalThis.__mnlBoot={asset:path=>'/assets/version'+path};
const withAssets=createFarmRenderer({createCanvas,ImageClass:DelayedImage,preloadCharacters:()=>{},characterStamp:()=>({canvas:{},width:120,height:160}),onAsset:()=>redraws++});
withAssets.draw(context,state,world,options);withAssets.draw(context,state,world,options);
assert.ok(requested.length>0);
assert.equal(new Set(requested.map(img=>img.url)).size,requested.length,'illustrated assets are requested once');
assert.ok(requested.every(img=>img.url.startsWith('/assets/version/')),'assets use the versioned boot resolver');
requested[0].onload();assert.equal(redraws,1,'loading an illustration requests a single scene refresh');
const late=requested[0].onload;withAssets.dispose();late();assert.equal(redraws,1,'late assets cannot wake a disposed scene');
delete globalThis.__mnlBoot;
// Exercise the real farm movement/collision/path code, including the new camera switch.
const walkSource=fs.readFileSync(new URL('../public/js/careers/farm_walk.js',import.meta.url),'utf8').replace(/^import .*;\r?$/gm,'').replace(/^export /gm,'');
const garden={farmCamera,farmMovement,farmProject,pickFarmSpot,needsFarmFrames,farmVisualKey,createFarmRenderer,lookOf:()=>({}),tr:s=>s};
const sandbox={...garden,console,Set,Map,Math,performance:{now:()=>0},matchMedia:()=>({matches:false}),requestAnimationFrame:()=>1,clearTimeout(){},setTimeout:()=>1};
const visibilitySource=fs.readFileSync(new URL('../public/js/careers/activity_visibility.js',import.meta.url),'utf8').replace(/^export /gm,'');
vm.createContext(sandbox);vm.runInContext(visibilitySource+'\n'+walkSource+'\nglobalThis.engine={W,step,tap,view,camera,route,gap,SPOT,SOLID,mount,loop};',sandbox);
const {engine}=sandbox;
for(const footprint of Object.values(farmObstacleBounds))assert.ok(engine.SOLID.some(s=>JSON.stringify(s)===JSON.stringify(footprint)),'each rendered obstacle matches a real collision rectangle');
assert.equal(engine.W.cam,'iso','the actual farm engine opens in the cozy garden view');
engine.W.w=390;engine.W.h=440;engine.W.x={ui:{},cc:{},room:{data:{plots:[],coop:{}}}};engine.W.hooks={};
for(const [keys,sx,sy] of [[['f'],0,-1],[['b'],0,1],[['l'],-1,0],[['r'],1,0],[['f','l'],-1,-1],[['f','r'],1,-1],[['b','l'],-1,1],[['b','r'],1,1]]){
  Object.assign(engine.W.me,{x:0,z:4,yaw:1.2});engine.W.keys=new Set(keys);engine.W.auto=null;
  const V=engine.view(),before=farmProject(0,0,4,V);engine.step(.025);const after=farmProject(engine.W.me.x,0,engine.W.me.z,V);
  assert.ok((after.x-before.x)*sx+(after.y-before.y)*sy>0,'real WASD moves in screen direction regardless of previous yaw');
  assert.ok(Math.abs((after.x-before.x)*sy-(after.y-before.y)*sx)<1e-8,'actual diagonal input follows the screen diagonal');
}
engine.W.keys.clear();Object.assign(engine.W.me,{x:0,z:4,yaw:0});
let V=engine.view(),tapPoint=farmProject(-5,.32,8,V);engine.tap(tapPoint.x,tapPoint.y);
assert.equal(engine.W.auto?.to,'P1','a rendered raised bed enters the existing route planner');
for(let i=0;i<100&&engine.W.auto;i++)engine.step(.05);
assert.ok(engine.gap(engine.SPOT.P1,engine.W.me.x,engine.W.me.z)<=1.05,'the existing route stops inside working reach');
assert.equal(engine.W.near,'P1','arrival exposes the original plot actions');
engine.camera('fp');assert.equal(engine.W.cam,'fp','first person remains selectable');
const yaw=engine.W.me.yaw;engine.W.keys=new Set(['r']);engine.step(.025);assert.ok(engine.W.me.yaw>yaw,'first person retains its original turn controls');
engine.camera('tp');assert.equal(engine.W.cam,'tp','third person remains selectable');
engine.camera('iso');engine.W.ride={x:1,z:2,yaw:.5};V=engine.view();assert.equal(V.iso,undefined,'deliveries keep the existing perspective ride camera');
// A hidden-tab pause preserves the route, resumes once and removes listeners on close.
const events=()=>{const listeners=new Map();return {listeners,addEventListener:(type,fn)=>listeners.set(type,fn),removeEventListener:(type,fn)=>{if(listeners.get(type)===fn)listeners.delete(type);},emit:type=>listeners.get(type)?.()};};
const doc={...events(),hidden:false,querySelectorAll:()=>dialog.open?[dialog]:[]},dialog={...events(),open:true},host={};let frames=0;
sandbox.document=doc;sandbox.requestAnimationFrame=()=>++frames;sandbox.cancelAnimationFrame=()=>{};
engine.W.el={isConnected:true,parentNode:host,dataset:{},closest:()=>dialog.open?dialog:null,getClientRects:()=>[{}]};
engine.W.ride=null;engine.W.keys.clear();engine.W.hint=0;engine.W.fx=[];engine.W.me.moving=0;
engine.W.auto={to:'P1',path:[{x:-4,z:6.8}],speed:4.2};
engine.mount(host,engine.W.x,{});engine.W.raf=0;
assert.equal(doc.listeners.size,1,'the visible farm installs one visibility listener');
engine.mount(host,engine.W.x,{});assert.equal(doc.listeners.size,1,'server updates do not duplicate the listener');
doc.hidden=true;doc.emit('visibilitychange');engine.loop(1000);const pausedFrames=frames;
assert.ok(engine.W.auto,'hiding the tab retains the active route');
doc.hidden=false;doc.emit('visibilitychange');assert.equal(frames,pausedFrames+1,'returning to an open farm resumes a paused route');
doc.emit('visibilitychange');assert.equal(frames,pausedFrames+1,'duplicate visibility events do not schedule another RAF');
engine.W.raf=0;engine.W.paintPending=false;engine.W.auto=null;doc.emit('visibilitychange');assert.equal(frames,pausedFrames+1,'an idle garden stays idle on visibility changes');
engine.W.auto={path:[{x:0,z:5}],to:'P1',speed:4};dialog.open=false;dialog.emit('close');
assert.equal(doc.listeners.size,0,'closing the dialog removes the visibility listener');
assert.equal(dialog.listeners.size,0,'closing also removes its own close listener');
doc.emit('visibilitychange');assert.equal(frames,pausedFrames+1,'a closed garden cannot restart from document visibility');
console.log('farm isometric: projection, screen-relative movement, real bed targeting, static caches, wardrobe and idle rendering passed');
