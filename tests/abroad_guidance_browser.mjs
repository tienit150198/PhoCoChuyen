import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdir} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
import {chromium} from 'file:///C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs';

const root=resolve(import.meta.dirname,'..');
const fixture=(await readFile(resolve(root,'tests/abroad-guidance.mjs'),'utf8')).split('const A=')[1].split('let html=')[0];
const html=`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/app.css"><link rel="stylesheet" href="/css/abroad.css"><style>body{margin:0}#sheet{box-sizing:border-box;padding:16px;max-width:700px;margin:auto}</style><main id="sheet"></main><script type="module">
import {abroadView} from '/js/v4/abroad.js';
const A=${fixture}
window.paint=()=>document.querySelector('#sheet').innerHTML=abroadView(env);
window.env=env;window.A=A;window.chosen=[];
document.addEventListener('click',e=>{const b=e.target.closest('[data-action="choose"]');if(b)chosen.push(b.dataset.career)});
paint();</script>`;
const server=createServer(async(req,res)=>{try{if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return;}
 const path=resolve(root,'public','.'+decodeURIComponent(req.url.split('?')[0]));if(!path.startsWith(resolve(root,'public')))throw Error('path');
 res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css'})[extname(path)]||'application/octet-stream');res.end(await readFile(path));
}catch{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await chromium.launch({headless:true});
const out=resolve(root,'output/playwright/abroad-guidance');await mkdir(out,{recursive:true});
try{for(const width of [390,1280]){
 const page=await browser.newPage({viewport:{width,height:860}}),errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(`http://127.0.0.1:${server.address().port}`);await page.locator('.ab-open-shifts').waitFor();
 await page.locator('.ab-open-shifts [data-career="accounting"]').click();
 assert.deepEqual(await page.evaluate(()=>chosen),['accounting']);
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 await page.screenshot({path:resolve(out,`work-${width}.png`),fullPage:true});
 await page.evaluate(()=>{env.ui={abTab:'study',abLast:{ok:true,text:'Đã học buổi 1'}};A.study={p:'kr',n:1,of:3,lesson:null};paint()});
 await page.getByRole('button',{name:'Về nơi làm việc để khép ca',exact:true}).click();
 assert.deepEqual(await page.evaluate(()=>chosen),['accounting','pharmacy']);
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 await page.screenshot({path:resolve(out,`study-${width}.png`),fullPage:true});assert.deepEqual(errors,[]);await page.close();
}console.log('Abroad guidance: navigation targets and no overflow at 390/1280px passed.');}
finally{await browser.close();await new Promise(r=>server.close(r));}
