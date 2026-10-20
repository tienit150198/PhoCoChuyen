// 🔨 20/10 auction items on the client: every one-of-a-kind piece of furniture has its drawing (its base piece with the
// sparkles), and the lot card draws the three new kinds, says what an item does, and escapes what it shows.
//   node tests/auction_items.mjs
import assert from 'node:assert/strict';
import {ART,UQ_DECO,thumb} from '../public/js/v4/deco-art.js';
import {itemArt,collectibleDetails,collectionGallery} from '../public/js/v4/auction-display.js';

assert.equal(Object.keys(UQ_DECO).length,9);
for(const [id,[base]] of Object.entries(UQ_DECO)){
  const a=ART['uq_'+id],b=ART[base];
  assert.ok(a&&b,`${id}: drawn from ${base}`);
  assert.equal(Boolean(a.wall),Boolean(b.wall));
  const svg=a.d(b.wall?80:120,b.wall?68:(b.h||40));
  assert.doesNotMatch(svg,/undefined|NaN/,id);
  assert.ok(svg.length>b.d(b.wall?80:120,b.wall?68:(b.h||40)).length,`${id}: sparkles on top of its base`);
}
const deco=itemArt({kind:'decor',item:'dc_sap_kham',tier:3,emoji:'🪵',data:{glow:'#f3e3c0',w:3,h:1,spot:'floor'}});
assert.match(deco,/au-decor/);assert.match(deco,/<svg class="dc-thumb"/);assert.doesNotMatch(deco,/undefined|NaN/);
assert.ok(thumb({id:'uq_dc_den_chum',w:2,h:1,spot:'wall'}).includes('<svg'));
const pet=itemArt({kind:'petgear',tier:3,emoji:'💎',data:{rank:6}});
assert.match(pet,/<b>SSS<\/b>/);assert.match(pet,/#ff4fa3/);
assert.match(itemArt({kind:'petgear',tier:1,emoji:'x',data:{rank:'<x>'}}),/<b>D<\/b>/);   // a bad rank: D, never raw
assert.match(itemArt({kind:'tool',tier:2,emoji:'<script>'}),/&lt;script&gt;/);
assert.match(itemArt({kind:'vehicle',tier:1,emoji:'🚗',data:{paint:'hong_ngoc',serial:'02/02'}}),/#a8203a/);
const det=collectibleDetails({tier:2,collector_points:40,data:{use:'Tự dùng ở <b>quán</b>: +3%',story:'s'}});
assert.match(det,/au-use/);assert.match(det,/&lt;b&gt;quán/);
const gal=collectionGallery({tl_quay_go:{k:'tool',t:'Quầy gỗ lim',p:50000}},{items:[{id:'tl_quay_go',kind:'tool',tier:2,emoji:'🧮',collector_points:40,use:'Tự dùng ở Tạp Hoá Cô Ba: lợi nhuận mỗi ca +3%'}]});
assert.match(gal,/Tạp Hoá Cô Ba/);assert.match(gal,/au-tool/);
console.log('9 furniture drawings, the decor / pet / tool cards, the use line and escaping passed.');
