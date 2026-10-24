/** ♿ Feedback #428 (isometric-pickups.js) in a real browser at 390 px, keyboard only: Tiện ích → "Rương & lì xì" opens on
 * its heading; the chests are listed nearest first, "Đi tới và nhặt" walks there through the world's own route
 * (world.go) and picks through its own onInteract (the same claim as a tap: isometric-treasure.js); a lì xì's "Giật"
 * goes through v4/lixi.js grab with the result read out by the panel's live region; the list refreshes without taking
 * the focused button away; Escape closes and gives focus back. The world, the lì xì store and grab are stand-ins.
 * Screenshot: output/playwright/pickups. */
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdir} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
import {chromium} from 'file:///C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs';

const root=resolve(import.meta.dirname,'..');
const html=`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/app.css"><style>body{margin:0;min-height:100vh;background:#cfe3c4}</style>
<body><button id="opener" type="button">Tiện ích</button><div id="toasts" role="status" aria-live="polite"></div><script type="module">
import {openPickups,chestRows} from '/js/isometric-pickups.js';
window.calls=[];
const world={mode:'town',treasure:[{id:'far',count:1},{id:'near',count:2}],
  hotspots:[{id:'career:pho',x:1,y:1},{id:'treasure:far',x:9,y:12},{id:'treasure:near',x:2,y:3}],
  getPresence:()=>({x:0,y:0}),
  go(id,done){calls.push(['go',id]);setTimeout(done,50);},
  onInteract(id){calls.push(['interact',id]);world.hotspots=world.hotspots.filter(h=>h.id!==id);}};
window.world=world;
const packets=[{id:'lx1',name:'Bơ',total:100000,n:20,left:7,status:'open',at:1},{id:'lx2',name:'',total:50000,n:10,left:3,status:'open',at:2}];
const fns=new Set();
const lixi={ranked:()=>packets.slice(),grabbable:p=>p.left>0,onChange(f){fns.add(f);return ()=>fns.delete(f);},refresh(){calls.push(['refresh']);}};
window.more=()=>{packets.push({id:'lx3',name:'Cam',total:10000,n:5,left:5,status:'open',at:3});fns.forEach(f=>f());};
const grab=async(id,cur,opt)=>{calls.push(['grab',id]);await new Promise(r=>setTimeout(r,30));const p=packets.find(x=>x.id===id);p.left--;opt.say('🧧 +4.321 xu từ lì xì của Bơ');};
window.chestRows=chestRows;
document.getElementById('opener').addEventListener('click',()=>openPickups({api:{},world},{lixi,grab,world:()=>world}));
</script>`;
const server=createServer(async(req,res)=>{try{if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return;}
 const path=resolve(root,'public','.'+decodeURIComponent(req.url.split('?')[0]));if(!path.startsWith(resolve(root,'public')))throw Error('path');
 res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css'})[extname(path)]||'application/octet-stream');res.end(await readFile(path));
}catch{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await chromium.launch({headless:true});
const out=resolve(root,'output/playwright/pickups');await mkdir(out,{recursive:true});
try{
  const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(`http://127.0.0.1:${server.address().port}`);
  const active=()=>page.evaluate(()=>{const a=document.activeElement;return {tag:a.tagName,text:(a.getAttribute('aria-label')||a.textContent||'').trim(),pick:a.dataset?.pickChest||a.dataset?.pickLixi||''};});
  await page.focus('#opener');await page.keyboard.press('Enter');
  await page.locator('.iso-pick').waitFor();
  assert.deepEqual(await active(),{tag:'H2',text:'Rương & lì xì',pick:''},'opens on its heading');
  // nearest first, with how far
  const rows=await page.locator('[data-pick-list="chests"] li').allInnerTexts();
  assert.equal(rows.length,2);assert.match(rows[0],/Rương 1 · 2 rương chồng · cách khoảng 4 bước/);assert.match(rows[1],/Rương 2 · cách khoảng 15 bước/);
  // every control has a name
  const unnamed=await page.evaluate(()=>[...document.querySelectorAll('.iso-pick button')].filter(b=>!(b.getAttribute('aria-label')||b.textContent).trim()).length);
  assert.equal(unnamed,0);
  const tree=await page.accessibility.snapshot();
  const names=[];const walk=n=>{if(n.role==='button')names.push(n.name);(n.children||[]).forEach(walk);};walk(tree);
  assert.ok(names.includes('Đi tới và nhặt rương 1')&&names.includes('Giật lì xì của Bơ')&&names.includes('Giật lì xì của một người hàng xóm'),names.join(' | '));
  await page.screenshot({path:resolve(out,'pickups-390.png')});
  // Tab → Đóng, → the first chest; Enter walks and picks through the world
  await page.keyboard.press('Tab');assert.equal((await active()).text,'Đóng danh sách');
  await page.keyboard.press('Tab');assert.equal((await active()).pick,'near');
  await page.keyboard.press('Enter');
  assert.match(await page.locator('.iso-pick-note').innerText(),/Đang đi tới rương, khoảng 4 bước/);
  await page.waitForFunction(()=>calls.some(c=>c[0]==='interact'));
  assert.deepEqual(await page.evaluate(()=>calls.filter(c=>c[0]!=='refresh')),[['go','treasure:near'],['interact','treasure:near']]);
  await page.waitForFunction(()=>document.querySelectorAll('[data-pick-list="chests"] li').length===1);   // picked: gone from the list
  assert.equal((await active()).tag,'H2','its button gone: focus back on the heading, not lost');
  // a lì xì: Giật, the result read out; a new packet comes in without taking the focused button away
  await page.keyboard.press('Tab');await page.keyboard.press('Tab');await page.keyboard.press('Tab');
  assert.equal((await active()).pick,'lx1');
  await page.keyboard.press('Enter');
  await page.waitForFunction(()=>/4\.321 xu/.test(document.querySelector('.iso-pick-note').textContent));
  await page.evaluate(()=>more());await page.waitForTimeout(100);
  assert.equal((await active()).pick,'lx1','the list rebuilt, the same button keeps focus');
  assert.equal(await page.locator('[data-pick-list="lixi"] li').count(),3);
  // a chest taken by someone else meanwhile
  await page.evaluate(()=>{world.hotspots=world.hotspots.filter(h=>h.id!=='treasure:far');});
  await page.waitForTimeout(1100);
  assert.match(await page.locator('[data-pick-empty="chests"]').innerText(),/Chưa có rương/);
  // Escape: closed, focus back where it was
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('.iso-pick').count(),0);
  assert.equal((await active()).text,'Tiện ích');
  // not in the town: says so
  await page.evaluate(()=>{world.mode='work';});await page.focus('#opener');await page.keyboard.press('Enter');
  await page.locator('.iso-pick').waitFor();
  assert.match(await page.locator('[data-pick-empty="chests"]').innerText(),/Ra phố để thấy rương/);
  assert.deepEqual(errors,[]);await page.close();
  console.log('isometric pickups browser: list nearest first, walk + pick via the world, Giật via grab, live note, focus kept, Escape at 390px passed.');
}finally{await browser.close();await new Promise(r=>server.close(r));}
