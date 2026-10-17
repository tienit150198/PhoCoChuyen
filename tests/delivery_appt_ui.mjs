// 📅 Đơn hẹn giờ on the courier page: run by tests/test_delivery_appt_ui.py (engine fixtures on stdin), or alone for
// the pure helpers (no stdin).
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const attrs=new Set();
const store=new Map();
globalThis.localStorage={getItem:k=>store.get(k)??null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
globalThis.document={documentElement:{hasAttribute:a=>attrs.has(a),lang:'vi'},querySelector:()=>null,addEventListener:()=>{},createElement:()=>({getContext:()=>null})};
globalThis.addEventListener=()=>{};
const delivery=await import('../public/js/careers/delivery.js');
const {apptPhase,apptChip,apptRoute,remindDue}=delivery;

/* ---------- helpers ---------- */
const a={day:3,start:60,end:90,call:null,done:null};
assert.deepEqual(apptPhase(a,40),{phase:'before',n:20});
assert.deepEqual(apptPhase(a,70),{phase:'in',n:20,soon:false});
assert.deepEqual(apptPhase(a,85),{phase:'in',n:5,soon:true});
assert.deepEqual(apptPhase(a,97),{phase:'late',n:7});
assert.match(apptChip(a,40),/class="dl-appt "[^>]*>📅 <b>18:00–18:30<\/b> · mở sau 20 phút/);
assert.match(apptChip(a,50),/class="dl-appt info"/,'opens soon: info colour');
assert.match(apptChip(a,85),/class="dl-appt warn"[\s\S]*sắp trễ · còn 5 phút/,'last 10 minutes: the warning colour');
assert.match(apptChip(a,97),/class="dl-appt bad"[\s\S]*trễ 7 phút/);
assert.match(apptChip(a,85,{terse:true}),/⚠️ 5′/,'phone layout: short chip');
assert.match(apptChip(a,85,{terse:true}),/aria-label="Hẹn giao 18:00–18:30, sắp trễ, còn 5 phút"/,'the words stay in aria-label');
const dist=(p,q)=>({hub:{x:1,y:2},apt:{x:6,y:3},villa:{x:5,y:4},market:{x:3,y:2}}[p]?Math.abs({hub:1,apt:6,villa:5,market:3}[p]-{hub:1,apt:6,villa:5,market:3}[q]):0);
const task=(id,pickup,dest,loaded,start)=>({id,known:true,needs:{pickup,dest},run:{loaded,outcome:null},...(start!=null?{appt:{day:3,start,end:start+30,call:null,done:null}}:{})});
assert.deepEqual(apptRoute([task('a','hub','apt',true,90),task('b','market','villa',false,40),task('c','hub','apt',true,null)],'hub',dist),
  ['market','villa','apt'],'pick-ups first, then the earliest booked hand-over');
const marks={'a@3:60':{fired:false}};
const due=remindDue([{id:'a',appt:{day:3,start:60,end:90,done:null}}],48,10,marks);
assert.equal(due.length,0,'not yet: 12 minutes before');
assert.equal(remindDue([{id:'a',appt:{day:3,start:60,end:90,done:null}}],50,10,marks).length,1,'10 minutes before the window');
assert.equal(remindDue([{id:'a',appt:{day:3,start:65,end:95,done:null}}],60,10,marks).length,0,'a booked-again window needs a new reminder');

/* ---------- the real page with engine state ---------- */
let input='';
try{input=readFileSync(0,'utf8');}catch{input='';}
if(input.trim()){
  const f=JSON.parse(input);
  const {careerContext}=await import('../public/js/v4/careers.js');
  const toasts=[];
  const env=state=>({api:{state,content:f.content},ui:{},cmd:()=>{},renderSheet:()=>{},toast:m=>toasts.push(m),confirmAction:async()=>true});
  const page=(state,id=f.task)=>{const x=careerContext(env(state));const t=x.room.tasks.find(r=>r.id===id);return {x,t,html:delivery.default.job(t,x)};};
  for(const layout of ['classic','clean']){
    if(layout==='clean')attrs.add('data-clean');else attrs.delete('data-clean');
    const early=page(f.door_early).html;
    assert.match(early,/class="dl-appt[^"]*"/,`${layout}: the window chip on the order`);
    assert.match(early,/dl-apptbox/);
    assert.match(early,/data-command="dl_appt" data-payload="[^"]*&quot;how&quot;:&quot;wait&quot;/,`${layout}: wait for the window at the door`);
    assert.match(early,/data-command="dl_call"/,`${layout}: at the door “📞 Gọi khách” asks whether to come early`);
    assert.doesNotMatch(early,/&quot;how&quot;:&quot;call&quot;/,`${layout}: no second call button beside it`);
    assert.match(early,/data-action="car:remind"/,`${layout}: ⏰ reminder toggle`);
    assert.doesNotMatch(early,/data-payload="[^"]*(start|end|bonus|fee)&quot;/,'the client never sends times or amounts');
    if(layout==='classic'){
      assert.match(early,/không bao giờ trừ vào ví/,'the deduction is explained before it can happen');
      assert.match(early,/mở sau \d+ phút/);
    }else assert.match(early,/aria-label="Đúng khung hẹn cộng 4 xu/);
    const soon=page(f.door_soon).html;
    assert.match(soon,/class="dl-appt warn"/,`${layout}: last minutes are amber`);
    assert.doesNotMatch(soon,/&quot;how&quot;:&quot;wait&quot;/,'no waiting once the window is open');
    const late=page(f.door_late).html;
    assert.match(late,/class="dl-appt bad"/,`${layout}: late is red`);
    // Before ✋ Nhận đơn the window is already on the card: planning starts on the board.
    const fresh=page(f.board_new,f.board_new.careers.delivery.tasks[0].id).html;
    assert.match(fresh,/class="dl-appt/,`${layout}: the window shows before accepting`);
  }
  // ⏰ Reminder: on → a toast once, a few game minutes before the window.
  attrs.delete('data-clean');
  const {x,t}=page(f.door_early);
  await delivery.default.actions.remind({task:t.id},null,x);
  assert.match(toasts.at(-1),/Sẽ nhắc trước giờ hẹn/);
  const [start]=f.window;
  const near=structuredClone(f.door_early);near.careers.delivery.data.clock=start-5;
  const ctx=careerContext(env(near));
  const root={dataset:{},style:{setProperty(){}},querySelector:()=>null,closest:()=>null};
  delivery.default.tick(root,ctx);
  assert.match(toasts.at(-1),/⏰ Sắp tới giờ hẹn/);
  const n=toasts.length;
  delivery.default.tick(root,ctx);
  assert.equal(toasts.length,n,'one reminder per window');
}

/* ---------- English ---------- */
globalThis.Node={ELEMENT_NODE:1,TEXT_NODE:3};globalThis.NodeFilter={SHOW_TEXT:4,SHOW_ELEMENT:1};
globalThis.document.body={nodeType:1,closest(){return false;}};globalThis.document.createTreeWalker=()=>({nextNode(){return null;}});globalThis.document.title='';
globalThis.MutationObserver=class {observe(){}};
globalThis.__mnlBoot={i18n:Promise.resolve(JSON.parse(readFileSync(new URL('../public/i18n/en.json',import.meta.url),'utf8')))};
const {setLanguage,t}=await import('../public/js/v4/i18n.js');await setLanguage('en');
assert.equal(t('mở sau 20 phút'),'opens in 20 min');
assert.equal(t('sắp trễ'),'almost late');
assert.equal(t('Hẹn giao 18:00–18:30, sắp trễ, còn 5 phút'),'Delivery window 18:00–18:30, almost late, 5 min left');
assert.equal(t('⏳ Chờ tới giờ hẹn · 12 phút'),'⏳ Wait for the window · 12 min');
assert.equal(t('📞 Gọi hỏi giao sớm · 2 phút'),'📞 Call to ask to come early · 2 min');
assert.match(t('📅 Bấm chuông không ai mở: Bé Vy hẹn nhận 17:40–18:10, giờ mới 17:23 (còn 17 phút).'),/^📅 Nobody answers the bell: .+ booked 17:40–18:10, it is only 17:23 \(17 min to go\)\.$/);
console.log('delivery 📅 scheduled orders: window chip, countdown colours, wait/call/remind, route draft, reminders and English passed');
