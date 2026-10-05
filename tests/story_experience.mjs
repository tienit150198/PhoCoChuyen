import assert from 'node:assert/strict';
import fs from 'node:fs';
import {icon,escapeHTML} from '../public/js/icons.js';
import {acctPlace} from '../public/js/v4/acct-jobs.js';
// Isolate this markup view from journey's browser boot side effects.
const source=fs.readFileSync(new URL('../public/js/v4/stories.js',import.meta.url),'utf8')
  .replace(/^import .*;\r?\n/gm,'').replace(/export /g,'');
const storiesCard=new Function('icon','esc','emojiOf','acctPlace',`${source}\nreturn storiesCard;`)(icon,escapeHTML,m=>m.emoji||'🧋',acctPlace);

const arc={career:'milk_tea',title:'Ly trà mùa thi',emoji:'📚',seen:2,total:5,done:false,pending:null,
  recap:'Linh: Từng trang một thôi.',beats:[{title:'Bốn mươi ngày',emoji:'⏳',pick:'Viết lên nắp ly',recap:'Linh: Từng trang một thôi.'}],
  next:{ready:false,requirements:[{id:'served',label:'Hoàn thành công việc',current:5,target:8,remaining:3,met:false},
    {id:'days',label:'Kết thúc ngày làm',current:4,target:4,remaining:0,met:true}]}};
const env={api:{content:{catalogue:[{id:'milk_tea',place:'Tiệm trà sữa',color:'#884422'}]},
  state:{careers:{milk_tea:{started:true}},stories:{arcs:[arc],due:[]}}}};
let html=storiesCard(env);
assert.ok(html.includes('Gần nhất'));
assert.ok(html.includes('Linh: Từng trang một thôi.'));
assert.ok(html.includes('Hoàn thành công việc'));
assert.ok(html.includes('5/8'));
assert.ok(html.includes('Còn 3'));
assert.ok(html.includes('Đã đạt'));
assert.ok(html.includes('data-action="choose" data-career="milk_tea"'));
env.api.state.journey={story:true,unlocked:['milk_tea'],places:{milk_tea:{paused:true}}};
html=storiesCard(env);
assert.ok(html.includes('data-action="jrPlaces"'), 'Paused workplace must offer its reopen route');
assert.ok(html.includes('Xem nơi làm việc'));
assert.ok(!html.includes('data-action="choose"'));
env.api.state.journey.places.milk_tea.paused=false;
env.api.state.journey.unlocked=[];
html=storiesCard(env);
assert.ok(html.includes('data-action="jrPlaces"'), 'Locked workplace must show the workplace list');
assert.ok(!html.includes('data-action="choose"'));
arc.pending='s1';
env.api.state.journey.places.milk_tea.paused=true;
html=storiesCard(env);
assert.ok(html.includes('data-action="jrArcOpen"'));
assert.ok(!html.includes('data-action="jrPlaces"'), 'Pending scene remains readable even when workplace is unavailable');
assert.ok(!html.includes('st-unlock'));
arc.pending=null;
env.api.state.journey.unlocked=['milk_tea'];
env.api.state.journey.places.milk_tea.paused=false;
html=storiesCard(env);
assert.ok(html.includes('data-action="choose"'), 'Available workplace keeps direct navigation');
arc.pending=null;arc.done=true;arc.next=null;
arc.keepsake={emoji:'🧋',name:'Công thức',desc:'Lời nhắn riêng của Linh'};
html=storiesCard(env);
assert.ok(html.includes('Lời nhắn riêng của Linh'));
assert.ok(!html.includes('data-action="choose"'));
console.log('Story recap, requirements, navigation and keepsake rendering passed.');
