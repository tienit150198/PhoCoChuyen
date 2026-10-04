import assert from 'node:assert/strict';
import {setup} from '../public/js/v4/home-walk.js';
import {defaultLook} from '../public/js/v4/look.js';
globalThis.requestAnimationFrame=fn=>fn();
const room={id:'bed',type:'bed',cols:6,frows:4,fix:[]};
let pieces=[{id:'f1',it:{id:'tu_quan_ao',w:2,spot:'floor'},q:{x:0,y:0}}];
const calls=[],commands=[];
const state={journey:{gender:'female'},wardrobe:{look:defaultLook('female'),owned:['dam_du_tiec']}};
const S={room:'bed',edit:false,dlg:{querySelector:()=>null,close:()=>calls.push('close')},env:{ui:{},api:{state,content:{journey:{wardrobe:{items:[
  {id:'dam_du_tiec',slot:'top',name:'Đầm đã mua <x>',price:180},
  {id:'dam_cong_chua',slot:'top',name:'Đầm chưa mua',price:160},
  {id:'ao_quen',slot:'top',name:'Áo quen',price:0},
  {id:'toc_bui_cao',slot:'hair',name:'Tóc không cất trong tủ',price:50}
]}}}},act:(...args)=>calls.push(args)}};
const A={PX:0,CW:40,FR:30,geom:()=>({FY:50,W:250,H:200}),anchor:()=>[0,50]};
const ui=setup({S,A,roomOf:()=>room,inRoom:()=>pieces,hostFor:()=>null,send:(...args)=>commands.push(args),render:()=>{},sfx:()=>{},calm:()=>true,roomSvg:()=>null});
const before=JSON.stringify(state);
ui.tap(room,{x:20,y:20},'f1');
assert.equal(calls.length,0,'furniture opens its clothes panel before navigating away');
let html=ui.panel({},room);
assert.ok(html.includes('Quần áo trong tủ'));
assert.ok(html.includes('Đầm đã mua &lt;x&gt;'));
assert.ok(!html.includes('Đầm chưa mua'));
assert.ok(!html.includes('Tóc không cất trong tủ'));
assert.ok(html.includes('<svg'),'character preview uses actual renderer');
await ui.click('hwClothesPick',{item:'dam_du_tiec'});
const preview=ui.panel({},room);
assert.notEqual(preview,html,'owned dress changes preview');
await ui.click('hwClothesPick',{item:'dam_cong_chua'});
assert.equal(ui.panel({},room),preview,'unowned preview selection is ignored');
assert.equal(JSON.stringify(state),before,'preview never moves inventory or equips');
assert.equal(commands.length,0,'no buy, move, or equip command on furniture/preview');
S.edit=true;assert.equal(ui.panel({},room),'');S.edit=false;
await ui.click('hwWardrobe',{});
assert.deepEqual(calls,['close',['jrWardrobe']]);
assert.equal(S.env.ui.wd.draft.top,'dam_du_tiec','the chosen owned item remains selected in the wardrobe');
pieces=[];assert.equal(ui.panel({},room),'','stored furniture panel closes if piece is no longer in room');
console.log('Home wardrobe: owned-only preview, escaped labels, no mutations/payment, existing wardrobe navigation passed');
