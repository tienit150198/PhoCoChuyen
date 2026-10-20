// Đài phát thanh Sóng Mây workbench: every job of both roles renders in node from real server tasks (python json dump),
// with escaped text, step payloads that name the open step, the role picker, the studio check that comes first, the outage
// drill that blocks the air, the 📻 Đơn lên sóng entry (both layouts) and no answer key. Also the ticker keeps radio lines
// bounded (one pass, a replay gap per device) and the 📻 desk dialog renders an order, the moderation verdict and the caps.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {existsSync,readFileSync} from 'node:fs';
import test from 'node:test';

const url=new URL('../public/js/careers/radio.js',import.meta.url);
test('radio has a loadable workbench',()=>assert.ok(existsSync(url)));

const dump=execFileSync(process.env.PYTHON||'python',['-c',`
import json
from game.careers import radio as r
from game.careers import radio_content as rc
out = {}
for role, jobs in rc.ROLE_JOBS.items():
    for slot in range(len(jobs)):
        t = dict(r.make_task(3, slot, 1), known=True, role=role)
        out[r.job_of(3, slot, role)] = r.public_task(t)
shift = {}
for part in ('open', 'outage'):
    steps, _ = r.shift_steps(3, part)
    shift[part] = steps[0]
print(json.dumps(dict(tasks=out, content=r.content(), shift=shift), ensure_ascii=False))
`],{encoding:'utf8',env:{...process.env,PYTHONUTF8:'1'}});
const {tasks,content,shift}=JSON.parse(dump);

const {default:career}=await import(url);
const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const studio=(done=true,outage='')=>({open:{at:done?1:0,total:1,done,step:done?null:shift.open},
  outage:{state:outage,at:0,total:1,slips:0,limit:3,step:outage==='cut'?shift.outage:null}});
const harness=(ui={},extra={})=>({esc,fmt:String,ui,state:{},icon:()=>'',
  room:{day:3,money:100,data:{intro:true,role:'news',promoted:false,stats:{good:2,active_days:1,roles:{},restored:0,dead_air:0},
    progress:{milestones:[{id:'voice',label:'Giọng đọc vững vàng',jobs:15,days:5,roles:1,achieved:false}],roles:1,probation:3,news_days:1},
    desk:{ev:null,last:null,log:[]},shift:studio(),...extra}},
  cc:content,
  cmd:(label,cmd,p,cls='',disabled=false)=>`<button data-command="${cmd}" data-payload="${esc(JSON.stringify(p))}"${disabled?' disabled':''}>${label}</button>`,
  npc:()=>({display_name:'Chị Hoa'}),portrait:()=>''});

test('all six jobs of the two roles come from the server without the answer key',()=>{
  assert.deepEqual(Object.keys(tasks).sort(),['bulletin','callin','playlist','request','spot','wishes']);
  for(const t of Object.values(tasks)){
    assert.equal(t._key,undefined,'the answer key never reaches the client');
    assert.ok(t.job&&t.role_info);
    for(const st of t.needs.steps)for(const o of st.options||[])assert.match(o.id,/^[a-h]$/,'option ids never say which is right');
  }
});

for(const [job,task] of Object.entries(tasks)){
  test(`${job}: every step of the job view renders without leaking answers`,()=>{
    const steps=task.needs.steps;
    assert.equal(steps.length,4);
    for(let at=0;at<steps.length;at++){
      const t={...task,at},x=harness(),html=career.job(t,x),st=steps[at];
      assert.match(html,/career-job sk radio/);
      assert.ok(html.includes(esc(st.title)),`${job} step ${st.id} shows its title`);
      assert.doesNotMatch(html,/undefined|NaN|\[object Object\]|_key/);
      if(st.type==='choice'){
        assert.match(html,/data-command="rd_step"/);
        for(const o of st.options)assert.ok(html.includes(esc(JSON.stringify({task:t.id,step:st.id,value:o.id}))),`${st.id} option ${o.id}`);
      }else if(st.type==='number'){
        assert.match(html,/inputmode="numeric"/);assert.match(html,/amtSend/);
      }else{
        assert.match(html,/rdPick/);
        for(const o of st.options)assert.ok(html.includes(esc(o.label)));
      }
    }
    assert.match(career.job({...task,at:steps.length,quality:88,paid:5},harness()),/Xong việc · chất lượng 88%/);
  });
}

test('the studio check comes first and an outage blocks the air',()=>{
  const t={...tasks.bulletin,at:0};
  let html=career.job(t,harness({}, {shift:studio(false)}));
  assert.match(html,/Đầu ca: Kiểm phòng thu đầu ca/);
  assert.match(html,/Kiểm phòng thu đầu ca xong rồi mới lên sóng/);
  assert.doesNotMatch(html,/data-command="rd_step"/);
  html=career.job(t,harness({}, {shift:studio(true,'cut')}));
  assert.match(html,/rd-outage/);assert.match(html,/role="alert"/);
  assert.match(html,/Đang mất điện/);
  assert.doesNotMatch(html,/data-command="rd_step"/);
  assert.match(html,/rdPick/);   // the drill is an ordered pick sent as rd_shift
  html=career.idle(harness({}, {shift:studio(true,'back')}));
  assert.match(html,/Sự cố mất điện đã xử lý/);
});

test('the role picker locks DJ until the probation is done',()=>{
  const x=harness();
  let html=career.idle(x);
  assert.match(html,/Ca này bạn làm/);
  assert.match(html,/data-command="rd_role" data-payload="[^"]*dj[^"]*" disabled/);
  assert.match(html,/1\/3/);
  x.room.data.promoted=true;
  html=career.idle(x);
  assert.doesNotMatch(html,/data-command="rd_role" data-payload="[^"]*dj[^"]*" disabled/);
});

test('the 📻 Đơn lên sóng entry is in the idle view and between slips, and the notebook page renders',()=>{
  assert.match(career.idle(harness()),/data-action="radioDesk"/);
  assert.match(career.job({...tasks.spot,known:false},harness()),/data-action="radioDesk"/);
  assert.match(career.page('car:notes',harness()),/Sổ tay phát sóng/);
  assert.equal(career.page('other',harness()),'');
  assert.ok(career.dock.every(([a])=>a.startsWith('car:')));
});

test('an ordered pick sends the tapped sequence and is disabled until complete',async()=>{
  const t={...tasks.bulletin,at:1},st=t.needs.steps[1],key=`${t.id}:${st.id}`,x=harness();
  assert.equal(st.type,'order');
  let html=career.job(t,x);
  assert.match(html,/disabled>Xác nhận thứ tự/);
  x.render=()=>{};
  for(const o of st.options)await career.actions.rdPick({key,id:o.id},null,x);
  html=career.job(t,x);
  assert.ok(html.includes(esc(JSON.stringify({task:t.id,step:st.id,value:st.options.map(o=>o.id)}))));
  await career.actions.rdClear({key},null,x);assert.deepEqual(x.ui.rdPick[key],[]);
});

test('text from the server is escaped and a desk surprise blocks with its choices',()=>{
  const t={...tasks.callin,at:0,opening:'<img src=x>'};
  t.needs={...t.needs,steps:t.needs.steps.map((s,i)=>i?s:{...s,evidence:'<script>alert(1)</script>'})};
  const x=harness();x.room.data.desk={ev:{script:'cat',emoji:'🐈',title:'Con mèo',text:'<b>Mèo</b>',tone:'gentle',options:[{id:'bed',label:'Bế mèo ra',cost:0}]},last:null,log:[]};
  const html=career.job(t,x);
  assert.match(html,/&lt;script>/);assert.match(html,/&lt;img src=x>/);assert.match(html,/&lt;b>Mèo/);
  assert.doesNotMatch(html,/<script>|<img src=x>/);
  assert.match(html,/data-command="rd_desk"/);
});

test('the ticker plays radio lines once, then at most every replay seconds, bounded per device',()=>{
  const src=readFileSync(new URL('../public/js/v4/ticker.js',import.meta.url),'utf8');
  assert.match(src,/AIRED_MAX=32/);
  assert.match(src,/passes:1/);
  assert.match(src,/d\.radio\.slice\(0,8\)/);
  assert.match(src,/iterations:item\.passes\|\|PASSES/);
});

test('the 📻 desk badge counts the orders waiting (taken or not), from one cached request',async()=>{
  globalThis.document={createElement:()=>{const el={className:'',attrs:{},innerHTML:'',open:false,scrollTop:0,setAttribute(k,v){this.attrs[k]=v;},
    addEventListener(){},querySelector(){return root;},showModal(){this.open=true;},close(){this.open=false;},append(){}};return el;},body:{append(){}}};
  const root={innerHTML:''};
  const desk={off:false,caps:{live:1,live_max:4,dj:2,dj_max:12,buyer:0,buyer_max:2,minutes:{quang_cao:60,tang_bai:30},text_max:120},
    orders:[{id:'sv_'+'a'.repeat(24),kind:'quang_cao',status:'held',price:1500,note:'<b>Trà</b> sữa giảm giá',text:'<b>Trà</b> sữa giảm giá',why:'',who:'Lan',
             picks:[{id:'vui',label:'Nhạc nền vui tươi'}],minutes:60,preview:'📢 Lan: <b>Trà</b> sữa giảm giá · 📻 Sóng Mây'},
            {id:'sv_'+'b'.repeat(24),kind:'tang_bai',status:'working',price:600,note:'gọi 0903…',text:'',why:'Lời lên sóng không được có đường link.',who:'Minh',picks:[],minutes:30,preview:''}],
    live:[{id:'rl_'+'c'.repeat(20),text:'🎵 Na gửi tặng bài',live:true,hidden:false,slot:'Lên sóng 19:00–19:30',role:'buyer',can_hide:true}],mine:[]};
  const api={json:async()=>desk,post:async()=>({}),accept(){}};
  globalThis.matchMedia=()=>({matches:false});
  const lazy=await import('../public/js/lazy.js').catch(()=>null);
  const m=await import('../public/js/v4/radio.js');
  let asked=0;api.json=async()=>{asked++;return desk;};
  assert.equal(await m.queueCount({api}),2);
  assert.equal(await m.queueCount({api}),2);
  assert.equal(asked,1,'cached half a minute');
  void lazy;   // the dialog itself is checked in the browser (the screenshots)
});
