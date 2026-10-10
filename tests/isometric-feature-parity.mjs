import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import vm from 'node:vm';
import ts from 'typescript';
import {wordsFor} from '../public/js/scenes/vocabulary.js';
import {townUtilityGroups} from '../public/js/isometric/town-utilities.js';

const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');
const layout=JSON.parse(read('game/town_layout.json'));
const legacy=['mother_baby','pharmacy','accounting','customer_care','teacher','tour_guide','milk_tea'];
const appText=process.env.PARITY_SOURCE_REF?execFileSync('git',['show',process.env.PARITY_SOURCE_REF+':public/js/app.js'],{encoding:'utf8'}):read('public/js/app.js');
const ast=(path)=>ts.createSourceFile(path,path==='public/js/app.js'?appText:read(path),ts.ScriptTarget.Latest,true,ts.ScriptKind.JS);
function declarations(path,names){
  const source=ast(path),out=[];
  for(const node of source.statements){
    if(ts.isFunctionDeclaration(node)&&names.includes(node.name?.text))out.push(node.getText(source).replace(/^export /,''));
    if(ts.isVariableStatement(node))for(const d of node.declarationList.declarations)if(names.includes(d.name.getText(source)))out.push('const '+d.getText(source)+';');
  }
  return out.join('\n');
}
const air=vm.runInNewContext(declarations('public/js/careers/air_kit.js',['nav'])+';({nav})');
const modules={};
for(const id of layout.careerOrder.filter(id=>!legacy.includes(id))){
  const path='public/js/careers/'+id+'.js';assert.ok(existsSync(new URL('../'+path,import.meta.url)),id+' has its real career UI');
  let source=ast(path),module=source.statements.find(ts.isExportAssignment)?.expression;
  if(module&&ts.isCallExpression(module)&&module.expression.getText(source)==='officeWork'){
    source=ast('public/js/careers/office_work.js');
    module=source.statements.find(node=>ts.isFunctionDeclaration(node)&&node.name?.text==='officeWork')?.body?.statements.find(ts.isReturnStatement)?.expression;
  }
  assert.ok(module&&ts.isObjectLiteralExpression(module),id+' exports its workbench');
  const members=module.properties.filter(p=>['dock','nav'].includes(p.name?.getText(source)));
  modules[id]=vm.runInNewContext('({'+members.map(p=>p.getText(source)).join(',')+'})',{air,AIR:{}});
}
const appSource=declarations('public/js/app.js',['sceneActions','navItems','stockBadge','dockItems','railHTML','groupBadge',
  'RAIL_MAIN','RAIL_GROUPS','RAIL_GROUPED','RAIL_NOTE','ACC_CAREERS','railItem','railMain','badgeHTML']);
const optionalJourney={garage:{},gadgets:{},pets:{},spend:{},lux:{},abroad:{},deco:{},household:{}};
const optionalContent={quay:{},auction:{},certs:{}};
const enabledLive={welcomed:true,flags:{street:true,dating:true,wedding:true,kara:true,bark:true}};
function harness(id,{mode='town',interfaceMode='new',screen='phone',full=false}={}){
  const state={current:id,journey:{story:true,home:{}},careers:{[id]:{life:{},ops:{},feed:[],tasks:[]}}};
  if(full){Object.assign(state.journey,optionalJourney);Object.assign(state,{marriage:{spouse:{}},rui:{},fair:{show:true,dog:{},knife:{},scratch:{},photo:{}}});state.careers[id].job={required:true,status:'hired'};}
  const ui={view:null,railGroup:null},root={dataset:{game:interfaceMode==='new'?'isometric':'classic',sceneMode:mode,layout:screen},classList:{contains:()=>false}};
  const context=vm.createContext({api:{state,content:{journey:full?optionalContent:{}}},ui,world:{mode},iso:{booted:()=>interfaceMode==='new'},
    newInterface:()=>interfaceMode==='new',document:{documentElement:root},career:()=>id,room:()=>state.careers[id],
    meta:()=>({icon:'briefcase',work:'Công việc',station:'Bàn làm việc'}),plugin:()=>!legacy.includes(id),EXT:['teacher','tour_guide','milk_tea'],
    careerUI:cid=>modules[cid],careerContext:()=>({}),env:()=>({}),wordsFor,layout:()=>screen,esc:String,icon:()=>'',
    lowOpen:()=>0,feedUnread:()=>false,openSituation:()=>null,L:{inc:{},people:{},live:full?{m:{live:enabledLive,liveNav:()=>['liveChat','chat','Chat'],dateNav:()=>['liveDate','heart','Hẹn hò']}}:{}},boardUnread:()=>0,needsJob:()=>false,
    certBadge:()=>0,quayBadge:()=>0,crates:()=>({ready:[]}),lowItems:()=>[]});
  vm.runInContext(appSource+';globalThis.routes={sceneActions,navItems,dockItems,railHTML};',context);
  return {state,ui,...context.routes};
}
const buttons=html=>[...html.matchAll(/<button\b([^>]*)>/g)].map(([,attrs])=>({action:attrs.match(/data-action="([^"]+)"/)?.[1],hidden:/\bhidden\b/.test(attrs)}));

test('town More exposes every real career dock action on phone, tablet and desktop while the dock is hidden',()=>{
  for(const id of layout.careerOrder)for(const screen of ['phone','tablet','desktop']){
    const app=harness(id,{screen}),visible=new Set(buttons(app.railHTML(app.state.careers[id])).filter(x=>!x.hidden).map(x=>x.action));
    for(const [action] of app.dockItems())assert.ok(visible.has(action),`${screen} ${id}: ${action} must remain reachable from town More`);
  }
});

test('phone work and classic layouts keep visible dock entries out of More duplicates',()=>{
  for(const id of layout.careerOrder)for(const opts of [{mode:'work'},{interfaceMode:'classic'}]){
    const app=harness(id,opts),visible=new Set(buttons(app.railHTML(app.state.careers[id])).filter(x=>!x.hidden).map(x=>x.action));
    for(const [action] of app.dockItems())assert.equal(visible.has(action),false,`${id}: ${action} stays on its visible dock`);
  }
});

test('aircrew keep their flight log and omit the shop book in every interface',()=>{
  for(const id of ['pilot','flight_attendant'])for(const mode of ['town','work']){
    const app=harness(id,{mode}),nav=app.navItems(app.state.careers[id]);
    assert.ok(nav.some(([action])=>action==='prices'));
    assert.equal(nav.some(([action])=>action==='operations'),false);
  }
});

function actionsHarness({isometric=true,jailed=false}={}){
  const calls=[],ui={},api={state:{jail:jailed}},context=vm.createContext({api,ui,
    iso:isometric?{booted:()=>true,isometricAction:async action=>{calls.push(['iso',action]);return true;}}:null,
    isoTownFirst:()=>true,env:()=>({api,ui}),openSheet:(...args)=>calls.push(['sheet',...args]),
    room:()=>({ops:{}}),openJail:()=>calls.push(['jail']),cmd:()=>assert.fail('navigation cannot write game state')});
  const source=declarations('public/js/app.js',['handleAction']).replace("(await import('./v4/jail.js')).openJail",'openJail');
  vm.runInContext(source+';globalThis.handle=handleAction;',context);
  return {calls,handle:context.handle};
}

test('legacy Home and both change-career entries open the chooser while isoTown returns to the island',async()=>{
  const x=actionsHarness(),switcher={classList:{contains:cls=>cls==='career-switch'}};
  await x.handle('home',{},switcher);await x.handle('home',{},null);await x.handle('isoTown',{},null);
  assert.deepEqual(x.calls,[['iso','isoCareers'],['iso','isoCareers'],['iso','isoTown']]);
  const classic=actionsHarness({isometric:false});await classic.handle('home',{},switcher);
  assert.equal(classic.calls[0][0],'sheet');assert.equal(classic.calls[0][1],'home');
});

test('the jail boundary remains ahead of all island navigation including change-career',async()=>{
  const x=actionsHarness({jailed:true}),switcher={classList:{contains:()=>true}};
  const actions=['home','leisurePlace','isoTown','isoWork','isoCareers','isoMission','isoPrepare','isoApply','isoQueue','isoGo','isoLeisure','isoBag'];
  for(const action of actions)await x.handle(action,{},switcher);
  assert.deepEqual(x.calls,actions.map(()=>['jail']));
});

test('shared core sheets dispatch identically in classic and 2.5D without game commands',async()=>{
  const routes=['prepare','prices','workshop','passport','town','people','phone','queue','decor','settings','album','summary','event','status','operations','staff','finance','security','property'];
  const classic=actionsHarness({isometric:false}),isometric=actionsHarness();
  for(const action of routes){await classic.handle(action,{},null);await isometric.handle(action,{},null);}
  assert.equal(isometric.calls.length,routes.length);
  assert.deepEqual(JSON.parse(JSON.stringify(isometric.calls)),JSON.parse(JSON.stringify(classic.calls)));
});

const inventoryPath=new URL('../docs/qa/isometric-feature-parity.json',import.meta.url);
const inventory=JSON.parse(readFileSync(inventoryPath,'utf8'));
const catalogue=JSON.parse(execFileSync(process.env.PYTHON||'python',['-c',
  'import json; from game.content import CAREERS,CATALOG; print(json.dumps([{"id":c["id"],"name":c.get("name",c["id"])} for c in CATALOG if c["id"] in CAREERS]))'],{encoding:'utf8'}));
const utilityState={journey:{story:true,...optionalJourney},marriage:{spouse:{}},rui:{},fair:{show:true,dog:{},knife:{},scratch:{},photo:{}}};
const utilityRoutes=townUtilityGroups(utilityState,{journey:optionalContent},enabledLive).flatMap(group=>group.items.map(item=>({id:item.id,action:item.action,data:item.actionData||{},group:group.id})));
const careerRows=catalogue.map(({id,name})=>{
  const x=harness(id,{full:true}),room=x.state.careers[id];
  // app.js registers every plugin plus these two modernized base careers, and
  // jobView dispatches to the registered module before its legacy fallback.
  const module='public/js/careers/'+id+'.js',workbench=!legacy.includes(id)||['mother_baby','milk_tea'].includes(id)?module:['teacher','tour_guide'].includes(id)?'public/js/experience-ui.js':'public/js/desk.js';
  return {id,name,door:'career:'+id,workbench,
    sceneActions:x.sceneActions().map(([a])=>a),menuActions:x.navItems(room).map(([a])=>a),phoneDock:x.dockItems().map(([a])=>a),
    presentation:'shared-sheet',verification:'behavioral-routing',transactions:'not-executed'};
});
const legacyMenuActions=[...new Set(careerRows.flatMap(c=>[...c.sceneActions,...c.menuActions]))].sort();
if(process.env.UPDATE_ISOMETRIC_PARITY==='1'){
  Object.assign(inventory,JSON.parse(JSON.stringify({careers:careerRows,utilityRoutes,legacyMenuActions})));
  writeFileSync(inventoryPath,JSON.stringify(inventory,null,2)+'\n');
}

test('inventory enumerates all 50 server careers, their real menu/dock variants and current utility routes',()=>{
  assert.equal(catalogue.length,50);
  assert.deepEqual([...catalogue.map(c=>c.id)].sort(),[...layout.careerOrder].sort());
  assert.equal(careerRows.length,inventory.careers.length);
  for(const [index,row] of careerRows.entries())assert.deepEqual(JSON.parse(JSON.stringify(row)),inventory.careers[index],row.id+' retains its actual scene, menu and phone dock');
  assert.deepEqual(utilityRoutes,inventory.utilityRoutes);
  assert.deepEqual(legacyMenuActions,inventory.legacyMenuActions);
  assert.equal(new Set(utilityRoutes.map(x=>x.id)).size,utilityRoutes.length);
});

test('every legacy top-level entry belongs to a documented feature family with existing source evidence',()=>{
  const covered=new Set(inventory.features.flatMap(f=>f.actions));
  for(const action of legacyMenuActions)assert.ok(covered.has(action),'unclassified legacy entry: '+action);
  for(const feature of inventory.features){
    assert.ok(feature.availability&&feature.isoEntry&&feature.subfeatures.length,feature.id+' records entry, eligibility and subfeatures');
    for(const path of feature.evidence)assert.ok(existsSync(new URL('../'+path,import.meta.url)),feature.id+' source exists: '+path);
  }
});
