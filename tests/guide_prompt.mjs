// Unit test of the per-workplace guide card (public/js/tutorial/announce.js guideDue, store.js guides*):
// once per workplace, never again after "Bỏ qua" or "Xem hướng dẫn" (both mark it seen), on any device (the
// mark rides in settings.notesSeen), never at a brand-new player's first workplace. Run by
// tests/test_guide_prompt.py (node tests/guide_prompt.mjs '<career ids json>'); exits non-zero on failure.
import assert from 'node:assert/strict';
import {guideDue,NOTES} from '../public/js/tutorial/announce.js';
import {GUIDE_BITS,guidesFrom,guidesId,notesSeen,markGuideSeen,markNoteSeen} from '../public/js/tutorial/store.js';

// Every workplace of the game has a bit (append only), and the packed id stays a valid notesSeen id.
const careers=JSON.parse(process.argv[2]||'[]');
for(const cid of careers)assert.ok(GUIDE_BITS.includes(cid),`${cid} is missing from store.js GUIDE_BITS (append it at the end)`);
assert.equal(new Set(GUIDE_BITS).size,GUIDE_BITS.length,'no workplace twice');
assert.ok(GUIDE_BITS.length<=105,'one id holds 105 workplaces');
const every=guidesId(new Set(GUIDE_BITS));
assert.match(every,/^[a-z0-9-]{1,24}$/,'the server accepts the id');
assert.deepEqual([...guidesFrom([every])].sort(),[...GUIDE_BITS].sort());
for(const cid of GUIDE_BITS)assert.deepEqual([...guidesFrom([guidesId(new Set([cid]))])],[cid],cid);
assert.equal(guidesId(new Set()),'');
assert.deepEqual([...guidesFrom(['gd-1','gd-2'])].sort(),[GUIDE_BITS[0],GUIDE_BITS[1]].sort(),'two devices merge');
assert.equal(NOTES.length,0,'the old "Có hướng dẫn mới" card is gone (the per-workplace card replaces it)');

// A fake player: settings synced through the "settings" command (store.js sync), no localStorage in node.
function player({current='cafe_bakery',careers={grocery:{day:3,started:true},cafe_bakery:{day:1,started:false},florist:{day:1}},notes='',story=true}={}){
  const state={current,careers,settings:{notesSeen:notes},journey:{story,life_day:3,intro:true}};
  const api={state,command:async(action,patch)=>{assert.equal(action,'settings');Object.assign(state.settings,patch);return {};}};
  return {api};
}
const due=env=>guideDue(env.api.state,notesSeen(env.api));

// The first time at a workplace: due once.
let env=player();
assert.equal(due(env),'cafe_bakery');
// "Bỏ qua" (or "Xem hướng dẫn": the card marks it seen either way): never again, here or on another device.
markGuideSeen(env,'cafe_bakery');
assert.equal(due(env),null,'not again after it was answered');
assert.match(env.api.state.settings.notesSeen,/(^|,)gd-[0-9a-v]+$/);
const other=player({notes:env.api.state.settings.notesSeen});
assert.equal(due(other),null,'not again on another device (same account)');
// The next new workplace still gets its own card, once.
env.api.state.current='florist';
assert.equal(due(env),'florist');
markGuideSeen(env,'florist');
assert.equal(due(env),null);
env.api.state.current='cafe_bakery';
assert.equal(due(env),null,'the first one stays answered');
assert.equal(env.api.state.settings.notesSeen.split(',').filter(x=>x.startsWith('gd-')).length,1,'one id for all workplaces');
// Other seen-flags keep theirs, and the guides id is never the one pushed out of the 12.
env=player({notes:'onb1,h-job,h-money'});markGuideSeen(env,'cafe_bakery');
for(let i=0;i<14;i++)markNoteSeen(env,'x-'+i);
const ids=env.api.state.settings.notesSeen.split(',');
assert.ok(ids.length<=12&&ids.every(x=>/^[a-z0-9-]{1,24}$/.test(x)),ids.join());
assert.equal(guideDue(env.api.state,notesSeen(env.api)),null,'still answered after many other notes');

// Not at a workplace already worked past its first day (players from before the card).
assert.equal(due(player({current:'grocery'})),null);
// A brand-new player's first workplace: the first-day tips teach it; their second workplace gets the card.
const fresh={grocery:{day:1,started:true}};
assert.equal(due(player({current:'grocery',careers:fresh,notes:'onb1'})),null,'first workplace of a new player');
assert.equal(due(player({current:'florist',careers:{...fresh,florist:{day:1}},notes:'onb1'})),'florist','their second workplace');
// A save without the onboarding (sandbox, older players) gets it at a new place, even the first one.
assert.equal(due(player({current:'grocery',careers:fresh,story:false})),'grocery');
assert.equal(guideDue({current:null,careers:{}},new Set()),null);
// A workplace whose work screen opens on its own "Giới thiệu nghề" card (pilot, street trades…): never both.
assert.equal(due(player({current:'pilot',careers:{grocery:{day:3,started:true},pilot:{day:1,data:{intro:false}}}})),null);
assert.equal(due(player({current:'pet_shop',careers:{grocery:{day:3,started:true},pet_shop:{day:1,data:{intro_seen:false}}}})),null);

console.log('guide_prompt.mjs: ok');
