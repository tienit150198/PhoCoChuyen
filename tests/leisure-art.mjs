import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync(new URL('../public/js/isometric/leisure-art.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
function harness(){
 const requests=[],canvases=[],draws=[],overlays=[];let fail=false,failedKey='';
 class Image{constructor(){this.naturalWidth=960;this.naturalHeight=600;this.rasterAvailable=true;}get width(){return this.naturalWidth;}get height(){return this.naturalHeight;}set src(path){this.path=path;if(path.includes('fishing-actions')){this.naturalWidth=800;this.naturalHeight=400;}requests.push(path);queueMicrotask(()=>fail||failedKey&&path.includes(failedKey)?this.onerror?.():this.onload?.());}}
 const doc={createElement(){const canvas={width:0,height:0,rasterAvailable:false,getContext:()=>({drawImage(...args){canvas.rasterAvailable=true;draws.push(args);},clearRect(){},imageSmoothingEnabled:true,
  getImageData(x,y,w,h){const data=new Uint8ClampedArray(w*h*4);for(let row=Math.floor(h*.15);row<h*.9;row++)for(let col=Math.floor(w*.3);col<w*.7;col++)data.set([170,140,100,255],(row*w+col)*4);return {data};},putImageData(){}})};canvases.push(canvas);return canvas;}};
 const context=vm.createContext({Image,document:doc,Map,Promise,setTimeout,clearTimeout,console,Uint8ClampedArray,getCharacterStamp:o=>({canvas:{},width:120,height:160,options:o}),recolourPixel:p=>p,paintWardrobeOverlay:(ctx,options,box,alignment)=>overlays.push({options,box,alignment}),defaultLook:()=>({}),art:()=>({c:'#aabbcc'}),topColour:()=> '#aabbcc',hairColour:()=> '#aabbcc'});
 vm.runInContext(source+'\nglobalThis.load=loadLeisureArt;globalThis.cell=fishingCell;',context);
 return {load:context.load,cell:context.cell,requests,canvases,draws,overlays,loseCanvasBitmaps(){for(const canvas of canvases)canvas.rasterAvailable=false;},fail(value){fail=value;},failKey(value){failedKey=value;}};
}
test('place opening loads at most three images and shares only two illustrated backgrounds',async()=>{
 const h=harness();const lake=await h.load('fishing');assert.equal(h.requests.length,3);
 assert.equal(h.requests.some(p=>p.endsWith('leisure-pool.webp')),false);
 assert.equal(lake.pixelated,false);const first=lake.background('fishing');assert.equal(first.width,960);assert.equal(first.height,600);
 const boat=await h.load('boat');assert.equal(h.requests.length,3);assert.equal(boat.background('boat'),first);
 const pool=await h.load('pool');assert.equal(h.requests.length,4);pool.background('pool');
 assert.equal(h.canvases.length,0,'backdrops do not duplicate decoded images in volatile canvas stores');assert.equal(pool.asset('boat'),lake.asset('boat'));
 assert.equal(first,lake.asset('lake'));assert.equal(pool.background('pool'),pool.asset('pool'));
 assert.equal(pool.background('pool').width,960);assert.equal(pool.background('pool').height,600,'pool keeps the image aspect ratio shared by the navigation polygon');
});

test('an open scene keeps a drawable backdrop after offscreen canvas bitmaps are discarded',async()=>{
 const h=harness(),art=await h.load('fishing'),capturedBackground=art.background('fishing');
 art.fishingCharacter({gender:'female',pose:'caught'});
 assert.ok(h.canvases.length>0,'fishing supplies other canvas stores for the loss boundary');
 h.loseCanvasBitmaps();
 assert.equal(capturedBackground.rasterAvailable,true,'the captured backdrop cannot become the blank cached canvas after a bitmap discard');
 assert.equal(art.background('boat'),capturedBackground,'fishing and rowing reuse the surviving lake source');
 const reopened=await h.load('fishing');assert.equal(reopened.background('fishing'),capturedBackground);
 assert.equal(h.requests.length,3,'recovering the frame does not require a reload or extra fetch');
});

test('fishing atlas keeps the strict four poses and two gender rows with a shared foot baseline',async()=>{
 const h=harness(),art=await h.load('fishing');
 assert.equal(h.cell('male','ready').x,0);assert.equal(h.cell('male','caught').x,3);assert.equal(h.cell('female','reel').y,1);
 const male=art.fishingCharacter({gender:'male',pose:'cast',look:{top:'ao_hoodie'}}),female=art.fishingCharacter({gender:'female',pose:'caught'});
 assert.equal(male.ready,true);assert.equal(male.pose,'cast');assert.equal(female.gender,'female');assert.equal(female.canvas.height,160);assert.equal(male.canvas.width,120);
 const cells=h.draws.filter(args=>args[0]?.path?.includes('fishing-actions'));assert.equal(cells.length,8);assert.equal(cells[7][1],600);assert.equal(cells[7][2],200);
 assert.equal(art.fishingCharacter({gender:'male',pose:'cast',look:{top:'ao_hoodie'}}),male,'pose and wardrobe stamps are cached');
});

test('optional fishing art failure falls back without animation-frame retries and reopening retries once',async()=>{
 const h=harness();h.failKey('fishing-actions');const art=await h.load('fishing');assert.match(art.notice,/Mở lại/);
 const before=h.requests.length;for(let i=0;i<60;i++)art.fishingCharacter({gender:'female',pose:'cast'});assert.equal(h.requests.length,before);
 h.failKey('');const retry=await h.load('fishing');assert.equal(h.requests.length,before+1);assert.equal(retry.notice,'');assert.equal(retry.fishingCharacter({pose:'reel'}).ready,true);
});
test('failed asset rejects once and the next explicit opening can retry successfully',async()=>{
 const h=harness();h.fail(true);await assert.rejects(h.load('fishing'),/Thử mở lại/);
 const failed=h.requests.length;h.fail(false);const art=await h.load('fishing');
 assert.ok(h.requests.length>failed);assert.ok(h.requests.length<=failed+3);assert.ok(art.background('fishing'));
});
test('character helper uses shared wardrobe atlas and maps steps to walk frames',async()=>{
 const h=harness(),art=await h.load('fishing');
 const stamp=art.character({step:3,direction:'sw',look:{top:'ao_hoodie'},gender:'female'});
 assert.equal(stamp.options.walkFrame,2);assert.equal(stamp.options.direction,'sw');assert.equal(stamp.width,120);
});

test('every fishing pose retains saved skirt and accessories with pose-specific body and head alignment',async()=>{
 const h=harness(),art=await h.load('fishing'),hands={ready:[2,-11],cast:[8,-18],reel:[6,-14],caught:[8,-20]};
 for(const pose of ['ready','cast','reel','caught']){
  const stamp=art.fishingCharacter({gender:'female',pose,look:{bottom:'vay_xoe',acc:'non_la'}}),overlay=h.overlays.at(-1);
  assert.ok(overlay,'fishing atlas calls the shared wardrobe overlay');
  assert.equal(overlay.options.look.bottom,'vay_xoe');assert.equal(overlay.options.look.acc,'non_la');assert.equal(overlay.options.direction,'se');
  assert.ok(Number.isFinite(overlay.alignment.faceX)&&Number.isFinite(overlay.alignment.bodyX));
  assert.equal(stamp.hand.x,hands[pose][0]);assert.equal(stamp.hand.y,hands[pose][1],'overlay never changes the rod hand anchor');
 }
 assert.notEqual(h.overlays[0].alignment.bodyX,h.overlays[2].alignment.bodyX,'leaning reel pose follows its torso');
 art.fishingCharacter({pose:'reel',look:{acc:'tui_cheo'}});assert.equal(h.overlays.at(-1).options.look.acc,'tui_cheo');
});
