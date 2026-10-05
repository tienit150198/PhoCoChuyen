import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import {resolve, extname} from 'node:path';
import {chromium} from 'file:///C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs';

// Local synthetic API boundary; the browser runs the real quay modules and styles.
const root=resolve(import.meta.dirname,'..'),out=resolve(root,'output/playwright/quay-dialog-pass2');
const dish={id:'tea',name:'Trà sữa',emoji:'🧋',base:10,cost:4,band:[1,1000]};
const st={id:'q1',name:'Quầy kiểm thử',trade:'tea',place:'xe',fund:1000,till:300,staff:[{id:'s1',name:'Lan',wage:10}],hist:[],items:[],look:{c:0,d:[],t:0},menu:{on:['tea'],p:{tea:10}},business:{status:'running',stock_total:100,sold:20,revenue:200,net:100,server_now:1000,stock:[{id:'tea',qty:100,cost:4}],expenses:{goods:80},recent:Array.from({length:5},(_,i)=>({id:i+1,at:990+i,dish:'tea',qty:1,total:10,channel:'counter'})),protection:{label:'Bảo vệ',options:[]}}};
const data={state:{journey:{story:true,wallet:1000,quay:{stalls:[st]}}},content:{journey:{quay:{places:[{id:'xe',name:'Xe',slots:2}],trades:{tea:{name:'Trà sữa',emoji:'🧋'}},menus:{tea:[dish]},colors:[['red','#d9534f','Đỏ']],tables:{xe:[0,0]},decor:[],items:[],weather:{},pace:{}}}}};
const html=`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/app.css"><script type="module">
import {openQuay} from '/js/v4/quay.js';
const api=Object.assign(new EventTarget(),${JSON.stringify(data)});api.refresh=async()=>{window.refreshes++;api.state.journey.wallet++;api.dispatchEvent(new Event('state'));};api.command=async()=>({message:'OK'});api.json=async()=>({});window.refreshes=0;
window.fixture={api,open:()=>openQuay({api,closeSheet(){},confirmAction:async()=>false})};await fixture.open();
</script>`;
const server=createServer(async(req,res)=>{try{if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return;}const path=resolve(root,'public','.'+decodeURIComponent(req.url.split('?')[0]));if(!path.startsWith(resolve(root,'public')))throw Error('path');res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[extname(path)]||'application/octet-stream');res.end(await readFile(path));}catch{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true}),page=await browser.newPage({viewport:{width:390,height:780},isMobile:true,hasTouch:true,deviceScaleFactor:2}),failures=[],errors=[];
await page.addInitScript(()=>{const originalSet=window.setTimeout,originalClear=window.clearTimeout;window.pollTimers=new Set();window.setTimeout=(fn,ms,...args)=>{let id=originalSet(()=>{pollTimers.delete(id);fn(...args);},ms);if(ms===5000)pollTimers.add(id);return id;};window.clearTimeout=id=>{pollTimers.delete(id);originalClear(id);};window.sceneDraws=0;const draw=CanvasRenderingContext2D.prototype.drawImage;CanvasRenderingContext2D.prototype.drawImage=function(...args){if(this.canvas.matches?.('[data-cv]'))sceneDraws++;return draw.apply(this,args);};});
page.on('pageerror',e=>errors.push(String(e)));
async function check(name,fn){try{await fn();console.log('PASS '+name);}catch(e){failures.push({name,error:e.message});console.log('FAIL '+name+': '+e.message);}}
const refresh=()=>page.evaluate(()=>fixture.api.refresh());
try{
 await page.goto(`http://127.0.0.1:${server.address().port}`);await page.waitForSelector('.qy-sheet[open]');
 await page.locator('[data-qy="visit"]').first().click();
 await check('Revenue details remain open through server refresh and nearby info click',async()=>{
  await page.locator('.qy-ledger summary').click();assert.equal(await page.locator('.qy-ledger').evaluate(e=>e.open),true);
  await refresh();assert.equal(await page.locator('.qy-ledger').evaluate(e=>e.open),true);
  await page.locator('.qy-protection summary').click();await refresh();assert.equal(await page.locator('.qy-protection').evaluate(e=>e.open),true);assert.equal(await page.locator('.qy-ledger').evaluate(e=>e.open),true);
  await page.locator('[data-qy="pause"]').click();assert.equal(await page.locator('.qy-ledger').evaluate(e=>e.open),true,'Command busy/result renders preserve disclosure');
 });
 await check('Click inside dialog padding does not dismiss',async()=>{
  const b=await page.locator('.qy-sheet').boundingBox();await page.mouse.click(b.x+2,b.y+b.height/2);assert.equal(await page.locator('.qy-sheet').evaluate(e=>e.open),true);
 });
 await check('Different disclosures keep identity when another disappears',async()=>{
  await page.evaluate(()=>{fixture.api.state.journey.quay.stalls[0].staff_life={employees:[{name:'Lan',wage:10,morale:80}],recent:[{name:'Lan',text:'Đã nhận lương'}]};return fixture.api.refresh();});
  await page.locator('.staff-life-card details').nth(1).locator('summary').click();
  await page.evaluate(()=>{fixture.api.state.journey.quay.stalls[0].staff_life.employees=[];return fixture.api.refresh();});
  assert.equal(await page.locator('.staff-life-card details').evaluate(e=>e.open),true);
 });
 await page.evaluate(()=>fixture.open());
 await check('Input value, caret and scroll survive live updates',async()=>{
  await page.locator('[data-qy="more"][data-part="menu"]').click();const input=page.locator('[name="qy-search"]');await input.fill('Trà');await input.evaluate(e=>e.setSelectionRange(1,2));
  const before=await page.locator('.qy-sheet').evaluate(e=>e.scrollTop);await refresh();assert.equal(await input.inputValue(),'Trà');assert.deepEqual(await input.evaluate(e=>[e===document.activeElement,e.selectionStart,e.selectionEnd]),[true,1,2]);assert.ok(Math.abs(await page.locator('.qy-sheet').evaluate(e=>e.scrollTop)-before)<3);
 });
 await check('Drag beginning inside and ending outside does not dismiss',async()=>{
  await page.setViewportSize({width:900,height:850});const b=await page.locator('.qy-sheet').boundingBox();await page.mouse.move(b.x+20,b.y+120);await page.mouse.down();await page.mouse.move(b.x-20,b.y+120);await page.mouse.up();assert.equal(await page.locator('.qy-sheet').evaluate(e=>e.open),true);
 });
 await check('A real backdrop click dismisses',async()=>{await page.mouse.click(1,1);assert.equal(await page.locator('.qy-sheet').evaluate(e=>e.open),false);});
 await page.waitForTimeout(50);await page.evaluate(()=>fixture.open());await page.locator('[data-qy="visit"]').first().click();
 for(const width of [320,390,430]){await page.setViewportSize({width,height:780});await refresh();await check('No overflow at '+width,async()=>assert.ok(await page.locator('.qy-sheet').evaluate(e=>e.scrollWidth-e.clientWidth)<=1));await page.waitForTimeout(500);await page.screenshot({path:resolve(out,`visit-${width}.png`)});}
 await check('Unchanged scene is cached across 100 state refreshes',async()=>{const before=await page.evaluate(()=>sceneDraws);await page.evaluate(async()=>{for(let i=0;i<100;i++)await fixture.api.refresh();});assert.equal(await page.evaluate(()=>sceneDraws),before);});
 await check('Fresh completed receipts expire, closed shop has no purchase stage, real queue stays bounded',async()=>{
  assert.equal(await page.locator('.qy-activity-person.completed').count(),5);
  await page.evaluate(()=>{fixture.api.state.journey.quay.stalls[0].business.server_now=1200;return fixture.api.refresh();});assert.equal(await page.locator('.qy-activity-person.completed').count(),0);
  await page.evaluate(()=>{const st=fixture.api.state.journey.quay.stalls[0];st.business.server_now=1000;st.business.status='paused';return fixture.api.refresh();});assert.equal(await page.locator('.qy-activity-person').count(),0);
  await page.evaluate(()=>{const st=fixture.api.state.journey.quay.stalls[0];st.run={crowd:Array.from({length:12},(_,i)=>({ticket:i,look:i,name:'Khách '+(i+1)}))};st.business.status='out_of_stock';return fixture.api.refresh();});assert.equal(await page.locator('.qy-activity-person.waiting').count(),8);assert.equal(await page.locator('.qy-activity-person.completed').count(),0);
  await page.evaluate(()=>{fixture.api.state.journey.quay.stalls[0].business.status='running';return fixture.api.refresh();});
  for(const width of [320,390,430]){await page.setViewportSize({width,height:780});await refresh();await page.waitForTimeout(500);await page.screenshot({path:resolve(out,`crowd-${width}.png`)});assert.ok(await page.locator('.qy-sheet').evaluate(e=>e.scrollWidth-e.clientWidth)<=1);}
 });
 await check('Hidden/closed sheet cancels its polling; reopening adds exactly one timer',async()=>{
  // Workplace visitors also own a poller; only the quay dialog timer is in this scope.
  const before=await page.evaluate(()=>pollTimers.size);assert.ok(before>=1);
  await page.evaluate(()=>{Object.defineProperty(document,'visibilityState',{configurable:true,get:()=> 'hidden'});document.dispatchEvent(new Event('visibilitychange'));});assert.equal(await page.evaluate(()=>pollTimers.size),before-1,'Hidden cancels quay timer');
  await page.evaluate(()=>{Object.defineProperty(document,'visibilityState',{configurable:true,get:()=> 'visible'});document.dispatchEvent(new Event('visibilitychange'));});assert.equal(await page.evaluate(()=>pollTimers.size),before);
  await page.evaluate(()=>document.querySelector('.qy-sheet').close());await page.waitForTimeout(50);assert.equal(await page.evaluate(()=>pollTimers.size),before-1,'Closed cancels quay timer');
  await page.evaluate(()=>fixture.open());await page.evaluate(()=>fixture.open());assert.equal(await page.evaluate(()=>pollTimers.size),before);
 });
 await check('No browser errors',async()=>assert.deepEqual(errors,[]));
 await writeFile(resolve(out,'report.json'),JSON.stringify({failures,errors},null,2));assert.deepEqual(failures,[]);
}finally{await browser.close();server.close();}
