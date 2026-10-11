// Công an phường, generator 2 (tests/test_police_cases.py UI): the real police.js renders the posts, the business
// inspection and the big case from public states at each step; no hole ("undefined", "NaN") and no meta words.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import police from '../public/js/careers/police.js';
import {careerContext} from '../public/js/v4/careers.js';
const {content,cases}=JSON.parse(readFileSync(0,'utf8'));
for(const c of cases){
  const x=careerContext({api:{state:c.state,content},ui:{}});
  const t=x.room.tasks.find(v=>v.id===(c.tid||x.room.active_task));
  const html=police.job(t,x);
  assert.doesNotMatch(html,/undefined|NaN|\[object Object\]/,c.name);
  assert.doesNotMatch(html,/\bNPC\b|trong game|mô phỏng/i,c.name);
  for(const re of c.expect)assert.match(html,new RegExp(re),`${c.name}: ${re}`);
  for(const re of c.absent||[])assert.doesNotMatch(html,new RegExp(re),`${c.name}: not ${re}`);
  assert.ok(police.next(t,x),c.name);
}
console.log(`police cases ui: ${cases.length} views passed`);
