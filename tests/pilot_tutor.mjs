import assert from 'node:assert/strict';
import {flightLesson} from '../public/js/careers/pilot_tutor.js';
let l=flightLesson('takeoff',{kt:20,ground:true});assert.match(l.target,/110/);assert.match(l.controls,/W/);
l=flightLesson('takeoff',{kt:112,ground:true});assert.match(l.target,/Kéo/);assert.match(l.controls,/↓/);
l=flightLesson('cell',{});assert.match(l.target,/giông/);
l=flightLesson('approach',{ft:900,kt:135,why:'nhanh quá'});assert.match(l.recovery,/Giảm ga/);assert.match(l.target,/115/);
l=flightLesson('approach',{ft:180,kt:115,why:'',canAround:true});assert.match(l.recovery,/bay lại/i);
l=flightLesson('approach',{ft:20,kt:115,why:'',canAround:false});assert.match(l.target,/Thu ga/);assert.doesNotMatch(l.recovery,/G để/);
l=flightLesson('ask',{});assert.match(l.controls,/phương án/);
console.log('Pilot lesson targets, controls and recovery passed.');

const {promotionCard}=await import('../public/js/careers/air_kit.js');
let card=promotionCard({room:{promo:{rank:2,title:'Cơ trưởng',next:{good:2,need:4,title:'Cơ trưởng huấn luyện'}}}}, {id:'pilot'});
assert.match(card,/data-action="promo"/);assert.match(card,/bậc 3/);assert.match(card,/2\/4/);
card=promotionCard({room:{open:false,promo:{rank:3,title:'Cơ trưởng huấn luyện',mgr:true}}},{id:'pilot'});
assert.match(card,/Ca quản lý/);assert.match(card,/Mở ca quản lý/);

const {signalState}=await import('../public/js/v4/traffic.js');
for(const axis of ['x','y']){const red=axis==='x'?16:8;assert.equal(signalState(red+.9,0,axis).grace,true);assert.equal(signalState(red+1,0,axis).grace,false);assert.equal(signalState(red+1,0,axis).color,'red');}
