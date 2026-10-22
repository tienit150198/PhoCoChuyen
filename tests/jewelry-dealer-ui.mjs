// 💍 Tiệm vàng Ngọc Mây and 🚗 Đại lý xe Phố Mây workbenches (careers/jewelry.js, car_dealer.js on careers/slip_kit.js).
// In node: every kind of slip renders from real server tasks (python json dump) with escaped text, step payloads that
// name the open step, no answer key, and no piece / vehicle / accessory on the slip before the first step picks it; the
// gold board shows today's prices against yesterday's only once the shop is open; the showroom links the garage for the
// player's own vehicle; the players' orders card (GET /api/svc/inbox) shows take / step / Giao for car services.
// In a browser (only with TEST_DATABASE_URL, a disposable PostgreSQL database): a dev server, the morning slip and one
// customer of each career played to the end at 390×844 in the compact layout (one wrong answer first, the desk card when
// it shows), a player's car service worked in the card, and the full layout drawn. Screenshots go to MNL_SHOTS
// (default: the session scratchpad); MNL_SERVE runs another launcher of server.py.
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
from game.careers import jewelry, car_dealer
out = {}
for mod in (jewelry, car_dealer):
    seen = {}
    for day in (30, 31, 32, 33, 34, 35):
        for slot in range(12):
            t = dict(mod.make_task(day, slot, 1), known=True)
            key = t['kind'] + ('-loan' if (t['needs'].get('loan') or {}).get('principal') else '')
            if key in seen:
                continue
            first = mod.public_task(t)['needs']
            seen[key] = dict(mod.public_task(dict(t, at=1, held=True)), first=first)
    svc = {s: mod.svc_job('sv_' + '0' * 24, s)[0] for s in getattr(mod, 'SERVICES', ())}
    extra = dict(board=jewelry.board(30), board_prev=jewelry.board(29)) if mod is jewelry else {}
    out[mod.ID] = dict(tasks=seen, content=mod.content(), svc=svc, hidden=mod.public_task(mod.make_task(30, 1, 1)), extra=extra)
print(json.dumps(out, ensure_ascii=False))
`);

const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const data=(id,extra={})=>({intro:true,today:{day:30,jobs:1,good:1,earned:9},stats:{jobs:5,good:4,active_days:2,earned:40,sold:1,bought:1,traded:0,refused:0,svc:0},
  closed_day:0,open_day:30,opened:true,desk:{ev:null,last:null,log:[]},svc:[],svc_ok:[],mastered:false,expert:false,...dump[id].extra,...extra});
const harness=(id,extra={},ui={})=>({esc,fmt:String,ui,state:{current:id},icon:()=>'',
  room:{day:30,money:100,data:data(id,extra)},cc:dump[id].content,
  cmd:(label,cmd,p,cls='',disabled=false)=>`<button class="btn ${cls}" data-command="${cmd}" data-payload="${esc(JSON.stringify(p))}"${disabled?' disabled':''}>${label}</button>`,
  npc:()=>({display_name:'Cô Ba Ngọc'}),portrait:()=>'',render(){},toast(){},api:{}});
const ticketOf=html=>html.match(/<article class="sl-ticket[^"]*">[\s\S]*?<\/article>/)?.[0]||'';
const NAMED={jewelry:{ban:'piece_name'},car_dealer:{ban:'model_name',pk:'item_name'}};

for(const [id,prefix] of [['jewelry','vg_'],['car_dealer','dx_']]){
  const {default:career}=await import(new URL(`../public/js/careers/${id}.js`,import.meta.url));
  const {tasks,content,hidden}=dump[id];

  test(`${id}: every kind comes from the server without the answer key and with neutral ids`,()=>{
    const kinds=new Set(Object.values(tasks).map(t=>t.kind));
    assert.deepEqual([...kinds].sort(),(id==='jewelry'?['ban','kc','mua','open']:['ban','hau_mai','open','pk','thu_cu']).sort());
    assert.equal(hidden.needs,null,'nothing of the job before the customer is heard');
    for(const t of Object.values(tasks)){
      assert.equal(t._key,undefined);assert.equal(t.needs.tuoi_key,undefined);
      if(t.needs.loan)assert.equal(t.needs.loan.ok,undefined,'the bank verdict is a step answer');
      for(const st of t.needs.steps)for(const o of st.options||[])assert.match(o.id,/^[a-j]$/);
    }
    assert.ok(content.rules.length>5&&content.intro.title);
  });

  for(const [name,task] of Object.entries(tasks)){
    test(`${id} ${name}: every step renders its own answer area and payload`,()=>{
      const steps=task.needs.steps,named=NAMED[id][task.kind];
      for(let at=0;at<steps.length;at++){
        const t={...task,at,quality:100,needs:at===0?task.first:task.needs},html=career.job(t,harness(id)),st=steps[at];
        assert.match(html,new RegExp(`career-job sk slip ${id}`));
        assert.ok(html.includes(esc(st.title)),`${st.id} shows its title`);
        assert.ok(html.includes(`Bước ${at+1}/${steps.length}`));
        assert.doesNotMatch(html,/undefined|NaN|\[object Object\]|_key/);
        if(named&&at===0){
          assert.equal(task.first[named],undefined,'the server does not name it before it is picked');
          assert.doesNotMatch(ticketOf(html),new RegExp(task.needs[named]),'the slip does not name it either');
          assert.ok(html.includes(`data-command="${prefix}out"`),'out of stock can be referred before the pick');
        }else if(named)assert.ok(ticketOf(html).includes(esc(task.needs[named])),'picked: the slip names it');
        if(at>0)assert.doesNotMatch(html,new RegExp(`data-command="${prefix}out"`));
        if(st.type==='choice'){
          for(const o of st.options)assert.ok(html.includes(esc(JSON.stringify({task:t.id,step:st.id,value:o.id}))),`${st.id} option ${o.id}`);
          assert.ok(html.includes(`data-command="${prefix}step"`));
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

  test(`${id}: intro, idle, notebook page, dock and the desk card`,()=>{
    const intro=career.job(Object.values(tasks)[0],harness(id,{intro:false}));
    assert.ok(intro.includes(`data-command="${prefix}intro"`));
    const idle=career.idle(harness(id));
    assert.match(idle,/📊 Hôm nay: 1/);assert.ok(idle.includes(esc(content.rules[1])));
    assert.match(career.page('car:notes',harness(id)),/sk-notes-page/);
    assert.equal(career.dock[0][0],'inventory');
    const ev={emoji:'🔌',title:'Cúp điện',text:'Cân tắt.',tone:'tense',options:[{id:'a',label:'Lấy cân dự phòng',cost:0}]};
    const desk=career.idle(harness(id,{desk:{ev,last:null,log:[]}}));
    assert.ok(desk.includes(esc(JSON.stringify({option:'a'}))));assert.ok(desk.includes(`data-command="${prefix}desk"`));
    assert.match(career.job({...hidden},harness(id)),/sk-ask/);
  });
}

test('jewelry: the board shows buy and sell against yesterday once the shop is open',async()=>{
  const {default:career}=await import(new URL('../public/js/careers/jewelry.js',import.meta.url));
  const {board,board_prev}=dump.jewelry.extra;
  const html=career.idle(harness('jewelry'));
  assert.match(html,/vg-board/);
  for(const k of ['9999','18k','14k','bac']){
    assert.ok(html.includes(`<td>${board.rows[k].buy}</td><td>${board.rows[k].sell}</td>`),k);
  }
  const d=board.rows['9999'].sell-board_prev.rows['9999'].sell;
  assert.match(html,d>0?/vg-up/:d<0?/vg-down/:/vg-same/);
  assert.match(html,/data-action="inventory"/);
  const closed=career.idle(harness('jewelry',{opened:false}));
  assert.match(closed,/Chưa treo bảng/);assert.doesNotMatch(closed,/vg-table/);
});

test('car_dealer: the player buys a vehicle in the garage; car services come through the orders card',async()=>{
  const {default:career}=await import(new URL('../public/js/careers/car_dealer.js',import.meta.url));
  const x0=harness('car_dealer');
  assert.match(career.idle(x0),/data-action="garage" data-tab="car"/);
  const svc=dump.car_dealer.svc,service=Object.keys(svc)[0],order=i=>`sv_${String(i).padStart(24,'0')}`;
  const items=[{id:order(1),career:'car_dealer',role:'provider',status:'held',service,icon:'🚗',name:'Bảo dưỡng ô tô',qty:1,unit:'chiếc',other:{name:'Bình'}},
    {id:order(2),career:'car_dealer',role:'provider',status:'working',service,icon:'🚗',name:'Xe <B>',qty:1,unit:'chiếc',other:{name:'An'}},
    {id:order(3),career:'moto',role:'provider',status:'working',service:'bao_duong',icon:'🔧',name:'Nghề khác',qty:1,unit:'',other:{name:'Én'}}];
  const step=svc[service][0];
  const extra={svc:[{order:order(2),service,at:0,total:svc[service].length,wrong:0,step}],svc_ok:[]};
  (await import('../public/js/careers/slip_kit.js')).inboxReset();
  let renders=0;const x={...harness('car_dealer',extra),render:()=>{renders++;},api:{json:async()=>({items})}};
  career.meters({querySelector:s=>s==='[data-sl-orders]'?{}:null},x);await new Promise(r=>setTimeout(r,10));
  assert.equal(renders,1);
  const html=career.idle(x);
  assert.ok(html.includes('data-coach="car_dealer-orders"'));
  assert.match(html,/car:slTake[^>]*data-order="sv_0+1"/);
  assert.ok(html.includes('data-command="dx_svc"')||step.type!=='choice');
  assert.match(html,/Xe &lt;B&gt;/);assert.doesNotMatch(html,/Nghề khác/);
});

/* ---------------------------------------------------------------- the browser walk (needs a disposable PostgreSQL) */
const DB=process.env.TEST_DATABASE_URL||'';
const SHOTS=process.env.MNL_SHOTS||'C:/Users/ADMIN/AppData/Local/Temp/claude/d--projects-Mot-ngay-lam-nghe/66d07a12-c696-4067-9738-df8be7ede1b5/scratchpad/luxbiz/shots';
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

test('browser: the morning slip and a customer of each career at 390×844, a car service, both layouts',{skip:!DB.startsWith('postgres')||!existsSync(new URL(CHROMIUM))?'set TEST_DATABASE_URL (and Playwright) for the browser walk':false,timeout:900000},async()=>{
  const {chromium}=await import(CHROMIUM);
  mkdirSync(SHOTS,{recursive:true});
  const port=await freePort(),tmp=mkdtempSync(join(tmpdir(),'mnl-vgdx-'));
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
      return py(`import json\nfrom game.careers import ${id} as m\nprint(json.dumps(m.slip(${day},${slot})[2]))`);};
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

    async function play(id,prefix,tid,tag){
      let wrong=false,desks=0;
      await page.evaluate(ACT,['job',{task:tid}]);await wait(900);
      for(let n=0;n<40;n++){
        desks=await desk(prefix,desks);
        const t=(await career(id)).tasks.find(x=>x.id===tid);
        if(t.status==='completed'){await shot(`${prefix}-${tag}-9-done`);return {t,wrong,desks};}
        if(!t.known){await shot(`${prefix}-${tag}-0-ask`);await page.locator(`${SHEET} .sk-ask`).click();await wait(900);continue;}
        const key=keyOf(id,t),st=t.needs.steps[t.at];
        await page.locator(`${SHEET} .sl-step`).first().scrollIntoViewIfNeeded();await shot(`${prefix}-${tag}-1-step-${String(t.at).padStart(2,'0')}-${st.type}`);
        if(!wrong){
          wrong=true;await answer(`${SHEET} .sl-step`,st,wrongOf(st,key[st.id]));
          const last=await page.locator(`${SHEET} .sl-last`).innerText();assert.match(last,/Chưa đúng/,'a wrong answer says so and stays open');
          await page.locator(`${SHEET} .sl-last`).scrollIntoViewIfNeeded();await shot(`${prefix}-${tag}-2-wrong`);
          continue;
        }
        await answer(`${SHEET} .sl-step`,st,key[st.id]);
      }
      throw new Error(`${prefix} ${tag}: the job did not finish`);
    }

    async function shop(id,prefix){
      let r=await page.evaluate(CMD,['select_career',{},id]);assert.equal(r.status,200,JSON.stringify(r));
      await page.evaluate(CMD,['settings',{newInterface:true,interfacePromptSeen:true},id]);
      await layout('on');
      await page.evaluate(SEND,['start_day',{}]);await wait(1500);
      await bench();await shot(`${prefix}-0-intro`);
      if(await page.locator(`${SHEET} .sk-intro-go`).count()){await page.locator(`${SHEET} .sk-intro-go`).click();await wait(900);}
      const c0=await career(id),open=c0.tasks.find(t=>t.kind==='open');
      assert.ok(open&&open.status!=='completed','the day starts with the morning slip');
      const morning=await play(id,prefix,open.id,'a-open');
      assert.equal((await career(id)).data.opened,true);
      const c1=await career(id),next=c1.tasks.find(t=>t.kind!=='open'&&!['completed','referred','cancelled'].includes(t.status));
      assert.ok(next,'a customer is waiting');
      const customer=await play(id,prefix,next.id,`b-${next.kind}`);
      assert.ok(customer.t.quality<100,'the wrong answer cost quality');
      return {morning,customer};
    }

    async function carService(){
      const id='car_dealer',order='sv_'+'ab'.repeat(12),service=Object.keys(dump[id].svc)[0];
      const r=await page.evaluate(CMD,['dx_svc',{order,service},id]);assert.equal(r.status,200,JSON.stringify(r));
      await layout('on');await bench();
      if(await page.locator(`${SHEET} [data-action="nextJob"]`).count()){await page.locator(`${SHEET} [data-action="nextJob"]`).first().click();await wait(900);}
      try{await page.waitForSelector(`${SHEET} [data-coach="${id}-orders"] .sl-step`,{timeout:15000});}
      catch(e){await shot('dx-c-debug');const c=await career(id);
        throw new Error(`no order step: svc=${JSON.stringify(c.data.svc)} sheet=${await page.evaluate(()=>(document.querySelector('#sheet[open]')?.innerText||'none').slice(0,600))}`);}
      const key=py(`import json\nfrom game.careers import ${id} as m\nprint(json.dumps(m.svc_job('${order}','${service}')[1]))`);
      for(let n=0;n<8;n++){
        const job=((await career(id)).data.svc||[]).find(j=>j.order===order);
        if(!job)break;
        await page.locator(`${SHEET} [data-coach="${id}-orders"]`).scrollIntoViewIfNeeded();await shot(`dx-c-order-${job.at}`);
        await answer(`${SHEET} [data-coach="${id}-orders"] .sl-step`,job.step,key[job.step.id]);
      }
      assert.ok((await career(id)).data.svc_ok.includes(order),'the car service is finished in the career save');
    }

    await page.goto(base);await page.waitForSelector('#app:not([hidden])',{timeout:30000});await wait(700);await settle();
    const vg=await shop('jewelry','vg');
    await layout('off');await bench();
    assert.ok(await page.locator(`${SHEET} .career-job.jewelry`).count());await shot('vg-z-full');
    await layout('on');
    await page.evaluate(SEND,['end_day',{carry_event:true}]);await wait(1500);await settle();
    await page.evaluate(()=>document.querySelectorAll('dialog[open] [data-action="close"]').forEach(b=>b.click()));
    const dx=await shop('car_dealer','dx');
    await carService();
    await layout('off');await bench();
    assert.ok(await page.locator(`${SHEET} .career-job.car_dealer`).count());await shot('dx-z-full');
    assert.deepEqual(errors,[],'no page errors');
    assert.deepEqual(overflow,[],'nothing wider than the phone');
    console.log(`jewelry-dealer browser: vg ${vg.customer.t.kind} q${vg.customer.t.quality}, dx ${dx.customer.t.kind} q${dx.customer.t.quality}; shots in ${SHOTS}`);
    await ctx.close();
  }finally{await browser.close();srv.kill();}
});
