// Toast text → rows (public/js/toast-lines.js). Run: node tests/toast_lines.mjs
import assert from 'node:assert/strict';
import {toastParts} from '../public/js/toast-lines.js';

const long='💵 Thu 100 xu, thối 100 xu. Cuối ca túi COD sẽ thiếu đúng chừng đó. ✅ Giao thành công lúc 17:58 · phí ship +22 xu. 💛 Bé Vy quý bạn hơn (thân thiết 2/10). 🗺️ Đã thuộc hẻm quanh Chung cư Mây Xanh. Túi COD đang giữ 82 xu. 👮 Chốt kiểm tra giấy tờ xe!';
const rows=toastParts(long);
assert.deepEqual(rows.map(r=>r.icon),['💵','✅','💛','🗺️','👮']);
assert.equal(rows[3].text,'Đã thuộc hẻm quanh Chung cư Mây Xanh. Túi COD đang giữ 82 xu.','a plain sentence stays with its note');
assert.deepEqual(toastParts('Đã chọn 🌸 hoa hồng.'),[],'an emoji inside a sentence does not split');
assert.deepEqual(toastParts('Xong. 👍'),[],'a trailing emoji alone is not a note');
assert.deepEqual(toastParts('Một câu thường.'),[]);
assert.deepEqual(toastParts('Mở hàng. ✅ Đã nhận cọc.').map(r=>r.icon),['','✅'],'a first note without an emoji keeps an empty icon');
console.log('toast_lines.mjs: ok');
// toastHead: a toast shows a few words; a tap shows the rest.
import {toastHead} from '../public/js/toast-lines.js';
const words=s=>s.split(' ').filter(w=>/\p{L}|\d/u.test(w)).length;
assert.equal(toastHead(long).head,'💵 Thu 100 xu, thối 100 xu','the first note, its first sentence');
assert.equal(toastHead(long).more,true);
assert.deepEqual(toastHead('Đã lấy tô ăn tại quán.'),{head:'Đã lấy tô ăn tại quán.',more:false},'a short note stays whole');
assert.equal(toastHead('Khách đặt lên quầy: 4 hộp Sữa hộp Mây Trắng, 2 ổ Bánh mì ổ. Khách chuyển khoản. “Lốc 4 hộp sữa có khuyến mãi đúng không em?”').head,'Khách đặt lên quầy','a long note stops at an early break');
assert.equal(toastHead('Linh để lại 5 xu tip: “Người mới hả? Làm khéo ghê!”').head,'Linh để lại 5 xu tip','quoted words go when a note is around them');
assert.equal(toastHead('“Cảm ơn em nha!”').head,'“Cảm ơn em nha!”','a quote alone stays');
for(const m of [long,'Bó hoa cầm tay dịp tốt nghiệp, ngân sách 120 xu, tông vàng – trắng, 7–15 cành, đúng 3 cành hướng dương, kèm thiệp viết tay. Em có 120 xu thôi.','Lấy tại Bưu cục Mây Chiều → giao Chung cư Mây Xanh (thiếu số phòng) · Váy dự tiệc tốt nghiệp (khai 0,8 kg)'])
  assert.ok(words(toastHead(m).head)<=8,`at most 8 words: ${toastHead(m).head}`);
assert.equal(toastHead('Quỹ tiệm không đủ 120 xu để nhập mẻ này, còn thiếu 35 xu. Rút từ ví?',{error:true}).head,'Quỹ tiệm không đủ 120 xu để nhập mẻ này, còn thiếu 35 xu','an error keeps its whole first sentence');
console.log('toast_lines.mjs (head): ok');
