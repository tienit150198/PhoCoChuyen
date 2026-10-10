import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {createResidentDirectory} from '../public/js/isometric/resident-shops.js';
import * as townUtilities from '../public/js/isometric/town-utilities.js';

const source=readFileSync(new URL('../public/js/iso-guide.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'')
  .replace("import('./v4/live.js')",'Promise.resolve({live:liveSocket})');
function bus(){
  const handlers=new Map();
  const on=(type,fn)=>{if(!handlers.has(type))handlers.set(type,new Set());handlers.get(type).add(fn);return ()=>handlers.get(type)?.delete(fn);};
  return {on,addEventListener:on,removeEventListener:(type,fn)=>handlers.get(type)?.delete(fn),emit:type=>{for(const fn of [...handlers.get(type)||[]])fn({type});},count:type=>handlers.get(type)?.size||0};
}
function harness(late=false,configure=()=>{}){
  const socket=Object.assign(bus(),{flags:{},welcomed:false}),api=Object.assign(bus(),{state:{journey:{story:true},fair:{show:false}},content:{journey:{},catalogue:[]}});
  const events=bus(),doc=bus(),timers=new Map(),frames=new Map();let timer=0,frame=0,rebuilds=0,renders=0,created=0,wakes=0;
  const shape=()=>{created++;return {destroyed:false,clear(){},lineStyle(){},beginPath(){},moveTo(){},lineTo(){},strokePath(){},fillCircle(){return this;},fillStyle(){return this;},fillRect(){return this;},fillEllipse(){return this;},setDepth(){return this;},setOrigin(){return this;},destroy(){this.destroyed=true;}};};
  const markers=[],removedMarkers=[],terrain=shape(),career={id:'career:zpop'},stage={navigation:{bounds:{x0:0,y0:0,x1:40,y1:40},roads:[{x0:0,y0:0,x1:40,y1:40}],obstacles:[]},
    buildings:[{}],staticObjects:[terrain],hits:[{hotspot:career}],add:{graphics:shape,text:shape},requestRender:()=>{renders++;}};
  stage.wayfindingSign=(label,approach)=>{const mount={x:approach.x-3,y:approach.y},sign=Object.assign(shape(),{label,approach,getData:key=>key==='interactionPoint'?mount:undefined});markers.push(sign);stage.staticObjects.push(sign);return sign;};
  stage.removeWayfindingSign=sign=>{removedMarkers.push(sign);sign.destroy();stage.staticObjects=stage.staticObjects.filter(object=>object!==sign);};
  const real={stage,mode:'town',career:'zpop',player:{x:3,y:3,path:[],goal:null},hotspots:[career],project:(x,y)=>({x,y}),onInteract(){},wake(){wakes++;}};
  stage.rebuild=()=>{rebuilds++;for(const x of stage.staticObjects)x.destroy();stage.staticObjects=[terrain];stage.hits=[{hotspot:career}];real.hotspots=[career];};
  const env={api,live:()=>late?null:socket,act:async()=>{},toast:()=>{}};
  configure({real,stage,env});
  const context=vm.createContext({liveSocket:socket,document:doc,esc:String,console,createResidentDirectory,...townUtilities,
    localStorage:{getItem:()=>null,setItem(){}},setInterval:fn=>{timers.set(++timer,fn);return timer;},clearInterval:id=>timers.delete(id),
    addEventListener:events.addEventListener,removeEventListener:events.removeEventListener,requestAnimationFrame:fn=>{frames.set(++frame,fn);return frame;},cancelAnimationFrame:id=>frames.delete(id)});
  vm.runInContext(source+'\nglobalThis.h={attachGuide,goTo,destinations,listHTML,previewDistrict:typeof previewDistrict===\'function\'?previewDistrict:null,setQuery:value=>{query=value;},setFilter:value=>{activeFilter=value;},loadShops:typeof loadShops===\'function\'?loadShops:null,showBody:body=>{dlg={open:true,querySelector:()=>body};}};',context);
  context.h.attachGuide(real,()=>env);
  return {h:context.h,real,stage,env,socket,api,doc,timers,frames,terrain,markers,removedMarkers,get rebuilds(){return rebuilds;},get renders(){return renders;},get created(){return created;},get wakes(){return wakes;},ids:()=>real.hotspots.map(x=>x.id),destinations:()=>context.h.destinations(env).map(x=>x.dest)};
}

test('amenity names use scene-owned supported stands while retaining their original arrival points',()=>{
  const x=harness(false,({real})=>{real.project=(x,y)=>({x:(x-y)*64,y:(x+y)*32});}),bank=x.real.hotspots.find(h=>h.id==='place:bank');
  const marker=x.markers.find(sign=>sign.label==='Ngân hàng');assert.ok(marker,'the guide delegates physical placement to the scene');
  assert.equal(marker.approach,bank.approach,'moving a nameboard must not move its walking destination');
  assert.equal(bank.interactionPoint,marker.getData('interactionPoint'),'E can select the amenity beside its visible stand');
  assert.deepEqual(bank.point,x.real.project(bank.approach.x,bank.approach.y),'hit ordering uses the same projected units as building signs');
  assert.ok(x.stage.hits.some(hit=>hit.hotspot===bank&&hit.object===marker));
  x.api.state.fair.show=true;x.api.emit('state');const fair=x.markers.at(-1);
  x.api.state.fair.show=false;x.api.emit('state');assert.ok(x.removedMarkers.includes(fair),'state changes remove the complete stand from scene visibility tracking');
});

test('changed signs wake a sleeping world, unchanged state keeps it idle',()=>{
  const x=harness(),n=x.wakes;
  x.api.state.fair.show=true;x.api.emit('state');assert.equal(x.wakes,n+1);
  x.api.emit('state');assert.equal(x.wakes,n+1);
  x.api.state.fair.show=false;x.api.emit('state');assert.equal(x.wakes,n+2);
});

test('guide searches existing utilities and opens their real actions without adding map signposts',async()=>{
  const actions=[],x=harness(false,({env,real})=>{
    env.api.state.journey.garage={cars:[]};env.act=async action=>actions.push(action);
    real.go=()=>assert.fail('a menu utility must not invent a walking destination');
  });
  assert.ok(x.destinations().includes('utility:garage'),'garage is discoverable in the town guide');
  assert.equal(x.ids().some(id=>id.includes('garage')),false,'direct utilities do not multiply on-map labels');
  x.h.setQuery('phuong tien');const html=x.h.listHTML(x.env);
  assert.match(html,/data-dest="utility:garage"/);assert.match(html,/>Mở ›<\/span>/);
  await x.h.goTo('utility:garage',x.env);assert.deepEqual(actions,['garage']);
  delete x.api.state.journey.garage;
  await x.h.goTo('utility:garage',x.env);await x.h.goTo('utility:not-an-action',x.env);
  assert.deepEqual(actions,['garage'],'stale or invented utilities cannot dispatch');
  assert.equal(x.destinations().includes('utility:garage'),false);
  assert.equal(x.destinations().includes('utility:bank'),false,'a bank with a real map destination is listed only once');
});

test('guide direct utilities work without changing workplace mode and follow live feature availability',async()=>{
  const actions=[],x=harness(false,({env,real})=>{real.mode='work';env.act=async action=>actions.push(action);});
  await x.h.goTo('utility:historyCourse',x.env);assert.deepEqual(actions,['historyCourse']);
  assert.equal(x.destinations().includes('utility:liveKara'),false);
  x.socket.welcomed=true;x.socket.flags.kara=true;x.socket.emit('welcome');
  assert.ok(x.destinations().includes('utility:liveKara'));
  await x.h.goTo('utility:liveKara',x.env);assert.deepEqual(actions,['historyCourse','liveKara']);
});

test('authored map services follow the same server gates as the compact utility menu',()=>{
  const x=harness(false,({real})=>{
    real.townAmenities=()=>[
      {id:'garage',label:'Gara xe',action:'garage',at:{x:8,y:8}},
      {id:'spa',label:'Spa Sen',action:'spendSpa',at:{x:9,y:8}},
      {id:'travel',label:'Đại lý vé',action:'luxTrip',at:{x:10,y:8}},
    ];
  });
  for(const id of ['garage','spa','travel'])assert.equal(x.destinations().includes('place:'+id),false,`${id} waits for its actual server feature`);
  Object.assign(x.api.state.journey,{garage:{},spend:{},lux:{}});x.api.emit('state');
  for(const id of ['garage','spa','travel'])assert.ok(x.destinations().includes('place:'+id));
  assert.equal(x.destinations().includes('utility:garage'),false,'the now-visible map service replaces its direct-open entry');
});

test('authored park, karaoke and pet-play destinations use their real action data and live gates',()=>{
  const authored=JSON.parse(readFileSync(new URL('../game/town_layout.json',import.meta.url),'utf8')).amenities;
  const actions=[],x=harness(false,({real,stage,env})=>{
    real.townAmenities=()=>authored.filter(p=>['walk','karaoke','bark'].includes(p.id));
    stage.navigation.bounds={x0:-40,y0:-10,x1:90,y1:65};stage.navigation.roads=[stage.navigation.bounds];
    env.act=async(action,data)=>actions.push({action,data});
  });
  x.socket.flags={street:true,kara:true,bark:true};x.socket.welcomed=true;x.socket.emit('welcome');
  for(const id of ['walk','karaoke','bark'])assert.ok(x.ids().includes('place:'+id),id+' is mapped once enabled');
  x.real.onInteract('place:walk');x.real.onInteract('place:karaoke');x.real.onInteract('place:bark');
  assert.equal(actions[0].action,'liveWalk');assert.equal(actions[0].data.place,'congvien','the illustrated park opens the park instead of a remembered street');
  assert.deepEqual(actions.slice(1).map(x=>x.action),['liveKara','liveBark']);
  x.api.state.journey.story=false;x.api.emit('state');x.real.onInteract('place:bark');assert.equal(actions.length,3);
  assert.equal(x.ids().includes('place:bark'),false);assert.ok(x.ids().includes('place:karaoke'));
  x.socket.flags={};x.socket.emit('welcome');x.real.onInteract('place:karaoke');assert.equal(actions.length,3);
  assert.equal(x.ids().includes('place:karaoke'),false);
});

test('amenity availability binds static artwork before signs and removes only interaction bindings',()=>{
  const calls=[],image={destroy:()=>assert.fail('locked artwork must remain visible because its footprint is static')};
  const x=harness(false,({real,stage})=>{
    real.townAmenities=()=>[{id:'fair',label:'Chợ đen',action:'fair',art:'civic-market',at:{x:8,y:8}}];
    stage.addAmenityVisual=(p,h)=>{if(p.art){calls.push(['bind',h.id]);return image;}};
    stage.removeAmenityVisual=(visual,h)=>{assert.equal(visual,image);calls.push(['unbind',h.id]);};
    const original=stage.wayfindingSign;stage.wayfindingSign=(...args)=>{if(args[0]==='Chợ đen')calls.push(['sign','place:fair']);return original(...args);};
  });
  assert.deepEqual(calls,[],'unavailable places do not gain a hit target');
  x.api.state.fair.show=true;x.api.emit('state');
  assert.deepEqual(calls,[['bind','place:fair'],['sign','place:fair']]);
  x.api.emit('state');assert.equal(calls.length,2,'an unchanged state keeps the same hit binding');
  x.api.state.fair.show=false;x.api.emit('state');assert.deepEqual(calls.at(-1),['unbind','place:fair']);
  assert.equal(x.ids().includes('place:fair'),false);
});

test('the black-market route has the same explicit gate as the map destination',()=>{
  assert.equal(townUtilities.townServiceAvailable('fair',{fair:{show:false}}),false);
  assert.equal(townUtilities.townServiceAvailable('fair',{fair:{show:true}}),true);
});

test('illustrated services mount their label on the scene facade and clean it up without moving the arrival point',()=>{
  const removed=[],image={},facade={getData:()=>undefined};let mounted;
  const x=harness(false,({real,stage})=>{
    real.townAmenities=()=>[{id:'fair',label:'Chợ đen',action:'fair',art:'civic-market',at:{x:8,y:8}}];
    stage.addAmenityVisual=p=>p.art?image:null;
    stage.amenitySign=(p,visual)=>{mounted={p,visual};return facade;};
    stage.removeAmenitySign=sign=>removed.push(sign);
  });
  x.api.state.fair.show=true;x.api.emit('state');
  assert.equal(mounted?.visual,image,'the scene mounts the label onto the existing artwork');
  const hotspot=x.real.hotspots.find(h=>h.id==='place:fair');
  assert.equal(hotspot.approach,mounted.p.at,'facade signage preserves the authored walking destination');
  assert.equal(hotspot.interactionPoint,hotspot.approach,'facade labels use the ground approach when no separate stand is provided');
  assert.ok(x.stage.hits.some(hit=>hit.hotspot===hotspot&&hit.object===facade),'the mounted label remains clickable');
  assert.ok(!x.markers.some(sign=>sign.label==='Chợ đen'),'a facade label does not also create a roadside nameboard');
  x.api.state.fair.show=false;x.api.emit('state');assert.deepEqual(removed,[facade]);
  assert.ok(!x.removedMarkers.includes(facade),'facade cleanup belongs to its scene binding');
});

test('a missing facade label falls back to a supported stand with its own interaction point',()=>{
  const x=harness(false,({real,stage})=>{
    real.townAmenities=()=>[{id:'bank',label:'Ngân hàng',action:'bank',art:'office',at:{x:8,y:8}}];
    stage.addAmenityVisual=()=>({});stage.amenitySign=()=>null;
  });
  const hotspot=x.real.hotspots.find(h=>h.id==='place:bank'),stand=x.markers.find(sign=>sign.label==='Ngân hàng');
  assert.ok(stand);assert.equal(hotspot.interactionPoint,stand.getData('interactionPoint'));
});

test('live welcome adds and removes only changed destination signs without terrain rebuilds',()=>{
  const x=harness(),baseObjects=[...x.stage.staticObjects];
  assert.equal(x.ids().includes('place:wedding'),false);
  x.socket.flags={wedding:true,street:true,dating:true};x.socket.welcomed=true;x.socket.emit('welcome');
  for(const id of ['wedding','walk','date']){
    assert.ok(x.ids().includes('place:'+id),id);assert.ok(x.destinations().includes('place:'+id),id);
  }
  assert.equal(x.rebuilds,0);assert.ok(baseObjects.every(o=>!o.destroyed));
  const count=x.created,hits=x.stage.hits.length;x.socket.emit('welcome');
  assert.equal(x.created,count,'unchanged availability does not recreate signs');assert.equal(x.stage.hits.length,hits);
  x.socket.flags={};x.socket.emit('welcome');
  for(const id of ['wedding','walk','date']){assert.equal(x.ids().includes('place:'+id),false);assert.equal(x.destinations().includes('place:'+id),false);}
  assert.equal(x.rebuilds,0);assert.ok(baseObjects.every(o=>!o.destroyed));
  assert.equal(x.stage.hits.some(h=>h.hotspot.id==='place:wedding'),false,'removed signs have no hit targets');
});

test('server state and deferred catalogue refresh signs and an already open guide',()=>{
  const x=harness(),body={innerHTML:''};x.h.showBody(body);
  x.api.state.fair.show=true;x.api.emit('state');
  assert.ok(x.ids().includes('place:fair'));assert.match(body.innerHTML,/Chợ đen/);
  x.api.content.journey.quay={};x.doc.emit('mnl:lazy');assert.ok(x.ids().includes('place:quay'));
  x.api.state.fair.show=false;x.api.emit('state');assert.equal(x.ids().includes('place:fair'),false);assert.doesNotMatch(body.innerHTML,/Chợ đen/);
  assert.equal(x.rebuilds,0);assert.equal(x.terrain.destroyed,false);
});

test('work-mode guide uses current flags and returning to town creates the matching signs once',()=>{
  const x=harness();x.real.mode='work';x.stage.rebuild();
  x.socket.flags={wedding:true};x.socket.welcomed=true;x.socket.emit('welcome');
  assert.ok(x.destinations().includes('place:wedding'));
  assert.equal(x.ids().includes('place:wedding'),false,'work mode never receives town markers');
  x.real.mode='town';x.stage.rebuild();
  assert.equal(x.ids().filter(id=>id==='place:wedding').length,1);
});

test('reattaching a guide replaces its subscriptions and signs',()=>{
  const x=harness();x.h.attachGuide(x.real,()=>x.env);
  assert.equal(x.socket.count('welcome'),1);assert.equal(x.api.count('state'),1);assert.equal(x.timers.size,1);
  assert.equal(x.ids().filter(id=>id==='place:bank').length,1);
  x.stage.rebuild();assert.equal(x.rebuilds,1);
});

test('a welcome received before the app lazy live cache is ready still refreshes the guide',async()=>{
  const x=harness(true);
  x.socket.flags={wedding:true};x.socket.welcomed=true;x.socket.emit('welcome');
  await Promise.resolve();
  assert.ok(x.ids().includes('place:wedding'));
  x.socket.flags={};x.socket.emit('welcome');assert.equal(x.ids().includes('place:wedding'),false);
  assert.equal(x.rebuilds,0);
});

test('authored civic hotspots are reused and their destination metadata is discoverable',()=>{
  const x=harness(false,({real})=>{
    real.townAmenities=()=>[{id:'library',label:'Thư viện ven hồ',action:'library',icon:'📚',at:{x:9,y:9}},{id:'bank',label:'Ngân hàng',action:'bank',icon:'🏦',at:{x:8,y:8}}];
    real.hotspots.push({id:'place:library',approach:{x:9,y:9}},{id:'place:bank',approach:{x:8,y:8}});
  });
  assert.equal(x.ids().filter(id=>id==='place:bank').length,1,'world-owned amenities must not get a second sign');
  assert.ok(x.destinations().includes('place:library'));
  let action;x.env.act=async name=>{action=name;};x.real.onInteract('place:library');assert.equal(action,'library');
});

test('district cards search their landmarks, filter careers and announce arrival without refocusing',()=>{
  const districts=[{id:'park',name:'Vườn ven hồ',icon:'🌳',description:'Bóng mát và lối đi dạo',features:['Ao câu cá','Sân chơi'],color:'#567e55',at:{x:8,y:8}}];
  let focus='',notice='';
  const x=harness(false,({real,env})=>{real.townDistricts=()=>districts;real.focusDistrict=id=>{focus=id;};env.toast=msg=>{notice=msg;};env.api.content.catalogue=[{id:'milk_tea',name:'Trà sữa',place:'Tiệm Trà'}];});
  assert.ok(x.destinations().includes('district:park'));
  x.h.setQuery('san choi');assert.match(x.h.listHTML(x.env),/Vườn ven hồ/);assert.doesNotMatch(x.h.listHTML(x.env),/Tiệm Trà/);
  x.h.setQuery('');x.h.setFilter('careers');assert.doesNotMatch(x.h.listHTML(x.env),/Vườn ven hồ/);assert.match(x.h.listHTML(x.env),/Tiệm Trà/);
  x.real.onInteract('district:park');assert.equal(focus,'');assert.match(notice,/Vườn ven hồ/);
});

test('shop loading is lazy, maps at most eight public places, and logout removes them without another request',async()=>{
  let calls=0,mapped=[],visited;
  const x=harness(false,({real,env})=>{
    real.setResidentShops=rows=>{mapped=rows;};env.api.account={username:'an'};
    env.api.json=async()=>{calls++;return {places:Array.from({length:40},(_,i)=>({id:'wp_'+i,name:'Tiệm '+i,kind:'career',target:'milk_tea',visibility:'public',owner:{name:'Chủ '+i}}))};};
    env.act=async(action,data)=>{visited={action,data};};
  });
  x.api.emit('state');x.socket.emit('welcome');assert.equal(calls,0);
  assert.equal(typeof x.h.loadShops,'function');await x.h.loadShops(x.env);assert.equal(calls,1);assert.equal(mapped.length,8);
  assert.equal(x.destinations().filter(id=>id.startsWith('resident:')).length,24);
  x.real.onInteract('resident:wp_0');assert.equal(visited.action,'workVisit');assert.equal(visited.data.place,'wp_0');
  x.api.account=null;x.api.emit('state');assert.equal(mapped.length,0);assert.equal(calls,1);
  visited=null;x.real.onInteract('resident:wp_0');assert.equal(visited,null,'cached markers never bypass a logout');
});

test('walking reaches district and resident doors, preserves career interactions, and excess shops visit directly',async()=>{
  const reached=[],actions=[],focus=[];
  const x=harness(false,({real,env})=>{
    real.townDistricts=()=>[{id:'park',name:'Công viên',description:'Ao câu cá',features:[]}];
    real.focusDistrict=id=>focus.push(id);
    real.hotspots.push({id:'district:park',label:'Công viên'},{id:'resident:wp_0',label:'Tiệm 0'});
    real.go=(id,done)=>{reached.push(id);done();};real.onInteract=id=>actions.push(id);
    env.api.account={username:'an'};env.api.json=async()=>({places:Array.from({length:12},(_,i)=>({id:'wp_'+i,name:'Tiệm '+i,kind:'quay',target:'stall_'+i,visibility:'public',owner:{name:'An'}}))});
    env.act=async(action,data)=>actions.push([action,data?.place]);
  });
  await x.h.loadShops(x.env);
  await x.h.goTo('district:park',x.env);await x.h.goTo('resident:wp_0',x.env);
  await x.h.goTo('resident:wp_10',x.env);await x.h.goTo('career:zpop',x.env);
  assert.deepEqual(reached,['district:park','resident:wp_0','career:zpop']);
  assert.deepEqual(focus,[],'walking arrival does not count as an explicit camera action');
  assert.deepEqual(actions,[['workVisit','wp_0'],['workVisit','wp_10'],'career:zpop']);
});

test('district preview changes only camera focus and has a separate walking button',()=>{
  const focuses=[],actions=[];
  const x=harness(false,({real,env})=>{
    real.townDistricts=()=>[{id:'park',name:'Công viên',description:'Ao câu cá',features:[]}];
    real.focusDistrict=id=>{focuses.push(id);return true;};real.go=()=>assert.fail('preview must not start walking');
    real.player.path=[{x:5,y:5}];real.player.goal={x:6,y:6};env.act=async action=>actions.push(action);
  });
  const player=JSON.stringify(x.real.player);
  assert.equal(typeof x.h.previewDistrict,'function');x.h.previewDistrict('park',x.env);
  assert.deepEqual(focuses,['park']);assert.deepEqual(actions,[]);assert.equal(JSON.stringify(x.real.player),player);
  const html=x.h.listHTML(x.env);
  assert.match(html,/<article class="iso-guide-row iso-guide-district"/);
  assert.match(html,/data-guide-preview="park"[^>]*>Xem khu<\/button>/);
  assert.match(html,/data-dest="district:park"[^>]*>Đi tới/);
  x.h.previewDistrict('missing',x.env);assert.deepEqual(focuses,['park'],'unknown districts cannot move the camera');
});

test('district arrival respects browsing started mid-route and explicit preview still focuses',async()=>{
  const focuses=[],notices=[];let finish;
  const x=harness(false,({real,env})=>{
    real.cameraMode='follow';real.townDistricts=()=>[{id:'park',name:'Công viên Bờ Sen',description:'Ao câu cá',features:[]}];
    real.hotspots.push({id:'district:park',label:'Công viên Bờ Sen'});
    real.focusDistrict=id=>{focuses.push(id);real.cameraMode='browse';return true;};env.toast=msg=>notices.push(msg);
    real.go=(id,done)=>{real.player.path=[{x:8,y:8}];real.pending=done;finish=()=>{real.player.path=[];real.pending=null;done();};};
  });
  await x.h.goTo('district:park',x.env);assert.equal(x.frames.size,1,'the guide draws an active route');
  x.real.cameraMode='browse';finish();
  assert.deepEqual(focuses,[],'arrival must not overwrite the view chosen while walking');
  assert.equal(x.real.cameraMode,'browse','arrival keeps the manual camera mode');
  assert.equal(x.frames.size,0,'arrival still removes its route animation');assert.match(notices.at(-1),/Công viên Bờ Sen/,'arrival still announces the destination');
  x.h.previewDistrict('park',x.env);assert.deepEqual(focuses,['park'],'explicit Xem khu still works while browsing');assert.equal(x.real.cameraMode,'browse');
  x.real.cameraMode='follow';await x.h.goTo('district:park',x.env);finish();
  assert.deepEqual(focuses,['park'],'normal arrival also leaves focus to an explicit camera action');
  assert.equal(x.real.cameraMode,'follow','normal arrival must not silently disable following');
});
