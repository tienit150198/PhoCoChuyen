import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';

const noop=()=>{};
function load(file,deps){const src=readFileSync(new URL('../public/js/v4/'+file,import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'').replace(/export /g,'');return new Function(...Object.keys(deps),src+'\nreturn '+(file==='fair-crowd.js'?'crowd':'setup')+';')(...Object.values(deps));}
function env(){
 const keys=['document','performance','requestAnimationFrame','cancelAnimationFrame','setTimeout','clearTimeout','ResizeObserver','matchMedia'],old=Object.fromEntries(keys.map(k=>[k,globalThis[k]]));
 let now=1000,id=0,reduced=false;const raf=new Map(),timers=new Map(),events=new Map(),fonts=new Map(),stats={text:0,measure:0,gradient:0,draw:0};
 const ctx=()=>new Proxy({measureText:s=>{stats.measure++;return {width:s.length*6};},fillText:()=>stats.text++,drawImage:()=>stats.draw++,getTransform:()=>({a:2}),createRadialGradient:()=>{stats.gradient++;return {addColorStop:noop};},createLinearGradient:()=>({addColorStop:noop})},{get:(t,k)=>k in t?t[k]:noop,set:(t,k,v)=>(t[k]=v,true)});
 const canvas=()=>({width:600,height:720,isConnected:true,_s:2,getContext:()=>ctx(),getBoundingClientRect:()=>({width:300}),addEventListener:noop});
 globalThis.document={hidden:false,documentElement:{dataset:{},classList:{contains:()=>reduced}},body:{classList:{contains:()=>false}},createElement:()=>canvas(),addEventListener:(k,f)=>events.set(k,f),fonts:{addEventListener:(k,f)=>fonts.set(k,f)}};
 globalThis.performance={now:()=>now};globalThis.requestAnimationFrame=f=>{raf.set(++id,f);return id;};globalThis.cancelAnimationFrame=i=>raf.delete(i);
 globalThis.setTimeout=(f,ms)=>{timers.set(++id,{f,ms});return id;};globalThis.clearTimeout=i=>timers.delete(i);
 globalThis.ResizeObserver=class{observe(){}};globalThis.matchMedia=()=>({matches:reduced,addEventListener:noop});
 return {raf,timers,events,fonts,stats,ctx,canvas,frame(ms=16){now+=ms;const tasks=[...raf.values()];raf.clear();tasks.forEach(f=>f(now));},timer(){const [i,t]=timers.entries().next().value;timers.delete(i);now+=t.ms;t.f();},reduce(v){reduced=v;},restore(){Object.assign(globalThis,old);}};
}
test('knife preview and active aiming retain every display frame and exact tap times',()=>{
 const h=env();try{
  const setup=load('fair-knife.js',{}),cv=h.canvas(),S={tab:'dt',dlg:{open:true,querySelector:()=>cv}};
  const k={fly:80,gap:10,impact:90,min_tap:120,level_ms:60000,run:null};
  const ui=setup({S,F:()=>({knife:k,now:1}),serverNow:()=>1000,reduce:()=>false,render:noop,sfx:noop,pick:a=>a[0]});
  ui.mount();h.frame();assert.equal(h.raf.size,1,'rotating preview should follow the next display frame');assert.equal(h.timers.size,0);
  const gradients=h.stats.gradient;h.frame();assert.equal(h.stats.gradient,gradients,'unchanged canvas background uses cached pixels');
  k.run={stage:'play',id:'level1',lv:1,el:0,tp:[],board:{need:8,pre:[],th0:0,segs:[[60000,60,0]]}};
  ui.start();assert.equal(h.raf.size,1,'starting a real level never duplicates a scheduled frame');h.frame();assert.equal(h.raf.size,1,'active aiming keeps full frame rate');
  const before=globalThis.__fairKnife.clock();h.frame(144);ui.click('knthrow',{});
  assert.equal(S.kn.L.taps[0],Math.round(before+144),'tap timestamp follows elapsed time, not drawn frame count');
  document.hidden=true;h.frame();assert.equal(h.raf.size+S.kn.timer,0,'hidden board has no animation work');
  document.hidden=false;h.events.get('visibilitychange')();assert.equal(h.raf.size,1,'visible active board resumes');
  ui.stop();assert.equal(h.raf.size,0);
 }finally{h.restore();}
});
test('knife result rotation stops in reduced motion and while hidden or closed',()=>{
 const h=env();try{
  const setup=load('fair-knife.js',{}),cv=h.canvas(),S={tab:'dt',dlg:{open:true,querySelector:()=>cv}};
  const k={fly:80,gap:10,impact:90,min_tap:120,level_ms:60000,run:null};
  const ui=setup({S,F:()=>({knife:k,now:1}),serverNow:()=>1000,reduce:()=>document.documentElement.classList.contains('reduce-motion'),render:noop,sfx:noop,pick:a=>a[0]});
  S.kn.rest=[30,150,270];ui.mount();h.frame();assert.equal(h.raf.size,1,'result board rotates at display cadence');
  h.reduce(true);h.frame();assert.equal(h.raf.size+h.timers.size,0,'reduced motion draws the result once and stops');
  h.reduce(false);ui.start();document.hidden=true;h.events.get('visibilitychange')();assert.equal(h.raf.size+h.timers.size,0,'hiding cancels result animation');
  document.hidden=false;h.events.get('visibilitychange')();h.frame();assert.equal(h.raf.size,1,'visible result resumes smoothly');
  S.dlg.open=false;const paints=h.stats.draw;h.frame();assert.equal(h.raf.size+h.timers.size,0,'closed result has no scheduled work');assert.equal(h.stats.draw,paints,'closed result is not painted');
 }finally{h.restore();}
});
test('fair walk sleeps while idle, stops in reduced motion, and wakes immediately for movement',()=>{
 const h=env();try{
  let redraw;const slot={},crowd={busy:()=>false,items:()=>[],tags:noop,join:noop,walk:noop,leave:noop,me:()=>null,coride:()=>false};
  const p={floor:[0,0,1000,1000],spots:[],has:{}};
  let avatarPaints=0,propPaints=0,onDraw=noop;
  const deps={VIEW:{port:[0,0,1000,1000],land:[0,0,1000,1000]},plan:()=>p,route:(p,a,b)=>[a,b],nearestFree:(p,a)=>a,paintBack:noop,props:(c,p,o)=>{onDraw();return [[1,()=>o.bitmap?o.bitmap('fixture',[0,0,100,100],()=>propPaints++):propPaints++]];},marks:noop,STALLS:{},figure:()=>({}),figureOf:noop,paintPlayer:()=>avatarPaints++,CANVAS:{},lookOf:s=>s.look||{},tr:s=>s,crowd:args=>(redraw=args.redraw,crowd),choice:()=>null,nextRide:noop,canRide:()=>false,rideLabel:noop,speedOf:()=>1,drawRide:noop,rider:()=>({turn:1}),steer:noop,halfOf:noop,topOf:noop,wire:noop,spouseOf:noop,loadSpouse:()=>Promise.resolve()};
  const S={env:{api:{state:{journey:{}},content:{}}},dlg:{open:true,querySelector:()=>slot,addEventListener:noop}},ui=load('fair-walk.js',deps)({S,F:()=>({open:true}),go:noop,list:noop,bar:noop,esc:s=>s});
  Object.assign(S.walk,{ok:true,el:{isConnected:true,parentNode:slot},cv:h.canvas(),c:h.ctx(),cw:300,ch:400,me:{x:400,y:500,path:null,step:0}});
  ui.mount();h.frame();assert.equal(h.raf.size,0,'idle fair does not wake on every display frame');assert.equal(h.timers.size,1);
  assert.equal(avatarPaints,1);h.timer();h.frame();assert.equal(avatarPaints,1,'unchanged own avatar reuses cached pixels');assert.equal(propPaints,1,'static floor pixels reused between frames');
  S.env.api.state.look={shirt:'new'};redraw();h.frame();assert.equal(avatarPaints,2,'changed own look invalidates avatar');
  S.walk.dpr=2;redraw();h.frame();assert.equal(avatarPaints,3,'canvas density invalidates avatar');
  S.walk.k=1.5;redraw();h.frame();assert.equal(avatarPaints,4,'scene scale invalidates avatar');
  onDraw=()=>{onDraw=noop;redraw();};redraw();h.frame();assert.equal(h.raf.size+h.timers.size,1,'a redraw during a frame cannot leave two scheduled callbacks');h.frame();
  h.reduce(true);h.timer();h.frame();assert.equal(h.raf.size+h.timers.size,0,'reduced motion stops after one unchanged frame');
  redraw();assert.equal(h.raf.size,1,'new crowd presence wakes a reduced-motion scene');h.frame();
  h.reduce(false);globalThis.__fairWalk.walk(.7,.5);assert.equal(h.raf.size,1,'input wakes without waiting for ambient timer');h.frame();assert.equal(h.raf.size,1,'movement draws at display rate');
  ui.off();assert.equal(h.raf.size+h.timers.size,0,'closing cancels both timer and animation frame');
 }finally{h.restore();}
});
test('crowd nameplates cache bounded per person and invalidate badge, pixel ratio, font and replaced identity',()=>{
 const h=env();try{
  const handlers=new Map(),live={flags:{fair:true},state:'open',on:(k,f)=>handlers.set(k,f),send:()=>true};
  const crowd=load('fair-crowd.js',{live,lookOf:()=>({}),figureOf:()=>({}),paintPlayer:noop,CANVAS:{},fromWire:()=>null,drawRide:noop,rider:()=>({turn:1}),steer:noop,halfOf:noop,topOf:noop});
  const c=crowd({state:()=>({}),redraw:noop,still:()=>true}),ctx=h.ctx(),pid='aaaaaaaaaaaaaaaa';
  c.join([.5,.5]);const room=name=>handlers.get('fair_room')({room:'r',me:'bbbbbbbbbbbbbbbb',people:[{pid,name,x:.5,y:.5}]});room('Lan');
  const draw=(dpr=2,fallback='Khách')=>{c.items(ctx,{xy:(x,y)=>[x*100,y*100],scale:()=>1,px:1,t:0});c.tags(ctx,{sx:x=>x,sy:y=>y,fallback,badge:s=>s==='dt'?'🗡️':'',dpr});};
  draw();const warm=h.stats.text;draw();assert.equal(h.stats.text,warm,'unchanged nameplates should reuse pixels');
  handlers.get('fair')({ev:[{k:'mv',pid,p:[[.5,.5]],ms:0,s:'dt'}]});draw();assert.ok(h.stats.text>warm,'new stall badge invalidates nameplate');
  let count=h.stats.text;draw(1);assert.ok(h.stats.text>count,'pixel ratio invalidates cache');count=h.stats.text;
  h.fonts.get('loadingdone')();draw(1);assert.ok(h.stats.text>count,'font readiness invalidates cache');count=h.stats.text;
  room('');draw(1,'Người mới');assert.ok(h.stats.text>count,'replacement anonymous identity uses current fallback');count=h.stats.text;draw(1,'Tên khác');assert.ok(h.stats.text>count);
  c.leave();count=h.stats.text;draw();assert.equal(h.stats.text,count,'leaving removes cached people and labels');
 }finally{h.restore();}
});

