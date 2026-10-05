import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../public/js/v4/fair.js',import.meta.url),'utf8');
const body=source.slice(source.indexOf('function buyPanel(){'),source.indexOf('function oldBuy(){'));
function panel(tier,n,side=0){
 const lt={tier,n,cl:side?'chan':null,cls:side,cot:null},g={tiers:{vua:5,dac_biet:500},cards:3,max_stake:500,modes:[],side_stakes:[2,100]};
 const deps={G:()=>g,F:()=>({wallet:5000}),curMode:()=>null,modeLabel:()=>"Thường",MODE_INFO:{thuong:['','','']},S:{lt},TIER_NAME:{},COLS:[],nowSlot:()=>0,xu:n=>`${n} xu`,esc:s=>s,btn:(label,op,data,cls,extra)=>`<button data-op="${op}"${extra}>${label}</button>`};
 return new Function(...Object.keys(deps),body+'\nreturn buyPanel();')(...Object.values(deps));
}
test('loto disables purchase when cards plus side bets exceed500',()=>{
 assert.match(panel('dac_biet',1,2),/data-op="buy" disabled/);
 assert.doesNotMatch(panel('dac_biet',1),/data-op="buy" disabled/);
 assert.match(panel('dac_biet',2),/data-op="buy" disabled/);
});

