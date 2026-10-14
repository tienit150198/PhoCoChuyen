import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';

assert.ok(existsSync(new URL('../public/js/v4/career-specialism.js',import.meta.url)), 'specialism UI module must exist');
const {specialismCard, specialismAction}=await import('../public/js/v4/career-specialism.js');
const sample={tier:1,kind:'business',quota:{available:1,daily:4,cap:12},
  catalog:Array.from({length:10},(_,i)=>({tier:i+1,title:`Gói ${i+1}`,fee:3000*(i+1),unlocked:i===0})),
  next:{title:'Bánh <script>',fee:9000,benefit:'Đơn 2 bộ',can_enrol:false,requirements:[{label:'Ngày thực',got:3,need:7,met:false}],action:{command:'special_enrol',label:'Đăng ký',payload:{tier:2}}},
  study:{title:'Thực hành',instructions:['Đong bột','Kiểm nguyên liệu'],feedback:'Thử lại <img>',progress:'1 / 3',actions:[{command:'special_practice',label:'Nộp',payload:{tier:1},fields:[{name:'amount',label:'Định lượng',type:'number',min:1,max:1000000,value:2},{name:'step',label:'Thao tác',type:'select',value:'b',options:[{value:'a',label:'Trộn <b>'},{value:'b',label:'Đong'}]}]}]},
  job:{title:'Đơn bánh',description:'Phục vụ khách',quantity:2,unit:'bộ',phase:'stock',quote:{revenue:600,materials:100,wages:50,premises:20,loss:6,tax:24,net:400},instructions:['Nhập đủ vật tư'],detail:'Giữ riêng cho đơn này',actions:[]},
  stock:{items:[{name:'Bột chuyên môn',code:'flour',unit:'kg',units:5,available:3,capacity:30,order:10,unit_cost:50}],actions:[{command:'special_stock_buy',label:'Nhập bột',payload:{code:'flour'},fields:[{name:'quantity',label:'Số lượng',type:'number',min:1,max:10}]}]},
  history:[{title:'Đơn hôm qua',quality:80,evidence:['Sai. Kiểm lại niêm phong.'],net:200,revenue:500,materials:200,tax:20}],actions:[]};
assert.equal(specialismCard(null),'');
const html=specialismCard(sample);
for(const text of ['9.000','Học phí','Gói 10','Đơn 2 bộ','suất','12','Bột chuyên môn','kg','Dự toán','400','Đơn hôm qua','80%','Sai. Kiểm lại niêm phong.','data-action="specialSubmit"'])assert.ok(html.includes(text),`render ${text}`);
assert.ok(html.includes('&lt;script&gt;')&&!html.includes('<script>'));
assert.ok(html.includes('&lt;img&gt;')&&!html.includes('<img>'));
assert.match(html,/data-command-name="special_enrol"[^>]* disabled/);
assert.match(html,/min="1" max="1000000"/);
assert.match(html,/value="b" selected/);
assert.match(html,/<details class="special-stock" open>/);
assert.match(specialismCard({...sample,job:{...sample.job,phase:'offered'}}),/<details class="special-stock" open>/);
assert.match(specialismCard({...sample,job:{...sample.job,phase:'working'}}),/Thực hiện đơn/);
assert.doesNotMatch(specialismCard({...sample,job:null}),/<details class="special-stock" open>/);
assert.match(specialismCard({tier:0,kind:'community',next:{title:'Công quả',fee:0}}),/Miễn phí/);
{ // F#382/383: the real-day row explains itself and the disabled enrol says why.
  const n={...sample.next,reason:'Cần thêm 3 ngày thực đạt chuẩn.',requirements:[{id:'real_days',label:'Ngày thực đạt chuẩn',got:0,need:3,met:false,hint:'Hôm nay: 3/3 việc sạch · đạt, cộng lúc 0h',rule:'Ngày lịch 0h–24h'}]};
  const out=specialismCard({...sample,next:n});
  assert.ok(out.includes('req-hint')&&out.includes('Hôm nay: 3/3 việc sạch')&&out.includes('class="req-rule"')&&out.includes('Ngày lịch 0h–24h'));
  assert.ok(out.includes('Cần thêm 3 ngày thực đạt chuẩn.'));
}
assert.match(specialismCard({tier:0,kind:'agency',next:{title:'Nghiệp vụ',fee:3000}}),/Học phí/);
assert.doesNotMatch(specialismCard({tier:Infinity,job:{quote:{net:NaN}},actions:[{command:'reset_all',label:'BAD'}]}),/NaN|Infinity|BAD/);
assert.ok(!specialismCard({actions:[{command:'special_ok',label:'<svg>',payload:{x:'" onmouseover="x'},fields:[{name:'x',label:'<img>',value:'"><script>',type:'text'}]}]}).includes('<script>'));

const button=(fields=[])=>({disabled:false,closest:()=>({querySelectorAll:()=>fields})});
let calls=0,release;
const el=button(),data={commandName:'special_start',payload:'{"id":"job-1"}'};
const env={cmd:async()=>{calls++;await new Promise(r=>release=r);}};
const pending=specialismAction('specialSubmit',data,el,env);
assert.equal(el.disabled,true);
await specialismAction('specialSubmit',data,el,env);
assert.equal(calls,1);
release();await pending;assert.equal(el.disabled,false);
assert.equal(await specialismAction('unrelated',{},el,env),false);
let sent;
const send={cmd:async(c,p)=>{sent={c,p};}};
const field=(name,type,value,valid=true)=>({name,type,value,reportValidity:()=>valid});
await specialismAction('specialSubmit',data,button([field('amount','number','5'),field('step','select-one','b')]),send);
assert.deepEqual(sent,{c:'special_start',p:{id:'job-1',amount:5,step:'b'}});
for(const invalid of [field('amount','number','1',false),field('amount','number','Infinity'),field('amount','number',''),field('amount','number','1.5')]){
  sent=null;await specialismAction('specialSubmit',data,button([invalid]),send);assert.equal(sent,null);
}
await assert.rejects(()=>specialismAction('specialSubmit',{commandName:'reset_all'},button(),send));
for(const payload of ['null','[]','1','{'])await assert.rejects(()=>specialismAction('specialSubmit',{...data,payload},button(),send));
await assert.rejects(()=>specialismAction('specialSubmit',data,button([field('__proto__','text','bad')]),send));
const failButton=button();
await assert.rejects(()=>specialismAction('specialSubmit',data,failButton,{cmd:async()=>{throw new Error('offline');}}));
assert.equal(failButton.disabled,false);
console.log('career specialism: rendering, escaping, stock disclosure, fees, validation and action guards passed');
