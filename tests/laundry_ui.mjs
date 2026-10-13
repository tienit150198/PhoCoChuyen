import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
assert.ok(existsSync('public/js/careers/laundry.js'), 'Laundry workbench is implemented');
const {default: laundry}=await import('../public/js/careers/laundry.js');
const sent=[];
const x={esc:s=>String(s).replaceAll('<','&lt;'),ui:{},room:{data:{stats:{good:2,active_days:1}}},
  cc:{stages:{wash:'Chọn chương trình giặt'},rules:['Giặt theo nhãn']},
  cmd:(label,cmd,p)=>`<button data-command="${cmd}">${label}</button>`,
  send:async(cmd,payload)=>sent.push({cmd,payload}),render:()=>{}};
const t={id:'laundry-0001-00',known:true,stage:'wash',quality:100,
  needs:{tag:'NT-0001-00',net:18,cost:4,quantity:2,garments:[{id:'g1',name:'Áo',description:'Cotton trắng',label:'40°C',packing:'Gấp',tag:'NT-0001-00/1'}]},
  options:[{id:'normal40',label:'Thường · 40°C'}],instruction:'Đọc nhãn'};
const html=laundry.job(t,x);
assert.match(html,/label[^>]*for=/);
assert.match(html,/40°C/);
assert.match(html,/data-stage="wash"/);
assert.doesNotMatch(html,/_key|ld_deliver/);
laundry.input({dataset:{ldField:'g1',ldTask:t.id,ldStage:'wash'},value:'normal40',type:'select-one'},x);
await laundry.actions.send({task:t.id,stage:'wash'},null,x);
assert.deepEqual(sent[0],{cmd:'ld_wash',payload:{task:t.id,choices:{g1:'normal40'}}});
assert.match(laundry.idle(x),/100/);
console.log('laundry workbench: labels, current stage, choice submission and progression pass');
