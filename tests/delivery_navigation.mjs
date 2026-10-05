import assert from 'node:assert/strict';
import {B,gateOf,onRoad,waypoint,roadRoute,navigation} from '../public/js/careers/delivery_navigation.js';
import * as navModule from '../public/js/careers/delivery_navigation.js';
let pairs=0;
for(let ax=0;ax<=6;ax++)for(let ay=0;ay<=4;ay++)for(let bx=0;bx<=6;bx++)for(let by=0;by<=4;by++){
 const a=gateOf({x:ax,y:ay}),b=gateOf({x:bx,y:by}),r=roadRoute(a.x,a.y-2.2,b);
 assert.deepEqual(r[0],{x:a.x,y:a.y-2.2});
 assert.ok(Math.hypot(r.at(-1).x-b.x,r.at(-1).y-(b.y-2))<.001,'ends at destination bay');
 for(let i=1;i<r.length;i++){
  const p=r[i-1],q=r[i],n=Math.ceil(Math.hypot(q.x-p.x,q.y-p.y)*2);
  for(let k=0;k<=n;k++)assert.ok(onRoad(p.x+(q.x-p.x)*k/(n||1),p.y+(q.y-p.y)*k/(n||1),.3),'every route segment is on the road');
 }
 assert.deepEqual(roadRoute(a.x,a.y-2.2,b),r,'deterministic route');
 const nav=navigation(r,0,b);
 assert.ok(Number.isFinite(nav.distance)&&nav.distance>=0);
 assert.equal(nav.distance,r.slice(1).reduce((sum,p,i)=>sum+Math.hypot(p.x-r[i].x,p.y-r[i].y),0));
 pairs++;
}
const target=gateOf({x:3,y:2});
assert.equal(navigation([{x:target.x,y:target.y-2}],0,target).cue,'arrive');
assert.equal(navigation([{x:0,y:0},{x:40,y:0},{x:40,y:40}],0,target).cue,'right');
assert.equal(navigation([{x:0,y:0},{x:40,y:0},{x:40,y:40}],0,target).turnDistance,40);
assert.equal(navigation([{x:0,y:0},{x:40,y:0}],Math.PI,target).cue,'uturn');
assert.equal(navigation([{x:0,y:0},{x:40,y:0}],0,target).cue,'straight');
assert.equal(B,40);assert.equal(typeof waypoint,'function');

// Approaching a junction must announce the nearest turn, even when under five metres away.
for(const [x,y,t,heading,cue] of [[40,76,{x:2,y:2},Math.PI/2,'left'],[116,0,{x:3,y:2},0,'right']]){
 const g=gateOf(t),nav=navigation(roadRoute(x,y,g),heading,g);
 assert.equal(nav.cue,cue,'nearest junction direction');
 assert.ok(nav.turnDistance>=2.5&&nav.turnDistance<=3.5,'nearest junction is about three metres away');
}
// Brief lane-centering corrections are not junction turns.
assert.equal(navigation([{x:0,y:-2},{x:0,y:0},{x:30,y:0}],0,target).cue,'straight');
const aligned=navigation([{x:0,y:0},{x:20,y:0},{x:20,y:.75},{x:40,y:0},{x:40,y:40}],0,target);
assert.equal(aligned.cue,'right');
assert.ok(aligned.turnDistance>40&&aligned.turnDistance<41,'ignore a sub-metre alignment wiggle before the real turn');
console.log(`ok: ${pairs} deterministic road routes and navigation cues`);
assert.equal(typeof navModule.mapTransform,'function');
for(const zoom of [1,1.5,2.25,3])for(const [x,y] of [[0,0],[240,160],[120,80]]){
 const view=navModule.mapTransform(600,420,zoom,{x,y});
 assert.ok(x*view.scale+view.ox>=0&&x*view.scale+view.ox<=600);
 assert.ok(y*view.scale+view.oy>=0&&y*view.scale+view.oy<=420);
}
const view=navModule.mapTransform(600,420,3,{x:-1000,y:1000});
assert.ok(view.center.x>=0&&view.center.y<=160,'panning is bounded to the town');
