// Unit test of public/js/v4/wealth.js (💰 the top bar chips and "Tiền của bạn").
// Run by tests/test_wealth.py (node tests/wealth.mjs); exits non-zero on failure.
import assert from 'node:assert/strict';
import {shortNum,hudMoney,hudChipsHTML,pockets,wealthHTML,married,fundMove,fundMoveHTML,investMax,firstAmount,MOVE,wealthAction} from '../public/js/v4/wealth.js';

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
// 💼 F#259: the place on screen is open (here milk_tea, nothing to draw → Góp vốn), the others fold to two tabs.
assert.match(html,/data-wl-move="milk_tea"[^>]*>|class="wl-move open" data-wl-move="milk_tea"/);
assert.match(html,/class="wl-move open" data-wl-move="milk_tea">.*data-action="wlInvest" data-career="milk_tea" data-amount="50">Góp 50 xu vào quỹ/s);
assert.match(html,/class="wl-move" data-wl-move="florist"><div class="wl-tabs"[^]*?data-mode="draw" data-fold="1" aria-pressed="false">👛 Rút về ví[^]*?data-mode="invest" data-fold="1" aria-pressed="false">📈 Góp vốn/);
assert.doesNotMatch(html,/data-action="wlDraw" data-career="florist"/,'a folded row has no amount yet');
assert.doesNotMatch(html,/data-action="wlDraw" data-career="milk_tea"/,'nothing to withdraw: no Rút button');
// Open a move: a quarter by default (never "all"), − N + typed box, 25% / 50% / Tất cả, what stays in the fund.
assert.equal(investMax(rich),120+800,'Góp vốn: the wallet, then the bank account');
assert.equal(investMax({journey:{story:true,wallet:-5,bank:{open:true,balance:900}}}),0,'a wallet in debt puts nothing in');
assert.equal(investMax({journey:{story:true,wallet:30,invest_max:77}}),77,'the server says it first');
assert.equal(firstAmount('draw',320),80);assert.equal(firstAmount('draw',1),1);assert.equal(firstAmount('draw',3),1);assert.equal(firstAmount('invest',920),50);assert.equal(firstAmount('invest',20),20);assert.equal(firstAmount('draw',0),0);
let mv=fundMove(rich,'florist',{open:true});
assert.deepEqual([mv.mode,mv.max,mv.n,mv.fund],['draw',320,80,500]);
html=fundMoveHTML(rich,'florist',{open:true});
assert.match(html,/data-mode="draw" aria-pressed="true">👛 Rút về ví/);
assert.match(html,/data-action="wlAmt" data-quick data-career="florist" data-n="70" aria-label="Bớt 10 xu">−/);
assert.match(html,/<input class="qty-in"[^>]*data-min="1" data-max="320"[^>]*value="80"[^>]*data-qty-money data-qty-go="data-action=&quot;wlAmt&quot; data-quick data-career=&quot;florist&quot; data-n=&quot;987654321&quot;" data-qty-live[^>]*id="wl-amt-florist"/);
assert.match(html,/data-n="80" aria-pressed="true">25%<\/button>.*data-n="160" aria-pressed="false">50%<\/button>.*data-n="320" aria-pressed="false">Tất cả<\/button>/s);
assert.match(html,/Quỹ còn lại <b>420 xu<\/b>/);
assert.match(html,/data-action="wlDraw" data-career="florist" data-amount="80">Rút 80 xu về ví/);
MOVE.amt['florist:draw']=999;assert.equal(fundMove(rich,'florist',{open:true}).n,320,'a typed number over the max is the max');
MOVE.amt['florist:draw']=0;assert.equal(fundMove(rich,'florist',{open:true}).n,1);
delete MOVE.amt['florist:draw'];
MOVE.mode.florist='invest';
mv=fundMove(rich,'florist');assert.ok(mv.open,'a chosen move opens a folded row');
MOVE.amt['florist:invest']=200;mv=fundMove(rich,'florist');
assert.deepEqual([mv.mode,mv.n,mv.cash,mv.bank],['invest',200,120,80]);
html=fundMoveHTML(rich,'florist');
assert.match(html,/Quỹ thành <b>700 xu<\/b> · lấy 120 xu từ ví, 80 xu từ tài khoản ngân hàng/);
assert.match(html,/data-action="wlInvest" data-career="florist" data-amount="200">Góp 200 xu vào quỹ/);
delete MOVE.mode.florist;delete MOVE.amt['florist:invest'];
html=fundMoveHTML(poorState,'grocery',{open:true});
assert.match(html,/data-action="wlDraw" data-career="grocery" data-amount="10">Rút 10 xu về ví/);
MOVE.mode.grocery='invest';html=fundMoveHTML(poorState,'grocery',{open:true});delete MOVE.mode.grocery;
assert.match(html,/Ví đang nợ\. Trả nợ trước rồi góp vốn nhé\./);assert.doesNotMatch(html,/wlInvest/);
const thin={journey:{story:true,wallet:200,places:{grocery:{fund:90,withdraw_max:0}}}};
assert.match(fundMoveHTML(thin,'grocery',{open:true}),/data-mode="invest" aria-pressed="true">📈 Góp vốn.*data-action="wlInvest"/s,'nothing to draw: Góp vốn opens first');
MOVE.mode.grocery='draw';html=fundMoveHTML(thin,'grocery',{open:true});delete MOVE.mode.grocery;
assert.match(html,/Chưa rút được: quỹ phải giữ 80 xu/);assert.doesNotMatch(html,/data-action="wlDraw"/);
// The actions: a confirm that says what stays in the fund, then the server command with the typed amount.
{
  const sent=[],asked=[];let renders=0;
  const env={api:{state:rich},renderSheet:()=>{renders++;},placeName:()=>'Tiệm hoa Mây',
    confirmAction:async(t,m,l)=>{asked.push([t,m,l]);return true;},cmd:async(c,p)=>{sent.push([c,p]);return {};}};
  assert.equal(await wealthAction('somethingElse',{},null,env),false);
  await wealthAction('wlAmt',{career:'florist',n:'150'},null,env);
  assert.equal(MOVE.amt['florist:draw'],150);
  await wealthAction('wlDraw',{career:'florist',amount:'150'},null,env);
  assert.deepEqual(sent.pop(),['jr_withdraw',{career:'florist',amount:150}]);
  assert.match(asked.pop()[1],/quỹ còn lại 350 xu/);
  assert.equal(MOVE.amt['florist:draw'],undefined,'done: back to the default amount');
  await wealthAction('wlDraw',{career:'florist',amount:'320'},null,env);
  assert.match(asked.pop()[1],/đây là mức rút tối đa, quỹ chỉ còn 180 xu/);sent.pop();
  await wealthAction('wlMode',{career:'florist',mode:'invest',fold:'1'},null,env);
  assert.equal(MOVE.mode.florist,'invest');
  await wealthAction('wlInvest',{career:'florist',amount:'500'},null,env);
  assert.deepEqual(sent.pop(),['jr_invest',{career:'florist',amount:500}]);
  assert.match(asked.pop()[1],/Lấy 120 xu từ ví và 380 xu từ tài khoản ngân hàng\. Quỹ thành 1\.000 xu\./);
  await wealthAction('wlMode',{career:'florist',mode:'invest',fold:'1'},null,env);
  assert.equal(MOVE.mode.florist,undefined,'tapping the open move again folds the row');
  const no={...env,confirmAction:async()=>false};
  await wealthAction('wlDraw',{career:'florist',amount:'20'},null,no);
  assert.equal(sent.length,0,'no confirm, no command');
  assert.ok(renders>=4);
}
html=wealthHTML(rich,{joint:300,current:'milk_tea',place});
for(const a of ['data-action="stView" data-view="wallet"','data-action="bank"','data-action="house"','data-action="marriage"'])assert.ok(html.includes(a),a);
// Feedback #110: a real button into Ngân hàng Phố on the bank's first row, not only a small header link.
assert.match(html,/data-wl="account"[^]*?<div class="wl-extra"><button type="button" class="btn small" data-action="bank">[^<]*<span aria-hidden="true">🏦<\/span> Vào Ngân hàng<\/button>/);
html=wealthHTML(poorState);
assert.doesNotMatch(html,/data-wl-debt="0"/);assert.match(html,/data-wl-debt="40"/);
assert.match(html,/Chưa mở tài khoản/);assert.match(html,/data-wl="bank-none"[^]*?data-action="bank"><span aria-hidden="true">🏦<\/span> Mở tài khoản<\/button>/);assert.doesNotMatch(html,/data-wl="joint"|data-wl="home"/);
assert.doesNotMatch(wealthHTML({journey:{story:true,wallet:5,places:{},bank:{open:false}}}),/data-wl-debt/,'no debt: no "Nợ" line');

// Several homes (housing.py VERSION 2): every one counts, the empty and the let ones too.
const two={journey:{story:true,wallet:0,life_day:9,places:{},bank:{open:false},home:{own:{kind:'tap_the',name:'Căn tập thể cũ',value:1800},
  props:[{kind:'nha_pho',name:'Nhà phố nhỏ',emoji:'🏠',value:7800,loan:{left:5000},let:{rent:33}},{kind:'can_ho_mini',name:'Căn hộ mini',value:3600,let:null}]}}};
const PT=pockets(two);
assert.deepEqual(PT.homes.map(x=>[x.kind,x.live,Boolean(x.let)]),[['tap_the',true,false],['nha_pho',false,true],['can_ho_mini',false,false]]);
assert.equal(PT.assets,1800+7800+3600);assert.equal(PT.debt,5000);assert.equal(PT.home.kind,'tap_the');
html=wealthHTML(two);
assert.match(html,/đang cho thuê/);assert.match(html,/đang để trống/);assert.match(html,/Vay mua nhà phố nhỏ/);

// Married: from the marriage view or the house view.
assert.ok(married({marriage:{spouse:{status:'married'}}}));
assert.ok(married({journey:{home:{married:true}}}));
assert.ok(!married({marriage:{spouse:{status:'engaged'}}}));

console.log('wealth: ok');
