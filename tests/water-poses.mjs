import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {waterFrame,waterStroke,drawSwimmer,drawRowboat} from '../public/js/isometric/water-poses.js';
import * as waterPoses from '../public/js/isometric/water-poses.js';
import {placeGeometry,placeWorldPoint} from '../public/js/pixel/place-geometry.js';
import {characterKey} from '../public/js/isometric/character-art.js';

test('water poses follow all eight movement directions without distorting heading',()=>{
  for(let i=0;i<8;i++){
    const h=i*Math.PI/4,p=waterFrame(h)(10,0),angle=Math.atan2(p[1],p[0]);
    assert.ok(Math.abs(Math.sin(angle-h))<1e-8);
    assert.ok(p[0]*Math.cos(h)+p[1]*Math.sin(h)>0);
  }
  assert.equal(waterStroke(200,false),0);
  assert.notEqual(waterStroke(200,true),waterStroke(800,true));
});

const close=(a,b)=>assert.ok(Math.hypot(a[0]-b[0],a[1]-b[1])<1e-8,`${a} must meet ${b}`);
const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);

test('hull walls join both rims without an exposed water seam at every heading',()=>{
  assert.equal(typeof waterPoses.rowboatGeometry,'function','boat must share one closed hull geometry');
  for(let i=0;i<32;i++){
    const {hull}=waterPoses.rowboatGeometry({x:10,y:20,bob:.5,heading:i*Math.PI/16},0,false);
    assert.equal(hull.walls.length,hull.rim.length);
    for(let j=0;j<hull.rim.length;j++){
      const next=(j+1)%hull.rim.length,wall=hull.walls[j];
      close(wall[0],hull.rim[j]);close(wall[1],hull.rim[next]);
      close(wall[2],hull.keel[next]);close(wall[3],hull.keel[j]);
    }
    assert.ok(hull.near.length>=4,'one connected near wall hides the seated lower body');
    assert.ok(hull.near.slice(1).some(point=>point[1]!==hull.near[0][1]));
  }
});

test('rowing grips and blades stay on rigid oars through stationary oarlocks',()=>{
  assert.equal(typeof waterPoses.rowboatGeometry,'function','rowing needs fixed oarlock geometry');
  for(let i=0;i<8;i++){
    const pose={x:20,y:30,bob:0,heading:i*Math.PI/4},rest=waterPoses.rowboatGeometry(pose,0,false);
    for(const time of [0,240*Math.PI/2,240*Math.PI,240*Math.PI*1.5]){
      const moving=waterPoses.rowboatGeometry(pose,time,true);
      for(const arm of moving.arms){
        const oar=moving.oars.find(o=>o.side===arm.side),restOar=rest.oars.find(o=>o.side===arm.side);
        close(arm.hand,oar.grip);close(oar.lock,restOar.lock);
        assert.ok(Math.abs(cross(oar.grip,oar.lock,oar.tip))<1e-8,'shaft pivots as a straight, attached oar');
        assert.ok(Math.abs(cross(oar.grip,oar.bladeStart,oar.tip))<1e-8,'blade continues the shaft');
        for(const joint of [arm.elbow,arm.hand])assert.ok(joint[1]>moving.head[1],`forearm must stay below the chin at heading ${pose.heading}`);
      }
      close(moving.seat,moving.hips);
    }
  }
});

test('chibi head crop meets the shoulders without an exposed upright neck',()=>{
  for(let i=0;i<8;i++){
    const pose={x:0,y:0,bob:0,heading:i*Math.PI/4},boat=waterPoses.rowboatGeometry(pose,500,true),swim=waterPoses.swimmerGeometry(pose,500,true);
    const shoulderMidpoint=boat.arms[0].shoulder.map((value,index)=>(value+boat.arms[1].shoulder[index])/2);
    assert.ok(Math.hypot(boat.head[0]-shoulderMidpoint[0],boat.head[1]-shoulderMidpoint[1])<=1.2,'rower head sits directly above its shoulders');
    assert.ok(Math.hypot(swim.neck[0][0]-swim.neck[1][0],swim.neck[0][1]-swim.neck[1][1])<=2.8,'prone swimmer has a short neck continuous with its chest');
  }
});

test('swimming shoulders, hips and neck connect to one visible submerged torso',()=>{
  assert.equal(typeof waterPoses.swimmerGeometry,'function','swimming must share body and limb anchors');
  for(let i=0;i<8;i++)for(const moving of [true,false]){
    const pose=waterPoses.swimmerGeometry({x:10,y:20,bob:.2,heading:i*Math.PI/4},500,moving);
    for(const arm of pose.arms)close(arm.shoulder,pose.shoulders.find(p=>p.side===arm.side).point);
    for(const leg of pose.legs)close(leg.hip,pose.hips.find(p=>p.side===leg.side).point);
    close(pose.neck[0],pose.chest);close(pose.neck[1],pose.head);
    assert.ok(pose.bodyAlpha>=.55,'torso cannot disappear while opaque limbs appear disconnected');
    assert.ok(pose.headSize<=20,'head stays proportionate to the articulated body');
    for(let j=1;j<pose.arms.length;j++)assert.ok(pose.arms[j-1].depth<=pose.arms[j].depth);
  }
});

test('oar blades dip into the water on the drive and lift clear during recovery',()=>{
  const pose={x:0,y:0,bob:0,heading:0},drive=waterPoses.rowboatGeometry(pose,240*Math.PI,true),recovery=waterPoses.rowboatGeometry(pose,0,true);
  for(const oar of drive.oars){
    const water=waterFrame(0)(2,oar.side*23),lifted=recovery.oars.find(item=>item.side===oar.side);
    assert.ok(oar.tip[1]>water[1],'driving blade must cross the water plane');
    assert.ok(lifted.tip[1]<water[1],'returning blade must clear the water plane');
    assert.equal(oar.inWater,true);assert.equal(lifted.inWater,false);
  }
});

function drawing(){
  const calls=[],state={globalAlpha:1},stack=[];let path=[];
  const c=new Proxy(state,{get(target,key){
    if(key in target)return target[key];
    if(key==='save')return ()=>stack.push({...state});
    if(key==='restore')return ()=>Object.assign(state,stack.pop());
    if(key==='beginPath')return ()=>{path=[];};
    if(key==='fill'||key==='stroke')return ()=>calls.push({kind:key,path:[...path],colour:state[key==='fill'?'fillStyle':'strokeStyle'],alpha:state.globalAlpha});
    if(key==='drawImage')return (...args)=>calls.push({kind:key,args});
    return (...args)=>path.push([key,...args]);
  },set(target,key,value){target[key]=value;return true;}});
  return {c,calls};
}

test('near hull covers the sitter and the near oar remains above its rim when turning',()=>{
  assert.equal(typeof waterPoses.rowboatGeometry,'function','renderer and draw order use the same geometry');
  for(let i=0;i<8;i++){
    const pose={x:110,y:100,bob:0,heading:i*Math.PI/4},g=waterPoses.rowboatGeometry(pose,500,true),{c,calls}=drawing();
    drawRowboat(c,{width:120,height:160},pose,500,true,{gender:'female'});
    const head=calls.findIndex(call=>call.kind==='drawImage'),near=calls.findIndex(call=>call.kind==='fill'&&call.path.length===g.hull.near.length+1&&g.hull.near.every((point,index)=>Math.hypot(call.path[index][1]-point[0],call.path[index][2]-point[1])<1e-8));
    assert.ok(near>head,'joined near wall must cover the sitter after the body is painted');
    const oar=g.oars.at(-1),shaft=calls.findIndex(call=>call.kind==='stroke'&&call.path.some(p=>p[0]==='moveTo'&&Math.hypot(p[1]-oar.lock[0],p[2]-oar.lock[1])<1e-8)&&call.path.some(p=>p[0]==='lineTo'&&Math.hypot(p[1]-oar.tip[0],p[2]-oar.tip[1])<1e-8));
    assert.ok(shaft>near,'near oar must emerge above the near rim');
    const farLock=g.oars[0].lock,farLockDraw=calls.findIndex(call=>call.kind==='fill'&&call.path.some(p=>p[0]==='ellipse'&&Math.hypot(p[1]-farLock[0],p[2]-farLock[1])<1e-8));
    assert.ok(farLockDraw>=0&&farLockDraw<head,'far oarlock cannot float over the seated torso');
    assert.equal(g.oars[0].side,-g.oars[1].side);
    assert.ok(g.oars[0].depth<=g.oars[1].depth,'turning changes which oar is far');
  }
});

test('water rendering stays finite at rest and in motion, preserves only illustrated head',()=>{
  for(const draw of [drawSwimmer,drawRowboat])for(let i=0;i<8;i++)for(const moving of [true,false]){
    const calls=[],c=new Proxy({}, {get:(_,name)=>(...args)=>{for(const n of args)if(typeof n==='number')assert.ok(Number.isFinite(n),`${String(name)} ${args}`);calls.push([name,args]);},set:()=>true});
    draw(c,{width:120,height:160},{x:110,y:100,bob:.4,heading:i*Math.PI/4},500,moving,{gender:'female'});
    const head=calls.find(([k])=>k==='drawImage');
    assert.ok(head);assert.equal(head[1][4],160*.58,'standing arms cannot be drawn over the articulated pose');
  }
});

// Run the actual scene's character selection with raster/DOM services at the boundary.
// Walking atlas rows have different trimmed bounds; cycling them changes the fixed head crop.
const placeSource=readFileSync(new URL('../public/js/pixel/places.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export \{.*\} from .*\r?\n/gm,'').replace(/^export /gm,'');
function actorPainter(useArt){
  const selections=[],select=options=>{selections.push(options);return {canvas:{width:120,height:160}};};
  const context=vm.createContext({placeGeometry,placeWorldPoint,drawSwimmer,drawRowboat,getCharacterStamp:select});
  vm.runInContext(placeSource+'\nglobalThis.draw=drawPlaceActor;globalThis.pose=leisurePose;',context);
  return {selections,draw(kind,state,time,appearance){const {c}=drawing();context.draw(c,kind,state,context.pose(state,time,1000),time,useArt?{character:select}:{},appearance);}};
}

for(const kind of ['pool','boat'])for(const useArt of [true,false])test(`${kind} moving water uses a stable illustrated head through ${useArt?'loaded art':'fallback'} character selection`,()=>{
  const h=actorPainter(useArt);
  for(const gender of ['male','female'])for(const direction of ['se','sw','nw','ne']){
    const appearance={gender,look:{top:'ao_len',acc:'non_la'}},state={kind,phase:kind,x:150,y:110,direction,moving:true};
    const start=h.selections.length;
    for(const time of [0,180,360,540])h.draw(kind,state,time,appearance);
    const selected=h.selections.slice(start);
    assert.equal(new Set(selected.map(characterKey)).size,1,'swimming/rowing must not cycle head placement or crop with walking steps');
    for(const options of selected){assert.equal(options.walkFrame,0);assert.equal(options.direction,direction);assert.equal(options.gender,gender);assert.equal(options.look,appearance.look);}
  }
});

test('land walking still uses both illustrated walking frames',()=>{
  const h=actorPainter(true),state={kind:'pool',phase:'walk',x:100,y:170,direction:'se',moving:true};
  for(const time of [0,180,360,540])h.draw('pool',state,time,{gender:'female'});
  assert.deepEqual(h.selections.map(options=>options.walkFrame),[0,1,0,2]);
});
