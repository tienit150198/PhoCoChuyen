import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {performance} from 'node:perf_hooks';
const compiled=await build({entryPoints:['client/isometric/model.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const m=await import('data:text/javascript;base64,'+Buffer.from(compiled.outputFiles[0].text).toString('base64'));
const catalogue=JSON.parse(execFileSync('python',['-c','import json; from game.content import public_content; print(json.dumps(public_content()["catalogue"]))'],{encoding:'utf8'}));
const buildings=m.townBuildings(catalogue),nav=m.townNavigation(buildings),start={x:6.2,y:6.2};
// Exercise the renderer's actual Catmull-Rom samples, including interpolation
// overshoot between safe control points and collision between sampled vertices.
const trailBuild=await build({entryPoints:['client/isometric/trail-geometry.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const {sampleTrailCurve}=await import('data:text/javascript;base64,'+Buffer.from(trailBuild.outputFiles[0].text).toString('base64'));
const groundSource=readFileSync('client/isometric/town-scenery.ts','utf8');
assert.match(groundSource,/import\s*\{sampleTrailCurve\}\s*from\s*'\.\/trail-geometry'/,'rendering uses the same curve sampler as collision validation');
assert.match(groundSource,/sampleTrailCurve\(trail\.points,trail\.sampled\)/,'the rendered centerline is the one checked below');
assert.deepEqual(sampleTrailCurve([]),[],'an empty authored trail adds no geometry');
assert.deepEqual(sampleTrailCurve([{x:1,y:2}]),[{x:1,y:2}],'a single trail marker remains finite');
for(const [index,trail] of m.townTrails().entries()){
  const before=JSON.stringify(trail.points),samples=sampleTrailCurve(trail.points,trail.sampled);
  assert.equal(samples.length,trail.sampled?trail.points.length:12*(trail.points.length-1)+1,'trail detail has bounded static cost');
  assert.equal(JSON.stringify(trail.points),before,'sampling never changes the authored controls');
  assert.deepEqual(samples[0],trail.points[0],'the trail starts at its authored connection');
  assert.deepEqual(samples.at(-1),trail.points.at(-1),'the trail ends at its authored connection');
  for(const [i,p] of samples.entries()){
    assert.ok(m.isWalkable(nav,p),`trail ${index} (${trail.district}) sample ${i} crosses a building, water or unwalkable gap`);
    if(i)assert.ok(m.lineClear(nav,samples[i-1],p),`trail ${index} (${trail.district}) segment ${i} crosses an obstacle between samples`);
  }
}
assert.ok(nav.bounds.x1-nav.bounds.x0>90,'the island opens its western and eastern districts');
assert.ok(m.townDistricts().length>=8,'distinct neighbourhoods can be discovered');
assert.equal(new Set(buildings.map(b=>b.id)).size,catalogue.filter(c=>c.playable!==false).length,'every career has exactly one door');
const goals=[...buildings.map(b=>({id:b.id,at:b.door})),...m.townDistricts(),...m.townAmenities(),...m.townLandmarks().map(l=>({id:l.id,at:l.approach}))];
let slowest=0;
for(const goal of goals){
  assert.ok(m.insideIsland(goal.at),`${goal.id} stays on the referenced island`);
  assert.ok(m.isWalkable(nav,goal.at),`${goal.id} is on open ground`);
  const t=performance.now(),path=m.findRoute(nav,start,goal.at);slowest=Math.max(slowest,performance.now()-t);
  assert.ok(path.length,`${goal.id} has a continuous path from the first street`);
  let last=start;for(const step of path){assert.ok(m.lineClear(nav,last,step),`${goal.id} never cuts through a tree, building or water`);last=step;}
}
assert.ok(slowest<1200,`long routes must remain bounded on the expanded map (${Math.round(slowest)} ms)`);
assert.ok(new Set(m.townDistricts().map(d=>d.material)).size>=5,'districts have visibly different ground materials');
assert.ok(m.townGarden(buildings).length<450,'static vegetation stays bounded');
for(const b of buildings)for(const prop of m.townGarden(buildings))assert.ok(Math.hypot(b.door.x-prop.at.x,b.door.y-prop.at.y)>1,'planting leaves entrances clear');
const mixed=m.townBuildings([{id:'grocery'},{id:'new-bakery'}]);
assert.equal(new Set(mixed.map(b=>b.slot)).size,2,'new catalogue entries do not occupy an existing career lot');
const actors=m.makeNavigation({bounds:{x0:0,y0:0,x1:10,y1:10},roads:[{x0:0,y0:0,x1:10,y1:10}],obstacles:[],step:.5});
assert.ok(m.isWalkable(actors,{x:4,y:4}));
actors.obstacles.push({x0:3.5,y0:3.5,x1:4.5,y1:4.5});
assert.ok(!m.isWalkable(actors,{x:4,y:4}),'an actor added after route lookup still blocks movement');
console.log(`Expanded island: ${buildings.length} doors, ${m.townDistricts().length} districts, ${goals.length} reachable destinations; slowest route ${Math.round(slowest)} ms.`);
