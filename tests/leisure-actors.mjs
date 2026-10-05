import assert from 'node:assert/strict';
import test from 'node:test';
import {createLeisureActors} from '../public/js/isometric/leisure-actors.js';
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
