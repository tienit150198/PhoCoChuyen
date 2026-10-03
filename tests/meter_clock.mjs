// Unit test of the clocks behind the live bars (stop-on-tap meters):
// - public/js/api.js clockSample: the page's estimate of the server clock leaves out the time a request spent on
//   the server and keeps the reading with the shortest network trip (a busy server no longer tilts the bars);
// - public/js/v4/dayclock.js daylight: the evening fade never keeps the hidden room repainting under a sheet.
// Run by tests/test_meter_lag.py (node tests/meter_clock.mjs); exits non-zero on failure.
import assert from 'node:assert/strict';
import {clockSample,CLOCK_AGE,CLOCK_KEEP} from '../public/js/api.js';
import {daylight,lightAt} from '../public/js/v4/dayclock.js';

const near=(a,b,eps=1e-6,msg='')=>assert.ok(Math.abs(a-b)<=eps,`${msg} ${a} ≈ ${b}`);

{ // The server is 100 s ahead of the phone; 50 ms each way; the command waited 900 ms on the server (a lock).
  const S=[],sent=1_000_000,recv=sent/1000+100+0.05,time=recv+0.9,got=sent+50+900+50;
  near(clockSample(S,sent,got,time,recv),100,1e-9,'server wait left out');
  // The way it was read before (no server_recv: an older server): leaned by half the wait.
  near(clockSample([],sent,got,time,undefined),100.45,1e-9,'older server: the old estimate');
}

{ // Of the recent readings the shortest network trip wins: a slow uplink (1.5 s) does not tilt the clock.
  const S=[];let t=2_000_000;
  const read=(up,down,stay=0.02)=>{const recv=t/1000+up+100,time=recv+stay,got=t+(up+stay+down)*1000;const o=clockSample(S,t,got,time,recv);t=got+500;return o;};
  near(read(0.06,0.06),100,1e-9,'symmetric');
  near(read(1.5,0.06),100,1e-9,'a slow way in: the earlier, shorter trip still wins');
  near(read(0.05,0.03),100.01,1e-9,'a shorter trip: its own (small) lean');
  assert.equal(S.length,3);
  // A tie keeps the newer reading.
  const T=[];near(clockSample(T,0,125,0.5625,0.5),0.46875);near(clockSample(T,1000,1125,2.5625,2.5),1.46875,1e-9,'tie: newer');
}

{ // Readings age out (CLOCK_AGE) and at most CLOCK_KEEP are kept; the newest always stays.
  const S=[];
  clockSample(S,0,40,100.02,100.0);   // a fine reading: trip 20 ms
  for(let i=1;i<=CLOCK_KEEP+3;i++)clockSample(S,i*1000,i*1000+300,100+i+0.25,100+i+0.1);
  assert.equal(S.length,CLOCK_KEEP,'kept at most CLOCK_KEEP');
  const S2=[];clockSample(S2,0,40,100.02,100.0);
  const o=clockSample(S2,CLOCK_AGE+5000,CLOCK_AGE+5300,100+CLOCK_AGE/1000+5+0.25,100+CLOCK_AGE/1000+5+0.1);
  assert.equal(S2.length,1,'an old reading ages out');
  near(o,100.025,1e-9,'the newest is used');   // ((225.25-0.15-125)+(225.25-125.3))/2
}

{ // A phone whose own clock is 5 s fast: the estimate holds it to the server's.
  const S=[],skew=5000,sent=3_000_000+skew,recv=(sent-skew)/1000+0.04,time=recv+0.01,got=sent+90;
  near((got/1000)+clockSample(S,sent,got,time,recv),time+0.04,1e-9,'phone clock + offset = server clock');
}

// daylight: a fake world and canvas.
const ctx=new Proxy({},{get:(o,k)=>k in o?o[k]:()=>({addColorStop(){}}),set:(o,k,v)=>{o[k]=v;return true;}});
let wall=0;Object.defineProperty(globalThis,'performance',{value:{now:()=>wall*1000},configurable:true,writable:true});
const world=(minute,covered)=>({ctx,c:{day_clock:{minute}},career:'clothing',_time:7,reduced:false,wakes:0,covered:()=>covered,
  wake(){this.wakes++;},outdoor:()=>false,plan:()=>({}),hotspots:[],isPortrait:()=>false,offset:{x:0,y:0},scale:1,width:100,height:100,scene:()=>({id:'shop'})});
const noon=12*60,night=21*60;
assert.notEqual(lightAt(noon).alpha,lightAt(night).alpha,'noon and night differ');
{ // Under a sheet the world's time stands still: the light is set at once, nothing asks for another frame.
  const w=world(noon,false);daylight(w);assert.equal(w.wakes,0);
  w.c.day_clock.minute=night;w.covered=()=>true;
  for(let i=0;i<5;i++){wall+=1/60;daylight(w);}
  assert.equal(w.wakes,0,'no repaint loop under a sheet');
  near(w._light.alpha,lightAt(night).alpha,1e-9,'the light is the target');
}
{ // In view the fade glides on the wall clock and ends, even when the world's own time stands still (paused).
  const w=world(noon,false);daylight(w);
  w.c.day_clock.minute=night;let frames=0;
  while(frames<2000){wall+=1/60;const before=w.wakes;daylight(w);frames++;if(w.wakes===before)break;}
  assert.ok(frames>10&&frames<600,`the fade ends (${frames} frames)`);
  near(w._light.alpha,lightAt(night).alpha,1e-9,'ends on the target');
}
console.log('meter clock ok');
