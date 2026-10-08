import assert from 'node:assert/strict';
import {investView,investEntry,investAction} from '../public/js/v4/invest.js';

const I={unlocked:true,need:500,max_wallet:1000,wallet:1000,life_day:10,rules:{cent:100,coin:1000,min_trade:10,fee_pct:2,rate_milli:3,term:7},
 saving:{balance:0,pending:0,earned:0,term_left:7},coin:{price:10000,prices:[9000,9500,10000],change:5,units:1000,value:100,basis:90,unrealised:10,realised:0,fees:2},log:[],badges:[],scam:null};
const G={p:500,buy:513,sell:487,y:490,hist:[480,490,500],phan:12,cost:550,value:584,date:'2026-10-05',market_news:{title:'Tin <script>x</script>',direction:'up',active:true}};
const sent=[],asked=[];
const env={api:{state:{invest:I,vang:G,journey:{wallet:1000,bank:{balance:20}}}},ui:{ivMarket:'gold'},renderSheet(){},
 cmd:async(...args)=>sent.push(args),confirmAction:async(...args)=>{asked.push(args);return true;}};
let html=investView(env);
assert.match(html,/data-action="ivMarket"[^>]*data-market="coin"/);
assert.match(html,/data-action="ivMarket"[^>]*data-market="gold"/);
assert.match(html,/id="ivGoldT"/);assert.match(html,/Lãi tạm tính/);
assert.match(html,/&lt;script&gt;x&lt;\/script&gt;/);assert.doesNotMatch(html,/<script>/);
assert.match(html,/ngày thực/);assert.match(html,/ngày sống/);
await investAction('ivGoldQty',{n:'1'},null,env);
await investAction('ivGoldBuy',{},null,env);
assert.deepEqual(sent.pop(),['jr_vang_buy',{phan:1}]);
assert.equal(asked.at(-1)[3].cost,52);
await investAction('ivGoldQty',{n:'50'},null,env);
await investAction('ivGoldSell',{},null,env);
assert.deepEqual(sent.pop(),['jr_vang_sell',{all:true}]);
const before=sent.length;env.confirmAction=async()=>false;
await investAction('ivGoldBuy',{},null,env);assert.equal(sent.length,before);
env.api.state.invest={...I,unlocked:false,max_wallet:20};
env.ui.ivMarket='gold';html=investView(env);
assert.match(html,/data-action="ivGoldBuy"/);assert.match(investEntry(env),/Vàng/);
env.ui.ivMarket='coin';html=investView(env);
assert.match(html,/500 xu/);assert.doesNotMatch(html,/data-action="ivBuy"/);
env.api.state.invest=I;env.ui.ivMarket='coin';
html=investView(env);assert.match(html,/data-action="ivBuy"/);assert.match(html,/data-action="ivSell"/);
let release;env.confirmAction=()=>new Promise(resolve=>{release=resolve;});
const pending=investAction('ivGoldBuy',{},null,env);
assert.equal(env.ui.ivBusy,true);
await investAction('ivGoldBuy',{},null,env);
const tradesBefore=sent.length;release(true);await pending;
assert.equal(sent.length,tradesBefore+1);assert.equal(env.ui.ivBusy,false);
// fb08 (players 07/10: "nhập được số liệu" for big gold trades): typed chỉ and odd phân, buy-max and sell-all chips.
env.api.state.invest=I;env.ui.ivMarket='gold';env.confirmAction=async()=>true;
await investAction('ivGoldQty',{n:'1'},null,env);
await investAction('ivGoldQty',{chi:'12'},null,env);assert.equal(env.ui.ivGoldQty,121);   // the odd phân stays
await investAction('ivGoldQty',{phan:'7'},null,env);assert.equal(env.ui.ivGoldQty,127);   // the chỉ stay
await investAction('ivGoldQty',{chi:'999999'},null,env);assert.equal(env.ui.ivGoldQty,100000);
await investAction('ivGoldQty',{n:'127'},null,env);
await investAction('ivGoldBuy',{},null,env);assert.deepEqual(sent.pop(),['jr_vang_buy',{phan:127}]);
html=investView(env);
assert.match(html,/value="12"[^>]*aria-label="Số chỉ vàng"/);assert.match(html,/value="7"[^>]*aria-label="Số phân vàng lẻ"/);
assert.match(html,/Mua tối đa · 1,9 chỉ/);                          // (1000 + 20) × 10 / 513 = 19 phân
assert.match(html,/data-n="19"/);assert.match(html,/Cả 1,2 chỉ đang giữ/);
delete env.ui.ivGoldQty;html=investView(env);assert.match(html,/Mua · 513 xu/);           // 1 chỉ until picked
console.log('Investment hub: markets, locked coin, escaped news, quotes, cancelled trades and duplicate-click guard passed');
