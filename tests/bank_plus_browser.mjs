// 🏦 22/10 (game/bank_plus.py) in the real bank dialog at phone width (390 px): 🐷 the savings tier card and its upgrade,
// 💳 Xét lại hạn mức, 📦 Vay nhập hàng with a loan to repay, and v4/stock-cover.js's payment list for a short restock.
// The public state comes on stdin from tests/test_bank_plus.py (a real save); synthetic API boundary, real modules and styles.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdir} from 'node:fs/promises';
import {readFileSync} from 'node:fs';
import {resolve,extname} from 'node:path';
import {chromium} from 'file:///C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs';
import {coverOptions} from '../public/js/v4/stock-cover.js';

const root=resolve(import.meta.dirname,'..'),out=resolve(root,'output/playwright/bank-plus');
const state=JSON.parse(readFileSync(0,'utf8'));
const plus=state.journey.bank.plus;

// The payment list of a short restock: ví (not enough), thẻ, vay nhập hàng, each with the server's reason.
{
  const o=coverOptions(state,100,{});
  assert.deepEqual(o.map(x=>x.id),['wallet','card','loan']);
  assert.equal(o[2].ok,plus.cover.loan.ok&&plus.cover.loan.room>=100);
  assert.equal(o[1].ok,plus.cover.card.ok&&plus.cover.card.available>=100);
  assert.match(o[2].text,/sau 7 ngày trả/);
  assert.equal(coverOptions({...state,journey:{...state.journey,story:false}},100),null,'not the story: nothing to offer');
  assert.equal(coverOptions({...state,journey:{...state.journey,places:{x:{employed:true}}}},100,{career:'x'}),null,'a job: the fund is the employer\'s');
  assert.equal(coverOptions(state,0),null);
}

const html=`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/app.css"><script type="module">
import {openBank} from '/js/v4/bank.js';
const api=Object.assign(new EventTarget(),{state:${JSON.stringify(state)},csrf:'x'});window.calls=[];window.asks=[];
api.json=async()=>({});api.command=async(action,p)=>{if(action!=='jr_bk_read')calls.push([action,JSON.parse(JSON.stringify(p))]);return {message:'OK'};};
window.fixture={api,open:tab=>openBank({api,ui:{},closeSheet(){},confirmAction:async(title,msg,label,money)=>{asks.push({title,msg,label,money});return true;}},tab)};
</script>`;
const server=createServer(async(req,res)=>{try{if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return;}const path=resolve(root,'public','.'+decodeURIComponent(req.url.split('?')[0]));if(!path.startsWith(resolve(root,'public')))throw Error('path');res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[extname(path)]||'application/octet-stream');res.end(await readFile(path));}catch{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true}),page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2}),errors=[];
page.on('pageerror',e=>errors.push(String(e)));
const noSideways=async()=>assert.ok(await page.locator('.bk-sheet').evaluate(e=>e.scrollWidth-e.clientWidth)<=1,'No sideways scroll at 390px');
try{
  await page.goto(`http://127.0.0.1:${server.address().port}`);
  await page.evaluate(()=>fixture.open('save'));await page.waitForSelector('.bk-sheet[open] .bk-tiers');
  const tiers=await page.locator('.bk-tiers').textContent();
  assert.match(tiers,new RegExp(`Hạng ${plus.name}`));assert.match(tiers,/còn gửi thêm được/);assert.match(tiers,/Kim cương · tới 10\.000\.000\.000 xu/);assert.match(tiers,/lãi thêm 1,5%/);assert.match(tiers,/lãi thêm 5%/);   // 💎👑 + the interest bonus
  await noSideways();await page.screenshot({path:resolve(out,'save-390.png'),fullPage:true});
  const up=plus.tiers.find(t=>!t.own);
  if(up){
    await page.locator(`[data-bk="tier"][data-n="${up.n}"]`).click();await page.waitForFunction(()=>window.calls.length>=1);
    assert.deepEqual((await page.evaluate(()=>window.calls))[0],['jr_bk_tier',{tier:up.n,src:'acc',confirm:true}]);
    assert.equal((await page.evaluate(()=>window.asks))[0].money.cost,up.cost);
  }
  await page.locator('[data-bk="tab"][data-tab="loan"]').click();await page.waitForSelector('.bk-card h3:text("Vay nhập hàng")');
  const loan=await page.locator('.bk-card:has(h3:text("Vay nhập hàng"))').textContent();
  assert.match(loan,/Trả một lần sau 7 ngày/);
  const ln=plus.stock_loans[0];
  if(ln){
    assert.match(loan,new RegExp(ln.label));
    await page.locator(`[data-bk="stockPay"][data-id="${ln.id}"]`).click();
    await page.waitForFunction(n=>window.calls.length>n,up?1:0);
    assert.deepEqual((await page.evaluate(()=>window.calls)).at(-1),['jr_bk_stock_pay',{id:ln.id,src:'acc'}]);
  }
  await noSideways();await page.screenshot({path:resolve(out,'loan-390.png'),fullPage:true});
  if(state.journey.bank.card){
    await page.locator('[data-bk="tab"][data-tab="card"]').click();await page.waitForSelector('[data-bk="cardReview"]');
    await noSideways();await page.screenshot({path:resolve(out,'card-390.png'),fullPage:true});
  }
  assert.deepEqual(errors,[]);
}finally{await browser.close();server.close();}
console.log('Bank tiers, card review and vay nhập hàng (390px) passed.');
