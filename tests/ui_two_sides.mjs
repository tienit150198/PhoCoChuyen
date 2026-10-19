// Both sides of every career (owner 19/10, #440 "các nghề đều phải có cả 2 bên"): the per-career interface choice
// (public/js/v4/shell.js careerCleanPref / setCareerCleanPref / setCleanCareer → html[data-clean]) and the tap guard of
// long choice lists (public/js/ui-kit.js tapSlip). Run: node tests/ui_two_sides.mjs (exits non-zero on failure).
import assert from 'node:assert/strict';

const store=new Map();
globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
const attrs=new Set();
const root={dataset:{layout:'desktop'},classList:{remove(){},add(){},toggle(){},contains:()=>false},style:{setProperty(){}},
  hasAttribute:a=>attrs.has(a),toggleAttribute:(a,on)=>{if(on)attrs.add(a);else attrs.delete(a);},setAttribute(){},removeAttribute(){}};
const el=()=>({style:{},dataset:{},classList:{add(){},remove(){},toggle(){}},append(){},setAttribute(){},addEventListener(){}});
globalThis.document={documentElement:root,head:el(),body:el(),addEventListener(){},querySelectorAll:()=>[],querySelector:()=>null,getElementById:()=>null,createElement:el};
globalThis.window={addEventListener(){},innerWidth:1366,innerHeight:900,matchMedia:()=>({matches:false})};
globalThis.matchMedia=()=>({matches:false});

const shell=await import('../public/js/v4/shell.js');
const {tapSlip,TAP_FLING}=await import('../public/js/ui-kit.js');
const on=()=>attrs.has('data-clean');

// Desktop, global "Tự động": the full layout; a phone: the compact one.
shell.setCleanCareer('group_accounting');shell.applyClean();
assert.equal(on(),false);
root.dataset.layout='phone';shell.applyClean();
assert.equal(on(),true);

// The bookkeeper picks the full layout for their career only: it wins over the global pref while it is current…
shell.setCareerCleanPref('group_accounting','off');
assert.equal(on(),false);
assert.equal(shell.careerCleanPref('group_accounting'),'off');
assert.deepEqual(JSON.parse(store.get('mnl.clean.c')),{group_accounting:'off'});
// …another career keeps the global setting (compact on a phone), and coming back applies the choice again.
shell.setCleanCareer('florist');
assert.equal(on(),true);
assert.equal(shell.careerCleanPref('florist'),'');
shell.setCleanCareer('group_accounting');
assert.equal(on(),false);
// The compact side on a desktop, for one career.
root.dataset.layout='desktop';shell.setCareerCleanPref('florist','on');shell.setCleanCareer('florist');
assert.equal(on(),true);
assert.equal(shell.careerCleanCount(),2);
// "↩️ Theo cài đặt chung": back to the global pref.
shell.setCareerCleanPref('florist','');
assert.equal(on(),false);
assert.equal(shell.careerCleanPref('florist'),'');
// The global "Tắt" still turns the compact layout off where no career choice is set; a career's "on" still wins.
root.dataset.layout='phone';shell.setCleanPref('off');shell.setCleanCareer('pho');
assert.equal(on(),false);
shell.setCareerCleanPref('pho','on');
assert.equal(on(),true);
// The server's kill switch (MNL_CLEAN_UI=off) wins over everything.
shell.setCleanServer(false);
assert.equal(on(),false);
shell.setCleanServer(true);
assert.equal(on(),true);
// Cài đặt → "Bỏ lựa chọn riêng": every career back to the global pref; broken storage reads as "none".
shell.clearCareerClean();
assert.equal(shell.careerCleanCount(),0);
assert.equal(on(),false);
store.set('mnl.clean.c','not json');
assert.equal(shell.careerCleanPref('pho'),'');
store.set('mnl.clean.c','["x"]');
assert.equal(shell.careerCleanCount(),0);
// Storage that throws (a private window): nothing breaks, the global pref rules.
const keep=globalThis.localStorage;
globalThis.localStorage={getItem(){throw new Error('blocked');},setItem(){throw new Error('blocked');},removeItem(){throw new Error('blocked');}};
shell.setCareerCleanPref('pho','off');
assert.equal(shell.careerCleanPref('pho'),'');
globalThis.localStorage=keep;

// Tap guard: a click right after a touch counts only as a real tap.
const g=(o={})=>({t:1000,moved:false,flung:false,scrollAt:-1e9,...o});
assert.equal(tapSlip(g(),1100),false);                         // a plain tap
assert.equal(tapSlip(g({moved:true}),1100),true);              // the finger travelled: a drag/scroll
assert.equal(tapSlip(g({flung:true}),1100),true);              // it came down on a gliding list (stops the fling)
assert.equal(tapSlip(g({scrollAt:1050}),1100),true);           // the list scrolled while it was down
assert.equal(tapSlip(g({scrollAt:900,moved:false}),1100),false); // a scroll that ended before the touch (the flung flag decides)
assert.equal(tapSlip(g({moved:true}),5000),false);             // no touch just before: a mouse click or a key
assert.equal(tapSlip(null,10),false);
assert.ok(TAP_FLING>=100&&TAP_FLING<=250);
console.log('ui_two_sides: ok');
