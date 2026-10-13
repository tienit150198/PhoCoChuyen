import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {equipmentView} from '../public/js/v4/work-equipment.js';
const items=JSON.parse(execFileSync('python',['-c',"import json;from game.content import UPGRADES;print(json.dumps([u for u in UPGRADES if u.get('gear_group')=='warehouse_storage']))"],{encoding:'utf8'}));
const careers=[...new Set(items.flatMap(u=>u.careers))];
assert.equal(careers.length,25);
for(const career of careers){
 const rows=items.filter(u=>u.careers.includes(career));
 let html=equipmentView({money:3000,upgrades:[]},career,items);
 assert.match(html,/Sức chứa kho nghề/);assert.match(html,/152.692.000/);
 assert.match(html,/Cần bậc 1 trước/);assert.match(html,/Lắp thiết bị · 3.000 xu/);
 assert.equal((html.match(/data-action="buyUpgrade"/g)||[]).length,10);
 assert.doesNotMatch(html,/undefined|NaN|%/);
 for(const resource of rows[0].effect_resources||[]){assert.ok(html.includes(resource.name));assert.ok(html.includes(resource.capacity.toLocaleString('vi-VN')));}
 html=equipmentView({money:0,upgrades:rows.map(u=>u.id)},career,items);
 assert.match(html,/Đã lắp bậc 10/);assert.equal((html.match(/ disabled/g)||[]).length,10);
 assert.match(html,new RegExp(Number(rows[9].effect_units).toLocaleString('vi-VN').replaceAll('.','\\.')));
}
console.log('Capacity equipment: all25 careers, sequential purchase state, exact tier10 units and disabled installed buttons passed.');
