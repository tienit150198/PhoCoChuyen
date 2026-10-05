import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {execFileSync} from 'node:child_process';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
import {chromium,webkit} from 'file:///C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs';

// Real fair module + CSS, controlled server reply; pixel samples verify the neck pierces the hoop.
const root=resolve(import.meta.dirname,'..'),baseline=process.argv.includes('--baseline');
const assets=resolve(root,baseline?'output/release-1715-fair-stability/stage/public':'public');
const out=resolve(root,'output/playwright/ring-geometry',baseline?'before':'after');await mkdir(out,{recursive:true});
const html=`<!doctype html><html data-theme="kem"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/app.css"><script type="module">
import {openFair} from '/js/v4/fair.js';
const api=Object.assign(new EventTarget(),{content:{},state:{settings:{sound:false,music:false},journey:{story:true},fair:{show:true,open:true,now:Date.now()/1000,closes:Date.now()/1000+86400,wallet:100,today_xu:{ring:0},money:{total:0},earn:{ring:{nocap:1}},rules:{nocap:1,rings:5,ring_hit:2,ring_all:5,ring_left:999,ring_tol:4.5,ring_chance:true}}}});
const f=api.state.fair;let id=0;window.fixture={api,requests:[]};api.command=async(name,payload)=>{fixture.requests.push({name,payload});if(name==='fair_ring_start'){f.ring={id:++id,chance:true,xs:[10,30,50,70,90],period:2400,phase:.05};return {fair:{round:f.ring}};}return new Promise(resolve=>{fixture.reply=(hits)=>{const n=hits.filter(h=>Number.isInteger(h)&&h>=0).length,prize=n*2+(n===5?5:0);f.ring=null;f.wallet+=prize;f.today_xu.ring+=prize;f.money.total+=prize;api.dispatchEvent(new Event('state'));resolve({fair:{hits,n,prize}});};});};api.refresh=async()=>{};await openFair({api,closeSheet(){}},{tab:'ring'});
</script></html>`;
const server=createServer(async(req,res)=>{try{
 if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return;}
 if(req.url.startsWith('/js/v4/fair-walk.js')){res.setHeader('Content-Type','text/javascript');res.end('export const setup=()=>({active:()=>false,off(){}});');return;}
 if(req.url.startsWith('/js/v4/live.js')){res.setHeader('Content-Type','text/javascript');res.end('export const live={on(){},send(){return false},reconnect(){},flags:{},state:"down"};export function liveBoot(){}');return;}
 const path=resolve(assets,'.'+decodeURIComponent(req.url.split('?')[0]));if(!path.startsWith(assets))throw Error('path');
 res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[extname(path)]||'application/octet-stream');res.end(await readFile(path));
}catch{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const results=[],errors=[];
const check=(name,fn)=>{try{fn();results.push({name,pass:true});console.log('PASS '+name);}catch(e){results.push({name,pass:false,error:e.message});console.log('FAIL '+name+': '+e.message);}};
const dist=(a,b)=>Math.hypot(...a.slice(0,3).map((v,i)=>v-b[i]));
try{for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await engine.launch({headless:true});try{for(const width of [390,1280]){
  const page=await browser.newPage({viewport:{width,height:900},deviceScaleFactor:1});page.on('pageerror',e=>errors.push({browser:name,error:String(e)}));
  const tag=name+'-'+width;await page.goto(`http://127.0.0.1:${server.address().port}`);await page.locator('[data-fh="ringstart"]').click();await page.locator('[data-fh="throw"]').click();await page.waitForTimeout(800);
  await page.locator('.fh-ringstage').screenshot({path:resolve(out,tag+'-pending.png')});
  const firstHit=await page.locator('.fh-bottle.ringed').count(),firstResult=await page.locator('.fh-ringres').count(),firstWallet=await page.locator('.fh-strip').innerText();
  check(tag+' one tap has no confirmed hit',()=>{assert.equal(firstHit,0);assert.equal(firstResult,0);assert.match(firstWallet,/100 xu/);});
  const pendingStyle=await page.locator('.fh-fly.pending').evaluate(el=>{const s=getComputedStyle(el),aim=getComputedStyle(document.querySelector('.fh-aim i'));return {style:s.borderTopStyle,color:s.borderTopColor,aimColor:aim.borderTopColor};});
  check(tag+' thrown ring stays a continuous hoop while awaiting the result',()=>{assert.equal(pendingStyle.style,'solid');assert.equal(pendingStyle.color,pendingStyle.aimColor);});
  for(let i=1;i<5;i++){await page.locator('[data-fh="throw"]').click();await page.waitForTimeout(280);}
  await page.waitForTimeout(1100);const pending=await page.locator('.fh-bottle.ringed').count(),requests=await page.evaluate(()=>fixture.requests.filter(r=>r.name==='fair_ring_throw').length);
  check(tag+' waits for one authoritative response after all five taps',()=>{assert.equal(pending,0);assert.equal(requests,1);});
  await page.evaluate(()=>fixture.reply([1,2,1,2,null]));
  const landings=await page.evaluate(()=>Array.from(document.querySelectorAll('.fh-fly.hit'),fly=>{
   for(const animation of fly.getAnimations()){animation.pause();animation.currentTime=animation.effect.getTiming().duration;}
   const actual=fly.getBoundingClientRect(),center=actual.left+actual.width/2;
   const bottle=[...document.querySelectorAll('.fh-bottle.ringed')].sort((a,b)=>Math.abs(a.getBoundingClientRect().left-center)-Math.abs(b.getBoundingClientRect().left-center))[0];
   const level=fly.style.getPropertyValue('--ring-level')||'0',hoop=[...bottle.querySelectorAll('.fh-neck-ring')].find(h=>h.style.getPropertyValue('--ring-level')===level),anchor=hoop||bottle.querySelector('i'),rect=anchor.getBoundingClientRect(),ring=getComputedStyle(anchor,'::after');
   return {actual:{x:center,y:actual.top,w:actual.width,h:actual.height},settled:{x:rect.left+parseFloat(ring.left)+parseFloat(ring.width)/2,y:hoop?rect.bottom-parseFloat(ring.bottom)-parseFloat(ring.height):rect.top+parseFloat(ring.top),w:parseFloat(ring.width),h:parseFloat(ring.height)}};
  }));
  check(tag+' flight settles into the same hoop geometry without a jump',()=>{assert.equal(landings.length,4);for(const ring of landings)for(const key of ['x','y','w','h'])assert.ok(Math.abs(ring.actual[key]-ring.settled[key])<1,'flight '+key+' must match its settled hoop');});
  await page.waitForTimeout(900);
  const image=resolve(out,tag+'-hit.png');await page.locator('.fh-ringstage').screenshot({path:image});await page.screenshot({path:resolve(out,tag+'-page.png')});
  const geometry=await page.locator('.fh-ringstage').evaluate(stage=>{
   const box=stage.getBoundingClientRect(),b=stage.querySelector('.fh-bottle.ringed i'),body=b.getBoundingClientRect(),hoop=b.parentElement.querySelector('.fh-neck-ring:last-child'),anchor=hoop||b,rect=anchor.getBoundingClientRect(),ring=getComputedStyle(anchor,'::after'),neck=getComputedStyle(b,'::before'),aim=stage.querySelector('.fh-aim i').getBoundingClientRect();
   const left=rect.left+parseFloat(ring.left)-box.left,top=(hoop?rect.bottom-parseFloat(ring.bottom)-parseFloat(ring.height):rect.top+parseFloat(ring.top))-box.top,w=parseFloat(ring.width),h=parseFloat(ring.height),border=parseFloat(ring.borderTopWidth),cx=left+w/2;
   return {ring:{left,top,w,h,border},neckWidth:parseFloat(neck.width),neckTop:body.top+parseFloat(neck.top)-box.top,neckBottom:body.top+parseFloat(neck.top)+parseFloat(neck.height)-box.top,red:ring.borderBottomColor.match(/[\d.]+/g).slice(0,3).map(Number),aim:{width:aim.width,height:aim.height},points:[[cx,top-5],[cx,top+border/2],[cx,top+h-border/2]],bottles:stage.querySelectorAll('.fh-bottle.ringed').length,hoops:stage.querySelectorAll('.fh-neck-ring').length,counts:[...stage.querySelectorAll('.fh-bottle.ringed')].map(b=>b.querySelectorAll('.fh-neck-ring').length),flies:stage.querySelectorAll('.fh-fly').length};
  });
  const pixels=JSON.parse(execFileSync('python',['-c','import sys,json;from PIL import Image;im=Image.open(sys.argv[1]).convert("RGB");print(json.dumps([im.getpixel((round(x),round(y))) for x,y in json.loads(sys.argv[2])]))',image,JSON.stringify(geometry.points)],{encoding:'utf8'}));
  await writeFile(resolve(out,tag+'-geometry.json'),JSON.stringify({geometry,pixels},null,2));
  check(tag+' settled hoop has an open center large enough for the neck',()=>assert.ok(geometry.ring.h-geometry.ring.border*2>=geometry.neckWidth/2,'the hoop opening must visibly contain the neck, not collapse to a one-pixel stripe'));
  check(tag+' neck occludes the rear arc while the front arc remains visible',()=>{assert.ok(dist(pixels[0],pixels[1])<55,'rear arc must pass behind the glass neck');assert.ok(dist(pixels[2],geometry.red)<55,'front arc must pass in front of the neck');});
  check(tag+' confirmed rings overlap neck and spent aim is gone',()=>{assert.equal(geometry.bottles,2);assert.equal(geometry.flies,0);assert.ok(geometry.ring.top>=geometry.neckTop);assert.ok(geometry.ring.top+geometry.ring.h/2<=geometry.neckBottom);assert.equal(geometry.aim.width,0,'an unused-looking aim must not remain floating above a finished round');});
  check(tag+' four server hits remain four visible hoops on two bottles',()=>{assert.equal(geometry.hoops,4);assert.deepEqual(geometry.counts,[2,2]);});
  await page.locator('[data-fh="ringstart"]').click();for(let i=0;i<5;i++){await page.locator('[data-fh="throw"]').click();await page.waitForTimeout(280);}
  await page.evaluate(()=>fixture.reply([-1,-1,-1,-1,-1]));await page.waitForTimeout(800);const missed=await page.locator('.fh-bottle.ringed').count(),wallet=await page.locator('.fh-strip').innerText();
  check(tag+' confirmed misses never add neck rings or extra money',()=>{assert.equal(missed,0);assert.match(wallet,/108 xu/);});
  await page.locator('[data-fh="ringstart"]').click();for(let i=0;i<5;i++){await page.locator('[data-fh="throw"]').click();await page.waitForTimeout(280);}
  await page.evaluate(()=>fixture.reply([3,3,3,3,3]));await page.waitForTimeout(800);
  const stack=await page.locator('.fh-bottle.ringed').evaluate(bottle=>{
   const body=bottle.querySelector('i').getBoundingClientRect(),neck=getComputedStyle(bottle.querySelector('i'),'::before'),top=body.top+parseFloat(neck.top),bottom=top+parseFloat(neck.height);
   return {top,bottom,hoops:[...bottle.querySelectorAll('.fh-neck-ring')].map(hoop=>{const r=hoop.getBoundingClientRect(),s=getComputedStyle(hoop,'::after'),y=r.bottom-parseFloat(s.bottom)-parseFloat(s.height);return {top:y,center:y+parseFloat(s.height)/2};})};
  });
  await page.locator('.fh-ringstage').screenshot({path:resolve(out,tag+'-five-on-one.png')});
  check(tag+' all five rings fit distinctly around one neck',()=>{assert.equal(stack.hoops.length,5);assert.equal(new Set(stack.hoops.map(h=>h.center)).size,5);for(const hoop of stack.hoops){assert.ok(hoop.top>=stack.top);assert.ok(hoop.center<=stack.bottom);}});await page.close();
 }}finally{await browser.close();}
}}finally{await new Promise(r=>server.close(r));}
await writeFile(resolve(out,'results.json'),JSON.stringify({results,errors},null,2));
assert.deepEqual(errors,[]);assert.equal(results.filter(r=>!r.pass).length,0,'visible ring geometry regressions');
