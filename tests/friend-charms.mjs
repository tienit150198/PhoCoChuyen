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
  setPairs(null);
});

test('the wardrobe sends a missing accessory to the shop; the menus open it',()=>{
  const wd=readFileSync(new URL('../public/js/v4/wardrobe.js',import.meta.url),'utf8');
  assert.match(wd,/r\.it\.slot==='acc'\?btn\(`🛍️ Mua/);
  const app=readFileSync(new URL('../public/js/app.js',import.meta.url),'utf8');
  assert.match(app,/\['jrAccShop','bag','Tiệm phụ kiện'/);assert.match(app,/charmsBoot\(api\)/);
  const town=readFileSync(new URL('../public/js/isometric/town-utilities.js',import.meta.url),'utf8');
  assert.match(town,/\['jrAccShop','bag','🎀','Tiệm phụ kiện'\]/);
});
