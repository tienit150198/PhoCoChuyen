// 🪽 Bay (owner 24/10 "cánh cho to hơn, và bay được k nhỉ, sẽ có tăng tốc độ như xe ấy, nếu sử dụng cánh thì k lái xe
// được"): the wings are larger (each tier a little more, still inside their cached boxes), a player wearing wings flies
// on the walk maps faster by the tier (a bicycle's pace at D, a supercar's at Huyền thoại), and never rides while
// flying: the toggles switch one off for the other with a toast (public/js/v4/ride.js). tests/test_wing_fly.py: the
// live service's side.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const store=new Map();
globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
const noop=()=>{};
const ctx2d=()=>new Proxy({measureText:s=>({width:String(s).length*6}),getTransform:()=>({a:1}),createLinearGradient:()=>({addColorStop:noop}),createRadialGradient:()=>({addColorStop:noop})},
  {get:(t,k)=>k in t?t[k]:noop,set:(t,k,v)=>{t[k]=v;return true;}});
globalThis.document={createElement:()=>({width:0,height:0,getContext:ctx2d})};
globalThis.Path2D??=class{constructor(){return new Proxy({},{get:()=>noop});}};

const R=await import('../public/js/v4/ride.js');
const WA=await import('../public/js/v4/wings-art.js');
const {SVG}=await import('../public/js/v4/look.js');
const CA=await import('../public/js/isometric/character-art.js');
const VA=await import('../public/js/isometric/vehicle-art.js');
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');

const content={journey:{garage:{
  vehicles:[['xe_ga','bike','🛵','xanh'],['o_to_suv','car','🚙','bac']].map(([id,group,emoji,paint])=>({id,group,emoji,paint,name:id})),
  paints:[{id:'xanh',hex:'#4f8fd1'},{id:'bac',hex:'#b8bec6'}]}}};
const save=({r=4,cars=[{id:'xe_ga',color:'xanh',plate:''}],story=true,jail=null}={})=>({jail,journey:{story,garage:{cars,ride:null},
  wings:r==null?{own:[],on:null}:{own:[{id:'w1',k:'rong',r}],on:'w1'}}});

test('larger wings, a little more each tier',()=>{
  for(let r=0;r<8;r++){
    assert.ok(WA.tierScale(r)>=(.94+.018*r)*1.18,`tier ${r}: larger than before (22/10)`);
    if(r)assert.ok(WA.tierScale(r)>WA.tierScale(r-1));
    assert.equal(WA.wingScale({k:'rong',r},2),2*WA.tierScale(r));
  }
});

const extent=(wg,o)=>{const out=[];WA.drawWings(out,SVG,wg,0,0,{anim:false,aura:false,sparkle:false,...o});const xs=[],ys=[];
  for(const m of out.join('').matchAll(/ d="([^"]+)"/g)){const v=m[1].match(/-?\d+(\.\d+)?/g).map(Number);for(let i=0;i+1<v.length;i+=2){xs.push(v[i]);ys.push(v[i+1]);}}
  return {x0:Math.min(...xs),x1:Math.max(...xs),y0:Math.min(...ys),y1:Math.max(...ys)};};

test('every style at every tier, at both ends of the beat, stays inside its cached boxes',()=>{
  const C=WA.CLASSIC_WING,[bw,bh,ox,oy]=WA.WING_BOX.map(v=>v*C.s);
  for(const k of WA.WING_STYLES??['buom','tien','doi','thien_than','rong','phuong'])for(let r=0;r<8;r++)for(const flap of [-1,1]){
    const e=extent({k,r},{s:C.s,gap:C.gap,tall:C.tall,spread:C.spread,flap});
    assert.ok(e.x0>=-ox&&e.x1<=bw-ox&&e.y0>=-oy&&e.y1<=bh-oy,`${k} ${r} ${flap}: the classic wing box ${JSON.stringify(e)}`);
    const iso=extent({k,r},{s:CA.STAMP_WING.front.s,gap:CA.STAMP_WING.front.gap,flap});
    assert.ok(iso.x1-iso.x0<CA.RIG_BOX[0]&&-iso.y0<CA.RIG_BOX[3]&&iso.y1<CA.RIG_BOX[1]-CA.RIG_BOX[3],`${k} ${r} ${flap}: the 2.5D rig`);
  }
  // the shop tile keeps its size: the icon's scale shrank as the tiers grew
  assert.match(read('../public/js/v4/wings-art.js'),/export function wingIcon\(c,K,wg\)\{[^\n]*s:\.21/);
});

test('faster by the tier, on the vehicles\' scale',()=>{
  assert.equal(WA.WING_FLY_FAST.length,8);
  assert.deepEqual([...WA.WING_FLY_FAST],[...WA.WING_FLY_FAST].sort((a,b)=>a-b));
  assert.equal(WA.WING_FLY_FAST[0],R.FAST.bicycle,'D: a bicycle');
  assert.equal(WA.WING_FLY_FAST[2],R.FAST.ebike,'B: an e-bike');
  assert.equal(WA.WING_FLY_FAST[4],R.FAST.scooter,'S: a motorbike');
  assert.equal(WA.WING_FLY_FAST[7],Math.max(...Object.values(R.FAST)),'Huyền thoại: the fastest car');
  assert.equal(WA.flySpeed(null),1);assert.equal(WA.flySpeed({k:'rong',r:5}),2);
  const py=read('../game/wings_content.py').match(/FLY_FAST = \(([^)]*)\)/)[1].split(',').map(Number);
  assert.deepEqual(py,[...WA.WING_FLY_FAST],'game/wings_content.py FLY_FAST');
});

test('hovering: higher with the tier, a bob with the beat, a smaller shadow the higher',()=>{
  assert.equal(WA.flyLift(null),0);
  assert.ok(WA.flyLift({k:'rong',r:7})>WA.flyLift({k:'rong',r:0}));
  for(let t=0;t<3;t+=.1){const h=WA.flyLift({k:'buom',r:3},t);assert.ok(Math.abs(h-WA.flyLift({k:'buom',r:3}))<=4.0001);}
  const lo=WA.flyShadow(10),hi=WA.flyShadow(40);
  assert.ok(hi.rx<lo.rx&&hi.a<lo.a&&hi.ry>0);
  assert.equal(VA.flyHeight(null),0);
  assert.ok(VA.flyHeight({k:'rong',r:7})>0);
});

test('flying and riding never together: each toggle switches the other off, with its toast',()=>{
  store.clear();
  const s=save();
  assert.equal(R.canFly(s),true);assert.equal(R.flying(s),false);
  assert.equal(R.choice(s,content)?.id,'xe_ga','riding by default');
  assert.equal(R.flyLabel(false),'🪽 Bay');assert.equal(R.flyLabel(true),'🪽 Hạ cánh');
  assert.equal(R.toggleFly(s,content),R.FLY_TOAST.off,'taking off: the scooter goes home');
  assert.equal(R.flying(s),true);assert.equal(R.choice(s,content),null);
  assert.equal(R.flySpeedNow(s),WA.WING_FLY_FAST[4]);
  assert.deepEqual(VA.townFly(s),{wg:{k:'rong',r:4},tier:4,speed:WA.WING_FLY_FAST[4]});
  assert.equal(R.toggleFly(s,content),'','landing: on foot, no toast');
  assert.equal(R.flying(s),false);assert.equal(R.flySpeedNow(s),1);assert.equal(VA.townFly(s),null);
  assert.equal(R.choice(s,content),null,'landed on foot (the vehicle stays home until its toggle)');
  R.toggleFly(s,content);assert.equal(R.flying(s),true);
  assert.equal(R.next(s,content)?.id,'xe_ga','the vehicle toggle lands first');
  assert.equal(R.flying(s),false);assert.equal(R.choice(s,content)?.id,'xe_ga');
  // no vehicle: taking off says nothing
  store.clear();const walker=save({cars:[]});assert.equal(R.toggleFly(walker,content),'');assert.equal(R.flying(walker),true);
});

test('no wings, the classic mode or the trại tạm giữ: no flying',()=>{
  store.clear();
  for(const s of [save({r:null}),save({story:false}),save({jail:{until:9e12}}),{},null]){
    assert.equal(R.canFly(s),false);assert.equal(R.toggleFly(s,content),'');assert.equal(R.flying(s),false);
    assert.equal(VA.townFly(s),null);
  }
  localStorage.setItem('mnl.fly','1');
  assert.equal(R.flying(save({r:null})),false,'the wings taken off: on foot');
});

test('the maps and the live presence carry it',()=>{
  const walk=read('../public/js/v4/walk.js'),town=read('../public/js/isometric-town.js'),world=read('../client/isometric/phaser-world.ts'),
    model=read('../client/isometric/model.ts'),classic=read('../public/js/v4/town-walk.js'),shell=read('../public/js/isometric-shell.js');
  assert.match(walk,/class="fl-toggle" data-wk="fly"/);assert.match(walk,/live\.send\(\{t:'fly',on:flying\(st\)\}\)/);
  assert.match(walk,/fl\?\{fl:true\}:\{\}/,'walk_in in flight');
  assert.match(town,/fl:true/);assert.match(town,/setFlyCap/);
  assert.match(world,/getFly\(\)/);assert.match(world,/flyShadow/);
  assert.match(model,/fl\?:number/);
  assert.match(classic,/class="fl-toggle"/);assert.match(classic,/flySpeedNow\(S\(\)\)/);
  assert.match(shell,/'isoFly'/);
  for(const css of ['../public/css/walk.css','../public/css/town.css'])assert.match(read(css),/\.fl-toggle/);
  const en=JSON.parse(read('../public/i18n/en.json')),strings=en.strings??en;
  for(const vi of ['🪽 Bay','🪽 Hạ cánh',R.FLY_TOAST.off,R.FLY_TOAST.land,'Đeo cánh rồi mới bay được nhé.','Ở đây đi bộ thôi, không bay được.'])assert.ok(strings[vi],`EN: ${vi}`);
});
