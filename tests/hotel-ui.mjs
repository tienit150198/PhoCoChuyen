// Khách sạn Sông Mây workbench: every post's job view renders in node from real server tasks (python -m json dump),
// with escaped text, step payloads that name the open step and no answer key.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {existsSync} from 'node:fs';
import test from 'node:test';

const url=new URL('../public/js/careers/hotel.js',import.meta.url);
test('hotel has a loadable workbench',()=>assert.ok(existsSync(url)));

const dump=execFileSync(process.env.PYTHON||'python',['-c',`
import json
from game.careers import hotel as h
out = {}
for slot in range(12):
    t = h.make_task(3, slot, 1)
    if t['kind'] in out:
        continue
    t['known'] = True
    out[t['kind']] = h.public_task(t)
season = dict(h.make_task(3, 3, 1), known=True, season='noel')
assert season['kind'] == 'decor'
out['decor_noel'] = h.public_task(season)
print(json.dumps(dict(tasks=out, content=h.content()), ensure_ascii=False))
`],{encoding:'utf8',env:{...process.env,PYTHONUTF8:'1'}});
const {tasks,content}=JSON.parse(dump);

const {default:career}=await import(url);
const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const harness=(ui={})=>({esc,fmt:String,ui,state:{},icon:()=>'',
  room:{day:3,money:100,data:{intro:true,stats:{good:2,active_days:1,posts:{}},progress:{milestones:[{id:'desk',label:'Đứng vững một quầy',jobs:15,days:5,posts:3,achieved:false}],posts:1},
    desk:{ev:null,last:null,log:[]},season:null}},
  cc:content,
  cmd:(label,cmd,p,cls='',disabled=false)=>`<button data-command="${cmd}" data-payload="${esc(JSON.stringify(p))}"${disabled?' disabled':''}>${label}</button>`,
  npc:()=>({display_name:'Chị Hằng'}),portrait:()=>''});

test('all six posts and a seasonal decor brief come from the server',()=>{
  assert.deepEqual(Object.keys(tasks).sort(),['breakfast','checkin','decor','decor_noel','housekeeping','laundry','repair']);
  for(const t of Object.values(tasks))assert.equal(t._key,undefined,'the answer key never reaches the client');
});

for(const [kind,task] of Object.entries(tasks)){
  test(`${kind}: every step of the job view renders without leaking answers`,()=>{
    const steps=task.needs.steps;
    assert.ok(steps.length>=3);
    for(let at=0;at<steps.length;at++){
      const t={...task,at},x=harness(),html=career.job(t,x),st=steps[at];
      assert.match(html,/career-job sk hotel/);
      assert.ok(html.includes(esc(st.title)),`${kind} step ${st.id} shows its title`);
      assert.doesNotMatch(html,/undefined|NaN|\[object Object\]|_key/);
      if(st.type==='choice'){
        assert.match(html,/data-command="ht_step"/);
        for(const o of st.options)assert.ok(html.includes(esc(JSON.stringify({task:t.id,step:st.id,value:o.id}))),`${st.id} option ${o.id}`);
      }else if(st.type==='number'){
        assert.match(html,/inputmode="numeric"/);assert.match(html,/amtSend/);
      }else if(st.type==='counts'){
        for(const f of st.fields)assert.match(html,new RegExp(`data-field="${f.id}"`));
        assert.match(html,/htCounts/);
      }else{
        assert.match(html,/htPick/);
        for(const o of st.options)assert.ok(html.includes(esc(o.label)));
      }
      if(st.id==='checkin.room'||st.id==='rush.room')assert.match(html,/Bảng phòng/);
      if(kind==='checkin'){assert.match(html,/khách đang chờ ở quầy/);assert.match(html,/xong trước/);assert.match(html,/⏱️ chuẩn 150 giây/);}
      if(kind==='housekeeping'){assert.match(html,/Khách đến hôm nay/);assert.match(html,/Bảng tình trạng phòng/);assert.match(html,/Sạch · đã kiểm/);}
    }
    const done=career.job({...task,at:steps.length,quality:88,paid:5},harness());
    assert.match(done,/Xong việc · chất lượng 88%/);
  });
}

test('the season banner shows on a seasonal task and the decor brief is the season one',()=>{
  const t=tasks.decor_noel,html=career.job(t,harness());
  assert.equal(t.needs.theme,'noel');
  assert.match(html,/Mùa Giáng sinh/);assert.match(html,/×1.5/);
});

test('the room board shows the supervisor\'s own decisions: the locked room and the signed-off room',()=>{
  const t=tasks.housekeeping,n=t.needs,tile=(html,no)=>html.match(new RegExp(`<li class="ht-room st-(\\w+)">\\s*<b>${no}</b>`))?.[1];
  const before=career.job({...t,at:2,work:{}},harness());
  assert.equal(tile(before,n.fault.room),'vd');assert.equal(tile(before,n.check.room),'vc');
  const after=career.job({...t,at:4,work:{'housekeeping.ooo':'ooo','housekeeping.inspect':'pass'}},harness());
  assert.equal(tile(after,n.fault.room),'ooo');assert.equal(tile(after,n.check.room),'vci');
});

test('an ordered pick sends the tapped sequence and is disabled until complete',async()=>{
  const t={...tasks.checkin,at:1},st=t.needs.steps[1],key=`${t.id}:${st.id}`,x=harness();   // the rush-hour serving order (#466)
  assert.equal(st.type,'order');
  let html=career.job(t,x);
  assert.match(html,/Xác nhận thứ tự<\/button>/);assert.match(html,/disabled>Xác nhận thứ tự/);
  x.render=()=>{};
  for(const o of st.options)await career.actions.htPick({key,id:o.id,ordered:'1'},null,x);
  html=career.job(t,x);
  assert.ok(html.includes(esc(JSON.stringify({task:t.id,step:st.id,value:st.options.map(o=>o.id)}))));
  await career.actions.htPick({key,id:st.options[0].id,ordered:'1'},null,x);
  assert.equal(x.ui.htPick[key].length,st.options.length-1,'tapping again removes it');
  await career.actions.htClear({key},null,x);assert.deepEqual(x.ui.htPick[key],[]);
});

test('counts are typed per field and refused until every field holds a number',async()=>{
  const t=tasks.laundry,st=t.needs.steps[0],key=`${t.id}:${st.id}`,sent=[],toasts=[];
  const x={...harness(),send:async(...v)=>sent.push(v),toast:m=>toasts.push(m)};
  const fields=st.fields.map(f=>f.id).join(',');
  await career.actions.htCounts({key,task:t.id,step:st.id,fields},null,x);
  assert.equal(sent.length,0);assert.equal(toasts.length,1);
  for(const f of st.fields)career.input({dataset:{htCnt:key,field:f.id},value:'3'},x);
  await career.actions.htCounts({key,task:t.id,step:st.id,fields},null,x);
  assert.equal(sent.length,1);assert.equal(sent[0][0],'ht_step');
  assert.deepEqual(sent[0][1],{task:t.id,step:st.id,value:Object.fromEntries(st.fields.map(f=>[f.id,3]))});
});

test('zero is a valid typed amount (an untouched minibar)',async()=>{
  const sent=[],x={ui:{amt:{k:0}},send:async(...v)=>sent.push(v),toast:()=>{}};
  await career.actions.amtSend({key:'k',def:'0',cmd:'ht_step',field:'value',extra:JSON.stringify({task:'t',step:'housekeeping.minibar'})},null,x);
  assert.deepEqual(sent,[['ht_step',{task:'t',step:'housekeeping.minibar',value:0}]]);
});

test('text from the server is escaped and a desk surprise blocks with its choices',()=>{
  const t={...tasks.repair,at:0,opening:'<img src=x>'};
  t.needs={...t.needs,steps:t.needs.steps.map((s,i)=>i?s:{...s,evidence:'<script>alert(1)</script>'})};
  const x=harness();x.room.data.desk={ev:{script:'duck',emoji:'🦆',title:'Khách mang theo con vịt',text:'<b>Quạc</b>',tone:'gentle',options:[{id:'a',label:'Nhẹ nhàng',cost:0}]},last:null,log:[]};
  const html=career.job(t,x);
  assert.match(html,/&lt;script>/);assert.match(html,/&lt;img src=x>/);assert.match(html,/&lt;b>Quạc/);
  assert.doesNotMatch(html,/<script>|<img src=x>/);
  assert.match(html,/data-command="ht_desk"/);
});

test('the intro, idle view and notebook page render',()=>{
  const x=harness();x.room.data.intro=false;
  assert.match(career.job(tasks.checkin,x),/ht_intro/);
  const idle=career.idle(harness());assert.match(idle,/Hành trình Sông Mây/);assert.match(idle,/hư cấu/);
  const brief=harness();brief.room.data.briefing='📋 Giao ban: công suất 88%';assert.match(career.idle(brief),/ht-brief/);
  assert.match(career.page('car:notes',harness()),/Sổ quy trình/);
  assert.equal(career.page('other',harness()),'');
});
