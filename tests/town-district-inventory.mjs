import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {build} from 'esbuild';
import sharp from 'sharp';
import {hasIcon} from '../public/js/illustrated-icons.js';
import {townUtilityGroups,townServiceAvailable} from '../public/js/isometric/town-utilities.js';

const layout=JSON.parse(readFileSync('game/town_layout.json','utf8'));
const housing=JSON.parse(execFileSync('python',['-c','import json; from game.housing import GROUPS,HOMES; print(json.dumps(dict(groups=[g[0] for g in GROUPS],homes=HOMES)))'],{encoding:'utf8'}));
async function compiled(path){const result=await build({entryPoints:[path],bundle:true,write:false,format:'esm',platform:'node',logLevel:'silent'});return import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].text).toString('base64'));}
const model=await compiled('client/isometric/model.ts'),geometry=await compiled('client/isometric/trail-geometry.ts');
const nav=model.townNavigation(model.townBuildings(layout.careerOrder.map(id=>({id}))));
const state={journey:{story:true,garage:{},pets:{},deco:{},household:{},lux:{},spend:{}},fair:{show:true,dog:{},knife:{},scratch:{},photo:{}}};
const items=(s=state)=>townUtilityGroups(s).flatMap(g=>g.items);

test('each housing group has a separate district and real catalogue membership',()=>{
  const districts=layout.districts.filter(d=>d.housingGroup);
  assert.deepEqual(districts.map(d=>d.housingGroup).sort(),[...housing.groups].sort());
  for(const d of districts){
    assert.deepEqual(d.homeKinds,[...Object.keys(housing.homes).filter(id=>housing.homes[id].group===d.housingGroup)]);
    const gate=layout.amenities.find(p=>p.id===d.id);
    assert.ok(gate&&gate.housingGroup===d.housingGroup,'district has a public entrance');
    assert.equal(gate.action,'house');assert.ok(!gate.actionData?.kind,'district never opens a rental as a purchase');
    for(const other of districts.filter(x=>x!==d))assert.ok(Math.hypot(d.at.x-other.at.x,d.at.y-other.at.y)>15,'neighborhoods are spread out');
    assert.ok(!('residents' in d)&&!('owner' in d),'public catalogue has no invented occupancy');
  }
});

test('fair, race, family and vehicles are distinct existing subviews',()=>{
  const fair=layout.amenities.find(p=>p.id==='fairgrounds'),dog=layout.amenities.find(p=>p.id==='dograce');
  assert.ok(fair&&dog,'both activities have their own approach');
  assert.deepEqual([fair.action,fair.actionData],['fair',{tab:'ring'}]);
  assert.deepEqual([dog.action,dog.actionData],['fair',{tab:'dg'}]);
  assert.match(fair.hint,/Chợ đen/);assert.match(dog.hint,/Chợ đen/);
  for(const [id,action,actionData] of [['garage-bike','garage',{tab:'bike'}],['garage-car','garage',{tab:'car'}],['household','stView',{view:'household'}],['family-children','marriage',{tab:'family',section:'children'}],['pets-adopt','pets',{tab:'adopt'}]]){
    const item=items().find(x=>x.id===id);assert.ok(item,id+' is discoverable');assert.equal(item.action,action);assert.deepEqual(item.actionData,actionData);
  }
  assert.equal(new Set(items().map(x=>x.id)).size,items().length,'utility destinations have unique identities');
});

test('optional subviews only appear when the actual server data is available',()=>{
  assert.equal(townServiceAvailable('fair',{fair:{show:true}},{},{},{tab:'dg'}),false);
  assert.equal(townServiceAvailable('fair',state,{},{},{tab:'dg'}),true);
  assert.equal(townServiceAvailable('fair',{...state,fair:{show:false,dog:{}}},{},{},{tab:'dg'}),false);
  assert.equal(townServiceAvailable('jrEnterHome',{journey:{story:true}}),false);
  assert.equal(townServiceAvailable('jrEnterHome',state),true);
  assert.equal(townServiceAvailable('stView',{journey:{story:true}},{},{},{view:'household'}),false);
  assert.equal(townServiceAvailable('stView',state,{},{},{view:'household'}),true);
  assert.ok(!items({journey:{story:false},fair:{show:false}}).some(x=>['garage','pets','jrEnterHome','homeGuests','stView'].includes(x.action)));
});

test('all new approaches and the painted road network remain inside the shoreline and reachable',()=>{
  for(const p of layout.amenities){assert.ok(model.insideIsland(p.at),p.id+' is on land');assert.ok(model.isWalkable(nav,p.at),p.id+' approach is clear');const path=model.findRoute(nav,{x:6.2,y:6.2},p.at);assert.deepEqual(path.at(-1),p.at,p.id+' is reachable');}
  for(const t of layout.trails){const samples=geometry.sampleTrailCurve(t.points,t.sampled);for(const [i,p] of samples.entries()){assert.ok(model.insideIsland(p),t.id+' is on land');assert.ok(model.isWalkable(nav,p),t.id+' has a free centerline');if(i)assert.ok(model.lineClear(nav,samples[i-1],p),t.id+' has no corner collision');}}
});

test('every discovered service uses an existing illustrated icon',()=>{
  for(const item of items())assert.ok(hasIcon(item.icon),item.id+' has an illustrated icon');
});

test('new illustrations preserve transparency and a bounded static payload',async()=>{
  const manifest=JSON.parse(readFileSync('public/icons/cozy-v5/manifest.json','utf8'));
  assert.equal(manifest.assets.length,6);let bytes=0;
  for(const asset of manifest.assets){
    const buffer=readFileSync(asset.path);bytes+=buffer.length;
    const {data,info}=await sharp(buffer).ensureAlpha().raw().toBuffer({resolveWithObject:true});
    assert.ok(info.width<=768&&info.height<=768);
    const alpha=(x,y)=>data[(y*info.width+x)*info.channels+info.channels-1];
    for(const [x,y]of[[0,0],[info.width-1,0],[0,info.height-1],[info.width-1,info.height-1]])assert.ok(alpha(x,y)<=1,asset.id+' has transparent corners');
    assert.ok(layout.amenities.some(p=>p.art===asset.id),asset.id+' is used by an actual destination');
  }
  assert.ok(bytes<1.25*1024*1024,'six district illustrations stay under 1.25 MiB');
});
