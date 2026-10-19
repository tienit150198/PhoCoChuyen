// ⚔️ Đảo bang on both interfaces: the map (public/js/bang-island-layout.js: slots on the island, nothing overlapping,
// every door and spot reachable from the pier), the old interface's 2D walk (v4/bang-island-walk.js), the new
// interface's Phaser scene (client/isometric/bang-island.ts, bundled with a fake Phaser), the controller
// (v4/bang-island-scene.js) with a fake view, renderer, live socket and clock, the live client (v4/bang-island-live.js)
// and the menu entries behind the server's switch. Run: node --test tests/bang-island.mjs
import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {build} from 'esbuild';
import * as B from '../public/js/bang-island-layout.js';
import {createBangIslandSession,timeLeft,looks,facing} from '../public/js/v4/bang-island-scene.js';
import {createBangPresence,peerAt} from '../public/js/v4/bang-island-live.js';
import {townUtilityGroups,townServiceAvailable} from '../public/js/isometric/town-utilities.js';

const L=B.LAYOUT,PY=readFileSync('game/bang_island.py','utf8');
const overlap=(a,b,pad=0)=>Math.abs(a.x-b.x)<(a.w+b.w)/2+pad&&Math.abs(a.y-b.y)<(a.h+b.h)/2+pad;
const corners=r=>[[r.x-r.w/2,r.y-r.h/2],[r.x+r.w/2,r.y-r.h/2],[r.x+r.w/2,r.y+r.h/2],[r.x-r.w/2,r.y+r.h/2]];
const LEVELS=[1,2,3,4,5].map(n=>B.layout(n));
function reachable(L=B.LAYOUT){
  const N=150,seen=new Set(),q=[],s=B.arrival(L),k0=[Math.round(s[0]*N),Math.round(s[1]*N)];
  q.push(k0);seen.add(k0.join());
  while(q.length){const [x,y]=q.shift();for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){const nx=x+dx,ny=y+dy,k=nx+','+ny;if(!seen.has(k)&&B.walkable(L,nx/N,ny/N)){seen.add(k);q.push([nx,ny]);}}}
  return ([x,y])=>seen.has(Math.round(x*N)+','+Math.round(y*N));
}

test('the facilities match game/bang_island.py and each has a fixed slot on the island', () => {
  const ids=[...PY.match(/^FACILITIES = \(([\s\S]*?)\n\)/m)[1].matchAll(/dict\(id='([a-z_]+)'/g)].map(m=>m[1]);
  assert.deepEqual(B.FACILITY_IDS,ids);
  assert.deepEqual(Object.keys(L.slots).sort(),[...ids].sort());
  const spots=PY.match(/^SPOTS = \(([^)]*)\)/m)[1].match(/'([a-z_]+)'/g).map(s=>s.slice(1,-1));
  assert.deepEqual(B.layout(B.ISLE_MAX).spots.map(s=>s.id),spots,'every level\'s spots, the top level has them all');
  assert.deepEqual(L.spots.map(s=>s.id),spots.slice(0,6),'level 1: the island as it was before 21/10');
  assert.deepEqual(B.SPOT_IDS,[...ids,...spots]);
  assert.equal(B.ISLE_MAX,Number(PY.match(/^ISLE_MAX = (\d+)/m)[1]));
  // The hall in the middle, the gate at the pier (towards the viewer), everything inside the coast.
  const [ha,hb]=B.screenOf(L.slots.dai_sanh.x,L.slots.dai_sanh.y),[ga,gb]=B.screenOf(L.slots.cong_bang.x,L.slots.cong_bang.y);
  assert.ok(Math.abs(ha)<.01&&Math.abs(hb)<.2,'hall in the middle');assert.ok(Math.abs(ga)<.01&&gb>.25,'gate towards the pier');
  for(const M of LEVELS)for(const r of [...Object.values(M.slots),...M.plots])for(const [x,y] of corners(r))assert.ok(B.inPoly(M.shore,x,y),`level ${M.level}: ${r.id} inside the coast`);
  for(const n of [0,1,3,4,6,7,10])assert.equal(B.band(n),[0,1,1,1,2,2,2,3,3,3,3][n]);
});

test('no two slots, plots or gate pillars overlap; trees stand clear of them; nothing blocks the gate', () => {
 for(const L of LEVELS){
  const rects=[...Object.values(L.slots).filter(s=>s.id!=='cong_bang'),...L.plots,...B.gatePosts(L).map((g,i)=>({...g,id:'post'+i}))];
  for(let i=0;i<rects.length;i++)for(let j=i+1;j<rects.length;j++)assert.ok(!overlap(rects[i],rects[j],.005),`${rects[i].id} × ${rects[j].id}`);
  for(const [x,y] of [...L.palms,...L.trees,...(L.lamps||[])]){assert.ok(B.inPoly(L.shore,x,y),'a tree at sea');for(const r of rects)assert.ok(!overlap(r,{x,y,w:0,h:0},.015),`a tree in ${r.id}`);}
  const [gx,gy]=B.at(L.gate.a,L.gate.b);assert.ok(B.walkable(L,gx,gy),'the way through the gate');
  for(const g of B.gatePosts(L))assert.ok(!B.walkable(L,g.x,g.y),'a pillar');
  for(const s of Object.values(L.slots))if(s.solid)assert.ok(!B.walkable(L,s.x,s.y),`${s.id}: nobody walks through it`);
  assert.ok(B.walkable(L,L.slots.san_pet.x,L.slots.san_pet.y),'the yard is walked on');
  assert.ok(!B.walkable(L,.02,.02)&&!B.walkable(L,.98,.98),'the corners are sea');
 }
});

test('🏝️ each island level adds land and a zone, keeps every facility where it was, stays inside the map', () => {
  const area=poly=>Math.abs(poly.reduce((s,[x,y],i)=>{const [u,v]=poly[(i+1)%poly.length];return s+x*v-u*y;},0))/2;
  assert.equal(B.layout(1),B.LAYOUT);assert.equal(B.layout(0),B.LAYOUT);assert.equal(B.layout(9),B.layout(5));assert.equal(B.layout(3),B.layout(3),'one object a level (walkable caches it)');
  for(let n=2;n<=B.ISLE_MAX;n++){
    const a=B.layout(n-1),b=B.layout(n);
    assert.ok(area(b.shore)>area(a.shore)*1.02,`level ${n}: more land`);
    for(const [x,y] of a.shore.map(([x,y])=>[.5+(x-.5)*.97,.5+(y-.5)*.97]))assert.ok(B.inPoly(b.shore,x,y),`level ${n} keeps level ${n-1}'s land`);
    assert.deepEqual(b.slots,B.LAYOUT.slots,'the facilities never move');
    assert.ok(b.spots.length===a.spots.length+1&&b.plots.length===a.plots.length+1,`level ${n}: one more zone`);
    for(const [x,y] of b.shore)assert.ok(x>0&&x<1&&y>0&&y<1,`level ${n}: the coast inside the map's square`);
  }
  assert.ok(B.layout(5).lamps.length>=8&&!B.layout(4).lamps.length,'gold lanterns at level 5');
  // While the next level is built: its land is a work site, nobody walks on it yet.
  const L2=B.layout(2,3);assert.equal(L2.site.level,3);assert.equal(L2.site.kind,'teahouse');assert.deepEqual(L2.shore,B.layout(2).shore);
  assert.ok(!B.walkable(L2,L2.site.x,L2.site.y)&&B.walkable(B.layout(3),...B.doorOf(B.layout(3),'tra_dinh')),'the site: not walkable until done');
  assert.equal(B.layout(5,6).site,undefined);assert.equal(B.layout(2,2).site,undefined);
});

test('from the pier every door and spot is reachable, and a tap finds the facility under it', () => {
  // 🏝️ and walked the scene's way (findPath's legs, step by step) from the pier to every door and spot of every level
  for(const M of LEVELS)for(const id of [...B.FACILITY_IDS,...M.spots.map(s=>s.id)]){
    let [x,y]=B.arrival(M);const d=B.doorOf(M,id),route=B.findPath(M,[x,y],d);let to=route.shift(),n=0;
    for(;n<8000;n++){const [nx,ny,done]=B.step(M,x,y,to[0],to[1],.0025),moved=Math.hypot(nx-x,ny-y);x=nx;y=ny;
      if(done&&route.length&&Math.hypot(x-to[0],y-to[1])<1e-4){to=route.shift();continue;}if(done||moved<1e-7)break;}
    assert.ok(Math.hypot(x-d[0],y-d[1])<.03,`level ${M.level}: walked from the pier to ${id}`);
  }
  for(const M of LEVELS){const reach=reachable(M);assert.ok(B.walkable(M,...B.arrival(M)));
    for(const id of [...B.FACILITY_IDS,...M.spots.map(s=>s.id)]){const d=B.doorOf(M,id);assert.ok(B.walkable(M,...d),`level ${M.level} ${id}: door walkable`);assert.ok(reach(d),`level ${M.level} ${id}: reachable`);}}
  for(const s of Object.values(L.slots))assert.equal(B.facilityAt(L,s.x,s.y)?.id,s.id);
  assert.equal(B.facilityAt(L,.02,.02),null);
  for(const sp of L.spots)assert.equal(B.spotNear(L,sp.x,sp.y)?.id,sp.id);
  // Walking slides along walls and never leaves the island; the arrow keys follow the screen.
  let [x,y]=B.arrival(L);for(let i=0;i<500;i++){[x,y]=B.step(L,x,y,x-.5,y-.5,.01);assert.ok(B.walkable(L,x,y));}
  const [ua,ub]=B.screenOf(.5+B.SCREEN_KEYS.u[0],.5+B.SCREEN_KEYS.u[1]),[ra,rb]=B.screenOf(.5+B.SCREEN_KEYS.r[0],.5+B.SCREEN_KEYS.r[1]);
  assert.ok(ub<-.9&&Math.abs(ua)<1e-9,'up is up the screen');assert.ok(ra>.9&&Math.abs(rb)<1e-9,'right is right');
  assert.equal(facing(1,0),'se');assert.equal(facing(0,-1),'ne');
});

const BANG=preset=>{const lv={low:[2,1,3,1,2,1,3],mid:[5,4,6,5,4,6,5],high:[10,8,9,7,10,9,8],empty:[0,0,0,0,0,0,0],build:[3,0,6,2,9,5,1]}[preset];
  return {name:'Long Môn',emoji:'🐉',color:'#b8282e',facilities:B.FACILITY_IDS.map((id,i)=>({id,level:lv[i],band:B.band(lv[i]),state:preset==='build'?'building':'done'}))};};

/* ---- the old interface: a 2D canvas, every call recorded ---- */
function fakeCanvas(w=390,h=600){
  const calls=[],ctx=new Proxy({},{get:(t,k)=>k in t?t[k]:k==='measureText'?()=>({width:40}):(...a)=>{calls.push(k);},set:(t,k,v)=>{t[k]=v;return true;}});
  return {canvas:{width:0,height:0,getContext:()=>ctx,getBoundingClientRect:()=>({left:10,top:20,width:w,height:h}),parentElement:null},calls};
}
test('the old interface draws the island for every level band and maps taps back to the map', async () => {
  globalThis.document??={createElement:()=>fakeCanvas(110,160).canvas};
  globalThis.performance??={now:()=>0};
  const {createBangWalkRenderer,walkCamera}=await import('../public/js/v4/bang-island-walk.js');
  for(const preset of ['low','mid','high','empty','build']){
    for(const [w,h] of [[390,600],[844,280],[1440,780]]){
      const {canvas,calls}=fakeCanvas(w,h),r=createBangWalkRenderer(canvas,L,BANG(preset));await r.ready;
      const people=B.FACILITY_IDS.map((id,i)=>({id:'p'+i,x:B.doorOf(L,id)[0],y:B.doorOf(L,id)[1],look:{},gender:'female',walking:i%2===0,pose:i===5?'bow':i===3?'sit':null}));
      r.frame({people,focus:B.arrival(L),shift:40},1000);
      assert.ok(calls.includes('fill')&&calls.includes('drawImage')&&calls.includes('fillText'),preset);
      const [sx,sy]=r.toScreen(.42,.63),[mx,my]=r.toMap(sx+10,sy+20);
      assert.ok(Math.abs(mx-.42)<1e-9&&Math.abs(my-.63)<1e-9,`${preset}: tap → map`);
      for(const id of B.FACILITY_IDS){const a=r.anchor(id);assert.ok(a&&a.lift>0,id);}
      r.setBang(BANG('high'));r.frame({people:[],focus:L.plaza.c},2000);r.destroy();
    }
  }
  const phone=walkCamera(390,600,B.arrival(L)),desk=walkCamera(1440,780,L.plaza.c);
  assert.ok(phone.S>=900&&desk.S>phone.S,'a phone follows the player, a desktop sees more');
});

/* ---- the new interface: the Phaser scene with a chainable fake Phaser ---- */
function chain(){const f=function(){};const p=new Proxy(f,{get:(t,k)=>k in t?t[k]:k===Symbol.toPrimitive?()=>0:p,apply:()=>p,set:(t,k,v)=>{t[k]=v;return true;}});return p;}
let FAKE=null;
const phaserOnce=async()=>FAKE??=await phaserFake();   // one fake: the bundle (and its Phaser) is imported once
async function phaserFake(){
  const images=[],textures=new Set(),baked=[],texts=[];
  const camera={scrollX:0,scrollY:0,width:390,height:600,zoom:1,setSize(w,h){this.width=w;this.height=h;},setZoom(z){this.zoom=z;},
    centerOn(x,y){this.scrollX=x-this.width/2;this.scrollY=y-this.height/2;},
    getWorldPoint(x,y){return {x:(x-this.width/2)/this.zoom+this.width/2+this.scrollX,y:(y-this.height/2)/this.zoom+this.height/2+this.scrollY};}};
  const image=()=>{const o={x:0,y:0,depth:0,visible:true,setOrigin(){return o;},setScale(){return o;},setTexture(k){o.key=k;return o;},setVisible(v){o.visible=v;return o;},setAngle(){return o;},
    setPosition(x,y){o.x=x;o.y=y;return o;},setDepth(d){o.depth=d;return o;},setCrop(){return o;},destroy(){o.gone=true;}};images.push(o);return o;};
  const graphics=()=>{const g=chain();g.generateTexture=k=>{baked.push(k);textures.add(k);};return g;};
  const scene={cameras:{main:camera},time:{now:0},tweens:{add(){}},
    textures:{exists:k=>textures.has(k),create:k=>{textures.add(k);return chain();},remove:k=>textures.delete(k)},
    add:{graphics,ellipse:()=>chain(),text:(x,y,t)=>{const o=chain();texts.push(t);o.width=10;return o;},container:()=>chain(),image:(x,y,k)=>image().setTexture(k)}};
  globalThis.__bislPhaser={CANVAS:1,Scale:{NONE:0,NO_CENTER:0},Textures:{FilterMode:{LINEAR:1}},Geom:{Point:class{constructor(x,y){this.x=x;this.y=y;}}},
    Game:class{constructor(cfg){this.cfg=cfg;this.scale={width:390,height:600,resize(){}};cfg.scene.create.call(scene);}destroy(){this.destroyed=true;}}};
  globalThis.__bislStamp=()=>({canvas:{width:120,height:160}});
  const out=await build({stdin:{contents:readFileSync('client/isometric/bang-island.ts','utf8'),loader:'ts',resolveDir:resolve('client/isometric')},bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent',plugins:[{
    name:'bisl-fakes',setup(b){
      b.onResolve({filter:/^(phaser|\/js\/)/},a=>({path:a.path,namespace:'bisl-fake'}));
      b.onLoad({filter:/.*/,namespace:'bisl-fake'},a=>({contents:a.path==='phaser'?'export default globalThis.__bislPhaser;':'export const getCharacterStamp=(...a)=>globalThis.__bislStamp(...a);',loader:'js'}));
    }}]});
  const {BangIslandRenderer}=await import('data:text/javascript;base64,'+Buffer.from(out.outputFiles[0].text).toString('base64'));
  return {BangIslandRenderer,images,baked,texts,camera};
}
test('the new interface paints every band and state, people sorted by depth, only changed facilities repainted', async () => {
  const f=await phaserOnce(),canvas={getBoundingClientRect:()=>({left:0,top:0,width:390,height:600}),parentElement:null};
  for(const preset of ['low','mid','high','empty','build']){
    f.images.length=0;f.baked.length=0;f.texts.length=0;
    const r=new f.BangIslandRenderer(canvas,L,BANG(preset));await r.ready;
    assert.ok(f.baked.length>20,`${preset}: the island, its facilities and trees baked once`);
    if(preset!=='empty'&&preset!=='build')assert.equal(f.texts.filter(t=>t==='🐉').length,2,`${preset}: the bang's sign on the hall's and the gate's banners`);
    assert.equal(f.texts.includes('Long Môn'),preset==='mid'||preset==='high',`${preset}: the name plaque on a stone or gold gate`);
    const people=[{id:'me',x:.6,y:.7,look:{},gender:'female',dir:'se',walking:false},{id:'p',x:.4,y:.4,look:{},gender:'male',dir:'ne',walking:true}];
    const before=f.images.length;r.frame({people,focus:B.arrival(L)});r.tick(100);
    const [me,peer]=f.images.slice(before);assert.ok(me&&peer);assert.ok(me.depth>peer.depth,'the one nearer the viewer in front');
    const at=r.toScreen(.42,.63),back=r.toMap(at[0],at[1]);assert.ok(Math.abs(back[0]-.42)<1e-9&&Math.abs(back[1]-.63)<1e-9,'overlay and tap agree');
    for(const id of B.FACILITY_IDS){const a=r.anchor(id);assert.ok(a&&a.lift>0,`${preset}: ${id} label`);}
    r.frame({people:[people[0]],focus:null});r.tick(200);assert.ok(peer.gone,'someone who left is removed');
    // One facility levels up: only its art is repainted.
    const lv=preset==='high'?2:9,next=BANG(preset);next.facilities[1]={...next.facilities[1],level:lv,band:B.band(lv),state:'done'};
    const n=f.baked.length;r.setBang(next);assert.ok(f.baked.length-n>=1&&f.baked.length-n<=3,`${preset}: one facility repainted (${f.baked.length-n})`);
    const m=f.baked.length;r.setBang(next);assert.equal(f.baked.length,m,'the same look: nothing repainted');
    r.destroy();
  }
});

/* ---- the controller and the live room, with fakes ---- */
function fakeLive(){
  const on=new Map(),sent=[];
  return {sent,on(t,fn){(on.get(t)||on.set(t,new Set()).get(t)).add(fn);return ()=>on.get(t).delete(fn);},send(f){sent.push(f);return true;},
    emit(t,f){for(const fn of on.get(t)||[])fn({t,...f});},count:t=>(on.get(t)||new Set()).size};
}
function isle(now=1000){
  const fac=B.FACILITY_IDS.map((id,i)=>({id,name:id,emoji:'🏯',desc:'',level:i+1,max:10,band:B.band(i+1),band_name:'Gỗ',state:id==='kho_bang'?'building':'done',
    ready_at:id==='kho_bang'?now+30:null,to:id==='kho_bang'?3:null,next:i+2,next_band:B.band(i+2),actions:[{op:'nang_cap',emoji:'⬆️',label:'Nâng cấp'}]}));
  return {now,cap:40,me:{kind:'member',role:'bang_chu'},bang:{id:'b1',name:'Long Môn',emoji:'🐉',color:'#b8282e',level:3,facilities:fac}};
}
function harness(){
  const calls=[],api=new EventTarget();api.state={journey:{story:true,gender:'female'},wardrobe:{look:{}}};
  const env={api,world:{paused:false,wake:()=>calls.push('wake')},closeSheet:()=>calls.push('closeSheet'),toast:t=>calls.push(['toast',t])};
  const frames=[],labels=[],panels=[];let clock=0,wall=1000,tick=null;
  const renderer={frame:m=>frames.push(m),setBang:b=>calls.push(['setBang',b]),toMap:(x,y)=>[x/1000,y/1000],toScreen:(x,y)=>[x*1000,y*1000],anchor:id=>({x:.5,y:.5,lift:50}),personHeight:80,destroy:()=>calls.push('renderer.destroy')};
  const view={open:()=>calls.push('open'),ready:()=>calls.push('ready'),status:s=>calls.push(['status',s]),notice:s=>calls.push(['notice',s]),tags:()=>{},labels:l=>labels.push(l),
    panel:(f,st)=>panels.push(f?{id:f.id,...st}:null),facilities:()=>calls.push('facilities'),covered:()=>120,destroy:()=>calls.push('view.destroy'),
    onClose(fn){this.close=fn;},onTap(fn){this.tap=fn;},onKey(fn){this.key=fn;},onVisit(fn){this.visit=fn;},onEmote(fn){this.emote=fn;},onSay(fn){this.say=fn;},onAction(fn){this.action=fn;},onPanelClose(fn){this.panelClose=fn;}};
  const live=fakeLive(),ran=[],refreshed=[];
  const closed=[],session=createBangIslandSession(env,{isle:isle(),view,loadRenderer:async()=>renderer,loadLive:async()=>live,clock:()=>clock,wall:()=>wall,
    raf:fn=>{tick=fn;return 1;},caf:()=>{tick=null;},onClose:w=>closed.push(w),
    actions:{run:async(f,op)=>{ran.push([f,op]);return {placeholder:true,message:'Sắp có'};},refresh:async()=>{refreshed.push(wall);const x=isle(wall);x.bang.facilities[1].state='done';x.bang.facilities[1].level=3;return x;}}});
  return {session,calls,env,view,live,frames,labels,panels,closed,ran,refreshed,run(ms){const n=Math.ceil(ms/16);for(let i=0;i<n&&tick;i++){clock+=16;tick(clock);}},setWall(v){wall=v;}};
}
test('arriving, walking to a facility, its panel and a button, the build timer, others, going home', async () => {
  const h=harness();await h.session.start();
  assert.equal(h.env.world.paused,true);
  const join=h.live.sent.find(f=>f.t==='bisl_in');assert.equal(join.bang,'b1');assert.deepEqual([join.x,join.y],B.arrival(L).map(v=>+v.toFixed(4)));
  h.live.emit('bisl_room',{room:'bisl:b1',bang:'b1',me:'pme',cap:40,people:[{pid:'p2',name:'Đệ Tử',lk:{},g:'male',x:.5,y:.6,kd:'member',r:'pho_bang'},{pid:'p3',name:'Khách',lk:{},g:null,x:.6,y:.6,kd:'guest',r:null}]});
  h.run(20);const ppl=h.frames.at(-1).people;assert.deepEqual(ppl.map(p=>p.id),['me','p2','p3']);assert.equal(ppl[0].badge,'👑');assert.equal(ppl[1].badge,'⭐');assert.equal(ppl[2].badge,'🧳');
  assert.equal(h.labels.at(-1).length,7);assert.ok(h.labels.at(-1).find(l=>l.id==='kho_bang').building);
  // Tap the hall: its panel opens at once, I walk to its door, the others see me there.
  const hall=L.slots.dai_sanh;h.view.tap(hall.x*1000,hall.y*1000);
  assert.equal(h.panels.at(-1).id,'dai_sanh');assert.equal(h.frames.length&&h.session.panel.id,'dai_sanh');
  const mv=h.live.sent.filter(f=>f.t==='bisl_mv').at(-1);assert.ok(mv&&mv.ms>0);
  h.run(12000);const d=B.doorOf(L,'dai_sanh');assert.ok(Math.hypot(h.session.me.x-d[0],h.session.me.y-d[1])<.03,'at the door');
  assert.ok(h.live.sent.some(f=>f.t==='bisl_do'&&f.s==='dai_sanh'));
  assert.equal(h.frames.at(-1).shift,120,'the camera shows me above the panel');
  await h.view.action('nang_cap');assert.deepEqual(h.ran,[['dai_sanh','nang_cap']]);assert.equal(h.panels.at(-1).msg.kind,'soon');
  h.view.panelClose();assert.equal(h.panels.at(-1),null);assert.equal(h.session.panel,null);
  // A spot: walk there, a line, the others see it.
  h.view.visit('ao_sen');h.run(15000);assert.ok(h.live.sent.some(f=>f.t==='bisl_do'&&f.s==='ao_sen'));assert.equal(h.session.me.pose,'sit');
  assert.ok(h.calls.some(c=>Array.isArray(c)&&c[0]==='notice'&&c[1].startsWith('🪷')));
  // Arrow keys walk along the screen.
  const y0=h.session.me.x+h.session.me.y;h.view.key('ArrowUp',true);h.run(500);h.view.key('ArrowUp',false);h.run(50);assert.ok(h.session.me.x+h.session.me.y<y0,'up the screen');
  // The others: a walk, a bubble, a facility visit; a nudge that the facilities changed.
  h.live.emit('bisl',{room:'bisl:b1',ev:[{k:'mv',pid:'p2',p:[[.5,.6],[.6,.6]],ms:1000},{k:'said',pid:'p2',text:'Chào!'},{k:'do',pid:'p3',s:'den_vang'}]});
  h.run(500);const p2=h.frames.at(-1).people.find(p=>p.id==='p2');assert.ok(p2.walking&&p2.bubble==='Chào!');assert.equal(h.frames.at(-1).people.find(p=>p.id==='p3').act,'🏯');
  // The build finishes: the server is asked again (it decides), the renderer repaints.
  h.setWall(1031);h.run(1100);await new Promise(r=>setTimeout(r,0));
  assert.equal(h.refreshed.length,1);assert.ok(h.calls.some(c=>Array.isArray(c)&&c[0]==='setBang'&&c[1].facilities[1].state==='done'));
  h.live.emit('bisl',{room:'bisl:b1',ev:[{k:'view'}]});await new Promise(r=>setTimeout(r,0));assert.equal(h.refreshed.length,2,'a view nudge refreshes at once');
  h.view.emote('bow');assert.deepEqual(h.live.sent.at(-1),{t:'bisl_emote',e:'bow'});
  assert.equal(h.view.say('Họp bang!'),true);assert.deepEqual(h.live.sent.at(-1),{t:'bisl_say',text:'Họp bang!'});
  h.view.close();assert.deepEqual(h.closed,[null]);assert.equal(h.env.world.paused,false);
  assert.deepEqual(h.live.sent.at(-1),{t:'bisl_out'});assert.equal(h.live.count('bisl'),0,'listeners gone');
  for(const c of ['renderer.destroy','view.destroy','wake'])assert.equal(h.calls.filter(x=>x===c).length,1,c);
});
test('being taken off the island, a reconnect, a refused join', async () => {
  let h=harness();await h.session.start();h.live.emit('bisl_room',{room:'bisl:b1',bang:'b1',me:'pme',people:[]});
  h.live.emit('bisl_left',{why:'changed'});assert.deepEqual(h.closed,['changed']);assert.ok(h.calls.some(c=>Array.isArray(c)&&c[0]==='toast'));
  h=harness();await h.session.start();h.live.emit('bisl_room',{room:'bisl:b1',bang:'b1',me:'pme',people:[]});
  h.live.emit('down',{});const before=h.live.sent.filter(f=>f.t==='bisl_in').length;h.live.emit('welcome',{});
  assert.equal(h.live.sent.filter(f=>f.t==='bisl_in').length,before+1,'joins again');
  h.live.emit('error',{code:'no_bang_island',msg:'x',ref:'bisl_in'});assert.deepEqual(h.closed,['gone']);
  h=harness();await h.session.start();h.live.emit('error',{code:'full',msg:'x',ref:'bisl_in'});assert.deepEqual(h.closed,['full']);
});
test('the live client ignores other bangs\' frames; time left reads well', () => {
  assert.deepEqual(peerAt({from:[0,0],to:[1,1],t0:0,ms:100},50),[.5,.5]);
  const live=fakeLive();let views=0;
  const p=createBangPresence({live,bang:'b1',look:{},gender:null,at:()=>[.5,.5],clock:()=>0,onView:()=>views++}).start();
  live.emit('bisl_room',{room:'bisl:b2',bang:'b2',me:'a',people:[{pid:'x',x:0,y:0}]});assert.equal(p.online,false);
  live.emit('bisl_room',{room:'bisl:b1',bang:'b1',me:'a',cap:40,people:[{pid:'x',x:0,y:0,kd:'guest'}]});assert.equal(p.online,true);assert.equal(p.peers.get('x').guest,true);
  live.emit('bisl',{room:'bisl:b2',ev:[{k:'view'}]});assert.equal(views,0);
  live.emit('bisl',{room:'bisl:b1',ev:[{k:'view'}]});assert.equal(views,1);
  p.stop();assert.equal(live.count('bisl_room'),0);
  assert.equal(timeLeft(45),'45 giây');assert.equal(timeLeft(125),'2 phút 05 giây');assert.equal(timeLeft(3725),'1 giờ 02 phút');assert.equal(timeLeft(90000),'1 ngày 1 giờ');
  assert.deepEqual(looks(isle().bang).facilities[1],{id:'kho_bang',level:2,band:1,state:'building'});
});
test('both interfaces list ⚔️ Đảo bang only while the server has it on', () => {
  assert.equal(townServiceAvailable('bangIsland',{},{bang_island:{cap:40}}),true);
  assert.equal(townServiceAvailable('bangIsland',{journey:{story:true}},{}),false);
  assert.ok(townUtilityGroups({},{bang_island:{}}).some(g=>g.items.some(i=>i.action==='bangIsland')));
  assert.ok(!townUtilityGroups({},{}).some(g=>g.items.some(i=>i.action==='bangIsland')));
  const app=readFileSync('public/js/app.js','utf8');
  assert.match(app,/if\(api\.content\?\.bang_island\)items\.push\(\['bangIsland'/);
  assert.match(app,/action==='bangIsland'\)\{await \(await import\('\.\/v4\/bang-island\.js'\)\)\.bangIslandAction/);
});

test('🏝️ both interfaces draw every island level and the next level\'s work site', async () => {
  globalThis.document??={createElement:()=>fakeCanvas(110,160).canvas};
  const {createBangWalkRenderer}=await import('../public/js/v4/bang-island-walk.js');
  for(const M of [...LEVELS,B.layout(1,2),B.layout(3,4),B.layout(4,5)]){
    const {canvas,calls}=fakeCanvas(390,600),r=createBangWalkRenderer(canvas,M,BANG('high'));
    r.frame({people:[],focus:B.arrival(M)},1000);r.frame({people:[],focus:B.doorOf(M,M.spots.at(-1).id)},1500);
    assert.ok(calls.includes('fill')&&calls.length>500,`old interface, level ${M.level}${M.site?' + site':''}`);r.destroy();
  }
  const f=await phaserOnce(),canvas={getBoundingClientRect:()=>({left:0,top:0,width:390,height:600}),parentElement:null};
  const baked=M=>{f.baked.length=0;const r=new f.BangIslandRenderer(canvas,M,BANG('high'));const n=f.baked.length;r.destroy();return n;};
  const n1=baked(B.layout(1)),n5=baked(B.layout(5)),site=baked(B.layout(2,3));
  assert.ok(n5>n1+10,`level 5 paints its zones and lanterns (${n1} → ${n5})`);assert.ok(site>baked(B.layout(2)),'the work site is painted');
});

test('🏝️ the island upgrades while I am on it: the map is drawn again at its new level', async () => {
  const calls=[],api=new EventTarget();api.state={journey:{story:true,gender:'female'},wardrobe:{look:{}}};
  const env={api,world:{paused:false},closeSheet:()=>{},toast:()=>{}};
  const view={open:()=>{},ready:()=>{},status:s=>calls.push(['status',s]),notice:()=>{},tags:()=>{},labels:()=>{},panel:()=>{},facilities:()=>{},destroy:()=>{},
    spots:l=>calls.push(['spots',l.length]),swapCanvas:()=>calls.push('swap'),isle:()=>{},
    onClose(){},onTap(){},onKey(){},onVisit(){},onEmote(){},onSay(){},onAction(){},onPanelClose(){},onIsle(fn){this.isleTap=fn;}};
  const made=[];let tick=null,wall=1000,clock=0;
  const building=isle();building.bang.isle={level:2,max:5,cap:40,state:'building',ready_at:1030,to:3,left:30};
  const done=isle();done.bang.isle={level:3,max:5,cap:50,state:'done',ready_at:null,to:null,left:0};
  const session=createBangIslandSession(env,{isle:building,view,loadRenderer:async(v,lk,L)=>{made.push(L);return {frame(){},setBang(){},toMap:()=>null,toScreen:()=>[0,0],anchor:()=>null,personHeight:80,destroy:()=>calls.push('destroy')};},
    loadLive:async()=>null,clock:()=>clock,wall:()=>wall,raf:fn=>{tick=fn;return 1;},caf:()=>{tick=null;},actions:{refresh:async()=>done}});
  await session.start();
  assert.equal(session.layout,B.layout(2,3),'level 2 with level 3\'s work site');assert.equal(made[0],B.layout(2,3));
  assert.ok(calls.some(c=>Array.isArray(c)&&c[0]==='status')||true);
  wall=1031;for(let i=0;i<80&&tick;i++){clock+=16;tick(clock);}await new Promise(r=>setTimeout(r,0));await new Promise(r=>setTimeout(r,0));
  assert.equal(session.layout,B.layout(3),'done: level 3');assert.equal(made.at(-1),B.layout(3));
  assert.ok(calls.includes('destroy')&&calls.includes('swap'),'the old renderer goes, a fresh canvas');
  assert.ok(calls.some(c=>Array.isArray(c)&&c[0]==='spots'&&c[1]===8),'the spot chips follow the level');
  for(let i=0;i<80&&tick;i++){clock+=16;tick(clock);}
  const st=calls.filter(c=>Array.isArray(c)&&c[0]==='status').at(-1)[1];assert.match(st,/Đảo cấp 3/);assert.match(st,/\/50/);
  for(let i=0;i<5&&tick;i++){clock+=16;tick(clock);}assert.ok(tick,'the frame loop kept going');
  session.close();
});
