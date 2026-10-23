// 🏝️ Thiết kế đảo on the clients (game/island_design.py is the server; tests/test_island_design.py checks the grid against
// it): the island at its size (withDesign), placement rules (fitsWhy), every decoration drawn on both interfaces (the old
// walk, v4/island-walk.js; the new Phaser scene, client/isometric/private-island.ts bundled with a fake Phaser), the
// cards' pictures, the buildings' models, and 🛠️ the build mode's map of what stands where (v4/island-editor.js).
import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {build} from 'esbuild';
import * as I from '../public/js/island-layout.js';
import * as A from '../public/js/island-decor-art.js';
import {HOUSE_IDS} from '../public/js/house-art.js';
import {occupiedCells} from '../public/js/v4/island-editor.js';

const SPOT_RE=/^[a-z_]{1,16}$/;   // live/island.py
const KINDS=Object.keys(I.DECOR_META);

/** A design with one of every decoration, each where it fits (scanning the grid like the server's tests). */
function fullDesign(look,t){
  const taken=new Set(),d=[];let id=0;
  for(const kind of KINDS){
    const m=I.decorMeta(kind);let at=null;
    for(let y=0;y<I.GRID.G&&!at;y++)for(let x=0;x<I.GRID.G&&!at;x++)if(!I.fitsWhy(look,t,m.w,m.h,m.where,x,y,0,taken))at=[x,y];
    assert.ok(at,`${look} ${t}: a place for ${kind}`);
    for(const c of I.footprint(m.w,m.h,at[0],at[1],0))taken.add(c);
    d.push([++id,kind,at[0],at[1],0]);
  }
  return {t,d,b:{},ap:1,pts:0};
}
const view=()=>{const n={fill:0,circle:0,line:0};return {n,v:{zs:1,depth:(x,y)=>x+y,P:(x,y,z)=>[(x-y)*560,(x+y)*280-z],fill(){n.fill++;},circle(){n.circle++;},line(){n.line++;}}};};

test('every decoration has its art, a footprint, a card picture and a spot id the live room accepts', () => {
  assert.deepEqual([...A.DECOR_ART_IDS].sort(),[...KINDS].sort());
  for(const kind of KINDS){
    const m=I.decorMeta(kind);assert.ok(m.w>=1&&m.h>=1&&['land','coast','sea','pier','any'].includes(m.where),kind);
    for(const r of [0,1,2,3]){const {n,v}=view();assert.ok(A.paintDecorItem(kind,r,v),`${kind} r${r}`);assert.ok(n.fill+n.circle+n.line>0,`${kind} r${r} drew`);}
  }
  for(const id of [1,25,26,700,999999])assert.match(I.decorSpot(id),SPOT_RE);
  assert.equal(A.paintDecorItem('nope',0,view().v),null);
});

test('the buildings have a model for the build mode (house styles and the first eight)', () => {
  for(const kind of [...HOUSE_IDS,'nha_san','biet_thu','lau_dai','cong_vien','ho_boi','golf','cam_trai','ben_thuyen'])
    for(const r of [0,1]){const {n,v}=view();const out=A.paintBuildingModel(kind,1,0,r,v);assert.ok(out&&out.top>0&&n.fill>0,`${kind} r${r}`);}
  assert.equal(A.paintBuildingModel('nope',1,0,0,view().v),null);
});

test('withDesign: the island grows with its tier, the sea features move out, decorations stand, block and offer spots', () => {
  for(const look of I.LOOK_IDS){
    const L=I.layout(look),w0=I.withDesign(L,null);
    assert.equal(w0.tier,0);assert.deepEqual(w0.bounds,I.BOUNDS);assert.equal(w0.decor.length,0);
    const area=s=>{let a=0;for(let i=0,j=s.length-1;i<s.length;j=i++)a+=(s[j][0]+s[i][0])*(s[j][1]-s[i][1]);return Math.abs(a/2);};
    let last=area(L.shore);
    for(let t=0;t<I.GRID.TIERS.length;t++){const s=I.withDesign(L,{t}).shore;assert.ok(area(s)>last,`${look} tier ${t} bigger`);last=area(s);}
    const D=fullDesign(look,2),W=I.withDesign(L,D);
    assert.equal(W.decor.length,KINDS.length);assert.equal(W.tier,2);
    const dock=I.withDesign(L,{t:2}).dock;assert.notDeepEqual([dock.x,dock.y],[L.dock.x,L.dock.y],`${look}: the pier moved out`);
    for(const it of W.decor){
      const c=I.footprint(it.meta.w,it.meta.h,it.gx,it.gy,it.r)[0];
      if(it.meta.solid)assert.equal(W.cellSolid[c],1,it.kind);
      if(it.meta.pose)assert.ok(W.spots.some(s=>s.decor===it&&SPOT_RE.test(s.id)),`${it.kind} spot`);
    }
    // a solid decoration is in the way, a pier is walkable on the water
    const tree=W.decor.find(d=>d.kind==='cay_dua');assert.ok(!I.walkable(W,tree.x,tree.y),'a tree is in the way');
    const pier=W.decor.find(d=>d.kind==='cau_tau');assert.ok(I.walkable(W,pier.x,pier.y),'the pier is walkable');
    // the footpaths reach the spots from the pier
    const lines=I.footpaths(W);assert.ok(lines.length>0,`${look}: footpaths`);for(const line of lines)assert.ok(line.length>=2);
    assert.equal(I.footpaths({...W,paths:false}).length,0);
  }
});

test('fitsWhy: out of the map, the island\'s own features, overlaps, land / coast / sea / pier', () => {
  const look='dua',t=0,{land,coast,fixed}=I.gridCells(look,t),G=I.GRID.G;
  assert.match(I.fitsWhy(look,t,1,1,'land',-1,0,0,new Set()),/ngoài đảo/);
  assert.match(I.fitsWhy(look,t,3,1,'land',G-2,5,0,new Set()),/ngoài đảo/);
  const f=[...fixed][0];assert.match(I.fitsWhy(look,t,1,1,'land',f%G,Math.floor(f/G),0,new Set()),/công trình sẵn/);
  let inland=-1,sea=-1,shore=-1;
  for(let c=0;c<G*G;c++){if(fixed.has(c))continue;if(inland<0&&land[c]&&!coast[c])inland=c;if(sea<0&&!land[c])sea=c;if(shore<0&&coast[c])shore=c;}
  const at=c=>[c%G,Math.floor(c/G)];
  assert.equal(I.fitsWhy(look,t,1,1,'land',...at(inland),0,new Set()),'');
  assert.match(I.fitsWhy(look,t,1,1,'land',...at(inland),0,new Set([inland])),/đồ khác/);
  assert.match(I.fitsWhy(look,t,1,1,'land',...at(sea),0,new Set()),/đất liền/);
  assert.match(I.fitsWhy(look,t,1,1,'coast',...at(inland),0,new Set()),/sát bờ/);
  assert.equal(I.fitsWhy(look,t,1,1,'coast',...at(shore),0,new Set()),'');
  assert.equal(I.fitsWhy(look,t,1,1,'sea',...at(sea),0,new Set()),'');
  assert.match(I.fitsWhy(look,t,1,1,'sea',...at(inland),0,new Set()),/mặt nước/);
  assert.match(I.fitsWhy(look,t,1,4,'pier',...at(inland),0,new Set()),/một đầu/);
  // a turn swaps the footprint
  assert.deepEqual(I.footprint(2,1,3,4,1),[4*G+3,5*G+3]);
  const [mx,my]=I.cellsMiddle(2,4,10,10,0);assert.deepEqual(I.cellOf(mx,my,2,4,0),[10,10]);assert.deepEqual(I.cellOf(mx,my,2,4,1),[9,11]);
});

test('🛠️ the build mode knows what stands where: buildings (3 × 3) and decorations, one left out while it moves', () => {
  const d={t:0,d:[[1,'cay_dua',20,20,0],[2,'ho_dai',30,30,1]],b:{0:[10,10,0],7:[40,12,1],9:[1,1,0]}};
  const builds={0:{k:'biet_thu'},7:{k:'pho_hoi_an__1'}};   // plot 9 has no building any more: nothing there
  const all=occupiedCells(d,builds),G=I.GRID.G;
  assert.equal(all.get(10*G+10),'b0');assert.equal(all.get(12*G+12),'b0');assert.equal(all.get(12*G+40),'b7');assert.equal(all.get(G+1),undefined);
  assert.equal(all.get(20*G+20),'d1');
  const m=I.decorMeta('ho_dai');for(const c of I.footprint(m.w,m.h,30,30,1))assert.equal(all.get(c),'d2');
  const skip=occupiedCells(d,builds,'d1');assert.equal(skip.get(20*G+20),undefined);assert.equal(skip.get(10*G+10),'b0');
  assert.equal(occupiedCells(null,{}).size,0);
});

/* ---- both interfaces draw a full island ---- */
function fakeCanvas(w=390,h=640){
  const calls=[],ctx=new Proxy({},{get:(t,k)=>k in t?t[k]:(...a)=>{calls.push(k);},set:(t,k,v)=>{t[k]=v;return true;}});
  return {canvas:{width:0,height:0,clientWidth:w,clientHeight:h,getContext:()=>ctx,getBoundingClientRect:()=>({left:0,top:0,width:w,height:h}),parentElement:null},calls};
}
test('the old interface draws every decoration at every size, the build mode\'s camera and overlay included', async () => {
  globalThis.document??={createElement:()=>fakeCanvas(110,160).canvas};
  globalThis.performance??={now:()=>0};
  const {createWalkRenderer}=await import('../public/js/v4/island-walk.js');
  for(const look of I.LOOK_IDS){
    const L=I.layout(look),{canvas,calls}=fakeCanvas(),r=createWalkRenderer(canvas,L);
    for(const t of [0,4]){
      const W=I.withDesign(L,fullDesign(look,t));r.setLayout(W,I.footpaths(W));calls.length=0;
      for(const hour of [0,1])r.frame({people:[],vehicle:null,focus:[.5,.6]},1000+hour*5e4);
      assert.ok(calls.filter(c=>c==='fill').length>KINDS.length*2,`${look} tier ${t}`);
      let drew=0;r.frame({people:[],vehicle:null,camera:{S:900,ox:10,oy:20},overlay:(ctx,P,cam)=>{drew++;assert.equal(cam.S,900);assert.deepEqual(P(0,0),[10,20]);}},2000);
      assert.equal(drew,1);
    }
    r.destroy();
  }
});

function chain(){const f=function(){};const p=new Proxy(f,{get:(t,k)=>k in t?t[k]:k===Symbol.toPrimitive?()=>0:p,apply:()=>p,set:(t,k,v)=>{t[k]=v;return true;}});return p;}
test('the new interface paints a designed island and paints it again only when the design changed', async () => {
  let made=0;
  const camera={scrollX:0,scrollY:0,width:390,height:640,zoom:1,setSize(){},setZoom(){},centerOn(){},getWorldPoint:(x,y)=>({x,y})};
  const children={list:[]};
  const track=()=>{made++;const c=chain();children.list.push(c);return c;};
  const scene={cameras:{main:camera},time:{now:0},tweens:{add(){},killTweensOf(){}},textures:{exists:()=>false,create:()=>chain()},children,
    add:{graphics:track,ellipse:track,text:track,container:track,image:track,rectangle:track}};
  globalThis.__islandPhaser={CANVAS:1,Scale:{NONE:0,NO_CENTER:0},Textures:{FilterMode:{LINEAR:1}},Geom:{Point:class{constructor(x,y){this.x=x;this.y=y;}}},
    Game:class{constructor(cfg){this.scale={width:390,height:640,resize(){}};cfg.scene.create.call(scene);}destroy(){}}};
  globalThis.__islandStamp=()=>({canvas:{width:120,height:160}});
  const out=await build({stdin:{contents:readFileSync('client/isometric/private-island.ts','utf8'),loader:'ts',resolveDir:resolve('client/isometric')},bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent',plugins:[{
    name:'island-fakes',setup(b){
      b.onResolve({filter:/^(phaser|\/js\/)/},a=>({path:a.path,namespace:'island-fake'}));
      b.onLoad({filter:/.*/,namespace:'island-fake'},a=>({contents:a.path==='phaser'?'export default globalThis.__islandPhaser;':'export const getCharacterStamp=(...a)=>globalThis.__islandStamp(...a);',loader:'js'}));
    }}]});
  const {PrivateIslandRenderer}=await import('data:text/javascript;base64,'+Buffer.from(out.outputFiles[0].text).toString('base64'));
  const canvas={getBoundingClientRect:()=>({left:0,top:0,width:390,height:640}),parentElement:null};
  for(const look of I.LOOK_IDS){
    const L=I.layout(look),r=new PrivateIslandRenderer(canvas,L);await r.ready;
    const W=I.withDesign(L,fullDesign(look,3)),paths=I.footpaths(W);
    const before=made;r.setLayout(W,paths);assert.ok(made-before>KINDS.length,`${look}: painted`);
    const again=made;r.setLayout(W,paths);assert.equal(made,again,`${look}: the same design is not painted again`);
    r.setLayout(I.withDesign(L,{t:1}),[]);assert.ok(made>again,`${look}: a new design repainted`);
    const p=r.toMap?.(195,320);assert.ok(!p||(p[0]>=I.BOUNDS[0]-.2&&p[0]<=I.BOUNDS[1]+.2));
    r.destroy();
  }
});

test('the card pictures draw on a canvas', () => {
  const {canvas,calls}=fakeCanvas(92,72);
  for(const kind of KINDS){calls.length=0;assert.equal(A.previewDecorItem(canvas,kind,0),true,kind);assert.ok(calls.includes('fill'),kind);}
  for(const kind of ['biet_thu','lau_dai','ben_thuyen'])assert.equal(A.previewBuilding(canvas,kind),true,kind);
  assert.equal(A.previewDecorItem(canvas,'nope'),false);
});
