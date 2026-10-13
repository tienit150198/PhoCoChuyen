import assert from 'node:assert/strict';
import fs from 'node:fs';
const modulePath=new URL('../public/js/scenes/venue-place.js',import.meta.url);
assert.ok(fs.existsSync(modulePath),'Walkable venue scene is implemented');
const {VENUE_IDS,venueLayout,walkableVenue,venuePath,createVenueWalk,projectVenue,unprojectVenue}=await import(modulePath);
const ids=['cafe','spa','cinema','karaoke','bark','salon','nails','craft','books','art','music','reading','garden','family'];
assert.deepEqual(VENUE_IDS,ids);
for(const id of ids){
  const room=venueLayout(id);
  assert.ok(room.props.length>=6,`${id} is furnished`);
  assert.ok(room.stations.length>=2,`${id} has contextual stations`);
  assert.ok(walkableVenue(room,room.entry.x,room.entry.y),`${id} entry clear`);
  for(const station of room.stations){
    assert.ok(walkableVenue(room,station.x,station.y),`${id}/${station.id} standing point clear`);
    const path=venuePath(room,room.entry,station);
    assert.ok(path.length,`${id}/${station.id} reachable from entrance`);
    for(const p of path)assert.ok(walkableVenue(room,p.x,p.y),`${id} path avoids obstacles`);
  }
  const solid=room.props.find(p=>p.solid!==false);
  assert.equal(walkableVenue(room,solid.x+solid.w/2,solid.y+solid.h/2),false,`${id} solid furniture collides`);
  for(const p of room.props)for(const x of [p.x-9.1,p.x+p.w+9.1])for(const y of [p.y-9.1,p.y+p.h+9.1]){
    if(walkableVenue(room,x,y))assert.ok(venuePath(room,{x,y},room.entry).length,`${id} can return to entry from furniture corner ${x},${y}`);
  }
  const point={x:147,y:213},roundTrip=unprojectVenue(projectVenue(point));
  assert.ok(Math.hypot(roundTrip.x-point.x,roundTrip.y-point.y)<.00001);
}
assert.throws(()=>venueLayout('unknown'),/venue/i);
assert.ok(venueLayout('bark').title.includes('thú cưng'),'Bark venue is the pet playground for the existing dog tug-of-war game');
assert.equal(venueLayout('bark').props.some(p=>p.kind==='counter'),false,'Pet playground has no bar counter');
const room=venueLayout('cafe');let selected=[];
assert.ok(venuePath(room,{x:53,y:194},room.stations[0]).length,'A valid position beside a table corner connects to a clear neighboring route node');
const walk=createVenueWalk(room,{onInteract:s=>selected.push(s.id)});
assert.equal(walk.interact('counter'),false,'Cannot use a distant station');
walk.goTo(room.stations[0]);
for(let i=0;i<2000&&walk.needsFrame();i++)walk.step(.03);
assert.ok(Math.hypot(walk.state.x-room.stations[0].x,walk.state.y-room.stations[0].y)<4,'Tap path arrives');
assert.equal(walk.interact(room.stations[0].id),true,'Nearby station opens');
assert.deepEqual(selected,[room.stations[0].id]);
walk.setInput(1,0);walk.suspend();const before={x:walk.state.x,y:walk.state.y};walk.step(1);
assert.deepEqual({x:walk.state.x,y:walk.state.y},before,'Suspension clears held movement');
assert.equal(walk.interact(room.stations[0].id),false,'Suspension blocks service input');
walk.resume();walk.step(1);assert.deepEqual({x:walk.state.x,y:walk.state.y},before,'Resume never restores held input');
walk.setInput(1,0);for(let i=0;i<1000;i++)walk.step(.05);
assert.ok(walkableVenue(room,walk.state.x,walk.state.y),'Keyboard movement cannot enter a wall');
walk.destroy();const ended={x:walk.state.x,y:walk.state.y};walk.resume();walk.setInput(-1,0);walk.goTo(room.entry);walk.step(1);
assert.deepEqual({x:walk.state.x,y:walk.state.y},ended,'Disposed movement cannot restart');
let exits=0;const exiting=createVenueWalk(room,{onExit:()=>exits++});
assert.equal(exiting.exit(),true,'Physical entrance is an exit');assert.equal(exits,1);
exiting.goTo(room.stations[0]);for(let i=0;i<2000&&exiting.needsFrame();i++)exiting.step(.03);
assert.equal(exiting.exit(),false,'Exit cannot teleport from a distant station');
console.log('venue-visit: 14 furnished venues, reachable stations, collision, tap paths, proximity and lifecycle passed');
