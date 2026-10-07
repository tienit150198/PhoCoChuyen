// Milk tea after end_day (07/10): the unfinished cup stays and the counter still opens, but game/boba.py refuses every
// brewing step ("Mở cửa quán trước khi pha nhé."). Run by tests/test_milk_tea_closed.py with {open, closed, content}
// on stdin: two public states of the same counter, the shop open and the shop closed.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import tea,{quickParts} from '../public/js/careers/milk_tea.js';
import {careerContext} from '../public/js/v4/careers.js';
const {canQuick,withLocal}=quickParts;
const {open,closed,content}=JSON.parse(readFileSync(0,'utf8'));

const draw=state=>{
  const x=careerContext({api:{state,content},ui:{}});
  const t=x.room.tasks.find(v=>v.id===x.room.active_task)||x.room.tasks.find(v=>v.status!=='completed');
  return {x,t,html:tea.job(t,x)};
};
const btns=html=>[...html.matchAll(/<button\b[^>]*>/g)].map(m=>m[0]);

// Open: the counter works as before (the tiles send their picks, a pick shows at once).
{
  const {x,t,html}=draw(open);
  assert.equal(x.room.open,true);
  assert.match(html,/data-op="tea_cup"/,'open: the cup tiles send tea_cup');
  assert.doesNotMatch(html,/data-why="Mở ca trước"/);
  assert.doesNotMatch(html,/data-action="startHere"/);
  assert.equal(canQuick(x,withLocal(t,x),'tea_cup',{task:t.id,size:'M'}),true,'open: a cup pick shows at once');
}
// Closed: no pick is shown ahead (the server would refuse it), every brewing control is dimmed with the reason, the
// bar's main button opens the shift.
{
  const {x,t,html}=draw(closed);
  assert.equal(x.room.open,false);
  assert.ok(t,'the unfinished cup is still there after end_day');
  for(const [op,p] of [['tea_cup',{size:'M'}],['tea_cup',{size:'L'}],['tea_ice',{level:'normal'}],['tea_sugar',{level:50}],['tea_add',{item:'black'}]])
    assert.equal(canQuick(x,withLocal(t,x),op,{task:t.id,...p}),false,`closed: ${op} is not shown ahead`);
  for(const op of ['tea_cup','tea_add','tea_ice','tea_sugar','tea_seal','tea_seal_start','tea_check'])
    assert.doesNotMatch(html,new RegExp(`data-op="${op}"`),`closed: nothing sends ${op}`);
  const tiles=btns(html).filter(b=>/class="mt-tile /.test(b)&&/data-k="cup_/.test(b));
  assert.ok(tiles.length>=2,'the cup tiles are drawn');
  for(const b of tiles){
    assert.match(b,/is-why/,'dimmed');assert.match(b,/aria-disabled="true"/);assert.match(b,/data-why="Mở ca trước"/);
    assert.match(b,/data-fix="[^"]*startHere/,'the fix opens the shift');
    assert.doesNotMatch(b,/\sdisabled(?=[\s>])/,'dimmed but tappable (docs/UI_KIT.md), never a mute grey tile');
  }
  const segs=btns(html).filter(b=>/class="mt-seg /.test(b)&&/data-k="(ice|sugar)-/.test(b));
  for(const b of segs)assert.match(b,/data-why="Mở ca trước"/);
  const bar=html.slice(html.lastIndexOf('fk-bar'));
  assert.match(bar,/data-action="startHere"[^>]*>☀️ Mở ca</,'the main button opens the shift');
  assert.match(tea.next(t,x),/Mở ca/,'the queue line says it too');
}
console.log('milk tea closed: ok');
