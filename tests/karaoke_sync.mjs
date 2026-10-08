// 🎙️ Voice and music together (07/10 "bị delay xíu"): the listener's video target while a live voice plays
// (public/js/v4/karaoke-mic.js followTarget, voiceLag, lagStep, bucket). Run by tests/test_karaoke_mic.py.
import assert from 'node:assert/strict';
import {followTarget,voiceLag,lagStep,bucket,LAG,mixPlan,musicMove,MIX} from '../public/js/v4/karaoke-mic.js';
import {run,SCENARIOS} from './karaoke_sim.mjs';

const near=(a,b,eps=1e-9,msg)=>assert.ok(Math.abs(a-b)<=eps,`${msg||''} ${a} ≉ ${b}`);
const vt={vt:42,at:1000};

// following: the singer's video time, moved on by the time since (server clock), minus the voice's delay
let r=followTarget({clock:43.9,vt,now:1001.5,age:1.5,lag:.4,voice:true});
assert.equal(r.voice,true);near(r.t,42+1.5-.4);

// the fallback: the shared clock, exactly as without a mic
for(const [why,o] of [
  ['no voice playing',{voice:false}],
  ['no video time yet',{vt:null}],
  ['stale (3 s or more)',{age:LAG.fresh}],
  ['stale',{age:12}],
  ['negative age',{age:-1}],
  ['age unknown',{age:NaN}],
  ['broken frame',{vt:{vt:'42',at:1000}}],
  ['broken frame at',{vt:{vt:42}}],
  ['far from the clock',{clock:43.9-LAG.span-1}],
  ['no clock reading',{now:undefined}],
]){
  const x=followTarget({clock:43.9,vt,now:1001.5,age:1.5,lag:.4,voice:true,...o});
  assert.deepEqual(x,{t:o.clock??43.9,voice:false},why);
}
// a listener clock behind the server's: never moves the singer's time backwards; far ahead: bounded by the age
near(followTarget({clock:42,vt,now:999,age:.2,lag:0,voice:true}).t,42);
near(followTarget({clock:42,vt,now:1009,age:.5,lag:0,voice:true}).t,42+.5+LAG.fresh);
near(followTarget({clock:42,vt,now:1001,age:1,lag:undefined,voice:true}).t,43,1e-9,'no lag known: none taken off');
// the singer's video nudged (their own sync at 1.05 / 0.95) runs on at that rate; a nonsense rate counts as 1
near(followTarget({clock:44,vt:{...vt,r:1.05},now:1002,age:2,lag:0,voice:true}).t,42+2*1.05);
near(followTarget({clock:44,vt:{...vt,r:.95},now:1002,age:2,lag:.3,voice:true}).t,42+2*.95-.3);
for(const r of [5,0,-1,'1.05',NaN])near(followTarget({clock:44,vt:{...vt,r},now:1002,age:2,lag:0,voice:true}).t,44,1e-9,`rate ${r}`);

// the voice's delay: capture/encode + my jitter buffer + half of each round trip, within 0..LAG.max
near(voiceLag({}),LAG.base+LAG.guess,1e-9,'nothing measured yet');
near(voiceLag({jb:.25,rtt:.08},.06),.04+.25+.07);
near(voiceLag({jb:.25,rtt:.08}),.04+.25+.08,1e-9,'the singer\'s round trip unknown: as mine');
near(voiceLag({jb:.25,rtt:.08},-1),.04+.25+.08,1e-9,'a nonsense round trip: as mine');
near(voiceLag({jb:3,rtt:2},2),LAG.max);
near(voiceLag(null),LAG.base+LAG.guess);
assert.ok(voiceLag({jb:0,rtt:0},0)>=0);

// getStats into the estimate: Δ jitterBufferDelay / Δ jitterBufferEmittedCount, smoothed
let s=lagStep({},{jbd:4800,jbn:24000,rtt:.1});
near(s.jb,.2,1e-9,'first reading: since subscribed');near(s.rtt,.1);
s=lagStep(s,{jbd:4800+.3*48000,jbn:72000,rtt:.2});
near(s.jb,.2+(.3-.2)*LAG.a,1e-9,'smoothed');near(s.rtt,.1+(.2-.1)*LAG.a);
const keep=s.jb;
s=lagStep(s,{jbd:1,jbn:10});            // counters went back (a new receiver): rebase, keep the estimate
near(s.jb,keep);assert.equal(s.jbn,10);
s=lagStep(s,{jbd:1,jbn:10});            // nothing played since: nothing learned
near(s.jb,keep);
assert.deepEqual(lagStep(s,null),s);
assert.deepEqual(lagStep(s,{jbd:undefined,jbn:undefined,rtt:undefined}),s,'Safari without the counters: unchanged');
assert.equal(lagStep({},{jbd:9e9,jbn:1}).jb,undefined,'an absurd reading is dropped');

// end to end: with the delay measured right, the listener's music is where the singer's was when they sang
// what the listener hears now, whatever the singer's own drift from the shared clock
for(const drift of [-.35,0,.3])for(const L of [.15,.45,.9]){
  const at0=500,S=T=>T-at0+drift;                  // the singer's video at server time T
  const st=1000,T=st+1.2;                          // kara_vt sampled at st, used 1.2 s later
  const t=followTarget({clock:T-at0,vt:{vt:S(st),at:st},now:T,age:1.2,lag:L,voice:true}).t;
  near(t,S(T-L),1e-9,`drift ${drift} lag ${L}`);
  near(Math.abs(t-(T-at0)),Math.abs(drift-L),1e-9);   // what the shared clock alone was off by
}

// the beacon's letters (its server masks digits)
assert.deepEqual([0,99,100,250,1499,1500,99999,-5].map(bucket),['a','a','b','c','o','p','p','a']);
assert.equal(bucket(NaN),'-');assert.equal(bucket(undefined),'-');
// 08/10: the singer's own output + capture latency (kara_vt `ol`) and my Web Audio path count in the delay
near(voiceLag({jb:.25,rtt:.08},.06,.18),.04+.25+.07+.18);
near(voiceLag({jb:.25,rtt:.08},.06,9),.04+.25+.07+LAG.side,1e-9,'side bounded');
near(voiceLag({jb:.25,rtt:.08},.06,-1),.04+.25+.07,1e-9,'a nonsense side: none');
near(voiceLag({jb:.25,rtt:.08},.06,NaN),.04+.25+.07);

// 🎙️ every voice with my music: the aim a margin behind the earliest lead voice, each voice held t − cur
let pl=mixPlan({cur:50,voices:[{id:'',t:50.3}],lead:['']});
near(pl.aim,50.3-MIX.margin);near(pl.d[''],.3,1e-9,'my music behind the voice: held .3 s');
pl=mixPlan({cur:50.4,voices:[{id:'',t:50.3}],lead:['']});
near(pl.d[''],0,1e-9,'a voice later than my music plays at once');
near(pl.aim,50.1);
pl=mixPlan({cur:40,voices:[{id:'',t:45}],lead:['']});
near(pl.d[''],MIX.dmax,1e-9,'held at most dmax');
pl=mixPlan({cur:50,voices:[{id:'',t:null},{id:'b',t:NaN}],lead:['','b']});
assert.deepEqual(pl,{aim:null,d:{}},'no video time: the clock, holds unchanged');
assert.deepEqual(mixPlan({cur:NaN,voices:[{id:'',t:50}],lead:['']}),{aim:null,d:{}});
// several singers: a listener follows the latest of them; every voice is held to the same music
pl=mixPlan({cur:59.8,voices:[{id:'',t:60.1},{id:'lan',t:59.95},{id:'minh',t:60.4}],lead:['','lan','minh']});
near(pl.aim,59.95-MIX.margin);
for(const [id,t] of [['',60.1],['lan',59.95],['minh',60.4]])near(59.8+pl.d[id],t,1e-9,`voice ${id} with my music`);
// a co-singer follows the stage singer only (another co-singer's voice, later, plays at once); the stage singer none
pl=mixPlan({cur:60.2,voices:[{id:'',t:60.3},{id:'minh',t:59.9}],lead:[''],margin:MIX.coMargin});
near(pl.aim,60.3-MIX.coMargin);near(pl.d[''],.1);near(pl.d.minh,0);
pl=mixPlan({cur:60.2,voices:[{id:'lan',t:59.7}],lead:[]});
assert.equal(pl.aim,null);near(pl.d.lan,0);

// my music: seek only when a lead voice would come late, or the hold would be too long; else nudge, or nothing
assert.equal(musicMove(0),'ok');assert.equal(musicMove(.1),'ok');assert.equal(musicMove(-.1),'ok');
assert.equal(musicMove(.15),'nudge');assert.equal(musicMove(-.5),'nudge');
assert.equal(musicMove(MIX.margin+MIX.late+.01),'seek','a voice late past MIX.late');
assert.equal(musicMove(-(MIX.dmax-MIX.margin-.25)-.01),'seek','a hold near dmax');
assert.equal(musicMove(NaN),'ok');

// before / after (karaoke_sim.mjs): the ear's error, voice against music, over a song
const ms=x=>`${Math.round(x*1000)} ms`;
for(const [name,o] of SCENARIOS){
  const b=run({algo:'before',...o}),a=run({algo:'after',...o});
  console.log(`  ${name}: before ${ms(b.mean)} (p95 ${ms(b.p95)}), after ${ms(a.mean)} (p95 ${ms(a.p95)})`);
  assert.ok(a.mean<.07,`${name}: after ${a.mean}`);
  assert.ok(a.mean<b.mean/3,`${name}: after ${a.mean} vs before ${b.mean}`);
}
assert.ok(run({algo:'before',L:.35}).mean>.3,'1.9.19 left a 0.35 s voice that late (no nudge, no seek under 0.6 s)');
console.log('karaoke voice sync: target, fallback, delay estimate, voice holds, several singers and beacon buckets passed');
