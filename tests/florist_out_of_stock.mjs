// Backlog #9: with 0 cards / 0 banners, the write/print buttons are off, say why, and offer restocking.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import florist from '../public/js/careers/florist.js';
import {careerContext} from '../public/js/v4/careers.js';
const {state,content}=JSON.parse(readFileSync(0,'utf8'));
const x=careerContext({api:{state,content},ui:{}});
const t=x.room.tasks.find(v=>v.id===x.room.active_task);
const render=tab=>{florist.job(t,x);x.ui.tab=tab;return florist.job(t,x);};
const btn=(html,action)=>(html.match(new RegExp(`<button[^>]*data-action="${action}"[^>]*>`,'g'))||[]);
// In stock: enabled, no "Hết" line.
let html=render('card');
assert.ok(btn(html,'car:card').length===1&&!/disabled/.test(btn(html,'car:card')[0]),'card button enabled with stock');
assert.doesNotMatch(html,/fl-out/);
// Out of cards.
x.room.inventory.stock.card=0;
html=render('card');
assert.match(btn(html,'car:card')[0],/disabled/,'write button off at 0 cards');
for(const b of btn(html,'car:cardtpl'))assert.match(b,/disabled/,'suggested-line button off at 0 cards');
assert.match(html,/Hết thiệp: nhập thêm mới viết được/);
assert.match(html,/class="btn small ghost rs-btn[^"]*" data-action="v4Restock"[^>]*data-items="card:6"/);
// Out of banners, on a wreath.
t.work.base='wreath';x.room.inventory.stock.banner=0;
html=render('design');
assert.match(btn(html,'car:banner')[0],/disabled/,'print button off at 0 banners');
for(const b of btn(html,'car:bannertpl'))assert.match(b,/disabled/);
assert.match(html,/Hết băng rôn: nhập thêm mới in được/);
assert.match(html,/data-action="v4Restock"[^>]*data-items="banner:2"/);
x.room.inventory.stock.banner=3;
html=render('design');
assert.doesNotMatch(btn(html,'car:banner')[0],/disabled/);
assert.doesNotMatch(html,/Hết băng rôn/);
console.log('florist out-of-stock checks passed');
