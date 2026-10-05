/** Game packaging only: preserve alpha, trim transparent padding, encode smaller WebP sprites. */
import sharp from 'sharp';
import {mkdir,writeFile} from 'node:fs/promises';
const names=['grocery','home','cafe','interior-shop','interior-office','interior-cafe','interior-home','tree','bench','counter','shelf','desk','crates','character-male','character-female'];
await mkdir('public/icons/isometric',{recursive:true});
const assets=[];
for(const name of names){
  const source=`docs/isometric-assets/${name}-source.png`;
  const output=`public/icons/isometric/${name}.webp`;
  const meta=await sharp(source).metadata();
  if(!meta.hasAlpha)throw new Error(`${name} has no alpha channel`);
  // Atlas cell boundaries must survive packaging: trim each directional view at runtime instead.
  const character=name.startsWith('character-');
  const input=character?sharp(source):sharp(source).trim({background:'#00000000',threshold:10});
  const {data,info}=await input.resize({width:character?1024:name.startsWith('interior-')?1280:768,withoutEnlargement:true}).webp({quality:86,alphaQuality:100,effort:6}).toBuffer({resolveWithObject:true});
  await writeFile(output,data);
  assets.push({id:name,url:`/icons/isometric/${name}.webp`,width:info.width,height:info.height,bytes:data.length,source});
  console.log(`${name}: ${info.width}×${info.height}, ${data.length} bytes`);
}
await writeFile('docs/isometric-assets/manifest.json',JSON.stringify({generated:'2026-10-05',assets},null,2)+'\n');
