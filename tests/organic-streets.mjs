import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {execFileSync} from 'node:child_process';
const bundle=await build({entryPoints:['client/isometric/trail-geometry.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const geometry=await import('data:text/javascript;base64,'+Buffer.from(bundle.outputFiles[0].text).toString('base64'));
assert.equal(typeof geometry.connectStreetDoors,'function','streets connect to actual doors instead of disconnected rectangular aprons');
const modelBundle=await build({entryPoints:['client/isometric/model.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const m=await import('data:text/javascript;base64,'+Buffer.from(modelBundle.outputFiles[0].text).toString('base64'));
const catalogue=JSON.parse(execFileSync('python',['-c','import json; from game.content import public_content; print(json.dumps(public_content()["catalogue"]))'],{encoding:'utf8'}));
const buildings=m.townBuildings(catalogue),nav=m.townNavigation(buildings),trails=m.townTrails();
const doors=[...buildings.map(b=>({id:b.id,district:b.neighbourhood,at:b.door})),...m.townShopLots().map((b,index)=>({id:'resident-lot-'+index,district:'resident',at:b.door}))];
const input=JSON.stringify({trails,doors});
const branches=geometry.connectStreetDoors(trails,doors,nav);
assert.equal(branches.length,doors.length,'all 50 workplaces and 8 resident storefronts meet the street network');
const mainSamples=trails.map(t=>geometry.sampleTrailCurve(t.points,t.sampled));
function distanceToSegment(p,a,b){const dx=b.x-a.x,dy=b.y-a.y,t=Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/(dx*dx+dy*dy||1)));return Math.hypot(p.x-a.x-t*dx,p.y-a.y-t*dy);}
for(const [index,branch] of branches.entries()){
  assert.deepEqual(branch.points[0],doors[index].at,`${branch.id} starts at its actual door`);
  const end=branch.points.at(-1);
  assert.ok(mainSamples.some(samples=>samples.some((p,i)=>i&&distanceToSegment(end,samples[i-1],p)<.001)),`${branch.id} reaches a main road without a grass gap`);
  assert.ok(branch.points.length<250,'door branches have bounded cached geometry');
  for(let i=0;i<branch.points.length;i++){
    assert.ok(m.isWalkable(nav,branch.points[i]),`${branch.id}: the entrance path does not cross a house, tree or water`);
    if(i)assert.ok(m.lineClear(nav,branch.points[i-1],branch.points[i]),`${branch.id}: rounded corners keep collision clearance`);
  }
}
assert.equal(JSON.stringify({trails,doors}),input,'the visual pass does not move the authored map or doors');
assert.deepEqual(geometry.connectStreetDoors(trails,doors,nav),branches,'static geometry is deterministic across reloads');
assert.deepEqual(geometry.connectStreetDoors([],doors,nav),[],'missing main roads do not invent disconnected paths');
const enclosed=m.makeNavigation({bounds:{x0:0,y0:0,x1:10,y1:10},roads:[{x0:0,y0:0,x1:10,y1:10}],obstacles:[{x0:4,y0:0,x1:6,y1:10}],step:.5});
assert.deepEqual(geometry.connectStreetDoors([{district:'test',width:1,points:[{x:8,y:1},{x:8,y:9}]}],[{id:'blocked',district:'test',at:{x:2,y:5}}],enclosed),[],'unreachable doors never get a painted path through a wall');
const profile=geometry.streetProfile(Array.from({length:101},(_,i)=>({x:i*.2,y:0})),2.2,3);
const radii=profile.map(p=>p.radius);
assert.ok(Math.max(...radii)-Math.min(...radii)>.15,'street width changes gently along the path');
assert.ok(radii.every(r=>r>.75&&r<1.5),'organic edges keep a useful road width');
assert.ok(radii.every((r,i)=>!i||Math.abs(r-radii[i-1])<.08),'road shoulders do not have abrupt steps');
console.log(`Organic streets: ${branches.length} safe, connected door paths; stable width variation.`);
