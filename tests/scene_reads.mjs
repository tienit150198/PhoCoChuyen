// Unit test of public/js/scenes/room-watch.js (what a backdrop paint read of the game, boba-world.js backdrop()).
// Run by tests/test_scene_reads.py (node tests/scene_reads.mjs); exits non-zero on failure.
import assert from 'node:assert/strict';
import {watch} from '../public/js/scenes/room-watch.js';

const clone=v=>JSON.parse(JSON.stringify(v));
const deepFreeze=o=>{if(o&&typeof o==='object'){Object.values(o).forEach(deepFreeze);Object.freeze(o);}return o;};
const base={current:'milk_tea',clock:{minute:480},settings:{reduceMotion:false},
  careers:{milk_tea:{open:true,turn:3,money:120,theme:'warm',life:{shop_name:'Trà Mây'},
    ops:{property:{tier:'cozy'},security:{items:['lock']}},decor:{plant:{spot:'window'}},
    tasks:[{id:'a',status:'new',npc:'n1'},{id:'b',status:'completed',npc:'n2'}],feed:[{text:'hi'}]}}};
const content={catalogue:[{id:'milk_tea',station:'Quầy'},{id:'florist',station:'Bàn hoa'}]};

/** A tiny room like scenes/teabar.js: reads a few things of the career, never the clock or the money. */
function room(w){const c=w.c;
  const active=(c?.tasks||[]).filter(t=>!['completed','referred','cancelled'].includes(t.status)).length;
  const decor=Object.entries(c?.decor||{}).map(([id,e])=>id+'@'+e?.spot).join(',');
  const station=w.game?.catalogue?.find(x=>x.id===w.career)?.station;
  return [c?.open,c?.ops?.property?.tier,(c?.ops?.security?.items||[]).includes('lock'),active,decor,c?.life?.shop_name,'theme' in c,station,w.state.careers[w.career].theme].join('|');}
const world=(state,game=content)=>({career:state.current,state,c:state.careers[state.current],game});
const paint=w=>{const r=watch(w,['c','state','game']);let out;try{out=room(w);}finally{r.stop();}return [r,out];};

// The views answer exactly as the data, and hand the data back afterwards.
{const w=world(clone(base)),c=w.c,s=w.state;const [r,out]=paint(w);
  assert.equal(out,room(world(clone(base))));
  assert.equal(w.c,c);assert.equal(w.state,s);assert.equal(w.game,content);
  assert.ok(r.log.length>10);
  assert.ok(r.same(w),'nothing changed');}

// What the room does not show can change freely; what it shows repaints.
const after=(edit)=>{const w=world(clone(base));const [r]=paint(w);const next=clone(base);edit(next);return r.same(world(next));};
assert.equal(after(s=>{s.careers.milk_tea.turn=4;s.careers.milk_tea.money=90;s.clock.minute=495;s.careers.milk_tea.feed.push({text:'x'});}),true);
assert.equal(after(s=>{s.careers.milk_tea.tasks[0].npc='n9';}),true,'the queue shows a count, not who');
assert.equal(after(s=>{s.careers.milk_tea.tasks[1].status='new';}),false,'one more open order');
assert.equal(after(s=>{s.careers.milk_tea.tasks.push({id:'c',status:'new'});}),false,'a new order');
assert.equal(after(s=>{s.careers.milk_tea.open=false;}),false,'closing');
assert.equal(after(s=>{s.careers.milk_tea.ops.property.tier='garden';}),false,'a lease upgrade');
assert.equal(after(s=>{delete s.careers.milk_tea.ops;}),false,'a branch gone');
assert.equal(after(s=>{s.careers.milk_tea.ops.security.items=[];}),false,'a list emptied');
assert.equal(after(s=>{s.careers.milk_tea.decor.lamp={spot:'door'};}),false,'decor bought (Object.entries)');
assert.equal(after(s=>{s.careers.milk_tea.decor.plant.spot='door';}),false,'decor moved');
assert.equal(after(s=>{s.careers.milk_tea.life.shop_name='Trà Gió';}),false,'renamed');
assert.equal(after(s=>{delete s.careers.milk_tea.theme;}),false,"'in' check");
assert.equal(after(s=>{s.careers.milk_tea.theme='sage';}),false,'read through state too');
// Another catalogue: same answers keep the drawing, a different station repaints.
{const w=world(clone(base));const [r]=paint(w);
  assert.equal(r.same(world(clone(base),clone(content))),true);
  const other=clone(content);other.catalogue[0].station='Quầy bar';assert.equal(r.same(world(clone(base),other)),false);}
// A world before its first state: nothing to read, and a state arriving repaints.
{const w={career:'milk_tea',state:null,c:null,game:null};const r=watch(w,['c','state','game']);r.stop();
  assert.equal(r.same(w),true);assert.equal(r.same(world(clone(base))),false);}

// Frozen states (api.js dev check) are read the same, through stand-in targets.
{const w=world(deepFreeze(clone(base)),deepFreeze(clone(content)));const [r,out]=paint(w);
  assert.equal(out,room(world(clone(base))));assert.ok(r.same(w));
  const r2=watch(w,['c']);try{assert.throws(()=>{'use strict';w.c.open=false;},TypeError);}finally{r2.stop();}
  assert.equal(w.c.open,true);}

// Writes go through to the data; arrays stay arrays; Maps and class instances are handed out as they are.
{const m=new Map([['k',1]]);const w={c:{list:[1,2,3],m,nested:{a:1}}};const r=watch(w,['c']);
  try{assert.ok(Array.isArray(w.c.list));assert.deepEqual([...w.c.list],[1,2,3]);assert.equal(w.c.list.map(x=>x*2).join(),'2,4,6');
    assert.equal(JSON.stringify(w.c.nested),'{"a":1}');assert.deepEqual({...w.c.nested},{a:1});
    assert.equal(w.c.m,m);assert.equal(w.c.m.get('k'),1);assert.equal(w.c.nested,w.c.nested,'one view per object');
  }finally{r.stop();}
  const later=w.c,n=r.log.length;
  assert.ok(r.same(w));w.c.m=new Map();assert.equal(r.same(w),false,'another Map');w.c.m=m;
  // Reads after stop() are not noted.
  const r3=watch(w,['c']);const kept=w.c;r3.stop();const n3=r3.log.length;kept.list.length;assert.equal(r3.log.length,n3);
  assert.equal(later,w.c);assert.equal(r.log.length,n);
  const r4=watch(w,['c']);try{w.c.nested.b=2;delete w.c.nested.a;}finally{r4.stop();}
  assert.deepEqual(w.c.nested,{b:2},'writes reach the data');}
// Values compare with Object.is: NaN stays NaN, 0 and -0 differ (a repaint at worst).
{const w={c:{x:NaN,z:0}};const r=watch(w,['c']);try{w.c.x;w.c.z;}finally{r.stop();}assert.equal(r.same(w),true);
  w.c.z=-0;assert.equal(r.same(w),false);}

console.log('scene_reads ok');
