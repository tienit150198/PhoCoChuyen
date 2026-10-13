// Real warehouse renderers and event handlers, disposable localhost fixture API.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdir} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {resolve,extname} from 'node:path';
import {chromium} from 'file:///C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs';

const root=resolve(import.meta.dirname,'..'),out=resolve(root,'output/playwright/warehouse-convenience');
const fixtures=JSON.parse(execFileSync('python',['-c',`
import json
from tests.helpers import Journey
from game.content import public_content
from game.engine import public_state
from game import convenience
out={'content':public_content(),'careers':{}}
for cid in ('mother_baby','pharmacy','restaurant'):
 j=Journey(cid);c=j.c;c['money']=1000000;c['ops']['finance']['opening_balance']=1000000
 c['upgrades']=[convenience.item_id(cid,'count',n) for n in range(1,11)]
 if cid in convenience.LEGACY:
  c['upgrades'] += [convenience.item_id(cid,'logistics',n) for n in range(1,11)]
  j.act('order_stock',item='bunny' if cid=='mother_baby' else 'P-01-A',qty=28)
 else:j.act('inv_order',item='noodle',qty=28,supplier='partner',confirm=True)
 j.c['turn']+=20
 out['careers'][cid]=public_state(j.state)['careers'][cid]
print(json.dumps(out))
`],{cwd:root,encoding:'utf8',maxBuffer:20*1024*1024}));
const app=await readFile(resolve(root,'public/js/app.js'),'utf8');
const extract=(start,end)=>app.slice(app.indexOf(start),app.indexOf(end,app.indexOf(start)));
const legacy=extract('function stockDesk(cap){','/** A "Gộp" box')+extract('const whQty=','/** The order button');
const html=`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/app.css"><link rel="stylesheet" href="/css/guide.css"><dialog open id="sheet" style="position:relative;width:100%;max-width:100%;padding:12px;border:0"></dialog><script type="module">
import {inventoryView,stockBoot,stockBatchButton,v4Action,v4Input} from '/js/v4/views.js';
import {qtyBox} from '/js/qty-input.js';import {icon,escapeHTML as esc} from '/js/icons.js';
const fixtures=${JSON.stringify(fixtures)},api={state:{current:'mother_baby',careers:fixtures.careers,settings:{sound:false}},content:fixtures.content};
let ui={},calls=[],mode='mother_baby';const fmt=n=>Number(n||0).toLocaleString('vi-VN'),career=()=>mode,room=()=>api.state.careers[mode];
const env=()=>({api,ui,renderSheet,cmd:async(a,p)=>{calls.push([a,p]);if(a==='receive_stock')room().shipments=room().shipments.filter(s=>s.id!==p.shipment);if(a==='inv_receive')room().inventory.orders=room().inventory.orders.filter(s=>s.id!==p.order);return true;}});
const product=id=>[...api.content.products,...api.content.lots].find(p=>p.id===id),careData=()=>room().data?.care,
itemArt=()=>'<span aria-hidden="true">📦</span>',pill=(s)=>'<span>'+s+'</span>',keepRow=()=>'',phDay=()=>'',leftWord=()=>'',sameDay=()=>false,commandButton=()=>'',priceWord=()=>'',SHIP_CAP=8,MERGE_CAP=12,stockVans=()=>0;
${legacy}
function renderSheet(){document.getElementById('sheet').innerHTML=mode==='restaurant'?inventoryView(env()):stockDesk(room().warehouse?.capacity??12);}
document.addEventListener('click',e=>{const b=e.target.closest('[data-action]');if(b&&!b.disabled)v4Action(b.dataset.action,b.dataset,b,env());});
document.addEventListener('input',e=>v4Input(e.target,env()));
document.addEventListener('submit',async e=>{e.preventDefault();const f=e.target;if(f.dataset.receive){await env().cmd('receive_stock',{shipment:f.dataset.receive,count:Number(f.querySelector('input').value)});renderSheet();}});
window.fixture={open(cid,step=1){mode=cid;api.state.current=cid;room().warehouse.count_step=step;ui={invTab:'orders'};calls=[];renderSheet();},calls:()=>calls,ui:()=>ui,redraw:()=>renderSheet()};fixture.open('mother_baby');
</script>`;
const server=createServer(async(req,res)=>{try{if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return;}const path=resolve(root,'public','.'+decodeURIComponent(req.url.split('?')[0]));if(!path.startsWith(resolve(root,'public')))throw Error('path');res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[extname(path)]||'application/octet-stream');res.end(await readFile(path));}catch{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true}),errors=[];
try{
 for(const width of [390,1280]){
  const page=await browser.newPage({viewport:{width,height:900},hasTouch:true});page.on('pageerror',e=>errors.push(String(e)));
  await page.goto('http://127.0.0.1:'+server.address().port);await page.waitForSelector('.inv-good');
  for(const cid of ['mother_baby','pharmacy','restaurant']){
   await page.evaluate(cid=>fixture.open(cid,1),cid);
   const input=page.locator('[data-v4-count]').first(),crate=page.locator('.inv-crate').first();
   await crate.dispatchEvent('pointerdown',{button:0,clientX:10,clientY:10,pointerType:'touch'});
   await page.evaluate(()=>document.getElementById('sheet').close());await page.waitForTimeout(480);
   assert.equal(await input.inputValue(),'','Closed dialog stops a pending hold');
   await page.evaluate(()=>document.getElementById('sheet').show());
   const total=await crate.locator('.inv-good').count();assert.ok(total>20);
   await crate.locator('.inv-good').first().click();assert.equal(await input.inputValue(),'1');
   await crate.locator('.inv-good').first().click();assert.equal(await input.inputValue(),'0');
   if(cid==='restaurant'){await page.locator('[data-action="v4TallyTray"]').first().click();assert.equal(await input.inputValue(),'10','Free tray still counts ten');}
   await page.evaluate(cid=>fixture.open(cid,1),cid);
   // Existing free tap and 10-unit tray remain available; cancelled touch never counts.
   await crate.dispatchEvent('pointerdown',{button:0,clientX:10,clientY:10,pointerType:'touch'});
   await crate.dispatchEvent('pointercancel',{pointerType:'touch'});await page.waitForTimeout(350);
   assert.equal(await input.inputValue(),'');
   // A release after a hold stops repetition and suppresses the synthetic click.
   await crate.dispatchEvent('pointerdown',{button:0,clientX:10,clientY:10,pointerType:'touch'});
   await page.waitForTimeout(370);await crate.dispatchEvent('pointerup',{pointerType:'touch'});
   const count=Number(await input.inputValue());assert.ok(count>=1&&count<10,'One free unit per tick');
   await page.waitForTimeout(330);assert.equal(Number(await input.inputValue()),count);
   assert.equal((await page.evaluate(()=>fixture.calls())).length,0,'Holding never receives');
   await page.waitForTimeout(300);
   await input.fill('9');await page.evaluate(()=>fixture.redraw());assert.equal(await input.inputValue(),'9','Typing survives render');
   // Repeated boots do not add listeners: exactly one paid 12-unit tick.
   await page.evaluate(cid=>fixture.open(cid,12),cid);await page.evaluate(()=>{fixture.redraw();fixture.redraw();});
   await crate.dispatchEvent('pointerdown',{button:0,clientX:10,clientY:10,pointerType:'touch'});
   await page.waitForTimeout(340);await crate.dispatchEvent('pointercancel',{pointerType:'touch'});
   assert.equal(Number(await input.inputValue()),12);
   await page.waitForTimeout(650);
   await page.locator('[data-action="v4TallyBatch"]').first().click();assert.equal(Number(await input.inputValue()),24);
   await page.locator('[data-action="v4TallyBatch"]').first().click();assert.equal(Number(await input.inputValue()),total,'Last batch clamps to actual goods');
   assert.equal((await page.evaluate(()=>fixture.calls())).length,0);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'No horizontal overflow');
   await page.screenshot({path:resolve(out,cid+'-'+width+'.png'),fullPage:false});
   if(cid==='restaurant')await page.locator('[data-action="v4Receive"]').last().click();else await page.locator('[data-receive] button[type="submit"]').click();
   const calls=await page.evaluate(()=>fixture.calls());assert.equal(calls.length,1);assert.equal(calls[0][1].count,total);
   assert.equal(await page.locator('.inv-good').count(),0);
  }
  await page.close();
 }
 assert.deepEqual(errors,[]);console.log('Warehouse browser: 390/1280px legacy MB, pharmacy and common inventory; touch cancel/release, typed counts, 12-unit holds, batch bounds and explicit single receipt passed.');
}finally{await browser.close();await new Promise(r=>server.close(r));}
