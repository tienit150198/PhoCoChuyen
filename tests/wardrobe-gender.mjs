// 👗 Tủ đồ & 👕 Cửa hàng, owner 24/10: each piece tagged nam / nữ / unisex (game/wardrobe.py g); a tab shows the character's
// gender + unisex (and anything worn or bought), owned first then by price and level, the rest behind "Xem cả đồ khác";
// the wedding pair says "Mở khi đính hôn" and opens from the engagement (v4/wardrobe.js, v4/shop-shelves.js).
import test from 'node:test';
import assert from 'node:assert/strict';

const store=new Map();
globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
globalThis.document??={querySelector:()=>null,querySelectorAll:()=>[],getElementById:()=>null,createElement:()=>({dataset:{},addEventListener(){}}),head:{append(){}},dispatchEvent(){},addEventListener(){}};

const {wardrobeView,wardrobeAction,arrange,forGender,wdStatus}=await import('../public/js/v4/wardrobe.js');
const {accShopView,accShopAction}=await import('../public/js/v4/acc-shop.js');

const I=(id,slot,name,price=0,g='unisex',need=null)=>({id,slot,name,price,g,need,plain:name});
const wardrobe={shop:'clothing',shop_name:'Tiệm Áo Chỉ Mây',staff_off:20,colors:[],acc_shop:{title:'Tiệm phụ kiện Hạt Cườm'},pairs:{kinds:[],box_max:10},
  slots:[{id:'top',name:'Áo · đầm'},{id:'bottom',name:'Quần · váy'},{id:'acc',name:'Phụ kiện'}],
  items:[I('ao_quen','top','Áo quen thuộc'),I('dam_maxi','top','Đầm maxi vàng nghệ',150,'female'),I('ao_hoodie','top','Áo hoodie tím',90),
    I('ao_cuoi','top','Áo dài cưới đỏ',0,'female','married'),I('vest_cuoi','top','Vest chú rể',0,'male','married'),
    I('ao_hoa','top','Sơ mi hoa đi biển',0,'unisex','level:5'),I('ao_len','top','Áo len mùa đông',80),I('vay_babydoll','top','Váy babydoll hồng',110,'female'),
    I('quan_kem','bottom','Quần lửng kem'),I('vay_xoe','bottom','Chân váy xòe',70,'female'),I('quan_jean','bottom','Quần jean',50),
    I('pk_khong','acc','Không đeo gì'),I('bong_tai','acc','Bông tai ngọc trai',45,'female'),I('kinh_tron','acc','Kính gọng tròn',40)]};
const mk=(gender,extra={})=>{
  const api={content:{journey:{wardrobe,titles:[]}},state:{name:'Minh',journey:{gender,story:false,wallet:5000,maturity:{level:1},titles:[]},
    wardrobe:{look:{},owned:[]},careers:{},...extra},account:{username:'minh'},json:async()=>({}),command:async()=>({})};
  const ui={};return {api,ui,env:{api,ui,renderSheet(){},renderMain(){},toast(){},cmd:async()=>({}),act(){}}};
};
const tops=list=>list.map(x=>x.id);

test('every piece fits a gender or both; no tag (an older server) counts as unisex',()=>{
  assert.equal(forGender({g:'female'},'male'),false);assert.equal(forGender({g:'male'},'male'),true);
  assert.equal(forGender({g:'unisex'},'female'),true);assert.equal(forGender({},'female'),true,'older content: everything shows');
  assert.equal(forGender({g:'male'},null),true,'no gender picked yet: everything shows');
});

test('a tab shows the gender + unisex, owned first then by price and level; the rest behind one switch',()=>{
  const {api}=mk('male',{wardrobe:{look:{},owned:['ao_len']}});
  const top=wardrobe.items.filter(x=>x.slot==='top');
  const {list,hidden}=arrange(api,top);
  assert.deepEqual(tops(list),['ao_quen','ao_len','ao_hoodie','vest_cuoi','ao_hoa'],'owned/free, to buy by price, then locked');
  assert.equal(hidden,3,'the dress, the babydoll and the áo dài cưới are hidden for him');
  const all=arrange(api,top,{all:true});assert.equal(all.hidden,0);assert.equal(all.list.length,top.length);
  assert.ok(tops(all.list).indexOf('ao_len')<tops(all.list).indexOf('ao_hoodie'));
  // a piece of the other gender he wears or bought stays in sight
  const {api:a2}=mk('male',{wardrobe:{look:{},owned:['dam_maxi']}});
  assert.ok(tops(arrange(a2,top).list).includes('dam_maxi'),'bought: shown');
  assert.ok(tops(arrange(api,top,{keep:['vay_babydoll']}).list).includes('vay_babydoll'),'worn / tried on: shown');
  const {api:her}=mk('female');const h=arrange(her,top);
  assert.ok(tops(h.list).includes('ao_cuoi')&&!tops(h.list).includes('vest_cuoi'),'the bride sees the áo dài cưới, not the vest');
  assert.equal(h.hidden,1);
});

test('the wedding pair: "Mở khi đính hôn", open when engaged or married, kept once worn',()=>{
  const it=wardrobe.items.find(x=>x.id==='ao_cuoi');
  assert.deepEqual(wdStatus(mk('female').api,it),{lock:'Mở khi đính hôn'});
  assert.equal(wdStatus(mk('female',{marriage:{spouse:{status:'engaged'}}}).api,it),null);
  assert.equal(wdStatus(mk('female',{marriage:{spouse:{status:'married'}}}).api,it),null);
  assert.equal(wdStatus(mk('female',{wardrobe_plus:{owned:['ao_cuoi'],look:{},wear:{}}}).api,it),null,'kept after a break-up');
});

test('Tủ đồ: his tab, sorted, the switch shows the rest and back',async()=>{
  const {ui,env}=mk('male');
  const h=wardrobeView(env);
  assert.match(h,/data-item="vest_cuoi"/);assert.doesNotMatch(h,/data-item="ao_cuoi"/);assert.doesNotMatch(h,/data-item="dam_maxi"/);
  assert.match(h,/🔒 Mở khi đính hôn/);
  assert.ok(h.indexOf('data-item="ao_quen"')<h.indexOf('data-item="ao_len"')&&h.indexOf('data-item="ao_len"')<h.indexOf('data-item="ao_hoodie"'),'free, then by price');
  assert.match(h,/data-action="jrWdAll" aria-pressed="false">👀 Xem cả đồ khác \(3\)/);
  await wardrobeAction('jrWdAll',{},null,env);assert.equal(ui.wd.all,true);
  const all=wardrobeView(env);assert.match(all,/data-item="ao_cuoi"/);assert.match(all,/data-item="dam_maxi"/);assert.match(all,/Chỉ đồ hợp với bạn/);
  await wardrobeAction('jrWdAll',{},null,env);assert.equal(ui.wd.all,false);
});

test('Cửa hàng 👕 Trang phục and 🎀 Phụ kiện: the same tidy shelf, one switch for both',async()=>{
  const {ui,env}=mk('male');
  ui.as={tab:'wear'};let h=accShopView(env);
  assert.match(h,/data-item="ao_hoodie"/);assert.doesNotMatch(h,/data-item="dam_maxi"/);assert.doesNotMatch(h,/data-item="vay_babydoll"/);
  assert.match(h,/data-action="jrAsAll"[^>]*>👀 Đồ khác \(2\)/);
  ui.as.tab='acc';h=accShopView(env);assert.match(h,/data-item="kinh_tron"/);assert.doesNotMatch(h,/data-item="bong_tai"/);
  await accShopAction('jrAsAll',{},null,env);assert.equal(ui.as.gall,true);
  h=accShopView(env);assert.match(h,/data-item="bong_tai"/);
  ui.as.tab='wear';h=accShopView(env);assert.match(h,/data-item="dam_maxi"/);
  const {ui:u2,env:e2}=mk('female');u2.as={tab:'wear'};const f=accShopView(e2);
  assert.match(f,/data-item="dam_maxi"/);assert.doesNotMatch(f,/jrAsAll/,'nothing hidden for her here: no switch');
});

// 👔 owner 24/10: 28 more pieces for men (game/wardrobe.py MENSWEAR), each drawn in every painter.
const MEN={hair:['toc_re_ngoi','toc_mohican','toc_vuot','toc_dau_dinh','toc_dai_buoc'],
  top:['ao_dai_nam_lam','ao_dai_nam_be','vest_den','vest_xam','so_mi_ke','ao_len_co_lo','ao_khoac_da','ao_ba_ba_nam','ao_gile'],
  bottom:['quan_au_den','quan_kaki_be','quan_short_tt','quan_jean_den'],shoes:['giay_tay_den','giay_luoi_nau','dep_quai_hau','giay_vai'],
  acc:['dong_ho_da','ca_vat','no_co','that_lung','kinh_phi_cong','mu_fedora']};
test('every menswear piece has its own drawing: the mirror, the bust, the town chibi, the chat face',async()=>{
  const {ART,defaultLook,figureSVG,portrait}=await import('../public/js/v4/look.js');
  const {paintWardrobeOverlay}=await import('../public/js/isometric/character-art.js');
  const {autoFace}=await import('../public/js/v4/face-code.js');
  const base=defaultLook('male');
  assert.equal(Object.values(MEN).flat().length,28);
  for(const [slot,ids] of Object.entries(MEN)){
    const figs=new Set([figureSVG(base,'male')]),busts=new Set([portrait(base,'male',80,'')]);
    for(const id of ids){
      assert.ok(ART[slot][id],`${id}: art`);
      const L={...base,[slot]:id};
      figs.add(figureSVG(L,'male'));if(slot!=='bottom'&&slot!=='shoes')busts.add(portrait(L,'male',80,''));
      if(slot==='acc'){
        const calls=[],ctx=new Proxy({createLinearGradient(){return {addColorStop(){}};}},{get:(o,k)=>k in o?o[k]:(...a)=>calls.push([k,...a]),set(o,k,v){calls.push(['set',k,v]);o[k]=v;return true;}});
        paintWardrobeOverlay(ctx,{gender:'male',direction:'se',look:{...L,tint:{[id]:'mint'}}},{x:10,y:8,w:100,h:148});
        assert.ok(calls.some(c=>c.includes('#8fd5c0')),`${id}: drawn on the town chibi in its colour`);
      }
      if(slot==='hair')assert.notEqual(autoFace({journey:{gender:'male'},wardrobe:{look:L}}).hair,undefined);
    }
    assert.equal(figs.size,ids.length+1,`${slot}: each piece changes the mirror`);
    if(slot!=='bottom'&&slot!=='shoes')assert.equal(busts.size,ids.length+1,`${slot}: each piece changes the bust`);
  }
  // tie and bow tie are seen from the front only; the fedora from every side
  for(const [id,back] of [['ca_vat',false],['mu_fedora',true]]){
    const calls=[],ctx=new Proxy({createLinearGradient(){return {addColorStop(){}};}},{get:(o,k)=>k in o?o[k]:(...a)=>calls.push([k,...a]),set(o,k,v){calls.push(['set',k,v]);o[k]=v;return true;}});
    paintWardrobeOverlay(ctx,{gender:'male',direction:'nw',look:{...base,acc:id}},{x:10,y:8,w:100,h:148});
    assert.equal(calls.some(c=>c[0]==='fill'),back,`${id} from the back`);
  }
});
