import assert from 'node:assert/strict';
import {equipmentView} from '../public/js/v4/work-equipment.js';
import {inventoryLimits,cratePage} from '../public/js/v4/inventory-limits.js';
import {inventoryView,v4Action} from '../public/js/v4/views.js';
import {execFileSync} from 'node:child_process';

const inv={capacity:550,line_cap:80,order_upgrade:{tier:0,max_tier:10,next_limit:120,next_price:3000}};
let html=inventoryLimits(inv);
assert.match(html,/550/);assert.match(html,/80/);assert.match(html,/120/);assert.match(html,/3.000/);
assert.match(html,/v4OrderUpgrade/);
assert.doesNotMatch(inventoryLimits({...inv,order_upgrade:{tier:10,max_tier:10}}),/v4OrderUpgrade/);
// #375/#378: the storage ladder sits beside the order line; a line that already fills the shelf is not sold here.
const st={tier:0,max_tier:10,capacity:80,next_capacity:120,next_price:3000};
html=inventoryLimits({...inv,storage_upgrade:{...st,capacity:550,next_capacity:825}});
assert.match(html,/v4StorageUpgrade/);assert.match(html,/Nâng sức chứa lên 825/);assert.match(html,/Nâng nhập mỗi dòng lên 120/);
html=inventoryLimits({capacity:80,line_cap:120,order_upgrade:{tier:1,max_tier:10,next_limit:200,next_price:9000},storage_upgrade:st});
assert.match(html,/Nâng sức chứa lên 120 · 3.000 xu/);assert.doesNotMatch(html,/v4OrderUpgrade/);assert.match(html,/nâng sức chứa trước/);
assert.match(inventoryLimits({capacity:4000,line_cap:4000,order_upgrade:{tier:10,max_tier:10},storage_upgrade:{...st,tier:10,next_capacity:null}}),/Đã mở tối đa/);
const ladder=(group,n,prev,units,label)=>({id:`warehouse_${group}_pet_shop_${n}`,kind:'equipment',careers:['pet_shop'],gear_group:`warehouse_${group}`,gear_tier:n,effect_previous:prev,effect_units:units,effect_label:label,name:group,description:'',price:3000});
const both=[ladder('storage',1,80,120,'phần / mã hàng'),ladder('storage',2,120,180,'phần / mã hàng'),ladder('order',1,80,120,'món / dòng đặt'),ladder('order',2,120,200,'món / dòng đặt')];
assert.match(equipmentView({money:0,upgrades:['warehouse_order_pet_shop_1']},'pet_shop',both),/Kho đang chứa 80 phần\/mã/);
assert.doesNotMatch(equipmentView({money:0,upgrades:['warehouse_storage_pet_shop_1','warehouse_storage_pet_shop_2']},'pet_shop',both),/Kho đang chứa/);
html=equipmentView({money:3000,upgrades:[]},'clothing',[{id:'warehouse_order_clothing_1',kind:'equipment',careers:['clothing'],gear_group:'warehouse_order',gear_tier:1,effect_previous:80,effect_units:120,effect_label:'món / dòng đặt',name:'Hạn mức',description:'Nâng riêng',price:3000}]);
assert.match(html,/data-gear-group="warehouse_order"/);assert.match(html,/80 → 120/);
// Page navigation never counts for the player or changes the actual/short delivery.
for(const [qty,actual] of [[528,523],[8000,6200],[8000,8000],[25,23]]){
 const o={id:'large-order',qty,count_hint:actual},indices=[];let slots=0;
 for(let page=0;page<Math.ceil(qty/100);page++){
  const result=cratePage(o,page);assert.ok(result.trays.length<=10);
  for(const tray of result.trays)for(const k of tray.cells){slots++;if(k!==null)indices.push(k);}
 }
 assert.equal(slots,qty);assert.deepEqual(indices,Array.from({length:actual},(_,i)=>i));
 assert.deepEqual(cratePage(o,0),cratePage(o,0));
 assert.equal(cratePage(o,999).page,Math.ceil(qty/100)-1);
}
const fixture=JSON.parse(execFileSync('python',['-c',`
import json
from tests.test_order_progression import fresh
from game.content import public_content
from game.engine import public_state
j=fresh(order=4)
print(json.dumps(dict(state=public_state(j.state),content=public_content())))
`],{encoding:'utf8',maxBuffer:20*1024*1024}));
const c=fixture.state.careers.clothing,env={api:fixture,ui:{orderItem:'tee'}};
html=inventoryView(env);assert.match(html,/max="528"/);
c.inventory.line_cap=80;html=inventoryView(env);assert.match(html,/max="80"/);
c.inventory.line_cap=550;
c.inventory.carts=[{supplier:'partner',lines:[{item:'tee',qty:300}],total:100,n:1,quote:{}}];
html=inventoryView(env);assert.match(html,/max="228"/);
let opened=null,scrolled=false;
globalThis.requestAnimationFrame=f=>f();globalThis.document={querySelector:()=>({scrollIntoView:()=>{scrolled=true;}})};
await v4Action('v4OrderUpgrade',{},null,{...env,openSheet:s=>{opened=s;}});
assert.equal(opened,'decor');assert.equal(scrolled,true);
opened=null;let target='';globalThis.document={querySelector:q=>{target=q;return {scrollIntoView:()=>{}};}};
await v4Action('v4StorageUpgrade',{},null,{...env,openSheet:s=>{opened=s;}});
assert.equal(opened,'decor');assert.equal(target,'[data-gear-group="warehouse_storage"]');
delete globalThis.document;delete globalThis.requestAnimationFrame;
console.log('Storage beside the order line, order upgrade labels, equipment, dynamic quantity/drafts, navigation and bounded short-delivery trays passed.');
