/** ✈️ Fixtures for tests/travel.mjs and tests/travel_browser.mjs: the real catalogue and the real public states of a
 * trip at each step, made by game/travel.py through the engine (python), so the client is tested on what the server
 * really sends. */
import {execFileSync} from 'node:child_process';
import {resolve} from 'node:path';

const root=resolve(import.meta.dirname,'..');
export function travelFixture(){
  const out=execFileSync(process.env.PYTHON||'python',['-c',`
import json
from game import travel as tv, lux
from game.engine import public_state
from tests.test_bank import act, story
def J(s):
    j = public_state(s)['journey']
    return dict(story=True, life_day=j['life_day'], wallet=j['wallet'], bank=j.get('bank'), travel=j['travel'], lux=j.get('lux'))
out = dict(content=tv.catalogue(), states={})
s = story(3000)
out['states']['list'] = J(s)
s1, _ = act(s, 'jr_trip_book', to='da_lat', cls='eco', day=s['journey']['life_day'] + 2, confirm=True)
out['states']['booked'] = J(s1)
s2, _ = act(s, 'jr_trip_book', to='da_lat', cls='eco', day=s['journey']['life_day'], confirm=True)
out['states']['today'] = J(s2)
s2, _ = act(s2, 'jr_trip_board')
out['states']['fly'] = J(s2)
s2, _ = act(s2, 'jr_trip_meal', food='com_ga', drink='tra_nong')
s2, _ = act(s2, 'jr_trip_land')
out['states']['here'] = J(s2)
s2, _ = act(s2, 'jr_trip_spot', id='dl_ho')
s2, _ = act(s2, 'jr_trip_buy', id='dl_mut')
out['states']['here2'] = J(s2)
s2, _ = act(s2, 'jr_trip_home')
out['states']['back'] = J(s2)
s2, r = act(s2, 'jr_trip_land')
out['states']['done'] = J(s2)
out['summary'] = r['travel']['summary']
print(json.dumps(out, ensure_ascii=False))
`],{cwd:root,encoding:'utf8',maxBuffer:1<<24});
  return JSON.parse(out);
}
