import assert from 'node:assert/strict';
import {build} from 'esbuild';
const compiled=await build({entryPoints:['client/isometric/model.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const m=await import('data:text/javascript;base64,'+Buffer.from(compiled.outputFiles[0].text).toString('base64'));
const buildings=m.townBuildings(Array.from({length:41},(_,i)=>({id:'job-'+i}))),nav=m.townNavigation(buildings);
assert.ok(m.isWalkable(nav,{x:.35,y:6.9}),'open grass at a block edge is walkable instead of confining the player to road strips');
assert.ok(m.isWalkable(nav,{x:.4,y:4.8}),'courtyard between buildings allows diagonal free movement');
const from={x:.4,y:4.8},to={x:.8,y:5.8};
assert.ok(m.lineClear(nav,from,to),'an unobstructed diagonal through a courtyard stays legal');
assert.deepEqual(m.findRoute(nav,from,to),[to],'tap movement takes the clear diagonal without grid turns');
assert.ok(new Set(buildings.map(b=>(b.footprint.x0%7).toFixed(2)+','+(b.footprint.y0%7).toFixed(2))).size>=4,'neighbouring houses have varied setbacks');
for(const landmark of m.townLandmarks())assert.equal(m.isWalkable(nav,landmark.at),false,'pond, pool and boats cannot be walked through');
for(const b of buildings){assert.ok(m.isWalkable(nav,b.door));assert.ok(m.findRoute(nav,{x:6.2,y:6.2},b.door).length);}
const steps=m.advanceRoute({x:0,y:0},[{x:.1,y:0},{x:.1,y:1}],.3);
assert.ok(Math.abs(steps.point.y-.2)<1e-9,'tap route consumes remaining stride across waypoints instead of pausing at each corner');
const garden=m.townGarden(buildings);
assert.ok(new Set(garden.map(p=>p.kind)).size>=6,'scenery uses several distinct vegetation silhouettes');
assert.deepEqual(garden,m.townGarden(buildings),'planting is stable between reloads and shared clients');
for(const p of garden){for(const b of buildings)assert.ok(Math.hypot(b.door.x-p.at.x,b.door.y-p.at.y)>1,'vegetation leaves all entrances open');}
const open=m.makeNavigation({bounds:{x0:-20,y0:-20,x1:20,y1:20},roads:[{x0:-20,y0:-20,x1:20,y1:20}],obstacles:[],step:.5});
for(const input of [{x:1,y:1},{x:-1,y:1},{x:1,y:-1},{x:-1,y:-1}]){
 const p=m.project(m.moveOnGround(open,{x:0,y:0},input,.05));
 assert.ok(Math.sign(p.x)===Math.sign(input.x)&&Math.sign(p.y)===Math.sign(input.y),'all four screen diagonals remain diagonal');
 assert.ok(Math.abs(Math.hypot(p.x,p.y)-8.5)<1e-7,'diagonals have the same speed as cardinal directions');
}
for(const goal of [{x:5,y:0},{x:0,y:5},{x:5,y:5},{x:-5,y:5}]){
 const next=m.advanceRoute({x:0,y:0},[goal],8.5,'screen');
 const screen=m.project(next.point);
 assert.ok(Math.abs(Math.hypot(screen.x,screen.y)-8.5)<1e-7,'tap walking has the same visible speed as the joystick in every direction');
}
console.log('Town polish: open diagonals, natural setbacks, garden collision and continuous routes passed');
