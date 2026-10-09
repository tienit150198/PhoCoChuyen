// F#295/#296 (quầy của mình) and F#294: the pure plans behind 🔁 Nhập lại như lần trước, 👛 thiếu thì lấy từ ví and
// 📋 Quản lý chung (public/js/v4/quay-manage.js); ✏️ Sửa góp ý (feedback.js) and 🏆 Xếp hạng nghề (leaderboard.js).
// With `--plan` it reads {kind, ...} JSON on stdin and prints the plan (tests/test_quay_manage.py feeds it real states).
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {againPlan,shortOf,groupStalls,stallLine,againAll,tillAll,openAll,STOCK_MAX} from '../public/js/v4/quay-manage.js';
import {quayHave} from '../public/js/v4/select-all.js';

if(process.argv.includes('--plan')){
  let raw='';for await(const chunk of process.stdin)raw+=chunk;
  const x=JSON.parse(raw),stalls=x.journey.quay.stalls,have=quayHave(x.journey);
  const out=x.kind==='again'?againPlan(stalls.find(st=>st.id===x.stall))
    :x.kind==='againAll'?againAll(stalls.filter(st=>!x.trade||st.trade===x.trade),have)
    :x.kind==='till'?tillAll(stalls):x.kind==='open'?openAll(stalls)
    :x.kind==='groups'?groupStalls(stalls).map(g=>[g.trade,g.stalls.map(st=>st.id)])
    :stalls.map(st=>stallLine(st));
  process.stdout.write(JSON.stringify(out));
  process.exit(0);
}

const row=(id,cost,qty=0)=>({id,cost,qty});
const stall=(id,trade,{again=[],stock=[row('a',3),row('b',5)],total=0,till=0,fund=0,status='running',paused=false,hours=null,staff=1}={})=>
  ({id,trade,name:id,place:'xe',till,fund,staff:Array.from({length:staff},(_,i)=>({id:`s${i}`})),
    business:{again,stock,stock_total:total,status,paused,income:hours==null?null:{stock_hours:hours}}});

// 🔁 the last order at today's cost; nothing when there was none.
assert.equal(againPlan(stall('q1','tea')),null);
assert.equal(againPlan(null),null);
let p=againPlan(stall('q1','tea',{again:[{id:'a',qty:4},{id:'b',qty:2}]}));
assert.deepEqual(p,{items:{a:4,b:2},count:6,total:4*3+2*5,trimmed:false});
// a dish no longer in the stock room is left out (and said so); the room left caps the order
p=againPlan(stall('q1','tea',{again:[{id:'gone',qty:4},{id:'b',qty:2}]}));
assert.deepEqual(p,{items:{b:2},count:2,total:10,trimmed:true});
p=againPlan(stall('q1','tea',{again:[{id:'a',qty:10},{id:'b',qty:10}],total:STOCK_MAX-12}));
assert.deepEqual(p,{items:{a:10,b:2},count:12,total:40,trimmed:true});
assert.equal(againPlan(stall('q1','tea',{again:[{id:'a',qty:10}],total:STOCK_MAX})),null,'A full stock room: nothing to send');

// 👛 the shortfall the wallet pays: till and fund first
assert.equal(shortOf({till:5,fund:10},40),25);
assert.equal(shortOf({till:50,fund:10},40),0);
assert.equal(shortOf(null,7),7);

// 📋 groups: by trade, the biggest group first, list order kept inside a group
const many=[stall('q1','tea'),stall('q2','flowers'),stall('q3','tea'),stall('q4','tea'),stall('q5','flowers')];
assert.deepEqual(groupStalls(many).map(g=>[g.trade,g.stalls.map(s=>s.id)]),[['tea',['q1','q3','q4']],['flowers',['q2','q5']]]);
assert.deepEqual(groupStalls([]),[]);

// one line per counter: low stock when out, empty or under two hours of sales
assert.equal(stallLine(stall('q1','tea',{total:50,hours:5})).low,false);
assert.equal(stallLine(stall('q1','tea',{total:50,hours:1.5})).low,true);
assert.equal(stallLine(stall('q1','tea',{total:0})).low,true);
assert.equal(stallLine(stall('q1','tea',{total:9,status:'out_of_stock'})).low,true);
assert.deepEqual((({cash,staff,status})=>({cash,staff,status}))(stallLine(stall('q1','tea',{till:7,fund:3,staff:2,total:9}))),{cash:10,staff:2,status:'running'});

// bulk: each counter's shortfall comes out of the wallet in turn; a counter the money no longer covers waits
const a=stall('q1','tea',{again:[{id:'a',qty:10}],till:30});           // 30 xu: enough
const b=stall('q2','tea',{again:[{id:'b',qty:10}],till:20});           // 50 xu: 30 short
const c=stall('q3','tea',{again:[{id:'b',qty:20}]});                   // 100 xu: all short
const d=stall('q4','tea');                                              // never restocked: not part of it
let all=againAll([a,b,c,d],60);
assert.deepEqual(all.steps,[{stall:'q1',items:{a:10}},{stall:'q2',items:{b:10},wallet:true}]);
assert.deepEqual([all.total,all.short,all.skip.map(s=>s.id)],[80,30,['q3']]);
all=againAll([a,b,c],1000);
assert.deepEqual([all.steps.length,all.total,all.short,all.skip.length],[3,180,130,0]);
assert.equal(all.steps[2].wallet,true);

// 💰 / ▶️
assert.deepEqual(tillAll([stall('q1','t',{till:12}),stall('q2','t'),stall('q3','t',{till:3})]),{steps:[{stall:'q1'},{stall:'q3'}],total:15});
assert.deepEqual(openAll([stall('q1','t',{paused:true}),stall('q2','t'),{...stall('q3','t',{paused:true}),due:5}]).steps,[{stall:'q1',on:false}]);

// No rates, odds or caps for players: the overview and the plans never print a percentage.
const quay=readFileSync(new URL('../public/js/v4/quay.js',import.meta.url),'utf8');
const part=quay.slice(quay.indexOf('/* 📋 Quản lý chung'),quay.indexOf('const ownerEvents='));
assert.ok(part.includes('manageView')&&part.includes('bulkRow'));
assert.doesNotMatch(part,/\d\s*%/);
for(const k of ['restockAsk','againRow','growPart','jr_quay_upgrade','wallet:true','📋 Quản lý chung'])assert.ok(quay.includes(k),k);

/* ---- ✏️ Sửa góp ý (feedback.js) ---- */
globalThis.document={documentElement:{dataset:{layout:'phone'}},getElementById:()=>null,querySelector:()=>null,createElement:()=>({getContext:()=>null}),addEventListener:()=>{}};
globalThis.innerWidth=390;globalThis.innerHeight=844;
const {feedbackPageView,feedbackAction,feedbackSubmit}=await import('../public/js/v4/feedback.js');
const posts=[];
const env={ui:{view:'gopy'},toast:(...a)=>env.toasts.push(a),toasts:[],renderSheet:()=>{},openSheet:()=>{},
  api:{admin:false,state:{journey:{life_day:3}},content:{catalogue:[]},
    json:async()=>({items:[{id:7,kind:'bug',text:'Chữ <cũ>',status:'seen',reply:null,created_at:0},{id:6,kind:'idea',text:'Đã có lời đáp',status:'done',reply:'Cảm ơn!',created_at:0,replied_at:0}],admin:false}),
    post:async(url,body)=>{posts.push([url,body]);if(body.text==='409 nhé'){const e=new Error('Góp ý này đã có lời đáp nên không sửa được nữa.');e.status=409;throw e;}
      return {ok:true,message:'Đã lưu góp ý.',item:{id:body.id,kind:'bug',text:body.text,status:'new',reply:null,created_at:0}};}}};
feedbackPageView(env);await new Promise(r=>setTimeout(r,0));
let html=feedbackPageView(env);
assert.equal((html.match(/data-action="fbEdit"/g)||[]).length,1,'Only the note without a reply can be edited');
assert.match(html,/data-action="fbEdit" data-id="7"/);
assert.equal(await feedbackAction('fbEdit',{id:'6'},null,env),true);
assert.equal(env.ui.fb.edit,undefined,'A replied note never opens the form');
assert.equal(await feedbackAction('fbEdit',{id:'7'},null,env),true);
html=feedbackPageView(env);
assert.match(html,/<form class="fb-edit-form" data-fb-edit="7"/);
assert.match(html,/Chữ &lt;cũ&gt;<\/textarea>/,'The draft starts from the note, escaped');
const form=text=>({dataset:{fbEdit:'7'},querySelector:()=>({value:text})});
assert.equal(await feedbackSubmit(form('ok'),env),true);
assert.equal(posts.length,0,'Too short: not sent');
assert.equal(await feedbackSubmit(form('Chữ mới, rõ hơn'),env),true);
assert.deepEqual(posts.at(-1),['/api/feedback/edit',{id:7,text:'Chữ mới, rõ hơn'}]);
assert.equal(env.ui.fb.edit,null);
assert.equal(env.ui.fb.mine.items[0].text,'Chữ mới, rõ hơn');
html=feedbackPageView(env);
assert.doesNotMatch(html,/fb-edit-form/);
assert.equal(await feedbackAction('fbEdit',{id:'7'},null,env),true);
assert.equal(await feedbackSubmit(form('409 nhé'),env),true);
assert.equal(env.ui.fb.edit,null,'A reply came meanwhile: the form closes and the list reloads');
assert.equal(env.ui.fb.mine,null);
assert.match(String(env.toasts.at(-1)[0]),/không sửa được/);
assert.equal(await feedbackAction('fbEditCancel',{},null,env),true);

/* ---- 🏆 Xếp hạng nghề (leaderboard.js rankWork) and the Công việc entry (app.js) ---- */
globalThis.requestAnimationFrame=()=>0;globalThis.location??={search:'',href:'http://x/',hostname:'x',protocol:'http:'};
globalThis.document.head={append:l=>setTimeout(()=>l.onload?.(),0)};
globalThis.document.createElement=()=>({dataset:{},getContext:()=>null});
const {leaderboardAction}=await import('../public/js/v4/leaderboard.js');
let opened=null;
const lenv={ui:{},openSheet:v=>{opened=v;},renderSheet:()=>{},api:{state:{current:'flight_attendant',careers:{flight_attendant:{xp:5},milk_tea:{}}}}};
assert.equal(await leaderboardAction('rankWork',{},null,lenv),true);
assert.equal(opened,'rank');
assert.deepEqual([lenv.ui.lb.kind,lenv.ui.lb.board],['exp','flight_attendant'],'Opens on the board of the workplace on screen');
lenv.api.state.current='nowhere';
await leaderboardAction('rankWork',{},null,lenv);
assert.equal(lenv.ui.lb.board,'all','No such workplace: the overall board');
const app=readFileSync(new URL('../public/js/app.js',import.meta.url),'utf8');
assert.match(app,/const RAIL_MAIN=\[[^\]]*'rankWork'/,'In the Công việc pages (rail / top of Thêm)');
assert.match(app,/result\.push\(\['rankWork','award','Xếp hạng nghề'\]\)/,'Added after a career reshapes its pages (the air crew too)');
assert.match(app,/action==='rankWork'/,'Routed to leaderboard.js');

console.log('quay-manage plans, ✏️ Sửa góp ý and 🏆 Xếp hạng nghề passed.');
