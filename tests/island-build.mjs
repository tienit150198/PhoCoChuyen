// 🏗️ Xây trên đảo on both interfaces: the plots of every island map (public/js/island-layout.js), what stands on them
// (withBuilds: houses and sites block the way, finished buildings are spots), walking around them (findPath), the old
// interface's drawings (v4/island-build-art.js through v4/island-walk.js), the new interface's (client/isometric/
// island-builds.ts through private-island.ts, bundled with a fake Phaser), and the scene controller: the owner taps a
// plot to build, a leisure building asks for its tinh thần, a home's door opens its inside, a site becomes a building.
import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {build} from 'esbuild';
import * as I from '../public/js/island-layout.js';
import {landing,createIslandSession} from '../public/js/v4/island-scene.js';

const KINDS=Object.keys(I.BUILD_ART);
const SPOT_RE=/^[a-z_]{1,16}$/;   // live/island.py
const NOW=2e9;
const all=(L,kind,lv=3,extra={})=>L.plots.map((p,i)=>({p:i,k:p[2]&&kind!=='ben_thuyen'?kind:kind,l:lv,b:0,t:0,...extra}));

test('each island has its plots inside the land, apart, a marina plot on the coast, and plot spot ids the live room accepts', () => {
  const want={dua:6,san_ho:10,may_da:16,hoang_hon:24};
  for(const id of I.LOOK_IDS){
    const L=I.LOOKS[id];assert.equal(L.plots.length,want[id],id);assert.ok(L.plots.some(p=>p[2]),`${id}: a coast plot`);
    for(const [x,y] of L.plots){assert.ok(I.walkable(L,x,y),`${id}: plot ${x},${y} on land`);}
    for(let i=0;i<24;i++)assert.match(I.plotSpot(i),SPOT_RE);
    assert.equal(I.plotAt(L,L.plots[3][0]+.01,L.plots[3][1]-.01),3);assert.equal(I.plotAt(L,.01,.01),-1);
  }
});

test('what stands on the plots: levels in time, blocks, spots, the marina pier; unknown kinds are skipped', () => {
  const L=I.layout('san_ho');
  const rows=[{p:0,k:'nha_san',l:2,b:0,t:0},{p:1,k:'ho_boi',l:0,b:1,t:NOW+3600},{p:2,k:'ho_boi',l:1,b:2,t:NOW-5},{p:9,k:'ben_thuyen',l:1,b:0,t:0},{p:3,k:'thap_moi',l:1,b:0,t:0}];
  const B=I.withBuilds(L,rows,NOW);
  assert.deepEqual(B.built.map(b=>[b.plot,b.kind,b.level,b.work]),[[0,'nha_san',2,false],[1,'ho_boi',0,true],[2,'ho_boi',2,false],[9,'ben_thuyen',1,false]]);
  const [hx,hy]=L.plots[0],[sx,sy]=L.plots[1],[px,py]=L.plots[2];
  assert.ok(!I.walkable(B,hx,hy)&&!I.walkable(B,sx,sy),'a house and a site are in the way');
  assert.ok(I.walkable(B,px,py),'a pool is not');
  const spots=B.spots.filter(s=>s.build);
  assert.deepEqual(spots.map(s=>s.id),['b_a','b_c','b_j']);
  assert.equal(spots[0].home,true);assert.equal(spots[1].pose,'swim');
  for(const s of spots)assert.ok(I.walkable(B,...I.standAt(B,s)),s.id);
  const pier=B.built.find(b=>b.kind==='ben_thuyen').pier;assert.ok(pier&&I.walkable(B,pier.rect.x,pier.rect.y),'the pier is walkable');
  assert.equal(I.levelAt(rows[1],NOW+3600),1);assert.equal(I.workAt(rows[1],NOW+3600),false);
  assert.equal(I.withBuilds(L,[],NOW).spots.length,L.spots.length);
});

test('a full island of houses: every door and every old spot can still be reached from the pier', () => {
  for(const id of I.LOOK_IDS){
    const L=I.layout(id),B=I.withBuilds(L,all(L,'biet_thu'),NOW),start=landing(B,'boat');
    for(const s of B.spots){const [x,y]=I.standAt(B,s),path=I.findPath(B,start,[x,y]);
      assert.ok(path.length,`${id}: ${s.id} reachable`);const end=path.at(-1);assert.ok(Math.hypot(end[0]-x,end[1]-y)<.02,`${id}: ${s.id} reached`);
      let [ax,ay]=start;for(const [bx,by] of path){assert.ok(I.clearWay(B,ax,ay,bx,by),`${id}: ${s.id} straight legs`);[ax,ay]=[bx,by];}}
  }
});

/* ---- the old interface ---- */
function fakeCanvas(w=375,h=560){
  const calls=[],ctx=new Proxy({},{get:(t,k)=>k in t?t[k]:(...a)=>{calls.push(k);},set:(t,k,v)=>{t[k]=v;return true;}});
  return {canvas:{width:0,height:0,getContext:()=>ctx,getBoundingClientRect:()=>({left:0,top:0,width:w,height:h}),parentElement:null},calls};
}
test('the old interface draws every kind at every level, sites and empty plots', async () => {
  globalThis.document??={createElement:()=>fakeCanvas(110,160).canvas};
  globalThis.performance??={now:()=>0};
  const {createWalkRenderer}=await import('../public/js/v4/island-walk.js');
  for(const id of I.LOOK_IDS){
    const L=I.layout(id),{canvas,calls}=fakeCanvas(),r=createWalkRenderer(canvas,L);
    for(const lv of [1,2,3]){
      const rows=L.plots.map((p,i)=>({p:i,k:p[2]?'ben_thuyen':KINDS[i%KINDS.length]==='ben_thuyen'?'golf':KINDS[i%KINDS.length],l:lv,b:i%5===0&&lv<3?lv+1:0,t:i%5===0&&lv<3?NOW+60:0}));
      r.setBuilds(I.withBuilds(L,rows,NOW).built);calls.length=0;
      r.frame({people:[],vehicle:null,focus:[.5,.6]},1000);
      assert.ok(calls.includes('fillRect')&&calls.includes('fill'),`${id} level ${lv}`);
    }
    r.setBuilds(I.withBuilds(L,[{p:0,k:'lau_dai',l:0,b:1,t:NOW+60}],NOW).built);r.frame({people:[],vehicle:null},1000);
    r.setBuilds([]);r.frame({people:[],vehicle:null},1000);r.destroy();
  }
});

/* ---- the new interface, with a chainable fake Phaser ---- */
function chain(){const f=function(){};const p=new Proxy(f,{get:(t,k)=>k in t?t[k]:k===Symbol.toPrimitive?()=>0:p,apply:()=>p,set:(t,k,v)=>{t[k]=v;return true;}});return p;}
test('the new interface paints the plots and repaints only when something changed', async () => {
  let made=0;
  const camera={scrollX:0,scrollY:0,width:375,height:560,zoom:1,setSize(){},setZoom(){},centerOn(){},getWorldPoint:(x,y)=>({x,y})};
  const graphics=()=>{made++;return chain();};
  const scene={cameras:{main:camera},time:{now:0},tweens:{add(){}},textures:{exists:()=>false,create:()=>chain()},
    add:{graphics,ellipse:()=>chain(),text:()=>chain(),container:()=>chain(),image:()=>chain()}};
  globalThis.__islandPhaser={CANVAS:1,Scale:{NONE:0,NO_CENTER:0},Textures:{FilterMode:{LINEAR:1}},Geom:{Point:class{constructor(x,y){this.x=x;this.y=y;}}},
    Game:class{constructor(cfg){this.scale={width:375,height:560,resize(){}};cfg.scene.create.call(scene);}destroy(){}}};
  globalThis.__islandStamp=()=>({canvas:{width:120,height:160}});
  const out=await build({stdin:{contents:readFileSync('client/isometric/private-island.ts','utf8'),loader:'ts',resolveDir:resolve('client/isometric')},bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent',plugins:[{
    name:'island-fakes',setup(b){
      b.onResolve({filter:/^(phaser|\/js\/)/},a=>({path:a.path,namespace:'island-fake'}));
      b.onLoad({filter:/.*/,namespace:'island-fake'},a=>({contents:a.path==='phaser'?'export default globalThis.__islandPhaser;':'export const getCharacterStamp=(...a)=>globalThis.__islandStamp(...a);',loader:'js'}));
    }}]});
  const {PrivateIslandRenderer}=await import('data:text/javascript;base64,'+Buffer.from(out.outputFiles[0].text).toString('base64'));
  const canvas={getBoundingClientRect:()=>({left:0,top:0,width:375,height:560}),parentElement:null};
  for(const id of I.LOOK_IDS){
    const L=I.layout(id),r=new PrivateIslandRenderer(canvas,L);await r.ready;
    for(const lv of [1,2,3]){
      const rows=L.plots.map((p,i)=>({p:i,k:p[2]?'ben_thuyen':KINDS[i%KINDS.length]==='ben_thuyen'?'cam_trai':KINDS[i%KINDS.length],l:lv,b:i%4===0&&lv<3?lv+1:0,t:i%4===0&&lv<3?NOW+60:0}));
      const built=I.withBuilds(L,rows,NOW).built,before=made;r.setBuilds(built);assert.ok(made>before,`${id} level ${lv} painted`);
      const again=made;r.setBuilds(I.withBuilds(L,rows,NOW).built);assert.equal(made,again,`${id}: the same list is not painted again`);
    }
    r.destroy();
  }
});

/* ---- the controller ---- */
function harness(builds,{mine=true}={}){
  const calls=[],api=new EventTarget();
  api.state={journey:{story:true,gender:'female'},wardrobe:{look:{}}};
  const env={api,world:{paused:false,wake(){}},closeSheet(){},toast:t=>calls.push(['toast',t])};
  let clock=0,wall=NOW,tick=null;const sets=[];
  const renderer={frame(){},toMap:(x,y)=>[x/1000,y/1000],toScreen:(x,y)=>[x*1000,y*1000],personHeight:80,destroy(){},setBuilds:b=>sets.push(b)};
  const view={open(){},ready(){},status:s=>calls.push(['status',s]),notice:s=>calls.push(['notice',s]),tags(){},signs:l=>calls.push(['signs',l.length]),spots:l=>calls.push(['spots',l.length]),
    inside:i=>calls.push(['inside',i]),destroy(){},onClose(fn){this.close=fn;},onTap(fn){this.tap=fn;},onKey(fn){this.key=fn;},onSpot(fn){this.spot=fn;},onEmote(){},onSay(){},onEnd(){},onBuild(fn){this.build=fn;}};
  const on=new Map(),live={sent:[],on(t,fn){(on.get(t)||on.set(t,new Set()).get(t)).add(fn);return ()=>on.get(t).delete(fn);},send(f){this.sent.push(f);return true;},
    emit(t,f){for(const fn of on.get(t)||[])fn({t,...f});}};
  const trip={id:'abcd1234abcd1234',island:{id:'dao_san_ho',name:'Đảo San Hô',emoji:'🌺',look:'san_ho'},vehicle:null,kind:'solo',seats:1,aboard:1,ends:NOW+1e8,unlimited:true,mine,builds,owner:{name:'Lan'}};
  const actions={build:p=>calls.push(['build',p]),use:async p=>{calls.push(['use',p]);return 'Tinh thần +1.';},reload:async()=>null};
  const session=createIslandSession(env,{trip,view,actions,loadRenderer:async()=>renderer,loadLive:async()=>live,clock:()=>clock,wall:()=>wall,raf:fn=>{tick=fn;return 1;},caf(){}});
  return {session,calls,view,live,sets,run(ms){const n=Math.ceil(ms/16);for(let i=0;i<n&&tick;i++){clock+=16;tick(clock);}},setWall(v){wall=v;}};
}
test('on the island: the owner taps a plot to build, a pool gives its tinh thần, a home opens inside, a site becomes a building', async () => {
  const L=I.layout('san_ho');
  const rows=[{p:0,k:'biet_thu',l:2,b:0,t:0},{p:1,k:'ho_boi',l:1,b:0,t:0},{p:6,k:'cam_trai',l:0,b:1,t:NOW+120}];
  const h=harness(rows);await h.session.start();h.live.emit('isl_room',{room:'isl:x',trip:'abcd1234abcd1234',me:'pme',owner:'pme',people:[]});h.run(3000);
  assert.equal(h.sets[0].length,3);assert.ok(h.calls.some(c=>c[0]==='spots'));
  // the owner taps an empty plot: the build sheet for it
  const [ex,ey]=L.plots[4];h.view.tap(ex*1000,ey*1000);assert.deepEqual(h.calls.at(-1),['build',4]);
  h.view.build();assert.deepEqual(h.calls.at(-1),['build',-1]);
  // the pool: walk there, the others see it, the tinh thần is asked for
  h.view.spot('b_b');h.run(9000);
  assert.ok(h.live.sent.some(f=>f.t==='isl_do'&&f.s==='b_b'));assert.equal(h.session.me.pose,'swim');
  await new Promise(r=>setTimeout(r,0));assert.ok(h.calls.some(c=>c[0]==='use'&&c[1]===1));
  assert.ok(h.calls.some(c=>c[0]==='notice'&&/Tinh thần \+1/.test(c[1])));
  // the villa's door: inside
  h.view.spot('b_a');h.run(9000);
  const inside=h.calls.find(c=>c[0]==='inside');assert.ok(inside,'the inside opened');assert.equal(inside[1].kind,'biet_thu');assert.equal(inside[1].level,2);
  // the campsite's hour is over: it stands, the map is painted again, its spot appears
  assert.ok(h.calls.some(c=>c[0]==='signs'&&c[1]===1));
  h.setWall(NOW+121);h.run(1200);
  const last=h.sets.at(-1);assert.equal(last.find(b=>b.plot===6).work,false);assert.ok(h.session.layout.spots.some(s=>s.id==='b_g'));
  h.view.close();
});
test('a visitor never builds: taps on plots just walk', async () => {
  const L=I.layout('san_ho');const h=harness([],{mine:false});await h.session.start();h.run(3000);
  const [ex,ey]=L.plots[4];h.view.tap(ex*1000,ey*1000);assert.ok(!h.calls.some(c=>c[0]==='build'));
  h.view.close();
});
