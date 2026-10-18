import assert from 'node:assert/strict';
import {isometricHUDModel,isometricHUDHTML,isometricAction,updateIsometricShell} from '../public/js/isometric-shell.js';

const content={catalogue:[{id:'florist',name:'Người bán hoa',place:'Tiệm hoa Mây'}]};
const state={name:'Mây',current:'florist',journey:{story:true,wallet:3373500,life_day:20},careers:{florist:{money:125400,open:true,day:4,active_task:'done',tasks:[
  {id:'done',title:'Đã xong',status:'completed'},
  {id:'ref',title:'Đã chuyển',status:'referred'},
  {id:'cancel',title:'Đã hủy',status:'cancelled'},
  {id:'next',title:'Bó hoa <Mây> & "Nắng"',status:'waiting'},
  {id:'last',title:'Giỏ hoa',status:'working'},
]}}};

let model=isometricHUDModel(state,content,'town');
assert.equal(model.task.id,'next','a finished active_task falls back to the first unfinished job');
assert.equal(model.taskCount,2,'completed, referred, and cancelled jobs are excluded');
assert.deepEqual(model.money,{wallet:3373500,fund:125400});
assert.equal(model.sceneTitle,'Đảo Hoàng Sa');
assert.equal(model.day,20,'story day takes precedence over workplace day');
let html=isometricHUDHTML(model,state);
assert.match(html,/Bó hoa &lt;Mây&gt; &amp; &quot;Nắng&quot;/);
assert.doesNotMatch(html,/<Mây>/);
assert.match(html,/Ví/);assert.match(html,/Quỹ/);
assert.match(html,/3,37tr/);assert.match(html,/125,4k/);
assert.match(html,/3\.373\.500 xu/,'accessible amounts retain the full real value');
assert.doesNotMatch(html,/XP|Kinh nghiệm|level|Đã xong/,'HUD contains neither invented progress nor ended task titles');
assert.match(html,/data-action="isoOverview"[^>]*aria-label="Xem toàn đảo"/,'overview is a clearly labelled camera action');
assert.match(html,/data-action="isoCamera"[^>]*aria-expanded="false"[^>]*aria-controls="isoCameraOptions"/,'small-screen camera controls have an accessible collapsed entry');
assert.match(html,/id="isoCameraOptions"/);
assert.match(html,/id="isoCameraOptions" hidden/,'camera actions are unfocusable while collapsed on every screen size');
const toolsHTML=html.match(/<details class="iso-tools">([\s\S]*?)<\/nav>/)?.[1]||'';
for(const action of ['isoQueue','people','status','isoBag','settings'])assert.ok(toolsHTML.includes(`data-action="${action}"`),`${action} remains available in the compact utilities disclosure`);
assert.match(toolsHTML,/summary[^>]*aria-controls="isoToolsOptions"/,'utilities has a semantic keyboard-operable disclosure');
assert.match(html,/<button type="button" class="iso-go" data-action="isoMission"[^>]*>[\s\S]*?<b>Làm tiếp<\/b><small>Tiệm hoa Mây<\/small>/,'the town has one main button for the next step (owner 18/10)');
assert.doesNotMatch(html,/iso-mission|iso-scene|class="iso-chat"/,'no task chip, "Đang ở" bar or chat card floats over the map');
assert.match(html,/data-action="isoGuide"/,'Guide remains outside utilities');
assert.equal(toolsHTML.includes('data-action="isoGuide"'),false);
const navHTML=html.match(/<nav class="iso-nav"[\s\S]*?<\/nav>/)?.[0]||'';
assert.equal((navHTML.match(/<button/g)||[]).length,3,'bottom navigation: Work, Chat and More');
assert.ok(navHTML.includes('data-action="isoChat"'),'chat is a tab of the bottom bar');
assert.ok(navHTML.includes('data-action="isoMore"'),'the complete existing rail remains reachable');
assert.equal((html.match(/data-action="isoAvatar"/g)||[]).length,1,'the portrait is the single dedicated avatar shortcut');
assert.equal((html.match(/data-action="settings"/g)||[]).length,1,'settings is not duplicated around the map');
{const work=isometricHUDHTML(isometricHUDModel(state,content,'work'),state),workNav=work.match(/<nav class="iso-nav[^"]*"[\s\S]*?<\/nav>/)?.[0]||'';
 assert.equal((workNav.match(/<button/g)||[]).length,4,'inside a workplace: Ra đảo, Work, Chat and More on one bar');
 assert.match(workNav,/data-action="isoTown"[^>]*>[\s\S]*?Ra đảo/);
 assert.doesNotMatch(work,/class="iso-go"/,'inside a workplace the work bar takes over from the main button');}
for(const [room,action,label] of [[{open:false},'isoOpen','Mở ca'],[{open:true,active_task:null,tasks:[]},'isoWork','Vào làm'],[{job:{required:true,status:'applied'}},'isoApply','Xin việc']]){
 const st={...state,careers:{florist:{...state.careers.florist,...room}}};
 assert.match(isometricHUDHTML(isometricHUDModel(st,content,'town'),st),new RegExp(`class="iso-go" data-action="${action}"[^]*?<b>${label}</b>`),`${label}: the main button names the next step`);
}
assert.match(isometricHUDHTML(isometricHUDModel({journey:{story:true,life_day:3}},content,'town'),{}),/class="iso-go" data-action="isoCareers"[\s\S]*?<b>Chọn nghề<\/b>/);
for(const kind of ['fishing','boat','pool'])assert.match(html,new RegExp(`data-action="isoLeisure" data-kind="${kind}"`),'outdoor activities have semantic controls');

const utilityState={...state,rui:{},marriage:{spouse:{name:'An'}},journey:{...state.journey,garage:{},gadgets:{},pets:{},spend:{},lux:{},abroad:{}}};
const utilityContent={...content,journey:{quay:{},auction:{},certs:{}}};
const utilityLive={welcomed:true,flags:{street:true,dating:true,wedding:true,kara:true}};
const utilityHTML=isometricHUDHTML(isometricHUDModel(utilityState,utilityContent,'town',utilityLive),utilityState);
for(const action of ['bank','house','garage','gadgets','pets','spend','spendStyle','lux','luxFw','auction','rui','jrInvest','quay','jrCerts','accountingSchool','historyCourse','abroad','friends','marriage','nhom','social','rank','liveWalk','liveDate','liveWed','liveKara','wedInvite']){
  assert.ok(utilityHTML.includes(`data-action="${action}"`),`${action} is discoverable from the town utilities without opening the work menu`);
}
assert.equal((utilityHTML.match(/class="iso-quick-button"/g)||[]).length,(html.match(/class="iso-quick-button"/g)||[]).length,'restoring utilities adds no floating map buttons');
for(const group of ['services','life','learning','community'])assert.match(utilityHTML,new RegExp(`<details[^>]+data-iso-group="${group}"[^>]*><summary`),'utility groups begin collapsed');
const basicHTML=isometricHUDHTML(isometricHUDModel(state,content,'town'),state);
for(const action of ['garage','gadgets','pets','spend','spendStyle','lux','luxFw','auction','rui','quay','jrCerts','abroad','liveWalk','liveDate','liveWed','liveKara','wedInvite'])assert.equal(basicHTML.includes(`data-action="${action}"`),false,`${action} is hidden until the corresponding server feature is available`);
assert.equal(utilityHTML.includes('data-action="liveBark"'),false,'the removed dog tug-of-war is not offered');
assert.doesNotMatch(utilityHTML,/\bdisabled\b/,'available utilities are real actions, not disabled placeholders');

model=isometricHUDModel({...state,careers:{florist:{...state.careers.florist,active_task:'last'}}},content,'work');
assert.equal(model.task.id,'last');
assert.equal(model.sceneTitle,'Tiệm hoa Mây');

model=isometricHUDModel({name:'Bạn',focus:'florist',journey:{story:true,wallet:-40},careers:state.careers},content,'work');
assert.equal(model.current,null,'a preload focus is not a chosen workplace');
assert.equal(model.mode,'town');
assert.equal(model.task,null);assert.equal(model.money.fund,null);
html=isometricHUDHTML(model,{});
assert.match(html,/Ví/);assert.match(html,/−40/);assert.doesNotMatch(html,/iso-fund/);

assert.equal(isometricHUDModel({},content,'town').taskCount,0,'booting with absent current and room is safe');
assert.equal(isometricHUDModel({},null,'town').current,null,'the catalogue may not have arrived at boot');
assert.equal(isometricHUDModel({...state,journey:{story:false,wallet:60}},content,'town').money.wallet,null,'free play does not invent a personal wallet');
model=isometricHUDModel({...state,careers:{florist:{...state.careers.florist,open:false}}},content,'town');
assert.equal(model.missionAction,'isoPrepare');

const social={state:'open',unread:()=>104};
model=isometricHUDModel(state,content,'town',social);
html=isometricHUDHTML(model,state);
assert.match(html,/data-action="isoChat"[^>]*aria-label="Trò chuyện · Cả phố · Bạn bè · 104 tin chưa đọc"/,'chat is a named dedicated control with the real unread total');
assert.match(html,/class="iso-chat-unread"[^>]*>99\+</,'the visible unread count is bounded');
assert.match(html,/Trò chuyện/);
html=isometricHUDHTML(isometricHUDModel(state,content,'town',{state:'down',unread:()=>0}),state);
assert.match(html,/data-action="isoChat"/,'the conversation entry stays discoverable while offline');
assert.match(html,/Mất kết nối/);
assert.match(html,/class="iso-chat-unread"[^>]*hidden/,'zero unread messages do not get an empty badge');
for(const [state,label] of [['idle','Chưa kết nối'],['connecting','Đang kết nối'],['off','Không khả dụng']]){
  html=isometricHUDHTML(isometricHUDModel({},content,'town',{state}),{});
  assert.match(html,new RegExp(`aria-label="Trò chuyện · ${label}"`),`chat describes the actual ${state} state`);
}
html=isometricHUDHTML(isometricHUDModel({},content,'town',{state:'open',flags:{chat:false}}),{});
assert.match(html,/aria-label="Trò chuyện · Tạm nghỉ"/,'a disabled chat does not claim to be connected');
html=isometricHUDHTML(isometricHUDModel({},content,'town',{state:'idle'}, {url:''}),{});
assert.match(html,/aria-label="Trò chuyện · Chưa khả dụng"/,'a missing live URL never claims a pending connection');
html=isometricHUDHTML(isometricHUDModel({},content,'town',{state:'open',me:{account:false}}),{});
assert.match(html,/aria-label="Trò chuyện · Khách · Chỉ xem"/,'a connected guest sees their actual chat permission at the entry');

const calls=[];
const env={api:{state,content},ui:{},world:{mode:'town',setMode:mode=>calls.push(['mode',mode]),overviewIsland:()=>calls.push(['overview'])},closeSheet:()=>calls.push(['close']),
  openSheet:(view,data)=>calls.push(['sheet',view,data]),act:async (action,data)=>calls.push(['act',action,data]),renderMain:()=>{}};
assert.equal(await isometricAction('isoCareers',{},null,env),true);
assert.deepEqual(calls.pop(),['sheet','home',{homeMode:'list',jrView:'home'}]);
assert.equal(await isometricAction('isoAvatar',{},null,env),true);
assert.deepEqual(calls.pop(),['sheet','home',{jrView:'wardrobe'}]);
await isometricAction('isoBag',{},null,env);
assert.deepEqual(calls.pop(),['act','warehouse',{}],'inventory uses the career-aware existing routing');
await isometricAction('isoMission',{},null,env);
assert.deepEqual(calls.pop(),['act','job',{task:'next'}]);
await isometricAction('isoTown',{},null,env);
assert.deepEqual(calls.slice(-2),[['close'],['mode','town']]);
await isometricAction('isoWork',{},null,env);
assert.deepEqual(calls.slice(-2),[['close'],['mode','work']],'entering a workplace changes no server state');
assert.equal(await isometricAction('unrelated',{},null,env),false);
{const closed={...state,careers:{florist:{...state.careers.florist,open:false}}},log=[];
 const e2={...env,api:{state:closed,content},world:{mode:'town',setMode:mode=>log.push(['mode',mode])},closeSheet:()=>log.push(['close']),act:async (action)=>log.push(['act',action])};
 await isometricAction('isoOpen',{},null,e2);
 assert.deepEqual(log,[['close'],['mode','work'],['act','start'],['act','prepare']],'"Mở ca" opens the shift in one tap; when it cannot, the prepare sheet says why');
 closed.careers.florist.open=true;log.length=0;e2.act=async action=>{log.push(['act',action]);};
 await isometricAction('isoOpen',{},null,e2);
 assert.deepEqual(log.filter(x=>x[0]==='act'),[['act','start']],'an opened shift needs no prepare sheet');}
await isometricAction('isoChat',{},null,env);
assert.deepEqual(calls.pop(),['act','liveChat',{}],'the HUD opens the existing real chat route');
await isometricAction('isoOverview',{},null,env);assert.deepEqual(calls.pop(),['overview']);
assert.equal(await isometricAction('isoCamera',{},null,env),true,'camera disclosure stays local to the HUD');
const beforeCameraClose=calls.length;
await isometricAction('isoCamera',{},null,env);
assert.equal(calls.length,beforeCameraClose,'opening and closing the camera sends no gameplay or API action');
for(const kind of ['fishing','boat','pool']){
  await isometricAction('isoLeisure',{kind},null,env);
  assert.deepEqual(calls.pop(),['act','leisurePlace',{kind}],'activity uses the existing full-screen location router');
}
assert.equal(await isometricAction('isoLeisure',{kind:'invented'},null,env),false);
assert.equal(calls.some(c=>c[0]==='command'),false);
console.log('isometric-shell: ok');

for(const show of [false,true]){
 const st={...state,fair:{show}},m=isometricHUDModel(st,content,'town');
 assert.equal(isometricHUDHTML(m,st).includes('data-action="fair"'),show,'Chợ đen stays discoverable while the server exposes the fair');
}

{
 const before=globalThis.document,appended=[],header={querySelector:()=>null,append:node=>appended.push(node)},hud={dataset:{},contains:()=>false,querySelector:()=>null};
 globalThis.document={documentElement:{dataset:{},classList:{contains:()=>false}},activeElement:null,
  getElementById:id=>id==='isoHUD'?hud:null,querySelector:sel=>sel.startsWith('#sheetContent')?header:null,
  createElement:()=>({dataset:{},setAttribute(){}})};
 try{updateIsometricShell({api:{state:{journey:{story:true,intro:false,gender:'female'}},content:{}},ui:{view:'home',jrView:'home'},world:{mode:'town'}});
 assert.equal(appended.length,1,'a newly profiled island player can close the first career list');assert.equal(appended[0].dataset.action,'isoTown');
 }finally{globalThis.document=before;}
}

// A live chat update replaces HUD markup; an open notebook and its keyboard focus survive.
for(const focused of ['summary','boat','garage']){
 const before=globalThis.document,focuses=[],panels=new Map();
 const makePanels=()=>{
  for(const name of ['iso-tools','iso-outings','iso-outings[data-iso-group="services"]'])panels.set(name,{dataset:name.includes('services')?{isoGroup:'services'}:{},open:false,setAttribute(key){if(key==='open')this.open=true;}});
 };
 makePanels();panels.get('iso-tools').open=true;panels.get('iso-outings').open=true;
 if(focused==='garage'){panels.get('iso-outings').open=false;panels.get('iso-outings[data-iso-group="services"]').open=true;}
 const active={dataset:focused==='summary'?{isoFocus:'iso-tools'}:focused==='garage'?{action:'garage'}:{action:'isoLeisure',kind:'boat'}};
 const hud={dataset:{},contains:el=>el===active,
  set innerHTML(value){this.html=value;makePanels();},
  querySelector(selector){
   if(selector.startsWith('.'))return panels.get(selector.slice(1).replace(':not([data-iso-group])',''));
   return {focus:()=>focuses.push(selector)};
  },querySelectorAll(selector){return selector==='.iso-outings'?[panels.get('iso-outings[data-iso-group="services"]'),panels.get('iso-outings')]:[panels.get(selector.slice(1))].filter(Boolean);}};
 globalThis.document={documentElement:{dataset:{},classList:{contains:()=>false}},activeElement:active,getElementById:id=>id==='isoHUD'?hud:null,
  querySelector:selector=>{const name=selector.match(/^#isoHUD \.(iso-[a-z]+)\[open\]$/)?.[1];return name&&panels.get(name)?.open?panels.get(name):null;}};
 try{
  updateIsometricShell({api:{state:{...state,name:`Live refresh ${focused}`},content},ui:{},world:{mode:'town'}});
  assert.equal(panels.get('iso-tools').open,true,'utilities remain open across live updates');
  assert.equal(panels.get(focused==='garage'?'iso-outings[data-iso-group="services"]':'iso-outings').open,true,'the correct nested utility group remains open across live updates');
  if(focused==='garage')assert.equal(panels.get('iso-outings').open,false,'refresh does not expand an unrelated group');
  assert.equal(hud.dataset.disclosureOpen,'true','live refresh retains the compatible elevated layer for the open utilities');
  assert.deepEqual(focuses,[focused==='summary'?'[data-iso-focus="iso-tools"]':focused==='garage'?'[data-action="garage"]':'[data-action="isoLeisure"][data-kind="boat"]'],'focus returns to the same summary or utility');
 }finally{globalThis.document=before;}
}
