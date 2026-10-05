import assert from 'node:assert/strict';
import {familyView, familyAction,familyRefresh} from '../public/js/v4/family.js';

const child={id:'shared',name:'<Bông>',stage:'Em bé',origin:'adopt',waiting:false,born:'2026-10-04',care_days:1,bond:2,
 needs:{food:65,clean:65,joy:65},owned:['basic'],outfit:'basic',acts:[{id:'milk',name:'Cho bé uống sữa',emoji:'🥛',cost:4,done:false}]};
const family={day:'2026-10-04',clock:'Ngày lịch Việt Nam (UTC+7)',child,copies:[],requests:[{id:7,kind:'home',home:'Nhà tập thể',mine:false}],
 ready:true,can_invite:true,can_leave:false,together:false,home_name:'Nhà tập thể',outfits:[{id:'basic',name:'Đồ mặc nhà',cost:0},{id:'yem',name:'Yếm',cost:18}]};
const html=familyView(family,{status:'married'},{});
assert.match(html,/UTC\+7/);assert.match(html,/&lt;Bông&gt;/);assert.doesNotMatch(html,/<Bông>/);
assert.match(html,/Đồng ý ở chung/);assert.match(familyView({...family,requests:[]},{status:'married'},{}),/Mời người ấy về ở chung/);
assert.match(html,/không tự giảm/);assert.match(html,/Con chung/);
const waiting=familyView({...family,child:{...child,waiting:true,origin:'birth',stage:'Chờ đón bé',born:'2026-10-05'}},{status:'married'},{});
assert.match(waiting,/2026-10-05/);assert.match(waiting,/disabled/);
const copy=familyView({...family,child:null,copies:[{...child,id:'copy:1',personal:true}],requests:[]},null,{});
assert.match(copy,/Bé bạn tiếp tục chăm/);assert.doesNotMatch(copy,/Mời người ấy về ở chung/);

const posts=[],confirm=[];
const env={api:{state:{journey:{wallet:50}}},confirmAction:async(...args)=>{confirm.push(args);return 'cash';}};
const ctx={env,family,form:{},post:async(op,p)=>{posts.push({op,p});return {};} };
assert.equal(await familyAction('fam:care',{child:'shared',act:'milk'},ctx),true);
assert.equal(posts[0].op,'family_child_care');assert.equal(posts[0].p.pay,'cash');assert.ok(posts[0].p.rid.length>=8);
assert.equal(confirm.length,1);
await familyAction('fam:answer',{id:'7',answer:'accept'},ctx);
assert.equal(posts[1].op,'family_answer');assert.equal(posts[1].p.id,7);assert.match(confirm[1][1],/nhà cá nhân/i);
await familyAction('fam:request',{}, {...ctx,form:{name:'Mít',origin:'birth'}});
assert.equal(posts[2].p.origin,'birth');assert.match(confirm[2][1],/ngày lịch Việt Nam/);
await familyAction('fam:care',{child:'shared',act:'milk'}, {...ctx,family:{...family,child:{...child,waiting:true}}});
assert.equal(posts.length,3);
const tasks=new Map(),applied=[];let timerId=0,active=true,resolveRead;
const refresh=familyRefresh({active:()=>active,read:()=>new Promise(r=>{resolveRead=r;}),apply:v=>applied.push(v),setTimer:(fn,ms)=>{assert.equal(ms,15000);tasks.set(++timerId,fn);return timerId;},clearTimer:id=>tasks.delete(id)});
async function tick(){const [id,fn]=tasks.entries().next().value;tasks.delete(id);return fn();}
refresh.start();let pending=tick();resolveRead({child:{care_days:2}});await pending;assert.equal(applied[0].child.care_days,2,'partner care refreshes canonical UI');
pending=tick();refresh.invalidate();resolveRead({child:{care_days:1}});await pending;assert.equal(applied.length,1,'older read cannot replace a mutation');
active=false;await tick();assert.equal(applied.length,1,'typing/hidden/busy sheet is skipped');
active=true;pending=tick();refresh.stop();resolveRead({child:{care_days:3}});await pending;assert.equal(applied.length,1);assert.equal(tasks.size,0,'close cancels polling and rejects in-flight reads');
console.log('Family UI: consent, safe names, VN day, birth waiting and personal custody pass.');
