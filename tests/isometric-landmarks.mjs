import assert from 'node:assert/strict';
import {build} from 'esbuild';
const output=await build({entryPoints:['client/isometric/model.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const m=await import('data:text/javascript;base64,'+Buffer.from(output.outputFiles[0].text).toString('base64'));
assert.equal(typeof m.landmarkSpritePlacement,'function','already-isometric artwork needs sprite placement, not another perspective transform');
for(const landmark of m.townLandmarks()){
 const plane=m.landmarkPlaneGeometry(landmark.footprint),sprite=m.landmarkSpritePlacement(landmark.footprint,576,320);
 assert.equal(sprite.width,plane.width);
 assert.ok(Math.abs(sprite.height/sprite.width-320/576)<1e-10,'isometric sprite keeps its illustrated aspect ratio');
 assert.equal(sprite.x,plane.x+plane.width/2);
 assert.equal(sprite.y,plane.y+plane.height);
 assert.ok(sprite.depth<0,'ground landmark cannot paint over pedestrians/buildings');
}
console.log('Landmark sprites: one projection, unchanged proportions and ground layer passed');

const {default:sharp}=await import('sharp');
const {stat}=await import('node:fs/promises');
const file='public/icons/cozy-v3/town-pool.webp',meta=await sharp(file).metadata();
assert.ok(meta.hasAlpha,'town sprite must not carry a rectangular landscape background');
assert.ok(meta.width<=576&&meta.height<=350);
assert.ok((await stat(file)).size<100000,'one static pool stays below the mobile download budget');
