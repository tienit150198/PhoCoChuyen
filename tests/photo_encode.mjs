// B10 (07/10): 3 iPhone commands refused as too large (> 256 KB). The 📸 scene photo (world.snapshot, app.js `photo`)
// and Sửa nhà's room photo (v4/reno.js) asked for WebP, which Safari cannot encode on a canvas: it handed back a PNG,
// often 1 MB at 1080 px. v4/photo-encode.js: WebP when made, else JPEG (never PNG), quality then size stepping down
// until the data URL is at most PHOTO_MAX characters. A fake canvas whose encoded size follows pixels × quality stands
// in for the browser (Chrome: WebP; Safari: no WebP, its PNG answer). Run by tests/test_photo_encode.py.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {encodePhoto,PHOTO_MAX} from '../public/js/v4/photo-encode.js';

const CAP=256*1024;   // server.py: a /api/command body over this is refused (413)
/** A canvas factory: `bpp(type,q)` bytes per pixel of the encoded image; `webp`: whether the browser makes WebP. */
function fakeDoc({webp,bpp}){
  const made=[];
  return {made,createElement(tag){
    assert.equal(tag,'canvas');
    const c={width:0,height:0,fills:[],getContext(){return {set fillStyle(v){c.fills.push(v);},fillRect(){},drawImage(){c.drawn=true;}};},
      toDataURL(type,q){
        const t=type==='image/webp'&&!webp?'image/png':type==='image/jpeg'||type==='image/webp'?type:'image/png';
        const bytes=Math.ceil(c.width*c.height*bpp(t,q));
        const out=`data:${t};base64,`+'A'.repeat(Math.ceil(bytes/3)*4);
        made.push({w:c.width,h:c.height,type:t,q,len:out.length});return out;
      }};
    return c;
  }};
}
// A busy scene: JPEG/WebP about (0.05 + 0.4 q) bytes a pixel, a PNG 2.5 (what Safari sent before).
const scene=(t,q)=>t==='image/png'?2.5:0.05+0.4*q;
const src={width:1600,height:1067};   // the world canvas (any size: drawn 1080 px wide)

for(const [name,webp] of [['Chrome (WebP)',true],['Safari (no WebP)',false]]){
  const doc=fakeDoc({webp,bpp:scene});
  const url=encodePhoto(src,{width:1080,bg:'#efe7d5',doc});
  assert.ok(url,name+': a photo');
  assert.ok(url.length<=PHOTO_MAX,`${name}: ${url.length} ≤ ${PHOTO_MAX}`);
  assert.ok(url.startsWith(webp?'data:image/webp;base64,':'data:image/jpeg;base64,'),name+': WebP, else JPEG');
  assert.ok(!doc.made.some(m=>m.type==='image/png'&&url.startsWith('data:image/png')),'never a PNG');
  assert.equal(doc.made[0].w,1080,'first tried at 1080 px');
  assert.equal(doc.made[0].h,720,'keeping the scene\'s shape');
  assert.ok(doc.made.length>1,'the full-quality 1080 px try was too big: it stepped down');
  // The whole command body (api.js command) stays under the server's cap.
  const body=JSON.stringify({request_id:'00000000-0000-4000-8000-000000000000',expected_revision:123456,career:'tra_da',action:'photo',
    payload:{image:url,title:'Trà đá gốc bàng · Ngày 12'},cv:'1.9.14',known:'x'.repeat(8*400)});
  assert.ok(body.length<CAP,`${name}: body ${body.length} < ${CAP}`);
}
// Quality first, then size: at 1080 px every quality is tried before a smaller canvas.
{
  const doc=fakeDoc({webp:false,bpp:scene});encodePhoto(src,{width:1080,doc});
  const jpeg=doc.made.filter(m=>m.type==='image/jpeg');
  const first=jpeg.findIndex(m=>m.w<1080);
  assert.ok(first>0&&jpeg.slice(0,first).length===5&&jpeg.slice(0,first).every(m=>m.w===1080),'5 qualities at 1080 px, then smaller');
  for(let i=1;i<first;i++)assert.ok(jpeg[i].q<jpeg[i-1].q,'quality steps down');
}
// A very heavy picture (noise): smallest step still fits, or nothing at all, never an oversized one.
{
  const doc=fakeDoc({webp:false,bpp:()=>1.2});
  const url=encodePhoto(src,{width:1080,doc});
  assert.ok(url===null||url.length<=PHOTO_MAX);
  const worse=encodePhoto(src,{width:1080,doc:fakeDoc({webp:false,bpp:()=>9})});
  assert.equal(worse,null,'nothing fits: null (the caller says "chụp lại"), not a 413');
}
// The room photo (reno): an SVG polaroid drawn at 2×, on its paper colour (JPEG has no transparency).
{
  const doc=fakeDoc({webp:false,bpp:scene});
  const url=encodePhoto({naturalWidth:0},{w:620,h:520,width:1240,bg:'#fffdf7',doc});
  assert.ok(url&&url.length<=PHOTO_MAX&&url.startsWith('data:image/jpeg'));
}
// Wiring: both senders use it, and neither falls back to PNG any more.
for(const f of ['public/js/world.js','public/js/v4/reno.js']){
  const src=readFileSync(new URL('../'+f,import.meta.url),'utf8');
  assert.match(src,/encodePhoto\(/,f+' uses encodePhoto');
  assert.doesNotMatch(src,/toDataURL\('image\/png'\)/,f+': no PNG fallback');
}
assert.match(readFileSync(new URL('../public/js/world.js',import.meta.url),'utf8'),/snapshot\(\)\{return encodePhoto\(this\.canvas,\{width:1080/);
console.log('photo encode ok');
