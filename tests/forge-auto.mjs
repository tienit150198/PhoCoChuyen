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
