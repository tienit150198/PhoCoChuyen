// Unit test of public/js/v4/whatsnew.js ("Có gì mới" card): when it is due and what keeps it
// waiting. Run by tests/test_whats_new.py (node tests/whats_new.mjs); exits non-zero on failure.
import assert from 'node:assert/strict';
import NOTES from '../public/js/v4/whatsnew-data.js';
import {compare,due,seenVersion,blocker,LATEST} from '../public/js/v4/whatsnew.js';

assert.equal(LATEST,NOTES[0].version);
assert.ok(compare('0.9.1','0.9.0')>0);
assert.ok(compare('0.10.0','0.9.9')>0,'numeric, not text order');
assert.equal(compare('0.9','0.9.0'),0);
assert.ok(compare('0.5.0','')>0,'"" is older than every release');
assert.equal(compare('',''),0);

const st=(seen,journey={story:true,intro:true,life_day:4})=>({settings:seen===undefined?{}:{whatsNewSeen:seen},journey,current:'grocery'});
// Once per release: due until the latest is read, never again after.
assert.equal(due(st('')),true,'an old save that never read the notes');
assert.equal(due(st(NOTES[1]?.version||'0.9.1')),true,'a player one release behind');
assert.equal(due(st(LATEST)),false,'read already: not again');
assert.equal(due(st('99.0.0')),false,'a newer release was read (rolled-back server)');
assert.equal(seenVersion(st('0.5.0')),'0.5.0');
assert.equal(seenVersion(st(undefined)),'','no key in the save and no storage: nothing read');

// What keeps it waiting.
function doc({hidden=false,tour=false,decision=false,menu=false,dialogs=[]}={}){
  return {hidden,
    getElementById:id=>id==='tutLayer'&&tour?{isConnected:true}:null,
    querySelectorAll:sel=>sel==='dialog[open]'?dialogs:sel==='.hap-choices'&&decision?[{offsetParent:{}},{offsetParent:null}]:[],
    documentElement:{classList:{contains:c=>c==='menu-open'&&menu}}};
}
const env=(state,view=null,paused=false)=>({api:{state},ui:{view,paused}});
const back=st('');
assert.equal(blocker(env(back),doc()),'','a returning player');
assert.equal(blocker(env(back,'job'),doc({dialogs:[{id:'sheet'}]})),'','over a work screen too (server-wide notice)');
assert.equal(blocker(env(back),doc({dialogs:[{id:'confirmDialog'}]})),'','over a question too');
assert.equal(blocker(env(back),doc({decision:true})),'','over a live decision too');
assert.equal(blocker(env(back),doc({menu:true})),'');
assert.equal(blocker(env(back),doc({dialogs:[{id:'tutWelcome'}]})),'tour','never over the tutorial welcome card');
assert.equal(blocker(env(back),doc({tour:true})),'tour','never over the tour');
assert.equal(blocker(env(back),doc({hidden:true})),'hidden');
assert.equal(blocker(env(null),doc()),'loading');
// A new player: only naming the character comes first.
assert.equal(blocker(env(st('',{story:true,intro:false,life_day:1})),doc()),'intro');
assert.equal(blocker(env(st('',{story:true,intro:true,life_day:1})),doc()),'','the first day: the notes show');
assert.equal(blocker(env(st('',{story:false,intro:false,life_day:1})),doc()),'','a save without the story has no intro');

console.log('whats_new.mjs: ok');
