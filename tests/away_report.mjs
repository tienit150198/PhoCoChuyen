// B4 (backlog 6, F#243 / F#247): the "Lúc bạn vắng" card, from the page's own copy of the totals at the last look.
import assert from 'node:assert/strict';
import test from 'node:test';

const store=new Map();
globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
let n=0;
const fresh=()=>import(`../public/js/away-report.js?tab=${++n}`);   // a new tab: a new module, the same localStorage
const words=s=>s.trim().split(/\s+/).length;
const MIN=60*1000,T0=Date.UTC(2026,9,7,13,0);

function bakery({served=0,net=0,cups=0,beans=0,milk=0,busy=false}={}){
  const used=[['beans_house','Hạt Arabica Đồi Mây',beans],['cup','Ly giấy 12oz',cups],['milk','Sữa tươi',milk]].filter(x=>x[2]);
  return {ops:{staff:[{status:'hired'}],business:{served,net,revenue:served*30,wages:served*8,materials:served,goods:served*10,profit_bonus:served*2,catching_up:busy,used}}};
}

test('a first look only remembers; a return after a while reports what the staff sold and used',async()=>{
  store.clear();
  let m=await fresh();
  assert.equal(m.workplaceAway(bakery({served:10,net:100,cups:10,beans:10}),'cafe_bakery','An',T0),null);
  m=await fresh();
  const rep=m.workplaceAway(bakery({served:47,net:1340,cups:47,beans:40,milk:7}),'cafe_bakery','An',T0+8*60*MIN);
  assert.equal(rep.orders,37);assert.equal(rep.profit,1240);
  assert.deepEqual(rep.items,[['Ly giấy 12oz',37],['Hạt Arabica Đồi Mây',30],['Sữa tươi',7]]);
  const line=m.awayLine(rep);
  assert.match(line,/^🧾 Lúc bạn vắng: nhân viên bán 37 đơn, dùng 37 ly giấy 12oz, 30 hạt Arabica Đồi Mây/);
  assert.match(line,/lãi 1\.240 xu$/);
  assert.ok(words(line)<=25,line);
  const toast=m.awayToast(rep);assert.ok(words(toast)<=8,toast);
  assert.equal(m.awayFresh(rep.key),true);assert.equal(m.awayFresh(rep.key),false,'one toast per return');
  const card=m.workplaceAwayCard(rep);
  assert.match(card,/data-testid="away-report"/);assert.match(card,/<details class="aw-more"><summary>Xem chi tiết<\/summary>/);
  assert.match(card,/Hàng không hết hạn: nhân viên đã bán, tiền vào quỹ nghề/);assert.match(card,/37<\/b> × Ly giấy 12oz/);
  assert.match(card,/data-away-seen="wp\.An\.cafe_bakery"/);assert.match(card,/data-action="warehouse"/);
  // the same tab keeps showing the same frozen report, even as the staff keep working while the player is here
  const again=m.workplaceAway(bakery({served:49,net:1400,cups:49,beans:42,milk:7}),'cafe_bakery','An',T0+8*60*MIN+MIN);
  assert.equal(again.orders,37);
});

test('a short absence, nothing sold, or another account is no report',async()=>{
  store.clear();
  let m=await fresh();m.workplaceAway(bakery({served:5,net:50,cups:5}),'cafe_bakery','An',T0);
  m=await fresh();assert.equal(m.workplaceAway(bakery({served:6,net:60,cups:6}),'cafe_bakery','An',T0+4*MIN),null,'under 5 minutes');
  m=await fresh();assert.equal(m.workplaceAway(bakery({served:6,net:60,cups:6}),'cafe_bakery','An',T0+60*MIN),null,'nothing new since the 4-minute look');
  m=await fresh();assert.equal(m.workplaceAway(bakery({served:50,net:60,cups:6}),'cafe_bakery','Bình',T0+120*MIN),null,'another player on this device');
  assert.equal(m.workplaceAway({ops:{staff:[],business:{served:9}}},'cafe_bakery','An',T0),null,'no staff, no report');
});

test('the offline catch-up still being written keeps counting until it is done',async()=>{
  store.clear();
  let m=await fresh();m.workplaceAway(bakery({served:0,net:0}),'cafe_bakery','An',T0);
  m=await fresh();
  let rep=m.workplaceAway(bakery({served:1024,net:9000,cups:1024,busy:true}),'cafe_bakery','An',T0+48*60*MIN);
  assert.equal(rep.orders,1024);
  rep=m.workplaceAway(bakery({served:1500,net:12000,cups:1500}),'cafe_bakery','An',T0+48*60*MIN+1000);
  assert.equal(rep.orders,1500);assert.deepEqual(rep.items,[['Ly giấy 12oz',1500]]);
});

test('a long item list folds into "+N món" and a loss says lỗ',async()=>{
  store.clear();
  const many=(k)=>({ops:{staff:[{status:'hired'}],business:{served:k,net:-k,revenue:0,used:Array.from({length:9},(_,i)=>[`i${i}`,`Món rất dài số ${i} có tên kép`,k+i])}}});
  let m=await fresh();m.workplaceAway(many(0),'grocery','An',T0);
  m=await fresh();const rep=m.workplaceAway(many(20),'grocery','An',T0+30*MIN);
  const line=m.awayLine(rep);
  assert.ok(words(line)<=25,line);assert.match(line,/\+\d+ món/);assert.match(line,/lỗ 20 xu$/);
});

test('a counter reports from its stock: only sales lower it',async()=>{
  store.clear();
  const stall=(sold,banh,tra)=>({id:'s1',staff:[{id:'e'}],business:{sold,net:sold*12,revenue:sold*20,expenses:{wages:sold,rent:2},stock:[{id:'banh_mi',qty:banh},{id:'tra',qty:tra}]}});
  const name=id=>({banh_mi:'Bánh mì',tra:'Trà đá'})[id];
  let m=await fresh();assert.equal(m.stallAway(stall(3,30,30),'An',name,T0),null);
  m=await fresh();const rep=m.stallAway(stall(40,10,13),'An',name,T0+3*60*MIN);
  assert.equal(rep.orders,37);assert.deepEqual(rep.items,[['Bánh mì',20],['Trà đá',17]]);
  assert.match(m.awayLine(rep,'món'),/bán 37 món, dùng 20 bánh mì, 17 trà đá · lãi 444 xu$/);
  assert.match(m.stallAwayCard(rep),/tiền vào két quầy/);
  assert.equal(m.stallAway({id:'s2',staff:[],business:{sold:9}},'An',name,T0),null,'no staff: the owner sold it');
});

test('in one tab: hours at another workplace, then back, is a return; a hidden tab is no look',async()=>{
  store.clear();
  const m=await fresh();
  assert.equal(m.workplaceAway(bakery({served:10,net:100,cups:10}),'cafe_bakery','An',T0),null);
  assert.equal(m.workplaceAway(bakery({served:11,net:110,cups:11}),'cafe_bakery','An',T0+MIN),null,'still here');
  const rep=m.workplaceAway(bakery({served:40,net:400,cups:40}),'cafe_bakery','An',T0+3*60*MIN);   // after 3 h elsewhere
  assert.equal(rep.orders,29);assert.equal(rep.since,T0+MIN);
  globalThis.document={visibilityState:'hidden',addEventListener(){}};
  try{assert.equal(m.workplaceAway(bakery({served:90,net:900,cups:90}),'cafe_bakery','Bình',T0),null);
    assert.equal(store.has('mnl.away.wp.Bình.cafe_bakery'),false,'a hidden render saves nothing');}
  finally{delete globalThis.document;}
});

test('a broken or blocked storage never breaks the page',async()=>{
  const real=globalThis.localStorage;
  globalThis.localStorage={getItem(){throw new Error('denied');},setItem(){throw new Error('denied');}};
  try{const m=await fresh();assert.equal(m.workplaceAway(bakery({served:3}),'cafe_bakery','An',T0),null);}
  finally{globalThis.localStorage=real;}
});

test('🔒 the owner\'s floor stopped the staff: the card says what it kept (B4 part 2)',async()=>{
  store.clear();
  const kept=[['cup','Ly giấy 12oz',5]];
  const withKeep=(served,k)=>({...bakery({served,net:served*10,cups:served}),ops:{...bakery({served,net:served*10,cups:served}).ops,
    business:{...bakery({served,net:served*10,cups:served}).ops.business,kept:k}}});
  let m=await fresh();m.workplaceAway(withKeep(3,null),'cafe_bakery','An',T0);
  m=await fresh();const rep=m.workplaceAway(withKeep(18,kept),'cafe_bakery','An',T0+6*60*MIN);
  assert.deepEqual(rep.kept,kept);
  const card=m.workplaceAwayCard(rep);
  assert.match(card,/<p class="aw-keep">🔒 Giữ lại 5 ly giấy 12oz cho bạn<\/p>/);
  assert.ok(words(m.awayLine(rep))<=25);
  m=await fresh();const none=m.workplaceAway(withKeep(30,null),'cafe_bakery','An',T0+12*60*MIN);
  assert.doesNotMatch(m.workplaceAwayCard(none),/<p class="aw-keep">/,'no floor reached: no line');
  // a counter names its dishes; three or more fold into "+N món"
  const stall=(sold,k)=>({id:'s1',staff:[{id:'e'}],business:{sold,net:sold,revenue:sold,expenses:{},stock:[{id:'banh_mi',qty:4}],kept:k}});
  const name=id=>({banh_mi:'Bánh mì',tra:'Trà đá',xoi:'Xôi'})[id];
  m=await fresh();m.stallAway(stall(1,null),'An',name,T0);
  m=await fresh();const sr=m.stallAway(stall(9,[['banh_mi',4],['tra',2],['xoi',1]]),'An',name,T0+3*60*MIN);
  assert.match(m.stallAwayCard(sr),/🔒 Giữ lại 4 bánh mì, 2 trà đá, \+1 món cho bạn/);
});

test('🔒 the keep stepper: few taps for a big floor, never below 0 or over 999',async()=>{
  const k=await import('../public/js/keep-ui.js');
  assert.deepEqual([0,9,10,45,50,60,995].map(k.keepUp),[1,10,15,50,60,70,999]);
  assert.deepEqual([0,1,10,15,50,60].map(k.keepDown),[0,0,9,10,45,50]);
  for(let n=0;n<990;n=k.keepUp(n))assert.equal(k.keepDown(k.keepUp(n)),n);   // every step back lands where it came from
  const B={keepable:['cup','milk']};
  assert.equal(k.keepRow({ops:{staff:[],business:B}},'cup'),'','no staff, no floor: nothing to set');
  assert.equal(k.keepRow({ops:{staff:[{status:'hired'}],business:B}},'towel'),'','an item the staff never take');
  assert.equal(k.keepRow({ops:{staff:[{status:'hired'}],business:{}}},'cup'),'','a server without ops_keep (rolling deploy)');
  const row=k.keepRow({ops:{staff:[{status:'hired'}],business_keep:{cup:5},business:B}},'cup','Ly giấy');
  assert.match(row,/🔒 Giữ cho ca bạn/);assert.match(row,/<output[^>]*>5<\/output>/);
  assert.match(row,/data-command="ops_keep" data-payload="\{&quot;item&quot;:&quot;cup&quot;,&quot;qty&quot;:6\}"/);
  assert.match(row,/data-payload="\{&quot;item&quot;:&quot;cup&quot;,&quot;qty&quot;:4\}"/);
  assert.match(k.keepRow({ops:{staff:[],business_keep:{cup:2},business:B}},'cup'),/keep-row/,'a floor set stays editable after the staff leave');
  assert.match(k.keepRow({ops:{staff:[{status:'hired'}],business:B}},'cup'),/aria-label="Giữ ít  hơn" disabled/);
});
