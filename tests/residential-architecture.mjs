import assert from 'node:assert/strict';
import {test} from 'node:test';
import * as T from 'three';
import {execFileSync} from 'node:child_process';
import {districtHomes,districtStep} from '../client/district3d/model.js';
import {roomStructure,resources} from '../client/home3d/meshes.js';
import {dimensions,placement,hitPlacement} from '../client/home3d/model.js';
const architecture=await import('../client/district3d/architecture.js').catch(()=>({}));
const source=JSON.parse(execFileSync('python',['-c',"from game import housing,deco; import json; print(json.dumps(dict(homes=[dict(v,id=k) for k,v in housing.HOMES.items()],rooms={k:deco.rooms_of('rent:'+k+':1' if v['kind']=='rent' else 'own:p:'+k) for k,v in housing.HOMES.items()})))"],{encoding:'utf8'}));
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
test('actual home kinds select distinct interior architecture while preserving saved placement coordinates',()=>{
  const R=resources(),profiles=new Set(),shells=new Set();
  try{for(const [kind,rooms]of Object.entries(source.rooms)){
    const room=rooms[0],scope=(kind==='ky_tuc_xa'||kind==='tro_moi')?'rent:'+kind+':1':'own:p:'+kind;
    const before=JSON.stringify(room),g=roomStructure(room,{},R,scope);assert.ok(g.userData.architecture,kind+' selects an authored shell');profiles.add(g.userData.architecture);
    const {width,depth}=dimensions(room),floor=g.getObjectByName('floor');g.updateMatrixWorld(true);const box=new T.Box3().setFromObject(floor);
    assert.ok(Math.abs(box.max.x-box.min.x-width)<.01);assert.ok(Math.abs(box.max.z-box.min.z-depth)<.01);
    const item={id:'chair',it:{spot:'floor',w:1,h:1},q:{r:room.id,x:20,y:20,f:0}},at=placement(room,item,[]);
    assert.deepEqual(hitPlacement(room,item.it,at),item.q);assert.equal(JSON.stringify(room),before);
    const standard={id:'living',type:'living',cols:7,frows:4,wrows:2,out:false,fix:[]},shell=roomStructure(standard,{},R,scope),physical=[];
    shell.traverse(o=>{if(o.isMesh&&o.userData.architectureOnly)physical.push([o.geometry.type,...o.position.toArray(),...o.scale.toArray(),o.rotation.x,o.rotation.y,o.rotation.z].join(','));});
    shells.add(physical.sort().join('|'));
  }
  assert.equal(profiles.size,12,'all twelve housing kinds have distinct structural interior treatments');
  assert.equal(shells.size,12,'identically sized rooms have twelve different structural geometries without relying on paint');
  }finally{R.dispose();}
});
test('estate signature rooms render their actual reserved fixtures as detailed geometry',()=>{
  const R=resources();
  try{for(const [type,fixture,layer]of [['study','bookwall','wall'],['cinema','screen','wall'],['cellar','racks','wall'],['gym','mirror','wall'],['closet','rails','wall'],['showroom','gate','wall'],['showroom','car','floor'],['pavilion','gazebo','floor']]){
    const room={id:type,type,cols:8,frows:4,wrows:2,out:type==='pavilion',fix:[{t:fixture,layer,x:1,y:0,w:3,h:2}]},g=roomStructure(room,{},R,'estate:vuon:1');let count=0;
    g.traverse(o=>{if(o.isMesh&&o.userData.fixture===fixture)count++;});assert.ok(count>=3,fixture+' is recognized as actual built-in structure');
  }}finally{R.dispose();}
});

test('deep windows are actual openings in reserved window cells, not geometry hidden behind a solid wall',()=>{
  const R=resources(),room={id:'living',type:'living',cols:7,frows:4,wrows:2,out:false,fix:[{t:'window',layer:'wall',x:2,y:0,w:2,h:1}]};
  try{for(const kind of ['can_ho_studio','can_ho_1pn','penthouse','biet_thu_song']){
    const g=roomStructure(room,{},R,'own:p:'+kind);g.updateMatrixWorld(true);
    const {width,depth,height}=dimensions(room),f=room.fix[0],x=-width/2+f.x+f.w/2,y=height-(f.y+f.h/2)*1.1;
    const ray=new T.Raycaster(new T.Vector3(x+.2,y+.1,1),new T.Vector3(0,0,-1));
    const hit=ray.intersectObject(g,true).find(q=>!q.object.userData.architectureOnly);
    assert.equal(hit?.object.userData.fixture,'window',kind+' keeps the actual window as the first visible surface');
    assert.ok(hit.point.z < -depth/2-.3,kind+' reveals the real depth behind the wall');
  }}finally{R.dispose();}
});

test('verandas and stair halls have open side walls, while central floor navigation stays clear',()=>{
  const R=resources(),room={id:'living',type:'living',cols:7,frows:4,wrows:2,out:false,fix:[]};
  try{for(const kind of ['can_ho_mini','nha_pho','nha_san','biet_thu_vuon','biet_thu_song']){
    const g=roomStructure(room,{},R,'own:p:'+kind);g.updateMatrixWorld(true);const side=g.getObjectByName('side-wall'),b=new T.Box3().setFromObject(side);
    assert.ok(b.max.y<=.82,kind+' exposes its actual side architecture');
    const walkingVolume=new T.Box3(new T.Vector3(-3.15,.08,-1.6),new T.Vector3(3.15,1.65,1.6));
    g.traverse(o=>{if(o.isMesh&&o.userData.architectureOnly)assert.equal(new T.Box3().setFromObject(o).intersectsBox(walkingVolume),false,kind+' architecture does not insert an unsaved walking obstacle');});
  }}finally{R.dispose();}
});
