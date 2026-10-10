import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import * as look from '../public/js/v4/look.js';
import {SceneFx} from '../public/js/v4/scene-events.js';

const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');
const app=read('public/js/app.js');
const take=(source,start,end)=>{
  const a=source.indexOf(start);assert.notEqual(a,-1,`Missing integration: ${start}`);
  const b=source.indexOf(end,a);assert.notEqual(b,-1,`Missing integration boundary: ${end}`);
  return source.slice(a,b);
};

test('deferred world preserves the latest state, mode and sound wrappers during adoption',()=>{
  const events=[],context=vm.createContext({document:{dispatchEvent:e=>events.push(e)},CustomEvent:class {constructor(type,options){this.type=type;this.detail=options.detail;}}});
  vm.runInContext(take(app,'function isoWorld(){','const world=isoWorld();')+'\nglobalThis.world=isoWorld();',context);
  const w=context.world,calls=[],latest={current:'zpop'};
  w.update({current:'old'},{});w.update(latest,{catalogue:[]});w.setMode('work');w.paused=true;
  const say=w.say;w.say=(...args)=>{calls.push(['sound']);say(...args);};
  w.adopt({setMode:m=>calls.push(['mode',m]),update:s=>calls.push(['state',s]),say:text=>calls.push(['say',text])});
  w.say('Hello');
  assert.equal(w.adopted,true);assert.equal(w.paused,true);
  assert.deepEqual(calls,[['mode','work'],['state',latest],['sound'],['say','Hello']]);
  assert.equal(events[0].detail.mode,'work');
});

test('scene effects started before Phaser loads keep a finite clock through adoption and completion',()=>{
  let now=12000;
  const context=vm.createContext({performance:{now:()=>now}});
  vm.runInContext(take(app,'function isoWorld(){','const world=isoWorld();')+'\nglobalThis.world=isoWorld();',context);
  const w=context.world,fx=new SceneFx();w.fx=fx;
  fx.start(w,{id:'happening',actor:'thief',anim:'snatch',target:'shelf'});
  assert.equal(fx.ev.t0,12);
  now=14500;
  w.adopt({get time(){return now/1000;},plan:()=>({spots:{door:[[0,0]]},customers:[[0,0],[20,20]]}),isPortrait:()=>false});
  assert.equal(w.fx,fx);assert.equal(w.time-fx.ev.t0,2.5);
  fx.finish(w,{won:true});assert.equal(fx.ev.end,14.5);
  now=17500;assert.equal(fx.path(w,w.time-fx.ev.t0),null,'the finished effect can expire normally');
});

test('Escape that closes any dialog never also toggles game pause',()=>{
  const listeners=[],ui={paused:false};let modal=false,disclosure=false;
  const context=vm.createContext({window:{addEventListener:(name,fn,options)=>listeners.push({name,fn,capture:options===true||options?.capture})},
    document:{querySelector:selector=>(selector==='dialog[open]'?modal:disclosure)?{}:null},$:()=>({open:false}),api:{state:{current:'zpop'}},ui,setPaused:value=>{ui.paused=value;}});
  vm.runInContext(take(app,"window.addEventListener('keydown',e=>{if(e.key==='Escape'",'\n// Back in the tab'),context);
  const escape=close=>{
    const event={key:'Escape',defaultPrevented:false};
    for(const l of listeners.filter(l=>l.capture))l.fn(event);
    if(close){modal=false;disclosure=false;} // later shell capture handler or dialog dismissal
    for(const l of listeners.filter(l=>!l.capture))l.fn(event);
  };
  modal=true;escape(true);assert.equal(ui.paused,false,'guide/leisure dismissal is not a pause action');
  modal=true;escape(false);assert.equal(ui.paused,false,'a still-open dialog also owns Escape');
  modal=false;disclosure=true;escape(true);assert.equal(ui.paused,false,'later shell capture dismissal cannot also pause');
  modal=false;escape(false);assert.equal(ui.paused,true,'Escape still pauses the uncovered world');
});

function router(jailed=false){
  const calls=[],api={state:{journey:{story:true,intro:true},jail:jailed?{day:1}:null}};
  const context=vm.createContext({api,isoTownFirst:()=>true,env:()=>({api}),
    iso:{booted:()=>true,openLeisure:async kind=>calls.push(['leisure',kind]),isometricAction:async action=>{calls.push(['iso',action]);return true;}},
    openJail:async()=>calls.push(['jail']),calls});
  const prefix=take(app,'async function handleAction(action,data,el){','  switch(action){')
    .replace("import('./v4/jail.js')",'Promise.resolve({openJail})');
  vm.runInContext(prefix+"calls.push(['fallback',action]);}\nglobalThis.route=handleAction;",context);
  return {route:context.route,calls};
}
test('home returns to the island and leisure uses the shared activity router',async()=>{
  const h=router();await h.route('home',{});await h.route('leisurePlace',{kind:'pool'});
  await h.route('leisurePlace',{kind:'invented'});
  assert.deepEqual(h.calls,[['iso','isoTown'],['leisure','pool']]);
});
test('jailed island destinations reopen the camp while chat remains available',async()=>{
  for(const action of ['home','leisurePlace','isoTown','isoWork','isoCareers','isoMission','isoPrepare','isoApply','isoQueue','isoGo','isoLeisure','isoBag']){
    const h=router(true);await h.route(action,{kind:'fishing',dest:'market'});
    assert.deepEqual(h.calls,[['jail']],action);
  }
  const h=router(true);await h.route('isoChat',{});
  assert.deepEqual(h.calls,[['iso','isoChat']]);
});

test('active fireworks welcome is subscribed before live connects, once per page',async()=>{
  const handlers=new Map(),calls=[];
  const m={live:{on:(type,fn)=>{calls.push(['on',type]);handlers.set(type,fn);}},liveBoot:()=>{
    calls.push(['boot']);handlers.get('welcome')?.({fw:{id:'active-show'}});
  }};
  const context=vm.createContext({env:()=>({}),console,fireworks:{onFireworks:(_env,f)=>calls.push(['fireworks',f.id])}});
  let src=take(app,'function bootLive(m){','\nconst env=');
  src=src.replace("import('./v4/fireworks.js')",'Promise.resolve(fireworks)');
  vm.runInContext(src+'\nglobalThis.boot=bootLive;',context);
  context.boot(m);await Promise.resolve();context.boot(m);await Promise.resolve();
  assert.ok(calls.findIndex(c=>c[1]==='welcome')<calls.findIndex(c=>c[0]==='boot'));
  assert.equal(calls.filter(c=>c[0]==='boot').length,1);
  assert.deepEqual(calls.filter(c=>c[0]==='fireworks'),[['fireworks','active-show']]);
  for(const type of ['auction_outbid','auction_won','wedinvite'])assert.ok(handlers.has(type));
});

test('every enabled live feature can keep a welcome connection open on its own',()=>{
  const src=read('public/js/v4/live.js').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
  for(const flag of ['chat','street','dating','wedding','fair','home','visits','town','kara','bark']){
    const context=vm.createContext({URLSearchParams,location:{search:''},console,clearTimeout(){},clearInterval(){},setInterval(){}});
    vm.runInContext(src+'\npaint=()=>{};deepLink=()=>{};syncFace=()=>{};adoptName=()=>{};globalThis.h={frame,live};',context);
    context.h.frame({t:'welcome',flags:{[flag]:true},me:{pid:'me'}});
    assert.equal(context.h.live.state,'open',flag);assert.equal(context.h.live.me.pid,'me',flag);
    assert.equal(context.h.live.send({t:'ping'}),false,'no synthetic socket is invented');
  }
});

test('cozy portrait markers retain current wardrobe additions and dress layering',()=>{
  assert.equal(typeof look.cozyPortraits,'function');
  look.cozyPortraits(true);
  try{
    assert.equal(look.cozyActive(),true);
    const outfit={...look.defaultLook('female'),hair:'toc_tet',top:'dam_kim_sa',bottom:'quan_cargo',shoes:'sneaker_chunky',acc:'balo_mini',uniform:false,tint:{dam_kim_sa:'mint',quan_cargo:'mint',balo_mini:'mint'}};
    const marker=html=>JSON.parse(decodeURIComponent(/data-cozy-portrait="([^"]+)"/.exec(html)[1]));
    const face=marker(look.portrait(outfit,'female',56,'<Bạn>'));
    for(const slot of look.SLOTS)assert.equal(face.look[slot],outfit[slot],slot);
    assert.match(look.portrait(outfit,'female',56,'<Bạn>'),/aria-label="&lt;Bạn&gt;"/);
    const body=marker(look.figureSVG(outfit,'female'));
    assert.equal(body.look.bottom,look.defaultLook('none').bottom);
    assert.equal(body.look.tint.quan_cargo,undefined);assert.equal(body.look.tint.dam_kim_sa,'mint');
    assert.doesNotMatch(look.figureSVG(outfit,'female',{box:'-20 -20 40 40'}),/data-cozy-portrait/,'item crop keeps current detailed SVG');
  }finally{look.cozyPortraits(false);}
});

test('wardrobe mirror rotation is carried by the cozy portrait marker',()=>{
  look.cozyPortraits(true);
  try{
    const outfit=look.defaultLook('female');
    for(const facing of ['se','sw','nw','ne']){
      const html=look.figureSVG(outfit,'female',{facing});
      const data=JSON.parse(decodeURIComponent(/data-cozy-portrait="([^"]+)"/.exec(html)[1]));
      assert.equal(data.facing,facing);
    }
    const html=look.figureSVG(outfit,'female',{facing:'invalid'});
    assert.equal(JSON.parse(decodeURIComponent(/data-cozy-portrait="([^"]+)"/.exec(html)[1])).facing,'se');
  }finally{look.cozyPortraits(false);}
});

test('island boots before normal sheets and returning saves land there',()=>{
  const predicate=take(app,'const isoTownFirst=','\nsoundsBoot(');
  const api={state:{journey:{story:true,intro:true,gender:'female'}}},context=vm.createContext({api,newInterface:s=>s?.settings?.newInterface!==false});
  vm.runInContext(predicate+'\nglobalThis.first=isoTownFirst;',context);
  assert.equal(context.first(),true);api.state.journey={story:true};assert.equal(context.first(),false);
  api.state.journey={story:false};assert.equal(context.first(),true);
  api.state.settings={newInterface:false};assert.equal(context.first(),false,'classic preference opens the existing home flow');
  assert.ok(app.indexOf('iso.bootShell(env)')<app.indexOf('shell.boot(env())'));
  assert.match(app,/if\(!oauthReturned\)[\s\S]*?if\(deep.get\('social'\)\)[\s\S]*?else if\(!isoTownFirst\(\)\)openSheet\('home'\)/);
  assert.doesNotMatch(app,/import\(`\.\/scenes\/\$\{kindOf\(id\)\}/);
});

test('early boot warms workbenches while renderer assets wait for account preferences',()=>{
  const src=take(read('public/js/boot.js'),'  const hinted=new Set();','  B.response?.then');
  const links=[],paths={'/js/isometric/phaser-world.js':'/js/isometric/phaser-world.js?v=123','/js/careers/zpop.js':'/js/careers/zpop.js?v=456','/js/scenes/teabar.js':'/js/scenes/teabar.js?v=old'};
  vm.runInNewContext(src,{asset:u=>paths[u]||u,store:k=>k==='mnl.warm'?'["/js/scenes/teabar.js","/js/careers/zpop.js"]':'/js/scenes/teabar.js',d:{createElement:()=>({}),head:{append:l=>links.push(l)}}});
  assert.ok(links.some(l=>l.href===paths['/js/careers/zpop.js']));
  assert.equal(links.some(l=>l.href.includes('/scenes/')),false);
  const phaser=links.find(l=>l.href===paths['/js/isometric/phaser-world.js']);
  assert.equal(phaser,undefined,'classic accounts must not download Phaser before bootstrap');
});

test('new player profile lands on the island without silently selecting a career',async()=>{
  const src=read('public/js/v4/journey.js');
  const calls=[],ui={jrGender:'female',jrJob:'zpop'},btn={disabled:false};
  const environment={ui,api:{state:{journey:{}}},cmd:async(action,payload)=>{calls.push([action,payload]);return {ok:true};},act:async()=>assert.fail('intro must not choose a career'),renderSheet:()=>assert.fail('intro must land on the island')};
  const context=vm.createContext({townWanted:()=>false,isoLand:e=>{assert.equal(e,environment);calls.push(['land']);}});
  vm.runInContext(take(src,'export async function journeySubmit(','/** A small line').replace('export ','')+'\nglobalThis.submit=journeySubmit;',context);
  const form={dataset:{jrForm:'start'},querySelector:selector=>selector==='[name="name"]'?{value:'  Mây  '}:btn};
  assert.equal(await context.submit(form,environment),true);
  assert.deepEqual(JSON.parse(JSON.stringify(calls)),[['jr_profile',{name:'Mây',gender:'female'}],['land']]);
  assert.equal(ui.jrJob,null);assert.equal(ui.jrGender,null);
});

test('saved old map preference never mounts the second town canvas',()=>{
  const src=take(read('public/js/v4/journey.js'),"const HOME_KEY='mnl.home';",'/** What the town needs').replace(/^export /gm,'');
  let stored=null;const context=vm.createContext({localStorage:{getItem:()=>stored}});
  vm.runInContext(src+'\nglobalThis.h={homeListFirst,homePref,townOn};',context);
  context.h.homeListFirst();assert.equal(context.h.homePref(),'list');stored='town';
  const env={api:{state:{journey:{story:true,intro:true}},content:{journey:{}}},ui:{homeMode:'town'}};
  assert.equal(context.h.townOn(env),false);
});

test('an island profile can open the career list and wardrobe before choosing its first career',()=>{
  const src=take(read('public/js/v4/journey.js'),'export function journeyHome(','// Hôn nhân').replace('export ','');
  const context=vm.createContext({isoLand:()=>{},townOn:()=>false,introView:()=>'<intro>',homeMain:()=>'<career-list>',WD:{use:()=>({wardrobeView:()=>'<wardrobe>'})}});
  vm.runInContext(src+'\nglobalThis.home=journeyHome;',context);
  const environment={api:{state:{journey:{story:true,intro:false,gender:'female'}},content:{journey:{}}},ui:{jrView:'home'}};
  assert.equal(context.home(environment),'<career-list>');
  environment.ui.jrView='wardrobe';assert.equal(context.home(environment),'<wardrobe>');
  environment.api.state.journey.gender='';assert.equal(context.home(environment),'<intro>');
  environment.api.state.journey.gender='invalid';assert.equal(context.home(environment),'<intro>');
  environment.api.state.journey.gender='female';context.isoLand=null;
  assert.equal(context.home(environment),'<intro>','legacy flow still waits for its career selection');
});

test('current career modules still load their data and workbench while entering from the island',async()=>{
  const calls=[],context=vm.createContext({CAREER_MODULES:['zpop','police'],hasCareerUI:()=>false,
    loadCareerScene:async()=>{},loadCareerModules:async(ids,wait)=>calls.push(['modules',...ids,wait]),api:{careerContent:async id=>calls.push(['content',id])}});
  vm.runInContext(take(app,'const careerAssets=','\nsetCareerData(')+'\nglobalThis.assets=careerAssets;',context);
  await context.assets('zpop',true);
  assert.deepEqual(calls,[['modules','zpop',true],['content','zpop']]);
});
