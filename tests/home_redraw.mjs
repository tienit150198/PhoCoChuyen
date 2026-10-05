import assert from 'node:assert/strict';
import {setup} from '../public/js/v4/home-walk.js';

const tasks=new Map();let id=0,renders=0,onRender=()=>{};
globalThis.setTimeout=(fn,ms)=>{tasks.set(++id,{fn,ms});return id;};
globalThis.clearTimeout=id=>tasks.delete(id);
globalThis.requestAnimationFrame=fn=>setTimeout(fn,16);
globalThis.cancelAnimationFrame=clearTimeout;
function tick(){const [id,task]=tasks.entries().next().value||[];assert.ok(task,'a redraw is scheduled');tasks.delete(id);task.fn();}
const events=new Map();
const live={state:'open',flags:{home:true},send:()=>true,on:(t,fn)=>{events.set(t,fn);return ()=>events.delete(t);}};
const room={id:'bed',cols:6,frows:4,fix:[]};
const root={querySelector:()=>null,querySelectorAll:()=>[]};
const S={room:'bed',dlg:{open:true,querySelector:()=>null},env:{api:{state:{}}}};
const A={PX:0,CW:40,FR:30,geom:()=>({FY:50,W:250,H:200})};
const ui=setup({S,A,live,V:()=>({place:{key:'home1'}}),roomOf:()=>room,inRoom:()=>[],hostFor:()=>null,
  send:()=>{},render:()=>{renders++;onRender();},sfx:()=>{},calm:()=>true,roomSvg:()=>root});
ui.markup(room,A.geom());ui.resume();
while(tasks.size)tick(); // Drain the initial avatar paint before exercising live redraws.
events.get('home_room')({r:'bed',room:'r1',me:'me',people:[]});
S.drag={uid:'chair'}; // Drag begins after the network callback, before the scheduled render.
tick();assert.equal(renders,0,'a joined peer cannot redraw active drag DOM');
assert.equal(tasks.size,1,'only one bounded retry remains');
events.get('home')({ev:[{k:'in',pid:'spouse',name:'Bình',x:.5,y:.5}]});
events.get('down')({});
assert.equal(tasks.size,1,'bursts coalesce into the pending retry');
tick();assert.equal(renders,0,'disconnect also waits for the drag');
assert.ok([...tasks.values()][0].ms>=100,'waiting uses a timer instead of an animation-frame loop');
S.drag=null;S.press={id:1};tick();assert.equal(renders,0,'pointer press remains protected');
S.press=null;S.busy=true;tick();assert.equal(renders,0,'in-flight command remains protected');
S.busy=false;tick();assert.equal(renders,1,'one redraw publishes the latest state once idle');
assert.equal(tasks.size,0);
events.get('down')({});ui.reset();assert.equal(tasks.size,0,'reset clears pending redraw');
S.dlg.open=false;events.get('down')({});assert.equal(tasks.size,0,'closed dialogs cannot schedule redraw');
S.dlg.open=true;events.get('down')({});S.dlg.open=false;tick();
assert.equal(renders,1,'close between scheduling and callback prevents redraw');
assert.equal(tasks.size,0,'close does not keep retrying');
// Expiring the short sender pose redraws while its 15-second invitation remains open.
function tickMs(ms){const [key,task]=[...tasks.entries()].find(([,v])=>v.ms===ms)||[];assert.ok(task,`timer ${ms} exists`);tasks.delete(key);task.fn();}
S.dlg.open=true;
ui.markup(room,A.geom());ui.resume();
events.get('home_room')({r:'bed',room:'r1',me:'me',people:[{pid:'spouse',name:'Bình',x:.5,y:.5}]});tickMs(16);
events.get('home')({ev:[{k:'emote',id:'focus-offer',pid:'spouse',to:'me',kind:'hug',ttl:15}]});tickMs(16);
const oldButton={dataset:{dc:'hwReply',id:'focus-offer',answer:'shy'}};
globalThis.document={activeElement:oldButton};
S.dlg.contains=node=>node===oldButton;
let focused=null;
const newButton={dataset:{dc:'hwReply',id:'focus-offer',answer:'shy'},focus:options=>{focused={node:newButton,options};}};
S.dlg.querySelectorAll=()=>[newButton];
onRender=()=>{document.activeElement=null;};
tickMs(3200);tickMs(16);
assert.equal(focused?.node,newButton,'pose expiry preserves focus on the same invitation response');
assert.equal(focused.options.preventScroll,true,'focus restoration does not scroll the room');
assert.match(ui.socialPanel(),/focus-offer/,'offer remains answerable after pose expiry');
ui.reset();assert.equal(tasks.size,0);delete globalThis.document;
console.log('Home redraw: drag, press and busy deferral, coalescing, idle recovery and close/reset cleanup passed');
