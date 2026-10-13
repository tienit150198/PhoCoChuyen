import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
import test from 'node:test';

const url=new URL('../public/js/careers/post_office.js',import.meta.url);
test('post office has a loadable workbench',()=>assert.ok(existsSync(url)));
if(existsSync(url)){
  const {default:career}=await import(url);
  const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
  const x={esc,fmt:String,ui:{},room:{data:{intro:true,stats:{qualified:2,active_days:1},progress:{milestones:[]}}},cc:{zones:[],services:[],notebook:[]},
    cmd:(label,cmd,p)=>`<button data-command="${cmd}" data-payload="${esc(JSON.stringify(p))}">${label}</button>`,
    npc:()=>({display_name:'Mai'}),portrait:()=>'',state:{}};
  const task={id:'post_office-0001-01',known:true,npc:'mai',title:'Bưu gửi',opening:'Một lời hẹn',patience:100,at:0,work:{},lines:[],
    needs:{parcels:[{id:'p1',code:'CT101',item:'Sách',sender:'Lộc',recipient:'Mai',zone_label:'Nội phố',weight_g:500,length_cm:20}],
      steps:[{id:'p1.tariff',parcel:'p1',kind:'tariff',title:'Tính cước',evidence:'500 g'}]}};
  test('tariff step is a labelled numeric input with scoped step payload',()=>{
    const html=career.job(task,x);
    assert.match(html,/inputmode="numeric"/);
    assert.match(html,/post_step/);
    assert.match(html,/p1.tariff/);
    assert.match(html,/aria-label="[^"]+"/);
    assert.match(html,/Bảng cước/);
    assert.doesNotMatch(html,/_key|undefined|NaN/);
  });
  test('choice labels and evidence are escaped and callbacks do not carry answers',()=>{
    const t=structuredClone(task);t.needs.steps=[{id:'p1.identity',parcel:'p1',kind:'identity',title:'Đối chiếu',evidence:'<script>',options:[{id:'match',label:'<b>Khớp</b>'}]}];
    const html=career.job(t,x);
    assert.match(html,/&lt;script>/);assert.match(html,/&lt;b>Khớp&lt;\/b>/);
    assert.doesNotMatch(html,/<script>|_key/);
  });
  test('prepaid collection and return parcels can submit zero postage',async()=>{
    const sent=[];
    const cx={ui:{amt:{fee:0}},send:async(...v)=>sent.push(v),toast:()=>{}};
    await career.actions.amtSend({key:'fee',def:'0',cmd:'post_step',field:'value',extra:JSON.stringify({task:task.id,step:'p1.tariff'})},null,cx);
    assert.equal(sent.length,1);
    assert.equal(sent[0][1].value,0);
  });
}
