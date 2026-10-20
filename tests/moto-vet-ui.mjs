// 🏍️ Tiệm sửa xe Út Lanh and 🩺 Phòng khám Thú y Cỏ May workbenches (careers/moto.js, vet.js on careers/slip_kit.js).
// In node: every fault and every case renders from real server tasks (python json dump) with escaped text, step payloads
// that name the open step, no answer key, and no diagnosis on the ticket before the first step settles it; the players'
// orders card (GET /api/svc/inbox) shows take / step / Giao for this career's orders only.
// In a browser (only with TEST_DATABASE_URL, a disposable PostgreSQL database): a dev server, one moto ticket and one vet
// case played to the end at 390×844 in the compact layout (one wrong answer first, the desk card when it shows), a player
// order worked in the card, and the full layout drawn. Screenshots go to MNL_SHOTS (default: the session scratchpad);
// MNL_SERVE runs another launcher of server.py.
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

const dump=py(`
import json
from game.careers import moto, vet
out = {}
for mod, kind in ((moto, 'fault'), (vet, 'case')):
    seen = {}
    for day in (40, 41, 42, 43):
        for slot in range(12):
            t = dict(mod.make_task(day, slot, 1), known=True)
            # the server hides the diagnosis until the first step is answered: keep both views
            seen.setdefault(t['needs'][kind], dict(mod.public_task(dict(t, at=1)), first=mod.public_task(t)['needs']))
    svc = {s: mod.svc_job('sv_' + '0' * 24, s)[0] for s in mod.SERVICES}
    out[mod.ID] = dict(tasks=seen, content=mod.content(), svc=svc, hidden=mod.public_task(mod.make_task(40, 0, 1)))
print(json.dumps(out, ensure_ascii=False))
`);

const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const data=(extra={})=>({intro:true,today:{day:3,jobs:1,good:1,earned:9,bonus:4},stats:{jobs:5,good:4,active_days:2,earned:40,bonus:12,svc:1},
  closed_day:0,desk:{ev:null,last:null,log:[]},svc:[],svc_ok:[],mastered:false,expert:false,...extra});
const harness=(id,extra={},ui={})=>({esc,fmt:String,ui,state:{current:id},icon:()=>'',
  room:{day:3,money:100,data:data(extra)},cc:dump[id].content,
  cmd:(label,cmd,p,cls='',disabled=false)=>`<button class="btn ${cls}" data-command="${cmd}" data-payload="${esc(JSON.stringify(p))}"${disabled?' disabled':''}>${label}</button>`,
  npc:()=>({display_name:'Út Lanh'}),portrait:()=>'',render(){},toast(){},api:{}});
const ticketOf=html=>html.match(/<article class="sl-ticket">[\s\S]*?<\/article>/)?.[0]||'';
const personOf=html=>html.match(/<article class="card sk-ticket">[\s\S]*?<\/article>/)?.[0]||'';

for(const [id,kind,cmd,svcCmd] of [['moto','fault','xm_step','xm_svc'],['vet','case','ty_step','ty_svc']]){
  const url=new URL(`../public/js/careers/${id}.js`,import.meta.url);
  const {default:career}=await import(url);
  const {tasks,content,svc,hidden}=dump[id];
  const nameKey=id==='moto'?'fault_name':'case_name';

  test(`${id}: every ${kind} comes from the server without the answer key or neutral-looking ids`,()=>{
    assert.ok(Object.keys(tasks).length>=(id==='moto'?8:5),Object.keys(tasks).join(','));
    assert.equal(hidden.needs,null,'nothing of the job before the customer is heard');
    for(const t of Object.values(tasks)){
      assert.equal(t._key,undefined);
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
        if(at===0){
          assert.equal(task.first[nameKey],undefined,'the server does not send the name before the first step');
          assert.doesNotMatch(ticketOf(html),new RegExp(task.needs[nameKey]),'the ticket does not name the diagnosis before it is made');
          assert.doesNotMatch(personOf(html),new RegExp(task.needs[nameKey].toLowerCase()),'nor does the customer card');
        }else assert.ok(ticketOf(html).includes(esc(task.needs[nameKey])),'settled: the ticket names it');
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

  test(`${id}: tapped picks fill in order, undo, and send the sequence`,async()=>{
    const task=Object.values(tasks).find(t=>t.needs.steps.some(s=>s.type==='order'));
    const at=task.needs.steps.findIndex(s=>s.type==='order'),st=task.needs.steps[at],t={...task,at},ui={};
    const x=harness(id,{},ui),key=`${t.id}-${st.id}`;
    for(const o of [...st.options].reverse())await career.actions.slPick({key,id:o.id},null,x);
    let html=career.job(t,x);
    const want=[...st.options].reverse().map(o=>o.id);
    assert.ok(html.includes(esc(JSON.stringify({task:t.id,step:st.id,value:want}))));
    assert.doesNotMatch(html,/sl-send"[^>]* disabled/);
    await career.actions.slPick({key,id:want[0]},null,x);   // tap again: off
    html=career.job(t,x);assert.match(html,/sl-send"[^>]* disabled/);
    await career.actions.slClear({key},null,x);assert.deepEqual(ui.slPick[key],[]);
  });

  test(`${id}: a reading of 0 can be written on the ticket`,async()=>{
    const sent=[],x={...harness(id,{},{amt:{k:0}}),send:async(c,p)=>sent.push([c,p])};
    await career.actions.amtSend({key:'k',def:'0',cmd,field:'value',extra:JSON.stringify({task:'t',step:'s'})},null,x);
    assert.deepEqual(sent,[[cmd,{task:'t',step:'s',value:0}]]);
  });

  test(`${id}: intro, idle, notebook page and the desk card`,()=>{
    const intro=career.job(Object.values(tasks)[0],harness(id,{intro:false}));
    assert.ok(intro.includes(`data-command="${id==='moto'?'xm_intro':'ty_intro'}"`));
    const idle=career.idle(harness(id));
    assert.match(idle,/sl-orders/);assert.match(idle,/📊 Hôm nay: 1/);assert.ok(idle.includes(esc(content.rules[1])));
    assert.match(career.page('car:notes',harness(id)),/sk-notes-page/);
    const ev={emoji:'🐈',title:'Mèo nhảy lên yên',text:'Một bé mèo nằm lì.',tone:'calm',options:[{id:'a',label:'Bế xuống',cost:0}]};
    const desk=career.idle(harness(id,{desk:{ev,last:null,log:[]}}));
    assert.ok(desk.includes(esc(JSON.stringify({option:'a'}))));assert.ok(desk.includes(`data-command="${id==='moto'?'xm_desk':'ty_desk'}"`));
    const unknown=career.job({...hidden},harness(id));
    assert.match(unknown,/sk-ask/);
  });

  test(`${id}: the players' orders card lists this career's orders: take, steps, Giao`,async()=>{
    const order=i=>`sv_${String(i).padStart(24,'0')}`,service=Object.keys(svc)[0];
    const items=[{id:order(1),career:id,role:'provider',status:'held',service,icon:'🔧',name:'Đơn A',qty:1,unit:'',other:{name:'Bình'}},
      {id:order(2),career:id,role:'provider',status:'working',service,icon:'🔧',name:'Đơn <B>',qty:2,unit:'chiếc',other:{name:'An'},note:'Xe đỏ'},
      {id:order(3),career:id,role:'provider',status:'working',service,icon:'🔧',name:'Đơn C',qty:1,unit:'',other:{name:'Chi'}},
      {id:order(4),career:id,role:'buyer',status:'working',service,icon:'🔧',name:'Của tôi',qty:1,unit:'',other:{name:'Dũng'}},
      {id:order(5),career:'radio',role:'provider',status:'working',service:'ad',icon:'📢',name:'Nghề khác',qty:1,unit:'',other:{name:'Én'}}];
    const step=svc[service][0];
    const extra={svc:[{order:order(2),service,at:0,total:svc[service].length,wrong:1,step},{order:order(4),service,at:0,total:svc[service].length,wrong:0,step}],svc_ok:[order(3)]};
    (await import('../public/js/careers/slip_kit.js')).inboxReset();
    let renders=0;const x={...harness(id,extra),render:()=>{renders++;},api:{json:async()=>({items})}};
    const root={querySelector:s=>s==='[data-sl-orders]'?{}:null};
    career.meters(root,x);await new Promise(r=>setTimeout(r,10));
    assert.equal(renders,1,'the card redraws once the inbox arrives');
    const html=career.idle(x);
    assert.ok(html.includes(`data-coach="${id}-orders"`));
    assert.match(html,/car:slTake[^>]*data-order="sv_0+1"/);
    assert.ok(html.includes(esc(JSON.stringify({order:order(2),service,step:step.id,value:step.options?.[0]?.id})))||step.type!=='choice');
    assert.ok(html.includes(`data-command="${svcCmd}"`)||step.type==='number');
    assert.match(html,/Đơn &lt;B&gt;/);assert.match(html,/Đã sai 1 lần/);
    assert.ok(html.includes(esc(JSON.stringify({order:order(4),drop:true}))),'an untouched job can be dropped');assert.match(html,/sl-drop/);
    assert.ok(!html.includes(esc(JSON.stringify({order:order(2),drop:true}))),'a job with a mistake is finished, never dropped');
    assert.match(html,/car:slDone[^>]*data-order="sv_0+3"/);
    assert.doesNotMatch(html,/Của tôi|Nghề khác/);
    career.meters(root,x);await new Promise(r=>setTimeout(r,10));
    assert.equal(renders,1,'kept 20 s: no second fetch, no redraw');
  });
}

/* ---------------------------------------------------------------- the browser walk (needs a disposable PostgreSQL) */
const DB=process.env.TEST_DATABASE_URL||'';
const SHOTS=process.env.MNL_SHOTS||'C:/Users/ADMIN/AppData/Local/Temp/claude/d--projects-Mot-ngay-lam-nghe/66d07a12-c696-4067-9738-df8be7ede1b5/scratchpad/careers2';
const CHROMIUM='file:///C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs';
// Page functions (Playwright serializes their source): a command, a client action and a command through the game's delegate.
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

test('browser: one moto ticket and one vet case to the end at 390×844, a player order, both layouts',{skip:!DB.startsWith('postgres')||!existsSync(new URL(CHROMIUM))?'set TEST_DATABASE_URL (and Playwright) for the browser walk':false,timeout:600000},async()=>{
  const {chromium}=await import(CHROMIUM);
  mkdirSync(SHOTS,{recursive:true});
  const port=await freePort(),tmp=mkdtempSync(join(tmpdir(),'mnl-mv-'));
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
    const keyOf=(id,t)=>{const [,day,slot]=t.id.split('-').map(Number);
      return py(`import json\nfrom game.careers import ${id} as m\nprint(json.dumps((m.ticket if '${id}'=='moto' else m.case)(${day},${slot})['key']))`);};
    const desk=async(prefix,n)=>{
      const opt=page.locator(`${SHEET} .sk-event .sk-opt:not([disabled])`);
      if(!await opt.count())return n;
      await page.locator(`${SHEET} .sk-event`).first().scrollIntoViewIfNeeded();await shot(`${prefix}-desk`);
      await opt.first().click();await wait(700);return n+1;
    };
    // One answer, typed the way a player does: tap the option, tap the picks then confirm, or type the number.
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

    async function play(id,prefix){
      let wrong=false,desks=0;
      await bench();await shot(`${prefix}-01-intro`);
      if(await page.locator(`${SHEET} .sk-intro-go`).count()){await page.locator(`${SHEET} .sk-intro-go`).click();await wait(900);}
      const c0=await career(id),tid=c0.tasks.find(t=>t.status!=='completed').id;
      for(let n=0;n<40;n++){
        desks=await desk(prefix,desks);
        const t=(await career(id)).tasks.find(x=>x.id===tid);
        if(t.status==='completed'){await shot(`${prefix}-09-done`);return {t,wrong,desks};}
        if(!t.known){await page.evaluate(ACT,['job',{task:tid}]);await wait(500);await shot(`${prefix}-02-ask`);await page.locator(`${SHEET} .sk-ask`).click();await wait(900);continue;}
        const key=keyOf(id,t),st=t.needs.steps[t.at];
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

    async function playerOrder(id,cmd,prefix){
      const order='sv_'+'ab'.repeat(12),service=Object.keys(dump[id].svc)[0];
      await page.evaluate(SEND,[cmd,{order,service}]);await wait(1200);   // through the game: its state follows
      await bench();
      if(await page.locator(`${SHEET} [data-action="nextJob"]`).count()){await page.locator(`${SHEET} [data-action="nextJob"]`).first().click();await wait(900);}
      try{await page.waitForSelector(`${SHEET} [data-coach="${id}-orders"] .sl-step`,{timeout:15000});}
      catch(e){await shot(`${prefix}-debug`);const c=await career(id);
        throw new Error(`no order step: svc=${JSON.stringify(c.data.svc)} sheet=${await page.evaluate(()=>(document.querySelector('#sheet[open]')?.innerText||'none').slice(0,600))}`);}
      const key=py(`import json\nfrom game.careers import ${id} as m\nprint(json.dumps(m.svc_job('${order}','${service}')[1]))`);
      for(let n=0;n<8;n++){
        const job=((await career(id)).data.svc||[]).find(j=>j.order===order);
        if(!job)break;
        const st=job.step;
        await page.locator(`${SHEET} [data-coach="${id}-orders"]`).scrollIntoViewIfNeeded();await shot(`${prefix}-06-order-${job.at}`);
        await answer(`${SHEET} [data-coach="${id}-orders"] .sl-step`,st,key[st.id]);
      }
      const d=(await career(id)).data;
      assert.ok(d.svc_ok.includes(order),'the order is finished in the career save');
      // A second order the buyer walked away from: the open job shows Bỏ đơn, a confirm, and it leaves the book.
      const stale='sv_'+'cd'.repeat(12);
      await page.evaluate(SEND,[cmd,{order:stale,service}]);await wait(1200);
      const drop=page.locator(`${SHEET} .sl-order[data-order="${stale}"] .sl-drop`);
      await drop.waitFor({timeout:15000});await drop.scrollIntoViewIfNeeded();await shot(`${prefix}-07-drop`);
      await drop.click();await wait(400);
      if(await page.locator('#confirmDialog[open]').count()){await shot(`${prefix}-07-drop-confirm`);await page.locator('#confirmDialog[open] [data-action="confirmYes"]').click();}
      await wait(1200);
      assert.ok(!((await career(id)).data.svc||[]).some(j=>j.order===stale),'the dropped job left the book');
    }

    await page.goto(base);await page.waitForSelector('#app:not([hidden])',{timeout:30000});await wait(700);await settle();
    // 🏍️ moto: the owner's shop
    let r=await page.evaluate(CMD,['select_career',{},'moto']);assert.equal(r.status,200,JSON.stringify(r));
    await page.evaluate(CMD,['settings',{newInterface:true,interfacePromptSeen:true},'moto']);
    await layout('on');
    await page.evaluate(SEND,['start_day',{}]);await wait(1500);
    const moto=await play('moto','moto');
    assert.equal(moto.t.status,'completed');assert.ok(moto.t.quality<100,'the wrong answer cost quality');
    await playerOrder('moto','xm_svc','moto');
    await layout('off');await bench();
    assert.ok(await page.locator(`${SHEET} .career-job.moto`).count());await shot('moto-10-full');
    await layout('on');
    await page.evaluate(SEND,['end_day',{carry_event:true}]);await wait(1500);await settle();
    await page.evaluate(()=>document.querySelectorAll('dialog[open] [data-action="close"]').forEach(b=>b.click()));
    // 🩺 vet: hired at the clinic
    r=await page.evaluate(CMD,['select_career',{},'vet']);assert.equal(r.status,200,JSON.stringify(r));
    r=await page.evaluate(CMD,['job_quick',{posting:'vet-comay',confirm:true},'vet']);assert.equal(r.status,200,JSON.stringify(r));
    await layout('on');
    await page.evaluate(SEND,['start_day',{}]);await wait(1500);
    const vet=await play('vet','vet');
    assert.equal(vet.t.status,'completed');assert.ok(vet.t.quality<100);
    await playerOrder('vet','ty_svc','vet');
    await layout('off');await bench();
    assert.ok(await page.locator(`${SHEET} .career-job.vet`).count());await shot('vet-10-full');
    assert.deepEqual(errors,[],'no page errors');
    assert.deepEqual(overflow,[],'nothing wider than the phone');
    console.log(`moto-vet browser: moto q${moto.t.quality} (${moto.desks} desk), vet q${vet.t.quality} (${vet.desks} desk); shots in ${SHOTS}`);
    await ctx.close();
  }finally{await browser.close();srv.kill();}
});
