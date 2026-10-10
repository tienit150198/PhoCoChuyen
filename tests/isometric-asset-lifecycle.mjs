import assert from 'node:assert/strict';
import test,{after} from 'node:test';
import {EventEmitter} from 'node:events';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {build} from 'esbuild';

// Exercise the actual world/scene methods; replace only the browser renderer.
const originalDocument=globalThis.document,originalWindow=globalThis.window,originalPhaser=globalThis.__assetLifecyclePhaser;
const environment={hidden:false,modal:false};
globalThis.document={get hidden(){return environment.hidden;},querySelector:()=>environment.modal?{}:null};
globalThis.window={};
globalThis.__assetLifecyclePhaser={Scene:class {},Loader:{Events:{COMPLETE:'complete'}},Scenes:{Events:{SHUTDOWN:'shutdown',CREATE:'create'}},Math:{Clamp:(v,min,max)=>Math.max(min,Math.min(max,v))}};
after(()=>{if(originalDocument===undefined)delete globalThis.document;else globalThis.document=originalDocument;if(originalWindow===undefined)delete globalThis.window;else globalThis.window=originalWindow;if(originalPhaser===undefined)delete globalThis.__assetLifecyclePhaser;else globalThis.__assetLifecyclePhaser=originalPhaser;});
const bundle=await build({stdin:{contents:readFileSync('client/isometric/phaser-world.ts','utf8')+'\nexport {DioramaScene};',loader:'ts',resolveDir:resolve('client/isometric')},bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent',plugins:[{
  name:'asset-lifecycle-renderer',setup(b){
    b.onResolve({filter:/^(phaser|\/js\/)/},args=>({path:args.path,namespace:'asset-test'}));
    b.onLoad({filter:/.*/,namespace:'asset-test'},args=>({contents:args.path==='phaser'?'export default globalThis.__assetLifecyclePhaser;':args.path.includes('/look.js')?'export const figure=()=>({}),defaultLook=()=>({});':args.path.includes('/character-art.js')?'export const getCharacterStamp=()=>({}),preloadIllustratedCharacters=()=>{};':'export const kindOf=()=>"home",wordsFor=()=>({});',loader:'js'}));
  },
}]});
const {PhaserWorld,DioramaScene}=await import('data:text/javascript;base64,'+Buffer.from(bundle.outputFiles[0].text+'\n//# sourceURL=isometric-asset-lifecycle-bundle.mjs').toString('base64'));
const flush=async()=>{for(let i=0;i<5;i++)await Promise.resolve();};

function harness(){
  environment.hidden=false;environment.modal=false;
  const calls={sleep:0,wake:0,start:0,rebuild:0},owner=Object.create(PhaserWorld.prototype);
  Object.assign(owner,{destroyed:false,visible:true,_paused:false,keys:new Set(),pointers:new Map(),movementInput:{x:0,y:0},player:{x:0,y:0,path:[],goal:null},mode:'town',reduced:false,cachedPreview:new Map([['old','preview']]),
    engine:{loop:{sleep:()=>calls.sleep++,wake:()=>calls.wake++}}});
  const scene=new DioramaScene(owner);owner.stage=scene;
  scene.sys={isActive:()=>true};scene.positionPlayer=()=>{};scene.updateOcclusion=()=>false;scene.stepRemotePlayers=()=>false;scene.hasEffects=()=>false;
  scene.rebuild=()=>{calls.rebuild++;scene.requestRender();};
  const textures=new Set(),queued=[];
  scene.textures={exists:key=>textures.has(key)};
  scene.load=Object.assign(new EventEmitter(),{loading:false,isLoading(){return this.loading;},image(key){queued.push(key);},start(){calls.start++;this.loading=true;}});
  scene.events=new EventEmitter();
  return {owner,scene,calls,textures,queued};
}

test('visible idle scenes keep ticking through loader download and decode work, then settle to sleep',()=>{
  const h=harness();h.scene.load.loading=true;
  for(let i=0;i<100;i++)h.owner.step(1/60);
  assert.equal(h.calls.sleep,0,'pending Phaser loader work needs Scene UPDATE to drain queued files');assert.equal(h.calls.wake,0,'pending work does not restart the loop every frame');
  h.scene.load.loading=false;
  for(let i=0;i<3;i++)h.owner.step(1/60);
  assert.equal(h.calls.sleep,1,'the ordinary bounded settle window sleeps after COMPLETE');
});

test('hidden, modal-covered and paused scenes still sleep with pending images',()=>{
  for(const reason of ['hidden','modal','paused','invisible']){
    const h=harness();h.scene.load.loading=true;h.owner.movementInput={x:1,y:0};
    if(reason==='hidden')environment.hidden=true;else if(reason==='modal')environment.modal=true;else if(reason==='paused')h.owner._paused=true;else h.owner.visible=false;
    h.owner.step(1/60);assert.equal(h.calls.sleep,1,reason);assert.equal(h.calls.wake,0);assert.deepEqual(h.owner.movementInput,{x:0,y:0});
  }
});

test('new lazy assets wake a settled scene once per request batch without requeuing existing files',async()=>{
  const h=harness();
  h.scene.ensureAssets(['career-pharmacy']);h.scene.ensureAssets(['career-teacher']);h.scene.ensureAssets(['career-repair']);
  await flush();assert.equal(h.calls.start,1);assert.equal(h.calls.wake,1,'one wake for a synchronous asset batch');
  assert.deepEqual(h.queued,['art-career-pharmacy','art-career-teacher','art-career-repair']);
  for(let i=0;i<100;i++)h.scene.ensureAssets(['career-pharmacy','unknown']);
  await flush();assert.equal(h.calls.start,1);assert.equal(h.calls.wake,1,'already requested and unknown assets cannot create an idle wake loop');
  h.textures.add('art-home');h.scene.ensureAssets(['home']);await flush();assert.equal(h.calls.wake,1,'cached images need no loader wake');
});

test('queued wakes respect hidden/pause guards and do not revive an inactive scene',async()=>{
  const h=harness();h.owner._paused=true;h.scene.ensureAssets(['career-pharmacy']);await flush();assert.equal(h.calls.wake,0);assert.equal(h.calls.sleep,1);
  const stopped=harness();stopped.scene.ensureAssets(['career-pharmacy']);stopped.scene.sys.isActive=()=>false;await flush();assert.equal(stopped.calls.wake,0);
});

test('loader COMPLETE invalidates preview art and performs one coalesced scene rebuild',async()=>{
  const h=harness();h.scene.create();h.scene.load.emit('complete');h.scene.load.emit('complete');await flush();
  assert.equal(h.owner.cachedPreview.size,0);assert.equal(h.calls.rebuild,1);assert.equal(h.calls.wake,1);
});

test('world ready follows the first active rebuild, after Phaser exits CREATING',()=>{
  const h=harness(),events=[];let active=false;
  h.scene.sys.isActive=()=>active;
  h.owner.resize=()=>events.push('resize');h.owner.resolveReady=()=>events.push('ready');h.owner.wake=()=>events.push('wake');
  h.scene.rebuild=()=>{assert.equal(active,true,'initial rendering cannot silently return during CREATING');events.push('rebuild');};
  h.scene.create();assert.deepEqual(events,[],'create callback must not announce ready while scene is still CREATING');
  active=true;h.scene.events.emit('create');assert.deepEqual(events,['resize','rebuild','ready','wake']);
  h.scene.events.emit('create');assert.equal(events.filter(e=>e==='ready').length,1,'boot is registered once');
});
