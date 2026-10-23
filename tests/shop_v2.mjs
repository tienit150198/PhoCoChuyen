// 🛍️ Cửa hàng v2 (owner 23/10 "gọn và dễ dùng như các game khác"): one row of tabs, a filtered grid of cards with a
// rarity border and a corner badge, the detail sheet, the small-purchase rule and ☑️ Không hỏi lại (v4/shop-shelves.js,
// v4/payment.js, the pets' cards from v4/pets.js petShopModel).
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const store=new Map();
globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
globalThis.document??={querySelector:()=>null,querySelectorAll:()=>[],createElement:()=>({dataset:{},addEventListener(){}}),head:{append(){}},dispatchEvent(){},addEventListener(){}};

const {bigBuy,askBuy,noAsk,setNoAsk,buyPayment,BIG_BUY_SHARE,NO_ASK_KEY}=await import('../public/js/v4/payment.js');
const {accShopView,accShopAction}=await import('../public/js/v4/acc-shop.js');
const {RARITY,F}=await import('../public/js/v4/shop-shelves.js');

test('a purchase asks only when it is big, never with ☑️ Không hỏi lại',async()=>{
  const J={wallet:8000,bank:{open:true,balance:2000,pref:'auto'}};
  assert.equal(BIG_BUY_SHARE,0.2);assert.equal(NO_ASK_KEY,'mnl.noAsk');
  assert.equal(bigBuy(J,1999),false);assert.equal(bigBuy(J,2000),true,'20% of wallet + bank');
  assert.equal(bigBuy({wallet:-50},10),true,'in debt: always asks');
  let asked=0;const env={api:{state:{journey:J}},confirmAction:async()=>{asked++;return true;}};
  assert.equal(await buyPayment(env,{title:'x',cost:500}),'cash');assert.equal(asked,0,'small: straight through');
  assert.equal(await buyPayment(env,{title:'x',cost:5000}),'cash');assert.equal(asked,1,'big: one question');
  setNoAsk(true);assert.equal(store.get('mnl.noAsk'),'1');assert.equal(noAsk(),true);assert.equal(askBuy(J,9000),false);
  assert.equal(await buyPayment(env,{title:'x',cost:7000}),'cash');assert.equal(asked,1,'ticked: no question of any size');
  assert.equal(await buyPayment(env,{title:'x',cost:9000}),'cash','nothing covers it: still no question, the server says why');assert.equal(asked,1);
  setNoAsk(false);assert.equal(store.has('mnl.noAsk'),false);assert.equal(askBuy(J,9000),true);
  const bad=globalThis.localStorage;globalThis.localStorage={getItem(){throw new Error('blocked');},setItem(){throw new Error('blocked');},removeItem(){throw new Error('blocked');}};
  assert.equal(noAsk(),false,'storage blocked: asks as before');setNoAsk(true);globalThis.localStorage=bad;
});

const wardrobe={shop:'clothing',shop_name:'Tiệm Áo Chỉ Mây',staff_off:20,slots:[{id:'acc',name:'Phụ kiện'},{id:'top',name:'Áo'}],colors:[],acc_shop:{title:'Tiệm phụ kiện Hạt Cườm'},
  pairs:{kinds:[],box_max:10},
  items:[{id:'pk_khong',slot:'acc',name:'Không đeo gì',price:0},{id:'kep_toc',slot:'acc',name:'Kẹp tóc',price:0},{id:'kinh_tron',slot:'acc',name:'Kính tròn',price:90},
    {id:'mu_len',slot:'acc',name:'Mũ len',price:120},{id:'vong',slot:'acc',name:'Vòng ngọc',price:1500},{id:'ao_len',slot:'top',name:'Áo len',price:88}],
  wings:{styles:[{id:'buom',emoji:'🦋',name:'Cánh bướm',price:8800,desc:''}],earn:[2,4,6,8,11,15,20,25],battle:[1,1,2,2,3,4,5,6],fee:[500],own_max:40,qty_max:20,lose_from:4}};
const pets={max:3,name_max:16,buy_qty:5,item_qty:20,
  breeds:[{id:'corgi',kind:'dog',name:'Corgi',price:2000,trait:'Chân ngắn',coats:[{b:'#e9a',m:'#fff',name:'Vàng'}]},{id:'muop',kind:'cat',name:'Mèo mướp',price:900,trait:'Hiền',coats:[{b:'#aaa',m:'#fff',name:'Xám'}]}],
  toys:[{id:'bong',emoji:'🎾',name:'Bóng cao su',price:30,uses:10,kind:'both'},{id:'dia',emoji:'🥏',name:'Đĩa bay',price:120,uses:0,kind:'dog'}]};
const mk=(extra={})=>{
  const api={content:{journey:{wardrobe,pets}},state:{name:'Lan',journey:{gender:'female',story:true,wallet:5000,pets:{story:true,pets:[],own:{bong:3}},...extra},wardrobe:{look:{acc:'kep_toc'},owned:['mu_len']},careers:{}},
    account:{username:'lan'},json:async()=>({}),command:async()=>({})};
  const ui={},toasts=[];return {api,ui,toasts,env:{api,ui,toasts,renderSheet(){},renderMain(){},toast:t=>toasts.push(t),cmd:async()=>({}),act(){}}};
};

test('one row of tabs, cards with a rarity and a corner badge, filters kept in ui.as.f',async()=>{
  const {ui,env}=mk();
  ui.as={tab:'acc'};const h=accShopView(env);
  assert.equal((h.match(/role="tablist"/g)||[]).length,1,'one row of tabs');
  for(const t of ['acc','wear','wing','pet'])assert.match(h,new RegExp(`data-action="jrAsTab" data-tab="${t}"`));
  assert.ok(h.indexOf('data-tab="acc"')<h.indexOf('data-tab="wear"')&&h.indexOf('data-tab="wear"')<h.indexOf('data-tab="wing"')&&h.indexOf('data-tab="wing"')<h.indexOf('data-tab="pair"')&&h.indexOf('data-tab="pair"')<h.indexOf('data-tab="pet"'),'the owner\'s order');
  assert.match(h,/data-item="mu_len"[^>]*>[\s\S]*?Đã có</,'bought: Đã có');assert.match(h,/data-item="kep_toc"[^>]*>[\s\S]*?Đang dùng</,'worn: Đang dùng');
  assert.match(h,/data-item="vong"[^>]*class="as-card t2/,'the dearest of three prices: the third class');
  assert.equal(RARITY.length,6);assert.doesNotMatch(h,/as-wallet/,'the app shows the money already');
  assert.doesNotMatch(h,/data-as-detail/,'nothing picked: no detail sheet');
  // the filter bar's actions keep their state per shelf
  await accShopAction('jrAsF',{key:'acc',k:'r',v:'2'},null,env);assert.equal(F(ui.as,'acc').r,2);
  const only=accShopView(env);assert.match(only,/data-item="vong"/);assert.doesNotMatch(only,/data-item="kinh_tron"/);assert.match(only,/Độ hiếm: <b>Hiếm<\/b>/);
  await accShopAction('jrAsF',{key:'acc',k:'reset',v:''},null,env);assert.deepEqual(F(ui.as,'acc'),{r:-1,sort:'',miss:false,g:''});
  await accShopAction('jrAsF',{key:'acc',k:'miss',v:'1'},null,env);await accShopAction('jrAsF',{key:'acc',k:'r',v:'2'},null,env);
  await accShopAction('jrAsF',{key:'acc',k:'r',v:'1'},null,env);
  assert.match(accShopView(env),/Không có món nào khớp bộ lọc[\s\S]*data-k="reset"/,'nothing left: one way back');
  // 🐾 one tab for the pets, its shelves as chips; the last one opened comes back
  await accShopAction('jrAsTab',{tab:'pet'},null,env);assert.equal(ui.as.tab,'pbuy');
  await accShopAction('jrAsTab',{tab:'ptoy'},null,env);await accShopAction('jrAsTab',{tab:'acc'},null,env);await accShopAction('jrAsTab',{tab:'pet'},null,env);
  assert.equal(ui.as.tab,'ptoy');
});

test('the detail sheet: try-on, total, one Mua, ☑️ Không hỏi lại; a small buy goes straight through with a toast',async()=>{
  const {api,ui,env,toasts}=mk();setNoAsk(false);
  ui.as={tab:'acc'};await accShopAction('jrAsTry',{item:'kinh_tron'},null,env);assert.equal(ui.as.draft,'kinh_tron');
  const d=accShopView(env);
  assert.match(d,/<section class="as-detail t\d" role="dialog" aria-labelledby="as-d-h"/);assert.match(d,/aria-label="Nhân vật của bạn đeo thử Kính tròn"/);
  assert.equal((d.match(/class="btn primary as-d-go"/g)||[]).length,1,'one primary button');assert.match(d,/Mua · 90 xu/);
  assert.match(d,/data-action="jrAsNoAsk"/);assert.doesNotMatch(d,/data-action="jrAsNoAsk" checked/);
  let asked=0,sent=null;env.confirmAction=async()=>{asked++;return true;};env.cmd=async(op,p,o)=>{sent=[op,p,o];return {ok:true};};
  await accShopAction('jrAsBuy',{item:'kinh_tron'},null,env);
  assert.equal(asked,0,'90 of 5.000 xu: no question');assert.deepEqual(sent,['jr_wd_buy',{item:'kinh_tron',wear:true,pay:'cash'},{quiet:true}]);
  assert.match(toasts.at(-1),/\+1 Kính tròn/);assert.equal(ui.as.draft,null,'bought and worn: the sheet closes');
  await accShopAction('jrAsTry',{item:'vong'},null,env);await accShopAction('jrAsBuy',{item:'vong'},null,env);assert.equal(asked,1,'1.500 of 5.000 xu (≥ 20%): asks');
  await accShopAction('jrAsNoAsk',{},{type:'checkbox',checked:true},env);assert.equal(store.get('mnl.noAsk'),'1');
  ui.as.draft='vong';assert.match(accShopView(env),/data-action="jrAsNoAsk" checked/);
  await accShopAction('jrAsBuy',{item:'vong'},null,env);assert.equal(asked,1,'ticked: buys at once');
  await accShopAction('jrAsNoAsk',{},{type:'checkbox',checked:false},env);assert.equal(noAsk(),false);
  // 🪽 wings: the quantity, the reveal in the sheet, ⚒️ when three of a tier can go up
  api.state.journey.wings={own:[{id:'w1',k:'buom',r:0},{id:'w2',k:'buom',r:0}],on:null};
  ui.as={tab:'wing',wtry:'buom'};env.cmd=async()=>({wings:[{k:'buom',r:0}]});const seen=[];env.toast=(t,k,o)=>seen.push([t,o]);
  api.state.journey.wallet=900000;
  await accShopAction('jrAsWingBuy',{k:'buom'},null,env);
  assert.deepEqual(ui.as.reveal,[{k:'buom',r:0}]);assert.equal(ui.as.wtry,'buom','the sheet stays on the style');
  api.state.journey.wings.own.push({id:'w3',k:'buom',r:0});
  const w=accShopView(env);assert.match(w,/wg-reveal[\s\S]*data-action="jrForge" data-tab="wing"/);
  assert.equal(seen.at(-1)[0],'🪽 +1 Cánh bướm');
});

test('🐾 the pets\' shelves as cards (v4/pets.js petShopModel) and their detail with the dialog\'s own main button',async()=>{
  const {env,ui}=mk();const {petShopModel,petShopPick}=await import('../public/js/v4/pets.js');
  const toy=petShopModel(env,'toy');
  assert.deepEqual(toy.cards.map(x=>[x.id,x.price,x.own,x.g]),[['bong',30,3,''],['dia',120,0,'dog']]);assert.match(toy.note,/Chưa có bé nào/);
  assert.equal(toy.detail,null);
  petShopPick(env,'toy','dia');const t2=petShopModel(env,'toy');
  assert.equal(t2.detail.id,'dia');assert.match(t2.detail.bar,/data-pt="go"/);assert.match(t2.detail.bar,/Mua · 120 xu/);
  const buy=petShopModel(env,'buy');assert.deepEqual(buy.cards.map(x=>[x.id,x.g]),[['corgi','dog'],['muop','cat']]);assert.equal(buy.detail,null,'another shelf: a fresh pick');
  ui.as={tab:'ptoy'};accShopView(env);await new Promise(r=>setTimeout(r,1700));   // v4/pets.js loads on first sight (lazy.js waits for its stylesheet)
  petShopPick(env,'toy','bong');
  const h=accShopView(env);
  assert.match(h,/data-action="jrAsTab" data-tab="pbuy"/);assert.match(h,/data-action="jrAsPet" data-id="bong" aria-pressed="true" class="as-card t\d sel"/);
  assert.match(h,/class="pt-root pt-embed as-ptd"/,'the dialog\'s clicks (data-pt) work in the sheet');assert.match(h,/data-action="jrAsNoAsk"/);
  const pj=readFileSync(new URL('../public/js/v4/pets.js',import.meta.url),'utf8');
  assert.equal((pj.match(/shopAsk\(pr[^)]*\)&&!await ask/g)||[]).length,4,'every purchase of the shop asks by the one rule');
});
