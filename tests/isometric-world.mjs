import assert from 'node:assert/strict';
import {build} from 'esbuild';

const compiled = await build({entryPoints:['client/isometric/model.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const m = await import('data:text/javascript;base64,'+Buffer.from(compiled.outputFiles[0].text).toString('base64'));
for(const name of ['project','unproject','makeNavigation','findRoute','lineClear','gestureIsDrag','activeTasks','townBuildings','townNavigation','townLandmarks','groundCacheRegion','townBuildingArt','islandCoastline','insideIsland','activeIslandRegions','islandOverviewCamera','islandWorldBounds','isWalkable','cameraWorldPoint','defaultCamera','resizedCamera','normalizeMovementInput','moveOnGround','advanceRoute','followCamera','presenceDirection','publicTownPlayers','interpolateRoute','roomAppearance','canvasDescription','effectFrameState','nearestReachableHotspot','workWindowAnchors'])
  assert.equal(typeof m[name], 'function', `Missing ${name}`);

for(const p of [{x:0,y:0},{x:-3.75,y:5.2},{x:30,y:17}]){
  const screen=m.project(p,64,32,{x:200,y:70}),back=m.unproject(screen,64,32,{x:200,y:70});
  assert.ok(Math.abs(back.x-p.x)<1e-10&&Math.abs(back.y-p.y)<1e-10,'inverse restores ground coordinates');
}
assert.deepEqual(m.project({x:1,y:0},64,32),{x:64,y:32},'projection uses a true 2:1 diamond');
const camera={width:800,height:600,scrollX:100,scrollY:200,zoom:1},cursor={x:150,y:400},before=m.cameraWorldPoint(cursor,camera);
camera.zoom=2;const after=m.cameraWorldPoint(cursor,camera);camera.scrollX+=before.x-after.x;camera.scrollY+=before.y-after.y;
assert.deepEqual(m.cameraWorldPoint(cursor,camera),before,'zoom anchor remains under the same pointer without a rendered frame');
const desktop=m.defaultCamera('work',1440,900),mobile=m.resizedCamera('work',desktop,390,844);
assert.ok(m.defaultCamera('town',390,844).zoom>=.6,'phone town opens close enough to see illustrated characters and frontage detail');
assert.ok(m.defaultCamera('work',1440,900).zoom<=900/1040,'desktop work camera includes the tall cutaway roof');
assert.ok(mobile.zoom>=.5,'phone work opens close enough to read the counter and see the actor; pan/zoom covers the whole room');
assert.deepEqual(m.cameraWorldPoint({x:195,y:422},mobile),{x:0,y:225},'desktop-to-phone resize recentres the workplace');
assert.deepEqual(m.defaultCamera('work',390,844),mobile,'reset uses the same phone fit');
const panned={...desktop,scrollX:desktop.scrollX+240,scrollY:desktop.scrollY-80,zoom:desktop.zoom*1.2};
assert.deepEqual(m.resizedCamera('work',panned,1440,900),panned,'same-size resize preserves user pan and zoom exactly');
const narrowed=m.resizedCamera('work',panned,1300,900);
assert.deepEqual(m.cameraWorldPoint({x:650,y:450},narrowed),m.cameraWorldPoint({x:720,y:450},panned),'resize within one viewport class preserves the panned world centre');

const nav=m.makeNavigation({bounds:{x0:0,y0:0,x1:10,y1:10},roads:[{x0:0,y0:0,x1:10,y1:10}],obstacles:[{x0:4,y0:2,x1:6,y1:8}],step:.5});
const start={x:1,y:5},target={x:9,y:5},path=m.findRoute(nav,start,target);
assert.ok(path.length>1,'route detours around the counter');
assert.deepEqual(path.at(-1),target,'route reaches the requested free point');
let last=start;for(const p of path){assert.ok(m.lineClear(nav,last,p),'no shortcut crosses a footprint');last=p;}
assert.equal(m.lineClear(nav,start,target),false,'direct path through furniture is blocked');
assert.equal(m.lineClear(nav,{x:3.5,y:1.5},{x:6.5,y:8.5}),false,'corner shortcut is blocked');
assert.deepEqual(m.findRoute(nav,start,{x:5,y:5}),[],'cannot walk inside furniture');
assert.deepEqual(m.normalizeMovementInput(Number.NaN,Number.POSITIVE_INFINITY),{x:0,y:0},'nonfinite joystick input does not move the player');
const diagonal=m.normalizeMovementInput(1,1);assert.ok(Math.abs(Math.hypot(diagonal.x,diagonal.y)-1)<1e-10,'joystick diagonal cannot exceed full walking speed');
const free=m.makeNavigation({bounds:{x0:0,y0:0,x1:10,y1:10},roads:[{x0:0,y0:0,x1:10,y1:10}],obstacles:[],step:.25}),feet={x:3,y:3};
const right=m.moveOnGround(free,feet,{x:1,y:0},.05),half=m.moveOnGround(free,feet,{x:.5,y:0},.05);
assert.ok(m.project(right).x>m.project(feet).x,'positive joystick x walks to visible screen right');
assert.ok(Math.abs(m.project(right).y-m.project(feet).y)<1e-10,'screen-right input keeps screen height');
assert.ok(Math.abs(Math.hypot(half.x-feet.x,half.y-feet.y)*2-Math.hypot(right.x-feet.x,right.y-feet.y))<1e-10,'partial joystick input preserves analog walking speed');
const down=m.moveOnGround(free,feet,{x:0,y:1},.05);assert.ok(m.project(down).y>m.project(feet).y,'positive joystick y walks down the screen');
assert.deepEqual(m.moveOnGround(free,feet,{x:0,y:0},.05),feet,'released joystick remains idle');
const wallStart={x:3.85,y:5},wallInput={x:1,y:.5},blocked=m.moveOnGround(nav,wallStart,wallInput,.06);
assert.ok(m.isWalkable(nav,blocked)&&m.lineClear(nav,wallStart,blocked),'analog movement and sliding cannot cross a furniture footprint');
const outside={x:600,y:1000},follow=m.followCamera(mobile,outside,.05);
assert.ok(follow.scrollX>mobile.scrollX&&follow.scrollY>mobile.scrollY,'moving player beyond phone comfort bounds guides the camera');
assert.ok(follow.scrollX<600-mobile.width/2,'camera correction remains gradual');
assert.deepEqual(m.followCamera(mobile,{x:0,y:225},.05),mobile,'comfortable player causes no camera drift');
assert.equal(m.presenceDirection(feet,{x:3.2,y:3},'nw'),'se','positive ground x faces southeast');
assert.equal(m.presenceDirection(feet,{x:3,y:3.2},'nw'),'sw','positive ground y faces southwest');
assert.equal(m.presenceDirection(feet,{x:3,y:2.8},'se'),'ne','negative ground y faces northeast');
assert.equal(m.presenceDirection(feet,{x:2.8,y:3},'se'),'nw','negative ground x faces northwest');
assert.equal(m.presenceDirection(feet,feet,'ne'),'ne','idle presence preserves facing');
const peerSource={pid:'real-123',name:'Bạn An',look:{top:'ao_len',acc:'non_la',tint:{ao_len:'mint'},bank:900},gender:'female',x:5,y:5,direction:'nw',tasks:[{private:true}],money:100,career:'grocery'};
const peers=m.publicTownPlayers([peerSource,{...peerSource},{pid:'invalid',x:NaN,y:1}],nav);
assert.equal(peers.length,1,'only valid unique server peers enter the scene');
assert.deepEqual(Object.keys(peers[0]).sort(),['pid','name','look','gender','x','y','direction'].sort(),'renderer retains only public presence fields');
assert.equal('bank' in peers[0].look,false,'avatar projection drops unrelated fields');
assert.ok(m.isWalkable(nav,peers[0]),'invalid peer coordinates clamp to a real free road point');
assert.equal(peers[0].look.acc,'non_la','public projection keeps real wardrobe accessories');
peers[0].look.tint.ao_len='navy';assert.equal(peerSource.look.tint.ao_len,'mint','renderer does not mutate the network avatar');
assert.deepEqual(m.interpolateRoute(start,path,0),start,'remote interpolation starts at the last rendered position');
assert.deepEqual(m.interpolateRoute(start,path,1),target,'remote interpolation ends exactly at the server position');
for(let i=0;i<=40;i++)assert.ok(m.isWalkable(nav,m.interpolateRoute(start,path,i/40)),'remote movement follows the road route around furniture');

const roads=m.makeNavigation({bounds:{x0:0,y0:0,x1:20,y1:20},roads:[{x0:1,y0:1,x1:19,y1:3},{x0:17,y0:1,x1:19,y1:19}],obstacles:[],step:.5});
const roadPath=m.findRoute(roads,{x:2,y:2},{x:18,y:18});
assert.ok(roadPath.length>=2,'L-shaped road keeps its turn');
last={x:2,y:2};for(const p of roadPath){assert.ok(m.lineClear(roads,last,p));last=p;}
assert.equal(m.lineClear(roads,{x:2,y:2},{x:18,y:18}),false,'no walking over lawns');
assert.equal(m.gestureIsDrag({x:0,y:0},{x:8,y:0}),false,'eight pixel tap tolerance');
assert.equal(m.gestureIsDrag({x:0,y:0},{x:8.1,y:0}),true,'drag must not activate a building');
assert.equal(m.gestureIsDrag({x:0,y:0},{x:6,y:6}),true,'diagonal displacement counts');

const tasks=[{id:'a',status:'completed'},{id:'b',status:'new',npc:'n1'},{id:'c',status:'referred'},{id:'d',status:'cancelled'},{id:'e',status:'in_progress',npc:'n2'}];
assert.deepEqual(m.activeTasks({tasks}).map(t=>t.id),['b','e'],'only server-active work creates people');
assert.deepEqual(tasks.map(t=>t.status),['completed','new','referred','cancelled','in_progress'],'presentation never changes task status');
const catalogue=Array.from({length:41},(_,i)=>({id:'career_'+i,short:'Nghề '+i}));
const lots=m.townBuildings(catalogue);
assert.equal(lots.length,41,'every catalogue career gets a door');
assert.equal(new Set(lots.map(b=>b.id)).size,41,'door IDs stay unique');
assert.deepEqual(lots.map(b=>b.id).sort(),catalogue.map(c=>c.id).sort(),'doors retain stable server IDs');
for(const l of m.townLandmarks())assert.equal(lots.some(b=>b.footprint.x0<l.footprint.x1&&b.footprint.x1>l.footprint.x0&&b.footprint.y0<l.footprint.y1&&b.footprint.y1>l.footprint.y0),false,'water commons is reserved from buildings');
const town=m.townNavigation(lots);
assert.ok(m.activeIslandRegions().length>=9,'the authored districts are open');
assert.deepEqual(m.ISLAND_PLAN.regions.find(r=>r.id==='core').navigationBounds,town.bounds,'core island wraps shared navigation bounds');
for(const building of lots)for(const x of [building.footprint.x0,building.footprint.x1])for(const y of [building.footprint.y0,building.footprint.y1])assert.ok(m.insideIsland({x,y}),`${building.id} has every footprint corner inside the shoreline`);
for(let x=0;x<=43;x+=1)for(let y=0;y<=50;y+=1)assert.ok(m.insideIsland({x,y}),'the complete existing navigation rectangle remains inland');
for(const sea of [{x:-60,y:25},{x:102,y:25},{x:20,y:-25},{x:20,y:75}]){assert.equal(m.insideIsland(sea),false,'ocean lies outside the island coast');assert.equal(m.isWalkable(town,sea),false,'ocean never becomes walkable');}
assert.equal(m.ISLAND_REFERENCE.name,'Đảo Hoàng Sa','map uses the real island name requested by the user');
assert.equal(m.ISLAND_REFERENCE.imageDate,'2014-02-01','the simplified outline records its actual reference date');
const shore=m.ISLAND_PLAN.regions[0].coastline,span=axis=>Math.max(...shore.map(p=>p[axis]))-Math.min(...shore.map(p=>p[axis]));
assert.ok(Math.abs(span('x')/span('y')-1.8)<.01,'shore preserves the observed natural island proportions before isometric projection');
for(const region of m.ISLAND_PLAN.regions.filter(r=>r.status==='reserved')){assert.ok(m.insideIsland(region.anchor),'future districts expand inland');assert.equal(region.navigationBounds,null,'future regions do not silently become playable');}
assert.ok(m.islandCoastline().length>80,'shoreline has smooth curves between data control points');
const islandBounds=m.islandWorldBounds();
for(const [width,height] of [[1440,900],[390,844],[320,640]]){
  const overview=m.islandOverviewCamera(width,height),toScreen=p=>({x:width/2+(p.x-overview.scrollX-width/2)*overview.zoom,y:height/2+(p.y-overview.scrollY-height/2)*overview.zoom});
  for(const x of [islandBounds.x0,islandBounds.x1])for(const y of [islandBounds.y0,islandBounds.y1]){const p=toScreen({x,y});assert.ok(p.x>=17&&p.x<=width-17,'whole-island overview fits horizontally');assert.ok(p.y>=85&&p.y<=height-85,'whole-island overview leaves room for the HUD');}
}
for(const b of lots){assert.ok(m.isWalkable(town,b.door),`door approach for ${b.id} stays on the road`);assert.ok(m.findRoute(town,{x:6.2,y:6.2},b.door).length,`all 41 career doors remain reachable: ${b.id}`);}
const beforeLandmarks=JSON.stringify(town),landmarks=m.townLandmarks();
assert.deepEqual(landmarks.map(l=>l.id).sort(),['outing:boat','outing:fishing','outing:pool'],'the common map has three real activity entrances');
for(const landmark of landmarks){assert.ok(m.isWalkable(town,landmark.approach),`${landmark.id} entrance stays on shared roads`);assert.ok(m.findRoute(town,{x:6.2,y:6.2},landmark.approach).length,`${landmark.id} is reachable from town entry`);}
assert.equal(JSON.stringify(town),beforeLandmarks,'activity landmarks never change server navigation geometry');
for(const zoom of [.03,.044,.24,.5,1,1.6]){
  const view={x0:-720/zoom,y0:-450/zoom,x1:720/zoom,y1:450/zoom},cache=m.groundCacheRegion(view,zoom);
  assert.ok(cache.width*cache.height<=2400000,'ground cache has a bounded pixel allocation at every zoom');
  assert.ok(cache.region.x0<view.x0&&cache.region.y0<view.y0&&cache.region.x1>view.x1&&cache.region.y1>view.y1,'ground cache includes a useful pan margin');
  const origin=m.cameraWorldPoint({x:0,y:0},{width:cache.width,height:cache.height,scrollX:cache.scroll.x,scrollY:cache.scroll.y,zoom:cache.scale});
  assert.ok(Math.abs(origin.x-cache.region.x0)<1e-8&&Math.abs(origin.y-cache.region.y0)<1e-8,'cache camera captures the exact upper-left world point');
  if(zoom===1)assert.ok(cache.scale>=.9,'illustrated ground keeps near-native detail on desktop');
}
assert.equal(m.townBuildingArt({id:'pharmacy'},'home'),'career-pharmacy','pharmacy loads its complete purpose-built exterior');
assert.equal(m.townBuildingArt({id:'mother_baby'},'grocery'),'career-mother_baby','mother and baby career has its own exterior');
assert.equal(m.townBuildingArt({id:'garage'},'home'),'garage','garage keeps its actual workshop identity');
assert.equal(m.townBuildingArt({id:'repair'},'home'),'career-repair','the actual repair career loads its dedicated workshop');
assert.equal(m.townBuildingArt({id:'pho'},'cafe'),'career-pho','pho keeps its own complete food frontage');
assert.equal(m.townBuildingArt({id:'career_unknown'},'home'),'home','unsupported facades use an existing illustrated family');
assert.equal(typeof m.landmarkPlaneGeometry,'function','landmarks expose their actual ground-plane geometry');
for(const landmark of landmarks){const r=landmark.footprint,g=m.landmarkPlaneGeometry(r),corners=[[0,0,{x:r.x0,y:r.y0}],[1,0,{x:r.x1,y:r.y0}],[0,1,{x:r.x0,y:r.y1}],[1,1,{x:r.x1,y:r.y1}]];for(const [u,v,p] of corners){const actual={x:g.x+g.a*u+g.c*v+g.e,y:g.y+g.b*u+g.d*v};const expected=m.project(p);assert.ok(Math.hypot(actual.x-expected.x,actual.y-expected.y)<1e-8,'landmark art stays on the true 2:1 ground plane');}assert.ok(g.height<=g.width/2+1e-7,'portrait boat art cannot become a towering upright sprite');}
const remote=m.findRoute(town,{x:6.2,y:6.2},lots.at(-1).door);
assert.ok(remote.length>0,'the farthest catalogue door stays connected to the entry');
last={x:6.2,y:6.2};for(const p of remote){assert.ok(m.lineClear(town,last,p),'remote route never cuts through a building');last=p;}
let walk={point:{x:6.2,y:6.2},path:remote,arrived:false},walkFrames=0;
while(walk.path.length&&walkFrames++<4000){const previous=walk.point;walk=m.advanceRoute(walk.point,walk.path,.145,'ground',town);assert.ok(m.lineClear(town,previous,walk.point),'door walking stays on the shared town roads, including frames spanning garden corners');}
assert.ok(walk.arrived,'the remote town door walk reaches arrival');
assert.deepEqual(walk.point,lots.at(-1).door,'the town route arrives at the exact door approach');
assert.equal(m.advanceRoute(walk.point,walk.path,.145).arrived,false,'idle frames do not retrigger door arrival');
const savedRoom={theme:'lavender',money:950,day:5,upgrades:['plant','lamp','seat','rug','poster','shelf','workbench','board','workgear_grocery_2'],decor:{plant:{spot:'window'},lamp:{spot:'corner'},seat:{spot:'front'},rug:{spot:'center'},poster:{spot:'wall'}},ops:{property:{tier:'garden'},security:{items:['camera','bell','lock','light'],insurance:true},equipment:{condition:65}},life:{shop_name:'Tiệm đã lưu'}};
const untouched=JSON.stringify(savedRoom),appearance=m.roomAppearance(savedRoom,'grocery');
assert.equal(appearance.theme,'lavender');assert.equal(appearance.wall,'#f3e9fb','saved wall choice controls the wall palette');
assert.equal(appearance.tier,'garden');assert.equal(appearance.gearTier,2,'only installed career gear is depicted');
assert.deepEqual(appearance.security,['bell','camera','light','lock']);
assert.deepEqual(appearance.decor.map(d=>d.id).sort(),['lamp','plant','poster','rug','seat'],'only server-owned decor is projected');
assert.equal(appearance.decor.find(d=>d.id==='plant').footprint,null,'window plants remain on the sill');
assert.equal(appearance.decor.find(d=>d.id==='poster').footprint,null,'wall decor does not block the floor');
assert.equal(appearance.decor.find(d=>d.id==='rug').footprint,null,'rugs remain walkable');
assert.ok(appearance.decor.find(d=>d.id==='seat').footprint,'placed seats block their footprint');
const furnished=m.makeNavigation({bounds:{x0:0,y0:0,x1:10,y1:9},roads:[{x0:0,y0:0,x1:10,y1:9}],obstacles:appearance.decor.flatMap(d=>d.footprint?[d.footprint]:[]),step:.25});
assert.equal(m.isWalkable(furnished,appearance.decor.find(d=>d.id==='seat').at),false,'the walker cannot enter saved floor furniture');
const moved=structuredClone(savedRoom);moved.decor.plant.spot='center';
assert.notDeepEqual(m.roomAppearance(moved,'grocery').decor.find(d=>d.id==='plant').at,appearance.decor.find(d=>d.id==='plant').at,'moving decor changes the mapped anchor');
assert.ok(m.roomAppearance(moved,'grocery').decor.find(d=>d.id==='plant').footprint,'moving a plant from its sill to the floor adds collision');
assert.equal(JSON.stringify(savedRoom),untouched,'render projection never rewrites the saved named spots');
assert.deepEqual(m.roomAppearance({...savedRoom,money:3,day:20,ops:{...savedRoom.ops,finance:{debt:800}}},'grocery'),appearance,'unrendered economic changes do not invalidate scenery');
assert.notDeepEqual(m.roomAppearance({...savedRoom,theme:'sage'},'grocery'),appearance,'wall repaint invalidates scenery');
assert.notDeepEqual(m.roomAppearance({...savedRoom,ops:{...savedRoom.ops,property:{tier:'cozy'}}},'grocery'),appearance,'property changes invalidate scenery');
assert.deepEqual(m.roomAppearance({decor:{seat:{spot:'front'}},upgrades:[]},'grocery').decor,[],'renderer never adds unowned furniture');
assert.match(m.canvasDescription('work','Quầy Bình An'),/Quầy Bình An/,'canvas announces its actual career in work mode');
assert.match(m.canvasDescription('town','Quầy Bình An'),/Khu phố/,'canvas announces town navigation in town mode');
assert.deepEqual(m.effectFrameState({t0:0,end:1},2,true),{animate:false,needsFrames:true,clear:false},'reduced-motion result still advances finite cleanup');
assert.deepEqual(m.effectFrameState({t0:0,end:1},4.3,true),{animate:false,needsFrames:false,clear:true},'reduced-motion finished incidents clear before sleeping');
assert.deepEqual(m.effectFrameState({t0:0,end:null},4,true),{animate:false,needsFrames:false,clear:false},'reduced-motion active incident is a static frame');
const chooseNav=m.makeNavigation({bounds:{x0:0,y0:0,x1:10,y1:10},roads:[{x0:0,y0:0,x1:4,y1:10},{x0:6,y0:0,x1:10,y1:10}],obstacles:[],step:.5});
const choices=[{id:'unreachable',approach:{x:6.2,y:5}},{id:'counter',approach:{x:1,y:5}}];
assert.equal(m.nearestReachableHotspot(chooseNav,{x:3.8,y:5},choices,3)?.id,'counter','E skips a closer station across disconnected ground');
assert.equal(m.nearestReachableHotspot(chooseNav,{x:3.8,y:1},choices,2),null,'E does not activate distant stations');
const foodNav=m.makeNavigation({bounds:{x0:0,y0:0,x1:10,y1:9},roads:[{x0:0,y0:0,x1:10,y1:9}],obstacles:[m.WORK_FOOD_SHELF],step:.25});
assert.equal(m.isWalkable(foodNav,{x:7,y:1}),false,'the family shelf has a real footprint');
assert.equal(m.lineClear(foodNav,{x:6.5,y:1},{x:7.2,y:1}),false,'walking cannot cross the visible family shelf');
assert.deepEqual(m.workWindowAnchors().glass,m.project(m.WORK_WINDOW,64,32,{x:0,y:-m.WORK_WINDOW.z}),'incident glass strike follows the window painter');
for(const tier of ['sunny','garden']){
  const garden=tier==='garden'?[{x0:5.72,y0:8.02,x1:6.18,y1:8.48},{x0:6.42,y0:8.02,x1:6.88,y1:8.48}]:[];
  const tierNav=m.makeNavigation({bounds:{x0:.25,y0:.25,x1:9.75,y1:8.75},roads:[{x0:.25,y0:.25,x1:9.75,y1:8.75}],obstacles:[{x0:3.05,y0:7.85,x1:4.55,y1:8.4},{x0:3.73,y0:7.25,x1:4.27,y1:7.65},...garden,...appearance.decor.flatMap(d=>d.footprint?[d.footprint]:[])],step:.25});
  const approach=m.nearestWalkable(tierNav,{x:3.4,y:7.8});
  assert.ok(approach,`${tier}: paid furniture leaves a usable nearby NPC approach`);
  assert.ok(m.isWalkable(tierNav,approach),`${tier}: NPC approach is genuinely free`);
  assert.ok(Math.hypot(approach.x-3.4,approach.y-7.8)<1,`${tier}: interaction approach stays adjacent to the NPC`);
  assert.ok(m.findRoute(tierNav,{x:6.4,y:6.4},approach).length,`${tier}: NPC remains reachable from the player spawn`);
}
console.log('isometric-world: geometry, routes, analog collision, responsive camera, gestures, saved appearance, incident cleanup and interaction selection passed');
