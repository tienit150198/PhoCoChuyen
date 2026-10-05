import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync(new URL('../public/js/pixel/places.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
function harness(kind='boat',command){
 let now=100000;const calls=[];
 const cmd=command||(async(name,p)=>{calls.push({name,p});if(name==='jr_leisure_start')return {leisure_round:{id:'round',kind,now:now/1000,bite_at:now/1000+3,bite_window:1.6,entry:[104,150],checkpoints:[[144,62],[260,70],[252,142],[104,150]],min_seconds:6}};return {message:'Đã lưu',next:p.index+1,leisure:{boat_laps:1}};});
 const context=vm.createContext({console,Math,Date,Set,Map});vm.runInContext(source+'\nglobalThis.exports={createPixelPlay,walkablePlace,createPlaceLifecycle,leisurePose,placeCamera,placePoint};',context);
 const play=context.exports.createPixelPlay(kind,{now:()=>now,command:cmd});
 return {play,calls,...context.exports,clock:()=>now,advance(ms){now+=ms;play.step(ms/1000);}};
}
test('walking respects shore and dock; activity requires approaching it',async()=>{
 const h=harness();await h.play.interact();assert.equal(h.calls.length,0);
 assert.equal(h.walkablePlace('boat',220,100,false),false);
 assert.equal(h.walkablePlace('boat',84,154,false),true);
 h.play.input(0,-1);for(let i=0;i<18;i++)h.advance(50);h.play.input(0,0);
 assert.ok(h.play.state.y<166);await h.play.interact();assert.equal(h.calls[0].name,'jr_leisure_start');
 assert.equal(h.play.state.phase,'boat');
});
test('fishing has cast wait bite timed reel and real save command',async()=>{
 const h=harness('fishing');h.play.state.x=84;h.play.state.y=154;
 await h.play.interact();assert.equal(h.play.state.phase,'waiting');
 await h.play.interact();assert.equal(h.calls.length,1);
 h.advance(3200);assert.equal(h.play.state.phase,'bite');
 await h.play.interact();assert.equal(h.calls.at(-1).name,'jr_leisure_finish');assert.equal(h.play.state.phase,'walk');
});
test('boat checkpoints cannot be skipped locally and completed lap can disembark',async()=>{
 const h=harness();h.play.state.x=84;h.play.state.y=154;await h.play.interact();
 h.play.state.x=252;h.play.state.y=142;h.advance(50);await Promise.resolve();assert.equal(h.calls.length,1);
 for(const [x,y] of h.play.state.round.checkpoints){h.play.state.x=x;h.play.state.y=y;h.advance(1000);await new Promise(resolve=>setImmediate(resolve));}
 assert.equal(h.play.state.next,4);
 await h.play.interact();assert.equal(h.calls.at(-1).name,'jr_leisure_finish');assert.equal(h.play.state.phase,'return');
 await h.play.interact();assert.equal(h.play.state.phase,'walk');assert.equal(h.play.state.y,174);
});

for(const kind of ['boat','pool'])for(const code of ['expired','bad_round']){
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
  h.play.state.x=84;h.play.state.y=154;await h.play.interact();h.advance(700);
  steerTo(checkpoint,4);await new Promise(resolve=>setImmediate(resolve));
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
 let resolve;const h=harness('boat',()=>new Promise(r=>{resolve=r;}));h.play.state.x=84;h.play.state.y=154;
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
 const h=harness('pool');h.play.state.x=84;h.play.state.y=154;await h.play.interact();
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
 const h=harness();h.play.state.x=84;h.play.state.y=154;await h.play.interact();
 assert.equal(h.play.state.action.kind,'board');h.play.input(1,0);h.advance(350);
 const pose=h.leisurePose(h.play.state,0,h.clock());assert.ok(pose.x>84&&pose.x<104);assert.equal(h.play.state.x,104);
 h.advance(350);assert.equal(h.play.state.action,null);h.advance(50);assert.ok(h.play.state.x>104);
 h.play.state.phase='return';h.play.state.x=104;h.play.state.y=150;await h.play.interact();
 assert.equal(h.play.state.action.kind,'exit');const start=h.leisurePose(h.play.state,0,h.clock());assert.equal(start.x,104);assert.equal(start.y,150);
 h.advance(700);assert.equal(h.play.state.action,null);assert.equal(h.play.state.y,174);
});

test('fishing shows a caught fish only after server success and releases the action for another cast',async()=>{
 const h=harness('fishing');h.play.state.x=84;h.play.state.y=154;await h.play.interact();assert.equal(h.play.state.action.kind,'cast');
 h.advance(3200);await h.play.interact();assert.equal(h.play.state.action.kind,'caught');
 assert.equal(h.leisurePose(h.play.state,0,h.clock()).fishingPose,'reel','a quick server answer still shows the jerk before the catch');
 assert.equal(h.leisurePose(h.play.state,0,h.clock()+700).fishingPose,'caught');
 const count=h.calls.length;await h.play.interact();assert.equal(h.calls.length,count);h.advance(1900);assert.equal(h.play.state.action,null);
 await h.play.interact();assert.equal(h.calls.at(-1).name,'jr_leisure_start');
 const failed=harness('fishing',async action=>{if(action==='jr_leisure_start')return {leisure_round:{id:'round',now:100,bite_at:103,bite_window:1.6}};throw Object.assign(new Error('Cá đã nhả mồi'),{data:{code:'missed'}});});
 failed.play.state.x=84;failed.play.state.y=154;await failed.play.interact();failed.advance(3200);await failed.play.interact();
 assert.equal(failed.play.state.action,null);assert.equal(failed.play.state.phase,'walk');assert.equal(failed.leisurePose(failed.play.state,0,failed.clock()).fishingPose,'ready');
});
