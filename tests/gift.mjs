// Unit test of public/js/v4/gift.js (🎁 Quà mừng card): when there is an offer and what keeps
// it waiting. Run by tests/test_gift.py (node tests/gift.mjs); exits non-zero on failure.
import assert from 'node:assert/strict';
import {offer,waitReason} from '../public/js/v4/gift.js';

const GIFT={id:'open2026',amount:150,label:'Quà mừng mở server',until:'2026-10-07T23:59:59+07:00',until_text:'07/10'};
const st=(gift=GIFT,journey={story:true,intro:true,life_day:3})=>({settings:{whatsNewSeen:''},journey:{...journey,gift},current:'grocery'});
assert.deepEqual(offer(st()),GIFT);
assert.equal(offer(st(null)),null,'claimed or expired: the server sends null');
assert.equal(offer(st({id:'x',amount:0})),null);
assert.equal(offer(null),null);

function doc({hidden=false,tour=false,confirm=false,dialogs=[]}={}){
  return {hidden,
    getElementById:id=>id==='tutLayer'&&tour?{isConnected:true}:id==='confirmDialog'?{open:confirm}:null,
    querySelectorAll:sel=>sel==='dialog[open]'?dialogs:[]};
}
const env=state=>({api:{state}});
const none=()=>false,notes=()=>true;
assert.equal(waitReason(env(st()),doc(),none),'','nothing in the way: the card may open');
assert.equal(waitReason(env(st()),doc(),notes),'whatsnew','"Có gì mới" first, never two cards at once');
assert.equal(waitReason(env(null),doc(),none),'loading');
assert.equal(waitReason(env(st(GIFT,{story:true,intro:false,life_day:1})),doc(),none),'intro','after naming the character');
assert.equal(waitReason(env(st()),doc({tour:true}),none),'tour','after the tutorial');
assert.equal(waitReason(env(st()),doc({dialogs:[{id:'tutWelcome'}]}),none),'tour');
assert.equal(waitReason(env(st()),doc({hidden:true}),none),'hidden');
assert.equal(waitReason(env(st()),doc({confirm:true}),none),'question','not over a question already on screen');
assert.equal(waitReason(env(st()),doc({dialogs:[{id:'sheet'}]}),none),'','over a sheet, like "Có gì mới"');

console.log('gift.mjs: ok');
