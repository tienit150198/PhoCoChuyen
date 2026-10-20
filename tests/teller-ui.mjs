// 🏦 Quầy số 3 workbench: every job (and every step of it) renders in node from real server tasks (python json dump), with
// escaped text, payloads that name the open step, the self-totalling tray (rules stay on the server), the recipient cards,
// the lessons, the exam, the badge, the float and the handover, the branches, and never an answer key.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {existsSync} from 'node:fs';
import test from 'node:test';

const url=new URL('../public/js/careers/teller.js',import.meta.url);
test('teller has a loadable workbench',()=>assert.ok(existsSync(url)));

const dump=execFileSync(process.env.PYTHON||'python',['-c',`
import json
import tests
from game.careers import teller as t
from game.careers import teller_content as tc
from game.careers import kit
out = {}
for day in range(2, 12):
    for slot in range(10):
        job = t.job_of(day, slot)
        arcs = [0, 4] if t.luu_slot(day, slot) else [-1]
        for arc in arcs:
            name = job + ('' if arc < 0 else f'_arc{arc}')
            if name in out and (job != 'withdraw' or any(s['type'] == 'tray' for s in out[name]['needs']['steps'])):
                continue   # (a withdrawal with a tray: the not-the-holder case has none)
            task = dict(t.make_task(day, slot, 1), known=True, arc=arc, rk=1)
            out[name] = t.public_task(task)
c = {'day': 3, 'tasks': [], 'ext': {'data': t.initial()}}
d = c['ext']['data']
data = t.public_data(c)
exam_parts, _ = t.exam_parts(1, 3)
shift = {p: dict(at=0, total=len(t.shift_steps(3, p)[0]), done=False, step=t.shift_steps(3, p)[0][0]) for p in ('open', 'close')}
print(json.dumps(dict(tasks=out, content=t.content(), data=data, exam=exam_parts, shift=shift), ensure_ascii=False))
`],{encoding:'utf8',env:{...process.env,PYTHONUTF8:'1'}});
const {tasks,content,data,exam,shift}=JSON.parse(dump);

const {default:career,vnd,trayTotal}=await import(url);
const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const harness=(ui={},extra={},room={})=>({esc,fmt:String,ui,state:{name:'Lan'},icon:()=>'',
  room:{day:3,money:100,open:true,tasks:[],data:{...data,intro:true,stage:'teller',badge:{day:1,fast:true,clean:false,secs:90},
    shift:{open:{...shift.open,done:true,at:2},close:{...shift.close}},...extra},...room},
  cc:content,now:()=>1000,
  cmd:(label,cmd,p,cls='',disabled=false)=>`<button class="${cls}" data-command="${cmd}" data-payload="${esc(JSON.stringify(p))}"${disabled?' disabled':''}>${label}</button>`,
  npc:()=>({display_name:'Bà Lựu'}),portrait:()=>'<i class="pt"></i>'});

test('money reads as Vietnamese đồng and the tray totals itself',()=>{
  assert.equal(vnd(2350),'2.350.000đ');
  assert.equal(vnd(10),'10.000đ');
  assert.equal(trayTotal({'500':2,'20':3}),1060);
});

test('every job and the tea-cart arc come from the server without the answer key',()=>{
  for(const job of ['withdraw','change','transfer','savings','atm','savings_arc0','savings_arc4'])assert.ok(tasks[job],job);
  for(const t of Object.values(tasks)){
    assert.equal(t._key,undefined,'the answer key never reaches the client');
    assert.ok(t.job_info&&t.needs?.steps?.length>=2);
  }
});

for(const [job,task] of Object.entries(tasks)){
  test(`${job}: every step renders, names its step and leaks nothing`,()=>{
    const steps=task.needs.steps;
    for(let at=0;at<steps.length;at++){
      const t={...task,at},x=harness(),html=career.job(t,x),st=steps[at];
      assert.match(html,/career-job sk teller/);
      assert.ok(html.includes(esc(st.title)),`${job} step ${st.id} shows its title`);
      assert.doesNotMatch(html,/undefined|NaN|\[object Object\]|_key|"total":|"exact":/);
      if(['choice','pick','multi','tray','number'].includes(st.type))assert.ok(html.includes(esc(JSON.stringify(st.id)).slice(0,-6))||html.includes(st.id),`${job} ${st.id} payload`);
      if(st.type==='tray'){
        assert.match(html,/data-tl-tray=/);
        assert.match(html,/tl-tray-send[^>]*disabled/,'an empty tray cannot be confirmed');
      }
      if(st.type==='pick')assert.equal((html.match(/class="tl-card[ "]/g)||[]).length,st.options.length);
    }
  });
}

test('a filled tray shows its total and can be confirmed once it matches the slip',()=>{
  const t={...tasks.withdraw},st=t.needs.steps.find(s=>s.type==='tray');
  t.at=t.needs.steps.indexOf(st);
  const key=`${t.id}:${st.id}`,ui={tray:{[key]:{}}};
  let rest=st.target;
  for(const d of ['500','200','100','50','20','10']){if(st.palette.includes(d)){ui.tray[key][d]=Math.floor(rest/Number(d));rest%=Number(d);}}
  const html=career.job(t,harness(ui));
  assert.ok(html.includes(vnd(st.target)));
  assert.match(html,/Khớp phiếu/);
  assert.doesNotMatch(html,/tl-tray-send[^>]*disabled/);
});

test('hiring: the lessons, the exam start, a running exam with its timer and hint, the badge',()=>{
  const learn=career.job(tasks.withdraw,harness({},{stage:'learn',badge:null,learned:[]}));
  assert.match(learn,/tl-learn/);
  assert.match(learn,/data-command="tl_learn"/);
  assert.doesNotMatch(learn,/tl_step/,'no counter work before the lessons');
  const ready=career.idle(harness({},{stage:'exam',badge:null,exam_view:null,exam_retry:false}));
  assert.match(ready,/tl-exam-go/);
  const running=career.job(tasks.withdraw,harness({},{stage:'exam',badge:null,exam_view:{at:0,total:3,step:exam[0],hints:0,started:900}}));
  assert.match(running,/tl-timer/);
  assert.match(running,/data-command="tl_exam_hint"/);
  assert.match(running,/data-command="tl_exam"/);
  const shadow=career.job(tasks.withdraw,harness({},{stage:'exam',badge:null,exam_view:null,exam_retry:true}));
  assert.match(shadow,/data-command="tl_shadow"/);
  const badge=career.job(tasks.withdraw,harness({},{stage:'training',training:1}));
  assert.match(badge,/tl-badge/);
  assert.match(badge,/Lan/);
  assert.match(badge,/⚡/);
});

test('the float comes first and the handover waits below the customers',()=>{
  const opening=career.job(tasks.withdraw,harness({},{shift:{open:{...shift.open},close:{...shift.close}}}));
  assert.match(opening,/tl-shift/);
  assert.doesNotMatch(opening,/tl-step"/,'no customer before the float is counted');
  const closing=career.idle(harness({},{},{tasks:[]}));
  assert.match(closing,/tl-close/);
  assert.match(closing,/data-command="tl_shift"/);
  assert.match(closing,/tl-rows/,'the receipts in the tray are listed');
});

test('branches: the current one is marked, a locked one shows no rank',()=>{
  const html=career.idle(harness());
  for(const b of ['Giao dịch','Tư vấn','Vận hành','Quản lý'])assert.ok(html.includes(b),b);
  assert.match(html,/Đang theo/);
  assert.match(html,/data-command="tl_branch"/);
});
