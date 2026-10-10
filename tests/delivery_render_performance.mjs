// Canvas-boundary benchmark: real world/renderer; records submitted work, not GPU/FPS.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {performance} from 'node:perf_hooks';
import {createIsometricRenderer} from '../public/js/careers/delivery_isometric.js';
import {buildWorld} from '../public/js/careers/delivery_drive.js';
import {mapTransform,roadRoute,B} from '../public/js/careers/delivery_navigation.js';

const nodes=Object.fromEntries(Object.entries({hub:[1,2],gas:[3,0],com:[0,4],bun:[4,1],tra:[2,3],apt:[6,3],alley:[0,1],school:[2,0],market:[3,2],office:[6,0],villa:[5,4],vet:[4,4],garage:[5,2]}).map(([id,[x,y]])=>[id,{x,y,name:id,emoji:'📍'}]));
const W=buildWorld(nodes),benchmark=process.argv.includes('--benchmark');
function boundary(){
  let calls=0,allocations=0,pixels=0;
  const noop=()=>{calls++;};
  const c=new Proxy({measureText:text=>({width:text.length*7}),createLinearGradient:()=>({addColorStop:noop})},
    {get:(object,key)=>key in object?object[key]:noop,set:(object,key,value)=>(object[key]=value,true)});
  const createCanvas=(width,height)=>{allocations++;pixels+=width*height;return {width,height,getContext:()=>c};};
  return {c,createCanvas,counts:()=>({calls,allocations,pixels}),reset:()=>{calls=0;allocations=0;pixels=0;}};
}
const summary=values=>{const v=[...values].sort((a,b)=>a-b);return {mean:values.reduce((a,b)=>a+b,0)/v.length,p95:v[Math.floor(v.length*.95)]};};
const findings=[];
for(const loaded of [false,true])for(const [w,h] of [[390,406],[1024,480],[1920,1080],[2560,1440]]){
  const canvas=boundary();
  class Illustration {naturalWidth=768;naturalHeight=795;set src(value){this.onload?.();}}
  const renderer=createIsometricRenderer({createCanvas:canvas.createCanvas,ImageClass:loaded?Illustration:null,preloadCharacters:()=>{},characterStamp:()=>({canvas:{width:120,height:160},width:120,height:160,ready:true})});
  const S={x:110,y:78,a:0,w,h,v:6,at:'hub',npcs:[],peds:[]};
  // Six deterministic visible scooters and people exercise the production geometry.
  for(let n=0;n<6;n++){S.npcs.push({x:85+n*12,y:82.3,axis:'x',dir:1,col:'#a2b58c'});S.peds.push({x:85+n*12,y:86.7,axis:'x',dir:1,variant:n});}
  for(let i=0;i<3;i++)renderer.draw(canvas.c,S,W,{target:'apt'},i);
  canvas.reset();const times=[];
  for(let i=0;i<240;i++){S.x=110+i*.01;const start=performance.now();renderer.draw(canvas.c,S,W,{target:'apt'},i/60);times.push(performance.now()-start);}
  findings.push({loaded,w,h,...canvas.counts(),...summary(times),...renderer.stats()});
  if(!benchmark)assert.ok(canvas.counts().allocations<20,`${w}×${h}: nearby warmed frames should reuse scenery; got ${canvas.counts().allocations} new surfaces`);
  // Leaving fullscreen releases the extra cached scenery instead of growing forever.
  renderer.draw(canvas.c,{...S,w:390,h:406},W,{target:'apt'},5);
  assert.ok(renderer.stats().stamps<=160,'a small viewport returns the sprite cache to its normal bound');
  assert.ok(renderer.stats().groundChunks<=12,'a small viewport returns the ground cache to its normal bound');
  renderer.dispose();
}

const drive=fs.readFileSync(new URL('../public/js/careers/delivery_drive.js',import.meta.url),'utf8');
const mapSource=drive.slice(drive.indexOf('const DISTRICTS='),drive.indexOf('function expandedMap(){'));
const mapBoundary=boundary(),S={x:110,y:78,a:0,at:'hub'},cv={width:240,height:178,getContext:()=>mapBoundary.c};S.mini=cv;
const mini=new Function('S','B','GX','GY','HW','mapTransform','routeNow','tr','devicePixelRatio','document',mapSource+';return mini;')(
  S,B,6,4,5,mapTransform,(o,W)=>roadRoute(S.x,S.y,W.marks[o.target].gate),text=>text,2,{createElement:()=>mapBoundary.createCanvas(240,178)});
mini({target:'apt'},W);mapBoundary.reset();const mapTimes=[];
for(let i=0;i<240;i++){S.x=110+i*.01;const start=performance.now();mini({target:'apt'},W);mapTimes.push(performance.now()-start);}
findings.push({minimap:true,...mapBoundary.counts(),...summary(mapTimes)});
console.log(JSON.stringify(findings,null,2));
if(!benchmark)assert.ok(mapBoundary.counts().calls<240*90,'the minimap must reuse static streets/footprints while updating its live route and rider');
if(!benchmark){
  const floor=S.miniGround.cv;
  mini({target:'gas'},W);assert.equal(S.miniGround.cv,floor,'changing destinations keeps static geometry but repaints route/markers');
  cv.width=156;mini({target:'gas'},W);
  assert.notEqual(S.miniGround.cv,floor,'resizing regenerates the floor at the new native resolution');
  assert.equal(S.miniGround.cv.width,156);
  const resizedFloor=S.miniGround.cv;mini({target:'gas'},{...W});
  assert.notEqual(S.miniGround.cv,resizedFloor,'a replacement street world invalidates the minimap floor');
}

const profileStart=drive.indexOf('function setupDrivingProfile(){');
assert.ok(profileStart>=0,'driving diagnostics are available through an explicit URL opt-in');
const profileSource=drive.slice(profileStart,drive.indexOf('function setView(view){',profileStart));
const mounted=[],elements=[];
const profileState={el:{append:element=>mounted.push(element)},iso:{stats:()=>({groundBuilds:16,groundChunks:16,stamps:251})},view:'isometric',v:6};
const environment={location:{search:''},__dlDrive:{stats:()=>({n:120,avg:16.7,p95:18,draw:3,draw95:4,dpr:1.5,w:2560,h:1440}),reset:()=>{profileState.reset=true;}}};
const document={createElement:tag=>{const e={tag,style:{},dataset:{},append(...children){this.children=children;},addEventListener(type,fn){this[type]=fn;}};elements.push(e);return e;}};
const profiles=new Function('S','globalThis','document',profileSource+';return {setupDrivingProfile,drivingProfileFrame};')(profileState,environment,document);
profiles.setupDrivingProfile();assert.equal(mounted.length,0,'normal players allocate no diagnostic panel');
environment.location.search='?drivingProfile=1';profiles.setupDrivingProfile();
assert.equal(mounted.length,1,'the diagnostic query creates one readable panel');
profiles.drivingProfileFrame(1000);
const output=elements.find(e=>e.tag==='output'),snapshot=JSON.parse(output.textContent);
assert.equal(snapshot.view,'isometric');assert.equal(snapshot.groundBuilds,16);assert.equal(snapshot.draw95,4);assert.equal(snapshot.w,2560);
output.textContent='unchanged';profiles.drivingProfileFrame(1100);assert.equal(output.textContent,'unchanged','diagnostics update at most once a second');
elements.find(e=>e.tag==='button').click();assert.equal(profileState.reset,true,'the visible reset starts a fresh measurement');

// Wire that button to the real reset implementation, not a counter stub. A
// measurement restart must not replace or resize the live fullscreen stage.
const activeStage={width:1280,height:720},activeCanvas={width:1920,height:1080};
Object.assign(profileState,{el:activeStage,cv:activeCanvas,w:1280,h:720,dpr:1.5,raf:72,frames:[16,17],cost:[2,3],
  full:{active:true,exit(){assert.fail('diagnostic reset must not exit fullscreen');}}});
const debugSource=drive.slice(drive.indexOf('globalThis.__dlDrive={'),drive.indexOf('const ARROW='));
const actualDiagnostics=new Function('S','globalThis',debugSource+';return globalThis.__dlDrive;')(profileState,{});
environment.__dlDrive.reset=actualDiagnostics.reset;
elements.find(e=>e.tag==='button').click();
assert.deepEqual(profileState.frames,[]);assert.deepEqual(profileState.cost,[]);
assert.equal(profileState.el,activeStage);assert.equal(profileState.cv,activeCanvas);
assert.deepEqual([profileState.w,profileState.h,profileState.dpr,activeCanvas.width,activeCanvas.height],[1280,720,1.5,1920,1080]);
assert.equal(profileState.full.active,true);assert.equal(profileState.raf,72);assert.equal(profileState.v,6);
