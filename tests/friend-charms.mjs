// 🤝 Phụ kiện đôi on the client (game/friend_charms.py, góp ý #484, owner 22/10): the pairs worn are drawn on the classic
// character, the round bust and the 2.5D chibi; they never enter lookOf (the live services refuse unknown look keys);
// peers carry them beside their look; 🛍️ Tiệm phụ kiện sells the accessories and the pairs, the wardrobe points there.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {defaultLook,lookOf,figure,figureOf,paintPlayer,SVG,portrait,myPortrait,cleanPairs,setPairs,myPairs,withPairs,paintPairs,pairsBust,pairIcon,PAIR_KINDS,withWings,cleanWing} from '../public/js/v4/look.js';
import {characterKey} from '../public/js/isometric/character-art.js';
import {decodeCozyPortrait} from '../public/js/isometric/portraits.js';
import {accShopView} from '../public/js/v4/acc-shop.js';
import {adopt,pairsCard,waiting} from '../public/js/v4/charms.js';

const state={name:'Lan',journey:{gender:'female',story:true,wallet:5000},wardrobe:{look:{...defaultLook('female'),acc:'kep_toc'}},careers:{}};
const svgOf=F=>{const out=[];paintPlayer(out,F,SVG);return out.join('');};

test('only known kinds, 1 to 99 each',()=>{
  assert.deepEqual(cleanPairs({tri_ki:2,chi_cot:'3',ban_than:0,nhan_cuoi:4}),{chi_cot:3,tri_ki:2});
  assert.deepEqual(cleanPairs({ban_than:500}),{ban_than:99});
  for(const bad of [null,[],'tri_ki',{x:1},{tri_ki:-1}])assert.equal(cleanPairs(bad),null);
  assert.deepEqual(PAIR_KINDS,['chi_cot','ban_than','tri_ki','chi_do','huy_hieu','gau_bong','bong_bay','quat','day_chuyen','ngoc_boi'],'the same ids as game/friend_charms_content.py');
  const py=readFileSync(new URL('../game/friend_charms_content.py',import.meta.url),'utf8');
  for(const k of PAIR_KINDS)assert.match(py,new RegExp(`_k\\('${k}'`));
});

test('the player wears them through figure(), never through lookOf()',()=>{
  setPairs(null);
  const plain=svgOf(figure(state));
  setPairs({tri_ki:1,chi_cot:2,ban_than:1});
  assert.deepEqual(myPairs(),{chi_cot:2,ban_than:1,tri_ki:1});
  assert.equal('pr' in lookOf(state),false,'lookOf goes on the wire (live/street.py clean_look refuses unknown keys)');
  const F=figure(state);assert.deepEqual(F.L.pr,{chi_cot:2,ban_than:1,tri_ki:1});
  const worn=svgOf(F);
  assert.ok(worn.length>plain.length+1500,'the three pieces are drawn');
  assert.match(worn,/#e3352b/);assert.match(worn,/#f58db1/);assert.match(worn,/#cf2a4b/);
  assert.match(myPortrait(state,40),/#cf2a4b/,'the bust shows them too');
  setPairs(null);assert.equal(figure(state).L.pr,undefined);
});

test('many of a kind stack, a turned back hides the rose, every kind has its own icon',()=>{
  const one=[],three=[];
  paintPairs(one,figureOf(withPairs(defaultLook('male'),{chi_cot:1}),'male'),SVG);
  paintPairs(three,figureOf(withPairs(defaultLook('male'),{chi_cot:7}),'male'),SVG);
  assert.ok(three.length>one.length*2,'up to three cars on the ring');
  const back=[];paintPairs(back,figureOf(withPairs(defaultLook('male'),{tri_ki:1}),'male'),SVG,{back:true});
  assert.equal(back.length,0);
  assert.equal(pairsBust(null),'');assert.match(pairsBust({ban_than:1}),/<path/);
  for(const k of PAIR_KINDS)assert.match(pairIcon(k,64,`Cặp ${k}`),new RegExp(`aria-label="Cặp ${k}"`));
  assert.equal(pairIcon('nhan_cuoi'),'');
  assert.match(portrait(withPairs(defaultLook('female'),{tri_ki:1}),'female',56),/#cf2a4b/);
});

test('the 2.5D chibi: its stamp key carries the pairs, the cozy portrait marker keeps them',()=>{
  const a=characterKey({look:defaultLook('female'),gender:'female'}),b=characterKey({look:withPairs(defaultLook('female'),{ban_than:1,zz:2}),gender:'female'});
  assert.notEqual(a,b);assert.match(b,/"pr":\{"ban_than":1\}/);
  const decoded=decodeCozyPortrait(encodeURIComponent(JSON.stringify({v:1,mode:'face',gender:'female',look:{...defaultLook('female'),pr:{tri_ki:2,bad:1}}})));
  assert.deepEqual(decoded.look.pr,{tri_ki:2});
});

test('a peer on the 2.5D map: pr beside the look, a later switch, and an outfit change keeps it',()=>{
  const src=readFileSync(new URL('../public/js/isometric-town.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
  const ctx=vm.createContext({withPairs,cleanPairs,withWings,cleanWing,lookOf,withBang:x=>x,tagLine:()=>'',tagInk:()=>'',badge:()=>'',publicActivity:()=>null,sitePresence:{},live:{},leisurePresence:{}});
  vm.runInContext(src+'\nglobalThis.peer=publicPeer;',ctx);
  const p=ctx.peer({pid:'p1',x:1,y:2,lk:{top:'ao_quen'},pr:{chi_cot:1,x:1}});
  assert.deepEqual(JSON.parse(JSON.stringify(p.look)),{top:'ao_quen',pr:{chi_cot:1}});
  assert.equal(ctx.peer({pid:'p2',x:1,y:2,lk:{top:'ao_quen'}}).look.pr,undefined);
  assert.match(src,/Object\.hasOwn\(e,'pr'\)/,'a mv with pr retags a walker already drawn');
  const model=readFileSync(new URL('../client/isometric/model.ts',import.meta.url),'utf8');
  assert.match(model,/look\.pr=pr/,'the scene keeps pr when it copies the peer look');
});

test('the classic street draws a walker with its pairs and hears the switch',()=>{
  const walk=readFileSync(new URL('../public/js/v4/walk.js',import.meta.url),'utf8');
  assert.match(walk,/pr:cleanPairs\(p\.pr\)/);
  assert.match(walk,/e\.k==='pr'/);
  assert.match(walk,/figureOf\(withPairs\(p\.lk,p\.pr\),p\.g\)/);
  assert.match(readFileSync(new URL('../public/js/v4/town-walk.js',import.meta.url),'utf8'),/myPairs\(\),wingOfState\(S\(\)\)\]\)/,'the town map sprite key changes with the pairs and the wings');
  assert.match(readFileSync(new URL('../public/js/boba-world.js',import.meta.url),'utf8'),/paintPairs\(c,F\)/,'the workplace character wears them');
});

const content={journey:{wardrobe:{shop:'clothing',shop_name:'Tiệm Áo Chỉ Mây',staff_off:20,slots:[{id:'acc',name:'Phụ kiện'}],colors:[],
  acc_shop:{name:'Tiệm phụ kiện',title:'Tiệm phụ kiện Hạt Cườm'},
  pairs:{kinds:[{id:'chi_cot',emoji:'🏎️',name:'Chí cốt',item:'Móc khóa mô hình siêu xe',price:220,desc:'Hai chiếc siêu xe.',hint:'Hay tặng nhau giữa hai người bạn trai'},
    {id:'ban_than',emoji:'👜',name:'Bạn thân',item:'Túi xách đôi',price:175,desc:'Hai chiếc túi.',hint:'Hay tặng nhau giữa hai cô bạn gái'},
    {id:'tri_ki',emoji:'💐',name:'Tri kỉ',item:'Hoa vĩnh sinh cài áo',price:130,desc:'Hai đóa hồng.',hint:'Hợp với mọi người bạn'}],box_max:10},
  items:[{id:'pk_khong',slot:'acc',name:'Không đeo gì',price:0},{id:'kep_toc',slot:'acc',name:'Kẹp tóc',price:0},{id:'mu_len',slot:'acc',name:'Mũ len',price:120,need:'open:3'},{id:'kinh_tron',slot:'acc',name:'Kính tròn',price:90}]}}};

test('🛍️ Tiệm phụ kiện: the accessory shelf sells, the pair shelf lists gifts, the box, the pairs',()=>{
  const ui={},api={content,state:{...state,journey:{...state.journey,story:false}},account:{username:'lan'},json:()=>new Promise(()=>{})};
  const env={api,ui,renderSheet(){},renderMain(){},toast(){}};
  ui.as={tab:'acc',draft:'kinh_tron',to:''};
  const acc=accShopView(env);
  assert.match(acc,/Tiệm phụ kiện Hạt Cườm/);assert.match(acc,/data-action="jrAsBuy" data-item="kinh_tron"/);assert.match(acc,/Mua Kính tròn · 90 xu/);
  assert.doesNotMatch(acc,/data-item="pk_khong"/,'nothing to sell in "Không đeo gì"');
  ui.as={tab:'pair',draft:null,to:'PCC-MAI'};
  assert.match(accShopView(env),/Đang mở hộp quà/,'the view is read on first sight');
  adopt(api,{charms:{box:[{id:'fc1',kind:'tri_ki',price:130,sell:104}],sent:[{id:'fc2',kind:'chi_cot',name:'Bảo',at:1}],incoming:[{id:'fc3',kind:'ban_than',name:'Mai',at:1}],
    pairs:[{id:'fc4',kind:'tri_ki',name:'Châu',on:true,since:1,mine:true},{id:'fc5',kind:'tri_ki',name:'Mai',on:false,since:2,mine:false}],worn:{tri_ki:1},
    friends:[{code:'PCC-MAI',name:'Mai'}],box_max:10,can_buy:true}},null);
  assert.deepEqual(myPairs(),{tri_ki:1},'the answer sets what the character wears');
  assert.equal(waiting(api),1);
  const pair=accShopView(env);
  assert.match(pair,/Quà đang chờ bạn/);assert.match(pair,/data-action="jrAsAnswer" data-id="fc3" data-answer="accept"/);
  assert.match(pair,/Đang chọn quà cho <b>Mai<\/b>/);assert.match(pair,/Mua &amp; tặng · 220 xu|Mua & tặng · 220 xu/);
  assert.match(pair,/data-action="jrAsGive" data-id="fc1"/);assert.match(pair,/Bán lại · 104 xu/);
  assert.match(pair,/data-action="jrAsCancel" data-id="fc2"/);
  assert.match(pair,/với Châu/);assert.match(pair,/với Mai/);
  assert.equal((pair.match(/data-action="jrAsWear"/g)||[]).length,2,'each pair its own switch, no limit');
  assert.match(pairsCard(env),/đang đeo 1\/2/);
  // 🛒 owner 23/10 "mua thì cho mua nhiều cái 1 lần": a quantity per kind (the box's room), one charm_buy with qty
  assert.match(pair,/data-action="jrAsPairQty" data-kind="tri_ki" data-n="2"/);
  ui.as={tab:'pair',draft:null,to:'',pq:{tri_ki:3}};assert.match(accShopView(env),/Mua cặp ×3 · 390 xu/);
  // 🧺 several accessories at once: the cart and its sum (jr_wd_buy items)
  ui.as={tab:'acc',draft:null,to:'',multi:true,cart:['kinh_tron']};
  const cart=accShopView(env);
  assert.match(cart,/🧺 Giỏ · 1 món/);assert.match(cart,/data-action="jrAsBuyMany"/);assert.match(cart,/Mua cả giỏ · 90 xu/);
  assert.match(cart,/class="wd-item in-cart" data-action="jrAsTry" data-item="kinh_tron" aria-pressed="true"/);
  setPairs(null);
});

test('the wardrobe sends a missing accessory or piece to Cửa hàng; the menus open it and ⚒️ Cường hóa',()=>{
  const wd=readFileSync(new URL('../public/js/v4/wardrobe.js',import.meta.url),'utf8');
  assert.match(wd,/r\.it\.slot==='acc'\?btn\(`🛍️ Mua/);
  assert.match(wd,/'jrAccShop',\{tab:'wear',item:r\.it\.id\}/,'Tủ đồ\'s clothes buy button opens the 👕 shelf with the piece');
  const app=readFileSync(new URL('../public/js/app.js',import.meta.url),'utf8');
  assert.match(app,/\['jrAccShop','bag','Cửa hàng'/);assert.match(app,/charmsBoot\(api\)/);
  assert.match(app,/\['jrForge','wrench','Cường hóa'\]/);
  assert.doesNotMatch(app,/Shop Phố Mây/,'one name: Cửa hàng (owner 23/10 "cửa hàng hoặc shop đều là 1")');
  // 🛍️ its own entry (owner 23/10 "shop riêng"), no longer inside the "Của mình" hub; ⚒️ likewise
  for(const a of ['jrAccShop','jrForge'])assert.doesNotMatch(app.match(/\['minh','gift','Của mình',\[[^\]]*\]/)[0],new RegExp(a));
  const town=readFileSync(new URL('../public/js/isometric/town-utilities.js',import.meta.url),'utf8');
  assert.doesNotMatch(town,/\['jrAccShop'/,'Tiện ích: one Cửa hàng button, no second list of its shelves');
  const shell=readFileSync(new URL('../public/js/isometric-shell.js',import.meta.url),'utf8');
  assert.match(shell,/control\('Cửa hàng','jrAccShop'/);assert.match(shell,/control\('Cường hóa','jrForge'/);
});

test('🛍️ Cửa hàng: 👤 Cho bạn, 🐾 Thú cưng and 🏠 Nhà & xe shelves',async()=>{
  const {townUtilityGroups,townServiceAvailable,forgeOpen}=await import('../public/js/isometric/town-utilities.js');
  const pets={wardrobe:{items:[],slots:[]},tiers:{}};
  const st={journey:{story:true,gender:'female',pets:{}}},ct={journey:{pets}};
  assert.equal(townUtilityGroups(st,ct,{}).some(g=>g.items.some(i=>i.action==='jrAccShop')),false);
  assert.equal(townServiceAvailable('jrAccShop',{journey:{story:true,gender:'male'}},{},{}, {tab:'pbuy'}),false,'no pets on the server: no pet shelf');
  assert.equal(townServiceAvailable('jrAccShop',{journey:{story:true}},ct,{}),false,'no character yet');
  assert.equal(forgeOpen(st,ct),true,'pets with tiers: ⚒️');assert.equal(forgeOpen({journey:{gender:'male'}},{journey:{wardrobe:{wings:{}}}}),true,'wings: ⚒️');
  assert.equal(forgeOpen({journey:{gender:'male'}},{journey:{}}),false,'nothing to ghép: no ⚒️');
  assert.equal(townServiceAvailable('jrForge',st,ct,{}),true);
  const wd={...content.journey.wardrobe,slots:[{id:'top',name:'Áo · đầm'},...content.journey.wardrobe.slots],items:[...content.journey.wardrobe.items,{id:'ao_len',slot:'top',name:'Áo len',price:88}]};
  const ui={},api={content:{...content,journey:{...content.journey,wardrobe:wd,pets:{...pets,breeds:[]}}},state:{...state,journey:{...state.journey,story:true,pets:{story:true,pets:[]},garage:true,gadgets:true}},account:{username:'lan'},json:()=>new Promise(()=>{})};
  const env={api,ui,renderSheet(){},renderMain(){},toast(){}};
  ui.as={tab:'wear',cdraft:'ao_len'};
  const wear=accShopView(env);
  assert.match(wear,/🛍️ Cửa hàng/);assert.match(wear,/data-action="jrAsGroup" data-group="pet"/);assert.match(wear,/data-action="jrAsGroup" data-group="more"/);
  assert.match(wear,/data-tab="wear"><span aria-hidden="true">👕<\/span>Trang phục/);
  assert.match(wear,/data-action="jrAsClBuy" data-item="ao_len"/);assert.match(wear,/Mua Áo len · 88 xu/);
  assert.match(wear,/class="wd-item on" data-action="jrAsClTry" data-item="ao_len"/,'the piece sent from Tủ đồ is on the mirror');
  assert.match(wear,/class="chip active" aria-pressed="true" data-action="jrAsClSlot" data-slot="top"/,'on its own rack');
  // the pet shelf is v4/pets.js, loaded on first sight (lazy.js: a stylesheet link and an event)
  globalThis.document??={querySelector:()=>null,createElement:()=>({dataset:{},addEventListener(){}}),head:{append(){}},dispatchEvent(){},addEventListener(){}};
  for(const t of ['acc','pair','wear'])assert.match(wear,new RegExp(`data-action="jrAsTab" data-tab="${t}"`));
  assert.doesNotMatch(wear,/data-tab="pbuy"/,'the other group\'s shelves wait behind its switch');
  ui.as.tab='pbuy';
  const pet=accShopView(env);
  for(const t of ['pbuy','pwear','pwing','ptoy','pgear'])assert.match(pet,new RegExp(`data-tab="${t}"`));
  assert.match(pet,/mnl-skel/,'the pet shelf loads v4/pets.js on first sight');
  ui.as.tab='nope';accShopView(env);assert.equal(ui.as.tab,'acc','an unknown shelf falls back to 🎀');
  // 🏠 Nhà & xe: a card for each screen that sells the rest, only those this save has
  ui.as.tab='more';const more=accShopView(env);
  assert.match(more,/class="jr-card as-kind as-more" data-action="garage"/);assert.match(more,/data-action="gadgets"/);
  assert.doesNotMatch(more,/data-action="lux"/,'no 💎 on this save');assert.doesNotMatch(more,/data-action="jrAsTab"/,'one shelf: no tabs');
  // v4/pets.js draws its own shelf in the sheet: same picks (data-pt), same main button, the way to a pet first
  const {petEmbedHTML}=await import('../public/js/v4/pets.js');
  api.content.journey.pets.toys=[{id:'bong',emoji:'🎾',name:'Bóng nảy',price:30}];
  const toy=petEmbedHTML(env,'toy');
  assert.match(toy,/class="pt-root pt-embed"/);assert.match(toy,/data-pt="item" data-id="bong"/);assert.match(toy,/data-pt="go"/);
  assert.match(toy,/Chưa có bé nào/);assert.match(toy,/data-action="jrAccShop" data-tab="pbuy"/);assert.match(toy,/data-action="pets" data-tab="adopt"/);
  assert.doesNotMatch(toy,/data-pt="kind"/,'the shop\'s tabs pick the shelf, not the dialog\'s chips');
});

test('⚒️ Cường hóa: wings ghép there, ⚡ Cường hóa nhanh fuses again and again (one command), never the worn wing',async()=>{
  const {wingSets,wingPlan,forgeView,forgeTabs}=await import('../public/js/v4/acc-shop.js');
  const wings={styles:[{id:'buom',emoji:'🦋',name:'Cánh bướm',price:8800,desc:''},{id:'rong',emoji:'🐉',name:'Cánh rồng',price:36000,desc:''}],
    earn:[2,4,6,8,11,15,20,25],battle:[1,1,2,2,3,4,5,6],fee:[500,2000,10000,50000,300000,2e7,2e8],own_max:40,qty_max:20,lose_from:4,auto_max:50};
  const own=[{id:'w1',k:'buom',r:0},{id:'w2',k:'rong',r:0},{id:'w3',k:'buom',r:0},{id:'w4',k:'buom',r:1},{id:'w5',k:'buom',r:1},{id:'w6',k:'rong',r:1},{id:'w7',k:'buom',r:0}];
  const api={content:{journey:{wardrobe:{...content.journey.wardrobe,wings}}},state:{...state,journey:{...state.journey,wings:{own,on:'w5'}}}};
  // as game/wings.py sets: the lowest tier first; the main one the worn wing, else the dearest style; the others the
  // cheapest, never the worn one
  const ids=api=>wingSets(api).map(x=>x.set.map(w=>w.id));
  assert.deepEqual(ids(api),[['w2','w1','w3'],['w5','w4','w6']]);
  api.state.journey.wings={own,on:null};
  assert.deepEqual(ids(api)[1],['w6','w4','w5'],'nothing worn: the dearest style is the main one');
  api.state.journey.wings={own,on:'w1'};
  assert.deepEqual(ids(api)[0],['w1','w3','w7'],'the worn one is the main one, never an ingredient');
  assert.deepEqual(wingSets(api,'rong'),[],'one style: only its wings');
  assert.deepEqual(wingSets(api,'all',1).map(x=>x.r),[0],'ghép tới hạng C: only D → C');
  api.state.journey.wings={own:own.slice(0,2),on:null};assert.equal(wingPlan(api).n,0,'two wings: nothing to ghép');
  api.state.journey.wings={own,on:'w5'};
  assert.deepEqual(wingPlan(api),{...wingPlan(api),n:2,est:2500,min:500});
  assert.deepEqual(forgeTabs(api),['wing'],'no pets on this server: wings only');
  const ui={as:{tab:'acc',wfz:[]}},env={api,ui,renderSheet(){},renderMain(){},toast(){}};
  const fg=forgeView(env);
  assert.match(fg,/⚒️ Cường hóa/);assert.match(fg,/data-action="jrAsWingAuto"/);assert.match(fg,/⚡ Cường hóa nhanh · tiêu tối đa 2\.500 xu/);
  assert.match(fg,/data-as-sel="wascope"/);assert.match(fg,/data-as-sel="watop"/);assert.match(fg,/<option value="7" selected>🌟 Huyền thoại<\/option>/);
  assert.match(fg,/data-action="jrAsWingBud" data-n="5000"[^>]*>×2</,'the budget chips: Vòng đầu / ×2 / ×5 (within the money)');
  assert.match(fg,/⚠️ Từ hạng S trở lên: trượt thì mất hai đôi phụ/,'up to Huyền thoại: what a miss may lose');
  ui.as.watop=4;assert.doesNotMatch(forgeView(env),/⚠️ Từ hạng S/,'up to S only: nothing is ever lost');ui.as.watop=7;
  assert.match(fg,/data-action="jrAsWingPick" data-id="w1"/,'Tự chọn: pick three by hand, below');
  assert.ok(fg.indexOf('jrAsWingAuto')<fg.indexOf('jrAsWingPick'),'⚡ first, Tự chọn below');
  // the last run's summary above the card: turns, successes, misses, xu spent, the wings that went up (the best big)
  ui.as.wres={n:5,ok:3,spent:4500,stop:'budget',used:6,made:[{id:'w4',k:'buom',r:2,z:1}],left:1};
  const res=forgeView(env);
  assert.match(res,/⚡ Kết quả cường hóa nhanh/);assert.match(res,/<b>5<\/b><small>lượt ghép/);assert.match(res,/<b>3<\/b><small>thành công/);
  assert.match(res,/<b>2<\/b><small>trượt/);assert.match(res,/<b>4\.500<\/b><small>xu đã tiêu/);assert.match(res,/Dừng vì chạm số xu đã đặt\. Còn 1 bộ ba\./);
  assert.match(res,/class="fg-ares-best"/);assert.match(res,/data-action="jrAsWingRes"/);
  delete ui.as.wres;
  // owner 23/10 "ghép thì đưa vào mục riêng": what is owned by kind, counted, ⚡ when a set is ready; the wings by tier
  assert.match(fg,/class="fg-kind active"[^>]*data-tab="wing"><span class="fg-kind-e" aria-hidden="true">🪽<\/span><b>Cánh<\/b><small>7 đôi · C×3 D×4<\/small><i class="fg-ready"/);
  assert.match(fg,/<b>Hạng C<\/b> · 3 đôi <small class="muted">· ghép được 1 lần/);assert.match(fg,/<b>Hạng D<\/b> · 4 đôi/);
  assert.doesNotMatch(fg,/tỉ lệ|tỷ lệ|%<\/small>/,'no odds (owner 19/10)');
  // the shop's Cánh shelf buys and wears; the ghép is a way to ⚒️
  ui.as.tab='wing';const shelf=accShopView(env);
  assert.match(shelf,/data-action="jrForge" data-tab="wing"/);assert.doesNotMatch(shelf,/jrAsWingPick|jrAsWingFuse|jrAsWingAuto/);
  assert.match(shelf,/data-action="jrAsWingQty" data-k="buom" data-n="2"/,'🛒 a quantity per style');
  ui.as.wq={rong:3};assert.match(accShopView(env),/Mua ×3 · 108\.000 xu/);
  // every pets' ghép shelf has its ⚡ card (v4/pets.js autoCard in lab, ward, the gear bag), one command each
  const pj=readFileSync(new URL('../public/js/v4/pets.js',import.meta.url),'utf8');
  assert.equal((pj.match(/autoCard\('(lab|ward|gear)'\)/g)||[]).length,3);
  for(const c of ['jr_pet_wfuse_auto','jr_pet_fuse_auto','jr_pet_gear_auto'])assert.match(pj,new RegExp(`cmd='${c}'`));
  assert.match(pj,/case'auto':return runAuto\(data\.kind\);/);
  assert.doesNotMatch(pj,/jrAsWingQuick|case'quick'|pt-autobtn|S\.sub==='wauto'/,'the one-fusion ⚡ and the 🤖 sub view are gone');
  assert.equal((pj.match(/forgeLink\('p(lab|ward|gear)'\)\+/g)||[]).length,3,'the ghép shelves of the dialog link to ⚒️ Cường hóa');
});
