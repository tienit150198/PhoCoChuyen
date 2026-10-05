/** Package approved illustrated source assets; preserve alpha and atlas cell boundaries. */
import sharp from 'sharp';
import {mkdir,readFile,writeFile} from 'node:fs/promises';

const root='docs/cozy-reference-assets',out='public/icons/cozy-v2';
await mkdir(out,{recursive:true});
const manifest=JSON.parse(await readFile(`${root}/sources.json`,'utf8'));
const assets=[];
for(const source of manifest.assets){
  const path=`${root}/${source.id}-source.png`,meta=await sharp(path).metadata();
  if(!meta.hasAlpha&&!source.background)throw new Error(`${source.id}: transparent alpha required`);
  const character=source.id.startsWith('character-'),atlas=character||source.atlas;
  const input=atlas||source.background?sharp(path):sharp(path).trim({background:'#00000000',threshold:10});
  const {data,info}=await input.resize({width:source.width||(character?1024:source.background?960:720),withoutEnlargement:true}).webp({quality:86,alphaQuality:100,effort:6}).toBuffer({resolveWithObject:true});
  await writeFile(`${out}/${source.id}.webp`,data);
  assets.push({id:source.id,url:`/icons/cozy-v2/${source.id}.webp`,width:info.width,height:info.height,bytes:data.length,...(atlas?{columns:source.columns||4,rows:source.rows||3}: {})});
  console.log(`${source.id}: ${info.width}×${info.height}, ${data.length} bytes`);
}
await writeFile(`${root}/manifest.json`,JSON.stringify({style:'reference-cozy-2.5d',assets},null,2)+'\n');
