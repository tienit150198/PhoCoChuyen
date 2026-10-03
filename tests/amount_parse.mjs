// public/js/v4/amount-parse.js: what a player types in a money box → a whole number (tests/test_amount_parse.py).
import assert from 'node:assert/strict';
import {parseAmount,amountOf,amountNote,formatAmount,amountAttrs,amountNoteHTML} from '../public/js/v4/amount-parse.js';

const ok=(raw,want,unit='đ')=>{const r=parseAmount(raw,unit);assert.deepEqual(r,{ok:true,value:want},`${JSON.stringify(raw)} [${unit}] → ${JSON.stringify(r)}`);};
const no=(raw,reason,unit='đ')=>{const r=parseAmount(raw,unit);assert.equal(r.ok,false,`${JSON.stringify(raw)} [${unit}] should not read, got ${JSON.stringify(r)}`);if(reason)assert.equal(r.reason,reason,JSON.stringify(raw));};

// Plain and negative numbers
ok('0',0);ok('500000',500000);ok('-500.000',-500000);ok('−500000',-500000);ok('–200',-200);ok('+300',300);ok('- 7',-7);
ok('(500.000)',-500000);ok('(500000)',-500000);ok(' ( 1.200 ) ',-1200);ok('(10 triệu)',-10000000);
ok('-(500.000)',-500000);ok('((500))',500);   // only one number in one bracket is the books' negative
// Thousand separators: dots, commas, spaces
ok('1.000.000',1000000);ok('1,000,000',1000000);ok('1 000 000',1000000);ok('1 000 000',1000000);ok('12.400',12400);ok('12,400',12400);
ok('1.234.567',1234567);ok('1,234.5 triệu',1234500000);ok('1.234,5 triệu',1234500000);
no('1.2345','fraction');no('1,5','fraction');no('0,5','fraction');no('0.500','fraction');no('1.00.000');no('1..000');no('1,000.000.000');no('10 2');
// Units
ok('10 triệu',10000000);ok('10triệu',10000000);ok('10 trieu',10000000);ok('10tr',10000000);ok('10 TR',10000000);ok('10 triệu đồng',10000000);
ok('1,5tr',1500000);ok('1.5tr',1500000);ok('1,5 triệu',1500000);ok('2.5 tỷ',2500000000);ok('2,5 tỷ',2500000000);ok('2 tỉ',2000000000);ok('3 ty',3000000000);
ok('1tr5',1500000);ok('2tr25',2250000);ok('1k5',1500);
ok('1.000.000đ',1000000);ok('1.000.000 đ',1000000);ok('1.000.000 đồng',1000000);ok('1.000.000 VND',1000000);ok('1.000.000vnđ',1000000);
ok('12k',12000);ok('12 K',12000);ok('12 nghìn',12000);ok('12 ngàn',12000);ok('500 nghìn đồng',500000);
ok('1.000.000 × 10%',100000);ok('1.5 million',1500000);ok('-500,000',-500000);ok('2 billion',2000000000);ok('3 thousand',3000);ok('12400 × 8%',992);
// Arithmetic
ok('6+4',10);ok('6 + 4',10);ok('3×4',12);ok('3*4',12);ok('3x4',12);ok('3 x 4',12);ok('3 X 4',12);ok('10/2',5);ok('10 : 2',5);ok('10÷2',5);
ok('(2+3)*1.000',5000);ok('2*(3+4)-1',13);ok('-2*-3',6);ok('10-15',-5);ok('6 − 4',2);ok('1tr - 250k',750000);ok('6+4=',10);
// One unit at the very end, every other number bare: it scales the whole sum ("6+4=10 triệu", coordinator 03/10)
ok('6 + 4 triệu',10000000);ok('6+4 triệu',10000000);ok('6+4tr',10000000);ok('(2+3) triệu',5000000);ok('(2+3)triệu',5000000);
ok('(2+3) tr đồng',5000000);ok('2 × 3 triệu',6000000);ok('10 - 2k',8000);ok('15 + 5 nghìn',20000);ok('1.500 + 500 nghìn',501500);ok('999 + 1k',1000000);ok('(1.000 + 5) k',1005000);ok('-6 - 4 triệu',-10000000);ok('6+4 đ',10);
ok('(10) triệu',-10000000);ok('2×(3+4) tỷ',14000000000);ok('1,5 + 1 triệu',2500000);
// Otherwise every number keeps its own unit
ok('100k + 5 triệu',5100000);ok('2tr + 5',2000005);ok('2tr + 5 triệu',7000000);ok('6 + 1tr5',1500006);no('100 + 10%','fraction');ok('100 + 1000 × 10%',200);ok('1.000 × 10% + 5',105);
ok('10 triệu',10000000);ok('(10 triệu)',-10000000);
no('(2+3) triệu + 1','syntax');no('(2tr+3) triệu','syntax');no('(2+3) triệu đồng k','syntax');
ok('6 + 4 triệu',10,'triệu');ok('(2+3) triệu',5,'triệu');ok('6+4 ngày',10,'ngày');ok('6 + 4 xu',10,'xu');ok('2k + 5 xu',2005,'xu');
ok('1.500.000 + 2tr',3500000);
no('10/3','fraction');no('1/0','syntax');no('5/2','fraction');
// Rejects
no('abc','syntax');no('1++','syntax');no('','empty');no('   ','empty');no(null,'empty');no(undefined,'empty');no('2(3)','syntax');no('(5','syntax');no('5)','syntax');
no('1e5','syntax');no('5 xu','syntax');no('5 kg','syntax');no('*5','syntax');no('5*','syntax');no('-','syntax');no('()','syntax');no('1 2','syntax');
no('9'.repeat(17),'big');no('2000000 tỷ','big');no('1'.repeat(121),'syntax');
// The box's own unit: a bare number keeps today's meaning
ok('10',10,'triệu');ok('10 triệu',10,'triệu');ok('10.000.000đ',10,'triệu');ok('10tr',10,'triệu');ok('6 + 4 triệu',10,'triệu');ok('6+4',10,'triệu');
ok('1,5 tỷ',1500,'triệu');no('1,5 triệu','fraction','triệu');no('500k','fraction','triệu');
ok('90',90,'ngày');ok('90 ngày',90,'ngày');ok('90 ngay',90,'ngày');ok('-3 kg',-3,'kg');ok('-3',-3,'kg');
ok('250 xu',250,'xu');ok('250xu',250,'xu');ok('-25 xu',-25,'xu');ok('1.250',1250,'xu');ok('3x4',12,'xu');ok('2k',2000,'xu');
ok('250 xu/tháng',250,'xu/tháng');ok('250',250,'xu/tháng');
ok('8%',8,'%');ok('8',8,'%');
ok('1.000.000',1000000,'');ok('1.000.000',1000000,undefined);ok('1.000.000',1000000,'VND');ok('1.000.000 vnd',1000000,'VND');
// Values saved as numbers (an older draft) still read
ok(1000000,1000000);ok(-250,-250);no(1.5,'fraction');no(NaN,'syntax');
// amountOf: the number or null, never NaN
assert.equal(amountOf('6+4'),10);assert.equal(amountOf(''),null);assert.equal(amountOf('abc'),null);assert.equal(amountOf('1,5'),null);
// The note under the box
assert.equal(formatAmount(10000000),'10.000.000');assert.equal(formatAmount(-500000),'-500.000');assert.equal(formatAmount(1.5),'1,5');assert.equal(formatAmount(0),'0');
assert.deepEqual(amountNote('6+4','đ'),{text:'= 10',bad:false});
assert.deepEqual(amountNote('10 triệu','đ'),{text:'= 10.000.000',bad:false});
assert.deepEqual(amountNote('1000000','đ'),{text:'',bad:false});
assert.deepEqual(amountNote('1.000.000','đ'),{text:'',bad:false});
assert.deepEqual(amountNote('-500000','đ'),{text:'',bad:false});
assert.deepEqual(amountNote('(500.000)','đ'),{text:'= -500.000',bad:false});
assert.deepEqual(amountNote('','đ'),{text:'',bad:false});
assert.deepEqual(amountNote('abc','đ'),{text:'Chưa hiểu số này',bad:true});
assert.deepEqual(amountNote('10/4','đ'),{text:'= 2,5 · cần số nguyên',bad:true});
assert.deepEqual(amountNote('9'.repeat(17),'đ'),{text:'Số quá lớn',bad:true});
// Markup: a text box with the full keyboard, escaped
assert.ok(amountAttrs('đ').includes('type="text"')&&!amountAttrs('đ').includes('inputmode')&&!amountAttrs('đ').includes('number'));
assert.ok(amountAttrs('"><x').includes('&#34;&#62;&#60;x'));
assert.equal(amountNoteHTML('6+4','đ'),'<small class="amt-note" data-amt-note>= 10</small>');
assert.equal(amountNoteHTML('x','đ'),'<small class="amt-note bad" data-amt-note>Chưa hiểu số này</small>');
console.log('amount_parse ok');
