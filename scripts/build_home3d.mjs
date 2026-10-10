import {build} from 'esbuild';
import {stat,readFile} from 'node:fs/promises';
import {gzipSync} from 'node:zlib';
import {homeCompatibility} from './home3d-compat.mjs';
import {resolve} from 'node:path';
const file='public/js/v4/home-3d-scene.js';
// Keep meaningful identifiers: the compatibility gate distinguishes WebGL
// state.reset() from the unsupported Canvas ctx.reset() by its receiver name.
await build({entryPoints:['client/home3d/scene.js'],outfile:file,bundle:true,format:'esm',platform:'browser',target:'es2020',minifyWhitespace:true,minifySyntax:true,minifyIdentifiers:false,sourcemap:false,legalComments:'eof',plugins:[{
  name:'three-explicit-safari-guards',setup(build){
    build.onResolve({filter:/^three$/},()=>({path:resolve('node_modules/three/src/Three.js')}));
    build.onLoad({filter:/three[\\/]src[\\/](math[\\/]Box3|renderers[\\/]webgl[\\/]WebGLTextures)\.js$/},async args=>({contents:homeCompatibility(args.path,await readFile(args.path,'utf8')),loader:'js'}));
  }
}]});
console.log(`Home 3D: ${(await stat(file)).size} bytes, ${gzipSync(await readFile(file)).length} bytes gzip`);
