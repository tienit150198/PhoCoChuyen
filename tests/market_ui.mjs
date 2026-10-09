// 📈 Lãi nhân viên theo thị trường + 🔥 nghề hot (game/staff_market.py → public/js/market-ui.js): few words, right numbers.
import assert from 'node:assert/strict';
import test from 'node:test';
import {mx,marketTag,marketLine,sparkline,curveAverage} from '../public/js/market-ui.js';

const store=new Map();
globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
const words=s=>s.trim().split(/\s+/).length;

test('the multiplier reads the Vietnamese way',()=>{
  assert.equal(mx(130),'×1,3');assert.equal(mx(80),'×0,8');assert.equal(mx(200),'×2');assert.equal(mx(246),'×2,5');assert.equal(mx(100),'×1');
});

test('a tag only when it matters: hot, high, low',()=>{
  const state={market:{hot:'clothing',x:{clothing:220,teacher:130,pho:80,grocery:104}}};
  assert.deepEqual(marketTag(state,'clothing'),['🔥 Nghề hot ×2,2','amber']);
  assert.deepEqual(marketTag(state,'teacher'),['📈 Lãi cao ×1,3','green']);
  assert.deepEqual(marketTag(state,'pho'),['📉 Lãi thấp ×0,8','']);
  assert.equal(marketTag(state,'grocery'),null);
  assert.equal(marketTag(state,'nowhere'),null);
  assert.equal(marketTag({},'clothing'),null);
  for(const id of ['clothing','teacher','pho'])assert.ok(words(marketTag(state,id)[0])<=4);
});

test('the Sổ tiệm line: hot, the trend arrow, a tiny curve',()=>{
  assert.equal(marketLine({x:210,was:205,hot:true}),'🔥 Hôm nay lãi cao ×2,1');
  assert.equal(marketLine({x:130,was:120,hot:false}),'📈 Lãi đang cao ×1,3 ↑');
  assert.equal(marketLine({x:80,was:85,hot:false}),'📉 Lãi đang thấp ×0,8 ↓');
  assert.equal(marketLine({x:100,was:100,hot:false}),'Lãi bình thường ×1');
  const svg=sparkline([100,110,120,130]);
  assert.match(svg,/^<svg class="mk-spark"/);assert.match(svg,/aria-hidden="true"/);
  assert.equal(sparkline([]),'');
});

test('the away card says the market that applied while away',async()=>{
  const slot=1800,now=Date.UTC(2026,9,9,13,0),curve=Array.from({length:96},(_,i)=>i>=90?150:100);
  const v={curve,slot,server_now:now/1000};
  assert.deepEqual(curveAverage(v,now-2.5*3600*1000,now),{x:150,hot:false});
  assert.deepEqual(curveAverage(v,now-60*3600*1000,now).hot,false);
  assert.equal(curveAverage({...v,curve:curve.map(()=>220)},now-3600e3,now).hot,true);
  const {workplaceAway,awayLine}=await import('../public/js/away-report.js?mk=1');
  const T0=now-3*3600*1000;
  const shop=served=>({ops:{staff:[{status:'hired'}],business:{served,net:served*20,revenue:served*30,wages:0,materials:0,goods:0,profit_bonus:0,used:[],
    market:{x:150,was:150,hot:false,curve,slot},server_now:now/1000}}});
  assert.equal(workplaceAway(shop(10),'pho','An',T0),null);
  const rep=workplaceAway(shop(40),'pho','An',now);
  assert.ok(rep.mx&&rep.mx.x>100);
  assert.match(awayLine(rep),/lãi 600 xu \(×1,\d\)$/);
});
