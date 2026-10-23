// 🪽 Cánh, the art (public/js/v4/wings-art.js through v4/look.js): every style at every tier draws in both pens, the
// classic character and the portraits carry the worn wing, the 2.5D stamp keys on it, walkers bring it on both maps.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {defaultLook,lookOf,figure,figureOf,figureSVG,portrait,myPortrait,paintPlayer,SVG,CANVAS,wingIcon,withWings,withPairs,cleanPairs,cleanWing,wingOfState,WING_STYLES,WING_TIERS,WING_TIER_COLOR} from '../public/js/v4/look.js';
import {characterKey,STAMP_WING,stampWingFrame,RIG_BOX,wingedStamp,WINGED_W} from '../public/js/isometric/character-art.js';
import {flapAt,WING_BEAT,wingMotes,moteAt,raysAt,burstAt,drawWings,stillMotion,flapStep,FLAP_STEPS,CLASSIC_WING} from '../public/js/v4/wings-art.js';

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
  assert.match(walk,/e\.k==='wg'/);
  assert.match(readFileSync(new URL('../public/js/boba-world.js',import.meta.url),'utf8'),/paintWings\(c,F,CANVAS,\{t:this\.reduced\?null:this\.time,walk:moving\}\)/);
});

// ✨ owner 22/10 "cánh có hoạt họa, có tia sáng này kia nhé": the same beat everywhere, light by tier, stillness respected
test('each style its own beat: butterfly and fairy quick, bat and dragon slow, all within 1.3–2.6 s',()=>{
  for(const k of WING_STYLES){assert.ok(WING_BEAT[k]>=1.3&&WING_BEAT[k]<=2.6,k);for(let t=0;t<3;t+=.1)assert.ok(Math.abs(flapAt(k,t))<=1);}
  assert.ok(WING_BEAT.buom<WING_BEAT.thien_than&&WING_BEAT.tien<WING_BEAT.thien_than);
  assert.ok(WING_BEAT.rong>WING_BEAT.thien_than&&WING_BEAT.doi>WING_BEAT.thien_than);
  assert.equal(flapAt('rong',0),0);assert.ok(Math.abs(flapAt('buom',WING_BEAT.buom/4))>Math.abs(flapAt('rong',WING_BEAT.rong/4)),'a dragon beats heavier, smaller');
  assert.deepEqual(FLAP_STEPS.map(flapStep),[...FLAP_STEPS]);assert.equal(flapStep(.6),.5);
});

test('light by tier: a few motes D–A, more from S, rays from S, the ring and a burst of motes for SSS and Huyền thoại',()=>{
  const n=r=>wingMotes({k:'thien_than',r}).filter(m=>!m.burst).length,burst=r=>wingMotes({k:'thien_than',r}).filter(m=>m.burst).length;
  for(const r of [0,1,2,3])assert.ok(n(r)>=2&&n(r)<=3,`tier ${r}`);
  assert.ok(n(4)>n(3)&&n(5)>=n(4)&&n(6)>n(5)&&n(7)>=n(6));
  for(const r of [0,1,2,3,4,5])assert.equal(burst(r),0);assert.ok(burst(6)>0&&burst(7)>0);
  for(const r of [0,1,2,3])assert.equal(raysAt(r,1),null);for(const r of [4,5,6,7])assert.ok(raysAt(r,1).n>=6);
  assert.ok(raysAt(7,1).n>raysAt(4,1).n);
  for(const m of wingMotes({k:'phuong',r:7}))for(let t=0;t<5;t+=.13){const p=moteAt(m,t);assert.ok(p.a>=0&&p.a<=1&&Number.isFinite(p.x)&&Number.isFinite(p.y));assert.deepEqual(moteAt(m,t),p,'a pure function of the time');}
  const seen=new Set();for(let t=0;t<2.6;t+=.05){const b=burstAt(t);seen.add(!!b);if(b)assert.ok(b.ph>=0&&b.ph<=1&&b.a>=0&&b.a<=.6);}assert.deepEqual([...seen].sort(),[false,true]);
});

test('the SVG pen animates by itself (SMIL), a canvas frame moves with t, reduced motion keeps it all still',()=>{
  const ht=wingIcon({k:'phuong',r:7},56),d=wingIcon({k:'buom',r:0},56);
  assert.match(ht,/<animateTransform attributeName="transform" type="rotate"/);assert.match(ht,/attributeName="r"/,'the ring');
  assert.ok((ht.match(/type="translate"/g)||[]).length>(d.match(/type="translate"/g)||[]).length,'more motes at HT');
  assert.ok((d.match(/type="translate"/g)||[]).length>=2,'a D wing still twinkles');assert.doesNotMatch(d,/attributeName="r"/);
  assert.doesNotMatch(portrait({...defaultLook('male'),wg:{k:'rong',r:7}},'male',56),/<animate/,'portraits stay still');
  const at=t=>{const o=[];drawWings(o,SVG,{k:'rong',r:5},0,0,{t,anim:false});return o.join('').replace(/wg\d+/g,'id');};
  assert.notEqual(at(0),at(.4),'a frame at t differs');assert.equal(at(.4),at(.4));
  const saved=globalThis.document;globalThis.document={documentElement:{classList:{contains:()=>false}},body:{classList:{contains:c=>c==='reduce-motion'}}};
  try{assert.ok(stillMotion());assert.doesNotMatch(wingIcon({k:'phuong',r:7},56),/<animate/);assert.equal(at(0),at(.4),'still: no flap, no motes');}
  finally{if(saved===undefined)delete globalThis.document;else globalThis.document=saved;}
});

test('the classic street draws the wings apart and moves them; the 2.5D map rigs them (the bundle is rebuilt)',()=>{
  const walk=readFileSync(new URL('../public/js/v4/walk.js',import.meta.url),'utf8');
  assert.match(walk,/const F=figureOf\(withPairs\(p\.lk,p\.pr\),p\.g\)/,'the sprite without wings');
  assert.match(walk,/wingsBack\(c,p,p\.x,p\.y\+bob,sec,calm\);/);assert.match(walk,/wingsFront\(c,p,p\.x,p\.y\+bob,sec,calm\);/);
  assert.match(walk,/S\.wingsOn\?66:120/);
  assert.deepEqual(Object.keys(STAMP_WING),['front','back','baked']);assert.equal(stampWingFrame({k:'rong',r:1},false,0),null,'no canvas in node');
  const ts=readFileSync(new URL('../client/isometric/phaser-world.ts',import.meta.url),'utf8');
  assert.match(ts,/if\(look\?\.wg\)\{const \{wg:_,\.\.\.bare\}=look;look=bare;\}/,'the 2.5D stamp without wings');
  assert.match(ts,/if\(wingsLive\)this\.wingTick\(\)/);
  const bundle=readFileSync(new URL('../public/js/isometric/phaser-world.js',import.meta.url),'utf8');
  assert.match(bundle,/wg-f:/);assert.match(bundle,/wingTop/);
});

// 🪽 owner 23/10 "cánh mua xong ra ngoài xấu quá, cho đẹp hơn, to hơn nhé": spread wide past the big head, rising high
const extent=(wg,o)=>{const out=[];drawWings(out,SVG,wg,0,0,{anim:false,aura:false,sparkle:false,...o});const xs=[],ys=[];
  for(const m of out.join('').matchAll(/ d="([^"]+)"/g)){const v=m[1].match(/-?\d+(\.\d+)?/g).map(Number);for(let i=0;i+1<v.length;i+=2){xs.push(v[i]);ys.push(v[i+1]);}}
  return {w:Math.max(...xs)-Math.min(...xs),top:Math.min(...ys),bottom:Math.max(...ys)};};
test('big wings: wide past the head, tips high, bướm and tiên a little smaller; a bigger stroke walking',()=>{
  for(const k of WING_STYLES){const e=extent({k,r:0},{s:CLASSIC_WING.s,gap:CLASSIC_WING.gap,tall:CLASSIC_WING.tall});
    const small=k==='buom'||k==='tien';assert.ok(e.w>=(small?120:135)&&e.w<=200,`${k} classic span ${e.w} (the head is 66 wide, the body 46)`);
    assert.ok(e.top<=-52,`${k} rises to the head (${e.top})`);
    const iso=extent({k,r:0},{s:STAMP_WING.front.s,gap:STAMP_WING.front.gap});assert.ok(iso.w>=(small?135:150)&&iso.w<=RIG_BOX[0],`${k} 2.5D span ${iso.w} (the chibi's head is ~95)`);
    const ht=extent({k,r:7},{s:STAMP_WING.front.s,gap:STAMP_WING.front.gap,flap:-1});assert.ok(ht.w<RIG_BOX[0]&&-ht.top<RIG_BOX[3]&&ht.bottom<RIG_BOX[1]-RIG_BOX[3],`${k} fits the rig's canvas`);
    const amp=walk=>Math.max(...[...Array(60)].map((_,i)=>Math.abs(flapAt(k,i*.05,walk))));assert.ok(amp(true)>amp(false)*1.8,`${k} walks with a bigger stroke`);}
  assert.ok(extent({k:'rong',r:0},{}).w>extent({k:'buom',r:0},{}).w);
  assert.equal(typeof wingedStamp,'function');assert.ok(WINGED_W>120);
});
