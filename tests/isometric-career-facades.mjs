import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';
import {build} from 'esbuild';
import './isometric-career-art.mjs';

async function compile(path){
  const result=await build({entryPoints:[path],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});
  return import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].text).toString('base64'));
}
const art=await compile('client/isometric/building-art.ts');
const facade=await compile('client/isometric/career-facade.ts').catch(()=>({}));
// Source data, without importing the entire server and connecting its optional services.
const core=await readFile('game/content.py','utf8'),extra=await readFile('game/extra_content.py','utf8');
const coreIds=[...core.match(/^CAREERS = \(([^)]+)\)/m)[1].matchAll(/"([a-z_]+)"/g)].map(m=>m[1]);
const extraIds=[...extra.match(/^NEW_CAREERS = \(([^)]+)\)/m)[1].matchAll(/'([a-z_]+)'/g)].map(m=>m[1]);
const plugins=await readFile('game/careers/__init__.py','utf8');
const pluginIds=[...plugins.split('ORDER = (')[1].split('\n)')[0].matchAll(/^\s*([^#\n]*)/gm)].flatMap(([_,line])=>[...line.matchAll(/'([a-z_]+)'/g)].map(m=>m[1]));
const ids=[...new Set([...coreIds,...extraIds,...pluginIds])];

test('every catalogue profession selects its own full painted exterior',()=>{
  const keys=new Set();
  for(const id of ids){
    assert.equal(art.BUILDING_ART[id],'career-'+id,`${id} loads its own building instead of a shared house with a badge`);
    keys.add(art.BUILDING_ART[id]);
  }
  assert.equal(ids.length,50);assert.equal(keys.size,50);
});

function canvasFactory(){
  const canvases=[];
  const create=()=>{
    const calls=[];
    const context=new Proxy({createLinearGradient:()=>({addColorStop(){}})}, {get(target,key){return target[key]??((...args)=>calls.push([key,...args]));},set(target,key,value){target[key]=value;return true;}});
    const canvas={width:0,height:0,getContext:()=>context,calls};context.canvas=canvas;canvases.push(canvas);return canvas;
  };
  return {create,canvases};
}

test('compositions are reused for the same source, and replaced for a newly loaded source',()=>{
  assert.equal(typeof facade.CareerFacadeCache,'function');
  const factory=canvasFactory(),cache=new facade.CareerFacadeCache(factory.create),source={width:292,height:390};
  const first=cache.get('accounting','office',source);
  assert.equal(first,cache.get('accounting','office',source));assert.equal(factory.canvases.length,1);
  assert.notEqual(first,cache.get('hr_admin','office',source));
  assert.notEqual(first,cache.get('accounting','office',{width:292,height:390}));
  assert.equal(first.width,292);assert.equal(first.height,390);
  assert.equal(first.calls.filter(c=>c[0]==='drawImage').length,1,'original illustration is composited once');
  assert.equal(cache.get('unreleased_career','home',source),null,'unmapped careers use the existing safe fallback');
  assert.equal(factory.canvases.length,3,'unknown IDs cannot grow the cache');
});

test('new painted exteriors pass through without any old roof glaze or floating motif overlay',()=>{
  assert.equal(typeof facade.drawCareerFacade,'function');
  const factory=canvasFactory();
  for(const id of ids){
    const canvas=factory.create();canvas.width=512;canvas.height=430;
    const source={width:512,height:430};
    facade.drawCareerFacade(canvas.getContext('2d'),source,id,'career-'+id);
    assert.deepEqual(canvas.calls,[['drawImage',source,0,0,512,430]],id+' is already complete painted artwork');
    assert.equal(facade.careerFacadeTextureKey(id,'career-'+id),null,'do not create a second composited GPU texture');
  }
});

test('finished exteriors never populate the legacy composition cache',()=>{
  const factory=canvasFactory(),cache=new facade.CareerFacadeCache(factory.create);
  for(const id of ids)assert.equal(cache.get(id,'career-'+id,{width:512,height:512}),null);
  assert.equal(factory.canvases.length,0);
});

test('legacy large source images stay within the per-building texture budget',()=>{
  assert.equal(typeof facade.careerFacadeSize,'function');
  for(const source of [{width:766,height:794},{width:720,height:681},{width:290,height:700}]){
    const size=facade.careerFacadeSize(source);
    assert.ok(size.width<=384&&size.height<=512);
    assert.ok(Math.abs(size.width/size.height-source.width/source.height)<.005);
  }
});

test('texture keys distinguish careers and base sources while unknown IDs stay bounded',()=>{
  assert.equal(typeof facade.careerFacadeTextureKey,'function');
  assert.notEqual(facade.careerFacadeTextureKey('salon','salon'),facade.careerFacadeTextureKey('nail','salon'));
  assert.notEqual(facade.careerFacadeTextureKey('nail','salon'),facade.careerFacadeTextureKey('nail','home'));
  assert.equal(facade.careerFacadeTextureKey('unknown','home'),null);
});
