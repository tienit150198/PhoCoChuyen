import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';
import {build} from 'esbuild';

async function compile(path){
  const result=await build({entryPoints:[path],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
  return import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].text).toString('base64'));
}
const registry=await compile('client/isometric/career-art.ts');
const manifest=await compile('client/isometric/asset-manifest.ts');
const art=await compile('client/isometric/building-art.ts');
const layout=JSON.parse(await readFile('game/town_layout.json','utf8'));

test('50 career exteriors have separate files, architectural briefs and trade names',()=>{
  assert.ok(registry.CAREER_ART,'dedicated career artwork registry exists');
  const entries=Object.values(registry.CAREER_ART);
  assert.equal(entries.length,50);
  assert.deepEqual(entries.map(a=>a.career).sort(),[...layout.careerOrder].sort());
  for(const a of entries){
    assert.equal(a.key,'career-'+a.career);
    assert.equal(a.src,'/icons/careers-v1/'+a.career+'.webp');
    assert.ok(a.tradeName.length>=3,a.career+' has a readable trade name');
    assert.ok(a.architecture.length>=75,a.career+' specifies a whole building, not only a badge');
    assert.equal(registry.CAREER_ASSETS[a.key],a.src);
    assert.equal(art.BUILDING_ART[a.career],a.key);
    assert.equal(registry.isCareerArtKey(a.key),true);
  }
  for(const field of ['key','src','architecture','tradeName'])assert.equal(new Set(entries.map(a=>a[field])).size,50,field+' is unique');
  for(const unknown of ['home','career-unknown','career-__proto__','__proto__','constructor'])assert.equal(registry.isCareerArtKey(unknown),false);
});

test('every finished illustration has a bounded front-facade sign without an added floating panel',()=>{
  assert.ok(registry.CAREER_ART);
  for(const a of Object.values(registry.CAREER_ART)){
    const s=a.sign;
    assert.deepEqual(art.FACADE_SIGNS[a.key],s);
    for(const key of ['x','y','width','height','angle'])assert.ok(Number.isFinite(s[key]),a.career+' '+key);
    assert.ok(s.width>.10&&s.width<.55&&s.height>.025&&s.height<.15,a.career+' usable name board; the lighthouse has a narrow cottage sign');
    assert.ok(s.x-s.width/2>0&&s.x+s.width/2<1);
    assert.ok(s.y-s.height/2>.1&&s.y+s.height/2<.8);
    assert.ok(Math.abs(s.angle)<.6);
    assert.notEqual(s.panel,true,'use the name board already painted on '+a.career);
  }
});

test('the shared load manifest includes each painted career plus all existing fallbacks and civic art',()=>{
  assert.ok(manifest.ISOMETRIC_ASSETS,'world and previews share one URL manifest');
  for(const [key,url] of Object.entries(registry.CAREER_ASSETS))assert.equal(manifest.ISOMETRIC_ASSETS[key],url);
  for(const [key,url] of Object.entries({home:'/icons/isometric/home.webp',grocery:'/icons/isometric/grocery.webp',office:'/icons/cozy-v3/office.webp',pharmacy:'/icons/cozy-v2/pharmacy.webp',gazebo:'/icons/cozy-v3/park-gazebo.webp','pool-map':'/icons/cozy-v3/town-pool.webp',fairgrounds:'/icons/cozy-v5/fairgrounds.webp'}))assert.equal(manifest.ISOMETRIC_ASSETS[key],url,key+' stays available');
  assert.equal(art.BUILDING_ART.garage,'garage','non-catalogue garage remains a valid fallback');
});

test('the full set has a mobile decoded-texture budget with no second career composition copy',()=>{
  assert.ok(registry.CAREER_ART_BUDGET);
  const b=registry.CAREER_ART_BUDGET;
  assert.equal(b.maxEdge,512);
  assert.ok(Object.keys(registry.CAREER_ART).length*b.maxEdge*b.maxEdge*4<=b.maxDecodedBytes);
  assert.ok(b.maxDecodedBytes<=64*1024*1024,'all 50 decoded exteriors fit within 64 MiB');
  assert.ok(b.maxAssetBytes<=256*1024&&b.maxTotalBytes<=10*1024*1024,'download budget is explicit');
});
