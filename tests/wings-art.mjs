// 🪽 Cánh, the art (public/js/v4/wings-art.js through v4/look.js): every style at every tier draws in both pens, the
// classic character and the portraits carry the worn wing, the 2.5D stamp keys on it, walkers bring it on both maps.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {defaultLook,lookOf,figure,figureOf,figureSVG,portrait,myPortrait,paintPlayer,SVG,CANVAS,wingIcon,withWings,withPairs,cleanPairs,cleanWing,wingOfState,WING_STYLES,WING_TIERS,WING_TIER_COLOR} from '../public/js/v4/look.js';
import {characterKey} from '../public/js/isometric/character-art.js';

const py=readFileSync(new URL('../game/wings_content.py',import.meta.url),'utf8');

test('the same styles and tiers as game/wings_content.py',()=>{
  assert.deepEqual([...py.matchAll(/_s\('([a-z_]+)'/g)].map(m=>m[1]),[...WING_STYLES]);
  assert.equal(WING_TIERS.length,8);assert.equal(WING_TIERS[7],'Huyền thoại');assert.equal(WING_TIER_COLOR.length,8);
  assert.deepEqual(cleanWing({k:'rong',r:'7'}),{k:'rong',r:7});
  for(const bad of [null,[],{k:'rong',r:8},{k:'rong',r:-1},{k:'x',r:1},{k:'rong'}])assert.equal(cleanWing(bad),null);
});

test('every style at every tier draws, in SVG and on a canvas, with unique gradient ids',()=>{
  const ids=new Set();
  for(const k of WING_STYLES)for(let r=0;r<8;r++){
    const svg=figureSVG({...defaultLook('female'),wg:{k,r}},'female');
    assert.doesNotMatch(svg,/NaN|undefined/);assert.match(svg,/linearGradient/);
    for(const m of svg.matchAll(/id="(wg\d+)"/g)){assert.ok(!ids.has(m[1]),'a gradient id once in the page');ids.add(m[1]);}
    const icon=wingIcon({k,r},56,`Cánh ${k}`);assert.match(icon,/aria-label="Cánh /);assert.doesNotMatch(icon,/NaN/);
    if(r>=4)assert.match(svg,/radialGradient/,'a glow from S');
  }
  globalThis.Path2D??=class{constructor(d){this.d=d;}};
  const calls=[];const c=new Proxy({},{get:(t,p)=>p in t?t[p]:typeof p==='string'?(...a)=>{calls.push(p);return {addColorStop(){}};}:undefined,set:(t,p,v)=>{t[p]=v;return true;}});
  paintPlayer(c,figureOf({...defaultLook('male'),wg:{k:'phuong',r:7}},'male'),CANVAS);
  assert.ok(calls.includes('createLinearGradient')&&calls.includes('createRadialGradient'));
  assert.equal(wingIcon({k:'nope',r:1}),'');
});

test('the worn wing of a save, on the character, the portraits and a walker',()=>{
  const state={journey:{gender:'male',wings:{own:[{id:'w1',k:'buom',r:2},{id:'w2',k:'doi',r:5}],on:'w2'}}};
  assert.deepEqual(wingOfState(state),{k:'doi',r:5});
  assert.equal(wingOfState({journey:{wings:{own:[{id:'w1',k:'buom',r:2}],on:null}}}),null);
  assert.deepEqual(figure(state).L.wg,{k:'doi',r:5});
  assert.notEqual(myPortrait(state,40),myPortrait({journey:{gender:'male'}},40));
  assert.deepEqual(withWings({top:'a'},{k:'tien',r:1}),{top:'a',wg:{k:'tien',r:1}});
  assert.deepEqual(withWings({top:'a',wg:{k:'tien',r:1}},null),{top:'a'});
  assert.notEqual(portrait({...defaultLook('male'),wg:{k:'rong',r:4}},'male',56),portrait(defaultLook('male'),'male',56));
  const a=characterKey({look:{...defaultLook('male'),wg:{k:'rong',r:4}},gender:'male'}),b=characterKey({look:defaultLook('male'),gender:'male'});
  assert.notEqual(a,b,'the 2.5D stamp keys on the wing');
  assert.equal(characterKey({look:{...defaultLook('male'),wg:{k:'??',r:4}},gender:'male'}),b,'an unknown style is dropped');
});

test('walkers bring their wings on both maps, the workplace scene flaps them',()=>{
  const src=readFileSync(new URL('../public/js/isometric-town.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
  const ctx=vm.createContext({withPairs,cleanPairs,withWings,cleanWing,lookOf,withBang:x=>x,tagLine:()=>'',tagInk:()=>'',badge:()=>'',publicActivity:()=>null,sitePresence:{},live:{},leisurePresence:{}});
  vm.runInContext(src+'\nglobalThis.peer=publicPeer;',ctx);
  const p=ctx.peer({pid:'p1',x:1,y:2,lk:{top:'ao_quen'},wg:{k:'thien_than',r:7}});
  assert.deepEqual(JSON.parse(JSON.stringify(p.look)),{top:'ao_quen',wg:{k:'thien_than',r:7}});
  assert.match(src,/Object\.hasOwn\(e,'wg'\)/);
  assert.match(readFileSync(new URL('../client/isometric/model.ts',import.meta.url),'utf8'),/look\.wg=\{k:/);
  assert.match(readFileSync(new URL('../public/js/isometric/phaser-world.js',import.meta.url),'utf8'),/\.wg=\{k:\w+\.wg\.k\.slice/,'the bundle is rebuilt');
  const walk=readFileSync(new URL('../public/js/v4/walk.js',import.meta.url),'utf8');
  assert.match(walk,/e\.k==='wg'/);assert.match(walk,/withWings\(withPairs\(p\.lk,p\.pr\),p\.wg\)/);
  assert.match(readFileSync(new URL('../public/js/boba-world.js',import.meta.url),'utf8'),/paintWings\(c,F,CANVAS,\{flap:/);
});
