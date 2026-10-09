// "Tất cả" (feedback #290) in the real quay dialog at phone width: 🛠️ Lắp tất cả sends jr_quay_buy once per item
// (cheapest first, only what the wallet pays) after ONE confirm, stops at the server's refusal and says how many were
// done; 👥 Thuê tất cả fills the free places with jr_quay_hire. Synthetic API boundary, real modules and styles.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdir} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
import {chromium} from 'file:///C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs';

const root=resolve(import.meta.dirname,'..'),out=resolve(root,'output/playwright/quay-select-all');
const items=[['camera','📹','Camera quầy',140],['hygiene','🧼','Tủ vệ sinh',280],['alarm','🔔','Chuông chống trộm',300],['bang','🪧','Bảng hiệu đèn',600]]
  .map(([id,emoji,name,sap])=>({id,emoji,name,line:'',price:{sap,xe:sap/2,kiot:sap*3}}));
const st={id:'q1',name:'Quầy kiểm thử',trade:'tea',place:'sap',fund:100,till:0,staff:[],hist:[],items:[],look:{c:0,d:[],t:0},closed:false,due:0,left:5,
  cands:[{id:'tea-1',name:'An',bio:'Nhanh nhẹn',ask:20,g:false},{id:'tea-2',name:'Bình',bio:'Cẩn thận',ask:22,g:true},{id:'tea-3',name:'Chi',bio:'Vui vẻ',ask:18,g:false}]};
const data={state:{journey:{story:true,wallet:500,bank:{open:true,balance:300},quay:{stalls:[st]}}},content:{journey:{quay:{places:[{id:'sap',name:'Sạp chợ',slots:2,emoji:'🏪'}],trades:{tea:{name:'Trà sữa',emoji:'🧋'}},items,orders:[{id:'vua',name:'Vừa'}],weather:{},pace:{}}}}};
const html=`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/app.css"><script type="module">
import {openQuay} from '/js/v4/quay.js';
const api=Object.assign(new EventTarget(),${JSON.stringify(data)});window.calls=[];window.asks=[];window.refuseAt=99;
api.refresh=async()=>{};api.json=async()=>({});
api.command=async(action,p)=>{calls.push([action,p]);await new Promise(r=>setTimeout(r,5));if(calls.length>=refuseAt){const e=new Error('Cần 300 xu.');e.data={code:'no_money'};throw e;}
  const s=api.state.journey.quay.stalls[0];if(action==='jr_quay_buy')s.items.push(p.item);if(action==='jr_quay_hire'){s.staff.push({id:p.cand,name:p.cand,wage:p.wage,ask:p.wage,mo:60});s.cands=s.cands.filter(c=>c.id!==p.cand);}
  api.dispatchEvent(new Event('state'));return {message:'OK'};};
window.fixture={api,open:()=>openQuay({api,closeSheet(){},confirmAction:async(title,msg,label,money)=>{asks.push({title,msg,label,money});return true;}})};await fixture.open();
</script>`;
const server=createServer(async(req,res)=>{try{if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return;}const path=resolve(root,'public','.'+decodeURIComponent(req.url.split('?')[0]));if(!path.startsWith(resolve(root,'public')))throw Error('path');res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[extname(path)]||'application/octet-stream');res.end(await readFile(path));}catch{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true}),page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2}),errors=[];
page.on('pageerror',e=>errors.push(String(e)));
try{
  await page.goto(`http://127.0.0.1:${server.address().port}`);await page.waitForSelector('.qy-sheet[open]');
  await page.locator('[data-qy="more"][data-part="up"]').click();
  const all=page.locator('[data-qy="buyAll"]');
  // 800 xu (wallet 500 + account 300): 140 + 280 + 300 fit, the 600 sign does not.
  assert.match(await all.textContent(),/Lắp 3\/4 món · 720 xu/);
  assert.ok(await page.locator('.qy-sheet').evaluate(e=>e.scrollWidth-e.clientWidth)<=1,'No sideways scroll at 390px');
  await page.screenshot({path:resolve(out,'up-390.png')});
  await page.evaluate(()=>{window.refuseAt=3;});   // the money moved meanwhile: the server refuses the third
  await all.click();await page.waitForFunction(()=>window.calls.length>=3&&!document.querySelector('.qy-sheet [data-qy="more"]')?.disabled);
  const asks=await page.evaluate(()=>window.asks);
  assert.equal(asks.length,1,'One confirm for the whole run');assert.equal(asks[0].money.cost,720);assert.match(asks[0].msg,/3\/4 món/);
  const calls=await page.evaluate(()=>window.calls);
  assert.deepEqual(calls.map(c=>[c[0],c[1].item]),[['jr_quay_buy','camera'],['jr_quay_buy','hygiene'],['jr_quay_buy','alarm']],'Same per-item command, cheapest first, stops at the refusal');
  assert.ok(calls.every(c=>c[1].confirm===true&&c[1].stall==='q1'));
  const flash=await page.locator('.qy-sheet').textContent();assert.match(flash,/Đã lắp 2\/4 món\. Cần 300 xu\./);
  // Hire all: two free places, the first two people at their asking wage.
  await page.evaluate(()=>{window.calls.length=0;window.asks.length=0;window.refuseAt=99;});
  await page.locator('[data-qy="more"][data-part="staff"]').click();
  const hire=page.locator('[data-qy="hireAll"]');assert.match(await hire.textContent(),/Thuê tất cả · 2 người/);
  await page.screenshot({path:resolve(out,'staff-390.png')});
  assert.ok(await page.locator('.qy-sheet').evaluate(e=>e.scrollWidth-e.clientWidth)<=1);
  await hire.click();await page.waitForFunction(()=>window.calls.length>=2);await page.waitForTimeout(50);
  assert.deepEqual(await page.evaluate(()=>window.calls.map(c=>[c[0],c[1].cand,c[1].wage])),[['jr_quay_hire','tea-1',20],['jr_quay_hire','tea-2',22]]);
  assert.match(await page.locator('.qy-sheet').textContent(),/2 người đã nhận việc/);
  assert.equal(await page.locator('[data-qy="hireAll"]').count(),0,'Full: no more Thuê tất cả');
  assert.deepEqual(errors,[]);
  console.log('Quay select-all (390px): one confirm, cheapest-first per-item buys that stop at a refusal, hire fills free places passed.');
}finally{await browser.close();server.close();}
