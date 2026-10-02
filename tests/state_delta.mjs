// Unit test of public/js/api.js state deltas (game/state_delta.py): inflate() on the server's own answers (a file
// written by tests/test_state_delta.py: each answer, the `known` it was encoded for, the whole state), then GameAPI
// against fake servers: an old server (no delta), references filled from the parts held when the command was sent,
// a reference that cannot be filled (the whole state is read instead), the header on every request.
// Run by tests/test_state_delta.py (node tests/state_delta.mjs <answers.json>); exits non-zero on failure.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {GameAPI,Held,inflate,UpdatingNote} from '../public/js/api.js';

const canon=x=>Array.isArray(x)?`[${x.map(canon).join(',')}]`:x&&typeof x==='object'?`{${Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canon(x[k])).join(',')}}`:JSON.stringify(x);
const chunks=s=>(s.match(/.{8}/g)||[]).sort().join();

{ // the server's answers, one after the other
  const answers=JSON.parse(readFileSync(process.argv[2],'utf8'));
  let held=new Held(),refs=0;
  for(const [i,a] of answers.entries()){
    assert.equal(chunks(held.known()),chunks(a.known),`answer ${i}: the page holds what the server was told`);
    const data=JSON.parse(a.text);refs+=data.delta.refs.length;
    const next=inflate(data,held);
    assert.equal(JSON.stringify(data.state),JSON.stringify(a.whole),`answer ${i}: the very state, in the same key order`);
    assert.equal(inflate(data,new Held()),next,'taking it again changes nothing');
    held=next;
  }
  assert.ok(refs>answers.length*10,'most of each answer came as references');
}

const json=(status,data)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
function install(script){
  const calls=[];
  globalThis.fetch=async(url,init={})=>{
    const body=init.body?JSON.parse(init.body):null;calls.push({url,method:init.method||'GET',body,headers:init.headers||{}});
    const step=script.shift();return typeof step==='function'?step(body,url):step;
  };
  return calls;
}
function api(){const a=new GameAPI();a.delays=[5];a.retryWindow=100;a.csrf='c';a.holding=new UpdatingNote(()=>'vi',null,0);return a;}
const big=n=>({id:n,text:'x'.repeat(300)});

{ // an old server: no delta, the whole state each time; nothing held, no `known` sent
  const calls=install([json(200,{state:{current:'grocery',a:1},revision:1}),json(200,{state:{current:'grocery',a:2},revision:2,result:{message:'ok'}})]);
  const a=api();await a.refresh();await a.command('sell',{});
  assert.equal(a.state.a,2);assert.equal(a.held.parts.size,0);
  assert.equal(calls[1].body.known,undefined,'nothing held: no known');
  assert.ok(calls.every(c=>c.headers['X-Game-Delta']==='1'),'the header on every request');
}
{ // references filled from what was held when the command was sent, even if another state came meanwhile
  const feed=[big(1),big(2)];
  const first={state:{current:'grocery',feed,n:1},revision:1,delta:{refs:[],keys:[[['feed'],'AAAAAAAA'],[['feed',0],'BBBBBBBB'],[['feed',1],'CCCCCCCC']]}};
  let release;const gate=new Promise(r=>release=r);
  const calls=install([json(200,first),async b=>{await gate;return json(200,{state:{current:'grocery',feed:0,n:2},revision:2,result:{message:'ok'},delta:{refs:[[['feed'],'AAAAAAAA']],keys:[]}});},
    json(200,{state:{current:'grocery',other:true},revision:1})]);
  const a=api();await a.refresh();const mine=a.state.feed;
  const job=a.command('sell',{});await new Promise(r=>setTimeout(r,5));
  assert.equal(chunks(calls[1].body.known),chunks('AAAAAAAABBBBBBBBCCCCCCCC'));
  a.held=new Held();  // what is held changes under the command (another answer adopted meanwhile)
  release();await job;
  assert.equal(a.revision,2);assert.deepEqual(a.state.feed,feed);assert.equal(a.state.feed,mine,'the very part held');
  assert.deepEqual([...a.held.parts.keys()].sort(),['AAAAAAAA','BBBBBBBB','CCCCCCCC'],'the posts stay held inside the reused list');
}
{ // a reference that cannot be filled: the whole state is read instead, the command still counts once
  const calls=install([json(200,{state:{current:'grocery',x:0},revision:5,result:{message:'done'},delta:{refs:[[['x'],'ZZZZZZZZ']],keys:[]}}),
    json(200,{state:{current:'grocery',x:{whole:true}},revision:5,delta:{refs:[],keys:[]}})]);
  const a=api();a.state={current:'grocery'};a.revision=4;const warn=console.warn;console.warn=()=>{};
  const out=await a.command('sell',{});console.warn=warn;
  assert.equal(out.message,'done');assert.deepEqual(a.state.x,{whole:true});assert.equal(calls[1].url,'/api/state');assert.equal(calls.length,2);
}
{ // a 409 with the whole state (named parts, no references) is adopted, the retry sends the new known
  const calls=install([json(409,{error:'moved',code:'revision_conflict',state:{current:'grocery',p:big(1)},revision:3,delta:{refs:[],keys:[[['p'],'PPPPPPPP']]}}),
    json(200,{state:{current:'grocery',p:0},revision:4,result:{message:'ok'},delta:{refs:[[['p'],'PPPPPPPP']],keys:[]}})]);
  const a=api();a.state={current:'grocery'};a.revision=2;await a.command('sell',{});
  assert.equal(calls[1].body.known,'PPPPPPPP');assert.deepEqual(a.state.p,big(1));assert.equal(a.revision,4);
}
console.log('ok');
