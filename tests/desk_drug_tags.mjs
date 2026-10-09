// F#278: the pharmacy desk tags nhóm K and hàng lạnh medicines on the papers and lists them in the rulebook.
import assert from 'node:assert/strict';
globalThis.location??={search:''};
const {drugTag,drugLegend}=await import('../public/js/desk.js');
const t={drugs:[{name:'Kháng Lam 250',group:'K'},{name:'Viên Hoạt Lan',group:'K'},{name:'Lọ Tuyết Lạnh',group:'L'}]};
assert.match(drugTag(t,'Kháng Lam 250'),/dk-drug k[^>]*>K</,'nhóm K is tagged');
assert.match(drugTag(t,'Lọ Tuyết Lạnh · 1 hộp'),/dk-drug cold[^>]*>❄️ Lạnh</,'cold chain is tagged');
assert.match(drugTag(t,'Phiếu PK-512','09:10 · Kháng Lam 250'),/>K</,'a name in the line label is tagged too');
assert.equal(drugTag(t,'Siro Mây Tâm'),'','everyday items carry no tag');
assert.equal(drugTag({},'Kháng Lam 250'),'','an older server without the list: no tags');
assert.equal(drugTag(t,null),'');
const legend=drugLegend(t);
for(const text of ['Nhóm K','<span>Kháng Lam 250</span>, <span>Viên Hoạt Lan</span>','Hàng lạnh','Lọ Tuyết Lạnh','hàng thông thường'])assert.ok(legend.includes(text),text);
assert.equal(drugLegend({}),'','no legend without the list');
console.log('desk drug tags: K / ❄️ Lạnh tags and none for everyday items passed');
