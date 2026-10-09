// F#295/#296 in the real quay dialog at phone width (390 px): 🔁 Nhập lại như lần trước with the total first and the
// 👛 shortfall taken from the wallet in the same command, 🏗️ Mở rộng quầy, and 📋 Quản lý chung (counters grouped by
// trade, one tap for a whole group). Synthetic API boundary, real modules and styles; no sideways scroll.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdir} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
import {chromium} from 'file:///C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs';

const root=resolve(import.meta.dirname,'..'),out=resolve(root,'output/playwright/quay-manage');
const biz=(o={})=>({status:'running',reason:'Nhân viên đang bán',paused:false,stock_total:4,sold:0,revenue:0,net:0,server_now:1000,period_seconds:600,
  stock:[{id:'tea',qty:4,cost:3,price:8,keep:0},{id:'milk',qty:0,cost:5,price:12,keep:0}],again:[],expenses:{},recent:[],protection:{label:'',options:[]},...o});
const stall=(id,name,trade,o={},b={})=>({id,name,trade,place:'xe',fund:0,till:0,staff:[{id:`${id}-s`,name:'Lan',wage:10,ask:10,mo:60,g:false}],hist:[],items:[],closed:false,due:0,left:5,
  grow:[{place:'sap',cost:3200},{place:'kiot',cost:14200}],...o,business:biz(b)});
const stalls=[
  stall('q1','Trà Mây','tea',{till:10},{again:[{id:'tea',qty:10},{id:'milk',qty:2}],income:{stock_hours:1.2}}),        // 40 xu: 30 short
  stall('q2','Trà Phố','tea',{till:100},{again:[{id:'tea',qty:5}],status:'out_of_stock',stock_total:0}),
  stall('q3','Hoa Nhỏ','flower',{till:25},{paused:true,status:'paused',reason:'Quầy tạm dừng'}),
];
const data={state:{name:'An',journey:{story:true,life_day:4,wallet:5000,bank:{open:true,balance:0},quay:{stalls,receipts:[],can:['tea','flower']}}},
  content:{journey:{quay:{places:[{id:'xe',name:'Xe đẩy đầu hẻm',slots:1,emoji:'🛺',rent:30,price:800,fund:99},{id:'sap',name:'Sạp chợ Phố',slots:2,emoji:'🏪',rent:100,price:4000,fund:300},{id:'kiot',name:'Ki-ốt mặt phố',slots:3,emoji:'🏬',rent:350,price:15000,fund:900}],
    trades:{tea:{name:'Trà sữa',emoji:'🧋'},flower:{name:'Hoa',emoji:'💐'}},items:[],orders:[{id:'vua',name:'Vừa'}],weather:{},pace:{},unlimited:true,served:10,chapter:3}}}};
const html=`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/app.css"><script type="module">
import {openQuay} from '/js/v4/quay.js';
const api=Object.assign(new EventTarget(),${JSON.stringify(data)});window.calls=[];window.asks=[];
api.refresh=async()=>{};api.json=async()=>({board:[],mine:[],friends:[]});
api.command=async(action,p)=>{calls.push([action,JSON.parse(JSON.stringify(p))]);await new Promise(r=>setTimeout(r,5));
  const st=api.state.journey.quay.stalls.find(s=>s.id===p.stall);
  if(action==='jr_quay_till'){api.state.journey.wallet+=st.till;st.till=0;}
  if(action==='jr_quay_pause'){st.business.paused=p.on;st.business.status=p.on?'paused':'running';}
  if(action==='jr_quay_upgrade'){st.place=p.place;st.grow=st.grow.filter(g=>g.place!=='sap'&&g.place!==p.place);}
  api.dispatchEvent(new Event('state'));return {message:'OK'};};
window.fixture={api,open:()=>openQuay({api,closeSheet(){},confirmAction:async(title,msg,label,money)=>{asks.push({title,msg,label,money});return true;}})};await fixture.open();
</script>`;
const server=createServer(async(req,res)=>{try{if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return;}const path=resolve(root,'public','.'+decodeURIComponent(req.url.split('?')[0]));if(!path.startsWith(resolve(root,'public')))throw Error('path');res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[extname(path)]||'application/octet-stream');res.end(await readFile(path));}catch{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true}),page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2}),errors=[];
page.on('pageerror',e=>errors.push(String(e)));
const noSideways=async()=>assert.ok(await page.locator('.qy-sheet').evaluate(e=>e.scrollWidth-e.clientWidth)<=1,'No sideways scroll at 390px');
const settle=()=>page.waitForFunction(()=>!document.querySelector('.qy-sheet')?.getAttribute('aria-busy')||document.querySelector('.qy-sheet').getAttribute('aria-busy')==='false');
try{
  await page.goto(`http://127.0.0.1:${server.address().port}`);await page.waitForSelector('.qy-sheet[open]');
  // 🔁 on the first counter: the total on the button, the shortfall said before the tap
  await page.locator('[data-qk="st:q1"] [data-qy="more"][data-part="stock"]').click();
  const again=page.locator('[data-qk="st:q1"] [data-qy="again"]');
  assert.match(await again.textContent(),/Nhập lại như lần trước · 40 xu/);
  assert.match(await page.locator('[data-qk="st:q1"] .qy-again').textContent(),/Thiếu 30 xu, lấy từ ví/);
  await noSideways();await page.screenshot({path:resolve(out,'again-390.png')});
  await again.click();await page.waitForFunction(()=>window.calls.length>=1);await settle();
  let asks=await page.evaluate(()=>window.asks);
  assert.equal(asks.length,1);assert.equal(asks[0].label,'Nhập hàng · 40 xu');assert.equal(asks[0].money.cost,30);assert.match(asks[0].msg,/thiếu 30 xu, lấy từ ví/);
  let calls=await page.evaluate(()=>window.calls);
  assert.deepEqual(calls[0],['jr_quay_restock',{stall:'q1',items:{tea:10,milk:2},wallet:true}],'One command: the order and the wallet flag');
  // the second counter has enough in its till: no wallet flag
  await page.locator('[data-qk="st:q2"] [data-qy="more"][data-part="stock"]').click();
  await page.locator('[data-qk="st:q2"] [data-qy="again"]').click();await page.waitForFunction(()=>window.calls.length>=2);await settle();
  calls=await page.evaluate(()=>window.calls);
  assert.deepEqual(calls[1],['jr_quay_restock',{stall:'q2',items:{tea:5}}]);
  assert.equal((await page.evaluate(()=>window.asks))[1].money,null);
  // 🏗️ Mở rộng quầy: in 🛠️ Nâng cấp, the price difference on the button and in the confirm
  await page.locator('[data-qk="st:q1"] [data-qy="more"][data-part="up"]').click();
  const grow=page.locator('[data-qk="st:q1"] [data-qy="grow"][data-place="sap"]');
  assert.match(await grow.textContent(),/Mở rộng · 3\.200 xu/);
  assert.ok(await page.locator('[data-qk="st:q1"] [data-qy="grow"][data-place="kiot"]').isDisabled(),'Not enough money: the button says so');
  await noSideways();await page.screenshot({path:resolve(out,'grow-390.png')});
  await grow.click();await page.waitForFunction(()=>window.calls.length>=3);await settle();
  calls=await page.evaluate(()=>window.calls);asks=await page.evaluate(()=>window.asks);
  assert.deepEqual(calls[2],['jr_quay_upgrade',{stall:'q1',place:'sap',confirm:true}]);
  assert.equal(asks.at(-1).money.cost,3200);assert.match(asks.at(-1).msg,/Giữ nguyên hàng, nhân viên/);
  // 📋 Quản lý chung: grouped by trade, the biggest group first, one tap per group
  await page.evaluate(()=>{window.calls.length=0;window.asks.length=0;});
  await page.locator('[data-qy="manage"]').click();await page.waitForSelector('.qy-group');
  const groups=await page.locator('.qy-group h3').allTextContents();
  assert.deepEqual(groups.map(t=>t.trim()),['🧋 Trà sữa · 2 quầy','💐 Hoa · 1 quầy']);
  assert.equal(await page.locator('.qy-mrow').count(),3);
  assert.equal(await page.locator('.qy-mrow.low').count(),2,'Out of stock and nearly out are marked');
  const text=await page.locator('.qy-sheet').textContent();assert.doesNotMatch(text,/\d\s*%/,'No odds or rates in the overview');
  await noSideways();await page.screenshot({path:resolve(out,'manage-390.png'),fullPage:true});
  await page.locator('[data-qk="grp:flower"] [data-qy="bulkOpen"]').click();await page.waitForFunction(()=>window.calls.length>=1);await settle();
  assert.deepEqual(await page.evaluate(()=>window.calls),[['jr_quay_pause',{stall:'q3',on:false}]]);
  await page.locator('[data-qk="grp:tea"] [data-qy="bulkTill"]').click();await page.waitForFunction(()=>window.calls.length>=3);await settle();
  assert.deepEqual((await page.evaluate(()=>window.calls)).slice(1).map(c=>c[0]+':'+c[1].stall),['jr_quay_till:q1','jr_quay_till:q2']);
  assert.match(await page.locator('.qy-sheet .bk-flash').textContent(),/Đã thu két 2 quầy/);
  await page.locator('.qy-manage-top [data-qy="bulkAgain"]').click();await page.waitForFunction(()=>window.calls.length>=5);await settle();
  const bulk=(await page.evaluate(()=>window.calls)).slice(3);
  assert.deepEqual(bulk.map(c=>c[1].stall),['q1','q2']);
  assert.ok(bulk.every(c=>c[0]==='jr_quay_restock'&&c[1].wallet===true),'Empty tills: each shortfall from the wallet');
  assert.equal((await page.evaluate(()=>window.asks)).length,1,'One confirm for the whole group');
  // a row opens its counter's card
  await page.locator('[data-qy="goStall"][data-id="q3"]').click();await page.waitForSelector('[data-qk="st:q3"]');
  assert.equal(await page.locator('.qy-group').count(),0);
  assert.deepEqual(errors,[]);
  console.log('Quay manage (390px): again with the total and the wallet shortfall, grow, overview by trade with bulk taps passed.');
}finally{await browser.close();server.close();}
