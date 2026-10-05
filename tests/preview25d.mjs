import assert from 'node:assert/strict';
import {walkable,move,route,SPAWN,SHOPS,advance} from '../public/preview25d/model.js';
assert.ok(walkable(SPAWN));
for(const shop of SHOPS){
 const path=route(SPAWN,shop.at);assert.ok(path.length,shop.name+' has a reachable doorstep');
 let p=SPAWN;
 for(const q of path){for(let i=0;i<=50;i++)assert.ok(walkable({x:p.x+(q.x-p.x)*i/50,y:p.y+(q.y-p.y)*i/50}),'path stays on paving');p=q;}
}
assert.equal(walkable({x:280,y:500}),false,'grocery walls block movement');
assert.equal(walkable({x:870,y:430}),false,'ocean is not walkable');
for(const axis of [{x:1,y:1},{x:-1,y:-1},{x:1,y:-1},{x:-1,y:1}]){
 const next=move(SPAWN,axis,.04);
 assert.ok((next.x-SPAWN.x)*axis.x>0&&(next.y-SPAWN.y)*axis.y>0,'both diagonal axes move');
 assert.ok(Math.abs(Math.hypot(next.x-SPAWN.x,next.y-SPAWN.y)-7.2)<1e-6,'diagonal speed normalized');
}
let p=SPAWN;for(let i=0;i<800;i++){p=move(p,{x:1,y:-1},.04);assert.ok(walkable(p),'continuous collision holds against shops');}
assert.deepEqual(move(SPAWN,{x:0,y:0},.04),SPAWN,'release stops immediately');
assert.deepEqual(move(SPAWN,{x:NaN,y:0},.04),SPAWN,'invalid input cannot corrupt position');
assert.deepEqual(advance({x:0,y:0},[{x:1,y:0},{x:1,y:3}],2).point,{x:1,y:1},'waypoints consume the whole stride');
console.log('Preview 2.5D: diagonal speed, routes, collision and release passed');
