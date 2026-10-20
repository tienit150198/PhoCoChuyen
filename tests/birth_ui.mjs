// 🏥 Phòng sinh & nhận nuôi (public/js/v4/birth.js): the chooser, the booking's states, safe names, the payloads.
import assert from 'node:assert/strict';
import {familyView,familyAction} from '../public/js/v4/family.js';
import {leftText} from '../public/js/v4/birth.js';

const birth={npc:{name:'Nhà hộ sinh Phố Mây',emoji:'🏥',price:800000,hours:3},agency:{name:'Trung tâm bảo trợ Phố Mây',emoji:'📄',fee:300000},
  floor:500000,max:5000000,hours:3,burn_pct:5,rooms:[{id:7,name:'<Phòng> Mây',owner:'Cúc',price:650000,stars:4.5,rated:2,born:3,busy:0,full:false}],
  stay:null,rate:null,my_room:null,nurse:null,now:1};
const base={day:'2026-10-21',clock:'Ngày lịch Việt Nam (UTC+7)',child:null,copies:[],requests:[],ready:true,outfits:[],birth};
const married={status:'married'};
const buttons=html=>[...html.matchAll(/<button\b[^>]*>[\s\S]*?<\/button>/g)].map(x=>x[0]);

let html=familyView(base,married,{});
assert.match(html,/800\.000 xu/);assert.match(html,/650\.000 xu/);assert.match(html,/&lt;Phòng&gt; Mây/);assert.doesNotMatch(html,/<Phòng>/);
assert.match(html,/⭐ 4,5 \(2\)/);assert.ok(buttons(html).some(b=>b.includes('fam:birth-book')));
assert.ok(!buttons(html).some(b=>b.includes('fam:request')),'the free request is gone when the server sends birth');
html=familyView(base,married,{mode:'adopt'});
assert.match(html,/300\.000 xu/);assert.match(html,/Trung tâm bảo trợ/);assert.doesNotMatch(html,/650\.000 xu/);
const legacy=familyView({...base,birth:undefined},married,{});
assert.ok(buttons(legacy).some(b=>b.includes('fam:request')),'an older server (rollback): the old invitation still works');

const posts=[],confirms=[];let renders=0;
const env={confirmAction:async(...a)=>{confirms.push(a);return true;}};
const ctx=(f,form={})=>({env,family:f,form,post:async(op,p)=>{posts.push({op,p});return {};},render:()=>renders++});
await familyAction('fam:birth-book',{},ctx(base,{name:' Bông ',where:'7',payer:'partner'}));
assert.deepEqual({...posts[0].p,rid:undefined},{kind:'birth',name:'Bông',where:7,price:650000,payer:'partner',nurse:true,rid:undefined});
assert.equal(posts[0].op,'family_birth_book');assert.match(confirms[0][1],/650\.000 xu/);assert.match(confirms[0][1],/Người ấy trả khi đồng ý/);
await familyAction('fam:birth-book',{},ctx(base,{name:'Na',mode:'adopt',nurse:false}));
assert.deepEqual({...posts[1].p,rid:undefined},{kind:'adopt',name:'Na',where:'agency',price:300000,payer:'me',nurse:false,rid:undefined});
await familyAction('fam:birth-book',{},ctx(base,{name:'Mít',where:'99'}));   // a room gone from the list: the NPC price
assert.equal(posts[2].p.where,'npc');assert.equal(posts[2].p.price,800000);
await familyAction('fam:birth-book',{},ctx(base,{name:'  '}));
assert.equal(posts.length,3,'no name, no post');
const form={};await familyAction('fam:birth-mode',{mode:'adopt'},ctx(base,form));assert.equal(form.mode,'adopt');assert.equal(renders,1);

const stay={id:5,kind:'birth',status:'proposed',name:'Bông',where:'Phòng Mây (Cúc)',emoji:'🏡',price:650000,payer:'partner',mine:false,nurse:'',nurse_ok:true,left:null,due:false,hours:3,paid:'',can_cancel:false,can_answer:true,can_checkin:false};
html=familyView({...base,birth:{...birth,stay}},married,{});
assert.match(html,/Lời mời cần bạn trả lời/);assert.ok(buttons(html).some(b=>b.includes('fam:birth-answer')&&b.includes('accept')));
assert.ok(!buttons(html).some(b=>b.includes('fam:birth-book')));
html=familyView({...base,birth:{...birth,stay:{...stay,payer:'me'}}},married,{});
assert.match(html,/Đồng ý · trả 650\.000 xu/);
html=familyView({...base,birth:{...birth,stay:{...stay,mine:true,payer:'me',can_answer:false,can_cancel:true}}},married,{});
assert.match(html,/Chưa có khoản nào bị trừ/);assert.ok(buttons(html).some(b=>b.includes('fam:birth-cancel')));
html=familyView({...base,birth:{...birth,stay:{...stay,status:'booked',paid:'650.000 xu tiền mặt',can_answer:false,can_checkin:true,can_cancel:true}}},married,{});
assert.ok(buttons(html).some(b=>b.includes('fam:birth-checkin')));assert.match(html,/Hủy · hoàn 650\.000 xu/);
html=familyView({...base,birth:{...birth,stay:{...stay,status:'staying',left:5400,nurse:'Đào',can_answer:false}}},married,{});
assert.match(html,/1 giờ 30 phút/);assert.match(html,/data-birth-end="\d+"/);assert.match(html,/Điều dưỡng Đào/);
assert.match(buttons(html).find(b=>b.includes('fam:birth-done')),/hidden/);assert.ok(!buttons(html).some(b=>b.includes('fam:birth-cancel')));
html=familyView({...base,birth:{...birth,stay:{...stay,status:'staying',left:0,due:true}}},married,{});
assert.doesNotMatch(buttons(html).find(b=>b.includes('fam:birth-done')),/hidden/);
assert.equal(leftText(59),'59 giây');assert.equal(leftText(61),'1 phút 01 giây');assert.equal(leftText(3*3600),'3 giờ 00 phút');

// the baby card line and the birth moment (once)
const child={id:'shared',name:'Bông',stage:'Em bé',origin:'birth',care_days:0,bond:10,needs:{food:85,clean:85,joy:85},acts:[],owned:['basic'],outfit:'basic',
  birth:{where:'Phòng Mây (Cúc)',nurse:'Đào',at:Math.floor(Date.now()/1000)}};
html=familyView({...base,child,birth:{...birth,rooms:[]}},married,{});
assert.match(html,/Chào đời ở Phòng Mây \(Cúc\) · 🩺 Điều dưỡng Đào hỗ trợ/);assert.match(html,/class="mr-born"/);assert.match(html,/Chào mừng bé Bông!/);
await familyAction('fam:born-seen',{},ctx({...base,child}));
assert.doesNotMatch(familyView({...base,child,birth:{...birth,rooms:[]}},married,{}),/class="mr-born"/,'seen: never again');
html=familyView({...base,child:{...child,birth:null}},married,{});
assert.doesNotMatch(html,/Chào đời ở/);

// the homestay owner and the nurse
html=familyView({...base,birth:{...birth,my_room:{can:true,career:'homestay',room:null,staying:0,booked:0}}},null,{});
assert.match(html,/Phòng sinh của bạn/);assert.match(html,/min="500000"/);
await familyAction('fam:room-save',{},ctx({...base,birth:{...birth,my_room:{can:true,room:null}}},{'room:name':'Phòng Gió','room:price':'720000','room:open':false}));
assert.deepEqual({...posts.at(-1).p,rid:undefined},{name:'Phòng Gió',price:720000,open:false,rid:undefined});
html=familyView({...base,birth:{...birth,nurse:{calls:[{id:5,name:'<b>Bông</b>',status:'booked',where:'X',left:null}],helping:[],done:2,full:false}}},null,{});
assert.match(html,/Ca sinh cần điều dưỡng/);assert.match(html,/&lt;b&gt;Bông/);assert.ok(buttons(html).some(b=>b.includes('fam:birth-nurse')&&b.includes('data-id="5"')));
await familyAction('fam:birth-nurse',{id:'5'},ctx({...base}));
assert.deepEqual({...posts.at(-1).p,rid:undefined},{id:5,rid:undefined});
console.log('Birth UI: chooser, prices, payloads, booking states, countdown, the birth moment once, provider and nurse cards passed.');
