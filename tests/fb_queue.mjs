// Backlog (06/10): fb_reply bounced with 409 revision_conflict (about 29 sessions: trà sữa, quần áo, cà phê, thư ký,
// homestay). The reviewer's AI answer (/api/ai/feedback, sent 1.6 s after fb_reply) and the reworded review
// (/api/ai/review, sent when a review is opened) save after the model has written and bump the revision; they went
// off the command queue, so their write landed under a tap already on its way. They now take their place in the
// queue (api.js aiQueued, as the teacher's voice) and the taps after them wait until they land, AI_WAIT at most.
// Run by tests/test_fb_queue.py.
import assert from 'node:assert/strict';
import {readFileSync,readdirSync,statSync} from 'node:fs';
import {GameAPI,AI_WAIT,aiQueued,CONFLICT_RETRIES} from '../public/js/api.js';

const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const ok=data=>new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}});
// A tiny server: one save with a revision; a command against an older revision is a 409; an AI write answers when
// the test lets it (the model writing) and saves then.
const srv={revision:1,commands:[],ai:[],conflicts:0};
const state=()=>({current:'milk_tea',focus:'milk_tea',settings:{lang:'vi',aiConsent:true}});
globalThis.fetch=async(url,init={})=>{
  const body=init.body?JSON.parse(init.body):null;
  if(url==='/api/command'){
    srv.commands.push(body);
    if(body.expected_revision!==srv.revision){srv.conflicts++;
      return new Response(JSON.stringify({error:'conflict',code:'revision_conflict',state:state(),revision:srv.revision}),{status:409,headers:{'Content-Type':'application/json'}});}
    srv.revision++;return ok({state:state(),revision:srv.revision,result:{message:''}});
  }
  if(url==='/api/state')return ok({state:state(),revision:srv.revision});
  if(url==='/api/ai/feedback'||url==='/api/ai/review'){
    let land;const answered=new Promise(r=>{land=r;});srv.ai.push({url,body,land});
    const how=await answered;
    if(how==='fail')return new Response(JSON.stringify({error:'x'}),{status:400,headers:{'Content-Type':'application/json'}});
    srv.revision++;return ok({state:state(),revision:srv.revision,result:{message:'Cảm ơn quán nha'},mode:'ai'});
  }
  throw new Error('unexpected '+url);
};
const a=new GameAPI();a.state=state();a.revision=1;a.csrf='c';
const free=q=>Promise.race([q.then(()=>'free'),sleep(40).then(()=>'held')]);

assert.ok(AI_WAIT>=2000&&AI_WAIT<=5000,'a usual model answer lands first; a slow one never holds the taps for long');

// 1. fb_reply lands, then the reviewer's answer is written (the model takes seconds): the next tap waits for it and
//    goes against the revision it wrote (before: 409 revision_conflict on that tap).
await a.command('fb_reply',{post:'p1',text:'Xin lỗi bạn',offer:'none',tone:'sorry'});
assert.equal(a.revision,2);
const fb=a.aiFeedback('p1');await sleep(0);
assert.equal(srv.ai.length,1);assert.equal(srv.ai[0].url,'/api/ai/feedback');assert.deepEqual(srv.ai[0].body,{career:'milk_tea',post:'p1'});
const tap=a.command('tea_prepare',{task:'t1'});
await sleep(200);
assert.equal(srv.commands.length,1,'the tap after the AI write waits for it');
assert.equal(await free(a.queue),'held');
srv.ai[0].land('ok');
assert.equal((await fb).result.message,'Cảm ơn quán nha');
await tap;
assert.equal(srv.commands[1].expected_revision,3,'the tap goes with the revision the AI wrote');
assert.equal(srv.conflicts,0,'no 409');assert.equal(a.revision,4);

// 2. Opening a review rewords it (/api/ai/review): same queue, and a tap queued before it goes first.
const before=a.command('tea_prepare',{task:'t2'});
const rv=a.aiReview('p2');
await before;await sleep(0);
assert.equal(srv.commands.at(-1).expected_revision,4,'the earlier tap went first');
assert.equal(srv.ai.length,2,'then the review is sent');assert.equal(srv.ai[1].url,'/api/ai/review');
const reply=a.command('fb_reply',{post:'p2',text:'Cảm ơn bạn',offer:'none',tone:'free'});
await sleep(100);assert.equal(srv.commands.length,3,'fb_reply waits behind the review');
srv.ai[1].land('ok');await rv;await reply;
assert.equal(srv.commands.at(-1).action,'fb_reply');assert.equal(srv.commands.at(-1).expected_revision,6);
assert.equal(srv.conflicts,0,'no 409');

// 3. A slow model: after the cap the taps go (the screen never freezes).
a.aiWait=60;
const slow=a.aiFeedback('p3');await sleep(0);
const t0=Date.now();await a.command('tea_prepare',{task:'t3'});
assert.ok(Date.now()-t0<1000,'the cap releases the tap');
srv.ai[2].land('ok');await slow;
assert.equal(srv.conflicts,0);
// An AI answer older than a state a tap adopted meanwhile is left out (the screen never steps back).
{
  const b=new GameAPI();b.state=state();b.revision=10;b.csrf='c';let go;
  b.post=()=>new Promise(r=>{go=()=>r({state:{...state(),old:true},revision:10});});
  const w=b.aiReview('p4');await sleep(0);
  b.accept({state:state(),revision:11});   // a tap landed while the model wrote (after the cap)
  go();await w;
  assert.equal(b.revision,11);assert.equal(b.state.old,undefined,'the older AI answer is left out');
}

// 4. A failed AI write frees the queue at once and answers {mode:'none'} (the reply already landed; nothing to show).
a.aiWait=undefined;
const bad=a.aiFeedback('p5');await sleep(0);
srv.ai[3].land('fail');
assert.deepEqual(await bad,{mode:'none'});
assert.equal(await free(a.queue),'free');

// 5. aiQueued itself: the cap releases the taps even while the write is still out; the write's own promise is returned.
{
  const q={queue:Promise.resolve()};let out;const pending=new Promise(r=>{out=r;});
  const job=aiQueued(q,()=>pending,150);
  assert.equal(await free(q.queue),'held');
  await sleep(150);assert.equal(await free(q.queue),'free','the cap releases the taps');
  out('done');assert.equal(await job,'done');
}

// 7. B4 (07/10, 29 → 148 refusals): the save moves under a reply more than once (a model slower than AI_WAIT, then
//    another write). It is sent again up to CONFLICT_RETRIES times against the fresh state, never dropped after one.
assert.equal(CONFLICT_RETRIES,3);
{
  const prev=globalThis.fetch,s={revision:1,sent:[],busy:0};
  const conflict=()=>new Response(JSON.stringify({error:'conflict',code:'revision_conflict',state:state(),revision:s.revision}),{status:409,headers:{'Content-Type':'application/json'}});
  globalThis.fetch=async(url,init={})=>{
    const body=JSON.parse(init.body);
    if(url!=='/api/command')throw new Error('unexpected '+url);
    s.sent.push({...body,at:Date.now()});
    if(s.busy>0){s.busy--;s.revision++;return conflict();}   // another write landed just before this one
    if(body.expected_revision!==s.revision)return conflict();
    s.revision++;return ok({state:state(),revision:s.revision,result:{message:'Đã gửi'}});
  };
  const b=new GameAPI();b.state=state();b.revision=1;b.csrf='c';
  s.busy=3;   // three conflicts in a row: the 4th try lands (before: dropped after the 2nd)
  const r=await b.command('fb_reply',{post:'q1',text:'Dạ em xin lỗi',offer:'none',tone:'sorry'});
  assert.equal(r.message,'Đã gửi');assert.equal(s.sent.length,4);
  assert.equal(new Set(s.sent.map(x=>x.request_id)).size,4,'each try is a new request against the fresh revision');
  assert.deepEqual(s.sent.map(x=>x.expected_revision),[1,2,3,4]);
  assert.ok(s.sent[1].at-s.sent[0].at>=150,'a short backoff before trying again');
  // Still moving after the retries: dropped, but marked (quiet for every other caller; conflict: "Gửi lại" offered).
  s.sent.length=0;s.busy=9;
  const e=await b.command('fb_reply',{post:'q2',text:'Dạ',offer:'none',tone:'free'}).then(()=>null,x=>x);
  assert.ok(e&&e.quiet&&e.conflict,'error.quiet + error.conflict');assert.equal(s.sent.length,1+CONFLICT_RETRIES);
  globalThis.fetch=prev;
}
// 8. A conflict while an AI write is on the wire (the model slower than AI_WAIT): the next try waits until it answers
//    (AI_SETTLE at most) and goes against the revision it wrote, so one conflict is all.
{
  const prev=globalThis.fetch,s={revision:1,sent:[],conflicts:0,aiAt:0};let save;
  globalThis.fetch=async(url,init={})=>{
    const body=JSON.parse(init.body);
    if(url==='/api/ai/feedback'){await new Promise(r=>{save=r;});s.revision++;const rev=s.revision;await sleep(300);s.aiAt=Date.now();
      return ok({state:state(),revision:rev,result:{message:'Ok quán'},mode:'ai'});}
    s.sent.push({...body,at:Date.now()});
    if(body.expected_revision!==s.revision){s.conflicts++;return new Response(JSON.stringify({error:'conflict',code:'revision_conflict',state:state(),revision:s.revision}),{status:409,headers:{'Content-Type':'application/json'}});}
    s.revision++;return ok({state:state(),revision:s.revision,result:{message:'Đã gửi'}});
  };
  const b=new GameAPI();b.state=state();b.revision=1;b.csrf='c';b.aiWait=40;
  const w=b.aiFeedback('q3');await sleep(60);   // past the cap: the queue lets the reply go
  save();await sleep(0);   // the model saves (revision 2); its answer comes 300 ms later
  const reply=b.command('fb_reply',{post:'q3',text:'Cảm ơn bạn',offer:'none',tone:'free'});
  const r=await reply;await w;
  assert.equal(r.message,'Đã gửi');assert.equal(s.conflicts,1,'one conflict, then it lands');
  assert.equal(s.sent.length,2);assert.ok(s.sent[1].at>=s.aiAt,'the retry waited for the AI answer');
  assert.equal(s.sent[1].expected_revision,2);assert.equal(b.revision,3);
  globalThis.fetch=prev;
}

// 6. Nothing else writes these routes off the queue: only api.js names them.
const walk=d=>readdirSync(d).flatMap(f=>{const p=d+'/'+f;return statSync(p).isDirectory()?walk(p):p.endsWith('.js')?[p]:[];});
const root=new URL('../public/js',import.meta.url).pathname;
const off=walk(root).filter(p=>!p.endsWith('/api.js')&&/\/api\/ai\/(feedback|review)\b/.test(readFileSync(p,'utf8')));
assert.deepEqual(off,[],'the reviews\' AI writes go through api.aiFeedback / api.aiReview');
console.log('fb_queue ok');
