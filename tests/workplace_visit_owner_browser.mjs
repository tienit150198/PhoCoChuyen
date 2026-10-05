/** Optional local layout regression: PLAYWRIGHT_MODULE may point to an installed Playwright ESM entry. */
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=fileURLToPath(new URL('../public/',import.meta.url));
const output=fileURLToPath(new URL('../output/playwright/visit-owner/',import.meta.url));
const fixture=`<!doctype html><html data-layout="desktop" data-theme="kem"><meta charset="utf-8"><link rel="stylesheet" href="/css/app.css"><link rel="stylesheet" href="/css/workplace-visit.css" data-lazy-css="/css/workplace-visit.css"><body>
<div id="app"><div class="brand">Nghề</div><header class="topbar">Chỗ làm của tôi</header><aside class="rail"></aside><main class="stage"></main><div id="side" class="side"><section id="taskHUD" class="task-hud"><article class="note-card calm-card task-card"><button class="calm-what"><span class="npc-mini">🙂</span><b>Kiểm tra yêu cầu của khách</b></button><button class="btn primary" id="continue">Làm tiếp</button></article></section><nav class="dock"><button class="dock-btn">Làm việc</button></nav></div><footer class="tiny-footer">Đã lưu</footer></div>
<dialog id="sheet" class="sheet cozy-job"><div id="sheetContent"><header class="sheet-head"><h2>Công việc</h2></header><div class="sheet-body"><p>Thực hiện công việc đang chờ.</p><button id="career-continue" class="btn primary">Làm tiếp</button></div><footer class="sheet-foot"><button class="btn primary" id="career-finish">Hoàn thành</button></footer></div></dialog>
<script type="module">
import {workVisitsBoot,workVisitsOwnerFocus} from '/js/v4/workplace-visit.js';
const api=new EventTarget();Object.assign(api,{account:{username:'fixture'},state:{current:'tea'},json:async url=>url.includes('/orders')?{incoming:[],outgoing:[]}:{places:[{id:'career:fixture:tea',kind:'career',target:'tea',name:'Tiệm trà'}]},refresh:async()=>{}});
window.fixtureEnv={api,live:()=>null};window.focusVisits=focus=>workVisitsOwnerFocus(window.fixtureEnv,focus);window.clicks=0;document.addEventListener('click',e=>{if(e.target.id==='continue'||e.target.id==='career-continue'||e.target.id==='career-finish')window.clicks++;});workVisitsBoot(window.fixtureEnv);
</script></body></html>`;
const server=createServer(async(req,res)=>{try{if(req.url==='/'){res.setHeader('Content-Type','text/html; charset=utf-8');res.end(fixture);return;}const file=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);if(!file.startsWith(root))throw Error('invalid path');res.setHeader('Content-Type',file.endsWith('.css')?'text/css':file.endsWith('.js')?'text/javascript':'application/octet-stream');res.end(await readFile(file));}catch{res.writeHead(404);res.end();}});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));await mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true});
try{
 for(const [layout,width,height,orientation] of [['desktop',1280,800,'landscape'],['phone',390,844,'portrait'],['phone',320,568,'portrait'],['phone',844,390,'landscape'],['tablet',820,1180,'portrait'],['tablet',1024,768,'landscape']]){
  const page=await browser.newPage({viewport:{width,height}}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(`http://127.0.0.1:${server.address().port}/`);
  await page.evaluate(({layout,orientation})=>{Object.assign(document.documentElement.dataset,{layout,orientation});},{layout,orientation});
  await page.locator('#wv-owner-toggle').waitFor();
  if(layout!=='desktop'){
   assert.equal(await page.locator('#wv-owner-toggle').evaluate(e=>{const r=e.getBoundingClientRect(),hud=document.getElementById('taskHUD').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.bottom<=innerHeight&&r.top>=hud.bottom&&Math.abs(r.width-hud.width)<2&&r.height>=44;}),true,'collapsed presence has its own fully readable row below the task scroller');
   assert.equal(await page.locator('#taskHUD>.task-card').count(),1,'task remains a direct child owned by app rendering');
   if(layout==='phone')assert.equal(await page.locator('#taskHUD>.task-card').evaluate(e=>Math.abs(e.getBoundingClientRect().width-e.parentElement.getBoundingClientRect().width)<2),true,'primary task retains full available width');
  }
  await page.screenshot({path:path.join(output,`${layout}-${orientation}-${width}-collapsed.png`)});
  const hit=async selector=>{const el=page.locator(selector);await el.scrollIntoViewIfNeeded();assert.equal(await el.evaluate(e=>{const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}),true,`${layout} ${orientation}: ${selector} has a clear hit target`);await el.click();};
  await hit('#continue');await page.locator('#wv-owner-toggle').click();await hit('#continue');
  assert.equal(await page.locator('.wv-owner').evaluate(e=>getComputedStyle(e).position),'relative');
  await page.screenshot({path:path.join(output,`${layout}-${orientation}.png`)});
  await page.evaluate(()=>document.getElementById('sheet').showModal());await hit('#career-continue');await hit('#career-finish');
  assert.equal(await page.locator('.wv-owner').evaluate(e=>e.parentElement.id),'sheet');
  assert.equal(await page.locator('.wv-owner-panel').evaluate(e=>getComputedStyle(e).position),'static');
  await page.screenshot({path:path.join(output,`${layout}-${orientation}-career.png`)});
  await page.evaluate(()=>document.getElementById('sheet').close());await hit('#continue');
  await page.evaluate(()=>{const hud=document.getElementById('taskHUD');hud.innerHTML= '<article class="note-card"><button id="continue" class="btn primary">Làm tiếp</button></article>';});await hit('#continue');
  await page.locator('#wv-owner-toggle').waitFor();assert.deepEqual(errors,[]);assert.equal(await page.evaluate(()=>window.clicks),6);
  // Long main task plus two additional task cards: presence is outside their scroller.
  await page.locator('#wv-owner-toggle').click();
  await page.evaluate(()=>{document.getElementById('taskHUD').innerHTML='<article class="note-card calm-card task-card"><button class="calm-what"><span class="npc-mini">🙂</span><b>Kiểm tra đầy đủ thông tin khách đã yêu cầu và xác nhận lại loại trà cùng lượng đường, lượng đá trước khi bắt đầu phục vụ</b></button><button class="btn primary" id="continue">Làm tiếp</button></article><article class="note-card"><h3>Khách đang chờ</h3><button id="second-task" class="btn">Phục vụ khách thứ hai</button></article><article class="note-card"><h3>Việc tiếp theo</h3><button id="third-task" class="btn">Xem việc thứ ba</button></article>';});
  if(layout==='phone'||layout==='tablet'&&orientation==='portrait')assert.equal(await page.locator('#taskHUD>.task-card').evaluate(e=>Math.abs(e.getBoundingClientRect().width-e.parentElement.getBoundingClientRect().width)<2),true,'additional tasks never shrink the primary card');
  await hit('#continue');await hit('#second-task');await hit('#third-task');await hit('#continue');
  if(layout!=='desktop')assert.equal(await page.locator('#wv-owner-toggle').evaluate(e=>{const r=e.getBoundingClientRect(),hud=document.getElementById('taskHUD').getBoundingClientRect();return r.top>=hud.bottom&&r.left>=0&&r.right<=innerWidth;}),true,'task swipes leave presence below the scroller');
  await page.locator('#wv-owner-toggle').click();await hit('#continue');
  if(layout!=='desktop')assert.equal(await page.locator('.wv-owner-panel').evaluate(e=>e.clientHeight<=Math.min(innerHeight*.24,220)+1),true,'expanded details stay bounded');
  await page.screenshot({path:path.join(output,`${layout}-${orientation}-${width}-multiple-tasks.png`)});
  assert.deepEqual(errors,[]);
  console.log(`PASS ${layout} ${orientation} ${width}x${height}: full-width task, readable presence row, expanded owner, career, rerender and multiple long tasks`);await page.close();
 }
}finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
