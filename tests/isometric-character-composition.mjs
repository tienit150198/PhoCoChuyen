import test from 'node:test';
import assert from 'node:assert/strict';
import sharp from 'sharp';
import {fileURLToPath} from 'node:url';
import * as characters from '../public/js/isometric/character-art.js';

test('atlas crops include complete shoes and exclude the next pose',()=>{
  assert.equal(typeof characters.atlasFrameRect,'function');
  const idle=characters.atlasFrameRect(1024,768,'sw',0),step=characters.atlasFrameRect(1024,768,'sw',1);
  assert.ok(idle.y+idle.h>262,'idle shoes end below the old 256px grid line');
  assert.ok(step.y>262,'the next walking pose must not inherit idle shoe fragments');
});

test('every real atlas pose has eye and head anchors independent of its feet',async()=>{
  assert.equal(typeof characters.characterPose,'function');
  for(const gender of ['male','female'])for(const direction of ['sw','se','nw','ne'])for(let frame=0;frame<3;frame++){
    const rect=characters.atlasFrameRect(1024,768,direction,frame),pose=characters.characterPose(gender,direction,frame);
    const {data,info}=await sharp(fileURLToPath(new URL(`../public/icons/cozy-v2/character-${gender}.webp`,import.meta.url))).ensureAlpha().raw().toBuffer({resolveWithObject:true});
    const alphaAt=([x,y])=>data[(Math.round(y)*info.width+Math.round(x))*4+3];
    assert.ok(pose.head[1]>rect.y&&pose.head[1]<rect.y+rect.h*.6);
    assert.ok(alphaAt(pose.head)>200,`${gender}/${direction}/${frame} head lies in the actual painted sprite`);
    if(direction==='sw'||direction==='se')for(const eye of pose.eyes)assert.ok(alphaAt(eye)>200,'glasses must attach to painted eyes');
  }
});

test('warm cream shirts recolour as fabric, while skin and eye highlights retain their own palette',()=>{
  const palette={hair:'#5b4436',skin:'#f5cfae',top:'#305aab',bottom:'#d36b9f',shoes:'#734532'};
  const shirt=characters.recolourPixel([244,208,179,253],.65,palette,'top');
  assert.ok(shirt[2]>shirt[0]*1.5,'a blue shirt must not turn into peach skin');
  const skin=characters.recolourPixel([243,191,150,255],.65,palette);
  assert.ok(skin[0]>skin[2],'the hand remains warm skin beside a blue sleeve');
  assert.deepEqual(characters.recolourPixel([252,249,245,255],.32,palette),[252,249,245,255]);
});

function recorder(){
  let matrix=[1,0,0,1,0,0];const stack=[],arcs=[];
  const multiply=m=>{const [a,b,c,d,e,f]=matrix,[u,v,w,x,y,z]=m;matrix=[a*u+c*v,b*u+d*v,a*w+c*x,b*w+d*x,a*y+c*z+e,b*y+d*z+f];};
  const c=new Proxy({save(){stack.push([...matrix]);},restore(){matrix=stack.pop();},translate(x,y){multiply([1,0,0,1,x,y]);},scale(x,y){multiply([x,0,0,y,0,0]);},transform(...m){multiply(m);},arc(x,y){arcs.push([matrix[0]*x+matrix[2]*y+matrix[4],matrix[1]*x+matrix[3]*y+matrix[5]]);}}, {get:(o,k)=>o[k]||(()=>{}),set:(o,k,v)=>(o[k]=v,true)});
  return {c,arcs};
}
test('round glasses meet both illustrated eye anchors throughout a walking pose',()=>{
  const {c,arcs}=recorder();
  characters.paintWardrobeOverlay(c,{gender:'male',direction:'sw',look:{acc:'kinh_tron'}},{x:10,y:10,w:100,h:146},{eyes:[[43,61],[69,60]],headX:60,headY:40});
  assert.equal(arcs.length,2);
  for(let i=0;i<2;i++)assert.ok(Math.hypot(arcs[i][0]-[43,69][i],arcs[i][1]-[61,60][i])<.01,`lens ${i} stays on the eye, not relative to the feet: ${arcs[i]}`);
});
test('the same cap remains visible when the street character turns away',()=>{
  let shapes=0;const c=new Proxy({save(){},restore(){},translate(){},scale(){},beginPath(){shapes++;}},{get:(o,k)=>o[k]||(()=>{}),set:(o,k,v)=>(o[k]=v,true)});
  characters.paintWardrobeOverlay(c,{gender:'female',direction:'nw',look:{acc:'mu_bucket'}},{x:10,y:10,w:100,h:146},{headX:60,headY:40});
  assert.ok(shapes>0,'rear view cannot silently drop the worn bucket hat');
});

test('a covering hat reaches above the illustrated bun rather than sitting across it',()=>{
  let y=0,sy=1,top=Infinity;const stack=[];
  const c=new Proxy({save(){stack.push([y,sy]);},restore(){[y,sy]=stack.pop();},translate(_x,v){y+=v*sy;},scale(_x,v){sy*=v;},roundRect(_x,v){top=Math.min(top,y+v*sy);}},{get:(o,k)=>o[k]||(()=>{}),set:(o,k,v)=>(o[k]=v,true)});
  characters.paintWardrobeOverlay(c,{gender:'female',direction:'nw',look:{acc:'mu_bucket'}},{x:10,y:10,w:100,h:146},{headX:60,headY:40});
  assert.ok(top<=7,`hat crown ${top} must cover the source bun above y=7`);
});

test('isolated pixels from an adjacent pose are removed without trimming the connected shoes',()=>{
  assert.equal(typeof characters.cleanAtlasPixels,'function');
  const w=20,h=20,data=new Uint8ClampedArray(w*h*4),put=(x,y)=>{data[(y*w+x)*4+3]=255;};
  for(let y=4;y<19;y++)for(let x=5;x<15;x++)put(x,y);
  put(2,0);put(3,0);put(4,18);
  characters.cleanAtlasPixels(data,w,h);
  assert.equal(data[(0*w+2)*4+3],0,'detached previous-frame shoe disappears');
  assert.equal(data[(18*w+4)*4+3],255,'this frame connected shoe stays intact');
});

test('in-place recoloring is byte-identical to the pixel oracle for real atlas poses and saved palettes',async()=>{
  assert.equal(typeof characters.recolourPixels,'function');
  const palettes=[
    {hair:'#5b4436',skin:'#f5cfae',top:'#305aab',bottom:'#d36b9f',shoes:'#734532'},
    {hair:'#FFFFFF',skin:'#000000',top:'#AbCdEf',bottom:'#091723',shoes:'#fFaA00'},
    {hair:'#101c44',skin:'#ac764c',top:'#882277',bottom:'#0088aa',shoes:'#dddddd'},
    {hair:'invalid',skin:'#abc',top:'',bottom:null,shoes:undefined},
  ];
  for(const gender of ['male','female']){
    const atlas=fileURLToPath(new URL(`../public/icons/cozy-v2/character-${gender}.webp`,import.meta.url));
    for(const direction of ['sw','se','nw','ne'])for(let frame=0;frame<3;frame++){
      const rect=characters.atlasFrameRect(1024,768,direction,frame);
      const {data:source,info}=await sharp(atlas).extract({left:rect.x,top:rect.y,width:rect.w,height:rect.h}).resize({width:108}).ensureAlpha().raw().toBuffer({resolveWithObject:true});
      const {width,height}=info;
      // Fractional anchors and inclusive edges exercise the exact production
      // torso predicate, including offsets from the cropped source pose.
      const bodies=[undefined,{x:6,y:8,topX:width*.51+6,topY:height*.56+8,hemY:height*.82+8,halfWidth:width*.21}];
      for(const palette of palettes)for(const body of bodies){
        const expected=new Uint8ClampedArray(source),actual=new Uint8ClampedArray(source);
        for(let row=0;row<height;row++)for(let col=0;col<width;col++){
          const i=(row*width+col)*4,torso=body&&row+body.y>=body.topY+2&&row+body.y<=body.hemY&&Math.abs(col+body.x-body.topX)<=body.halfWidth;
          expected.set(characters.recolourPixel(Array.from(source.subarray(i,i+4)),row/height,palette,torso?'top':''),i);
        }
        assert.equal(characters.recolourPixels(actual,width,height,palette,body),actual,'reuse the RGBA buffer');
        assert.deepEqual(actual,expected,`${gender}/${direction}/${frame}: every RGB and alpha byte must match the oracle`);
      }
    }
  }
});

