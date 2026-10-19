// Players #427 #431 (19/10): a merged crate goes onto the shelf line by line ("Nhập món này", "Nhập luôn phần đã
// đếm"), 👥 the staff on shift count every crate at the door, and leaving the stock room with crates counted right
// puts them on the shelf (receiveCounted). Server: game/inventory.py, tests/test_receive_partial.py.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {inventoryView,v4Action,receiveCounted} from '../public/js/v4/views.js';

const fixture=JSON.parse(execFileSync('python',['-c',`
import json
from tests.test_receive_partial import fresh, ready_group, hire
from game.content import public_content
from game.engine import public_state
j=fresh()
hire(j)
gid=ready_group(j)
one=j.act('inv_order', item='mushroom', qty=3, supplier='partner', confirm=True)['eta']['order']
from tests.test_inventory_flow import wait_until_ready
wait_until_ready(j, one)
st=public_state(j.state)
st['current']='restaurant'
print(json.dumps(dict(state=st,content=public_content(),gid=gid,one=one)))
`],{encoding:'utf8',maxBuffer:30*1024*1024,env:{...process.env,PYTHONUTF8:'1'}}));
const api={state:fixture.state,content:fixture.content},gid=fixture.gid,inv=api.state.careers.restaurant.inventory;
const lines=inv.orders.filter(o=>o.group===gid&&o.status==='in_transit'),single=inv.orders.find(o=>o.id===fixture.one);
assert.equal(lines.length,3);assert.ok(lines.every(o=>o.ready_now&&o.count_hint!=null));assert.ok(single.ready_now);
assert.ok(inv.helper,'a staff member on shift is named');

const ui={invOpen:gid,invTab:'orders'};let calls=[];
const cmd=async(op,payload)=>{calls.push([op,payload]);return {message:'ok'};};
const env={api,ui,cmd,toast:()=>{},renderSheet:()=>{}};
// The stock sheet renders without a DOM (as tests/order_limits.mjs); the actions read the count boxes through one.
const dom=()=>{globalThis.document={getElementById:()=>null,querySelectorAll:()=>[],querySelector:()=>({}),addEventListener(){}};globalThis.window??={addEventListener(){}};globalThis.CSS={escape:s=>s};};
const undom=()=>{delete globalThis.document;delete globalThis.CSS;};

let html=inventoryView(env);
assert.equal((html.match(/Nhập món này/g)||[]).length,3,'one button per line of the merged crate');
assert.match(html,/Nhận cả thùng lên kệ/);
assert.match(html,new RegExp(`👥 ${inv.helper} đếm giúp`),'the staff button');
assert.match(html,/data-command="inv_receive" data-payload="\{&quot;staff&quot;:true\}"/);

// One line counted: the big button says it takes the part counted so far.
ui.invCount={[lines[0].id]:String(lines[0].count_hint)};
html=inventoryView(env);
assert.match(html,/Nhập luôn phần đã đếm · 1\/3 món/);
dom();await v4Action('v4ReceiveGroup',{group:gid},null,env);undom();
assert.deepEqual(calls,[['inv_receive',{group:gid,counts:{[lines[0].id]:lines[0].count_hint}}]]);
assert.equal(ui.invOpen,gid,'the crate stays open for the lines left');

// "Nhập món này" on one line sends that line only.
calls=[];ui.invCount={[lines[1].id]:String(lines[1].count_hint),[lines[2].id]:String(lines[2].count_hint)};
dom();await v4Action('v4ReceiveGroup',{group:gid,line:lines[2].id},null,env);
assert.deepEqual(calls,[['inv_receive',{group:gid,counts:{[lines[2].id]:lines[2].count_hint}}]]);
assert.equal(ui.invCount[lines[1].id],String(lines[1].count_hint),'the other line keeps its count');
// A line not counted yet: asked to count, nothing sent.
calls=[];ui.invCount={};
await v4Action('v4ReceiveGroup',{group:gid,line:lines[0].id},null,env);
assert.deepEqual(calls,[]);

// Leaving the stock room: crates counted right go onto the shelf; a wrong count stays for the player.
calls=[];
ui.invCount={[lines[0].id]:String(lines[0].count_hint),[lines[1].id]:String(lines[1].count_hint+1),[single.id]:String(single.count_hint)};
await receiveCounted(env);
assert.deepEqual(calls,[['inv_receive',{group:gid,counts:{[lines[0].id]:lines[0].count_hint}}],['inv_receive',{order:single.id,count:single.count_hint}]]);
assert.equal(ui.invCount[lines[0].id],undefined);assert.equal(ui.invCount[single.id],undefined);
assert.equal(ui.invCount[lines[1].id],String(lines[1].count_hint+1));
calls=[];ui.invCount={};await receiveCounted(env);assert.deepEqual(calls,[],'nothing counted: nothing sent');

// No staff on shift: no staff button.
delete inv.helper;html=inventoryView(env);assert.doesNotMatch(html,/đếm giúp/);
undom();
console.log('Merged crate line by line, the counted part, staff counting and counted crates on leaving the stock room passed.');
