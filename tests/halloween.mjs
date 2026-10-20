// 🎃 Lễ hội Ma Phố in the client (v4/halloween-data.js, v4/halloween.js, isometric/town-utilities.js): the season's status
// from the server, the start card's rule and the Tiện ích entry's window. The server decides the dates (game/halloween.py).
import assert from 'node:assert/strict';
import {seedHween,setHween,hwNow,hwOpen,hwShown,hwNight,vnDay,_reset} from '../public/js/v4/halloween-data.js';
import {due,cardKey} from '../public/js/v4/halloween.js';
import {townUtilityGroups,townServiceAvailable} from '../public/js/isometric/town-utilities.js';

const now=Date.now()/1000;
const hint=(state,o={})=>({state,starts:now-3600,ends:now+86400,until:now+2*86400,night:now+80000,now,day:1,title:'Phố treo đèn bí ngô',icon:'🎃',...o});
const has=s=>townUtilityGroups(s,{},{}).some(g=>g.items.some(i=>i.action==='halloween'));
const s=(day,more={})=>({journey:{story:true,intro:true,life_day:day,...more}});
const acct={username:'lan'};

// nothing without the server's word: no hint (before 26/10, kill switch, over) → nothing shows
_reset();seedHween(null);
assert.equal(hwNow(),null);assert.ok(!hwShown()&&!hwOpen());
assert.ok(!has(s(5)),'no Tiện ích entry before the season');
assert.equal(townServiceAvailable('halloween'),false);
_reset();seedHween({state:'before'});assert.equal(hwNow(),null,'an unknown state is nothing');
_reset();seedHween({state:'open',starts:'x'});assert.equal(hwNow(),null,'no end date: nothing (never forever)');

// open: shown, in Tiện ích for a story save only
_reset();seedHween(hint('open'));
assert.ok(hwOpen()&&hwShown()&&!hwNight());
assert.ok(has(s(5)));assert.ok(!has({journey:{story:false}}),'free play: no entry');
// the night of 31/10
_reset();seedHween(hint('open',{night:now-60}));assert.ok(hwNight());
assert.ok(cardKey().endsWith(':night'));
// the season moved on since the poll: open → grace → gone, without waiting for the server
_reset();seedHween(hint('open',{ends:now-1}));assert.equal(hwNow().state,'grace');assert.ok(!hwOpen()&&hwShown()&&!hwNight());
_reset();seedHween(hint('grace',{ends:now-10,until:now-1}));assert.equal(hwNow(),null);
// a server clock ahead of the device's: the skew counts
_reset();seedHween(hint('open',{ends:now+30,now:now+60}));assert.equal(hwNow().state,'grace','server time, not the device');

// setHween fires the event once per change
_reset();let fired=0;globalThis.document={dispatchEvent:e=>{if(e.type==='mnl:hween')fired++;}};
setHween(hint('open'));setHween(hint('open'));assert.equal(fired,1);
setHween(null);assert.equal(fired,2);assert.equal(hwNow(),null);
delete globalThis.document;

// the start card: open season, an account, past the first day, once per key on a device
assert.equal(vnDay(Date.UTC(2026,9,25,17,0,0)/1000),'2026-10-26','00:00 in Vietnam');
assert.equal(cardKey(false,'2026-10-26'),'2026-10-26');assert.equal(cardKey(true,'2026-10-31'),'2026-10-31:night');
const o={open:true,seen:'',key:'2026-10-26'};
assert.equal(due(s(3),acct,o),true);
assert.equal(due(s(3),null,o),false,'a guest: the sheet asks to sign in, no card');
assert.equal(due(s(1),acct,o),false,"a new neighbour's first day");
assert.equal(due(s(3),acct,{...o,seen:'2026-10-26'}),false,'seen today');
assert.equal(due(s(3),acct,{...o,seen:'2026-10-25'}),true,'a new day');
assert.equal(due(s(3),acct,{...o,seen:'blocked'}),false,'no storage: never every load');
assert.equal(due(s(3),acct,{...o,open:false}),false,'the grace day: no card');
assert.equal(due({journey:{story:false}},acct,o),false);
console.log('halloween ok');
