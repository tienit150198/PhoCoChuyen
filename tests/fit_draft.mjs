// Unit test of restock.js fitDraft: the "🛒 Gộp N món" draft the stock room offers (views.js fillGo) holds
// no more lines than the supplier's draft has left and costs no more than the fund. Run by
// tests/test_fit_draft.py; with a JSON argument ({lines, sup, money, free, have}) it prints the draft instead,
// which the Python side places on the real server rules.
import assert from 'node:assert/strict';
import {fitDraft,orderQuote} from '../public/js/v4/restock.js';

if(process.argv[2]){
  const a=JSON.parse(process.argv[2]);
  process.stdout.write(JSON.stringify(fitDraft(a.lines,a.sup,a.money,{free:a.free,have:a.have})));
  process.exit(0);
}

const sup={factor:1,bulk:[[10,4],[20,8]],ship:3,free_from:60};
const cost=(lines,s=sup,have=0)=>{const g=have+lines.reduce((n,l)=>n+orderQuote({cost:8},l.q,s).cost,0);return g+(g>=s.free_from?0:s.ship);};
const gels=n=>Array.from({length:n},(_,i)=>({id:'g'+i,cost:8,q:10}));

// Twenty items low, plenty of money: the first `free` lines, quantities kept.
let d=fitDraft(gels(20),sup,1e6,{free:8});
assert.equal(d.length,8);
assert.deepEqual(d.map(l=>l.id),gels(8).map(l=>l.id));
assert.ok(d.every(l=>l.q===10));
// Only the lines the draft still has room for.
assert.equal(fitDraft(gels(20),sup,1e6,{free:3}).length,3);
assert.equal(fitDraft(gels(20),sup,1e6,{free:0}).length,0);

// The nail shop's 320 xu: quantities come down evenly until the fund pays for it (ship included).
d=fitDraft(gels(20),sup,320,{free:8});
assert.equal(d.length,8);
assert.ok(cost(d)<=320,`costs ${cost(d)}`);
assert.ok(Math.max(...d.map(l=>l.q))-Math.min(...d.map(l=>l.q))<=1,'trimmed evenly');
// Goods already in the draft count.
d=fitDraft(gels(8),sup,320,{free:8,have:200});
assert.ok(cost(d,sup,200)<=320);
// Too little money for one unit each: lines drop from the end; nothing fits: empty.
d=fitDraft(gels(8),sup,30,{free:8});
assert.ok(d.length>0&&d.length<8&&cost(d)<=30&&d.every(l=>l.q===1),JSON.stringify(d));
assert.deepEqual(fitDraft(gels(8),sup,5,{free:8}),[]);
// Quantities stay 1–30; zero or junk lines are left out.
d=fitDraft([{id:'a',cost:1,q:99},{id:'b',cost:1,q:0},{id:'c',cost:1,q:'x'}],sup,1e6);
assert.deepEqual(d,[{id:'a',q:30}]);
console.log('fit_draft ok');
