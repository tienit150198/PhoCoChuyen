// ♿ Chạm chọn, chạm đặt (góp ý #443, a player who uses a screen reader): the room editor (v4/reno.js) without dragging.
// Every placed piece is named with its row and column, every cell of the chosen piece's zone is a real button, the
// chosen piece steps one cell at a time, refusals say why, and every move is the same jr_deco_put a drag sends.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import * as art from '../public/js/v4/deco-art.js';
import {setup} from '../public/js/v4/home-walk.js';
import * as view from '../public/js/v4/home-view.js';
import {escapeHTML,icon} from '../public/js/icons.js';
import {zoomer} from '../public/js/v4/home-zoom.js';
globalThis.document={body:{classList:{contains:()=>true}}};
globalThis.window={matchMedia:()=>({matches:false})};
const source=(await readFile(new URL('../public/js/v4/reno.js',import.meta.url),'utf8')).replace(/^import .*;.*\r?\n/gm,'').replace(/^export /gm,'');
const none=()=>'',many=new Proxy({},{get:()=>()=>[]});
const ui=new Function('A','walkSetup','live','sharedRooms','ownershipOrder','guestSession','icon','esc','Sound','BB','flagSVG','flagBadge','PALETTE','tr','zoomer',
  source+'\nreturn {S,page,onClick,say,chosen,placeChosen};')(art,setup,{on:()=>()=>{}},view.sharedRooms,view.ownershipOrder,view.guestSession,icon,escapeHTML,class{},many,none,none,{},t=>t,zoomer);
const U=art.U,wait=ms=>new Promise(r=>setTimeout(r,ms));
const chair={id:'ghe_dau',name:'Ghế đẩu',spot:'floor',cat:'table',w:1,h:1,rooms:['living'],tags:[],cozy:1,price:10,sell:5};
const frame={id:'tranh',name:'Tranh treo',spot:'wall',cat:'wall',w:1,h:1,rooms:['living'],tags:[],cozy:1,price:10,sell:5};
const room={id:'living',name:'Phòng khách',emoji:'🛋️',type:'living',cols:6,frows:3,wrows:2,cap:20,skin:{},
  fix:[{t:'cua',layer:'floor',x:5,y:0,w:1,h:1,block:true}]};
const deco={place:{key:'attic',where:'attic',name:'Gác',emoji:'🏠'},rooms:[room],items:[{id:'a',k:chair.id,r:room.id,fx:20,fy:20,f:0}],
  bag:[{id:'b',k:frame.id}],owned:[],cozy:{total:3,level:'Ấm',items:3,sets:0,steps:[]},sets:[],stats:{},count:2,ready:100};
const sent=[];
const env={confirmAction:async()=>true,api:{state:{journey:{deco},settings:{sound:false}},
  content:{journey:{deco:{items:[chair,frame],cats:[],skins:[],levels:[],fix_names:{cua:'cửa ra vào'}}}},
  command:async(action,payload)=>{sent.push({action,payload});return {message:'Đã lưu'};}}};
Object.assign(ui.S,{env,dlg:null,edit:true,room:'living',undoKey:'attic'});

// Choosing a placed piece: its name and place, the steps, ✕ Bỏ chọn, and every floor cell as a named button.
ui.S.sel='a';
let html=ui.page();
assert.match(html,/role="button" aria-label="Ghế đẩu, hàng 2 cột 2" aria-pressed="true"/,'a placed piece says its name, row and column, and that it is chosen');
for(const label of ['Dời sang trái một ô','Dời lên một ô','Dời xuống một ô','Dời sang phải một ô'])assert.ok(html.includes(`aria-label="${label}"`),label);
assert.match(html,/<button type="button" class="btn ghost small dc-unsel" data-dc="unsel">✕ Bỏ chọn<\/button>/,'a real button lets go of the piece');
const cells=[...html.matchAll(/<button type="button" class="dc-cell( \w+)?" data-dc="cell" data-x="(\d+)" data-y="(\d+)"[^>]*aria-label="([^"]+)"/g)];
assert.equal(cells.length,6*3,'every cell of the floor is a button (6 columns, 3 rows)');
assert.ok(cells.some(c=>c[4]==='hàng 1 cột 1, trống'),'an empty cell');
assert.ok(cells.some(c=>c[4]==='hàng 2 cột 2, đang ở đây'&&c[1]===' now'),'the chosen piece\'s own cell');
assert.ok(cells.some(c=>c[4]==='hàng 1 cột 6, vướng cửa ra vào'&&c[1]===' bad'),'a cell the door keeps clear says why');
assert.match(html,/class="dc-cells over" role="group" aria-label="Chỗ đặt ghế đẩu trên sàn: hàng 1 ở trong cùng, cột 1 bên trái"/,'the cells are one named group over the drawing');

// A cell: the same jr_deco_put a drag sends.
await ui.onClick('cell',{x:'60',y:'0'});
assert.deepEqual(sent.pop(),{action:'jr_deco_put',payload:{uid:'a',r:'living',x:60,y:0,f:0}},'a cell moves the chosen piece there');
ui.S.sel='a';
await ui.onClick('cell',{x:'100',y:'0'});
assert.equal(sent.length,0,'a blocked cell sends nothing');
assert.equal(ui.S.flash.text,'Chỗ này vướng cửa ra vào.','and says why');
ui.S.flash=null;

// ⬅️⬆️⬇️➡️ one cell; quick steps go as one move; at the edge, a line instead of a move.
ui.S.sel='a';
await ui.onClick('step',{uid:'a',dx:'1',dy:'0'});
await ui.onClick('step',{uid:'a',dx:'0',dy:'1'});
await wait(400);
assert.deepEqual(sent.pop(),{action:'jr_deco_put',payload:{uid:'a',r:'living',x:40,y:40,f:0}},'two quick steps: one move, right and down');
ui.S.sel='a';
await ui.onClick('step',{uid:'a',dx:'0',dy:'-1'});await ui.onClick('step',{uid:'a',dx:'0',dy:'-1'});await wait(400);
assert.equal(sent.pop().payload.y,0,'up to the back row');
const edge=structuredClone(deco.items[0]);deco.items[0]={...edge,fx:0,fy:0};ui.S.sel='a';
await ui.onClick('step',{uid:'a',dx:'-1',dy:'0'});await wait(400);
assert.equal(sent.length,0,'no step past the edge');
assert.equal(ui.S.flash.text,'Đã sát mép trái rồi.');
deco.items[0]={...edge,fx:80,fy:0};ui.S.sel='a';
await ui.onClick('step',{uid:'a',dx:'1',dy:'0'});await wait(400);
assert.equal(sent.length,0,'the door is the last column: nothing free beyond it');
assert.equal(ui.S.flash.text,'Chỗ này vướng cửa ra vào.');
deco.items[0]={...edge,fx:60,fy:0};ui.S.flash=null;ui.S.sel='a';
env.api.state.journey.deco={...deco,rooms:[{...room,cols:8}]};   // a wider room: the step hops over the door to the next free cell
await ui.onClick('step',{uid:'a',dx:'1',dy:'0'});await ui.onClick('step',{uid:'a',dx:'1',dy:'0'});await wait(400);
assert.equal(sent.pop().payload.x,120,'over the door (column 6) to column 7');
env.api.state.journey.deco=deco;deco.items[0]=edge;

// 📌 a pinned piece is not moved by a tap or a step either.
globalThis.localStorage={getItem:()=>'["a"]',setItem:()=>{}};
const pinned=new Function('A','walkSetup','live','sharedRooms','ownershipOrder','guestSession','icon','esc','Sound','BB','flagSVG','flagBadge','PALETTE','tr','zoomer',
  source+'\nreturn {S,onClick};')(art,setup,{on:()=>()=>{}},view.sharedRooms,view.ownershipOrder,view.guestSession,icon,escapeHTML,class{},many,none,none,{},t=>t,zoomer);
Object.assign(pinned.S,{env,dlg:null,edit:true,room:'living',sel:'a'});
await pinned.onClick('cell',{x:'0',y:'0'});await pinned.onClick('step',{uid:'a',dx:'1',dy:'0'});await wait(400);
assert.equal(sent.length,0,'pinned: nothing sent');
assert.match(pinned.S.flash.text,/ghim/);
delete globalThis.localStorage;

// A card from the bag: chosen, then a wall cell puts it there (the bag's own uid).
ui.S.sel='';
ui.S.held={k:frame.id,src:'bag'};   // a tap on its card (onClick 'hold' also scrolls the real drawer)
assert.equal(ui.chosen().it.id,frame.id);
html=ui.page();
assert.match(html,/class="dc-held" role="group" aria-label="Đang chọn tranh treo"/,'the held card is a named group, not a live region');
assert.ok(html.includes('aria-label="tường hàng 1 cột 1, trống"'),'a wall piece gets the wall\'s cells');
assert.ok(html.includes('data-dc="unhold">✕ Bỏ chọn</button>'),'✕ Bỏ chọn lets go of the card');
await ui.onClick('cell',{x:'20',y:'0'});
assert.deepEqual(sent.pop(),{action:'jr_deco_put',payload:{uid:'b',r:'living',x:20,y:0,f:0}},'the bag piece goes to the cell');
ui.S.held={k:frame.id,src:'bag'};await ui.onClick('unhold',{});
assert.equal(ui.chosen(),null,'Bỏ chọn: nothing chosen');

// 🔍 The room zooms (pinch, wheel, ＋ / － / ⤢) and the chosen piece's cells stay over the drawing, inside the zoomed frame.
ui.S.sel='a';
html=ui.page();
assert.match(html,/<div class="dc-zoom"><svg data-whole class="dc-room edit/,'the room sits in its zoom frame');
assert.match(html,/class="dc-zoombar" role="group" aria-label="Phóng to, thu nhỏ căn phòng"/,'zoom buttons over the room');
for(const z of ['out','in','fit'])assert.match(html,new RegExp(`data-dc="zoom" data-z="${z}"`),'zoom '+z);
assert.ok(html.indexOf('class="dc-cells over"')>html.indexOf('class="dc-zoom"')&&html.indexOf('class="dc-cells over"')<html.indexOf('class="dc-zoombar"'),'the cells zoom with the room');
assert.match(html,/class="dc-cell now" data-dc="cell" data-x="20" data-y="20"[^>]*aria-label="hàng 2 cột 2, đang ở đây"/);
assert.match(html,/class="dc-donecorner"><button type="button" class="btn primary small" data-dc="done"/,'✓ Xong always over the room while decorating');
assert.doesNotMatch(html,/home3d|Nhà 3D|dc-cells map/,'no 3D view any more');
await ui.onClick('unsel',{});
assert.equal(ui.S.sel,'','✕ Bỏ chọn');

// The live region: lines said together are read together; the same line again is read again.
const live={textContent:''};
ui.S.dlg={querySelector:s=>s==='.dc-live'?live:null};
ui.say('Đã chọn ghế đẩu, hàng 2 cột 2.');ui.say('Chạm chỗ muốn đặt.');
await wait(150);
assert.equal(live.textContent,'Đã chọn ghế đẩu, hàng 2 cột 2. Chạm chỗ muốn đặt.');
ui.say('Chạm chỗ muốn đặt.');await wait(70);
assert.equal(live.textContent,'','cleared first, so the same line is read again');
await wait(80);
assert.equal(live.textContent,'Chạm chỗ muốn đặt.');
ui.S.dlg=null;
console.log('Chạm chọn, chạm đặt: named pieces and cells, cell / step / bag moves as jr_deco_put, refusals say why, pins, zoom frame, live region passed');
