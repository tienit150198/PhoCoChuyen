import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {test} from 'node:test';
import {build} from 'esbuild';

// Keep the real snapshot adoption, marker lifecycle and navigation; only Phaser
// drawing is replaced so retained marker identities can be asserted directly.
class Visual {
  constructor(x=0,y=0,children=[]){Object.assign(this,{x,y,children,visible:true,alpha:1});}
  getBounds(){return {contains:(x,y)=>x>=this.x-29&&x<=this.x+29&&y>=this.y-34&&y<=this.y+10};}
  fillStyle(){return this;} lineStyle(){return this;} fillEllipse(){return this;}
  fillPoints(){return this;} strokePoints(){return this;} lineBetween(){return this;}
  fillRoundedRect(){return this;} setDepth(depth){this.depth=depth;return this;}
  setSize(){return this;} setOrigin(){return this;} setVisible(visible){this.visible=visible;return this;}
  setText(text){this.text=text;return this;}
  destroy(){this.destroyed=true;for(const child of this.children)child.destroy();}
}
const previous=globalThis.__treasureTestPhaser;
globalThis.__treasureTestPhaser={Scene:class {},Geom:{Point:class {constructor(x,y){Object.assign(this,{x,y});}}}};
const out=await build({stdin:{contents:readFileSync('client/isometric/phaser-world.ts','utf8')+'\nexport {DioramaScene,project};',loader:'ts',resolveDir:resolve('client/isometric')},bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent',plugins:[{
  name:'treasure-drawing-boundary',setup(b){
    b.onResolve({filter:/^(phaser|\/js\/)/},args=>({path:args.path,namespace:'treasure-test'}));
    b.onLoad({filter:/.*/,namespace:'treasure-test'},args=>({contents:args.path==='phaser'?'export default globalThis.__treasureTestPhaser;':args.path.includes('/look.js')?
      'export const figure=()=>({}),defaultLook=()=>({});':args.path.includes('/character-art.js')?
      'export const getCharacterStamp=()=>({}),preloadIllustratedCharacters=()=>{};':'export const kindOf=()=>"home",wordsFor=()=>({});',loader:'js'}));
  }
}]});
const {DioramaScene,PhaserWorld,project}=await import('data:text/javascript;base64,'+Buffer.from(out.outputFiles[0].text).toString('base64'));
function fixture(){
  const owner={mode:'town',treasure:[],hotspots:[],wake(){this.wakes=(this.wakes||0)+1;}},scene=new DioramaScene(owner);
  owner.stage=scene;
  Object.assign(scene,{navigation:{bounds:{x0:0,y0:0,x1:100,y1:100},roads:[{x0:0,y0:0,x1:100,y1:100}],obstacles:[],step:.5,clearance:0},
    add:{graphics:()=>new Visual(),container:(x,y,children)=>new Visual(x,y,children),text:(x,y,text)=>new Visual(x,y).setText(text)},reindexStatics(){}});
  const adopt=rows=>PhaserWorld.prototype.setTreasure.call(owner,rows);
  return {owner,scene,adopt};
}
try {
  await test('chest receives taps above an overlapping service and leaves the service accessible',()=>{
    const {owner,scene,adopt}=fixture(),at={x:34,y:34.8},point=project(at);
    const service={id:'place:bank',approach:at,point},hit={hotspot:service,footprint:{x0:at.x-.45,x1:at.x+.45,y0:at.y-.45,y1:at.y+.45}};
    owner.hotspots.push(service);scene.hits.push(hit);adopt([{id:'bank-chest',...at,count:1}]);
    for(const [x,y] of [[0,0],[10,-10],[0,-20]])assert.equal(scene.hitTest({x:point.x+x,y:point.y+y})?.id,'treasure:bank-chest','visible chest wins equal-depth overlap');
    assert.equal(scene.hitTest(project({x:at.x+.4,y:at.y+.4}))?.id,'place:bank','service remains clickable outside chest bounds');
    scene.hits.reverse();assert.equal(scene.hitTest(point)?.id,'treasure:bank-chest','priority does not depend on insertion order');
    const foreground={id:'place:foreground',point:{...point,y:point.y+1}};
    scene.hits.push({hotspot:foreground,footprint:hit.footprint});assert.equal(scene.hitTest(point)?.id,foreground.id,'ordinary foreground depth still wins');
    scene.hits.pop();adopt([]);assert.equal(scene.hitTest(point)?.id,'place:bank','service receives taps after the last chest is removed');
  });
  await test('all cumulative treasure locations remain available, including stacks larger than one wave',()=>{
    const {owner,scene,adopt}=fixture(),rows=Array.from({length:12},(_,i)=>({id:'chest-'+i,x:i+3,y:5,count:i===0?78:1}));
    adopt(rows);
    assert.equal(owner.treasure.length,12,'older unclaimed locations are not capped to the newest five');
    assert.equal(owner.treasure[0].count,78,'the count survives snapshot adoption');
    assert.equal(scene.hits.length,12);assert.equal(owner.hotspots.length,12);
    assert.match(owner.hotspots[0].label,/78 rương/);assert.match(owner.hotspots[0].label,/Mở 1 rương/);assert.match(owner.hotspots[0].label,/10\.000 xu/);
  });
  await test('claiming one stacked chest updates its target/count without recreating the marker',()=>{
    const {owner,scene,adopt}=fixture();adopt([{id:'oldest',x:4,y:5,count:3}]);
    const marker=scene.hits[0].object;adopt([{id:'next',x:4,y:5,count:2}]);
    assert.equal(scene.hits[0].object,marker,'same location retains the illustrated chest');
    assert.equal(marker.destroyed,undefined);assert.equal(scene.hits[0].hotspot.id,'treasure:next');
    assert.equal(owner.hotspots[0].id,'treasure:next');assert.match(owner.hotspots[0].label,/2 rương/);
    assert.ok(marker.children.some(child=>child.visible&&child.text==='2 rương'),'stack count is visible on the map');
    const wakes=owner.wakes;adopt([{id:'next',x:4,y:5,count:2}]);assert.equal(owner.wakes,wakes,'unchanged snapshots leave the idle map asleep');
    adopt([{id:'last',x:4,y:5,count:1}]);assert.equal(scene.hits[0].object,marker);assert.ok(marker.children.every(child=>child.text!=='2 rương'||!child.visible));
    adopt([]);assert.equal(marker.destroyed,true);assert.equal(scene.hits.length,0);assert.equal(owner.hotspots.length,0);assert.equal(scene.staticObjects.length,0);
  });
  await test('map changes and removed locations clear stale markers and claim targets',()=>{
    const {owner,scene,adopt}=fixture();adopt([{id:'first',x:4,y:5,count:2}]);const first=scene.hits[0].object;
    owner.mode='work';scene.syncTreasure();assert.equal(first.destroyed,true);assert.equal(scene.hits.length,0);assert.equal(owner.hotspots.length,0);
    owner.mode='town';scene.syncTreasure();assert.equal(scene.hits.length,1);assert.notEqual(scene.hits[0].object,first);
    const second=scene.hits[0].object;adopt([{id:'moved',x:6,y:5,count:4}]);assert.equal(second.destroyed,true);assert.equal(scene.hits.length,1);assert.equal(owner.hotspots[0].id,'treasure:moved');
  });
} finally {
  if(previous===undefined)delete globalThis.__treasureTestPhaser;else globalThis.__treasureTestPhaser=previous;
}
