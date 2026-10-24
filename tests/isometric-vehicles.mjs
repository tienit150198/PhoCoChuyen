// 🚗 Vehicles in the island town (owner 16/10): public/js/isometric/vehicle-art.js (what a save shows, peers' `r`,
// the stamps, the berths and stands), the live presence carrying `r` (public/js/isometric-town.js) and the Phaser scene
// (client/isometric/phaser-world.ts) riding, parking and flying them within the phone budget: a stamp per look, vehicle,
// side and wheel frame (never per frame), static parked images rebuilt only when the list changes, riding at most 1.8×
// the walk and under the live service's movement budget (live/town.py SPEED).
import assert from 'node:assert/strict';
import {withPairs,cleanPairs,withWings,cleanWing} from '../public/js/v4/look.js';   // 🤝 the walkers' pairs, 🪽 their wings (isometric-town.js)
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import vm from 'node:vm';
import {build} from 'esbuild';

const store=new Map(),noop=()=>{};
globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
const ctx2d=()=>new Proxy({measureText:s=>({width:String(s).length*6}),getTransform:()=>({a:1}),createLinearGradient:()=>({addColorStop:noop}),createRadialGradient:()=>({addColorStop:noop})},
  {get:(t,k)=>k in t?t[k]:noop,set:(t,k,v)=>{t[k]=v;return true;}});
globalThis.document={createElement:()=>({width:0,height:0,getContext:ctx2d})};
globalThis.Path2D=class{constructor(){return new Proxy({},{get:()=>noop});}};
const VA=await import('../public/js/isometric/vehicle-art.js');

const content={journey:{garage:{
  vehicles:[['xe_ga','bike','🛵','xanh'],['o_to_suv','car','🚙','bac'],['lx_sieu_xe_01','car','🏎️','vang_kim',{limited:true,base:'sieu_xe'}],['du_thuyen','boat','🛥️','navy'],
    ['sieu_du_thuyen','boat','🛳️','navy'],['phan_luc','plane','✈️','vang'],['may_bay_nho','plane','🛩️','vang']].map(([id,group,emoji,paint,x])=>({id,group,emoji,paint,name:'Tên '+id,...x})),
  paints:[{id:'xanh',hex:'#4f8fd1'},{id:'bac',hex:'#b8bec6'},{id:'navy',hex:'#2f4a7a'},{id:'vang',hex:'#e8c547'},{id:'vang_kim',hex:'#d4a838',limited:true}]}}};
const car=(id,color,extra={})=>({id,color,plate:'',...extra});
const save=(cars,ride,extra={})=>({journey:{story:true,garage:{cars,ride,plates:[],...extra}}});

test('what a save shows: the ride in the streets, yachts and planes parked, the plate in gold',()=>{
  store.clear();
  const s=save([car('o_to_suv','bac',{uq:{t:'29A-888.88',pct:7}}),car('du_thuyen','navy',{uq:{t:'NGỌC MÂY'}}),car('phan_luc','vang',{plate:'MÂY'}),car('xe_ga','xanh')],'o_to_suv');
  const v=VA.townVehicles(s,content);
  assert.equal(v.ride.id,'o_to_suv');assert.equal(v.ride.group,'car');assert.equal(v.ride.plate,'29A-888.88');assert.equal(v.ride.uq,true);
  assert.deepEqual(v.wire,{v:'o_to_suv',c:'bac',p:'29A-888.88'});
  assert.deepEqual(v.fleet.map(f=>[f.id,f.group,f.plate,f.uq]),[['du_thuyen','boat','NGỌC MÂY',true],['phan_luc','plane','MÂY',false]]);
  assert.equal(v.fly,'');
  // the toggle set to walking (ride.js): a yacht "đang đi" travels instead, with its name plate
  store.set('mnl.ride','0');
  const w=VA.townVehicles(save([car('du_thuyen','navy',{uq:{t:'NGỌC MÂY'}}),car('xe_ga','xanh')],'du_thuyen'),content);
  assert.equal(w.ride,null);assert.deepEqual(w.wire,{v:'du_thuyen',c:'navy',p:'NGỌC MÂY'});
  store.clear();
  // a broken one stays home; the plane taken out today flies over
  const f=VA.townVehicles(save([car('phan_luc','vang'),car('may_bay_nho','vang',{broken:40})],null,{tripped:true,trip_id:'phan_luc'}),content);
  assert.deepEqual(f.fleet.map(x=>x.id),['phan_luc']);assert.equal(f.fly,'phan_luc');
  for(const odd of [{},{journey:null},save(null),save([car('tau_ngam','x')]),{journey:{story:false,garage:{cars:[car('xe_ga','xanh')]}}}])
    assert.deepEqual(VA.townVehicles(odd,content),{ride:null,fleet:[],fly:'',wire:null});
  assert.equal(VA.townVehicles(s,null).ride,null,'an older server without the catalogue: nothing');
});

test('peers: a road vehicle under them, a yacht or plane parked, a copied plate never trusted beyond the service',()=>{
  assert.equal(VA.peerVehicle({v:'xe_ga',c:'xanh',p:'30K-666.66'},content).uq,true);
  assert.equal(VA.peerVehicle({v:'xe_ga',c:'xanh'},content).group,'bike');
  assert.deepEqual(VA.peerVehicle({v:'phan_luc',c:'vang',p:'VN-A888'},content),{id:'phan_luc',group:'plane',name:'Tên phan_luc',emoji:'✈️',hex:'#e8c547',plate:'VN-A888',uq:true});
  for(const odd of [null,'xe_ga',{v:5},{v:'tau_ngam'},{v:'xe_ga',p:'x'.repeat(30)}])
    assert.ok(odd&&odd.v==='xe_ga'?VA.peerVehicle(odd,content).plate==='':VA.peerVehicle(odd,content)===null);
  const mine=Array.from({length:6},(_,i)=>({id:'du_thuyen',group:'boat',hex:'#000000',plate:'',uq:false,i}));
  const peers=Array.from({length:30},(_,i)=>({pid:'p'+i,name:'Bạn '+i,r:{v:i%2?'du_thuyen':'phan_luc',c:'navy'}}));
  const list=VA.parkedFleet(mine,peers,content);
  assert.equal(list.filter(f=>f.group==='boat').length,VA.BERTHS.length,'yachts: one per berth');
  assert.equal(list.filter(f=>f.group==='plane').length,VA.STANDS.length,'planes: one per stand');
  assert.deepEqual(list.filter(f=>f.group==='boat').slice(0,6).map(f=>f.owner),Array(6).fill(undefined),'the player\'s own first');
  const slots=new Set(list.map(f=>JSON.stringify(VA.slotOf(f))));assert.equal(slots.size,list.length,'never two on one spot');
  for(const p of [...VA.BERTHS])assert.ok(p.x>=80&&p.x<=87&&p.y>=30&&p.y<=43.5,'in the harbour basin, clear of the jetty');
  for(const p of [...VA.STANDS])assert.ok(p.x>=57&&p.x<=79&&p.y>=20.6&&p.y<=23.7,'on the airfield');
});

test('stamps draw without throwing; speed and facing',()=>{
  const look={hair:'toc_bob',top:'ao_hoodie'};
  for(const kind of ['scooter','cub','mini','suv','convertible','super']){
    const cv=VA.rideStamp({look,gender:'female',v:{id:'x',kind,hex:'#d4a838',plate:'29A-888.88',uq:true},face:1,frame:2});
    assert.ok(cv.width>100&&cv.height>100,kind);
  }
  for(const f of [{group:'boat',hex:'#1b2a52',plate:'HOÀNG HÔN VÀNG',uq:true},{group:'plane',hex:'#dfe3e6',plate:'VN-A888',uq:true},{group:'plane',hex:'bad',plate:''}]){
    const cv=VA.stampOf(f);assert.ok(cv.width>0&&cv.height>0);
    assert.ok(VA.stampOrigin(f).y>.8&&VA.stampOrigin(f).y<1);
  }
  assert.ok(VA.planeStamp({hex:'#000000'},1,true).width>0);
  assert.equal(VA.rideSpeed(null),1);
  for(const kind of ['scooter','cub','mini','suv','convertible','super'])assert.ok(VA.rideSpeed({kind})>1&&VA.rideSpeed({kind})<=1.8,kind);
  assert.deepEqual(['se','ne','sw','nw'].map(VA.faceOf),[1,1,-1,-1]);
  assert.notEqual(VA.stampKey({group:'boat',id:'a',hex:'#000000',uq:true,plate:'A B'}),VA.stampKey({group:'boat',id:'a',hex:'#000000',uq:true,plate:'A C'}));
});

test('the live presence carries `r` on joining and when it changes, and reads peers\' `r`',()=>{
  const source=readFileSync(new URL('../public/js/isometric-town.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
  let now=1000,id=0,ride={v:'xe_ga',c:'xanh',p:'30K-666.66'};const timers=new Map(),listeners=new Map(),sent=[],drawn=[];
  const live={state:'open',flags:{town:true},on(t,fn){listeners.set(t,fn);return()=>listeners.delete(t);},send(f){sent.push(f);return true;}};
  const target={addEventListener(){},removeEventListener(){}};
  const world={mode:'town',x:6,getPresence(){return {x:this.x,y:6,direction:'se'};},getRide(){return ride;},setRemotePlayers(p){drawn.push(p);}};
  const env={world,api:{live:{url:'/live'},state:{journey:{gender:'female'}}}};
  const leisure={current:null,updatePeers(){},observeLocal(){return()=>{};}};
  const context=vm.createContext({sitePresence:{active:false,subscribe:()=>()=>{}},live,leisurePresence:leisure,publicActivity:()=>null,lookOf:()=>({top:'ao'}),withPairs,cleanPairs,withWings,cleanWing,withBang:x=>x,tagLine:()=>'',tagInk:()=>'',exTownTag:()=>null,badge:()=>'',console,document:{visibilityState:'visible',...target},window:target,
    setInterval:fn=>{timers.set(++id,fn);return id;},clearInterval:i=>timers.delete(i),Date:{now:()=>now},JSON,Object,Array,Map,Number,String,Boolean,Math});
  vm.runInContext(source+'\nglobalThis.factory=createTownPresence;',context);
  const bridge=context.factory(()=>env,{transport:live,document:{visibilityState:'visible',...target},events:target,now:()=>now,leisure,status(){}});
  bridge.start();
  const tick=(ms=300)=>{now+=ms;for(const fn of [...timers.values()])fn();};
  const plain=x=>JSON.parse(JSON.stringify(x));   // frames built inside the vm realm
  assert.equal(sent[0].t,'town_in');assert.deepEqual(plain(sent[0].r),ride);
  listeners.get('town_room')({map:'iso-town-v1',room:'r',me:'me',cid:sent[0].cid,people:[{pid:'p',name:'Lan',x:6,y:8,r:{v:'phan_luc',c:'vang',p:'VN-A888'}}]});
  assert.deepEqual(plain(drawn.at(-1)[0].r),{v:'phan_luc',c:'vang',p:'VN-A888'});
  world.x=6.2;tick();
  assert.equal(sent.at(-1).t,'town_mv');assert.equal('r' in sent.at(-1),false,'unchanged: not repeated');
  ride=null;tick();
  assert.equal(sent.at(-1).t,'town_mv');assert.equal(sent.at(-1).r,null,'on foot now: said once');
  const n=sent.length;tick();assert.equal(sent.length,n,'nothing moved, nothing changed: nothing sent');
  listeners.get('town')({room:'r',ev:[{k:'mv',pid:'p',x:6,y:8.2,direction:'se',r:null}]});
  assert.equal('r' in drawn.at(-1)[0],false);
  listeners.get('town')({room:'r',ev:[{k:'mv',pid:'p',x:6,y:8.3,direction:'se',r:{v:'xe_ga',c:'xanh'}}]});
  assert.deepEqual(plain(drawn.at(-1)[0].r),{v:'xe_ga',c:'xanh'});
  bridge.stop();
});

/* ---- the scene: the production DioramaScene with Phaser's display objects and the art module instrumented ---- */
const counters={rideStamps:0,parkedStamps:0,planeStamps:0,images:0,destroyed:0,textureSwaps:0};
class Image {
  visible=true;x=NaN;y=NaN;depth=NaN;scale=1;
  constructor(key){this.key=key;counters.images++;}
  setOrigin(x,y){this.origin=[x,y];return this;} setScale(s){this.scale=s;return this;} setRotation(){return this;} setAlpha(){return this;}
  setPosition(x,y){Object.assign(this,{x,y});return this;} setDepth(depth){this.depth=depth;return this;}
  setX(x){this.x=x;return this;} setY(y){this.y=y;return this;} setData(k,v){(this.data??={})[k]=v;return this;} getData(k){return this.data?.[k];}
  setVisible(visible){this.visible=visible;return this;} setTexture(key){counters.textureSwaps++;this.key=key;return this;}
  setText(text){this.text=text;return this;} getBounds(){return {left:this.x-10,top:this.y-10,right:this.x+10,bottom:this.y+10,width:20,height:20};}
  destroy(){counters.destroyed++;this.destroyed=true;}
}
globalThis.__vehicleSceneTest={Phaser:{Scene:class {},Textures:{FilterMode:{LINEAR:1}},GameObjects:{Image,Container:class {},Text:class {}}},
  art:{RES:2,RIDE_ORIGIN:{x:.5,y:.9},faceOf:d=>d==='se'||d==='ne'?1:-1,rideSpeed:v=>v?1.8:1,
    townVehicles:(state)=>state?.vehicles||{ride:null,fleet:[],fly:'',wire:null},
    peerVehicle:r=>r?.v==='xe_ga'?{id:'xe_ga',kind:'scooter',group:'bike',hex:'#4f8fd1',plate:r.p||'',uq:!!r.p}:r?.v==='du_thuyen'?{id:'du_thuyen',group:'boat',hex:'#2f4a7a',plate:'',uq:false}:null,
    rideStamp:()=>{counters.rideStamps++;return {width:300,height:320};},
    parkedFleet:(mine,peers,content)=>[...(mine||[]),...(peers||[]).filter(p=>p.r?.v==='du_thuyen').map(p=>({id:'du_thuyen',group:'boat',hex:'#2f4a7a',plate:'',owner:p.name}))].slice(0,6).map((f,slot)=>({...f,slot})),
    slotOf:f=>({x:83.6,y:32+f.slot*3}),stampKey:f=>`veh-${f.group}-${f.id}-${f.slot}`,stampOf:()=>{counters.parkedStamps++;return {width:200,height:120};},
    stampOrigin:()=>({x:.5,y:.85}),planeStamp:()=>{counters.planeStamps++;return {width:250,height:110};}}};
globalThis.window={};globalThis.sessionStorage={getItem:()=>null,setItem(){}};
const out=await build({stdin:{contents:readFileSync('client/isometric/phaser-world.ts','utf8')+'\nexport {DioramaScene};',loader:'ts',resolveDir:resolve('client/isometric')},bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent',plugins:[{
  name:'vehicle-scene',setup(b){
    b.onResolve({filter:/^(phaser|\/js\/)/},args=>({path:args.path,namespace:'vehicle-test'}));
    b.onLoad({filter:/.*/,namespace:'vehicle-test'},args=>({contents:args.path==='phaser'?'export default globalThis.__vehicleSceneTest.Phaser;':
      args.path.includes('/vehicle-art.js')?Object.keys(globalThis.__vehicleSceneTest.art).map(k=>`export const ${k}=globalThis.__vehicleSceneTest.art.${k};`).join('\n'):
      args.path.includes('/look.js')?'export const figure=s=>({L:{top:"ao"},g:"female"}),defaultLook=()=>({});':
      args.path.includes('/character-art.js')?'export const getCharacterStamp=()=>({canvas:{width:120,height:160}}),preloadIllustratedCharacters=()=>{};':
      'export const kindOf=()=>"home",wordsFor=()=>({});',loader:'js'}));
  }}]});
const {DioramaScene,PhaserWorld}=await import('data:text/javascript;base64,'+Buffer.from(out.outputFiles[0].text).toString('base64'));
const reset=()=>{for(const k of Object.keys(counters))counters[k]=0;};
function fixture({peers=0,vehicles=null}={}){
  const owner={mode:'town',reduced:false,time:1,walkDistance:0,direction:'se',player:{x:6,y:6,path:[],goal:null},state:{journey:{life_day:3}},game:{},
    vehicles:vehicles||{ride:{id:'xe_ga',kind:'scooter',group:'bike',hex:'#4f8fd1',plate:'30K-666.66',uq:true},fleet:[],fly:'',wire:null},
    remotePlayers:Array.from({length:peers},(_,i)=>({pid:'peer-'+i,name:'Bạn '+i,look:{top:'ao'},gender:'male',x:6+i*.02,y:6,direction:'se',r:{v:'xe_ga',c:'xanh'}}))};
  const textures=new Map(),texture=key=>{const t={add(){return t;},setFilter(){return t;}};textures.set(key,t);return t;};
  const scene=new DioramaScene(owner);
  Object.assign(scene,{sys:{isActive:()=>true},cameras:{main:{scrollX:-390,scrollY:70,width:780,height:630,zoom:1,worldView:{x:-390,y:70,width:780,height:630,right:390}}},
    navigation:{bounds:{x0:-100,y0:-100,x1:100,y1:100},roads:[{x0:-100,y0:-100,x1:100,y1:100}],obstacles:[],step:.5,clearance:0},
    add:{image:(_x,_y,key)=>new Image(key).setPosition(_x,_y),text:(_x,_y,text)=>new Image().setText(text)},
    tweens:{add:o=>{scene.lastTween=o;},getTweens:()=>[]},
    textures:{exists:key=>textures.has(key),remove:key=>textures.delete(key),create:key=>texture(key),addCanvas:key=>texture(key)}});
  return {scene,owner,textures};
}

test('riding: one stamp per side and wheel frame, never per frame; scaled from the texture resolution',()=>{
  const {scene,owner}=fixture();reset();
  scene.positionPlayer(false);
  assert.equal(counters.rideStamps,1);assert.equal(scene.actor.scale,1/2);assert.deepEqual(scene.actor.origin,[.5,.9]);
  for(let i=0;i<600;i++){owner.walkDistance+=3;owner.direction=i%200<100?'se':'sw';scene.positionPlayer(true);}
  assert.ok(counters.rideStamps<=6,`at most 2 sides × 3 wheel frames, got ${counters.rideStamps}`);
  assert.equal(scene.actor.scale,1/2);
  owner.vehicles={ride:null,fleet:[],fly:'',wire:null};scene.positionPlayer(false);   // off the vehicle: the walking character again
  assert.deepEqual(scene.actor.origin,[.5,1]);
});

test('29 riding peers: stamps once per peer pose, nothing per frame when they stand still',()=>{
  const {scene,owner}=fixture({peers:29});scene.syncRemotePlayers();reset();
  for(let i=0;i<120;i++)scene.stepRemotePlayers(1+i/60);
  assert.equal(counters.rideStamps,0,'still riders: no new stamps');assert.equal(counters.textureSwaps,0);
  const actor=scene.remoteActors.get('peer-0');assert.equal(actor.ride.id,'xe_ga');assert.equal(actor.image.scale,1/2);
  owner.remotePlayers=owner.remotePlayers.map(p=>({...p,r:undefined}));scene.syncRemotePlayers();scene.stepRemotePlayers(3);
  assert.equal(actor.ride,null);assert.equal(actor.image.scale,.65,'on foot: the character again');
});

test('parked yachts and planes: static images, rebuilt only when the list changes, a fly-over once',()=>{
  const fleet=[{id:'du_thuyen',group:'boat',hex:'#2f4a7a',plate:'NGỌC MÂY',uq:true},{id:'phan_luc',group:'plane',hex:'#e8c547',plate:'VN-A888',uq:true}];
  const {scene,owner}=fixture({vehicles:{ride:null,fleet,fly:'phan_luc',wire:null}});
  scene.staticObjects=[];scene.reindexStatics=()=>{};reset();
  scene.refreshVehicles();
  assert.equal(scene.parked.length,2);assert.equal(counters.parkedStamps,2);assert.equal(counters.planeStamps,1,'the plane taken out today flies over');
  assert.ok(scene.lastTween&&scene.lastTween.duration>=5000);
  for(let i=0;i<50;i++)scene.refreshVehicles();
  assert.equal(counters.parkedStamps,2);assert.equal(counters.destroyed,0);assert.equal(counters.planeStamps,1,'once per day');
  owner.remotePlayers=[{pid:'p',name:'Lan',x:6,y:6,direction:'se',look:{},gender:'female',r:{v:'du_thuyen',c:'navy'}}];
  scene.syncRemotePlayers();
  assert.equal(scene.parked.length,3,'a peer\'s yacht moors too');
  owner.mode='work';scene.refreshVehicles();assert.equal(scene.parked.length,0,'inside a workplace: none');
});

test('riding speed: builds up, then at most 1.8× the walk and within live/town.py SPEED',()=>{
  const speed=Number(/^SPEED = ([\d.]+)/m.exec(readFileSync('live/town.py','utf8'))[1]);
  globalThis.document={hidden:false,querySelector:()=>null};
  const run=ride=>{
    const w=Object.create(PhaserWorld.prototype);
    Object.assign(w,{destroyed:false,visible:true,_paused:false,keys:new Set(),pointers:new Map(),movementInput:{x:0,y:1},player:{x:0,y:0,path:[],goal:null},mode:'town',reduced:false,direction:'se',walkDistance:0,rideBoost:0,rideParked:false,
      vehicles:{ride,fleet:[],fly:'',wire:null},engine:{loop:{sleep(){},wake(){}}}});
    w.stage={navigation:{bounds:{x0:-100,y0:-100,x1:100,y1:100},roads:[{x0:-100,y0:-100,x1:100,y1:100}],obstacles:[],step:.5,clearance:0},cameraMode:'browse',cameras:{main:{scrollX:0,scrollY:0,zoom:1,setScroll(){}}},
      positionPlayer(){},bobParked(){},updateOcclusion:()=>false,stepRemotePlayers:()=>false,hasEffects:()=>false,renderRequested:false,settle:()=>true,load:{isLoading:()=>false}};
    for(let i=0;i<60;i++)w.step(1/60);   // owner 17/10 "cảm giác lái": the ride speeds up over RIDE_RAMP (0.7 s) first
    const from=Math.hypot(w.player.x,w.player.y);
    for(let i=0;i<60;i++)w.step(1/60);   // then one second at its top speed
    return Math.hypot(w.player.x,w.player.y)-from;
  };
  const walk=run(null),rideD=run({kind:'super'});
  assert.ok(Math.abs(rideD/walk-1.8)<.01,`${rideD/walk}`);
  assert.ok(rideD<speed,`riding ${rideD.toFixed(2)} grid/s, the service allows ${speed}`);
});
