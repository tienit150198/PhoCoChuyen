// 🐱 Mèo Mai (owner 24/10, his own Scottish Fold: game/pets_content.py meo_mai) as public/js/v4/pet-art.js draws her
// in every pose and every place a pet is drawn (shop, home, the stroll, the 2.5D town's <img> textures). Run by
// tests/test_pets.py.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {SHAPES,petSVG,petURL,refURL,refBox,lookup} from '../public/js/v4/pet-art.js';

const py=readFileSync(new URL('../game/pets_content.py',import.meta.url),'utf8');
const row=py.slice(py.indexOf("_b('meo_mai'"));
const coat=row.match(/_c\('([^']+)', '(#[0-9a-f]{6})', '(#[0-9a-f]{6})', '(#[0-9a-f]{6})', '(#[0-9a-f]{6})'\)/);
assert.ok(coat,'the coat in the catalogue');
const breed={id:'meo_mai',kind:'cat',name:'Mèo Mai',shape:'mai',size:'m',shop:true,fuse:'',coats:[{name:coat[1],b:coat[2],m:coat[3],l:coat[4],e:coat[5]}]};
assert.ok(row.startsWith("_b('meo_mai', 'cat', 'Mèo Mai', 'mai', "),'the shape the catalogue names');
assert.ok(SHAPES.mai&&SHAPES.mai.k==='cat'&&SHAPES.mai.ear==='fold'&&SHAPES.mai.slump,'her shape: a fold-eared cat that slumps');
const K=breed.coats[0];

/** Well-formed enough to load as an <img>: balanced tags, no duplicate attribute, no NaN / undefined. */
function sane(svg,what){
  assert.doesNotMatch(svg,/NaN|undefined|Infinity/,what);
  for(const tag of svg.match(/<[a-zA-Z][^>]*>/g)){
    const names=[...tag.matchAll(/\s([a-zA-Z:-]+)=/g)].map(m=>m[1]);
    assert.equal(new Set(names).size,names.length,`${what}: a duplicate attribute in ${tag.slice(0,120)}`);
  }
  const open=(svg.match(/<(g|svg|defs|linearGradient|radialGradient|filter|text)[\s>]/g)||[]).length;
  const close=(svg.match(/<\/(g|svg|defs|linearGradient|radialGradient|filter|text)>/g)||[]).length;
  assert.equal(open,close,`${what}: balanced groups`);
}
const looks=[{},{neck:'vong_chuong',head:'no_hong',body:'ao_len',bed:'nem_may'}];
const fxs=[{},{r:4},{r:6,x:'cau_vong'},{lg:true}];
for(const pose of ['sit','happy','walk','sleep'])for(const acc of looks)for(const fx of fxs)sane(petSVG(breed,K,pose,acc,120,'pet-svg',fx),`${pose} ${JSON.stringify(acc)} ${JSON.stringify(fx)}`);

const sit=petSVG(breed,K,'sit',{},120),happy=petSVG(breed,K,'happy',{},120),walk=petSVG(breed,K,'walk',{},120),sleep=petSVG(breed,K,'sleep',{},120);
for(const [pose,svg] of Object.entries({sit,happy,walk,sleep})){
  assert.ok(svg.includes(`fill="${K.m}"`),`${pose}: the lilac cap / saddle`);
  assert.ok(svg.includes('stroke-dasharray'),`${pose}: the ringed tail`);
  assert.ok(svg.includes(`fill="${K.b}"`),`${pose}: the white coat`);
}
for(const [pose,svg] of Object.entries({sit,happy,walk}))assert.ok(svg.includes(`fill="${K.e}"`),`${pose}: her amber eyes`);
assert.ok(!sleep.includes(`fill="${K.e}"`),'asleep: eyes closed');
// the thin yellow collar with its silver ring, unless a neck piece is worn
for(const svg of [sit,walk,sleep])assert.ok(svg.includes('fill="#f2c230"'),'her yellow collar');
assert.ok(!petSVG(breed,K,'sit',{neck:'vong_chuong'},120).includes('fill="#f2c230"'),'a worn collar replaces hers');
// her pose: slumped, the grey toe beans of both hind feet to you; happy: a paw raised (the photos)
assert.ok((sit.match(/fill="#8e8992"/g)||[]).length>=10,'grey toe beans');
assert.ok(happy.includes('class="pet-wave"')&&!sit.includes('class="pet-wave"'),'happy waves a paw');
assert.notEqual(sit,petSVG({...breed,shape:'fold'},K,'sit',{},120),'not the plain Scottish Fold');

// the stroll and the 2.5D town draw a pet from a save's ref through refURL / refBox
const cat={breeds:[breed],accs:[]};
assert.equal(lookup(cat,'meo_mai',0).breed,breed);
for(const pose of ['walk','sit']){
  const url=refURL(cat,{b:'meo_mai',c:0,a:[],r:5},pose,96);
  assert.ok(url.startsWith('data:image/svg+xml'),pose);
  const svg=decodeURIComponent(url.slice(url.indexOf(',')+1));
  assert.ok(svg.includes('xmlns="http://www.w3.org/2000/svg"'));sane(svg,'refURL '+pose);
}
assert.ok(petURL(breed,K,'walk',{},96).length>1000);
const box=refBox(cat,{b:'meo_mai',c:0},'walk');
assert.ok(box.w>0&&box.h>0&&box.k===1.1,'a cat walks at the cats\' size');
console.log('pet art: Mèo Mai ok');
