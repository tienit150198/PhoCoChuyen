import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {checkSource} from '../scripts/check_old_safari.mjs';
const {homeCompatibility}=await import('../scripts/home3d-compat.mjs').catch(()=>({}));
assert.equal(typeof homeCompatibility,'function','vendor transforms must be reproducible');
for(const file of ['math/Box3.js','renderers/webgl/WebGLTextures.js']){
  const source=await readFile(new URL('../node_modules/three/src/'+file,import.meta.url),'utf8');
  const transformed=homeCompatibility(file,source);
  assert.notEqual(transformed,source,file+' has the documented narrow transform');
  const issues=checkSource(transformed).filter(x=>/Set#union|OffscreenCanvas/.test(x.msg));
  assert.deepEqual(issues,[],file+' exposes the actual guards to the compatibility check');
}
const src='this.union( _box );';
const code=homeCompatibility('math/Box3.js',src);
const {Vector3}=await import('three'),box={min:new Vector3(2,3,4),max:new Vector3(5,6,7)};
new Function('_box',code).call(box,{min:new Vector3(-1,4,2),max:new Vector3(4,8,9)});
assert.deepEqual(box.min.toArray(),[-1,3,2]);assert.deepEqual(box.max.toArray(),[5,8,9]);
console.log('Home 3D vendor compatibility: explicit feature guard and unchanged bounding-box union passed');
