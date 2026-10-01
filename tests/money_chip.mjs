// Unit test of public/js/v4/money.js (the 💰 Ví / Quỹ tiệm chip and the confirm's "còn thiếu" line).
// Run by tests/test_money_chip.py (node tests/money_chip.mjs); exits non-zero on failure.
import assert from 'node:assert/strict';
import {shortXu,fundLabel,balances,chipHTML,chipText,priceIn,isSpend,shortfall,confirmMoney,confirmShort} from '../public/js/v4/money.js';

// Formatting: full numbers, shortened only on phones and only when big.
assert.equal(shortXu(1234),'1.234 xu');
assert.equal(shortXu(125400,true),'125,4k xu');
assert.equal(shortXu(3373500,true),'3,37tr xu');
assert.equal(shortXu(99999,true),'99.999 xu');

// The workplace's own money word, never "Ví …" (that is the player's wallet).
assert.equal(fundLabel('Ví của tiệm'),'Quỹ tiệm');
assert.equal(fundLabel('Ví của homestay'),'Quỹ tiệm');
assert.equal(fundLabel('Quỹ lớp'),'Quỹ lớp');
assert.equal(fundLabel('Quỹ'),'Quỹ tiệm');
assert.equal(fundLabel('Túi tiền lẻ'),'Túi tiền lẻ');

// Scopes: wallet only, wallet + the place's fund, nothing.
const state={journey:{wallet:60},careers:{florist:{money:314}}};
assert.deepEqual(balances(state,{fund:null}),{wallet:60,fund:null,fundName:'Quỹ tiệm'});
assert.deepEqual(balances(state,{fund:'florist'},'Ví của tiệm'),{wallet:60,fund:314,fundName:'Quỹ tiệm'});
assert.equal(balances(state,null),null);
assert.equal(balances({careers:{}},{fund:null}),null,'no journey, no fund: no chip');
assert.equal(balances({journey:{story:false,wallet:60},careers:{}},{fund:null}),null,'free play has no wallet');
assert.deepEqual(balances({journey:{story:false,wallet:60},careers:{florist:{money:9}}},{fund:'florist'}),{wallet:null,fund:9,fundName:'Quỹ tiệm'});
assert.deepEqual(balances({careers:{farm:{money:5}}},{fund:'farm'},'Quỹ nông trại'),{wallet:null,fund:5,fundName:'Quỹ nông trại'});

const both=balances(state,{fund:'florist'},'');
assert.equal(chipText(both),'Ví 60 xu, Quỹ tiệm 314 xu');
assert.match(chipHTML(both),/👛.*Ví <b>60 xu<\/b>.*🏪.*Quỹ tiệm <b>314 xu<\/b>/);
assert.match(chipHTML({wallet:-20,fund:null}),/class="mn-part mn-wallet neg".*−20 xu/,'a wallet in debt shows as negative');
assert.equal(chipHTML(null),'');

// Reading a confirm: one price, spending words only.
assert.equal(priceIn('Đặt hàng?','10 nhánh Baby trắng: trả 10 xu ngay.'),10);
assert.equal(priceIn('Mua nhẫn?','1.200 xu được trừ từ ví.','Mua · 1.200 xu'),1200,'same price twice is one price');
assert.equal(priceIn('Nộp 50 xu?','Ví còn 10 xu sau khi nộp.'),null,'two amounts: unknown');
assert.equal(priceIn('Không có tiền ở đây'),null);
assert.ok(isSpend('Mua hàng ở chợ?'));
assert.ok(isSpend('Xác nhận','Nhập hỏa tốc 10 hộp sữa · khoảng 45 xu?','Đồng ý'));
assert.ok(isSpend('📦 Đặt hàng?'));
assert.ok(!isSpend('Rút 20 xu tiền mặt?','Tiền về ví.','Rút · 20 xu'));
assert.ok(!isSpend('Trả máy cho khách?','Thu phí kiểm 15 xu.'),'handing back a device earns a fee');
assert.ok(!isSpend('Bỏ lô?','Giá trị 30 xu ghi vào hao hụt.'));

// Missing money, from the right pocket.
assert.equal(shortfall(both,400,'fund'),86);
assert.equal(shortfall(both,50,'wallet'),0);
assert.equal(shortfall(both,90,'wallet'),30);
assert.equal(shortfall({wallet:-5,fund:null},10,'wallet'),10,'a negative wallet counts as empty');
assert.equal(shortfall(both,0,'fund'),0);

// The confirm block.
const wallet=balances(state,{fund:null});
assert.equal(confirmMoney(both,['Khóa phòng?','Đóng lại lúc 22:00.','Đồng ý']),'','no money talk: nothing');
let html=confirmMoney(both,['Đặt hàng?','10 nhánh: trả 10 xu ngay.','Đặt hàng']);
assert.match(html,/mn-confirm/);assert.doesNotMatch(html,/còn thiếu/);
html=confirmMoney(both,['Đặt hàng?','Hoa hồng: trả 500 xu ngay.','Đặt hàng']);
assert.match(html,/Quỹ tiệm còn thiếu <b>186 xu<\/b>/,'a work sheet pays from the fund');
html=confirmMoney(wallet,['Mua nhẫn vàng?','150 xu được trừ từ ví.','Mua · 150 xu']);
assert.match(html,/Ví còn thiếu <b>90 xu<\/b>/,'elsewhere from the wallet');
html=confirmMoney(both,['Đăng ký lớp?','Học phí 80 xu (ví còn 60 xu).','Đóng 80 xu'],{cost:80,pocket:'wallet'});
assert.match(html,/Ví còn thiếu <b>20 xu<\/b>/,'the caller says what and from where');
html=confirmMoney(both,['Rút 500 xu tiền mặt?','Tiền về ví.','Rút · 500 xu']);
assert.doesNotMatch(html,/còn thiếu/,'withdrawing is not spending');
assert.equal(confirmMoney(null,['Mua?','5 xu','Mua']),'');
// Shut the confirm only when the price is exact and comes out of the fund (the server's own check).
assert.equal(confirmShort(both,['Khóa phòng?','Đóng lại lúc 22:00.','Đồng ý']),null);
assert.deepEqual(confirmShort(both,['Đặt hàng?','Hoa hồng: trả 500 xu ngay.','Đặt hàng']),{miss:186,where:'Quỹ tiệm',sure:true});
assert.equal(confirmShort(both,['Nhập gấp?','Nhập hỏa tốc 30 · khoảng 500 xu?','Đồng ý']).sure,false,'an estimate never shuts');
assert.equal(confirmShort(wallet,['Mua nhẫn vàng?','150 xu được trừ từ ví.','Mua · 150 xu']).sure,false,'wallet spends keep their own checks');
assert.equal(confirmShort(both,['Đặt hàng?','10 nhánh: trả 10 xu ngay.','Đặt hàng']).sure,false,'enough: open');
assert.equal(confirmShort(both,['Xác nhận?','Một bước.','Đồng ý'],{cost:400,pocket:'fund'}).sure,true,'the caller says the cost');
// The bank and 🏠 Nhà của bạn: wallet + bank account (+ the couple's Quỹ chung), paid from the account first.
const bankState={journey:{wallet:40,bank:{open:true,balance:900}},careers:{}};
const bk=balances(bankState,{fund:null,account:true,joint:300});
assert.deepEqual(bk,{wallet:40,fund:null,fundName:'Quỹ tiệm',account:900,joint:300});
assert.equal(chipText(bk),'Ví 40 xu, Tài khoản 900 xu, Quỹ chung 300 xu');
assert.match(chipHTML(bk),/👛.*Ví.*🏦.*Tài khoản <b>900 xu<\/b>.*💞.*Quỹ chung <b>300 xu<\/b>/);
assert.match(chipHTML(bk,{phone:true}),/🏦.*TK <b>900 xu<\/b>/,'short label on phones');
assert.equal(balances({journey:{wallet:40,bank:{open:false}}},{fund:null,account:true}).account,null,'no account before opening one');
assert.equal(shortfall(bk,1000,['account','wallet']),60);
assert.equal(shortfall(bk,900,'account'),0);
html=confirmMoney(bk,['Mua nhà phố?','Trả trước 1.200 xu.','Ký hợp đồng mua nhà'],{cost:1200,pocket:['account','wallet']});
assert.match(html,/Tài khoản \+ Ví còn thiếu <b>260 xu<\/b>/,'a house: the account then the cash');
console.log('money chip: ok');
