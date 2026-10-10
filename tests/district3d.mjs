import test from 'node:test';
import assert from 'node:assert/strict';
import {districtStep,districtHomes,customerPoint} from '../client/district3d/model.js';
test('diagonal movement stays normalized and in the shared public street',()=>{
  const a=districtStep({x:0,y:0},{x:1,y:1},.05),b=districtStep({x:0,y:0},{x:1,y:0},.05);
  assert.ok(Math.abs(Math.hypot(a.x,a.y)-b.x)<1e-9);
  assert.deepEqual(districtStep({x:2.8,y:14},{x:1,y:1},3),{x:2.8,y:14});
});
test('public houses identify real ownership and listings, catalogue houses are marked model',()=>{
  const content={journey:{homes:{homes:[{id:'v',group:'villa',name:'Villa'},{id:'r',group:'rent',name:'Trọ'}]}}};
  const rows=districtHomes('villa',content,{journey:{home:{own:{id:'p1',kind:'v'}}}},{market:[{id:'ad',kind:'v',status:'listing',owner_name:'Lan'}]});
  assert.deepEqual(rows.map(r=>r.status),['current','listing','model']);assert.equal(rows[1].label,'Lan · cho thuê');
  assert.equal(districtHomes('rent',content,{},{}).length,1);
});
test('six reused customers stay in walking space over a full day',()=>{
  for(let t=0;t<86400;t+=37)for(let i=0;i<6;i++){const p=customerPoint(i,t);assert.ok(Math.abs(p.x)<2&&Math.abs(p.y)<=13);}
});

const housingContent={journey:{homes:{homes:[
  {id:'garden',group:'villa',kind:'own',name:'Biệt thự vườn'},
  {id:'river',group:'villa',kind:'own',name:'Biệt thự sông'},
  {id:'dorm',group:'rent',kind:'rent',name:'Ký túc xá'},
]}}};
test('shared home is the current residence when the public place says shared',()=>{
  const rows=districtHomes('villa',housingContent,{journey:{home:{shared:{id:'spouse-house',kind:'garden',name:'Lan'},place:{where_id:'shared',kind:'garden',group:'villa'}}}},{});
  assert.equal(rows[0].status,'current');assert.equal(rows[0].id,'shared:spouse-house');
  assert.match(rows[0].label,/ở cùng/);assert.equal(rows.filter(r=>r.status==='current').length,1);
});
test('actual luxury estate takes precedence over the stored owned home',()=>{
  const rows=districtHomes('villa',housingContent,{journey:{home:{own:{id:'p1',kind:'garden'},place:{where_id:'estate',kind:'estate_1',group:'villa',name:'Dinh thự đang ở'}}}},{});
  assert.deepEqual(rows.filter(r=>r.status==='current').map(r=>r.name),['Dinh thự đang ở']);
  assert.equal(rows.find(r=>r.id==='own:p1').status,'owned');
  assert.equal(rows[0].status,'current','the current place remains in the eight visible scene slots');
});
test('active player rental uses public home tenancy if directory loading fails',()=>{
  const home={own:{id:'p1',kind:'garden'},tenancy:{id:'lease1',kind:'river'},place:{where_id:'lease',kind:'river',group:'villa'}};
  const rows=districtHomes('villa',housingContent,{journey:{home}},null);
  assert.equal(rows.find(r=>r.id==='own:p1').status,'owned');
  assert.deepEqual(rows.filter(r=>r.status==='current').map(r=>r.id),['lease:lease1']);
});
test('inactive ownership and tenancies never override the authoritative public place',()=>{
  const home={rent:{kind:'dorm'},own:{id:'p1',kind:'garden'},shared:{id:'s1',kind:'river'},place:{where_id:'attic',kind:null,group:null}};
  const rentals={tenancy:{id:'expired',kind:'river'}};
  for(const group of ['rent','villa'])assert.equal(districtHomes(group,housingContent,{journey:{home}},rentals).filter(r=>r.status==='current').length,0);
});
test('owned property labels distinguish existing tenancy from public listings',()=>{
  const home={props:[{id:'p2',kind:'garden',let:{name:'NPC'}},{id:'p3',kind:'river'}],place:{where_id:'attic',kind:null}};
  const rows=districtHomes('villa',housingContent,{journey:{home}},{mine:[{property:'p3',status:'listing'}]});
  assert.equal(rows.find(r=>r.id==='own:p2').status,'owned');assert.match(rows.find(r=>r.id==='own:p2').label,/đang cho thuê/);
  assert.match(rows.find(r=>r.id==='own:p3').label,/đăng cho thuê/);
});
test('UI retains a bounded full rental page and catalogue independently of the eight scene slots',()=>{
  const market=Array.from({length:130},(_,i)=>({id:'ad'+i,kind:'garden',status:'listing',owner_name:'Lan'}));
  const input={journey:{home:{own:{id:'p1',kind:'river'},place:{where_id:'own',kind:'river'}}}},before=JSON.stringify({input,market,housingContent});
  const rows=districtHomes('villa',housingContent,input,{market,next_offset:100});
  assert.equal(rows.filter(r=>r.status==='listing').length,100);
  assert.equal(rows.filter(r=>r.status==='model').length,2);
  assert.equal(rows.length,103);
  assert.ok(rows.some(r=>r.id==='listing:ad99'));
  assert.equal(JSON.stringify({input,market,housingContent}),before,'directory composition never changes state or server data');
});
