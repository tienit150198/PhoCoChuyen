// 🎣 Each rod looks like itself (public/js/v4/fish-rod.js; owner 25/10 "cần xịn thì nhìn khác đi nữa chứ nhìn cần giống
// nhau quá"): every rod of game/fishing_content.py RODS (their ids on stdin, tests/test_fishing.py Content.test_rods_in_node)
// has its own look, no two alike (body colours, line, reel, rings, decorations), a better rod never shorter, thinner or
// with a smaller reel; drawn on a canvas with finite numbers only and as a shop icon.
//   python -c "import json;from game import fishing_content as C;print(json.dumps([r['id'] for r in C.RODS]))" | node tests/fishing-rod.mjs
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

let ids=[];try{ids=JSON.parse(readFileSync(0,'utf8')||'[]');}catch{ids=[];}
const R=await import('../public/js/v4/fish-rod.js');
if(!ids.length)ids=[...R.ROD_IDS];
assert.deepEqual(ids,[...R.ROD_IDS],'a look for every rod of the catalogue, in its order');
const sig=id=>{const L=R.rodLook(id);return JSON.stringify([L.body,L.line,L.grip,L.reel,L.rings,L.nodes,L.weave||'',L.scales||'',L.gem,L.head,L.glow]);};
assert.equal(new Set(ids.map(sig)).size,ids.length,'no two rods alike');
assert.equal(new Set(ids.map(R.lineColor)).size,ids.length,'each its own line colour');
assert.equal(new Set(ids.map(id=>R.rodLook(id).body.join())).size,ids.length,'each its own colour / material');
for(let i=1;i<ids.length;i++){const a=R.rodLook(ids[i-1]),b=R.rodLook(ids[i]);
  assert.ok(b.len>=a.len,`${ids[i]} not shorter`);assert.ok((b.reel?.r||0)>=(a.reel?.r||0),`${ids[i]}: its reel not smaller`);}
const top=R.rodLook(ids.at(-1));assert.ok(top.head&&top.glow&&top.spark>0,'Long Vương: the dragon head, a glow, sparkles');
assert.equal(R.rodLook('a_newer_rod'),R.rodLook('tre'),'an unknown rod: the bamboo one');
const bad=v=>typeof v==='number'&&!Number.isFinite(v);let calls=0;
const ctx=new Proxy({},{get:(o,k)=>k in o?o[k]:(...a)=>{calls++;for(const x of a)assert.ok(!bad(x),`canvas ${String(k)}: ${a}`);},set:(o,k,v)=>{o[k]=v;return true;}});
const drawn=new Map();
for(const id of ids){const before=calls;R.drawRod(ctx,id,{bx:10,by:200,x:60,y:40,cx:40,cy:120,s:1,t:1.5});R.drawRod(ctx,id,{bx:10,by:200,x:10,y:200,s:.5,t:null,calm:true});
  drawn.set(id,calls-before);
  const tip=R.rodTipOf(id,{bx:10,by:200,x:60,y:40});assert.ok(tip.every(Number.isFinite));
  const svg=R.rodSvg(id,40,'Cần');assert.ok(svg.startsWith('<svg')&&svg.endsWith('</svg>')&&!/NaN|undefined|null/.test(svg),`${id}: svg`);}
assert.ok(drawn.get(ids.at(-1))>drawn.get(ids[0]),'the top rod has more to it than the bamboo one');
console.log(`fishing-rod: ok (${ids.length} rods)`);
