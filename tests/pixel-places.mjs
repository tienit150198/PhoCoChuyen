import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import * as geometry from '../public/js/pixel/place-geometry.js';
import {rowboatGeometry,swimmerGeometry} from '../public/js/isometric/water-poses.js';
const source=readFileSync(new URL('../public/js/pixel/places.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export \{.*\} from .*\r?\n/gm,'').replace(/^export /gm,'');
function harness(kind='boat',command){
 let now=100000;const calls=[],boats=[];
 const cmd=command||(async(name,p)=>{calls.push({name,p});if(name==='jr_leisure_start')return {leisure_round:{id:'round',kind,now:now/1000,bite_at:now/1000+3,bite_window:1.6,entry:geometry.placeGeometry(kind).entry,checkpoints:kind==='pool'?[[86,64],[250,64],[250,140],[86,142]]:[[144,62],[260,70],[252,142],[104,150]],min_seconds:6}};return {message:'Đã lưu',next:p.index+1,leisure:{boat_laps:1}};});
 const context=vm.createContext({console,Math,Date,Set,Map,...geometry,getCharacterStamp:()=>({canvas:{}}),drawRowboat:(ctx,stamp,pose)=>boats.push({...pose})});vm.runInContext(source+'\nglobalThis.exports={createPixelPlay,walkablePlace,createPlaceLifecycle,leisurePose,placeCamera,placePoint,drawPlaceActor};',context);
 const play=context.exports.createPixelPlay(kind,{now:()=>now,command:cmd});
 return {play,calls,boats,...context.exports,dock(){[play.state.x,play.state.y]=geometry.placeGeometry(kind).dock;},clock:()=>now,advance(ms){now+=ms;play.step(ms/1000);}};
}
test('walking respects shore and dock; activity requires approaching it',async()=>{
 const h=harness();await h.play.interact();assert.equal(h.calls.length,0);
 assert.equal(h.walkablePlace('boat',220,100,false),false);
 assert.equal(h.walkablePlace('boat',93,154,false),true);
 h.play.input(0,-1);for(let i=0;i<18;i++)h.advance(50);h.play.input(0,0);
 assert.ok(h.play.state.y<166);await h.play.interact();assert.equal(h.calls.length,0,'boarding a free boat does not create a server round');
 assert.equal(h.play.state.phase,'boat');
});
test('fishing has cast wait bite timed reel and real save command',async()=>{
 const h=harness('fishing');h.dock();
 await h.play.interact();assert.equal(h.play.state.phase,'waiting');
 await h.play.interact();assert.equal(h.calls.length,1);
 h.advance(3200);assert.equal(h.play.state.phase,'bite');
 await h.play.interact();assert.equal(h.calls.at(-1).name,'jr_leisure_finish');assert.equal(h.play.state.phase,'walk');
});
test('free rowing has no round, checkpoints, expiry or save request',async()=>{
 const h=harness();h.dock();await h.play.interact();h.advance(700);
 assert.equal(h.play.state.phase,'boat');assert.equal(h.play.state.round,null);assert.deepEqual(h.calls,[]);
 for(const target of [[144,62],[260,70],[252,142],[104,150]]){
  for(let n=0;n<1000;n++){
   const p=geometry.placeWorldPoint('boat',h.play.state,true),to=geometry.placeWorldPoint('boat',{x:target[0],y:target[1]},true);
   if(Math.hypot(to.x-p.x,to.y-p.y)<3)break;
   h.play.input(to.x-p.x,to.y-p.y);h.advance(50);await Promise.resolve();
   assert.equal(h.play.state.busy,false);assert.equal(h.play.state.phase,'boat');
  }
  assert.ok(Math.hypot(h.play.state.x-target[0],h.play.state.y-target[1])<5,'former route points are ordinary water');
 }
 h.play.reset();h.advance(3600000);assert.equal(h.play.state.phase,'boat');assert.equal(h.play.needsFrame(),false);
 await h.play.interact();assert.equal(h.play.state.phase,'walk');assert.deepEqual(h.calls,[]);
 h.advance(700);await h.play.interact();assert.equal(h.play.state.phase,'boat');assert.equal(h.play.state.round,null);
});

test('legacy checkpoint data cannot freeze or submit a free boat',async()=>{
 const h=harness();h.dock();await h.play.interact();h.advance(700);
 h.play.state.round={id:'legacy',checkpoints:[[104,150]],entry:[104,150]};
 h.play.input(1,0);h.advance(50);await Promise.resolve();
 assert.equal(h.play.state.busy,false);assert.deepEqual(h.calls,[]);assert.ok(h.play.state.x>104);
});

test('a delayed swimming checkpoint does not stop movement or send duplicates',async()=>{
 let reply;const calls=[];
 const h=harness('pool',(name,payload)=>{calls.push({name,payload});return new Promise(resolve=>{reply=resolve;});});
 Object.assign(h.play.state,{phase:'pool',x:86,y:142,round:{id:'lap',entry:[86,142],checkpoints:[[86,142],[250,140]]}});
 h.play.input(1,0);h.advance(50);const x=h.play.state.x;
 for(let i=0;i<10;i++)h.advance(50);
 assert.ok(h.play.state.x>x+10,'server latency must not freeze a held swim input');
 assert.equal(h.play.state.busy,false,'automatic checkpoint bookkeeping must not disable controls');
 assert.equal(h.play.needsFrame(),true);assert.equal(calls.length,1,'one request per pending checkpoint');
 reply({next:1});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(h.play.state.next,1);
});

for(const failure of [false,true])test(`late checkpoint ${failure?'failure':'success'} cannot change a swimmer who already climbed out`,async()=>{
 let resolve,reject;const h=harness('pool',()=>new Promise((a,b)=>{resolve=a;reject=b;}));
 Object.assign(h.play.state,{phase:'pool',x:86,y:142,round:{id:'lap',entry:[86,142],checkpoints:[[86,142]]}});
 h.advance(50);await h.play.leave();
 assert.equal(h.play.state.phase,'walk','physical exit stays available while checkpoint saves');
 const before=JSON.stringify(h.play.state);
 if(failure)reject(Object.assign(new Error('Expired'),{data:{code:'expired'}}));else resolve({next:1});
 await new Promise(resolve=>setImmediate(resolve));assert.equal(JSON.stringify(h.play.state),before);
});

for(const kind of ['pool'])for(const code of ['expired','bad_round']){
 test(`${kind} ${code} offshore retains water movement and returns physically without more round commands`,async()=>{
  const calls=[],entry=kind==='boat'?[104,150]:[86,142],checkpoint=kind==='boat'?[144,62]:[86,64];let offshore,h;
  h=harness(kind,async(name,payload)=>{
   calls.push({name,payload});
   if(name==='jr_leisure_start')return {leisure_round:{id:'ended-round',kind,now:100,entry,checkpoints:[checkpoint,entry]}};
   offshore={x:h.play.state.x,y:h.play.state.y};throw Object.assign(new Error('Vòng không còn hiệu lực'),{data:{code}});
  });
  const steerTo=(target,threshold)=>{
   for(let n=0;n<1000&&Math.hypot(target[0]-h.play.state.x,target[1]-h.play.state.y)>threshold;n++){
    h.play.input(target[0]-h.play.state.x,target[1]-h.play.state.y);h.advance(50);
    if(h.play.state.busy)break;
   }
   h.play.reset();
  };
  h.dock();await h.play.interact();h.advance(700);
  steerTo(checkpoint,4);offshore={x:h.play.state.x,y:h.play.state.y};await new Promise(resolve=>setImmediate(resolve));
  assert.equal(h.play.state.phase,'return');assert.equal(h.play.state.x,offshore.x);assert.equal(h.play.state.y,offshore.y,'terminal error never teleports an offshore player');
  assert.deepEqual(Array.from(h.play.state.round.entry),entry);assert.equal(h.play.state.round.id,undefined,'expired proof is discarded');
  assert.equal(h.play.state.round.checkpoints,undefined);assert.match(h.play.state.message,/Vòng đã kết thúc/);assert.match(h.play.state.message,kind==='boat'?/bến/:/thang/);
  assert.equal(h.leisurePose(h.play.state,0,h.clock()).water,true);
  await h.play.interact();assert.equal(h.play.state.phase,'return','exit requires returning close to the entry');
  const before={x:h.play.state.x,y:h.play.state.y};steerTo(entry,4);
  assert.ok(Math.hypot(before.x-h.play.state.x,before.y-h.play.state.y)>40,'player can move through water back to the entry');
  assert.ok(Math.hypot(entry[0]-h.play.state.x,entry[1]-h.play.state.y)<=4);
  await h.play.interact();assert.equal(h.play.state.phase,'walk');assert.equal(h.play.state.action.kind,'exit');assert.equal(h.play.state.round,null);
  h.advance(700);assert.equal(h.play.state.action,null);
  assert.deepEqual(calls.map(c=>c.name),['jr_leisure_start','jr_leisure_checkpoint'],'return and exit send no checkpoint or finish after terminal failure');
 });
}
test('destroy stops movement and late pending replies never mutate the closed scene',async()=>{
 let resolve;const h=harness('pool',()=>new Promise(r=>{resolve=r;}));h.dock();
 const pending=h.play.interact();h.play.destroy();const before=JSON.stringify(h.play.state);
 resolve({leisure_round:{id:'late',entry:[104,150],checkpoints:[]}});await pending;
 h.play.input(1,1);h.advance(1000);assert.equal(JSON.stringify(h.play.state),before);
});
test('animation lifecycle cancels frames and resets inputs on suspend and destroy',()=>{
 const h=harness();let next=0,reset=0;const frames=new Map();
 const loop=h.createPlaceLifecycle({step:()=>{},render:()=>{},reset:()=>reset++,needsFrame:()=>true},{raf:f=>{frames.set(++next,f);return next;},caf:i=>frames.delete(i),now:()=>0});
 loop.resume();assert.equal(frames.size,1);loop.suspend();assert.equal(frames.size,0);assert.equal(reset,1);
 loop.resume();loop.destroy();assert.equal(frames.size,0);loop.resume();assert.equal(frames.size,0);
});

test('an idle place owns no RAF and input or a changed network pose wakes only the required frames',()=>{
 const h=harness();let next=0,clock=0,active=false,paint=0;const frames=new Map();
 const loop=h.createPlaceLifecycle({step:()=>{},render:()=>paint++,reset:()=>{},needsFrame:()=>active},{raf:f=>{frames.set(++next,f);return next;},caf:i=>frames.delete(i),now:()=>clock});
 const flush=()=>{const [id,frame]=frames.entries().next().value;frames.delete(id);clock+=40;frame(clock);};
 loop.resume();assert.equal(paint,1);assert.equal(frames.size,0,'idle opening paints once and sleeps');
 loop.wake();assert.equal(frames.size,1);flush();assert.equal(frames.size,0,'a static network appearance needs one paint');
 active=true;loop.wake();flush();assert.equal(frames.size,1,'held movement continues');
 active=false;loop.wake();flush();assert.equal(frames.size,0,'release paints the stopped pose and sleeps');
});

test('suspension reset callbacks and late replies cannot resurrect animation before focus resumes',()=>{
 const h=harness();let next=0,reset=0;const frames=new Map();let loop;
 loop=h.createPlaceLifecycle({step:()=>{},render:()=>{},needsFrame:()=>true,reset:()=>{reset++;loop.wake();loop.resume();}},{raf:f=>{frames.set(++next,f);return next;},caf:i=>frames.delete(i),now:()=>0});
 loop.resume();assert.equal(frames.size,1);loop.suspend();assert.equal(reset,1);assert.equal(frames.size,0);
 loop.wake();assert.equal(frames.size,0,'late async reply while blurred cannot enable animation');
 loop.resume();assert.equal(frames.size,1);loop.destroy();assert.equal(frames.size,0);loop.resume();loop.wake();assert.equal(frames.size,0);
});

test('reset immediately clears motion and an idle boat has no timed simulation work',()=>{
 const h=harness();assert.equal(h.play.needsFrame(),false);h.play.input(1,0);assert.equal(h.play.needsFrame(),true);h.advance(50);
 assert.equal(h.play.state.moving,true);h.play.reset();assert.equal(h.play.state.moving,false);assert.equal(h.play.needsFrame(),false);
});
test('pool swimmer stays inside water and can complete a lap then climb out',async()=>{
 const h=harness('pool');h.dock();await h.play.interact();
 assert.equal(h.play.state.phase,'pool');assert.equal(h.walkablePlace('pool',45,90,true),false);
 assert.equal(h.walkablePlace('pool',250,140,true),true);
 h.play.state.round.entry=[86,142];h.play.state.round.checkpoints=[[86,64],[250,64],[250,140],[86,142]];
 for(const [x,y] of h.play.state.round.checkpoints){h.play.state.x=x;h.play.state.y=y;h.advance(1500);await new Promise(resolve=>setImmediate(resolve));}
 await h.play.interact();assert.equal(h.play.state.phase,'return');await h.play.interact();assert.equal(h.play.state.phase,'walk');
});
test('illustrated pose follows all four headings, atlas walk rows and water state',()=>{
 const h=harness();
 assert.equal(h.leisurePose({direction:'ne',phase:'boat',moving:true},180).walkFrame,1);
 assert.equal(h.leisurePose({direction:'sw',phase:'pool',moving:true},540).walkFrame,2);
 assert.equal(h.leisurePose({direction:'sw',phase:'walk',moving:false},540).walkFrame,0);
 for(const [direction,heading] of Object.entries({se:Math.PI/4,sw:Math.PI*3/4,nw:-Math.PI*3/4,ne:-Math.PI/4})){
  const pose=h.leisurePose({direction,phase:'boat',moving:false},100);assert.equal(pose.heading,heading);assert.equal(pose.water,true);
 }
 h.play.input(1,0);h.advance(50);assert.equal(h.leisurePose(h.play.state,100).heading,0,'boat follows actual steering angle');
});

test('full-screen portrait and landscape cameras cover without stretching and preserve world coordinates',()=>{
 const h=harness();
 for(const [width,height] of [[390,844],[1440,900],[844,390]]){
  const camera=h.placeCamera(width,height,{x:84,y:180});
  assert.ok(camera.viewWidth<=320&&camera.viewHeight<=200);assert.ok(Math.abs(camera.viewWidth/camera.viewHeight-width/height)<1e-12);
  assert.ok(camera.x>=0&&camera.y>=0&&camera.x+camera.viewWidth<=320+.0001&&camera.y+camera.viewHeight<=200+.0001);
  const point=h.placePoint(camera,(84-camera.x)*camera.scale,(180-camera.y)*camera.scale);assert.ok(Math.abs(point.x-84)<.0001&&Math.abs(point.y-180)<.0001);
 }
});

test('boarding and exit interpolate across the dock while input cannot move during the action',async()=>{
 const h=harness();h.dock();await h.play.interact();
 assert.equal(h.play.state.action.kind,'board');h.play.input(1,0);h.advance(350);
 const pose=h.leisurePose(h.play.state,0,h.clock());assert.ok(pose.x>96&&pose.x<132);assert.equal(h.play.state.x,104);
 h.advance(350);assert.equal(h.play.state.action,null);h.advance(50);assert.ok(h.play.state.x>104);
 h.play.state.phase='return';h.play.state.x=104;h.play.state.y=150;await h.play.interact();
 assert.equal(h.play.state.action.kind,'exit');const start=h.leisurePose(h.play.state,0,h.clock());assert.equal(start.x,132);assert.equal(start.y,130);
 h.advance(700);assert.equal(h.play.state.action,null);assert.equal(h.play.state.y,geometry.placeGeometry('boat').dock[1]);
});

test('fishing shows a caught fish only after server success and releases the action for another cast',async()=>{
 const h=harness('fishing');h.dock();await h.play.interact();assert.equal(h.play.state.action.kind,'cast');
 h.advance(3200);await h.play.interact();assert.equal(h.play.state.action.kind,'caught');
 assert.equal(h.leisurePose(h.play.state,0,h.clock()).fishingPose,'reel','a quick server answer still shows the jerk before the catch');
 assert.equal(h.leisurePose(h.play.state,0,h.clock()+700).fishingPose,'caught');
 const count=h.calls.length;await h.play.interact();assert.equal(h.calls.length,count);h.advance(1900);assert.equal(h.play.state.action,null);
 await h.play.interact();assert.equal(h.calls.at(-1).name,'jr_leisure_start');
 const failed=harness('fishing',async action=>{if(action==='jr_leisure_start')return {leisure_round:{id:'round',now:100,bite_at:103,bite_window:1.6}};throw Object.assign(new Error('Cá đã nhả mồi'),{data:{code:'missed'}});});
 failed.dock();await failed.play.interact();failed.advance(3200);await failed.play.interact();
 assert.equal(failed.play.state.action,null);assert.equal(failed.play.state.phase,'walk');assert.equal(failed.leisurePose(failed.play.state,0,failed.clock()).fishingPose,'ready');
});

test('boat hull cannot occupy the pier even when its center remains in the old water rectangle',()=>{
 const h=harness();
 assert.equal(h.walkablePlace('boat',80,150,true),false,'hull must clear the illustrated pier and its posts');
});

test('swimming can reach the illustrated water beyond the old narrow rectangle',()=>{
 const h=harness('pool');
 assert.equal(h.walkablePlace('pool',43,125,true),true,'left lower swimming lane is usable water');
 assert.equal(h.walkablePlace('pool',265,125,true),true,'right lower swimming lane is usable water');
});

test('water activities can be left at the entry without completing or saving a lap',async()=>{
 for(const kind of ['boat','pool']){
  const h=harness(kind);h.dock();await h.play.interact();h.advance(700);
  assert.equal(typeof h.play.leave,'function','free play needs a physical exit independent of the lap');
  await h.play.leave();assert.equal(h.play.state.phase,'walk');
  assert.equal(h.play.state.round,null);assert.deepEqual(h.calls.map(c=>c.name),kind==='boat'?[]:['jr_leisure_start']);
 }
});

test('every activity entry and checkpoint lies in navigable art-space with reversible public coordinates',()=>{
 for(const kind of ['boat','pool']){
  const g=geometry.placeGeometry(kind),points=[g.entry,...(kind==='boat'?[[144,62],[260,70],[252,142]]:[[86,64],[250,64],[250,140]])];
  for(const [x,y] of points){
   assert.equal(geometry.walkablePlace(kind,x,y,true),true,`${kind} route point ${x},${y} must fit the whole actor`);
   const world=geometry.placeWorldPoint(kind,{x,y},true),back=geometry.placeNetworkPoint(kind,world,true);
   assert.ok(Math.hypot(back.x-x,back.y-y)<1e-8,'proof and peer coordinates round trip');
  }
 }
});

test('conservative clearance encloses every hull heading including bobbing without a pier overlap',()=>{
 const g=geometry.placeGeometry('boat'),center=geometry.placeWorldPoint('boat',{x:g.entry[0],y:g.entry[1]},true);
 for(let i=0;i<64;i++)for(const bob of [-.65,.65]){
  const hull=rowboatGeometry({...center,heading:i*Math.PI/32,bob},500,true).hull.outer;
  for(const [x,y] of hull){
   assert.ok(x>=center.x-g.footprint.x&&x<=center.x+g.footprint.x);
   assert.ok(y>=center.y-g.footprint.top&&y<=center.y+g.footprint.bottom);
   assert.ok(x>g.pier.right||x<g.pier.left||y<g.pier.top||y>g.pier.bottom,'moored hull never overlaps wood');
  }
 }
});

test('swept movement cannot tunnel through the pier or cut its corner diagonally',()=>{
 const start={x:104,y:150},g=geometry.placeGeometry('boat');
 for(const [dx,dy] of [[-200,0],[-200,-25],[-120,70],[0,400]]){
  const result=geometry.moveInPlace('boat',start,dx,dy,true),p=geometry.placeWorldPoint('boat',result,true);
  assert.equal(geometry.walkablePlace('boat',result.x,result.y,true),true);
  assert.ok(p.x-g.footprint.x>=g.pier.right,'long displacement cannot emerge on the other side of the dock');
 }
 let p=start;
 for(let i=0;i<100;i++){
  p=geometry.moveInPlace('boat',p,-1,-1,true);assert.equal(geometry.walkablePlace('boat',p.x,p.y,true),true);
 }
 const end=geometry.placeWorldPoint('boat',p,true);assert.ok(end.y+g.footprint.bottom<=g.pier.top,'diagonal sliding can round the open tip safely');
});

test('pool bank follows the trapezoid, and the swimmer has materially more room relative to body size',()=>{
 const g=geometry.placeGeometry('pool');
 assert.equal(geometry.navigablePlaceWorld('pool',90,130,true),false,'sloping left bank blocks the upper corner');
 assert.equal(geometry.navigablePlaceWorld('pool',100,250,true),true,'the wider lower corner remains usable');
 assert.equal(geometry.navigablePlaceWorld('pool',550,130,true),false,'sloping right bank blocks the upper corner');
 assert.equal(geometry.navigablePlaceWorld('pool',550,250,true),true);
 const left=geometry.placeNetworkPoint('pool',{x:100,y:250},true),right=geometry.placeNetworkPoint('pool',{x:550,y:250},true);
 assert.ok(geometry.walkablePlace('pool',left.x,left.y,true)&&geometry.walkablePlace('pool',right.x,right.y,true));
 assert.ok((550-100)/32>2*196/32,'swimming span relative to unchanged actor width more than doubles');
 for(let i=0;i<8;i++){
  const pose=swimmerGeometry({x:0,y:0,heading:i*Math.PI/4,bob:0},500,true);
  for(const point of [...pose.body,...pose.arms.flatMap(a=>[a.shoulder,a.elbow,a.hand]),...pose.legs.flatMap(a=>[a.hip,a.knee,a.foot])]){
   assert.ok(Math.abs(point[0])<=g.footprint.x);assert.ok(point[1]>=-g.footprint.top&&point[1]<=g.footprint.bottom);
  }
 }
});

test('real steering reaches each ordered pool checkpoint and returns',async()=>{
 for(const kind of ['pool']){
  const h=harness(kind);h.dock();await h.play.interact();const started=h.clock();h.advance(700);
  for(let index=0;index<4;index++){
   const target=h.play.state.round.checkpoints[index];
   for(let n=0;n<1000&&h.play.state.next===index;n++){
    const p=geometry.placeWorldPoint(kind,h.play.state,true),to=geometry.placeWorldPoint(kind,{x:target[0],y:target[1]},true);
    h.play.input(to.x-p.x,to.y-p.y);h.advance(50);
    assert.equal(h.walkablePlace(kind,h.play.state.x,h.play.state.y,true),true);
    await new Promise(resolve=>setImmediate(resolve));
   }
   assert.equal(h.play.state.next,index+1,`${kind} reaches checkpoint ${index} using movement, without teleporting`);
  }
  assert.ok(h.clock()-started>=(kind==='boat'?6000:7000),'natural full-speed lap satisfies the server minimum duration');
  h.play.reset();await h.play.interact();assert.equal(h.play.state.phase,'return');await h.play.interact();assert.equal(h.play.state.phase,'walk');
  for(const c of h.calls.filter(c=>c.name==='jr_leisure_checkpoint')){
   const target=kind==='boat'?[[144,62],[260,70],[252,142],[104,150]][c.p.index]:[[86,64],[250,64],[250,140],[86,142]][c.p.index];
   assert.ok(Math.hypot(c.p.x-target[0],c.p.y-target[1])<=8.02,'server receives original normalized proof coordinates');
  }
 }
});

test('leaving offshore preserves physical movement while dropping proof and guiding the player to the entry',async()=>{
 for(const kind of ['boat','pool']){
  const h=harness(kind);h.dock();await h.play.interact();h.advance(700);
  h.play.input(1,0);for(let n=0;n<20;n++)h.advance(50);h.play.reset();
  const before={x:h.play.state.x,y:h.play.state.y};await h.play.leave();assert.equal(h.play.state.phase,'return');
  assert.equal(h.play.state.x,before.x);assert.equal(h.play.state.y,before.y);assert.equal(h.play.state.round?.id,undefined);
  assert.equal(h.play.needsFrame(),false,'abandoning an idle lap does not create a RAF loop');
  for(let n=0;n<100;n++){
   const p=geometry.placeWorldPoint(kind,h.play.state,true),entry=geometry.placeWorldPoint(kind,{x:geometry.placeGeometry(kind).entry[0],y:geometry.placeGeometry(kind).entry[1]},true);
   if(Math.hypot(entry.x-p.x,entry.y-p.y)<5)break;
   h.play.input(entry.x-p.x,entry.y-p.y);h.advance(50);
  }
  h.play.reset();await h.play.interact();assert.equal(h.play.state.phase,'walk');
  assert.deepEqual(h.calls.map(c=>c.name),kind==='boat'?[]:['jr_leisure_start'],'exit never awards a lap');
 }
});

test('pool camera and boarding use the same enlarged world for land, water, and public peer poses',async()=>{
 const h=harness('pool');h.dock();const land=h.leisurePose(h.play.state,0,h.clock());
 await h.play.interact();assert.equal(h.leisurePose(h.play.state,0,h.clock()).x,land.x);
 h.advance(700);const pose=h.leisurePose(h.play.state,0,h.clock()),publicPose=h.leisurePose({...h.play.state,heading:undefined},0,h.clock(),true);
 assert.equal(pose.x,183);assert.equal(pose.y,260);assert.equal(publicPose.x,pose.x);assert.equal(publicPose.y,pose.y);
 for(const [width,height] of [[390,844],[1440,900],[844,390]]){
  const c=h.placeCamera(width,height,pose,'pool'),p=h.placePoint(c,(pose.x-c.x)*c.scale,(pose.y-c.y)*c.scale);
  assert.ok(c.x>=0&&c.y>=0&&c.x+c.viewWidth<=640+.0001&&c.y+c.viewHeight<=400+.0001);
  assert.ok(Math.hypot(p.x-pose.x,p.y-pose.y)<1e-8);
 }
});

test('the hull stays at its safe mooring throughout boarding while only the avatar crosses the deck edge',async()=>{
 const h=harness(),ctx=new Proxy({}, {get:()=>()=>{},set:()=>true});h.dock();await h.play.interact();
 for(const elapsed of [0,140,280,420,560,650]){
  const pose=h.leisurePose(h.play.state,elapsed,100000+elapsed);
  h.drawPlaceActor(ctx,'boat',h.play.state,pose,elapsed,{}, {},{local:true});
 }
 assert.ok(h.boats.length>=6);
 for(const boat of h.boats){assert.equal(boat.x,132);assert.equal(boat.y,130,'boarding cannot drag the hull across the pier');}
});


test('disembarking keeps the boat at its actual landing pose, including the next boarding',async()=>{
 const h=harness(),ctx=new Proxy({}, {get:()=>()=>{},set:()=>true});h.dock();await h.play.interact();h.advance(700);
 h.play.input(1,-1);for(let n=0;n<3;n++)h.advance(50);h.play.reset();
 const expected=geometry.placeWorldPoint('boat',h.play.state,true),heading=h.play.state.heading;
 await h.play.leave();assert.equal(h.play.state.phase,'walk');
 for(const elapsed of [0,350,700]){
  const pose=h.leisurePose(h.play.state,elapsed,h.clock()+elapsed);h.drawPlaceActor(ctx,'boat',h.play.state,pose,elapsed,{}, {},{local:true});
  assert.ok(Math.hypot(h.boats.at(-1).x-expected.x,h.boats.at(-1).y-expected.y)<.01,'hull never jumps back to the original mooring');
  assert.equal(h.boats.at(-1).heading,heading);
 }
 h.advance(700);await h.play.interact();
 const next=geometry.placeWorldPoint('boat',h.play.state,true);assert.ok(Math.hypot(next.x-expected.x,next.y-expected.y)<.01);
});
