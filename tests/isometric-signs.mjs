import assert from 'node:assert/strict';
import test from 'node:test';
import {existsSync,readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {build} from 'esbuild';
import {PLACES} from '../public/js/iso-guide.js';
import sharp from 'sharp';

class Display {
  constructor(x=0,y=0){Object.assign(this,{x,y,scaleX:1,scaleY:1,depth:0,visible:true,data:{},width:0,height:0});}
  setPosition(x,y){Object.assign(this,{x,y});return this;}
  setOrigin(x,y=x){Object.assign(this,{originX:x,originY:y});return this;}
  setScale(x,y=x){Object.assign(this,{scaleX:x,scaleY:y});return this;}
  setDepth(depth){this.depth=depth;return this;}
  setRotation(rotation){this.rotation=rotation;return this;}
  setData(key,value){this.data[key]=value;return this;}
  getData(key){return this.data[key];}
  setVisible(visible){this.visible=visible;return this;}
  setDisplaySize(displayWidth,displayHeight){Object.assign(this,{displayWidth,displayHeight});return this;}
  setTexture(key){this.texture={key};return this;}
  destroy(){this.destroyed=true;for(const child of this.list||[])child.destroy();}
  getBounds(){return {width:this.width,height:this.height,left:this.x-this.width/2,right:this.x+this.width/2,top:this.y-this.height/2,bottom:this.y+this.height/2};}
}
class Graphics extends Display {
  constructor(){super();this.calls=[];}
  fillStyle(){return this;}lineStyle(){return this;}
  fillRoundedRect(...args){this.calls.push(['rect',...args]);return this;}
  fillRect(...args){this.calls.push(['rect',...args]);return this;}
  fillEllipse(...args){this.calls.push(['ellipse',...args]);return this;}
  fillCircle(){return this;}lineBetween(){return this;}
  getBounds(){
    const rects=this.calls.map(([kind,x,y,width,height])=>kind==='ellipse'?{left:x-width/2,top:y-height/2,right:x+width/2,bottom:y+height/2}:{left:x,top:y,right:x+width,bottom:y+height});
    const left=Math.min(...rects.map(r=>r.left)),top=Math.min(...rects.map(r=>r.top)),right=Math.max(...rects.map(r=>r.right)),bottom=Math.max(...rects.map(r=>r.bottom));
    return {left,top,right,bottom,width:right-left,height:bottom-top};
  }
}
class Text extends Display {
  constructor(x,y,text,style){super(x,y);this.text=text;const size=parseFloat(style.fontSize);this.width=Math.max(...text.split('\n').map(line=>line.length))*size*.56;this.height=text.split('\n').length*(size+2);}
}
class Container extends Display {
  constructor(x,y,list){super(x,y);this.list=list;this.width=Math.max(0,...list.map(child=>child.width));this.height=Math.max(0,...list.map(child=>child.height));}
  getBounds(){
    if(!this.list.length)return super.getBounds();
    const rows=this.list.map(child=>child.getBounds()),left=this.x+Math.min(...rows.map(r=>r.left)),right=this.x+Math.max(...rows.map(r=>r.right)),top=this.y+Math.min(...rows.map(r=>r.top)),bottom=this.y+Math.max(...rows.map(r=>r.bottom));
    return {left,right,top,bottom,width:right-left,height:bottom-top};
  }
}
const original=globalThis.__signTestPhaser;
globalThis.__signTestPhaser={Scene:class {},GameObjects:{Image:Display,Container,Text},Math:{Clamp:(v,min,max)=>Math.max(min,Math.min(max,v))}};
const source=readFileSync('client/isometric/phaser-world.ts','utf8');
const bundle=await build({stdin:{contents:source+'\nexport {DioramaScene};',loader:'ts',resolveDir:resolve('client/isometric')},bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent',plugins:[{
  name:'sign-display-boundary',setup(b){
    b.onResolve({filter:/^(phaser|\/js\/)/},args=>({path:args.path,namespace:'sign-test'}));
    b.onLoad({filter:/.*/,namespace:'sign-test'},args=>({contents:args.path==='phaser'?'export default globalThis.__signTestPhaser;':args.path.includes('/look.js')?'export const figure=()=>({}),defaultLook=()=>({});':args.path.includes('/character-art.js')?'export const getCharacterStamp=()=>({}),preloadIllustratedCharacters=()=>{};':'export const kindOf=()=>"home",wordsFor=()=>({});',loader:'js'}));
  }
}]});
const {DioramaScene}=await import('data:text/javascript;base64,'+Buffer.from(bundle.outputFiles[0].text).toString('base64'));
if(original===undefined)delete globalThis.__signTestPhaser;else globalThis.__signTestPhaser=original;
const compiled=await build({entryPoints:['client/isometric/model.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const model=await import('data:text/javascript;base64,'+Buffer.from(compiled.outputFiles[0].text).toString('base64'));
const assetsBundle=await build({entryPoints:['client/isometric/asset-manifest.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const {ISOMETRIC_ASSETS}=await import('data:text/javascript;base64,'+Buffer.from(assetsBundle.outputFiles[0].text).toString('base64'));
const fullBuildings=model.townBuildings(JSON.parse(readFileSync('game/town_layout.json','utf8')).careerOrder.map(id=>({id})));
const buildingDimensions=new Map(await Promise.all([...new Set(fullBuildings.map(b=>model.townBuildingArt(b.meta,b.variant)))].map(async kind=>{
  const path='public'+ISOMETRIC_ASSETS[kind];
  assert.ok(existsSync(path),`${kind} must ship its own exterior before testing full-town sign occlusion`);
  const meta=await sharp(path).metadata();return [kind,meta];
})));
const loadedBuildingOccluders=fullBuildings.map(b=>{
  const source=buildingDimensions.get(model.townBuildingArt(b.meta,b.variant)),width=b.neighbourhood==='garden'?375:b.neighbourhood==='office'?340:355,height=width*source.height/source.width,foot=model.project(b.at);
  return {id:b.id,depth:foot.y,bounds:{x0:foot.x-width/2,x1:foot.x+width/2,y0:foot.y-height,y1:foot.y}};
});
const trailsBundle=await build({entryPoints:['client/isometric/trail-geometry.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const {sampleTrailCurve,streetProfile}=await import('data:text/javascript;base64,'+Buffer.from(trailsBundle.outputFiles[0].text).toString('base64'));
function scene(){
  const s=new DioramaScene({mode:'town',residentShops:[],hotspots:[],game:{catalogue:[]}});
  s.add={text:(...args)=>new Text(...args),graphics:()=>new Graphics(),container:(...args)=>new Container(...args)};
  s.reindexStatics=()=>{};s.registerOccluder=(image,tag)=>s.lastOccluder={image,tag};
  s.navigation={bounds:{x0:-100,y0:-100,x1:100,y1:100},roads:[{x0:-100,y0:-100,x1:100,y1:100}],obstacles:[]};
  return s;
}

test('authored civic scenery exists independently of gated interactions and binds once',()=>{
  const s=scene();
  s.ensureAssets=()=>{};s.textures={exists:()=>true,get:()=>({getSourceImage:()=>({width:768,height:640})})};
  s.add.image=(x,y,key)=>new Display(x,y).setTexture(key);
  s.amenities();
  const place=model.townAmenities().find(p=>p.id==='date'),hotspot={id:'place:date'},before=s.staticObjects.length;
  assert.ok(before>=6,'closed online features still have real static scenery');
  const image=s.addAmenityVisual(place,hotspot);
  assert.ok(image,'illustrated place can bind to its existing guide hotspot');
  s.addAmenityVisual(place,hotspot);
  assert.equal(s.staticObjects.length,before,'binding never allocates a duplicate building');
  assert.equal(s.hits.filter(h=>h.hotspot===hotspot).length,1,'no duplicate hit bindings');
  s.removeAmenityVisual(image,hotspot);
  assert.equal(image.destroyed,undefined,'gate changes never leave an invisible solid footprint');
  assert.equal(s.hits.filter(h=>h.hotspot===hotspot).length,0);
});

test('facade label accounts for the amenity ground anchor instead of placing text below the image',()=>{
  const s=scene(),image=new Display(100,300).setTexture('art-home').setOrigin(.5,.82).setDisplaySize(270,330).setDepth(300);
  const sign=s.facadeSign('Nhà của bạn',image,'home',0x668574);
  assert.equal(sign.y,300+(.50-.82)*330);
});

test('freestanding board and both supports form one object rooted on the ground',()=>{
  const s=scene(),at={x:4,y:5},foot=model.project(at),sign=s.placard('Ao câu cá',at,15,190,0x668574);
  assert.deepEqual({x:sign.x,y:sign.y},foot,'zoom/culling acts on the whole stand from its planted feet');
  const plate=sign.list.find(child=>child instanceof Container),supports=sign.list.find(child=>child instanceof Graphics);
  assert.ok(plate&&supports,'the visible board is physically attached to supports');
  assert.ok(plate.y<=-96,'nameboards stand above character waist height');
  const posts=supports.calls.filter(([kind,,y,width,height])=>kind==='rect'&&width>=5&&width<=10&&y+height===0);
  assert.equal(posts.length,2,'two supports meet the ground and carry the board');
  assert.equal(s.staticObjects.length,1,'supports cannot be culled or destroyed independently from the board');
  assert.equal(s.placards[0].mounted,true,'the physical stand does not enlarge its board independently when zooming out');
});

test('facade sign anchors follow the actual loaded building and preserve occlusion binding',()=>{
  const s=scene(),image=new Display(150,520).setTexture('art-home').setOrigin(.5,1).setDisplaySize(300,400).setDepth(520);
  const tag=s.facadeSign('Trung tâm kế toán',image,'office',0x668574);
  assert.equal(tag.x,150+(.34-.5)*300,'lazy office art falls back to the painted home facade anchor');
  assert.equal(tag.y,520-(1-.50)*400);
  assert.equal(tag.depth,520.4);assert.equal(tag.getData('buildingSign'),true);
  assert.deepEqual(s.lastOccluder,{image,tag},'building and sign still fade together');
});

test('empty resident lots do not repeat ground-level placeholder nameboards',()=>{
  const s=scene();let signs=0;
  s.artObject=()=>new Display().setTexture('art-market');s.facadeSign=()=>{signs++;return new Container(0,0,[]);};
  s.refreshResidentShops();assert.equal(signs,0,'unoccupied lots have no fake business name');
  s.owner.residentShops=[{id:'real-shop',name:'Tiệm của Mây'}];s.refreshResidentShops();
  assert.equal(signs,1,'an actual public shop keeps its mounted name');
});

test('a resident building awaiting its image keeps a real facade for its mounted sign',()=>{
  const s=scene();s.ensureAssets=()=>{};s.textures={exists:key=>key==='art-home'};
  s.textureObject=key=>key;
  for(const kind of ['office','market','garage'])assert.equal(s.artTexture(kind),'art-home',`${kind} has a real wall until its image loads`);
  assert.equal(s.artTexture('lamp'),'illustrated-detail-lamp-0','small props keep their existing illustrated fallback');
});

test('wayfinding stands leave their original walking destinations clear',()=>{
  const s=scene();assert.equal(typeof s.wayfindingSign,'function');
  const catalogue=JSON.parse(readFileSync('game/town_layout.json','utf8')).careerOrder.map(id=>({id}));
  s.buildings=model.townBuildings(catalogue);s.navigation=model.townNavigation(s.buildings);
  const roads=model.townTrails().map((trail,index)=>streetProfile(sampleTrailCurve(trail.points,trail.sampled),trail.width,index));
  const destinations=[...model.townLandmarks().map(p=>({...p,at:p.approach})),...model.townAmenities()];
  for(const p of destinations){
    const sign=s.wayfindingSign(p.label,p.at,15,190,0x668574),mount=model.unproject(sign);
    assert.ok(Math.hypot(mount.x-p.at.x,mount.y-p.at.y)>=1.2,`${p.id} leaves its arrival point clear`);
    assert.ok(Math.hypot(mount.x-p.at.x,mount.y-p.at.y)<=6,`${p.id} stays close to its destination`);
    assert.ok(model.isWalkable(s.navigation,mount),`${p.id} stand avoids water, buildings and trees`);
    const supports=sign.list.find(child=>child instanceof Graphics).calls.filter(([kind,,y,width,height])=>kind==='rect'&&width>=5&&width<=10&&y+height===0);
    for(const [,x,,width] of supports){
      const foot=model.unproject({x:sign.x+x+width/2,y:sign.y});
      for(const path of roads)for(let i=1;i<path.length;i++){
        const a=path[i-1],b=path[i],dx=b.x-a.x,dy=b.y-a.y,length=dx*dx+dy*dy,t=Math.max(0,Math.min(1,((foot.x-a.x)*dx+(foot.y-a.y)*dy)/(length||1)));
        assert.ok(Math.hypot(foot.x-a.x-t*dx,foot.y-a.y-t*dy)>Math.max(a.radius,b.radius)+.13,`${p.id} plants both posts outside the rendered main path`);
      }
    }
  }
});

function townInteractions(){
  const s=scene(),catalogue=JSON.parse(readFileSync('game/town_layout.json','utf8')).careerOrder.map(id=>({id}));
  s.buildings=model.townBuildings(catalogue);s.navigation=model.townNavigation(s.buildings);
  s.occluders=loadedBuildingOccluders;
  const hotspots=[...s.buildings.map(b=>({id:'career:'+b.id,approach:b.door})),...model.townDistricts().map(d=>({id:'district:'+d.id,approach:d.at}))];
  const places=new Map(PLACES.map(p=>[p.id,p]));for(const p of model.townAmenities())places.set(p.id,{...places.get(p.id),...p});
  const destinations=[...model.townLandmarks().map(p=>({...p,at:p.approach})),...[...places.values()].map(p=>({...p,id:'place:'+p.id}))];
  for(const p of destinations){
    const tag=s.wayfindingSign(p.label,p.at),mount=model.unproject(tag);
    hotspots.push({id:p.id,approach:p.at,interactionPoint:mount,tag});
  }
  return {s,hotspots};
}

for(const id of ['walk','marriage','cinema','temple'])test(`E beside the ${id} stand selects its destination instead of a nearby building or district`,()=>{
  const {s,hotspots}=townInteractions(),target=hotspots.find(h=>h.id==='place:'+id),approach={...target.approach};
  assert.equal(model.nearestReachableHotspot(s.navigation,target.interactionPoint,hotspots)?.id,target.id);
  assert.deepEqual(target.approach,approach,'selection retains the original walking destination');
  assert.ok(model.findRoute(s.navigation,target.interactionPoint,target.approach).length,'the selected destination remains reachable');
});

test('wayfinding signs publish their actual ground mount for interaction binding',()=>{
  const {hotspots}=townInteractions();
  for(const h of hotspots.filter(h=>h.tag)){
    const point=h.tag.getData('interactionPoint');assert.ok(point,h.id);
    assert.ok(Math.hypot(point.x-h.interactionPoint.x,point.y-h.interactionPoint.y)<1e-8,`${h.id} uses ground coordinates`);
  }
});

test('a nearby sign still requires a route to its unchanged approach and does not extend the global radius',()=>{
  const nav=model.makeNavigation({bounds:{x0:0,y0:0,x1:10,y1:10},roads:[{x0:0,y0:0,x1:4,y1:10},{x0:6,y0:0,x1:10,y1:10}],obstacles:[],step:.5});
  const from={x:3.8,y:5},unreachable={id:'unreachable',approach:{x:6.2,y:5},interactionPoint:from},reachable={id:'counter',approach:{x:2,y:5}};
  assert.equal(model.nearestReachableHotspot(nav,from,[unreachable,reachable])?.id,'counter','a visible stand cannot bypass disconnected navigation');
  assert.equal(model.nearestReachableHotspot(nav,{x:3.8,y:1},[reachable]),null,'ordinary station range remains 2.4');
});

test('pool and amenity stands remain visible in front of the actual loaded building silhouettes',()=>{
  const {hotspots}=townInteractions(),hidden=[];
  for(const h of hotspots.filter(h=>h.tag)){
    const r=h.tag.getBounds();
    for(const house of loadedBuildingOccluders){const b=house.bounds;
      if(house.depth>h.tag.depth&&r.left<b.x1&&r.right>b.x0&&r.top<b.y1&&r.bottom>b.y0)hidden.push(`${h.id} behind ${house.id}`);
    }
  }
  assert.deepEqual(hidden,[],'clear ground does not guarantee a nameboard clears a foreground facade');
});
