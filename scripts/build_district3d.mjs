import {build} from 'esbuild';
import {stat,readFile} from 'node:fs/promises';
import {gzipSync} from 'node:zlib';
import {threeCompatibility} from './three-compat.mjs';
import {resolve} from 'node:path';
/** 🏘️ The residential district (khu nhà, v4/residential.js): the only three.js scene left. The home itself is the
 * illustrated room of v4/reno.js since the owner's 23/10 call ("xóa cái nhà 3d đi… chỉ cần nhà bình thường"). */
const file='public/js/v4/district-3d-scene.js';
// Keep meaningful identifiers: the compatibility gate distinguishes WebGL
// state.reset() from the unsupported Canvas ctx.reset() by its receiver name.
await build({entryPoints:['client/district3d/scene.js'],outfile:file,bundle:true,format:'esm',platform:'browser',target:'es2020',minifyWhitespace:true,minifySyntax:true,minifyIdentifiers:false,sourcemap:false,legalComments:'eof',plugins:[{
  name:'three-explicit-safari-guards',setup(build){
    build.onResolve({filter:/^three$/},()=>({path:resolve('node_modules/three/src/Three.js')}));
    build.onLoad({filter:/three[\\/]src[\\/](math[\\/]Box3|renderers[\\/]webgl[\\/]WebGLTextures)\.js$/},async args=>({contents:threeCompatibility(args.path,await readFile(args.path,'utf8')),loader:'js'}));
  }
}]});
console.log(`District 3D: ${(await stat(file)).size} bytes, ${gzipSync(await readFile(file)).length} bytes gzip`);
