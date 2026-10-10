import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
import {termsSource} from '../public/js/v4/terms.js';
import * as legacy from '../public/js/scenes/index.js';

assert.ok(existsSync(new URL('../public/js/scenes/vocabulary.js',import.meta.url)),
  'career words must be importable without the legacy scene loader');
const vocabulary=await import('../public/js/scenes/vocabulary.js');
assert.equal(Object.keys(vocabulary.KIND_OF).length,50,'all current careers keep their scene family');
for(const symbol of ['KIND_OF','kindOf','wordsFor'])assert.equal(legacy[symbol],vocabulary[symbol],`${symbol} keeps the legacy API`);
for(const career of Object.keys(vocabulary.KIND_OF)){
  const words=vocabulary.wordsFor(career);
  assert.equal(vocabulary.kindOf(career),vocabulary.KIND_OF[career]);
  for(const key of ['till','books','rail_in','confirm_title','end_title','end_text'])assert.equal(typeof words[key],'string',`${career}.${key}`);
}
assert.equal(vocabulary.kindOf('unknown'),'shop');
assert.equal(vocabulary.wordsFor('zpop').shelf,'Kệ album');
assert.equal(vocabulary.wordsFor('police').books,'Sổ trực ban');
assert.equal(vocabulary.wordsFor('teacher').till,'Quỹ lớp');
const cabin=vocabulary.wordsFor('flight_attendant');
assert.equal(cabin.counter,'Cửa lên máy bay','cabin boarding uses an aircraft door');
assert.equal(cabin.warehouse,'Khoang bếp','cabin supplies belong to the aircraft galley');
assert.equal(cabin.store,'KHOANG BẾP');
assert.equal(cabin.rail_in,'Trên máy bay','the cabin menu describes the current workplace');
assert.equal(cabin.property,'Khoang khách Cánh Cò');
assert.equal(cabin.security,'An toàn khoang khách');
const transportFields=['shelf','counter','evidence','warehouse','property','security','rail_in','open_hint'];
for(const career of ['pilot','flight_attendant']){
  const words=vocabulary.wordsFor(career),labels=transportFields.map(key=>words[key]).join(' | ');
  assert.doesNotMatch(labels,/bếp tàu|cửa (?:ra )?tàu|đường ngang|chòi gác|giàn dầu/i,`${career}: no sea or railway station labels`);
}
const pilot=vocabulary.wordsFor('pilot'),railway=vocabulary.wordsFor('railway');
assert.equal(pilot.counter,'Quầy điều phái');
assert.equal(pilot.evidence,'Bản tin & phiếu dầu');
assert.equal(railway.counter,'Chòi gác');
assert.equal(railway.evidence,'Bảng giờ tàu');
assert.doesNotMatch(transportFields.map(key=>railway[key]).join(' | '),/máy bay|sân bay|khoang bếp|điều phái|giàn dầu/i,'railway labels remain specific to the crossing');
termsSource(()=>[{id:'unknown',terms:{commerce:false,confirm:'Xác nhận mới',end_title:'Kết ca mới',end_text:'Nội dung mới',rail_in:'Nơi mới',books:'Sổ mới'}}]);
assert.equal(vocabulary.wordsFor('unknown').confirm_title,'Xác nhận mới','vocabulary reads live catalogue terms');
termsSource(()=>null);
assert.equal(vocabulary.wordsFor('unknown').confirm_title,'Xác nhận việc của tiệm','fallback is restored when catalogue disappears');
assert.equal(typeof legacy.sceneFor,'function');assert.equal(typeof legacy.loadAllScenes,'function');
console.log('career-vocabulary: all 50 careers, terms, fallback and legacy exports passed');
