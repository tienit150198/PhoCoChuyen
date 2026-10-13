import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
const data=JSON.parse(execFileSync('python',['-c',"import runpy,json; p=runpy.run_path('game/promotion_content.py'); print(json.dumps({k:p[k] for k in ('EMP_TITLES','OWN_TITLES','BADGE')}))"],{encoding:'utf8'}));
for(const [id,rows] of Object.entries(data.EMP_TITLES)){
  assert.equal(rows.length,7,id+' employee ladder');assert.equal(new Set(rows).size,7,id+' distinct titles');
}
for(const [id,rows] of Object.entries(data.OWN_TITLES)){
  assert.equal(rows.length,7,id+' owner ladder');assert.equal(new Set(rows).size,7,id+' distinct titles');
}
assert.deepEqual(data.EMP_TITLES.teacher.slice(0,5),['GV giỏi cấp trường','Tổ phó chuyên môn','Tổ trưởng chuyên môn','Phó hiệu trưởng','Hiệu trưởng']);
assert.deepEqual(data.EMP_TITLES.pilot,['Cơ phó cao cấp','Cơ trưởng','Cơ trưởng Huấn luyện','Trưởng đội bay','Phó Giám đốc Khối khai thác bay','Giám đốc Khối khai thác bay','Phó Tổng Giám đốc']);
assert.deepEqual(data.OWN_TITLES.shop.slice(0,4),['Chủ quầy vững tay','Chủ tiệm có tiếng','{chu} được nể','{ong} chuỗi tiệm']);
assert.equal(data.BADGE.teacher.length,8);
console.log('Promotion titles: seven distinct steps, existing pilot/teacher/shop ranks preserved');
