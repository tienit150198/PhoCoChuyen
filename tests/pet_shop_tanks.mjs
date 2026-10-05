import assert from 'node:assert/strict';
globalThis.document={querySelector:()=>({sheet:{}}),addEventListener(){}};
const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');
const x={esc,ui:{},stock:()=>5,room:{data:{animals:{betta:6,goldfish:10},coats:{}}},cc:{
  tanks:{tank_10:10,tank_30:30},fish:['betta','goldfish'],animals:{betta:{name:'Cá betta',litres:5},goldfish:{name:'Cá vàng',litres:10}},
  items:{filter:{name:'Lọc'},heater:{name:'Sưởi'},conditioner:{name:'Khử clo'}},prices:{},tips:{},
}};
const t={id:'test',cart:{tank_10:2,betta:2,conditioner:2},work:{advice:[]},tanks:[
  {cart:{tank_10:1,betta:1,conditioner:1},load:{litres:5,size:10},problems:[]},
  {cart:{tank_10:1,betta:1,conditioner:1},load:{litres:5,size:10},problems:[]},
]};
// The production panel must send the selected aquarium with each edit.
const {tankPanel}=await import('../public/js/careers/pet_shop.js');
let html=tankPanel(t,x,new Set(['tanks','fish','gear','tips']));
const commands=[...html.matchAll(/data-command="([^"]+)" data-payload="([^"]+)"/g)].map(m=>({command:m[1],p:JSON.parse(m[2].replaceAll('&quot;','"').replaceAll('&amp;','&'))}));
for(const tank of [0,1]){
  assert.ok(commands.some(({command,p})=>command==='ps_cart'&&p.tank===tank&&p.key==='betta'&&p.qty===2));
  assert.ok(commands.some(({command,p})=>command==='ps_tank'&&p.tank===tank&&p.size==='tank_30'));
}
assert.ok(commands.some(({command,p})=>command==='ps_tank'&&p.tank===2),'Add a separate third aquarium');
assert.match(html,/Bể 1/);assert.match(html,/Bể 2/);assert.match(html,/Thêm bể riêng/);
t.tanks[1].problems=[{code:'crowded',note:'bể quá tải: 20/10 lít'}];
html=tankPanel(t,x,new Set(['tanks','fish','gear','tips']));
assert.match(html,/bể quá tải: 20\/10 lít/,'Show actionable warning before payment');
t.billed=true;
html=tankPanel(t,x,new Set(['tanks','fish','gear','tips']));
for(const button of html.matchAll(/<button\b[^>]*data-command="(?:ps_cart|ps_tank|ps_tank_remove)"[^>]*>/g))assert.match(button[0],/ disabled/);
console.log('Pet shop UI: per-tank edits, add aquarium, warnings and checkout locks passed.');
