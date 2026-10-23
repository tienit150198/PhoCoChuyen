// 🎣 The fish drawn in code (public/js/v4/fish-art.js) for every species of game/fishing_content.py, the fish carried in
// the hands (v4/look.js), tranh cá and the aquarium (v4/deco-art.js). The species come on stdin (tests/test_fishing.py
// Content.test_art_in_node: game/fishing.catalogue()['species']).
//   python -c "import json;from game import fishing;print(json.dumps(fishing.catalogue()['species']))" | node tests/fishing-art.mjs
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

globalThis.Path2D??=class{constructor(d){this.d=d;}};
const species=JSON.parse(readFileSync(0,'utf8'));
assert.ok(species.length>=40,'the catalogue');
const {fishSvg,drawFish,carrySize,fmtKg,FAMILIES,RARITY_COLORS}=await import('../public/js/v4/fish-art.js');

// 1. every species draws: an SVG with no NaN, its silhouette too, and on a canvas with only finite numbers
const bad=v=>typeof v==='number'&&!Number.isFinite(v);
const ctx=new Proxy({},{get:(o,k)=>k in o?o[k]:(...a)=>{for(const x of a)assert.ok(!bad(x),`canvas ${String(k)}: ${a}`);return {addColorStop(){}};},set:(o,k,v)=>{o[k]=v;return true;}});
for(const sp of species){
  assert.ok(FAMILIES.includes(sp.fam),`${sp.id}: family ${sp.fam}`);
  assert.ok(RARITY_COLORS[sp.r],`${sp.id}: rarity ${sp.r}`);
  for(const sil of [false,true]){
    const s=fishSvg(sp,{w:64,h:32,silhouette:sil});
    assert.ok(s.startsWith('<svg')&&s.endsWith('</svg>'),`${sp.id}: svg`);
    assert.ok(!/NaN|undefined|null/.test(s),`${sp.id}: ${s.match(/.{20}(NaN|undefined|null).{10}/)?.[0]}`);
  }
  drawFish(ctx,sp,50,50,40,{flip:true,wiggle:.3});
}

// 2. carried fish: rarer is never smaller, a cap for the walk maps
for(let r=1;r<7;r++)assert.ok(carrySize(r,5)>=carrySize(r-1,5));
assert.ok(carrySize(6,100000)<=34&&carrySize(3,1)>=10);
assert.equal(fmtKg(350),'350 g');assert.equal(fmtKg(1250),'1,3 kg');assert.equal(fmtKg(2500000),'2,5 tấn');

// 3. 💪 in the hands (look.js): figure() reads journey.fish.wear, withFish adds / drops it, both pens draw it
const L=await import('../public/js/v4/look.js');
const sp=species.find(s=>s.r>=3),fh={sp:sp.id,r:sp.r,kg:sp.w[0],fam:sp.fam,body:sp.body,belly:sp.belly,fin:sp.fin,pat:sp.pat};
const F=L.figure({journey:{gender:'female',fish:{wear:fh}}});
assert.deepEqual(F.L.fh,fh);
const out=[];L.paintPlayer(out,F,L.SVG);assert.ok(out.join('').includes('fish-art'),'the SVG pen draws the fish');
const plain=[];L.paintPlayer(plain,L.figure({journey:{gender:'female'}}),L.SVG);assert.ok(!plain.join('').includes('fish-art'));
assert.deepEqual(L.withFish({hair:'a',fh},null),{hair:'a'});
assert.equal(L.withFish({hair:'a'},{sp:'x'}).fh,undefined,'no drawing fields: no fish');
L.paintPlayer(ctx,F,L.CANVAS);

// 4. 🖼️ tranh cá and 🐠 the aquarium (deco-art.js): a shadow until reno.js fills the maps, then the catch and its weight
const A=await import('../public/js/v4/deco-art.js');
assert.ok(A.ART.tranh_ca.d(76,68,'u1').includes('fish-sil'));
A.FISH_TRO.set('u1',{sp,g:4200});
const t=A.ART.tranh_ca.d(76,68,'u1');assert.ok(t.includes('4,2 kg')&&!t.includes('fish-sil')&&!/NaN/.test(t));
const tank=A.ART.be_ca.d(80);A.AQUA.push(...species.slice(0,4));
const full=A.ART.be_ca.d(80);assert.equal((full.match(/class="fish-art/g)||[]).length,3,'three fish show');assert.ok(!tank.includes('fish-art'));
console.log(`fishing art ok: ${species.length} species`);
