// Unit test of the teacher's class chat sends (public/js/v4/teach-tour.js: classSend, classVoice, clReply) and of the
// api binding (experience-ui.js teachTour). Run by tests/test_teacher_care.py (node tests/class_send.mjs).
// "Ad sao cái chỗ trả lời học sinh á mình bấm rồi mà bị đứng lun ạ" (chat 03/10): the model's wait (op 'voice', or a
// reply voiced inline) sat in the command queue and disabled the answers, and after a reload the module had no api.
// Backlog 3 #8 (06/10): fully off the queue, the voice's save write landed under taps already on their way (409
// revision_conflict on lesson_next / lesson_call, 15 sessions). The voice now waits its turn in the queue and holds the
// taps after it until it lands, VOICE_WAIT at most.
import assert from 'node:assert/strict';
const TT=await import('../public/js/v4/teach-tour.js');
const {teachTour}=await import('../public/js/experience-ui.js');
globalThis.document??=new EventTarget();  // experience-ui.js announces the lazy module on document

const sleep=ms=>new Promise(r=>setTimeout(r,ms));
class FakeApi extends EventTarget{
  constructor(){super();this.queue=Promise.resolve();this.revision=5;this.accepted=0;this.ai={configured:true};this.state={settings:{aiConsent:true}};this.posts=[];this.adopted=[];}
  post(url,body){let done;const p=new Promise(r=>{done=r;});this.posts.push({url,body,done});return p;}
  accept(data,since){if(since!==undefined&&since!==this.accepted&&typeof data?.revision==='number'&&data.revision<this.revision)return false;this.accepted++;this.revision=data.revision;this.adopted.push(data.revision);return true;}
}
const api=new FakeApi();
assert.equal(TT.classAiOn(),false,'nothing bound yet: a fresh page before any state was adopted');
await teachTour(api);
assert.equal(TT.classAiOn(),true,'loading the lesson module with the api binds it (a reload mid-lesson: the first answer tap works)');

const key='ask:t1',body={kind:'pupil',pupil:'minh',task:'t1'};
const chips=()=>TT.clReply(key,body,[{id:'a',label:'A'}],200,'Trả lời…');

// The question is being reworded (the model takes seconds): the taps after it wait (VOICE_WAIT at most), the answers
// wait VOICE_HOLD at most.
assert.ok(TT.VOICE_WAIT>TT.VOICE_HOLD&&TT.VOICE_WAIT<=5000,'a slow model never holds the class for long');
const t0=Date.now(),voice=TT.classSend({...body,op:'voice'},key,'');
await sleep(0);
assert.equal(api.posts.length,1);assert.equal(api.posts[0].body.op,'voice');assert.equal(api.posts[0].body.later,undefined);
assert.equal(await Promise.race([api.queue.then(()=>'free'),sleep(50).then(()=>'held')]),'held','a voice on its way holds the taps after it: its save write lands first');
assert.match(chips(),/ disabled/,'right away the answers wait for the question');
assert.equal(TT.classVoicing(key),true);assert.equal(TT.classWaiting(key),false,'the "Trả lời" step stays the next step');
await sleep(TT.VOICE_HOLD+60);
assert.doesNotMatch(chips(),/ disabled/,'after VOICE_HOLD the scripted question and the answers show');
assert.equal(TT.classVoicing(key),false);

// The player answers while the question is still being reworded (a slow model): the reply waits until VOICE_WAIT after
// the voice was sent, then goes (queue, later:true) and lands fast.
const reply=TT.classSend({...body,option:'a',op:'reply'},key,'A');
await sleep(0);
assert.equal(api.posts.length,1,'the reply waits behind the voice');
await sleep(Math.max(0,TT.VOICE_WAIT-(Date.now()-t0))+60);
const r=api.posts[1];assert.equal(r.body.op,'reply');assert.equal(r.body.later,true);assert.equal(r.body.expected_revision,5);assert.equal(r.body.option,'a');
assert.equal(TT.classWaiting(key),true);assert.match(chips(),/ disabled/,'one reply at a time');
assert.equal(await TT.classSend({...body,option:'a',op:'reply'},key,'A'),null,'a second reply while one is on its way is not sent');
r.done({state:{},revision:6,reason:'later',result:{message:''}});
assert.equal((await reply).revision,6);
assert.deepEqual(api.adopted,[6]);
await sleep(0);
// Then the reaction is reworded, in the queue: only what the server needs, no answer repeated.
const react=api.posts[2];
assert.deepEqual(react.body.op,'voice');assert.equal(react.body.task,'t1');assert.equal(react.body.option,undefined);assert.equal(react.body.text,undefined);
assert.equal(TT.classWaiting(key),false);
// The reaction's "typing…" stands where its scripted words are.
const lines=[{who:'pupil',text:'Q',mode:'scripted'},{who:'teacher',text:'A',mode:'scripted'},{who:'pupil',text:'Dạ.',mode:'scripted'}];
assert.match(TT.clBubbles(lines,key),/typing/);assert.doesNotMatch(TT.clBubbles(lines,key),/Dạ\./);
// A slow model (up to 25 s) no longer keeps the class on "typing…": after VOICE_HOLD the scripted reaction shows.
await sleep(TT.VOICE_HOLD+60);
assert.match(TT.clBubbles(lines,key),/Dạ\./,'after VOICE_HOLD the scripted reaction shows while the AI wording is on its way');
assert.doesNotMatch(TT.clBubbles(lines,key),/typing/);
assert.doesNotMatch(chips(),/ disabled/,'the answers never wait for a reaction being reworded');
// A tap landed meanwhile (revision 7): the older question voice answer (6) is not adopted over it.
api.revision=7;api.accepted++;
api.posts[0].done({state:{},revision:6,mode:'ai'});await voice;
assert.deepEqual(api.adopted,[6],'an answer older than the state on screen is left out');
react.done({state:{},revision:8,mode:'ai'});await sleep(0);await sleep(0);
assert.deepEqual(api.adopted,[6,8]);
assert.match(TT.clBubbles(lines,key),/Dạ\./,'the reaction shows once its voice is back');
assert.doesNotMatch(TT.clBubbles(lines,key),/typing/);

// An older server (no later): it voiced the reaction inline, so no second call.
const n=api.posts.length,old=TT.classSend({...body,option:'b',op:'reply'},'ask:t2','B');await sleep(0);
api.posts[n].done({state:{},revision:9,mode:'ai',reason:null});await old;await sleep(0);
assert.equal(api.posts.length,n+1);

// A refused reply shows why and frees the answers.
const bad=TT.classSend({...body,option:'c',op:'reply'},'ask:t3','C');await sleep(0);
api.posts[n+1].done(Promise.reject(Object.assign(new Error('Minh đã hạ tay.'),{status:400})));
assert.equal(await bad,null);
assert.match(TT.clBubbles([],'ask:t3'),/Minh đã hạ tay/);
assert.doesNotMatch(TT.clReply('ask:t3',body,[{id:'a',label:'A'}],200,'x'),/ disabled/);

// A usual model answer lands within VOICE_WAIT: the tap waiting behind it goes right then, against the voice's
// revision (no 409), and well before VOICE_WAIT.
{
  const k='ask:t9',start=Date.now(),v=TT.classSend({...body,task:'t9',op:'voice'},k,'');await sleep(0);
  const vp=api.posts.at(-1);assert.equal(vp.body.op,'voice');
  let sentAt=null;const tap=api.queue.then(()=>{sentAt=api.revision;});api.queue=tap;   // what api.command does
  await sleep(300);assert.equal(sentAt,null,'the tap waits for the voice');
  vp.done({state:{},revision:21,mode:'ai'});await v;await tap;
  assert.equal(sentAt,21,'the tap goes with the revision the voice wrote');
  assert.ok(Date.now()-start<TT.VOICE_WAIT,'released by the landing, not the cap');
}
// A voice that fails frees the queue too.
{
  const v=TT.classSend({...body,task:'t10',op:'voice'},'ask:t10','');await sleep(0);
  api.posts.at(-1).done(Promise.reject(Object.assign(new Error('x'),{status:400})));
  assert.equal(await v,null);
  assert.equal(await Promise.race([api.queue.then(()=>'free'),sleep(50).then(()=>'held')]),'free');
}
// clVoiceQueued: after `wait` the taps go even if the voice is still out.
{
  const q={queue:Promise.resolve()};let out;const pending=new Promise(r=>{out=r;});
  const job=TT.clVoiceQueued(q,()=>pending,30);
  assert.equal(await Promise.race([q.queue.then(()=>'free'),sleep(10).then(()=>'held')]),'held');
  assert.equal(await Promise.race([q.queue.then(()=>'free'),sleep(80).then(()=>'held')]),'free','the cap releases the taps');
  out('done');assert.equal(await job,'done');
}
console.log('class_send ok');
