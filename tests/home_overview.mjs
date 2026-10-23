// 🗺️ Tổng quan nhà and 🚘 Hầm để xe, the client's pure parts (public/js/v4/home-overview.js, villa-garage.js), on the
// real plans (tests/test_homelife.py writes game/home_overview.py's catalogue and runs `node tests/home_overview.mjs
// <plans.json>`; without it, a small plan): every room of a plan is drawn once, inside the stage, never over another
// room, the floors from the top down, the garage under the ground, at phone and desktop widths and every zoom; who is
// home stands in a room of the plan; then the overview and the garage render from a save without throwing.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const noop=()=>{};
const store=new Map();
globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
const mk=cls=>{const root={innerHTML:'',querySelector:()=>null,clientWidth:360},dlg={open:false,listeners:{},dataset:{},setAttribute:noop,addEventListener(t,f){this.listeners[t]=f;},
  showModal(){this.open=true;},close(){this.open=false;},querySelector:s=>s===cls?root:null,contains:()=>true};return {root,dlg};};
const dialogs=[mk('.ho-root'),mk('.vg-root')];let next=0;
globalThis.document={querySelector:()=>({}),createElement:t=>t==='dialog'?dialogs[next++].dlg:{width:0,height:0,getContext:()=>new Proxy({},{get:()=>noop})},
  body:{append:noop},head:{append:noop},getElementById:()=>null};
globalThis.Path2D=class{constructor(){return new Proxy({},{get:()=>noop});}};

const O=await import('../public/js/v4/home-overview.js');
const G=await import('../public/js/v4/villa-garage.js');

const fixture=process.argv[2]?JSON.parse(readFileSync(process.argv[2],'utf8')):null;
const plans=fixture?.plans||{demo:{kind:'demo',name:'Nhà',emoji:'🏠',group:'villa',garage:{style:'ham',name:'Hầm',slots:4},
  floors:[{fl:1,name:'Tầng trệt',rooms:[{id:'living',type:'living',emoji:'🛋️',name:'Phòng khách',cols:9,frows:4,zone:'in'},{id:'yard',type:'yard',emoji:'🌳',name:'Vườn',cols:9,frows:4,zone:'garden'}]},
    {fl:2,name:'Lầu 1',rooms:[{id:'bed',type:'bed',emoji:'🛏️',name:'Phòng ngủ',cols:8,frows:4,zone:'in'},{id:'balcony',type:'balcony',emoji:'🌤️',name:'Ban công',cols:6,frows:2,zone:'deck'}]}]}};
assert.ok(Object.keys(plans).length>=1);

const overlap=(a,b)=>a.x<b.x+b.w&&b.x<a.x+a.w&&a.y<b.y+b.h&&b.y<a.y+a.h;
for(const [kind,plan] of Object.entries(plans)){
  const ids=plan.floors.flatMap(f=>f.rooms.map(r=>r.id));
  for(const width of [300,358,720])for(const zoom of [O.ZOOM_MIN,1,O.ZOOM_MAX]){
    const L=O.layoutPlan(plan,{width,zoom}),tag=`${kind} @${width}px ×${zoom}`;
    assert.deepEqual(L.rooms.map(r=>r.id).sort(),[...ids].sort(),`${tag}: every room once`);
    assert.equal(L.w,width,tag);
    for(const r of L.rooms){
      assert.ok(r.x>=0&&r.y>=0&&r.x+r.w<=L.w&&r.y+r.h<=L.h,`${tag}: ${r.id} inside the stage`);
      assert.ok(r.w>=20&&r.h>=30,`${tag}: ${r.id} big enough to tap`);
      assert.ok(r.y+r.h<=L.ground,`${tag}: ${r.id} above the ground`);
    }
    for(let i=0;i<L.rooms.length;i++)for(let k=i+1;k<L.rooms.length;k++)assert.ok(!overlap(L.rooms[i],L.rooms[k]),`${tag}: ${L.rooms[i].id} / ${L.rooms[k].id}`);
    const tops=L.floors.map(f=>[f.fl,f.y]);
    for(let i=1;i<tops.length;i++)assert.ok(tops[i-1][0]>tops[i][0]&&tops[i-1][1]<tops[i][1],`${tag}: the floors from the top down`);
    for(const r of L.rooms){const f=L.floors.find(x=>x.fl===r.fl);assert.ok(r.y>=f.y&&r.y+r.h<=f.y+f.h,`${tag}: ${r.id} on its floor`);}
    if(plan.garage?.slots){assert.ok(L.garage&&L.garage.y>=L.ground&&L.garage.y+L.garage.h<=L.h,`${tag}: the garage under the ground`);}
  }
  const ppl=O.placePeople(plan,[{k:'me'},{k:'spouse',n:'A'},{k:'child',n:'B'},{k:'pet',n:'C'},{k:'pet',n:'D'},{k:'guest',n:'E'}]);
  for(const p of ppl)assert.ok(ids.includes(p.room),`${kind}: ${p.k} stands in a room of the plan`);
  if(ids.includes('living'))assert.equal(ppl[0].room,'living');
  const garden=plan.floors.flatMap(f=>f.rooms).find(r=>r.type==='yard'||r.type==='pavilion');
  if(garden)assert.equal(ppl[3].room,garden.id,`${kind}: the first pet in the garden`);
}
assert.equal(G.bayName('ham',0),'B1-01');
assert.equal(G.bayName('ham',11),'B1-12');
assert.equal(G.bayName('chung',1),'Ô 2');

// Rendering from a save (the fixture's state, when given): no throw, the rooms and the bays are there, a tap sends.
if(fixture?.state){
  const calls=[];
  const env={api:{state:fixture.state,content:fixture.content,addEventListener:noop,json:async()=>({}),command:async(a,p)=>{calls.push([a,p]);return {message:'OK'};}},
    closeSheet:noop,openSheet:noop,confirmAction:async()=>true,toast:noop};
  const tick=()=>new Promise(r=>setTimeout(r,0));
  await O.openOverview(env);await tick();
  const ho=dialogs[0].root.innerHTML;
  const kind=fixture.state.journey.homelife.ov.kind;
  for(const r of plans[kind].floors.flatMap(f=>f.rooms))assert.ok(ho.includes(`data-room="${r.id}"`),`overview: ${r.id}`);
  assert.ok(ho.includes('Việc nhà hôm nay')&&ho.includes('Ai đang ở nhà'));
  const click=async(d,data)=>{d.listeners.click({target:{closest:()=>({dataset:data,disabled:false})},preventDefault:noop});await tick();await tick();};
  await click(dialogs[0].dlg,{ho:'chore',act:'tuoi_cay'});
  assert.deepEqual(calls.pop(),['jr_chore_do',{act:'tuoi_cay'}]);
  await G.openVillaGarage(env);await tick();
  const vg=dialogs[1].root.innerHTML,park=fixture.state.journey.homelife.hamxe.park;
  assert.ok(park.length&&park.every(id=>vg.includes(`data-id="${id}"`)),'garage: the parked vehicles');
  assert.ok(vg.includes('B1-01'));
  await click(dialogs[1].dlg,{vg:'pick',id:park[0]});
  assert.ok(dialogs[1].root.innerHTML.includes('data-vg="wash"'));
  await click(dialogs[1].dlg,{vg:'wash',id:park[0]});
  assert.deepEqual(calls.pop(),['jr_hamxe_wash',{id:park[0]}]);
}
console.log(`home_overview.mjs: ${Object.keys(plans).length} plans OK`);
