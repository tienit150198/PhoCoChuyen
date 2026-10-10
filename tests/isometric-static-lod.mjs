import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
import {build} from 'esbuild';

assert.ok(existsSync('client/isometric/static-lod.ts'),'static scenery needs a scene-owned raster LOD cache');
const compiled=await build({entryPoints:['client/isometric/static-lod.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const {StaticLodCache}=await import('data:text/javascript;base64,'+Buffer.from(compiled.outputFiles[0].text).toString('base64'));
const paints=[],canvases=[];
function createCanvas(width,height){
  const context={drawImage(...args){paints.push({canvas,context,args});}},canvas={width,height,getContext:()=>context};
  canvases.push(canvas);return canvas;
}
const cache=new StaticLodCache({createCanvas,keyPrefix:'test-lod'});
const source={width:2048,height:1024};
const frame=Object.freeze({source,frameId:'house:se',x:512,y:128,width:1024,height:768});
const far=cache.get(frame,600,450,.04);
assert.ok(far,'a 24×18 screen-pixel building can use a small mip');
assert.equal(far.width,64);assert.equal(far.height,48);
assert.equal(far.source,source);assert.equal(far.frameId,'house:se');
assert.deepEqual(paints[0].args,[source,512,128,1024,768,0,0,64,48],'only the original atlas frame is rasterized');
assert.equal(paints[0].context.imageSmoothingEnabled,true);
assert.equal(paints[0].context.imageSmoothingQuality,'high');
assert.equal(cache.get(frame,600,450,.05),far,'nearby zooms share the same raster level');
assert.equal(paints.length,1,'cached scenery has no repeated raster work');
const middle=cache.get(frame,600,450,.1),near=cache.get(frame,600,450,.2);
assert.deepEqual([middle.width,middle.height],[128,96]);
assert.deepEqual([near.width,near.height],[256,192]);
assert.notEqual(middle.key,far.key);assert.notEqual(near.key,middle.key);
assert.equal(cache.get(frame,600,450,.3),null,'zoom beyond a safely oversampled mip requests the original frame');
assert.equal(cache.get(frame,600,450,1),null,'close view restores the full-detail original');
assert.equal(cache.get(frame,600,450,.1,2),near,'device resolution is included in the target raster size');
assert.equal(cache.get(frame,600,450,.04),far,'zooming back out reuses its earlier raster');
assert.equal(canvases.length,3,'one source/frame has at most three fixed levels');
assert.equal(cache.get({...frame,width:80,height:60},600,450,.1),null,'a small source is never upsampled into a mip');

const secondCrop=cache.get({...frame,x:0},600,450,.04);
const secondFrame=cache.get({...frame,frameId:'house:sw'},600,450,.04);
const secondSource=cache.get({...frame,source:{width:2048,height:1024}},600,450,.04);
for(const entry of [secondCrop,secondFrame,secondSource])assert.notEqual(entry.key,far.key,'source identity, frame id, and exact crop cannot alias');
assert.equal(frame.x,512);assert.equal(frame.width,1024,'requesting mips cannot mutate the original atlas frame');
const portrait=cache.get({...frame,frameId:'tree',width:256,height:1024},60,240,.1);
assert.deepEqual([portrait.width,portrait.height],[16,64],'portrait sprites keep their source aspect');
for(const [width,height,zoom,resolution] of [[0,100,.1,1],[100,100,0,1],[NaN,100,.1,1],[100,100,Infinity,1],[100,100,.1,0]]){
  assert.equal(cache.get(frame,width,height,zoom,resolution),null,'invalid or hidden display geometry uses the original');
}
assert.equal(cache.get({...frame,x:-1},600,450,.04),null,'invalid atlas crops do not allocate canvases');
const bounded=new StaticLodCache({createCanvas,maxEntries:2,keyPrefix:'bounded'});
const a=bounded.get(frame,600,450,.04),b=bounded.get(frame,600,450,.1);
assert.equal(bounded.get(frame,600,450,.04),a,'reading a mip keeps it recently used');
bounded.get(frame,600,450,.2);
assert.equal(bounded.stats().entries,2,'scene memory has a finite entry bound');
assert.equal(bounded.get(frame,600,450,.04),a,'the visible reused mip survives LRU eviction');
const rebuilt=bounded.get(frame,600,450,.1);
assert.notEqual(rebuilt,b,'least recently used mip can be reclaimed');
assert.equal(rebuilt.key,b.key,'reconstructed mip keeps its stable source/frame/level key');
bounded.dispose();assert.equal(bounded.stats().entries,0);
assert.equal(bounded.get(frame,600,450,.04),null,'destroyed scenes cannot create or retain fresh raster surfaces');
assert.notEqual(new StaticLodCache({createCanvas}).get(frame,600,450,.04).key,new StaticLodCache({createCanvas}).get(frame,600,450,.04).key,'default keys cannot collide between scene-owned caches');
console.log('static image LOD: atlas crop, aspect, fixed levels, DPR, cache reuse, original restoration and bounded disposal passed');
