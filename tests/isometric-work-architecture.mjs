import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {build} from 'esbuild';
import {KIND_OF} from '../public/js/scenes/vocabulary.js';

const load=async entry=>{const out=await build({entryPoints:[entry],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});return import('data:text/javascript;base64,'+Buffer.from(out.outputFiles[0].text).toString('base64'));};
const room=await load('client/isometric/work-layout.ts'),model=await load('client/isometric/model.ts');
const contains=(a,b)=>a.x0<=b.x0&&a.y0<=b.y0&&a.x1>=b.x1&&a.y1>=b.y1;
const careers=Object.entries(KIND_OF),shapes=new Map(),envelopes=new Map(),finishes=new Set(),apertures=new Set(),fittings=new Set();
assert.equal(careers.length,50);
const appearance=model.roomAppearance({upgrades:['plant','lamp','seat','rug','poster','shelf','workbench','board'],ops:{property:{tier:'garden'}}});
for(const [career,family] of careers){
  const layout=room.workLayout(family,career),a=layout.architecture;
  assert.ok(a,`${career}: physical architecture must accompany the occupational plan`);
  assert.equal(a.career,career,`${career}: no shared fallback architecture`);
  assert.ok(a.walls.length>=4,`${career}: cutaway has architectural bays, not the same two walls`);
  assert.ok(a.elements.length>=2,`${career}: occupational fit-out has multiple physical details`);
  const geometry=JSON.stringify({walls:a.walls.map(({from,to,height,crest,finish,opening})=>({from,to,height,crest,finish,opening})),elements:a.elements.map(({kind,footprint,height})=>({kind,footprint,height}))});
  assert.ok(!shapes.has(geometry),`${career}: architecture duplicates ${shapes.get(geometry)} without labels/colors`);shapes.set(geometry,career);
  const footprintOnly=JSON.stringify(a.walls.map(({from,to})=>({from,to})));
  assert.ok(!envelopes.has(footprintOnly),`${career}: shell footprint must differ physically from ${envelopes.get(footprintOnly)}`);envelopes.set(footprintOnly,career);
  assert.notEqual(footprintOnly,JSON.stringify([{from:{x:0,y:0},to:{x:10,y:0}},{from:{x:0,y:0},to:{x:0,y:9}}]),`${career}: shell is spatially authored`);
  for(const wall of a.walls){
    finishes.add(wall.finish);if(wall.opening)apertures.add(wall.opening);
    assert.ok(wall.height>=45&&wall.height<=240,`${career}: cutaway walls remain at a readable scale`);
    for(let t=0;t<=1;t+=.1){const p={x:wall.from.x+(wall.to.x-wall.from.x)*t,y:wall.from.y+(wall.to.y-wall.from.y)*t};assert.ok(!model.inside(p,layout.bounds),`${career}: perimeter cannot cross the walkable floor`);}
  }
  assert.deepEqual(a.window,model.WORK_WINDOW,`${career}: saved sill and window-break anchor remain fixed`);
  const occupied=[...layout.fixtures,...layout.stations.filter(s=>s.footprint)].map(s=>s.footprint);
  for(const element of a.elements){
    fittings.add(element.kind);
    assert.ok(occupied.some(r=>contains(r,element.footprint)),`${career}/${element.kind}: fit-out must stay on an already solid furniture footprint`);
  }
  const nav=room.workNavigation(layout,appearance);
  assert.ok(model.isWalkable(nav,layout.spawn),`${career}: saved entry remains clear`);
  const people=room.workActorPositions(layout,nav,9);assert.equal(people.length,9,`${career}: actors still fit`);
  nav.obstacles.push(...people.map(room.workActorFootprint));
  for(const station of layout.stations){const route=model.findRoute(nav,layout.spawn,station.approach);assert.ok(route.length,`${career}/${station.id}: route remains reachable`);let last=layout.spawn;for(const p of route){assert.ok(model.lineClear(nav,last,p),`${career}: route crosses no architectural solid`);last=p;}}
}
assert.equal(shapes.size,50,'every occupation needs its own physical architecture');
assert.ok(finishes.size>=8,'workplaces have different construction, not just recoloring');
assert.ok(apertures.size>=6,'occupations use physically different window/opening structures');
assert.ok(fittings.size>=12,'recognition comes from architectural equipment, not labels');
const architecture=await load('client/isometric/work-architecture.ts');
assert.deepEqual([...architecture.WORK_ARCHITECTURE_CAREERS].sort(),Object.keys(KIND_OF).sort(),'the registry explicitly authors all 50 careers; no silent fallback');
assert.equal(typeof architecture.workFurnitureElevation,'function','a raised platform must lift furniture, not paint a stripe underneath it');
for(const career of ['teacher','group_accounting','pagoda','lighthouse','zpop']){
  const layout=room.workLayout(KIND_OF[career],career),platforms=layout.architecture.elements.filter(e=>e.kind==='plinth');
  assert.ok(platforms.length,`${career}: occupational dais exists`);
  for(const platform of platforms)assert.equal(architecture.workFurnitureElevation(layout.architecture,platform.footprint),platform.height,`${career}: furniture stands on the actual raised surface`);
  assert.equal(architecture.workFurnitureElevation(layout.architecture,layout.stations.find(s=>s.id==='door').footprint),0,`${career}: the entry never floats on a stage`);
}
for(const [career,expected] of [
  ['cafe_bakery',['arched-niche','extractor']],['florist',['trellis']],['pharmacy',['sorting-cubbies','glass-screen']],
  ['accounting',['pigeonholes','arched-niche']],['corp_accounting',['glass-screen']],['tax_payroll',['timber-screen','acoustic-baffle']],
  ['group_accounting',['plinth']],['customer_care',['acoustic-baffle']],['hr_admin',['glass-screen','timber-screen']],
  ['secretary',['service-hatch','canopy']],['it_helpdesk',['pipe-chase','pegwall']],
  ['nurse',['privacy-curtain','wash-splash']],['pilot',['cabin-ribs']],['flight_attendant',['cabin-ribs','sorting-cubbies']],
  ['pagoda',['plinth','canopy']],['photobooth',['privacy-curtain','lightbox']],['oil',['pipe-chase']],
]){
  const kinds=room.workLayout(KIND_OF[career],career).architecture.elements.map(e=>e.kind);
  for(const kind of expected)assert.ok(kinds.includes(kind),`${career}: occupational construction preserves ${kind}`);
}
for(const [career,family] of careers){
  const a=room.workLayout(family,career).architecture,commands=[];
  const ink={polygon:(points,color,alpha=1)=>commands.push({type:'polygon',points,color,alpha}),line:(from,to,color,width,alpha=1)=>commands.push({type:'line',points:[from,to],color,width,alpha})};
  for(const pass of ['base','walls','fittings'])architecture.drawWorkArchitecture(a,ink,pass,0xf0dfc6);
  assert.ok(commands.length>80&&commands.length<2600,`${career}: finite authored static drawing (${commands.length})`);
  assert.ok(commands.every(c=>c.points.every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y))),`${career}: no invalid graphics coordinates`);
  const before=JSON.stringify(a);architecture.drawWorkArchitecture(a,ink,'walls',0xf0dfc6);assert.equal(JSON.stringify(a),before,'rendering never mutates room/save geometry');
}
const source=readFileSync('client/isometric/phaser-world.ts','utf8').split('  private work(){')[1].split('  private operationsStation(')[0];
assert.match(source,/drawWorkArchitecture\(/,'live work renderer consumes tested architectural commands');
assert.doesNotMatch(source,/const wallHeight=layout\.outdoor/,'generic two-wall shell no longer replaces occupation architecture');
assert.match(source,/this\.window\(WORK_WINDOW,WORK_WINDOW\.z\)/,'window break keeps its actual rendered anchor');
console.log('PASS 50 career architectures: physical identity, bounded static rendering, saved anchors and all actor/station routes');
