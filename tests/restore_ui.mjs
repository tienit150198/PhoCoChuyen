// 🧰 Xưởng phục chế (public/js/careers/restore.js): each stage draws its choices with the coach's markers
// (game/coach/services.py), sends exactly the payload game/careers/restore.py expects, and never shows hidden answers.
import assert from 'node:assert/strict';
const {default: rs}=await import('../public/js/careers/restore.js');
const sent=[];
const x={esc:s=>String(s).replaceAll('<','&lt;'),ui:{},room:{data:{stats:{good:3,active_days:2}}},
  cc:{stages:{talk:'Chốt yêu cầu với khách'},rules:['Giữ hồn món đồ']},
  cmd:(label,cmd,p)=>`<button data-command="${cmd}">${label}</button>`,
  send:async(cmd,payload)=>sent.push({cmd,payload}),render:()=>{}};
const needs={item:'Đồng hồ quả lắc của ông nội',material:'wood',material_name:'Gỗ',tag:'HX-0001-00',tag_options:['HX-0001-00','HX-0001-01','HX-0001-02'],
  net:22,cost:3,damages:2,signs:[{id:'s1',text:'Dấu hiệu 1: có đường nứt.'},{id:'s2',text:'Dấu hiệu 2: kẹt máy.'}],
  demands:[{id:'scratch',text:'Khách dặn: giữ vết xước.',options:[{id:'sand',label:'Chà hết'},{id:'keep',label:'Giữ nguyên vết xước'},{id:'paint',label:'Sơn đè'}]}],
  parts:[{id:'p1',name:'kim phút',missing:false}]};
const task=(stage,extra={})=>({id:'restore-0001-00',known:true,stage,quality:100,needs,options:[{id:'crack',label:'Nứt'},{id:'seized',label:'Kẹt máy'}],
  instruction:'Làm đúng bước',work:{talk:{scratch:'keep'}},found:[{id:'crack',name:'Nứt'},{id:'seized',name:'Kẹt máy'}],last_issue:'',...extra});
const marks={inspect:'restore-signs',talk:'restore-talk',parts:'restore-parts',clean:'restore-clean',fix:'restore-fix',finish:'restore-finish',check:'restore-checks',deliver:'restore-tags'};
for(const [stage,mark] of Object.entries(marks)){
  const html=rs.job(task(stage),x);
  assert.match(html,new RegExp(`class="rs-stage" data-stage="${stage}"`),stage);
  assert.match(html,new RegExp(`data-coach="${mark}"`),stage+' carries the coach marker');
  assert.match(html,/class="btn primary rs-submit"/);
  assert.match(html,/data-coach="restore-desk"/,'the players\' bench is reachable from every stage');
  assert.doesNotMatch(html,/_key/);
}
assert.match(rs.job(task('finish'),x),/Đã chốt với khách: Giữ nguyên vết xước/,'the finish stage reminds what was agreed');
assert.match(rs.job({...task('inspect'),known:false,opening:'Nhờ xưởng'},x),/data-command="ask"/);
// payloads: per-item choices, one choice, the checks, the ticket
const put=(stage,field,value,type='select-one',checked)=>rs.input({dataset:{rsField:field,rsTask:'restore-0001-00',rsStage:stage},value,type,checked},x);
put('inspect','s1','crack');put('inspect','s2','seized');
await rs.actions.send({task:'restore-0001-00',stage:'inspect'},null,x);
put('talk','scratch','keep','radio',true);
await rs.actions.send({task:'restore-0001-00',stage:'talk'},null,x);
put('clean','choice','oil_wipe','radio',true);
await rs.actions.send({task:'restore-0001-00',stage:'clean'},null,x);
for(const k of ['stable','photo','note','care'])put('check',k,'on','checkbox',true);
await rs.actions.send({task:'restore-0001-00',stage:'check'},null,x);
put('deliver','tag','HX-0001-00','radio',true);
await rs.actions.send({task:'restore-0001-00',stage:'deliver'},null,x);
assert.deepEqual(sent,[
  {cmd:'phc_inspect',payload:{task:'restore-0001-00',choices:{s1:'crack',s2:'seized'}}},
  {cmd:'phc_talk',payload:{task:'restore-0001-00',choices:{scratch:'keep'}}},
  {cmd:'phc_clean',payload:{task:'restore-0001-00',choice:'oil_wipe'}},
  {cmd:'phc_check',payload:{task:'restore-0001-00',checks:['stable','photo','note','care']}},
  {cmd:'phc_deliver',payload:{task:'restore-0001-00',tag:'HX-0001-00'}},
]);
assert.match(rs.idle(x),/3 \/ 100/);
console.log('restore workbench: every stage, coach markers, payloads and the players\' bench entry pass');
