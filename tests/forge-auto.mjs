// ⚡ Cường hóa nhanh of the pets' ghép shelves (v4/pets.js autoCard, owner 23/10: "cường hóa nhanh sẽ tự ghép mà cường hóa
// chứ sao lại cường hóa từng lần", "nó giống ghép tự động của áo quần ấy"): drawn in node from a real save and the real
// catalogue (python), each shelf (🧬 lab, 👗 ward, 🧰 gear) shows one card (which ones, up to which rank, the most to
// spend, one button); a tap asks once (what a miss may lose) and sends ONE command, whose summary is drawn above the card;
// a picker drops the budget back to the estimate; the sheet redraws in place (env.renderSheet, no jump); no odds.
import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';

const dump=execFileSync(process.env.PYTHON||'python',['-c',`
import json
from tests.test_forge_auto import pets
from tests.test_bank import act
from game.engine import public_state
from game import pets as pt
s, ids = pets(0, 0, 0, 0, 1, 1, 1, 4, 4, 4)
s, _ = act(s, 'jr_pet_gear_buy', slot='giay', model=0, rank=0, qty=3, confirm=True)
s, _ = act(s, 'jr_pet_wbuy', id='no_hong', qty=3, confirm=True)
print(json.dumps(dict(state=public_state(s), pets=pt.catalogue()), ensure_ascii=False))
`],{encoding:'utf8',env:{...process.env,PYTHONUTF8:'1'},maxBuffer:64*1024*1024});
const {state,pets}=JSON.parse(dump);

// a page with a sheet: the clicks and the pickers reach v4/pets.js through its document listeners (bindSheet)
const on={};
globalThis.document={addEventListener:(type,fn)=>{(on[type]??=[]).push(fn);},querySelector:()=>({}),documentElement:null};
const fire=(type,data,extra={})=>{const el={dataset:data,disabled:false,...extra};
  for(const fn of on[type]||[])fn({target:{closest:()=>el,...el},preventDefault(){}});};
const tap=data=>fire('click',data);
const {petEmbedHTML,petForgeCounts}=await import('../public/js/v4/pets.js');

const asked=[],sent=[];let draws=0,answer=null;
const api={state,content:{journey:{pets}},command:async(action,payload)=>{sent.push([action,payload]);return answer;}};
const env={api,renderSheet:keep=>{draws++;assert.notEqual(keep,false,'a redraw keeps the scroll (owner 23/10: no jump)');},
  confirmAction:async(title,msg,label,o)=>{asked.push({title,msg,label,o});return true;},toast(){},act(){}};
const card=html=>html.match(/<section class="pt-card pt-auto pt-quick"[\s\S]*?<\/section>/)?.[0]||'';
const settle=()=>new Promise(r=>setTimeout(r,0));

test('🧬 lab: one card, one question, ONE jr_pet_fuse_auto, its summary above the card',async()=>{
  let html=petEmbedHTML(env,'lab'),c=card(html);
  assert.match(c,/⚡ Cường hóa nhanh/);
  assert.match(c,/<option value="4" selected>/,'🎯 up to S by default (owner 23/10)');assert.match(c,/<b>2<\/b><small>bộ ba bé/,'not the S three');
  fire('change',{ptSel:'latop'},{value:'7'});html=petEmbedHTML(env,'lab');c=card(html);
  assert.match(c,/data-pt-sel="lascope"/);assert.match(c,/<option value="7" selected>🌟 Huyền thoại<\/option>/);
  assert.match(c,/<b>3<\/b><small>bộ ba bé ghép được ngay/,'D, C and S each have three');
  const est=pets.tiers.ranks[0].fee+pets.tiers.ranks[1].fee+pets.tiers.ranks[4].fee;
  assert.match(c,new RegExp(`⚡ Cường hóa nhanh · tiêu tối đa ${est.toLocaleString('vi-VN').replace('.','\\.')} xu`));
  assert.match(c,/⚠️ Từ hạng S trở lên: trượt thì mất 2 bé nguyên liệu/);
  assert.doesNotMatch(c,/tỉ lệ|tỷ lệ|\d%/,'never the odds (owner 19/10)');
  assert.ok(html.indexOf('pt-auto')<html.indexOf('Tự chọn ba bé'),'⚡ first, Tự chọn below');
  answer={message:'⚡ Cường hóa nhanh 3 lượt: 2 thành công, 1 trượt.',ok:true,
    auto:{n:3,ok:2,spent:2500,stop:'done',used:4,made:[{id:'p1',n:'Bé 1',b:'meo_mun',r:1,legend:false}],myth:null,left:0}};
  tap({pt:'auto',kind:'lab'});await settle();await settle();
  assert.equal(asked.length,1);assert.equal(asked[0].title,'⚡ Cường hóa nhanh?');
  assert.match(asked[0].msg,/tới 🌟 huyền thoại/);assert.match(asked[0].msg,/⚠️ từ hạng S trở lên mất hai bé nguyên liệu/);
  assert.match(asked[0].msg,/Bé đang dắt không bao giờ là nguyên liệu/);
  assert.deepEqual(sent,[['jr_pet_fuse_auto',{scope:'all',top:7,budget:est,confirm:true}]]);
  html=petEmbedHTML(env,'lab');
  assert.match(html,/⚡ Kết quả cường hóa nhanh/);assert.match(html,/<b>3<\/b><small>lượt/);assert.match(html,/<b>2<\/b><small>thành công/);
  assert.match(html,/<b>1<\/b><small>trượt/);assert.match(html,/<b[^>]*>2\.500<\/b><small>xu đã tiêu/);assert.match(html,/Bé lên hạng/);
  assert.ok(html.indexOf('Kết quả cường hóa nhanh')<html.indexOf('pt-auto pt-quick'),'the summary above the card');
  assert.ok(draws>0);
  // ghép tới hạng B: nothing at S, nothing lost; the budget back to the estimate
  fire('change',{ptSel:'latop'},{value:'2'});
  c=card(petEmbedHTML(env,'lab'));
  assert.match(c,/<b>2<\/b><small>bộ ba bé ghép được ngay/);assert.doesNotMatch(c,/⚠️/);
  tap({pt:'abud',kind:'lab',n:'9000'});await settle();
  assert.match(card(petEmbedHTML(env,'lab')),/tiêu tối đa 9\.000 xu/);
  tap({pt:'ares',kind:'lab'});
  assert.doesNotMatch(petEmbedHTML(env,'lab'),/Kết quả cường hóa nhanh/);
  fire('change',{ptSel:'latop'},{value:'7'});
});

test('👗 ward: its ⚡ is Ghép tự động (jr_pet_wfuse_auto), in place of the one-fusion button',async()=>{
  asked.length=0;sent.length=0;
  const html=petEmbedHTML(env,'ward'),c=card(html);
  assert.match(c,/data-pt-sel="wascope"/);assert.match(c,/<b>1<\/b><small>bộ ba ghép được ngay/);
  assert.doesNotMatch(html,/pt-autobtn|data-sub="wauto"/);
  answer={message:'🤖',ok:true,auto:{n:1,ok:1,lux:0,spent:200,stop:'done',used:3,made:[{id:'o9',k:'no_hong',r:1}],left:0}};
  tap({pt:'auto',kind:'ward'});await settle();await settle();
  assert.equal(asked.length,1);assert.match(asked[0].msg,/Đồ đang mặc được giữ nguyên/);
  assert.deepEqual(sent,[['jr_pet_wfuse_auto',{scope:'all',max_rank:6,budget:pets.wardrobe.fee[0],confirm:true}]]);
  assert.match(petEmbedHTML(env,'ward'),/Món mới/);
});

test('🧰 gear: +max then a rank up, ONE jr_pet_gear_auto',async()=>{
  asked.length=0;sent.length=0;
  const c=card(petEmbedHTML(env,'gearup')),L=pets.tiers.gear.lv_max;
  assert.match(c,/data-pt-sel="gascope"/);assert.match(c,/<b>1<\/b><small>món lên hạng được/);
  let est=pets.tiers.gear.fuse_fee[0];for(let lv=0;lv<L;lv++)est+=pets.tiers.gear.up_fee[0]*(lv+1);
  assert.match(c,new RegExp(`tiêu tối đa ${est.toLocaleString('vi-VN').replace('.','\\.')} xu`));
  answer={message:'⚡',ok:true,auto:{n:11,ok:11,spent:est,stop:'done',used:2,fuses:1,made:[{id:'g1',s:'giay',r:1,rank:'C',lv:0,emoji:'👟',name:'Giày chạy bộ'}],left:0}};
  tap({pt:'auto',kind:'gear'});await settle();await settle();
  assert.match(asked[0].msg,/Món đang gắn không bao giờ là nguyên liệu/);
  assert.deepEqual(sent,[['jr_pet_gear_auto',{scope:'all',top:6,budget:est,confirm:true}]]);
  const html=petEmbedHTML(env,'gearup');
  assert.match(html,/1 lần ghép lên hạng · dùng 2 món/);assert.match(html,/Món mạnh lên/);
});

test('⚒️ the overview: ⚡ where each card has something to do',()=>{
  const n=petForgeCounts(env);
  assert.equal(n.lab.quick,true);assert.equal(n.ward.quick,true);assert.equal(n.gear.quick,true);
  const none={...api,state:{...state,journey:{...state.journey,pets:{...state.journey.pets,petx:{...state.journey.pets.petx,gear:[]},petw:{...state.journey.pets.petw,it:[]}}}}};
  const m=petForgeCounts({...env,api:none});
  assert.equal(m.ward.quick,false);assert.equal(m.gear.quick,false);
  petForgeCounts(env);
});

test('☑️ Không hỏi lại (localStorage mnl.noAsk): ⚡ and the ghép buttons act at once, no question; unticked asks again',async()=>{
  const store=new Map();
  globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
  const {noAsk,setNoAsk}=await import('../public/js/v4/no-ask.js');
  assert.equal(noAsk(),false,'the default asks');
  setNoAsk(true);assert.equal(store.get('mnl.noAsk'),'1');assert.equal(noAsk(),true);
  asked.length=0;sent.length=0;answer={message:'⚡',ok:true,auto:{n:1,ok:1,spent:1,stop:'done',used:2,made:[],myth:null,left:0}};
  petEmbedHTML(env,'lab');
  tap({pt:'auto',kind:'lab'});await settle();await settle();
  assert.equal(asked.length,0,'no confirm dialog');
  assert.equal(sent.length,1);assert.equal(sent[0][0],'jr_pet_fuse_auto');assert.equal(sent[0][1].confirm,true);
  setNoAsk(false);assert.equal(store.has('mnl.noAsk'),false);
  sent.length=0;petEmbedHTML(env,'lab');tap({pt:'auto',kind:'lab'});await settle();await settle();
  assert.equal(asked.length,1,'unticked: the question again');
  globalThis.localStorage={getItem(){throw new Error('blocked');},setItem(){throw new Error('blocked');},removeItem(){throw new Error('blocked');}};
  assert.equal(noAsk(),false,'no storage: it asks');setNoAsk(true);assert.equal(noAsk(),false);
  delete globalThis.localStorage;
});

/* ---- ⚒️ Cường hóa v2 (v4/forge.js, owner 23/10 "gọn và dễ dùng như các game khác"): one grid per kind, the upgrade
 * panel (Cường hóa / Cường hóa tối đa), ⚡ Ghép tất cả, 🔒 Khóa, ⏩ Bỏ qua hiệu ứng. The plans drawn are the server's own
 * picks (game/wings.py sets, game/pet_tiers.py fuse_sets / gear_step, game/pet_wardrobe.py triples), locks and pin
 * included: compared here with python's on one save (wings D/C/S, pets D/C, gear, clothes, four pieces 🔒). ---- */
const v2=JSON.parse(execFileSync(process.env.PYTHON||'python',['-c',`
import json
from tests.test_forge_auto import wings, act, X, Wg
from tests.test_pet_tiers import get as get_pet
from game import wings as W, pet_tiers as px, pet_wardrobe as pw, forge_locks as fl, pets as pt
from game.engine import public_state
s = wings(10**9, ('buom', 0, 4), ('rong', 0, 3), ('buom', 1, 3), ('rong', 4, 1), on=0)
for i, r in enumerate((0, 0, 0, 0, 1, 1, 1)):
    s, _ = get_pet(s, f'Bé {i + 1}', rank=r)
s, _ = act(s, 'jr_pet_gear_buy', slot='giay', model=0, rank=0, qty=4, confirm=True)
s, _ = act(s, 'jr_pet_wbuy', id='no_hong', qty=4, confirm=True)
s, _ = act(s, 'jr_pet_lock', ids=['w5', 'p2', 'g2', 'o2'], on=True)
locks = fl.ids(s)
ids = lambda xs: [[r, [x['id'] for x in t], k] for r, t, k in xs]
step = lambda st: [st[0], st[1]['id']] if st else None
plans = dict(wing=ids(W.sets(Wg(s), 'all', W.TOP, locks)), wing_pin=ids(W.sets(Wg(s), 'all', W.TOP, locks, 'w9')),
             wing_top=ids(W.sets(Wg(s), 'all', W.TOP, locks, 'w11')),
             pet=[list(x) for x in px.fuse_sets(s, 'all', px.TOP + 1, locks)], pet_pin=[list(x) for x in px.fuse_sets(s, 'all', px.TOP + 1, locks, 'p5')],
             ward=[[k, r, [i['id'] for i in its]] for k, r, its in pw.triples(pw.get(s), 'all', pw.TOP, True, locks)],
             gear=step(px.gear_step(s, X(s), 'all', px.TOP, locks)), gear_pin=step(px.gear_step(s, X(s), 'all', px.TOP, locks, 'g4')))
print(json.dumps(dict(state=public_state(s), content=dict(journey=dict(wardrobe=dict(wings=W.catalogue()), pets=pt.catalogue())), plans=plans), ensure_ascii=False))
`],{encoding:'utf8',env:{...process.env,PYTHONUTF8:'1',PYTHONPATH:'.'},maxBuffer:64*1024*1024}));

const FG=await import('../public/js/v4/forge.js');
const fg={asked:[],sent:[],draws:[],answers:[]};
const fgApi={state:v2.state,content:v2.content,command:async()=>null};
const fgEnv={api:fgApi,ui:{},
  cmd:async(action,payload,o)=>{fg.sent.push([action,payload,o]);const a=fg.answers.shift();return typeof a==='function'?a(action,payload):a??null;},
  renderSheet:keep=>{fg.draws.push(keep);},confirmAction:async(title,msg,label,o)=>{fg.asked.push({title,msg,label,o});return true;},toast(){},act(){}};
const fgReset=()=>{fg.asked.length=0;fg.sent.length=0;fg.draws.length=0;fg.answers.length=0;};
const go=(action,data={})=>FG.forgeAction(action,data,null,fgEnv);
const view=()=>FG.forgeView(fgEnv);
const store=new Map();
const fakeStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};

test('⚒️ v2: the ⚡ plans are the server\'s picks, 🔒 locks and the pin included',()=>{
  const P=v2.plans,ids=xs=>xs.map(x=>[x.r,x.set.map(y=>y.id),x.t]);
  assert.deepEqual(ids(FG.wingSets(fgApi)),P.wing);
  assert.deepEqual(ids(FG.wingSets(fgApi,'all',7,'w9')),P.wing_pin,'pin: the pinned wing is the main one');
  assert.deepEqual(ids(FG.wingSets(fgApi,'all',7,'w11')),P.wing_top,'pin on S: the tiers below build its ingredients');
  assert.deepEqual(ids(FG.petSets(fgApi)),P.pet);
  assert.deepEqual(ids(FG.petSets(fgApi,'all',7,'p5')),P.pet_pin);
  assert.deepEqual(FG.wardSets(fgApi).map(x=>[x.k,x.r]),P.ward.map(x=>[x[0],x[1]]));
  assert.equal(FG.wardSets(fgApi)[0].t,Math.floor(P.ward[0][2].length/3));
  const g=FG.gearPlan(fgApi),gp=FG.gearPlan(fgApi,'all',6,'g4');
  assert.equal(g.sets[0].g.id,P.gear[1],'the gear that goes up first');assert.equal(gp.sets[0].g.id,P.gear_pin[1]);
  for(const [,set] of [...P.wing,...P.pet])for(const id of set.slice(1))assert.ok(!['w5','p2'].includes(id),'a locked piece is never an ingredient');
});

test('⚒️ v2: kind tabs, the grid with rank colours, ⚡ dots, 🔒, the three short ticks, ⚡ Ghép tất cả',()=>{
  fgReset();
  const html=view();
  assert.deepEqual(FG.forgeTabs(fgApi),['wing','plab','pward','pgear']);
  assert.match(html,/role="tablist"/);assert.equal((html.match(/role="tab"/g)||[]).length,4);
  assert.match(html,/id="fv-t-wing" class="fv-kind on" aria-selected="true"/);
  assert.equal((html.match(/class="fv-tile/g)||[]).length,11,'every wing a tile');
  assert.match(html,/style="--tc:#e8820f" data-action="jrFgSel" data-id="w11"/,'S: orange');
  assert.match(html,/data-id="w5"[^>]*aria-label="[^"]*đã khóa"/);assert.match(html,/class="fv-lk"/);
  assert.match(html,/class="fv-dot"/,'⚡ on a piece that can go up now');
  assert.ok(html.indexOf('data-id="w11"')<html.indexOf('data-id="w8"')&&html.indexOf('data-id="w8"')<html.indexOf('data-id="w1"'),'highest rank first');
  for(const l of ['Không hỏi lại','Ẩn tên','Bỏ qua hiệu ứng'])assert.match(html,new RegExp(`<span>${l}</span>`));
  assert.match(html,/data-action="jrFgAll"[^>]*>⚡ Ghép tất cả</);
  assert.doesNotMatch(html,/tỉ lệ|tỷ lệ/,'no odds');
  assert.doesNotMatch(html,/id="fv-panel"/,'no panel until a tap');
});

test('⚒️ v2: tap → the panel; Cường hóa sends the one-shot command with the slots; a swap; the result card',async()=>{
  fgReset();
  await go('jrFgSel',{id:'w1'});assert.deepEqual(fg.draws,[undefined],'a redraw in place');
  let html=view();
  assert.match(html,/id="fv-panel"/);assert.match(html,/aria-label="hạng D lên hạng C"/);
  assert.match(html,/<span class="fv-cnt">3\/3<\/span>/);assert.match(html,/Phí <b title="500 xu">500 xu<\/b>/);
  assert.match(html,/\+2%<\/b> → <b class="up">\+4%/,'what changes: % thu nhập');
  assert.doesNotMatch(html,/⚠️/,'D: nothing is lost');
  assert.match(html,/data-action="jrFgSlot" data-i="0"/);
  await go('jrFgSlot',{i:'0'});html=view();
  assert.match(html,/class="fv-cands"/);assert.doesNotMatch(html,/data-action="jrFgPick" data-i="0" data-id="w5"/,'🔒 not offered');
  await go('jrFgPick',{i:'0',id:'w7'});
  fg.answers.push({message:'🎉',fuse:{ok:true,main:'w1',tier:1}});
  await go('jrFgOne',{id:'w1'});
  assert.equal(fg.asked.length,1);assert.equal(fg.asked[0].title,'⚒️ Cường hóa D → C?');assert.equal(fg.asked[0].msg,'Phí 500 xu.');
  assert.equal(fg.sent[0][0],'jr_pet_wing_fuse');assert.equal(fg.sent[0][1].main,'w1');
  assert.equal(fg.sent[0][1].wings[0],'w1');assert.equal(fg.sent[0][1].wings[1],'w7','the swapped slot');assert.equal(fg.sent[0][1].confirm,true);
  assert.deepEqual(fg.sent[0][2],{quiet:true});
  html=view();assert.match(html,/🎉 Thành công/);assert.match(html,/<b>1<\/b><small>lượt/);assert.match(html,/xu đã tiêu/);
  await go('jrFgRes');assert.doesNotMatch(view(),/fv-res/);
});

test('⚒️ v2: Cường hóa tối đa = the kind\'s ⚡ pinned on the piece, the budget chips, from S the loss line',async()=>{
  fgReset();
  await go('jrFgSel',{id:'w11'});let html=view();
  assert.match(html,/⚠️ Trượt mất 2 đôi phụ/,'S: the short loss line');
  await go('jrFgSel',{id:'w9'});html=view();
  assert.match(html,/⚡ Cường hóa tối đa/);assert.match(html,/data-action="jrFgBud"[^>]*>×2</);
  const est=FG.planOf(fgApi,'wing','all','w9').est;
  fg.answers.push({message:'⚡',auto:{n:3,ok:2,spent:4500,stop:'done',used:4,made:[{id:'w9',k:'buom',r:2,z:1}],left:0}});
  await go('jrFgMax',{id:'w9'});
  const [a,p]=fg.sent[0];assert.equal(a,'jr_pet_wing_fuse_auto');
  assert.equal(p.pin,'w9');assert.equal(p.top,4,'⚡ goes up to S by default');assert.equal(p.scope,'all');assert.equal(p.budget,est);assert.equal(p.confirm,true);assert.ok(p.rid);
  assert.match(fg.asked[0].msg,/🔒 Món khóa không bị dùng/);
  html=view();assert.match(html,/<b>3<\/b><small>lượt/);assert.match(html,/<b>2<\/b><small>thành công/);assert.match(html,/<b title="4\.500 xu">4\.500<\/b>/);
  await go('jrFgRes');
});

test('⚒️ v2: each kind sends its own commands (pets, clothes, gear +1)',async()=>{
  fgReset();
  await go('jrFgTab',{tab:'plab'});assert.notEqual(fg.draws.at(-1),false,'a new tab keeps the scroll too');
  await go('jrFgSel',{id:'p6'});let html=view();assert.match(html,/id="fv-panel"/);
  await go('jrFgOne',{id:'p6'});assert.equal(fg.sent[0][0],'jr_pet_fuse');assert.equal(fg.sent[0][1].main,'p6');assert.ok(!fg.sent[0][1].pets.includes('p2'));
  await go('jrFgMax',{id:'p6'});assert.equal(fg.sent[1][0],'jr_pet_fuse_auto');assert.equal(fg.sent[1][1].pin,'p6');
  await go('jrFgTab',{tab:'pward'});html=view();
  await go('jrFgSel',{id:'no_hong|0'});html=view();
  assert.match(html,/<span class="fv-cnt">3\/3<\/span>/,'four pieces, one 🔒: three to use');
  await go('jrFgOne',{id:'no_hong|0'});assert.deepEqual(fg.sent[2].slice(0,2),['jr_pet_wfuse',{k:'no_hong',r:0,confirm:true}]);
  await go('jrFgMax',{id:'no_hong|0'});assert.equal(fg.sent[3][0],'jr_pet_wfuse_auto');assert.equal(fg.sent[3][1].scope,'no_hong');
  await go('jrFgTab',{tab:'pgear'});await go('jrFgSel',{id:'g1'});html=view();
  assert.match(html,/<b>\+0<\/b> <span aria-hidden="true">→<\/span> <b class="up">\+1<\/b>/,'+0 → +1');
  await go('jrFgOne',{id:'g1'});assert.deepEqual(fg.sent[4].slice(0,2),['jr_pet_gear_up',{gear:'g1',confirm:true}]);
  await go('jrFgMax',{id:'g1'});assert.equal(fg.sent[5][0],'jr_pet_gear_auto');assert.equal(fg.sent[5][1].pin,'g1');assert.equal(fg.sent[5][1].scope,'giay');
  await go('jrFgTab',{tab:'wing'});
});

test('⚒️ v2: 🔒 Khóa sends jr_pet_lock (a clothes stack: all its pieces)',async()=>{
  fgReset();
  await go('jrFgLock',{id:'w5'});assert.deepEqual(fg.sent[0].slice(0,2),['jr_pet_lock',{ids:['w5'],on:false}],'locked: unlock');
  await go('jrFgLock',{id:'w1'});assert.deepEqual(fg.sent[1].slice(0,2),['jr_pet_lock',{ids:['w1'],on:true}]);
  await go('jrFgTab',{tab:'pward'});await go('jrFgLock',{id:'no_hong|0'});
  assert.deepEqual(fg.sent[2][1],{ids:['o1','o2','o3','o4'],on:true},'some locked: lock them all');
  await go('jrFgTab',{tab:'wing'});
});

test('⚒️ v2: ⚡ Ghép tất cả runs each kind\'s ⚡ in turn, one question (none with Không hỏi lại), one result card',async()=>{
  fgReset();globalThis.localStorage=fakeStorage;store.clear();
  const auto=(n,ok,spent,made=[])=>({message:'⚡',auto:{n,ok,spent,stop:'done',used:2,made,left:0}});
  fg.answers.push(auto(2,1,1000,[{id:'w1',k:'buom',r:1,z:1}]),auto(2,2,2500,[{id:'p1',n:'Bé 1',b:'meo_mun',r:1,legend:false}]),auto(1,1,200,[{id:'o9',k:'no_hong',r:1}]),auto(11,10,4000000,[]));
  await go('jrFgAll');
  assert.equal(fg.asked.length,1);assert.equal(fg.asked[0].title,'⚡ Ghép tất cả?');assert.match(fg.asked[0].msg,/^Ghép 🪽 🧬 👗 🧰\. Tiêu tối đa [\d.]+ xu\./);
  assert.deepEqual(fg.sent.map(x=>x[0]),['jr_pet_wing_fuse_auto','jr_pet_fuse_auto','jr_pet_wfuse_auto','jr_pet_gear_auto']);
  assert.ok(fg.sent.every(x=>x[1].confirm===true&&!x[1].pin&&x[2]?.quiet));
  const html=view();
  assert.match(html,/<b>16<\/b><small>lượt/);assert.match(html,/<b>14<\/b><small>thành công/);assert.match(html,/<b>2<\/b><small>trượt/);
  assert.match(html,/<b title="4\.003\.700 xu">4tr<\/b><small>xu đã tiêu/,'big xu short (shortNum)');
  assert.equal((html.match(/<ul class="fv-made"[\s\S]*?<\/ul>/)?.[0].match(/<li style=/g)||[]).length,3,'what went up');
  // ☑️ Không hỏi lại: no question
  fgReset();
  const {setNoAsk}=await import('../public/js/v4/no-ask.js');setNoAsk(true);
  await go('jrFgAll');assert.equal(fg.asked.length,0);assert.equal(fg.sent.length,4);
  setNoAsk(false);
  await go('jrFgAllX',{x:'5'});assert.match(view(),/data-x="5" aria-pressed="true"/);await go('jrFgAllX',{x:'1'});
  await go('jrFgRes');delete globalThis.localStorage;
});

test('⚒️ v2: 🎯 Tới S by default (owner 23/10), this device may raise it (mnl.forgeTop): the ⚡ commands carry it',async()=>{
  fgReset();globalThis.localStorage=fakeStorage;store.clear();
  assert.equal(FG.autoTop(),4);assert.match(view(),/data-action="jrFgTop" data-top="4" aria-pressed="true">S</);
  fg.answers.push({message:'⚡',auto:{n:0,ok:0,spent:0,stop:'done',used:0,made:[],left:0}});
  await go('jrFgMax',{id:'w9'});assert.equal(fg.sent[0][1].top,4);
  await go('jrFgTop',{top:'6'});assert.equal(store.get('mnl.forgeTop'),'6');assert.equal(FG.autoTop(),6);
  assert.match(view(),/data-top="6" aria-pressed="true">SSS</);
  fg.answers.push({message:'⚡',auto:{n:0,ok:0,spent:0,stop:'done',used:0,made:[],left:0}});
  await go('jrFgMax',{id:'w9'});assert.equal(fg.sent[1][1].top,6);
  await go('jrFgTop',{top:'9'});assert.equal(FG.autoTop(),4,'nonsense: back to S');assert.equal(store.has('mnl.forgeTop'),false);
  globalThis.localStorage={getItem(){throw new Error('blocked');},setItem(){throw new Error('blocked');},removeItem(){throw new Error('blocked');}};
  assert.equal(FG.autoTop(),4,'no storage: S');FG.setAutoTop(7);
  delete globalThis.localStorage;await go('jrFgRes');
});

test('⚒️ v2: ⏩ Bỏ qua hiệu ứng (localStorage mnl.forgeFast, try/catch): no animation, no wait',async()=>{
  globalThis.localStorage=fakeStorage;store.clear();
  assert.equal(FG.fastFx(),false);FG.setFastFx(true);assert.equal(store.get('mnl.forgeFast'),'1');assert.equal(FG.fastFx(),true);
  assert.match(view(),/data-fv-pref="fast" checked/);
  fgReset();fg.answers.push({message:'🎉',fuse:{ok:true,main:'w1',tier:1}});
  await go('jrFgSel',{id:'w1'});const t0=Date.now();await go('jrFgOne',{id:'w1'});
  assert.ok(Date.now()-t0<FG.FX.wait,'no wait');assert.doesNotMatch(view(),/fv-pop/,'no animation');
  FG.setFastFx(false);assert.equal(store.has('mnl.forgeFast'),false);
  fg.answers.push({message:'🎉',fuse:{ok:true,main:'w1',tier:1}});FG.FX.wait=5;
  await go('jrFgOne',{id:'w1'});assert.match(view(),/fv-pop/,'the effect plays');
  globalThis.localStorage={getItem(){throw new Error('blocked');},setItem(){throw new Error('blocked');},removeItem(){throw new Error('blocked');}};
  assert.equal(FG.fastFx(),false,'no storage: the effects play');FG.setFastFx(true);
  delete globalThis.localStorage;await go('jrFgRes');await go('jrFgSel',{id:''});
});

test('⚒️ v2: the ticks: 🕶️ Ẩn tên is the save\'s setting (forgeAnon), ☑️ Không hỏi lại this device\'s (mnl.noAsk)',async()=>{
  fgReset();globalThis.localStorage=fakeStorage;store.clear();view();
  fire('change',{fvPref:'anon'},{checked:true});await settle();
  assert.deepEqual(fg.sent[0].slice(0,2),['settings',{forgeAnon:true}]);
  fire('change',{fvPref:'noask'},{checked:true});assert.equal(store.get('mnl.noAsk'),'1');
  fire('change',{fvPref:'noask'},{checked:false});assert.equal(store.has('mnl.noAsk'),false);
  fire('change',{fvPref:'fast'},{checked:true});assert.equal(store.get('mnl.forgeFast'),'1');
  fire('change',{fvPref:'fast'},{checked:false});delete globalThis.localStorage;
});
