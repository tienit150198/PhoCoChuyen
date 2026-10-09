import assert from 'node:assert/strict';
import * as view from '../public/js/v4/home-view.js';
import {setup} from '../public/js/v4/home-walk.js';
import {readFile} from 'node:fs/promises';
import * as art from '../public/js/v4/deco-art.js';
import {escapeHTML,icon} from '../public/js/icons.js';
globalThis.location={search:''};
const {homeGuestsView}=await import('../public/js/v4/home-guests.js');

assert.equal(typeof view.guestSession,'function','guest view needs an isolated, cancellable session');
const draft={tab:'deco',room:'bed',edit:true,held:{k:'chair'},undo:[{chair:{x:12}}],undoKey:'own',mate:null};
const S={...draft}, session=view.guestSession(S);
const a={owner:{code:'A'},deco:{rooms:[],items:[]}},b={owner:{code:'B'},deco:{rooms:[],items:[]}};
let finishA;
const first=session.open('A',()=>new Promise(resolve=>finishA=resolve));
assert.equal(S.edit,false,'guest loading disables editing immediately');
await session.open('B',async()=>b);
finishA(a);assert.equal(await first,false,'late home A cannot replace home B');
assert.equal(S.remote,b);
let finishRefresh;
const refresh=session.refresh(()=>new Promise(resolve=>finishRefresh=resolve));
session.close();finishRefresh(a);await refresh;
assert.equal(S.remote,null,'a late refresh cannot reopen a closed guest view');
for(const key of Object.keys(draft))assert.deepEqual(S[key],draft[key],`personal ${key} restored`);
await assert.rejects(session.open('A',async()=>{throw new Error('revoked');}),/revoked/);
assert.equal(S.remote,null,'failed opening restores the personal draft');

const room={id:'bed',type:'bed',cols:6,frows:4,fix:[]};
const pieces=['tu_lanh','giuong','bon_tam','tu_quan_ao'].map((k,i)=>({id:`f${i}`,it:{id:k,w:2,spot:'floor'},q:{x:0,y:0}}));
const commands=[],actions=[],state={needs:{evening:{}},journey:{deco:{fridge:{cap:5}}}};
const G={room:'bed',edit:false,remote:a,dlg:{querySelector:()=>null,close:()=>actions.push('close')},env:{ui:{wd:{draft:{top:'own-shirt'}}},api:{state},act:(...args)=>actions.push(args)}};
const before=JSON.stringify(G.env);
const ui=setup({S:G,A:{PX:0,CW:40,FR:30,geom:()=>({FY:50}),anchor:()=>[0,50]},V:()=>({relax:[{id:'ngam',ok:true}]}),roomOf:()=>room,inRoom:()=>pieces,hostFor:()=>null,send:(...args)=>commands.push(args),render:()=>{},sfx:()=>{},calm:()=>true,roomSvg:()=>null});
for(const p of pieces)ui.tap(room,{x:20,y:20},p.id);
for(const op of ['hwOpen','hwBuy','hwEat','hwWardrobe','hwClothesPick'])await ui.click(op,{item:'food'});
assert.deepEqual(commands,[],'guest furniture never charges or changes home benefits');
assert.deepEqual(actions,[],'guest furniture never routes into personal house actions');
assert.equal(ui.panel({fridge:{cap:5}},room),'','guest never opens own fridge as fallback');
assert.equal(JSON.stringify(G.env),before,'avatar state and wardrobe drafts remain personal and unchanged');
ui.reset();

const listing={own_home:{home:{name:'Nhà phố'}},friends:[{code:'A',name:'An <script>'}],incoming:[{id:1,code:'A',name:'An',kind:'stay'}],outgoing:[{id:2,code:'B',name:'Bình',kind:'visit'}],active:[{id:3,code:'A',name:'An',kind:'stay',mine:false},{id:4,code:'B',name:'Bình',kind:'visit',mine:true}],homes:[{code:'A',name:'An',kind:'stay',home:{name:'Nhà phố'}}]};
const html=homeGuestsView(listing,{code:'A'});
for(const text of ['Mời vào chơi','Mời ở chung','Không cần kết hôn','Vào nhà','Thu hồi quyền vào nhà','Từ chối','Rời nhà','An &lt;script&gt;'])assert.ok(html.includes(text),text);
assert.match(html,/value="A" selected/,'friend entrypoint preselects the requested friend');
assert.ok(!html.includes('<script>'));
assert.ok(html.includes('Vào chơi trong 2 giờ kể từ khi đồng ý.'),'temporary invitation duration is clear before accepting');
{ // 🏡 F#307: a stay home offers moving your own things in, then back
  const stayHome=on=>homeGuestsView({...listing,homes:[{code:'A',name:'An',kind:'stay',id:'abc',here:on,home:{name:'Nhà phố'}}]});
  assert.match(stayHome(false),/data-hg="move" data-id="abc" data-on="1"[^>]*>🪴 Dọn đồ sang ở</);
  assert.match(stayHome(true),/data-hg="move" data-id="abc" data-on="0"[^>]*>📦 Dọn đồ về</);
  assert.ok(!homeGuestsView({...listing,homes:[{code:'B',name:'Bình',kind:'visit',id:'v1',home:{name:'Nhà'}}]}).includes('data-hg="move"'),'a visit never moves things in');
}

// Exercise the actual renderer with precisely the minimal, private-field-free server projection.
globalThis.document={body:{classList:{contains:()=>true}}};
globalThis.window={matchMedia:()=>({matches:false})};
const source=(await readFile(new URL('../public/js/v4/reno.js',import.meta.url),'utf8')).replace(/^import .*;.*\r?\n/gm,'').replace(/^export /gm,'');
const renderer=new Function('A','walkSetup','live','sharedRooms','ownershipOrder','guestSession','icon','esc','Sound',source+'\nreturn {S,page,onClick,send,guest,loadMate,tintOf};')(art,setup,{on:()=>()=>{}},view.sharedRooms,view.ownershipOrder,view.guestSession,icon,escapeHTML,class {});
const remote={owner:{code:'A',name:'An'},access:{kind:'stay'},deco:{place:{key:'house-A',where:'own',name:'Nhà phố',emoji:'🏡',repairs:false},rooms:[{...room,name:'Phòng ngủ',emoji:'🛏️',wrows:3,skin:{},cap:30}],more:[],items:[]},reno:{parts:[]},mate:{},colors:{deco:{}}};
Object.assign(renderer.S,{env:{api:{state,content:{journey:{deco:{items:[]}}},command:(...args)=>commands.push(args)}},remote,dlg:{querySelector:()=>null},room:'bed'});
const screen=renderer.page();
assert.ok(screen.includes('Nhà An'),'minimal guest projection renders');
assert.ok(!screen.includes('data-dc="edit"'),'guest has no decorating controls');
assert.ok(!screen.includes('data-dc="fix"'),'guest has no repair controls');
for(const op of ['edit','buyBag','flip','pickAll','photoSave','fix','relax'])await renderer.onClick(op,{});
await renderer.send('jr_deco_buy',{item:'chair'});
assert.deepEqual(commands,[],'direct forged UI operations cannot reach personal commands during a guest session');
assert.equal(renderer.S.edit,false);
// F#280: a housemate in a villa switches floors like the owner (the rail shows one floor at a time).
const up={...room,id:'up',name:'Phòng trên lầu',emoji:'🛋️',wrows:3,skin:{},cap:30,fl:2};
// 🏰 F 09/10: a villa bought in Mua sắm is projected as it is (place 'estate', no repairs, no structure).
const villa={...remote,reno:null,deco:{...remote.deco,place:{key:'estate:bt_vuon_da_lat:3',where:'estate',kind:'bt_vuon_da_lat',name:'Biệt thự vườn Đà Lạt',emoji:'🌲',repairs:false},rooms:[{...remote.deco.rooms[0],fl:1},up]}};
await renderer.guest.open('A',async()=>villa);renderer.S.room='bed';
assert.ok(renderer.page().includes('data-dc="floor" data-fl="2"'),'the floor tabs show for a guest');
const dlg=renderer.S.dlg;renderer.S.dlg=null;   // render() is a no-op without the dialog; the state is what counts
await renderer.onClick('floor',{fl:'2'});renderer.S.dlg=dlg;
assert.equal(renderer.S.room,'up','a guest reaches the second floor');
assert.ok(renderer.page().includes('Phòng trên lầu'),'the second floor rooms are drawn');
assert.ok(renderer.page().includes('Nhà An'),'the villa guest card shows');
renderer.guest.close();await renderer.guest.open('A',async()=>remote);renderer.S.room='bed';
state.colors={deco:{same:'my-blue'}};remote.colors.deco.same='host-red';
assert.equal(renderer.tintOf('same'),'host-red','identical furniture IDs use owner projection colors');
let closed=0,notified=0;
await renderer.guest.open('A',async()=>remote);
renderer.S.env.api.json=async()=>{throw Object.assign(new Error('Access revoked'),{status:403});};
renderer.S.env.toast=()=>notified++;
renderer.S.dlg={open:true,close:()=>{closed++;renderer.guest.close();}};
await renderer.loadMate();
assert.equal(closed,1,'revocation closes the room on the next refresh');
assert.equal(notified,1,'revocation explains why the guest view closed');
assert.equal(renderer.S.remote,null);
const managerSource=(await readFile(new URL('../public/js/v4/home-guests.js',import.meta.url),'utf8')).replace(/^import .*;.*\r?\n/gm,'').replace(/^export /gm,'');
const manager=new Function('icon','esc','live',managerSource+'\nreturn {S,act};')(icon,escapeHTML,{on:()=>()=>{}});
const sent=[];
Object.assign(manager.S,{data:listing,env:{api:{csrf:'test',json:async(url,options)=>{if(options?.method==='POST')sent.push(JSON.parse(options.body));return listing;}}},dlg:{open:true,querySelector:()=>({innerHTML:''}),setAttribute:()=>{}}});
for(const op of ['answer','revoke','leave']){
  await manager.act(op,{id:'abcdef0123456789abcdef0123456789',answer:'accept'});
  clearTimeout(manager.S.timer);
}
assert.deepEqual(sent.map(r=>r.id),Array(3).fill('abcdef0123456789abcdef0123456789'),'opaque invitation IDs remain strings in accept, revoke, and leave requests');

// 🎨 Trang trí giúp (game/home_coop.py): the owner's bag only, every change a checked POST, nothing personal.
const sofa={id:'sofa',name:'Sofa vải',cat:'table',spot:'floor',w:3,h:1,price:200,sell:100,cozy:3,rooms:['bed'],tags:[],surface:0,ledge:0};
const coopRemote={...remote,access:{kind:'deco'},deco:{...remote.deco,bag:[{id:'b1',k:'sofa'}],count:2,items:[{id:'p1',k:'sofa',r:'bed',x:0,y:0,f:0}]},coop:{id:'g1',expires_at:null,log:[{id:7,name:'Bình <b>',text:'đã đặt Sofa vải ở phòng ngủ',undone:false}]}};
const posts=[],coopCommands=[];
Object.assign(renderer.S,{coop:true,edit:true,held:null,sel:'',drawer:'bag',undo:[],env:{toast:()=>notified++,api:{csrf:'t',state,content:{journey:{deco:{items:[sofa],cats:[],sets:[],levels:[],skins:[]}}},command:(...args)=>coopCommands.push(args),
  json:async(url,options)=>{posts.push([url,options?JSON.parse(options.body):null]);return {message:'Đã dời Sofa vải.',duplicate:false,view:{...coopRemote,deco:{...coopRemote.deco,bag:[]}}};}}},
  dlg:{open:false,querySelector:()=>null,querySelectorAll:()=>[],setAttribute:()=>{}}});
await renderer.guest.open('A',async()=>coopRemote);renderer.S.edit=true;   // openCoopReno opens straight into decorating
let coopScreen=renderer.page();
for(const text of ['Trang trí giúp nhà An','Túi chủ nhà','data-dc="done"','đã đặt Sofa vải ở phòng ngủ','Bình &lt;b&gt;','hoàn tác được'])assert.ok(coopScreen.includes(text),text);
for(const text of ['dc-money','data-d="shop"','data-d="skin"','data-dc="pickAll"','data-dc="photo"'])assert.ok(!coopScreen.includes(text),`coop hides ${text}`);
renderer.S.sel='p1';coopScreen=renderer.page();
assert.ok(coopScreen.includes('data-dc="flip"')&&coopScreen.includes('data-dc="pick"'),'a friend can flip and put back');
assert.ok(!coopScreen.includes('data-dc="sell"')&&!coopScreen.includes('data-dc="tint"'),'a friend can never sell or paint');
for(const [op,data] of [['buyBag',{}],['sell',{uid:'p1'}],['pickAll',{}],['tint',{uid:'p1'}],['skin',{part:'wall',skin:'x'}],['photoSave',{}],['fix',{part:'all'}],['relax',{act:'x'}],['drawer',{d:'shop'}],['hold',{k:'sofa',src:'shop'}]])await renderer.onClick(op,data);
assert.equal(renderer.S.drawer,'bag','the shop never opens');assert.equal(renderer.S.held,null,'nothing held from the shop');
for(const action of ['jr_deco_buy','jr_deco_sell','jr_deco_skin','jr_wd_deco','jr_relax_do','jr_reno_fix'])assert.equal(await renderer.send(action,{uid:'p1'}),null,action);
assert.deepEqual(posts,[],'only place / move / put back / undo reach the server');
const moved=await renderer.send('jr_deco_put',{uid:'p1',r:'bed',x:4,y:0,f:0});
assert.equal(posts.length,1);assert.equal(posts[0][0],'/api/home-guests/deco/act');
assert.deepEqual(posts[0][1],{uid:'p1',r:'bed',x:4,y:0,f:0,code:'A',action:'put'});
assert.equal(moved.duplicate,false);assert.deepEqual(renderer.S.remote.deco.bag,[],'the owner room that came back is the one drawn');
await renderer.send('jr_deco_pick',{uid:'p1'});await renderer.send('jr_deco_layout',{set:{p1:null}});
assert.deepEqual(posts.slice(1).map(p=>p[1].action),['pick','layout']);
assert.deepEqual(coopCommands,[],'the friend\'s own save never gets a command');
let coopClosed=0;renderer.S.dlg={open:true,querySelector:()=>null,querySelectorAll:()=>[],setAttribute:()=>{},close(){coopClosed++;this.open=false;}};
renderer.S.env.api.json=async()=>{throw Object.assign(new Error('Quyền trang trí đã kết thúc.'),{status:403});};
assert.equal(await renderer.send('jr_deco_put',{uid:'p1',r:'bed',x:0,y:0,f:0}),null);
assert.equal(coopClosed,1,'a revoked permission closes the room');
renderer.guest.close();renderer.S.coop=false;

const {decoView}=await import('../public/js/v4/home-guests.js');
const decoList={...listing,friends:[{code:'A',name:'An'},{code:'B',name:'Bình'}],deco:{hours:[0,2,24,168],mine:[{id:'g1',code:'B',name:'Bình',expires_at:null}],homes:[{id:'g2',code:'A',name:'An <i>',expires_at:2e9,home:{name:'Nhà phố'}}],
  log:[{id:9,name:'Bình',text:'đã dời Sofa vải',undo:true,undone:false},{id:8,name:'Bình',text:'đã cất Đèn vào túi',undo:false,undone:true}]}};
const decoHtml=decoView(decoList,{decoCode:'A'});
for(const text of ['Cho trang trí','Thu hồi','Vào trang trí','Thôi trang trí','↶ Hoàn tác','Đã hoàn tác','An &lt;i&gt;','7 ngày','không đổi chủ'])assert.ok(decoHtml.includes(text),text);
assert.ok(!/<option value="B"/.test(decoHtml),'a friend who already may decorate is not offered again');
assert.match(decoHtml,/value="A" selected/);
assert.ok(decoView({...decoList,own_home:null},{}).includes('căn nhà mình sở hữu'),'only an owner can grant');
assert.equal(decoView(listing,{}),'','older servers without the listing show nothing');
Object.assign(manager.S,{data:decoList,decoCode:'A',decoHours:24});sent.length=0;
const urls=[];manager.S.env.api.json=async(url,options)=>{if(options?.method==='POST'){urls.push(url);sent.push(JSON.parse(options.body));}return decoList;};
manager.S.env.api.refresh=async()=>{};
for(const [op,data] of [['decoGrant',{}],['decoRevoke',{id:'g1'}],['decoLeave',{id:'g2'}],['decoUndo',{id:'9'}]]){await manager.act(op,data);clearTimeout(manager.S.timer);}
assert.deepEqual(urls,['grant','revoke','leave','undo'].map(x=>`/api/home-guests/deco/${x}`));
assert.deepEqual(sent,[{code:'A',hours:24},{id:'g1'},{id:'g2'},{id:9}]);
manager.S.decoCode='nobody';sent.length=0;await manager.act('decoGrant',{});clearTimeout(manager.S.timer);
assert.deepEqual(sent,[],'only a friend in the list can be granted');
console.log('Guest home: isolated state, preserved drafts, stale reads, and denied furniture actions passed; Trang trí giúp: bag only, checked POSTs, owner controls');
