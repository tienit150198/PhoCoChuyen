// 📱 Studio Hẻm Xanh, 🎤 Phòng trà Mây Chiều and 🎬 Hãng phim Bến Mây workbenches (careers/kol.js, singer.js, actor.js on
// careers/slip_kit.js). In node: every deal, set and scene renders from real server tasks (python json dump) with escaped
// text, step payloads that name the open step, no answer key, and no format/kind of set/scene on the ticket before the
// first step settles it; no players' orders card (these careers take no player services).
// In a browser (only with TEST_DATABASE_URL, a disposable PostgreSQL database): a dev server, one deal, one set and one
// scene played to the end at 390×844 in the compact layout (one wrong answer first, the desk card when it shows), and the
// full layout drawn. Screenshots go to MNL_SHOTS (default: the session scratchpad); MNL_SERVE runs another launcher.
import assert from 'node:assert/strict';
import {execFileSync,spawn} from 'node:child_process';
import {existsSync,mkdirSync,mkdtempSync} from 'node:fs';
import {createServer} from 'node:net';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import test from 'node:test';

const ROOT=resolve(import.meta.dirname,'..');
const PY=process.env.PYTHON||'python';
const py=code=>JSON.parse(execFileSync(PY,['-c',code],{cwd:ROOT,encoding:'utf8',env:{...process.env,PYTHONUTF8:'1'}}));
const CAREERS=[['kol','deal','deal_name','ko_','deal'],['singer','set','set_name','cs_','evening'],['actor','scene','scene_name','dn_','scene']];

const dump=py(`
import json
from game.careers import kol, singer, actor
out = {}
for mod, kind in ((kol, 'deal'), (singer, 'set'), (actor, 'scene')):
    seen = {}
    for day in (1, 5, 12, 25, 41, 42, 43):
        for slot in range(12):
            t = dict(mod.make_task(day, slot, 1), known=True)
            # the server hides the kind of job until the first step is answered: keep both views
            seen.setdefault(t['needs'][kind], dict(mod.public_task(dict(t, at=1)), first=mod.public_task(t)['needs']))
    out[mod.ID] = dict(tasks=seen, content=mod.content(), hidden=mod.public_task(mod.make_task(40, 0, 1)))
print(json.dumps(out, ensure_ascii=False))
`);

const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const data=(extra={})=>({intro:true,today:{day:3,jobs:1,good:1,earned:9,bonus:4},stats:{jobs:5,good:4,active_days:2,earned:40,bonus:12},
  closed_day:0,desk:{ev:null,last:null,log:[]},mastered:false,expert:false,...extra});
const harness=(id,extra={},ui={})=>({esc,fmt:String,ui,state:{current:id},icon:()=>'',
  room:{day:3,money:100,data:data(extra)},cc:dump[id].content,
  cmd:(label,cmd,p,cls='',disabled=false)=>`<button class="btn ${cls}" data-command="${cmd}" data-payload="${esc(JSON.stringify(p))}"${disabled?' disabled':''}>${label}</button>`,
  npc:()=>({display_name:'Ngân'}),portrait:()=>'',render(){},toast(){},api:{}});
const ticketOf=html=>html.match(/<article class="sl-ticket">[\s\S]*?<\/article>/)?.[0]||'';

for(const [id,kind,nameKey,prefix] of CAREERS){
  const {default:career}=await import(new URL(`../public/js/careers/${id}.js`,import.meta.url));
  const {tasks,content,hidden}=dump[id],cmd=prefix+'step';

  test(`${id}: every ${kind} comes from the server without the answer key or telling ids`,()=>{
    assert.ok(Object.keys(tasks).length>=6,Object.keys(tasks).join(','));
    assert.equal(hidden.needs,null,'nothing of the job before it is read');
    for(const t of Object.values(tasks)){
      assert.equal(t._key,undefined);
      assert.equal(t.first[nameKey],undefined,'the server does not send the kind before the first step');
      for(const st of t.needs.steps)for(const o of st.options||[])assert.match(o.id,/^[a-j]$/);
    }
    assert.ok(content.rules.length>5&&content.intro.title);
  });

  for(const [name,task] of Object.entries(tasks)){
    test(`${id} ${name}: every step renders its own answer area and payload`,()=>{
      const steps=task.needs.steps;
      for(let at=0;at<steps.length;at++){
        const t={...task,at,quality:100,needs:at===0?task.first:task.needs},html=career.job(t,harness(id)),st=steps[at];
        assert.match(html,new RegExp(`career-job sk slip ${id}`));
        assert.ok(html.includes(esc(st.title)),`${st.id} shows its title`);
        assert.ok(html.includes(`Bước ${at+1}/${steps.length}`));
        assert.doesNotMatch(html,/undefined|NaN|\[object Object\]|_key/);
        if(at===0)assert.ok(!ticketOf(html).includes(esc(task.needs[nameKey])),'the ticket does not name the kind before it is settled');
        else assert.ok(ticketOf(html).includes(esc(task.needs[nameKey])),'settled: the ticket names it');
        if(st.type==='choice'){
          for(const o of st.options)assert.ok(html.includes(esc(JSON.stringify({task:t.id,step:st.id,value:o.id}))),`${st.id} option ${o.id}`);
          assert.ok(html.includes(`data-command="${cmd}"`));
        }else if(st.type==='number'){
          assert.match(html,/inputmode="numeric"/);assert.match(html,/car:amtSend/);
          if(st.unit)assert.ok(html.includes(`<small>${esc(st.unit)}</small>`),`${st.id} shows its unit`);
        }else{
          assert.ok(html.includes(`data-pick="${st.type}"`));assert.match(html,/car:slPick/);
          assert.match(html,/sl-send"[^>]* disabled/,'the send button waits for the picks');
          for(const o of st.options)assert.ok(html.includes(esc(o.label)));
        }
      }
      const done=career.job({...task,at:steps.length,quality:88,paid:7},harness(id));
      assert.match(done,/chất lượng 88%/);assert.doesNotMatch(done,/sl-step"/);
    });
  }

  test(`${id}: intro, idle without an orders card, notebook page and the desk card`,()=>{
    const intro=career.job(Object.values(tasks)[0],harness(id,{intro:false}));
    assert.ok(intro.includes(`data-command="${prefix}intro"`));
    const idle=career.idle(harness(id));
    assert.doesNotMatch(idle,/sl-orders|đơn người chơi/);assert.match(idle,/📊 Hôm nay: 1/);assert.ok(idle.includes(esc(content.rules[1])));
    assert.match(career.page('car:notes',harness(id)),/sk-notes-page/);
    const ev={emoji:'🐈',title:'Mèo nhảy lên bàn',text:'Một bé mèo nằm lì.',tone:'calm',options:[{id:'a',label:'Bế xuống',cost:0}]};
    const desk=career.idle(harness(id,{desk:{ev,last:null,log:[]}}));
    assert.ok(desk.includes(esc(JSON.stringify({option:'a'}))));assert.ok(desk.includes(`data-command="${prefix}desk"`));
    assert.match(career.job({...hidden},harness(id)),/sk-ask/);
  });
}

/* ---------------------------------------------------------------- the browser walk (needs a disposable PostgreSQL) */
const DB=process.env.TEST_DATABASE_URL||'';
const SHOTS=process.env.MNL_SHOTS||'C:/Users/ADMIN/AppData/Local/Temp/claude/d--projects-Mot-ngay-lam-nghe/66d07a12-c696-4067-9738-df8be7ede1b5/scratchpad/kol';
const CHROMIUM='file:///C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs';
const CMD=async([action,payload,career])=>{
  const st=await fetch('/api/state').then(r=>r.json());
  const csrf=(await fetch('/api/bootstrap').then(r=>r.json())).csrf;
  const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':csrf},
    body:JSON.stringify({request_id:crypto.randomUUID(),expected_revision:st.revision,career:career||st.state.current,action,payload})});
  const d=await r.json();return {status:r.status,error:d.error||null};
};
const ACT=([a,data])=>{const b=document.createElement('button');b.dataset.action=a;Object.entries(data||{}).forEach(([k,v])=>b.dataset[k]=v);b.hidden=true;document.body.append(b);b.click();b.remove();};
const SEND=([c,p])=>{const b=document.createElement('button');b.dataset.command=c;b.dataset.payload=JSON.stringify(p||{});b.hidden=true;document.body.append(b);b.click();b.remove();};
const SHEET='#sheet[open]';
const freePort=()=>new Promise(r=>{const s=createServer();s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>r(p));});});

test('browser: one deal, one set and one scene to the end at 390×844, both layouts',{skip:!DB.startsWith('postgres')||!existsSync(new URL(CHROMIUM))?'set TEST_DATABASE_URL (and Playwright) for the browser walk':false,timeout:900000},async()=>{
  const {chromium}=await import(CHROMIUM);
  mkdirSync(SHOTS,{recursive:true});
  const port=await freePort(),tmp=mkdtempSync(join(tmpdir(),'mnl-kol-'));
  const env={...process.env,QUIET:'1',PUSH_DISABLED:'1',MNL_DEV:'1',PYTHONUTF8:'1'};
  for(const k of ['DATABASE_URL','MNL_CAREERS','LLM_API_KEY'])delete env[k];
  const srv=spawn(PY,[process.env.MNL_SERVE||'server.py','--port',String(port),'--namespace',join(tmp,'g.db')],{cwd:ROOT,env,stdio:'ignore'});
  const base=`http://127.0.0.1:${port}`;
  for(let i=0;i<900;i++){try{if((await fetch(base+'/api/health')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  const browser=await chromium.launch({headless:true});
  const errors=[],overflow=[];
  try{
    const ctx=await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true,deviceScaleFactor:1});
    const page=await ctx.newPage();page.on('pageerror',e=>errors.push(String(e).slice(0,300)));
    const wait=ms=>page.waitForTimeout(ms);
    const shot=async name=>{
      await page.screenshot({path:join(SHOTS,name+'.png')});
      const o=await page.evaluate(()=>{const d=document.documentElement,s=document.querySelector('#sheet[open] .sheet-body')||d;return d.scrollWidth>d.clientWidth+1||s.scrollWidth>s.clientWidth+1;});
      if(o)overflow.push(name);
    };
    const settle=async()=>{for(let i=0;i<3;i++){await page.evaluate(()=>{document.querySelector('#wnDialog[open] .wn-foot [data-wn="close"]')?.click();document.querySelector('#interfacePrompt[open] .btn.primary')?.click();});await wait(300);}};
    const career=async id=>(await page.evaluate(()=>fetch('/api/state').then(r=>r.json()))).state.careers[id];
    const bench=async()=>{await page.evaluate(ACT,['workbench',{}]);await wait(900);await page.evaluate(()=>document.querySelector('#coachLayer [data-coach-btn="off"],#coachChip [data-chip="x"]')?.click());};
    const layout=async side=>{await page.evaluate(v=>{try{localStorage.setItem('mnl.clean',v);localStorage.removeItem('mnl.clean.c');localStorage.setItem('mnl.coach.off','1');}catch{}},side);
      await page.reload();await page.waitForSelector('#app:not([hidden])',{timeout:30000});await wait(1000);await settle();};
    const keyOf=(id,fn,t)=>{const [,day,slot]=t.id.split('-').map(Number);
      return py(`import json\nfrom game.careers import ${id} as m\nprint(json.dumps(m.${fn}(${day},${slot})['key']))`);};
    const desk=async(prefix,n)=>{
      const opt=page.locator(`${SHEET} .sk-event .sk-opt:not([disabled])`);
      if(!await opt.count())return n;
      await page.locator(`${SHEET} .sk-event`).first().scrollIntoViewIfNeeded();await shot(`${prefix}-desk`);
      await opt.first().click();await wait(700);return n+1;
    };
    const answer=async(scope,st,want)=>{
      if(st.type==='choice'){
        await page.evaluate(([scope,v])=>{const b=[...document.querySelectorAll(scope+' .sl-option')].find(e=>JSON.parse(e.dataset.payload).value===v);b.scrollIntoView({block:'center'});b.click();},[scope,want]);
      }else if(st.type==='order'||st.type==='multi'){
        for(const v of want){await page.locator(`${scope} .sl-pick[data-id="${v}"]`).first().click();await wait(120);}
        await page.locator(`${scope} .sl-send`).first().click();
      }else{
        const box=page.locator(`${scope} [data-sk-amt]`).first();await box.fill(String(want));await box.dispatchEvent('input');
        await page.locator(`${scope} .sk-amt-go`).first().click();
      }
      await wait(900);
    };
    const wrongOf=(st,want)=>st.type==='choice'?st.options.find(o=>o.id!==want).id:st.type==='number'?want+7:st.type==='order'?[...want].reverse():st.options.map(o=>o.id).filter(v=>!want.includes(v)).slice(0,1);

    async function play(id,fn,prefix){
      let wrong=false,desks=0;
      await bench();await shot(`${prefix}-01-intro`);
      if(await page.locator(`${SHEET} .sk-intro-go`).count()){await page.locator(`${SHEET} .sk-intro-go`).click();await wait(900);}
      const c0=await career(id),tid=c0.tasks.find(t=>t.status!=='completed').id;
      for(let n=0;n<40;n++){
        desks=await desk(prefix,desks);
        const t=(await career(id)).tasks.find(x=>x.id===tid);
        if(t.status==='completed'){await page.locator(`${SHEET} .sl-finished`).first().scrollIntoViewIfNeeded().catch(()=>{});await shot(`${prefix}-09-done`);return {t,wrong,desks};}
        if(!t.known){await page.evaluate(ACT,['job',{task:tid}]);await wait(500);await shot(`${prefix}-02-ask`);await page.locator(`${SHEET} .sk-ask`).click();await wait(900);continue;}
        const key=keyOf(id,fn,t),st=t.needs.steps[t.at];
        await page.locator(`${SHEET} .sl-step`).first().scrollIntoViewIfNeeded();await shot(`${prefix}-03-step-${String(t.at).padStart(2,'0')}-${st.type}`);
        if(!wrong){
          wrong=true;await answer(`${SHEET} .sl-step`,st,wrongOf(st,key[st.id]));
          const last=await page.locator(`${SHEET} .sl-last`).innerText();assert.match(last,/Chưa đúng/,'a wrong answer says so and stays open');
          await page.locator(`${SHEET} .sl-last`).scrollIntoViewIfNeeded();await shot(`${prefix}-04-wrong`);
          continue;
        }
        await answer(`${SHEET} .sl-step`,st,key[st.id]);
      }
      throw new Error(prefix+': the job did not finish');
    }

    await page.goto(base);await page.waitForSelector('#app:not([hidden])',{timeout:30000});await wait(700);await settle();
    const results=[];
    for(const [id,,,,fn] of CAREERS){
      let r=await page.evaluate(CMD,['select_career',{},id]);assert.equal(r.status,200,JSON.stringify(r));
      if(id!=='kol'){
        const posting=id==='singer'?'singer-maychieu':'actor-benmay';
        r=await page.evaluate(CMD,['job_quick',{posting,confirm:true},id]);assert.equal(r.status,200,JSON.stringify(r));
      }
      await page.evaluate(CMD,['settings',{newInterface:true,interfacePromptSeen:true},id]);
      await layout('on');
      await page.evaluate(SEND,['start_day',{}]);await wait(1500);
      const out=await play(id,fn,id);
      assert.equal(out.t.status,'completed');assert.ok(out.t.quality<100,'the wrong answer cost quality');
      results.push(`${id} q${out.t.quality} paid ${out.t.paid} (${out.desks} desk)`);
      await layout('off');await bench();
      assert.ok(await page.locator(`${SHEET} .career-job.${id}`).count());await shot(`${id}-10-full`);
      await layout('on');
      await page.evaluate(SEND,['end_day',{carry_event:true}]);await wait(1500);await settle();
      await page.evaluate(()=>document.querySelectorAll('dialog[open] [data-action="close"]').forEach(b=>b.click()));
    }
    assert.deepEqual(errors,[],'no page errors');
    assert.deepEqual(overflow,[],'nothing wider than the phone');
    console.log(`kol-singer-actor browser: ${results.join(', ')}; shots in ${SHOTS}`);
    await ctx.close();
  }finally{await browser.close();srv.kill();}
});
