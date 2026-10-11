import assert from 'node:assert/strict';
import test from 'node:test';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

const source=readFileSync(new URL('../public/js/v4/dog-bark.js',import.meta.url),'utf8')
  .replace(/^import .*;\r?\n/gm,'').replace(/^export /gm,'');
function harness(){
  const sent=[],handlers=new Map(),intervals=[];let info={on:true,me:{open:null}},commands=0,collected=0;
  const ctx=vm.createContext({console,Date,Number,Math,Promise,setTimeout,clearTimeout,setInterval:(f,ms)=>{intervals.push(ms);return 0;},clearInterval:()=>{},stylesheet:async()=>{},
    localStorage:{getItem:()=>null},esc:s=>s,actBar:()=>'',barkCompetition:()=>''});
  vm.runInContext(source+`\npaint=()=>{};dialog=()=>B.dlg;collect=async()=>{recordCollect()};micOn=async()=>true;micReady=async()=>'live';
    globalThis.subject={B,bind,loadInfo,find,openDogBark};`,ctx);
  ctx.recordCollect=()=>collected++;
  const {B}=ctx.subject;
  B.dlg={open:true};B.live={on:(t,f)=>handlers.set(t,f),send:f=>{sent.push(f);return true;}};
  B.env={api:{state:{journey:{wallet:10000}},json:async()=>info,command:async()=>{commands++;throw new Error('Network interrupted');}}};
  B.info=info;
  return {s:ctx.subject,sent,handlers,intervals,setInfo:v=>{info=v;},commands:()=>commands,collected:()=>collected,
    flush:async()=>{for(let i=0;i<8;i++)await Promise.resolve();}};
}
const waiting={on:true,me:{open:{ticket:'saved-ticket',status:'wait',stake:5000,at:Date.now()/1000-30}}};

test('an existing durable ticket restores waiting UI and is resubmitted even when already remembered',async()=>{
  const h=harness();h.setInfo(waiting);h.s.B.ticket='saved-ticket';
  await h.s.loadInfo();
  assert.equal(h.s.B.view,'wait');assert.equal(h.s.B.stake,5000);
  assert.ok(h.sent.some(f=>f.t==='bark_find'&&f.ticket==='saved-ticket'));
  assert.ok(Date.now()-h.s.B.waitAt>=29000);
});
test('reconnect recovers escrow absent from live service memory',async()=>{
  const h=harness();h.setInfo(waiting);h.s.bind();h.handlers.get('welcome')({});await h.flush();
  assert.equal(h.s.B.view,'wait');assert.ok(h.sent.some(f=>f.t==='bark_find'));
});
test('bark_none recovers waiting escrow instead of showing another bet button',async()=>{
  const h=harness();h.setInfo(waiting);h.s.B.ticket='saved-ticket';h.s.B.view='wait';h.s.bind();
  h.handlers.get('bark_none')({});await h.flush();
  assert.equal(h.s.B.view,'wait');assert.ok(h.sent.some(f=>f.t==='bark_find'));
});
test('ambiguous join response reconciles the committed ticket without another debit',async()=>{
  const h=harness();h.setInfo(waiting);await h.s.find();
  assert.equal(h.commands(),1);assert.equal(h.s.B.ticket,'saved-ticket');assert.equal(h.s.B.view,'wait');
});
test('stale waiting ticket clears after refund and collects the wallet effect',async()=>{
  const h=harness();h.s.B.ticket='saved-ticket';h.s.B.view='wait';await h.s.loadInfo();
  assert.equal(h.s.B.ticket,null);assert.equal(h.s.B.view,'lobby');assert.equal(h.collected(),1);
});
test('a repeated click while joining cannot submit another stake',async()=>{
  const h=harness();h.s.B.busy=true;await h.s.find();assert.equal(h.commands(),0);
});
test('a refunded ticket remembered in the lobby is cleared too',async()=>{
  const h=harness();h.s.B.ticket='saved-ticket';await h.s.find();
  assert.equal(h.s.B.ticket,null);assert.equal(h.collected(),1);
});
test('a pre-join info response cannot clear the new committed ticket',async()=>{
  const h=harness();let resolveInfo;h.s.B.env.api.json=()=>new Promise(r=>{resolveInfo=r;});
  const loading=h.s.loadInfo();
  h.s.B.env.api.command=async()=>({bark:{ticket:'new-ticket'}});await h.s.find();
  resolveInfo({on:true,me:{open:null}});await loading;
  assert.equal(h.s.B.ticket,'new-ticket');assert.equal(h.s.B.view,'wait');assert.equal(h.collected(),0);
});
test('late join response preserves a match recovered before the response arrives',async()=>{
  const h=harness();let resolveJoin;h.s.B.env.api.command=()=>new Promise(r=>{resolveJoin=r;});
  const joining=h.s.find();await h.flush();h.setInfo(waiting);await h.s.loadInfo();
  h.s.bind();h.handlers.get('bark_go')({m:'live-match',x:0,left:60});
  resolveJoin({bark:{ticket:'saved-ticket'}});await joining;
  assert.equal(h.s.B.view,'match');assert.equal(h.s.B.ticket,null);assert.equal(h.s.B.match.m,'live-match');
  clearInterval(h.s.B.send);
});
test('closing during initial info load does not resume a stake or start dialog timers',async()=>{
  const h=harness();let resolveInfo;h.s.B.env.api.json=()=>new Promise(r=>{resolveInfo=r;});
  const opening=h.s.openDogBark(h.s.B.env);await h.flush();h.s.B.dlg.open=false;
  resolveInfo(waiting);await opening;
  assert.equal(h.s.B.ticket,null);assert.equal(h.sent.length,0);assert.equal(h.intervals.length,0);
});
test('fallback info cannot restore a ticket after bark_go already attached a match',async()=>{
  const h=harness();let resolveInfo;h.s.B.env.api.json=()=>new Promise(r=>{resolveInfo=r;});
  h.s.B.env.api.command=async()=>({});h.s.bind();const joining=h.s.find();await h.flush();
  h.handlers.get('bark_go')({m:'live-match',x:0,left:60});resolveInfo(waiting);await joining;
  assert.equal(h.s.B.view,'match');assert.equal(h.s.B.ticket,null);
  h.handlers.get('bark_back')({ticket:'saved-ticket'});assert.equal(h.s.B.view,'match');
});
