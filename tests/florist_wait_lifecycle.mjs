import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {getEventListeners} from 'node:events';
import vm from 'node:vm';
import ts from 'typescript';
import florist from '../public/js/careers/florist.js';
import {careerContext} from '../public/js/v4/careers.js';

// Use the real workbench action, career context and app command routing. Only
// the transport, clock and unrelated sound/toast effects are replaced.
const source=ts.createSourceFile('app.js',readFileSync(new URL('../public/js/app.js',import.meta.url),'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.JS);
const command=source.statements.find(n=>ts.isFunctionDeclaration(n)&&n.name?.text==='cmd').getText(source);
let serial=0;
function harness(t){
  const timers=new Map(),sent=[],pending=[],api=new EventTarget();let nextTimer=0;
  t.mock.method(globalThis,'setTimeout',(fn,ms)=>{const id=++nextTimer;timers.set(id,{fn,ms});return id;});
  t.mock.method(globalThis,'clearTimeout',id=>timers.delete(id));
  const task={id:`flower-${++serial}`,career:'florist',status:'in_progress',cur:0,work:{soak:1,arranged:false,foam:{start:1}}};
  api.state={current:'florist',careers:{florist:{open:true,active_task:task.id,tasks:[task]},grocery:{open:true,tasks:[]}}};
  api.content={careers:{},npcs:[]};api.sending=()=>false;
  const room=()=>api.state.careers.florist;
  let onSend=()=>{};
  api.command=async(op,payload,career)=>{
    sent.push({op,payload:JSON.parse(JSON.stringify(payload)),career});
    if(op==='fl_lift')room().tasks.find(v=>v.id===payload.task).work.soak=null;
    if(op==='fl_arrange')room().tasks.find(v=>v.id===payload.task).work.arranged=true;
    await onSend(op);api.dispatchEvent(new Event('state'));return {};
  };
  const context=vm.createContext({api,career:()=>api.state.current,acctDue:()=>false,toast(){},sound:{click(){},error(){}},ui:{},pmWant:null});
  vm.runInContext(command+';globalThis.command=cmd;',context);
  const hostUI={task:task.id,view:'job'},x=careerContext({api,ui:hostUI,cmd:context.command,toast(){},renderSheet(){}});x.now=()=>0;
  const wait=(data={})=>{const p=florist.actions.wait({task:task.id,cmd:'fl_lift',at:10,...data},null,x);pending.push(p);return p;};
  const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
  const fire=async(id=timers.keys().next().value)=>{const timer=timers.get(id);assert.ok(timer,'a wait is armed');timers.delete(id);timer.fn();await flush();};
  const change=fn=>{fn();api.dispatchEvent(new Event('state'));};
  t.after(async()=>{
    while(timers.size)await fire();await Promise.all(pending);
    assert.equal(getEventListeners(api,'state').length,0,'settled waits release their state listeners');
  });
  return {api,task,room,x,hostUI,timers,sent,wait,fire,flush,change,onSend:fn=>{onSend=fn;}};
}

function pendingSelection(h,{task=h.task.id,career='florist'}={}){
  h.room().active_task='previous-task';
  let resolve,reject;
  const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});
  let pending=true;
  promise.then(()=>{pending=false;},()=>{pending=false;});
  h.api.sending=(op,payload,cid)=>pending&&op==='task_select'&&payload.task===task&&cid===career?promise:null;
  return {
    acknowledge(){h.change(()=>{h.room().active_task=task;});resolve({});},
    resolve,reject,
  };
}

test('a valid soak wait still lifts then arranges through the current florist transport',async t=>{
  const h=harness(t),p=h.wait({then:'fl_arrange'});
  assert.deepEqual(h.sent,[]);assert.equal([...h.timers.values()][0].ms,10300);
  // Ordinary server snapshots and closing the workbench do not cancel a live shift.
  h.hostUI.view=null;h.change(()=>{h.api.state=structuredClone(h.api.state);});
  await h.fire();await p;
  assert.deepEqual(h.sent,[{op:'fl_lift',payload:{task:h.task.id},career:'florist'},{op:'fl_arrange',payload:{task:h.task.id},career:'florist'}]);
  assert.equal(h.timers.size,0);
});

test('switching career cancels the timer instead of routing fl_lift into grocery',async t=>{
  const h=harness(t),p=h.wait();
  h.change(()=>{h.api.state.current='grocery';h.task.status='cancelled';});
  assert.equal(h.timers.size,0,'the cancelled wait releases its timer immediately');await p;
  assert.deepEqual(h.sent,[]);
});

for(const [reason,change] of [
  ['career changed',h=>{h.api.state.current='grocery';}],
  ['no current career',h=>{h.api.state.current=null;}],
  ['shift closed',h=>{h.room().open=false;}],
  ['another task selected',h=>{h.room().active_task='another-task';}],
  ['task removed',h=>{h.room().tasks=[];}],
  ...['cancelled','completed','referred'].map(status=>[status,h=>{h.task.status=status;}]),
  ['another piece selected',h=>{h.task.cur=1;}],
  ['a new soak started',h=>{h.task.work.soak=9;}],
])test(`the callback rechecks live state when ${reason}`,async t=>{
  const h=harness(t),p=h.wait();change(h);await h.fire();await p;
  assert.deepEqual(h.sent,[],reason);
});

test('a cancelled wait cannot resume after leaving and returning to the same task',async t=>{
  const h=harness(t),p=h.wait();
  h.change(()=>{h.room().active_task='another-task';});
  h.change(()=>{h.room().active_task=h.task.id;});
  assert.equal(h.timers.size,0);await p;assert.deepEqual(h.sent,[]);
  const next=h.wait();await h.fire();await next;
  assert.equal(h.sent.length,1,'the player can explicitly arm a fresh wait');
});

test('a replaced soak supersedes its old wait without the old cleanup clearing the new wait',async t=>{
  const h=harness(t),old=h.wait();h.task.work.soak=9;
  const next=h.wait({at:18});await h.flush();
  assert.equal(h.timers.size,1);assert.equal([...h.timers.values()][0].ms,18300);
  await h.wait({at:18});assert.equal(h.timers.size,1,'a repeated tap keeps one timer');
  assert.deepEqual(h.sent,[]);await h.fire();await Promise.all([old,next]);
  assert.deepEqual(h.sent,[{op:'fl_lift',payload:{task:h.task.id},career:'florist'}]);
});

test('changing career while lift is on the wire suppresses its chained arrange',async t=>{
  const h=harness(t);h.onSend(()=>{h.api.state.current='grocery';h.task.status='cancelled';});
  const p=h.wait({then:'fl_arrange'});await h.fire();await p;
  assert.deepEqual(h.sent,[{op:'fl_lift',payload:{task:h.task.id},career:'florist'}]);
});

test('a restarted soak while lift is on the wire suppresses its chained arrange',async t=>{
  const h=harness(t);h.onSend(()=>{h.task.work.soak=9;});
  const p=h.wait({then:'fl_arrange'});await h.fire();await p;
  assert.deepEqual(h.sent,[{op:'fl_lift',payload:{task:h.task.id},career:'florist'}]);
});

test('foam waits arrange once, but a replacement foam cancels the previous countdown',async t=>{
  const h=harness(t);h.task.work.soak=null;
  const old=h.wait({cmd:'fl_arrange'});h.task.work.foam.start=9;await h.fire();await old;
  assert.deepEqual(h.sent,[]);
  const next=h.wait({cmd:'fl_arrange',at:18});await h.fire();await next;
  assert.deepEqual(h.sent,[{op:'fl_arrange',payload:{task:h.task.id},career:'florist'}]);
});

test('a manual lift or an already-sending lift still suppresses the pending timer',async t=>{
  const h=harness(t),first=h.wait();h.task.work.soak=null;await h.fire();await first;
  h.task.work.soak=9;h.api.sending=cmd=>cmd==='fl_lift';
  const second=h.wait({at:18});await h.fire();await second;
  assert.deepEqual(h.sent,[]);
});

test('the visible task arms its timer while its exact task_select is pending, then sends after confirmation',async t=>{
  const h=harness(t),selection=pendingSelection(h),p=h.wait();
  assert.equal(h.timers.size,1,'the optimistic workbench accepts the wait tap');
  h.change(()=>{});assert.equal(h.timers.size,1,'an unrelated refresh with the previous selection preserves the wait');
  selection.acknowledge();await h.flush();await h.fire();await p;
  assert.deepEqual(h.sent,[{op:'fl_lift',payload:{task:h.task.id},career:'florist'}]);
});

for(const [reason,options] of [['another task',{task:'different-task'}],['another career',{career:'grocery'}]])
  test(`a pending selection for ${reason} cannot authorize this task's wait`,async t=>{
    const h=harness(t),selection=pendingSelection(h,options);await h.wait();
    assert.equal(h.timers.size,0);selection.resolve({});await h.flush();assert.deepEqual(h.sent,[]);
  });

test('a previous active task without a pending selection cannot arm the wait',async t=>{
  const h=harness(t);h.room().active_task='previous-task';await h.wait();
  assert.equal(h.timers.size,0);assert.deepEqual(h.sent,[]);
});

test('an elapsed countdown waits for confirmed selection before sending',async t=>{
  const h=harness(t),selection=pendingSelection(h),p=h.wait();
  await h.fire();assert.deepEqual(h.sent,[],'the previous task is still active');
  selection.acknowledge();await h.flush();await p;
  assert.deepEqual(h.sent,[{op:'fl_lift',payload:{task:h.task.id},career:'florist'}]);
});

for(const expired of [false,true])test(`a rejected task selection cancels the wait ${expired?'after':'before'} its countdown expires`,async t=>{
  const h=harness(t),selection=pendingSelection(h),p=h.wait();
  assert.equal(h.timers.size,1);if(expired)await h.fire();
  // Network failures need not publish a new state snapshot.
  selection.reject(new Error('selection rejected'));await h.flush();await p;
  assert.equal(h.timers.size,0);assert.deepEqual(h.sent,[]);
});

test('a settled selection that leaves the previous task active cancels the wait',async t=>{
  const h=harness(t),selection=pendingSelection(h),p=h.wait();
  assert.equal(h.timers.size,1);selection.resolve({});await h.flush();await p;
  assert.equal(h.timers.size,0);assert.deepEqual(h.sent,[]);
});

for(const careerChanged of [false,true])test(`a pending selection cannot revive a wait after ${careerChanged?'leaving the career':'selecting another task'}`,async t=>{
  const h=harness(t),selection=pendingSelection(h),p=h.wait();assert.equal(h.timers.size,1);
  h.change(()=>{if(careerChanged)h.api.state.current='grocery';else h.room().active_task='different-task';});
  assert.equal(h.timers.size,0);await p;
  h.api.state.current='florist';selection.acknowledge();await h.flush();assert.deepEqual(h.sent,[]);
});
