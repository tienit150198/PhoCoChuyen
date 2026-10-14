import assert from 'node:assert/strict';
import {scaleCard, scaleAction} from '../public/js/v4/career-scale.js';

const sample={tier:1,title:'Tạp hóa mở rộng',kind:'business',resource_name:'quầy thanh toán',
  limits:{stock:550,order:80},quota:{available:1,daily:4,cap:12},
  next:{tier:2,title:'Minimart',fee:250000,can_buy:false,requirements:[{label:'Ngày thực đạt chuẩn',got:3,need:7,met:false}]},
  sites:[{id:'base',name:'Cơ sở gốc',resources:2}],resources:[],
  contract:{id:'grocery-1',title:'Tiếp tế <script>',phase:'planning',actions:[{command:'scale_choose',label:'Xác nhận',payload:{id:'grocery-1',option:'a'},fields:[]}]}};
assert.equal(scaleCard(null),'');
const html=scaleCard(sample);
assert.ok(html.includes('250.000'));
assert.ok(html.includes('550')&&html.includes('80'));
assert.ok(html.includes('&lt;script&gt;')&&!html.includes('<script>'));
assert.match(html,/disabled/);
assert.ok(html.includes('scaleVisit'));
assert.ok(html.includes('grocery-1'));
assert.ok(!html.includes('NaN'));
assert.ok(scaleCard({...sample,kind:'agency',next:{...sample.next,fee:0}}).includes('Giao phạm vi'));
assert.ok(!scaleCard({...sample,kind:'community',quota:null}).includes('suất quản lý'));
assert.ok(scaleCard(sample,{compact:true}).includes('Xem mở rộng'));
// F#382/383: today's live status shows while unmet; the rule sits behind "Cách tính ?" and is escaped.
const days={id:'real_days',label:'Ngày thực đạt chuẩn',got:0,need:3,met:false,hint:'Hôm nay: 2/2 việc sạch · còn 1 việc sạch nữa là tính hôm nay',rule:'Ngày thực là ngày lịch 0h–24h <b>'};
const why=scaleCard({...sample,next:{...sample.next,requirements:[days],reason:'Cần thêm 3 ngày thực đạt chuẩn.'}});
assert.ok(why.includes('class="req-hint">Hôm nay: 2/2 việc sạch · còn 1 việc sạch nữa là tính hôm nay<'),'owner 14/10: the live line says what is left today');
assert.match(why,/<details class="req-rule"><summary aria-label="Cách tính: Ngày thực đạt chuẩn">Cách tính \?<\/summary>/);
assert.ok(why.includes('0h–24h &lt;b&gt;')&&why.includes('Cần thêm 3 ngày thực đạt chuẩn.'));
assert.ok(!scaleCard({...sample,next:{...sample.next,requirements:[{...days,got:3,met:true}]}}).includes('req-hint'),'met rows drop the live line');

let calls=0,release;
const el={disabled:false,closest:()=>({querySelectorAll:()=>[]})};
const data={command:'scale_choose',payload:'{"id":"grocery-1","option":"a"}'};
const env={cmd:async()=>{calls++;await new Promise(r=>release=r);return {};},renderSheet:()=>{},toast:()=>{}};
const pending=scaleAction('scaleSubmit',data,el,env);
assert.equal(el.disabled,true);
await scaleAction('scaleSubmit',data,el,env);
assert.equal(calls,1);
release();await pending;
assert.equal(el.disabled,false);
let sent;
const field={name:'quantity',type:'number',value:'80',reportValidity:()=>true};
await scaleAction('scaleSubmit',{command:'scale_stock_buy',payload:'{}'},
  {disabled:false,closest:()=>({querySelectorAll:()=>[field]})},
  {cmd:async(a,p)=>{sent=p;},renderSheet:()=>{},toast:()=>{}});
assert.deepEqual(sent,{quantity:80});
await assert.rejects(()=>scaleAction('scaleSubmit',{command:'reset_all',payload:'{}'},el,env));
console.log('career scale rendering, escaping, numeric fields and double-click checks passed');

const scoped={...sample,sites:[{id:'base',name:'Base'},{id:'branch-1',name:'Branch'}],
 resources:[{id:'r1',site:'base',label:'Base resource'},{id:'r2',site:'branch-1',label:'Branch resource'}],
 stock:{items:[{name:'Supplies',locations:[{site:'base',name:'Base stock'},{site:'branch-1',name:'Branch stock'}]}],actions:[
 {site:'base',command:'scale_stock_receive',label:'Receive base',payload:{order:'s1'}},
 {site:'branch-1',command:'scale_stock_receive',label:'Receive branch',payload:{order:'s2'}},
 {command:'scale_stock_move',label:'Transfer',payload:{},fields:[{name:'source',label:'Source',options:[{value:'base',label:'Base'},{value:'branch-1',label:'Branch'}],value:'base'},{name:'site',label:'Target',options:[{value:'base',label:'Base'},{value:'branch-1',label:'Branch'}],value:'branch-1'}]}]}};
const scopedHTML=scaleCard(scoped,{site:'branch-1'});
assert.ok(!scopedHTML.includes('Receive base')&&!scopedHTML.includes('Base resource')&&!scopedHTML.includes('Base stock'));
assert.ok(scopedHTML.includes('Receive branch')&&scopedHTML.includes('Branch resource'));
assert.match(scopedHTML,/name="source"[^]*?value="branch-1" selected/);
assert.match(scopedHTML,/name="site"[^]*?value="base" selected/);
