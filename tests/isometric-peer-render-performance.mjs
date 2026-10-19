import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {test} from 'node:test';
import {build} from 'esbuild';

// Exercise the production scene, pose cache and route interpolation. Only the
// browser image compositor and Phaser display objects are instrumented doubles.
const counters={lookups:0,stamps:0,depths:0,positions:0,textureSwaps:0,readbacks:0};
class Image {
  visible=true; x=NaN; y=NaN; depth=NaN;
  constructor(key){this.key=key;}
  setOrigin(){return this;} setScale(){return this;} setRotation(){return this;} setAlpha(){return this;}
  setPosition(x,y){counters.positions++;Object.assign(this,{x,y});return this;}
  setDepth(depth){counters.depths++;this.depth=depth;return this;}
  setVisible(visible){this.visible=visible;return this;}
  setTexture(key){counters.textureSwaps++;this.key=key;return this;}
  setText(text){this.text=text;return this;}
  setColor(){return this;}   // ⚔️ the bang tag's ink (phaser-world.ts)
  destroy(){this.destroyed=true;}
}
const original=globalThis.__peerRenderTest;
globalThis.__peerRenderTest={Phaser:{Scene:class {},Textures:{FilterMode:{LINEAR:1}}},
  stamp(){counters.stamps++;return {canvas:{width:120,height:160},ready:true};}};
const out=await build({stdin:{contents:readFileSync('client/isometric/phaser-world.ts','utf8')+'\nexport {DioramaScene};',loader:'ts',resolveDir:resolve('client/isometric')},bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent',plugins:[{
  name:'peer-render-boundary',setup(b){
    b.onResolve({filter:/^(phaser|\/js\/)/},args=>({path:args.path,namespace:'peer-test'}));
    b.onLoad({filter:/.*/,namespace:'peer-test'},args=>({contents:args.path==='phaser'?'export default globalThis.__peerRenderTest.Phaser;':args.path.includes('/look.js')?
      'export const figure=()=>({}),defaultLook=()=>({hair:"toc_ngan",top:"ao_thun_kem"});':args.path.includes('/character-art.js')?
      'export const getCharacterStamp=globalThis.__peerRenderTest.stamp,preloadIllustratedCharacters=()=>{};':'export const kindOf=()=>"home",wordsFor=()=>({});',loader:'js'}));
  }
}]});
const {DioramaScene,PhaserWorld}=await import('data:text/javascript;base64,'+Buffer.from(out.outputFiles[0].text).toString('base64'));
const reset=()=>{for(const key of Object.keys(counters))counters[key]=0;};
test('social anchors follow interpolated actors, zoom and mode; picking uses visible actors',()=>{
  const {scene,owner}=fixture(1);scene.syncRemotePlayers();
  const actor=scene.remoteActors.get('peer-0');
  const anchor=scene.socialAnchor('peer-0');
  assert.deepEqual(anchor,{x:390,y:174});
  assert.equal(scene.hitRemote({x:actor.image.x,y:actor.image.y-50}),'peer-0');
  actor.image.setPosition(64,400);scene.cameras.main.zoom=.5;
  assert.deepEqual(scene.socialAnchor('peer-0'),{x:422,y:252.5});
  actor.image.visible=false;assert.equal(scene.socialAnchor('peer-0'),null);
  assert.equal(scene.hitRemote({x:64,y:350}),null);
  owner.mode='work';assert.equal(scene.socialAnchor('peer-0'),null);
});
function fixture(count=29){
  const owner={mode:'town',reduced:false,time:1,remotePlayers:Array.from({length:count},(_,i)=>({pid:'peer-'+i,name:'Bạn '+i,look:{top:'ao_thun_kem'},gender:'male',x:6+i*.02,y:6,direction:'se'}))};
  const textures=new Map(),texture=key=>{const t={add(){return t;},setFilter(){return t;}};textures.set(key,t);return t;};
  const scene=new DioramaScene(owner);
  Object.assign(scene,{sys:{isActive:()=>true},cameras:{main:{scrollX:-390,scrollY:70,width:780,height:630,zoom:1}},
    navigation:{bounds:{x0:-100,y0:-100,x1:100,y1:100},roads:[{x0:-100,y0:-100,x1:100,y1:100}],obstacles:[],step:.5,clearance:0},
    add:{image:(_x,_y,key)=>new Image(key),text:(_x,_y,text)=>new Image().setText(text)},
    textures:{exists:key=>textures.has(key),remove:key=>textures.delete(key),create:key=>texture(key),addCanvas(key){counters.readbacks++;return texture(key);}}});
  const lookup=scene.characterTexture;
  scene.characterTexture=function(...args){counters.lookups++;return lookup.apply(this,args);};
  return {scene,owner,textures};
}

try {
  await test('29 stationary street avatars do no pose-cache or depth work over 120 frames',t=>{
    const {scene}=fixture();scene.syncRemotePlayers();reset();
    for(let i=0;i<120;i++)scene.stepRemotePlayers(1+i/60);
    t.diagnostic(JSON.stringify(counters));
    assert.equal(counters.lookups,0,'unchanged peers must not normalize/serialize their wardrobe every frame');
    assert.equal(counters.depths,0,'unchanged feet must not queue a full Phaser display-list depth sort');
    assert.equal(counters.positions,0,'stationary peers keep their transforms');
  });
  await test('offscreen peers retain live state without creating poses or keeping the scene awake',t=>{
    const {scene,owner}=fixture();scene.cameras.main.scrollX=5000;reset();scene.syncRemotePlayers();
    for(let i=1;i<=120;i++){
      owner.time=1+i/60;
      if(i%18===0){owner.remotePlayers=owner.remotePlayers.map(p=>({...p,x:p.x+.2}));scene.syncRemotePlayers();}
      assert.equal(scene.stepRemotePlayers(owner.time),false,'movement outside the view cannot keep the map rendering');
    }
    t.diagnostic(JSON.stringify(counters));
    assert.equal(counters.stamps,0,'do not synchronously recolour 29 hidden avatars and their walk frames');
    assert.ok([...scene.remoteActors.values()].every(a=>!a.image.visible&&!a.tag.visible));
    owner.remotePlayers[0].look={top:'ao_so_mi'};scene.syncRemotePlayers();
    scene.cameras.main.scrollX=-390;scene.stepRemotePlayers(owner.time+.4);
    assert.ok([...scene.remoteActors.values()].every(a=>a.image.visible),'panning back reveals current avatars');
    const actor=scene.remoteActors.get('peer-0'),peer=owner.remotePlayers[0];
    assert.deepEqual([actor.at.x,actor.at.y],[peer.x,peer.y],'hidden movement is not discarded');
    assert.equal(actor.peer.look.top,'ao_so_mi','hidden outfit updates are not discarded');
    assert.ok(counters.stamps>=29,'first visible frame receives the correct real textures');
  });
  await test('a live packet does not swap all moving peers to idle and back',()=>{
    const {scene,owner}=fixture(1);scene.syncRemotePlayers();
    owner.time=1.3;owner.remotePlayers[0]={...owner.remotePlayers[0],x:6.2};scene.syncRemotePlayers();
    scene.stepRemotePlayers(1.33);const actor=scene.remoteActors.get('peer-0'),walking=actor.texture;
    reset();owner.time=1.34;owner.remotePlayers[0]={...owner.remotePlayers[0],x:6.3};scene.syncRemotePlayers();
    assert.equal(actor.texture,walking);assert.equal(counters.textureSwaps,0,'a packet in the same gait does not cause two unnecessary texture swaps');
    scene.stepRemotePlayers(2);assert.notEqual(actor.texture,walking,'arrival restores idle');
    const idle=actor.texture;owner.remotePlayers[0]={...owner.remotePlayers[0],look:{top:'ao_so_mi'}};scene.syncRemotePlayers();
    assert.notEqual(actor.texture,idle,'a stationary visible outfit change renders immediately');
  });
  await test('character textures keep immutable canvas sources without duplicate pixel readback',()=>{
    const {scene}=fixture(1);reset();scene.syncRemotePlayers();
    assert.equal(counters.stamps,1);assert.equal(counters.readbacks,0,'Phaser CanvasTexture allocates an unnecessary second RGBA copy of every stamp');
    assert.equal(scene.characterFrames.size,1);scene.stepRemotePlayers(2);assert.equal(scene.characterFrames.size,1);
    const actor=scene.remoteActors.get('peer-0'),before=actor.texture;
    scene.characterRevision++;scene.stepRemotePlayers(3);assert.notEqual(actor.texture,before,'a loaded atlas invalidates cached visible poses');
    scene.owner.remotePlayers=[];scene.syncRemotePlayers();assert.equal(scene.characterFrames.size,0);assert.equal(actor.image.destroyed,true);assert.equal(actor.tag.destroyed,true);
  });
  await test('hidden-only live packets do not wake an idle world but visible changes do',()=>{
    const {scene,owner}=fixture(1);scene.cameras.main.scrollX=5000;
    let wakes=0;const world={mode:'town',stage:scene,remoteSignature:'',wake(){wakes++;}};
    // Keep the real scene tied to the list published by the actual world method.
    Object.defineProperty(owner,'remotePlayers',{get:()=>world.remotePlayers});
    const sample=[{pid:'peer',name:'Bạn',look:{},gender:'male',x:6,y:6,direction:'se'}];
    PhaserWorld.prototype.setRemotePlayers.call(world,sample);assert.equal(wakes,0);
    PhaserWorld.prototype.setRemotePlayers.call(world,[{...sample[0],x:6.2}]);assert.equal(wakes,0);
    scene.cameras.main.scrollX=-390;scene.stepRemotePlayers(2);
    PhaserWorld.prototype.setRemotePlayers.call(world,[{...sample[0],x:6.3}]);assert.equal(wakes,1);
  });
  await test('a stationary local player does not sort the whole display list while peers move',()=>{
    const {scene,owner}=fixture(0);Object.assign(owner,{walkDistance:0,direction:'se',player:{x:6,y:6}});
    scene.actor=new Image('local');scene.positionPlayer(false);reset();
    for(let i=0;i<120;i++)scene.positionPlayer(false);
    assert.equal(counters.depths,0);assert.equal(counters.positions,0);
    owner.player.y+=.1;scene.positionPlayer(false);assert.equal(counters.depths,1);assert.equal(counters.positions,1,'real movement still updates foot depth');
  });
  await test('an incoming route crossing the viewport wakes even when both endpoints are offscreen',()=>{
    const {scene,owner}=fixture(1),start={x:.6875,y:11.3125},end={x:11.3125,y:.6875};
    owner.remotePlayers[0]={...owner.remotePlayers[0],...start};scene.syncRemotePlayers();
    const actor=scene.remoteActors.get('peer-0');assert.equal(actor.image.visible,false);
    owner.time=2;owner.remotePlayers[0]={...owner.remotePlayers[0],...end};
    assert.equal(scene.syncRemotePlayers(),true,'a segment through the view must schedule interpolation before its endpoint is visible');
    scene.stepRemotePlayers(2.12);assert.equal(actor.image.visible,true,'the actor appears while traversing the view');
    assert.ok(Math.abs(actor.image.x)<1e-8);
    assert.equal(scene.stepRemotePlayers(2.3),false);assert.equal(actor.image.visible,false,'offscreen arrival can sleep again');
  });
  await test('the stationary foot marker does not requeue depth sorts during remote movement',()=>{
    const {scene,owner}=fixture(0);Object.assign(owner,{player:{x:6,y:6}});
    scene.actor=new Image('local').setDepth(384.5);scene.actorRing=new Image('ring');scene.updateOcclusion(1/60);reset();
    for(let i=0;i<120;i++)scene.updateOcclusion(1/60);
    assert.equal(counters.depths,0);assert.equal(counters.positions,0);
  });
  await test('peer traffic cannot wake a covered world and closing the modal restores the latest avatar',()=>{
    const originalDocument=globalThis.document,environment={hidden:false,modal:true};
    globalThis.document={get hidden(){return environment.hidden;},querySelector:()=>environment.modal?{}:null};
    try{
      const {scene,owner}=fixture(1);Object.setPrototypeOf(owner,PhaserWorld.prototype);
      const calls={wake:0,sleep:0};Object.assign(owner,{visible:true,_paused:false,keys:new Set(),movementInput:{x:0,y:0},stage:scene,
        engine:{loop:{wake(){calls.wake++;},sleep(){calls.sleep++;}}}});
      const initial=[...owner.remotePlayers];owner.setRemotePlayers(initial);assert.equal(calls.wake,0);assert.equal(calls.sleep,1);
      owner.time=1.3;owner.setRemotePlayers([{...initial[0],name:'Tên mới',x:6.2,look:{top:'ao_so_mi'}}]);assert.equal(calls.wake,0);
      environment.hidden=true;environment.modal=false;owner.setRemotePlayers([{...initial[0],x:6.3,look:{top:'ao_len'}}]);assert.equal(calls.wake,0);
      environment.hidden=false;owner.wake();assert.equal(calls.wake,1);scene.stepRemotePlayers(2);
      const actor=scene.remoteActors.get('peer-0');assert.equal(actor.image.visible,true);assert.equal(actor.peer.look.top,'ao_len');assert.equal(actor.at.x,6.3);
      const key=actor.texture;scene.characterRevision++;scene.stepRemotePlayers(3);assert.notEqual(actor.texture,key,'the loaded atlas still refreshes a retained peer');
    }finally{if(originalDocument===undefined)delete globalThis.document;else globalThis.document=originalDocument;}
  });
  await test('labels retain their names across culling and respond immediately to zoom and renaming',()=>{
    const {scene,owner}=fixture(1);scene.syncRemotePlayers();const actor=scene.remoteActors.get('peer-0');assert.equal(actor.tag.visible,true);
    scene.cameras.main.zoom=.1;scene.stepRemotePlayers(2);assert.equal(actor.tag.visible,false);
    owner.remotePlayers[0]={...owner.remotePlayers[0],name:'Lan'};scene.syncRemotePlayers();assert.equal(actor.tag.text,'Lan');
    scene.cameras.main.scrollX=5000;scene.stepRemotePlayers(3);assert.equal(actor.image.visible,false);
    scene.cameras.main.scrollX=-390;scene.cameras.main.zoom=1;scene.stepRemotePlayers(4);assert.equal(actor.tag.visible,true);assert.equal(actor.tag.text,'Lan');
  });
  await test('the shared-island world runs inside its own dialog but pauses under a second dialog',()=>{
    const originalDocument=globalThis.document;let other=false;
    globalThis.document={hidden:false,querySelector:selector=>selector.includes(':not([data-shared-island])')?(other?{}:null):{}};
    try{
      const world=Object.create(PhaserWorld.prototype);Object.assign(world,{canvas:{closest:()=>({})},visible:true,_paused:false,mode:'town',destroyed:false,wake(){}});
      assert.equal(world.shouldSleep(),false,'its own fullscreen modal is the active game surface');world.setMovementInput(1,1);assert.ok(world.movementInput.x>0&&world.movementInput.y>0);
      other=true;assert.equal(world.shouldSleep(),true,'nested dialogs still pause the map');world.setMovementInput(1,1);assert.deepEqual(world.movementInput,{x:0,y:0});
      other=false;world.canvas.closest=()=>null;assert.equal(world.shouldSleep(),true,'the regular island still pauses for any normal dialog');
    }finally{globalThis.document=originalDocument;}
  });
} finally {
  if(original===undefined)delete globalThis.__peerRenderTest;else globalThis.__peerRenderTest=original;
}
