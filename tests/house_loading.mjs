import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import {escapeHTML} from '../public/js/icons.js';
import {rentalRetryable,propertyNews} from '../public/js/v4/rentals-ui.js';

const source=readFileSync(new URL('../public/js/v4/house.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};
function harness(){
  const reads=[],posts=[],commands=[],accepted=[];
  const api={state:{journey:{home:{}}},json(){const d=deferred();reads.push(d);return d.promise;},post(){const d=deferred();posts.push(d);return d.promise;},command(){const d=deferred();commands.push(d);return d.promise;},accept:r=>accepted.push(r)};
  const ctx=vm.createContext({esc:escapeHTML,icon:()=>'',rentalRetryable,propertyNews,crypto:{randomUUID:()=> 'request-id'},console});
  vm.runInContext(source+'\nrender=()=>{};globalThis.h={S,loadRentals,rentalPost,send,btn,propCard,nextStep,onClick};',ctx);
  const h=ctx.h;h.S.env={api};return {...h,reads,posts,commands,accepted};
}
test('slow rental read leaves navigation and mortgage actions available',async()=>{
  const h=harness(),pending=h.loadRentals();
  assert.equal(h.S.busy,false);
  assert.doesNotMatch(h.btn('Vào nhà','inside'),/disabled/);
  assert.doesNotMatch(h.btn('Trả góp','pay'),/disabled/);
  assert.match(h.btn('Thuê','rentalAccept'),/disabled/);
  h.reads[0].resolve({market:[],mine:[]});await pending;
  assert.doesNotMatch(h.btn('Thuê','rentalAccept'),/disabled/);
});
test('rental mutation stays exclusive and late GET cannot overwrite its result',async()=>{
  const h=harness(),pending=h.loadRentals(),mutation=h.rentalPost('accept',{id:1});
  assert.equal(h.posts.length,1);assert.equal(h.S.busy,true);
  await h.rentalPost('accept',{id:1});assert.equal(h.posts.length,1);
  h.posts[0].resolve({rentals:{tenancy:{id:1},market:[]}});await mutation;
  h.reads[0].resolve({market:[{id:1}],tenancy:null,state:{stale:true},revision:1});await pending;
  assert.equal(h.S.rentals.tenancy.id,1);assert.equal(h.accepted.length,0);
});
test('read completion cannot unlock an in-flight housing payment',async()=>{
  const h=harness(),pending=h.loadRentals(),payment=h.send('jr_home_pay');
  h.reads[0].resolve({market:[],mine:[]});await pending;
  assert.equal(h.S.busy,true);assert.match(h.btn('Trả góp','pay'),/disabled/);
  h.commands[0].resolve({approved:true});await payment;
  assert.equal(h.S.busy,false);
  for(const read of h.reads)read.resolve({market:[],mine:[]});
});
test('property sale and move wait for listing status while management remains available',async()=>{
  const h=harness(),pending=h.loadRentals();
  const home={id:'h1',name:'Nhà',move:{ok:true},sell:{ok:true},let_rent:20};
  const html=h.propCard({},home);
  assert.match(html,/<button[^>]*data-hs="move"[^>]*disabled/);
  assert.match(html,/<button[^>]*data-hs="sell"[^>]*disabled/);
  assert.doesNotMatch(html,/<button[^>]*data-hs="let"[^>]*disabled/);
  h.reads[0].resolve({market:[],mine:[{property:'h1',status:'listing'}]});await pending;
  assert.match(h.propCard({},home),/Quản lý cho thuê/);
});
test('repeated navigation during a pending read reuses it; failed reads can retry',async()=>{
  const h=harness(),pending=h.loadRentals();
  await h.onClick('rentals',{});assert.equal(h.reads.length,1);assert.equal(h.S.view,'rentals');
  h.reads[0].reject(new Error('offline'));await pending;
  assert.equal(h.S.busy,false);assert.match(h.S.rentals.error,/offline/);
  const retry=h.loadRentals();assert.equal(h.reads.length,2);
  h.reads[1].resolve({market:[],mine:[]});await retry;assert.equal(h.S.rentals.error,undefined);
});
test('suggested move waits for lookup and never targets an active player listing',async()=>{
  const h=harness(),v={props:[{id:'h1',name:'Nhà',move:{ok:true}}]};
  const pending=h.loadRentals();assert.doesNotMatch(h.nextStep(v),/data-hs="move"/);
  h.reads[0].resolve({mine:[{property:'h1',status:'listing'}]});await pending;
  assert.doesNotMatch(h.nextStep(v),/data-hs="move"/);
  h.S.rentals={mine:[]};assert.match(h.nextStep(v),/data-hs="move"/);
});
test('mortgage payments without a pending lookup do not fetch unrelated rental data',async()=>{
  const h=harness();h.S.dlg={open:true,querySelector:()=>null};
  const payment=h.send('jr_home_pay');h.commands[0].resolve({approved:true});await payment;
  assert.equal(h.reads.length,0);
});
test('payment completion after closing the dialog does not start another rental request',async()=>{
  const h=harness();h.S.dlg={open:false,querySelector:()=>null};
  const pending=h.loadRentals(),payment=h.send('jr_home_pay');
  h.commands[0].resolve({approved:true});await payment;
  assert.equal(h.reads.length,1);
  h.reads[0].resolve({market:[],mine:[]});await pending;
});
