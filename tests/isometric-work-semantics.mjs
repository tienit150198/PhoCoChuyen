import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {build,transform} from 'esbuild';
import {KIND_OF} from '../public/js/scenes/vocabulary.js';

const compiled=await build({entryPoints:['client/isometric/work-layout.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const {workLayout}=await import('data:text/javascript;base64,'+Buffer.from(compiled.outputFiles[0].text).toString('base64'));
const layout=career=>workLayout(KIND_OF[career],career),objects=career=>[...layout(career).stations,...layout(career).fixtures];
const pharmacy=layout('pharmacy');
assert.ok(!objects('pharmacy').some(o=>o.kind==='bed'),'a dispensing pharmacy must not inherit the clinic patient bed');
assert.ok(objects('pharmacy').some(o=>o.kind==='coldcabinet'),'pharmacy stock uses upright cold storage');
assert.ok(objects('pharmacy').filter(o=>o.kind==='medicine').length>=2,'pharmacy has stock and separately organized storage cabinets');
assert.equal(pharmacy.stations.find(s=>s.id==='workbench').kind,'counter','checking and packing happen on a dispensing surface');
assert.ok(!objects('pharmacy').some(o=>o.kind==='freezer'),'medicine storage must not show ice-cream scoops');
assert.ok(!workLayout('drugstore','unknown').fixtures.some(o=>o.kind==='bed'),'future dispensing careers cannot inherit a patient-bed fallback');

// Every row reflects the existing vocabulary/tasks: this guards against a family
// fallback importing an unrelated profession's equipment into a new career.
const required={
  milk_tea:['counter','display'],cafe_bakery:['oven','display'],restaurant:['stove','sink'],grocery:['shelf','crate'],florist:['planter','sink'],
  mother_baby:['shelf','crib'],pharmacy:['medicine','coldcabinet','counter'],salon:['mirror','sink'],pet_care:['sink','bench'],repair:['tools','rack'],nail:['desk','display'],
  teacher:['chalkboard','bookcase'],accounting:['bookcase','desk'],corp_accounting:['bookcase','desk'],tax_payroll:['bookcase','board'],group_accounting:['bookcase','desk'],
  customer_care:['console','sofa'],hr_admin:['desk','bench'],secretary:['board','sofa'],it_helpdesk:['tools','rack'],farm:['planter','crate'],delivery:['crate','shelf'],
  tour_guide:['routeboard','bench'],homestay:['bed','sofa'],homemaker:['stove','coldcabinet','washer'],naucom:['stove','coldcabinet','sink'],tra_da:['counter','bench'],
  clothing:['display','mirror'],pet_shop:['shelf','display'],fruit:['crate','display'],garbage:['bin'],drain:['pipework','tools'],ice_cream:['freezer'],
  com:['stove','display'],pagoda:['altar','planter'],pho:['stove','sink'],photobooth:['photobooth','console','crate'],giupviec:['washer','sink'],babysitter:['crib','desk'],
  library:['bookcase','desk'],pilot:['console','seatrow'],flight_attendant:['seatrow','counter'],oil:['pipework','tools'],railway:['signal'],nurse:['bed','sink'],
  lighthouse:['beacon','planter'],rescue:['console','routeboard'],lifeguard:['pool','seatrow'],police:['bookcase','seatrow'],zpop:['bookcase','display'],
};
assert.deepEqual(Object.keys(required).sort(),Object.keys(KIND_OF).sort(),'all 50 careers receive a semantic review');
const exclusive={bed:['nurse','homestay'],crib:['babysitter','mother_baby'],stove:['restaurant','homemaker','naucom','com','pho'],oven:['cafe_bakery'],
  washer:['giupviec','homemaker'],freezer:['ice_cream'],coldcabinet:['pharmacy','homemaker','naucom'],pool:['lifeguard'],beacon:['lighthouse'],signal:['railway'],photobooth:['photobooth']};
const fixtures=new Map();
for(const [career,wanted] of Object.entries(required)){
  const room=layout(career),kinds=objects(career).map(o=>o.kind);
  for(const kind of wanted)assert.ok(kinds.includes(kind),`${career}: recognizable equipment ${kind}`);
  for(const [kind,allowed] of Object.entries(exclusive))if(kinds.includes(kind))assert.ok(allowed.includes(career),`${career}: ${kind} belongs to another profession`);
  const footprint=JSON.stringify(room.fixtures.map(({kind,footprint})=>({kind,footprint})).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b))));
  assert.ok(!fixtures.has(footprint),`${career}: fixture geometry duplicates ${fixtures.get(footprint)}`);fixtures.set(footprint,career);
}
assert.equal(fixtures.size,50,'each career has its own equipment arrangement without relying on labels, colors or walls');
for(const career of ['homemaker','naucom'])assert.equal(layout(career).stations.find(s=>s.id==='shelf').kind,'coldcabinet',`${career}: refrigerator vocabulary binds to a refrigerator`);
assert.equal(layout('pagoda').stations.find(s=>s.id==='shelf').kind,'planter','pagoda ornamental plants are not an office bookcase');
assert.equal(layout('photobooth').stations.find(s=>s.id==='workbench').kind,'photobooth','camera booth is not the generic merchandise/bottle display');
const renderer=readFileSync('client/isometric/phaser-world.ts','utf8').split('    const furnishing=(item:WorkFixture)')[1].split('    for(const item of layout.fixtures)')[0];
assert.match(renderer,/if\(kind==='coldcabinet'\)/,'the cold cabinet has its own visible silhouette');
assert.match(renderer,/if\(kind==='photobooth'\)/,'the photo booth has its own visible camera and curtain silhouette');
assert.match(renderer,/const signature=.*'coldcabinet'.*'photobooth'/,'both new shapes share the existing bounded static signature cache');
// Execute the real furnishing function through a minimal Phaser recorder. This
// catches missing drawing branches, wrong cached bounds and accidental reuse of
// the ice-cream tub artwork without building a browser bundle.
const rendererJs=await transform('function createFurnishing(){const furnishing=(item:WorkFixture)'+renderer+';return furnishing;}',{loader:'ts',format:'cjs'});
const factory=new Function('Phaser','px','workFurnitureElevation','architecture','shade','ground','document',rendererJs.code+';return createFurnishing.call(this);');
const project=(p,z=0)=>({x:(p.x-p.y)*64,y:(p.x+p.y)*32-z});
class Rectangle {constructor(x,y,width,height){Object.assign(this,{x,y,width,height});}}
class Camera {setScene(){return this;}setOrigin(){return this;}setScroll(){return this;}setZoom(){return this;}preRender(){}destroy(){}}
const Phaser={Geom:{Rectangle},Cameras:{Scene2D:{Camera}},Textures:{FilterMode:{LINEAR:1}}};
const document={createElement:()=>({width:0,height:0,getContext:()=>({})})};
for(const career of ['pharmacy','homemaker','naucom','photobooth']){
  const kind=career==='photobooth'?'photobooth':'coldcabinet',item=objects(career).find(o=>o.kind===kind),draws=[],textures=new Set();
  const graphics=()=>{const target={depth:0};let proxy;proxy=new Proxy(target,{get:(target,name)=>name==='depth'?target.depth:(...args)=>{if(name==='setDepth')target.depth=args[0];else draws.push({name,args});return proxy;}});return proxy;};
  const image=()=>{const result={depth:0,setOrigin(){return this;},setScale(){return this;},setDepth(d){this.depth=d;return this;}};return result;};
  const scene={staticObjects:[],add:{graphics,image},game:{renderer:{}},textures:{exists:key=>textures.has(key),create:key=>{textures.add(key);return {add(){},setFilter(){}};}}};
  const ground={fillStyle(){},fillEllipse(){}};
  const furnish=factory.call(scene,Phaser,project,()=>0,layout(career).architecture,c=>c,ground,document);
  const first=furnish(item),paintCount=draws.length,second=furnish(item);
  assert.equal(draws.length,paintCount,`${career}: subsequent room refresh reuses the signature texture`);
  assert.equal(textures.size,1,`${career}: one stable texture, no unbounded per-refresh allocation`);
  assert.deepEqual(second.bounds,first.bounds,`${career}: cached art keeps identical hit bounds`);
  assert.ok(first.bounds.width>0&&first.bounds.height>0&&paintCount<240,`${career}: finite, visible drawing and texture dimensions`);
  assert.equal(draws.filter(c=>c.name==='renderCanvas').length,1,`${career}: drawing is rasterized once`);
  const circles=draws.filter(c=>c.name==='fillCircle').length,ellipses=draws.filter(c=>c.name==='fillEllipse').length;
  if(kind==='coldcabinet'){assert.equal(circles,0,'closed cold cabinet does not contain ice-cream scoops');assert.equal(ellipses,0,'closed cold cabinet has no serving tubs');}
  else{
    assert.ok(circles>=2,'the actual booth contains a camera lens');
    const lensIndex=draws.findIndex(c=>c.name==='fillCircle'),[x,y]=draws[lensIndex].args;
    const covers=(polygon,x,y)=>{let inside=false;for(let i=0,j=polygon.length-1;i<polygon.length;j=i++){const a=polygon[i],b=polygon[j];if((a.y>y)!==(b.y>y)&&x<(b.x-a.x)*(y-a.y)/(b.y-a.y)+a.x)inside=!inside;}return inside;};
    assert.ok(!draws.slice(lensIndex+1).filter(c=>c.name==='fillPoints').some(c=>covers(c.args[0],x,y)),'the booth cutaway roof and curtains must leave the camera lens visible');
  }
}
console.log('PASS 50 career equipment semantics: no pharmacy bed, correct cold storage/photobooth/temple plants, 50 unique fixture plans');
