// 🏗️ Công trình của phố on the client: the shared page data (v4/town-projects-data.js), the 2.5D lots
// (client/isometric/town-projects.ts, game/town_layout.json tp_*), the old town's lots (scenes/town-place.js) and the
// menu entries. Server rules: tests/test_town_projects.py.
import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {build} from 'esbuild';

const noop=()=>{};
const ctx2d=()=>new Proxy({measureText:s=>({width:String(s).length*7}),createRadialGradient:()=>({addColorStop:noop}),createLinearGradient:()=>({addColorStop:noop}),getImageData:()=>({data:[]})},{get:(t,k)=>k in t?t[k]:noop,set:(t,k,v)=>{t[k]=v;return true;}});
globalThis.document??={hidden:false,createElement:()=>({getContext:ctx2d})};
globalThis.location??={search:''};

async function compiled(path){const result=await build({entryPoints:[path],bundle:true,write:false,format:'esm',platform:'node',logLevel:'silent'});return import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].text).toString('base64'));}
const data=await import('../public/js/v4/town-projects-data.js');
const art=await compiled('client/isometric/town-projects.ts');
const model=await compiled('client/isometric/model.ts'),trails=await compiled('client/isometric/trail-geometry.ts');
const place=await import('../public/js/scenes/town-place.js');
const {townUtilityGroups,townServiceAvailable}=await import('../public/js/isometric/town-utilities.js');
const layout=JSON.parse(readFileSync('game/town_layout.json','utf8'));
const IDS=['cong_vien','rap_phim','thu_vien','san_van_dong','cau_ra_dao','benh_vien'];
const STAGES=['soon','funding','building','done'];

const view=(over={})=>({now:1000,projects:[
  {id:'cong_vien',status:'done',goal:20e6,raised:20e6,ready:500},
  {id:'rap_phim',status:'building',goal:30e6,raised:30e6,ready:1000+3600*30+10},
  {id:'thu_vien',status:'funding',goal:30e6,raised:13.5e6},
  {id:'san_van_dong',status:'soon',goal:50e6,raised:0}],...over});

test('each lot gets its stage: built, hours left, money raised, still to come',()=>{
  const s=data.stagesOf(view(),1000);
  assert.deepEqual(s.map(x=>x.id),IDS);
  assert.deepEqual(s.slice(0,4),[{id:'cong_vien',stage:'done',pct:0,left:0},{id:'rap_phim',stage:'building',pct:0,left:31},
    {id:'thu_vien',stage:'funding',pct:45,left:0},{id:'san_van_dong',stage:'soon',pct:0,left:0}]);
  assert.equal(s[5].stage,'soon','a project the page does not list is still to come');
  assert.equal(data.stagesOf(view(),1000+3600*31).find(x=>x.id==='rap_phim').stage,'done','a build past its time shows built');
  assert.equal(data.stagesOf({projects:[{id:'thu_vien',status:'funding',goal:100,raised:100}]},0)[2].pct,99,'never 100% while still raising');
  assert.ok(data.stagesOf(null).every(x=>x.stage==='soon'));
  assert.equal(data.leftText(2*86400+3*3600+59),'2 ngày 3 giờ');
  assert.equal(data.leftText(5*3600+12*60),'5 giờ 12 phút');
  assert.equal(data.leftText(30),'Sắp xong');
});

test('one request a minute shared by the panel and both maps, never a throw',async()=>{
  data.resetTownForTests();
  let calls=0,fail=false;const api={json:async url=>{calls++;assert.equal(url,'/api/town');if(fail)throw new Error('down');return view();}};
  const seen=[];data.onTown(v=>seen.push(v));
  const world={got:[],setTownProjects(x){this.got.push(x);}};
  await Promise.all([data.loadTown(api),data.loadTown(api)]);
  assert.equal(calls,1);assert.equal(seen.length,1);
  data.syncWorld(world,api);assert.equal(world.got.length,1);assert.equal(calls,1,'a fresh page is reused');
  fail=true;assert.ok(await data.loadTown(api,{force:true}),'a failed load keeps the last page');
  data.syncWorld({},api);   // an older bundle without setTownProjects: nothing
  data.resetTownForTests();
});

test('the island paints every lot in every stage, from untrusted input only known lots',()=>{
  assert.deepEqual(art.TOWN_PROJECT_IDS,IDS);
  assert.deepEqual(art.normalizeTownProjects([{id:'x'},{id:'rap_phim',stage:'building',left:99,pct:50},{id:'rap_phim',stage:'done'},{id:'thu_vien',stage:'??',pct:'7'}]),
    [{id:'rap_phim',stage:'building',pct:0,left:48},{id:'thu_vien',stage:'soon',pct:0,left:0}]);
  assert.deepEqual(art.normalizeTownProjects('nope'),[]);
  assert.equal(art.townProjectBadge({stage:'funding',pct:45}),'🏗️ 45%');
  assert.equal(art.townProjectBadge({stage:'building',left:0}),'⏳ 1h');
  assert.equal(art.townProjectBadge({stage:'done'}),'');
  for(const id of IDS){
    const lot=layout.amenities.find(a=>a.id==='tp_'+id),size=art.townProjectCanvas(lot.footprint);
    assert.ok(size.width<=640&&size.height<=640&&size.originX>0&&size.originY>0,id+' is a small texture');
    for(const stage of STAGES)art.drawTownProject(ctx2d(),id,stage,lot.footprint);
  }
  assert.match(readFileSync('client/isometric/phaser-world.ts','utf8'),/setTownProjects\(value:unknown\)/);
  assert.ok(readFileSync('public/js/isometric/phaser-world.js','utf8').includes('town-project-'),'the shipped bundle is rebuilt');
});

test('six lots on the island: solid plots beside the road, each reachable and opening its project',()=>{
  const lots=layout.amenities.filter(a=>a.id.startsWith('tp_'));
  assert.deepEqual(lots.map(a=>a.id.slice(3)),IDS);
  const buildings=model.townBuildings(layout.careerOrder.map(id=>({id}))),nav=model.townNavigation(buildings);
  const overlap=(a,b)=>a.x0<b.x1&&a.x1>b.x0&&a.y0<b.y1&&a.y1>b.y0;
  const distance=(p,r)=>Math.hypot(Math.max(r.x0-p.x,0,p.x-r.x1),Math.max(r.y0-p.y,0,p.y-r.y1));
  const others=[...buildings.map(b=>b.footprint),...layout.commons.map(c=>c.footprint),...layout.shopLots.map(s=>s.footprint),...layout.planting.map(p=>p.footprint),
    ...layout.amenities.filter(a=>a.footprint&&!a.id.startsWith('tp_')).map(a=>a.footprint)];
  const lanes=layout.trails.flatMap((t,i)=>trails.streetProfile(trails.sampleTrailCurve(t.points,t.sampled),t.width,i));
  const entrances=[...layout.lots.map(p=>p.door),...layout.shopLots.map(p=>p.door),...layout.amenities.map(p=>p.at),...layout.commons.map(p=>p.approach)];
  for(const [i,lot] of lots.entries()){
    const r=lot.footprint,c={x:(r.x0+r.x1)/2,y:(r.y0+r.y1)/2};
    assert.equal(lot.action,'townProjects');assert.deepEqual(lot.actionData,{id:lot.id.slice(3)});assert.ok(lot.label&&lot.icon&&lot.hint);
    assert.ok(model.insideIsland(c),lot.id+' is on the island');
    assert.equal(model.isWalkable(nav,c),false,lot.id+' is not walked through');
    for(const other of [...others,...lots.slice(0,i).map(l=>l.footprint)])assert.equal(overlap(r,other),false,lot.id+' overlaps nothing');
    for(const at of entrances)assert.ok(distance(at,r)>.14,lot.id+' leaves every entrance free');
    for(const point of lanes)assert.ok(distance(point,r)>point.radius+.1,lot.id+' stays off the road');
    assert.ok(model.isWalkable(nav,lot.at),lot.id+' approach is free');
    const path=model.findRoute(nav,{x:6.2,y:6.2},lot.at);assert.ok(path.length,lot.id+' has a route');
  }
});

test('the old town has the six lots in their own block, painted for every stage',()=>{
  const pl=place.plan([]);
  for(const id of IDS){
    const L=place.LANDMARKS['tp_'+id];assert.equal(L.action,'townProjects');assert.deepEqual(L.data,{id});
    assert.equal(pl.items.filter(it=>it.lm==='tp_'+id).length,1);
    assert.equal(place.kindOf('lm:tp_'+id),'project');
  }
  assert.ok(pl.rows[5].districts.some(d=>d.id==='cong_trinh'));
  for(const stage of [...STAGES,undefined])place.back(ctx2d(),pl,it=>({color:'#5f8f3e',emoji:'🏗️',name:'x',stage,pct:45,left:31}));
  const walk=readFileSync('public/js/v4/town-walk.js','utf8');
  assert.match(walk,/L\.action,L\.data\|\|\{\}/,'the card button carries the project id');
  assert.match(walk,/s\.stage,s\.pct,s\.left/,'a new stage repaints the cached town');
});

test('menus: Tiện ích and Khu phố for a story player only, the app opens the panel',()=>{
  assert.equal(townServiceAvailable('townProjects',{journey:{story:true}}),true);
  assert.equal(townServiceAvailable('townProjects',{journey:{}}),false);
  const items=townUtilityGroups({journey:{story:true}},{},{}).flatMap(g=>g.items);
  assert.ok(items.some(x=>x.action==='townProjects'));
  const app=readFileSync('public/js/app.js','utf8');
  assert.match(app,/items\.push\(\['townProjects','building','Công trình của phố'\]\)/);
  assert.match(app,/'jrTown','rank','townProjects'(,'[A-Za-z]+')*\]/);   // later entries (⚔️ bang) may follow
  assert.match(app,/action==='townProjects'\)\{await \(await import\('\.\/v4\/town-projects\.js'\)\)\.openTownProjects\(env\(\),data\)/);
  assert.match(readFileSync('public/js/iso-guide.js','utf8'),/syncProjects\(env\)/);
});

test('every new visible line has its English',()=>{
  const en=JSON.parse(readFileSync('public/i18n/en.json','utf8'));
  for(const s of ['Công trình của phố','Sắp xây','Công viên ven sông','Bệnh viện phường','Nhà tài trợ vàng','Góp gạch xây phố','Xem cả bia ghi danh'])assert.ok(en.strings[s],s);
  const patterns=en.patterns.map(([re,out])=>[new RegExp(re),out]);
  for(const s of ['Góp 10.000 xu','Bấm lần nữa để góp 1.000.000 xu','🚧 Đang xây · còn 31 giờ','👥 12 người góp'])assert.ok(patterns.some(([re])=>re.test(s)),s);
});
