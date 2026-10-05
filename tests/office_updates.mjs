import assert from 'node:assert/strict';
import hr from '../public/js/careers/hr_admin.js';
import {escapeHTML as esc} from '../public/js/icons.js';
const x={esc,ui:{},state:{},room:{day:5,data:{},metrics:{served:5},tasks:[]},cc:{},
 npc:()=>({display_name:'Chị Huyền'}),portrait:()=>'',icon:()=>'',fmt:String,money:String,render:()=>{},
 cmd:()=>'',confirmCmd:()=>'',button:(label,action,d={})=>`<button data-action="${action}" ${Object.entries(d).map(([k,v])=>`data-${k}="${esc(v)}"`).join(' ')}>${label}</button>`};
const t={id:'hr-5-0',career:'hr_admin',status:'waiting',known:true,title:'Lọc hồ sơ',opening:'Hồ sơ',brief:'',ans:{a:'verify',b:'invite'},tips:[],papers:[],work:{type:'sort',bins:[{id:'verify',label:'Cần xác minh',emoji:'🔎'},{id:'invite',label:'Mời phỏng vấn',emoji:'✓'}],items:[{id:'a',title:'Người A',lines:['Ban đầu: 9 tháng']},{id:'b',title:'Người B',lines:[]}],twist:{item:'a',note:'BHXH <đã bổ sung>'}}};
x.room.tasks=[t];x.ui[t.id]={card:'b'};
let html=hr.job(t,x);assert.match(html,/data-action="car:reviewUpdate"/);assert.match(html,/Xem hồ sơ vừa cập nhật/);assert.match(html,/BHXH &lt;đã bổ sung&gt;/);
hr.actions.reviewUpdate({task:t.id},null,x);assert.equal(x.ui[t.id].card,'a');
t.work={type:'mark',opts:['Đủ công','Nghỉ không phép','Nghỉ có phép'],blocks:[{k:'table',head:['Tên','T2'],rows:[['Người A',{id:'r0d0',t:'—',keep:0}]]}],twist:{seg:'r0d0',note:'Đơn nghỉ đã được duyệt bổ sung'}};t.ans={r0d0:1};
html=hr.job(t,x);assert.match(html,/Mở ô vừa cập nhật/);
hr.actions.reviewUpdate({task:t.id},null,x);assert.equal(x.ui[t.id].seg,'r0d0');
hr.actions.reviewUpdate({task:t.id},null,x);assert.equal(x.ui[t.id].seg,'r0d0','reopening keeps the target selected');
html=hr.job(t,x);assert.match(html,/ow-picker[\s\S]*Đơn nghỉ đã được duyệt bổ sung/);
t.filed=true;t.result={ok:1,total:1,lines:[],errors:[]};html=hr.job(t,x);assert.doesNotMatch(html,/data-action="car:reviewUpdate"/,'filed work is not editable');
console.log('Office updates: targeted card/cell links, persistent selection and escaped context passed.');
