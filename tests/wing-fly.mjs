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

// 🪽 Owner 24/10 "bay thì cho cánh to hơn nha, cánh to hơn người và người k cần di chuyển nữa (k cần bước đi)": in the
// air the pair opens wider than the flyer is tall and the flyer hovers (no walking cycle), on every map.
const BODY=122;   // the classic character's height (v4/look.js paintPlayer: the feet at 0, the hair's top at -119)
test('in the air the wings span wider than the flyer is tall (about 1.6–2.2×), a little more each tier',()=>{
  assert.ok(WA.FLY_WING>1.2&&WA.FLY_WING<1.6,'larger in the air, never huge');
  const C=WA.CLASSIC_WING,styles=WA.WING_STYLES,avg=r=>styles.reduce((a,k)=>{const e=extent({k,r},{s:C.s*WA.FLY_WING,gap:C.gap,tall:C.tall,spread:C.spread,flap:0});return a+(e.x1-e.x0);},0)/styles.length/BODY;
  for(const k of styles)for(let r=0;r<8;r++){
    const e=extent({k,r},{s:C.s*WA.FLY_WING,gap:C.gap,tall:C.tall,spread:C.spread,flap:0}),ratio=(e.x1-e.x0)/BODY;
    assert.ok(ratio>1.45&&ratio<2.6,`${k} ${r}: wingspan ${ratio.toFixed(2)}× the body`);
    const ground=extent({k,r},{s:C.s,gap:C.gap,tall:C.tall,spread:C.spread,flap:0});
    assert.ok(e.x1-e.x0>(ground.x1-ground.x0)*1.2,`${k} ${r}: larger than on the ground`);
  }
  assert.ok(avg(0)>=1.6&&avg(0)<1.9,`D: ${avg(0).toFixed(2)}×`);
  assert.ok(avg(7)>2&&avg(7)<=2.2,`Huyền thoại: ${avg(7).toFixed(2)}×`);
  for(let r=1;r<8;r++)assert.ok(avg(r)>avg(r-1),'a little more each tier');
});

test('the hover: slow and wide gliding, quicker moving, no jump when the pace changes, a float with the beat',()=>{
  const wg={k:'rong',r:3},base=24+2*3,dt=1/30;
  const run=(o,from,to,moving)=>{const out=[];for(let t=from;t<to-1e-9;t+=dt)out.push({t,...WA.flyMotion(o,wg,t,moving)});return out;};
  // gliding: the beat is 1.3 of the style's own (rồng 2.6 s → 3.38 s), the full stroke; the float follows the flap
  const glide=run({},0,10,false),cross=a=>a.slice(1).filter((p,i)=>a[i].flap<0&&p.flap>=0).map(p=>p.t);
  const gc=cross(glide),gp=(gc.at(-1)-gc[0])/(gc.length-1);
  assert.ok(Math.abs(gp-WA.WING_BEAT.rong*1.3)<.1,`gliding beat ${gp.toFixed(2)} s`);
  assert.ok(Math.max(...glide.map(p=>p.flap))>.65,'the full stroke');
  for(const p of glide){assert.ok(Math.abs(p.lift-base)<=4.0001);assert.equal(p.lean,0);assert.ok(Math.sign(p.lift-base)===Math.sign(p.flap)||Math.abs(p.flap)<1e-9,'rises as the wings come down');}
  // moving: a quicker beat (.55), the lean eases in
  const o={},mv=run(o,0,12,true),mc=cross(mv.slice(90)),mp=(mc.at(-1)-mc[0])/(mc.length-1);
  assert.ok(Math.abs(mp-WA.WING_BEAT.rong*.55)<.1,`moving beat ${mp.toFixed(2)} s`);
  assert.ok(mv[1].lean<.3&&mv.at(-1).lean>.99,'leaning in, eased');
  // starting / stopping: the flap and the float never jump
  const s={},seq=[...run(s,0,3,false),...run(s,3,6,true),...run(s,6,9,false)];
  for(let i=1;i<seq.length;i++){assert.ok(Math.abs(seq[i].flap-seq[i-1].flap)<.25,`flap jump at ${seq[i].t.toFixed(2)}`);assert.ok(Math.abs(seq[i].lift-seq[i-1].lift)<1.2,'float jump');}
  assert.ok(seq.at(-1).lean<.01,'upright again, gliding');
  // still pictures: the wings still, no lean, the hover height
  assert.deepEqual(WA.flyMotion({},wg,null,true),{flap:0,lift:base,lean:0});
  assert.deepEqual(WA.flyMotion({},null,1,true),{flap:0,lift:0,lean:0});
  assert.ok(WA.FLY_LEAN>0&&WA.FLY_LEAN<.15,'a slight lean');
});

test('no steps in the air, on every map; the larger pair behind the body; others see it (fl)',()=>{
  const world=read('../client/isometric/phaser-world.ts'),rigs=read('../client/isometric/wing-rigs.ts'),classic=read('../public/js/v4/town-walk.js'),walk=read('../public/js/v4/walk.js'),
    bundle=read('../public/js/isometric/phaser-world.js');
  // 2.5D: me on the standing frame (no walking pose), others too; the hover's lean and lift; the wings at the hover's flap
  assert.match(world,/const pose=flying\?\{frame:0,lean:0,squash:1\}:walkingPose\(/);
  assert.match(world,/walkFrame=moving&&!this\.owner\.reduced&&actor\.fly==null\?/);
  assert.match(world,/fly,flap:fly\?this\.myFly\.flap:null/);assert.match(world,/fly,flap:fly\?actor\.fp\?\.flap\?\?0:null/);
  assert.match(world,/setRotation\(flying\?leanOf\(this\.myFly\.lean/);
  assert.match(rigs,/big=h\.fly\?flyWing\(\):1,sc=host\.scaleX\*big/);assert.match(rigs,/setRotation\(rot\)/);
  assert.match(rigs,/depth\+\(back\?\.001:-\.001\)/,'behind the body facing us, over its back from behind');
  // a player leaving while their sparkles were over the budget (a hole in the motes list) never breaks the scene
  assert.match(rigs,/for\(const m of rig\.motes\)m\?\.destroy\(\)/);assert.match(rigs,/for\(const m of rig\.motes\)m\?\.setVisible\(false\)/);assert.match(rigs,/rig\.motes\[i\]\?\.setVisible\(false\)/);
  assert.match(bundle,/flyMotion/,'the built scene carries it (npm run build:isometric)');
  // classic town: no hop, the larger pair, the lean
  const fl=classic.slice(classic.indexOf('function flyer('),classic.indexOf('/* ---- test hooks'));
  assert.match(fl,/flyMotion\(FLY_STATE/);assert.match(fl,/z=ME\*FLY_WING/);assert.doesNotMatch(fl,/hop/);
  // strolls: the flyer's sprite without the walking bob; the wing bitmap really drawn (2.6.0 lost it in a comment)
  assert.match(walk,/z=AV\*\(p\.flying\?FLY_WING:1\)/);
  const back=walk.slice(walk.indexOf('function wingsBack('),walk.indexOf('function wingsFront('));
  assert.match(back,/\n[^/\n]*if\(bm\)c\.drawImage\(bm\.canvas/,'the wings drawn, not commented out');
  assert.match(walk,/const bob=p\.moving\?/,'the walking bob only on foot');
  // live: town and street carry the flyer's tier
  assert.match(read('../public/js/isometric-town.js'),/flyOf\(e\.fl\)/);assert.match(walk,/p\.fl=q\.fl/);
});
