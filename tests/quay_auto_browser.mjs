// 🤖 Tự nhập hàng (#461) in the real quay dialog at phone width (390 px): the switch at the top of 📋 Quản lý chung next to
// 🔁 Nhập lại, its rule in one line, today's automatic restocks, a note on the counters it could not restock, and one
// jr_quay_auto command per tap. Synthetic API boundary, real modules and styles; no sideways scroll.
// Usage: node tests/quay_auto_browser.mjs [screenshot folder]
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdir} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
import {chromium} from 'file:///C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs';

const root=resolve(import.meta.dirname,'..'),out=resolve(process.argv[2]||resolve(root,'output/playwright/quay-auto'));
const now=Math.floor(Date.now()/1000);
const biz=(o={})=>({status:'running',reason:'Nhân viên đang bán',paused:false,stock_total:40,sold:0,revenue:0,net:0,server_now:now,period_seconds:600,
  stock:[{id:'tea',qty:40,cost:3,price:8,keep:0},{id:'milk',qty:0,cost:5,price:12,keep:0}],again:[],expenses:{},recent:[],protection:{label:'',options:[]},
  auto:{why:null,spent:0,at:null},...o});
const stall=(id,name,trade,o={},b={})=>({id,name,trade,place:'xe',fund:0,till:0,staff:[{id:`${id}-s`,name:'Lan',wage:10,ask:10,mo:60,g:false}],hist:[],items:[],closed:false,due:0,left:5,
  grow:[],...o,business:biz(b)});
const stalls=[
  stall('q1','Trà Mây','tea',{till:400},{again:[{id:'tea',qty:10},{id:'milk',qty:2}],auto:{why:null,spent:36,at:now-600}}),
  stall('q2','Trà Phố','tea',{till:2},{again:[{id:'tea',qty:50}],status:'out_of_stock',stock_total:0,auto:{why:'cash',spent:0,at:null}}),
  stall('q3','Hoa Nhỏ','flower',{till:25},{auto:{why:'none',spent:0,at:null}}),
];
const auto={on:true,low:20,share:30,n:1,xu:36,at:now-600};
const data={state:{name:'An',journey:{story:true,life_day:4,wallet:5000,bank:{open:true,balance:0},quay:{stalls,receipts:[],can:['tea','flower'],auto}}},
  content:{journey:{quay:{places:[{id:'xe',name:'Xe đẩy đầu hẻm',slots:1,emoji:'🛺',rent:30,price:800,fund:99}],
    trades:{tea:{name:'Trà sữa',emoji:'🧋'},flower:{name:'Hoa',emoji:'💐'}},items:[],orders:[{id:'vua',name:'Vừa'}],weather:{},pace:{},unlimited:true,served:10,chapter:3}}}};
const html=`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/app.css"><script type="module">
import {openQuay} from '/js/v4/quay.js';
const api=Object.assign(new EventTarget(),${JSON.stringify(data)});window.calls=[];
api.refresh=async()=>{};api.json=async()=>({board:[],mine:[],friends:[]});
api.command=async(action,p)=>{calls.push([action,JSON.parse(JSON.stringify(p))]);await new Promise(r=>setTimeout(r,5));
  if(action==='jr_quay_auto')api.state.journey.quay.auto.on=p.on;
  api.dispatchEvent(new Event('state'));return {message:p.on?'🤖 Tự nhập hàng: Bật.':'🤖 Tự nhập hàng: Tắt.'};};
window.fixture={api,open:()=>openQuay({api,ui:{},closeSheet(){},confirmAction:async()=>true})};await fixture.open();
</script>`;
const server=createServer(async(req,res)=>{try{if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return;}const path=resolve(root,'public','.'+decodeURIComponent(req.url.split('?')[0]));if(!path.startsWith(resolve(root,'public')))throw Error('path');res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[extname(path)]||'application/octet-stream');res.end(await readFile(path));}catch{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true}),page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2}),errors=[];
page.on('pageerror',e=>errors.push(String(e)));
const noSideways=async()=>assert.ok(await page.locator('.qy-sheet').evaluate(e=>e.scrollWidth-e.clientWidth)<=1,'No sideways scroll at 390px');
try{
  await page.goto(`http://127.0.0.1:${server.address().port}`);await page.waitForSelector('.qy-sheet[open]');
  await page.locator('[data-qy="manage"]').click();await page.waitForSelector('.qy-group');
  const sw=page.locator('.qy-manage-top [data-qy="auto"]');
  assert.equal(await sw.getAttribute('aria-checked'),'true');
  const top=await page.locator('.qy-manage-top').textContent();
  assert.match(top,/Quầy còn dưới 20% kho thì nhập như lần trước, mỗi quầy tối đa 30% két \+ vốn mỗi ngày\./);
  assert.match(top,/Hôm nay đã tự nhập 1 quầy · 36 xu · lần cuối \d\d:\d\d/);
  assert.match(await page.locator('[data-qk="m:q2"]').textContent(),/Thiếu vốn, chưa tự nhập được/);
  assert.match(await page.locator('[data-qk="m:q3"]').textContent(),/Chưa có lần nhập trước/);
  assert.doesNotMatch(await page.locator('[data-qk="m:q1"]').textContent(),/🤖/);
  await noSideways();await page.screenshot({path:resolve(out,'quay-auto-manage-390.png')});
  await page.locator('[data-qk="m:q3"]').scrollIntoViewIfNeeded();
  await page.screenshot({path:resolve(out,'quay-auto-rows-390.png')});
  await sw.click();await page.waitForFunction(()=>window.calls.length>=1);
  await page.waitForFunction(()=>document.querySelector('.qy-manage-top [data-qy="auto"]')?.getAttribute('aria-checked')==='false');
  assert.deepEqual(await page.evaluate(()=>window.calls),[['jr_quay_auto',{on:false}]]);
  assert.doesNotMatch(await page.locator('[data-qk="m:q2"]').textContent(),/Thiếu vốn/,'Switch off: no notes');
  await page.screenshot({path:resolve(out,'quay-auto-off-390.png')});
  assert.deepEqual(errors,[]);
}finally{await browser.close();server.close();}
console.log('quay auto-restock switch at 390 px passed.');
