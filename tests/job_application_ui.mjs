import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {jobView,v4Action} from '../public/js/v4/views.js';
import {GameAPI} from '../public/js/api.js';
import {skeleton} from '../public/js/lazy.js';

const fixture=JSON.parse(readFileSync(0,'utf8'));
const envFor=state=>({api:{state:structuredClone(state),content:fixture.content},ui:{}});
const stages=new Set(),statuses=new Set();
for(const {label,state} of fixture.states){
  const env=envFor(state),job=state.careers[state.current].job;
  const html=jobView(env);
  assert.match(html,/<header class="sheet-head">/,label);
  assert.match(html,/<div class="sheet-body">[\s\S]+<\/div>$/,label);
  statuses.add(job.status);
  if(job.status==='applying'){
    const stage=job.application.stage;stages.add(stage);
    assert.match(html,/data-command="job_withdraw"/,`${label}: withdrawal remains available`);
    const control={exam:'data-command="job_exam"',cv:'data-action="v4Cv"',letter:'data-action="v4Letter"',
      interview:'data-action="v4Jb',test:'data-action="v4Jb',trial:'data-action="v4Jb'}[stage];
    assert.ok(html.includes(control),`${label}: current stage has an actionable control`);
  }else if(job.status==='offer')assert.match(html,/data-op="job_accept"/,label);
  else if(job.status==='hired')assert.match(html,/data-op="job_quit"/,label);
  else assert.match(html,/data-command="job_apply"/,label);
}
assert.deepEqual([...stages].sort(),['cv','exam','interview','letter','test','trial']);
assert.deepEqual([...statuses].sort(),['applying','hired','none','offer','rejected']);

// While AI wording is in flight, keep the question, pending response and exit visible.
const sample=fixture.states.find(({state})=>state.current==='flight_attendant'&&state.careers.flight_attendant.job.application?.stage==='interview');
const env=envFor(sample.state),post=fixture.content.employment.postings.flight_attendant.find(p=>p.id===env.api.state.careers.flight_attendant.job.application.posting);
const qid=post.questions[0],option=fixture.content.employment.questions.flight_attendant[qid].options[0];
let reject,resolve;const renders=[],messages=[],sent=[];
Object.assign(env.api,{queue:Promise.resolve(),revision:1,ai:{configured:true},accept(data){if(data.state)this.state=data.state;},
  post:()=>new Promise((yes,no)=>{resolve=yes;reject=no;})});
Object.assign(env,{renderSheet(){renders.push(jobView(env));},toast:(...args)=>messages.push(args),
  cmd:async(...args)=>{sent.push(args);return {message:'fallback'};}});
const answer={question:qid,option:option.id,label:option.label};
let request=v4Action('v4JbAnswer',answer,null,env);
await Promise.resolve();
assert.match(renders.at(-1),/class="bubble npc typing"/);
assert.match(renders.at(-1),/data-command="job_withdraw"/);
await v4Action('v4JbAnswer',answer,null,env);
reject(Object.assign(new Error('Chưa gửi được câu trả lời.'),{status:503}));
await request;
assert.equal(messages.length,1);
assert.doesNotMatch(renders.at(-1),/class="bubble npc typing"/);
assert.match(renders.at(-1),/data-action="v4JbAnswer"/);
request=v4Action('v4JbAnswer',answer,null,env);await Promise.resolve();
reject(new TypeError('offline'));await request;
assert.equal(sent.length,1,'an unreachable AI route uses the normal command');
assert.equal(sent[0][0],'job_answer');
assert.doesNotMatch(renders.at(-1),/class="bubble npc typing"/);
request=v4Action('v4JbAnswer',answer,null,env);await Promise.resolve();
resolve({state:env.api.state,result:{}});await request;
assert.doesNotMatch(renders.at(-1),/class="bubble npc typing"/);

// The real app wrapper keeps a loading body until employment catalogue content
// arrives. A failed fetch releases the cached request so the next render can retry.
const api=new GameAPI(),warnings=[];
api.content={...fixture.content,part:'core'};delete api.content.employment;
api.state=sample.state;api.contentBase='/api/content?v=fixture';
api.json=()=>new Promise((yes,no)=>{resolve=yes;reject=no;});
const appSource=readFileSync(new URL('../public/js/app.js',import.meta.url),'utf8');
const wrapper=appSource.match(/^const moreView=(.*);\r?$/m)?.[1];
assert.ok(wrapper,'the actual job sheet catalogue wrapper is available');
const moreView=new Function('api','header','skeleton','console',`return (${wrapper});`)(api,()=>'<header class="sheet-head"></header>',skeleton,{warn:(...args)=>warnings.push(args)});
const render=()=>moreView(()=>jobView({api,ui:{}}));
assert.match(render(),/<div class="sheet-body"><div class="mnl-skel" role="status" aria-busy="true">/);
reject(new TypeError('offline'));await Promise.resolve();await Promise.resolve();
assert.equal(warnings.length,1);
assert.equal(api._more,null,'catalogue errors allow a fresh request');
assert.match(render(),/class="mnl-skel"/);
resolve({employment:fixture.content.employment});await api._more;
assert.match(render(),/data-action="v4JbAnswer"/);
assert.doesNotMatch(render(),/class="mnl-skel"/);
console.log(`Hiring body content passed for ${fixture.states.length} engine states, all six stages, catalogue loading/retry, interview pending and network failures.`);
