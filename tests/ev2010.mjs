// 💐 Thiệp 20/10 in the game (public/js/v4/ev2010.js, isometric/town-utilities.js): which card opens by itself, the entries' window.
import assert from 'node:assert/strict';
import {due} from '../public/js/v4/ev2010.js';
import {EV2010_UNTIL,ev2010Open,townUtilityGroups,townServiceAvailable} from '../public/js/isometric/town-utilities.js';

const s=(day,more={})=>({journey:{story:true,intro:true,life_day:day,...more}});
const acct={username:'lan'};
// the season's card: once a device, never on a new neighbour's first day
assert.equal(due(s(2),null,{seen:'',coming:false,open:true}),'news');
assert.equal(due(s(1),null,{seen:'',coming:false,open:true}),'',"a new neighbour's first day");
assert.equal(due(s(5),acct,{seen:'1',coming:false,open:true}),'','seen on this device');
assert.equal(due(s(5),acct,{seen:'blocked',coming:false,open:true}),'','no storage: never every load');
assert.equal(due(s(5),acct,{seen:'',coming:false,open:false}),'','the window closed');
assert.equal(due({journey:{story:false}},null,{seen:'',coming:false,open:true}),'news','a free-play save too');
// the way back from /2010's sign-in: only once there is an account, never over the form
assert.equal(due(s(1),null,{seen:'',coming:true,open:true}),'');
assert.equal(due(s(1),acct,{seen:'1',coming:true,open:true}),'back');
// the window: 21/10/2026 23:59:59 VN
assert.equal(new Date(EV2010_UNTIL).toISOString(),'2026-10-20T16:59:59.000Z');
assert.ok(ev2010Open(EV2010_UNTIL)&&!ev2010Open(EV2010_UNTIL+1000));
const has=()=>townUtilityGroups(s(5),{},{}).some(g=>g.items.some(i=>i.action==='ev2010'));
assert.equal(townServiceAvailable('ev2010'),ev2010Open());
assert.equal(has(),ev2010Open());
console.log('ev2010 ok');
