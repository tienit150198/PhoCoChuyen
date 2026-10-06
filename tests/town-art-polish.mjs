import './phaser25d-wired.mjs';  // skipped while the 2.5D client is not wired (docs/PHASER_25D.md)
import assert from 'node:assert/strict';
const {build}=await import('esbuild');  // after the guard
import {readFile,stat} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
const {default:sharp}=await import('sharp');
const compile=async path=>{const result=await build({entryPoints:[path],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});return import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].text).toString('base64'));};
const m=await compile('client/isometric/model.ts'),art=await compile('client/isometric/building-art.ts');
const content=JSON.parse(execFileSync(process.env.PYTHON||'python',['-c','import json; from game.content import public_content; print(json.dumps({"catalogue":public_content()["catalogue"]}))'],{encoding:'utf8'}));
const careers=content.catalogue.filter(c=>c.playable!==false),families=new Set();
for(const career of careers){
  assert.ok(art.BUILDING_ART[career.id],`${career.id} has an intentional visual family`);
  const kind=m.townBuildingArt(career,'home');families.add(kind);
  const sign=art.FACADE_SIGNS[kind];assert.ok(sign&&sign.x>0&&sign.x<1&&sign.y>0&&sign.y<.65,`${career.id} sign is on its facade`);
  const title=String(career.place||career.short||career.name||career.id),lines=art.facadeTextLines(title);assert.ok(lines.split('\n').length<=2);assert.equal(lines.replace(/\s+/g,' '),title.trim().replace(/\s+/g,' '),'fitting signs never drops part of the real shop name');
}
assert.ok(families.size>=14,'the catalogue does not collapse into three repeated houses');
const manifest=JSON.parse(await readFile('docs/cozy-reference-assets/town-buildings.json','utf8'));
assert.equal(manifest.length,8);
let bytes=0;
for(const asset of manifest){
  const file='public'+asset.url,meta=await sharp(file).metadata();bytes+=(await stat(file)).size;
  assert.equal(meta.hasAlpha,true,asset.id+' has transparency');assert.ok(meta.width<=384&&meta.height<=512,'sprites stay within the mobile texture budget');
}
assert.ok(bytes<450000,'eight new facades are under 450 kB together');
// A transparent boundary prevents neighbouring atlas cells bleeding into a facade.
const {data,info}=await sharp('docs/cozy-reference-assets/town-buildings-source.png').raw().toBuffer({resolveWithObject:true});
for(const x of [0,383,384,767,768,1151,1152,1535])for(let y=0;y<1024;y++)assert.ok(data[(y*1536+x)*info.channels+3]<20,`clear atlas gutter ${x},${y}`);
for(let x=0;x<1536;x++)for(const y of [0,511,512,1023])assert.ok(data[(y*1536+x)*info.channels+3]<20,`clear atlas gutter ${x},${y}`);
for(const direction of ['se','sw'])assert.equal(m.presenceDirection({x:0,y:0},{x:1,y:1.01},direction),direction,'boundary noise does not flip a valid facing');
assert.equal(m.presenceDirection({x:0,y:0},{x:1,y:1.5},'se'),'sw','a real turn changes facing');
assert.deepEqual(m.walkingPose(35,false),{frame:0,lean:0,squash:1},'stopping resets to a planted idle pose');
assert.deepEqual(m.walkingPose(35,true,true),{frame:0,lean:0,squash:1},'reduced motion disables gait deformation');
assert.equal(new Set([0,26,52,78].map(d=>m.walkingPose(d,true).frame)).size,3,'walking passes through planted and both step poses');
assert.equal(m.walkingPose(40,true).frame,m.walkingPose(144,true).frame,'a completed stride returns to the same planted cycle');
const tangent=m.makeNavigation({bounds:{x0:0,y0:0,x1:43,y1:50},roads:[{x0:0,y0:0,x1:43,y1:50}],obstacles:[{x0:18.5,y0:7.08,x1:18.799999999999997,y1:7.380000000000001}],step:.5});
assert.ok(m.lineClear(tangent,{x:18.936354935641457,y:6.9363549356414635},{x:18.98062576897479,y:6.980625768974797}),'short movement across a padded tangent remains consistent despite rounding');
assert.equal(m.lineClear(tangent,{x:18.5,y:6.8},{x:18.5,y:7.6}),false,'the tolerance never permits crossing an obstacle interior');
console.log(`Town art: ${careers.length} mapped careers, ${families.size} families, eight clean sprites (${bytes} bytes), stable facing and distance gait passed.`);
