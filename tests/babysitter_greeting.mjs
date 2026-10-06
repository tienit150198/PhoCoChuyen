import assert from 'node:assert/strict';
import babysitter from '../public/js/careers/babysitter.js';
import {escapeHTML as esc} from '../public/js/icons.js';
const x={esc,ui:{},room:{day:1,metrics:{served:1},data:{intro:true,fam:{kid:'Bin',temper:'shy'},today:{},plan:[]}},
 cc:{tempers:{shy:['🙈','Nhút nhát','squat']},greets:{squat:['🧎','Chào nhỏ nhẹ'],grab:['🙆','Bế xốc']}},
 npc:()=>({display_name:'Mẹ'}),portrait:()=>'',cmd:(label,cmd,payload,cls='',disabled=false)=>`<button data-command="${cmd}"${disabled?' disabled':''}>${label}</button>`};
const t={id:'babysitter-1-0',kind:'arrive',npc:'mom',needs:{bag:[],missing:'ao'},st:{wash:true,note:true,bag:true,ask:'ao',greet:'grab'}};
let html=babysitter.job(t,x);
let buttons=[...html.matchAll(/<button[^>]+data-command="bm_greet"[^>]*>/g)].map(v=>v[0]);
assert.equal(buttons.length,2);assert.ok(buttons.every(v=>!v.includes('disabled')),'wrong greeting must leave choices available');
assert.match(html,/thử cách chào khác/i);assert.match(html,/class="bm-temper warn"[^>]*>Tính bé: 🙈 <b>Nhút nhát<\/b>/,'a wrong try names the temper, readable');
assert.doesNotMatch(html,/Tính bé:[^<]*Chào nhỏ nhẹ/,'the temper line never names the greeting');assert.match(html,/class="bad gd-todo"[^>]*>.*?Chào bé hợp tính/);
t.st.greet='squat';html=babysitter.job(t,x);buttons=[...html.matchAll(/<button[^>]+data-command="bm_greet"[^>]*>/g)].map(v=>v[0]);
assert.ok(buttons.every(v=>v.includes('disabled')));assert.doesNotMatch(html,/thử cách chào khác/i);assert.match(html,/class="bm-temper">Tính bé:/);
assert.match(html,/class="ok"><span>✓<\/span>Chào bé hợp tính/);
console.log('Babysitter greeting: retry controls, corrective hint and honest checklist passed.');
