// Unit test of public/js/v4/wealth.js (💰 the top bar chips and "Tiền của bạn").
// Run by tests/test_wealth.py (node tests/wealth.mjs); exits non-zero on failure.
import assert from 'node:assert/strict';
import {shortNum,hudMoney,hudChipsHTML,pockets,wealthHTML,married} from '../public/js/v4/wealth.js';

// Short numbers (no "xu") only for big sums.
assert.equal(shortNum(358),'358');
assert.equal(shortNum(99999),'99.999');
assert.equal(shortNum(125400),'125,4k');
assert.equal(shortNum(3373500),'3,37tr');

// The top bar: this workplace's fund and the wallet; free play has no wallet.
const base={journey:{story:true,wallet:14,life_day:20,places:{}},careers:{florist:{money:358}}};
assert.deepEqual(hudMoney(base,'florist'),{fund:358,wallet:14});
assert.deepEqual(hudMoney({journey:{story:false,wallet:60},careers:{florist:{money:9}}},'florist'),{fund:9,wallet:null});
assert.deepEqual(hudMoney({careers:{florist:{money:9}}},'florist'),{fund:9,wallet:null});
let html=hudChipsHTML({fund:358,wallet:14});
assert.match(html,/hud-fund[^>]*data-action="money".*🏪.*<small>Quỹ<\/small><b data-testid="money">358<\/b>/);
assert.match(html,/hud-wallet[^>]*data-action="money".*👛.*<small>Ví<\/small><b data-testid="wallet">14<\/b>/);
html=hudChipsHTML({fund:358,wallet:-40});
assert.match(html,/class="hud-chip hud-wallet neg"[^>]*aria-label="Ví đang nợ 40 xu/,'a wallet in debt is red and says so');
assert.match(html,/👛<\/span><b data-testid="wallet">−40<\/b>/,'debt: "👛 −40", no label');
assert.match(hudChipsHTML({fund:125400,wallet:3373500},{phone:true}),/>125,4k<.*>3,37tr</,'phones shorten big numbers');
assert.match(hudChipsHTML({fund:125400,wallet:5},{phone:true,short:n=>`S${n}`}),/>S125400</,'app.js passes its shortMoney');
assert.match(hudChipsHTML({fund:125400,wallet:5}),/>125\.400</,'full numbers off the phone');
assert.doesNotMatch(hudChipsHTML({fund:9,wallet:null}),/hud-wallet/);
assert.match(hudChipsHTML({fund:12345,wallet:45678},{phone:true}),/hud-fund tight.*hud-wallet tight/,'long numbers on a phone: tight chips');
assert.match(hudChipsHTML({fund:294,wallet:3000},{phone:true}),/tight/);
assert.doesNotMatch(hudChipsHTML({fund:358,wallet:14},{phone:true}),/tight/,'short numbers keep the emoji');
assert.doesNotMatch(hudChipsHTML({fund:12345,wallet:45678}),/tight/,'never off the phone');

// Every pocket.
const rich={journey:{story:true,wallet:120,life_day:40,
  places:{florist:{fund:500,withdraw_max:320,employed:false,paused:false},milk_tea:{fund:90,withdraw_max:0,employed:false,paused:true},
          teacher:{fund:0,withdraw_max:0,employed:true,paused:false}},
  bank:{open:true,balance:800,savings:{demand:50,total:1250,terms:[{id:'T1',name:'12 tháng',amount:400,value:436,due:100,days_left:60}]},
        loans:[{id:'L1',name:'Vay tiêu dùng',emoji:'💸',left:210,overdue:0},{id:'L2',name:'Vay đã trả',emoji:'💸',left:0}],card:{bal:35}},
  home:{married:true,own:{kind:'can_ho_1pn',name:'Căn hộ Mây Xanh',emoji:'☁️',value:5600,loan:{left:3900}}}},
  careers:{florist:{money:500}}};
const P=pockets(rich,{joint:300,current:'milk_tea'});
assert.equal(P.wallet,120);
assert.deepEqual(P.places.map(p=>p.cid),['milk_tea','florist','teacher'],'the workplace on screen first, then the richest');
assert.equal(P.places.find(p=>p.cid==='florist').max,320);
assert.equal(P.bank.balance,800);assert.equal(P.bank.demand,50);
assert.deepEqual(P.bank.loans.map(l=>l.id),['L1'],'paid-off loans are not debt');
assert.equal(P.bank.card,35);
assert.equal(P.joint,300);
assert.deepEqual(P.home,{kind:'can_ho_1pn',name:'Căn hộ Mây Xanh',emoji:'☁️',value:5600,loan:3900});
assert.equal(P.assets,120+500+90+0+800+50+400+300+5600);
assert.equal(P.debt,210+35+3900);
assert.equal(P.net,P.assets-P.debt);

// Debt in the wallet counts as debt, not as a negative asset; no bank account yet.
const poorState={journey:{story:true,wallet:-40,life_day:3,places:{grocery:{fund:120,withdraw_max:40}},bank:{open:false}}};
const poor=pockets(poorState);
assert.equal(poor.assets,120);assert.equal(poor.debt,40);assert.equal(poor.bank.open,false);assert.equal(poor.joint,null);assert.equal(poor.home,null);
// Free play: no wallet, no bank, funds without withdrawals.
const free=pockets({journey:{story:false,wallet:60,places:{florist:{fund:77,withdraw_max:0}}}},{joint:500});
assert.equal(free.wallet,null);assert.equal(free.bank,null);assert.equal(free.joint,null);assert.equal(free.places[0].max,0);assert.equal(free.assets,77);
// No journey at all: the current place's fund.
assert.deepEqual(pockets({careers:{pharmacy:{money:360}}},{current:'pharmacy'}).places.map(p=>[p.cid,p.fund]),[['pharmacy',360]]);

// The sheet: every row, totals, links to the existing screens, the withdraw button with its max.
const place=cid=>({name:{florist:'Tiệm hoa Mây',milk_tea:'Quán trà sữa',teacher:'Lớp Mầm Nắng'}[cid]||cid,emoji:'🏪'});
html=wealthHTML(rich,{joint:300,current:'milk_tea',place});
assert.match(html,new RegExp(`data-wl-total="${P.assets}">${P.assets.toLocaleString('vi-VN')} xu`));
assert.match(html,new RegExp(`data-wl-debt="${P.debt}">−${P.debt.toLocaleString('vi-VN')} xu`));
for(const id of ['wallet','account','demand','term','loan','card','fund','joint','home','home-loan'])assert.match(html,new RegExp(`data-wl="${id}"`),id);
assert.match(html,/12 tháng.*đáo hạn Ngày 100 · còn 60 ngày/);
assert.match(html,/data-action="wlDraw" data-career="florist" data-amount="320">Rút về ví · tối đa 320 xu/);
assert.doesNotMatch(html,/data-action="wlDraw" data-career="milk_tea"/,'nothing to withdraw: no button');
for(const a of ['data-action="stView" data-view="wallet"','data-action="bank"','data-action="house"','data-action="marriage"'])assert.ok(html.includes(a),a);
html=wealthHTML(poorState);
assert.doesNotMatch(html,/data-wl-debt="0"/);assert.match(html,/data-wl-debt="40"/);
assert.match(html,/Chưa mở tài khoản/);assert.doesNotMatch(html,/data-wl="joint"|data-wl="home"/);
assert.doesNotMatch(wealthHTML({journey:{story:true,wallet:5,places:{},bank:{open:false}}}),/data-wl-debt/,'no debt: no "Nợ" line');

// Married: from the marriage view or the house view.
assert.ok(married({marriage:{spouse:{status:'married'}}}));
assert.ok(married({journey:{home:{married:true}}}));
assert.ok(!married({marriage:{spouse:{status:'engaged'}}}));

console.log('wealth: ok');
