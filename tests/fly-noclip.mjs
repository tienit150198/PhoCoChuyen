// 🪽 Owner 24/10 "bay bị mắc nhà, đi khó chịu quá, sửa lại đi bay cứ vướng vướng": in the air nothing on the ground is in
// the way (houses, trees, fences, water, props) on the 2.5D island town, the classic town map and the strolls; only the
// map's bounds hold. Walking still collides. Hạ cánh over something solid comes down on the nearest walkable point.
// The flyer is drawn above the roofs. tests/test_fly_noclip.py: the live service's side.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {build} from 'esbuild';

const load=async file=>{const b=await build({entryPoints:[file],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});return import('data:text/javascript;base64,'+Buffer.from(b.outputFiles[0].text).toString('base64'));};
const m=await load('client/isometric/model.ts');
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');

// A street with a row of houses across it: open ground 0..12 × 0..10, a wall of footprints at x 5..7 (no gap).
const row=m.makeNavigation({bounds:{x0:0,y0:0,x1:12,y1:10},roads:[{x0:0,y0:0,x1:12,y1:10}],obstacles:[{x0:5,y0:0,x1:7,y1:4},{x0:5,y0:4,x1:7,y1:7},{x0:5,y0:7,x1:7,y1:10}],step:.25});
const east={x:1,y:0};   // screen right: +x (and -y) on the ground (project: (x-y)*64)
const run=(fn,from,steps)=>{let p={...from};for(let i=0;i<steps;i++)p=fn(row,p,east,.05);return p;};

test('walking still collides with the houses',()=>{
  const p=run(m.moveOnGround,{x:3,y:5},400);
  assert.ok(p.x<5-row.clearance+1e-6,`stopped before the wall (${p.x.toFixed(2)})`);
  assert.ok(m.isWalkable(row,p));
  assert.deepEqual(m.findRoute(row,{x:3,y:5},{x:9,y:5}),[],'no way round a closed row on foot');
});

test('flying ignores every obstacle in a straight line, only the bounds hold',()=>{
  const from={x:3,y:5},p=run(m.moveInAir,from,400);
  assert.equal(p.x,row.bounds.x1,'over the houses to the edge of the map');
  assert.ok(p.y>=row.bounds.y0&&p.y<=row.bounds.y1);
  // one step in the air goes exactly where the stick points, at the walking pace (the speed comes from the caller)
  const a=m.moveInAir(row,from,east,.05),b=m.moveOnGround(m.makeNavigation({bounds:row.bounds,roads:row.roads,obstacles:[],step:.25}),from,east,.05);
  assert.ok(Math.abs(a.x-b.x)<1e-9&&Math.abs(a.y-b.y)<1e-9,'the same stride as on open ground');
  // over a house mid-way: the next step is not refused
  const over={x:6,y:5};assert.equal(m.isWalkable(row,over),false);
  assert.ok(m.moveInAir(row,over,east,.05).x>over.x,'a flyer over a roof keeps going');
  // a tap / a door: straight there, never around
  assert.deepEqual(m.airRoute(row,from,{x:9,y:5}),[{x:9,y:5}]);
  assert.deepEqual(m.airRoute(row,from,{x:6,y:2}),[{x:6,y:2}],'onto a roof');
  assert.deepEqual(m.airRoute(row,from,{x:40,y:-9}),[{x:12,y:0}],'kept on the map');
  assert.deepEqual(m.airRoute(row,from,from),[],'already there');
  assert.deepEqual(m.clampToBounds(row,{x:-3,y:20}),{x:0,y:10});
});

test('landing over a house comes down on the nearest walkable point',()=>{
  for(const at of [{x:5.6,y:5},{x:6.4,y:2},{x:6.1,y:9.5}]){
    const down=m.landingSpot(row,at);
    assert.ok(m.isWalkable(row,down),`${JSON.stringify(at)} → ${JSON.stringify(down)} is open ground`);
    const side=at.x<6?5-row.clearance:7+row.clearance;
    assert.ok(Math.abs(down.x-side)<.02&&Math.abs(down.y-at.y)<1e-9,`the nearer side of the row: ${JSON.stringify(down)}`);
  }
  assert.deepEqual(m.landingSpot(row,{x:2,y:2}),{x:2,y:2},'on open ground: where they are');
});

test('a door in reach from the air (E): no ground route needed',()=>{
  const spots=[{id:'shop',approach:{x:7.6,y:5}}];
  assert.equal(m.nearestReachableHotspot(row,{x:6,y:5},spots),null,'over the roof on foot rules: none');
  assert.equal(m.nearestReachableHotspot(row,{x:6,y:5},spots,2.4,true)?.id,'shop');
});

test('others: a flyer stays where they are (over a roof), a walker is put on the ground',()=>{
  const wg={k:'rong',r:3},peers=[{pid:'a',x:6,y:5,fl:3,look:{wg}},{pid:'b',x:6,y:5,look:{wg}},{pid:'c',x:6,y:5,fl:3,look:{}}];
  const [a,b,c]=m.publicTownPlayers(peers,row);
  assert.deepEqual([a.x,a.y,a.fl],[6,5,3]);
  assert.ok(m.isWalkable(row,b)&&b.fl===undefined,'no fl: on the ground');
  assert.ok(m.isWalkable(row,c)&&c.fl===undefined,'no wings: not flying');
  assert.deepEqual(m.publicTownPlayers([{pid:'d',x:99,y:-50,fl:1,look:{wg}}],row).map(p=>[p.x,p.y]),[[12,0]],'inside the bounds');
});

test('the island town: every building, tree and prop lands on open ground, as the live service does',()=>{
  const cat=JSON.parse(execFileSync('python',['-c','import json; from game.content import public_content; print(json.dumps(public_content()["catalogue"]))'],{encoding:'utf8'}));
  const nav=m.townNavigation(m.townBuildings(cat));
  const centres=nav.obstacles.map(o=>({x:(o.x0+o.x1)/2,y:(o.y0+o.y1)/2})).filter(p=>!m.isWalkable(nav,p));
  assert.ok(centres.length>150,'buildings, trees and props');
  const py=JSON.parse(execFileSync('python',['-c',`import json,math,sys
from live.town import nearest_walkable as n
print(json.dumps([n(x,y) or n(x,y,reach=math.inf) for x,y in json.load(sys.stdin)]))`],{encoding:'utf8',input:JSON.stringify(centres.map(p=>[p.x,p.y])),env:{...process.env,PYTHONIOENCODING:'utf-8'}}));
  centres.forEach((p,i)=>{
    const down=m.landingSpot(nav,p),[sx,sy]=py[i];
    assert.ok(m.isWalkable(nav,down),`${JSON.stringify(p)}: the client lands on open ground`);
    assert.ok(m.isWalkable(nav,{x:sx,y:sy}),`${JSON.stringify(p)}: the server's spot is open ground for the client too`);
    assert.ok(Math.abs(Math.hypot(down.x-p.x,down.y-p.y)-Math.hypot(sx-p.x,sy-p.y))<.02,`${JSON.stringify(p)}: as near`);
    // the flight over it is never refused
    assert.equal(m.airRoute(nav,{x:p.x-3,y:p.y},p).length,1);
  });
});

test('the classic town: straight over the shops, down to the street on landing',async()=>{
  const T=await import('../public/js/scenes/town-place.js');
  const pl=T.plan(['grocery','pho','milk_tea','salon','tailor','laundry']),it=pl.items.find(i=>!i.lm)||pl.items[0];
  const roof=[it.cx,it.G-it.h*.6],street=it.stand;
  assert.equal(T.walkable(pl,roof),false,'a shop is not floor');
  const fly=T.airRoute(pl,street,roof);
  assert.deepEqual(fly,[street,roof],'a straight line onto the roof');
  assert.deepEqual(T.airRoute(pl,street,[-500,1e6]),[street,[14,pl.H-14]],'kept inside the town');
  assert.ok(T.airPoint(pl,[10,-200])[1]>0,'never above the top of the map');
  const down=T.groundRoute(pl,roof,street);
  assert.deepEqual(down[0],roof,'from where they are');
  assert.ok(T.walkable(pl,down[1]),'down to the nearest street point first');
  assert.deepEqual(down[1],T.nearest(pl,roof));
  for(const p of down.slice(1))assert.ok(T.walkable(pl,p));
  assert.deepEqual(T.groundRoute(pl,street,street),T.route(pl,street,street),'on the street: the usual route');
  const classic=read('../public/js/v4/town-walk.js');
  assert.match(classic,/const legPath=\(g,from\)=>g\.fly&&W\.fly\?airRoute\(W\.pl,from,g\.to\):groundRoute\(W\.pl,from,g\.to\)/);
  assert.match(classic,/else landNow\(\)/,'Hạ cánh: the rest on foot');
});

test('the strolls: a flyer goes straight (live/street.py Geo.air) and is drawn over everyone',()=>{
  const walk=read('../public/js/v4/walk.js');
  assert.match(walk,/air=m\.fl!=null,target=air\?airPoint\(S\.geo,x,y\):clamp\(x,y\)/);
  assert.match(walk,/m\.p=air\?airPath\(S\.geo,\[cx,cy\],target\):route\(\[cx,cy\],target\)/);
  assert.match(walk,/const up=p=>!p\.parked&&p\.fl!=null&&p\.wg&&!p\.s\?1e5:0/);
  const src=walk.match(/export const airPoint=[^\n]*\n/)[0]+walk.match(/export const airPath=[^\n]*\n/)[0];
  const W=(new Function(src.replace(/export /g,'')+';return {airPoint,airPath};'))();
  const geo={w:600,h:900};
  assert.deepEqual(W.airPath(geo,[100,200],[300,450]),[[100,200],[300,450]]);
  assert.deepEqual(W.airPoint(geo,-20,1200),[0,900]);
});

test('2.5D wiring: no collision in the air, landing, above the roofs',()=>{
  const world=read('../client/isometric/phaser-world.ts'),bundle=read('../public/js/isometric/phaser-world.js');
  assert.match(world,/\(air\?moveInAir:moveOnGround\)\(stage\.navigation/,'joystick and keys');
  assert.match(world,/'screen',air\?undefined:stage\.navigation\)/,'a route in the air never stops at a corner');
  assert.match(world,/this\.inAir\?airRoute\(this\.stage\.navigation,this\.player,h\.approach\)/,'doors: straight');
  assert.match(world,/if\(this\.inAir&&!this\.landing\)\{const nav=this\.stage!\.navigation,at=clampToBounds\(nav,ground\)/,'a tap anywhere on the map');
  assert.match(world,/if\(flight\)this\.landing=null;else if\(this\.wasAir\)this\.land\(\)/,'Hạ cánh glides down');
  assert.match(world,/getFly\(\)\{return this\.mode==='town'&&\(!!this\.flight\|\|!!this\.landing\)/,'the live service hears `fl` until they touch down');
  assert.match(world,/depth=this\.owner\.inAir\?FLY_DEPTH\+f\.y:f\.y\+\.5/,'me above the roofs');
  assert.match(world,/const depth=actor\.fly!=null\|\|actor\.down\?FLY_DEPTH\+point\.y:point\.y\+\.5/,'others too');
  assert.match(world,/this\.owner\.inAir\?\[\]:this\.occluderIndex\.query/,'no roof fades for a flyer');
  assert.match(world,/air\?airRoute\(this\.navigation,actor\.at,peer\):findRoute\(this\.navigation,actor\.at,peer\)/,'others fly straight');
  const statics=[...world.matchAll(/setDepth\((\d{4,})\)/g)].map(x=>+x[1]);
  assert.ok(statics.every(d=>d>=11000),'the HUD-like layers stay above flyers');
  const {FLY_DEPTH}={FLY_DEPTH:+world.match(/export const FLY_DEPTH=(\d+)/)[1]};
  assert.ok(FLY_DEPTH-1568>(80+58)*32,'above the farthest building of the island');
  assert.ok(FLY_DEPTH+(80+58)*32<11000,'below the effects');
  assert.match(bundle,/\.landing/,'the built scene carries it (npm run build:isometric)');
});
