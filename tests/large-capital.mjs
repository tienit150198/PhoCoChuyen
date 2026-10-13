import assert from 'node:assert/strict';
import {fundMove,wealthAction,MOVE} from '../public/js/v4/wealth.js';

const state={journey:{story:true,wallet:25_000_000,invest_max:100_000_000,
  bank:{open:true,balance:90_000_000},places:{milk_tea:{fund:600,withdraw_max:0,invest_max:100_000_000}}}};
MOVE.mode.milk_tea='invest';
MOVE.amt['milk_tea:invest']=100_000_000;
assert.equal(fundMove(state,'milk_tea').max,100_000_000);
const sent=[],prompts=[];
await wealthAction('wlInvest',{career:'milk_tea',amount:'100000000'},null,{
  api:{state},renderSheet(){},placeName:()=>'Quán trà sữa',
  confirmAction:async(...args)=>{prompts.push(args);return true;},
  cmd:async(...args)=>{sent.push(args);return {};},
});
assert.deepEqual(sent,[['jr_invest',{career:'milk_tea',amount:100_000_000}]]);
assert.match(prompts[0][1],/25\.000\.000 xu từ ví và 75\.000\.000 xu từ tài khoản/);
state.journey.places.milk_tea={fund:999_999_990,withdraw_max:0,invest_max:10};
MOVE.amt['milk_tea:invest']=100_000_000;
assert.equal(fundMove(state,'milk_tea').max,10,'respect server fund room as well as personal cash');
assert.equal(fundMove(state,'milk_tea').n,10);
state.journey.places.milk_tea.invest_max=0;
assert.equal(fundMove(state,'milk_tea').max,0);
delete state.journey.places.milk_tea.invest_max;
assert.equal(fundMove(state,'milk_tea').max,100_000_000,'older server fallback');
delete MOVE.mode.milk_tea;delete MOVE.amt['milk_tea:invest'];
console.log('Large capital: exact funding source, confirmation, server fund cap, and old-server fallback passed.');
