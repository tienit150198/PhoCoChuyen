/** ✈️ v4/travel.js (#464) in a real browser at 390 px and 1280 px: the whole trip tapped through (pick a place, a day,
 * book, the airport's steps, the crew's menu, landing, two spot scenes, a souvenir, the flight home, the summary, the
 * Sổ du lịch). The server is stood in for by the real states game/travel.py sent at each step (tests/travel-fixture.mjs);
 * the test checks the payloads the page sends, that nothing overflows sideways, and saves screenshots
 * (output/playwright/travel). */
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdir} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
import {chromium} from 'file:///C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs';
import {travelFixture} from './travel-fixture.mjs';

const root=resolve(import.meta.dirname,'..');
const F=travelFixture();
const html=`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/app.css"><style>body{margin:0}</style>
<body><script type="module">
import {openTravel} from '/js/v4/travel.js';
const F=${JSON.stringify(F)};
const clone=x=>structuredClone(x);
const api=new EventTarget();
api.state={journey:clone(F.states.list)};api.content={journey:{travel:F.content}};
window.sent=[];
const tr=()=>api.state.journey.travel.trip;
const move=(name,patch)=>{const j=clone(F.states[name]);if(patch)patch(j);api.state.journey=j;};
api.command=async(action,payload)=>{
  sent.push([action,payload]);await new Promise(r=>setTimeout(r,30));
  let r={message:'OK',effects:[]};
  if(action==='jr_trip_book')move(payload.day===api.state.journey.life_day?'today':'booked');
  else if(action==='jr_trip_board')move('fly');
  else if(action==='jr_trip_meal'){const j=clone(api.state.journey);j.travel.trip.meal=true;api.state.journey=j;r.effects=['💁 Dạ của mình đây ạ.'];}
  else if(action==='jr_trip_land'){if(tr().ph==='fly'){move('here');r.travel={stamp:'da_lat',first:true};}else{move('done');r.travel={summary:F.summary};}}
  else if(action==='jr_trip_spot'){const j=clone(api.state.journey);j.travel.trip.seen.push(payload.id);if(!j.travel.cards.includes(payload.id))j.travel.cards.push(payload.id);api.state.journey=j;r.travel={card:payload.id,new:true};}
  else if(action==='jr_trip_buy'){const j=clone(api.state.journey);j.travel.souv[payload.id]=(j.travel.souv[payload.id]||0)+1;api.state.journey=j;}
  else if(action==='jr_trip_home')move('back');
  api.dispatchEvent(new Event('state'));return r;
};
window.env={api,closeSheet(){}};
window.open=()=>openTravel(env);
open();
</script>`;
const server=createServer(async(req,res)=>{try{if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return;}
 const path=resolve(root,'public','.'+decodeURIComponent(req.url.split('?')[0]));if(!path.startsWith(resolve(root,'public')))throw Error('path');
 res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css'})[extname(path)]||'application/octet-stream');res.end(await readFile(path));
}catch{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await chromium.launch({headless:true});
const out=resolve(root,'output/playwright/travel');await mkdir(out,{recursive:true});
const life=F.states.list.life_day;
try{for(const width of [390,1280]){
  const page=await browser.newPage({viewport:{width,height:860}}),errors=[];page.on('pageerror',e=>errors.push(String(e)));
  const dlg=page.locator('dialog.tv-sheet');
  const main=dlg.locator('.sd-main');
  const fits=async(name)=>{
    if(process.env.TV_DEBUG)console.log(name,await page.evaluate(()=>{const d=document.querySelector('dialog.tv-sheet');const w=d.clientWidth;return [document.documentElement.scrollWidth,innerWidth,d.scrollWidth,w,[...d.querySelectorAll('*')].filter(e=>{const r=e.getBoundingClientRect();const dr=d.getBoundingClientRect();return r.right>dr.right+1;}).slice(0,6).map(e=>e.className+':'+Math.round(e.getBoundingClientRect().right))];}));
    assert.ok(await page.evaluate(()=>{const d=document.querySelector('dialog.tv-sheet');return document.documentElement.scrollWidth<=innerWidth+1&&d.scrollWidth<=d.clientWidth+1;}),`${name}: no sideways scroll at ${width}px`);
    await page.screenshot({path:resolve(out,`${name}-${width}.png`)});
  };
  await page.goto(`http://127.0.0.1:${server.address().port}`);
  await dlg.locator('.tv-place').first().waitFor();
  await fits('1-places');
  // ♿ #519: opened on its heading; a place picked with the keyboard: focus on the place's heading, never on <body>
  const focused=()=>page.evaluate(()=>{const a=document.activeElement;return {tag:a.tagName,text:a.textContent.trim(),tv:a.dataset?.tv||'',id:a.dataset?.id||''};});
  assert.equal((await focused()).tag,'H2');
  for(let i=0;i<30&&(await focused()).id!=='da_lat';i++)await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
  await dlg.locator('.tv-days').waitFor();
  {const f=await focused();assert.equal(f.tag,'H3');assert.match(f.text,/Đà Lạt/);}
  await dlg.locator('.tv-day[data-n="1"]').focus();await page.keyboard.press('Enter');
  assert.equal((await focused()).tv,'ahead','a day picked: focus stays on the day');
  await dlg.locator('.tv-day[data-n="4"]').click();
  assert.match(await main.innerText(),/Đặt vé · 270 xu/);
  await fits('2-place');
  await dlg.locator('.tv-day[data-n="0"]').click();
  assert.match(await main.innerText(),/Đặt vé · 530 xu/);
  await main.click();
  await page.waitForFunction(()=>sent.length===1);
  assert.deepEqual(await page.evaluate(()=>sent[0]),['jr_trip_book',{to:'da_lat',cls:'eco',day:life,confirm:true}]);   // today: the dear fare
  await dlg.locator('.tv-pass').waitFor();
  await fits('3-ticket');
  await main.click();   // 🧳 Ra sân bay
  await dlg.locator('.tv-desk').waitFor();
  await fits('4-airport');
  await dlg.locator('[data-tv="step"]').click();
  await dlg.locator('[data-tv="step"]').click();
  assert.match(await main.innerText(),/Lên máy bay/);
  await main.click();
  await dlg.locator('.tv-window').waitFor();
  await dlg.locator('[data-tv="food"][data-id="com_ga"]').click();
  await dlg.locator('[data-tv="drink"][data-id="tra_nong"]').click();
  await dlg.locator('[data-tv="meal"]').click();
  await page.waitForFunction(()=>sent.some(x=>x[0]==='jr_trip_meal'));
  assert.deepEqual(await page.evaluate(()=>sent.find(x=>x[0]==='jr_trip_meal')[1]),{food:'com_ga',drink:'tra_nong'});
  await dlg.locator('[data-tv="crew"][data-id="gio"]').click();
  assert.match(await dlg.locator('.tv-bubble').last().innerText(),/phút nữa là hạ cánh/);
  await fits('5-cabin');
  await main.click();   // 🛬
  await dlg.locator('.tv-stampfx').waitFor();
  await fits('6-landed');
  await dlg.locator('.tv-spots-list').waitFor();
  await dlg.locator('[data-tv="spot"][data-id="dl_cho"]').click();   // 🍽️ three bites
  for(let i=0;i<3;i++)await dlg.locator('[data-tv="miniTap"]').click();
  await dlg.locator('.tv-postcard').waitFor();
  await fits('7-postcard');
  await dlg.locator('[data-tv="cardClose"]').click();
  await dlg.locator('[data-tv="spot"][data-id="dl_ga"]').click();    // 📸 the viewfinder
  await dlg.locator('.tv-finder').waitFor();
  await fits('8-photo');
  await page.waitForTimeout(300);
  await dlg.locator('[data-tv="miniTap"]').click();
  await dlg.locator('.tv-stars').waitFor();
  await dlg.locator('[data-tv="cardClose"]').click();
  await dlg.locator('[data-tv="souv"][data-id="dl_mut"]').click();
  await dlg.locator('[data-tv="buy"]').click();
  await page.waitForFunction(()=>sent.some(x=>x[0]==='jr_trip_buy'));
  await fits('9-here');
  assert.deepEqual(await page.evaluate(()=>sent.filter(x=>x[0]==='jr_trip_spot').map(x=>x[1].id)),['dl_cho','dl_ga']);
  await main.click();   // 🛫 về nhà
  await dlg.locator('.tv-window').waitFor();
  await main.click();   // 🏠 hạ cánh
  await dlg.locator('.tv-summary').waitFor();
  await fits('10-summary');
  await main.click();   // Xong
  await dlg.locator('[data-tv="tab"][data-tab="book"]').click();
  await dlg.locator('.tv-stamps').waitFor();
  await fits('11-book');
  assert.deepEqual(await page.evaluate(()=>sent.map(x=>x[0])),['jr_trip_book','jr_trip_board','jr_trip_meal','jr_trip_land','jr_trip_spot','jr_trip_spot','jr_trip_buy','jr_trip_home','jr_trip_land']);
  assert.deepEqual(errors,[]);await page.close();
}console.log('Travel browser: book → airport → cabin → land → spots → souvenir → home → summary → Sổ du lịch at 390/1280px passed.');}
finally{await browser.close();await new Promise(r=>server.close(r));}
