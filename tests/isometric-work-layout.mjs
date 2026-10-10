import assert from 'node:assert/strict';
import {existsSync,readFileSync} from 'node:fs';
import {build,transform} from 'esbuild';
import {KIND_OF,wordsFor} from '../public/js/scenes/vocabulary.js';
import {SceneFx} from '../public/js/v4/scene-events.js';

assert.ok(existsSync('client/isometric/work-layout.ts'), 'career rooms need authored, testable furniture plans');
const compiled=await build({entryPoints:['client/isometric/work-layout.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const room=await import('data:text/javascript;base64,'+Buffer.from(compiled.outputFiles[0].text).toString('base64'));
const modelBuild=await build({entryPoints:['client/isometric/model.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const model=await import('data:text/javascript;base64,'+Buffer.from(modelBuild.outputFiles[0].text).toString('base64'));
assert.equal(typeof room.workEventAnchors,'function','room events need semantic anchors derived from the current furniture');
// Run the actual plan() body, then the real event path consumer. A nurse's shelf
// and treatment bed sit far from the old shop's fixed shelf/table coordinates.
const worldSource=readFileSync('client/isometric/phaser-world.ts','utf8');
const planBody=worldSource.slice(worldSource.indexOf('  plan(){'),worldSource.indexOf('  resize(){')).replace('  plan(){','function plan(){');
const planJs=await transform(planBody,{loader:'ts',format:'cjs'});
const actualPlan=new Function('px','workWindowAnchors','workEventAnchors',planJs.code+'; return plan;')(model.project,model.workWindowAnchors,room.workEventAnchors);
const nurseLayout=room.workLayout('ward','nurse'),nurse={hotspots:nurseLayout.stations.map(s=>({...s.at,id:s.id,approach:s.approach,range:45})),reduced:true,time:3,isPortrait:()=>false,scene:()=>({id:'iso-ward'})};
nurse.plan=()=>actualPlan.call(nurse);
const event=new SceneFx();
for(const [target,station] of [['shelf','shelf'],['till','counter'],['table','workbench']]){
  const projected=model.project(nurseLayout.stations.find(s=>s.id===station).approach),expected=[projected.x,projected.y];
  event.start(nurse,{id:'nurse-'+target,target,anim:'spill',actor:'customer'});
  assert.deepEqual(nurse.plan().anchors[target],expected,`nurse ${target}: spilled items use the actual station approach`);
  assert.deepEqual(event.path(nurse,3).p,expected,`nurse ${target}: the real event actor stands beside the correct furniture`);
}
const windowAnchors=model.workWindowAnchors();
assert.deepEqual(nurse.plan().anchors.glass,[windowAnchors.glass.x,windowAnchors.glass.y],'window events still use the glass, never the treatment bed');
assert.deepEqual(nurse.plan().anchors.window,[windowAnchors.window.x,windowAnchors.window.y],'window debris preserves the real sill anchor');
const containsRect=(outer,inner)=>outer.x0<=inner.x0&&outer.y0<=inner.y0&&outer.x1>=inner.x1&&outer.y1>=inner.y1;
const nurseWard=nurseLayout.floors.find(f=>f.label==='Buồng bệnh'),nurseDesk=nurseLayout.floors.find(f=>f.label==='Điều dưỡng');
const nursingSurface=nurseLayout.stations.find(s=>s.id==='workbench').footprint;
assert.ok(containsRect(nurseDesk.footprint,nursingSurface),'nursing area contains the nursing workbench');
assert.ok(!containsRect(nurseWard.footprint,nursingSurface),'patient ward does not label the nursing workbench');
for(const bed of nurseLayout.fixtures.filter(f=>f.kind==='bed')){
  assert.ok(containsRect(nurseWard.footprint,bed.footprint),'every patient bed belongs to the named patient ward');
  assert.ok(!containsRect(nurseDesk.footprint,bed.footprint),'patient beds are separate from the nursing area');
}
const lighthouseLayout=room.workLayout('lighthouse','lighthouse'),lighthouseDuty=lighthouseLayout.stations.find(s=>s.id==='workbench');
assert.equal(lighthouseDuty.kind,'desk','the general lighthouse duty action uses a duty desk');
assert.match(lighthouseLayout.identity.workbench,/trực|ca/,'lighthouse workbench names the general duty action');
assert.equal(wordsFor('lighthouse').workbench,lighthouseLayout.identity.workbench,'lighthouse action vocabulary and rendered workbench agree');
const lighthouseGarden=lighthouseLayout.floors.find(f=>f.label==='Vườn rau trên đá');
assert.ok([...lighthouseLayout.stations,...lighthouseLayout.fixtures].some(f=>f.kind==='planter'&&containsRect(lighthouseGarden.footprint,f.footprint)),'lighthouse garden remains its own planted area');
assert.ok(!containsRect(lighthouseGarden.footprint,lighthouseDuty.footprint),'garden label does not describe the duty desk');
const cabinLayout=room.workLayout('airfield','flight_attendant');
assert.ok(cabinLayout.floors.some(f=>f.label==='Khoang bếp'),'aircraft galley zone uses the same terminology as its supply station');
assert.doesNotMatch([cabinLayout.identity.focus,cabinLayout.identity.workbench,...cabinLayout.identity.zones].join(' | '),/bếp tàu|cửa (?:ra )?tàu/i,'cabin identity does not reuse sea or railway vocabulary');
const ids=['shelf','warehouse','workbench','counter','evidence','board','door','pet','ops:finance','ops:property','ops:security'].sort();
const decorated=model.roomAppearance({upgrades:['plant','lamp','seat','rug','poster','shelf','workbench','board'],ops:{property:{tier:'garden'}}});
// Reserving the union proves every supported choice or combination fits, including
// legacy `wall` floor placements and the optional property bench/flower pots.
for(const spot of ['corner','center','front','wall','window']){
  decorated.decor.push(...model.roomAppearance({upgrades:['plant','lamp','seat','rug','poster'],decor:Object.fromEntries(['plant','lamp','seat','rug','poster'].map(id=>[id,{spot}]))}).decor);
}
const fingerprints=new Set(),floorPlans=new Set(),furniturePlans=new Set();
// Compare physical plans independently of labels, colours and career IDs: a
// renamed room is still the same room. Check before the navigation suite so the
// failure identifies which occupations have silently fallen back to one plan.
const occupationalPlans=new Map();
for(const [career,family] of Object.entries(KIND_OF)){
  const layout=room.workLayout(family,career);
  const shape=({kind,footprint})=>({kind,footprint}),canonical=items=>items.map(item=>JSON.stringify(item)).sort();
  const fingerprint=JSON.stringify({stations:canonical(layout.stations.map(shape)),fixtures:canonical(layout.fixtures.map(shape)),floors:canonical(layout.floors.map(({footprint,pattern})=>({footprint,pattern})))});
  assert.ok(!occupationalPlans.has(fingerprint),`${career} must have its own occupational plan; duplicates ${occupationalPlans.get(fingerprint)}`);
  occupationalPlans.set(fingerprint,career);
}
const focuses=new Set();
const officeNames=Object.entries(KIND_OF).filter(([,family])=>family==='office').map(([career])=>wordsFor(career).counter);
assert.equal(new Set(officeNames).size,officeNames.length,'office handover stations describe each actual department');
for(const [career,family] of Object.entries(KIND_OF)){
  const layout=room.workLayout(family,career);
  assert.ok(layout.identity?.focus,`${career}: the room explains its work focus`);
  assert.ok(!focuses.has(layout.identity.focus),`${career}: focus must describe this occupation`);
  focuses.add(layout.identity.focus);
  assert.ok(layout.identity.workbench,`${career}: the actual work surface has an occupational name`);
  assert.equal(layout.floors.filter(f=>f.label).length,2,`${career}: two named functional areas accompany the room`);
}
let checked=0;
for(const [career,family] of [...Object.entries(KIND_OF),['unknown','shop']]){
  const layout=room.workLayout(family,career);
  assert.deepEqual(layout.stations.map(s=>s.id).sort(),ids,`${career}: every old interaction remains available`);
  assert.deepEqual(layout.spawn,{x:6.4,y:6.4},'saved entry remains stable');
  assert.ok(layout.floors.length>=2,`${career}: the room has functional floor zones`);
  assert.ok(layout.fixtures.length>=2,`${career}: visible furnishings carry career identity`);
  for(const station of layout.stations)if(station.footprint){
    assert.deepEqual(station.at,{x:(station.footprint.x0+station.footprint.x1)/2,y:station.footprint.y1},`${career}/${station.id}: the interaction follows its final furniture footprint`);
  }
  fingerprints.add(JSON.stringify(layout.stations.filter(s=>s.footprint).map(s=>s.footprint)));
  floorPlans.add(JSON.stringify(layout.floors.map(({footprint,pattern})=>({footprint,pattern}))));
  furniturePlans.add(JSON.stringify(layout.fixtures.map(({kind,footprint})=>({kind,footprint}))));
  for(const appearance of [model.roomAppearance({}),decorated]){
    const before=JSON.stringify(appearance),nav=room.workNavigation(layout,appearance);
    assert.equal(JSON.stringify(appearance),before,'rendering never rewrites saved decorations');
    assert.ok(model.isWalkable(nav,layout.spawn),`${career}: spawn must remain clear with saved decor`);
    const checkApproaches=()=>{
      for(const station of layout.stations){
        assert.ok(model.isWalkable(nav,station.approach),`${career}/${station.id}: approach is inside free floor`);
        const route=model.findRoute(nav,layout.spawn,station.approach);
        assert.ok(route.length,`${career}/${station.id}: reachable with all furnishings and saved decor`);
        let previous=layout.spawn;
        for(const point of route){assert.ok(model.lineClear(nav,previous,point),`${career}/${station.id}: route never crosses furniture`);previous=point;}
      }
    };
    checkApproaches();
    const people=room.workActorPositions(layout,nav,9);
    assert.equal(people.length,9,`${career}: active customers, staff and event visitors all fit`);
    for(const at of people){
      assert.ok(model.isWalkable(nav,at),`${career}: actor stands on free floor`);
      nav.obstacles.push(room.workActorFootprint(at));
    }
    checkApproaches();
    for(const at of people)assert.ok(model.findRoute(nav,layout.spawn,{x:at.x-.6,y:at.y+.35}).length,`${career}: all actor interactions remain reachable`);
  }
  checked++;
}
assert.ok(fingerprints.size>=10,'rooms must change station arrangement, not just colors');
assert.ok(floorPlans.size>=6,'families use materially different floor zoning');
assert.ok(furniturePlans.size>=10,'families have distinct furniture types and placement');
for(const [career,expected] of [['cafe_bakery','oven'],['pharmacy','medicine'],['nurse','bed'],['teacher','chalkboard'],['babysitter','crib'],['farm','planter'],['library','bookcase'],['pilot','routeboard'],['salon','mirror'],['repair','tools']]){
  const layout=room.workLayout(KIND_OF[career],career);
  assert.ok([...layout.stations,...layout.fixtures].some(p=>p.kind===expected),`${career} preserves its original scene's distinguishing furniture (${expected})`);
}
for(const [career,signature] of [['pilot','console'],['flight_attendant','seatrow'],['lighthouse','beacon'],['oil','pipework'],['lifeguard','pool'],['railway','signal'],['it_helpdesk','rack'],['giupviec','washer'],['garbage','bin'],['ice_cream','freezer']]){
  const layout=room.workLayout(KIND_OF[career],career);
  assert.ok([...layout.stations,...layout.fixtures].some(f=>f.kind===signature),`${career}: recognizable occupational silhouette (${signature})`);
}
const source=readFileSync('client/isometric/phaser-world.ts','utf8').split('  private work(){')[1].split('  private operationsStation(')[0];
assert.match(source,/workLayout\(/,'the active renderer consumes the authored plans');
assert.match(source,/workNavigation\(/,'the active renderer uses the geometry verified above');
assert.match(source,/workActorPositions\(/,'task actors use the same protected approaches');
assert.doesNotMatch(source,/this\.roomBackdrop\(/,'a flattened generic room must not hide the authored career floor plan');
assert.match(source,/savedRoomDetails\(\{\.\.\.appearance/,'saved appearance and upgrades remain rendered without mutating their stored anchors');
assert.match(source,/layout\.identity\.focus/,'work focus is visible in the active room');
assert.match(source,/zone\.label/,'functional area names are visible in the active room');
console.log(`PASS ${checked} careers: distinct interiors, all actions and actors reachable with maximum saved decor`);
