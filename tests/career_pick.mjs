// 🔎 Đổi nghề (v4/career-pick.js, owner 23/10): search without accents ("ban hoa" → Tiệm hoa), everyday words, chips,
// the place you are at first then the last ones worked, and every shut place saying why on its card.
import assert from 'node:assert/strict';
import test from 'node:test';

globalThis.document={head:{append(){}},createElement:()=>({getContext:()=>null,dataset:{}}),getElementById:()=>null,querySelector:()=>null,addEventListener:()=>{}};
globalThis.addEventListener=()=>{};
const {pickPlan,keyOf,lockOf,chapterLock,pickSections,pickView,KEYS}=await import('../public/js/v4/career-pick.js');
const {foldVi,journeyHome}=await import('../public/js/v4/journey.js');

const M=[['milk_tea','Tiệm trà sữa','Trà Mây & Trân Châu','food'],['florist','Tiệm hoa','Tiệm Hoa Nắng','shop'],['pho','Bán phở','Quán phở Cây Si','food'],
  ['police','Công an phường','Công an phường Mây','office'],['nurse','Điều dưỡng','Bệnh viện phường Lá Sen','service'],['stationery','Văn phòng phẩm','Tiệm văn phòng phẩm Bút Mây','shop'],
  ['grocery','Tạp hóa đầu hẻm','Tạp Hoá Cô Ba','shop'],['corp_accounting','Kế toán doanh nghiệp','Công ty CP Mây Tre Xanh','office'],['salon','Salon tóc','Salon Tóc Gió','service']];
const catalogue=M.map(([id,short,place,category])=>({id,short,place,category}));
const unlock={milk_tea:1,florist:1,grocery:1,stationery:1,salon:2,pho:3,police:4,nurse:4,corp_accounting:5};
function env(ui={},more={}){
  const careers=Object.fromEntries(M.map(([id])=>[id,{started:['milk_tea','florist','grocery'].includes(id),day:id==='florist'?7:3,level:2,job:{required:['police','nurse'].includes(id),status:'none'},metrics:{}}]));
  const journey={story:true,intro:true,gender:'female',chapter:2,life_day:10,wallet:100,debt:0,titles:[],skills:[],places:{},goals:[{id:'a',done:true},{id:'b',done:false},{id:'c',done:false}],
    unlocked:['milk_tea','florist','grocery','stationery','salon','nurse'],recent:['grocery','milk_tea','florist'],maturity:{level:1,xp:0,floor:0,next:100,name:'Mới đến'},
    locks:{nurse:{k:'retry',soft:true,t:'⏳ Phỏng vấn lại được từ Ngày 13 (còn 3 ngày)',how:'Lần phỏng vấn trước chưa đạt.'}},...more};
  return {ui,api:{state:{name:'An',current:'milk_tea',careers,journey},content:{catalogue,journey:{unlock_chapter:unlock,chapters:[],skills:[],titles:[],cats:[]}}}};
}
const items=h=>[...h.matchAll(/<li class="cp-item" data-k="([^"]*)" data-sec="(\w+)" data-ok="(\d)" data-done="(\d)" data-cat="(\w+)"( hidden)?>\s*<button[^>]*data-career="(\w+)"/g)]
  .map(m=>({k:m[1],sec:m[2],ok:m[3]==='1',done:m[4]==='1',cat:m[5],hidden:!!m[6],id:m[7]}));

test('accent-free search: "ban hoa" finds Tiệm hoa, everyday words and groups count, whole words win',()=>{
  const rows=catalogue.map(m=>({k:keyOf(m,m.id),sec:'open',ok:true,done:false,cat:m.category}));
  const ids=q=>catalogue.filter((m,i)=>pickPlan(rows,{q:foldVi(q),st:'',cat:'',more:{}}).show[i]).map(m=>m.id);
  assert.deepEqual(ids('ban hoa'),['florist']);
  assert.deepEqual(ids('Bán Hoa'),['florist']);
  assert.deepEqual(ids('cong an'),['police']);
  assert.deepEqual(ids('y ta'),['nurse'],'an everyday word (KEYS) finds Điều dưỡng');
  assert.deepEqual(ids('pho'),['pho'],'phở, not văn phòng phẩm');
  assert.deepEqual(ids('van phong'),['police','stationery','corp_accounting'],'the group Văn phòng counts, and Văn phòng phẩm');
  assert.deepEqual(ids('tra s'),['milk_tea']);
  assert.deepEqual(ids('zzz'),[]);
  for(const [id,k] of Object.entries(KEYS))assert.equal(k,foldVi(k),id+': KEYS are written without accents');
});

test('chips: Làm được · Đã làm · Bị khóa and a group; long sections fold until a search or a chip',()=>{
  const rows=Array.from({length:30},(_,i)=>({k:`noi ${i}`,sec:i<20?'open':'lock',ok:i<20,done:i<5,cat:i%2?'food':'shop'}));
  const p=f=>pickPlan(rows,{q:'',st:'',cat:'',more:{},...f});
  assert.deepEqual([p({}).n.open,p({}).more.open,p({}).more.lock],[20,10,4],'10 of Làm được, 6 of Bị khóa shown first');
  assert.equal(p({st:'ok'}).total,20);assert.equal(p({st:'done'}).total,5);assert.equal(p({st:'lock'}).total,10);
  assert.equal(p({cat:'food'}).total,15);
  assert.equal(p({more:{open:true}}).more.open,undefined);
  assert.equal(p({q:'noi'}).show.filter(Boolean).length,30,'a search shows every match');
});

test('why a place is shut: the server reason first, else the chapter line, else nothing',()=>{
  const e=env();
  assert.equal(lockOf(e.api,'nurse').k,'retry');
  assert.deepEqual(lockOf(e.api,'pho'),{k:'chapter',t:'🔒 Xong chương 2 là mở',how:'Làm xong việc cần làm của chương 2 (đã xong 1/3) là sang chương 3 và mở nơi này.'});
  assert.equal(lockOf(e.api,'police').t,'🔒 Mở ở chương 4');
  assert.equal(lockOf(e.api,'salon'),null);
  assert.equal(chapterLock({chapter:2,goals:[]},undefined).t,'🔒 Chưa mở');
  const free=env({},{story:false});assert.equal(lockOf(free.api,'pho'),null,'outside the story every place is open');
});

test('sections: here first, then the last places worked, then what you can start, then the shut ones (waiting first)',()=>{
  const {secs}=pickSections(env().api);
  assert.deepEqual(secs.map(([id,,ids])=>[id,ids]),[['now',['milk_tea']],['recent',['grocery','florist']],['open',['stationery','salon']],['lock',['nurse','pho','police','corp_accounting']]]);
});

test('the page: search on top, chips, a reason on every shut card and its explanation behind a tap',()=>{
  const h=pickView(env());
  assert.ok(h.indexOf('data-cp-q')<h.indexOf('cp-chips'),'the search comes first');
  assert.match(h,/placeholder="Tìm nghề: phở, bán hoa, công an…"/);
  assert.match(h,/data-action="jrPickClear"[^>]*hidden/,'the clear button waits for a word');
  for(const l of ['Tất cả','Làm được','Đã làm','Bị khóa','Mọi nhóm','💰 Nhiều xu trước'])assert.ok(h.includes(l),l);
  const list=items(h);
  assert.equal(list.length,9);
  assert.deepEqual(list.map(x=>x.id).slice(0,3),['milk_tea','grocery','florist']);
  assert.match(h,/data-action="choose" data-career="milk_tea"/);
  assert.match(h,/data-action="jrPickWhy" data-career="pho" aria-expanded="false" aria-controls="cp-why-pho"/);
  assert.match(h,/🔒 Xong chương 2 là mở/);
  assert.match(h,/⏳ Phỏng vấn lại được từ Ngày 13/);
  assert.match(h,/id="cp-why-nurse"[^>]*hidden><p>Lần phỏng vấn trước chưa đạt\.<\/p><div class="cp-why-go">[\s\S]*?data-action="choose" data-career="nurse"/,'a soft lock still lets you look in');
  assert.match(h,/id="cp-why-corp_accounting"[\s\S]*?data-action="accountingSchool"/,'the exam way in');
  assert.match(h,/id="cp-why-pho"[\s\S]*?data-action="jrView" data-view="home"/,'the goals of the chapter');
  assert.match(h,/Đổi nghề · 5\/9 nơi làm được/);
  const q=items(pickView(env({cpQ:'ban hoa'}))).filter(x=>!x.hidden).map(x=>x.id);
  assert.deepEqual(q,['florist']);
  const locked=items(pickView(env({cpSt:'lock'}))).filter(x=>!x.hidden).map(x=>x.id);
  assert.deepEqual(locked,['nurse','pho','police','corp_accounting']);
});

test('the journey list and the old list say the same reason on a shut place',()=>{
  const e=env({homeMode:'list',jrView:'home'});
  e.api.state.journey.maturity={level:1,xp:0,floor:0,next:100,name:'Mới đến'};
  const h=journeyHome(e);
  assert.match(h,/🔒 Xong chương 2 là mở/);
  assert.match(h,/data-action="jrPick"/,'🔎 Đổi nghề one tap from the list');
  assert.match(journeyHome(env({jrView:'pick'})),/class="cp"/,'jrView pick is the picker');
});
