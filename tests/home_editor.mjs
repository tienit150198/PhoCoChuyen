// 🪴 The home room editor without 3D (owner 23/10: "nhà bình thường", góp ý #358 #330 #372): every move, turn and put
// away is one server command (owned pieces only; a guest edits nothing; a friend with the owner's grant goes through the
// checked coop endpoint), a turned piece is drawn turned, the room zooms, and the character sits, lies and uses things.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import * as art from '../public/js/v4/deco-art.js';
import {setup} from '../public/js/v4/home-walk.js';
import * as view from '../public/js/v4/home-view.js';
import {zoomer,ZMAX} from '../public/js/v4/home-zoom.js';
import {actFor,poseFigure,posed,POSES} from '../public/js/v4/home-pose.js';
import {figureOf} from '../public/js/v4/look.js';
import {escapeHTML,icon} from '../public/js/icons.js';
const source=(await readFile(new URL('../public/js/v4/reno.js',import.meta.url),'utf8')).replace(/^import .*;.*\r?\n/gm,'').replace(/^export /gm,'');
globalThis.document={body:{classList:{contains:()=>true}}};
globalThis.window={matchMedia:()=>({matches:false})};
const make=()=>new Function('A','walkSetup','live','sharedRooms','ownershipOrder','guestSession','icon','esc','Sound','zoomer','BB','flagSVG','tr',
  source+'\nreturn {S,dropAt,pickSkin,onClick,onKey,guest,page,placeChosen,hw};')(art,setup,{on:()=>()=>{}},view.sharedRooms,view.ownershipOrder,view.guestSession,icon,escapeHTML,class{},zoomer,new Proxy({},{get:()=>()=>[]}),()=>'',t=>t);
const ui=make();
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const chair={id:'ghe_dau',name:'Ghế',spot:'floor',cat:'table',w:1,h:1,rooms:['living'],tags:['seat'],cozy:1,price:10,sell:5};
const sofa={id:'sofa',name:'Sofa vải',spot:'floor',cat:'table',w:3,h:1,rooms:['living'],tags:['seat','soft'],cozy:3,price:180,sell:90};
const lamp={id:'den_ngu',name:'Đèn ngủ',spot:'top',cat:'light',w:1,h:1,rooms:['living'],tags:['lamp'],cozy:1,price:30,sell:15};
const bed={id:'giuong',name:'Giường',spot:'floor',cat:'bed',w:3,h:2,rooms:['living'],tags:['bed'],cozy:3,price:300,sell:150};
const room={id:'living',name:'Phòng',emoji:'🛋️',type:'living',cols:6,frows:3,wrows:2,cap:20,skin:{},fix:[{t:'door',layer:'floor',x:5,y:0,w:1,h:1,block:true}]};
const deco={place:{key:'attic',where:'attic',name:'Gác',emoji:'🏠'},rooms:[room],
  items:[{id:'a',k:chair.id,r:room.id,fx:20,fy:20,f:0},{id:'s',k:sofa.id,r:room.id,fx:0,fy:40,f:0},{id:'t',k:sofa.id,r:room.id,fx:60,fy:0,f:0,rot:3},
    {id:'g',k:bed.id,r:room.id,fx:0,fy:0,f:0,rot:2,face:'back'}],
  bag:[{id:'b',k:chair.id},{id:'c',k:sofa.id,rot:1}],owned:[],cozy:{total:3,level:'Ấm',items:3,sets:0,steps:[]},sets:[],stats:{},count:4,ready:100};
const sent=[],posts=[];
const state={journey:{deco},settings:{sound:false}};
const env={confirmAction:async()=>true,api:{state,csrf:'x',content:{journey:{deco:{items:[chair,sofa,lamp,bed],cats:[],levels:[],facing:['sofa','tv'],skins:[{id:'kem',part:'wall',price:0}]}}},
  command:async(action,payload)=>{sent.push({action,payload});return {message:'Đã lưu'};},
  json:async(url,options)=>{posts.push({url,body:JSON.parse(options.body)});return {message:'Đã lưu'};}}};
Object.assign(ui.S,{env,dlg:null,edit:true,room:'living',undoKey:'attic'});

// ---- moves stay server commands on owned pieces
ui.S.sel='a';await ui.placeChosen({r:'living',x:40,y:0,f:0});
assert.deepEqual(sent.pop(),{action:'jr_deco_put',payload:{uid:'a',r:'living',x:40,y:0,f:0}},'a straight piece sends no turn');
ui.S.sel='p:other';await ui.placeChosen({r:'living',x:0,y:0,f:0});assert.equal(sent.length,0,'other residents\' pieces cannot be moved');
ui.S.held={src:'bag',k:chair.id};await ui.dropAt({r:'living',x:40,y:20,f:0});assert.deepEqual(sent.pop().payload,{uid:'b',r:'living',x:40,y:20,f:0},'bag placement uses the owned uid');
await ui.pickSkin('wall','kem');assert.equal(sent.pop().action,'jr_deco_skin','paint remains server-owned');
await ui.onClick('pick',{uid:'a'});assert.equal(sent.pop().action,'jr_deco_pick','storage remains server-owned');

// ---- ↻ Xoay 90°: the turned footprint must fit (a 3 × 1 sofa turned is 1 × 3: in a 3-row room it goes to the back row)
await ui.onClick('turn',{uid:'s'});
assert.deepEqual(sent.pop().payload,{uid:'s',r:'living',x:0,y:0,f:0,rot:1},'turned a quarter, moved back to fit');
deco.items[1]={...deco.items[1],rot:3};
await ui.onClick('turn',{uid:'s'});
assert.equal(sent.pop().payload.rot,0,'from the left back to the front: rot 0 is sent');
deco.items[1]={id:'s',k:sofa.id,r:room.id,fx:0,fy:40,f:0};
await ui.onClick('turn',{uid:'a'});assert.equal(sent.pop().payload.rot,1,'a chair turns');
// the door is in the way: the nearest spot that fits
deco.items[0]={id:'a',k:sofa.id,r:room.id,fx:60,fy:40,f:0};
await ui.onClick('turn',{uid:'a'});const fit=sent.pop().payload;
assert.equal(fit.rot,1);assert.equal(fit.y,0);assert.ok(fit.x<100,'not into the door column');
deco.items[0]={id:'a',k:chair.id,r:room.id,fx:20,fy:20,f:0};
// a small thing on a table never turns
deco.items.push({id:'l',k:lamp.id,r:room.id,fx:0,fy:0,f:0,on:'s'});
await ui.onClick('turn',{uid:'l'});assert.equal(sent.length,0,'a lamp on the sofa does not turn');
deco.items.pop();
// the piece in hand turns before it is put down (and a bag piece keeps its own turn)
ui.S.held={src:'bag',k:sofa.id,rot:1};await ui.onClick('turn',{});assert.equal(ui.S.held.rot,2);
await ui.dropAt({r:'living',x:0,y:40,f:0});assert.deepEqual(sent.pop().payload,{uid:'c',r:'living',x:0,y:40,f:0,rot:2},'the turn in hand goes with it');
// R turns the chosen piece; busy: nothing
const key=k=>({key:k,shiftKey:false,preventDefault(){},target:{closest:s=>s==='svg.dc-room'?{}:null}});
ui.S.held=null;ui.S.sel='s';ui.S.busy=true;ui.onKey(key('r'));await wait(5);assert.equal(sent.length,0,'pending commands block another turn');
ui.S.busy=false;ui.onKey(key('r'));await wait(5);assert.equal(sent.pop().payload.rot,1,'R turns');

// ---- drawn turned: tools, the turned drawing, the bed's back
ui.S.sel='t';ui.S.held=null;
let html=ui.page();
assert.match(html,/data-dc="turn" data-uid="t"[^>]*>↻ Xoay · quay trái<\/button>/,'↻ Xoay says where it faces');
assert.match(html,/<g class="dc-it sel" data-uid="t" data-k="sofa"[^>]*><g class="dc-piece"><g transform="translate\([^)]*\)"><g transform="matrix\(-/,'turned left: the slanted side drawing');
const turned=art.turn(sofa,1);
assert.deepEqual([turned.w,turned.h,turned.rot,turned.base],[1,3,1,sofa]);
assert.equal(art.turn(sofa,0),sofa);assert.equal(art.turn(turned,2),turned,'never turned twice');
assert.equal(art.turn(sofa,1),turned,'the same turned item each time');
assert.match(art.pieceAt(turned,10,90,0),/matrix\(0\.6 -0\.\d+ 0 1/);
assert.ok(art.lift(turned)>0&&art.lift(sofa)===0);
const back=art.pieceAt(art.turn(sofa,2),0,0,0),front=art.pieceAt(sofa,0,0,0);
assert.notEqual(back,front);assert.equal(back,art.pieceAt(sofa,0,0,0,null,'back'),'rot 2 is the drawn back');
assert.doesNotMatch(html,/home3d|Nhà 3D|◈/,'no 3D view any more');

// ---- 🔍 zoom: controls, a pinch-free check of the math, the wheel at full view leaves the page scrolling
assert.match(html,/class="dc-zoombar"/);
const Z=zoomer(),frame={style:{},classList:{add(){},remove(){}},offsetWidth:400,offsetHeight:300,parentElement:{getBoundingClientRect:()=>({left:0,top:0,width:400,height:300}),classList:{toggle(){}},querySelector:()=>null,querySelectorAll:()=>[]}};
const root={querySelector:s=>s==='.dc-zoom'?frame:null};
Z.button(root,'in');assert.ok(Z.k>1);assert.match(frame.style.transform,/scale\(1\.350\)/);
Z.zoomAt(root,1);Z.zoomAt(root,ZMAX,400,300);assert.equal(Z.k,ZMAX);assert.match(frame.style.transform,/translate\(-800\.0px,-600\.0px\) scale\(3\.000\)/,'zoomed at the corner stays inside');
Z.zoomAt(root,9,0,0);assert.equal(Z.k,ZMAX,'never past the max');
Z.button(root,'fit');assert.equal(Z.k,1);assert.equal(frame.style.transform,'');
let prevented=false;assert.equal(Z.wheel(root,{deltaY:100,preventDefault(){prevented=true;}}),false);assert.equal(prevented,false,'full view: the wheel scrolls the page');
assert.equal(Z.wheel(root,{deltaY:-100,clientX:200,clientY:150,preventDefault(){prevented=true;}}),true);assert.ok(prevented&&Z.k>1);
// two fingers: a pinch, then one finger up ends it (not a tap)
Z.reset(root);
assert.equal(Z.down(root,{pointerId:1,isPrimary:true,clientX:100,clientY:100}),false);
assert.equal(Z.down(root,{pointerId:2,isPrimary:false,clientX:200,clientY:100}),true,'second finger: a pinch');
assert.equal(Z.move(root,{pointerId:2,clientX:300,clientY:100}),true);assert.ok(Math.abs(Z.k-2)<.01,'fingers twice as far: twice as big');
assert.equal(Z.up(root,{pointerId:2}),true);assert.equal(Z.pinching,false);

// ---- 🪑 using the furniture: what each piece is for, every pose drawn, and the character sits down
const actOf=(id,tags=[],extra={})=>actFor({id,tags,spot:'floor',...extra});
assert.equal(actOf('sofa',['seat']),'sit');assert.equal(actOf('giuong',['bed']),'lie');assert.equal(actOf('tv',['screen']),'watch');
assert.equal(actOf('ke_sach',['books']),'read');assert.equal(actOf('may_chay_bo'),'gym');assert.equal(actOf('bep_ga',['kitchen']),'cook');
assert.equal(actOf('bon_tam',['soak']),'bath');assert.equal(actOf('may_choi_game',['screen','gaming']),'play');assert.equal(actOf('tranh',['art']),'');
const F=figureOf({},'female');
for(const a of POSES){const svg=posed(poseFigure(F,a,{asleep:true}),a);assert.match(svg,new RegExp(`class="hp-pose hp-${a}"`));assert.ok(svg.length>500,a);}
assert.match(posed(poseFigure(F,'lie',{asleep:true}),'lie',{asleep:true}),/rotate\(-90\)[\s\S]*class="hp-zz"/,'lying down, asleep');
ui.S.edit=false;ui.S.sel='';deco.items[1]={id:'s',k:sofa.id,r:room.id,fx:0,fy:40,f:0};
ui.hw().tap(room,{x:60,y:120},'s');await wait(5);
assert.equal(globalThis.__homeWalk.state().pose,'sit','tapping the sofa: walk up and sit down');
ui.hw().tap(room,{x:200,y:150},'');await wait(5);
assert.equal(globalThis.__homeWalk.state().pose,'','a tap on the floor: up again and walk');
state.needs={evening:{chosen:true}};
ui.hw().tap(room,{x:0,y:0},'g');await wait(5);
assert.equal(globalThis.__homeWalk.state().pose,'lie','after choosing the evening the bed is for sleeping');
delete state.needs;

// ---- 🏡 living in a friend's home (góp ý #330): the host's furniture is arranged only with the host's grant
state.journey.deco={...deco,place:{...deco.place,where:'stay'}};ui.S.edit=true;
env.api.homeGuests={homes:[{kind:'stay',here:true,code:'host1',name:'Lan'}],deco:{homes:[]}};
html=ui.page();assert.match(html,/🏡 Đồ của Lan/);assert.match(html,/Nhờ chủ nhà bật 🎨 Cho trang trí/);assert.doesNotMatch(html,/data-dc="stayCoop"/,'no grant: no button');
env.api.homeGuests.deco.homes=[{code:'host1',name:'Lan'}];
html=ui.page();assert.match(html,/data-dc="stayCoop" data-code="host1"/,'with the grant: arrange the host furniture');
state.journey.deco=deco;delete env.api.homeGuests;

// ---- a visitor edits nothing; a friend with the owner's grant goes through the checked endpoint
ui.S.edit=true;
const remote={owner:{code:'friend'},deco};
await ui.guest.open('friend',async()=>remote);
ui.S.sel='s';await ui.onClick('turn',{uid:'s'});await ui.onClick('pick',{uid:'s'});ui.onKey(key('r'));await wait(5);
assert.equal(sent.length+posts.length,0,'guest cannot edit even when an owned id collides');
ui.S.coop=true;ui.S.edit=true;await ui.onClick('turn',{uid:'s'});
assert.equal(sent.length,0,'cooperative edits never touch the visitor save');
assert.equal(posts.at(-1).url,'/api/home-guests/deco/act');assert.equal(posts.at(-1).body.code,'friend');
assert.equal(posts.at(-1).body.action,'put');assert.equal(posts.at(-1).body.rot,1,'the friend turns the owner\'s sofa');
await ui.onClick('pick',{uid:'s'});assert.equal(posts.at(-1).body.action,'pick','and may put it away into the owner\'s bag');
// ---- #518 "nhà cứ có nét đứt": stroke, stroke-width and stroke-dasharray are inherited, so a class that draws dashes in
// the SVG must never also name an HTML box (the editor's layout <div class="dc-grid"> once dashed every drawing inside it)
{const css=await readFile(new URL('../public/css/reno.css',import.meta.url),'utf8'),js=source+await readFile(new URL('../public/js/v4/deco-art.js',import.meta.url),'utf8');
  const dashed=new Set();for(const m of css.matchAll(/([^{}]+)\{([^}]*)\}/g))if(/stroke-dasharray\s*:/.test(m[2]))for(const c of m[1].matchAll(/\.([\w-]+)/g))dashed.add(c[1]);
  for(const m of js.matchAll(/<(div|section|p|span|button|figure|li|ul|header|footer|dialog|label)\b[^>]*class="([^"$]*)"/g))
    for(const c of m[2].split(/\s+/))assert.ok(!dashed.has(c),`HTML <${m[1]} class="${c}"> would dash every drawing inside it`);
  assert.match(source,/class="dc-snapgrid"/,'the snap grid has its own class');}
console.log('Home editor (2D): owned moves, turns that fit, held turns, R, busy/guest rejection, coop endpoint, turned drawing, zoom, poses passed');
