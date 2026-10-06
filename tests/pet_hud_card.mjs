// The pet shop's home card (public/js/careers/pet_care.js hudCard). Run by tests/test_career_pet_care.py.
// "Hết khăn, kẹt khách chưa xong nên không khép ca được" (chat C#23990): the card showed only "Làm tiếp" while any
// pet was unfinished, even one parked with ⋯ › Để lát nữa. Closing was never blocked on the server.
import assert from 'node:assert/strict';
import pet,{_test} from '../public/js/careers/pet_care.js';
import {escapeHTML as esc} from '../public/js/icons.js';
const x={esc,cc:{},content:{},ui:{},room:{data:{}},npc:()=>({display_name:'Chị Mây'}),portrait:()=>'<svg></svg>',icon:()=>'→',stock:()=>0,
  button:(label,action,data,cls='')=>`<button class="btn ${cls}" data-action="${action}">${label}</button>`};
const t={id:'pet_care-1-0',title:'Tắm cho Mướp',npc:'pet_care_1',status:'open',deferred:false,known:false,job:'groom'};
const room=(extra={})=>({open:true,tasks:[t],day:2,...extra});
assert.equal(_test.hudCard(room(),t,x,{}),'','nothing parked, no closing time, nothing missing: the shared card');
assert.equal(_test.hudCard({...room(),open:false},t,x,{}),'','closed: the shared card');
const parked={...t,id:'pet_care-1-1',deferred:true};
let html=pet.hudCard(room({tasks:[t,parked]}),t,x,{});
assert.match(html,/data-action="end"[^>]*>Khép ca</,'a parked pet: Khép ca is on the card');
assert.match(html,/data-action="job"[^>]*>Làm tiếp/,'and Làm tiếp stays');
assert.match(html,/class="dc-closing-line[^"]*"[^>]*>⏸️/,'the line says why (shown on a phone too)');
html=pet.hudCard(room(),t,x,{note:'<p class="dc-closing-line">🔔 Đến giờ đóng cửa</p>'});
assert.match(html,/Đến giờ đóng cửa/);assert.match(html,/>Khép ca</,'closing time: Khép ca is on the card');
assert.doesNotMatch(html,/⏸️/);
console.log('pet hud card ok');
