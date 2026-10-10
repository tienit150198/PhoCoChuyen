import assert from 'node:assert/strict';
import {test} from 'node:test';
import {execFileSync} from 'node:child_process';
const model=await import('../client/home3d/model.js').catch(()=>({}));
const room={id:'living',cols:7,frows:4,wrows:2,out:false,fix:[]};
const chair={id:'chair',cat:'table',spot:'floor',w:1,h:1};
test('free saved coordinates round trip through the real 3D floor',()=>{
  assert.equal(typeof model.placement,'function','3D placement adapter exists');
  const p=model.placement(room,{id:'c',it:chair,q:{r:'living',x:43,y:17,f:0}},[]);
  assert.deepEqual(model.hitPlacement(room,chair,{x:p.x,y:0,z:p.z}),{r:'living',x:43,y:17,f:0});
});
test('wall coordinates and tabletop riders retain their saved zone',()=>{
  assert.equal(typeof model.placement,'function');
  const frame={id:'frame',it:{...chair,spot:'wall'},q:{r:'living',x:21,y:10,f:0}};
  const p=model.placement(room,frame,[]);
  assert.deepEqual(model.hitPlacement(room,frame.it,p),frame.q);
  const table={id:'t',it:{...chair,w:2,surface:24},q:{r:'living',x:20,y:20,f:0}};
  const cup={id:'cup',it:{...chair,spot:'top'},q:{r:'living',on:'t',x:10,y:0,f:0}};
  const on=model.placement(room,cup,[table,cup]);
  assert.ok(on.y>0,'small items stand above the 3D table');
  assert.deepEqual(model.hitPlacement(room,cup.it,on,{host:table,all:[table,cup]}),cup.q);
});
test('pointer commands keep foreign furniture read only and clamp to room',()=>{
  assert.equal(typeof model.editIntent,'function');
  const own={id:'a',it:chair,q:{r:'living',x:0,y:0,f:0}},mate={...own,id:'p:b',mate:true};
  assert.equal(model.editIntent({edit:true,remote:true,coop:false},mate,{x:0,z:0}),null);
  assert.equal(model.editIntent({edit:true},mate,{x:0,z:0}),null);
  assert.deepEqual(model.editIntent({edit:true},own,{x:0,z:0}),{type:'select',uid:'a'});
  assert.deepEqual(model.hitPlacement(room,chair,{x:99,y:0,z:-99}),{r:'living',x:120,y:0,f:0});
});
test('children and pets use bounded slots without replacing live residents',()=>{
  assert.equal(typeof model.boundedActors,'function');
  const people=Array.from({length:20},(_,i)=>({id:'p'+i})),family=Array.from({length:30},(_,i)=>({id:'b'+i}));
  const list=model.boundedActors([{id:'me'},...people],family,family);
  assert.equal(list.length,28);assert.equal(list[0].id,'me');assert.equal(list[11].id,'p10');
});
test('lazy scene closes pending mounts and disposes exactly once',async()=>{
  const {sceneSession}=await import('../public/js/v4/home-3d.js').catch(()=>({}));
  assert.equal(typeof sceneSession,'function');
  let finish,disposed=0,updates=0;
  const session=sceneSession(()=>new Promise(r=>finish=r));
  const pending=session.mount({},{});session.close();
  finish({createHomeScene:()=>({dispose(){disposed++;},update(){updates++;}})});
  await pending;assert.equal(disposed,0,'a closed pending mount never creates a renderer');
  const next=session.mount({},{});finish({createHomeScene:()=>({dispose(){disposed++;},update(){updates++;}})});
  await next;session.close();session.close();assert.equal(disposed,1);
});
test('every catalogue item produces volumetric meshes with category-specific silhouettes',async()=>{
  const mesh=await import('../client/home3d/meshes.js').catch(()=>({}));
  assert.equal(typeof mesh.furniture,'function');
  const items=JSON.parse(execFileSync('python',['-c',"from game import deco_content as d; import json; print(json.dumps([dict(v,id=k) for k,v in d.ITEMS.items()]))"],{encoding:'utf8'}));
  const palette=mesh.resources(),families=new Set();
  for(const it of items){const group=mesh.furniture(it,null,palette);let count=0;group.traverse(o=>{if(o.isMesh){count++;assert.ok(o.geometry.attributes.position.count>0);}});assert.ok(count>=2,it.id+' has physical detail');assert.ok(group.userData.family,it.id);families.add(group.userData.family);}
  assert.ok(families.size>=25,'recognizable furniture families, not generic boxes');palette.dispose();
});
test('outdoor rooms have railings and indoor rooms have actual walls and fixtures',async()=>{
  const mesh=await import('../client/home3d/meshes.js').catch(()=>({}));assert.equal(typeof mesh.roomStructure,'function');
  const palette=mesh.resources(),inside=mesh.roomStructure(room,null,palette),outside=mesh.roomStructure({...room,out:true,type:'yard'}, {},palette);
  assert.ok(inside.getObjectByName('back-wall'));assert.ok(inside.getObjectByName('floor'));
  assert.equal(outside.getObjectByName('back-wall'),undefined);assert.ok(outside.getObjectByName('garden-fence'));palette.dispose();
});
test('disposal releases shared geometry, materials and textures just once',async()=>{
  const THREE=await import('three');let calls=0;
  const geometry=new THREE.BoxGeometry(),material=new THREE.MeshBasicMaterial(),texture=new THREE.Texture();material.map=texture;
  for(const o of [geometry,material,texture])o.addEventListener('dispose',()=>calls++);
  const group=new THREE.Group();group.add(new THREE.Mesh(geometry,material),new THREE.Mesh(geometry,material));
  model.disposeTree(group);assert.equal(calls,3);assert.equal(group.children.length,0);
});
test('repair and upgrade state changes visible structure without changing the saved room',async()=>{
  const mesh=await import('../client/home3d/meshes.js'),palette=mesh.resources();
  const old=mesh.roomStructure(room,{floor:{c:30},wall:{c:30},roof:{c:30}},palette);
  const fresh=mesh.roomStructure(room,{floor:{c:100,lv:2},wall:{c:100,lv:2},roof:{c:100}},palette);
  assert.ok(old.getObjectByName('floor-damage'));assert.ok(old.getObjectByName('roof-damage'));
  assert.equal(fresh.getObjectByName('floor-damage'),undefined);assert.ok(fresh.getObjectByName('wall-upgrade'));
  palette.dispose();
});
test('a late rejected load from a closed home cannot fail the newly opened session',async()=>{
  const {sceneSession}=await import('../public/js/v4/home-3d.js');let reject;
  const session=sceneSession(()=>new Promise((resolve,no)=>reject=no));
  const opening=session.mount({},{});session.close();reject(new Error('old load'));
  assert.equal(await opening,null);
});
