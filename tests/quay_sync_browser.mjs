import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
import {chromium} from 'file:///C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs';

// Real Quay UI and scheduled polling, with only the HTTP boundary replaced.
const root=resolve(import.meta.dirname,'..');
const dish={id:'tea',name:'Trà sữa',emoji:'🧋',base:10,cost:4,band:[1,1000]};
const st={id:'q1',name:'Quầy kiểm thử',trade:'tea',place:'xe',fund:1000,till:300,staff:[{id:'s1',name:'Lan',wage:10}],hist:[],items:[],look:{c:0,d:[],t:0},menu:{on:['tea'],p:{tea:10}},business:{status:'running',stock_total:100,sold:20,revenue:200,net:100,server_now:1000,stock:[{id:'tea',qty:100,cost:4}],expenses:{goods:80},recent:[],protection:{label:'Bảo vệ',options:[]}}};
const data={revision:1,csrf:'session-a',state:{journey:{story:true,life_day:1,wallet:1000,quay:{stalls:[st]}}},content:{journey:{quay:{places:[{id:'xe',name:'Xe',slots:2}],trades:{tea:{name:'Trà sữa',emoji:'🧋'}},menus:{tea:[dish]},colors:[['red','#d9534f','Đỏ']],tables:{xe:[0,0]},decor:[],items:[],weather:{},pace:{}}}}};
const html=`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/app.css"><script type="module">
import {openQuay} from '/js/v4/quay.js';
const api=Object.assign(new EventTarget(),${JSON.stringify(data)});
window.fixture={api,fullReads:0,stateEvents:0,commands:[],polls:0,fail:false,next:{revision:2,journey:structuredClone(api.state.journey)}};
fixture.next.journey.quay.stalls[0].till=777;
api.addEventListener('state',()=>fixture.stateEvents++);
api.json=async url=>{if(url!='/api/business/quay')return {};fixture.polls++;if(fixture.fail)throw Error('offline');return structuredClone(fixture.next);};
api.refresh=async()=>{fixture.fullReads++;api.revision=fixture.next.revision;api.state={journey:structuredClone(fixture.next.journey)};api.dispatchEvent(new Event('state'));};
api.command=async(action,payload)=>{fixture.commands.push({action,payload,revision:api.revision});return {message:'Đã thu két'};};
await openQuay({api,closeSheet(){},confirmAction:async()=>true});
</script>`;
const server=createServer(async(req,res)=>{try{if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return;}const path=resolve(root,'public','.'+decodeURIComponent(req.url.split('?')[0]));if(!path.startsWith(resolve(root,'public')))throw Error('path');res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[extname(path)]||'application/octet-stream');res.end(await readFile(path));}catch{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await chromium.launch({headless:true}),page=await browser.newPage({viewport:{width:390,height:780},isMobile:true,hasTouch:true}),errors=[];
page.on('pageerror',e=>errors.push(String(e)));
await page.addInitScript(()=>{
  const originalSet=setTimeout,originalClear=clearTimeout;let seq=0;const polls=new Map();
  window.setTimeout=(fn,ms,...args)=>ms===5000?(polls.set(--seq,()=>fn(...args)),seq):originalSet(fn,ms,...args);
  window.clearTimeout=id=>id<0?polls.delete(id):originalClear(id);
  window.tickQuay=async()=>{const next=polls.entries().next().value;if(!next)throw Error('No active Quay poll');polls.delete(next[0]);await next[1]();};
});
try{
 await page.goto(`http://127.0.0.1:${server.address().port}`);await page.waitForSelector('.qy-sheet[open]');
 await page.locator('[data-qy="more"][data-part="menu"]').click();const input=page.locator('[name="qy-search"]');await input.fill('Trà');await input.evaluate(e=>e.setSelectionRange(1,2));
 const before=await page.locator('.qy-sheet').evaluate(e=>e.scrollTop);
 await page.evaluate(()=>tickQuay());
 assert.equal(await page.locator('.qy-till strong').innerText(),'777 xu');
 assert.deepEqual(await input.evaluate(e=>[e.value,e===document.activeElement,e.selectionStart,e.selectionEnd]),['Trà',true,1,2]);
 assert.ok(Math.abs(await page.locator('.qy-sheet').evaluate(e=>e.scrollTop)-before)<3);
 assert.deepEqual(await page.evaluate(()=>[fixture.fullReads,fixture.stateEvents,fixture.api.revision,fixture.api.state.journey.quay.stalls[0].till]),[0,0,1,300]);
 console.log('PASS Quay poll updates confirmed till without full state event; draft, focus, caret and scroll survive');
 await page.evaluate(()=>{window.mutations=0;window.observer=new MutationObserver(rows=>mutations+=rows.length);observer.observe(document.querySelector('.qy-root'),{subtree:true,childList:true,characterData:true,attributes:true});});
 await page.evaluate(()=>tickQuay());assert.equal(await page.evaluate(()=>mutations),0);await page.evaluate(()=>observer.disconnect());
 console.log('PASS Identical confirmed projection does not redraw');
 await page.locator('[data-qy="till"]').click();await page.waitForFunction(()=>fixture.commands.length===1);
 assert.deepEqual(await page.evaluate(()=>[fixture.fullReads,fixture.stateEvents,fixture.commands[0].revision,fixture.commands[0].action]),[1,1,2,'jr_quay_till']);
 console.log('PASS Command synchronizes full state once before using latest projection revision');
 await page.evaluate(()=>{fixture.fail=true;return tickQuay();});assert.equal(await page.locator('.qy-till strong').innerText(),'777 xu');
 await page.evaluate(()=>{fixture.fail=false;fixture.next.revision=3;fixture.next.journey.quay.stalls[0].till=888;return tickQuay();});
 assert.equal(await page.locator('.qy-till strong').innerText(),'888 xu');assert.equal(await page.evaluate(()=>fixture.commands.length),1);
 console.log('PASS Failed poll keeps confirmed amounts and next poll recovers without replaying command');
 assert.deepEqual(errors,[]);
}finally{await browser.close();server.close();}
