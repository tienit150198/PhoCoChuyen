// 🔎 Tìm nghề (journey.js placesSection, owner 14/10 "tìm nghề cũng khó"): search without accents, status/group chips,
// đang làm → mở được → khóa, locked places named with the step that opens them, long groups folded.
import assert from 'node:assert/strict';
import test from 'node:test';

globalThis.document={head:{append(){}},createElement:()=>({getContext:()=>null,dataset:{}}),getElementById:()=>null,querySelector:()=>null,addEventListener:()=>{}};
globalThis.addEventListener=()=>{};
const {journeyHome,findPlan,foldVi}=await import('../public/js/v4/journey.js');

const cats=['food','shop','service','office','outdoor'];
const catalogue=Array.from({length:74},(_,i)=>({id:`c${i}`,short:i===3?'Bán phở':`Nghề ${i}`,place:i===3?'Quán Phở Cây Si':i===4?'Văn phòng Mây':`Nơi ${i}`,category:cats[i%5]}));
const careers=Object.fromEntries(catalogue.map((m,i)=>[m.id,{started:i<9,level:1,day:i+1,job:{},metrics:{}}]));
const unlock=Object.fromEntries(catalogue.map((m,i)=>[m.id,i<60?1:i<70?3:4]));
function env(ui={}){
  return {ui,api:{state:{name:'An',current:'c2',careers,journey:{story:true,intro:true,gender:'female',chapter:2,life_day:10,wallet:100,debt:0,titles:[],skills:[],places:{},
    unlocked:catalogue.slice(0,60).map(m=>m.id),goals:[],maturity:{level:1,xp:0,floor:0,next:100,name:'Mới đến'}}},
    content:{catalogue,journey:{chapters:[{n:1,title:'',tagline:'',intro:[{emoji:'🙂',name:'A',text:'x'}],unlocks:[]},{n:2,title:'',tagline:'',intro:[{emoji:'🙂',name:'A',text:'x'}],unlocks:[]}],unlock_chapter:unlock,skills:[],titles:[],cats:[]}}}};
}
const rows=h=>[...h.matchAll(/<article class="(jr-place jr-row[^"]*|jr-row jr-place locked)"[^>]*data-k="([^"]*)" data-st="(\w+)"[^>]*?( hidden)?(?: style| aria-label)/g)].map(m=>({k:m[2],st:m[3],hidden:!!m[4]}));

test('accent-free folding: phở, Đ and spacing',()=>{
  assert.equal(foldVi('  Quán  PHỞ Đầu hẻm '),'quan pho dau hem');
});
test('whole words win over parts of words, then word starts, then anywhere',()=>{
  const r=['Quán phở · Bán phở','Văn phòng','Photobooth','Trà sữa','Trạm Lắng Nghe'].map(x=>({k:foldVi(x),st:'open',cat:'food'}));
  const show=q=>findPlan(r,{q:foldVi(q),st:'',cat:'',more:{}}).show.map(Number).join('');
  assert.equal(show('pho'),'10000');
  assert.equal(show('tra sua'),'00010');
  assert.equal(show('tr'),'00011');
  assert.equal(show('xyz'),'00000');
});
test('đang làm, then mở được, then khóa; every career is listed and locked ones say how they open',()=>{
  const h=journeyHome(env()),list=rows(h);
  assert.equal(list.length,74);
  const order=list.map(x=>x.st).join(',');
  assert.match(order,/^(mine,){9}(open,){51}(lock,){13}lock$/);
  assert.match(h,/Quán Phở Cây Si/);
  assert.match(h,/🔒 Xong chương 2 là mở/);
  assert.match(h,/🔒 Mở ở chương 4/);
  assert.match(h,/data-action="rankWork"/,'🏆 Xếp hạng nghề stays one tap away');
  assert.ok(h.indexOf('data-career="c2"')<h.indexOf('data-career="c0"'),'the place on screen leads the list');
});
test('long groups fold after six rows behind "Xem thêm"; a search or a chip shows them all',()=>{
  const plain=rows(journeyHome(env()));
  assert.equal(plain.filter(x=>!x.hidden).length,18);
  assert.match(journeyHome(env()),/Xem thêm 45 nơi/);
  const pho=rows(journeyHome(env({jrQ:'pho'}))).filter(x=>!x.hidden);
  assert.deepEqual(pho.map(x=>x.k),[foldVi('Quán Phở Cây Si Bán phở Văn phòng c3')]);
  const office=rows(journeyHome(env({jrCat:'office'}))).filter(x=>!x.hidden);
  assert.ok(office.length>6&&office.every(x=>x.k.includes('van phong')));
  const lock=rows(journeyHome(env({jrSt:'lock'}))).filter(x=>!x.hidden);
  assert.equal(lock.length,14);
  assert.ok(lock.every(x=>x.st==='lock'));
});
test('💵 #406: an honest pay chip (the last shift there, else the posted salary) and "Nhiều xu trước"',async()=>{
  const {payOf}=await import('../public/js/v4/journey.js');
  const cat=catalogue.map((m,i)=>i===10?{...m,pay:[52,66]}:i===11?{...m,pay:[80,140]}:m);
  const cs=Object.fromEntries(Object.entries(careers).map(([id,c])=>[id,{...c,summary:true}]));
  cs.c5={...cs.c5,last_net:340};cs.c6={...cs.c6,last_net:-12};
  const mk=ui=>{const e=env(ui);e.api.content.catalogue=cat;e.api.state.careers=cs;return e;};
  const e=mk();
  assert.deepEqual(payOf(e.api,'c5'),{n:340,text:'💵 ~340 xu/ngày · ca gần nhất'});
  assert.equal(payOf(e.api,'c6').text,'💵 Ca gần nhất lỗ 12 xu');
  assert.deepEqual(payOf(e.api,'c11'),{n:110,text:'💵 Lương 80–140 xu/ngày'});
  assert.equal(payOf(e.api,'c12'),null,'a shop never worked there: no number is made up');
  const h=journeyHome(e);
  assert.match(h,/💵 ~340 xu\/ngày · ca gần nhất/);
  assert.match(h,/💵 Lương 52–66 xu\/ngày/);
  assert.match(h,/data-action="jrPaySort"/);
  const ids=(s,st)=>rows(s).filter(x=>x.st===st).map(x=>x.k.split(' ').pop());
  assert.deepEqual(ids(h,'open').slice(0,3),['c9','c10','c11'],'catalogue order by default');
  const hs=journeyHome(mk({jrPay:true}));
  assert.deepEqual(ids(hs,'open').slice(0,3),['c11','c10','c9'],'the higher salary first, then the rest in catalogue order');
  assert.deepEqual(ids(hs,'mine').slice(0,2),['c5','c6'],'the best last shift leads Đang làm');
  assert.equal(ids(hs,'lock').length,14,'Khóa keeps its chapter order');
});
