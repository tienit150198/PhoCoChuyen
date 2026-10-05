/** Reproducible local Phaser bundle. Backend import maps version the generated module. */
import {build} from 'esbuild';
import {mkdir, stat} from 'node:fs/promises';
import {gzipSync} from 'node:zlib';
import {readFileSync} from 'node:fs';

await mkdir('public/js/isometric', {recursive:true});
await build({
  entryPoints:['client/isometric/phaser-world.ts'],
  outfile:'public/js/isometric/phaser-world.js',
  bundle:true, format:'esm', platform:'browser', target:'es2020',
  external:['/js/*'], minify:true, sourcemap:false,
  legalComments:'eof',
  define:{CANVAS_RENDERER:'true', WEBGL_RENDERER:'true'},
});
const file='public/js/isometric/phaser-world.js';
console.log(`Phaser scene: ${(await stat(file)).size} bytes, ${gzipSync(readFileSync(file)).length} bytes gzip`);
