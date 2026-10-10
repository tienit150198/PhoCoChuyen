import assert from 'node:assert/strict';
import test from 'node:test';
import vm from 'node:vm';
import {readFileSync,existsSync} from 'node:fs';

const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');
const path=new URL('../public/js/interface-mode.js',import.meta.url);
const source=existsSync(path)?readFileSync(path,'utf8'):'';
function moduleContext(extra={}){
  const calls=[];
  const context=vm.createContext({console,Promise,WeakMap,location:{reload:()=>calls.push('reload')},
    stylesheet:async path=>calls.push(path),setIconRenderer:fn=>calls.push(fn),kindOf:id=>id,
    isoModule:{bootShell(){}},classicModule:{BobaWorld:class{}},classicIcons:{classicIcon:()=>'<classic>'},...extra});
  const code=source.replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'')
    .replace("import('./iso-boot.js')",'Promise.resolve(isoModule)')
    .replace("import('./boba-world.js')",'Promise.resolve(classicModule)')
    .replace("import('./classic-icons.js')",'Promise.resolve(classicIcons)')
    .replace(/import\(`\.\/scenes\/\$\{kindOf\(id\)\}\.js`\)/g,"Promise.resolve(calls.push('scene:'+id))");
  context.calls=calls;
  vm.runInContext(code+'\nglobalThis.m={'+['newInterface','interfacePromptDue','saveInterface','loadInterface','loadCareerScene','promptInterface'].map(n=>`${n}:typeof ${n}==='undefined'?undefined:${n}`).join(',')+'};',context);
  return {m:context.m,calls,context};
}

test('server preference defaults new, preserves false and has an account-specific one-time prompt',()=>{
  const {m}=moduleContext();assert.equal(typeof m.newInterface,'function','interface preference resolver is available');
  assert.equal(m.newInterface({settings:{}}),true);
  assert.equal(m.newInterface({settings:{newInterface:false}}),false);
  assert.equal(m.interfacePromptDue({settings:{newInterface:true,interfacePromptSeen:false}}),true);
  assert.equal(m.interfacePromptDue({settings:{newInterface:true,interfacePromptSeen:true}}),false);
  assert.equal(m.interfacePromptDue({settings:{newInterface:false,interfacePromptSeen:false}}),false);
});

test('switch saves both flags before reloading, keeping the existing authenticated API',async()=>{
  const {m,calls}=moduleContext();assert.equal(typeof m.saveInterface,'function');
  let finish;const api={state:{settings:{newInterface:true}}};
  const env={api,cmd:(action,payload,options)=>{calls.push([action,payload,options]);return new Promise(resolve=>{finish=resolve;});}};
  const pending=m.saveInterface(env,false);assert.equal(calls.length,1);
  assert.deepEqual(JSON.parse(JSON.stringify(calls[0])),['settings',{newInterface:false,interfacePromptSeen:true},{quiet:true}]);
  finish({ok:true});assert.equal(await pending,true);assert.equal(calls.at(-1),'reload');
});

test('failed settings save leaves the current renderer and preference intact',async()=>{
  const {m,calls}=moduleContext();assert.equal(typeof m.saveInterface,'function');
  const api={state:{settings:{newInterface:true}}};
  assert.equal(await m.saveInterface({api,cmd:async()=>null},false),false);
  assert.equal(api.state.settings.newInterface,true);assert.deepEqual(calls,[]);
});

test('classic load imports its renderer and icons without requesting Phaser or new styles',async()=>{
  const {m,calls,context}=moduleContext();assert.equal(typeof m.loadInterface,'function');
  const loaded=await m.loadInterface({settings:{newInterface:false}});
  assert.equal(loaded.iso,null);assert.equal(loaded.World,context.classicModule.BobaWorld);
  assert.deepEqual(calls,[context.classicIcons.classicIcon]);
  await m.loadCareerScene({settings:{newInterface:false}},'farm');assert.equal(calls.at(-1),'scene:farm');
});

test('new mode loads only the island shell and its styles, leaving legacy scene modules cold',async()=>{
  const {m,calls,context}=moduleContext();assert.equal(typeof m.loadInterface,'function');
  const loaded=await m.loadInterface({settings:{newInterface:true}});
  assert.equal(loaded.iso,context.isoModule);assert.equal(loaded.World,null);
  assert.deepEqual(calls,['/css/isometric.css','/css/cozy-reference.css']);
  await m.loadCareerScene({settings:{newInterface:true}},'farm');assert.equal(calls.length,2);
});

test('Settings offers the named accessible switch and routes it through the mode saver',async()=>{
  const calls=[];const context=vm.createContext({icon:()=>'',esc:String,layoutPref:()=> 'auto',cleanPref:()=> 'auto',townOK:()=>false,
    document:{documentElement:{dataset:{layout:'phone'}}},newInterface:s=>s.settings.newInterface!==false,
    saveInterface:async(_env,on)=>calls.push(on)});
  vm.runInContext(read('public/js/v4/settings.js').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'')+'\nglobalThis.m={settingsView,settingsChange};',context);
  const env={api:{state:{settings:{newInterface:true}}},ui:{setTab:'look'},cmd:async()=>assert.fail('interface setting must use the renderer lifecycle')};
  const html=context.m.settingsView(env);
  assert.match(html,/Giao diện mới/);assert.match(html,/<input[^>]*role="switch"[^>]*data-setting="newInterface"[^>]*checked/);
  const el={dataset:{setting:'newInterface'},checked:false};await context.m.settingsChange(el,env);assert.deepEqual(calls,[false]);
});

function promptDocument(){
  const handlers={},attributes={},focus=[];
  const buttons=['legacy','new'].map(choice=>({dataset:{interface:choice},disabled:false,focus(){doc.activeElement=this;focus.push(choice);}}));
  const status={textContent:''};
  const dialog={open:false,setAttribute:(k,v)=>{attributes[k]=v;},
    addEventListener:(name,fn)=>{handlers[name]=fn;},
    querySelector:s=>s==='[role="status"]'?status:s.includes('legacy')?buttons[0]:buttons[1],
    querySelectorAll:()=>buttons,contains:node=>buttons.includes(node),
    showModal(){this.open=true;},close(){this.open=false;},remove(){this.removed=true;}};
  const back={isConnected:true,focus:()=>focus.push('back')};
  const doc={activeElement:back,createElement:()=>dialog,body:{append(){}},querySelector:()=>null};
  const click=async index=>handlers.click({target:{closest:()=>buttons[index]}});
  return {doc,dialog,buttons,attributes,handlers,status,focus,click};
}

test('first-visit prompt offers classic and keep-new choices, traps focus and acknowledges once',async()=>{
  const h=promptDocument(),{m,calls}=moduleContext({document:h.doc});assert.equal(typeof m.promptInterface,'function');
  const api={state:{settings:{newInterface:true,interfacePromptSeen:false}}};
  const env={api,cmd:async(_action,payload)=>{Object.assign(api.state.settings,payload);return {ok:true};}};
  const done=m.promptInterface(env);
  assert.equal(h.dialog.open,true);assert.equal(h.attributes['aria-modal'],'true');assert.equal(h.attributes['aria-labelledby'],'interfacePromptTitle');
  assert.match(h.dialog.innerHTML,/Bạn có muốn quay về giao diện cũ\?/);assert.match(h.dialog.innerHTML,/Về giao diện cũ/);assert.match(h.dialog.innerHTML,/Giữ giao diện mới/);
  let prevented=false;h.doc.activeElement=h.buttons[1];h.handlers.keydown({key:'Tab',preventDefault:()=>{prevented=true;}});
  assert.equal(prevented,true);assert.equal(h.doc.activeElement,h.buttons[0]);
  await h.click(1);assert.equal(await done,true);assert.equal(h.dialog.removed,true);assert.equal(h.focus.at(-1),'back');
  assert.equal(api.state.settings.interfacePromptSeen,true);assert.deepEqual(calls,[]);
  h.dialog.removed=false;assert.equal(await m.promptInterface(env),true);assert.equal(h.dialog.removed,false,'seen prompt never opens again');
});

test('return-to-classic prompt button saves preference before reloading',async()=>{
  const h=promptDocument(),{m,calls}=moduleContext({document:h.doc});assert.equal(typeof m.promptInterface,'function');
  const api={state:{settings:{newInterface:true}}};
  const done=m.promptInterface({api,cmd:async(_action,payload)=>{Object.assign(api.state.settings,payload);return {ok:true};}});
  await h.click(0);assert.equal(await done,false);assert.equal(api.state.settings.newInterface,false);assert.deepEqual(calls,['reload']);
});

test('failed prompt save stays open and Escape can retry keeping the new interface',async()=>{
  const h=promptDocument(),{m}=moduleContext({document:h.doc});assert.equal(typeof m.promptInterface,'function');
  let succeed=false;const api={state:{settings:{newInterface:true}}};
  const done=m.promptInterface({api,cmd:async(_action,payload)=>{if(!succeed)return null;Object.assign(api.state.settings,payload);return {ok:true};}});
  await h.click(0);assert.equal(h.dialog.open,true);assert.match(h.status.textContent,/Chưa lưu/);assert.equal(h.buttons[0].disabled,false);
  succeed=true;await h.handlers.cancel({preventDefault(){}});assert.equal(await done,true);assert.equal(api.state.settings.newInterface,true);
});

test('the first page does not statically load either renderer or new interface styles',()=>{
  const app=read('public/js/app.js'),boot=read('public/js/boot.js'),html=read('public/index.html');
  assert.doesNotMatch(app,/^import .*from '\.\/(?:iso-boot|boba-world)\.js'/m);
  assert.match(app,/await loadInterface\(api.state\)/);
  assert.doesNotMatch(boot,/modulepreload[^\n]*phaser-world|const u=asset\('\/js\/isometric\/phaser-world\.js'\)/);
  assert.doesNotMatch(html,/<link[^>]*href="\/css\/(?:isometric|cozy-reference)\.css"/);
});

test('legacy map remains available until the island supplies its own map',()=>{
  const src=read('public/js/v4/journey.js'),start=src.indexOf("const HOME_KEY='mnl.home';"),end=src.indexOf('/** What the town needs',start);
  const context=vm.createContext({localStorage:{getItem:()=>null},document:{createElement:()=>({getContext:()=>({})})},ResizeObserver:class{}});
  vm.runInContext(src.slice(start,end).replace(/^export /gm,'')+'\nglobalThis.m={townOK,onIsoLand,homeListFirst};',context);
  assert.equal(context.m.townOK(),true);context.m.homeListFirst();context.m.onIsoLand(()=>{});assert.equal(context.m.townOK(),false);
});

test('activity cameras start in the selected interface while preserving a deliberate farm camera',()=>{
  for(const newMode of [false,true]){
    const context=vm.createContext({document:{documentElement:{dataset:{game:newMode?'isometric':'classic'}}},globalThis:null,HOME:{}});
    context.globalThis=context;
    for(const [file,name,property,oldValue,newValue,end] of [
      ['pilot_fly.js','F','view','cockpit','outside','\nconst S='],
      ['delivery_drive.js','S','view','firstperson','isometric','\nexport'],
      ['farm_walk.js','W','cam','fp','iso','\nconst'],
    ]){
      const src=read('public/js/careers/'+file),start=src.indexOf('const '+name+'={');
      const declaration=src.slice(start,src.indexOf('};',start)+2);
      const c=vm.createContext({document:context.document,HOME:{},Set,performance:{now:()=>0},globalThis:{document:context.document}});
      vm.runInContext(declaration+'\nglobalThis.value='+name+'.'+property+';',c);
      assert.equal(c.globalThis.value,newMode?newValue:oldValue,file);
    }
    const farm=read('public/js/careers/farm.js');
    const start=farm.indexOf('  x.ui.fvCam??='),line=farm.slice(start,farm.indexOf('\n',start));
    for(const saved of [undefined,'iso','fp','tp']){
      const x={ui:{},api:{state:{settings:{newInterface:newMode}}}};
      vm.runInNewContext(line,{x,prefs:()=>({cam:saved}),document:context.document,newInterface:s=>s.settings.newInterface!==false});
      assert.equal(x.ui.fvCam,saved||(newMode?'iso':'fp'));
    }
  }
});

test('classic icons retain the original single-stroke artwork',async()=>{
  const {classicIcon}=await import('../public/js/classic-icons.js');
  const {icon,setIconRenderer}=await import('../public/js/icons.js');
  const {illustratedIcon}=await import('../public/js/illustrated-icons.js');
  try{setIconRenderer(classicIcon);assert.equal(icon('settings',22),classicIcon('settings',22));assert.match(icon('settings'),/stroke="currentColor"/);}
  finally{setIconRenderer(illustratedIcon);}
  assert.equal(icon('settings',22),illustratedIcon('settings',22));
});
