/** Slice the generated eight-building atlas into individually lazy-loaded sprites. */
import sharp from 'sharp';
import {mkdir,writeFile} from 'node:fs/promises';
const source='docs/cozy-reference-assets/town-buildings-source.png';
const names=['florist','salon','office','pet','school','pagoda','airport','market'];
await mkdir('public/icons/cozy-v3',{recursive:true});
const meta=await sharp(source).metadata();
if(meta.width!==1536||meta.height!==1024||!meta.hasAlpha)throw Error('Expected transparent 1536×1024 atlas');
const manifest=[];
for(const [i,id] of names.entries()){
  const cell=await sharp(source).extract({left:i%4*384,top:Math.floor(i/4)*512,width:384,height:512}).png().toBuffer();
  const {data,info}=await sharp(cell).trim({background:'#00000000',threshold:10}).webp({quality:90,alphaQuality:100,effort:6}).toBuffer({resolveWithObject:true});
  const url=`/icons/cozy-v3/${id}.webp`;
  await writeFile('public'+url,data);manifest.push({id,url,width:info.width,height:info.height,bytes:data.length});
}
await writeFile('docs/cozy-reference-assets/town-buildings.json',JSON.stringify(manifest,null,2)+'\n');
console.log(manifest);
