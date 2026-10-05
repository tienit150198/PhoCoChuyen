/** Compare the actual TS navigation and all career doors with live's mirrored geometry. */
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {build} from 'esbuild';

const compiled=await build({entryPoints:['client/isometric/model.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const model=await import('data:text/javascript;base64,'+Buffer.from(compiled.outputFiles[0].text).toString('base64'));
const server=JSON.parse(execFileSync(process.env.PYTHON||'python',['-c',
  'import json; from live.town import BOUNDS, ROADS, OBSTACLES; from game.content import CAREERS,public_content; print(json.dumps(dict(bounds=BOUNDS, roads=ROADS, obstacles=OBSTACLES, careers=CAREERS,catalogue=public_content()["catalogue"])))'],{encoding:'utf8'}));
const buildings=model.townBuildings(server.catalogue);
assert.deepEqual(buildings.map(b=>b.id).sort(),[...server.careers].sort(),'the actual public catalogue puts only playable careers on the shared island');
const nav=model.townNavigation(buildings),rect=r=>[r.x0,r.y0,r.x1,r.y1];
assert.deepEqual(rect(nav.bounds),server.bounds,'server bounds match actual townNavigation');
assert.deepEqual(nav.roads.map(rect),server.roads,'server roads match actual townNavigation');
assert.deepEqual(nav.obstacles.map(rect),server.obstacles,'server uses the same house, water and garden collision data');
for(const building of buildings){
  assert.ok(model.isWalkable(nav,building.door),`${building.id} door is reachable on the client`);
  assert.ok(server.roads.some(([x0,y0,x1,y1])=>building.door.x>=x0&&building.door.x<=x1&&building.door.y>=y0&&building.door.y<=y1),`${building.id} door is accepted on the live map`);
}
for(let x=0;x<=nav.bounds.x1;x+=.5)for(let y=0;y<=nav.bounds.y1;y+=.5){
  const serverWalk=server.roads.some(([x0,y0,x1,y1])=>x>=x0&&x<=x1&&y>=y0&&y<=y1)&&!server.obstacles.some(([x0,y0,x1,y1])=>x>=x0-.14&&x<=x1+.14&&y>=y0-.14&&y<=y1+.14);
  assert.equal(serverWalk,model.isWalkable(nav,{x,y}),`same walkability at ${x},${y}`);
}
console.log(`Town geometry agrees for ${buildings.length} careers and every sampled ground point.`);
for(const count of [7,8,12,41,42,48,49]){
  const future=model.townBuildings(Array.from({length:count},(_,i)=>({id:`future-${i}`}))),nav=model.townNavigation(future);
  const mirrored=JSON.parse(execFileSync(process.env.PYTHON||'python',['-c',`import json; from live.town import town_geometry,town_obstacles; b,r=town_geometry(${count}); print(json.dumps(dict(bounds=b,roads=r,obstacles=town_obstacles(${count}))))`],{encoding:'utf8'}));
  assert.deepEqual(rect(nav.bounds),mirrored.bounds,'future row bounds also include the reserved commons slot');
  assert.deepEqual(nav.roads.map(rect),mirrored.roads);
  assert.deepEqual(nav.obstacles.map(rect),mirrored.obstacles);
  for(const b of future)assert.ok(model.isWalkable(nav,b.door),`expansion ${count}: ${b.id} door stays reachable`);
}
