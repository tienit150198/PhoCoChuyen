import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdir} from 'node:fs/promises';
import {resolve,extname,sep} from 'node:path';
// Set PLAYWRIGHT_MODULE to a file URL when using a bundled Playwright runtime.
const {chromium,webkit}=await import(process.env.PLAYWRIGHT_MODULE||'playwright');

// Exercise the real dialog, click handlers, stylesheet and renderer with controlled API responses.
const root=resolve(import.meta.dirname,'..'),assets=resolve(root,'public'),out=resolve(root,'output/playwright/fair-loss-board');
await mkdir(out,{recursive:true});
const html=`<!doctype html><html lang="vi" data-theme="kem"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/app.css"><script type="module">
import {openFair} from '/js/v4/fair.js';
const api=Object.assign(new EventTarget(),{content:{},state:{settings:{sound:false,music:false},journey:{story:true},fair:{board:'fair-2026',show:true,open:true,forever:true,now:Date.now()/1000,wallet:100,today_xu:{},money:{total:9999},earn:{},rules:{}}}});
window.fixture={fail:false,hidden:false,net:-250};api.json=async url=>{if(fixture.fail)throw new Error('Mất kết nối thử nghiệm');const loss=url.includes('fair-loss');return {board:loss?'fair-loss':'fair-2026',rows:fixture.hidden?[]:[{rank:1,name:'Người chơi có tên thật dài để kiểm tra màn hình nhỏ <b>',guest:true,xu:loss?250:9999,days:4,me:true}],me:{net:fixture.net,xu:250,rank:1,visible:!fixture.hidden},fair:{loss,weekly:true,next:Date.now()/1000+86400,week:'2026-10-05',started:1791583200,winners:loss?[{rank:1,name:'Minh <img>',score:700,title:'Vua đen đủi',emoji:'🥀'}]:[],crowned:'2026-10-05'}};};await openFair({api,closeSheet(){}},{tab:'board'});
</script></html>`;
const server=createServer(async(req,res)=>{try{
 if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return;}
 if(req.url.startsWith('/js/v4/fair-walk.js')){res.setHeader('Content-Type','text/javascript');res.end('export const setup=()=>({active:()=>false,off(){}});');return;}
 if(req.url.startsWith('/js/v4/live.js')){res.setHeader('Content-Type','text/javascript');res.end('export const live={on(){},send(){return false},reconnect(){},flags:{},state:"down"};export function liveBoot(){}');return;}
 const path=resolve(assets,'.'+decodeURIComponent(req.url.split('?')[0]));if(!path.startsWith(assets+sep))throw Error('path');
 res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[extname(path)]||'application/octet-stream');res.end(await readFile(path));
}catch{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const errors=[];
try{for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await engine.launch({headless:true});try{for(const width of [320,390,1280]){
  const page=await browser.newPage({viewport:{width,height:900},deviceScaleFactor:1});page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(`http://127.0.0.1:${server.address().port}`);
  await page.locator('.fh-board li').waitFor();assert.match(await page.locator('.fh-board').innerText(),/\+9.999 xu/);
  await page.getByRole('button',{name:'Top lỗ',exact:true}).click();await page.locator('.fh-loss .fh-board li').waitFor();
  assert.match(await page.locator('.fh-pts').innerText(),/lời tích lũy 9.999 xu/);
  assert.match(await page.locator('.fh-loss .fh-me').innerText(),/Tuần này bạn đang lỗ -250 xu/);
  assert.match(await page.locator('.fh-loss .fh-crowned').innerText(),/-700 xu/);
  assert.equal(await page.locator('.fh-board-modes button[aria-pressed="true"]').innerText(),'Top lỗ');
  assert.equal(await page.locator('.fh-board img,.fh-crowned img').count(),0);
  const bounds=await page.locator('.fh-gold').evaluate(el=>({width:el.clientWidth,scroll:el.scrollWidth}));assert.ok(bounds.scroll<=bounds.width+1,`${name} ${width}: board overflows`);
  await page.screenshot({path:resolve(out,`${name}-${width}-loss.png`),fullPage:true});
  await page.getByRole('button',{name:'Top lời',exact:true}).click();await page.locator('.fh-gold:not(.fh-loss) .fh-board li').waitFor();assert.match(await page.locator('.fh-me').innerText(),/9.999 xu/);
  await page.evaluate(()=>{fixture.fail=true;});await page.getByRole('button',{name:'Top lỗ',exact:true}).click();await page.getByRole('alert').waitFor();assert.match(await page.getByRole('alert').innerText(),/Mất kết nối/);
  await page.evaluate(()=>{fixture.fail=false;fixture.hidden=true;fixture.net=0;});await page.getByRole('button',{name:'Thử lại',exact:true}).click();await page.locator('.fh-hidden').waitFor();
  assert.match(await page.locator('.fh-me').innerText(),/hòa vốn 0 xu/);assert.doesNotMatch(await page.locator('.fh-me>span').innerText(),/hạng/);
  assert.equal(await page.locator('.fh-board li').count(),0);console.log(`PASS ${name} ${width}: toggle, amounts, escaping, privacy, retry, no horizontal overflow`);await page.close();
 }}finally{await browser.close();}
}}finally{await new Promise(r=>server.close(r));}
assert.deepEqual(errors,[]);
