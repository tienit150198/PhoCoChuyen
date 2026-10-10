import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {test} from 'node:test';
import {build} from 'esbuild';

// Run the production world, event listeners, movement and scene camera methods.
// Only browser/Phaser services and unrelated scene artwork are replaced.
class BrowserTarget extends EventTarget {
  // Node's EventTarget requires capture in an object when removing listeners.
  addEventListener(type,fn,options){super.addEventListener(type,fn,typeof options==='boolean'?{capture:options}:options);}
  removeEventListener(type,fn,options){super.removeEventListener(type,fn,typeof options==='boolean'?{capture:options}:options);}
}
class Canvas extends BrowserTarget {
  width=1000;height=700;style={};dataset={};rect={left:0,top:0,width:1000,height:700};
  getBoundingClientRect(){return this.rect;}
  getContext(){return {};}
  setAttribute(){}focus(){}setPointerCapture(){}closest(){return null;}
}
class Observer {observe(){}disconnect(){}}
class Camera {
  constructor(width,height){Object.assign(this,{width,height,scrollX:0,scrollY:0,zoom:1});}
  setScroll(x,y){this.scrollX=x;this.scrollY=y;return this;}
  setZoom(value){this.zoom=value;return this;}
  setSize(width,height){Object.assign(this,{width,height});return this;}
  centerOn(x,y){return this.setScroll(x-this.width/2,y-this.height/2);}
  setBackgroundColor(){return this;}
}
class Graphic {setDepth(){return this;}destroy(){}}
class Game {
  constructor(config){
    this.stage=config.scene[0];this.loop={running:true,wake(){this.running=true;},sleep(){this.running=false;}};
    this.scale={width:config.width,height:config.height,resize:(width,height)=>{Object.assign(this.scale,{width,height});Object.assign(config.canvas,{width,height});}};
    this.textures={exists:()=>false};
    this.stage.load={isLoading:()=>false};
    Object.assign(this.stage,{sys:{isActive:()=>true},children:{length:0},cameras:{main:new Camera(config.width,config.height)},add:{graphics:()=>new Graphic()},tweens:{getTweens:()=>[]}});
  }
  destroy(){}
}
const original=Object.fromEntries(['window','document','location','ResizeObserver','MutationObserver','__cameraTestPhaser'].map(key=>[key,globalThis[key]]));
const doc=new BrowserTarget();Object.assign(doc,{hidden:false,body:{},querySelector:()=>null,createElement:()=>new Canvas()});
Object.assign(globalThis,{window:new BrowserTarget(),document:doc,location:{search:''},ResizeObserver:Observer,MutationObserver:Observer,
  __cameraTestPhaser:{Scene:class {},Game,CANVAS:1,Scale:{NONE:0,NO_CENTER:0},Math:{Clamp:(v,min,max)=>Math.max(min,Math.min(max,v))}}});

try {
  const source=readFileSync('client/isometric/phaser-world.ts','utf8');
  const out=await build({stdin:{contents:source+'\nexport {DioramaScene};',loader:'ts',resolveDir:resolve('client/isometric')},bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent',plugins:[{
    name:'camera-browser-boundary',setup(b){
      b.onResolve({filter:/^(phaser|\/js\/)/},args=>({path:args.path,namespace:'camera-test'}));
      b.onLoad({filter:/.*/,namespace:'camera-test'},args=>({contents:args.path==='phaser'?'export default globalThis.__cameraTestPhaser;':args.path.includes('/look.js')?
        'export const figure=()=>({}),defaultLook=()=>({});':args.path.includes('/character-art.js')?
        'export const getCharacterStamp=()=>({}),preloadIllustratedCharacters=()=>{};':'export const kindOf=()=>"home",wordsFor=()=>({});',loader:'js'}));
    }
  }]});
  const {PhaserWorld}=await import('data:text/javascript;base64,'+Buffer.from(out.outputFiles[0].text).toString('base64'));
  function fixture(t){
    const canvas=new Canvas(),world=new PhaserWorld(canvas,()=>{}),stage=world.engine.stage;
    // Navigation remains real, with ample empty ground so camera assertions are
    // independent of town-art changes or collisions at a particular shop.
    stage.navigation={bounds:{x0:-100,y0:-100,x1:100,y1:100},roads:[{x0:-100,y0:-100,x1:100,y1:100}],obstacles:[],step:.25,clearance:0};
    Object.assign(stage,{town(){},work(){},reindexStatics(){},refreshPlayer(){return false;},positionPlayer(){},updateOcclusion(){return false;},syncRemotePlayers(){},stepRemotePlayers(){return false;},highlight(){},mark(){},hitTest(){}});
    world.boot(stage);
    t.after(()=>world.destroy());
    return {world,stage,canvas,camera:stage.cameras.main};
  }
  const view=c=>({x:c.scrollX,y:c.scrollY,zoom:c.zoom});
  const center=c=>({x:c.scrollX+c.width/2,y:c.scrollY+c.height/2});
  function pointer(f,type,x,y,id=1){const e=new Event(type,{cancelable:true});Object.assign(e,{clientX:x,clientY:y,pointerId:id});f.canvas.dispatchEvent(e);}
  function keyboard(f,type,key){const e=new Event(type,{cancelable:true});Object.assign(e,{key});f.canvas.matches=()=>false;f.canvas.dispatchEvent(e);}
  function drag(f){pointer(f,'pointerdown',400,300);pointer(f,'pointermove',-1000,900);pointer(f,'pointerup',-1000,900);}
  function walk(f,count=10){f.world.setMovementInput(1,0);for(let i=0;i<count;i++)f.world.step(1/60);f.world.setMovementInput(0,0);}
  function resize(f,width,height){Object.assign(f.canvas.rect,{width,height});f.world.resize();}

  await test('releasing a drag keeps the chosen view during autowalk and route completion',t=>{
    const f=fixture(t);let arrived=0;f.world.player.path=[{x:10,y:6.2}];f.world.player.goal={x:10,y:6.2};f.world.pending=()=>arrived++;
    f.world.step(1/60);drag(f);const chosen=view(f.camera),before=f.world.player.x;
    f.world.step(1/60);assert.ok(f.world.player.x>before,'the player continues walking after pan');
    assert.deepEqual(view(f.camera),chosen,'release must not resume camera follow');
    for(let i=0;i<240;i++)f.world.step(1/60);
    assert.equal(arrived,1);assert.equal(f.world.player.path.length,0);assert.deepEqual(view(f.camera),chosen,'arrival does not reset browse');
    assert.equal(f.world.engine.loop.running,false,'idle browse still lets the existing loop sleep');
  });
  await test('joystick and WASD movement preserve browse until explicit recenter or Home',t=>{
    const f=fixture(t);drag(f);const chosen=view(f.camera),before={...f.world.player};walk(f,30);
    assert.notEqual(f.world.player.x,before.x);assert.deepEqual(view(f.camera),chosen,'joystick does not resume follow');
    keyboard(f,'keydown','w');for(let i=0;i<30;i++)f.world.step(1/60);keyboard(f,'keyup','w');
    assert.deepEqual(view(f.camera),chosen,'WASD does not resume follow');
    f.world.recenter();assert.notDeepEqual(view(f.camera),chosen);const recentered=view(f.camera);walk(f,240);
    assert.notDeepEqual(view(f.camera),recentered,'recenter restores follow while walking');
    drag(f);const panned=view(f.camera);keyboard(f,'keydown','Home');assert.notDeepEqual(view(f.camera),panned);const home=view(f.camera);walk(f,240);
    assert.notDeepEqual(view(f.camera),home,'Home restores follow while walking');
  });
  await test('manual camera center and zoom survive resize across desktop and mobile breakpoints',t=>{
    const f=fixture(t);drag(f);const chosen=center(f.camera),zoom=f.camera.zoom;
    for(const [width,height] of [[850,600],[390,740],[1300,800]]){
      resize(f,width,height);assert.deepEqual(center(f.camera),chosen,'resize preserves the viewed world point');assert.equal(f.camera.zoom,zoom,'browse retains the chosen zoom');
      const resized=view(f.camera);walk(f);assert.deepEqual(view(f.camera),resized,'resize must not restore following');
    }
  });
  await test('layout refresh and relocation keep browse, while switching scene mode restores follow',t=>{
    const f=fixture(t);drag(f);const chosen=view(f.camera);
    f.world.update({current:'home'},{catalogue:[]});assert.deepEqual(view(f.camera),chosen,'state layout refresh keeps camera');
    f.stage.navigation.obstacles=[{x0:5,y0:5,x1:7,y1:7}];f.stage.rebuild();
    assert.ok(f.world.player.x!==6.2||f.world.player.y!==6.2,'fixture forces layout relocation');assert.deepEqual(view(f.camera),chosen,'relocating a blocked player cannot reset browse');
    f.world.setMode('work');assert.notDeepEqual(view(f.camera),chosen,'changing scene mode resets the view');
    const reset=view(f.camera);walk(f,240);assert.notDeepEqual(view(f.camera),reset,'scene switch restores follow');
    drag(f);const workView=view(f.camera);f.world.update({current:'grocery',careers:{}},{catalogue:[]});
    assert.deepEqual(view(f.camera),workView,'a layout change inside the same scene mode keeps browse');
  });
  for(const gesture of ['wheel','pinch'])await test(gesture+' chooses a persistent view and preserves the gesture anchor',t=>{
      const f=fixture(t);f.camera.setScroll(2000,1000);
      const initialZoom=f.camera.zoom,anchor=f.world.worldPoint(gesture==='wheel'?{x:240,y:220}:{x:300,y:220});
      if(gesture==='wheel'){
        const e=new Event('wheel',{cancelable:true});Object.assign(e,{clientX:240,clientY:220,deltaY:-180});f.canvas.dispatchEvent(e);
      }else{
        pointer(f,'pointerdown',200,220,1);pointer(f,'pointerdown',400,220,2);
        const chosen=view(f.camera);walk(f);assert.deepEqual(view(f.camera),chosen,'placing a second finger suspends follow before the first pinch move');
        pointer(f,'pointermove',500,220,2);pointer(f,'pointerup',500,220,2);pointer(f,'pointerup',200,220,1);
      }
      const after=f.world.worldPoint(gesture==='wheel'?{x:240,y:220}:{x:350,y:220});
      assert.ok(Math.hypot(after.x-anchor.x,after.y-anchor.y)<1e-8,'zoom keeps the same world point under the gesture');
      const chosen=view(f.camera);assert.notEqual(chosen.zoom,initialZoom);walk(f,30);assert.deepEqual(view(f.camera),chosen,gesture+' persists after release');
  });
  for(const kind of ['district','career','overview','zoom'])await test(kind+' controls preserve manual browsing through movement',t=>{
      const f=fixture(t);
      if(kind==='district')assert.equal(f.world.focusDistrict(f.world.townDistricts().at(-1).id),true);
      if(kind==='career'){f.stage.buildings=[{id:'home',at:{x:50,y:2}}];f.world.focusCareer('home');}
      if(kind==='overview')f.world.overviewIsland();
      if(kind==='zoom'){drag(f);f.world.zoomBy(1.2);}
      const chosen=view(f.camera);walk(f,30);assert.deepEqual(view(f.camera),chosen,kind+' must not recenter on movement');
      if(kind==='overview')assert.equal(f.stage.islandOverview,true,'overview remains selected until an explicit camera action');
  });
  await test('cancelled drags and window blur preserve the chosen view',t=>{
    const f=fixture(t);pointer(f,'pointerdown',400,300);pointer(f,'pointermove',-1000,900);pointer(f,'pointercancel',-1000,900);
    const chosen=view(f.camera);walk(f,30);assert.deepEqual(view(f.camera),chosen,'pointer cancellation does not resume follow');
    window.dispatchEvent(new Event('blur'));walk(f,30);assert.deepEqual(view(f.camera),chosen,'returning after blur does not resume follow');
  });
  await test('plain walking and a tap without a drag retain the default follow behavior',t=>{
    const f=fixture(t);const start=view(f.camera);pointer(f,'pointerdown',400,300);pointer(f,'pointerup',401,301);walk(f,240);
    assert.notDeepEqual(view(f.camera),start,'tap does not silently disable following');
  });
  await test('the public camera mode and opt-in diagnostics expose browsing and recenter transitions',t=>{
    const f=fixture(t);assert.equal(f.world.cameraMode,'follow');assert.equal(f.world.debug().cameraMode,'follow');
    drag(f);assert.equal(f.world.cameraMode,'browse');assert.equal(f.world.debug().cameraMode,'browse');
    f.world.recenter();assert.equal(f.world.cameraMode,'follow');assert.equal(f.world.debug().cameraMode,'follow');
  });
} finally {
  for(const [key,value] of Object.entries(original))if(value===undefined)delete globalThis[key];else globalThis[key]=value;
}
