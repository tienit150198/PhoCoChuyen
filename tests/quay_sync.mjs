import assert from 'node:assert/strict';
import {createQuaySync} from '../public/js/v4/quay-sync.js';

const pending=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const journey=(wallet=10)=>({story:true,life_day:1,wallet,quay:{stalls:[]}});
const projection=(revision,wallet=10)=>({revision,journey:journey(wallet)});
const api=()=>Object.assign(new EventTarget(),{revision:1,accepted:1,state:{journey:journey()},account:{username:'a'},csrf:'session-a'});

{
 const a=api();let renders=0,states=0;
 a.addEventListener('state',()=>states++);a.json=async url=>{assert.equal(url,'/api/business/quay');return projection(2,25);};
 const sync=createQuaySync(a,()=>renders++);
 await sync.refresh();assert.equal(sync.journey().wallet,25);assert.equal(a.state.journey.wallet,10);assert.equal(a.revision,1);assert.equal(states,0);assert.equal(renders,1);
 await sync.refresh();assert.equal(renders,1,'Identical projection does not redraw');
}
{
 const a=api(),p=pending();a.json=()=>p.promise;const sync=createQuaySync(a);
 const read=sync.refresh();a.revision=3;a.accepted++;a.state={journey:journey(30)};a.dispatchEvent(new Event('state'));p.resolve(projection(2,20));await read;
 assert.equal(sync.journey().wallet,30,'Late read cannot replace command result');
}
{
 const a=api(),p=pending();a.json=()=>p.promise;const sync=createQuaySync(a);
 const read=sync.refresh();a.csrf='session-b';a.account={username:'b'};a.revision=0;a.accepted++;a.state={journey:journey(99)};a.dispatchEvent(new Event('state'));p.resolve(projection(9,20));await read;
 assert.equal(sync.journey().wallet,99,'Late read from previous login is discarded');
}
{
 const a=api();a.json=async()=>projection(5,50);const sync=createQuaySync(a);await sync.refresh();let refreshes=0,commands=0;
 a.refresh=async()=>{refreshes++;a.revision=5;a.state={journey:journey(50)};a.dispatchEvent(new Event('state'));};
 a.command=async(action,payload)=>{commands++;assert.equal(a.revision,5);assert.equal(action,'jr_quay_collect');assert.deepEqual(payload,{stall:'q1'});return {message:'ok'};};
 assert.deepEqual(await sync.command('jr_quay_collect',{stall:'q1'}),{message:'ok'});assert.equal(refreshes,1);assert.equal(commands,1);
 await sync.command('jr_quay_collect',{stall:'q1'});assert.equal(refreshes,1,'No full refresh for already current revision');assert.equal(commands,2);
}
{
 const a=api();a.json=async()=>projection(5,50);const sync=createQuaySync(a);await sync.refresh();let commands=0;
 a.refresh=async()=>{throw new Error('offline');};a.command=async()=>commands++;
 await assert.rejects(sync.command('jr_quay_collect'),/offline/);assert.equal(commands,0,'Failed prerequisite cannot send stale command');
}
{
 const a=api();a.json=async()=>projection(5,50);const sync=createQuaySync(a);await sync.refresh();let refreshes=0;
 a.refresh=async()=>{if(++refreshes===2){a.revision=5;a.state={journey:journey(50)};a.dispatchEvent(new Event('state'));}};
 await sync.ensureCurrent();assert.equal(refreshes,2,'An older coalesced full read is followed by a fresh read');assert.equal(a.state.journey.wallet,50);
}
{
 const a=api(),p=pending();a.json=()=>p.promise;const sync=createQuaySync(a);const poll=sync.refresh();let commands=0,refreshes=0;
 a.refresh=async()=>{refreshes++;a.revision=7;a.state={journey:journey(70)};a.dispatchEvent(new Event('state'));};
 a.command=async()=>{commands++;assert.equal(a.revision,7);return {message:'ok'};};
 const command=sync.command('jr_quay_till');assert.equal(commands,0);p.resolve(projection(7,70));await Promise.all([poll,command]);assert.equal(commands,1);assert.equal(refreshes,1);
}
{
 const a=api();let calls=0;a.json=async()=>{if(++calls===1)throw Error('offline');return projection(2,20);};const sync=createQuaySync(a);
 await assert.rejects(sync.refresh(),/offline/);await sync.refresh();assert.equal(sync.journey().wallet,20);assert.equal(calls,2);
}
{
 const a=api(),p=pending();let calls=0;a.json=()=>{calls++;return p.promise;};const sync=createQuaySync(a);
 const first=sync.refresh(),second=sync.refresh();assert.equal(calls,1);p.resolve(projection(2));await Promise.all([first,second]);
 sync.dispose();a.revision=3;a.state={journey:journey(30)};a.dispatchEvent(new Event('state'));assert.equal(sync.journey().wallet,30);
}
console.log('Quay projection sync: race, account isolation, no full renders, command guard, retry and coalescing passed');
