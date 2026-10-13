import assert from 'node:assert/strict';
import {scaleRoom} from '../public/js/v4/scale-site.js';
import {venuePath,walkableVenue} from '../public/js/scenes/venue-place.js';
for(const cid of ['grocery','laundry','homestay','lawyer','salon','police','pagoda','art_studio']){
 const room=scaleRoom({cid,title:'Cơ sở thử',resource_name:'Vị trí',resources:Array.from({length:6},(_,i)=>({id:`r${i+1}`,label:`Máy ${i+1}`,crew_name:'Lan',site:'base'}))},{id:'base',name:'Cơ sở gốc'});
 assert.equal(room.stations.length,8);
 assert.ok(walkableVenue(room,room.entry.x,room.entry.y));
 for(const s of room.stations){assert.ok(walkableVenue(room,s.x,s.y));assert.ok(venuePath(room,room.entry,s).length,`${cid}/${s.id} unreachable`);}
 assert.ok(room.stations.every(s=>s.site==='base'));
 assert.equal(room.actors.length,6);
 assert.equal(room.actors[0].name,'Lan');
}
const other=scaleRoom({cid:'grocery',resources:[{id:'secret',site:'branch-2'}]},{id:'base',name:'Gốc'});
assert.ok(!other.stations.some(s=>s.id==='secret'));
console.log('8 career site interiors: collision, reachable stations, staff and site isolation passed');
