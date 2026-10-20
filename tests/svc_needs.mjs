// 🧰 / 🔬 public/js/v4/svc-needs.js: the buyer's missing step shows before "Đặt" (directory card, provider page, 🎪 fair),
// read from the buyer's own GET /api/restore/mine and save; other services never get a need.
import assert from 'node:assert/strict';
import {needsFor,needsReset,goNeed} from '../public/js/v4/svc-needs.js';

const calls=[];
const api=(mine,state={})=>({state,json:async url=>{calls.push(url);if(url==='/api/restore/mine')return mine;throw new Error('unexpected '+url);}});
const services=[{id:'xe',name:'Phục hồi xe máy, xe đạp hỏng',items:[{ref:'honda'}]},{id:'nha',name:'Phục hồi một phần nhà xuống cấp',items:[]}];

// no open ticket: hard, with the 🧰 Phục chế đồ button for that service; nothing to bring at all: says so
needsReset();
let n=await needsFor(api({off:false,services,tickets:[]}),[{career:'restore',service:'xe'},{career:'restore',service:'nha'},{career:'milk_tea',service:'tra'}]);
assert.equal(n['restore.xe'].hard,true);assert.match(n['restore.xe'].why,/chọn món cần mang tới thợ/);
assert.deepEqual(n['restore.xe'].go,{action:'restoreDesk',label:'🧰 Mở Phục chế đồ',data:{service:'xe'}});
assert.match(n['restore.nha'].why,/chưa có món nào cần “Phục hồi một phần nhà xuống cấp”/);
assert.equal(n['milk_tea.tra'],undefined,'other services: no need');
// an open ticket for that service: no need; the answer is cached (one GET for the directory, a card and the fair)
needsReset();calls.length=0;
const m={off:false,services,tickets:[{service:'xe',status:'open'}]};
n=await needsFor(api(m),[{career:'restore',service:'xe'}]);assert.equal(n['restore.xe'],undefined);
await needsFor(api(m),[{career:'restore',service:'xe'}]);assert.equal(calls.length,1);
// my own listing never needs anything; nothing to check → no GET
needsReset();calls.length=0;
assert.deepEqual(await needsFor(api(m),[{career:'restore',service:'xe',mine:true}]),{});assert.equal(calls.length,0);

// 🔬 seeds need the farm (🌱 Mở Vườn mới); the farm open and a batch running: wait; recipes need a food shop
n=await needsFor(api(null,{careers:{}}),[{career:'research',service:'giong'},{career:'research',service:'mon'},{career:'research',service:'may'}]);
assert.equal(n['research.giong'].hard,true);assert.equal(n['research.giong'].go.label,'🌱 Mở Vườn mới');
assert.match(n['research.mon'].why,/Mở quán trước đã/);assert.equal(n['research.may'],undefined);
const now=Date.now()/1000;
n=await needsFor(api(null,{current:'farm',careers:{farm:{started:true,data:{plus:{open:true}}},pho:{started:true}},journey:{lab:{seed:{left:2,until:now+3600},recipe:null}}}),
  [{career:'research',service:'giong'},{career:'research',service:'mon'}]);
assert.match(n['research.giong'].why,/đang dùng một lô giống/);assert.equal(n['research.mon'],undefined);
n=await needsFor(api(null,{current:'pho',careers:{farm:{started:true}}}),[{career:'research',service:'giong'}]);
assert.equal(n['research.giong'].hard,false,'the farm is not the current career: only a hint, Đặt stays on');

// the buttons: 🧰 opens its dialog; 🌱 goes to the farm's 🌟 Trại pane
const acts=[];const env={api:{state:{current:'farm'}},act:async(a,d)=>{acts.push([a,d]);}};
await goNeed(env,{action:'restoreDesk',data:{service:'xe'}});
await goNeed(env,{action:'svcGarden',data:{}});
assert.deepEqual(acts,[['restoreDesk',{service:'xe'}],['car:tab',{tab:'plus'}],['job',{}]]);
console.log('svc-needs: restore tickets, research prerequisites, cache, buttons pass');
