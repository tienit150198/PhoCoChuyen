import assert from 'node:assert/strict';
import test from 'node:test';

const shops=await import('../public/js/isometric/resident-shops.js').catch(()=>({}));
const row=(id='wp_a',extra={})=>({id,name:'Tiệm Trà',kind:'career',target:'milk_tea',visibility:'public',owner:{name:'An'},...extra});

test('directory normalizes only real public workplaces, removes duplicates and bounds entries',()=>{
  assert.equal(typeof shops.normalizeResidentShops,'function');
  const out=shops.normalizeResidentShops({places:[null,row(),row(),row('private',{visibility:'friends'}),row('closed',{visibility:'closed'}),row('broken',{kind:'land'}),row('missing',{name:''}),...Array.from({length:40},(_,i)=>row('wp_'+i,{kind:'quay',target:'stall_'+i,career:'boba'}))]});
  assert.equal(out.length,24);
  assert.deepEqual(out[0],{id:'wp_a',name:'Tiệm Trà',kind:'career',target:'milk_tea',ownerName:'An',career:'milk_tea'});
  assert.equal(out[1].kind,'quay');assert.equal(out[1].career,'boba');
  assert.equal(out.some(x=>['private','closed','broken','missing'].includes(x.id)),false);
});

test('loading is explicit, guests make no requests, parallel opens reuse one request and TTL is at least 60 seconds',async()=>{
  assert.equal(typeof shops.createResidentDirectory,'function');
  let now=0,calls=0,resolve;const api={account:null,json:(url,options)=>{calls++;assert.equal(url,'/api/work-visits/places?scope=public');assert.equal(options.retry,false);return new Promise(r=>{resolve=r;});}};
  const cache=shops.createResidentDirectory({now:()=>now,ttlMs:1});
  assert.equal(cache.read(api).status,'guest');await cache.load(api);assert.equal(calls,0);
  api.account={username:'an'};assert.equal(cache.read(api).status,'idle');assert.equal(calls,0);
  const a=cache.load(api),b=cache.load(api);assert.equal(calls,1);assert.equal(cache.read(api).status,'loading');
  resolve({places:[row()]});await Promise.all([a,b]);assert.equal(cache.read(api).status,'ready');
  now=59999;await cache.load(api);assert.equal(calls,1);
  now=60000;const c=cache.load(api);assert.equal(calls,2);resolve({places:[]});await c;assert.equal(cache.read(api).status,'empty');
});

test('failed requests are bounded and malformed data is an error rather than a false empty street',async()=>{
  assert.equal(typeof shops.createResidentDirectory,'function');
  let calls=0,now=0;const api={account:{username:'an'},json:async()=>{calls++;throw Error('offline');}};
  const cache=shops.createResidentDirectory({now:()=>now});
  await cache.load(api);assert.equal(cache.read(api).status,'error');
  await cache.load(api);assert.equal(calls,1);
  now=60001;api.json=async()=>{calls++;return {};};await cache.load(api);assert.equal(cache.read(api).status,'error');assert.equal(calls,2);
});

test('an account switch or logout invalidates old directory data and in-flight responses',async()=>{
  assert.equal(typeof shops.createResidentDirectory,'function');
  const requests=[];const api={account:{username:'an'},json:()=>new Promise(resolve=>requests.push(resolve))};
  const cache=shops.createResidentDirectory();
  const old=cache.load(api);api.account={username:'binh'};const next=cache.load(api);
  requests[0]({places:[row('old')]});await old;assert.equal(cache.read(api).status,'loading');assert.equal(cache.read(api).shops.length,0);
  requests[1]({places:[row('new')]});await next;assert.equal(cache.read(api).shops[0].id,'new');
  api.account=null;assert.equal(cache.read(api).status,'guest');assert.equal(cache.read(api).shops.length,0);
});

test('a replaced API cannot reset the new account when its old request finishes',async()=>{
  let finishOld;const oldApi={account:{username:'an'},json:()=>new Promise(r=>{finishOld=r;})};
  const newApi={account:{username:'binh'},json:async()=>({places:[row('new')]})};
  const cache=shops.createResidentDirectory();const old=cache.load(oldApi);await cache.load(newApi);
  finishOld({places:[row('old')]});await old;
  assert.equal(cache.read(newApi).shops[0]?.id,'new');
});
