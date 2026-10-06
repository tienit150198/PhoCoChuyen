import './phaser25d-wired.mjs';  // skipped while the 2.5D client is not wired (docs/PHASER_25D.md)
import assert from 'node:assert/strict';
import fs from 'node:fs';
// The 2.5D switch (CHANGELOG "Giao diện 2.5D") wires the town and the workplaces only. The delivery career's own
// isometric ride (delivery_drive.js view 'isometric', docs/PHASER_25D.md) is not ported: the ride stays the
// rider's-seat view in both UIs. This test runs again once delivery_drive.js imports the renderer.
if(!fs.readFileSync(new URL('../public/js/careers/delivery_drive.js',import.meta.url),'utf8').includes('./delivery_isometric.js')){
  console.log('delivery_isometric: skipped: delivery_drive.js does not use the isometric ride (not ported with the 2.5D switch)');process.exit(0);
}

const moduleURL=new URL('../public/js/careers/delivery_isometric.js',import.meta.url);
assert.ok(fs.existsSync(moduleURL),'the isometric driving renderer exists');
const {isoProject,isoCamera,destinationPoints,depthOf,createIsometricRenderer,needsDrivingFrames,riderPalette,riderDirection,neighbourhoodKind}=await import(moduleURL);
const {B,gateOf,onRoad}=await import('../public/js/careers/delivery_navigation.js');
const camera={x:30,y:40,scale:4,cx:195,cy:340};
const p=isoProject(30,40,0,camera),east=isoProject(31,40,0,camera),south=isoProject(30,41,0,camera);
assert.deepEqual(p,{x:195,y:340});
assert.equal(east.x-p.x,4);assert.equal(east.y-p.y,2,'east tiles have exact 2:1 edges');
assert.equal(south.x-p.x,-4);assert.equal(south.y-p.y,2,'south tiles have exact 2:1 edges');
assert.equal(isoProject(30,40,3,camera).y,328,'height projects vertically without moving the ground anchor');
const state={x:54,y:78,a:0,v:0,steer:0,keys:{},btn:{},joy:{steer:0,drive:0},stopDone:true};
const cam=isoCamera(state,390,844),rider=isoProject(state.x,state.y,0,cam);
assert.ok(cam.scale>=7&&cam.scale<=8,'the default phone camera shows a close neighbourhood instead of a map-sized grid');
const moved=isoCamera({...state,x:state.x+B},390,844);
assert.deepEqual(isoProject(state.x+B,state.y,0,moved),rider,'the camera follows the real scooter coordinates');
assert.notDeepEqual(isoCamera({...state,a:Math.PI/2},390,844),cam,'heading gives the camera a small look ahead');
for(const node of [{x:0,y:0},{x:6,y:4},{x:3,y:2}]){
  const g=gateOf(node),points=destinationPoints(g,cam);
  assert.deepEqual(points.anchor,isoProject(g.x,g.y,0,cam),'destination badge is attached to the actual gate');
  assert.equal(points.bay.length,4);
  assert.deepEqual(points.bay[0],isoProject(g.x-5.5,g.y-4.7,0,cam),'parking bay matches the existing first-person bay');
  assert.ok(onRoad(g.x,g.y-2.2),'the visible bay is a valid arrival location');
}
assert.ok(depthOf({x:0,y:20})<depthOf({x:20,y:20}),'screen ground depth sorts props before the nearer rider');
assert.equal(needsDrivingFrames(state),false,'an idle scene does not request animation frames');
assert.equal(needsDrivingFrames({...state,v:.1}),true,'coasting stays smooth');
assert.equal(needsDrivingFrames({...state,keys:{u:true}}),true,'the keyboard wakes the scene');
assert.equal(needsDrivingFrames({...state,joy:{steer:.2,drive:0}}),true,'analogue steering wakes the scene');
assert.equal(needsDrivingFrames({...state,stopDone:false}),true,'parking continues until the existing arrival handler completes');
assert.equal(needsDrivingFrames({...state,stopDone:false,sending:true}),false,'pending server work does not spin animation frames');
assert.equal(typeof riderPalette,'function','courier colors come from the saved wardrobe');
const look={top:'ao_so_mi',skin:'da_ngam',shade:'mau_den',hair:'toc_duoi_ngua',bottom:'quan_jean',acc:'kinh_ram',tint:{ao_so_mi:'hong'}};
assert.equal(riderPalette(look,'female').top,'#f4b0c4','the courier wears the chosen clothing tint');
assert.equal(riderPalette(look,'female').skin,'#c48d64','the courier keeps the chosen skin');
assert.equal(riderPalette(look,'female').hair,'#2f2826','the courier keeps the chosen hair');
assert.equal(typeof riderDirection,'function','the illustrated rider has a view derived from vehicle heading');
for(const [angle,direction] of [[0,'se'],[Math.PI/2,'sw'],[Math.PI,'nw'],[-Math.PI/2,'ne'],[Math.PI*2,'se']])assert.equal(riderDirection(angle),direction);
assert.equal(neighbourhoodKind({x0:3,y0:0}),'pharmacy');
assert.equal(neighbourhoodKind({x0:2,y0:8}),'mother-baby');
assert.equal(neighbourhoodKind({x0:1,y0:0}),'home');
assert.equal(neighbourhoodKind({x0:3,y0:0,assetKind:'cafe'}),'cafe','an explicit storefront illustration takes precedence');

// Canvas is injected only to exercise the real cache and draw pass in Node.
globalThis.Path2D=class {constructor(path){this.path=path;}};
let surfaces=0;const surfaceSizes=[];
const context=new Proxy({measureText:s=>({width:s.length*7})},{get:(o,k)=>k in o?o[k]:()=>{},set:(o,k,v)=>(o[k]=v,true)});
const createCanvas=(width,height)=>{surfaces++;surfaceSizes.push([width,height]);return {width,height,getContext:()=>context};};
const characterCalls=[];
const characterStamp=options=>{characterCalls.push(options);return {canvas:{width:120,height:160},width:120,height:160,ready:true};};
const renderer=createIsometricRenderer({createCanvas,ImageClass:null,characterStamp});
const world={cells:new Map(),trees:[],lamps:[],lights:[],props:[],gardens:[],signs:[],marks:{home:{id:'home',name:'Nhà Hoa',gate:{x:54,y:80},x0:48,x1:60,y1:72,look:{h:7}}}};
renderer.draw(context,{...state,w:390,h:844,npcs:[],peds:[],at:'hub'},world,{target:'home',fuel:62,look,player:{gender:'female'}},0);
assert.equal(context.imageSmoothingEnabled,true,'illustrated assets retain smooth shading and contours');
assert.ok(!surfaceSizes.some(([w,h])=>w===195&&h===422),'the phone scene is drawn at display resolution without a coarse pixel surface');
assert.equal(characterCalls.at(-1).direction,'se');assert.deepEqual(characterCalls.at(-1).look,look);assert.equal(characterCalls.at(-1).gender,'female');
const first=surfaces;
assert.ok(surfaceSizes.every(([w,h])=>w*h<1000000),'close phone view caches small chunks rather than a large full-town bitmap');
renderer.draw(context,{...state,x:60,w:390,h:844,npcs:[],peds:[],at:'hub'},world,{target:'home',fuel:62,look,player:{gender:'female'}},1);
assert.equal(surfaces,first,'moving the scooter reuses the static ground and building stamps');
assert.equal(characterCalls.filter(o=>o.look===look).length,1,'a static rider pose is reused while travelling in the same direction');
renderer.draw(context,{...state,x:60,a:Math.PI/2,w:390,h:844,npcs:[],peds:[],at:'hub'},world,{target:'home',fuel:62,look,player:{gender:'female'}},1);
assert.equal(characterCalls.at(-1).direction,'sw','turning selects the corresponding illustrated view');
const built=renderer.stats().groundBuilds;
assert.ok(built>=1&&built<=9,'only visible ground chunks are cached');
renderer.draw(context,{...state,x:60,w:600,h:480,npcs:[],peds:[],at:'hub'},world,{target:'home',fuel:62},2);
assert.ok(renderer.stats().groundBuilds>built,'a viewport scale change builds visible ground chunks at the new scale');
for(let x=0;x<=240;x+=40)renderer.draw(context,{...state,x,w:600,h:480,npcs:[],peds:[],at:'hub'},world,{target:'home'},2);
assert.ok(renderer.stats().groundChunks<=12,'travelling across town keeps the ground cache bounded');
const resizedWorld={...world,trees:Array.from({length:8},(_,i)=>({x:54+i,y:76,r:1.1+i*.1}))};
for(let width=390;width<450;width+=2)renderer.draw(context,{...state,w:width,h:480,npcs:[],peds:[],at:'hub'},resizedWorld,{target:'home'},2);
assert.ok(renderer.stats().stamps<=160,'repeated viewport resizing keeps sprite stamps bounded');
const stampPaths=[];
const fallbackRenderer=createIsometricRenderer({ImageClass:null,createCanvas:(width,height)=>{
  const paths=[];stampPaths.push(paths);
  return {width,height,getContext:()=>new Proxy({measureText:s=>({width:s.length*7})},{get:(o,key)=>key in o?o[key]:(...args)=>{if(key==='moveTo'||key==='lineTo')paths.push(args);},set:(o,key,value)=>(o[key]=value,true)})};
},characterStamp});
fallbackRenderer.draw(context,{...state,w:390,h:844,npcs:[],peds:[],at:'hub'},world,{target:'home'},0);
assert.equal(fallbackRenderer.stats().images,0,'a native fallback works without a browser image loader');
const requested=[];
class Sprite {naturalWidth=768;naturalHeight=795;set src(url){requested.push(url);this.onload?.();}}
globalThis.__mnlBoot={asset:url=>'/assets/versioned'+url};
const assetRenderer=createIsometricRenderer({createCanvas,ImageClass:Sprite,characterStamp});
assetRenderer.draw(context,{...state,w:390,h:844,npcs:[],peds:[],at:'hub'},world,{target:'home'},0);
assetRenderer.draw(context,{...state,w:390,h:844,npcs:[],peds:[],at:'hub'},world,{target:'home'},1);
assert.deepEqual(requested,['/assets/versioned/icons/isometric/home.webp'],'illustrated buildings use the versioned boot resolver and request an asset only once');
const leafyWorld={...world,trees:[{x:54,y:76,r:1.3}]};
assetRenderer.draw(context,{...state,w:390,h:844,npcs:[],peds:[],at:'hub'},leafyWorld,{target:'home'},1);
assetRenderer.draw(context,{...state,w:390,h:844,npcs:[],peds:[],at:'hub'},leafyWorld,{target:'home'},2);
assert.deepEqual(requested,['/assets/versioned/icons/isometric/home.webp','/assets/versioned/icons/isometric/tree.webp'],'illustrated foliage shares the cached asset loader');
const shops={...world,cells:new Map([['1,2',[{x0:48,x1:56,y0:64,y1:72,h:7,assetKind:'pharmacy'},{x0:58,x1:66,y0:64,y1:72,h:7,assetKind:'mother-baby'}]]])};
assetRenderer.draw(context,frameStateForShops(),shops,{target:'home'},3);
assetRenderer.draw(context,frameStateForShops(),shops,{target:'home'},4);
assert.deepEqual(requested.slice(-2),['/assets/versioned/icons/cozy-v2/pharmacy.webp','/assets/versioned/icons/cozy-v2/mother-baby.webp'],'the new detailed storefronts use their exact asset paths and are cached');
function frameStateForShops(){return {...state,w:390,h:844,npcs:[],peds:[],at:'hub'};}
delete globalThis.__mnlBoot;

const waitingImages=[];let illustrationRedraws=0;
class WaitingSprite {naturalWidth=0;naturalHeight=0;set src(url){this.url=url;waitingImages.push(this);}}
const deferred=createIsometricRenderer({createCanvas,ImageClass:WaitingSprite,characterStamp,preloadCharacters:()=>{},onAsset:()=>illustrationRedraws++});
const frameState={...state,w:390,h:844,npcs:[],peds:[],at:'hub'};
deferred.draw(context,frameState,world,{target:'home',look},0);deferred.draw(context,frameState,world,{target:'home',look},1);
assert.equal(waitingImages.length,1,'a pending building image is requested once');
assert.equal(illustrationRedraws,0,'waiting for an asset does not request animation frames');
const deferredGround=deferred.stats().groundBuilds;
waitingImages[0].naturalWidth=768;waitingImages[0].naturalHeight=795;waitingImages[0].onload();
assert.equal(illustrationRedraws,1,'a loaded illustration requests a single redraw');
deferred.draw(context,frameState,world,{target:'home',look},2);
assert.equal(deferred.stats().groundBuilds,deferredGround,'a building load preserves the cached static ground');
const lateImageCallback=waitingImages[0].onload;deferred.dispose();lateImageCallback();
assert.equal(illustrationRedraws,1,'a disposed driving scene ignores late image callbacks');

let avatarReady=false,avatarCallback,avatarRedraws=0;const avatarCalls=[];
const avatarRenderer=createIsometricRenderer({createCanvas,ImageClass:null,preloadCharacters:fn=>avatarCallback=fn,onAsset:()=>avatarRedraws++,characterStamp:options=>{avatarCalls.push(options);return {canvas:{width:120,height:160},width:120,height:160,ready:avatarReady};}});
avatarRenderer.draw(context,frameState,world,{target:'home',look},0);avatarRenderer.draw(context,frameState,world,{target:'home',look},1);
assert.equal(avatarCalls.filter(o=>o.look===look).length,1,'the initial character fallback is cached');
avatarReady=true;avatarCallback();avatarRenderer.draw(context,frameState,world,{target:'home',look},2);
assert.equal(avatarCalls.filter(o=>o.look===look).length,2,'the illustrated character replaces its cached loading fallback');
assert.equal(avatarRedraws,1,'character atlas readiness schedules one refresh');
avatarRenderer.dispose();avatarCallback();assert.equal(avatarRedraws,1,'a late character load cannot wake a destroyed scene');
const colors=[];
const signalContext=new Proxy({measureText:s=>({width:s.length*7})},{get:(o,key)=>key in o?o[key]:()=>{if(key==='fill'||key==='fillRect')colors.push(o.fillStyle);},set:(o,key,value)=>(o[key]=value,true)});
const signalRenderer=createIsometricRenderer({createCanvas:(width,height)=>({width,height,getContext:()=>signalContext}),characterStamp});
const signalWorld={...world,lights:[{i:1,j:1,x:45.8,y:34.2,x2:34.2,y2:45.8,off:0}]};
signalRenderer.draw(signalContext,{...state,w:390,h:844,a:0,npcs:[],peds:[],at:'hub'},signalWorld,{target:'home'},0);
assert.ok(colors.includes('#da624c'),'the visible x-axis signal is red at the real phase');
colors.length=0;
signalRenderer.draw(signalContext,{...state,w:390,h:844,a:Math.PI/2,npcs:[],peds:[],at:'hub'},signalWorld,{target:'home'},0);
assert.ok(colors.includes('#75ad69'),'the visible y-axis signal is green at that same real phase');
const source=fs.readFileSync(moduleURL,'utf8');
assert.doesNotMatch(source,/\bfetch\s*\(|\.send\s*\(|dl_ride|dl_plan/,'the visual renderer cannot award or send game commands');
assert.match(source,/getCharacterStamp/,'the main rider uses the shared illustrated wardrobe figure');
assert.doesNotMatch(source,/getPixelCharacter|PIXEL_SCALE|imageSmoothingEnabled\s*=\s*false/,'delivery retains the detail of the illustrated assets');
const drive=fs.readFileSync(new URL('../public/js/careers/delivery_drive.js',import.meta.url),'utf8');
assert.match(drive,/view:'isometric'/,'isometric is the default driving view');
assert.doesNotMatch(drive,/dd-view-toggle/,'the user remains in the illustrated neighbourhood view');
const frameSource=drive.slice(drive.indexOf('function frame(now){'),drive.indexOf('/** Frame times;'));
let frames=0,idleTicks=0,trafficSteps=0;
const stage={el:{isConnected:true},opts:{},keys:{},btn:{},joy:{},v:0,steer:0,stopDone:true,view:'isometric',last:0,t:0,visible:false};
const frame=new Function('S','live','park','ride','moveTraffic','draw','measure','requestAnimationFrame','setTimeout','needsDrivingFrames',frameSource+';return frame;')(
  stage,()=>true,()=>{},()=>{},()=>trafficSteps++,()=>{},()=>{},()=>++frames,()=>++idleTicks,needsDrivingFrames);
frame(16);
assert.equal(frames,0,'the real idle frame handler schedules no RAF');
assert.equal(idleTicks,1,'the real signal clock receives a low-frequency idle refresh');
assert.equal(trafficSteps,0,'idle scenery has no perpetual NPC animation');
stage.v=1;frame(32);
assert.equal(frames,1,'the real frame handler animates coasting');
assert.equal(trafficSteps,1,'moving traffic still uses the existing simulation');
stage.view='firstperson';stage.v=0;frame(48);
assert.equal(frames,2,'the optional original view keeps its frame loop');
console.log('delivery isometric: exact projection, real gate alignment, camera heading, depth, idle frames and static cache passed');
