import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
import {build} from 'esbuild';
const load=async path=>{const r=await build({entryPoints:[path],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});return import('data:text/javascript;base64,'+Buffer.from(r.outputFiles[0].text).toString('base64'));};
const art=await load('client/isometric/building-art.ts'),registry=await load('client/isometric/career-art.ts'),rooms=await load('client/isometric/work-layout.ts'),model=await load('client/isometric/model.ts'),facade=await load('client/isometric/career-facade.ts');
const cases={art_studio:{family:'office',base:'office',wanted:['board','desk','sink']},lawyer:{family:'office',base:'office',wanted:['bookcase','desk','sofa']},laundry:{family:'service',base:'home',wanted:['washer','rack','sink']},post_office:{family:'office',base:'garage',wanted:['crate','routeboard','shelf']}};
assert.equal(Object.keys(registry.CAREER_ART).length,50,'preserve the 50 finished paintings');
assert.equal(typeof art.careerPreview,'function','gallery needs an honest source resolver for new careers');
const fingerprints=new Set(),appearance=model.roomAppearance({upgrades:['plant','lamp','seat','rug','poster','shelf','workbench','board'],ops:{property:{tier:'garden'}}});
for(const [id,{family,base,wanted}] of Object.entries(cases)){
  const preview=art.careerPreview(id);
  assert.equal(preview.dedicated,false);assert.ok(existsSync('public'+preview.src),id+' uses a shipped image');
  assert.equal(art.BUILDING_ART[id],base);assert.ok(facade.careerFacadeTextureKey(id,base));
  assert.notEqual(preview.src,'/icons/careers-v1/'+id+'.webp');
  const room=rooms.workLayout(family,id),kinds=[...room.fixtures,...room.stations].map(f=>f.kind);
  assert.notEqual(room.identity.focus,'Chuẩn bị và bàn giao công việc');
  for(const k of wanted)assert.ok(kinds.includes(k),id+' has '+k);
  fingerprints.add(JSON.stringify({stations:room.stations,fixtures:room.fixtures,architecture:room.architecture}));
  assert.equal(room.architecture.career,id);assert.ok(room.architecture.elements.length>=3);
  const nav=rooms.workNavigation(room,appearance);
  const people=rooms.workActorPositions(room,nav,9);assert.equal(people.length,9);
  nav.obstacles.push(...people.map(rooms.workActorFootprint));
  for(const s of room.stations){assert.ok(model.isWalkable(nav,s.approach),id+'/'+s.id);assert.ok(model.findRoute(nav,room.spawn,s.approach).length,id+'/'+s.id+' reachable');}
}
assert.equal(fingerprints.size,4);
for(const [id,a] of Object.entries(registry.CAREER_ART))assert.deepEqual(art.careerPreview(id),{src:a.src,dedicated:true});
for(const id of ['unknown','__proto__','constructor'])assert.equal(art.careerPreview(id),null);
console.log('PASS four creative/civic interiors, routes, honest raster fallbacks and preserved 50 paintings');
