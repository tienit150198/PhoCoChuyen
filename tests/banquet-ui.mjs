// Nhà hàng tiệc Hồng Mây workbench: every job of every role renders in node from real server tasks (python json dump),
// with escaped text, step payloads that name the open step, the role picker, the kitchen checklists, the fire warning
// and no answer key.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {existsSync} from 'node:fs';
import test from 'node:test';

const url=new URL('../public/js/careers/banquet.js',import.meta.url);
test('banquet has a loadable workbench',()=>assert.ok(existsSync(url)));

const dump=execFileSync(process.env.PYTHON||'python',['-c',`
import json
from game.careers import banquet as b
from game.careers import banquet_content as bc
out = {}
for role, jobs in bc.ROLE_JOBS.items():
    for slot in range(len(jobs)):
        t = dict(b.make_task(3, slot, 1), known=True, role=role)
        out[b.job_of(3, slot, role)] = b.public_task(t)
rush = dict(b.make_task(3, 0, 1), known=True, role='hall', rush='vnwomen')
out['event_rush'] = b.public_task(rush)
shift = {}
for part in ('open', 'close'):
    steps, _ = b.shift_steps(3, part)
    shift[part] = dict(at=0, total=len(steps), done=False, step=steps[0])
print(json.dumps(dict(tasks=out, content=b.content(), shift=shift, fine=b.fire_fine({})), ensure_ascii=False))
`],{encoding:'utf8',env:{...process.env,PYTHONUTF8:'1'}});
const {tasks,content,shift,fine}=JSON.parse(dump);

const {default:career}=await import(url);
const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const harness=(ui={},extra={})=>({esc,fmt:String,ui,state:{},icon:()=>'',
  room:{day:3,money:100,data:{intro:true,role:'prep',promoted:false,stats:{good:2,active_days:1,roles:{}},
    progress:{milestones:[{id:'helper',label:'Phụ bếp vững tay',jobs:15,days:5,roles:1,achieved:false}],roles:1,probation:3,prep_days:1},
    desk:{ev:null,last:null,log:[]},rush:null,fire_fine:fine,
    shift:{open:{...shift.open},close:{...shift.close},kitchen:false,insp:'',fire:0},...extra}},
  cc:content,
  cmd:(label,cmd,p,cls='',disabled=false)=>`<button data-command="${cmd}" data-payload="${esc(JSON.stringify(p))}"${disabled?' disabled':''}>${label}</button>`,
  npc:()=>({display_name:'Chị Loan'}),portrait:()=>''});

test('all seven jobs of the three roles and a rush event come from the server',()=>{
  assert.deepEqual(Object.keys(tasks).sort(),['check','cook','event','event_rush','plate','prep','salad','tools']);
  for(const t of Object.values(tasks)){
    assert.equal(t._key,undefined,'the answer key never reaches the client');
    assert.ok(t.job&&t.role_info);
  }
});

for(const [job,task] of Object.entries(tasks)){
  test(`${job}: every step of the job view renders without leaking answers`,()=>{
    const steps=task.needs.steps;
    assert.ok(steps.length>=4);
    for(let at=0;at<steps.length;at++){
      const t={...task,at},x=harness({},{shift:{open:{...shift.open,done:true,at:1},close:{...shift.close},kitchen:true,insp:'',fire:0}}),html=career.job(t,x),st=steps[at];
      assert.match(html,/career-job sk banquet/);
      assert.ok(html.includes(esc(st.title)),`${job} step ${st.id} shows its title`);
      assert.doesNotMatch(html,/undefined|NaN|\[object Object\]|_key/);
      if(st.type==='choice'){
        assert.match(html,/data-command="bq_step"/);
        for(const o of st.options)assert.ok(html.includes(esc(JSON.stringify({task:t.id,step:st.id,value:o.id}))),`${st.id} option ${o.id}`);
      }else if(st.type==='number'){
        assert.match(html,/inputmode="numeric"/);assert.match(html,/amtSend/);
      }else{
        assert.match(html,/bqPick/);
        for(const o of st.options)assert.ok(html.includes(esc(o.label)));
      }
    }
    const done=career.job({...task,at:steps.length,quality:88,paid:5},harness());
    assert.match(done,/Xong việc · chất lượng 88%/);
  });
}

test('the event brief lists the halls and the rush banner shows on a rush slip',()=>{
  const html=career.job(tasks.event_rush,harness());
  assert.match(html,/Phòng tiệc/);assert.match(html,/Sảnh Hồng Mây/);
  assert.match(html,/Phụ nữ Việt Nam 20\/10/);assert.match(html,/×1.5/);
});

test('the role picker locks Đầu bếp until the probation is done',()=>{
  const x=harness();
  let html=career.idle(x);
  assert.match(html,/Ca này bạn làm/);
  assert.match(html,/data-command="bq_role" data-payload="[^"]*chef[^"]*" disabled/);
  assert.match(html,/1\/3/);
  x.room.data.promoted=true;
  html=career.idle(x);
  assert.doesNotMatch(html,/data-command="bq_role" data-payload="[^"]*chef[^"]*" disabled/);
});

test('the kitchen opens with the hygiene checklist and closes with the fire warning',async()=>{
  const x=harness();x.render=()=>{};
  let html=career.idle(x);
  assert.match(html,/Đầu ca: Vệ sinh đầu ca/);
  const st=shift.open.step,key=`open:${st.id}`;
  for(const o of st.options)await career.actions.bqPick({key,id:o.id},null,x);
  html=career.idle(x);
  assert.ok(html.includes(esc(JSON.stringify({part:'open',step:st.id,value:st.options.map(o=>o.id)}))));
  const closing=harness({}, {shift:{open:{...shift.open,done:true,at:1},close:{...shift.close},kitchen:true,insp:'pass',fire:0}});
  html=career.idle(closing);
  assert.match(html,/Cuối ca: dọn bếp và tắt điện/);
  assert.match(html,new RegExp(`Tiền đền bù ${fine} xu`));assert.match(html,/tối đa 6 xu/);assert.match(html,/không bao giờ quá số tiền đang có/);
  assert.match(html,/Đoàn kiểm tra: đạt/);
  const hall=harness({}, {role:'hall'});
  assert.doesNotMatch(career.idle(hall),/Đầu ca:/,'the hall track has no kitchen checklist');
});

test('closing waits for the dish in hand',()=>{
  const t={...tasks.cook,at:1};
  const html=career.job(t,harness({}, {shift:{open:{...shift.open,done:true,at:1},close:{...shift.close},kitchen:true,insp:'',fire:0}}));
  assert.match(html,/Xong món đang làm rồi mới dọn bếp/);
  assert.doesNotMatch(html,/data-payload="[^"]*close[^"]*"/);
});

test('an ordered pick sends the tapped sequence and is disabled until complete',async()=>{
  const t={...tasks.salad,at:0},st=t.needs.steps[0],key=`${t.id}:${st.id}`,x=harness();
  let html=career.job(t,x);
  assert.equal(st.type,'order');
  assert.match(html,/disabled>Xác nhận thứ tự/);
  x.render=()=>{};
  for(const o of st.options)await career.actions.bqPick({key,id:o.id},null,x);
  html=career.job(t,x);
  assert.ok(html.includes(esc(JSON.stringify({task:t.id,step:st.id,value:st.options.map(o=>o.id)}))));
  await career.actions.bqPick({key,id:st.options[0].id},null,x);
  assert.equal(x.ui.bqPick[key].length,st.options.length-1,'tapping again removes it');
  await career.actions.bqClear({key},null,x);assert.deepEqual(x.ui.bqPick[key],[]);
});

test('a typed number is sent as an integer and nonsense is refused',async()=>{
  const sent=[],toasts=[],x={ui:{amt:{k:480}},send:async(...v)=>sent.push(v),toast:m=>toasts.push(m)};
  await career.actions.amtSend({key:'k',def:'0',cmd:'bq_step',field:'value',extra:JSON.stringify({task:'t',step:'prep.grams'})},null,x);
  assert.deepEqual(sent,[['bq_step',{task:'t',step:'prep.grams',value:480}]]);
  x.ui.amt.k=-3;await career.actions.amtSend({key:'k',def:'0',cmd:'bq_step',field:'value',extra:'{}'},null,x);
  assert.equal(sent.length,1);assert.equal(toasts.length,1);
});

test('text from the server is escaped and a desk surprise blocks with its choices',()=>{
  const t={...tasks.plate,at:0,opening:'<img src=x>'};
  t.needs={...t.needs,steps:t.needs.steps.map((s,i)=>i?s:{...s,evidence:'<script>alert(1)</script>'})};
  const x=harness();x.room.data.desk={ev:{script:'ring',emoji:'💍',title:'Nhờ giấu nhẫn',text:'<b>Bàn 7</b>',tone:'gentle',options:[{id:'plate',label:'Đĩa riêng',cost:0}]},last:null,log:[]};
  const html=career.job(t,x);
  assert.match(html,/&lt;script>/);assert.match(html,/&lt;img src=x>/);assert.match(html,/&lt;b>Bàn 7/);
  assert.doesNotMatch(html,/<script>|<img src=x>/);
  assert.match(html,/data-command="bq_desk"/);
});

test('the intro, idle view and notebook page render',()=>{
  const x=harness();x.room.data.intro=false;
  assert.match(career.job(tasks.prep,x),/bq_intro/);
  const idle=career.idle(harness());assert.match(idle,/Hành trình Hồng Mây/);assert.match(idle,/hư cấu/);assert.match(idle,/Thử việc phụ bếp/);
  assert.match(career.page('car:notes',harness()),/Sổ bếp và sổ sảnh/);
  assert.equal(career.page('other',harness()),'');
});
