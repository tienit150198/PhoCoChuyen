// Headless check of the delivery street view's town (public/js/careers/delivery_drive.js), no browser needed.
// The stops come on stdin (game/careers/delivery.py NODES, as tests/test_delivery_drive.py sends them):
//   • every stop's door bay (where stopping arrives) lies on the street, clear of the junctions and of the other stops;
//   • from every stop to every other, following the on-screen arrow (waypoint) keeps the scooter on the street and
//     ends in the target's bay — the town is rideable, the arrow never points into a wall;
//   • no house or stop building stands on a street or a pavement, no two buildings overlap.
// Exits non-zero on failure.
import assert from 'node:assert/strict';
globalThis.document={documentElement:{classList:{contains:()=>false}},body:{classList:{contains:()=>false}}};
const {B,onRoad,gateOf,waypoint,buildWorld}=await import('../public/js/careers/delivery_drive.js');

const nodes=JSON.parse(await new Promise(done=>{let s='';process.stdin.on('data',d=>{s+=d;});process.stdin.on('end',()=>done(s));}));
const HW=5,FRONT=8;
const inBay=(x,y,g)=>Math.abs(x-g.x)<6.5&&y>=g.y-HW-1&&y<=g.y+HW+1;

// Door bays.
for(const [id,n] of Object.entries(nodes)){
  const g=gateOf(n);
  assert.ok(onRoad(g.x,g.y-2.2),`${id}: the start point by its door is on the street`);
  assert.ok(onRoad(g.x-5,g.y)&&onRoad(g.x+5,g.y),`${id}: its bay is street`);
  for(let i=0;i<=6;i++)assert.ok(Math.abs(g.x-i*B)>HW+6.5,`${id}: its bay is clear of the junction`);
  for(const [id2,n2] of Object.entries(nodes)){if(id2===id)continue;const h=gateOf(n2);assert.ok(h.gy!==g.gy||Math.abs(h.x-g.x)>=13,`${id} and ${id2}: bays overlap`);}
}

// Ride every pair by the arrow: steer straight at the waypoint, a metre at a time.
let legs=0;
for(const [a,na] of Object.entries(nodes))for(const [b,nb] of Object.entries(nodes)){
  if(a===b)continue;
  const from=gateOf(na),T=gateOf(nb);
  let x=from.x,y=from.y-2.2,steps=0,done=false;
  while(steps++<2000){
    const wp=waypoint(x,y,T),dx=wp.x-x,dy=wp.y-y,d=Math.hypot(dx,dy);
    if(wp.last&&inBay(x,y,T)&&d<2){done=true;break;}
    const k=Math.min(1,d)/(d||1);x+=dx*k;y+=dy*k;
    assert.ok(onRoad(x,y,.3),`${a}→${b}: off the street at ${x.toFixed(1)},${y.toFixed(1)} (waypoint ${wp.x},${wp.y})`);
  }
  assert.ok(done,`${a}→${b}: the arrow never led to the door`);
  legs++;
}

// Buildings: off the streets, not inside one another.
const W=buildWorld(nodes),boxes=[];
for(const list of W.cells.values())for(const b of list)if(b.zb===0&&!b.pump)boxes.push(b);
for(const b of boxes){
  for(let i=0;i<=6;i++)assert.ok(b.x1<=i*B-FRONT+.01||b.x0>=i*B+FRONT-.01||b.y1<=-FRONT||b.y0>=4*B+FRONT,`a building stands on street x=${i*B}`);
  for(let j=0;j<=4;j++)assert.ok(b.y1<=j*B-FRONT+.01||b.y0>=j*B+FRONT-.01||b.x1<=-FRONT||b.x0>=6*B+FRONT,`a building stands on street y=${j*B}`);
}
// Trees and lamps stand on the pavements, not on a street.
assert.ok(W.trees.length>40,'the pavements have trees');
for(const t of W.trees)assert.ok(!onRoad(t.x,t.y,-.6),`a tree on the street at ${t.x.toFixed(1)},${t.y.toFixed(1)}`);
for(const l of W.lamps)assert.ok(!onRoad(l.x,l.y,0),`a lamp on the street at ${l.x.toFixed(1)},${l.y.toFixed(1)}`);
let overlaps=0;
for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){
  const p=boxes[i],q=boxes[j];if(p.L&&q.L&&p.L===q.L)continue;   // one stop's own parts
  if(p.x0<q.x1-.05&&q.x0<p.x1-.05&&p.y0<q.y1-.05&&q.y0<p.y1-.05)overlaps++;
}
assert.equal(overlaps,0,'buildings overlap');
assert.equal(Object.keys(W.marks).length,Object.keys(nodes).length,'every stop has its building');
assert.ok(W.houses.every(h=>Number.isInteger(h.no)&&h.no>0),'every house has its number');
console.log(`ok: ${Object.keys(nodes).length} stops, ${legs} legs ridden by the arrow, ${boxes.length} buildings`);
