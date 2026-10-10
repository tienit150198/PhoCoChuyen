import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {build} from 'esbuild';
import sharp from 'sharp';

const layout=JSON.parse(readFileSync('game/town_layout.json','utf8'));
async function compiled(path){const result=await build({entryPoints:[path],bundle:true,write:false,format:'esm',platform:'node',logLevel:'silent'});return import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].text).toString('base64'));}
const model=await compiled('client/isometric/model.ts'),trails=await compiled('client/isometric/trail-geometry.ts');
const buildings=model.townBuildings(layout.careerOrder.map(id=>({id}))),nav=model.townNavigation(buildings);
const overlap=(a,b,margin=0)=>a.x0<b.x1+margin&&a.x1>b.x0-margin&&a.y0<b.y1+margin&&a.y1>b.y0-margin;
const distanceToRect=(p,r)=>Math.hypot(Math.max(r.x0-p.x,0,p.x-r.x1),Math.max(r.y0-p.y,0,p.y-r.y1));

test('illustrated community places dispatch existing routes, including the actual park and black market',()=>{
  const expected={walk:['civic-park','liveWalk'],date:['civic-date','liveDate'],fair:['civic-market','fair'],wedding:['civic-wedding','liveWed'],karaoke:['civic-karaoke','liveKara'],bark:['civic-pets','liveBark']};
  for(const [id,[art,action]] of Object.entries(expected)){
    const p=layout.amenities.find(p=>p.id===id);assert.ok(p,`${id} has a real destination`);
    assert.equal(p.art,art);assert.equal(p.action,action);
  }
  assert.equal(layout.amenities.find(p=>p.id==='fair').label,'Chợ đen');
  assert.deepEqual(layout.amenities.find(p=>p.id==='walk').actionData,{place:'congvien'});
  for(const action of ['money','settings','friends','jrInvest','rui'])assert.ok(!layout.amenities.some(p=>p.action===action),'menu '+action+' must not invent a physical destination');
});

test('amenity art reserves distinct solid plots clear of every road ribbon and existing entrance',()=>{
  const art=layout.amenities.filter(p=>p.art);assert.equal(art.length,23);
  const original=[...layout.lots,...layout.commons,...layout.shopLots,...layout.planting];
  const lanes=layout.trails.flatMap((t,i)=>trails.streetProfile(trails.sampleTrailCurve(t.points,t.sampled),t.width,i));
  const entrances=[...layout.lots.map(p=>p.door),...layout.shopLots.map(p=>p.door),...layout.amenities.map(p=>p.at),...layout.commons.map(p=>p.approach)];
  const centers=new Set();
  for(const [i,p] of art.entries()){
    assert.ok(p.artWidth>=250&&p.artWidth<=500,p.id+' has a bounded sprite width');
    assert.ok(p.footprint&&model.insideIsland(p.artAt),p.id+' has a physical plot on the island');
    assert.equal(model.isWalkable(nav,p.artAt),false,p.id+' cannot be walked through');
    const key=JSON.stringify(p.artAt);assert.ok(!centers.has(key),'art cannot stack at the same anchor');centers.add(key);
    for(const other of [...original,...art.slice(0,i)])assert.equal(overlap(p.footprint,other.footprint),false,`${p.id} does not overlap an existing plot`);
    for(const at of entrances)assert.ok(distanceToRect(at,p.footprint)>.14,p.id+' leaves every entrance free');
    for(const point of lanes)assert.ok(distanceToRect(point,p.footprint)>point.radius+.1,p.id+' stays beside the complete road ribbon');
  }
});

test('all amenity approaches remain reachable after reserving artwork plots, including future career lots',()=>{
  for(const place of layout.amenities){
    assert.ok(model.isWalkable(nav,place.at),place.id+' approach stays free');
    const path=model.findRoute(nav,{x:6.2,y:6.2},place.at);assert.ok(path.length,place.id+' has a route');
    assert.deepEqual(path.at(-1),place.at,place.id+' reaches its exact authored approach');
  }
});

test('civic illustrations ship with clear margins and a bounded download size',async()=>{
  const manifest=JSON.parse(readFileSync('public/icons/cozy-v4/manifest.json','utf8'));
  assert.equal(manifest.assets.length,6);
  let bytes=0;
  for(const asset of manifest.assets){
    const buffer=readFileSync(asset.path);bytes+=buffer.length;
    const {data,info}=await sharp(buffer).ensureAlpha().raw().toBuffer({resolveWithObject:true});
    assert.ok(info.width<=768&&info.height<=768,asset.id+' fits a small static texture');
    const alpha=(x,y)=>data[(y*info.width+x)*info.channels+info.channels-1];
    // Allow one alpha quantization level at resized edges (less than 0.4% opacity).
    for(const [x,y] of [[0,0],[info.width-1,0],[0,info.height-1],[info.width-1,info.height-1]])assert.ok(alpha(x,y)<=1,asset.id+' has no opaque background rectangle');
  }
  assert.ok(bytes<1024*1024,'all six civic illustrations stay under 1 MiB');
});
