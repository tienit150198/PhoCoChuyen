import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync(new URL('../public/js/v4/fair-booth.js',import.meta.url),'utf8');
const slice=(start,end)=>source.slice(source.indexOf(start),source.indexOf(end,source.indexOf(start)));
function fixture(){
 const D={mode:'solo',step:'room',shoot:null,paying:false,ticket:false,shots:[],room:null,visit:0},S={tab:'pb',dlg:{open:true},busy:false};
 let reply,loops=0,renders=0,requests=0,builds=0;const sounds=[],tickets=[],timers=[];
 const sourceParts=[slice('  async function pay(){','  const canPay='),slice('  function toLobby(){','  /* ---- actions ---- */'),slice('  function startSolo(){','  function find(){'),slice('  async function shootSolo(){','  function go(){'),slice('  function startShoot(','  function capture(){'),slice('  function tickShoot(','  function loop(){')].join('\n');
 const context=vm.createContext({D,S,SHOTS:4,GAP:3200,SHOOTER:{shoot:['shoot'],room:['room'],done:['done']},pick:a=>a[0],performance:{now:()=>1000},
  send:()=>{requests++;return new Promise(resolve=>{reply=resolve;});},render:()=>renders++,sfx:type=>sounds.push(type),setTimeout:fn=>timers.push(fn),clearTimeout:()=>{},stopLoop:()=>{D.shoot=null;},live:{send:()=>true},keepTicket:v=>{D.ticket=v;tickets.push(v);},edit:()=>({reset(){}}),loop:()=>loops++,capture:()=>D.shots.push({}),build:()=>builds++});
 const ui=vm.runInContext(sourceParts+';({shootSolo,leave,startSolo,tickShoot})',context);
 return {D,S,ui,sounds,tickets,timers,answer:(ok=true)=>reply(ok?{fair:{game:'photo'}}:null),stats:()=>({loops,renders,requests,builds})};
}

for(const reopen of [false,true])test(`a delayed photo payment after leaving ${reopen?'and reopening ':''}retains a ticket for an explicit next shot`,async()=>{
 const f=fixture(),pending=f.ui.shootSolo();f.S.tab='home';f.S.dlg.open=false;f.ui.leave();
 if(reopen){f.S.tab='pb';f.S.dlg.open=true;f.ui.startSolo();}
 f.answer();await pending;
 assert.equal(f.D.ticket,true,'paid ticket remains reusable until a later explicit shot');assert.equal(f.D.shoot,null);assert.equal(f.stats().loops,0);
 if(!reopen)assert.deepEqual(f.sounds,[],'a closed booth makes no payment sound');
 f.S.tab='pb';f.S.dlg.open=true;if(!reopen)f.ui.startSolo();await f.ui.shootSolo();
 assert.equal(f.D.step,'shoot');assert.equal(f.D.ticket,false);assert.equal(f.stats().requests,1,'the retained ticket is consumed without a second payment');assert.equal(f.stats().loops,1);
});

test('leaving a paid ticket then entering another stall cannot start a hidden shoot',async()=>{
 const f=fixture(),pending=f.ui.shootSolo();f.S.tab='ring';f.ui.leave();f.answer();await pending;
 assert.equal(f.D.ticket,true);assert.equal(f.stats().loops,0);assert.equal(f.D.step,'lobby');
});

test('a visible shoot consumes one ticket and duplicate taps cannot start twice',async()=>{
 const f=fixture(),first=f.ui.shootSolo(),second=f.ui.shootSolo();f.answer();await Promise.all([first,second]);
 assert.equal(f.stats().requests,1);assert.equal(f.stats().loops,1);assert.deepEqual(f.tickets,[true,false]);
 await f.ui.shootSolo();assert.equal(f.stats().requests,1);assert.equal(f.stats().loops,1);
});

test('refused payment never leaves a ticket or starts a shoot',async()=>{
 const f=fixture(),pending=f.ui.shootSolo();f.answer(false);await pending;
 assert.equal(f.D.ticket,false);assert.equal(f.D.shoot,null);assert.equal(f.D.paying,false);assert.equal(f.stats().loops,0);
});

test('leaving during the final photo flash cannot resurrect an empty print screen',async()=>{
 const f=fixture(),pending=f.ui.shootSolo();f.answer();await pending;
 f.D.shoot.done=3;f.ui.tickShoot(13800);assert.equal(f.timers.length,1);
 f.S.tab='home';f.ui.leave();const renders=f.stats().renders;f.timers[0]();
 assert.equal(f.D.step,'lobby');assert.equal(f.stats().builds,0);assert.equal(f.stats().renders,renders);assert.equal(f.D.ticket,false,'a started shoot never gains a free retake');
});
