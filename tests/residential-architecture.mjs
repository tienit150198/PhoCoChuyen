import assert from 'node:assert/strict';
import {test} from 'node:test';
import * as T from 'three';
import {execFileSync} from 'node:child_process';
import {districtHomes,districtStep} from '../client/district3d/model.js';
const architecture=await import('../client/district3d/architecture.js').catch(()=>({}));
const source=JSON.parse(execFileSync('python',['-c',"from game import housing; import json; print(json.dumps(dict(homes=[dict(v,id=k) for k,v in housing.HOMES.items()])))"],{encoding:'utf8'}));
const content={journey:{homes:{homes:source.homes}}};
test('real owned and leased catalogue kinds survive the public directory mapping',()=>{
  const rows=districtHomes('apartment',content,{journey:{home:{own:{id:'p',kind:'tap_the'}}}},{market:[{id:'ad',kind:'can_ho_mini',status:'listing',owner_name:'Lan'}]});
  assert.equal(rows.find(x=>x.status==='current').kindId,'tap_the');assert.equal(rows.find(x=>x.status==='listing').kindId,'can_ho_mini');
});
test('each district has eight deterministic, structurally distinct authored homes with a clear street',()=>{
  assert.equal(typeof architecture.districtArchitecture,'function');assert.equal(typeof architecture.createResidenceKit,'function');
  const geometries=new Set(),materials=new Map(),kit=architecture.createResidenceKit(color=>{if(!materials.has(color))materials.set(color,new T.MeshStandardMaterial({color}));return materials.get(color);},geometries);
  try{for(const group of ['rent','apartment','townhouse','villa']){
    const homes=districtHomes(group,content,{},null),plans=architecture.districtArchitecture(group,homes);
    assert.equal(plans.length,8);assert.equal(new Set(plans.map(p=>p.id)).size,8);assert.deepEqual(plans,architecture.districtArchitecture(group,homes));
    const signatures=[];
    for(const [i,plan]of plans.entries()){
      const g=kit.build(plan),masses=[];let count=0;g.traverse(o=>{if(o.isMesh){count++;if(o.userData.structure==='mass')masses.push(o);}});
      assert.ok(count>=35&&count<700,plan.id+' has detailed but bounded architecture');assert.ok(masses.length>=2,plan.id+' has articulated volumes');
      g.updateMatrixWorld(true);
      signatures.push(masses.map(o=>{const b=new T.Box3().setFromObject(o);return [...b.min.toArray(),...b.max.toArray()].map(n=>+n.toFixed(2));}).sort().join('|'));
      g.position.set((i%2?1:-1)*6.6,0,Math.floor(i/2)*8-12);g.rotation.y=i%2?-Math.PI/2:Math.PI/2;g.updateMatrixWorld(true);
      const b=new T.Box3().setFromObject(g);assert.ok(i%2?b.min.x>3.05:b.max.x< -3.05,plan.id+' preserves the whole shared street');
      assert.ok(b.min.z>=-16&&b.max.z<=16,plan.id+' stays inside its district');
    }
    assert.equal(new Set(signatures).size,8,group+' differs in physical massing, not paint or windows');
    for(let y=-14;y<=14;y++)assert.deepEqual(districtStep({x:0,y},{x:0,y:0},.02),{x:0,y});
  }}finally{for(const g of geometries)g.dispose();for(const m of materials.values())m.dispose();}
});
