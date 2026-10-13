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
