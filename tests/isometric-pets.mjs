// 🐾 Pets in the island town (owner 19/10 "đi thị trấn hoặc đi đâu cũng cho phép dẫn theo", "cún cưng to hơn tí"):
// client/isometric/pet-walkers.ts trails a pet behind its owner, sits when they stop, is put back beside them after a
// jump, loads one texture per look and pose (never per frame) and hides beside a ride; the presence `pt` is cleaned
// the same way on both sides (public/js/isometric-town.js publicPet, client/isometric/model.ts publicPet).
import assert from 'node:assert/strict';
import test from 'node:test';
import {resolve} from 'node:path';
import {build} from 'esbuild';

const loads=[];
globalThis.Image=class{set src(v){this._src=v;loads.push(v);queueMicrotask(()=>this.onload?.());}get src(){return this._src;}};
globalThis.document??={createElement:()=>({}),addEventListener(){},querySelector:()=>null};
globalThis.location??={protocol:'https:',host:'localhost',hostname:'localhost',search:'',href:'https://localhost/'};
globalThis.window??=globalThis;globalThis.addEventListener??=()=>{};

async function bundle(entry){
  const out=await build({entryPoints:[resolve(entry)],bundle:true,write:false,format:'esm',platform:'neutral',logLevel:'silent',plugins:[{name:'stubs',setup(b){
    b.onResolve({filter:/^phaser$/},()=>({path:'phaser',namespace:'stub'}));
    b.onLoad({filter:/.*/,namespace:'stub'},()=>({contents:'export default {};'}));
    b.onResolve({filter:/^\/js\//},a=>({path:resolve('public'+a.path)}));
  }}]});
  return import('data:text/javascript;base64,'+Buffer.from(out.outputFiles[0].text).toString('base64'));
}
const {PetWalkers}=await bundle('client/isometric/pet-walkers.ts');
const model=await bundle('client/isometric/model.ts');
const town=await import('../public/js/isometric-town.js');

function scene(){
  const textures=new Map(),images=[];
  const image=()=>{const im={visible:true,x:0,y:0,depth:0,flip:false,key:'',w:0,h:0,destroyed:false,
    setVisible(v){this.visible=v;return this;},setTexture(k){this.key=k;return this;},setDisplaySize(w,h){this.w=w;this.h=h;return this;},setOrigin(){return this;},
    setFlipX(f){this.flip=f;return this;},setPosition(x,y){this.x=x;this.y=y;return this;},setDepth(d){this.depth=d;return this;},destroy(){this.destroyed=true;}};images.push(im);return im;};
  return {images,textures,time:{now:0},sys:{isActive:()=>true},add:{image},
    textures:{exists:k=>textures.has(k),addImage:(k,img)=>textures.set(k,img),remove:k=>textures.delete(k)}};
}
const cat={breeds:[{id:'corgi',kind:'dog',size:'m',shape:'corgi',coats:[{b:'#e2a65a',m:'#c4823a',l:'#fbe3bd'}]},{id:'meo_mun',kind:'cat',size:'m',shape:'cat',coats:[{b:'#333',m:'#222',l:'#555'}]}],accs:[]};
const flush=()=>new Promise(r=>setTimeout(r,0));

test('a pet trails its owner, sits when they stop, and comes back beside them after a jump',async()=>{
  loads.length=0;const sc=scene();let ready=0;const pw=new PetWalkers(sc,()=>ready++),ref={b:'corgi',c:0,a:[],r:5};
  const me={x:5,y:5};
  pw.step('me',ref,me,1/60,cat,false);await flush();
  assert.equal(ready,1,'the picture loads once, then the scene is told');
  for(let i=0;i<120;i++){me.x+=.02;sc.time.now+=16;pw.step('me',ref,me,1/60,cat,false);}
  const im=sc.images[0];await flush();me.x+=.02;pw.step('me',ref,me,1/60,cat,false);   // the walking picture loaded meanwhile
  const f=pw['all'].get('me'),d=Math.hypot(f.at.x-me.x,f.at.y-me.y);
  assert.ok(d<.6&&d>.3,'it keeps a little behind: '+d);
  assert.equal(f.pose,'walk');
  let moving=true;for(let i=0;i<60;i++)moving=pw.step('me',ref,me,1/60,cat,false);
  assert.equal(moving,false,'still: the loop may sleep');assert.equal(f.pose,'sit');
  me.x+=20;pw.step('me',ref,me,1/60,cat,false);
  assert.ok(Math.hypot(f.at.x-me.x,f.at.y-me.y)<1,'a door or a new map: back beside its owner');
  const keys=new Set(loads);assert.equal(keys.size,loads.length,'each pose is drawn once, never per frame');assert.ok(loads.length<=2);
  // a dog of rank SS is drawn bigger than a cat of rank D (walkScale, refBox)
  pw.step('cat',{b:'meo_mun',c:0,a:[]},{x:1,y:1},1/60,cat,false);await flush();pw.step('cat',{b:'meo_mun',c:0,a:[]},{x:1,y:1},1/60,cat,false);
  for(let i=0;i<30;i++)pw.step('cat',{b:'meo_mun',c:0,a:[]},{x:1,y:1},1/60,cat,false);
  for(let i=0;i<30;i++)pw.step('me',ref,me,1/60,cat,false);
  assert.ok(sc.images[0].w>sc.images[1].w*1.2,`dog ${sc.images[0].w} vs cat ${sc.images[1].w}`);
  assert.ok(im.visible);
});

test('no pet beside a ride or without a pet; gone with its owner',async()=>{
  const sc=scene(),pw=new PetWalkers(sc,()=>{}),ref={b:'corgi',c:0,a:[]};
  pw.step('peer:a',ref,{x:1,y:1},1/60,cat,false);await flush();pw.step('peer:a',ref,{x:1,y:1},1/60,cat,false);
  assert.equal(sc.images[0].visible,true);
  assert.equal(pw.step('peer:a',ref,null,1/60,cat,false),false);assert.equal(sc.images[0].visible,false,'riding: hidden');
  pw.step('peer:a',null,{x:1,y:1},1/60,cat,false);assert.equal(sc.images[0].visible,false);
  pw.prune(new Set());assert.equal(sc.images[0].destroyed,true);assert.equal(pw.size,0);
});

test('the presence pet is cleaned the same way on both sides',()=>{
  const raw={b:'corgi',c:2,n:'Bơ',a:['no_hong',5],r:6,x:'cau_vong',evil:'<script>'};
  const want={b:'corgi',c:2,n:'Bơ',a:['no_hong'],r:6,x:'cau_vong'};
  assert.deepEqual(model.publicPet(raw),want);
  assert.deepEqual(town.publicPet(raw),want);
  for(const bad of [null,'x',{b:5,c:0},{b:'corgi'},{b:'corgi',c:1.5}]){assert.equal(model.publicPet(bad),undefined);assert.equal(town.publicPet(bad),null);}
  assert.equal(model.publicPet({b:'corgi',c:0,r:9}).r,undefined,'a rank out of range is dropped');
  const peers=model.publicTownPlayers([{pid:'a',name:'A',x:1,y:1,pt:raw},{pid:'b',name:'B',x:2,y:2}]);
  assert.deepEqual(peers[0].pt,want);assert.equal(peers[1].pt,undefined);
});
