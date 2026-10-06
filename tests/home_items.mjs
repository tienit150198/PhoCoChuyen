// 🧺 Đồ đạc của bạn (v4/home-items.js): everything the player owns is listed on the house screen with its name and
// what it is: furniture room by room and in the bag (same kind ×N), clothes and accessories, every vehicle (the one
// parked out front marked), food in the fridge, wallpapers bought. Closed folds draw no rows.
import assert from 'node:assert/strict';
import {inventoryHTML,ownedCounts,decoGroups} from '../public/js/v4/home-items.js';

const item=(id,name,extra={})=>({id,name,cat:'table',spot:'floor',w:1,h:1,price:100,cozy:2,sell:50,emoji:'🪑',...extra});
const content={journey:{
  deco:{items:[item('sofa','Sofa vải',{price:180,sell:90}),item('lich','Lịch treo tường',{spot:'wall',cat:'wall',price:15,sell:7}),item('rubik','Khối rubik',{spot:'top',cat:'fun'}),item('bon_tam','Bồn tắm nằm',{cat:'bath'})],
    cats:[{id:'table',emoji:'🪑',name:'Bàn ghế'},{id:'wall',emoji:'🖼️',name:'Trang trí tường'},{id:'fun',emoji:'🧸',name:'Đồ chơi & tiện ích'},{id:'bath',emoji:'🛁',name:'Nhà tắm'}],
    kits:{bath_m:{id:'bath',emoji:'🛁',name:'Nhà tắm'}},skins:[{id:'hoa_nhi',part:'wall',name:'Giấy hoa nhí',price:35}]},
  wardrobe:{slots:[{id:'top',name:'Áo · đầm'},{id:'acc',name:'Phụ kiện'}],colors:[{id:'navy',name:'Xanh navy'}],
    items:[{id:'ao_thun',slot:'top',name:'Áo thun trắng',price:0},{id:'mu_len',slot:'acc',name:'Mũ len',price:40},{id:'pk_khong',slot:'acc',name:'Không đeo gì',price:0},{id:'toc_dai',slot:'hair',name:'Tóc dài',price:0}]},
  garage:{vehicles:[{id:'xe_dap',emoji:'🚲',name:'Xe đạp phố'},{id:'xe_may',emoji:'🛵',name:'Xe máy'}],paints:[{id:'do',name:'Đỏ'}]},
}};
const state={journey:{story:true,
  deco:{rooms:[{id:'living',emoji:'🛋️',name:'Phòng khách'}],more:[{t:'bath_m'}],owned:['hoa_nhi'],
    items:[{id:'d1',k:'sofa',r:'living',face:'back'},{id:'d2',k:'lich',r:'living'},{id:'d3',k:'lich',r:'living'},{id:'d4',k:'bon_tam',r:'bath'}],
    bag:[{id:'d5',k:'rubik'},{id:'d6',k:'gone_in_a_newer_build'}],
    fridge:{foods:[{id:'sua',emoji:'🥛',name:'Hộp sữa tươi',price:2,full:10,wake:0,n:3},{id:'ca_phe',emoji:'🧋',name:'Chai cà phê sữa',price:3,full:0,wake:15,n:0}]}},
  garage:{ride:'xe_may',cars:[{id:'xe_dap',color:'do',plate:'',day:3,paid:120,sell:60},{id:'xe_may',color:'do',plate:'59-HK',day:9,paid:900,sell:450,upkeep:5}]}},
  wardrobe:{owned:['mu_len'],look:{top:'ao_thun',acc:'mu_len',hair:'toc_dai'}},colors:{deco:{d2:'navy'},wear:{}},wardrobe_colors:{wear:{mu_len:'navy'}}};

const n=ownedCounts(state,content);
assert.deepEqual({deco:n.deco,wear:n.wear,cars:n.cars,food:n.food,skins:n.skins},{deco:6,wear:2,cars:2,food:3,skins:1});
assert.equal(n.total,14);

const groups=decoGroups(state,content);
assert.deepEqual(groups.map(g=>g.title),['🛋️ Phòng khách','🛁 Nhà tắm','🎒 Trong túi đồ (chưa bày)'],'rooms in order, the new rooms by their kit, then the bag');
assert.equal(groups[0].rows.length,3,'two calendars of different colours are two rows');
const lich=groups[0].rows.filter(r=>r.it.id==='lich');assert.deepEqual(lich.map(r=>r.n).sort(),[1,1]);
assert.equal(groups[2].rows.length,1,'a kind this build does not know is left out, nothing breaks');

const closed=inventoryHTML(state,content,{});
assert.match(closed,/Đồ đạc của bạn · 14 món/);
assert.doesNotMatch(closed,/Sofa vải/,'closed folds draw no rows');
for(const fold of ['deco','wear','cars','food','skins'])assert.match(closed,new RegExp(`data-inv="${fold}"`));

const thumb=(it,size,tint)=>`<svg data-thumb="${it.id}" data-tint="${tint||''}"></svg>`;
const btn=(label,op)=>`<button data-hs="${op}">${label}</button>`;
const all=inventoryHTML(state,content,{open:new Set(['deco','wear','cars','food','skins']),thumb,btn});
for(const name of ['Sofa vải','Lịch treo tường','Bồn tắm nằm','Khối rubik','Áo thun trắng','Mũ len','Xe đạp phố','Xe máy','Hộp sữa tươi','Giấy hoa nhí'])
  assert.ok(all.includes(name),`${name} is listed`);
assert.doesNotMatch(all,/Không đeo gì|Tóc dài|Chai cà phê sữa/,'no "nothing worn", no hair, no empty food');
assert.match(all,/đang quay mặt sau/,'a piece turned round says so');
assert.match(all,/màu Xanh navy/,'a recoloured piece names its colour');
assert.match(all,/data-thumb="lich" data-tint="navy"/,'and is drawn in it');
assert.match(all,/bán lại 90 xu/,'what it is worth');
assert.match(all,/🅿️ Đậu trước nhà/,'the vehicle parked out front is marked');
assert.match(all,/biển “59-HK”/);
assert.match(all,/Đang mặc/);
assert.match(all,/×3/,'three of the same food');
assert.match(all,/data-hs="inside"/);assert.match(all,/data-hs="garage"/);assert.match(all,/data-hs="wardrobe"/);
assert.doesNotMatch(all,/undefined|NaN|\[object/);

// a player with nothing yet: every fold says so, nothing breaks
const empty=inventoryHTML({journey:{story:true}},content,{open:new Set(['deco','cars'])});
assert.match(empty,/Đồ đạc của bạn · 0 món/);assert.match(empty,/Chưa có món nào/);assert.match(empty,/Chưa có xe/);
console.log('Home items: furniture by room and bag, clothes, vehicles, fridge and wallpapers listed with names and info');
