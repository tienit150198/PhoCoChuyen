import assert from 'node:assert/strict';
import {existsSync,readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {build} from 'esbuild';
assert.ok(existsSync('client/isometric/visibility.ts'),'visibility geometry must be implemented');
const out=await build({entryPoints:['client/isometric/visibility.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const {SpatialIndex,coversPlayer,fadeAlpha}=await import('data:text/javascript;base64,'+Buffer.from(out.outputFiles[0].text).toString('base64'));
const index=new SpatialIndex(128),near={id:1},edge={id:2},far={id:3};
index.add(near,{x0:-30,y0:-90,x1:35,y1:10});index.add(edge,{x0:120,y0:0,x1:280,y1:150});index.add(far,{x0:3000,y0:3000,x1:3100,y1:3200});
assert.deepEqual(new Set(index.query({x0:-5,y0:-20,x1:128,y1:100})),new Set([near,edge]));
assert.equal(index.query({x0:125,y0:5,x1:275,y1:140}).filter(x=>x===edge).length,1,'multi-cell object occurs once');
assert.deepEqual(index.query({x0:-900,y0:900,x1:-600,y1:1100}),[]);
index.clear();assert.equal(index.query({x0:-100,y0:-100,x1:4000,y1:4000}).length,0);
const body={x:50,y:110,depth:110.5},object={bounds:{x0:0,y0:0,x1:100,y1:160},depth:160,mask:{width:4,height:4,alpha:new Uint8Array(16).fill(255)}};
assert.equal(coversPlayer(body,object),true,'solid foreground building covers upper body');
assert.equal(coversPlayer({...body,depth:170},object),false,'player in front must not fade building');
assert.equal(coversPlayer({...body,x:180},object),false,'nearby non-overlapping house stays opaque');
const empty={...object,mask:{...object.mask,alpha:new Uint8Array(16)}};
assert.equal(coversPlayer(body,empty),false,'transparent sprite margin is not an occluder');
assert.equal(coversPlayer(body,{...object,mask:{...object.mask,alpha:new Uint8Array(16).fill(15)}}),false,'soft ground shadow alone does not hide a player');
assert.equal(fadeAlpha(1,.3,.02,true),.3,'reduce-motion uses immediate transition');
let alpha=1;for(let i=0;i<100;i++)alpha=fadeAlpha(alpha,.3,1/60,false);
assert.equal(alpha,.3,'fade terminates exactly so idle loop can sleep');
for(let i=0;i<100;i++)alpha=fadeAlpha(alpha,1,1/60,false);
assert.equal(alpha,1,'leaving obstruction restores opacity');
assert.equal(fadeAlpha(1,.3,NaN,false),1,'invalid delta cannot corrupt alpha');

// Exercise the actual scene methods, keeping only Phaser's display objects and
// Canvas pixel I/O as test doubles. No production export or generated file is needed.
const allocations={canvases:0,readbacks:0,images:0};
const frameFor=(image,width=120,height=160,name='__BASE')=>({name,source:{image},cutX:0,cutY:0,cutWidth:width,cutHeight:height});
class TestImage {
  constructor(scene,x=0,y=0,key='source'){
    this.scene=scene;this.x=x;this.y=y;this.alpha=1;this.visible=true;this.depth=0;
    this.scaleX=1;this.scaleY=1;this.rotation=0;this.boundsReads=0;this.setTexture(key);
  }
  setTexture(key){this.texture={key};this.frame=this.scene.textures.frames.get(key)||frameFor({});this.frame.texture=this.texture;return this;}
  setAlpha(value){assert.equal(this.destroyed,undefined,'destroyed objects must never receive fade updates');this.alpha=value;return this;}
  setVisible(value){this.visible=value;return this;}
  setDepth(value){this.depth=value;return this;}
  setDisplaySize(width,height){this.displayWidth=width;this.displayHeight=height;return this;}
  setOrigin(x,y=x){this.originX=x;this.originY=y;return this;}
  setPosition(x,y){this.x=x;this.y=y;return this;}
  setRotation(value){this.rotation=value;return this;}
  setScale(x,y=x){this.scaleX=x;this.scaleY=y;return this;}
  setData(key,value){this.data??={};this.data[key]=value;return this;}
  getData(key){return this.data?.[key];}
  getBounds(){this.boundsReads++;const r=this.bounds||{x0:this.x-10,y0:this.y-10,x1:this.x+10,y1:this.y+10};return {left:r.x0,top:r.y0,right:r.x1,bottom:r.y1,width:r.x1-r.x0,height:r.y1-r.y0,contains:(x,y)=>x>=r.x0&&x<=r.x1&&y>=r.y0&&y<=r.y1};}
  destroy(){this.destroyed=true;this.visible=false;}
}
class TestContainer extends TestImage {}
class TestText extends TestImage {}
class TestScene {}
const testPhaser={Scene:TestScene,GameObjects:{Image:TestImage,Container:TestContainer,Text:TestText},Textures:{FilterMode:{LINEAR:1}}};
function canvas(){
  allocations.canvases++;
  const cv={width:0,height:0},ctx={canvas:cv,beginPath(){},ellipse(){},stroke(){},drawImage(){},fillRect(){},
    setTransform(){},roundRect(){},clip(){},getImageData(){allocations.readbacks++;return {data:new Uint8ClampedArray(cv.width*cv.height*4).fill(255)};}};
  cv.getContext=()=>ctx;return cv;
}
const originalDocument=globalThis.document,originalPhaser=globalThis.__visibilityTestPhaser;
globalThis.document={createElement(tag){assert.equal(tag,'canvas');return canvas();}};
globalThis.__visibilityTestPhaser=testPhaser;
try {
  const sceneSource=readFileSync('client/isometric/phaser-world.ts','utf8');
  const bundled=await build({stdin:{contents:sceneSource+'\nexport {DioramaScene};',loader:'ts',resolveDir:resolve('client/isometric')},bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent',plugins:[{
    name:'visibility-display-boundary',setup(b){
      b.onResolve({filter:/^(phaser|\/js\/)/},args=>({path:args.path,namespace:'visibility-test'}));
      b.onLoad({filter:/.*/,namespace:'visibility-test'},args=>({contents:args.path==='phaser'?'export default globalThis.__visibilityTestPhaser;':args.path.includes('/look.js')?
        'export const figure=state=>({L:state?.look||{},g:"male"}),defaultLook=()=>({});':args.path.includes('/character-art.js')?
        'export const getCharacterStamp=()=>({canvas:Object.assign(document.createElement("canvas"),{width:120,height:160})}),preloadIllustratedCharacters=()=>{};':
        'export const kindOf=()=>"home",wordsFor=()=>({});',loader:'js'}));
    }
  }]});
  const {DioramaScene}=await import('data:text/javascript;base64,'+Buffer.from(bundled.outputFiles[0].text).toString('base64'));
  function scene(){
    const owner={hotspots:[],treasure:[],mode:'town',career:'home',state:{look:{}},player:{x:2,y:2,path:[],goal:null},walkDistance:0,direction:'se',reduced:false,remotePlayers:[],width:800,height:600,canvas:{closest:()=>null}};
    const s=new DioramaScene(owner),frames=new Map();
    s.sys={isActive:()=>true};
    s.textures={frames,exists:key=>frames.has(key),remove:key=>frames.delete(key),addCanvas(key,source){frames.set(key,frameFor(source,source.width,source.height));return {setFilter(){return this;}};}};
    s.add={image(x,y,key){allocations.images++;return new TestImage(s,x,y,key);},graphics:()=>new TestImage(s)};
    s.cameras={main:{scrollX:0,scrollY:0,width:800,height:600,zoom:1,setBackgroundColor(){return this;},setZoom(v){this.zoom=v;return this;},setScroll(x,y){this.scrollX=x;this.scrollY=y;return this;}}};
    s.refreshPlayer();s.positionPlayer(false);return s;
  }
  function blocker(s,key,bounds,depth=170){
    const image=new TestImage(s,0,0,key).setDepth(depth);image.bounds=bounds;
    const sign=new TestContainer(s);s.staticObjects.push(image,sign);s.registerOccluder(image,sign);return {image,sign};
  }
  function settle(s){
    let frames=0,active;
    do {active=s.updateOcclusion(1/60);frames++;}while(active&&frames<90);
    assert.equal(active,false,'all opacity transitions terminate so the world can sleep');return frames;
  }
  function move(s,x,y){Object.assign(s.owner.player,{x,y});s.positionPlayer(false);}

  const s=scene();
  const first=blocker(s,'house-a',{x0:-45,y0:0,x1:45,y1:180});
  const second=blocker(s,'house-b',{x0:-60,y0:-10,x1:60,y1:175},175);
  const behind=blocker(s,'house-behind',{x0:-60,y0:-10,x1:60,y1:175},100);
  assert.equal(s.updateOcclusion(1/60),true,'entering cover starts a bounded transition');
  assert.equal(s.occludedCount,2,'all foreground blockers are faded together');
  settle(s);
  for(const object of [first,second]){assert.equal(object.image.alpha,.35);assert.equal(object.sign.alpha,.35,'mounted signs fade with their houses');}
  assert.equal(behind.image.alpha,1,'a house drawn behind the player stays opaque');
  assert.equal(s.actorRing.visible,false,'the ground marker must not float over a covering roof');
  assert.equal(s.actorOutline,undefined,'no full-body sticker may be composited over a foreground roof');
  assert.ok(s.actor.depth<second.image.depth,'the real player keeps ground-based depth behind the covering house');
  const coveredHotspot={id:'covered-shop',point:{x:0,y:170}};s.hits=[{hotspot:coveredHotspot,object:first.image}];
  assert.equal(s.hitTest({x:0,y:100}),undefined,'a faded roof must not intercept a tap on the revealed road');

  const stable={...allocations};
  for(let i=0;i<100;i++){move(s,2+i%2*.01,2);s.updateOcclusion(1/60);}
  assert.deepEqual(allocations,stable,'walking beneath cached cover performs no canvas reads, texture allocation or display-object creation');
  move(s,2+60/128,2-60/128);settle(s);
  assert.equal(s.occludedCount,1,'leaving one overlapping blocker preserves the other');
  assert.equal(first.image.alpha,1);assert.equal(first.sign.alpha,1);
  assert.equal(second.image.alpha,.35);assert.equal(second.sign.alpha,.35);
  move(s,5,2);settle(s);
  assert.equal(s.occludedCount,0);assert.equal(s.actorRing.visible,true);assert.ok(s.actorRing.depth<s.actor.depth,'the foot marker remains on the ground');
  for(const object of [first,second]){assert.equal(object.image.alpha,1);assert.equal(object.sign.alpha,1,'leaving cover restores mounted signs too');}
  assert.equal(s.fadingOccluders.size,0,'fully restored objects leave the fade set');
  assert.equal(s.hitTest({x:0,y:100}),coveredHotspot,'a restored shop can be selected again');

  move(s,2,2);s.owner.reduced=true;
  assert.equal(s.updateOcclusion(1/60),false,'reduced motion applies cover opacity immediately');
  assert.equal(first.image.alpha,.35);
  move(s,5,2);assert.equal(s.updateOcclusion(1/60),false);assert.equal(first.sign.alpha,1);

  // Pose and outfit caches still use real TextureFrames without overlay textures.
  move(s,2,2);s.owner.reduced=false;
  for(const direction of ['sw','se','nw','ne'])for(let pose=0;pose<3;pose++){s.owner.direction=direction;s.refreshPlayer(pose);s.updateOcclusion(1/60);}
  assert.equal([...s.textures.frames.keys()].filter(key=>key.startsWith('character-frame-')).length,12,'character textures are bounded by the twelve directional poses');
  const cached={...allocations};
  for(let i=0;i<120;i++){s.owner.direction=['sw','se','nw','ne'][i%4];s.refreshPlayer(i%3);s.updateOcclusion(1/60);}
  assert.deepEqual(allocations,cached,'revisiting directional poses reuses character textures');
  s.owner.state.look={top:'changed'};s.refreshPlayer();s.updateOcclusion(1/60);
  assert.equal([...s.textures.frames.keys()].filter(key=>key.startsWith('character-frame-')).length,1,'an outfit change releases the previous character textures');
  assert.equal(s.actorOutline,undefined);assert.equal([...s.textures.frames.keys()].filter(key=>key.startsWith('outline-')).length,0);

  // Rebuild the real scene around tiny map fixtures, avoiding unrelated town art.
  // The new town fixture is placed at the actual town spawn used by rebuild().
  let replacement;
  s.work=()=>{};
  s.town=()=>{replacement=blocker(s,'house-a',{x0:-45,y0:290,x1:45,y1:440},440);};
  const beforeRebuild={...allocations},oldObjects=[...s.staticObjects];
  s.owner.mode='work';s.rebuild();
  assert.ok(oldObjects.every(object=>object.destroyed),'map changes destroy the previous scenery');
  assert.equal(s.occluders.length,0);assert.equal(s.fadingOccluders.size,0);assert.equal(s.occludedCount,0);
  assert.equal(s.actorOutline,undefined);assert.equal(s.actorRing.visible,false);
  assert.equal(s.updateOcclusion(1/60),false);
  s.owner.mode='town';s.rebuild();settle(s);
  assert.equal(s.occludedCount,1,'returning to town recomputes cover at the new spawn');
  assert.equal(replacement.image.alpha,.35);assert.equal(replacement.sign.alpha,.35);
  assert.equal(allocations.readbacks,beforeRebuild.readbacks,'rebuilding a known sprite reuses its alpha mask');
  move(s,10,6.2);settle(s);assert.equal(replacement.image.alpha,1);assert.equal(replacement.sign.alpha,1);

  // The live landmark renderer consumes an isometric sprite once, without
  // re-projecting the already-perspective fullscreen activity photograph.
  const landmarks=scene(),sources=[],queued=[];
  landmarks.owner.hotspots=[];
  landmarks.ensureAssets=kinds=>queued.push(...kinds);
  landmarks.artSource=kind=>{sources.push(kind);return {width:640,height:400};};
  landmarks.artObject=()=>new TestImage(landmarks);
  landmarks.floorRect=()=>{};
  landmarks.placard=()=>new TestContainer(landmarks);
  landmarks.background={fillStyle(){return this;},fillPoints(){return this;}};
  landmarks.textures.get=key=>({getSourceImage:()=>landmarks.textures.frames.get(key).source.image});
  landmarks.textures.frames.set('art-pool-map',frameFor({width:576,height:314},576,314));
  landmarks.landmarks();
  for(const h of landmarks.owner.hotspots){const stand=landmarks.hits.find(hit=>hit.hotspot===h&&hit.object)?.object;assert.deepEqual(h.interactionPoint,stand.getData('interactionPoint'),'leisure E target follows the visible stand');}
  const pool=landmarks.staticObjects.find(image=>image.texture.key==='art-pool-map');
  assert.ok(pool,'the actual town scene uses the transparent pool sprite');
  assert.equal(pool.originX,.5);assert.equal(pool.originY,1);
  assert.ok(Math.abs(pool.displayWidth/pool.displayHeight-576/314)<1e-10);
  assert.ok(pool.depth<landmarks.actor.depth,'pool stays below pedestrians');
  assert.equal(sources.includes('pool'),false,'the activity backdrop is not transformed into a town carpet');
  assert.ok(queued.includes('pool-map'));

  // Camera bounds include zoom and an edge margin. Previously hidden sprites must
  // reappear after panning, resizing, zooming and rebuilding the spatial index.
  const c=scene(),camera=c.cameras.main;
  Object.assign(camera,{width:200,height:100,scrollX:0,scrollY:0,zoom:1});
  function scenery(bounds){const image=new TestImage(c);image.bounds=bounds;c.staticObjects.push(image);return image;}
  const onEdge=scenery({x0:248,y0:10,x1:270,y1:30}),offEdge=scenery({x0:249,y0:10,x1:270,y1:30});
  const left=scenery({x0:0,y0:10,x1:20,y1:30}),farRight=scenery({x0:800,y0:10,x1:830,y1:30});
  c.reindexStatics();c.syncStaticVisibility();
  assert.equal(onEdge.visible,true,'objects touching the camera margin remain visible');assert.equal(offEdge.visible,false);assert.equal(farRight.visible,false);
  const reads=c.staticObjects.map(object=>object.boundsReads);
  for(let i=0;i<40;i++)c.syncStaticVisibility();
  assert.deepEqual(c.staticObjects.map(object=>object.boundsReads),reads,'unchanged cameras do not recompute object bounds');
  camera.scrollX=750;c.syncStaticVisibility();assert.equal(farRight.visible,true);assert.equal(left.visible,false);
  camera.scrollX=0;c.syncStaticVisibility();assert.equal(left.visible,true);assert.equal(farRight.visible,false);
  camera.zoom=.5;c.syncStaticVisibility();assert.equal(offEdge.visible,true,'zooming out reveals objects beyond the prior viewport');
  camera.zoom=1;camera.width=900;c.syncStaticVisibility();assert.equal(farRight.visible,true,'resizing invalidates the cached view');
  camera.width=200;c.syncStaticVisibility();assert.equal(farRight.visible,false);
  c.reindexStatics();c.syncStaticVisibility();assert.equal(farRight.visible,false,'reindexing preserves correct hidden state');
  camera.scrollX=750;c.syncStaticVisibility();assert.equal(farRight.visible,true,'reindexed hidden objects can become visible again');

  // The actual renderer adapter swaps a small static raster at overview zoom,
  // then restores the original art without changing geometry or occlusion alpha.
  const lodScene=scene();lodScene.textures.create=(key,source)=>({add(){lodScene.textures.frames.set(key,frameFor(source,source.width,source.height));},setFilter(){return this;}});
  lodScene.textures.frames.set('large-house',frameFor({width:768,height:1024},768,1024));
  const house=new TestImage(lodScene,25,40,'large-house').setOrigin(.5,1).setDisplaySize(300,400).setAlpha(.4).setDepth(40);
  lodScene.staticImageLod(house,.08);assert.notEqual(house.texture.key,'large-house');
  assert.equal(house.frame.cutHeight,64);const firstLod=house.texture.key,builds=lodScene.staticLod.stats().builds;
  lodScene.staticImageLod(house,.08);assert.equal(house.texture.key,firstLod);assert.equal(lodScene.staticLod.stats().builds,builds);
  lodScene.staticImageLod(house,1);assert.equal(house.texture.key,'large-house');
  assert.deepEqual([house.displayWidth,house.displayHeight,house.originX,house.originY,house.alpha,house.depth],[300,400,.5,1,.4,40]);
} finally {
  if(originalDocument===undefined)delete globalThis.document;else globalThis.document=originalDocument;
  if(originalPhaser===undefined)delete globalThis.__visibilityTestPhaser;else globalThis.__visibilityTestPhaser=originalPhaser;
}
console.log('Visibility: geometry, multiple blockers, sign restoration, map resets, bounded allocation and camera culling passed');
