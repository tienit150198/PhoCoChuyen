import assert from 'node:assert/strict';
import test from 'node:test';
import * as invest from '../public/js/v4/invest.js';
import {acceptQuote,marketView} from '../public/js/v4/invest-market.js';
const clock={tick:8,market_day:2,as_of:1791157200,next_at:1791157800,timestamps:[1791156000,1791156600,1791157200]};
const I={unlocked:true,need:500,wallet:1000,rules:{cent:100,coin:1000,min_trade:10,fee_pct:2,rate_milli:3,term:7},saving:{balance:0,pending:0,earned:0,term_left:7},coin:{price:10000,prices:[9000,9500,10000],change:5,units:1000,value:100,basis:90,unrealised:10,realised:0,fees:2,market_clock:clock},log:[],badges:[],scam:null};
const G={p:500,buy:513,sell:487,y:490,hist:[480,490,500],phan:12,cost:550,value:584,market_clock:clock};
const quote=(range='1D',tick=8)=>({...clock,range,tick,epoch:1791150000,coin:{price:10000,previous:9500,points:[[1791156000,9000],[1791157200,10000]],news:{}},gold:{price:500,previous:490,points:[[1791156000,480],[1791157200,500]],news:{}}});
const fixture=()=>({api:{state:structuredClone({invest:I,vang:G,journey:{wallet:1000}})},ui:{view:'home',jrView:'invest'},renderSheet(){}});
const flush=async()=>{for(let i=0;i<10;i++)await Promise.resolve();};
test('real axes, range choices, chart scrubber and limited market history',()=>{
 const env=fixture();acceptQuote(env,quote());let html=invest.investView(env);
 assert.match(html,/data-action="ivRefresh"/);assert.match(html,/Cập nhật giá/);
 for(const span of ['1H','1D','3D','1W','1M'])assert.match(html,new RegExp('data-range="'+span+'"'));
 assert.match(html,/ngoài đời/);assert.match(html,/iv-chart-grid/);assert.match(html,/data-iv-point/);
 assert.match(html,/toàn bộ lịch sử đã có/);assert.match(html,/1 giờ thực = 1 ngày thị trường/);
 env.ui.ivMarket='gold';assert.match(invest.investView(env),/trục giá theo xu và thời gian thực/);
});
test('socket subscription replaces full-state polls, switches range and unsubscribes hidden/closed',async()=>{
 const old={document:globalThis.document,setTimeout:globalThis.setTimeout,clearTimeout:globalThis.clearTimeout};
 const doc=new EventTarget(),sheet=new EventTarget(),sent=[],listeners={};let reads=0,full=0;
 Object.assign(sheet,{open:true});Object.assign(doc,{hidden:false,getElementById:()=>sheet});
 globalThis.document=doc;globalThis.setTimeout=()=>1;globalThis.clearTimeout=()=>{};
 const env=fixture();env.marketLive={state:'open',flags:{market:true},send:f=>{sent.push(f);return true;},on:(t,f)=>listeners[t]=f};
 env.api.refresh=async()=>full++;env.api.json=async()=>{reads++;return quote();};env.renderSheet=()=>doc.dispatchEvent(new Event('sheetrender'));
 try{
  invest.investBoot(env);invest.investBoot(env);assert.equal(sent.length,1);
  listeners.market_quote(quote());
  for(let i=0;i<100;i++)env.renderSheet();await flush();assert.equal(reads,0);assert.equal(full,0);assert.equal(sent.length,1);
  await invest.investAction('ivRange',{range:'1W'},null,env);assert.equal(sent.length,2);assert.equal(sent[1].range,'1W');
  listeners.market_quote(quote('1W'));doc.hidden=true;doc.dispatchEvent(new Event('visibilitychange'));assert.equal(sent.at(-1).open,false);
  doc.hidden=false;doc.dispatchEvent(new Event('visibilitychange'));assert.equal(sent.at(-1).range,'1W');
  listeners.welcome({});assert.equal(sent.at(-1).range,'1W');
  sheet.open=false;sheet.dispatchEvent(new Event('close'));assert.equal(sent.at(-1).open,false);
  assert.equal(full,0);
 }finally{Object.assign(globalThis,old);}
});
test('manual refresh coalesces clicks, errors retry without polling and never loads full save',async()=>{
 const env=fixture();let requests=0,finish;
 env.api.json=()=>{requests++;return new Promise(r=>finish=r);};env.api.refresh=()=>assert.fail('full state requested');
 const p=invest.investAction('ivRefresh',{},null,env);const second=invest.investAction('ivRefresh',{},null,env);await flush();
 assert.equal(requests,1);assert.equal(env.ui.ivRefreshing,true);finish(quote());await Promise.all([p,second]);assert.equal(env.ui.ivRefreshing,false);
 env.ui.ivBusy=true;await invest.investAction('ivRefresh',{},null,env);assert.equal(requests,1);env.ui.ivBusy=false;
 env.api.json=async()=>{requests++;throw Error('offline');};await invest.investAction('ivRefresh',{},null,env);assert.match(env.ui.ivRefreshError,/cập nhật/);
 env.api.json=async()=>{requests++;return quote();};await invest.investAction('ivRefresh',{},null,env);assert.equal(env.ui.ivRefreshError,'');assert.equal(requests,3);
});
test('older replies never overwrite newer quote or confirmed holdings; display never mutates save',()=>{
 const env=fixture(),original=structuredClone(env.api.state);
 acceptQuote(env,{...quote(),tick:10,coin:{...quote().coin,price:12000}});
 assert.equal(marketView(env).I.coin.price,12000);assert.equal(marketView(env).I.coin.value,120);
 acceptQuote(env,quote('1D',9));assert.equal(marketView(env).I.coin.price,12000);
 assert.deepEqual(env.api.state,original);
 env.api.state.invest.coin.market_clock.tick=11;env.api.state.invest.coin.price=11000;
 assert.equal(marketView(env).I.coin.price,11000);
});
