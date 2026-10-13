// F#362: reserve setting, saved preview, collection receipts and preserved drafts at mobile width.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdir} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
import {chromium} from 'file:///C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs';

const root=resolve(import.meta.dirname,'..'),out=resolve(root,'output/playwright/quay-reserve');
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
  if(action==='jr_quay_reserve')st.reserve=p.amount;
  let collected=0,retained=0;
  if(action==='jr_quay_till'){if(st.id==='q2')st.till+=5;retained=Math.min(st.till,Math.max(0,(st.reserve||0)-st.fund));collected=st.till-retained;st.fund+=retained;api.state.journey.wallet+=collected;st.till=0;}
  st.collectable_till=Math.max(0,st.till-Math.max(0,(st.reserve||0)-st.fund));
  if(action==='jr_quay_pause'){st.business.paused=p.on;st.business.status=p.on?'paused':'running';}
  if(action==='jr_quay_upgrade'){st.place=p.place;st.grow=st.grow.filter(g=>g.place!=='sap'&&g.place!==p.place);}
  api.dispatchEvent(new Event('state'));return {message:'OK',collected,retained};};
window.fixture={api,open:()=>openQuay({api,ui:{},closeSheet(){},confirmAction:async(title,msg,label,money)=>{asks.push({title,msg,label,money});return true;}})};await fixture.open();
</script>`;
const server=createServer(async(req,res)=>{try{if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return;}const path=resolve(root,'public','.'+decodeURIComponent(req.url.split('?')[0]));if(!path.startsWith(resolve(root,'public')))throw Error('path');res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[extname(path)]||'application/octet-stream');res.end(await readFile(path));}catch{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true}),page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2}),errors=[];
page.on('pageerror',e=>errors.push(String(e)));
const noSideways=async()=>assert.ok(await page.locator('.qy-sheet').evaluate(e=>e.scrollWidth-e.clientWidth)<=1,'No sideways scroll at 390px');
const settle=()=>page.waitForFunction(()=>!document.querySelector('.qy-sheet')?.getAttribute('aria-busy')||document.querySelector('.qy-sheet').getAttribute('aria-busy')==='false');
try{
  await page.goto(`http://127.0.0.1:${server.address().port}`);await page.waitForSelector('.qy-sheet[open]');
  const card=page.locator('[data-qk="st:q2"]');
  await card.locator('[data-qy="more"][data-part="fund"]').click();
  const reserve=card.getByLabel('Vốn giữ lại khi thu két',{exact:true});
  await reserve.waitFor({timeout:5000});
  assert.equal(await reserve.inputValue(),'0');
  await reserve.fill('60');
  assert.equal(await page.evaluate(()=>window.calls.length),0,'Editing does not submit or transfer money');
  await card.locator('[data-qy="reservesave"]').click();
  await page.waitForFunction(()=>window.calls.length===1);await settle();
  assert.deepEqual(await page.evaluate(()=>window.calls[0]),['jr_quay_reserve',{stall:'q2',amount:60}]);
  assert.deepEqual(await page.evaluate(()=>{const s=fixture.api.state.journey.quay.stalls[1];return [s.fund,s.till,fixture.api.state.journey.wallet];}),[0,100,5000]);
  for(const invalid of ['', '-1','1.5','100000001']){
    await reserve.fill(invalid);await card.locator('[data-qy="reservesave"]').click();
    assert.equal(await page.evaluate(()=>window.calls.length),1,'Invalid amount stays local');
  }
  await reserve.fill('75');
  await page.evaluate(()=>fixture.api.dispatchEvent(new Event('state')));
  assert.equal(await reserve.inputValue(),'75','A sync render preserves the unsaved draft');
  await noSideways();await page.screenshot({path:resolve(out,'reserve-390.png')});
  await page.locator('[data-qy="manage"]').click();
  const bulk=page.locator('[data-qk="grp:tea"] [data-qy="bulkTill"]');
  assert.match(await bulk.textContent(),/50 xu/,'Preview uses saved reserve, not the draft');
  await bulk.click();await page.waitForFunction(()=>window.calls.length===3);await settle();
  assert.equal(await page.evaluate(()=>fixture.api.state.journey.wallet),5055);
  assert.match(await page.locator('.qy-sheet').textContent(),/55 xu vào ví/);
  assert.match(await page.locator('.qy-sheet').textContent(),/60 xu vào vốn/);
  await noSideways();
  assert.deepEqual(errors,[]);
  console.log('Quay reserve: explicit save, validation, sync draft, bulk preview and server receipts passed.');
}finally{await browser.close();await new Promise(r=>server.close(r));}
