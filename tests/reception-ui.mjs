// Lễ tân Hoa Sứ workbench: every kind of job and the three trial check-ins render in node from real server tasks
// (python -m json dump): every step, escaped text, step payloads that name the open step, no answer key; the room board,
// the hook board, the luggage cart and the timeline; the idle view and the Sổ nghề page.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {existsSync} from 'node:fs';
import test from 'node:test';

const url=new URL('../public/js/careers/reception.js',import.meta.url);
test('reception has a loadable workbench',()=>assert.ok(existsSync(url)));

const dump=execFileSync(process.env.PYTHON||'python',['-c',`
import json
from game.careers import reception as r
out = {}
for slot in range(8):
    t = r.make_task(4, slot, 1)
    if t['kind'] in out:
        continue
    t['known'] = True
    out[t['kind']] = r.public_task(t)
for part in ('normal', 'early', 'group'):
    t = dict(r.make_task(4, 1, 1), known=True, trial=part)
    out['trial_' + part] = r.public_task(t)
c = dict(day=4, ext=dict(data=r.initial()))
print(json.dumps(dict(tasks=out, content=r.content(), data=r.public_data(c)), ensure_ascii=False))
`],{encoding:'utf8',env:{...process.env,PYTHONUTF8:'1'}});
const {tasks,content,data}=JSON.parse(dump);

const {default:career}=await import(url);
const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const harness=(ui={})=>({esc,fmt:String,ui,state:{},icon:()=>'',
  room:{day:4,money:100,promo:{rank:0},data:{...data,intro:true}},
  cc:content,
  cmd:(label,cmd,p,cls='',disabled=false)=>`<button class="${cls}" data-command="${cmd}" data-payload="${esc(JSON.stringify(p))}"${disabled?' disabled':''}>${label}</button>`,
  npc:()=>({display_name:'Chị Quyên'}),portrait:()=>''});

test('six kinds and three trial parts come from the server without their key',()=>{
  assert.deepEqual(Object.keys(tasks).sort(),['arrival','checkout','complaint','lost','rooms','services','trial_early','trial_group','trial_normal']);
  for(const t of Object.values(tasks))assert.equal(t._key,undefined,'the answer key never reaches the client');
  assert.equal(tasks.trial_early.trial_info.id,'early');
  assert.equal(tasks.trial_early.needs.variant,'early');
});

for(const [kind,task] of Object.entries(tasks)){
  test(`${kind}: every step renders, names its step, leaks nothing`,()=>{
    const steps=task.needs.steps;
    assert.ok(steps.length>=3);
    for(let at=0;at<steps.length;at++){
      const t={...task,at},x=harness(),html=career.job(t,x),st=steps[at];
      assert.match(html,/career-job sk reception/);
      assert.ok(html.includes(esc(st.title)),`${kind} step ${st.id} shows its title`);
      assert.doesNotMatch(html,/undefined|NaN|\[object Object\]|_key/);
      if(st.type==='choice'){
        for(const o of st.options)assert.ok(html.includes(esc(JSON.stringify({task:t.id,step:st.id,value:o.id}))),`${st.id} option ${o.id}`);
      }else if(st.type==='assign'){
        assert.match(html,st.id==='arrival.rooms'?/class="rc-board"/:/class="rc-cart"/);
        for(const c of st.cards)assert.match(html,new RegExp(`data-rc-drag="[^"]+" data-id="${c.id}"`));
        for(const g of st.targets)assert.match(html,new RegExp(`data-target="${g.id}"`));
        assert.match(html,/rc-send[^"]*" data-command="rc_step"[^>]*disabled/,'nothing placed yet: the confirm waits');
      }else if(st.type==='times'){
        for(const f of st.fields)assert.match(html,new RegExp(`<select[^>]+data-id="${f.id}"`));
      }else if(st.type==='number'){
        assert.match(html,/amtSend/);
      }else{
        for(const o of st.options)assert.match(html,new RegExp(`data-id="${o.id}"`));
      }
    }
  });
}

test('the guests\' tags show only after the need step',()=>{
  const t=tasks.trial_group,x=harness();
  assert.ok(t.needs.cards.every(c=>c.tags.length===0),'what the guest needs is read from what they say');
  assert.match(career.job({...t,at:0},x),/<q>/);
});

test('a card placed on a room shows there and arms the confirm',()=>{
  const t={...tasks.trial_normal,at:1},st=t.needs.steps[1],key=`${t.id}:${st.id}`,room=t.needs.board[0].no;
  const x=harness({rcAsg:{[key]:{[t.needs.cards[0].id]:room}}});
  const html=career.job(t,x);
  assert.match(html,/rc-room[^"]*filled/);
  assert.doesNotMatch(html,/rc-send-rooms"[^>]*disabled/);
});

test('idle view and the Sổ nghề page',()=>{
  const x=harness();
  assert.match(career.idle(x),/Ca thử việc với chị Quyên/);
  const page=career.page('car:notes',x);
  for(const name of ['Chị Quyên','Khoa','Na','Cô Lài','Ông Tư Bến'])assert.ok(page.includes(name),name);
  assert.match(page,/data-command="rc_branch"/);
});
