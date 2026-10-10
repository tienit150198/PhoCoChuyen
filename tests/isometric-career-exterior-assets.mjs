// Run after generating the 50 paintings. This deliberately fails on missing
// files; metadata alone cannot count as completed artwork.
import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import sharp from 'sharp';
import {build} from 'esbuild';

const result=await build({entryPoints:['client/isometric/career-art.ts'],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
const {CAREER_ART,CAREER_ART_BUDGET:b}=await import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].text).toString('base64'));

test('all 50 delivered paintings are transparent, distinct and within the texture/download budgets',async()=>{
  let totalBytes=0,decodedBytes=0;
  const hashes=new Set(),failures=[];
  for(const a of Object.values(CAREER_ART)){
    try{
      const bytes=await readFile('public'+a.src),meta=await sharp(bytes).metadata();
      assert.equal(meta.format,'webp',a.career+' has a real WebP file');
      assert.ok(meta.hasAlpha,a.career+' retains transparency');
      assert.ok(meta.width>0&&meta.width<=b.maxEdge&&meta.height>0&&meta.height<=b.maxEdge,a.career+' is trimmed within 512px, without requiring a square');
      assert.ok(bytes.length<=b.maxAssetBytes,a.career+' individual download budget');
      const {data,info}=await sharp(bytes).ensureAlpha().raw().toBuffer({resolveWithObject:true});
      let clear=0,painted=0;
      for(let i=3;i<data.length;i+=4){if(data[i]<16)clear++;if(data[i]>127)painted++;}
      assert.ok(clear>info.width*info.height*.02,a.career+' has a genuinely clear background');
      assert.ok(painted>info.width*info.height*.05,a.career+' has visible painted architecture');
      const hash=createHash('sha256').update(String(info.width)+':'+info.height+':').update(data).digest('hex');
      assert.ok(!hashes.has(hash),a.career+' does not reuse another finished building image');
      hashes.add(hash);totalBytes+=bytes.length;decodedBytes+=meta.width*meta.height*4;
    }catch(error){failures.push(a.career+': '+error.message);}
  }
  assert.deepEqual(failures,[],'each registry entry must ship its own finished painting');
  assert.equal(hashes.size,50);
  assert.ok(totalBytes<=b.maxTotalBytes,'all painted exteriors fit the download budget');
  assert.ok(decodedBytes<=b.maxDecodedBytes,'all painted exteriors fit the decoded GPU budget');
});

test('measured name areas keep text ink on opaque, light painted boards in all 50 actual assets',async()=>{
  const luminance=rgb=>rgb.map(v=>{const n=v/255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4;}).reduce((sum,n,i)=>sum+n*[.2126,.7152,.0722][i],0);
  const ink=luminance([0x68,0x47,0x2e]);
  for(const a of Object.values(CAREER_ART)){
    const {data,info}=await sharp('public'+a.src).ensureAlpha().raw().toBuffer({resolveWithObject:true}),s=a.sign;
    const width=s.width*info.width,height=s.height*info.height,cx=s.x*info.width,cy=s.y*info.height;
    assert.ok(width>=45&&height>=12,a.career+' retains a useful text area in the real trimmed image');
    let readable=0,total=0;
    for(const u of [-.4,-.2,0,.2,.4])for(const v of [-.4,0,.4]){
      const dx=u*width,dy=v*height,x=Math.round(cx+dx*Math.cos(s.angle)-dy*Math.sin(s.angle)),y=Math.round(cy+dx*Math.sin(s.angle)+dy*Math.cos(s.angle));
      assert.ok(x>=0&&x<info.width&&y>=0&&y<info.height,a.career+' rotated name ink stays inside its sprite');
      const i=(y*info.width+x)*4,contrast=(luminance([data[i],data[i+1],data[i+2]])+.05)/(ink+.05);
      if(data[i+3]>=230&&contrast>=4)readable++;total++;
    }
    assert.ok(readable/total>=.9,`${a.career}: only ${readable}/${total} ink samples lie on its light painted board`);
  }
});
