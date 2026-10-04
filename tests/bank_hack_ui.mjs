import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

// Render the actual card and help functions without opening a DOM dialog.
const source=readFileSync(new URL('../public/js/v4/rui.js',import.meta.url),'utf8')
  .replace(/^import .*;\r?\n/gm,'').replace(/^export /gm,'');
const {S,popHTML,ruiPage}=new Function('icon','esc',source+'\nreturn {S,popHTML,ruiPage};')(()=>'',String);
const f=JSON.parse(readFileSync(0,'utf8'));
S.env={api:{state:f.warning,content:{journey:{rui:f.catalogue}}}};
const warning=popHTML();
assert.match(warning,/Đăng nhập ngân hàng bất thường/);
assert.match(warning,/data-rui="prevent" data-opt="secure"/);
assert.match(warning,/Không tốn xu/);
S.env.api.state=f.loss;
const loss=popHTML();
assert.match(loss,/−800 xu trong tài khoản/);
assert.doesNotMatch(loss,/−800 xu tiền mặt/);
assert.match(loss,/data-rui="choose"[^>]*data-choice="secure"/);
assert.match(loss,/Bảo hiểm hiện tại không bồi thường/);
assert.match(loss,/Khóa phiên lạ & báo công an/);
assert.match(loss,/30% bắt được và hoàn đủ xu sau 2 ngày sống/);
const page=ruiPage();
assert.match(page,/mất 8% tài khoản thanh toán, tối đa 3\.000 xu/);
assert.doesNotMatch(page,/không bao giờ bị trộm/);
S.env.api.state=f.pending;
assert.match(ruiPage(),/Đã trình báo 1 vụ hack\. Kết quả gần nhất sau 2 ngày sống/);
const pack=JSON.parse(readFileSync(new URL('../public/i18n/en.json',import.meta.url),'utf8'));
assert.equal(pack.strings[f.loss.rui.card.title],'Bank account hacked');
assert.ok(pack.strings[f.warning.rui.warn.text]);
assert.ok(pack.strings[f.loss.rui.card.text]);
assert.ok(pack.strings['Khóa phiên lạ & báo công an']);
assert.ok(pack.patterns.some(([pattern,replacement])=>new RegExp('^'+pattern+'$','u').test('−800 xu trong tài khoản') && replacement.includes('from account')));
console.log('Bank hack warning, loss source, free actions, help and English pack passed.');
