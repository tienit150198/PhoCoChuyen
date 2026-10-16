// 🏝️ Đảo riêng on both interfaces: the island maps (public/js/island-layout.js), the old interface's 2D walk
// (v4/island-walk.js), the new interface's Phaser scene (client/isometric/private-island.ts, bundled with a fake
// Phaser), the shared controller (v4/island-scene.js) with a fake live socket, and the live room client (v4/island-live.js).
import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {build} from 'esbuild';
import * as I from '../public/js/island-layout.js';
import {vehicleRoute,vehicleAt,landing,facing,createIslandSession} from '../public/js/v4/island-scene.js';
import {createIslandPresence,peerAt} from '../public/js/v4/island-live.js';
import {townUtilityGroups,townServiceAvailable} from '../public/js/isometric/town-utilities.js';

const ISLANDS=readFileSync('game/island_content.py','utf8');

test('every island id in game/island_content.py has a map, and every map is one connected walk', () => {
  for(const look of [...ISLANDS.matchAll(/look='([a-z_]+)'/g)].map(m=>m[1]))assert.ok(I.LOOK_IDS.includes(look),look);
  for(const id of I.LOOK_IDS){
    const L=I.LOOKS[id],N=100,seen=new Set(),q=[];
    const start=landing(L,'boat'),s=[Math.round(start[0]*N),Math.round(start[1]*N)];
    assert.ok(I.walkable(L,...start),`${id}: the pier end is walkable`);
    q.push(s);seen.add(s.join());
    while(q.length){const [x,y]=q.shift();for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){const nx=x+dx,ny=y+dy,k=nx+','+ny;if(!seen.has(k)&&I.walkable(L,nx/N,ny/N)){seen.add(k);q.push([nx,ny]);}}}
    const reach=([x,y])=>seen.has(Math.round(x*N)+','+Math.round(y*N));
    for(const kind of ['heli','plane','solo','boat'])assert.ok(reach(landing(L,kind)),`${id}: ${kind} lands where you can walk`);
    assert.ok(reach(I.centre(L)),`${id}: the middle`);
    for(const sp of L.spots){assert.ok(reach(I.standAt(L,sp)),`${id}: ${sp.id}`);assert.ok(sp.lines.length&&sp.name&&sp.emoji);}
    for(const [x,y] of L.palms)assert.ok(I.inPoly(L.shore,x,y),`${id}: palm in the sea`);
    assert.ok(!I.walkable(L,L.villa.x,L.villa.y),`${id}: nobody walks through the villa`);
    assert.ok(!I.walkable(L,.01,.01)&&!I.walkable(L,.99,.99),`${id}: the corners are sea`);
    // A boat moors in the water beside the end of the pier, a helicopter on its pad.
    const boat=vehicleRoute(L,'boat');assert.ok(!I.walkable(L,...boat.at)&&Math.abs(boat.at[0]-L.dock.x)<.1,`${id}: boat beside the pier`);
    assert.deepEqual(vehicleRoute(L,'heli').at,[L.pad.x,L.pad.y]);
    const arrive=vehicleAt(boat,0),moored=vehicleAt(boat,1);assert.notDeepEqual([arrive.x,arrive.y],[moored.x,moored.y]);assert.deepEqual([moored.x,moored.y],boat.at);
    assert.equal(vehicleAt(vehicleRoute(L,'heli'),0).lift,260);assert.equal(vehicleAt(vehicleRoute(L,'heli'),1).lift,0);
  }
});

test('walking slides along a wall and never leaves the island', () => {
  const L=I.layout('dua');let [x,y]=landing(L,'boat');
  for(let i=0;i<400;i++){[x,y]=I.step(L,x,y,.5,-1,.01);assert.ok(I.walkable(L,x,y));}
  assert.ok(y<.9);
  assert.deepEqual(facing(1,0),'se');assert.deepEqual(facing(0,1),'sw');assert.deepEqual(facing(-1,0),'nw');assert.deepEqual(facing(0,-1),'ne');assert.equal(facing(0,0,'ne'),'ne');
});

/* ---- the old interface: a 2D canvas, every call recorded ---- */
function fakeCanvas(w=375,h=560){
  const calls=[],ctx=new Proxy({},{get:(t,k)=>k in t?t[k]:(...a)=>{calls.push(k);},set:(t,k,v)=>{t[k]=v;return true;}});
  const canvas={width:0,height:0,getContext:()=>ctx,getBoundingClientRect:()=>({left:10,top:20,width:w,height:h}),parentElement:null};
  return {canvas,calls};
}
test('the old interface draws each island, the people and the boat, and maps taps back to the island', async () => {
  globalThis.document??={createElement:()=>fakeCanvas(110,160).canvas};
  globalThis.performance??={now:()=>0};
  const {createWalkRenderer}=await import('../public/js/v4/island-walk.js');
  for(const id of I.LOOK_IDS){
    const L=I.layout(id),{canvas,calls}=fakeCanvas(),r=createWalkRenderer(canvas,L);
    await r.ready;
    const me={id:'me',x:.5,y:.7,look:{},gender:'female',dir:'se',walking:true,left:true},swim={id:'b',x:.4,y:.6,look:{},gender:'male',dir:'sw',walking:false,pose:'swim'};
    r.frame({people:[me,swim],vehicle:vehicleAt(vehicleRoute(L,'heli'),.5),focus:[.5,.7]},1000);
    assert.ok(calls.includes('fill')&&calls.includes('drawImage'),id);
    const [sx,sy]=r.toScreen(.42,.63),[mx,my]=r.toMap(sx+10,sy+20);
    assert.ok(Math.abs(mx-.42)<1e-9&&Math.abs(my-.63)<1e-9,`${id}: tap → map`);
    assert.ok(r.personHeight>30);r.destroy();
  }
});

/* ---- the new interface: the Phaser scene with a chainable fake Phaser ---- */
function chain(){const f=function(){};const p=new Proxy(f,{get:(t,k)=>k in t?t[k]:k===Symbol.toPrimitive?()=>0:p,apply:()=>p,set:(t,k,v)=>{t[k]=v;return true;}});return p;}
test('the new interface renders an island with Phaser: people sorted by depth, taps and overlays line up', async () => {
  const images=[],textures=new Set();
  const camera={scrollX:0,scrollY:0,width:375,height:560,zoom:1,setSize(w,h){this.width=w;this.height=h;},setZoom(z){this.zoom=z;},
    centerOn(x,y){this.scrollX=x-this.width/2;this.scrollY=y-this.height/2;},
    getWorldPoint(x,y){return {x:(x-this.width/2)/this.zoom+this.width/2+this.scrollX,y:(y-this.height/2)/this.zoom+this.height/2+this.scrollY};}};
  const image=()=>{const o={x:0,y:0,depth:0,visible:true,crop:null,setOrigin(){return o;},setScale(){return o;},setTexture(k){o.key=k;return o;},setVisible(v){o.visible=v;return o;},
    setPosition(x,y){o.x=x;o.y=y;return o;},setDepth(d){o.depth=d;return o;},setCrop(...a){o.crop=a.length?a:null;return o;},destroy(){o.gone=true;}};images.push(o);return o;};
  const scene={cameras:{main:camera},time:{now:0},tweens:{add(){}},
    textures:{exists:k=>textures.has(k),create:k=>{textures.add(k);return chain();}},
    add:{graphics:()=>chain(),ellipse:()=>chain(),text:()=>chain(),container:()=>{const c=chain();c.getData=k=>c['_'+k];c.setData=(k,v)=>{c['_'+k]=v;return c;};return c;},image:(x,y,k)=>image().setTexture(k)}};
  globalThis.__islandPhaser={CANVAS:1,Scale:{NONE:0,NO_CENTER:0},Textures:{FilterMode:{LINEAR:1}},Geom:{Point:class{constructor(x,y){this.x=x;this.y=y;}}},
    Game:class{constructor(cfg){this.cfg=cfg;this.scale={width:375,height:560,resize(){}};cfg.scene.create.call(scene);}destroy(){this.destroyed=true;}}};
  globalThis.__islandStamp=()=>({canvas:{width:120,height:160}});
  const out=await build({stdin:{contents:readFileSync('client/isometric/private-island.ts','utf8'),loader:'ts',resolveDir:resolve('client/isometric')},bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent',plugins:[{
    name:'island-fakes',setup(b){
      b.onResolve({filter:/^(phaser|\/js\/)/},a=>({path:a.path,namespace:'island-fake'}));
      b.onLoad({filter:/.*/,namespace:'island-fake'},a=>({contents:a.path==='phaser'?'export default globalThis.__islandPhaser;':'export const getCharacterStamp=(...a)=>globalThis.__islandStamp(...a);',loader:'js'}));
    }}]});
  const {PrivateIslandRenderer}=await import('data:text/javascript;base64,'+Buffer.from(out.outputFiles[0].text).toString('base64'));
  const canvas={getBoundingClientRect:()=>({left:0,top:0,width:375,height:560}),parentElement:null};
  for(const id of I.LOOK_IDS){
    images.length=0;
    const L=I.layout(id),r=new PrivateIslandRenderer(canvas,L);await r.ready;
    r.frame({people:[{id:'me',x:.5,y:.7,look:{},gender:'female',dir:'se',walking:false},{id:'p',x:.3,y:.4,look:{},gender:'male',dir:'ne',walking:true,pose:'swim'}],vehicle:vehicleAt(vehicleRoute(L,'plane'),.3),focus:[.5,.7]});
    r.tick(100);
    const [me,peer]=images;assert.ok(me&&peer,id);
    assert.ok(me.depth>peer.depth,`${id}: the one further south is drawn in front`);
    assert.ok(peer.crop&&!me.crop,`${id}: a swimmer shows only above the water`);
    const at=r.toScreen(.42,.63),back=r.toMap(at[0],at[1]);
    assert.ok(Math.abs(back[0]-.42)<1e-9&&Math.abs(back[1]-.63)<1e-9,`${id}: overlay and tap agree`);
    r.frame({people:[{id:'me',x:.5,y:.7,look:{},gender:'female',dir:'se',walking:false}],vehicle:null});r.tick(200);
    assert.ok(peer.gone,`${id}: someone who left is removed`);
    r.destroy();
  }
});

/* ---- the controller and the live room, with a fake socket ---- */
function fakeLive(){
  const on=new Map(),sent=[];
  return {sent,state:'open',on(t,fn){(on.get(t)||on.set(t,new Set()).get(t)).add(fn);return ()=>on.get(t).delete(fn);},send(f){sent.push(f);return true;},
    emit(t,f){for(const fn of on.get(t)||[])fn({t,...f});},count:t=>(on.get(t)||new Set()).size};
}
function harness({kind='boat',ends=1e9}={}){
  const calls=[],api=new EventTarget();
  api.state={journey:{story:true,gender:'female'},wardrobe:{look:{}}};
  const env={api,world:{paused:false,wake:()=>calls.push('wake')},closeSheet:()=>calls.push('closeSheet'),toast:t=>calls.push(['toast',t])};
  const frames=[],tags=[];let clock=0,wall=1000,tick=null;
  const renderer={frame:m=>frames.push(m),toMap:(x,y)=>[x/1000,y/1000],toScreen:(x,y)=>[x*1000,y*1000],personHeight:80,destroy:()=>calls.push('renderer.destroy')};
  const view={open:(L,t)=>calls.push(['open',L.name,t.id]),ready:()=>calls.push('ready'),status:s=>calls.push(['status',s]),notice:s=>calls.push(['notice',s]),tags:l=>tags.push(l),
    destroy:()=>calls.push('view.destroy'),onClose(fn){this.close=fn;},onTap(fn){this.tap=fn;},onKey(fn){this.key=fn;},onSpot(fn){this.spot=fn;},onEmote(fn){this.emote=fn;},onSay(fn){this.say=fn;},onEnd(fn){this.end=fn;}};
  const live=fakeLive(),trip={id:'abcd1234abcd1234',island:{id:'dao_dua',name:'Đảo Dừa',emoji:'🏝️',look:'dua'},vehicle:{id:'du_thuyen',name:'Du thuyền',emoji:'🛥️'},kind,seats:8,aboard:2,ends,mine:true};
  const closed=[],session=createIslandSession(env,{trip,view,loadRenderer:async()=>renderer,loadLive:async()=>live,clock:()=>clock,wall:()=>wall,
    raf:fn=>{tick=fn;return 1;},caf:()=>{tick=null;},actions:{end:async()=>calls.push('end')},onClose:w=>closed.push(w)});
  return {session,calls,env,view,live,trip,frames,tags,closed,run(ms){const n=Math.ceil(ms/16);for(let i=0;i<n&&tick;i++){clock+=16;tick(clock);}},setWall(v){wall=v;}};
}
test('arriving, walking, the others, waves and bubbles, then going home', async () => {
  const h=harness();await h.session.start();
  assert.equal(h.env.world.paused,true);
  const join=h.live.sent.find(f=>f.t==='isl_in');assert.equal(join.trip,h.trip.id);assert.equal(join.g,'female');assert.deepEqual([join.x,join.y],landing(I.layout('dua'),'boat').map(v=>+v.toFixed(4)));
  h.run(200);assert.equal(h.frames.at(-1).people[0].hidden,true,'still on the boat');
  const boat=h.frames.at(-1).vehicle;assert.equal(boat.kind,'boat');
  h.run(2600);assert.equal(h.session.arrived,true);assert.equal(h.frames.at(-1).people[0].hidden,false);
  // The room: one friend already there.
  h.live.emit('isl_room',{room:'isl:x',trip:h.trip.id,me:'pme',owner:'pme',people:[{pid:'p2',name:'Ban Mot',lk:{},g:'male',x:.4,y:.6,o:false}]});
  h.run(20);assert.deepEqual(h.frames.at(-1).people.map(p=>p.id),['me','p2']);
  h.live.emit('isl',{room:'isl:x',ev:[{k:'mv',pid:'p2',p:[[.4,.6],[.6,.6]],ms:1000}]});
  h.run(500);const mid=h.frames.at(-1).people[1];assert.ok(mid.x>.45&&mid.x<.55&&mid.walking,'the friend walks over time');
  h.live.emit('isl',{room:'isl:x',ev:[{k:'said',pid:'p2',text:'Chào!'},{k:'emote',pid:'pme',e:'wave'},{k:'do',pid:'p2',s:'bar'}]});
  h.run(600);const people=h.frames.at(-1).people;
  assert.equal(people[1].bubble,'Chào!');assert.equal(people[0].emote,'wave');assert.equal(people[1].pose,'stand','at the bar');
  assert.ok(h.tags.at(-1).some(t=>t.id==='p2'&&t.bubble==='Chào!'));
  // A tap walks there and tells the others.
  const n=h.live.sent.length;h.view.tap(500,520);
  const mv=h.live.sent.slice(n).find(f=>f.t==='isl_mv');assert.ok(mv&&mv.ms>0,'move sent');assert.deepEqual(mv.p[1],[.5,.52]);
  h.run(4000);const me=h.session.me;assert.ok(Math.hypot(me.x-.5,me.y-.52)<.01,'walked there');
  // A spot button: walk up, then everyone sees it.
  h.view.spot('lua');h.run(5000);
  assert.ok(h.live.sent.some(f=>f.t==='isl_do'&&f.s==='lua'));assert.equal(h.session.me.pose,'sit');
  assert.ok(h.calls.some(c=>Array.isArray(c)&&c[0]==='notice'&&c[1].startsWith('🔥')));
  // Keys walk too.
  h.view.key('ArrowUp',true);h.run(400);h.view.key('ArrowUp',false);h.run(50);
  assert.ok(h.live.sent.filter(f=>f.t==='isl_mv').length>=3);
  h.view.emote('heart');assert.deepEqual(h.live.sent.at(-1),{t:'isl_emote',e:'heart'});
  assert.equal(h.view.say('Đẹp quá'),true);assert.deepEqual(h.live.sent.at(-1),{t:'isl_say',text:'Đẹp quá'});
  // ← Về phố: the scene closes, the trip goes on.
  h.view.close();assert.deepEqual(h.closed,[null]);assert.equal(h.env.world.paused,false);
  assert.deepEqual(h.live.sent.at(-1),{t:'isl_out'});assert.equal(h.live.count('isl'),0,'listeners gone');
  for(const c of ['renderer.destroy','view.destroy','wake'])assert.equal(h.calls.filter(x=>x===c).length,1,c);
});
test('the owner ends it, the hour runs out, a reconnect joins again', async () => {
  let h=harness();await h.session.start();h.live.emit('isl_room',{room:'isl:x',trip:h.trip.id,me:'pme',owner:'pme',people:[]});
  h.live.emit('isl_left',{why:'ended'});assert.deepEqual(h.closed,['ended']);
  assert.ok(h.calls.some(c=>Array.isArray(c)&&c[0]==='toast'&&/kết thúc/.test(c[1])));
  h=harness();await h.session.start();h.setWall(1e9+1);h.run(1100);assert.deepEqual(h.closed,['time']);
  h=harness();await h.session.start();h.live.emit('isl_room',{room:'isl:x',trip:h.trip.id,me:'pme',owner:'pme',people:[]});
  h.live.emit('down',{});const before=h.live.sent.filter(f=>f.t==='isl_in').length;h.live.emit('welcome',{});
  assert.equal(h.live.sent.filter(f=>f.t==='isl_in').length,before+1);
  h.live.emit('error',{code:'no_island',msg:'Bạn chưa ở trên đảo.',ref:'isl_in'});assert.deepEqual(h.closed,['gone']);
  h=harness({kind:'heli'});await h.session.start();await h.view.end();assert.ok(h.calls.includes('end'));assert.deepEqual(h.closed,['ended']);
});
test('the live client: a walker between two points, frames of another room are ignored', () => {
  assert.deepEqual(peerAt({from:[0,0],to:[1,1],t0:0,ms:100},50),[.5,.5]);assert.deepEqual(peerAt({from:[0,0],to:[1,1],t0:0,ms:100},500),[1,1]);
  const live=fakeLive(),left=[];let now=0;
  const p=createIslandPresence({live,trip:'t1',look:{},gender:null,at:()=>[.5,.5],clock:()=>now,onLeft:w=>left.push(w)}).start();
  live.emit('isl_room',{room:'r1',trip:'t2',me:'a',people:[{pid:'b',x:0,y:0}]});assert.equal(p.online,false,'another trip');
  live.emit('isl_room',{room:'r1',trip:'t1',me:'a',people:[{pid:'b',x:0,y:0}]});assert.equal(p.online,true);assert.equal(p.peers.size,1);
  live.emit('isl',{room:'r9',ev:[{k:'out',pid:'b'}]});assert.equal(p.peers.size,1,'another room');
  live.emit('isl',{room:'r1',ev:[{k:'out',pid:'b'}]});assert.equal(p.peers.size,0);
  live.emit('isl_left',{why:'out'});assert.deepEqual(left,[]);live.emit('isl_left',{why:'removed'});assert.deepEqual(left,['removed']);
  p.stop();assert.equal(live.count('isl_room'),0);
});
test('both interfaces list 🏝️ Đảo riêng only when the server has it', () => {
  const state={journey:{story:true}},content={journey:{island:{islands:[]}}};
  assert.equal(townServiceAvailable('island',state,content),true);
  assert.equal(townServiceAvailable('island',state,{journey:{}}),false);
  assert.equal(townServiceAvailable('island',{journey:{story:false}},content),false);
  assert.ok(townUtilityGroups(state,content).some(g=>g.items.some(i=>i.action==='island')));
  const app=readFileSync('public/js/app.js','utf8');
  assert.match(app,/content\?\.journey\?\.island\)items\.push\(\['island'/);
  assert.match(app,/action==='island'\|\|action==='islandInvites'/);
  assert.match(app,/live\.on\('island_ping'/);
});
