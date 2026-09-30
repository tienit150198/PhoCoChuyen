// Unit test of public/js/api.js retry through a server restart (0.9.5): 502/503/504 and lost connections are
// sent again with the same body (same request_id), 4xx never, other writes never; commands keep their order;
// the "Đang cập nhật máy chủ…" note shows during a long retry and leaves with it.
// Run by tests/test_api_retry.py (node tests/api_retry.mjs); exits non-zero on failure.
import assert from 'node:assert/strict';
import {GameAPI,UpdatingNote,transient,UPDATING_TEXT,RETRY_DELAYS,RETRY_WINDOW} from '../public/js/api.js';

const json=(status,data)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','X-Game-Version':'0.9.5+abc'}});
const html=status=>new Response(`<html><body><h1>${status} Bad Gateway</h1><hr>nginx</body></html>`,{status,headers:{'Content-Type':'text/html'}});
const down=()=>Promise.reject(new TypeError('Failed to fetch'));
const state=rev=>({state:{current:'grocery',settings:{lang:'vi'}},revision:rev,result:{message:`ok ${rev}`}});

/** A fake server: `script` answers attempt by attempt (a function of the parsed body, or a Response, or 'down'). */
function install(script){
  const calls=[];
  globalThis.fetch=async(url,init={})=>{
    const body=init.body?JSON.parse(init.body):null;calls.push({url,method:init.method||'GET',body,raw:init.body});
    const step=script.length?script.shift():null;
    if(step==='down')return down();
    if(typeof step==='function')return step(body,url);
    if(step)return step;
    return json(200,state(1));
  };
  return calls;
}
function api(){
  const a=new GameAPI();a.delays=[5,5,5,5,5,5,5,5,5];a.retryWindow=2000;a.state={current:'grocery'};a.revision=7;a.csrf='c';
  a.holding=new UpdatingNote(()=>'vi',null,0);
  const seen={offline:0,results:[],updating:[],net:[]};
  a.addEventListener('offline',()=>seen.offline++);a.addEventListener('result',e=>seen.results.push(e.detail.result.message));
  a.addEventListener('updating',e=>seen.updating.push(e.detail));a.addEventListener('net',e=>seen.net.push(e.detail));
  return [a,seen];
}

assert.deepEqual(RETRY_DELAYS.slice(0,5),[300,600,1000,1500,2000],'backoff 0.3, 0.6, 1, 1.5, 2 s…');
assert.ok(RETRY_DELAYS.reduce((a,b)=>a+b,0)>=11000&&RETRY_WINDOW<=15000,'about 12 s of retries');
assert.equal(transient({}),true);assert.equal(transient({status:502}),true);assert.equal(transient({status:504}),true);
assert.equal(transient({status:400}),false);assert.equal(transient({status:409}),false);assert.equal(transient({status:500}),false);

{ // a deploy: two 502 pages from nginx, a dropped connection, a 503 db_unavailable, then the command lands once
  const calls=install([html(502),html(502),'down',json(503,{error:'Máy chủ đang bận, thử lại sau giây lát.',code:'db_unavailable'}),b=>json(200,{...state(8),result:{message:'sold '+b.request_id}})]);
  const [a,seen]=api();
  const out=await a.command('sell',{item:'milk'});
  assert.equal(calls.length,5,'retried until it landed');
  assert.ok(calls.every(c=>c.raw===calls[0].raw),'the very same body each time (request_id, expected_revision)');
  assert.equal(calls[0].body.expected_revision,7);
  assert.equal(out.message,'sold '+calls[0].body.request_id);
  assert.equal(a.revision,8);assert.equal(seen.offline,0,'no offline, no error');
  assert.deepEqual(seen.results,[out.message],'one result');
  assert.deepEqual(seen.updating,[true,false],'the note came and went');
  assert.equal(Math.min(...seen.net),0);assert.ok(seen.net.slice(0,-1).every(n=>n>0),'the tap stays pending through the retries');
}
{ // a lost response: the server applied it, the retry replays the receipt (never applied twice)
  let applied=0;const receipts=new Map();
  const server=b=>{if(!receipts.has(b.request_id)){applied++;receipts.set(b.request_id,state(8));}return json(200,{...receipts.get(b.request_id),replayed:applied>0});};
  const calls=install([b=>{server(b);return html(504);},server]);
  const [a]=api();await a.command('sell',{});
  assert.equal(calls.length,2);assert.equal(applied,1,'applied once');assert.equal(a.revision,8);
}
{ // 4xx: never retried; 409 with a state is adopted
  install([json(400,{error:'Không hợp lệ',code:'bad'})]);
  let [a,seen]=api();
  await assert.rejects(a.command('x',{}),e=>e.status===400&&e.message==='Không hợp lệ');
  assert.equal(seen.offline,0);assert.deepEqual(seen.updating,[]);
  const calls=install([json(409,{error:'Tiến trình đã thay đổi',code:'revision_conflict',...state(12)}),json(200,state(99))]);
  [a,seen]=api();
  await assert.rejects(a.command('x',{}),e=>e.status===409);
  assert.equal(calls.length,1,'409 not retried');assert.equal(a.revision,12,'the server state was adopted');
  const c2=install([json(429,{error:'Nhiều thao tác quá nhanh',code:'rate_limited'}),json(200,state(99))]);
  [a]=api();await assert.rejects(a.command('x',{}),e=>e.status===429);assert.equal(c2.length,1);
  const c3=install([json(500,{error:'Không thực hiện được thao tác.',code:'internal_error'})]);
  [a]=api();await assert.rejects(a.command('x',{}),e=>e.status===500);assert.equal(c3.length,1,'500 is a bug, not a restart');
}
{ // the server never comes back: bounded retries, then the offline path (no endless spinner)
  const calls=install(Array.from({length:200},()=>html(502)));
  const [a,seen]=api();a.delays=[5,5,5];
  await assert.rejects(a.command('x',{}),e=>e.status===502&&/Mất kết nối/.test(e.message));
  assert.equal(calls.length,4,'1 + delays.length tries');assert.equal(seen.offline,1);assert.deepEqual(seen.updating,[true,false]);
  const c2=install(Array.from({length:200},()=>'down'));
  const [b,seen2]=api();b.retryWindow=30;
  const t0=Date.now();await assert.rejects(b.command('x',{}),e=>!e.status);assert.ok(Date.now()-t0<1000,'window bounds it');
  assert.ok(c2.length>=2);assert.equal(seen2.offline,1);
}
{ // commands keep their order: the second waits in the queue while the first retries
  const order=[];
  const calls=install([html(502),'down',b=>{order.push(b.action);return json(200,state(8));},b=>{order.push(b.action);return json(200,state(9));}]);
  const [a,seen]=api();
  const p1=a.command('first',{}),p2=a.command('second',{});
  await Promise.all([p1,p2]);
  assert.deepEqual(order,['first','second']);assert.deepEqual(calls.map(c=>c.body.action),['first','first','first','second']);
  assert.equal(calls[3].body.expected_revision,8,'the second one is sent with the revision the first produced');
  assert.equal(seen.results.length,2);
}
{ // reads (GET) retry by themselves; other writes (posts) are sent once
  let calls=install([html(503),'down',json(200,state(5))]);
  let [a]=api();await a.refresh();assert.equal(calls.length,3);assert.equal(a.revision,5);
  calls=install([html(502),json(200,{items:[]})]);
  [a]=api();assert.deepEqual((await a.socialGet('inbox')).items,[]);assert.equal(calls.length,2);
  calls=install([html(502),json(200,{ok:true})]);
  [a]=api();await assert.rejects(a.post('/api/social/gift',{to:'x'}),e=>e.status===502);assert.equal(calls.length,1,'a post is never re-sent');
  calls=install([html(502),json(200,{ok:true})]);
  [a]=api();await assert.rejects(a.json('/api/leaderboard?x=1',{retry:false}),e=>e.status===502);assert.equal(calls.length,1,'retry:false');
  calls=install([json(404,{error:'Không có API này.'})]);
  [a]=api();await assert.rejects(a.json('/api/nope'),e=>e.status===404);assert.equal(calls.length,1);
}
{ // boot: boot.js's early bootstrap got a 502 page: init() asks again (with retries) instead of failing
  globalThis.__mnlBoot={response:Promise.resolve(html(502)),sent:Date.now(),content:null,contentUrl:null,css:Promise.resolve()};
  const calls=install([html(502),json(200,{...state(3),csrf:'k',ai:{},content:{careers:{}}})]);
  const [a]=api();const data=await a.init();a.updates.stop?.();
  assert.equal(data.revision,3);assert.equal(calls.length,2);
  delete globalThis.__mnlBoot;
}
{ // the note: shown only after `after` ms, once, and removed with the last retry
  const body={children:[],append(el){this.children.push(el);}};
  const make=()=>({attrs:{},style:{},setAttribute(k,v){this.attrs[k]=v;},remove(){body.children=body.children.filter(x=>x!==this);}});
  const doc={body,createElement:make};
  const n=new UpdatingNote(()=>'vi',doc,20);
  n.hold();n.hold();assert.equal(body.children.length,0,'not at once');
  await new Promise(r=>setTimeout(r,40));
  assert.equal(body.children.length,1);const el=body.children[0];
  assert.equal(el.textContent,UPDATING_TEXT);assert.equal(el.attrs.role,'status');assert.match(el.style.cssText,/pointer-events:none/);
  n.release();assert.equal(body.children.length,1,'still one retry going');
  n.release();assert.equal(body.children.length,0,'gone');
  n.hold();n.release();await new Promise(r=>setTimeout(r,40));assert.equal(body.children.length,0,'a quick blip shows nothing');
  const en=new UpdatingNote(()=>'en',doc,0);en.hold();await new Promise(r=>setTimeout(r,5));assert.equal(body.children[0].textContent,'Updating the server…');en.release();
}
console.log('api_retry.mjs: ok');
process.exit(0);
