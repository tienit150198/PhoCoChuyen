/** Production packaging of generated RGBA artwork; never modifies source paintings. */
import sharp from 'sharp';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
const rows=JSON.parse(await readFile('output/career-art-20261011/sources.json','utf8'));
await mkdir('public/icons/careers-v1',{recursive:true});
const results=[];
for(const row of rows){
  if(!row.path)continue;
  const source=sharp(row.path),meta=await source.metadata();
  if(!meta.hasAlpha)throw new Error(`${row.id}: source must be transparent`);
  const {data,info}=await source.ensureAlpha().raw().toBuffer({resolveWithObject:true});
  let x0=info.width,y0=info.height,x1=0,y1=0;
  for(let y=0;y<info.height;y++)for(let x=0;x<info.width;x++)if(data[(y*info.width+x)*4+3]>12){x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y);}
  if(x1<=x0||y1<=y0)throw new Error(`${row.id}: empty alpha`);
  x0=Math.max(0,x0-3);y0=Math.max(0,y0-3);x1=Math.min(info.width-1,x1+3);y1=Math.min(info.height-1,y1+3);
  const target=`public/icons/careers-v1/${row.id}.webp`;
  const output=await sharp(row.path).extract({left:x0,top:y0,width:x1-x0+1,height:y1-y0+1}).resize({width:512,height:512,fit:'inside',withoutEnlargement:true}).webp({quality:86,alphaQuality:100,effort:5}).toFile(target);
  results.push({id:row.id,width:output.width,height:output.height,bytes:output.size,source:{width:info.width,height:info.height,crop:{x0,y0,x1,y1}}});
}
await writeFile('output/career-art-20261011/packaged.json',JSON.stringify(results,null,2)+'\n');
console.log(`${results.length}/50 career paintings packaged: ${(results.reduce((s,r)=>s+r.bytes,0)/1024/1024).toFixed(2)} MiB`);
