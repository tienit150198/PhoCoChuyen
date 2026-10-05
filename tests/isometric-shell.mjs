import assert from 'node:assert/strict';
import {isometricHUDModel,isometricHUDHTML,isometricAction} from '../public/js/isometric-shell.js';

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
for(const kind of ['fishing','boat','pool'])assert.match(html,new RegExp(`data-action="isoLeisure" data-kind="${kind}"`),'outdoor activities have semantic controls');

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
assert.match(html,/data-action="isoChat"[^>]*aria-label="Trò chuyện · 104 tin chưa đọc"/,'chat is a named dedicated control with the real unread total');
assert.match(html,/class="iso-chat-unread"[^>]*>99\+</,'the visible unread count is bounded');
assert.match(html,/Trò chuyện/);
html=isometricHUDHTML(isometricHUDModel(state,content,'town',{state:'down',unread:()=>0}),state);
assert.match(html,/data-action="isoChat"/,'the conversation entry stays discoverable while offline');
assert.match(html,/Mất kết nối/);
assert.match(html,/class="iso-chat-unread"[^>]*hidden/,'zero unread messages do not get an empty badge');
for(const [state,label] of [['idle','Chưa kết nối'],['connecting','Đang kết nối'],['off','Không khả dụng']]){
  html=isometricHUDHTML(isometricHUDModel({},content,'town',{state}),{});
  assert.match(html,new RegExp(`<small>${label}</small>`),`chat describes the actual ${state} state`);
}
html=isometricHUDHTML(isometricHUDModel({},content,'town',{state:'open',flags:{chat:false}}),{});
assert.match(html,/<small>Tạm nghỉ<\/small>/,'a disabled chat does not claim to be connected');
html=isometricHUDHTML(isometricHUDModel({},content,'town',{state:'idle'}, {url:''}),{});
assert.match(html,/<small>Chưa khả dụng<\/small>/,'a missing live URL never claims a pending connection');

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
await isometricAction('isoChat',{},null,env);
assert.deepEqual(calls.pop(),['act','liveChat',{}],'the HUD opens the existing real chat route');
await isometricAction('isoOverview',{},null,env);assert.deepEqual(calls.pop(),['overview']);
for(const kind of ['fishing','boat','pool']){
  await isometricAction('isoLeisure',{kind},null,env);
  assert.deepEqual(calls.pop(),['act','leisurePlace',{kind}],'activity uses the existing full-screen location router');
}
assert.equal(await isometricAction('isoLeisure',{kind:'invented'},null,env),false);
assert.equal(calls.some(c=>c[0]==='command'),false);
console.log('isometric-shell: ok');
