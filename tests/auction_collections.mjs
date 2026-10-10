import assert from 'node:assert/strict';
import {PAINTINGS,paintingSVG,landmarkSVG} from '../public/js/v4/auction-art.js';
import {ART} from '../public/js/v4/deco-art.js';
import {itemArt,collectibleDetails,collectionGallery,collectorBoard} from '../public/js/v4/auction-display.js';
assert.equal(Object.keys(PAINTINGS).length,14);
const shapes=[];
for(const id of Object.keys(PAINTINGS)){
  const svg=paintingSVG(id);assert.match(svg,/<svg/);assert.doesNotMatch(svg,/undefined|NaN|url\(|<image|<script/);
  shapes.push(svg.replace(/#[a-f0-9]{6}/gi,''));
  assert.ok(ART['uq_'+id].d(80,68).includes(paintingSVG(id,80,58)),'Auction and home use the same scene');
}
assert.equal(new Set(shapes).size,14,'Distinct composition, even with colors removed');
assert.equal(new Set(['dt_ho','dt_doi','dt_ben','dt_vuon','dt_cau','dt_thac'].map(landmarkSVG)).size,6);
assert.match(itemArt({kind:'plate',name:'<svg onload=alert(1)>'}),/&lt;svg/);
assert.doesNotMatch(itemArt({kind:'title',emoji:'<script>'}),/<script>/);
assert.match(collectibleDetails({tier:3,collector_points:120,data:{story:'<x>',medium:'Sơn mài'}}),/120 điểm/);
assert.match(collectibleDetails({tier:3,data:{story:'<x>'}}),/&lt;x&gt;/);
assert.match(collectionGallery({},{}),/Món độc bản/);
assert.match(collectionGallery({unknown:{k:'phone',t:'0901',p:5000}},{}),/ngoài danh mục/);
assert.match(collectorBoard(null),/Đang tải/);
assert.match(collectorBoard({error:true}),/topRetry/);
assert.match(collectorBoard({rows:[]}),/Chưa có nhà sưu tầm/);
const html=collectorBoard({rows:[{name:'<img src=x>',rank:1,score:120,items:1,legendary:1}],me:{visible:false,rank:2,score:40}});
assert.match(html,/&lt;img src=x&gt;/);assert.doesNotMatch(html,/<img/);assert.match(html,/Nếu hiện tên/);assert.match(html,/Tên bạn đang ẩn/);
console.log('14 distinct paintings, shared home rendering, 6 landmarks, collection states and escaping passed.');
