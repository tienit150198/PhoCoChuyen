// public/js/v4/ride.js: who rides what on the walkable maps (tests/test_ride.py runs this with node).
// The ride is only ever on for a save that owns a road vehicle that is not broken; the toggle goes through each owned
// vehicle, then walking, and is remembered (localStorage); the live presence's vehicle is checked; drawing a rider,
// parked or turning never throws.
import assert from 'node:assert/strict';

const store=new Map();
globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
const noop=()=>{};
const ctx2d=()=>new Proxy({measureText:s=>({width:String(s).length*6}),getTransform:()=>({a:1}),createLinearGradient:()=>({addColorStop:noop}),createRadialGradient:()=>({addColorStop:noop})},
  {get:(t,k)=>k in t?t[k]:noop,set:(t,k,v)=>{t[k]=v;return true;}});
globalThis.document={createElement:()=>({width:0,height:0,getContext:ctx2d})};
globalThis.Path2D=class{constructor(){return new Proxy({},{get:()=>noop});}};
const warned=[];console.warn=(...a)=>warned.push(a.map(String).join(' '));   // ride.js logs (and survives) an art error

const R=await import('../public/js/v4/ride.js');
const {figureOf,defaultLook}=await import('../public/js/v4/look.js');

const content={journey:{garage:{
  vehicles:[['xe_dap','bike','🚲','xanh_la'],['xe_ga','bike','🛵','xanh'],['o_to_suv','car','🚙','bac'],['du_thuyen','boat','🛥️','navy'],
    ['may_bay_nho','plane','🛩️','vang'],['xe_moi','bike','🛵','do']].map(([id,group,emoji,paint])=>({id,group,emoji,paint,name:id})),
  paints:[{id:'do',hex:'#d9534f'},{id:'xanh',hex:'#4f8fd1'},{id:'xanh_la',hex:'#5cbf9a'},{id:'bac',hex:'#b8bec6'},{id:'navy',hex:'#2f4a7a'},{id:'hong',hex:'#ef9bb8'}]}}};
const car=(id,color='do',extra={})=>({id,color,plate:'',...extra});
const save=(cars,ride=null,story=true)=>({journey:{story,garage:cars===null?undefined:{cars,ride}}});
const ids=list=>list.map(v=>v.id);

// No garage, an empty one, story mode off, only a boat and a plane: never riding, no toggle.
for(const s of [save(null),save([]),save([car('xe_ga')],null,false),save([car('du_thuyen'),car('may_bay_nho')]),{},{journey:null}]){
  assert.equal(R.choice(s,content),null,JSON.stringify(s));
  assert.equal(R.canRide(s,content),false);
  assert.equal(R.next(s,content),null);
}
assert.equal(R.choice(save([car('xe_ga')]),null),null,'an older server without the catalogue: walking');
// A broken vehicle stays home (game/rui.py: "Xe đang hỏng").
assert.equal(R.choice(save([car('xe_ga',undefined,{broken:40})]),content),null);
// Owned: riding by default, in its paint; the garage's "đang đi" first, a car only where cars go.
store.clear();
const both=save([car('xe_ga','hong',{plate:'MÂY 01'}),car('o_to_suv','bac')],'o_to_suv');
assert.deepEqual(ids(R.options(both,content)),['o_to_suv','xe_ga']);
assert.deepEqual(ids(R.options(both,content,{two:true})),['xe_ga']);
let v=R.choice(both,content);
assert.equal(v.id,'o_to_suv');assert.equal(v.kind,'suv');assert.equal(v.hex,'#b8bec6');
v=R.choice(both,content,{two:true});
assert.deepEqual([v.id,v.kind,v.hex,v.plate],['xe_ga','scooter','#ef9bb8','MÂY 01']);
assert.equal(R.label(v),'🛵 Đi xe');assert.equal(R.label(null),'🚶 Đi bộ');
assert.ok(R.speedOf(v)>1&&R.speedOf(null)===1);
// A vehicle id this build does not know (a newer server): drawn by its group; an unknown paint: its own.
assert.equal(R.choice(save([car('xe_moi','tim_moi')]),content).kind,'scooter');
assert.equal(R.choice(save([car('xe_moi','tim_moi')]),content).hex,'#d9534f');
// The toggle: the next owned vehicle, then walking, then the first again; remembered.
assert.equal(R.next(both,content).id,'xe_ga');
assert.equal(store.get('mnl.ride'),'1');assert.equal(store.get('mnl.ride.pick'),'xe_ga');
assert.equal(R.choice(both,content).id,'xe_ga');
assert.equal(R.next(both,content),null);
assert.equal(store.get('mnl.ride'),'0');
assert.equal(R.choice(both,content),null,'walking is remembered');
assert.equal(R.choice(both,content,{two:true}),null,'on every map');
assert.equal(R.next(both,content).id,'o_to_suv');
assert.equal(R.choice(both,content).id,'o_to_suv');
// The fair and the strolls only take a two-wheeler: the SUV picked in town means the scooter there.
assert.equal(R.choice(both,content,{two:true}).id,'xe_ga');
// A sold vehicle that was picked: the first one left.
assert.equal(R.choice(save([car('xe_dap')]),content).id,'xe_dap');
// Storage blocked: riding by default, the toggle still works for this visit.
const real=globalThis.localStorage;
globalThis.localStorage={getItem(){throw new Error('blocked');},setItem(){throw new Error('blocked');}};
assert.equal(R.next(save([car('xe_dap')]),content),null);
assert.equal(R.choice(save([car('xe_dap')]),content),null);
assert.equal(R.next(save([car('xe_dap')]),content).id,'xe_dap');
globalThis.localStorage=real;

// The live presence: {v, c} out, and back only for what this build can draw.
assert.deepEqual(R.wire(v),{v:'xe_ga',c:'hong'});assert.equal(R.wire(null),null);
assert.deepEqual([R.fromWire({v:'xe_ga',c:'hong'},content).kind,R.fromWire({v:'xe_ga',c:'hong'},content).hex],['scooter','#ef9bb8']);
assert.equal(R.fromWire({v:'xe_ga',c:'../x'},content).hex,'#4f8fd1','an odd paint: the default one');
for(const bad of [null,undefined,'xe_ga',5,{},{v:5},{v:'du_thuyen'},{v:'nope'},{v:'__proto__'}])assert.equal(R.fromWire(bad,content),null,JSON.stringify(bad));
assert.equal(R.fromWire({v:'xe_dap'},null).kind,'bicycle','an older content list: still drawn by its id');

// Steering: the side follows the way it goes, the turn eases through, the wheels roll.
const r=R.rider(-1);
R.steer(r,5,5,.016);assert.equal(r.face,1);assert.equal(r.from,-1);assert.ok(r.turn<1);
for(let i=0;i<30;i++)R.steer(r,0,0,.016);assert.equal(r.turn,1);
const a0=r.ang;R.steer(r,3,30,.016);assert.ok(r.ang!==a0);
const q=R.rider(1);R.steer(q,-2,2,.016,true);assert.equal(q.turn,1,'reduced motion: no turn animation');

// Every kind draws (with a rider, parked, mid-turn, facing either way) without throwing.
const F=figureOf(defaultLook('female'),'female'),c=ctx2d();
for(const kind of new Set(Object.values(R.KINDS))){
  const veh={id:kind,kind,hex:'#4f8fd1',plate:'AB 12'};
  for(const face of [-1,1]){
    R.drawRide(c,{x:10,y:20,s:.5,px:2,F,fkey:'f',v:veh,r:{face,from:-face,turn:.3,ang:1}});
    R.drawRide(c,{x:10,y:20,s:.5,px:2,v:veh,r:R.rider(face)});
  }
  assert.ok(R.halfOf(veh)>40&&R.topOf(veh)>80,kind);
}
assert.deepEqual(warned,[],'every vehicle draws without an error');
// 💑 The spouse's vehicles (GET /api/garage/spouse): listed after mine as "Xe của <tên>", picked by key (owner:id),
// sent with `o` (the owner's live id); a player with no vehicle of their own rides their spouse's.
store.clear();
const SPP='0123456789abcdef';
R.setSpouse({pid:SPP,name:'Lan',cars:[{id:'xe_ga',color:'xanh',plate:'LAN 02'},{id:'o_to_suv',color:'bac',plate:''},{id:'du_thuyen',color:'navy',plate:''}],ride:'o_to_suv'});
const mine=save([car('xe_ga','hong',{plate:'MÂY 01'})]);
assert.deepEqual(R.options(mine,content).map(v=>v.key),['xe_ga',SPP+':o_to_suv',SPP+':xe_ga']);
assert.deepEqual(R.options(mine,content,{two:true}).map(v=>v.key),['xe_ga',SPP+':xe_ga']);
const theirs=R.options(mine,content,{two:true})[1];
assert.deepEqual([theirs.o,theirs.owner,theirs.hex,theirs.plate],[SPP,'Lan','#4f8fd1','LAN 02']);
assert.equal(R.label(theirs),'🛵 Xe của Lan');
assert.deepEqual(R.wire(theirs),{v:'xe_ga',c:'xanh',o:SPP});
assert.deepEqual(R.wire(R.options(mine,content)[0]),{v:'xe_ga',c:'hong'},'my own: no owner on the wire');
assert.equal(R.next(mine,content,{two:true}).key,SPP+':xe_ga');
assert.equal(store.get('mnl.ride.pick'),SPP+':xe_ga');
assert.equal(R.choice(mine,content,{two:true}).owner,'Lan','the pick survives');
assert.equal(R.next(mine,content,{two:true}),null);
assert.equal(R.next(mine,content,{two:true}).key,'xe_ga');
assert.equal(R.choice(save([]),content).owner,'Lan','no vehicle of my own: the spouse one');
assert.equal(R.canRide(save(null),content),true);
assert.equal(R.choice(save([car('xe_ga')],null,false),content),null,'story mode off: never');
R.setSpouse(null);
assert.equal(R.canRide(save([]),content),false,'not married: as before');
// The spouse behind the driver: every two-wheeler draws it; a car (the town, no live seat) ignores it.
warned.length=0;
for(const kind of ['bicycle','ebike','cub','scooter','mini']){
  const veh={id:kind,kind,hex:'#4f8fd1',plate:''};
  for(const face of [-1,1])R.drawRide(c,{x:0,y:0,s:.5,px:2,F,fkey:'a',F2:F,fkey2:'b',v:veh,r:R.rider(face)});
}
assert.deepEqual(warned,[],'a pillion draws without an error');
let fetched=0;
const api={json:async u=>{fetched++;assert.equal(u,'/api/garage/spouse');return {spouse:{pid:SPP,name:'Minh',cars:[]}};}};
assert.equal((await R.loadSpouse(api,true)).name,'Minh');
await R.loadSpouse(api);assert.equal(fetched,1,'once a minute');
assert.equal(await R.loadSpouse({json:async()=>{throw new Error('404');}},true),R.spouse(),'an older server: kept, never thrown');
assert.equal(await R.loadSpouse({json:async()=>({spouse:{pid:'nope',name:'x',cars:[]}})},true),null,'an odd answer: none');
console.log('ride.mjs ok');
