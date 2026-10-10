/** Package approved imagegen outputs; preserve original sources and alpha. */
import sharp from 'sharp';
import {mkdir,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
const root=process.argv[2];if(!root)throw new Error('Pass the generated image directory');
const sources={
 park:'exec-26c4dea5-12cf-49f9-93eb-d21c0048b00b.png',
 date:'exec-750bc7c7-51f3-48bb-b9ae-28344c66311f.png',
 market:'exec-feb948aa-754e-475a-b709-e0f4a6993484.png',
 wedding:'exec-856347f5-ce18-4de7-b8cc-a60a1f4f9c17.png',
 karaoke:'exec-04fb5c01-6709-4a99-8847-975d31e79207.png',
 pets:'exec-0569388a-9711-4317-96bc-7d13147c3acc.png',
};
const output='public/icons/cozy-v4';await mkdir(output,{recursive:true});
const assets=[];
for(const [name,file] of Object.entries(sources)){
 const source=join(root,file),image=sharp(source),meta=await image.metadata();if(!meta.hasAlpha)throw new Error(name+' needs transparency');
 const {data,info}=await image.resize({width:768,withoutEnlargement:true}).webp({quality:85,alphaQuality:100,effort:6}).toBuffer({resolveWithObject:true});
 const path=`${output}/civic-${name}.webp`;await writeFile(path,data);assets.push({id:`civic-${name}`,source:file,path,width:info.width,height:info.height,bytes:data.length});
}
await writeFile(`${output}/manifest.json`,JSON.stringify({generated:'2026-10-11',tool:'built-in imagegen',assets},null,2)+'\n');
console.log(JSON.stringify(assets,null,2));
