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
