// Unit test of the first-day coach engine (public/js/tutorial/coach-core.js) and its memory (store.js markCoach /
// coachSeen): a step moves on when the player does it (a tap the game accepts), stays on a refusal, "Bỏ qua" skips it,
// a control that is not on screen gets the "where" bubble after a moment, a closed tab gets its tab ringed, an
// optional step that does not come up is dropped, and the marks ride in settings.notesSeen (≤ 12 valid ids).
// Run by tests/test_coach.py (node tests/coach_engine.mjs '<career ids json>'); exits non-zero on failure.
import assert from 'node:assert/strict';
import {CoachRun,planFor,norm,labelScore,labelHit,OPEN,CLOSE,SUM,SETTLE,GRACE,OPT_WAIT} from '../public/js/tutorial/coach-core.js';
import {coachSeen,markCoach,notesSeen,markNoteSeen,markGuideSeen,guidesFrom,GUIDE_BITS,COACH_NEW,FEATURE_BITS,featuresSeen,markFeature} from '../public/js/tutorial/store.js';
import data from '../public/js/tutorial/coach-content.js';

/* ---- words */
assert.equal(norm('🛒 Mời đặt hàng →'),'mời đặt hàng');
assert.equal(norm('📦  Kho & nhập hàng'),'kho nhập hàng');
const want=l=>l.map(norm);
assert.equal(labelScore('CHỐT BILL',want(['CHỐT BILL'])),3);
assert.equal(labelScore('Quét ×4',want(['Quét'])),2,'"Quét ×4" starts with the label');
assert.equal(labelScore('Soát hóa đơn rồi bấm CHỐT BILL →',want(['CHỐT BILL'])),1,'a hint that mentions a long label');
assert.equal(labelScore('Bấm Quét',want(['Quét'])),0,'a short label is never matched inside other words');
assert.equal(labelHit('Khép ca',want(['Kho'])),false);

/* ---- the plan: open, the workplace's own steps, close, summary */
const plan=planFor(data,'grocery');
assert.equal(plan[0],OPEN);assert.equal(plan.at(-2),CLOSE);assert.equal(plan.at(-1),SUM);
assert.ok(plan.length>=6);
for(const cid of JSON.parse(process.argv[2]||'[]')){
  const steps=data.careers[cid]?.steps;
  assert.ok(steps?.length>=3,`${cid}: no coach steps in coach-content.js`);
  for(const s of steps){
    assert.ok(s.e&&s.t,`${cid}: a step without emoji or words`);
    assert.ok(s.x||s.k?.length||s.s?.length,`${cid}: "${s.t}" has no control and is not words-only`);
  }
}

/* ---- the machine, with a fake clock and a fake screen */
let now=0;const clock=()=>now;
const steps=[OPEN,{id:'a',e:'1',t:'A',k:['A']},{id:'b',e:'2',t:'B',k:['B'],v:{t:'tab',k:['Tab']}},{id:'opt',e:'3',t:'O',k:['O'],o:1},
  {id:'c',e:'4',t:'C',k:['C']},{id:'x',e:'5',t:'X',x:1},CLOSE,SUM];
const screen={open:false,on:new Set(),tab:false,summary:false};
/** What coach.js's probe would say for this fake screen. */
const probe=s=>{
  if(s.kind==='open')return screen.open?{done:true}:{el:'open-btn'};
  if(screen.summary&&s.kind!=='sum')return {done:true};
  if(s.kind==='close')return {dock:true};
  if(s.kind==='sum')return screen.summary?{el:'sum'}:{done:true};
  if(s.k?.some(k=>screen.on.has(k)))return {el:s.k[0]};
  if(s.v&&screen.tab)return {via:'tab'};
  return {};
};
const run=new CoachRun({cid:'demo',steps,now:clock});
let f=run.frame(probe);
assert.equal(f.mode,'spot');assert.equal(f.step.id,'open');assert.equal(f.el,'open-btn');
screen.open=true;
f=run.frame(probe);
assert.equal(f.step.id,'a','the shift opened: on to the first own step');
assert.equal(f.mode,'hidden','a moment of quiet before saying where a control is');
now+=GRACE;f=run.frame(probe);
assert.equal(f.mode,'fallback','not on screen: the "where" bubble');
screen.on.add('A');f=run.frame(probe);
assert.equal(f.mode,'spot');assert.equal(f.el,'A');
// A tap the game refuses keeps the step; an accepted one moves on.
run.tap(run.which(s=>s.k?.includes('A')));run.answered(false);now+=10;
assert.equal(run.frame(probe).step.id,'a','refused: same step');
run.tap(run.i);run.answered(true);now+=10;
f=run.frame(probe);assert.equal(f.step.id,'b','accepted: next step');
// The control is inside a closed tab: the tab is ringed.
screen.tab=true;f=run.frame(probe);
assert.equal(f.mode,'via');assert.equal(f.el,'tab');
// A tap with no command (a tab, a fold) counts once SETTLE has passed and nothing is on its way.
screen.on.add('B');run.tap(run.i);now+=SETTLE-1;
assert.equal(run.frame(probe,{busy:()=>false}).step.id,'b');
now+=2;assert.equal(run.frame(probe,{busy:()=>true}).step.id,'b','a command still on its way: wait for it');
f=run.frame(probe,{busy:()=>false});
// The optional step never came up: dropped, and it does not count in "n/total".
assert.equal(f.step.id,'opt');
const total=run.total;
now+=OPT_WAIT;f=run.frame(probe);
assert.equal(f.step.id,'c','an optional step that is not around is dropped');
assert.equal(run.total,total-1,'a dropped optional step is not counted');
// "Bỏ qua".
run.skip();f=run.frame(probe);
assert.equal(f.step.id,'x');assert.equal(f.mode,'text','a words-only step');
// A words-only step also ends when the player does something the game accepts (after a moment on screen).
run.answered(true);assert.equal(run.frame(probe).step.id,'x','not at once');
now+=1300;run.answered(true);f=run.frame(probe);
assert.equal(f.step.id,'close');assert.equal(f.mode,'dock');
// The day closes: the summary, then the end.
screen.summary=true;f=run.frame(probe);
assert.equal(f.step.id,'sum');assert.equal(f.mode,'spot');
screen.summary=false;f=run.frame(probe);
assert.equal(f.mode,'end');assert.ok(run.ended);

// Going ahead: a tap on a later step's control jumps there (the player knew the way).
const r2=new CoachRun({cid:'demo',steps,now:clock});screen.open=true;
r2.frame(probe);
const j=r2.which(s=>s.k?.includes('C'));assert.equal(j,4);
r2.tap(j);r2.answered(true);f=r2.frame(probe);
assert.equal(f.step.id,'x','after the later step');
// A control that sends a command waits for the game's answer: no answer (a cancelled confirm, a form that does not
// send, a dimmed button) never counts by time alone.
const r4=new CoachRun({cid:'demo',steps,at:1,now:clock});screen.on.add('A');
r4.frame(probe);r4.tap(r4.i,{cmd:true});now+=SETTLE*3;
assert.equal(r4.frame(probe).step.id,'a','a command tap without an answer stays');
r4.answered(true);now+=1;assert.equal(r4.frame(probe).step.id,'b');
// The game's own guidance already points at a later step (the player is past this one): the walk follows.
const r3=new CoachRun({cid:'demo',steps,now:clock});
const jumpy=s=>s.kind==='open'?{done:true}:s.id==='a'?{jump:4}:probe(s);
assert.equal(r3.frame(jumpy).step.id,'a','not while the screen may still be redrawing after the last move');
now+=OPT_WAIT;f=r3.frame(jumpy);
assert.equal(f.step.id,'c','jumped to the step the game is at');
assert.equal(new CoachRun({cid:'demo',steps,at:4,now:clock}).frame(s=>s.id==='c'?{jump:1}:{}).step.id,'c','never jumps back');
// A resumed run starts where it was.
assert.equal(new CoachRun({cid:'demo',steps,at:4,now:clock}).step.id,'c');
// Back to the step before: an optional step not on screen while the step before it (f: kept open on a wrong answer) is
// open again (coach.js probe says {back}): the walk shows that one again rather than dropping the rest.
const two=[OPEN,{id:'p1',e:'1',t:'P1',k:['P1'],o:1,f:1},{id:'p2',e:'2',t:'P2',k:['P2'],o:1},CLOSE,SUM];
const r5=new CoachRun({cid:'demo',steps:two,at:1,now:clock});
const on5=new Set(['P1']);
const p5=s=>s.id==='p2'&&on5.has('P1')?{back:1}:s.k?.some(k=>on5.has(k))?{el:s.k[0]}:{};
assert.equal(r5.frame(p5).step.id,'p1');
r5.tap(r5.i,{cmd:true});r5.answered(true);now+=1;
assert.equal(r5.frame(p5).step.id,'p2','accepted: on to the next one');
now+=OPT_WAIT;f=r5.frame(p5);
assert.equal(f.step.id,'p1','still open (a wrong answer): back to it');assert.equal(f.mode,'spot');
on5.delete('P1');on5.add('P2');r5.tap(r5.i,{cmd:true});r5.answered(true);now+=OPT_WAIT;
assert.equal(r5.frame(p5).step.id,'p2','fixed: the next step');
assert.equal(new CoachRun({cid:'demo',steps:two,at:2,now:clock}).frame(()=>({back:0})).step.id,'p2','only ever one step back');

/* ---- memory: settings.notesSeen (node: no localStorage, the server copy is the truth) */
function player(notes=''){
  const state={current:'grocery',careers:{grocery:{day:1}},settings:{notesSeen:notes},journey:{story:true,life_day:1,intro:true}};
  return {api:{state,command:async(action,patch)=>{assert.equal(action,'settings');Object.assign(state.settings,patch);return {};}}};
}
let env=player('onb1,h-job');
assert.deepEqual([...coachSeen(env.api).offered],[]);
assert.equal(coachSeen(env.api).native,false);
markNoteSeen(env,COACH_NEW);
assert.equal(coachSeen(env.api).native,true,'cn1: this save started with the coach');
markCoach(env,'grocery');
assert.ok(coachSeen(env.api).offered.has('grocery'));assert.ok(!coachSeen(env.api).done.has('grocery'));
markCoach(env,'florist',{done:true});
assert.ok(coachSeen(env.api).done.has('florist')&&coachSeen(env.api).offered.has('florist'));
markGuideSeen(env,'grocery');
assert.ok(guidesFrom(notesSeen(env.api)).has('grocery'),'the guide card mark still works beside the coach');
// Many other notes later: the packed ids and cn1 are never pushed out; every id stays valid for the server.
for(let i=0;i<20;i++)markNoteSeen(env,'x-'+i);
const ids=env.api.state.settings.notesSeen.split(',');
assert.ok(ids.length<=12,ids.join());
assert.ok(ids.every(x=>/^[a-z0-9-]{1,24}$/.test(x)),ids.join());
assert.ok(coachSeen(env.api).offered.has('grocery')&&coachSeen(env.api).done.has('florist')&&coachSeen(env.api).native);
// Every workplace marked: still one short id each.
env=player();for(const cid of GUIDE_BITS)markCoach(env,cid,{done:true});
for(const x of env.api.state.settings.notesSeen.split(','))assert.match(x,/^[a-z0-9-]{1,24}$/);
assert.equal(coachSeen(env.api).done.size,GUIDE_BITS.length);
// First-use hints of the player services (tips.js FEATS): one packed "fh-" id beside the coach's, never pushed out.
for(const id of FEATURE_BITS)markFeature(env,id);
for(let i=0;i<20;i++)markNoteSeen(env,'y-'+i);
assert.equal(featuresSeen(env.api).size,FEATURE_BITS.length);
assert.equal(coachSeen(env.api).done.size,GUIDE_BITS.length,'the hints do not touch the coach marks');
assert.equal(env.api.state.settings.notesSeen.split(',').filter(x=>x.startsWith('fh-')).length,1);
for(const x of env.api.state.settings.notesSeen.split(','))assert.match(x,/^[a-z0-9-]{1,24}$/);
console.log('coach_engine.mjs: ok');
