import assert from 'node:assert/strict';
import test from 'node:test';
import {createLeisureActors} from '../public/js/isometric/leisure-actors.js';
import {createLeisurePresence,publicActivity} from '../public/js/isometric/leisure-presence.js';
import {leisurePose} from '../public/js/pixel/places.js';
import {placeWorldPoint} from '../public/js/pixel/place-geometry.js';
const peer=(x=84,extra={})=>({pid:'peer',name:'Lan',look:{top:'ao'},gender:'female',activity:{kind:'fishing',x,y:170,direction:'ne',phase:'walk',moving:false,action:null,...extra}});
test('public actors filter places, interpolate positions and disappear with authoritative snapshots',()=>{
  const actors=createLeisureActors('fishing');actors.receive([peer(),{...peer(),pid:'other',activity:{...peer().activity,kind:'pool'}}]);
  assert.equal(actors.sample(.03).length,1);actors.receive([peer(94,{moving:true})]);
  const mid=actors.sample(.04)[0];assert.ok(mid.state.x>84&&mid.state.x<94);assert.equal(mid.state.moving,true);
  actors.receive([]);assert.equal(actors.sample(.03).length,0);
});
test('remote action timing is finite, does not replay repeated samples, and carries no private state',()=>{
  let now=1000;const actors=createLeisureActors('fishing',()=>now),p=peer(84,{action:'caught'});p.round='private';p.wallet=1000;actors.receive([p]);
  assert.equal(actors.sample(.03)[0].state.action.kind,'caught');now+=2100;
  assert.equal(actors.sample(.03)[0].state.action,null);actors.receive([p]);assert.equal(actors.sample(.03)[0].state.action,null);
  const visible=actors.sample(.03)[0];assert.equal(visible.round,undefined);assert.equal(visible.wallet,undefined);
  actors.receive([peer()]);actors.receive([p]);assert.equal(actors.sample(.03)[0].state.action.kind,'caught');
});

test('unchanged public snapshots do not wake idle rendering and motion settles to the reported position',()=>{
 let now=1000;const actors=createLeisureActors('fishing',()=>now),idle=peer();
 assert.equal(actors.receive([idle]),true);assert.equal(actors.needsFrame(),false);
 assert.equal(actors.receive([idle]),false,'unchanged town snapshots are ignored');
 assert.equal(actors.receive([peer(94)]),true);assert.equal(actors.needsFrame(),true);
 for(let i=0;i<80&&actors.needsFrame();i++)actors.sample(.04);
 assert.equal(actors.needsFrame(),false);assert.equal(actors.sample(0)[0].state.x,94);
 assert.equal(actors.receive([peer(94,{action:'cast'})]),true);assert.equal(actors.needsFrame(),true);
 now+=800;actors.sample(.04);assert.equal(actors.needsFrame(),false,'finite remote action clears even without another packet');
});

function waterPeerPipeline(kind){
 const presence=createLeisurePresence(),actors=createLeisureActors(kind,()=>1000);
 presence.subscribe(kind,people=>actors.receive(people));
 return {actors,receive(x,y,direction,moving=true,name='Lan'){
  const activity=publicActivity({kind,phase:kind,x,y,direction,moving,heading:1.234,action:null});
  assert.equal(activity.heading,undefined,'the existing public/server contract still excludes heading');
  presence.updatePeers([{pid:'water-peer',name,gender:'female',look:{},activity}]);
 },pose(){const state=actors.sample(0)[0].state;return {state,pose:leisurePose(state,0,1000,true)};}};
}
function assertHeading(pose,kind,dx,dy,message='body heading follows projected direction'){
 const origin=placeWorldPoint(kind,{x:0,y:0},true),end=placeWorldPoint(kind,{x:dx,y:dy},true);
 const expected=Math.atan2(end.y-origin.y,end.x-origin.x);
 assert.ok(Math.abs(pose.heading-expected)<1e-10,`${kind}: ${message}: ${pose.heading} should equal ${expected}`);
}

for(const kind of ['pool','boat'])for(const settled of [false,true])test(`${kind} stationary facing updates both head and body with interpolation ${settled?'settled':'in flight'}`,()=>{
 const h=waterPeerPipeline(kind);h.receive(100,100,'se');h.receive(110,102,'se');
 if(settled)for(let i=0;i<80;i++)h.actors.sample(.05);else h.actors.sample(.01);
 h.receive(110,102,'nw',false);
 const {state,pose}=h.pose();
 assert.equal(state.direction,'nw');assertHeading(pose,kind,-1,-1);
 assert.deepEqual({x:pose.x,y:pose.y},placeWorldPoint(kind,state,true),'facing changes preserve the shared peer coordinate conversion');
 h.receive(110,102,'nw',false,'New name');
 assertHeading(h.pose().pose,kind,-1,-1,'an appearance update cannot resurrect the old heading from interpolation drift');
});

for(const kind of ['pool','boat'])test(`${kind} uses reported travel for precise headings and retains them after stopping`,()=>{
 const h=waterPeerPipeline(kind);h.receive(100,100,'se');h.receive(110,102,'se');h.actors.sample(.01);
 h.receive(111,106,'se');
 assertHeading(h.pose().pose,kind,1,4);
 h.receive(111,106,'se',false);
 assertHeading(h.pose().pose,kind,1,4,'stopping keeps the precise travel angle, not a diagonal');
 h.receive(111,106,'se',false,'New name');
 assertHeading(h.pose().pose,kind,1,4,'cosmetic updates are not new movement');
 h.receive(107,105,'nw');
 assertHeading(h.pose().pose,kind,-4,-1,'new real movement takes precedence over a changed direction label');
});
