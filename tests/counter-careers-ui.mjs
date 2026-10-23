// 🍱 Căn tin trường and ✏️ Tiệm văn phòng phẩm workbenches (careers/canteen.js, stationery.js on careers/counter_kit.js).
// In node, from real server tasks and content (python json dump of game/careers/canteen.py, stationery.py): the counter
// shows every good of every shelf with its stock (a service: its material's stock, less what the tray already uses);
// a tile tap is <prefix>add with the task and the item; the tray lists its lines with − / + and the bill; Giao waits for
// a tray; "Đang chờ khách…" with nobody at the counter; the canteen's lunch order shows 🧪 Lưu mẫu (then "Đã lưu mẫu")
// and a rush order the bell chip; the reviews panel lists the feed; intro, desk card, notes page and dock.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {resolve} from 'node:path';
import test from 'node:test';

const ROOT=resolve(import.meta.dirname,'..');
const PY=process.env.PYTHON||'python';
const dump=JSON.parse(execFileSync(PY,['-c',`
import json
from game.careers import canteen, counterkit, stationery
out = {}
for mod in (canteen, stationery):
    tasks = {}
    for day in (1, 3, 5, 9):
        for slot in range(12):
            t = mod.make_task(day, slot, 1)
            key = (t.get('phase') or '') + ':' + t['kind']
            if key not in tasks:
                tasks[key] = dict(mod.public_task(dict(t, known=True)), hidden=mod.public_task(t)['needs'])
    said = set()   # what the counter says: titles, openings (days 1-30) and the words of a wrong tray
    for day in range(1, 31):
        for slot in range(12):
            t = mod.make_task(day, slot, 1)
            said |= {t['title'], t['opening']}
            for tray in ({}, {t['needs']['lines'][0]['any'][0]: 1}, {k: 9 for ln in t['needs']['lines'] for k in ln['any'][:1]},
                         {k: 1 for k in list(mod.SHOP.goods)[:4]}):
                said.add(counterkit.grade(mod.SHOP, dict(t, tray=tray), mod._who_of(t))[1])
    out[mod.ID] = dict(tasks=tasks, content=mod.content(), items=[i['id'] for i in mod.ITEMS], said=sorted(x for x in said if x))
print(json.dumps(out, ensure_ascii=False))
`],{cwd:ROOT,encoding:'utf8',env:{...process.env,PYTHONUTF8:'1'}}));

const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const pay=o=>esc(JSON.stringify(o));
const stockFor=id=>Object.fromEntries(dump[id].items.map((k,i)=>[k,10+i]));
function harness(id,{data={},tasks=[],stock=stockFor(id),feed=[],ui={},open=true}={}){
  return {esc,fmt:String,ui,state:{current:id},icon:()=>'',
    room:{day:5,money:100,open,more_gate:false,metrics:{served:5},rating:4.6,feed,tasks,inventory:{stock},
      data:{intro:true,today:{day:5,jobs:2,good:2,earned:18},stats:{jobs:2,good:2,active_days:1,earned:18,missed:0},desk:{ev:null,last:null,log:[]},
        mastered:false,expert:false,mod:{id:'normal',emoji:'🏫',label:'Ngày học bình thường',hint:'Trống vào lớp lúc 7 giờ.'},...data}},
    cc:dump[id].content,
    cmd:(label,cmd,p,cls='',disabled=false)=>`<button class="btn ${cls}" data-command="${cmd}" data-payload="${pay(p)}"${disabled?' disabled':''}>${label}</button>`,
    button:(label,action,d={},cls='',disabled=false)=>`<button class="btn ${cls}" data-action="${action}"${disabled?' disabled':''}>${label}</button>`,
    npc:()=>({display_name:'Bé Na',role:'Học sinh lớp 2A'}),portrait:()=>'<i class="pt"></i>',render(){},toast(){}};
}
const goods=id=>dump[id].content.shelves.flatMap(s=>s.items);
const taskOf=(id,pred)=>{const t=Object.values(dump[id].tasks).find(pred);assert.ok(t,'a task of that kind');return structuredClone(t);};
const tileOf=(html,prefix,task,item)=>{
  const m=html.match(new RegExp(`<button type="button" class="ck-tile[^"]*" data-command="${prefix}add" data-payload="${pay({task,item}).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}"[^>]*>[\\s\\S]*?</button>`));
  return m?.[0]||'';
};

for(const [id,prefix] of [['canteen','ct_'],['stationery','vp_']]){
  const {default:career}=await import(new URL(`../public/js/careers/${id}.js`,import.meta.url));
  const content=dump[id].content;

  test(`${id}: the module contract`,()=>{
    assert.equal(career.id,id);assert.equal(career.css,true);assert.equal(career.autoNext,true);
    assert.equal(typeof career.job,'function');assert.equal(typeof career.idle,'function');assert.equal(typeof career.next,'function');
    assert.equal(career.dock[0][0],'inventory');assert.ok(career.dock.some(d=>d[0]==='car:notes'));
    assert.ok(content.shelves.length>=4&&content.rules.length>5&&content.intro.title);
  });

  test(`${id}: every good of every shelf is on the counter with its stock; a tap adds it to this customer's tray`,()=>{
    const t=taskOf(id,v=>v.needs&&!v.needs.budget);t.tray={};
    const stock=stockFor(id),html=career.job(t,harness(id,{tasks:[t],stock}));
    assert.match(html,new RegExp(`career-job sk ck-counter ${id}`));
    assert.doesNotMatch(html,/undefined|NaN|\[object Object\]/);
    for(const s of content.shelves)assert.ok(html.includes(esc(s.title)),`shelf ${s.title}`);
    for(const i of goods(id)){
      const tile=tileOf(html,prefix,t.id,i.id);
      assert.ok(tile,`${i.id} has a tile that sends ${prefix}add`);
      assert.ok(tile.includes(esc(i.name))&&tile.includes(`${i.price} xu`),`${i.id} name and price`);
      const left=stock[i.service?i.uses:i.id];
      assert.match(tile,new RegExp(`class="ck-count[^"]*"[^>]*>[^<]*${left}</em>`),`${i.id} shows ${left} on the shelf`);
      assert.doesNotMatch(tile,/ disabled/,`${i.id} can be tapped`);
    }
    assert.match(html,/data-action="inventory"/);
  });

  test(`${id}: the tray lists − / + per line, the bill, and Giao waits for a tray`,()=>{
    const t=taskOf(id,v=>v.needs);
    const empty=career.job({...t,tray:{},bill:0},harness(id,{tasks:[t]}));
    assert.match(empty,new RegExp(`data-command="${prefix}serve"[^>]* disabled`),'Giao is disabled on an empty tray');
    const [a,b]=goods(id).filter(i=>!i.service);
    const tray={[a.id]:2,[b.id]:1},bill=a.price*2+b.price,stock=stockFor(id);
    const html=career.job({...t,tray,bill},harness(id,{tasks:[t],stock}));
    assert.doesNotMatch(html,new RegExp(`data-command="${prefix}serve"[^>]* disabled`),'Giao is ready');
    assert.ok(html.includes(`data-command="${prefix}serve" data-payload="${pay({task:t.id})}"`));
    assert.ok(html.includes(`data-command="${prefix}remove" data-payload="${pay({task:t.id,item:a.id})}"`),'− on a line');
    assert.ok(html.includes(`data-command="${prefix}clear"`),'the tray can be cleared');
    assert.match(html,new RegExp(`<b>${bill} xu</b>`),'the bill');
    assert.match(html,new RegExp(`${a.price*2} xu</span>`),'the line subtotal');
    const tile=tileOf(html,prefix,t.id,a.id);
    assert.match(tile,/ck-tile on/);assert.match(tile,/×2/);
    assert.match(tile,new RegExp(`>${stock[a.id]-2}</em>`),'the shelf shows what is left after the tray');
  });

  test(`${id}: nobody at the counter, a customer not heard yet, an empty shelf`,()=>{
    const idle=career.idle(harness(id));
    assert.match(idle,/Đang chờ khách…/);
    assert.match(idle,/data-command="more_work"/,'one tap calls the next customer');
    assert.doesNotMatch(idle,new RegExp(`data-command="${prefix}serve"`));
    assert.match(career.idle(harness(id,{open:false})),/chưa mở cửa/);
    const t=taskOf(id,v=>v.needs);const hidden={...t,known:false,needs:t.hidden,tray:{}};
    assert.equal(t.hidden,null,'the server sends nothing of the order before it is heard');
    const html=career.job(hidden,harness(id,{tasks:[hidden]}));
    assert.ok(html.includes(`data-command="ask" data-payload="${pay({task:t.id})}"`));
    assert.match(tileOf(html,prefix,t.id,goods(id)[0].id),/ disabled/,'tiles wait for the order');
    const i=goods(id).find(g=>!g.service),stock={...stockFor(id),[i.id]:0};
    const out=tileOf(career.job({...t,tray:{}},harness(id,{tasks:[t],stock})),prefix,t.id,i.id);
    assert.match(out,/ck-tile[^"]* zero/);assert.match(out,/ disabled/);assert.match(out,/>0<\/em>/);
  });

  test(`${id}: a screen reader hears each step and keeps its place (player #497, blind)`,async()=>{
    const t=taskOf(id,v=>v.needs&&!v.needs.budget);t.tray={};
    const hidden={...t,known:false,needs:null},ui={};
    const LIVE=/<p class="sr-only ck-live" aria-live="polite" aria-atomic="true" data-morph-static><\/p>/;
    assert.match(career.job(hidden,harness(id,{tasks:[hidden]})),LIVE);assert.match(career.idle(harness(id)),LIVE);
    assert.match(career.job(t,harness(id,{tasks:[t],data:{intro:false}})),LIVE,'the intro card too, so the line is there before the first step');
    assert.match(career.job(t,harness(id,{tasks:[t]})),/<span class="sr-only">Kiên nhẫn <\/span>/);
    // A page in miniature: the counter's root, its live line, the buttons each step leaves on it.
    const was=globalThis.document,raf=globalThis.requestAnimationFrame,doc={body:{},activeElement:null};
    globalThis.document=doc;globalThis.requestAnimationFrame=()=>0;doc.activeElement=doc.body;
    const live={textContent:'',isConnected:true},btn=()=>({isConnected:true,offsetParent:{},disabled:false,focus(){doc.activeElement=this;},matches:()=>false});
    let buttons={};
    const root={dataset:{ckTask:t.id},querySelector:q=>q==='.ck-live'?live:null,querySelectorAll:q=>buttons[q]||[],contains:el=>!!el&&el!==doc.body};
    const wait=()=>new Promise(r=>setTimeout(r,220));
    try{
      const ask=btn();buttons={'.ck-ask':[ask]};doc.activeElement=ask;
      career.tick(root,harness(id,{tasks:[hidden],ui}));await wait();
      assert.equal(live.textContent,'','the first look says nothing (the reader reads the screen)');
      const tile=btn();buttons={'.ck-tile:not([disabled])':[tile]};doc.activeElement=doc.body;   // Hỏi khách left the page
      career.tick(root,harness(id,{tasks:[t],ui}));
      assert.equal(doc.activeElement,tile,'the focus goes on to the shelf, not to <body>');
      await wait();assert.ok(live.textContent.includes(t.opening.slice(-12)),'what the customer asked for is said');
      const next={...hidden,id:t.id+'n'},done={...t,status:'completed',stage:'done',lines:['Giao đủ cho Bé Na. Thu 12 xu.']},ask2=btn();
      root.dataset.ckTask=next.id;buttons={'.ck-ask':[ask2]};doc.activeElement=doc.body;   // Giao: the next customer
      career.tick(root,harness(id,{tasks:[done,next],ui}));
      assert.equal(doc.activeElement,ask2,'the next customer\'s Hỏi khách cần gì');
      await wait();assert.match(live.textContent,/^Giao đủ cho Bé Na\. Thu 12 xu\. · Bé Na: /,'the outcome, then who is next');
      career.tick(root,harness(id,{tasks:[done,next],ui}));await wait();
      assert.match(live.textContent,/^Giao đủ/,'nothing new: nothing said again');
      doc.activeElement={outside:true,isConnected:true};root.contains=el=>el===ask2;
      career.tick(root,harness(id,{tasks:[done,next],ui}));
      assert.ok(doc.activeElement.outside,'focus the player put elsewhere stays there');
    }finally{globalThis.document=was;globalThis.requestAnimationFrame=raf;}
  });

  test(`${id}: the reviews panel, the queue, the intro, the desk card and the notes page`,()=>{
    const feed=[{author:'Chị <Thảo>',stars:5,text:'Bán đúng giá, hỏi kỹ dị ứng.',day:4},{author:'Anh Tuấn',stars:3,text:'Hơi lâu.',day:5},{text:'tin phố',day:5}];
    const idle=career.idle(harness(id,{},));
    assert.match(idle,/Chưa có đánh giá nào/);
    const html=career.idle(harness(id,{feed}));
    assert.match(html,/⭐ Đánh giá/);assert.match(html,/Chị &lt;Thảo&gt;/);assert.match(html,/Hơi lâu\./);
    assert.match(html,/aria-label="5 sao"/);assert.match(html,/4\.6/);assert.doesNotMatch(html,/tin phố/);
    const t1=taskOf(id,v=>v.needs),t2={...structuredClone(t1),id:t1.id+'b',patience:30};
    const q=career.job(t1,harness(id,{tasks:[t1,t2]}));
    assert.ok(q.includes(`data-command="task_select" data-payload="${pay({task:t2.id})}"`),'switch to another customer');
    assert.match(q,/ck-guest on/);
    const intro=career.job(t1,harness(id,{data:{intro:false}}));
    assert.ok(intro.includes(`data-command="${prefix}intro"`));assert.doesNotMatch(intro,/ck-tile/);
    const ev={emoji:'💦',title:'Đổ nước',text:'Sàn ướt.',tone:'tense',options:[{id:'mop',label:'Lau ngay',cost:0}]};
    const desk=career.job(t1,harness(id,{data:{desk:{ev,last:null,log:[]}},tasks:[t1]}));
    assert.ok(desk.includes(`data-command="${prefix}desk" data-payload="${pay({option:'mop'})}"`));
    assert.match(tileOf(desk,prefix,t1.id,goods(id)[0].id),/ disabled/,'the counter waits for the decision');
    const notes=career.page('car:notes',harness(id));
    assert.match(notes,/sk-notes-page/);assert.ok(notes.includes(esc(content.rules[0])));
    for(const i of goods(id))assert.ok(notes.includes(esc(i.name)),`price board ${i.id}`);
    assert.equal(career.page('other',harness(id)),'');
  });
}

test('canteen: a lunch order shows 🧪 Lưu mẫu until the day is sampled; trays count; a rush order shows the bell',async()=>{
  const {default:career}=await import(new URL('../public/js/careers/canteen.js',import.meta.url));
  const t={...taskOf('canteen',v=>v.phase==='trua'),tray:{}};
  const html=career.job(t,harness('canteen',{tasks:[t],data:{sampled:false,bells:{}}}));
  assert.match(html,/data-command="ct_sample"/);assert.match(html,/🧪 Lưu mẫu/);
  assert.match(html,new RegExp(`🍱 ${t.needs.trays} phần`));
  assert.match(html,/Giao cơm cho lớp/);
  assert.equal(career.next(t,harness('canteen',{tasks:[t],data:{sampled:false}})),'Lưu mẫu thức ăn trưa');
  const done=career.job(t,harness('canteen',{tasks:[t],data:{sampled:true}}));
  assert.doesNotMatch(done,/data-command="ct_sample"/);assert.match(done,/✓ Đã lưu mẫu/);
  const rush={...taskOf('canteen',v=>v.phase==='sang'),tray:{}};
  const r=career.job(rush,harness('canteen',{tasks:[rush],data:{bells:{[rush.id]:4}}}));
  assert.match(r,/🥁 còn 4 nhịp/);assert.match(r,/ck-tag bell hurry/);assert.doesNotMatch(r,/data-command="ct_sample"/);
  assert.match(r,/Giao cho bé/);
  const calm=career.job(rush,harness('canteen',{tasks:[rush],data:{bells:{[rush.id]:null}}}));
  assert.doesNotMatch(calm,/🥁/);
  const allergy=Object.values(dump.canteen.tasks).find(v=>v.needs?.avoid?.length);
  if(allergy){const a=career.job({...allergy,tray:{}},harness('canteen',{tasks:[allergy]}));
    for(const tag of allergy.needs.avoid)assert.ok(a.includes(`🚫 ${dump.canteen.content.tags[tag]}`));}
  const budget=Object.values(dump.canteen.tasks).find(v=>v.needs?.budget!=null);
  if(budget){const g=goods('canteen')[0],k=g.id,over=budget.needs.budget+5;
    const b=career.job({...budget,tray:{[k]:1},bill:over},harness('canteen',{tasks:[budget]}));
    assert.match(b,new RegExp(`💰 ${budget.needs.budget} xu`));assert.match(b,/ck-bill over/);assert.ok(g);}
});

test('stationery: services show their material, + 5 for a big order, Giỏ and Giao cho khách',async()=>{
  const {default:career}=await import(new URL('../public/js/careers/stationery.js',import.meta.url));
  const t={...taskOf('stationery',v=>v.kind==='photo'),tray:{vp_photo:3},bill:15};
  const stock=stockFor('stationery'),html=career.job(t,harness('stationery',{tasks:[t],stock}));
  assert.match(html,/🧺 Giỏ/);assert.match(html,/Giao cho khách/);assert.match(html,/Dọn giỏ/);
  assert.match(html,new RegExp(`🖨️ ${t.needs.sets} bộ × ${t.needs.pages} trang`));
  const tile=tileOf(html,'vp_',t.id,'vp_photo');
  assert.match(tile,new RegExp(`📄${stock.vp_a4-3}</em>`),'photo shows the A4 left after the tray');
  assert.ok(html.includes(`data-command="vp_add" data-payload="${pay({task:t.id,item:'vp_photo',qty:5})}"`),'+5 on a service');
  const list=Object.values(dump.stationery.tasks).find(v=>v.kind==='list');
  if(list){const l=career.job({...list,tray:{}},harness('stationery',{tasks:[list]}));assert.match(l,new RegExp(`🎒 Lớp ${list.needs.grade}`));}
  assert.equal(career.next({...t,tray:{}},harness('stationery')),'Chạm món trên kệ');
  assert.equal(career.next(t,harness('stationery')),'Giao cho khách');
});

test('every visible line of both counters has its English (public/i18n/en.json through v4/i18n.js)',async()=>{
  const {readFileSync}=await import('node:fs');
  globalThis.Node??={ELEMENT_NODE:1,TEXT_NODE:3};globalThis.NodeFilter??={SHOW_TEXT:4,SHOW_ELEMENT:1};
  globalThis.document??={documentElement:{lang:'vi'},body:{nodeType:1,closest(){return false;}},createTreeWalker:()=>({nextNode(){return null;}}),title:''};
  globalThis.MutationObserver??=class {observe(){}};
  globalThis.__mnlBoot={...(globalThis.__mnlBoot||{}),i18n:Promise.resolve(JSON.parse(readFileSync(resolve(ROOT,'public/i18n/en.json'),'utf8')))};
  const {setLanguage,t:tr}=await import('../public/js/v4/i18n.js');await setLanguage('en');
  const VI=/[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i;
  const bad=s=>(s.match(/\p{L}+/gu)||[]).some(w=>VI.test(w)&&w===w.toLowerCase());
  const text=html=>html.split(/<[^>]+>/).map(x=>x.replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').trim()).filter(Boolean);
  const attrs=html=>[...html.matchAll(/(?:title|aria-label|placeholder)="([^"]*)"/g)].map(m=>m[1].replace(/&amp;/g,'&')).filter(Boolean);
  const lines=new Set();
  const add=html=>{for(const x of [...text(html),...attrs(html)])lines.add(x);};
  for(const id of ['canteen','stationery']){
    const {default:career}=await import(new URL(`../public/js/careers/${id}.js`,import.meta.url));
    const [a,b]=goods(id).filter(i=>!i.service);
    for(const task of Object.values(dump[id].tasks)){
      const t=structuredClone(task);
      add(career.job({...t,tray:{}},harness(id,{tasks:[t],data:{sampled:false,bells:{[t.id]:3}}})));
      add(career.job({...t,tray:{[a.id]:2,[b.id]:1},bill:t.needs?.budget!=null?t.needs.budget+5:20},harness(id,{tasks:[t],data:{sampled:true}})));
      add(career.job({...t,known:false,needs:t.hidden,tray:{}},harness(id,{tasks:[t]})));
      lines.add(career.next({...t,tray:{}},harness(id,{tasks:[t],data:{sampled:false}})));
    }
    add(career.idle(harness(id)));add(career.idle(harness(id,{open:false})));
    add(career.job(structuredClone(Object.values(dump[id].tasks)[0]),harness(id,{data:{intro:false}})));
    add(career.page('car:notes',harness(id)));
    for(const ev of dump[id].content.desk||[])add(career.idle(harness(id,{data:{desk:{ev,last:null,log:[]}}})));
    for(const d of career.dock)for(const x of d.slice(2))lines.add(x);
    for(const x of dump[id].said)lines.add(x);
  }
  for(const x of ['Bé Na','Học sinh lớp 2A','Ngày học bình thường','Trống vào lớp lúc 7 giờ.'])lines.delete(x);   // the harness's own stand-ins
  const miss=[...lines].filter(s=>VI.test(s)&&bad(tr(s)));
  assert.deepEqual(miss,[]);
  assert.equal(tr('Mời bạn tiếp theo'),'Next, please');
});
