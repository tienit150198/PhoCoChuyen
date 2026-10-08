// Feedback #265 (08/10): a wrong check / stamp in Kế toán doanh nghiệp is said big and in place, not in a corner toast.
import assert from 'node:assert/strict';
import ca from '../public/js/careers/corp_accounting.js';
import {escapeHTML as esc} from '../public/js/icons.js';

const toasts=[];let reply=null;const sent=[];
const attrs=d=>Object.entries(d).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const x={esc,ui:{},state:{},cc:{accounts:[],max_circles:3},
  room:{day:3,open:true,data:{office:{clock:540,time:'09:00',limit:1050,limit_time:'17:30',trust:50,notes:[],can:{work:true}},today:{rules:[]},care:{}},metrics:{served:5},tasks:[]},
  npc:()=>({display_name:'Chị Hạnh'}),portrait:()=>'',icon:()=>'',fmt:String,money:String,render:()=>{},
  toast:(m,k)=>toasts.push([m,k]),
  send:async(command,payload,options)=>{sent.push([command,payload,options]);return reply;},
  cmd:(label,command,payload={},style='')=>`<button type="button" class="btn ${style}" data-command="${command}" data-payload="${esc(JSON.stringify(payload))}">${label}</button>`,
  confirmCmd:()=>'',button:(label,action,d={},style='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(d)}>${label}</button>`};
const step={id:'acct',kind:'choice',title:'Chọn tài khoản',prompt:'Ghi Nợ tài khoản nào?',state:'current',docs:[],options:[{id:'152',label:'152'},{id:'156',label:'156'}]};
const t={id:'corp_accounting-0003-01',career:'corp_accounting',status:'in_progress',known:true,variant:'journal',title:'Định khoản',opening:'Ghi giúp chị',
  brief:'',docs:[],proc:[step],proc_state:{at:0,total:1,attempts:{}},tips:[],kind_info:{name:'Định khoản',emoji:'✍️'},due:720};
x.room.tasks=[t];

// A choice answers through car:choose with a quiet send (the career says the result itself).
let html=ca.job(t,x);
assert.match(html,/data-action="car:choose"[^>]*data-answer="152"|data-answer="152"[^>]*data-action="car:choose"/);
assert.match(html,/class="btn ca-opt"/,'the coach still finds the options by .ca-opt[data-opt]');
assert.match(html,/data-opt="152"/);

const why='✗ Mua mây sợi về làm nguyên liệu thì ghi Nợ 152, không phải 156. Hàng mua về để bán lại mới vào 156.';
reply={correct:false,message:why};
await ca.actions.choose({task:t.id,step:'acct',answer:'156'},null,x);
assert.deepEqual(sent.at(-1),['ca_step',{task:t.id,step:'acct',answer:'156'},{quiet:true}]);
assert.equal(toasts.length,0,'no corner toast for the mistake');
html=ca.job(t,x);
assert.match(html,/class="ca-miss" role="alert"/);
assert.ok(html.includes(esc(why.slice(2))),'the whole message, not its first words');
assert.ok(!html.includes('✗ Mua'),'the leading ✗ is the badge, not repeated in the text');
assert.match(html,/data-action="car:missClose"/);
assert.ok(html.indexOf('class="ca-miss"')<html.indexOf('class="ca-options"'),'said above the answers, where the player looks');

// It stays across renders until "Đã hiểu"…
assert.match(ca.job(t,x),/ca-miss/);
ca.actions.missClose({key:`${t.id}:acct`},null,x);
assert.doesNotMatch(ca.job(t,x),/class="ca-miss"/);

// …or the next answer there: a right one clears it and says its line in the usual toast.
reply={correct:false,message:why};
await ca.actions.choose({task:t.id,step:'acct',answer:'156'},null,x);
reply={correct:true,message:'Đúng: mây sợi là nguyên liệu, Nợ 152.'};
await ca.actions.choose({task:t.id,step:'acct',answer:'152'},null,x);
assert.doesNotMatch(ca.job(t,x),/class="ca-miss"/);
assert.deepEqual(toasts.at(-1),['Đúng: mây sợi là nguyên liệu, Nợ 152.',false]);

// A wrong stamp: the note sits on that set, above its paper.
const paper={kind:'invoice',title:'HÓA ĐƠN',rows:[{z:'mst',k:'MST',v:'0107531246'}],foot:[]};
const c1={id:'c1',doc:'invoice',who:'Bà Sáu',quote:'Thanh toán giúp',paper,zones:['mst'],circles:[],stamp:null};
const desk={...t,id:'corp_accounting-0003-00',variant:'desk',proc:[],proc_state:null,cases:[c1],tray:{total:1,stamped:0,ok:0,ready:false}};
x.room.tasks=[desk];
reply={correct:false,result:'wrong',message:'✗ Duyệt nhầm. Hóa đơn này đã ghi sổ hôm trước. Bạn bị trừ 20 xu. Trùng số hóa đơn trong sổ.'};
await ca.actions.stamp({task:desk.id,case:'c1',verdict:'approve'},null,x);
assert.deepEqual(sent.at(-1)[2],{quiet:true});
Object.assign(c1,{stamp:'approve',result:'wrong',truth:{v:'reject',z:['mst'],why:'Trùng số hóa đơn trong sổ.'}});
html=ca.job(desk,x);
assert.ok(html.includes('Bạn bị trừ 20 xu'),'the fine is said, not cut off after the first sentence');
assert.ok(html.indexOf('class="ca-miss"')<html.indexOf('class="ca-sheet'),'above the paper');
console.log('Corp accounting mistake note: in place, whole message, stays until read; right answers still toast.');
